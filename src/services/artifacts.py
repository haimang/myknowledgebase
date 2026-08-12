"""Bytes-first stage artifact commit bridge (S12 TX-05 / S13).

Stage handlers promote immutable bytes before their Process outcome is accepted.
This module retains only bounded in-memory *pending commit descriptors*; the
catalog rows, object references, and domain-specific callback are written by
the workflow runtime in the very same UoW as the Process success CAS.  A crash
between promotion and that UoW leaves unreferenced bytes, which is the intended
S13 orphan-GC case rather than a false business success.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from src.contracts.common.errors import ConflictError, MkbError
from src.contracts.common.ids import uuid7
from src.contracts.runtime.models import ProcessCommand, ProcessOutcome
from src.contracts.storage.models import ObjectStat, PromoteRequest
from src.persistence.ports import UnitOfWork
from src.storage.ports import ObjectStorePort

StageCommitCallback = Callable[[UnitOfWork], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class StagedArtifacts:
    """Opaque references a handler can safely put in a ProcessOutcome."""

    output_ref: str
    output_digest: str
    proof_ref: str
    proof_digest: str


@dataclass(slots=True)
class _PendingCommit:
    command: ProcessCommand
    output: ObjectStat
    proof: ObjectStat
    callback: StageCommitCallback


class OutcomeArtifactCommitter:
    """An S03 outcome-commit port backed by S13 local CAS and catalog tables."""

    def __init__(self, storage: ObjectStorePort) -> None:
        self._storage = storage
        self._pending: dict[tuple[str, int], _PendingCommit] = {}

    async def stage(
        self,
        command: ProcessCommand,
        *,
        output_bytes: bytes,
        proof_bytes: bytes,
        output_media_type: str = "application/json",
        proof_media_type: str = "application/json",
        callback: StageCommitCallback,
    ) -> StagedArtifacts:
        """Promote bytes now and defer catalog/domain rows until outcome CAS."""

        output = await self._storage.promote(
            output_bytes,
            PromoteRequest(team_uuid=command.team_uuid, purpose="process_io", media_type=output_media_type),
        )
        proof = await self._storage.promote(
            proof_bytes,
            PromoteRequest(team_uuid=command.team_uuid, purpose="process_io", media_type=proof_media_type),
        )
        key = (command.process_uuid, command.fencing_generation)
        existing = self._pending.get(key)
        if existing is not None:
            if (
                existing.output.sha256 != output.sha256
                or existing.proof.sha256 != proof.sha256
                or existing.command.execution_uuid != command.execution_uuid
            ):
                raise ConflictError("stage-output-conflict", "A process fence already staged different output bytes")
        else:
            self._pending[key] = _PendingCommit(command=command, output=output, proof=proof, callback=callback)
        return StagedArtifacts(
            output_ref=output.handle.value,
            output_digest=output.sha256,
            proof_ref=proof.handle.value,
            proof_digest=proof.sha256,
        )

    async def validate_and_commit(self, tx: UnitOfWork, command: ProcessCommand, outcome: ProcessOutcome) -> None:
        """Runtime hook: validate opaque refs, catalog them, then run domain TX."""

        pending = self._pending.get((command.process_uuid, command.fencing_generation))
        if pending is None:
            raise MkbError(
                "OBJECT_PENDING_OUTPUT_MISSING", "Promoted stage output is unavailable for outcome commit", 409
            )
        if pending.command != command:
            raise ConflictError("stage-command-conflict", "Staged bytes do not belong to this Process command")
        if (
            outcome.output_manifest_ref != pending.output.handle.value
            or outcome.output_manifest_digest != pending.output.sha256
            or outcome.proof_ref != pending.proof.handle.value
            or outcome.proof_digest != pending.proof.sha256
        ):
            raise ConflictError("stage-output-integrity", "Process outcome does not match staged CAS bytes")
        await self._catalog_stat(
            tx,
            team_uuid=command.team_uuid,
            stat=pending.output,
            owner_kind="process_output",
            owner_uuid=command.process_uuid,
        )
        await self._catalog_stat(
            tx,
            team_uuid=command.team_uuid,
            stat=pending.proof,
            owner_kind="process_proof",
            owner_uuid=command.process_uuid,
        )
        await pending.callback(tx)

    async def _catalog_stat(
        self,
        tx: UnitOfWork,
        *,
        team_uuid: str,
        stat: ObjectStat,
        owner_kind: str,
        owner_uuid: str,
    ) -> None:
        existing = await tx.fetchone(
            "SELECT stored_object_uuid FROM mkb_stored_objects WHERE team_uuid=? AND content_digest=? AND size_bytes=?",
            (team_uuid, stat.sha256, stat.size_bytes),
        )
        if existing is None:
            stored_object_uuid = uuid7()
            await tx.execute(
                "INSERT INTO mkb_stored_objects "
                "(stored_object_uuid,team_uuid,digest_algorithm,content_digest,size_bytes,media_type,storage_backend,"
                "created_at,payload_extra) VALUES (?,?, 'sha256',?,?,?,?,strftime('%Y-%m-%dT%H:%M:%fZ','now'),'{}')",
                (stored_object_uuid, team_uuid, stat.sha256, stat.size_bytes, stat.media_type, "local_fs"),
            )
        else:
            stored_object_uuid = existing["stored_object_uuid"]
        await tx.execute(
            "INSERT INTO mkb_object_references "
            "(reference_uuid,team_uuid,stored_object_uuid,purpose,owner_kind,owner_uuid,expected_digest,expected_size,"
            "created_at,payload_extra) VALUES (?,?,?,'process_io',?,?,?,?,strftime('%Y-%m-%dT%H:%M:%fZ','now'),'{}')",
            (uuid7(), team_uuid, stored_object_uuid, owner_kind, owner_uuid, stat.sha256, stat.size_bytes),
        )


__all__ = ["OutcomeArtifactCommitter", "StagedArtifacts", "StageCommitCallback"]
