"""NS4-T16 / T17: optional persist and swallowed audit TX are gone."""

from __future__ import annotations

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_no_getattr_persist_failed_generation_invocation() -> None:
    text = (REPOSITORY_ROOT / "src/runtime/intake/generation_construct.py").read_text(encoding="utf-8")
    assert 'getattr(self, "_persist_failed_generation_invocation"' not in text


def test_persist_failed_does_not_swallow_exceptions() -> None:
    text = (REPOSITORY_ROOT / "src/runtime/intake/generation_live.py").read_text(encoding="utf-8")
    assert "except Exception:" not in text.split("async def _persist_failed_generation_invocation")[1].split(
        "async def _record_generation"
    )[0]
    assert "Best-effort failure audit outside" not in text
