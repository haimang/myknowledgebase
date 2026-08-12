"""Thin IntakePipeline entry: composition root for stage mixins.

Public import path remains :mod:`src.runtime.intake_pipeline` for compatibility.
"""

from __future__ import annotations

from src.runtime.intake.acceptance import IntakeAcceptanceMixin
from src.runtime.intake.acquisition import IntakeAcquisitionMixin
from src.runtime.intake.clean_preflight import IntakeCleanPreflightMixin
from src.runtime.intake.core import IntakeCoreMixin
from src.runtime.intake.generation import IntakeGenerationMixin
from src.runtime.intake.index_rebuild import IntakeIndexRebuildMixin
from src.runtime.intake.vector_publish import IntakeVectorPublishMixin
from src.runtime.workflow_engine import ProcessStageHandler


class IntakePipeline(
    IntakeCoreMixin,
    IntakeAcquisitionMixin,
    IntakeIndexRebuildMixin,
    IntakeCleanPreflightMixin,
    IntakeAcceptanceMixin,
    IntakeGenerationMixin,
    IntakeVectorPublishMixin,
    ProcessStageHandler,
):
    """Concrete handler for the built-in single-intake workflow.

    Stage implementations live in focused mixins under :mod:`src.runtime.intake`.
    This class only composes those mixins so the workflow worker still receives
    one ProcessStageHandler type.
    """


__all__ = ["IntakePipeline"]
