"""NH2-T03 L2: only the fact-read port may materialize the browser edge."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.contracts.common.ids import stable_digest
from src.contracts.intake.representation import RepresentationRouteFacts
from src.contracts.workflow.models import (
    WorkflowDefinition,
    WorkflowExecutionRole,
    WorkflowGuardDefinition,
    WorkflowOutcomeSelector,
    WorkflowPhaseKey,
    WorkflowPortDefinition,
    WorkflowRequiredness,
    WorkflowRouteDefinition,
    WorkflowRouteKind,
    WorkflowStepDefinition,
    WorkflowStepKind,
    WorkflowTerminalKind,
    WorkflowValueType,
)
from src.runtime.workflow.constants import _TERMINAL_EXECUTION_STATUSES
from tests.integration.test_nh2_selected_output_control import _seed, _seed_candidate


class _FactReader:
    def __init__(self, value: str | None) -> None:
        self.value = value

    async def read_route_facts(self, *, team_uuid: str, execution_uuid: str) -> RepresentationRouteFacts | None:
        del team_uuid, execution_uuid
        if self.value is None:
            return None
        return RepresentationRouteFacts(
            main_text_presence=self.value,  # type: ignore[arg-type]
            observer_key="nh2.test.main-text",
            observer_version="v1",
            fact_digest=stable_digest({"main_text_presence": self.value}),
        )


def _process(step_key: str, process_key: str, *, required: bool) -> WorkflowStepDefinition:
    return WorkflowStepDefinition(
        step_key=step_key,
        step_kind=WorkflowStepKind.PROCESS,
        requiredness=WorkflowRequiredness.REQUIRED if required else WorkflowRequiredness.OPTIONAL,
        process_key=process_key,
        contract_version="v1",
        phase_key=WorkflowPhaseKey.RESOLVING_SOURCE,
        required_proof_kind="acquisition_proof",
        output_ports=[
            WorkflowPortDefinition(
                slot_name="output",
                value_type=WorkflowValueType.LOGICAL_REF,
                schema_ref="mkb.test.representation.v1",
            )
        ],
    )


def _terminal_routes(step_key: str) -> list[WorkflowRouteDefinition]:
    return [
        WorkflowRouteDefinition(
            route_key=f"{step_key}.failed",
            from_step_key=step_key,
            to_step_key="failed",
            route_kind=WorkflowRouteKind.TERMINAL,
            outcome_selector=WorkflowOutcomeSelector.FAILED,
            priority=0,
        ),
        WorkflowRouteDefinition(
            route_key=f"{step_key}.cancelled",
            from_step_key=step_key,
            to_step_key="cancelled",
            route_kind=WorkflowRouteKind.TERMINAL,
            outcome_selector=WorkflowOutcomeSelector.CANCELLED,
            priority=0,
        ),
    ]


def _guard_graph() -> WorkflowDefinition:
    steps = [
        WorkflowStepDefinition(step_key="start", step_kind=WorkflowStepKind.START),
        _process("observe", "test.observe.main-text", required=True),
        _process("browser", "intake.acquire.http_browser", required=False),
        _process("stop", "test.stop-without-browser", required=False),
        WorkflowStepDefinition(
            step_key="succeeded",
            step_kind=WorkflowStepKind.TERMINAL,
            terminal_kind=WorkflowTerminalKind.SUCCESS,
        ),
        WorkflowStepDefinition(
            step_key="failed",
            step_kind=WorkflowStepKind.TERMINAL,
            terminal_kind=WorkflowTerminalKind.FAILURE,
        ),
        WorkflowStepDefinition(
            step_key="cancelled",
            step_kind=WorkflowStepKind.TERMINAL,
            terminal_kind=WorkflowTerminalKind.CANCELLED,
        ),
    ]
    routes = [
        WorkflowRouteDefinition(
            route_key="start.observe",
            from_step_key="start",
            to_step_key="observe",
            route_kind=WorkflowRouteKind.NORMAL,
            outcome_selector=WorkflowOutcomeSelector.ALWAYS,
            priority=0,
        ),
        WorkflowRouteDefinition(
            route_key="observe.browser",
            from_step_key="observe",
            to_step_key="browser",
            route_kind=WorkflowRouteKind.NORMAL,
            outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
            priority=0,
            guard_key="main_text_absent",
        ),
        WorkflowRouteDefinition(
            route_key="observe.stop",
            from_step_key="observe",
            to_step_key="stop",
            route_kind=WorkflowRouteKind.NORMAL,
            outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
            priority=10,
        ),
        WorkflowRouteDefinition(
            route_key="browser.succeeded",
            from_step_key="browser",
            to_step_key="succeeded",
            route_kind=WorkflowRouteKind.TERMINAL,
            outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
            priority=0,
        ),
        WorkflowRouteDefinition(
            route_key="stop.succeeded",
            from_step_key="stop",
            to_step_key="succeeded",
            route_kind=WorkflowRouteKind.TERMINAL,
            outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
            priority=0,
        ),
        *_terminal_routes("observe"),
        *_terminal_routes("browser"),
        *_terminal_routes("stop"),
    ]
    return WorkflowDefinition(
        schema_version="mkb.workflow-definition.v1",
        workflow_key="test.nh2.representation-guard",
        revision_number=1,
        domain_key="ls_rag",
        purpose_key="intake.ingest",
        execution_role=WorkflowExecutionRole.SINGLE_ROOT,
        display_name="NH2 representation guard",
        description="A durable main-text fact selects or refuses one declared browser edge.",
        required_process_keys=["test.observe.main-text"],
        steps=steps,
        routes=routes,
        guards=[
            WorkflowGuardDefinition(
                guard_key="main_text_absent",
                predicate_type="representation_main_text_presence",
                operator="eq",
                expected_value="absent",
            )
        ],
    )


async def _route_case(tmp_path: Path, value: str | None, *, output_claim: str | None = None) -> tuple[int, int]:
    graph = _guard_graph()
    persistence, runtime, _, identity, ids = await _seed(
        tmp_path,
        f"guard-{value or 'missing'}-{output_claim or 'none'}",
        graph=graph,
        representation_facts=_FactReader(value),
    )
    try:
        process_uuid, _ = await _seed_candidate(
            persistence,
            identity,
            ids,
            step_key="observe",
            suffix=f"observe-{value or 'missing'}",
        )
        if output_claim is not None:
            async with persistence.transaction() as tx:
                await tx.execute(
                    "UPDATE mkb_processes SET payload_extra=? WHERE process_uuid=?",
                    (json.dumps({"main_text_presence": output_claim}), process_uuid),
                )
        async with persistence.transaction() as tx:
            execution = await tx.fetchone(
                "SELECT * FROM mkb_executions WHERE execution_uuid=?",
                (ids["execution_uuid"],),
            )
            process = await tx.fetchone("SELECT * FROM mkb_processes WHERE process_uuid=?", (process_uuid,))
            assert execution is not None and process is not None
            assert execution["status"] not in _TERMINAL_EXECUTION_STATUSES
            await runtime._route_after_terminal_process_tx(  # noqa: SLF001
                tx,
                execution,
                process,
                WorkflowOutcomeSelector.SUCCEEDED,
                {},
                None,
            )
        async with persistence.transaction() as tx:
            browser = await tx.fetchone(
                "SELECT COUNT(*) AS count FROM mkb_processes WHERE execution_uuid=? "
                "AND process_key='intake.acquire.http_browser'",
                (ids["execution_uuid"],),
            )
            stop = await tx.fetchone(
                "SELECT COUNT(*) AS count FROM mkb_processes WHERE execution_uuid=? "
                "AND process_key='test.stop-without-browser'",
                (ids["execution_uuid"],),
            )
        assert browser is not None and stop is not None
        return int(browser["count"]), int(stop["count"])
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_missing_or_unknown_main_text_does_not_materialize_browser_acquire(tmp_path: Path) -> None:
    assert await _route_case(tmp_path, None) == (0, 1)
    assert await _route_case(tmp_path, "unknown") == (0, 1)
    assert await _route_case(tmp_path, "present") == (0, 1)
    assert await _route_case(tmp_path, "absent") == (1, 0)
    assert await _route_case(tmp_path, None, output_claim="absent") == (0, 1)
