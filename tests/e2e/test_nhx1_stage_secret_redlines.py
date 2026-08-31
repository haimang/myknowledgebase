"""NHX1-T18: stage envelopes persist CAS coordinates, not body/secret material."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.runtime.models import ProcessCommand
from src.runtime.intake.pipeline import IntakePipeline


def _command() -> ProcessCommand:
    digest = stable_digest({"input": "nhx1"})
    return ProcessCommand(
        schema_version="mkb.process-command.v1",
        team_uuid=uuid7(),
        task_uuid=uuid7(),
        trace_uuid=uuid7(),
        execution_uuid=uuid7(),
        process_uuid=uuid7(),
        step_key="decode_text",
        process_key="intake.decode.text_json_html",
        process_contract_version="v1",
        fencing_generation=1,
        command_input_digest=digest,
        input_manifest_ref="mkbtest:input:nhx1",
        input_manifest_digest=digest,
        config_snapshot_ref="mkbtest:config:nhx1",
        config_snapshot_digest=digest,
        binding_digest=digest,
    )


def test_stage_material_drops_body_when_cas_coordinate_exists() -> None:
    pipeline = IntakePipeline(None, None, None)  # type: ignore[arg-type]
    command = _command()
    state = {
        "raw_text": "NHX1-BODY-SENTINEL",
        "raw_cas_handle": "mkbobj:v1:team:digest",
        "raw_cas_digest": "a" * 64,
        "raw_cas_size": 19,
        "payload_extra": {"api_token": "should-never-persist"},
    }
    material = pipeline._material(command, state, {"stage": "decode"})  # noqa: SLF001
    encoded = json.dumps(material.envelope, ensure_ascii=False)
    assert "NHX1-BODY-SENTINEL" not in encoded
    assert "should-never-persist" not in encoded
    assert material.envelope["state"]["raw_cas_handle"] == "mkbobj:v1:team:digest"


@pytest.mark.asyncio
async def test_load_state_hydrates_only_the_declared_cas_bytes(tmp_path: Path) -> None:
    from src.contracts.storage.models import PromoteRequest
    from src.storage.local_store import LocalObjectStore

    store = LocalObjectStore(tmp_path / "objects")
    team_uuid = uuid7()
    pipeline = IntakePipeline(None, store, None)  # type: ignore[arg-type]
    command = _command().model_copy(update={"team_uuid": team_uuid})
    cas = await store.promote(b"frozen stage body", PromoteRequest(team_uuid=team_uuid, purpose="process_io"))
    body = {"raw_text": "frozen stage body", "raw_cas_handle": cas.handle.value, "raw_cas_digest": cas.sha256, "raw_cas_size": cas.size_bytes}
    material = pipeline._material(command, body, {"stage": "decode"})  # noqa: SLF001
    envelope = await store.promote(material.output_bytes, PromoteRequest(team_uuid=team_uuid, purpose="process_io"))
    loaded = await pipeline._load_state(  # noqa: SLF001
        command.model_copy(update={"input_manifest_ref": envelope.handle.value, "input_manifest_digest": envelope.sha256}),
    )
    assert loaded["raw_text"] == "frozen stage body"
