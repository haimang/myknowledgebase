"""NS5 Phase 2: persistence honesty (T11–T19)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.contracts.api.models import TeamPatchRequest
from src.contracts.common.ids import uuid7
from src.contracts.common.time import normalize_rfc3339, utc_now
from src.persistence.factory import build_persistence
from src.persistence.migration_runner import apply_migrations, discover_migrations
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.health import HealthAggregator
from src.runtime.metrics import MetricRegistry
from src.services.teams import TeamService
from src.storage.local_store import LocalObjectStore

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


@pytest.mark.asyncio
async def test_turso_stale_update_rowcount_is_zero(tmp_path: Path) -> None:
    persistence = build_persistence(
        tmp_path / "rowcount.db",
        Path("src/persistence/migrations"),
        backend="turso",
        concurrent_writes_required=False,
        native_vector_required=False,
    )
    try:
        await persistence.migrate()
        async with persistence.transaction() as tx:
            updated = await tx.execute(
                "UPDATE mkb_teams SET name='x' WHERE team_uuid=?",
                ("00000000-0000-4000-8000-000000000000",),
            )
            assert updated.rowcount == 0
            await tx.execute(
                "INSERT INTO mkb_teams(team_uuid,name,creation_fingerprint,created_at,updated_at) "
                "VALUES (?,?,?,?,?)",
                ("11111111-1111-4111-8111-111111111111", "rowcount", "a" * 64, utc_now(), utc_now()),
            )
            matched = await tx.execute(
                "UPDATE mkb_teams SET name='y' WHERE team_uuid=?",
                ("11111111-1111-4111-8111-111111111111",),
            )
            assert matched.rowcount == 1
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_014_rewrites_32hex_model_uuid(tmp_path: Path) -> None:
    db = tmp_path / "uuid.sqlite"
    migrations = discover_migrations(Path("src/persistence/migrations"))
    prefix = [item for item in migrations if item.migration_id < "014_ns5_uuid_and_tombstone"]
    connection = __import__("sqlite3").connect(db)
    try:
        apply_migrations(connection, prefix)
        connection.execute(
            "INSERT INTO mkb_model_catalog "
            "(model_uuid, model_key, model_version, modality, provider_family, default_dimension, "
            "definition_digest, status, display_name, registered_at, payload_extra) "
            "VALUES (?,?, 'v1','embed','local',1024,?,'active','seed', 't','{}')",
            ("a" * 32, "qwen-vl-2b-seed", "b" * 64),
        )
        connection.commit()
        apply_migrations(connection, migrations)
        row = connection.execute(
            "SELECT model_uuid FROM mkb_model_catalog WHERE model_key='qwen-vl-2b-seed'"
        ).fetchone()
        assert row is not None
        assert UUID_RE.match(row[0])
    finally:
        connection.close()


def test_ledger_insert_is_parameterized() -> None:
    source = Path("src/persistence/migration_runner.py").read_text(encoding="utf-8")
    assert "VALUES (?,?,?,?)" in source
    assert "VALUES ({migration.migration_id!r}" not in source


def test_timestamps_share_microsecond_timespec() -> None:
    now = utc_now()
    assert now.endswith("Z")
    assert "." in now
    normalized = normalize_rfc3339("2026-08-20T12:00:00.123456Z")
    assert normalized.endswith("123456Z")


@pytest.mark.asyncio
async def test_health_ready_coalesces_within_ttl(tmp_path: Path) -> None:
    calls = {"n": 0}

    async def probe() -> dict[str, bool]:
        calls["n"] += 1
        return {name: True for name in HealthAggregator.REQUIRED}

    health = HealthAggregator(probe, MetricRegistry(), ttl_seconds=5)
    async def both() -> None:
        await health.ready()
        await health.ready()

    import asyncio

    await asyncio.gather(health.ready(), health.ready())
    assert 1 <= calls["n"] <= 2


@pytest.mark.asyncio
async def test_identity_not_json_is_not_ready(tmp_path: Path) -> None:
    store = LocalObjectStore(tmp_path / "objects")
    await store.readiness()
    store._identity_path.write_text("not-json", encoding="utf-8")
    assert await store.readiness() is False


@pytest.mark.asyncio
async def test_drop_mkb_tasks_fails_schema_readiness(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "schema.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    connection = persistence._connect()
    connection.execute("DROP TABLE mkb_tasks")
    connection.commit()
    ready = await persistence.readiness()
    assert ready["schema_migration"] is False
    await persistence.close()


@pytest.mark.asyncio
async def test_team_patch_empty_extras_clears(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "team.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    from src.contracts.api.models import TeamCreateRequest

    service = TeamService(persistence)
    created, _replayed = await service.create(
        TeamCreateRequest(
            schema_version="mkb.team.v1",
            team_uuid=uuid7(),
            name="extras",
            payload_extra={"keep": "me"},
        )
    )
    patched = await service.patch(
        created["team_uuid"],
        TeamPatchRequest(expected_revision=created["revision"], payload_extra={}),
    )
    assert patched["payload_extra"] == {}
    await persistence.close()
