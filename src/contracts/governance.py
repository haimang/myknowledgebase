"""Code-owned NHX1 identity, evidence, operation, and error registries."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import StrEnum
from types import MappingProxyType

from src.contracts.common.ids import stable_digest


class ObservationState(StrEnum):
    RESERVED = "reserved"
    ACQUIRED = "acquired"
    ACCEPTED = "accepted"
    FAILED = "failed"
    ABANDONED = "abandoned"


class ObjectUploadSessionState(StrEnum):
    RECEIVING = "receiving"
    PREPARED = "prepared"
    PROMOTED = "promoted"
    COMMITTED = "committed"
    RESERVED = "reserved"
    CONSUMED = "consumed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    FAILED = "failed"


class ProcessingBindingFamily(StrEnum):
    CLEAN_STRATEGY = "clean_strategy"
    REGISTERED_API_OPERATION = "registered_api_operation"


@dataclass(frozen=True, slots=True)
class ProcessingBinding:
    """Typed union for the ten clean strategies and three API operations."""

    family: ProcessingBindingFamily
    key: str
    definition_version: str
    definition_digest: str

    def __post_init__(self) -> None:
        if not self.key or not self.definition_version or not re.fullmatch(r"[0-9a-f]{64}", self.definition_digest):
            raise ValueError("processing binding coordinates are invalid")


class EvidenceVerdict(StrEnum):
    VERIFIED = "verified"
    INVALID = "invalid"
    LEGACY_UNVERIFIABLE = "legacy_unverifiable"


class CommandDisposition(StrEnum):
    APPLIED = "applied"
    REPLAYED = "replayed"
    NOOP = "noop"
    REJECTED = "rejected"


class OutboxCriticality(StrEnum):
    CRITICAL = "critical"
    ADVISORY = "advisory"


@dataclass(frozen=True, slots=True)
class OutboxKindDefinition:
    kind: str
    owner_kind: str
    criticality: OutboxCriticality
    attempt_budget: int
    dead_error_code: str
    requeue_policy: str = "generation_fenced"
    definition_version: str = "mkb.outbox-kind.v2"

    @property
    def definition_digest(self) -> str:
        return stable_digest(asdict(self))


@dataclass(frozen=True, slots=True)
class ErrorDefinition:
    code: str
    category: str
    http_status: int
    retryable: bool
    public_message: str
    legacy_aliases: tuple[str, ...] = ()
    definition_version: str = "mkb.error-definition.v2"

    def __post_init__(self) -> None:
        if re.fullmatch(r"[A-Z][A-Z0-9_]{1,127}", self.code) is None:
            raise ValueError("canonical error code must be UPPER_SNAKE_CASE")
        if not 400 <= self.http_status <= 599:
            raise ValueError("error definition HTTP status is invalid")

    @property
    def definition_digest(self) -> str:
        return stable_digest(asdict(self))


_OUTBOX_KIND_DEFINITIONS = {
    definition.kind: definition
    for definition in (
        OutboxKindDefinition("wake_execution", "execution", OutboxCriticality.CRITICAL, 8, "OUTBOX_WAKE_DEAD"),
        OutboxKindDefinition("wake_process", "process", OutboxCriticality.CRITICAL, 8, "OUTBOX_WAKE_DEAD"),
        OutboxKindDefinition("cancel_execution", "execution", OutboxCriticality.CRITICAL, 8, "OUTBOX_CANCEL_DEAD"),
        OutboxKindDefinition("gate_decision", "execution", OutboxCriticality.CRITICAL, 8, "OUTBOX_GATE_DEAD"),
        OutboxKindDefinition(
            "vectorize_construct", "execution", OutboxCriticality.CRITICAL, 8, "OUTBOX_VECTORIZE_DEAD"
        ),
    )
}
OUTBOX_KIND_DEFINITIONS = MappingProxyType(_OUTBOX_KIND_DEFINITIONS)

_ERROR_DEFINITIONS = {
    definition.code: definition
    for definition in (
        ErrorDefinition("OBSERVATION_CONFLICT", "conflict", 409, False, "Observation identity conflicts"),
        ErrorDefinition(
            "ITEM_EPOCH_CONFLICT",
            "fence",
            409,
            True,
            "Item changed; reload and retry",
            legacy_aliases=("intake-item-revision-conflict",),
        ),
        ErrorDefinition(
            "FULL_REPLAY_INPUT_UNAVAILABLE", "conflict", 409, False, "Frozen replay input is unavailable"
        ),
        ErrorDefinition("MODEL_AT_CAPACITY", "dependency", 429, True, "model at capacity"),
        ErrorDefinition("OBJECT_SESSION_CONFLICT", "conflict", 409, False, "Upload session conflicts"),
        ErrorDefinition(
            "LEGACY_EVIDENCE_UNVERIFIABLE", "integrity", 409, False, "Legacy evidence cannot be verified"
        ),
        ErrorDefinition("OUTBOX_CRITICAL_DEAD", "dependency", 503, True, "Required delivery failed permanently"),
        ErrorDefinition(
            "COMMAND_FENCE_CONFLICT",
            "fence",
            409,
            True,
            "Command target generation changed",
            legacy_aliases=("stale-process-fence",),
        ),
        ErrorDefinition("NHX1_SHADOW_MISMATCH", "integrity", 503, False, "Migration shadow validation failed"),
    )
}
ERROR_DEFINITIONS = MappingProxyType(_ERROR_DEFINITIONS)


def resolve_error_definition(code: str) -> ErrorDefinition:
    direct = ERROR_DEFINITIONS.get(code)
    if direct is not None:
        return direct
    for definition in ERROR_DEFINITIONS.values():
        if code in definition.legacy_aliases:
            return definition
    raise KeyError(code)
