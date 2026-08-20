"""runtime core"""

from __future__ import annotations

import json
import secrets
from collections.abc import Awaitable, Callable
from typing import Any

from src.contracts.common.errors import ConflictError, MkbError, NotFoundError, NotReadyError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.models import ExecutionStatus, ProcessStatus
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand, ProcessOutcome
from src.contracts.workflow.models import (
    WorkflowDefinition,
    WorkflowOutcomeSelector,
    WorkflowStepKind,
)
from src.persistence.ports import PersistencePort, UnitOfWork
from src.runtime.workflow.constants import (
    _ACTIVE_PROCESS_STATUSES,
    _TERMINAL_EXECUTION_STATUSES,
)
from src.runtime.workflow.dispatch import (
    OVER_BUDGET_PROCESS_KEYS,
    DispatchCaps,
    choose_pool,
    get_pool_occupancies,
    pool_kind,
)
from src.runtime.workflow.helpers import (
    _add_seconds,
    _compiled_workflow_digest,
    _json,
)
from src.runtime.workflow.types import (
    ClaimedProcess,
    ProcessOutcomeCommitter,
    ReadinessProbe,
)
from src.services.billing import BillingPort, DefaultBillingService


class WorkflowCoreMixin:
    """runtime core"""

    def __init__(
        self,
        persistence: PersistencePort,
        definition: WorkflowDefinition,
        *,
        additional_definitions: tuple[WorkflowDefinition, ...] = (),
        compatibility_definitions: tuple[WorkflowDefinition, ...] = (),
        readiness: ReadinessProbe | Callable[[], Awaitable[bool]] | None = None,
        outcome_committer: ProcessOutcomeCommitter | None = None,
        billing: BillingPort | None = None,
        dispatch_caps: DispatchCaps | None = None,
        live_inference: bool = True,
        default_max_retries: int = 3,
        default_max_recoveries: int = 3,
        retry_delay_seconds: int = 1,
        cleanup_recovery_window_seconds: int = 60,
    ) -> None:
        if default_max_retries < 0 or default_max_recoveries < 0:
            raise ValueError("retry and recovery limits must be non-negative")
        if retry_delay_seconds < 0:
            raise ValueError("retry_delay_seconds must be non-negative")
        if cleanup_recovery_window_seconds < 0:
            raise ValueError("cleanup recovery window must be non-negative")
        self.persistence = persistence
        self.definition = definition
        self.readiness = readiness
        self.outcome_committer = outcome_committer
        self.billing = billing or DefaultBillingService()
        self.dispatch_caps = dispatch_caps or DispatchCaps()
        self.live_inference = live_inference
        self.default_max_retries = default_max_retries
        self.default_max_recoveries = default_max_recoveries
        self.retry_delay_seconds = retry_delay_seconds
        # A terminal row remains recoverable for this bounded interval even
        # when all of its visible Process facts are already terminal.  The
        # evaluator below only appends eligibility evidence; physical archive
        # or deletion stays in the S12/S15 retention owner.
        self.cleanup_recovery_window_seconds = cleanup_recovery_window_seconds
        active_definitions = (definition, *additional_definitions)
        self._active_workflow_keys = {candidate.workflow_key for candidate in active_definitions}
        if len(self._active_workflow_keys) != len(active_definitions):
            raise ValueError("active workflow definitions must have distinct workflow_key values")
        self._plans_by_compiled_digest: dict[str, WorkflowDefinition] = {}
        for candidate in (*compatibility_definitions, *active_definitions):
            if candidate.workflow_key not in self._active_workflow_keys:
                raise ValueError("compatibility definition must belong to an active workflow key")
            compiled_digest = _compiled_workflow_digest(candidate)
            existing = self._plans_by_compiled_digest.get(compiled_digest)
            if existing is not None and existing != candidate:
                raise ValueError("different compatibility definitions share a compiled digest")
            self._plans_by_compiled_digest[compiled_digest] = candidate


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
            if execution["status"] == ExecutionStatus.WAITING.value:
                if execution.get("waiting_reason") == "scatter_children":
                    changed = await self._maybe_converge_scatter_root_tx(tx, execution)
                    await self._refresh_execution_counts_tx(tx, execution["execution_uuid"])
                    return changed
                # Other typed waits (notably human review and retry) may only
                # be resumed by their own bounded transition, never by a
                # duplicate root wake replay.
                return False
            plan = await self._assert_execution_binding(tx, execution)
            task = await tx.fetchone(
                "SELECT request_intent FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
                (execution["team_uuid"], execution["task_uuid"]),
            )
            if task is None or not isinstance(task.get("request_intent"), str):
                await self._fail_execution_integrity_tx(
                    tx,
                    execution,
                    "workflow-task-intent-missing",
                    "Execution has no durable Task intent for static route selection",
                )
                return False
            route_context = {"request_intent": task["request_intent"]}
            start = next(step for step in plan.steps if step.step_kind is WorkflowStepKind.START)
            decision = self._route_decision(
                plan=plan,
                execution=execution,
                source_step_key=start.step_key,
                selector=WorkflowOutcomeSelector.ALWAYS,
                route_context=route_context,
            )
            if not decision["routes"]:
                await self._fail_execution_integrity_tx(
                    tx, execution, "workflow-start-route-missing", "The bound workflow has no eligible start route"
                )
                return False
            changed = await self._apply_routes_tx(
                tx,
                plan=plan,
                execution=execution,
                decision=decision,
                source_process=None,
                route_context=route_context,
                terminal_error=None,
            )
            await self._refresh_execution_counts_tx(tx, execution["execution_uuid"])
            return changed


    def _dispatch_facts_from_audit(self, payload_json: str | None) -> dict[str, Any]:
        """Recover frozen admit inputs from the task audit envelope."""

        explicit_channel: str | None = None
        channel_source = "priority"
        source_chars = 0
        if payload_json:
            try:
                envelope = json.loads(payload_json)
            except (TypeError, json.JSONDecodeError):
                envelope = {}
            payload = envelope.get("payload") if isinstance(envelope, dict) else None
            if isinstance(payload, dict):
                raw = payload.get("compression_channel")
                source = payload.get("channel_source")
                if raw in {"local-inference", "non-interactive"} and source == "explicit":
                    explicit_channel = raw
                    channel_source = "explicit"
                elif raw in {"local-inference", "non-interactive"} and source is None:
                    # Audit dumps the original request. An explicit field is present
                    # only when the caller set compression_channel.
                    explicit_channel = raw
                    channel_source = "explicit"
                origin = payload.get("source")
                if isinstance(origin, dict) and isinstance(origin.get("size_bytes"), int):
                    source_chars = origin["size_bytes"]
        inference_mode = "live" if self.live_inference else "deterministic"
        return {
            "snapshot": {
                "l2": {
                    "inference_mode": inference_mode,
                    "compression_channel": explicit_channel,
                    "channel_source": channel_source,
                }
            },
            "explicit_channel": explicit_channel,
            "channel_source": channel_source,
            "source_chars": source_chars,
        }

    async def _admit_one_tx(
        self,
        tx: UnitOfWork,
        row: dict[str, Any],
        *,
        pool: str | None,
        now: str,
        priority: str,
        channel_source: str,
    ) -> bool:
        updated = await tx.execute(
            "UPDATE mkb_processes SET dispatch_admitted=1, dispatch_pool=?, dispatch_enqueued_at=?, updated_at=? "
            "WHERE process_uuid=? AND dispatch_admitted=0",
            (pool, now, now, row["process_uuid"]),
        )
        if updated.rowcount != 1:
            return False
        label = "unpooled dispatch" if pool is None else f"{pool} dispatch pool"
        await self._record_event_tx(
            tx,
            execution=row,
            event_type="process.dispatch_admitted",
            aggregate="process",
            summary=f"Process admitted to {label}",
            process_uuid=row["process_uuid"],
            payload={"pool": pool, "priority": priority, "channel_source": channel_source},
        )
        return True

    async def _admit_waiting_processes_tx(self, tx: UnitOfWork, now: str) -> None:
        """Admit queued processes into pools within capacity limits (T-O-353 / T-O-355 / T-O-356)."""

        occupancies = await get_pool_occupancies(tx)
        local_queued = occupancies["local-inference"].queued
        ni_queued = occupancies["non-interactive"].queued
        embed_queued = occupancies["embed"].queued
        caps = self.dispatch_caps
        billing = getattr(self, "billing", None) or DefaultBillingService()

        waiting_rows = await tx.fetchall(
            "SELECT p.process_uuid, p.process_key, p.execution_uuid, p.task_uuid, p.team_uuid,"
            "p.priority_rank, p.available_at, p.created_at, e.trace_uuid, t.priority, "
            "a.strict_payload_json "
            "FROM mkb_processes AS p "
            "JOIN mkb_executions AS e ON e.execution_uuid=p.execution_uuid AND e.team_uuid=p.team_uuid "
            "JOIN mkb_tasks AS t ON t.team_uuid=p.team_uuid AND t.task_uuid=p.task_uuid "
            "LEFT JOIN mkb_task_audits AS a ON a.team_uuid=p.team_uuid AND a.task_uuid=p.task_uuid "
            "WHERE p.status='ready' AND p.dispatch_admitted = 0 AND p.available_at <= ? "
            "AND e.status IN ('ready','running') AND t.status IN ('queued','running')",
            (now,),
        )

        classified: list[tuple[dict[str, Any], str, dict[str, Any]]] = []
        for row in waiting_rows:
            facts = self._dispatch_facts_from_audit(row.get("strict_payload_json"))
            kind = pool_kind(row["process_key"], facts["snapshot"])
            classified.append((row, kind, facts))

        unpooled = [item for item in classified if item[1] == "unpooled"]
        embeds = [item for item in classified if item[1] == "embed"]
        generates = [item for item in classified if item[1] == "generate"]
        embeds.sort(key=lambda item: (item[0]["available_at"] or "", item[0]["created_at"] or "", item[0]["process_uuid"]))
        generates.sort(
            key=lambda item: (
                -(item[0]["priority_rank"] or 0),
                item[0]["available_at"] or "",
                item[0]["created_at"] or "",
                item[0]["process_uuid"],
            )
        )

        for row, _kind, facts in unpooled:
            await self._admit_one_tx(
                tx,
                row,
                pool=None,
                now=now,
                priority=row["priority"] or "normal",
                channel_source=facts["channel_source"],
            )

        for row, _kind, facts in embeds:
            if embed_queued >= caps.embed_queued:
                break
            if await self._admit_one_tx(
                tx,
                row,
                pool="embed",
                now=now,
                priority=row["priority"] or "normal",
                channel_source=facts["channel_source"],
            ):
                embed_queued += 1

        for row, _kind, facts in generates:
            priority = row["priority"] or "normal"
            over_budget = (
                row["process_key"] in OVER_BUDGET_PROCESS_KEYS
                and facts["source_chars"] > caps.local_char_budget
            )
            pool = choose_pool(
                priority,
                "generate",
                local_queued=local_queued,
                ni_queued=ni_queued,
                local_available=self.live_inference,
                ni_quota=billing.has_quota("non-interactive"),
                over_budget=over_budget,
                explicit_channel=facts["explicit_channel"],
                local_queued_cap=caps.local_queued,
                ni_queued_cap=caps.ni_queued,
            )
            if pool == "local-inference" and local_queued < caps.local_queued:
                if await self._admit_one_tx(
                    tx,
                    row,
                    pool="local-inference",
                    now=now,
                    priority=priority,
                    channel_source=facts["channel_source"],
                ):
                    local_queued += 1
            elif pool == "non-interactive" and ni_queued < caps.ni_queued:
                if await self._admit_one_tx(
                    tx,
                    row,
                    pool="non-interactive",
                    now=now,
                    priority=priority,
                    channel_source=facts["channel_source"],
                ):
                    ni_queued += 1

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
            for _ in range(64):
                expired = await tx.fetchone(
                    "SELECT p.*, e.trace_uuid, e.status AS execution_status, e.domain_binding_digest,"
                    "e.workflow_uuid,e.workflow_revision_uuid,e.compiled_digest "
                    "FROM mkb_processes AS p JOIN mkb_executions AS e "
                    "ON e.execution_uuid=p.execution_uuid AND e.team_uuid=p.team_uuid "
                    "JOIN mkb_tasks AS t ON t.team_uuid=p.team_uuid AND t.task_uuid=p.task_uuid "
                    "WHERE p.status='ready' AND p.deadline_at IS NOT NULL AND p.deadline_at < ? "
                    "AND e.status IN ('ready','running') AND t.status IN ('queued','running') "
                    "LIMIT 1",
                    (now,),
                )
                if expired is not None:
                    await self._fail_expired_ready_tx(tx, expired)
                    continue

                # Same-transaction admission for waiting processes
                await self._admit_waiting_processes_tx(tx, now)

                # Query pool occupancy to check running capacity
                occupancies = await get_pool_occupancies(tx)
                caps = self.dispatch_caps
                local_can_run = 1 if occupancies["local-inference"].running < caps.local_running else 0
                ni_can_run = 1 if occupancies["non-interactive"].running < caps.ni_running else 0
                embed_can_run = occupancies["embed"].running < caps.embed_running

                embed_candidate = None
                if embed_can_run:
                    embed_candidate = await tx.fetchone(
                        "SELECT p.*, e.trace_uuid, e.status AS execution_status, e.domain_binding_digest,"
                        "e.workflow_uuid,e.workflow_revision_uuid,e.compiled_digest, t.priority AS task_priority "
                        "FROM mkb_processes AS p JOIN mkb_executions AS e "
                        "ON e.execution_uuid=p.execution_uuid AND e.team_uuid=p.team_uuid "
                        "JOIN mkb_tasks AS t ON t.team_uuid=p.team_uuid AND t.task_uuid=p.task_uuid "
                        "WHERE p.status='ready' AND p.available_at<=? AND p.dispatch_admitted = 1 "
                        "AND p.dispatch_pool = 'embed' "
                        "AND e.status IN ('ready','running') AND t.status IN ('queued','running') "
                        "ORDER BY p.available_at ASC, p.created_at ASC, p.process_uuid ASC "
                        "LIMIT 1",
                        (now,),
                    )
                other_candidate = await tx.fetchone(
                    "SELECT p.*, e.trace_uuid, e.status AS execution_status, e.domain_binding_digest,"
                    "e.workflow_uuid,e.workflow_revision_uuid,e.compiled_digest, t.priority AS task_priority "
                    "FROM mkb_processes AS p JOIN mkb_executions AS e "
                    "ON e.execution_uuid=p.execution_uuid AND e.team_uuid=p.team_uuid "
                    "JOIN mkb_tasks AS t ON t.team_uuid=p.team_uuid AND t.task_uuid=p.task_uuid "
                    "WHERE p.status='ready' AND p.available_at<=? AND p.dispatch_admitted = 1 "
                    "AND ("
                    "  p.dispatch_pool IS NULL "
                    "  OR (p.dispatch_pool = 'local-inference' AND ? = 1) "
                    "  OR (p.dispatch_pool = 'non-interactive' AND ? = 1)"
                    ") "
                    "AND e.status IN ('ready','running') AND t.status IN ('queued','running') "
                    "ORDER BY "
                    "  p.priority_rank DESC,"
                    "  p.available_at ASC,"
                    "  CASE WHEN p.deadline_at IS NULL THEN 1 ELSE 0 END, p.deadline_at ASC,"
                    "  p.created_at ASC, p.process_uuid ASC "
                    "LIMIT 1",
                    (now, local_can_run, ni_can_run),
                )
                if embed_candidate is not None and other_candidate is not None:
                    embed_key = (
                        embed_candidate["available_at"] or "",
                        embed_candidate["created_at"] or "",
                        embed_candidate["process_uuid"],
                    )
                    other_key = (
                        other_candidate["available_at"] or "",
                        other_candidate["created_at"] or "",
                        other_candidate["process_uuid"],
                    )
                    candidate = embed_candidate if embed_key <= other_key else other_candidate
                else:
                    candidate = embed_candidate if embed_candidate is not None else other_candidate
                if candidate is None:
                    return None
                # Do not lease a side-effecting Process unless its immutable
                # revision has a reviewed interpreter in this deployment.  This
                # closes the gap where an old Execution could be claimed under a
                # newer graph and only fail after the handler had already run.
                await self._assert_execution_binding(tx, candidate)
                if candidate["deadline_at"] is not None and candidate["deadline_at"] < now:
                    await self._fail_expired_ready_tx(tx, candidate)
                    continue
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
                    continue
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
            return None


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
                # Single owned projection path (D01 review R2).
                from src.contracts.common.models import TaskStatus
                from src.runtime.task.task_projection import project_task_status_tx
                from src.services.events import DomainEventWriter

                await project_task_status_tx(
                    tx,
                    team_uuid=execution["team_uuid"],
                    task_uuid=execution["task_uuid"],
                    target=TaskStatus.RUNNING,
                    events=DomainEventWriter(),
                    trace_uuid=execution.get("trace_uuid"),
                    current_root_execution_uuid=execution["execution_uuid"],
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


    async def _fail_expired_ready_tx(self, tx: UnitOfWork, row: dict[str, Any]) -> None:
        await self._assert_execution_binding(tx, row)
        await self._fail_process_tx(
            tx,
            row,
            error_code="deadline-exceeded-before-start",
            error_message="The process deadline elapsed before it could be claimed",
            failure_disposition="deadline",
        )
        execution = await self._execution(tx, row["execution_uuid"])
        await self._route_after_terminal_process_tx(
            tx, execution, row, WorkflowOutcomeSelector.FAILED, {}, "deadline-exceeded-before-start"
        )
        await self._refresh_execution_counts_tx(tx, row["execution_uuid"])

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


    async def _assert_ready_for_claim(self) -> None:
        if self.readiness is not None:
            ready = await self.readiness()
        else:
            readiness = await self.persistence.readiness()
            ready = all(
                readiness.get(name)
                for name in ("db_primary", "schema_migration", "concurrent_writes", "native_vector")
            )
        if not ready:
            raise NotReadyError("workflow-not-ready", "Readiness is false; new Process claims are fenced")


    async def _execution(self, tx: UnitOfWork, execution_uuid: str) -> dict[str, Any]:
        row = await tx.fetchone("SELECT * FROM mkb_executions WHERE execution_uuid=?", (execution_uuid,))
        if row is None:
            raise NotFoundError("execution-not-found", "Execution was not found")
        return row


    async def _process_with_execution(self, tx: UnitOfWork, process_uuid: str) -> dict[str, Any]:
        row = await tx.fetchone(
            "SELECT p.*,e.trace_uuid,e.status AS execution_status,e.domain_binding_digest,"
            "t.priority AS task_priority "
            "FROM mkb_processes AS p JOIN mkb_executions AS e "
            "ON e.execution_uuid=p.execution_uuid AND e.team_uuid=p.team_uuid "
            "JOIN mkb_tasks AS t ON t.team_uuid=p.team_uuid AND t.task_uuid=p.task_uuid "
            "WHERE p.process_uuid=?",
            (process_uuid,),
        )
        if row is None:
            raise NotFoundError("process-not-found", "Process was not found")
        return row


    async def _assert_execution_binding(self, tx: UnitOfWork, execution: dict[str, Any]) -> WorkflowDefinition:
        """Return the exact static plan pinned by an Execution's digest.

        Registry revision rows are immutable, but the active revision may move
        while an outbox wake or Process lease for an older execution remains
        outstanding.  Resolve the execution's stored digest against reviewed
        compatibility declarations, never against the currently active graph.
        """

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
            or revision["workflow_key"] not in self._active_workflow_keys
        ):
            raise MkbError(
                "workflow-binding-mismatch", "Execution binding does not match the loaded immutable workflow", 409
            )
        plan = self._plans_by_compiled_digest.get(str(execution["compiled_digest"]))
        if plan is None:
            raise MkbError(
                "workflow-compiled-plan-unavailable",
                "No reviewed runtime plan is available for the execution's immutable workflow revision",
                503,
            )
        if plan.workflow_key != revision["workflow_key"]:
            raise MkbError(
                "workflow-binding-mismatch", "Execution digest resolved to a different immutable workflow key", 409
            )
        rows = await tx.fetchall(
            "SELECT workflow_step_uuid,step_key FROM mkb_workflow_steps WHERE workflow_revision_uuid=?",
            (execution["workflow_revision_uuid"],),
        )
        persisted = {row["step_key"] for row in rows}
        declared = {step.step_key for step in plan.steps}
        if persisted != declared:
            raise MkbError(
                "workflow-step-registry-mismatch", "Workflow revision steps do not match the loaded declaration", 409
            )
        return plan


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
        # Task progress is an Execution-membership projection, not a count of
        # workflow steps.  A single-root intake therefore has exactly one
        # required member, while a future scatter root can project all of its
        # child Executions through the same query.  Keeping this update in the
        # outcome transaction prevents the public Task view from reporting a
        # terminal success alongside stale all-zero counters.
        execution = await tx.fetchone(
            "SELECT team_uuid,task_uuid,root_execution_uuid FROM mkb_executions WHERE execution_uuid=?",
            (execution_uuid,),
        )
        if execution is None:
            raise MkbError("execution-not-found", "Execution disappeared while refreshing progress", 409)
        root = await tx.fetchone(
            "SELECT execution_uuid,execution_role FROM mkb_executions WHERE execution_uuid=?",
            (execution["root_execution_uuid"],),
        )
        if root is not None and root.get("execution_role") == "scatter_root":
            task = await tx.fetchone(
                "SELECT intake_snapshot_uuid,change_set_uuid FROM mkb_tasks "
                "WHERE team_uuid=? AND task_uuid=? AND current_root_execution_uuid=?",
                (execution["team_uuid"], execution["task_uuid"], root["execution_uuid"]),
            )
            if task is not None and task.get("intake_snapshot_uuid") and task.get("change_set_uuid"):
                expected = await self._scatter_expected_members_tx(
                    tx,
                    team_uuid=execution["team_uuid"],
                    snapshot_uuid=task["intake_snapshot_uuid"],
                    change_set_uuid=task["change_set_uuid"],
                )
                if expected is not None:
                    await self._refresh_scatter_task_counts_tx(
                        tx,
                        team_uuid=execution["team_uuid"],
                        task_uuid=execution["task_uuid"],
                        root_execution_uuid=root["execution_uuid"],
                        expected=expected,
                    )
                    return
        member_rows = await tx.fetchall(
            "WITH child_count AS ("
            "  SELECT COUNT(*) AS count FROM mkb_executions "
            "  WHERE team_uuid=? AND task_uuid=? AND root_execution_uuid=? AND parent_execution_uuid IS NOT NULL"
            ") "
            "SELECT requiredness,status,COUNT(*) AS count FROM mkb_executions "
            "WHERE team_uuid=? AND task_uuid=? AND root_execution_uuid=? "
            "AND (parent_execution_uuid IS NOT NULL OR (SELECT count FROM child_count)=0) "
            "GROUP BY requiredness,status",
            (
                execution["team_uuid"],
                execution["task_uuid"],
                execution["root_execution_uuid"],
                execution["team_uuid"],
                execution["task_uuid"],
                execution["root_execution_uuid"],
            ),
        )
        member_total = sum(int(row["count"]) for row in member_rows)
        member_required = sum(int(row["count"]) for row in member_rows if row["requiredness"] == "required")
        member_active = sum(
            int(row["count"])
            for row in member_rows
            if row["status"]
            in {
                ExecutionStatus.CREATED.value,
                ExecutionStatus.READY.value,
                ExecutionStatus.RUNNING.value,
                ExecutionStatus.WAITING.value,
                ExecutionStatus.CANCELLING.value,
            }
        )
        member_succeeded = sum(
            int(row["count"]) for row in member_rows if row["status"] == ExecutionStatus.SUCCEEDED.value
        )
        member_failed = sum(int(row["count"]) for row in member_rows if row["status"] == ExecutionStatus.FAILED.value)
        member_cancelled = sum(
            int(row["count"]) for row in member_rows if row["status"] == ExecutionStatus.CANCELLED.value
        )
        await tx.execute(
            "UPDATE mkb_tasks SET cnt_total=?,cnt_required=?,cnt_active=?,cnt_succeeded=?,cnt_failed=?,"
            "cnt_cancelled=?,cnt_skipped=0,row_revision=row_revision+1,updated_at=? "
            "WHERE team_uuid=? AND task_uuid=? AND current_root_execution_uuid=?",
            (
                member_total,
                member_required,
                member_active,
                member_succeeded,
                member_failed,
                member_cancelled,
                now,
                execution["team_uuid"],
                execution["task_uuid"],
                execution["root_execution_uuid"],
            ),
        )


    async def _refresh_scatter_task_counts_tx(
        self,
        tx: UnitOfWork,
        *,
        team_uuid: str,
        task_uuid: str,
        root_execution_uuid: str,
        expected: list[dict[str, Any]],
    ) -> None:
        """Project counts from the accepted denominator, never child-row count."""

        rows = await tx.fetchall(
            "SELECT execution_uuid,execution_role,requiredness,target_kind,target_uuid,status,"
            "scatter_intake_revision_uuid,scatter_member_ordinal,scatter_change_set_uuid "
            "FROM mkb_executions WHERE team_uuid=? AND task_uuid=? AND root_execution_uuid=? "
            "AND parent_execution_uuid=? ORDER BY execution_uuid",
            (team_uuid, task_uuid, root_execution_uuid, root_execution_uuid),
        )
        expected_by_item = {member["intake_item_uuid"]: member for member in expected}
        by_item: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            target_uuid = row.get("target_uuid")
            if isinstance(target_uuid, str) and target_uuid in expected_by_item:
                by_item.setdefault(target_uuid, []).append(row)
        statuses: list[str] = []
        for item_uuid, member in expected_by_item.items():
            candidates = by_item.get(item_uuid, [])
            if len(candidates) != 1:
                statuses.append(ExecutionStatus.CREATED.value)
                continue
            candidate = candidates[0]
            if (
                candidate.get("execution_role") != "scatter_child"
                or candidate.get("requiredness") != "required"
                or candidate.get("target_kind") != "intake_item"
                or candidate.get("scatter_intake_revision_uuid") != member["intake_revision_uuid"]
                or candidate.get("scatter_member_ordinal") != member["member_ordinal"]
            ):
                statuses.append(ExecutionStatus.CREATED.value)
                continue
            statuses.append(str(candidate["status"]))
        total = len(expected)
        active = sum(
            status
            in {
                ExecutionStatus.CREATED.value,
                ExecutionStatus.READY.value,
                ExecutionStatus.RUNNING.value,
                ExecutionStatus.WAITING.value,
                ExecutionStatus.CANCELLING.value,
            }
            for status in statuses
        )
        succeeded = sum(status == ExecutionStatus.SUCCEEDED.value for status in statuses)
        failed = sum(status == ExecutionStatus.FAILED.value for status in statuses)
        cancelled = sum(status == ExecutionStatus.CANCELLED.value for status in statuses)
        now = utc_now()
        await tx.execute(
            "UPDATE mkb_executions SET total_child_count=?,active_child_count=?,succeeded_child_count=?,"
            # Progress counters are a derived projection.  They must not
            # perturb the root control CAS revision after a Gate target has
            # frozen it; otherwise an innocent child-count refresh makes a
            # still-open human Gate spuriously stale.
            "failed_child_count=?,cancelled_child_count=?,updated_at=? WHERE execution_uuid=?",
            (total, active, succeeded, failed, cancelled, now, root_execution_uuid),
        )
        await tx.execute(
            "UPDATE mkb_tasks SET cnt_total=?,cnt_required=?,cnt_active=?,cnt_succeeded=?,cnt_failed=?,"
            "cnt_cancelled=?,cnt_skipped=0,row_revision=row_revision+1,updated_at=? "
            "WHERE team_uuid=? AND task_uuid=? AND current_root_execution_uuid=?",
            (
                total,
                total,
                active,
                succeeded,
                failed,
                cancelled,
                now,
                team_uuid,
                task_uuid,
                root_execution_uuid,
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
        from src.services.events import DomainEventWriter

        await DomainEventWriter().write(
            tx,
            team_uuid=execution["team_uuid"],
            trace_uuid=execution["trace_uuid"],
            event_type=event_type,
            aggregate=aggregate,
            summary=summary[:512],
            task_uuid=execution.get("task_uuid"),
            execution_uuid=execution.get("execution_uuid"),
            process_uuid=process_uuid,
            payload=payload,
            severity=severity,
            status_before=status_before,
            status_after=status_after,
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
            dispatch_pool=process.get("dispatch_pool"),
            task_priority=process.get("task_priority"),
        )


    def _assert_outcome_identity(self, process: dict[str, Any], outcome: ProcessOutcome) -> None:
        fields = ("team_uuid", "task_uuid", "execution_uuid", "process_uuid")
        if any(process[field] != getattr(outcome, field) for field in fields):
            raise ConflictError(
                "outcome-identity-mismatch", "Process outcome identity does not match the claimed Process"
            )
        if process["fencing_generation"] != outcome.fencing_generation:
            raise ConflictError("stale-process-fence", "Process outcome fence is no longer current")
