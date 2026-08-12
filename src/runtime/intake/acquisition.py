"""Acquisition package facade."""

from __future__ import annotations

from src.runtime.intake.acquisition_ingest import IntakeAcquisitionIngestMixin
from src.runtime.intake.acquisition_intents import IntakeAcquisitionIntentsMixin


class IntakeAcquisitionMixin(
    IntakeAcquisitionIngestMixin,
    IntakeAcquisitionIntentsMixin,
):
    """Combined mixin kept for a stable composition surface."""


__all__ = ['IntakeAcquisitionMixin' , 'IntakeAcquisitionIngestMixin', 'IntakeAcquisitionIntentsMixin']
