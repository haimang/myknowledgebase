"""S15 contracts that must hold even when observability itself is unhealthy."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

import pytest

from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.metrics import default_metrics
from src.services.observability import DiagnosticSink, ObservabilityReadService, ObservabilityRetentionService


def test_metric_catalogue_rejects_ad_hoc_families_and_high_cardinality_samples() -> None:
    metrics = default_metrics()

    metrics.increment("mkb_sec_auth_total", result="ok")
    metrics.increment("mkb_sec_auth_total", result=uuid7())
    metrics.increment("mkb_readiness", component="/unbounded/caller/path")
    metrics.increment("mkb_sec_auth_total", task_uuid=uuid7())

    with pytest.raises(ValueError, match="static S15 catalogue"):
        metrics.register("mkb_experimental_by_task_total", "counter", ("task_uuid",))
    # Re-declaring a reviewed family is harmless, which makes composition
    # explicit without granting an extension point.
    metrics.register("mkb_readiness", "gauge", ("component",))

    rendered = metrics.render()
    assert 'mkb_sec_auth_total{result="ok"} 1.0' in rendered
    assert "mkb_experimental_by_task_total" not in rendered
    assert "/unbounded/caller/path" not in rendered
    assert metrics.cardinality_drops == 3


@pytest.mark.asyncio
async def test_diagnostic_sink_redacts_records_tracks_missing_trace_and_never_raises(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "diagnostics.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    team_uuid = uuid7()
    async with persistence.transaction() as tx:
        now = utc_now()
        await tx.execute(
            "INSERT INTO mkb_teams (team_uuid,name,creation_fingerprint,created_at,updated_at) VALUES (?,?,?,?,?)",
            (team_uuid, "diagnostics", stable_digest({"team": "diagnostics"}), now, now),
        )
    try:
        metrics = default_metrics()
        sink = DiagnosticSink(persistence, metrics)
        assert await sink.write(
            log_code="TEST_DIAGNOSTIC",
            message="Authorization: Bearer should-not-leak at /srv/mkb/log.txt",
            calling_module="tests.observability",
            team_uuid=team_uuid,
            payload={"token": "should-not-leak", "safe": "ok"},
        )
        assert await sink.write(
            log_code="TEST_DIAGNOSTIC",
            message="trace present",
            calling_module="tests.observability",
            team_uuid=team_uuid,
            trace_uuid=uuid7(),
        )
        async with persistence.transaction() as tx:
            rows = await tx.fetchall("SELECT log_message,payload_json FROM mkb_ops_diagnostic_logs ORDER BY occurred_at,log_uuid")
        serialized = json.dumps(rows)
        assert "should-not-leak" not in serialized
        assert "/srv/mkb/log.txt" not in serialized
        assert "[REDACTED]" in serialized
        assert "mkb_diagnostic_missing_trace_ratio 0.5" in metrics.render()
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_operator_projections_return_digests_not_event_payloads_and_complete_dead_fields(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "operator-projection.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    team_uuid, trace_uuid = uuid7(), uuid7()
    now = utc_now()
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_teams (team_uuid,name,creation_fingerprint,created_at,updated_at) VALUES (?,?,?,?,?)",
            (team_uuid, "operator", stable_digest({"team": "operator"}), now, now),
        )
        await tx.execute(
            "INSERT INTO mkb_domain_events "
            "(event_uuid,team_uuid,trace_uuid,event_type,aggregate,severity,actor_kind,summary,payload_digest,payload_json,"
            "schema_version,occurred_at,recorded_at,payload_extra) VALUES (?,?,?,'task.created','task','info','system',?,?,?"
            ",'mkb.domain-event.v1',?,?,'{}')",
            (
                uuid7(),
                team_uuid,
                trace_uuid,
                "safe event",
                stable_digest({"secret": "not-returned"}),
                '{"token":"not-returned"}',
                now,
                now,
            ),
        )
        await tx.execute(
            "INSERT INTO mkb_outbox "
            "(outbox_id,team_uuid,kind,payload_json,payload_digest,dedupe_key,status,available_at,created_at,updated_at,payload_extra) "
            "VALUES (?,?, 'wake_process','{}',?,'operator-dead','dead',?,?,?,'{}')",
            (uuid7(), team_uuid, stable_digest({}), now, now, now),
        )
    try:
        reader = ObservabilityReadService(persistence)
        timeline, _ = await reader.timeline_by_trace(team_uuid, trace_uuid)
        assert timeline[0]["trace_uuid"] == trace_uuid
        assert timeline[0]["payload_digest"] == stable_digest({"secret": "not-returned"})
        assert "payload" not in timeline[0]
        assert "not-returned" not in json.dumps(timeline[0])

        dead, _ = await reader.dead_outbox(team_uuid)
        assert dead == [
            {
                "outbox_id": dead[0]["outbox_id"],
                "team_uuid": team_uuid,
                "kind": "wake_process",
                "status": "dead",
                "attempts": 0,
                "last_error": "",
                "created_at": now,
                "updated_at": now,
            }
        ]
    finally:
        await persistence.close()


class _BrokenPersistence:
    @asynccontextmanager
    async def transaction(self):  # type: ignore[no-untyped-def]
        raise RuntimeError("diagnostic store unavailable")
        yield


@pytest.mark.asyncio
async def test_diagnostic_sink_failure_is_best_effort_but_visible() -> None:
    metrics = default_metrics()
    stderr_lines: list[str] = []
    sink = DiagnosticSink(_BrokenPersistence(), metrics, stderr=stderr_lines.append)  # type: ignore[arg-type]

    assert not await sink.write(
        log_code="TEST_DIAGNOSTIC",
        message="Authorization: Bearer should-not-leak at /srv/mkb/log.txt",
        calling_module="tests.observability",
    )

    rendered = metrics.render()
    assert 'mkb_diagnostic_drop_total{reason="append_fail"} 1.0' in rendered
    emitted = "\n".join(stderr_lines)
    assert "OBS_DIAG_APPEND_FAIL" in emitted
    assert "should-not-leak" not in emitted
    assert "/srv/mkb/log.txt" not in emitted


class _FailingRetention(ObservabilityRetentionService):
    async def _delete_batch(self, table: str, primary_key: str, cutoff: str) -> int:
        del table, primary_key, cutoff
        raise RuntimeError("retention backend unavailable")


@pytest.mark.asyncio
async def test_retention_failure_is_counted_and_diagnosed_without_business_mutation(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "retention-failure.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    try:
        metrics = default_metrics()
        sink = DiagnosticSink(persistence, metrics, stderr=lambda _line: None)
        retention = _FailingRetention(persistence, metrics, diagnostics=sink)

        with pytest.raises(RuntimeError, match="retention backend unavailable"):
            await retention.run_once()

        rendered = metrics.render()
        assert "mkb_retention_job_success 0" in rendered
        assert "mkb_retention_job_fail_total 1.0" in rendered
        async with persistence.transaction() as tx:
            rows = await tx.fetchall("SELECT log_code FROM mkb_ops_diagnostic_logs")
            tasks = await tx.fetchone("SELECT count(*) AS count FROM mkb_tasks")
        assert rows == [{"log_code": "OBS_RETENTION_JOB_FAIL"}]
        assert tasks == {"count": 0}
    finally:
        await persistence.close()
