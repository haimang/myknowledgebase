"""FF-F5-T03 (F5-02): vec0 退化路径 fail-loud 告警 (含机器可读 reason).

先红后绿 ([Q7]): pre-F5 HEAD 的 apply_vec_schema except 分支静默退化 (零日志,
G-CR3-02 假绿根因) → 本断言红。修复后退化路径 logger.warning 含 reason。
"""

import logging
import tempfile
from pathlib import Path

from vector_sqlite_vec.engine import VecSQLiteEngine
from vector_sqlite_vec.schema import apply_vec_schema


def test_fallback_emits_warning_with_reason(caplog) -> None:
    tmp = Path(tempfile.mkdtemp(prefix="ff-f5-degraded-"))
    conn = VecSQLiteEngine(tmp / "vec.db").connect()
    with caplog.at_level(logging.WARNING, logger="vector_sqlite_vec.schema"):
        apply_vec_schema(conn)
    # 环境无 sqlite_vec → vec0 不可用 → 退化路径必须告警 (非静默)。
    msgs = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert any("degrad" in m.lower() for m in msgs), msgs
    assert any("sqlite_vec_unavailable_degraded_to_bruteforce" in m for m in msgs), msgs
    # 退化表确实建成 (功能仍可用)。
    cols = {r[1] for r in conn.execute("PRAGMA table_info(chunk_embedding_index)").fetchall()}
    assert {"rowid", "embedding"} <= cols
