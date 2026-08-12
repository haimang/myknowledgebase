"""Internal-only, token-and-network guarded observability reads."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from api.dependencies import OperatorToken, require_operator_token
from src.contracts.common.ids import validate_external_uuid

# Keep the router-level guard even while the bounded v1 operator surface is
# empty.  Any future read/repair endpoint therefore inherits token plus
# internal-network admission instead of accidentally becoming public.
router = APIRouter(prefix="/internal", tags=["internal"], dependencies=[Depends(require_operator_token)])


@router.get("/teams/{team_uuid}/traces/{trace_uuid}/timeline")
async def timeline_by_trace(
    request: Request,
    team_uuid: str,
    trace_uuid: str,
    token: OperatorToken,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    """Read redacted, bounded event evidence; never mutate a workflow."""

    del token
    items, next_cursor = await request.app.state.container.observability.timeline_by_trace(
        validate_external_uuid(team_uuid, field="team_uuid"),
        validate_external_uuid(trace_uuid, field="trace_uuid"),
        limit=limit,
        cursor=cursor,
    )
    return {"items": items, "next_cursor": next_cursor}


@router.get("/teams/{team_uuid}/tasks/{task_uuid}/timeline")
async def timeline_by_task(
    request: Request,
    team_uuid: str,
    task_uuid: str,
    token: OperatorToken,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    del token
    items, next_cursor = await request.app.state.container.observability.timeline_by_task(
        validate_external_uuid(team_uuid, field="team_uuid"),
        validate_external_uuid(task_uuid, field="task_uuid"),
        limit=limit,
        cursor=cursor,
    )
    return {"items": items, "next_cursor": next_cursor}


@router.get("/teams/{team_uuid}/outbox/dead")
async def dead_outbox(
    request: Request,
    team_uuid: str,
    token: OperatorToken,
    kind: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    del token
    items, next_cursor = await request.app.state.container.observability.dead_outbox(
        validate_external_uuid(team_uuid, field="team_uuid"), kind=kind, limit=limit, cursor=cursor
    )
    return {"items": items, "next_cursor": next_cursor}


@router.get("/teams/{team_uuid}/security-audit")
async def security_audit(
    request: Request,
    team_uuid: str,
    token: OperatorToken,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    del token
    items, next_cursor = await request.app.state.container.observability.security_audit(
        validate_external_uuid(team_uuid, field="team_uuid"), limit=limit, cursor=cursor
    )
    return {"items": items, "next_cursor": next_cursor}
