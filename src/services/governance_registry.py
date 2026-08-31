"""Durable projections of code-owned NHX1 operation and error registries."""

from __future__ import annotations

from src.contracts.common.errors import MkbError
from src.contracts.common.time import utc_now
from src.contracts.governance import ERROR_DEFINITIONS, OUTBOX_KIND_DEFINITIONS
from src.persistence.ports import PersistencePort, UnitOfWork
from src.runtime.workflow.capability_registry import (
    DEFAULT_PROCESS_CAPABILITY_REGISTRY,
    ProcessCapabilityRegistry,
)


class GovernanceRegistryService:
    def __init__(
        self,
        persistence: PersistencePort,
        capabilities: ProcessCapabilityRegistry | None = None,
    ) -> None:
        self.persistence = persistence
        self.capabilities = capabilities or DEFAULT_PROCESS_CAPABILITY_REGISTRY

    async def bootstrap(self) -> None:
        async with self.persistence.transaction() as tx:
            for definition in OUTBOX_KIND_DEFINITIONS.values():
                await self._register_outbox(tx, definition)
            for definition in ERROR_DEFINITIONS.values():
                await self._register_error(tx, definition)
        await self.capabilities.bootstrap(self.persistence)

    async def readiness(self) -> bool:
        async with self.persistence.read_snapshot() as tx:
            outbox = await tx.fetchall("SELECT kind,definition_digest FROM mkb_outbox_kind_definitions")
            errors = await tx.fetchall("SELECT error_code,definition_digest FROM mkb_error_definitions")
            aliases = await tx.fetchall("SELECT legacy_code,canonical_error_code FROM mkb_error_aliases")
        expected_aliases = {
            (alias, definition.code) for definition in ERROR_DEFINITIONS.values() for alias in definition.legacy_aliases
        }
        return (
            {(row["kind"], row["definition_digest"]) for row in outbox}
            == {(definition.kind, definition.definition_digest) for definition in OUTBOX_KIND_DEFINITIONS.values()}
            and {(row["error_code"], row["definition_digest"]) for row in errors}
            == {(definition.code, definition.definition_digest) for definition in ERROR_DEFINITIONS.values()}
            and {(row["legacy_code"], row["canonical_error_code"]) for row in aliases} == expected_aliases
            and await self.capabilities.readiness(self.persistence)
        )

    @staticmethod
    async def _register_outbox(tx: UnitOfWork, definition) -> None:
        existing = await tx.fetchone(
            "SELECT definition_digest FROM mkb_outbox_kind_definitions WHERE kind=?", (definition.kind,)
        )
        if existing is not None:
            if existing["definition_digest"] != definition.definition_digest:
                raise MkbError("REGISTRY_DIGEST_MISMATCH", "Outbox kind definition conflicts", 503)
            return
        await tx.execute(
            "INSERT INTO mkb_outbox_kind_definitions(kind,definition_version,definition_digest,owner_kind,criticality,"
            "attempt_budget,dead_error_code,requeue_policy,registered_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                definition.kind,
                definition.definition_version,
                definition.definition_digest,
                definition.owner_kind,
                definition.criticality.value,
                definition.attempt_budget,
                definition.dead_error_code,
                definition.requeue_policy,
                utc_now(),
            ),
        )

    @staticmethod
    async def _register_error(tx: UnitOfWork, definition) -> None:
        existing = await tx.fetchone(
            "SELECT definition_digest FROM mkb_error_definitions WHERE error_code=?", (definition.code,)
        )
        if existing is not None:
            if existing["definition_digest"] != definition.definition_digest:
                raise MkbError("REGISTRY_DIGEST_MISMATCH", "Error definition conflicts", 503)
        else:
            await tx.execute(
                "INSERT INTO mkb_error_definitions(error_code,definition_version,category,http_status,retryable,"
                "public_message,definition_digest,registered_at) VALUES (?,?,?,?,?,?,?,?)",
                (
                    definition.code,
                    definition.definition_version,
                    definition.category,
                    definition.http_status,
                    int(definition.retryable),
                    definition.public_message,
                    definition.definition_digest,
                    utc_now(),
                ),
            )
        for alias in definition.legacy_aliases:
            existing_alias = await tx.fetchone(
                "SELECT canonical_error_code FROM mkb_error_aliases WHERE legacy_code=?", (alias,)
            )
            if existing_alias is not None and existing_alias["canonical_error_code"] != definition.code:
                raise MkbError("REGISTRY_DIGEST_MISMATCH", "Error alias conflicts", 503)
            if existing_alias is None:
                await tx.execute(
                    "INSERT INTO mkb_error_aliases(legacy_code,canonical_error_code,route_version,registered_at) "
                    "VALUES (?,?,?,?)",
                    (alias, definition.code, "v1-compat", utc_now()),
                )
