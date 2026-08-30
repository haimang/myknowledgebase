"""NH7-T03 companion: L3 success tests must not assign pipeline fetchers."""

from __future__ import annotations

from pathlib import Path

_FORBIDDEN = ("_browser_fetcher =", "_http_fetcher =", "_clean_llm =")
_L3_FILES = (
    "tests/e2e/test_nh7_inline_static_retrieval.py",
    "tests/e2e/test_nh7_pdf_text_retrieval.py",
    "tests/e2e/test_nh7_browser_dom_retrieval.py",
    "tests/e2e/test_nh7_print_pdf_retrieval.py",
    "tests/e2e/test_nh7_multimodal_lanes.py",
    "tests/e2e/test_nh7_registered_api_retrieval.py",
    "tests/e2e/test_nh7_exhausted_zero.py",
)


def test_l3_success_tests_do_not_assign_fetchers() -> None:
    for relative in _L3_FILES:
        path = Path(relative)
        if not path.is_file():
            continue
        source = path.read_text(encoding="utf-8")
        for token in _FORBIDDEN:
            assert token not in source, f"{relative} assigns {token}"
        assert "sqlite3.connect" not in source
        assert "import sqlite3" not in source
