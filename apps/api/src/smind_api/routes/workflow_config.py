import json
from sqlite3 import Connection

from fastapi import APIRouter, Depends

from smind_api.deps import AuthContext, get_auth_context, get_core_conn

router = APIRouter(prefix="/workflow-configs", tags=["workflow-config"])


@router.get("")
def list_workflow_configs(
    ctx: AuthContext = Depends(get_auth_context),
    conn: Connection = Depends(get_core_conn),
) -> dict:
    rows = conn.execute(
        """
        SELECT id, config_scope, config_key, version, content_json, status
        FROM configs
        WHERE (team_id = ? OR team_id IS NULL)
        ORDER BY created_at DESC
        """,
        (ctx.team_id,),
    ).fetchall()
    if not rows:
        return {
            "items": [
                {
                    "id": "default",
                    "config_scope": "workflow",
                    "config_key": "default",
                    "version": "v1",
                    "content": {"profile": "default"},
                    "status": "active",
                }
            ]
        }
    return {
        "items": [
            {
                "id": r["id"],
                "config_scope": r["config_scope"],
                "config_key": r["config_key"],
                "version": r["version"],
                "content": json.loads(r["content_json"]),
                "status": r["status"],
            }
            for r in rows
        ]
    }
