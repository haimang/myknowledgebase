"""Shared status/priority constants for the workflow runtime."""

from __future__ import annotations

from src.contracts.common.models import ExecutionStatus, ProcessStatus

_TERMINAL_EXECUTION_STATUSES = {
    ExecutionStatus.SUCCEEDED.value,
    ExecutionStatus.FAILED.value,
    ExecutionStatus.CANCELLED.value,
}
_TERMINAL_PROCESS_STATUSES = {
    ProcessStatus.SUCCEEDED.value,
    ProcessStatus.FAILED.value,
    ProcessStatus.CANCELLED.value,
}
_ACTIVE_PROCESS_STATUSES = {
    ProcessStatus.READY.value,
    ProcessStatus.CLAIMED.value,
    ProcessStatus.RUNNING.value,
    ProcessStatus.RETRY_WAIT.value,
    ProcessStatus.CANCELLING.value,
}
_TASK_PRIORITY_RANK = {
    "low": 100,
    "normal": 200,
    "high": 300,
    "urgent": 400,
}

__all__ = [
    "_TERMINAL_EXECUTION_STATUSES",
    "_TERMINAL_PROCESS_STATUSES",
    "_ACTIVE_PROCESS_STATUSES",
    "_TASK_PRIORITY_RANK",
]
