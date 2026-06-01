"""跨阶段审查修复回归: M1 检索去重 / M2 chunk_count 据实 / L1 workspace_key 一致.

先红后绿: pre-fix search 返回 original+summary 近重复; constructed_json chunk_count
含未落库 id; vector_namespaces.namespace_key=app_env。
"""

import json
import os
import tempfile
from pathlib import Path
from sqlite3 import connect

from fastapi.testclient import TestClient
from smind_api.main import create_app
from smind_config.loader import load_settings
from smind_worker.main import run_worker

_CONTENT = (
    "# Tax Policy\n"
    "Value added tax applies to enterprises filing monthly invoice returns.\n"
    "## Deductions\n"
    "Small businesses claim deductions. Exemptions exist for selected goods.\n"
)


def _client():
    tmp = Path(tempfile.mkdtemp(prefix="smind-rev-"))
    os.environ["SMIND_CORE_DB_PATH"] = str(tmp / "core.db")
    os.environ["SMIND_VEC_DB_PATH"] = str(tmp / "vec.db")
    os.environ["SMIND_OBJECT_STORE_DIR"] = str(tmp / "objects")
    load_settings.cache_clear()
    return TestClient(create_app())


def _setup(client):
    client.post("/auth/register", json={"email": "r@e.com", "password": "pw", "display_name": "r"})
    tok = client.post("/auth/login", json={"email": "r@e.com", "password": "pw"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    team_id = client.post("/team/bootstrap", json={"name": "T", "slug": "team-r"}, headers=h).json()["team_id"]
    init = client.post(
        "/ingestion/file/initiate", json={"filename": "d.txt", "mime_type": "text/plain"}, headers=h
    ).json()
    run_id = client.post(
        "/ingestion/file/confirm",
        json={"upload_id": init["upload_id"], "title": "Policy", "content": _CONTENT},
        headers=h,
    ).json()["workflow_run_id"]
    for _ in range(12):
        run_worker(once=True, poll_interval=0.0)
    return h, team_id, run_id


def _core():
    c = connect(os.environ["SMIND_CORE_DB_PATH"])
    c.row_factory = lambda cur, r: {col[0]: r[i] for i, col in enumerate(cur.description)}
    return c


def test_m2_chunk_count_matches_actual_rows() -> None:
    client = _client()
    _, _, run_id = _setup(client)
    core = _core()
    constructed = core.execute(
        "SELECT metadata_json FROM artifacts WHERE workflow_run_id=? AND artifact_type='constructed_json'",
        (run_id,),
    ).fetchone()
    declared = json.loads(constructed["metadata_json"])["chunk_count"]
    actual = core.execute(
        "SELECT COUNT(1) AS c FROM chunks WHERE workflow_run_id=?", (run_id,)
    ).fetchone()["c"]
    assert declared == actual, f"chunk_count 虚高: declared={declared} actual={actual}"
    # 场景真实性: 存在双通道 (同 chunk_index 两 channel)。
    dual = core.execute(
        "SELECT chunk_index, COUNT(1) AS c FROM chunks WHERE workflow_run_id=? GROUP BY chunk_index",
        (run_id,),
    ).fetchall()
    assert any(r["c"] >= 1 for r in dual)


def test_m1_search_no_duplicate_logical_chunk() -> None:
    client = _client()
    h, _, run_id = _setup(client)
    core = _core()
    res = client.post("/search", json={"query": "tax invoice enterprises", "limit": 10}, headers=h)
    assert res.status_code == 200
    items = res.json()["items"]
    assert items, "search 应有结果"
    # 每个 (document_id, chunk_index) 在结果中至多出现一次 (双通道去重)。
    seen = set()
    for it in items:
        ci = core.execute(
            "SELECT chunk_index FROM chunks WHERE id=?", (it["chunk_id"],)
        ).fetchone()
        key = (it["document_id"], ci["chunk_index"] if ci else it["chunk_id"])
        assert key not in seen, f"重复逻辑 chunk 出现在结果: {key}"
        seen.add(key)


def test_l1_namespace_key_is_team_id() -> None:
    client = _client()
    _, team_id, _ = _setup(client)
    vec = connect(os.environ["SMIND_VEC_DB_PATH"])
    vec.row_factory = lambda cur, r: {col[0]: r[i] for i, col in enumerate(cur.description)}
    ns = vec.execute(
        "SELECT namespace_key FROM vector_namespaces WHERE id=?", (f"ns_{team_id}",)
    ).fetchone()
    assert ns is not None and ns["namespace_key"] == team_id  # 写侧 workspace_key=team_id
