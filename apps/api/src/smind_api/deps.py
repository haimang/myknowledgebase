from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache
from sqlite3 import Connection

from auth import AuthService
from fastapi import Depends, Header, HTTPException
from ingestion import IngestionService
from management import ManagementService
from smind_config.loader import load_settings
from storage_objects import FileSystemObjectStore
from storage_sqlite.engine import CoreSQLiteEngine
from storage_sqlite.migrations.runner import apply_core_migrations
from team import TeamService
from vector_sqlite_vec import VecSQLiteEngine, apply_vec_schema


@lru_cache(maxsize=16)
def _ensure_core_migrated(db_path: str) -> None:
    conn = CoreSQLiteEngine(db_path).connect()
    apply_core_migrations(conn)
    conn.close()


@lru_cache(maxsize=16)
def _ensure_vec_migrated(db_path: str) -> None:
    conn = VecSQLiteEngine(db_path).connect()
    apply_vec_schema(conn)
    conn.close()


def get_core_conn() -> Iterator[Connection]:
    """Yield a core connection, closing it when the request ends.

    F2-01 (G-CR2-01 / part-cr-2.md R1): generator dependency so FastAPI runs
    the ``finally`` on request teardown -> no per-request connection leak.
    Endpoint signatures (``Depends(get_core_conn)``) are unchanged.
    """
    settings = load_settings()
    _ensure_core_migrated(settings.core_db_path)
    conn = CoreSQLiteEngine(settings.core_db_path).connect()
    try:
        yield conn
    finally:
        conn.close()


def get_vec_conn() -> Iterator[Connection]:
    """Yield a vector connection, closing it when the request ends."""
    settings = load_settings()
    _ensure_vec_migrated(settings.vec_db_path)
    conn = VecSQLiteEngine(settings.vec_db_path).connect()
    try:
        yield conn
    finally:
        conn.close()


@dataclass
class AuthContext:
    user_id: str | None
    session_id: str | None
    team_id: str | None
    email: str
    is_api_key: bool = False


def get_auth_context(
    authorization: str = Header(default=""),
    x_api_key: str = Header(default=""),
    conn: Connection = Depends(get_core_conn),
) -> AuthContext:
    # F6-07: Bearer session 优先 (存量路径不变); 否则走 API key 分支 (ApiKey/X-Api-Key)。
    if authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "", 1).strip()
        row = AuthService(conn).validate_session(token)
        if not row:
            raise HTTPException(status_code=401, detail="invalid session")
        return AuthContext(
            user_id=row["user_id"],
            session_id=row["id"],
            team_id=row["team_id"],
            email=row["email"],
        )

    raw_key = x_api_key.strip()
    if not raw_key and authorization.startswith("ApiKey "):
        raw_key = authorization.replace("ApiKey ", "", 1).strip()
    if raw_key:
        # F6-07 P2-03/04: team 归属唯一取 api_keys.team_id (不信请求侧, ⛔3);
        # 伪造/无效/revoked/expired 统一 401 (不泄漏细节, ⛔4)。
        key_row = AuthService(conn).validate_api_key(raw_key)
        if not key_row:
            raise HTTPException(status_code=401, detail="invalid api key")
        return AuthContext(
            user_id=key_row["created_by_user_id"],
            session_id=None,
            team_id=key_row["team_id"],
            email="",
            is_api_key=True,
        )

    raise HTTPException(status_code=401, detail="missing bearer token")


def require_team(ctx: AuthContext) -> str:
    if not ctx.team_id:
        raise HTTPException(status_code=403, detail="team_setup_required")
    return ctx.team_id


def make_ingestion_service(conn: Connection) -> IngestionService:
    settings = load_settings()
    store = FileSystemObjectStore(settings.object_store_dir)
    return IngestionService(conn, store)


def make_team_service(conn: Connection) -> TeamService:
    return TeamService(conn)


def make_management_service(conn: Connection, vec_conn: Connection) -> ManagementService:
    settings = load_settings()
    store = FileSystemObjectStore(settings.object_store_dir)
    return ManagementService(conn, vec_conn=vec_conn, object_store=store)
