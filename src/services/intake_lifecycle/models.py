"""Lifecycle DTOs and frozen target shapes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

LifecycleAction = Literal["deactivate", "reactivate", "delete"]


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
    proof_ref: str | None = None
    proof_digest: str | None = None
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
class IntakePublicationCommand:
    """One proof-bound S04 serving-pointer advancement.

    S09 owns vector/index generation and produces the immutable
    ``mkb_publication_proofs`` row.  It must hand that row to this service to
    expose a Revision: no vector worker is allowed to update an Item's
    ``serving_revision_uuid`` directly.  The command is intentionally
    worker-only and causally complete so the Item CAS, transition ledger, and
    durable wake intent can be committed in the caller's Process UoW.
    """

    team_uuid: str
    intake_item_uuid: str
    intake_revision_uuid: str
    publication_proof_uuid: str
    namespace_uuid: str
    index_generation: int
    trace_uuid: str
    idempotency_key: str
    expected_item_revision: int | None = None
    task_uuid: str | None = None
    execution_uuid: str | None = None
    process_uuid: str | None = None
    proof_ref: str | None = None
    proof_digest: str | None = None
    actor_kind: Literal["system", "worker", "upstream", "operator"] = "worker"


@dataclass(frozen=True, slots=True)
class PublicationTransitionResult:
    """Compact outcome of a proof-valid serving pointer transition."""

    team_uuid: str
    intake_item_uuid: str
    intake_revision_uuid: str
    publication_proof_uuid: str
    before_serving_revision_uuid: str | None
    serving_revision_uuid: str | None
    item_revision: int
    transition_fence: str
    applied: bool


@dataclass(frozen=True, slots=True)
class FrozenIntakeTarget:
    """Exact non-secret Intake coordinates to embed in a new Execution input."""

    team_uuid: str
    intake_item_uuid: str
    intake_source_uuid: str
    normalized_external_key: str
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
            "normalized_external_key": self.normalized_external_key,
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
    fingerprint_participation: bool
    value: bool | int | float | str
    value_digest: str

    def as_manifest(self) -> dict[str, Any]:
        return {
            "semantic_key": self.semantic_key,
            "definition_version": self.definition_version,
            "definition_digest": self.definition_digest,
            "value_kind": self.value_kind,
            "fingerprint_participation": self.fingerprint_participation,
            "value": self.value,
            "value_digest": self.value_digest,
        }


@dataclass(frozen=True, slots=True)
class FrozenMetadataUpdate:
    target: FrozenIntakeTarget
    base_semantics: tuple[FrozenMetadataValue, ...]
    semantics: tuple[FrozenMetadataValue, ...]

    def as_manifest(self) -> dict[str, Any]:
        return {
            "schema_version": "mkb.frozen-metadata-update.v1",
            "target": self.target.as_manifest(),
            "base_semantics": [value.as_manifest() for value in self.base_semantics],
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
