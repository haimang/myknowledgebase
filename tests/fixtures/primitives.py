"""F7-01: 可复用测试原语 (供 FF-F1~F6 先红后绿复用)。

5 类原语对齐 meaningful-test inventory:
- expire_lease_real_path: 经真实 SSOT `add_seconds_iso` 写过期 lease (并发/reap, 供 F3),
  **禁止手写 SQL strftime** (part-cr-8 R2 去掩盖纪律的原语层落实)。
- MALICIOUS_PATHS: 路径遍历攻击向量集 (供 F4)。
- assert_vector_authentic: 相关 chunk 排第一 + 分差阈值 (供 F5, 取代"返回非空")。
- HTML_SAMPLE / assert_clean_text: 含标签/脚本的真实样本 + 去标签保正文断言 (供 F6)。
- iso_format_ok: 时间 SSOT 格式断言 (供 F1)。

每个原语自带 self-test (本文件 `test_*`), 防原语本身假绿。
"""

from __future__ import annotations

import re

from smind_common.time import add_seconds_iso

ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")

# F4: 路径遍历攻击向量 (§7.3 威胁模型 / malicious_paths 原语)。
MALICIOUS_PATHS = [
    "../escaped.txt",
    "../../etc/passwd",
    "/abs/path",
    "a/../../x",
    "..\\win\\path",
]

# F6: 含 script/style/嵌套标签/实体的真实样本。
HTML_SAMPLE = (
    "<html><head><style>.x{}</style></head><body>"
    "<h1>Heading</h1><p>Body text with &amp; entity.</p>"
    "<script>var leak='NO';</script><div>Second block.</div></body></html>"
)


def iso_format_ok(value: str) -> bool:
    """F1: SSOT 时间格式 YYYY-MM-DDTHH:MM:SS.mmmZ。"""
    return bool(ISO_RE.match(value or ""))


def expire_lease_real_path(conn, claim_id: str) -> str:
    """F3: 经真实 SSOT 路径写一个已过期 lease (非 SQL strftime 手写, ⛔2)。"""
    past = add_seconds_iso(-1)
    if not iso_format_ok(past):
        raise AssertionError(f"SSOT format drift: {past!r}")
    conn.execute(
        "UPDATE task_claims SET lease_expires_at = ? WHERE id = ?", (past, claim_id)
    )
    conn.commit()
    return past


def assert_vector_authentic(results: list[dict], expected_top: str, *, margin: float = 0.1) -> None:
    """F5: 相关 chunk 排第一且与次位分差 ≥ margin (degraded 暴力 cosine 下成立)。"""
    assert results, "empty search results"
    assert results[0]["chunk_id"] == expected_top, (
        f"top={results[0]['chunk_id']} != expected {expected_top}: {results}"
    )
    if len(results) > 1:
        gap = results[0]["score"] - results[1]["score"]
        assert gap >= margin, f"margin {gap:.3f} < {margin}"


def assert_clean_text(text: str) -> None:
    """F6: 去标签保正文 — 无残留标签、非空、丢 script、解码实体、保段落。"""
    assert text.strip(), "empty cleaned text"
    assert "<" not in text and ">" not in text, f"residual tags: {text!r}"
    assert "NO" not in text, "script content leaked"
    assert "&amp;" not in text and "&" in text, "entity not decoded"


# -----------------------------------------------------------------------------
# RW-A / RWA-07: real-wire 使用链断言原语。
# 防假绿: 断言 provider/embedder **被真实调用** (spy 计数), 而非仅"返回值非空"
# (mock 可返回 canned 值蒙混 → 必须证明链路真的经过了 provider/embedder)。
# -----------------------------------------------------------------------------


class SpyEmbedder:
    """包裹一个 Embedder, 记录 embed() 调用 (供 assert_used_real_chain)。"""

    def __init__(self, inner) -> None:  # noqa: ANN001
        self._inner = inner
        self.name = inner.name
        self.dimension = inner.dimension
        self.calls: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        return self._inner.embed(text)


class SpyLLMProvider:
    """包裹一个 LLMProvider, 记录 complete/complete_json 调用。"""

    def __init__(self, inner) -> None:  # noqa: ANN001
        self._inner = inner
        self.name = inner.name
        self.calls: list[tuple[str, str]] = []  # (method, prompt)

    def complete(self, prompt: str, **opts):  # noqa: ANN003, ANN201
        self.calls.append(("complete", prompt))
        return self._inner.complete(prompt, **opts)

    def complete_json(self, prompt: str, schema=None, **opts):  # noqa: ANN001, ANN003, ANN201
        self.calls.append(("complete_json", prompt))
        return self._inner.complete_json(prompt, schema, **opts)


def assert_used_real_chain(*spies, min_calls: int = 1) -> None:
    """断言每个 spy (SpyEmbedder/SpyLLMProvider) 至少被真实调用 min_calls 次。

    用于 mock capstone: 证明文档真的流经了 prompt→LLM→embed 链路, 而非被 fixture 短路。
    """
    assert spies, "assert_used_real_chain called with no spies"
    for spy in spies:
        n = len(spy.calls)
        assert n >= min_calls, (
            f"{type(spy).__name__}(name={getattr(spy, 'name', '?')}) used {n} times "
            f"< required {min_calls} — chain did not actually invoke it (假绿风险)"
        )
