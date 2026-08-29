"""runtime materialize"""

from __future__ import annotations

import json
from typing import Any

from src.contracts.common.errors import ConflictError, MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.models import ExecutionStatus, ProcessStatus
from src.contracts.common.time import utc_now
from src.contracts.workflow.models import (
    WorkflowDefinition,
    WorkflowOutcomeSelector,
    WorkflowRouteDefinition,
    WorkflowStepDefinition,
    WorkflowStepKind,
)
from src.persistence.ports import UnitOfWork
from src.runtime.binding.actual_s05 import projected_actual_digest, requires_actual_binding
from src.runtime.workflow.constants import (
    _TASK_PRIORITY_RANK,
    _TERMINAL_EXECUTION_STATUSES,
)
from src.runtime.workflow.dispatch import GENERATE_PROCESS_KEYS, OVER_BUDGET_PROCESS_KEYS
from src.runtime.workflow.helpers import (
    _json,
)
from src.services.prompt_profiles import default_prompt_ids


def _markdown_id_from_domain_flavor(payload: dict[str, Any]) -> str | None:
    """Resolve optional markdown hop from domain/flavor defaults."""

    try:
        defaults = default_prompt_ids(
            domain=payload.get("domain") if isinstance(payload.get("domain"), str) else None,
            flavor=payload.get("flavor") if isinstance(payload.get("flavor"), str) else None,
            granularity=payload.get("granularity") if isinstance(payload.get("granularity"), str) else None,
        )
    except ValueError:
        return None
    markdown_id = defaults.get("markdown")
    return markdown_id if isinstance(markdown_id, str) and markdown_id else None


class WorkflowMaterializeMixin:
    """runtime materialize"""

    def _route_decision(
        self,
        *,
        plan: WorkflowDefinition,
        execution: dict[str, Any],
        source_step_key: str,
        selector: WorkflowOutcomeSelector,
        route_context: dict[str, Any],
    ) -> dict[str, Any]:
        candidates = [
            route
            for route in plan.routes
            if route.from_step_key == source_step_key and route.outcome_selector is selector
        ]
        candidates.sort(key=lambda route: route.priority)
        if (
            selector is WorkflowOutcomeSelector.SUCCEEDED
            and plan.workflow_key.startswith("intake.ingest.kind.")
            and route_context.get("media_family") == "text"
            and route_context.get("main_text_presence") == "absent"
        ):
            guards = {guard.guard_key: guard for guard in plan.guards}
            has_declared_reacquire = any(
                route.guard_key is not None
                and (guard := guards.get(route.guard_key)) is not None
                and guard.predicate_type == "representation_main_text_presence"
                and guard.expected_value == "absent"
                for route in candidates
            )
            if not has_declared_reacquire:
                raise ConflictError(
                    "workflow-reacquire-edge-undeclared",
                    "An absent text representation has no declared forward reacquisition edge",
                )
        selected: list[WorkflowRouteDefinition] = []
        guard_results: dict[str, bool] = {}
        for route in candidates:
            matched = self._guard_matches(plan, route, route_context, guard_results)
            if not matched:
                continue
            selected.append(route)
            # A normal/branch/terminal route has a single deterministic winner.
            if route.route_kind.value != "fan_out":
                break
        payload = {
            "workflow_key": plan.workflow_key,
            "workflow_revision_uuid": execution["workflow_revision_uuid"],
            "execution_uuid": execution["execution_uuid"],
            "source_step_key": source_step_key,
            "outcome_selector": selector.value,
            "guard_results": guard_results,
            "routes": [route.route_key for route in selected],
        }
        return {"routes": selected, "digest": stable_digest(payload), "payload": payload}


    def _guard_matches(
        self,
        plan: WorkflowDefinition,
        route: WorkflowRouteDefinition,
        context: dict[str, Any],
        results: dict[str, bool],
    ) -> bool:
        if route.guard_key is None:
            return True
        guards = {guard.guard_key: guard for guard in plan.guards}
        guard = guards.get(route.guard_key)
        if guard is None:
            raise MkbError("workflow-guard-missing", "Workflow route references an unavailable guard", 409)
        if guard.operator != "eq":
            raise MkbError("workflow-guard-unsupported", "Workflow guard is not supported by the bounded runtime", 409)
        context_key = {
            "registered_admission_result": "admission_result",
            "registered_request_intent": "request_intent",
            "registered_metadata_disposition": "metadata_disposition",
            "registered_markdown_selection": "markdown_selection",
            "registered_admission_markdown_selection": "admission_markdown_selection",
            "representation_main_text_presence": "main_text_presence",
            "registered_acquisition_mode": "acquisition_mode",
            "representation_media_family": "media_family",
            "registered_clean_strategy": "selected_clean_strategy",
        }.get(guard.predicate_type)
        if context_key is None:
            raise MkbError("workflow-guard-unsupported", "Workflow guard is not supported by the bounded runtime", 409)
        # Missing typed fact fails closed (D02 R2): extra-only context never matches.
        if context_key not in context:
            results[route.guard_key] = False
            return False
        result = context.get(context_key)
        matched = result == guard.expected_value
        results[route.guard_key] = matched
        return matched

    async def _typed_route_context_tx(self, tx: UnitOfWork, execution: dict[str, Any]) -> dict[str, Any]:
        """Build route guard context from durable Task/CandidateSet/transition facts."""

        context: dict[str, Any] = {}
        task = await tx.fetchone(
            "SELECT request_intent FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
            (execution["team_uuid"], execution["task_uuid"]),
        )
        if task is not None and isinstance(task.get("request_intent"), str):
            context["request_intent"] = task["request_intent"]
        candidate = await tx.fetchone(
            "SELECT admission_result FROM mkb_intake_candidate_sets "
            "WHERE team_uuid=? AND producer_execution_uuid=?",
            (execution["team_uuid"], execution["execution_uuid"]),
        )
        if candidate is not None and isinstance(candidate.get("admission_result"), str):
            context["admission_result"] = candidate["admission_result"]
        no_change = await tx.fetchone(
            "SELECT 1 AS present FROM mkb_intake_item_transitions "
            "WHERE team_uuid=? AND causation_execution_uuid=? AND action_key='no_change' LIMIT 1",
            (execution["team_uuid"], execution["execution_uuid"]),
        )
        if no_change is not None:
            context["metadata_disposition"] = "no_change"
        audit = await tx.fetchone(
            "SELECT strict_payload_json FROM mkb_task_audits WHERE team_uuid=? AND task_uuid=? "
            "ORDER BY received_at DESC LIMIT 1",
            (execution["team_uuid"], execution["task_uuid"]),
        )
        if audit is not None and isinstance(audit.get("strict_payload_json"), str):
            try:
                envelope = json.loads(audit["strict_payload_json"])
                payload = envelope.get("payload") if isinstance(envelope, dict) else None
                source = payload.get("source") if isinstance(payload, dict) else None
                if isinstance(source, dict):
                    acquisition_mode = source.get("acquisition_mode")
                    if acquisition_mode in {"static", "browser", "pdf"}:
                        context["acquisition_mode"] = acquisition_mode
                    media_type = source.get("media_type")
                    if isinstance(media_type, str):
                        normalized_media = media_type.split(";", 1)[0].strip().casefold()
                        if normalized_media == "application/pdf":
                            context["media_family"] = "pdf"
                        elif normalized_media.startswith("image/"):
                            context["media_family"] = "image"
                        elif normalized_media.startswith("text/") or normalized_media == "application/json":
                            context["media_family"] = "text"
                        else:
                            context["media_family"] = "opaque"
                selection = payload.get("prompt_selection") if isinstance(payload, dict) else None
                markdown = selection.get("markdown") if isinstance(selection, dict) else None
                markdown_id = markdown.get("prompt_id") if isinstance(markdown, dict) else None
                if not markdown_id and isinstance(payload, dict):
                    markdown_id = payload.get("markdown_prompt_id")
                if not markdown_id and isinstance(payload, dict):
                    markdown_id = _markdown_id_from_domain_flavor(payload)
                if isinstance(markdown_id, str) and markdown_id:
                    context["markdown_selection"] = "present"
                    if context.get("admission_result") == "auto_admitted":
                        context["admission_markdown_selection"] = "auto_admitted"
            except (TypeError, ValueError, json.JSONDecodeError):
                # A missing/invalid optional fact leaves the unguarded
                # no-markdown route as the only static fallback; it never
                # manufactures a markdown Process.
                pass
        if self.representation_facts is not None:
            facts = await self.representation_facts.read_route_facts(
                tx=tx,
                team_uuid=str(execution["team_uuid"]),
                execution_uuid=str(execution["execution_uuid"]),
            )
            if facts is not None:
                context["main_text_presence"] = facts.main_text_presence
                if facts.media_family is not None:
                    context["media_family"] = facts.media_family
                if facts.selected_clean_strategy is not None:
                    context["selected_clean_strategy"] = facts.selected_clean_strategy
        return context


    async def _apply_routes_tx(
        self,
        tx: UnitOfWork,
        *,
        plan: WorkflowDefinition,
        execution: dict[str, Any],
        decision: dict[str, Any],
        source_process: dict[str, Any] | None,
        route_context: dict[str, Any],
        terminal_error: str | None,
    ) -> bool:
        routes: list[WorkflowRouteDefinition] = decision["routes"]
        if not routes:
            await self._fail_execution_integrity_tx(
                tx,
                execution,
                "workflow-route-unmatched",
                "No deterministic route matched the terminal Process outcome",
            )
            return False
        changed = False
        for route in routes:
            steps = {step.step_key: step for step in plan.steps}
            target = steps.get(route.to_step_key)
            if target is None:
                await self._fail_execution_integrity_tx(
                    tx,
                    execution,
                    "workflow-target-missing",
                    "A route targeted a step absent from the immutable execution plan",
                )
                continue
            if target.step_kind is WorkflowStepKind.TERMINAL:
                await self._terminalize_execution_tx(
                    tx,
                    execution,
                    target.terminal_kind,
                    source_process=source_process,
                    route_digest=decision["digest"],
                    error_code=terminal_error,
                )
                changed = True
            elif target.step_kind is WorkflowStepKind.PROCESS:
                inserted = await self._materialize_process_tx(
                    tx,
                    plan=plan,
                    execution=execution,
                    step=target,
                    route_digest=decision["digest"],
                )
                changed = changed or inserted
            elif target.step_kind is WorkflowStepKind.CONTROL:
                inserted = await self._enter_control_tx(
                    tx,
                    plan=plan,
                    execution=execution,
                    step=target,
                    route_digest=decision["digest"],
                    source_process=source_process,
                    route_context=route_context,
                )
                changed = changed or inserted
            else:
                await self._fail_execution_integrity_tx(
                    tx,
                    execution,
                    "workflow-target-invalid",
                    "A route targeted a non-actionable workflow step",
                )
        await self._record_event_tx(
            tx,
            execution=execution,
            event_type="execution.status_changed",
            aggregate="execution",
            summary="Workflow route decision persisted",
            process_uuid=None if source_process is None else source_process["process_uuid"],
            payload=decision["payload"],
        )
        return changed


    async def _materialize_process_tx(
        self,
        tx: UnitOfWork,
        *,
        plan: WorkflowDefinition,
        execution: dict[str, Any],
        step: WorkflowStepDefinition,
        route_digest: str,
    ) -> bool:
        step_row = await tx.fetchone(
            "SELECT workflow_step_uuid FROM mkb_workflow_steps WHERE workflow_revision_uuid=? AND step_key=?",
            (execution["workflow_revision_uuid"], step.step_key),
        )
        if step_row is None:
            raise MkbError("workflow-step-missing", "Bound workflow step is absent from the registry", 503)
        # Runtime controls are copied from the Task's immutable create-time
        # scheduling contract into every durable Process.  Claim ordering and
        # latest-claim-time enforcement operate on Process rows, so merely
        # retaining these values on the public Task projection would be a
        # cosmetic deadline/priority implementation.
        task = await tx.fetchone(
            "SELECT priority,deadline_at,request_intent FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
            (execution["team_uuid"], execution["task_uuid"]),
        )
        if task is None:
            raise MkbError("workflow-task-missing", "Execution has no owning Task scheduling contract", 409)
        if (
            requires_actual_binding(str(step.process_key))
            and task["request_intent"] not in {"intake.rebuild", "intake.update_metadata", "index.rebuild"}
        ):
            state = str(execution.get("actual_binding_state") or "legacy_unverifiable")
            if state == "unsealed":
                raise ConflictError(
                    "ACTUAL_S05_UNSEALED",
                    "A clean-or-later Process cannot materialize before actual S05 is sealed",
                )
            if state == "sealed" and projected_actual_digest(execution) is None:
                raise MkbError("ACTUAL_S05_INTEGRITY", "Sealed actual S05 state lacks a valid digest", 503)
        priority_rank = _TASK_PRIORITY_RANK.get(task["priority"])
        if priority_rank is None:
            raise MkbError("workflow-task-priority-invalid", "Task priority is outside the closed scheduling set", 409)
        input_manifest, input_ref, input_object_digest = await self._input_manifest_tx(tx, plan, execution, step)
        input_binding_digest = stable_digest(input_manifest)
        materialization_key = stable_digest(
            {
                "execution_uuid": execution["execution_uuid"],
                "step_key": step.step_key,
                "route_decision_digest": route_digest,
            }
        )
        process_spec_digest = stable_digest(
            {
                "workflow_revision_uuid": execution["workflow_revision_uuid"],
                "workflow_step_uuid": step_row["workflow_step_uuid"],
                "step_key": step.step_key,
                "process_key": step.process_key,
                "contract_version": step.contract_version,
                # This is the immutable *binding* shape, distinct from the
                # bytes digest carried by ``ProcessCommand`` below.  Keeping
                # both prevents a runner from confusing a graph wiring hash
                # with the object it is authorized to read.
                "input_binding_digest": input_binding_digest,
                "config_snapshot_digest": execution["config_snapshot_digest"],
                "actual_binding_state": execution.get("actual_binding_state"),
                "actual_binding_digest": projected_actual_digest(execution),
                "route_decision_digest": route_digest,
                "priority": task["priority"],
                "deadline_at": task["deadline_at"],
            }
        )
        now = utc_now()
        process_uuid = uuid7()
        control = {
            "safe_replay": step.process_key not in GENERATE_PROCESS_KEYS
            and step.process_key not in OVER_BUDGET_PROCESS_KEYS
            and step.process_key != "lsrag.vectorize",
            "retry_delay_seconds": self.retry_delay_seconds,
            "materialized_from_route": route_digest,
        }
        existing = await tx.fetchone(
            "SELECT * FROM mkb_processes WHERE execution_uuid=? AND workflow_step_uuid=? AND materialization_key=?",
            (execution["execution_uuid"], step_row["workflow_step_uuid"], materialization_key),
        )
        if existing is not None:
            return False
        root_execution_uuid = execution.get("root_execution_uuid") or execution["execution_uuid"]
        if not root_execution_uuid:
            raise MkbError("execution-root-missing", "Execution lacks a durable root lineage pointer", 503)
        inserted = await tx.execute(
            "INSERT INTO mkb_processes "
            "(process_uuid,team_uuid,execution_uuid,task_uuid,root_execution_uuid,workflow_step_uuid,step_key,process_key,"
            "process_contract_version,materialization_key,route_decision_digest,requiredness,process_spec_digest,"
            "input_manifest_ref,input_manifest_digest,control_snapshot_ref,config_snapshot_ref,config_snapshot_digest,"
            "proof_kind,status,row_revision,available_at,priority_rank,deadline_at,fencing_generation,max_retries,max_recoveries,"
            "backoff_policy_json,created_at,updated_at,payload_extra) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                process_uuid,
                execution["team_uuid"],
                execution["execution_uuid"],
                execution["task_uuid"],
                root_execution_uuid,
                step_row["workflow_step_uuid"],
                step.step_key,
                step.process_key,
                step.contract_version,
                materialization_key,
                route_digest,
                step.requiredness.value,
                process_spec_digest,
                input_ref,
                input_object_digest,
                f"mkbworkflow-control:v1:{stable_digest(control)}",
                execution["config_snapshot_ref"],
                execution["config_snapshot_digest"],
                step.required_proof_kind,
                ProcessStatus.READY.value,
                0,
                now,
                priority_rank,
                task["deadline_at"],
                0,
                self.default_max_retries,
                self.default_max_recoveries,
                _json(control),
                now,
                now,
                "{}",
            ),
        )
        existing = await tx.fetchone(
            "SELECT * FROM mkb_processes WHERE execution_uuid=? AND workflow_step_uuid=? AND materialization_key=?",
            (execution["execution_uuid"], step_row["workflow_step_uuid"], materialization_key),
        )
        if existing is None:
            raise MkbError("process-materialization-missing", "Process insert did not create a durable Process", 500)
        await tx.execute(
            "UPDATE mkb_executions SET status='ready',phase_key=?,waiting_reason=NULL,waiting_ref=NULL,next_wake_at=NULL,"
            "current_process_uuid=?,row_revision=row_revision+1,updated_at=? "
            "WHERE execution_uuid=? AND status NOT IN ('succeeded','failed','cancelled','cancelling')",
            (
                step.phase_key.value if step.phase_key else None,
                existing["process_uuid"],
                now,
                execution["execution_uuid"],
            ),
        )
        await self._enqueue_tx(
            tx,
            execution["team_uuid"],
            "wake_process",
            {"execution_uuid": execution["execution_uuid"], "process_uuid": existing["process_uuid"]},
            f"materialize-process:{existing['process_uuid']}",
        )
        if inserted.rowcount:
            await self._record_event_tx(
                tx,
                execution=execution,
                event_type="process.materialized",
                aggregate="process",
                summary="Eligible workflow Process materialized with durable wake intent",
                process_uuid=existing["process_uuid"],
                status_before=None,
                status_after=ProcessStatus.READY.value,
                payload={"step_key": step.step_key, "route_decision_digest": route_digest},
            )
        return bool(inserted.rowcount)


    async def _input_manifest_tx(
        self, tx: UnitOfWork, plan: WorkflowDefinition, execution: dict[str, Any], step: WorkflowStepDefinition
    ) -> tuple[dict[str, Any], str, str]:
        """Return the declared wiring plus a real immutable input object.

        The graph manifest itself is a deterministic specification digest.  It
        is intentionally not fabricated as a storage handle.  A Process reads
        either the root Execution's catalogued input manifest or a successful
        predecessor's catalogued output.  Legacy/in-memory unit fixtures that
        predate root manifests retain a clearly non-serving test fallback;
        production Tasks always materialize ``manifest_ref`` before scheduling.
        """

        bindings: list[dict[str, Any]] = []
        primary_ref: str | None = None
        primary_digest: str | None = None
        primary_completed_at = ""
        input_ports = {port.slot_name: port for port in step.input_ports}
        for binding in plan.bindings:
            if binding.target_step_key != step.step_key:
                continue
            source: dict[str, Any] = {"kind": binding.source_kind.value}
            if binding.source_kind.value == "prior_output":
                source_step = next(
                    (candidate for candidate in plan.steps if candidate.step_key == binding.source_step_key),
                    None,
                )
                if source_step is not None and source_step.control_key == "selected_output":
                    selection = await tx.fetchone(
                        "SELECT candidate_port,output_manifest_ref,output_manifest_digest,projected_at "
                        "FROM mkb_workflow_selected_outputs WHERE execution_uuid=? AND control_step_key=?",
                        (execution["execution_uuid"], binding.source_step_key),
                    )
                    source_row = (
                        None
                        if selection is None
                        else {
                            "output_manifest_ref": selection["output_manifest_ref"],
                            "output_manifest_digest": selection["output_manifest_digest"],
                            "status": ProcessStatus.SUCCEEDED.value,
                            "completed_at": selection["projected_at"],
                            "candidate_port": selection["candidate_port"],
                        }
                    )
                else:
                    source_row = await tx.fetchone(
                        "SELECT output_manifest_ref,output_manifest_digest,status,completed_at FROM mkb_processes "
                        "WHERE execution_uuid=? AND step_key=? ORDER BY completed_at DESC LIMIT 1",
                        (execution["execution_uuid"], binding.source_step_key),
                    )
                if source_row is None or source_row["status"] != ProcessStatus.SUCCEEDED.value:
                    target = input_ports.get(binding.target_slot_name)
                    if target is not None and not target.required:
                        # A declarative branch may supply one of several optional,
                        # typed upstream handoffs.  Do not treat an unvisited
                        # alternate branch as a missing required predecessor.
                        continue
                    raise MkbError(
                        "workflow-binding-unavailable", "Required prior output is not a terminal success", 409
                    )
                source.update(
                    {
                        "step_key": binding.source_step_key,
                        "port": binding.source_port_name,
                        "ref": source_row["output_manifest_ref"],
                        "digest": source_row["output_manifest_digest"],
                    }
                )
                if source_row.get("candidate_port"):
                    source["selected_candidate_port"] = source_row["candidate_port"]
                # A stage output is a cumulative immutable envelope.  For a
                # multi-input node select the *most recently completed*
                # declared predecessor, rather than the incidental source
                # order in the workflow file.  It therefore carries the
                # complete predecessor state without inventing a mutable side
                # channel (for example, sealed candidate state beats an older
                # clean candidate at preflight).
                completed_at = str(source_row.get("completed_at") or "")
                if completed_at >= primary_completed_at:
                    primary_ref = source_row["output_manifest_ref"]
                    primary_digest = source_row["output_manifest_digest"]
                    primary_completed_at = completed_at
            else:
                source["ref_key"] = binding.source_ref_key
                source["execution_uuid"] = execution["execution_uuid"]
            bindings.append({"target_slot": binding.target_slot_name, "source": source})
        manifest = {
            "schema_version": "mkb.workflow-input-manifest.v1",
            "execution_uuid": execution["execution_uuid"],
            "workflow_revision_uuid": execution["workflow_revision_uuid"],
            "step_key": step.step_key,
            "bindings": bindings,
        }
        if primary_ref is not None and primary_digest is not None:
            return manifest, primary_ref, primary_digest
        if execution.get("manifest_ref") and execution.get("manifest_digest"):
            return manifest, str(execution["manifest_ref"]), str(execution["manifest_digest"])
        fallback_digest = stable_digest(manifest)
        return manifest, f"mkbworkflow-test-input:v1:{fallback_digest}", fallback_digest


    async def _enter_control_tx(
        self,
        tx: UnitOfWork,
        *,
        plan: WorkflowDefinition,
        execution: dict[str, Any],
        step: WorkflowStepDefinition,
        route_digest: str,
        source_process: dict[str, Any] | None,
        route_context: dict[str, Any],
    ) -> bool:
        """Open a human gate only for a fully durable, exact review target.

        A route decision is not evidence.  In particular, it is never safe to
        synthesize an Artifact digest or a logical preflight reference from the
        route digest: a human would then be approving a moving/current target.
        The accept stage is already terminal at this point, so the exact Intake
        rows and the preceding preflight output must be present in this same
        transaction or the Execution fails closed.
        """

        if step.control_key == "scatter_children_join":
            return await self._enter_scatter_children_join_tx(
                tx,
                plan=plan,
                execution=execution,
                route_digest=route_digest,
                source_process=source_process,
            )
        if step.control_key == "selected_output":
            return await self._enter_selected_output_tx(
                tx,
                plan=plan,
                execution=execution,
                step=step,
                route_digest=route_digest,
            )
        if step.control_key != "human_review_gate":
            raise MkbError("workflow-control-unsupported", "Only the bounded human-review control is supported", 409)
        existing = await tx.fetchone(
            "SELECT * FROM mkb_execution_gates WHERE execution_uuid=? AND gate_kind=? AND status='open'",
            (execution["execution_uuid"], step.control_key),
        )
        if existing is not None:
            return False
        current_execution = await self._execution(tx, execution["execution_uuid"])
        if current_execution["status"] in _TERMINAL_EXECUTION_STATUSES | {ExecutionStatus.CANCELLING.value}:
            return False
        try:
            if route_context.get("admission_result") != "human_review_required":
                raise MkbError(
                    "gate-target-evidence-invalid",
                    "Human-review routing lacks the required admission result",
                    409,
                )
            if current_execution.get("execution_role") == "scatter_root":
                evidence = await self._scatter_human_review_evidence_tx(tx, current_execution, source_process)
            else:
                evidence = await self._human_review_evidence_tx(tx, current_execution, source_process)
        except MkbError as exc:
            # Missing or ambiguous evidence is an integrity failure, not a
            # reason to create an empty/placeholder target or leave a Process
            # lease waiting for a decision that cannot be reviewed safely.
            if exc.code != "gate-target-evidence-invalid":
                raise
            await self._fail_execution_integrity_tx(tx, current_execution, exc.code, exc.message)
            return False

        now = utc_now()
        gate_uuid = uuid7()
        expected_execution_revision = current_execution["row_revision"] + 1
        actual_binding_digest = projected_actual_digest(current_execution)
        if actual_binding_digest is None:
            await self._fail_execution_integrity_tx(
                tx,
                current_execution,
                "ACTUAL_S05_UNSEALED",
                "A human Gate cannot freeze an unsealed actual S05 target",
            )
            return False
        review_target = {
            "schema_version": "mkb.execution-gate-target.v1",
            "team_uuid": current_execution["team_uuid"],
            "task_uuid": current_execution["task_uuid"],
            "execution_uuid": current_execution["execution_uuid"],
            "generation": current_execution["generation"],
            "waiting_ref": gate_uuid,
            "expected_execution_revision": expected_execution_revision,
            "workflow_binding": {
                "workflow_revision_uuid": current_execution["workflow_revision_uuid"],
                "compiled_digest": current_execution["compiled_digest"],
                "config_snapshot_digest": current_execution["config_snapshot_digest"],
                "actual_binding_state": "sealed",
                "actual_binding_digest": actual_binding_digest,
            },
            "route_decision_digest": route_digest,
            "accept_process": evidence["accept_process"],
            "preflight_outcome": evidence["preflight_outcome"],
            "intake_refs": evidence["intake_refs"],
            "clean_artifact": evidence["clean_artifact"],
            # This seed has explicit approval/failure routes but no declared
            # reclean route.  S05 requires reclean to take a workflow route or
            # causal restart; advertising it here would create an unsafe
            # implicit rewrite of an accepted artifact.
            "allowed_actions": ["approve", "reject"],
        }
        target_digest = stable_digest(review_target)
        await tx.execute(
            "INSERT INTO mkb_execution_gates "
            "(gate_uuid,team_uuid,task_uuid,execution_uuid,generation,gate_kind,status,gate_revision,opened_at,"
            "workflow_revision_uuid,binding_digest,actual_binding_digest,actual_binding_state,payload_extra) "
            "VALUES (?,?,?,?,?,?,'open',0,?,?,?,?,?,'{}')",
            (
                gate_uuid,
                current_execution["team_uuid"],
                current_execution["task_uuid"],
                current_execution["execution_uuid"],
                current_execution["generation"],
                step.control_key,
                now,
                current_execution["workflow_revision_uuid"],
                stable_digest(
                    {
                        "route": route_digest,
                        "execution": current_execution["execution_uuid"],
                        "actual_binding_digest": actual_binding_digest,
                    }
                ),
                actual_binding_digest,
                "sealed",
            ),
        )
        await tx.execute(
            "INSERT INTO mkb_execution_gate_targets "
            "(gate_uuid,team_uuid,target_digest,review_target_json,clean_artifact_digest,preflight_outcome_ref,"
            "intake_refs_json,created_at,payload_extra) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                gate_uuid,
                current_execution["team_uuid"],
                target_digest,
                _json(review_target),
                evidence["clean_artifact"]["content_digest"],
                evidence["preflight_outcome"]["output_manifest_ref"],
                _json(evidence["intake_refs"]),
                now,
                "{}",
            ),
        )
        for stored_object in evidence["evidence_objects"]:
            await self._hold_gate_evidence_tx(
                tx,
                team_uuid=current_execution["team_uuid"],
                gate_uuid=gate_uuid,
                stored_object=stored_object,
            )
        updated = await tx.execute(
            "UPDATE mkb_executions SET status='waiting',phase_key=?,waiting_reason='human_review',waiting_ref=?,"
            "next_wake_at=NULL,row_revision=row_revision+1,updated_at=? "
            "WHERE execution_uuid=? AND row_revision=? AND status NOT IN ('succeeded','failed','cancelled','cancelling')",
            (
                step.phase_key.value if step.phase_key else None,
                gate_uuid,
                now,
                current_execution["execution_uuid"],
                current_execution["row_revision"],
            ),
        )
        if updated.rowcount != 1:
            raise ConflictError("execution-transition-conflict", "Execution could not enter the human-review wait")
        await self._record_event_tx(
            tx,
            execution=execution,
            event_type="gate.opened",
            aggregate="gate",
            summary="Execution entered durable human-review wait",
            payload={"gate_uuid": gate_uuid, "route_decision_digest": route_digest},
        )
        await self._record_event_tx(
            tx,
            execution=execution,
            event_type="execution.waiting_entered",
            aggregate="execution",
            summary="Execution waiting for a human-review Gate",
            payload={"waiting_reason": "human_review", "waiting_ref": gate_uuid},
        )
        return True


    async def _enter_selected_output_tx(
        self,
        tx: UnitOfWork,
        *,
        plan: WorkflowDefinition,
        execution: dict[str, Any],
        step: WorkflowStepDefinition,
        route_digest: str,
    ) -> bool:
        """Persist and route one canonical output without waiting or re-running guards."""

        current = await self._execution(tx, execution["execution_uuid"])
        if current["status"] in _TERMINAL_EXECUTION_STATUSES | {ExecutionStatus.CANCELLING.value}:
            return False
        bindings = [binding for binding in plan.bindings if binding.target_step_key == step.step_key]
        candidates: list[dict[str, Any]] = []
        for binding in bindings:
            if binding.source_kind.value != "prior_output":
                continue
            rows = await tx.fetchall(
                "SELECT process_uuid,step_key,accepted_outcome_digest,output_manifest_ref,output_manifest_digest "
                "FROM mkb_processes WHERE execution_uuid=? AND step_key=? AND status='succeeded' "
                "ORDER BY completed_at,process_uuid",
                (current["execution_uuid"], binding.source_step_key),
            )
            for row in rows:
                if not row.get("output_manifest_ref") or not row.get("output_manifest_digest"):
                    await self._fail_execution_integrity_tx(
                        tx,
                        current,
                        "workflow-selected-output-proof-invalid",
                        "Selected-output candidate lacks a durable output manifest",
                    )
                    return False
                candidates.append(
                    {
                        "candidate_port": binding.target_slot_name,
                        "source_process": row,
                        "output_manifest_ref": row["output_manifest_ref"],
                        "output_manifest_digest": row["output_manifest_digest"],
                        "fallback_used": False,
                    }
                )
        if not candidates and step.control_fallback_port is not None:
            fallback = next(
                (binding for binding in bindings if binding.target_slot_name == step.control_fallback_port),
                None,
            )
            if fallback is not None and fallback.source_kind.value == "execution_context":
                if current.get("manifest_ref") and current.get("manifest_digest"):
                    candidates.append(
                        {
                            "candidate_port": fallback.target_slot_name,
                            "source_process": None,
                            "output_manifest_ref": current["manifest_ref"],
                            "output_manifest_digest": current["manifest_digest"],
                            "fallback_used": True,
                        }
                    )
        if not candidates:
            await self._fail_execution_integrity_tx(
                tx,
                current,
                "workflow-selected-output-missing",
                "Selected-output CONTROL has no committed candidate",
            )
            return False
        if len(candidates) != 1:
            await self._fail_execution_integrity_tx(
                tx,
                current,
                "workflow-selected-output-conflict",
                "Selected-output CONTROL observed more than one committed candidate",
            )
            return False

        selected = candidates[0]
        version = step.control_version or ""
        source_process = selected["source_process"]
        material = {
            "execution_uuid": current["execution_uuid"],
            "control_step_key": step.step_key,
            "control_version": version,
            "candidate_port": selected["candidate_port"],
            "selected_source_process_uuid": None if source_process is None else source_process["process_uuid"],
            "accepted_outcome_digest": None if source_process is None else source_process["accepted_outcome_digest"],
            "output_manifest_ref": selected["output_manifest_ref"],
            "output_manifest_digest": selected["output_manifest_digest"],
            "route_decision_digest": route_digest,
            "fallback_used": selected["fallback_used"],
        }
        selection_digest = stable_digest(material)
        now = utc_now()
        inserted = await tx.execute(
            "INSERT OR IGNORE INTO mkb_workflow_selected_outputs "
            "(selection_uuid,team_uuid,execution_uuid,control_step_key,control_version,candidate_port,"
            "selected_source_process_uuid,output_manifest_ref,output_manifest_digest,route_decision_digest,"
            "selection_digest,fallback_used,projected_at,payload_extra) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'{}')",
            (
                uuid7(),
                current["team_uuid"],
                current["execution_uuid"],
                step.step_key,
                version,
                selected["candidate_port"],
                material["selected_source_process_uuid"],
                selected["output_manifest_ref"],
                selected["output_manifest_digest"],
                route_digest,
                selection_digest,
                int(selected["fallback_used"]),
                now,
            ),
        )
        durable = await tx.fetchone(
            "SELECT selection_digest FROM mkb_workflow_selected_outputs "
            "WHERE execution_uuid=? AND control_step_key=?",
            (current["execution_uuid"], step.step_key),
        )
        if durable is None or durable["selection_digest"] != selection_digest:
            await self._fail_execution_integrity_tx(
                tx,
                current,
                "workflow-selected-output-conflict",
                "Selected-output CONTROL conflicts with its prior durable projection",
            )
            return False
        if inserted.rowcount:
            await self._record_event_tx(
                tx,
                execution=current,
                event_type="execution.selection_projected",
                aggregate="execution",
                summary="Selected-output CONTROL projected one durable candidate",
                process_uuid=material["selected_source_process_uuid"],
                payload={
                    "control_step_key": step.step_key,
                    "control_version": version,
                    "candidate_port": selected["candidate_port"],
                    "selection_digest": selection_digest,
                    "fallback_used": selected["fallback_used"],
                },
            )
        decision = self._route_decision(
            plan=plan,
            execution=current,
            source_step_key=step.step_key,
            selector=WorkflowOutcomeSelector.SUCCEEDED,
            route_context={},
        )
        return await self._apply_routes_tx(
            tx,
            plan=plan,
            execution=current,
            decision=decision,
            source_process=source_process,
            route_context={},
            terminal_error=None,
        )


    def _control_step(self, plan: WorkflowDefinition, control_key: str | None = None) -> WorkflowStepDefinition:
        controls = [step for step in plan.steps if step.step_kind is WorkflowStepKind.CONTROL]
        if control_key is not None:
            matches = [step for step in controls if step.control_key == control_key]
            if len(matches) != 1:
                raise MkbError("gate-control-mismatch", "Gate does not belong to the bound workflow control step", 409)
            return matches[0]
        if len(controls) != 1:
            raise MkbError(
                "workflow-control-ambiguous",
                "A control key is required when the bound workflow has multiple controls",
                409,
            )
        return controls[0]


    @staticmethod
    def _safe_replay(policy_json: str | None) -> bool:
        if policy_json is None:
            return False
        try:
            policy = json.loads(policy_json)
        except (TypeError, json.JSONDecodeError):
            return False
        return isinstance(policy, dict) and policy.get("safe_replay") is True
