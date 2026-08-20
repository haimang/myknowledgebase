"""Candidate fetch, ANN/token rank, eligibility, and publication fence."""

from __future__ import annotations

import inspect
import json
import math
import struct
from collections.abc import Mapping, Sequence
from typing import Any

from src.contracts.common.errors import MkbError
from src.persistence.ports import UnitOfWork
from src.services.deterministic_embedding import deterministic_embedding
from src.services.retrieval.models import (
    _PROOF_COMPLETE_SET_PREDICATE,
    _TOKEN,
    _Candidate,
    _SearchInput,
)


class RetrievalRankMixin:
    """Candidate fetch, ANN/token rank, eligibility, and publication fence."""

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
        params.append(self._candidate_scan_limit + 1)
        rows = await tx.fetchall(sql, tuple(params))
        if len(rows) > self._candidate_scan_limit:
            raise MkbError(
                "RETRIEVE_SCAN_TRUNCATED",
                "Retrieval candidate scan exceeded the bounded UUID scan limit",
                503,
            )
        return rows

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
            adapter = str(namespace.get("adapter_kind") or "")
            live = bool(getattr(self, "_live_inference", False))
            if not live and adapter in {"local_vllm", "remote_gemini"}:
                raise MkbError(
                    "RETRIEVE_SPACE_LAYER_A_MISMATCH",
                    "Live namespace ranking requires a live query embedding",
                    409,
                )
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
            return RetrievalRankMixin._cosine(left, right)
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
