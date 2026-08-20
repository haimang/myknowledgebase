"""NS5-T06: deactivated-item retirement intents must not occupy the due queue."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from src.contracts.common.ids import uuid7
from src.persistence.sqlite_port import SqlitePersistence
from src.services.index_retirement import (
    RETIREMENT_POLICY_REF,
    RETIREMENT_TARGET_KIND,
    IndexGenerationRetirementDisposition,
    IndexGenerationRetirementService,
)
from tests.unit.test_index_generation_retirement import (
    CUTOVER,
    ITEM,
    NAMESPACE,
    TEAM,
    MutableClock,
    _seed_retired_generation,
    _timestamp,
)


@pytest.mark.asyncio
async def test_stuck_intents_yield_to_healthy_item(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "stuck-retirement.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    await _seed_retired_generation(persistence)
    clock = MutableClock(CUTOVER + timedelta(hours=2))
    now = _timestamp(clock.now)
    connection = persistence._connect()
    connection.execute("PRAGMA foreign_keys = OFF")
    connection.execute(
        "UPDATE mkb_intake_items SET lifecycle_state='deactivated', serving_revision_uuid=NULL WHERE intake_item_uuid=?",
        (ITEM,),
    )
    digest = "b" * 64
    for index in range(100):
        intent_uuid = uuid7()
        target = f"index-generation:v1:{ITEM}:{NAMESPACE}:{index + 10}"
        connection.execute(
            "INSERT INTO mkb_intake_cleanup_intents "
            "(intent_uuid,team_uuid,policy_ref,target_kind,target_ref,required_substrate_set_digest,hold_refs_json,"
            "status,requested_at,eligible_at,payload_extra) VALUES (?,?,?,?,?,?, '[]','open',?,?, '{}')",
            (intent_uuid, TEAM, RETIREMENT_POLICY_REF, RETIREMENT_TARGET_KIND, target, digest, now, now),
        )
    healthy_item = "123e4567-e89b-42d3-a456-426614174099"
    healthy_intent = uuid7()
    connection.execute(
        "INSERT INTO mkb_intake_items "
        "(team_uuid,intake_item_uuid,intake_source_uuid,normalized_external_key,lifecycle_state,"
        "latest_revision_uuid,serving_revision_uuid,row_revision,created_at,updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            TEAM,
            healthy_item,
            "123e4567-e89b-42d3-a456-426614174006",
            "healthy",
            "active",
            "123e4567-e89b-42d3-a456-426614174003",
            "123e4567-e89b-42d3-a456-426614174003",
            0,
            now,
            now,
        ),
    )
    connection.execute(
        "INSERT INTO mkb_index_active_pointers "
        "(team_uuid,intake_item_uuid,namespace_uuid,active_index_generation,pointer_row_revision,lifecycle_state,"
        "updated_at) VALUES (?,?,?,?,?,?,?)",
        (TEAM, healthy_item, NAMESPACE, 2, 1, "active", now),
    )
    connection.execute(
        "INSERT INTO mkb_intake_cleanup_intents "
        "(intent_uuid,team_uuid,policy_ref,target_kind,target_ref,required_substrate_set_digest,hold_refs_json,"
        "status,requested_at,eligible_at,payload_extra) VALUES (?,?,?,?,?,?, '[]','open',?,?, '{}')",
        (
            healthy_intent,
            TEAM,
            RETIREMENT_POLICY_REF,
            RETIREMENT_TARGET_KIND,
            f"index-generation:v1:{healthy_item}:{NAMESPACE}:1",
            "c" * 64,
            now,
            now,
        ),
    )
    connection.commit()

    service = IndexGenerationRetirementService(persistence, grace=timedelta(hours=1), clock=clock)
    first = await service.scan_once(limit=100)
    assert any(result.disposition is IndexGenerationRetirementDisposition.ABANDONED for result in first.results)
    second = await service.scan_once(limit=100)
    intent_ids = {result.intent_uuid for result in second.results}
    due = await service.collect_due(limit=100)
    due_ids = {item.intent_uuid for item in due}
    assert healthy_intent in intent_ids or healthy_intent in due_ids
    await persistence.close()
