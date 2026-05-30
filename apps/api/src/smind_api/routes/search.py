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

router = APIRouter(prefix="/search", tags=["search"])


class SearchBody(BaseModel):
    query: str
    limit: int = 6


@router.post("")
def search(
    body: SearchBody,
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
    vec_conn: Connection = Depends(get_vec_conn),
) -> dict:
    team_id = require_team(ctx)
    items = make_management_service(conn, vec_conn).search(
        team_id=team_id,
        query=body.query,
        limit=body.limit,
    )
    return {"items": items}


@router.post("/debug")
def search_debug(
    body: SearchBody,
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
    vec_conn: Connection = Depends(get_vec_conn),
) -> dict:
    team_id = require_team(ctx)
    return make_management_service(conn, vec_conn).search_debug(
        team_id=team_id,
        query=body.query,
        limit=body.limit,
    )
