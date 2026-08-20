"""Generation-scoped S08 logical vector purge.

This service deliberately owns only ``mkb_vector_records.deleted_at``.  It
does not delete generation artifacts, change an Intake lifecycle, alter an
index pointer, or drop a namespace.  Those concerns are intentionally fenced
in S04/S09/S15 respectively.
"""

from __future__ import annotations

from src.contracts.common.errors import MkbError
from src.contracts.common.time import utc_now
from src.contracts.vector.models import VectorizeCommand, VectorizePurgeReceiptV1
from src.persistence.ports import PersistencePort, UnitOfWork


class VectorGenerationPurger:
    """Plan and execute one frozen ``purge_generation`` command.

    Planning happens before the process output is promoted.  The callback
    repeats the target and active-set checks in its outcome transaction, so a
    concurrent change cannot turn a stale planned receipt into a success.
    """

    def __init__(self, persistence: PersistencePort) -> None:
        self._persistence = persistence

    async def plan(self, command: VectorizeCommand) -> VectorizePurgeReceiptV1:
        self._assert_purge_command(command)
        async with self._persistence.transaction() as tx:
            await self._assert_targets_tx(tx, command)
            matched = await self._active_count_tx(tx, command)
        return self._receipt(command, matched)

    async def purge_tx(
        self,
        tx: UnitOfWork,
        command: VectorizeCommand,
        *,
        expected: VectorizePurgeReceiptV1,
    ) -> VectorizePurgeReceiptV1:
        """Soft-delete exactly the command target set under the Process fence."""

        self._assert_purge_command(command)
        if (
            expected.team_uuid != command.team_uuid
            or expected.execution_uuid != command.execution_uuid
            or expected.command_input_digest != command.command_input_digest
            or expected.target_generation_artifact_uuids != command.target_generation_artifact_uuids
            or expected.channel_filter != command.channel_filter
        ):
            raise MkbError("PURGE_RECEIPT_BINDING_INVALID", "Purge receipt does not bind the frozen command", 409)
        await self._assert_targets_tx(tx, command)
        matched = await self._active_count_tx(tx, command)
        if matched != expected.matched_records:
            raise MkbError("PURGE_REQUIRED_SET_CHANGED", "Purge target changed after its receipt was planned", 409)
        where, params = self._active_where(command)
        changed = await tx.execute(
            "UPDATE mkb_vector_records SET deleted_at=?,updated_at=? " + where,
            (utc_now(), utc_now(), *params),
        )
        soft_deleted = max(int(changed.rowcount), 0)
        if soft_deleted != matched:
            raise MkbError("PURGE_REQUIRED_SET_CHANGED", "Purge target changed during its fenced soft-delete", 409)
        return self._receipt(command, soft_deleted)

    @staticmethod
    def _assert_purge_command(command: VectorizeCommand) -> None:
        if command.mode != "purge_generation":
            raise MkbError("PURGE_COMMAND_INVALID", "Vector purge service accepts only purge_generation commands", 422)
        if command.channel_filter != "all":
            raise MkbError(
                "PURGE_CHANNEL_FILTER_UNSUPPORTED",
                "Partial-channel purge would break the publication proof",
                422,
            )

    async def _assert_targets_tx(self, tx: UnitOfWork, command: VectorizeCommand) -> None:
        placeholders = ",".join("?" for _ in command.target_generation_artifact_uuids)
        rows = await tx.fetchall(
            "SELECT generation_artifact_uuid FROM mkb_generation_artifacts "
            "WHERE team_uuid=? AND artifact_type='dual_channel_projection' "
            "AND validation_disposition='full_valid' "
            f"AND generation_artifact_uuid IN ({placeholders}) ORDER BY generation_artifact_uuid",
            (command.team_uuid, *command.target_generation_artifact_uuids),
        )
        actual = [str(row["generation_artifact_uuid"]) for row in rows]
        if actual != command.target_generation_artifact_uuids:
            raise MkbError("PURGE_TARGET_NOT_FOUND", "Purge target is not a full-valid dual-channel generation", 409)

    @staticmethod
    def _active_where(command: VectorizeCommand) -> tuple[str, tuple[str, ...]]:
        placeholders = ",".join("?" for _ in command.target_generation_artifact_uuids)
        where = "WHERE team_uuid=? AND deleted_at IS NULL " f"AND generation_artifact_uuid IN ({placeholders})"
        params: tuple[str, ...] = (command.team_uuid, *command.target_generation_artifact_uuids)
        if command.channel_filter != "all":
            where += " AND channel=?"
            params += (command.channel_filter,)
        return where, params

    async def _active_count_tx(self, tx: UnitOfWork, command: VectorizeCommand) -> int:
        where, params = self._active_where(command)
        row = await tx.fetchone("SELECT COUNT(*) AS count FROM mkb_vector_records " + where, params)
        return 0 if row is None else int(row["count"])

    @staticmethod
    def _receipt(command: VectorizeCommand, matched: int) -> VectorizePurgeReceiptV1:
        return VectorizePurgeReceiptV1(
            team_uuid=command.team_uuid,
            execution_uuid=command.execution_uuid,
            command_input_digest=command.command_input_digest,
            target_generation_artifact_uuids=command.target_generation_artifact_uuids,
            channel_filter=command.channel_filter,
            matched_records=matched,
            soft_deleted_records=matched,
        )


__all__ = ["VectorGenerationPurger"]
