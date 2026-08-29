"""NH3-T07: selected route, actual seal, and clean eligibility are one UoW."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.errors import ConflictError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.intake.representation import RepresentationObservation
from src.contracts.runtime.models import ProcessOutcome
from src.persistence.ports import UnitOfWork
from src.runtime.binding.actual_s05 import seal_actual_binding_tx
from src.runtime.intake.representation_history import (
    PersistenceRepresentationFactReader,
    append_representation_tx,
    prepare_representation_append,
)
from src.runtime.workflow_engine import WorkflowRuntime
from src.workflows.builtin_lsrag import BUILTIN_HTTP_RESOURCE_KIND_WORKFLOW
from tests.e2e.test_registered_api_scatter import (
    _create_team,
    _records,
    _settings,
    _submit,
    _wait_for_gate,
)
from tests.integration.test_nh2_selected_output_control import _seed, _seed_candidate
from tests.integration.test_nh3_fact_history_uow import _running_process, _success


class _DecodedFactCommitter:
    async def validate_and_commit(
        self,
        tx: UnitOfWork,
        command,
        outcome: ProcessOutcome,
    ) -> None:
        del outcome
        assert command.step_key == "decode_web_static"
        await append_representation_tx(
            tx,
            prepare_representation_append(
                RepresentationObservation(
                    team_uuid=command.team_uuid,
                    execution_uuid=command.execution_uuid,
                    process_uuid=command.process_uuid,
                    step_key=command.step_key,
                    fact_kind="decode",
                    capability=command.process_key,
                    representation_kind="transferred",
                    declared_media_type="text/html",
                    detected_media_type="text/html",
                    verified_media_type="text/html",
                    raw_byte_digest=stable_digest({"raw": "decoded-main"}),
                    raw_byte_size=24,
                    main_text_presence="present",
                    canonicalizer_key="utf8-lf-nfc",
                    canonicalizer_version="v1",
                    observer_key="deterministic-html-main-text",
                    observer_version="v1",
                )
            ),
        )


async def _runtime(tmp_path: Path, name: str):
    reader = PersistenceRepresentationFactReader()
    persistence, _, definition, identity, ids = await _seed(
        tmp_path,
        name,
        graph=BUILTIN_HTTP_RESOURCE_KIND_WORKFLOW,
        representation_facts=reader,
    )
    async with persistence.transaction() as tx:
        await tx.execute(
            "UPDATE mkb_executions SET actual_binding_state='unsealed',actual_binding_digest=NULL,seal_generation=0 "
            "WHERE execution_uuid=?",
            (ids["execution_uuid"],),
        )
    acquire_process, _ = await _seed_candidate(
        persistence,
        identity,
        ids,
        step_key="acquire_static",
        suffix=f"{name}-acquire",
    )
    async with persistence.transaction() as tx:
        await append_representation_tx(
            tx,
            prepare_representation_append(
                RepresentationObservation(
                    team_uuid=ids["team_uuid"],
                    execution_uuid=ids["execution_uuid"],
                    process_uuid=acquire_process,
                    step_key="acquire_static",
                    fact_kind="acquire",
                    capability="intake.acquire.http_static",
                    representation_kind="transferred",
                    declared_media_type="text/html",
                    detected_media_type="text/html",
                    verified_media_type="text/html",
                    raw_byte_digest=stable_digest({"raw": "acquired-shell"}),
                    raw_byte_size=31,
                    main_text_presence="unknown",
                    canonicalizer_key="raw-byte-identity",
                    canonicalizer_version="v1",
                    observer_key="media-signature-sniffer",
                    observer_version="v1",
                )
            ),
        )
    process_uuid = await _running_process(
        persistence,
        identity,
        ids,
        step_key="decode_web_static",
        suffix=f"{name}-decode",
    )
    runtime = WorkflowRuntime(
        persistence,
        definition,
        outcome_committer=_DecodedFactCommitter(),
        representation_facts=reader,
    )
    return persistence, runtime, ids, process_uuid


async def _assert_rolled_back(persistence, ids: dict[str, str], process_uuid: str) -> None:
    async with persistence.transaction() as tx:
        execution = await tx.fetchone(
            "SELECT actual_binding_state,actual_binding_digest,seal_generation FROM mkb_executions "
            "WHERE execution_uuid=?",
            (ids["execution_uuid"],),
        )
        process = await tx.fetchone(
            "SELECT status FROM mkb_processes WHERE process_uuid=?", (process_uuid,)
        )
        history = await tx.fetchone(
            "SELECT COUNT(*) AS count FROM mkb_acquire_decode_history WHERE execution_uuid=?",
            (ids["execution_uuid"],),
        )
        clean = await tx.fetchone(
            "SELECT COUNT(*) AS count FROM mkb_processes WHERE execution_uuid=? AND process_key LIKE 'clean.%'",
            (ids["execution_uuid"],),
        )
    assert execution == {
        "actual_binding_state": "unsealed",
        "actual_binding_digest": None,
        "seal_generation": 0,
    }
    assert process == {"status": "running"}
    assert history == {"count": 1}
    assert clean == {"count": 0}


@pytest.mark.asyncio
@pytest.mark.parametrize("window", ["W-SEL", "W-SEAL"])
async def test_route_seal_fault_windows_leave_no_half_commit(tmp_path: Path, window: str) -> None:
    persistence, runtime, ids, process_uuid = await _runtime(tmp_path, f"fault-{window.lower()}")

    def fault(stage: str) -> None:
        if stage == window:
            raise RuntimeError(f"fault-{window}")

    runtime.actual_s05_fault_hook = fault
    try:
        with pytest.raises(RuntimeError, match=f"fault-{window}"):
            await runtime.accept_outcome(_success(ids, process_uuid, window))
        await _assert_rolled_back(persistence, ids, process_uuid)
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_route_seal_and_clean_eligibility_commit_together_and_propagate_command(tmp_path: Path) -> None:
    persistence, runtime, ids, process_uuid = await _runtime(tmp_path, "seal-success")
    outcome = _success(ids, process_uuid, "seal-success")
    try:
        async with persistence.transaction() as tx:
            running = await runtime._process_with_execution(tx, process_uuid)  # noqa: SLF001
        unsealed_command = runtime._command_from_process(running)  # noqa: SLF001
        assert unsealed_command.binding_state == "unsealed"
        assert unsealed_command.binding_digest is None
        assert unsealed_command.policy_binding_digest == running["domain_binding_digest"]
        assert await runtime.accept_outcome(outcome)
        assert not await runtime.accept_outcome(outcome)
        async with persistence.transaction() as tx:
            execution = await tx.fetchone(
                "SELECT domain_binding_digest,actual_binding_digest,actual_binding_state,seal_generation,"
                "actual_selected_route_digest,actual_clean_step_key,actual_clean_process_key,actual_clean_strategy "
                "FROM mkb_executions WHERE execution_uuid=?",
                (ids["execution_uuid"],),
            )
            clean = await tx.fetchone(
                "SELECT process_uuid,status FROM mkb_processes WHERE execution_uuid=? AND step_key='clean_web_static'",
                (ids["execution_uuid"],),
            )
        assert execution is not None and clean is not None
        assert execution["actual_binding_state"] == "sealed"
        assert execution["seal_generation"] == 1
        assert execution["actual_binding_digest"] != execution["domain_binding_digest"]
        assert execution["actual_clean_step_key"] == "clean_web_static"
        assert execution["actual_clean_process_key"] == "clean.extract.web"
        assert execution["actual_clean_strategy"] == "web.deterministic"
        assert clean["status"] == "ready"

        claimed = await runtime.claim_next("nh3-actual-command")
        assert claimed is not None
        assert claimed.command.process_uuid == clean["process_uuid"]
        assert claimed.command.binding_state == "sealed"
        assert claimed.command.binding_digest == execution["actual_binding_digest"]
        assert claimed.command.policy_binding_digest == execution["domain_binding_digest"]

        with pytest.raises(ConflictError) as raised:
            async with persistence.transaction() as tx:
                await seal_actual_binding_tx(
                    tx,
                    execution_uuid=ids["execution_uuid"],
                    selected_route_digest=stable_digest({"route": "different"}),
                    clean_step_key="clean_web_static",
                    clean_process_key="clean.extract.web",
                    clean_strategy="web.deterministic",
                )
        assert raised.value.code == "ACTUAL_S05_SEAL_CONFLICT"
        async with persistence.transaction() as tx:
            unchanged = await tx.fetchone(
                "SELECT actual_binding_digest,seal_generation FROM mkb_executions WHERE execution_uuid=?",
                (ids["execution_uuid"],),
            )
        assert unchanged == {
            "actual_binding_digest": execution["actual_binding_digest"],
            "seal_generation": 1,
        }
    finally:
        await persistence.close()


def test_sealed_actual_propagates_to_candidate_snapshot_gate_and_scatter_children(tmp_path: Path) -> None:
    headers = {"Authorization": "Bearer scatter-token"}
    team_uuid = uuid7()
    app = create_app(_settings(tmp_path))
    with TestClient(app, raise_server_exceptions=True) as client:
        _create_team(client, team_uuid=team_uuid, headers=headers)
        task_uuid = _submit(
            client,
            team_uuid=team_uuid,
            headers=headers,
            records=_records("nh3-actual"),
            require_human_review=True,
        )
        _, public_gate = _wait_for_gate(
            client,
            team_uuid=team_uuid,
            task_uuid=task_uuid,
            headers=headers,
        )
        persistence = app.state.container.persistence

        async def inspect() -> tuple[dict, dict, dict, dict, list[dict]]:
            async with persistence.transaction() as tx:
                root = await tx.fetchone(
                    "SELECT execution_uuid,domain_binding_digest,s05_binding_digest,actual_binding_digest,"
                    "actual_binding_state FROM mkb_executions WHERE team_uuid=? AND task_uuid=? "
                    "AND parent_execution_uuid IS NULL",
                    (team_uuid, task_uuid),
                )
                assert root is not None
                candidate = await tx.fetchone(
                    "SELECT s05_binding_digest,actual_binding_digest,actual_binding_state "
                    "FROM mkb_intake_candidate_sets WHERE producer_execution_uuid=?",
                    (root["execution_uuid"],),
                )
                snapshot = await tx.fetchone(
                    "SELECT s05_binding_digest,actual_binding_digest,actual_binding_state "
                    "FROM mkb_intake_snapshots WHERE producer_execution_uuid=?",
                    (root["execution_uuid"],),
                )
                gate = await tx.fetchone(
                    "SELECT g.actual_binding_digest,g.actual_binding_state,t.review_target_json "
                    "FROM mkb_execution_gates g JOIN mkb_execution_gate_targets t ON t.gate_uuid=g.gate_uuid "
                    "WHERE g.gate_uuid=?",
                    (public_gate["gate_uuid"],),
                )
                children = await tx.fetchall(
                    "SELECT domain_binding_digest,s05_binding_digest,actual_binding_digest,actual_binding_state "
                    "FROM mkb_executions WHERE team_uuid=? AND task_uuid=? AND parent_execution_uuid IS NOT NULL",
                    (team_uuid, task_uuid),
                )
            assert candidate is not None and snapshot is not None and gate is not None
            return root, candidate, snapshot, gate, children

        root, candidate, snapshot, gate, children = client.portal.call(inspect)
        actual = root["actual_binding_digest"]
        assert root["actual_binding_state"] == "sealed" and actual
        assert actual != root["domain_binding_digest"]
        assert root["s05_binding_digest"] == root["domain_binding_digest"]
        for projection in (candidate, snapshot, gate, *children):
            assert projection["actual_binding_state"] == "sealed"
            assert projection["actual_binding_digest"] == actual
        assert candidate["s05_binding_digest"] != actual
        assert snapshot["s05_binding_digest"] != actual
        assert children and all(child["s05_binding_digest"] == child["domain_binding_digest"] for child in children)
        target = json.loads(gate["review_target_json"])
        assert target["workflow_binding"]["actual_binding_state"] == "sealed"
        assert target["workflow_binding"]["actual_binding_digest"] == actual
        assert "s05_binding_digest" not in target["workflow_binding"]
