"""runtime repair"""

from __future__ import annotations

from typing import Any

from src.contracts.common.ids import stable_digest
from src.contracts.common.models import ExecutionStatus, ProcessStatus
from src.contracts.common.time import utc_now
from src.contracts.workflow.models import (
    WorkflowOutcomeSelector,
)
from src.persistence.ports import UnitOfWork
from src.runtime.workflow.constants import (
    _TERMINAL_EXECUTION_STATUSES,
)
from src.runtime.workflow.helpers import (
    _add_seconds,
)


class WorkflowRepairMixin:
    """runtime repair"""

    async def repair_once(self) -> int:
        """Run bounded semantic recovery; repeated calls are idempotent.

        The database is the scheduling truth.  This scanner only rebuilds
        legal Engine intents from that truth; it never invents a route,
        approval, child denominator, or publication proof from queue/log
        state.  Ambiguous terminal-route or waiting rows fail closed.
        """

        repaired = await self.promote_due_retries()
        repaired += await self.recover_expired_leases()
        async with self.persistence.transaction() as tx:
            # Gate decisions are immutable causal truth.  Re-delivering the
            # decision invokes the same bounded resume path and is safer than
            # waking a review-gated root as though it were a fresh start.
            decisions = await tx.fetchall(
                "SELECT d.decision_uuid,d.team_uuid FROM mkb_execution_gate_decisions AS d "
                "JOIN mkb_execution_gates AS g ON g.gate_uuid=d.gate_uuid "
                "WHERE (d.action='approve' AND g.status='released') OR (d.action='reject' AND g.status='rejected')",
            )
            for decision in decisions:
                before = await tx.fetchone(
                    "SELECT outbox_id FROM mkb_outbox WHERE team_uuid=? AND dedupe_key IN (?,?)",
                    (
                        decision["team_uuid"],
                        f"gate-decision:{decision['decision_uuid']}",
                        f"repair-gate-decision:{decision['decision_uuid']}",
                    ),
                )
                if before is None:
                    await self._enqueue_tx(
                        tx,
                        decision["team_uuid"],
                        "gate_decision",
                        {"decision_uuid": decision["decision_uuid"]},
                        f"repair-gate-decision:{decision['decision_uuid']}",
                    )
                    repaired += 1

            # A root cancellation may have been committed before its cancel
            # outbox delivery.  Continue the same recursive fence path here.
            cancelling_roots = await tx.fetchall(
                "SELECT * FROM mkb_executions WHERE execution_uuid=root_execution_uuid "
                "AND status='cancelling' ORDER BY execution_uuid",
            )
            for root in cancelling_roots:
                repaired += await self._cancel_execution_tree_tx(tx, root, include_root=True)

            ready_processes = await tx.fetchall(
                "SELECT p.process_uuid,p.execution_uuid,p.team_uuid,p.fencing_generation FROM mkb_processes AS p "
                "JOIN mkb_executions AS e ON e.execution_uuid=p.execution_uuid "
                "WHERE p.status='ready' AND e.status NOT IN ('succeeded','failed','cancelled','cancelling') "
                "ORDER BY p.process_uuid",
            )
            for process in ready_processes:
                dedupe = f"repair-wake-process:{process['process_uuid']}:{process['fencing_generation']}"
                exists = await tx.fetchone(
                    "SELECT outbox_id FROM mkb_outbox WHERE team_uuid=? AND dedupe_key=?",
                    (process["team_uuid"], dedupe),
                )
                if exists is None:
                    await self._enqueue_tx(
                        tx,
                        process["team_uuid"],
                        "wake_process",
                        {"execution_uuid": process["execution_uuid"], "process_uuid": process["process_uuid"]},
                        dedupe,
                    )
                    repaired += 1

            # Materialized child Executions have no Process until their first
            # start route is interpreted.  Never include durable_prerequisite
            # rows here: root review approval is their only release authority.
            ready_executions = await tx.fetchall(
                "SELECT e.execution_uuid,e.team_uuid,e.task_uuid,e.generation,e.manifest_revision FROM mkb_executions AS e "
                "WHERE e.status IN ('created','ready') AND e.status NOT IN ('succeeded','failed','cancelled','cancelling') "
                "AND NOT EXISTS (SELECT 1 FROM mkb_processes AS p WHERE p.execution_uuid=e.execution_uuid "
                " AND p.status IN ('ready','claimed','running','retry_wait','cancelling')) "
                "ORDER BY e.execution_uuid",
            )
            for execution in ready_executions:
                dedupe = f"repair-wake-execution:{execution['execution_uuid']}:{execution['manifest_revision']}"
                exists = await tx.fetchone(
                    "SELECT outbox_id FROM mkb_outbox WHERE team_uuid=? AND dedupe_key=?",
                    (execution["team_uuid"], dedupe),
                )
                if exists is None:
                    await self._enqueue_tx(
                        tx,
                        execution["team_uuid"],
                        "wake_execution",
                        {
                            "execution_uuid": execution["execution_uuid"],
                            "task_uuid": execution["task_uuid"],
                            "generation": execution["generation"],
                        },
                        dedupe,
                    )
                    repaired += 1

            stalled = await tx.fetchall(
                "SELECT e.*,p.status AS process_status,p.process_uuid AS stalled_process_uuid "
                "FROM mkb_executions AS e JOIN mkb_processes AS p ON p.process_uuid=e.current_process_uuid "
                "WHERE e.status NOT IN ('waiting','cancelling','succeeded','failed','cancelled') "
                "AND p.status IN ('succeeded','failed','cancelled') "
                # A committed Gate decision is the only safe route context
                # for its preceding guarded accept process.  Its durable
                # decision outbox is repaired above; re-evaluating the old
                # branch with an empty context would fail a valid review.
                "AND NOT EXISTS (SELECT 1 FROM mkb_execution_gates AS g "
                " JOIN mkb_execution_gate_decisions AS d ON d.gate_uuid=g.gate_uuid "
                " WHERE g.execution_uuid=e.execution_uuid) "
                "ORDER BY e.execution_uuid",
            )
            for execution in stalled:
                repaired += int(await self._repair_terminal_process_transition_tx(tx, execution))

            waits = await tx.fetchall(
                "SELECT * FROM mkb_executions WHERE status='waiting' ORDER BY execution_uuid",
            )
            for execution in waits:
                reason = execution.get("waiting_reason")
                if reason == "scatter_children":
                    repaired += int(await self._maybe_converge_scatter_root_tx(tx, execution))
                    continue
                if reason == "durable_prerequisite":
                    parent_uuid = execution.get("parent_execution_uuid")
                    parent = (
                        await self._execution(tx, parent_uuid)
                        if isinstance(parent_uuid, str) and parent_uuid
                        else None
                    )
                    if (
                        execution.get("execution_role") == "scatter_child"
                        and parent is not None
                        and parent.get("execution_role") == "scatter_root"
                        and execution.get("waiting_ref")
                    ):
                        if parent["status"] in _TERMINAL_EXECUTION_STATUSES:
                            await self._cancel_execution_tree_tx(tx, parent, include_root=False)
                            repaired += 1
                        # An open root Gate or a committed decision that will
                        # be replayed above are both valid; do not wake child.
                        continue
                    await self._fail_execution_integrity_tx(
                        tx,
                        execution,
                        "waiting-prerequisite-invalid",
                        "Execution has an invalid durable prerequisite wait",
                    )
                    repaired += 1
                    continue
                if reason == "human_review":
                    gate = await tx.fetchone(
                        "SELECT gate_uuid,status FROM mkb_execution_gates WHERE gate_uuid=? AND execution_uuid=?",
                        (execution.get("waiting_ref"), execution["execution_uuid"]),
                    )
                    if gate is not None and gate["status"] == "open":
                        continue
                    # S02 may have CAS-closed the Gate while the S03 outbox
                    # resume is still pending (D02 R3 two-phase ownership).
                    pending = await tx.fetchone(
                        "SELECT o.outbox_id FROM mkb_outbox AS o "
                        "JOIN mkb_execution_gate_decisions AS d "
                        "ON json_extract(o.payload_json,'$.decision_uuid')=d.decision_uuid "
                        "WHERE o.team_uuid=? AND o.kind='gate_decision' AND o.status IN ('pending','in_flight') "
                        "AND d.gate_uuid=?",
                        (execution["team_uuid"], execution.get("waiting_ref")),
                    )
                    if pending is not None or (
                        gate is not None and gate["status"] in {"released", "rejected", "superseded"}
                    ):
                        continue
                    await self._fail_execution_integrity_tx(
                        tx,
                        execution,
                        "waiting-gate-invalid",
                        "Execution human-review wait has no current open Gate",
                    )
                    repaired += 1
                    continue
                if reason == "retry_due":
                    process = await tx.fetchone(
                        "SELECT process_uuid FROM mkb_processes WHERE process_uuid=? AND execution_uuid=? "
                        "AND status='retry_wait'",
                        (execution.get("waiting_ref"), execution["execution_uuid"]),
                    )
                    if process is not None:
                        continue
                    await self._fail_execution_integrity_tx(
                        tx,
                        execution,
                        "waiting-retry-invalid",
                        "Execution retry wait has no matching retry Process",
                    )
                    repaired += 1
                    continue
                await self._fail_execution_integrity_tx(
                    tx,
                    execution,
                    "waiting-reason-invalid",
                    "Execution waiting state has no registered durable trigger",
                )
                repaired += 1

            terminal_roots = await tx.fetchall(
                "SELECT * FROM mkb_executions WHERE execution_uuid=root_execution_uuid "
                "AND status IN ('succeeded','failed','cancelled') ORDER BY execution_uuid",
            )
            for root in terminal_roots:
                repaired += await self._repair_terminal_projection_tx(tx, root)
            repaired += await self._evaluate_cleanup_eligibility_tx(tx)
        return repaired


    async def evaluate_cleanup_eligibility_once(self, *, limit: int = 256) -> int:
        """Append cleanup eligibility fences for safely quiescent Processes.

        This is intentionally a marker-only operation.  It never deletes a
        Process, Execution, Task, audit record, Intake fact, vector record, or
        observability evidence.  The scanner can run repeatedly: its CAS only
        fills a previously-null eligibility pair, preserving the first durable
        terminal fence as historical evidence.
        """

        if not 1 <= limit <= 10_000:
            raise ValueError("cleanup eligibility limit must be between 1 and 10000")
        async with self.persistence.transaction() as tx:
            return await self._evaluate_cleanup_eligibility_tx(tx, limit=limit)


    async def _evaluate_cleanup_eligibility_tx(self, tx: UnitOfWork, *, limit: int = 256) -> int:
        """Evaluate the S03 terminal-cleanup predicate from durable facts only."""

        now = utc_now()
        recovery_not_before = _add_seconds(now, -self.cleanup_recovery_window_seconds)
        # ``mkb_outbox`` intentionally has one typed payload column rather
        # than an execution foreign-key.  The direct execution UUID handles
        # wakes/cancels/process scheduling; the gate join covers a durable
        # decision payload, which carries only its decision UUID.  Done/dead
        # deliveries are historical evidence, not pending control intent.
        candidates = await tx.fetchall(
            "SELECT p.*,e.trace_uuid,e.status AS execution_status,e.row_revision AS execution_row_revision,"
            "e.terminal_summary_digest,e.summary_completed_at,e.completed_at AS execution_completed_at,"
            "e.current_process_uuid,e.publication_proof_ref "
            "FROM mkb_processes AS p JOIN mkb_executions AS e "
            "ON e.team_uuid=p.team_uuid AND e.execution_uuid=p.execution_uuid "
            "WHERE p.status IN ('succeeded','failed','cancelled') "
            "AND p.cleanup_eligible_at IS NULL "
            "AND e.status IN ('succeeded','failed','cancelled') "
            "AND e.terminal_summary_digest IS NOT NULL AND e.summary_completed_at IS NOT NULL "
            "AND e.completed_at IS NOT NULL AND e.completed_at<=? "
            "AND e.current_process_uuid IS NULL "
            "AND (e.status<>'succeeded' OR e.publication_proof_ref IS NOT NULL) "
            "AND NOT EXISTS (SELECT 1 FROM mkb_processes AS active "
            "  WHERE active.execution_uuid=e.execution_uuid "
            "  AND active.status IN ('ready','claimed','running','retry_wait','cancelling')) "
            "AND NOT EXISTS (SELECT 1 FROM mkb_processes AS leased "
            "  WHERE leased.execution_uuid=e.execution_uuid "
            "  AND leased.lease_expires_at IS NOT NULL AND leased.lease_expires_at>?) "
            "AND NOT EXISTS ("
            "  SELECT 1 FROM mkb_outbox AS o "
            "  LEFT JOIN mkb_execution_gate_decisions AS d "
            "    ON o.kind='gate_decision' AND json_extract(o.payload_json,'$.decision_uuid')=d.decision_uuid "
            "  LEFT JOIN mkb_execution_gates AS g ON g.gate_uuid=d.gate_uuid "
            "  WHERE o.team_uuid=e.team_uuid AND o.status IN ('pending','in_flight') "
            "  AND (json_extract(o.payload_json,'$.execution_uuid')=e.execution_uuid OR g.execution_uuid=e.execution_uuid)"
            ") "
            "ORDER BY e.completed_at ASC,p.completed_at ASC,p.process_uuid ASC LIMIT ?",
            (recovery_not_before, now, limit),
        )
        marked = 0
        for process in candidates:
            fence_digest = stable_digest(
                {
                    "schema_version": "mkb.process-cleanup-fence.v1",
                    "team_uuid": process["team_uuid"],
                    "execution_uuid": process["execution_uuid"],
                    "process_uuid": process["process_uuid"],
                    "process_status": process["status"],
                    "process_fencing_generation": process["fencing_generation"],
                    "execution_status": process["execution_status"],
                    "execution_row_revision": process["execution_row_revision"],
                    "terminal_summary_digest": process["terminal_summary_digest"],
                    "summary_completed_at": process["summary_completed_at"],
                    "execution_completed_at": process["execution_completed_at"],
                }
            )
            updated = await tx.execute(
                "UPDATE mkb_processes SET cleanup_eligible_at=?,cleanup_fence_digest=?,"
                "row_revision=row_revision+1,updated_at=? "
                "WHERE process_uuid=? AND cleanup_eligible_at IS NULL "
                "AND status IN ('succeeded','failed','cancelled')",
                (now, fence_digest, now, process["process_uuid"]),
            )
            if updated.rowcount != 1:
                continue
            marked += 1
            await self._record_event_tx(
                tx,
                execution=process,
                event_type="process.cleanup_eligible",
                aggregate="process",
                summary="Process met the terminal cleanup eligibility predicate",
                process_uuid=process["process_uuid"],
                status_before=process["status"],
                status_after=process["status"],
                payload={
                    "cleanup_fence_digest": fence_digest,
                    "recovery_window_seconds": self.cleanup_recovery_window_seconds,
                },
            )
        return marked


    async def _repair_terminal_process_transition_tx(self, tx: UnitOfWork, execution: dict[str, Any]) -> bool:
        """Re-drive an unambiguous terminal Process route, otherwise fail loud."""

        process = await self._process_with_execution(tx, execution["stalled_process_uuid"])
        selector = {
            ProcessStatus.SUCCEEDED.value: WorkflowOutcomeSelector.SUCCEEDED,
            ProcessStatus.FAILED.value: WorkflowOutcomeSelector.FAILED,
            ProcessStatus.CANCELLED.value: WorkflowOutcomeSelector.CANCELLED,
        }[process["status"]]
        plan = await self._assert_execution_binding(tx, execution)
        candidates = [
            route
            for route in plan.routes
            if route.from_step_key == process["step_key"] and route.outcome_selector is selector and route.guard_key is None
        ]
        if len(candidates) != 1:
            await self._fail_execution_integrity_tx(
                tx,
                execution,
                "repair-terminal-route-ambiguous",
                "Terminal Process has no uniquely reconstructable route context",
            )
            return True
        decision = self._route_decision(
            plan=plan,
            execution=execution,
            source_step_key=process["step_key"],
            selector=selector,
            route_context={},
        )
        await self._apply_routes_tx(
            tx,
            plan=plan,
            execution=execution,
            decision=decision,
            source_process=process,
            route_context={},
            terminal_error=process.get("error_code") if selector is WorkflowOutcomeSelector.FAILED else None,
        )
        return True


    async def _repair_terminal_projection_tx(self, tx: UnitOfWork, root: dict[str, Any]) -> int:
        """Close projection-only terminal gaps from already terminal facts."""

        await self._refresh_execution_counts_tx(tx, root["execution_uuid"])
        changed = 0
        cleared = await tx.execute(
            "UPDATE mkb_executions SET current_process_uuid=NULL,row_revision=row_revision+1,updated_at=? "
            "WHERE execution_uuid=? AND current_process_uuid IS NOT NULL",
            (utc_now(), root["execution_uuid"]),
        )
        changed += int(bool(cleared.rowcount))
        from src.contracts.common.models import TaskStatus
        from src.runtime.task.task_projection import project_task_status_tx
        from src.services.events import DomainEventWriter

        task_status = {
            ExecutionStatus.SUCCEEDED.value: TaskStatus.SUCCEEDED,
            ExecutionStatus.FAILED.value: TaskStatus.FAILED,
            ExecutionStatus.CANCELLED.value: TaskStatus.CANCELLED,
        }[root["status"]]
        projected = await project_task_status_tx(
            tx,
            team_uuid=root["team_uuid"],
            task_uuid=root["task_uuid"],
            target=task_status,
            events=DomainEventWriter(),
            trace_uuid=root.get("trace_uuid"),
            current_root_execution_uuid=root["execution_uuid"],
            result_ref=root.get("result_ref"),
            proof_ref=root.get("publication_proof_ref"),
            error_code=root.get("final_error_code"),
            error_message=root.get("final_error_message"),
        )
        changed += int(bool(projected))
        return changed
