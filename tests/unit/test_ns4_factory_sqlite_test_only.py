"""NS4-T08: sqlite factory is pytest-only."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.persistence.factory import build_persistence, sqlite_backend_permitted


def test_sqlite_backend_permitted_follows_pytest_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    assert sqlite_backend_permitted() is False
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/unit/test_ns4_factory_sqlite_test_only.py::x")
    assert sqlite_backend_permitted() is True


def test_factory_rejects_sqlite_when_not_permitted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.persistence.factory.sqlite_backend_permitted", lambda: False)
    with pytest.raises(ValueError, match="test-only"):
        build_persistence(
            tmp_path / "x.db",
            Path("src/persistence/migrations"),
            backend="sqlite",
        )


def test_factory_still_builds_sqlite_under_pytest(tmp_path: Path) -> None:
    engine = build_persistence(
        tmp_path / "x.db",
        Path("src/persistence/migrations"),
        backend="sqlite",
        concurrent_writes_required=False,
        native_vector_required=False,
    )
    assert engine.database_path == tmp_path / "x.db"
