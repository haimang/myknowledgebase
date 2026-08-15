"""Traceback inflate, pack view, rerank fallback, and result material."""

from __future__ import annotations

import inspect
from collections.abc import Mapping, Sequence
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.models import assert_safe_public_data
from src.contracts.vector.models import (
    GenerationScopedCoordinate,
    PackSegment,
    PackView,
    RetrievalBody,
    RetrievalGenerationRefs,
    RetrievalResult,
)
from src.services.retrieval.models import (
    _ABSOLUTE_PATH_IN_TEXT,
    _GRANULARITY_PATTERNS,
    _Candidate,
    _Material,
    _ResultWork,
    _SearchInput,
)


class RetrievalPackMixin:
    """Traceback inflate, pack view, rerank fallback, and result material."""

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
            # T-O-352: g0 original is construct-only. Hydrate original from the
            # dual-channel artifact at the same coordinate; do not require an
            # original vector row.
            original_material = await self._load_material(query.team_uuid, row, "original")
            original_vector = traceback_rows.get((str(row["generation_artifact_uuid"]), str(row["block_or_unit_id"])))
            if original_material.hydrated and original_material.available:
                payload_material = original_material
                if original_material.granularity is not None:
                    granularity = original_material.granularity
                traceback_status = "resolved"
            elif original_vector is not None:
                traceback_status = "degraded"
            else:
                traceback_status = "failed"

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
            if existing is None or RetrievalPackMixin._dedup_key(item) < RetrievalPackMixin._dedup_key(existing):
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
