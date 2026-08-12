"""Persistence ports. Domain services depend on these abstractions, never a driver."""

from __future__ import annotations

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


@runtime_checkable
class TaskRepository(Protocol):
    async def get_task(self, team_uuid: str, task_uuid: str) -> dict[str, Any] | None: ...
