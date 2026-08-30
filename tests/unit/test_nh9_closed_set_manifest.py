"""NH9-T01: closed-set manifest covers 82 works / 10+3 / seven intents / layers."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import get_args

from intake.api.registry import REGISTERED_PROVIDER_OPERATIONS
from src.contracts.api.models import TaskCreateRequest
from src.contracts.intake.strategies import CLEAN_STRATEGY_DEFINITIONS
from tests.unit.test_nh1_legal_matrix import legal_matrix_manifest

_GEN = Path("tests/fixtures/new_harvest/generate_closed_set_manifest.py")
_SPEC = importlib.util.spec_from_file_location("nh9_generate_closed_set_manifest", _GEN)
assert _SPEC is not None and _SPEC.loader is not None
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)
MANIFEST_PATH = _MOD.MANIFEST_PATH
_FAKE_GREEN = _MOD._FAKE_GREEN
_WINDOWS = _MOD._WINDOWS
build_manifest = _MOD.build_manifest
render = _MOD.render
work_ids = _MOD.work_ids

FROZEN_82 = work_ids()


def _frozen() -> dict:
    generated = build_manifest()
    assert render(generated) == render(build_manifest())
    return generated


def test_manifest_digest_stable() -> None:
    live = legal_matrix_manifest()
    frozen = _frozen()
    for key in ("strategy_cells", "op_cells", "intent_illegal", "digest"):
        assert frozen[key] == live[key]
    on_disk = MANIFEST_PATH.read_text(encoding="utf-8")
    assert on_disk == render(frozen)


def test_work_ids_are_exact_82() -> None:
    ids = _frozen()["work_ids"]
    assert len(ids) == 82
    assert ids == FROZEN_82
    assert set(ids) == set(FROZEN_82)


def test_strategies_ops_intents_match_registries() -> None:
    frozen = _frozen()
    assert len(frozen["strategy_cells"]) == 10
    assert len(frozen["op_cells"]) == 3
    assert {cell["strategy_key"] for cell in frozen["strategy_cells"]} == {
        definition.strategy_key.value for definition in CLEAN_STRATEGY_DEFINITIONS
    }
    assert {(cell["provider"], cell["operation"]) for cell in frozen["op_cells"]} == {
        (definition.provider, definition.operation) for definition in REGISTERED_PROVIDER_OPERATIONS
    }
    intents = list(get_args(TaskCreateRequest.model_fields["request_intent"].annotation))
    assert len(intents) == 7
    assert {row["request_intent"] for row in frozen["intent_illegal"]} == set(intents) - {"intake.ingest"}


def test_illegal_cells_not_cartesian_28() -> None:
    frozen = _frozen()
    assert "intent_cells" not in frozen
    assert len(frozen["intent_illegal"]) == 6
    assert all(row.get("disposition") and row.get("error_code") for row in frozen["intent_illegal"])
    assert 28 not in {len(value) for value in frozen.values() if isinstance(value, list)}
    assert len(frozen["legal_cells"]) == 13


def test_layers_l1_l4_recorded() -> None:
    frozen = _frozen()
    layers = {cell["min_layer"] for cell in frozen["legal_cells"]}
    assert layers <= {"L1", "L2", "L3", "L4"}
    assert "L4" in layers
    assert frozen["windows"] == _WINDOWS
    assert frozen["fake_green"] == _FAKE_GREEN
    assert all(cell["query_expected"] == 0 for cell in frozen["negative_cells"])


def test_experiment_fields_empty_and_not_in_join() -> None:
    experiment = _frozen()["experiment"]
    assert experiment["launch_date"] is None
    assert experiment["scores"] is None
    assert experiment["in_closure_join"] is False
