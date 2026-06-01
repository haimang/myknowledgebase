"""F5-01: 真实 (语义相关) embedding 替换 SHA-256 伪向量。

[Q2] 裁决=选项 A: `Embedder` adapter + 本地小模型, 维度强约束 = 1536。
本环境离线、无 numpy/sentence-transformers, 故"本地小模型"的忠实落地为
**纯 stdlib 确定性 signed feature-hashing 词袋**: 把文本切成词/字 token 与
字符 n-gram, 每个 token 经 md5 哈希投影到 1536 维之一并带符号累加, 最后 L2 归一。

与被替换的 SHA-256 伪向量 (`embed_text_fake`) 的本质区别: 共享 token 的文本
余弦更高 (语义相关源于词面重叠), 而 SHA 哈希向量与文本语义零关联。真实神经
embedding (捕捉超越词面的同义性) 需 ML 依赖, 离线不可得 → 记技术债 handoff
(见 FF-F5-closure §4)。
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol, runtime_checkable

DIMENSION = 1536

# 拉丁词 (含数字) + 单个 CJK 字。CJK 不依赖空格分词, 逐字 + 相邻二元组捕捉局部序。
_LATIN_RE = re.compile(r"[a-z0-9]+")
_CJK_RE = re.compile(r"[一-鿿]")


@runtime_checkable
class Embedder(Protocol):
    """写/查共用的 embedding 适配层契约 (⛔3: 写/查必须同一实现)。"""

    name: str
    dimension: int

    def embed(self, text: str) -> list[float]: ...


def _tokens(text: str) -> list[str]:
    """切 token: 拉丁词 + CJK 单字 + CJK 相邻二元组 + 拉丁词 3-char-gram。

    字符 n-gram 给一点形态鲁棒性 (running/runs 共享前缀 gram), 使相关性不止于
    精确词匹配。
    """
    lowered = text.lower()
    toks: list[str] = []
    for word in _LATIN_RE.findall(lowered):
        toks.append(f"w:{word}")
        if len(word) >= 4:
            for i in range(len(word) - 2):
                toks.append(f"g:{word[i:i + 3]}")
    cjk = _CJK_RE.findall(text)
    for i, ch in enumerate(cjk):
        toks.append(f"c:{ch}")
        if i + 1 < len(cjk):
            toks.append(f"b:{ch}{cjk[i + 1]}")
    return toks


def _hash_dim_sign(token: str) -> tuple[int, float]:
    digest = hashlib.md5(token.encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:4], "big") % DIMENSION
    sign = 1.0 if (digest[4] & 1) == 0 else -1.0
    return bucket, sign


class LocalEmbedder:
    """确定性、离线、零计费的本地 embedding (维度 = 1536)。"""

    name = "local-bow-hash-v1"
    dimension = DIMENSION

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * DIMENSION
        for tok in _tokens(text or ""):
            bucket, sign = _hash_dim_sign(tok)
            vec[bucket] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            # 空 / 无可切 token 文本: 返回零向量 (cosine 与任意向量为 0, 不串味)。
            return vec
        out = [v / norm for v in vec]
        if len(out) != DIMENSION:  # 不变式: adapter 边界强约束维度 (⛔5)
            raise ValueError(f"embedding dimension drift: {len(out)} != {DIMENSION}")
        return out


_DEFAULT_EMBEDDER = LocalEmbedder()


def default_embedder() -> LocalEmbedder:
    """返回进程级默认 Embedder (写/查共用同一实现)。"""
    return _DEFAULT_EMBEDDER


def embed_text(text: str, dims: int = DIMENSION) -> list[float]:
    """交付用 embedding: 委托给本地小模型 (LocalEmbedder)。

    写入侧 (workflow_rag) 与查询侧 (search) 都经此函数 → 同一 Embedder 实例,
    避免"查询命中自身"掩盖向量无意义 (⛔3 / part-cr-7 R1)。
    """
    if dims != DIMENSION:
        raise ValueError(f"unsupported embedding dimension: {dims} (must be {DIMENSION})")
    return _DEFAULT_EMBEDDER.embed(text)


def embed_text_fake(text: str, dims: int = DIMENSION) -> list[float]:
    """⚠️ 仅离线测试 fixture, 非交付向量 (旧 SHA-256 链式哈希伪向量, G-CR7-01)。

    与文本语义零关联; 切勿用于交付检索或语义断言 (§8.5)。保留仅为对照/红测。
    """
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
