"""NS4-T06 / T07: CW required consumes the probe; no silent waiver."""

from __future__ import annotations

from src.persistence.engine import apply_capability_gates, probe_concurrent_writes


def test_required_cw_follows_probe_false() -> None:
    gates = apply_capability_gates(
        concurrent_writes=False,
        native_vector=True,
        concurrent_writes_required=True,
        native_vector_required=True,
    )
    assert gates["concurrent_writes"] is False
    assert gates["concurrent_writes_probe"] is False


def test_required_cw_follows_probe_true() -> None:
    gates = apply_capability_gates(
        concurrent_writes=True,
        native_vector=True,
        concurrent_writes_required=True,
        native_vector_required=True,
    )
    assert gates["concurrent_writes"] is True


def test_probe_concurrent_writes_is_the_constitution_probe() -> None:
    assert "BEGIN CONCURRENT" in (probe_concurrent_writes.__doc__ or "")
