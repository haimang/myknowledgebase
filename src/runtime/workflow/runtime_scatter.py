"""runtime scatter"""

from __future__ import annotations

import json
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest
from src.contracts.common.models import ExecutionStatus, ProcessStatus
from src.contracts.common.time import utc_now
from src.contracts.workflow.models import (
    WorkflowDefinition,
    WorkflowTerminalKind,
)
from src.persistence.ports import UnitOfWork
from src.runtime.workflow.constants import (
    _TERMINAL_EXECUTION_STATUSES,
)


class WorkflowScatterMixin:
    """runtime scatter"""

    async def _enter_scatter_children_join_tx(
        self,
        tx: UnitOfWork,
        *,
        plan: WorkflowDefinition,
        execution: dict[str, Any],
        route_digest: str,
        source_process: dict[str, Any] | None,
    ) -> bool:
        """Enter the durable collect-all wait after acceptance committed N intents.

        The expected denominator is not the current child-row count.  It is
        the accepted Snapshot/ChangeSet required set, which the acceptance
        transaction wrote before it made any child wake visible.
        """

        del plan
        current = await self._execution(tx, execution["execution_uuid"])
        if current["status"] in _TERMINAL_EXECUTION_STATUSES | {ExecutionStatus.CANCELLING.value}:
            return False
        task = await tx.fetchone(
            "SELECT intake_snapshot_uuid,change_set_uuid FROM mkb_tasks "
            "WHERE team_uuid=? AND task_uuid=? AND current_root_execution_uuid=?",
            (current["team_uuid"], current["task_uuid"], current["execution_uuid"]),
        )
        if (
            task is None
            or not task.get("intake_snapshot_uuid")
            or not task.get("change_set_uuid")
            or current.get("intake_snapshot_uuid") != task["intake_snapshot_uuid"]
        ):
            await self._fail_execution_integrity_tx(
                tx,
                current,
                "scatter-acceptance-binding-missing",
                "Scatter join has no exact accepted Snapshot and ChangeSet binding",
            )
            return False
        expected = await self._scatter_expected_members_tx(
            tx,
            team_uuid=current["team_uuid"],
            snapshot_uuid=task["intake_snapshot_uuid"],
            change_set_uuid=task["change_set_uuid"],
        )
        if expected is None:
            await self._fail_execution_integrity_tx(
                tx,
                current,
                "scatter-required-set-invalid",
                "Scatter ChangeSet does not match the accepted required membership set",
            )
            return False
        if not expected:
            # A complete zero-member observation is a real business terminal,
            # not a queue-empty heuristic.  A Gate decision/recovery can
            # reach this control with no in-memory source Process, so resolve
            # the immutable accepted-set Process from durable rows instead of
            # treating that call-shape as an integrity failure.
            terminal_proof = await self._scatter_root_terminal_proof_tx(tx, current, source_process)
            if terminal_proof is None:
                await self._fail_execution_integrity_tx(
                    tx,
                    current,
                    "scatter-zero-proof-missing",
                    "Zero-member Scatter Snapshot has no immutable acceptance proof",
                )
                return False
            await self._terminalize_execution_tx(
                tx,
                current,
                WorkflowTerminalKind.SUCCESS,
                source_process=terminal_proof,
                route_digest=route_digest,
                error_code=None,
            )
            return True
        await self._release_scatter_children_tx(
            tx,
            root=current,
            change_set_uuid=task["change_set_uuid"],
        )
        now = utc_now()
        updated = await tx.execute(
            "UPDATE mkb_executions SET status='waiting',phase_key='fan_in',waiting_reason='scatter_children',"
            "waiting_ref=?,next_wake_at=NULL,current_process_uuid=NULL,row_revision=row_revision+1,updated_at=? "
            "WHERE execution_uuid=? AND status NOT IN ('succeeded','failed','cancelled','cancelling')",
            (task["change_set_uuid"], now, current["execution_uuid"]),
        )
        if updated.rowcount:
            await self._record_event_tx(
                tx,
                execution=current,
                event_type="execution.waiting_entered",
                aggregate="execution",
                summary="Scatter root waiting for the accepted required child set",
                process_uuid=None if source_process is None else source_process["process_uuid"],
                status_before=current["status"],
                status_after=ExecutionStatus.WAITING.value,
                payload={
                    "waiting_reason": "scatter_children",
                    "change_set_uuid": task["change_set_uuid"],
                    "required_member_count": len(expected),
                    "route_decision_digest": route_digest,
                },
            )
        await self._refresh_execution_counts_tx(tx, current["execution_uuid"])
        return bool(updated.rowcount)


    async def _scatter_expected_members_tx(
        self,
        tx: UnitOfWork,
        *,
        team_uuid: str,
        snapshot_uuid: str,
        change_set_uuid: str,
    ) -> list[dict[str, Any]] | None:
        """Return the immutable required denominator, or ``None`` if corrupt.

        A child row is only a materialized intent.  The accepted membership
        and ChangeSet fact pair is the authoritative fan-out/fan-in contract;
        treating a short child list as a smaller collection would convert a
        crash window into silent loss.
        """

        change_set = await tx.fetchone(
            "SELECT change_set_uuid FROM mkb_intake_change_sets "
            "WHERE team_uuid=? AND change_set_uuid=? AND intake_snapshot_uuid=?",
            (team_uuid, change_set_uuid, snapshot_uuid),
        )
        if change_set is None:
            return None
        memberships = await tx.fetchall(
            "SELECT member_ordinal,intake_item_uuid,observed_revision_uuid,decision_kind,required "
            "FROM mkb_intake_snapshot_memberships WHERE team_uuid=? AND intake_snapshot_uuid=? "
            "ORDER BY member_ordinal",
            (team_uuid, snapshot_uuid),
        )
        facts = await tx.fetchall(
            "SELECT fact_ordinal,intake_item_uuid,intake_revision_uuid FROM mkb_intake_change_set_facts "
            "WHERE team_uuid=? AND change_set_uuid=? AND fact_kind='accept_revision' ORDER BY fact_ordinal",
            (team_uuid, change_set_uuid),
        )
        expected: list[dict[str, Any]] = []
        for membership in memberships:
            if int(membership["required"]) != 1:
                continue
            if (
                membership["decision_kind"] != "accepted"
                or not membership.get("intake_item_uuid")
                or not membership.get("observed_revision_uuid")
            ):
                return None
            expected.append(
                {
                    "member_ordinal": int(membership["member_ordinal"]),
                    "intake_item_uuid": str(membership["intake_item_uuid"]),
                    "intake_revision_uuid": str(membership["observed_revision_uuid"]),
                }
            )
        expected_facts = {
            (member["member_ordinal"], member["intake_item_uuid"], member["intake_revision_uuid"])
            for member in expected
        }
        actual_facts = {
            (int(fact["fact_ordinal"]), str(fact["intake_item_uuid"]), str(fact["intake_revision_uuid"]))
            for fact in facts
            if fact.get("intake_item_uuid") and fact.get("intake_revision_uuid")
        }
        if len(actual_facts) != len(facts) or actual_facts != expected_facts:
            return None
        return expected


    async def _release_scatter_children_tx(
        self,
        tx: UnitOfWork,
        *,
        root: dict[str, Any],
        change_set_uuid: str,
    ) -> int:
        """Release review-gated child intents only through the declared join."""

        now = utc_now()
        rows = await tx.fetchall(
            "SELECT * FROM mkb_executions "
            "WHERE team_uuid=? AND parent_execution_uuid=? AND root_execution_uuid=? "
            "AND execution_role='scatter_child' AND status='waiting' "
            "AND waiting_reason='durable_prerequisite' AND waiting_ref=? ORDER BY execution_uuid",
            (root["team_uuid"], root["execution_uuid"], root["execution_uuid"], change_set_uuid),
        )
        released = 0
        for child in rows:
            updated = await tx.execute(
                "UPDATE mkb_executions SET status='ready',waiting_reason=NULL,waiting_ref=NULL,next_wake_at=NULL,"
                "row_revision=row_revision+1,updated_at=? WHERE execution_uuid=? AND status='waiting' "
                "AND waiting_reason='durable_prerequisite' AND waiting_ref=?",
                (now, child["execution_uuid"], change_set_uuid),
            )
            if updated.rowcount != 1:
                continue
            released += 1
            await self._enqueue_tx(
                tx,
                root["team_uuid"],
                "wake_execution",
                {
                    "execution_uuid": child["execution_uuid"],
                    "task_uuid": child["task_uuid"],
                    "generation": child["generation"],
                },
                f"scatter-child-release:{child['execution_uuid']}:{change_set_uuid}",
            )
            await self._record_event_tx(
                tx,
                execution=child,
                event_type="execution.prerequisite_released",
                aggregate="execution",
                summary="Scatter child released after root human-review approval",
                status_before=ExecutionStatus.WAITING.value,
                status_after=ExecutionStatus.READY.value,
                payload={"change_set_uuid": change_set_uuid},
            )
        return released


    async def _scatter_root_terminal_proof_tx(
        self,
        tx: UnitOfWork,
        root: dict[str, Any],
        source_process: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Resolve the typed accept Process used by a zero-member terminal."""

        process_uuid = None if source_process is None else source_process.get("process_uuid")
        if isinstance(process_uuid, str) and process_uuid:
            row = await tx.fetchone(
                "SELECT * FROM mkb_processes WHERE process_uuid=? AND team_uuid=? AND execution_uuid=? "
                "AND status='succeeded' AND step_key='accept_snapshot' AND process_key='intake.accept_snapshot'",
                (process_uuid, root["team_uuid"], root["execution_uuid"]),
            )
            if row is not None and row.get("proof_ref") and row.get("output_manifest_ref"):
                return row
        return await tx.fetchone(
            "SELECT * FROM mkb_processes WHERE team_uuid=? AND execution_uuid=? "
            "AND status='succeeded' AND step_key='accept_snapshot' AND process_key='intake.accept_snapshot' "
            "AND proof_ref IS NOT NULL AND output_manifest_ref IS NOT NULL "
            "ORDER BY completed_at DESC,process_uuid DESC LIMIT 1",
            (root["team_uuid"], root["execution_uuid"]),
        )


    async def _maybe_converge_scatter_root_tx(self, tx: UnitOfWork, root: dict[str, Any]) -> bool:
        """Collect the exact required child set after every leaf transition.

        This method is intentionally also used by recovery.  It never derives
        success from queue emptiness or from however many children happen to
        exist: a missing, duplicated, or misbound child is an integrity
        failure, and active siblings keep a failed child from fail-fast
        terminalization until the collect-all denominator is terminal.
        """

        current = await self._execution(tx, root["execution_uuid"])
        if (
            current.get("execution_role") != "scatter_root"
            or current["status"] != ExecutionStatus.WAITING.value
            or current.get("waiting_reason") != "scatter_children"
        ):
            return False
        task = await tx.fetchone(
            "SELECT intake_snapshot_uuid,change_set_uuid FROM mkb_tasks "
            "WHERE team_uuid=? AND task_uuid=? AND current_root_execution_uuid=?",
            (current["team_uuid"], current["task_uuid"], current["execution_uuid"]),
        )
        if task is None or not task.get("intake_snapshot_uuid") or not task.get("change_set_uuid"):
            await self._fail_execution_integrity_tx(
                tx,
                current,
                "scatter-acceptance-binding-missing",
                "Scatter fan-in has no exact accepted Snapshot and ChangeSet binding",
            )
            return True
        expected = await self._scatter_expected_members_tx(
            tx,
            team_uuid=current["team_uuid"],
            snapshot_uuid=task["intake_snapshot_uuid"],
            change_set_uuid=task["change_set_uuid"],
        )
        if expected is None:
            await self._fail_execution_integrity_tx(
                tx,
                current,
                "scatter-required-set-invalid",
                "Scatter ChangeSet does not match the accepted required membership set",
            )
            return True
        if not expected:
            # Normally handled at join entry; retain this recovery branch for
            # a crash after the wait CAS but before its terminal summary.
            proof = await self._scatter_root_terminal_proof_tx(tx, current, None)
            if proof is None:
                await self._fail_execution_integrity_tx(
                    tx,
                    current,
                    "scatter-zero-proof-missing",
                    "Zero-member Scatter Snapshot has no immutable acceptance proof",
                )
                return True
            await self._terminalize_execution_tx(
                tx,
                current,
                WorkflowTerminalKind.SUCCESS,
                source_process=proof,
                route_digest=stable_digest(
                    {
                        "kind": "scatter-zero-fan-in",
                        "snapshot_uuid": task["intake_snapshot_uuid"],
                        "change_set_uuid": task["change_set_uuid"],
                    }
                ),
                error_code=None,
            )
            return True

        change_set = await tx.fetchone(
            "SELECT change_set_digest FROM mkb_intake_change_sets WHERE team_uuid=? AND change_set_uuid=?",
            (current["team_uuid"], task["change_set_uuid"]),
        )
        if change_set is None:
            await self._fail_execution_integrity_tx(
                tx,
                current,
                "scatter-change-set-missing",
                "Scatter fan-in ChangeSet disappeared",
            )
            return True
        children = await tx.fetchall(
            "SELECT * FROM mkb_executions WHERE team_uuid=? AND parent_execution_uuid=? "
            "AND root_execution_uuid=? ORDER BY execution_uuid",
            (current["team_uuid"], current["execution_uuid"], current["execution_uuid"]),
        )
        expected_by_item = {member["intake_item_uuid"]: member for member in expected}
        children_by_item: dict[str, list[dict[str, Any]]] = {}
        malformed = False
        for child in children:
            item_uuid = child.get("target_uuid")
            if not isinstance(item_uuid, str) or item_uuid not in expected_by_item:
                malformed = True
                continue
            children_by_item.setdefault(item_uuid, []).append(child)
        bound_children: list[dict[str, Any]] = []
        for item_uuid, member in expected_by_item.items():
            rows = children_by_item.get(item_uuid, [])
            if len(rows) != 1:
                malformed = True
                continue
            child = rows[0]
            try:
                binding = json.loads(child.get("payload_extra") or "{}")
            except (TypeError, json.JSONDecodeError):
                binding = None
            if (
                child.get("execution_role") != "scatter_child"
                or child.get("requiredness") != "required"
                or child.get("target_kind") != "intake_item"
                or child.get("intake_snapshot_uuid") != task["intake_snapshot_uuid"]
                or not isinstance(binding, dict)
                or binding.get("change_set_uuid") != task["change_set_uuid"]
                or binding.get("change_set_digest") != change_set["change_set_digest"]
                or binding.get("member_ordinal") != member["member_ordinal"]
                or binding.get("intake_revision_uuid") != member["intake_revision_uuid"]
            ):
                malformed = True
                continue
            bound_children.append(child)
        if malformed or len(bound_children) != len(expected):
            await self._fail_execution_integrity_tx(
                tx,
                current,
                "scatter-child-intent-invalid",
                "Scatter child intents do not exactly cover the accepted required set",
            )
            return True

        nonterminal = [child for child in bound_children if child["status"] not in _TERMINAL_EXECUTION_STATUSES]
        if nonterminal:
            return False
        route_digest = stable_digest(
            {
                "kind": "scatter-fan-in.v1",
                "snapshot_uuid": task["intake_snapshot_uuid"],
                "change_set_uuid": task["change_set_uuid"],
                "children": [
                    {"execution_uuid": child["execution_uuid"], "status": child["status"]}
                    for child in sorted(bound_children, key=lambda row: str(row["execution_uuid"]))
                ],
            }
        )
        failed = [child for child in bound_children if child["status"] == ExecutionStatus.FAILED.value]
        cancelled = [child for child in bound_children if child["status"] == ExecutionStatus.CANCELLED.value]
        if failed or cancelled:
            source = await self._last_terminal_process_tx(tx, (failed or cancelled)[0]["execution_uuid"])
            await self._terminalize_execution_tx(
                tx,
                current,
                WorkflowTerminalKind.FAILURE,
                source_process=source,
                route_digest=route_digest,
                error_code="scatter-required-child-failed" if failed else "scatter-required-child-cancelled",
            )
            return True

        terminal_proofs: list[dict[str, Any]] = []
        for child, member in zip(
            sorted(bound_children, key=lambda row: str(row["target_uuid"])),
            sorted(expected, key=lambda row: str(row["intake_item_uuid"])),
            strict=True,
        ):
            proofs = await tx.fetchall(
                "SELECT proof_uuid,process_uuid FROM mkb_publication_proofs WHERE team_uuid=? "
                "AND intake_item_uuid=? AND intake_revision_uuid=? AND execution_uuid=? ORDER BY proof_uuid",
                (
                    current["team_uuid"],
                    member["intake_item_uuid"],
                    member["intake_revision_uuid"],
                    child["execution_uuid"],
                ),
            )
            if len(proofs) != 1 or not proofs[0].get("process_uuid"):
                await self._fail_execution_integrity_tx(
                    tx,
                    current,
                    "scatter-publication-proof-missing",
                    "A succeeded required Scatter child lacks one exact publication proof",
                )
                return True
            process = await tx.fetchone(
                "SELECT * FROM mkb_processes WHERE process_uuid=? AND team_uuid=? AND execution_uuid=? "
                "AND status='succeeded' AND step_key='validate_publication' "
                "AND process_key='index.validate_publication'",
                (proofs[0]["process_uuid"], current["team_uuid"], child["execution_uuid"]),
            )
            if (
                process is None
                or not process.get("proof_ref")
                or not process.get("output_manifest_ref")
                or child.get("publication_proof_ref") != process["proof_ref"]
            ):
                await self._fail_execution_integrity_tx(
                    tx,
                    current,
                    "scatter-publication-proof-invalid",
                    "A succeeded required Scatter child has no matching terminal publication evidence",
                )
                return True
            terminal_proofs.append(process)
        source = max(terminal_proofs, key=lambda row: (str(row.get("completed_at") or ""), str(row["process_uuid"])))
        await self._terminalize_execution_tx(
            tx,
            current,
            WorkflowTerminalKind.SUCCESS,
            source_process=source,
            route_digest=route_digest,
            error_code=None,
        )
        return True


    async def _last_terminal_process_tx(self, tx: UnitOfWork, execution_uuid: str) -> dict[str, Any] | None:
        return await tx.fetchone(
            "SELECT * FROM mkb_processes WHERE execution_uuid=? AND status IN ('succeeded','failed','cancelled') "
            "ORDER BY completed_at DESC,process_uuid DESC LIMIT 1",
            (execution_uuid,),
        )


    async def _scatter_human_review_evidence_tx(
        self,
        tx: UnitOfWork,
        execution: dict[str, Any],
        source_process: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Build a collection Gate target without pretending it is one Item.

        The single-item helper intentionally rejects multiple memberships.  A
        scatter root has one accepted collection, so its review target is
        instead bound to the Snapshot/ChangeSet and a real member Artifact
        (or the real collection acquisition Artifact for a legal empty set).
        """

        def invalid(message: str) -> None:
            raise MkbError("gate-target-evidence-invalid", message, 409)

        if source_process is None:
            invalid("Scatter human-review Gate has no source Process")
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
            or not accepted.get("input_manifest_ref")
            or not accepted.get("input_manifest_digest")
            or not accepted.get("output_manifest_ref")
            or not accepted.get("output_manifest_digest")
            or not accepted.get("proof_ref")
            or not accepted.get("proof_digest")
        ):
            invalid("Scatter Gate requires a succeeded accept_snapshot Process with immutable evidence")

        task = await tx.fetchone(
            "SELECT intake_snapshot_uuid,change_set_uuid FROM mkb_tasks "
            "WHERE team_uuid=? AND task_uuid=? AND current_root_execution_uuid=?",
            (execution["team_uuid"], execution["task_uuid"], execution["execution_uuid"]),
        )
        if task is None or not task.get("intake_snapshot_uuid") or not task.get("change_set_uuid"):
            invalid("Scatter Gate has no accepted Snapshot/ChangeSet")
        snapshot = await tx.fetchone(
            "SELECT s.intake_source_uuid,s.intake_snapshot_uuid,c.candidate_set_uuid,cs.change_set_uuid,"
            "cs.change_set_digest,source_def.preflight_profile_key "
            "FROM mkb_intake_snapshots AS s "
            "JOIN mkb_intake_change_sets AS cs ON cs.team_uuid=s.team_uuid "
            " AND cs.intake_snapshot_uuid=s.intake_snapshot_uuid "
            "JOIN mkb_intake_sources AS source ON source.team_uuid=s.team_uuid "
            " AND source.intake_source_uuid=s.intake_source_uuid "
            "JOIN mkb_source_kind_definitions AS source_def ON source_def.source_kind=source.source_kind "
            " AND source_def.definition_version=source.source_kind_definition_version "
            "LEFT JOIN mkb_intake_candidate_sets AS c ON c.team_uuid=s.team_uuid "
            " AND c.accepted_snapshot_uuid=s.intake_snapshot_uuid AND c.staging_state='accepted' "
            "WHERE s.team_uuid=? AND s.intake_snapshot_uuid=? AND s.producer_execution_uuid=? "
            " AND s.preflight_outcome_ref=? AND s.preflight_outcome_digest=? AND cs.change_set_uuid=?",
            (
                execution["team_uuid"],
                task["intake_snapshot_uuid"],
                execution["execution_uuid"],
                accepted["input_manifest_ref"],
                accepted["input_manifest_digest"],
                task["change_set_uuid"],
            ),
        )
        if snapshot is None:
            invalid("Scatter Gate Snapshot is not exactly bound to the accepted Process")

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
        if len(preflight_rows) != 1 or not preflight_rows[0].get("proof_ref") or not preflight_rows[0].get("proof_digest"):
            invalid("Scatter accepted Snapshot is not bound to one proved preflight outcome")
        preflight = preflight_rows[0]

        profile_key = snapshot.get("preflight_profile_key")
        if not isinstance(profile_key, str) or not profile_key:
            invalid("Scatter source has no exact preflight profile")
        profiles = await tx.fetchall(
            "SELECT profile_key,definition_version,check_set_digest,definition_digest "
            "FROM mkb_preflight_profile_definitions WHERE profile_key=? ORDER BY definition_version",
            (profile_key,),
        )
        if len(profiles) != 1:
            invalid("Scatter preflight profile is missing or version-ambiguous")
        profile = profiles[0]

        members = await tx.fetchall(
            "SELECT m.member_ordinal,a.intake_artifact_uuid,a.stored_object_uuid,a.artifact_role "
            "FROM mkb_intake_snapshot_memberships AS m "
            "JOIN mkb_intake_revisions AS r ON r.team_uuid=m.team_uuid "
            " AND r.intake_revision_uuid=m.observed_revision_uuid "
            "JOIN mkb_intake_artifacts AS a ON a.team_uuid=r.team_uuid "
            " AND a.owner_revision_uuid=r.intake_revision_uuid AND a.artifact_role='clean_text' "
            "WHERE m.team_uuid=? AND m.intake_snapshot_uuid=? AND m.required=1 "
            "ORDER BY m.member_ordinal",
            (execution["team_uuid"], snapshot["intake_snapshot_uuid"]),
        )
        required = await tx.fetchone(
            "SELECT COUNT(*) AS count FROM mkb_intake_snapshot_memberships "
            "WHERE team_uuid=? AND intake_snapshot_uuid=? AND required=1",
            (execution["team_uuid"], snapshot["intake_snapshot_uuid"]),
        )
        required_count = int(required["count"]) if required is not None else 0
        if len(members) != required_count:
            invalid("Scatter Gate membership does not have one clean Artifact per required member")
        if members:
            artifact = members[0]
            artifact_role = "clean_text"
        else:
            artifact = await tx.fetchone(
                "SELECT intake_artifact_uuid,stored_object_uuid,artifact_role FROM mkb_intake_artifacts "
                "WHERE team_uuid=? AND owner_snapshot_uuid=? AND artifact_role='raw_acquisition' "
                "ORDER BY intake_artifact_uuid",
                (execution["team_uuid"], snapshot["intake_snapshot_uuid"]),
            )
            artifact_role = "raw_acquisition"
            if artifact is None:
                invalid("Empty Scatter Gate has no collection acquisition Artifact")
        artifact_object = await self._gate_evidence_object_tx(
            tx,
            team_uuid=execution["team_uuid"],
            stored_object_uuid=artifact["stored_object_uuid"],
            label="Scatter review Artifact",
        )
        preflight_object = await tx.fetchone(
            "SELECT stored_object_uuid,content_digest,size_bytes FROM mkb_stored_objects "
            "WHERE team_uuid=? AND content_digest=? AND tombstoned_at IS NULL",
            (execution["team_uuid"], preflight["output_manifest_digest"]),
        )
        if preflight_object is None:
            invalid("Scatter preflight output has no live catalogued object")

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
                "intake_source_uuid": snapshot["intake_source_uuid"],
                "candidate_set_uuid": snapshot["candidate_set_uuid"],
                "intake_snapshot_uuid": snapshot["intake_snapshot_uuid"],
                "change_set_uuid": snapshot["change_set_uuid"],
                "change_set_digest": snapshot["change_set_digest"],
                "required_member_count": required_count,
            },
            "clean_artifact": {
                "intake_artifact_uuid": artifact["intake_artifact_uuid"],
                "content_digest": artifact_object["content_digest"],
                "artifact_role": artifact_role,
            },
            "evidence_objects": (artifact_object, preflight_object),
        }


    async def _notify_scatter_parent_terminal_tx(self, tx: UnitOfWork, execution: dict[str, Any]) -> None:
        """Re-evaluate a parent from durable child terminal truth."""

        parent_uuid = execution.get("parent_execution_uuid")
        if not isinstance(parent_uuid, str) or not parent_uuid:
            return
        parent = await self._execution(tx, parent_uuid)
        if parent["status"] == ExecutionStatus.CANCELLING.value:
            await self._converge_cancellation_tx(tx, parent)
        elif parent.get("execution_role") == "scatter_root":
            await self._maybe_converge_scatter_root_tx(tx, parent)
