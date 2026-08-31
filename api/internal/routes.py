"""Internal-only, token-and-network guarded observability reads."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from api.dependencies import OperatorToken, require_operator_token
from api.internal.prompts import PromptCatalogPatch, PromptCatalogWrite
from src.contracts.api.models import (
    CleanupJobDebugView,
    CleanupResumeRequest,
    CommandReceiptView,
    ExecutionDebugView,
    GenerationControlRequest,
    OutboxRequeueRequest,
    ProcessDebugView,
)
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import validate_external_uuid

# Keep the router-level guard even while the bounded v1 operator surface is
# empty.  Any future read/repair endpoint therefore inherits token plus
# internal-network admission instead of accidentally becoming public.
router = APIRouter(prefix="/internal", tags=["internal"], dependencies=[Depends(require_operator_token)])


@router.get("/teams/{team_uuid}/processes/{process_uuid}", response_model=ProcessDebugView)
async def process_debug(request: Request, team_uuid: str, process_uuid: str, token: OperatorToken) -> ProcessDebugView:
    del token
    return await request.app.state.container.operator_control.process(
        validate_external_uuid(team_uuid, field="team_uuid"),
        validate_external_uuid(process_uuid, field="process_uuid"),
    )


@router.get("/teams/{team_uuid}/executions/{execution_uuid}", response_model=ExecutionDebugView)
async def execution_debug(request: Request, team_uuid: str, execution_uuid: str, token: OperatorToken) -> ExecutionDebugView:
    del token
    return await request.app.state.container.operator_control.execution(
        validate_external_uuid(team_uuid, field="team_uuid"),
        validate_external_uuid(execution_uuid, field="execution_uuid"),
    )


@router.get("/teams/{team_uuid}/cleanup/{cleanup_job_uuid}", response_model=CleanupJobDebugView)
async def cleanup_debug(request: Request, team_uuid: str, cleanup_job_uuid: str, token: OperatorToken) -> CleanupJobDebugView:
    del token
    return await request.app.state.container.operator_control.cleanup(
        validate_external_uuid(team_uuid, field="team_uuid"),
        validate_external_uuid(cleanup_job_uuid, field="cleanup_job_uuid"),
    )


@router.post(
    "/teams/{team_uuid}/outbox/{outbox_id}:requeue",
    response_model=CommandReceiptView,
)
async def requeue_outbox(
    request: Request,
    team_uuid: str,
    outbox_id: str,
    body: OutboxRequeueRequest,
    token: OperatorToken,
) -> CommandReceiptView:
    del token
    if not outbox_id or len(outbox_id) > 256:
        raise MkbError("OUTBOX_ID_INVALID", "Outbox identifier is invalid", 422)
    result = await request.app.state.container.operator_control.requeue_outbox(
        validate_external_uuid(team_uuid, field="team_uuid"),
        outbox_id,
        expected_generation=body.expected_generation,
        idempotency_key=body.idempotency_key,
    )
    return CommandReceiptView.model_validate(
        {
            "command_receipt_uuid": result["command_receipt_uuid"],
            "command_kind": "outbox.requeue",
            "target_kind": "outbox",
            "target_uuid": outbox_id,
            "disposition": result["disposition"],
            "expected_generation": body.expected_generation,
            "observed_generation": body.expected_generation,
            "result_ref": result.get("outbox_id"),
            "outbox_id": result.get("outbox_id"),
            "decided_at": result.get("decided_at"),
        }
    )


@router.post(
    "/teams/{team_uuid}/cleanup/{cleanup_job_uuid}:resume",
    response_model=CommandReceiptView,
)
async def resume_cleanup(
    request: Request,
    team_uuid: str,
    cleanup_job_uuid: str,
    body: CleanupResumeRequest,
    token: OperatorToken,
) -> CommandReceiptView:
    del token
    result = await request.app.state.container.operator_control.resume_cleanup(
        validate_external_uuid(team_uuid, field="team_uuid"),
        validate_external_uuid(cleanup_job_uuid, field="cleanup_job_uuid"),
        expected_revision=body.expected_revision,
        idempotency_key=body.idempotency_key,
    )
    return CommandReceiptView.model_validate(
        {
            "command_receipt_uuid": result["command_receipt_uuid"],
            "command_kind": "cleanup.resume",
            "target_kind": "cleanup_job",
            "target_uuid": cleanup_job_uuid,
            "disposition": result["disposition"],
            "expected_generation": body.expected_revision,
            "observed_generation": body.expected_revision,
            "result_ref": cleanup_job_uuid,
            "cleanup_job_uuid": cleanup_job_uuid,
            "decided_at": result.get("decided_at"),
        }
    )


@router.post(
    "/teams/{team_uuid}/executions/{execution_uuid}:stop",
    response_model=CommandReceiptView,
)
async def stop_execution(
    request: Request,
    team_uuid: str,
    execution_uuid: str,
    body: GenerationControlRequest,
    token: OperatorToken,
) -> CommandReceiptView:
    del token
    result = await request.app.state.container.operator_control.stop_execution(
        validate_external_uuid(team_uuid, field="team_uuid"),
        validate_external_uuid(execution_uuid, field="execution_uuid"),
        expected_generation=body.expected_generation,
        idempotency_key=body.idempotency_key,
    )
    return CommandReceiptView.model_validate(
        {
            "command_receipt_uuid": result["command_receipt_uuid"],
            "command_kind": "execution.stop",
            "target_kind": "execution",
            "target_uuid": execution_uuid,
            "disposition": result["disposition"],
            "expected_generation": body.expected_generation,
            "observed_generation": body.expected_generation,
            "result_ref": execution_uuid,
            "decided_at": result.get("decided_at"),
        }
    )


@router.post(
    "/teams/{team_uuid}/processes/{process_uuid}:restart",
    response_model=CommandReceiptView,
)
async def restart_process(
    request: Request,
    team_uuid: str,
    process_uuid: str,
    body: GenerationControlRequest,
    token: OperatorToken,
) -> CommandReceiptView:
    del token
    result = await request.app.state.container.operator_control.restart_process(
        validate_external_uuid(team_uuid, field="team_uuid"),
        validate_external_uuid(process_uuid, field="process_uuid"),
        expected_generation=body.expected_generation,
        idempotency_key=body.idempotency_key,
    )
    return CommandReceiptView.model_validate(
        {
            "command_receipt_uuid": result["command_receipt_uuid"],
            "command_kind": "process.restart",
            "target_kind": "process",
            "target_uuid": process_uuid,
            "disposition": result["disposition"],
            "expected_generation": body.expected_generation,
            "observed_generation": body.expected_generation + 1,
            "result_ref": result.get("result_ref"),
            "decided_at": result.get("decided_at"),
        }
    )


@router.get("/prompts")
async def list_prompts(
    request: Request,
    token: OperatorToken,
    prompt_id: str | None = None,
    role: str | None = None,
    status: str | None = "active",
) -> dict[str, object]:
    del token
    entries = await request.app.state.container.registry.list_prompt_catalog(
        prompt_id=prompt_id, role=role, status=status
    )
    return {"items": [entry.as_dict() for entry in entries]}


@router.get("/prompts/{prompt_id}")
async def get_prompt(
    request: Request,
    prompt_id: str,
    token: OperatorToken,
    version: str | None = None,
) -> dict[str, object]:
    del token
    entry = await request.app.state.container.registry.resolve_prompt(prompt_id, version=version)
    return entry.as_dict()


@router.post("/prompts", status_code=201)
async def create_prompt(
    request: Request,
    payload: PromptCatalogWrite,
    token: OperatorToken,
) -> dict[str, object]:
    del token
    # The service computes the digest from the checked-in bytes; the API never
    # accepts a body or caller-supplied hash as an alternate source of truth.
    entry = await request.app.state.container.registry.register_prompt(
        prompt_id=payload.prompt_id,
        prompt_version=payload.prompt_version,
        relative_path=payload.git_relative_path,
        role=payload.role,
        granularity_set=payload.granularity_set,
    )
    return entry.as_dict()


@router.patch("/prompts/{prompt_id}")
async def update_prompt(
    request: Request,
    prompt_id: str,
    payload: PromptCatalogPatch,
    token: OperatorToken,
) -> dict[str, object]:
    del token
    entry = await request.app.state.container.registry.register_prompt(
        prompt_id=prompt_id,
        prompt_version=payload.prompt_version,
        relative_path=payload.git_relative_path,
        role=payload.role,
        granularity_set=payload.granularity_set,
    )
    return entry.as_dict()


@router.delete("/prompts/{prompt_id}")
async def retire_prompt(
    request: Request,
    prompt_id: str,
    token: OperatorToken,
    version: str | None = None,
) -> dict[str, object]:
    del token
    entry = await request.app.state.container.registry.retire_prompt(prompt_id, version=version)
    return entry.as_dict()


@router.get("/teams/{team_uuid}/traces/{trace_uuid}/timeline")
async def timeline_by_trace(
    request: Request,
    team_uuid: str,
    trace_uuid: str,
    token: OperatorToken,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    """Read redacted, bounded event evidence; never mutate a workflow."""

    del token
    items, next_cursor = await request.app.state.container.observability.timeline_by_trace(
        validate_external_uuid(team_uuid, field="team_uuid"),
        validate_external_uuid(trace_uuid, field="trace_uuid"),
        limit=limit,
        cursor=cursor,
    )
    return {"items": items, "next_cursor": next_cursor}


@router.get("/teams/{team_uuid}/tasks/{task_uuid}/timeline")
async def timeline_by_task(
    request: Request,
    team_uuid: str,
    task_uuid: str,
    token: OperatorToken,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    del token
    items, next_cursor = await request.app.state.container.observability.timeline_by_task(
        validate_external_uuid(team_uuid, field="team_uuid"),
        validate_external_uuid(task_uuid, field="task_uuid"),
        limit=limit,
        cursor=cursor,
    )
    return {"items": items, "next_cursor": next_cursor}


@router.get("/teams/{team_uuid}/outbox/dead")
async def dead_outbox(
    request: Request,
    team_uuid: str,
    token: OperatorToken,
    kind: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    del token
    items, next_cursor = await request.app.state.container.observability.dead_outbox(
        validate_external_uuid(team_uuid, field="team_uuid"), kind=kind, limit=limit, cursor=cursor
    )
    return {"items": items, "next_cursor": next_cursor}


@router.get("/teams/{team_uuid}/security-audit")
async def security_audit(
    request: Request,
    team_uuid: str,
    token: OperatorToken,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    del token
    items, next_cursor = await request.app.state.container.observability.security_audit(
        validate_external_uuid(team_uuid, field="team_uuid"), limit=limit, cursor=cursor
    )
    return {"items": items, "next_cursor": next_cursor}
