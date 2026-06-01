"""F6-01 / F6a-DG: clean action registry (branch→handler) + 分派抽象。

替换 `process_clean_step` 的 `provider or universal` if/else 硬选 (G-CR6-04)。
handler 是内容层 (`(ctx) -> 清洗正文`); ExecutorResult 终态/下游/run 推进统一在
`process_clean_step` 组装一次 (遵守 F3-02 终态单一归属, 避免每个 handler 复刻
artifact 写入)。degraded action 显式抛 `DegradedActionError`, 不留装成完成的桩 (⛔2)。

对齐 legacy clean-universal/services/action_registry.ts (UNKNOWN_CLEANER_BRANCH)。
"""

from __future__ import annotations

from dataclasses import dataclass

from cleaners_universal import clean_payload, html_crawl
from providers_dedicated import chinatax_etl


class UnknownActionError(RuntimeError):
    """未注册的 action branch (不可重试; 对齐 legacy UNKNOWN_CLEANER_BRANCH)。"""


class DegradedActionError(RuntimeError):
    """显式不支持的 action ([Q3] degraded), 带机器可读 reason。"""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class ActionSpec:
    branch: str
    degraded: bool
    description: str


@dataclass(frozen=True)
class CleanContext:
    source_kind: str
    source_uri: str
    raw_text: str


class CleanActionRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, object] = {}
        self._specs: dict[str, ActionSpec] = {}

    def register(self, branch: str, handler, *, degraded: bool = False, description: str = "") -> None:  # noqa: ANN001
        self._handlers[branch] = handler
        self._specs[branch] = ActionSpec(branch=branch, degraded=degraded, description=description)

    def register_degraded(self, branch: str, reason: str) -> None:
        def _degraded(_ctx, _reason=reason):  # noqa: ANN001
            raise DegradedActionError(_reason)

        self.register(branch, _degraded, degraded=True, description=reason)

    def get_handler(self, branch: str):  # noqa: ANN001
        if branch not in self._handlers:
            raise UnknownActionError(f"unknown action branch: {branch!r}")
        return self._handlers[branch]

    def has(self, branch: str) -> bool:
        return branch in self._handlers

    def list_actions(self) -> list[ActionSpec]:
        return sorted(self._specs.values(), key=lambda s: s.branch)


def build_default_registry(*, llm=None, render_clean_prompt=None) -> CleanActionRegistry:  # noqa: ANN001
    """构建 clean action 注册表。

    RWB-06: 当传入 `llm` (LLMProvider) + `render_clean_prompt` (raw_text→已渲染 prompt,
    由 workflow 层绑定 conn/team_id) 时, `geminiUnderstanding` 注册为**真实 LLM handler**
    (走 prompt→provider); 否则保持 [Q3] degraded fallback。真实 MLX provider 延后, 本轮
    经 MockLLMProvider 验链路。handler 仍只产正文 (F3-02 终态单一归属), 不复刻 artifact 写入。
    """
    reg = CleanActionRegistry()
    # 真实实现 ([Q3] 增量范围)。
    reg.register(
        "text",
        lambda ctx: clean_payload(ctx.source_kind, ctx.raw_text),
        description="file/static/api plain-text clean",
    )
    reg.register(
        "htmlCrawl",
        lambda ctx: html_crawl(ctx.source_uri),
        description="url static fetch + HTML→text",
    )
    reg.register(
        "fetch-chinatax-articles",
        lambda ctx: chinatax_etl(ctx.source_uri),
        description="chinatax dedicated ETL",
    )
    # [Q3] 显式 degraded (浏览器/PDF/多 provider)。
    for branch, reason in (
        ("browserFetch", "browser rendering not supported this round"),
        ("browserFetch-geminiClean", "browser+LLM clean not supported this round"),
        ("browserPDF", "PDF rendering not supported this round"),
        ("browserPDF-geminiClean", "PDF+LLM clean not supported this round"),
        ("domain", "domain provider not supported this round"),
        ("realestate", "realestate provider not supported this round"),
        ("scatter", "scatter/multi-document not supported this round"),
    ):
        reg.register_degraded(branch, reason)
    # RWB-06: geminiUnderstanding — LLM 模式 (真实/mock provider 注入) 或 degraded fallback。
    if llm is not None and render_clean_prompt is not None:
        reg.register(
            "geminiUnderstanding",
            lambda ctx: llm.complete(render_clean_prompt(ctx.raw_text)).text,
            description="LLM understanding clean (prompt→provider)",
        )
    else:
        reg.register_degraded(
            "geminiUnderstanding", "LLM understanding not supported this round"
        )
    return reg
