"""Workflow graph helpers.

F3-07: the duplicate event writer ``write_workflow_event`` (dead code that
self-committed and wrote a malformed ``created_at``) was removed. The single
event writer is :func:`workflow_core.events.append_workflow_event`, which runs
inside the caller's transaction and lets the DDL DEFAULT stamp ``created_at``.

DAG edges (``workflow_step_links``) are written by
:func:`workflow_core.executors.apply_executor_result` when the kernel derives a
downstream step (F3-08), so there is no standalone graph writer here.
"""

from __future__ import annotations
