"""S03 registry regressions for immutable code-owned workflow revisions."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts.workflow.models import WorkflowDefinition
from src.persistence.sqlite_port import SqlitePersistence
from src.services.workflow_registry import WorkflowRegistryService
from src.workflows.builtin_lsrag import BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW


def _v1_before_index_rebuild() -> WorkflowDefinition:
    """Return the prior immutable graph shape without the new S09 branch.

    The helper deliberately derives a historical declaration from the current
    static source rather than relying on a Git checkout at test time.  It
    models a database that already contains revision 1 when revision 2 gains
    the independently schedulable ``index.rebuild`` Process.
    """

    # The contracts are strict, so retain enum instances rather than the JSON
    # strings a transport payload would contain.
    document = BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW.model_dump()
    document["revision_number"] = 1
    document["context_slots"] = [
        slot for slot in document["context_slots"] if slot["slot_name"] != "index_rebuild_scope"
    ]
    document["required_process_keys"] = [key for key in document["required_process_keys"] if key != "index.rebuild"]
    document["steps"] = [step for step in document["steps"] if step["step_key"] != "index_rebuild"]
    document["routes"] = [
        route
        for route in document["routes"]
        if route["from_step_key"] != "index_rebuild"
        and route["to_step_key"] != "index_rebuild"
        and route["guard_key"] != "request_intent_index_rebuild"
    ]
    document["bindings"] = [
        binding for binding in document["bindings"] if binding["target_step_key"] != "index_rebuild"
    ]
    document["guards"] = [guard for guard in document["guards"] if guard["guard_key"] != "request_intent_index_rebuild"]
    return WorkflowDefinition.model_validate(document)


@pytest.mark.asyncio
async def test_registry_appends_v2_without_mutating_or_rebinding_v1(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "registry.sqlite3", Path("src/persistence/migrations"))
    await persistence.migrate()
    registry = WorkflowRegistryService(persistence)
    v1 = _v1_before_index_rebuild()

    try:
        registered_v1 = await registry.register(v1)
        assert (await registry.resolve(v1.purpose_key)).workflow_revision_uuid == registered_v1.workflow_revision_uuid

        registered_v2 = await registry.register(BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW)
        replayed_v2 = await registry.register(BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW)

        assert registered_v2.workflow_uuid == registered_v1.workflow_uuid
        assert registered_v2.workflow_revision_uuid != registered_v1.workflow_revision_uuid
        assert replayed_v2 == registered_v2
        assert (await registry.resolve(v1.purpose_key)).workflow_revision_uuid == registered_v2.workflow_revision_uuid

        async with persistence.transaction() as tx:
            revisions = await tx.fetchall(
                "SELECT workflow_revision_uuid,revision_number,registration_fingerprint,compiled_digest "
                "FROM mkb_workflow_revisions WHERE workflow_uuid=? ORDER BY revision_number",
                (registered_v1.workflow_uuid,),
            )
            active = await tx.fetchone(
                "SELECT active_revision_uuid FROM mkb_workflow_registry WHERE workflow_uuid=?",
                (registered_v1.workflow_uuid,),
            )
            v1_steps = await tx.fetchall(
                "SELECT step_key FROM mkb_workflow_steps WHERE workflow_revision_uuid=? ORDER BY order_hint",
                (registered_v1.workflow_revision_uuid,),
            )
            v2_steps = await tx.fetchall(
                "SELECT step_key FROM mkb_workflow_steps WHERE workflow_revision_uuid=? ORDER BY order_hint",
                (registered_v2.workflow_revision_uuid,),
            )

        assert [row["revision_number"] for row in revisions] == [1, 2]
        assert [row["workflow_revision_uuid"] for row in revisions] == [
            registered_v1.workflow_revision_uuid,
            registered_v2.workflow_revision_uuid,
        ]
        assert revisions[0]["registration_fingerprint"] != revisions[1]["registration_fingerprint"]
        assert revisions[0]["compiled_digest"] != revisions[1]["compiled_digest"]
        assert active == {"active_revision_uuid": registered_v2.workflow_revision_uuid}
        assert "index_rebuild" not in [row["step_key"] for row in v1_steps]
        assert "index_rebuild" in [row["step_key"] for row in v2_steps]
    finally:
        await persistence.close()
