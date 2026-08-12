"""Supporting models/constants for this service package."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from src.contracts.vector.models import (
    RetrievalResult,
)

_FILTER_KEYS = frozenset({"intake_item_uuid", "source_kind", "channel"})

_SOURCE_KINDS = frozenset({"inline_payload", "local_object", "http_resource", "registered_api"})

_DISTANCE_METRICS = frozenset({"cosine", "l2", "inner_product"})

_REQUEST_KEYS = frozenset(
    {
        "schema_version",
        "team_uuid",
        "query",
        "namespace_key",
        "namespace_uuid",
        "return_k",
        "recall_k",
        "score_threshold",
        "threshold",  # compact-profile compatibility alias
        "include_pack",
        "top_k",  # compact-profile compatibility alias
        "filters",
    }
)

_FORBIDDEN_REQUEST_KEYS = frozenset(
    {
        "index_generation",
        "raw_query_vector",
        "query_embedding",
        "distance_metric",
        "embedding_model",
        "model_override",
        "include_answer",
        "stream",
    }
)

_ABSOLUTE_PATH_IN_TEXT = re.compile(r"(?<![:/\w])/(?:[\w.-]+/)*[\w.-]+")

_GRANULARITY_PATTERNS = (
    re.compile(r"(?:^|[._:/-])g(?:ranularity)?[=_:-]?([012])(?:$|[._:/-])", re.IGNORECASE),
    re.compile(r"^(?:granularity[=_:-]?)?([012])(?:[._:/-]|$)", re.IGNORECASE),
)

_TOKEN = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)

_PROOF_COMPLETE_SET_PREDICATE = (
    "proof.actual_count=(SELECT COUNT(*) FROM mkb_vector_records AS proof_record "
    "WHERE proof_record.team_uuid=proof.team_uuid "
    "AND proof_record.intake_item_uuid=proof.intake_item_uuid "
    "AND proof_record.intake_revision_uuid=proof.intake_revision_uuid "
    "AND proof_record.namespace_uuid=proof.namespace_uuid "
    "AND proof_record.generation_artifact_uuid=proof.generation_artifact_uuid "
    "AND proof_record.generation_artifact_type=proof.generation_artifact_type "
    "AND proof_record.embedding_model=proof.embedding_model "
    "AND proof_record.embedding_model_key=proof.embedding_model_key "
    "AND proof_record.embedding_model_version=proof.embedding_model_version "
    "AND proof_record.adapter_kind=proof.adapter_kind "
    "AND proof_record.dimension=proof.dimension "
    "AND proof_record.index_generation=proof.index_generation "
    "AND proof_record.deleted_at IS NULL "
    "AND proof_record.publication_state='indexed')"
)

class CandidateScorer(Protocol):
    """Optional deterministic/ANN scoring seam for non-live test profiles.

    Scores supplied by this seam must already be a finite, higher-is-better
    relevance score in the selected namespace metric.  The local exact profile
    below performs that normalization itself, including for controlled ``l2``
    namespaces.
    """

    def __call__(
        self,
        *,
        query: str,
        namespace: Mapping[str, Any],
        candidates: Sequence[Mapping[str, Any]],
    ) -> Mapping[str, float] | Awaitable[Mapping[str, float]]: ...

@dataclass(frozen=True, slots=True)
class _SearchInput:
    team_uuid: str
    query: str
    namespace_key: str | None
    namespace_uuid: str | None
    return_k: int
    recall_k: int
    threshold: float
    filters: dict[str, str]
    include_pack: bool

@dataclass(slots=True)
class _Candidate:
    row: dict[str, Any]
    ann_score: float
    granularity: int

    @property
    def vector_record_uuid(self) -> str:
        return str(self.row["vector_record_uuid"])

@dataclass(slots=True)
class _Material:
    content: str | None
    content_ref: str | None
    granularity: int | None = None
    # ``content_ref`` can be a safe fallback derived from a vector row.  It is
    # useful to keep an otherwise valid hit inspectable, but it is not proof
    # that the requested generation/channel was actually hydrated.  Traceback
    # must never mistake that fallback for a resolved original.
    hydrated: bool = False

    @property
    def available(self) -> bool:
        return self.content is not None or self.content_ref is not None

@dataclass(slots=True)
class _ResultWork:
    result: RetrievalResult
    candidate: _Candidate
