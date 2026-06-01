"""FF-F6a-T02/T03/T09: clean 执行器契约 (无硬选/无自提交/重放安全) + scatter degraded.

先红后绿 ([Q7]):
- 契约 gate: clean service 源码无 `or clean_payload`/`maybe_clean_with_provider` 硬选,
  无 `status='succeeded'`/`conn.commit()`/`CURRENT_TIMESTAMP` (core 侧自提交)。
- 重放安全: process_clean_step 重复执行不产重复 artifact (确定性 id, F3-02 契约)。
- F6-08: 多文档源 (child_files>0) 显式 DegradedActionError。
"""

import json
import tempfile
from pathlib import Path

import pytest
from ingestion.service import IngestionService
from storage_objects import FileSystemObjectStore
from workflow_clean import DegradedActionError, process_clean_step
from workflow_clean import service as clean_svc

from tests.fixtures.sqlite_kernel import make_kernel_dbs

_SRC = Path(clean_svc.__file__).read_text(encoding="utf-8")


def test_no_ifelse_hardselect_in_source() -> None:
    assert "or clean_payload" not in _SRC
    assert "maybe_clean_with_provider" not in _SRC


def test_no_self_commit_terminal_in_source() -> None:
    assert "status='succeeded'" not in _SRC
    assert "status=\"succeeded\"" not in _SRC
    assert "conn.commit()" not in _SRC
    assert "CURRENT_TIMESTAMP" not in _SRC


def _setup_file_clean_step():
    core_conn, _ = make_kernel_dbs()
    core_conn.execute("INSERT INTO teams (id, slug, name) VALUES ('team_x','tx','TX')")
    core_conn.execute(
        "INSERT INTO users (id, email, display_name, password_hash) VALUES ('u','e@e','U','h')"
    )
    core_conn.commit()
    store = FileSystemObjectStore(str(Path(tempfile.mkdtemp(prefix="ff-f6a-")) / "obj"))
    svc = IngestionService(core_conn, store)
    init = svc.file_initiate("team_x", "u", "doc.txt", "text/plain")
    svc.file_confirm(team_id="team_x", upload_id=init["upload_id"], title="T", content="body text")
    step = core_conn.execute(
        "SELECT id FROM workflow_steps WHERE stage = 'clean' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    return core_conn, store, step["id"]


def test_clean_step_returns_executor_result_no_terminal() -> None:
    core_conn, store, step_id = _setup_file_clean_step()
    result = process_clean_step(core_conn, step_id, store)
    # 返回 ExecutorResult (下游 rag:structurize + run advance); 不写 step 终态。
    assert result.downstream and result.downstream[0].stage == "rag:structurize"
    row = core_conn.execute(
        "SELECT status FROM workflow_steps WHERE id = ?", (step_id,)
    ).fetchone()
    assert row["status"] == "pending"  # 终态归内核, 执行器不写


def test_clean_replay_safe_deterministic_artifact() -> None:
    core_conn, store, step_id = _setup_file_clean_step()
    process_clean_step(core_conn, step_id, store)
    process_clean_step(core_conn, step_id, store)  # 重放
    count = core_conn.execute(
        "SELECT COUNT(1) AS c FROM artifacts WHERE workflow_step_id = ? AND artifact_type='cleaned_text'",
        (step_id,),
    ).fetchone()["c"]
    assert count == 1, "重放产生了重复 artifact (确定性 id 失效)"


def test_scatter_multi_document_degraded() -> None:
    core_conn, store, step_id = _setup_file_clean_step()
    # 注入多文档源标记 → 显式 degraded。
    core_conn.execute(
        "UPDATE workflow_steps SET payload_json = ? WHERE id = ?",
        (json.dumps({"action_branch": "text", "child_files": ["a", "b"]}), step_id),
    )
    core_conn.commit()
    with pytest.raises(DegradedActionError):
        process_clean_step(core_conn, step_id, store)
