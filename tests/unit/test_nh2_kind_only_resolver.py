"""NH2-T01: public workflow resolution is source-kind only."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.contracts.api.models import TaskCreateRequest
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import uuid7
from src.persistence.sqlite_port import SqlitePersistence
from src.services.workflow_registry import WorkflowRegistryService
from src.workflows.builtin_lsrag import SOURCE_KIND_WORKFLOW_KEYS
from src.workflows.builtin_scatter import SCATTER_ROOT_WORKFLOW_KEY


async def _registry(tmp_path: Path) -> tuple[SqlitePersistence, WorkflowRegistryService]:
    persistence = SqlitePersistence(tmp_path / "nh2-kind-resolver.sqlite3", Path("src/persistence/migrations"))
    await persistence.migrate()
    registry = WorkflowRegistryService(persistence)
    await registry.bootstrap()
    return persistence, registry


@pytest.mark.asyncio
async def test_four_kinds_resolve_unique_graphs(tmp_path: Path) -> None:
    persistence, registry = await _registry(tmp_path)
    try:
        identities = {
            kind: await registry.resolve_for_source("intake.ingest", kind)
            for kind in (*SOURCE_KIND_WORKFLOW_KEYS, "registered_api")
        }
        assert {kind: value.workflow_key for kind, value in identities.items()} == {
            **SOURCE_KIND_WORKFLOW_KEYS,
            "registered_api": SCATTER_ROOT_WORKFLOW_KEY,
        }
        assert len({identity.compiled_digest for identity in identities.values()}) == 4
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_mode_and_media_do_not_change_workflow_key(tmp_path: Path) -> None:
    persistence, registry = await _registry(tmp_path)
    try:
        http = {
            (await registry.resolve_for_source("intake.ingest", "http_resource", profile)).workflow_key
            for profile in ("http_resource.static", "http_resource.browser", "http_resource.pdf")
        }
        local = {
            (await registry.resolve_for_source("intake.ingest", "local_object", profile)).workflow_key
            for profile in ("local_object", "local_object.pdf", "local_object.image")
        }
        assert http == {SOURCE_KIND_WORKFLOW_KEYS["http_resource"]}
        assert local == {SOURCE_KIND_WORKFLOW_KEYS["local_object"]}
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_unknown_source_kind_is_422(tmp_path: Path) -> None:
    persistence, registry = await _registry(tmp_path)
    try:
        with pytest.raises(MkbError) as raised:
            await registry.resolve_for_source("intake.ingest", "fifth_kind")
        assert raised.value.code == "SOURCE_KIND_INVALID"
        assert raised.value.status_code == 422
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_missing_kind_graph_is_503(tmp_path: Path) -> None:
    persistence, registry = await _registry(tmp_path)
    try:
        async with persistence.transaction() as tx:
            await tx.execute(
                "UPDATE mkb_workflow_registry SET registry_status='disabled' WHERE workflow_key=?",
                (SOURCE_KIND_WORKFLOW_KEYS["http_resource"],),
            )
        with pytest.raises(MkbError) as raised:
            await registry.resolve_for_source("intake.ingest", "http_resource")
        assert raised.value.code == "REGISTRY_NOT_FOUND"
        assert raised.value.status_code == 503
    finally:
        await persistence.close()


def test_public_task_contract_rejects_workflow_key() -> None:
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    with pytest.raises(ValidationError):
        TaskCreateRequest.model_validate(
            {
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": task_uuid,
                "trace_uuid": trace_uuid,
                "request_intent": "intake.ingest",
                "workflow_key": SOURCE_KIND_WORKFLOW_KEYS["inline_payload"],
                "payload": {
                    "json_prompt_id": "promptB.json.generic",
                    "source": {
                        "source_kind": "inline_payload",
                        "realm": "documentation",
                        "type": "article",
                        "channel": "general",
                        "source_name": "test-fixture",
                        "external_key": "nh2",
                        "content": "body",
                    },
                },
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": task_uuid,
                    "trace_uuid": trace_uuid,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "nh2",
                    "created_at": "2026-08-29T00:00:00Z",
                },
            }
        )
