"""Index rebuild package facade."""

from __future__ import annotations

from src.runtime.intake.index_rebuild_commit import IntakeIndexRebuildCommitMixin
from src.runtime.intake.index_rebuild_plan import IntakeIndexRebuildPlanMixin


class IntakeIndexRebuildMixin(
    IntakeIndexRebuildPlanMixin,
    IntakeIndexRebuildCommitMixin,
):
    """Combined mixin kept for a stable composition surface."""


__all__ = ['IntakeIndexRebuildMixin' , 'IntakeIndexRebuildPlanMixin', 'IntakeIndexRebuildCommitMixin']
