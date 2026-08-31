"""NHX1-T04: Source identity and Observation reservation semantics."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.api.models import (
    HttpSourceDescriptor,
    InlineSourceDescriptor,
    LocalObjectSourceDescriptor,
    RegisteredApiSourceDescriptor,
    TaskCreateRequest,
)
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.services.observation_reservations import ObservationReservationService
from tests.local_runtime import local_mock_settings


def _request(source, task_uuid: str) -> TaskCreateRequest:
    trace_uuid = uuid7()
    return TaskCreateRequest(
        schema_version="mkb.task.v1",
        team_uuid="01900000-0000-7000-8000-000000000001",
        task_uuid=task_uuid,
        trace_uuid=trace_uuid,
        request_intent="intake.ingest",
        payload={"json_prompt_id": "promptB.json.generic", "source": source},
        audit={
            "schema_version": "mkb.task-audit.v1",
            "team_uuid": "01900000-0000-7000-8000-000000000001",
            "task_uuid": task_uuid,
            "trace_uuid": trace_uuid,
            "audit_type": "business_review",
            "audit_status": "not_required",
            "source": "nhx1",
            "created_at": utc_now(),
        },
    )


def test_four_source_kinds_have_explicit_or_compat_observation_coordinates() -> None:
    sources = (
        InlineSourceDescriptor(
            source_kind="inline_payload",
            realm="documentation",
            type="article",
            channel="general",
            source_name="fixture",
            external_key="inline-key",
            content="inline body",
        ),
        LocalObjectSourceDescriptor(
            source_kind="local_object",
            realm="documentation",
            type="article",
            channel="general",
            source_name="fixture",
            external_key="local-key",
            logical_handle="mkbobj:v1:01900000-0000-7000-8000-000000000001:" + "a" * 64,
        ),
        HttpSourceDescriptor(
            source_kind="http_resource",
            realm="documentation",
            type="article",
            channel="general",
            source_name="fixture",
            external_key="http-key",
            url="https://example.com/article",
        ),
        RegisteredApiSourceDescriptor(
            source_kind="registered_api",
            external_key="api-key",
            connector_key="chinatax.get_articles",
            provider="chinatax",
            operation="get_articles",
            definition_version="v1",
            records=[
                {
                    "id": "article-1",
                    "label": "fixture",
                    "column": "policy",
                    "title": "title",
                    "content": "body",
                    "xxgk_aging": "有效",
                }
            ],
            exhaustion_proof="caller_frozen_records.v1",
        ),
    )
    service = ObservationReservationService()
    task_ids = [uuid7() for _ in sources]
    coordinates = [
        service.observation_coordinates(_request(source, task_uuid))
        for source, task_uuid in zip(sources, task_ids, strict=True)
    ]
    assert [row[0] for row in coordinates] == [
        "inline_payload",
        "local_object",
        "http_resource",
        "registered_api",
    ]
    assert [row[2] for row in coordinates[:3]] == [
        task_ids[0],
        task_ids[1],
        task_ids[2],
    ]
    assert coordinates[3][2] == "api-key"
    assert all(len(row[3]) == 64 for row in coordinates)


def _inline_payload(team_uuid: str, task_uuid: str, *, content: str, observation_key: str) -> dict[str, object]:
    trace_uuid = uuid7()
    return {
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
                "source_name": "nhx1-observation",
                "external_key": "same-source",
                "observation_key": observation_key,
                "content": content,
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
    }


def _wait(client: TestClient, team_uuid: str, task_uuid: str, headers: dict[str, str]) -> dict[str, object]:
    deadline = time.monotonic() + 30
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
        assert response.status_code == 200, response.text
        latest = response.json()
        if latest["status"] in {"succeeded", "failed", "cancelled"}:
            return latest
        time.sleep(0.02)
    raise AssertionError(latest)


def test_observation_reservation_replay_conflict_and_new_observation(tmp_path: Path) -> None:
    team_uuid = uuid7()
    token = "nhx1-observation-token"
    headers = {"Authorization": f"Bearer {token}"}
    app = create_app(
        local_mock_settings(
            database_path=tmp_path / "mkb.sqlite3",
            object_root=tmp_path / "objects",
            internal_token=token,
            inference_probe_enabled=False,
            live_inference=False,
        )
    )
    first_uuid, replay_uuid, conflict_uuid, second_observation_uuid = (uuid7() for _ in range(4))
    with TestClient(app, raise_server_exceptions=True) as client:
        assert client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nhx1"},
        ).status_code == 201
        first = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_inline_payload(team_uuid, first_uuid, content="same bytes", observation_key="observation-a"),
        )
        assert first.status_code == 201, first.text
        replay = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_inline_payload(team_uuid, replay_uuid, content="same bytes", observation_key="observation-a"),
        )
        assert replay.status_code == 200, replay.text
        assert replay.json()["task_uuid"] == first_uuid
        conflict = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_inline_payload(team_uuid, conflict_uuid, content="different bytes", observation_key="observation-a"),
        )
        assert conflict.status_code == 409, conflict.text
        assert conflict.json()["error"]["code"] == "OBSERVATION_CONFLICT"
        second = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_inline_payload(team_uuid, second_observation_uuid, content="same bytes", observation_key="observation-b"),
        )
        assert second.status_code == 201, second.text
        assert _wait(client, team_uuid, first_uuid, headers)["status"] == "succeeded"
        assert _wait(client, team_uuid, second_observation_uuid, headers)["status"] == "succeeded"

        async def inspect() -> dict[str, object]:
            async with app.state.container.persistence.read_snapshot() as tx:
                rows = await tx.fetchall(
                    "SELECT observation_key,state,owner_task_uuid FROM mkb_intake_observations "
                    "WHERE team_uuid=? ORDER BY observation_key",
                    (team_uuid,),
                )
                snapshots = await tx.fetchone(
                    "SELECT COUNT(*) AS count FROM mkb_intake_snapshots WHERE team_uuid=?", (team_uuid,)
                )
                tasks = await tx.fetchone("SELECT COUNT(*) AS count FROM mkb_tasks WHERE team_uuid=?", (team_uuid,))
            return {"observations": rows, "snapshots": snapshots["count"], "tasks": tasks["count"]}

        state = client.portal.call(inspect)
        assert [row["observation_key"] for row in state["observations"]] == ["observation-a", "observation-b"]
        assert all(row["state"] == "accepted" for row in state["observations"])
        # first Task + second-observation Task; replay/conflict create no Task.
        assert state["tasks"] == 2
        assert state["snapshots"] == 2


def test_concurrent_same_observation_has_one_task_winner(tmp_path: Path) -> None:
    team_uuid = uuid7()
    token = "nhx1-observation-race-token"
    headers = {"Authorization": f"Bearer {token}"}
    app = create_app(
        local_mock_settings(
            database_path=tmp_path / "mkb.sqlite3",
            object_root=tmp_path / "objects",
            internal_token=token,
            inference_probe_enabled=False,
            live_inference=False,
        )
    )
    task_ids = [uuid7(), uuid7()]
    with TestClient(app, raise_server_exceptions=True) as client:
        assert client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "race"},
        ).status_code == 201

        def submit(task_uuid: str):
            return client.post(
                f"/v1/teams/{team_uuid}/tasks",
                headers=headers,
                json=_inline_payload(team_uuid, task_uuid, content="same concurrent bytes", observation_key="race-key"),
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(submit, task_ids))
        assert sorted(response.status_code for response in responses) == [200, 201]

        async def inspect() -> dict[str, int]:
            async with app.state.container.persistence.read_snapshot() as tx:
                observation = await tx.fetchone(
                    "SELECT COUNT(*) AS count FROM mkb_intake_observations WHERE team_uuid=? AND observation_key=?",
                    (team_uuid, "race-key"),
                )
                tasks = await tx.fetchone("SELECT COUNT(*) AS count FROM mkb_tasks WHERE team_uuid=?", (team_uuid,))
            return {"observations": observation["count"], "tasks": tasks["count"]}

        assert client.portal.call(inspect) == {"observations": 1, "tasks": 1}
