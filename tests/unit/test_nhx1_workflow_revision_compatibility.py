"""NHX1-T09: persisted kind-family rev1 remains exact while rev2 activates."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.contracts.common.ids import stable_digest
from src.contracts.workflow.models import canonical_workflow_manifest
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.workflow_engine import WorkflowRuntime
from src.services.workflow_registry import WorkflowRegistryService
from src.workflows.builtin_lsrag import BUILTIN_KIND_V1_COMPATIBILITY_WORKFLOWS, BUILTIN_KIND_WORKFLOWS
from tests.unit.test_workflow_revision_compatibility import _seed_v1_execution

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/new_harvest_nhx1/rev1-manifest.json"


def test_kind_family_rev1_fixture_is_not_recomputed_from_rev2() -> None:
    manifest = json.loads(FIXTURE.read_text(encoding="utf-8"))
    frozen = {row["workflow_key"]: row for row in manifest["workflows"]}
    assert all(definition.revision_number == 2 for definition in BUILTIN_KIND_WORKFLOWS)
    assert all(definition.revision_number == 1 for definition in BUILTIN_KIND_V1_COMPATIBILITY_WORKFLOWS)
    for definition in BUILTIN_KIND_V1_COMPATIBILITY_WORKFLOWS:
        row = frozen[definition.workflow_key]
        assert stable_digest(canonical_workflow_manifest(definition)) == row["registration_fingerprint"]
        assert stable_digest(
            {
                "compiler": "mkb.workflow-compiler.v1",
                "definition": canonical_workflow_manifest(definition),
                "capability_registry": sorted(definition.required_process_keys),
            }
        ) == row["compiled_digest"]


@pytest.mark.asyncio
async def test_registry_appends_kind_rev2_without_mutating_rev1(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "kind-revisions.db", ROOT / "src/persistence/migrations")
    await persistence.migrate()
    registry = WorkflowRegistryService(persistence)
    old = BUILTIN_KIND_V1_COMPATIBILITY_WORKFLOWS[0]
    current = BUILTIN_KIND_WORKFLOWS[0]
    try:
        registered_old = await registry.register(old)
        registered_current = await registry.register(current)
        assert registered_old.workflow_uuid == registered_current.workflow_uuid
        assert registered_old.workflow_revision_uuid != registered_current.workflow_revision_uuid
        async with persistence.read_snapshot() as tx:
            revisions = await tx.fetchall(
                "SELECT revision_number,registration_fingerprint,compiled_digest FROM mkb_workflow_revisions "
                "WHERE workflow_uuid=? ORDER BY revision_number",
                (registered_old.workflow_uuid,),
            )
        assert [row["revision_number"] for row in revisions] == [1, 2]
        assert revisions[0]["compiled_digest"] == registered_old.compiled_digest
        assert revisions[1]["compiled_digest"] == registered_current.compiled_digest
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_persisted_kind_rev1_materializes_with_exact_compatibility_plan(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "kind-old-runtime.db", ROOT / "src/persistence/migrations")
    await persistence.migrate()
    registry = WorkflowRegistryService(persistence)
    old = BUILTIN_KIND_V1_COMPATIBILITY_WORKFLOWS[0]
    current = BUILTIN_KIND_WORKFLOWS[0]
    try:
        old_identity = await registry.register(old)
        await registry.register(current)
        team_uuid, task_uuid, execution_uuid = await _seed_v1_execution(persistence, old_identity)
        runtime = WorkflowRuntime(
            persistence,
            current,
            compatibility_definitions=(old,),
            retry_delay_seconds=0,
        )
        assert await runtime.materialize_root(execution_uuid)
        async with persistence.read_snapshot() as tx:
            process = await tx.fetchone(
                "SELECT process_key FROM mkb_processes WHERE execution_uuid=?",
                (execution_uuid,),
            )
            execution = await tx.fetchone(
                "SELECT workflow_revision_uuid,compiled_digest FROM mkb_executions "
                "WHERE team_uuid=? AND task_uuid=?",
                (team_uuid, task_uuid),
            )
        assert process == {"process_key": "intake.acquire.inline"}
        assert execution == {
            "workflow_revision_uuid": old_identity.workflow_revision_uuid,
            "compiled_digest": old_identity.compiled_digest,
        }
    finally:
        await persistence.close()
