"""Request normalisation, namespace resolve, and embed query."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Callable, Mapping
from typing import Any

from src.contracts.api.models import RetrievalRequest
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import validate_external_uuid
from src.contracts.common.models import assert_safe_public_data
from src.contracts.inference.models import EmbeddingRequest, InferenceBinding
from src.contracts.vector.models import (
    PackView,
    RetrievalBundle,
    RetrievalDiagnostics,
)
from src.persistence.ports import IntakeEligibilityPort, PersistencePort, RetrievalBodyPort, UnitOfWork
from src.runtime.inference.facade import InferenceFacade
from src.services.retrieval.models import (
    _DISTANCE_METRICS,
    _FILTER_KEYS,
    _FORBIDDEN_REQUEST_KEYS,
    _REQUEST_KEYS,
    _SOURCE_KINDS,
    CandidateScorer,
    _SearchInput,
)


class RetrievalRequestMixin:
    """Request normalisation, namespace resolve, and embed query."""

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
        body_port = getattr(self, "_body_port", None)
        begin_cache = getattr(body_port, "begin_request_cache", None) if body_port is not None else None
        end_cache = getattr(body_port, "end_request_cache", None) if body_port is not None else None
        cache_token = begin_cache() if callable(begin_cache) else None
        try:
            return await self._search_with_query(query, query_digest)
        finally:
            if cache_token is not None and callable(end_cache):
                end_cache(cache_token)

    async def _search_with_query(self, query: _SearchInput, query_digest: str) -> dict[str, Any]:
        try:
            async with self._persistence.transaction() as tx:
                team = await tx.fetchone(
                    "SELECT status, deleted_at FROM mkb_teams WHERE team_uuid=?",
                    (query.team_uuid,),
                )
                if team is not None and (team["status"] != "active" or team["deleted_at"] is not None):
                    raise MkbError("RETRIEVE_TEAM_INACTIVE", "Team is not active for retrieval", 409)
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
            raise MkbError(
                "RETRIEVE_SCHEMA_NAMESPACE_REQUIRED",
                "retrieval requires namespace_key or namespace_uuid; default is not a Layer-A space",
                422,
            )
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
                EmbeddingRequest(
                    team_uuid=query.team_uuid,
                    binding=binding,
                    texts=[query.query],
                    expected_dimension=int(namespace["dimension"]),
                )
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
