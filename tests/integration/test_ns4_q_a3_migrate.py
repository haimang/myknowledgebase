"""NS4-T09: one-shot Q-A3 copy onto Turso does not invent reports."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "ns4_migrate_q_a3.py"
_SPEC = importlib.util.spec_from_file_location("ns4_migrate_q_a3", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MIGRATE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MIGRATE)
Q_A3_TASK = _MIGRATE.Q_A3_TASK
migrate = _MIGRATE.migrate

SOURCE = Path(".experiment/0815/runs/MKB-0815-R2/runtime/mkb.db")


@pytest.mark.skipif(not SOURCE.is_file(), reason="R2 archive db is not present")
def test_migrate_copies_seventeen_vectors_and_no_stage_reports(tmp_path: Path) -> None:
    dest = tmp_path / "mkb.turso.db"
    report = migrate(SOURCE, dest)
    assert report["vector_records"] == 17
    assert report["vector_facets"] == 17
    assert report["stage_reports"] == 0
    assert dest.is_file()
    assert Path(str(report["dest"])) == dest

    import turso

    connection = turso.connect(str(dest))
    try:
        status = connection.execute(
            "SELECT status FROM mkb_tasks WHERE task_uuid=?",
            (Q_A3_TASK,),
        ).fetchone()
        assert status is not None
        assert status[0] == "succeeded"
    finally:
        connection.close()


def test_migrate_refuses_in_place_source(tmp_path: Path) -> None:
    if not SOURCE.is_file():
        pytest.skip("R2 archive db is not present")
    with pytest.raises(ValueError, match="new Turso path"):
        migrate(SOURCE, SOURCE)
