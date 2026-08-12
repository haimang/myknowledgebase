"""Workflow runtime protocols and claim/outbox value objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from src.contracts.runtime.models import ProcessCommand, ProcessOutcome
from src.persistence.ports import UnitOfWork


@runtime_checkable
class ProcessStageHandler(Protocol):
    """Business-stage port.

    Implementations must make any external side effect idempotent on
    ``(process_uuid, fencing_generation)`` (or a stricter business key), and
    then return a ``ProcessOutcome``.  They do not choose a route or mutate
    Task/Execution/Process records.
    """

    async def run(self, command: ProcessCommand) -> ProcessOutcome: ...


@runtime_checkable
class ProcessOutcomeCommitter(Protocol):
    """Atomic bridge from a successful stage outcome to its owned catalogues.

    The committer runs inside the same persistence transaction as the Process
    outcome CAS.  It may register/promote output and proof references in the
    object, generation, or vector owners' tables, but it must not choose a
    workflow route or mutate Task/Execution/Process state.  Raising aborts the
    whole transaction; the caller must then either preserve a stale/conflict
    fence or submit a bounded failure outcome for the still-running Process.
    """

    async def validate_and_commit(
        self,
        tx: UnitOfWork,
        command: ProcessCommand,
        outcome: ProcessOutcome,
    ) -> None: ...


@runtime_checkable
class ReadinessProbe(Protocol):
    """Small, injectable readiness boundary used before accepting a new claim."""

    async def __call__(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class ClaimedProcess:
    """An in-memory delivery envelope; it is not a fourth durable identity."""

    command: ProcessCommand
    claim_token: str
    lease_expires_at: str


@dataclass(frozen=True, slots=True)
class OutboxDelivery:
    """One leased scheduling intent returned by the local outbox worker."""

    outbox_id: str
    team_uuid: str
    kind: str
    payload: dict[str, Any]
    lease_owner: str
