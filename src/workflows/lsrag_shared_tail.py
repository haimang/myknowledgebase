"""Single source for the accepted-clean through publication LS-RAG tail."""

from __future__ import annotations

from dataclasses import dataclass

from src.contracts.common.ids import stable_digest
from src.contracts.workflow.models import (
    WorkflowBindingDefinition,
    WorkflowDefinition,
    WorkflowGuardDefinition,
    WorkflowRouteDefinition,
    WorkflowStepDefinition,
    WorkflowStepKind,
)
from src.workflows.lsrag_definition import BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW

SHARED_TAIL_STEP_KEYS = frozenset(
    {
        "seal_candidate_set",
        "preflight_validate",
        "accept_snapshot",
        "human_review",
        "transcribe_markdown",
        "structurize",
        "construct",
        "vectorize",
        "validate_publication",
        "succeeded",
        "failed",
        "cancelled",
    }
)


@dataclass(frozen=True, slots=True)
class SharedTailComponents:
    steps: tuple[WorkflowStepDefinition, ...]
    routes: tuple[WorkflowRouteDefinition, ...]
    bindings: tuple[WorkflowBindingDefinition, ...]
    guards: tuple[WorkflowGuardDefinition, ...]
    required_process_keys: tuple[str, ...]


def shared_tail_components() -> SharedTailComponents:
    """Return deep immutable copies so all kind graphs consume one source."""

    base = BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW
    steps = tuple(
        step.model_copy(deep=True)
        for step in base.steps
        if step.step_key in SHARED_TAIL_STEP_KEYS
    )
    adjusted_steps = []
    for step in steps:
        if step.step_key == "preflight_validate":
            step = step.model_copy(
                update={
                    "input_ports": [
                        port
                        for port in step.input_ports
                        if port.slot_name != "acquisition_evidence"
                    ]
                },
                deep=True,
            )
        adjusted_steps.append(step)
    routes = tuple(
        route.model_copy(deep=True)
        for route in base.routes
        if route.from_step_key in SHARED_TAIL_STEP_KEYS
        and route.to_step_key in SHARED_TAIL_STEP_KEYS
    )
    bindings = tuple(
        binding.model_copy(deep=True)
        for binding in base.bindings
        if binding.target_step_key in SHARED_TAIL_STEP_KEYS
        and (
            binding.source_step_key is None
            or binding.source_step_key in SHARED_TAIL_STEP_KEYS
        )
    )
    referenced_guards = {route.guard_key for route in routes if route.guard_key is not None}
    guards = tuple(
        guard.model_copy(deep=True)
        for guard in base.guards
        if guard.guard_key in referenced_guards
    )
    required_process_keys = tuple(
        step.process_key
        for step in adjusted_steps
        if step.step_kind is WorkflowStepKind.PROCESS and step.process_key is not None
    )
    return SharedTailComponents(
        steps=tuple(adjusted_steps),
        routes=routes,
        bindings=bindings,
        guards=guards,
        required_process_keys=required_process_keys,
    )


def shared_tail_digest(definition: WorkflowDefinition) -> str:
    """Digest only the shared generation/publication subgraph."""

    return stable_digest(
        {
            "steps": [
                step.model_dump(mode="json")
                for step in definition.steps
                if step.step_key in SHARED_TAIL_STEP_KEYS
            ],
            "routes": [
                route.model_dump(mode="json")
                for route in definition.routes
                if route.from_step_key in SHARED_TAIL_STEP_KEYS
                and route.to_step_key in SHARED_TAIL_STEP_KEYS
            ],
            "bindings": [
                binding.model_dump(mode="json")
                for binding in definition.bindings
                if binding.target_step_key in SHARED_TAIL_STEP_KEYS
                and (
                    binding.source_step_key is None
                    or binding.source_step_key in SHARED_TAIL_STEP_KEYS
                )
            ],
        }
    )


__all__ = [
    "SHARED_TAIL_STEP_KEYS",
    "SharedTailComponents",
    "shared_tail_components",
    "shared_tail_digest",
]
