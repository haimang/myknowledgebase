from __future__ import annotations

import sqlite3
from pathlib import Path


class CoreSQLiteEngine:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Autocommit: all transaction control is explicit via BEGIN IMMEDIATE
        # in the workflow_core multi-write helpers (CR-2 R2, F1-04).
        conn.isolation_level = None
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        return conn
