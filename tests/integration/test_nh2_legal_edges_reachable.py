"""NH2-T05: legal kind edges are durable and public resolution never selects old profiles."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.persistence.factory import build_persistence
from src.runtime.workflow_engine import WorkflowRuntime
from src.services.workflow_registry import WorkflowRegistryService
from src.workflows.builtin_lsrag import (
    BUILTIN_INLINE_KIND_WORKFLOW,
    SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS,
    SOURCE_KIND_WORKFLOW_KEYS,
)
from src.workflows.builtin_scatter import SCATTER_ROOT_WORKFLOW_KEY
from tests.integration.test_nh2_selected_output_control import _seed


async def _registry(tmp_path: Path):
    persistence = build_persistence(
        tmp_path / "nh2-legal-edges.sqlite3",
        Path("src/persistence/migrations"),
        backend="turso",
        concurrent_writes_required=False,
        native_vector_required=False,
    )
    await persistence.migrate()
    registry = WorkflowRegistryService(persistence)
    await registry.bootstrap()
    return persistence, registry


@pytest.mark.asyncio
async def test_kind_graphs_declare_all_legal_edges(tmp_path: Path) -> None:
    persistence, registry = await _registry(tmp_path)
    expected = {
        "inline_payload": {"intake.acquire.inline", "intake.decode.text_json_html", "clean.extract.deterministic"},
        "local_object": {
            "intake.acquire.local_object",
            "intake.decode.text_json_html",
            "intake.decode.pdf",
            "clean.extract.deterministic",
            "clean.extract.doc_llm",
            "clean.ocr.local",
            "clean.extract.vision",
            "clean.extract.pdf_text",
            "clean.extract.pdf_llm",
        },
        "http_resource": {
            "intake.acquire.http_static",
            "intake.acquire.http_browser",
            "intake.decode.text_json_html",
            "intake.decode.pdf",
            "clean.extract.web",
            "clean.extract.web_llm",
            "clean.extract.pdf_text",
            "clean.extract.pdf_llm",
            "clean.ocr.local",
        },
    }
    try:
        for kind, required in expected.items():
            identity = await registry.resolve_for_source("intake.ingest", kind)
            async with persistence.transaction() as tx:
                rows = await tx.fetchall(
                    "SELECT process_key FROM mkb_workflow_steps WHERE workflow_revision_uuid=? "
                    "AND step_kind='process'",
                    (identity.workflow_revision_uuid,),
                )
            assert required <= {str(row["process_key"]) for row in rows}
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_former_unselectable_six_not_selected_by_public_resolver(tmp_path: Path) -> None:
    persistence, registry = await _registry(tmp_path)
    old_keys = set(SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS.values()) | {
        "intake.ingest.single.vision-rejected.lsrag.v1",
        "intake.ingest.single.doc-llm.lsrag.v1",
        "intake.ingest.single.http-web-llm.lsrag.v1",
        "intake.ingest.single.http-browser-web-llm.lsrag.v1",
        "intake.ingest.single.local-pdf-understanding.lsrag.v1",
        "intake.ingest.single.http-browser-print-pdf.lsrag.v1",
    }
    try:
        selected = {
            (
                await registry.resolve_for_source("intake.ingest", kind, legacy_profile)
            ).workflow_key
            for kind, legacy_profile in (
                ("inline_payload", "inline_payload"),
                ("local_object", "local_object.pdf"),
                ("http_resource", "http_resource.browser"),
                ("registered_api", "registered_api"),
            )
        }
        assert selected == {*SOURCE_KIND_WORKFLOW_KEYS.values(), SCATTER_ROOT_WORKFLOW_KEY}
        assert not selected & old_keys
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_public_resolve_does_not_require_resolve_by_key(tmp_path: Path) -> None:
    persistence, registry = await _registry(tmp_path)
    try:
        identities = [
            await registry.resolve_for_source("intake.ingest", kind)
            for kind in (*SOURCE_KIND_WORKFLOW_KEYS, "registered_api")
        ]
        assert all(identity.workflow_key for identity in identities)
        assert all(identity.compiled_digest for identity in identities)
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_undeclared_process_key_is_409(tmp_path: Path) -> None:
    persistence, runtime, _, identity, ids = await _seed(
        tmp_path,
        "undeclared-process",
        graph=BUILTIN_INLINE_KIND_WORKFLOW,
    )
    assert isinstance(runtime, WorkflowRuntime)
    now = utc_now()
    process_uuid = uuid7()
    try:
        async with persistence.transaction() as tx:
            step = await tx.fetchone(
                "SELECT workflow_step_uuid FROM mkb_workflow_steps "
                "WHERE workflow_revision_uuid=? AND step_key='acquire_inline'",
                (identity.workflow_revision_uuid,),
            )
            assert step is not None
            await tx.execute(
                "INSERT INTO mkb_processes(process_uuid,team_uuid,execution_uuid,task_uuid,root_execution_uuid,"
                "workflow_step_uuid,step_key,process_key,process_contract_version,materialization_key,requiredness,"
                "process_spec_digest,input_manifest_ref,input_manifest_digest,config_snapshot_ref,config_snapshot_digest,"
                "proof_kind,status,row_revision,available_at,priority_rank,fencing_generation,max_retries,max_recoveries,"
                "backoff_policy_json,dispatch_admitted,created_at,updated_at,payload_extra) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'ready',0,?,0,0,0,0,'{}',1,?,?,'{}')",
                (
                    process_uuid,
                    ids["team_uuid"],
                    ids["execution_uuid"],
                    ids["task_uuid"],
                    ids["execution_uuid"],
                    step["workflow_step_uuid"],
                    "acquire_inline",
                    "clean.extract.vision",
                    "v1",
                    stable_digest({"materialization": "undeclared"}),
                    "required",
                    stable_digest({"spec": "undeclared"}),
                    "mkbtest:input",
                    stable_digest({"input": "undeclared"}),
                    "mkbtest:config",
                    stable_digest({"config": "undeclared"}),
                    "clean_candidate_evidence",
                    now,
                    now,
                    now,
                ),
            )
        with pytest.raises(MkbError) as raised:
            await runtime.claim_next("nh2-undeclared-worker")
        assert raised.value.code == "workflow-process-undeclared"
        assert raised.value.status_code == 409
        async with persistence.transaction() as tx:
            row = await tx.fetchone("SELECT status FROM mkb_processes WHERE process_uuid=?", (process_uuid,))
        assert row == {"status": "ready"}
    finally:
        await persistence.close()
