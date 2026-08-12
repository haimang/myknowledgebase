"""WorkflowRuntime composition root."""

from __future__ import annotations

from src.runtime.workflow.runtime_core import WorkflowCoreMixin
from src.runtime.workflow.runtime_gates import WorkflowGatesMixin
from src.runtime.workflow.runtime_materialize import WorkflowMaterializeMixin
from src.runtime.workflow.runtime_outbox import WorkflowOutboxMixin
from src.runtime.workflow.runtime_outcome import WorkflowOutcomeMixin
from src.runtime.workflow.runtime_repair import WorkflowRepairMixin
from src.runtime.workflow.runtime_scatter import WorkflowScatterMixin


class WorkflowRuntime(
    WorkflowCoreMixin,
    WorkflowOutcomeMixin,
    WorkflowMaterializeMixin,
    WorkflowScatterMixin,
    WorkflowGatesMixin,
    WorkflowOutboxMixin,
    WorkflowRepairMixin,
):
    """Durable workflow runtime."""
