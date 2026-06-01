"""FF-F6c-T03/T04 (F6-07): api_keys 读写 + key 生成/hash 存储 (明文不入库).

先红后绿 ([Q7]): pre-F6c api_keys 零访问、无 generate/hash/validate → import 红。
"""

from auth import AuthService, generate_api_key, hash_api_key
from tests.fixtures.sqlite_kernel import make_kernel_dbs


def _seed_team(conn):
    conn.execute("INSERT INTO teams (id, slug, name) VALUES ('team_x','tx','TX')")
    conn.execute(
        "INSERT INTO users (id, email, display_name, password_hash) VALUES ('u','e@e','U','h')"
    )
    conn.commit()


def test_generate_api_key_prefix() -> None:
    key = generate_api_key()
    assert key.startswith("sm_") and len(key) > 20
    assert generate_api_key() != generate_api_key()  # 随机


def test_hash_api_key_deterministic_and_irreversible() -> None:
    assert hash_api_key("sm_abc") == hash_api_key("sm_abc")
    assert hash_api_key("sm_abc") != "sm_abc"


def test_create_api_key_stores_only_hash_not_plaintext() -> None:
    core, _ = make_kernel_dbs()
    _seed_team(core)
    svc = AuthService(core)
    result = svc.create_api_key(team_id="team_x", name="ci", created_by_user_id="u")
    raw = result["api_key"]
    assert raw.startswith("sm_")
    # 库内只存 hash, 无明文 (⛔1)。
    rows = core.execute("SELECT key_hash, key_prefix FROM api_keys").fetchall()
    assert len(rows) == 1
    assert rows[0]["key_hash"] == hash_api_key(raw)
    assert raw not in rows[0]["key_hash"]
    # 明文不应作为任何列值落库。
    all_text = " ".join(
        str(v) for r in core.execute("SELECT * FROM api_keys").fetchall() for v in tuple(r)
    )
    assert raw not in all_text


def test_validate_api_key_roundtrip() -> None:
    core, _ = make_kernel_dbs()
    _seed_team(core)
    svc = AuthService(core)
    raw = svc.create_api_key(team_id="team_x", name="ci", created_by_user_id="u")["api_key"]
    row = svc.validate_api_key(raw)
    assert row is not None and row["team_id"] == "team_x"


def test_validate_rejects_forged_and_revoked_and_expired() -> None:
    core, _ = make_kernel_dbs()
    _seed_team(core)
    svc = AuthService(core)
    assert svc.validate_api_key("not-a-key") is None
    assert svc.validate_api_key("sm_forged_random") is None

    raw = svc.create_api_key(team_id="team_x", name="r", created_by_user_id="u")["api_key"]
    core.execute("UPDATE api_keys SET status='revoked' WHERE key_hash=?", (hash_api_key(raw),))
    core.commit()
    assert svc.validate_api_key(raw) is None  # revoked

    raw2 = svc.create_api_key(
        team_id="team_x", name="e", created_by_user_id="u", expires_at="2000-01-01T00:00:00.000Z"
    )["api_key"]
    assert svc.validate_api_key(raw2) is None  # expired
