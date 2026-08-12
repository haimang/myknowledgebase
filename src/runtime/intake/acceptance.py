"""Acceptance package facade."""

from __future__ import annotations

from src.runtime.intake.acceptance_lifecycle import IntakeAcceptanceLifecycleMixin
from src.runtime.intake.acceptance_scatter import IntakeAcceptanceScatterMixin
from src.runtime.intake.acceptance_snapshot import IntakeAcceptanceSnapshotMixin


class IntakeAcceptanceMixin(
    IntakeAcceptanceSnapshotMixin,
    IntakeAcceptanceScatterMixin,
    IntakeAcceptanceLifecycleMixin,
):
    """Combined mixin kept for a stable composition surface."""


__all__ = ['IntakeAcceptanceMixin' , 'IntakeAcceptanceSnapshotMixin', 'IntakeAcceptanceScatterMixin', 'IntakeAcceptanceLifecycleMixin']
