"""Executor contract (F3-02) — the F3->F6 bridge.

The once-only execution invariant (G-CR4-03 / G-CR6-03 / G-CR7-06) requires a
single owner of terminal state. Executors MUST NOT write step terminal status,
advance the run, derive downstream steps, or commit. Instead an executor
*produces* an :class:`ExecutorResult` (downstream intent + run advance); the
kernel (:func:`workflow_core.retry.succeed_claim`) applies it inside the same
explicit ``BEGIN IMMEDIATE`` transaction, *after* re-confirming the claim is
still active. A claim that was reaped (lease expired) re-reads as inactive, so
its terminal state + downstream steps are never written twice.

Executor *data* side-effects (artifacts, chunks, vectors, objects) are written
by the executor directly, but with **deterministic idempotency keys** (not
``uuid4``), so a retried/re-executed step rewrites identical rows
(``INSERT OR IGNORE`` / ``INSERT OR REPLACE``) instead of duplicating them
(anti ⛔3).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from sqlite3 import Connection

from smind_common.time import utc_now_iso


@dataclass
class DownstreamStep:
    """A derived next step. ``step_key`` must be deterministic per run."""

    step_key: str
    stage: str
    action: str
    payload: dict


@dataclass
class ExecutorResult:
    """The kernel-applied intent of an executor — no terminal DB writes here."""

    downstream: list[DownstreamStep] = field(default_factory=list)
    run_advance: dict | None = None  # e.g. {"status": "running", "current_stage": "rag"}


def deterministic_artifact_id(step_id: str, suffix: str) -> str:
    """Stable artifact id for a (step, suffix) pair (idempotent re-execution)."""
    digest = hashlib.sha1(f"{step_id}:{suffix}".encode()).hexdigest()[:24]
    return f"art_{digest}"


def deterministic_step_id(workflow_run_id: str, step_key: str) -> str:
    """Stable downstream step id for a (run, step_key) pair."""
    digest = hashlib.sha1(f"{workflow_run_id}:{step_key}".encode()).hexdigest()[:24]
    return f"step_{digest}"


def apply_executor_result(
    conn: Connection,
    *,
    team_id: str,
    workflow_run_id: str,
    parent_step_id: str,
    result: ExecutorResult,
) -> None:
    """Apply an ExecutorResult's downstream steps + run advance.

    MUST be called inside the kernel's already-open ``BEGIN IMMEDIATE``
    transaction (⛔4: never open a new transaction here). Uses deterministic
    ids + ``ON CONFLICT DO NOTHING`` so a re-executed step never duplicates the
    derived steps or DAG edges.
    """
    for ds in result.downstream:
        new_step_id = deterministic_step_id(workflow_run_id, ds.step_key)
        conn.execute(
            """
            INSERT INTO workflow_steps(
              id, team_id, workflow_run_id, parent_step_id, step_key,
              stage, action, payload_json, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            ON CONFLICT(workflow_run_id, step_key) DO NOTHING
            """,
            (
                new_step_id,
                team_id,
                workflow_run_id,
                parent_step_id,
                ds.step_key,
                ds.stage,
                ds.action,
                json.dumps(ds.payload),
            ),
        )
        # F3-08: record the DAG edge (idempotent on (from,to,type)).
        conn.execute(
            """
            INSERT INTO workflow_step_links(id, workflow_run_id, from_step_id, to_step_id, link_type)
            VALUES (?, ?, ?, ?, 'next')
            ON CONFLICT(from_step_id, to_step_id, link_type) DO NOTHING
            """,
            (
                deterministic_step_id(workflow_run_id, f"link:{ds.step_key}"),
                workflow_run_id,
                parent_step_id,
                new_step_id,
            ),
        )

    if result.run_advance:
        adv = result.run_advance
        sets = ["status = ?", "current_stage = ?", "updated_at = ?"]
        params: list = [adv.get("status", "running"), adv.get("current_stage"), utc_now_iso()]
        if adv.get("status") == "completed":
            sets.append("finished_at = ?")
            params.append(utc_now_iso())
        params.append(workflow_run_id)
        conn.execute(
            f"UPDATE workflow_runs SET {', '.join(sets)} WHERE id = ?",
            params,
        )
