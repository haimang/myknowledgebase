"""Durable NHX1 shadow/cutover, drain inventory, and forward rollback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.contracts.common.errors import ConflictError, MkbError
from src.contracts.common.ids import stable_digest
from src.contracts.common.time import utc_now
from src.persistence.nhx1_migration import Nhx1MigrationService
from src.persistence.ports import PersistencePort


@dataclass(frozen=True, slots=True)
class CutoverState:
    cutover_key: str
    writer_mode: str
    reader_mode: str
    admission_enabled: bool
    expected_migration_revision: int
    row_revision: int


class Nhx1CutoverService:
    """Own the one-way v2 writer transition; legacy rows remain readable."""

    def __init__(self, persistence: PersistencePort) -> None:
        self._persistence = persistence
        self._migration = Nhx1MigrationService(persistence)

    async def ensure_state(self, cutover_key: str = "nhx1") -> CutoverState:
        now = utc_now()
        async with self._persistence.transaction() as tx:
            await tx.execute(
                "INSERT OR IGNORE INTO mkb_nhx1_cutover_state(cutover_key,writer_mode,reader_mode,admission_enabled,"
                "expected_migration_revision,updated_at) VALUES (?,'legacy','legacy',1,0,?)",
                (cutover_key, now),
            )
            row = await tx.fetchone("SELECT * FROM mkb_nhx1_cutover_state WHERE cutover_key=?", (cutover_key,))
        if row is None:
            raise MkbError("NHX1_CUTOVER_STATE_MISSING", "Cutover state is unavailable", 503)
        return self._state(row)

    async def begin_shadow(self, cutover_key: str = "nhx1") -> CutoverState:
        state = await self.ensure_state(cutover_key)
        async with self._persistence.transaction() as tx:
            now = utc_now()
            updated = await tx.execute(
                "UPDATE mkb_nhx1_cutover_state SET writer_mode='dual',reader_mode='shadow',row_revision=row_revision+1,"
                "updated_at=? WHERE cutover_key=? AND row_revision=? AND writer_mode='legacy'",
                (now, cutover_key, state.row_revision),
            )
            if updated.rowcount != 1:
                raise ConflictError("NHX1_CUTOVER_FENCE_CONFLICT", "Cutover state changed before shadow start")
            row = await tx.fetchone("SELECT * FROM mkb_nhx1_cutover_state WHERE cutover_key=?", (cutover_key,))
        assert row is not None
        return self._state(row)

    async def cutover(self, *, cutover_key: str = "nhx1", expected_revision: int) -> CutoverState:
        state = await self.ensure_state(cutover_key)
        if state.row_revision != expected_revision:
            raise ConflictError("NHX1_CUTOVER_FENCE_CONFLICT", "Cutover state revision is stale")
        async with self._persistence.read_snapshot() as tx:
            mismatch = await tx.fetchone(
                "SELECT COUNT(*) AS count FROM mkb_nhx1_shadow_mismatches WHERE resolved_at IS NULL"
            )
        if mismatch is None or int(mismatch["count"]) != 0:
            raise MkbError("NHX1_SHADOW_MISMATCH", "Shadow mismatch blocks v2 cutover", 503)
        if state.writer_mode not in {"legacy", "dual"}:
            if state.writer_mode == "v2_only":
                return state
            raise MkbError("NHX1_CUTOVER_STATE_INVALID", "Cutover writer state is invalid", 503)
        async with self._persistence.transaction() as tx:
            now = utc_now()
            updated = await tx.execute(
                "UPDATE mkb_nhx1_cutover_state SET writer_mode='v2_only',reader_mode='v2',row_revision=row_revision+1,"
                "updated_at=? WHERE cutover_key=? AND row_revision=? AND admission_enabled=1",
                (now, cutover_key, expected_revision),
            )
            if updated.rowcount != 1:
                raise ConflictError("NHX1_CUTOVER_FENCE_CONFLICT", "Cutover changed before v2 activation")
            row = await tx.fetchone("SELECT * FROM mkb_nhx1_cutover_state WHERE cutover_key=?", (cutover_key,))
        assert row is not None
        return self._state(row)

    async def stop_admission(self, *, cutover_key: str = "nhx1", expected_revision: int) -> CutoverState:
        """Forward rollback primitive: stop new admission, never revive legacy writer."""

        state = await self.ensure_state(cutover_key)
        if state.row_revision != expected_revision:
            raise ConflictError("NHX1_CUTOVER_FENCE_CONFLICT", "Cutover state revision is stale")
        async with self._persistence.transaction() as tx:
            now = utc_now()
            updated = await tx.execute(
                "UPDATE mkb_nhx1_cutover_state SET admission_enabled=0,row_revision=row_revision+1,updated_at=? "
                "WHERE cutover_key=? AND row_revision=? AND admission_enabled=1",
                (now, cutover_key, expected_revision),
            )
            if updated.rowcount != 1:
                raise ConflictError("NHX1_CUTOVER_FENCE_CONFLICT", "Admission state changed before stop")
            row = await tx.fetchone("SELECT * FROM mkb_nhx1_cutover_state WHERE cutover_key=?", (cutover_key,))
        assert row is not None
        return self._state(row)

    @staticmethod
    def assert_writer_allowed(state: CutoverState, writer: str) -> None:
        if writer == "v2" and state.writer_mode == "v2_only":
            return
        if writer == "legacy" and state.writer_mode == "legacy":
            return
        raise MkbError("NHX1_LEGACY_WRITER_DISABLED", "The requested writer is disabled by cutover", 409)

    async def resolve_shadow_mismatch(self, mismatch_uuid: str, *, resolution_code: str) -> None:
        if not resolution_code or len(resolution_code) > 128:
            raise ValueError("resolution_code is invalid")
        async with self._persistence.transaction() as tx:
            updated = await tx.execute(
                "UPDATE mkb_nhx1_shadow_mismatches SET resolved_at=?,resolution_code=? "
                "WHERE mismatch_uuid=? AND resolved_at IS NULL",
                (utc_now(), resolution_code, mismatch_uuid),
            )
            if updated.rowcount != 1:
                raise MkbError("NHX1_SHADOW_MISMATCH_NOT_FOUND", "Shadow mismatch is unavailable", 404)

    async def inventory(self) -> dict[str, int]:
        async with self._persistence.read_snapshot() as tx:
            queries = {
                "rev1_pins": "SELECT COUNT(*) AS count FROM mkb_executions e JOIN mkb_workflow_revisions r ON r.workflow_revision_uuid=e.workflow_revision_uuid WHERE r.revision_number=1 AND e.status NOT IN ('succeeded','failed','cancelled')",
                "pending_outbox": "SELECT COUNT(*) AS count FROM mkb_outbox WHERE status IN ('pending','in_flight')",
                "open_restarts": "SELECT COUNT(*) AS count FROM mkb_task_restarts WHERE admission_outcome='accepted' AND decided_at IS NULL",
                "live_object_refs": "SELECT COUNT(*) AS count FROM mkb_object_references WHERE released_at IS NULL",
                "open_cleanup_jobs": "SELECT COUNT(*) AS count FROM mkb_cleanup_jobs WHERE state NOT IN ('completed','cancelled')",
                "legacy_evidence": "SELECT COUNT(*) AS count FROM mkb_evidence_verifications WHERE verdict='legacy_unverifiable'",
                "unresolved_shadow": "SELECT COUNT(*) AS count FROM mkb_nhx1_shadow_mismatches WHERE resolved_at IS NULL",
            }
            result: dict[str, int] = {}
            for key, sql in queries.items():
                row = await tx.fetchone(sql)
                result[key] = int(row["count"]) if row is not None else 0
        return result

    async def retire_legacy(self, *, cutover_key: str = "nhx1", expected_revision: int) -> CutoverState:
        state = await self.ensure_state(cutover_key)
        if state.row_revision != expected_revision:
            raise ConflictError("NHX1_CUTOVER_FENCE_CONFLICT", "Cutover state revision is stale")
        if state.writer_mode != "v2_only" or state.reader_mode != "v2":
            raise MkbError("NHX1_RETIREMENT_NOT_CUTOVER", "Legacy retirement requires v2 cutover", 409)
        inventory = await self.inventory()
        if any(value for key, value in inventory.items() if key != "legacy_evidence"):
            raise MkbError("NHX1_RETIREMENT_BLOCKED", "Legacy retirement inventory is not empty", 409, inventory)
        async with self._persistence.transaction() as tx:
            now = utc_now()
            updated = await tx.execute(
                "UPDATE mkb_nhx1_cutover_state SET row_revision=row_revision+1,updated_at=?,payload_extra=? "
                "WHERE cutover_key=? AND row_revision=? AND writer_mode='v2_only'",
                (now, stable_digest({"retired": True, "at": now}), cutover_key, expected_revision),
            )
            if updated.rowcount != 1:
                raise ConflictError("NHX1_CUTOVER_FENCE_CONFLICT", "Legacy retirement changed before commit")
            row = await tx.fetchone("SELECT * FROM mkb_nhx1_cutover_state WHERE cutover_key=?", (cutover_key,))
        assert row is not None
        return self._state(row)

    @staticmethod
    def _state(row: dict[str, Any]) -> CutoverState:
        return CutoverState(
            cutover_key=str(row["cutover_key"]),
            writer_mode=str(row["writer_mode"]),
            reader_mode=str(row["reader_mode"]),
            admission_enabled=bool(row["admission_enabled"]),
            expected_migration_revision=int(row["expected_migration_revision"]),
            row_revision=int(row["row_revision"]),
        )


__all__ = ["CutoverState", "Nhx1CutoverService"]
