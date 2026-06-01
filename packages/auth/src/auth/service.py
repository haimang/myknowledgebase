from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from sqlite3 import Connection, Row
from uuid import uuid4

_PBKDF2_PREFIX = "pbkdf2_sha256"
_PBKDF2_ITERATIONS = 120_000
_API_KEY_PREFIX = "sm_"


def _hash_token(v: str) -> str:
    return hashlib.sha256(v.encode("utf-8")).hexdigest()


def generate_api_key() -> str:
    """F6-07: 生成 `sm_<base64url(32B)>` 明文 (对齐 legacy generateApiKey)。"""
    body = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii").rstrip("=")
    return f"{_API_KEY_PREFIX}{body}"


def hash_api_key(raw: str) -> str:
    """F6-07: api key 仅以 sha256 hash 存储 (与会话 token 同策略, ⛔1 明文绝不入库)。"""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _hash_password(password: str, *, iterations: int = _PBKDF2_ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{_PBKDF2_PREFIX}${iterations}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    # F6-11 ([Q6]): 统一 PBKDF2 单路径; 非 PBKDF2 hash 一律不通过 (删 legacy 兼容死代码)。
    if not stored_hash.startswith(f"{_PBKDF2_PREFIX}$"):
        return False
    parts = stored_hash.split("$", 3)
    if len(parts) != 4:
        return False
    _, iterations_text, salt_hex, digest_hex = parts
    try:
        iterations = int(iterations_text)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


class AuthService:
    def __init__(self, conn: Connection) -> None:
        self.conn = conn

    def register(self, email: str, password: str, display_name: str) -> str:
        user_id = f"user_{uuid4().hex}"
        self.conn.execute(
            """
            INSERT INTO users (id, email, display_name, password_hash)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, email, display_name, _hash_password(password)),
        )
        self.conn.commit()
        return user_id

    def login(self, email: str, password: str) -> str:
        row = self.conn.execute(
            "SELECT id, password_hash FROM users WHERE email = ? AND status = 'active'",
            (email,),
        ).fetchone()
        if not row or not _verify_password(password, row["password_hash"]):
            raise ValueError("invalid credentials")
        # F6-11: 统一 PBKDF2 单路径 — 删 legacy rehash 分支 (非 PBKDF2 已在 _verify 拒绝)。
        token = f"sess_{uuid4().hex}"
        session_id = f"session_{uuid4().hex}"
        self.conn.execute(
            """
            INSERT INTO sessions (id, user_id, token_hash, expires_at)
            VALUES (?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '+7 day'))
            """,
            (session_id, row["id"], _hash_token(token)),
        )
        self.conn.commit()
        return token

    def validate_session(self, token: str) -> Row | None:
        token_hash = _hash_token(token)
        row = self.conn.execute(
            """
            SELECT s.*, u.email, u.display_name
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ?
              AND s.status = 'active'
              AND u.status = 'active'
              AND s.expires_at > strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            """,
            (token_hash,),
        ).fetchone()
        if row is not None:
            return row
        self.conn.execute(
            """
            UPDATE sessions
            SET status = 'expired',
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE token_hash = ?
              AND status = 'active'
              AND expires_at <= strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            """,
            (token_hash,),
        )
        self.conn.commit()
        return None

    # --- F6-07: 团队 API key 认证 -------------------------------------------

    def create_api_key(
        self,
        *,
        team_id: str,
        name: str,
        created_by_user_id: str | None = None,
        scopes_json: str | None = None,
        expires_at: str | None = None,
    ) -> dict:
        """生成 key, 仅落 sha256 hash + key_prefix; 明文一次性返回 (P2-02/05)。"""
        raw = generate_api_key()
        key_hash = hash_api_key(raw)
        key_prefix = raw[:12]
        key_id = f"apikey_{uuid4().hex}"
        self.conn.execute(
            """
            INSERT INTO api_keys (
                id, team_id, name, key_prefix, key_hash, scopes_json,
                status, created_by_user_id, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)
            """,
            (key_id, team_id, name, key_prefix, key_hash, scopes_json,
             created_by_user_id, expires_at),
        )
        self.conn.commit()
        # 明文 key 仅此一次返回; 库内只存 hash (⛔1)。
        return {"id": key_id, "api_key": raw, "key_prefix": key_prefix}

    def validate_api_key(self, raw: str) -> Row | None:
        """校验 api key: 前缀 → sha256 → active 查表 → expires_at → team 归属 (P2-03/04)。

        失败 (无前缀/无匹配/revoked/expired) 统一返回 None (调用侧 401, 不泄漏细节 ⛔4)。
        """
        if not raw or not raw.startswith(_API_KEY_PREFIX):
            return None
        key_hash = hash_api_key(raw)
        row = self.conn.execute(
            """
            SELECT id, team_id, created_by_user_id, status, expires_at
            FROM api_keys
            WHERE key_hash = ?
              AND status = 'active'
              AND (expires_at IS NULL OR expires_at > strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            """,
            (key_hash,),
        ).fetchone()
        if row is None:
            return None
        self.conn.execute(
            "UPDATE api_keys SET last_used_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
            (row["id"],),
        )
        self.conn.commit()
        return row
