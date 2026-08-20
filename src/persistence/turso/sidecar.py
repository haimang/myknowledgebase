"""Best-effort Turso diagnostic writer on one serial connection.

A second ``BEGIN CONCURRENT`` connection per insert races the in-process
writer and has aborted the native engine (exit 134). This sidecar keeps a
single handle, a thread lock, and ``BEGIN IMMEDIATE`` — never flipping
``journal_mode`` on the live file.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

DIAGNOSTIC_LOG_CODES = frozenset(
    {
        "GEN_STRUCTURIZE_REJECT",
        "GEN_CLI_ENVELOPE",
        "GEN_CONSTRUCT_REJECT",
        "GEN_STAGE_TIMING",
    }
)

_INSERT_SQL = (
    "INSERT INTO mkb_ops_diagnostic_logs "
    "(log_uuid,team_uuid,trace_uuid,task_uuid,execution_uuid,process_uuid,log_level,log_code,"
    "log_message,calling_module,calling_worker,payload_json,payload_digest,occurred_at,payload_extra) "
    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'{}')"
)


class TursoDiagnosticSidecar:
    def __init__(self, database_path: Path, *, max_queue: int = 256) -> None:
        if max_queue < 1:
            raise ValueError("sidecar max_queue must be positive")
        self.database_path = database_path
        self.max_queue = max_queue
        self._lock = threading.Lock()
        self._connection: Any | None = None

    def _discard(self) -> None:
        connection = self._connection
        self._connection = None
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass

    def _connect(self) -> Any:
        if self._connection is None:
            import turso

            connection = turso.connect(str(self.database_path))
            try:
                connection.execute("PRAGMA busy_timeout = 5000")
            except Exception:
                pass
            self._connection = connection
        return self._connection

    def insert(self, params: tuple[Any, ...]) -> None:
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    connection.execute(_INSERT_SQL, params)
                    connection.execute("COMMIT")
                except Exception:
                    try:
                        connection.execute("ROLLBACK")
                    except Exception:
                        self._discard()
                    raise
            except Exception:
                self._discard()
                raise
