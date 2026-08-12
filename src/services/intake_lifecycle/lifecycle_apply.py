"""lifecycle_apply"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from src.contracts.common.errors import ConflictError, MkbError, NotFoundError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.persistence.ports import PersistencePort, UnitOfWork
from src.services.events import DomainEventWriter
from src.services.intake_lifecycle.models import (
    IntakeLifecycleCommand,
    LifecycleAction,
    LifecycleTransitionResult,
)


class LifecycleApplyMixin:
    """lifecycle_apply"""

    _ACTION_EFFECT = {"deactivate": "deactivate", "reactivate": "reactivate", "delete": "delete"}

    def __init__(self, persistence: PersistencePort, events: DomainEventWriter) -> None:
        self._persistence = persistence
        self._events = events


    async def apply(self, command: IntakeLifecycleCommand) -> LifecycleTransitionResult:
        """Atomically transition a canonical Item, append its ledger, and wake.

        Each lifecycle action leaves both S04's serving pointer and the S09
        index projection withdrawn in the same relational transaction.
        Reactivation changes only canonical lifecycle truth: a fresh
        proof/publish path is required before the Item may serve again.  The
        projection withdrawal is defence in depth; S10's Item/serving double
        fence remains the authoritative protection against stale ANN material.
        """

        async with self._persistence.transaction() as tx:
            return await self.apply_tx(tx, command)


    async def apply_tx(self, tx: UnitOfWork, command: IntakeLifecycleCommand) -> LifecycleTransitionResult:
        """Apply a lifecycle command inside a caller-owned authoritative UoW.

        Pipeline outcome callbacks use this form so the Process outcome fence,
        Item CAS, transition ledger, event, and wake-up intent either commit
        together or all roll back.  It deliberately opens no nested
        transaction and contains no storage or runtime adapter dependency.
        """

        self._validate_command(command)
        transition_fence = stable_digest(
            {
                "schema_version": "mkb.intake-lifecycle-command.v1",
                "team_uuid": command.team_uuid,
                "intake_item_uuid": command.intake_item_uuid,
                "action": command.action,
                "idempotency_key": command.idempotency_key,
            }
        )
        item = await tx.fetchone(
            "SELECT * FROM mkb_intake_items WHERE team_uuid=? AND intake_item_uuid=?",
            (command.team_uuid, command.intake_item_uuid),
        )
        if item is None:
            raise NotFoundError("intake-item-not-found", "Intake item was not found")
        previous = await tx.fetchone(
            "SELECT transition_uuid FROM mkb_intake_item_transitions "
            "WHERE team_uuid=? AND intake_item_uuid=? AND transition_fence=?",
            (command.team_uuid, command.intake_item_uuid, transition_fence),
        )
        cleanup = await self._existing_cleanup_tx(tx, command.team_uuid, command.intake_item_uuid)
        if previous is not None:
            return self._result(
                command,
                item,
                before_lifecycle=item["lifecycle_state"],
                transition_fence=transition_fence,
                applied=False,
                cleanup_intent_uuid=cleanup,
            )
        if command.expected_item_revision is not None and item["row_revision"] != command.expected_item_revision:
            raise ConflictError(
                "intake-item-revision-conflict",
                "Intake item revision is stale",
                {"current_revision": item["row_revision"]},
            )
        target = self._target_state(command.action, item["lifecycle_state"])
        if target is None:
            # A separately admitted command may arrive after an equivalent
            # earlier Task.  It is an honest no-op, not a fabricated second
            # lifecycle transition.
            return self._result(
                command,
                item,
                before_lifecycle=item["lifecycle_state"],
                transition_fence=transition_fence,
                applied=False,
                cleanup_intent_uuid=cleanup,
            )
        definition = await self._action_definition_tx(tx, command.action, item["lifecycle_state"])
        now = utc_now()
        changed = await tx.execute(
            "UPDATE mkb_intake_items SET lifecycle_state=?,serving_revision_uuid=NULL,row_revision=row_revision+1,"
            "deactivated_at=?,deleted_at=?,updated_at=? "
            "WHERE team_uuid=? AND intake_item_uuid=? AND row_revision=? AND lifecycle_state=?",
            (
                target,
                None if target == "active" else now if target == "deactivated" else item["deactivated_at"],
                now if target == "deleted" else item["deleted_at"],
                now,
                command.team_uuid,
                command.intake_item_uuid,
                item["row_revision"],
                item["lifecycle_state"],
            ),
        )
        if changed.rowcount != 1:
            raise ConflictError("intake-item-revision-conflict", "Intake item changed concurrently")
        await tx.execute(
            "UPDATE mkb_index_active_pointers SET lifecycle_state='withdrawn',candidate_index_generation=NULL,"
            "pointer_row_revision=pointer_row_revision+1,updated_at=? "
            "WHERE team_uuid=? AND intake_item_uuid=? AND lifecycle_state<>'withdrawn'",
            (now, command.team_uuid, command.intake_item_uuid),
        )
        await tx.execute(
            "UPDATE mkb_vector_records SET publication_state='withdrawn',updated_at=? "
            "WHERE team_uuid=? AND intake_item_uuid=? AND deleted_at IS NULL AND publication_state='indexed'",
            (now, command.team_uuid, command.intake_item_uuid),
        )
        cleanup_intent_uuid = cleanup
        if command.action == "delete":
            cleanup_intent_uuid = await self._ensure_delete_cleanup_tx(
                tx,
                team_uuid=command.team_uuid,
                intake_item_uuid=command.intake_item_uuid,
                trace_uuid=command.trace_uuid,
            )
        await tx.execute(
            "INSERT INTO mkb_intake_item_transitions "
            "(transition_uuid,team_uuid,intake_item_uuid,action_key,action_version,before_lifecycle,after_lifecycle,"
            "before_latest_revision_uuid,after_latest_revision_uuid,before_serving_revision_uuid,after_serving_revision_uuid,"
            "item_revision_before,item_revision_after,causation_task_uuid,causation_execution_uuid,causation_process_uuid,"
            "proof_ref,proof_digest,policy_ref,policy_version,transition_fence,occurred_at,payload_extra) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'{}')",
            (
                uuid7(),
                command.team_uuid,
                command.intake_item_uuid,
                command.action,
                definition["definition_version"],
                item["lifecycle_state"],
                target,
                item["latest_revision_uuid"],
                item["latest_revision_uuid"],
                item["serving_revision_uuid"],
                None,
                item["row_revision"],
                item["row_revision"] + 1,
                command.task_uuid,
                command.execution_uuid,
                command.process_uuid,
                command.proof_ref,
                command.proof_digest,
                "mkb.retention.intake-delete" if command.action == "delete" else None,
                "v1" if command.action == "delete" else None,
                transition_fence,
                now,
            ),
        )
        await self._events.write(
            tx,
            team_uuid=command.team_uuid,
            trace_uuid=command.trace_uuid,
            event_type="intake.item_transitioned",
            aggregate="intake",
            summary=f"Intake item {command.action} accepted",
            actor_kind=command.actor_kind,
            task_uuid=command.task_uuid,
            execution_uuid=command.execution_uuid,
            process_uuid=command.process_uuid,
            payload={
                "intake_item_uuid": command.intake_item_uuid,
                "action": command.action,
                "before_lifecycle": item["lifecycle_state"],
                "after_lifecycle": target,
                "transition_fence": transition_fence,
                "cleanup_intent_uuid": cleanup_intent_uuid,
                "proof_digest": command.proof_digest,
            },
        )
        if command.execution_uuid is not None:
            await self._enqueue_wake_tx(tx, command, transition_fence)
        updated = await tx.fetchone(
            "SELECT * FROM mkb_intake_items WHERE team_uuid=? AND intake_item_uuid=?",
            (command.team_uuid, command.intake_item_uuid),
        )
        assert updated is not None
        return self._result(
            command,
            updated,
            before_lifecycle=item["lifecycle_state"],
            transition_fence=transition_fence,
            applied=True,
            cleanup_intent_uuid=cleanup_intent_uuid,
        )


    @staticmethod
    def _validate_command(command: IntakeLifecycleCommand) -> None:
        if command.action not in {"deactivate", "reactivate", "delete"}:
            raise MkbError("INTAKE_LIFECYCLE_ACTION_INVALID", "Lifecycle action is invalid", 422)
        if not command.team_uuid or not command.intake_item_uuid or not command.trace_uuid:
            raise MkbError("INTAKE_LIFECYCLE_COMMAND_INVALID", "Lifecycle command identity is required", 422)
        if not command.idempotency_key or len(command.idempotency_key) > 256:
            raise MkbError("INTAKE_LIFECYCLE_COMMAND_INVALID", "Lifecycle idempotency key is invalid", 422)
        if command.expected_item_revision is not None and command.expected_item_revision < 0:
            raise MkbError("INTAKE_LIFECYCLE_COMMAND_INVALID", "Expected Intake item revision is invalid", 422)


    @staticmethod
    def _target_state(action: LifecycleAction, current: str) -> str | None:
        if action == "deactivate":
            if current == "active":
                return "deactivated"
            if current == "deactivated":
                return None
            raise ConflictError("intake-item-deleted", "Deleted Intake items cannot be deactivated")
        if action == "reactivate":
            if current == "deactivated":
                return "active"
            if current == "active":
                return None
            raise ConflictError("intake-item-deleted", "Deleted Intake items cannot be reactivated")
        if current in {"active", "deactivated"}:
            return "deleted"
        return None


    async def _action_definition_tx(self, tx: UnitOfWork, action: LifecycleAction, current: str) -> dict[str, Any]:
        definition = await tx.fetchone(
            "SELECT definition_version,allowed_from_mask,core_effect_mask FROM mkb_intake_action_definitions "
            "WHERE action_key=? AND definition_version='v1'",
            (action,),
        )
        if definition is None:
            raise MkbError("INTAKE_ACTION_UNREGISTERED", "Intake lifecycle action is not registered", 503)
        allowed = set(definition["allowed_from_mask"].split("|"))
        if current not in allowed:
            raise ConflictError("intake-lifecycle-transition-invalid", "Intake lifecycle transition is invalid")
        if self._ACTION_EFFECT[action] not in set(definition["core_effect_mask"].split("|")):
            raise MkbError("INTAKE_ACTION_DEFINITION_INVALID", "Intake lifecycle action effect is invalid", 503)
        return definition


    async def _existing_cleanup_tx(self, tx: UnitOfWork, team_uuid: str, intake_item_uuid: str) -> str | None:
        row = await tx.fetchone(
            "SELECT intent_uuid FROM mkb_intake_cleanup_intents "
            "WHERE team_uuid=? AND target_kind='intake_item' AND target_ref=? AND status='open' "
            "ORDER BY requested_at DESC,intent_uuid DESC LIMIT 1",
            (team_uuid, f"intake_item:{intake_item_uuid}"),
        )
        return None if row is None else row["intent_uuid"]


    async def _ensure_delete_cleanup_tx(
        self,
        tx: UnitOfWork,
        *,
        team_uuid: str,
        intake_item_uuid: str,
        trace_uuid: str,
    ) -> str:
        existing = await self._existing_cleanup_tx(tx, team_uuid, intake_item_uuid)
        if existing is not None:
            return existing
        intent_uuid = uuid7()
        now = utc_now()
        target_ref = f"intake_item:{intake_item_uuid}"
        required_substrates = ("derived_generation", "intake_artifact", "vector_projection")
        await tx.execute(
            "INSERT INTO mkb_intake_cleanup_intents "
            "(intent_uuid,team_uuid,policy_ref,target_kind,target_ref,required_substrate_set_digest,hold_refs_json,"
            "reference_snapshot_ref,status,requested_trace_uuid,requested_at,payload_extra) "
            "VALUES (?,?,?,'intake_item',?,?, '[]',NULL,'open',?,?, '{}')",
            (
                intent_uuid,
                team_uuid,
                "mkb.retention.intake-delete.v1",
                target_ref,
                stable_digest({"target_ref": target_ref, "required_substrates": required_substrates}),
                trace_uuid,
                now,
            ),
        )
        return intent_uuid


    async def _enqueue_wake_tx(self, tx: UnitOfWork, command: IntakeLifecycleCommand, transition_fence: str) -> None:
        assert command.execution_uuid is not None
        await self._enqueue_execution_wake_tx(
            tx,
            team_uuid=command.team_uuid,
            task_uuid=command.task_uuid,
            execution_uuid=command.execution_uuid,
            transition_fence=transition_fence,
            dedupe_prefix="intake-lifecycle-wake",
        )


    async def _enqueue_execution_wake_tx(
        self,
        tx: UnitOfWork,
        *,
        team_uuid: str,
        task_uuid: str | None,
        execution_uuid: str,
        transition_fence: str,
        dedupe_prefix: str,
    ) -> None:
        payload: dict[str, Any] = {"execution_uuid": execution_uuid}
        if task_uuid is not None:
            payload["task_uuid"] = task_uuid
        now = utc_now()
        await tx.execute(
            "INSERT OR IGNORE INTO mkb_outbox "
            "(outbox_id,team_uuid,kind,payload_json,payload_digest,dedupe_key,status,available_at,created_at,updated_at,payload_extra) "
            "VALUES (?,?,'wake_execution',?,?,?,?,?,?,?,'{}')",
            (
                uuid7(),
                team_uuid,
                json.dumps(payload, sort_keys=True, separators=(",", ":")),
                stable_digest(payload),
                f"{dedupe_prefix}:{execution_uuid}:{transition_fence}",
                "pending",
                now,
                now,
                now,
            ),
        )


    @staticmethod
    def _result(
        command: IntakeLifecycleCommand,
        item: Mapping[str, Any],
        *,
        before_lifecycle: str,
        transition_fence: str,
        applied: bool,
        cleanup_intent_uuid: str | None,
    ) -> LifecycleTransitionResult:
        return LifecycleTransitionResult(
            team_uuid=command.team_uuid,
            intake_item_uuid=command.intake_item_uuid,
            action=command.action,
            before_lifecycle=before_lifecycle,
            lifecycle_state=item["lifecycle_state"],
            item_revision=item["row_revision"],
            serving_revision_cleared=item["serving_revision_uuid"] is None,
            transition_fence=transition_fence,
            applied=applied,
            cleanup_intent_uuid=cleanup_intent_uuid,
        )
