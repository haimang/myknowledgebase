from sqlite3 import Connection

from auth import AuthService
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from smind_api.deps import (
    AuthContext,
    get_auth_context,
    get_core_conn,
    make_team_service,
    require_team,
)

router = APIRouter(prefix="/team", tags=["team"])


class BootstrapBody(BaseModel):
    name: str
    slug: str


class SelectBody(BaseModel):
    team_id: str


class ApiKeyBody(BaseModel):
    name: str
    expires_at: str | None = None


@router.post("/bootstrap")
def bootstrap_team(
    body: BootstrapBody,
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
) -> dict:
    service = make_team_service(conn)
    team_id = service.bootstrap(ctx.user_id, body.name, body.slug)
    service.select_team(ctx.session_id, team_id)
    return {"team_id": team_id}


@router.get("/list")
def list_teams(
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
) -> dict:
    rows = make_team_service(conn).list_memberships(ctx.user_id)
    return {"items": [dict(r) for r in rows]}


@router.post("/select")
def select_team(
    body: SelectBody,
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
) -> dict:
    service = make_team_service(conn)
    if not service.is_member(ctx.user_id, body.team_id):
        raise HTTPException(status_code=403, detail="team_membership_required")
    service.select_team(ctx.session_id, body.team_id)
    return {"team_id": body.team_id}


@router.post("/api-keys")
def create_api_key(
    body: ApiKeyBody,
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
) -> dict:
    # F6-07 P2-05: 仅 team owner 可创建; 明文 key 仅一次性返回。
    team_id = require_team(ctx)
    if not make_team_service(conn).is_owner(ctx.user_id, team_id):
        raise HTTPException(status_code=403, detail="owner_role_required")
    result = AuthService(conn).create_api_key(
        team_id=team_id,
        name=body.name,
        created_by_user_id=ctx.user_id,
        expires_at=body.expires_at,
    )
    return result
