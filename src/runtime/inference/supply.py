"""S16 binding-only fence for model transports.

The fence deliberately holds only already-resolved identities and topology
coordinates.  It does not resolve a different binding after a failure, and it
never accepts an endpoint from a request body.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from urllib.parse import urlsplit

from src.contracts.common.errors import MkbError
from src.contracts.inference.models import InferenceBinding


def normalize_model_endpoint(value: str) -> str:
    """Normalize a configured L2 endpoint without exposing it in errors."""

    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("invalid endpoint")
        # Accessing ``port`` catches malformed values such as ``:not-a-port``.
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise ValueError("model endpoint must be a configured http(s) origin") from exc
    authority = parsed.hostname.lower()
    if ":" in authority:
        # `urlsplit().hostname` removes the IPv6 brackets, while a rendered
        # authority must retain them in order not to become ambiguous.
        authority = f"[{authority}]"
    if port is not None:
        authority = f"{authority}:{port}"
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme.lower()}://{authority}{path}"


@runtime_checkable
class TransportIdentity(Protocol):
    """The non-secret identity an adapter exposes to its enclosing facade."""

    adapter_kind: str
    base_url: str
    secret_slot: str | None


@dataclass(frozen=True, slots=True)
class SupplyBinding:
    """One exact L4 binding bound to one configured adapter endpoint."""

    capability_key: str
    adapter_kind: str
    model_key: str
    model_version: str
    binding_digest: str
    base_url: str
    secret_slot: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_url", normalize_model_endpoint(self.base_url))
        if (
            self.secret_slot is not None
            and (not isinstance(self.secret_slot, str) or not self.secret_slot.strip())
        ):
            raise ValueError("secret_slot must be a non-empty logical slot or None")

    @classmethod
    def from_binding(cls, binding: InferenceBinding, *, base_url: str, secret_slot: str | None = None) -> SupplyBinding:
        return cls(
            capability_key=binding.capability_key,
            adapter_kind=binding.adapter_kind,
            model_key=binding.model_key,
            model_version=binding.model_version,
            binding_digest=binding.binding_digest,
            base_url=base_url,
            secret_slot=secret_slot,
        )

    def matches_binding(self, binding: InferenceBinding) -> bool:
        return (
            self.capability_key == binding.capability_key
            and self.adapter_kind == binding.adapter_kind
            and self.model_key == binding.model_key
            and self.model_version == binding.model_version
            and self.binding_digest == binding.binding_digest
        )


class SupplyFence:
    """Fail closed unless a request uses a registered exact transport target."""

    def __init__(self, bindings: tuple[SupplyBinding, ...] | list[SupplyBinding]) -> None:
        if not bindings:
            raise ValueError("SupplyFence requires at least one registered binding")
        keys: set[tuple[str, str, str, str, str]] = set()
        for item in bindings:
            key = (
                item.capability_key,
                item.adapter_kind,
                item.model_key,
                item.model_version,
                item.binding_digest,
            )
            if key in keys:
                raise ValueError("SupplyFence binding identities must be unique")
            keys.add(key)
        self._bindings = tuple(bindings)

    def validate(self, binding: InferenceBinding, adapter: TransportIdentity) -> None:
        """Reject an unregistered model, adapter swap, or endpoint swap.

        Every message is deliberately endpoint-free: a caller learns only that
        a registration fence rejected its request, never the configured URL or
        secret-slot name.
        """

        matches = [entry for entry in self._bindings if entry.matches_binding(binding)]
        if not matches:
            raise MkbError("SEC_SUPPLY_UNBOUND", "Inference binding is not registered for transport", 503)
        if getattr(adapter, "adapter_kind", None) != binding.adapter_kind:
            raise MkbError("SEC_SUPPLY_UNBOUND", "Inference adapter does not match the frozen binding", 503)
        try:
            endpoint = normalize_model_endpoint(adapter.base_url)
        except (AttributeError, TypeError, ValueError) as exc:
            raise MkbError("SEC_MODEL_ENDPOINT_REJECTED", "Inference endpoint is not permitted", 503) from exc
        if not any(entry.base_url == endpoint and entry.secret_slot == getattr(adapter, "secret_slot", None) for entry in matches):
            raise MkbError("SEC_MODEL_ENDPOINT_REJECTED", "Inference endpoint is not permitted", 503)


__all__ = ["SupplyBinding", "SupplyFence", "TransportIdentity", "normalize_model_endpoint"]
