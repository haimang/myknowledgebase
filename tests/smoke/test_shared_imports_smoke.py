from smind_common import SmindError, new_id, utc_now_iso
from smind_config import load_settings
from smind_contracts import WorkflowRunContract


def test_shared_imports() -> None:
    err = SmindError("x")
    assert err.code == "SMIND_ERROR"
    assert new_id("run").startswith("run_")
    assert "T" in utc_now_iso()
    assert load_settings().app_env == "local"
    run = WorkflowRunContract(workflow_run_id="w", team_id="t", status="pending")
    assert run.status == "pending"

