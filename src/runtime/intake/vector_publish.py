"""Vectorize/publish package facade."""

from __future__ import annotations

from src.runtime.intake.vector_publish_commit import IntakeVectorPublishCommitMixin
from src.runtime.intake.vectorize import IntakeVectorizeMixin


class IntakeVectorPublishMixin(
    IntakeVectorizeMixin,
    IntakeVectorPublishCommitMixin,
):
    """Combined mixin kept for a stable composition surface."""


__all__ = ['IntakeVectorPublishMixin' , 'IntakeVectorizeMixin', 'IntakeVectorPublishCommitMixin']
