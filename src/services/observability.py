"""S15 bounded read and retention services.

The observability tables are evidence and diagnostics, never a second task or
workflow state machine.  This module deliberately offers only tenant-scoped,
cursor-bounded reads plus a periodic, append-only-retention delete protocol.
It has no repair or arbitrary SQL surface.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7, validate_external_uuid
from src.contracts.common.time import utc_now
from src.persistence.ports import PersistencePort
from src.runtime.metrics import MetricRegistry
from src.runtime.security import redact


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _encode_cursor(kind: str, **fields: Any) -> str:
    body = _json({"kind": kind, **fields}).encode("utf-8")
    return base64.urlsafe_b64encode(body).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str, *, kind: str, filter_digest: str) -> dict[str, Any]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (ValueError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError) as exc:
        raise MkbError("OBS_TIMELINE_QUERY_FAIL", "Observability cursor is invalid", 422) from exc
    if not isinstance(value, dict) or value.get("kind") != kind or value.get("filter_digest") != filter_digest:
        raise MkbError("OBS_TIMELINE_QUERY_FAIL", "Observability cursor is invalid", 422)
    if not isinstance(value.get("occurred_at"), str) or not isinstance(value.get("row_uuid"), str):
        raise MkbError("OBS_TIMELINE_QUERY_FAIL", "Observability cursor is invalid", 422)
    return value


def _bounded_limit(limit: int) -> int:
    if not 1 <= limit <= 200:
        raise MkbError("OBS_TIMELINE_QUERY_FAIL", "Observability limit must be between 1 and 200", 422)
    return limit


def _payload(value: str | None) -> dict[str, Any]:
    """Re-redact stored JSON before it crosses the controlled operator port."""

    try:
        parsed = json.loads(value or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return {"disposition": "malformed"}
    safe = redact(parsed)
    return safe if isinstance(safe, dict) else {"disposition": "malformed"}


_DIAGNOSTIC_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
_DIAGNOSTIC_LEVELS = frozenset({"debug", "info", "warn", "error"})


class DiagnosticSink:
    """Best-effort structured diagnostics with an observable failure path.

    Diagnostic evidence may never decide a business outcome.  Consequently a
    write failure is deliberately swallowed after it is made visible through
    the closed metric catalogue and one safe stderr line.  The sink accepts no
    arbitrary SQL or file handle and redacts before persisting.
    """

    def __init__(
        self,
        persistence: PersistencePort,
        metrics: MetricRegistry,
        *,
        stderr: Callable[[str], None] | None = None,
    ) -> None:
        self._persistence = persistence
        self._metrics = metrics
        self._stderr = stderr or self._write_stderr
        self._attempted = 0
        self._missing_trace = 0

    async def write(
        self,
        *,
        log_code: str,
        message: str,
        calling_module: str,
        log_level: str = "error",
        team_uuid: str | None = None,
        trace_uuid: str | None = None,
        task_uuid: str | None = None,
        execution_uuid: str | None = None,
        process_uuid: str | None = None,
        calling_worker: str = "mkb-leaf",
        payload: dict[str, Any] | None = None,
    ) -> bool:
        """Persist one bounded diagnostic record, returning ``False`` on drop.

        ``False`` is intentional: callers must not turn a non-authoritative
        diagnostic failure into a second business-state transition.
        """

        safe = self._validate_entry(
            log_code=log_code,
            message=message,
            calling_module=calling_module,
            log_level=log_level,
            team_uuid=team_uuid,
            trace_uuid=trace_uuid,
            task_uuid=task_uuid,
            execution_uuid=execution_uuid,
            process_uuid=process_uuid,
            calling_worker=calling_worker,
            payload=payload,
        )
        if safe is None:
            self._drop("invalid_entry", log_code)
            return False

        self._attempted += 1
        if safe["trace_uuid"] is None:
            self._missing_trace += 1
        self._metrics.set(
            "mkb_diagnostic_missing_trace_ratio",
            self._missing_trace / self._attempted,
        )
        try:
            async with self._persistence.transaction() as tx:
                await tx.execute(
                    "INSERT INTO mkb_ops_diagnostic_logs "
                    "(log_uuid,team_uuid,trace_uuid,task_uuid,execution_uuid,process_uuid,log_level,log_code,"
                    "log_message,calling_module,calling_worker,payload_json,payload_digest,occurred_at,payload_extra) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'{}')",
                    (
                        uuid7(),
                        safe["team_uuid"],
                        safe["trace_uuid"],
                        safe["task_uuid"],
                        safe["execution_uuid"],
                        safe["process_uuid"],
                        safe["log_level"],
                        safe["log_code"],
                        safe["message"],
                        safe["calling_module"],
                        safe["calling_worker"],
                        safe["payload_json"],
                        stable_digest(safe["payload"]),
                        utc_now(),
                    ),
                )
        except Exception:
            self._drop("append_fail", safe["log_code"])
            return False
        return True

    @staticmethod
    def _validate_entry(
        *,
        log_code: str,
        message: str,
        calling_module: str,
        log_level: str,
        team_uuid: str | None,
        trace_uuid: str | None,
        task_uuid: str | None,
        execution_uuid: str | None,
        process_uuid: str | None,
        calling_worker: str,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if (
            not isinstance(log_code, str)
            or _DIAGNOSTIC_IDENTIFIER.fullmatch(log_code) is None
            or not isinstance(calling_module, str)
            or _DIAGNOSTIC_IDENTIFIER.fullmatch(calling_module) is None
            or not isinstance(calling_worker, str)
            or _DIAGNOSTIC_IDENTIFIER.fullmatch(calling_worker) is None
            or log_level not in _DIAGNOSTIC_LEVELS
            or not isinstance(message, str)
        ):
            return None
        identifiers = (team_uuid, trace_uuid, task_uuid, execution_uuid, process_uuid)
        if any(value is not None and (not isinstance(value, str) or len(value) > 128) for value in identifiers):
            return None
        safe_message = redact(message)
        safe_payload = redact(payload or {})
        if not isinstance(safe_message, str) or not isinstance(safe_payload, dict) or len(safe_message) > 1024:
            return None
        try:
            payload_json = _json(safe_payload)
        except (TypeError, ValueError):
            return None
        if len(payload_json.encode("utf-8")) > 64 * 1024:
            return None
        return {
            "log_code": log_code,
            "message": safe_message,
            "calling_module": calling_module,
            "calling_worker": calling_worker,
            "log_level": log_level,
            "team_uuid": team_uuid,
            "trace_uuid": trace_uuid,
            "task_uuid": task_uuid,
            "execution_uuid": execution_uuid,
            "process_uuid": process_uuid,
            "payload": safe_payload,
            "payload_json": payload_json,
        }

    def _drop(self, reason: str, log_code: object) -> None:
        self._metrics.increment("mkb_diagnostic_drop_total", reason=reason)
        # Never write the message, payload, IDs, or raw exception here: the
        # fallback must itself obey S16's redaction boundary.
        try:
            code = log_code if isinstance(log_code, str) and _DIAGNOSTIC_IDENTIFIER.fullmatch(log_code) else "invalid"
            self._stderr(_json({"event": "OBS_DIAG_APPEND_FAIL", "reason": reason, "log_code": code}))
        except Exception:
            # stderr failure is also observable without allowing diagnostics to
            # throw into a business transaction.
            self._metrics.increment("mkb_diagnostic_drop_total", reason="stderr_fail")

    @staticmethod
    def _write_stderr(line: str) -> None:
        print(line, file=sys.stderr)


class ObservabilityReadService:
    """Read only the caller's team's operational evidence in bounded pages."""

    def __init__(self, persistence: PersistencePort) -> None:
        self._persistence = persistence

    async def timeline_by_trace(
        self, team_uuid: str, trace_uuid: str, *, limit: int = 50, cursor: str | None = None
    ) -> tuple[list[dict[str, Any]], str | None]:
        team_uuid = validate_external_uuid(team_uuid, field="team_uuid")
        trace_uuid = validate_external_uuid(trace_uuid, field="trace_uuid")
        return await self._timeline(
            team_uuid=team_uuid,
            kind="trace-timeline",
            predicate="trace_uuid=?",
            predicate_params=(trace_uuid,),
            filter_material={"team_uuid": team_uuid, "trace_uuid": trace_uuid},
            limit=limit,
            cursor=cursor,
        )

    async def timeline_by_task(
        self, team_uuid: str, task_uuid: str, *, limit: int =50, cursor: str | None = None
    ) -> tuple[list[dict[str, Any]], str | None]:
        team_uuid = validate_external_uuid(team_uuid, field="team_uuid")
        task_uuid = validate_external_uuid(task_uuid, field="task_uuid")
        return await self._timeline(
            team_uuid=team_uuid,
            kind="task-timeline",
            predicate="task_uuid=?",
            predicate_params=(task_uuid,),
            filter_material={"team_uuid": team_uuid, "task_uuid": task_uuid},
            limit=limit,
            cursor=cursor,
        )

    async def _timeline(
        self,
        *,
        team_uuid: str,
        kind: str,
        predicate: str,
        predicate_params: tuple[str, ...],
        filter_material: dict[str, str],
        limit: int,
        cursor: str | None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        limit = _bounded_limit(limit)
        filter_digest = stable_digest(filter_material)
        cursor_row = _decode_cursor(cursor, kind=kind, filter_digest=filter_digest) if cursor else None
        boundary_sql = ""
        boundary_params: tuple[Any, ...] = ()
        if cursor_row is not None:
            boundary_sql = " AND (occurred_at<? OR (occurred_at=? AND event_uuid<?))"
            boundary_params = (cursor_row["occurred_at"], cursor_row["occurred_at"], cursor_row["row_uuid"])
        try:
            async with self._persistence.transaction() as tx:
                rows = await tx.fetchall(
                    "SELECT event_uuid,trace_uuid,event_type,aggregate,severity,task_uuid,execution_uuid,process_uuid,"
                    "subject_kind,subject_uuid,actor_kind,summary,payload_digest,occurred_at,recorded_at "
                    "FROM mkb_domain_events "
                    f"WHERE team_uuid=? AND {predicate}{boundary_sql} "
                    "ORDER BY occurred_at DESC,event_uuid DESC LIMIT ?",
                    (team_uuid, *predicate_params, *boundary_params, limit + 1),
                )
        except MkbError:
            raise
        except Exception as exc:
            raise MkbError("OBS_TIMELINE_QUERY_FAIL", "Observability timeline is unavailable", 503) from exc
        page = rows[:limit]
        next_cursor = None
        if len(rows) > limit and page:
            tail = page[-1]
            next_cursor = _encode_cursor(
                kind,
                filter_digest=filter_digest,
                occurred_at=tail["occurred_at"],
                row_uuid=tail["event_uuid"],
            )
        return [self._event_view(row) for row in page], next_cursor

    @staticmethod
    def _event_view(row: dict[str, Any]) -> dict[str, Any]:
        # These are an internal, token-and-network-protected operator view.
        # They are intentionally absent from the caller-facing Task API.
        return {
            "event_uuid": row["event_uuid"],
            "trace_uuid": row["trace_uuid"],
            "event_type": row["event_type"],
            "aggregate": row["aggregate"],
            "severity": row["severity"],
            "task_uuid": row["task_uuid"],
            "execution_uuid": row["execution_uuid"],
            "process_uuid": row["process_uuid"],
            "subject_kind": row["subject_kind"],
            "subject_uuid": row["subject_uuid"],
            "actor_kind": row["actor_kind"],
            "summary": redact(row["summary"]),
            # The default operator projection deliberately returns only the
            # immutable digest.  Full event payload requires a separately
            # governed debug surface and is not part of the v1 read port.
            "payload_digest": row["payload_digest"],
            "occurred_at": row["occurred_at"],
            "recorded_at": row["recorded_at"],
        }

    async def dead_outbox(
        self, team_uuid: str, *, kind: str | None = None, limit: int = 50, cursor: str | None = None
    ) -> tuple[list[dict[str, Any]], str | None]:
        team_uuid = validate_external_uuid(team_uuid, field="team_uuid")
        limit = _bounded_limit(limit)
        if kind is not None and (not kind or len(kind) > 128):
            raise MkbError("OBS_TIMELINE_QUERY_FAIL", "Outbox kind filter is invalid", 422)
        filter_digest = stable_digest({"team_uuid": team_uuid, "kind": kind})
        cursor_row = _decode_cursor(cursor, kind="dead-outbox", filter_digest=filter_digest) if cursor else None
        clauses = ["team_uuid=?", "status='dead'"]
        params: list[Any] = [team_uuid]
        if kind is not None:
            clauses.append("kind=?")
            params.append(kind)
        if cursor_row is not None:
            clauses.append("(updated_at<? OR (updated_at=? AND outbox_id<?))")
            params.extend((cursor_row["occurred_at"], cursor_row["occurred_at"], cursor_row["row_uuid"]))
        try:
            async with self._persistence.transaction() as tx:
                rows = await tx.fetchall(
                    "SELECT outbox_id,team_uuid,kind,status,attempts,last_error,created_at,updated_at FROM mkb_outbox WHERE "
                    + " AND ".join(clauses)
                    + " ORDER BY updated_at DESC,outbox_id DESC LIMIT ?",
                    (*params, limit + 1),
                )
        except MkbError:
            raise
        except Exception as exc:
            raise MkbError("OBS_TIMELINE_QUERY_FAIL", "Observability dead-letter view is unavailable", 503) from exc
        page = rows[:limit]
        next_cursor = None
        if len(rows) > limit and page:
            tail = page[-1]
            next_cursor = _encode_cursor(
                "dead-outbox",
                filter_digest=filter_digest,
                occurred_at=tail["updated_at"],
                row_uuid=tail["outbox_id"],
            )
        return [
            {
                "outbox_id": row["outbox_id"],
                "team_uuid": row["team_uuid"],
                "kind": row["kind"],
                "status": row["status"],
                "attempts": row["attempts"],
                "last_error": redact(row["last_error"] or ""),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in page
        ], next_cursor

    async def security_audit(
        self, team_uuid: str, *, limit: int = 50, cursor: str | None = None
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Return only one team's redacted admission audit evidence."""

        team_uuid = validate_external_uuid(team_uuid, field="team_uuid")
        limit = _bounded_limit(limit)
        filter_digest = stable_digest({"team_uuid": team_uuid})
        cursor_row = _decode_cursor(cursor, kind="security-audit", filter_digest=filter_digest) if cursor else None
        boundary_sql = ""
        params: tuple[Any, ...] = (team_uuid,)
        if cursor_row is not None:
            boundary_sql = " AND (occurred_at<? OR (occurred_at=? AND audit_uuid<?))"
            params = (*params, cursor_row["occurred_at"], cursor_row["occurred_at"], cursor_row["row_uuid"])
        try:
            async with self._persistence.transaction() as tx:
                rows = await tx.fetchall(
                    "SELECT audit_uuid,trace_uuid,actor_kind,action,outcome,denial_code,http_status,target_kind,target_uuid,"
                    "summary,payload_json,occurred_at FROM mkb_security_audit_events WHERE team_uuid=?"
                    + boundary_sql
                    + " ORDER BY occurred_at DESC,audit_uuid DESC LIMIT ?",
                    (*params, limit + 1),
                )
        except MkbError:
            raise
        except Exception as exc:
            raise MkbError("OBS_TIMELINE_QUERY_FAIL", "Observability audit view is unavailable", 503) from exc
        page = rows[:limit]
        next_cursor = None
        if len(rows) > limit and page:
            tail = page[-1]
            next_cursor = _encode_cursor(
                "security-audit",
                filter_digest=filter_digest,
                occurred_at=tail["occurred_at"],
                row_uuid=tail["audit_uuid"],
            )
        return [
            {
                "audit_uuid": row["audit_uuid"],
                "trace_uuid": row["trace_uuid"],
                "actor_kind": row["actor_kind"],
                "action": row["action"],
                "outcome": row["outcome"],
                "denial_code": row["denial_code"],
                "http_status": row["http_status"],
                "target_kind": row["target_kind"],
                "target_uuid": row["target_uuid"],
                "summary": redact(row["summary"]),
                "payload": _payload(row["payload_json"]),
                "occurred_at": row["occurred_at"],
            }
            for row in page
        ], next_cursor


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    domain_events_days: int = 90
    diagnostic_logs_days: int = 14
    security_audit_days: int = 180
    batch_size: int = 1_000

    def __post_init__(self) -> None:
        if any(days < 1 or days > 36_500 for days in self._days()) or not 1 <= self.batch_size <= 10_000:
            raise ValueError("retention policy values are outside safe bounds")

    def _days(self) -> tuple[int, int, int]:
        return self.domain_events_days, self.diagnostic_logs_days, self.security_audit_days


@dataclass(frozen=True, slots=True)
class RetentionResult:
    deleted: dict[str, int]


class ObservabilityRetentionService:
    """Delete only expired evidence in bounded, independently committed batches."""

    _TABLES = (
        ("mkb_domain_events", "event_uuid", "domain_events_days"),
        ("mkb_ops_diagnostic_logs", "log_uuid", "diagnostic_logs_days"),
        ("mkb_security_audit_events", "audit_uuid", "security_audit_days"),
    )

    def __init__(
        self,
        persistence: PersistencePort,
        metrics: MetricRegistry,
        *,
        policy: RetentionPolicy | None = None,
        clock: Callable[[], datetime] | None = None,
        diagnostics: DiagnosticSink | None = None,
    ) -> None:
        self._persistence = persistence
        self._metrics = metrics
        self._policy = policy or RetentionPolicy()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._diagnostics = diagnostics or DiagnosticSink(persistence, metrics)

    async def run_once(self) -> RetentionResult:
        try:
            deleted: dict[str, int] = {}
            for table, primary_key, policy_field in self._TABLES:
                days = getattr(self._policy, policy_field)
                cutoff = self._timestamp(self._clock() - timedelta(days=days))
                count = await self._delete_batch(table, primary_key, cutoff)
                deleted[table] = count
                if count:
                    self._metrics.increment("mkb_retention_delete_rows_total", count, table=table)
        except Exception as exc:
            self._metrics.set("mkb_retention_job_success", 0)
            self._metrics.increment("mkb_retention_job_fail_total")
            await self._diagnostics.write(
                log_code="OBS_RETENTION_JOB_FAIL",
                message="Observability retention batch failed; no business state was changed",
                calling_module="observability.retention",
                log_level="error",
            )
            # The caller decides its retry interval.  A safe typed error keeps
            # a manual/internal invocation observable without leaking a driver
            # message; the app loop can retry because no business rows were
            # touched by this service.
            raise MkbError("OBS_RETENTION_JOB_FAIL", "Observability retention batch failed", 503) from exc
        self._metrics.set("mkb_retention_job_success", 1)
        return RetentionResult(deleted=deleted)

    async def _delete_batch(self, table: str, primary_key: str, cutoff: str) -> int:
        async with self._persistence.transaction() as tx:
            rows = await tx.fetchall(
                f"SELECT {primary_key} FROM {table} WHERE occurred_at<? ORDER BY occurred_at,{primary_key} LIMIT ?",
                (cutoff, self._policy.batch_size),
            )
            if not rows:
                return 0
            identifiers = tuple(row[primary_key] for row in rows)
            placeholders = ",".join("?" for _ in identifiers)
            result = await tx.execute(f"DELETE FROM {table} WHERE {primary_key} IN ({placeholders})", identifiers)
            return int(result.rowcount)

    @staticmethod
    def _timestamp(value: datetime) -> str:
        return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


__all__ = [
    "DiagnosticSink",
    "ObservabilityReadService",
    "ObservabilityRetentionService",
    "RetentionPolicy",
    "RetentionResult",
]
