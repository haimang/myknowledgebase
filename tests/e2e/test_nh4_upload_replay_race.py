"""NH4-T02: concurrent public replay converges on one live CAS identity."""

from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from tests.e2e.test_nh4_public_upload import _settings, _team


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
