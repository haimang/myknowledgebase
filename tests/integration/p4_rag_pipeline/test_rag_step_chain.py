"""FF-F6b-T02/T04/T05/T06/T08 (F6-05/06): 独立 rag:vectorize step + 双通道 + 重放幂等 + 契约.

先红后绿 ([Q7]): pre-F6b 向量化内联于 construct (无独立 rag:vectorize step)、单通道、
chunk_id=uuid4 (replay 产重复)。本测试断言独立 step + 双通道 + 确定性 replay 幂等。
"""

import os
import tempfile
from pathlib import Path
from sqlite3 import connect

from fastapi.testclient import TestClient
from smind_api.main import create_app
from smind_config.loader import load_settings
from smind_worker.main import run_worker
from workflow_rag import service as rag_svc

_CONTENT = (
    "# Tax Policy\n"
    "Value added tax applies to enterprises. Returns are filed monthly.\n"
    "## Deductions\n"
    "Small businesses may claim deductions. Exemptions exist for some goods.\n"
)


def _client():
    tmp = Path(tempfile.mkdtemp(prefix="smind-f6b-"))
    os.environ["SMIND_CORE_DB_PATH"] = str(tmp / "core.db")
    os.environ["SMIND_VEC_DB_PATH"] = str(tmp / "vec.db")
    os.environ["SMIND_OBJECT_STORE_DIR"] = str(tmp / "objects")
    load_settings.cache_clear()
    return TestClient(create_app())


def _setup_file_run(client) -> str:
    client.post("/auth/register", json={"email": "f6b@e.com", "password": "pw", "display_name": "f"})
    token = client.post("/auth/login", json={"email": "f6b@e.com", "password": "pw"}).json()["token"]
    h = {"Authorization": f"Bearer {token}"}
    client.post("/team/bootstrap", json={"name": "T", "slug": "team-f6b"}, headers=h)
    init = client.post(
        "/ingestion/file/initiate", json={"filename": "p.txt", "mime_type": "text/plain"}, headers=h
    ).json()
    run_id = client.post(
        "/ingestion/file/confirm",
        json={"upload_id": init["upload_id"], "title": "Policy", "content": _CONTENT},
        headers=h,
    ).json()["workflow_run_id"]
    return run_id


def _core():
    c = connect(os.environ["SMIND_CORE_DB_PATH"])
    c.row_factory = lambda cur, row: {col[0]: row[i] for i, col in enumerate(cur.description)}
    return c


def test_independent_vectorize_step_and_dual_channel() -> None:
    client = _client()
    run_id = _setup_file_run(client)
    for _ in range(8):
        run_worker(once=True, poll_interval=0.0)

    core = _core()
    # T06: 独立 rag:vectorize step 存在且成功。
    vec_step = core.execute(
        "SELECT status FROM workflow_steps WHERE workflow_run_id=? AND stage='rag:vectorize'",
        (run_id,),
    ).fetchone()
    assert vec_step is not None and vec_step["status"] == "succeeded"
    # construct step 独立于 vectorize step。
    construct_step = core.execute(
        "SELECT status FROM workflow_steps WHERE workflow_run_id=? AND stage='rag:construct'",
        (run_id,),
    ).fetchone()
    assert construct_step is not None and construct_step["status"] == "succeeded"

    # T03/双通道: chunk_text artifacts 含 original + summary 两通道。
    channels = {
        __import__("json").loads(r["metadata_json"]).get("channel")
        for r in core.execute(
            "SELECT metadata_json FROM artifacts WHERE workflow_run_id=? AND artifact_type='chunk_text'",
            (run_id,),
        ).fetchall()
    }
    assert "original" in channels and "summary" in channels, channels

    # 全部 vectorized + run completed。
    pending = core.execute(
        "SELECT COUNT(1) AS c FROM chunks WHERE workflow_run_id=? AND vec_status!='vectorized'",
        (run_id,),
    ).fetchone()["c"]
    assert pending == 0
    assert core.execute("SELECT status FROM workflow_runs WHERE id=?", (run_id,)).fetchone()["status"] == "completed"


def test_replay_idempotent_no_duplicate_chunks() -> None:
    client = _client()
    run_id = _setup_file_run(client)
    for _ in range(8):
        run_worker(once=True, poll_interval=0.0)
    core = _core()
    before = core.execute(
        "SELECT COUNT(1) AS c FROM chunks WHERE workflow_run_id=?", (run_id,)
    ).fetchone()["c"]
    vec = connect(os.environ["SMIND_VEC_DB_PATH"])
    vec.row_factory = lambda cur, row: {col[0]: row[i] for i, col in enumerate(cur.description)}
    vbefore = vec.execute("SELECT COUNT(1) AS c FROM vector_records").fetchone()["c"]
    # 再驱动 worker (重放): 确定性 chunk_id + INSERT OR IGNORE → 不产重复。
    for _ in range(3):
        run_worker(once=True, poll_interval=0.0)
    after = core.execute(
        "SELECT COUNT(1) AS c FROM chunks WHERE workflow_run_id=?", (run_id,)
    ).fetchone()["c"]
    vec2 = connect(os.environ["SMIND_VEC_DB_PATH"])
    vec2.row_factory = lambda cur, row: {col[0]: row[i] for i, col in enumerate(cur.description)}
    vafter = vec2.execute("SELECT COUNT(1) AS c FROM vector_records").fetchone()["c"]
    assert after == before, f"replay produced duplicate chunks {before}->{after}"
    assert vafter == vbefore, f"replay produced duplicate/orphan vectors {vbefore}->{vafter}"


def test_construct_vectorize_contract_no_self_commit() -> None:
    """T02/T05: rag 执行器源码无自提交终态 / conn.commit (遵 F3-02)。"""
    src = Path(rag_svc.__file__).read_text(encoding="utf-8")
    assert "conn.commit()" not in src
    assert "status = 'succeeded'" not in src
    assert "status='succeeded'" not in src
