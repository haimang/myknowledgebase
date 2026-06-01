"""FF-F6c-T09 (F6-11): 统一 PBKDF2 单路径 (删 legacy 密码兼容死代码).

先红后绿 ([Q7]): pre-F6c `_verify_password` 对非 PBKDF2 hash 回退 `_hash_legacy_password`
(裸 sha256) → 一个 sha256 存储的密码会登录成功 (红)。删除后非 PBKDF2 一律失败。
"""

import hashlib
from pathlib import Path

from auth import AuthService
from auth import service as auth_svc
from tests.fixtures.sqlite_kernel import make_kernel_dbs


def test_no_legacy_hash_symbol() -> None:
    src = Path(auth_svc.__file__).read_text(encoding="utf-8")
    assert "_hash_legacy_password" not in src


def test_non_pbkdf2_hash_rejected() -> None:
    core, _ = make_kernel_dbs()
    # 植入一个 legacy 裸 sha256 密码 hash 的用户。
    sha = hashlib.sha256(b"secret").hexdigest()
    core.execute(
        "INSERT INTO users (id, email, display_name, password_hash) VALUES ('u','e@e','U',?)",
        (sha,),
    )
    core.commit()
    # 删 legacy 兼容后: sha256 hash 一律不通过 (非 PBKDF2)。
    assert auth_svc._verify_password("secret", sha) is False


def test_pbkdf2_register_login_happy_path() -> None:
    core, _ = make_kernel_dbs()
    svc = AuthService(core)
    svc.register("a@e.com", "pw123", "A")
    token = svc.login("a@e.com", "pw123")
    assert token.startswith("sess_")
    assert svc.validate_session(token) is not None


def test_login_wrong_password_fails() -> None:
    core, _ = make_kernel_dbs()
    svc = AuthService(core)
    svc.register("b@e.com", "right", "B")
    import pytest

    with pytest.raises(ValueError):
        svc.login("b@e.com", "wrong")
