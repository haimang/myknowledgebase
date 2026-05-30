from sqlite3 import Connection

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from smind_api.deps import AuthContext, get_auth_context, get_core_conn, make_team_service

router = APIRouter(prefix="/team", tags=["team"])


class BootstrapBody(BaseModel):
    name: str
    slug: str


class SelectBody(BaseModel):
    team_id: str


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
