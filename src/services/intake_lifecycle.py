"""S04 lifecycle mutations and frozen target resolution.

The public Task aggregate owns admission, Audit, and the six-state Task
projection.  This module owns neither of those things.  Instead it gives a
workflow handler the two S04 operations it needs once a Task has already been
accepted:

* resolve an immutable IntakeItem/Revision target for rebuild, metadata, or
  index work; and
* apply the logical-first ``deactivate`` / ``delete`` state transition in one
  transaction with its transition ledger, event, and durable cleanup intent.

Keeping this boundary here prevents a Task command from directly mutating an
IntakeItem in the HTTP layer, and prevents lifecycle state from being inferred
from a vector row or from a parent Task terminal state.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from src.contracts.api.models import (
    IndexRebuildPayload,
    IntakeLifecyclePayload,
    IntakeRebuildPayload,
    IntakeUpdateMetadataPayload,
)
from src.contracts.common.errors import ConflictError, MkbError, NotFoundError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.persistence.ports import PersistencePort, UnitOfWork
from src.services.events import DomainEventWriter

LifecycleAction = Literal["deactivate", "delete"]


@dataclass(frozen=True, slots=True)
class IntakeLifecycleCommand:
    """One idempotent, workflow-owned logical lifecycle command.

    ``idempotency_key`` is deliberately caller-independent: a Process handler
    should derive it from its immutable command/fence, while an operator
    command may use its persisted request fingerprint.  Retrying the same
    command therefore cannot append a second transition ledger row.
    """

    team_uuid: str
    intake_item_uuid: str
    action: LifecycleAction
    trace_uuid: str
    idempotency_key: str
    expected_item_revision: int | None = None
    task_uuid: str | None = None
    execution_uuid: str | None = None
    process_uuid: str | None = None
    actor_kind: Literal["system", "worker", "upstream", "operator"] = "worker"


@dataclass(frozen=True, slots=True)
class LifecycleTransitionResult:
    """Safe, compact result of an S04 state command."""

    team_uuid: str
    intake_item_uuid: str
    action: LifecycleAction
    before_lifecycle: str
    lifecycle_state: str
    item_revision: int
    serving_revision_cleared: bool
    transition_fence: str
    applied: bool
    cleanup_intent_uuid: str | None = None


@dataclass(frozen=True, slots=True)
class FrozenIntakeTarget:
    """Exact non-secret Intake coordinates to embed in a new Execution input."""

    team_uuid: str
    intake_item_uuid: str
    intake_source_uuid: str
    lifecycle_state: str
    item_revision: int
    intake_revision_uuid: str
    revision_fingerprint: str
    source_snapshot_uuid: str
    source_kind: str
    source_kind_definition_digest: str
    source_descriptor_ref: str
    source_descriptor_digest: str
    clean_artifact_uuid: str | None
    clean_artifact_ref: str | None
    clean_artifact_digest: str | None
    clean_artifact_size: int | None

    def as_manifest(self) -> dict[str, Any]:
        """Return the only target representation suitable for L4 input bytes.

        In particular, connector secrets and physical object paths never cross
        this boundary.  Rebuild workers receive an immutable logical handle
        plus digest/size evidence only.
        """

        return {
            "schema_version": "mkb.frozen-intake-target.v1",
            "team_uuid": self.team_uuid,
            "intake_item_uuid": self.intake_item_uuid,
            "intake_source_uuid": self.intake_source_uuid,
            "lifecycle_state": self.lifecycle_state,
            "item_revision": self.item_revision,
            "intake_revision_uuid": self.intake_revision_uuid,
            "revision_fingerprint": self.revision_fingerprint,
            "source_snapshot_uuid": self.source_snapshot_uuid,
            "source_kind": self.source_kind,
            "source_kind_definition_digest": self.source_kind_definition_digest,
            "source_descriptor_ref": self.source_descriptor_ref,
            "source_descriptor_digest": self.source_descriptor_digest,
            "clean_artifact": (
                None
                if self.clean_artifact_uuid is None
                else {
                    "intake_artifact_uuid": self.clean_artifact_uuid,
                    "logical_handle": self.clean_artifact_ref,
                    "content_digest": self.clean_artifact_digest,
                    "size_bytes": self.clean_artifact_size,
                }
            ),
        }


@dataclass(frozen=True, slots=True)
class FrozenMetadataValue:
    """A registered semantic value, validated but not yet persisted."""

    semantic_key: str
    definition_version: str
    definition_digest: str
    value_kind: str
    value: bool | int | float | str
    value_digest: str

    def as_manifest(self) -> dict[str, Any]:
        return {
            "semantic_key": self.semantic_key,
            "definition_version": self.definition_version,
            "definition_digest": self.definition_digest,
            "value_kind": self.value_kind,
            "value": self.value,
            "value_digest": self.value_digest,
        }


@dataclass(frozen=True, slots=True)
class FrozenMetadataUpdate:
    target: FrozenIntakeTarget
    semantics: tuple[FrozenMetadataValue, ...]

    def as_manifest(self) -> dict[str, Any]:
        return {
            "schema_version": "mkb.frozen-metadata-update.v1",
            "target": self.target.as_manifest(),
            "semantics": [value.as_manifest() for value in self.semantics],
        }


@dataclass(frozen=True, slots=True)
class FrozenIndexRebuildScope:
    """Controlled, tenant-fenced index-rebuild scope, never a SQL selector."""

    team_uuid: str
    scope: Literal["team", "intake_item"]
    targets: tuple[tuple[str, str], ...]
    target_set_digest: str

    def as_manifest(self) -> dict[str, Any]:
        return {
            "schema_version": "mkb.frozen-index-rebuild-scope.v1",
            "team_uuid": self.team_uuid,
            "scope": self.scope,
            "targets": [
                {"intake_item_uuid": item_uuid, "intake_revision_uuid": revision_uuid}
                for item_uuid, revision_uuid in self.targets
            ],
            "target_set_digest": self.target_set_digest,
        }


class IntakeTargetResolver:
    """Resolve Task intent inputs to exact Intake facts before materialization.

    The resolver is intentionally read-only.  It does not create a Task,
    Revision, vector, or lifecycle transition; callers promote its immutable
    manifest into the Task's execution input and let the bound workflow own
    subsequent work.
    """

    def __init__(self, persistence: PersistencePort) -> None:
        self._persistence = persistence

    async def resolve_rebuild(self, team_uuid: str, payload: IntakeRebuildPayload) -> FrozenIntakeTarget:
        async with self._persistence.transaction() as tx:
            return await self._target_tx(
                tx,
                team_uuid=team_uuid,
                intake_item_uuid=payload.intake_item_uuid,
                expected_revision_uuid=payload.expected_intake_revision_uuid,
                require_clean_artifact=True,
            )

    async def resolve_metadata_update(
        self, team_uuid: str, payload: IntakeUpdateMetadataPayload
    ) -> FrozenMetadataUpdate:
        async with self._persistence.transaction() as tx:
            target = await self._target_tx(
                tx,
                team_uuid=team_uuid,
                intake_item_uuid=payload.intake_item_uuid,
                expected_revision_uuid=payload.expected_intake_revision_uuid,
                require_clean_artifact=False,
            )
            semantics = await self._metadata_values_tx(tx, payload.semantics)
        return FrozenMetadataUpdate(target=target, semantics=semantics)

    async def resolve_lifecycle_target(self, team_uuid: str, payload: IntakeLifecyclePayload) -> FrozenIntakeTarget:
        """Freeze the current CAS coordinate for a lifecycle Task.

        The public lifecycle payload intentionally has no mutable pointer or
        revision field.  This read turns it into a workflow-only target with
        the exact Item revision that the later S04 transition must compare.
        """

        async with self._persistence.transaction() as tx:
            return await self._target_tx(
                tx,
                team_uuid=team_uuid,
                intake_item_uuid=payload.intake_item_uuid,
                expected_revision_uuid=None,
                require_clean_artifact=False,
            )

    async def resolve_index_rebuild(self, team_uuid: str, payload: IndexRebuildPayload) -> FrozenIndexRebuildScope:
        """Freeze only active, revision-bearing targets for a rebuild.

        A deactivated Item is intentionally excluded: reindexing it must not
        become an implicit reactivation or a route around the lifecycle fence.
        An empty team scope is valid and deterministically represents a no-op
        rebuild rather than an arbitrary unbounded query expression.
        """

        async with self._persistence.transaction() as tx:
            team = await tx.fetchone("SELECT status FROM mkb_teams WHERE team_uuid=?", (team_uuid,))
            if team is None:
                raise NotFoundError("team-not-registered", "Team is not registered")
            if team["status"] != "active":
                raise ConflictError("team-not-active", "Team is not active")
            if payload.scope == "intake_item":
                assert payload.intake_item_uuid is not None
                target = await self._target_tx(
                    tx,
                    team_uuid=team_uuid,
                    intake_item_uuid=payload.intake_item_uuid,
                    expected_revision_uuid=None,
                    require_clean_artifact=False,
                )
                if target.lifecycle_state != "active":
                    raise ConflictError(
                        "index-rebuild-item-not-active",
                        "Index rebuild cannot make an inactive Intake item servable",
                    )
                targets = ((target.intake_item_uuid, target.intake_revision_uuid),)
            else:
                rows = await tx.fetchall(
                    "SELECT intake_item_uuid,latest_revision_uuid FROM mkb_intake_items "
                    "WHERE team_uuid=? AND lifecycle_state='active' AND latest_revision_uuid IS NOT NULL "
                    "ORDER BY intake_item_uuid",
                    (team_uuid,),
                )
                targets = tuple((row["intake_item_uuid"], row["latest_revision_uuid"]) for row in rows)
        return FrozenIndexRebuildScope(
            team_uuid=team_uuid,
            scope=payload.scope,
            targets=targets,
            target_set_digest=stable_digest(
                {
                    "schema_version": "mkb.index-rebuild-target-set.v1",
                    "team_uuid": team_uuid,
                    "scope": payload.scope,
                    "targets": targets,
                }
            ),
        )

    async def _target_tx(
        self,
        tx: UnitOfWork,
        *,
        team_uuid: str,
        intake_item_uuid: str,
        expected_revision_uuid: str | None,
        require_clean_artifact: bool,
    ) -> FrozenIntakeTarget:
        item = await tx.fetchone(
            "SELECT * FROM mkb_intake_items WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, intake_item_uuid),
        )
        if item is None:
            # The team predicate is deliberately part of every lookup.  A
            # caller scoped to one team receives the same result for an absent
            # item and another team's Item.
            raise NotFoundError("intake-item-not-found", "Intake item was not found")
        if item["lifecycle_state"] == "deleted":
            raise ConflictError("intake-item-deleted", "Deleted Intake items cannot be rebuilt or updated")
        revision_uuid = expected_revision_uuid or item["latest_revision_uuid"]
        if revision_uuid is None:
            raise ConflictError("intake-revision-unavailable", "Intake item has no accepted revision")
        revision = await tx.fetchone(
            "SELECT * FROM mkb_intake_revisions WHERE team_uuid=? AND intake_item_uuid=? AND intake_revision_uuid=?",
            (team_uuid, intake_item_uuid, revision_uuid),
        )
        if revision is None:
            raise ConflictError(
                "intake-revision-mismatch", "Requested Intake revision does not belong to the Intake item"
            )
        source = await tx.fetchone(
            "SELECT source_kind,source_kind_definition_digest,source_descriptor_ref,source_descriptor_digest "
            "FROM mkb_intake_sources WHERE team_uuid=? AND intake_source_uuid=?",
            (team_uuid, item["intake_source_uuid"]),
        )
        if source is None:
            raise MkbError("INTAKE_SOURCE_MISSING", "Intake item source is unavailable", 503)
        artifact = await tx.fetchone(
            "SELECT intake_artifact_uuid,logical_handle,content_digest,size_bytes FROM mkb_intake_artifacts "
            "WHERE team_uuid=? AND owner_revision_uuid=? AND artifact_role='clean_text' "
            "ORDER BY created_at DESC,intake_artifact_uuid DESC LIMIT 1",
            (team_uuid, revision_uuid),
        )
        if require_clean_artifact and artifact is None:
            raise ConflictError(
                "intake-rebuild-input-missing", "The selected Intake revision has no retained clean artifact"
            )
        return FrozenIntakeTarget(
            team_uuid=team_uuid,
            intake_item_uuid=intake_item_uuid,
            intake_source_uuid=item["intake_source_uuid"],
            lifecycle_state=item["lifecycle_state"],
            item_revision=item["row_revision"],
            intake_revision_uuid=revision_uuid,
            revision_fingerprint=revision["revision_fingerprint"],
            source_snapshot_uuid=revision["source_snapshot_uuid"],
            source_kind=source["source_kind"],
            source_kind_definition_digest=source["source_kind_definition_digest"],
            source_descriptor_ref=source["source_descriptor_ref"],
            source_descriptor_digest=source["source_descriptor_digest"],
            clean_artifact_uuid=None if artifact is None else artifact["intake_artifact_uuid"],
            clean_artifact_ref=None if artifact is None else artifact["logical_handle"],
            clean_artifact_digest=None if artifact is None else artifact["content_digest"],
            clean_artifact_size=None if artifact is None else artifact["size_bytes"],
        )

    async def _metadata_values_tx(
        self, tx: UnitOfWork, semantics: Mapping[str, Any]
    ) -> tuple[FrozenMetadataValue, ...]:
        if not semantics:
            raise MkbError("METADATA_SEMANTICS_EMPTY", "Metadata update requires at least one semantic value", 422)
        values: list[FrozenMetadataValue] = []
        for semantic_key in sorted(semantics):
            if not isinstance(semantic_key, str) or not semantic_key or len(semantic_key) > 128:
                raise MkbError("METADATA_SEMANTIC_KEY_INVALID", "Metadata semantic key is invalid", 422)
            definitions = await tx.fetchall(
                "SELECT semantic_key,definition_version,definition_digest,value_kind "
                "FROM mkb_intake_semantic_definitions WHERE semantic_key=? ORDER BY definition_version",
                (semantic_key,),
            )
            if not definitions:
                raise MkbError(
                    "METADATA_SEMANTIC_UNREGISTERED",
                    "Metadata semantic key is not registered",
                    422,
                    {"semantic_key": semantic_key},
                )
            if len(definitions) != 1:
                # Without a version selector in the public contract, silently
                # selecting a newly registered definition would reinterpret a
                # command.  Fail closed until the contract is versioned.
                raise MkbError(
                    "METADATA_SEMANTIC_AMBIGUOUS",
                    "Metadata semantic definition requires an explicit version",
                    409,
                    {"semantic_key": semantic_key},
                )
            definition = definitions[0]
            value = self._validate_semantic_value(definition["value_kind"], semantics[semantic_key])
            values.append(
                FrozenMetadataValue(
                    semantic_key=semantic_key,
                    definition_version=definition["definition_version"],
                    definition_digest=definition["definition_digest"],
                    value_kind=definition["value_kind"],
                    value=value,
                    value_digest=stable_digest(
                        {
                            "semantic_key": semantic_key,
                            "definition_version": definition["definition_version"],
                            "definition_digest": definition["definition_digest"],
                            "value": value,
                        }
                    ),
                )
            )
        return tuple(values)

    @staticmethod
    def _validate_semantic_value(value_kind: str, value: Any) -> bool | int | float | str:
        if value_kind == "bool" and type(value) is bool:
            return value
        if value_kind == "int" and type(value) is int:
            return value
        if value_kind == "real" and type(value) in {int, float}:
            return float(value)
        if value_kind == "text" and isinstance(value, str) and len(value) <= 16_384:
            return value
        # ``ref`` remains a logical opaque reference.  It must not be a
        # filesystem path, because S13 object/secret references are handles.
        if value_kind == "ref" and isinstance(value, str) and 0 < len(value) <= 4096 and not value.startswith("/"):
            return value
        raise MkbError(
            "METADATA_SEMANTIC_VALUE_INVALID",
            "Metadata value does not match its registered semantic definition",
            422,
        )


class IntakeLifecycleService:
    """Apply S04's logical lifecycle truth without a public write shortcut."""

    _ACTION_EFFECT = {"deactivate": "deactivate", "delete": "delete"}

    def __init__(self, persistence: PersistencePort, events: DomainEventWriter) -> None:
        self._persistence = persistence
        self._events = events

    async def apply(self, command: IntakeLifecycleCommand) -> LifecycleTransitionResult:
        """Atomically transition a canonical Item, append its ledger, and wake.

        Deactivation and deletion withdraw both S04's serving pointer and the
        S09 index projection in the same relational transaction.  The latter
        is defence in depth; S10's Item/serving double fence remains the
        authoritative protection against stale ANN material.
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
                now if target == "deactivated" else item["deactivated_at"],
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
            "policy_ref,policy_version,transition_fence,occurred_at,payload_extra) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'{}')",
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
        if command.action not in {"deactivate", "delete"}:
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
        payload: dict[str, Any] = {"execution_uuid": command.execution_uuid}
        if command.task_uuid is not None:
            payload["task_uuid"] = command.task_uuid
        now = utc_now()
        await tx.execute(
            "INSERT OR IGNORE INTO mkb_outbox "
            "(outbox_id,team_uuid,kind,payload_json,payload_digest,dedupe_key,status,available_at,created_at,updated_at,payload_extra) "
            "VALUES (?,?,'wake_execution',?,?,?,?,?,?,?,'{}')",
            (
                uuid7(),
                command.team_uuid,
                json.dumps(payload, sort_keys=True, separators=(",", ":")),
                stable_digest(payload),
                f"intake-lifecycle-wake:{command.execution_uuid}:{transition_fence}",
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


__all__ = [
    "FrozenIndexRebuildScope",
    "FrozenIntakeTarget",
    "FrozenMetadataUpdate",
    "FrozenMetadataValue",
    "IntakeLifecycleCommand",
    "IntakeLifecycleService",
    "IntakeTargetResolver",
    "LifecycleTransitionResult",
]
