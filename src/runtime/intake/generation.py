"""S06/S07 generation package facade (composed sub-mixins).

Prefer importing the specific mixins from ``generation_*`` modules; this module
re-exports a combined mixin for any residual single-import call sites.
"""

from __future__ import annotations

from src.runtime.intake.generation_artifacts import IntakeGenerationArtifactsMixin
from src.runtime.intake.generation_construct import IntakeGenerationConstructMixin
from src.runtime.intake.generation_live import IntakeGenerationLiveMixin


class IntakeGenerationMixin(
    IntakeGenerationArtifactsMixin,
    IntakeGenerationConstructMixin,
    IntakeGenerationLiveMixin,
):
    """Combined generation mixin kept for a stable composition surface."""


__all__ = [
    "IntakeGenerationMixin",
    "IntakeGenerationArtifactsMixin",
    "IntakeGenerationConstructMixin",
    "IntakeGenerationLiveMixin",
]
