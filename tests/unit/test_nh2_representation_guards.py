"""NH2-T03 L1: registered main-text facts remain eq-only and fail closed."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.contracts.workflow.models import WorkflowDefinition, WorkflowGuardDefinition
from src.runtime.workflow.runtime_materialize import WorkflowMaterializeMixin
from tests.unit.test_nh1_selected_output_control import selected_output_test_graph


def _plan_and_route() -> tuple[WorkflowDefinition, object]:
    payload = selected_output_test_graph().model_dump()
    payload["guards"] = [
        WorkflowGuardDefinition(
            guard_key="main_text_absent",
            predicate_type="representation_main_text_presence",
            operator="eq",
            expected_value="absent",
        ).model_dump()
    ]
    route = next(item for item in payload["routes"] if item["route_key"] == "candidate_a.merge")
    route["guard_key"] = "main_text_absent"
    plan = WorkflowDefinition.model_validate(payload)
    return plan, next(item for item in plan.routes if item.route_key == "candidate_a.merge")


def _matches(context: dict[str, object]) -> tuple[bool, dict[str, bool]]:
    plan, route = _plan_and_route()
    runtime = WorkflowMaterializeMixin.__new__(WorkflowMaterializeMixin)
    results: dict[str, bool] = {}
    return runtime._guard_matches(plan, route, context, results), results


def test_present_does_not_take_browser_edge() -> None:
    matched, results = _matches({"main_text_presence": "present"})
    assert not matched
    assert results == {"main_text_absent": False}


def test_absent_takes_declared_browser_edge() -> None:
    matched, results = _matches({"main_text_presence": "absent"})
    assert matched
    assert results == {"main_text_absent": True}


def test_unknown_fail_closed() -> None:
    matched, results = _matches({"main_text_presence": "unknown"})
    assert not matched
    assert results == {"main_text_absent": False}


def test_missing_key_fail_closed() -> None:
    matched, results = _matches({})
    assert not matched
    assert results == {"main_text_absent": False}


def test_non_eq_operator_rejected() -> None:
    with pytest.raises(ValidationError):
        WorkflowGuardDefinition.model_validate(
            {
                "guard_key": "main_text_absent",
                "predicate_type": "representation_main_text_presence",
                "operator": "ne",
                "expected_value": "absent",
            }
        )


def test_unknown_predicate_type_rejected() -> None:
    with pytest.raises(ValidationError):
        WorkflowGuardDefinition.model_validate(
            {
                "guard_key": "llm_quality",
                "predicate_type": "llm_quality_score",
                "operator": "eq",
                "expected_value": "good",
            }
        )


def test_guard_ignores_process_output_json() -> None:
    matched, results = _matches({"process_output": {"main_text_presence": "absent"}})
    assert not matched
    assert results == {"main_text_absent": False}
