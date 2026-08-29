"""Three source-kind Workflow definitions with one shared LS-RAG tail."""

from __future__ import annotations

from collections.abc import Iterable
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
    WorkflowValueType,
)
from src.workflows.lsrag_definition import BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW
from src.workflows.lsrag_shared_tail import shared_tail_components

INLINE_KIND_WORKFLOW_KEY = "intake.ingest.kind.inline-payload.lsrag.v1"
LOCAL_OBJECT_KIND_WORKFLOW_KEY = "intake.ingest.kind.local-object.lsrag.v1"
HTTP_RESOURCE_KIND_WORKFLOW_KEY = "intake.ingest.kind.http-resource.lsrag.v1"

SOURCE_KIND_WORKFLOW_KEYS: Final[dict[str, str]] = {
    "inline_payload": INLINE_KIND_WORKFLOW_KEY,
    "local_object": LOCAL_OBJECT_KIND_WORKFLOW_KEY,
    "http_resource": HTTP_RESOURCE_KIND_WORKFLOW_KEY,
}


def _ref(slot_name: str, schema_ref: str, *, required: bool = True) -> WorkflowPortDefinition:
    return WorkflowPortDefinition(
        slot_name=slot_name,
        value_type=WorkflowValueType.LOGICAL_REF,
        schema_ref=schema_ref,
        required=required,
    )


def _process(
    step_key: str,
    process_key: str,
    *,
    input_schema: str,
    output_slot: str,
    output_schema: str,
    phase: WorkflowPhaseKey,
    proof: str,
) -> WorkflowStepDefinition:
    return WorkflowStepDefinition(
        step_key=step_key,
        step_kind=WorkflowStepKind.PROCESS,
        process_key=process_key,
        contract_version="v1",
        phase_key=phase,
        required_proof_kind=proof,
        input_ports=[_ref("input", input_schema)],
        output_ports=[_ref(output_slot, output_schema)],
    )


def _acquire(step_key: str, process_key: str) -> WorkflowStepDefinition:
    return _process(
        step_key,
        process_key,
        input_schema="mkb.intake.source-descriptor.v1",
        output_slot="acquisition_evidence",
        output_schema="mkb.intake.acquisition-evidence.v1",
        phase=WorkflowPhaseKey.RESOLVING_SOURCE,
        proof="acquisition_evidence",
    )


def _decode(step_key: str, process_key: str) -> WorkflowStepDefinition:
    return _process(
        step_key,
        process_key,
        input_schema="mkb.intake.acquisition-evidence.v1",
        output_slot="decoded_representation",
        output_schema="mkb.intake.decoded-representation.v1",
        phase=WorkflowPhaseKey.RESOLVING_SOURCE,
        proof="decode_evidence",
    )


def _clean(step_key: str, process_key: str) -> WorkflowStepDefinition:
    return _process(
        step_key,
        process_key,
        input_schema="mkb.intake.decoded-representation.v1",
        output_slot="clean_candidate",
        output_schema="mkb.intake.clean-candidate.v1",
        phase=WorkflowPhaseKey.CLEANING,
        proof="clean_candidate_evidence",
    )


def _route(
    key: str,
    source: str,
    target: str,
    *,
    selector: WorkflowOutcomeSelector = WorkflowOutcomeSelector.SUCCEEDED,
    priority: int = 0,
    guard: str | None = None,
) -> WorkflowRouteDefinition:
    return WorkflowRouteDefinition(
        route_key=key,
        from_step_key=source,
        to_step_key=target,
        route_kind=WorkflowRouteKind.NORMAL,
        outcome_selector=selector,
        priority=priority,
        guard_key=guard,
    )


def _terminal_routes(step_keys: Iterable[str]) -> list[WorkflowRouteDefinition]:
    routes: list[WorkflowRouteDefinition] = []
    for step_key in step_keys:
        routes.extend(
            [
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
        )
    return routes


def _bind(target: str, slot: str, source: str, port: str) -> WorkflowBindingDefinition:
    return WorkflowBindingDefinition(
        target_step_key=target,
        target_slot_name=slot,
        source_kind=WorkflowBindingSourceKind.PRIOR_OUTPUT,
        source_step_key=source,
        source_port_name=port,
    )


def _bind_context(target: str, slot: str, ref_key: str) -> WorkflowBindingDefinition:
    return WorkflowBindingDefinition(
        target_step_key=target,
        target_slot_name=slot,
        source_kind=WorkflowBindingSourceKind.EXECUTION_CONTEXT,
        source_ref_key=ref_key,
    )


def _guard(key: str, predicate: str, expected: str) -> WorkflowGuardDefinition:
    return WorkflowGuardDefinition(
        guard_key=key,
        predicate_type=predicate,  # type: ignore[arg-type]
        operator="eq",
        expected_value=expected,
    )


def _selected_control(clean_steps: list[WorkflowStepDefinition]) -> WorkflowStepDefinition:
    return WorkflowStepDefinition(
        step_key="selected_clean",
        step_kind=WorkflowStepKind.CONTROL,
        control_key="selected_output",
        control_version="selected-output.v1",
        phase_key=WorkflowPhaseKey.CLEANING,
        input_ports=[
            _ref(step.step_key, "mkb.intake.clean-candidate.v1", required=False)
            for step in clean_steps
        ],
        output_ports=[_ref("clean_candidate", "mkb.intake.clean-candidate.v1")],
    )


def _compose(
    *,
    workflow_key: str,
    display_name: str,
    prefix_steps: list[WorkflowStepDefinition],
    prefix_routes: list[WorkflowRouteDefinition],
    prefix_bindings: list[WorkflowBindingDefinition],
    prefix_guards: list[WorkflowGuardDefinition],
    context_slots: list[WorkflowPortDefinition] | None = None,
) -> WorkflowDefinition:
    tail = shared_tail_components()
    clean_steps = [step for step in prefix_steps if step.process_key and step.process_key.startswith("clean.")]
    control = _selected_control(clean_steps)
    control_routes = [
        _route("selected_clean.to_seal", "selected_clean", "seal_candidate_set"),
        *_terminal_routes(["selected_clean"]),
    ]
    control_bindings = [
        _bind("selected_clean", step.step_key, step.step_key, "clean_candidate")
        for step in clean_steps
    ]
    control_bindings.extend(
        [
            _bind("seal_candidate_set", "clean_candidate", "selected_clean", "clean_candidate"),
            _bind("preflight_validate", "clean_candidate", "selected_clean", "clean_candidate"),
        ]
    )
    all_steps = [
        WorkflowStepDefinition(step_key="start", step_kind=WorkflowStepKind.START),
        *prefix_steps,
        control,
        *tail.steps,
    ]
    required_process_keys = list(
        dict.fromkeys(
            [
                *(step.process_key for step in prefix_steps if step.process_key is not None),
                *tail.required_process_keys,
            ]
        )
    )
    return WorkflowDefinition(
        schema_version="mkb.workflow-definition.v1",
        workflow_key=workflow_key,
        revision_number=1,
        domain_key="ls_rag",
        purpose_key="intake.ingest",
        execution_role=WorkflowExecutionRole.SINGLE_ROOT,
        display_name=display_name,
        description="A source-kind graph with declared acquisition/clean candidates and one shared publication tail.",
        context_slots=context_slots or [_ref("source_descriptor", "mkb.intake.source-descriptor.v1")],
        required_process_keys=required_process_keys,
        steps=all_steps,
        routes=[*prefix_routes, *control_routes, *tail.routes],
        bindings=[*prefix_bindings, *control_bindings, *tail.bindings],
        guards=[*prefix_guards, *tail.guards],
    )


def _inline_kind() -> WorkflowDefinition:
    index_step = next(
        step.model_copy(deep=True)
        for step in BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW.steps
        if step.step_key == "index_rebuild"
    )
    acquire = _acquire("acquire_inline", "intake.acquire.inline")
    decode = _decode("decode_text", "intake.decode.text_json_html")
    clean = _clean("clean_deterministic", "clean.extract.deterministic")
    routes = [
        _route(
            "start.index_rebuild",
            "start",
            "index_rebuild",
            selector=WorkflowOutcomeSelector.ALWAYS,
            priority=0,
            guard="request_intent_index_rebuild",
        ),
        _route("start.acquire", "start", "acquire_inline", selector=WorkflowOutcomeSelector.ALWAYS, priority=10),
        _route(
            "acquire.deactivate",
            "acquire_inline",
            "succeeded",
            priority=0,
            guard="request_intent_deactivate",
        ).model_copy(update={"route_kind": WorkflowRouteKind.TERMINAL}),
        _route(
            "acquire.reactivate",
            "acquire_inline",
            "succeeded",
            priority=1,
            guard="request_intent_reactivate",
        ).model_copy(update={"route_kind": WorkflowRouteKind.TERMINAL}),
        _route(
            "acquire.delete",
            "acquire_inline",
            "succeeded",
            priority=2,
            guard="request_intent_delete",
        ).model_copy(update={"route_kind": WorkflowRouteKind.TERMINAL}),
        _route(
            "acquire.metadata_no_change",
            "acquire_inline",
            "succeeded",
            priority=3,
            guard="metadata_no_change",
        ).model_copy(update={"route_kind": WorkflowRouteKind.TERMINAL}),
        _route("acquire.decode", "acquire_inline", "decode_text", priority=10),
        _route("decode.clean", "decode_text", "clean_deterministic"),
        _route("clean.selected", "clean_deterministic", "selected_clean"),
        _route("index.succeeded", "index_rebuild", "succeeded").model_copy(
            update={"route_kind": WorkflowRouteKind.TERMINAL}
        ),
        *_terminal_routes(["index_rebuild", "acquire_inline", "decode_text", "clean_deterministic"]),
    ]
    bindings = [
        _bind_context("index_rebuild", "index_rebuild_scope", "index_rebuild_scope"),
        _bind_context("acquire_inline", "input", "source_descriptor"),
        _bind("decode_text", "input", "acquire_inline", "acquisition_evidence"),
        _bind("clean_deterministic", "input", "decode_text", "decoded_representation"),
    ]
    guards = [
        _guard("request_intent_index_rebuild", "registered_request_intent", "index.rebuild"),
        _guard("request_intent_deactivate", "registered_request_intent", "intake.deactivate"),
        _guard("request_intent_reactivate", "registered_request_intent", "intake.reactivate"),
        _guard("request_intent_delete", "registered_request_intent", "intake.delete"),
        _guard("metadata_no_change", "registered_metadata_disposition", "no_change"),
    ]
    return _compose(
        workflow_key=INLINE_KIND_WORKFLOW_KEY,
        display_name="Inline-payload kind LS-RAG",
        prefix_steps=[index_step, acquire, decode, clean],
        prefix_routes=routes,
        prefix_bindings=bindings,
        prefix_guards=guards,
        context_slots=[
            _ref("source_descriptor", "mkb.intake.source-descriptor.v1"),
            _ref("index_rebuild_scope", "mkb.index.rebuild-scope.v1"),
        ],
    )


def _local_kind() -> WorkflowDefinition:
    acquire = _acquire("acquire_local", "intake.acquire.local_object")
    decodes = [
        _decode("decode_text", "intake.decode.text_json_html"),
        _decode("decode_pdf", "intake.decode.pdf"),
        _decode("decode_image", "intake.decode.text_json_html"),
    ]
    clean_specs = [
        ("clean_deterministic", "clean.extract.deterministic"),
        ("clean_doc_llm", "clean.extract.doc_llm"),
        ("clean_doc_ocr", "clean.ocr.local"),
        ("clean_vision", "clean.extract.vision"),
        ("clean_pdf_text", "clean.extract.pdf_text"),
        ("clean_pdf_llm", "clean.extract.pdf_llm"),
        ("clean_pdf_ocr", "clean.ocr.local"),
    ]
    cleans = [_clean(*spec) for spec in clean_specs]
    routes = [
        _route("start.acquire", "start", "acquire_local", selector=WorkflowOutcomeSelector.ALWAYS),
        _route("acquire.decode_pdf", "acquire_local", "decode_pdf", priority=0, guard="media_pdf"),
        _route("acquire.decode_image", "acquire_local", "decode_image", priority=1, guard="media_image"),
        _route("acquire.decode_text", "acquire_local", "decode_text", priority=10),
        _route("decode_text.doc_llm", "decode_text", "clean_doc_llm", priority=0, guard="strategy_doc_llm"),
        _route("decode_text.deterministic", "decode_text", "clean_deterministic", priority=10),
        _route("decode_image.vision", "decode_image", "clean_vision", priority=0, guard="strategy_doc_vision"),
        _route("decode_image.ocr", "decode_image", "clean_doc_ocr", priority=10),
        _route("decode_pdf.llm", "decode_pdf", "clean_pdf_llm", priority=0, guard="strategy_pdf_llm"),
        _route("decode_pdf.ocr", "decode_pdf", "clean_pdf_ocr", priority=1, guard="strategy_pdf_ocr"),
        _route("decode_pdf.text", "decode_pdf", "clean_pdf_text", priority=10),
        *(
            _route(f"{step.step_key}.selected", step.step_key, "selected_clean")
            for step in cleans
        ),
        *_terminal_routes(["acquire_local", *(step.step_key for step in decodes), *(step.step_key for step in cleans)]),
    ]
    bindings = [
        _bind_context("acquire_local", "input", "source_descriptor"),
        *(_bind(step.step_key, "input", "acquire_local", "acquisition_evidence") for step in decodes),
        _bind("clean_deterministic", "input", "decode_text", "decoded_representation"),
        _bind("clean_doc_llm", "input", "decode_text", "decoded_representation"),
        _bind("clean_doc_ocr", "input", "decode_image", "decoded_representation"),
        _bind("clean_vision", "input", "decode_image", "decoded_representation"),
        _bind("clean_pdf_text", "input", "decode_pdf", "decoded_representation"),
        _bind("clean_pdf_llm", "input", "decode_pdf", "decoded_representation"),
        _bind("clean_pdf_ocr", "input", "decode_pdf", "decoded_representation"),
    ]
    guards = [
        _guard("media_pdf", "representation_media_family", "pdf"),
        _guard("media_image", "representation_media_family", "image"),
        _guard("strategy_doc_llm", "registered_clean_strategy", "doc.document_understanding"),
        _guard("strategy_doc_vision", "registered_clean_strategy", "doc.vision"),
        _guard("strategy_pdf_llm", "registered_clean_strategy", "pdf.document_understanding"),
        _guard("strategy_pdf_ocr", "registered_clean_strategy", "pdf.ocr"),
    ]
    return _compose(
        workflow_key=LOCAL_OBJECT_KIND_WORKFLOW_KEY,
        display_name="Local-object kind LS-RAG",
        prefix_steps=[acquire, *decodes, *cleans],
        prefix_routes=routes,
        prefix_bindings=bindings,
        prefix_guards=guards,
    )


def _http_kind() -> WorkflowDefinition:
    acquires = [
        _acquire("acquire_static", "intake.acquire.http_static"),
        _acquire("acquire_browser", "intake.acquire.http_browser"),
        _acquire("acquire_browser_reacquire", "intake.acquire.http_browser"),
        _acquire("acquire_print", "intake.acquire.http_browser"),
    ]
    decodes = [
        _decode("decode_web_static", "intake.decode.text_json_html"),
        _decode("decode_web_browser", "intake.decode.text_json_html"),
        _decode("decode_web_reacquire", "intake.decode.text_json_html"),
        _decode("decode_pdf", "intake.decode.pdf"),
        _decode("decode_print", "intake.decode.pdf"),
    ]
    clean_specs = [
        ("clean_web_static", "clean.extract.web"),
        ("clean_web_browser", "clean.extract.web"),
        ("clean_web_llm_static", "clean.extract.web_llm"),
        ("clean_web_llm_browser", "clean.extract.web_llm"),
        ("clean_web_reacquire", "clean.extract.web"),
        ("clean_web_llm_reacquire", "clean.extract.web_llm"),
        ("clean_pdf_text", "clean.extract.pdf_text"),
        ("clean_pdf_llm", "clean.extract.pdf_llm"),
        ("clean_pdf_ocr", "clean.ocr.local"),
        ("clean_print_pdf", "clean.extract.pdf_llm"),
    ]
    cleans = [_clean(*spec) for spec in clean_specs]
    routes = [
        _route(
            "start.browser",
            "start",
            "acquire_browser",
            selector=WorkflowOutcomeSelector.ALWAYS,
            priority=0,
            guard="mode_browser",
        ),
        _route("start.static", "start", "acquire_static", selector=WorkflowOutcomeSelector.ALWAYS, priority=10),
        _route("static.decode_pdf", "acquire_static", "decode_pdf", priority=0, guard="mode_pdf"),
        _route("static.decode_web", "acquire_static", "decode_web_static", priority=10),
        _route("browser.decode_web", "acquire_browser", "decode_web_browser"),
        _route("reacquire.decode_web", "acquire_browser_reacquire", "decode_web_reacquire"),
        _route("print.decode_pdf", "acquire_print", "decode_print"),
        _route(
            "decode_static.reacquire_browser",
            "decode_web_static",
            "acquire_browser_reacquire",
            priority=0,
            guard="main_text_absent",
        ),
        _route(
            "decode_static.print",
            "decode_web_static",
            "acquire_print",
            priority=1,
            guard="strategy_print_pdf",
        ),
        _route(
            "decode_static.web_llm",
            "decode_web_static",
            "clean_web_llm_static",
            priority=2,
            guard="strategy_web_llm",
        ),
        _route("decode_static.web", "decode_web_static", "clean_web_static", priority=10),
        _route(
            "decode_browser.print",
            "decode_web_browser",
            "acquire_print",
            priority=0,
            guard="strategy_print_pdf",
        ),
        _route(
            "decode_browser.web_llm",
            "decode_web_browser",
            "clean_web_llm_browser",
            priority=1,
            guard="strategy_web_llm",
        ),
        _route("decode_browser.web", "decode_web_browser", "clean_web_browser", priority=10),
        _route(
            "decode_reacquire.print",
            "decode_web_reacquire",
            "acquire_print",
            priority=0,
            guard="strategy_print_pdf",
        ),
        _route(
            "decode_reacquire.web_llm",
            "decode_web_reacquire",
            "clean_web_llm_reacquire",
            priority=1,
            guard="strategy_web_llm",
        ),
        _route("decode_reacquire.web", "decode_web_reacquire", "clean_web_reacquire", priority=10),
        _route("decode_pdf.llm", "decode_pdf", "clean_pdf_llm", priority=0, guard="strategy_pdf_llm"),
        _route("decode_pdf.ocr", "decode_pdf", "clean_pdf_ocr", priority=1, guard="strategy_pdf_ocr"),
        _route("decode_pdf.text", "decode_pdf", "clean_pdf_text", priority=10),
        _route("decode_print.clean", "decode_print", "clean_print_pdf"),
        *(
            _route(f"{step.step_key}.selected", step.step_key, "selected_clean")
            for step in cleans
        ),
        *_terminal_routes([*(step.step_key for step in acquires), *(step.step_key for step in decodes), *(step.step_key for step in cleans)]),
    ]
    bindings = [
        *(_bind_context(step.step_key, "input", "source_descriptor") for step in acquires),
        _bind("decode_web_static", "input", "acquire_static", "acquisition_evidence"),
        _bind("decode_pdf", "input", "acquire_static", "acquisition_evidence"),
        _bind("decode_web_browser", "input", "acquire_browser", "acquisition_evidence"),
        _bind("decode_web_reacquire", "input", "acquire_browser_reacquire", "acquisition_evidence"),
        _bind("decode_print", "input", "acquire_print", "acquisition_evidence"),
        _bind("clean_web_static", "input", "decode_web_static", "decoded_representation"),
        _bind("clean_web_llm_static", "input", "decode_web_static", "decoded_representation"),
        _bind("clean_web_browser", "input", "decode_web_browser", "decoded_representation"),
        _bind("clean_web_llm_browser", "input", "decode_web_browser", "decoded_representation"),
        _bind("clean_web_reacquire", "input", "decode_web_reacquire", "decoded_representation"),
        _bind("clean_web_llm_reacquire", "input", "decode_web_reacquire", "decoded_representation"),
        _bind("clean_pdf_text", "input", "decode_pdf", "decoded_representation"),
        _bind("clean_pdf_llm", "input", "decode_pdf", "decoded_representation"),
        _bind("clean_pdf_ocr", "input", "decode_pdf", "decoded_representation"),
        _bind("clean_print_pdf", "input", "decode_print", "decoded_representation"),
    ]
    guards = [
        _guard("mode_browser", "registered_acquisition_mode", "browser"),
        _guard("mode_pdf", "registered_acquisition_mode", "pdf"),
        _guard("main_text_absent", "representation_main_text_presence", "absent"),
        _guard("strategy_print_pdf", "registered_clean_strategy", "web.browser_print_pdf"),
        _guard("strategy_web_llm", "registered_clean_strategy", "web.llm_rewrite"),
        _guard("strategy_pdf_llm", "registered_clean_strategy", "pdf.document_understanding"),
        _guard("strategy_pdf_ocr", "registered_clean_strategy", "pdf.ocr"),
    ]
    return _compose(
        workflow_key=HTTP_RESOURCE_KIND_WORKFLOW_KEY,
        display_name="HTTP-resource kind LS-RAG",
        prefix_steps=[*acquires, *decodes, *cleans],
        prefix_routes=routes,
        prefix_bindings=bindings,
        prefix_guards=guards,
    )


BUILTIN_INLINE_KIND_WORKFLOW: Final[WorkflowDefinition] = _inline_kind()
BUILTIN_LOCAL_OBJECT_KIND_WORKFLOW: Final[WorkflowDefinition] = _local_kind()
BUILTIN_HTTP_RESOURCE_KIND_WORKFLOW: Final[WorkflowDefinition] = _http_kind()
BUILTIN_KIND_WORKFLOWS: Final[tuple[WorkflowDefinition, ...]] = (
    BUILTIN_INLINE_KIND_WORKFLOW,
    BUILTIN_LOCAL_OBJECT_KIND_WORKFLOW,
    BUILTIN_HTTP_RESOURCE_KIND_WORKFLOW,
)


__all__ = [
    "BUILTIN_HTTP_RESOURCE_KIND_WORKFLOW",
    "BUILTIN_INLINE_KIND_WORKFLOW",
    "BUILTIN_KIND_WORKFLOWS",
    "BUILTIN_LOCAL_OBJECT_KIND_WORKFLOW",
    "HTTP_RESOURCE_KIND_WORKFLOW_KEY",
    "INLINE_KIND_WORKFLOW_KEY",
    "LOCAL_OBJECT_KIND_WORKFLOW_KEY",
    "SOURCE_KIND_WORKFLOW_KEYS",
]
