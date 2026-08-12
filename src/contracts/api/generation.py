"""Strict, Task-scoped public projections for immutable generation artifacts.

The generation ledger is intentionally richer than this contract.  Runtime
execution/process identities, storage object IDs, fences, and repair payloads
never cross this boundary; callers receive only immutable references, digests,
and bounded task-relative metadata.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from src.contracts.common.models import StrictModel

GenerationArtifactType = Literal[
    "structure_document",
    "retrieval_block_projection",
    "structure_validation_report",
    "construction_document",
    "dual_channel_projection",
    "construction_validation_report",
]
GenerationValidationDisposition = Literal["full_valid", "invalid", "partial_rejected"]


class GenerationArtifactView(StrictModel):
    """Safe immutable artifact history visible through a Task route."""

    generation_artifact_uuid: str
    artifact_type: GenerationArtifactType
    artifact_ordinal: int = Field(ge=0)
    task_generation: int = Field(ge=1)
    intake_item_uuid: str | None = None
    intake_revision_uuid: str | None = None
    clean_artifact_uuid: str | None = None
    clean_artifact_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    schema_key: str | None = None
    schema_version: str | None = None
    schema_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    profile_key: str | None = None
    profile_version: str | None = None
    profile_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    model_key: str | None = None
    model_version: str | None = None
    prompt_key: str | None = None
    prompt_version: str | None = None
    prompt_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    logical_handle: str = Field(pattern=r"^mkbobj:v1:[a-zA-Z0-9._:-]+$", max_length=4096)
    media_type: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(ge=0)
    digest_algorithm: Literal["sha256"]
    content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    validation_disposition: GenerationValidationDisposition
    validation_report_ref: str | None = Field(default=None, max_length=4096)
    validation_report_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    proof_ref: str | None = Field(default=None, max_length=4096)
    proof_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    predecessor_generation_artifact_uuid: str | None = None
    created_at: str
    links: dict[str, str]


class GenerationArtifactPointerView(StrictModel):
    """Current, full-valid pointer without its internal Execution identity."""

    task_generation: int = Field(ge=1)
    artifact_type: GenerationArtifactType
    current_generation_artifact_uuid: str
    pointer_revision: int = Field(ge=0)
    updated_at: str
    intake_item_uuid: str | None = None
    intake_revision_uuid: str | None = None
    content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    validation_disposition: Literal["full_valid"]
    links: dict[str, str]


class GenerationArtifactPage(StrictModel):
    items: list[GenerationArtifactView]
    next_cursor: str | None = None


class GenerationArtifactPointerPage(StrictModel):
    items: list[GenerationArtifactPointerView]
    next_cursor: str | None = None
