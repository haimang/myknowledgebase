"""NH7-T01: 10+3 activation matrix is registry-generated, not a cartesian product."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from intake.api.registry import REGISTERED_PROVIDER_OPERATIONS
from src.contracts.common.errors import MkbError
from src.contracts.intake.strategies import (
    CLEAN_STRATEGY_DEFINITIONS,
    resolve_bound_clean_strategy,
    resolve_clean_strategy,
)
from tests.unit.test_nh1_legal_matrix import MANIFEST_PATH, legal_matrix_manifest


def test_registry_emits_10_strategy_and_3_ops_not_cartesian() -> None:
    manifest = legal_matrix_manifest()
    assert len(manifest["strategy_cells"]) == 10
    assert len(manifest["op_cells"]) == 3
    assert len(manifest["intent_illegal"]) == 6
    assert "intent_cells" not in manifest
    assert 28 not in {len(value) for value in manifest.values() if isinstance(value, list)}
    assert 40 not in {len(value) for value in manifest.values() if isinstance(value, list)}


def test_identity_strategy_process_representation_split() -> None:
    by_capability = Counter(definition.clean_capability for definition in CLEAN_STRATEGY_DEFINITIONS)
    assert by_capability["clean.extract.pdf_llm"] == 2
    assert by_capability["clean.ocr.local"] == 2
    print_pdf = resolve_clean_strategy("web.browser_print_pdf")
    assert print_pdf.channel == "pdf"
    assert print_pdf.clean_capability == "clean.extract.pdf_llm"
    assert resolve_bound_clean_strategy(
        step_key="clean_print_pdf", process_key="clean.extract.pdf_llm"
    ).strategy_key.value == "web.browser_print_pdf"
    assert resolve_bound_clean_strategy(
        step_key="clean_pdf_llm", process_key="clean.extract.pdf_llm"
    ).strategy_key.value == "pdf.document_understanding"
    assert resolve_bound_clean_strategy(
        step_key="clean_pdf_ocr", process_key="clean.ocr.local"
    ).strategy_key.value == "pdf.ocr"
    assert resolve_bound_clean_strategy(
        step_key="clean_doc_ocr", process_key="clean.ocr.local"
    ).strategy_key.value == "doc.ocr"


def test_illegal_cells_409_or_422() -> None:
    with pytest.raises(MkbError) as unknown:
        resolve_clean_strategy("web.unknown")
    assert unknown.value.status_code == 409
    with pytest.raises(MkbError) as mismatch:
        resolve_bound_clean_strategy(step_key="clean_web_static", process_key="clean.extract.pdf_text")
    assert mismatch.value.status_code == 409
    with pytest.raises(MkbError) as unbound:
        resolve_bound_clean_strategy(step_key="not_a_clean_step", process_key="clean.extract.web")
    assert unbound.value.status_code == 409


def test_consumes_nh1_preembedded_closed_set_manifest() -> None:
    frozen = json.loads(Path(MANIFEST_PATH).read_text(encoding="utf-8"))
    live = legal_matrix_manifest()
    assert {key: frozen[key] for key in live} == live
    assert {cell["strategy_key"] for cell in frozen["strategy_cells"]} == {
        definition.strategy_key.value for definition in CLEAN_STRATEGY_DEFINITIONS
    }
    assert len(REGISTERED_PROVIDER_OPERATIONS) == 3
    assert all(cell.get("disposition") != "live" for cell in frozen["intent_illegal"])
