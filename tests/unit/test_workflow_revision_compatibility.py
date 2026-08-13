"""Upgrade regressions for executions pinned to an immutable workflow plan."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand, ProcessOutcome
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.workflow_engine import WorkflowRuntime, WorkflowWorker, canonical_outcome_digest
from src.services.workflow_registry import WorkflowIdentity, WorkflowRegistryService
from src.workflows.builtin_lsrag import (
    BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW,
    HISTORICAL_SINGLE_INTAKE_LSRAG_WORKFLOW_V1,
)
from tests.unit.test_workflow_runtime import seed_typed_auto_admission


class _SuccessfulLegacyStage:
    async def run(self, command: ProcessCommand) -> ProcessOutcome:
        output_digest = stable_digest({"output": command.process_uuid, "fence": command.fencing_generation})
        proof_digest = stable_digest({"proof": command.process_key, "output": output_digest})
        provisional = ProcessOutcome(
            schema_version="mkb.process-outcome.v1",
            team_uuid=command.team_uuid,
            task_uuid=command.task_uuid,
            execution_uuid=command.execution_uuid,
            process_uuid=command.process_uuid,
            fencing_generation=command.fencing_generation,
            disposition="succeeded",
            outcome_digest="0" * 64,
            output_manifest_ref=f"mkbtest:output:{output_digest}",
            output_manifest_digest=output_digest,
            proof_ref=f"mkbtest:proof:{proof_digest}",
            proof_digest=proof_digest,
            payload_extra=(
                {"admission_result": "auto_admitted"} if command.process_key == "intake.accept_snapshot" else {}
            ),
        )
        return provisional.model_copy(update={"outcome_digest": canonical_outcome_digest(provisional)})


async def _seed_v1_execution(persistence: SqlitePersistence, identity: WorkflowIdentity) -> tuple[str, str, str]:
    now = utc_now()
    team_uuid, task_uuid, execution_uuid = uuid7(), uuid7(), uuid7()
    trace_uuid = uuid7()
    config_digest = stable_digest({"config": "legacy-v1"})
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_teams (team_uuid,name,creation_fingerprint,created_at,updated_at) VALUES (?,?,?,?,?)",
            (team_uuid, "legacy-v1", stable_digest({"team": team_uuid}), now, now),
        )
        await tx.execute(
            "INSERT INTO mkb_tasks "
            "(team_uuid,task_uuid,trace_uuid,schema_version,request_intent,creation_fingerprint,audit_bound,title,status,"
            "current_generation,current_root_execution_uuid,received_at,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,1,?,'queued',1,?,?,?,?)",
            (
                team_uuid,
                task_uuid,
                trace_uuid,
                "mkb.task.v1",
                "intake.ingest",
                stable_digest({"task": task_uuid}),
                "legacy v1 execution",
                execution_uuid,
                now,
                now,
                now,
            ),
        )
        await tx.execute(
            "INSERT INTO mkb_executions "
            "(execution_uuid,team_uuid,task_uuid,trace_uuid,generation,root_execution_uuid,execution_role,target_kind,"
            "workflow_uuid,workflow_revision_uuid,compiled_digest,resolver_decision_digest,domain_binding_digest,"
            "s05_binding_digest,config_snapshot_ref,config_snapshot_digest,status,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,'root','task',?,?,?,?,?,?,?,?, 'ready',?,?)",
            (
                execution_uuid,
                team_uuid,
                task_uuid,
                trace_uuid,
                1,
                execution_uuid,
                identity.workflow_uuid,
                identity.workflow_revision_uuid,
                identity.compiled_digest,
                stable_digest({"resolver": identity.workflow_revision_uuid}),
                stable_digest({"binding": "legacy-v1"}),
                stable_digest({"s05": "legacy-v1"}),
                f"mkbtest:config:{config_digest}",
                config_digest,
                now,
                now,
            ),
        )
        await seed_typed_auto_admission(tx, team_uuid=team_uuid, execution_uuid=execution_uuid)
    return team_uuid, task_uuid, execution_uuid


@pytest.mark.asyncio
async def test_v2_runtime_materializes_and_completes_unstarted_v1_execution(tmp_path: Path) -> None:
    """A deploy between Task commit and wake execution must not strand v1."""

    persistence = SqlitePersistence(tmp_path / "workflow-upgrade.sqlite3", Path("src/persistence/migrations"))
    await persistence.migrate()
    registry = WorkflowRegistryService(persistence)
    try:
        registered_v1 = await registry.register(HISTORICAL_SINGLE_INTAKE_LSRAG_WORKFLOW_V1)
        team_uuid, task_uuid, execution_uuid = await _seed_v1_execution(persistence, registered_v1)

        registered_v2 = await registry.register(BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW)
        assert (await registry.resolve("intake.ingest")).workflow_revision_uuid == registered_v2.workflow_revision_uuid

        runtime = WorkflowRuntime(
            persistence,
            BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW,
            compatibility_definitions=(HISTORICAL_SINGLE_INTAKE_LSRAG_WORKFLOW_V1,),
            retry_delay_seconds=0,
        )
        assert await runtime.materialize_root(execution_uuid)

        async with persistence.transaction() as tx:
            initial = await tx.fetchone(
                "SELECT process_key FROM mkb_processes WHERE execution_uuid=?", (execution_uuid,)
            )
        assert initial == {"process_key": "intake.acquire.inline"}

        worker = WorkflowWorker(runtime, _SuccessfulLegacyStage())
        for _ in range(12):
            if not await worker.run_once("upgrade-test-worker"):
                break

        async with persistence.transaction() as tx:
            execution = await tx.fetchone(
                "SELECT status,workflow_revision_uuid,compiled_digest FROM mkb_executions WHERE execution_uuid=?",
                (execution_uuid,),
            )
            task = await tx.fetchone(
                "SELECT status FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?", (team_uuid, task_uuid)
            )
            process_rows = await tx.fetchall(
                "SELECT process_key,status FROM mkb_processes WHERE execution_uuid=? ORDER BY created_at,process_uuid",
                (execution_uuid,),
            )

        assert execution == {
            "status": "succeeded",
            "workflow_revision_uuid": registered_v1.workflow_revision_uuid,
            "compiled_digest": registered_v1.compiled_digest,
        }
        assert task == {"status": "succeeded"}
        assert [row["process_key"] for row in process_rows] == [
            "intake.acquire.inline",
            "intake.decode.text_json_html",
            "clean.extract.deterministic",
            "intake.collection.seal",
            "intake.preflight_validate",
            "intake.accept_snapshot",
            "lsrag.structurize",
            "lsrag.construct",
            "lsrag.vectorize",
            "index.validate_publication",
        ]
        assert {row["status"] for row in process_rows} == {"succeeded"}
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_unknown_historical_compiled_plan_fails_before_process_materialization(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "workflow-upgrade-fence.sqlite3", Path("src/persistence/migrations"))
    await persistence.migrate()
    registry = WorkflowRegistryService(persistence)
    try:
        registered_v1 = await registry.register(HISTORICAL_SINGLE_INTAKE_LSRAG_WORKFLOW_V1)
        _, _, execution_uuid = await _seed_v1_execution(persistence, registered_v1)
        await registry.register(BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW)

        runtime = WorkflowRuntime(persistence, BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW)
        with pytest.raises(MkbError, match="workflow-compiled-plan-unavailable"):
            await runtime.materialize_root(execution_uuid)

        async with persistence.transaction() as tx:
            processes = await tx.fetchall(
                "SELECT process_uuid FROM mkb_processes WHERE execution_uuid=?", (execution_uuid,)
            )
        assert processes == []
    finally:
        await persistence.close()
