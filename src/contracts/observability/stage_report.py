"""Strict, dependency-free validator for NS4 generation stage reports.

Evidence lives in first-class columns / this typed bag. Prompt text, model
bodies, stdout, and original content are rejected. Contracts stay pure.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest

STAGE_REPORT_SCHEMA = "mkb.generation-stage-report.v1"
LAYER_COUNTS_SCHEMA = "mkb.layer-counts.v1"

STAGE_KEYS = frozenset({"markdown", "structurize", "construct"})
DISPOSITIONS = frozenset({"accepted", "rejected", "transport_failed"})
ADAPTER_KINDS = frozenset({"claude_cli", "local_inference"})
CLI_STRUCTURED_KINDS = frozenset(
    {"object", "list", "string", "empty_result", "missing", "null", "number", "bool", "other"}
)
FORBIDDEN_EVIDENCE_KEYS = frozenset(
    {
        "content",
        "prompt",
        "stdout",
        "stderr",
        "original",
        "original_content",
        "body",
        "clean",
        "candidate",
    }
)

_REPORT_KEYS = frozenset(
    {
        "schema",
        "stage_key",
        "disposition",
        "error_code",
        "cli_structured_kind",
        "has_g0",
        "block_count",
        "granularity_set",
        "layer_counts",
        "latency_ms",
        "schema_digest",
    }
)


class StageReportValidationError(MkbError):
    """Raised when a stage report or layer-count bag fails the NS4 contract."""

    def __init__(self, message: str) -> None:
        super().__init__("OBS_STAGE_REPORT_INVALID", message, 422)


def _reject_forbidden_keys(value: object, *, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            name = str(key)
            lowered = name.lower()
            if lowered in FORBIDDEN_EVIDENCE_KEYS or any(
                token in lowered for token in ("prompt", "stdout", "original")
            ):
                raise StageReportValidationError(f"{path}.{name} is forbidden on the evidence plane")
            _reject_forbidden_keys(item, path=f"{path}.{name}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_forbidden_keys(item, path=f"{path}[{index}]")


def validate_layer_counts(value: object) -> dict[str, int]:
    """Accept only a granularity→count map. Reject text and unknown keys."""

    if not isinstance(value, Mapping):
        raise StageReportValidationError("layer_counts must be an object")
    _reject_forbidden_keys(value, path="layer_counts")
    counts: dict[str, int] = {}
    for key, raw in value.items():
        name = str(key)
        if name in {"schema"}:
            if raw not in {None, LAYER_COUNTS_SCHEMA}:
                raise StageReportValidationError("layer_counts.schema is not the registered digest schema")
            continue
        if not name.isdigit() or int(name) < 0:
            raise StageReportValidationError(f"layer_counts key {name!r} is not a granularity")
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
            raise StageReportValidationError(f"layer_counts[{name}] must be a non-negative int")
        counts[name] = raw
    return counts


def layer_counts_digest(counts: Mapping[str, int]) -> str:
    return stable_digest({"schema": LAYER_COUNTS_SCHEMA, "counts": dict(sorted(counts.items()))})


def validate_stage_report(value: object) -> dict[str, Any]:
    """Validate and project a redacted stage-report payload."""

    if not isinstance(value, Mapping):
        raise StageReportValidationError("stage report must be an object")
    extra = set(value) - _REPORT_KEYS
    if extra:
        raise StageReportValidationError(f"stage report has unknown keys: {sorted(extra)}")
    _reject_forbidden_keys(value)

    schema = value.get("schema", STAGE_REPORT_SCHEMA)
    if schema != STAGE_REPORT_SCHEMA:
        raise StageReportValidationError("stage report schema is not registered")

    stage_key = value.get("stage_key")
    if stage_key not in STAGE_KEYS:
        raise StageReportValidationError("stage_key is not in the closed set")

    disposition = value.get("disposition")
    if disposition not in DISPOSITIONS:
        raise StageReportValidationError("disposition is not in the closed set")

    error_code = value.get("error_code")
    if disposition in {"rejected", "transport_failed"}:
        if not isinstance(error_code, str) or not error_code.strip():
            raise StageReportValidationError("error_code is required when disposition is not accepted")
    elif error_code is not None and not isinstance(error_code, str):
        raise StageReportValidationError("error_code must be a string when present")

    kind = value.get("cli_structured_kind")
    if kind is not None and kind not in CLI_STRUCTURED_KINDS:
        raise StageReportValidationError("cli_structured_kind is not in the closed set")

    has_g0 = value.get("has_g0")
    if has_g0 is not None and not isinstance(has_g0, bool):
        raise StageReportValidationError("has_g0 must be a bool when present")

    block_count = value.get("block_count")
    if block_count is not None and (isinstance(block_count, bool) or not isinstance(block_count, int) or block_count < 0):
        raise StageReportValidationError("block_count must be a non-negative int")

    granularity_set = value.get("granularity_set")
    if granularity_set is not None:
        if not isinstance(granularity_set, str) or not all(
            part.isdigit() for part in granularity_set.split(",") if part
        ):
            raise StageReportValidationError("granularity_set must be a comma-sorted digit list")

    raw_counts = value.get("layer_counts")
    counts = validate_layer_counts(raw_counts) if raw_counts is not None else {}

    latency_ms = value.get("latency_ms")
    if isinstance(latency_ms, bool) or not isinstance(latency_ms, int) or latency_ms < 0:
        raise StageReportValidationError("latency_ms must be a non-negative int")

    projected = {
        "schema": STAGE_REPORT_SCHEMA,
        "stage_key": stage_key,
        "disposition": disposition,
        "error_code": error_code,
        "cli_structured_kind": kind,
        "has_g0": has_g0,
        "block_count": block_count,
        "granularity_set": granularity_set,
        "layer_counts": counts,
        "latency_ms": latency_ms,
    }
    digest = layer_counts_digest(counts) if counts else stable_digest({"schema": STAGE_REPORT_SCHEMA, "empty": True})
    given = value.get("schema_digest")
    if given is not None and given != digest:
        raise StageReportValidationError("schema_digest does not match the registered layer-count bag")
    projected["schema_digest"] = digest
    return projected
