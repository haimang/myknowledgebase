"""Internal-only operator read surfaces. No repair/write or debug file route."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/internal", tags=["internal"])
