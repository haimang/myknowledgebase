"""NS4-T05 / T10: 0815 R2 production entrypoints no longer waive sqlite."""

from __future__ import annotations

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
R2 = REPOSITORY_ROOT / ".experiment/0815/runs/MKB-0815-R2"
WATCH = (
    R2 / "runner.py",
    R2 / "collect.py",
    R2 / "retrieve.py",
    R2 / "r3_prepare.py",
)


def test_r2_entrypoints_do_not_override_sqlite_or_disable_cw() -> None:
    hits: list[str] = []
    for path in WATCH:
        text = path.read_text(encoding="utf-8")
        if 'persistence_backend="sqlite"' in text or "persistence_backend='sqlite'" in text:
            hits.append(f"{path.name}: sqlite backend")
        if "concurrent_writes_required=False" in text:
            hits.append(f"{path.name}: CW waiver")
        if "SqlitePersistence" in text:
            hits.append(f"{path.name}: SqlitePersistence")
        if 'runtime" / "mkb.db"' in text or "runtime / mkb.db" in text:
            # archive path may be mentioned as source; production dest must be turso
            if "mkb.turso.db" not in text and path.name != "inspect_dump.py":
                hits.append(f"{path.name}: still opens mkb.db as dest")
    assert hits == [], "0815 still has sqlite waiver:\n" + "\n".join(hits)


def test_r2_runner_points_at_turso_file() -> None:
    text = (R2 / "runner.py").read_text(encoding="utf-8")
    assert "mkb.turso.db" in text
    assert 'persistence_backend="turso"' in text
    assert "concurrent_writes_required=True" in text
