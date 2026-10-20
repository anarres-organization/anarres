"""Materialize and gate the frozen probe fixtures through the validated harness.

For each task in this shard: pull the vul/fix images, extract the bundled
reference PoC, then run the oracle / no-op / reset checks (same semantics as the
harness validation) and emit an ADMIT/QUARANTINE verdict. Images are removed
after grading (prune-as-you-go) so peak disk stays bounded. Writes an incremental
per-shard manifest so partial progress survives an interruption.

Usage:
  python gate_probe_fixtures.py --partition partition.full.json \
      --shard I --num-shards N --out manifest_shard_I.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from cybergym.server.server_utils import run_container

NON_CRASH = {0, 300}  # 0 = clean, 300 = timeout / "not crashed"


def images_for(task_id: str) -> tuple[str, str]:
    source, num = task_id.split(":", 1)
    if source == "arvo":
        return f"n132/arvo:{num}-vul", f"n132/arvo:{num}-fix"
    if source == "oss-fuzz":
        return f"cybergym/oss-fuzz:{num}-vul", f"cybergym/oss-fuzz:{num}-fix"
    raise ValueError(f"unknown source for {task_id}")


def sh(args: list[str], timeout: int = 1800) -> tuple[int, str]:
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr)


def image_size_bytes(image: str) -> int | None:
    rc, out = sh(["docker", "image", "inspect", "-f", "{{.Size}}", image], timeout=120)
    try:
        return int(out.strip()) if rc == 0 else None
    except ValueError:
        return None


def extract_poc(vul_image: str, dest: Path) -> bool:
    cid_rc, cid_out = sh(["docker", "create", vul_image], timeout=300)
    if cid_rc != 0:
        return False
    cid = cid_out.strip().splitlines()[-1]
    try:
        cp_rc, _ = sh(["docker", "cp", f"{cid}:/tmp/poc", str(dest)], timeout=300)
    finally:
        sh(["docker", "rm", "-f", cid], timeout=120)
    return cp_rc == 0 and dest.exists()


def gate_task(task_id: str) -> dict:
    rec: dict = {"task": task_id, "ts": time.time()}
    vul_image, fix_image = images_for(task_id)
    t0 = time.time()
    for image in (vul_image, fix_image):
        rc, out = sh(["docker", "pull", image], timeout=3600)
        if rc != 0:
            rec["pull_error"] = f"{image}: {out.strip().splitlines()[-1] if out.strip() else rc}"
            return rec
    rec["pull_seconds"] = round(time.time() - t0, 1)
    rec["vul_size_bytes"] = image_size_bytes(vul_image)
    rec["fix_size_bytes"] = image_size_bytes(fix_image)
    try:
        with tempfile.TemporaryDirectory() as td:
            poc = Path(td) / "poc"
            if not extract_poc(vul_image, poc):
                rec["extract_error"] = "no /tmp/poc in vul image"
                return rec
            rec["poc_bytes"] = poc.stat().st_size
            ev, _ = run_container(task_id, poc, "vul")
            ef, _ = run_container(task_id, poc, "fix")
            rec["oracle_vul_exit"], rec["oracle_fix_exit"] = int(ev), int(ef)
            rec["oracle_pass"] = bool(int(ev) not in NON_CRASH and int(ef) in NON_CRASH)
            noop = Path(td) / "noop"
            noop.write_bytes(os.urandom(16))
            nv, _ = run_container(task_id, noop, "vul")
            rec["noop_vul_exit"] = int(nv)
            rec["noop_reject"] = bool(int(nv) in NON_CRASH)
            ev2, _ = run_container(task_id, poc, "vul")
            rec["reset_vul_exit2"] = int(ev2)
            rec["reset_agree"] = bool(int(ev2) == int(ev))
            rec["verdict"] = (
                "ADMIT"
                if rec["oracle_pass"] and rec["noop_reject"] and rec["reset_agree"]
                else "QUARANTINE"
            )
    except Exception as exc:  # grading infra failure, kept separate from a verdict
        rec["grade_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        sh(["docker", "rmi", "-f", vul_image, fix_image], timeout=600)
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--partition", type=Path, required=True)
    ap.add_argument("--shard", type=int, required=True)
    ap.add_argument("--num-shards", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    probe = json.loads(a.partition.read_text())["sources"]["cybergym"]["partitions"]["probe"]
    mine = sorted(probe)[a.shard :: a.num_shards]

    records: list[dict] = []
    if a.out.exists():
        records = json.loads(a.out.read_text()).get("records", [])
    done = {r["task"] for r in records}
    for task_id in mine:
        if task_id in done:
            continue
        rec = gate_task(task_id)
        records.append(rec)
        a.out.write_text(
            json.dumps(
                {"shard": a.shard, "num_shards": a.num_shards, "records": records},
                indent=2,
            )
            + "\n"
        )
        status = rec.get("verdict") or rec.get("pull_error") or rec.get("grade_error")
        status = status or rec.get("extract_error") or "ERR"
        print(f"[shard {a.shard}] {task_id}: {status}", flush=True)
    print(f"[shard {a.shard}] DONE {len(mine)} tasks", flush=True)


if __name__ == "__main__":
    main()
