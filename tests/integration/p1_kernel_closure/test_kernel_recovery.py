"""FF-F3 kernel recovery + once-only semantics regressions.

先红后绿 ([Q7]): every test here fails on the pre-F3 code (executor self-commit
+ no executor contract + always-clean restart + hardcoded 1s backoff) and passes
after F3. The double-execution harness goes through the REAL now_iso lease write
path (claim with a negative lease so it is already expired) — no hand-written SQL
overriding lease_expires_at (anti G-CR8-02 fixture masking).
"""

from __future__ import annotations

import re
import tempfile

from smind_common.time import utc_now_iso
from storage_objects import FileSystemObjectStore
from workflow_core.claim import claim_next_step
from workflow_core.leases import reap_expired_claims
from workflow_core.restart import process_restart_requests
from workflow_core.retry import fail_claim, succeed_claim
from workflow_clean.service import process_clean_step

from tests.fixtures.sqlite_kernel import make_kernel_dbs, seed_minimum_graph

_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def _store() -> FileSystemObjectStore:
    return FileSystemObjectStore(tempfile.mkdtemp(prefix="ff-f3-"))


def _seed_run_with_clean_step(core_conn, step_id: str = "step_clean") -> dict:
    ids = seed_minimum_graph(core_conn)
    core_conn.execute(
        """
        INSERT INTO workflow_runs (id, team_id, source_id, document_id,
            workflow_kind, trigger_kind, config_snapshot_json, current_stage, status)
        VALUES (?, ?, ?, ?, 'full', 'api', '{}', 'clean', 'running')
        """,
        (ids["run_id"], ids["team_id"], ids["source_id"], ids["document_id"]),
    )
    core_conn.execute(
        """
        INSERT INTO workflow_steps (id, team_id, workflow_run_id, step_key,
            stage, action, payload_json, status)
        VALUES (?, ?, ?, 'clean:init', 'clean', 'clean.start', '{}', 'pending')
        """,
        (step_id, ids["team_id"], ids["run_id"]),
    )
    core_conn.commit()
    return ids


def _count(core_conn, sql: str, params: tuple) -> int:
    return int(core_conn.execute(sql, params).fetchone()[0])


def test_t14_concurrent_no_double_execution() -> None:
    """A reaped (expired) claim's late succeed must NOT apply terminal state or
    create duplicate downstream steps/artifacts — at-most-once under race."""
    core_conn, _ = make_kernel_dbs()
    ids = _seed_run_with_clean_step(core_conn)

    # worker-A claims with an already-expired lease (real now_iso write path).
    claim_a = claim_next_step(core_conn, worker_type="w", worker_id="A", lease_seconds=-1)
    assert claim_a is not None
    result_a = process_clean_step(core_conn, claim_a["step_id"], _store())

    # reap returns the expired claim's step to the ready set.
    assert reap_expired_claims(core_conn) == 1

    # worker-B re-claims the same step and succeeds.
    claim_b = claim_next_step(core_conn, worker_type="w", worker_id="B", lease_seconds=60)
    assert claim_b is not None and claim_b["step_id"] == claim_a["step_id"]
    result_b = process_clean_step(core_conn, claim_b["step_id"], _store())
    assert succeed_claim(core_conn, claim_b["claim_token"], result_b) is True

    # worker-A's late succeed: claim no longer active -> False, no side effects.
    assert succeed_claim(core_conn, claim_a["claim_token"], result_a) is False

    # at-most-once: exactly one cleaned artifact + one downstream structurize step.
    assert _count(
        core_conn,
        "SELECT COUNT(*) FROM artifacts WHERE workflow_run_id=? AND artifact_type='cleaned_text'",
        (ids["run_id"],),
    ) == 1
    assert _count(
        core_conn,
        "SELECT COUNT(*) FROM workflow_steps WHERE workflow_run_id=? AND stage='rag:structurize'",
        (ids["run_id"],),
    ) == 1


def test_t06_succeed_claim_applies_downstream_and_run_advance() -> None:
    """Kernel (not the executor) writes terminal state + downstream + run advance."""
    core_conn, _ = make_kernel_dbs()
    ids = _seed_run_with_clean_step(core_conn)
    claim = claim_next_step(core_conn, worker_type="w", worker_id="A", lease_seconds=60)
    result = process_clean_step(core_conn, claim["step_id"], _store())
    assert succeed_claim(core_conn, claim["claim_token"], result) is True

    step = core_conn.execute(
        "SELECT status FROM workflow_steps WHERE id=?", (claim["step_id"],)
    ).fetchone()
    assert step["status"] == "succeeded"
    run = core_conn.execute(
        "SELECT status, current_stage FROM workflow_runs WHERE id=?", (ids["run_id"],)
    ).fetchone()
    assert run["current_stage"] == "rag"
    # F3-08: the DAG edge to the downstream step was recorded.
    assert _count(
        core_conn,
        "SELECT COUNT(*) FROM workflow_step_links WHERE workflow_run_id=?",
        (ids["run_id"],),
    ) == 1


def test_t07_idempotent_replay_no_duplicates() -> None:
    """Re-executing the same step (deterministic ids) does not duplicate rows."""
    core_conn, _ = make_kernel_dbs()
    ids = _seed_run_with_clean_step(core_conn)
    claim = claim_next_step(core_conn, worker_type="w", worker_id="A", lease_seconds=60)
    # run the executor twice against the same step.
    process_clean_step(core_conn, claim["step_id"], _store())
    process_clean_step(core_conn, claim["step_id"], _store())
    core_conn.commit()
    assert _count(
        core_conn,
        "SELECT COUNT(*) FROM artifacts WHERE workflow_run_id=? AND artifact_type='cleaned_text'",
        (ids["run_id"],),
    ) == 1


def test_t09_restart_recovery_anchors_on_failed_stage() -> None:
    """recovery restart resets only the failed step's stage, not succeeded clean."""
    core_conn, _ = make_kernel_dbs()
    ids = seed_minimum_graph(core_conn)
    core_conn.execute(
        """
        INSERT INTO workflow_runs (id, team_id, source_id, document_id,
            workflow_kind, trigger_kind, config_snapshot_json, current_stage, status)
        VALUES (?, ?, ?, ?, 'full', 'api', '{}', 'rag', 'failed')
        """,
        (ids["run_id"], ids["team_id"], ids["source_id"], ids["document_id"]),
    )
    core_conn.execute(
        """
        INSERT INTO workflow_steps (id, team_id, workflow_run_id, step_key,
            stage, action, payload_json, status)
        VALUES ('s_clean', ?, ?, 'clean:init', 'clean', 'clean.start', '{}', 'succeeded')
        """,
        (ids["team_id"], ids["run_id"]),
    )
    core_conn.execute(
        """
        INSERT INTO workflow_steps (id, team_id, workflow_run_id, step_key,
            stage, action, payload_json, status)
        VALUES ('s_rag', ?, ?, 'rag:structurize', 'rag:structurize', 'rag.structurize', '{}', 'failed')
        """,
        (ids["team_id"], ids["run_id"]),
    )
    core_conn.execute(
        """
        INSERT INTO restart_requests (id, team_id, workflow_run_id, mode, scope_json, status)
        VALUES ('rr1', ?, ?, 'recovery', '{}', 'pending')
        """,
        (ids["team_id"], ids["run_id"]),
    )
    core_conn.commit()

    assert process_restart_requests(core_conn) == 1

    clean = core_conn.execute("SELECT status FROM workflow_steps WHERE id='s_clean'").fetchone()
    rag = core_conn.execute(
        "SELECT status, available_at FROM workflow_steps WHERE id='s_rag'"
    ).fetchone()
    run = core_conn.execute(
        "SELECT status, current_stage FROM workflow_runs WHERE id=?", (ids["run_id"],)
    ).fetchone()
    # clean (succeeded) is NOT reset; rag (failed) is reset to pending & ready.
    assert clean["status"] == "succeeded"
    assert rag["status"] == "pending"
    assert rag["available_at"] <= utc_now_iso()
    assert run["status"] == "running"
    # anchor is the failed step's own stage (rag:structurize), not the coarse
    # 'rag' — recovery reset only the failed work, leaving succeeded clean alone.
    assert run["current_stage"] == "rag:structurize"


def test_t10_restart_force_mode_is_deferred() -> None:
    """force/kickstart modes are explicitly not supported this round ([Q4])."""
    core_conn, _ = make_kernel_dbs()
    ids = seed_minimum_graph(core_conn)
    core_conn.execute(
        """
        INSERT INTO workflow_runs (id, team_id, source_id, document_id,
            workflow_kind, trigger_kind, config_snapshot_json, current_stage, status)
        VALUES (?, ?, ?, ?, 'full', 'api', '{}', 'rag', 'failed')
        """,
        (ids["run_id"], ids["team_id"], ids["source_id"], ids["document_id"]),
    )
    core_conn.execute(
        """
        INSERT INTO restart_requests (id, team_id, workflow_run_id, mode, scope_json, status)
        VALUES ('rr2', ?, ?, 'force_recovery', '{}', 'pending')
        """,
        (ids["team_id"], ids["run_id"]),
    )
    core_conn.commit()
    process_restart_requests(core_conn)
    rr = core_conn.execute("SELECT status, error_message FROM restart_requests WHERE id='rr2'").fetchone()
    assert rr["status"] == "failed"
    assert "recovery" in (rr["error_message"] or "")


def test_t11_fail_claim_exponential_backoff_reads_schema_column() -> None:
    """fail_claim with no explicit backoff reads the step's schema column and
    schedules a future retry (not the old hardcoded 1s)."""
    core_conn, _ = make_kernel_dbs()
    ids = _seed_run_with_clean_step(core_conn, step_id="s_backoff")
    # give the step a distinctive base backoff.
    core_conn.execute(
        "UPDATE workflow_steps SET retry_backoff_seconds=120, max_attempts=5 WHERE id='s_backoff'"
    )
    core_conn.commit()
    claim = claim_next_step(core_conn, worker_type="w", worker_id="A", lease_seconds=60)
    assert claim is not None
    # no explicit retry_backoff_seconds -> reads schema column (120s, attempt 1).
    assert fail_claim(core_conn, claim["claim_token"], error_message="boom") is True
    step = core_conn.execute(
        "SELECT status, available_at FROM workflow_steps WHERE id='s_backoff'"
    ).fetchone()
    assert step["status"] == "retry_wait"
    # available_at must be well into the future (>=~120s), proving the column was
    # read rather than the old hardcoded 1s.
    assert step["available_at"] > utc_now_iso()
    secs = core_conn.execute(
        "SELECT (julianday(?) - julianday(?)) * 86400 AS d",
        (step["available_at"], utc_now_iso()),
    ).fetchone()["d"]
    assert secs > 60, f"backoff only {secs}s, expected ~120s"


def test_t12_single_event_writer_and_created_at_format() -> None:
    """graph.write_workflow_event is gone (F3-07); the surviving writer lets the
    DDL DEFAULT stamp a correct SSOT created_at."""
    import workflow_core.graph as graph

    assert not hasattr(graph, "write_workflow_event")

    core_conn, _ = make_kernel_dbs()
    ids = _seed_run_with_clean_step(core_conn)
    claim = claim_next_step(core_conn, worker_type="w", worker_id="A", lease_seconds=60)
    succeed_claim(core_conn, claim["claim_token"])
    row = core_conn.execute(
        "SELECT created_at FROM workflow_events WHERE workflow_run_id=? LIMIT 1",
        (ids["run_id"],),
    ).fetchone()
    assert row is not None
    assert _TS_RE.match(row["created_at"]), f"bad created_at: {row['created_at']}"
