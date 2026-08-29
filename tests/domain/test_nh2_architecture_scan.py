"""NH2-T07: source-kind graph and bounded-control architecture redlines."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.contracts.workflow.models import WorkflowGuardDefinition, WorkflowStepKind
from src.runtime.workflow.runtime_materialize import WorkflowMaterializeMixin
from src.workflows.kind_family import BUILTIN_KIND_WORKFLOWS
from src.workflows.lsrag_shared_tail import shared_tail_digest


def test_public_api_has_no_workflow_key_parameter() -> None:
    for path in (Path("src/contracts/api"), Path("api/public")):
        for source_path in path.rglob("*.py"):
            tree = ast.parse(source_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                    assert node.target.id != "workflow_key", source_path
                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                    assert all(argument.arg != "workflow_key" for argument in node.args.args), source_path


def test_zero_action_branch_in_runtime_surface() -> None:
    token = "action" + "_branch"
    for root in (Path("src"), Path("api"), Path("intake")):
        for path in root.rglob("*.py"):
            assert token not in path.read_text(encoding="utf-8"), path


def test_guard_operator_eq_only_no_free_expression() -> None:
    assert WorkflowGuardDefinition.model_fields["operator"].annotation.__args__ == ("eq",)
    for predicate in ("jsonata", "javascript", "sql", "feel", "when"):
        with pytest.raises(ValidationError):
            WorkflowGuardDefinition.model_validate(
                {
                    "guard_key": "unsafe_expression",
                    "predicate_type": predicate,
                    "operator": "eq",
                    "expected_value": "true",
                }
            )


def test_three_kind_graphs_share_one_tail_source() -> None:
    digests = {shared_tail_digest(graph) for graph in BUILTIN_KIND_WORKFLOWS}
    assert len(BUILTIN_KIND_WORKFLOWS) == 3
    assert len(digests) == 1
    assert all(step.step_kind is not WorkflowStepKind.JOIN for graph in BUILTIN_KIND_WORKFLOWS for step in graph.steps)
    source = Path("src/workflows/kind_family.py").read_text(encoding="utf-8")
    assert "shared_tail_components" in source
    assert "_source_profile_workflow" not in source


def test_selected_output_not_aliased_to_scatter_join() -> None:
    source = inspect.getsource(WorkflowMaterializeMixin._enter_selected_output_tx)
    assert "_enter_" + "scatter_children_join_tx" not in source
    assert "waiting_reason" not in source
