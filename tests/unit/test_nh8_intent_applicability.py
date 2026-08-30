"""NH8-T01: seven-intent applicability fails closed before Task insert."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.config import Settings

_TOKEN = "nh8-intent-token"
_HEADERS = {"Authorization": f"Bearer {_TOKEN}"}
_CLOSED_422 = {
    "task-schema-invalid",
    "workflow-intent-not-supported",
    "INTAKE_INTENT_UNSUPPORTED",
    "SOURCE_KIND_INVALID",
    "INTAKE_SEMANTIC_KEY_UNREGISTERED",
    "METADATA_SEMANTICS_EMPTY",
    "SCATTER_EXHAUSTION_PROOF_REQUIRED",
    "CLEAN_STRATEGY_KIND_INCOMPATIBLE",
    "METADATA_SEMANTIC_SYSTEM_OWNED",
}
_CLOSED_409 = {
    "intake-item-deleted",
    "index-rebuild-item-not-active",
    "intake-revision-unavailable",
    "intake-revision-mismatch",
    "METADATA_TARGET_STALE",
}


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        internal_token=_TOKEN,
        database_path=tmp_path / "mkb.sqlite3",
        object_root=tmp_path / "objects",
        inference_probe_enabled=False,
        live_inference=False,
        persistence_backend="turso",
        concurrent_writes_required=False,
        native_vector_required=False,
        rate_limit_ip_per_min=2_000,
        rate_limit_token_per_min=4_000,
    )


def _audit(team_uuid: str, task_uuid: str, trace_uuid: str) -> dict[str, object]:
    return {
        "schema_version": "mkb.task-audit.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "audit_type": "business_review",
        "audit_status": "not_required",
        "source": "nh8-t01",
        "created_at": utc_now(),
    }


def _counts(app, team_uuid: str, task_uuid: str, client: TestClient) -> tuple[int, int]:
    async def inspect() -> tuple[int, int]:
        async with app.state.container.persistence.transaction() as tx:
            tasks = await tx.fetchone(
                "SELECT COUNT(*) AS n FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
                (team_uuid, task_uuid),
            )
            processes = await tx.fetchone(
                "SELECT COUNT(*) AS n FROM mkb_processes WHERE team_uuid=? AND task_uuid=?",
                (team_uuid, task_uuid),
            )
        return int(tasks["n"]) if tasks is not None else -1, int(processes["n"]) if processes is not None else -1

    return client.portal.call(inspect)


def test_legal_ingest_creates_exactly_one_task(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=_HEADERS,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh8-intent"},
            ).status_code
            == 201
        )
        created = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=_HEADERS,
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
                        "external_key": "nh8-legal-ingest",
                        "content": "NH8 legal ingest cell",
                        "realm": "documentation",
                        "type": "article",
                        "channel": "general",
                        "source_name": "nh8-intent",
                    },
                },
                "audit": _audit(team_uuid, task_uuid, trace_uuid),
            },
        )
        assert created.status_code == 201, created.text
        assert _counts(app, team_uuid, task_uuid, client)[0] == 1


def test_illegal_cells_fail_before_task_insert(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=_HEADERS,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh8-illegal"},
            ).status_code
            == 201
        )
        cases = [
            ("eighth-intent", {"request_intent": "intake.upgrade"}, 422, "task-schema-invalid"),
            (
                "fifth-kind",
                {
                    "request_intent": "intake.ingest",
                    "payload": {
                        "json_prompt_id": "promptB.json.generic",
                        "source": {
                            "source_kind": "supplier_crawl",
                            "external_key": "x",
                            "realm": "documentation",
                            "type": "article",
                            "channel": "general",
                            "source_name": "nh8",
                        },
                    },
                },
                422,
                "task-schema-invalid",
            ),
            (
                "workflow-key",
                {
                    "request_intent": "intake.ingest",
                    "payload": {
                        "json_prompt_id": "promptB.json.generic",
                        "source": {
                            "source_kind": "inline_payload",
                            "external_key": "x",
                            "content": "x",
                            "realm": "documentation",
                            "type": "article",
                            "channel": "general",
                            "source_name": "nh8",
                        },
                    },
                    "workflow_key": "intake.ingest.kind.inline-payload.lsrag.v1",
                },
                422,
                "task-schema-invalid",
            ),
            (
                "rebuild-with-source",
                {
                    "request_intent": "intake.rebuild",
                    "payload": {
                        "source": {
                            "source_kind": "inline_payload",
                            "external_key": "x",
                            "content": "x",
                            "realm": "documentation",
                            "type": "article",
                            "channel": "general",
                            "source_name": "nh8",
                        }
                    },
                },
                422,
                "task-schema-invalid",
            ),
            (
                "ingest-with-item",
                {
                    "request_intent": "intake.ingest",
                    "payload": {"intake_item_uuid": uuid7()},
                },
                422,
                "task-schema-invalid",
            ),
            (
                "unregistered-semantic",
                {
                    "request_intent": "intake.update_metadata",
                    "payload": {"intake_item_uuid": uuid7(), "semantics": {"not_a_registered_key": "x"}},
                },
                422,
                "INTAKE_SEMANTIC_KEY_UNREGISTERED",
            ),
            (
                "empty-semantics",
                {
                    "request_intent": "intake.update_metadata",
                    "payload": {"intake_item_uuid": uuid7(), "semantics": {}},
                },
                422,
                "task-schema-invalid",
            ),
        ]
        for name, extra, status, code in cases:
            task_uuid, trace_uuid = uuid7(), uuid7()
            body = {
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": task_uuid,
                "trace_uuid": trace_uuid,
                "audit": _audit(team_uuid, task_uuid, trace_uuid),
                **extra,
            }
            response = client.post(f"/v1/teams/{team_uuid}/tasks", headers=_HEADERS, json=body)
            assert response.status_code == status, (name, response.text)
            assert response.json()["error"]["code"] == code, name
            if status == 422:
                assert code in _CLOSED_422
            tasks, processes = _counts(app, team_uuid, task_uuid, client)
            assert tasks == 0 and processes == 0, name


def _wait(client: TestClient, team_uuid: str, task_uuid: str) -> dict[str, object]:
    deadline = time.monotonic() + 30
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=_HEADERS)
        latest = response.json()
        if latest.get("status") in {"succeeded", "failed", "cancelled"}:
            return latest
        time.sleep(0.02)
    return latest


def test_deleted_and_inactive_fail_before_task_insert(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=_HEADERS,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh8-deleted"},
            ).status_code
            == 201
        )
        ingest_uuid, ingest_trace = uuid7(), uuid7()
        created = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=_HEADERS,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": ingest_uuid,
                "trace_uuid": ingest_trace,
                "request_intent": "intake.ingest",
                "payload": {
                    "json_prompt_id": "promptB.json.generic",
                    "source": {
                        "source_kind": "inline_payload",
                        "external_key": "nh8-deleted-item",
                        "content": "NH8 deleted item sentinel",
                        "realm": "documentation",
                        "type": "article",
                        "channel": "general",
                        "source_name": "nh8-deleted",
                    },
                },
                "audit": _audit(team_uuid, ingest_uuid, ingest_trace),
            },
        )
        assert created.status_code == 201, created.text
        assert _wait(client, team_uuid, ingest_uuid)["status"] == "succeeded"

        async def item_uuid() -> str:
            async with app.state.container.persistence.transaction() as tx:
                row = await tx.fetchone(
                    "SELECT intake_item_uuid FROM mkb_intake_items WHERE team_uuid=?",
                    (team_uuid,),
                )
            assert row is not None
            return str(row["intake_item_uuid"])

        target = client.portal.call(item_uuid)
        delete_uuid, delete_trace = uuid7(), uuid7()
        deleted = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=_HEADERS,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": delete_uuid,
                "trace_uuid": delete_trace,
                "request_intent": "intake.delete",
                "payload": {"intake_item_uuid": target},
                "audit": _audit(team_uuid, delete_uuid, delete_trace),
            },
        )
        assert deleted.status_code == 201, deleted.text
        assert _wait(client, team_uuid, delete_uuid)["status"] == "succeeded"
        rebuild_uuid, rebuild_trace = uuid7(), uuid7()
        rebuild = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=_HEADERS,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": rebuild_uuid,
                "trace_uuid": rebuild_trace,
                "request_intent": "intake.rebuild",
                "payload": {"intake_item_uuid": target},
                "audit": _audit(team_uuid, rebuild_uuid, rebuild_trace),
            },
        )
        assert rebuild.status_code == 409, rebuild.text
        assert rebuild.json()["error"]["code"] == "intake-item-deleted"
        assert rebuild.json()["error"]["code"] in _CLOSED_409
        assert _counts(app, team_uuid, rebuild_uuid, client) == (0, 0)
        for intent in ("intake.update_metadata", "intake.deactivate", "intake.reactivate"):
            extra_uuid, extra_trace = uuid7(), uuid7()
            payload: dict[str, object] = {"intake_item_uuid": target}
            if intent == "intake.update_metadata":
                payload["semantics"] = {"realm": "documentation"}
            extra = client.post(
                f"/v1/teams/{team_uuid}/tasks",
                headers=_HEADERS,
                json={
                    "schema_version": "mkb.task.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": extra_uuid,
                    "trace_uuid": extra_trace,
                    "request_intent": intent,
                    "payload": payload,
                    "audit": _audit(team_uuid, extra_uuid, extra_trace),
                },
            )
            assert extra.status_code == 409, (intent, extra.text)
            assert extra.json()["error"]["code"] == "intake-item-deleted"
            assert _counts(app, team_uuid, extra_uuid, client) == (0, 0)


def test_inactive_index_rebuild_fail_before_task_insert(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=_HEADERS,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh8-inactive"},
            ).status_code
            == 201
        )
        ingest_uuid, ingest_trace = uuid7(), uuid7()
        created = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=_HEADERS,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": ingest_uuid,
                "trace_uuid": ingest_trace,
                "request_intent": "intake.ingest",
                "payload": {
                    "json_prompt_id": "promptB.json.generic",
                    "source": {
                        "source_kind": "inline_payload",
                        "external_key": "nh8-inactive-item",
                        "content": "NH8 inactive item sentinel",
                        "realm": "documentation",
                        "type": "article",
                        "channel": "general",
                        "source_name": "nh8-inactive",
                    },
                },
                "audit": _audit(team_uuid, ingest_uuid, ingest_trace),
            },
        )
        assert created.status_code == 201, created.text
        assert _wait(client, team_uuid, ingest_uuid)["status"] == "succeeded"

        async def item_uuid() -> str:
            async with app.state.container.persistence.transaction() as tx:
                row = await tx.fetchone(
                    "SELECT intake_item_uuid FROM mkb_intake_items WHERE team_uuid=?",
                    (team_uuid,),
                )
            assert row is not None
            return str(row["intake_item_uuid"])

        target = client.portal.call(item_uuid)
        deactivate_uuid, deactivate_trace = uuid7(), uuid7()
        deactivated = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=_HEADERS,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": deactivate_uuid,
                "trace_uuid": deactivate_trace,
                "request_intent": "intake.deactivate",
                "payload": {"intake_item_uuid": target},
                "audit": _audit(team_uuid, deactivate_uuid, deactivate_trace),
            },
        )
        assert deactivated.status_code == 201, deactivated.text
        assert _wait(client, team_uuid, deactivate_uuid)["status"] == "succeeded"
        index_uuid, index_trace = uuid7(), uuid7()
        indexed = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=_HEADERS,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": index_uuid,
                "trace_uuid": index_trace,
                "request_intent": "index.rebuild",
                "payload": {"scope": "intake_item", "intake_item_uuid": target},
                "audit": _audit(team_uuid, index_uuid, index_trace),
            },
        )
        assert indexed.status_code == 409, indexed.text
        assert indexed.json()["error"]["code"] == "index-rebuild-item-not-active"
        assert _counts(app, team_uuid, index_uuid, client) == (0, 0)


def test_http_422_vs_409_code_closed_set() -> None:
    assert "task-schema-invalid" in _CLOSED_422
    assert "INTAKE_SEMANTIC_KEY_UNREGISTERED" in _CLOSED_422
    assert "METADATA_SEMANTICS_EMPTY" in _CLOSED_422
    assert "intake-item-deleted" in _CLOSED_409
    assert "index-rebuild-item-not-active" in _CLOSED_409
    assert "intake-revision-unavailable" in _CLOSED_409
    assert "intake-revision-mismatch" in _CLOSED_409
