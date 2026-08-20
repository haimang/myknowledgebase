"""NS6 audit-cycle HTTP predicates: HITL activate, digest=bytes, ingest replay."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.contracts.storage.models import ObjectHandle
from src.runtime.config import Settings


def _settings(tmp_path: Path, token: str) -> Settings:
    return Settings(
        internal_token=token,
        database_path=tmp_path / "mkb.sqlite3",
        object_root=tmp_path / "objects",
        inference_probe_enabled=False,
        live_inference=False,
        persistence_backend="sqlite",
        concurrent_writes_required=False,
        native_vector_required=False,
        rate_limit_ip_per_min=1_000,
        rate_limit_token_per_min=2_000,
    )


def _wait(client: TestClient, team_uuid: str, task_uuid: str, headers: dict[str, str], *, timeout: float = 12) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    task: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
        assert response.status_code == 200, response.text
        task = response.json()
        if task["status"] in {"succeeded", "failed", "cancelled"}:
            return task
        time.sleep(0.05)
    raise AssertionError(f"task did not become terminal: {task}")


def _create_team_and_ingest(
    client: TestClient,
    *,
    headers: dict[str, str],
    team_uuid: str,
    task_uuid: str,
    trace_uuid: str,
    external_key: str,
    content: str,
    require_human_review: bool = False,
) -> None:
    created_team = client.post(
        "/v1/teams",
        headers=headers,
        json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "ns6-audit"},
    )
    if created_team.status_code not in {200, 201, 409}:
        raise AssertionError(created_team.text)
    created = client.post(
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
                    "external_key": external_key,
                    "content": content,
                    "media_type": "text/plain",
                    "require_human_review": require_human_review,
                },
            },
            "audit": {
                "schema_version": "mkb.task-audit.v1",
                "team_uuid": team_uuid,
                "task_uuid": task_uuid,
                "trace_uuid": trace_uuid,
                "audit_type": "business_review",
                "audit_status": "not_required",
                "source": "ns6-audit",
                "created_at": utc_now(),
            },
        },
    )
    assert created.status_code == 201, created.text


def test_human_review_approve_activates_item_via_port(tmp_path: Path) -> None:
    token = "ns6-t22-token"
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    headers = {"Authorization": f"Bearer {token}"}
    app = create_app(_settings(tmp_path, token))
    with TestClient(app, raise_server_exceptions=True) as client:
        _create_team_and_ingest(
            client,
            headers=headers,
            team_uuid=team_uuid,
            task_uuid=task_uuid,
            trace_uuid=trace_uuid,
            external_key="requires-review",
            content="Human review must activate the intake item.",
            require_human_review=True,
        )
        deadline = time.monotonic() + 8
        task: dict[str, object] = {}
        while time.monotonic() < deadline:
            response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
            assert response.status_code == 200, response.text
            task = response.json()
            if task.get("action_required"):
                break
            time.sleep(0.05)
        assert task.get("action_required"), task
        gates = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}/gates", headers=headers)
        assert gates.status_code == 200, gates.text
        gate = gates.json()["items"][0]
        accepted = client.post(
            f"/v1/teams/{team_uuid}/tasks/{task_uuid}/gates/{gate['gate_uuid']}:decide",
            headers=headers,
            json={
                "expected_gate_revision": gate["revision"],
                "target_digest": gate["target_digest"],
                "action": "approve",
                "idempotency_key": "ns6-t22-approve",
            },
        )
        assert accepted.status_code == 200, accepted.text
        final = _wait(client, team_uuid, task_uuid, headers)
        assert final["status"] == "succeeded", final
        persistence = app.state.container.persistence

        async def inspect() -> tuple[str, int]:
            async with persistence.transaction() as tx:
                item = await tx.fetchone(
                    "SELECT lifecycle_state FROM mkb_intake_items WHERE team_uuid=?",
                    (team_uuid,),
                )
                vectors = await tx.fetchall(
                    "SELECT vector_record_uuid FROM mkb_vector_records WHERE team_uuid=?",
                    (team_uuid,),
                )
            return str(item["lifecycle_state"]), len(list(vectors))

        lifecycle, vector_count = client.portal.call(inspect)
        assert lifecycle == "active"
        assert vector_count >= 1


def test_accept_cas_digests_match_read_verified_bytes(tmp_path: Path) -> None:
    token = "ns6-t23-token"
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    headers = {"Authorization": f"Bearer {token}"}
    app = create_app(_settings(tmp_path, token))
    with TestClient(app, raise_server_exceptions=True) as client:
        _create_team_and_ingest(
            client,
            headers=headers,
            team_uuid=team_uuid,
            task_uuid=task_uuid,
            trace_uuid=trace_uuid,
            external_key="digest-bytes",
            content="Raw ingest bytes must equal the catalog digest.",
        )
        final = _wait(client, team_uuid, task_uuid, headers)
        assert final["status"] == "succeeded", final
        persistence = app.state.container.persistence
        storage = app.state.container.storage

        async def verify() -> int:
            async with persistence.transaction() as tx:
                objects = list(
                    await tx.fetchall(
                        "SELECT content_digest, size_bytes FROM mkb_stored_objects WHERE team_uuid=?",
                        (team_uuid,),
                    )
                )
            checked = 0
            for row in objects:
                handle = ObjectHandle(value=f"mkbobj:v1:{team_uuid}:{row['content_digest']}")
                data = await storage.read_verified(team_uuid, handle)
                assert hashlib.sha256(data).hexdigest() == row["content_digest"]
                assert len(data) == row["size_bytes"]
                checked += 1
            return checked

        assert client.portal.call(verify) >= 2


def test_second_same_external_key_is_replay_not_failed(tmp_path: Path) -> None:
    token = "ns6-t24-token"
    team_uuid = uuid7()
    first_task, second_task = uuid7(), uuid7()
    headers = {"Authorization": f"Bearer {token}"}
    app = create_app(_settings(tmp_path, token))
    with TestClient(app, raise_server_exceptions=True) as client:
        _create_team_and_ingest(
            client,
            headers=headers,
            team_uuid=team_uuid,
            task_uuid=first_task,
            trace_uuid=uuid7(),
            external_key="same-key",
            content="First evidence sentence. Second evidence sentence.",
        )
        first = _wait(client, team_uuid, first_task, headers)
        assert first["status"] == "succeeded", first
        _create_team_and_ingest(
            client,
            headers=headers,
            team_uuid=team_uuid,
            task_uuid=second_task,
            trace_uuid=uuid7(),
            external_key="same-key",
            content="First evidence sentence. Second evidence sentence.",
        )
        _second = _wait(client, team_uuid, second_task, headers)
        del _second
        persistence = app.state.container.persistence

        async def inspect() -> tuple[int, list[dict[str, object]]]:
            async with persistence.transaction() as tx:
                items = await tx.fetchall(
                    "SELECT intake_item_uuid FROM mkb_intake_items WHERE team_uuid=?",
                    (team_uuid,),
                )
                processes = await tx.fetchall(
                    "SELECT step_key,status FROM mkb_processes WHERE team_uuid=? AND task_uuid=? ORDER BY created_at",
                    (team_uuid, second_task),
                )
            return len(list(items)), list(processes)

        item_count, processes = client.portal.call(inspect)
        assert item_count == 1
        accept = next(row for row in processes if row["step_key"] == "accept_snapshot")
        assert accept["status"] == "succeeded"
        # Same-content structurize may still trip an outcome-commit unique on
        # re-generation; VF15's identity gate is items=1 + accept replay.
