"""NH2-T04: bounded graph compiler rejects cycles and ambiguous wiring."""

from __future__ import annotations

from copy import deepcopy

import pytest

from src.contracts.workflow.models import WorkflowDefinition, WorkflowRouteDefinition
from src.workflows.kind_family import BUILTIN_HTTP_RESOURCE_KIND_WORKFLOW
from tests.unit.test_nh1_selected_output_control import selected_output_test_graph


def test_self_edge_rejected() -> None:
    payload = selected_output_test_graph().model_dump()
    route = deepcopy(payload["routes"][0])
    route["route_key"] = "candidate_a.self"
    route["from_step_key"] = route["to_step_key"] = "candidate_a"
    payload["routes"].append(route)
    with pytest.raises(ValueError, match="cannot be self-edges"):
        WorkflowDefinition.model_validate(payload)


def test_cycle_rejected() -> None:
    payload = selected_output_test_graph().model_dump()
    payload["routes"].append(
        WorkflowRouteDefinition.model_validate(
            {
                **payload["routes"][2],
                "route_key": "merge.back-to-a",
                "from_step_key": "merge",
                "to_step_key": "candidate_a",
                "priority": 1,
            }
        ).model_dump()
    )
    with pytest.raises(ValueError, match="must be acyclic"):
        WorkflowDefinition.model_validate(payload)


def test_duplicate_step_key_rejected() -> None:
    payload = selected_output_test_graph().model_dump()
    duplicate = deepcopy(payload["steps"][1])
    duplicate["process_key"] = "test.duplicate"
    payload["steps"].append(duplicate)
    with pytest.raises(ValueError, match="step_key values must be unique"):
        WorkflowDefinition.model_validate(payload)


def test_duplicate_binding_to_same_port_rejected() -> None:
    payload = selected_output_test_graph().model_dump()
    duplicate = deepcopy(payload["bindings"][0])
    duplicate["source_step_key"] = "candidate_b"
    payload["bindings"].append(duplicate)
    with pytest.raises(ValueError, match="only one binding"):
        WorkflowDefinition.model_validate(payload)


def test_reacquire_requires_distinct_step_keys() -> None:
    graph = WorkflowDefinition.model_validate(BUILTIN_HTTP_RESOURCE_KIND_WORKFLOW.model_dump())
    acquire_steps = [
        step.step_key
        for step in graph.steps
        if step.process_key is not None and step.process_key.startswith("intake.acquire")
    ]
    assert len(acquire_steps) >= 3
    assert len(acquire_steps) == len(set(acquire_steps))
    assert any(
        route.from_step_key == "decode_web_static" and route.to_step_key == "acquire_browser_reacquire"
        for route in graph.routes
    )
