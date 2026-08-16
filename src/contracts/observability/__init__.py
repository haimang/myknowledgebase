"""NS4 generation-evidence contracts. Pure: no persistence or runtime I/O."""

from src.contracts.observability.stage_report import (
    ADAPTER_KINDS,
    CLI_STRUCTURED_KINDS,
    FORBIDDEN_EVIDENCE_KEYS,
    LAYER_COUNTS_SCHEMA,
    STAGE_KEYS,
    STAGE_REPORT_SCHEMA,
    StageReportValidationError,
    layer_counts_digest,
    validate_layer_counts,
    validate_stage_report,
)

__all__ = [
    "ADAPTER_KINDS",
    "CLI_STRUCTURED_KINDS",
    "FORBIDDEN_EVIDENCE_KEYS",
    "LAYER_COUNTS_SCHEMA",
    "STAGE_KEYS",
    "STAGE_REPORT_SCHEMA",
    "StageReportValidationError",
    "layer_counts_digest",
    "validate_layer_counts",
    "validate_stage_report",
]
