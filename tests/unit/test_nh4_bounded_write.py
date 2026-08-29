"""NH4 Phase 1: bounded streaming CAS writes remain atomic and replayable."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import uuid7
from src.contracts.storage.models import PromoteRequest
from src.storage.local_store import LocalObjectStore


async def _chunks(*values: bytes):
    for value in values:
        yield value


def _request(team_uuid: str, *, expected: str | None = None) -> PromoteRequest:
    return PromoteRequest(
        team_uuid=team_uuid,
        purpose="process_io",
        media_type="application/octet-stream",
        expected_sha256=expected,
    )


def _staging(root: Path) -> list[Path]:
    path = root / "staging"
    return [] if not path.exists() else list(path.iterdir())


@pytest.mark.asyncio
async def test_stream_hash_size_atomic_promote_and_replay(tmp_path: Path) -> None:
    team_uuid = uuid7()
    body = b"bounded-" + b"stream-" * 257
    expected = hashlib.sha256(body).hexdigest()
    store = LocalObjectStore(tmp_path / "objects", max_object_bytes=len(body) + 1)

    first = await store.promote_stream(
        _chunks(body[:17], body[17:1024], body[1024:]),
        _request(team_uuid, expected=expected),
    )
    replay = await store.promote_stream(
        _chunks(body[:3], body[3:]),
        _request(team_uuid, expected=expected),
    )

    assert first == replay
    assert first.sha256 == expected
    assert first.size_bytes == len(body)
    assert await store.read_verified(team_uuid, first.handle) == body
    assert _staging(store.root) == []
    assert len(list((store.root / "objects" / team_uuid / "sha256").rglob(expected))) == 1


@pytest.mark.asyncio
async def test_stream_cap_413_cleans_staging_and_never_promotes(tmp_path: Path) -> None:
    team_uuid = uuid7()
    store = LocalObjectStore(tmp_path / "objects", max_object_bytes=8)
    with pytest.raises(MkbError) as raised:
        await store.promote_stream(_chunks(b"1234", b"5678", b"9"), _request(team_uuid))
    assert raised.value.code == "OBJECT_BUDGET_SIZE"
    assert raised.value.status_code == 413
    assert _staging(store.root) == []
    assert list((store.root / "objects").rglob("*")) == []


@pytest.mark.asyncio
async def test_expected_digest_mismatch_422_cleans_staging_and_cas(tmp_path: Path) -> None:
    team_uuid = uuid7()
    store = LocalObjectStore(tmp_path / "objects", max_object_bytes=1024)
    with pytest.raises(MkbError) as raised:
        await store.promote_stream(_chunks(b"actual bytes"), _request(team_uuid, expected="0" * 64))
    assert raised.value.code == "OBJECT_INTEGRITY_DIGEST"
    assert raised.value.status_code == 422
    assert _staging(store.root) == []
    assert list((store.root / "objects").rglob("*")) == []


@pytest.mark.asyncio
async def test_interrupted_stream_leaves_only_reapable_staging_then_cleans_it(tmp_path: Path) -> None:
    team_uuid = uuid7()
    store = LocalObjectStore(tmp_path / "objects", max_object_bytes=1024)

    async def interrupted():
        yield b"partial"
        raise RuntimeError("transport interrupted")

    with pytest.raises(RuntimeError, match="transport interrupted"):
        await store.promote_stream(interrupted(), _request(team_uuid))
    assert _staging(store.root) == []
    assert list((store.root / "objects").rglob("*")) == []


@pytest.mark.asyncio
async def test_bytes_promote_uses_the_same_streaming_fences(tmp_path: Path) -> None:
    team_uuid = uuid7()
    store = LocalObjectStore(tmp_path / "objects", max_object_bytes=4)
    stat = await store.promote(b"four", _request(team_uuid))
    assert stat.size_bytes == 4
    with pytest.raises(MkbError) as raised:
        await store.promote(b"five!", _request(team_uuid))
    assert raised.value.code == "OBJECT_BUDGET_SIZE"
    assert _staging(store.root) == []
