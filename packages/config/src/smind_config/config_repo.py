"""F6-09: prompt_versions / provider_configs 读取访问层 (从零访问 → 可读)。

供 FF-F6a (provider_configs) / FF-F6b (prompt_versions) 去桩按
`(team_id, key, status='active')` 解析配置载体。team 级优先, 回退全局 (team_id IS NULL)。
本轮只做**读路径** (写入/激活端点 OOS, [O3])。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from sqlite3 import Connection


@dataclass(frozen=True)
class PromptVersion:
    prompt_key: str
    version: str
    template_path: str | None
    template_digest: str
    metadata: dict


@dataclass(frozen=True)
class ProviderConfig:
    provider_key: str
    version: str
    settings: dict


def get_active_prompt(
    conn: Connection, team_id: str | None, prompt_key: str
) -> PromptVersion | None:
    row = _select_active(
        conn,
        table="prompt_versions",
        key_col="prompt_key",
        key=prompt_key,
        team_id=team_id,
    )
    if row is None:
        return None
    return PromptVersion(
        prompt_key=row["prompt_key"],
        version=row["version"],
        template_path=row["template_path"],
        template_digest=row["template_digest"],
        metadata=json.loads(row["metadata_json"] or "{}"),
    )


def get_active_provider(
    conn: Connection, team_id: str | None, provider_key: str
) -> ProviderConfig | None:
    row = _select_active(
        conn,
        table="provider_configs",
        key_col="provider_key",
        key=provider_key,
        team_id=team_id,
    )
    if row is None:
        return None
    return ProviderConfig(
        provider_key=row["provider_key"],
        version=row["version"],
        settings=json.loads(row["settings_json"]),
    )


def _select_active(conn: Connection, *, table: str, key_col: str, key: str, team_id: str | None):
    # team 级优先, 未命中回退全局 (team_id IS NULL)。多版本取最新 activated_at/version。
    candidates: list[tuple[str, tuple]] = []
    if team_id is not None:
        candidates.append((f"team_id = ? AND {key_col} = ?", (team_id, key)))
    candidates.append((f"team_id IS NULL AND {key_col} = ?", (key,)))
    for where, params in candidates:
        row = conn.execute(
            f"SELECT * FROM {table} WHERE {where} AND status = 'active' "
            "ORDER BY activated_at DESC, version DESC LIMIT 1",
            params,
        ).fetchone()
        if row is not None:
            return row
    return None
