from sqlite3 import Connection

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from smind_api.deps import (
    AuthContext,
    get_auth_context,
    get_core_conn,
    make_ingestion_service,
    require_team,
)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


class FileInitiateBody(BaseModel):
    filename: str
    mime_type: str = "text/plain"


class FileConfirmBody(BaseModel):
    upload_id: str
    title: str
    content: str


class UrlSubmitBody(BaseModel):
    url: str
    title: str


class ApiSubmitBody(BaseModel):
    external_ref: str
    title: str
    payload: dict


class StaticConfirmBody(BaseModel):
    upload_id: str
    path: str
    content: str
    role: str = "uploaded"


@router.post("/file/initiate")
def file_initiate(
    body: FileInitiateBody,
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
) -> dict:
    team_id = require_team(ctx)
    return make_ingestion_service(conn).file_initiate(
        team_id=team_id,
        user_id=ctx.user_id,
        filename=body.filename,
        mime_type=body.mime_type,
    )


@router.post("/file/confirm")
def file_confirm(
    body: FileConfirmBody,
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
) -> dict:
    team_id = require_team(ctx)
    return make_ingestion_service(conn).file_confirm(
        team_id=team_id,
        upload_id=body.upload_id,
        title=body.title,
        content=body.content,
    )


@router.post("/url/submit")
def url_submit(
    body: UrlSubmitBody,
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
) -> dict:
    team_id = require_team(ctx)
    return make_ingestion_service(conn).url_submit(team_id=team_id, url=body.url, title=body.title)


@router.post("/api/submit")
def api_submit(
    body: ApiSubmitBody,
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
) -> dict:
    team_id = require_team(ctx)
    return make_ingestion_service(conn).api_submit(
        team_id=team_id,
        external_ref=body.external_ref,
        title=body.title,
        payload=body.payload,
    )


@router.post("/static/initiate")
def static_initiate(
    body: FileInitiateBody,
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
) -> dict:
    team_id = require_team(ctx)
    return make_ingestion_service(conn).static_initiate(
        team_id=team_id,
        user_id=ctx.user_id,
        filename=body.filename,
        mime_type=body.mime_type,
    )


@router.post("/static/confirm")
def static_confirm(
    body: StaticConfirmBody,
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
) -> dict:
    team_id = require_team(ctx)
    return make_ingestion_service(conn).static_confirm(
        team_id=team_id,
        upload_id=body.upload_id,
        path=body.path,
        content=body.content,
        role=body.role,
    )
