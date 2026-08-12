"""Workflow worker loop: claim → handler.run → accept_outcome."""

from __future__ import annotations

from typing import Literal

from src.contracts.common.errors import ConflictError, MkbError
from src.contracts.runtime.models import ProcessCommand, ProcessOutcome
from src.runtime.workflow.helpers import canonical_outcome_digest
from src.runtime.workflow.runtime import WorkflowRuntime
from src.runtime.workflow.types import ProcessStageHandler


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
            error_message=error_message[:512],
        )
        return provisional.model_copy(update={"outcome_digest": canonical_outcome_digest(provisional)})

    async def run_once(self, lease_owner: str, *, lease_seconds: int = 30) -> bool:
        """Claim, start, invoke, and submit one Process outcome."""

        claim = await self.runtime.claim_next(lease_owner, lease_seconds=lease_seconds)
        if claim is None:
            return False
        await self.runtime.mark_running(claim.command.process_uuid, claim.command.fencing_generation)
        try:
            outcome = await self.handler.run(claim.command)
        except Exception as exc:  # Stage exception becomes an explicit bounded retryable outcome.
            outcome = self._failure_outcome(
                claim.command,
                disposition="retryable_failure",
                error_code="stage-handler-exception",
                error_message=str(exc)[:512] or "Stage handler raised an exception",
            )
        try:
            await self.runtime.accept_outcome(outcome)
        except ConflictError:
            # These are the durable stale/lease/status fences.  A worker must
            # never submit a different failure Outcome over a competing owner.
            raise
        except MkbError as exc:
            # A typed callback/committer rejection aborted its success UoW, so
            # the Process is still running at this exact claim fence.  Submit
            # the domain failure as a terminal Outcome rather than waiting for
            # lease recovery to discover an otherwise deterministic error.
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
            await self.runtime.accept_outcome(
                self._failure_outcome(
                    claim.command,
                    disposition="retryable_failure",
                    error_code="outcome-commit-exception",
                    error_message="Outcome commit raised an unexpected error",
                )
            )
        return True
