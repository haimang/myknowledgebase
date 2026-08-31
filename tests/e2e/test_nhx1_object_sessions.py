"""NHX1-T15: upload sessions own exact pending refs independently of byte handles."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.storage.models import ObjectHandle
from tests.local_runtime import local_mock_settings


def test_same_bytes_have_isolated_sessions_and_reserved_session_survives_ttl(tmp_path: Path) -> None:
    token = "nhx1-session-token"
    headers = {"Authorization": f"Bearer {token}", "content-type": "text/plain"}
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
    team_uuid = uuid7()
    body = b"same bytes, two independent upload calls"
    with TestClient(app, raise_server_exceptions=True) as client:
        assert client.post(
            "/v1/teams",
            headers={"Authorization": f"Bearer {token}"},
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "sessions"},
        ).status_code == 201
        first = client.post(
            f"/v1/teams/{team_uuid}/objects:upload",
            headers={**headers, "idempotency-key": "session-a"},
            content=body,
        )
        assert first.status_code == 201, first.text
        first_view = first.json()
        session_a = first_view["session_token"]
        replay = client.post(
            f"/v1/teams/{team_uuid}/objects:upload",
            headers={**headers, "idempotency-key": "session-a"},
            content=body,
        )
        assert replay.status_code == 200, replay.text
        assert replay.json()["session_token"] == session_a
        second = client.post(
            f"/v1/teams/{team_uuid}/objects:upload",
            headers={**headers, "idempotency-key": "session-b"},
            content=body,
        )
        assert second.status_code == 201, second.text
        second_view = second.json()
        session_b = second_view["session_token"]
        assert session_a != session_b
        assert first_view["handle"] == second_view["handle"]

        async def counts() -> dict[str, object]:
            async with app.state.container.persistence.read_snapshot() as tx:
                refs = await tx.fetchall(
                    "SELECT owner_kind,upload_session_uuid,released_at FROM mkb_object_references "
                    "WHERE team_uuid=? AND purpose='upload_pending' ORDER BY upload_session_uuid",
                    (team_uuid,),
                )
                sessions = await tx.fetchall(
                    "SELECT idempotency_key,state,row_revision FROM mkb_object_upload_sessions WHERE team_uuid=? "
                    "ORDER BY idempotency_key",
                    (team_uuid,),
                )
            return {"refs": refs, "sessions": sessions}

        observed = client.portal.call(counts)
        assert len(observed["refs"]) == 2
        assert all(row["owner_kind"] == "upload_session" for row in observed["refs"])
        assert [row["idempotency_key"] for row in observed["sessions"]] == ["session-a", "session-b"]
        cancelled = client.post(
            f"/v1/teams/{team_uuid}/objects:cancel",
            headers={"Authorization": f"Bearer {token}"},
            json={"handle": first_view["handle"], "session_token": session_a},
        )
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["disposition"] == "expired"
        stat_b = client.get(
            f"/v1/teams/{team_uuid}/objects:stat",
            headers={"Authorization": f"Bearer {token}", "x-mkb-session-token": session_b},
            params={"handle": second_view["handle"]},
        )
        assert stat_b.status_code == 200 and stat_b.json()["disposition"] == "pending"

        async def seed_task_and_age() -> str:
            task_uuid = uuid7()
            trace_uuid = uuid7()
            now = "2026-08-31T00:00:00Z"
            async with app.state.container.persistence.transaction() as tx:
                await tx.execute(
                    "INSERT INTO mkb_tasks(team_uuid,task_uuid,trace_uuid,schema_version,request_intent,"
                    "creation_fingerprint,audit_bound,title,status,current_generation,received_at,created_at,updated_at) "
                    "VALUES (?,?,?,?,?,?,1,?,'queued',1,?,?,?)",
                    (team_uuid, task_uuid, trace_uuid, "mkb.task.v1", "intake.ingest", "a" * 64, "session-task", now, now, now),
                )
                await tx.execute(
                    "UPDATE mkb_object_upload_sessions SET expires_at=?,created_at=? WHERE idempotency_key='session-b'",
                    (now, now),
                )
            return task_uuid

        task_uuid = client.portal.call(seed_task_and_age)

        async def reserve() -> bool:
            return await app.state.container.object_upload.reserve_session(
                team_uuid=team_uuid,
                session_token=session_b,
                task_uuid=task_uuid,
                task_generation=1,
            )

        assert client.portal.call(reserve) is True
        app.state.container.object_upload_lifecycle._pending_ttl = timedelta(seconds=1)  # noqa: SLF001
        scan = client.portal.call(app.state.container.object_upload_lifecycle.scan_once)
        assert scan.released_pending == 0

        async def reserved_stat():
            return await app.state.container.object_upload.stat(
                team_uuid=team_uuid,
                handle=ObjectHandle(value=second_view["handle"]),
                session_token=session_b,
            )

        reserved = client.portal.call(reserved_stat)
        assert reserved.disposition == "pending"

        async def consume() -> bool:
            return await app.state.container.object_upload.consume_session(
                team_uuid=team_uuid,
                session_token=session_b,
            )

        assert client.portal.call(consume) is True
        final = client.get(
            f"/v1/teams/{team_uuid}/objects:stat",
            headers={"Authorization": f"Bearer {token}", "x-mkb-session-token": session_b},
            params={"handle": second_view["handle"]},
        )
        assert final.status_code == 200 and final.json()["disposition"] == "expired"
