"""Offline deterministic embedding profile shared by intake and retrieval.

The deployed profile obtains vectors through S11.  CI and a deliberately
offline single-node profile still need a real semantic-golden path rather than
ranking opaque unit identifiers.  This pure helper is the explicit local
profile: it has no transport, persistence, or storage dependency, and intake
and retrieval use the same versioned transform.
"""

from __future__ import annotations

import hashlib
import math
import re

_TOKEN = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


def deterministic_embedding(value: str, *, dimension: int) -> list[float]:
    """Return a stable normalized token-hash vector for offline profiles."""

    if dimension < 1:
        raise ValueError("embedding dimension must be positive")
    vector = [0.0] * dimension
    for token in _TOKEN.findall(value.casefold()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        first = int.from_bytes(digest[:4], "big") % dimension
        second = int.from_bytes(digest[4:8], "big") % dimension
        vector[first] += 1.0
        vector[second] -= 0.25
    norm = math.sqrt(sum(component * component for component in vector))
    if norm == 0.0:
        vector[0] = 1.0
        return vector
    return [component / norm for component in vector]


__all__ = ["deterministic_embedding"]
