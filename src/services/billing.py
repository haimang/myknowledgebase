"""Billing quota port for non-interactive and inference channels."""

from __future__ import annotations

from typing import Protocol


class BillingPort(Protocol):
    """Port for checking tenant/channel billing quotas."""

    def has_quota(self, channel: str) -> bool:
        """Return whether quota is available for the given channel."""
        ...


class DefaultBillingService:
    """Default stub implementation that always permits execution."""

    def has_quota(self, channel: str) -> bool:
        del channel
        return True
