"""Focused S16 admission, audit, redaction, and controlled-egress tests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpcore
import httpx
import pytest
from starlette.applications import Starlette
from starlette.requests import Request

from api.dependencies import require_business_token, require_metrics_access, require_operator_token
from src.contracts.common.errors import MkbError
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.http_acquisition import HttpAcquirer, PinnedNetworkBackend
from src.runtime.metrics import MetricRegistry, default_metrics
from src.runtime.security import (
    ActiveTokenSet,
    AuditSampleDisposition,
    DenialAuditSampler,
    EgressPolicy,
    EgressTarget,
    FixedWindowRateLimiter,
    SecretResolver,
    hash_remote_address,
    redact,
)
from src.services.events import SecurityAuditWriter


@dataclass(slots=True)
class _SecurityContainer:
    persistence: SqlitePersistence
    security_audit: Any
    metrics: MetricRegistry
    tokens: ActiveTokenSet
    rate_limiter: FixedWindowRateLimiter
    settings: SimpleNamespace


def _request(
    app: Starlette, headers: dict[str, str] | None = None, client: tuple[str, int] = ("198.51.100.2", 1234)
) -> Request:
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "path": "/v1/teams/example/tasks",
            "raw_path": b"/v1/teams/example/tasks",
            "query_string": b"",
            "headers": [(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()],
            "client": client,
            "server": ("mkb.test", 443),
            "app": app,
        }
    )


@pytest.fixture
async def security_environment(tmp_path: Path) -> tuple[SqlitePersistence, _SecurityContainer, Starlette]:
    persistence = SqlitePersistence(tmp_path / "security.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    container = _SecurityContainer(
        persistence=persistence,
        security_audit=SecurityAuditWriter(),
        metrics=default_metrics(),
        tokens=ActiveTokenSet(("current-token", "previous-token")),
        rate_limiter=FixedWindowRateLimiter(ip_limit=100, token_limit=100),
        settings=SimpleNamespace(
            rate_limit_window_seconds=60,
            audit_invalid_token_sample_per_ip_per_min=2,
            audit_rate_limited_sample_per_ip_per_min=2,
        ),
    )
    app = Starlette()
    app.state.container = container
    try:
        yield persistence, container, app
    finally:
        await persistence.close()


def test_active_token_set_is_fingerprint_only_dual_active_and_bearer_precedence() -> None:
    tokens = ActiveTokenSet(("current", "previous"))

    assert tokens.authenticate("Bearer current", None) in tokens.active_fingerprints
    assert tokens.authenticate(None, "previous") in tokens.active_fingerprints
    assert "current" not in repr(tokens.active_fingerprints)
    assert "previous" not in repr(tokens.active_fingerprints)

    with pytest.raises(MkbError) as malformed_bearer:
        tokens.authenticate("NotBearer malformed", "current")
    assert malformed_bearer.value.code == "SEC_TOKEN_INVALID"

    with pytest.raises(MkbError) as missing:
        tokens.authenticate(None, None)
    assert missing.value.code == "SEC_TOKEN_MISSING"

    tokens.replace(("next",))
    with pytest.raises(MkbError) as revoked:
        tokens.authenticate("Bearer current", None)
    assert revoked.value.code == "SEC_TOKEN_INVALID"
    assert tokens.authenticate("Bearer next", None) in tokens.active_fingerprints


def test_secret_resolver_accepts_only_registered_logical_slots_and_never_echoes_values() -> None:
    resolver = SecretResolver({"MODEL_API_KEY": "very-secret-value"})

    assert resolver.resolve("MODEL_API_KEY") == "very-secret-value"
    assert "very-secret-value" not in repr(resolver)
    assert resolver.slots == ("MODEL_API_KEY",)
    with pytest.raises(MkbError) as missing:
        resolver.resolve("UNKNOWN_SLOT")
    assert missing.value.code == "SEC_SECRET_UNRESOLVED"
    with pytest.raises(MkbError) as malformed:
        resolver.resolve("../../etc/passwd")
    assert malformed.value.code == "SEC_SECRET_UNRESOLVED"


def test_fixed_window_limiter_is_dual_dimension_bounded_and_degrades_open_only_for_counting() -> None:
    def fixed_clock() -> float:
        return 100.0

    limiter = FixedWindowRateLimiter(ip_limit=1, token_limit=1, clock=fixed_clock)

    assert limiter.check_ip("198.51.100.2").allowed
    assert not limiter.check_ip("198.51.100.2").allowed
    assert limiter.check_token("f" * 64).allowed
    assert not limiter.check_token("f" * 64).allowed

    def broken_clock() -> float:
        raise RuntimeError("clock unavailable")

    degraded = FixedWindowRateLimiter(clock=broken_clock)
    assert not degraded.check_ip("198.51.100.2").allowed
    assert degraded.degraded

    bounded = FixedWindowRateLimiter(ip_limit=1, token_limit=1, max_buckets=1, clock=fixed_clock)
    assert bounded.check_ip("198.51.100.2").allowed
    assert not bounded.check_ip("198.51.100.3").allowed
    assert not bounded.check_ip("198.51.100.2").allowed


def test_denial_sampler_caps_detail_rows_and_keeps_one_summary_per_window() -> None:
    now = [10.0]
    sampler = DenialAuditSampler(clock=lambda: now[0])

    decisions = [sampler.decide(category="invalid_token", source_identity="ip", limit=2) for _ in range(5)]
    assert decisions == [
        AuditSampleDisposition.DETAIL,
        AuditSampleDisposition.DETAIL,
        AuditSampleDisposition.SUMMARY,
        AuditSampleDisposition.DROP,
        AuditSampleDisposition.DROP,
    ]
    now[0] += 60
    assert sampler.decide(category="invalid_token", source_identity="ip", limit=2) is AuditSampleDisposition.DETAIL

    bounded = DenialAuditSampler(max_buckets=1, clock=lambda: 100.0)
    assert bounded.decide(category="invalid_token", source_identity="first", limit=1) is AuditSampleDisposition.DETAIL
    # New attacker-controlled source IDs collapse into one bounded aggregate
    # witness instead of expanding an in-memory audit cache indefinitely.
    assert bounded.decide(category="invalid_token", source_identity="second", limit=1) is AuditSampleDisposition.DETAIL
    assert bounded.decide(category="invalid_token", source_identity="third", limit=1) is AuditSampleDisposition.SUMMARY


@pytest.mark.asyncio
async def test_invalid_admission_is_audited_without_raw_ip_or_token_and_is_sampled(
    security_environment: tuple[SqlitePersistence, _SecurityContainer, Starlette],
) -> None:
    persistence, _container, app = security_environment
    request = _request(app, {"authorization": "Bearer definitely-not-active", "x-request-id": "safe-request-1"})

    for _ in range(5):
        with pytest.raises(MkbError) as denied:
            await require_business_token(request)
        assert denied.value.code == "SEC_TOKEN_INVALID"

    async with persistence.transaction() as tx:
        rows = await tx.fetchall(
            "SELECT action,actor_kind,remote_addr_hash,payload_json FROM mkb_security_audit_events ORDER BY occurred_at,audit_uuid"
        )
        business_rows = await tx.fetchone("SELECT count(*) AS count FROM mkb_tasks")
    assert [row["action"] for row in rows] == [
        "auth.token_invalid",
        "auth.token_invalid",
        "auth.token_invalid_sampled",
    ]
    assert all(row["actor_kind"] == "anonymous" for row in rows)
    assert all(row["remote_addr_hash"] == hash_remote_address("198.51.100.2") for row in rows)
    assert all("198.51.100.2" not in row["payload_json"] for row in rows)
    assert all("definitely-not-active" not in row["payload_json"] for row in rows)
    assert business_rows == {"count": 0}
    assert 'mkb_sec_auth_total{result="invalid"} 5.0' in _container.metrics.render()


@pytest.mark.asyncio
async def test_failed_invalid_token_audit_fails_closed_but_rate_limit_audit_is_best_effort(
    security_environment: tuple[SqlitePersistence, _SecurityContainer, Starlette],
) -> None:
    _persistence, container, app = security_environment

    class BrokenAudit:
        async def write_denied(self, *args: object, **kwargs: object) -> str:
            del args, kwargs
            raise RuntimeError("audit store unavailable")

    container.security_audit = BrokenAudit()
    invalid = _request(app, {"authorization": "Bearer unknown"})
    with pytest.raises(MkbError) as invalid_result:
        await require_business_token(invalid)
    assert invalid_result.value.code == "SEC_AUDIT_WRITE_FAIL"

    container.rate_limiter = FixedWindowRateLimiter(ip_limit=1, token_limit=100)
    valid = _request(app, {"authorization": "Bearer current-token"})
    assert await require_business_token(valid)
    with pytest.raises(MkbError) as rate_result:
        await require_business_token(valid)
    assert rate_result.value.code == "SEC_RATE_LIMITED"
    assert "mkb_sec_audit_write_fail_total 2.0" in container.metrics.render()


@pytest.mark.asyncio
async def test_operator_dependency_requires_valid_token_then_internal_peer(
    security_environment: tuple[SqlitePersistence, _SecurityContainer, Starlette],
) -> None:
    _persistence, _container, app = security_environment
    external = _request(app, {"authorization": "Bearer current-token"}, client=("8.8.8.8", 1234))
    with pytest.raises(MkbError) as denied:
        await require_operator_token(external)
    assert denied.value.code == "SEC_INTERNAL_NETWORK_DENIED"

    internal = _request(app, {"authorization": "Bearer previous-token"}, client=("127.0.0.1", 1234))
    assert await require_operator_token(internal)


@pytest.mark.asyncio
async def test_metrics_dependency_requires_internal_peer_and_optionally_a_token(
    security_environment: tuple[SqlitePersistence, _SecurityContainer, Starlette],
) -> None:
    _persistence, container, app = security_environment
    external = _request(app, client=("8.8.8.8", 1234))
    with pytest.raises(MkbError) as external_denied:
        await require_metrics_access(external)
    assert external_denied.value.code == "SEC_INTERNAL_NETWORK_DENIED"

    internal = _request(app, client=("127.0.0.1", 1234))
    assert await require_metrics_access(internal) is None

    container.settings.metrics_require_token = True
    with pytest.raises(MkbError) as missing:
        await require_metrics_access(internal)
    assert missing.value.code == "SEC_TOKEN_MISSING"
    authenticated = _request(app, {"authorization": "Bearer current-token"}, client=("127.0.0.1", 1234))
    assert await require_metrics_access(authenticated) is None


@pytest.mark.asyncio
async def test_security_audit_writer_redacts_payload_summary_and_hashes_remote_address(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "audit.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    try:
        async with persistence.transaction() as tx:
            await SecurityAuditWriter().write_denied(
                tx,
                action="auth.token_invalid",
                denial_code="SEC_TOKEN_INVALID",
                summary="Authorization: Bearer super-secret at /srv/mkb/private.txt",
                http_status=401,
                remote_ip="203.0.113.99",
                request_id="good-request-id",
                payload={
                    "Authorization": "Bearer super-secret",
                    "nested": {"connection_string": "postgres://user:pw@db/private"},
                    "url": "https://example.test/download?X-Amz-Signature=secret",
                },
            )
        async with persistence.transaction() as tx:
            row = await tx.fetchone(
                "SELECT request_id,remote_addr_hash,summary,payload_json FROM mkb_security_audit_events"
            )
        assert row is not None
        serialized = json.dumps(row)
        assert "super-secret" not in serialized
        assert "/srv/mkb/private.txt" not in serialized
        assert "203.0.113.99" not in serialized
        assert row["request_id"] == "good-request-id"
        assert row["remote_addr_hash"] == hash_remote_address("203.0.113.99")
    finally:
        await persistence.close()


def test_redaction_handles_header_values_presigned_urls_connection_strings_and_paths() -> None:
    protected = redact(
        {
            "x-mkb-internal-token": "not-visible",
            "message": "Authorization: Bearer no-leak /var/lib/mkb/state.db",
            "url": "https://example.test/a?signature=no-leak",
            "dsn": "postgres://username:password@host/database",
        }
    )
    encoded = json.dumps(protected)
    assert "not-visible" not in encoded
    assert "no-leak" not in encoded
    assert "/var/lib/mkb/state.db" not in encoded
    assert "password" not in encoded


def test_public_error_envelope_never_echoes_secret_path_driver_detail_or_unsafe_request_id() -> None:
    error = MkbError(
        "unexpected-driver-error",
        "database at postgres://user:password@db/private failed at /srv/mkb/db.sqlite",
        503,
        {
            "Authorization": "Bearer no-leak",
            "driver": RuntimeError("SQLITE_BUSY /srv/mkb/db.sqlite"),
            "safe": {"path": "/srv/mkb/also-private"},
        },
    )

    envelope = error.as_dict("/unsafe/request-id")
    rendered = json.dumps(envelope)
    assert "password" not in rendered
    assert "no-leak" not in rendered
    assert "/srv/mkb" not in rendered
    assert "request_id" not in envelope


def _resolver(hostname: str, port: int) -> list[str]:
    del port
    return {
        "public.example": ["8.8.8.8"],
        "private.example": ["10.0.0.5"],
    }.get(hostname, ["8.8.8.8"])


def test_egress_policy_rejects_http_metadata_literal_private_and_dns_private_destinations() -> None:
    policy = EgressPolicy(resolver=_resolver)

    for url in ("http://169.254.169.254/latest", "https://169.254.169.254/latest", "https://private.example/"):
        with pytest.raises(MkbError) as denied:
            policy.check_url(url)
        assert denied.value.code == "SEC_EGRESS_DENIED"

    strict_literal = EgressPolicy(resolver=_resolver, allow_literal_ip=True, allow_private_default=True)
    with pytest.raises(MkbError) as link_local:
        strict_literal.check_url("https://169.254.169.254/latest")
    assert link_local.value.code == "SEC_EGRESS_DENIED"

    target = policy.check_url("https://public.example/path")
    assert target.addresses == ("8.8.8.8",)
    assert target.port == 443


@pytest.mark.asyncio
async def test_http_acquirer_rechecks_redirects_and_never_sends_a_private_redirect() -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return httpx.Response(302, headers={"location": "https://private.example/metadata"}, request=request)

    acquirer = HttpAcquirer(EgressPolicy(resolver=_resolver), transport=httpx.MockTransport(handler))
    with pytest.raises(MkbError) as denied:
        await acquirer("https://public.example/start")
    assert denied.value.code == "SEC_EGRESS_REDIRECT_DENIED"
    assert requests == ["https://public.example/start"]


@pytest.mark.asyncio
async def test_http_acquirer_follows_only_valid_bounded_redirects_and_enforces_body_budget() -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "/final"}, request=request)
        return httpx.Response(200, content=b"safe response", request=request)

    acquirer = HttpAcquirer(EgressPolicy(resolver=_resolver), transport=httpx.MockTransport(handler))
    assert await acquirer("https://public.example/start") == b"safe response"
    assert requests == ["/start", "/final"]

    oversized = HttpAcquirer(
        EgressPolicy(resolver=_resolver),
        max_response_bytes=3,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"oversized", request=request)),
    )
    with pytest.raises(MkbError) as too_large:
        await oversized("https://public.example/large")
    assert too_large.value.code == "ACQUISITION_RESPONSE_TOO_LARGE"


@pytest.mark.asyncio
async def test_pinned_backend_connects_only_to_the_egress_validated_ip_set() -> None:
    class FailingDelegate(httpcore.AsyncNetworkBackend):
        def __init__(self) -> None:
            self.calls: list[tuple[str, int]] = []

        async def connect_tcp(self, host: str, port: int, **kwargs: object) -> httpcore.AsyncNetworkStream:
            del kwargs
            self.calls.append((host, port))
            raise httpcore.ConnectError("fixture refused connection")

        async def connect_unix_socket(self, *args: object, **kwargs: object) -> httpcore.AsyncNetworkStream:
            del args, kwargs
            raise httpcore.ConnectError("fixture refused unix socket")

        async def sleep(self, seconds: float) -> None:
            del seconds

    target = EgressTarget(
        url="https://public.example/resource",
        hostname="public.example",
        port=443,
        addresses=("8.8.8.8", "1.1.1.1"),
    )
    delegate = FailingDelegate()
    backend = PinnedNetworkBackend(target, delegate=delegate)

    with pytest.raises(httpcore.ConnectError):
        await backend.connect_tcp("public.example", 443)
    assert delegate.calls == [("8.8.8.8", 443), ("1.1.1.1", 443)]

    with pytest.raises(httpcore.ConnectError):
        await backend.connect_tcp("rebound.example", 443)
    assert delegate.calls == [("8.8.8.8", 443), ("1.1.1.1", 443)]
