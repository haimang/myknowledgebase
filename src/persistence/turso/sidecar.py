"""Best-effort Turso diagnostic writer using a second BEGIN CONCURRENT connection."""

from __future__ import annotations

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


class TursoDiagnosticSidecar:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def insert(self, params: tuple[Any, ...]) -> None:
        import turso

        connection = turso.connect(str(self.database_path))
        try:
            try:
                mode = connection.execute("PRAGMA journal_mode=mvcc")
                row = mode.fetchone() if hasattr(mode, "fetchone") else None
                _ = row
            except Exception:
                pass
            try:
                connection.execute("BEGIN CONCURRENT")
            except Exception:
                connection.execute("BEGIN")
            try:
                connection.execute(
                    "INSERT INTO mkb_ops_diagnostic_logs "
                    "(log_uuid,team_uuid,trace_uuid,task_uuid,execution_uuid,process_uuid,log_level,log_code,"
                    "log_message,calling_module,calling_worker,payload_json,payload_digest,occurred_at,payload_extra) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'{}')",
                    params,
                )
                connection.execute("COMMIT")
            except Exception:
                try:
                    connection.execute("ROLLBACK")
                except Exception:
                    pass
                raise
        finally:
            try:
                connection.close()
            except Exception:
                pass
