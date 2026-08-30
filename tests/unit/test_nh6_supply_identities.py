"""NH6-T09/T10: every supply has an independent identity, limit, and probe key."""

from __future__ import annotations

import inspect

from src.runtime.supply.identities import SUPPLY_BY_CAPABILITY, SUPPLY_IDENTITIES
from src.runtime.workflow.dispatch import DispatchPool


def test_five_supply_identities_have_distinct_readiness_and_limits() -> None:
    assert set(SUPPLY_BY_CAPABILITY) == {
        "pdf.parse",
        "browser.render",
        "browser.print_pdf",
        "ocr.deterministic",
        "s11.multimodal",
    }
    assert len({item.readiness_key for item in SUPPLY_IDENTITIES}) == 5
    assert SUPPLY_BY_CAPABILITY["browser.render"].limits.concurrency == 2
    assert SUPPLY_BY_CAPABILITY["browser.print_pdf"].limits.concurrency == 1
    assert SUPPLY_BY_CAPABILITY["pdf.parse"].network_policy == "denied"
    assert SUPPLY_BY_CAPABILITY["s11.multimodal"].prompt_required is True
    assert SUPPLY_BY_CAPABILITY["ocr.deterministic"].prompt_required is False


def test_registry_freezes_no_implementation_library_as_truth_or_fourth_pool() -> None:
    source = inspect.getsource(__import__("src.runtime.supply.identities", fromlist=["SUPPLY_IDENTITIES"]))
    forbidden = ("playwright", "pypdf", "tesseract", "poppler", "mupdf", "latest")
    assert all(value not in source.casefold() for value in forbidden)
    assert set(DispatchPool.__args__) == {"local-inference", "non-interactive", "embed"}
