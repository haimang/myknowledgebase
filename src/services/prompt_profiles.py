"""Closed intake domain/flavor/granularity defaults for catalog identities.

``documentation`` is a generic writing-system domain.  Flavor selects which
document template family the optional markdown hop should preserve.

    qna         owner decision register (singular one-shot or progressive rounds)
    eval        analysis snapshot family (state-analysis and sibling eval forms)
    plan        executable action-plan sequence
    closure     phase close, evidence, deferrals, handoff
    code-review review artifact, findings ledger, or implementer response

Granularity is a closed level, not a free list.  Each level maps to one json
prompt whose catalog ``granularity_set`` is inclusive of coarser layers:

    g0 → {0}
    g1 → {0,1}     (default json template)
    g2 → {0,1,2}

Compression channel is independent of prompt identity:

    non-interactive   Claude ``-p``
    local-inference   Local vLLM generate (Qwen / Lightning)

Omit is not a Claude default. Snapshot/admit derive the channel from
Task.priority (normal/low first local; urgent/high lock NI).
"""

from __future__ import annotations

from typing import Literal

DOCUMENTATION_DOMAIN = "documentation"
DOCUMENTATION_FLAVORS = frozenset({"qna", "eval", "closure", "plan", "code-review"})
GRANULARITY_LEVELS: dict[str, tuple[int, ...]] = {
    "g0": (0,),
    "g1": (0, 1),
    "g2": (0, 1, 2),
}

COMPRESSION_CHANNELS = frozenset({"non-interactive", "local-inference"})
INTERNAL_RESERVED_CHANNELS = frozenset({"non-interactive", "local-inference", "cloud-inference"})
DEFAULT_COMPRESSION_CHANNEL = "non-interactive"
CompressionChannel = Literal["non-interactive", "local-inference"]

IntakeDomain = Literal["documentation"]
IntakeFlavor = Literal["qna", "eval", "closure", "plan", "code-review"]
IntakeGranularity = Literal["g0", "g1", "g2"]

_DOCUMENTATION_DEFAULTS: dict[str, str | None] = {
    "clean": "promptA.documentation.default",
    "markdown": None,
    "json": "promptB.documentation.g1",
    "summarizer": "promptC.documentation.default",
}


def json_prompt_id_for(*, domain: str | None, granularity: str | None) -> str | None:
    """Return the json catalog id implied by domain + granularity level."""

    if granularity is not None and granularity not in GRANULARITY_LEVELS:
        raise ValueError(f"unsupported granularity: {granularity}")
    if domain == DOCUMENTATION_DOMAIN:
        return f"promptB.documentation.{granularity or 'g1'}"
    if granularity is not None:
        return f"promptB.json.{granularity}"
    return None


def default_prompt_ids(
    *,
    domain: str | None,
    flavor: str | None,
    granularity: str | None = None,
) -> dict[str, str | None]:
    """Return role defaults for a domain/flavor/granularity triple.

    Unknown combinations fail closed.  Flavor without domain is invalid.
    Documentation without flavor still selects A/json/C and skips markdown.
    Granularity without domain still selects a generic json.g0/g1/g2 row.
    """

    if flavor is not None and domain is None:
        raise ValueError("flavor requires domain")
    if granularity is not None and granularity not in GRANULARITY_LEVELS:
        raise ValueError(f"unsupported granularity: {granularity}")
    if domain is not None and domain != DOCUMENTATION_DOMAIN:
        raise ValueError(f"unsupported intake domain: {domain}")

    selected: dict[str, str | None] = {}
    if domain == DOCUMENTATION_DOMAIN:
        selected = dict(_DOCUMENTATION_DEFAULTS)
        if flavor is not None:
            if flavor not in DOCUMENTATION_FLAVORS:
                raise ValueError(f"unsupported documentation flavor: {flavor}")
            selected["markdown"] = f"promptB.documentation.{flavor}"
    json_id = json_prompt_id_for(domain=domain, granularity=granularity)
    if json_id is not None:
        selected["json"] = json_id
    return selected
