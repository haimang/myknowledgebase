"""The caller-facing, polling-only MKB Task and synchronous retrieval surface."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from api.dependencies import BusinessToken, Ready
from src.contracts.api.models import (
    ExpectedRevisionRequest,
    RetrievalRequest,
    RetryRequest,
    TaskCreateRequest,
    TaskPatchRequest,
    TeamCreateRequest,
    TeamPatchRequest,
)
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import validate_external_uuid

router = APIRouter(prefix="/v1", tags=["tasks"])


def _team_path(team_uuid: str) -> str:
    return validate_external_uuid(team_uuid, field="team_uuid")


def _task_path(task_uuid: str) -> str:
    return validate_external_uuid(task_uuid, field="task_uuid")


@router.post("/teams", status_code=201)
async def create_team(request: Request, body: TeamCreateRequest, token: BusinessToken) -> Response:
    del token
    team, replay = await request.app.state.container.teams.create(body)
    return Response(
        content=__import__("json").dumps(team),
        media_type="application/json",
        status_code=200 if replay else 201,
    )


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
    if body.team_uuid != team_uuid:
        raise MkbError("team-path-mismatch", "Body team_uuid must match path", 422)
    task, replay = await request.app.state.container.tasks.create(body, token)
    return Response(
        content=__import__("json").dumps(task),
        media_type="application/json",
        status_code=200 if replay else 201,
        headers={"Location": task["links"]["self"]},
    )


@router.get("/teams/{team_uuid}/tasks")
async def list_tasks(
    request: Request,
    team_uuid: str,
    token: BusinessToken,
    status: str | None = None,
    request_intent: str | None = None,
    include_deleted: bool = False,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    del token
    items, next_cursor = await request.app.state.container.tasks.list(
        _team_path(team_uuid),
        status=status,
        request_intent=request_intent,
        include_deleted=include_deleted,
        limit=limit,
        cursor=cursor,
    )
    return {"items": items, "next_cursor": next_cursor}


@router.get("/teams/{team_uuid}/tasks/{task_uuid}")
async def get_task(request: Request, team_uuid: str, task_uuid: str, token: BusinessToken) -> dict[str, object]:
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


@router.post("/teams/{team_uuid}/retrieval:search")
async def retrieval_search(
    request: Request, team_uuid: str, body: RetrievalRequest, token: BusinessToken, ready: Ready
) -> dict[str, object]:
    """Canonical S10 route; service implementation is intentionally side-effect free."""

    del token, ready
    team_uuid = _team_path(team_uuid)
    if body.team_uuid != team_uuid:
        raise MkbError("team-path-mismatch", "Body team_uuid must match path", 422)
    return await request.app.state.container.retrieval.search(body)
