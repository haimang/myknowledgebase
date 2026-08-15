"""Unit tests for pure dispatch policy and pool classification (NS2-T03..T05, T09)."""

from __future__ import annotations

from api.app import create_app
from src.runtime.config import Settings
from src.runtime.workflow.dispatch import (
    DISPATCH_EMBED_QUEUED_CAP,
    DISPATCH_EMBED_RUNNING_CAP,
    DISPATCH_LOCAL_CHAR_BUDGET,
    DISPATCH_LOCAL_QUEUED_CAP,
    DISPATCH_LOCAL_RUNNING_CAP,
    DISPATCH_NI_QUEUED_CAP,
    DISPATCH_NI_RUNNING_CAP,
    choose_pool,
    pool_kind,
)
from src.services.billing import BillingPort, DefaultBillingService


class MockBillingService:
    def __init__(self, quota: bool = True) -> None:
        self._quota = quota

    def has_quota(self, channel: str) -> bool:
        del channel
        return self._quota


def test_choose_pool_table_driven_lanes_and_occupancy_boundaries() -> None:
    # NS2-T03: Table driven coverage across all 4 lanes and occupancy bounds
    # 1. urgent & high -> non-interactive when ni_queued < 4
    assert choose_pool("urgent", "generate", ni_queued=0) == "non-interactive"
    assert choose_pool("urgent", "generate", ni_queued=3) == "non-interactive"
    assert choose_pool("urgent", "generate", ni_queued=4) is None  # wait in orchestrator
    assert choose_pool("high", "generate", ni_queued=0) == "non-interactive"
    assert choose_pool("high", "generate", ni_queued=3) == "non-interactive"
    assert choose_pool("high", "generate", ni_queued=4) is None

    # 2. normal -> local when local_queued < 6 and available; overflows to NI when local full/offline
    assert choose_pool("normal", "generate", local_queued=0, ni_queued=0) == "local-inference"
    assert choose_pool("normal", "generate", local_queued=5, ni_queued=0) == "local-inference"
    assert choose_pool("normal", "generate", local_queued=6, ni_queued=0) == "non-interactive"
    assert choose_pool("normal", "generate", local_queued=6, ni_queued=3) == "non-interactive"
    assert choose_pool("normal", "generate", local_queued=6, ni_queued=4) is None  # both full -> wait
    assert choose_pool("normal", "generate", local_available=False, ni_queued=0) == "non-interactive"
    assert choose_pool("normal", "generate", local_available=False, ni_queued=4) is None

    # 3. low -> always local-inference; never overflows to NI
    assert choose_pool("low", "generate", local_queued=0, ni_queued=0) == "local-inference"
    assert choose_pool("low", "generate", local_queued=5, ni_queued=0) == "local-inference"
    assert choose_pool("low", "generate", local_queued=6, ni_queued=0) is None  # wait, never NI
    assert choose_pool("low", "generate", local_available=False, ni_queued=0) is None


def test_low_never_chooses_non_interactive_and_billing_false_blocks_ni() -> None:
    # NS2-T04: Low never selects NI regardless of NI capacity; billing False blocks NI
    assert choose_pool("low", "generate", local_queued=6, ni_queued=0, ni_quota=True) is None

    # Urgent and High blocked when ni_quota is False
    assert choose_pool("urgent", "generate", ni_quota=False) is None
    assert choose_pool("high", "generate", ni_quota=False) is None

    # Normal local path still works when ni_quota is False, but overflow blocked
    assert choose_pool("normal", "generate", local_queued=0, ni_quota=False) == "local-inference"
    assert choose_pool("normal", "generate", local_queued=6, ni_quota=False) is None


def test_over_budget_json_overflows_normal_to_ni_but_locks_low_to_local() -> None:
    # NS2-T35 (policy slice): normal over budget -> NI; low over budget -> local or wait
    assert choose_pool("normal", "generate", local_queued=0, over_budget=True) == "non-interactive"
    assert choose_pool("normal", "generate", local_queued=0, over_budget=True, ni_queued=4) is None
    assert choose_pool("low", "generate", local_queued=0, over_budget=True) == "local-inference"
    assert choose_pool("low", "generate", local_queued=6, over_budget=True) is None


def test_explicit_channel_override_respects_pool_capacity() -> None:
    assert choose_pool("low", "generate", explicit_channel="non-interactive", ni_queued=0) == "non-interactive"
    assert choose_pool("low", "generate", explicit_channel="non-interactive", ni_queued=4) is None
    assert choose_pool("urgent", "generate", explicit_channel="local-inference", local_queued=0) == "local-inference"
    assert choose_pool("urgent", "generate", explicit_channel="local-inference", local_queued=6) is None


def test_pool_kind_classification_covers_all_process_keys() -> None:
    # NS2-T05: pool_kind covers full core dispatch process_key spectrum
    generate_keys = [
        "lsrag.transcribe_markdown",
        "lsrag.structurize",
        "lsrag.construct",
        "clean.extract.web_llm",
        "clean.extract.doc_llm",
        "clean.extract.pdf_llm",
    ]
    for key in generate_keys:
        assert pool_kind(key) == "generate", f"expected {key} to be generate"

    # Vectorize depends on inference mode
    assert pool_kind("lsrag.vectorize") == "embed"
    assert pool_kind("lsrag.vectorize", {"l2": {"inference_mode": "live"}}) == "embed"
    assert pool_kind("lsrag.vectorize", {"l2": {"inference_mode": "deterministic"}}) == "unpooled"

    # All unpooled stages
    unpooled_keys = [
        "acquire.http",
        "acquire.blob",
        "decode.text",
        "decode.pdf",
        "clean.extract.deterministic",
        "clean.seal",
        "clean.preflight",
        "accept.fast_forward",
        "accept.review",
        "publish.generation",
        "index.rebuild",
        "human_review",
    ]
    for key in unpooled_keys:
        assert pool_kind(key) == "unpooled", f"expected {key} to be unpooled"


def test_settings_dispatch_constants_and_facade_composition() -> None:
    # NS2-T09: settings three-pool constants and facade composition gate >= 12
    settings = Settings()
    assert settings.dispatch_local_running == DISPATCH_LOCAL_RUNNING_CAP == 2
    assert settings.dispatch_local_queued == DISPATCH_LOCAL_QUEUED_CAP == 6
    assert settings.dispatch_ni_running == DISPATCH_NI_RUNNING_CAP == 2
    assert settings.dispatch_ni_queued == DISPATCH_NI_QUEUED_CAP == 4
    assert settings.dispatch_embed_running == DISPATCH_EMBED_RUNNING_CAP == 8
    assert settings.dispatch_embed_queued == DISPATCH_EMBED_QUEUED_CAP == 20
    assert settings.dispatch_local_char_budget == DISPATCH_LOCAL_CHAR_BUDGET == 16_000
    assert settings.inference_max_in_flight >= 12

    app = create_app(settings)
    facade = app.state.container.inference
    assert facade._gate._global_max >= 12
    assert facade._gate._capability_limits["embed"] == 8
    assert facade._gate._capability_limits["structured_generate"] == 2
    assert facade._gate._capability_limits["text_generate"] == 2


def test_billing_port_protocol_and_default_implementation() -> None:
    billing: BillingPort = DefaultBillingService()
    assert billing.has_quota("non-interactive") is True
    assert billing.has_quota("local-inference") is True

    mock_billing: BillingPort = MockBillingService(quota=False)
    assert mock_billing.has_quota("non-interactive") is False
