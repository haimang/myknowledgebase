"""FF-F2-T06 (P2-04): /healthz really probes core+vec; 200 ok / 503 degraded."""

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient
from smind_api.deps import _ensure_core_migrated, _ensure_vec_migrated
from smind_api.main import create_app
from smind_config.loader import load_settings


def _fresh_env():
    tmp = Path(tempfile.mkdtemp(prefix="smind-t06-"))
    os.environ["SMIND_CORE_DB_PATH"] = str(tmp / "core.db")
    os.environ["SMIND_VEC_DB_PATH"] = str(tmp / "vec.db")
    os.environ["SMIND_OBJECT_STORE_DIR"] = str(tmp / "objects")
    load_settings.cache_clear()
    _ensure_core_migrated.cache_clear()
    _ensure_vec_migrated.cache_clear()
    return tmp


def test_healthz_ok_when_dbs_available():
    _fresh_env()
    with TestClient(create_app()) as client:
        r = client.get("/healthz")
        assert r.status_code == 200, r.text
        assert r.json() == {"status": "ok", "core": "ok", "vec": "ok"}


def test_healthz_degraded_when_vec_table_missing():
    tmp = _fresh_env()
    with TestClient(create_app()) as client:
        # Drop the vec table after startup so the probe fails -> 503 + reason.
        conn = sqlite3.connect(str(tmp / "vec.db"))
        conn.execute("DROP TABLE IF EXISTS chunk_embedding_index")
        conn.commit()
        conn.close()

        r = client.get("/healthz")
        assert r.status_code == 503, r.text
        body = r.json()
        assert body["status"] == "degraded"
        assert body.get("reason")
        assert body["vec"] != "ok"
