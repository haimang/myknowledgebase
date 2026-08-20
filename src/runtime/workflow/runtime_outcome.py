"""runtime outcome"""

from __future__ import annotations

import json
from typing import Any

from src.contracts.common.errors import ConflictError, MkbError
from src.contracts.common.ids import stable_digest
from src.contracts.common.models import ExecutionStatus, ProcessStatus
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessOutcome
from src.contracts.workflow.models import (
    WorkflowOutcomeSelector,
    WorkflowTerminalKind,
)
from src.persistence.ports import UnitOfWork
from src.runtime.workflow.constants import (
    _TERMINAL_EXECUTION_STATUSES,
    _TERMINAL_PROCESS_STATUSES,
)
from src.runtime.workflow.helpers import (
    _add_seconds,
    canonical_outcome_digest,
)


def _safe_persisted_error(message: str) -> str:
    from src.runtime.security import redact

    redacted = redact(message)
    text = redacted if isinstance(redacted, str) else str(redacted)
    return text[:512]


class WorkflowOutcomeMixin:
    """runtime outcome"""

    async def accept_outcome(self, outcome: ProcessOutcome) -> bool:
        """Validate and linearize one handler outcome.

        A duplicate accepted outcome is a no-op.  A different or stale outcome
        raises a conflict and never changes durable state.
        """

        if canonical_outcome_digest(outcome) != outcome.outcome_digest:
            raise ConflictError("outcome-digest-invalid", "Process outcome digest does not match its canonical payload")
        now = utc_now()
        async with self.persistence.transaction() as tx:
            process = await self._process_with_execution(tx, outcome.process_uuid)
            self._assert_outcome_identity(process, outcome)
            if process["status"] in _TERMINAL_PROCESS_STATUSES:
                if process["accepted_outcome_digest"] == outcome.outcome_digest:
                    return False
                raise ConflictError("stale-process-outcome", "A terminal Process cannot accept a different outcome")
            if process["status"] != ProcessStatus.RUNNING.value:
                raise ConflictError("process-not-running", "Process must be running to accept an outcome")
            execution = await self._execution(tx, process["execution_uuid"])
            if execution["status"] == ExecutionStatus.CANCELLING.value:
                raise ConflictError("execution-cancelling", "Cancellation fenced this process outcome")

            if outcome.disposition == "succeeded":
                if not all(
                    (
                        outcome.output_manifest_ref,
                        outcome.output_manifest_digest,
                        outcome.proof_ref,
                        outcome.proof_digest,
                    )
                ):
                    await self._fail_process_tx(
                        tx,
                        process,
                        error_code="outcome-proof-invalid",
                        error_message="A successful process outcome requires typed output and completion proof",
                        failure_disposition="integrity",
                    )
                    await self._route_after_terminal_process_tx(
                        tx,
                        execution,
                        process,
                        WorkflowOutcomeSelector.FAILED,
                        {},
                        "outcome-proof-invalid",
                    )
                    await self._refresh_execution_counts_tx(tx, execution["execution_uuid"])
                    return True
                if self.outcome_committer is not None:
                    # The only caller-owned business mutation in this engine
                    # path: artifact/proof registration is linearized with the
                    # Process success, and cannot survive a later fence/CAS
                    # failure because both use this same UnitOfWork.
                    await self.outcome_committer.validate_and_commit(
                        tx,
                        self._command_from_process(process),
                        outcome,
                    )
                updated = await tx.execute(
                    "UPDATE mkb_processes SET status='succeeded',accepted_outcome_digest=?,output_manifest_ref=?,"
                    "output_manifest_digest=?,proof_ref=?,proof_digest=?,error_code=NULL,error_message=NULL,"
                    "claim_token_hash=NULL,lease_owner=NULL,"
                    "lease_expires_at=NULL,heartbeat_at=NULL,completed_at=?,row_revision=row_revision+1,updated_at=? "
                    "WHERE process_uuid=? AND status='running' AND fencing_generation=?",
                    (
                        outcome.outcome_digest,
                        outcome.output_manifest_ref,
                        outcome.output_manifest_digest,
                        outcome.proof_ref,
                        outcome.proof_digest,
                        now,
                        now,
                        process["process_uuid"],
                        outcome.fencing_generation,
                    ),
                )
                if updated.rowcount != 1:
                    raise ConflictError("stale-process-fence", "Process outcome fence is no longer current")
                accepted_process = await self._process_with_execution(tx, process["process_uuid"])
                await self._record_event_tx(
                    tx,
                    execution=accepted_process,
                    event_type="process.outcome_accepted",
                    aggregate="process",
                    summary="Process success outcome accepted",
                    process_uuid=process["process_uuid"],
                    status_before=ProcessStatus.RUNNING.value,
                    status_after=ProcessStatus.SUCCEEDED.value,
                    payload={"outcome_digest": outcome.outcome_digest, "proof_digest": outcome.proof_digest},
                )
                await self._route_after_terminal_process_tx(
                    tx,
                    execution,
                    accepted_process,
                    WorkflowOutcomeSelector.SUCCEEDED,
                    outcome.payload_extra,
                    None,
                )
            elif outcome.disposition == "retryable_failure":
                if not outcome.error_code or not outcome.error_message:
                    raise MkbError(
                        "outcome-error-required",
                        "A retryable failure must include a bounded error code and message",
                        422,
                    )
                if process["retry_count"] < process["max_retries"]:
                    import random

                    cap = max(float(self.retry_delay_seconds), 0.001) * (2 ** int(process["retry_count"]))
                    due = _add_seconds(now, random.uniform(0.0, cap))
                    updated = await tx.execute(
                        "UPDATE mkb_processes SET status='retry_wait',accepted_outcome_digest=?,retry_count=retry_count+1,"
                        "next_retry_at=?,available_at=?,last_failure_retryability=1,error_code=?,error_message=?,"
                        "failure_disposition='retryable',claim_token_hash=NULL,lease_owner=NULL,lease_expires_at=NULL,"
                        "heartbeat_at=NULL,dispatch_admitted=0,dispatch_pool=NULL,dispatch_enqueued_at=NULL,"
                        "row_revision=row_revision+1,updated_at=? "
                        "WHERE process_uuid=? AND status='running' AND fencing_generation=?",
                        (
                            outcome.outcome_digest,
                            due,
                            due,
                            outcome.error_code,
                            _safe_persisted_error(outcome.error_message),
                            now,
                            process["process_uuid"],
                            outcome.fencing_generation,
                        ),
                    )
                    if updated.rowcount != 1:
                        raise ConflictError("stale-process-fence", "Process outcome fence is no longer current")
                    await tx.execute(
                        "UPDATE mkb_executions SET status='waiting',waiting_reason='retry_due',waiting_ref=?,next_wake_at=?,"
                        "row_revision=row_revision+1,updated_at=? "
                        "WHERE execution_uuid=? AND status IN ('ready','running','waiting')",
                        (process["process_uuid"], due, now, execution["execution_uuid"]),
                    )
                    await self._enqueue_tx(
                        tx,
                        process["team_uuid"],
                        "wake_process",
                        {"execution_uuid": process["execution_uuid"], "process_uuid": process["process_uuid"]},
                        f"retry-process:{process['process_uuid']}:{process['retry_count'] + 1}",
                    )
                    await self._record_event_tx(
                        tx,
                        execution=process,
                        event_type="process.status_changed",
                        aggregate="process",
                        summary="Retryable process failure scheduled for durable retry",
                        process_uuid=process["process_uuid"],
                        status_before=ProcessStatus.RUNNING.value,
                        status_after=ProcessStatus.RETRY_WAIT.value,
                        payload={"retry_count": process["retry_count"] + 1, "next_retry_at": due},
                    )
                else:
                    await self._fail_process_tx(
                        tx,
                        process,
                        error_code="retry-exhausted",
                        error_message=outcome.error_message,
                        failure_disposition="retry-exhausted",
                        accepted_outcome_digest=outcome.outcome_digest,
                    )
                    await self._route_after_terminal_process_tx(
                        tx, execution, process, WorkflowOutcomeSelector.FAILED, {}, "retry-exhausted"
                    )
            elif outcome.disposition == "failed":
                if not outcome.error_code or not outcome.error_message:
                    raise MkbError(
                        "outcome-error-required", "A failed outcome must include a bounded error code and message", 422
                    )
                await self._fail_process_tx(
                    tx,
                    process,
                    error_code=outcome.error_code,
                    error_message=outcome.error_message,
                    failure_disposition="non-retryable",
                    accepted_outcome_digest=outcome.outcome_digest,
                    payload_extra=outcome.payload_extra,
                )
                await self._route_after_terminal_process_tx(
                    tx, execution, process, WorkflowOutcomeSelector.FAILED, outcome.payload_extra, outcome.error_code
                )
            else:
                # Waiting is an Execution-level, typed durable condition.  A
                # generic stage cannot invent it through a Process outcome.
                raise MkbError(
                    "unsupported-process-outcome",
                    "Stages must return succeeded, failed, or retryable_failure; control waits are engine-owned",
                    422,
                )
            await self._refresh_execution_counts_tx(tx, execution["execution_uuid"])
            return True


    async def promote_due_retries(self, *, limit: int = 128) -> int:
        """Move durable due retries back to ``ready`` without consuming a claim."""

        if limit < 1:
            return 0
        now = utc_now()
        promoted = 0
        async with self.persistence.transaction() as tx:
            rows = await tx.fetchall(
                "SELECT p.*,e.trace_uuid FROM mkb_processes AS p JOIN mkb_executions AS e "
                "ON e.execution_uuid=p.execution_uuid AND e.team_uuid=p.team_uuid "
                "WHERE p.status='retry_wait' AND p.next_retry_at<=? AND e.status NOT IN ('cancelling','cancelled','failed','succeeded') "
                "ORDER BY p.next_retry_at ASC,p.process_uuid ASC LIMIT ?",
                (now, limit),
            )
            for process in rows:
                updated = await tx.execute(
                    "UPDATE mkb_processes SET status='ready',available_at=?,next_retry_at=NULL,"
                    "row_revision=row_revision+1,updated_at=? "
                    "WHERE process_uuid=? AND status='retry_wait' AND next_retry_at<=? AND row_revision=?",
                    (now, now, process["process_uuid"], now, process["row_revision"]),
                )
                if updated.rowcount != 1:
                    continue
                promoted += 1
                await tx.execute(
                    "UPDATE mkb_executions SET status='ready',waiting_reason=NULL,waiting_ref=NULL,next_wake_at=NULL,"
                    "row_revision=row_revision+1,updated_at=? "
                    "WHERE execution_uuid=? AND status='waiting' AND waiting_reason='retry_due' AND waiting_ref=?",
                    (now, process["execution_uuid"], process["process_uuid"]),
                )
                await self._enqueue_tx(
                    tx,
                    process["team_uuid"],
                    "wake_process",
                    {"execution_uuid": process["execution_uuid"], "process_uuid": process["process_uuid"]},
                    f"retry-ready:{process['process_uuid']}:{process['row_revision'] + 1}",
                )
                await self._record_event_tx(
                    tx,
                    execution=process,
                    event_type="process.status_changed",
                    aggregate="process",
                    summary="Due Process retry promoted to ready",
                    process_uuid=process["process_uuid"],
                    status_before=ProcessStatus.RETRY_WAIT.value,
                    status_after=ProcessStatus.READY.value,
                    payload={"retry_count": process["retry_count"]},
                )
        return promoted


    async def recover_expired_leases(self, *, limit: int = 128) -> int:
        """Fence expired claims and either safely replay or fail loud.

        Recovery deliberately increments ``recovery_count`` but never
        ``retry_count``.  A policy snapshot can opt out of replay with
        ``{"safe_replay": false}``; missing/invalid snapshots fail closed.
        """

        if limit < 1:
            return 0
        now = utc_now()
        recovered = 0
        async with self.persistence.transaction() as tx:
            rows = await tx.fetchall(
                "SELECT p.*,e.trace_uuid,e.status AS execution_status FROM mkb_processes AS p "
                "JOIN mkb_executions AS e ON e.execution_uuid=p.execution_uuid AND e.team_uuid=p.team_uuid "
                "WHERE p.status IN ('claimed','running','cancelling') AND p.lease_expires_at IS NOT NULL "
                "AND p.lease_expires_at<=? ORDER BY p.lease_expires_at ASC,p.process_uuid ASC LIMIT ?",
                (now, limit),
            )
            for process in rows:
                execution = await self._execution(tx, process["execution_uuid"])
                if (
                    process["status"] == ProcessStatus.CANCELLING.value
                    or execution["status"] == ExecutionStatus.CANCELLING.value
                ):
                    updated = await tx.execute(
                        "UPDATE mkb_processes SET status='cancelled',claim_token_hash=NULL,lease_owner=NULL,"
                        "lease_expires_at=NULL,heartbeat_at=NULL,completed_at=?,row_revision=row_revision+1,updated_at=? "
                        "WHERE process_uuid=? AND status='cancelling' AND fencing_generation=?",
                        (now, now, process["process_uuid"], process["fencing_generation"]),
                    )
                    if updated.rowcount:
                        recovered += 1
                        await self._record_event_tx(
                            tx,
                            execution=process,
                            event_type="process.status_changed",
                            aggregate="process",
                            summary="Cancelling process lease expired and is now fenced cancelled",
                            process_uuid=process["process_uuid"],
                            status_before=ProcessStatus.CANCELLING.value,
                            status_after=ProcessStatus.CANCELLED.value,
                            payload={"fencing_generation": process["fencing_generation"]},
                        )
                    await self._converge_cancellation_tx(tx, execution)
                    continue
                safe_replay = self._safe_replay(process.get("backoff_policy_json"))
                if not safe_replay:
                    await self._fail_process_tx(
                        tx,
                        process,
                        error_code="indeterminate-side-effect",
                        error_message="Lease expired for a process that is not safe to replay",
                        failure_disposition="indeterminate",
                    )
                    await self._route_after_terminal_process_tx(
                        tx, execution, process, WorkflowOutcomeSelector.FAILED, {}, "indeterminate-side-effect"
                    )
                    recovered += 1
                    continue
                if process["recovery_count"] >= process["max_recoveries"]:
                    await self._fail_process_tx(
                        tx,
                        process,
                        error_code="recovery-exhausted",
                        error_message="Lease recovery budget is exhausted",
                        failure_disposition="recovery-exhausted",
                    )
                    await self._route_after_terminal_process_tx(
                        tx, execution, process, WorkflowOutcomeSelector.FAILED, {}, "recovery-exhausted"
                    )
                    recovered += 1
                    continue
                updated = await tx.execute(
                    "UPDATE mkb_processes SET status='ready',claim_token_hash=NULL,lease_owner=NULL,lease_expires_at=NULL,"
                    "heartbeat_at=NULL,fencing_generation=fencing_generation+1,recovery_count=recovery_count+1,"
                    "available_at=?,dispatch_admitted=0,dispatch_pool=NULL,dispatch_enqueued_at=NULL,"
                    "row_revision=row_revision+1,updated_at=? "
                    "WHERE process_uuid=? AND status IN ('claimed','running') AND fencing_generation=? "
                    "AND lease_expires_at<=?",
                    (now, now, process["process_uuid"], process["fencing_generation"], now),
                )
                if updated.rowcount != 1:
                    continue
                recovered += 1
                await self._enqueue_tx(
                    tx,
                    process["team_uuid"],
                    "wake_process",
                    {"execution_uuid": process["execution_uuid"], "process_uuid": process["process_uuid"]},
                    f"lease-recovery:{process['process_uuid']}:{process['fencing_generation'] + 1}",
                )
                await self._record_event_tx(
                    tx,
                    execution=process,
                    event_type="process.lease_recovered",
                    aggregate="process",
                    summary="Expired lease was fenced and Process returned to ready",
                    process_uuid=process["process_uuid"],
                    status_before=process["status"],
                    status_after=ProcessStatus.READY.value,
                    payload={"recovery_count": process["recovery_count"] + 1},
                )
            for execution_uuid in {row["execution_uuid"] for row in rows}:
                await self._refresh_execution_counts_tx(tx, execution_uuid)
        return recovered


    async def request_cancellation(self, execution_uuid: str) -> bool:
        """Propagate an accepted Execution cancellation without inventing success."""

        async with self.persistence.transaction() as tx:
            execution = await self._execution(tx, execution_uuid)
            if execution["status"] in _TERMINAL_EXECUTION_STATUSES:
                return False
            root = await self._execution(tx, execution["root_execution_uuid"])
            await self._cancel_execution_tree_tx(tx, root, include_root=True)
            await self._refresh_execution_counts_tx(tx, root["execution_uuid"])
            return True


    async def _route_after_terminal_process_tx(
        self,
        tx: UnitOfWork,
        execution: dict[str, Any],
        process: dict[str, Any],
        selector: WorkflowOutcomeSelector,
        route_context: dict[str, Any],
        terminal_error: str | None,
    ) -> None:
        plan = await self._assert_execution_binding(tx, execution)
        typed = await self._typed_route_context_tx(tx, execution)
        if "gate_action" in route_context:
            typed["gate_action"] = route_context["gate_action"]
        decision = self._route_decision(
            plan=plan,
            execution=execution,
            source_step_key=process["step_key"],
            selector=selector,
            route_context=typed,
        )
        await self._apply_routes_tx(
            tx,
            plan=plan,
            execution=execution,
            decision=decision,
            source_process=process,
            route_context=typed,
            terminal_error=terminal_error,
        )


    async def _fail_process_tx(
        self,
        tx: UnitOfWork,
        process: dict[str, Any],
        *,
        error_code: str,
        error_message: str,
        failure_disposition: str,
        accepted_outcome_digest: str | None = None,
        payload_extra: dict[str, Any] | None = None,
    ) -> None:
        now = utc_now()
        extras = payload_extra if isinstance(payload_extra, dict) else {}
        extra_json = json.dumps(extras, ensure_ascii=False, separators=(",", ":")) if extras else None
        updated = await tx.execute(
            "UPDATE mkb_processes SET status='failed',accepted_outcome_digest=COALESCE(?,accepted_outcome_digest),"
            "error_class='workflow-stage',error_code=?,error_message=?,failure_disposition=?,claim_token_hash=NULL,"
            "lease_owner=NULL,lease_expires_at=NULL,heartbeat_at=NULL,completed_at=?,row_revision=row_revision+1,updated_at=?,"
            "payload_extra=COALESCE(?,payload_extra) "
            "WHERE process_uuid=? AND status NOT IN ('succeeded','failed','cancelled')",
            (
                accepted_outcome_digest,
                error_code,
                _safe_persisted_error(error_message),
                failure_disposition,
                now,
                now,
                extra_json,
                process["process_uuid"],
            ),
        )
        if updated.rowcount:
            from src.runtime.intake.generation_evidence import write_pending_generation_evidence_tx

            await write_pending_generation_evidence_tx(tx, process)
            event_payload = {"error_code": error_code, "failure_disposition": failure_disposition}
            if extras:
                event_payload.update(extras)
            await self._record_event_tx(
                tx,
                execution=process,
                event_type="process.status_changed",
                aggregate="process",
                summary="Process reached a terminal failure",
                process_uuid=process["process_uuid"],
                status_before=process["status"],
                status_after=ProcessStatus.FAILED.value,
                severity="error",
                payload=event_payload,
            )


    async def _terminalize_execution_tx(
        self,
        tx: UnitOfWork,
        execution: dict[str, Any],
        terminal_kind: WorkflowTerminalKind | None,
        *,
        source_process: dict[str, Any] | None,
        route_digest: str,
        error_code: str | None,
    ) -> None:
        if terminal_kind is None:
            raise MkbError("workflow-terminal-invalid", "Terminal workflow step is missing its terminal kind", 500)
        status = {
            WorkflowTerminalKind.SUCCESS: ExecutionStatus.SUCCEEDED.value,
            WorkflowTerminalKind.FAILURE: ExecutionStatus.FAILED.value,
            WorkflowTerminalKind.CANCELLED: ExecutionStatus.CANCELLED.value,
            WorkflowTerminalKind.NOOP: ExecutionStatus.SUCCEEDED.value,
        }[terminal_kind]
        current = await self._execution(tx, execution["execution_uuid"])
        if current["status"] in _TERMINAL_EXECUTION_STATUSES:
            return
        if (
            current["root_execution_uuid"] == current["execution_uuid"]
            and current.get("execution_role") == "scatter_root"
            and status in {ExecutionStatus.FAILED.value, ExecutionStatus.CANCELLED.value}
        ):
            # A root rejection/failure may happen while review-gated children
            # are still durable-but-unstarted.  Fence only unfinished work;
            # proof-valid siblings stay untouched (forward-stop/no rollback).
            await self._cancel_execution_tree_tx(tx, current, include_root=False)
        if status == ExecutionStatus.SUCCEEDED.value and source_process is None:
            await self._fail_execution_integrity_tx(
                tx,
                current,
                "workflow-success-proof-missing",
                "Workflow success lacks a source Process completion proof",
            )
            return
        if status == ExecutionStatus.SUCCEEDED.value and not source_process.get("proof_ref"):
            await self._fail_execution_integrity_tx(
                tx,
                current,
                "workflow-success-proof-missing",
                "Workflow success lacks a publication proof",
            )
            return
        await self._refresh_execution_counts_tx(tx, current["execution_uuid"])
        counts = await tx.fetchone(
            "SELECT total_process_count,active_process_count,succeeded_process_count,failed_process_count,cancelled_process_count "
            "FROM mkb_executions WHERE execution_uuid=?",
            (current["execution_uuid"],),
        )
        now = utc_now()
        summary = {
            "workflow_revision_uuid": current["workflow_revision_uuid"],
            "compiled_digest": current["compiled_digest"],
            "route_decision_digest": route_digest,
            "terminal_status": status,
            "counts": counts,
            "source_process_uuid": None if source_process is None else source_process["process_uuid"],
            "error_code": error_code,
        }
        final_error = error_code or (None if status == ExecutionStatus.SUCCEEDED.value else "workflow-terminal-failure")
        final_message = None if final_error is None else "Workflow reached a terminal failure route"
        updated = await tx.execute(
            "UPDATE mkb_executions SET status=?,waiting_reason=NULL,waiting_ref=NULL,next_wake_at=NULL,current_process_uuid=NULL,"
            "result_ref=?,publication_proof_ref=?,final_error_code=?,final_error_message=?,terminal_summary_digest=?,"
            "summary_completed_at=?,completed_at=?,row_revision=row_revision+1,updated_at=? "
            "WHERE execution_uuid=? AND status NOT IN ('succeeded','failed','cancelled')",
            (
                status,
                None if source_process is None else source_process.get("output_manifest_ref"),
                None if source_process is None else source_process.get("proof_ref"),
                final_error,
                final_message,
                stable_digest(summary),
                now,
                now,
                now,
                current["execution_uuid"],
            ),
        )
        if updated.rowcount != 1:
            return
        await self._project_root_task_tx(tx, current, status, source_process, final_error, final_message)
        await self._record_event_tx(
            tx,
            execution=current,
            event_type="execution.status_changed",
            aggregate="execution",
            summary="Execution reached a terminal workflow route",
            process_uuid=None if source_process is None else source_process["process_uuid"],
            status_before=current["status"],
            status_after=status,
            severity="error" if status == ExecutionStatus.FAILED.value else "info",
            payload=summary,
        )
        await self._notify_scatter_parent_terminal_tx(tx, current)


    async def _project_root_task_tx(
        self,
        tx: UnitOfWork,
        execution: dict[str, Any],
        status: str,
        source_process: dict[str, Any] | None,
        error_code: str | None,
        error_message: str | None,
    ) -> None:
        """Project Task terminal status through the single owned helper (R2)."""

        if execution["root_execution_uuid"] != execution["execution_uuid"]:
            return
        from src.contracts.common.models import TaskStatus
        from src.runtime.task.task_projection import project_task_status_tx
        from src.services.events import DomainEventWriter

        task_status = {
            ExecutionStatus.SUCCEEDED.value: TaskStatus.SUCCEEDED,
            ExecutionStatus.FAILED.value: TaskStatus.FAILED,
            ExecutionStatus.CANCELLED.value: TaskStatus.CANCELLED,
        }[status]
        await project_task_status_tx(
            tx,
            team_uuid=execution["team_uuid"],
            task_uuid=execution["task_uuid"],
            target=task_status,
            events=DomainEventWriter(),
            trace_uuid=execution.get("trace_uuid"),
            current_root_execution_uuid=execution["execution_uuid"],
            result_ref=None if source_process is None else source_process.get("output_manifest_ref"),
            proof_ref=None if source_process is None else source_process.get("proof_ref"),
            error_code=error_code,
            error_message=error_message,
        )


    async def _fail_execution_integrity_tx(
        self, tx: UnitOfWork, execution: dict[str, Any], error_code: str, message: str
    ) -> None:
        now = utc_now()
        current = await self._execution(tx, execution["execution_uuid"])
        if (
            current["root_execution_uuid"] == current["execution_uuid"]
            and current.get("execution_role") == "scatter_root"
        ):
            await self._cancel_execution_tree_tx(tx, current, include_root=False)
        updated = await tx.execute(
            "UPDATE mkb_executions SET status='failed',final_error_code=?,final_error_message=?,"
            "terminal_summary_digest=?,summary_completed_at=?,completed_at=?,current_process_uuid=NULL,"
            "row_revision=row_revision+1,updated_at=? "
            "WHERE execution_uuid=? AND status NOT IN ('succeeded','failed','cancelled')",
            (
                error_code,
                message[:512],
                stable_digest({"execution_uuid": execution["execution_uuid"], "error_code": error_code}),
                now,
                now,
                now,
                execution["execution_uuid"],
            ),
        )
        if updated.rowcount:
            await self._project_root_task_tx(tx, current, ExecutionStatus.FAILED.value, None, error_code, message)
            await self._record_event_tx(
                tx,
                execution=current,
                event_type="execution.status_changed",
                aggregate="execution",
                summary="Execution failed closed on a workflow integrity violation",
                status_before=execution["status"],
                status_after=ExecutionStatus.FAILED.value,
                severity="error",
                payload={"error_code": error_code},
            )
            await self._notify_scatter_parent_terminal_tx(tx, current)


    async def _cancel_execution_tree_tx(
        self,
        tx: UnitOfWork,
        root: dict[str, Any],
        *,
        include_root: bool,
    ) -> int:
        """Fence a root's unfinished descendants without rolling back proofs."""

        if root["root_execution_uuid"] != root["execution_uuid"]:
            raise MkbError("cancel-tree-root-invalid", "Cancellation tree root is not a root Execution", 409)
        rows = await tx.fetchall(
            "SELECT * FROM mkb_executions WHERE root_execution_uuid=? "
            + ("" if include_root else "AND execution_uuid<>? ")
            + "AND status NOT IN ('succeeded','failed','cancelled') "
            "ORDER BY CASE WHEN parent_execution_uuid IS NULL THEN 1 ELSE 0 END,execution_uuid",
            (root["execution_uuid"],) if include_root else (root["execution_uuid"], root["execution_uuid"]),
        )
        now = utc_now()
        changed = 0
        for row in rows:
            transitioned = await tx.execute(
                "UPDATE mkb_executions SET status='cancelling',cancel_requested_at=COALESCE(cancel_requested_at,?),"
                "row_revision=row_revision+1,updated_at=? WHERE execution_uuid=? "
                "AND status NOT IN ('succeeded','failed','cancelled','cancelling')",
                (now, now, row["execution_uuid"]),
            )
            changed += int(bool(transitioned.rowcount))
            await tx.execute(
                "UPDATE mkb_execution_gates SET status='superseded',gate_revision=gate_revision+1,terminal_at=? "
                "WHERE execution_uuid=? AND status='open'",
                (now, row["execution_uuid"]),
            )
            # R4: idle Processes pass through cancelling then terminal in this UoW
            # so observers never see a durable cancel path that skips cancelling.
            await tx.execute(
                "UPDATE mkb_processes SET status='cancelling',fencing_generation=fencing_generation+1,"
                "row_revision=row_revision+1,updated_at=? "
                "WHERE execution_uuid=? AND status IN ('ready','retry_wait')",
                (now, row["execution_uuid"]),
            )
            await tx.execute(
                "UPDATE mkb_processes SET status='cancelled',completed_at=?,claim_token_hash=NULL,lease_owner=NULL,"
                "lease_expires_at=NULL,heartbeat_at=NULL,row_revision=row_revision+1,updated_at=? "
                "WHERE execution_uuid=? AND status='cancelling' AND lease_owner IS NULL "
                "AND claim_token_hash IS NULL",
                (now, now, row["execution_uuid"]),
            )
            await tx.execute(
                "UPDATE mkb_processes SET status='cancelling',fencing_generation=fencing_generation+1,"
                "row_revision=row_revision+1,updated_at=? "
                "WHERE execution_uuid=? AND status IN ('claimed','running')",
                (now, row["execution_uuid"]),
            )
            await tx.execute(
                "UPDATE mkb_intake_candidate_sets SET staging_state='abandoned',"
                "row_revision=row_revision+1,updated_at=? "
                "WHERE team_uuid=? AND producer_execution_uuid=? AND staging_state IN ('open','sealed')",
                (now, row["team_uuid"], row["execution_uuid"]),
            )
        # Children are ordered first.  A waiting review child has no Process
        # and therefore converges immediately; claimed/running children retain
        # their fence until a worker or lease recovery closes them.
        for row in rows:
            current = await self._execution(tx, row["execution_uuid"])
            await self._converge_cancellation_tx(tx, current)
        return changed


    async def _converge_cancellation_tx(self, tx: UnitOfWork, execution: dict[str, Any]) -> bool:
        current = await self._execution(tx, execution["execution_uuid"])
        if current["status"] != ExecutionStatus.CANCELLING.value:
            return False
        active = await tx.fetchone(
            "SELECT COUNT(*) AS count FROM mkb_processes WHERE execution_uuid=? "
            "AND status IN ('ready','claimed','running','retry_wait','cancelling')",
            (current["execution_uuid"],),
        )
        if active is not None and active["count"]:
            return False
        if current["root_execution_uuid"] == current["execution_uuid"]:
            descendants = await tx.fetchone(
                "SELECT COUNT(*) AS count FROM mkb_executions WHERE root_execution_uuid=? AND execution_uuid<>? "
                "AND status NOT IN ('succeeded','failed','cancelled')",
                (current["execution_uuid"], current["execution_uuid"]),
            )
            if descendants is not None and descendants["count"]:
                return False
        now = utc_now()
        updated = await tx.execute(
            "UPDATE mkb_executions SET status='cancelled',waiting_reason=NULL,waiting_ref=NULL,next_wake_at=NULL,"
            "cancel_converged_at=?,completed_at=?,current_process_uuid=NULL,"
            "terminal_summary_digest=?,summary_completed_at=?,row_revision=row_revision+1,updated_at=? "
            "WHERE execution_uuid=? AND status='cancelling'",
            (
                now,
                now,
                stable_digest({"execution_uuid": current["execution_uuid"], "terminal_status": "cancelled"}),
                now,
                now,
                current["execution_uuid"],
            ),
        )
        if updated.rowcount:
            if current["root_execution_uuid"] == current["execution_uuid"]:
                # Root cancellation owns the public aggregate.  Refresh the
                # immutable membership projection before exposing Task
                # cancellation so stale active child counts cannot leak.
                await self._refresh_execution_counts_tx(tx, current["execution_uuid"])
            await self._project_root_task_tx(tx, current, ExecutionStatus.CANCELLED.value, None, None, None)
            await self._record_event_tx(
                tx,
                execution=current,
                event_type="execution.status_changed",
                aggregate="execution",
                summary="Execution cancellation converged after all Processes and descendants became terminal",
                status_before=ExecutionStatus.CANCELLING.value,
                status_after=ExecutionStatus.CANCELLED.value,
                payload={},
            )
            await self._notify_scatter_parent_terminal_tx(tx, current)
            return True
        return False
