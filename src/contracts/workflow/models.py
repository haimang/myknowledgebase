"""Strict, static contracts for declarative Workflow definitions.

These schemas describe a versioned workflow graph and its logical data slots.
They intentionally do not describe execution state, leases, retries, delivery,
or side effects.  Those concerns belong to the S03 engine and its ports, not
to a definition loaded from :mod:`src.workflows`.
"""

from __future__ import annotations

from collections import defaultdict
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from src.contracts.common.models import StrictModel

_KEY_PATTERN = r"^[a-z][a-z0-9_.-]{0,127}$"
_SCHEMA_REF_PATTERN = r"^mkb\.[a-z][a-z0-9_.-]{0,127}$"
_CONTRACT_VERSION_PATTERN = r"^[a-z0-9][a-z0-9_.-]{0,63}$"

WorkflowKey = Annotated[str, Field(pattern=_KEY_PATTERN, min_length=1, max_length=128)]
SchemaRef = Annotated[str, Field(pattern=_SCHEMA_REF_PATTERN, min_length=1, max_length=132)]
ContractVersion = Annotated[str, Field(pattern=_CONTRACT_VERSION_PATTERN, min_length=1, max_length=64)]


class WorkflowStepKind(StrEnum):
    START = "start"
    PROCESS = "process"
    CONTROL = "control"
    JOIN = "join"
    TERMINAL = "terminal"


class WorkflowRequiredness(StrEnum):
    REQUIRED = "required"
    OPTIONAL = "optional"


class WorkflowTerminalKind(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    NOOP = "noop"


class WorkflowRouteKind(StrEnum):
    NORMAL = "normal"
    BRANCH = "branch"
    FAN_OUT = "fan_out"
    JOIN = "join"
    TERMINAL = "terminal"


class WorkflowOutcomeSelector(StrEnum):
    ALWAYS = "always"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class WorkflowJoinMode(StrEnum):
    NONE = "none"
    ALL_REQUIRED = "all_required"
    ALL_TERMINAL = "all_terminal"


class WorkflowPhaseKey(StrEnum):
    RESOLVING_SOURCE = "resolving_source"
    CLEANING = "cleaning"
    SCATTERING = "scattering"
    PREFLIGHT_ADMISSION = "preflight_admission"
    AWAITING_HUMAN_REVIEW = "awaiting_human_review"
    STRUCTURIZING = "structurizing"
    CONSTRUCTING = "constructing"
    VECTORIZING_INDEXING = "vectorizing_indexing"
    VALIDATING_PUBLICATION = "validating_publication"
    FAN_IN = "fan_in"
    UPDATING_METADATA = "updating_metadata"
    DEACTIVATING = "deactivating"
    DELETING = "deleting"
    PURGING = "purging"
    REBUILDING_INDEX = "rebuilding_index"


class WorkflowValueType(StrEnum):
    LOGICAL_REF = "logical_ref"
    DIGEST = "digest"
    PROOF = "proof"


class WorkflowMultiplicity(StrEnum):
    ONE = "one"
    MANY = "many"


class WorkflowBindingSourceKind(StrEnum):
    EXECUTION_CONTEXT = "execution_context"
    INTAKE_SNAPSHOT = "intake_snapshot"
    PRIOR_OUTPUT = "prior_output"
    CONTROL_VALUE = "control_value"
    REGISTRY_REF = "registry_ref"


class WorkflowExecutionRole(StrEnum):
    SINGLE_ROOT = "single_root"
    SCATTER_ROOT = "scatter_root"
    SCATTER_CHILD = "scatter_child"


class WorkflowPortDefinition(StrictModel):
    """A logical, typed slot; never a filesystem or object-store location."""

    slot_name: WorkflowKey
    value_type: WorkflowValueType
    schema_ref: SchemaRef
    required: bool = True
    multiplicity: WorkflowMultiplicity = WorkflowMultiplicity.ONE


class WorkflowStepDefinition(StrictModel):
    """One static graph node and, for process nodes, its capability reference."""

    step_key: WorkflowKey
    step_kind: WorkflowStepKind
    requiredness: WorkflowRequiredness = WorkflowRequiredness.REQUIRED
    process_key: WorkflowKey | None = None
    contract_version: ContractVersion | None = None
    phase_key: WorkflowPhaseKey | None = None
    required_proof_kind: WorkflowKey | None = None
    control_key: WorkflowKey | None = None
    input_ports: list[WorkflowPortDefinition] = Field(default_factory=list)
    output_ports: list[WorkflowPortDefinition] = Field(default_factory=list)
    terminal_kind: WorkflowTerminalKind | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> WorkflowStepDefinition:
        input_names = [port.slot_name for port in self.input_ports]
        output_names = [port.slot_name for port in self.output_ports]
        if len(input_names) != len(set(input_names)):
            raise ValueError("input port names must be unique within a step")
        if len(output_names) != len(set(output_names)):
            raise ValueError("output port names must be unique within a step")

        if self.step_kind is WorkflowStepKind.PROCESS:
            if self.process_key is None or self.contract_version is None:
                raise ValueError("process steps require process_key and contract_version")
            if self.phase_key is None:
                raise ValueError("process steps require a registered phase_key")
            if self.required_proof_kind is None:
                raise ValueError("process steps require a proof kind")
            if self.control_key is not None or self.terminal_kind is not None:
                raise ValueError("process steps cannot define control_key or terminal_kind")
            if not self.output_ports:
                raise ValueError("process steps require at least one output port")
            return self

        if self.step_kind is WorkflowStepKind.CONTROL:
            if self.control_key is None:
                raise ValueError("control steps require a registered control_key")
            if self.phase_key is None:
                raise ValueError("control steps require a registered phase_key")
            if any(
                value is not None
                for value in (self.process_key, self.contract_version, self.required_proof_kind, self.terminal_kind)
            ):
                raise ValueError("control steps cannot declare a process capability, proof, or terminal kind")
            return self

        if self.step_kind is WorkflowStepKind.TERMINAL:
            if self.requiredness is not WorkflowRequiredness.REQUIRED:
                raise ValueError("terminal steps must be required")
            if self.terminal_kind is None:
                raise ValueError("terminal steps require terminal_kind")
            if self.input_ports or self.output_ports or self.phase_key is not None:
                raise ValueError("terminal steps cannot declare ports or a phase")
            if any(
                value is not None
                for value in (self.process_key, self.contract_version, self.required_proof_kind, self.control_key)
            ):
                raise ValueError("terminal steps cannot declare process or control fields")
            return self

        if self.step_kind is WorkflowStepKind.START:
            if self.requiredness is not WorkflowRequiredness.REQUIRED:
                raise ValueError("the start step must be required")
            if self.input_ports or self.output_ports or self.phase_key is not None:
                raise ValueError("start steps cannot declare ports or a phase")
            if any(
                value is not None
                for value in (
                    self.process_key,
                    self.contract_version,
                    self.required_proof_kind,
                    self.control_key,
                    self.terminal_kind,
                )
            ):
                raise ValueError("start steps cannot declare process, control, or terminal fields")
            return self

        if any(
            value is not None
            for value in (
                self.process_key,
                self.contract_version,
                self.required_proof_kind,
                self.control_key,
                self.terminal_kind,
            )
        ):
            raise ValueError("join steps cannot declare process, control, proof, or terminal fields")
        if self.phase_key is not None:
            raise ValueError("join steps cannot declare a phase")
        return self


class WorkflowRouteDefinition(StrictModel):
    """A deterministic edge.  Its selector is a registered outcome, not code."""

    route_key: WorkflowKey
    from_step_key: WorkflowKey
    to_step_key: WorkflowKey
    route_kind: WorkflowRouteKind
    outcome_selector: WorkflowOutcomeSelector
    priority: Annotated[int, Field(ge=0, le=1_000_000)]
    guard_key: WorkflowKey | None = None
    join_mode: WorkflowJoinMode = WorkflowJoinMode.NONE

    @model_validator(mode="after")
    def validate_shape(self) -> WorkflowRouteDefinition:
        if self.route_kind is WorkflowRouteKind.JOIN and self.join_mode is WorkflowJoinMode.NONE:
            raise ValueError("join routes require a non-none join_mode")
        if self.route_kind is not WorkflowRouteKind.JOIN and self.join_mode is not WorkflowJoinMode.NONE:
            raise ValueError("only join routes may declare a join_mode")
        # A start route may use a registered, bounded guard to select one of
        # several statically declared command paths.  It is still an
        # ``always`` outcome because no Process outcome exists before the
        # first step; the guard is a fixed selector, not an expression surface.
        return self


class WorkflowGuardDefinition(StrictModel):
    """A bounded, registered admission guard with no free expression surface."""

    guard_key: WorkflowKey
    predicate_type: Literal["registered_admission_result", "registered_request_intent"]
    operator: Literal["eq"]
    expected_value: Annotated[str, Field(min_length=1, max_length=128)]
    failure_disposition: Literal["route_false"] = "route_false"

    @model_validator(mode="after")
    def validate_registered_value(self) -> WorkflowGuardDefinition:
        allowed = {
            "registered_admission_result": {"auto_admitted", "human_review_required", "rejected"},
            "registered_request_intent": {
                "intake.ingest",
                "intake.rebuild",
                "intake.update_metadata",
                "intake.deactivate",
                "intake.reactivate",
                "intake.delete",
                "index.rebuild",
            },
        }
        if self.expected_value not in allowed[self.predicate_type]:
            raise ValueError("guard expected_value is not registered for its predicate")
        return self


class WorkflowBindingDefinition(StrictModel):
    """Connect one process/control input slot to a typed logical source."""

    target_step_key: WorkflowKey
    target_slot_name: WorkflowKey
    source_kind: WorkflowBindingSourceKind
    source_ref_key: WorkflowKey | None = None
    source_step_key: WorkflowKey | None = None
    source_port_name: WorkflowKey | None = None

    @model_validator(mode="after")
    def validate_source_shape(self) -> WorkflowBindingDefinition:
        if self.source_kind is WorkflowBindingSourceKind.PRIOR_OUTPUT:
            if self.source_step_key is None or self.source_port_name is None:
                raise ValueError("prior_output bindings require source_step_key and source_port_name")
            if self.source_ref_key is not None:
                raise ValueError("prior_output bindings cannot declare source_ref_key")
            return self

        if self.source_ref_key is None:
            raise ValueError("non-prior-output bindings require source_ref_key")
        if self.source_step_key is not None or self.source_port_name is not None:
            raise ValueError("non-prior-output bindings cannot declare a source step or port")
        return self


class WorkflowDefinition(StrictModel):
    """The loadable, immutable declaration for one workflow revision."""

    schema_version: Literal["mkb.workflow-definition.v1"]
    workflow_key: WorkflowKey
    revision_number: Annotated[int, Field(ge=1)]
    domain_key: Literal["ls_rag"]
    purpose_key: Literal["intake.ingest", "intake.rebuild"]
    execution_role: WorkflowExecutionRole
    display_name: Annotated[str, Field(min_length=1, max_length=256)]
    description: Annotated[str, Field(min_length=1, max_length=2048)]
    context_slots: list[WorkflowPortDefinition] = Field(default_factory=list)
    required_process_keys: list[WorkflowKey] = Field(min_length=1)
    steps: list[WorkflowStepDefinition] = Field(min_length=3)
    routes: list[WorkflowRouteDefinition] = Field(min_length=2)
    bindings: list[WorkflowBindingDefinition] = Field(default_factory=list)
    guards: list[WorkflowGuardDefinition] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_definition(self) -> WorkflowDefinition:
        steps_by_key = self._unique_steps()
        context_by_slot = self._unique_context_slots()
        guards_by_key = self._unique_guards()
        self._validate_required_process_keys(steps_by_key)
        adjacency = self._validate_routes(steps_by_key, guards_by_key)
        self._validate_graph(steps_by_key, adjacency)
        self._validate_bindings(steps_by_key, context_by_slot, adjacency)
        return self

    def _unique_steps(self) -> dict[str, WorkflowStepDefinition]:
        steps_by_key = {step.step_key: step for step in self.steps}
        if len(steps_by_key) != len(self.steps):
            raise ValueError("step_key values must be unique")
        starts = [step for step in self.steps if step.step_kind is WorkflowStepKind.START]
        if len(starts) != 1:
            raise ValueError("a workflow definition must contain exactly one start step")
        if not any(step.step_kind is WorkflowStepKind.TERMINAL for step in self.steps):
            raise ValueError("a workflow definition must contain at least one terminal step")
        return steps_by_key

    def _unique_context_slots(self) -> dict[str, WorkflowPortDefinition]:
        context_by_slot = {slot.slot_name: slot for slot in self.context_slots}
        if len(context_by_slot) != len(self.context_slots):
            raise ValueError("context slot names must be unique")
        return context_by_slot

    def _unique_guards(self) -> dict[str, WorkflowGuardDefinition]:
        guards_by_key = {guard.guard_key: guard for guard in self.guards}
        if len(guards_by_key) != len(self.guards):
            raise ValueError("guard_key values must be unique")
        return guards_by_key

    def _validate_required_process_keys(self, steps_by_key: dict[str, WorkflowStepDefinition]) -> None:
        if len(set(self.required_process_keys)) != len(self.required_process_keys):
            raise ValueError("required_process_keys must not contain duplicates")
        required_process_keys = {
            step.process_key
            for step in steps_by_key.values()
            if step.step_kind is WorkflowStepKind.PROCESS and step.requiredness is WorkflowRequiredness.REQUIRED
        }
        if None in required_process_keys:
            raise ValueError("required process steps must declare process_key")
        if set(self.required_process_keys) != required_process_keys:
            raise ValueError("required_process_keys must exactly match required process steps")

    def _validate_routes(
        self,
        steps_by_key: dict[str, WorkflowStepDefinition],
        guards_by_key: dict[str, WorkflowGuardDefinition],
    ) -> dict[str, set[str]]:
        route_keys = {route.route_key for route in self.routes}
        if len(route_keys) != len(self.routes):
            raise ValueError("route_key values must be unique")

        adjacency: dict[str, set[str]] = defaultdict(set)
        selector_priorities: set[tuple[str, WorkflowOutcomeSelector, int]] = set()
        referenced_guards: set[str] = set()
        start_key = next(step.step_key for step in steps_by_key.values() if step.step_kind is WorkflowStepKind.START)
        for route in self.routes:
            if route.from_step_key not in steps_by_key or route.to_step_key not in steps_by_key:
                raise ValueError("routes must reference steps from the same workflow definition")
            if route.from_step_key == route.to_step_key:
                raise ValueError("workflow routes cannot be self-edges")
            if steps_by_key[route.from_step_key].step_kind is WorkflowStepKind.TERMINAL:
                raise ValueError("terminal steps cannot have outgoing routes")

            priority_key = (route.from_step_key, route.outcome_selector, route.priority)
            if priority_key in selector_priorities:
                raise ValueError("route priority must be deterministic for each step and outcome selector")
            selector_priorities.add(priority_key)

            target_is_terminal = steps_by_key[route.to_step_key].step_kind is WorkflowStepKind.TERMINAL
            if (route.route_kind is WorkflowRouteKind.TERMINAL) != target_is_terminal:
                raise ValueError("terminal routes must target a terminal step, and only terminal routes may do so")
            if (
                route.outcome_selector is WorkflowOutcomeSelector.ALWAYS
                and route.guard_key is not None
                and route.from_step_key != start_key
            ):
                raise ValueError("only a start route may guard an always selector")
            if route.guard_key is not None:
                if route.guard_key not in guards_by_key:
                    raise ValueError("route guard_key must reference a registered guard")
                referenced_guards.add(route.guard_key)
            adjacency[route.from_step_key].add(route.to_step_key)

        if set(guards_by_key) != referenced_guards:
            raise ValueError("every registered guard must be referenced by a route")
        return adjacency

    def _validate_graph(
        self,
        steps_by_key: dict[str, WorkflowStepDefinition],
        adjacency: dict[str, set[str]],
    ) -> None:
        start_key = next(step.step_key for step in self.steps if step.step_kind is WorkflowStepKind.START)
        if not any(route.from_step_key == start_key for route in self.routes):
            raise ValueError("the start step must have an outgoing route")

        visit_state: dict[str, Literal["visiting", "visited"]] = {}

        def visit(step_key: str) -> None:
            state = visit_state.get(step_key)
            if state == "visiting":
                raise ValueError("workflow route graph must be acyclic")
            if state == "visited":
                return
            visit_state[step_key] = "visiting"
            for target_key in adjacency.get(step_key, set()):
                visit(target_key)
            visit_state[step_key] = "visited"

        visit(start_key)
        unreachable = sorted(set(steps_by_key) - set(visit_state))
        if unreachable:
            raise ValueError(f"workflow steps must be reachable from start: {', '.join(unreachable)}")

        reverse_adjacency: dict[str, set[str]] = defaultdict(set)
        for source_key, target_keys in adjacency.items():
            for target_key in target_keys:
                reverse_adjacency[target_key].add(source_key)
        terminal_keys = {step.step_key for step in self.steps if step.step_kind is WorkflowStepKind.TERMINAL}
        can_reach_terminal = set(terminal_keys)
        pending = list(terminal_keys)
        while pending:
            target_key = pending.pop()
            for source_key in reverse_adjacency.get(target_key, set()):
                if source_key not in can_reach_terminal:
                    can_reach_terminal.add(source_key)
                    pending.append(source_key)
        missing_terminal_coverage = sorted(set(steps_by_key) - can_reach_terminal)
        if missing_terminal_coverage:
            raise ValueError("every workflow step must reach a terminal: " + ", ".join(missing_terminal_coverage))

        routes_by_step: dict[str, set[WorkflowOutcomeSelector]] = defaultdict(set)
        for route in self.routes:
            routes_by_step[route.from_step_key].add(route.outcome_selector)
        for step in self.steps:
            if step.step_kind in {WorkflowStepKind.PROCESS, WorkflowStepKind.CONTROL}:
                missing_outcomes = {
                    WorkflowOutcomeSelector.SUCCEEDED,
                    WorkflowOutcomeSelector.FAILED,
                    WorkflowOutcomeSelector.CANCELLED,
                } - routes_by_step[step.step_key]
                if missing_outcomes:
                    rendered = ", ".join(sorted(outcome.value for outcome in missing_outcomes))
                    raise ValueError(f"{step.step_key} lacks terminal coverage for: {rendered}")

    def _validate_bindings(
        self,
        steps_by_key: dict[str, WorkflowStepDefinition],
        context_by_slot: dict[str, WorkflowPortDefinition],
        adjacency: dict[str, set[str]],
    ) -> None:
        input_ports = {(step.step_key, port.slot_name): port for step in self.steps for port in step.input_ports}
        output_ports = {(step.step_key, port.slot_name): port for step in self.steps for port in step.output_ports}
        bound_targets: set[tuple[str, str]] = set()
        for binding in self.bindings:
            target_step = steps_by_key.get(binding.target_step_key)
            if target_step is None or target_step.step_kind not in {
                WorkflowStepKind.PROCESS,
                WorkflowStepKind.CONTROL,
            }:
                raise ValueError("bindings may target only process or control input ports")
            target_key = (binding.target_step_key, binding.target_slot_name)
            target_port = input_ports.get(target_key)
            if target_port is None:
                raise ValueError("binding target_slot_name must name a declared input port")
            if target_key in bound_targets:
                raise ValueError("each workflow input port may have only one binding")
            bound_targets.add(target_key)

            if binding.source_kind is WorkflowBindingSourceKind.PRIOR_OUTPUT:
                source_key = (binding.source_step_key, binding.source_port_name)
                source_port = output_ports.get(source_key)
                if source_port is None:
                    raise ValueError("prior_output bindings must reference a declared output port")
                if not self._can_reach(binding.source_step_key, binding.target_step_key, adjacency):
                    raise ValueError("prior_output bindings must come from an upstream step")
                self._validate_compatible_ports(source_port, target_port)
                continue

            source_port = context_by_slot.get(binding.source_ref_key or "")
            if binding.source_kind is WorkflowBindingSourceKind.EXECUTION_CONTEXT:
                if source_port is None:
                    raise ValueError("execution_context bindings must reference a declared context slot")
                self._validate_compatible_ports(source_port, target_port)
            elif binding.source_kind in {
                WorkflowBindingSourceKind.INTAKE_SNAPSHOT,
                WorkflowBindingSourceKind.CONTROL_VALUE,
                WorkflowBindingSourceKind.REGISTRY_REF,
            }:
                if source_port is not None:
                    self._validate_compatible_ports(source_port, target_port)

        for input_key, port in input_ports.items():
            if port.required and input_key not in bound_targets:
                raise ValueError(f"required input port is unbound: {input_key[0]}.{input_key[1]}")

    @staticmethod
    def _can_reach(source_key: str | None, target_key: str, adjacency: dict[str, set[str]]) -> bool:
        if source_key is None or source_key == target_key:
            return False
        visited: set[str] = set()
        pending = [source_key]
        while pending:
            current_key = pending.pop()
            if current_key == target_key:
                return True
            if current_key in visited:
                continue
            visited.add(current_key)
            pending.extend(adjacency.get(current_key, set()) - visited)
        return False

    @staticmethod
    def _validate_compatible_ports(source: WorkflowPortDefinition, target: WorkflowPortDefinition) -> None:
        if (
            source.value_type is not target.value_type
            or source.schema_ref != target.schema_ref
            or source.multiplicity is not target.multiplicity
        ):
            raise ValueError("binding source and target ports must have identical type, schema_ref, and multiplicity")


__all__ = [
    "ContractVersion",
    "SchemaRef",
    "WorkflowBindingDefinition",
    "WorkflowBindingSourceKind",
    "WorkflowDefinition",
    "WorkflowExecutionRole",
    "WorkflowGuardDefinition",
    "WorkflowJoinMode",
    "WorkflowMultiplicity",
    "WorkflowOutcomeSelector",
    "WorkflowPhaseKey",
    "WorkflowPortDefinition",
    "WorkflowRequiredness",
    "WorkflowRouteDefinition",
    "WorkflowRouteKind",
    "WorkflowStepDefinition",
    "WorkflowStepKind",
    "WorkflowTerminalKind",
    "WorkflowValueType",
]
