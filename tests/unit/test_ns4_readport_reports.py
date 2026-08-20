"""NS4-T24 / NS6-T33: ReadPort actually queries generation evidence tables."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.persistence.sqlite_port import SqlitePersistence
from src.services.observability import ObservabilityReadService


@pytest.mark.asyncio
async def test_generation_evidence_bundle_shape(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "obs.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    team = uuid7()
    process = uuid7()
    execution = uuid7()
    now = utc_now()
    persistence._connect().execute("PRAGMA foreign_keys = OFF")
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_teams(team_uuid,name,creation_fingerprint,created_at,updated_at) VALUES (?,?,?,?,?)",
            (team, "obs", "a" * 64, now, now),
        )
        await tx.execute(
            "INSERT INTO mkb_generation_invocations "
            "(invocation_uuid,team_uuid,execution_uuid,process_uuid,process_attempt,invocation_ordinal,"
            "invocation_kind,input_digest,occurred_at,status,stage_key,error_code,adapter_kind) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                uuid7(),
                team,
                execution,
                process,
                1,
                0,
                "generation",
                "b" * 64,
                now,
                "failed",
                "structurize",
                "x",
                "local_vllm",
            ),
        )
    service = ObservabilityReadService(persistence)
    bundle = await service._generation_evidence(team, [process])
    assert bundle[process]["invocations"][0]["status"] == "failed"
    await persistence.close()
