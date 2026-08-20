"""Composition-root factory. Domain code never selects a driver."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Literal, Protocol


def sqlite_backend_permitted() -> bool:
    """Stock sqlite is a pytest fixture only (NS4 T-O-364 / T-O-371).

    Both factors are required: the pytest env marker *and* a real pytest
    import.  Forging ``PYTEST_CURRENT_TEST`` in a production process is
    not enough; ``MKB_ALLOW_SQLITE`` is not a permit factor.
    """

    return bool(os.environ.get("PYTEST_CURRENT_TEST")) and "pytest" in sys.modules


class PersistenceEngine(Protocol):
    database_path: Path

    async def migrate(self) -> None: ...

    def transaction(self): ...

    async def readiness(self) -> dict[str, bool]: ...

    async def close(self) -> None: ...


def build_persistence(
    database_path: Path,
    migration_directory: Path,
    *,
    backend: Literal["sqlite", "turso"] = "turso",
    vector_backend: Literal["deterministic_exact", "native_ann"] = "deterministic_exact",
    concurrent_writes_required: bool = True,
    native_vector_required: bool = True,
) -> PersistenceEngine:
    if backend == "sqlite":
        if not sqlite_backend_permitted():
            raise ValueError("sqlite persistence is test-only; production and 0815 must use turso")
        from src.persistence.sqlite_port import SqlitePersistence

        return SqlitePersistence(
            database_path,
            migration_directory,
            vector_backend=vector_backend,
            concurrent_writes_required=concurrent_writes_required,
            native_vector_required=native_vector_required,
        )
    if backend != "turso":
        raise ValueError("persistence backend is unsupported")
    if vector_backend == "native_ann":
        raise ValueError("native_ann is not bound; VectorSearchPort is not implemented")
    from src.persistence.turso.port import TursoPersistence

    return TursoPersistence(
        database_path,
        migration_directory,
        concurrent_writes_required=concurrent_writes_required,
        native_vector_required=native_vector_required,
    )
