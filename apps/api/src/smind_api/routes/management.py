from sqlite3 import Connection

from fastapi import APIRouter, Depends, HTTPException

from smind_api.deps import (
    AuthContext,
    get_auth_context,
    get_core_conn,
    get_vec_conn,
    make_management_service,
    require_team,
)

router = APIRouter(prefix="/management", tags=["management"])


@router.get("/workflows")
def list_workflows(
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
    vec_conn: Connection = Depends(get_vec_conn),
) -> dict:
    team_id = require_team(ctx)
    rows = make_management_service(conn, vec_conn).list_workflows(team_id)
    return {"items": [dict(r) for r in rows]}


@router.get("/workflows/{workflow_run_id}")
def get_workflow(
    workflow_run_id: str,
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
    vec_conn: Connection = Depends(get_vec_conn),
) -> dict:
    team_id = require_team(ctx)
    row = make_management_service(conn, vec_conn).get_workflow(team_id, workflow_run_id)
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    return {"item": dict(row)}


@router.get("/documents")
def list_documents(
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
    vec_conn: Connection = Depends(get_vec_conn),
) -> dict:
    team_id = require_team(ctx)
    rows = make_management_service(conn, vec_conn).list_documents(team_id)
    return {"items": [dict(r) for r in rows]}


@router.get("/documents/{document_id}")
def get_document(
    document_id: str,
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
    vec_conn: Connection = Depends(get_vec_conn),
) -> dict:
    team_id = require_team(ctx)
    row = make_management_service(conn, vec_conn).get_document(team_id, document_id)
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    return {"item": dict(row)}


@router.get("/static-files")
def list_static_files(
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
    vec_conn: Connection = Depends(get_vec_conn),
) -> dict:
    team_id = require_team(ctx)
    rows = make_management_service(conn, vec_conn).list_static_files(team_id)
    return {"items": [dict(r) for r in rows]}


@router.get("/static-files/{static_file_id}")
def get_static_file(
    static_file_id: str,
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
    vec_conn: Connection = Depends(get_vec_conn),
) -> dict:
    team_id = require_team(ctx)
    row = make_management_service(conn, vec_conn).get_static_file(team_id, static_file_id)
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    return {"item": dict(row)}
