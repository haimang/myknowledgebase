"""Safe, read-only workflow/capability/source discovery projections."""

from __future__ import annotations

import base64
import binascii
import json
from collections.abc import Mapping
from typing import Any

from src.contracts.api.models import (
    CapabilityCatalogView,
    CatalogView,
    IntakeItemView,
    NamespaceView,
    SourceKindCatalogView,
    WorkflowCatalogView,
)
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, validate_external_uuid
from src.persistence.ports import PersistencePort
from src.runtime.roles import DeploymentRole
from src.runtime.workflow.capability_registry import ProcessCapabilityRegistry
from src.services.workflow_registry import WorkflowRegistryService


class WorkflowCatalogService:
    """Project only registered, bounded identities; never returns graph payloads."""

    def __init__(
        self,
        persistence: PersistencePort,
        workflows: WorkflowRegistryService,
        capabilities: ProcessCapabilityRegistry,
    ) -> None:
        self._persistence = persistence
        self._workflows = workflows
        self._capabilities = capabilities

    async def catalog(
        self,
        *,
        role: DeploymentRole | str,
        available_supplies: Mapping[str, bool] | None = None,
    ) -> CatalogView:
        return CatalogView(
            deployment_role=role.value if isinstance(role, DeploymentRole) else str(role),
            capability_manifest_digest=self._capabilities.definition_digest,
            workflows=await self.workflows(),
            capabilities=[
                CapabilityCatalogView.model_validate(item)
                for item in self._capabilities.availability(available_supplies or {})
            ],
            source_kinds=await self.source_kinds(),
        )

    async def workflows(self) -> list[WorkflowCatalogView]:
        async with self._persistence.read_snapshot() as tx:
            rows = await tx.fetchall(
                "SELECT r.workflow_key,r.workflow_uuid,r.active_revision_uuid,r.purpose_key,r.execution_role,"
                "v.revision_number,v.compiled_digest,r.registry_status "
                "FROM mkb_workflow_registry r JOIN mkb_workflow_revisions v "
                "ON v.workflow_revision_uuid=r.active_revision_uuid "
                "WHERE r.registry_status='enabled' ORDER BY r.workflow_key"
            )
            required_rows = await tx.fetchall(
                "SELECT r.workflow_key,s.process_key FROM mkb_workflow_registry r "
                "JOIN mkb_workflow_revisions v ON v.workflow_revision_uuid=r.active_revision_uuid "
                "JOIN mkb_workflow_steps s ON s.workflow_revision_uuid=v.workflow_revision_uuid "
                "WHERE r.registry_status='enabled' AND s.step_kind='process' AND s.requiredness='required' "
                "ORDER BY r.workflow_key,s.process_key"
            )
        required: dict[str, list[str]] = {}
        for row in required_rows:
            if row["process_key"] is not None:
                required.setdefault(row["workflow_key"], []).append(row["process_key"])
        result: list[WorkflowCatalogView] = []
        for row in rows:
            result.append(
                WorkflowCatalogView(
                    workflow_key=row["workflow_key"],
                    workflow_uuid=row["workflow_uuid"],
                    workflow_revision_uuid=row["active_revision_uuid"],
                    revision_number=int(row["revision_number"]),
                    purpose_key=row["purpose_key"],
                    execution_role=row["execution_role"],
                    compiled_digest=row["compiled_digest"],
                    required_process_keys=required.get(row["workflow_key"], []),
                    availability="registered",
                )
            )
        return result

    async def source_kinds(self) -> list[SourceKindCatalogView]:
        async with self._persistence.read_snapshot() as tx:
            rows = await tx.fetchall(
                "SELECT source_kind,definition_version,definition_digest,cardinality,definition_body_json "
                "FROM mkb_source_kind_definitions WHERE status='active' ORDER BY source_kind"
            )
        result: list[SourceKindCatalogView] = []
        for row in rows:
            try:
                body = json.loads(row["definition_body_json"] or "{}")
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise MkbError("CATALOG_DEFINITION_INVALID", "Source catalog definition is invalid", 503) from exc
            if not isinstance(body, dict):
                raise MkbError("CATALOG_DEFINITION_INVALID", "Source catalog definition is invalid", 503)
            result.append(
                SourceKindCatalogView(
                    source_kind=row["source_kind"],
                    definition_version=row["definition_version"],
                    definition_digest=row["definition_digest"],
                    cardinality=row["cardinality"],
                    acquisition_capabilities=list(body.get("acquire", body.get("acquisition", [])) or []),
                    decode_capabilities=list(body.get("decode", []) or []),
                    clean_capabilities=list(body.get("clean", []) or []),
                )
            )
        return result

    async def items(
        self,
        team_uuid: str,
        *,
        source_kind: str | None = None,
        external_key: str | None = None,
        lifecycle_state: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[IntakeItemView], str | None]:
        validate_external_uuid(team_uuid, field="team_uuid")
        if not 1 <= limit <= 100:
            raise MkbError("CATALOG_LIMIT_INVALID", "Catalog limit must be between 1 and 100", 422)
        if lifecycle_state is not None and lifecycle_state not in {"active", "deactivated", "deleted"}:
            raise MkbError("CATALOG_FILTER_INVALID", "Lifecycle filter is invalid", 422)
        conditions = ["i.team_uuid=?"]
        params: list[Any] = [team_uuid]
        if source_kind is not None:
            conditions.append("s.source_kind=?")
            params.append(source_kind)
        if external_key is not None:
            if not external_key.strip():
                raise MkbError("CATALOG_FILTER_INVALID", "External key filter is invalid", 422)
            conditions.append("i.normalized_external_key=?")
            params.append(external_key.strip().casefold())
        if lifecycle_state is not None:
            conditions.append("i.lifecycle_state=?")
            params.append(lifecycle_state)
        filter_digest = stable_digest(
            {
                "team_uuid": team_uuid,
                "source_kind": source_kind,
                "external_key": external_key.strip().casefold() if external_key else None,
                "lifecycle_state": lifecycle_state,
            }
        )
        if cursor:
            row = self._decode_cursor(cursor, "items", filter_digest)
            conditions.append("(i.updated_at<? OR (i.updated_at=? AND i.intake_item_uuid<?))")
            params.extend([row["updated_at"], row["updated_at"], row["intake_item_uuid"]])
        params.append(limit + 1)
        async with self._persistence.read_snapshot() as tx:
            rows = await tx.fetchall(
                "SELECT i.intake_item_uuid,i.normalized_external_key,i.lifecycle_state,i.row_revision,"
                "i.latest_revision_uuid,i.serving_revision_uuid,i.created_at,i.updated_at,s.source_kind "
                "FROM mkb_intake_items i JOIN mkb_intake_sources s "
                "ON s.team_uuid=i.team_uuid AND s.intake_source_uuid=i.intake_source_uuid WHERE "
                + " AND ".join(conditions)
                + " ORDER BY i.updated_at DESC,i.intake_item_uuid DESC LIMIT ?",
                tuple(params),
            )
        page = rows[:limit]
        views = [
            IntakeItemView(
                intake_item_uuid=row["intake_item_uuid"],
                external_key=row["normalized_external_key"],
                source_kind=row["source_kind"],
                lifecycle_state=row["lifecycle_state"],
                row_revision=int(row["row_revision"]),
                latest_revision_uuid=row["latest_revision_uuid"],
                serving_revision_uuid=row["serving_revision_uuid"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in page
        ]
        next_cursor = None
        if len(rows) > limit and page:
            next_cursor = self._encode_cursor(
                "items",
                filter_digest=filter_digest,
                updated_at=page[-1]["updated_at"],
                intake_item_uuid=page[-1]["intake_item_uuid"],
            )
        return views, next_cursor

    async def namespaces(
        self,
        team_uuid: str,
        *,
        status: str | None = "active",
        namespace_key: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[NamespaceView], str | None]:
        validate_external_uuid(team_uuid, field="team_uuid")
        if not 1 <= limit <= 100:
            raise MkbError("CATALOG_LIMIT_INVALID", "Catalog limit must be between 1 and 100", 422)
        if status is not None and status not in {"active", "disabled", "deleted"}:
            raise MkbError("CATALOG_FILTER_INVALID", "Namespace status filter is invalid", 422)
        conditions = ["team_uuid=?"]
        params: list[Any] = [team_uuid]
        if status is not None:
            conditions.append("status=?")
            params.append(status)
        if namespace_key is not None:
            if not namespace_key.strip():
                raise MkbError("CATALOG_FILTER_INVALID", "Namespace key filter is invalid", 422)
            conditions.append("namespace_key=?")
            params.append(namespace_key.strip())
        filter_digest = stable_digest({"team_uuid": team_uuid, "status": status, "namespace_key": namespace_key})
        if cursor:
            row = self._decode_cursor(cursor, "namespaces", filter_digest)
            conditions.append("(updated_at<? OR (updated_at=? AND namespace_uuid<?))")
            params.extend([row["updated_at"], row["updated_at"], row["namespace_uuid"]])
        params.append(limit + 1)
        async with self._persistence.read_snapshot() as tx:
            rows = await tx.fetchall(
                "SELECT namespace_uuid,namespace_key,embedding_model_key,embedding_model_version,dimension,status,updated_at "
                "FROM mkb_vector_namespaces WHERE "
                + " AND ".join(conditions)
                + " ORDER BY updated_at DESC,namespace_uuid DESC LIMIT ?",
                tuple(params),
            )
        page = rows[:limit]
        views = [
            NamespaceView(
                namespace_uuid=row["namespace_uuid"],
                namespace_key=row["namespace_key"],
                model_key=row["embedding_model_key"],
                model_version=row["embedding_model_version"],
                dimension=int(row["dimension"]),
                status=row["status"],
            )
            for row in page
        ]
        next_cursor = None
        if len(rows) > limit and page:
            next_cursor = self._encode_cursor(
                "namespaces",
                filter_digest=filter_digest,
                updated_at=rows[limit - 1]["updated_at"],
                namespace_uuid=rows[limit - 1]["namespace_uuid"],
            )
        return views, next_cursor

    @staticmethod
    def _encode_cursor(kind: str, **fields: Any) -> str:
        return base64.urlsafe_b64encode(
            json.dumps({"kind": kind, **fields}, sort_keys=True, separators=(",", ":")).encode()
        ).decode().rstrip("=")

    @staticmethod
    def _decode_cursor(cursor: str, kind: str, filter_digest: str) -> dict[str, Any]:
        try:
            padded = cursor + "=" * (-len(cursor) % 4)
            value = json.loads(base64.urlsafe_b64decode(padded.encode()))
        except (ValueError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError) as exc:
            raise MkbError("CATALOG_CURSOR_INVALID", "Catalog cursor is invalid", 422) from exc
        if (
            not isinstance(value, dict)
            or value.get("kind") != kind
            or value.get("filter_digest") != filter_digest
            or not isinstance(value.get("updated_at"), str)
        ):
            raise MkbError("CATALOG_CURSOR_INVALID", "Catalog cursor is invalid", 422)
        return value


__all__ = ["WorkflowCatalogService"]
