from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
VERO_ROOT = ROOT / "data" / "formal-verification" / "vero"
if str(VERO_ROOT) not in sys.path:
    sys.path.insert(0, str(VERO_ROOT))
PROTOCOL_PATH = VERO_ROOT / "policy-probe-protocol.codex-sol-v2.json"
QUEUE_PATH = VERO_ROOT / "probe-queue.codex-sol-v2.json"
ANALYSIS_PATH = VERO_ROOT / "measurement-analysis.codex-sol-v1.json"
PROTOCOL = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
QUEUE = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
ANALYSIS = json.loads(ANALYSIS_PATH.read_text(encoding="utf-8"))
AUTHORIZATION_SHA256 = "a" * 64


def load(name: str, filename: str) -> ModuleType:
    specification = importlib.util.spec_from_file_location(name, VERO_ROOT / filename)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"could not load {filename}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


VALIDATOR = load("vero_validate_codex_sol_probe_protocol", "validate_codex_sol_probe_protocol.py")
BUILDER = load("vero_build_probe_queue_sol", "build_probe_queue.py")
AGGREGATOR = load("vero_aggregate_codex_sol_measurements", "aggregate_codex_sol_measurements.py")
RUNNER = load("vero_run_codex_sol_queue_item", "run_codex_sol_queue_item.py")
PROBE = load("vero_codex_sol_probe_for_measurement", "run_codex_sol_probe.py")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def authorization_record(**overrides: object) -> dict[str, object]:
    return {
        "schema_version": RUNNER.AUTHORIZATION_SCHEMA,
        "authorized": True,
        "protocol_sha256": digest(PROTOCOL_PATH),
        "queue_sha256": digest(QUEUE_PATH),
        "spend_ceiling_usd": 250,
        "per_attempt_reserve_usd": 15,
        **overrides,
    }


def fake_result(
    entry: dict,
    *,
    passed: int = 0,
    statuses: dict[int, str] | None = None,
    infrastructure: str | None = None,
    integrity: bool = False,
    tree: str = "tree",
) -> object:
    """An attempt result with ``passed`` leading passes and the given status overrides."""
    result = PROBE.AttemptResult(
        attempt_id=f"{entry['benchmark_id']}_{entry['mode']}_a{entry['replicate']}_00000000",
        benchmark_id=entry["benchmark_id"],
        mode=entry["mode"],
        attempt_index=entry["replicate"],
        turns=10,
        input_tokens=1_000_000,
        cached_input_tokens=900_000,
        output_tokens=10_000,
        reasoning_output_tokens=4_000,
        tool_calls=12,
        wall_seconds=100.0,
        stop_reason="stop",
        materialization={"task_tree_sha256": tree, "instruction_sha256": "instruction"},
    )
    if infrastructure:
        result.infrastructure_errors.append(infrastructure)
        return result
    if integrity:
        result.integrity_errors.append("workspace collection failed: too many entries")
        return result
    statuses = statuses or {}
    specs = [
        {
            "module": "Spec",
            "spec": f"spec_{index:03d}",
            "status": statuses.get(index, "passed" if index < passed else "build_error"),
        }
        for index in range(entry["expected_specifications"])
    ]
    result.grade = {"total_specs": len(specs), "specs": specs}
    return result


def receipt_for(entry: dict, *results: object) -> dict:
    runs = [
        RUNNER.run_record(entry, run, "attempt", result)
        for run, result in enumerate(results, start=1)
    ]
    return RUNNER.grade_receipt(entry, runs, ANALYSIS, AUTHORIZATION_SHA256)


def receipts_passing(passed: object) -> dict[str, dict]:
    """One receipt per queue entry; ``passed(entry)`` gives its leading pass count."""
    return {
        entry["attempt_id"]: receipt_for(entry, fake_result(entry, passed=passed(entry)))
        for entry in QUEUE["attempts"]
    }


def mixed_receipts() -> dict[str, dict]:
    """Each replicate r passes the first 2r specifications of every repository."""
    return receipts_passing(
        lambda entry: min(entry["expected_specifications"], 2 * entry["replicate"])
    )


class FrozenProtocolTest(unittest.TestCase):
    def test_protocol_validates_against_the_qualified_route(self) -> None:
        VALIDATOR.validate(PROTOCOL)
        self.assertFalse(PROTOCOL["execution_authorized"])
        self.assertEqual(
            PROTOCOL["execution_interface"]["runtime_image_id"],
            "sha256:9ca594ce645b2be8903dcdadd7c58c11bb0d8b7448077842ee559e0a4dfb574c",
        )

    def test_stopped_v1_queue_counts_against_the_approved_total(self) -> None:
        stop = json.loads(
            (VERO_ROOT / "results/repeated-measurement-stop.codex-sol-v1.json").read_text()
        )
        authorization = json.loads(
            (VERO_ROOT / "execution-authorization.codex-sol-v2.json").read_text()
        )
        self.assertEqual(authorization["protocol_sha256"], digest(PROTOCOL_PATH))
        self.assertEqual(authorization["queue_sha256"], digest(QUEUE_PATH))
        self.assertAlmostEqual(
            stop["planning_usd_total"] + authorization["spend_ceiling_usd"], 250, places=2
        )
        self.assertAlmostEqual(
            sum(run["planning_usd"] or 0 for run in stop["runs"]),
            stop["planning_usd_total"],
            places=2,
        )
        # The stop record must stay outcome-blind: only run identity, cost, and infrastructure.
        allowed = {
            "attempt_id",
            "run",
            "kind",
            "outcome",
            "input_tokens",
            "cached_input_tokens",
            "output_tokens",
            "reasoning_output_tokens",
            "turns",
            "stop_reason",
            "infrastructure_errors",
            "planning_usd",
        }
        for run in stop["runs"]:
            self.assertLessEqual(set(run), allowed)
            self.assertIn(run["outcome"], {"scored", "integrity_failure", "infrastructure_failure"})
        # The executed v1 artifacts stay frozen exactly as the stop record names them.
        frozen = {
            "policy-probe-protocol.codex-sol-v1.json": stop["protocol_sha256"],
            "probe-queue.codex-sol-v1.json": stop["queue_sha256"],
            "execution-authorization.codex-sol-v1.json": stop["authorization_sha256"],
        }
        for name, expected in frozen.items():
            self.assertEqual(digest(VERO_ROOT / name), expected, name)
        self.assertEqual(
            stop["protocol_sha256"],
            "08bc80f95dfa664563e0f1f8e5cfdba4bb709200c5bfdfaafb41fc562c66c1fb",
        )

    def test_queue_matches_the_protocol_and_panel(self) -> None:
        panel_path = VERO_ROOT / PROTOCOL["source"]["development_panel"]
        expected = BUILDER.build_queue(
            PROTOCOL,
            json.loads(panel_path.read_text(encoding="utf-8")),
            protocol_sha256=digest(PROTOCOL_PATH),
            panel_sha256=digest(panel_path),
        )
        self.assertEqual(QUEUE, expected)
        self.assertEqual(len(QUEUE["attempts"]), 32)
        self.assertEqual(len({entry["attempt_id"] for entry in QUEUE["attempts"]}), 32)
        for entry in QUEUE["attempts"]:
            self.assertIn("-sol-v2-r0", entry["attempt_id"])
            self.assertEqual(entry["output_token_stop_threshold"], 200_000)
            self.assertEqual(entry["maximum_agent_turns"], 100)

    def test_cost_plan_comes_from_the_released_screen_record(self) -> None:
        screen = json.loads((VERO_ROOT / PROTOCOL["cost_plan"]["basis_record"]).read_text())
        self.assertEqual(screen["totals"]["passed_specs"], 388)
        self.assertEqual(screen["totals"]["total_specs"], 694)
        larger = [
            attempt
            for attempt in screen["attempts"]
            if attempt["benchmark_id"] in ("verified-bitmasks", "arithmetic-v2")
        ]
        self.assertEqual({attempt["stop_reason"] for attempt in larger}, {"max_turns"})
        protocol = copy.deepcopy(PROTOCOL)
        protocol["cost_plan"]["screen_planning_usd"] = 20.0
        with self.assertRaisesRegex(VALIDATOR.ProtocolError, "screen record"):
            VALIDATOR.validate(protocol)

    def test_protocol_cannot_authorize_its_own_execution(self) -> None:
        protocol = copy.deepcopy(PROTOCOL)
        protocol["execution_authorized"] = True
        with self.assertRaisesRegex(VALIDATOR.ProtocolError, "separate record"):
            VALIDATOR.validate(protocol)

    def test_policy_settings_must_match_the_qualified_harness(self) -> None:
        for section, field, value in (
            ("starting_policy", "reasoning_effort", "high"),
            ("probe_design", "maximum_agent_turns_per_attempt", 200),
            ("probe_design", "output_token_stop_threshold_per_attempt", 400_000),
        ):
            protocol = copy.deepcopy(PROTOCOL)
            protocol[section][field] = value
            with self.assertRaisesRegex(VALIDATOR.ProtocolError, "qualified harness"):
                VALIDATOR.validate(protocol)

    def test_retry_policy_is_one_infrastructure_retry(self) -> None:
        protocol = copy.deepcopy(PROTOCOL)
        protocol["probe_design"]["scientific_retry_count"] = 1
        with self.assertRaisesRegex(VALIDATOR.ProtocolError, "retry policy"):
            VALIDATOR.validate(protocol)

    def test_tampered_inputs_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vero"
            shutil.copytree(VERO_ROOT, root, ignore=shutil.ignore_patterns("__pycache__"))
            VALIDATOR.validate(PROTOCOL, root)
            for name, mutate in (
                ("measurement-analysis.codex-sol-v1.json", self.change_inherited_estimand),
                ("run_codex_sol_queue_item.py", lambda text: text + "\n# edited\n"),
                ("run_codex_sol_probe.py", lambda text: text + "\n# edited\n"),
                ("source-pin.json", lambda text: text.replace("0a7325df", "0a7325dd", 1)),
            ):
                path = root / name
                original = path.read_text(encoding="utf-8")
                path.write_text(mutate(original), encoding="utf-8")
                with self.assertRaises((VALIDATOR.ProtocolError, ValueError)):
                    VALIDATOR.validate(PROTOCOL, root)
                path.write_text(original, encoding="utf-8")

    @staticmethod
    def change_inherited_estimand(text: str) -> str:
        analysis = json.loads(text)
        analysis["admission_summary"]["minimum_mixed_specification_groups"] = 1
        return json.dumps(analysis)

    def test_analysis_inherits_the_earlier_estimands(self) -> None:
        inherited = json.loads((VERO_ROOT / "measurement-analysis.v2.json").read_text())
        for field in VALIDATOR.INHERITED_ESTIMANDS:
            self.assertEqual(ANALYSIS[field], inherited[field])
        self.assertEqual(ANALYSIS["specification_scoring"]["strict_reward_one"], ["passed"])
        for status in ("check_incomplete", "sat_unverified", "axiom_recheck_failed"):
            self.assertIn(status, ANALYSIS["specification_scoring"]["strict_reward_zero"])


class AggregateTest(unittest.TestCase):
    def test_mixed_outcomes_are_ready(self) -> None:
        result = AGGREGATOR.aggregate(QUEUE, ANALYSIS, mixed_receipts())
        self.assertEqual(result["decision"], "ready")
        self.assertTrue(result["support"]["passes_support_gate"])
        self.assertTrue(result["readiness"]["passes_readiness_gate"])
        primepy = result["measurements_by_mode"]["proof"]["repositories"]["primepy"]
        self.assertEqual(
            primepy["specifications_by_successes"], {"0": 1, "1": 2, "2": 2, "3": 2, "4": 2}
        )
        self.assertEqual(primepy["union_coverage"], 8 / 9)
        self.assertEqual(result["attempt_outcomes"], {"scored": 32, "integrity_failure": 0})
        self.assertEqual(result["runs"]["scored_runs"], 32)
        self.assertEqual(result["authorization_sha256"], AUTHORIZATION_SHA256)
        self.assertGreater(result["cost"]["planning_usd"], 0)

    def test_uniform_outcomes_abstain(self) -> None:
        result = AGGREGATOR.aggregate(QUEUE, ANALYSIS, receipts_passing(lambda entry: 0))
        self.assertEqual(result["decision"], "abstain")
        self.assertEqual(result["abstention_reason"], "readiness_gate_failed")
        self.assertFalse(result["support"]["passes_support_gate"])
        self.assertIsNone(result["cost"]["model_tokens_per_strict_success"])

    def test_one_mixed_repository_fails_readiness(self) -> None:
        receipts = receipts_passing(
            lambda entry: 2 * entry["replicate"] if entry["benchmark_id"] == "arithmetic-v2" else 0
        )
        result = AGGREGATOR.aggregate(QUEUE, ANALYSIS, receipts)
        self.assertEqual(result["decision"], "abstain")
        self.assertEqual(
            result["readiness"]["mixed_groups_after_leaving_out_repository"]["arithmetic-v2"], 0
        )

    def test_leaving_out_the_main_repository_can_fail_readiness_alone(self) -> None:
        def passed(entry: dict) -> int:
            if entry["benchmark_id"] == "arithmetic-v2":
                return 2 * entry["replicate"]
            return 1 if entry["benchmark_id"] == "primepy" and entry["replicate"] == 1 else 0

        result = AGGREGATOR.aggregate(QUEUE, ANALYSIS, receipts_passing(passed))
        self.assertTrue(result["support"]["passes_support_gate"])
        for names in result["readiness"]["repositories_with_mixed_groups_by_mode"].values():
            self.assertEqual(names, ["arithmetic-v2", "primepy"])
        self.assertEqual(
            result["readiness"]["mixed_groups_after_leaving_out_repository"]["arithmetic-v2"], 2
        )
        self.assertFalse(result["readiness"]["passes_readiness_gate"])
        self.assertEqual(result["decision"], "abstain")

    def test_unconfirmed_passes_count_only_in_the_sensitivity(self) -> None:
        receipts = mixed_receipts()
        entry = QUEUE["attempts"][0]
        statuses = {0: "check_incomplete", 1: "sat_unverified"}
        receipts[entry["attempt_id"]] = receipt_for(
            entry, fake_result(entry, passed=0, statuses=statuses)
        )
        result = AGGREGATOR.aggregate(QUEUE, ANALYSIS, receipts)
        baseline = AGGREGATOR.aggregate(QUEUE, ANALYSIS, mixed_receipts())
        primary = result["support"]["pooled_strict_successes"]
        upper = result["sensitivity"]["support"]["pooled_strict_successes"]
        self.assertEqual(upper - primary, 2)
        lost = min(entry["expected_specifications"], 2 * entry["replicate"])
        self.assertEqual(baseline["support"]["pooled_strict_successes"] - primary, lost)
        self.assertEqual(result["specification_statuses"]["check_incomplete"], 1)

    def test_integrity_failure_scores_zero_for_every_specification(self) -> None:
        receipts = mixed_receipts()
        entry = next(e for e in QUEUE["attempts"] if e["benchmark_id"] == "primepy")
        receipts[entry["attempt_id"]] = receipt_for(entry, fake_result(entry, integrity=True))
        result = AGGREGATOR.aggregate(QUEUE, ANALYSIS, receipts)
        self.assertEqual(result["attempt_outcomes"]["integrity_failure"], 1)
        baseline = AGGREGATOR.aggregate(QUEUE, ANALYSIS, mixed_receipts())
        self.assertEqual(
            baseline["support"]["pooled_strict_successes"]
            - result["support"]["pooled_strict_successes"],
            min(9, 2 * entry["replicate"]),
        )

    def test_a_cell_of_integrity_failures_scores_zero(self) -> None:
        receipts = mixed_receipts()
        cell = [e for e in QUEUE["attempts"] if e["task_id"] == "primepy:codeproof"]
        for entry in cell:
            receipts[entry["attempt_id"]] = receipt_for(entry, fake_result(entry, integrity=True))
        result = AGGREGATOR.aggregate(QUEUE, ANALYSIS, receipts)
        primepy = result["measurements_by_mode"]["codeproof"]["repositories"]["primepy"]
        self.assertEqual(primepy["strict_successes"], 0)
        self.assertEqual(primepy["specifications_by_successes"]["0"], 9)

    def test_infrastructure_failure_abstains_instead_of_scoring_zero(self) -> None:
        receipts = mixed_receipts()
        entry = QUEUE["attempts"][3]
        failed = fake_result(entry, infrastructure="sandbox: docker daemon unavailable")
        receipts[entry["attempt_id"]] = receipt_for(entry, failed, failed)
        result = AGGREGATOR.aggregate(QUEUE, ANALYSIS, receipts)
        self.assertEqual(result["decision"], "abstain")
        self.assertEqual(result["abstention_reason"], "infrastructure_incomplete")
        self.assertEqual(result["incomplete_attempts"], [entry["attempt_id"]])
        self.assertEqual(result["runs"]["infrastructure_failure_runs"], 2)
        self.assertNotIn("support", result)
        del receipts[entry["attempt_id"]]
        stopped = AGGREGATOR.aggregate(QUEUE, ANALYSIS, receipts, spend_ceiling_stopped=True)
        self.assertEqual(stopped["abstention_reason"], "spend_ceiling_reached")
        self.assertEqual(stopped["incomplete_attempts"], [entry["attempt_id"]])

    def test_receipts_must_follow_the_frozen_scoring_rule(self) -> None:
        receipts = mixed_receipts()
        entry = QUEUE["attempts"][0]
        receipts[entry["attempt_id"]]["per_specification"][-1]["strict_reward"] = 1
        with self.assertRaisesRegex(AGGREGATOR.AggregateError, "scoring rule"):
            AGGREGATOR.aggregate(QUEUE, ANALYSIS, receipts)
        receipts = mixed_receipts()
        receipts[entry["attempt_id"]]["per_specification"][0]["status"] = "made_up"
        with self.assertRaisesRegex(AGGREGATOR.AggregateError, "not in the frozen scoring"):
            AGGREGATOR.aggregate(QUEUE, ANALYSIS, receipts)

    def test_a_hidden_scientific_retry_is_rejected(self) -> None:
        receipts = mixed_receipts()
        entry = QUEUE["attempts"][0]
        receipts[entry["attempt_id"]] = receipt_for(
            entry, fake_result(entry, passed=0), fake_result(entry, passed=5)
        )
        with self.assertRaisesRegex(AGGREGATOR.AggregateError, "retried a scientific outcome"):
            AGGREGATOR.aggregate(QUEUE, ANALYSIS, receipts)

    def test_replicates_must_share_one_materialized_task(self) -> None:
        receipts = mixed_receipts()
        entry = QUEUE["attempts"][0]
        receipts[entry["attempt_id"]] = receipt_for(entry, fake_result(entry, tree="other"))
        with self.assertRaisesRegex(AGGREGATOR.AggregateError, "materialized differently"):
            AGGREGATOR.aggregate(QUEUE, ANALYSIS, receipts)

    def test_receipts_must_match_the_frozen_task_digests(self) -> None:
        frozen = {"task_tree_sha256": "tree", "instruction_sha256": "instruction"}
        digests = {entry["task_id"]: frozen for entry in QUEUE["attempts"]}
        AGGREGATOR.aggregate(QUEUE, ANALYSIS, mixed_receipts(), task_digests=digests)
        with self.assertRaisesRegex(AGGREGATOR.AggregateError, "not materialized as frozen"):
            AGGREGATOR.aggregate(
                QUEUE,
                ANALYSIS,
                mixed_receipts(),
                task_digests=PROTOCOL["probe_design"]["task_digests"],
            )

    def test_receipts_must_share_one_authorization(self) -> None:
        receipts = mixed_receipts()
        receipts[QUEUE["attempts"][0]["attempt_id"]]["authorization_sha256"] = "b" * 64
        with self.assertRaisesRegex(AGGREGATOR.AggregateError, "more than one"):
            AGGREGATOR.aggregate(QUEUE, ANALYSIS, receipts)

    def test_receipts_outside_the_queue_are_rejected(self) -> None:
        receipts = mixed_receipts()
        receipts["extra"] = copy.deepcopy(next(iter(receipts.values())))
        with self.assertRaisesRegex(AGGREGATOR.AggregateError, "outside the frozen queue"):
            AGGREGATOR.aggregate(QUEUE, ANALYSIS, receipts)

    def test_aggregate_binds_the_frozen_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authorization = Path(directory) / "authorization.json"
            authorization.write_text(json.dumps(authorization_record()))
            queue, analysis, digests = AGGREGATOR.bound_inputs(
                PROTOCOL_PATH, QUEUE_PATH, authorization
            )
            self.assertEqual(analysis, ANALYSIS)
            self.assertEqual(digests["analysis_sha256"], digest(ANALYSIS_PATH))
            edited = Path(directory) / "queue.json"
            changed = copy.deepcopy(queue)
            changed["attempts"].pop()
            edited.write_text(json.dumps(changed))
            with self.assertRaisesRegex(AGGREGATOR.AggregateError, "does not match"):
                AGGREGATOR.bound_inputs(PROTOCOL_PATH, edited, authorization)
            copied = Path(directory) / PROTOCOL_PATH.name
            shutil.copy(PROTOCOL_PATH, copied)
            with self.assertRaisesRegex(AGGREGATOR.AggregateError, "this study directory"):
                AGGREGATOR.bound_inputs(copied, QUEUE_PATH, authorization)


class AggregateReleaseTest(unittest.TestCase):
    def release(self, grades: Path, directory: Path) -> dict:
        authorization = directory / "authorization.json"
        authorization.write_text(json.dumps(authorization_record()))
        output = directory / "result.json"
        argv = [
            "aggregate",
            "--protocol",
            str(PROTOCOL_PATH),
            "--queue",
            str(QUEUE_PATH),
            "--authorization",
            str(authorization),
            "--grades",
            str(grades),
            "--output",
            str(output),
        ]
        loader = AGGREGATOR.load

        def load_without_git_check(name: str, filename: str) -> object:
            if filename == "run_codex_sol_queue_item.py":
                return SimpleNamespace(
                    QueueItemError=RUNNER.QueueItemError,
                    validate_committed_authorization=lambda _: None,
                    ledger=RUNNER.ledger,
                )
            return loader(name, filename)

        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch("builtins.print"),
            mock.patch.object(AGGREGATOR, "load", side_effect=load_without_git_check),
        ):
            AGGREGATOR.main()
        return json.loads(output.read_text())

    def test_a_rejected_ledger_is_released_as_an_abstention(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            grades = root / "grades"
            entry = QUEUE["attempts"][0]
            attempt_root = grades / entry["attempt_id"]
            attempt_root.mkdir(parents=True)
            (attempt_root / "run-2.started.json").write_text("{}")
            result = self.release(grades, root)
            self.assertEqual(result["decision"], "abstain")
            self.assertEqual(result["abstention_reason"], "aggregate_rejected")
            self.assertIn("QueueItemError", result["rejection"])
            self.assertEqual(result["inputs"]["queue_sha256"], digest(QUEUE_PATH))

    def test_a_rejected_ledger_behind_a_receipt_is_released(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            grades = root / "grades"
            entry = QUEUE["attempts"][0]
            attempt_root = grades / entry["attempt_id"]
            attempt_root.mkdir(parents=True)
            (attempt_root / "grade-receipt.json").write_text(
                json.dumps(receipt_for(entry, fake_result(entry, passed=1)))
            )
            (attempt_root / "run-2.started.json").write_text("{}")
            result = self.release(grades, root)
            self.assertEqual(result["abstention_reason"], "aggregate_rejected")
            self.assertIn("QueueItemError", result["rejection"])

    def test_runs_without_a_receipt_are_still_counted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            grades = root / "grades"
            entry = QUEUE["attempts"][0]
            attempt_root = grades / entry["attempt_id"]
            attempt_root.mkdir(parents=True)
            failed = fake_result(entry, infrastructure="sandbox: docker daemon unavailable")
            (attempt_root / "run-1.started.json").write_text(
                json.dumps({"attempt_id": entry["attempt_id"], "kind": "attempt"})
            )
            (attempt_root / "run-1.json").write_text(
                json.dumps(RUNNER.run_record(entry, 1, "attempt", failed))
            )
            (grades / "spend-ceiling-stop.json").write_text("{}")
            result = self.release(grades, root)
            self.assertEqual(result["abstention_reason"], "spend_ceiling_reached")
            self.assertEqual(result["runs"]["infrastructure_failure_runs"], 1)
            self.assertGreater(result["runs"]["recorded_planning_usd"], 0)


class QueueItemTest(unittest.TestCase):
    def authorization(self, **overrides: object) -> dict:
        return authorization_record(**overrides)

    def test_execution_requires_a_binding_authorization(self) -> None:
        RUNNER.validate_frozen_inputs(PROTOCOL_PATH, QUEUE_PATH, self.authorization())
        for overrides in (
            {"authorized": False},
            {"queue_sha256": "0" * 64},
            {"spend_ceiling_usd": 0},
            {"spend_ceiling_usd": True},
            {"spend_ceiling_usd": 10, "per_attempt_reserve_usd": 15},
            {"schema_version": "other"},
        ):
            with self.assertRaises(RUNNER.QueueItemError):
                RUNNER.validate_frozen_inputs(
                    PROTOCOL_PATH, QUEUE_PATH, self.authorization(**overrides)
                )
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / PROTOCOL_PATH.name
            shutil.copy(PROTOCOL_PATH, copied)
            with self.assertRaisesRegex(RUNNER.QueueItemError, "directory that runs it"):
                RUNNER.validate_frozen_inputs(copied, QUEUE_PATH, self.authorization())

    def test_execution_requires_a_committed_authorization_file(self) -> None:
        authorization = VERO_ROOT / "execution-authorization.test.json"

        def completed(returncode: int = 0, stdout: str = "") -> subprocess.CompletedProcess:
            return subprocess.CompletedProcess([], returncode, stdout, "")

        with mock.patch.object(
            RUNNER.subprocess,
            "run",
            side_effect=[completed(stdout=str(ROOT) + "\n"), completed(), completed()],
        ):
            RUNNER.validate_committed_authorization(authorization)
        with (
            mock.patch.object(
                RUNNER.subprocess,
                "run",
                side_effect=[completed(stdout=str(ROOT) + "\n"), completed(1), completed()],
            ),
            self.assertRaisesRegex(RUNNER.QueueItemError, "committed and unchanged"),
        ):
            RUNNER.validate_committed_authorization(authorization)
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(RUNNER.QueueItemError, "this study directory"),
        ):
            RUNNER.validate_committed_authorization(Path(directory) / "authorization.json")

    def test_entries_run_once_and_in_queue_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            first, second = QUEUE["attempts"][:2]
            RUNNER.select_entry(QUEUE, first["attempt_id"], output)
            with self.assertRaisesRegex(RUNNER.QueueItemError, "has not finished"):
                RUNNER.select_entry(QUEUE, second["attempt_id"], output)
            (output / first["attempt_id"]).mkdir()
            receipt = output / first["attempt_id"] / "grade-receipt.json"
            receipt.write_text("{}")
            with self.assertRaisesRegex(RUNNER.QueueItemError, "not its own"):
                RUNNER.select_entry(QUEUE, second["attempt_id"], output)
            receipt.write_text(json.dumps(receipt_for(first, fake_result(first, passed=1))))
            RUNNER.select_entry(QUEUE, second["attempt_id"], output)
            with self.assertRaisesRegex(RUNNER.QueueItemError, "already has a receipt"):
                RUNNER.select_entry(QUEUE, first["attempt_id"], output)

    def test_outcome_prefers_integrity_when_both_are_reported(self) -> None:
        entry = QUEUE["attempts"][0]
        result = fake_result(entry, integrity=True)
        result.infrastructure_errors.append("sandbox: collection outlasted its limit")
        self.assertEqual(RUNNER.outcome(result), "integrity_failure")
        self.assertFalse(RUNNER.run_record(entry, 1, "attempt", result)["grading_stage"])

    def test_collection_timeout_is_an_integrity_failure(self) -> None:
        entry = QUEUE["attempts"][0]
        result = fake_result(
            entry,
            infrastructure="sandbox: workspace collection failed: " + RUNNER.COLLECTION_TIMEOUT,
        )
        record = RUNNER.run_record(entry, 1, "attempt", result)
        self.assertEqual(record["outcome"], "integrity_failure")
        self.assertIn(RUNNER.COLLECTION_TIMEOUT, record["integrity_errors"][0])

    def run_with(
        self,
        output: Path,
        *results: object,
        leftovers: list[str] | None = None,
        **overrides: object,
    ) -> tuple:
        calls: list[dict] = []
        regrades: list[dict] = []
        sequence = list(results)

        def next_result() -> object:
            result = sequence.pop(0)
            if isinstance(result, BaseException):
                raise result
            return result

        def run_one_attempt(**arguments: object) -> object:
            calls.append(arguments)
            result = next_result()
            source = Path(arguments["probe_root"]) / result.attempt_id / "run" / "source"
            source.mkdir(parents=True, exist_ok=True)
            return result

        def grade_attempt(*arguments: object, **keywords: object) -> dict:
            regrades.append({"source": arguments[3], **keywords})
            return next_result().grade

        harness = SimpleNamespace(
            run_one_attempt=run_one_attempt,
            grade_attempt=grade_attempt,
            AttemptResult=PROBE.AttemptResult,
        )
        loader = RUNNER.load

        def fake_load(name: str, filename: str) -> object:
            if filename == PROTOCOL["starting_policy"]["harness"]:
                return harness
            return loader(name, filename)

        entry = QUEUE["attempts"][0]
        with (
            mock.patch.object(RUNNER, "load", side_effect=fake_load),
            mock.patch.object(RUNNER, "verify_vero", return_value="0" * 40),
            mock.patch.object(RUNNER, "leftover_containers", return_value=leftovers),
        ):
            receipt = RUNNER.run_entry(
                entry,
                PROTOCOL,
                ANALYSIS,
                self.authorization(**overrides),
                authorization_sha256=AUTHORIZATION_SHA256,
                output_root=output,
                vero_root=output / "vero",
                vero_python="python3",
                api_key="test-key",
            )
        return receipt, calls, regrades

    def test_infrastructure_failure_reruns_the_attempt_once(self) -> None:
        entry = QUEUE["attempts"][0]
        with tempfile.TemporaryDirectory() as directory:
            receipt, calls, regrades = self.run_with(
                Path(directory),
                fake_result(entry, infrastructure="sandbox: docker daemon unavailable"),
                fake_result(entry, passed=3),
            )
            self.assertEqual(len(calls), 2)
            self.assertEqual(regrades, [])
            image = PROTOCOL["execution_interface"]["runtime_image_id"]
            self.assertEqual(calls[0]["docker_image"], image)
            self.assertEqual(receipt["outcome"], "scored")
            self.assertEqual(
                [run["outcome"] for run in receipt["runs"]], ["infrastructure_failure", "scored"]
            )
            self.assertEqual(sum(r["strict_reward"] for r in receipt["per_specification"]), 3)
            AGGREGATOR.validate_ledger(Path(directory), {entry["attempt_id"]: receipt}, RUNNER)

    def test_grading_failure_regrades_the_preserved_workspace(self) -> None:
        entry = QUEUE["attempts"][0]
        with tempfile.TemporaryDirectory() as directory:
            receipt, calls, regrades = self.run_with(
                Path(directory),
                fake_result(entry, infrastructure="grade: grader exceeded 10800 seconds"),
                fake_result(entry, passed=4),
            )
            self.assertEqual(len(calls), 1)
            self.assertEqual(len(regrades), 1)
            self.assertTrue(str(regrades[0]["source"]).endswith("run/source"))
            self.assertEqual([run["kind"] for run in receipt["runs"]], ["attempt", "regrade"])
            self.assertEqual(receipt["outcome"], "scored")
            self.assertEqual(receipt["input_tokens"], 1_000_000)
            self.assertEqual(receipt["runs"][1]["input_tokens"], 0)
            self.assertEqual(sum(r["strict_reward"] for r in receipt["per_specification"]), 4)
            AGGREGATOR.validate_ledger(Path(directory), {entry["attempt_id"]: receipt}, RUNNER)

    def test_scientific_and_integrity_outcomes_are_never_retried(self) -> None:
        entry = QUEUE["attempts"][0]
        for first in (fake_result(entry, integrity=True), fake_result(entry, passed=0)):
            with tempfile.TemporaryDirectory() as directory:
                receipt, calls, _ = self.run_with(
                    Path(directory), first, fake_result(entry, passed=5)
                )
                self.assertEqual(len(calls), 1)
                self.assertNotEqual(receipt["outcome"], "infrastructure_failure")

    def test_an_interrupted_run_is_recorded_charged_and_resumed(self) -> None:
        entry = QUEUE["attempts"][0]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with self.assertRaises(KeyboardInterrupt):
                self.run_with(output, KeyboardInterrupt())
            attempt_root = output / entry["attempt_id"]
            self.assertTrue((attempt_root / "run-1.started.json").is_file())
            self.assertEqual(RUNNER.ledger(attempt_root)[0]["outcome"], "interrupted")
            self.assertEqual(RUNNER.spent_usd(output, ANALYSIS, 15), 15)
            receipt, calls, _ = self.run_with(output, fake_result(entry, passed=2))
            self.assertEqual(len(calls), 1)
            self.assertEqual([run["outcome"] for run in receipt["runs"]], ["interrupted", "scored"])
            AGGREGATOR.validate_ledger(output, {entry["attempt_id"]: receipt}, RUNNER)
            # Two interruptions exhaust the entry, which then has no score.
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            for _ in range(2):
                with self.assertRaises(KeyboardInterrupt):
                    self.run_with(output, KeyboardInterrupt())
            receipt, calls, _ = self.run_with(output)
            self.assertEqual(calls, [])
            self.assertEqual(receipt["outcome"], "infrastructure_failure")

    def test_resuming_requires_the_interrupted_run_to_be_cleaned_up(self) -> None:
        entry = QUEUE["attempts"][0]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with self.assertRaises(KeyboardInterrupt):
                self.run_with(output, KeyboardInterrupt())
            with self.assertRaisesRegex(RUNNER.QueueItemError, "remove leftover sandbox"):
                self.run_with(output, fake_result(entry, passed=1), leftovers=["abc123"])
            started = json.loads((output / entry["attempt_id"] / "run-1.started.json").read_text())
            self.assertEqual(started["vero_commit"], "0" * 40)

    def test_a_run_without_a_started_record_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            attempt_root = Path(directory)
            (attempt_root / "run-1").mkdir()
            with self.assertRaisesRegex(RUNNER.QueueItemError, "without a started record"):
                RUNNER.ledger(attempt_root)

    def test_an_unknown_status_still_writes_a_receipt_the_aggregate_rejects(self) -> None:
        entry = QUEUE["attempts"][0]
        with tempfile.TemporaryDirectory() as directory:
            receipt, calls, _ = self.run_with(
                Path(directory), fake_result(entry, passed=1, statuses={2: "new_vero_status"})
            )
            self.assertEqual(len(calls), 1)
            self.assertIsNone(receipt["per_specification"][2]["strict_reward"])
        receipts = mixed_receipts()
        receipts[entry["attempt_id"]] = receipt
        with self.assertRaisesRegex(AGGREGATOR.AggregateError, "not in the frozen scoring"):
            AGGREGATOR.aggregate(QUEUE, ANALYSIS, receipts)

    def test_spend_ceiling_stops_the_queue(self) -> None:
        entry = QUEUE["attempts"][0]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            earlier = output / "earlier"
            earlier.mkdir()
            (earlier / "run-1.started.json").write_text(
                json.dumps({"attempt_id": "earlier", "kind": "attempt"})
            )
            (earlier / "run-1.json").write_text(
                json.dumps(
                    {
                        "run": 1,
                        "kind": "attempt",
                        "outcome": "scored",
                        "input_tokens": 10_000_000,
                        "cached_input_tokens": 0,
                        "output_tokens": 0,
                    }
                )
            )
            with self.assertRaisesRegex(RUNNER.QueueItemError, "spend ceiling"):
                self.run_with(output, fake_result(entry, passed=1), spend_ceiling_usd=60)
            self.assertTrue((output / RUNNER.STOP_RECORD).is_file())
            with self.assertRaisesRegex(RUNNER.QueueItemError, "already stopped"):
                self.run_with(output, fake_result(entry, passed=1))

    def test_an_output_root_belongs_to_one_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            RUNNER.bind_root(output, AUTHORIZATION_SHA256)
            RUNNER.bind_root(output, AUTHORIZATION_SHA256)
            with self.assertRaisesRegex(RUNNER.QueueItemError, "different authorization"):
                RUNNER.bind_root(output, "b" * 64)


class FormalCliRepeatedMeasurementTest(unittest.TestCase):
    def test_status_reports_the_frozen_unauthorized_protocol(self) -> None:
        sys.path.insert(0, str(VERO_ROOT / "src"))
        from anarres_formal_adapter import cli

        arguments = argparse.Namespace(repository=ROOT)
        status = cli.command_status(arguments)
        repeated = status["repeated_measurement"]
        self.assertEqual(repeated["protocol_id"], PROTOCOL["protocol_id"])
        self.assertEqual(repeated["queue_sha256"], f"sha256:{digest(QUEUE_PATH)}")
        self.assertEqual(repeated["queued_attempts"], 32)
        self.assertTrue(repeated["frozen"])
        self.assertFalse(repeated["execution_authorized"])
        self.assertFalse(status["policy_probe_available"])
        self.assertEqual(
            status["next_required_gate"],
            "execution authorization for the frozen repeated measurement",
        )
        report = cli.command_qualification(arguments)
        self.assertEqual(report["repeated_measurement"], repeated)
        self.assertFalse(report["decision"]["repeated_measurement_authorized"])


if __name__ == "__main__":
    unittest.main()
