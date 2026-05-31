"""F1-05 integration tests: real time write-path + explicit-tx atomicity.

Covers T04 (reap via real SSOT now_iso write path, fixture mask removed),
T05 (clean finished_at no CURRENT_TIMESTAMP), T06 (BEGIN IMMEDIATE after bare
DML under autocommit), T07 (parametrized rollback of the 6 multi-write helpers).
"""

import re

import pytest

from smind_common.time import add_seconds_iso
from storage_sqlite.repositories.steps import StepRepository
from storage_sqlite.repositories.workflow import WorkflowRepository
from workflow_core.claim import claim_next_step
from workflow_core.leases import heartbeat_claim, reap_expired_claims
from workflow_core.purge import process_purge_requests
from workflow_core.restart import process_restart_requests
from workflow_core.retry import fail_claim, succeed_claim

from tests.fixtures.sqlite_kernel import make_kernel_dbs, seed_minimum_graph

ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def _seed_run_with_step(core_conn, *, step_id="step_p1", step_key="clean:seed"):
    ids = seed_minimum_graph(core_conn)
    WorkflowRepository(core_conn).create_run(
        run_id=ids["run_id"],
        team_id=ids["team_id"],
        source_id=ids["source_id"],
        document_id=ids["document_id"],
    )
    StepRepository(core_conn).create_step(
        step_id=step_id,
        team_id=ids["team_id"],
        workflow_run_id=ids["run_id"],
        step_key=step_key,
        stage="clean",
        action="mock",
        max_attempts=3,
    )
    return ids


def test_t04_reap_real_now_iso_write_path() -> None:
    """T04: reap an expired claim whose lease_expires_at was written via the
    REAL SSOT add_seconds_iso path, not the SQL-side strftime mask.

    Pre-fix the lease was written via the malformed _utils.now_iso format, so
    the v_stale_claims comparison was unreliable; this exercises that the
    Python-written lease value is comparable with the view's SQL strftime.
    """
    core_conn, _ = make_kernel_dbs()
    _seed_run_with_step(core_conn, step_id="step_expire", step_key="clean:expire")

    claim = claim_next_step(
        core_conn, worker_type="worker", worker_id="w1", lease_seconds=1
    )
    assert claim is not None

    # Real SSOT write path: a genuinely-past lease via add_seconds_iso(-1).
    past_lease = add_seconds_iso(-1)
    assert ISO_RE.match(past_lease)
    core_conn.execute(
        "UPDATE task_claims SET lease_expires_at = ? WHERE id = ?",
        (past_lease, claim["id"]),
    )

    assert reap_expired_claims(core_conn) == 1
    reclaim = claim_next_step(
        core_conn, worker_type="worker", worker_id="w3", lease_seconds=60
    )
    assert reclaim is not None
    assert reclaim["step_id"] == "step_expire"


def test_t05_clean_finished_at_no_current_timestamp() -> None:
    """T05: clean process_clean_step writes finished_at in SSOT format
    (not CURRENT_TIMESTAMP, which would be 'YYYY-MM-DD HH:MM:SS')."""
    from workflow_clean.service import process_clean_step

    core_conn, _ = make_kernel_dbs()
    ids = _seed_run_with_step(core_conn, step_id="step_clean", step_key="clean:init")

    class _NoopStore:
        def get_text(self, key):  # noqa: ANN001
            return "hello world"

    core_conn.execute(
        """
        INSERT INTO uploads (id, team_id, source_kind, object_key, status)
        VALUES ('up1', ?, 'file', 'k1', 'confirmed')
        """,
        (ids["team_id"],),
    )
    core_conn.execute(
        "UPDATE sources SET upload_id='up1' WHERE id = ?",
        (ids["source_id"],),
    )

    process_clean_step(core_conn, "step_clean", _NoopStore())

    row = core_conn.execute(
        "SELECT status, finished_at FROM workflow_steps WHERE id = 'step_clean'"
    ).fetchone()
    assert row["status"] == "succeeded"
    assert ISO_RE.match(row["finished_at"]), f"format drift: {row['finished_at']!r}"
    run = core_conn.execute(
        "SELECT updated_at FROM workflow_runs WHERE id = ?", (ids["run_id"],)
    ).fetchone()
    assert ISO_RE.match(run["updated_at"]), f"format drift: {run['updated_at']!r}"


def test_t06_begin_immediate_after_bare_dml_under_autocommit() -> None:
    """T06: under autocommit, a helper's BEGIN IMMEDIATE after a bare DML must
    not raise 'cannot start a transaction within a transaction'.

    Pre-fix (isolation_level='') the bare DML auto-opened an implicit
    transaction that was never committed, so the helper's BEGIN IMMEDIATE
    would raise (CR-2 R2).
    """
    core_conn, _ = make_kernel_dbs()
    _seed_run_with_step(core_conn, step_id="step_p1", step_key="clean:seed")

    claim = claim_next_step(
        core_conn, worker_type="worker", worker_id="w1", lease_seconds=60
    )
    assert claim is not None

    # Bare DML directly on the autocommit connection (no surrounding tx).
    core_conn.execute(
        "UPDATE workflow_steps SET priority = 50 WHERE id = 'step_p1'"
    )
    # heartbeat_claim opens its own BEGIN IMMEDIATE — must not raise.
    assert heartbeat_claim(core_conn, claim["claim_token"], lease_seconds=60) is True
    # succeed_claim likewise.
    assert succeed_claim(core_conn, claim["claim_token"]) is True


# --- T07: parametrized rollback of the 6 multi-write helpers ----------------


class _Boom(RuntimeError):
    pass


class _FailingConn:
    """Wraps a real conn, raising _Boom on the Nth write execute().

    BEGIN IMMEDIATE / COMMIT / ROLLBACK and SELECTs are forwarded verbatim so
    the helper's own transaction control still works; only the Nth
    UPDATE/INSERT/DELETE raises, to inject a mid-transaction failure.
    """

    def __init__(self, conn, fail_on_nth_write):
        self._conn = conn
        self._writes = 0
        self._fail_on = fail_on_nth_write

    def execute(self, sql, *args):
        stripped = sql.strip().upper()
        if stripped.startswith(("UPDATE", "INSERT", "DELETE")):
            self._writes += 1
            if self._writes == self._fail_on:
                raise _Boom("injected mid-write failure")
        return self._conn.execute(sql, *args)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()


def _snapshot(conn):
    def dump(sql):
        return [tuple(r) for r in conn.execute(sql).fetchall()]

    return {
        "steps": dump(
            "SELECT id, status, attempt_count, available_at, finished_at, "
            "error_code FROM workflow_steps ORDER BY id"
        ),
        "claims": dump(
            "SELECT id, status, lease_expires_at, finished_at "
            "FROM task_claims ORDER BY id"
        ),
        "attempts": dump(
            "SELECT id, termination_reason FROM step_attempts ORDER BY id"
        ),
        "restart": dump("SELECT id, status FROM restart_requests ORDER BY id"),
        "purge": dump("SELECT id, status FROM purge_requests ORDER BY id"),
        "chunks": dump("SELECT id, vec_status FROM chunks ORDER BY id"),
        "documents": dump("SELECT id, status FROM documents ORDER BY id"),
    }


def _claimed(core_conn):
    _seed_run_with_step(core_conn)
    claim = claim_next_step(
        core_conn, worker_type="worker", worker_id="w1", lease_seconds=60
    )
    assert claim is not None
    return claim


def _case_succeed(core_conn):
    claim = _claimed(core_conn)
    return lambda c: succeed_claim(c, claim["claim_token"])


def _case_fail(core_conn):
    claim = _claimed(core_conn)
    return lambda c: fail_claim(c, claim["claim_token"], retry_backoff_seconds=0)


def _case_heartbeat(core_conn):
    claim = _claimed(core_conn)
    return lambda c: heartbeat_claim(c, claim["claim_token"])


def _case_reap(core_conn):
    claim = _claimed(core_conn)
    core_conn.execute(
        "UPDATE task_claims SET lease_expires_at = ? WHERE id = ?",
        (add_seconds_iso(-1), claim["id"]),
    )
    return lambda c: reap_expired_claims(c)


def _case_restart(core_conn):
    ids = _seed_run_with_step(core_conn)
    core_conn.execute(
        """
        INSERT INTO restart_requests (id, team_id, workflow_run_id, mode, scope_json)
        VALUES ('rr1', ?, ?, 'recovery', '{}')
        """,
        (ids["team_id"], ids["run_id"]),
    )
    return lambda c: process_restart_requests(c)


def _case_purge(core_conn):
    ids = _seed_run_with_step(core_conn)
    core_conn.execute(
        """
        INSERT INTO chunks (
            id, team_id, workflow_run_id, document_id, chunk_index, content_hash
        ) VALUES ('chk1', ?, ?, ?, 0, 'h1')
        """,
        (ids["team_id"], ids["run_id"], ids["document_id"]),
    )
    core_conn.execute(
        """
        INSERT INTO purge_requests (id, team_id, target_kind, target_id, scope_json)
        VALUES ('pr1', ?, 'document', ?, '{}')
        """,
        (ids["team_id"], ids["document_id"]),
    )
    return lambda c: process_purge_requests(c, None)


HELPER_CASES = [
    ("succeed_claim", _case_succeed, 1),
    ("fail_claim", _case_fail, 1),
    ("heartbeat_claim", _case_heartbeat, 1),
    ("reap_expired_claims", _case_reap, 2),
    ("process_restart_requests", _case_restart, 2),
    ("process_purge_requests", _case_purge, 2),
]


@pytest.mark.parametrize(
    "name,setup,fail_on",
    HELPER_CASES,
    ids=[c[0] for c in HELPER_CASES],
)
def test_t07_helper_rollback_on_midwrite_exception(name, setup, fail_on) -> None:
    """T07: a mid-write exception rolls back the WHOLE helper transaction.

    Snapshot pre-state, run the helper through a conn that raises mid-write,
    and assert every observable row is unchanged (0 residual partial writes).
    """
    core_conn, _ = make_kernel_dbs()
    call = setup(core_conn)

    before = _snapshot(core_conn)

    failing = _FailingConn(core_conn, fail_on)
    with pytest.raises(_Boom):
        call(failing)

    after = _snapshot(core_conn)
    assert after == before, f"{name}: partial write survived rollback"
