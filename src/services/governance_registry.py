"""Durable projections of code-owned NHX1 operation and error registries."""

from __future__ import annotations

from src.contracts.common.errors import MkbError
from src.contracts.common.time import utc_now
from src.contracts.governance import ERROR_DEFINITIONS, OUTBOX_KIND_DEFINITIONS
from src.persistence.ports import PersistencePort, UnitOfWork
from src.runtime.signals import DEFAULT_SIGNAL_REGISTRY, OperationalSignalRegistry
from src.runtime.workflow.capability_registry import (
    DEFAULT_PROCESS_CAPABILITY_REGISTRY,
    ProcessCapabilityRegistry,
)


class GovernanceRegistryService:
    def __init__(
        self,
        persistence: PersistencePort,
        capabilities: ProcessCapabilityRegistry | None = None,
        signals: OperationalSignalRegistry | None = None,
    ) -> None:
        self.persistence = persistence
        self.capabilities = capabilities or DEFAULT_PROCESS_CAPABILITY_REGISTRY
        self.signals = signals or DEFAULT_SIGNAL_REGISTRY

    async def bootstrap(self) -> None:
        async with self.persistence.transaction() as tx:
            for definition in OUTBOX_KIND_DEFINITIONS.values():
                await self._register_outbox(tx, definition)
            for definition in ERROR_DEFINITIONS.values():
                await self._register_error(tx, definition)
        await self.capabilities.bootstrap(self.persistence)
        await self._bootstrap_signals()

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
            and await self._signals_readiness()
        )

    async def _bootstrap_signals(self) -> None:
        async with self.persistence.transaction() as tx:
            for definition in self.signals.definitions:
                existing = await tx.fetchone(
                    "SELECT definition_digest FROM mkb_operational_signal_definitions WHERE signal_key=?",
                    (definition.signal_key,),
                )
                if existing is not None:
                    if existing["definition_digest"] != definition.definition_digest:
                        raise MkbError("REGISTRY_DIGEST_MISMATCH", "Operational signal definition conflicts", 503)
                    continue
                await tx.execute(
                    "INSERT INTO mkb_operational_signal_definitions(signal_key,definition_version,definition_digest,"
                    "severity,emitter_key,metric_name,alert_id,runbook_ref,owner_component,registered_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        definition.signal_key,
                        definition.definition_version,
                        definition.definition_digest,
                        definition.severity,
                        definition.emitter_key,
                        definition.metric_name,
                        definition.alert_id,
                        definition.runbook_ref,
                        definition.owner_component,
                        utc_now(),
                    ),
                )

    async def _signals_readiness(self) -> bool:
        async with self.persistence.read_snapshot() as tx:
            rows = await tx.fetchall("SELECT signal_key,definition_digest FROM mkb_operational_signal_definitions")
        expected = {(item.signal_key, item.definition_digest) for item in self.signals.definitions}
        return {(row["signal_key"], row["definition_digest"]) for row in rows} == expected

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
