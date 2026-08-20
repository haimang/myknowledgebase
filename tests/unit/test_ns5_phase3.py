"""NS5 Phase 3: inference lane and evidence (T20–T29 subset)."""

from __future__ import annotations

import os

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import uuid7
from src.contracts.runtime.models import ProcessCommand
from src.runtime.inference.claude_cli import (
    ClaudeCliCleanLanguageModel,
    SubprocessClaudeCli,
    prompt_transport_for,
)
from src.runtime.intake.core import IntakeCoreMixin
from src.runtime.intake.generation_construct import IntakeGenerationConstructMixin
from src.runtime.intake.generation_evidence import (
    record_pending_generation_evidence,
    take_pending_generation_evidence,
)
from src.runtime.workflow.dispatch import OVER_BUDGET_PROCESS_KEYS


def _command(**kwargs: object) -> ProcessCommand:
    digest = "a" * 64
    payload = dict(
        schema_version="mkb.process-command.v1",
        team_uuid=uuid7(),
        task_uuid=uuid7(),
        trace_uuid=uuid7(),
        execution_uuid=uuid7(),
        process_uuid=uuid7(),
        process_key="lsrag.construct",
        process_contract_version="v1",
        fencing_generation=1,
        command_input_digest=digest,
        input_manifest_ref="mkbtest:in",
        input_manifest_digest=digest,
        config_snapshot_ref="mkbtest:cfg",
        config_snapshot_digest=digest,
        binding_digest=digest,
    )
    payload.update(kwargs)
    return ProcessCommand(**payload)  # type: ignore[arg-type]


def test_prompt_transport_is_always_stdin() -> None:
    assert prompt_transport_for("short") == "stdin"
    argv = SubprocessClaudeCli(executable="claude")._env
    assert "MKB_INTERNAL_TOKEN" not in argv


def test_cli_child_env_strips_mkb(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MKB_INTERNAL_TOKEN", "secret-token")
    monkeypatch.setenv("PATH", os.environ.get("PATH", "/bin"))
    cli = SubprocessClaudeCli(executable="claude")
    assert "MKB_INTERNAL_TOKEN" not in cli._env


def test_salvage_allows_urgent_local() -> None:
    mixin = IntakeGenerationConstructMixin()
    mixin._claude_cli = object()  # type: ignore[attr-defined]
    exc = MkbError("INFERENCE_TRANSPORT_RETRYABLE", "retry", 503)
    urgent = _command(dispatch_pool="local-inference", task_priority="urgent")
    low = _command(dispatch_pool="local-inference", task_priority="low")
    assert mixin._can_salvage_local_inference(exc, urgent) is True
    assert mixin._can_salvage_local_inference(exc, low) is False


def test_ns1_prompt_file_requires_state() -> None:
    mixin = IntakeGenerationConstructMixin()
    mixin._prompt_root = __import__("pathlib").Path("data/prompts")  # type: ignore[attr-defined]
    with pytest.raises(MkbError, match="PROMPT_NOT_REGISTERED"):
        mixin._ns1_prompt_file(
            "json/promptB.json.generic.v1.md",
            error_code="PROMPT_HASH_MISMATCH",
            state=None,
            role="json",
        )


def test_exhausted_is_process_retryable() -> None:
    assert "INFERENCE_TRANSPORT_EXHAUSTED" in IntakeCoreMixin._RECOVERABLE_ERROR_CODES
    assert "INFERENCE_BACKPRESSURE" in IntakeCoreMixin._RECOVERABLE_ERROR_CODES


def test_construct_is_over_budget_key() -> None:
    assert "lsrag.construct" in OVER_BUDGET_PROCESS_KEYS


def test_evidence_is_keyed_by_process_uuid() -> None:
    first = uuid7()
    second = uuid7()
    record_pending_generation_evidence(
        invocation={"status": "failed", "error_code": "one", "input_digest": "a" * 64},
        process_uuid=first,
    )
    record_pending_generation_evidence(
        invocation={"status": "failed", "error_code": "two", "input_digest": "a" * 64},
        process_uuid=second,
    )
    items = take_pending_generation_evidence(second)
    assert items[0]["invocation"]["error_code"] == "two"
    leftover = take_pending_generation_evidence(first)
    assert leftover[0]["invocation"]["error_code"] == "one"


@pytest.mark.asyncio
async def test_non_text_blob_is_rejected() -> None:
    model = ClaudeCliCleanLanguageModel(cli=None, system_prompt_file="p.md")  # type: ignore[arg-type]
    with pytest.raises(MkbError, match="CLEAN_MEDIA_UNSUPPORTED"):
        await model.complete(prompt="x", blob=b"%PDF-1.4", media_type="application/pdf")
