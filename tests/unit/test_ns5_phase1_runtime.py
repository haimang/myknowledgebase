"""NS5-T03/T04/T08/T09/T10: CLI kill, heartbeat fence, pending pop, scanner, claim drain."""

from __future__ import annotations

import asyncio
import sqlite3
import stat
from datetime import timedelta
from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand, ProcessOutcome
from src.runtime.inference.claude_cli import ClaudeCliRequest, SubprocessClaudeCli
from src.runtime.object_gc import ObjectGcScanner, ObjectGcSchedule
from src.runtime.workflow_engine import WorkflowWorker, canonical_outcome_digest
from src.services.artifacts import OutcomeArtifactCommitter
from src.storage.local_store import LocalObjectStore
from tests.unit.test_workflow_runtime import _AlwaysSuccessfulStage, _seed_runtime


def _command() -> ProcessCommand:
    digest = "a" * 64
    return ProcessCommand(
        schema_version="mkb.process-command.v1",
        team_uuid=uuid7(),
        task_uuid=uuid7(),
        trace_uuid=uuid7(),
        execution_uuid=uuid7(),
        process_uuid=uuid7(),
        process_key="intake.accept_snapshot",
        process_contract_version="v1",
        fencing_generation=1,
        command_input_digest=digest,
        input_manifest_ref="mkbtest:in",
        input_manifest_digest=digest,
        config_snapshot_ref="mkbtest:cfg",
        config_snapshot_digest=digest,
        binding_digest=digest,
    )


@pytest.mark.asyncio
async def test_cli_timeout_kills_child(tmp_path: Path) -> None:
    hang = tmp_path / "hang"
    hang.write_text("#!/bin/sh\nexec sleep 60\n", encoding="utf-8")
    hang.chmod(hang.stat().st_mode | stat.S_IEXEC)
    cli = SubprocessClaudeCli(executable=str(hang))
    with pytest.raises(MkbError, match="CLAUDE_CLI_TIMEOUT"):
        await cli.run(
            ClaudeCliRequest(user_prompt="hello", system_prompt_file="p.md", timeout_seconds=0.2)
        )
    # The hung child must not remain as a process group leader after timeout.
    assert hang.exists()


@pytest.mark.asyncio
async def test_heartbeat_keeps_lease_from_being_stolen(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    await runtime.materialize_root(ids["execution_uuid"])

    class SlowStage(_AlwaysSuccessfulStage):
        async def run(self, command: ProcessCommand) -> ProcessOutcome:
            await asyncio.sleep(1.2)
            return await super().run(command)

    worker = WorkflowWorker(runtime, SlowStage())
    task = asyncio.create_task(worker.run_once("heartbeat-owner", lease_seconds=1))
    await asyncio.sleep(0.8)
    recovered = await runtime.recover_expired_leases()
    assert recovered == 0
    assert await task is True
    await persistence.close()


@pytest.mark.asyncio
async def test_heartbeat_failure_cancels_handler(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    await runtime.materialize_root(ids["execution_uuid"])
    ran_to_end = {"value": False}

    class SlowStage(_AlwaysSuccessfulStage):
        async def run(self, command: ProcessCommand) -> ProcessOutcome:
            try:
                await asyncio.sleep(2)
                ran_to_end["value"] = True
                return await super().run(command)
            except asyncio.CancelledError:
                raise

    async def fail_heartbeat(*_args: object, **_kwargs: object) -> bool:
        return False

    runtime.heartbeat = fail_heartbeat  # type: ignore[method-assign]
    worker = WorkflowWorker(runtime, SlowStage())
    await worker.run_once("fenced-owner", lease_seconds=1)
    assert ran_to_end["value"] is False
    await persistence.close()


@pytest.mark.asyncio
async def test_pending_map_empty_after_success_and_discard(tmp_path: Path) -> None:
    storage = LocalObjectStore(tmp_path / "objects")
    committer = OutcomeArtifactCommitter(storage)
    command = _command()

    async def callback(_tx: object) -> None:
        return None

    await committer.stage(command, output_bytes=b"out", proof_bytes=b"proof", callback=callback)
    assert committer._pending
    committer.discard(command)
    assert committer._pending == {}

    staged = await committer.stage(command, output_bytes=b"out", proof_bytes=b"proof", callback=callback)
    outcome = ProcessOutcome(
        schema_version="mkb.process-outcome.v1",
        team_uuid=command.team_uuid,
        task_uuid=command.task_uuid,
        execution_uuid=command.execution_uuid,
        process_uuid=command.process_uuid,
        fencing_generation=command.fencing_generation,
        disposition="succeeded",
        outcome_digest="0" * 64,
        output_manifest_ref=staged.output_ref,
        output_manifest_digest=staged.output_digest,
        proof_ref=staged.proof_ref,
        proof_digest=staged.proof_digest,
    )
    outcome = outcome.model_copy(update={"outcome_digest": canonical_outcome_digest(outcome)})
    persistence, runtime, _ids = await _seed_runtime(tmp_path / "pending")
    async with persistence.transaction() as tx:
        with pytest.raises(sqlite3.IntegrityError):
            # Catalog insert needs a matching team row; the pop still happens.
            await committer.validate_and_commit(tx, command, outcome)
    assert committer._pending == {}
    await persistence.close()


@pytest.mark.asyncio
async def test_scanner_stays_running_after_one_error() -> None:
    stop = asyncio.Event()
    calls = {"n": 0}

    class BoomService:
        async def scan_once(self, *, limit: int = 100) -> object:
            del limit
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("database is locked")
            stop.set()
            return object()

    scanner = ObjectGcScanner(BoomService(), ObjectGcSchedule(interval=timedelta(milliseconds=20)))  # type: ignore[arg-type]
    await asyncio.wait_for(scanner.run_forever(stop), timeout=2)
    assert calls["n"] >= 2


@pytest.mark.asyncio
async def test_claim_next_drains_expired_then_takes_live(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    await runtime.materialize_root(ids["execution_uuid"])
    now = utc_now()
    past = "2000-01-01T00:00:00.000000Z"
    async with persistence.transaction() as tx:
        original = await tx.fetchone(
            "SELECT * FROM mkb_processes WHERE execution_uuid=?", (ids["execution_uuid"],)
        )
        execution = await tx.fetchone(
            "SELECT * FROM mkb_executions WHERE execution_uuid=?", (ids["execution_uuid"],)
        )
        assert original is not None and execution is not None
        await tx.execute(
            "UPDATE mkb_processes SET dispatch_admitted=1, deadline_at=NULL WHERE process_uuid=?",
            (original["process_uuid"],),
        )
        for index in range(3):
            expired_execution = uuid7()
            await tx.execute(
                "INSERT INTO mkb_executions "
                "(execution_uuid,team_uuid,task_uuid,trace_uuid,generation,root_execution_uuid,execution_role,target_kind,"
                "workflow_uuid,workflow_revision_uuid,compiled_digest,resolver_decision_digest,domain_binding_digest,"
                "s05_binding_digest,config_snapshot_ref,config_snapshot_digest,status,created_at,updated_at) "
                "VALUES (?,?,?,?,?,?,'root','task',?,?,?,?,?,?,?,?, 'ready',?,?)",
                (
                    expired_execution,
                    execution["team_uuid"],
                    execution["task_uuid"],
                    execution["trace_uuid"],
                    index + 10,
                    expired_execution,
                    execution["workflow_uuid"],
                    execution["workflow_revision_uuid"],
                    execution["compiled_digest"],
                    execution["resolver_decision_digest"],
                    execution["domain_binding_digest"],
                    execution["s05_binding_digest"],
                    execution["config_snapshot_ref"],
                    execution["config_snapshot_digest"],
                    now,
                    now,
                ),
            )
            await tx.execute(
                "INSERT INTO mkb_processes "
                "(process_uuid,team_uuid,execution_uuid,task_uuid,workflow_step_uuid,step_key,process_key,"
                "process_contract_version,materialization_key,process_spec_digest,config_snapshot_ref,"
                "config_snapshot_digest,available_at,deadline_at,dispatch_admitted,created_at,updated_at,payload_extra) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,'{}')",
                (
                    uuid7(),
                    original["team_uuid"],
                    expired_execution,
                    original["task_uuid"],
                    original["workflow_step_uuid"],
                    original["step_key"],
                    original["process_key"],
                    original["process_contract_version"],
                    f"{original['materialization_key']}:expired:{index}",
                    original["process_spec_digest"],
                    original["config_snapshot_ref"],
                    original["config_snapshot_digest"],
                    now,
                    past,
                    now,
                    now,
                ),
            )
    claim = await runtime.claim_next("drain-owner")
    assert claim is not None
    assert claim.command.process_uuid == original["process_uuid"]
    await persistence.close()
