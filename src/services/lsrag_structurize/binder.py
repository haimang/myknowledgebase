"""Pure S06 structurize input binding.  No I/O."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from src.contracts.common.errors import MkbError


@dataclass(frozen=True, slots=True)
class StructurizeBinding:
    clean_text: str
    clean_artifact_uuid: str
    clean_digest: str
    layered_candidate: Mapping[str, object]
    granularity_set: tuple[int, ...]
    structure_artifact_uuid: str
    projection_artifact_uuid: str


def _fail(code: str, message: str, status: int = 422) -> None:
    raise MkbError(code, message, status)


def bind_structurize(
    *,
    clean_text: str,
    clean_artifact_uuid: str,
    clean_digest: str,
    layered_candidate: Mapping[str, object] | None,
    granularity_set: tuple[int, ...] | list[int] | None,
    structure_artifact_uuid: str,
    projection_artifact_uuid: str,
) -> StructurizeBinding:
    """Fail-closed bind of already-read structurize primitives."""

    if not isinstance(clean_text, str) or not clean_text.strip():
        _fail("STRUCTURE_KERNEL_EMPTY", "A structure document requires non-empty clean text")
    if not isinstance(clean_artifact_uuid, str) or not clean_artifact_uuid:
        _fail("STRUCTURE_BINDING_INVALID", "Generation and clean artifact identities are required")
    if not isinstance(structure_artifact_uuid, str) or not structure_artifact_uuid:
        _fail("STRUCTURE_BINDING_INVALID", "Generation and clean artifact identities are required")
    if not isinstance(projection_artifact_uuid, str) or not projection_artifact_uuid:
        _fail("STRUCTURE_BINDING_INVALID", "Generation and clean artifact identities are required")
    if structure_artifact_uuid == projection_artifact_uuid:
        _fail("STRUCTURE_BINDING_INVALID", "Structure and projection artifact identities must be distinct")
    if not isinstance(clean_digest, str) or not clean_digest:
        _fail("STRUCTURE_BINDING_CLEAN_DIGEST", "The selected clean artifact digest does not match its bytes")
    if not isinstance(layered_candidate, Mapping):
        _fail("STRUCTURE_CANDIDATE_MISSING", "Accepted layered JSON candidate is unavailable", 409)
    if not isinstance(granularity_set, list | tuple) or not granularity_set:
        _fail("STRUCTURE_PROFILE_INVALID", "Layered granularity profile is unavailable", 409)
    profile = tuple(sorted(set(granularity_set)))
    if any(isinstance(value, bool) or not isinstance(value, int) or value not in {0, 1, 2} for value in profile) or 0 not in profile:
        _fail("STRUCTURE_PROFILE_INVALID", "Layered granularity profile is invalid", 409)
    return StructurizeBinding(
        clean_text=clean_text,
        clean_artifact_uuid=clean_artifact_uuid,
        clean_digest=clean_digest,
        layered_candidate=layered_candidate,
        granularity_set=profile,
        structure_artifact_uuid=structure_artifact_uuid,
        projection_artifact_uuid=projection_artifact_uuid,
    )
