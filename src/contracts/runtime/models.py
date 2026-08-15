"""Typed commands and outcomes between the workflow runtime and services."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field, field_validator

from src.contracts.common.ids import validate_external_uuid
from src.contracts.common.models import ExecutionStatus, PayloadExtraModel, ProcessStatus


class ProcessCommand(PayloadExtraModel):
    schema_version: Literal["mkb.process-command.v1"]
    team_uuid: str
    task_uuid: str
    trace_uuid: str
    execution_uuid: str
    process_uuid: str
    process_key: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_.-]{0,127}$")]
    process_contract_version: Annotated[str, Field(min_length=1, max_length=128)]
    fencing_generation: Annotated[int, Field(ge=1)]
    command_input_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    input_manifest_ref: Annotated[str, Field(min_length=1, max_length=1024)]
    input_manifest_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    config_snapshot_ref: Annotated[str, Field(min_length=1, max_length=1024)]
    config_snapshot_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    binding_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    dispatch_pool: Literal["local-inference", "non-interactive", "embed"] | None = None
    task_priority: Literal["low", "normal", "high", "urgent"] | None = None

    @field_validator("team_uuid", "task_uuid", "trace_uuid", "execution_uuid", "process_uuid")
    @classmethod
    def validate_ids(cls, value: str, info: Any) -> str:
        return validate_external_uuid(value, field=info.field_name)


class ProcessOutcome(PayloadExtraModel):
    schema_version: Literal["mkb.process-outcome.v1"]
    team_uuid: str
    task_uuid: str
    execution_uuid: str
    process_uuid: str
    fencing_generation: Annotated[int, Field(ge=1)]
    disposition: Literal["succeeded", "failed", "retryable_failure", "waiting"]
    outcome_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    output_manifest_ref: str | None = None
    output_manifest_digest: Annotated[str | None, Field(pattern=r"^[0-9a-f]{64}$")] = None
    proof_ref: str | None = None
    proof_digest: Annotated[str | None, Field(pattern=r"^[0-9a-f]{64}$")] = None
    error_code: Annotated[str | None, Field(max_length=128)] = None
    error_message: Annotated[str | None, Field(max_length=512)] = None

    @field_validator("team_uuid", "task_uuid", "execution_uuid", "process_uuid")
    @classmethod
    def validate_ids(cls, value: str, info: Any) -> str:
        return validate_external_uuid(value, field=info.field_name)


class Claim(ProcessCommand):
    lease_owner: Annotated[str, Field(min_length=1, max_length=256)]
    lease_seconds: Annotated[int, Field(ge=1, le=3600)]


__all__ = ["Claim", "ProcessCommand", "ProcessOutcome", "ExecutionStatus", "ProcessStatus"]
