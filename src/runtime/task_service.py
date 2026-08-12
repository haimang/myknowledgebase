"""S01/S02 Task aggregate service.

The public API can only express Task commands. Execution and Process identities
remain internal, even though this service durably materializes root execution
records in the same Task/Audit/outbox transaction.
"""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any

from src.contracts.api.models import (
    ExpectedRevisionRequest,
    RetryRequest,
    TaskCreateRequest,
    TaskPatchRequest,
)
from src.contracts.common.errors import ConflictError, MkbError, NotFoundError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.models import TaskStatus
from src.contracts.common.time import normalize_rfc3339, utc_now
from src.persistence.ports import PersistencePort, UnitOfWork
from src.services.events import DomainEventWriter
from src.services.teams import TeamService


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _encode_task_list_cursor(**fields: Any) -> str:
    """Produce an opaque, URL-safe Task-list continuation token."""

    payload = _json(fields).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_task_list_cursor(cursor: str) -> dict[str, Any]:
    """Decode only the Task-list token shape; callers bind its filters."""

    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (ValueError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError) as exc:
        raise MkbError("cursor-invalid", "Task cursor is invalid", 422) from exc
    if not isinstance(value, dict):
        raise MkbError("cursor-invalid", "Task cursor is invalid", 422)
    return value


class TaskService:
    _REQUEST_INTENTS = frozenset(
        {
            "intake.ingest",
            "intake.rebuild",
            "intake.update_metadata",
            "intake.deactivate",
            "intake.reactivate",
            "intake.delete",
            "index.rebuild",
        }
    )
    _PRIORITIES = frozenset({"low", "normal", "high", "urgent"})

    def __init__(self, persistence: PersistencePort, teams: TeamService, events: DomainEventWriter) -> None:
        self.persistence = persistence
        self.teams = teams
        self.events = events

    @staticmethod
    def _links(team_uuid: str, task_uuid: str) -> dict[str, str]:
        root = f"/v1/teams/{team_uuid}/tasks/{task_uuid}"
        return {
            "self": root,
            "result": f"{root}/result",
            "items": f"{root}/items",
            "generations": f"{root}/generations",
            "gates": f"{root}/gates",
        }

    @classmethod
    def _view(cls, row: dict[str, Any], gate: dict[str, Any] | None = None) -> dict[str, Any]:
        deleted = row["deleted_at"] is not None
        error = None
        if row["error_code"]:
            error = {"code": row["error_code"], "message": row["error_message"] or "Task failed"}
        action_required = None
        if gate:
            action_required = {
                "gate_uuid": gate["gate_uuid"],
                "gate_kind": gate["gate_kind"],
                "revision": gate["gate_revision"],
                "href": f"{cls._links(row['team_uuid'], row['task_uuid'])['gates']}/{gate['gate_uuid']}",
            }
        return {
            "team_uuid": row["team_uuid"],
            "task_uuid": row["task_uuid"],
            "trace_uuid": row["trace_uuid"],
            "schema_version": row["schema_version"],
            "request_intent": row["request_intent"],
            "status": row["status"],
            "revision": row["row_revision"],
            "current_generation": row["current_generation"],
            "title": row["title"] or None,
            "description": row["description"],
            "priority": row["priority"],
            "deadline_at": row["deadline_at"],
            "payload_extra": json.loads(row["payload_extra"]),
            "received_at": row["received_at"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "result_ref": row["result_ref"],
            "proof_ref": row["proof_ref"],
            "error": error,
            "action_required": action_required,
            "deleted_at": row["deleted_at"] if deleted else None,
            "counts": {
                "total": row["cnt_total"],
                "required": row["cnt_required"],
                "active": row["cnt_active"],
                "succeeded": row["cnt_succeeded"],
                "failed": row["cnt_failed"],
                "cancelled": row["cnt_cancelled"],
                "skipped": row["cnt_skipped"],
            },
            "links": cls._links(row["team_uuid"], row["task_uuid"]),
        }

    async def _open_gate(self, tx: UnitOfWork, team_uuid: str, task_uuid: str) -> dict[str, Any] | None:
        return await tx.fetchone(
            "SELECT * FROM mkb_execution_gates WHERE team_uuid=? AND task_uuid=? AND status='open' "
            "ORDER BY opened_at DESC LIMIT 1",
            (team_uuid, task_uuid),
        )

    async def _get_row(self, tx: UnitOfWork, team_uuid: str, task_uuid: str) -> dict[str, Any]:
        row = await tx.fetchone("SELECT * FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?", (team_uuid, task_uuid))
        if row is None:
            raise NotFoundError("task-not-found", "Task was not found")
        return row

    @staticmethod
    def _require_public_visibility(row: dict[str, Any]) -> None:
        """Make a Task tombstone a real public visibility fence.

        Lineage and restart governance deliberately bypass this helper because
        those surfaces are specified to retain tombstone identity.  Ordinary
        Task reads and commands must not resurrect a hidden Task through a
        subresource.
        """

        if row["deleted_at"] is not None:
            error = {"code": row["error_code"]} if row["error_code"] else None
            raise MkbError(
                "task-deleted",
                "Task has been soft-deleted",
                410,
                {
                    "tombstone": {
                        "task_uuid": row["task_uuid"],
                        "status": row["status"],
                        "current_generation": row["current_generation"],
                        "result_ref": row["result_ref"],
                        "proof_ref": row["proof_ref"],
                        "error": error,
                        "completed_at": row["completed_at"],
                        "deleted_at": row["deleted_at"],
                    }
                },
                trace_uuid=row["trace_uuid"],
            )

    @staticmethod
    def _assert_future_deadline(deadline_at: str | None, *, received_at: str) -> None:
        """Reject an already-expired create-time scheduling fence."""

        if deadline_at is None:
            return
        try:
            # Both values have already been normalized to canonical UTC
            # RFC3339 strings.  Their lexicographic order is chronological.
            deadline = normalize_rfc3339(deadline_at)
            received = normalize_rfc3339(received_at)
        except (ValueError, MkbError) as exc:  # defensive seam for non-HTTP callers
            raise MkbError("task-deadline-invalid", "Task deadline is invalid", 422) from exc
        if deadline <= received:
            raise MkbError("task-deadline-invalid", "Task deadline must be later than receipt", 422)

    async def create(self, request: TaskCreateRequest, caller_token_fingerprint: str) -> tuple[dict[str, Any], bool]:
        fingerprint = stable_digest(request.model_dump(mode="json"))
        now = utc_now()
        root_execution_uuid = uuid7()
        config_snapshot_digest = stable_digest(
            {
                "request_intent": request.request_intent,
                "schema_version": request.schema_version,
                "prompt_contract": "promptA/B/C.v1",
                "models": ["qwen-vl-2b@v1", "qwen35-a3b@v1"],
            }
        )
        # A logical immutable ref becomes a catalogued object once the config
        # snapshot service is initialized; it is never a floating registry alias.
        config_snapshot_ref = f"mkbconfig:v1:{config_snapshot_digest}"
        async with self.persistence.transaction() as tx:
            team = await tx.fetchone("SELECT status FROM mkb_teams WHERE team_uuid=?", (request.team_uuid,))
            if team is None:
                raise NotFoundError("team-not-registered", "Team is not registered")
            if team["status"] != "active":
                raise ConflictError("team-not-active", "Team is not active")
            existing = await tx.fetchone(
                "SELECT * FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?", (request.team_uuid, request.task_uuid)
            )
            if existing:
                if existing["creation_fingerprint"] != fingerprint:
                    raise ConflictError("task-identity-conflict", "Task identity has a different creation fingerprint")
                return self._view(existing, await self._open_gate(tx, request.team_uuid, request.task_uuid)), True
            self._assert_future_deadline(request.deadline_at, received_at=now)
            await tx.execute(
                "INSERT INTO mkb_tasks "
                "(team_uuid,task_uuid,trace_uuid,schema_version,request_intent,creation_fingerprint,audit_bound,title,"
                "description,priority,deadline_at,status,row_revision,current_generation,current_root_execution_uuid,received_at,"
                "created_at,updated_at,payload_extra) "
                "VALUES (?,?,?,?,?,?,1,?,?,?,?,'queued',0,1,?,?,?,?,?)",
                (
                    request.team_uuid,
                    request.task_uuid,
                    request.trace_uuid,
                    request.schema_version,
                    request.request_intent,
                    fingerprint,
                    request.title or "",
                    request.description,
                    request.priority,
                    request.deadline_at,
                    root_execution_uuid,
                    now,
                    now,
                    now,
                    _json(request.payload_extra),
                ),
            )
            await tx.execute(
                "INSERT INTO mkb_task_audits "
                "(team_uuid,task_uuid,request_envelope_digest,strict_payload_json,caller_token_fingerprint,received_at,payload_extra) "
                "VALUES (?,?,?,?,?,?,'{}')",
                (
                    request.team_uuid,
                    request.task_uuid,
                    fingerprint,
                    _json(request.model_dump(mode="json")),
                    caller_token_fingerprint,
                    now,
                ),
            )
            await self._insert_root_execution(
                tx,
                team_uuid=request.team_uuid,
                task_uuid=request.task_uuid,
                trace_uuid=request.trace_uuid,
                execution_uuid=root_execution_uuid,
                generation=1,
                config_snapshot_ref=config_snapshot_ref,
                config_snapshot_digest=config_snapshot_digest,
                retry_of_execution_uuid=None,
            )
            await self._enqueue(
                tx,
                request.team_uuid,
                "wake_execution",
                {"execution_uuid": root_execution_uuid, "task_uuid": request.task_uuid, "generation": 1},
                f"wake-execution:{root_execution_uuid}",
            )
            await self.events.write(
                tx,
                team_uuid=request.team_uuid,
                trace_uuid=request.trace_uuid,
                event_type="task.created",
                aggregate="task",
                summary="Task accepted",
                actor_kind="upstream",
                task_uuid=request.task_uuid,
                payload={"request_intent": request.request_intent, "generation": 1},
            )
            created = await self._get_row(tx, request.team_uuid, request.task_uuid)
        return self._view(created), False

    async def _insert_root_execution(
        self,
        tx: UnitOfWork,
        *,
        team_uuid: str,
        task_uuid: str,
        trace_uuid: str,
        execution_uuid: str,
        generation: int,
        config_snapshot_ref: str,
        config_snapshot_digest: str,
        retry_of_execution_uuid: str | None,
    ) -> None:
        now = utc_now()
        # Workflow IDs and compiled digest are immutable binding coordinates. The
        # built-in workflow registry later supplies the corresponding durable rows.
        workflow_uuid = uuid7()
        workflow_revision_uuid = uuid7()
        compiled_digest = stable_digest({"workflow": "lsrag.default", "revision": 1})
        binding_digest = stable_digest({"config_snapshot": config_snapshot_digest, "workflow": compiled_digest})
        await tx.execute(
            "INSERT INTO mkb_executions "
            "(execution_uuid,team_uuid,task_uuid,trace_uuid,generation,root_execution_uuid,parent_execution_uuid,"
            "retry_of_execution_uuid,execution_role,target_kind,workflow_uuid,workflow_revision_uuid,compiled_digest,"
            "resolver_decision_digest,domain_binding_digest,s05_binding_digest,config_snapshot_ref,config_snapshot_digest,"
            "status,row_revision,created_at,updated_at,payload_extra) "
            "VALUES (?,?,?,?,?,?,NULL,?,'root','task',?,?,?,?,?,?,?,?,'ready',0,?,?,'{}')",
            (
                execution_uuid,
                team_uuid,
                task_uuid,
                trace_uuid,
                generation,
                execution_uuid,
                retry_of_execution_uuid,
                workflow_uuid,
                workflow_revision_uuid,
                compiled_digest,
                stable_digest({"workflow": compiled_digest}),
                binding_digest,
                binding_digest,
                config_snapshot_ref,
                config_snapshot_digest,
                now,
                now,
            ),
        )

    async def _enqueue(
        self,
        tx: UnitOfWork,
        team_uuid: str,
        kind: str,
        payload: dict[str, Any],
        dedupe_key: str,
    ) -> None:
        now = utc_now()
        payload_json = _json(payload)
        await tx.execute(
            "INSERT OR IGNORE INTO mkb_outbox "
            "(outbox_id,team_uuid,kind,payload_json,payload_digest,dedupe_key,status,available_at,created_at,updated_at,payload_extra) "
            "VALUES (?,?,?,?,?,?,'pending',?,?,?,'{}')",
            (uuid7(), team_uuid, kind, payload_json, stable_digest(payload), dedupe_key, now, now, now),
        )

    async def get(self, team_uuid: str, task_uuid: str, *, include_deleted: bool = False) -> dict[str, Any]:
        async with self.persistence.transaction() as tx:
            row = await self._get_row(tx, team_uuid, task_uuid)
            gate = await self._open_gate(tx, team_uuid, task_uuid)
        if row["deleted_at"] and not include_deleted:
            self._require_public_visibility(row)
        return self._view(row, gate)

    async def list(
        self,
        team_uuid: str,
        *,
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
    ) -> tuple[list[dict[str, Any]], str | None]:
        if status is not None and status not in {item.value for item in TaskStatus}:
            raise MkbError("task-status-invalid", "Task status filter is invalid", 422)
        if request_intent is not None and request_intent not in self._REQUEST_INTENTS:
            raise MkbError("task-intent-invalid", "Task request intent filter is invalid", 422)
        if priority is not None and priority not in self._PRIORITIES:
            raise MkbError("task-priority-invalid", "Task priority filter is invalid", 422)
        if created_at_from is not None:
            created_at_from = normalize_rfc3339(created_at_from, field="created_at_from")
        if created_at_to is not None:
            created_at_to = normalize_rfc3339(created_at_to, field="created_at_to")
        if updated_at_from is not None:
            updated_at_from = normalize_rfc3339(updated_at_from, field="updated_at_from")
        if updated_at_to is not None:
            updated_at_to = normalize_rfc3339(updated_at_to, field="updated_at_to")
        if created_at_from is not None and created_at_to is not None and created_at_from > created_at_to:
            raise MkbError("task-time-range-invalid", "Task creation time range is invalid", 422)
        if updated_at_from is not None and updated_at_to is not None and updated_at_from > updated_at_to:
            raise MkbError("task-time-range-invalid", "Task update time range is invalid", 422)
        limit = min(max(limit, 1), 100)
        conditions = ["team_uuid=?"]
        params: list[Any] = [team_uuid]
        if not include_deleted:
            conditions.append("deleted_at IS NULL")
        if status:
            conditions.append("status=?")
            params.append(status)
        if request_intent:
            conditions.append("request_intent=?")
            params.append(request_intent)
        if priority:
            conditions.append("priority=?")
            params.append(priority)
        if created_at_from is not None:
            conditions.append("julianday(created_at)>=julianday(?)")
            params.append(created_at_from)
        if created_at_to is not None:
            conditions.append("julianday(created_at)<=julianday(?)")
            params.append(created_at_to)
        if updated_at_from is not None:
            conditions.append("julianday(updated_at)>=julianday(?)")
            params.append(updated_at_from)
        if updated_at_to is not None:
            conditions.append("julianday(updated_at)<=julianday(?)")
            params.append(updated_at_to)
        filter_digest = stable_digest(
            {
                "team_uuid": team_uuid,
                "status": status,
                "request_intent": request_intent,
                "priority": priority,
                "created_at_from": created_at_from,
                "created_at_to": created_at_to,
                "updated_at_from": updated_at_from,
                "updated_at_to": updated_at_to,
                "include_deleted": include_deleted,
            }
        )
        if cursor:
            decoded = _decode_task_list_cursor(cursor)
            created_at, task_uuid = decoded.get("created_at"), decoded.get("task_uuid")
            if (
                decoded.get("filter_digest") != filter_digest
                or not isinstance(created_at, str)
                or not isinstance(task_uuid, str)
            ):
                raise MkbError("cursor-invalid", "Task cursor is invalid", 422)
            conditions.append("(created_at < ? OR (created_at = ? AND task_uuid < ?))")
            params.extend([created_at, created_at, task_uuid])
        params.append(limit + 1)
        query = (
            "SELECT * FROM mkb_tasks WHERE "
            + " AND ".join(conditions)
            + " ORDER BY created_at DESC, task_uuid DESC LIMIT ?"
        )
        async with self.persistence.transaction() as tx:
            rows = await tx.fetchall(query, tuple(params))
        more = len(rows) > limit
        page = rows[:limit]
        next_cursor = (
            _encode_task_list_cursor(
                filter_digest=filter_digest,
                created_at=page[-1]["created_at"],
                task_uuid=page[-1]["task_uuid"],
            )
            if more and page
            else None
        )
        return [self._view(row) for row in page], next_cursor

    async def patch(self, team_uuid: str, task_uuid: str, request: TaskPatchRequest) -> dict[str, Any]:
        async with self.persistence.transaction() as tx:
            row = await self._get_row(tx, team_uuid, task_uuid)
            self._require_public_visibility(row)
            if row["row_revision"] != request.expected_revision:
                raise ConflictError(
                    "revision-conflict", "Task revision is stale", {"current_revision": row["row_revision"]}
                )
            if request.priority is not None and row["status"] != "queued":
                raise ConflictError("task-priority-locked", "Task priority is mutable only while queued")
            title = request.title if request.title is not None else row["title"]
            description = request.description if request.description is not None else row["description"]
            priority = request.priority if request.priority is not None else row["priority"]
            extra = request.payload_extra if "payload_extra" in request.model_fields_set else json.loads(row["payload_extra"])
            await tx.execute(
                "UPDATE mkb_tasks SET title=?,description=?,priority=?,payload_extra=?,row_revision=row_revision+1,updated_at=? "
                "WHERE team_uuid=? AND task_uuid=? AND row_revision=?",
                (
                    title,
                    description,
                    priority,
                    _json(extra),
                    utc_now(),
                    team_uuid,
                    task_uuid,
                    request.expected_revision,
                ),
            )
            updated = await self._get_row(tx, team_uuid, task_uuid)
        return self._view(updated)

    async def cancel(
        self, team_uuid: str, task_uuid: str, request: ExpectedRevisionRequest
    ) -> tuple[dict[str, Any], bool]:
        async with self.persistence.transaction() as tx:
            row = await self._get_row(tx, team_uuid, task_uuid)
            self._require_public_visibility(row)
            if row["row_revision"] != request.expected_revision:
                raise ConflictError(
                    "revision-conflict", "Task revision is stale", {"current_revision": row["row_revision"]}
                )
            if row["status"] in {"succeeded", "failed", "cancelled"}:
                return self._view(row), False
            now = utc_now()
            await tx.execute(
                "UPDATE mkb_tasks SET status='cancelling',cancel_requested_at=?,row_revision=row_revision+1,updated_at=? "
                "WHERE team_uuid=? AND task_uuid=? AND row_revision=? AND status IN ('queued','running','cancelling')",
                (now, now, team_uuid, task_uuid, request.expected_revision),
            )
            await tx.execute(
                "UPDATE mkb_executions SET status='cancelling',cancel_requested_at=?,cancel_command_revision=?,updated_at=? "
                "WHERE execution_uuid=? AND status NOT IN ('succeeded','failed','cancelled')",
                (now, request.expected_revision + 1, now, row["current_root_execution_uuid"]),
            )
            await self._enqueue(
                tx,
                team_uuid,
                "cancel_execution",
                {"execution_uuid": row["current_root_execution_uuid"], "task_uuid": task_uuid},
                f"cancel-execution:{row['current_root_execution_uuid']}:{request.expected_revision + 1}",
            )
            await self.events.write(
                tx,
                team_uuid=team_uuid,
                trace_uuid=row["trace_uuid"],
                event_type="task.cancel_requested",
                aggregate="task",
                summary="Task cancellation requested",
                task_uuid=task_uuid,
            )
            updated = await self._get_row(tx, team_uuid, task_uuid)
        return self._view(updated), True

    async def retry(self, team_uuid: str, task_uuid: str, request: RetryRequest) -> dict[str, Any]:
        command_digest = stable_digest({"expected_revision": request.expected_revision, "reason": request.reason})
        async with self.persistence.transaction() as tx:
            row = await self._get_row(tx, team_uuid, task_uuid)
            self._require_public_visibility(row)
            # A retry command is replayed by its immutable command digest,
            # not by the Task's *current* generation/revision.  The first
            # accepted attempt has already advanced both coordinates, so
            # checking CAS first would turn a normal network replay into a
            # false revision conflict and invite duplicate manual retries.
            replay = await tx.fetchone(
                "SELECT restart_uuid FROM mkb_task_restarts WHERE team_uuid=? AND source_task_uuid=? "
                "AND restart_scope='full_task' AND admission_outcome='accepted' AND command_fingerprint=? "
                "ORDER BY requested_at DESC,restart_uuid DESC LIMIT 1",
                (team_uuid, task_uuid, command_digest),
            )
            if replay is not None:
                return self._view(row)
            if row["row_revision"] != request.expected_revision:
                raise ConflictError(
                    "revision-conflict", "Task revision is stale", {"current_revision": row["row_revision"]}
                )
            if row["status"] in {"queued", "running", "cancelling"}:
                raise ConflictError("task-active", "An active Task cannot be retried")
            if row["status"] == "succeeded":
                raise ConflictError("retry-not-allowed", "Succeeded Task must be rebuilt as a new Task")
            prior_root = row["current_root_execution_uuid"]
            target_generation = row["current_generation"] + 1
            root_execution_uuid = uuid7()
            previous = await tx.fetchone("SELECT * FROM mkb_executions WHERE execution_uuid=?", (prior_root,))
            if previous is None:
                raise MkbError("execution-missing", "Task current execution is missing", 503)
            restart_uuid = uuid7()
            now = utc_now()
            await tx.execute(
                "INSERT INTO mkb_task_restarts "
                "(restart_uuid,team_uuid,restart_scope,source_task_uuid,source_generation,source_root_execution_uuid,"
                "restart_task_uuid,target_generation,target_root_execution_uuid,causation_trace_uuid,command_fingerprint,"
                "admission_outcome,decision_code,reason,requested_at,decided_at,payload_extra) "
                "VALUES (?,?,'full_task',?,?,?,?,?,?,?,?,'accepted','retry-accepted',?,?,?,'{}')",
                (
                    restart_uuid,
                    team_uuid,
                    task_uuid,
                    row["current_generation"],
                    prior_root,
                    task_uuid,
                    target_generation,
                    root_execution_uuid,
                    row["trace_uuid"],
                    command_digest,
                    request.reason,
                    now,
                    now,
                ),
            )
            await self._insert_root_execution(
                tx,
                team_uuid=team_uuid,
                task_uuid=task_uuid,
                trace_uuid=row["trace_uuid"],
                execution_uuid=root_execution_uuid,
                generation=target_generation,
                config_snapshot_ref=previous["config_snapshot_ref"],
                config_snapshot_digest=previous["config_snapshot_digest"],
                retry_of_execution_uuid=prior_root,
            )
            await tx.execute(
                "UPDATE mkb_tasks SET status='queued',current_generation=?,current_root_execution_uuid=?,"
                "cancel_requested_at=NULL,intake_snapshot_uuid=NULL,change_set_uuid=NULL,"
                "cnt_total=0,cnt_required=0,cnt_active=0,cnt_succeeded=0,cnt_failed=0,cnt_cancelled=0,cnt_skipped=0,"
                "result_ref=NULL,proof_ref=NULL,error_code=NULL,error_message=NULL,started_at=NULL,completed_at=NULL,"
                "row_revision=row_revision+1,updated_at=? WHERE team_uuid=? AND task_uuid=? AND row_revision=?",
                (target_generation, root_execution_uuid, now, team_uuid, task_uuid, request.expected_revision),
            )
            await self._enqueue(
                tx,
                team_uuid,
                "wake_execution",
                {"execution_uuid": root_execution_uuid, "task_uuid": task_uuid, "generation": target_generation},
                f"wake-execution:{root_execution_uuid}",
            )
            await self.events.write(
                tx,
                team_uuid=team_uuid,
                trace_uuid=row["trace_uuid"],
                event_type="task.retry_accepted",
                aggregate="task",
                summary="Task full retry accepted",
                task_uuid=task_uuid,
                payload={"restart_uuid": restart_uuid, "target_generation": target_generation},
            )
            updated = await self._get_row(tx, team_uuid, task_uuid)
        return self._view(updated)

    async def result(self, team_uuid: str, task_uuid: str) -> tuple[dict[str, Any], int]:
        view = await self.get(team_uuid, task_uuid)
        status = view["status"]
        if status in {"queued", "running", "cancelling"}:
            return {"readiness": "not_ready", "task": view}, 202
        if status == "succeeded":
            return {
                "readiness": "ready",
                "task": view,
                "result_ref": view["result_ref"],
                "proof_ref": view["proof_ref"],
            }, 200
        if status == "failed":
            return {"readiness": "terminal_failed", "task": view}, 200
        return {"readiness": "terminal_cancelled", "task": view}, 200

    async def soft_delete(self, team_uuid: str, task_uuid: str, request: ExpectedRevisionRequest) -> dict[str, Any]:
        async with self.persistence.transaction() as tx:
            row = await self._get_row(tx, team_uuid, task_uuid)
            if row["row_revision"] != request.expected_revision:
                raise ConflictError(
                    "revision-conflict", "Task revision is stale", {"current_revision": row["row_revision"]}
                )
            if row["status"] not in {"succeeded", "failed", "cancelled"}:
                raise ConflictError("task-active", "Active Task must be cancelled before soft-delete")
            if row["deleted_at"]:
                return self._view(row)
            now = utc_now()
            await tx.execute(
                "UPDATE mkb_tasks SET deleted_at=?,deleted_actor='internal',deleted_reason=?,"
                "row_revision=row_revision+1,updated_at=? WHERE team_uuid=? AND task_uuid=? AND row_revision=?",
                (now, request.reason, now, team_uuid, task_uuid, request.expected_revision),
            )
            await self.events.write(
                tx,
                team_uuid=team_uuid,
                trace_uuid=row["trace_uuid"],
                event_type="task.soft_deleted",
                aggregate="task",
                summary="Task soft-deleted",
                task_uuid=task_uuid,
            )
            updated = await self._get_row(tx, team_uuid, task_uuid)
        return self._view(updated)

    async def transition_from_runtime(
        self,
        tx: UnitOfWork,
        *,
        team_uuid: str,
        task_uuid: str,
        expected_generation: int,
        target: TaskStatus,
        result_ref: str | None = None,
        proof_ref: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> bool:
        """Internal state owner: successful terminal transition requires a proof."""

        row = await self._get_row(tx, team_uuid, task_uuid)
        if row["current_generation"] != expected_generation:
            return False
        if target == TaskStatus.SUCCEEDED and not proof_ref:
            raise MkbError("task-proof-missing", "Task cannot succeed without a durable publication proof", 409)
        if row["status"] == "cancelling" and target == TaskStatus.SUCCEEDED:
            return False
        if target == TaskStatus.RUNNING and row["status"] != "queued":
            return False
        if target in {TaskStatus.SUCCEEDED, TaskStatus.FAILED} and row["status"] != "running":
            return False
        if target == TaskStatus.CANCELLED and row["status"] != "cancelling":
            return False
        now = utc_now()
        completed = (
            now if target in {TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED} else row["completed_at"]
        )
        await tx.execute(
            "UPDATE mkb_tasks SET status=?,result_ref=?,proof_ref=?,error_code=?,error_message=?,started_at=COALESCE(started_at,?),"
            "completed_at=?,row_revision=row_revision+1,updated_at=? WHERE team_uuid=? AND task_uuid=? AND current_generation=?",
            (
                target.value,
                result_ref,
                proof_ref,
                error_code,
                error_message,
                now if target == TaskStatus.RUNNING else None,
                completed,
                now,
                team_uuid,
                task_uuid,
                expected_generation,
            ),
        )
        await self.events.write(
            tx,
            team_uuid=team_uuid,
            trace_uuid=row["trace_uuid"],
            event_type="task.status_changed",
            aggregate="task",
            summary=f"Task transitioned to {target.value}",
            task_uuid=task_uuid,
            payload={"status": target.value, "generation": expected_generation},
        )
        return True
