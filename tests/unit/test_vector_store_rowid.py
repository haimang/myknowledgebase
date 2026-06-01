"""FF-F4-T03/T04 (F4-03/F4-04): VectorStore rowid 不变量与软删审计.

先红后绿 ([Q7]) — 主审实测两条红:
- T03 孤儿: 同 chunk_id upsert ×3 当前 HEAD 用 MAX(rowid)+1 每次新号
  → chunk_embedding_index 孤儿 [1,2] (违反 vec.sql:56-57 一一对应)。
- T04 重号/审计: upsert a,b → delete_chunk(b) 软删 vr 但硬删 index rowid →
  upsert 新 c 时 MAX(1)+1=2 重号 → INSERT OR REPLACE 撞 embedding_rowid UNIQUE
  静默删 b 软删审计行 (b survived?=0)。
修复后: 同 chunk_id 复用现有 rowid (0 孤儿)、rowid 单调不复用 (b 审计幸存)。
"""

from tests.fixtures.sqlite_kernel import make_kernel_dbs
from vector_sqlite_vec import VectorStore

# RWA-09: 写侧维度守卫 + DB CHECK 现要求维度=1024 (真实不变量); 测试向量补齐 1024。
_EMB = [0.1, 0.2, 0.3, 0.4] + [0.0] * 1020


def _index_rowids(vec_conn) -> list[int]:
    return [
        r["rowid"]
        for r in vec_conn.execute(
            "SELECT rowid FROM chunk_embedding_index ORDER BY rowid"
        ).fetchall()
    ]


def _vr_rowids(vec_conn, *, include_deleted: bool) -> list[int]:
    sql = "SELECT embedding_rowid FROM vector_records"
    if not include_deleted:
        sql += " WHERE deleted_at IS NULL"
    return [r["embedding_rowid"] for r in vec_conn.execute(sql + " ORDER BY embedding_rowid").fetchall()]


def _assert_one_to_one(vec_conn) -> None:
    """vec.sql:56-57 不变量: index 每个 rowid 在 vector_records 有对应 (含软删)。"""
    index = set(_index_rowids(vec_conn))
    vr_all = set(_vr_rowids(vec_conn, include_deleted=True))
    assert index == vr_all, f"orphan/missing: index={sorted(index)} vr={sorted(vr_all)}"


def test_upsert_no_orphan() -> None:
    """FF-F4-T03: 同 chunk_id upsert ×3 → 0 孤儿、rowid 恒定。"""
    _, vec_conn = make_kernel_dbs()
    store = VectorStore(vec_conn, workspace_key="team_x")
    for _ in range(3):
        store.upsert_chunk(chunk_id="chk_a", team_id="team_x", embedding=_EMB)
    assert _index_rowids(vec_conn) == [1], "expected exactly one index row, no orphans"
    _assert_one_to_one(vec_conn)


def test_soft_delete_audit_survives() -> None:
    """FF-F4-T04: 软删 b 后 upsert 新 c，b 软删审计行幸存、rowid 不复用。"""
    _, vec_conn = make_kernel_dbs()
    store = VectorStore(vec_conn, workspace_key="team_x")
    store.upsert_chunk(chunk_id="chk_a", team_id="team_x", embedding=_EMB)
    store.upsert_chunk(chunk_id="chk_b", team_id="team_x", embedding=_EMB)
    b_rowid = vec_conn.execute(
        "SELECT embedding_rowid FROM vector_records WHERE chunk_id='chk_b'"
    ).fetchone()["embedding_rowid"]

    store.delete_chunk("chk_b")

    # b 软删审计行幸存 (deleted_at 非空)。
    b_row = vec_conn.execute(
        "SELECT chunk_id, deleted_at, embedding_rowid FROM vector_records WHERE chunk_id='chk_b'"
    ).fetchone()
    assert b_row is not None, "b survived?=0: soft-deleted audit row was destroyed"
    assert b_row["deleted_at"] is not None

    # upsert 新 c → 拿到不复用的新 rowid。
    store.upsert_chunk(chunk_id="chk_c", team_id="team_x", embedding=_EMB)
    c_rowid = vec_conn.execute(
        "SELECT embedding_rowid FROM vector_records WHERE chunk_id='chk_c'"
    ).fetchone()["embedding_rowid"]
    assert c_rowid != b_rowid, f"rowid {b_rowid} reused for c (renumber bug)"

    # b 审计行仍在 (未被 c 的 INSERT OR REPLACE 抹除)。
    still_b = vec_conn.execute(
        "SELECT 1 FROM vector_records WHERE chunk_id='chk_b'"
    ).fetchone()
    assert still_b is not None, "b survived?=0 after upserting c"
    _assert_one_to_one(vec_conn)


def test_resurrect_same_chunk_reuses_rowid() -> None:
    """软删后再 upsert 同 chunk_id → 复用其 rowid 并复活 (deleted_at 清空)。"""
    _, vec_conn = make_kernel_dbs()
    store = VectorStore(vec_conn, workspace_key="team_x")
    store.upsert_chunk(chunk_id="chk_a", team_id="team_x", embedding=_EMB)
    a_rowid = _vr_rowids(vec_conn, include_deleted=True)[0]
    store.delete_chunk("chk_a")
    store.upsert_chunk(chunk_id="chk_a", team_id="team_x", embedding=_EMB)
    row = vec_conn.execute(
        "SELECT embedding_rowid, deleted_at FROM vector_records WHERE chunk_id='chk_a'"
    ).fetchone()
    assert row["embedding_rowid"] == a_rowid
    assert row["deleted_at"] is None
    _assert_one_to_one(vec_conn)
