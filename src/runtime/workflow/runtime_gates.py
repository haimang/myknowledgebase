"""runtime gates"""

from __future__ import annotations

import json
from typing import Any

from src.contracts.common.errors import ConflictError, MkbError, NotFoundError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.models import ExecutionStatus, ProcessStatus
from src.contracts.common.time import utc_now
from src.contracts.workflow.models import (
    WorkflowOutcomeSelector,
)
from src.persistence.ports import UnitOfWork
from src.runtime.workflow.constants import (
    _TERMINAL_EXECUTION_STATUSES,
)


class WorkflowGatesMixin:
    """runtime gates"""

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
            plan = await self._assert_execution_binding(tx, execution)
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
            control = self._control_step(plan, gate["gate_kind"])
            if action == "approve":
                await tx.execute(
                    "UPDATE mkb_executions SET status='ready',waiting_reason=NULL,waiting_ref=NULL,next_wake_at=NULL,"
                    "row_revision=row_revision+1,updated_at=? WHERE execution_uuid=? AND status='waiting' AND waiting_ref=?",
                    (now, execution["execution_uuid"], gate_uuid),
                )
                updated_execution = await self._execution(tx, execution["execution_uuid"])
                decision = self._route_decision(
                    plan=plan,
                    execution=updated_execution,
                    source_step_key=control.step_key,
                    selector=WorkflowOutcomeSelector.SUCCEEDED,
                    route_context={"gate_action": action},
                )
                await self._apply_routes_tx(
                    tx,
                    plan=plan,
                    execution=updated_execution,
                    decision=decision,
                    source_process=None,
                    route_context={"gate_action": action},
                    terminal_error=None,
                )
            elif action == "reject":
                decision = self._route_decision(
                    plan=plan,
                    execution=execution,
                    source_step_key=control.step_key,
                    selector=WorkflowOutcomeSelector.FAILED,
                    route_context={"gate_action": action},
                )
                await self._apply_routes_tx(
                    tx,
                    plan=plan,
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

        The public Task service owns decision admission and Gate CAS only.
        This consumer is the sole writer of Execution resume/failure for that
        command (D02 R3).  It never rewrites the terminal Gate state.
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
            if execution["status"] == ExecutionStatus.WAITING.value:
                now = utc_now()
                resumed = await tx.execute(
                    "UPDATE mkb_executions SET status='ready',waiting_reason=NULL,waiting_ref=NULL,next_wake_at=NULL,"
                    "row_revision=row_revision+1,updated_at=? "
                    "WHERE execution_uuid=? AND status='waiting' AND waiting_ref=?",
                    (now, execution["execution_uuid"], decision["gate_uuid"]),
                )
                if resumed.rowcount != 1:
                    raise ConflictError(
                        "gate-execution-projection-missing",
                        "Gate decision could not resume the waiting Execution",
                    )
                execution = await self._execution(tx, decision["execution_uuid"])
            plan = await self._assert_execution_binding(tx, execution)
            control = self._control_step(plan, decision["gate_kind"])
            if decision["action"] == "approve":
                if execution["status"] not in {ExecutionStatus.RUNNING.value, ExecutionStatus.READY.value}:
                    raise ConflictError(
                        "gate-execution-projection-missing",
                        "Gate decision was not projected to a resumable Execution",
                    )
                selector = WorkflowOutcomeSelector.SUCCEEDED
                terminal_error = None
            elif decision["action"] == "reject":
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
            typed = await self._typed_route_context_tx(tx, execution)
            typed["gate_action"] = decision["action"]
            decision_result = self._route_decision(
                plan=plan,
                execution=execution,
                source_step_key=control.step_key,
                selector=selector,
                route_context=typed,
            )
            changed = await self._apply_routes_tx(
                tx,
                plan=plan,
                execution=execution,
                decision=decision_result,
                source_process=None,
                route_context=typed,
                terminal_error=terminal_error,
            )
            await self._refresh_execution_counts_tx(tx, execution["execution_uuid"])
            return changed


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
