"""In-request stash so failed generation evidence commits with Process Outcome."""

from __future__ import annotations

from typing import Any

from src.contracts.observability.stage_report import validate_stage_report

_pending: dict[str, list[dict[str, Any]]] = {}
_DEFAULT_EVIDENCE_KEY = "_"


def record_pending_generation_evidence(
    *,
    invocation: dict[str, Any] | None = None,
    report: dict[str, Any] | None = None,
    process_uuid: str | None = None,
) -> None:
    item: dict[str, Any] = {}
    if invocation is not None:
        item["invocation"] = dict(invocation)
    if report is not None:
        item["report"] = validate_stage_report(report)
    if not item:
        return
    key = process_uuid or _DEFAULT_EVIDENCE_KEY
    _pending.setdefault(key, []).append(item)


def take_pending_generation_evidence(process_uuid: str | None = None) -> list[dict[str, Any]]:
    key = process_uuid or _DEFAULT_EVIDENCE_KEY
    return _pending.pop(key, [])


async def write_pending_generation_evidence_tx(tx: Any, process: dict[str, Any]) -> None:
    """Write stashed failed invocation/report rows inside the Outcome TX."""

    import json

    from src.contracts.common.ids import uuid7
    from src.contracts.common.time import utc_now
    from src.contracts.observability.stage_report import validate_stage_report

    now = utc_now()
    team = process["team_uuid"]
    execution = process["execution_uuid"]
    process_uuid = process["process_uuid"]
    task = process.get("task_uuid")
    trace = process.get("trace_uuid")
    for item in take_pending_generation_evidence(process_uuid):
        invocation = item.get("invocation")
        if isinstance(invocation, dict):
            from src.contracts.observability.stage_report import evidence_stage_key

            status = invocation.get("status") or "failed"
            stage_key = evidence_stage_key(invocation.get("stage_key") or "structurize")
            adapter_kind = invocation.get("adapter_kind") or "local_inference"
            if adapter_kind not in {"claude_cli", "local_inference", "local_vllm"}:
                adapter_kind = "local_inference"
            await tx.execute(
                "INSERT OR IGNORE INTO mkb_generation_invocations "
                "(invocation_uuid,team_uuid,execution_uuid,process_uuid,process_attempt,invocation_ordinal,"
                "invocation_kind,model_key,model_version,prompt_key,prompt_version,prompt_digest,"
                "schema_key,schema_version,schema_digest,input_digest,output_digest,error_digest,"
                "input_tokens,output_tokens,total_tokens,occurred_at,payload_extra,"
                "status,stage_key,error_code,adapter_kind,cli_structured_kind) "
                "VALUES (?,?,?,?,?,?,'generation',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    invocation.get("invocation_uuid") or uuid7(),
                    team,
                    execution,
                    process_uuid,
                    int(invocation.get("process_attempt") or 1),
                    int(invocation.get("invocation_ordinal") or 0),
                    invocation.get("model_key"),
                    invocation.get("model_version"),
                    invocation.get("prompt_key"),
                    invocation.get("prompt_version"),
                    invocation.get("prompt_digest"),
                    invocation.get("schema_key"),
                    invocation.get("schema_version"),
                    invocation.get("schema_digest"),
                    invocation.get("input_digest") or ("0" * 64),
                    invocation.get("output_digest"),
                    invocation.get("error_digest"),
                    invocation.get("input_tokens"),
                    invocation.get("output_tokens"),
                    invocation.get("total_tokens"),
                    now,
                    json.dumps({"capability_key": invocation.get("capability_key")}, ensure_ascii=False),
                    status,
                    stage_key,
                    invocation.get("error_code"),
                    adapter_kind,
                    invocation.get("cli_structured_kind"),
                ),
            )
        report = item.get("report")
        if isinstance(report, dict):
            projected = validate_stage_report(report)
            has_g0 = projected.get("has_g0")
            counts = projected.get("layer_counts") or {}
            await tx.execute(
                "INSERT INTO mkb_generation_stage_reports "
                "(report_uuid,team_uuid,trace_uuid,task_uuid,execution_uuid,process_uuid,stage_key,"
                "disposition,error_code,cli_structured_kind,has_g0,block_count,granularity_set,"
                "layer_counts,latency_ms,schema_digest,occurred_at,payload_extra) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    uuid7(),
                    team,
                    str(trace or "00000000-0000-4000-8000-000000000000"),
                    str(task or "00000000-0000-4000-8000-000000000000"),
                    execution,
                    process_uuid,
                    projected["stage_key"],
                    projected["disposition"],
                    projected.get("error_code"),
                    projected.get("cli_structured_kind"),
                    None if has_g0 is None else int(has_g0),
                    projected.get("block_count"),
                    projected.get("granularity_set"),
                    json.dumps(counts, ensure_ascii=False) if counts else None,
                    int(projected["latency_ms"]),
                    projected["schema_digest"],
                    now,
                    "{}",
                ),
            )
