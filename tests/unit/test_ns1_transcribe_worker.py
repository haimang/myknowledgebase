"""NS1-T22/T23: markdown is an optional no-schema worker before B.json."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.runtime.models import ProcessCommand
from src.runtime.inference.claude_cli import ClaudeCliResult, RecordingStub
from src.runtime.intake.pipeline import IntakePipeline
from src.services.artifacts import OutcomeArtifactCommitter


def _command() -> ProcessCommand:
    return ProcessCommand(
        schema_version="mkb.process-command.v1",
        team_uuid=uuid7(),
        task_uuid=uuid7(),
        trace_uuid=uuid7(),
        execution_uuid=uuid7(),
        process_uuid=uuid7(),
        process_key="lsrag.transcribe_markdown",
        process_contract_version="v1",
        fencing_generation=1,
        command_input_digest=stable_digest({"test": "markdown"}),
        input_manifest_ref="mkbtest:input:markdown",
        input_manifest_digest="a" * 64,
        config_snapshot_ref="mkbtest:config:markdown",
        config_snapshot_digest="b" * 64,
        binding_digest="c" * 64,
    )


@pytest.mark.asyncio
async def test_transcribe_markdown_uses_plain_cli_without_schema() -> None:
    stub = RecordingStub(responses=(ClaudeCliResult("# heading\n\nsource", None, 0, session_id="md-1"),))
    pipeline = IntakePipeline(
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        OutcomeArtifactCommitter(None),  # type: ignore[arg-type]
        claude_cli=stub,
        prompt_root=Path("data/prompts"),
    )
    clean = "source"
    material, _, _ = await pipeline._transcribe_markdown(
        _command(),
        {
            "clean_text": clean,
            "clean_digest": stable_digest({"text": clean}),
        },
    )

    assert material.envelope["state"]["markdown_text"] == "# heading\n\nsource"
    request = stub.requests[0]
    assert request.role == "markdown"
    assert request.json_schema is None
