"""Persistence ports. Domain services depend on these abstractions, never a driver."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import AbstractAsyncContextManager
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class UnitOfWork(Protocol):
    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any: ...

    async def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None: ...

    async def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]: ...


@runtime_checkable
class PersistencePort(Protocol):
    def transaction(self) -> AbstractAsyncContextManager[UnitOfWork]: ...

    async def readiness(self) -> dict[str, bool]: ...

    async def migrate(self) -> None: ...

    async def close(self) -> None: ...


@runtime_checkable
class TaskRepository(Protocol):
    async def get_task(self, team_uuid: str, task_uuid: str) -> dict[str, Any] | None: ...


@runtime_checkable
class IntakeEligibilityPort(Protocol):
    """S04's batch read fence consumed by S10.

    The return value contains only vector-record UUIDs that remain eligible
    after the authoritative team/item/serving-revision/lifecycle check.  The
    compact mapping input deliberately avoids importing a service or a driver
    into this low-level port module.
    """

    async def filter_retrieval_eligible(
        self, *, team_uuid: str, candidates: Sequence[Mapping[str, str]]
    ) -> set[str]: ...


@runtime_checkable
class RetrievalBodyPort(Protocol):
    """Read immutable dual-channel material by a generation-scoped coordinate.

    Implementations may dereference a logical object handle, but the retrieval
    service never receives a filesystem path and never imports an object-store
    adapter directly.
    """

    async def load_retrieval_body(
        self,
        *,
        team_uuid: str,
        generation_artifact_uuid: str,
        unit_id: str,
        channel: str,
    ) -> Mapping[str, Any] | str | None: ...
