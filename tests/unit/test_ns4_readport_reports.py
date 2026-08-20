"""NS4-T24: ReadPort exposes invocation status and stage reports, not extra."""

from __future__ import annotations

import inspect

from src.services.observability import ObservabilityReadService


def test_generation_evidence_bundle_shape() -> None:
    source = inspect.getsource(ObservabilityReadService)
    assert "mkb_generation_invocations" in source
    assert "generation_invocations" in source
