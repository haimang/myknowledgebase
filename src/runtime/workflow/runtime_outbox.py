"""runtime outbox"""

from __future__ import annotations

import json
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.runtime.workflow.runtime_outcome import _safe_persisted_error
from src.contracts.common.time import utc_now
from src.persistence.ports import UnitOfWork
from src.runtime.workflow.helpers import (
    _add_seconds,
    _is_sha256_digest,
    _required_payload_uuid,
)
from src.runtime.workflow.types import (
    OutboxDelivery,
)


def _safe_outbox_error(error: str) -> str:
    return _safe_persisted_error(error)


class WorkflowOutboxMixin:
    """runtime outbox"""

    async def claim_outbox(self, lease_owner: str, *, lease_seconds: int = 30) -> OutboxDelivery | None:
        """Lease one durable wake-up intent; uniqueness is enforced by its dedupe key."""

        if not lease_owner:
            raise MkbError("invalid-lease-owner", "lease_owner must be non-empty", 422)
        leased = await self._lease_outbox_row(lease_owner, lease_seconds=lease_seconds)
        if leased is None:
            return None
        row, delivery_lease_owner = leased
        return await self._parse_or_kill_outbox(row, delivery_lease_owner)

    async def _lease_outbox_row(
        self, lease_owner: str, *, lease_seconds: int
    ) -> tuple[dict[str, Any], str] | None:
        now = utc_now()
        expires_at = _add_seconds(now, lease_seconds)
        delivery_lease_owner = f"{lease_owner}:{uuid7()}"
        if len(delivery_lease_owner) > 256:
            raise MkbError("invalid-lease-owner", "lease_owner is too long for a unique delivery lease", 422)
        async with self.persistence.transaction() as tx:
            row = await tx.fetchone(
                "SELECT * FROM mkb_outbox WHERE (status='pending' AND available_at<=?) "
                "OR (status='in_flight' AND lease_expires_at<=?) "
                "ORDER BY available_at ASC,created_at ASC,outbox_id ASC LIMIT 1",
                (now, now),
            )
            if row is None:
                return None
            updated = await tx.execute(
                "UPDATE mkb_outbox SET status='in_flight',lease_owner=?,lease_expires_at=?,attempts=attempts+1,updated_at=? "
                "WHERE outbox_id=? AND ((status='pending' AND available_at<=?) OR (status='in_flight' AND lease_expires_at<=?))",
                (delivery_lease_owner, expires_at, now, row["outbox_id"], now, now),
            )
            if updated.rowcount != 1:
                return None
            return dict(row), delivery_lease_owner

    async def _parse_or_kill_outbox(self, row: dict[str, Any], delivery_lease_owner: str) -> OutboxDelivery | None:
        try:
            payload = json.loads(row["payload_json"])
        except (json.JSONDecodeError, TypeError):
            await self._mark_outbox_dead(row["outbox_id"], delivery_lease_owner, "Outbox payload is not valid JSON")
            return None
        if not isinstance(payload, dict) or stable_digest(payload) != row["payload_digest"]:
            await self._mark_outbox_dead(row["outbox_id"], delivery_lease_owner, "Outbox payload digest is invalid")
            return None
        return OutboxDelivery(
            row["outbox_id"],
            row["team_uuid"],
            row["kind"],
            payload,
            delivery_lease_owner,
        )


    async def dispatch_outbox_once(self, lease_owner: str, *, lease_seconds: int = 30) -> bool:
        """Consume one scheduling intent after it is durably leased.

        Wakes do not execute business work.  They only ensure that materialized
        work is observable by a process worker; the worker subsequently claims
        the Process from the database.
        """

        if not lease_owner:
            raise MkbError("invalid-lease-owner", "lease_owner must be non-empty", 422)
        leased = await self._lease_outbox_row(lease_owner, lease_seconds=lease_seconds)
        if leased is None:
            return False
        row, delivery_lease_owner = leased
        delivery = await self._parse_or_kill_outbox(row, delivery_lease_owner)
        if delivery is None:
            return True
        try:
            if delivery.kind == "wake_execution":
                await self.materialize_root(_required_payload_uuid(delivery.payload, "execution_uuid"))
            elif delivery.kind == "wake_process":
                # A DB scan is the source of truth; no in-memory queue item is
                # required to make a Process runnable.
                _required_payload_uuid(delivery.payload, "execution_uuid")
                _required_payload_uuid(delivery.payload, "process_uuid")
            elif delivery.kind == "cancel_execution":
                await self.request_cancellation(_required_payload_uuid(delivery.payload, "execution_uuid"))
            elif delivery.kind == "gate_decision":
                await self.consume_gate_decision(_required_payload_uuid(delivery.payload, "decision_uuid"))
            elif delivery.kind == "vectorize_construct":
                # This delivery is a typed S07→S08 handoff fence, rather than
                # a claim or an execution-success signal.  The vector Process
                # remains the only place that can produce the vectorization
                # Outcome; consuming the intent only proves that the exact
                # full-valid construct package is still current and bound to
                # that Process.
                await self._consume_vectorize_construct_intent(delivery)
            else:
                raise MkbError("outbox-kind-unsupported", "Outbox kind is not owned by the workflow runtime", 500)
        except Exception as exc:
            await self._release_outbox(delivery.outbox_id, delivery.lease_owner, str(exc))
            raise
        await self._complete_outbox(delivery.outbox_id, delivery.lease_owner)
        return True


    async def _consume_vectorize_construct_intent(self, delivery: OutboxDelivery) -> None:
        """Validate an exact construct handoff without treating ACK as work.

        S07 writes this intent in the same transaction as the construction
        generation-pointer CAS.  It can be delivered more than once, so this
        consumer has no business side effect: it validates the immutable
        generation package and the materialized ``lsrag.vectorize`` Process.
        The Process handler independently rechecks the same package at its
        outcome fence and is solely responsible for vector upserts/success.
        """

        payload = delivery.payload
        required_keys = {
            "schema_version",
            "team_uuid",
            "task_uuid",
            "execution_uuid",
            "construction_artifact_uuid",
            "construction_ref",
            "construction_content_digest",
            "dual_channel_artifact_uuid",
            "dual_channel_ref",
            "dual_channel_content_digest",
            "construction_schema_digest",
            "content_full_recipe_version",
        }
        if set(payload) != required_keys or payload.get("schema_version") != "mkb.vectorize-construct-intent.v1":
            raise MkbError(
                "vectorize-construct-intent-invalid",
                "Vectorize construct intent has an invalid closed payload shape",
                409,
            )
        string_keys = required_keys - {"schema_version"}
        if any(not isinstance(payload.get(key), str) or not payload[key] for key in string_keys):
            raise MkbError(
                "vectorize-construct-intent-invalid",
                "Vectorize construct intent has an invalid scalar value",
                409,
            )
        digest_keys = {
            "construction_content_digest",
            "dual_channel_content_digest",
            "construction_schema_digest",
        }
        if any(not _is_sha256_digest(str(payload[key])) for key in digest_keys):
            raise MkbError(
                "vectorize-construct-intent-invalid",
                "Vectorize construct intent has an invalid immutable digest",
                409,
            )
        if payload["team_uuid"] != delivery.team_uuid:
            raise MkbError(
                "vectorize-construct-team-mismatch",
                "Vectorize construct intent does not belong to its outbox team",
                409,
            )

        async with self.persistence.transaction() as tx:
            execution = await self._execution(tx, payload["execution_uuid"])
            if execution["team_uuid"] != delivery.team_uuid or execution["task_uuid"] != payload["task_uuid"]:
                raise MkbError(
                    "vectorize-construct-execution-mismatch",
                    "Vectorize construct intent does not match its owning Execution",
                    409,
                )
            task = await tx.fetchone(
                "SELECT task_uuid FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
                (delivery.team_uuid, payload["task_uuid"]),
            )
            if task is None:
                raise MkbError(
                    "vectorize-construct-task-missing",
                    "Vectorize construct intent has no owning Task",
                    409,
                )

            construction = await self._vectorize_construct_artifact_tx(
                tx,
                team_uuid=delivery.team_uuid,
                task_uuid=payload["task_uuid"],
                execution_uuid=payload["execution_uuid"],
                artifact_uuid=payload["construction_artifact_uuid"],
                artifact_type="construction_document",
                logical_handle=payload["construction_ref"],
                content_digest=payload["construction_content_digest"],
                schema_digest=payload["construction_schema_digest"],
            )
            dual = await self._vectorize_construct_artifact_tx(
                tx,
                team_uuid=delivery.team_uuid,
                task_uuid=payload["task_uuid"],
                execution_uuid=payload["execution_uuid"],
                artifact_uuid=payload["dual_channel_artifact_uuid"],
                artifact_type="dual_channel_projection",
                logical_handle=payload["dual_channel_ref"],
                content_digest=payload["dual_channel_content_digest"],
                schema_digest=payload["construction_schema_digest"],
            )
            if construction["generation_artifact_uuid"] == dual["generation_artifact_uuid"]:
                raise MkbError(
                    "vectorize-construct-artifact-alias",
                    "Construction and dual-channel generation members must be distinct",
                    409,
                )
            if (
                not construction.get("validation_report_ref")
                or not construction.get("validation_report_digest")
                or construction["validation_report_ref"] != dual.get("validation_report_ref")
                or construction["validation_report_digest"] != dual.get("validation_report_digest")
            ):
                raise MkbError(
                    "vectorize-construct-validation-missing",
                    "Construction package has no shared validation-report binding",
                    409,
                )
            validation = await tx.fetchone(
                "SELECT a.generation_artifact_uuid FROM mkb_generation_pointers AS p "
                "JOIN mkb_generation_artifacts AS a ON a.team_uuid=p.team_uuid "
                "AND a.generation_artifact_uuid=p.current_generation_artifact_uuid "
                "WHERE p.team_uuid=? AND p.execution_uuid=? AND p.artifact_type='construction_validation_report' "
                "AND a.artifact_type='construction_validation_report' AND a.task_uuid=? "
                "AND a.execution_uuid=? AND a.validation_disposition='full_valid' "
                "AND a.logical_handle=? AND a.content_digest=?",
                (
                    delivery.team_uuid,
                    payload["execution_uuid"],
                    payload["task_uuid"],
                    payload["execution_uuid"],
                    construction["validation_report_ref"],
                    construction["validation_report_digest"],
                ),
            )
            if validation is None:
                raise MkbError(
                    "vectorize-construct-validation-missing",
                    "Construction validation report is not the current full-valid member",
                    409,
                )
            schema = await tx.fetchone(
                "SELECT schema_key,schema_version FROM mkb_construction_schema_definitions "
                "WHERE schema_digest=? AND content_full_recipe_version=?",
                (payload["construction_schema_digest"], payload["content_full_recipe_version"]),
            )
            if (
                schema is None
                or construction.get("schema_key") != schema["schema_key"]
                or construction.get("schema_version") != schema["schema_version"]
                or dual.get("schema_key") != schema["schema_key"]
                or dual.get("schema_version") != schema["schema_version"]
            ):
                raise MkbError(
                    "vectorize-construct-schema-mismatch",
                    "Construction package does not match a registered content_full schema",
                    409,
                )
            processes = await tx.fetchall(
                "SELECT process_uuid FROM mkb_processes WHERE team_uuid=? AND task_uuid=? AND execution_uuid=? "
                "AND process_key='lsrag.vectorize' ORDER BY process_uuid",
                (delivery.team_uuid, payload["task_uuid"], payload["execution_uuid"]),
            )
            if len(processes) != 1:
                raise MkbError(
                    "vectorize-construct-process-missing",
                    "Construction handoff is not bound to exactly one lsrag.vectorize Process",
                    409,
                )


    async def _vectorize_construct_artifact_tx(
        self,
        tx: UnitOfWork,
        *,
        team_uuid: str,
        task_uuid: str,
        execution_uuid: str,
        artifact_uuid: str,
        artifact_type: str,
        logical_handle: str,
        content_digest: str,
        schema_digest: str,
    ) -> dict[str, Any]:
        """Return one exact current, full-valid construction member or fail closed."""

        row = await tx.fetchone(
            "SELECT a.* FROM mkb_generation_pointers AS p JOIN mkb_generation_artifacts AS a "
            "ON a.team_uuid=p.team_uuid AND a.generation_artifact_uuid=p.current_generation_artifact_uuid "
            "WHERE p.team_uuid=? AND p.execution_uuid=? AND p.artifact_type=? "
            "AND a.generation_artifact_uuid=? AND a.artifact_type=? AND a.task_uuid=? "
            "AND a.execution_uuid=? AND a.validation_disposition='full_valid' "
            "AND a.logical_handle=? AND a.content_digest=? AND a.schema_digest=?",
            (
                team_uuid,
                execution_uuid,
                artifact_type,
                artifact_uuid,
                artifact_type,
                task_uuid,
                execution_uuid,
                logical_handle,
                content_digest,
                schema_digest,
            ),
        )
        if row is None:
            raise MkbError(
                "vectorize-construct-generation-mismatch",
                "Construction handoff no longer matches its current full-valid generation member",
                409,
            )
        return row


    async def _mark_outbox_dead(self, outbox_id: str, lease_owner: str, error: str) -> None:
        now = utc_now()
        async with self.persistence.transaction() as tx:
            row = await tx.fetchone(
                "SELECT team_uuid,kind FROM mkb_outbox WHERE outbox_id=?", (outbox_id,)
            )
            await tx.execute(
                "UPDATE mkb_outbox SET status='dead',lease_owner=NULL,lease_expires_at=NULL,last_error=?,updated_at=? "
                "WHERE outbox_id=? AND status='in_flight' AND lease_owner=?",
                (_safe_outbox_error(error), now, outbox_id, lease_owner),
            )
            if row is not None:
                await self._record_outbox_dead_tx(tx, row, error=_safe_outbox_error(error))

    async def _record_outbox_dead_tx(self, tx: UnitOfWork, row: dict[str, Any], *, error: str) -> None:
        from src.services.events import DomainEventWriter

        await DomainEventWriter().write(
            tx,
            team_uuid=str(row["team_uuid"]),
            trace_uuid=uuid7(),
            event_type="outbox.dead",
            aggregate="outbox",
            summary="Outbox delivery marked dead",
            payload={"kind": row.get("kind"), "error": error[:128]},
            severity="error",
            status_after="dead",
        )
        metrics = getattr(self, "metrics", None)
        if metrics is not None:
            kind = str(row.get("kind") or "wake_process")
            try:
                metrics.increment("mkb_outbox_dead_total", 1, kind=kind)
            except Exception:
                pass

    async def _complete_outbox(self, outbox_id: str, lease_owner: str) -> None:
        now = utc_now()
        async with self.persistence.transaction() as tx:
            await tx.execute(
                "UPDATE mkb_outbox SET status='done',lease_owner=NULL,lease_expires_at=NULL,updated_at=? "
                "WHERE outbox_id=? AND status='in_flight' AND lease_owner=?",
                (now, outbox_id, lease_owner),
            )


    async def _release_outbox(self, outbox_id: str, lease_owner: str, error: str) -> None:
        now = utc_now()
        async with self.persistence.transaction() as tx:
            row = await tx.fetchone("SELECT attempts FROM mkb_outbox WHERE outbox_id=?", (outbox_id,))
            if row is None:
                return
            status = "dead" if row["attempts"] >= 8 else "pending"
            safe_error = _safe_outbox_error(error)
            meta = await tx.fetchone(
                "SELECT team_uuid,kind FROM mkb_outbox WHERE outbox_id=?", (outbox_id,)
            )
            await tx.execute(
                "UPDATE mkb_outbox SET status=?,lease_owner=NULL,lease_expires_at=NULL,last_error=?,available_at=?,updated_at=? "
                "WHERE outbox_id=? AND status='in_flight' AND lease_owner=?",
                (status, safe_error, _add_seconds(now, 1), now, outbox_id, lease_owner),
            )
            if status == "dead" and meta is not None:
                await self._record_outbox_dead_tx(tx, meta, error=safe_error)
