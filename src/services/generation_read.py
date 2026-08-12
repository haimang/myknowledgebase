"""Read-only Task projections over the immutable generation artifact ledger."""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any

from pydantic import ValidationError

from src.contracts.api.generation import (
    GenerationArtifactPointerView,
    GenerationArtifactView,
)
from src.contracts.common.errors import MkbError, NotFoundError
from src.contracts.common.ids import stable_digest
from src.contracts.common.models import assert_safe_public_data
from src.persistence.ports import PersistencePort, UnitOfWork

_ARTIFACT_TYPES = frozenset(
    {
        "structure_document",
        "retrieval_block_projection",
        "structure_validation_report",
        "construction_document",
        "dual_channel_projection",
        "construction_validation_report",
    }
)
_VALIDATION_DISPOSITIONS = frozenset({"full_valid", "invalid", "partial_rejected"})
_ARTIFACT_CURSOR_KIND = "task-generation-artifacts"
_POINTER_CURSOR_KIND = "task-generation-artifact-pointers"


class GenerationArtifactReadService:
    """Expose only safe artifact history rooted by a visible Task.

    Generation artifacts are not Task identities.  Every lookup therefore
    joins through the owning execution and rejects malformed cross-Task ledger
    rows instead of treating a coincidental artifact UUID as authorization.
    """

    def __init__(self, persistence: PersistencePort) -> None:
        self.persistence = persistence

    @staticmethod
    def _task_root(team_uuid: str, task_uuid: str) -> str:
        return f"/v1/teams/{team_uuid}/tasks/{task_uuid}"

    @classmethod
    def _artifact_links(cls, team_uuid: str, task_uuid: str, artifact_uuid: str) -> dict[str, str]:
        task_root = cls._task_root(team_uuid, task_uuid)
        return {
            "self": f"{task_root}/generation-artifacts/{artifact_uuid}",
            "task": task_root,
        }

    @classmethod
    def _pointer_links(cls, team_uuid: str, task_uuid: str, artifact_uuid: str) -> dict[str, str]:
        task_root = cls._task_root(team_uuid, task_uuid)
        return {
            "artifact": f"{task_root}/generation-artifacts/{artifact_uuid}",
            "task": task_root,
        }

    @staticmethod
    async def _visible_task(tx: UnitOfWork, team_uuid: str, task_uuid: str) -> dict[str, Any]:
        row = await tx.fetchone(
            "SELECT task_uuid,status,current_generation,result_ref,proof_ref,error_code,completed_at,deleted_at,trace_uuid "
            "FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
            (team_uuid, task_uuid),
        )
        if row is None:
            raise NotFoundError("task-not-found", "Task was not found")
        if row["deleted_at"] is not None:
            error = {"code": row["error_code"]} if row["error_code"] else None
            raise MkbError(
                "task-deleted",
                "Task has been soft-deleted",
                410,
                {
                    "tombstone": {
                        "task_uuid": row["task_uuid"],
                        "status": row["status"],
                        "current_generation": row["current_generation"],
                        "result_ref": row["result_ref"],
                        "proof_ref": row["proof_ref"],
                        "error": error,
                        "completed_at": row["completed_at"],
                        "deleted_at": row["deleted_at"],
                    }
                },
                trace_uuid=row["trace_uuid"],
            )
        return row

    @staticmethod
    def _validate_artifact_type(artifact_type: str | None) -> None:
        if artifact_type is not None and artifact_type not in _ARTIFACT_TYPES:
            raise MkbError("generation-artifact-type-invalid", "Generation artifact type filter is invalid", 422)

    @staticmethod
    def _validate_disposition(validation_disposition: str | None) -> None:
        if validation_disposition is not None and validation_disposition not in _VALIDATION_DISPOSITIONS:
            raise MkbError(
                "generation-artifact-validation-invalid",
                "Generation artifact validation filter is invalid",
                422,
            )

    @staticmethod
    def _validate_generation(generation: int | None) -> None:
        if generation is not None and generation < 1:
            raise MkbError("generation-invalid", "generation must be positive", 422)

    @staticmethod
    def _limit(limit: int) -> int:
        return min(max(limit, 1), 100)

    @staticmethod
    def _filter_digest(
        *,
        kind: str,
        team_uuid: str,
        task_uuid: str,
        artifact_type: str | None,
        validation_disposition: str | None = None,
        generation: int | None,
    ) -> str:
        return stable_digest(
            {
                "kind": kind,
                "team_uuid": team_uuid,
                "task_uuid": task_uuid,
                "artifact_type": artifact_type,
                "validation_disposition": validation_disposition,
                "generation": generation,
            }
        )

    @staticmethod
    def _encode_cursor(kind: str, **fields: str) -> str:
        payload = json.dumps({"kind": kind, **fields}, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_cursor(cursor: str, *, kind: str, required_fields: set[str]) -> dict[str, str]:
        if len(cursor) > 2048:
            raise MkbError("cursor-invalid", "Cursor is invalid", 422)
        try:
            padded = cursor + "=" * (-len(cursor) % 4)
            raw = base64.b64decode(padded.encode("ascii"), altchars=b"-_", validate=True)
            value = json.loads(raw)
        except (ValueError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError) as exc:
            raise MkbError("cursor-invalid", "Cursor is invalid", 422) from exc
        if (
            not isinstance(value, dict)
            or set(value) != {"kind", *required_fields}
            or value.get("kind") != kind
            or any(not isinstance(value.get(field), str) or not value[field] for field in required_fields)
        ):
            raise MkbError("cursor-invalid", "Cursor is invalid", 422)
        return {field: value[field] for field in required_fields}

    @classmethod
    def _artifact_view(cls, team_uuid: str, task_uuid: str, row: dict[str, Any]) -> dict[str, Any]:
        artifact_uuid = row["generation_artifact_uuid"]
        safe_fields = {
            "generation_artifact_uuid": artifact_uuid,
            "artifact_type": row["artifact_type"],
            "artifact_ordinal": row["artifact_ordinal"],
            "task_generation": row["task_generation"],
            "intake_item_uuid": row["intake_item_uuid"],
            "intake_revision_uuid": row["intake_revision_uuid"],
            "clean_artifact_uuid": row["clean_artifact_uuid"],
            "clean_artifact_digest": row["clean_artifact_digest"],
            "schema_key": row["schema_key"],
            "schema_version": row["schema_version"],
            "schema_digest": row["schema_digest"],
            "profile_key": row["profile_key"],
            "profile_version": row["profile_version"],
            "profile_digest": row["profile_digest"],
            "model_key": row["model_key"],
            "model_version": row["model_version"],
            "prompt_key": row["prompt_key"],
            "prompt_version": row["prompt_version"],
            "prompt_digest": row["prompt_digest"],
            "logical_handle": row["logical_handle"],
            "media_type": row["media_type"],
            "size_bytes": row["size_bytes"],
            "digest_algorithm": row["digest_algorithm"],
            "content_digest": row["content_digest"],
            "validation_disposition": row["validation_disposition"],
            "validation_report_ref": row["validation_report_ref"],
            "validation_report_digest": row["validation_report_digest"],
            "proof_ref": row["proof_ref"],
            "proof_digest": row["proof_digest"],
            "predecessor_generation_artifact_uuid": row["predecessor_generation_artifact_uuid"],
            "created_at": row["created_at"],
        }
        try:
            assert_safe_public_data(safe_fields)
            return GenerationArtifactView.model_validate(
                {**safe_fields, "links": cls._artifact_links(team_uuid, task_uuid, artifact_uuid)}
            ).model_dump(mode="json")
        except (TypeError, ValueError, ValidationError) as exc:
            raise MkbError(
                "generation-artifact-projection-invalid",
                "Generation artifact public projection is invalid",
                503,
            ) from exc

    @classmethod
    def _pointer_view(cls, team_uuid: str, task_uuid: str, row: dict[str, Any]) -> dict[str, Any]:
        artifact_uuid = row["current_generation_artifact_uuid"]
        if (
            row["artifact_task_uuid"] != task_uuid
            or row["artifact_execution_uuid"] != row["pointer_execution_uuid"]
            or row["artifact_type"] != row["pointer_artifact_type"]
            or row["validation_disposition"] != "full_valid"
        ):
            raise MkbError("generation-pointer-invalid", "Generation artifact pointer is invalid", 409)
        safe_fields = {
            "task_generation": row["task_generation"],
            "artifact_type": row["pointer_artifact_type"],
            "current_generation_artifact_uuid": artifact_uuid,
            "pointer_revision": row["pointer_revision"],
            "updated_at": row["updated_at"],
            "intake_item_uuid": row["intake_item_uuid"],
            "intake_revision_uuid": row["intake_revision_uuid"],
            "content_digest": row["content_digest"],
            "validation_disposition": row["validation_disposition"],
        }
        try:
            assert_safe_public_data(safe_fields)
            return GenerationArtifactPointerView.model_validate(
                {**safe_fields, "links": cls._pointer_links(team_uuid, task_uuid, artifact_uuid)}
            ).model_dump(mode="json")
        except (TypeError, ValueError, ValidationError) as exc:
            raise MkbError(
                "generation-artifact-projection-invalid",
                "Generation artifact public projection is invalid",
                503,
            ) from exc

    @staticmethod
    def _artifact_select() -> str:
        return (
            "SELECT a.generation_artifact_uuid,a.artifact_type,a.artifact_ordinal,e.generation AS task_generation,"
            "a.intake_item_uuid,a.intake_revision_uuid,a.clean_artifact_uuid,a.clean_artifact_digest,"
            "a.schema_key,a.schema_version,a.schema_digest,a.profile_key,a.profile_version,a.profile_digest,"
            "a.model_key,a.model_version,a.prompt_key,a.prompt_version,a.prompt_digest,a.logical_handle,a.media_type,"
            "a.size_bytes,a.digest_algorithm,a.content_digest,a.validation_disposition,a.validation_report_ref,"
            "a.validation_report_digest,a.proof_ref,a.proof_digest,a.predecessor_generation_artifact_uuid,a.created_at "
            "FROM mkb_generation_artifacts AS a JOIN mkb_executions AS e "
            "ON e.team_uuid=a.team_uuid AND e.execution_uuid=a.execution_uuid AND e.task_uuid=a.task_uuid "
        )

    async def list_artifacts(
        self,
        team_uuid: str,
        task_uuid: str,
        *,
        artifact_type: str | None = None,
        validation_disposition: str | None = None,
        generation: int | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        self._validate_artifact_type(artifact_type)
        self._validate_disposition(validation_disposition)
        self._validate_generation(generation)
        limit = self._limit(limit)
        filter_digest = self._filter_digest(
            kind=_ARTIFACT_CURSOR_KIND,
            team_uuid=team_uuid,
            task_uuid=task_uuid,
            artifact_type=artifact_type,
            validation_disposition=validation_disposition,
            generation=generation,
        )
        conditions = ["a.team_uuid=?", "a.task_uuid=?", "e.task_uuid=?"]
        params: list[Any] = [team_uuid, task_uuid, task_uuid]
        if artifact_type is not None:
            conditions.append("a.artifact_type=?")
            params.append(artifact_type)
        if validation_disposition is not None:
            conditions.append("a.validation_disposition=?")
            params.append(validation_disposition)
        if generation is not None:
            conditions.append("e.generation=?")
            params.append(generation)
        if cursor:
            decoded = self._decode_cursor(
                cursor,
                kind=_ARTIFACT_CURSOR_KIND,
                required_fields={"filter_digest", "created_at", "generation_artifact_uuid"},
            )
            if decoded["filter_digest"] != filter_digest:
                raise MkbError("cursor-invalid", "Cursor is invalid", 422)
            conditions.append(
                "(a.created_at < ? OR (a.created_at = ? AND a.generation_artifact_uuid < ?))"
            )
            params.extend(
                [decoded["created_at"], decoded["created_at"], decoded["generation_artifact_uuid"]]
            )
        params.append(limit + 1)
        query = (
            self._artifact_select()
            + "WHERE "
            + " AND ".join(conditions)
            + " ORDER BY a.created_at DESC,a.generation_artifact_uuid DESC LIMIT ?"
        )
        async with self.persistence.transaction() as tx:
            await self._visible_task(tx, team_uuid, task_uuid)
            rows = await tx.fetchall(query, tuple(params))
        more = len(rows) > limit
        page = rows[:limit]
        next_cursor = (
            self._encode_cursor(
                _ARTIFACT_CURSOR_KIND,
                filter_digest=filter_digest,
                created_at=page[-1]["created_at"],
                generation_artifact_uuid=page[-1]["generation_artifact_uuid"],
            )
            if more and page
            else None
        )
        return [self._artifact_view(team_uuid, task_uuid, row) for row in page], next_cursor

    async def get_artifact(self, team_uuid: str, task_uuid: str, artifact_uuid: str) -> dict[str, Any]:
        query = (
            self._artifact_select()
            + "WHERE a.team_uuid=? AND a.task_uuid=? AND e.task_uuid=? AND a.generation_artifact_uuid=?"
        )
        async with self.persistence.transaction() as tx:
            await self._visible_task(tx, team_uuid, task_uuid)
            row = await tx.fetchone(query, (team_uuid, task_uuid, task_uuid, artifact_uuid))
        if row is None:
            raise NotFoundError("generation-artifact-not-found", "Generation artifact was not found for this Task")
        return self._artifact_view(team_uuid, task_uuid, row)

    async def list_pointers(
        self,
        team_uuid: str,
        task_uuid: str,
        *,
        artifact_type: str | None = None,
        generation: int | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        self._validate_artifact_type(artifact_type)
        self._validate_generation(generation)
        limit = self._limit(limit)
        filter_digest = self._filter_digest(
            kind=_POINTER_CURSOR_KIND,
            team_uuid=team_uuid,
            task_uuid=task_uuid,
            artifact_type=artifact_type,
            generation=generation,
        )
        conditions = ["p.team_uuid=?", "e.task_uuid=?"]
        params: list[Any] = [team_uuid, task_uuid]
        if artifact_type is not None:
            conditions.append("p.artifact_type=?")
            params.append(artifact_type)
        if generation is not None:
            conditions.append("e.generation=?")
            params.append(generation)
        if cursor:
            decoded = self._decode_cursor(
                cursor,
                kind=_POINTER_CURSOR_KIND,
                required_fields={"filter_digest", "updated_at", "current_generation_artifact_uuid"},
            )
            if decoded["filter_digest"] != filter_digest:
                raise MkbError("cursor-invalid", "Cursor is invalid", 422)
            conditions.append(
                "(p.updated_at < ? OR (p.updated_at = ? AND p.current_generation_artifact_uuid < ?))"
            )
            params.extend(
                [decoded["updated_at"], decoded["updated_at"], decoded["current_generation_artifact_uuid"]]
            )
        params.append(limit + 1)
        query = (
            "SELECT p.execution_uuid AS pointer_execution_uuid,p.artifact_type AS pointer_artifact_type,"
            "p.current_generation_artifact_uuid,p.pointer_revision,p.updated_at,e.generation AS task_generation,"
            "a.task_uuid AS artifact_task_uuid,a.execution_uuid AS artifact_execution_uuid,a.artifact_type,"
            "a.intake_item_uuid,a.intake_revision_uuid,a.content_digest,a.validation_disposition "
            "FROM mkb_generation_pointers AS p JOIN mkb_executions AS e "
            "ON e.team_uuid=p.team_uuid AND e.execution_uuid=p.execution_uuid "
            "LEFT JOIN mkb_generation_artifacts AS a "
            "ON a.team_uuid=p.team_uuid AND a.generation_artifact_uuid=p.current_generation_artifact_uuid "
            "WHERE "
            + " AND ".join(conditions)
            + " ORDER BY p.updated_at DESC,p.current_generation_artifact_uuid DESC LIMIT ?"
        )
        async with self.persistence.transaction() as tx:
            await self._visible_task(tx, team_uuid, task_uuid)
            rows = await tx.fetchall(query, tuple(params))
        more = len(rows) > limit
        page = rows[:limit]
        next_cursor = (
            self._encode_cursor(
                _POINTER_CURSOR_KIND,
                filter_digest=filter_digest,
                updated_at=page[-1]["updated_at"],
                current_generation_artifact_uuid=page[-1]["current_generation_artifact_uuid"],
            )
            if more and page
            else None
        )
        return [self._pointer_view(team_uuid, task_uuid, row) for row in page], next_cursor


__all__ = ["GenerationArtifactReadService"]
