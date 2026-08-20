"""NS5-T02: sidecar 4×20 inserts must not abort; serial single-connection writer."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.persistence.factory import build_persistence
from src.persistence.turso.sidecar import TursoDiagnosticSidecar


def _params(index: int) -> tuple[object, ...]:
    return (
        uuid7(),
        None,
        None,
        None,
        None,
        None,
        "error",
        "GEN_STAGE_TIMING",
        f"timing-{index}",
        "runtime.intake.generation",
        "mkb-leaf",
        "{}",
        "a" * 64,
        utc_now(),
    )


@pytest.mark.asyncio
async def test_sidecar_threadpool_inserts_survive(tmp_path: Path) -> None:
    db_path = tmp_path / "sidecar.db"
    persistence = build_persistence(
        db_path,
        Path("src/persistence/migrations"),
        backend="turso",
        concurrent_writes_required=False,
        native_vector_required=False,
    )
    try:
        await persistence.migrate()
        ready = await persistence.readiness()
        assert ready["db_primary"] is True
        async with persistence.transaction() as tx:
            begin = await tx.fetchone("SELECT 1 AS ok")
        assert begin == {"ok": 1}
    finally:
        await persistence.close()

    sidecar = TursoDiagnosticSidecar(db_path)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda index: sidecar.insert(_params(index)), range(80)))

    persistence = build_persistence(
        db_path,
        Path("src/persistence/migrations"),
        backend="turso",
        concurrent_writes_required=False,
        native_vector_required=False,
    )
    try:
        async with persistence.transaction() as tx:
            row = await tx.fetchone("SELECT COUNT(*) AS count FROM mkb_ops_diagnostic_logs")
        assert row == {"count": 80}
    finally:
        await persistence.close()


def test_sidecar_source_does_not_flip_journal_mode() -> None:
    source = Path("src/persistence/turso/sidecar.py").read_text(encoding="utf-8")
    assert 'connection.execute("BEGIN IMMEDIATE")' in source
    assert "PRAGMA journal_mode=mvcc" not in source
    assert 'connection.execute("BEGIN CONCURRENT")' not in source
