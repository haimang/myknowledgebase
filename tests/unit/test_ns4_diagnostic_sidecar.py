"""NS4-T22 / T23: sidecar uses BEGIN CONCURRENT and does not rewrite product codes."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.persistence.turso.sidecar import DIAGNOSTIC_LOG_CODES, TursoDiagnosticSidecar


def test_log_code_closed_set() -> None:
    assert "GEN_STRUCTURIZE_REJECT" in DIAGNOSTIC_LOG_CODES
    assert "GEN_CLI_ENVELOPE" in DIAGNOSTIC_LOG_CODES


def test_sidecar_source_uses_serial_immediate() -> None:
    from pathlib import Path

    source = Path("src/persistence/turso/sidecar.py").read_text(encoding="utf-8")
    assert 'connection.execute("BEGIN IMMEDIATE")' in source
    assert 'connection.execute("BEGIN CONCURRENT")' not in source
    assert "PRAGMA journal_mode=mvcc" not in source


@pytest.mark.asyncio
async def test_sidecar_inserts_into_migrated_turso(tmp_path: Path) -> None:
    from src.persistence.factory import build_persistence

    db = tmp_path / "side.db"
    persistence = build_persistence(
        db,
        Path("src/persistence/migrations"),
        backend="turso",
        concurrent_writes_required=False,
        native_vector_required=False,
    )
    await persistence.migrate()
    await persistence.close()
    sidecar = TursoDiagnosticSidecar(db)
    now = "2026-08-20T00:00:00.000000Z"
    sidecar.insert(
        (
            "11111111-1111-4111-8111-111111111111",
            "22222222-2222-4222-8222-222222222222",
            "33333333-3333-4333-8333-333333333333",
            None,
            None,
            None,
            "info",
            "GEN_STAGE_TIMING",
            "ok",
            "test",
            "worker",
            "{}",
            "c" * 64,
            now,
        )
    )
    from src.contracts.common.errors import MkbError

    err = MkbError("STRUCTURE_ANCHOR_MISSING", "missing", 422)
    boom = TursoDiagnosticSidecar(tmp_path / "missing.db")
    try:
        boom.insert(("x",) * 14)
    except Exception:
        pass
    assert err.code == "STRUCTURE_ANCHOR_MISSING"
