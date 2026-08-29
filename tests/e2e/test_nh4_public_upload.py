"""NH4-T01/T03: authenticated streamed upload and metadata-only stat."""

from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.runtime.config import Settings


def _settings(tmp_path: Path, *, global_cap: int = 1_048_576, object_cap: int = 8 * 1024 * 1024) -> Settings:
    return Settings(
        internal_token="nh4-upload-token",
        database_path=tmp_path / "mkb.sqlite3",
        object_root=tmp_path / "objects",
        persistence_backend="turso",
        concurrent_writes_required=False,
        native_vector_required=False,
        inference_probe_enabled=False,
        live_inference=False,
        max_request_bytes=global_cap,
        object_max_bytes=object_cap,
        rate_limit_ip_per_min=10_000,
        rate_limit_token_per_min=10_000,
    )


def _team(client: TestClient, team_uuid: str, headers: dict[str, str]) -> None:
    response = client.post(
        "/v1/teams",
        headers=headers,
        json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": f"team-{team_uuid[-6:]}"},
    )
    assert response.status_code == 201, response.text


def _upload(
    client: TestClient,
    team_uuid: str,
    headers: dict[str, str],
    body: bytes,
    *,
    media_type: str = "text/plain",
):
    return client.post(
        f"/v1/teams/{team_uuid}/objects:upload",
        headers={
            **headers,
            "content-type": media_type,
            "x-mkb-expected-sha256": hashlib.sha256(body).hexdigest(),
        },
        content=body,
    )


def test_auth_upload_returns_handle_catalog_pending_zero_intake(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    headers = {"Authorization": "Bearer nh4-upload-token"}
    body = (b"nh4-public-upload-sentinel-" * 64) + b"end"
    with TestClient(app, raise_server_exceptions=True) as client:
        _team(client, team_uuid, headers)
        response = _upload(client, team_uuid, headers, body)
        assert response.status_code == 201, response.text
        uploaded = response.json()
        assert set(uploaded) == {"handle", "digest", "size_bytes", "media_type", "disposition"}
        assert uploaded == {
            "handle": f"mkbobj:v1:{team_uuid}:{hashlib.sha256(body).hexdigest()}",
            "digest": hashlib.sha256(body).hexdigest(),
            "size_bytes": len(body),
            "media_type": "text/plain",
            "disposition": "pending",
        }
        stat = client.get(
            f"/v1/teams/{team_uuid}/objects:stat",
            headers=headers,
            params={"handle": uploaded["handle"]},
        )
        assert stat.status_code == 200, stat.text
        assert stat.json() == uploaded

        async def inspect() -> tuple[dict, dict, dict[str, int]]:
            async with app.state.container.persistence.transaction() as tx:
                catalog = await tx.fetchone(
                    "SELECT content_digest,size_bytes,media_type,tombstoned_at FROM mkb_stored_objects WHERE team_uuid=?",
                    (team_uuid,),
                )
                pending = await tx.fetchone(
                    "SELECT purpose,released_at FROM mkb_object_references WHERE team_uuid=?",
                    (team_uuid,),
                )
                counts = {}
                for table in ("mkb_intake_sources", "mkb_intake_items", "mkb_intake_revisions"):
                    row = await tx.fetchone(f"SELECT COUNT(*) AS count FROM {table} WHERE team_uuid=?", (team_uuid,))
                    assert row is not None
                    counts[table] = int(row["count"])
            assert catalog is not None and pending is not None
            return catalog, pending, counts

        catalog, pending, counts = client.portal.call(inspect)
        assert catalog == {
            "content_digest": uploaded["digest"],
            "size_bytes": len(body),
            "media_type": "text/plain",
            "tombstoned_at": None,
        }
        assert pending == {"purpose": "upload_pending", "released_at": None}
        assert counts == {
            "mkb_intake_sources": 0,
            "mkb_intake_items": 0,
            "mkb_intake_revisions": 0,
        }


def test_upload_stream_respects_object_cap_not_global_1mib(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path, global_cap=1024, object_cap=8192))
    team_uuid = uuid7()
    headers = {"Authorization": "Bearer nh4-upload-token"}
    body = b"x" * 4096
    with TestClient(app, raise_server_exceptions=True) as client:
        _team(client, team_uuid, headers)
        response = _upload(client, team_uuid, headers, body)
        assert response.status_code == 201, response.text
        assert response.json()["size_bytes"] == 4096


def test_stat_closed_set_cross_team_403_unauth_401(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_a, team_b = uuid7(), uuid7()
    headers = {"Authorization": "Bearer nh4-upload-token"}
    with TestClient(app, raise_server_exceptions=True) as client:
        _team(client, team_a, headers)
        _team(client, team_b, headers)
        uploaded = _upload(client, team_a, headers, b"team scoped").json()
        cross = client.get(
            f"/v1/teams/{team_b}/objects:stat",
            headers=headers,
            params={"handle": uploaded["handle"]},
        )
        assert cross.status_code == 403
        assert cross.json()["error"]["code"] == "OBJECT_AUTH_TEAM_MISMATCH"
        unauth = client.get(
            f"/v1/teams/{team_a}/objects:stat",
            params={"handle": uploaded["handle"]},
        )
        assert unauth.status_code == 401
        assert unauth.json()["error"]["code"] == "SEC_TOKEN_MISSING"
        raw = client.get(f"/v1/teams/{team_a}/objects/{uploaded['digest']}", headers=headers)
        assert raw.status_code in {404, 405}


def test_cancel_releases_pending_and_stat_becomes_expired(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    headers = {"Authorization": "Bearer nh4-upload-token"}
    with TestClient(app, raise_server_exceptions=True) as client:
        _team(client, team_uuid, headers)
        uploaded = _upload(client, team_uuid, headers, b"cancel-before-ingest").json()
        cancelled = client.post(
            f"/v1/teams/{team_uuid}/objects:cancel",
            headers=headers,
            json={"handle": uploaded["handle"]},
        )
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json() == {**uploaded, "disposition": "expired"}
        stat = client.get(
            f"/v1/teams/{team_uuid}/objects:stat",
            headers=headers,
            params={"handle": uploaded["handle"]},
        )
        assert stat.json()["disposition"] == "expired"
        async def released() -> dict:
            async with app.state.container.persistence.transaction() as tx:
                row = await tx.fetchone(
                    "SELECT released_at FROM mkb_object_references WHERE team_uuid=? AND purpose='upload_pending'",
                    (team_uuid,),
                )
            assert row is not None
            return row
        assert client.portal.call(released)["released_at"] is not None
