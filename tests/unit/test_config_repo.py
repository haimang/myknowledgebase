"""FF-F6c-T01/T02 (F6-09): prompt_versions / provider_configs 读取访问层.

先红后绿 ([Q7]): pre-F6c 两表零访问、无 config_repo → import 红。
"""

import json

from smind_config import get_active_prompt, get_active_provider
from tests.fixtures.sqlite_kernel import make_kernel_dbs


def _seed_team(conn):
    conn.execute("INSERT INTO teams (id, slug, name) VALUES ('team_x','tx','TX')")
    conn.commit()


def test_get_active_prompt_returns_active() -> None:
    core, _ = make_kernel_dbs()
    _seed_team(core)
    core.execute(
        """
        INSERT INTO prompt_versions (id, team_id, prompt_key, version, template_path,
            template_digest, status, activated_at)
        VALUES ('p1','team_x','structurize','v1','tpl/s.txt','dig1','active','2026-01-01')
        """
    )
    core.commit()
    pv = get_active_prompt(core, "team_x", "structurize")
    assert pv is not None and pv.version == "v1" and pv.template_digest == "dig1"
    assert get_active_prompt(core, "team_x", "missing") is None


def test_get_active_prompt_latest_version() -> None:
    core, _ = make_kernel_dbs()
    _seed_team(core)
    for v, act in [("v1", "2026-01-01"), ("v2", "2026-02-01")]:
        core.execute(
            """
            INSERT INTO prompt_versions (id, team_id, prompt_key, version, template_digest,
                status, activated_at) VALUES (?, 'team_x','k',?, 'd','active',?)
            """,
            (f"p_{v}", v, act),
        )
    core.commit()
    assert get_active_prompt(core, "team_x", "k").version == "v2"


def test_prompt_team_fallback_to_global() -> None:
    core, _ = make_kernel_dbs()
    _seed_team(core)
    core.execute(
        """
        INSERT INTO prompt_versions (id, team_id, prompt_key, version, template_digest, status)
        VALUES ('pg', NULL, 'global_k', 'v1', 'd', 'active')
        """
    )
    core.commit()
    # team 无此 prompt → 回退全局。
    pv = get_active_prompt(core, "team_x", "global_k")
    assert pv is not None and pv.version == "v1"


def test_get_active_provider_parses_settings() -> None:
    core, _ = make_kernel_dbs()
    _seed_team(core)
    core.execute(
        """
        INSERT INTO provider_configs (id, team_id, provider_key, version, settings_json, status)
        VALUES ('c1','team_x','chinatax','v1',?,'active')
        """,
        (json.dumps({"base_url": "https://chinatax.gov.cn", "timeout": 10}),),
    )
    core.commit()
    pc = get_active_provider(core, "team_x", "chinatax")
    assert pc is not None and pc.settings["base_url"] == "https://chinatax.gov.cn"
    assert get_active_provider(core, "team_x", "none") is None
