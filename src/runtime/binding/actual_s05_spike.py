"""SPIKE-ONLY actual-S05 sealed-once slice for AP-NH1.

The helper installs test-session tables only.  AP-NH3 owns the forward-only
production migration and the complete Execution propagation chain.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from src.contracts.common.errors import ConflictError, MkbError
from src.persistence.ports import UnitOfWork

ActualBindingState = Literal["legacy_unverifiable", "unsealed", "sealed"]


async def install_actual_s05_spike(tx: UnitOfWork) -> None:
    await tx.execute(
        "CREATE TABLE IF NOT EXISTS nh1_s05_spike_bindings ("
        "execution_uuid TEXT PRIMARY KEY,"
        "domain_binding_digest TEXT NOT NULL,"
        "legacy_policy_alias_digest TEXT,"
        "actual_binding_digest TEXT,"
        "actual_binding_state TEXT NOT NULL "
        "CHECK(actual_binding_state IN ('legacy_unverifiable','unsealed','sealed')),"
        "seal_generation INTEGER NOT NULL DEFAULT 0 CHECK(seal_generation >= 0),"
        "CHECK((actual_binding_state='sealed' AND actual_binding_digest IS NOT NULL AND seal_generation >= 1) "
        "OR (actual_binding_state<>'sealed' AND actual_binding_digest IS NULL AND seal_generation=0))"
        ")"
    )
    await tx.execute(
        "CREATE TABLE IF NOT EXISTS nh1_s05_spike_outcomes ("
        "execution_uuid TEXT PRIMARY KEY,"
        "selected_route_digest TEXT NOT NULL,"
        "actual_binding_digest TEXT NOT NULL,"
        "FOREIGN KEY(execution_uuid) REFERENCES nh1_s05_spike_bindings(execution_uuid)"
        ")"
    )


async def insert_actual_s05_sample(
    tx: UnitOfWork,
    *,
    execution_uuid: str,
    domain_binding_digest: str,
    state: ActualBindingState,
    actual_binding_digest: str | None = None,
) -> None:
    if state == "sealed" and not _is_digest(actual_binding_digest):
        raise ValueError("sealed samples require an actual binding digest")
    if state != "sealed" and actual_binding_digest is not None:
        raise ValueError("non-sealed samples cannot carry an actual binding digest")
    await tx.execute(
        "INSERT INTO nh1_s05_spike_bindings("
        "execution_uuid,domain_binding_digest,legacy_policy_alias_digest,actual_binding_digest,"
        "actual_binding_state,seal_generation) VALUES (?,?,?,?,?,?)",
        (
            execution_uuid,
            domain_binding_digest,
            domain_binding_digest if state == "legacy_unverifiable" else None,
            actual_binding_digest,
            state,
            1 if state == "sealed" else 0,
        ),
    )


async def seal_actual_s05(
    tx: UnitOfWork,
    *,
    execution_uuid: str,
    actual_binding_digest: str,
    selected_route_digest: str,
) -> dict[str, Any]:
    """Commit route outcome and actual CAS in the caller's one UoW."""

    if not _is_digest(actual_binding_digest) or not _is_digest(selected_route_digest):
        raise MkbError("ACTUAL_S05_SEAL_INVALID", "Actual S05 seal digests are invalid", 422)
    row = await tx.fetchone(
        "SELECT * FROM nh1_s05_spike_bindings WHERE execution_uuid=?",
        (execution_uuid,),
    )
    if row is None:
        raise MkbError("ACTUAL_S05_EXECUTION_MISSING", "Actual S05 spike execution is missing", 404)
    state = row["actual_binding_state"]
    if state == "legacy_unverifiable":
        raise ConflictError("ACTUAL_S05_LEGACY_UNVERIFIABLE", "Legacy policy aliases cannot be sealed as actual")
    if state == "sealed":
        outcome = await tx.fetchone(
            "SELECT selected_route_digest FROM nh1_s05_spike_outcomes WHERE execution_uuid=?",
            (execution_uuid,),
        )
        if row["actual_binding_digest"] == actual_binding_digest and outcome is not None and outcome[
            "selected_route_digest"
        ] == selected_route_digest:
            return row
        raise ConflictError("ACTUAL_S05_SEAL_CONFLICT", "Execution already carries a different actual S05 seal")

    result = await tx.execute(
        "UPDATE nh1_s05_spike_bindings SET actual_binding_digest=?,actual_binding_state='sealed',"
        "seal_generation=1 WHERE execution_uuid=? AND actual_binding_state='unsealed' "
        "AND actual_binding_digest IS NULL AND seal_generation=0",
        (actual_binding_digest, execution_uuid),
    )
    if getattr(result, "rowcount", 0) != 1:
        raise ConflictError("ACTUAL_S05_SEAL_CONFLICT", "Actual S05 seal lost its compare-and-swap fence")
    await tx.execute(
        "INSERT INTO nh1_s05_spike_outcomes(execution_uuid,selected_route_digest,actual_binding_digest) "
        "VALUES (?,?,?)",
        (execution_uuid, selected_route_digest, actual_binding_digest),
    )
    sealed = await tx.fetchone(
        "SELECT * FROM nh1_s05_spike_bindings WHERE execution_uuid=?",
        (execution_uuid,),
    )
    assert sealed is not None
    return sealed


def projected_actual_digest(row: Mapping[str, Any]) -> str | None:
    """Expose actual only after an explicit sealed state; never infer from hex shape."""

    if row.get("actual_binding_state") != "sealed":
        return None
    value = row.get("actual_binding_digest")
    return value if _is_digest(value) else None


def _is_digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


__all__ = [
    "install_actual_s05_spike",
    "insert_actual_s05_sample",
    "projected_actual_digest",
    "seal_actual_s05",
]
