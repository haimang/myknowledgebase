"""NH4-T02: concurrent public replay converges on one live CAS identity."""

from __future__ import annotations

import hashlib
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.services.object_gc import ObjectGcDisposition
from tests.e2e.test_nh4_public_upload import _settings, _team, _upload


def test_concurrent_same_team_digest_size_same_handle(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    headers = {"Authorization": "Bearer nh4-upload-token", "content-type": "application/octet-stream"}
    body = b"concurrent-public-upload" * 256
    with TestClient(app, raise_server_exceptions=True) as client:
        _team(client, team_uuid, {"Authorization": "Bearer nh4-upload-token"})

        def upload() -> tuple[int, dict]:
            response = client.post(
                f"/v1/teams/{team_uuid}/objects:upload",
                headers={**headers, "x-mkb-expected-sha256": hashlib.sha256(body).hexdigest()},
                content=body,
            )
            return response.status_code, response.json()

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: upload(), range(2)))
        assert sorted(status for status, _ in responses) == [200, 201]
        assert {payload["handle"] for _, payload in responses} == {
            f"mkbobj:v1:{team_uuid}:{hashlib.sha256(body).hexdigest()}"
        }

        async def counts() -> tuple[dict, dict]:
            async with app.state.container.persistence.transaction() as tx:
                catalog = await tx.fetchone(
                    "SELECT COUNT(*) AS count FROM mkb_stored_objects WHERE team_uuid=? "
                    "AND content_digest=? AND size_bytes=? AND tombstoned_at IS NULL",
                    (team_uuid, hashlib.sha256(body).hexdigest(), len(body)),
                )
                pending = await tx.fetchone(
                    "SELECT COUNT(*) AS count FROM mkb_object_references WHERE team_uuid=? "
                    "AND purpose='upload_pending' AND released_at IS NULL",
                    (team_uuid,),
                )
            assert catalog is not None and pending is not None
            return catalog, pending

        assert client.portal.call(counts) == ({"count": 1}, {"count": 1})


def test_expected_digest_conflicting_size_typed_fail(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    headers = {"Authorization": "Bearer nh4-upload-token", "content-type": "text/plain"}
    original = b"original-upload"
    original_digest = hashlib.sha256(original).hexdigest()
    with TestClient(app, raise_server_exceptions=True) as client:
        _team(client, team_uuid, {"Authorization": "Bearer nh4-upload-token"})
        first = client.post(
            f"/v1/teams/{team_uuid}/objects:upload",
            headers={**headers, "x-mkb-expected-sha256": original_digest},
            content=original,
        )
        assert first.status_code == 201
        conflicting = client.post(
            f"/v1/teams/{team_uuid}/objects:upload",
            headers={**headers, "x-mkb-expected-sha256": original_digest},
            content=b"different-sized-body",
        )
        assert conflicting.status_code == 422
        assert conflicting.json()["error"]["code"] == "OBJECT_INTEGRITY_DIGEST"

        async def live() -> dict:
            async with app.state.container.persistence.transaction() as tx:
                row = await tx.fetchone(
                    "SELECT content_digest,size_bytes FROM mkb_stored_objects WHERE team_uuid=? AND tombstoned_at IS NULL",
                    (team_uuid,),
                )
            assert row is not None
            return row

        assert client.portal.call(live) == {"content_digest": original_digest, "size_bytes": len(original)}


_NH4_HEADERS = {"Authorization": "Bearer nh4-upload-token"}


def _clocked_app(tmp_path: Path):
    app = create_app(_settings(tmp_path).model_copy(update={"object_gc_enabled": False}))
    now = datetime.now(UTC)
    clock = {"t": now}
    app.state.container.object_gc._clock = lambda: clock["t"]  # noqa: SLF001
    app.state.container.object_gc._orphan_grace = timedelta(seconds=10)  # noqa: SLF001
    app.state.container.object_upload_lifecycle._clock = lambda: clock["t"]  # noqa: SLF001
    app.state.container.object_upload_lifecycle._pending_ttl = timedelta(seconds=10)  # noqa: SLF001
    return app, clock


def _created_at(app, client: TestClient, team_uuid: str) -> datetime:
    row = _port(
        app,
        client,
        "SELECT created_at FROM mkb_object_references WHERE team_uuid=? AND purpose='upload_pending'",
        (team_uuid,),
    )
    assert row is not None
    return datetime.fromisoformat(str(row["created_at"]).replace("Z", "+00:00")).astimezone(UTC)


def _port(app, client: TestClient, query: str, params: tuple[object, ...]) -> Any:
    async def inspect() -> Any:
        async with app.state.container.persistence.transaction() as tx:
            return await tx.fetchone(query, params)

    return client.portal.call(inspect)


def _wait_task(client: TestClient, team_uuid: str, task_uuid: str) -> dict[str, Any]:
    deadline = time.monotonic() + 40
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=_NH4_HEADERS)
        assert response.status_code == 200, response.text
        latest = response.json()
        if latest["status"] in {"succeeded", "failed", "cancelled"}:
            return latest
        time.sleep(0.02)
    raise AssertionError(f"Task {task_uuid} did not become terminal: {latest}")


def test_interleave_parallel_upload_and_gc(tmp_path: Path) -> None:
    app, _clock = _clocked_app(tmp_path)
    team_uuid = uuid7()
    body = b"nh9-upload-gc-interleave" * 32
    with TestClient(app, raise_server_exceptions=True) as client:
        _team(client, team_uuid, _NH4_HEADERS)
        first = _upload(client, team_uuid, _NH4_HEADERS, body)
        assert first.status_code == 201, first.text

        def second_upload() -> tuple[int, dict]:
            response = _upload(client, team_uuid, _NH4_HEADERS, body)
            return response.status_code, response.json()

        def gc_scan() -> tuple:
            return client.portal.call(app.state.container.object_gc.collect_candidates)

        with ThreadPoolExecutor(max_workers=2) as pool:
            uploaded = pool.submit(second_upload)
            scanned = pool.submit(gc_scan)
            status, payload = uploaded.result()
            candidates = scanned.result()
        assert status in {200, 201}, payload
        assert payload["handle"] == first.json()["handle"]
        assert candidates == ()
        catalog = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_stored_objects WHERE team_uuid=? AND tombstoned_at IS NULL",
            (team_uuid,),
        )
        pending = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_object_references WHERE team_uuid=? "
            "AND purpose='upload_pending' AND released_at IS NULL",
            (team_uuid,),
        )
        items = _port(app, client, "SELECT COUNT(*) AS n FROM mkb_intake_items WHERE team_uuid=?", (team_uuid,))
        assert catalog is not None and int(catalog["n"]) == 1
        assert pending is not None and int(pending["n"]) == 1
        assert items is not None and int(items["n"]) == 0


def test_interleave_ttl_and_ingest(tmp_path: Path) -> None:
    app, clock = _clocked_app(tmp_path)
    team_uuid = uuid7()
    body = b"NH9 ttl ingest interleave sentinel zephyrquartz"
    with TestClient(app, raise_server_exceptions=True) as client:
        _team(client, team_uuid, _NH4_HEADERS)
        uploaded = _upload(client, team_uuid, _NH4_HEADERS, body)
        assert uploaded.status_code == 201, uploaded.text
        handle = uploaded.json()["handle"]
        task_uuid, trace_uuid = uuid7(), uuid7()
        created = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=_NH4_HEADERS,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": task_uuid,
                "trace_uuid": trace_uuid,
                "request_intent": "intake.ingest",
                "payload": {
                    "json_prompt_id": "promptB.json.generic",
                    "source": {
                        "source_kind": "local_object",
                        "realm": "documentation",
                        "type": "article",
                        "channel": "general",
                        "source_name": "nh9-ttl-ingest",
                        "external_key": "nh9-ttl-ingest",
                        "logical_handle": handle,
                        "media_type": "text/plain",
                    },
                },
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": task_uuid,
                    "trace_uuid": trace_uuid,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "nh9-t06",
                    "created_at": utc_now(),
                },
            },
        )
        assert created.status_code == 201, created.text
        deadline = time.monotonic() + 40
        acquired = False
        while time.monotonic() < deadline:
            process = _port(
                app,
                client,
                "SELECT status FROM mkb_processes WHERE team_uuid=? AND task_uuid=? "
                "AND process_key='intake.acquire.local_object'",
                (team_uuid, task_uuid),
            )
            if process is not None and process["status"] == "succeeded":
                acquired = True
                break
            time.sleep(0.02)
        assert acquired, "local_object acquire did not succeed before TTL interleave"
        clock["t"] = _created_at(app, client, team_uuid) + timedelta(seconds=11)
        ttl = client.portal.call(app.state.container.object_upload_lifecycle.scan_once)
        assert ttl.released_pending in {0, 1}
        terminal = _wait_task(client, team_uuid, task_uuid)
        assert terminal["status"] == "succeeded", terminal
        items = _port(app, client, "SELECT COUNT(*) AS n FROM mkb_intake_items WHERE team_uuid=?", (team_uuid,))
        assert items is not None and int(items["n"]) == 1
        stat = client.get(
            f"/v1/teams/{team_uuid}/objects:stat",
            headers=_NH4_HEADERS,
            params={"handle": handle},
        )
        assert stat.status_code == 200, stat.text
        assert stat.json()["disposition"] in {"ingested", "pending"}
        candidates = client.portal.call(app.state.container.object_gc.collect_candidates)
        assert candidates == ()


def test_tombstone_then_reupload_new_handle_zero_item(tmp_path: Path) -> None:
    app, clock = _clocked_app(tmp_path)
    team_uuid = uuid7()
    body = b"nh9-tombstone-reupload-bytes"
    with TestClient(app, raise_server_exceptions=True) as client:
        _team(client, team_uuid, _NH4_HEADERS)
        first = _upload(client, team_uuid, _NH4_HEADERS, body)
        assert first.status_code == 201, first.text
        handle = first.json()["handle"]
        created = _created_at(app, client, team_uuid)
        clock["t"] = created + timedelta(seconds=11)
        released = client.portal.call(app.state.container.object_upload_lifecycle.scan_once)
        assert released.released_pending == 1
        clock["t"] = created + timedelta(seconds=23)
        gc = client.portal.call(app.state.container.object_gc.scan_once)
        assert gc.deleted_count == 1
        assert gc.results[0].disposition is ObjectGcDisposition.DELETED
        tombstoned = client.get(
            f"/v1/teams/{team_uuid}/objects:stat",
            headers=_NH4_HEADERS,
            params={"handle": handle},
        )
        assert tombstoned.status_code == 200, tombstoned.text
        assert tombstoned.json()["disposition"] == "tombstoned"
        before_items = _port(app, client, "SELECT COUNT(*) AS n FROM mkb_intake_items WHERE team_uuid=?", (team_uuid,))
        second = _upload(client, team_uuid, _NH4_HEADERS, body)
        assert second.status_code == 201, second.text
        assert second.json()["handle"] == handle
        live = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_stored_objects WHERE team_uuid=? AND tombstoned_at IS NULL",
            (team_uuid,),
        )
        dead = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_stored_objects WHERE team_uuid=? AND tombstoned_at IS NOT NULL",
            (team_uuid,),
        )
        after_items = _port(app, client, "SELECT COUNT(*) AS n FROM mkb_intake_items WHERE team_uuid=?", (team_uuid,))
        assert live is not None and int(live["n"]) == 1
        assert dead is not None and int(dead["n"]) == 1
        assert before_items is not None and after_items is not None
        assert int(before_items["n"]) == int(after_items["n"]) == 0
