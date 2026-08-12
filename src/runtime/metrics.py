"""Low-cardinality Prometheus exposition with an explicit metric registry."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

_FORBIDDEN_LABELS = {"task_uuid", "trace_uuid", "execution_uuid", "process_uuid", "team_uuid", "url", "path"}


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    name: str
    kind: str
    labels: frozenset[str] = frozenset()


class MetricRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, MetricDefinition] = {}
        self._values: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self.cardinality_drops = 0

    def register(self, name: str, kind: str, labels: tuple[str, ...] = ()) -> None:
        if not name.startswith("mkb_") or set(labels) & _FORBIDDEN_LABELS:
            raise ValueError("metric uses an invalid name or high-cardinality label")
        definition = MetricDefinition(name, kind, frozenset(labels))
        existing = self._definitions.get(name)
        if existing is not None and existing != definition:
            raise ValueError(f"metric {name} registered inconsistently")
        self._definitions[name] = definition

    def set(self, name: str, value: float, **labels: str) -> None:
        self._write(name, value, labels, replace=True)

    def increment(self, name: str, value: float = 1, **labels: str) -> None:
        self._write(name, value, labels, replace=False)

    def _write(self, name: str, value: float, labels: dict[str, str], *, replace: bool) -> None:
        definition = self._definitions.get(name)
        if definition is None or frozenset(labels) != definition.labels:
            self.cardinality_drops += 1
            return
        key = (name, tuple(sorted(labels.items())))
        if replace:
            self._values[key] = value
        else:
            self._values[key] += value

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
    registry = MetricRegistry()
    registry.register("mkb_readiness", "gauge", ("component",))
    registry.register("mkb_sec_auth_total", "counter", ("result",))
    registry.register("mkb_sec_rate_limited_total", "counter", ("dim",))
    registry.register("mkb_sec_rate_limiter_degraded", "gauge")
    registry.register("mkb_sec_audit_write_fail_total", "counter")
    registry.register("mkb_metric_cardinality_drop_total", "counter")
    return registry
