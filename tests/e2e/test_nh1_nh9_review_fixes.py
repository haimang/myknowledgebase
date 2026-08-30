"""Review-fix coverage for NH1–NH9 first-round verified findings."""

from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.storage.models import ObjectHandle
from tests.e2e.test_nh4_public_upload import _settings as _nh4_settings
from tests.e2e.test_nh4_public_upload import _team
from tests.unit.test_nh8_intent_applicability import _HEADERS, _audit, _counts, _settings


def _ingest_inline(client: TestClient, team_uuid: str, content: str, external_key: str) -> dict[str, object]:
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
    assert created.status_code == 201, created.text
    deadline = __import__("time").monotonic() + 30
    latest: dict[str, object] = {}
    while __import__("time").monotonic() < deadline:
        latest = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=_HEADERS).json()
        if latest["status"] in {"succeeded", "failed", "cancelled"}:
            return latest
        __import__("time").sleep(0.02)
    return latest


def test_illegal_inline_pdf_ocr_rejected_before_task_insert(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=_HEADERS,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "review-strategy"},
            ).status_code
            == 201
        )
        response = client.post(
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
                        "external_key": "illegal-strategy",
                        "content": "inline text must not run pdf.ocr",
                        "clean_strategy": "pdf.ocr",
                        "realm": "documentation",
                        "type": "article",
                        "channel": "general",
                        "source_name": "illegal-strategy",
                    },
                },
                "audit": _audit(team_uuid, task_uuid, trace_uuid),
            },
        )
        assert response.status_code == 422, response.text
        assert response.json()["error"]["code"] == "CLEAN_STRATEGY_KIND_INCOMPATIBLE"
        assert _counts(app, team_uuid, task_uuid, client) == (0, 0)


def test_metadata_rejects_system_owned_keys_before_task_insert(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid, ingest_uuid, ingest_trace = uuid7(), uuid7(), uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=_HEADERS,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "review-meta"},
            ).status_code
            == 201
        )
        created = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=_HEADERS,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": ingest_uuid,
                "trace_uuid": ingest_trace,
                "request_intent": "intake.ingest",
                "payload": {
                    "json_prompt_id": "promptB.json.generic",
                    "source": {
                        "source_kind": "inline_payload",
                        "external_key": "meta-system",
                        "content": "system owned semantic keys stay derived",
                        "realm": "documentation",
                        "type": "article",
                        "channel": "general",
                        "source_name": "meta-system",
                    },
                },
                "audit": _audit(team_uuid, ingest_uuid, ingest_trace),
            },
        )
        assert created.status_code == 201, created.text
        deadline = __import__("time").monotonic() + 30
        latest = {}
        while __import__("time").monotonic() < deadline:
            latest = client.get(f"/v1/teams/{team_uuid}/tasks/{ingest_uuid}", headers=_HEADERS).json()
            if latest["status"] in {"succeeded", "failed", "cancelled"}:
                break
            __import__("time").sleep(0.02)
        assert latest["status"] == "succeeded", latest

        async def item() -> str:
            async with app.state.container.persistence.transaction() as tx:
                row = await tx.fetchone(
                    "SELECT intake_item_uuid FROM mkb_intake_items WHERE team_uuid=?",
                    (team_uuid,),
                )
            assert row is not None
            return str(row["intake_item_uuid"])

        item_uuid = client.portal.call(item)
        meta_uuid, meta_trace = uuid7(), uuid7()
        response = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=_HEADERS,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": meta_uuid,
                "trace_uuid": meta_trace,
                "request_intent": "intake.update_metadata",
                "payload": {
                    "intake_item_uuid": item_uuid,
                    "semantics": {"canonical_content": "ATTACKER-CONTENT"},
                },
                "audit": _audit(team_uuid, meta_uuid, meta_trace),
            },
        )
        assert response.status_code == 422, response.text
        assert response.json()["error"]["code"] == "METADATA_SEMANTIC_SYSTEM_OWNED"
        assert _counts(app, team_uuid, meta_uuid, client) == (0, 0)


def test_mapping_retrieval_v2_is_accepted(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=_HEADERS,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "review-ret"},
            ).status_code
            == 201
        )
        request = {
            "schema_version": "mkb.retrieval.v2",
            "team_uuid": team_uuid,
            "namespace_key": "missing-namespace",
            "query": "review mapping v2",
            "return_k": 5,
            "recall_k": 10,
        }
        normalised = app.state.container.retrieval._normalise_request(request)
        assert normalised.schema_version == "mkb.retrieval.v2"


def test_gc_reconcile_restores_quarantined_live_catalog(tmp_path: Path) -> None:
    settings = _nh4_settings(tmp_path)
    app = create_app(settings)
    team_uuid = uuid7()
    headers = {"Authorization": "Bearer nh4-upload-token"}
    body = b"quarantine-restore-bytes"
    with TestClient(app, raise_server_exceptions=True) as client:
        _team(client, team_uuid, headers)
        uploaded = client.post(
            f"/v1/teams/{team_uuid}/objects:upload",
            headers={**headers, "content-type": "text/plain"},
            content=body,
        )
        assert uploaded.status_code == 201, uploaded.text
        handle = ObjectHandle(value=uploaded.json()["handle"])
        storage = app.state.container.storage

        async def quarantine() -> bool:
            return bool(await storage.quarantine_object(team_uuid, handle))

        assert client.portal.call(quarantine) is True
        digest = hashlib.sha256(body).hexdigest()
        assert not (storage.root / "objects" / team_uuid / "sha256" / digest[:2] / digest[2:4] / digest).exists()

        async def reconcile() -> int:
            return int(await app.state.container.object_gc.reconcile_quarantine())

        assert client.portal.call(reconcile) == 1
        assert storage.root.joinpath("objects", team_uuid, "sha256", digest[:2], digest[2:4], digest).read_bytes() == body


def test_sealed_actual_sql_rewrite_is_aborted(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=_HEADERS,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "review-seal"},
            ).status_code
            == 201
        )
        terminal = _ingest_inline(client, team_uuid, "sealed actual cannot be rewritten", "seal-rewrite")
        assert terminal["status"] == "succeeded", terminal

        async def rewrite() -> str | None:
            async with app.state.container.persistence.transaction() as tx:
                try:
                    await tx.execute(
                        "UPDATE mkb_executions SET actual_binding_digest=? "
                        "WHERE team_uuid=? AND actual_binding_state='sealed'",
                        ("f" * 64, team_uuid),
                    )
                except Exception as exc:
                    return type(exc).__name__ + ":" + str(exc)
            return None

        error = client.portal.call(rewrite)
        assert error is not None
        assert "sealed" in error.casefold() or "abort" in error.casefold() or "constraint" in error.casefold()


def test_health_required_omits_disabled_multimodal() -> None:
    from api.app import _health_required
    from src.runtime.config import Settings
    from src.runtime.health import HealthAggregator

    required = _health_required(
        Settings(runtime_supply_readiness_required=True, multimodal_enabled=False)
    )
    assert "supply_s11_multimodal" not in required
    assert "supply_pdf_parse" in required
    enabled = _health_required(
        Settings(runtime_supply_readiness_required=True, multimodal_enabled=True)
    )
    assert enabled == HealthAggregator.REQUIRED


def test_inline_kind_declares_rebuild_guards() -> None:
    from src.workflows.kind_family import BUILTIN_INLINE_KIND_WORKFLOW

    keys = {guard.guard_key for guard in BUILTIN_INLINE_KIND_WORKFLOW.guards}
    assert "request_intent_rebuild" in keys
    assert "request_intent_metadata_refresh" in keys
