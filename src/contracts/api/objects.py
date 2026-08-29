"""Closed public object upload/stat projections; never raw bytes or paths."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from src.contracts.common.models import StrictModel


class PublicObjectView(StrictModel):
    handle: Annotated[str, Field(pattern=r"^mkbobj:v1:[a-zA-Z0-9._:-]+$")]
    digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    size_bytes: Annotated[int, Field(ge=0)]
    media_type: Annotated[str | None, Field(max_length=255)] = None
    disposition: Literal["pending", "ingested", "expired", "tombstoned"]


class ObjectCancelRequest(StrictModel):
    handle: Annotated[str, Field(pattern=r"^mkbobj:v1:[a-zA-Z0-9._:-]+$")]


__all__ = ["ObjectCancelRequest", "PublicObjectView"]
