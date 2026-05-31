"""FF-F2-T02 (P1-02): CLI commands must close core+vec connections.

Deterministic close-counting (no OS fd scraping, ⛔ §7.2). On the pre-fix
``_service`` the two connections were created and never closed; after F2-02
they are owned by a ``@contextlib.contextmanager`` and closed on command exit.
"""

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

from smind_cli.main import main
from smind_config.loader import load_settings
from storage_sqlite.engine import CoreSQLiteEngine
from storage_sqlite.migrations.runner import apply_core_migrations
from vector_sqlite_vec import VecSQLiteEngine, apply_vec_schema


def _fresh_env():
    tmp = Path(tempfile.mkdtemp(prefix="smind-t02-"))
    os.environ["SMIND_CORE_DB_PATH"] = str(tmp / "core.db")
    os.environ["SMIND_VEC_DB_PATH"] = str(tmp / "vec.db")
    os.environ["SMIND_OBJECT_STORE_DIR"] = str(tmp / "objects")
    load_settings.cache_clear()
    settings = load_settings()
    c = CoreSQLiteEngine(settings.core_db_path).connect()
    apply_core_migrations(c)
    c.close()
    v = VecSQLiteEngine(settings.vec_db_path).connect()
    apply_vec_schema(v)
    v.close()
    return tmp


def _run_counting(argv):
    counters = {"opened": 0, "closed": 0}
    real_connect = sqlite3.connect

    # sqlite3.Connection.close is read-only on instances; count via a
    # Connection subclass used as the connect() factory (⛔ §7.2: no fd scrape).
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
    old_argv = sys.argv
    sys.argv = ["smind-cli", *argv]
    try:
        rc = main()
    finally:
        sys.argv = old_argv
        sqlite3.connect = real_connect  # type: ignore[assignment]
    return rc, counters


def test_ops_health_closes_all_connections(capsys):
    _fresh_env()
    rc, counters = _run_counting(["ops-health", "--team-id", "none"])
    assert rc == 0
    assert counters["opened"] >= 2
    assert counters["closed"] == counters["opened"], (
        f"CLI ops-health leaked connections: "
        f"opened={counters['opened']} closed={counters['closed']}"
    )


def test_search_closes_all_connections(capsys):
    _fresh_env()
    rc, counters = _run_counting(["search", "--team-id", "none", "--query", "x"])
    assert rc == 0
    assert counters["opened"] >= 2
    assert counters["closed"] == counters["opened"], (
        f"CLI search leaked connections: "
        f"opened={counters['opened']} closed={counters['closed']}"
    )
