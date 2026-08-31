"""Bounded operator reads and generation-fenced control commands.

This service is deliberately not a SQL console.  Every mutation either
delegates to an existing owner (the workflow outbox/cleanup service) or
returns a typed rejection, and every returned projection omits raw payloads.
"""

from __future__ import annotations

from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7, validate_external_uuid
from src.contracts.common.time import utc_now
from src.persistence.ports import PersistencePort
from src.runtime.security import redact
from src.runtime.workflow.runtime import WorkflowRuntime
from src.services.cleanup_jobs import CleanupJobService


class OperatorControlService:
    def __init__(
        self,
        persistence: PersistencePort,
        runtime: WorkflowRuntime,
        cleanup: CleanupJobService | None = None,
    ) -> None:
        self._persistence = persistence
        self._runtime = runtime
        self._cleanup = cleanup

    async def process(self, team_uuid: str, process_uuid: str) -> dict[str, Any]:
        validate_external_uuid(team_uuid, field="team_uuid")
        async with self._persistence.read_snapshot() as tx:
            row = await tx.fetchone(
                "SELECT process_uuid,team_uuid,execution_uuid,task_uuid,step_key,process_key,process_contract_version,"
                "status,row_revision,fencing_generation,lease_owner,delivery_count,retry_count,max_retries,error_class,"
                "error_code,failure_disposition,created_at,started_at,completed_at,updated_at,proof_ref,proof_digest "
                "FROM mkb_processes WHERE team_uuid=? AND process_uuid=?",
                (team_uuid, process_uuid),
            )
        if row is None:
            raise MkbError("PROCESS_NOT_FOUND", "Process was not found", 404)
        return {**row, "lease_owner": redact(row.get("lease_owner") or "")}

    async def execution(self, team_uuid: str, execution_uuid: str) -> dict[str, Any]:
        validate_external_uuid(team_uuid, field="team_uuid")
        async with self._persistence.read_snapshot() as tx:
            row = await tx.fetchone(
                "SELECT execution_uuid,team_uuid,task_uuid,generation,execution_role,target_kind,target_uuid,status,"
                "workflow_uuid,workflow_revision_uuid,compiled_digest,actual_binding_state,actual_binding_digest,"
                "phase_key,waiting_reason,current_process_uuid,total_process_count,active_process_count,"
                "succeeded_process_count,failed_process_count,cancelled_process_count,result_ref,publication_proof_ref,"
                "final_error_code,created_at,started_at,completed_at,updated_at "
                "FROM mkb_executions WHERE team_uuid=? AND execution_uuid=?",
                (team_uuid, execution_uuid),
            )
        if row is None:
            raise MkbError("EXECUTION_NOT_FOUND", "Execution was not found", 404)
        return row

    async def stop_execution(
        self,
        team_uuid: str,
        execution_uuid: str,
        *,
        expected_generation: int,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Fence an active execution tree into cancellation with a receipt."""

        if expected_generation < 1 or not idempotency_key:
            raise MkbError("COMMAND_FENCE_CONFLICT", "Execution command coordinates are invalid", 422)
        async with self._persistence.transaction() as tx:
            prior = await tx.fetchone(
                "SELECT command_receipt_uuid,decided_at FROM mkb_command_receipts WHERE team_uuid=? "
                "AND command_kind='execution.stop' AND target_kind='execution' AND target_uuid=? AND idempotency_key=?",
                (team_uuid, execution_uuid, idempotency_key),
            )
            if prior is not None:
                return {
                    "disposition": "replayed",
                    "command_receipt_uuid": prior["command_receipt_uuid"],
                    "execution_uuid": execution_uuid,
                    "decided_at": prior["decided_at"],
                }
            execution = await tx.fetchone(
                "SELECT * FROM mkb_executions WHERE team_uuid=? AND execution_uuid=?",
                (team_uuid, execution_uuid),
            )
            if execution is None:
                raise MkbError("EXECUTION_NOT_FOUND", "Execution was not found", 404)
            if int(execution["generation"]) != expected_generation:
                raise MkbError("COMMAND_FENCE_CONFLICT", "Execution generation is stale", 409)
            if execution["status"] in {"succeeded", "failed", "cancelled"}:
                raise MkbError("CONTROL_TERMINAL_IMMUTABLE", "Terminal execution cannot be stopped", 409)
            root = await self._runtime._execution(tx, execution["root_execution_uuid"])  # noqa: SLF001
            await self._runtime._cancel_execution_tree_tx(tx, root, include_root=True)  # noqa: SLF001
            now = utc_now()
            receipt_uuid = await self._receipt_tx(
                tx,
                team_uuid=team_uuid,
                command_kind="execution.stop",
                target_kind="execution",
                target_uuid=execution_uuid,
                idempotency_key=idempotency_key,
                expected_generation=expected_generation,
                observed_generation=int(execution["generation"]),
                result_ref=execution_uuid,
            )
        return {
            "disposition": "applied",
            "command_receipt_uuid": receipt_uuid,
            "execution_uuid": execution_uuid,
            "decided_at": now,
        }

    async def restart_process(
        self,
        team_uuid: str,
        process_uuid: str,
        *,
        expected_generation: int,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Restart an active Process by fencing its lease and creating a new generation."""

        if expected_generation < 0 or not idempotency_key:
            raise MkbError("COMMAND_FENCE_CONFLICT", "Process command coordinates are invalid", 422)
        async with self._persistence.transaction() as tx:
            prior = await tx.fetchone(
                "SELECT command_receipt_uuid,decided_at,result_ref FROM mkb_command_receipts WHERE team_uuid=? "
                "AND command_kind='process.restart' AND target_kind='process' AND target_uuid=? AND idempotency_key=?",
                (team_uuid, process_uuid, idempotency_key),
            )
            if prior is not None:
                return {
                    "disposition": "replayed",
                    "command_receipt_uuid": prior["command_receipt_uuid"],
                    "process_uuid": process_uuid,
                    "decided_at": prior["decided_at"],
                    "result_ref": prior["result_ref"],
                }
            process = await tx.fetchone(
                "SELECT * FROM mkb_processes WHERE team_uuid=? AND process_uuid=?",
                (team_uuid, process_uuid),
            )
            if process is None:
                raise MkbError("PROCESS_NOT_FOUND", "Process was not found", 404)
            if int(process["fencing_generation"]) != expected_generation:
                raise MkbError("COMMAND_FENCE_CONFLICT", "Process generation is stale", 409)
            if process["status"] in {"succeeded", "failed", "cancelled"}:
                raise MkbError("CONTROL_TERMINAL_IMMUTABLE", "Terminal process cannot be restarted in place", 409)
            now = utc_now()
            updated = await tx.execute(
                "UPDATE mkb_processes SET status='ready',claim_token_hash=NULL,lease_owner=NULL,lease_expires_at=NULL,"
                "heartbeat_at=NULL,fencing_generation=fencing_generation+1,row_revision=row_revision+1,updated_at=? "
                "WHERE team_uuid=? AND process_uuid=? AND fencing_generation=? "
                "AND status IN ('claimed','running','retry_wait')",
                (now, team_uuid, process_uuid, expected_generation),
            )
            if updated.rowcount != 1:
                raise MkbError("COMMAND_FENCE_CONFLICT", "Process changed before restart", 409)
            await self._runtime._enqueue_tx(  # noqa: SLF001
                tx,
                team_uuid,
                "wake_process",
                {"execution_uuid": process["execution_uuid"], "process_uuid": process_uuid},
                f"operator-restart:{process_uuid}:{expected_generation + 1}",
            )
            receipt_uuid = await self._receipt_tx(
                tx,
                team_uuid=team_uuid,
                command_kind="process.restart",
                target_kind="process",
                target_uuid=process_uuid,
                idempotency_key=idempotency_key,
                expected_generation=expected_generation,
                observed_generation=expected_generation + 1,
                result_ref=process_uuid,
            )
        return {
            "disposition": "applied",
            "command_receipt_uuid": receipt_uuid,
            "process_uuid": process_uuid,
            "result_ref": process_uuid,
            "decided_at": now,
        }

    async def cleanup(self, team_uuid: str, cleanup_job_uuid: str) -> dict[str, Any]:
        if self._cleanup is None:
            raise MkbError("CLEANUP_CONTROL_UNAVAILABLE", "Cleanup control is unavailable", 503)
        status = await self._cleanup.status(team_uuid, cleanup_job_uuid)
        job = status["job"]
        return {
            "cleanup_job_uuid": job["cleanup_job_uuid"],
            "intent_uuid": job["intent_uuid"],
            "team_uuid": job["team_uuid"],
            "intake_item_uuid": job["intake_item_uuid"],
            "item_epoch": int(job["item_epoch"]),
            "required_substrate_set_digest": job["required_substrate_set_digest"],
            "retention_until": job["retention_until"],
            "state": job["state"],
            "blocked_reason": job.get("blocked_reason"),
            "created_at": job["created_at"],
            "updated_at": job["updated_at"],
            "steps": [
                {
                    "substrate_kind": step["substrate_kind"],
                    "state": step["state"],
                    "proof_uuid": step["proof_uuid"],
                    "blocked_reason": step["blocked_reason"],
                }
                for step in status["steps"]
            ],
        }

    async def requeue_outbox(
        self,
        team_uuid: str,
        outbox_id: str,
        *,
        expected_generation: int,
        idempotency_key: str,
    ) -> dict[str, Any]:
        validate_external_uuid(team_uuid, field="team_uuid")
        if not idempotency_key or len(idempotency_key) > 256:
            raise MkbError("COMMAND_IDEMPOTENCY_INVALID", "Command idempotency key is invalid", 422)
        async with self._persistence.read_snapshot() as tx:
            row = await tx.fetchone("SELECT team_uuid FROM mkb_outbox WHERE outbox_id=?", (outbox_id,))
        if row is None:
            raise MkbError("OUTBOX_NOT_FOUND", "Outbox delivery was not found", 404)
        if row["team_uuid"] != team_uuid:
            raise MkbError("SEC_TEAM_SCOPE_VIOLATION", "Outbox delivery is outside the operator team", 403)
        return await self._runtime.requeue_dead_outbox(
            outbox_id,
            expected_generation=expected_generation,
            idempotency_key=idempotency_key,
        )

    async def resume_cleanup(
        self,
        team_uuid: str,
        cleanup_job_uuid: str,
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Resume only a due job under its durable row revision fence."""

        if self._cleanup is None:
            raise MkbError("CLEANUP_CONTROL_UNAVAILABLE", "Cleanup control is unavailable", 503)
        if expected_revision < 0 or not idempotency_key:
            raise MkbError("COMMAND_FENCE_CONFLICT", "Cleanup command coordinates are invalid", 422)
        async with self._persistence.transaction() as tx:
            prior = await tx.fetchone(
                "SELECT command_receipt_uuid,decided_at FROM mkb_command_receipts WHERE team_uuid=? AND command_kind=? "
                "AND target_kind='cleanup_job' AND target_uuid=? AND idempotency_key=?",
                (team_uuid, "cleanup.resume", cleanup_job_uuid, idempotency_key),
            )
            if prior is not None:
                return {
                    "disposition": "replayed",
                    "command_receipt_uuid": prior["command_receipt_uuid"],
                    "cleanup_job_uuid": cleanup_job_uuid,
                    "decided_at": prior["decided_at"],
                }
            row = await tx.fetchone(
                "SELECT row_revision,retention_until,state FROM mkb_cleanup_jobs WHERE team_uuid=? AND cleanup_job_uuid=?",
                (team_uuid, cleanup_job_uuid),
            )
            if row is None:
                raise MkbError("CLEANUP_JOB_NOT_FOUND", "Cleanup job was not found", 404)
            if int(row["row_revision"]) != expected_revision:
                raise MkbError("COMMAND_FENCE_CONFLICT", "Cleanup job revision is stale", 409)
            now = utc_now()
            updated = await tx.execute(
                "UPDATE mkb_cleanup_jobs SET state='pending',blocked_reason=NULL,row_revision=row_revision+1,updated_at=? "
                "WHERE team_uuid=? AND cleanup_job_uuid=? AND row_revision=? AND state IN ('blocked','failed')",
                (now, team_uuid, cleanup_job_uuid, expected_revision),
            )
            if updated.rowcount != 1:
                raise MkbError("COMMAND_FENCE_CONFLICT", "Cleanup job changed before resume", 409)
            receipt_uuid = await self._receipt_tx(
                tx,
                team_uuid=team_uuid,
                command_kind="cleanup.resume",
                target_kind="cleanup_job",
                target_uuid=cleanup_job_uuid,
                idempotency_key=idempotency_key,
                expected_generation=expected_revision,
                observed_generation=expected_revision,
                result_ref=cleanup_job_uuid,
            )
        return {
            "disposition": "applied",
            "command_receipt_uuid": receipt_uuid,
            "cleanup_job_uuid": cleanup_job_uuid,
            "decided_at": now,
        }

    @staticmethod
    async def _receipt_tx(
        tx: Any,
        *,
        team_uuid: str,
        command_kind: str,
        target_kind: str,
        target_uuid: str,
        idempotency_key: str,
        expected_generation: int,
        observed_generation: int,
        result_ref: str,
    ) -> str:
        existing = await tx.fetchone(
            "SELECT command_receipt_uuid FROM mkb_command_receipts WHERE team_uuid=? AND command_kind=? "
            "AND target_kind=? AND target_uuid=? AND idempotency_key=?",
            (team_uuid, command_kind, target_kind, target_uuid, idempotency_key),
        )
        if existing is not None:
            return str(existing["command_receipt_uuid"])
        receipt_uuid = uuid7()
        now = utc_now()
        await tx.execute(
            "INSERT INTO mkb_command_receipts(command_receipt_uuid,team_uuid,command_kind,target_kind,target_uuid,"
            "idempotency_key,command_fingerprint,expected_generation,observed_generation,disposition,result_ref,"
            "decided_at,first_applied_at) VALUES (?,?,?,?,?,?,?,?,?,'applied',?,?,?)",
            (
                receipt_uuid,
                team_uuid,
                command_kind,
                target_kind,
                target_uuid,
                idempotency_key,
                stable_digest({"command_kind": command_kind, "target_uuid": target_uuid, "idempotency_key": idempotency_key}),
                expected_generation,
                observed_generation,
                result_ref,
                now,
                now,
            ),
        )
        return receipt_uuid


__all__ = ["OperatorControlService"]
