"""FastAPI dependencies that enforce S16 admission ordering."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from src.contracts.common.errors import MkbError
from src.runtime.security import (
    AuditSampleDisposition,
    DenialAuditSampler,
    hash_remote_address,
    is_internal_ip,
    request_ip,
)


def _sampler_for(request: Request) -> DenialAuditSampler:
    """Obtain one app-scoped sampler without turning it into business state."""

    container = request.app.state.container
    configured = getattr(container, "denial_audit_sampler", None)
    if isinstance(configured, DenialAuditSampler):
        return configured
    sampler = getattr(request.app.state, "_mkb_denial_audit_sampler", None)
    if not isinstance(sampler, DenialAuditSampler):
        window_seconds = max(1, int(getattr(container.settings, "rate_limit_window_seconds", 60)))
        sampler = DenialAuditSampler(window_seconds=window_seconds)
        request.app.state._mkb_denial_audit_sampler = sampler
    return sampler


def _sample_limit(request: Request, category: str) -> int:
    settings = request.app.state.container.settings
    field = {
        "invalid_token": "audit_invalid_token_sample_per_ip_per_min",
        "rate_limited": "audit_rate_limited_sample_per_ip_per_min",
    }[category]
    # These conservative S16 defaults remain valid before a deployment exposes
    # the optional ops knobs on Settings.
    return max(1, int(getattr(settings, field, 10)))


async def _audit_denial(
    request: Request,
    code: str,
    status: int,
    summary: str,
    *,
    category: str,
    actor_fingerprint: str | None = None,
    fail_closed: bool = True,
    action: str | None = None,
) -> None:
    """Persist a bounded admission-denial witness with S16 failure semantics.

    Invalid/missing authentication is fail-closed if its audit cannot be
    recorded.  A rate-limited request is already denied, so its sampled audit
    is best-effort to avoid turning a database outage into a request-amplifier.
    """

    container = request.app.state.container
    remote_ip = request_ip(request)
    disposition, sample_key = _sampler_for(request).decide(
        category=category,
        source_identity=hash_remote_address(remote_ip),
        limit=_sample_limit(request, category),
    )
    if disposition is AuditSampleDisposition.DROP:
        return
    sampled = disposition is AuditSampleDisposition.SUMMARY
    if action is None:
        action = {
            "invalid_token": "auth.token_invalid_sampled" if sampled else "auth.token_invalid",
            "rate_limited": "auth.rate_limited_sampled",
        }[category]
    payload: dict[str, object] = {}
    if sampled:
        payload = {"aggregation": "sampled", "sample_window": "per_ip_per_min"}
    try:
        async with container.persistence.transaction() as tx:
            await container.security_audit.write_denied(
                tx,
                action=action,
                denial_code=code,
                summary=summary,
                http_status=status,
                actor_fingerprint=actor_fingerprint,
                request_id=request.headers.get("x-request-id"),
                remote_ip=remote_ip,
                payload=payload,
            )
    except Exception as exc:
        container.metrics.increment("mkb_sec_audit_write_fail_total")
        try:
            _sampler_for(request).undo(
                category=category,
                source_identity=hash_remote_address(remote_ip),
                disposition=disposition,
                effective_key=sample_key,
            )
        except Exception:
            pass
        if fail_closed:
            raise MkbError("SEC_AUDIT_WRITE_FAIL", "Security audit persistence failed", 503) from exc


async def require_business_token(request: Request) -> str:
    """Authenticate before handlers can read a team, task, or any other resource."""

    container = request.app.state.container
    ip_decision = container.rate_limiter.check_ip(request_ip(request))
    container.metrics.set("mkb_sec_rate_limiter_degraded", float(container.rate_limiter.degraded))
    if not ip_decision.allowed:
        container.metrics.increment("mkb_sec_rate_limited_total", dim="ip")
        await _audit_denial(
            request,
            "SEC_RATE_LIMITED",
            429,
            "IP rate limit exceeded",
            category="rate_limited",
            fail_closed=False,
        )
        raise MkbError("SEC_RATE_LIMITED", "Request rate limit exceeded", 429)
    try:
        fingerprint = container.tokens.authenticate(
            request.headers.get("authorization"), request.headers.get("x-mkb-internal-token")
        )
    except MkbError as exc:
        result = "missing" if exc.code == "SEC_TOKEN_MISSING" else "invalid"
        container.metrics.increment("mkb_sec_auth_total", result=result)
        await _audit_denial(
            request,
            exc.code,
            exc.status_code,
            "Internal token denied",
            category="invalid_token",
        )
        raise
    token_decision = container.rate_limiter.check_token(fingerprint)
    if not token_decision.allowed:
        container.metrics.increment("mkb_sec_rate_limited_total", dim="token")
        await _audit_denial(
            request,
            "SEC_RATE_LIMITED",
            429,
            "Token rate limit exceeded",
            category="rate_limited",
            actor_fingerprint=fingerprint,
            fail_closed=False,
        )
        raise MkbError("SEC_RATE_LIMITED", "Request rate limit exceeded", 429)
    container.metrics.increment("mkb_sec_auth_total", result="ok")
    container.metrics.set("mkb_sec_rate_limiter_degraded", float(container.rate_limiter.degraded))
    return fingerprint


async def require_operator_token(request: Request) -> str:
    """Apply the stricter S16 operator/repair network boundary after auth."""

    fingerprint = await require_business_token(request)
    if not is_internal_ip(request_ip(request)):
        await _audit_denial(
            request,
            "SEC_INTERNAL_NETWORK_DENIED",
            403,
            "Operator endpoint requires an internal network peer",
            category="invalid_token",
            actor_fingerprint=fingerprint,
            action="team.access",
        )
        raise MkbError("SEC_INTERNAL_NETWORK_DENIED", "Operator endpoint is not available from this network", 403)
    return fingerprint


async def require_metrics_access(request: Request) -> None:
    """Enforce S16's non-public metrics posture without changing scrape shape.

    The default is an internal-network scrape without a bearer token.  A
    deployment can require the same internal token by setting the explicitly
    named ``metrics_require_token`` knob; callers still never receive metrics
    from a public peer in either mode.
    """

    if not is_internal_ip(request_ip(request)):
        await _audit_denial(
            request,
            "SEC_INTERNAL_NETWORK_DENIED",
            403,
            "Metrics endpoint requires an internal network peer",
            category="invalid_token",
            action="team.access",
        )
        raise MkbError("SEC_INTERNAL_NETWORK_DENIED", "Metrics endpoint is not available from this network", 403)
    if bool(getattr(request.app.state.container.settings, "metrics_require_token", False)):
        await require_business_token(request)


async def require_ready(request: Request) -> None:
    readiness = await request.app.state.container.health.ready()
    if readiness["status"] != "ready":
        raise MkbError("not-ready", "Service is not ready to accept new business", 503)


BusinessToken = Annotated[str, Depends(require_business_token)]
OperatorToken = Annotated[str, Depends(require_operator_token)]
MetricsAccess = Annotated[None, Depends(require_metrics_access)]
Ready = Annotated[None, Depends(require_ready)]
