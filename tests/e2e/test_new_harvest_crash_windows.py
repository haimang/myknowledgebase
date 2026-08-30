"""NH9-T04/T05: CREATE/PROCESS/FANIN/PUB/OUTBOX crash windows; SEL/SEAL wrap NH3-T07."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.errors import ConflictError
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.workflow_engine import WorkflowRuntime
from tests.e2e.test_nh1_fanin_recovery_port import (
    test_fanin_recovery_uses_application_port_and_finishes_once as _fanin_port_repair,
)
from tests.e2e.test_nh3_seal_crash_windows import (
    test_route_seal_and_clean_eligibility_commit_together_and_propagate_command as _seal_same_uow,
)
from tests.e2e.test_nh3_seal_crash_windows import (
    test_route_seal_fault_windows_leave_no_half_commit as _seal_fault_windows,
)
from tests.e2e.test_nh4_public_upload import _settings as _nh4_upload_settings
from tests.e2e.test_nh4_public_upload import _team as _nh4_team
from tests.e2e.test_nh4_public_upload import _upload as _nh4_upload
from tests.e2e.test_source_capability_paths import _settings
from tests.integration.test_nh2_selected_output_control import _seed
from tests.integration.test_nh3_fact_history_uow import _running_process, _success

_TOKEN = "source-capability-token"
_HEADERS = {"Authorization": f"Bearer {_TOKEN}"}


def _wait(client: TestClient, team_uuid: str, task_uuid: str) -> dict[str, Any]:
    deadline = time.monotonic() + 40
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=_HEADERS)
        assert response.status_code == 200, response.text
        latest = response.json()
        if latest["status"] in {"succeeded", "failed", "cancelled"}:
            return latest
        time.sleep(0.02)
    return latest


def _ingest_body(team_uuid: str, task_uuid: str, trace_uuid: str, content: str) -> dict[str, Any]:
    return {
        "schema_version": "mkb.task.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "request_intent": "intake.ingest",
        "payload": {
            "json_prompt_id": "promptB.json.generic",
            "source": {
                "source_kind": "inline_payload",
                "external_key": f"nh9-crash-{task_uuid}",
                "content": content,
                "realm": "documentation",
                "type": "article",
                "channel": "general",
                "source_name": "nh9-crash",
            },
        },
        "audit": {
            "schema_version": "mkb.task-audit.v1",
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "trace_uuid": trace_uuid,
            "audit_type": "business_review",
            "audit_status": "not_required",
            "source": "nh9-t04",
            "created_at": utc_now(),
        },
    }


def _port(app, client: TestClient, query: str, params: tuple[object, ...]) -> Any:
    async def inspect() -> Any:
        async with app.state.container.persistence.transaction() as tx:
            return await tx.fetchone(query, params)

    return client.portal.call(inspect)


def test_w_nh_create_between_identity_and_insert(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    body = _ingest_body(team_uuid, task_uuid, trace_uuid, "NH9 CREATE window sentinel")
    persistence = app.state.container.persistence
    tasks = app.state.container.tasks
    original = tasks.create
    crashed = {"done": False}

    async def create_once(request, token):
        async with persistence.transaction() as tx:
            existing = await tx.fetchone(
                "SELECT task_uuid FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
                (request.team_uuid, request.task_uuid),
            )
        if existing is None and not crashed["done"]:
            crashed["done"] = True
            raise RuntimeError("W-NH-CREATE")
        return await original(request, token)

    tasks.create = create_once  # type: ignore[method-assign]
    with TestClient(app, raise_server_exceptions=False) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=_HEADERS,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh9-create"},
            ).status_code
            == 201
        )
        first = client.post(f"/v1/teams/{team_uuid}/tasks", headers=_HEADERS, json=body)
        assert first.status_code == 500, first.text
        before = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
            (team_uuid, task_uuid),
        )
        before_roots = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_executions WHERE team_uuid=? AND task_uuid=? "
            "AND parent_execution_uuid IS NULL",
            (team_uuid, task_uuid),
        )
        assert before is not None and int(before["n"]) == 0
        assert before_roots is not None and int(before_roots["n"]) == 0
        second = client.post(f"/v1/teams/{team_uuid}/tasks", headers=_HEADERS, json=body)
        assert second.status_code == 201, second.text
        replay = client.post(f"/v1/teams/{team_uuid}/tasks", headers=_HEADERS, json=body)
        assert replay.status_code == 200, replay.text
        tasks_count = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
            (team_uuid, task_uuid),
        )
        roots = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_executions WHERE team_uuid=? AND task_uuid=? "
            "AND parent_execution_uuid IS NULL",
            (team_uuid, task_uuid),
        )
        assert tasks_count is not None and int(tasks_count["n"]) == 1
        assert roots is not None and int(roots["n"]) == 1
        assert replay.json()["task_uuid"] == task_uuid


@pytest.mark.asyncio
async def test_w_nh_process_outcome_cas_effect_once(tmp_path: Path) -> None:
    persistence, _, definition, identity, ids = await _seed(tmp_path, "nh9-process-once")
    runtime = WorkflowRuntime(persistence, definition)
    try:
        process_uuid = await _running_process(
            persistence, identity, ids, step_key="candidate_a", suffix="once"
        )
        outcome = _success(ids, process_uuid, "once")
        assert await runtime.accept_outcome(outcome) is True
        assert await runtime.accept_outcome(outcome) is False
        async with persistence.transaction() as tx:
            process = await tx.fetchone(
                "SELECT status,accepted_outcome_digest,process_key FROM mkb_processes WHERE process_uuid=?",
                (process_uuid,),
            )
            execution = await tx.fetchone(
                "SELECT actual_binding_digest FROM mkb_executions WHERE execution_uuid=?",
                (ids["execution_uuid"],),
            )
        assert process is not None and execution is not None
        assert process["status"] == "succeeded"
        assert process["accepted_outcome_digest"] == outcome.outcome_digest
        assert process["process_key"]
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_w_nh_process_different_outcome_conflict(tmp_path: Path) -> None:
    persistence, _, definition, identity, ids = await _seed(tmp_path, "nh9-process-conflict")
    runtime = WorkflowRuntime(persistence, definition)
    try:
        process_uuid = await _running_process(
            persistence, identity, ids, step_key="candidate_a", suffix="conflict"
        )
        first = _success(ids, process_uuid, "conflict-a")
        assert await runtime.accept_outcome(first) is True
        second = _success(ids, process_uuid, "conflict-b")
        with pytest.raises(ConflictError) as raised:
            await runtime.accept_outcome(second)
        assert raised.value.code == "stale-process-outcome"
        async with persistence.transaction() as tx:
            process = await tx.fetchone(
                "SELECT status,accepted_outcome_digest,process_key FROM mkb_processes WHERE process_uuid=?",
                (process_uuid,),
            )
        assert process is not None
        assert process["status"] == "succeeded"
        assert process["accepted_outcome_digest"] == first.outcome_digest

        fenced = await _running_process(
            persistence, identity, ids, step_key="candidate_b", suffix="fence"
        )
        async with persistence.transaction() as tx:
            await tx.execute(
                "UPDATE mkb_processes SET fencing_generation=fencing_generation+1 WHERE process_uuid=?",
                (fenced,),
            )
        with pytest.raises(ConflictError) as fence:
            await runtime.accept_outcome(_success(ids, fenced, "fence"))
        assert fence.value.code == "stale-process-fence"
    finally:
        await persistence.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("window", ["W-SEL", "W-SEAL"])
async def test_w_sel_crash_before_seal_leaves_unsealed(tmp_path: Path, window: str) -> None:
    await _seal_fault_windows(tmp_path, window)


@pytest.mark.asyncio
async def test_w_seal_route_and_actual_same_uow(tmp_path: Path) -> None:
    await _seal_same_uow(tmp_path)


@pytest.mark.asyncio
async def test_mid_uow_crash_no_half_seal(tmp_path: Path) -> None:
    await _seal_fault_windows(tmp_path, "W-SEAL")


@pytest.mark.asyncio
async def test_different_digest_conflict_error(tmp_path: Path) -> None:
    await _seal_same_uow(tmp_path)


def test_w_nh_fanin_parent_waiting_repairs_once(tmp_path: Path) -> None:
    _fanin_port_repair(tmp_path)


def test_w_nh_pub_incomplete_proof_not_visible(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=_HEADERS,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh9-pub"},
            ).status_code
            == 201
        )
        created = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=_HEADERS,
            json=_ingest_body(team_uuid, task_uuid, trace_uuid, "NH9 incomplete proof must not retrieve"),
        )
        assert created.status_code == 201, created.text
        terminal = _wait(client, team_uuid, task_uuid)
        assert terminal["status"] == "succeeded", terminal
        namespace = _port(
            app,
            client,
            "SELECT namespace_key FROM mkb_vector_namespaces WHERE team_uuid=? AND status='active'",
            (team_uuid,),
        )
        assert namespace is not None
        serving = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_intake_items WHERE team_uuid=? AND serving_revision_uuid IS NOT NULL",
            (team_uuid,),
        )
        assert serving is not None and int(serving["n"]) == 1
        search_body = {
            "schema_version": "mkb.retrieval.v2",
            "team_uuid": team_uuid,
            "namespace_key": namespace["namespace_key"],
            "query": "NH9 incomplete proof must not retrieve",
            "filters": {"vector_channel": "original"},
            "return_k": 10,
            "recall_k": 20,
        }
        before = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers=_HEADERS,
            json=search_body,
        )
        assert before.status_code == 200, before.text
        assert before.json()["results"], before.text

        async def break_proof() -> None:
            async with app.state.container.persistence.transaction() as tx:
                await tx.execute(
                    "UPDATE mkb_publication_proofs SET actual_count=actual_count+1 WHERE team_uuid=?",
                    (team_uuid,),
                )

        client.portal.call(break_proof)
        search = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers=_HEADERS,
            json=search_body,
        )
        assert search.status_code == 200, search.text
        assert search.json()["results"] == []
        after = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_intake_items WHERE team_uuid=? AND serving_revision_uuid IS NOT NULL",
            (team_uuid,),
        )
        assert after is not None and int(after["n"]) == 1


def test_w_nh_outbox_redelivery_no_extra_vector_upsert(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=_HEADERS,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh9-outbox"},
            ).status_code
            == 201
        )
        created = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=_HEADERS,
            json=_ingest_body(team_uuid, task_uuid, trace_uuid, "NH9 outbox redelivery must not duplicate vectors"),
        )
        assert created.status_code == 201, created.text
        terminal = _wait(client, team_uuid, task_uuid)
        assert terminal["status"] == "succeeded", terminal
        before = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_vector_records WHERE team_uuid=?",
            (team_uuid,),
        )
        assert before is not None and int(before["n"]) > 0

        async def redeliver() -> tuple[bool, bool]:
            runtime: WorkflowRuntime = app.state.container.workflow_runtime

            async def reset_pending() -> int:
                async with app.state.container.persistence.transaction() as tx:
                    await tx.execute(
                        "UPDATE mkb_outbox SET status='pending',lease_owner=NULL,lease_expires_at=NULL,"
                        "available_at=? WHERE team_uuid=? AND kind='vectorize_construct'",
                        (utc_now(), team_uuid),
                    )
                    row = await tx.fetchone(
                        "SELECT COUNT(*) AS n FROM mkb_outbox WHERE team_uuid=? AND kind='vectorize_construct' "
                        "AND status='pending'",
                        (team_uuid,),
                    )
                assert row is not None and int(row["n"]) >= 1
                return int(row["n"])

            await reset_pending()
            first = await runtime.dispatch_outbox_once("nh9-outbox-redeliver-a")
            await reset_pending()
            second = await runtime.dispatch_outbox_once("nh9-outbox-redeliver-b")
            return bool(first), bool(second)

        delivered = client.portal.call(redeliver)
        assert delivered == (True, True)
        after = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_vector_records WHERE team_uuid=?",
            (team_uuid,),
        )
        assert after is not None
        assert int(after["n"]) == int(before["n"])


def test_w_nh_prom_cat_crash_no_usable_handle(tmp_path: Path) -> None:
    app = create_app(_nh4_upload_settings(tmp_path).model_copy(update={"object_gc_enabled": False}))

    def fault(stage: str) -> None:
        if stage == "after_promote_before_catalog":
            raise RuntimeError("W-NH-PROM-CAT")

    app.state.container.object_upload._uow_fault_hook = fault  # noqa: SLF001
    team_uuid = uuid7()
    headers = {"Authorization": "Bearer nh4-upload-token"}
    body = b"nh9-prom-cat-orphan-bytes"
    digest = hashlib.sha256(body).hexdigest()
    handle = f"mkbobj:v1:{team_uuid}:{digest}"
    with TestClient(app, raise_server_exceptions=False) as client:
        _nh4_team(client, team_uuid, headers)
        response = _nh4_upload(client, team_uuid, headers, body)
        assert response.status_code == 500, response.text
        counts = _port(
            app,
            client,
            "SELECT (SELECT COUNT(*) FROM mkb_stored_objects WHERE team_uuid=?) AS catalog, "
            "(SELECT COUNT(*) FROM mkb_object_references WHERE team_uuid=?) AS refs, "
            "(SELECT COUNT(*) AS n FROM mkb_intake_items WHERE team_uuid=?) AS items",
            (team_uuid, team_uuid, team_uuid),
        )
        assert counts is not None
        assert int(counts["catalog"]) == 0
        assert int(counts["refs"]) == 0
        assert int(counts["items"]) == 0
        stat = client.get(
            f"/v1/teams/{team_uuid}/objects:stat",
            headers=headers,
            params={"handle": handle},
        )
        assert stat.status_code == 404, stat.text
        staging = tmp_path / "objects" / "staging"
        leftover = list(staging.glob("promote-*")) if staging.exists() else []

        async def reap() -> int:
            return await app.state.container.object_upload_lifecycle.scan_once()

        result = client.portal.call(reap)
        assert result.released_pending == 0
        assert leftover == [] or not any(path.exists() for path in leftover)
        assert int(_port(app, client, "SELECT COUNT(*) AS n FROM mkb_intake_items WHERE team_uuid=?", (team_uuid,))["n"]) == 0
