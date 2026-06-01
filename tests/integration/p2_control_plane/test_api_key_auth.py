"""FF-F6c-T05/T06/T07/T08 (F6-07): API key 认证端到端 + 攻击向量.

先红后绿 ([Q7]): pre-F6c 无 create_api_key 端点、无 api_key 校验 → 全红。
攻击向量 (§7.3): 伪造/非 owner/跨 team 归属 — 不只测 happy-path (§8.5)。
"""

import os
import tempfile
from pathlib import Path
from sqlite3 import connect

from fastapi.testclient import TestClient
from smind_api.main import create_app
from smind_config.loader import load_settings


def _client() -> TestClient:
    tmp = Path(tempfile.mkdtemp(prefix="smind-f6c-"))
    os.environ["SMIND_CORE_DB_PATH"] = str(tmp / "core.db")
    os.environ["SMIND_VEC_DB_PATH"] = str(tmp / "vec.db")
    os.environ["SMIND_OBJECT_STORE_DIR"] = str(tmp / "objects")
    load_settings.cache_clear()
    return TestClient(create_app())


def _owner(client, email, slug):
    client.post("/auth/register", json={"email": email, "password": "pw", "display_name": "o"})
    token = client.post("/auth/login", json={"email": email, "password": "pw"}).json()["token"]
    h = {"Authorization": f"Bearer {token}"}
    team_id = client.post("/team/bootstrap", json={"name": slug, "slug": slug}, headers=h).json()[
        "team_id"
    ]
    return h, team_id


def test_owner_creates_key_and_it_authenticates() -> None:
    client = _client()
    h, team_id = _owner(client, "owner@e.com", "team-k")
    resp = client.post("/team/api-keys", json={"name": "ci"}, headers=h)
    assert resp.status_code == 200, resp.text
    raw = resp.json()["api_key"]
    assert raw.startswith("sm_")
    # 用 api key 调需鉴权端点 (/team/list) → 通过, 解析出 key 的 user/team。
    via_key = client.get("/team/list", headers={"X-Api-Key": raw})
    assert via_key.status_code == 200
    # ApiKey 头形式同样可用。
    via_auth = client.get("/team/list", headers={"Authorization": f"ApiKey {raw}"})
    assert via_auth.status_code == 200


def test_forged_and_missing_key_rejected() -> None:
    client = _client()
    _owner(client, "o2@e.com", "team-k2")
    assert client.get("/team/list", headers={"X-Api-Key": "not-a-key"}).status_code == 401
    assert client.get("/team/list", headers={"X-Api-Key": "sm_forged_random_xyz"}).status_code == 401
    assert client.get("/team/list").status_code == 401  # 无任何凭据


def test_revoked_key_rejected() -> None:
    client = _client()
    h, _ = _owner(client, "o3@e.com", "team-k3")
    raw = client.post("/team/api-keys", json={"name": "r"}, headers=h).json()["api_key"]
    assert client.get("/team/list", headers={"X-Api-Key": raw}).status_code == 200
    # 吊销后立即失效。
    import hashlib

    db = connect(os.environ["SMIND_CORE_DB_PATH"])
    db.execute(
        "UPDATE api_keys SET status='revoked' WHERE key_hash=?",
        (hashlib.sha256(raw.encode()).hexdigest(),),
    )
    db.commit()
    db.close()
    assert client.get("/team/list", headers={"X-Api-Key": raw}).status_code == 401


def test_non_owner_cannot_create_key() -> None:
    client = _client()
    h_owner, team_id = _owner(client, "o4@e.com", "team-k4")
    # 注册第二个用户, 直插为该 team 的非 owner 成员并选中该 team。
    client.post("/auth/register", json={"email": "m@e.com", "password": "pw", "display_name": "m"})
    token2 = client.post("/auth/login", json={"email": "m@e.com", "password": "pw"}).json()["token"]
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
    h_member = {"Authorization": f"Bearer {token2}"}
    resp = client.post("/team/api-keys", json={"name": "x"}, headers=h_member)
    assert resp.status_code == 403, resp.text
