"""Code-owned ProcessCapabilityManifest and deployment availability.

Workflow rows contain the program, while this registry contains the reviewed
interpreter contract for every required process.  It is intentionally a
closed set: a workflow or operator cannot invent a process key at runtime.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from types import MappingProxyType
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest
from src.contracts.workflow.models import WorkflowDefinition
from src.runtime.roles import DeploymentRole
from src.runtime.supply.identities import SUPPLY_BY_CAPABILITY
from src.workflows.builtin_lsrag import BUILTIN_WORKFLOWS
from src.workflows.builtin_scatter import BUILTIN_SCATTER_WORKFLOWS

_BROWSER_RENDER = ("browser.render",)
_BROWSER_PRINT = ("browser.print_pdf",)
_BROWSER_ALL = ("browser.render", "browser.print_pdf")
_PDF_PARSE = ("pdf.parse",)
_OCR = ("ocr.deterministic",)
_MULTIMODAL = ("s11.multimodal",)


@dataclass(frozen=True, slots=True)
class ProcessCapabilityManifest:
    """The immutable contract required to claim one Process key."""

    process_key: str
    contract_version: str
    handler_key: str
    deployment_roles: tuple[str, ...]
    supply_requirements: tuple[str, ...]
    side_effect_class: str
    replay_law: str
    idempotency_key_recipe: str
    allowed_phase_keys: tuple[str, ...] = ()
    outcome_schema_ref: str = "mkb.process-outcome.v1"
    proof_kind: str = "mkb.stage-proof.v1"

    def __post_init__(self) -> None:
        if not self.process_key or not self.contract_version or not self.handler_key:
            raise ValueError("process capability coordinates are required")
        if not self.deployment_roles:
            raise ValueError("process capability must have a deployment role")
        unknown_roles = set(self.deployment_roles) - {role.value for role in DeploymentRole}
        if unknown_roles:
            raise ValueError(f"unknown deployment roles: {sorted(unknown_roles)}")
        unknown_supply = set(self.supply_requirements) - set(SUPPLY_BY_CAPABILITY)
        if unknown_supply:
            raise ValueError(f"unknown runtime supplies: {sorted(unknown_supply)}")
        if self.side_effect_class not in {
            "pure",
            "durable_idempotent",
            "external_idempotent",
            "external_nonrepeatable",
        }:
            raise ValueError("unknown process side-effect class")
        if self.replay_law not in {"recompute", "frozen_input", "effect_once", "verify_then_retry"}:
            raise ValueError("unknown process replay law")

    @property
    def definition_digest(self) -> str:
        return stable_digest(self.as_dict())

    def as_dict(self) -> dict[str, Any]:
        return asdict(self) | {"definition_digest": self.definition_digest_without_self()}

    def definition_digest_without_self(self) -> str:
        return stable_digest(
            {
                "process_key": self.process_key,
                "contract_version": self.contract_version,
                "handler_key": self.handler_key,
                "deployment_roles": self.deployment_roles,
                "supply_requirements": self.supply_requirements,
                "side_effect_class": self.side_effect_class,
                "replay_law": self.replay_law,
                "idempotency_key_recipe": self.idempotency_key_recipe,
                "allowed_phase_keys": self.allowed_phase_keys,
                "outcome_schema_ref": self.outcome_schema_ref,
                "proof_kind": self.proof_kind,
            }
        )


def _supply_for(process_key: str) -> tuple[str, ...]:
    if process_key == "intake.acquire.http_browser":
        return _BROWSER_ALL
    if process_key == "intake.acquire.http_static":
        return ()
    if process_key == "intake.decode.pdf":
        return _PDF_PARSE
    if process_key == "clean.ocr.local":
        return _OCR
    if process_key in {"clean.extract.vision", "clean.extract.web_llm", "clean.extract.pdf_llm", "clean.extract.doc_llm"}:
        return _MULTIMODAL
    if process_key == "index.validate_publication":
        return ()
    return ()


def _side_effect_for(process_key: str) -> tuple[str, str]:
    if process_key.startswith("intake.acquire.http") or process_key == "intake.acquire.registered_api":
        return "external_idempotent", "frozen_input"
    if process_key in {"intake.acquire.inline", "intake.acquire.local_object", "intake.decode.text_json_html", "intake.decode.pdf"}:
        return "pure", "recompute"
    if process_key in {"clean.extract.web_llm", "clean.extract.pdf_llm", "clean.extract.doc_llm", "clean.extract.vision"}:
        return "external_idempotent", "frozen_input"
    if process_key in {"clean.extract.deterministic", "clean.ocr.local", "clean.map.registered_api"}:
        return "durable_idempotent", "recompute"
    if process_key in {"intake.collection.seal", "intake.preflight_validate", "intake.accept_snapshot", "intake.metadata_no_change"}:
        return "durable_idempotent", "effect_once"
    if process_key == "intake.replay_frozen_clean":
        return "durable_idempotent", "frozen_input"
    if process_key in {"lsrag.vectorize", "lsrag.construct", "lsrag.transcribe_markdown"}:
        return "external_idempotent", "verify_then_retry"
    if process_key in {"index.rebuild", "index.validate_publication", "intake.physical_purge"}:
        return "durable_idempotent", "effect_once"
    if process_key in {"lsrag.structurize"}:
        return "durable_idempotent", "recompute"
    return "durable_idempotent", "effect_once"


def _build_manifests() -> dict[str, ProcessCapabilityManifest]:
    definitions: dict[str, ProcessCapabilityManifest] = {}
    workflows: Iterable[WorkflowDefinition] = (*BUILTIN_WORKFLOWS, *BUILTIN_SCATTER_WORKFLOWS)
    for workflow in workflows:
        for process_key in workflow.required_process_keys:
            side_effect, replay_law = _side_effect_for(process_key)
            definitions.setdefault(
                process_key,
                ProcessCapabilityManifest(
                    process_key=process_key,
                    contract_version="v2",
                    handler_key="intake_pipeline",
                    deployment_roles=(DeploymentRole.WORKFLOW_WORKER.value, DeploymentRole.ALL.value),
                    supply_requirements=_supply_for(process_key),
                    side_effect_class=side_effect,
                    replay_law=replay_law,
                    idempotency_key_recipe="team_uuid:execution_uuid:process_uuid:fencing_generation",
                ),
            )
    return definitions


PROCESS_CAPABILITY_MANIFESTS = MappingProxyType(_build_manifests())


class ProcessCapabilityRegistry:
    """Resolve and validate the closed process manifest set."""

    def __init__(self, manifests: Mapping[str, ProcessCapabilityManifest] | None = None) -> None:
        self._manifests = MappingProxyType(dict(manifests or PROCESS_CAPABILITY_MANIFESTS))
        if not self._manifests:
            raise ValueError("process capability registry cannot be empty")

    @property
    def manifests(self) -> tuple[ProcessCapabilityManifest, ...]:
        return tuple(self._manifests[key] for key in sorted(self._manifests))

    @property
    def definition_digest(self) -> str:
        return stable_digest([manifest.as_dict() for manifest in self.manifests])

    def resolve(self, process_key: str, contract_version: str = "v2") -> ProcessCapabilityManifest:
        manifest = self._manifests.get(process_key)
        if manifest is None or manifest.contract_version != contract_version:
            raise MkbError("CAPABILITY_UNKNOWN", "Process capability is not registered", 503)
        return manifest

    def validate_workflow(self, definition: WorkflowDefinition) -> tuple[ProcessCapabilityManifest, ...]:
        return tuple(self.resolve(key) for key in definition.required_process_keys)

    def required_for(self, definitions: Iterable[WorkflowDefinition]) -> tuple[ProcessCapabilityManifest, ...]:
        keys = sorted({key for definition in definitions for key in definition.required_process_keys})
        return tuple(self.resolve(key) for key in keys)

    def claimable_process_keys(
        self,
        role: DeploymentRole | str,
        *,
        available_supplies: Mapping[str, bool] | None = None,
    ) -> frozenset[str]:
        role_value = role.value if isinstance(role, DeploymentRole) else str(role)
        available = available_supplies or {}
        result: set[str] = set()
        for manifest in self.manifests:
            if role_value not in manifest.deployment_roles:
                continue
            if all(available.get(supply, True) for supply in manifest.supply_requirements):
                result.add(manifest.process_key)
        return frozenset(result)

    def availability(self, available_supplies: Mapping[str, bool]) -> tuple[dict[str, Any], ...]:
        return tuple(
            {
                "process_key": manifest.process_key,
                "contract_version": manifest.contract_version,
                "definition_digest": manifest.definition_digest,
                "deployment_roles": manifest.deployment_roles,
                "supply_requirements": manifest.supply_requirements,
                "available": all(available_supplies.get(key, False) for key in manifest.supply_requirements),
                "missing_supplies": tuple(
                    key for key in manifest.supply_requirements if not available_supplies.get(key, False)
                ),
            }
            for manifest in self.manifests
        )

    async def bootstrap(self, persistence: Any) -> None:
        """Project this code registry into the durable ops table idempotently."""

        from src.contracts.common.time import utc_now

        async with persistence.transaction() as tx:
            for manifest in self.manifests:
                existing = await tx.fetchone(
                    "SELECT definition_digest FROM mkb_process_capability_definitions WHERE process_key=? AND contract_version=?",
                    (manifest.process_key, manifest.contract_version),
                )
                if existing is not None:
                    if existing["definition_digest"] != manifest.definition_digest:
                        raise MkbError("REGISTRY_DIGEST_MISMATCH", "Process capability definition conflicts", 503)
                    continue
                await tx.execute(
                    "INSERT INTO mkb_process_capability_definitions(process_key,contract_version,definition_digest,handler_key,"
                    "deployment_roles_json,supply_requirements_json,side_effect_class,replay_law,registered_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        manifest.process_key,
                        manifest.contract_version,
                        manifest.definition_digest,
                        manifest.handler_key,
                        json.dumps(manifest.deployment_roles, separators=(",", ":")),
                        json.dumps(manifest.supply_requirements, separators=(",", ":")),
                        manifest.side_effect_class,
                        manifest.replay_law,
                        utc_now(),
                    ),
                )

    async def readiness(self, persistence: Any) -> bool:
        async with persistence.read_snapshot() as tx:
            rows = await tx.fetchall(
                "SELECT process_key,contract_version,definition_digest,status FROM mkb_process_capability_definitions"
            )
        expected = {
            (manifest.process_key, manifest.contract_version, manifest.definition_digest, "active")
            for manifest in self.manifests
        }
        observed = {(row["process_key"], row["contract_version"], row["definition_digest"], row["status"]) for row in rows}
        return observed == expected


DEFAULT_PROCESS_CAPABILITY_REGISTRY = ProcessCapabilityRegistry()


__all__ = [
    "DEFAULT_PROCESS_CAPABILITY_REGISTRY",
    "PROCESS_CAPABILITY_MANIFESTS",
    "ProcessCapabilityManifest",
    "ProcessCapabilityRegistry",
]
