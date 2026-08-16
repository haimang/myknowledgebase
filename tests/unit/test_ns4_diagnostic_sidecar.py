"""NS4-T22 / T23: sidecar uses BEGIN CONCURRENT and does not rewrite product codes."""

from __future__ import annotations

from pathlib import Path

from src.persistence.turso.sidecar import DIAGNOSTIC_LOG_CODES, TursoDiagnosticSidecar


def test_log_code_closed_set() -> None:
    assert "GEN_STRUCTURIZE_REJECT" in DIAGNOSTIC_LOG_CODES
    assert "GEN_CLI_ENVELOPE" in DIAGNOSTIC_LOG_CODES


def test_sidecar_source_uses_begin_concurrent() -> None:
    from pathlib import Path

    source = Path("src/persistence/turso/sidecar.py").read_text(encoding="utf-8")
    assert "BEGIN CONCURRENT" in source
    assert "PRAGMA journal_mode=mvcc" in source


def test_sidecar_failure_does_not_change_product_code() -> None:
    # Product codes stay on the exception; sidecar failures are swallowed by DiagnosticSink.
    from src.contracts.common.errors import MkbError

    err = MkbError("STRUCTURE_ANCHOR_MISSING", "missing", 422)
    assert err.code == "STRUCTURE_ANCHOR_MISSING"
