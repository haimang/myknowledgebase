"""Internal-only operator read surfaces. No repair/write or debug file route."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.dependencies import require_operator_token

# Keep the router-level guard even while the bounded v1 operator surface is
# empty.  Any future read/repair endpoint therefore inherits token plus
# internal-network admission instead of accidentally becoming public.
router = APIRouter(prefix="/internal", tags=["internal"], dependencies=[Depends(require_operator_token)])
