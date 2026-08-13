"""Current built-in single-intake LS-RAG workflow definition."""

from __future__ import annotations

from typing import Final

from src.contracts.workflow.models import (
    WorkflowBindingDefinition,
    WorkflowBindingSourceKind,
    WorkflowDefinition,
    WorkflowExecutionRole,
    WorkflowGuardDefinition,
    WorkflowOutcomeSelector,
    WorkflowPhaseKey,
    WorkflowPortDefinition,
    WorkflowRouteDefinition,
    WorkflowRouteKind,
    WorkflowStepDefinition,
    WorkflowStepKind,
    WorkflowTerminalKind,
    WorkflowValueType,
)


def _ref(slot_name: str, schema_ref: str) -> WorkflowPortDefinition:
    return WorkflowPortDefinition(
        slot_name=slot_name,
        value_type=WorkflowValueType.LOGICAL_REF,
        schema_ref=schema_ref,
    )


def _optional_ref(slot_name: str, schema_ref: str) -> WorkflowPortDefinition:
    return WorkflowPortDefinition(
        slot_name=slot_name,
        value_type=WorkflowValueType.LOGICAL_REF,
        schema_ref=schema_ref,
        required=False,
    )


def _process(
    *,
    step_key: str,
    process_key: str,
    phase_key: WorkflowPhaseKey,
    proof_kind: str,
    input_ports: list[WorkflowPortDefinition],
    output_ports: list[WorkflowPortDefinition],
) -> WorkflowStepDefinition:
    return WorkflowStepDefinition(
        step_key=step_key,
        step_kind=WorkflowStepKind.PROCESS,
        process_key=process_key,
        contract_version="v1",
        phase_key=phase_key,
        required_proof_kind=proof_kind,
        input_ports=input_ports,
        output_ports=output_ports,
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


_STEPS = [
    WorkflowStepDefinition(step_key="start", step_kind=WorkflowStepKind.START),
    _process(
        step_key="index_rebuild",
        process_key="index.rebuild",
        phase_key=WorkflowPhaseKey.REBUILDING_INDEX,
        proof_kind="index_rebuild_proof",
        input_ports=[_ref("index_rebuild_scope", "mkb.index.rebuild-scope.v1")],
        output_ports=[_ref("index_rebuild_receipt", "mkb.index.rebuild-receipt.v1")],
    ),
    _process(
        step_key="acquire",
        process_key="intake.acquire.inline",
        phase_key=WorkflowPhaseKey.RESOLVING_SOURCE,
        proof_kind="acquisition_evidence",
        input_ports=[_ref("source_descriptor", "mkb.intake.source-descriptor.v1")],
        output_ports=[_ref("acquisition_evidence", "mkb.intake.acquisition-evidence.v1")],
    ),
    _process(
        step_key="decode",
        process_key="intake.decode.text_json_html",
        phase_key=WorkflowPhaseKey.RESOLVING_SOURCE,
        proof_kind="decode_evidence",
        input_ports=[_ref("acquisition_evidence", "mkb.intake.acquisition-evidence.v1")],
        output_ports=[_ref("decoded_representation", "mkb.intake.decoded-representation.v1")],
    ),
    _process(
        step_key="clean",
        process_key="clean.extract.deterministic",
        phase_key=WorkflowPhaseKey.CLEANING,
        proof_kind="clean_candidate_evidence",
        input_ports=[_ref("decoded_representation", "mkb.intake.decoded-representation.v1")],
        output_ports=[_ref("clean_candidate", "mkb.intake.clean-candidate.v1")],
    ),
    _process(
        step_key="seal_candidate_set",
        process_key="intake.collection.seal",
        phase_key=WorkflowPhaseKey.PREFLIGHT_ADMISSION,
        proof_kind="candidate_set_seal_proof",
        input_ports=[_ref("clean_candidate", "mkb.intake.clean-candidate.v1")],
        output_ports=[_ref("candidate_set_seal", "mkb.intake.candidate-set-seal.v1")],
    ),
    _process(
        step_key="preflight_validate",
        process_key="intake.preflight_validate",
        phase_key=WorkflowPhaseKey.PREFLIGHT_ADMISSION,
        proof_kind="preflight_outcome_evidence",
        input_ports=[
            _ref("acquisition_evidence", "mkb.intake.acquisition-evidence.v1"),
            _ref("candidate_set_seal", "mkb.intake.candidate-set-seal.v1"),
            _ref("clean_candidate", "mkb.intake.clean-candidate.v1"),
        ],
        output_ports=[_ref("preflight_outcome", "mkb.intake.preflight-outcome.v1")],
    ),
    _process(
        step_key="accept_snapshot",
        process_key="intake.accept_snapshot",
        phase_key=WorkflowPhaseKey.PREFLIGHT_ADMISSION,
        proof_kind="acceptance_proof",
        input_ports=[
            _ref("candidate_set_seal", "mkb.intake.candidate-set-seal.v1"),
            _ref("preflight_outcome", "mkb.intake.preflight-outcome.v1"),
        ],
        output_ports=[_ref("accepted_intake_revision", "mkb.intake.accepted-revision.v1")],
    ),
    WorkflowStepDefinition(
        step_key="human_review",
        step_kind=WorkflowStepKind.CONTROL,
        control_key="human_review_gate",
        phase_key=WorkflowPhaseKey.AWAITING_HUMAN_REVIEW,
        input_ports=[
            _ref("accepted_intake_revision", "mkb.intake.accepted-revision.v1"),
            _ref("preflight_outcome", "mkb.intake.preflight-outcome.v1"),
        ],
        output_ports=[_ref("gate_decision", "mkb.intake.gate-decision.v1")],
    ),
    _process(
        step_key="structurize",
        process_key="lsrag.structurize",
        phase_key=WorkflowPhaseKey.STRUCTURIZING,
        proof_kind="structure_proof",
        input_ports=[_ref("accepted_intake_revision", "mkb.intake.accepted-revision.v1")],
        output_ports=[_ref("structure_artifact", "mkb.lsrag.structure-artifact.v1")],
    ),
    _process(
        step_key="construct",
        process_key="lsrag.construct",
        phase_key=WorkflowPhaseKey.CONSTRUCTING,
        proof_kind="construct_to_vectorize_gate",
        # Metadata refresh is a distinct S07 mode.  It reaches this Process
        # directly from acceptance with a frozen source construction handoff;
        # normal intake reaches it through fresh S06 output.  The engine
        # resolves the one successful optional predecessor without treating an
        # unvisited branch as a missing required input.
        input_ports=[
            _optional_ref("structure_artifact", "mkb.lsrag.structure-artifact.v1"),
            _optional_ref("accepted_intake_revision", "mkb.intake.accepted-revision.v1"),
        ],
        output_ports=[_ref("construct_package", "mkb.lsrag.construct-package.v1")],
    ),
    _process(
        step_key="vectorize",
        process_key="lsrag.vectorize",
        phase_key=WorkflowPhaseKey.VECTORIZING_INDEXING,
        proof_kind="vectorization_proof",
        input_ports=[_ref("construct_package", "mkb.lsrag.construct-package.v1")],
        output_ports=[_ref("vectorization_receipt", "mkb.vector.vectorization-receipt.v1")],
    ),
    _process(
        step_key="validate_publication",
        process_key="index.validate_publication",
        phase_key=WorkflowPhaseKey.VALIDATING_PUBLICATION,
        proof_kind="publication_proof",
        input_ports=[
            _ref("accepted_intake_revision", "mkb.intake.accepted-revision.v1"),
            _ref("vectorization_receipt", "mkb.vector.vectorization-receipt.v1"),
        ],
        output_ports=[_ref("publication_proof", "mkb.vector.publication-proof.v1")],
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


_ROUTES = [
    # ``index.rebuild`` is a distinct S09 capability, not an acquire mode
    # hidden inside the normal intake skeleton.  The guard is a bounded Task
    # intent selector evaluated before any Process exists.
    WorkflowRouteDefinition(
        route_key="start.to_index_rebuild",
        from_step_key="start",
        to_step_key="index_rebuild",
        route_kind=WorkflowRouteKind.NORMAL,
        outcome_selector=WorkflowOutcomeSelector.ALWAYS,
        priority=0,
        guard_key="request_intent_index_rebuild",
    ),
    WorkflowRouteDefinition(
        route_key="start.to_acquire",
        from_step_key="start",
        to_step_key="acquire",
        route_kind=WorkflowRouteKind.NORMAL,
        outcome_selector=WorkflowOutcomeSelector.ALWAYS,
        priority=10,
    ),
    WorkflowRouteDefinition(
        route_key="acquire.to_succeeded_index_rebuild",
        from_step_key="acquire",
        to_step_key="succeeded",
        route_kind=WorkflowRouteKind.TERMINAL,
        outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
        priority=0,
        guard_key="request_intent_index_rebuild",
    ),
    WorkflowRouteDefinition(
        route_key="acquire.to_succeeded_deactivate",
        from_step_key="acquire",
        to_step_key="succeeded",
        route_kind=WorkflowRouteKind.TERMINAL,
        outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
        priority=1,
        guard_key="request_intent_deactivate",
    ),
    WorkflowRouteDefinition(
        route_key="acquire.to_succeeded_reactivate",
        from_step_key="acquire",
        to_step_key="succeeded",
        route_kind=WorkflowRouteKind.TERMINAL,
        outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
        priority=2,
        guard_key="request_intent_reactivate",
    ),
    WorkflowRouteDefinition(
        route_key="acquire.to_succeeded_delete",
        from_step_key="acquire",
        to_step_key="succeeded",
        route_kind=WorkflowRouteKind.TERMINAL,
        outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
        priority=3,
        guard_key="request_intent_delete",
    ),
    WorkflowRouteDefinition(
        route_key="acquire.to_succeeded_metadata_no_change",
        from_step_key="acquire",
        to_step_key="succeeded",
        route_kind=WorkflowRouteKind.TERMINAL,
        outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
        priority=4,
        guard_key="metadata_no_change",
    ),
    WorkflowRouteDefinition(
        route_key="acquire.to_decode",
        from_step_key="acquire",
        to_step_key="decode",
        route_kind=WorkflowRouteKind.NORMAL,
        outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
        priority=10,
    ),
    WorkflowRouteDefinition(
        route_key="decode.to_clean",
        from_step_key="decode",
        to_step_key="clean",
        route_kind=WorkflowRouteKind.NORMAL,
        outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
        priority=0,
    ),
    WorkflowRouteDefinition(
        route_key="clean.to_seal_candidate_set",
        from_step_key="clean",
        to_step_key="seal_candidate_set",
        route_kind=WorkflowRouteKind.NORMAL,
        outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
        priority=0,
    ),
    WorkflowRouteDefinition(
        route_key="seal_candidate_set.to_preflight_validate",
        from_step_key="seal_candidate_set",
        to_step_key="preflight_validate",
        route_kind=WorkflowRouteKind.NORMAL,
        outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
        priority=0,
    ),
    WorkflowRouteDefinition(
        route_key="preflight_validate.to_accept_snapshot",
        from_step_key="preflight_validate",
        to_step_key="accept_snapshot",
        route_kind=WorkflowRouteKind.NORMAL,
        outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
        priority=0,
    ),
    WorkflowRouteDefinition(
        route_key="accept_snapshot.metadata_refresh",
        from_step_key="accept_snapshot",
        to_step_key="construct",
        route_kind=WorkflowRouteKind.BRANCH,
        outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
        priority=0,
        guard_key="request_intent_metadata_refresh",
    ),
    WorkflowRouteDefinition(
        route_key="accept_snapshot.auto_admitted",
        from_step_key="accept_snapshot",
        to_step_key="structurize",
        route_kind=WorkflowRouteKind.BRANCH,
        outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
        priority=10,
        guard_key="admission_auto_admitted",
    ),
    WorkflowRouteDefinition(
        route_key="accept_snapshot.human_review",
        from_step_key="accept_snapshot",
        to_step_key="human_review",
        route_kind=WorkflowRouteKind.BRANCH,
        outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
        priority=20,
        guard_key="admission_human_review_required",
    ),
    WorkflowRouteDefinition(
        route_key="accept_snapshot.rejected",
        from_step_key="accept_snapshot",
        to_step_key="failed",
        route_kind=WorkflowRouteKind.TERMINAL,
        outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
        priority=30,
        guard_key="admission_rejected",
    ),
    WorkflowRouteDefinition(
        route_key="human_review.to_structurize",
        from_step_key="human_review",
        to_step_key="structurize",
        route_kind=WorkflowRouteKind.NORMAL,
        outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
        priority=0,
    ),
    WorkflowRouteDefinition(
        route_key="structurize.to_construct",
        from_step_key="structurize",
        to_step_key="construct",
        route_kind=WorkflowRouteKind.NORMAL,
        outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
        priority=0,
    ),
    WorkflowRouteDefinition(
        route_key="construct.to_vectorize",
        from_step_key="construct",
        to_step_key="vectorize",
        route_kind=WorkflowRouteKind.NORMAL,
        outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
        priority=0,
    ),
    WorkflowRouteDefinition(
        route_key="vectorize.to_validate_publication",
        from_step_key="vectorize",
        to_step_key="validate_publication",
        route_kind=WorkflowRouteKind.NORMAL,
        outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
        priority=0,
    ),
    WorkflowRouteDefinition(
        route_key="validate_publication.to_succeeded",
        from_step_key="validate_publication",
        to_step_key="succeeded",
        route_kind=WorkflowRouteKind.TERMINAL,
        outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
        priority=0,
    ),
    WorkflowRouteDefinition(
        route_key="index_rebuild.to_succeeded",
        from_step_key="index_rebuild",
        to_step_key="succeeded",
        route_kind=WorkflowRouteKind.TERMINAL,
        outcome_selector=WorkflowOutcomeSelector.SUCCEEDED,
        priority=0,
    ),
]


for _step_key in (
    "index_rebuild",
    "acquire",
    "decode",
    "clean",
    "seal_candidate_set",
    "preflight_validate",
    "accept_snapshot",
    "human_review",
    "structurize",
    "construct",
    "vectorize",
    "validate_publication",
):
    _ROUTES.extend(_terminal_routes(_step_key))


_BINDINGS = [
    WorkflowBindingDefinition(
        target_step_key="index_rebuild",
        target_slot_name="index_rebuild_scope",
        source_kind=WorkflowBindingSourceKind.EXECUTION_CONTEXT,
        source_ref_key="index_rebuild_scope",
    ),
    WorkflowBindingDefinition(
        target_step_key="acquire",
        target_slot_name="source_descriptor",
        source_kind=WorkflowBindingSourceKind.EXECUTION_CONTEXT,
        source_ref_key="source_descriptor",
    ),
    WorkflowBindingDefinition(
        target_step_key="decode",
        target_slot_name="acquisition_evidence",
        source_kind=WorkflowBindingSourceKind.PRIOR_OUTPUT,
        source_step_key="acquire",
        source_port_name="acquisition_evidence",
    ),
    WorkflowBindingDefinition(
        target_step_key="clean",
        target_slot_name="decoded_representation",
        source_kind=WorkflowBindingSourceKind.PRIOR_OUTPUT,
        source_step_key="decode",
        source_port_name="decoded_representation",
    ),
    WorkflowBindingDefinition(
        target_step_key="seal_candidate_set",
        target_slot_name="clean_candidate",
        source_kind=WorkflowBindingSourceKind.PRIOR_OUTPUT,
        source_step_key="clean",
        source_port_name="clean_candidate",
    ),
    WorkflowBindingDefinition(
        target_step_key="preflight_validate",
        target_slot_name="acquisition_evidence",
        source_kind=WorkflowBindingSourceKind.PRIOR_OUTPUT,
        source_step_key="acquire",
        source_port_name="acquisition_evidence",
    ),
    WorkflowBindingDefinition(
        target_step_key="preflight_validate",
        target_slot_name="candidate_set_seal",
        source_kind=WorkflowBindingSourceKind.PRIOR_OUTPUT,
        source_step_key="seal_candidate_set",
        source_port_name="candidate_set_seal",
    ),
    WorkflowBindingDefinition(
        target_step_key="preflight_validate",
        target_slot_name="clean_candidate",
        source_kind=WorkflowBindingSourceKind.PRIOR_OUTPUT,
        source_step_key="clean",
        source_port_name="clean_candidate",
    ),
    WorkflowBindingDefinition(
        target_step_key="accept_snapshot",
        target_slot_name="candidate_set_seal",
        source_kind=WorkflowBindingSourceKind.PRIOR_OUTPUT,
        source_step_key="seal_candidate_set",
        source_port_name="candidate_set_seal",
    ),
    WorkflowBindingDefinition(
        target_step_key="accept_snapshot",
        target_slot_name="preflight_outcome",
        source_kind=WorkflowBindingSourceKind.PRIOR_OUTPUT,
        source_step_key="preflight_validate",
        source_port_name="preflight_outcome",
    ),
    WorkflowBindingDefinition(
        target_step_key="human_review",
        target_slot_name="accepted_intake_revision",
        source_kind=WorkflowBindingSourceKind.PRIOR_OUTPUT,
        source_step_key="accept_snapshot",
        source_port_name="accepted_intake_revision",
    ),
    WorkflowBindingDefinition(
        target_step_key="human_review",
        target_slot_name="preflight_outcome",
        source_kind=WorkflowBindingSourceKind.PRIOR_OUTPUT,
        source_step_key="preflight_validate",
        source_port_name="preflight_outcome",
    ),
    WorkflowBindingDefinition(
        target_step_key="structurize",
        target_slot_name="accepted_intake_revision",
        source_kind=WorkflowBindingSourceKind.PRIOR_OUTPUT,
        source_step_key="accept_snapshot",
        source_port_name="accepted_intake_revision",
    ),
    WorkflowBindingDefinition(
        target_step_key="construct",
        target_slot_name="structure_artifact",
        source_kind=WorkflowBindingSourceKind.PRIOR_OUTPUT,
        source_step_key="structurize",
        source_port_name="structure_artifact",
    ),
    WorkflowBindingDefinition(
        target_step_key="construct",
        target_slot_name="accepted_intake_revision",
        source_kind=WorkflowBindingSourceKind.PRIOR_OUTPUT,
        source_step_key="accept_snapshot",
        source_port_name="accepted_intake_revision",
    ),
    WorkflowBindingDefinition(
        target_step_key="vectorize",
        target_slot_name="construct_package",
        source_kind=WorkflowBindingSourceKind.PRIOR_OUTPUT,
        source_step_key="construct",
        source_port_name="construct_package",
    ),
    WorkflowBindingDefinition(
        target_step_key="validate_publication",
        target_slot_name="accepted_intake_revision",
        source_kind=WorkflowBindingSourceKind.PRIOR_OUTPUT,
        source_step_key="accept_snapshot",
        source_port_name="accepted_intake_revision",
    ),
    WorkflowBindingDefinition(
        target_step_key="validate_publication",
        target_slot_name="vectorization_receipt",
        source_kind=WorkflowBindingSourceKind.PRIOR_OUTPUT,
        source_step_key="vectorize",
        source_port_name="vectorization_receipt",
    ),
]


BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW: Final[WorkflowDefinition] = WorkflowDefinition(
    schema_version="mkb.workflow-definition.v1",
    workflow_key="intake.ingest.single.inline.lsrag.v1",
    # Revision 3 adds the typed S07 metadata-refresh branch.  Existing
    # executions remain pinned to their prior immutable revision.
    revision_number=3,
    domain_key="ls_rag",
    purpose_key="intake.ingest",
    execution_role=WorkflowExecutionRole.SINGLE_ROOT,
    display_name="Single inline intake LS-RAG",
    description=(
        "A declarative single-intake path from source acquisition and clean evidence through publication validation."
    ),
    context_slots=[
        _ref("source_descriptor", "mkb.intake.source-descriptor.v1"),
        _ref("index_rebuild_scope", "mkb.index.rebuild-scope.v1"),
    ],
    required_process_keys=[
        "index.rebuild",
        "intake.acquire.inline",
        "intake.decode.text_json_html",
        "clean.extract.deterministic",
        "intake.collection.seal",
        "intake.preflight_validate",
        "intake.accept_snapshot",
        "lsrag.structurize",
        "lsrag.construct",
        "lsrag.vectorize",
        "index.validate_publication",
    ],
    steps=_STEPS,
    routes=_ROUTES,
    bindings=_BINDINGS,
    guards=[
        WorkflowGuardDefinition(
            guard_key="request_intent_index_rebuild",
            predicate_type="registered_request_intent",
            operator="eq",
            expected_value="index.rebuild",
        ),
        WorkflowGuardDefinition(
            guard_key="request_intent_metadata_refresh",
            predicate_type="registered_request_intent",
            operator="eq",
            expected_value="intake.update_metadata",
        ),
        WorkflowGuardDefinition(
            guard_key="request_intent_deactivate",
            predicate_type="registered_request_intent",
            operator="eq",
            expected_value="intake.deactivate",
        ),
        WorkflowGuardDefinition(
            guard_key="request_intent_reactivate",
            predicate_type="registered_request_intent",
            operator="eq",
            expected_value="intake.reactivate",
        ),
        WorkflowGuardDefinition(
            guard_key="request_intent_delete",
            predicate_type="registered_request_intent",
            operator="eq",
            expected_value="intake.delete",
        ),
        WorkflowGuardDefinition(
            guard_key="metadata_no_change",
            predicate_type="registered_metadata_disposition",
            operator="eq",
            expected_value="no_change",
        ),
        WorkflowGuardDefinition(
            guard_key="admission_auto_admitted",
            predicate_type="registered_admission_result",
            operator="eq",
            expected_value="auto_admitted",
        ),
        WorkflowGuardDefinition(
            guard_key="admission_human_review_required",
            predicate_type="registered_admission_result",
            operator="eq",
            expected_value="human_review_required",
        ),
        WorkflowGuardDefinition(
            guard_key="admission_rejected",
            predicate_type="registered_admission_result",
            operator="eq",
            expected_value="rejected",
        ),
    ],
)


def _pre_metadata_refresh_execution_document() -> dict[str, object]:
    """Return the exact revision-2 graph shape before S07 refresh routing.

    Source-profile workflows remain revision 1 because metadata-only Tasks
    deliberately resolve the canonical inline skeleton.  Keeping their
    reviewed graph byte-for-byte stable avoids silently replacing an active
    source profile just because the canonical metadata branch gained a new
    S07 mode.
    """

    _d02_acquire_shortcuts = {
        "acquire.to_succeeded_index_rebuild",
        "acquire.to_succeeded_deactivate",
        "acquire.to_succeeded_reactivate",
        "acquire.to_succeeded_delete",
        "acquire.to_succeeded_metadata_no_change",
    }
    _d02_acquire_guards = {
        "request_intent_deactivate",
        "request_intent_reactivate",
        "request_intent_delete",
        "metadata_no_change",
    }
    document = BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW.model_dump()
    document["routes"] = [
        {
            **route,
            **({"priority": 0} if route["route_key"] == "acquire.to_decode" else {}),
        }
        for route in document["routes"]
        if route["guard_key"] != "request_intent_metadata_refresh"
        and route["route_key"] not in _d02_acquire_shortcuts
    ]
    document["guards"] = [
        guard
        for guard in document["guards"]
        if guard["guard_key"] != "request_intent_metadata_refresh"
        and guard["guard_key"] not in _d02_acquire_guards
    ]
    document["bindings"] = [
        binding
        for binding in document["bindings"]
        if not (
            binding["target_step_key"] == "construct"
            and binding["target_slot_name"] == "accepted_intake_revision"
        )
    ]
    for step in document["steps"]:
        if step["step_key"] == "construct":
            step["input_ports"] = [
                {
                    **port,
                    "required": True,
                }
                for port in step["input_ports"]
                if port["slot_name"] == "structure_artifact"
            ]
    return document


def _source_profile_workflow(
    *,
    workflow_key: str,
    display_name: str,
    acquire_process_key: str,
    decode_process_key: str,
    clean_process_key: str = "clean.extract.deterministic",
) -> WorkflowDefinition:
    """Derive one reviewed, immutable source-profile graph.

    ``source_kind`` and acquisition/decode/clean capabilities are deliberately
    not a runtime branch string.  Each source/profile has its own workflow
    identity and compiled capability set, which ConfigSnapshotService freezes
    before an Execution exists.  The shared LS-RAG tail stays byte-for-byte
    declarative across profiles.
    """

    # Keep enum instances because these strict Workflow models intentionally
    # reject stringly-typed graph declarations during bootstrap validation.
    document = _pre_metadata_refresh_execution_document()
    document.update(
        {
            "workflow_key": workflow_key,
            "revision_number": 1,
            "display_name": display_name,
            "description": (
                f"A source-profile LS-RAG path with {acquire_process_key}, "
                f"{decode_process_key}, and {clean_process_key}."
            ),
        }
    )
    replacements = {
        "intake.acquire.inline": acquire_process_key,
        "intake.decode.text_json_html": decode_process_key,
        "clean.extract.deterministic": clean_process_key,
    }
    for step in document["steps"]:
        if step["step_key"] == "acquire":
            step["process_key"] = acquire_process_key
        elif step["step_key"] == "decode":
            step["process_key"] = decode_process_key
        elif step["step_key"] == "clean":
            step["process_key"] = clean_process_key
    document["required_process_keys"] = [replacements.get(key, key) for key in document["required_process_keys"]]
    return WorkflowDefinition.model_validate(document)


SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS: Final[dict[str, str]] = {
    "inline_payload": BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW.workflow_key,
    "local_object": "intake.ingest.single.local-object.lsrag.v1",
    "local_object.pdf": "intake.ingest.single.local-pdf.lsrag.v1",
    "http_resource.static": "intake.ingest.single.http-static.lsrag.v1",
    "http_resource.browser": "intake.ingest.single.http-browser.lsrag.v1",
    "http_resource.pdf": "intake.ingest.single.http-pdf.lsrag.v1",
    # Local image input has one explicit first stop: a local OCR capability.
    # The handler fail-closes when no reviewed OCR runtime is deployed; it may
    # never silently reinterpret binary bytes as deterministic text.
    "local_object.image": "intake.ingest.single.local-ocr.lsrag.v1",
}


BUILTIN_LOCAL_OBJECT_INTAKE_WORKFLOW: Final[WorkflowDefinition] = _source_profile_workflow(
    workflow_key=SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS["local_object"],
    display_name="Single local-object intake LS-RAG",
    acquire_process_key="intake.acquire.local_object",
    decode_process_key="intake.decode.text_json_html",
)


BUILTIN_LOCAL_PDF_INTAKE_WORKFLOW: Final[WorkflowDefinition] = _source_profile_workflow(
    workflow_key=SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS["local_object.pdf"],
    display_name="Single local-PDF intake LS-RAG",
    acquire_process_key="intake.acquire.local_object",
    decode_process_key="intake.decode.pdf",
)


BUILTIN_HTTP_STATIC_INTAKE_WORKFLOW: Final[WorkflowDefinition] = _source_profile_workflow(
    workflow_key=SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS["http_resource.static"],
    display_name="Single static-HTTP intake LS-RAG",
    acquire_process_key="intake.acquire.http_static",
    decode_process_key="intake.decode.text_json_html",
)


BUILTIN_HTTP_BROWSER_INTAKE_WORKFLOW: Final[WorkflowDefinition] = _source_profile_workflow(
    workflow_key=SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS["http_resource.browser"],
    display_name="Single browser-rendered intake LS-RAG",
    acquire_process_key="intake.acquire.http_browser",
    decode_process_key="intake.decode.text_json_html",
)


BUILTIN_HTTP_PDF_INTAKE_WORKFLOW: Final[WorkflowDefinition] = _source_profile_workflow(
    workflow_key=SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS["http_resource.pdf"],
    display_name="Single PDF intake LS-RAG",
    acquire_process_key="intake.acquire.http_static",
    decode_process_key="intake.decode.pdf",
)


BUILTIN_LOCAL_OCR_INTAKE_WORKFLOW: Final[WorkflowDefinition] = _source_profile_workflow(
    workflow_key=SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS["local_object.image"],
    display_name="Single local-image OCR intake LS-RAG",
    acquire_process_key="intake.acquire.local_object",
    # OCR receives the acquired image representation directly in its handler.
    # The decode slot remains a typed envelope coordinate, and the deployed
    # capability currently rejects with a stable unavailability code.
    decode_process_key="intake.decode.text_json_html",
    clean_process_key="clean.ocr.local",
)


BUILTIN_VISION_REJECTION_INTAKE_WORKFLOW: Final[WorkflowDefinition] = _source_profile_workflow(
    workflow_key="intake.ingest.single.vision-rejected.lsrag.v1",
    display_name="Controlled Vision intake capability refusal",
    acquire_process_key="intake.acquire.local_object",
    decode_process_key="intake.decode.text_json_html",
    clean_process_key="clean.extract.vision",
)


BUILTIN_SOURCE_PROFILE_WORKFLOWS: Final[tuple[WorkflowDefinition, ...]] = (
    BUILTIN_LOCAL_OBJECT_INTAKE_WORKFLOW,
    BUILTIN_LOCAL_PDF_INTAKE_WORKFLOW,
    BUILTIN_HTTP_STATIC_INTAKE_WORKFLOW,
    BUILTIN_HTTP_BROWSER_INTAKE_WORKFLOW,
    BUILTIN_HTTP_PDF_INTAKE_WORKFLOW,
    BUILTIN_LOCAL_OCR_INTAKE_WORKFLOW,
    BUILTIN_VISION_REJECTION_INTAKE_WORKFLOW,
)

