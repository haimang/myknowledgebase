"""Execution-backed evidence records used by NHX1 phase and final gates."""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

_LAYER_RANK = {"contract": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4, "process-crash": 5, "full": 6}
_FALSE_GREEN = re.compile(r"(?:\b(?:skip|skipped|xfail|xfailed|xpass)\b|rerun-until-pass)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class EvidenceCommand:
    test_id: str
    argv: tuple[str, ...]
    work_items: tuple[str, ...]
    truth_ids: tuple[str, ...]
    profile: str
    observed_layer: str
    minimum_layer: str


def execute(command: EvidenceCommand, *, repository_root: Path) -> dict[str, object]:
    completed = subprocess.run(command.argv, cwd=repository_root, text=True, capture_output=True, check=False)
    stdout = completed.stdout + completed.stderr
    commit = subprocess.run(
        ("git", "rev-parse", "HEAD"), cwd=repository_root, text=True, capture_output=True, check=True
    ).stdout.strip()
    record = {
        **asdict(command),
        "argv": list(command.argv),
        "work_items": list(command.work_items),
        "truth_ids": list(command.truth_ids),
        "commit": commit,
        "observed_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "exit_code": completed.returncode,
        "stdout_digest": hashlib.sha256(stdout.encode()).hexdigest(),
        "stdout": stdout,
    }
    verify(record, expected_commit=commit)
    return record


def verify(record: dict[str, object], *, expected_commit: str) -> None:
    if record.get("commit") != expected_commit or not re.fullmatch(r"[0-9a-f]{40}", str(record.get("commit", ""))):
        raise ValueError("evidence commit does not match the current full SHA")
    if record.get("exit_code") != 0:
        raise ValueError("evidence command did not exit zero")
    stdout = str(record.get("stdout", ""))
    if stdout.strip().upper() == "PASS" or _FALSE_GREEN.search(stdout):
        raise ValueError("success-shaped or degraded output is not executable evidence")
    if hashlib.sha256(stdout.encode()).hexdigest() != record.get("stdout_digest"):
        raise ValueError("evidence stdout digest mismatch")
    try:
        datetime.strptime(str(record["observed_at_utc"]), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except (KeyError, ValueError) as exc:
        raise ValueError("evidence UTC timestamp is invalid") from exc
    observed = str(record.get("observed_layer", ""))
    minimum = str(record.get("minimum_layer", ""))
    if observed not in _LAYER_RANK or minimum not in _LAYER_RANK or _LAYER_RANK[observed] < _LAYER_RANK[minimum]:
        raise ValueError("evidence did not reach its minimum layer")
    if not record.get("profile") or not record.get("argv") or not record.get("work_items") or not record.get("truth_ids"):
        raise ValueError("evidence command is missing its profile, command, work, or Truth coordinates")
