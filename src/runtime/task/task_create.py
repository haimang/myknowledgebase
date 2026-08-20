"""Task create admission, root execution insert, and enqueue."""

from __future__ import annotations

from typing import Any

from src.contracts.api.models import (
    TaskCreateRequest,
)
from src.contracts.common.errors import ConflictError, MkbError, NotFoundError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.persistence.ports import PersistencePort, UnitOfWork
from src.runtime.task.helpers import _json
from src.services.config_snapshots import ConfigSnapshotService, PreparedExecutionInputs
from src.services.events import DomainEventWriter
from src.services.teams import TeamService


def _creation_fingerprint(request: TaskCreateRequest) -> str:
    payload = request.model_dump(mode="json")
    audit = payload.get("audit")
    if isinstance(audit, dict):
        audit.pop("created_at", None)
        audit.pop("reviewed_at", None)
    return stable_digest(payload)


def _is_unique_conflict(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "unique" in text or "constraint" in text or type(exc).__name__ == "IntegrityError"


class TaskCreateMixin:
    """Task create admission, root execution insert, and enqueue."""

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

    def __init__(
        self,
        persistence: PersistencePort,
        teams: TeamService,
        events: DomainEventWriter,
        config_snapshots: ConfigSnapshotService | None = None,
    ) -> None:
        self.persistence = persistence
        self.teams = teams
        self.events = events
        # Unit tests may compose the Task aggregate without checked-in config
        # assets.  The application composition root always provides this
        # dependency, making public Execution admission object-backed and
        # registry-bound rather than a floating alias.
        self.config_snapshots = config_snapshots


    async def create(self, request: TaskCreateRequest, caller_token_fingerprint: str) -> tuple[dict[str, Any], bool]:
        fingerprint = _creation_fingerprint(request)
        root_execution_uuid = uuid7()
        # First resolve the idempotency identity.  Object promotion happens
        # only for a genuinely new Task, so an exact client replay cannot make
        # fresh orphan objects or re-resolve mutable registry state.
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
        now = utc_now()
        self._assert_future_deadline(request.deadline_at, received_at=now)
        prepared = await self.config_snapshots.prepare(request) if self.config_snapshots is not None else None
        async with self.persistence.transaction() as tx:
            # Recheck immediately before the business UoW.  A concurrent
            # creator wins atomically; our pre-promoted bytes then remain safe
            # S13 orphans rather than partially-visible configuration rows.
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
            try:
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
            except Exception as exc:
                if not _is_unique_conflict(exc):
                    raise
                raced = await tx.fetchone(
                    "SELECT * FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
                    (request.team_uuid, request.task_uuid),
                )
                if raced is None:
                    raise ConflictError("task-identity-conflict", "Task identity collided") from exc
                if raced["creation_fingerprint"] != fingerprint:
                    raise ConflictError("task-identity-conflict", "Task identity has a different creation fingerprint") from exc
                return self._view(raced, await self._open_gate(tx, request.team_uuid, request.task_uuid)), True
            await tx.execute(
                "INSERT INTO mkb_task_audits "
                "(team_uuid,task_uuid,request_envelope_digest,strict_payload_json,caller_token_fingerprint,received_at,payload_extra) "
                "VALUES (?,?,?,?,?,?,'{}')",
                (
                    request.team_uuid,
                    request.task_uuid,
                    fingerprint,
                    _json(
                        prepared.audit_envelope
                        if prepared is not None
                        else ConfigSnapshotService.redacted_request_envelope(request, None)
                    ),
                    caller_token_fingerprint,
                    now,
                ),
            )
            if prepared is not None:
                await self.config_snapshots.audit_explicit_channel(tx, request)
                await self.config_snapshots.catalog_for_execution(
                    tx,
                    team_uuid=request.team_uuid,
                    execution_uuid=root_execution_uuid,
                    prepared=prepared,
                )
            await self._insert_root_execution(
                tx,
                team_uuid=request.team_uuid,
                task_uuid=request.task_uuid,
                trace_uuid=request.trace_uuid,
                execution_uuid=root_execution_uuid,
                generation=1,
                config_snapshot_ref=(prepared.config_snapshot_ref if prepared is not None else None),
                config_snapshot_digest=(prepared.config_snapshot_digest if prepared is not None else None),
                workflow_uuid=(prepared.workflow.workflow_uuid if prepared is not None else None),
                workflow_revision_uuid=(prepared.workflow.workflow_revision_uuid if prepared is not None else None),
                compiled_digest=(prepared.workflow.compiled_digest if prepared is not None else None),
                domain_binding_digest=(prepared.domain_binding_digest if prepared is not None else None),
                s05_binding_digest=(prepared.domain_binding_digest if prepared is not None else None),
                manifest_ref=(prepared.input_manifest_ref if prepared is not None else None),
                manifest_digest=(prepared.input_manifest_digest if prepared is not None else None),
                execution_role=(
                    self._root_execution_role(prepared.workflow.execution_role) if prepared is not None else "root"
                ),
                retry_of_execution_uuid=None,
            )
            if request.request_intent == "intake.rebuild" and prepared is not None:
                await self._insert_atomic_rebuild_restart(
                    tx,
                    request=request,
                    prepared=prepared,
                    root_execution_uuid=root_execution_uuid,
                    command_fingerprint=fingerprint,
                    now=now,
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
            if prepared is not None and prepared.override_applied is not None:
                # S14-T017: allowlisted override success writes exactly one
                # config.override_applied domain event in the Task UoW.
                await self.events.write(
                    tx,
                    team_uuid=request.team_uuid,
                    trace_uuid=request.trace_uuid,
                    event_type="config.override_applied",
                    aggregate="ops",
                    summary="Allowlisted Task override applied",
                    actor_kind="upstream",
                    task_uuid=request.task_uuid,
                    execution_uuid=root_execution_uuid,
                    payload=prepared.override_applied,
                )
            created = await self._get_row(tx, request.team_uuid, request.task_uuid)
        return self._view(created), False


    async def _insert_atomic_rebuild_restart(
        self,
        tx: UnitOfWork,
        *,
        request: TaskCreateRequest,
        prepared: PreparedExecutionInputs,
        root_execution_uuid: str,
        command_fingerprint: str,
        now: str,
    ) -> None:
        """Link an admitted rebuild Task to its exact prior Item revision.

        A public rebuild is not a retry of the old Task: it has its own Audit
        and root Execution.  The restart ledger is nevertheless the durable
        causal edge, recorded in the same UoW as the new Task/root/wake.
        """

        context = prepared.intent_context
        target = context.get("target") if isinstance(context, dict) else None
        if not isinstance(target, dict):
            raise MkbError("rebuild-target-missing", "Frozen rebuild target is unavailable", 503)
        item_uuid = target.get("intake_item_uuid")
        revision_uuid = target.get("intake_revision_uuid")
        snapshot_uuid = target.get("source_snapshot_uuid")
        if not all(isinstance(value, str) and value for value in (item_uuid, revision_uuid, snapshot_uuid)):
            raise MkbError("rebuild-target-invalid", "Frozen rebuild target is invalid", 503)
        snapshot = await tx.fetchone(
            "SELECT producer_execution_uuid FROM mkb_intake_snapshots "
            "WHERE team_uuid=? AND intake_snapshot_uuid=?",
            (request.team_uuid, snapshot_uuid),
        )
        if snapshot is None or not snapshot["producer_execution_uuid"]:
            raise MkbError("rebuild-causation-missing", "Selected Intake revision has no producing execution", 503)
        source = await tx.fetchone(
            "SELECT task_uuid,generation,root_execution_uuid FROM mkb_executions "
            "WHERE team_uuid=? AND execution_uuid=?",
            (request.team_uuid, snapshot["producer_execution_uuid"]),
        )
        if source is None:
            raise MkbError("rebuild-causation-missing", "Selected Intake revision has no producing Task", 503)
        await tx.execute(
            "INSERT INTO mkb_task_restarts "
            "(restart_uuid,team_uuid,restart_scope,source_task_uuid,source_generation,source_root_execution_uuid,"
            "intake_item_uuid,intake_revision_uuid,restart_task_uuid,target_generation,target_root_execution_uuid,"
            "causation_trace_uuid,command_fingerprint,admission_outcome,decision_code,reason,requested_at,decided_at,payload_extra) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                uuid7(),
                request.team_uuid,
                "atomic_intake_item",
                source["task_uuid"],
                source["generation"],
                source["root_execution_uuid"],
                item_uuid,
                revision_uuid,
                request.task_uuid,
                1,
                root_execution_uuid,
                request.trace_uuid,
                command_fingerprint,
                "accepted",
                "atomic-rebuild-accepted",
                request.description,
                now,
                now,
                "{}",
            ),
        )


    async def _insert_root_execution(
        self,
        tx: UnitOfWork,
        *,
        team_uuid: str,
        task_uuid: str,
        trace_uuid: str,
        execution_uuid: str,
        generation: int,
        config_snapshot_ref: str | None,
        config_snapshot_digest: str | None,
        workflow_uuid: str | None,
        workflow_revision_uuid: str | None,
        compiled_digest: str | None,
        domain_binding_digest: str | None,
        s05_binding_digest: str | None,
        manifest_ref: str | None,
        manifest_digest: str | None,
        execution_role: str,
        retry_of_execution_uuid: str | None,
    ) -> None:
        if execution_role not in {"root", "scatter_root"}:
            raise MkbError("workflow-root-role-invalid", "Workflow cannot materialize a Task root execution", 503)
        now = utc_now()
        # The optional fallback preserves isolated aggregate/projection tests.
        # Production Task admission always receives all these coordinates from
        # ConfigSnapshotService after durable WorkflowRegistry resolution.
        resolved_compiled_digest = compiled_digest or stable_digest({"workflow": "lsrag.default", "revision": 1})
        resolved_config_digest = config_snapshot_digest or stable_digest(
            {"request": "legacy-test", "generation": generation}
        )
        resolved_workflow_uuid = workflow_uuid or uuid7()
        resolved_workflow_revision_uuid = workflow_revision_uuid or uuid7()
        binding_digest = domain_binding_digest or stable_digest(
            {"config_snapshot": resolved_config_digest, "workflow": resolved_compiled_digest}
        )
        resolved_s05_digest = s05_binding_digest or binding_digest
        resolved_config_ref = config_snapshot_ref or f"mkbworkflow-test-config:v1:{resolved_config_digest}"
        resolved_manifest_digest = manifest_digest or stable_digest(
            {"execution_uuid": execution_uuid, "generation": generation, "kind": "legacy-test-input"}
        )
        resolved_manifest_ref = manifest_ref or f"mkbworkflow-test-input:v1:{resolved_manifest_digest}"
        await tx.execute(
            "INSERT INTO mkb_executions "
            "(execution_uuid,team_uuid,task_uuid,trace_uuid,generation,root_execution_uuid,parent_execution_uuid,"
            "retry_of_execution_uuid,execution_role,target_kind,workflow_uuid,workflow_revision_uuid,compiled_digest,"
            "resolver_decision_digest,domain_binding_digest,s05_binding_digest,config_snapshot_ref,config_snapshot_digest,"
            "status,row_revision,manifest_ref,manifest_digest,created_at,updated_at,payload_extra) "
            "VALUES (?,?,?,?,?,?,NULL,?,?,?,?,?,?,?,?,?,?,?,'ready',0,?,?,?,?,'{}')",
            (
                execution_uuid,
                team_uuid,
                task_uuid,
                trace_uuid,
                generation,
                execution_uuid,
                retry_of_execution_uuid,
                execution_role,
                "task",
                resolved_workflow_uuid,
                resolved_workflow_revision_uuid,
                resolved_compiled_digest,
                stable_digest({"workflow": resolved_compiled_digest}),
                binding_digest,
                resolved_s05_digest,
                resolved_config_ref,
                resolved_config_digest,
                resolved_manifest_ref,
                resolved_manifest_digest,
                now,
                now,
            ),
        )


    async def _link_execution_object_refs(
        self,
        tx: UnitOfWork,
        *,
        team_uuid: str,
        execution_uuid: str,
        config_digest: str,
        manifest_digest: str | None,
    ) -> None:
        """Attach retry ownership to the already immutable S13 objects.

        Full retries reuse exact L4/input bytes.  They never re-resolve a
        registry alias, but they do receive their own live-reference evidence
        so object GC cannot consider the new Execution unowned.
        """

        entries = [("execution_config_snapshot", config_digest)]
        if manifest_digest:
            entries.append(("execution_input_manifest", manifest_digest))
        for owner_kind, digest in entries:
            object_row = await tx.fetchone(
                "SELECT stored_object_uuid,size_bytes FROM mkb_stored_objects "
                "WHERE team_uuid=? AND content_digest=? AND tombstoned_at IS NULL "
                "ORDER BY created_at ASC LIMIT 1",
                (team_uuid, digest),
            )
            if object_row is None:
                raise MkbError("OBJECT_CATALOGUE_MISSING", "Retry input object is unavailable", 503)
            existing = await tx.fetchone(
                "SELECT reference_uuid FROM mkb_object_references WHERE team_uuid=? AND owner_kind=? AND owner_uuid=? "
                "AND expected_digest=? AND released_at IS NULL",
                (team_uuid, owner_kind, execution_uuid, digest),
            )
            if existing is not None:
                continue
            await tx.execute(
                "INSERT INTO mkb_object_references "
                "(reference_uuid,team_uuid,stored_object_uuid,purpose,owner_kind,owner_uuid,expected_digest,expected_size,"
                "created_at,payload_extra) VALUES (?,?,?,'process_io',?,?,?,?,?,'{}')",
                (
                    uuid7(),
                    team_uuid,
                    object_row["stored_object_uuid"],
                    owner_kind,
                    execution_uuid,
                    digest,
                    object_row["size_bytes"],
                    utc_now(),
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
