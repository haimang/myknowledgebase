"""L2: API key 吊销端点 (泄漏 key 可经 API 即时失效).

先红后绿: pre-fix 无 /team/api-keys/revoke, 泄漏 key 只能直连 DB 撤销。
"""

import os
import tempfile
from pathlib import Path
from sqlite3 import connect

from fastapi.testclient import TestClient
from smind_api.main import create_app
from smind_config.loader import load_settings


def _client():
    tmp = Path(tempfile.mkdtemp(prefix="smind-rev2-"))
    os.environ["SMIND_CORE_DB_PATH"] = str(tmp / "core.db")
    os.environ["SMIND_VEC_DB_PATH"] = str(tmp / "vec.db")
    os.environ["SMIND_OBJECT_STORE_DIR"] = str(tmp / "objects")
    load_settings.cache_clear()
    return TestClient(create_app())


def _owner(client, email, slug):
    client.post("/auth/register", json={"email": email, "password": "pw", "display_name": "o"})
    tok = client.post("/auth/login", json={"email": email, "password": "pw"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    team_id = client.post("/team/bootstrap", json={"name": slug, "slug": slug}, headers=h).json()["team_id"]
    return h, team_id


def test_owner_revokes_key_then_401() -> None:
    client = _client()
    h, _ = _owner(client, "o@e.com", "team-rv")
    created = client.post("/team/api-keys", json={"name": "k"}, headers=h).json()
    raw, key_id = created["api_key"], created["id"]
    # 吊销前可用。
    assert client.get("/team/list", headers={"X-Api-Key": raw}).status_code == 200
    # owner 吊销。
    rv = client.post("/team/api-keys/revoke", json={"key_id": key_id}, headers=h)
    assert rv.status_code == 200, rv.text
    # 吊销后即时失效。
    assert client.get("/team/list", headers={"X-Api-Key": raw}).status_code == 401


def test_revoke_unknown_key_404() -> None:
    client = _client()
    h, _ = _owner(client, "o2@e.com", "team-rv2")
    rv = client.post("/team/api-keys/revoke", json={"key_id": "apikey_nonexistent"}, headers=h)
    assert rv.status_code == 404


def test_non_owner_cannot_revoke_403() -> None:
    client = _client()
    h_owner, team_id = _owner(client, "o3@e.com", "team-rv3")
    created = client.post("/team/api-keys", json={"name": "k"}, headers=h_owner).json()
    # 非 owner 成员。
    client.post("/auth/register", json={"email": "m@e.com", "password": "pw", "display_name": "m"})
    tok2 = client.post("/auth/login", json={"email": "m@e.com", "password": "pw"}).json()["token"]
    db = connect(os.environ["SMIND_CORE_DB_PATH"])
    db.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
    uid = db.execute("SELECT id FROM users WHERE email='m@e.com'").fetchone()["id"]
    sid = db.execute(
        "SELECT id FROM sessions WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (uid,)
    ).fetchone()["id"]
    db.execute(
        "INSERT INTO team_members (team_id, user_id, role, status, joined_at) "
        "VALUES (?, ?, 'member', 'active', strftime('%Y-%m-%dT%H:%M:%fZ','now'))",
        (team_id, uid),
    )
    db.execute("UPDATE sessions SET team_id=? WHERE id=?", (team_id, sid))
    db.commit()
    db.close()
    rv = client.post(
        "/team/api-keys/revoke",
        json={"key_id": created["id"]},
        headers={"Authorization": f"Bearer {tok2}"},
    )
    assert rv.status_code == 403
