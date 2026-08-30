"""NH9-T02: same fingerprint replays; different fingerprint 409; double-flight single root."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from tests.e2e.test_source_capability_paths import _settings

_TOKEN = "source-capability-token"
_HEADERS = {"Authorization": f"Bearer {_TOKEN}"}


def _body(team_uuid: str, task_uuid: str, trace_uuid: str, content: str) -> dict[str, Any]:
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
                "external_key": "nh9-identity",
                "content": content,
                "realm": "documentation",
                "type": "article",
                "channel": "general",
                "source_name": "nh9-identity",
            },
        },
        "audit": {
            "schema_version": "mkb.task-audit.v1",
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "trace_uuid": trace_uuid,
            "audit_type": "business_review",
            "audit_status": "not_required",
            "source": "nh9-t02",
            "created_at": utc_now(),
        },
    }


def _port(app, client: TestClient, query: str, params: tuple[object, ...]) -> Any:
    async def inspect() -> Any:
        async with app.state.container.persistence.transaction() as tx:
            return await tx.fetchone(query, params)

    return client.portal.call(inspect)


def test_same_fingerprint_replays_original_view(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    body = _body(team_uuid, task_uuid, trace_uuid, "NH9 identity replay sentinel")
    with TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=_HEADERS,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh9-identity"},
            ).status_code
            == 201
        )
        first = client.post(f"/v1/teams/{team_uuid}/tasks", headers=_HEADERS, json=body)
        assert first.status_code == 201, first.text
        replay = client.post(f"/v1/teams/{team_uuid}/tasks", headers=_HEADERS, json=body)
        assert replay.status_code == 200, replay.text
        assert replay.json()["task_uuid"] == task_uuid
        assert replay.json()["links"]["self"] == first.json()["links"]["self"]
        roots = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_executions WHERE team_uuid=? AND task_uuid=? "
            "AND parent_execution_uuid IS NULL",
            (team_uuid, task_uuid),
        )
        assert roots is not None and int(roots["n"]) == 1


def test_different_fingerprint_409_task_identity_conflict(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    original = _body(team_uuid, task_uuid, trace_uuid, "NH9 identity original")
    with TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=_HEADERS,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh9-conflict"},
            ).status_code
            == 201
        )
        first = client.post(f"/v1/teams/{team_uuid}/tasks", headers=_HEADERS, json=original)
        assert first.status_code == 201, first.text
        changed = _body(team_uuid, task_uuid, trace_uuid, "NH9 identity mutated payload")
        conflict = client.post(f"/v1/teams/{team_uuid}/tasks", headers=_HEADERS, json=changed)
        assert conflict.status_code == 409, conflict.text
        assert conflict.json()["error"]["code"] == "task-identity-conflict"
        fingerprint = _port(
            app,
            client,
            "SELECT creation_fingerprint FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
            (team_uuid, task_uuid),
        )
        assert fingerprint is not None
        replay = client.post(f"/v1/teams/{team_uuid}/tasks", headers=_HEADERS, json=original)
        assert replay.status_code == 200
        after = _port(
            app,
            client,
            "SELECT creation_fingerprint FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
            (team_uuid, task_uuid),
        )
        assert after is not None
        assert after["creation_fingerprint"] == fingerprint["creation_fingerprint"]


def test_concurrent_double_flight_single_root(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    body = _body(team_uuid, task_uuid, trace_uuid, "NH9 concurrent identity")
    with TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=_HEADERS,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh9-race"},
            ).status_code
            == 201
        )

        def post() -> tuple[int, str]:
            response = client.post(f"/v1/teams/{team_uuid}/tasks", headers=_HEADERS, json=body)
            code = response.json().get("error", {}).get("code") if response.status_code >= 400 else ""
            return response.status_code, str(code)

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(lambda _: post(), range(2)))
        codes = sorted(status for status, _ in statuses)
        assert codes[0] in {200, 201, 409}
        assert codes[1] in {200, 201, 409}
        assert 201 in codes or codes == [200, 200]
        assert all(err in {"", "task-identity-conflict"} for _, err in statuses)
        roots = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_executions WHERE team_uuid=? AND task_uuid=? "
            "AND parent_execution_uuid IS NULL",
            (team_uuid, task_uuid),
        )
        tasks = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
            (team_uuid, task_uuid),
        )
        assert tasks is not None and int(tasks["n"]) == 1
        assert roots is not None and int(roots["n"]) == 1
