"""Workflow worker loop: claim → handler.run → accept_outcome."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Literal

from src.contracts.common.errors import ConflictError, MkbError
from src.contracts.runtime.models import ProcessCommand, ProcessOutcome
from src.runtime.workflow.helpers import canonical_outcome_digest
from src.runtime.workflow.runtime import WorkflowRuntime
from src.runtime.workflow.runtime_outcome import _safe_persisted_error
from src.runtime.workflow.types import ProcessStageHandler


def _safe_error_message(message: str) -> str:
    return _safe_persisted_error(message)


class WorkflowWorker:
    """Small worker loop that invokes an injected stage handler exactly via claims."""

    def __init__(self, runtime: WorkflowRuntime, handler: ProcessStageHandler) -> None:
        self.runtime = runtime
        self.handler = handler

    @staticmethod
    def _failure_outcome(
        command: ProcessCommand,
        *,
        disposition: Literal["failed", "retryable_failure"],
        error_code: str,
        error_message: str,
    ) -> ProcessOutcome:
        """Build one canonical fallback Outcome for an already claimed Process."""

        provisional = ProcessOutcome(
            schema_version="mkb.process-outcome.v1",
            team_uuid=command.team_uuid,
            task_uuid=command.task_uuid,
            execution_uuid=command.execution_uuid,
            process_uuid=command.process_uuid,
            fencing_generation=command.fencing_generation,
            disposition=disposition,
            outcome_digest="0" * 64,
            error_code=error_code[:128],
            error_message=_safe_error_message(error_message),
        )
        return provisional.model_copy(update={"outcome_digest": canonical_outcome_digest(provisional)})

    def _discard_pending(self, command: ProcessCommand) -> None:
        committer = getattr(self.runtime, "outcome_committer", None)
        discard = getattr(committer, "discard", None)
        if callable(discard):
            discard(command)

    async def run_once(self, lease_owner: str, *, lease_seconds: int = 30) -> bool:
        """Claim, start, invoke, and submit one Process outcome."""

        claim = await self.runtime.claim_next(lease_owner, lease_seconds=lease_seconds)
        if claim is None:
            return False
        await self.runtime.mark_running(claim.command.process_uuid, claim.command.fencing_generation)
        fenced = asyncio.Event()
        handler_task = asyncio.create_task(self.handler.run(claim.command))
        heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(
                claim.command.process_uuid,
                claim.command.fencing_generation,
                lease_seconds=lease_seconds,
                handler_task=handler_task,
                fenced=fenced,
            )
        )
        try:
            try:
                outcome = await handler_task
            except asyncio.CancelledError:
                if fenced.is_set():
                    outcome = self._failure_outcome(
                        claim.command,
                        disposition="retryable_failure",
                        error_code="lease-heartbeat-fenced",
                        error_message="Process lease heartbeat lost the running fence",
                    )
                else:
                    self._discard_pending(claim.command)
                    raise
            except Exception as exc:  # Stage exception becomes an explicit bounded retryable outcome.
                outcome = self._failure_outcome(
                    claim.command,
                    disposition="retryable_failure",
                    error_code="stage-handler-exception",
                    error_message=str(exc)[:512] or "Stage handler raised an exception",
                )
            if outcome.disposition != "succeeded":
                self._discard_pending(claim.command)
            try:
                await self.runtime.accept_outcome(outcome)
            except ConflictError:
                # These are the durable stale/lease/status fences.  A worker must
                # never submit a different failure Outcome over a competing owner.
                self._discard_pending(claim.command)
                raise
            except MkbError as exc:
                # A typed callback/committer rejection aborted its success UoW, so
                # the Process is still running at this exact claim fence.  Submit
                # the domain failure as a terminal Outcome rather than waiting for
                # lease recovery to discover an otherwise deterministic error.
                self._discard_pending(claim.command)
                await self.runtime.accept_outcome(
                    self._failure_outcome(
                        claim.command,
                        disposition="failed",
                        error_code=exc.code,
                        error_message=exc.message,
                    )
                )
            except Exception:
                # Unexpected commit failures can be transient (for example a
                # database adapter interruption).  The Process retry policy owns
                # the bounded retry/recovery decision; do not expose raw details.
                self._discard_pending(claim.command)
                await self.runtime.accept_outcome(
                    self._failure_outcome(
                        claim.command,
                        disposition="retryable_failure",
                        error_code="outcome-commit-exception",
                        error_message="Outcome commit raised an unexpected error",
                    )
                )
            return True
        finally:
            heartbeat_task.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await heartbeat_task
            if not handler_task.done():
                handler_task.cancel()
                with suppress(asyncio.CancelledError):
                    await handler_task
                self._discard_pending(claim.command)

    async def _heartbeat_loop(
        self,
        process_uuid: str,
        fencing_generation: int,
        *,
        lease_seconds: int,
        handler_task: asyncio.Task[ProcessOutcome],
        fenced: asyncio.Event,
    ) -> None:
        interval = max(lease_seconds / 3.0, 0.2)
        try:
            while not handler_task.done():
                await asyncio.sleep(interval)
                if handler_task.done():
                    return
                ok = await self.runtime.heartbeat(
                    process_uuid, fencing_generation, lease_seconds=lease_seconds
                )
                if not ok:
                    fenced.set()
                    handler_task.cancel()
                    return
        except asyncio.CancelledError:
            return
        except Exception:
            fenced.set()
            handler_task.cancel()
            return
