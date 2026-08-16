"""NS4-T29: Turso fail-path evidence is readable from the ReadPort."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts.observability.stage_report import validate_stage_report
from src.persistence.factory import build_persistence
from src.runtime.intake.generation_evidence import (
    record_pending_generation_evidence,
    take_pending_generation_evidence,
    write_pending_generation_evidence_tx,
)
from src.services.observability import ObservabilityReadService


@pytest.mark.asyncio
async def test_fail_path_report_is_queryable_on_turso(tmp_path: Path) -> None:
    take_pending_generation_evidence()
    persistence = build_persistence(
        tmp_path / "fail.db",
        Path("src/persistence/migrations"),
        backend="turso",
        concurrent_writes_required=False,
        native_vector_required=False,
    )
    try:
        await persistence.migrate()
        record_pending_generation_evidence(
            invocation={
                "invocation_uuid": "00000000-0000-4000-8000-0000000000aa",
                "status": "failed",
                "stage_key": "structurize",
                "error_code": "CLAUDE_CLI_OUTPUT_INVALID",
                "adapter_kind": "claude_cli",
                "cli_structured_kind": "list",
                "input_digest": "b" * 64,
                "process_attempt": 1,
                "invocation_ordinal": 0,
            },
            report=validate_stage_report(
                {
                    "stage_key": "structurize",
                    "disposition": "transport_failed",
                    "error_code": "CLAUDE_CLI_OUTPUT_INVALID",
                    "cli_structured_kind": "list",
                    "latency_ms": 3,
                }
            ),
        )
        process = {
            "team_uuid": "00000000-0000-4000-8000-000000000001",
            "execution_uuid": "00000000-0000-4000-8000-000000000002",
            "process_uuid": "00000000-0000-4000-8000-000000000003",
            "task_uuid": "00000000-0000-4000-8000-000000000004",
            "trace_uuid": "00000000-0000-4000-8000-000000000005",
        }
        async with persistence.transaction() as tx:
            try:
                await tx.execute("PRAGMA foreign_keys=OFF")
            except Exception:
                pass
            await write_pending_generation_evidence_tx(tx, process)
        port = ObservabilityReadService(persistence)
        evidence = await port._generation_evidence(process["team_uuid"], [process["process_uuid"]])
        assert evidence[process["process_uuid"]]["invocations"][0]["status"] == "failed"
        assert evidence[process["process_uuid"]]["reports"][0]["cli_structured_kind"] == "list"
    finally:
        await persistence.close()
