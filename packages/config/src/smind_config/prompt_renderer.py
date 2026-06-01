"""RW-B / RWB-02+03: prompt 渲染引擎 + 本地文件↔SQLite-SSOT digest 对账。

Q-RW-3 架构: prompt 正文存本地文件 (owner 编辑层) → 经 sha256 digest 注册入
`prompt_versions` (SQLite = SSOT, 替代 Cloudflare KV)。运行时 `render_prompt`:
  get_active_prompt(SQLite) → 读 template_path 文件 → 校 sha256 == template_digest
  (不一致 fail-loud, 禁止静默用文件/旧本) → 注入 {{var}} (缺变量 fail-loud) → 返回。
SQLite 是「哪个 prompt/版本/digest 权威」的 SSOT; 本地文件是被其 digest 校验的编辑层。
"""

from __future__ import annotations

import re
from hashlib import sha256
from pathlib import Path
from sqlite3 import Connection

from .config_repo import get_active_prompt

_VAR_RE = re.compile(r"\{\{(\w+)\}\}")


class PromptError(RuntimeError):
    """prompt 渲染失败基类 (机器可读 reason)。"""

    def __init__(self, reason: str, detail: str = "") -> None:
        self.reason = reason
        super().__init__(f"{reason}: {detail}" if detail else reason)


def compute_digest(text: str) -> str:
    """prompt 正文 → sha256 hexdigest (SSOT 对账用)。"""
    return sha256(text.encode("utf-8")).hexdigest()


def _resolve_template_path(prompts_dir: str | Path, template_path: str) -> Path:
    return Path(prompts_dir) / template_path


def seed_prompt_version(
    conn: Connection,
    *,
    prompt_key: str,
    template_path: str,
    prompts_dir: str | Path = "prompts",
    version: str = "v1",
    team_id: str | None = None,
) -> str:
    """读本地 prompt 文件 → 算 digest → INSERT 一行 prompt_versions (SQLite-SSOT)。返回 digest。"""
    path = _resolve_template_path(prompts_dir, template_path)
    if not path.is_file():
        raise PromptError("prompt_file_missing", str(path))
    digest = compute_digest(path.read_text(encoding="utf-8"))
    row_id = f"pv_{prompt_key}_{version}" + ("" if team_id is None else f"_{team_id}")
    conn.execute(
        """
        INSERT OR REPLACE INTO prompt_versions (
            id, team_id, prompt_key, version, template_path, template_digest,
            metadata_json, status, activated_at
        ) VALUES (?, ?, ?, ?, ?, ?, NULL, 'active', strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        """,
        (row_id, team_id, prompt_key, version, template_path, digest),
    )
    conn.commit()
    return digest


def sync_prompts_dir(
    conn: Connection,
    mapping: dict[str, str],
    *,
    prompts_dir: str | Path = "prompts",
    team_id: str | None = None,
) -> dict[str, str]:
    """批量 seed: {prompt_key -> template_filename}。返回 {prompt_key -> digest}。"""
    return {
        key: seed_prompt_version(
            conn, prompt_key=key, template_path=fname, prompts_dir=prompts_dir, team_id=team_id
        )
        for key, fname in mapping.items()
    }


def render_prompt(
    conn: Connection,
    team_id: str | None,
    prompt_key: str,
    variables: dict[str, object],
    *,
    prompts_dir: str | Path = "prompts",
) -> str:
    """SQLite-SSOT 渲染: 取活跃记录 → 加载文件 → digest 对账 (fail-loud) → 注入变量。"""
    pv = get_active_prompt(conn, team_id, prompt_key)
    if pv is None:
        raise PromptError("prompt_not_registered", prompt_key)
    if not pv.template_path:
        raise PromptError("prompt_template_path_empty", prompt_key)
    path = _resolve_template_path(prompts_dir, pv.template_path)
    if not path.is_file():
        raise PromptError("prompt_file_missing", str(path))
    raw = path.read_text(encoding="utf-8")
    actual = compute_digest(raw)
    if actual != pv.template_digest:
        # 文件↔SQLite 不一致: 文件被改未重新 seed → fail-loud, 不静默用文件 (假 SSOT)。
        raise PromptError(
            "prompt_digest_mismatch",
            f"{prompt_key}: file={actual[:12]} != ssot={pv.template_digest[:12]}",
        )
    missing: list[str] = []

    def _sub(m: re.Match) -> str:
        name = m.group(1)
        if name not in variables:
            missing.append(name)
            return m.group(0)
        return str(variables[name])

    rendered = _VAR_RE.sub(_sub, raw)
    if missing:
        raise PromptError("prompt_missing_variables", ",".join(sorted(set(missing))))
    return rendered
