"""Closed operational signal, alert, and runbook registry (S15)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from types import MappingProxyType
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest


@dataclass(frozen=True, slots=True)
class OperationalSignalDefinition:
    signal_key: str
    severity: str
    emitter_key: str
    metric_name: str
    alert_id: str
    runbook_ref: str
    owner_component: str
    definition_version: str = "mkb.operational-signal.v1"

    def __post_init__(self) -> None:
        if self.severity not in {"info", "warn", "error", "critical"}:
            raise ValueError("signal severity is invalid")
        if not self.signal_key or not self.emitter_key or not self.metric_name or not self.alert_id:
            raise ValueError("signal coordinates are required")
        if not self.runbook_ref or not self.owner_component:
            raise ValueError("signal runbook and owner are required")

    @property
    def definition_digest(self) -> str:
        return stable_digest(asdict(self))


_DEFINITIONS = (
    OperationalSignalDefinition("outbox.dead", "critical", "workflow_outbox", "mkb_outbox_dead_total", "ALERT_OUTBOX_DEAD", "docs/runbooks/new-harvest/phase7-signals.md", "S12/S15"),
    OperationalSignalDefinition("readiness.false", "error", "health_aggregator", "mkb_readiness", "ALERT_READINESS_FALSE", "docs/runbooks/new-harvest/phase7-signals.md", "S15"),
    OperationalSignalDefinition("repair.failed", "error", "workflow_repair", "mkb_repair_applied_total", "ALERT_REPAIR_FAIL", "docs/runbooks/new-harvest/phase7-signals.md", "S03/S15"),
    OperationalSignalDefinition("diagnostic.drop", "warn", "diagnostic_sink", "mkb_diagnostic_drop_total", "ALERT_DIAG_DROP", "docs/runbooks/new-harvest/phase7-signals.md", "S15"),
    OperationalSignalDefinition("lease.stuck", "error", "workflow_supervisor", "mkb_lease_recover_total", "ALERT_LEASE_STUCK", "docs/runbooks/new-harvest/phase7-signals.md", "S12/S15"),
    OperationalSignalDefinition("retention.failed", "error", "observability_retention", "mkb_retention_job_fail_total", "ALERT_RETENTION_JOB_FAIL", "docs/runbooks/new-harvest/phase7-signals.md", "S15"),
    OperationalSignalDefinition("security.deny_spike", "critical", "security_audit", "mkb_sec_auth_total", "ALERT_SECURITY_DENY_SPIKE", "docs/runbooks/new-harvest/phase7-signals.md", "S16/S15"),
    OperationalSignalDefinition("security.rate_limiter_degraded", "critical", "security_limiter", "mkb_sec_rate_limiter_degraded", "ALERT_SEC_RATE_LIMITER_DEGRADED", "docs/runbooks/new-harvest/phase7-signals.md", "S16/S15"),
    OperationalSignalDefinition("security.token_reload_failed", "error", "security_tokens", "mkb_sec_token_reload_total", "ALERT_SEC_TOKEN_RELOAD_FAIL", "docs/runbooks/new-harvest/phase7-signals.md", "S16/S15"),
    OperationalSignalDefinition("security.audit_write_failed", "critical", "security_audit", "mkb_sec_audit_write_fail_total", "ALERT_SEC_AUDIT_WRITE_FAIL", "docs/runbooks/new-harvest/phase7-signals.md", "S16/S15"),
)

SIGNAL_DEFINITIONS = MappingProxyType({definition.signal_key: definition for definition in _DEFINITIONS})


class OperationalSignalRegistry:
    def __init__(self, definitions: Mapping[str, OperationalSignalDefinition] | None = None) -> None:
        self._definitions = MappingProxyType(dict(definitions or SIGNAL_DEFINITIONS))
        if len(self._definitions) != len(_DEFINITIONS):
            raise ValueError("operational signal definitions must be unique")

    @property
    def definitions(self) -> tuple[OperationalSignalDefinition, ...]:
        return tuple(self._definitions[key] for key in sorted(self._definitions))

    @property
    def definition_digest(self) -> str:
        return stable_digest([asdict(item) for item in self.definitions])

    def resolve(self, signal_key: str) -> OperationalSignalDefinition:
        definition = self._definitions.get(signal_key)
        if definition is None:
            raise MkbError("SIGNAL_UNKNOWN", "Operational signal is not registered", 503)
        return definition

    def emit(self, metrics: Any, signal_key: str, *, value: float = 1) -> None:
        definition = self.resolve(signal_key)
        metrics.increment("mkb_alert_raised_total", value, alert_id=definition.alert_id)

    def validate_metrics(self, metrics: Any) -> tuple[str, ...]:
        """Return signal metrics missing from the closed S15 catalogue."""

        return tuple(
            definition.metric_name
            for definition in self.definitions
            if not bool(getattr(metrics, "has_definition", lambda _name: False)(definition.metric_name))
        )


DEFAULT_SIGNAL_REGISTRY = OperationalSignalRegistry()


__all__ = ["DEFAULT_SIGNAL_REGISTRY", "OperationalSignalDefinition", "OperationalSignalRegistry", "SIGNAL_DEFINITIONS"]
