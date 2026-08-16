"""NS4-T21: generate stages refuse to run without DiagnosticSink."""

from __future__ import annotations

import pytest

from src.contracts.common.errors import MkbError
from src.runtime.intake.generation_construct import IntakeGenerationConstructMixin


def test_require_diagnostics_fails_when_missing() -> None:
    mixin = IntakeGenerationConstructMixin.__new__(IntakeGenerationConstructMixin)
    mixin._diagnostics = None
    with pytest.raises(MkbError) as caught:
        mixin._require_diagnostics()
    assert caught.value.code == "OBS_DIAGNOSTIC_SINK_MISSING"


def test_require_diagnostics_passes_when_present() -> None:
    mixin = IntakeGenerationConstructMixin.__new__(IntakeGenerationConstructMixin)
    mixin._diagnostics = object()
    mixin._require_diagnostics()
