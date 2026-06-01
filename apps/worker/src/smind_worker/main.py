import argparse
import time

from smind_common.logging import get_logger
from smind_config.loader import load_settings
from storage_objects import FileSystemObjectStore
from storage_sqlite.engine import CoreSQLiteEngine
from storage_sqlite.migrations.runner import apply_core_migrations
from vector_sqlite_vec import VecSQLiteEngine, apply_vec_schema
from workflow_clean import process_clean_step
from workflow_core import (
    WorkflowScheduler,
    fail_claim,
    heartbeat_claim,
    process_purge_requests,
    process_restart_requests,
    reap_expired_claims,
    succeed_claim,
)
from workflow_rag import process_rag_step


def run_worker(*, once: bool, poll_interval: float) -> int:
    settings = load_settings()
    logger = get_logger("smind.worker")
    core_conn = CoreSQLiteEngine(settings.core_db_path).connect()
    vec_conn = VecSQLiteEngine(settings.vec_db_path).connect()
    apply_core_migrations(core_conn)
    apply_vec_schema(vec_conn)
    object_store = FileSystemObjectStore(settings.object_store_dir)
    scheduler = WorkflowScheduler(core_conn, worker_type="worker", worker_id="local")

    logger.info("worker boot env=%s", settings.app_env)
    logger.info("worker poll interval=%.2fs", poll_interval)

    def _run_once() -> bool:
        # F3-01: reap expired claims first so stalled steps return to the ready
        # set before this worker claims (now hits after F1 fixed time compare).
        reaped = reap_expired_claims(core_conn)
        if reaped:
            logger.info("reaped %d expired claim(s)", reaped)
        process_restart_requests(core_conn)
        process_purge_requests(core_conn, vec_conn, object_store)
        claim = scheduler.claim_one()
        if claim is None:
            return False
        heartbeat_claim(core_conn, claim["claim_token"])
        step = core_conn.execute(
            "SELECT * FROM workflow_steps WHERE id = ?",
            (claim["step_id"],),
        ).fetchone()
        try:
            # F3-02: executors only produce an ExecutorResult (downstream + run
            # advance) + idempotent data writes; the kernel (succeed_claim) owns
            # terminal state in one transaction after re-checking the claim.
            if step["stage"].startswith("clean"):
                result = process_clean_step(core_conn, step["id"], object_store)
            elif step["stage"].startswith("rag:"):
                result = process_rag_step(
                    core_conn, vec_conn, settings.app_env, step["id"], object_store
                )
            else:
                raise ValueError(f"unsupported stage: {step['stage']}")
            # F3-03: check the return value. False => claim was reaped/lost; the
            # executor's idempotent data writes are harmless, terminal state was
            # NOT applied (no double execution).
            ok = succeed_claim(core_conn, claim["claim_token"], result)
            if not ok:
                logger.warning(
                    "claim %s no longer active at succeed; terminal state not applied",
                    claim["claim_token"],
                )
        except Exception as exc:  # noqa: BLE001
            logger.exception("worker step failed: %s", exc)
            failed = fail_claim(core_conn, claim["claim_token"], error_message=str(exc))
            if not failed:
                logger.warning("claim %s no longer active at fail", claim["claim_token"])
        return True

    if once:
        _run_once()
        logger.info("worker once mode, exiting")
        return 0
    while True:
        did_work = _run_once()
        if not did_work:
            time.sleep(poll_interval)


def main() -> int:
    parser = argparse.ArgumentParser(description="smind-family worker")
    parser.add_argument("--once", action="store_true", help="run one loop and exit")
    parser.add_argument("--poll-interval", type=float, default=1.0)
    args = parser.parse_args()
    return run_worker(once=args.once, poll_interval=args.poll_interval)


if __name__ == "__main__":
    raise SystemExit(main())
