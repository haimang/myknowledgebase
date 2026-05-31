"""FF-F2 fastapi-free unit coverage for app-assembly logic.

These tests exercise the pure functions in ``smind_api.app_support`` so the core
F2 invariants (exception->status mapping, healthz probe, startup self-check)
have real red->green proof even when the FastAPI web stack is absent. They do
NOT import fastapi.
"""

import sqlite3

import pytest

from smind_api.app_support import (
    error_code,
    health_report,
    is_business_exception,
    map_exception_to_status,
    run_startup_checks,
)
from smind_common.errors import SmindError
from storage_sqlite.engine import CoreSQLiteEngine
from storage_sqlite.migrations.runner import apply_core_migrations
from vector_sqlite_vec import VecSQLiteEngine, apply_vec_schema


# --- map_exception_to_status (P2-03) ----------------------------------------

def test_invalid_credentials_value_error_maps_401():
    assert map_exception_to_status(ValueError("invalid credentials")) == 401


def test_not_found_value_error_maps_404():
    assert map_exception_to_status(ValueError("upload 123 not found")) == 404


def test_conflict_value_error_maps_409():
    assert map_exception_to_status(ValueError("run already running")) == 409


def test_unclassified_value_error_maps_400_not_500():
    assert map_exception_to_status(ValueError("some odd validation")) == 400


def test_sminderror_code_takes_priority():
    assert map_exception_to_status(SmindError("x", code="AUTH_INVALID_CREDENTIALS")) == 401
    assert map_exception_to_status(SmindError("x", code="NOT_FOUND")) == 404
    assert map_exception_to_status(SmindError("x", code="CONFLICT")) == 409


def test_sminderror_unknown_code_maps_400():
    assert map_exception_to_status(SmindError("x", code="WHATEVER")) == 400


def test_programming_error_is_not_business_exception():
    assert is_business_exception(KeyError("bug")) is False
    with pytest.raises(TypeError):
        map_exception_to_status(KeyError("bug"))


def test_error_code_reads_smind_code():
    assert error_code(SmindError("x", code="NOT_FOUND")) == "NOT_FOUND"
    assert error_code(ValueError("y")) == "ValueError"


# --- health_report (P2-04) --------------------------------------------------

def _init_dbs(tmp_path):
    core = str(tmp_path / "core.db")
    vec = str(tmp_path / "vec.db")
    c = CoreSQLiteEngine(core).connect()
    apply_core_migrations(c)
    c.close()
    v = VecSQLiteEngine(vec).connect()
    apply_vec_schema(v)
    v.close()
    return core, vec


def test_health_report_ok(tmp_path):
    core, vec = _init_dbs(tmp_path)
    status, body = health_report(core, vec)
    assert status == 200
    assert body == {"status": "ok", "core": "ok", "vec": "ok"}


def test_health_report_degraded_when_vec_missing(tmp_path):
    core, vec = _init_dbs(tmp_path)
    conn = sqlite3.connect(vec)
    conn.execute("DROP TABLE chunk_embedding_index")
    conn.commit()
    conn.close()
    status, body = health_report(core, vec)
    assert status == 503
    assert body["status"] == "degraded"
    assert body["vec"] != "ok"
    assert body["reason"]


def test_probe_connections_are_closed(tmp_path, monkeypatch):
    # health_report must not leak probe connections (⛔ §7.2: probe conn closed).
    # sqlite3.Connection.close is read-only on instances, so we count via a
    # Connection subclass passed as the connect() factory.
    core, vec = _init_dbs(tmp_path)
    counters = {"opened": 0, "closed": 0}
    real_connect = sqlite3.connect

    class _Tracked(sqlite3.Connection):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            counters["opened"] += 1

        def close(self):
            counters["closed"] += 1
            super().close()

    def counting_connect(*args, **kwargs):
        kwargs["factory"] = _Tracked
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", counting_connect)
    health_report(core, vec)
    assert counters["opened"] == counters["closed"] >= 2


# --- run_startup_checks (P2-01) ---------------------------------------------

def test_startup_checks_apply_migrations(tmp_path):
    core = str(tmp_path / "core.db")
    vec = str(tmp_path / "vec.db")
    run_startup_checks(core, vec)
    conn = sqlite3.connect(core)
    try:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    finally:
        conn.close()
    assert {"users", "sessions"} <= tables


def test_startup_checks_fail_loud_on_unusable_path(tmp_path):
    # A path whose parent is a *file* (not a directory) must raise (fail-loud)
    # so the app refuses to boot rather than starting silently broken.
    blocker = tmp_path / "not_a_dir"
    blocker.write_text("i am a file")
    bad = str(blocker / "core.db")
    with pytest.raises(Exception):
        run_startup_checks(bad, str(tmp_path / "vec.db"))
