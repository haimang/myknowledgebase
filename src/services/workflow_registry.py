"""Durable registration and resolution of code-owned workflow definitions.

The Python declaration in :mod:`src.workflows` is reviewed source material.  A
Task never binds directly to that module at run time: this service first
registers the graph into the seven S03 relational tables, then returns the
immutable revision coordinates from that durable registry.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.workflow.models import (
    WorkflowBindingSourceKind,
    WorkflowDefinition,
    WorkflowStepKind,
)
from src.persistence.ports import PersistencePort, UnitOfWork
from src.workflows.builtin_lsrag import (
    BUILTIN_WORKFLOWS as BUILTIN_SINGLE_WORKFLOWS,
)
from src.workflows.builtin_lsrag import (
    SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS,
)
from src.workflows.builtin_scatter import (
    BUILTIN_SCATTER_WORKFLOWS,
    SCATTER_ROOT_WORKFLOW_KEY,
)

# Registry resolution is deliberately internal.  Public Task payloads carry a
# bounded request intent and strict source descriptor, never a graph key.  A
# registered-API collection has a distinct root controller; every other v1
# intake entry continues to use the existing single-root declaration.
BUILTIN_WORKFLOWS = BUILTIN_SINGLE_WORKFLOWS + BUILTIN_SCATTER_WORKFLOWS


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class WorkflowIdentity:
    """The only workflow coordinates that an Execution may freeze."""

    workflow_key: str
    workflow_uuid: str
    workflow_revision_uuid: str
    compiled_digest: str
    registration_fingerprint: str
    execution_role: str


class WorkflowRegistryService:
    """Internal-only S03 registry writer and deterministic resolver."""

    def __init__(self, persistence: PersistencePort) -> None:
        self.persistence = persistence

    async def bootstrap(self) -> None:
        for definition in BUILTIN_WORKFLOWS:
            await self.register(definition)

    async def readiness(self) -> bool:
        try:
            for definition in BUILTIN_WORKFLOWS:
                identity = await self.resolve_by_key(definition.workflow_key)
                if identity.workflow_key != definition.workflow_key:
                    return False
            return True
        except Exception:
            return False

    async def resolve_for_source(
        self,
        purpose_key: str,
        source_kind: str | None = None,
        source_profile: str | None = None,
    ) -> WorkflowIdentity:
        """Resolve a code-owned graph from immutable, typed ingress facts.

        This is intentionally not a public selector: the caller supplies only
        a purpose and SourceKindDefinition discriminator.  It cannot select a
        workflow key, revision, process, or branch.
        """

        if purpose_key == "intake.ingest" and source_kind == "registered_api":
            return await self.resolve_by_key(SCATTER_ROOT_WORKFLOW_KEY)
        if purpose_key == "intake.ingest":
            profile = source_profile or source_kind
            # Non-ingest Task intents deliberately reuse the canonical inline
            # skeleton after ConfigSnapshotService freezes their own target
            # context.  They have no source descriptor to profile-select.
            workflow_key = SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS.get(
                profile or "inline_payload"
            )
            if workflow_key is None:
                raise MkbError("REGISTRY_NOT_FOUND", "Source profile has no exact active workflow binding", 503)
            return await self.resolve_by_key(workflow_key)
        return await self.resolve(purpose_key)

    async def resolve(self, purpose_key: str) -> WorkflowIdentity:
        """Return exactly one enabled active workflow without floating aliases."""

        async with self.persistence.transaction() as tx:
            rows = await tx.fetchall(
                "SELECT r.workflow_key,r.workflow_uuid,r.active_revision_uuid,r.execution_role,v.compiled_digest,"
                "v.registration_fingerprint FROM mkb_workflow_registry r "
                "JOIN mkb_workflow_revisions v ON v.workflow_revision_uuid=r.active_revision_uuid "
                "WHERE r.purpose_key=? AND r.registry_status='enabled' "
                "ORDER BY r.selector_priority ASC,r.workflow_key ASC",
                (purpose_key,),
            )
        if len(rows) != 1:
            raise MkbError("REGISTRY_NOT_FOUND", "An exact active workflow binding is required", 503)
        return self._identity(rows[0])

    async def resolve_by_key(self, workflow_key: str) -> WorkflowIdentity:
        """Return one exact enabled code-owned workflow key.

        Multiple graphs may intentionally share a purpose (single intake,
        scatter root, and scatter child), therefore broad purpose resolution
        is never used for bootstrap/readiness or source dispatch.
        """

        async with self.persistence.transaction() as tx:
            rows = await tx.fetchall(
                "SELECT r.workflow_key,r.workflow_uuid,r.active_revision_uuid,r.execution_role,v.compiled_digest,"
                "v.registration_fingerprint FROM mkb_workflow_registry r "
                "JOIN mkb_workflow_revisions v ON v.workflow_revision_uuid=r.active_revision_uuid "
                "WHERE r.workflow_key=? AND r.registry_status='enabled'",
                (workflow_key,),
            )
        if len(rows) != 1:
            raise MkbError("REGISTRY_NOT_FOUND", "An exact active workflow binding is required", 503)
        return self._identity(rows[0])

    @staticmethod
    def _identity(row: dict[str, Any]) -> WorkflowIdentity:
        return WorkflowIdentity(
            workflow_key=row["workflow_key"],
            workflow_uuid=row["workflow_uuid"],
            workflow_revision_uuid=row["active_revision_uuid"],
            compiled_digest=row["compiled_digest"],
            registration_fingerprint=row["registration_fingerprint"],
            execution_role=row["execution_role"],
        )

    async def register(self, definition: WorkflowDefinition) -> WorkflowIdentity:
        """Atomically register a graph or verify the immutable prior revision."""

        canonical = definition.model_dump(mode="json")
        registration_fingerprint = stable_digest(canonical)
        compiled_digest = stable_digest(
            {
                "compiler": "mkb.workflow-compiler.v1",
                "definition": canonical,
                "capability_registry": sorted(definition.required_process_keys),
            }
        )
        capability_registry_digest = stable_digest(sorted(definition.required_process_keys))
        async with self.persistence.transaction() as tx:
            existing = await tx.fetchone(
                "SELECT workflow_uuid,domain_key,purpose_key,execution_role,active_revision_uuid "
                "FROM mkb_workflow_registry WHERE workflow_key=?",
                (definition.workflow_key,),
            )
            if existing is not None:
                self._assert_registry_shape(existing, definition)
                revision = await tx.fetchone(
                    "SELECT workflow_revision_uuid,registration_fingerprint,canonical_definition_digest,compiled_digest "
                    "FROM mkb_workflow_revisions WHERE workflow_uuid=? AND revision_number=?",
                    (existing["workflow_uuid"], definition.revision_number),
                )
                if revision is None:
                    # A code-owned workflow may advance by adding a new
                    # immutable revision while old Executions remain pinned
                    # to their stored revision UUID/digest.  Never mutate the
                    # prior rows in place merely to make a new capability
                    # available.
                    return await self._insert_definition(
                        tx,
                        definition,
                        registration_fingerprint=registration_fingerprint,
                        compiled_digest=compiled_digest,
                        capability_registry_digest=capability_registry_digest,
                        existing_workflow_uuid=existing["workflow_uuid"],
                    )
                if (
                    revision["registration_fingerprint"] != registration_fingerprint
                    or revision["canonical_definition_digest"] != registration_fingerprint
                    or revision["compiled_digest"] != compiled_digest
                ):
                    raise MkbError("REGISTRY_DIGEST_MISMATCH", "Workflow revision digest conflicts", 503)
                if existing["active_revision_uuid"] != revision["workflow_revision_uuid"]:
                    await tx.execute(
                        "UPDATE mkb_workflow_registry SET active_revision_uuid=?,updated_at=? WHERE workflow_uuid=?",
                        (revision["workflow_revision_uuid"], utc_now(), existing["workflow_uuid"]),
                    )
                return WorkflowIdentity(
                    workflow_key=definition.workflow_key,
                    workflow_uuid=existing["workflow_uuid"],
                    workflow_revision_uuid=revision["workflow_revision_uuid"],
                    compiled_digest=compiled_digest,
                    registration_fingerprint=registration_fingerprint,
                    execution_role=definition.execution_role.value,
                )

            return await self._insert_definition(
                tx,
                definition,
                registration_fingerprint=registration_fingerprint,
                compiled_digest=compiled_digest,
                capability_registry_digest=capability_registry_digest,
            )

    @staticmethod
    def _assert_registry_shape(existing: dict[str, Any], definition: WorkflowDefinition) -> None:
        expected = (definition.domain_key, definition.purpose_key, definition.execution_role.value)
        actual = (existing["domain_key"], existing["purpose_key"], existing["execution_role"])
        if actual != expected:
            raise MkbError("REGISTRY_DIGEST_MISMATCH", "Workflow identity coordinates conflict", 503)

    async def _insert_definition(
        self,
        tx: UnitOfWork,
        definition: WorkflowDefinition,
        *,
        registration_fingerprint: str,
        compiled_digest: str,
        capability_registry_digest: str,
        existing_workflow_uuid: str | None = None,
    ) -> WorkflowIdentity:
        now = utc_now()
        workflow_uuid = existing_workflow_uuid or uuid7()
        revision_uuid = uuid7()
        if existing_workflow_uuid is None:
            await tx.execute(
                "INSERT INTO mkb_workflow_registry "
                "(workflow_uuid,workflow_key,domain_key,purpose_key,execution_role,selector_key,selector_priority,"
                "read_exposure,registry_status,active_revision_uuid,display_name,description,created_at,updated_at,"
                "created_by_origin,payload_extra) VALUES (?,?,?,?,?,?,?,'internal','enabled',NULL,?,?,?,?,?,'{}')",
                (
                    workflow_uuid,
                    definition.workflow_key,
                    definition.domain_key,
                    definition.purpose_key,
                    definition.execution_role.value,
                    definition.purpose_key,
                    100,
                    definition.display_name,
                    definition.description,
                    now,
                    now,
                    "code_bootstrap",
                ),
            )
        await tx.execute(
            "INSERT INTO mkb_workflow_revisions "
            "(workflow_revision_uuid,workflow_uuid,revision_number,schema_version,capability_registry_digest,"
            "registration_source_kind,registration_module,source_commit_digest,migration_key,registration_fingerprint,"
            "canonical_definition_digest,compiled_digest,registered_at,activated_at,registration_trace_uuid,payload_extra) "
            "VALUES (?,?,?,?,?,'code','src.workflows.builtin_lsrag',NULL,NULL,?,?,?,?,?,NULL,'{}')",
            (
                revision_uuid,
                workflow_uuid,
                definition.revision_number,
                definition.schema_version,
                capability_registry_digest,
                registration_fingerprint,
                registration_fingerprint,
                compiled_digest,
                now,
                now,
            ),
        )

        step_ids: dict[str, str] = {}
        for order_hint, step in enumerate(definition.steps):
            step_uuid = uuid7()
            step_ids[step.step_key] = step_uuid
            await tx.execute(
                "INSERT INTO mkb_workflow_steps "
                "(workflow_step_uuid,workflow_revision_uuid,step_key,step_kind,process_key,process_contract_version,"
                "phase_key,requiredness,terminal_kind,order_hint,display_name,payload_extra) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,'{}')",
                (
                    step_uuid,
                    revision_uuid,
                    step.step_key,
                    step.step_kind.value,
                    step.process_key,
                    step.contract_version,
                    step.phase_key.value if step.phase_key else None,
                    step.requiredness.value,
                    step.terminal_kind.value if step.terminal_kind else None,
                    order_hint,
                    step.step_key,
                ),
            )

        route_ids: dict[str, str] = {}
        for route in definition.routes:
            route_uuid = uuid7()
            route_ids[route.route_key] = route_uuid
            await tx.execute(
                "INSERT INTO mkb_workflow_routes "
                "(workflow_route_uuid,workflow_revision_uuid,route_key,from_step_uuid,to_step_uuid,route_kind,"
                "outcome_selector,priority,guard_group_key,join_mode,predecessor_requiredness,payload_extra) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,NULL,'{}')",
                (
                    route_uuid,
                    revision_uuid,
                    route.route_key,
                    step_ids[route.from_step_key],
                    step_ids[route.to_step_key],
                    route.route_kind.value,
                    route.outcome_selector.value,
                    route.priority,
                    route.guard_key,
                    route.join_mode.value,
                ),
            )

        await self._insert_bindings(tx, definition, revision_uuid, step_ids)
        await tx.execute(
            "INSERT INTO mkb_workflow_controls "
            "(workflow_control_uuid,workflow_revision_uuid,scope_type,workflow_step_uuid,workflow_route_uuid,"
            "timeout_ms,lease_duration_ms,heartbeat_interval_ms,max_retries,retry_policy,backoff_kind,"
            "backoff_initial_ms,backoff_max_ms,backoff_multiplier,jitter_pct,max_recoveries,"
            "indeterminate_side_effect_policy,cancel_mode,cancel_grace_ms,case_mode,purge_mode,failure_policy,"
            "concurrency_limit,fan_out_limit,deadline_mode,payload_extra) "
            "VALUES (?,?, 'revision',NULL,NULL,30000,60000,10000,2,'transient_only','exponential',"
            "100,2000,2.0,0.0,2,'verify_then_retry','cooperative',10000,NULL,NULL,'fail_fast',16,NULL,"
            "'latest_claim_time','{}')",
            (uuid7(), revision_uuid),
        )
        for guard in definition.guards:
            operand_kind, operand_ref = {
                "registered_admission_result": ("admission_result", "candidate_set.admission_result"),
                "registered_request_intent": ("request_intent", "task.request_intent"),
                "registered_metadata_disposition": ("metadata_disposition", "intake_item_transition.no_change"),
                "registered_markdown_selection": ("markdown_selection", "task.prompt_selection.markdown"),
                "registered_admission_markdown_selection": (
                    "admission_markdown_selection",
                    "candidate_set.admission_result+task.prompt_selection.markdown",
                ),
            }.get(guard.predicate_type, (None, None))
            if operand_kind is None or operand_ref is None:
                raise MkbError("workflow-guard-unsupported", "Workflow guard declaration is unsupported", 503)
            await tx.execute(
                "INSERT INTO mkb_workflow_guards "
                "(workflow_guard_uuid,workflow_revision_uuid,scope_type,scope_key,guard_group_key,group_mode,"
                "order_index,predicate_type,operand_kind,operand_ref,operator,expected_type,expected_bool,"
                "expected_int,expected_real,expected_text,expected_uuid,expected_ref,failure_code,"
                "failure_disposition,payload_extra) "
                "VALUES (?,?, 'route',?,?, 'all',0,?,?,?,"
                "?, 'text',NULL,NULL,NULL,?,NULL,NULL,'workflow-route-false',?,'{}')",
                (
                    uuid7(),
                    revision_uuid,
                    guard.guard_key,
                    guard.guard_key,
                    guard.predicate_type,
                    operand_kind,
                    operand_ref,
                    guard.operator,
                    guard.expected_value,
                    guard.failure_disposition,
                ),
            )
        await tx.execute(
            "UPDATE mkb_workflow_registry SET active_revision_uuid=?,updated_at=? WHERE workflow_uuid=?",
            (revision_uuid, now, workflow_uuid),
        )
        return WorkflowIdentity(
            workflow_key=definition.workflow_key,
            workflow_uuid=workflow_uuid,
            workflow_revision_uuid=revision_uuid,
            compiled_digest=compiled_digest,
            registration_fingerprint=registration_fingerprint,
            execution_role=definition.execution_role.value,
        )

    async def _insert_bindings(
        self,
        tx: UnitOfWork,
        definition: WorkflowDefinition,
        revision_uuid: str,
        step_ids: dict[str, str],
    ) -> None:
        """Persist typed context/input/output slots without a second JSON SSOT."""

        start_step = next(step for step in definition.steps if step.step_kind is WorkflowStepKind.START)
        for port in definition.context_slots:
            await self._insert_binding_row(
                tx,
                revision_uuid=revision_uuid,
                step_uuid=step_ids[start_step.step_key],
                binding_kind="context",
                slot_name=port.slot_name,
                value_type="ref",
                schema_ref=port.schema_ref,
                required=port.required,
                multiplicity=port.multiplicity.value,
                source_kind=WorkflowBindingSourceKind.EXECUTION_CONTEXT.value,
                source_ref_key=port.slot_name,
            )
        bindings = {(binding.target_step_key, binding.target_slot_name): binding for binding in definition.bindings}
        for step in definition.steps:
            for port in step.input_ports:
                binding = bindings[(step.step_key, port.slot_name)]
                await self._insert_binding_row(
                    tx,
                    revision_uuid=revision_uuid,
                    step_uuid=step_ids[step.step_key],
                    binding_kind="input",
                    slot_name=port.slot_name,
                    value_type="ref",
                    schema_ref=port.schema_ref,
                    required=port.required,
                    multiplicity=port.multiplicity.value,
                    source_kind=binding.source_kind.value,
                    source_step_uuid=step_ids.get(binding.source_step_key or ""),
                    source_port=binding.source_port_name,
                    source_ref_key=binding.source_ref_key,
                )
            for port in step.output_ports:
                await self._insert_binding_row(
                    tx,
                    revision_uuid=revision_uuid,
                    step_uuid=step_ids[step.step_key],
                    binding_kind="output",
                    slot_name=port.slot_name,
                    value_type="ref",
                    schema_ref=port.schema_ref,
                    required=port.required,
                    multiplicity=port.multiplicity.value,
                    source_kind=WorkflowBindingSourceKind.REGISTRY_REF.value,
                    source_ref_key=f"output.{step.step_key}.{port.slot_name}",
                )

    @staticmethod
    async def _insert_binding_row(
        tx: UnitOfWork,
        *,
        revision_uuid: str,
        step_uuid: str,
        binding_kind: str,
        slot_name: str,
        value_type: str,
        schema_ref: str,
        required: bool,
        multiplicity: str,
        source_kind: str,
        source_step_uuid: str | None = None,
        source_port: str | None = None,
        source_ref_key: str | None = None,
    ) -> None:
        await tx.execute(
            "INSERT INTO mkb_workflow_bindings "
            "(workflow_binding_uuid,workflow_revision_uuid,workflow_step_uuid,binding_kind,slot_name,value_type,"
            "schema_ref,required,multiplicity,binding_source_kind,binding_source_step_uuid,binding_source_port,"
            "binding_source_ref_key,payload_extra) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'{}')",
            (
                uuid7(),
                revision_uuid,
                step_uuid,
                binding_kind,
                slot_name,
                value_type,
                schema_ref,
                int(required),
                multiplicity,
                source_kind,
                source_step_uuid,
                source_port,
                source_ref_key,
            ),
        )


__all__ = ["WorkflowIdentity", "WorkflowRegistryService"]
