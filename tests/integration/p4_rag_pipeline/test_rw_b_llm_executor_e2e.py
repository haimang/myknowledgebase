"""复审回应 R3: 生产 executor 在 semantic_mode=llm 下的端到端集成测试。

原 mock capstone (tests/e2e/test_real_wire_mock_capstone.py) **绕过**了 executor
(`process_rag_step`/`process_clean_step`) 与 `SearchService`, 手工直调库函数。本测试补上
缺口: 经真实 worker (claim/lease/executor 全栈) 在 `SMIND_SEMANTIC_MODE=llm` 下跑
clean→structurize(llm)→construct→summary(llm)→vectorize, 再经 management `SearchService`
检索, 断言:
  1. structured artifact 带 `produced_by=llm` (走了 prompt→render→MockLLM, 非规则桩);
  2. rag:vectorize step succeeded + document active;
  3. SearchService (经 R1 的 vector_index 注入路径) 命中目标文。

mock 经 `SMIND_MOCK_LLM_RESPONSES_PATH` 注入; 预置响应 key = executor 实际渲染出的 prompt
(用与 executor 同源的 clean_payload / structurize_via_llm 归一化结果预先算出, 确保命中)。
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from sqlite3 import connect

from cleaners_universal import clean_payload
from fastapi.testclient import TestClient
from provider_runtime import MockLLMProvider
from rag_constructor import build_section_chunks
from rag_structurizer import structurize_via_llm
from rag_vectorizer import SearchService
from smind_api.main import create_app
from smind_config import render_prompt, sync_prompts_dir
from smind_config.loader import load_settings
from smind_worker.main import run_worker
from storage_objects import FileSystemObjectStore

PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"

_CONTENT = (
    "Value added tax invoice filing for enterprises follows a monthly cycle. "
    "Enterprises must submit the tax invoice filing declaration before the "
    "fifteenth day. Late value added tax filing incurs a penalty."
)

_ENV_KEYS = (
    "SMIND_CORE_DB_PATH",
    "SMIND_VEC_DB_PATH",
    "SMIND_OBJECT_STORE_DIR",
    "SMIND_SEMANTIC_MODE",
    "SMIND_LLM_PROVIDER",
    "SMIND_MOCK_LLM_RESPONSES_PATH",
    "SMIND_PROMPTS_DIR",
)


def _core(path: str):  # noqa: ANN202
    c = connect(path)
    c.row_factory = lambda cur, row: {col[0]: row[i] for i, col in enumerate(cur.description)}
    return c


def test_semantic_mode_llm_executor_end_to_end() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="smind-rwb-llm-"))
    saved = {k: os.environ.get(k) for k in _ENV_KEYS}
    responses_path = tmp / "mock_llm_responses.json"
    try:
        os.environ["SMIND_CORE_DB_PATH"] = str(tmp / "core.db")
        os.environ["SMIND_VEC_DB_PATH"] = str(tmp / "vec.db")
        os.environ["SMIND_OBJECT_STORE_DIR"] = str(tmp / "objects")
        os.environ["SMIND_SEMANTIC_MODE"] = "llm"
        os.environ["SMIND_LLM_PROVIDER"] = "mock"
        os.environ["SMIND_PROMPTS_DIR"] = str(PROMPTS_DIR)
        os.environ["SMIND_MOCK_LLM_RESPONSES_PATH"] = str(responses_path)
        load_settings.cache_clear()

        client = TestClient(create_app())
        core_path = os.environ["SMIND_CORE_DB_PATH"]

        # ingest 一个 file run (请求触发 core 迁移 → prompt_versions 表就位)。
        client.post(
            "/auth/register",
            json={"email": "rwb@e.com", "password": "pw", "display_name": "r"},
        )
        token = client.post(
            "/auth/login", json={"email": "rwb@e.com", "password": "pw"}
        ).json()["token"]
        h = {"Authorization": f"Bearer {token}"}
        client.post("/team/bootstrap", json={"name": "T", "slug": "team-rwb"}, headers=h)
        init = client.post(
            "/ingestion/file/initiate",
            json={"filename": "p.txt", "mime_type": "text/plain"},
            headers=h,
        ).json()
        run_id = client.post(
            "/ingestion/file/confirm",
            json={"upload_id": init["upload_id"], "title": "Policy", "content": _CONTENT},
            headers=h,
        ).json()["workflow_run_id"]

        # prompts seed 入 SQLite (global team_id=None; get_active_prompt 回退全局)。
        # 在 confirm 之后 → 迁移已跑、prompt_versions 已建; 在 run_worker 之前 → structurize 可读。
        seed_conn = _core(core_path)
        sync_prompts_dir(
            seed_conn,
            {"structurize": "structurize.md", "summarize": "summarize.md"},
            prompts_dir=PROMPTS_DIR,
        )

        # 预置 mock 响应: key = executor 将渲染出的 prompt (与 executor 同源计算)。
        # cleaned 文本 = executor 对 file 源的 clean 结果 (clean_payload, 与 _load_raw_payload.strip 一致)。
        cleaned = clean_payload("file", _CONTENT.strip())
        authored = {
            "schema_version": "v1",
            "context_meta": {"title": "Policy", "source_hint": ""},
            "sections": [{"heading": "Policy", "level": 1, "text": cleaned, "order": 0}],
        }
        p_struct = render_prompt(
            seed_conn, None, "structurize", {"input_text": cleaned}, prompts_dir=PROMPTS_DIR
        )
        responses = {p_struct: json.dumps(authored)}
        # 用与 executor 同源的归一化结果算每个 chunk 的 summarize prompt (确保 key 命中)。
        normalized = structurize_via_llm(
            cleaned, MockLLMProvider({p_struct: json.dumps(authored)}), p_struct
        )
        for ch in build_section_chunks(normalized["sections"]):
            p_sum = render_prompt(
                seed_conn,
                None,
                "summarize",
                {"section_path": ch.section_path, "chunk_text": ch.text},
                prompts_dir=PROMPTS_DIR,
            )
            responses[p_sum] = f"summary: {ch.text[:80]}"
        responses_path.write_text(json.dumps(responses), encoding="utf-8")
        load_settings.cache_clear()  # 确保 worker 读到 responses_path + semantic_mode=llm

        for _ in range(12):
            run_worker(once=True, poll_interval=0.0)

        core = _core(core_path)
        team_id = core.execute(
            "SELECT team_id FROM workflow_runs WHERE id = ?", (run_id,)
        ).fetchone()["team_id"]

        # 1) structured artifact 走了 llm (produced_by=llm), 非规则桩。
        art = core.execute(
            "SELECT metadata_json FROM artifacts "
            "WHERE workflow_run_id = ? AND artifact_type = 'structured_json'",
            (run_id,),
        ).fetchone()
        assert art is not None, "no structured_json artifact (structurize step did not run)"
        assert json.loads(art["metadata_json"]).get("produced_by") == "llm", (
            "structurize did not route through llm provider"
        )

        # 2) 独立 rag:vectorize step succeeded + document active。
        vec_step = core.execute(
            "SELECT status FROM workflow_steps "
            "WHERE workflow_run_id = ? AND stage = 'rag:vectorize'",
            (run_id,),
        ).fetchone()
        assert vec_step is not None and vec_step["status"] == "succeeded"
        doc_status = core.execute(
            "SELECT status FROM documents WHERE id = "
            "(SELECT document_id FROM workflow_runs WHERE id = ?)",
            (run_id,),
        ).fetchone()["status"]
        assert doc_status == "active"

        # 3) 经 management SearchService (R1 vector_index 注入路径) 检索命中目标文。
        object_store = FileSystemObjectStore(os.environ["SMIND_OBJECT_STORE_DIR"])
        vec = connect(os.environ["SMIND_VEC_DB_PATH"])
        vec.row_factory = lambda cur, row: {col[0]: row[i] for i, col in enumerate(cur.description)}
        hits = SearchService(
            core, vec, workspace_key=team_id, object_store=object_store
        ).search(team_id=team_id, query="tax invoice filing for enterprises", limit=5)
        assert hits, "search returned no hits over llm-produced chunks"
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        load_settings.cache_clear()
