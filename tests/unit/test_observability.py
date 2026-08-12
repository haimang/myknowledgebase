"""S15 bounded operator-read and retention tests against the real schema."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.metrics import default_metrics
from src.services.observability import ObservabilityReadService, ObservabilityRetentionService, RetentionPolicy


async def _environment(tmp_path: Path) -> tuple[SqlitePersistence, str, str, str]:
    persistence = SqlitePersistence(tmp_path / "observability.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    team_uuid, other_team_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    now = utc_now()
    async with persistence.transaction() as tx:
        for team_uuid_value, name in ((team_uuid, "observability"), (other_team_uuid, "other")):
            await tx.execute(
                "INSERT INTO mkb_teams (team_uuid,name,creation_fingerprint,created_at,updated_at) VALUES (?,?,?,?,?)",
                (team_uuid_value, name, stable_digest({"team": name}), now, now),
            )
    return persistence, team_uuid, other_team_uuid, trace_uuid


async def _event(
    persistence: SqlitePersistence,
    *,
    team_uuid: str,
    trace_uuid: str,
    occurred_at: str,
    summary: str,
    payload: str = "{}",
) -> str:
    event_uuid = uuid7()
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_domain_events "
            "(event_uuid,team_uuid,trace_uuid,event_type,aggregate,severity,actor_kind,summary,payload_digest,payload_json,"
            "schema_version,occurred_at,recorded_at,payload_extra) VALUES (?,?,?,'task.created','task','info','system',?,?"
            ",?,'mkb.domain-event.v1',?,?,'{}')",
            (event_uuid, team_uuid, trace_uuid, summary, stable_digest({"payload": payload}), payload, occurred_at, occurred_at),
        )
    return event_uuid


@pytest.mark.asyncio
async def test_operator_reads_are_team_scoped_cursor_bounded_and_redacted(tmp_path: Path) -> None:
    persistence, team_uuid, other_team_uuid, trace_uuid = await _environment(tmp_path)
    try:
        first = await _event(
            persistence,
            team_uuid=team_uuid,
            trace_uuid=trace_uuid,
            occurred_at="2026-01-01T00:00:00.000000Z",
            summary="Authorization: Bearer should-not-leak at /srv/mkb/file",
            payload='{"token":"should-not-leak","safe":"ok"}',
        )
        second = await _event(
            persistence,
            team_uuid=team_uuid,
            trace_uuid=trace_uuid,
            occurred_at="2026-01-02T00:00:00.000000Z",
            summary="newer event",
        )
        await _event(
            persistence,
            team_uuid=other_team_uuid,
            trace_uuid=trace_uuid,
            occurred_at="2026-01-03T00:00:00.000000Z",
            summary="foreign event",
        )
        reader = ObservabilityReadService(persistence)
        page, cursor = await reader.timeline_by_trace(team_uuid, trace_uuid, limit=1)
        assert [entry["event_uuid"] for entry in page] == [second]
        assert cursor
        next_page, next_cursor = await reader.timeline_by_trace(team_uuid, trace_uuid, limit=1, cursor=cursor)
        assert [entry["event_uuid"] for entry in next_page] == [first]
        assert next_cursor is None
        rendered = str(next_page[0])
        assert "should-not-leak" not in rendered
        assert "[REDACTED]" in rendered
        assert "foreign event" not in rendered
        with pytest.raises(MkbError) as invalid_limit:
            await reader.timeline_by_trace(team_uuid, trace_uuid, limit=201)
        assert invalid_limit.value.code == "OBS_TIMELINE_QUERY_FAIL"
        with pytest.raises(MkbError) as invalid_cursor:
            await reader.timeline_by_trace(team_uuid, trace_uuid, limit=1, cursor="malformed")
        assert invalid_cursor.value.code == "OBS_TIMELINE_QUERY_FAIL"
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_retention_deletes_only_expired_rows_in_bounded_batches(tmp_path: Path) -> None:
    persistence, team_uuid, _other_team_uuid, trace_uuid = await _environment(tmp_path)
    try:
        old = "2020-01-01T00:00:00.000000Z"
        fresh = "2026-01-10T00:00:00.000000Z"
        await _event(persistence, team_uuid=team_uuid, trace_uuid=trace_uuid, occurred_at=old, summary="old-1")
        await _event(persistence, team_uuid=team_uuid, trace_uuid=trace_uuid, occurred_at=old, summary="old-2")
        await _event(persistence, team_uuid=team_uuid, trace_uuid=trace_uuid, occurred_at=fresh, summary="fresh")
        async with persistence.transaction() as tx:
            await tx.execute(
                "INSERT INTO mkb_ops_diagnostic_logs "
                "(log_uuid,team_uuid,trace_uuid,log_level,log_code,log_message,calling_module,payload_digest,occurred_at,payload_extra) "
                "VALUES (?,?,?,'warn','test','old diagnostic','tests',?,?, '{}')",
                (uuid7(), team_uuid, trace_uuid, stable_digest({"diagnostic": "old"}), old),
            )
            await tx.execute(
                "INSERT INTO mkb_security_audit_events "
                "(audit_uuid,team_uuid,actor_kind,action,outcome,denial_code,http_status,summary,payload_digest,occurred_at,payload_extra) "
                "VALUES (?,?, 'anonymous','auth.test','denied','SEC_TOKEN_INVALID',401,'old audit',?,?, '{}')",
                (uuid7(), team_uuid, stable_digest({"audit": "old"}), old),
            )
        metrics = default_metrics()
        retention = ObservabilityRetentionService(
            persistence,
            metrics,
            policy=RetentionPolicy(domain_events_days=90, diagnostic_logs_days=14, security_audit_days=180, batch_size=1),
            clock=lambda: datetime(2026, 1, 20, tzinfo=UTC),
        )
        first = await retention.run_once()
        assert first.deleted == {
            "mkb_domain_events": 1,
            "mkb_ops_diagnostic_logs": 1,
            "mkb_security_audit_events": 1,
        }
        second = await retention.run_once()
        assert second.deleted["mkb_domain_events"] == 1
        assert second.deleted["mkb_ops_diagnostic_logs"] == 0
        assert second.deleted["mkb_security_audit_events"] == 0
        async with persistence.transaction() as tx:
            remaining = await tx.fetchall("SELECT summary FROM mkb_domain_events ORDER BY occurred_at")
        assert remaining == [{"summary": "fresh"}]
        rendered = metrics.render()
        assert 'mkb_retention_delete_rows_total{table="mkb_domain_events"} 2.0' in rendered
    finally:
        await persistence.close()
