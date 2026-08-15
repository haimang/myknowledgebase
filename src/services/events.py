"""Append-only domain/security event writers with redaction and transaction discipline."""

from __future__ import annotations

import json
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.persistence.ports import UnitOfWork
from src.runtime.security import hash_remote_address, redact, safe_request_id


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
        "execution.prerequisite_released",
        "process.materialized",
        "process.dispatch_admitted",
        "process.claimed",
        "process.status_changed",
        "process.outcome_accepted",
        "process.lease_recovered",
        "process.cleanup_eligible",
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
        status_before: str | None = None,
        status_after: str | None = None,
    ) -> str:
        if event_type not in self.ALLOWED_TYPES:
            raise MkbError("OBS_EVENT_PAYLOAD_INVALID", "Unregistered domain event type", 422)
        if not team_uuid or not trace_uuid:
            raise MkbError("OBS_EVENT_PAYLOAD_INVALID", "Domain events require team and trace", 422)
        safe_payload = redact(payload or {})
        safe_summary = redact(summary)
        if not isinstance(safe_payload, dict) or not isinstance(safe_summary, str) or len(safe_summary) > 512:
            raise MkbError("OBS_EVENT_PAYLOAD_INVALID", "Domain event payload is invalid", 422)
        event_uuid = uuid7()
        now = utc_now()
        await tx.execute(
            "INSERT INTO mkb_domain_events "
            "(event_uuid,team_uuid,trace_uuid,event_type,aggregate,severity,task_uuid,execution_uuid,process_uuid,"
            "actor_kind,status_before,status_after,summary,payload_digest,payload_json,schema_version,occurred_at,"
            "recorded_at,payload_extra) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'{}')",
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
                status_before,
                status_after,
                safe_summary,
                stable_digest(safe_payload),
                json.dumps(safe_payload, separators=(",", ":")),
                "mkb.domain-event.v1",
                now,
                now,
            ),
        )
        return event_uuid


class SecurityAuditWriter:
    """Write non-business admission denials without accepting sensitive data.

    The writer deliberately has no dependency on Task/domain event services:
    a failed authentication or trust-boundary decision must never create a
    business event merely to leave an audit trail.
    """

    _ACTOR_KINDS = frozenset({"anonymous", "internal_token", "system", "operator"})

    async def write_denied(
        self,
        tx: UnitOfWork,
        *,
        action: str,
        denial_code: str,
        summary: str,
        http_status: int,
        actor_fingerprint: str | None = None,
        actor_kind: str | None = None,
        team_uuid: str | None = None,
        trace_uuid: str | None = None,
        request_id: str | None = None,
        target_kind: str | None = None,
        target_uuid: str | None = None,
        remote_ip: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> str:
        safe_payload = redact(payload or {})
        safe_summary = redact(summary)
        effective_actor_kind = actor_kind or ("anonymous" if actor_fingerprint is None else "internal_token")
        if (
            not isinstance(safe_payload, dict)
            or not isinstance(safe_summary, str)
            or effective_actor_kind not in self._ACTOR_KINDS
            or len(safe_summary) > 512
        ):
            raise MkbError("SEC_AUDIT_WRITE_FAIL", "Security audit payload is invalid", 500)
        encoded_payload = json.dumps(safe_payload, separators=(",", ":"))
        if len(encoded_payload.encode("utf-8")) > 64 * 1024:
            raise MkbError("SEC_AUDIT_WRITE_FAIL", "Security audit payload is invalid", 500)
        audit_uuid = uuid7()
        await tx.execute(
            "INSERT INTO mkb_security_audit_events "
            "(audit_uuid,team_uuid,trace_uuid,request_id,actor_kind,actor_fingerprint,action,outcome,denial_code,"
            "http_status,target_kind,target_uuid,remote_addr_hash,summary,payload_json,payload_digest,occurred_at,"
            "payload_extra) VALUES (?,?,?,?,?,?,?,'denied',?,?,?,?,?,?,?,?,?,'{}')",
            (
                audit_uuid,
                team_uuid,
                trace_uuid,
                safe_request_id(request_id),
                effective_actor_kind,
                actor_fingerprint,
                action,
                denial_code,
                http_status,
                target_kind[:128] if target_kind else None,
                target_uuid[:128] if target_uuid else None,
                hash_remote_address(remote_ip),
                safe_summary[:512],
                encoded_payload,
                stable_digest(safe_payload),
                utc_now(),
            ),
        )
        return audit_uuid
