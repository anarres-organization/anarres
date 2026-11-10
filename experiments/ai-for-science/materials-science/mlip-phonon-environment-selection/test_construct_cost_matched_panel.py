import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parent / "construct_cost_matched_panel.py"
SPEC = importlib.util.spec_from_file_location("construct_cost_matched_panel", SCRIPT)
assert SPEC is not None
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def synthetic_candidates():
    values = []
    rules = MODULE.CONSTRUCTOR.SELECTION_RULES
    for source_index in range(8):
        for rule_index, rule in enumerate(rules):
            values.append(
                {
                    "candidate_id": f"source-{source_index}__{rule}",
                    "signal_density_per_atom": 1.0 + source_index + rule_index,
                    "effective_signal_coverage": 0.05 + 0.02 * rule_index,
                    "chemical_system_entropy": 0.8 + 0.01 * source_index,
                    "mean_target_affinity": 0.1 + 0.01 * (source_index + rule_index),
                    "record_indices": [
                        source_index * 100 + rule_index,
                        source_index * 100 + 50,
                    ],
                }
            )
    return values


def test_panel_selection_balances_sources_and_rules():
    selected = MODULE.choose_panel(synthetic_candidates())
    assert len(selected) == 16
    sources = [candidate["candidate_id"].rsplit("__", 1)[0] for candidate in selected]
    rules = [candidate["candidate_id"].rsplit("__", 1)[1] for candidate in selected]
    assert all(sources.count(source) == 2 for source in set(sources))
    assert min(rules.count(rule) for rule in set(rules)) >= 2
    assert max(rules.count(rule) for rule in set(rules)) <= 3


def test_prospective_split_preserves_four_sources_and_rules():
    panel = MODULE.choose_panel(synthetic_candidates())
    prospective = MODULE.choose_prospective(panel)
    chosen = [candidate for candidate in panel if candidate["candidate_id"] in prospective]
    assert len(chosen) == 4
    sources = {candidate["candidate_id"].rsplit("__", 1)[0] for candidate in chosen}
    assert len(sources) == 4
    assert len({candidate["candidate_id"].rsplit("__", 1)[1] for candidate in chosen}) == 4
