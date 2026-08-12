"""Controlled HTTP acquisition for S05 sources.

The callable is intentionally narrow: callers provide a URL only, never
headers, cookies, proxy settings, or an endpoint override.  Every initial and
redirect target is passed through :class:`EgressPolicy` immediately before the
HTTP client opens that hop.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Final
from urllib.parse import urljoin

import httpcore
import httpx

from src.contracts.common.errors import MkbError
from src.runtime.security import EgressPolicy, EgressTarget

_REDIRECT_STATUSES: Final = frozenset({301, 302, 303, 307, 308})


class PinnedNetworkBackend(httpcore.AsyncNetworkBackend):
    """Connect a validated hostname only to its just-resolved public IPs.

    HTTPX would otherwise resolve the hostname again after :class:`EgressPolicy`
    has inspected it.  Replacing that one connection seam preserves the URL's
    hostname (and therefore HTTPS SNI / Host header) while pinning the TCP
    destination to the exact validated address set.
    """

    def __init__(self, target: EgressTarget, *, delegate: httpcore.AsyncNetworkBackend | None = None) -> None:
        from httpcore._backends.anyio import AnyIOBackend

        self._target = target
        self._delegate = delegate or AnyIOBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Any = None,
    ) -> httpcore.AsyncNetworkStream:
        if host.rstrip(".").lower() != self._target.hostname or port != self._target.port:
            raise httpcore.ConnectError("unvalidated HTTP connection target")
        last_error: httpcore.ConnectError | httpcore.ConnectTimeout | None = None
        for address in self._target.addresses:
            try:
                return await self._delegate.connect_tcp(
                    address,
                    port,
                    timeout=timeout,
                    local_address=local_address,
                    socket_options=socket_options,
                )
            except (httpcore.ConnectError, httpcore.ConnectTimeout) as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        raise httpcore.ConnectError("validated HTTP target has no address")

    async def connect_unix_socket(self, *args: Any, **kwargs: Any) -> httpcore.AsyncNetworkStream:
        del args, kwargs
        raise httpcore.ConnectError("Unix socket HTTP acquisition is not permitted")

    async def sleep(self, seconds: float) -> None:
        await self._delegate.sleep(seconds)


def _pinned_transport(target: EgressTarget) -> httpx.AsyncHTTPTransport:
    """Build a short-lived HTTPX transport whose TCP resolver cannot rebind."""

    transport = httpx.AsyncHTTPTransport(trust_env=False, retries=0)
    # HTTPX does not yet expose the httpcore network backend on its public
    # constructor.  This narrow composition seam is isolated here and covered
    # by the backend test below; the public `HttpAcquirer` API remains stable.
    transport._pool._network_backend = PinnedNetworkBackend(target)  # type: ignore[attr-defined]
    return transport


class HttpAcquirer:
    """Fetch bounded response bytes through the S16 egress fence.

    ``transport`` exists for deterministic tests and is not exposed through
    any Task descriptor.  Production construction leaves it unset, disables
    environment proxies, and does not follow redirects automatically.
    """

    def __init__(
        self,
        policy: EgressPolicy,
        *,
        timeout_seconds: float = 15.0,
        max_response_bytes: int = 8 * 1024 * 1024,
        allow_http: bool = False,
        transport: httpx.AsyncBaseTransport | None = None,
        on_egress_denied: Callable[[str], None] | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if max_response_bytes < 1:
            raise ValueError("max_response_bytes must be positive")
        self._policy = policy
        self._timeout_seconds = timeout_seconds
        self._max_response_bytes = max_response_bytes
        self._allow_http = allow_http
        self._transport = transport
        self._on_egress_denied = on_egress_denied

    async def __call__(self, url: str) -> bytes:
        """Return a response body or a safe, typed acquisition/security error."""

        current_url = url
        timeout = httpx.Timeout(self._timeout_seconds)
        for redirect_count in range(self._policy.max_redirects + 1):
            try:
                if redirect_count == 0:
                    target = self._policy.check_url(current_url, allow_http=self._allow_http)
                else:
                    target = self._policy.validate_redirect(current_url, allow_http=self._allow_http)
            except MkbError:
                if self._on_egress_denied is not None:
                    self._on_egress_denied("policy")
                raise
            # Test transports intentionally remain injectable.  The production
            # path creates one short-lived pinned transport per redirect hop.
            transport = self._transport or _pinned_transport(target)
            async with httpx.AsyncClient(
                follow_redirects=False,
                timeout=timeout,
                transport=transport,
                trust_env=False,
                headers={"Accept": "text/plain, text/html, application/json, application/pdf;q=0.8"},
            ) as client:
                try:
                    async with client.stream("GET", current_url) as response:
                        if response.status_code in _REDIRECT_STATUSES:
                            location = response.headers.get("location")
                            if location is None or not location.strip() or redirect_count >= self._policy.max_redirects:
                                self._record_denied("redirect")
                                raise MkbError("SEC_EGRESS_REDIRECT_DENIED", "Redirect target is not permitted", 422)
                            current_url = urljoin(current_url, location)
                            continue
                        if response.status_code < 200 or response.status_code >= 300:
                            raise MkbError(
                                "ACQUISITION_HTTP_STATUS",
                                "HTTP source returned an unsuccessful status",
                                502,
                            )
                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > self._max_response_bytes:
                                raise MkbError(
                                    "ACQUISITION_RESPONSE_TOO_LARGE",
                                    "HTTP source response exceeds the configured size limit",
                                    413,
                                )
                        return bytes(body)
                except MkbError:
                    raise
                except httpx.HTTPError as exc:
                    raise MkbError("ACQUISITION_HTTP_UNAVAILABLE", "HTTP acquisition is unavailable", 503) from exc
        # The loop either returns a body or raises when the redirect budget is
        # exhausted; retaining a typed fallback keeps this defensive branch
        # non-echoing if the control flow changes in the future.
        self._record_denied("redirect")
        raise MkbError("SEC_EGRESS_REDIRECT_DENIED", "Redirect target is not permitted", 422)

    def _record_denied(self, reason: str) -> None:
        if self._on_egress_denied is not None:
            self._on_egress_denied(reason)
