"""NH1-T04 L1: selected-output fits the existing single-binding graph fence."""

from __future__ import annotations

from copy import deepcopy

import pytest

from src.contracts.workflow.models import (
    WorkflowBindingDefinition,
    WorkflowBindingSourceKind,
    WorkflowDefinition,
    WorkflowExecutionRole,
    WorkflowMultiplicity,
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
from src.runtime.workflow.selected_output import selected_output_compiled_digest


def _port(name: str, *, required: bool = True) -> WorkflowPortDefinition:
    return WorkflowPortDefinition(
        slot_name=name,
        value_type=WorkflowValueType.LOGICAL_REF,
        schema_ref="mkb.test.clean-candidate.v1",
        required=required,
        multiplicity=WorkflowMultiplicity.ONE,
    )


def _candidate(step_key: str) -> WorkflowStepDefinition:
    return WorkflowStepDefinition(
        step_key=step_key,
        step_kind=WorkflowStepKind.PROCESS,
        requiredness=WorkflowRequiredness.OPTIONAL,
        process_key=f"test.{step_key}",
        contract_version="v1",
        phase_key=WorkflowPhaseKey.CLEANING,
        required_proof_kind="clean_candidate",
        output_ports=[_port("candidate")],
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


def selected_output_test_graph() -> WorkflowDefinition:
    steps = [
        WorkflowStepDefinition(step_key="start", step_kind=WorkflowStepKind.START),
        _candidate("candidate_a"),
        _candidate("candidate_b"),
        WorkflowStepDefinition(
            step_key="merge",
            step_kind=WorkflowStepKind.CONTROL,
            control_key="selected_output",
            control_version="selected-output.v1",
            phase_key=WorkflowPhaseKey.CLEANING,
            input_ports=[_port("candidate_a", required=False), _port("candidate_b", required=False)],
            output_ports=[_port("selected")],
        ),
        WorkflowStepDefinition(
            step_key="tail",
            step_kind=WorkflowStepKind.PROCESS,
            process_key="test.publication_tail",
            contract_version="v1",
            phase_key=WorkflowPhaseKey.VALIDATING_PUBLICATION,
            required_proof_kind="publication_proof",
            input_ports=[_port("selected")],
            output_ports=[_port("published")],
        ),
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
            route_key="start.candidate_a",
            from_step_key="start",
            to_step_key="candidate_a",
            route_kind=WorkflowRouteKind.FAN_OUT,
            outcome_selector=WorkflowOutcomeSelector.ALWAYS,
            priority=0,
        ),
        WorkflowRouteDefinition(
            route_key="start.candidate_b",
            from_step_key="start",
            to_step_key="candidate_b",
            route_kind=WorkflowRouteKind.FAN_OUT,
            outcome_selector=WorkflowOutcomeSelector.ALWAYS,
            priority=1,
        ),
        WorkflowRouteDefinition(
            route_key="candidate_a.merge",
            from_step_key="candidate_a",
            to_step_key="merge",
            route_kind=WorkflowRouteKind.NORMAL,
            outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
            priority=0,
        ),
        WorkflowRouteDefinition(
            route_key="candidate_b.merge",
            from_step_key="candidate_b",
            to_step_key="merge",
            route_kind=WorkflowRouteKind.NORMAL,
            outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
            priority=0,
        ),
        WorkflowRouteDefinition(
            route_key="merge.tail",
            from_step_key="merge",
            to_step_key="tail",
            route_kind=WorkflowRouteKind.NORMAL,
            outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
            priority=0,
        ),
        WorkflowRouteDefinition(
            route_key="tail.succeeded",
            from_step_key="tail",
            to_step_key="succeeded",
            route_kind=WorkflowRouteKind.TERMINAL,
            outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
            priority=0,
        ),
        *_terminal_routes("candidate_a"),
        *_terminal_routes("candidate_b"),
        *_terminal_routes("merge"),
        *_terminal_routes("tail"),
    ]
    bindings = [
        WorkflowBindingDefinition(
            target_step_key="merge",
            target_slot_name="candidate_a",
            source_kind=WorkflowBindingSourceKind.PRIOR_OUTPUT,
            source_step_key="candidate_a",
            source_port_name="candidate",
        ),
        WorkflowBindingDefinition(
            target_step_key="merge",
            target_slot_name="candidate_b",
            source_kind=WorkflowBindingSourceKind.PRIOR_OUTPUT,
            source_step_key="candidate_b",
            source_port_name="candidate",
        ),
        WorkflowBindingDefinition(
            target_step_key="tail",
            target_slot_name="selected",
            source_kind=WorkflowBindingSourceKind.PRIOR_OUTPUT,
            source_step_key="merge",
            source_port_name="selected",
        ),
    ]
    return WorkflowDefinition(
        schema_version="mkb.workflow-definition.v1",
        workflow_key="test.nh1.selected-output",
        revision_number=1,
        domain_key="ls_rag",
        purpose_key="intake.ingest",
        execution_role=WorkflowExecutionRole.SINGLE_ROOT,
        display_name="NH1 selected-output spike",
        description="Two optional candidates converge through one CONTROL output and one publication tail.",
        required_process_keys=["test.publication_tail"],
        steps=steps,
        routes=routes,
        bindings=bindings,
    )


def test_optional_candidate_ports_compile_with_single_tail() -> None:
    graph = selected_output_test_graph()
    merge = next(step for step in graph.steps if step.step_key == "merge")
    assert [port.required for port in merge.input_ports] == [False, False]
    assert sum(step.process_key == "test.publication_tail" for step in graph.steps) == 1
    assert len([binding for binding in graph.bindings if binding.target_step_key == "tail"]) == 1


def test_each_input_still_has_only_one_binding() -> None:
    graph = selected_output_test_graph().model_dump()
    duplicate = deepcopy(graph["bindings"][0])
    duplicate["source_step_key"] = "candidate_b"
    graph["bindings"].append(duplicate)
    with pytest.raises(ValueError, match="each workflow input port may have only one binding"):
        WorkflowDefinition.model_validate(graph)


def test_compiled_digest_includes_control_version() -> None:
    v1 = selected_output_compiled_digest(("candidate_a", "candidate_b"))
    v2 = selected_output_compiled_digest(
        ("candidate_a", "candidate_b"),
        control_version="selected-output.v2",
    )
    assert len(v1) == 64
    assert v1 != v2


def test_cycle_is_rejected() -> None:
    graph = selected_output_test_graph().model_dump()
    graph["routes"].append(
        WorkflowRouteDefinition(
            route_key="merge.back-to-a",
            from_step_key="merge",
            to_step_key="candidate_a",
            route_kind=WorkflowRouteKind.NORMAL,
            outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
            priority=1,
        ).model_dump()
    )
    with pytest.raises(ValueError, match="acyclic"):
        WorkflowDefinition.model_validate(graph)
