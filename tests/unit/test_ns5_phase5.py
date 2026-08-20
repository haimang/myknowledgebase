"""NS5 Phase 5 security-boundary tests (T48–T55 subset)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.contracts.api.models import TeamCreateRequest
from src.contracts.common.errors import MkbError
from src.contracts.common.models import assert_safe_public_data
from src.persistence.factory import sqlite_backend_permitted
from src.runtime.security import EgressPolicy, FixedWindowRateLimiter, is_internal_ip


def test_camelcase_secret_and_signed_url_rejected() -> None:
    with pytest.raises(ValueError):
        assert_safe_public_data({"apiKey": "sk-live"})
    with pytest.raises(ValueError):
        assert_safe_public_data({"url": "https://s3.example/x?X-Amz-Signature=abc"})
    with pytest.raises(ValidationError):
        TeamCreateRequest(
            schema_version="mkb.team.v1",
            team_uuid="11111111-1111-4111-8111-111111111111",
            name="x",
            payload_extra={"token": "x"},
        )


def test_rate_limiter_overflow_does_not_fail_open() -> None:
    limiter = FixedWindowRateLimiter(ip_limit=1, token_limit=1, max_buckets=2, window_seconds=60)
    assert limiter.check_ip("1.1.1.1").allowed is True
    assert limiter.check_ip("2.2.2.2").allowed is True
    assert limiter.check_ip("3.3.3.3").allowed is False
    assert limiter.check_ip("4.4.4.4").allowed is False


def test_starlette_left_badhost_cve_range() -> None:
    import starlette

    parts = tuple(int(part) for part in starlette.__version__.split(".")[:3])
    assert parts >= (1, 0, 1)


def test_mapped_ipv6_loopback_is_restricted() -> None:
    policy = EgressPolicy(allow_literal_ip=True)
    with pytest.raises(MkbError):
        policy.check_url("http://[::ffff:127.0.0.1]/")
    assert is_internal_ip("::ffff:127.0.0.1") is True


def test_sqlite_requires_pytest_module(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "forged::test")
    monkeypatch.delenv("MKB_ALLOW_SQLITE", raising=False)
    assert sqlite_backend_permitted() is True  # real pytest process still has pytest loaded
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    assert sqlite_backend_permitted() is False
