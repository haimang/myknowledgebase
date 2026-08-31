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


class PublicObjectUploadView(PublicObjectView):
    """Upload response extension; stat remains the historical closed view."""

    session_token: Annotated[str, Field(pattern=r"^mkbsession:v1:[-A-Za-z0-9._~:]{16,512}$")] | None = None


class ObjectCancelRequest(StrictModel):
    handle: Annotated[str, Field(pattern=r"^mkbobj:v1:[a-zA-Z0-9._:-]+$")]
    session_token: Annotated[str, Field(pattern=r"^mkbsession:v1:[-A-Za-z0-9._~:]{16,512}$")] | None = None


__all__ = ["ObjectCancelRequest", "PublicObjectUploadView", "PublicObjectView"]
