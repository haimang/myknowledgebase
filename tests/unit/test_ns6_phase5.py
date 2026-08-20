"""NS6-T28–T32: empty CIDR XFF, PATCH secrets, chunked body, overflow undo, mapped IPs."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from starlette.requests import Request

from src.contracts.api.models import TeamPatchRequest
from src.runtime.security import (
    AuditSampleDisposition,
    DenialAuditSampler,
    _is_private_peer,
    is_internal_ip,
    request_ip,
)


def _xff_request(*, peer: str, forwarded: str, cidrs: str = "") -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/metrics",
        "raw_path": b"/metrics",
        "query_string": b"",
        "headers": [(b"x-forwarded-for", forwarded.encode("ascii"))],
        "client": (peer, 1234),
        "server": ("testserver", 80),
        "app": SimpleNamespace(
            state=SimpleNamespace(container=SimpleNamespace(settings=SimpleNamespace(trusted_proxy_cidrs=cidrs)))
        ),
    }

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


def test_empty_cidr_ignores_private_xff() -> None:
    request = _xff_request(peer="10.0.0.1", forwarded="127.0.0.1")
    assert request_ip(request) == "10.0.0.1"


def test_team_patch_rejects_secret_extras() -> None:
    with pytest.raises(ValidationError):
        TeamPatchRequest(expected_revision=0, payload_extra={"apiKey": "sk-live"})


def test_overflow_undo_returns_quota_to_overflow_bucket() -> None:
    sampler = DenialAuditSampler(max_buckets=1, clock=lambda: 10.0)
    first, first_key = sampler.decide(category="invalid_token", source_identity="ip-a", limit=1)
    assert first is AuditSampleDisposition.DETAIL
    second, second_key = sampler.decide(category="invalid_token", source_identity="ip-b", limit=1)
    assert second is AuditSampleDisposition.DETAIL
    assert second_key[1] == "overflow"
    sampler.undo(category="invalid_token", source_identity="ip-b", disposition=second, effective_key=second_key)
    third, _ = sampler.decide(category="invalid_token", source_identity="ip-c", limit=1)
    assert third is AuditSampleDisposition.DETAIL
    del first_key


def test_mapped_loopback_is_private_like_internal_ip() -> None:
    assert _is_private_peer("::ffff:127.0.0.1") is is_internal_ip("::ffff:127.0.0.1")
    assert _is_private_peer("::ffff:127.0.0.1") is True


@pytest.mark.asyncio
async def test_chunked_body_without_content_length_is_capped(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from api.app import create_app
    from src.runtime.config import Settings

    app = create_app(
        Settings(
            internal_token="ns6-body",
            database_path=tmp_path / "mkb.sqlite3",
            object_root=tmp_path / "objects",
            persistence_backend="sqlite",
            concurrent_writes_required=False,
            native_vector_required=False,
            max_request_bytes=1024,
        )
    )
    with TestClient(app) as client:
        def chunks() -> object:
            yield b"x" * 1025

        response = client.post(
            "/v1/teams",
            headers={"Authorization": "Bearer ns6-body"},
            content=chunks(),
        )
        assert response.status_code == 413
