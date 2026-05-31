"""FF-F2-T05 (P2-03 / P3-02): business exceptions map to 4xx, not 500.

先红后绿 ([Q7]): without the global exception handler the service-layer
``ValueError``s bubble up as 500 (RED). After P2-03 they map to precise status
codes (GREEN): invalid credentials -> 401, not found -> 404.

restart-409: there is NO restart endpoint in this cluster (management routes
are read-only; ManagementService has no request_restart). Per AP §8.4 the 409
path is therefore a GAP handed off to FF-F3-kernel-recovery.md; it is NOT faked
here. The 409 mapping itself is unit-covered in tests/unit/test_app_support.py.
"""

import os
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient
from smind_api.deps import _ensure_core_migrated, _ensure_vec_migrated
from smind_api.main import create_app
from smind_config.loader import load_settings


def _client():
    tmp = Path(tempfile.mkdtemp(prefix="smind-t05-"))
    os.environ["SMIND_CORE_DB_PATH"] = str(tmp / "core.db")
    os.environ["SMIND_VEC_DB_PATH"] = str(tmp / "vec.db")
    os.environ["SMIND_OBJECT_STORE_DIR"] = str(tmp / "objects")
    load_settings.cache_clear()
    _ensure_core_migrated.cache_clear()
    _ensure_vec_migrated.cache_clear()
    return TestClient(create_app())


def _register_login_team(client):
    reg = client.post(
        "/auth/register",
        json={"email": "t05@example.com", "password": "pw", "display_name": "t05"},
    )
    assert reg.status_code == 200, reg.text
    login = client.post("/auth/login", json={"email": "t05@example.com", "password": "pw"})
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['token']}"}
    team = client.post(
        "/team/bootstrap", json={"name": "T05", "slug": "t05"}, headers=headers
    )
    assert team.status_code == 200, team.text
    return headers


def test_login_invalid_credentials_maps_401():
    with _client() as client:
        r = client.post(
            "/auth/login", json={"email": "nobody@example.com", "password": "x"}
        )
        assert r.status_code == 401, r.text
        body = r.json()
        assert "detail" in body and "code" in body


def test_static_confirm_unknown_upload_maps_404():
    with _client() as client:
        headers = _register_login_team(client)
        r = client.post(
            "/ingestion/static/confirm",
            json={
                "upload_id": "does-not-exist",
                "path": "/static/x.json",
                "content": "{}",
                "role": "uploaded",
            },
            headers=headers,
        )
        assert r.status_code == 404, r.text
        body = r.json()
        assert "detail" in body and "code" in body


def test_real_app_registers_business_exception_handlers():
    """G-CR5-05 wiring is honest: the REAL ``create_app()`` must register the
    ValueError + SmindError handlers on the app itself.

    This exercises ``main.create_app``'s wiring directly (not a hand-built app),
    so it is genuinely RED on the pre-fix ``main.py`` (which registered no
    handlers) and GREEN only once P2-03 wires them in. The body-level 401/404
    tests above prove the handler *behaves*; this proves the handler is actually
    attached to the production app object.
    """
    from smind_common.errors import SmindError

    app = create_app()
    handlers = app.exception_handlers
    assert ValueError in handlers, (
        "create_app() did not register a ValueError exception handler "
        f"(handlers: {list(handlers)})"
    )
    assert SmindError in handlers, (
        "create_app() did not register a SmindError exception handler "
        f"(handlers: {list(handlers)})"
    )
    # Both business exceptions must route to the same business handler.
    assert handlers[ValueError] is handlers[SmindError]
