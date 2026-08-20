"""S16 internal-token admission, egress fencing, and redaction primitives.

This module deliberately owns no business state.  It provides the small,
in-process control-plane state required before public routes may reach a Team,
Task, or retrieval record.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import re
import socket
import threading
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlsplit

from fastapi import Request

from src.contracts.common.errors import MkbError, UnauthorizedError


def token_fingerprint(token: str) -> str:
    """Return the fixed-width, non-reversible token identifier used at rest."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_remote_address(remote_ip: str | None) -> str | None:
    """Hash an address before it crosses an observability persistence boundary."""

    if remote_ip is None:
        return None
    normalized = remote_ip.strip()
    return token_fingerprint(normalized) if normalized else None


_BEARER = re.compile(r"^bearer[ \t]+([^\s]+)$", re.IGNORECASE)


def extract_presented_token(authorization: str | None, compatibility_token: str | None) -> str | None:
    """Extract the one credential that is allowed to reach token verification.

    An ``Authorization`` header always wins over the compatibility header,
    including when the Authorization syntax is malformed.  This avoids a
    malformed higher-precedence header unexpectedly falling back to another
    credential supplied by an intermediary.
    """

    if authorization is not None:
        match = _BEARER.fullmatch(authorization.strip())
        return None if match is None else match.group(1)
    if compatibility_token is not None:
        candidate = compatibility_token.strip()
        return candidate or None
    return None


class ActiveTokenSet:
    """At most two active token *fingerprints*, compared in constant time."""

    def __init__(self, tokens: Iterable[str] = ()) -> None:
        self._fingerprints: tuple[str, ...] = ()
        self.replace(tokens)

    @staticmethod
    def _normalize(tokens: Iterable[str]) -> tuple[str, ...]:
        fingerprints = tuple(
            dict.fromkeys(token_fingerprint(token.strip()) for token in tokens if token and token.strip())
        )
        if len(fingerprints) > 2:
            raise ValueError("at most current and previous internal tokens are allowed")
        return fingerprints

    @property
    def loaded(self) -> bool:
        return bool(self._fingerprints)

    @property
    def active_fingerprints(self) -> tuple[str, ...]:
        """Expose only fingerprints for readiness/operations diagnostics."""

        return self._fingerprints

    def replace(self, tokens: Iterable[str]) -> None:
        """Atomically replace the active set without retaining plaintext tokens."""

        self._fingerprints = self._normalize(tokens)

    def authenticate(self, authorization: str | None, compatibility_token: str | None) -> str:
        token = extract_presented_token(authorization, compatibility_token)
        if token is None:
            if authorization is None and compatibility_token is None:
                raise UnauthorizedError("SEC_TOKEN_MISSING", "Internal token is required")
            raise UnauthorizedError("SEC_TOKEN_INVALID")
        fingerprint = token_fingerprint(token)
        # Do not return early: every active fingerprint follows the same
        # comparison path.  The candidate and supplied values are fixed-width
        # SHA-256 hex strings before comparison.
        matched = False
        for candidate in self._fingerprints:
            matched = hmac.compare_digest(fingerprint, candidate) or matched
        if not matched:
            raise UnauthorizedError("SEC_TOKEN_INVALID")
        return fingerprint


_SECRET_SLOT = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")


class SecretResolver:
    """A logical-slot resolver that never falls back to arbitrary env names.

    The resolver is deliberately small: an application composition root may
    populate it from an environment/file/Vault adapter, but contracts and
    durable records only carry the logical slot.  Missing, malformed, or empty
    slots always fail closed with one non-echoing S16 code.
    """

    def __init__(self, values: Mapping[str, str] | None = None) -> None:
        self._values: dict[str, str] = {}
        self.replace(values or {})

    def __repr__(self) -> str:
        return f"SecretResolver(slots={tuple(sorted(self._values))!r})"

    @property
    def slots(self) -> tuple[str, ...]:
        """Return logical names only, never resolved values."""

        return tuple(sorted(self._values))

    def replace(self, values: Mapping[str, str]) -> None:
        normalized: dict[str, str] = {}
        for slot, value in values.items():
            if not isinstance(slot, str) or _SECRET_SLOT.fullmatch(slot) is None:
                raise ValueError("secret slot names must be uppercase logical identifiers")
            if not isinstance(value, str) or not value:
                raise ValueError("secret values must be non-empty strings")
            normalized[slot] = value
        # Atomic mapping replacement keeps readers from observing a partial
        # rotation map.  Values remain in process memory only.
        self._values = normalized

    def resolve(self, slot: str) -> str:
        if not isinstance(slot, str) or _SECRET_SLOT.fullmatch(slot) is None:
            raise MkbError("SEC_SECRET_UNRESOLVED", "Secret slot cannot be resolved", 503)
        value = self._values.get(slot)
        if not value:
            raise MkbError("SEC_SECRET_UNRESOLVED", "Secret slot cannot be resolved", 503)
        return value


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    dimension: str | None = None


class FixedWindowRateLimiter:
    """Bounded in-process token/IP limiter with an explicit degraded signal."""

    def __init__(
        self,
        *,
        ip_limit: int = 120,
        token_limit: int = 600,
        window_seconds: int = 60,
        enabled: bool = True,
        max_buckets: int = 4_096,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if ip_limit < 1 or token_limit < 1 or window_seconds < 1 or max_buckets < 1:
            raise ValueError("rate-limit values must be positive")
        self.ip_limit = ip_limit
        self.token_limit = token_limit
        self.window_seconds = window_seconds
        self.enabled = enabled
        self.max_buckets = max_buckets
        self._clock = clock
        self._buckets: dict[tuple[str, str, int], int] = {}
        self._lock = threading.Lock()
        self.degraded = False

    def _allow(self, dimension: str, identity: str, limit: int, now: float) -> bool:
        if not self.enabled:
            return True
        bucket = int(now // self.window_seconds)
        key = (dimension, identity, bucket)
        with self._lock:
            # Keep only the active and immediately preceding windows.  This is
            # a control-plane cache, not an unbounded request history.
            cutoff = bucket - 1
            self._buckets = {item: count for item, count in self._buckets.items() if item[2] >= cutoff}
            if key not in self._buckets and len(self._buckets) >= self.max_buckets:
                overflow_key = (dimension, "__overflow__", bucket)
                self._buckets[overflow_key] = self._buckets.get(overflow_key, 0) + 1
                return False
            self._buckets[key] = self._buckets.get(key, 0) + 1
            return self._buckets[key] <= limit

    def _check(self, dimension: str, identity: str, limit: int) -> RateLimitDecision:
        try:
            allowed = self._allow(dimension, identity, limit, self._clock())
            self.degraded = False
            return RateLimitDecision(allowed, None if allowed else dimension)
        except Exception:
            self.degraded = True
            return RateLimitDecision(False, dimension)

    def check_ip(self, remote_ip: str | None) -> RateLimitDecision:
        return self._check("ip", hash_remote_address(remote_ip) or "unknown", self.ip_limit)

    def check_token(self, fingerprint: str) -> RateLimitDecision:
        return self._check("token", fingerprint, self.token_limit)


class AuditSampleDisposition(StrEnum):
    DETAIL = "detail"
    SUMMARY = "summary"
    DROP = "drop"


class DenialAuditSampler:
    """Bound denied-event detail volume while keeping one aggregate witness.

    Each source identity/category/window receives at most ``limit`` detailed
    records and exactly one summary record.  Later events are represented by
    the mandatory full metric counter and do not create unbounded audit rows.
    """

    def __init__(
        self,
        *,
        window_seconds: int = 60,
        max_buckets: int = 4_096,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if window_seconds < 1 or max_buckets < 1:
            raise ValueError("sampling window and bucket capacity must be positive")
        self.window_seconds = window_seconds
        self.max_buckets = max_buckets
        self._clock = clock
        self._buckets: dict[tuple[str, str, int], tuple[int, bool]] = {}
        self._lock = threading.Lock()

    def decide(self, *, category: str, source_identity: str | None, limit: int) -> AuditSampleDisposition:
        if limit < 1:
            raise ValueError("audit sample limit must be positive")
        bucket = int(self._clock() // self.window_seconds)
        key = (category, source_identity or "unknown", bucket)
        with self._lock:
            cutoff = bucket - 1
            self._buckets = {item: state for item, state in self._buckets.items() if item[2] >= cutoff}
            if key not in self._buckets and len(self._buckets) >= self.max_buckets:
                # Preserve one bounded aggregate witness for source-cardinality
                # floods, without retaining attacker-controlled identities.
                key = (category, "overflow", bucket)
                if key not in self._buckets:
                    # Reserve bounded capacity for the aggregate.  Losing a
                    # per-source sample under a flood is preferable to letting
                    # attacker-controlled source identities consume memory.
                    self._buckets.pop(next(iter(self._buckets)))
            detail_count, summary_written = self._buckets.get(key, (0, False))
            if detail_count < limit:
                self._buckets[key] = (detail_count + 1, summary_written)
                result = AuditSampleDisposition.DETAIL
            elif not summary_written:
                self._buckets[key] = (detail_count, True)
                result = AuditSampleDisposition.SUMMARY
            else:
                result = AuditSampleDisposition.DROP
            return result

    def undo(self, *, category: str, source_identity: str | None, disposition: AuditSampleDisposition) -> None:
        if disposition is AuditSampleDisposition.DROP:
            return
        bucket = int(self._clock() // self.window_seconds)
        key = (category, source_identity or "unknown", bucket)
        with self._lock:
            detail_count, summary_written = self._buckets.get(key, (0, False))
            if disposition is AuditSampleDisposition.DETAIL and detail_count > 0:
                self._buckets[key] = (detail_count - 1, summary_written)
            elif disposition is AuditSampleDisposition.SUMMARY:
                self._buckets[key] = (detail_count, False)


@dataclass(frozen=True, slots=True)
class EgressTarget:
    """A DNS-resolved target validated immediately before a client connects."""

    url: str
    hostname: str
    port: int
    addresses: tuple[str, ...]


Resolver = Callable[[str, int], Iterable[str]]


def _system_resolver(hostname: str, port: int) -> tuple[str, ...]:
    addresses = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    return tuple(dict.fromkeys(str(address[4][0]) for address in addresses))


class EgressPolicy:
    """Fail-closed URL/IP policy used by controlled acquisition clients.

    ``check_url`` returns the validated addresses so a caller can pin its
    connection to that result rather than resolving the hostname again after
    policy validation.  Redirect targets must be passed through the same
    method one hop at a time.
    """

    _metadata_hosts = frozenset({"metadata", "metadata.google.internal", "metadata.aws.internal"})
    _carrier_grade_nat = ipaddress.ip_network("100.64.0.0/10")

    def __init__(
        self,
        *,
        resolver: Resolver = _system_resolver,
        allow_literal_ip: bool = False,
        allow_private_default: bool = False,
        max_redirects: int = 3,
    ) -> None:
        if max_redirects < 0 or max_redirects > 3:
            raise ValueError("max_redirects must be between 0 and 3")
        self._resolver = resolver
        self.allow_literal_ip = allow_literal_ip
        self.allow_private_default = allow_private_default
        self.max_redirects = max_redirects

    @staticmethod
    def _literal_ip(hostname: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
        try:
            return ipaddress.ip_address(hostname)
        except ValueError:
            return None

    @staticmethod
    def _restricted(address: ipaddress.IPv4Address | ipaddress.IPv6Address, *, allow_private: bool) -> bool:
        # These categories never become valid HTTP-source destinations, even
        # for the tightly scoped internal_only profile.
        mapped = getattr(address, "ipv4_mapped", None)
        if mapped is not None:
            return EgressPolicy._restricted(mapped, allow_private=allow_private)
        if address.is_loopback or address.is_link_local or address.is_multicast or address.is_unspecified:
            return True
        if address.is_reserved:
            return True
        if isinstance(address, ipaddress.IPv4Address) and address in EgressPolicy._carrier_grade_nat:
            return True
        return address.is_private and not allow_private

    def check_url(
        self,
        url: str,
        *,
        allow_http: bool = False,
        allow_private: bool | None = None,
        allow_literal_ip: bool | None = None,
    ) -> EgressTarget:
        try:
            parsed = urlsplit(url)
            hostname = parsed.hostname
            port = parsed.port
        except ValueError as exc:
            raise MkbError("SEC_EGRESS_DENIED", "URL is not permitted", 422) from exc
        allowed_schemes = {"https", "http"} if allow_http else {"https"}
        if parsed.scheme.lower() not in allowed_schemes:
            raise MkbError("SEC_EGRESS_DENIED", "URL scheme is not permitted", 422)
        if not hostname or parsed.username is not None or parsed.password is not None:
            raise MkbError("SEC_EGRESS_DENIED", "URL host is not permitted", 422)
        try:
            hostname = hostname.rstrip(".").encode("idna").decode("ascii").lower()
        except UnicodeError as exc:
            raise MkbError("SEC_EGRESS_DENIED", "URL host is not permitted", 422) from exc
        if hostname in self._metadata_hosts:
            raise MkbError("SEC_EGRESS_DENIED", "URL host is not permitted", 422)
        effective_private = self.allow_private_default if allow_private is None else allow_private
        effective_literal = self.allow_literal_ip if allow_literal_ip is None else allow_literal_ip
        literal = self._literal_ip(hostname)
        if literal is not None and not effective_literal:
            raise MkbError("SEC_EGRESS_DENIED", "Literal IP destinations are not permitted", 422)
        effective_port = port or (443 if parsed.scheme.lower() == "https" else 80)
        try:
            raw_addresses = (str(literal),) if literal is not None else tuple(self._resolver(hostname, effective_port))
        except (OSError, ValueError) as exc:
            raise MkbError("SEC_EGRESS_DENIED", "URL host cannot be resolved", 422) from exc
        if not raw_addresses:
            raise MkbError("SEC_EGRESS_DENIED", "URL host cannot be resolved", 422)
        validated: list[str] = []
        for raw_address in raw_addresses:
            try:
                address = ipaddress.ip_address(raw_address)
            except ValueError as exc:
                raise MkbError("SEC_EGRESS_DENIED", "URL host cannot be resolved", 422) from exc
            if self._restricted(address, allow_private=effective_private):
                raise MkbError("SEC_EGRESS_DENIED", "URL resolves to a restricted address", 422)
            validated.append(str(address))
        return EgressTarget(url=url, hostname=hostname, port=effective_port, addresses=tuple(dict.fromkeys(validated)))

    def validate_url(
        self,
        url: str,
        *,
        allow_http: bool = False,
        allow_private: bool | None = None,
        allow_literal_ip: bool | None = None,
    ) -> str:
        """Compatibility facade for callers that only need an allow/deny result."""

        return self.check_url(
            url,
            allow_http=allow_http,
            allow_private=allow_private,
            allow_literal_ip=allow_literal_ip,
        ).url

    def validate_redirect(self, url: str, **kwargs: bool | None) -> EgressTarget:
        """Validate one redirect hop with the redirect-specific public code."""

        try:
            return self.check_url(url, **kwargs)
        except MkbError as exc:
            raise MkbError("SEC_EGRESS_REDIRECT_DENIED", "Redirect target is not permitted", 422) from exc


_REDACT_KEY = re.compile(
    r"(authorization|x[-_]?mkb[-_]?internal[-_]?token|token|password|passphrase|secret|api[_-]?key|"
    r"access[_-]?key|private[_-]?key|credential|cookie|signature|signed|connection|dsn)",
    re.IGNORECASE,
)
_SECRET_HEADER = re.compile(
    r"\b(?:authorization|x[-_]?mkb[-_]?internal[-_]?token|api[_-]?key|access[_-]?key|token|password)"
    r"\s*[:=]\s*(?:bearer\s+)?[^\s,;]+",
    re.IGNORECASE,
)
_BEARER_VALUE = re.compile(r"\bbearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_CONNECTION_URL = re.compile(
    r"\b(?:postgres(?:ql)?|mysql|redis|mongodb(?:\+srv)?|amqp|file)://[^\s'\"<>]+", re.IGNORECASE
)
_PRESIGNED_URL = re.compile(
    r"https?://[^\s'\"<>]*[?&](?:x-amz-[^=]+|signature|token|access[_-]?key|credential)=[^\s'\"<>]*",
    re.IGNORECASE,
)
_ABS_PATH = re.compile(r"(?<![:A-Za-z0-9_])/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+")


def _redact_text(value: str) -> str:
    result = _CONNECTION_URL.sub("[REDACTED_CONNECTION]", value)
    result = _PRESIGNED_URL.sub("[REDACTED_URL]", result)
    result = _SECRET_HEADER.sub("[REDACTED]", result)
    result = _BEARER_VALUE.sub("Bearer [REDACTED]", result)
    return _ABS_PATH.sub("[REDACTED_PATH]", result)


def redact(value: object) -> object:
    """Recursively remove values prohibited from public/audit/metric surfaces."""

    if isinstance(value, dict):
        return {str(key): "[REDACTED]" if _REDACT_KEY.search(str(key)) else redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    if isinstance(value, str):
        return _redact_text(value)
    return value


def request_ip(request: Request) -> str | None:
    """Use the ASGI peer; X-Forwarded-For is trusted only for configured proxies."""

    client = request.client
    peer = None if client is None or not client.host or len(client.host) > 255 else client.host
    forwarded = request.headers.get("x-forwarded-for")
    cidrs: list[str] = []
    try:
        settings = request.app.state.container.settings
        raw = getattr(settings, "trusted_proxy_cidrs", "") or ""
        cidrs = [item.strip() for item in str(raw).split(",") if item.strip()]
    except Exception:
        cidrs = []
    if forwarded:
        presented = forwarded.split(",")[0].strip()
        if presented and len(presented) <= 255:
            if cidrs:
                if peer and _ip_in_cidrs(peer, cidrs):
                    return presented
            elif peer and _is_private_peer(peer):
                # Empty CIDR: a private ASGI peer is treated as an untrusted
                # reverse proxy, so the forwarded client is the identity.
                return presented
    return peer


def _is_private_peer(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return address.is_private or address.is_loopback or address.is_link_local


def _ip_in_cidrs(value: str, cidrs: list[str]) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    for cidr in cidrs:
        try:
            if address in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


def is_internal_ip(remote_ip: str | None) -> bool:
    """Fail closed for operator/repair routes when the peer is not private."""

    if remote_ip is None:
        return False
    try:
        address = ipaddress.ip_address(remote_ip)
    except ValueError:
        return False
    mapped = getattr(address, "ipv4_mapped", None)
    if mapped is not None:
        return is_internal_ip(str(mapped))
    return address.is_private or address.is_loopback or address.is_link_local


_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def safe_request_id(value: str | None) -> str | None:
    """Do not persist an unbounded caller-controlled request-id in audit rows."""

    return value if value is not None and _REQUEST_ID.fullmatch(value) else None
