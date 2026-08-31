"""Linearizable Source/Observation admission and attempt lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.contracts.api.models import TaskCreateRequest
from src.contracts.common.errors import ConflictError, MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.persistence.ports import PersistencePort, UnitOfWork


@dataclass(frozen=True, slots=True)
class ObservationAdmission:
    intake_source_uuid: str
    observation_uuid: str
    observation_key: str
    observation_fingerprint: str
    attempt_generation: int
    expected_item_epoch: int | None
    compatibility_mode: str
    retry_existing: bool = False
    replay_task_uuid: str | None = None


class ObservationReservationService:
    @staticmethod
    def _source(request: TaskCreateRequest) -> Any | None:
        return getattr(request.payload, "source", None) if request.request_intent == "intake.ingest" else None

    @classmethod
    def applies(cls, request: TaskCreateRequest) -> bool:
        return cls._source(request) is not None

    @classmethod
    def observation_coordinates(cls, request: TaskCreateRequest) -> tuple[str, str, str, str, str, bool, int | None]:
        source = cls._source(request)
        if source is None:
            raise ValueError("request has no intake observation")
        source_kind = str(source.source_kind)
        external_key = str(source.external_key).strip()
        normalized_external_key = external_key.casefold()
        explicit_key = getattr(source, "observation_key", None)
        if isinstance(explicit_key, str) and explicit_key.strip():
            observation_key = explicit_key.strip()
            compatibility_mode = "v2_explicit"
        elif source_kind == "registered_api":
            observation_key = normalized_external_key
            compatibility_mode = "v1_registered_external_key"
        else:
            observation_key = request.task_uuid
            compatibility_mode = "v1_task_derived"
        material = source.model_dump(
            mode="json",
            exclude={
                "observation_key",
                "retry_failed_observation",
                "expected_observation_attempt_generation",
            },
        )
        fingerprint = stable_digest(
            {
                "schema_version": "mkb.observation-fingerprint.v2",
                "source_kind": source_kind,
                "normalized_external_key": normalized_external_key,
                "source": material,
            }
        )
        return (
            source_kind,
            normalized_external_key,
            observation_key,
            fingerprint,
            compatibility_mode,
            bool(getattr(source, "retry_failed_observation", False)),
            getattr(source, "expected_observation_attempt_generation", None),
        )

    async def resolve_tx(
        self,
        tx: UnitOfWork,
        request: TaskCreateRequest,
        *,
        source_descriptor_ref: str,
        source_descriptor_digest: str,
    ) -> ObservationAdmission:
        source_kind, external_key, observation_key, fingerprint, compatibility_mode, retry_failed, expected_attempt = (
            self.observation_coordinates(request)
        )
        definition = await tx.fetchone(
            "SELECT definition_digest FROM mkb_source_kind_definitions "
            "WHERE source_kind=? AND definition_version='v1' AND status='active'",
            (source_kind,),
        )
        if definition is None:
            raise MkbError("REGISTRY_NOT_FOUND", "Source kind definition is unavailable", 503)
        source = await tx.fetchone(
            "SELECT intake_source_uuid FROM mkb_intake_sources "
            "WHERE team_uuid=? AND source_kind=? AND normalized_external_key=?",
            (request.team_uuid, source_kind, external_key),
        )
        intake_source_uuid = str(source["intake_source_uuid"]) if source is not None else uuid7()
        if source is None:
            now = utc_now()
            await tx.execute(
                "INSERT INTO mkb_intake_sources"
                "(team_uuid,intake_source_uuid,source_kind,source_kind_definition_version,source_kind_definition_digest,"
                "source_descriptor_ref,source_descriptor_digest,accepts_new_snapshots,created_at,updated_at,payload_extra,"
                "normalized_external_key) VALUES (?,?,?,'v1',?,?,?,1,?,?,'{}',?)",
                (
                    request.team_uuid,
                    intake_source_uuid,
                    source_kind,
                    definition["definition_digest"],
                    source_descriptor_ref,
                    source_descriptor_digest,
                    now,
                    now,
                    external_key,
                ),
            )
        item = await tx.fetchone(
            "SELECT intake_item_uuid,lifecycle_state,row_revision FROM mkb_intake_items "
            "WHERE team_uuid=? AND intake_source_uuid=? AND normalized_external_key=?",
            (request.team_uuid, intake_source_uuid, external_key),
        )
        if item is not None and item["lifecycle_state"] != "active":
            code = "INTAKE_ITEM_DELETED" if item["lifecycle_state"] == "deleted" else "INTAKE_ITEM_NOT_ACTIVE"
            raise ConflictError(code, "Inactive Intake identity requires an explicit lifecycle command")
        expected_item_epoch = None if item is None else int(item["row_revision"])
        existing = await tx.fetchone(
            "SELECT observation_uuid,observation_fingerprint,state,current_attempt_generation,owner_task_uuid,"
            "compatibility_mode FROM mkb_intake_observations "
            "WHERE team_uuid=? AND intake_source_uuid=? AND observation_key=?",
            (request.team_uuid, intake_source_uuid, observation_key),
        )
        if existing is None:
            if retry_failed:
                raise ConflictError("OBSERVATION_RETRY_TARGET_MISSING", "Failed Observation does not exist")
            return ObservationAdmission(
                intake_source_uuid=intake_source_uuid,
                observation_uuid=uuid7(),
                observation_key=observation_key,
                observation_fingerprint=fingerprint,
                attempt_generation=1,
                expected_item_epoch=expected_item_epoch,
                compatibility_mode=compatibility_mode,
            )
        if existing["observation_fingerprint"] != fingerprint:
            raise ConflictError("OBSERVATION_CONFLICT", "Observation key has a different fingerprint")
        state = str(existing["state"])
        generation = int(existing["current_attempt_generation"])
        if state == "failed":
            if not retry_failed:
                raise ConflictError("OBSERVATION_FAILED_RETRY_REQUIRED", "Failed Observation requires a typed retry")
            if expected_attempt != generation:
                raise ConflictError("OBSERVATION_ATTEMPT_CONFLICT", "Observation attempt generation changed")
            return ObservationAdmission(
                intake_source_uuid=intake_source_uuid,
                observation_uuid=str(existing["observation_uuid"]),
                observation_key=observation_key,
                observation_fingerprint=fingerprint,
                attempt_generation=generation + 1,
                expected_item_epoch=expected_item_epoch,
                compatibility_mode=str(existing["compatibility_mode"]),
                retry_existing=True,
            )
        if retry_failed:
            raise ConflictError("OBSERVATION_RETRY_STATE_CONFLICT", "Only a failed Observation can be retried")
        if state in {"reserved", "acquired", "accepted"}:
            return ObservationAdmission(
                intake_source_uuid=intake_source_uuid,
                observation_uuid=str(existing["observation_uuid"]),
                observation_key=observation_key,
                observation_fingerprint=fingerprint,
                attempt_generation=generation,
                expected_item_epoch=expected_item_epoch,
                compatibility_mode=str(existing["compatibility_mode"]),
                replay_task_uuid=str(existing["owner_task_uuid"]),
            )
        raise ConflictError("OBSERVATION_STATE_CONFLICT", "Observation cannot be adopted in its current state")

    async def reserve_tx(
        self,
        tx: UnitOfWork,
        request: TaskCreateRequest,
        admission: ObservationAdmission,
        *,
        execution_uuid: str,
    ) -> None:
        now = utc_now()
        if admission.retry_existing:
            updated = await tx.execute(
                "UPDATE mkb_intake_observations SET state='reserved',current_attempt_generation=?,owner_task_uuid=?,"
                "owner_execution_uuid=?,accepted_snapshot_uuid=NULL,acquired_at=NULL,accepted_at=NULL,terminal_at=NULL,"
                "last_error_code=NULL,row_revision=row_revision+1,reserved_at=? "
                "WHERE team_uuid=? AND observation_uuid=? AND state='failed' AND current_attempt_generation=?",
                (
                    admission.attempt_generation,
                    request.task_uuid,
                    execution_uuid,
                    now,
                    request.team_uuid,
                    admission.observation_uuid,
                    admission.attempt_generation - 1,
                ),
            )
            if updated.rowcount != 1:
                raise ConflictError("OBSERVATION_ATTEMPT_CONFLICT", "Observation retry lost its generation fence")
        else:
            await tx.execute(
                "INSERT INTO mkb_intake_observations"
                "(observation_uuid,team_uuid,intake_source_uuid,observation_key,observation_fingerprint,state,"
                "current_attempt_generation,owner_task_uuid,owner_execution_uuid,row_revision,reserved_at,"
                "compatibility_mode,payload_extra) VALUES (?,?,?,?,?,'reserved',?,?,?,?,?,?,'{}')",
                (
                    admission.observation_uuid,
                    request.team_uuid,
                    admission.intake_source_uuid,
                    admission.observation_key,
                    admission.observation_fingerprint,
                    admission.attempt_generation,
                    request.task_uuid,
                    execution_uuid,
                    0,
                    now,
                    admission.compatibility_mode,
                ),
            )
        attempt_uuid = uuid7()
        await tx.execute(
            "INSERT INTO mkb_observation_attempts"
            "(attempt_uuid,observation_uuid,team_uuid,attempt_generation,task_uuid,execution_uuid,state,"
            "expected_observation_revision,row_revision,created_at,payload_extra) "
            "VALUES (?,?,?,?,?,?,'reserved',?,0,?,'{}')",
            (
                attempt_uuid,
                admission.observation_uuid,
                request.team_uuid,
                admission.attempt_generation,
                request.task_uuid,
                execution_uuid,
                1 if admission.retry_existing else 0,
                now,
            ),
        )
        await self._attempt_transition_tx(
            tx,
            team_uuid=request.team_uuid,
            observation_uuid=admission.observation_uuid,
            attempt_uuid=attempt_uuid,
            attempt_generation=admission.attempt_generation,
            before=None,
            after="reserved",
            expected_revision=0,
            actual_revision=0,
        )
        for table, key_column, key in (
            ("mkb_tasks", "task_uuid", request.task_uuid),
            ("mkb_executions", "execution_uuid", execution_uuid),
        ):
            await tx.execute(
                f"UPDATE {table} SET observation_uuid=?,observation_attempt_generation=?,expected_item_epoch=? "
                f"WHERE team_uuid=? AND {key_column}=?",
                (
                    admission.observation_uuid,
                    admission.attempt_generation,
                    admission.expected_item_epoch,
                    request.team_uuid,
                    key,
                ),
            )

    @staticmethod
    async def identity_for_execution_tx(
        tx: UnitOfWork, *, team_uuid: str, execution_uuid: str
    ) -> dict[str, Any] | None:
        return await tx.fetchone(
            "SELECT o.observation_uuid,o.observation_key,o.observation_fingerprint,o.current_attempt_generation,"
            "o.intake_source_uuid,e.expected_item_epoch,i.intake_item_uuid,i.lifecycle_state,i.row_revision AS item_epoch "
            "FROM mkb_executions e "
            "JOIN mkb_intake_observations o ON o.team_uuid=e.team_uuid AND o.observation_uuid=e.observation_uuid "
            "JOIN mkb_intake_sources s ON s.team_uuid=o.team_uuid AND s.intake_source_uuid=o.intake_source_uuid "
            "LEFT JOIN mkb_intake_items i ON i.team_uuid=s.team_uuid AND i.intake_source_uuid=s.intake_source_uuid "
            "AND i.normalized_external_key=s.normalized_external_key "
            "WHERE e.team_uuid=? AND e.execution_uuid=?",
            (team_uuid, execution_uuid),
        )

    async def mark_acquired_tx(
        self,
        tx: UnitOfWork,
        *,
        team_uuid: str,
        execution_uuid: str,
        artifact_ref: str | None,
        artifact_digest: str | None,
    ) -> None:
        identity = await self.identity_for_execution_tx(tx, team_uuid=team_uuid, execution_uuid=execution_uuid)
        if identity is None:
            return
        now = utc_now()
        attempt = await tx.fetchone(
            "SELECT attempt_uuid,row_revision,state FROM mkb_observation_attempts "
            "WHERE team_uuid=? AND observation_uuid=? AND attempt_generation=?",
            (team_uuid, identity["observation_uuid"], identity["current_attempt_generation"]),
        )
        if attempt is None or attempt["state"] == "acquired":
            return
        updated = await tx.execute(
            "UPDATE mkb_observation_attempts SET state='acquired',acquired_artifact_ref=?,acquired_artifact_digest=?,"
            "acquired_at=?,row_revision=row_revision+1 WHERE attempt_uuid=? AND state IN ('reserved','acquiring') "
            "AND row_revision=?",
            (artifact_ref, artifact_digest, now, attempt["attempt_uuid"], attempt["row_revision"]),
        )
        if updated.rowcount != 1:
            raise ConflictError("OBSERVATION_ATTEMPT_CONFLICT", "Observation acquire attempt changed")
        await tx.execute(
            "UPDATE mkb_intake_observations SET state='acquired',acquired_at=?,row_revision=row_revision+1 "
            "WHERE team_uuid=? AND observation_uuid=? AND state='reserved' AND current_attempt_generation=?",
            (now, team_uuid, identity["observation_uuid"], identity["current_attempt_generation"]),
        )
        await self._attempt_transition_tx(
            tx,
            team_uuid=team_uuid,
            observation_uuid=str(identity["observation_uuid"]),
            attempt_uuid=str(attempt["attempt_uuid"]),
            attempt_generation=int(identity["current_attempt_generation"]),
            before=str(attempt["state"]),
            after="acquired",
            expected_revision=int(attempt["row_revision"]),
            actual_revision=int(attempt["row_revision"]) + 1,
        )

    async def mark_accepted_tx(
        self,
        tx: UnitOfWork,
        *,
        team_uuid: str,
        execution_uuid: str,
        snapshot_uuid: str,
    ) -> None:
        identity = await self.identity_for_execution_tx(tx, team_uuid=team_uuid, execution_uuid=execution_uuid)
        if identity is None:
            return
        now = utc_now()
        await tx.execute(
            "INSERT INTO mkb_observation_snapshot_links(observation_uuid,team_uuid,intake_snapshot_uuid,linked_at,payload_extra) "
            "VALUES (?,?,?,?,'{}')",
            (identity["observation_uuid"], team_uuid, snapshot_uuid, now),
        )
        attempt = await tx.fetchone(
            "SELECT attempt_uuid,row_revision,state FROM mkb_observation_attempts "
            "WHERE team_uuid=? AND observation_uuid=? AND attempt_generation=?",
            (team_uuid, identity["observation_uuid"], identity["current_attempt_generation"]),
        )
        if attempt is None:
            raise MkbError("OBSERVATION_ATTEMPT_MISSING", "Observation attempt is unavailable", 503)
        await tx.execute(
            "UPDATE mkb_observation_attempts SET state='accepted',terminal_at=?,row_revision=row_revision+1 "
            "WHERE attempt_uuid=? AND state='acquired' AND row_revision=?",
            (now, attempt["attempt_uuid"], attempt["row_revision"]),
        )
        updated = await tx.execute(
            "UPDATE mkb_intake_observations SET state='accepted',accepted_snapshot_uuid=?,accepted_at=?,terminal_at=?,"
            "row_revision=row_revision+1 WHERE team_uuid=? AND observation_uuid=? AND state='acquired'",
            (snapshot_uuid, now, now, team_uuid, identity["observation_uuid"]),
        )
        if updated.rowcount != 1:
            raise ConflictError("OBSERVATION_STATE_CONFLICT", "Observation acceptance changed")
        await self._attempt_transition_tx(
            tx,
            team_uuid=team_uuid,
            observation_uuid=str(identity["observation_uuid"]),
            attempt_uuid=str(attempt["attempt_uuid"]),
            attempt_generation=int(identity["current_attempt_generation"]),
            before=str(attempt["state"]),
            after="accepted",
            expected_revision=int(attempt["row_revision"]),
            actual_revision=int(attempt["row_revision"]) + 1,
        )

    async def mark_failed_for_execution(
        self,
        persistence: PersistencePort,
        *,
        team_uuid: str,
        execution_uuid: str,
        error_code: str,
    ) -> None:
        now = utc_now()
        async with persistence.transaction() as tx:
            identity = await self.identity_for_execution_tx(tx, team_uuid=team_uuid, execution_uuid=execution_uuid)
            if identity is None:
                return
            attempt = await tx.fetchone(
                "SELECT attempt_uuid,row_revision,state FROM mkb_observation_attempts WHERE team_uuid=? "
                "AND observation_uuid=? AND attempt_generation=?",
                (team_uuid, identity["observation_uuid"], identity["current_attempt_generation"]),
            )
            if attempt is None or attempt["state"] in {"accepted", "failed", "abandoned"}:
                return
            await tx.execute(
                "UPDATE mkb_observation_attempts SET state='failed',error_code=?,terminal_at=?,row_revision=row_revision+1 "
                "WHERE attempt_uuid=? AND row_revision=?",
                (error_code, now, attempt["attempt_uuid"], attempt["row_revision"]),
            )
            await tx.execute(
                "UPDATE mkb_intake_observations SET state='failed',last_error_code=?,terminal_at=?,"
                "row_revision=row_revision+1 WHERE team_uuid=? AND observation_uuid=? "
                "AND current_attempt_generation=? AND state IN ('reserved','acquired')",
                (error_code, now, team_uuid, identity["observation_uuid"], identity["current_attempt_generation"]),
            )
            await self._attempt_transition_tx(
                tx,
                team_uuid=team_uuid,
                observation_uuid=str(identity["observation_uuid"]),
                attempt_uuid=str(attempt["attempt_uuid"]),
                attempt_generation=int(identity["current_attempt_generation"]),
                before=str(attempt["state"]),
                after="failed",
                expected_revision=int(attempt["row_revision"]),
                actual_revision=int(attempt["row_revision"]) + 1,
            )

    @staticmethod
    async def _attempt_transition_tx(
        tx: UnitOfWork,
        *,
        team_uuid: str,
        observation_uuid: str,
        attempt_uuid: str,
        attempt_generation: int,
        before: str | None,
        after: str,
        expected_revision: int,
        actual_revision: int,
    ) -> None:
        material = {
            "observation_uuid": observation_uuid,
            "attempt_uuid": attempt_uuid,
            "attempt_generation": attempt_generation,
            "state_before": before,
            "state_after": after,
            "actual_row_revision": actual_revision,
        }
        await tx.execute(
            "INSERT INTO mkb_observation_attempt_transitions"
            "(transition_uuid,team_uuid,observation_uuid,attempt_uuid,attempt_generation,state_before,state_after,"
            "expected_row_revision,actual_row_revision,transition_digest,occurred_at,payload_extra) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,'{}')",
            (
                uuid7(),
                team_uuid,
                observation_uuid,
                attempt_uuid,
                attempt_generation,
                before,
                after,
                expected_revision,
                actual_revision,
                stable_digest(material),
                utc_now(),
            ),
        )
