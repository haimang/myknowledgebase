# smind-family Database Design Specification

## 0. 文档定位

本文定义 `smind-family` 重构后的完整数据库设计规范，并与以下两份 DDL SSOT 文件配套：

1. `docs/refactor/core.sql` — `core.db` 的关系型与工作流状态内核 DDL
2. `docs/refactor/vec.sql` — `vec.db` 的向量索引数据库 DDL

三者的关系是：

| 文件 | 角色 |
| --- | --- |
| `database.md` | 设计原则、边界、语义、一致性策略、迁移规范 |
| `core.sql` | `core.db` 的 DDL SSOT |
| `vec.sql` | `vec.db` 的 DDL SSOT |

---

## 1. 设计目标

本次数据库重构必须同时满足以下目标：

1. **用 SQLite 替代 Cloudflare D1 作为业务与工作流状态中心**
2. **用 sqlite-vec / vec0 virtual table 替代 Cloudflare Vectorize**
3. **保留 clean / rag 的明显分段处理与状态机语义**
4. **去掉 queue / callback / service binding / Durable Object**
5. **支持 claim / lease / heartbeat / retry / restart / purge**
6. **支持本地对象存储而不是把大文本、大文件塞进数据库**
7. **支持组件化 monorepo，但运行时仍是模块化单体**

---

## 2. 总体数据库拓扑

## 2.1 两库分离

重构后数据库必须拆分为两个 SQLite 文件：

```text
data/
  db/
    core.db
    vec.db
```

职责分工如下：

| 数据库 | 角色 | 承载内容 |
| --- | --- | --- |
| `core.db` | 关系型主库 + workflow kernel | 用户/团队/ingestion/workflow/claims/artifacts/configs/audit |
| `vec.db` | 向量索引库 | namespace、vector records、sqlite-vec embedding index |

## 2.2 为什么必须拆成两库

拆成 `core.db` 与 `vec.db`，是为了显式隔离两类完全不同的数据形态：

1. **业务状态写入**
   - 高频小事务
   - 强调工作流一致性
   - 强调 claim/lease/retry
2. **向量索引写入**
   - 写放大更明显
   - 删除与重建成本不同
   - 查询模式不同

这样做的好处是：

1. 避免 workflow 写入和向量写入互相污染；
2. 便于独立备份、vacuum、重建；
3. 便于未来替换向量实现；
4. 让 `core.db` 继续保持“状态内核”定位。

---

## 3. 全局设计原则

## 3.1 `core.db` 是 workflow kernel，不是普通业务库

`core.db` 除了承载关系数据，还承担：

1. 任务分配；
2. step claim/lease；
3. 失败恢复；
4. restart / purge / replay；
5. 审计与观测。

因此所有阶段流转都必须落到 `core.db`。

## 3.2 `vec.db` 只做向量索引，不做工作流控制

`vec.db` 不承担：

1. 任务调度；
2. 权限与租户主判断；
3. retry / restart 的状态机；
4. 业务主记录。

它只承担：

1. chunk 向量存储；
2. namespace 维度；
3. 最小向量元数据；
4. 相似度检索。

## 3.3 不依赖跨库强事务

`core.db` 与 `vec.db` 之间**不以跨库原子事务为前提**。  
系统一致性依赖：

1. `core.db` 中显式的状态字段；
2. `workflow_steps` 的重试与补偿；
3. `chunks.vec_status` 的过渡状态；
4. `purge_requests` / `restart_requests` 的显式请求状态。

## 3.4 所有大对象都存对象层，不存数据库

以下内容禁止直接内联存入数据库字段：

1. 原始文件二进制；
2. 大段清洗文本；
3. 完整 structured JSON；
4. 长段 chunk 文本；
5. 浏览器抓取中间缓存。

数据库只保存：

1. 对象引用；
2. 内容 hash；
3. 元数据；
4. 产物类型；
5. 工作流关系。

## 3.5 payload 只存引用，不存大正文

`workflow_steps.payload_json` 必须遵守以下规则：

1. 仅允许保存 IDs、object keys、schema version、配置版本、参数；
2. 不允许直接内联大文本内容；
3. 超过轻量控制数据范围的内容必须转成 artifact + object store ref。

这是为了避免 step 表膨胀，并确保 restart/replay 时 payload 稳定可复用。

---

## 4. 关键数据不变量

以下不变量必须在实现与审计中被严格维护。

## 4.1 Step claim 不变量

1. 一个 `workflow_step` 在任一时刻最多只能有一个 `status='active'` 的 claim；
2. lease 的唯一权威记录在 `task_claims`；
3. `workflow_steps` 不再单独保存 `claimed_by` / `lease_expires_at`；
4. step 被 claim 时，必须在同一事务里：
   - 创建 `task_claims`
   - 更新 `workflow_steps.status='running'`
   - 增加 `attempt_count`

以上第 1 条应直接由 DDL 约束保证：  
`core.sql` 里的部分唯一索引 `ux_task_claims_active_step ON task_claims(step_id) WHERE status = 'active'` 是这个不变量的结构性保障，而不是仅靠应用层“自觉避免”重复 claim。

## 4.2 Chunk identity 不变量

1. `chunk_id` 在全系统全局唯一；
2. `core.db.chunks` 是 chunk 身份的 SSOT；
3. `vec.db.vector_records.chunk_id` 只能引用已存在的 `core.db.chunks.id`；
4. 向量重试必须围绕同一个 `chunk_id` 做幂等 upsert，而不是生成新 ID。

## 4.3 Vector consistency 不变量

1. `chunks.vec_status='vectorized'` 只表示 **core.db 侧** 已完成向量化；最终检索可见性还必须同时满足 active namespace 且 `vec.db.vector_records.deleted_at IS NULL`；
2. purge 时必须先把 `chunks.vec_status` 置为 `pending_purge`；
3. 删除 `vec.db` 记录成功后，才能把 `chunks.vec_status` 置为 `purged`；
4. 凡是 `pending_purge` 长时间滞留的 chunk，都视为异常并应重试或告警。

## 4.4 Restart / purge request 不变量

`restart_requests` 与 `purge_requests` 必须有独立状态机：

1. `pending`
2. `processing`
3. `completed`
4. `failed`
5. `cancelled`

任何重构实现都不允许把 restart/purge 设计成“无状态管理动作”。

---

## 5. `core.db` 设计说明

## 5.1 表分组

`core.db` 分为六类表：

| 分组 | 主要表 | 作用 |
| --- | --- | --- |
| 身份与控制面 | `users`, `teams`, `team_members`, `api_keys`, `sessions` | auth / team / API key |
| 输入与文档对象 | `uploads`, `sources`, `documents`, `static_files`, `artifacts`, `chunks` | ingestion 与对象元数据 |
| 工作流内核 | `workflow_runs`, `workflow_steps`, `task_claims`, `step_attempts`, `workflow_step_links`, `workflow_events` | workflow state machine |
| 配置与版本 | `configs`, `prompt_versions`, `provider_configs` | prompt / provider / workflow config |
| 运维请求 | `restart_requests`, `purge_requests` | restart / purge 执行入口 |
| 审计 | `audit_logs` | 操作审计 |

## 5.2 为什么增加 `chunks`

`chunks` 表是本次设计里的关键补充。  
它用于：

1. 固化 chunk 身份；
2. 承载 chunk 与 document/artifact 的关系；
3. 记录 `vec_status`；
4. 为 vec.db 提供稳定逻辑主键。

如果没有 `chunks` 表，vectorize retry/purge/replay 很容易出现孤儿向量或重复 chunk。

## 5.3 为什么保留 `workflow_step_links`

本设计不使用静态模板化 `workflow_edges`，而是使用运行时形成的 `workflow_step_links`。  
它的用途不是驱动调度，而是：

1. 记录实际产生的下游 step；
2. 支持工作流拓扑观测；
3. 支持 restart / downstream replay 分析；
4. 保留动态 fan-out 的轨迹。

也就是说，**调度逻辑在代码里，运行图在数据库里。**

## 5.4 `workflow_runs` 需要配置快照

`workflow_runs.config_snapshot_json` 必须在创建 run 时写入。  
这是为了：

1. 让历史 run 可复现；
2. 支持 restart 时选择“沿用旧配置”或“升级到新配置”；
3. 防止 prompt/config 演进导致历史问题无法追踪。

## 5.5 `workflow_steps` 的关键语义

`workflow_steps` 是调度核心。  
最关键字段包括：

| 字段 | 作用 |
| --- | --- |
| `stage` | 逻辑阶段，例如 `clean`, `structurize`, `construct`, `vectorize` |
| `action` | 阶段内动作，如 `html_crawl`, `browser_pdf`, `provider_x_fetch` |
| `status` | 当前状态 |
| `payload_json` | 输入引用与参数 |
| `attempt_count` | 已发起的执行尝试总数 |
| `max_attempts` | 最大尝试次数 |
| `available_at` | 该 step 何时可被重新调度 |
| `priority` | 调度优先级 |
| `executor_hint` | 预期由哪个 worker lane 处理 |

## 5.6 `task_claims` 的关键语义

`task_claims` 是唯一的 lease 权威记录。  
它必须支持：

1. claim token；
2. worker identity；
3. 过期时间；
4. heartbeat；
5. active / finished / expired / released / cancelled 等状态。

`workflow_steps.status='running'` 只表示 step 正在执行；  
“是否仍然被持有”以 `task_claims` 为准。

## 5.7 `step_attempts` 的关键语义

`step_attempts` 用于记录每一次尝试，不仅记录失败，还要区分终止原因：

1. `success`
2. `executor_failure`
3. `lease_timeout`
4. `cancelled`

这样重试策略和告警才能区分“业务失败”和“worker 崩溃”。

---

## 6. `vec.db` 设计说明

## 6.1 表分组

`vec.db` 保持最小化，建议包含：

| 表 | 作用 |
| --- | --- |
| `vector_namespaces` | namespace / collection 元数据 |
| `vector_records` | chunk 与向量索引行的映射 |
| `chunk_embedding_index` | sqlite-vec 虚拟向量表 |

## 6.2 单一 embedding 维度约束

第一版设计建议：

> **一个部署实例只启用一个主 embedding 维度。**

原因是 sqlite-vec 的向量表通常需要固定维度。  
因此：

1. 选定 embedding model 即意味着确定一个维度；
2. 若未来更换 embedding 维度，应视为一次 schema migration；
3. 若确实要并存多维度，应扩展为多 virtual tables，而不是让业务代码动态拼装底层索引。

当前 `vec.sql` 使用 **1536 维** 作为默认 SSOT。

## 6.3 为什么使用 `embedding_rowid`

`vector_records` 与虚拟向量表之间通过 `embedding_rowid` 关联，而不是把业务字段直接塞进向量 virtual table。  
这样做的好处：

1. 向量层与业务元数据解耦；
2. search 命中后可以先拿 `rowid`，再 join 到 `vector_records`；
3. future migration 更容易；
4. 业务字段变动不会污染虚拟向量表结构。

这里必须冻结一个实现不变量：  
`chunk_embedding_index.rowid` 必须与 `vector_records.embedding_rowid` 一一对应。  
否则 P5 定义的 “KNN rowid scan -> 映射到 `chunk_id` -> core hydration” 合同就会失效。

## 6.4 为什么有 `deleted_at`

`vector_records.deleted_at` 不是多余字段。  
它用于：

1. 在 purge 过程中先软删除，再删虚拟索引；
2. 给检索层一个过滤窗口；
3. 支持定位“逻辑已删除但物理清理尚未完成”的记录。

## 6.5 Search / hydration 查询契约

P5 的检索链路必须显式区分 **vec candidate** 与 **core hydration**：

1. 查询入口先用 `(team_id, namespace_key)` 解析 active namespace；
2. 读取该 namespace 的 `distance_metric`，并据此选择正确的 sqlite-vec KNN 查询模式；
3. vec 查询只返回 `rowid` 候选，再通过 `embedding_rowid -> chunk_id` 做映射；
4. 映射后的 `chunk_id` 必须回到 `core.db` 做 hydration / post-filter，而不是直接把 vec 结果当最终结果返回；
5. 当前 v1 的权限边界仍以 team isolation 为准；尚未把 document 级私有 ACL 做成数据库 SSOT。

也就是说，`core.db` 不是 KNN 入口；它是 **KNN 之后** 的上下文补全与状态过滤层。

---

## 7. 关键事务流程

## 7.1 Claim step

标准 claim 事务应为：

1. `BEGIN IMMEDIATE`
2. 选取某个 `pending/retry_wait` 且 `available_at <= now` 的 step
3. 验证该 step 不存在 active claim
4. 更新 `workflow_steps.status='running'`
5. `attempt_count = attempt_count + 1`
6. 插入新的 `task_claims`
7. 插入新的 `step_attempts`
8. `COMMIT`

## 7.2 Heartbeat

长任务运行期间，worker 必须定期：

1. 更新 `task_claims.last_heartbeat_at`
2. 必要时续租 `lease_expires_at`

heartbeat 是长任务安全执行的必要条件。

## 7.3 Step success

step 成功时应：

1. 写 `artifacts` / `chunks` / 其他结果元数据
2. 更新当前 `workflow_steps.status='succeeded'`
3. 写 `step_attempts.termination_reason='success'`
4. 将 `task_claims.status='finished'`
5. 创建下游 `workflow_steps`
6. 写 `workflow_step_links`
7. 发 `workflow_events`

## 7.4 Step failure

若执行器明确失败：

1. 记录 `step_attempts.termination_reason='executor_failure'`
2. 若还有剩余尝试次数，则：
   - `workflow_steps.status='retry_wait'`
   - 更新 `available_at`
3. 否则：
   - `workflow_steps.status='failed'`
4. claim 标记为 `finished` 或 `cancelled`
5. 记录 `workflow_events`

## 7.5 Lease timeout

如果 worker 崩溃或超时：

1. claim reaper 把 claim 标为 `expired`
2. 补写一条 `step_attempts`，`termination_reason='lease_timeout'`
3. 根据 `attempt_count/max_attempts` 决定转为 `retry_wait` 还是 `failed`

## 7.6 Vector upsert

vectorize 成功时建议按以下逻辑推进：

1. `core.db.chunks.vec_status='pending_vectorize'`
2. 生成 embedding
3. 在 `vec.db.vector_records` 中 upsert 映射，并确定 `embedding_rowid`
4. 在 `chunk_embedding_index` 中以同一个 `rowid=embedding_rowid` upsert 向量
5. 回写 `core.db.chunks.vec_status='vectorized'`

## 7.7 Purge

purge 不能直接删除所有内容，建议顺序如下：

1. 创建 `purge_requests(status='pending')`
2. worker 领取并置 `processing`
3. `core.db.chunks.vec_status='pending_purge'`
4. 软删除 `vec.db.vector_records.deleted_at`
5. 删除 `chunk_embedding_index` 中的向量行
6. 回写 `core.db.chunks.vec_status='purged'`
7. 如需删除对象，再走 artifact/object store 清理
8. `purge_requests.status='completed'`

---

## 8. 核心视图与运维视图

## 8.1 `core.db` 核心视图

建议重点依赖这些视图：

| View | 作用 |
| --- | --- |
| `v_ready_steps` | 调度器查询待执行 step |
| `v_active_claims` | 查看当前 lease 占用 |
| `v_latest_step_attempts` | 查看每个 step 的最近尝试（attempt 级定位） |
| `v_failed_steps` | 浏览当前 failed step 及其最近一次失败上下文（step 级扫描） |
| `v_stale_claims` | 查找 lease 已过期但仍未收敛的 claim |
| `v_workflow_run_summary` | 统计每个 workflow run 的进度 |
| `v_document_vector_status` | 查看文档的 chunk / vec 状态（core 侧汇总，不等于最终检索可见数） |
| `v_search_hydration` | KNN 命中后的 chunk/document/source/workflow hydration 与 core 侧 post-filter |
| `v_restart_backlog` | 查看未处理 restart 请求 |
| `v_purge_backlog` | 查看未处理 purge 请求 |
| `v_pending_purge_chunks` | 查看长时间处于 `pending_purge` 的 chunk backlog |

## 8.2 `vec.db` 核心视图

| View | 作用 |
| --- | --- |
| `v_active_vector_namespaces` | 当前 active namespace 及其 model / dim / metric 契约 |
| `v_active_vector_records` | active namespace 下、用于 `rowid -> chunk_id` 映射的向量记录 |
| `v_namespace_stats` | namespace 下的 vec 侧向量统计（不等于最终检索可见数） |

## 8.3 跨库 detector 约定

P6/P7 需要的 detector / ops read model 允许是 **服务层拼装结果**，不要求都固化成单个跨库 SQL view：

1. stale claim、failed step、restart/purge backlog 直接依赖 `core.db` 视图；
2. vec/core mismatch detector 由 `core.db` 的 `v_pending_purge_chunks` / `v_document_vector_status` 与 `vec.db` 的 `v_active_vector_records` / `v_namespace_stats` 组合得到；
3. 由于本方案不依赖跨库强事务，所以“跨库对账”是显式 detector 责任，而不是假设数据库层天然一致。

---

## 9. ID、时间、JSON 约定

## 9.1 ID

全系统主键统一使用 `TEXT`，由应用层生成稳定 ID。  
建议：

1. workflow / step / chunk / artifact / request 都采用显式字符串 ID；
2. 不依赖 SQLite 自增主键表达业务身份；
3. 跨库关联全部使用逻辑主键。

## 9.2 时间

统一使用 UTC ISO-8601 文本时间，格式示例：

```text
2026-05-30T18:16:48.420Z
```

原因：

1. 便于 SQLite 文本排序；
2. 便于日志与 API 输出一致；
3. 避免本地时区混乱。

## 9.3 JSON

`*_json` 字段只用于：

1. 轻量 metadata；
2. config snapshot；
3. payload refs；
4. event payload。

所有 JSON 字段都应通过 `json_valid(...)` 约束。

---

## 10. 从 legacy-family 的迁移映射

## 10.1 `smind-admin`

主要映射到：

1. `users`
2. `teams`
3. `api_keys`
4. `uploads`
5. `sources`
6. `documents`
7. `workflow_runs`

## 10.2 `smind-clean-dispatcher`

主要映射到：

1. `workflow_runs`
2. `workflow_steps`
3. `task_claims`
4. `step_attempts`
5. `workflow_step_links`
6. `workflow_events`

## 10.3 clean skills

主要映射到：

1. `artifacts`
2. `static_files`
3. `documents`
4. `workflow_events`

## 10.4 rag skills

主要映射到：

1. `chunks`
2. `artifacts`
3. `vector_records`
4. `chunk_embedding_index`

## 10.5 vectorizer DO / Vectorize

主要映射到：

1. `chunks.vec_status`
2. `purge_requests`
3. `restart_requests`
4. `vec.db.vector_records`
5. `vec.db.chunk_embedding_index`

---

## 11. 实施顺序

数据库层建议按以下顺序落地：

1. 先创建 `core.sql`
2. 先让 `workflow_runs/workflow_steps/task_claims/step_attempts` 跑通
3. 再补 `uploads/sources/documents/artifacts/chunks`
4. 再补 `restart_requests/purge_requests`
5. 最后接入 `vec.sql`
6. 接入向量后再落 `VectorStore` 与 P5 search/hydration query layer

原因是：

1. 工作流状态机先于向量检索；
2. claim/retry/restart 先于 search；
3. `core.db` 是真正的第一性基础设施。

P7 的默认入口切换、legacy freeze、回滚/对账 runbook 属于 **运行时收敛阶段**，不是新增基表阶段；  
但凡 cutover 改动触及 claim、restart、purge、search/hydration、namespace 解析这些数据库契约，都必须先回写本文件与对应 SQL SSOT。

---

## 12. 最终结论

`smind-family` 的数据库设计必须围绕三个核心判断展开：

1. **`core.db` 是状态机内核**
2. **`vec.db` 是向量索引层**
3. **系统一致性依赖显式状态与补偿，而不是跨库强事务**

因此，后续所有实现都必须服从这三条底线：

1. 任何异步推进都必须在 `core.db` 留痕；
2. 任何向量状态都必须能回溯到 `core.db.chunks`；
3. 任何 restart/purge 都必须作为数据库中的显式请求执行；
4. 任何 P7 cutover / legacy freeze 都不能绕过这些数据库契约单独演化。

只要这三条底线不被破坏，整个 Python 模块化单体的 workflow kernel 就是稳定的。
