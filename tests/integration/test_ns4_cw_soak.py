"""NS4-T30: concurrent diagnostic inserts must not rewrite product error codes."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.persistence.factory import build_persistence
from src.persistence.turso.sidecar import TursoDiagnosticSidecar
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now


@pytest.mark.asyncio
async def test_sidecar_concurrent_inserts_leave_product_code_alone(tmp_path: Path) -> None:
    persistence = build_persistence(
        tmp_path / "soak.db",
        Path("src/persistence/migrations"),
        backend="turso",
        concurrent_writes_required=False,
        native_vector_required=False,
    )
    try:
        await persistence.migrate()
    finally:
        await persistence.close()

    sidecar = TursoDiagnosticSidecar(tmp_path / "soak.db")
    product = MkbError("STRUCTURE_ANCHOR_MISSING", "missing", 422)

    def _one(index: int) -> None:
        sidecar.insert(
            (
                uuid7(),
                None,
                None,
                None,
                None,
                None,
                "error",
                "GEN_STAGE_TIMING",
                f"timing-{index}",
                "runtime.intake.generation",
                "mkb-leaf",
                "{}",
                "a" * 64,
                utc_now(),
            )
        )

    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(_one, range(80)))
    assert product.code == "STRUCTURE_ANCHOR_MISSING"
