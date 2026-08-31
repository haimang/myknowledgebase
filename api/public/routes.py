"""The caller-facing, polling-only MKB Task and synchronous retrieval surface."""

from __future__ import annotations

import json
import re
from urllib.parse import unquote

from fastapi import APIRouter, Query, Request, Response
from pydantic import ValidationError

from api.dependencies import BusinessToken, Ready
from src.contracts.api.generation import (
    GenerationArtifactPage,
    GenerationArtifactPointerPage,
    GenerationArtifactView,
)
from src.contracts.api.models import (
    CapabilityCatalogView,
    CatalogView,
    ExpectedRevisionRequest,
    GateDecisionRequest,
    IntakeItemListView,
    NamespaceListView,
    RetryRequest,
    TaskCreateRequest,
    TaskListView,
    TaskPatchRequest,
    TaskView,
    TeamCreateRequest,
    TeamPatchRequest,
    parse_retrieval_request,
)
from src.contracts.api.objects import ObjectCancelRequest, PublicObjectUploadView, PublicObjectView
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import validate_external_uuid
from src.contracts.storage.models import ObjectHandle
from src.services.generation_read import GenerationArtifactReadService

router = APIRouter(prefix="/v1", tags=["tasks"])


@router.get("/catalog", response_model=CatalogView, tags=["catalog"])
async def catalog(request: Request, token: BusinessToken) -> CatalogView:
    """Discover registered capabilities without exposing a graph selector."""

    del token
    container = request.app.state.container
    supplies = {
        "pdf.parse": container.pdf_parser is not None,
        "browser.render": container.browser_runtime is not None,
        "browser.print_pdf": container.browser_runtime is not None,
        "ocr.deterministic": container.deterministic_ocr is not None,
        "s11.multimodal": container.clean_llm is not None,
    }
    return await container.workflow_catalog.catalog(role=container.settings.deployment_role, available_supplies=supplies)


@router.get("/capabilities", response_model=list[CapabilityCatalogView], tags=["catalog"])
async def list_capabilities(request: Request, token: BusinessToken) -> list[CapabilityCatalogView]:
    del token
    container = request.app.state.container
    supplies = {
        "pdf.parse": container.pdf_parser is not None,
        "browser.render": container.browser_runtime is not None,
        "browser.print_pdf": container.browser_runtime is not None,
        "ocr.deterministic": container.deterministic_ocr is not None,
        "s11.multimodal": container.clean_llm is not None,
    }
    return [
        CapabilityCatalogView.model_validate(item)
        for item in container.capability_registry.availability(supplies)
    ]


@router.get("/teams/{team_uuid}/intake-items", response_model=IntakeItemListView, tags=["catalog"])
async def list_intake_items(
    request: Request,
    team_uuid: str,
    token: BusinessToken,
    source_kind: str | None = None,
    external_key: str | None = None,
    lifecycle_state: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    del token
    items, next_cursor = await request.app.state.container.workflow_catalog.items(
        _team_path(team_uuid),
        source_kind=source_kind,
        external_key=external_key,
        lifecycle_state=lifecycle_state,
        limit=limit,
        cursor=cursor,
    )
    return {"items": items, "next_cursor": next_cursor}


@router.get("/teams/{team_uuid}/namespaces", response_model=NamespaceListView, tags=["catalog"])
async def list_namespaces(
    request: Request,
    team_uuid: str,
    token: BusinessToken,
    status: str | None = "active",
    namespace_key: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    del token
    items, next_cursor = await request.app.state.container.workflow_catalog.namespaces(
        _team_path(team_uuid), status=status, namespace_key=namespace_key, limit=limit, cursor=cursor
    )
    return {"items": items, "next_cursor": next_cursor}


def _team_path(team_uuid: str) -> str:
    return validate_external_uuid(team_uuid, field="team_uuid")


def _task_path(task_uuid: str) -> str:
    return validate_external_uuid(task_uuid, field="task_uuid")


def _restart_path(restart_uuid: str) -> str:
    return validate_external_uuid(restart_uuid, field="restart_uuid")


def _gate_path(gate_uuid: str) -> str:
    return validate_external_uuid(gate_uuid, field="gate_uuid")


def _item_path(intake_item_uuid: str) -> str:
    return validate_external_uuid(intake_item_uuid, field="intake_item_uuid")


def _generation_artifact_path(generation_artifact_uuid: str) -> str:
    return validate_external_uuid(generation_artifact_uuid, field="generation_artifact_uuid")


def _public_object_view(stat, disposition: str, *, session_token: str | None = None) -> PublicObjectView:
    model = PublicObjectUploadView if session_token is not None else PublicObjectView
    return model(
        handle=stat.handle.value,
        digest=stat.sha256,
        size_bytes=stat.size_bytes,
        media_type=stat.media_type,
        disposition=disposition,
        session_token=session_token,
    )


def _object_handle_query(value: str) -> ObjectHandle:
    try:
        return ObjectHandle(value=value)
    except ValidationError as exc:
        raise MkbError("SEC_PATH_REJECTED", "Object handle is invalid", 422) from exc


def _upload_media_type(request: Request) -> str | None:
    value = request.headers.get("content-type")
    if value is None:
        return None
    media_type = value.split(";", 1)[0].strip().casefold()
    if not media_type or len(media_type) > 255:
        raise MkbError("OBJECT_MEDIA_TYPE_INVALID", "Declared object media type is invalid", 422)
    if media_type == "multipart/form-data":
        raise MkbError("OBJECT_MEDIA_TYPE_INVALID", "Object upload accepts a raw byte stream", 422)
    return media_type


def _expected_upload_digest(request: Request) -> str | None:
    value = request.headers.get("x-mkb-expected-sha256")
    if value is None:
        return None
    normalized = value.strip().casefold()
    if re.fullmatch(r"[0-9a-f]{64}", normalized) is None:
        raise MkbError("OBJECT_EXPECTED_DIGEST_INVALID", "Expected SHA-256 header is invalid", 422)
    return normalized


def _reject_filename_identity(request: Request) -> None:
    disposition = request.headers.get("content-disposition")
    decoded = unquote(disposition) if disposition else None
    if decoded and ("\x00" in decoded or "%00" in decoded.casefold()):
        raise MkbError("SEC_PATH_REJECTED", "Upload filenames cannot contain NUL", 422)
    if decoded and any(marker in decoded for marker in ("..", "/", "\\")):
        raise MkbError("SEC_PATH_REJECTED", "Upload filenames cannot contain path syntax", 422)


@router.post("/teams", status_code=201)
async def create_team(request: Request, body: TeamCreateRequest, token: BusinessToken) -> Response:
    del token
    team, replay = await request.app.state.container.teams.create(body)
    return Response(
        content=__import__("json").dumps(team),
        media_type="application/json",
        status_code=200 if replay else 201,
    )


@router.post("/teams/{team_uuid}/objects:upload", response_model=PublicObjectUploadView, status_code=201)
async def upload_object(
    request: Request,
    team_uuid: str,
    token: BusinessToken,
    ready: Ready,
) -> Response:
    del token, ready
    team_uuid = _team_path(team_uuid)
    _reject_filename_identity(request)
    record = await request.app.state.container.object_upload.upload(
        team_uuid=team_uuid,
        chunks=request.stream(),
        media_type=_upload_media_type(request),
        expected_sha256=_expected_upload_digest(request),
        idempotency_key=request.headers.get("idempotency-key"),
    )
    view = _public_object_view(record.stat, "pending", session_token=record.session_token)
    return Response(
        content=view.model_dump_json(exclude_none=True),
        media_type="application/json",
        status_code=200 if record.replay else 201,
    )


@router.get("/teams/{team_uuid}/objects:stat", response_model=PublicObjectView, response_model_exclude_none=True)
async def stat_object(
    request: Request,
    team_uuid: str,
    token: BusinessToken,
    handle: str = Query(min_length=1, max_length=256),
) -> PublicObjectView:
    del token
    status = await request.app.state.container.object_upload.stat(
        team_uuid=_team_path(team_uuid),
        handle=_object_handle_query(handle),
        session_token=request.headers.get("x-mkb-session-token"),
    )
    return _public_object_view(status.stat, status.disposition)


@router.post("/teams/{team_uuid}/objects:cancel", response_model=PublicObjectUploadView, response_model_exclude_none=True)
async def cancel_object(
    request: Request,
    team_uuid: str,
    body: ObjectCancelRequest,
    token: BusinessToken,
) -> PublicObjectView:
    del token
    team_uuid = _team_path(team_uuid)
    handle = _object_handle_query(body.handle)
    if body.session_token is not None:
        await request.app.state.container.object_upload_lifecycle.cancel_session(
            team_uuid=team_uuid,
            session_token=body.session_token,
        )
        status = await request.app.state.container.object_upload.stat(
            team_uuid=team_uuid,
            handle=handle,
            session_token=body.session_token,
        )
    else:
        await request.app.state.container.object_upload_lifecycle.cancel(team_uuid=team_uuid, handle=handle)
        status = await request.app.state.container.object_upload.stat(team_uuid=team_uuid, handle=handle)
    return _public_object_view(status.stat, status.disposition, session_token=body.session_token)


@router.get("/teams")
async def list_teams(request: Request, token: BusinessToken, status: str | None = None) -> dict[str, object]:
    del token
    return {"items": await request.app.state.container.teams.list(status)}


@router.get("/teams/{team_uuid}")
async def get_team(request: Request, team_uuid: str, token: BusinessToken) -> dict[str, object]:
    del token
    return await request.app.state.container.teams.get(_team_path(team_uuid))


@router.patch("/teams/{team_uuid}")
async def patch_team(
    request: Request, team_uuid: str, body: TeamPatchRequest, token: BusinessToken
) -> dict[str, object]:
    del token
    return await request.app.state.container.teams.patch(_team_path(team_uuid), body)


@router.post("/teams/{team_uuid}:activate")
async def activate_team(
    request: Request, team_uuid: str, body: ExpectedRevisionRequest, token: BusinessToken
) -> dict[str, object]:
    del token
    return await request.app.state.container.teams.transition(_team_path(team_uuid), "activate", body.expected_revision)


@router.post("/teams/{team_uuid}:deactivate")
async def deactivate_team(
    request: Request, team_uuid: str, body: ExpectedRevisionRequest, token: BusinessToken
) -> dict[str, object]:
    del token
    return await request.app.state.container.teams.transition(
        _team_path(team_uuid), "deactivate", body.expected_revision
    )


@router.delete("/teams/{team_uuid}")
async def delete_team(
    request: Request, team_uuid: str, body: ExpectedRevisionRequest, token: BusinessToken
) -> dict[str, object]:
    del token
    return await request.app.state.container.teams.transition(_team_path(team_uuid), "delete", body.expected_revision)


@router.post("/teams/{team_uuid}:restore")
async def restore_team(
    request: Request, team_uuid: str, body: ExpectedRevisionRequest, token: BusinessToken
) -> dict[str, object]:
    del token
    return await request.app.state.container.teams.transition(_team_path(team_uuid), "restore", body.expected_revision)


@router.post("/teams/{team_uuid}/tasks", status_code=201)
async def create_task(
    request: Request,
    team_uuid: str,
    body: TaskCreateRequest,
    token: BusinessToken,
    ready: Ready,
) -> Response:
    del ready
    team_uuid = _team_path(team_uuid)
    # Preserve the caller-owned root trace for any later safe error envelope.
    # Runtime IDs remain internal; this is only request correlation.
    request.state.trace_uuid = body.trace_uuid
    if body.team_uuid != team_uuid:
        raise MkbError("team-path-mismatch", "Body team_uuid must match path", 422)
    task, replay = await request.app.state.container.tasks.create(body, token)
    return Response(
        content=__import__("json").dumps(task),
        media_type="application/json",
        status_code=200 if replay else 201,
        headers={"Location": task["links"]["self"]},
    )


@router.get("/teams/{team_uuid}/tasks", response_model=TaskListView)
async def list_tasks(
    request: Request,
    team_uuid: str,
    token: BusinessToken,
    status: str | None = None,
    request_intent: str | None = None,
    priority: str | None = None,
    created_at_from: str | None = None,
    created_at_to: str | None = None,
    updated_at_from: str | None = None,
    updated_at_to: str | None = None,
    include_deleted: bool = False,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    del token
    items, next_cursor = await request.app.state.container.tasks.list(
        _team_path(team_uuid),
        status=status,
        request_intent=request_intent,
        priority=priority,
        created_at_from=created_at_from,
        created_at_to=created_at_to,
        updated_at_from=updated_at_from,
        updated_at_to=updated_at_to,
        include_deleted=include_deleted,
        limit=limit,
        cursor=cursor,
    )
    return {"items": items, "next_cursor": next_cursor}


@router.get("/teams/{team_uuid}/tasks/{task_uuid}", response_model=TaskView)
async def get_task(request: Request, team_uuid: str, task_uuid: str, token: BusinessToken) -> TaskView:
    del token
    return await request.app.state.container.tasks.get(_team_path(team_uuid), _task_path(task_uuid))


@router.patch("/teams/{team_uuid}/tasks/{task_uuid}")
async def patch_task(
    request: Request, team_uuid: str, task_uuid: str, body: TaskPatchRequest, token: BusinessToken
) -> dict[str, object]:
    del token
    return await request.app.state.container.tasks.patch(_team_path(team_uuid), _task_path(task_uuid), body)


@router.delete("/teams/{team_uuid}/tasks/{task_uuid}")
async def delete_task(
    request: Request, team_uuid: str, task_uuid: str, body: ExpectedRevisionRequest, token: BusinessToken
) -> dict[str, object]:
    del token
    return await request.app.state.container.tasks.soft_delete(_team_path(team_uuid), _task_path(task_uuid), body)


@router.post("/teams/{team_uuid}/tasks/{task_uuid}:cancel", status_code=202)
async def cancel_task(
    request: Request, team_uuid: str, task_uuid: str, body: ExpectedRevisionRequest, token: BusinessToken
) -> Response:
    del token
    task, accepted = await request.app.state.container.tasks.cancel(_team_path(team_uuid), _task_path(task_uuid), body)
    return Response(
        content=__import__("json").dumps(task), media_type="application/json", status_code=202 if accepted else 200
    )


@router.post("/teams/{team_uuid}/tasks/{task_uuid}:retry", status_code=202)
async def retry_task(
    request: Request, team_uuid: str, task_uuid: str, body: RetryRequest, token: BusinessToken, ready: Ready
) -> dict[str, object]:
    del token, ready
    return await request.app.state.container.tasks.retry(_team_path(team_uuid), _task_path(task_uuid), body)


@router.get("/teams/{team_uuid}/tasks/{task_uuid}/result")
async def task_result(request: Request, team_uuid: str, task_uuid: str, token: BusinessToken) -> Response:
    del token
    result, status = await request.app.state.container.tasks.result(_team_path(team_uuid), _task_path(task_uuid))
    return Response(content=__import__("json").dumps(result), media_type="application/json", status_code=status)


@router.get("/teams/{team_uuid}/tasks/{task_uuid}/generation-artifacts")
async def list_generation_artifacts(
    request: Request,
    team_uuid: str,
    task_uuid: str,
    token: BusinessToken,
    artifact_type: str | None = None,
    validation_disposition: str | None = None,
    generation: int | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> GenerationArtifactPage:
    """Read immutable Task-owned history without addressing runtime identities."""

    del token
    service = GenerationArtifactReadService(request.app.state.container.persistence)
    items, next_cursor = await service.list_artifacts(
        _team_path(team_uuid),
        _task_path(task_uuid),
        artifact_type=artifact_type,
        validation_disposition=validation_disposition,
        generation=generation,
        limit=limit,
        cursor=cursor,
    )
    return GenerationArtifactPage.model_validate({"items": items, "next_cursor": next_cursor})


@router.get("/teams/{team_uuid}/tasks/{task_uuid}/generation-artifacts/{generation_artifact_uuid}")
async def get_generation_artifact(
    request: Request,
    team_uuid: str,
    task_uuid: str,
    generation_artifact_uuid: str,
    token: BusinessToken,
) -> GenerationArtifactView:
    del token
    service = GenerationArtifactReadService(request.app.state.container.persistence)
    return await service.get_artifact(
        _team_path(team_uuid),
        _task_path(task_uuid),
        _generation_artifact_path(generation_artifact_uuid),
    )


@router.get("/teams/{team_uuid}/tasks/{task_uuid}/generation-artifact-pointers")
async def list_generation_artifact_pointers(
    request: Request,
    team_uuid: str,
    task_uuid: str,
    token: BusinessToken,
    artifact_type: str | None = None,
    generation: int | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> GenerationArtifactPointerPage:
    """Read current full-valid pointer selections through their owning Task."""

    del token
    service = GenerationArtifactReadService(request.app.state.container.persistence)
    items, next_cursor = await service.list_pointers(
        _team_path(team_uuid),
        _task_path(task_uuid),
        artifact_type=artifact_type,
        generation=generation,
        limit=limit,
        cursor=cursor,
    )
    return GenerationArtifactPointerPage.model_validate({"items": items, "next_cursor": next_cursor})


@router.get("/teams/{team_uuid}/tasks/{task_uuid}/items")
async def task_items(
    request: Request,
    team_uuid: str,
    task_uuid: str,
    token: BusinessToken,
    generation: int | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    """Bounded membership-derived scatter projection; never child executions."""

    del token
    items, next_cursor = await request.app.state.container.tasks.items(
        _team_path(team_uuid),
        _task_path(task_uuid),
        generation=generation,
        limit=limit,
        cursor=cursor,
    )
    return {"items": items, "next_cursor": next_cursor}


@router.get("/teams/{team_uuid}/tasks/{task_uuid}/generations")
async def task_generations(
    request: Request,
    team_uuid: str,
    task_uuid: str,
    token: BusinessToken,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    """Read stable generation summaries without exposing their execution IDs."""

    del token
    items, next_cursor = await request.app.state.container.tasks.generations(
        _team_path(team_uuid), _task_path(task_uuid), limit=limit, cursor=cursor
    )
    return {"items": items, "next_cursor": next_cursor}


@router.get("/teams/{team_uuid}/tasks/{task_uuid}/gates")
async def task_gates(
    request: Request,
    team_uuid: str,
    task_uuid: str,
    token: BusinessToken,
    status: str | None = "open",
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    del token
    items, next_cursor = await request.app.state.container.tasks.gates(
        _team_path(team_uuid), _task_path(task_uuid), status=status, limit=limit, cursor=cursor
    )
    return {"items": items, "next_cursor": next_cursor}


@router.get("/teams/{team_uuid}/tasks/{task_uuid}/gates/{gate_uuid}")
async def get_task_gate(
    request: Request, team_uuid: str, task_uuid: str, gate_uuid: str, token: BusinessToken
) -> dict[str, object]:
    del token
    return await request.app.state.container.tasks.gate(
        _team_path(team_uuid), _task_path(task_uuid), _gate_path(gate_uuid)
    )


@router.post("/teams/{team_uuid}/tasks/{task_uuid}/gates/{gate_uuid}:decide")
async def decide_task_gate(
    request: Request,
    team_uuid: str,
    task_uuid: str,
    gate_uuid: str,
    body: GateDecisionRequest,
    token: BusinessToken,
    ready: Ready,
) -> dict[str, object]:
    """Commit a Task-scoped human decision; runtime advancement remains async."""

    del ready
    return await request.app.state.container.tasks.decide_gate(
        _team_path(team_uuid),
        _task_path(task_uuid),
        _gate_path(gate_uuid),
        body,
        token,
    )


@router.get("/teams/{team_uuid}/task-restarts")
async def list_task_restarts(
    request: Request,
    team_uuid: str,
    token: BusinessToken,
    restart_uuid: str | None = None,
    source_task_uuid: str | None = None,
    restart_task_uuid: str | None = None,
    intake_item_uuid: str | None = None,
    scope: str | None = None,
    admission_outcome: str | None = None,
    current_task_status: str | None = None,
    requested_at_from: str | None = None,
    requested_at_to: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    del token
    items, next_cursor = await request.app.state.container.tasks.restarts(
        _team_path(team_uuid),
        restart_uuid=_restart_path(restart_uuid) if restart_uuid else None,
        source_task_uuid=_task_path(source_task_uuid) if source_task_uuid else None,
        restart_task_uuid=_task_path(restart_task_uuid) if restart_task_uuid else None,
        intake_item_uuid=_item_path(intake_item_uuid) if intake_item_uuid else None,
        scope=scope,
        admission_outcome=admission_outcome,
        current_task_status=current_task_status,
        requested_at_from=requested_at_from,
        requested_at_to=requested_at_to,
        limit=limit,
        cursor=cursor,
    )
    return {"items": items, "next_cursor": next_cursor}


@router.get("/teams/{team_uuid}/task-restarts/{restart_uuid}")
async def get_task_restart(
    request: Request, team_uuid: str, restart_uuid: str, token: BusinessToken
) -> dict[str, object]:
    del token
    return await request.app.state.container.tasks.restart(_team_path(team_uuid), _restart_path(restart_uuid))


@router.get("/teams/{team_uuid}/task-lineage")
async def task_lineage(
    request: Request,
    team_uuid: str,
    token: BusinessToken,
    restart_uuid: str | None = None,
    task_uuid: str | None = None,
    intake_item_uuid: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    del token
    return await request.app.state.container.tasks.lineage(
        _team_path(team_uuid),
        restart_uuid=_restart_path(restart_uuid) if restart_uuid else None,
        task_uuid=_task_path(task_uuid) if task_uuid else None,
        intake_item_uuid=_item_path(intake_item_uuid) if intake_item_uuid else None,
        limit=limit,
        cursor=cursor,
    )


@router.post("/teams/{team_uuid}/retrieval:search")
async def retrieval_search(
    request: Request, team_uuid: str, token: BusinessToken, ready: Ready
) -> dict[str, object]:
    """Canonical S10 route; service implementation is intentionally side-effect free."""

    del token, ready
    team_uuid = _team_path(team_uuid)
    try:
        payload = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise MkbError("RETRIEVE_SCHEMA_INVALID", "Retrieval request must be valid JSON", 422) from exc
    body = parse_retrieval_request(payload)
    if body.team_uuid != team_uuid:
        # Retrieval has its own public error taxonomy: callers must be able
        # to distinguish an invalid search scope from a Task-write mismatch.
        raise MkbError("RETRIEVE_SCHEMA_TEAM_MISMATCH", "Body team_uuid must match path", 422)
    return await request.app.state.container.retrieval.search(body)
