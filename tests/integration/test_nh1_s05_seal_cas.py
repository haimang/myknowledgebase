"""NH1-T05: prove legacy/unsealed/sealed and one-UoW CAS without production DDL."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts.common.errors import ConflictError
from src.contracts.common.ids import stable_digest
from src.persistence.factory import build_persistence
from src.runtime.binding.actual_s05_spike import (
    insert_actual_s05_sample,
    install_actual_s05_spike,
    projected_actual_digest,
    seal_actual_s05,
)


async def _persistence(tmp_path: Path, name: str):
    persistence = build_persistence(
        tmp_path / f"{name}.sqlite3",
        Path("src/persistence/migrations"),
        backend="turso",
        concurrent_writes_required=False,
        native_vector_required=False,
    )
    await persistence.migrate()
    async with persistence.transaction() as tx:
        await install_actual_s05_spike(tx)
    return persistence


@pytest.mark.asyncio
async def test_legacy_unsealed_sealed_sql_distinct(tmp_path: Path) -> None:
    persistence = await _persistence(tmp_path, "states")
    domain = stable_digest({"binding": "domain"})
    actual = stable_digest({"binding": "actual"})
    try:
        async with persistence.transaction() as tx:
            await insert_actual_s05_sample(
                tx,
                execution_uuid="legacy",
                domain_binding_digest=domain,
                state="legacy_unverifiable",
            )
            await insert_actual_s05_sample(
                tx,
                execution_uuid="unsealed",
                domain_binding_digest=domain,
                state="unsealed",
            )
            await insert_actual_s05_sample(
                tx,
                execution_uuid="sealed",
                domain_binding_digest=domain,
                state="sealed",
                actual_binding_digest=actual,
            )
        async with persistence.transaction() as tx:
            rows = await tx.fetchall(
                "SELECT * FROM nh1_s05_spike_bindings ORDER BY execution_uuid"
            )
        assert {row["actual_binding_state"] for row in rows} == {
            "legacy_unverifiable",
            "unsealed",
            "sealed",
        }
        assert [row["execution_uuid"] for row in rows if projected_actual_digest(row)] == ["sealed"]
    finally:
        await persistence.close()

@pytest.mark.asyncio
async def test_seal_same_uow_as_outcome(tmp_path: Path) -> None:
    persistence = await _persistence(tmp_path, "rollback")
    domain = stable_digest({"binding": "domain"})
    actual = stable_digest({"binding": "actual"})
    route = stable_digest({"route": "selected"})
    try:
        async with persistence.transaction() as tx:
            await insert_actual_s05_sample(
                tx,
                execution_uuid="rollback",
                domain_binding_digest=domain,
                state="unsealed",
            )
        with pytest.raises(RuntimeError, match="fault-after-seal-before-commit"):
            async with persistence.transaction() as tx:
                await seal_actual_s05(
                    tx,
                    execution_uuid="rollback",
                    actual_binding_digest=actual,
                    selected_route_digest=route,
                )
                raise RuntimeError("fault-after-seal-before-commit")
        async with persistence.transaction() as tx:
            binding = await tx.fetchone(
                "SELECT * FROM nh1_s05_spike_bindings WHERE execution_uuid='rollback'"
            )
            outcome = await tx.fetchone(
                "SELECT * FROM nh1_s05_spike_outcomes WHERE execution_uuid='rollback'"
            )
        assert binding is not None and binding["actual_binding_state"] == "unsealed"
        assert binding["actual_binding_digest"] is None
        assert outcome is None
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_same_seal_replay(tmp_path: Path) -> None:
    persistence = await _persistence(tmp_path, "replay")
    domain = stable_digest({"binding": "domain"})
    actual = stable_digest({"binding": "actual"})
    route = stable_digest({"route": "selected"})
    try:
        async with persistence.transaction() as tx:
            await insert_actual_s05_sample(
                tx,
                execution_uuid="replay",
                domain_binding_digest=domain,
                state="unsealed",
            )
            first = await seal_actual_s05(
                tx,
                execution_uuid="replay",
                actual_binding_digest=actual,
                selected_route_digest=route,
            )
        async with persistence.transaction() as tx:
            replayed = await seal_actual_s05(
                tx,
                execution_uuid="replay",
                actual_binding_digest=actual,
                selected_route_digest=route,
            )
            count = await tx.fetchone("SELECT COUNT(*) AS count FROM nh1_s05_spike_outcomes")
        assert first["seal_generation"] == replayed["seal_generation"] == 1
        assert count == {"count": 1}
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_different_digest_conflict_error(tmp_path: Path) -> None:
    persistence = await _persistence(tmp_path, "conflict")
    domain = stable_digest({"binding": "domain"})
    route = stable_digest({"route": "selected"})
    try:
        async with persistence.transaction() as tx:
            await insert_actual_s05_sample(
                tx,
                execution_uuid="conflict",
                domain_binding_digest=domain,
                state="unsealed",
            )
            await seal_actual_s05(
                tx,
                execution_uuid="conflict",
                actual_binding_digest=stable_digest({"actual": 1}),
                selected_route_digest=route,
            )
        with pytest.raises(ConflictError) as raised:
            async with persistence.transaction() as tx:
                await seal_actual_s05(
                    tx,
                    execution_uuid="conflict",
                    actual_binding_digest=stable_digest({"actual": 2}),
                    selected_route_digest=route,
                )
        assert raised.value.status_code == 409
        assert raised.value.code == "ACTUAL_S05_SEAL_CONFLICT"
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_domain_hex_is_not_sealed_actual(tmp_path: Path) -> None:
    persistence = await _persistence(tmp_path, "domain-is-not-actual")
    domain = stable_digest({"binding": "domain"})
    try:
        async with persistence.transaction() as tx:
            await insert_actual_s05_sample(
                tx,
                execution_uuid="legacy",
                domain_binding_digest=domain,
                state="legacy_unverifiable",
            )
            legacy = await tx.fetchone(
                "SELECT * FROM nh1_s05_spike_bindings WHERE execution_uuid='legacy'"
            )
        assert legacy is not None
        assert legacy["legacy_policy_alias_digest"] == domain
        assert projected_actual_digest(legacy) is None
        with pytest.raises(ConflictError) as raised:
            async with persistence.transaction() as tx:
                await seal_actual_s05(
                    tx,
                    execution_uuid="legacy",
                    actual_binding_digest=domain,
                    selected_route_digest=stable_digest({"route": "legacy"}),
                )
        assert raised.value.code == "ACTUAL_S05_LEGACY_UNVERIFIABLE"
    finally:
        await persistence.close()
