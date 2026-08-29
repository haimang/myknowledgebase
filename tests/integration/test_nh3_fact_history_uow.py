"""NH3-T01: representation facts share the successful Outcome transaction."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts.common.errors import ConflictError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.intake.representation import RepresentationObservation
from src.contracts.runtime.models import ProcessOutcome
from src.persistence.ports import UnitOfWork
from src.runtime.intake.representation_history import (
    append_representation_tx,
    prepare_representation_append,
)
from src.runtime.workflow.helpers import canonical_outcome_digest
from src.runtime.workflow_engine import WorkflowRuntime
from tests.integration.test_nh2_selected_output_control import _seed


class _FactCommitter:
    def __init__(self, *, explode: bool = False) -> None:
        self.explode = explode

    async def validate_and_commit(self, tx: UnitOfWork, command, outcome: ProcessOutcome) -> None:
        del outcome
        assert command.step_key is not None
        prepared = prepare_representation_append(
            RepresentationObservation(
                team_uuid=command.team_uuid,
                execution_uuid=command.execution_uuid,
                process_uuid=command.process_uuid,
                step_key=command.step_key,
                fact_kind="acquire",
                capability=command.process_key,
                representation_kind="transferred",
                declared_media_type="text/plain",
                detected_media_type="text/plain",
                verified_media_type="text/plain",
                raw_byte_digest=stable_digest({"raw": command.step_key}),
                raw_byte_size=4,
                main_text_presence="unknown",
                canonicalizer_key="raw-byte-identity",
                canonicalizer_version="v1",
                observer_key="test-observer",
                observer_version="v1",
            )
        )
        await append_representation_tx(tx, prepared)
        if self.explode:
            raise RuntimeError("fault-after-fact-before-outcome-cas")


async def _running_process(persistence, identity, ids: dict[str, str], *, step_key: str, suffix: str) -> str:
    process_uuid = uuid7()
    now = utc_now()
    async with persistence.transaction() as tx:
        step = await tx.fetchone(
            "SELECT workflow_step_uuid,process_key,process_contract_version,requiredness "
            "FROM mkb_workflow_steps WHERE workflow_revision_uuid=? AND step_key=?",
            (identity.workflow_revision_uuid, step_key),
        )
        assert step is not None
        await tx.execute(
            "INSERT INTO mkb_processes(process_uuid,team_uuid,execution_uuid,task_uuid,root_execution_uuid,"
            "workflow_step_uuid,step_key,process_key,process_contract_version,materialization_key,requiredness,"
            "process_spec_digest,input_manifest_ref,input_manifest_digest,config_snapshot_ref,config_snapshot_digest,"
            "proof_kind,status,row_revision,available_at,priority_rank,fencing_generation,max_retries,max_recoveries,"
            "backoff_policy_json,dispatch_admitted,started_at,created_at,updated_at,payload_extra) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'running',0,?,0,1,0,0,'{}',1,?,?,?,'{}')",
            (
                process_uuid,
                ids["team_uuid"],
                ids["execution_uuid"],
                ids["task_uuid"],
                ids["execution_uuid"],
                step["workflow_step_uuid"],
                step_key,
                step["process_key"],
                step["process_contract_version"],
                stable_digest({"materialization": suffix}),
                step["requiredness"],
                stable_digest({"spec": suffix}),
                f"mkbtest:input:{suffix}",
                stable_digest({"input": suffix}),
                f"mkbtest:config:{suffix}",
                stable_digest({"config": suffix}),
                "clean_candidate",
                now,
                now,
                now,
                now,
            ),
        )
    return process_uuid


def _success(ids: dict[str, str], process_uuid: str, suffix: str) -> ProcessOutcome:
    output_digest = stable_digest({"output": suffix})
    proof_digest = stable_digest({"proof": suffix})
    provisional = ProcessOutcome(
        schema_version="mkb.process-outcome.v1",
        team_uuid=ids["team_uuid"],
        task_uuid=ids["task_uuid"],
        execution_uuid=ids["execution_uuid"],
        process_uuid=process_uuid,
        fencing_generation=1,
        disposition="succeeded",
        outcome_digest="0" * 64,
        output_manifest_ref=f"mkbtest:output:{suffix}",
        output_manifest_digest=output_digest,
        proof_ref=f"mkbtest:proof:{suffix}",
        proof_digest=proof_digest,
    )
    return provisional.model_copy(update={"outcome_digest": canonical_outcome_digest(provisional)})


@pytest.mark.asyncio
async def test_success_appends_fact_and_history_with_outcome(tmp_path: Path) -> None:
    persistence, _, definition, identity, ids = await _seed(tmp_path, "fact-success")
    runtime = WorkflowRuntime(persistence, definition, outcome_committer=_FactCommitter())
    try:
        process_uuid = await _running_process(
            persistence, identity, ids, step_key="candidate_a", suffix="success"
        )
        assert await runtime.accept_outcome(_success(ids, process_uuid, "success"))
        async with persistence.transaction() as tx:
            process = await tx.fetchone(
                "SELECT status FROM mkb_processes WHERE process_uuid=?", (process_uuid,)
            )
            facts = await tx.fetchall(
                "SELECT process_uuid,step_key,fact_digest FROM mkb_representation_facts WHERE execution_uuid=?",
                (ids["execution_uuid"],),
            )
            history = await tx.fetchall(
                "SELECT process_uuid,step_key,ordinal,representation_path_digest "
                "FROM mkb_acquire_decode_history WHERE execution_uuid=?",
                (ids["execution_uuid"],),
            )
        assert process == {"status": "succeeded"}
        assert len(facts) == len(history) == 1
        assert facts[0]["process_uuid"] == history[0]["process_uuid"] == process_uuid
        assert facts[0]["step_key"] == history[0]["step_key"] == "candidate_a"
        assert history[0]["ordinal"] == 1
        assert len(history[0]["representation_path_digest"]) == 64
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_rollback_leaves_zero_fact_and_history_rows(tmp_path: Path) -> None:
    persistence, _, definition, identity, ids = await _seed(tmp_path, "fact-rollback")
    runtime = WorkflowRuntime(persistence, definition, outcome_committer=_FactCommitter(explode=True))
    try:
        process_uuid = await _running_process(
            persistence, identity, ids, step_key="candidate_b", suffix="rollback"
        )
        with pytest.raises(RuntimeError, match="fault-after-fact-before-outcome-cas"):
            await runtime.accept_outcome(_success(ids, process_uuid, "rollback"))
        async with persistence.transaction() as tx:
            process = await tx.fetchone(
                "SELECT status FROM mkb_processes WHERE process_uuid=?", (process_uuid,)
            )
            fact_count = await tx.fetchone(
                "SELECT COUNT(*) AS count FROM mkb_representation_facts WHERE execution_uuid=?",
                (ids["execution_uuid"],),
            )
            history_count = await tx.fetchone(
                "SELECT COUNT(*) AS count FROM mkb_acquire_decode_history WHERE execution_uuid=?",
                (ids["execution_uuid"],),
            )
        assert process == {"status": "running"}
        assert fact_count == history_count == {"count": 0}
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_second_success_for_same_step_is_rejected_without_overwrite(tmp_path: Path) -> None:
    persistence, _, definition, identity, ids = await _seed(tmp_path, "fact-conflict")
    runtime = WorkflowRuntime(persistence, definition, outcome_committer=_FactCommitter())
    try:
        first = await _running_process(persistence, identity, ids, step_key="candidate_a", suffix="first")
        second = await _running_process(persistence, identity, ids, step_key="candidate_a", suffix="second")
        assert await runtime.accept_outcome(_success(ids, first, "first"))
        with pytest.raises(ConflictError) as raised:
            await runtime.accept_outcome(_success(ids, second, "second"))
        assert raised.value.code == "representation-step-conflict"
        async with persistence.transaction() as tx:
            rows = await tx.fetchall(
                "SELECT process_uuid,fact_digest FROM mkb_representation_facts WHERE execution_uuid=? AND step_key=?",
                (ids["execution_uuid"], "candidate_a"),
            )
            second_row = await tx.fetchone(
                "SELECT status FROM mkb_processes WHERE process_uuid=?", (second,)
            )
        assert len(rows) == 1 and rows[0]["process_uuid"] == first
        assert second_row == {"status": "running"}
    finally:
        await persistence.close()
