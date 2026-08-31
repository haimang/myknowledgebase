"""NHX1-T11: terminal execution fences late outcomes and domain conflicts fail loud."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts.common.errors import ConflictError
from src.contracts.common.ids import stable_digest
from src.contracts.runtime.models import ProcessOutcome
from src.runtime.workflow.helpers import canonical_outcome_digest
from src.runtime.workflow.worker import WorkflowWorker
from tests.unit.test_workflow_runtime import _seed_runtime


@pytest.mark.asyncio
async def test_terminal_execution_rejects_late_outcome_without_follow_on_process(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    try:
        assert await runtime.materialize_root(ids["execution_uuid"])
        claim = await runtime.claim_next("nhx1-terminal")
        assert claim is not None
        await runtime.mark_running(claim.command.process_uuid, claim.command.fencing_generation)
        outcome = ProcessOutcome(
            schema_version="mkb.process-outcome.v1",
            team_uuid=ids["team_uuid"],
            task_uuid=ids["task_uuid"],
            execution_uuid=ids["execution_uuid"],
            process_uuid=claim.command.process_uuid,
            fencing_generation=claim.command.fencing_generation,
            disposition="succeeded",
            outcome_digest="0" * 64,
            output_manifest_ref="mkbtest:late-output",
            output_manifest_digest=stable_digest({"late": "output"}),
            proof_ref="mkbtest:late-proof",
            proof_digest=stable_digest({"late": "proof"}),
        )
        outcome = outcome.model_copy(update={"outcome_digest": canonical_outcome_digest(outcome)})
        async with persistence.transaction() as tx:
            await tx.execute(
                "UPDATE mkb_executions SET status='failed',final_error_code='TEST_TERMINAL' WHERE execution_uuid=?",
                (ids["execution_uuid"],),
            )
        with pytest.raises(ConflictError, match="terminal Execution"):
            await runtime.accept_outcome(outcome)
        async with persistence.read_snapshot() as tx:
            process = await tx.fetchone(
                "SELECT status,accepted_outcome_digest FROM mkb_processes WHERE process_uuid=?",
                (claim.command.process_uuid,),
            )
            follow_on = await tx.fetchone(
                "SELECT COUNT(*) AS count FROM mkb_processes WHERE execution_uuid=?",
                (ids["execution_uuid"],),
            )
        assert process == {"status": "running", "accepted_outcome_digest": None}
        assert follow_on == {"count": 1}
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_domain_conflict_is_terminal_not_an_infinite_running_process(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    try:
        assert await runtime.materialize_root(ids["execution_uuid"])
        # A stage with an invalid success proof exercises the worker's typed
        # domain-failure path; the Process must not remain running after the
        # callback rejects its contract.
        class InvalidProofStage:
            async def run(self, command):
                provisional = ProcessOutcome(
                    schema_version="mkb.process-outcome.v1",
                    team_uuid=command.team_uuid,
                    task_uuid=command.task_uuid,
                    execution_uuid=command.execution_uuid,
                    process_uuid=command.process_uuid,
                    fencing_generation=command.fencing_generation,
                    disposition="succeeded",
                    outcome_digest="0" * 64,
                )
                return provisional.model_copy(update={"outcome_digest": canonical_outcome_digest(provisional)})

        worker = WorkflowWorker(runtime, InvalidProofStage())
        assert await worker.run_once("nhx1-domain")
        async with persistence.read_snapshot() as tx:
            process = await tx.fetchone(
                "SELECT status,error_code FROM mkb_processes WHERE execution_uuid=?",
                (ids["execution_uuid"],),
            )
        assert process["status"] == "failed"
        assert process["error_code"] == "outcome-proof-invalid"
    finally:
        await persistence.close()
