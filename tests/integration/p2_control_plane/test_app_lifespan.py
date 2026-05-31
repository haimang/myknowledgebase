"""FF-F2-T03 (P2-01): lifespan applies migrations + self-checks (fail-loud)."""

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


def _fresh_env(prefix="smind-t03-"):
    tmp = Path(tempfile.mkdtemp(prefix=prefix))
    os.environ["SMIND_CORE_DB_PATH"] = str(tmp / "core.db")
    os.environ["SMIND_VEC_DB_PATH"] = str(tmp / "vec.db")
    os.environ["SMIND_OBJECT_STORE_DIR"] = str(tmp / "objects")
    load_settings.cache_clear()
    _ensure_core_migrated.cache_clear()
    _ensure_vec_migrated.cache_clear()
    return tmp


def test_lifespan_runs_migrations():
    tmp = _fresh_env()
    core_db = str(tmp / "core.db")
    with TestClient(create_app()):
        conn = sqlite3.connect(core_db)
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        finally:
            conn.close()
    tables = {r[0] for r in rows}
    assert {"users", "sessions"} <= tables


def test_lifespan_fail_loud_on_unusable_db():
    # Point the core db at a path whose parent is a *file* (not a directory),
    # so opening/migrating it fails. The startup self-check must raise and abort
    # boot (fail-loud) rather than starting silently broken.
    tmp = Path(tempfile.mkdtemp(prefix="smind-t03-fail-"))
    blocker = tmp / "not_a_dir"
    blocker.write_text("i am a file, not a directory")
    os.environ["SMIND_CORE_DB_PATH"] = str(blocker / "core.db")
    os.environ["SMIND_VEC_DB_PATH"] = str(tmp / "vec.db")
    os.environ["SMIND_OBJECT_STORE_DIR"] = str(tmp / "objects")
    load_settings.cache_clear()
    _ensure_core_migrated.cache_clear()
    _ensure_vec_migrated.cache_clear()
    try:
        with pytest.raises(Exception):
            with TestClient(create_app()):
                pass
    finally:
        load_settings.cache_clear()
