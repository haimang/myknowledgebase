"""FF-F2-T01 (P3-01): request-scoped connections must be closed.

先红后绿 ([Q7]): on the pre-fix ``return``-style deps the open-but-never-closed
connection count grows ~1:1 with the number of requests (RED). After F2-01
turns the deps into ``yield`` generators with ``finally: conn.close()`` the net
open-connection count stays flat (GREEN).

We avoid flaky OS fd scraping (⛔ §7.2) and deterministically count
``sqlite3.Connection`` open/close events by wrapping ``sqlite3.connect`` and
each connection's ``close``.
"""

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
    tmp = Path(tempfile.mkdtemp(prefix="smind-t01-"))
    os.environ["SMIND_CORE_DB_PATH"] = str(tmp / "core.db")
    os.environ["SMIND_VEC_DB_PATH"] = str(tmp / "vec.db")
    os.environ["SMIND_OBJECT_STORE_DIR"] = str(tmp / "objects")
    load_settings.cache_clear()
    _ensure_core_migrated.cache_clear()
    _ensure_vec_migrated.cache_clear()
    return tmp


def _register_login_team(client):
    reg = client.post(
        "/auth/register",
        json={"email": "t01@example.com", "password": "pw", "display_name": "t01"},
    )
    assert reg.status_code == 200, reg.text
    login = client.post("/auth/login", json={"email": "t01@example.com", "password": "pw"})
    assert login.status_code == 200, login.text
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    team = client.post(
        "/team/bootstrap", json={"name": "T01", "slug": "t01"}, headers=headers
    )
    assert team.status_code == 200, team.text
    return headers


def test_no_connection_leak_over_many_requests():
    _fresh_env()
    counters = {"opened": 0, "closed": 0}
    real_connect = sqlite3.connect

    # sqlite3.Connection.close is read-only on instances; count via a
    # Connection subclass used as the connect() factory (deterministic, no fd
    # scraping per ⛔ §7.2).
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

    sqlite3.connect = counting_connect  # type: ignore[assignment]
    try:
        with TestClient(create_app()) as client:
            headers = _register_login_team(client)
            baseline_open = counters["opened"] - counters["closed"]

            N = 60
            for _ in range(N):
                r = client.get("/management/workflows", headers=headers)
                assert r.status_code == 200, r.text

            net_open_after = counters["opened"] - counters["closed"]
    finally:
        sqlite3.connect = real_connect  # type: ignore[assignment]

    # Each request opens get_core_conn + get_vec_conn (get_auth_context reuses
    # the core dependency within a request). Net open connections must NOT grow
    # with N. A real leak would be ~2*N; allow a tiny constant slack.
    leak = net_open_after - baseline_open
    assert leak <= 2, (
        f"connection leak: {leak} net-open connections after {N} requests "
        f"(opened={counters['opened']}, closed={counters['closed']})"
    )
