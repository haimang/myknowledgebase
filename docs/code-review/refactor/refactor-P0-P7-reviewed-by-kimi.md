# [P0-P7 / smind-family 重构全阶段] Code Review —— Reviewed by Kimi

> 阶段: `P0-P7 — smind-family 重构`
> 范围: `P0-P7 全阶段收口回溯 + 跨阶段跨包深度审查`
> Close-type: `close-with-known-issues`（本审查结论，非原 closure 结论）
> 状态: `reviewed`
> 日期: `2026-05-30` · 作者: `Kimi`
> 关联 charter: `docs/refactor/todo-list.md`
> 关联 design: `docs/refactor/index.md`, `docs/refactor/database.md`
> 关联 action-plan: `docs/action-plan/P0.md` ~ `docs/action-plan/P7.md`
> 关联 evidence: `inline §2`
> 关联 review: `本文档`

---

## 0. 一句话 verdict

> P0-P7 的骨架、workflow kernel、北向 API、clean/rag 执行链、检索面与运维面在**测试层面**已跑通最小闭环，14 个自动化测试全部通过。然而，在**代码契约、数据流完整性、schema 落地度、生产就绪性与命名规范**四个维度上，存在大量已闭合于 closure 但尚未闭合于事实的 gap。最危险的三个结构性缺陷是：**(1) clean 阶段存在数据流断点——未真正读取文件内容与抓取网页；(2) 向量检索退化为全表内存扫描，未使用 sqlite-vec 索引；(3) API 层每次请求都重建数据库连接并重新执行 migration，无连接复用与事务边界控制。**

> **本阶段最关键的 known gap（对下游影响）**：
> 1. `clean_payload` 与 `extract_text` 的输入契约断裂：file/url 的实际内容从未进入 cleaner，clean 产出是虚假的。
> 2. `VectorStore.search` 完全未调用 sqlite-vec 的 KNN 能力，在 vec0 不可用时 fallback 为普通表，但 production 场景下是 O(n) 内存暴力扫描。
> 3. `deps.get_core_conn()` / `deps.get_vec_conn()` 每次调用均创建新连接并重新跑 migration，存在严重的性能与正确性隐患。

---

## 1. 工作项收口表（回溯原始 action-plan 与 closure）

| Item | 原始 closure 状态 | 本审查判定 | 证据 / 判定依据 |
|------|------------------|-----------|----------------|
| P0 仓库骨架与工程命令 | ✅ full-close | 🟡 partial | 目录结构存在，但 `pyproject.toml` target-version (`py312`) 与实际 Python 3.9.6 不符；包命名规范不一致（`smind_common` vs `auth`） |
| P0 API/worker/CLI 最小壳 | ✅ full-close | ✅ verified | `tests/smoke` 通过；`apps/api/src/smind_api/main.py` 存在 FastAPI 实例；`apps/worker` / `apps/cli` 可运行 |
| P1 core.db engine + migration | ✅ full-close | 🟡 partial | `core.sql` 可应用，但 `schema_migrations` 仅记录单条 `"core-0001-ssot"`，无增量迁移机制；`workflow_step_links` / `workflow_events` 等表无任何代码写入 |
| P1 vec.db schema + VectorStore | ✅ full-close | 🟡 partial | `vec.sql` 存在，但 `apply_vec_schema` 在 vec0 不可用时 fallback 为普通表，且 `VectorStore.search` 未使用 sqlite-vec 的 KNN |
| P1 workflow kernel claim/lease/retry | ✅ full-close | 🟡 partial | claim/heartbeat/succeed/fail 通过单元测试，但 `reap_expired_claims` 无事务包裹批量循环；`v_ready_steps` 的并发安全性依赖 SQLite IMMEDIATE，但未验证高并发 |
| P1 restart/purge request 持久化 | ✅ full-close | ✅ verified | `RestartRequestRepository` / `PurgeRequestRepository` 存在且测试通过 |
| P2 auth/team 控制面 | ✅ full-close | 🟡 partial | 注册/登录/team bootstrap 可用，但 `validate_session` 未检查 `expires_at`，session 永不过期；password 使用 SHA256 无 salt，不符合安全规范 |
| P2 file/url/api ingestion | ✅ full-close | 🟡 partial | 三类入口均可创建 source/document/run，但 `file_confirm` 与 `url_submit` / `api_submit` 的数据模型不一致（file 有 upload，url/api 没有） |
| P2 static initiate-confirm | ✅ full-close | ⚠ observed-OK-at-closure | 可创建 `static_files` 记录，但 `static_confirm` 不创建 workflow_run，与 `file_confirm` 行为分叉 |
| P2 management 读面 | ✅ full-close | 🟡 partial | list/detail 可用，但无分页、无关联 steps / chunks / artifacts 查询 |
| P3 clean pipeline 执行 | ✅ full-close | ❌ **missing / broken** | `clean_payload` 对 file 返回 object_key（非内容），对 url 返回 URL 字符串（非网页内容）；clean 产出是虚假的 |
| P3 universal/dedicated/browser runtime | ✅ full-close | 🟡 partial | `browser_runtime/extract.py` 存在但仅做 regex 去标签，未真正抓取网页；`providers_dedicated` 只有 chinatax 硬编码 mock |
| P3 artifact 持久化 + rag handoff | ✅ full-close | ✅ verified | `cleaned_text` artifact 可写入，`rag:structurize` step 可被创建 |
| P4 rag structurize/construct/vectorize | ✅ full-close | 🟡 partial | 链路可跑通，但 `chunks.vec_status` 被直接写入 `vectorized`（跳过 `pending_vectorize`）；`embed_text` 是伪随机哈希向量，非语义嵌入 |
| P4 workflow completed 收口 | ✅ full-close | ✅ verified | `workflow_runs.status` 可被更新为 `completed` |
| P5 search / hydration | ✅ full-close | 🟡 partial | 可返回结果，但 `SearchService.search` 的 `chunk_text` 字段实际返回 `content_hash`，用户看不到内容；`VectorStore.search` 无 `team_id` 过滤 |
| P5 debug 检索视图 | ✅ full-close | 🟡 partial | `/search/debug` 返回结构与 `/search` 几乎相同，无额外调试信息 |
| P6 restart/purge 执行 | ✅ full-close | 🟡 partial | restart 只创建 `clean:init` step，不区分 mode；purge 只支持 `target_kind='document'`，不支持 `workflow_run` / `source` / `chunk` |
| P6 ops API + CLI ops-health | ✅ full-close | 🟡 partial | `/ops/health` 返回基础指标，但无 `vec/core mismatch detector`；CLI `ops-health` 存在 |
| P7 legacy freeze 守卫 | ✅ full-close | 🟡 partial | `check_legacy_freeze.sh` 只检查字符串匹配，未检查运行时导入；无 parity matrix / shadow diff |
| P7 跨阶段总回归 | ✅ full-close | ✅ verified | `14 passed` 通过 |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| 全量测试回归 | `python3 -m pytest tests/integration tests/smoke -v` | `14 passed` | P0-P7 联合 |
| 代码规范 | `python3 -m ruff check .` | `All checks passed` | 全仓 Python |
| clean 数据流断点 | 静态审查 `workflow_clean/service.py:48` + `cleaners_universal/service.py:6` | **确认断裂** | file/url 实际内容未进入 cleaner |
| 向量检索实现 | 静态审查 `vector_sqlite_vec/store.py:91-106` | **确认全表扫描** | 未使用 sqlite-vec KNN |
| API 连接管理 | 静态审查 `smind_api/deps.py:18-29` | **确认每次请求新建连接+ migration** | 性能与正确性隐患 |
| schema 空置表 | `grep -n "CREATE TABLE" docs/refactor/core.sql` vs `grep -rn "INSERT INTO\|UPDATE\|DELETE FROM" packages/` | 大量表无 DML | `configs`, `prompt_versions`, `provider_configs`, `api_keys`, `audit_logs`, `workflow_step_links`, `workflow_events` |

---

## 3. Hard-gate 判定（本审查独立判定）

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| 数据流完整性 gate | clean 阶段必须真正消费输入内容（file 内容 / 网页 HTML / API payload） | file 返回 object_key，url 返回 URL 字符串，未读取实际内容 | ❌ FAIL |
| 向量索引 gate | 向量检索必须使用 sqlite-vec 的 KNN，而非全表内存扫描 | `VectorStore.search` 遍历全部记录做 Python 级余弦计算 | ❌ FAIL |
| 连接管理 gate | API 层不得每次请求重建数据库连接并重新执行 migration | `deps.get_core_conn()` 每次调用均 `connect() + apply_core_migrations()` | ❌ FAIL |
| session 安全 gate | session 必须校验过期时间；password 必须有 salt | `validate_session` 不查 `expires_at`；`_hash(password)` 无 salt | ❌ FAIL |
| schema 落地 gate | `core.sql` 中定义的表必须在业务代码中有读写操作 | 至少 8 张表无任何业务代码写入 | ❌ FAIL |
| 命名规范 gate | packages 的 import 名应保持一致风格 | `smind_common` vs `auth` / `team` / `ingestion` 混用 | ⚠ PARTIAL |
| 测试覆盖 gate | 至少应有 unit + integration + smoke 三层覆盖 | `tests/unit/` 与 `tests/e2e/` 为空 | ⚠ PARTIAL |
| 并发安全 gate | claim 语义在并发 worker 下必须保证唯一性 | `v_ready_steps` + `BEGIN IMMEDIATE` 在单进程内安全，但未验证多进程 | ⚠ PARTIAL |
| 总回归 gate | P0-P7 联合测试通过 | `14 passed` | ✅ PASS |
| 文档收口 gate | closure 文档格式符合模板，且与代码事实一致 | 格式符合，但 evidence 为 working-tree（无 commit SHA） | ⚠ PARTIAL |

---

## 4. Deferred / Carry-over ledger（本审查新增与确认）

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| clean 数据流修复（真正读取 file 内容、抓取网页、消费 API payload） | B | 代码存在但契约断裂 | P3+ 迭代或专项修复 | P3/P4 |
| sqlite-vec KNN 集成（替换 fallback 全表扫描） | B | fallback 机制存在但生产不可用 | P5+ 向量层专项 | P5 |
| API 数据库连接池与事务边界 | B | 每次请求新建连接 | P2+ 控制面专项 | P2 |
| password salt + session 过期校验 | B | 当前 SHA256 无 salt，session 不查 expires_at | P2+ 安全专项 | P2 |
| schema 空置表收敛（configs / prompt_versions / provider_configs / api_keys / audit_logs / workflow_step_links / workflow_events） | B | 表已定义但无业务代码 | P6/P7 运维与观测专项 | P6-P7 |
| 命名规范统一（smind_* 前缀或全部统一） | B | 当前混用 | P0+ 工程约定迭代 | P0 |
| unit / e2e 测试补全 | B | 目录为空 | 后续质量门禁迭代 | Future |
| purge 多 target_kind 支持（workflow_run / source / chunk） | B | 当前仅支持 document | P6+ 运维专项 | P6 |
| restart mode 语义实现（kickstart / recovery / force_recovery / force_kickstart） | B | 当前不区分 mode | P6+ 运维专项 | P6 |
| parity matrix / shadow diff / golden fixture | B | 未实现 | P7+ cutover 质量专项 | P7 |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred）| ✅（本审查已逐条归类） |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | ⚠（原 closure 全部为 working-tree，无 commit SHA；本审查基于静态代码分析 + 测试运行，run-time 为 `2026-05-30`） |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改）| N/A（本审查为只读审查，未修改代码） |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ |
| owner-test 项未经 owner 复测的标 ⏸ PENDING（无「我修了」式宣称）| N/A |

---

## 6. Handoff / 下阶段 entry-gate 预核对

| 入口条件 | 状态 | 备注 |
|----------|------|------|
| clean 数据流修复：file 内容 / 网页 HTML / API payload 真正进入 cleaner | ❌ | 当前断裂，必须先修复 |
| sqlite-vec KNN 真正启用，或明确生产环境的向量引擎选型 | ⏸ | fallback 全表扫描不可用于生产 |
| API 层数据库连接复用（connection pool / per-request 单连接 / 依赖注入优化） | ⏸ | 当前每次请求新建连接并跑 migration |
| session 安全加固（password salt + expires_at 校验 + token rotation） | ⏸ | 当前存在安全缺口 |
| schema 空置表决策：删除未使用表，或补全业务代码 | ⏸ | 当前 8+ 张表无业务写入 |
| unit / e2e 测试基线建立 | ⏸ | 当前为空目录 |

---

## 7. Cross-cut 不变量（0-drift 确认）

| 不变量 | 状态 | 证据 |
|--------|------|------|
| `core.db` 与 `vec.db` 职责分离 | ✅ 保持 | `core.sql` / `vec.sql` 边界清晰；业务代码未混用 |
| `workflow_steps.status` 状态枚举 | ✅ 保持 | `pending/running/succeeded/failed/retry_wait/cancelled/skipped` 与 `core.sql:251-262` 一致 |
| `chunks.vec_status` 状态枚举 | ⚠ 部分保持 | `core.sql` 定义 `pending_vectorize/vectorized/pending_purge/purged/failed`，但代码中直接写入 `vectorized`（跳过 `pending_vectorize`） |
| `apps/` 只承载入口，`packages/` 承载业务 | ✅ 保持 | 目录结构符合 `docs/refactor/index.md:6.3` |
| `legacy-family/` 只读约束 | ✅ 保持 | `check_legacy_freeze.sh` 通过；无运行时导入 |
| 包间依赖方向：apps -> packages，packages 不反向依赖 apps | ✅ 保持 | 静态审查未发现有 packages 导入 apps |
| `task_claims` 与 `workflow_steps` 分离 | ✅ 保持 | `claimed_by` / `lease_expires_at` 未出现在 `workflow_steps` 中，符合 `index.md:4.4` |

---

## 8. 价值 / 负债台账

**价值台账**

| 章节 | 真实价值 | 状态 |
|------|----------|------|
| P0 骨架 | monorepo 结构、workspace、lint/test 脚本、三入口壳 | ✅ 可用 |
| P1 内核 | `core.db` / `vec.db` schema、migration runner、claim/lease/retry 状态机 | 🟡 骨架可用，关键实现有 gap |
| P2 控制面 | auth/team/ingestion/management API 存在，可创建 source/document/run | 🟡 表面可用，安全与性能有 gap |
| P3 Clean | clean step 可被 worker 消费，artifact 可写入，rag step 可被创建 | ❌ 数据流断裂，clean 产出虚假 |
| P4 RAG | structurize -> construct -> vectorize 链可跑通，workflow 可 completed | 🟡 链路可跑通，但 embedding 是伪随机，状态推进不规范 |
| P5 检索 | search / debug API 可返回命中结果 | 🟡 可返回结果，但 chunk_text 是 content_hash，检索未用索引 |
| P6 运维 | restart/purge/health API 与 CLI 存在 | 🟡 存在但功能不完整（mode 不区分，purge target 单一） |
| P7 收敛 | legacy freeze 守卫脚本、跨阶段回归通过 | 🟡 回归通过，但无 parity matrix |

**负债台账**

| # | 负债 | 级别 | 来源 | 消化路径 |
|---|------|------|------|----------|
| 1 | clean 数据流断裂：未真正读取输入内容 | 🔴 blocking | P3 实现 | 修复 `workflow_clean._load_raw_payload` 与 `cleaners_universal.clean_payload`，引入 object store 读取与 HTTP 抓取 |
| 2 | 向量检索退化为全表内存扫描 | 🔴 blocking | P4/P5 实现 | 移除 vec0 fallback 的默认启用，或确保生产环境安装 sqlite-vec 并改用 KNN SQL |
| 3 | API 每次请求新建连接并重新 migration | 🔴 blocking | P2 实现 | 引入连接池或 FastAPI 依赖注入单连接模式；分离 migration 启动时一次性执行 |
| 4 | password 无 salt、session 不校验过期 | 🔴 blocking | P2 实现 | 引入 bcrypt/argon2；在 `validate_session` 中检查 `expires_at` |
| 5 | schema 中 8+ 张表无业务代码写入 | 🟡 structural | P1-P6 实现 | 逐张决策：删除未使用表，或补全业务代码（configs / prompt_versions / provider_configs / api_keys / audit_logs / workflow_step_links / workflow_events） |
| 6 | `chunks.vec_status` 直接写入 `vectorized`，跳过 `pending_vectorize` | 🟡 structural | P4 实现 | 在 `process_rag_step` 中先写 `pending_vectorize`，向量 upsert 成功后再更新为 `vectorized` |
| 7 | 包命名规范不一致 | 🟢 maintenance | P0 实现 | 统一为 `smind_*` 前缀或全部裸名 |
| 8 | unit / e2e 测试缺失 | 🟢 maintenance | P0-P7 实现 | 补充分层测试 |
| 9 | `/search` 返回的 `chunk_text` 实际是 `content_hash` | 🟡 structural | P5 实现 | 修改 `SearchService.search` 的 hydration 逻辑，返回实际文本片段（需从 artifact 或 chunk 表中取） |
| 10 | `workflow_events` / `audit_logs` 无任何写入 | 🟡 structural | P1/P6 实现 | 在 claim / succeed / fail / restart / purge 等关键路径插入事件与审计记录 |
| 11 | `SearchService.search` 的 `chunk_text` 返回 `content_hash` 而非文本 | 🟡 structural | P5 实现 | 需要从 artifacts 或 object store 中读取实际文本 |
| 12 | `embedding` 维度检查不一致：`vec.sql` 强制 1536，但 `VectorStore.upsert_chunk` 接受任意长度 | 🟡 structural | P4 实现 | 在 upsert 时检查 `len(embedding) == 1536`，或与 schema 动态对齐 |
| 13 | `process_purge_requests` 异常时无回滚，可能导致 chunks 状态为 `pending_purge` 但向量未删除 | 🟡 structural | P6 实现 | 使用事务包裹整个 purge 处理逻辑，或增加补偿机制 |
| 14 | `reap_expired_claims` 循环内逐条 commit，无批量事务 | 🟡 structural | P1 实现 | 在循环开始前 `BEGIN`，循环结束后 `COMMIT` |
| 15 | `ingestion` 中 `url_submit` / `api_submit` 与 `file_confirm` 的数据模型不一致 | 🟡 structural | P2 实现 | 统一 url/api 也走 upload 表，或明确文档化差异 |

---

## 9. Closing statement + 定位裁定

### 9.1 总体裁定

P0-P7 的 closure 文件将每个阶段标记为 `full-close`，其依据是**测试通过 + 代码存在 + 接口可调用**。然而，一份诚实的 code review 必须区分「接口存在」与「契约正确」、「测试通过」与「数据流完整」、「骨架搭好」与「生产就绪」。

本次审查的裁定是：**P0-P7 在「接口与测试层面」完成了最小闭环，但在「数据流完整性、生产性能、安全规范、schema 落地度」四个维度上存在显著 gap。其中 P3（clean 数据流断裂）与 P5（向量检索退化）是最危险的两个盲点，它们使得当前代码无法直接承担生产职责。**

### 9.2 按阶段详细分析

#### P0 — 基础骨架

**正面**：monorepo 结构清晰，`apps/` / `packages/` / `tests/` / `tools/` / `data/` 全部存在；`bootstrap.sh` 与 `smoke.sh` 可用；三入口壳可启动。

**负面**：
1. `pyproject.toml` 中 `target-version = "py312"` 与实际运行环境 Python 3.9.6 不符。虽然代码中没有使用 3.12 特有语法，但这一配置会导致 ruff 不会检查 3.9 兼容性（如 `list[str]` 在 3.9 需要 `from __future__ import annotations` 或 `typing.List`）。幸运的是现有代码大多使用了 `from __future__ import annotations`。
2. 包命名规范不一致：`packages/common/src/smind_common` 使用 `smind_` 前缀，而 `packages/auth/src/auth` 使用裸名。虽然 import 时功能正常，但这违背了 P0「定义长期边界」的目标。
3. `tests/unit/` 与 `tests/e2e/` 为空目录，P0 closure 中未提及此缺口。

#### P1 — 数据库与状态内核

**正面**：`core.sql` / `vec.sql` 作为 SSOT 落盘；migration runner 具备单次执行保护；`WorkflowScheduler` / `claim_next_step` / `heartbeat_claim` / `succeed_claim` / `fail_claim` / `reap_expired_claims` 构成了可运行的状态机；integration test 验证了 claim -> heartbeat -> fail -> retry -> succeed 的完整链路。

**负面**：
1. **`schema 落地度严重不足`**：`core.sql` 中定义了 22 张表，但业务代码实际读写的表约 14 张。以下表在全部 P0-P7 代码中**没有任何写入操作**：`configs`, `prompt_versions`, `provider_configs`, `api_keys`, `audit_logs`, `workflow_step_links`, `workflow_events`。`workflow_events` 虽然 `graph.py` 中有一个 `write_workflow_event` 函数，但没有任何调用方。这意味着 P1 的 schema 设计「过于超前」，大量表处于「schema 漂移」状态——它们存在于 DDL，但不存在于 DML。
2. **`reap_expired_claims` 的事务边界缺陷**：该函数遍历每个过期 claim，对每个 claim 执行 `UPDATE task_claims` + `INSERT OR REPLACE INTO step_attempts` + `UPDATE workflow_steps`，最后一次性 `conn.commit()`。如果循环中途抛出异常，已经处理的部分会被 commit，未处理的部分不会回滚，导致状态不一致。正确的做法是在循环开始前 `BEGIN`，循环结束后 `COMMIT`，或在每次迭代内使用独立事务并记录已处理 ID。
3. **`step_attempts` 的 `INSERT OR REPLACE` 隐患**：`succeed_claim` 和 `fail_claim` 都使用 `INSERT OR REPLACE INTO step_attempts`，其主键是 `f"attempt_{claim['id']}"`（基于 claim_id）。如果同一个 claim 被错误地调用两次 succeed，第二次会覆盖第一次的记录，导致 attempt 历史丢失。应使用 `INSERT OR IGNORE` 或显式主键冲突处理。
4. **`task_claims` 的 `UNIQUE (step_id) WHERE status = 'active'` 部分索引**（`ux_task_claims_active_step`）设计正确，但 `claim_next_step` 中虽然使用了 `BEGIN IMMEDIATE`，其 `v_ready_steps` 的 `NOT EXISTS (SELECT 1 FROM task_claims WHERE step_id = ws.id AND status = 'active')` 检查与 `UPDATE workflow_steps` + `INSERT INTO task_claims` 之间存在理论上的竞态窗口（虽然 SQLite 的 IMMEDIATE 事务在单进程中是串行的）。
5. **`common` 与 `workflow_core._utils` 的 `new_id` 重复**：`smind_common.ids.new_id` 与 `workflow_core._utils.new_id` 功能完全一致，都是 `f"{prefix}_{uuid4().hex}"`。这违反了 DRY 原则。

#### P2 — 控制面与 ingestion

**正面**：auth / team / ingestion / management 的 API 路由全部存在；file / url / api / static 四类入口均可调用；management 的 list/detail 可用；FastAPI 的 `TestClient` 集成测试通过。

**负面**：
1. **`deps.get_core_conn()` 每次请求重建连接并重新执行 migration**：这是本阶段最严重的性能与正确性隐患。`get_core_conn()` 在每次调用时都会 `CoreSQLiteEngine(settings.core_db_path).connect()` 并 `apply_core_migrations(conn)`。在 FastAPI 的一个请求中，如果 router 调用 `get_core_conn()` 一次，service 中又调用一次，就会产生两个独立连接。SQLite 在 WAL 模式下支持多连接，但 `apply_core_migrations` 会读取文件并执行 `executescript`，这在高并发下会导致严重的 I/O 竞争。更严重的是，如果 API 层和 worker 层同时执行 migration，可能产生冲突。
2. **`AuthService` 的安全缺口**：
   - `register` 使用 `hashlib.sha256(password).hexdigest()`，**无 salt**。这意味着相同密码的哈希值相同，极易受到彩虹表攻击。
   - `validate_session` **不检查 `expires_at`**。只要 session 的 `status='active'`，就永远视为有效，即使用户注销或 token 已过期。
   - `login` 返回的 token 没有过期时间信息，客户端无法知道何时需要重新登录。
3. **`ingestion` 数据模型不一致**：`file_confirm` 会创建 `uploads` 记录并将其状态更新为 `confirmed`，然后创建 `source` / `document` / `workflow_run`。但 `url_submit` 和 `api_submit` 直接创建 `source` / `document` / `workflow_run`，**不创建 `uploads` 记录**。这导致 management 面的 list 逻辑无法统一处理所有 source 类型（例如，无法从 url source 回溯到 upload）。
4. **`static_confirm` 与 `file_confirm` 行为分叉**：`static_confirm` 不创建 `workflow_run`，只创建 `static_files` 记录。这与 `file_confirm` 的行为不一致，且 closure 中声称 "static initiate-confirm 可落 `static_files` 且不自动跑 run"，这虽然是一个设计决策，但应在文档中明确说明 static 文件不参与 workflow。
5. **API 设计缺口**：所有 list API 均无分页参数（limit/offset）；所有 API 均无 OpenAPI `response_model`，前端无法自动生成类型；`/management/workflows/{id}` 不返回关联的 steps；`/management/documents/{id}` 不返回关联的 chunks。

#### P3 — Clean Pipeline

**正面**：`workflow_clean.service.process_clean_step` 可被 worker 调用；成功后会创建 `cleaned_text` artifact 和下游 `rag:structurize` step；`cleaners_universal` 与 `providers_dedicated` 的 registry 模式已建立。

**负面**：
1. **clean 数据流断裂（本审查最严重的发现之一）**：
   - 对于 `file` 类型：`workflow_clean.service._load_raw_payload` 返回的是 `uploads.object_key`（文件路径字符串），而不是文件内容。`cleaners_universal.clean_payload` 对 `file` 类型直接返回 `payload.strip()`，即返回 object_key 本身。这意味着 `cleaned_text` artifact 中存储的 `"text"` 实际上是文件路径，而非文件内容。
   - 对于 `url` 类型：`_load_raw_payload` 返回的是 `sources.source_uri`（URL 字符串）。`cleaners_universal.clean_payload` 对 `url` 类型调用 `browser_runtime.extract_text(payload)`，而 `extract_text` 使用正则表达式移除 HTML 标签。但输入是 `"https://example.com"` 这样的 URL 字符串，不是 HTML 内容，所以 `extract_text` 只是对 URL 字符串做无意义的标签移除，返回的仍是 URL 字符串。
   - 对于 `api` 类型：与 `url` 类似，返回的是 `external_ref` 或 payload 的字符串表示，而非需要清洗的原始内容。
   - **结论**：`cleaned_text` artifact 中存储的文本**从未真正经过清洗**。整个 clean pipeline 只是在搬运 metadata，没有执行任何实质性的内容清洗。这是一个**数据流断点**。
2. **`providers_dedicated` 的 mock 化**：`maybe_clean_with_provider` 只在 URL 包含 `"chinatax.gov.cn"` 时返回一个带 marker 的字符串，否则返回 `None`。这是极窄的硬编码，没有真正的 provider adapter 抽象。
3. **`browser_runtime` 的虚假性**：`extract_text` 只是一个正则表达式 HTML tag stripper，没有使用 Playwright 或任何真正的浏览器运行时。这与 action-plan 中提到的 "Playwright runner" 严重不符。
4. **`process_clean_step` 的 step 状态管理**：该函数在内部直接 `UPDATE workflow_steps SET status='succeeded'` 并创建下游 step，而不是通过 `workflow_core` 的 `succeed_claim` 来统一处理。虽然当前 worker 的调用链中 `process_clean_step` 是在 `succeed_claim` 之前被调用的（`worker/main.py:44-51`），但如果在 `process_clean_step` 内部抛出异常，`worker/main.py` 的 `except` 块会调用 `fail_claim`，此时 step 状态会被 `fail_claim` 覆盖为 `failed`。这看似正确，但 `process_clean_step` 内部已经修改了 step 状态为 `succeeded` 并 commit，如果后续抛出异常（例如创建下游 step 时），状态已经不可逆地变为 `succeeded`。实际上 `process_clean_step` 的代码顺序是：先 INSERT artifact + INSERT downstream step + UPDATE current step succeeded + commit，所以如果在 INSERT 阶段失败，不会到达 UPDATE。但如果 commit 后、worker 的 `succeed_claim` 之前发生进程崩溃，step 状态在数据库中已经是 `succeeded`，但 `task_claims` 仍然是 `active`，这会导致 `reap_expired_claims` 无法回收这个 claim（因为 step 已经是 succeeded）。这是一个边界情况。

#### P4 — RAG Pipeline

**正面**：`process_rag_step` 可处理 `rag:structurize` 和 `rag:construct` 两个阶段；structurizer -> constructor -> vectorizer 的链路可跑通；`workflow_runs` 可被标记为 `completed`；`chunks` 可被写入 `core.db`；`vec.db` 可被写入。

**负面**：
1. **`chunks.vec_status` 状态推进不规范**：`process_rag_step` 在 `rag:construct` 阶段直接 `INSERT INTO chunks(..., vec_status, ...) VALUES (..., 'vectorized', ...)`，**跳过了 `pending_vectorize` 状态**。这与 `docs/refactor/todo-list.md` 中明确要求的 "`chunks.vec_status` 能从 `pending_vectorize` 进入 `vectorized`" 不符，也违背了 `database.md` 中定义的状态机语义。
2. **`embed_text` 是伪随机哈希向量**：`rag_vectorizer.embedder.embed_text` 使用 SHA256 哈希的 digest 生成伪随机浮点数。这**不是语义嵌入**，对任意文本生成的向量之间没有语义相似性。测试中的 search 能够通过是因为所有向量都是伪随机的，但查询向量与被查询向量在统计上可能产生偶然的相似度。这在生产环境中完全不可接受。
3. **`chunks` 表的 `UNIQUE (document_id, content_hash)` 冲突风险**：`process_rag_step` 为每个 chunk 生成 `content_hash = sha256(text.encode("utf-8")).hexdigest()`，然后 INSERT INTO chunks。如果同一个 document 的两次 run 产生相同文本的 chunk（例如 restart 后重新运行），这个 UNIQUE 约束会触发 `IntegrityError`，但代码中没有 `ON CONFLICT` 处理。
4. **`SearchService` 的 `chunk_text` 字段返回 `content_hash`**：`SearchService.search` 在 hydration 时从 `v_search_hydration` 取数据，但返回给用户的 `chunk_text` 字段被赋值为 `row["content_hash"]`。这意味着用户调用 `/search` 看到的 "chunk_text" 实际上是一个 SHA256 哈希字符串，**不是文本内容**。这是一个严重的 API 契约错误。
5. **向量写入与 core.db 状态的原子性**：`process_rag_step` 中先 `INSERT INTO chunks`（core.db），然后 `vector_store.upsert_chunk`（vec.db），然后 UPDATE documents / workflow_runs。如果 `upsert_chunk` 失败，core.db 中已插入的 chunk 记录不会自动回滚（因为不在同一数据库事务中）。这与 `database.md` 中"通过工作流状态机保证一致性，而不是跨库事务"的原则一致，但当前实现中如果向量写入失败，chunk 记录会残留且 `vec_status='vectorized'`，这需要 retry / purge 来纠正，但代码中没有对这种失败场景做显式处理。

#### P5 — 检索与查询面

**正面**：`/search` 与 `/search/debug` API 存在；`SearchService` 可从 query 生成 embedding 并返回 hydrated 结果；P5 集成测试通过。

**负面**：
1. **`VectorStore.search` 完全未使用 sqlite-vec 的 KNN**：`VectorStore.search` 的执行逻辑是 `SELECT vr.chunk_id, cei.embedding FROM vector_records vr JOIN chunk_embedding_index cei ... WHERE vr.deleted_at IS NULL`，然后在 Python 内存中遍历所有行，计算余弦相似度，排序后取 top-k。这是**O(n) 的全表扫描 + 内存暴力计算**。即使 `chunk_embedding_index` 是 sqlite-vec 的虚拟表，查询也没有使用 `vec0` 的 KNN 语法（如 `SELECT rowid, distance FROM chunk_embedding_index WHERE embedding MATCH ? AND k = ?`）。当 vec0 不可用时，fallback 机制将虚拟表替换为普通表，这进一步丧失了向量索引能力。
2. **`VectorStore.search` 无 `team_id` / `namespace_id` 过滤**：查询中没有 `WHERE team_id = ?` 或 `WHERE namespace_id = ?`，这意味着跨 team 的向量会被一起扫描。虽然 `SearchService` 在 hydration 阶段会按 `team_id` 过滤，但如果在扫描阶段就限制范围，可以显著减少计算量。
3. **`/search/debug` 无额外调试信息**：`search_debug` 路由与 `search` 路由返回几乎相同的数据结构，只是多包了一层 `{"query": ..., "count": ..., "items": ...}`。没有返回 embedding 维度、检索耗时、命中的 namespace、过滤条件等真正的 debug 信息。
4. **search 结果缺少实际文本**：如前所述，`chunk_text` 返回的是 `content_hash`，用户无法阅读搜索结果。

#### P6 — 运维与恢复能力

**正面**：`/ops/restarts` 与 `/ops/purges` API 存在；`process_restart_requests` 与 `process_purge_requests` 可被 worker 调用；`/ops/health` 可返回 stale_claims / restart_backlog / purge_backlog / pending_purge_chunks 指标。

**负面**：
1. **`restart` 不区分 mode**：`restart_requests` 的 `mode` 字段支持 `kickstart/recovery/force_recovery/force_kickstart`，但 `process_restart_requests` 对任何 mode 都统一创建一个 `clean:init` step。这与 action-plan 中要求的 "recovery / force recovery / kickstart 模式" 不符。
2. **`purge` 只支持 `target_kind='document'`**：`process_purge_requests` 在遇到非 `document` 的 target_kind 时直接标记为 failed。但 schema 中 `purge_requests.target_kind` 的 CHECK 约束包含 `workflow_run/document/source/chunk`，action-plan 也要求支持多类型。
3. **`purge` 的异常处理缺陷**：`process_purge_requests` 对每个 request 的处理流程是：UPDATE -> SELECT chunks -> UPDATE chunks pending_purge -> VectorStore.delete_chunks -> UPDATE chunks purged -> UPDATE documents purged -> UPDATE purge_requests completed -> commit。如果 `VectorStore.delete_chunks` 抛出异常（例如 vec.db 连接断开），整个 `process_purge_requests` 会中断，且由于异常发生在循环内部，已经处理的前面几个 request 的 `UPDATE ... processing` 不会被回滚（因为 SQLite 默认 autocommit 模式下每个 statement 是一个事务，但代码中在最后才 `conn.commit()`，所以如果异常发生在 commit 之前，所有未 commit 的更改会回滚——这是正确的。但如果异常发生在 `conn.commit()` 之后呢？实际上代码结构是循环内逐个处理，最后统一 `conn.commit()`，所以如果循环中途异常，当前 request 的部分更新不会 commit。但问题是：在异常之前已经处理的 request，其状态仍然是 `processing`（因为还没 commit），这会导致这些 request 在下次 worker 循环中被重新处理。这是幂等的，但效率低下。更严重的场景是：如果 `VectorStore.delete_chunks` 内部已经执行了 `self.conn.commit()`（它确实会 commit vec_conn），那么 vec.db 的删除已经持久化，但 core.db 的 `UPDATE chunks SET vec_status='purged'` 没有 commit，导致 core.db 与 vec.db 状态不一致。）
4. **`ManagementService.restart_workflow` 与 `purge_document` 同步执行**：在 API 层调用 restart/purge 后，直接同步调用 `process_restart_requests` / `process_purge_requests`，而不是将其放入 backlog 由 worker 异步处理。这虽然简化了实现，但违背了 P1-P6 建立的 "request backlog + worker 消费" 的异步模型。
5. **health 指标缺失**：`collect_health` 只返回了 4 个计数指标，但 action-plan 中要求的 "vec/core mismatch detector" 未实现。

#### P7 — 收敛与替换

**正面**：`check_legacy_freeze.sh` 脚本存在且通过测试；P0-P7 联合回归 14 个测试全部通过；legacy-family 目录未被修改。

**负面**：
1. **`check_legacy_freeze.sh` 过于宽松**：该脚本只检查 `rg 'legacy[-_]family|legacy-family/'` 是否在 `apps packages tests tools` 中出现。这只能发现显式的字符串引用，无法发现通过 Python import 或 symlink 引入的 legacy 代码依赖。例如，如果某个 package 的 `pyproject.toml` 依赖了 legacy 的 path，该脚本无法检测。
2. **无 parity matrix / shadow diff**：P7 action-plan 明确要求 "对照 legacy-family 校验产出结构"、"做端到端回归"、"golden fixture 与 shadow diff"。当前没有任何自动化测试比较新实现与 legacy 的产出差异。
3. **无 cutover 文档**：P7 的 closure 声称 "cutover guard 已落地"，但除了 `check_legacy_freeze.sh` 和回归测试外，没有看到明确的 cutover runbook、回滚策略或 shadow deployment 计划。

### 9.3 跨阶段跨包深度分析

#### API Surface 一致性审查

| API 端点 | 请求契约 | 响应契约 | 与代码实现匹配度 |
|----------|---------|---------|----------------|
| `POST /auth/register` | `email`, `password`, `display_name` | `{"user_id": str}` | ✅ 匹配 |
| `POST /auth/login` | `email`, `password` | `{"token": str}` | ✅ 匹配，但无过期时间 |
| `POST /team/bootstrap` | `name`, `slug` | `{"team_id": str}` | ✅ 匹配，且自动 select team |
| `POST /ingestion/file/initiate` | `filename`, `mime_type` | `{"upload_id": str, "object_key": str}` | ✅ 匹配 |
| `POST /ingestion/file/confirm` | `upload_id`, `title`, `content` | `{"source_id": str, "document_id": str, "workflow_run_id": str}` | ✅ 匹配 |
| `POST /ingestion/url/submit` | `url`, `title` | `{"source_id": str, "document_id": str, "workflow_run_id": str}` | ✅ 匹配 |
| `POST /ingestion/api/submit` | `external_ref`, `title`, `payload` | 同 url | ✅ 匹配 |
| `POST /ingestion/static/initiate` | 同 file | 同 file | ✅ 匹配 |
| `POST /ingestion/static/confirm` | `upload_id`, `path`, `content`, `role` | `{"static_file_id": str, ...}` | ✅ 匹配，但 **不返回 workflow_run_id** |
| `GET /management/workflows` | — | `{"items": [...]}` | ✅ 匹配，无分页 |
| `GET /management/workflows/{id}` | — | `{"item": {...}}` | ✅ 匹配，不返回 steps |
| `GET /management/documents` | — | `{"items": [...]}` | ✅ 匹配，无分页 |
| `GET /management/documents/{id}` | — | `{"item": {...}}` | ✅ 匹配，不返回 chunks |
| `POST /search` | `query`, `limit` | `{"items": [{chunk_id, document_id, title, canonical_uri, chunk_text, score}]}` | ❌ **不匹配**：`chunk_text` 实际是 `content_hash` |
| `POST /search/debug` | 同 search | `{"query": str, "count": int, "items": [...]}` | 🟡 匹配，但无额外 debug 信息 |
| `GET /ops/health` | — | `{"item": {stale_claims, restart_backlog, purge_backlog, pending_purge_chunks}}` | ✅ 匹配 |
| `POST /ops/restarts` | `workflow_run_id`, `mode` | `{"request_id": str}` | ✅ 匹配，但 mode 不生效 |
| `POST /ops/purges` | `document_id` | `{"request_id": str}` | ✅ 匹配，但只支持 document |

#### 测试用例核实

| 测试文件 | 测试内容 | 是否与代码实现正确匹配 | 问题 |
|----------|---------|---------------------|------|
| `test_kernel_flow.py` | claim/heartbeat/succeed/fail/retry/reclaim | ✅ | 未覆盖并发场景 |
| `test_requests_and_vec.py` | restart/purge request 持久化；vec upsert/delete | ✅ | `test_vec_store_upsert_and_delete` 中 embedding 长度为 8，与 schema 的 1536 不符 |
| `test_ingestion_management.py` | auth/team/ingestion/management 集成 | ✅ | 未覆盖错误场景（如重复注册、过期 session） |
| `test_clean_pipeline.py` | clean artifact + rag step 创建 | 🟡 | 只检查存在性，未检查 `cleaned_text` 内容 |
| `test_rag_pipeline.py` | workflow completed + chunk vectorized | 🟡 | 未验证向量可被 search 检索 |
| `test_search.py` | search/debug 返回结果 | 🟡 | 未验证 `chunk_text` 是否为真实文本 |
| `test_operations.py` | restart/purge/health | 🟡 | 未验证 restart mode 语义、purge 后 document status |
| `test_cutover.py` | legacy freeze 字符串检查 | 🟡 | 过于简单 |
| `test_api_smoke.py` | `/healthz` | ✅ | — |
| `test_worker_smoke.py` | worker 进程启动 | 🟡 | 未验证 step 处理 |
| `test_cli_smoke.py` | CLI `--help` | ✅ | — |
| `test_shared_imports_smoke.py` | 公共包 import | ✅ | — |

#### SQLite 表结构符合性（Schema Drift）

| 表名 | schema 定义 | 代码中是否有读写 | 是否符合要求 |
|------|------------|----------------|-------------|
| `users` | ✅ 完整 | ✅ 读写 | 符合 |
| `teams` | ✅ 完整 | ✅ 读写 | 符合 |
| `team_members` | ✅ 完整 | ✅ 读写 | 符合 |
| `api_keys` | ✅ 完整 | ❌ **无任何代码写入** | **Drift** |
| `sessions` | ✅ 完整 | ✅ 读写 | 符合（但未校验过期） |
| `uploads` | ✅ 完整 | ✅ 读写 | 符合（但 `uploaded` 状态未使用） |
| `sources` | ✅ 完整 | ✅ 读写 | 符合 |
| `documents` | ✅ 完整 | ✅ 读写 | 符合（但 `latest_*_artifact_id` 等字段未更新） |
| `static_files` | ✅ 完整 | ✅ 读写 | 符合 |
| `workflow_runs` | ✅ 完整 | ✅ 读写 | 符合 |
| `artifacts` | ✅ 完整 | ✅ 读写 | 符合 |
| `chunks` | ✅ 完整 | ✅ 读写 | 符合（但 `vec_status` 推进不规范） |
| `workflow_steps` | ✅ 完整 | ✅ 读写 | 符合 |
| `task_claims` | ✅ 完整 | ✅ 读写 | 符合 |
| `step_attempts` | ✅ 完整 | ✅ 读写 | 符合（但 `INSERT OR REPLACE` 有隐患） |
| `workflow_step_links` | ✅ 完整 | ❌ **无任何代码写入** | **Drift** |
| `workflow_events` | ✅ 完整 | ❌ **无任何代码写入**（函数存在但未被调用） | **Drift** |
| `configs` | ✅ 完整 | ❌ **无任何代码写入** | **Drift** |
| `prompt_versions` | ✅ 完整 | ❌ **无任何代码写入** | **Drift** |
| `provider_configs` | ✅ 完整 | ❌ **无任何代码写入** | **Drift** |
| `restart_requests` | ✅ 完整 | ✅ 读写 | 符合 |
| `purge_requests` | ✅ 完整 | ✅ 读写 | 符合 |
| `audit_logs` | ✅ 完整 | ❌ **无任何代码写入** | **Drift** |

**总结**：22 张表中，**8 张表**在全部业务代码中没有任何写入操作，存在严重的 schema drift。这违背了 P1 "先落 schema 再迁业务" 的原则——schema 超前于业务实现，导致大量"死表"存在。

#### 命名规范与执行逻辑错误

1. **命名不一致**：
   - `packages/common/src/smind_common` vs `packages/auth/src/auth`：前者带 `smind_` 前缀，后者不带。
   - `apps/api/src/smind_api` vs `packages/auth/src/auth`：apps 统一使用 `smind_` 前缀，但 packages 中约一半使用裸名。
   - 建议：统一规范，全部使用 `smind_` 前缀或全部使用裸名（但裸名容易与 PyPI 上的公共包冲突）。

2. **执行逻辑错误**：
   - `ingestion/service.py:33`：`static_initiate` 调用 `file_initiate` 后，将 upload 的 `source_kind` 更新为 `'api'`。这是错误的：`static_files` 在 schema 中通过 `source_id` 关联到 `sources`，而 `sources.source_kind` 的 CHECK 约束是 `('file', 'url', 'api')`，没有 `'static'`。因此 static 文件被归类为 `'api'` source。这是一个分类错误。
   - `workflow_rag/service.py:40`：代码在 `run` 为 `None` 时引用 `step["run_id"]`，但 `workflow_steps` 表中实际列名为 `workflow_run_id`，不存在 `run_id` 列。`sqlite3.Row` 对不存在的列名会抛出 `IndexError`。当前因外键约束存在，`run` 不会为 `None`，该路径不会触发；但属于**死代码中的 bug**，一旦数据不一致或外键检查关闭即会暴露。

3. **类型注解不一致**：
   - `pyproject.toml` 的 `target-version = "py312"` 与 `requires-python = ">=3.9"` 不一致。
   - `common/src/smind_common/time.py` 的 `utc_now_iso` 返回 `str`，但 `workflow_core._utils.now_iso` 的格式略有不同（前者用 `.isoformat()`，后者用 `strftime("%Y-%m-%dT%H:%M:%fZ")`）。两者都合法，但不统一。

4. **缺失的 error handling**：
   - 所有 API 路由都没有 try/except 块，异常会直接抛出为 500 Internal Server Error。
   - `ingestion/service.py` 的 `file_confirm` 在 `upload` 不存在时抛出 `ValueError`，但 API 层没有将其转换为 404。

### 9.4 真实存在的盲点与断点

1. **盲点：clean 阶段未真正处理内容**。测试只验证 artifact 存在，未验证内容正确性。这是测试设计的盲点。
2. **盲点：schema 空置表**。22 张表中有 8 张死表，但 closure 中没有任何一项提及此问题。
3. **断点：file/url 内容到 cleaner 的数据流**。`_load_raw_payload` 返回 object_key / URL 字符串，而非内容；`clean_payload` 接收这些字符串并直接返回，未调用 object store 的 `get_text` 或 HTTP client 的 `fetch`。
4. **断点：sqlite-vec KNN 到 SearchService 的调用链**。`VectorStore.search` 未使用 `vec0` 的 KNN SQL，导致向量索引层完全失效。
5. **断点：API 连接管理**。`deps.get_core_conn()` 的每次请求新建连接模式，在并发场景下会迅速耗尽文件描述符并导致性能崩溃。

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| `r1` | `2026-05-30` | `Kimi` | 初版审查：P0-P7 全阶段回溯 + 跨阶段跨包深度分析 |
