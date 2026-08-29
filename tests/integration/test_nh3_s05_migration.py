"""NH3-T06: legacy policy aliases and new actual S05 states are distinguishable."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.runtime.binding.actual_s05 import projected_actual_digest
from tests.integration.test_nh2_selected_output_control import _seed


async def _execution(
    persistence,
    identity,
    ids: dict[str, str],
    *,
    name: str,
    state: str,
    actual_digest: str | None,
) -> str:
    execution_uuid = uuid7()
    now = utc_now()
    domain = stable_digest({"domain": name})
    route = stable_digest({"route": name}) if state == "sealed" else None
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_executions(execution_uuid,team_uuid,task_uuid,trace_uuid,generation,root_execution_uuid,"
            "execution_role,target_kind,workflow_uuid,workflow_revision_uuid,compiled_digest,resolver_decision_digest,"
            "domain_binding_digest,s05_binding_digest,actual_binding_digest,actual_binding_state,seal_generation,"
            "actual_selected_route_digest,actual_clean_step_key,actual_clean_process_key,actual_clean_strategy,"
            "config_snapshot_ref,config_snapshot_digest,status,manifest_ref,manifest_digest,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,'root','task',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                execution_uuid,
                ids["team_uuid"],
                ids["task_uuid"],
                ids["trace_uuid"],
                2 if name == "unsealed" else 3,
                execution_uuid,
                identity.workflow_uuid,
                identity.workflow_revision_uuid,
                identity.compiled_digest,
                stable_digest({"resolver": name}),
                domain,
                domain,
                actual_digest,
                state,
                1 if state == "sealed" else 0,
                route,
                "clean_deterministic" if state == "sealed" else None,
                "clean.extract.deterministic" if state == "sealed" else None,
                "doc.deterministic" if state == "sealed" else None,
                f"mkbtest:config:{name}",
                stable_digest({"config": name}),
                "ready",
                f"mkbtest:manifest:{name}",
                stable_digest({"manifest": name}),
                now,
                now,
            ),
        )
    return execution_uuid


@pytest.mark.asyncio
async def test_legacy_unsealed_sealed_sql_distinguishable(tmp_path: Path) -> None:
    persistence, _, _, identity, ids = await _seed(tmp_path, "s05-migration")
    sealed_actual = stable_digest({"actual": "sealed-path"})
    try:
        unsealed_uuid = await _execution(
            persistence,
            identity,
            ids,
            name="unsealed",
            state="unsealed",
            actual_digest=None,
        )
        sealed_uuid = await _execution(
            persistence,
            identity,
            ids,
            name="sealed",
            state="sealed",
            actual_digest=sealed_actual,
        )
        async with persistence.transaction() as tx:
            rows = await tx.fetchall(
                "SELECT execution_uuid,domain_binding_digest,"
                "s05_binding_digest AS legacy_policy_alias_digest,actual_binding_digest,actual_binding_state,"
                "seal_generation FROM mkb_executions ORDER BY generation"
            )
        assert [row["actual_binding_state"] for row in rows] == [
            "legacy_unverifiable",
            "unsealed",
            "sealed",
        ]
        legacy, unsealed, sealed = rows
        assert legacy["actual_binding_digest"] is None
        assert len(legacy["legacy_policy_alias_digest"]) == 64
        assert legacy["legacy_policy_alias_digest"] != sealed_actual
        assert projected_actual_digest(legacy) is None
        assert unsealed["execution_uuid"] == unsealed_uuid
        assert unsealed["actual_binding_digest"] is None and unsealed["seal_generation"] == 0
        assert sealed["execution_uuid"] == sealed_uuid
        assert projected_actual_digest(sealed) == sealed_actual
        assert sealed_actual != sealed["domain_binding_digest"]
    finally:
        await persistence.close()


def test_migration_does_not_copy_domain_into_actual() -> None:
    migration = (
        Path(__file__).resolve().parents[2]
        / "src/persistence/migrations/020_nh3_actual_s05_binding.sql"
    ).read_text(encoding="utf-8")
    normalized = " ".join(migration.casefold().split())
    assert "update mkb_executions" not in normalized
    assert "actual_binding_digest=s05_binding_digest" not in normalized
    assert "actual_binding_digest=domain_binding_digest" not in normalized


@pytest.mark.asyncio
async def test_new_create_does_not_write_domain_as_actual(tmp_path: Path) -> None:
    from tests.unit.test_nh3_lineage_matrix import _request, _task_service

    persistence, service, team_uuid = await _task_service(tmp_path)
    request = _request(team_uuid, intent="intake.ingest")
    try:
        await service.create(request, "token-fingerprint")
        async with persistence.transaction() as tx:
            row = await tx.fetchone(
                "SELECT domain_binding_digest,s05_binding_digest AS legacy_policy_alias_digest,"
                "actual_binding_digest,actual_binding_state,seal_generation FROM mkb_executions "
                "WHERE team_uuid=? AND task_uuid=?",
                (team_uuid, request.task_uuid),
            )
        assert row is not None
        assert row["actual_binding_digest"] is None
        assert row["actual_binding_state"] == "unsealed"
        assert row["seal_generation"] == 0
        assert row["legacy_policy_alias_digest"] == row["domain_binding_digest"]
    finally:
        await persistence.close()
