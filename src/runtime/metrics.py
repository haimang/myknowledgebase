"""Low-cardinality Prometheus exposition with a closed metric catalogue.

Metrics are an in-process observation surface, never an extensible telemetry
database.  Keeping the catalogue and each label value bounded here means a
call-site mistake cannot turn a task UUID, URL, or other caller input into an
unbounded Prometheus series.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from types import MappingProxyType

_FORBIDDEN_LABELS = frozenset(
    {"task_uuid", "trace_uuid", "execution_uuid", "process_uuid", "team_uuid", "user_id", "url", "path"}
)

_READINESS_COMPONENTS = frozenset(
    {
        "schema_migration",
        "registry_bootstrap",
        "db_primary",
        "concurrent_writes",
        "native_vector",
        "object_root",
        "inference_binding",
        "obs_tables",
        "sec_token_loaded",
    }
)
_OUTBOX_KINDS = frozenset({"wake_execution", "wake_process", "cancel_execution", "gate_decision"})
_CAPABILITIES = frozenset({"embed", "rerank", "structured_generate", "text_generate"})
_COMMON_RESULTS = frozenset({"success", "conflict", "error", "ok", "noop", "fail"})
_OBS_TABLES = frozenset(
    {"mkb_domain_events", "mkb_ops_diagnostic_logs", "mkb_security_audit_events"}
)


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    """One statically reviewed Prometheus family and its label allowlists."""

    name: str
    kind: str
    labels: frozenset[str] = frozenset()
    allowed_values: tuple[tuple[str, frozenset[str]], ...] = ()

    def allows(self, labels: dict[str, str]) -> bool:
        if frozenset(labels) != self.labels:
            return False
        allowed = dict(self.allowed_values)
        for key, value in labels.items():
            if not isinstance(value, str) or len(value) > 64 or value not in allowed.get(key, frozenset()):
                return False
        return True


def _metric(
    name: str,
    kind: str,
    *,
    labels: tuple[str, ...] = (),
    allowed: dict[str, frozenset[str]] | None = None,
) -> MetricDefinition:
    return MetricDefinition(
        name=name,
        kind=kind,
        labels=frozenset(labels),
        allowed_values=tuple(sorted((allowed or {}).items())),
    )


# S15-E03 is deliberately a code-owned closed catalogue.  New series require
# a reviewed change here rather than a runtime ``register`` call.
_METRIC_CATALOG = MappingProxyType(
    {
        "mkb_process_claim_total": _metric(
            "mkb_process_claim_total", "counter", labels=("result",), allowed={"result": _COMMON_RESULTS}
        ),
        "mkb_process_running": _metric("mkb_process_running", "gauge"),
        "mkb_outbox_depth": _metric(
            "mkb_outbox_depth", "gauge", labels=("kind",), allowed={"kind": _OUTBOX_KINDS}
        ),
        "mkb_outbox_dead_total": _metric(
            "mkb_outbox_dead_total", "gauge", labels=("kind",), allowed={"kind": _OUTBOX_KINDS}
        ),
        "mkb_outbox_dead_oldest_age_seconds": _metric("mkb_outbox_dead_oldest_age_seconds", "gauge"),
        "mkb_readiness": _metric(
            "mkb_readiness", "gauge", labels=("component",), allowed={"component": _READINESS_COMPONENTS}
        ),
        "mkb_repair_applied_total": _metric(
            "mkb_repair_applied_total", "counter", labels=("outcome",), allowed={"outcome": frozenset({"ok", "noop", "fail"})}
        ),
        "mkb_diagnostic_drop_total": _metric(
            "mkb_diagnostic_drop_total",
            "counter",
            labels=("reason",),
            allowed={"reason": frozenset({"append_fail", "invalid_entry", "stderr_fail"})},
        ),
        "mkb_diagnostic_missing_trace_ratio": _metric("mkb_diagnostic_missing_trace_ratio", "gauge"),
        "mkb_inference_requests_total": _metric(
            "mkb_inference_requests_total",
            "counter",
            labels=("capability", "result"),
            allowed={"capability": _CAPABILITIES, "result": _COMMON_RESULTS},
        ),
        "mkb_inference_duration_seconds": _metric(
            "mkb_inference_duration_seconds", "histogram", labels=("capability",), allowed={"capability": _CAPABILITIES}
        ),
        "mkb_vector_upsert_total": _metric(
            "mkb_vector_upsert_total", "counter", labels=("result",), allowed={"result": _COMMON_RESULTS}
        ),
        "mkb_index_generation_active": _metric(
            "mkb_index_generation_active",
            "gauge",
            labels=("status",),
            allowed={"status": frozenset({"active", "candidate", "rebuilding", "failed", "none"})},
        ),
        "mkb_worker_queue_lag_seconds": _metric("mkb_worker_queue_lag_seconds", "gauge"),
        # v1's portable profile has no declared GPU-device inventory, so it
        # emits one aggregate ratio or omits the series altogether.
        "mkb_gpu_util_ratio": _metric("mkb_gpu_util_ratio", "gauge"),
        "mkb_registry_resolve_total": _metric(
            "mkb_registry_resolve_total", "counter", labels=("result",), allowed={"result": _COMMON_RESULTS}
        ),
        "mkb_prompt_hash_mismatch_total": _metric("mkb_prompt_hash_mismatch_total", "counter"),
        "mkb_registry_bootstrap_fail_total": _metric("mkb_registry_bootstrap_fail_total", "counter"),
        "mkb_config_override_rejected_total": _metric("mkb_config_override_rejected_total", "counter"),
        "mkb_config_ops_reload_total": _metric(
            "mkb_config_ops_reload_total", "counter", labels=("result",), allowed={"result": frozenset({"ok", "fail"})}
        ),
        "mkb_sec_auth_total": _metric(
            "mkb_sec_auth_total", "counter", labels=("result",), allowed={"result": frozenset({"missing", "invalid", "ok"})}
        ),
        "mkb_sec_rate_limited_total": _metric(
            "mkb_sec_rate_limited_total", "counter", labels=("dim",), allowed={"dim": frozenset({"token", "ip"})}
        ),
        "mkb_sec_rate_limiter_degraded": _metric("mkb_sec_rate_limiter_degraded", "gauge"),
        "mkb_sec_egress_denied_total": _metric(
            "mkb_sec_egress_denied_total", "counter", labels=("reason",), allowed={"reason": frozenset({"policy", "redirect"})}
        ),
        "mkb_sec_secret_unresolved_total": _metric("mkb_sec_secret_unresolved_total", "counter"),
        "mkb_sec_audit_write_fail_total": _metric("mkb_sec_audit_write_fail_total", "counter"),
        "mkb_sec_token_reload_total": _metric(
            "mkb_sec_token_reload_total", "counter", labels=("result",), allowed={"result": frozenset({"ok", "fail", "last_good"})}
        ),
        "mkb_sec_supply_reject_total": _metric(
            "mkb_sec_supply_reject_total",
            "counter",
            labels=("code",),
            allowed={
                "code": frozenset(
                    {"SEC_SUPPLY_UNBOUND", "SEC_SUPPLY_DIGEST_MISMATCH", "SEC_SUPPLY_SIGNATURE_INVALID"}
                )
            },
        ),
        "mkb_retention_delete_rows_total": _metric(
            "mkb_retention_delete_rows_total", "counter", labels=("table",), allowed={"table": _OBS_TABLES}
        ),
        "mkb_retention_job_success": _metric("mkb_retention_job_success", "gauge"),
        "mkb_retention_job_fail_total": _metric("mkb_retention_job_fail_total", "counter"),
        "mkb_metric_cardinality_drop_total": _metric(
            "mkb_metric_cardinality_drop_total",
            "counter",
            labels=("reason",),
            allowed={"reason": frozenset({"invalid_label", "unknown_metric", "label_keys", "label_value"})},
        ),
        "mkb_backup_last_success_unixtime": _metric("mkb_backup_last_success_unixtime", "gauge"),
        "mkb_backup_fail_total": _metric("mkb_backup_fail_total", "counter"),
        "mkb_alert_raised_total": _metric(
            "mkb_alert_raised_total",
            "counter",
            labels=("alert_id",),
            allowed={
                "alert_id": frozenset(
                    {
                        "ALERT_OUTBOX_DEAD",
                        "ALERT_READINESS_FALSE",
                        "ALERT_REPAIR_FAIL",
                        "ALERT_DIAG_DROP",
                        "ALERT_LEASE_STUCK",
                        "ALERT_RETENTION_JOB_FAIL",
                        "ALERT_SECURITY_DENY_SPIKE",
                        "ALERT_SEC_RATE_LIMITER_DEGRADED",
                        "ALERT_SEC_TOKEN_RELOAD_FAIL",
                        "ALERT_SEC_AUDIT_WRITE_FAIL",
                    }
                )
            },
        ),
        "mkb_lease_recover_total": _metric(
            "mkb_lease_recover_total", "counter", labels=("outcome",), allowed={"outcome": _COMMON_RESULTS}
        ),
        "mkb_gc_orphans_deleted_total": _metric("mkb_gc_orphans_deleted_total", "counter"),
        "mkb_gc_fail_total": _metric("mkb_gc_fail_total", "counter"),
    }
)


class MetricRegistry:
    """Closed metric registry that drops invalid samples instead of exploding series."""

    def __init__(self) -> None:
        self._definitions: dict[str, MetricDefinition] = dict(_METRIC_CATALOG)
        self._values: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self.cardinality_drops = 0

    def register(self, name: str, kind: str, labels: tuple[str, ...] = ()) -> None:
        """Validate an idempotent catalogue declaration; reject ad-hoc metrics."""

        definition = _METRIC_CATALOG.get(name)
        if definition is None or definition.kind != kind or definition.labels != frozenset(labels):
            raise ValueError("metric is not part of the static S15 catalogue")

    def set(self, name: str, value: float, **labels: str) -> None:
        self._write(name, value, labels, replace=True)

    def increment(self, name: str, value: float = 1, **labels: str) -> None:
        self._write(name, value, labels, replace=False)

    def _write(self, name: str, value: float, labels: dict[str, str], *, replace: bool) -> None:
        definition = self._definitions.get(name)
        if definition is None:
            self._drop()
            return
        if frozenset(labels) != definition.labels:
            self._drop()
            return
        if not definition.allows(labels):
            self._drop()
            return
        key = (name, tuple(sorted(labels.items())))
        if replace:
            self._values[key] = value
        else:
            self._values[key] += value

    def _drop(self) -> None:
        # Keep the compatibility scalar consumed by the HTTP scrape adapter;
        # it batches the fixed, permitted ``invalid_label`` sample rather than
        # recursively creating one series per rejected caller value.
        self.cardinality_drops += 1

    def render(self) -> str:
        lines: list[str] = []
        for name, definition in sorted(self._definitions.items()):
            lines.append(f"# TYPE {name} {definition.kind}")
            for (metric_name, labels), value in sorted(self._values.items()):
                if metric_name != name:
                    continue
                rendered_labels = ""
                if labels:
                    rendered_labels = "{" + ",".join(f'{key}="{value}"' for key, value in labels) + "}"
                lines.append(f"{name}{rendered_labels} {value}")
        return "\n".join(lines) + "\n"


def default_metrics() -> MetricRegistry:
    """Return the one closed S15 catalogue with no runtime extensions."""

    return MetricRegistry()


__all__ = ["MetricDefinition", "MetricRegistry", "default_metrics"]
