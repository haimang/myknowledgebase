"""TaskService composition root."""

from __future__ import annotations

from src.runtime.task.task_commands import TaskCommandsMixin
from src.runtime.task.task_create import TaskCreateMixin
from src.runtime.task.task_projections import TaskProjectionsMixin
from src.runtime.task.task_views import TaskViewsMixin


class TaskService(
    TaskViewsMixin,
    TaskCreateMixin,
    TaskCommandsMixin,
    TaskProjectionsMixin,
):
    """S01/S02 Task aggregate service."""
