from __future__ import annotations

import re


def extract_text(payload: str) -> str:
    # Lightweight HTML/text extraction for local test environments.
    text = re.sub(r"<script.*?>.*?</script>", " ", payload, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style.*?>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

