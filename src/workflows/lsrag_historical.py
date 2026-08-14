"""Historical immutable workflow revisions for registry compatibility tests."""

from __future__ import annotations

from typing import Final

from src.contracts.workflow.models import (
    WorkflowDefinition,
)
from src.workflows.lsrag_definition import (
    _pre_ns1_metadata_refresh_execution_document,
)


def _historical_v2_execution_plan() -> WorkflowDefinition:
    """Return the exact pre-S07-refresh graph for pinned revision-2 work."""

    document = _pre_ns1_metadata_refresh_execution_document()
    document["revision_number"] = 2
    return WorkflowDefinition.model_validate(document)


def _historical_v1_execution_plan() -> WorkflowDefinition:
    """Return the exact pre-S09 immutable declaration for pinned executions.

    Revision 2's index-rebuild capability is deliberately additive.  A
    persisted revision-1 Execution carries its own compiled digest, so the
    runtime must retain this reviewed graph rather than reinterpreting its
    remaining work through the active graph.  Deriving the declaration here
    keeps the shared v1 nodes literal while documenting every v2-only delta in
    one place.  In particular, the original acquire start route priority was
    zero; merely deleting the new higher-priority route would not restore the
    old compiled plan.
    """

    document = _historical_v2_execution_plan().model_dump()
    document["revision_number"] = 1
    document["context_slots"] = [
        slot for slot in document["context_slots"] if slot["slot_name"] != "index_rebuild_scope"
    ]
    document["required_process_keys"] = [key for key in document["required_process_keys"] if key != "index.rebuild"]
    document["steps"] = [step for step in document["steps"] if step["step_key"] != "index_rebuild"]
    document["routes"] = [
        {
            **route,
            **({"priority": 0} if route["route_key"] == "start.to_acquire" else {}),
        }
        for route in document["routes"]
        if route["from_step_key"] != "index_rebuild"
        and route["to_step_key"] != "index_rebuild"
        and route["guard_key"] != "request_intent_index_rebuild"
    ]
    document["bindings"] = [
        binding for binding in document["bindings"] if binding["target_step_key"] != "index_rebuild"
    ]
    document["guards"] = [guard for guard in document["guards"] if guard["guard_key"] != "request_intent_index_rebuild"]
    return WorkflowDefinition.model_validate(document)


HISTORICAL_SINGLE_INTAKE_LSRAG_WORKFLOW_V1: Final[WorkflowDefinition] = _historical_v1_execution_plan()

HISTORICAL_SINGLE_INTAKE_LSRAG_WORKFLOW_V2: Final[WorkflowDefinition] = _historical_v2_execution_plan()

BUILTIN_EXECUTION_COMPATIBILITY_WORKFLOWS: Final[tuple[WorkflowDefinition, ...]] = (
    HISTORICAL_SINGLE_INTAKE_LSRAG_WORKFLOW_V1,
    HISTORICAL_SINGLE_INTAKE_LSRAG_WORKFLOW_V2,
)
