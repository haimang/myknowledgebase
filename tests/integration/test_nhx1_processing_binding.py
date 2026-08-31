"""NHX1-T10: ProcessingBinding is a 10+3 typed union, not an 11th strategy."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from intake.api.registry import REGISTERED_PROVIDER_OPERATIONS
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.contracts.governance import ProcessingBinding, ProcessingBindingFamily
from src.contracts.intake.strategies import CLEAN_STRATEGY_DEFINITIONS
from tests.local_runtime import local_mock_settings


def _wait(client: TestClient, team_uuid: str, task_uuid: str, headers: dict[str, str]) -> dict[str, object]:
    deadline = time.monotonic() + 35
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
        assert response.status_code == 200, response.text
        latest = response.json()
        if latest["status"] in {"succeeded", "failed", "cancelled"}:
            return latest
        time.sleep(0.02)
    raise AssertionError(latest)


def test_registry_union_keeps_ten_clean_and_three_provider_cells() -> None:
    assert len(CLEAN_STRATEGY_DEFINITIONS) == 10
    assert len(REGISTERED_PROVIDER_OPERATIONS) == 3
    bindings = [
        ProcessingBinding(
            family=ProcessingBindingFamily.CLEAN_STRATEGY,
            key=definition.strategy_key.value,
            definition_version=definition.definition_version,
            definition_digest=definition.definition_digest,
        )
        for definition in CLEAN_STRATEGY_DEFINITIONS
    ]
    bindings.extend(
        ProcessingBinding(
            family=ProcessingBindingFamily.REGISTERED_API_OPERATION,
            key=f"{definition.provider}.{definition.operation}",
            definition_version=definition.definition_version,
            definition_digest=definition.definition_digest,
        )
        for definition in REGISTERED_PROVIDER_OPERATIONS
    )
    assert len(bindings) == 13
    assert len({binding.definition_digest for binding in bindings}) == 13


def test_production_seal_writes_typed_binding_and_fact_digest(tmp_path: Path) -> None:
    token = "nhx1-binding-token"
    headers = {"Authorization": f"Bearer {token}"}
    settings = local_mock_settings(
        database_path=tmp_path / "mkb.sqlite3",
        object_root=tmp_path / "objects",
        internal_token=token,
        inference_probe_enabled=False,
        live_inference=False,
        rate_limit_ip_per_min=10_000,
        rate_limit_token_per_min=20_000,
    )
    app = create_app(settings)
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        assert client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "binding"},
        ).status_code == 201
        response = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": task_uuid,
                "trace_uuid": trace_uuid,
                "request_intent": "intake.ingest",
                "payload": {
                    "json_prompt_id": "promptB.json.generic",
                    "source": {
                        "source_kind": "inline_payload",
                        "realm": "documentation",
                        "type": "article",
                        "channel": "general",
                        "source_name": "binding",
                        "external_key": "binding-source",
                        "content": "typed binding evidence",
                    },
                },
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": task_uuid,
                    "trace_uuid": trace_uuid,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "nhx1",
                    "created_at": utc_now(),
                },
            },
        )
        assert response.status_code == 201, response.text
        assert _wait(client, team_uuid, task_uuid, headers)["status"] == "succeeded"

        async def inspect() -> dict[str, object]:
            async with app.state.container.persistence.read_snapshot() as tx:
                binding = await tx.fetchone(
                    "SELECT binding_family,binding_key,definition_version,definition_digest,selected_process_key "
                    "FROM mkb_processing_binding_assertions WHERE team_uuid=?",
                    (team_uuid,),
                )
                selection = await tx.fetchone(
                    "SELECT representation_fact_uuid,representation_fact_digest,output_manifest_digest "
                    "FROM mkb_selection_assertions_v2 WHERE team_uuid=?",
                    (team_uuid,),
                )
            return {"binding": binding, "selection": selection}

        observed = client.portal.call(inspect)
        assert observed["binding"]["binding_family"] == "clean_strategy"
        assert observed["binding"]["binding_key"] in {definition.strategy_key.value for definition in CLEAN_STRATEGY_DEFINITIONS}
        assert len(observed["binding"]["definition_digest"]) == 64
        assert observed["selection"] is not None
        assert observed["selection"]["representation_fact_uuid"]
        assert observed["selection"]["representation_fact_digest"] != observed["selection"]["output_manifest_digest"]
