"""Durable, bounded execution runtime for code-owned Workflow definitions.

The :mod:`src.workflows` package deliberately contains only declarative data.
This module is its runtime counterpart: it materializes eligible process rows,
claims work with a lease and monotonically increasing fence, accepts a typed
outcome, and records the next durable scheduling intent in the same database
transaction.  It does *not* implement acquisition, cleaning, construction,
embedding, or publication.  Those stages are injected through
``ProcessStageHandler`` and only receive the narrow ``ProcessCommand`` contract.

The implementation intentionally uses SQL compare-and-swap predicates even in
the local SQLite profile.  SQLite serializes local writes, while the predicates
remain the correctness boundary when the persistence port is replaced with a
concurrent libSQL/Turso adapter.
"""

from __future__ import annotations

import json
import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, Protocol, runtime_checkable

from src.contracts.common.errors import ConflictError, MkbError, NotFoundError, NotReadyError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.models import ExecutionStatus, ProcessStatus
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand, ProcessOutcome
from src.contracts.workflow.models import (
    WorkflowDefinition,
    WorkflowOutcomeSelector,
    WorkflowRouteDefinition,
    WorkflowStepDefinition,
    WorkflowStepKind,
    WorkflowTerminalKind,
)
from src.persistence.ports import PersistencePort, UnitOfWork

_TERMINAL_EXECUTION_STATUSES = {
    ExecutionStatus.SUCCEEDED.value,
    ExecutionStatus.FAILED.value,
    ExecutionStatus.CANCELLED.value,
}
_TERMINAL_PROCESS_STATUSES = {
    ProcessStatus.SUCCEEDED.value,
    ProcessStatus.FAILED.value,
    ProcessStatus.CANCELLED.value,
}
_ACTIVE_PROCESS_STATUSES = {
    ProcessStatus.READY.value,
    ProcessStatus.CLAIMED.value,
    ProcessStatus.RUNNING.value,
    ProcessStatus.RETRY_WAIT.value,
    ProcessStatus.CANCELLING.value,
}


@runtime_checkable
class ProcessStageHandler(Protocol):
    """Business-stage port.

    Implementations must make any external side effect idempotent on
    ``(process_uuid, fencing_generation)`` (or a stricter business key), and
    then return a ``ProcessOutcome``.  They do not choose a route or mutate
    Task/Execution/Process records.
    """

    async def run(self, command: ProcessCommand) -> ProcessOutcome: ...


@runtime_checkable
class ProcessOutcomeCommitter(Protocol):
    """Atomic bridge from a successful stage outcome to its owned catalogues.

    The committer runs inside the same persistence transaction as the Process
    outcome CAS.  It may register/promote output and proof references in the
    object, generation, or vector owners' tables, but it must not choose a
    workflow route or mutate Task/Execution/Process state.  Raising aborts the
    whole transaction; the caller must then either preserve a stale/conflict
    fence or submit a bounded failure outcome for the still-running Process.
    """

    async def validate_and_commit(
        self,
        tx: UnitOfWork,
        command: ProcessCommand,
        outcome: ProcessOutcome,
    ) -> None: ...


@runtime_checkable
class ReadinessProbe(Protocol):
    """Small, injectable readiness boundary used before accepting a new claim."""

    async def __call__(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class ClaimedProcess:
    """An in-memory delivery envelope; it is not a fourth durable identity."""

    command: ProcessCommand
    claim_token: str
    lease_expires_at: str


@dataclass(frozen=True, slots=True)
class OutboxDelivery:
    """One leased scheduling intent returned by the local outbox worker."""

    outbox_id: str
    team_uuid: str
    kind: str
    payload: dict[str, Any]
    lease_owner: str


def canonical_outcome_digest(outcome: ProcessOutcome) -> str:
    """Return the canonical digest a stage must put in ``outcome_digest``.

    The helper makes outcome integrity testable without exposing a mutable JSON
    escape hatch.  A handler can construct an outcome with a temporary 64-hex
    value and replace that value with this result before returning it.
    """

    material = outcome.model_dump(mode="json")
    material.pop("outcome_digest", None)
    return stable_digest(material)


class WorkflowRuntime:
    """State machine and durable scheduler for one immutable workflow revision.

    ``definition`` is code-owned, validated declaration data.  Runtime rows are
    still bound to a registry revision in the database; materialization checks
    that binding and looks up the registry's stable step UUIDs before inserting
    a Process.  This deliberately prevents a caller from substituting a graph
    or a step UUID at runtime.
    """

    def __init__(
        self,
        persistence: PersistencePort,
        definition: WorkflowDefinition,
        *,
        readiness: ReadinessProbe | Callable[[], Awaitable[bool]] | None = None,
        outcome_committer: ProcessOutcomeCommitter | None = None,
        default_max_retries: int = 3,
        default_max_recoveries: int = 3,
        retry_delay_seconds: int = 1,
    ) -> None:
        if default_max_retries < 0 or default_max_recoveries < 0:
            raise ValueError("retry and recovery limits must be non-negative")
        if retry_delay_seconds < 0:
            raise ValueError("retry_delay_seconds must be non-negative")
        self.persistence = persistence
        self.definition = definition
        self.readiness = readiness
        self.outcome_committer = outcome_committer
        self.default_max_retries = default_max_retries
        self.default_max_recoveries = default_max_recoveries
        self.retry_delay_seconds = retry_delay_seconds
        self._steps = {step.step_key: step for step in definition.steps}
        self._routes_by_source: dict[str, list[WorkflowRouteDefinition]] = {}
        for route in definition.routes:
            self._routes_by_source.setdefault(route.from_step_key, []).append(route)
        for routes in self._routes_by_source.values():
            routes.sort(key=lambda route: route.priority)
        self._guards = {guard.guard_key: guard for guard in definition.guards}

    async def materialize_root(self, execution_uuid: str) -> bool:
        """Materialize the start route exactly once and enqueue its durable wake.

        Returns ``True`` when this call inserted the first process and ``False``
        when a prior call already materialized it or the execution is terminal.
        """

        async with self.persistence.transaction() as tx:
            execution = await self._execution(tx, execution_uuid)
            if execution["status"] in _TERMINAL_EXECUTION_STATUSES:
                return False
            if execution["status"] == ExecutionStatus.CANCELLING.value:
                await self._converge_cancellation_tx(tx, execution)
                return False
            await self._assert_execution_binding(tx, execution)
            start = next(step for step in self.definition.steps if step.step_kind is WorkflowStepKind.START)
            decision = self._route_decision(
                execution=execution,
                source_step_key=start.step_key,
                selector=WorkflowOutcomeSelector.ALWAYS,
                route_context={},
            )
            if not decision["routes"]:
                await self._fail_execution_integrity_tx(
                    tx, execution, "workflow-start-route-missing", "The bound workflow has no eligible start route"
                )
                return False
            changed = await self._apply_routes_tx(
                tx,
                execution=execution,
                decision=decision,
                source_process=None,
                route_context={},
                terminal_error=None,
            )
            await self._refresh_execution_counts_tx(tx, execution["execution_uuid"])
            return changed

    async def claim_next(self, lease_owner: str, *, lease_seconds: int = 30) -> ClaimedProcess | None:
        """Atomically claim the next due process, or return ``None`` when idle."""

        if not lease_owner or len(lease_owner) > 256:
            raise MkbError("invalid-lease-owner", "lease_owner must be a non-empty bounded identifier", 422)
        if not 1 <= lease_seconds <= 3600:
            raise MkbError("invalid-lease-seconds", "lease_seconds must be between 1 and 3600", 422)
        await self._assert_ready_for_claim()
        # Due retries are durable state, not an implicit claim side effect.
        await self.promote_due_retries(limit=64)

        now = utc_now()
        expires_at = _add_seconds(now, lease_seconds)
        claim_token = secrets.token_urlsafe(32)
        claim_token_hash = stable_digest({"claim_token": claim_token})
        async with self.persistence.transaction() as tx:
            candidate = await tx.fetchone(
                "SELECT p.*, e.trace_uuid, e.status AS execution_status, e.domain_binding_digest "
                "FROM mkb_processes AS p JOIN mkb_executions AS e "
                "ON e.execution_uuid=p.execution_uuid AND e.team_uuid=p.team_uuid "
                "JOIN mkb_tasks AS t ON t.team_uuid=p.team_uuid AND t.task_uuid=p.task_uuid "
                "WHERE p.status='ready' AND p.available_at<=? "
                "AND e.status IN ('ready','running') AND t.status IN ('queued','running') "
                "ORDER BY p.priority_rank DESC,p.available_at ASC,"
                "CASE WHEN p.deadline_at IS NULL THEN 1 ELSE 0 END,p.deadline_at ASC,p.created_at ASC,p.process_uuid ASC "
                "LIMIT 1",
                (now,),
            )
            if candidate is None:
                return None
            if candidate["deadline_at"] is not None and candidate["deadline_at"] < now:
                await self._fail_process_tx(
                    tx,
                    candidate,
                    error_code="deadline-exceeded-before-start",
                    error_message="The process deadline elapsed before it could be claimed",
                    failure_disposition="deadline",
                )
                execution = await self._execution(tx, candidate["execution_uuid"])
                await self._route_after_terminal_process_tx(
                    tx, execution, candidate, WorkflowOutcomeSelector.FAILED, {}, "deadline-exceeded-before-start"
                )
                await self._refresh_execution_counts_tx(tx, candidate["execution_uuid"])
                return None
            updated = await tx.execute(
                "UPDATE mkb_processes SET status='claimed',claim_token_hash=?,lease_owner=?,lease_expires_at=?,"
                "fencing_generation=fencing_generation+1,delivery_count=delivery_count+1,row_revision=row_revision+1,"
                "updated_at=? WHERE process_uuid=? AND status='ready' AND row_revision=? AND available_at<=?",
                (
                    claim_token_hash,
                    lease_owner,
                    expires_at,
                    now,
                    candidate["process_uuid"],
                    candidate["row_revision"],
                    now,
                ),
            )
            if updated.rowcount != 1:
                return None
            claimed = await self._process_with_execution(tx, candidate["process_uuid"])
            await self._record_event_tx(
                tx,
                execution=claimed,
                event_type="process.claimed",
                aggregate="process",
                summary="Process claimed with a new lease fence",
                process_uuid=claimed["process_uuid"],
                status_before=ProcessStatus.READY.value,
                status_after=ProcessStatus.CLAIMED.value,
                payload={"fencing_generation": claimed["fencing_generation"], "lease_owner": lease_owner},
            )
            command = self._command_from_process(claimed)
            return ClaimedProcess(command=command, claim_token=claim_token, lease_expires_at=expires_at)

    async def mark_running(self, process_uuid: str, fencing_generation: int) -> bool:
        """Record runner start evidence under the current fence."""

        now = utc_now()
        async with self.persistence.transaction() as tx:
            process = await self._process_with_execution(tx, process_uuid)
            if process["status"] == ProcessStatus.RUNNING.value and process["fencing_generation"] == fencing_generation:
                return False
            updated = await tx.execute(
                "UPDATE mkb_processes SET status='running',started_at=COALESCE(started_at,?),heartbeat_at=?,"
                "row_revision=row_revision+1,updated_at=? "
                "WHERE process_uuid=? AND status='claimed' AND fencing_generation=?",
                (now, now, now, process_uuid, fencing_generation),
            )
            if updated.rowcount != 1:
                raise ConflictError("stale-process-fence", "Process claim is no longer current")
            execution = await self._execution(tx, process["execution_uuid"])
            if execution["status"] == ExecutionStatus.READY.value:
                await tx.execute(
                    "UPDATE mkb_executions SET status='running',started_at=COALESCE(started_at,?),"
                    "row_revision=row_revision+1,updated_at=? WHERE execution_uuid=? AND status='ready'",
                    (now, now, execution["execution_uuid"]),
                )
            if execution["root_execution_uuid"] == execution["execution_uuid"]:
                await tx.execute(
                    "UPDATE mkb_tasks SET status='running',started_at=COALESCE(started_at,?),"
                    "row_revision=row_revision+1,updated_at=? "
                    "WHERE team_uuid=? AND task_uuid=? AND current_root_execution_uuid=? AND status='queued'",
                    (now, now, execution["team_uuid"], execution["task_uuid"], execution["execution_uuid"]),
                )
            await self._record_event_tx(
                tx,
                execution=process,
                event_type="process.status_changed",
                aggregate="process",
                summary="Process runner started",
                process_uuid=process_uuid,
                status_before=ProcessStatus.CLAIMED.value,
                status_after=ProcessStatus.RUNNING.value,
                payload={"fencing_generation": fencing_generation},
            )
            return True

    async def heartbeat(self, process_uuid: str, fencing_generation: int, *, lease_seconds: int = 30) -> bool:
        """Extend only the current running lease; stale runners cannot heartbeat."""

        if not 1 <= lease_seconds <= 3600:
            raise MkbError("invalid-lease-seconds", "lease_seconds must be between 1 and 3600", 422)
        now = utc_now()
        async with self.persistence.transaction() as tx:
            updated = await tx.execute(
                "UPDATE mkb_processes SET heartbeat_at=?,lease_expires_at=?,row_revision=row_revision+1,updated_at=? "
                "WHERE process_uuid=? AND status='running' AND fencing_generation=? AND lease_expires_at>?",
                (now, _add_seconds(now, lease_seconds), now, process_uuid, fencing_generation, now),
            )
            return updated.rowcount == 1

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
                    "output_manifest_digest=?,proof_ref=?,proof_digest=?,claim_token_hash=NULL,lease_owner=NULL,"
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
                    due = _add_seconds(now, self.retry_delay_seconds)
                    updated = await tx.execute(
                        "UPDATE mkb_processes SET status='retry_wait',accepted_outcome_digest=?,retry_count=retry_count+1,"
                        "next_retry_at=?,available_at=?,last_failure_retryability=1,error_code=?,error_message=?,"
                        "failure_disposition='retryable',claim_token_hash=NULL,lease_owner=NULL,lease_expires_at=NULL,"
                        "heartbeat_at=NULL,row_revision=row_revision+1,updated_at=? "
                        "WHERE process_uuid=? AND status='running' AND fencing_generation=?",
                        (
                            outcome.outcome_digest,
                            due,
                            due,
                            outcome.error_code,
                            outcome.error_message,
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
                    "available_at=?,row_revision=row_revision+1,updated_at=? "
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

        now = utc_now()
        async with self.persistence.transaction() as tx:
            execution = await self._execution(tx, execution_uuid)
            if execution["status"] in _TERMINAL_EXECUTION_STATUSES:
                return False
            if execution["status"] != ExecutionStatus.CANCELLING.value:
                await tx.execute(
                    "UPDATE mkb_executions SET status='cancelling',cancel_requested_at=COALESCE(cancel_requested_at,?),"
                    "row_revision=row_revision+1,updated_at=? WHERE execution_uuid=? AND status NOT IN ('succeeded','failed','cancelled')",
                    (now, now, execution_uuid),
                )
                execution = await self._execution(tx, execution_uuid)
            # Non-running work owns no external side effect and can converge in
            # the same transaction.  A running/claimed worker is first fenced
            # and left cancelling until its lease has closed.
            await tx.execute(
                "UPDATE mkb_processes SET status='cancelled',completed_at=?,claim_token_hash=NULL,lease_owner=NULL,"
                "lease_expires_at=NULL,heartbeat_at=NULL,row_revision=row_revision+1,updated_at=? "
                "WHERE execution_uuid=? AND status IN ('ready','retry_wait')",
                (now, now, execution_uuid),
            )
            await tx.execute(
                "UPDATE mkb_processes SET status='cancelling',fencing_generation=fencing_generation+1,"
                "row_revision=row_revision+1,updated_at=? "
                "WHERE execution_uuid=? AND status IN ('claimed','running')",
                (now, execution_uuid),
            )
            await self._converge_cancellation_tx(tx, execution)
            await self._refresh_execution_counts_tx(tx, execution_uuid)
            return True

    async def resolve_gate(
        self,
        gate_uuid: str,
        *,
        expected_gate_revision: int,
        action: str,
        idempotency_key: str,
        actor_fingerprint: str,
    ) -> bool:
        """Resolve the bounded human-review control hook for this Workflow.

        HTTP authorization/admission belongs to the Task API.  This method is
        intentionally internal and only accepts a previously durable gate.
        """

        if action not in {"approve", "reject", "reclean"}:
            raise MkbError("gate-action-invalid", "Gate action must be approve, reject, or reclean", 422)
        if not idempotency_key or not actor_fingerprint:
            raise MkbError(
                "gate-decision-invalid", "Gate decisions require an idempotency key and actor fingerprint", 422
            )
        now = utc_now()
        async with self.persistence.transaction() as tx:
            gate = await tx.fetchone("SELECT * FROM mkb_execution_gates WHERE gate_uuid=?", (gate_uuid,))
            if gate is None:
                raise NotFoundError("gate-not-found", "Execution Gate was not found")
            existing = await tx.fetchone(
                "SELECT decision_uuid FROM mkb_execution_gate_decisions WHERE gate_uuid=? AND idempotency_key=?",
                (gate_uuid, idempotency_key),
            )
            if existing is not None:
                return False
            if gate["status"] != "open" or gate["gate_revision"] != expected_gate_revision:
                raise ConflictError(
                    "gate-revision-conflict", "Execution Gate is no longer open at the supplied revision"
                )
            target = await self._gate_target_for_action_tx(tx, gate_uuid, action)
            execution = await self._execution(tx, gate["execution_uuid"])
            if execution["status"] != ExecutionStatus.WAITING.value or execution["waiting_ref"] != gate_uuid:
                raise ConflictError("gate-execution-conflict", "Gate is not the current durable execution wait")
            decision_digest = stable_digest(
                {
                    "gate_uuid": gate_uuid,
                    "gate_revision": expected_gate_revision,
                    "action": action,
                    "idempotency_key": idempotency_key,
                }
            )
            await tx.execute(
                "INSERT INTO mkb_execution_gate_decisions "
                "(decision_uuid,gate_uuid,team_uuid,expected_gate_revision,action,actor_fingerprint,idempotency_key,target_digest,"
                "decision_digest,created_at,payload_extra) VALUES (?,?,?,?,?,?,?,?,?,?,'{}')",
                (
                    uuid7(),
                    gate_uuid,
                    gate["team_uuid"],
                    expected_gate_revision,
                    action,
                    actor_fingerprint,
                    idempotency_key,
                    target["target_digest"],
                    decision_digest,
                    now,
                ),
            )
            gate_status = "released" if action in {"approve", "reclean"} else "rejected"
            updated = await tx.execute(
                "UPDATE mkb_execution_gates SET status=?,gate_revision=gate_revision+1,terminal_at=? "
                "WHERE gate_uuid=? AND status='open' AND gate_revision=?",
                (gate_status, now, gate_uuid, expected_gate_revision),
            )
            if updated.rowcount != 1:
                raise ConflictError("gate-revision-conflict", "Execution Gate changed during decision")
            control = self._control_step()
            if action == "approve":
                await tx.execute(
                    "UPDATE mkb_executions SET status='ready',waiting_reason=NULL,waiting_ref=NULL,next_wake_at=NULL,"
                    "row_revision=row_revision+1,updated_at=? WHERE execution_uuid=? AND status='waiting' AND waiting_ref=?",
                    (now, execution["execution_uuid"], gate_uuid),
                )
                updated_execution = await self._execution(tx, execution["execution_uuid"])
                decision = self._route_decision(
                    execution=updated_execution,
                    source_step_key=control.step_key,
                    selector=WorkflowOutcomeSelector.SUCCEEDED,
                    route_context={"gate_action": action},
                )
                await self._apply_routes_tx(
                    tx,
                    execution=updated_execution,
                    decision=decision,
                    source_process=None,
                    route_context={"gate_action": action},
                    terminal_error=None,
                )
            elif action == "reject":
                decision = self._route_decision(
                    execution=execution,
                    source_step_key=control.step_key,
                    selector=WorkflowOutcomeSelector.FAILED,
                    route_context={"gate_action": action},
                )
                await self._apply_routes_tx(
                    tx,
                    execution=execution,
                    decision=decision,
                    source_process=None,
                    route_context={"gate_action": action},
                    terminal_error=f"gate-{action}",
                )
            else:
                # A future workflow may explicitly add a reclean route.  This
                # seed does not have one, so it must not reinterpret reclean as
                # approval or mutate the old artifact in place.
                raise MkbError(
                    "gate-action-route-unavailable", "No declared reclean route exists for this workflow", 409
                )
            await self._record_event_tx(
                tx,
                execution=execution,
                event_type="gate.decided",
                aggregate="gate",
                summary="Human-review Gate decision accepted",
                payload={"gate_uuid": gate_uuid, "action": action, "decision_digest": decision_digest},
            )
            await self._refresh_execution_counts_tx(tx, execution["execution_uuid"])
            return True

    async def consume_gate_decision(self, decision_uuid: str) -> bool:
        """Advance an already committed Task-surface Gate decision exactly once.

        The public Task service owns decision admission, Gate CAS, and the
        waiting-to-running projection.  This consumer never rewrites the
        terminal Gate state.  It simply interprets the immutable decision in
        the bound workflow and materializes its next durable intent.
        """

        async with self.persistence.transaction() as tx:
            decision = await tx.fetchone(
                "SELECT d.*,g.status AS gate_status,g.execution_uuid,g.gate_kind,g.gate_revision,"
                "g.team_uuid AS gate_team_uuid FROM mkb_execution_gate_decisions AS d "
                "JOIN mkb_execution_gates AS g ON g.gate_uuid=d.gate_uuid WHERE d.decision_uuid=?",
                (decision_uuid,),
            )
            if decision is None:
                raise NotFoundError("gate-decision-not-found", "Execution Gate decision was not found")
            if decision["action"] not in {"approve", "reject", "reclean"}:
                raise MkbError("gate-action-invalid", "Persisted Gate action is unsupported", 409)
            target = await self._gate_target_for_action_tx(tx, decision["gate_uuid"], decision["action"])
            if decision["target_digest"] != target["target_digest"]:
                raise ConflictError(
                    "gate-target-digest-conflict", "Gate decision does not bind the current frozen review target"
                )
            expected_status = "rejected" if decision["action"] == "reject" else "released"
            if decision["gate_status"] != expected_status:
                raise ConflictError("gate-decision-state-conflict", "Gate terminal state does not match its decision")
            execution = await self._execution(tx, decision["execution_uuid"])
            if execution["status"] in _TERMINAL_EXECUTION_STATUSES:
                return False
            control = self._control_step()
            if decision["gate_kind"] != control.control_key:
                raise MkbError("gate-control-mismatch", "Gate does not belong to the bound workflow control step", 409)
            if decision["action"] == "approve":
                if execution["status"] not in {ExecutionStatus.RUNNING.value, ExecutionStatus.READY.value}:
                    raise ConflictError(
                        "gate-execution-projection-missing",
                        "Gate decision was not projected to a resumable Execution",
                    )
                selector = WorkflowOutcomeSelector.SUCCEEDED
                terminal_error = None
            elif decision["action"] == "reject":
                # The Task service leaves a rejected decision's Execution
                # resumable enough for the runtime to take the declared
                # failure terminal; it must not alter Gate state here.
                if execution["status"] not in {
                    ExecutionStatus.WAITING.value,
                    ExecutionStatus.RUNNING.value,
                    ExecutionStatus.READY.value,
                }:
                    raise ConflictError("gate-execution-projection-missing", "Rejected Gate has no routable Execution")
                selector = WorkflowOutcomeSelector.FAILED
                terminal_error = "gate-rejected"
            else:
                raise MkbError(
                    "gate-action-route-unavailable", "No declared reclean route exists for this workflow", 409
                )
            decision_result = self._route_decision(
                execution=execution,
                source_step_key=control.step_key,
                selector=selector,
                route_context={"gate_action": decision["action"]},
            )
            changed = await self._apply_routes_tx(
                tx,
                execution=execution,
                decision=decision_result,
                source_process=None,
                route_context={"gate_action": decision["action"]},
                terminal_error=terminal_error,
            )
            await self._refresh_execution_counts_tx(tx, execution["execution_uuid"])
            return changed

    async def claim_outbox(self, lease_owner: str, *, lease_seconds: int = 30) -> OutboxDelivery | None:
        """Lease one durable wake-up intent; uniqueness is enforced by its dedupe key."""

        if not lease_owner:
            raise MkbError("invalid-lease-owner", "lease_owner must be non-empty", 422)
        now = utc_now()
        expires_at = _add_seconds(now, lease_seconds)
        # `mkb_outbox` has no fencing column, so use a fresh opaque delivery
        # owner as the compare-and-swap token.  A worker that wakes after its
        # lease was reclaimed cannot mark a newer delivery done or pending.
        delivery_lease_owner = f"{lease_owner}:{uuid7()}"
        if len(delivery_lease_owner) > 256:
            raise MkbError("invalid-lease-owner", "lease_owner is too long for a unique delivery lease", 422)
        async with self.persistence.transaction() as tx:
            row = await tx.fetchone(
                "SELECT * FROM mkb_outbox WHERE (status='pending' AND available_at<=?) "
                "OR (status='in_flight' AND lease_expires_at<=?) "
                "ORDER BY available_at ASC,created_at ASC,outbox_id ASC LIMIT 1",
                (now, now),
            )
            if row is None:
                return None
            updated = await tx.execute(
                "UPDATE mkb_outbox SET status='in_flight',lease_owner=?,lease_expires_at=?,attempts=attempts+1,updated_at=? "
                "WHERE outbox_id=? AND ((status='pending' AND available_at<=?) OR (status='in_flight' AND lease_expires_at<=?))",
                (delivery_lease_owner, expires_at, now, row["outbox_id"], now, now),
            )
            if updated.rowcount != 1:
                return None
            try:
                payload = json.loads(row["payload_json"])
            except json.JSONDecodeError as exc:
                raise MkbError("outbox-payload-invalid", "Outbox payload is not valid JSON", 500) from exc
            if not isinstance(payload, dict) or stable_digest(payload) != row["payload_digest"]:
                raise MkbError("outbox-payload-invalid", "Outbox payload digest is invalid", 500)
            return OutboxDelivery(
                row["outbox_id"],
                row["team_uuid"],
                row["kind"],
                payload,
                delivery_lease_owner,
            )

    async def dispatch_outbox_once(self, lease_owner: str, *, lease_seconds: int = 30) -> bool:
        """Consume one scheduling intent after it is durably leased.

        Wakes do not execute business work.  They only ensure that materialized
        work is observable by a process worker; the worker subsequently claims
        the Process from the database.
        """

        delivery = await self.claim_outbox(lease_owner, lease_seconds=lease_seconds)
        if delivery is None:
            return False
        try:
            if delivery.kind == "wake_execution":
                await self.materialize_root(_required_payload_uuid(delivery.payload, "execution_uuid"))
            elif delivery.kind == "wake_process":
                # A DB scan is the source of truth; no in-memory queue item is
                # required to make a Process runnable.
                _required_payload_uuid(delivery.payload, "execution_uuid")
                _required_payload_uuid(delivery.payload, "process_uuid")
            elif delivery.kind == "cancel_execution":
                await self.request_cancellation(_required_payload_uuid(delivery.payload, "execution_uuid"))
            elif delivery.kind == "gate_decision":
                await self.consume_gate_decision(_required_payload_uuid(delivery.payload, "decision_uuid"))
            else:
                raise MkbError("outbox-kind-unsupported", "Outbox kind is not owned by the workflow runtime", 500)
        except Exception as exc:
            await self._release_outbox(delivery.outbox_id, delivery.lease_owner, str(exc))
            raise
        await self._complete_outbox(delivery.outbox_id, delivery.lease_owner)
        return True

    async def repair_once(self) -> int:
        """Run bounded semantic recovery; repeated calls are idempotent."""

        promoted = await self.promote_due_retries()
        recovered = await self.recover_expired_leases()
        return promoted + recovered

    async def _assert_ready_for_claim(self) -> None:
        if self.readiness is not None:
            ready = await self.readiness()
        else:
            readiness = await self.persistence.readiness()
            ready = all(readiness.values())
        if not ready:
            raise NotReadyError("workflow-not-ready", "Readiness is false; new Process claims are fenced")

    async def _execution(self, tx: UnitOfWork, execution_uuid: str) -> dict[str, Any]:
        row = await tx.fetchone("SELECT * FROM mkb_executions WHERE execution_uuid=?", (execution_uuid,))
        if row is None:
            raise NotFoundError("execution-not-found", "Execution was not found")
        return row

    async def _process_with_execution(self, tx: UnitOfWork, process_uuid: str) -> dict[str, Any]:
        row = await tx.fetchone(
            "SELECT p.*,e.trace_uuid,e.status AS execution_status,e.domain_binding_digest "
            "FROM mkb_processes AS p JOIN mkb_executions AS e "
            "ON e.execution_uuid=p.execution_uuid AND e.team_uuid=p.team_uuid WHERE p.process_uuid=?",
            (process_uuid,),
        )
        if row is None:
            raise NotFoundError("process-not-found", "Process was not found")
        return row

    async def _assert_execution_binding(self, tx: UnitOfWork, execution: dict[str, Any]) -> None:
        revision = await tx.fetchone(
            "SELECT r.workflow_revision_uuid,r.compiled_digest,w.workflow_key FROM mkb_workflow_revisions AS r "
            "JOIN mkb_workflow_registry AS w ON w.workflow_uuid=r.workflow_uuid "
            "WHERE r.workflow_revision_uuid=?",
            (execution["workflow_revision_uuid"],),
        )
        if revision is None:
            raise MkbError("workflow-binding-missing", "Execution references a missing workflow revision", 503)
        if (
            revision["compiled_digest"] != execution["compiled_digest"]
            or revision["workflow_key"] != self.definition.workflow_key
        ):
            raise MkbError(
                "workflow-binding-mismatch", "Execution binding does not match the loaded immutable workflow", 409
            )
        rows = await tx.fetchall(
            "SELECT workflow_step_uuid,step_key FROM mkb_workflow_steps WHERE workflow_revision_uuid=?",
            (execution["workflow_revision_uuid"],),
        )
        persisted = {row["step_key"] for row in rows}
        declared = set(self._steps)
        if persisted != declared:
            raise MkbError(
                "workflow-step-registry-mismatch", "Workflow revision steps do not match the loaded declaration", 409
            )

    def _route_decision(
        self,
        *,
        execution: dict[str, Any],
        source_step_key: str,
        selector: WorkflowOutcomeSelector,
        route_context: dict[str, Any],
    ) -> dict[str, Any]:
        candidates = [
            route for route in self._routes_by_source.get(source_step_key, []) if route.outcome_selector is selector
        ]
        selected: list[WorkflowRouteDefinition] = []
        guard_results: dict[str, bool] = {}
        for route in candidates:
            matched = self._guard_matches(route, route_context, guard_results)
            if not matched:
                continue
            selected.append(route)
            # A normal/branch/terminal route has a single deterministic winner.
            if route.route_kind.value != "fan_out":
                break
        payload = {
            "workflow_key": self.definition.workflow_key,
            "workflow_revision_uuid": execution["workflow_revision_uuid"],
            "execution_uuid": execution["execution_uuid"],
            "source_step_key": source_step_key,
            "outcome_selector": selector.value,
            "guard_results": guard_results,
            "routes": [route.route_key for route in selected],
        }
        return {"routes": selected, "digest": stable_digest(payload), "payload": payload}

    def _guard_matches(
        self,
        route: WorkflowRouteDefinition,
        context: dict[str, Any],
        results: dict[str, bool],
    ) -> bool:
        if route.guard_key is None:
            return True
        guard = self._guards[route.guard_key]
        if guard.predicate_type != "registered_admission_result" or guard.operator != "eq":
            raise MkbError("workflow-guard-unsupported", "Workflow guard is not supported by the bounded runtime", 409)
        result = context.get("admission_result")
        matched = result == guard.expected_value
        results[route.guard_key] = matched
        return matched

    async def _apply_routes_tx(
        self,
        tx: UnitOfWork,
        *,
        execution: dict[str, Any],
        decision: dict[str, Any],
        source_process: dict[str, Any] | None,
        route_context: dict[str, Any],
        terminal_error: str | None,
    ) -> bool:
        routes: list[WorkflowRouteDefinition] = decision["routes"]
        if not routes:
            await self._fail_execution_integrity_tx(
                tx,
                execution,
                "workflow-route-unmatched",
                "No deterministic route matched the terminal Process outcome",
            )
            return False
        changed = False
        for route in routes:
            target = self._steps[route.to_step_key]
            if target.step_kind is WorkflowStepKind.TERMINAL:
                await self._terminalize_execution_tx(
                    tx,
                    execution,
                    target.terminal_kind,
                    source_process=source_process,
                    route_digest=decision["digest"],
                    error_code=terminal_error,
                )
                changed = True
            elif target.step_kind is WorkflowStepKind.PROCESS:
                inserted = await self._materialize_process_tx(
                    tx,
                    execution=execution,
                    step=target,
                    route_digest=decision["digest"],
                )
                changed = changed or inserted
            elif target.step_kind is WorkflowStepKind.CONTROL:
                inserted = await self._enter_control_tx(
                    tx,
                    execution=execution,
                    step=target,
                    route_digest=decision["digest"],
                    source_process=source_process,
                    route_context=route_context,
                )
                changed = changed or inserted
            else:
                await self._fail_execution_integrity_tx(
                    tx,
                    execution,
                    "workflow-target-invalid",
                    "A route targeted a non-actionable workflow step",
                )
        await self._record_event_tx(
            tx,
            execution=execution,
            event_type="execution.status_changed",
            aggregate="execution",
            summary="Workflow route decision persisted",
            process_uuid=None if source_process is None else source_process["process_uuid"],
            payload=decision["payload"],
        )
        return changed

    async def _materialize_process_tx(
        self,
        tx: UnitOfWork,
        *,
        execution: dict[str, Any],
        step: WorkflowStepDefinition,
        route_digest: str,
    ) -> bool:
        step_row = await tx.fetchone(
            "SELECT workflow_step_uuid FROM mkb_workflow_steps WHERE workflow_revision_uuid=? AND step_key=?",
            (execution["workflow_revision_uuid"], step.step_key),
        )
        if step_row is None:
            raise MkbError("workflow-step-missing", "Bound workflow step is absent from the registry", 503)
        input_manifest, input_ref, input_object_digest = await self._input_manifest_tx(tx, execution, step)
        input_binding_digest = stable_digest(input_manifest)
        materialization_key = stable_digest(
            {
                "execution_uuid": execution["execution_uuid"],
                "step_key": step.step_key,
                "route_decision_digest": route_digest,
            }
        )
        process_spec_digest = stable_digest(
            {
                "workflow_revision_uuid": execution["workflow_revision_uuid"],
                "workflow_step_uuid": step_row["workflow_step_uuid"],
                "step_key": step.step_key,
                "process_key": step.process_key,
                "contract_version": step.contract_version,
                # This is the immutable *binding* shape, distinct from the
                # bytes digest carried by ``ProcessCommand`` below.  Keeping
                # both prevents a runner from confusing a graph wiring hash
                # with the object it is authorized to read.
                "input_binding_digest": input_binding_digest,
                "config_snapshot_digest": execution["config_snapshot_digest"],
                "route_decision_digest": route_digest,
            }
        )
        now = utc_now()
        process_uuid = uuid7()
        control = {
            "safe_replay": True,
            "retry_delay_seconds": self.retry_delay_seconds,
            "materialized_from_route": route_digest,
        }
        existing = await tx.fetchone(
            "SELECT * FROM mkb_processes WHERE execution_uuid=? AND workflow_step_uuid=? AND materialization_key=?",
            (execution["execution_uuid"], step_row["workflow_step_uuid"], materialization_key),
        )
        if existing is not None:
            return False
        inserted = await tx.execute(
            "INSERT INTO mkb_processes "
            "(process_uuid,team_uuid,execution_uuid,task_uuid,workflow_step_uuid,step_key,process_key,"
            "process_contract_version,materialization_key,route_decision_digest,requiredness,process_spec_digest,"
            "input_manifest_ref,input_manifest_digest,control_snapshot_ref,config_snapshot_ref,config_snapshot_digest,"
            "proof_kind,status,row_revision,available_at,priority_rank,fencing_generation,max_retries,max_recoveries,"
            "backoff_policy_json,created_at,updated_at,payload_extra) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                process_uuid,
                execution["team_uuid"],
                execution["execution_uuid"],
                execution["task_uuid"],
                step_row["workflow_step_uuid"],
                step.step_key,
                step.process_key,
                step.contract_version,
                materialization_key,
                route_digest,
                step.requiredness.value,
                process_spec_digest,
                input_ref,
                input_object_digest,
                f"mkbworkflow-control:v1:{stable_digest(control)}",
                execution["config_snapshot_ref"],
                execution["config_snapshot_digest"],
                step.required_proof_kind,
                ProcessStatus.READY.value,
                0,
                now,
                0,
                0,
                self.default_max_retries,
                self.default_max_recoveries,
                _json(control),
                now,
                now,
                "{}",
            ),
        )
        existing = await tx.fetchone(
            "SELECT * FROM mkb_processes WHERE execution_uuid=? AND workflow_step_uuid=? AND materialization_key=?",
            (execution["execution_uuid"], step_row["workflow_step_uuid"], materialization_key),
        )
        if existing is None:
            raise MkbError("process-materialization-missing", "Process insert did not create a durable Process", 500)
        await tx.execute(
            "UPDATE mkb_executions SET status='ready',phase_key=?,waiting_reason=NULL,waiting_ref=NULL,next_wake_at=NULL,"
            "current_process_uuid=?,row_revision=row_revision+1,updated_at=? "
            "WHERE execution_uuid=? AND status NOT IN ('succeeded','failed','cancelled','cancelling')",
            (
                step.phase_key.value if step.phase_key else None,
                existing["process_uuid"],
                now,
                execution["execution_uuid"],
            ),
        )
        await self._enqueue_tx(
            tx,
            execution["team_uuid"],
            "wake_process",
            {"execution_uuid": execution["execution_uuid"], "process_uuid": existing["process_uuid"]},
            f"materialize-process:{existing['process_uuid']}",
        )
        if inserted.rowcount:
            await self._record_event_tx(
                tx,
                execution=execution,
                event_type="process.materialized",
                aggregate="process",
                summary="Eligible workflow Process materialized with durable wake intent",
                process_uuid=existing["process_uuid"],
                status_before=None,
                status_after=ProcessStatus.READY.value,
                payload={"step_key": step.step_key, "route_decision_digest": route_digest},
            )
        return bool(inserted.rowcount)

    async def _input_manifest_tx(
        self, tx: UnitOfWork, execution: dict[str, Any], step: WorkflowStepDefinition
    ) -> tuple[dict[str, Any], str, str]:
        """Return the declared wiring plus a real immutable input object.

        The graph manifest itself is a deterministic specification digest.  It
        is intentionally not fabricated as a storage handle.  A Process reads
        either the root Execution's catalogued input manifest or a successful
        predecessor's catalogued output.  Legacy/in-memory unit fixtures that
        predate root manifests retain a clearly non-serving test fallback;
        production Tasks always materialize ``manifest_ref`` before scheduling.
        """

        bindings: list[dict[str, Any]] = []
        primary_ref: str | None = None
        primary_digest: str | None = None
        primary_completed_at = ""
        for binding in self.definition.bindings:
            if binding.target_step_key != step.step_key:
                continue
            source: dict[str, Any] = {"kind": binding.source_kind.value}
            if binding.source_kind.value == "prior_output":
                source_row = await tx.fetchone(
                    "SELECT output_manifest_ref,output_manifest_digest,status,completed_at FROM mkb_processes "
                    "WHERE execution_uuid=? AND step_key=? ORDER BY completed_at DESC LIMIT 1",
                    (execution["execution_uuid"], binding.source_step_key),
                )
                if source_row is None or source_row["status"] != ProcessStatus.SUCCEEDED.value:
                    raise MkbError(
                        "workflow-binding-unavailable", "Required prior output is not a terminal success", 409
                    )
                source.update(
                    {
                        "step_key": binding.source_step_key,
                        "port": binding.source_port_name,
                        "ref": source_row["output_manifest_ref"],
                        "digest": source_row["output_manifest_digest"],
                    }
                )
                # A stage output is a cumulative immutable envelope.  For a
                # multi-input node select the *most recently completed*
                # declared predecessor, rather than the incidental source
                # order in the workflow file.  It therefore carries the
                # complete predecessor state without inventing a mutable side
                # channel (for example, sealed candidate state beats an older
                # clean candidate at preflight).
                completed_at = str(source_row.get("completed_at") or "")
                if completed_at >= primary_completed_at:
                    primary_ref = source_row["output_manifest_ref"]
                    primary_digest = source_row["output_manifest_digest"]
                    primary_completed_at = completed_at
            else:
                source["ref_key"] = binding.source_ref_key
                source["execution_uuid"] = execution["execution_uuid"]
            bindings.append({"target_slot": binding.target_slot_name, "source": source})
        manifest = {
            "schema_version": "mkb.workflow-input-manifest.v1",
            "execution_uuid": execution["execution_uuid"],
            "workflow_revision_uuid": execution["workflow_revision_uuid"],
            "step_key": step.step_key,
            "bindings": bindings,
        }
        if primary_ref is not None and primary_digest is not None:
            return manifest, primary_ref, primary_digest
        if execution.get("manifest_ref") and execution.get("manifest_digest"):
            return manifest, str(execution["manifest_ref"]), str(execution["manifest_digest"])
        fallback_digest = stable_digest(manifest)
        return manifest, f"mkbworkflow-test-input:v1:{fallback_digest}", fallback_digest

    async def _enter_control_tx(
        self,
        tx: UnitOfWork,
        *,
        execution: dict[str, Any],
        step: WorkflowStepDefinition,
        route_digest: str,
        source_process: dict[str, Any] | None,
        route_context: dict[str, Any],
    ) -> bool:
        """Open a human gate only for a fully durable, exact review target.

        A route decision is not evidence.  In particular, it is never safe to
        synthesize an Artifact digest or a logical preflight reference from the
        route digest: a human would then be approving a moving/current target.
        The accept stage is already terminal at this point, so the exact Intake
        rows and the preceding preflight output must be present in this same
        transaction or the Execution fails closed.
        """

        if step.control_key != "human_review_gate":
            raise MkbError("workflow-control-unsupported", "Only the bounded human-review control is supported", 409)
        existing = await tx.fetchone(
            "SELECT * FROM mkb_execution_gates WHERE execution_uuid=? AND gate_kind=? AND status='open'",
            (execution["execution_uuid"], step.control_key),
        )
        if existing is not None:
            return False
        current_execution = await self._execution(tx, execution["execution_uuid"])
        if current_execution["status"] in _TERMINAL_EXECUTION_STATUSES | {ExecutionStatus.CANCELLING.value}:
            return False
        try:
            if route_context.get("admission_result") != "human_review_required":
                raise MkbError(
                    "gate-target-evidence-invalid",
                    "Human-review routing lacks the required admission result",
                    409,
                )
            evidence = await self._human_review_evidence_tx(tx, current_execution, source_process)
        except MkbError as exc:
            # Missing or ambiguous evidence is an integrity failure, not a
            # reason to create an empty/placeholder target or leave a Process
            # lease waiting for a decision that cannot be reviewed safely.
            if exc.code != "gate-target-evidence-invalid":
                raise
            await self._fail_execution_integrity_tx(tx, current_execution, exc.code, exc.message)
            return False

        now = utc_now()
        gate_uuid = uuid7()
        expected_execution_revision = current_execution["row_revision"] + 1
        review_target = {
            "schema_version": "mkb.execution-gate-target.v1",
            "team_uuid": current_execution["team_uuid"],
            "task_uuid": current_execution["task_uuid"],
            "execution_uuid": current_execution["execution_uuid"],
            "generation": current_execution["generation"],
            "waiting_ref": gate_uuid,
            "expected_execution_revision": expected_execution_revision,
            "workflow_binding": {
                "workflow_revision_uuid": current_execution["workflow_revision_uuid"],
                "compiled_digest": current_execution["compiled_digest"],
                "config_snapshot_digest": current_execution["config_snapshot_digest"],
                "s05_binding_digest": current_execution["s05_binding_digest"],
            },
            "route_decision_digest": route_digest,
            "accept_process": evidence["accept_process"],
            "preflight_outcome": evidence["preflight_outcome"],
            "intake_refs": evidence["intake_refs"],
            "clean_artifact": evidence["clean_artifact"],
            # This seed has explicit approval/failure routes but no declared
            # reclean route.  S05 requires reclean to take a workflow route or
            # causal restart; advertising it here would create an unsafe
            # implicit rewrite of an accepted artifact.
            "allowed_actions": ["approve", "reject"],
        }
        target_digest = stable_digest(review_target)
        await tx.execute(
            "INSERT INTO mkb_execution_gates "
            "(gate_uuid,team_uuid,task_uuid,execution_uuid,generation,gate_kind,status,gate_revision,opened_at,"
            "workflow_revision_uuid,binding_digest,payload_extra) VALUES (?,?,?,?,?,?,'open',0,?,?,?,'{}')",
            (
                gate_uuid,
                current_execution["team_uuid"],
                current_execution["task_uuid"],
                current_execution["execution_uuid"],
                current_execution["generation"],
                step.control_key,
                now,
                current_execution["workflow_revision_uuid"],
                stable_digest(
                    {
                        "route": route_digest,
                        "execution": current_execution["execution_uuid"],
                        "s05_binding_digest": current_execution["s05_binding_digest"],
                    }
                ),
            ),
        )
        await tx.execute(
            "INSERT INTO mkb_execution_gate_targets "
            "(gate_uuid,team_uuid,target_digest,review_target_json,clean_artifact_digest,preflight_outcome_ref,"
            "intake_refs_json,created_at,payload_extra) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                gate_uuid,
                current_execution["team_uuid"],
                target_digest,
                _json(review_target),
                evidence["clean_artifact"]["content_digest"],
                evidence["preflight_outcome"]["output_manifest_ref"],
                _json(evidence["intake_refs"]),
                now,
                "{}",
            ),
        )
        for stored_object in evidence["evidence_objects"]:
            await self._hold_gate_evidence_tx(
                tx,
                team_uuid=current_execution["team_uuid"],
                gate_uuid=gate_uuid,
                stored_object=stored_object,
            )
        updated = await tx.execute(
            "UPDATE mkb_executions SET status='waiting',phase_key=?,waiting_reason='human_review',waiting_ref=?,"
            "next_wake_at=NULL,row_revision=row_revision+1,updated_at=? "
            "WHERE execution_uuid=? AND row_revision=? AND status NOT IN ('succeeded','failed','cancelled','cancelling')",
            (
                step.phase_key.value if step.phase_key else None,
                gate_uuid,
                now,
                current_execution["execution_uuid"],
                current_execution["row_revision"],
            ),
        )
        if updated.rowcount != 1:
            raise ConflictError("execution-transition-conflict", "Execution could not enter the human-review wait")
        await self._record_event_tx(
            tx,
            execution=execution,
            event_type="gate.opened",
            aggregate="gate",
            summary="Execution entered durable human-review wait",
            payload={"gate_uuid": gate_uuid, "route_decision_digest": route_digest},
        )
        await self._record_event_tx(
            tx,
            execution=execution,
            event_type="execution.waiting_entered",
            aggregate="execution",
            summary="Execution waiting for a human-review Gate",
            payload={"waiting_reason": "human_review", "waiting_ref": gate_uuid},
        )
        return True

    async def _human_review_evidence_tx(
        self,
        tx: UnitOfWork,
        execution: dict[str, Any],
        source_process: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Resolve the target entirely from durable S04/S05/S03 truth.

        The predecessor edge is checked through the accept Process's immutable
        input reference.  This makes a later preflight row, an arbitrary
        current Artifact, or a same-Team row from another Execution unusable as
        Gate evidence.
        """

        def invalid(message: str) -> None:
            raise MkbError("gate-target-evidence-invalid", message, 409)

        if source_process is None:
            invalid("Human-review Gate has no source Process")
        accepted = await tx.fetchone(
            "SELECT * FROM mkb_processes WHERE process_uuid=? AND team_uuid=? AND execution_uuid=? AND task_uuid=?",
            (
                source_process["process_uuid"],
                execution["team_uuid"],
                execution["execution_uuid"],
                execution["task_uuid"],
            ),
        )
        if (
            accepted is None
            or accepted["status"] != ProcessStatus.SUCCEEDED.value
            or accepted["step_key"] != "accept_snapshot"
            or accepted["process_key"] != "intake.accept_snapshot"
            or not accepted["input_manifest_ref"]
            or not accepted["input_manifest_digest"]
            or not accepted["output_manifest_ref"]
            or not accepted["output_manifest_digest"]
            or not accepted["proof_ref"]
            or not accepted["proof_digest"]
        ):
            invalid("Human-review Gate requires a succeeded accept_snapshot Process with immutable evidence")

        preflight_rows = await tx.fetchall(
            "SELECT * FROM mkb_processes WHERE team_uuid=? AND execution_uuid=? AND task_uuid=? "
            "AND step_key='preflight_validate' AND process_key='intake.preflight_validate' AND status='succeeded' "
            "AND output_manifest_ref=? AND output_manifest_digest=? ORDER BY process_uuid",
            (
                execution["team_uuid"],
                execution["execution_uuid"],
                execution["task_uuid"],
                accepted["input_manifest_ref"],
                accepted["input_manifest_digest"],
            ),
        )
        if len(preflight_rows) != 1:
            invalid("Accepted snapshot is not bound to exactly one succeeded preflight output")
        preflight = preflight_rows[0]
        if not preflight["proof_ref"] or not preflight["proof_digest"]:
            invalid("Preflight outcome has no immutable completion proof")

        rows = await tx.fetchall(
            "SELECT s.intake_source_uuid,s.intake_snapshot_uuid,c.candidate_set_uuid,"
            "i.intake_item_uuid,r.intake_revision_uuid,a.intake_artifact_uuid AS clean_artifact_uuid,"
            "a.content_digest AS clean_artifact_digest,a.stored_object_uuid AS clean_stored_object_uuid,"
            "source_def.preflight_profile_key "
            "FROM mkb_intake_snapshots AS s "
            "JOIN mkb_intake_candidate_sets AS c ON c.team_uuid=s.team_uuid "
            " AND c.accepted_snapshot_uuid=s.intake_snapshot_uuid "
            " AND c.producer_execution_uuid=s.producer_execution_uuid "
            " AND c.preflight_outcome_ref=s.preflight_outcome_ref "
            " AND c.preflight_outcome_digest=s.preflight_outcome_digest "
            "JOIN mkb_intake_snapshot_memberships AS m ON m.team_uuid=s.team_uuid "
            " AND m.intake_snapshot_uuid=s.intake_snapshot_uuid AND m.decision_kind='accepted' "
            "JOIN mkb_intake_items AS i ON i.team_uuid=m.team_uuid AND i.intake_item_uuid=m.intake_item_uuid "
            "JOIN mkb_intake_revisions AS r ON r.team_uuid=m.team_uuid "
            " AND r.intake_revision_uuid=m.observed_revision_uuid "
            " AND r.intake_item_uuid=i.intake_item_uuid AND r.source_snapshot_uuid=s.intake_snapshot_uuid "
            "JOIN mkb_intake_artifacts AS a ON a.team_uuid=r.team_uuid "
            " AND a.owner_revision_uuid=r.intake_revision_uuid AND a.artifact_role='clean_text' "
            "JOIN mkb_intake_sources AS source ON source.team_uuid=s.team_uuid "
            " AND source.intake_source_uuid=s.intake_source_uuid "
            "JOIN mkb_source_kind_definitions AS source_def ON source_def.source_kind=source.source_kind "
            " AND source_def.definition_version=source.source_kind_definition_version "
            "WHERE s.team_uuid=? AND s.producer_execution_uuid=? "
            " AND s.preflight_outcome_ref=? AND s.preflight_outcome_digest=? "
            " AND c.staging_state='accepted' AND i.latest_revision_uuid=r.intake_revision_uuid "
            "ORDER BY s.intake_snapshot_uuid,a.intake_artifact_uuid",
            (
                execution["team_uuid"],
                execution["execution_uuid"],
                preflight["output_manifest_ref"],
                preflight["output_manifest_digest"],
            ),
        )
        if len(rows) != 1:
            invalid("Human-review Gate requires one exact accepted Intake evidence set")
        intake = rows[0]
        profile_key = intake["preflight_profile_key"]
        if not isinstance(profile_key, str) or not profile_key:
            invalid("Accepted Intake source has no exact preflight profile")
        profiles = await tx.fetchall(
            "SELECT profile_key,definition_version,check_set_digest,definition_digest "
            "FROM mkb_preflight_profile_definitions WHERE profile_key=? ORDER BY definition_version",
            (profile_key,),
        )
        if len(profiles) != 1:
            invalid("Preflight profile is missing or version-ambiguous for Gate evidence")
        profile = profiles[0]

        clean_object = await self._gate_evidence_object_tx(
            tx,
            team_uuid=execution["team_uuid"],
            stored_object_uuid=intake["clean_stored_object_uuid"],
            label="clean Artifact",
        )
        preflight_object = await tx.fetchone(
            "SELECT stored_object_uuid,content_digest,size_bytes FROM mkb_stored_objects "
            "WHERE team_uuid=? AND content_digest=? AND tombstoned_at IS NULL",
            (execution["team_uuid"], preflight["output_manifest_digest"]),
        )
        if preflight_object is None:
            invalid("Preflight output has no live catalogued object")

        return {
            "accept_process": {
                "process_uuid": accepted["process_uuid"],
                "fencing_generation": accepted["fencing_generation"],
                "output_manifest_ref": accepted["output_manifest_ref"],
                "output_manifest_digest": accepted["output_manifest_digest"],
                "proof_ref": accepted["proof_ref"],
                "proof_digest": accepted["proof_digest"],
            },
            "preflight_outcome": {
                "process_uuid": preflight["process_uuid"],
                "fencing_generation": preflight["fencing_generation"],
                "output_manifest_ref": preflight["output_manifest_ref"],
                "output_manifest_digest": preflight["output_manifest_digest"],
                "proof_ref": preflight["proof_ref"],
                "proof_digest": preflight["proof_digest"],
                "profile_key": profile["profile_key"],
                "profile_definition_version": profile["definition_version"],
                "profile_definition_digest": profile["definition_digest"],
                "check_set_digest": profile["check_set_digest"],
            },
            "intake_refs": {
                "intake_source_uuid": intake["intake_source_uuid"],
                "candidate_set_uuid": intake["candidate_set_uuid"],
                "intake_snapshot_uuid": intake["intake_snapshot_uuid"],
                "intake_item_uuid": intake["intake_item_uuid"],
                "intake_revision_uuid": intake["intake_revision_uuid"],
            },
            "clean_artifact": {
                "intake_artifact_uuid": intake["clean_artifact_uuid"],
                "content_digest": intake["clean_artifact_digest"],
            },
            "evidence_objects": (clean_object, preflight_object),
        }

    async def _gate_evidence_object_tx(
        self,
        tx: UnitOfWork,
        *,
        team_uuid: str,
        stored_object_uuid: Any,
        label: str,
    ) -> dict[str, Any]:
        if not isinstance(stored_object_uuid, str) or not stored_object_uuid:
            raise MkbError("gate-target-evidence-invalid", f"{label} has no catalogued object", 409)
        row = await tx.fetchone(
            "SELECT stored_object_uuid,content_digest,size_bytes FROM mkb_stored_objects "
            "WHERE team_uuid=? AND stored_object_uuid=? AND tombstoned_at IS NULL",
            (team_uuid, stored_object_uuid),
        )
        if row is None:
            raise MkbError("gate-target-evidence-invalid", f"{label} object is unavailable", 409)
        return row

    async def _hold_gate_evidence_tx(
        self,
        tx: UnitOfWork,
        *,
        team_uuid: str,
        gate_uuid: str,
        stored_object: dict[str, Any],
    ) -> None:
        """Protect target bytes while the Gate remains durable and open."""

        await tx.execute(
            "INSERT INTO mkb_object_references "
            "(reference_uuid,team_uuid,stored_object_uuid,purpose,owner_kind,owner_uuid,expected_digest,expected_size,"
            "created_at,payload_extra) VALUES (?,?,?,'gate_evidence','execution_gate',?,?,?,?, '{}')",
            (
                uuid7(),
                team_uuid,
                stored_object["stored_object_uuid"],
                gate_uuid,
                stored_object["content_digest"],
                stored_object["size_bytes"],
                utc_now(),
            ),
        )

    async def _route_after_terminal_process_tx(
        self,
        tx: UnitOfWork,
        execution: dict[str, Any],
        process: dict[str, Any],
        selector: WorkflowOutcomeSelector,
        route_context: dict[str, Any],
        terminal_error: str | None,
    ) -> None:
        decision = self._route_decision(
            execution=execution,
            source_step_key=process["step_key"],
            selector=selector,
            route_context=route_context,
        )
        await self._apply_routes_tx(
            tx,
            execution=execution,
            decision=decision,
            source_process=process,
            route_context=route_context,
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
    ) -> None:
        now = utc_now()
        updated = await tx.execute(
            "UPDATE mkb_processes SET status='failed',accepted_outcome_digest=COALESCE(?,accepted_outcome_digest),"
            "error_class='workflow-stage',error_code=?,error_message=?,failure_disposition=?,claim_token_hash=NULL,"
            "lease_owner=NULL,lease_expires_at=NULL,heartbeat_at=NULL,completed_at=?,row_revision=row_revision+1,updated_at=? "
            "WHERE process_uuid=? AND status NOT IN ('succeeded','failed','cancelled')",
            (
                accepted_outcome_digest,
                error_code,
                error_message[:512],
                failure_disposition,
                now,
                now,
                process["process_uuid"],
            ),
        )
        if updated.rowcount:
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
                payload={"error_code": error_code, "failure_disposition": failure_disposition},
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

    async def _project_root_task_tx(
        self,
        tx: UnitOfWork,
        execution: dict[str, Any],
        status: str,
        source_process: dict[str, Any] | None,
        error_code: str | None,
        error_message: str | None,
    ) -> None:
        if execution["root_execution_uuid"] != execution["execution_uuid"]:
            return
        now = utc_now()
        task_status = {
            ExecutionStatus.SUCCEEDED.value: "succeeded",
            ExecutionStatus.FAILED.value: "failed",
            ExecutionStatus.CANCELLED.value: "cancelled",
        }[status]
        await tx.execute(
            "UPDATE mkb_tasks SET status=?,result_ref=?,proof_ref=?,error_code=?,error_message=?,completed_at=?,"
            "row_revision=row_revision+1,updated_at=? "
            "WHERE team_uuid=? AND task_uuid=? AND current_root_execution_uuid=? "
            "AND status NOT IN ('succeeded','failed','cancelled')",
            (
                task_status,
                None if source_process is None else source_process.get("output_manifest_ref"),
                None if source_process is None else source_process.get("proof_ref"),
                error_code,
                error_message,
                now,
                now,
                execution["team_uuid"],
                execution["task_uuid"],
                execution["execution_uuid"],
            ),
        )

    async def _fail_execution_integrity_tx(
        self, tx: UnitOfWork, execution: dict[str, Any], error_code: str, message: str
    ) -> None:
        now = utc_now()
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
            await self._project_root_task_tx(tx, execution, ExecutionStatus.FAILED.value, None, error_code, message)
            await self._record_event_tx(
                tx,
                execution=execution,
                event_type="execution.status_changed",
                aggregate="execution",
                summary="Execution failed closed on a workflow integrity violation",
                status_before=execution["status"],
                status_after=ExecutionStatus.FAILED.value,
                severity="error",
                payload={"error_code": error_code},
            )

    async def _converge_cancellation_tx(self, tx: UnitOfWork, execution: dict[str, Any]) -> bool:
        now = utc_now()
        active = await tx.fetchone(
            "SELECT COUNT(*) AS count FROM mkb_processes WHERE execution_uuid=? "
            "AND status IN ('ready','claimed','running','retry_wait','cancelling')",
            (execution["execution_uuid"],),
        )
        if active is not None and active["count"]:
            return False
        current = await self._execution(tx, execution["execution_uuid"])
        if current["status"] != ExecutionStatus.CANCELLING.value:
            return False
        updated = await tx.execute(
            "UPDATE mkb_executions SET status='cancelled',cancel_converged_at=?,completed_at=?,current_process_uuid=NULL,"
            "terminal_summary_digest=?,summary_completed_at=?,row_revision=row_revision+1,updated_at=? "
            "WHERE execution_uuid=? AND status='cancelling'",
            (
                now,
                now,
                stable_digest({"execution_uuid": execution["execution_uuid"], "terminal_status": "cancelled"}),
                now,
                now,
                execution["execution_uuid"],
            ),
        )
        if updated.rowcount:
            await self._project_root_task_tx(tx, current, ExecutionStatus.CANCELLED.value, None, None, None)
            await self._record_event_tx(
                tx,
                execution=current,
                event_type="execution.status_changed",
                aggregate="execution",
                summary="Execution cancellation converged after all Processes became terminal",
                status_before=ExecutionStatus.CANCELLING.value,
                status_after=ExecutionStatus.CANCELLED.value,
                payload={},
            )
            return True
        return False

    async def _refresh_execution_counts_tx(self, tx: UnitOfWork, execution_uuid: str) -> None:
        rows = await tx.fetchall(
            "SELECT status,COUNT(*) AS count FROM mkb_processes WHERE execution_uuid=? GROUP BY status",
            (execution_uuid,),
        )
        by_status = {row["status"]: row["count"] for row in rows}
        total = sum(by_status.values())
        active = sum(by_status.get(status, 0) for status in _ACTIVE_PROCESS_STATUSES)
        now = utc_now()
        await tx.execute(
            "UPDATE mkb_executions SET total_process_count=?,active_process_count=?,succeeded_process_count=?,"
            "failed_process_count=?,cancelled_process_count=?,updated_at=? WHERE execution_uuid=?",
            (
                total,
                active,
                by_status.get(ProcessStatus.SUCCEEDED.value, 0),
                by_status.get(ProcessStatus.FAILED.value, 0),
                by_status.get(ProcessStatus.CANCELLED.value, 0),
                now,
                execution_uuid,
            ),
        )

    async def _enqueue_tx(
        self, tx: UnitOfWork, team_uuid: str, kind: str, payload: dict[str, Any], dedupe_key: str
    ) -> None:
        now = utc_now()
        payload_json = _json(payload)
        await tx.execute(
            "INSERT OR IGNORE INTO mkb_outbox "
            "(outbox_id,team_uuid,kind,payload_json,payload_digest,dedupe_key,status,available_at,created_at,updated_at,payload_extra) "
            "VALUES (?,?,?,?,?,?,'pending',?,?,?,'{}')",
            (uuid7(), team_uuid, kind, payload_json, stable_digest(payload), dedupe_key, now, now, now),
        )

    async def _record_event_tx(
        self,
        tx: UnitOfWork,
        *,
        execution: dict[str, Any],
        event_type: str,
        aggregate: str,
        summary: str,
        process_uuid: str | None = None,
        status_before: str | None = None,
        status_after: str | None = None,
        payload: dict[str, Any],
        severity: str = "info",
    ) -> None:
        now = utc_now()
        await tx.execute(
            "INSERT INTO mkb_domain_events "
            "(event_uuid,team_uuid,trace_uuid,event_type,aggregate,severity,task_uuid,execution_uuid,process_uuid,"
            "actor_kind,status_before,status_after,summary,payload_digest,payload_json,schema_version,occurred_at,"
            "recorded_at,payload_extra) VALUES (?,?,?,?,?,?,?,?,?,'system',?,?,?,?,?,?,?,?,'{}')",
            (
                uuid7(),
                execution["team_uuid"],
                execution["trace_uuid"],
                event_type,
                aggregate,
                severity,
                execution["task_uuid"],
                execution["execution_uuid"],
                process_uuid,
                status_before,
                status_after,
                summary[:512],
                stable_digest(payload),
                _json(payload),
                "mkb.domain-event.v1",
                now,
                now,
            ),
        )

    def _command_from_process(self, process: dict[str, Any]) -> ProcessCommand:
        required = (
            "input_manifest_ref",
            "input_manifest_digest",
            "config_snapshot_ref",
            "config_snapshot_digest",
            "process_spec_digest",
            "domain_binding_digest",
        )
        if any(not process.get(key) for key in required):
            raise MkbError("process-command-integrity", "Claimed Process is missing immutable command material", 503)
        return ProcessCommand(
            schema_version="mkb.process-command.v1",
            team_uuid=process["team_uuid"],
            task_uuid=process["task_uuid"],
            trace_uuid=process["trace_uuid"],
            execution_uuid=process["execution_uuid"],
            process_uuid=process["process_uuid"],
            process_key=process["process_key"],
            process_contract_version=process["process_contract_version"],
            fencing_generation=process["fencing_generation"],
            command_input_digest=process["process_spec_digest"],
            input_manifest_ref=process["input_manifest_ref"],
            input_manifest_digest=process["input_manifest_digest"],
            config_snapshot_ref=process["config_snapshot_ref"],
            config_snapshot_digest=process["config_snapshot_digest"],
            binding_digest=process["domain_binding_digest"],
        )

    def _assert_outcome_identity(self, process: dict[str, Any], outcome: ProcessOutcome) -> None:
        fields = ("team_uuid", "task_uuid", "execution_uuid", "process_uuid")
        if any(process[field] != getattr(outcome, field) for field in fields):
            raise ConflictError(
                "outcome-identity-mismatch", "Process outcome identity does not match the claimed Process"
            )
        if process["fencing_generation"] != outcome.fencing_generation:
            raise ConflictError("stale-process-fence", "Process outcome fence is no longer current")

    async def _gate_target_for_action_tx(self, tx: UnitOfWork, gate_uuid: str, action: str) -> dict[str, Any]:
        """Load and validate the immutable review target before any decision.

        Gate actions are a target-owned bounded set, not a public string enum
        that may be accepted merely because a caller supplied it.  Keeping this
        check in the engine protects outbox replay as well as the Task surface.
        """

        target = await tx.fetchone(
            "SELECT target_digest,review_target_json FROM mkb_execution_gate_targets WHERE gate_uuid=?",
            (gate_uuid,),
        )
        if target is None:
            raise MkbError("gate-target-missing", "Execution Gate has no frozen review target", 409)
        try:
            review_target = json.loads(target["review_target_json"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise MkbError("gate-target-invalid", "Execution Gate review target is malformed", 409) from exc
        actions = review_target.get("allowed_actions") if isinstance(review_target, dict) else None
        if (
            not isinstance(actions, list)
            or not actions
            or any(item not in {"approve", "reject", "reclean"} for item in actions)
            or len(set(actions)) != len(actions)
        ):
            raise MkbError("gate-target-invalid", "Execution Gate allowed actions are invalid", 409)
        if action not in actions:
            raise ConflictError("gate-action-not-allowed", "Gate action is not allowed by its frozen review target")
        return target

    def _control_step(self) -> WorkflowStepDefinition:
        controls = [step for step in self.definition.steps if step.step_kind is WorkflowStepKind.CONTROL]
        if len(controls) != 1:
            raise MkbError("workflow-control-ambiguous", "Bounded runtime requires exactly one control step", 409)
        return controls[0]

    @staticmethod
    def _safe_replay(policy_json: str | None) -> bool:
        if policy_json is None:
            return False
        try:
            policy = json.loads(policy_json)
        except (TypeError, json.JSONDecodeError):
            return False
        return isinstance(policy, dict) and policy.get("safe_replay") is True

    async def _complete_outbox(self, outbox_id: str, lease_owner: str) -> None:
        now = utc_now()
        async with self.persistence.transaction() as tx:
            await tx.execute(
                "UPDATE mkb_outbox SET status='done',lease_owner=NULL,lease_expires_at=NULL,updated_at=? "
                "WHERE outbox_id=? AND status='in_flight' AND lease_owner=?",
                (now, outbox_id, lease_owner),
            )

    async def _release_outbox(self, outbox_id: str, lease_owner: str, error: str) -> None:
        now = utc_now()
        async with self.persistence.transaction() as tx:
            row = await tx.fetchone("SELECT attempts FROM mkb_outbox WHERE outbox_id=?", (outbox_id,))
            if row is None:
                return
            status = "dead" if row["attempts"] >= 8 else "pending"
            await tx.execute(
                "UPDATE mkb_outbox SET status=?,lease_owner=NULL,lease_expires_at=NULL,last_error=?,available_at=?,updated_at=? "
                "WHERE outbox_id=? AND status='in_flight' AND lease_owner=?",
                (status, error[:512], _add_seconds(now, 1), now, outbox_id, lease_owner),
            )


class WorkflowWorker:
    """Small worker loop that invokes an injected stage handler exactly via claims."""

    def __init__(self, runtime: WorkflowRuntime, handler: ProcessStageHandler) -> None:
        self.runtime = runtime
        self.handler = handler

    @staticmethod
    def _failure_outcome(
        command: ProcessCommand,
        *,
        disposition: Literal["failed", "retryable_failure"],
        error_code: str,
        error_message: str,
    ) -> ProcessOutcome:
        """Build one canonical fallback Outcome for an already claimed Process."""

        provisional = ProcessOutcome(
            schema_version="mkb.process-outcome.v1",
            team_uuid=command.team_uuid,
            task_uuid=command.task_uuid,
            execution_uuid=command.execution_uuid,
            process_uuid=command.process_uuid,
            fencing_generation=command.fencing_generation,
            disposition=disposition,
            outcome_digest="0" * 64,
            error_code=error_code[:128],
            error_message=error_message[:512],
        )
        return provisional.model_copy(update={"outcome_digest": canonical_outcome_digest(provisional)})

    async def run_once(self, lease_owner: str, *, lease_seconds: int = 30) -> bool:
        """Claim, start, invoke, and submit one Process outcome."""

        claim = await self.runtime.claim_next(lease_owner, lease_seconds=lease_seconds)
        if claim is None:
            return False
        await self.runtime.mark_running(claim.command.process_uuid, claim.command.fencing_generation)
        try:
            outcome = await self.handler.run(claim.command)
        except Exception as exc:  # Stage exception becomes an explicit bounded retryable outcome.
            outcome = self._failure_outcome(
                claim.command,
                disposition="retryable_failure",
                error_code="stage-handler-exception",
                error_message=str(exc)[:512] or "Stage handler raised an exception",
            )
        try:
            await self.runtime.accept_outcome(outcome)
        except ConflictError:
            # These are the durable stale/lease/status fences.  A worker must
            # never submit a different failure Outcome over a competing owner.
            raise
        except MkbError as exc:
            # A typed callback/committer rejection aborted its success UoW, so
            # the Process is still running at this exact claim fence.  Submit
            # the domain failure as a terminal Outcome rather than waiting for
            # lease recovery to discover an otherwise deterministic error.
            await self.runtime.accept_outcome(
                self._failure_outcome(
                    claim.command,
                    disposition="failed",
                    error_code=exc.code,
                    error_message=exc.message,
                )
            )
        except Exception:
            # Unexpected commit failures can be transient (for example a
            # database adapter interruption).  The Process retry policy owns
            # the bounded retry/recovery decision; do not expose raw details.
            await self.runtime.accept_outcome(
                self._failure_outcome(
                    claim.command,
                    disposition="retryable_failure",
                    error_code="outcome-commit-exception",
                    error_message="Outcome commit raised an unexpected error",
                )
            )
        return True


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _add_seconds(value: str, seconds: int) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (
        (parsed.astimezone(UTC) + timedelta(seconds=seconds)).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


def _required_payload_uuid(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise MkbError("outbox-payload-invalid", f"Outbox payload must contain {key}", 500)
    return value


__all__ = [
    "ClaimedProcess",
    "OutboxDelivery",
    "ProcessOutcomeCommitter",
    "ProcessStageHandler",
    "WorkflowRuntime",
    "WorkflowWorker",
    "canonical_outcome_digest",
]
