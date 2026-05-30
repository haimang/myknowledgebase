from __future__ import annotations

import hashlib


def embed_text(text: str, dims: int = 1536) -> list[float]:
    seed = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    while len(values) < dims:
        seed = hashlib.sha256(seed).digest()
        for i in range(0, len(seed), 2):
            num = int.from_bytes(seed[i : i + 2], byteorder="big", signed=False)
            values.append((num / 65535.0) * 2.0 - 1.0)
            if len(values) >= dims:
                break
    return values

