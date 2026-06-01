"""FF-F6a-T01/T02/T10 (F6-01/F6a-DG): clean action registry 分派 + degraded + 能力发现.

先红后绿 ([Q7]): pre-F6a HEAD 无 action_registry 模块、process_clean_step 用
`provider or universal` if/else 硬选 → import 红 + 无 list_actions。
"""

import pytest

from workflow_clean import (
    CleanActionRegistry,
    CleanContext,
    DegradedActionError,
    UnknownActionError,
    build_default_registry,
)


def test_register_and_dispatch() -> None:
    reg = CleanActionRegistry()
    reg.register("echo", lambda ctx: ctx.raw_text.upper())
    handler = reg.get_handler("echo")
    out = handler(CleanContext(source_kind="file", source_uri="", raw_text="hi"))
    assert out == "HI"


def test_unknown_branch_raises() -> None:
    reg = CleanActionRegistry()
    with pytest.raises(UnknownActionError):
        reg.get_handler("nope")


def test_default_registry_has_real_branches() -> None:
    reg = build_default_registry()
    assert reg.has("text") and reg.has("htmlCrawl") and reg.has("fetch-chinatax-articles")


def test_degraded_handler_raises_with_reason() -> None:
    reg = build_default_registry()
    for branch in ("browserFetch", "browserPDF", "geminiUnderstanding", "domain", "realestate"):
        handler = reg.get_handler(branch)
        with pytest.raises(DegradedActionError) as exc:
            handler(CleanContext(source_kind="url", source_uri="x", raw_text=""))
        assert str(exc.value)  # 机器可读 reason 非空


def test_list_actions_marks_degraded() -> None:
    specs = {s.branch: s for s in build_default_registry().list_actions()}
    assert specs["text"].degraded is False
    assert specs["htmlCrawl"].degraded is False
    assert specs["browserPDF"].degraded is True
    assert specs["domain"].degraded is True
