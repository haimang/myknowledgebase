"""Idempotent NHX1 expand/backfill/validate/cutover progress authority."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from src.contracts.common.errors import ConflictError, MkbError
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.persistence.ports import PersistencePort


class MigrationStage(StrEnum):
    EXPAND = "expand"
    BACKFILL = "backfill"
    VALIDATE = "validate"
    CUTOVER = "cutover"
    CONTRACT = "contract"


class MigrationStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    BLOCKED = "blocked"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class MigrationProgress:
    migration_key: str
    stage: MigrationStage
    status: MigrationStatus
    cursor_value: str | None
    processed_count: int
    mismatch_count: int
    row_revision: int


class Nhx1MigrationService:
    def __init__(self, persistence: PersistencePort) -> None:
        self.persistence = persistence

    async def start_or_resume(self, migration_key: str, stage: MigrationStage) -> MigrationProgress:
        now = utc_now()
        async with self.persistence.transaction() as tx:
            await tx.execute(
                "INSERT OR IGNORE INTO mkb_nhx1_migration_state"
                "(migration_key,stage,status,started_at,updated_at) VALUES (?,?,'running',?,?)",
                (migration_key, stage.value, now, now),
            )
            row = await tx.fetchone("SELECT * FROM mkb_nhx1_migration_state WHERE migration_key=?", (migration_key,))
            if row is None:
                raise MkbError("NHX1_MIGRATION_STATE_MISSING", "Migration progress could not be read", 503)
            if row["stage"] != stage.value:
                raise ConflictError("NHX1_MIGRATION_STAGE_CONFLICT", "Migration stage conflicts with durable state")
        return self._progress(row)

    async def advance(
        self,
        migration_key: str,
        *,
        expected_revision: int,
        cursor_value: str | None,
        processed_delta: int,
        completed: bool = False,
    ) -> MigrationProgress:
        if processed_delta < 0:
            raise ValueError("processed_delta must be non-negative")
        now = utc_now()
        status = MigrationStatus.COMPLETED.value if completed else MigrationStatus.RUNNING.value
        async with self.persistence.transaction() as tx:
            updated = await tx.execute(
                "UPDATE mkb_nhx1_migration_state SET cursor_value=?,processed_count=processed_count+?,status=?,"
                "row_revision=row_revision+1,updated_at=?,completed_at=? "
                "WHERE migration_key=? AND row_revision=? AND status IN ('running','pending')",
                (
                    cursor_value,
                    processed_delta,
                    status,
                    now,
                    now if completed else None,
                    migration_key,
                    expected_revision,
                ),
            )
            if updated.rowcount != 1:
                raise ConflictError("NHX1_MIGRATION_FENCE_CONFLICT", "Migration progress changed")
            row = await tx.fetchone("SELECT * FROM mkb_nhx1_migration_state WHERE migration_key=?", (migration_key,))
        assert row is not None
        return self._progress(row)

    async def record_shadow_mismatch(
        self,
        migration_key: str,
        *,
        team_uuid: str | None,
        aggregate_kind: str,
        aggregate_uuid_hash: str,
        old_digest: str,
        new_digest: str,
        mismatch_kind: str,
    ) -> str:
        if old_digest == new_digest:
            raise ValueError("matching shadow digests are not mismatches")
        mismatch_uuid = uuid7()
        now = utc_now()
        async with self.persistence.transaction() as tx:
            state = await tx.fetchone(
                "SELECT status FROM mkb_nhx1_migration_state WHERE migration_key=?", (migration_key,)
            )
            if state is None:
                raise MkbError("NHX1_MIGRATION_STATE_MISSING", "Migration progress could not be read", 503)
            await tx.execute(
                "INSERT INTO mkb_nhx1_shadow_mismatches"
                "(mismatch_uuid,migration_key,team_uuid,aggregate_kind,aggregate_uuid_hash,old_digest,new_digest,"
                "mismatch_kind,observed_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    mismatch_uuid,
                    migration_key,
                    team_uuid,
                    aggregate_kind,
                    aggregate_uuid_hash,
                    old_digest,
                    new_digest,
                    mismatch_kind,
                    now,
                ),
            )
            await tx.execute(
                "UPDATE mkb_nhx1_migration_state SET mismatch_count=mismatch_count+1,status='blocked',"
                "row_revision=row_revision+1,updated_at=?,last_error_code='NHX1_SHADOW_MISMATCH' WHERE migration_key=?",
                (now, migration_key),
            )
        return mismatch_uuid

    async def snapshot(self, migration_key: str) -> tuple[MigrationProgress, int]:
        async with self.persistence.read_snapshot() as tx:
            row = await tx.fetchone("SELECT * FROM mkb_nhx1_migration_state WHERE migration_key=?", (migration_key,))
            mismatch = await tx.fetchone(
                "SELECT COUNT(*) AS count FROM mkb_nhx1_shadow_mismatches "
                "WHERE migration_key=? AND resolved_at IS NULL",
                (migration_key,),
            )
        if row is None or mismatch is None:
            raise MkbError("NHX1_MIGRATION_STATE_MISSING", "Migration progress could not be read", 503)
        return self._progress(row), int(mismatch["count"])

    @staticmethod
    def _progress(row: dict[str, Any]) -> MigrationProgress:
        return MigrationProgress(
            migration_key=str(row["migration_key"]),
            stage=MigrationStage(row["stage"]),
            status=MigrationStatus(row["status"]),
            cursor_value=None if row["cursor_value"] is None else str(row["cursor_value"]),
            processed_count=int(row["processed_count"]),
            mismatch_count=int(row["mismatch_count"]),
            row_revision=int(row["row_revision"]),
        )
