"""Collect-all orchestrator for MKB-0815-R2. One failure does not cancel siblings."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from runner import LANES, RESULTS, RUN_ROOT, SAMPLES, _load_dotenv, ingest_cell, load_or_create_team_uuid, parse_cell

ROOT = RUN_ROOT.parents[3]
FIRST_WAVE = ["N-A5", "N-A3", "N-A6", "N-A2", "Q-A5", "Q-A3"]
STATUS_PATH = RESULTS / "wave_status.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_JOURNAL_FORBIDDEN = frozenset({"structure_reject", "cli_structured_kind", "prompt", "content", "stdout"})


def _journal_row(row: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in row.items() if key not in _JOURNAL_FORBIDDEN}


def _write_meta(team_uuid: str) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / "_meta.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {}
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    subjects_md5 = (RUN_ROOT / "evidence" / "SUBJECTS.md5").read_bytes()
    import hashlib

    data.update(
        {
            "run_id": "MKB-0815-R2",
            "parent_run": "MKB-0815-R1",
            "team_name": "mkb-dogfood-0815-r2",
            "team_uuid": team_uuid,
            "git_head": head,
            "subjects_md5_file_md5": hashlib.md5(subjects_md5).hexdigest(),
            "started_at": data.get("started_at") or _now(),
            "status": "running",
            "first_wave": FIRST_WAVE,
            "settings_overrides": {
                "persistence_backend": "turso",
                "concurrent_writes_required": True,
                "ns1_cli_mode": "subprocess",
                "live_inference": True,
                "inference_probe_enabled": False,
                "inference_generate_timeout_seconds": 900,
                "database_path": str(RUN_ROOT / "runtime" / "mkb.turso.db"),
            },
            "updated_at": _now(),
        }
    )
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def _load_rows() -> list[dict[str, object]]:
    path = RESULTS / "runs.jsonl"
    if not path.exists():
        return []
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _write_status(cells: list[str], done: dict[str, dict[str, object]], current: str | None) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(
        json.dumps(
            {
                "run_id": "MKB-0815-R2",
                "updated_at": _now(),
                "current": current,
                "planned": cells,
                "done": {
                    cell: {
                        "task_status": row.get("task_status"),
                        "error_code": row.get("error_code"),
                        "wall_ms": row.get("wall_ms"),
                        "dispatch_pools": row.get("dispatch_pools"),
                    }
                    for cell, row in done.items()
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def extras_after(done: dict[str, dict[str, object]]) -> list[str]:
    extra: list[str] = []
    if done.get("N-A5", {}).get("task_status") == "succeeded":
        extra.append("N-A5g2")
    if done.get("Q-A5", {}).get("task_status") == "succeeded":
        extra.append("Q-A5g2")
    a2_or_a3 = any(done.get(cell, {}).get("task_status") == "succeeded" for cell in ("N-A2", "N-A3"))
    if a2_or_a3:
        extra.extend(["N-A1", "N-A4"])
    return extra


def run_cell(cell_id: str, team_uuid: str, *, key_suffix: str = "") -> dict[str, object]:
    parse_cell(cell_id)
    print(f"\n===== START {cell_id} {SAMPLES[cell_id.split('-', 1)[1]]['path']} {LANES[cell_id[0]]} suffix={key_suffix!r} =====", flush=True)
    try:
        return ingest_cell(cell_id, team_uuid=team_uuid, key_suffix=key_suffix)
    except Exception as exc:
        row = {
            "experiment_run_id": "MKB-0815-R2",
            "cell_id": cell_id,
            "sample_id": cell_id.split("-", 1)[1],
            "lane": cell_id[0],
            "team_uuid": team_uuid,
            "task_status": "failed",
            "error_code": "collect-exception",
            "error_message": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc()[-2000:],
        }
        RESULTS.mkdir(parents=True, exist_ok=True)
        with (RESULTS / "runs.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(_journal_row(row), ensure_ascii=False) + "\n")
        print("collect-exception", cell_id, type(exc).__name__, exc, flush=True)
        return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rerun", action="store_true", help="ignore prior jsonl terminals and run FIRST_WAVE again")
    parser.add_argument("--cells", default="", help="comma-separated cell ids; default FIRST_WAVE")
    parser.add_argument("--suffix", default="", help="appended to external_key, e.g. -r3")
    parser.add_argument("--no-extras", action="store_true", help="do not append A5g2/A1/A4")
    args = parser.parse_args()
    os.chdir(ROOT)
    _load_dotenv()
    team_uuid = load_or_create_team_uuid()
    _write_meta(team_uuid)
    planned = [item.strip() for item in args.cells.split(",") if item.strip()] or list(FIRST_WAVE)
    done: dict[str, dict[str, object]] = {}
    if not args.rerun:
        for row in _load_rows():
            cell = row.get("cell_id")
            if isinstance(cell, str) and row.get("task_status") in {"succeeded", "failed", "cancelled", "timeout"}:
                done[cell] = row
    extras_added = False
    index = 0
    while index < len(planned):
        cell = planned[index]
        index += 1
        if cell in done:
            print(f"skip already-terminal {cell}", flush=True)
            continue
        _write_status(planned, done, cell)
        done[cell] = run_cell(cell, team_uuid, key_suffix=args.suffix)
        _write_status(planned, done, None)
        if not args.no_extras and not extras_added and set(FIRST_WAVE) <= set(done):
            more = extras_after(done)
            extras_added = True
            for extra in more:
                if extra not in planned:
                    planned.append(extra)
            print("extras", more, flush=True)
    meta = json.loads((RESULTS / "_meta.json").read_text(encoding="utf-8"))
    meta["status"] = "ingest-complete"
    meta["completed_at"] = _now()
    meta["wave"] = {
        "planned": planned,
        "succeeded": [cell for cell, row in done.items() if row.get("task_status") == "succeeded"],
        "failed": [cell for cell, row in done.items() if row.get("task_status") != "succeeded"],
    }
    (RESULTS / "_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    _write_status(planned, done, None)
    print("INGEST COMPLETE", json.dumps(meta["wave"], ensure_ascii=False), flush=True)
    if any(row.get("task_status") == "succeeded" for row in done.values()):
        retrieve = subprocess.run([sys.executable, str(RUN_ROOT / "retrieve.py")], cwd=ROOT)
        print("retrieve", retrieve.returncode, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
