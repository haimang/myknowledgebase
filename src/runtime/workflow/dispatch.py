"""Pure dispatch policy, occupancy arithmetic, and pool definitions."""

from __future__ import annotations

from typing import Any, Literal

DISPATCH_LOCAL_RUNNING_CAP = 2
DISPATCH_LOCAL_QUEUED_CAP = 6
DISPATCH_NI_RUNNING_CAP = 2
DISPATCH_NI_QUEUED_CAP = 4
DISPATCH_EMBED_RUNNING_CAP = 8
DISPATCH_EMBED_QUEUED_CAP = 20
DISPATCH_LOCAL_CHAR_BUDGET = 16_000

DispatchPool = Literal["local-inference", "non-interactive", "embed"]
PoolKind = Literal["generate", "embed", "unpooled"]


def pool_kind(process_key: str, snapshot: dict[str, Any] | None = None) -> PoolKind:
    """Classify a process_key into a dispatch kind: generate, embed, or unpooled."""

    if process_key in {
        "lsrag.transcribe_markdown",
        "lsrag.structurize",
        "lsrag.construct",
        "clean.extract.web_llm",
        "clean.extract.doc_llm",
        "clean.extract.pdf_llm",
    }:
        return "generate"

    if process_key == "lsrag.vectorize":
        if snapshot is not None:
            l2 = snapshot.get("l2") or {}
            mode = l2.get("inference_mode")
            if mode == "live":
                return "embed"
            if mode == "deterministic":
                return "unpooled"
        return "embed"

    return "unpooled"


def choose_pool(
    priority: str,
    kind: str,
    *,
    local_queued: int = 0,
    ni_queued: int = 0,
    local_available: bool = True,
    ni_quota: bool = True,
    over_budget: bool = False,
    explicit_channel: str | None = None,
) -> str | None:
    """Determine the dispatch pool for a task based on lane, occupancy, and bounds.

    Returns:
        "local-inference" | "non-interactive" | "embed" | None
        None indicates the task must wait in orchestrator or is unpooled.
    """

    if kind == "unpooled":
        return None

    if kind == "embed":
        return "embed"

    if kind != "generate":
        return None

    # Handle explicit channel override if present
    if explicit_channel == "local-inference":
        if local_available and local_queued < DISPATCH_LOCAL_QUEUED_CAP:
            return "local-inference"
        return None

    if explicit_channel == "non-interactive":
        if ni_quota and ni_queued < DISPATCH_NI_QUEUED_CAP:
            return "non-interactive"
        return None

    if explicit_channel is not None:
        return None

    # Lane policy based on Task.priority
    if priority in {"urgent", "high"}:
        if ni_quota and ni_queued < DISPATCH_NI_QUEUED_CAP:
            return "non-interactive"
        return None

    if priority == "normal":
        if over_budget:
            if ni_quota and ni_queued < DISPATCH_NI_QUEUED_CAP:
                return "non-interactive"
            return None

        if local_available and local_queued < DISPATCH_LOCAL_QUEUED_CAP:
            return "local-inference"

        if ni_quota and ni_queued < DISPATCH_NI_QUEUED_CAP:
            return "non-interactive"
        return None

    if priority == "low":
        if local_available and local_queued < DISPATCH_LOCAL_QUEUED_CAP:
            return "local-inference"
        return None

    return None
