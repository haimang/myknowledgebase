"""Task public projection helpers, cursors, and row visibility."""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any

from src.contracts.common.errors import MkbError, NotFoundError
from src.contracts.common.models import assert_safe_public_data
from src.contracts.common.time import normalize_rfc3339
from src.persistence.ports import UnitOfWork
from src.runtime.task.helpers import _json


class TaskViewsMixin:
    """Task public projection helpers, cursors, and row visibility."""

    @staticmethod
    def _links(team_uuid: str, task_uuid: str) -> dict[str, str]:
        root = f"/v1/teams/{team_uuid}/tasks/{task_uuid}"
        return {
            "self": root,
            "result": f"{root}/result",
            "items": f"{root}/items",
            "generations": f"{root}/generations",
            "gates": f"{root}/gates",
            "restarts": f"/v1/teams/{team_uuid}/task-restarts?source_task_uuid={task_uuid}",
            "lineage": f"/v1/teams/{team_uuid}/task-lineage?task_uuid={task_uuid}",
        }


    @classmethod
    def _view(cls, row: dict[str, Any], gate: dict[str, Any] | None = None) -> dict[str, Any]:
        deleted = row["deleted_at"] is not None
        error = None
        if row["error_code"]:
            error = {"code": row["error_code"], "message": row["error_message"] or "Task failed"}
        action_required = None
        if gate:
            review_summary = None
            try:
                target_data = json.loads(gate.get("review_target_json") or "{}")
                candidate = target_data.get("review_summary") if isinstance(target_data, dict) else None
                if isinstance(candidate, str):
                    assert_safe_public_data(candidate)
                    review_summary = candidate[:512]
            except (TypeError, ValueError, json.JSONDecodeError):
                # A malformed target must never become a raw database echo in
                # the Task aggregate. Gate detail/decision remains fail-closed.
                review_summary = None
            action_required = {
                "count": gate.get("open_gate_count", 1),
                "gate_uuid": gate["gate_uuid"],
                "gate_kind": gate["gate_kind"],
                "revision": gate["gate_revision"],
                "review_summary": review_summary,
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
            "SELECT g.*, t.review_target_json, "
            "(SELECT COUNT(*) FROM mkb_execution_gates open_gates "
            " WHERE open_gates.team_uuid=g.team_uuid AND open_gates.task_uuid=g.task_uuid "
            "   AND open_gates.status='open') AS open_gate_count "
            "FROM mkb_execution_gates g LEFT JOIN mkb_execution_gate_targets t "
            " ON t.team_uuid=g.team_uuid AND t.gate_uuid=g.gate_uuid "
            "WHERE g.team_uuid=? AND g.task_uuid=? AND g.status='open' "
            "ORDER BY g.opened_at DESC, g.gate_uuid DESC LIMIT 1",
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


    @staticmethod
    def _root_execution_role(workflow_role: str) -> str:
        """Map registry vocabulary to the durable Task-root vocabulary.

        The historical single graph uses ``root`` rows.  A registered-API
        collection needs the explicit ``scatter_root`` controller role; child
        graphs are internal fan-out targets and can never be selected at Task
        ingress.
        """

        if workflow_role == "single_root":
            return "root"
        if workflow_role == "scatter_root":
            return "scatter_root"
        raise MkbError("workflow-root-role-invalid", "Workflow cannot materialize a Task root execution", 503)


    @staticmethod
    def _encode_cursor(kind: str, **fields: Any) -> str:
        payload = _json({"kind": kind, **fields}).encode("utf-8")
        return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


    @staticmethod
    def _decode_cursor(cursor: str, *, kind: str) -> dict[str, Any]:
        try:
            padded = cursor + "=" * (-len(cursor) % 4)
            value = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        except (ValueError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError) as exc:
            raise MkbError("cursor-invalid", "Cursor is invalid", 422) from exc
        if not isinstance(value, dict) or value.get("kind") != kind:
            raise MkbError("cursor-invalid", "Cursor is invalid", 422)
        return value


    @staticmethod
    def _public_execution_status(status: str) -> str:
        """Map internal execution phases to the six-state Task vocabulary."""

        return {
            "created": "queued",
            "ready": "queued",
            "running": "running",
            "waiting": "running",
            "cancelling": "cancelling",
            "succeeded": "succeeded",
            "failed": "failed",
            "cancelled": "cancelled",
        }.get(status, "queued")


    @classmethod
    def _generation_view(cls, row: dict[str, Any]) -> dict[str, Any]:
        error = None
        if row.get("final_error_code"):
            error = {"code": row["final_error_code"]}
        return {
            "generation": row["generation"],
            "status": cls._public_execution_status(row["status"]),
            "counts": {
                "total": row["total_child_count"],
                "active": row["active_child_count"],
                "succeeded": row["succeeded_child_count"],
                "failed": row["failed_child_count"],
                # Child-execution axis only (D01 review R3).
                "cancelled": int(row["cancelled_child_count"] or 0)
                if row["cancelled_child_count"] is not None
                else 0,
            },
            "result_ref": row["result_ref"],
            "proof_ref": row["publication_proof_ref"],
            "error": error,
            "created_at": row["created_at"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
        }


    @staticmethod
    def _task_summary(row: dict[str, Any]) -> dict[str, Any]:
        error = {"code": row["error_code"]} if row.get("error_code") else None
        return {
            "task_uuid": row["task_uuid"],
            "status": row["status"],
            "current_generation": row["current_generation"],
            "result_ref": row["result_ref"],
            "proof_ref": row["proof_ref"],
            "error": error,
            "completed_at": row["completed_at"],
            "deleted_at": row["deleted_at"],
        }


    async def _root_execution(self, tx: UnitOfWork, team_uuid: str, task_uuid: str, generation: int) -> dict[str, Any]:
        row = await tx.fetchone(
            "SELECT * FROM mkb_executions WHERE team_uuid=? AND task_uuid=? AND generation=? "
            "AND parent_execution_uuid IS NULL AND root_execution_uuid=execution_uuid",
            (team_uuid, task_uuid, generation),
        )
        if row is None:
            raise NotFoundError("generation-not-found", "Task generation was not found")
        return row


    @staticmethod
    def _parse_gate_target(target: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
        """Validate the durable target before either projecting or deciding it."""

        try:
            raw = json.loads(target["review_target_json"])
            if not isinstance(raw, dict):
                raise ValueError("not an object")
            allowed_actions = raw.get("allowed_actions")
            expected_revision = raw.get("expected_execution_revision")
            if (
                not isinstance(allowed_actions, list)
                or not allowed_actions
                or any(action not in {"approve", "reject", "reclean"} for action in allowed_actions)
                or len(set(allowed_actions)) != len(allowed_actions)
                or not isinstance(expected_revision, int)
                or isinstance(expected_revision, bool)
                or raw.get("team_uuid") != gate["team_uuid"]
                or raw.get("task_uuid") != gate["task_uuid"]
                or raw.get("generation") != gate["generation"]
                or raw.get("waiting_ref") != gate["gate_uuid"]
            ):
                raise ValueError("target coordinates are incomplete")
            assert_safe_public_data(raw)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise MkbError("gate-target-invalid", "Gate target is not a valid control target", 409) from exc
        return raw


    def _gate_view(self, gate: dict[str, Any], target: dict[str, Any], target_data: dict[str, Any]) -> dict[str, Any]:
        review_summary = target_data.get("review_summary")
        if not isinstance(review_summary, str):
            review_summary = None
        elif len(review_summary) > 512:
            review_summary = review_summary[:512]
        root = self._links(gate["team_uuid"], gate["task_uuid"])["self"]
        return {
            "gate_uuid": gate["gate_uuid"],
            "gate_kind": gate["gate_kind"],
            "status": gate["status"],
            "revision": gate["gate_revision"],
            "target_digest": target["target_digest"],
            "allowed_actions": target_data["allowed_actions"] if gate["status"] == "open" else [],
            "review_summary": review_summary,
            "evidence": {"clean_artifact_digest": target["clean_artifact_digest"]},
            "opened_at": gate["opened_at"],
            "terminal_at": gate["terminal_at"],
            "links": {
                "self": f"{root}/gates/{gate['gate_uuid']}",
                "task": root,
            },
        }


    @staticmethod
    def _restart_view(row: dict[str, Any]) -> dict[str, Any]:
        target_task = None
        if row.get("target_task_uuid") is not None:
            target_task = {
                "task_uuid": row["target_task_uuid"],
                "status": row["target_task_status"],
                "current_generation": row["target_task_generation"],
                "result_ref": row["target_task_result_ref"],
                "proof_ref": row["target_task_proof_ref"],
                "error": {"code": row["target_task_error_code"]} if row["target_task_error_code"] else None,
                "completed_at": row["target_task_completed_at"],
                "deleted_at": row["target_task_deleted_at"],
            }
        return {
            "restart_uuid": row["restart_uuid"],
            "scope": row["restart_scope"],
            "source_task_uuid": row["source_task_uuid"],
            "source_generation": row["source_generation"],
            "intake_item_uuid": row["intake_item_uuid"],
            "intake_revision_uuid": row["intake_revision_uuid"],
            "restart_task_uuid": row["restart_task_uuid"],
            "target_generation": row["target_generation"],
            "admission_outcome": row["admission_outcome"],
            "decision_code": row["decision_code"],
            "requested_at": row["requested_at"],
            "decided_at": row["decided_at"],
            "target_task": target_task,
            "links": {
                "self": f"/v1/teams/{row['team_uuid']}/task-restarts/{row['restart_uuid']}",
                "lineage": f"/v1/teams/{row['team_uuid']}/task-lineage?restart_uuid={row['restart_uuid']}",
            },
        }


    @staticmethod
    def _restart_select() -> str:
        return (
            "SELECT r.*, t.task_uuid AS target_task_uuid, t.status AS target_task_status, "
            "t.current_generation AS target_task_generation, t.result_ref AS target_task_result_ref, "
            "t.proof_ref AS target_task_proof_ref, t.error_code AS target_task_error_code, "
            "t.completed_at AS target_task_completed_at, t.deleted_at AS target_task_deleted_at "
            "FROM mkb_task_restarts r LEFT JOIN mkb_tasks t "
            "ON t.team_uuid=r.team_uuid AND t.task_uuid=r.restart_task_uuid "
        )
