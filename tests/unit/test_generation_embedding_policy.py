"""Generation local-off switch must not disable Qwen embedding."""

from __future__ import annotations

from pathlib import Path

from api.app import create_app
from src.runtime.config import Settings


def test_generation_local_switch_keeps_live_embedding_path(tmp_path: Path) -> None:
    settings = Settings(
        internal_token="split-token",
        database_path=tmp_path / "mkb.sqlite3",
        object_root=tmp_path / "objects",
        persistence_backend="sqlite",
        concurrent_writes_required=False,
        native_vector_required=False,
        inference_probe_enabled=False,
        live_inference=True,
        generation_local_enabled=False,
        ns1_cli_mode="stub",
    )

    container = create_app(settings).state.container

    assert container.settings.live_inference is True
    assert container.settings.generation_local_enabled is False
    assert container.workflow_runtime.live_inference is True
    assert container.workflow_runtime.local_generation_enabled is False
    assert container.retrieval._live_inference is True  # noqa: SLF001
    assert container.clean_llm is None
