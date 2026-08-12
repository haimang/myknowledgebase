"""Items, generations, gates, restarts, and lineage projections."""

from __future__ import annotations

from typing import Any

from src.contracts.api.models import (
    GateDecisionRequest,
)
from src.contracts.common.errors import ConflictError, MkbError, NotFoundError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import normalize_rfc3339, utc_now
from src.persistence.ports import UnitOfWork
from src.runtime.task.helpers import _json


class TaskProjectionsMixin:
    """Items, generations, gates, restarts, and lineage projections."""

    async def items(
        self,
        team_uuid: str,
        task_uuid: str,
        *,
        generation: int | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Return the immutable membership-derived scatter projection.

        Membership is the collection SSOT.  Child execution rows only provide
        a terminal summary; they are deliberately not identities in this API.
        """

        limit = min(max(limit, 1), 100)
        async with self.persistence.transaction() as tx:
            task = await self._get_row(tx, team_uuid, task_uuid)
            self._require_public_visibility(task)
            selected_generation = generation if generation is not None else task["current_generation"]
            if selected_generation < 1:
                raise MkbError("generation-invalid", "generation must be positive", 422)
            root = await self._root_execution(tx, team_uuid, task_uuid, selected_generation)
            snapshot_uuid = root["intake_snapshot_uuid"] or (
                task["intake_snapshot_uuid"] if selected_generation == task["current_generation"] else None
            )
            if snapshot_uuid is None:
                if cursor:
                    raise MkbError("cursor-invalid", "Cursor does not match this Task generation", 422)
                return [], None

            after_ordinal = -1
            if cursor:
                decoded = self._decode_cursor(cursor, kind="task-items")
                if (
                    decoded.get("task_uuid") != task_uuid
                    or decoded.get("generation") != selected_generation
                    or decoded.get("snapshot_uuid") != snapshot_uuid
                    or not isinstance(decoded.get("after_ordinal"), int)
                ):
                    raise MkbError("cursor-invalid", "Cursor does not match this Task generation", 422)
                after_ordinal = decoded["after_ordinal"]

            rows = await tx.fetchall(
                "SELECT m.*, "
                "(SELECT e.status FROM mkb_executions e WHERE e.team_uuid=m.team_uuid AND e.task_uuid=? "
                " AND e.generation=? AND e.parent_execution_uuid=? AND e.target_uuid=m.intake_item_uuid "
                " ORDER BY e.created_at DESC LIMIT 1) AS child_status, "
                "(SELECT e.result_ref FROM mkb_executions e WHERE e.team_uuid=m.team_uuid AND e.task_uuid=? "
                " AND e.generation=? AND e.parent_execution_uuid=? AND e.target_uuid=m.intake_item_uuid "
                " ORDER BY e.created_at DESC LIMIT 1) AS child_result_ref, "
                "(SELECT e.publication_proof_ref FROM mkb_executions e WHERE e.team_uuid=m.team_uuid "
                " AND e.task_uuid=? AND e.generation=? AND e.parent_execution_uuid=? AND e.target_uuid=m.intake_item_uuid "
                " ORDER BY e.created_at DESC LIMIT 1) AS child_proof_ref, "
                "(SELECT e.final_error_code FROM mkb_executions e WHERE e.team_uuid=m.team_uuid "
                " AND e.task_uuid=? AND e.generation=? AND e.parent_execution_uuid=? AND e.target_uuid=m.intake_item_uuid "
                " ORDER BY e.created_at DESC LIMIT 1) AS child_error_code, "
                "EXISTS(SELECT 1 FROM mkb_publication_proofs p "
                " JOIN mkb_index_active_pointers ip ON ip.team_uuid=p.team_uuid "
                "  AND ip.intake_item_uuid=p.intake_item_uuid AND ip.last_proof_uuid=p.proof_uuid "
                "  AND ip.lifecycle_state='active' "
                " WHERE p.team_uuid=m.team_uuid AND p.intake_item_uuid=m.intake_item_uuid "
                "  AND (m.observed_revision_uuid IS NULL OR p.intake_revision_uuid=m.observed_revision_uuid)) "
                " AS publication_ready "
                "FROM mkb_intake_snapshot_memberships m "
                "WHERE m.team_uuid=? AND m.intake_snapshot_uuid=? AND m.member_ordinal>? "
                "ORDER BY m.member_ordinal ASC LIMIT ?",
                (
                    task_uuid,
                    selected_generation,
                    root["execution_uuid"],
                    task_uuid,
                    selected_generation,
                    root["execution_uuid"],
                    task_uuid,
                    selected_generation,
                    root["execution_uuid"],
                    task_uuid,
                    selected_generation,
                    root["execution_uuid"],
                    team_uuid,
                    snapshot_uuid,
                    after_ordinal,
                    limit + 1,
                ),
            )

        more = len(rows) > limit
        page = rows[:limit]
        root_link = self._links(team_uuid, task_uuid)["self"]
        items: list[dict[str, Any]] = []
        for row in page:
            child_status = row["child_status"]
            if not row["required"]:
                outcome = "skipped"
            elif child_status == "succeeded":
                outcome = "succeeded"
            elif child_status == "failed":
                outcome = "failed"
            elif child_status == "cancelled":
                outcome = "cancelled"
            else:
                outcome = "active"
            error = {"code": row["child_error_code"]} if row["child_error_code"] else None
            items.append(
                {
                    "member_ordinal": row["member_ordinal"],
                    "intake_item_uuid": row["intake_item_uuid"],
                    "intake_revision_uuid": row["observed_revision_uuid"],
                    "external_key": row["normalized_external_key"],
                    "required": bool(row["required"]),
                    "outcome": outcome,
                    "publication_ready": bool(row["publication_ready"]),
                    "result_ref": row["child_result_ref"],
                    "proof_ref": row["child_proof_ref"],
                    "error": error,
                    "links": {"task": root_link},
                }
            )
        next_cursor = None
        if more and page:
            next_cursor = self._encode_cursor(
                "task-items",
                task_uuid=task_uuid,
                generation=selected_generation,
                snapshot_uuid=snapshot_uuid,
                after_ordinal=page[-1]["member_ordinal"],
            )
        return items, next_cursor


    async def generations(
        self,
        team_uuid: str,
        task_uuid: str,
        *,
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        limit = min(max(limit, 1), 100)
        before_generation: int | None = None
        if cursor:
            decoded = self._decode_cursor(cursor, kind="task-generations")
            if decoded.get("task_uuid") != task_uuid or not isinstance(decoded.get("before_generation"), int):
                raise MkbError("cursor-invalid", "Cursor is invalid", 422)
            before_generation = decoded["before_generation"]
        conditions = ["team_uuid=?", "task_uuid=?", "parent_execution_uuid IS NULL", "root_execution_uuid=execution_uuid"]
        params: list[Any] = [team_uuid, task_uuid]
        if before_generation is not None:
            conditions.append("generation<?")
            params.append(before_generation)
        params.append(limit + 1)
        async with self.persistence.transaction() as tx:
            task = await self._get_row(tx, team_uuid, task_uuid)
            self._require_public_visibility(task)
            rows = await tx.fetchall(
                "SELECT * FROM mkb_executions WHERE " + " AND ".join(conditions) + " ORDER BY generation DESC LIMIT ?",
                tuple(params),
            )
        more = len(rows) > limit
        page = rows[:limit]
        next_cursor = (
            self._encode_cursor("task-generations", task_uuid=task_uuid, before_generation=page[-1]["generation"])
            if more and page
            else None
        )
        return [self._generation_view(row) for row in page], next_cursor


    async def _gate_and_target(
        self, tx: UnitOfWork, team_uuid: str, task_uuid: str, gate_uuid: str
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        gate = await tx.fetchone(
            "SELECT * FROM mkb_execution_gates WHERE team_uuid=? AND task_uuid=? AND gate_uuid=?",
            (team_uuid, task_uuid, gate_uuid),
        )
        if gate is None:
            raise NotFoundError("gate-not-found", "Gate was not found for this Task")
        target = await tx.fetchone(
            "SELECT * FROM mkb_execution_gate_targets WHERE team_uuid=? AND gate_uuid=?",
            (team_uuid, gate_uuid),
        )
        if target is None:
            raise MkbError("gate-target-invalid", "Gate target is unavailable", 409)
        return gate, target, self._parse_gate_target(target, gate)


    async def gates(
        self,
        team_uuid: str,
        task_uuid: str,
        *,
        status: str | None = "open",
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        if status is not None and status not in {"open", "released", "rejected", "superseded"}:
            raise MkbError("gate-status-invalid", "Gate status filter is invalid", 422)
        limit = min(max(limit, 1), 100)
        conditions = ["team_uuid=?", "task_uuid=?"]
        params: list[Any] = [team_uuid, task_uuid]
        if status is not None:
            conditions.append("status=?")
            params.append(status)
        if cursor:
            decoded = self._decode_cursor(cursor, kind="task-gates")
            opened_at, gate_uuid = decoded.get("opened_at"), decoded.get("gate_uuid")
            if (
                decoded.get("task_uuid") != task_uuid
                or decoded.get("status") != status
                or not isinstance(opened_at, str)
                or not isinstance(gate_uuid, str)
            ):
                raise MkbError("cursor-invalid", "Cursor is invalid", 422)
            conditions.append("(opened_at < ? OR (opened_at = ? AND gate_uuid < ?))")
            params.extend([opened_at, opened_at, gate_uuid])
        params.append(limit + 1)
        async with self.persistence.transaction() as tx:
            task = await self._get_row(tx, team_uuid, task_uuid)
            self._require_public_visibility(task)
            rows = await tx.fetchall(
                "SELECT * FROM mkb_execution_gates WHERE "
                + " AND ".join(conditions)
                + " ORDER BY opened_at DESC, gate_uuid DESC LIMIT ?",
                tuple(params),
            )
            page = rows[:limit]
            views: list[dict[str, Any]] = []
            for gate in page:
                target = await tx.fetchone(
                    "SELECT * FROM mkb_execution_gate_targets WHERE team_uuid=? AND gate_uuid=?",
                    (team_uuid, gate["gate_uuid"]),
                )
                if target is None:
                    raise MkbError("gate-target-invalid", "Gate target is unavailable", 409)
                views.append(self._gate_view(gate, target, self._parse_gate_target(target, gate)))
        more = len(rows) > limit
        next_cursor = (
            self._encode_cursor(
                "task-gates",
                task_uuid=task_uuid,
                status=status,
                opened_at=page[-1]["opened_at"],
                gate_uuid=page[-1]["gate_uuid"],
            )
            if more and page
            else None
        )
        return views, next_cursor


    async def gate(self, team_uuid: str, task_uuid: str, gate_uuid: str) -> dict[str, Any]:
        async with self.persistence.transaction() as tx:
            task = await self._get_row(tx, team_uuid, task_uuid)
            self._require_public_visibility(task)
            gate, target, target_data = await self._gate_and_target(tx, team_uuid, task_uuid, gate_uuid)
        return self._gate_view(gate, target, target_data)


    async def decide_gate(
        self,
        team_uuid: str,
        task_uuid: str,
        gate_uuid: str,
        request: GateDecisionRequest,
        actor_fingerprint: str,
    ) -> dict[str, Any]:
        """Append a decision and atomically release the same waiting execution.

        The outbox carries the durable decision after the commit.  The workflow
        runtime consumes it idempotently; an HTTP acknowledgement is never a
        substitute for route advancement.
        """

        decision_extra: dict[str, Any] = {"actor_evidence": "internal_token"}
        if request.reason is not None:
            decision_extra["reason"] = request.reason
        if request.payload_extra:
            decision_extra["evidence"] = request.payload_extra
        command = {
            "expected_gate_revision": request.expected_gate_revision,
            "target_digest": request.target_digest,
            "action": request.action,
            "idempotency_key": request.idempotency_key,
            "actor_fingerprint": actor_fingerprint,
            "payload_extra": decision_extra,
        }
        decision_digest = stable_digest(command)
        async with self.persistence.transaction() as tx:
            task = await self._get_row(tx, team_uuid, task_uuid)
            self._require_public_visibility(task)
            gate, target, target_data = await self._gate_and_target(tx, team_uuid, task_uuid, gate_uuid)
            existing = await tx.fetchone(
                "SELECT * FROM mkb_execution_gate_decisions WHERE gate_uuid=? AND idempotency_key=?",
                (gate_uuid, request.idempotency_key),
            )
            if existing is not None:
                if existing["decision_digest"] != decision_digest:
                    raise ConflictError(
                        "gate-idempotency-conflict", "Gate idempotency key was reused with a different decision"
                    )
                return {
                    "committed": True,
                    "idempotent": True,
                    "decision_uuid": existing["decision_uuid"],
                    "gate": self._gate_view(gate, target, target_data),
                }
            if gate["status"] != "open":
                raise ConflictError("gate-terminal", "Gate is already terminal")
            if gate["gate_revision"] != request.expected_gate_revision:
                raise ConflictError(
                    "gate-revision-conflict",
                    "Gate revision is stale",
                    {"current_revision": gate["gate_revision"]},
                )
            if target["target_digest"] != request.target_digest:
                raise ConflictError("gate-target-conflict", "Gate target digest is stale")
            if request.action not in target_data["allowed_actions"]:
                raise ConflictError("gate-action-not-allowed", "Action is not allowed for this gate target")
            execution = await tx.fetchone(
                "SELECT * FROM mkb_executions WHERE execution_uuid=? AND team_uuid=? AND task_uuid=? AND generation=?",
                (gate["execution_uuid"], team_uuid, task_uuid, gate["generation"]),
            )
            if (
                execution is None
                or execution["status"] != "waiting"
                or execution["waiting_ref"] != gate_uuid
                or execution["row_revision"] != target_data["expected_execution_revision"]
            ):
                raise ConflictError("gate-execution-stale", "Gate no longer controls the expected execution")
            now = utc_now()
            decision_uuid = uuid7()
            await tx.execute(
                "INSERT INTO mkb_execution_gate_decisions "
                "(decision_uuid,gate_uuid,team_uuid,expected_gate_revision,action,actor_fingerprint,idempotency_key,"
                "target_digest,decision_digest,created_at,payload_extra) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    decision_uuid,
                    gate_uuid,
                    team_uuid,
                    request.expected_gate_revision,
                    request.action,
                    actor_fingerprint,
                    request.idempotency_key,
                    request.target_digest,
                    decision_digest,
                    now,
                    _json(decision_extra),
                ),
            )
            terminal_status = "rejected" if request.action == "reject" else "released"
            gate_update = await tx.execute(
                "UPDATE mkb_execution_gates SET status=?,gate_revision=gate_revision+1,terminal_at=? "
                "WHERE gate_uuid=? AND team_uuid=? AND task_uuid=? AND status='open' AND gate_revision=?",
                (terminal_status, now, gate_uuid, team_uuid, task_uuid, request.expected_gate_revision),
            )
            if gate_update.rowcount != 1:
                raise ConflictError("gate-revision-conflict", "Gate changed while the decision was being committed")
            execution_update = await tx.execute(
                "UPDATE mkb_executions SET status='running',waiting_reason=NULL,waiting_ref=NULL,next_wake_at=?,"
                "row_revision=row_revision+1,updated_at=? WHERE execution_uuid=? AND team_uuid=? AND task_uuid=? "
                "AND generation=? AND status='waiting' AND waiting_ref=? AND row_revision=?",
                (
                    now,
                    now,
                    gate["execution_uuid"],
                    team_uuid,
                    task_uuid,
                    gate["generation"],
                    gate_uuid,
                    target_data["expected_execution_revision"],
                ),
            )
            if execution_update.rowcount != 1:
                raise ConflictError("gate-execution-stale", "Execution changed while the decision was being committed")
            await self._enqueue(
                tx,
                team_uuid,
                "gate_decision",
                {
                    "gate_uuid": gate_uuid,
                    "task_uuid": task_uuid,
                    "generation": gate["generation"],
                    "action": request.action,
                    "decision_uuid": decision_uuid,
                },
                f"gate-decision:{decision_uuid}",
            )
            await self.events.write(
                tx,
                team_uuid=team_uuid,
                trace_uuid=execution["trace_uuid"],
                event_type="gate.decided",
                aggregate="gate",
                summary="Gate decision committed",
                actor_kind="upstream",
                task_uuid=task_uuid,
                execution_uuid=gate["execution_uuid"],
                payload={"gate_uuid": gate_uuid, "decision_uuid": decision_uuid, "action": request.action},
            )
            updated_gate, updated_target, updated_target_data = await self._gate_and_target(
                tx, team_uuid, task_uuid, gate_uuid
            )
        return {
            "committed": True,
            "idempotent": False,
            "decision_uuid": decision_uuid,
            "gate": self._gate_view(updated_gate, updated_target, updated_target_data),
        }


    async def restarts(
        self,
        team_uuid: str,
        *,
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
    ) -> tuple[list[dict[str, Any]], str | None]:
        if scope is not None and scope not in {"atomic_intake_item", "full_task"}:
            raise MkbError("restart-scope-invalid", "Restart scope filter is invalid", 422)
        if admission_outcome is not None and admission_outcome not in {"accepted", "rejected"}:
            raise MkbError("restart-outcome-invalid", "Restart outcome filter is invalid", 422)
        if current_task_status is not None and current_task_status not in {
            "queued",
            "running",
            "cancelling",
            "succeeded",
            "failed",
            "cancelled",
        }:
            raise MkbError("task-status-invalid", "Task status filter is invalid", 422)
        if requested_at_from is not None:
            requested_at_from = normalize_rfc3339(requested_at_from, field="requested_at_from")
        if requested_at_to is not None:
            requested_at_to = normalize_rfc3339(requested_at_to, field="requested_at_to")
        if requested_at_from is not None and requested_at_to is not None and requested_at_from > requested_at_to:
            raise MkbError("restart-time-range-invalid", "Restart time range is invalid", 422)
        limit = min(max(limit, 1), 100)
        conditions = ["r.team_uuid=?"]
        params: list[Any] = [team_uuid]
        for column, value in (
            ("r.restart_uuid", restart_uuid),
            ("r.source_task_uuid", source_task_uuid),
            ("r.restart_task_uuid", restart_task_uuid),
            ("r.intake_item_uuid", intake_item_uuid),
            ("r.restart_scope", scope),
            ("r.admission_outcome", admission_outcome),
            ("t.status", current_task_status),
        ):
            if value is not None:
                conditions.append(f"{column}=?")
                params.append(value)
        if requested_at_from is not None:
            # Durable rows may have microsecond precision while public range
            # bounds are canonicalized to milliseconds.  ``julianday`` keeps
            # the comparison temporal rather than relying on variable-width
            # RFC3339 text ordering.
            conditions.append("julianday(r.requested_at)>=julianday(?)")
            params.append(requested_at_from)
        if requested_at_to is not None:
            conditions.append("julianday(r.requested_at)<=julianday(?)")
            params.append(requested_at_to)
        filter_digest = stable_digest(
            {
                "team_uuid": team_uuid,
                "restart_uuid": restart_uuid,
                "source_task_uuid": source_task_uuid,
                "restart_task_uuid": restart_task_uuid,
                "intake_item_uuid": intake_item_uuid,
                "scope": scope,
                "admission_outcome": admission_outcome,
                "current_task_status": current_task_status,
                "requested_at_from": requested_at_from,
                "requested_at_to": requested_at_to,
            }
        )
        if cursor:
            decoded = self._decode_cursor(cursor, kind="task-restarts")
            requested_at, restart_uuid = decoded.get("requested_at"), decoded.get("restart_uuid")
            if (
                decoded.get("filter_digest") != filter_digest
                or not isinstance(requested_at, str)
                or not isinstance(restart_uuid, str)
            ):
                raise MkbError("cursor-invalid", "Cursor is invalid", 422)
            conditions.append("(r.requested_at < ? OR (r.requested_at = ? AND r.restart_uuid < ?))")
            params.extend([requested_at, requested_at, restart_uuid])
        params.append(limit + 1)
        async with self.persistence.transaction() as tx:
            rows = await tx.fetchall(
                self._restart_select()
                + "WHERE "
                + " AND ".join(conditions)
                + " ORDER BY r.requested_at DESC, r.restart_uuid DESC LIMIT ?",
                tuple(params),
            )
        more = len(rows) > limit
        page = rows[:limit]
        next_cursor = (
            self._encode_cursor(
                "task-restarts",
                filter_digest=filter_digest,
                requested_at=page[-1]["requested_at"],
                restart_uuid=page[-1]["restart_uuid"],
            )
            if more and page
            else None
        )
        return [self._restart_view(row) for row in page], next_cursor


    async def restart(self, team_uuid: str, restart_uuid: str) -> dict[str, Any]:
        async with self.persistence.transaction() as tx:
            row = await tx.fetchone(
                self._restart_select() + "WHERE r.team_uuid=? AND r.restart_uuid=?",
                (team_uuid, restart_uuid),
            )
        if row is None:
            raise NotFoundError("restart-not-found", "Restart was not found")
        return self._restart_view(row)


    async def lineage(
        self,
        team_uuid: str,
        *,
        restart_uuid: str | None = None,
        task_uuid: str | None = None,
        intake_item_uuid: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Build a bounded causal graph from restart ledger truth only."""

        seeds = [value for value in (restart_uuid, task_uuid, intake_item_uuid) if value is not None]
        if len(seeds) != 1:
            raise MkbError("lineage-seed-invalid", "Exactly one lineage seed is required", 422)
        limit = min(max(limit, 1), 100)
        if restart_uuid is not None:
            seed_kind, seed_value, predicate = "restart_uuid", restart_uuid, "r.restart_uuid=?"
        elif task_uuid is not None:
            seed_kind, seed_value, predicate = "task_uuid", task_uuid, "(r.source_task_uuid=? OR r.restart_task_uuid=?)"
        else:
            seed_kind, seed_value, predicate = "intake_item_uuid", intake_item_uuid, "r.intake_item_uuid=?"
        conditions = ["r.team_uuid=?", predicate]
        params: list[Any] = [team_uuid]
        params.extend([seed_value] if seed_kind != "task_uuid" else [seed_value, seed_value])
        if cursor:
            decoded = self._decode_cursor(cursor, kind="task-lineage")
            if decoded.get("seed_kind") != seed_kind or decoded.get("seed_value") != seed_value:
                raise MkbError("cursor-invalid", "Cursor does not match lineage seed", 422)
            requested_at, after_restart = decoded.get("requested_at"), decoded.get("restart_uuid")
            if not isinstance(requested_at, str) or not isinstance(after_restart, str):
                raise MkbError("cursor-invalid", "Cursor is invalid", 422)
            conditions.append("(r.requested_at < ? OR (r.requested_at = ? AND r.restart_uuid < ?))")
            params.extend([requested_at, requested_at, after_restart])
        params.append(limit + 1)
        async with self.persistence.transaction() as tx:
            if seed_kind == "task_uuid":
                if (
                    await tx.fetchone(
                        "SELECT 1 FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?", (team_uuid, seed_value)
                    )
                    is None
                ):
                    raise NotFoundError("task-not-found", "Task was not found")
            elif seed_kind == "intake_item_uuid":
                if (
                    await tx.fetchone(
                        "SELECT 1 FROM mkb_intake_items WHERE team_uuid=? AND intake_item_uuid=?",
                        (team_uuid, seed_value),
                    )
                    is None
                ):
                    raise NotFoundError("intake-item-not-found", "Intake item was not found")
            rows = await tx.fetchall(
                self._restart_select()
                + "WHERE "
                + " AND ".join(conditions)
                + " ORDER BY r.requested_at DESC, r.restart_uuid DESC LIMIT ?",
                tuple(params),
            )
            if seed_kind == "restart_uuid" and not rows:
                raise NotFoundError("restart-not-found", "Restart was not found")
            page = rows[:limit]
            task_ids = {seed_value} if seed_kind == "task_uuid" else set()
            task_ids.update(row["source_task_uuid"] for row in page)
            task_ids.update(row["restart_task_uuid"] for row in page if row["restart_task_uuid"])
            task_rows: dict[str, dict[str, Any]] = {}
            if task_ids:
                placeholders = ",".join("?" for _ in task_ids)
                selected = await tx.fetchall(
                    f"SELECT * FROM mkb_tasks WHERE team_uuid=? AND task_uuid IN ({placeholders})",
                    (team_uuid, *sorted(task_ids)),
                )
                task_rows = {row["task_uuid"]: row for row in selected}
            generation_rows: dict[tuple[str, int], dict[str, Any]] = {}
            generation_keys = {(row["source_task_uuid"], row["source_generation"]) for row in page}
            generation_keys.update(
                (row["restart_task_uuid"], row["target_generation"])
                for row in page
                if row["restart_task_uuid"] and row["target_generation"] is not None
            )
            for generation_task_uuid, generation_number in generation_keys:
                record = await tx.fetchone(
                    "SELECT * FROM mkb_executions WHERE team_uuid=? AND task_uuid=? AND generation=? "
                    "AND parent_execution_uuid IS NULL AND root_execution_uuid=execution_uuid",
                    (team_uuid, generation_task_uuid, generation_number),
                )
                if record is not None:
                    generation_rows[(generation_task_uuid, generation_number)] = record

        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, str]] = []
        for candidate_task_uuid, row in task_rows.items():
            nodes[f"task:{candidate_task_uuid}"] = {
                "id": f"task:{candidate_task_uuid}",
                "kind": "task",
                "summary": self._task_summary(row),
            }
        if seed_kind == "intake_item_uuid":
            nodes[f"intake-item:{seed_value}"] = {
                "id": f"intake-item:{seed_value}",
                "kind": "intake_item",
                "intake_item_uuid": seed_value,
            }
        for (generation_task_uuid, generation_number), row in generation_rows.items():
            node_id = f"generation:{generation_task_uuid}:{generation_number}"
            nodes[node_id] = {"id": node_id, "kind": "generation", "summary": self._generation_view(row)}
        for row in page:
            restart_id = f"restart:{row['restart_uuid']}"
            nodes[restart_id] = {"id": restart_id, "kind": "restart", "summary": self._restart_view(row)}
            source_task_id = f"task:{row['source_task_uuid']}"
            edges.append({"from": source_task_id, "to": restart_id, "kind": "caused_restart"})
            source_generation_id = f"generation:{row['source_task_uuid']}:{row['source_generation']}"
            if source_generation_id in nodes:
                edges.append({"from": source_generation_id, "to": restart_id, "kind": "source_generation"})
            if row["intake_item_uuid"]:
                item_id = f"intake-item:{row['intake_item_uuid']}"
                nodes.setdefault(
                    item_id,
                    {"id": item_id, "kind": "intake_item", "intake_item_uuid": row["intake_item_uuid"]},
                )
                edges.append({"from": item_id, "to": restart_id, "kind": "rebuild_target"})
            if row["restart_task_uuid"]:
                target_task_id = f"task:{row['restart_task_uuid']}"
                edges.append({"from": restart_id, "to": target_task_id, "kind": "starts_task"})
                if row["target_generation"] is not None:
                    target_generation_id = f"generation:{row['restart_task_uuid']}:{row['target_generation']}"
                    if target_generation_id in nodes:
                        edges.append({"from": restart_id, "to": target_generation_id, "kind": "target_generation"})
        more = len(rows) > limit
        next_cursor = (
            self._encode_cursor(
                "task-lineage",
                seed_kind=seed_kind,
                seed_value=seed_value,
                requested_at=page[-1]["requested_at"],
                restart_uuid=page[-1]["restart_uuid"],
            )
            if more and page
            else None
        )
        return {
            "seed": {seed_kind: seed_value},
            "nodes": list(nodes.values()),
            "edges": edges,
            "next_cursor": next_cursor,
        }
