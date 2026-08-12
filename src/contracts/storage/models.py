"""Logical object handles only; public/domain code never receives disk paths."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from src.contracts.common.models import PayloadExtraModel, StrictModel


class ObjectHandle(StrictModel):
    value: Annotated[str, Field(pattern=r"^mkbobj:v1:[a-zA-Z0-9._:-]+$")]


class PromoteRequest(PayloadExtraModel):
    team_uuid: str
    purpose: Literal[
        "intake_snapshot_artifact",
        "intake_revision_artifact",
        "clean_candidate",
        "gate_evidence",
        "generation_artifact",
        "process_io",
        "operator_hold",
        "backup_hold",
    ]
    media_type: Annotated[str | None, Field(max_length=255)] = None
    expected_sha256: Annotated[str | None, Field(pattern=r"^[0-9a-f]{64}$")] = None


class ObjectStat(StrictModel):
    handle: ObjectHandle
    sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    size_bytes: Annotated[int, Field(ge=0)]
    media_type: str | None = None
