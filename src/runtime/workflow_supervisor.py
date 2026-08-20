"""Same-process durable worker supervision for the single MKB application."""

from __future__ import annotations

import asyncio

from src.runtime.workflow_engine import WorkflowRuntime, WorkflowWorker


class WorkflowSupervisor:
    """Drain durable outbox/process work without treating memory as a queue.

    Each iteration re-reads authoritative rows through ``WorkflowRuntime``.
    The loop is deliberately bounded so API requests, cancellation, and the
    health probe retain an opportunity to run in the single asyncio process.
    """

    def __init__(
        self,
        runtime: WorkflowRuntime,
        worker: WorkflowWorker,
        *,
        lease_owner: str = "mkb-leaf-worker",
        max_outbox_per_tick: int = 32,
        max_processes_per_tick: int = 16,
        idle_seconds: float = 0.05,
    ) -> None:
        if max_outbox_per_tick < 1 or max_processes_per_tick < 1 or idle_seconds <= 0:
            raise ValueError("workflow supervisor bounds must be positive")
        self.runtime = runtime
        self.worker = worker
        self.lease_owner = lease_owner
        self.max_outbox_per_tick = max_outbox_per_tick
        self.max_processes_per_tick = max_processes_per_tick
        self.idle_seconds = idle_seconds
        self.last_error: Exception | None = None
        self.consecutive_failures = 0
        # VF62: per-pool worker sets may be introduced later. Overlapping
        # ``run_once`` stays disabled until NS5-T04 heartbeat fencing is green.
        self.allow_overlapping_run_once = False

    async def drain_once(self) -> int:
        """Advance a bounded amount of durable work and return the progress count."""

        progressed = 0
        for _ in range(self.max_outbox_per_tick):
            try:
                if not await self.runtime.dispatch_outbox_once(self.lease_owner):
                    break
                progressed += 1
            except Exception as exc:
                self.last_error = exc
                self.consecutive_failures += 1
        for _ in range(self.max_processes_per_tick):
            try:
                if not await self.worker.run_once(self.lease_owner):
                    break
                progressed += 1
            except Exception as exc:
                self.last_error = exc
                self.consecutive_failures += 1
        return progressed + await self.runtime.repair_once()

    async def run(self, stop: asyncio.Event) -> None:
        """Run until lifecycle shutdown; exceptions stay visible to supervision."""

        while not stop.is_set():
            try:
                progressed = await self.drain_once()
                self.last_error = None
                self.consecutive_failures = 0
            except Exception as exc:
                # Durable rows retain their lease/retry evidence; one transient
                # adapter failure must not permanently kill the only in-process
                # supervisor and silently strand future work.
                self.last_error = exc
                self.consecutive_failures += 1
                progressed = 0
            timeout = 0.001 if progressed else self.idle_seconds
            try:
                await asyncio.wait_for(stop.wait(), timeout=timeout)
            except TimeoutError:
                pass


__all__ = ["WorkflowSupervisor"]
