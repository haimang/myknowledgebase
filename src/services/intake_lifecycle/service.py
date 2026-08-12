"""IntakeLifecycleService composition."""

from __future__ import annotations

from src.services.intake_lifecycle.lifecycle_apply import LifecycleApplyMixin
from src.services.intake_lifecycle.lifecycle_publish import LifecyclePublishMixin


class IntakeLifecycleService(LifecycleApplyMixin, LifecyclePublishMixin):
    """Intake lifecycle and publication transitions."""
