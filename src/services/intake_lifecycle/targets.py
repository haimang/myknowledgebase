"""Intake target resolution for rebuild/metadata/lifecycle/index scopes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.contracts.api.models import (
    IndexRebuildPayload,
    IntakeLifecyclePayload,
    IntakeRebuildPayload,
    IntakeUpdateMetadataPayload,
)
from src.contracts.common.errors import ConflictError, MkbError, NotFoundError
from src.contracts.common.ids import stable_digest
from src.persistence.ports import PersistencePort, UnitOfWork
from src.services.intake_lifecycle.models import (
    FrozenIndexRebuildScope,
    FrozenIntakeTarget,
    FrozenMetadataUpdate,
    FrozenMetadataValue,
)


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
            base_semantics = await self._revision_metadata_values_tx(
                tx,
                team_uuid=team_uuid,
                intake_revision_uuid=target.intake_revision_uuid,
            )
            semantics = await self._metadata_values_tx(tx, team_uuid, payload.semantics)
        return FrozenMetadataUpdate(target=target, base_semantics=base_semantics, semantics=semantics)

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
            normalized_external_key=item["normalized_external_key"],
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
        self, tx: UnitOfWork, team_uuid: str, semantics: Mapping[str, Any]
    ) -> tuple[FrozenMetadataValue, ...]:
        if not semantics:
            raise MkbError("METADATA_SEMANTICS_EMPTY", "Metadata update requires at least one semantic value", 422)
        values: list[FrozenMetadataValue] = []
        for semantic_key in sorted(semantics):
            if not isinstance(semantic_key, str) or not semantic_key or len(semantic_key) > 128:
                raise MkbError("METADATA_SEMANTIC_KEY_INVALID", "Metadata semantic key is invalid", 422)
            definitions = await tx.fetchall(
                "SELECT semantic_key,definition_version,definition_digest,value_kind,fingerprint_participation "
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
            definition_version, raw_value = self._parse_metadata_submission(semantics[semantic_key])
            if definition_version is not None:
                definition = next(
                    (row for row in definitions if row["definition_version"] == definition_version),
                    None,
                )
                if definition is None:
                    raise MkbError(
                        "METADATA_SEMANTIC_VERSION_UNREGISTERED",
                        "Metadata semantic definition version is not registered",
                        422,
                        {"semantic_key": semantic_key, "definition_version": definition_version},
                    )
            elif len(definitions) != 1:
                # Without a version selector in the public contract, silently
                # selecting a newly registered definition would reinterpret a
                # command.  Fail closed until the contract is versioned.
                raise MkbError(
                    "METADATA_SEMANTIC_AMBIGUOUS",
                    "Metadata semantic definition requires an explicit version",
                    409,
                    {"semantic_key": semantic_key},
                )
            else:
                definition = definitions[0]
            value = self._validate_semantic_value(definition["value_kind"], raw_value)
            if definition["value_kind"] == "ref":
                artifact = await tx.fetchone(
                    "SELECT intake_artifact_uuid FROM mkb_intake_artifacts "
                    "WHERE team_uuid=? AND intake_artifact_uuid=?",
                    (team_uuid, value),
                )
                if artifact is None:
                    # Do not distinguish a foreign-team identity from a
                    # missing one: the ref is a tenant-fenced durable fact.
                    raise MkbError(
                        "METADATA_SEMANTIC_REF_UNAVAILABLE",
                        "Metadata reference is not an available Intake artifact",
                        422,
                    )
            values.append(
                FrozenMetadataValue(
                    semantic_key=semantic_key,
                    definition_version=definition["definition_version"],
                    definition_digest=definition["definition_digest"],
                    value_kind=definition["value_kind"],
                    fingerprint_participation=bool(definition["fingerprint_participation"]),
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

    async def _revision_metadata_values_tx(
        self,
        tx: UnitOfWork,
        *,
        team_uuid: str,
        intake_revision_uuid: str,
    ) -> tuple[FrozenMetadataValue, ...]:
        """Freeze the predecessor's exact semantic set for a metadata Task.

        The worker must not recompute fingerprint participation from a later
        registry read.  Snapshotting every inherited definition/value tuple
        also makes the metadata merge independently reproducible from the
        immutable Task input object.
        """

        rows = await tx.fetchall(
            "SELECT s.semantic_key,s.definition_version,s.value_digest,s.value_kind,s.value_bool,s.value_int,s.value_real,"
            "s.value_text,s.value_artifact_uuid,d.definition_digest,d.value_kind AS definition_value_kind,"
            "d.fingerprint_participation FROM mkb_intake_revision_semantics AS s "
            "JOIN mkb_intake_semantic_definitions AS d ON d.semantic_key=s.semantic_key "
            "AND d.definition_version=s.definition_version "
            "WHERE s.team_uuid=? AND s.intake_revision_uuid=? ORDER BY s.semantic_key",
            (team_uuid, intake_revision_uuid),
        )
        values: list[FrozenMetadataValue] = []
        for row in rows:
            storage_kind = row["value_kind"]
            definition_kind = row["definition_value_kind"]
            participation = row["fingerprint_participation"]
            if type(participation) is not int or participation not in {0, 1}:
                raise MkbError("METADATA_SEMANTICS_INVALID", "Semantic definition participation is invalid", 503)
            if storage_kind == "bool" and row["value_bool"] in {0, 1}:
                kind, value = "bool", bool(row["value_bool"])
            elif storage_kind == "int" and isinstance(row["value_int"], int):
                kind, value = "int", row["value_int"]
            elif storage_kind == "real" and isinstance(row["value_real"], int | float):
                kind, value = "real", float(row["value_real"])
            elif storage_kind == "text" and isinstance(row["value_text"], str):
                kind, value = "text", row["value_text"]
            elif storage_kind == "artifact_ref" and definition_kind == "ref" and isinstance(row["value_artifact_uuid"], str):
                kind, value = "ref", row["value_artifact_uuid"]
            else:
                raise MkbError("METADATA_SEMANTICS_INVALID", "Existing semantic value cannot be frozen", 503)
            if kind != definition_kind:
                raise MkbError("METADATA_SEMANTICS_INVALID", "Existing semantic definition does not match its value", 503)
            expected_digest = stable_digest(
                {
                    "semantic_key": row["semantic_key"],
                    "definition_version": row["definition_version"],
                    "definition_digest": row["definition_digest"],
                    "value": value,
                }
            )
            if row["value_digest"] != expected_digest:
                raise MkbError("METADATA_SEMANTICS_INVALID", "Existing semantic value digest is invalid", 503)
            values.append(
                FrozenMetadataValue(
                    semantic_key=row["semantic_key"],
                    definition_version=row["definition_version"],
                    definition_digest=row["definition_digest"],
                    value_kind=kind,
                    fingerprint_participation=bool(participation),
                    value=value,
                    value_digest=row["value_digest"],
                )
            )
        return tuple(values)

    @staticmethod
    def _parse_metadata_submission(value: Any) -> tuple[str | None, Any]:
        """Accept a scalar v1 value or an exact versioned value wrapper.

        Scalar values remain compatible only while a semantic key has one
        registered definition.  Once a definition evolves, callers must bind
        the version explicitly so a frozen Task can never silently select a
        newly registered meaning.
        """

        if not isinstance(value, Mapping):
            return None, value
        if set(value) != {"definition_version", "value"}:
            raise MkbError(
                "METADATA_SEMANTIC_SUBMISSION_INVALID",
                "Versioned metadata value must contain only definition_version and value",
                422,
            )
        definition_version = value.get("definition_version")
        if not isinstance(definition_version, str) or not definition_version or len(definition_version) > 128:
            raise MkbError(
                "METADATA_SEMANTIC_VERSION_INVALID",
                "Metadata semantic definition version is invalid",
                422,
            )
        return definition_version, value["value"]

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
