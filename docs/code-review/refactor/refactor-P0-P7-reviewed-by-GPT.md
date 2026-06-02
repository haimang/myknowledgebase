# [Refactor-P0-P7 / 全阶段复审] Closure

> 阶段: `smind-family/P0-P7 — refactor 全阶段复审`
> 范围: `P0-P7 action-plan / closure / 执行日志 / 事实代码 / tests / docs/refactor/index.md / docs/refactor/todo-list.md / docs/refactor/core.sql / docs/refactor/vec.sql`
> Close-type: `close-with-known-issues`
> 状态: `close-with-known-issues`
> 日期: `2026-05-31` · 作者: `GPT-5.4`
> 关联 charter: `docs/refactor/todo-list.md`
> 关联 design: `docs/refactor/index.md`
> 关联 action-plan: `docs/action-plan/P0.md` ~ `docs/action-plan/P7.md`
> 关联 evidence: `inline §2`
> 关联 review: `docs/code-review/refactor-P0-P7-reviewed-by-GPT.md`

---

## 0. 一句话 verdict

> 本次复审结论是：当前仓库已经形成 **P0-P2 的基础骨架 + 一条 submit → clean → rag → search → ops 的最小 happy-path demo**，但**并不构成 `docs/action-plan/P0.md` ~ `P7.md` 与 `docs/closure/P0-closure.md` ~ `P7-closure.md` 所宣称的 P0-P7 `full-close`**；其中 P2 存在真实租户越权与会话过期失效问题，P4/P5/P6 与 action-plan 的 contract 漂移明显，P7 仅完成了 grep 级 legacy freeze 守卫，尚未完成真正的 cutover / parity / rollback gate。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. `team/select` 未校验 membership，B 用户可切到 A 团队并成功读取 A 团队的 `/management/documents`，这会直接击穿 P2/P5/P6 的 team boundary。
> 2. 检索面会返回 `archived` 文档，`/search` 返回体里的 `chunk_text` 实际是 `content_hash`，`/search/debug` 也没有 raw hits / filtered hits / filter reasons，P5 的 API surface 与 debug surface 都未达到 action-plan。
> 3. P4/P6/P7 的实现仍停留在 happy-path/demo 或 grep-guard 级别：RAG 没有独立 vectorize stage / `constructed_json` / `pending_vectorize -> vectorized` 生命周期；ops 没有 audit trail、mismatch detector、operator CLI；P7 没有 parity matrix、shadow diff、default entrypoint cutover、rollback drill。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| `P0 基础骨架` | ✅ | `docs/action-plan/P0.md:71-103,442-456`、`docs/closure/P0-closure.md:18-30`、`README.md:14-27`、`apps/api/src/smind_api/main.py:15-38`、`apps/worker/src/smind_worker/main.py:21-76`、`apps/cli/src/smind_cli/main.py:19-46`、`tests/smoke/*.py` —— 说明 repo 骨架、三入口与 smoke 基线真实存在 |
| `P1 数据库与状态内核` | 🟡 partial | `docs/action-plan/P1.md:74-105,138-143,583-607`、`docs/closure/P1-closure.md:18-30`、`packages/storage_sqlite/**`、`packages/workflow_core/**`、`tests/integration/p1_kernel_closure/*.py` —— 最小 kernel 成立；但 `packages/vector_sqlite_vec/src/vector_sqlite_vec/schema.py:24-59` 会把 SSOT `vec0` 虚表回退成普通表，形成事实 schema drift；`packages/workflow_core/src/workflow_core/graph.py:9-35` 定义了 event writer，但全仓没有接线调用 |
| `P2 控制面与 ingestion` | 🟡 partial | `docs/action-plan/P2.md:20-48,111-133,657-675`、`docs/closure/P2-closure.md:18-30`、`packages/auth/src/auth/service.py:28-56`、`packages/team/src/team/service.py:41-43`、`apps/api/src/smind_api/routes/team.py:34-38` —— 基础 northbound 面成立；但 API key 面缺失、`expires_at` 不参与鉴权、`team/select` 无 membership 校验，已被定点复现为跨 team 越权 |
| `P3 Clean Pipeline` | 🟡 partial | `docs/action-plan/P3.md:72-108,142-147,159-166,661-663`、`docs/closure/P3-closure.md:18-28`、`packages/workflow_clean/src/workflow_clean/service.py:35-97`、`packages/cleaners_universal/src/cleaners_universal/service.py:6-11`、`packages/providers_dedicated/src/providers_dedicated/service.py:4-8`、`tests/integration/p3_clean_pipeline/test_clean_pipeline.py:33-69` —— 只存在最小 clean -> artifact -> rag handoff；planner/finalizer/action registry/browser runtime/provider contract 仍远未达到 action-plan 描述 |
| `P4 RAG Pipeline` | 🟡 partial | `docs/action-plan/P4.md:78-119,154-159,520-528,696-701`、`docs/closure/P4-closure.md:18-28`、`packages/workflow_rag/src/workflow_rag/service.py:42-132`、`tests/integration/p4_rag_pipeline/test_rag_pipeline.py:38-55` —— 只有 `rag:structurize -> rag:construct` 两步 happy-path；没有独立 `vectorize` stage、没有 `constructed_json` artifact、没有 `pending_vectorize -> vectorized` 状态推进，和 P4 DoD 存在实质漂移 |
| `P5 检索与查询面` | 🟡 partial | `docs/action-plan/P5.md:80-122,159-164,503-507,667-671`、`docs/closure/P5-closure.md:18-28`、`packages/vector_sqlite_vec/src/vector_sqlite_vec/store.py:91-106`、`packages/rag_vectorizer/src/rag_vectorizer/search.py:15-54`、`apps/api/src/smind_api/routes/search.py:20-41`、`tests/integration/p5_search_surface/test_search.py:39-47` —— 基础 search 能跑，但 namespace/model guard、post-filter、debug retrieval、hydrated content 都没有达到计划定义 |
| `P6 运维与恢复能力` | 🟡 partial | `docs/action-plan/P6.md:73-109,147-152,493-497,673-678`、`docs/closure/P6-closure.md:18-28`、`packages/workflow_core/src/workflow_core/restart.py:26-91`、`packages/workflow_core/src/workflow_core/purge.py:26-93`、`packages/workflow_core/src/workflow_core/health.py:6-28`、`apps/cli/src/smind_cli/main.py:20-41`、`tests/integration/p6_operations/test_operations.py:40-61` —— 只有 restart/purge/health happy-path；缺 audit logs、mismatch detector、pending_purge detector、step inspect/retry CLI、recovery drills |
| `P7 收敛与替换` | ❌ | `docs/action-plan/P7.md:72-109,143-148,624-626`、`docs/closure/P7-closure.md:18-28`、`tools/scripts/check_legacy_freeze.sh:4-17`、`tests/integration/p7_cutover/test_cutover.py:5-9` —— 事实交付只有 grep 级 legacy freeze enforcement；看不到 parity matrix 自动校验、golden fixtures、shadow diff、default entrypoint cutover、rollback drill、management-plane cutover |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| 现状全量回归 | `python3 -m pytest tests/integration tests/smoke` | `14 passed in 0.91s` | 证明当前仓库至少有一条 demo 级 happy-path；不能证明 action-plan 的完整 DoD 已兑现 |
| 规范检查 | `python3 -m ruff check .` | `All checks passed!` | 代码风格与导入层面无显式错误 |
| vec schema 事实形态 | 定点脚本：`apply_vec_schema()` 后查询 `sqlite_master` | `chunk_embedding_index` 实际为普通 `table`，不是 `docs/refactor/vec.sql:58-60` 的 `vec0` virtual table | 证明 `packages/vector_sqlite_vec/src/vector_sqlite_vec/schema.py:24-59` 存在 dev/runtime 级 schema drift |
| 租户隔离核验 | 定点脚本：User B `POST /team/select {team_id: TeamA}` 后 `GET /management/documents` | `200`，且返回 Team A 文档 | 证明 `apps/api/src/smind_api/routes/team.py:34-38` + `packages/team/src/team/service.py:41-43` 形成真实越权 |
| 会话过期核验 | 定点脚本：把 `sessions.expires_at` 改到过去后调用 `/auth/session` | 仍然 `200` | 证明 `packages/auth/src/auth/service.py:47-56` 未校验 `expires_at` |
| 检索过滤/结果体核验 | 定点脚本：把已向量化文档改为 `archived` 后调用 `/search` | 仍返回命中；返回体 `chunk_text` 为 SHA-256 hash | 证明 `packages/rag_vectorizer/src/rag_vectorizer/search.py:22-54` 没有按 `v_search_hydration.core_post_filter_eligible` 过滤，也没有 hydrate 实际 chunk text |
| RAG 落地形态核验 | 定点脚本：完整跑一条 URL -> worker 链后读取 `workflow_steps` / `artifacts` | 实际只有 `clean` / `rag:structurize` / `rag:construct` 三步；artifact 只有 `cleaned_text` 与 `structured_json` | 证明 `packages/workflow_rag/src/workflow_rag/service.py:42-132` 没有实现 action-plan 要求的 `constructed_json` / vectorize step / `pending_vectorize` 生命周期 |
| Ops 审计核验 | 定点脚本：执行 restart + purge 后查询 `audit_logs` | `audit_logs = 0`；只有 `restart_requests = 1`、`purge_requests = 1` | 证明 P6 尚未兑现 `docs/action-plan/P6.md:57-58,147-152,493-497` 的 audit/debug surface |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| 基础骨架 gate | P0 至少提供可安装、可启动、可 smoke 的 monorepo 基线 | `README.md`、三入口、smoke tests 与当前 `pytest tests/integration tests/smoke` 均成立 | ✅ PASS |
| 租户与会话安全 gate | team 选择必须受 membership 约束；session expiry 必须参与鉴权 | `team/select` 越权可复现；expired session 仍可通过 `/auth/session` | ❌ FAIL |
| RAG contract gate | P4 必须存在 `structured -> constructed -> chunks -> vectorize` 明确图谱，且 `chunks.vec_status` 走 `pending_vectorize -> vectorized` | 当前只有 `rag:structurize -> rag:construct`；construct 内直接 upsert vector 并写 `vec_status='vectorized'` | ❌ FAIL |
| Retrieval correctness gate | P5 必须执行 namespace/model guard、candidate over-fetch、core truth post-filter、hydrated result、debug filter reasons | 当前 search 全表扫 vec 记录，忽略 `document_status/source_status/core_post_filter_eligible`，`chunk_text` 仅为 `content_hash`，`/search/debug` 无真实 debug 信息 | ❌ FAIL |
| Ops / recovery gate | P6 必须具备 request state machine、audit trail、detectors、operator API/CLI、drills | 当前只有 request row + restart/purge happy-path + `ops-health`；无 audit、无 mismatch detector、无 inspect/retry CLI、无 drills | ⚠ PARTIAL |
| Cutover gate | P7 必须完成 parity matrix、shadow diff、default switch、rollback drill、legacy freeze | 当前只有 `check_legacy_freeze.sh` 与单测；无 default entrypoint cutover、无 parity/canary/rollback 资产 | ❌ FAIL |
| 文档一致性 gate | action-plan、执行日志、closure、代码事实必须口径一致 | `docs/action-plan/P4.md:532-534`、`P5.md:511-513`、`P6.md:501-503` 的 `## 9. 执行日志回填` 仍是 `draft`，但对应 closure 已宣称 `full-close` | ❌ FAIL |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| 修复 `team/select` 越权、session expiry 缺失、补齐 API key surface | `B` | 未完成，且属于阻断问题 | 先修 `packages/team` / `packages/auth` / `apps/api`，再补 negative tests；未完成前不应宣称 P2 `full-close` | `P2 maintainer` |
| 把 P4 恢复到 action-plan contract：`constructed_json`、独立 vectorize stage、`pending_vectorize -> vectorized`、artifact pointer 更新 | `B` | 未完成 | 优先重构 `packages/workflow_rag` / `packages/rag_constructor` / `packages/rag_vectorizer`；P5/P6 继续消费前必须先收口 | `P4 maintainer` |
| 重写 P5 retrieval：namespace/model guard、core truth post-filter、hydrated chunk text/snippet、debug reasons | `B` | 未完成且已有错误返回 | 修 `packages/vector_sqlite_vec` / `packages/rag_vectorizer` / `apps/api`；补 archived / cross-team / pending_purge / candidate depletion tests | `P5 maintainer` |
| 明确 vec schema policy：要么硬依赖 `vec0`，要么把 fallback 升格为显式版本化 schema 与文档合同 | `B` | 当前存在事实 drift | 先回写 `docs/refactor/vec.sql` / `docs/refactor/database.md` 或禁止 fallback；否则 P1/P5 的“无 drift”前提不成立 | `P1/P5 maintainer` |
| 补齐 P6 的 audit logs / workflow events 接线、detectors、operator CLI、drills | `B` | 未完成 | 修 `workflow_core` / `management` / `apps/cli` / `tests/integration/p6_operations`；完成前不应宣称 P6 `full-close` | `P6 maintainer` |
| 真正交付 P7：parity matrix、golden fixtures、shadow diff、default switch、rollback gate、management-plane cutover | `C` | 基本未开始 | 按 `docs/action-plan/P7.md:78-108,143-148` 重新拆分并落盘；当前 closure 应降级 | `P7 maintainer` |
| 把现有 closure 口径回调到真实状态 | `C` | 未完成 | 至少 P2、P4、P5、P6、P7 应从 `full-close` 下调到 `close-with-known-issues` 或更保守状态 | `refactor owner` |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred）| ⚠（当前 8 份 closure 几乎把所有 ✅ 都当作 `verified`；但从代码与测试看，P3-P7 大多只是 happy-path `observed-OK-at-closure` 或 `partial`） |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | ⚠（现有 closure 统一写成 `working-tree + 测试名 + 时间`，没有 commit SHA；且测试粒度普遍不足以支撑 `full-close`） |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改）| ⚠（本次复审环境未提供可追溯的提交边界；既有 closure 也没有给出足够的 diff 守卫证据） |
| deferred 已三分类（A/B/C）且每项有承接位置 | ⚠（表面上有 ledger，但很多真正影响 P4-P7 结论的结构性缺口没有进入 deferred，而是被 closure 直接跳过） |
| owner-test 项未经 owner 复测的标 ⏸ PENDING（无「我修了」式宣称）| N/A |

---

## 6. Handoff / 下阶段 entry-gate 预核对

| 入口条件 | 状态 | 备注 |
|----------|------|------|
| P2 安全边界先修复（membership / session expiry / API key） | `⏸` | 这是所有后续 team-scoped management/search/ops 的前置 gate |
| P4 graph 与 artifact contract 纠偏完成 | `⏸` | P5/P6 当前站在漂移后的简化 RAG 上，继续叠加会放大返工 |
| P5 retrieval 过滤与 debug 真相层补齐 | `⏸` | archived/purged/cross-team/pending_purge 必须先收口 |
| P6 audit/detector/operator CLI 到位 | `⏸` | 没有它们，P7 的 cutover / rollback 无法成立 |
| P7 真正的 parity/cutover 资产落地 | `⏸` | 当前只有 grep 守卫，不足以进入 cutover 讨论 |

**下阶段 kickoff checklist**：
- [ ] 以本文作为当前 P0-P7 事实真相锚点，先下调 closure 口径，再重新定义 repair scope
- [ ] 先把 `P2 security`、`P4 graph drift`、`P5 retrieval correctness` 三个 blocking 项拆成独立修复批次
- [ ] 为 archived/cross-team/pending_purge/API-key/session-expiry/vectorize-stage/constructed-artifact/audit-log 增加明确回归用例

---

## 7. Cross-cut 不变量（0-drift 确认）

| 不变量 | 状态 | 证据 |
|--------|------|------|
| `core.db` 仍是 workflow kernel 真相层 | `✅ 保持` | `apps/worker/src/smind_worker/main.py:24-55` 通过 `workflow_runs/workflow_steps/task_claims` 驱动主循环；`docs/refactor/index.md:69-75`、`docs/refactor/todo-list.md:97-101` 的大方向基本成立 |
| 向量操作仍通过 `VectorStore` 适配层完成 | `✅ 保持` | `packages/workflow_rag/src/workflow_rag/service.py:82-120`、`packages/rag_vectorizer/src/rag_vectorizer/search.py:11-18` 都通过 `VectorStore` 访问 vec 层 |
| 检索必须是“vec candidate -> core truth hydrate/filter”两段式 | `❌ 漂移` | `docs/action-plan/P5.md:80-122` 要求两段式；但 `packages/rag_vectorizer/src/rag_vectorizer/search.py:22-54` 没有消费 `v_search_hydration.core_post_filter_eligible/core_post_filter_reason` |
| `chunks.vec_status` 生命周期应显式推进 | `❌ 漂移` | `docs/refactor/todo-list.md:408-412` 与 `docs/action-plan/P4.md:90-92,154-159` 要求 `pending_vectorize -> vectorized`；但 `packages/workflow_rag/src/workflow_rag/service.py:86-120` 直接写成 `vectorized` |
| `legacy-family` 只读、不承接新 runtime | `⚠ 部分保持` | `tools/scripts/check_legacy_freeze.sh:4-17` 的 grep guard 存在，但它不等于 default cutover / rollback gate；`docs/action-plan/P7.md:78-108` 的主目标仍未兑现 |
| 文档与实现应保持同口径 | `❌ 漂移` | `docs/action-plan/P4.md:532-534`、`P5.md:511-513`、`P6.md:501-503` 的执行日志节仍为 `draft`，而 closure 已宣称 `full-close` |

---

## 8. 价值 / 负债台账

**价值台账**

| 章节 | 真实价值 | 状态 |
|------|----------|------|
| `P0-P1` | monorepo 骨架、双库 bootstrap、最小 claim/lease/retry/reaper 内核已落地；这是后续修复仍可复用的基础 | `🟢 short-verified` |
| `P2` | FastAPI 控制面、基础 ingestion 与 management list/detail 已形成最小 northbound demo | `🟡 partial` |
| `P3-P5` | 仓库内已经有一条单团队 happy-path：submit -> clean -> rag -> search 可以跑通，便于后续修正 contract | `🟡 partial` |
| `P6-P7` | request row、health summary、legacy freeze grep guard 已有最小雏形，能作为后续 operator/cutover 的起点 | `🟡 partial` |

**负债台账**

| # | 负债 | 级别 | 来源 | 消化路径 |
|---|------|------|------|----------|
| 1 | `team/select` 无 membership 校验，造成跨 team 越权读取 | `🔴 blocking` | `apps/api/src/smind_api/routes/team.py:34-38`、`packages/team/src/team/service.py:41-43`、定点复现 | 先修服务层授权，再补 negative tests，随后重新审视 P2/P5/P6 closure |
| 2 | session `expires_at` 不参与鉴权，过期会话仍然有效 | `🔴 blocking` | `packages/auth/src/auth/service.py:47-56`、定点复现 | 在 `validate_session()` 加入 expiry/revocation 校验并补回归 |
| 3 | search 会返回 `archived` 文档，且 `chunk_text` 实际是 hash，不是 hydrated content/snippet | `🔴 blocking` | `packages/rag_vectorizer/src/rag_vectorizer/search.py:22-54`、定点复现 | 重写 post-filter/hydration/result assembly，并补 archived/purged/cross-team tests |
| 4 | P4 contract 漂移：无独立 vectorize stage、无 `constructed_json`、无 `pending_vectorize` 生命周期 | `🔴 blocking` | `packages/workflow_rag/src/workflow_rag/service.py:42-132`、`tests/integration/p4_rag_pipeline/test_rag_pipeline.py:38-55` | 先把 graph/artifact/status 真相层修正，再让 P5/P6 重新站上真实 P4 |
| 5 | `vec.db` 在当前环境实际落成 fallback table，不等于 `docs/refactor/vec.sql` 的 `vec0` | `🟡 structural` | `packages/vector_sqlite_vec/src/vector_sqlite_vec/schema.py:24-59`、定点核验 | 明确 dev/prod schema policy；若接受 fallback，需把 drift 升格为显式版本化合同 |
| 6 | `workflow_events` / `audit_logs` 基本未接线，P6 的 audit/debug surface 失真 | `🟡 structural` | `packages/workflow_core/src/workflow_core/graph.py:9-35`、定点核验 `audit_logs=0` | 把 worker / restart / purge / management 全链路接入事件与审计 |
| 7 | P4/P5/P6 action-plan 的 `## 9 执行日志回填` 仍是 `draft`，但 closure 已宣称 `full-close` | `🟡 structural` | `docs/action-plan/P4.md:532-534`、`P5.md:511-513`、`P6.md:501-503` 对照对应 closure | 回调 closure 口径，并补真实执行日志或下调状态 |
| 8 | P7 只有 grep 级 freeze guard，没有 parity / cutover / rollback 资产 | `🟡 structural` | `tools/scripts/check_legacy_freeze.sh:4-17`、`tests/integration/p7_cutover/test_cutover.py:5-9` | 把 P7 重新拆成 parity、shadow diff、switch、rollback、freeze 五个显式工项 |
| 9 | P0 workspace 仍是脚本式 `pip install -e`，不是 declarative workspace | `🟢 maintenance` | 根 `pyproject.toml`、`tools/scripts/bootstrap.sh:4-27` | 若长期维护该 monorepo，可在后续引入更明确的 workspace / lock 策略 |

---

## 9. Closing statement + 定位裁定

这轮回溯把一个核心事实钉死了：**当前 `smind-family` 不是“P0-P7 已完整收口”的状态，而是“P0-P2 基础闭环成立，P3-P6 有一条可跑的单团队 happy-path，P7 只有 freeze guard 雏形”的状态。**

换句话说，当前仓库最大的价值不是“已经 cutover-ready”，而是**已经提供了足够清晰的修复基座**：目录边界、双库基底、最小 worker、最小 northbound API、最小 processing/search/ops demo 都在，所以下一步不是推倒重来，而是**把 security boundary、RAG/search contract、ops observability、P7 cutover gate 四条主线从 demo 修正到 contract-complete**。

因此，本次复审后的定位裁定是：

1. **不接受**现有 P0-P7 全部 `full-close` 的口径；
2. `P0` 可保留“骨架已成立”的正面结论；
3. `P1-P6` 应统一下调为 **`close-with-known-issues` / `partial`** 的现实状态；
4. `P7` 当前只能被视为 **“legacy freeze 守卫已存在，但 cutover 未开始”**；
5. 后续所有 phase repair，应以本文而不是既有 closure 的乐观结论作为新的 single-truth anchor。

---

## 10. 实现者回应（post-review repair log）

> 回应范围：合并 DeepSeek/GPT/Kimi 三份评审后形成的 unified findings（UF-01 ~ UF-12），逐项完成真实性核查与修复。  
> 回应状态：`all unified findings fixed in this round`

### 10.1 Unified findings 核查结论（去重后）

| UF | 阶段 | 核查结论 | 修复状态 |
|----|------|----------|----------|
| UF-01 | P2 | 真实：密码哈希为无盐 SHA256 | ✅ 已修复（PBKDF2 + legacy 登录升级） |
| UF-02 | P2 | 真实：session 校验未约束 `expires_at` | ✅ 已修复（过期会话拒绝并置 `expired`） |
| UF-03 | P2 | 真实：`/team/select` 缺 membership 校验 | ✅ 已修复（非成员 403） |
| UF-04 | P3 | 真实：clean 未读取 file/url/api 真实 payload | ✅ 已修复（object_store + URL 抓取 + API metadata payload） |
| UF-05 | P4 | 真实：异常路径用错 `step['run_id']` | ✅ 已修复（改为 `workflow_run_id`） |
| UF-06 | P4-P5 | 真实：chunk 文本未持久化，search 返回 hash | ✅ 已修复（chunk_text artifact + hydrate） |
| UF-07 | P5 | 真实：search 未强制 core post-filter/debug 弱 | ✅ 已修复（eligible 强过滤 + debug 明细） |
| UF-08 | P5 | 真实：向量候选阶段未按 team 过滤 | ✅ 已修复（candidate 阶段 team scope） |
| UF-09 | P6 | 真实：restart/purge 时间戳格式漂移 | ✅ 已修复（统一 `now_iso`） |
| UF-10 | P6 | 真实：workflow_events/audit_logs 接线缺失 | ✅ 已修复（claim/retry/leases/restart/purge 全链路接线） |
| UF-11 | P1-P6 | 真实：API deps 重复迁移/连接复用不足 | ✅ 已修复（Depends 注入 + 迁移 ensure 缓存） |
| UF-12 | P2/P6 | 真实：static source_kind 错配 + migration loader 路径依赖 | ✅ 已修复（static 归档为 file + SQL package fallback） |

### 10.2 关键修复落点（代码）

1. **P2 安全与边界**  
`packages/auth/src/auth/service.py`、`packages/team/src/team/service.py`、`apps/api/src/smind_api/routes/team.py`、`apps/api/src/smind_api/deps.py`
2. **P3-P5 数据与检索契约**  
`packages/workflow_clean/src/workflow_clean/service.py`、`packages/cleaners_universal/src/cleaners_universal/service.py`、`packages/workflow_rag/src/workflow_rag/service.py`、`packages/rag_vectorizer/src/rag_vectorizer/search.py`、`packages/vector_sqlite_vec/src/vector_sqlite_vec/store.py`、`apps/api/src/smind_api/routes/search.py`
3. **P6 可观测与运维时序**  
`packages/workflow_core/src/workflow_core/events.py`（新增）+ `claim.py/retry.py/leases.py/restart.py/purge.py`
4. **迁移可移植与 static 契约**  
`packages/storage_sqlite/src/storage_sqlite/migrations/{runner.py,core.sql}`、`packages/vector_sqlite_vec/src/vector_sqlite_vec/{schema.py,vec.sql}`、`packages/ingestion/src/ingestion/service.py`

### 10.3 测试回填（test ↔ fix 完整循环）

新增/增强了 P2~P6 集成断言（成员越权、过期 session、真实 payload、RAG 异常路径、跨 team 检索隔离、ops 审计与时间格式），并完成全量回归：

- `python3 -m ruff check .` → `All checks passed!`
- `python3 -m pytest tests/integration/p2_control_plane tests/integration/p3_clean_pipeline tests/integration/p4_rag_pipeline tests/integration/p5_search_surface tests/integration/p6_operations -q` → `12 passed`
- `python3 -m pytest tests/integration tests/smoke -q` → `20 passed`

### 10.4 收口说明

本次回填针对 unified findings（UF-01~UF-12）已全部关闭；未新增 blocker。后续若要推进 P7 parity/cutover 的完整资产化（shadow diff、rollback drills、default switch），建议作为新一轮独立 action-plan 条目执行。
