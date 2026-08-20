"""Pure dispatch policy, occupancy arithmetic, and pool definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from src.persistence.ports import UnitOfWork
    from src.runtime.config import Settings

DISPATCH_LOCAL_RUNNING_CAP = 2
DISPATCH_LOCAL_QUEUED_CAP = 6
DISPATCH_NI_RUNNING_CAP = 2
DISPATCH_NI_QUEUED_CAP = 4
DISPATCH_EMBED_RUNNING_CAP = 8
DISPATCH_EMBED_QUEUED_CAP = 20
DISPATCH_LOCAL_CHAR_BUDGET = 16_000

GENERATE_PROCESS_KEYS = frozenset(
    {
        "lsrag.transcribe_markdown",
        "lsrag.structurize",
        "lsrag.construct",
        "clean.extract.web_llm",
        "clean.extract.doc_llm",
        "clean.extract.pdf_llm",
    }
)
OVER_BUDGET_PROCESS_KEYS = frozenset(
    {
        "lsrag.structurize",
        "lsrag.construct",
        "lsrag.transcribe_markdown",
        "clean.extract.web_llm",
        "clean.extract.doc_llm",
        "clean.extract.pdf_llm",
    }
)
POOLED_PROCESS_KEYS = GENERATE_PROCESS_KEYS | {"lsrag.vectorize"}

DispatchPool = Literal["local-inference", "non-interactive", "embed"]
PoolKind = Literal["generate", "embed", "unpooled"]


@dataclass(frozen=True)
class DispatchCaps:
    """Runtime-injected pool capacities. Defaults match the frozen NS2 constants."""

    local_running: int = DISPATCH_LOCAL_RUNNING_CAP
    local_queued: int = DISPATCH_LOCAL_QUEUED_CAP
    ni_running: int = DISPATCH_NI_RUNNING_CAP
    ni_queued: int = DISPATCH_NI_QUEUED_CAP
    embed_running: int = DISPATCH_EMBED_RUNNING_CAP
    embed_queued: int = DISPATCH_EMBED_QUEUED_CAP
    local_char_budget: int = DISPATCH_LOCAL_CHAR_BUDGET

    @classmethod
    def from_settings(cls, settings: Settings) -> DispatchCaps:
        return cls(
            local_running=settings.dispatch_local_running,
            local_queued=settings.dispatch_local_queued,
            ni_running=settings.dispatch_ni_running,
            ni_queued=settings.dispatch_ni_queued,
            embed_running=settings.dispatch_embed_running,
            embed_queued=settings.dispatch_embed_queued,
            local_char_budget=settings.dispatch_local_char_budget,
        )


@dataclass(frozen=True)
class PoolOccupancy:
    running: int
    queued: int
    waiting: int = 0


async def get_pool_occupancies(tx: UnitOfWork) -> dict[str, PoolOccupancy]:
    """Query current running and admitted queued counts for each dispatch pool."""

    rows = await tx.fetchall(
        """
        SELECT dispatch_pool,
               SUM(CASE WHEN status IN ('claimed', 'running') THEN 1 ELSE 0 END) AS running_count,
               SUM(CASE WHEN status = 'ready' AND dispatch_admitted = 1 THEN 1 ELSE 0 END) AS queued_count
        FROM mkb_processes
        WHERE dispatch_pool IS NOT NULL
        GROUP BY dispatch_pool
        """
    )
    result = {
        "local-inference": PoolOccupancy(running=0, queued=0),
        "non-interactive": PoolOccupancy(running=0, queued=0),
        "embed": PoolOccupancy(running=0, queued=0),
    }
    for row in rows:
        pool = row["dispatch_pool"]
        if pool in result:
            result[pool] = PoolOccupancy(
                running=int(row.get("running_count") or 0),
                queued=int(row.get("queued_count") or 0),
            )
    return result


async def get_waiting_count(tx: UnitOfWork) -> int:
    """Count ready processes that still need a generate/embed pool slot."""

    placeholders = ",".join("?" for _ in POOLED_PROCESS_KEYS)
    row = await tx.fetchone(
        f"""
        SELECT COUNT(*) AS waiting_count
        FROM mkb_processes
        WHERE status = 'ready' AND dispatch_admitted = 0
          AND process_key IN ({placeholders})
        """,
        tuple(sorted(POOLED_PROCESS_KEYS)),
    )
    return int(row.get("waiting_count") or 0) if row else 0


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
    local_queued_cap: int = DISPATCH_LOCAL_QUEUED_CAP,
    ni_queued_cap: int = DISPATCH_NI_QUEUED_CAP,
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
        if local_available and local_queued < local_queued_cap:
            return "local-inference"
        return None

    if explicit_channel == "non-interactive":
        if ni_quota and ni_queued < ni_queued_cap:
            return "non-interactive"
        return None

    if explicit_channel is not None:
        return None

    # Lane policy based on Task.priority
    if priority in {"urgent", "high"}:
        if ni_quota and ni_queued < ni_queued_cap:
            return "non-interactive"
        return None

    if priority == "normal":
        if over_budget:
            if ni_quota and ni_queued < ni_queued_cap:
                return "non-interactive"
            return None

        if local_available and local_queued < local_queued_cap:
            return "local-inference"

        if ni_quota and ni_queued < ni_queued_cap:
            return "non-interactive"
        return None

    if priority == "low":
        if local_available and local_queued < local_queued_cap:
            return "local-inference"
        return None

    return None
