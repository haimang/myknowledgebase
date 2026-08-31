"""Production actual-S05 aggregate and sealed-once transaction helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from src.contracts.common.errors import ConflictError, MkbError
from src.contracts.common.ids import stable_digest
from src.contracts.common.time import utc_now
from src.contracts.governance import ProcessingBinding, ProcessingBindingFamily
from src.persistence.ports import UnitOfWork

ActualBindingState = Literal["legacy_unverifiable", "unsealed", "sealed"]


def clean_strategy_for_step(step_key: str, process_key: str) -> str:
    """Resolve an exact declared clean step without inspecting representation bytes."""

    unique = {
        "clean.extract.deterministic": "doc.deterministic",
        "clean.extract.web": "web.deterministic",
        "clean.extract.web_llm": "web.llm_rewrite",
        "clean.extract.pdf_text": "pdf.text_layer",
        "clean.extract.doc_llm": "doc.document_understanding",
        "clean.extract.vision": "doc.vision",
        "clean.map.registered_api": "registered_api.map",
    }
    if process_key in unique:
        return unique[process_key]
    if process_key == "clean.extract.pdf_llm":
        return "web.browser_print_pdf" if step_key == "clean_print_pdf" else "pdf.document_understanding"
    if process_key == "clean.ocr.local":
        return "pdf.ocr" if "pdf" in step_key else "doc.ocr"
    raise MkbError("CLEAN_STRATEGY_UNSUPPORTED", "Selected clean Process has no registered strategy", 409)


def requires_actual_binding(process_key: str) -> bool:
    """The clean boundary and every later stage require one sealed actual digest."""

    return process_key.startswith(("clean.", "lsrag.")) or process_key in {
        "intake.collection.seal",
        "intake.preflight_validate",
        "intake.accept_snapshot",
        "index.validate_publication",
    }


def projected_actual_digest(row: Mapping[str, Any]) -> str | None:
    if row.get("actual_binding_state") != "sealed":
        return None
    value = row.get("actual_binding_digest")
    return value if _is_digest(value) else None


async def seal_actual_binding_tx(
    tx: UnitOfWork,
    *,
    execution_uuid: str,
    selected_route_digest: str,
    clean_step_key: str,
    clean_process_key: str,
    clean_strategy: str,
) -> dict[str, Any]:
    """Seal ordered representation history and the selected clean edge once."""

    if not _is_digest(selected_route_digest):
        raise MkbError("ACTUAL_S05_SEAL_INVALID", "Selected route digest is invalid", 422)
    history = await tx.fetchone(
        "SELECT representation_path_digest FROM mkb_acquire_decode_history "
        "WHERE execution_uuid=? ORDER BY ordinal DESC LIMIT 1",
        (execution_uuid,),
    )
    if history is None or not _is_digest(history.get("representation_path_digest")):
        raise ConflictError(
            "ACTUAL_S05_HISTORY_MISSING",
            "A clean route cannot be selected without durable ordered representation history",
        )
    actual_digest = stable_digest(
        {
            "schema_version": "mkb.actual-s05-binding.v1",
            "representation_path_digest": history["representation_path_digest"],
            "selected_route_digest": selected_route_digest,
            "clean_step_key": clean_step_key,
            "clean_process_key": clean_process_key,
            "clean_strategy": clean_strategy,
        }
    )
    if clean_process_key == "clean.map.registered_api":
        binding = ProcessingBinding(
            family=ProcessingBindingFamily.REGISTERED_API_OPERATION,
            key="registered_api",
            definition_version="v1",
            definition_digest=stable_digest({"registry": "registered_provider_operations", "version": "v1"}),
        )
    else:
        from src.contracts.intake.strategies import resolve_clean_strategy

        strategy = resolve_clean_strategy(clean_strategy)
        binding = ProcessingBinding(
            family=ProcessingBindingFamily.CLEAN_STRATEGY,
            key=clean_strategy,
            definition_version=strategy.definition_version,
            definition_digest=strategy.definition_digest,
        )
    row = await tx.fetchone(
        "SELECT actual_binding_digest,actual_binding_state,seal_generation,actual_selected_route_digest,"
        "actual_clean_step_key,actual_clean_process_key,actual_clean_strategy "
        "FROM mkb_executions WHERE execution_uuid=?",
        (execution_uuid,),
    )
    if row is None:
        raise MkbError("ACTUAL_S05_EXECUTION_MISSING", "Actual S05 execution is missing", 404)
    if row["actual_binding_state"] == "legacy_unverifiable":
        raise ConflictError(
            "ACTUAL_S05_LEGACY_UNVERIFIABLE",
            "A legacy policy alias cannot be promoted to actual S05 truth",
        )
    if row["actual_binding_state"] == "sealed":
        if (
            row["actual_binding_digest"] == actual_digest
            and row["actual_selected_route_digest"] == selected_route_digest
            and row["actual_clean_step_key"] == clean_step_key
            and row["actual_clean_process_key"] == clean_process_key
            and row["actual_clean_strategy"] == clean_strategy
        ):
            return dict(row)
        raise ConflictError("ACTUAL_S05_SEAL_CONFLICT", "Execution already has a different actual S05 seal")
    now = utc_now()
    updated = await tx.execute(
        "UPDATE mkb_executions SET actual_binding_digest=?,actual_binding_state='sealed',seal_generation=1,"
        "actual_selected_route_digest=?,actual_clean_step_key=?,actual_clean_process_key=?,actual_clean_strategy=?,"
        "row_revision=row_revision+1,updated_at=? WHERE execution_uuid=? AND actual_binding_state='unsealed' "
        "AND actual_binding_digest IS NULL AND seal_generation=0",
        (
            actual_digest,
            selected_route_digest,
            clean_step_key,
            clean_process_key,
            clean_strategy,
            now,
            execution_uuid,
        ),
    )
    if updated.rowcount != 1:
        raise ConflictError("ACTUAL_S05_SEAL_CONFLICT", "Actual S05 seal lost its compare-and-swap fence")
    await tx.execute(
        "INSERT INTO mkb_processing_binding_assertions"
        "(binding_assertion_uuid,team_uuid,execution_uuid,binding_family,binding_key,definition_version,"
        "definition_digest,selected_process_key,selected_route_digest,assertion_digest,formula_version,seal_generation,"
        "asserted_at,payload_extra) "
        "SELECT ?,team_uuid,execution_uuid,?,?,?,?,?,?,?,'selection.v2',seal_generation,?,'{}' "
        "FROM mkb_executions WHERE execution_uuid=?",
        (
            stable_digest({"execution_uuid": execution_uuid, "binding": binding.key})[:32],
            binding.family.value,
            binding.key,
            binding.definition_version,
            binding.definition_digest,
            clean_process_key,
            selected_route_digest,
            stable_digest({"actual_binding_digest": actual_digest, "binding": binding.key}),
            now,
            execution_uuid,
        ),
    )
    sealed = await tx.fetchone(
        "SELECT actual_binding_digest,actual_binding_state,seal_generation,actual_selected_route_digest,"
        "actual_clean_step_key,actual_clean_process_key,actual_clean_strategy "
        "FROM mkb_executions WHERE execution_uuid=?",
        (execution_uuid,),
    )
    assert sealed is not None
    return sealed


def _is_digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


__all__ = [
    "ActualBindingState",
    "clean_strategy_for_step",
    "projected_actual_digest",
    "requires_actual_binding",
    "seal_actual_binding_tx",
]
