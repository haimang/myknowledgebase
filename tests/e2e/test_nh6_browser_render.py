"""NH6-T03: default-root real SPA rendering with a measured browser profile."""

from __future__ import annotations

import inspect
import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand
from src.runtime.supply.browser import HardenedBrowserRuntime
from tests.nh6_runtime_support import browser_settings, local_spa_server


def _command() -> ProcessCommand:
    digest = "6" * 64
    return ProcessCommand(
        schema_version="mkb.process-command.v1",
        team_uuid=uuid7(),
        task_uuid=uuid7(),
        trace_uuid=uuid7(),
        execution_uuid=uuid7(),
        process_uuid=uuid7(),
        step_key="acquire_browser",
        process_key="intake.acquire.http_browser",
        process_contract_version="v1",
        fencing_generation=1,
        command_input_digest=digest,
        input_manifest_ref="mkbtest:nh6:browser-input",
        input_manifest_digest=digest,
        config_snapshot_ref="mkbtest:nh6:browser-config",
        config_snapshot_digest=digest,
        binding_digest=digest,
    )


def _source(url: str) -> dict[str, object]:
    return {
        "source_kind": "http_resource",
        "realm": "documentation",
        "type": "article",
        "channel": "general",
        "source_name": "nh6-browser-runtime",
        "external_key": "nh6-spa",
        "url": url,
        "acquisition_mode": "browser",
    }


def _task(team_uuid: str, task_uuid: str, trace_uuid: str, url: str) -> dict[str, object]:
    return {
        "schema_version": "mkb.task.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "request_intent": "intake.ingest",
        "payload": {"json_prompt_id": "promptB.json.generic", "source": _source(url)},
        "audit": {
            "schema_version": "mkb.task-audit.v1",
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "trace_uuid": trace_uuid,
            "audit_type": "business_review",
            "audit_status": "not_required",
            "source": "nh6-t03",
            "created_at": utc_now(),
        },
    }


def _await_terminal(client: TestClient, team_uuid: str, task_uuid: str, headers: dict[str, str]) -> dict[str, object]:
    deadline = time.monotonic() + 40
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
        assert response.status_code == 200, response.text
        latest = response.json()
        if latest["status"] in {"succeeded", "failed", "cancelled"}:
            return latest
        time.sleep(0.02)
    return latest


def test_spa_real_dom_nonconstant_profile(tmp_path: Path) -> None:
    app = create_app(browser_settings(tmp_path))
    runtime = app.state.container.browser_runtime
    assert isinstance(runtime, HardenedBrowserRuntime)
    with local_spa_server() as (origin, marker):
        acquired = __import__("asyncio").run(
            app.state.container.workflow_worker.handler._acquire_content(  # noqa: SLF001
                _command(), _source(f"{origin}/spa")
            )
        )
    assert marker in acquired.raw_text
    assert "static shell" not in acquired.raw_text
    assert acquired.evidence["representation_kind"] == "rendered"
    profile = acquired.evidence["browser_profile"]
    assert isinstance(profile, str) and profile.startswith("browser.render.v1;")
    assert profile != "injected-browser-renderer.v1"
    assert acquired.evidence["browser_runtime_uid"] != 0
    assert acquired.evidence["budget_profile"] == "acquisition.v1"


def test_create_app_without_patch_reaches_render(tmp_path: Path) -> None:
    app = create_app(browser_settings(tmp_path))
    container = app.state.container
    runtime = container.browser_runtime
    assert isinstance(runtime, HardenedBrowserRuntime)
    assert container.workflow_worker.handler._browser_fetcher is runtime  # noqa: SLF001
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    headers = {"Authorization": "Bearer nh6-browser"}
    with local_spa_server() as (origin, _marker), TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=headers,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh6-browser"},
            ).status_code
            == 201
        )
        created = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_task(team_uuid, task_uuid, trace_uuid, f"{origin}/spa"),
        )
        assert created.status_code == 201, created.text
        terminal = _await_terminal(client, team_uuid, task_uuid, headers)
    assert terminal["status"] == "succeeded", terminal
    source = inspect.getsource(__import__(__name__, fromlist=["*"]))
    assert "_browser" + "_fetcher =" not in source
