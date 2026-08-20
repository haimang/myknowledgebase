"""Storage-backed S04/S10 read adapters.

``ArtifactRetrievalAccess`` is deliberately a persistence-side composition
root.  It owns the two read boundaries consumed by :mod:`src.services.retrieval`:

* S04's batch eligibility fence, evaluated from authoritative Intake rows;
* S10's immutable, generation-scoped dual-channel body hydration.

The adapter has no filesystem knowledge.  It receives an ``ObjectStorePort``
and dereferences only the artifact's opaque logical handle after first proving
that the generation belongs to the requested Team.  The on-disk object-store
adapter remains the only component that can resolve that handle to bytes.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping, Sequence
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest
from src.contracts.storage.models import ObjectHandle
from src.persistence.ports import IntakeEligibilityPort, PersistencePort, RetrievalBodyPort
from src.storage.ports import ObjectStorePort

DUAL_CHANNEL_PROJECTION_SCHEMA = "mkb.dual-channel-projection.v1"
_JSON_MEDIA_TYPES = frozenset({"application/json", "application/ld+json"})
_CHANNELS = frozenset({"original", "summary"})
_MAX_UNIT_ID_LENGTH = 512
_MAX_CHANNEL_CHARS = 8 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class _ProjectionUnit:
    unit_id: str
    granularity: int
    channels: Mapping[str, str]


_HYDRATION_CACHE: ContextVar[dict[tuple[str, str], dict[str, _ProjectionUnit]] | None] = ContextVar(
    "mkb_retrieval_hydration_cache", default=None
)


def begin_hydration_cache() -> Token[dict[tuple[str, str], dict[str, _ProjectionUnit]] | None]:
    return _HYDRATION_CACHE.set({})


def end_hydration_cache(token: Token[dict[tuple[str, str], dict[str, _ProjectionUnit]] | None]) -> None:
    _HYDRATION_CACHE.reset(token)


class ArtifactRetrievalAccess(IntakeEligibilityPort, RetrievalBodyPort):
    """Concrete, read-only adapter for S04 eligibility and S10 body hydration.

    The canonical bytes format for a ``dual_channel_projection`` artifact is
    intentionally small and deterministic::

        {
          "schema_version": "mkb.dual-channel-projection.v1",
          "generation_artifact_uuid": "<optional exact coordinate>",
          "units": [
            {
              "unit_id": "g1:revenue",
              "granularity": 1,
              "channels": {
                "original": {"content": "authoritative source text"},
                "summary": {"content": "retrieval summary"}
              }
            }
          ]
        }

    A channel may additionally carry a ``content_digest``.  When present it is
    verified against the UTF-8 content, making the artifact self-checking while
    retaining the generation artifact's outer S13 digest as the durable source
    of truth.

    The runtime also stores the projection inside its immutable
    ``mkb.stage-output.v1`` envelope.  For that compatibility form this adapter
    accepts only ``output.construct_package.dual_channel`` and requires the
    matching ``state.dual_channel_artifact_uuid``.  Its direct channel units
    use the current deterministic form ``original`` / ``summary`` plus their
    ``stable_digest({"text": ...})`` receipts.  The document intentionally
    embeds text rather than filesystem locations; callers receive text plus
    granularity and never a host path.
    """

    def __init__(
        self,
        persistence: PersistencePort,
        storage: ObjectStorePort,
        *,
        candidate_chunk_size: int = 200,
        max_artifact_bytes: int = 16 * 1024 * 1024,
    ) -> None:
        if candidate_chunk_size < 1:
            raise ValueError("candidate_chunk_size must be positive")
        if max_artifact_bytes < 1:
            raise ValueError("max_artifact_bytes must be positive")
        self._persistence = persistence
        self._storage = storage
        # 200 * three candidate parameters stays well under stock SQLite's
        # common 999-variable ceiling, while still being a genuine batch fence.
        self._candidate_chunk_size = min(candidate_chunk_size, 250)
        self._max_artifact_bytes = max_artifact_bytes

    @staticmethod
    def begin_request_cache() -> Token[dict[tuple[str, str], dict[str, _ProjectionUnit]] | None]:
        return begin_hydration_cache()

    @staticmethod
    def end_request_cache(token: Token[dict[tuple[str, str], dict[str, _ProjectionUnit]] | None]) -> None:
        end_hydration_cache(token)

    async def filter_retrieval_eligible(self, *, team_uuid: str, candidates: Sequence[Mapping[str, str]]) -> set[str]:
        """Return only candidates whose current S04 serving fence still holds.

        The candidate coordinate is checked as a tuple, not just by vector ID:
        a record must still be owned by ``team_uuid``, point at exactly the
        submitted Item/Revision pair, and that Item must be active with that
        revision as its current serving revision.  Repeated vector IDs with
        conflicting coordinates are rejected fail-closed before SQL.
        """

        requested = self._normalise_candidates(candidates)
        if not requested or not self._safe_identifier(team_uuid, max_length=128):
            return set()

        approved: set[str] = set()
        async with self._persistence.transaction() as tx:
            for start in range(0, len(requested), self._candidate_chunk_size):
                chunk = requested[start : start + self._candidate_chunk_size]
                placeholders = ",".join("(?,?,?)" for _ in chunk)
                params: list[str] = []
                for vector_record_uuid, intake_item_uuid, intake_revision_uuid in chunk:
                    params.extend((vector_record_uuid, intake_item_uuid, intake_revision_uuid))
                params.append(team_uuid)
                rows = await tx.fetchall(
                    "WITH requested(vector_record_uuid,intake_item_uuid,intake_revision_uuid) AS "
                    f"(VALUES {placeholders}) "
                    "SELECT DISTINCT record.vector_record_uuid "
                    "FROM requested "
                    "JOIN mkb_vector_records AS record "
                    "  ON record.vector_record_uuid=requested.vector_record_uuid "
                    " AND record.intake_item_uuid=requested.intake_item_uuid "
                    " AND record.intake_revision_uuid=requested.intake_revision_uuid "
                    "JOIN mkb_intake_items AS item "
                    "  ON item.team_uuid=record.team_uuid "
                    " AND item.intake_item_uuid=record.intake_item_uuid "
                    "WHERE record.team_uuid=? "
                    "  AND record.deleted_at IS NULL "
                    "  AND item.lifecycle_state='active' "
                    "  AND item.deleted_at IS NULL "
                    "  AND item.serving_revision_uuid IS NOT NULL "
                    "  AND item.serving_revision_uuid=record.intake_revision_uuid",
                    tuple(params),
                )
                approved.update(str(row["vector_record_uuid"]) for row in rows)
        return approved

    async def load_retrieval_body(
        self,
        *,
        team_uuid: str,
        generation_artifact_uuid: str,
        unit_id: str,
        channel: str,
    ) -> Mapping[str, Any] | None:
        """Hydrate a single generation-scoped channel from verified S13 bytes.

        ``None`` means the requested coordinate/channel is genuinely absent.
        Integrity, schema, and storage failures remain typed errors so S10 can
        fail closed; only a missing original channel may degrade one summary
        traceback without fabricating text.
        """

        if channel not in _CHANNELS or not self._safe_identifier(unit_id, max_length=_MAX_UNIT_ID_LENGTH):
            return None
        if not self._safe_identifier(team_uuid, max_length=128) or not self._safe_identifier(
            generation_artifact_uuid, max_length=128
        ):
            return None

        cache = _HYDRATION_CACHE.get()
        cache_key = (team_uuid, generation_artifact_uuid)
        units = None if cache is None else cache.get(cache_key)
        if units is None:
            async with self._persistence.transaction() as tx:
                artifact = await tx.fetchone(
                    "SELECT generation_artifact_uuid,logical_handle,media_type,size_bytes,content_digest "
                    "FROM mkb_generation_artifacts "
                    "WHERE team_uuid=? AND generation_artifact_uuid=? "
                    "  AND artifact_type='dual_channel_projection' "
                    "  AND validation_disposition='full_valid'",
                    (team_uuid, generation_artifact_uuid),
                )
            if artifact is None:
                # Do not reveal whether the same opaque generation exists in a
                # different Team.  S10 will retain its safe fallback ref instead.
                return None

            declared_size = self._as_declared_size(artifact.get("size_bytes"))
            if declared_size > self._max_artifact_bytes:
                raise MkbError("RETRIEVE_BODY_BUDGET", "Retrieval artifact exceeds the configured hydration budget", 422)
            media_type = str(artifact.get("media_type") or "").split(";", maxsplit=1)[0].strip().casefold()
            if media_type not in _JSON_MEDIA_TYPES and not media_type.endswith("+json"):
                raise MkbError("RETRIEVE_BODY_MEDIA_TYPE", "Retrieval artifact has an unsupported media type", 422)
            try:
                handle = ObjectHandle(value=str(artifact["logical_handle"]))
            except Exception as exc:
                raise MkbError("RETRIEVE_BODY_HANDLE_INVALID", "Retrieval artifact handle is invalid", 422) from exc

            # The object-store implementation enforces the Team encoded in the
            # logical handle and verifies its own content-addressed digest.  We
            # additionally compare with the immutable generation ledger so a bad
            # catalog row cannot cause a different valid object to be served.
            data = await self._storage.read_verified(team_uuid, handle)
            if len(data) != declared_size:
                raise MkbError("RETRIEVE_BODY_INTEGRITY", "Retrieval artifact size does not match its ledger", 503)
            actual_digest = hashlib.sha256(data).hexdigest()
            expected_digest = str(artifact.get("content_digest") or "")
            if not hmac.compare_digest(actual_digest, expected_digest):
                raise MkbError("RETRIEVE_BODY_INTEGRITY", "Retrieval artifact digest does not match its ledger", 503)

            units = self._parse_projection(
                data,
                expected_generation_artifact_uuid=generation_artifact_uuid,
            )
            if cache is not None:
                cache[cache_key] = units
        selected = units.get(unit_id)
        if selected is None:
            return None
        content = selected.channels.get(channel)
        if content is None:
            return None
        return {"content": content, "granularity": selected.granularity}

    @staticmethod
    def _safe_identifier(value: object, *, max_length: int) -> bool:
        return (
            isinstance(value, str)
            and bool(value)
            and len(value) <= max_length
            and "\x00" not in value
            and all(ord(character) >= 32 for character in value)
        )

    @classmethod
    def _normalise_candidates(cls, candidates: Sequence[Mapping[str, str]]) -> list[tuple[str, str, str]]:
        by_vector: dict[str, tuple[str, str]] = {}
        conflicted: set[str] = set()
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                continue
            vector_record_uuid = candidate.get("vector_record_uuid")
            intake_item_uuid = candidate.get("intake_item_uuid")
            intake_revision_uuid = candidate.get("intake_revision_uuid")
            if not all(
                cls._safe_identifier(value, max_length=512)
                for value in (vector_record_uuid, intake_item_uuid, intake_revision_uuid)
            ):
                continue
            assert isinstance(vector_record_uuid, str)
            assert isinstance(intake_item_uuid, str)
            assert isinstance(intake_revision_uuid, str)
            coordinate = (intake_item_uuid, intake_revision_uuid)
            prior = by_vector.get(vector_record_uuid)
            if prior is not None and prior != coordinate:
                by_vector.pop(vector_record_uuid, None)
                conflicted.add(vector_record_uuid)
            elif vector_record_uuid not in conflicted:
                by_vector[vector_record_uuid] = coordinate
        return [(record, item, revision) for record, (item, revision) in by_vector.items()]

    @staticmethod
    def _as_declared_size(value: object) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise MkbError("RETRIEVE_BODY_ARTIFACT_INVALID", "Retrieval artifact ledger is invalid", 503)
        return value

    def _parse_projection(self, data: bytes, *, expected_generation_artifact_uuid: str) -> dict[str, _ProjectionUnit]:
        if len(data) > self._max_artifact_bytes:
            raise MkbError("RETRIEVE_BODY_BUDGET", "Retrieval artifact exceeds the configured hydration budget", 422)
        try:
            decoded = data.decode("utf-8")
            document = json.loads(
                decoded,
                object_pairs_hook=self._reject_duplicate_keys,
                parse_constant=self._reject_non_finite_json,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise MkbError(
                "RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval artifact is not valid deterministic JSON", 422
            ) from exc
        projection = self._projection_from_document(document, expected_generation_artifact_uuid)
        declared_generation = projection.get("generation_artifact_uuid")
        if declared_generation is not None and declared_generation != expected_generation_artifact_uuid:
            raise MkbError(
                "RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval artifact generation coordinate does not match", 422
            )
        raw_units = projection.get("units")
        if not isinstance(raw_units, list):
            raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval artifact units are invalid", 422)

        parsed: dict[str, _ProjectionUnit] = {}
        direct_channels = "recipe_version" in projection
        for raw_unit in raw_units:
            unit = self._parse_direct_channel_unit(raw_unit) if direct_channels else self._parse_unit(raw_unit)
            if unit.unit_id in parsed:
                raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval artifact repeats a unit coordinate", 422)
            parsed[unit.unit_id] = unit
        return parsed

    def _projection_from_document(self, document: object, expected_generation_artifact_uuid: str) -> dict[str, Any]:
        if not isinstance(document, dict):
            raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval artifact has an invalid document shape", 422)
        schema_version = document.get("schema_version")
        if schema_version == DUAL_CHANNEL_PROJECTION_SCHEMA:
            allowed = {"schema_version", "generation_artifact_uuid", "units"}
            direct_allowed = allowed | {"recipe_version"}
            if set(document) - direct_allowed:
                raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval artifact has unknown document fields", 422)
            if "recipe_version" in document and document.get("recipe_version") != "content_full.v1":
                raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval artifact recipe is unsupported", 422)
            return document
        if schema_version != "mkb.stage-output.v1":
            raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval artifact schema version is unsupported", 422)
        # A generation artifact must point at the exact construct envelope that
        # produced it.  Do not scan arbitrary predecessor state or accept a
        # same-shaped projection from another stage/output port.
        if document.get("process_key") != "lsrag.construct":
            raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval artifact is not a construct stage output", 422)
        state = document.get("state")
        output = document.get("output")
        if not isinstance(state, dict) or not isinstance(output, dict):
            raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval stage envelope is invalid", 422)
        if state.get("dual_channel_artifact_uuid") != expected_generation_artifact_uuid:
            raise MkbError(
                "RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval stage envelope has the wrong artifact coordinate", 422
            )
        construct_package = output.get("construct_package")
        if not isinstance(construct_package, dict) or construct_package.get("content_full") is not True:
            raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval construct package is incomplete", 422)
        projection = construct_package.get("dual_channel")
        if not isinstance(projection, dict) or projection != state.get("dual_channel"):
            raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval construct package is inconsistent", 422)
        if projection.get("schema_version") != DUAL_CHANNEL_PROJECTION_SCHEMA:
            raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval construct projection is invalid", 422)
        return projection

    def _parse_unit(self, raw_unit: object) -> _ProjectionUnit:
        if not isinstance(raw_unit, dict) or set(raw_unit) != {"unit_id", "granularity", "channels"}:
            raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval artifact unit is invalid", 422)
        unit_id = raw_unit["unit_id"]
        granularity = raw_unit["granularity"]
        raw_channels = raw_unit["channels"]
        if not self._safe_identifier(unit_id, max_length=_MAX_UNIT_ID_LENGTH):
            raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval artifact unit identifier is invalid", 422)
        if isinstance(granularity, bool) or not isinstance(granularity, int) or granularity not in {0, 1, 2}:
            raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval artifact granularity is invalid", 422)
        if not isinstance(raw_channels, dict) or not raw_channels or set(raw_channels) - _CHANNELS:
            raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval artifact channels are invalid", 422)
        channels: dict[str, str] = {}
        for channel, raw_channel in raw_channels.items():
            channels[channel] = self._parse_channel(raw_channel)
        assert isinstance(unit_id, str)
        return _ProjectionUnit(unit_id=unit_id, granularity=granularity, channels=channels)

    def _parse_direct_channel_unit(self, raw_unit: object) -> _ProjectionUnit:
        """Parse the deterministic ``lsrag.construct`` direct-channel unit."""

        required = {
            "unit_id",
            "granularity",
            "original",
            "summary",
            "original_digest",
            "summary_digest",
        }
        if not isinstance(raw_unit, dict) or set(raw_unit) != required:
            raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval construct unit is invalid", 422)
        unit_id = raw_unit["unit_id"]
        granularity = raw_unit["granularity"]
        original = raw_unit["original"]
        summary = raw_unit["summary"]
        if not self._safe_identifier(unit_id, max_length=_MAX_UNIT_ID_LENGTH):
            raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval construct unit identifier is invalid", 422)
        if isinstance(granularity, bool) or not isinstance(granularity, int) or granularity not in {0, 1, 2}:
            raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval construct granularity is invalid", 422)
        if not isinstance(original, str) or not isinstance(summary, str):
            raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval construct channels are invalid", 422)
        if len(original) > _MAX_CHANNEL_CHARS or len(summary) > _MAX_CHANNEL_CHARS:
            raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval construct channel exceeds the body budget", 422)
        for content, digest_key in ((original, "original_digest"), (summary, "summary_digest")):
            expected_digest = raw_unit[digest_key]
            if not isinstance(expected_digest, str) or len(expected_digest) != 64:
                raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval construct channel digest is invalid", 422)
            if not hmac.compare_digest(stable_digest({"text": content}), expected_digest):
                raise MkbError("RETRIEVE_BODY_INTEGRITY", "Retrieval construct channel digest does not match", 503)
        assert isinstance(unit_id, str)
        return _ProjectionUnit(
            unit_id=unit_id,
            granularity=granularity,
            channels={"original": original, "summary": summary},
        )

    @staticmethod
    def _parse_channel(raw_channel: object) -> str:
        if not isinstance(raw_channel, dict) or set(raw_channel) - {"content", "content_digest"}:
            raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval artifact channel is invalid", 422)
        content = raw_channel.get("content")
        if not isinstance(content, str) or len(content) > _MAX_CHANNEL_CHARS:
            raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval artifact channel content is invalid", 422)
        expected_digest = raw_channel.get("content_digest")
        if expected_digest is not None:
            if not isinstance(expected_digest, str) or len(expected_digest) != 64:
                raise MkbError("RETRIEVE_BODY_DOCUMENT_INVALID", "Retrieval artifact channel digest is invalid", 422)
            actual_digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if not hmac.compare_digest(actual_digest, expected_digest):
                raise MkbError("RETRIEVE_BODY_INTEGRITY", "Retrieval artifact channel digest does not match", 503)
        return content

    @staticmethod
    def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    @staticmethod
    def _reject_non_finite_json(value: str) -> None:
        raise ValueError(f"non-finite JSON constant: {value}")


__all__ = [
    "ArtifactRetrievalAccess",
    "DUAL_CHANNEL_PROJECTION_SCHEMA",
    "begin_hydration_cache",
    "end_hydration_cache",
]
