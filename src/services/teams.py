"""Minimal Team Registry; it is an admission projection, not an ownership platform."""

from __future__ import annotations

import json
from typing import Any

from src.contracts.api.models import TeamCreateRequest, TeamPatchRequest
from src.contracts.common.errors import ConflictError, NotFoundError
from src.contracts.common.ids import stable_digest
from src.contracts.common.time import utc_now
from src.persistence.ports import PersistencePort


class TeamService:
    def __init__(self, persistence: PersistencePort) -> None:
        self.persistence = persistence

    @staticmethod
    def _view(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": "mkb.team.v1",
            "team_uuid": row["team_uuid"],
            "name": row["name"],
            "description": row["description"],
            "status": row["status"],
            "revision": row["row_revision"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "deactivated_at": row["deactivated_at"],
            "deleted_at": row["deleted_at"],
            "payload_extra": json.loads(row["payload_extra"]),
        }

    async def create(self, request: TeamCreateRequest) -> tuple[dict[str, Any], bool]:
        data = request.model_dump(mode="json")
        fingerprint = stable_digest(data)
        now = utc_now()
        async with self.persistence.transaction() as tx:
            existing = await tx.fetchone("SELECT * FROM mkb_teams WHERE team_uuid=?", (request.team_uuid,))
            if existing:
                if existing["creation_fingerprint"] != fingerprint:
                    raise ConflictError("team-identity-conflict", "Team identity is already registered")
                return self._view(existing), True
            await tx.execute(
                "INSERT INTO mkb_teams "
                "(team_uuid,name,description,status,row_revision,creation_fingerprint,created_at,updated_at,payload_extra) "
                "VALUES (?,?,?,'active',0,?,?,?,?)",
                (
                    request.team_uuid,
                    request.name,
                    request.description,
                    fingerprint,
                    now,
                    now,
                    json.dumps(request.payload_extra, separators=(",", ":")),
                ),
            )
            created = await tx.fetchone("SELECT * FROM mkb_teams WHERE team_uuid=?", (request.team_uuid,))
        assert created is not None
        return self._view(created), False

    async def get(self, team_uuid: str) -> dict[str, Any]:
        async with self.persistence.transaction() as tx:
            row = await tx.fetchone("SELECT * FROM mkb_teams WHERE team_uuid=?", (team_uuid,))
        if row is None:
            raise NotFoundError("team-not-registered", "Team is not registered")
        return self._view(row)

    async def list(self, status: str | None = None) -> list[dict[str, Any]]:
        async with self.persistence.transaction() as tx:
            if status:
                rows = await tx.fetchall(
                    "SELECT * FROM mkb_teams WHERE status=? ORDER BY updated_at DESC, team_uuid DESC", (status,)
                )
            else:
                rows = await tx.fetchall("SELECT * FROM mkb_teams ORDER BY updated_at DESC, team_uuid DESC")
        return [self._view(row) for row in rows]

    async def patch(self, team_uuid: str, request: TeamPatchRequest) -> dict[str, Any]:
        async with self.persistence.transaction() as tx:
            row = await tx.fetchone("SELECT * FROM mkb_teams WHERE team_uuid=?", (team_uuid,))
            if row is None:
                raise NotFoundError("team-not-registered", "Team is not registered")
            if row["status"] == "deleted":
                raise ConflictError("team-deleted", "Deleted Team must be restored before it can be changed")
            if row["row_revision"] != request.expected_revision:
                raise ConflictError(
                    "revision-conflict", "Team revision is stale", {"current_revision": row["row_revision"]}
                )
            name = request.name if request.name is not None else row["name"]
            description = request.description if request.description is not None else row["description"]
            extra = request.payload_extra if request.payload_extra else json.loads(row["payload_extra"])
            await tx.execute(
                "UPDATE mkb_teams SET name=?,description=?,payload_extra=?,row_revision=row_revision+1,updated_at=? "
                "WHERE team_uuid=? AND row_revision=?",
                (
                    name,
                    description,
                    json.dumps(extra, separators=(",", ":")),
                    utc_now(),
                    team_uuid,
                    request.expected_revision,
                ),
            )
            updated = await tx.fetchone("SELECT * FROM mkb_teams WHERE team_uuid=?", (team_uuid,))
        assert updated is not None
        return self._view(updated)

    async def transition(self, team_uuid: str, action: str, expected_revision: int) -> dict[str, Any]:
        transitions = {
            ("active", "deactivate"): "inactive",
            ("inactive", "activate"): "active",
            ("active", "delete"): "deleted",
            ("inactive", "delete"): "deleted",
            ("deleted", "restore"): "inactive",
        }
        async with self.persistence.transaction() as tx:
            row = await tx.fetchone("SELECT * FROM mkb_teams WHERE team_uuid=?", (team_uuid,))
            if row is None:
                raise NotFoundError("team-not-registered", "Team is not registered")
            if row["row_revision"] != expected_revision:
                raise ConflictError(
                    "revision-conflict", "Team revision is stale", {"current_revision": row["row_revision"]}
                )
            target = transitions.get((row["status"], action))
            if target is None:
                raise ConflictError("team-transition-invalid", "Team lifecycle transition is invalid")
            now = utc_now()
            deactivated_at = now if target == "inactive" and action == "deactivate" else row["deactivated_at"]
            deleted_at = now if target == "deleted" else row["deleted_at"]
            await tx.execute(
                "UPDATE mkb_teams SET status=?,deactivated_at=?,deleted_at=?,row_revision=row_revision+1,updated_at=? "
                "WHERE team_uuid=? AND row_revision=?",
                (target, deactivated_at, deleted_at, now, team_uuid, expected_revision),
            )
            updated = await tx.fetchone("SELECT * FROM mkb_teams WHERE team_uuid=?", (team_uuid,))
        assert updated is not None
        return self._view(updated)

    async def require_active(self, team_uuid: str) -> dict[str, Any]:
        async with self.persistence.transaction() as tx:
            row = await tx.fetchone("SELECT * FROM mkb_teams WHERE team_uuid=?", (team_uuid,))
        if row is None:
            raise NotFoundError("team-not-registered", "Team is not registered")
        if row["status"] != "active":
            raise ConflictError("team-not-active", "Team is not active")
        return row
