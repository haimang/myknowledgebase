"""NH3-T05: reacquisition follows only a declared finite forward edge."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts.common.errors import ConflictError
from src.contracts.common.ids import stable_digest
from src.contracts.intake.representation import RepresentationObservation
from src.contracts.runtime.models import ProcessCommand
from src.contracts.workflow.models import WorkflowOutcomeSelector
from src.runtime.intake.pipeline import IntakePipeline
from src.runtime.intake.representation_history import (
    PersistenceRepresentationFactReader,
    append_representation_tx,
    prepare_representation_append,
)
from src.workflows.builtin_lsrag import BUILTIN_HTTP_RESOURCE_KIND_WORKFLOW
from tests.integration.test_nh2_selected_output_control import _seed
from tests.integration.test_nh3_fact_history_uow import _running_process
from tests.integration.test_nh3_print_fact import _source_definition


def _command(ids: dict[str, str], process_uuid: str) -> ProcessCommand:
    digest = stable_digest({"reacquire": process_uuid})
    return ProcessCommand(
        schema_version="mkb.process-command.v1",
        team_uuid=ids["team_uuid"],
        task_uuid=ids["task_uuid"],
        trace_uuid=ids["trace_uuid"],
        execution_uuid=ids["execution_uuid"],
        process_uuid=process_uuid,
        step_key="acquire_browser_reacquire",
        process_key="intake.acquire.http_browser",
        process_contract_version="v1",
        fencing_generation=1,
        command_input_digest=digest,
        input_manifest_ref="mkbtest:input:reacquire",
        input_manifest_digest=digest,
        config_snapshot_ref="mkbtest:config:reacquire",
        config_snapshot_digest=digest,
        binding_digest=digest,
    )


async def _declared_path(tmp_path: Path, name: str, browser_body: str):
    reader = PersistenceRepresentationFactReader()
    persistence, runtime, definition, identity, ids = await _seed(
        tmp_path,
        name,
        graph=BUILTIN_HTTP_RESOURCE_KIND_WORKFLOW,
        representation_facts=reader,
    )
    calls: list[str] = []

    def browser(url: str) -> str:
        calls.append(url)
        return browser_body

    pipeline = IntakePipeline(
        persistence,
        None,
        None,
        browser_fetcher=browser,
    )  # type: ignore[arg-type]
    await _source_definition(persistence)
    decode_process = await _running_process(
        persistence, identity, ids, step_key="decode_web_static", suffix=f"{name}-decode"
    )
    first = prepare_representation_append(
        RepresentationObservation(
            team_uuid=ids["team_uuid"],
            execution_uuid=ids["execution_uuid"],
            process_uuid=decode_process,
            step_key="decode_web_static",
            fact_kind="decode",
            capability="intake.decode.text_json_html",
            representation_kind="transferred",
            declared_media_type="text/html",
            detected_media_type="text/html",
            verified_media_type="text/html",
            raw_byte_digest=stable_digest({"raw": "static-shell"}),
            raw_byte_size=31,
            text_layer="not_applicable",
            main_text_presence="absent",
            canonicalizer_key="utf8-lf-nfc",
            canonicalizer_version="v1",
            observer_key="deterministic-html-main-text",
            observer_version="v1",
        )
    )
    async with persistence.transaction() as tx:
        await append_representation_tx(tx, first)
        execution = await tx.fetchone(
            "SELECT * FROM mkb_executions WHERE execution_uuid=?", (ids["execution_uuid"],)
        )
        assert execution is not None
        context = await runtime._typed_route_context_tx(tx, execution)  # noqa: SLF001
    decision = runtime._route_decision(  # noqa: SLF001
        plan=definition,
        execution=execution,
        source_step_key="decode_web_static",
        selector=WorkflowOutcomeSelector.SUCCEEDED,
        route_context=context,
    )
    assert [route.route_key for route in decision["routes"]] == ["decode_static.reacquire_browser"]

    reacquire_process = await _running_process(
        persistence,
        identity,
        ids,
        step_key="acquire_browser_reacquire",
        suffix=f"{name}-browser",
    )
    state = {
        "request_intent": "intake.ingest",
        "payload": {
            "source": {
                "source_kind": "http_resource",
                "external_key": f"{name}-source",
                "url": "https://public.example/reacquire",
                "acquisition_mode": "static",
            }
        },
    }
    material, _, callback = await pipeline._acquire(_command(ids, reacquire_process), state)  # noqa: SLF001
    assert material.envelope["state"]["acquisition_evidence"]["representation_kind"] == "rendered"
    async with persistence.transaction() as tx:
        await callback(tx, {})
    async with persistence.transaction() as tx:
        rows = await tx.fetchall(
            "SELECT step_key,ordinal,capability,representation_kind,representation_path_digest "
            "FROM mkb_acquire_decode_history WHERE execution_uuid=? ORDER BY ordinal",
            (ids["execution_uuid"],),
        )
    return persistence, first, rows, calls


@pytest.mark.asyncio
async def test_declared_static_to_browser_history_len_2(tmp_path: Path) -> None:
    persistence, first, rows, calls = await _declared_path(
        tmp_path, "declared-two", "<main>browser main text</main>"
    )
    try:
        assert calls == ["https://public.example/reacquire"]
        assert [row["ordinal"] for row in rows] == [1, 2]
        assert [row["step_key"] for row in rows] == [
            "decode_web_static",
            "acquire_browser_reacquire",
        ]
        assert rows[-1]["capability"] == "intake.acquire.http_browser"
        assert rows[-1]["representation_kind"] == "rendered"
        with pytest.raises(ConflictError) as raised:
            async with persistence.transaction() as tx:
                await append_representation_tx(tx, first)
        assert raised.value.code == "representation-step-conflict"
        async with persistence.transaction() as tx:
            count = await tx.fetchone(
                "SELECT COUNT(*) AS count FROM mkb_acquire_decode_history"
            )
        assert count == {"count": 2}
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_two_paths_differ_same_path_stable(tmp_path: Path) -> None:
    first_p, _, first_rows, _ = await _declared_path(tmp_path, "stable-a", "<main>same</main>")
    second_p, _, second_rows, _ = await _declared_path(tmp_path, "stable-b", "<main>same</main>")
    different_p, _, different_rows, _ = await _declared_path(
        tmp_path, "different", "<main>different</main>"
    )
    try:
        assert first_rows[-1]["representation_path_digest"] == second_rows[-1]["representation_path_digest"]
        assert first_rows[-1]["representation_path_digest"] != different_rows[-1]["representation_path_digest"]
    finally:
        await first_p.close()
        await second_p.close()
        await different_p.close()


def test_undeclared_edge_409() -> None:
    routes = [
        route
        for route in BUILTIN_HTTP_RESOURCE_KIND_WORKFLOW.routes
        if route.route_key != "decode_static.reacquire_browser"
    ]
    plan = BUILTIN_HTTP_RESOURCE_KIND_WORKFLOW.model_copy(update={"routes": routes})
    from src.runtime.workflow_engine import WorkflowRuntime

    runtime = WorkflowRuntime(None, plan)  # type: ignore[arg-type]
    calls: list[str] = []
    with pytest.raises(ConflictError) as raised:
        runtime._route_decision(  # noqa: SLF001
            plan=plan,
            execution={"workflow_revision_uuid": "revision", "execution_uuid": "execution"},
            source_step_key="decode_web_static",
            selector=WorkflowOutcomeSelector.SUCCEEDED,
            route_context={"media_family": "text", "main_text_presence": "absent"},
        )
    assert raised.value.code == "workflow-reacquire-edge-undeclared"
    assert raised.value.status_code == 409
    assert calls == []


def test_unknown_main_text_does_not_take_browser_edge() -> None:
    from src.runtime.workflow_engine import WorkflowRuntime

    runtime = WorkflowRuntime(None, BUILTIN_HTTP_RESOURCE_KIND_WORKFLOW)  # type: ignore[arg-type]
    decision = runtime._route_decision(  # noqa: SLF001
        plan=BUILTIN_HTTP_RESOURCE_KIND_WORKFLOW,
        execution={"workflow_revision_uuid": "revision", "execution_uuid": "execution"},
        source_step_key="decode_web_static",
        selector=WorkflowOutcomeSelector.SUCCEEDED,
        route_context={"media_family": "text", "main_text_presence": "unknown"},
    )
    assert [route.route_key for route in decision["routes"]] == ["decode_static.web"]
