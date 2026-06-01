"""FF-F7-T01a..e: 测试原语 self-test (防原语本身假绿)。

每条断言喂"应成功"必过、喂"应失败"必失败 — 证明原语有效, 否则所有下游红测失效。
"""

import pytest

from browser_runtime import extract_text
from tests.fixtures.primitives import (
    HTML_SAMPLE,
    MALICIOUS_PATHS,
    assert_clean_text,
    assert_vector_authentic,
    expire_lease_real_path,
    iso_format_ok,
)
from tests.fixtures.sqlite_kernel import make_kernel_dbs, seed_minimum_graph


def test_iso_format_ok_self() -> None:
    assert iso_format_ok("2026-06-01T03:00:00.123Z")
    assert not iso_format_ok("2026-06-01 03:00:00")  # 空格式 (CURRENT_TIMESTAMP) 应判错
    assert not iso_format_ok("2026-06-01T03:00:00Z")  # 缺毫秒


def test_malicious_paths_nonempty_and_attack_vectors() -> None:
    assert "../escaped.txt" in MALICIOUS_PATHS
    assert any(p.startswith("/") for p in MALICIOUS_PATHS)
    assert any(".." in p for p in MALICIOUS_PATHS)


def test_assert_vector_authentic_self() -> None:
    good = [{"chunk_id": "a", "score": 0.9}, {"chunk_id": "b", "score": 0.4}]
    assert_vector_authentic(good, "a")
    # 目标未排第一 → 应失败。
    with pytest.raises(AssertionError):
        assert_vector_authentic(good, "b")
    # 分差不足 → 应失败。
    with pytest.raises(AssertionError):
        assert_vector_authentic([{"chunk_id": "a", "score": 0.5}, {"chunk_id": "b", "score": 0.49}], "a")


def test_assert_clean_text_self() -> None:
    assert_clean_text(extract_text(HTML_SAMPLE))
    # 残留标签 → 应失败。
    with pytest.raises(AssertionError):
        assert_clean_text("<p>still tagged</p>")


def test_expire_lease_real_path_self() -> None:
    from workflow_core.claim import claim_next_step
    from storage_sqlite.repositories.steps import StepRepository
    from storage_sqlite.repositories.workflow import WorkflowRepository
    from workflow_core.leases import reap_expired_claims

    core, _ = make_kernel_dbs()
    ids = seed_minimum_graph(core)
    WorkflowRepository(core).create_run(
        run_id=ids["run_id"], team_id=ids["team_id"],
        source_id=ids["source_id"], document_id=ids["document_id"],
    )
    StepRepository(core).create_step(
        step_id="s1", team_id=ids["team_id"], workflow_run_id=ids["run_id"],
        step_key="clean:x", stage="clean", action="mock",
    )
    claim = claim_next_step(core, worker_type="w", worker_id="w1", lease_seconds=60)
    past = expire_lease_real_path(core, claim["id"])
    assert iso_format_ok(past)
    # 经真实 SSOT 路径过期后可被 reap。
    assert reap_expired_claims(core) == 1
