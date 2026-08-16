"""R3 preflight kit: method, protocol, subjects, and owner gate files exist."""

from __future__ import annotations

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
R3 = REPOSITORY_ROOT / ".experiment/0815/runs/MKB-0815-R3"
REQUIRED = (
    R3 / "RUN.md",
    R3 / "preflight.py",
    R3 / "collect.py",
    R3 / "retrieve.py",
    R3 / "results/OBJECTIVES.md",
    R3 / "protocol/T-O-375.md",
    R3 / "protocol/after-NS3-test-plan.md",
    R3 / "protocol/NS4-generation-evidence-plane-closure.md",
    R3 / "subjects/manifest.json",
    R3 / "evidence/SUBJECTS.md5",
    R3 / "evidence/PROTOCOL.md5",
    R3 / "evidence/METHOD.md5",
    R3 / "evidence/SEAL.json",
)


def test_r3_kit_files_exist() -> None:
    missing = [str(path.relative_to(REPOSITORY_ROOT)) for path in REQUIRED if not path.is_file()]
    assert missing == [], "R3 preflight kit incomplete:\n" + "\n".join(missing)


def test_r3_seal_is_subjects_only() -> None:
    seal = (R3 / "evidence/SEAL.json").read_text(encoding="utf-8")
    assert '"run_id": "MKB-0815-R3"' in seal
    assert '"status": "subjects-sealed"' in seal
    assert '"token"' not in seal.split("conclusions")[-1] or '"unsealed"' in seal


def test_r3_collect_refuses_to_launch() -> None:
    text = (R3 / "collect.py").read_text(encoding="utf-8")
    assert "return 2" in text
    assert "--suffix -r3 --no-extras --rerun" in text
    assert "ingest_cell" not in text
