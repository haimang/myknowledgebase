"""Explicit deployment-role ownership for the single MKB binary.

The workflow ``execution_role`` stored on a durable Execution answers a
different question from this module: deployment roles describe which loops a
process is authorised to own.  Keeping that distinction in one small,
code-owned registry lets readiness and the lifespan use the same truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DeploymentRole(StrEnum):
    API = "api"
    WORKFLOW_WORKER = "workflow_worker"
    MAINTENANCE = "maintenance"
    ALL = "all"


@dataclass(frozen=True, slots=True)
class DeploymentRoleSpec:
    role: DeploymentRole
    owns_api: bool
    owns_workflow_claims: bool
    owns_maintenance: bool
    owns_retention: bool

    @property
    def loop_names(self) -> tuple[str, ...]:
        loops: list[str] = []
        if self.owns_workflow_claims:
            loops.append("workflow_supervisor")
        if self.owns_maintenance:
            loops.extend(("object_gc", "object_upload_lifecycle", "index_retirement"))
        if self.owns_retention:
            loops.append("observability_retention")
        return tuple(loops)


ROLE_SPECS: dict[DeploymentRole, DeploymentRoleSpec] = {
    DeploymentRole.API: DeploymentRoleSpec(DeploymentRole.API, True, False, False, False),
    DeploymentRole.WORKFLOW_WORKER: DeploymentRoleSpec(DeploymentRole.WORKFLOW_WORKER, False, True, False, False),
    DeploymentRole.MAINTENANCE: DeploymentRoleSpec(DeploymentRole.MAINTENANCE, False, False, True, True),
    DeploymentRole.ALL: DeploymentRoleSpec(DeploymentRole.ALL, True, True, True, True),
}


def role_spec(value: DeploymentRole | str) -> DeploymentRoleSpec:
    """Resolve a configured role without accepting workflow execution roles."""

    try:
        role = value if isinstance(value, DeploymentRole) else DeploymentRole(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("deployment_role must be api, workflow_worker, maintenance, or all") from exc
    return ROLE_SPECS[role]


def role_loop_enabled(value: DeploymentRole | str, loop_name: str) -> bool:
    """Return whether ``loop_name`` belongs to the configured deployment role."""

    return loop_name in role_spec(value).loop_names


__all__ = ["DeploymentRole", "DeploymentRoleSpec", "ROLE_SPECS", "role_loop_enabled", "role_spec"]
