"""Append-only domain/security event writers with redaction and transaction discipline."""

from __future__ import annotations

from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.persistence.ports import UnitOfWork
from src.runtime.security import redact


class DomainEventWriter:
    ALLOWED_TYPES = {
        "task.created",
        "task.status_changed",
        "task.cancel_requested",
        "task.retry_accepted",
        "task.soft_deleted",
        "execution.created",
        "execution.status_changed",
        "execution.waiting_entered",
        "execution.waiting_released",
        "process.materialized",
        "process.claimed",
        "process.status_changed",
        "process.outcome_accepted",
        "process.lease_recovered",
        "intake.snapshot_accepted",
        "intake.item_transitioned",
        "intake.candidate_sealed",
        "intake.candidate_accepted",
        "generation.artifact_accepted",
        "generation.pointer_cas",
        "generation.invocation_recorded",
        "gate.opened",
        "gate.decided",
        "gate.terminal",
        "object.registered",
        "object.ref_released",
        "object.deleted",
        "vector.upserted",
        "vector.soft_deleted",
        "vector.rebuild_started",
        "ops.repair_applied",
        "ops.readiness_changed",
        "ops.alert_raised",
        "ops.retention_policy_changed",
        "config.ops_reload",
        "config.override_applied",
        "registry.bootstrap_completed",
        "registry.digest_mismatch",
        "outbox.enqueued",
        "outbox.dead",
    }

    async def write(
        self,
        tx: UnitOfWork,
        *,
        team_uuid: str,
        trace_uuid: str,
        event_type: str,
        aggregate: str,
        summary: str,
        actor_kind: str = "system",
        task_uuid: str | None = None,
        execution_uuid: str | None = None,
        process_uuid: str | None = None,
        payload: dict[str, Any] | None = None,
        severity: str = "info",
    ) -> str:
        if event_type not in self.ALLOWED_TYPES:
            raise MkbError("OBS_EVENT_PAYLOAD_INVALID", "Unregistered domain event type", 422)
        if not team_uuid or not trace_uuid:
            raise MkbError("OBS_EVENT_PAYLOAD_INVALID", "Domain events require team and trace", 422)
        safe_payload = redact(payload or {})
        if not isinstance(safe_payload, dict) or len(summary) > 512:
            raise MkbError("OBS_EVENT_PAYLOAD_INVALID", "Domain event payload is invalid", 422)
        event_uuid = uuid7()
        now = utc_now()
        await tx.execute(
            "INSERT INTO mkb_domain_events "
            "(event_uuid,team_uuid,trace_uuid,event_type,aggregate,severity,task_uuid,execution_uuid,process_uuid,"
            "actor_kind,summary,payload_digest,payload_json,schema_version,occurred_at,recorded_at,payload_extra) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'{}')",
            (
                event_uuid,
                team_uuid,
                trace_uuid,
                event_type,
                aggregate,
                severity,
                task_uuid,
                execution_uuid,
                process_uuid,
                actor_kind,
                summary,
                stable_digest(safe_payload),
                __import__("json").dumps(safe_payload, separators=(",", ":")),
                "mkb.domain-event.v1",
                now,
                now,
            ),
        )
        return event_uuid


class SecurityAuditWriter:
    async def write_denied(
        self,
        tx: UnitOfWork,
        *,
        action: str,
        denial_code: str,
        summary: str,
        http_status: int,
        actor_fingerprint: str | None = None,
        team_uuid: str | None = None,
        trace_uuid: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> str:
        safe_payload = redact(payload or {})
        if not isinstance(safe_payload, dict):
            raise MkbError("SEC_AUDIT_WRITE_FAIL", "Security audit payload is invalid", 500)
        audit_uuid = uuid7()
        await tx.execute(
            "INSERT INTO mkb_security_audit_events "
            "(audit_uuid,team_uuid,trace_uuid,actor_kind,actor_fingerprint,action,outcome,denial_code,http_status,"
            "summary,payload_json,payload_digest,occurred_at,payload_extra) "
            "VALUES (?,?,?,?,? ,?,'denied',?,?,?,?,?,?,?,'{}')",
            (
                audit_uuid,
                team_uuid,
                trace_uuid,
                "anonymous" if actor_fingerprint is None else "internal_token",
                actor_fingerprint,
                action,
                denial_code,
                http_status,
                summary[:512],
                __import__("json").dumps(safe_payload, separators=(",", ":")),
                stable_digest(safe_payload),
                utc_now(),
            ),
        )
        return audit_uuid
