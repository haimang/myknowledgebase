"""R4 preflight kit: method, protocol, subjects, and owner gate files exist."""

from __future__ import annotations

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
R4 = REPOSITORY_ROOT / ".experiment/0815/runs/MKB-0815-R4"
REQUIRED = (
    R4 / "RUN.md",
    R4 / "preflight.py",
    R4 / "collect.py",
    R4 / "retrieve.py",
    R4 / "r4_prepare.py",
    R4 / "protocol/R4-ledger.md",
    R4 / "subjects/manifest.json",
    R4 / "evidence/SUBJECTS.md5",
    R4 / "evidence/PROTOCOL.md5",
    R4 / "evidence/METHOD.md5",
    R4 / "evidence/SEAL.json",
)


def test_r4_kit_files_exist() -> None:
    missing = [str(path.relative_to(REPOSITORY_ROOT)) for path in REQUIRED if not path.is_file()]
    assert missing == [], "R4 preflight kit incomplete:\n" + "\n".join(missing)


def test_r4_seal_is_subjects_only() -> None:
    seal = (R4 / "evidence/SEAL.json").read_text(encoding="utf-8")
    assert '"run_id": "MKB-0815-R4"' in seal
    assert '"status": "subjects-sealed"' in seal
    assert '"unsealed"' in seal


def test_r4_collect_refuses_to_launch() -> None:
    text = (R4 / "collect.py").read_text(encoding="utf-8")
    assert "return 2" in text
    assert "--suffix=-r4 --no-extras --rerun" in text
    assert "ingest_cell" not in text
