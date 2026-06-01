import re

from smind_common.time import add_seconds_iso
from storage_sqlite.repositories.steps import StepRepository
from storage_sqlite.repositories.workflow import WorkflowRepository
from workflow_core.claim import claim_next_step
from workflow_core.leases import heartbeat_claim, reap_expired_claims
from workflow_core.retry import fail_claim, succeed_claim

from tests.fixtures.sqlite_kernel import make_kernel_dbs, seed_minimum_graph

_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def test_claim_heartbeat_success_and_retry() -> None:
    core_conn, _ = make_kernel_dbs()
    ids = seed_minimum_graph(core_conn)
    workflow_repo = WorkflowRepository(core_conn)
    steps = StepRepository(core_conn)
    workflow_repo.create_run(
        run_id=ids["run_id"],
        team_id=ids["team_id"],
        source_id=ids["source_id"],
        document_id=ids["document_id"],
    )
    steps.create_step(
        step_id="step_p1",
        team_id=ids["team_id"],
        workflow_run_id=ids["run_id"],
        step_key="clean:seed",
        stage="clean",
        action="mock",
        max_attempts=2,
    )

    claim = claim_next_step(core_conn, worker_type="worker", worker_id="w1", lease_seconds=60)
    assert claim is not None
    assert heartbeat_claim(core_conn, claim["claim_token"], lease_seconds=60) is True
    assert fail_claim(
        core_conn,
        claim["claim_token"],
        error_code="MOCK_FAIL",
        error_message="boom",
        retry_backoff_seconds=0,
    )
    step = steps.get_step("step_p1")
    assert step is not None
    assert step["status"] == "retry_wait"

    reclaim = claim_next_step(core_conn, worker_type="worker", worker_id="w2", lease_seconds=60)
    assert reclaim is not None
    assert reclaim["step_id"] == "step_p1"
    assert succeed_claim(core_conn, reclaim["claim_token"])
    step = steps.get_step("step_p1")
    assert step is not None
    assert step["status"] == "succeeded"


def test_expired_claim_can_be_reclaimed() -> None:
    core_conn, _ = make_kernel_dbs()
    ids = seed_minimum_graph(core_conn)
    workflow_repo = WorkflowRepository(core_conn)
    steps = StepRepository(core_conn)
    workflow_repo.create_run(
        run_id=ids["run_id"],
        team_id=ids["team_id"],
        source_id=ids["source_id"],
        document_id=ids["document_id"],
    )
    steps.create_step(
        step_id="step_expire",
        team_id=ids["team_id"],
        workflow_run_id=ids["run_id"],
        step_key="clean:expire",
        stage="clean",
        action="mock",
    )
    claim = claim_next_step(core_conn, worker_type="worker", worker_id="w1", lease_seconds=1)
    assert claim is not None
    # F7-02: 去夹具掩盖 (part-cr-8 R2)。原代码用 SQL `strftime` 手写正确格式覆盖
    # lease_expires_at, 绕过 now_iso() 真实写入路径。改为经**真实 SSOT Python 路径**
    # `add_seconds_iso(-1)` 写一个真正过期的 lease (与 now_iso 同源格式, 非 SQL 手写)。
    past_lease = add_seconds_iso(-1)
    assert _ISO_RE.match(past_lease), f"SSOT format drift: {past_lease!r}"
    core_conn.execute(
        "UPDATE task_claims SET lease_expires_at = ? WHERE id = ?",
        (past_lease, claim["id"]),
    )
    core_conn.commit()
    assert reap_expired_claims(core_conn) == 1
    reclaim = claim_next_step(core_conn, worker_type="worker", worker_id="w3", lease_seconds=60)
    assert reclaim is not None
    assert reclaim["step_id"] == "step_expire"
