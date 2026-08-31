"""NHX1-T25: signal↔metric↔alert↔runbook and error aliases are closed."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.governance import ERROR_DEFINITIONS, resolve_error_definition
from src.runtime.config import Settings
from src.runtime.metrics import default_metrics
from src.runtime.signals import DEFAULT_SIGNAL_REGISTRY


def test_signal_catalog_has_metric_alert_runbook_and_emitter() -> None:
    metrics = default_metrics()
    assert DEFAULT_SIGNAL_REGISTRY.validate_metrics(metrics) == ()
    assert len(DEFAULT_SIGNAL_REGISTRY.definitions) == 10
    assert all(Path(definition.runbook_ref).is_file() for definition in DEFAULT_SIGNAL_REGISTRY.definitions)
    for definition in DEFAULT_SIGNAL_REGISTRY.definitions:
        DEFAULT_SIGNAL_REGISTRY.emit(metrics, definition.signal_key)
    rendered = metrics.render()
    assert "ALERT_OUTBOX_DEAD" in rendered
    assert "ALERT_SECURITY_DENY_SPIKE" in rendered


def test_error_registry_is_canonical_with_legacy_aliases() -> None:
    assert all(definition.code == definition.code.upper() for definition in ERROR_DEFINITIONS.values())
    assert resolve_error_definition("stale-process-fence").code == "COMMAND_FENCE_CONFLICT"
    assert resolve_error_definition("intake-item-revision-conflict").code == "ITEM_EPOCH_CONFLICT"


def test_signal_projection_and_readiness_alert_are_durable(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            internal_token="nhx1-signal-token",
            database_path=tmp_path / "signals.sqlite3",
            object_root=tmp_path / "objects",
            persistence_backend="turso",
            concurrent_writes_required=False,
            native_vector_required=False,
            rate_limit_ip_per_min=10_000,
            rate_limit_token_per_min=10_000,
        )
    )
    with TestClient(app, raise_server_exceptions=True) as client:
        ready = client.get("/ready")
        assert ready.status_code == 200, ready.text

        async def count() -> int:
            async with app.state.container.persistence.read_snapshot() as tx:
                row = await tx.fetchone("SELECT COUNT(*) AS count FROM mkb_operational_signal_definitions")
            assert row is not None
            return int(row["count"])

        assert client.portal.call(count) == 10
        app.state.container.signal_registry.emit(app.state.container.metrics, "readiness.false")
        assert "ALERT_READINESS_FALSE" in app.state.container.metrics.render()
