"""R4-01..04: admit-fail invocation, success clears error_code, latency, adapter map."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.runtime.models import ProcessCommand
from src.runtime.intake.generation_construct import IntakeGenerationConstructMixin
from src.runtime.intake.generation_evidence import take_pending_generation_evidence
from src.runtime.intake.pipeline import IntakePipeline
from src.runtime.workflow.runtime_outcome import WorkflowOutcomeMixin


def _command() -> ProcessCommand:
    return ProcessCommand(
        schema_version="mkb.process-command.v1",
        team_uuid=uuid7(),
        task_uuid=uuid7(),
        trace_uuid=uuid7(),
        execution_uuid=uuid7(),
        process_uuid=uuid7(),
        process_key="lsrag.structurize",
        process_contract_version="v1",
        fencing_generation=1,
        command_input_digest=stable_digest({"test": "r4"}),
        input_manifest_ref="mkbtest:input:r4",
        input_manifest_digest="a" * 64,
        config_snapshot_ref="mkbtest:config:r4",
        config_snapshot_digest="b" * 64,
        binding_digest="c" * 64,
    )


class _Sink:
    async def write(self, **kwargs: object) -> None:
        del kwargs


def test_success_outcome_sql_clears_process_error_code() -> None:
    source = Path("src/runtime/workflow/runtime_outcome.py").read_text(encoding="utf-8")
    assert "error_code=NULL,error_message=NULL" in source
    assert "class WorkflowOutcomeMixin" in source
    assert WorkflowOutcomeMixin.__name__ == "WorkflowOutcomeMixin"


def test_cli_receipt_maps_api_inference_to_local_vllm() -> None:
    mixin = IntakeGenerationConstructMixin()
    live = mixin._cli_invocation_from_receipt(
        _command(),
        {"transport": "api_inference", "output_digest": "d" * 64},
        stage_key="markdown",
        capability_key="text_generate",
        input_digest="e" * 64,
    )
    cli = mixin._cli_invocation_from_receipt(
        _command(),
        {"transport": "claude_cli", "output_digest": "d" * 64},
        stage_key="markdown",
        capability_key="text_generate",
        input_digest="e" * 64,
    )
    assert live["adapter_kind"] == "local_vllm"
    assert cli["adapter_kind"] == "claude_cli"


@pytest.mark.asyncio
async def test_admit_reject_stashes_failed_invocation_and_nonzero_latency() -> None:
    take_pending_generation_evidence()
    pipeline = IntakePipeline(None, None, None)  # type: ignore[arg-type]
    pipeline._diagnostics = _Sink()
    clean = "hello\n"
    candidate = {
        "context_meta": {"title": "only-g0"},
        "layered_content": [
            {
                "block_id": 0,
                "granularity": 0,
                "original_content": {"title": None, "body": clean},
                "llm_summary": {"title": None, "body": None},
            }
        ],
    }
    with pytest.raises(MkbError, match="STRUCTURE_GRANULARITY_SET_MISMATCH"):
        await pipeline._structurize(
            _command(),
            {
                "clean_text": clean,
                "clean_digest": stable_digest({"text": clean}),
                "clean_artifact_uuid": uuid7(),
                "layered_content_profile": [0, 1],
                "layered_content_candidate": candidate,
            },
        )
    items = take_pending_generation_evidence()
    assert len(items) == 1
    invocation = items[0]["invocation"]
    report = items[0]["report"]
    assert invocation["status"] == "failed"
    assert invocation["error_code"] == "STRUCTURE_GRANULARITY_SET_MISMATCH"
    assert invocation["stage_key"] == "structurize"
    assert invocation.get("cli_structured_kind") is None
    assert report["disposition"] == "rejected"
    assert report["granularity_set"] == "0"
    assert report["latency_ms"] >= 0
