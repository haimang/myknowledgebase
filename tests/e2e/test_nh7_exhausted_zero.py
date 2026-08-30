"""NH7-T09: exhausted_zero is a product disposition, not indexed success."""

from __future__ import annotations

import inspect
import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.models import TaskStatus
from src.contracts.common.time import utc_now
from src.runtime.workflow.runtime_outcome import WorkflowOutcomeMixin
from src.runtime.workflow.runtime_scatter import WorkflowScatterMixin
from tests.e2e.test_registered_api_scatter import _create_team, _settings, _submit, _task_body, _wait_for_terminal


def _headers() -> dict[str, str]:
    return {"Authorization": "Bearer scatter-token"}


def _counts(app, team_uuid: str, task_uuid: str, client: TestClient) -> dict[str, int]:
    async def inspect() -> dict[str, int]:
        async with app.state.container.persistence.transaction() as tx:
            children = await tx.fetchone(
                "SELECT COUNT(*) AS n FROM mkb_executions WHERE team_uuid=? AND task_uuid=? "
                "AND parent_execution_uuid IS NOT NULL",
                (team_uuid, task_uuid),
            )
            items = await tx.fetchone(
                "SELECT COUNT(*) AS n FROM mkb_intake_items WHERE team_uuid=?",
                (team_uuid,),
            )
            revisions = await tx.fetchone(
                "SELECT COUNT(*) AS n FROM mkb_intake_revisions WHERE team_uuid=?",
                (team_uuid,),
            )
            vectors = await tx.fetchone(
                "SELECT COUNT(*) AS n FROM mkb_vector_records WHERE team_uuid=?",
                (team_uuid,),
            )
            proofs = await tx.fetchone(
                "SELECT COUNT(*) AS n FROM mkb_publication_proofs WHERE team_uuid=?",
                (team_uuid,),
            )
        assert children is not None and items is not None and revisions is not None
        assert vectors is not None and proofs is not None
        return {
            "children": int(children["n"]),
            "items": int(items["n"]),
            "revisions": int(revisions["n"]),
            "vectors": int(vectors["n"]),
            "proofs": int(proofs["n"]),
        }

    return client.portal.call(inspect)


def _namespace(app, team_uuid: str, client: TestClient) -> str:
    async def inspect() -> str:
        async with app.state.container.persistence.transaction() as tx:
            row = await tx.fetchone(
                "SELECT namespace_key FROM mkb_vector_namespaces WHERE team_uuid=? AND status='active'",
                (team_uuid,),
            )
        assert row is not None
        return str(row["namespace_key"])

    return client.portal.call(inspect)


def _search(client: TestClient, team_uuid: str, namespace: str, query: str):
    return client.post(
        f"/v1/teams/{team_uuid}/retrieval:search",
        headers=_headers(),
        json={
            "schema_version": "mkb.retrieval.v2",
            "team_uuid": team_uuid,
            "namespace_key": namespace,
            "query": query,
            "filters": {"vector_channel": "original"},
            "return_k": 10,
            "recall_k": 20,
        },
    )


def _disposition_samples(app) -> dict[str, float]:
    values: dict[str, float] = {}
    for (name, labels), amount in app.state.container.metrics._values.items():  # noqa: SLF001
        if name != "mkb_task_result_disposition_total":
            continue
        values[dict(labels)["disposition"]] = amount
    return values


def test_disposition_exhausted_zero_not_indexed_success(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        _create_team(client, team_uuid=team_uuid, headers=_headers())
        task_uuid = _submit(client, team_uuid=team_uuid, headers=_headers(), records=[])
        terminal = _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=task_uuid, headers=_headers())
        assert terminal["status"] == "succeeded", terminal
        assert terminal["result_disposition"] == "exhausted_zero"
        assert terminal["result_disposition"] != "no_change"
        assert not terminal.get("proof_ref")
        assert _counts(app, team_uuid, task_uuid, client) == {
            "children": 0,
            "items": 0,
            "revisions": 0,
            "vectors": 0,
            "proofs": 0,
        }
        samples = _disposition_samples(app)
        assert samples.get("exhausted_zero", 0) >= 1
        assert samples.get("indexed_success", 0) == 0


def test_exhaustion_proof_retrieval_empty(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        _create_team(client, team_uuid=team_uuid, headers=_headers())
        seed_uuid, seed_trace = uuid7(), uuid7()
        seeded = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=_headers(),
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": seed_uuid,
                "trace_uuid": seed_trace,
                "request_intent": "intake.ingest",
                "payload": {
                    "json_prompt_id": "promptB.json.generic",
                    "source": {
                        "source_kind": "inline_payload",
                        "external_key": "nh7-zero-control",
                        "content": "NH7 exhausted zero control sentinel",
                        "realm": "documentation",
                        "type": "article",
                        "channel": "general",
                        "source_name": "nh7-zero-control",
                    },
                },
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": seed_uuid,
                    "trace_uuid": seed_trace,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "nh7-t09",
                    "created_at": utc_now(),
                },
            },
        )
        assert seeded.status_code == 201, seeded.text
        assert (
            _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=seed_uuid, headers=_headers())["status"]
            == "succeeded"
        )
        task_uuid = _submit(client, team_uuid=team_uuid, headers=_headers(), records=[])
        terminal = _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=task_uuid, headers=_headers())
        assert terminal["status"] == "succeeded"
        assert terminal["result_disposition"] == "exhausted_zero"
        namespace = _namespace(app, team_uuid, client)
        found = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers=_headers(),
            json={
                "schema_version": "mkb.retrieval.v2",
                "team_uuid": team_uuid,
                "namespace_key": namespace,
                "query": "Tax fixture reaches",
                "filters": {"realm": "tax_china", "vector_channel": "original"},
                "return_k": 10,
                "recall_k": 20,
            },
        )
        assert found.status_code == 200, found.text
        assert found.json()["results"] == []
        control = _search(client, team_uuid, namespace, "NH7 exhausted zero control sentinel")
        assert control.status_code == 200, control.text
        assert control.json()["results"]
        unproven = _task_body(
            team_uuid=team_uuid,
            task_uuid=uuid7(),
            trace_uuid=uuid7(),
            records=[],
        )
        unproven["payload"]["source"].pop("exhaustion_proof")
        rejected = client.post(f"/v1/teams/{team_uuid}/tasks", headers=_headers(), json=unproven)
        assert rejected.status_code == 422, rejected.text
        assert rejected.json()["error"]["code"] == "SCATTER_EXHAUSTION_PROOF_REQUIRED"


def test_same_fingerprint_replay_same_disposition(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    task_uuid, trace_uuid = uuid7(), uuid7()
    body = _task_body(team_uuid=team_uuid, task_uuid=task_uuid, trace_uuid=trace_uuid, records=[])
    with TestClient(app, raise_server_exceptions=True) as client:
        _create_team(client, team_uuid=team_uuid, headers=_headers())
        first = client.post(f"/v1/teams/{team_uuid}/tasks", headers=_headers(), json=body)
        assert first.status_code == 201, first.text
        terminal = _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=task_uuid, headers=_headers())
        assert terminal["result_disposition"] == "exhausted_zero"
        replay = client.post(f"/v1/teams/{team_uuid}/tasks", headers=_headers(), json=body)
        assert replay.status_code == 200, replay.text
        assert replay.json()["result_disposition"] == "exhausted_zero"
        assert replay.json()["task_uuid"] == task_uuid
        assert _counts(app, team_uuid, task_uuid, client)["children"] == 0


def test_noop_terminal_alone_is_not_product_zero(tmp_path: Path) -> None:
    outcome = inspect.getsource(WorkflowOutcomeMixin._terminalize_execution_tx)
    scatter = inspect.getsource(WorkflowScatterMixin)
    assert "WorkflowTerminalKind.NOOP: ExecutionStatus.SUCCEEDED.value" in outcome
    assert 'result_disposition="exhausted_zero"' not in outcome
    assert 'result_disposition="exhausted_zero"' in scatter
    assert "NOOP cannot materialize exhausted_zero" in outcome
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    task_uuid, trace_uuid = uuid7(), uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        _create_team(client, team_uuid=team_uuid, headers=_headers())
        created = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=_headers(),
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": task_uuid,
                "trace_uuid": trace_uuid,
                "request_intent": "intake.ingest",
                "payload": {
                    "json_prompt_id": "promptB.json.generic",
                    "source": {
                        "source_kind": "inline_payload",
                        "external_key": "nh7-noop-control",
                        "content": "NH7 noop control sentinel",
                        "realm": "documentation",
                        "type": "article",
                        "channel": "general",
                        "source_name": "nh7-noop-control",
                    },
                },
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": task_uuid,
                    "trace_uuid": trace_uuid,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "nh7-t09",
                    "created_at": utc_now(),
                },
            },
        )
        assert created.status_code == 201, created.text
        deadline = time.monotonic() + 30
        latest: dict[str, object] = {}
        while time.monotonic() < deadline:
            latest = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=_headers()).json()
            if latest["status"] in {"succeeded", "failed", "cancelled"}:
                break
            time.sleep(0.02)
        assert latest["status"] == "succeeded", latest
        assert latest.get("result_disposition") in {None, ""}
        assert latest["status"] == TaskStatus.SUCCEEDED.value
        samples = _disposition_samples(app)
        assert samples.get("indexed_success", 0) >= 1
        assert samples.get("exhausted_zero", 0) == 0
