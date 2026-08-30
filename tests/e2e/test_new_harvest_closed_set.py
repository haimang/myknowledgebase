"""NH9-T03/T07/T09: closed-set fail-loud zeros, scatter query, and legal-cell mega."""

from __future__ import annotations

import ast
import json
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.supply.pdf_parser import build_compressed_pdf_fixture
from tests.e2e.test_nh4_public_upload import _upload
from tests.e2e.test_registered_api_scatter import (
    _create_team as _scatter_team,
)
from tests.e2e.test_registered_api_scatter import (
    _FailOneScatterChild,
)
from tests.e2e.test_registered_api_scatter import (
    _items as _scatter_items,
)
from tests.e2e.test_registered_api_scatter import (
    _records as _scatter_records,
)
from tests.e2e.test_registered_api_scatter import (
    _settings as _scatter_settings,
)
from tests.e2e.test_registered_api_scatter import (
    _submit as _scatter_submit,
)
from tests.e2e.test_registered_api_scatter import (
    _wait_for_terminal as _scatter_wait,
)
from tests.e2e.test_source_capability_paths import _settings

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


def _audit(team_uuid: str, task_uuid: str, trace_uuid: str) -> dict[str, str]:
    return {
        "schema_version": "mkb.task-audit.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "audit_type": "business_review",
        "audit_status": "not_required",
        "source": "nh9-t03",
        "created_at": utc_now(),
    }


def _port(app, client: TestClient, query: str, params: tuple[object, ...]) -> Any:
    async def inspect() -> Any:
        async with app.state.container.persistence.transaction() as tx:
            return await tx.fetchone(query, params)

    return client.portal.call(inspect)


def _namespace(app, client: TestClient, team_uuid: str) -> str:
    row = _port(
        app,
        client,
        "SELECT namespace_key FROM mkb_vector_namespaces WHERE team_uuid=? AND status='active'",
        (team_uuid,),
    )
    assert row is not None
    return str(row["namespace_key"])


def _search(client: TestClient, team_uuid: str, namespace: str | None, query: str, filters: dict[str, str] | None = None):
    body: dict[str, Any] = {
        "schema_version": "mkb.retrieval.v2",
        "team_uuid": team_uuid,
        "query": query,
        "return_k": 10,
        "recall_k": 20,
    }
    if namespace is not None:
        body["namespace_key"] = namespace
    if filters:
        body["filters"] = filters
    return client.post(f"/v1/teams/{team_uuid}/retrieval:search", headers=_HEADERS, json=body)


def _team(client: TestClient, team_uuid: str) -> None:
    created = client.post(
        "/v1/teams",
        headers=_HEADERS,
        json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh9-closed-set"},
    )
    assert created.status_code == 201, created.text


def _seed_namespace(client: TestClient, team_uuid: str) -> str:
    task_uuid, trace_uuid = uuid7(), uuid7()
    created = client.post(
        f"/v1/teams/{team_uuid}/tasks",
        headers=_HEADERS,
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
                    "external_key": f"nh9-control-{task_uuid}",
                    "content": "NH9 closed-set control document zephyrquartz",
                    "realm": "documentation",
                    "type": "article",
                    "channel": "general",
                    "source_name": "nh9-control",
                },
            },
            "audit": _audit(team_uuid, task_uuid, trace_uuid),
        },
    )
    assert created.status_code == 201, created.text
    terminal = _wait(client, team_uuid, task_uuid)
    assert terminal["status"] == "succeeded", terminal
    return task_uuid


def _vectors(app, client: TestClient, team_uuid: str) -> int:
    row = _port(app, client, "SELECT COUNT(*) AS n FROM mkb_vector_records WHERE team_uuid=?", (team_uuid,))
    assert row is not None
    return int(row["n"])


def test_empty_html_clean_empty_zero_hits(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    task_uuid, trace_uuid = uuid7(), uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        _team(client, team_uuid)
        _seed_namespace(client, team_uuid)
        before = _vectors(app, client, team_uuid)
        created = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=_HEADERS,
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
                        "external_key": "nh9-empty-html",
                        "content": "<html><body>   </body></html>",
                        "media_type": "text/html",
                        "realm": "documentation",
                        "type": "article",
                        "channel": "general",
                        "source_name": "nh9-empty",
                    },
                },
                "audit": _audit(team_uuid, task_uuid, trace_uuid),
            },
        )
        assert created.status_code == 201, created.text
        terminal = _wait(client, team_uuid, task_uuid)
        assert terminal["status"] != "succeeded", terminal
        assert _vectors(app, client, team_uuid) == before
        namespace = _namespace(app, client, team_uuid)
        search = _search(
            client, team_uuid, namespace, "zzzz-empty-html-failure", {"realm": "tax_china", "vector_channel": "original"}
        )
        assert search.status_code == 200, search.text
        assert search.json()["results"] == []


def test_empty_pdf_text_zero_hits(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    task_uuid, trace_uuid = uuid7(), uuid7()
    blob = build_compressed_pdf_fixture("")
    with TestClient(app, raise_server_exceptions=True) as client:
        _team(client, team_uuid)
        _seed_namespace(client, team_uuid)
        before = _vectors(app, client, team_uuid)
        uploaded = _upload(
            client,
            team_uuid,
            {**_HEADERS, "content-type": "application/pdf"},
            blob,
            media_type="application/pdf",
        )
        assert uploaded.status_code == 201, uploaded.text
        handle = uploaded.json()["handle"]
        created = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=_HEADERS,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": task_uuid,
                "trace_uuid": trace_uuid,
                "request_intent": "intake.ingest",
                "payload": {
                    "json_prompt_id": "promptB.json.generic",
                    "source": {
                        "source_kind": "local_object",
                        "external_key": "nh9-empty-pdf",
                        "logical_handle": handle,
                        "media_type": "application/pdf",
                        "realm": "documentation",
                        "type": "article",
                        "channel": "general",
                        "source_name": "nh9-empty-pdf",
                    },
                },
                "audit": _audit(team_uuid, task_uuid, trace_uuid),
            },
        )
        assert created.status_code == 201, created.text
        terminal = _wait(client, team_uuid, task_uuid)
        assert terminal["status"] != "succeeded", terminal
        assert _vectors(app, client, team_uuid) == before
        namespace = _namespace(app, client, team_uuid)
        search = _search(
            client, team_uuid, namespace, "zzzz-empty-pdf-failure", {"realm": "tax_china", "vector_channel": "original"}
        )
        assert search.status_code == 200, search.text
        assert search.json()["results"] == []


def test_unknown_filter_key_422_zero_hits(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        _team(client, team_uuid)
        _seed_namespace(client, team_uuid)
        namespace = _namespace(app, client, team_uuid)
        before = _vectors(app, client, team_uuid)
        unknown = _search(client, team_uuid, namespace, "anything", {"not_a_filter": "x"})
        assert unknown.status_code == 422
        assert unknown.json()["error"]["code"] == "RETRIEVE_FILTER_INVALID"
        assert _vectors(app, client, team_uuid) == before


def test_bad_api_member_zero_hits(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    task_uuid, trace_uuid = uuid7(), uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        _team(client, team_uuid)
        created = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=_HEADERS,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": task_uuid,
                "trace_uuid": trace_uuid,
                "request_intent": "intake.ingest",
                "payload": {
                    "json_prompt_id": "promptB.json.generic",
                    "source": {
                        "source_kind": "registered_api",
                        "external_key": "nh9-empty-api",
                        "connector_key": "nh9",
                        "provider": "chinatax",
                        "operation": "get_articles",
                        "definition_version": "v1",
                        "representation": "raw",
                        "records": [],
                    },
                },
                "audit": _audit(team_uuid, task_uuid, trace_uuid),
            },
        )
        assert created.status_code == 422, created.text
        assert created.json()["error"]["code"] == "SCATTER_EXHAUSTION_PROOF_REQUIRED"
        tasks = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
            (team_uuid, task_uuid),
        )
        assert tasks is not None and int(tasks["n"]) == 0
        assert _vectors(app, client, team_uuid) == 0


def test_missing_supply_typed_fail_not_live_dod(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    app = create_app(settings.model_copy(update={"browser_runtime_enabled": False}))
    team_uuid = uuid7()
    task_uuid, trace_uuid = uuid7(), uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        _team(client, team_uuid)
        _seed_namespace(client, team_uuid)
        before = _vectors(app, client, team_uuid)
        created = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=_HEADERS,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": task_uuid,
                "trace_uuid": trace_uuid,
                "request_intent": "intake.ingest",
                "payload": {
                    "json_prompt_id": "promptB.json.generic",
                    "source": {
                        "source_kind": "http_resource",
                        "external_key": "nh9-missing-browser",
                        "url": "https://example.invalid/missing-browser",
                        "acquisition_mode": "browser",
                        "realm": "documentation",
                        "type": "article",
                        "channel": "general",
                        "source_name": "nh9-missing",
                    },
                },
                "audit": _audit(team_uuid, task_uuid, trace_uuid),
            },
        )
        if created.status_code == 201:
            terminal = _wait(client, team_uuid, task_uuid)
            assert terminal["status"] != "succeeded", terminal
            if terminal.get("error"):
                assert terminal["error"]["code"] != "live"
        else:
            assert created.status_code in {422, 503}
            assert created.json()["error"]["code"] in {
                "ACQUISITION_BROWSER_CAPABILITY_UNAVAILABLE",
                "BROWSER_RUNTIME_UNAVAILABLE",
            }
        assert _vectors(app, client, team_uuid) == before
        namespace = _namespace(app, client, team_uuid)
        search = _search(
            client,
            team_uuid,
            namespace,
            "zzzz-missing-browser-failure",
            {"realm": "tax_china", "vector_channel": "original"},
        )
        assert search.status_code == 200, search.text
        assert search.json()["results"] == []


_SCATTER_HEADERS = {"Authorization": "Bearer scatter-token"}


def _scatter_search(
    client: TestClient,
    team_uuid: str,
    namespace: str,
    query: str,
    filters: dict[str, str] | None = None,
):
    body: dict[str, Any] = {
        "schema_version": "mkb.retrieval.v2",
        "team_uuid": team_uuid,
        "namespace_key": namespace,
        "query": query,
        "return_k": 10,
        "recall_k": 20,
    }
    if filters:
        body["filters"] = filters
    return client.post(f"/v1/teams/{team_uuid}/retrieval:search", headers=_SCATTER_HEADERS, json=body)


def _scatter_control(client: TestClient, team_uuid: str, external_key: str, content: str) -> None:
    task_uuid, trace_uuid = uuid7(), uuid7()
    seeded = client.post(
        f"/v1/teams/{team_uuid}/tasks",
        headers=_SCATTER_HEADERS,
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
                    "external_key": external_key,
                    "content": content,
                    "realm": "documentation",
                    "type": "article",
                    "channel": "general",
                    "source_name": external_key,
                },
            },
            "audit": _audit(team_uuid, task_uuid, trace_uuid),
        },
    )
    assert seeded.status_code == 201, seeded.text
    assert _scatter_wait(client, team_uuid=team_uuid, task_uuid=task_uuid, headers=_SCATTER_HEADERS)["status"] == "succeeded"


def test_exhausted_zero_namespace_search_empty(tmp_path: Path) -> None:
    app = create_app(_scatter_settings(tmp_path))
    team_uuid = uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        _scatter_team(client, team_uuid=team_uuid, headers=_SCATTER_HEADERS)
        _scatter_control(client, team_uuid, "nh9-zero-control", "NH9 exhausted zero control sentinel zephyrquartz")
        before = _vectors(app, client, team_uuid)
        namespace = _namespace(app, client, team_uuid)
        task_uuid = _scatter_submit(client, team_uuid=team_uuid, headers=_SCATTER_HEADERS, records=[])
        terminal = _scatter_wait(client, team_uuid=team_uuid, task_uuid=task_uuid, headers=_SCATTER_HEADERS)
        assert terminal["status"] == "succeeded", terminal
        assert terminal["result_disposition"] == "exhausted_zero"
        assert terminal["result_disposition"] != "indexed_success"
        empty = _scatter_search(
            client,
            team_uuid,
            namespace,
            "Tax fixture reaches",
            {"realm": "tax_china", "vector_channel": "original"},
        )
        assert empty.status_code == 200, empty.text
        assert empty.json()["results"] == []
        control = _scatter_search(client, team_uuid, namespace, "zephyrquartz", {"vector_channel": "original"})
        assert control.status_code == 200, control.text
        assert control.json()["results"]
        assert _vectors(app, client, team_uuid) == before


def test_required_child_failed_parent_not_retrievable(tmp_path: Path) -> None:
    app = create_app(_scatter_settings(tmp_path))
    team_uuid = uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        _scatter_team(client, team_uuid=team_uuid, headers=_SCATTER_HEADERS)
        _scatter_control(client, team_uuid, "nh9-child-fail-control", "NH9 child-fail control sentinel zephyrquartz")
        app.state.container.workflow_worker.handler = _FailOneScatterChild(
            app.state.container.workflow_worker.handler
        )
        namespace = _namespace(app, client, team_uuid)
        task_uuid = _scatter_submit(
            client,
            team_uuid=team_uuid,
            headers=_SCATTER_HEADERS,
            records=_scatter_records("nh9-child-fail"),
        )
        failed = _scatter_wait(client, team_uuid=team_uuid, task_uuid=task_uuid, headers=_SCATTER_HEADERS)
        assert failed["status"] == "failed", failed
        assert failed["error"]["code"] == "scatter-required-child-failed"
        items = _scatter_items(client, team_uuid=team_uuid, task_uuid=task_uuid, headers=_SCATTER_HEADERS)
        outcomes = sorted(item["outcome"] for item in items)
        assert outcomes == ["failed", "succeeded"]
        assert any(item.get("publication_ready") for item in items)
        failed_item = next(item for item in items if item["outcome"] == "failed")
        hidden = _scatter_search(
            client,
            team_uuid,
            namespace,
            "nh9-child-fail",
            {
                "intake_item_uuid": str(failed_item["intake_item_uuid"]),
                "vector_channel": "original",
            },
        )
        assert hidden.status_code == 200, hidden.text
        assert hidden.json()["results"] == []
        assert failed["status"] != "succeeded"


def test_bad_member_root_not_succeeded_zero_hits(tmp_path: Path) -> None:
    app = create_app(_scatter_settings(tmp_path))
    team_uuid = uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        _scatter_team(client, team_uuid=team_uuid, headers=_SCATTER_HEADERS)
        _scatter_control(client, team_uuid, "nh9-bad-member-control", "NH9 bad-member control sentinel zephyrquartz")
        before = _vectors(app, client, team_uuid)
        namespace = _namespace(app, client, team_uuid)
        task_uuid, trace_uuid = uuid7(), uuid7()
        created = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=_SCATTER_HEADERS,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": task_uuid,
                "trace_uuid": trace_uuid,
                "request_intent": "intake.ingest",
                "payload": {
                    "json_prompt_id": "promptB.json.generic",
                    "source": {
                        "source_kind": "registered_api",
                        "external_key": "nh9-bad-member",
                        "connector_key": "nh9",
                        "provider": "chinatax",
                        "operation": "get_articles",
                        "definition_version": "v1",
                        "representation": "raw",
                        "records": [{"id": "nh9-empty-clean", "label": "公告", "column": "政策法规"}],
                        "exhaustion_proof": "caller_frozen_records.v1",
                    },
                },
                "audit": _audit(team_uuid, task_uuid, trace_uuid),
            },
        )
        if created.status_code == 201:
            terminal = _scatter_wait(client, team_uuid=team_uuid, task_uuid=task_uuid, headers=_SCATTER_HEADERS)
            assert terminal["status"] != "succeeded", terminal
        else:
            assert created.status_code == 422, created.text
            tasks = _port(
                app,
                client,
                "SELECT COUNT(*) AS n FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
                (team_uuid, task_uuid),
            )
            assert tasks is not None and int(tasks["n"]) == 0
        assert _vectors(app, client, team_uuid) == before
        hidden = _scatter_search(
            client,
            team_uuid,
            namespace,
            "nh9-empty-clean",
            {"realm": "tax_china", "vector_channel": "original"},
        )
        assert hidden.status_code == 200, hidden.text
        assert hidden.json()["results"] == []


def _legal_cells() -> list[dict[str, Any]]:
    manifest = json.loads(Path("tests/fixtures/new_harvest/closed_set_manifest.v1.json").read_text(encoding="utf-8"))
    return list(manifest["legal_cells"])


def _cell_id(cell: dict[str, Any]) -> str:
    if cell.get("kind") == "strategy":
        return str(cell["strategy_key"])
    return f"{cell['provider']}.{cell['operation']}"


def _lane_runners() -> dict[str, Any]:
    from tests.e2e.test_nh7_browser_dom_retrieval import (
        test_web_llm_rewrite_namespace_hit as web_llm_rewrite,
    )
    from tests.e2e.test_nh7_inline_static_retrieval import (
        test_http_static_web_deterministic_namespace_facet_hit as web_deterministic,
    )
    from tests.e2e.test_nh7_inline_static_retrieval import (
        test_inline_doc_deterministic_namespace_facet_hit as doc_deterministic,
    )
    from tests.e2e.test_nh7_multimodal_lanes import (
        test_doc_document_understanding_query as doc_document_understanding,
    )
    from tests.e2e.test_nh7_multimodal_lanes import test_doc_ocr_query as doc_ocr
    from tests.e2e.test_nh7_multimodal_lanes import test_doc_vision_query as doc_vision
    from tests.e2e.test_nh7_multimodal_lanes import (
        test_pdf_document_understanding_query as pdf_document_understanding,
    )
    from tests.e2e.test_nh7_multimodal_lanes import test_pdf_ocr_query as pdf_ocr
    from tests.e2e.test_nh7_pdf_text_retrieval import (
        test_http_pdf_text_layer_namespace_hit as pdf_text_layer,
    )
    from tests.e2e.test_nh7_print_pdf_retrieval import (
        test_print_fact_pdf_clean_namespace_hit as web_browser_print_pdf,
    )
    from tests.e2e.test_nh7_registered_api_retrieval import (
        test_chinatax_member_namespace_hit as chinatax_get_articles,
    )
    from tests.e2e.test_nh7_registered_api_retrieval import (
        test_domain_member_namespace_hit as domain_get_agency_listings,
    )
    from tests.e2e.test_nh7_registered_api_retrieval import (
        test_realestate_member_namespace_hit as realestate_get_listings,
    )
    from tests.e2e.test_nh8_delete_tombstone import (
        test_delete_tombstone_rejects_rebuild_and_search_empty as delete_zero,
    )

    return {
        "doc.deterministic": doc_deterministic,
        "web.deterministic": web_deterministic,
        "web.llm_rewrite": web_llm_rewrite,
        "web.browser_print_pdf": web_browser_print_pdf,
        "pdf.text_layer": pdf_text_layer,
        "pdf.document_understanding": pdf_document_understanding,
        "pdf.ocr": pdf_ocr,
        "doc.document_understanding": doc_document_understanding,
        "doc.ocr": doc_ocr,
        "doc.vision": doc_vision,
        "chinatax.get_articles": chinatax_get_articles,
        "domain.get_agency_listings": domain_get_agency_listings,
        "realestate.get_listings": realestate_get_listings,
        "delete_zero": delete_zero,
    }


@pytest.mark.parametrize("cell", _legal_cells(), ids=_cell_id)
def test_every_legal_knowledge_cell_namespace_facet_proof(tmp_path: Path, cell: dict[str, Any]) -> None:
    source = Path("tests/e2e/test_new_harvest_closed_set.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    assigned = [
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and node.attr == "_browser_fetcher"
        and isinstance(node.ctx, ast.Store)
    ]
    assert assigned == []
    cell_id = _cell_id(cell)
    runners = _lane_runners()
    runner = runners.get(cell_id)
    assert runner is not None, f"legal cell {cell_id} has no NH7 lane to join"
    runner(tmp_path)
    if cell_id == "doc.deterministic":
        lifecycle = tmp_path / "lifecycle-delete"
        lifecycle.mkdir()
        runners["delete_zero"](lifecycle)
