"""R3 live Turso copy must already carry 013, Q-A3, and g1 v3 — no -r3 ingest."""

from __future__ import annotations

from pathlib import Path

import pytest

Q_A3_TASK = "01a00887-3cef-7379-92ea-3a6a38fd4188"
TURSO = Path(".experiment/0815/runs/MKB-0815-R2/runtime/mkb.turso.db")


@pytest.mark.skipif(not TURSO.is_file(), reason="R2 Turso copy is not present")
def test_live_turso_is_r3_ready() -> None:
    import turso

    connection = turso.connect(str(TURSO))
    try:
        migs = {
            row[0]
            for row in connection.execute("SELECT migration_id FROM mkb_schema_migrations").fetchall()
        }
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        vectors = connection.execute("SELECT COUNT(*) FROM mkb_vector_records").fetchone()[0]
        facets = connection.execute("SELECT COUNT(*) FROM mkb_vector_record_facets").fetchone()[0]
        task = connection.execute("SELECT status FROM mkb_tasks WHERE task_uuid=?", (Q_A3_TASK,)).fetchone()
        g1 = connection.execute(
            "SELECT prompt_version FROM mkb_prompt_hash_pointers "
            "WHERE prompt_id='promptB.documentation.g1' AND status='active'"
        ).fetchone()
        q_a3_vectors = connection.execute(
            "SELECT COUNT(*) FROM mkb_vector_records WHERE task_uuid=?",
            (Q_A3_TASK,),
        ).fetchone()[0]
        mapped = connection.execute(
            "SELECT COUNT(*) FROM mkb_generation_invocations WHERE stage_key='transcribe_markdown'"
        ).fetchone()[0]
        markdown = connection.execute(
            "SELECT COUNT(*) FROM mkb_generation_invocations WHERE stage_key='markdown'"
        ).fetchone()[0]
    finally:
        connection.close()
    assert "013_generation_evidence_plane" in migs
    assert "mkb_generation_stage_reports" in tables
    assert int(vectors) >= 17
    assert int(facets) >= 17
    assert int(q_a3_vectors) == 17
    assert task is not None and task[0] == "succeeded"
    assert g1 is not None and g1[0] == "v3"
    assert int(mapped) == 0
    assert int(markdown) >= 1
