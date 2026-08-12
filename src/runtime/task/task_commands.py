"""Task get/list/patch/cancel/retry/result and soft-delete."""

from __future__ import annotations

import json
from typing import Any

from src.contracts.api.models import (
    ExpectedRevisionRequest,
    RetryRequest,
    TaskPatchRequest,
)
from src.contracts.common.errors import ConflictError, MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.models import TaskStatus
from src.contracts.common.time import normalize_rfc3339, utc_now
from src.persistence.ports import UnitOfWork
from src.runtime.task.helpers import _decode_task_list_cursor, _encode_task_list_cursor, _json


class TaskCommandsMixin:
    """Task get/list/patch/cancel/retry/result and soft-delete."""

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
                workflow_uuid=previous["workflow_uuid"],
                workflow_revision_uuid=previous["workflow_revision_uuid"],
                compiled_digest=previous["compiled_digest"],
                domain_binding_digest=previous["domain_binding_digest"],
                s05_binding_digest=previous["s05_binding_digest"],
                manifest_ref=previous["manifest_ref"],
                manifest_digest=previous["manifest_digest"],
                execution_role=previous["execution_role"],
                retry_of_execution_uuid=prior_root,
            )
            if self.config_snapshots is not None:
                await self._link_execution_object_refs(
                    tx,
                    team_uuid=team_uuid,
                    execution_uuid=root_execution_uuid,
                    config_digest=previous["config_snapshot_digest"],
                    manifest_digest=previous["manifest_digest"],
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
        """Internal state owner: successful terminal transition requires a proof.

        Delegates to :func:`project_task_status_tx` so command tests and the
        workflow runtime share one success-wins projection contract.
        """

        from src.runtime.task.task_projection import project_task_status_tx

        return await project_task_status_tx(
            tx,
            team_uuid=team_uuid,
            task_uuid=task_uuid,
            target=target,
            events=self.events,
            expected_generation=expected_generation,
            result_ref=result_ref,
            proof_ref=proof_ref,
            error_code=error_code,
            error_message=error_message,
        )
