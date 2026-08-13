"""Web fetch + local-browser representation clean channel."""

from __future__ import annotations

import inspect

from intake.text import extract_html_text
from intake.types import BrowserFetch, CleanLanguageModel, CleanPrompt, CleanResult, HttpFetch
from intake.web.sanitize import sanitize_html_document
from src.contracts.common.errors import MkbError
from src.contracts.intake.strategies import CleanStrategyKey, resolve_clean_strategy


async def _call_fetch(fetcher: HttpFetch | BrowserFetch, url: str) -> str:
    result = fetcher(url)
    if inspect.isawaitable(result):
        result = await result
    if isinstance(result, bytes):
        return result.decode("utf-8", errors="replace")
    if isinstance(result, str):
        return result
    raise MkbError("CLEAN_WEB_FETCH_INVALID", "Web fetcher did not return text or bytes", 422)


def clean_html_representation(html: str, *, capability: str, representation: str) -> CleanResult:
    sanitized, sanitizer_evidence = sanitize_html_document(html)
    text, evidence = extract_html_text(sanitized)
    if not text:
        raise MkbError("CLEAN_EMPTY", "Web cleaning produced no admissible text", 422)
    evidence = {
        **evidence,
        **sanitizer_evidence,
        "channel": "web",
        "representation": representation,
        "strategy": CleanStrategyKey.WEB_DETERMINISTIC.value,
    }
    return CleanResult(text=text, capability=capability, evidence=evidence)


async def clean_web(
    *,
    html: str | None = None,
    url: str | None = None,
    representation: str = "static",
    strategy: str = CleanStrategyKey.WEB_DETERMINISTIC.value,
    capability: str = "clean.extract.web",
    llm: CleanLanguageModel | None = None,
    prompt: CleanPrompt | None = None,
    http_fetch: HttpFetch | None = None,
    browser_fetch: BrowserFetch | None = None,
) -> CleanResult:
    """Clean a web document from acquired HTML or an injected fetch/browser port."""

    definition = resolve_clean_strategy(strategy)
    if definition.channel != "web" or definition.clean_capability != capability:
        raise MkbError("CLEAN_STRATEGY_CAPABILITY_MISMATCH", "Web strategy does not match the Process capability", 409)
    if representation not in {"static", "rendered"}:
        raise MkbError("CLEAN_WEB_REPRESENTATION_INVALID", "Web representation is not registered", 422)
    body = html
    if body is None:
        if not isinstance(url, str) or not url:
            raise MkbError("CLEAN_WEB_INPUT_INVALID", "Web clean requires HTML bytes or a URL", 422)
        if representation == "rendered":
            if browser_fetch is None:
                raise MkbError("CLEAN_BROWSER_UNAVAILABLE", "Local browser fetch is not injected", 503)
            body = await _call_fetch(browser_fetch, url)
        else:
            if http_fetch is None:
                raise MkbError("CLEAN_HTTP_UNAVAILABLE", "HTTP fetch is not injected", 503)
            body = await _call_fetch(http_fetch, url)
    deterministic = clean_html_representation(body, capability=capability, representation=representation)
    if strategy == CleanStrategyKey.WEB_DETERMINISTIC.value:
        return CleanResult(
            text=deterministic.text,
            capability=capability,
            evidence={
                **deterministic.evidence,
                "definition_version": definition.definition_version,
                "strategy_definition_digest": definition.definition_digest,
            },
        )
    if strategy != CleanStrategyKey.WEB_LLM_REWRITE.value:
        raise MkbError("CLEAN_STRATEGY_UNSUPPORTED", "Clean strategy is not a web text strategy", 409)
    if llm is None:
        raise MkbError("CLEAN_LLM_UNAVAILABLE", "Web LLM rewrite requires an injected language model", 503)
    if prompt is None or prompt.key != definition.prompt_key or prompt.version != definition.prompt_version:
        raise MkbError("PROMPT_HASH_MISMATCH", "Web LLM rewrite lacks its frozen prompt pointer", 503)
    rewritten = (await llm.complete(prompt=prompt.text, text=deterministic.text, media_type="text/plain")).strip()
    if not rewritten:
        raise MkbError("CLEAN_EMPTY", "Web LLM rewrite produced no admissible text", 422)
    return CleanResult(
        text=rewritten,
        capability=capability,
        evidence={
            **deterministic.evidence,
            "strategy": strategy,
            "definition_version": definition.definition_version,
            "strategy_definition_digest": definition.definition_digest,
            "producer": "injected-llm",
            "prompt_key": definition.prompt_key,
            "prompt_version": definition.prompt_version,
            "prompt_content_sha256": prompt.content_sha256,
        },
    )


__all__ = ["clean_html_representation", "clean_web"]
