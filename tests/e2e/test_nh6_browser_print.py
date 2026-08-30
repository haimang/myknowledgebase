"""NH6-T04: real print-to-PDF and independent render/print budgets."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from api.app import create_app
from src.contracts.common.errors import MkbError
from src.runtime.supply.browser import HardenedBrowserRuntime
from tests.nh6_runtime_support import browser_settings, local_spa_server


def test_print_real_pdf_header(tmp_path: Path) -> None:
    app = create_app(browser_settings(tmp_path))
    runtime = app.state.container.browser_runtime
    assert isinstance(runtime, HardenedBrowserRuntime)
    with local_spa_server() as (origin, marker):
        result = asyncio.run(runtime.print_pdf(f"{origin}/spa"))
    assert result.body.startswith(b"%PDF-")
    assert len(result.body) > 1_000
    assert result.profile_identity.startswith("browser.print_pdf.v1;")
    assert result.runtime_uid != 0
    assert result.timeout_seconds == app.state.container.settings.browser_print_timeout_seconds
    assert result.output_limit_bytes == app.state.container.settings.browser_print_max_bytes
    extracted = asyncio.run(app.state.container.pdf_parser.parse(result.body))
    assert marker in extracted.text


def test_independent_budget_from_render(tmp_path: Path) -> None:
    app = create_app(browser_settings(tmp_path))
    runtime = app.state.container.browser_runtime
    assert isinstance(runtime, HardenedBrowserRuntime)
    gate = app.state.container.inference._gate  # noqa: SLF001
    held_render = asyncio.run(gate.try_acquire("browser.render"))
    assert held_render is not None
    try:
        with local_spa_server() as (origin, _marker):
            printed = asyncio.run(runtime.print_pdf(f"{origin}/spa"))
        assert printed.body.startswith(b"%PDF-")
    finally:
        asyncio.run(gate.release(held_render))
    assert runtime.success_counts == {"browser.render": 0, "browser.print_pdf": 1}


def test_render_success_does_not_satisfy_print(tmp_path: Path) -> None:
    app = create_app(browser_settings(tmp_path, browser_print_max_bytes=1))
    runtime = app.state.container.browser_runtime
    assert isinstance(runtime, HardenedBrowserRuntime)
    with local_spa_server() as (origin, marker):
        rendered = asyncio.run(runtime.render(f"{origin}/spa"))
        with pytest.raises(MkbError) as raised:
            asyncio.run(runtime.print_pdf(f"{origin}/spa"))
    assert marker in rendered.body
    assert raised.value.code == "BROWSER_OUTPUT_LIMIT"
    assert runtime.success_counts == {"browser.render": 1, "browser.print_pdf": 0}
