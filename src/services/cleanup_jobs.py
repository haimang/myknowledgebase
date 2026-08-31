"""Durable, idempotent physical-convergence executors for deleted Items."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from src.contracts.common.errors import ConflictError, MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.persistence.ports import PersistencePort, UnitOfWork


@dataclass(frozen=True, slots=True)
class CleanupStepResult:
    substrate_kind: str
    state: str
    proof_uuid: str | None
    blocked_reason: str | None = None


@dataclass(frozen=True, slots=True)
class CleanupRunResult:
    cleanup_job_uuid: str
    state: str
    steps: tuple[CleanupStepResult, ...]


class CleanupJobService:
    """Run one frozen Item owner graph to terminal per-substrate proofs."""

    _SUBSTRATES = ("intake_artifact", "derived_generation", "vector_projection", "object_reference", "object_gc")

    def __init__(self, persistence: PersistencePort, *, retention: timedelta = timedelta(hours=24)) -> None:
        if retention <= timedelta(0):
            raise ValueError("cleanup retention must be greater than zero")
        self._persistence = persistence
        self._retention = retention

    async def ensure_for_item(
        self,
        *,
        team_uuid: str,
        intake_item_uuid: str,
        intent_uuid: str,
        item_epoch: int,
        required_substrate_set_digest: str,
        retention_until: str | None = None,
    ) -> str:
        now = utc_now()
        retention = retention_until or self._retention_timestamp()
        async with self._persistence.transaction() as tx:
            existing = await tx.fetchone(
                "SELECT cleanup_job_uuid FROM mkb_cleanup_jobs WHERE intent_uuid=?", (intent_uuid,)
            )
            if existing is not None:
                return str(existing["cleanup_job_uuid"])
            refs = await tx.fetchall(
                "SELECT purpose,owner_kind,owner_uuid,expected_digest,expected_size FROM mkb_object_references "
                "WHERE team_uuid=? AND owner_uuid IN (?,?) AND released_at IS NULL ORDER BY reference_uuid",
                (team_uuid, intake_item_uuid, intake_item_uuid),
            )
            owner_graph_digest = stable_digest(
                {
                    "team_uuid": team_uuid,
                    "intake_item_uuid": intake_item_uuid,
                    "item_epoch": item_epoch,
                    "refs": refs,
                    "substrates": self._SUBSTRATES,
                }
            )
            job_uuid = uuid7()
            await tx.execute(
                "INSERT INTO mkb_cleanup_jobs(cleanup_job_uuid,intent_uuid,team_uuid,intake_item_uuid,item_epoch,"
                "owner_graph_digest,required_substrate_set_digest,retention_until,state,created_at,updated_at,payload_extra) "
                "VALUES (?,?,?,?,?,?,?,?,'pending',?,?, '{}')",
                (
                    job_uuid,
                    intent_uuid,
                    team_uuid,
                    intake_item_uuid,
                    item_epoch,
                    owner_graph_digest,
                    required_substrate_set_digest,
                    retention,
                    now,
                    now,
                ),
            )
            for ordinal, substrate in enumerate(self._SUBSTRATES, start=1):
                await tx.execute(
                    "INSERT INTO mkb_cleanup_job_steps(cleanup_step_uuid,cleanup_job_uuid,team_uuid,substrate_kind,"
                    "ordinal,target_set_digest,state,available_at,payload_extra) VALUES (?,?,?,?,?,?,'pending',?,'{}')",
                    (uuid7(), job_uuid, team_uuid, substrate, ordinal, owner_graph_digest, now),
                )
        return job_uuid

    async def run_once(self, *, limit: int = 20) -> tuple[CleanupRunResult, ...]:
        if limit < 1 or limit > 1000:
            raise ValueError("cleanup batch limit is invalid")
        async with self._persistence.read_snapshot() as tx:
            jobs = await tx.fetchall(
                "SELECT * FROM mkb_cleanup_jobs WHERE state IN ('pending','failed','blocked') "
                "AND retention_until<=? ORDER BY created_at,cleanup_job_uuid LIMIT ?",
                (utc_now(), limit),
            )
        results: list[CleanupRunResult] = []
        for job in jobs:
            results.append(await self._run_job(dict(job)))
        return tuple(results)

    async def status(self, team_uuid: str, cleanup_job_uuid: str) -> dict[str, Any]:
        async with self._persistence.read_snapshot() as tx:
            job = await tx.fetchone(
                "SELECT * FROM mkb_cleanup_jobs WHERE team_uuid=? AND cleanup_job_uuid=?",
                (team_uuid, cleanup_job_uuid),
            )
            steps = await tx.fetchall(
                "SELECT substrate_kind,state,proof_uuid,blocked_reason FROM mkb_cleanup_job_steps "
                "WHERE cleanup_job_uuid=? ORDER BY ordinal",
                (cleanup_job_uuid,),
            )
        if job is None:
            raise MkbError("CLEANUP_JOB_NOT_FOUND", "Cleanup job was not found", 404)
        return {"job": job, "steps": steps}

    async def _run_job(self, job: dict[str, Any]) -> CleanupRunResult:
        now = utc_now()
        async with self._persistence.transaction() as tx:
            changed = await tx.execute(
                "UPDATE mkb_cleanup_jobs SET state='running',row_revision=row_revision+1,updated_at=? "
                "WHERE cleanup_job_uuid=? AND state IN ('pending','failed','blocked')",
                (now, job["cleanup_job_uuid"]),
            )
            if changed.rowcount != 1:
                raise ConflictError("CLEANUP_JOB_FENCE", "Cleanup job changed before execution")
            steps = await tx.fetchall(
                "SELECT * FROM mkb_cleanup_job_steps WHERE cleanup_job_uuid=? ORDER BY ordinal",
                (job["cleanup_job_uuid"],),
            )
            results: list[CleanupStepResult] = []
            blocked = False
            for step in steps:
                if step["state"] == "completed":
                    results.append(CleanupStepResult(step["substrate_kind"], "completed", step["proof_uuid"]))
                    continue
                result = await self._run_step_tx(tx, job, dict(step))
                results.append(result)
                blocked = blocked or result.state == "blocked"
                if result.state == "blocked":
                    break
            if blocked:
                await tx.execute(
                    "UPDATE mkb_cleanup_jobs SET state='blocked',blocked_reason=?,row_revision=row_revision+1,updated_at=? "
                    "WHERE cleanup_job_uuid=?",
                    (next((item.blocked_reason for item in results if item.blocked_reason), "hold"), now, job["cleanup_job_uuid"]),
                )
                state = "blocked"
            elif len(results) == len(steps) and all(item.state == "completed" for item in results):
                await tx.execute(
                    "UPDATE mkb_cleanup_jobs SET state='completed',completed_at=?,row_revision=row_revision+1,updated_at=? "
                    "WHERE cleanup_job_uuid=?",
                    (now, now, job["cleanup_job_uuid"]),
                )
                await tx.execute(
                    "UPDATE mkb_intake_cleanup_intents SET status='completed',completed_at=? WHERE intent_uuid=? AND status='open'",
                    (now, job["intent_uuid"]),
                )
                state = "completed"
            else:
                state = "failed"
                await tx.execute(
                    "UPDATE mkb_cleanup_jobs SET state='failed',row_revision=row_revision+1,updated_at=? "
                    "WHERE cleanup_job_uuid=?",
                    (now, job["cleanup_job_uuid"]),
                )
        return CleanupRunResult(job["cleanup_job_uuid"], state, tuple(results))

    async def _run_step_tx(
        self, tx: UnitOfWork, job: dict[str, Any], step: dict[str, Any]
    ) -> CleanupStepResult:
        substrate = str(step["substrate_kind"])
        if substrate == "object_reference":
            holds = await tx.fetchone(
                "SELECT COUNT(*) AS count FROM mkb_object_references WHERE team_uuid=? AND released_at IS NULL "
                "AND purpose IN ('operator_hold','backup_hold') AND owner_uuid=?",
                (job["team_uuid"], job["intake_item_uuid"]),
            )
            if holds is not None and int(holds["count"]) > 0:
                return await self._block_step_tx(tx, step, "cleanup_hold_active")
            await tx.execute(
                "UPDATE mkb_object_references SET released_at=? WHERE team_uuid=? AND owner_uuid=? "
                "AND released_at IS NULL AND purpose NOT IN ('operator_hold','backup_hold')",
                (utc_now(), job["team_uuid"], job["intake_item_uuid"]),
            )
        elif substrate == "intake_artifact":
            await tx.execute(
                "UPDATE mkb_object_references SET released_at=? WHERE team_uuid=? AND released_at IS NULL "
                "AND owner_uuid IN (SELECT intake_snapshot_uuid FROM mkb_intake_snapshot_memberships "
                "WHERE team_uuid=? AND intake_item_uuid=?)",
                (utc_now(), job["team_uuid"], job["team_uuid"], job["intake_item_uuid"]),
            )
        elif substrate == "vector_projection":
            await tx.execute(
                "UPDATE mkb_vector_records SET publication_state='withdrawn',deleted_at=COALESCE(deleted_at,?),updated_at=? "
                "WHERE team_uuid=? AND intake_item_uuid=?",
                (utc_now(), utc_now(), job["team_uuid"], job["intake_item_uuid"]),
            )
        elif substrate == "derived_generation":
            await tx.execute(
                "UPDATE mkb_object_references SET released_at=? WHERE team_uuid=? AND released_at IS NULL "
                "AND owner_kind='generation_artifact' AND owner_uuid IN "
                "(SELECT generation_artifact_uuid FROM mkb_generation_artifacts WHERE team_uuid=? AND intake_item_uuid=?)",
                (utc_now(), job["team_uuid"], job["team_uuid"], job["intake_item_uuid"]),
            )
        elif substrate == "object_gc":
            pass
        proof_uuid = uuid7()
        digest = stable_digest(
            {
                "cleanup_job_uuid": job["cleanup_job_uuid"],
                "substrate_kind": substrate,
                "target_set_digest": step["target_set_digest"],
            }
        )
        await tx.execute(
            "INSERT INTO mkb_intake_cleanup_proofs(proof_uuid,intent_uuid,team_uuid,substrate_kind,target_ref,"
            "target_digest,proof_kind,proof_digest,verified_at,payload_extra) VALUES (?,?,?,?,?,?,?,?,?,'{}')",
            (
                proof_uuid,
                job["intent_uuid"],
                job["team_uuid"],
                substrate,
                f"intake_item:{job['intake_item_uuid']}",
                step["target_set_digest"],
                "nhx1.cleanup.v1",
                digest,
                utc_now(),
            ),
        )
        await tx.execute(
            "UPDATE mkb_cleanup_job_steps SET state='completed',proof_uuid=?,terminal_at=?,row_revision=row_revision+1 "
            "WHERE cleanup_step_uuid=? AND state IN ('pending','failed','blocked')",
            (proof_uuid, utc_now(), step["cleanup_step_uuid"]),
        )
        return CleanupStepResult(substrate, "completed", proof_uuid)

    @staticmethod
    async def _block_step_tx(tx: UnitOfWork, step: dict[str, Any], reason: str) -> CleanupStepResult:
        await tx.execute(
            "UPDATE mkb_cleanup_job_steps SET state='blocked',blocked_reason=?,row_revision=row_revision+1 "
            "WHERE cleanup_step_uuid=? AND state IN ('pending','failed')",
            (reason, step["cleanup_step_uuid"]),
        )
        return CleanupStepResult(step["substrate_kind"], "blocked", None, reason)

    @staticmethod
    def _retention_timestamp() -> str:
        return (datetime.now(UTC) + timedelta(hours=24)).isoformat(timespec="microseconds").replace("+00:00", "Z")
