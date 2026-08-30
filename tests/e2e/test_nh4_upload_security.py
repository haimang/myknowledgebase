"""NH4-T07: public upload attack vectors fail closed without false catalog truth."""

from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from tests.e2e.test_nh4_public_upload import _settings, _team


def _auth() -> dict[str, str]:
    return {"Authorization": "Bearer nh4-upload-token"}


def test_filename_path_traversal_rejected(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        _team(client, team_uuid, _auth())
        for filename in (
            'filename="../escape.txt"',
            'filename="..\\..\\windows.txt"',
            'filename="%2e%2e%2fencoded.txt"',
            'filename="nul\x00name.txt"',
            "filename=\"percent%00nul.txt\"",
        ):
            response = client.post(
                f"/v1/teams/{team_uuid}/objects:upload",
                headers={**_auth(), "content-type": "text/plain", "content-disposition": filename},
                content=b"must not be accepted",
            )
            assert response.status_code == 422
            assert response.json()["error"]["code"] == "SEC_PATH_REJECTED"
        assert not any(".." in path.parts for path in app.state.container.storage.root.rglob("*"))


def test_declared_mime_is_not_identity(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    body = b"plain bytes declared as an image"
    digest = hashlib.sha256(body).hexdigest()
    with TestClient(app, raise_server_exceptions=True) as client:
        _team(client, team_uuid, _auth())
        response = client.post(
            f"/v1/teams/{team_uuid}/objects:upload",
            headers={**_auth(), "content-type": "image/png"},
            content=body,
        )
        assert response.status_code == 201, response.text
        assert response.json()["digest"] == digest
        assert response.json()["media_type"] == "image/png"
        expected = app.state.container.storage.root / "objects" / team_uuid / "sha256" / digest[:2] / digest[2:4] / digest
        assert expected.read_bytes() == body
        assert not list((app.state.container.storage.root / "objects").rglob("*.png"))


def test_oversize_and_chunked_413(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path, global_cap=1024, object_cap=32))
    team_uuid = uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        _team(client, team_uuid, _auth())
        sized = client.post(
            f"/v1/teams/{team_uuid}/objects:upload",
            headers={**_auth(), "content-type": "application/octet-stream"},
            content=b"x" * 33,
        )
        assert sized.status_code == 413
        assert sized.json()["error"]["code"] == "OBJECT_BUDGET_SIZE"

        def chunks():
            yield b"y" * 20
            yield b"z" * 20

        chunked = client.post(
            f"/v1/teams/{team_uuid}/objects:upload",
            headers={**_auth(), "content-type": "application/octet-stream"},
            content=chunks(),
        )
        assert chunked.status_code == 413
        assert chunked.json()["error"]["code"] == "OBJECT_BUDGET_SIZE"

        async def count() -> dict:
            async with app.state.container.persistence.transaction() as tx:
                row = await tx.fetchone("SELECT COUNT(*) AS count FROM mkb_stored_objects WHERE team_uuid=?", (team_uuid,))
            assert row is not None
            return row

        assert client.portal.call(count) == {"count": 0}


def test_digest_mismatch_422_and_empty_body_no_catalog(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        _team(client, team_uuid, _auth())
        mismatch = client.post(
            f"/v1/teams/{team_uuid}/objects:upload",
            headers={
                **_auth(),
                "content-type": "text/plain",
                "x-mkb-expected-sha256": "0" * 64,
            },
            content=b"actual",
        )
        assert mismatch.status_code == 422
        assert mismatch.json()["error"]["code"] == "OBJECT_INTEGRITY_DIGEST"
        empty = client.post(
            f"/v1/teams/{team_uuid}/objects:upload",
            headers={**_auth(), "content-type": "text/plain"},
            content=b"",
        )
        assert empty.status_code == 422
        assert empty.json()["error"]["code"] == "OBJECT_EMPTY"
        multipart = client.post(
            f"/v1/teams/{team_uuid}/objects:upload",
            headers={**_auth(), "content-type": "multipart/form-data; boundary=forbidden"},
            content=b"--forbidden--",
        )
        assert multipart.status_code == 422
        assert multipart.json()["error"]["code"] == "OBJECT_MEDIA_TYPE_INVALID"
        empty_digest = hashlib.sha256(b"").hexdigest()
        empty_path = (
            app.state.container.storage.root
            / "objects"
            / team_uuid
            / "sha256"
            / empty_digest[:2]
            / empty_digest[2:4]
            / empty_digest
        )
        assert not empty_path.exists()
        async def count() -> dict:
            async with app.state.container.persistence.transaction() as tx:
                row = await tx.fetchone("SELECT COUNT(*) AS count FROM mkb_stored_objects WHERE team_uuid=?", (team_uuid,))
            assert row is not None
            return row
        assert client.portal.call(count) == {"count": 0}


def test_unauth_and_cross_team(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_a, team_b = uuid7(), uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        _team(client, team_a, _auth())
        _team(client, team_b, _auth())
        unauth = client.post(
            f"/v1/teams/{team_a}/objects:upload",
            headers={"content-type": "text/plain"},
            content=b"unauthorized",
        )
        assert unauth.status_code == 401
        uploaded = client.post(
            f"/v1/teams/{team_a}/objects:upload",
            headers={**_auth(), "content-type": "text/plain"},
            content=b"team-a",
        )
        assert uploaded.status_code == 201
        cross = client.get(
            f"/v1/teams/{team_b}/objects:stat",
            headers=_auth(),
            params={"handle": uploaded.json()["handle"]},
        )
        assert cross.status_code == 403
        assert cross.json()["error"]["code"] == "OBJECT_AUTH_TEAM_MISMATCH"


def test_zero_presign_symbols_in_upload_surface() -> None:
    root = Path(__file__).resolve().parents[2]
    paths = [
        root / "api/public/routes.py",
        root / "src/contracts/api/objects.py",
        root / "src/services/object_upload.py",
        root / "src/services/object_upload_ttl.py",
    ]
    source = "\n".join(path.read_text(encoding="utf-8").casefold() for path in paths)
    assert "presign" not in source
    assert "r2.cloudflare" not in source
