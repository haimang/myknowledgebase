from __future__ import annotations

import hashlib
import hmac
import secrets
from sqlite3 import Connection, Row
from uuid import uuid4

_PBKDF2_PREFIX = "pbkdf2_sha256"
_PBKDF2_ITERATIONS = 120_000


def _hash_token(v: str) -> str:
    return hashlib.sha256(v.encode("utf-8")).hexdigest()


def _hash_legacy_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _hash_password(password: str, *, iterations: int = _PBKDF2_ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{_PBKDF2_PREFIX}${iterations}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash.startswith(f"{_PBKDF2_PREFIX}$"):
        return hmac.compare_digest(_hash_legacy_password(password), stored_hash)
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
        if not row["password_hash"].startswith(f"{_PBKDF2_PREFIX}$"):
            self.conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (_hash_password(password), row["id"]),
            )
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
