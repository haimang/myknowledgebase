"""lifecycle_publish"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.contracts.common.errors import ConflictError, MkbError, NotFoundError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.persistence.ports import UnitOfWork
from src.services.intake_lifecycle.models import (
    IntakePublicationCommand,
    PublicationTransitionResult,
)


class LifecyclePublishMixin:
    """lifecycle_publish"""

    async def publish_revision(self, command: IntakePublicationCommand) -> PublicationTransitionResult:
        """Publish a Revision only after S09's exact proof/pointer fence passes."""

        async with self._persistence.transaction() as tx:
            return await self.publish_revision_tx(tx, command)


    async def publish_revision_tx(
        self, tx: UnitOfWork, command: IntakePublicationCommand
    ) -> PublicationTransitionResult:
        """Advance ``serving_revision_uuid`` in a caller-owned Process UoW.

        The ordering is deliberate: S09 first writes and activates its exact
        index proof/pointer in this same transaction, then S04 verifies those
        facts and performs the Item CAS.  Any later failure rolls all of that
        back, so neither an indexed vector nor a publication proof can become
        a false serving assertion on its own.
        """

        self._validate_publication_command(command)
        transition_fence = stable_digest(
            {
                "schema_version": "mkb.intake-publication-command.v1",
                "team_uuid": command.team_uuid,
                "intake_item_uuid": command.intake_item_uuid,
                "intake_revision_uuid": command.intake_revision_uuid,
                "publication_proof_uuid": command.publication_proof_uuid,
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
        if previous is not None:
            if item["serving_revision_uuid"] != command.intake_revision_uuid:
                raise ConflictError(
                    "intake-publication-replay-conflict",
                    "Published serving pointer no longer matches the replayed proof",
                )
            return self._publication_result(command, item, item["serving_revision_uuid"], transition_fence, False)
        if command.expected_item_revision is not None and item["row_revision"] != command.expected_item_revision:
            raise ConflictError(
                "intake-item-revision-conflict",
                "Intake item revision is stale",
                {"current_revision": item["row_revision"]},
            )
        if item["lifecycle_state"] != "active":
            raise ConflictError("PUBLICATION_SERVING_FENCE", "Intake item is not active for publication")
        if item["latest_revision_uuid"] != command.intake_revision_uuid:
            raise ConflictError(
                "PUBLICATION_SERVING_FENCE",
                "Publication revision is no longer the Intake item's latest revision",
            )
        definition = await self._publication_definition_tx(tx)
        proof = await tx.fetchone(
            "SELECT * FROM mkb_publication_proofs WHERE proof_uuid=? AND team_uuid=? "
            "AND intake_item_uuid=? AND intake_revision_uuid=? AND namespace_uuid=? AND index_generation=?",
            (
                command.publication_proof_uuid,
                command.team_uuid,
                command.intake_item_uuid,
                command.intake_revision_uuid,
                command.namespace_uuid,
                command.index_generation,
            ),
        )
        if proof is None:
            raise MkbError("PUBLICATION_PROOF_INVALID", "Publication proof does not match the serving target", 409)
        if (
            proof["execution_uuid"] != command.execution_uuid
            or proof["process_uuid"] != command.process_uuid
            or proof["expected_count"] != proof["actual_count"]
            or proof["expected_count"] != proof["matched_count"]
        ):
            raise MkbError("PUBLICATION_PROOF_INVALID", "Publication proof is incomplete or causally mismatched", 409)
        pointer = await tx.fetchone(
            "SELECT active_index_generation,lifecycle_state,last_proof_uuid,generation_artifact_uuid "
            "FROM mkb_index_active_pointers WHERE team_uuid=? AND intake_item_uuid=? AND namespace_uuid=?",
            (command.team_uuid, command.intake_item_uuid, command.namespace_uuid),
        )
        if (
            pointer is None
            or pointer["lifecycle_state"] != "active"
            or pointer["active_index_generation"] != command.index_generation
            or pointer["last_proof_uuid"] != command.publication_proof_uuid
            or pointer["generation_artifact_uuid"] != proof["generation_artifact_uuid"]
        ):
            raise MkbError("PUBLICATION_POINTER_FENCE", "Active index pointer does not match publication proof", 409)
        now = utc_now()
        changed = await tx.execute(
            "UPDATE mkb_intake_items SET serving_revision_uuid=?,row_revision=row_revision+1,updated_at=? "
            "WHERE team_uuid=? AND intake_item_uuid=? AND lifecycle_state='active' AND row_revision=? "
            "AND latest_revision_uuid=?",
            (
                command.intake_revision_uuid,
                now,
                command.team_uuid,
                command.intake_item_uuid,
                item["row_revision"],
                command.intake_revision_uuid,
            ),
        )
        if changed.rowcount != 1:
            raise ConflictError("PUBLICATION_SERVING_FENCE", "Serving revision changed concurrently")
        await tx.execute(
            "INSERT INTO mkb_intake_item_transitions "
            "(transition_uuid,team_uuid,intake_item_uuid,action_key,action_version,before_lifecycle,after_lifecycle,"
            "before_latest_revision_uuid,after_latest_revision_uuid,before_serving_revision_uuid,after_serving_revision_uuid,"
            "item_revision_before,item_revision_after,causation_task_uuid,causation_execution_uuid,causation_process_uuid,"
            "proof_ref,proof_digest,policy_ref,policy_version,transition_fence,occurred_at,payload_extra) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                uuid7(),
                command.team_uuid,
                command.intake_item_uuid,
                "publish_revision",
                definition["definition_version"],
                "active",
                "active",
                item["latest_revision_uuid"],
                item["latest_revision_uuid"],
                item["serving_revision_uuid"],
                command.intake_revision_uuid,
                item["row_revision"],
                item["row_revision"] + 1,
                command.task_uuid,
                command.execution_uuid,
                command.process_uuid,
                command.proof_ref,
                command.proof_digest,
                None,
                None,
                transition_fence,
                now,
                "{}",
            ),
        )
        await self._events.write(
            tx,
            team_uuid=command.team_uuid,
            trace_uuid=command.trace_uuid,
            event_type="intake.item_transitioned",
            aggregate="intake",
            summary="Intake revision publication accepted",
            actor_kind=command.actor_kind,
            task_uuid=command.task_uuid,
            execution_uuid=command.execution_uuid,
            process_uuid=command.process_uuid,
            payload={
                "intake_item_uuid": command.intake_item_uuid,
                "intake_revision_uuid": command.intake_revision_uuid,
                "action": "publish_revision",
                "publication_proof_uuid": command.publication_proof_uuid,
                "index_generation": command.index_generation,
                "transition_fence": transition_fence,
                "proof_digest": command.proof_digest,
            },
        )
        assert command.execution_uuid is not None
        await self._enqueue_execution_wake_tx(
            tx,
            team_uuid=command.team_uuid,
            task_uuid=command.task_uuid,
            execution_uuid=command.execution_uuid,
            transition_fence=transition_fence,
            dedupe_prefix="intake-publication-wake",
        )
        updated = await tx.fetchone(
            "SELECT * FROM mkb_intake_items WHERE team_uuid=? AND intake_item_uuid=?",
            (command.team_uuid, command.intake_item_uuid),
        )
        assert updated is not None
        return self._publication_result(
            command,
            updated,
            item["serving_revision_uuid"],
            transition_fence,
            True,
        )


    @staticmethod
    def _validate_publication_command(command: IntakePublicationCommand) -> None:
        required = (
            command.team_uuid,
            command.intake_item_uuid,
            command.intake_revision_uuid,
            command.publication_proof_uuid,
            command.namespace_uuid,
            command.trace_uuid,
            command.idempotency_key,
            command.task_uuid,
            command.execution_uuid,
            command.process_uuid,
            command.proof_ref,
            command.proof_digest,
        )
        if not all(isinstance(value, str) and value for value in required):
            raise MkbError("INTAKE_PUBLICATION_COMMAND_INVALID", "Publication command identity and proof are required", 422)
        if len(command.idempotency_key) > 256 or command.index_generation < 0:
            raise MkbError("INTAKE_PUBLICATION_COMMAND_INVALID", "Publication command fence is invalid", 422)
        if command.expected_item_revision is not None and command.expected_item_revision < 0:
            raise MkbError("INTAKE_PUBLICATION_COMMAND_INVALID", "Expected Intake item revision is invalid", 422)
        if len(command.proof_digest) != 64 or any(character not in "0123456789abcdef" for character in command.proof_digest):
            raise MkbError("INTAKE_PUBLICATION_COMMAND_INVALID", "Publication process proof digest is invalid", 422)


    async def _publication_definition_tx(self, tx: UnitOfWork) -> dict[str, Any]:
        definition = await tx.fetchone(
            "SELECT definition_version,allowed_from_mask,core_effect_mask FROM mkb_intake_action_definitions "
            "WHERE action_key='publish_revision' AND definition_version='v1'"
        )
        if definition is None:
            raise MkbError("INTAKE_ACTION_UNREGISTERED", "Intake publication action is not registered", 503)
        if "active" not in set(definition["allowed_from_mask"].split("|")):
            raise MkbError("INTAKE_ACTION_DEFINITION_INVALID", "Intake publication action is invalid", 503)
        if "advance_serving" not in set(definition["core_effect_mask"].split("|")):
            raise MkbError("INTAKE_ACTION_DEFINITION_INVALID", "Intake publication action effect is invalid", 503)
        return definition


    @staticmethod
    def _publication_result(
        command: IntakePublicationCommand,
        item: Mapping[str, Any],
        before_serving_revision_uuid: str | None,
        transition_fence: str,
        applied: bool,
    ) -> PublicationTransitionResult:
        return PublicationTransitionResult(
            team_uuid=command.team_uuid,
            intake_item_uuid=command.intake_item_uuid,
            intake_revision_uuid=command.intake_revision_uuid,
            publication_proof_uuid=command.publication_proof_uuid,
            before_serving_revision_uuid=before_serving_revision_uuid,
            serving_revision_uuid=item["serving_revision_uuid"],
            item_revision=item["row_revision"],
            transition_fence=transition_fence,
            applied=applied,
        )
