from sqlite3 import Connection

from auth import AuthService
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from smind_api.deps import get_auth_context, get_core_conn

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterBody(BaseModel):
    email: str
    password: str
    display_name: str


class LoginBody(BaseModel):
    email: str
    password: str


@router.post("/register")
def register(body: RegisterBody, conn: Connection = Depends(get_core_conn)) -> dict:
    user_id = AuthService(conn).register(body.email, body.password, body.display_name)
    return {"user_id": user_id}


@router.post("/login")
def login(body: LoginBody, conn: Connection = Depends(get_core_conn)) -> dict:
    token = AuthService(conn).login(body.email, body.password)
    return {"token": token}


@router.get("/session")
def validate_session(ctx=Depends(get_auth_context)) -> dict:
    return {"user_id": ctx.user_id, "team_id": ctx.team_id, "email": ctx.email}
