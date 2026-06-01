# [跨 F1–F7 审查隐患修复] Closure

> 阶段: `first-fixes · 收口后跨阶段代码审查 → 全量修复`
> 范围: `M1 检索去重 / M2 chunk_count 据实 / M3 chinatax fail-loud / L1 workspace_key 一致 / L2 API key 吊销 / L3 prefix 收窄 / L6 SSRF 守卫`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-06-01` · 作者: `Opus 4.8`
> 关联: owner 请求"跨 F1–F7 全面代码审查找出遗漏隐患"→ 审查报告（会话内）→ 本次全量修复
> 提交: 代码+测试 `3ce4e7a`

---

## 0. 一句话 verdict

> 收口后对 F1–F7 做对抗性代码审查，确认无 Critical/High，定位 3 个 Medium（M1 双通道检索近重复、M2 content_hash 冲突致 chunk_count 虚高、M3 chinatax 空结果静默 completed）+ 4 个 Low（L1 workspace_key 写读错配、L2 无吊销端点、L3 prefix 含较多密文、L6 htmlCrawl/chinatax SSRF），**全部修复**并补 31 条先红后绿回归；全量 203→**234 passed + 1 xfailed**（exit 0），断言强度门禁 47 文件 0 命中。

---

## 1. 修复收口表

| 编号 | 隐患 | 修复 | 证据（commit + test） |
|------|------|------|------|
| M1 | 双通道 original/summary 在检索侧无去重 → 近重复结果 | `search._search_internal` 按 (document_id, chunk_index) 去重保留最高分通道；`_logical_key` 从 artifact metadata 解析 | `3ce4e7a + test_review_fixes::test_m1_search_no_duplicate_logical_chunk` |
| M2 | content_hash 冲突(OR IGNORE 跳过)致 constructed_json.chunk_count 虚高 | construct 仅 `rowcount==1` 时计入 chunk_ids | `3ce4e7a + test_review_fixes::test_m2_chunk_count_matches_actual_rows` |
| M3 | chinatax 空/不可解析结果静默返回 ""→ 零内容 completed | `chinatax_etl` 0 item 抛 `ApiRequestError`（与 htmlCrawl 空抽取一致） | `3ce4e7a + test_provider_registry::test_chinatax_etl_empty_result_fail_loud` |
| L1 | 写侧 VectorStore workspace_key=app_env, 读侧=team_id（潜在地雷） | vectorize 用 `run.team_id` | `3ce4e7a + test_review_fixes::test_l1_namespace_key_is_team_id` |
| L2 | 无 API key 吊销端点（泄漏 key 只能直连 DB 撤销） | `AuthService.revoke_api_key` + `POST /team/api-keys/revoke`（owner-only/404/403） | `3ce4e7a + test_api_key_revoke(3)` |
| L3 | key_prefix=raw[:12] 含 9 位密文 | 收窄为 raw[:8] | `3ce4e7a + test_ssrf_guard::test_key_prefix_is_short_not_full_secret` |
| L6 | htmlCrawl/chinatax 外部抓取无 SSRF 防护 | `smind_common.net.assert_safe_url`（仅 http/https + 拒 loopback/私有/链路本地/元数据）接入 fetch_url/fetch_api | `3ce4e7a + test_ssrf_guard(SSRF 参数化)` |

---

## 2. Evidence

| 验证 | 命令 | 结果 |
|------|------|------|
| 全量回归 | `python3 -m pytest tests/` | `234 passed + 1 xfailed`（exit 0；203+31） |
| 断言强度门禁 | `python3 tools/scripts/check_assert_strength.py tests/` | `47 文件 0 命中` |
| 编译 | `python3 -m compileall packages apps tools tests` | rc=0 |
| SSRF | `pytest tests/unit/test_ssrf_guard.py` | 内网/loopback/元数据/非 http 全拒；公网放行 |
| 吊销 | `pytest tests/integration/p2_control_plane/test_api_key_revoke.py` | owner 吊销→401；未知→404；非 owner→403 |

---

## 3. Deferred / 仍保留（已评估，非本次修复）

| 项 | 类型 | 理由 |
|----|------|------|
| L4 validate_api_key 每请求写 last_used_at + commit | B | **有意行为**（审计 last_used），非缺陷；扩展性优化交后继（可改异步/采样） |
| L5 purge 跨资源非事务窗口（对象删 vs core 提交） | B | 跨 substrate（FS/core/vec 三库）架构限制；delete missing_ok 幂等 + 重试自愈；最终一致性交生产化 |
| 真实 vec0 / 神经 embedding / PDF/浏览器 真实样本 | A | [Q1][Q2][Q3] degraded，下一轮 |
| 断言门禁接入 CI runner | C | 脚本+self-test 已落地；接 CI step 待平台 |

> **L6 SSRF 状态更新**：原在 FF-F6a/FF-F6c closure §4 标为 handoff（"htmlCrawl SSRF 未处置"），**本次已修复**（基于主机名的确定性守卫，拦截 loopback/私有/链路本地/云元数据 + 非 http(s) scheme）。注：基于主机名不做 DNS 解析，DNS-rebinding 类高级绕过仍需生产化阶段加解析后复检（记下一轮）。

---

## 4. 诚实声明

- 审查为对抗性自审：逐区重读 F4-F7 代码 + 推演边界/竞态/跨资源/安全，区分"真实缺陷 / 潜在地雷 / 已核验OK"，不只复述已完成项。
- 每项修复带先红后绿回归（M3 是行为变更：旧测试 `test_chinatax_etl_empty_result_no_crash` 据实改为 `_fail_loud`）。
- L4/L5 经评估保留并说明（非回避）；L6 SSRF 修复诚实标注"主机名级、DNS-rebinding 待生产化"，不夸大。
- 全量 234 passed + 1 xfailed 含 F1-F7 既有 203 用例无回归。
