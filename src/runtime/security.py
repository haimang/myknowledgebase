"""S16 internal-token admission, rate limiting, redaction, and egress fence."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import re
import socket
import time
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import urlsplit

from fastapi import Request

from src.contracts.common.errors import MkbError, UnauthorizedError


def token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class ActiveTokenSet:
    """At most two deployment-provided tokens, compared in constant time."""

    def __init__(self, tokens: Iterable[str] = ()) -> None:
        normalized = tuple(token.strip() for token in tokens if token and token.strip())
        if len(normalized) > 2:
            raise ValueError("at most current and previous internal tokens are allowed")
        self._tokens = normalized

    @property
    def loaded(self) -> bool:
        return bool(self._tokens)

    def authenticate(self, authorization: str | None, compatibility_token: str | None) -> str:
        token: str | None = None
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        elif compatibility_token:
            token = compatibility_token.strip()
        if not token:
            raise UnauthorizedError("SEC_TOKEN_MISSING", "Internal token is required")
        # Do not return early: the comparison path is stable across active tokens.
        matched = False
        for candidate in self._tokens:
            matched = hmac.compare_digest(token, candidate) or matched
        if not matched:
            raise UnauthorizedError("SEC_TOKEN_INVALID")
        return token_fingerprint(token)


@dataclass(slots=True)
class RateLimitDecision:
    allowed: bool
    dimension: str | None = None


class FixedWindowRateLimiter:
    """In-process admission limiter; failure of the limiter intentionally fails open."""

    def __init__(self, *, ip_limit: int = 120, token_limit: int = 600, window_seconds: int = 60) -> None:
        self.ip_limit = ip_limit
        self.token_limit = token_limit
        self.window_seconds = window_seconds
        self._buckets: dict[tuple[str, str, int], int] = defaultdict(int)
        self.degraded = False

    def _allow(self, dimension: str, identity: str, limit: int, now: float) -> bool:
        bucket = int(now // self.window_seconds)
        key = (dimension, identity, bucket)
        self._buckets[key] += 1
        return self._buckets[key] <= limit

    def check_ip(self, remote_ip: str | None) -> RateLimitDecision:
        try:
            allowed = self._allow("ip", remote_ip or "unknown", self.ip_limit, time.monotonic())
            return RateLimitDecision(allowed, None if allowed else "ip")
        except Exception:
            self.degraded = True
            return RateLimitDecision(True)

    def check_token(self, fingerprint: str) -> RateLimitDecision:
        try:
            allowed = self._allow("token", fingerprint, self.token_limit, time.monotonic())
            return RateLimitDecision(allowed, None if allowed else "token")
        except Exception:
            self.degraded = True
            return RateLimitDecision(True)


_REDACT_KEY = re.compile(r"(authorization|token|password|secret|api[_-]?key|private[_-]?key)", re.I)
_ABS_PATH = re.compile(r"(?:^|\s)(?:/[\w.-]+)+")


def redact(value: object) -> object:
    if isinstance(value, dict):
        return {key: "[REDACTED]" if _REDACT_KEY.search(key) else redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return _ABS_PATH.sub("[REDACTED_PATH]", value)
    return value


class EgressPolicy:
    """Deny private/link-local/loopback destinations even if a caller allowlists them."""

    _hard_denied = (
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("169.254.0.0/16"),
        ipaddress.ip_network("::1/128"),
        ipaddress.ip_network("fe80::/10"),
    )

    def validate_url(self, url: str, *, allow_http: bool = False, allow_private: bool = False) -> str:
        parsed = urlsplit(url)
        if parsed.scheme not in ({"https", "http"} if allow_http else {"https"}):
            raise MkbError("SEC_EGRESS_DENIED", "URL scheme is not permitted", 422)
        if not parsed.hostname or parsed.username or parsed.password:
            raise MkbError("SEC_EGRESS_DENIED", "URL host is not permitted", 422)
        try:
            addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise MkbError("SEC_EGRESS_DENIED", "URL host cannot be resolved", 422) from exc
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not allow_private and any(ip in network for network in self._hard_denied):
                raise MkbError("SEC_EGRESS_DENIED", "URL resolves to a restricted address", 422)
        return url


def request_ip(request: Request) -> str | None:
    return request.client.host if request.client else None
