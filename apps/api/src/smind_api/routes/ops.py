from sqlite3 import Connection

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from smind_api.deps import (
    AuthContext,
    get_auth_context,
    get_core_conn,
    get_vec_conn,
    make_management_service,
    require_team,
)

router = APIRouter(prefix="/ops", tags=["ops"])


class RestartBody(BaseModel):
    workflow_run_id: str
    mode: str = "recovery"


class PurgeBody(BaseModel):
    document_id: str


@router.get("/health")
def health(
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
    vec_conn: Connection = Depends(get_vec_conn),
) -> dict:
    team_id = require_team(ctx)
    return {"item": make_management_service(conn, vec_conn).health(team_id)}


@router.get("/claims")
def claims(
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
    vec_conn: Connection = Depends(get_vec_conn),
) -> dict:
    team_id = require_team(ctx)
    rows = make_management_service(conn, vec_conn).list_active_claims(team_id)
    return {"items": [dict(row) for row in rows]}


@router.get("/restarts")
def restart_backlog(
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
    vec_conn: Connection = Depends(get_vec_conn),
) -> dict:
    team_id = require_team(ctx)
    rows = make_management_service(conn, vec_conn).list_restart_backlog(team_id)
    return {"items": [dict(row) for row in rows]}


@router.post("/restarts")
def restart(
    body: RestartBody,
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
    vec_conn: Connection = Depends(get_vec_conn),
) -> dict:
    team_id = require_team(ctx)
    request_id = make_management_service(conn, vec_conn).restart_workflow(
        team_id=team_id, workflow_run_id=body.workflow_run_id, mode=body.mode
    )
    return {"request_id": request_id}


@router.get("/purges")
def purge_backlog(
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
    vec_conn: Connection = Depends(get_vec_conn),
) -> dict:
    team_id = require_team(ctx)
    rows = make_management_service(conn, vec_conn).list_purge_backlog(team_id)
    return {"items": [dict(row) for row in rows]}


@router.post("/purges")
def purge(
    body: PurgeBody,
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
    vec_conn: Connection = Depends(get_vec_conn),
) -> dict:
    team_id = require_team(ctx)
    request_id = make_management_service(conn, vec_conn).purge_document(
        team_id=team_id,
        document_id=body.document_id,
    )
    return {"request_id": request_id}
