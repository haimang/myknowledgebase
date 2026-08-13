"""Explicit local/CI waiver profile for mock tests that still need /ready=200."""

from __future__ import annotations

from pathlib import Path

from src.runtime.config import Settings


def local_mock_settings(
    *,
    database_path: Path,
    object_root: Path,
    persistence_backend: str = "turso",
    **kwargs: object,
) -> Settings:
    payload = {
        "database_path": database_path,
        "object_root": object_root,
        "persistence_backend": persistence_backend,
        "concurrent_writes_required": False,
        "native_vector_required": False,
        "inference_probe_enabled": False,
        "live_inference": False,
    }
    payload.update(kwargs)
    return Settings(**payload)
