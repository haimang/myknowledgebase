from sqlite3 import Connection

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from smind_api.deps import AuthContext, get_auth_context, get_core_conn

router = APIRouter(prefix="/me", tags=["me"])


class UpdateBody(BaseModel):
    display_name: str


@router.get("")
def me(
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
) -> dict:
    row = conn.execute(
        "SELECT id, email, display_name FROM users WHERE id = ?",
        (ctx.user_id,),
    ).fetchone()
    return {"user": dict(row) if row else None}


@router.patch("")
def update_me(
    body: UpdateBody,
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
) -> dict:
    conn.execute(
        """
        UPDATE users
        SET display_name = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        WHERE id = ?
        """,
        (body.display_name, ctx.user_id),
    )
    conn.commit()
    return {"ok": True}
