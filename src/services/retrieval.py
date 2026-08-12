"""S10's synchronous, context-only retrieval capability.

This module is deliberately read-only.  It talks to persistence only through
``PersistencePort`` and to inference only through ``InferenceFacade``; it never
imports a database driver, object-store adapter, or model adapter.  The SQL
candidate predicate is intentionally explicit rather than relying on a loose
"ANN hit means serve" convention: a record must be indexed, proven, pointed to
by an active index pointer, and attached to an active serving Intake revision.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import math
import re
import struct
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from src.contracts.api.models import RetrievalRequest
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import validate_external_uuid
from src.contracts.common.models import assert_safe_public_data
from src.contracts.inference.models import EmbeddingRequest, InferenceBinding
from src.contracts.vector.models import (
    GenerationScopedCoordinate,
    PackSegment,
    PackView,
    RetrievalBody,
    RetrievalBundle,
    RetrievalDiagnostics,
    RetrievalGenerationRefs,
    RetrievalResult,
)
from src.persistence.ports import IntakeEligibilityPort, PersistencePort, RetrievalBodyPort, UnitOfWork
from src.runtime.inference.facade import InferenceFacade
from src.services.deterministic_embedding import deterministic_embedding

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
# A durable proof is a complete-set assertion, not merely a permissive label
# on whichever rows happen to be returned by an ANN scan.  Both candidate
# reads below apply this predicate so a deleted or injected active row cannot
# make a partial generation appear publishable.
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


class RetrievalService:
    """A sync S10 search surface with no Task/Process/Audit side effects.

    ``live_inference=False`` is an explicit deterministic profile intended for
    unit/e2e fixtures where an inference service is not present.  Production
    callers set it to ``True`` to bind the query to S11's embed facade.  In both
    profiles SQL still enforces the same S09+S04 serving fences.

    ``body_port`` is a persistence-side port that can dereference immutable
    generation artifacts.  It is optional so query-only deployments can return
    logical content references without allowing the service to touch a storage
    adapter directly.
    """

    def __init__(
        self,
        persistence: PersistencePort,
        inference: InferenceFacade | None = None,
        *,
        body_port: RetrievalBodyPort | Callable[..., Any] | None = None,
        eligibility_port: IntakeEligibilityPort | None = None,
        candidate_scorer: CandidateScorer | None = None,
        live_inference: bool = False,
        rerank_enabled: bool = True,
        max_topk: int = 100,
        default_score_threshold: float = 0.0,
        pack_max_hits: int = 5,
        pack_max_chars: int = 12_000,
        inflation_max_roots: int = 3,
        inflation_per_root_max_chars: int = 8_000,
        candidate_scan_limit: int = 1_000,
    ) -> None:
        if max_topk < 1 or pack_max_hits < 1 or pack_max_chars < 1:
            raise ValueError("retrieval limits must be positive")
        if inflation_max_roots < 0 or inflation_per_root_max_chars < 1 or candidate_scan_limit < max_topk:
            raise ValueError("invalid retrieval bounded-scan configuration")
        try:
            normalized_default_threshold = float(default_score_threshold)
        except (TypeError, ValueError) as exc:
            raise ValueError("default_score_threshold must be finite") from exc
        if not math.isfinite(normalized_default_threshold):
            raise ValueError("default_score_threshold must be finite")
        self._persistence = persistence
        self._inference = inference
        self._body_port = body_port
        self._eligibility_port = eligibility_port
        self._candidate_scorer = candidate_scorer
        self._live_inference = live_inference
        self._rerank_enabled = rerank_enabled
        self._max_topk = max_topk
        self._default_score_threshold = normalized_default_threshold
        self._pack_max_hits = pack_max_hits
        self._pack_max_chars = pack_max_chars
        self._inflation_max_roots = inflation_max_roots
        self._inflation_per_root_max_chars = inflation_per_root_max_chars
        self._candidate_scan_limit = candidate_scan_limit

    async def search(self, request: RetrievalRequest | Mapping[str, Any] | Any) -> dict[str, Any]:
        """Return a JSON-safe S10 bundle or raise a typed ``RETRIEVE_*`` error."""

        query = self._normalise_request(request)
        query_digest = hashlib.sha256(query.query.encode("utf-8")).hexdigest()
        if not query.query.strip():
            return self._empty_bundle(query, query_digest, "blank_query").model_dump(mode="json")

        try:
            async with self._persistence.transaction() as tx:
                namespace = await self._resolve_namespace(tx, query)
                binding = await self._resolve_embed_binding(tx, query.team_uuid, namespace)
        except MkbError:
            raise
        except Exception as exc:
            raise MkbError("RETRIEVE_DEPENDENCY_PERSISTENCE", "Retrieval persistence is unavailable", 503) from exc

        query_embedding: list[float] | None = None
        if self._live_inference:
            query_embedding = await self._embed_query(query, namespace, binding)

        try:
            async with self._persistence.transaction() as tx:
                rows = await self._fetch_candidate_rows(tx, namespace, query)
        except MkbError:
            raise
        except Exception as exc:
            raise MkbError("RETRIEVE_DEPENDENCY_VECTOR", "Vector retrieval dependency is unavailable", 503) from exc

        candidates = await self._rank_ann_candidates(query, namespace, rows, query_embedding)
        ann_hit_count = len(candidates)
        if not candidates:
            return self._empty_bundle(query, query_digest, "no_hit", ann_hit_count=0).model_dump(mode="json")

        thresholded = [candidate for candidate in candidates if candidate.ann_score >= query.threshold]
        if not thresholded:
            return self._empty_bundle(
                query,
                query_digest,
                "below_threshold",
                ann_hit_count=ann_hit_count,
                filtered_count=ann_hit_count,
            ).model_dump(mode="json")

        # The S04 batch fence is necessary but not sufficient: a publication
        # can be withdrawn between the initial S09 candidate scan and this
        # point.  ``_apply_batch_eligibility`` therefore completes with a
        # second, current S09 proof/pointer check before any body is hydrated.
        eligible = await self._apply_batch_eligibility(query, namespace, thresholded)
        filtered_count = ann_hit_count - len(eligible)
        if not eligible:
            return self._empty_bundle(
                query,
                query_digest,
                "all_filtered",
                ann_hit_count=ann_hit_count,
                filtered_count=filtered_count,
            ).model_dump(mode="json")

        traceback_rows = await self._load_traceback_originals(query, namespace, eligible)
        work = [await self._to_result_work(query, candidate, traceback_rows) for candidate in eligible]
        await self._inflate_documents(query, namespace, work)
        work = self._deduplicate(work)

        rerank_status = await self._rerank(query.query, work)
        work = work[: query.return_k]
        results = [item.result for item in work]

        pack: PackView | None = None
        pack_truncated = False
        if query.include_pack:
            try:
                pack = self._pack(results)
                pack_truncated = pack.truncated
            except Exception:
                # Packing is a view only; it must never erase otherwise valid
                # grounded results.
                pack = None
                pack_truncated = True

        diagnostics = RetrievalDiagnostics(
            recall_k=query.recall_k,
            return_k=query.return_k,
            threshold_applied=query.threshold,
            ann_hit_count=ann_hit_count,
            eligible_count=len(eligible),
            filtered_count=filtered_count,
            rerank_status=rerank_status,
            pack_truncated=pack_truncated,
            inflation_truncated=any(item.result.inflation_status == "truncated" for item in work),
            filters_echo=query.filters,
        )
        return RetrievalBundle(
            disposition="ok",
            team_uuid=query.team_uuid,
            query_digest=query_digest,
            results=results,
            pack=pack,
            diagnostics=diagnostics,
        ).model_dump(mode="json")

    def _normalise_request(self, request: RetrievalRequest | Mapping[str, Any] | Any) -> _SearchInput:
        if isinstance(request, Mapping):
            if not all(isinstance(key, str) for key in request):
                raise MkbError("RETRIEVE_SCHEMA_INVALID", "retrieval request field names are invalid", 422)
            supplied_keys = {str(key) for key in request}
            forbidden = supplied_keys & _FORBIDDEN_REQUEST_KEYS
            if forbidden:
                raise MkbError(
                    "RETRIEVE_SCHEMA_FORBIDDEN_FIELD",
                    "v1 retrieval does not allow client index/model/vector/answer overrides",
                    422,
                    {"keys": sorted(forbidden)},
                )
            unknown = supplied_keys - _REQUEST_KEYS
            if unknown:
                raise MkbError(
                    "RETRIEVE_SCHEMA_UNKNOWN_FIELD",
                    "unknown retrieval request field",
                    422,
                    {"keys": sorted(unknown)},
                )
            schema_version = self._request_value(request, "schema_version")
            if schema_version is not None and schema_version != "mkb.retrieval.v1":
                raise MkbError("RETRIEVE_SCHEMA_INVALID", "unsupported retrieval schema version", 422)
        team_uuid = self._request_value(request, "team_uuid")
        raw_query = self._request_value(request, "query")
        if not isinstance(team_uuid, str) or not team_uuid.strip():
            raise MkbError("RETRIEVE_SCHEMA_TEAM_REQUIRED", "team_uuid is required for retrieval", 422)
        try:
            team_uuid = validate_external_uuid(team_uuid, field="team_uuid")
        except Exception as exc:
            raise MkbError("RETRIEVE_SCHEMA_TEAM_REQUIRED", "team_uuid is required for retrieval", 422) from exc
        if not isinstance(raw_query, str):
            raise MkbError("RETRIEVE_SCHEMA_QUERY_INVALID", "query must be a string", 422)
        if len(raw_query) > 8192:
            raise MkbError("RETRIEVE_SCHEMA_INVALID", "query exceeds the v1 size limit", 422)

        # ``top_k`` remains a transitional API input; the S10 name is
        # ``return_k``.  Supplying both is ambiguous and therefore rejected.
        raw_return_k = self._request_value(request, "return_k")
        raw_top_k = self._request_value(request, "top_k")
        if raw_return_k is not None and raw_top_k is not None:
            raise MkbError("RETRIEVE_TOPK_INVALID", "use return_k instead of top_k", 422)
        if raw_return_k is None:
            raw_return_k = raw_top_k
        return_k = 10 if raw_return_k is None else self._as_positive_int(raw_return_k, "return_k")
        raw_recall_k = self._request_value(request, "recall_k")
        recall_k = 20 if raw_recall_k is None else self._as_positive_int(raw_recall_k, "recall_k")
        if return_k > self._max_topk or recall_k > self._max_topk or return_k > recall_k:
            raise MkbError(
                "RETRIEVE_TOPK_INVALID",
                "return_k and recall_k must satisfy 1 <= return_k <= recall_k <= max_topk",
                422,
                {"max_topk": self._max_topk},
            )

        raw_threshold = self._request_value(request, "score_threshold")
        if raw_threshold is None:
            raw_threshold = self._request_value(request, "threshold")
        threshold = (
            self._default_score_threshold
            if raw_threshold is None
            else self._as_finite_float(raw_threshold, "score_threshold")
        )

        raw_filters = self._request_value(request, "filters")
        filters = self._normalise_filters(raw_filters)
        namespace_key = self._request_value(request, "namespace_key")
        namespace_uuid = self._request_value(request, "namespace_uuid")
        if namespace_key is None and namespace_uuid is None:
            namespace_key = "default"
        if namespace_key is not None and (not isinstance(namespace_key, str) or not namespace_key.strip()):
            raise MkbError("RETRIEVE_SCHEMA_NAMESPACE_INVALID", "namespace_key must be a non-empty string", 422)
        if isinstance(namespace_key, str) and len(namespace_key) > 256:
            raise MkbError("RETRIEVE_SCHEMA_NAMESPACE_INVALID", "namespace_key exceeds the v1 size limit", 422)
        if namespace_uuid is not None and (not isinstance(namespace_uuid, str) or not namespace_uuid.strip()):
            raise MkbError("RETRIEVE_SCHEMA_NAMESPACE_INVALID", "namespace_uuid must be a non-empty string", 422)
        if namespace_uuid is not None:
            try:
                namespace_uuid = validate_external_uuid(namespace_uuid, field="namespace_uuid")
            except Exception as exc:
                raise MkbError("RETRIEVE_SCHEMA_NAMESPACE_INVALID", "namespace_uuid is invalid", 422) from exc
        if namespace_key is not None and namespace_uuid is not None:
            raise MkbError("RETRIEVE_SCHEMA_NAMESPACE_INVALID", "only one namespace selector may be supplied", 422)

        include_pack = self._request_value(request, "include_pack")
        if include_pack is None:
            include_pack = True
        if not isinstance(include_pack, bool):
            raise MkbError("RETRIEVE_SCHEMA_PACK_INVALID", "include_pack must be boolean", 422)

        return _SearchInput(
            team_uuid=team_uuid,
            query=raw_query.strip(),
            namespace_key=namespace_key,
            namespace_uuid=namespace_uuid,
            return_k=return_k,
            recall_k=recall_k,
            threshold=threshold,
            filters=filters,
            include_pack=include_pack,
        )

    @staticmethod
    def _request_value(request: RetrievalRequest | Mapping[str, Any] | Any, key: str) -> Any:
        if isinstance(request, Mapping):
            return request.get(key)
        return getattr(request, key, None)

    @staticmethod
    def _as_positive_int(value: Any, field: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise MkbError("RETRIEVE_TOPK_INVALID", f"{field} must be a positive integer", 422)
        return value

    @staticmethod
    def _as_finite_float(value: Any, field: str) -> float:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise MkbError("RETRIEVE_SCHEMA_THRESHOLD_INVALID", f"{field} must be a number", 422)
        result = float(value)
        if not math.isfinite(result):
            raise MkbError("RETRIEVE_SCHEMA_THRESHOLD_INVALID", f"{field} must be finite", 422)
        return result

    def _normalise_filters(self, raw_filters: Any) -> dict[str, str]:
        if raw_filters is None:
            return {}
        if hasattr(raw_filters, "model_dump"):
            raw_filters = raw_filters.model_dump(exclude_none=True)
        if not isinstance(raw_filters, Mapping):
            raise MkbError("RETRIEVE_FILTER_INVALID", "filters must be an object", 422)
        if not all(isinstance(key, str) for key in raw_filters):
            raise MkbError("RETRIEVE_FILTER_INVALID", "retrieval filter keys are invalid", 422)
        unknown = set(raw_filters) - _FILTER_KEYS
        if unknown:
            raise MkbError(
                "RETRIEVE_FILTER_INVALID",
                "unknown retrieval filter key",
                422,
                {"keys": sorted(unknown)},
            )
        filters: dict[str, str] = {}
        for key, value in raw_filters.items():
            if value is None:
                continue
            if not isinstance(value, str) or not value:
                raise MkbError("RETRIEVE_FILTER_INVALID", f"filter {key} must be a non-empty string", 422)
            if key == "intake_item_uuid":
                try:
                    value = validate_external_uuid(value, field="intake_item_uuid")
                except Exception as exc:
                    raise MkbError("RETRIEVE_FILTER_INVALID", "intake_item_uuid filter is invalid", 422) from exc
            if key == "source_kind" and value not in _SOURCE_KINDS:
                raise MkbError("RETRIEVE_FILTER_INVALID", "source_kind is not registered", 422)
            if key == "channel" and value not in {"original", "summary"}:
                raise MkbError("RETRIEVE_FILTER_INVALID", "channel must be original or summary", 422)
            filters[str(key)] = value
        try:
            assert_safe_public_data(filters)
        except ValueError as exc:
            raise MkbError("RETRIEVE_FILTER_INVALID", "unsafe retrieval filter", 422) from exc
        return filters

    async def _resolve_namespace(self, tx: UnitOfWork, query: _SearchInput) -> dict[str, Any]:
        if query.namespace_uuid is not None:
            row = await tx.fetchone(
                "SELECT namespace_uuid,team_uuid,namespace_key,embedding_model,embedding_model_key,embedding_model_version,"
                "adapter_kind,dimension,distance_metric FROM mkb_vector_namespaces "
                "WHERE team_uuid=? AND namespace_uuid=? AND status='active' AND deleted_at IS NULL",
                (query.team_uuid, query.namespace_uuid),
            )
        else:
            row = await tx.fetchone(
                "SELECT namespace_uuid,team_uuid,namespace_key,embedding_model,embedding_model_key,embedding_model_version,"
                "adapter_kind,dimension,distance_metric FROM mkb_vector_namespaces "
                "WHERE team_uuid=? AND namespace_key=? AND status='active' AND deleted_at IS NULL",
                (query.team_uuid, query.namespace_key),
            )
        if row is None:
            raise MkbError("RETRIEVE_SPACE_NAMESPACE_UNKNOWN", "active retrieval namespace was not found", 404)
        try:
            dimension = int(row["dimension"])
        except (TypeError, ValueError) as exc:
            raise MkbError("RETRIEVE_SPACE_INVALID", "namespace has an invalid embedding dimension", 503) from exc
        if isinstance(row["dimension"], bool) or dimension < 1:
            raise MkbError("RETRIEVE_SPACE_INVALID", "namespace has an invalid embedding dimension", 503)
        if any(
            not isinstance(row[field], str) or not row[field]
            for field in ("embedding_model", "embedding_model_key", "embedding_model_version", "adapter_kind")
        ):
            raise MkbError("RETRIEVE_SPACE_INVALID", "namespace has an invalid Layer A", 503)
        if row["distance_metric"] not in _DISTANCE_METRICS:
            raise MkbError("RETRIEVE_SPACE_METRIC_INVALID", "namespace has an unsupported distance metric", 503)
        return row

    async def _resolve_embed_binding(
        self, tx: UnitOfWork, team_uuid: str, namespace: Mapping[str, Any]
    ) -> InferenceBinding | None:
        if not self._live_inference:
            return None
        row = await tx.fetchone(
            "SELECT capability_key,adapter_kind,model_key,model_version,binding_digest "
            "FROM mkb_adapter_bindings WHERE capability_key='embed' AND enabled=1 "
            "AND adapter_kind=? AND model_key=? AND model_version=? "
            "AND (team_uuid=? OR team_uuid IS NULL) "
            "ORDER BY CASE WHEN team_uuid=? THEN 0 ELSE 1 END, priority ASC LIMIT 1",
            (
                namespace["adapter_kind"],
                namespace["embedding_model_key"],
                namespace["embedding_model_version"],
                team_uuid,
                team_uuid,
            ),
        )
        if row is None:
            raise MkbError("RETRIEVE_INFERENCE_BINDING_MISSING", "embed binding is unavailable", 503)
        try:
            return InferenceBinding.model_validate(row)
        except Exception as exc:
            raise MkbError("RETRIEVE_SPACE_BINDING_INVALID", "embed binding is invalid", 503) from exc

    async def _embed_query(
        self, query: _SearchInput, namespace: Mapping[str, Any], binding: InferenceBinding | None
    ) -> list[float]:
        if self._inference is None or binding is None:
            raise MkbError("RETRIEVE_INFERENCE_EMBED_UNAVAILABLE", "embed facade is unavailable", 503)
        try:
            response = await self._inference.embed(
                EmbeddingRequest(team_uuid=query.team_uuid, binding=binding, texts=[query.query])
            )
        except MkbError as exc:
            raise MkbError("RETRIEVE_INFERENCE_EMBED_FAILED", "query embedding failed", 503) from exc
        except Exception as exc:
            raise MkbError("RETRIEVE_INFERENCE_EMBED_FAILED", "query embedding failed", 503) from exc
        response_adapter_kind = getattr(response, "adapter_kind", None)
        if (
            response.model_key != namespace["embedding_model_key"]
            or response.model_version != namespace["embedding_model_version"]
            or (response_adapter_kind is not None and response_adapter_kind != namespace["adapter_kind"])
            or response.dimension != int(namespace["dimension"])
            or len(response.vectors) != 1
            or len(response.vectors[0]) != int(namespace["dimension"])
        ):
            raise MkbError("RETRIEVE_SPACE_LAYER_A_MISMATCH", "query embedding does not match namespace Layer A", 422)
        try:
            vector = [float(value) for value in response.vectors[0]]
        except (TypeError, ValueError) as exc:
            raise MkbError("RETRIEVE_INFERENCE_EMBED_FAILED", "query embedding is invalid", 503) from exc
        if not all(math.isfinite(value) for value in vector):
            raise MkbError("RETRIEVE_INFERENCE_EMBED_FAILED", "query embedding is invalid", 503)
        return vector

    async def _fetch_candidate_rows(
        self,
        tx: UnitOfWork,
        namespace: Mapping[str, Any],
        query: _SearchInput,
        *,
        coordinate_pairs: Sequence[tuple[str, str]] = (),
        generation_artifact_ids: Sequence[str] = (),
        force_channel: str | None = None,
    ) -> list[dict[str, Any]]:
        """Read candidates through S09 proof/pointer and S04 serving fences."""

        where = [
            "r.team_uuid=?",
            "r.namespace_uuid=?",
            "r.deleted_at IS NULL",
            "r.publication_state='indexed'",  # record-level S09 projection
            "n.status='active'",
            "n.deleted_at IS NULL",
            "r.embedding_model=n.embedding_model",
            "r.embedding_model_key=n.embedding_model_key",
            "r.embedding_model_version=n.embedding_model_version",
            "r.adapter_kind=n.adapter_kind",
            "r.dimension=n.dimension",
            "p.lifecycle_state='active'",  # ActiveIndexPointer fence
            "p.active_index_generation=r.index_generation",
            "p.generation_artifact_uuid=r.generation_artifact_uuid",
            "p.last_proof_uuid IS NOT NULL",
            "proof.proof_uuid=p.last_proof_uuid",  # durable PublicationProof
            "proof.proof_type='index.publication.v1'",
            "proof.proof_version='v1'",
            "proof.team_uuid=r.team_uuid",
            "proof.intake_item_uuid=r.intake_item_uuid",
            "proof.intake_revision_uuid=r.intake_revision_uuid",
            "proof.namespace_uuid=r.namespace_uuid",
            "proof.generation_artifact_uuid=r.generation_artifact_uuid",
            "proof.generation_artifact_type=r.generation_artifact_type",
            "proof.embedding_model_key=r.embedding_model_key",
            "proof.embedding_model_version=r.embedding_model_version",
            "proof.adapter_kind=r.adapter_kind",
            "proof.dimension=r.dimension",
            "proof.index_generation=r.index_generation",
            "proof.expected_count=proof.actual_count",
            "proof.actual_count=proof.matched_count",
            _PROOF_COMPLETE_SET_PREDICATE,
            "generation.artifact_type=r.generation_artifact_type",
            "generation.validation_disposition='full_valid'",
            "item.lifecycle_state='active'",  # S04 batch-eligibility native fence
            "item.deleted_at IS NULL",
            "item.serving_revision_uuid IS NOT NULL",
            "item.serving_revision_uuid=r.intake_revision_uuid",
        ]
        params: list[Any] = [query.team_uuid, namespace["namespace_uuid"]]

        if "intake_item_uuid" in query.filters:
            where.append("r.intake_item_uuid=?")
            params.append(query.filters["intake_item_uuid"])
        if "source_kind" in query.filters:
            where.append("source.source_kind=?")
            params.append(query.filters["source_kind"])
        channel = force_channel or query.filters.get("channel")
        if channel is not None:
            where.append("r.channel=?")
            params.append(channel)
        if coordinate_pairs:
            pair_terms = []
            for generation_artifact_uuid, unit_id in coordinate_pairs:
                pair_terms.append("(r.generation_artifact_uuid=? AND r.block_or_unit_id=?)")
                params.extend((generation_artifact_uuid, unit_id))
            where.append("(" + " OR ".join(pair_terms) + ")")
        if generation_artifact_ids:
            where.append("r.generation_artifact_uuid IN (" + ",".join("?" for _ in generation_artifact_ids) + ")")
            params.extend(generation_artifact_ids)

        sql = (
            """
            SELECT r.vector_record_uuid, r.team_uuid, r.namespace_uuid,
                   r.generation_artifact_uuid, r.generation_artifact_type,
                   r.block_or_unit_id, r.channel, r.intake_item_uuid,
                   r.intake_revision_uuid, r.source_handle, r.embedding,
                   r.dimension, r.content_digest, r.index_generation,
                   proof.proof_uuid AS publication_proof_uuid,
                   generation.logical_handle AS generation_logical_handle,
                   generation.validation_disposition AS generation_validation_disposition
            FROM mkb_vector_records AS r
            JOIN mkb_vector_namespaces AS n
              ON n.namespace_uuid=r.namespace_uuid AND n.team_uuid=r.team_uuid
            JOIN mkb_index_active_pointers AS p
              ON p.team_uuid=r.team_uuid AND p.intake_item_uuid=r.intake_item_uuid
             AND p.namespace_uuid=r.namespace_uuid
            JOIN mkb_publication_proofs AS proof
              ON proof.proof_uuid=p.last_proof_uuid
            JOIN mkb_intake_items AS item
              ON item.team_uuid=r.team_uuid AND item.intake_item_uuid=r.intake_item_uuid
            LEFT JOIN mkb_intake_sources AS source
              ON source.team_uuid=item.team_uuid AND source.intake_source_uuid=item.intake_source_uuid
            JOIN mkb_generation_artifacts AS generation
              ON generation.team_uuid=r.team_uuid
             AND generation.generation_artifact_uuid=r.generation_artifact_uuid
            WHERE """
            + " AND ".join(where)
            + " ORDER BY r.vector_record_uuid LIMIT ?"
        )
        params.append(self._candidate_scan_limit)
        return await tx.fetchall(sql, tuple(params))

    async def _rank_ann_candidates(
        self,
        query: _SearchInput,
        namespace: Mapping[str, Any],
        rows: Sequence[dict[str, Any]],
        query_embedding: list[float] | None,
    ) -> list[_Candidate]:
        scores: Mapping[str, float] | None = None
        # CI/offline deployments use the same explicit deterministic embedding
        # profile as vectorization.  Ranking opaque unit IDs/digests would make
        # the semantic release gate impossible to exercise without an external
        # inference service; this remains a vector comparison, not a body-text
        # shortcut around S09/S10's fences.
        if query_embedding is None and self._candidate_scorer is None:
            try:
                query_embedding = deterministic_embedding(query.query, dimension=int(namespace["dimension"]))
            except (TypeError, ValueError) as exc:
                raise MkbError("RETRIEVE_SPACE_LAYER_A_MISMATCH", "offline vector space is invalid", 503) from exc
        if query_embedding is None and self._candidate_scorer is not None:
            try:
                response = self._candidate_scorer(query=query.query, namespace=namespace, candidates=rows)
                scores = await response if inspect.isawaitable(response) else response
                if not isinstance(scores, Mapping):
                    raise TypeError("candidate scorer must return a score mapping")
            except Exception as exc:
                raise MkbError("RETRIEVE_DEPENDENCY_VECTOR", "candidate scorer is unavailable", 503) from exc
        candidates: list[_Candidate] = []
        invalid_vector_count = 0
        for row in rows:
            if query_embedding is not None:
                try:
                    score = self._embedding_score(
                        str(namespace["distance_metric"]),
                        query_embedding,
                        self._decode_embedding(row["embedding"], int(row["dimension"])),
                    )
                except (OverflowError, TypeError, ValueError, struct.error):
                    invalid_vector_count += 1
                    continue
            elif scores is not None:
                if str(row["vector_record_uuid"]) not in scores:
                    # A delegated ANN scorer returns its own candidate set; a
                    # missing ID is not a synthetic zero-score hit.
                    continue
                raw_score = scores[str(row["vector_record_uuid"])]
                score = self._as_finite_float(raw_score, "candidate score")
            else:
                score = self._token_similarity(query.query, self._candidate_search_text(row))
                # The deterministic local profile is a candidate scan rather
                # than a semantic model.  Treat no shared token as no ANN hit,
                # so unrelated queries remain machine-readable empty results.
                if score <= 0:
                    continue
            candidates.append(
                _Candidate(row=dict(row), ann_score=score, granularity=self._infer_granularity(row["block_or_unit_id"]))
            )
        if query_embedding is not None and rows and not candidates and invalid_vector_count:
            raise MkbError("RETRIEVE_DEPENDENCY_VECTOR_INVALID", "active vector records are malformed", 503)
        candidates.sort(key=lambda item: (-item.ann_score, item.vector_record_uuid))
        return candidates[: query.recall_k]

    @staticmethod
    def _decode_embedding(value: Any, dimension: int) -> list[float]:
        if isinstance(dimension, bool) or not isinstance(dimension, int) or dimension < 1:
            raise ValueError("invalid vector dimension")
        if isinstance(value, memoryview):
            value = value.tobytes()
        if isinstance(value, bytes | bytearray):
            if len(value) != dimension * 4:
                raise ValueError("invalid vector byte length")
            decoded = list(struct.unpack(f"<{dimension}f", value))
        elif isinstance(value, str):
            parsed = json.loads(value)
            if not isinstance(parsed, list) or len(parsed) != dimension:
                raise ValueError("invalid vector JSON")
            decoded = [float(item) for item in parsed]
        elif isinstance(value, Sequence):
            if len(value) != dimension:
                raise ValueError("invalid vector sequence")
            decoded = [float(item) for item in value]
        else:
            raise ValueError("unsupported vector representation")
        if not all(math.isfinite(item) for item in decoded):
            raise ValueError("vector has a non-finite component")
        return decoded

    @staticmethod
    def _embedding_score(metric: str, left: Sequence[float], right: Sequence[float]) -> float:
        """Return a finite, higher-is-better score for the frozen metric.

        ``l2`` is converted to inverse Euclidean distance so S10's common
        descending rank policy and default threshold of ``0.0`` remain valid
        without silently changing the namespace's metric to cosine.
        """

        if metric == "cosine":
            return RetrievalService._cosine(left, right)
        if len(left) != len(right):
            raise ValueError("embedding dimensions differ")
        if metric == "inner_product":
            score = math.fsum(a * b for a, b in zip(left, right, strict=True))
        elif metric == "l2":
            squared_distance = math.fsum((a - b) * (a - b) for a, b in zip(left, right, strict=True))
            if squared_distance < 0 or not math.isfinite(squared_distance):
                raise ValueError("invalid l2 distance")
            score = 1.0 / (1.0 + math.sqrt(squared_distance))
        else:
            raise ValueError("unsupported distance metric")
        if not math.isfinite(score):
            raise ValueError("invalid metric score")
        return score

    @staticmethod
    def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
        if len(left) != len(right):
            raise ValueError("embedding dimensions differ")
        dot = math.fsum(a * b for a, b in zip(left, right, strict=True))
        left_norm = math.sqrt(math.fsum(value * value for value in left))
        right_norm = math.sqrt(math.fsum(value * value for value in right))
        if not all(math.isfinite(value) for value in (dot, left_norm, right_norm)):
            raise ValueError("invalid cosine score")
        if left_norm == 0 or right_norm == 0:
            return 0.0
        score = dot / (left_norm * right_norm)
        if not math.isfinite(score):
            raise ValueError("invalid cosine score")
        return score

    @staticmethod
    def _candidate_search_text(row: Mapping[str, Any]) -> str:
        return " ".join(
            str(value)
            for value in (row.get("block_or_unit_id"), row.get("content_digest"), row.get("generation_artifact_type"))
            if value
        )

    @staticmethod
    def _token_similarity(query: str, candidate: str) -> float:
        query_tokens = set(token.casefold() for token in _TOKEN.findall(query))
        candidate_tokens = set(token.casefold() for token in _TOKEN.findall(candidate))
        if not query_tokens or not candidate_tokens:
            return 0.0
        overlap = len(query_tokens & candidate_tokens)
        if overlap == 0:
            return 0.0
        return overlap / math.sqrt(len(query_tokens) * len(candidate_tokens))

    async def _apply_batch_eligibility(
        self,
        query: _SearchInput,
        namespace: Mapping[str, Any],
        candidates: Sequence[_Candidate],
    ) -> list[_Candidate]:
        """Apply S04, then revalidate the complete current S09 predicate.

        These are deliberately separate checks.  S04 owns the current
        lifecycle/serving decision, while S09 owns the active index pointer and
        publication proof.  The second check closes the interval after the
        initial candidate scan: an eligibility adapter must not be able to
        accidentally re-admit a record that was withdrawn while it ran.
        """

        payload = [
            {
                "vector_record_uuid": candidate.vector_record_uuid,
                "intake_item_uuid": str(candidate.row["intake_item_uuid"]),
                "intake_revision_uuid": str(candidate.row["intake_revision_uuid"]),
            }
            for candidate in candidates
        ]
        if self._eligibility_port is not None:
            try:
                approved = await self._eligibility_port.filter_retrieval_eligible(
                    team_uuid=query.team_uuid, candidates=payload
                )
            except MkbError:
                raise
            except Exception as exc:
                raise MkbError(
                    "RETRIEVE_DEPENDENCY_ELIGIBILITY", "intake eligibility dependency is unavailable", 503
                ) from exc
        else:
            # Even the compact local profile makes the S04 eligibility stage a
            # separate batch fence after candidate ranking.  The candidate SQL
            # has already joined the same facts; this re-check closes the race
            # between candidate scan and hydrate without importing an S04
            # adapter or letting an ANN result bypass eligibility.
            approved = await self._sql_batch_eligibility(query.team_uuid, payload)
        approved_ids = {str(value) for value in approved}
        s04_eligible = [candidate for candidate in candidates if candidate.vector_record_uuid in approved_ids]
        return await self._revalidate_publication_fence(query, namespace, s04_eligible)

    async def _revalidate_publication_fence(
        self,
        query: _SearchInput,
        namespace: Mapping[str, Any],
        candidates: Sequence[_Candidate],
    ) -> list[_Candidate]:
        """Return only records still valid under the full S09+S04 read fence.

        The initial vector scan is necessarily a separate operation from the
        S04 port call.  Rechecking the *same exact submitted coordinates* here
        prevents a pointer/proof/record withdrawal during that gap from being
        returned as a grounded hit.  The query intentionally names every
        publication-valid fact rather than relying on an ANN result or a loose
        vector-record existence test.
        """

        if not candidates:
            return []
        requested = [
            (
                candidate.vector_record_uuid,
                str(candidate.row["intake_item_uuid"]),
                str(candidate.row["intake_revision_uuid"]),
            )
            for candidate in candidates
        ]
        placeholders = ",".join("(?,?,?)" for _ in requested)
        params: list[Any] = []
        for vector_record_uuid, intake_item_uuid, intake_revision_uuid in requested:
            params.extend((vector_record_uuid, intake_item_uuid, intake_revision_uuid))
        params.extend((query.team_uuid, str(namespace["namespace_uuid"])))
        sql = (
            "WITH requested(vector_record_uuid,intake_item_uuid,intake_revision_uuid) AS "
            f"(VALUES {placeholders}) "
            "SELECT DISTINCT r.vector_record_uuid "
            "FROM requested "
            "JOIN mkb_vector_records AS r "
            "  ON r.vector_record_uuid=requested.vector_record_uuid "
            " AND r.intake_item_uuid=requested.intake_item_uuid "
            " AND r.intake_revision_uuid=requested.intake_revision_uuid "
            "JOIN mkb_vector_namespaces AS n "
            "  ON n.namespace_uuid=r.namespace_uuid AND n.team_uuid=r.team_uuid "
            "JOIN mkb_index_active_pointers AS p "
            "  ON p.team_uuid=r.team_uuid AND p.intake_item_uuid=r.intake_item_uuid "
            " AND p.namespace_uuid=r.namespace_uuid "
            "JOIN mkb_publication_proofs AS proof ON proof.proof_uuid=p.last_proof_uuid "
            "JOIN mkb_intake_items AS item "
            "  ON item.team_uuid=r.team_uuid AND item.intake_item_uuid=r.intake_item_uuid "
            "JOIN mkb_generation_artifacts AS generation "
            "  ON generation.team_uuid=r.team_uuid "
            " AND generation.generation_artifact_uuid=r.generation_artifact_uuid "
            "WHERE r.team_uuid=? AND r.namespace_uuid=? "
            "  AND r.deleted_at IS NULL AND r.publication_state='indexed' "
            "  AND n.status='active' AND n.deleted_at IS NULL "
            "  AND r.embedding_model=n.embedding_model "
            "  AND r.embedding_model_key=n.embedding_model_key "
            "  AND r.embedding_model_version=n.embedding_model_version "
            "  AND r.adapter_kind=n.adapter_kind AND r.dimension=n.dimension "
            "  AND p.lifecycle_state='active' "
            "  AND p.active_index_generation=r.index_generation "
            "  AND p.generation_artifact_uuid=r.generation_artifact_uuid "
            "  AND p.last_proof_uuid IS NOT NULL "
            "  AND proof.proof_type='index.publication.v1' AND proof.proof_version='v1' "
            "  AND proof.team_uuid=r.team_uuid "
            "  AND proof.intake_item_uuid=r.intake_item_uuid "
            "  AND proof.intake_revision_uuid=r.intake_revision_uuid "
            "  AND proof.namespace_uuid=r.namespace_uuid "
            "  AND proof.generation_artifact_uuid=r.generation_artifact_uuid "
            "  AND proof.generation_artifact_type=r.generation_artifact_type "
            "  AND proof.embedding_model_key=r.embedding_model_key "
            "  AND proof.embedding_model_version=r.embedding_model_version "
            "  AND proof.adapter_kind=r.adapter_kind AND proof.dimension=r.dimension "
            "  AND proof.index_generation=r.index_generation "
            "  AND proof.expected_count=proof.actual_count "
            "  AND proof.actual_count=proof.matched_count "
            "  AND "
            + _PROOF_COMPLETE_SET_PREDICATE
            + " "
            "  AND generation.artifact_type=r.generation_artifact_type "
            "  AND generation.validation_disposition='full_valid' "
            "  AND item.lifecycle_state='active' AND item.deleted_at IS NULL "
            "  AND item.serving_revision_uuid IS NOT NULL "
            "  AND item.serving_revision_uuid=r.intake_revision_uuid"
        )
        try:
            async with self._persistence.transaction() as tx:
                rows = await tx.fetchall(sql, tuple(params))
        except MkbError:
            raise
        except Exception as exc:
            raise MkbError(
                "RETRIEVE_DEPENDENCY_VECTOR", "publication fence revalidation is unavailable", 503
            ) from exc
        approved = {str(row["vector_record_uuid"]) for row in rows}
        return [candidate for candidate in candidates if candidate.vector_record_uuid in approved]

    async def _sql_batch_eligibility(self, team_uuid: str, candidates: Sequence[Mapping[str, str]]) -> set[str]:
        if not candidates:
            return set()
        terms: list[str] = []
        params: list[str] = [team_uuid]
        for candidate in candidates:
            terms.append("(r.vector_record_uuid=? AND r.intake_item_uuid=? AND r.intake_revision_uuid=?)")
            params.extend(
                (
                    candidate["vector_record_uuid"],
                    candidate["intake_item_uuid"],
                    candidate["intake_revision_uuid"],
                )
            )
        sql = (
            """
            SELECT r.vector_record_uuid
            FROM mkb_vector_records AS r
            JOIN mkb_intake_items AS item
              ON item.team_uuid=r.team_uuid AND item.intake_item_uuid=r.intake_item_uuid
            WHERE r.team_uuid=?
              AND item.lifecycle_state='active'
              AND item.deleted_at IS NULL
              AND item.serving_revision_uuid IS NOT NULL
              AND item.serving_revision_uuid=r.intake_revision_uuid
              AND ("""
            + " OR ".join(terms)
            + ")"
        )
        try:
            async with self._persistence.transaction() as tx:
                rows = await tx.fetchall(sql, tuple(params))
        except Exception as exc:
            raise MkbError(
                "RETRIEVE_DEPENDENCY_ELIGIBILITY", "intake eligibility dependency is unavailable", 503
            ) from exc
        return {str(row["vector_record_uuid"]) for row in rows}

    async def _load_traceback_originals(
        self, query: _SearchInput, namespace: Mapping[str, Any], candidates: Sequence[_Candidate]
    ) -> dict[tuple[str, str], dict[str, Any]]:
        pairs = [
            (str(candidate.row["generation_artifact_uuid"]), str(candidate.row["block_or_unit_id"]))
            for candidate in candidates
            if candidate.row["channel"] == "summary"
        ]
        if not pairs:
            return {}
        try:
            async with self._persistence.transaction() as tx:
                rows = await self._fetch_candidate_rows(
                    tx,
                    namespace,
                    query,
                    coordinate_pairs=pairs,
                    force_channel="original",
                )
        except MkbError:
            raise
        except Exception as exc:
            raise MkbError("RETRIEVE_DEPENDENCY_VECTOR", "traceback query is unavailable", 503) from exc
        return {(str(row["generation_artifact_uuid"]), str(row["block_or_unit_id"])): row for row in rows}

    async def _to_result_work(
        self,
        query: _SearchInput,
        candidate: _Candidate,
        traceback_rows: Mapping[tuple[str, str], dict[str, Any]],
    ) -> _ResultWork:
        row = candidate.row
        hit_material = await self._load_material(query.team_uuid, row, str(row["channel"]))
        granularity = hit_material.granularity if hit_material.granularity is not None else candidate.granularity
        payload_material = hit_material
        traceback_status: str
        if row["channel"] == "original":
            traceback_status = "not_needed"
        else:
            original = traceback_rows.get((str(row["generation_artifact_uuid"]), str(row["block_or_unit_id"])))
            if original is None:
                traceback_status = "failed"
            else:
                original_material = await self._load_material(query.team_uuid, original, "original")
                # A fallback reference derived from a vector row is not an
                # authoritative original body.  Only a successful port
                # hydration may resolve a summary traceback.
                if original_material.hydrated and original_material.available:
                    payload_material = original_material
                    if original_material.granularity is not None:
                        granularity = original_material.granularity
                    traceback_status = "resolved"
                else:
                    traceback_status = "degraded"

        coordinate = GenerationScopedCoordinate(
            generation_artifact_uuid=str(row["generation_artifact_uuid"]),
            unit_id=str(row["block_or_unit_id"]),
            granularity=granularity,
            channel=str(row["channel"]),
        )
        generation_refs = RetrievalGenerationRefs(
            intake_item_uuid=str(row["intake_item_uuid"]),
            intake_revision_uuid=str(row["intake_revision_uuid"]),
            generation_artifact_uuid=str(row["generation_artifact_uuid"]),
            generation_artifact_type=str(row["generation_artifact_type"]),
            namespace_uuid=str(row["namespace_uuid"]),
            publication_proof_uuid=str(row["publication_proof_uuid"]),
        )
        result = RetrievalResult(
            score=float(candidate.ann_score),
            ann_score=float(candidate.ann_score),
            hit_channel=str(row["channel"]),
            hit_content=hit_material.content,
            hit_content_ref=hit_material.content_ref,
            payload_content=payload_material.content,
            payload_content_ref=payload_material.content_ref,
            coordinate=coordinate,
            granularity=granularity,
            generation_refs=generation_refs,
            traceback_status=traceback_status,  # type: ignore[arg-type]
            context_tier="document_root" if granularity == 0 else "focus_fragment",
            filters_echo=query.filters,
        )
        return _ResultWork(result=result, candidate=candidate)

    async def _load_material(self, team_uuid: str, row: Mapping[str, Any], channel: str) -> _Material:
        fallback_ref = self._safe_ref(row.get("source_handle")) or self._safe_ref(row.get("generation_logical_handle"))
        if self._body_port is None:
            return _Material(content=None, content_ref=fallback_ref, hydrated=False)
        kwargs = {
            "team_uuid": team_uuid,
            "generation_artifact_uuid": str(row["generation_artifact_uuid"]),
            "unit_id": str(row["block_or_unit_id"]),
            "channel": channel,
        }
        try:
            loader = getattr(self._body_port, "load_retrieval_body", self._body_port)
            raw = loader(**kwargs)
            raw = await raw if inspect.isawaitable(raw) else raw
        except MkbError:
            # Integrity, schema, and storage failures are hard S12 dependency
            # errors.  Only a genuine ``None`` channel miss may degrade one
            # summary traceback below.
            raise
        except Exception as exc:
            raise MkbError(
                "RETRIEVE_DEPENDENCY_BODY", "retrieval body dependency is unavailable", 503
            ) from exc
        if raw is None:
            return _Material(content=None, content_ref=fallback_ref, hydrated=False)
        try:
            if isinstance(raw, str):
                body = RetrievalBody(content=raw)
            elif isinstance(raw, RetrievalBody):
                body = raw
            else:
                body = RetrievalBody.model_validate(raw)
        except Exception as exc:
            raise MkbError(
                "RETRIEVE_BODY_DOCUMENT_INVALID", "retrieval body response is invalid", 503
            ) from exc
        content = self._redact_paths(body.content) if body.content is not None else None
        content_ref = self._safe_ref(body.content_ref) or fallback_ref
        return _Material(content=content, content_ref=content_ref, granularity=body.granularity, hydrated=True)

    @staticmethod
    def _safe_ref(value: Any) -> str | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            assert_safe_public_data(value)
        except ValueError:
            return None
        return value

    @staticmethod
    def _redact_paths(value: str) -> str:
        """Keep document text useful while not exposing host absolute paths."""

        return _ABSOLUTE_PATH_IN_TEXT.sub("[redacted-path]", value)

    @staticmethod
    def _infer_granularity(unit_id: Any) -> int:
        text = str(unit_id)
        for pattern in _GRANULARITY_PATTERNS:
            match = pattern.search(text)
            if match:
                return int(match.group(1))
        lowered = text.casefold()
        if any(token in lowered for token in ("root", "document", "full")):
            return 0
        if any(token in lowered for token in ("leaf", "sentence", "paragraph", "fragment")):
            return 2
        return 1

    async def _inflate_documents(
        self, query: _SearchInput, namespace: Mapping[str, Any], work: Sequence[_ResultWork]
    ) -> None:
        targets = list(
            dict.fromkeys(
                str(item.candidate.row["generation_artifact_uuid"]) for item in work if item.result.granularity != 0
            )
        )
        if not targets or self._inflation_max_roots == 0:
            return
        try:
            async with self._persistence.transaction() as tx:
                rows = await self._fetch_candidate_rows(
                    tx,
                    namespace,
                    query,
                    generation_artifact_ids=targets,
                    force_channel="original",
                )
        except Exception:
            # Inflation is a bounded enhancement.  A failure is observable per
            # result but does not invalidate a fence-qualified focus hit.
            for item in work:
                if item.result.granularity != 0:
                    item.result.inflation_status = "missing"
            return

        roots: dict[str, dict[str, Any]] = {}
        for row in rows:
            generation = str(row["generation_artifact_uuid"])
            if generation not in roots and self._infer_granularity(row["block_or_unit_id"]) == 0:
                roots[generation] = row

        attached_generations: set[str] = set()
        for item in work:
            if item.result.granularity == 0:
                continue
            generation = str(item.candidate.row["generation_artifact_uuid"])
            root = roots.get(generation)
            if root is None:
                item.result.inflation_status = "missing"
                continue
            if generation not in attached_generations and len(attached_generations) >= self._inflation_max_roots:
                item.result.inflation_status = "skipped"
                continue
            material = await self._load_material(query.team_uuid, root, "original")
            if not material.available:
                item.result.inflation_status = "missing"
                continue
            root_granularity = material.granularity
            if root_granularity is None:
                root_granularity = self._infer_granularity(root["block_or_unit_id"])
            if root_granularity != 0:
                # An artifact body that contradicts the g=0 vector coordinate
                # is not safe to pass off as document-level context.
                item.result.inflation_status = "missing"
                continue
            attached_generations.add(generation)
            item.result.inflation_root_coordinate = GenerationScopedCoordinate(
                generation_artifact_uuid=generation,
                unit_id=str(root["block_or_unit_id"]),
                granularity=0,
                channel="original",
            )
            content = material.content
            if content is not None and len(content) > self._inflation_per_root_max_chars:
                item.result.inflation_root_content = content[: self._inflation_per_root_max_chars]
                item.result.inflation_root_content_ref = material.content_ref
                item.result.inflation_status = "truncated"
            else:
                item.result.inflation_root_content = content
                item.result.inflation_root_content_ref = material.content_ref
                item.result.inflation_status = "attached"

    @staticmethod
    def _deduplicate(work: Sequence[_ResultWork]) -> list[_ResultWork]:
        selected: dict[tuple[str, str], _ResultWork] = {}
        for item in work:
            key = (item.result.coordinate.generation_artifact_uuid, item.result.coordinate.unit_id)
            existing = selected.get(key)
            if existing is None or RetrievalService._dedup_key(item) < RetrievalService._dedup_key(existing):
                selected[key] = item
        return sorted(selected.values(), key=lambda item: (-item.result.ann_score, item.candidate.vector_record_uuid))

    @staticmethod
    def _dedup_key(item: _ResultWork) -> tuple[int, float, str]:
        resolved_priority = 0 if item.result.traceback_status == "resolved" else 1
        return (resolved_priority, -item.result.ann_score, item.candidate.vector_record_uuid)

    async def _rerank(self, query: str, work: list[_ResultWork]) -> str:
        if not self._rerank_enabled:
            return "not_requested"
        if len(work) <= 1:
            return "skipped"
        if self._inference is None:
            # A configured/default-ON reranker that cannot be invoked is a
            # failure, not a small-pool skip.  Preserve ANN ordering below but
            # make the degradation visible to callers and operators.
            return "failed"
        documents = [item.result.payload_content for item in work]
        if any(document is None for document in documents):
            return "skipped"
        try:
            scores = await self._inference.rerank(query, [str(document) for document in documents])
            if len(scores) != len(work):
                raise ValueError("rerank cardinality mismatch")
            parsed = [self._as_finite_float(score, "rerank score") for score in scores]
        except Exception:
            # Preserve the already ANN-sorted sequence and ann_score exactly.
            return "failed"
        for item, score in zip(work, parsed, strict=True):
            item.result.rerank_score = score
            item.result.score = score
        work.sort(key=lambda item: (-item.result.score, item.candidate.vector_record_uuid))
        return "applied"

    def _pack(self, results: Sequence[RetrievalResult]) -> PackView:
        segments: list[PackSegment] = []
        text_parts: list[str] = []
        used_chars = 0
        included_hits = 0
        truncated = False
        for index, result in enumerate(results):
            if included_hits >= self._pack_max_hits:
                truncated = True
                break
            focus, focus_chars, focus_truncated = self._pack_segment(
                tier="document_root" if result.granularity == 0 else "focus_fragment",
                coordinate=result.coordinate,
                content=result.payload_content,
                content_ref=result.payload_content_ref,
                available_chars=self._pack_max_chars - used_chars,
            )
            if focus is None:
                truncated = True
                continue
            segments.append(focus)
            included_hits += 1
            used_chars += focus_chars
            if focus.content:
                text_parts.append(focus.content)
            truncated = truncated or focus_truncated
            if result.inflation_status in {"attached", "truncated"}:
                root_coordinate = result.inflation_root_coordinate
                if root_coordinate is None:
                    # A root without its own coordinate would create false
                    # provenance in the context pack.  Preserve the result,
                    # but make the omitted enhancement observable.
                    truncated = True
                    continue
                root, root_chars, root_truncated = self._pack_segment(
                    tier="document_root",
                    coordinate=root_coordinate,
                    content=result.inflation_root_content,
                    content_ref=result.inflation_root_content_ref,
                    available_chars=self._pack_max_chars - used_chars,
                )
                if root is None:
                    truncated = True
                else:
                    segments.append(root)
                    used_chars += root_chars
                    if root.content:
                        text_parts.append(root.content)
                    truncated = truncated or root_truncated
            if used_chars >= self._pack_max_chars and index + 1 < len(results):
                truncated = True
                break
        if included_hits < len(results):
            truncated = True
        return PackView(
            text="\n\n".join(text_parts) if text_parts else None,
            segments=segments,
            pack_hit_count=included_hits,
            pack_char_count=used_chars,
            truncated=truncated,
        )

    @staticmethod
    def _pack_segment(
        *,
        tier: str,
        coordinate: GenerationScopedCoordinate,
        content: str | None,
        content_ref: str | None,
        available_chars: int,
    ) -> tuple[PackSegment | None, int, bool]:
        if available_chars < 0:
            return None, 0, True
        if content is None:
            if content_ref is None:
                return None, 0, False
            return PackSegment(tier=tier, coordinate=coordinate, content_ref=content_ref), 0, False  # type: ignore[arg-type]
        if available_chars == 0:
            return None, 0, True
        included = content[:available_chars]
        return (
            PackSegment(tier=tier, coordinate=coordinate, content=included),  # type: ignore[arg-type]
            len(included),
            len(included) < len(content),
        )

    def _empty_bundle(
        self,
        query: _SearchInput,
        query_digest: str,
        reason: str,
        *,
        ann_hit_count: int = 0,
        filtered_count: int = 0,
    ) -> RetrievalBundle:
        pack = (
            PackView(text=None, segments=[], pack_hit_count=0, pack_char_count=0, truncated=False)
            if query.include_pack
            else None
        )
        return RetrievalBundle(
            disposition="empty",
            team_uuid=query.team_uuid,
            query_digest=query_digest,
            results=[],
            pack=pack,
            diagnostics=RetrievalDiagnostics(
                recall_k=query.recall_k,
                return_k=query.return_k,
                threshold_applied=query.threshold,
                ann_hit_count=ann_hit_count,
                eligible_count=0,
                filtered_count=filtered_count,
                rerank_status="skipped" if self._rerank_enabled else "not_requested",
                empty_reason=reason,  # type: ignore[arg-type]
                filters_echo=query.filters,
            ),
        )


# ``RetrievalSearchService`` is the descriptive S10 name; retain the shorter
# alias used by the composition root and route code.
RetrievalSearchService = RetrievalService


__all__ = ["CandidateScorer", "RetrievalSearchService", "RetrievalService"]
