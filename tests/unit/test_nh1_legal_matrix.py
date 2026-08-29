"""NH1-T07: generate the 10+3 capability matrix without a 7x4 product fiction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import get_args

from intake.api.registry import REGISTERED_PROVIDER_OPERATIONS
from src.contracts.api.models import TaskCreateRequest
from src.contracts.common.ids import stable_digest
from src.contracts.intake.strategies import CLEAN_STRATEGY_DEFINITIONS

MANIFEST_PATH = Path("tests/fixtures/new_harvest/closed_set_manifest.v1.json")


def legal_matrix_material() -> dict[str, object]:
    strategy_cells = [definition.model_dump(mode="json") for definition in CLEAN_STRATEGY_DEFINITIONS]
    op_cells = [
        {
            "provider": definition.provider,
            "operation": definition.operation,
            "definition_version": definition.definition_version,
            "definition_digest": definition.definition_digest,
        }
        for definition in REGISTERED_PROVIDER_OPERATIONS
    ]
    request_intents = list(get_args(TaskCreateRequest.model_fields["request_intent"].annotation))
    intent_illegal = [
        {
            "request_intent": intent,
            "illegal_combination": "source_descriptor_on_non_ingest_intent",
            "disposition": "rejected_before_task",
            "http_status": 422,
            "error_code": "task-schema-invalid",
        }
        for intent in request_intents
        if intent != "intake.ingest"
    ]
    return {
        "strategy_cells": strategy_cells,
        "op_cells": op_cells,
        "intent_illegal": intent_illegal,
    }


def legal_matrix_manifest() -> dict[str, object]:
    material = legal_matrix_material()
    return {**material, "digest": stable_digest(material)}


def test_registry_emits_10_strategy_and_3_ops() -> None:
    manifest = legal_matrix_manifest()
    assert len(manifest["strategy_cells"]) == 10  # type: ignore[arg-type]
    assert len(manifest["op_cells"]) == 3  # type: ignore[arg-type]
    assert len(str(manifest["digest"])) == 64


def test_seven_intent_illegal_cells_have_disposition() -> None:
    intents = list(get_args(TaskCreateRequest.model_fields["request_intent"].annotation))
    rows = legal_matrix_manifest()["intent_illegal"]
    assert isinstance(rows, list)
    assert len(intents) == 7
    assert len(rows) == 6
    assert {row["request_intent"] for row in rows} == set(intents) - {"intake.ingest"}
    assert all(row["disposition"] == "rejected_before_task" for row in rows)
    assert all(row["error_code"] and row["http_status"] == 422 for row in rows)


def test_forbids_7x4_cartesian() -> None:
    manifest = legal_matrix_manifest()
    assert "intent_cells" not in manifest
    assert len(manifest["strategy_cells"]) + len(manifest["op_cells"]) == 13  # type: ignore[arg-type]
    assert len(manifest["intent_illegal"]) == 6  # type: ignore[arg-type]
    assert 28 not in {len(value) for value in manifest.values() if isinstance(value, list)}


def test_frozen_manifest_matches_registry_canonical_bytes() -> None:
    frozen = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert frozen == legal_matrix_manifest()
