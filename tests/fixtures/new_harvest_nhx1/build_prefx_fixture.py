"""Build the immutable migration-024 fixture from the checked-in rev1 manifest.

This script deliberately never imports ``src.workflows.kind_family``.  The
manifest is the frozen ba099ee artifact; current workflow builders cannot
silently redefine the old fixture.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
from pathlib import Path

from src.contracts.common.ids import stable_digest
from src.contracts.workflow.models import WorkflowDefinition
from src.persistence.migration_runner import apply_migrations, discover_migrations
from src.persistence.sqlite_port import SqlitePersistence
from src.services.workflow_registry import WorkflowRegistryService

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DATABASE = HERE / "pre-fix-024.db"
CHECKSUM = HERE / "pre-fix-024.sha256"
MANIFEST = HERE / "rev1-manifest.json"
MIGRATIONS = ROOT / "src/persistence/migrations"
NOW = "2026-08-31T00:00:00Z"


async def _populate() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    definitions = [
        WorkflowDefinition.model_validate(row["canonical_definition"], strict=False) for row in manifest["workflows"]
    ]
    persistence = SqlitePersistence(DATABASE, MIGRATIONS)
    registry = WorkflowRegistryService(persistence)
    identities = [await registry.register(definition) for definition in definitions]
    identity = identities[0]
    team_uuid = "00000000-0000-7000-8000-000000000001"
    task_uuid = "00000000-0000-7000-8000-000000000002"
    trace_uuid = "00000000-0000-7000-8000-000000000003"
    execution_uuid = "00000000-0000-7000-8000-000000000004"
    object_uuid = "00000000-0000-7000-8000-000000000005"
    digest = "a" * 64
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_teams(team_uuid,name,creation_fingerprint,created_at,updated_at) VALUES (?,?,?,?,?)",
            (team_uuid, "nhx1-pre-fix-team", stable_digest({"fixture": "team"}), NOW, NOW),
        )
        await tx.execute(
            "INSERT INTO mkb_tasks(team_uuid,task_uuid,trace_uuid,schema_version,request_intent,creation_fingerprint,"
            "audit_bound,title,status,current_generation,current_root_execution_uuid,received_at,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,1,?,'failed',1,?,?,?,?)",
            (
                team_uuid,
                task_uuid,
                trace_uuid,
                "mkb.task.v1",
                "intake.ingest",
                stable_digest({"fixture": "task"}),
                "NHX1 persisted legacy task",
                execution_uuid,
                NOW,
                NOW,
                NOW,
            ),
        )
        await tx.execute(
            "INSERT INTO mkb_executions(execution_uuid,team_uuid,task_uuid,trace_uuid,generation,root_execution_uuid,"
            "execution_role,target_kind,workflow_uuid,workflow_revision_uuid,compiled_digest,resolver_decision_digest,"
            "domain_binding_digest,s05_binding_digest,config_snapshot_ref,config_snapshot_digest,status,created_at,"
            "completed_at,updated_at) VALUES (?,?,?,?,?,?,'root','task',?,?,?,?,?,?,?,?,'failed',?,?,?)",
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
                stable_digest({"fixture": "resolver"}),
                stable_digest({"fixture": "binding"}),
                stable_digest({"fixture": "s05"}),
                f"mkbfixture:config:{digest}",
                digest,
                NOW,
                NOW,
                NOW,
            ),
        )
        await tx.execute(
            "INSERT INTO mkb_workflow_selected_outputs(selection_uuid,team_uuid,execution_uuid,control_step_key,"
            "control_version,candidate_port,selected_source_process_uuid,output_manifest_ref,output_manifest_digest,"
            "route_decision_digest,selection_digest,fallback_used,projected_at,payload_extra) "
            "VALUES (?,?,?,?,?,? ,NULL,?,?,?,?,0,?,'{}')",
            (
                "00000000-0000-7000-8000-000000000006",
                team_uuid,
                execution_uuid,
                "selected_clean",
                "mkb.selected-output.v1",
                "clean_candidate",
                f"mkbfixture:manifest:{digest}",
                digest,
                "b" * 64,
                "c" * 64,
                NOW,
            ),
        )
        await tx.execute(
            "INSERT INTO mkb_stored_objects(stored_object_uuid,team_uuid,content_digest,size_bytes,media_type,created_at) "
            "VALUES (?,?,?,?,?,?)",
            (object_uuid, team_uuid, digest, 17, "text/plain", NOW),
        )
        await tx.execute(
            "INSERT INTO mkb_object_references(reference_uuid,team_uuid,stored_object_uuid,purpose,owner_kind,owner_uuid,"
            "expected_digest,expected_size,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                "00000000-0000-7000-8000-000000000007",
                team_uuid,
                object_uuid,
                "upload_pending",
                "public_upload",
                "00000000-0000-7000-8000-000000000008",
                digest,
                17,
                NOW,
            ),
        )
    await persistence.close()


def build() -> None:
    if DATABASE.exists():
        DATABASE.unlink()
    connection = sqlite3.connect(DATABASE)
    try:
        migrations = [migration for migration in discover_migrations(MIGRATIONS) if migration.migration_id <= "024_nh_review_invariants"]
        apply_migrations(connection, migrations)
        connection.execute("UPDATE mkb_schema_migrations SET applied_at=?, applied_by='mkb-fixture'", (NOW,))
        connection.commit()
    finally:
        connection.close()
    asyncio.run(_populate())
    connection = sqlite3.connect(DATABASE)
    try:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("VACUUM")
    finally:
        connection.close()
    CHECKSUM.write_text(hashlib.sha256(DATABASE.read_bytes()).hexdigest() + "  pre-fix-024.db\n", encoding="utf-8")


if __name__ == "__main__":
    build()
