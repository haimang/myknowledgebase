"""FastAPI dependencies that enforce S16 admission ordering."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from src.contracts.common.errors import MkbError
from src.runtime.security import request_ip


async def _audit_denial(request: Request, code: str, status: int, summary: str) -> None:
    """Security denial audit is fail-closed: failure returns a 5xx, not success."""

    container = request.app.state.container
    try:
        async with container.persistence.transaction() as tx:
            await container.security_audit.write_denied(
                tx,
                action="auth.token_invalid" if code.startswith("SEC_TOKEN") else "auth.rate_limited_sampled",
                denial_code=code,
                summary=summary,
                http_status=status,
                payload={"remote_addr_hash": request_ip(request)},
            )
    except Exception as exc:
        container.metrics.increment("mkb_sec_audit_write_fail_total")
        raise MkbError("SEC_AUDIT_WRITE_FAIL", "Security audit persistence failed", 503) from exc


async def require_business_token(request: Request) -> str:
    """Authenticate before handlers can read a team, task, or any other resource."""

    container = request.app.state.container
    ip_decision = container.rate_limiter.check_ip(request_ip(request))
    if not ip_decision.allowed:
        container.metrics.increment("mkb_sec_rate_limited_total", dim="ip")
        await _audit_denial(request, "SEC_RATE_LIMITED", 429, "IP rate limit exceeded")
        raise MkbError("SEC_RATE_LIMITED", "Request rate limit exceeded", 429)
    try:
        fingerprint = container.tokens.authenticate(
            request.headers.get("authorization"), request.headers.get("x-mkb-internal-token")
        )
    except MkbError as exc:
        result = "missing" if exc.code == "SEC_TOKEN_MISSING" else "invalid"
        container.metrics.increment("mkb_sec_auth_total", result=result)
        await _audit_denial(request, exc.code, exc.status_code, "Internal token denied")
        raise
    token_decision = container.rate_limiter.check_token(fingerprint)
    if not token_decision.allowed:
        container.metrics.increment("mkb_sec_rate_limited_total", dim="token")
        await _audit_denial(request, "SEC_RATE_LIMITED", 429, "Token rate limit exceeded")
        raise MkbError("SEC_RATE_LIMITED", "Request rate limit exceeded", 429)
    container.metrics.increment("mkb_sec_auth_total", result="ok")
    container.metrics.set("mkb_sec_rate_limiter_degraded", float(container.rate_limiter.degraded))
    return fingerprint


async def require_ready(request: Request) -> None:
    readiness = await request.app.state.container.health.ready()
    if readiness["status"] != "ready":
        raise MkbError("not-ready", "Service is not ready to accept new business", 503)


BusinessToken = Annotated[str, Depends(require_business_token)]
Ready = Annotated[None, Depends(require_ready)]
