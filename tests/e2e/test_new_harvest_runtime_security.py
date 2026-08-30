"""Fixed NH6/NH9 runtime-security surface (NH6 nodes first)."""

from __future__ import annotations

import asyncio
import hashlib
import time
from pathlib import Path

import pytest

from api.app import create_app
from intake.types import CleanPrompt
from src.contracts.common.errors import MkbError
from src.runtime.http_acquisition import HttpAcquirer
from src.runtime.inference.facade import ConcurrencyGate
from src.runtime.security import EgressPolicy
from src.runtime.supply.browser import HardenedBrowserRuntime
from src.runtime.supply.glyph_ocr_worker import render_fixture_png
from src.runtime.supply.pdf_parser import IsolatedPdfParser, build_compressed_pdf_fixture
from tests.nh6_runtime_support import (
    browser_settings,
    local_multimodal_server,
    local_spa_server,
    observed_spa_paths,
)


class _CountingPolicy(EgressPolicy):
    def __init__(self) -> None:
        super().__init__(allow_literal_ip=True, allow_private_default=True, max_redirects=3)
        self.initial_or_hop_checks = 0
        self.redirect_checks = 0

    def check_url(self, url: str, **kwargs: bool | None):  # type: ignore[no-untyped-def]
        self.initial_or_hop_checks += 1
        return super().check_url(url, **kwargs)

    def validate_redirect(self, url: str, **kwargs: bool | None):  # type: ignore[no-untyped-def]
        self.redirect_checks += 1
        return super().validate_redirect(url, **kwargs)


def test_browser_runs_non_root(tmp_path: Path) -> None:
    runtime = create_app(browser_settings(tmp_path)).state.container.browser_runtime
    assert isinstance(runtime, HardenedBrowserRuntime)
    assert asyncio.run(runtime.readiness("browser.render")) is True
    observed = runtime.last_observation
    assert observed is not None
    assert observed.runtime_uid != 0
    assert observed.driver_uid != 0
    assert "--clear-groups" in observed.launch_args


def test_production_forbids_no_sandbox(tmp_path: Path) -> None:
    runtime = create_app(browser_settings(tmp_path)).state.container.browser_runtime
    assert isinstance(runtime, HardenedBrowserRuntime)
    assert asyncio.run(runtime.readiness("browser.print_pdf")) is True
    observed = runtime.last_observation
    assert observed is not None
    assert all("no-sandbox" not in argument.casefold() for argument in observed.launch_args)
    assert "no-sandbox" not in " ".join(runtime._driver_command(1, uid=65534, gid=65534)).casefold()  # noqa: SLF001


def test_browser_egress_rechecks_each_redirect() -> None:
    policy = _CountingPolicy()
    acquirer = HttpAcquirer(policy, allow_http=True)
    runtime = HardenedBrowserRuntime.discover(
        acquirer=acquirer,
        gate=ConcurrencyGate(
            4,
            capability_limits={"browser.render": 2, "browser.print_pdf": 1},
        ),
    )
    with local_spa_server() as (origin, marker):
        rendered = asyncio.run(runtime.render(f"{origin}/redirect"))
        assert marker in rendered.body
        assert rendered.source_evidence["redirect_count"] == 1
        assert policy.redirect_checks == 1
        assert policy.initial_or_hop_checks >= 2
        with pytest.raises(MkbError) as denied:
            asyncio.run(runtime.render(f"{origin}/restricted-redirect"))
    assert denied.value.code == "SEC_EGRESS_REDIRECT_DENIED"
    assert policy.redirect_checks == 2
    # A denied redirect never reaches the browser process.
    assert runtime.invocation_counts["browser.render"] == 1


def test_browser_page_cannot_bypass_s16_prefetch() -> None:
    policy = _CountingPolicy()
    runtime = HardenedBrowserRuntime.discover(
        acquirer=HttpAcquirer(policy, allow_http=True),
        gate=ConcurrencyGate(4, capability_limits={"browser.render": 2, "browser.print_pdf": 1}),
    )
    with local_spa_server() as (origin, marker):
        rendered = asyncio.run(runtime.render(f"{origin}/egress-attempt"))
        assert marker in rendered.body
        time.sleep(0.5)
        paths = observed_spa_paths()
    assert paths == ("/egress-attempt",)


def test_parser_process_network_denied() -> None:
    parser = IsolatedPdfParser.discover()
    proof = asyncio.run(parser.isolation_probe())
    assert proof["network_denied"] is True
    assert proof["uid"] != 0
    assert "--net" in parser.command()


def test_campaign_security_signoff_aggregates_nh6_gates() -> None:
    """NH9-T10 optional campaign index: NH6 nodes already listed, no new product asserts."""

    tests_txt = Path("docs/evidence/new-harvest/AP-NH6/tests.txt").read_text(encoding="utf-8")
    for listed in (
        "tests/e2e/test_nh6_parser_isolation.py",
        "tests/e2e/test_nh6_readiness.py",
        "test_browser_runs_non_root",
        "test_production_forbids_no_sandbox",
        "test_browser_egress_rechecks_each_redirect",
        "test_parser_process_network_denied",
        "test_backpressure_zero_downstream",
    ):
        assert listed in tests_txt, listed
    nodes = {
        "tests/e2e/test_nh6_parser_isolation.py": (
            "test_parser_subprocess_has_no_network",
            "test_resource_kill_on_timeout",
            "test_malicious_pdf_does_not_kill_api",
        ),
        "tests/e2e/test_nh6_readiness.py": (
            "test_positive_probe_matches_presence",
            "test_missing_binary_component_not_overall_green",
            "test_models_list_insufficient_for_ready",
            "test_create_app_readiness_without_patch",
        ),
        "tests/e2e/test_new_harvest_runtime_security.py": (
            "test_browser_runs_non_root",
            "test_production_forbids_no_sandbox",
            "test_browser_egress_rechecks_each_redirect",
            "test_parser_process_network_denied",
            "test_backpressure_zero_downstream",
        ),
    }
    for path, names in nodes.items():
        source = Path(path).read_text(encoding="utf-8")
        for name in names:
            assert f"def {name}" in source, name
    forbidden = ("which " + "chromium", "import " + "pypdf")
    for path in (
        Path("tests/e2e/test_new_harvest_closed_set.py"),
        Path("tests/e2e/test_new_harvest_crash_windows.py"),
        Path("tests/domain/test_nh9_evidence_pack_checker.py"),
    ):
        text = path.read_text(encoding="utf-8")
        assert all(token not in text for token in forbidden)


def test_backpressure_zero_downstream(tmp_path: Path) -> None:
    with (
        local_multimodal_server() as (base_url, model_key, payloads),
        local_spa_server() as (
            origin,
            _marker,
        ),
    ):
        app = create_app(
            browser_settings(
                tmp_path,
                multimodal_enabled=True,
                multimodal_model_key=model_key,
                multimodal_model_version="v1",
                inference_vllm_base_url=base_url,
                pdf_parser_concurrency=1,
                browser_render_concurrency=1,
                multimodal_concurrency=1,
            )
        )
        container = app.state.container

        async def scenario() -> None:
            gate = container.inference._gate  # noqa: SLF001
            parser_before = container.pdf_parser.subprocess_call_count
            parser_lease = await gate.try_acquire("pdf.parse")
            assert parser_lease is not None
            try:
                with pytest.raises(MkbError) as parser_error:
                    await container.pdf_parser.parse(build_compressed_pdf_fixture("blocked parser"))
            finally:
                await gate.release(parser_lease)
            assert parser_error.value.code == "INFERENCE_BACKPRESSURE"
            assert container.pdf_parser.subprocess_call_count == parser_before

            render_before = dict(container.browser_runtime.invocation_counts)
            render_lease = await gate.try_acquire("browser.render")
            assert render_lease is not None
            try:
                with pytest.raises(MkbError) as browser_error:
                    await container.browser_runtime.render(f"{origin}/spa")
            finally:
                await gate.release(render_lease)
            assert browser_error.value.code == "INFERENCE_BACKPRESSURE"
            assert container.browser_runtime.invocation_counts == render_before

            prompt_text = "Read visible glyphs."
            prompt = CleanPrompt(
                key="promptA.default",
                version="v1",
                text=prompt_text,
                content_sha256=hashlib.sha256(prompt_text.encode()).hexdigest(),
            )
            model_lease = await gate.try_acquire("s11.multimodal")
            assert model_lease is not None
            try:
                with pytest.raises(MkbError) as model_error:
                    await container.clean_llm.complete_bound(
                        team_uuid="nh6-team",
                        prompt=prompt,
                        blob=render_fixture_png("BLOCKED"),
                        media_type="image/png",
                        purpose="vision",
                    )
            finally:
                await gate.release(model_lease)
            assert model_error.value.code == "INFERENCE_BACKPRESSURE"

        asyncio.run(scenario())
    assert payloads == []
