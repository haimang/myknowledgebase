"""FF-F2-T04 (P2-02): CORS middleware returns CORS headers."""

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
    tmp = Path(tempfile.mkdtemp(prefix="smind-t04-"))
    os.environ["SMIND_CORE_DB_PATH"] = str(tmp / "core.db")
    os.environ["SMIND_VEC_DB_PATH"] = str(tmp / "vec.db")
    os.environ["SMIND_OBJECT_STORE_DIR"] = str(tmp / "objects")
    load_settings.cache_clear()
    _ensure_core_migrated.cache_clear()
    _ensure_vec_migrated.cache_clear()
    return TestClient(create_app())


def test_preflight_returns_cors_headers():
    with _client() as client:
        r = client.options(
            "/auth/login",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert r.status_code in (200, 204)
        assert "access-control-allow-origin" in {k.lower() for k in r.headers}


def test_actual_request_returns_cors_header():
    with _client() as client:
        r = client.get("/healthz", headers={"Origin": "https://example.com"})
        assert "access-control-allow-origin" in {k.lower() for k in r.headers}
