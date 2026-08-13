"""Single owned Task status projection helper used by command and runtime paths.

Success-while-cancelling is allowed (success-wins): a root Execution that
reaches validated terminal success may project Task to succeeded even when
cancel was already accepted, matching the live CAS filter that only excludes
already-terminal Task rows.
"""

from __future__ import annotations

from src.contracts.common.errors import MkbError
from src.contracts.common.models import TaskStatus
from src.contracts.common.time import utc_now
from src.persistence.ports import UnitOfWork
from src.services.events import DomainEventWriter


async def project_task_status_tx(
    tx: UnitOfWork,
    *,
    team_uuid: str,
    task_uuid: str,
    target: TaskStatus,
    events: DomainEventWriter | None = None,
    trace_uuid: str | None = None,
    expected_generation: int | None = None,
    current_root_execution_uuid: str | None = None,
    result_ref: str | None = None,
    proof_ref: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> bool:
    """Project Task aggregate status from a root Execution runtime transition.

    Returns True when a row was updated. Root-only callers must pass
    ``current_root_execution_uuid`` for terminal updates so a stale root cannot
    overwrite a newer generation's Task.
    """

    row = await tx.fetchone(
        "SELECT * FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
        (team_uuid, task_uuid),
    )
    if row is None:
        return False
    if expected_generation is not None and row["current_generation"] != expected_generation:
        return False
    if current_root_execution_uuid is not None and row["current_root_execution_uuid"] != current_root_execution_uuid:
        return False

    if target == TaskStatus.SUCCEEDED and not proof_ref:
        raise MkbError("task-proof-missing", "Task cannot succeed without a durable publication proof", 409)

    status = row["status"]
    if target == TaskStatus.RUNNING:
        if status != "queued":
            return False
    elif target == TaskStatus.SUCCEEDED:
        # Success-wins: running or cancelling may become succeeded.
        if status not in {"running", "cancelling"}:
            return False
    elif target == TaskStatus.FAILED:
        if status not in {"running", "cancelling", "queued"}:
            return False
    elif target == TaskStatus.CANCELLED:
        if status != "cancelling":
            return False
    else:
        return False

    now = utc_now()
    completed = (
        now if target in {TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED} else row["completed_at"]
    )
    started = now if target == TaskStatus.RUNNING else None
    updated = await tx.execute(
        "UPDATE mkb_tasks SET status=?,result_ref=COALESCE(?,result_ref),proof_ref=COALESCE(?,proof_ref),"
        "error_code=?,error_message=?,started_at=COALESCE(started_at,?),"
        "completed_at=?,row_revision=row_revision+1,updated_at=? "
        "WHERE team_uuid=? AND task_uuid=? AND status=? AND row_revision=?",
        (
            target.value,
            result_ref,
            proof_ref,
            error_code,
            error_message,
            started,
            completed,
            now,
            team_uuid,
            task_uuid,
            status,
            row["row_revision"],
        ),
    )
    if updated.rowcount != 1:
        return False
    if events is not None:
        await events.write(
            tx,
            team_uuid=team_uuid,
            trace_uuid=trace_uuid or row["trace_uuid"],
            event_type="task.status_changed",
            aggregate="task",
            summary=f"Task transitioned to {target.value}",
            task_uuid=task_uuid,
            payload={
                "status": target.value,
                "generation": row["current_generation"],
                "source": "runtime_projection",
            },
        )
    return True


__all__ = ["project_task_status_tx"]
