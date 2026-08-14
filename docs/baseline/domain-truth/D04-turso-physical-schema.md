# D04 — Turso Physical Schema Constitution

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 共有域**：跨全部子系统的 **Turso 主库物理表、列约束、索引与只读 VIEW 宪法**
>
> **文档性质**：`shared-domain constitution / physical schema truth`
>
> **文档状态**：`accepted / owner-frozen`（域内已接受并进入真相层；全系统 truth layer 尚未统一 frozen）
>
> **Truth 版本 / 日期**：`D04-v1.1 / 2026-08-12`（v1.0 + S11 窄 reopen：model/inference 三表）；**D08-calibrated 2026-08-13**（registry 要求重排 + 3 表 proposed，**55 required 不变**）
>
> **作者 / 规范化**：`Codex`；**裁决**：`MKB owner` 2026-08-11 冻结 v1.0；2026-08-12 批准 S11 增表 reopen
>
> **权威输入**：
> - 持久化宪法：`S12-v1.0`（`T-O-97..110`）
> - 对象 catalog 语义：`S13-v1.0`（`T-O-111..125`；物理表由 S12 migration 承载）
> - 业务列族与不变量：`S01-v1.5`、`S02-v1.3`、`S03-v1.3`、`S04-v1.2`、`S05-v1.1`、`S06-v1.0`、`S07-v1.0`、`D01-v1.4`、`D02-v1.0`
> - 仓库落点：`D03-v1.0`（`data/database/`、`src/persistence/`；**D03 不拥有 DDL**）
> - Owner 冻结授权：采纳 v0.2 台账与 OG-D04-01..11 推荐默认；登记 `T-O-160..179`
> - legacy-family/console + legacy-python vec 对照（ReferenceAnchor only）
>
> **词汇权威**：`docs/baseline/spec-glossary.md` v2.0
>
> **下游消费者**：S12 migration 链、`src/persistence` repositories、architecture tests、S15 运维扫描、S09 检索、`17` topology 挂载路径

> **与 S12 分账**：S12 冻结 **拓扑、TX-01..08、outbox/claim 环、migration/readiness、模块前缀、vector 最小合同**；D04 冻结 **物理表闭集、表名、列、CHECK/UNIQUE/FK 语义、索引与 VIEW**。冲突时：业务状态机合法边仍以 S02–S07 为准；**物理唯一性/索引可验收性**以 D04 为准并回填上游叙述。

> **与 S15 分账**：D04 提供 **可观测物理表**（domain_events / diagnostic_logs / security_audit）；S15 拥有 **retention 数值、告警阈值、export 到 Prometheus/OTLP、runbook**。事件/日志 **不是** 业务状态 SSOT。

> **与 S09 分账**：D04 提供 **同库最终向量列 + ANN 索引 + filter 列 + namespace**；S09 拥有 **metric/topk/index generation 策略/serving publication 算法**。`存在向量行 ≠ serving`。

> **与 contracts 分账**：`src/contracts/` 是 **typed 消息体** SSOT（D03）；D04 是 **关系行形状** SSOT。

> **与 S13 分账**：对象 **字节** 在 `data/objects/`；catalog 三表在主库。存在≠业务成功。

> **Legacy 边界（T-O-42 / T-O-101）**：禁止 `smind_*`；禁止 clean/rag 双 process；禁止 `smind_vec_process` 克隆；禁止 log 作状态 SSOT；禁止外置 Vectorize 作 v1 最终向量 SSOT。

> **冻结声明**：Owner 2026-08-11 批准本文件为 **数据库表结构与细节的真相层**。§2 全域 Truth **append-only**（`T-O-160..179` + S11 reopen `T-O-193`/`T-O-194`）。v1 required **55 表**（52 + model/inference 3）以 §2.2 为准；变更须显式 reopen。

> **S11 校准 / reopen（2026-08-12）**：Owner 接受 catalog 独立三表（`T-O-193`）。新增 `mkb_model_catalog`、`mkb_adapter_bindings`、`mkb_inference_invocations`。embedding 空间严禁跨 model 混用；写/读须带 model/namespace/adapter 围栏（`T-O-192`）。

---

## 1. Domain 介绍

### 1.1 Domain 价值

D04 回答：在 **单主库 `mkb_primary`**（T-O-102）上，如何用 **一份可 migration 的物理 schema** 兑现已冻业务真相——使 TX 矩阵、CAS、claim/fence、bytes-first、generation pointer、Intake 十表、object catalog 与派生 vector **可编码、可索引、可验收**，而不把业务状态机泄漏进 DDL 注释或 JSON。

没有 D04，实现者会：

- 各写一套表名/列名，破坏 migration 单链；  
- 用 `payload_extra` 塞 identity/state/proof；  
- 漏建队列/租户/幂等索引，退回全表扫描；  
- 另起第二 outbox 或 VIEW 写路径。

### 1.2 Scope fence

**D04 负责：**

- 主库逻辑模块分区与 **物理表闭集**（v1 强制 + 显式 defer）；  
- 稳定表名（`mkb_` 前缀）与 **表级职责 owner**；  
- 每表：PK/UNIQUE/CHECK/逻辑 FK、不可变性、CAS 列、默认值；  
- 索引闭集（四类：租户列表 / 状态队列 / 主体反查 / 幂等唯一，S12-T029）；  
- 只读 VIEW 清单与禁止写路径；  
- 与 TX-01..08 的 **表参与映射**。

**D04 不负责：**

| 排除项 | 归属 |
|---|---|
| 状态机合法边 / 业务语义 | D01/D02、S02–S07 |
| Persistence Ports 接口形状 | S12 |
| Object bytes layout / GC 数值策略 | S13（catalog 表语义已冻，物理列本文件） |
| Embedding 模型、ANN、serving 资格 | S08–S10 |
| Prompt 正文 | `data/prompts/**` + hash 指针（D03） |
| 告警阈值 / backup 排程 | S15 |

### 1.3 全局物理定律（继承 + 本文件强制）

| ID | 定律 |
|---|---|
| `D04-P01` | 物理库逻辑名：`mkb_primary`；单一可写 SSOT；无 DB-per-team / 无第二可写业务库。 |
| `D04-P02` | 全部 **team-owned 业务表** 含 `team_uuid TEXT NOT NULL`；查询/写必须 team-scoped。 |
| `D04-P03` | 表名前缀 **`mkb_`**；禁止 `smind_*`。 |
| `D04-P04` | 业务表（除 ops bookkeeping 与纯 registry 全局定义表的排除项）含 `payload_extra TEXT NOT NULL DEFAULT '{}'`；**禁止**承载 identity/state/proof/route/auth/secret/正文。 |
| `D04-P05` | 时间列：UTC ISO-8601 文本或 INTEGER epoch-ms（实现二选一，**库内统一**）；本草案用 `TEXT` RFC3339 UTC。 |
| `D04-P06` | Digest 列：完整 `sha256:<64 lowercase hex>` 或分离 `digest_algorithm + digest_hex`；本草案采用 **`digest_algorithm TEXT + content_digest TEXT`**（hex 无前缀）+ CHECK algorithm∈`sha256`。 |
| `D04-P07` | MKB 内生 UUID：UUIDv7 字符串；上游 `team_uuid`/`task_uuid`/`trace_uuid` 允许 v4/v7。 |
| `D04-P08` | **单一 outbox 表** `mkb_outbox`；禁止 `intake_scheduling_outbox` 等第二 SSOT（S04 逻辑“scheduling outbox”映射为 `kind` 行）。 |
| `D04-P09` | Claim/fence **行内** 落在 `mkb_processes`（不另建 claim 表为 SSOT；避免双写）。 |
| `D04-P10` | SQL VIEW **只读**；禁止 trigger 经 VIEW 改业务真相。 |
| `D04-P11` | FK：同模块强 FK 优先；跨模块可用逻辑 UUID 引用 + 应用校验（避免迁移环）。本草案对关键父子链使用 `REFERENCES`。 |
| `D04-P12` | 默认启用 Concurrent Writes / Native Vector；vector 列与 ANN 索引必须在 migration 中创建；能力缺失 → readiness=false。 |
| `D04-P13` | **可观测三表 v1 强制**：`mkb_domain_events`、`mkb_ops_diagnostic_logs`、`mkb_security_audit_events`。三者 **均非业务 SSOT**；不得替代 tasks/processes CAS。 |
| `D04-P14` | **domain_events 与触发业务同事务写入**（强一致）；插入失败 → 整 TX 失败。diagnostic_logs 允许同 TX 或 best-effort 后写（见 §3.1.5）。 |
| `D04-P15` | 认证/schema/跨 team 拒绝等 **不进业务表** 的 admission 结果 → 只写 `mkb_security_audit_events`（及可选 diagnostic）。 |
| `D04-P16` | **最终向量本体** 仅存于 `mkb_vector_records.embedding`（native F32）；**禁止** 外置 Vectorize/独立 vec.db 作为 v1 可写 SSOT；**禁止** `content_full` 大正文列。 |
| `D04-P17` | **禁止** `mkb_vec_process` / 等价向量工作单元 SSOT 表；vectorize 队列 = `mkb_outbox.kind ∈ vectorize_*` + 幂等 upsert records。 |
| `D04-P18` | 每 team 至少一个 `mkb_vector_namespaces` active 行（bootstrap 可默认 `default`）；records 必须 FK/逻辑引用 namespace。 |

### 1.4 Domain 完成定义

| # | 条件 | 状态 |
|---|---|---|
| 1 | §2 表名台账闭集无歧义（52 required） | **met** |
| 2 | §3 每强制表具备可落地列/约束/索引（含 ops 三表与 vector 物理合同） | **met** |
| 3 | TX-01..08 + domain_events 同事务映射完整 | **met** |
| 4 | VIEW 清单只读可验收（含 vectors_active / events_by_trace） | **met** |
| 5 | Owner 冻结 + `T-O-160..179` + `spec-index` / glossary 回填 | **met** |

实现期仍须通过 migration/architecture 测试兑现 §3；本冻结不冒充代码已交付。

---

## 2. 真相层（已冻结）

> 全局 Truth-ID：`T-O-160..179`（接续 D03 `T-O-159`）。域内 `D04-T*` 与 `D04-P*` 为同文引用别名，**不**构成第二编号空间的改写权。

### 2.0 Owner / 域内 Truth 台账（append-only）

| Truth-ID | 域内 ID | 已锁定真相 | 来源 | 下游约束 |
|---|---|---|---|---|
| `T-O-160` | `D04-T001` | D04 是 MKB **Turso 物理 schema 宪法**：表闭集、表名、列/CHECK/UNIQUE、索引、只读 VIEW、TX 表参与映射。不拥有业务状态机合法边。 | Owner freeze | migration/architecture 必须服从 |
| `T-O-161` | `D04-T002` / `D04-P01` | 物理库逻辑名 `mkb_primary`；单可写 SSOT；禁 DB-per-team / 第二可写业务库。 | S12 + Owner | 17 topology 继承 |
| `T-O-162` | `D04-T003` / `D04-P02-P03` | 表前缀 **`mkb_`**；team-owned 表 `team_uuid NOT NULL`；禁 `smind_*`。 | S12 + Owner | greenfield DDL |
| `T-O-163` | `D04-T004` | v1 **required 表闭集 = 52 张**（ops5+runtime9+registry14+intake15+generation4+object3+vector2）；§2.2 台账为权威枚举；canonical 十表与 ops/vector 强制集不可砍。 | Owner + v0.2 | 实现不得私自增减 required 而不 reopen |
| `T-O-164` | `D04-T005` / `D04-P08` | **单一** `mkb_outbox`；禁第二 outbox SSOT；scheduling/vectorize 均映射 `kind`。 | S12 + OG-02 | |
| `T-O-165` | `D04-T006` / `D04-P09` | Claim/fence **行内** `mkb_processes`；禁附属 claim 表作 SSOT（OG-01）。 | S03/S12 + OG-01 | |
| `T-O-166` | `D04-T007` / `D04-P13-P15` | 可观测三表 **required 且非业务 SSOT**：`mkb_domain_events`、`mkb_ops_diagnostic_logs`、`mkb_security_audit_events`。 | OG-08 + Owner | S15 定 retention/alert |
| `T-O-167` | `D04-T008` / `D04-P14` | **domain_events 与触发业务同事务**；插入失败 → 整 TX 失败（OG-09）。 | OG-09 | TX-01..08 映射 |
| `T-O-168` | `D04-T009` / `D04-P16` | **最终向量本体** = `mkb_vector_records.embedding`（native F32）；禁 `content_full`；禁外置 Vectorize/独立 vec.db 作 v1 可写 SSOT。 | OG-10/11 + T-O-107 | S09 算法不改落点 |
| `T-O-169` | `D04-T010` / `D04-P17-P18` | 禁 `mkb_vec_process`；vectorize 队列 = outbox `vectorize_*` + 幂等 upsert；**namespaces 头表 required**；records 引用 namespace。 | OG-05/11 | |
| `T-O-170` | `D04-T011` / `D04-P12` | 同库 **ANN 索引强制**（`vec_idx_mkb_vector_records_embedding` 或引擎等价）；CW+vector 能力缺失 → readiness=false。 | S12 + OG-11 | |
| `T-O-171` | `D04-T012` / `D04-P10` | SQL VIEW **只读**；禁经 VIEW 写业务真相；存在向量/日志 ≠ serving/Task success。 | S12-T028 | |
| `T-O-172` | `D04-T013` | TX-01..08 必须触及 §2.4 表集；适用状态变更 **同事务** 写 `mkb_domain_events`。 | T-O-104 + T-O-167 | 验收覆盖 |
| `T-O-173` | `D04-T014` / `D04-P04` | 业务表 `payload_extra` 非空默认 `{}`；禁 identity/state/proof/route/auth/secret/正文。 | S01/S04 | |
| `T-O-174` | `D04-T015` | 逻辑模块闭集：`ops|runtime|registry|intake|generation|object|vector`；单 migration 链。 | S12-T023 + D04 | |
| `T-O-175` | `D04-T016` | **冲突裁决**：业务状态合法边 → S02–S07；**物理唯一性/索引/表闭集** → D04；typed 消息形状 → contracts（D03）。 | Owner | 双源须回填 |
| `T-O-176` | `D04-T017` | 索引四类最低：租户列表 / 状态队列 / 主体反查 / 幂等唯一（含 partial unique 按需）。 | S12-T029 | |
| `T-O-177` | `D04-T018` | security_audit 承载 **不进业务表** 的 admission 拒绝；diagnostic 可 best-effort；二者均非 SSOT。 | OG-08 + S02 | |
| `T-O-178` | `D04-T019` | S15 拥有 retention/export/alert 数值；S09 拥有 ANN 参数与 serving publication；**不得**在 S15/S09 另起第二套表名闭集绕过 D04。 | 分账 | |
| `T-O-179` | `D04-T020` | OG-D04-01..11 以 v0.2 写入默认 **冻结**（见 §8）；reopen 须显式变更记录。 | Owner freeze | |
| `T-O-193` | `D04-T021` | S11 要求独立 **model catalog / adapter binding / inference invocation** 三表；不得并入 generation_invocations 或仅靠 diagnostic_logs。 | S11 Q3 | §2.2.8 / §3.8 |
| `T-O-194` | `D04-T022` | v1 required 表闭集 **55** 张 = 原 52 + `mkb_model_catalog` + `mkb_adapter_bindings` + `mkb_inference_invocations`。 | S11 reopen | 替换 T-O-163 之「52」计数解释 |
| `T-O-192` | `D04-T023` | **不同 embedding_model 向量严禁混用**；写/读必须校验 namespace 的 model+dimension 与记录一致；adapter_kind（或 binding 快照）作 **空间隔离** filter；禁止 silent 跨模型 fallback。 | S11 Q2 | vector 模块 |
| `T-O-197` | `D04-T024` | Layer A 空间隔离 + 调用 fail-closed 规则（见 §3.7.4b / S11 Q6）。 | S11 Q6 | |
| `T-O-198` | `D04-T025` | **Layer B 业务 filter** 独立于空间隔离：强制 `team_uuid`；intake source/item/revision 坐标；上游 facet（如 `industry-domain` + map）必须可索引过滤；B 不替代 A。 | S11 Q6 amended | S04/S10 对齐 |

**`D04-P01..P18`**：§1.3 物理定律全文冻结；与 T-O 冲突时以最新 T-O 为准。**计数**：表闭集以 `T-O-194`（55）为准，覆盖 `T-O-163` 的 52 计数。

### 2.1 逻辑模块与 migration 切片

物理仍 **一份** `mkb_primary`；migration 文件可分模块，**版本号全局线性**（S12-T020/T023）。

| 模块 | 目录建议（实现） | 职责 |
|---|---|---|
| `ops` | `…/migrations/ops/` | migrations、teams、domain_events / diagnostic_logs / security_audit、**inference_invocations** |
| `runtime` | `…/migrations/runtime/` | Task/Execution/Process/outbox/gate |
| `registry` | `…/migrations/registry/` | Workflow 七表 + definition + prompt hash + **model_catalog / adapter_bindings** |
| `intake` | `…/migrations/intake/` | S04 十表 + candidate/cleanup supporting |
| `generation` | `…/migrations/generation/` | S06/S07 artifact/pointer/invocation |
| `object` | `…/migrations/object/` | S13 catalog 三表 |
| `vector` | `…/migrations/vector/` | namespaces + records + native ANN index |

### 2.2 表名台账（v1 强制闭集 · **55** 张）

> **Status**：`required` = v1 必须；`defer` / `forbid` = 明确不做。  
> **Product owner** = 语义权威；**DDL owner** = D04 + S12 migration。

#### 2.2.1 `ops` 模块（5）

| # | 物理表名 | 逻辑职责 | Product owner | 是否 SSOT | Status |
|---|---|---|---|---|---|
| 1 | `mkb_schema_migrations` | 线性 migration 账本 | S12 | schema 版本 SSOT | required |
| 2 | `mkb_teams` | 最小 Team Registry | S01 | team 投影 SSOT | required |
| 3 | `mkb_domain_events` | 业务变迁统一时间线（append-only） | S15 语义 / D04 物理 | **否** | required |
| 4 | `mkb_ops_diagnostic_logs` | 诊断级日志（降维 smind_logs） | S15 / D04 | **否** | required |
| 5 | `mkb_security_audit_events` | admission/安全审计（不进业务表的拒绝） | S16/S15 / D04 | **否** | required |
| 53 | `mkb_inference_invocations` | **全能力** inference 调用账（append-only；非业务状态 SSOT） | S11 / D04 | **否** | required |

#### 2.2.2 `runtime` 模块（9）

| # | 物理表名 | 逻辑职责 | Product owner | Status |
|---|---|---|---|---|
| 6 | `mkb_tasks` | Task 六态聚合投影 | S02 | required |
| 7 | `mkb_task_audits` | 1:1 不可变 create audit | S01/S02 | required |
| 8 | `mkb_task_restarts` | 人工 restart 因果/admission | S02 | required |
| 9 | `mkb_executions` | Execution 八态 + binding | S03 | required |
| 10 | `mkb_processes` | Process 八态 + claim/fence + error | S03 | required |
| 11 | `mkb_outbox` | 全库 transactional outbox（含 vectorize_*） | S12/S03 | required |
| 12 | `mkb_execution_gates` | Human gate 头 | S05 | required |
| 13 | `mkb_execution_gate_targets` | ReviewTarget 快照 | S05 | required |
| 14 | `mkb_execution_gate_decisions` | Decision append-only | S05 | required |
| — | `mkb_process_claims` | 附属 claim | — | **defer**（行内） |
| — | `mkb_process_outcomes` | 独立 outcome | — | **defer**（列并入 processes） |
| — | `intake_scheduling_outbox` | 第二 outbox | — | **forbid** |
| — | `mkb_vec_process` / `smind_vec_process` | 向量工作单元表 | — | **forbid**（outbox 替代） |

#### 2.2.3 `registry` 模块（14）

| # | 物理表名 | 逻辑职责 | Product owner | Status |
|---|---|---|---|---|
| 15 | `mkb_workflow_registry` | Workflow 注册头 + active pointer | S03 | required |
| 16 | `mkb_workflow_revisions` | 不可变 revision | S03 | required |
| 17 | `mkb_workflow_steps` | 步骤定义 | S03 | required |
| 18 | `mkb_workflow_routes` | 路由边 | S03 | required |
| 19 | `mkb_workflow_bindings` | 槽位绑定 | S03 | required |
| 20 | `mkb_workflow_controls` | 超时/retry/cancel | S03 | required |
| 21 | `mkb_workflow_guards` | 确定性 guard | S03 | required |
| 22 | `mkb_intake_semantic_definitions` | 语义键定义 | S04 | required |
| 23 | `mkb_intake_action_definitions` | Item action 定义 | S04 | required |
| 24 | `mkb_source_kind_definitions` | Source kind | S05 | required |
| 25 | `mkb_preflight_profile_definitions` | preflight profile | S05 | required |
| 26 | `mkb_structure_schema_definitions` | StructureSchema | S06 | required |
| 27 | `mkb_construction_schema_definitions` | ConstructionSchema | S07 | required |
| 28 | `mkb_prompt_hash_pointers` | prompt path + content hash | D03/S14 | required |
| 54 | `mkb_model_catalog` | 逻辑模型目录（embed/rerank/generate…） | S11/S14 | required |
| 55 | `mkb_adapter_bindings` | 能力 → adapter_kind + model 绑定 | S11 | required |
| — | ProcessCapabilityManifest 表 | code registry | S03 | **defer 表** |
| — | `mkb_intake_provider_definitions` | registered_api provider 头 | D08/S05 | **proposed / D08**（非 required） |
| — | `mkb_intake_provider_operations` | operation + request/envelope/member schema digest | D08/S05 | **proposed / D08**（非 required） |
| — | `mkb_intake_clean_strategy_definitions` | web/pdf/doc clean strategy | D08/S05 | **proposed / D08**（非 required） |

#### 2.2.4 `intake` 模块（15）

| # | 物理表名 | 逻辑职责 | Product owner | Status |
|---|---|---|---|---|
| 29 | `mkb_intake_sources` | IntakeSource | S04 | required |
| 30 | `mkb_intake_snapshots` | IntakeSnapshot | S04 | required |
| 31 | `mkb_intake_items` | IntakeItem 三态 | S04 | required |
| 32 | `mkb_intake_revisions` | IntakeRevision | S04 | required |
| 33 | `mkb_intake_artifacts` | IntakeArtifact 元数据 | S04 | required |
| 34 | `mkb_intake_snapshot_memberships` | Membership | S04 | required |
| 35 | `mkb_intake_revision_semantics` | 修订语义值 | S04 | required |
| 36 | `mkb_intake_item_transitions` | Item transition ledger | S04 | required |
| 37 | `mkb_intake_candidate_sets` | CandidateSet head | S04/S05 | required |
| 38 | `mkb_intake_candidate_pages` | Candidate pages | S04/S05 | required |
| 39 | `mkb_intake_change_sets` | ChangeSet 头 | S04 | required |
| 40 | `mkb_intake_change_set_facts` | ChangeSet typed facts | S04 | required |
| 41 | `mkb_intake_repair_intents` | Repair intent | S04 | required |
| 42 | `mkb_intake_cleanup_intents` | Cleanup intent | S04 | required |
| 43 | `mkb_intake_cleanup_proofs` | Cleanup proof | S04 | required |

#### 2.2.5 `generation` 模块（4）

| # | 物理表名 | 逻辑职责 | Product owner | Status |
|---|---|---|---|---|
| 44 | `mkb_generation_artifacts` | 不可变 generation 元数据 | S06/S07 | required |
| 45 | `mkb_generation_invocations` | LLM/工具调用账 | S06/S07 | required |
| 46 | `mkb_generation_pointers` | per-type current CAS | S06/S07 | required |
| 47 | `mkb_generation_pointer_transitions` | pointer 变更账 | S06/S07 | required |

#### 2.2.6 `object` 模块（3）

| # | 物理表名 | 逻辑职责 | Product owner | Status |
|---|---|---|---|---|
| 48 | `mkb_stored_objects` | CAS catalog | S13 | required |
| 49 | `mkb_object_references` | live-ref 账本 | S13 | required |
| 50 | `mkb_object_delete_proofs` | 删除证据 | S13 | required |

#### 2.2.7 `vector` 模块（2）

| # | 物理表名 | 逻辑职责 | Product owner | Status |
|---|---|---|---|---|
| 51 | `mkb_vector_namespaces` | 向量空间头（model/dim/metric） | S09/S12 | required |
| 52 | `mkb_vector_records` | **最终向量本体** + filter 元数据 + soft-delete | S09/S12 | required |

**v1 强制表合计：55 张**（原 52 + inference_invocations + model_catalog + adapter_bindings）。  
编号 53–55 为 S11 reopen 追加；实现 migration 顺序仍全局线性，不要求物理编号等于创建顺序。

### 2.3 产品 / 持久化分工矩阵

| 关切 | 产品 Spec 决定 | D04/S12 决定 | 禁止 |
|---|---|---|---|
| 状态名与合法边 | S02–S07 | CHECK 枚举镜像 | DDL 发明新状态 |
| 身份与唯一键 | S01–S07 | PK/UNIQUE 实现 | 跨 team 裸 UUID 查询 |
| 事务边界 | S12 TX 矩阵 + 上游 | 同 UoW 多表写 | 拆 TX-05/06 |
| Outbox 语义 | S12/S03 | 单表 + kind（含 vectorize_*） | 多 outbox；vec_process 表 |
| Artifact 正文 | S13 bytes | handle+digest 列 | BLOB 塞大正文进业务/向量表 |
| Schema 定义正文 | contracts / code registry | digest + 可选 JSON | 运行期双源解释 |
| Prompt 正文 | git `data/prompts` | hash 指针表 | DB 存第二正文 |
| 可观测时间线 | S15 retention/export | domain_events 物理 + 同 TX | log 当业务成功 |
| 安全拒绝审计 | S16/S02 错误码 | security_audit 物理表 | 静默丢弃 admission 证据 |
| 向量可检索 | S09 serving/publication | 同库 F32 + ANN index + filter 列 | 有向量=已 serving；外置 Vectorize v1 SSOT；**跨 embedding_model 混用** |
| Model catalog / binding | S11/S14 语义 | `mkb_model_catalog` / `mkb_adapter_bindings` | 口头 config 当唯一目录 |
| Inference 调用账 | S11 写入语义 | `mkb_inference_invocations` | 仅靠 generation_invocations 或 diagnostic_logs |

### 2.4 TX 矩阵 → 表参与

| TX | 必须同事务触及的表（最小） |
|---|---|
| `TX-01` | `mkb_tasks` + `mkb_task_audits` +（契约要求时）`mkb_executions` + **`mkb_domain_events`** [+ `mkb_outbox`] |
| `TX-02` | `mkb_tasks` CAS + **`mkb_domain_events`** |
| `TX-03` | `mkb_processes` claim CAS + **`mkb_domain_events`** |
| `TX-04` | `mkb_processes` +（可选）`mkb_executions` + **`mkb_domain_events`** |
| `TX-05` | candidate→snapshot/item/revision/membership/changeset 规定集合 + `mkb_outbox` + **`mkb_domain_events`** |
| `TX-06` | generation artifacts/pointers/transitions + object catalog/ref + `mkb_outbox` + **`mkb_domain_events`** |
| `TX-07` | 任意业务行 + `mkb_outbox` + **`mkb_domain_events`**（若该变更属事件表覆盖类） |
| `TX-08` | gate decisions + gates CAS + executions + `mkb_outbox` + **`mkb_domain_events`** |

**vectorize 副作用（非 TX-06 内嵌 embedding）**：业务 proof commit → outbox `vectorize_*` → 异步 upsert `mkb_vector_records`（独立 TX）+ 可选 domain_event `vector.upserted`。

### 2.5 列类型约定（全表）

| 逻辑类型 | SQLite/libSQL 物理 | 说明 |
|---|---|---|
| UUID | `TEXT` | 36-char canonical |
| ENUM | `TEXT` + `CHECK` | 应用层双校验 |
| INT | `INTEGER` | revision、counters |
| BOOL | `INTEGER` 0/1 | `CHECK IN (0,1)` |
| DIGEST_HEX | `TEXT` | 64 hex；配 `digest_algorithm` |
| JSON | `TEXT` | `payload_extra` 等；核心真相不得只活在 JSON |
| UTC_TS | `TEXT` | RFC3339 |
| F32_VECTOR | `F32_BLOB(n)` 或 libSQL 等价 | **最终向量本体**；n = namespace.dimension |
| EVENT_TYPE | `TEXT` | 点分命名 `domain.action`（见 §3.1.3 闭集扩展规则） |

---

## 3. 逐表 Schema 与 Index

> 下列 DDL 为 **规范草案**（逻辑 SQL）。实现 migration 可调整列顺序/精确类型映射，但 **不得削弱** UNIQUE/CHECK/不可变语义。  
> 公共尾列缩写：`std_payload` = `payload_extra TEXT NOT NULL DEFAULT '{}'`；`std_created` = `created_at TEXT NOT NULL`。

---

### 3.1 `ops`

#### 3.1.1 `mkb_schema_migrations`

| 列 | 类型 | 约束 |
|---|---|---|
| `migration_id` | TEXT | PK |
| `checksum` | TEXT | NOT NULL |
| `applied_at` | TEXT | NOT NULL |
| `applied_by` | TEXT | NULL（进程/版本标识） |

**索引**：无额外索引（全表极小）。  
**规则**：已应用行 **禁止 UPDATE/DELETE**（应用层 + 可选触发器禁改）。无 `payload_extra`（S04 排除 bookkeeping）。

#### 3.1.2 `mkb_teams`

| 列 | 类型 | 约束 |
|---|---|---|
| `team_uuid` | TEXT | PK |
| `name` | TEXT | NOT NULL |
| `description` | TEXT | NULL |
| `status` | TEXT | NOT NULL CHECK ∈ `active,inactive,deleted` |
| `row_revision` | INTEGER | NOT NULL DEFAULT 0 |
| `creation_fingerprint` | TEXT | NOT NULL |
| `deactivated_at` | TEXT | NULL |
| `deleted_at` | TEXT | NULL |
| `created_at` / `updated_at` | TEXT | NOT NULL |
| `payload_extra` | TEXT | NOT NULL DEFAULT `'{}'` |

**索引**

| 名 | 定义 | 用途 |
|---|---|---|
| `ux_mkb_teams_fingerprint` | UNIQUE(`team_uuid`, `creation_fingerprint`) 语义：同 team 异 fingerprint → 应用冲突；物理可用单行 PK + 应用校验 | 幂等注册 |
| `ix_mkb_teams_status` | (`status`, `updated_at`) | list 过滤 |

#### 3.1.3 `mkb_domain_events`（append-only · 非 SSOT）

> 对标 legacy-python `workflow_events`，升级为 **全 leaf-worker 统一业务时间线**。  
> **不**推进状态；状态仍以 tasks/executions/processes/intake/generation 表为准。  
> **与触发业务同事务**（D04-P14）：插入失败 → 整 TX 失败。

| 列 | 类型 | 约束 |
|---|---|---|
| `event_uuid` | TEXT | **PK**（UUIDv7） |
| `team_uuid` | TEXT | NOT NULL（全局/bootstrap 事件可用 sentinel team 或 NULL——v1：**业务事件强制 team**；系统事件允许 `team_uuid` 特殊值 `00000000-0000-0000-0000-000000000000` 仅 ops） |
| `trace_uuid` | TEXT | NOT NULL |
| `event_type` | TEXT | NOT NULL（见下方类型族） |
| `severity` | TEXT | NOT NULL CHECK ∈ `task,execution,process,intake,generation,gate,outbox,object,vector,registry,ops` |
| `severity` | TEXT | NOT NULL DEFAULT `'info'` CHECK ∈ `debug,info,warn,error` |
| `task_uuid` | TEXT | NULL |
| `execution_uuid` | TEXT | NULL |
| `process_uuid` | TEXT | NULL |
| `subject_kind` | TEXT | NULL（如 `intake_item`,`gate`,`generation_artifact`） |
| `subject_uuid` | TEXT | NULL |
| `causation_event_uuid` | TEXT | NULL（因果链） |
| `actor_kind` | TEXT | NOT NULL CHECK ∈ `system,worker,upstream,operator` |
| `actor_id` | TEXT | NULL（worker_id / token fingerprint，非明文 secret） |
| `severity_before` | TEXT | NULL（状态变迁时） |
| `severity_after` | TEXT | NULL |
| `summary` | TEXT | NOT NULL（短人类可读，≤512） |
| `payload_digest` | TEXT | NOT NULL（对 `payload_json` 的 sha256 hex；空载荷用固定 empty digest） |
| `payload_json` | TEXT | NOT NULL DEFAULT `'{}'`（**bounded**；禁止正文/secret；大对象只放 handle/digest） |
| `schema_version` | TEXT | NOT NULL DEFAULT `'mkb.domain-event.v1'` |
| `occurred_at` | TEXT | NOT NULL |
| `recorded_at` | TEXT | NOT NULL |
| `payload_extra` | TEXT | NOT NULL DEFAULT `'{}'` |

**event_type 最小闭集（可扩展注册，禁止自由字符串漂移）**

| 族 | 示例 types |
|---|---|
| task | `task.created`,`task.status_changed`,`task.cancel_requested`,`task.retry_accepted`,`task.soft_deleted` |
| execution | `execution.created`,`execution.status_changed`,`execution.waiting_entered`,`execution.waiting_released` |
| process | `process.materialized`,`process.claimed`,`process.status_changed`,`process.outcome_accepted`,`process.lease_recovered` |
| intake | `intake.snapshot_accepted`,`intake.item_transitioned`,`intake.candidate_sealed`,`intake.candidate_accepted` |
| generation | `generation.artifact_accepted`,`generation.pointer_cas`,`generation.invocation_recorded` |
| gate | `gate.opened`,`gate.decided`,`gate.terminal` |
| object | `object.registered`,`object.ref_released`,`object.deleted` |
| vector | `vector.upserted`,`vector.soft_deleted`,`vector.rebuild_started` |
| ops | `ops.repair_applied`,`ops.readiness_changed`,`ops.alert_raised`,`ops.retention_policy_changed`,`config.ops_reload`,`config.override_applied` |
| registry | `registry.bootstrap_completed`,`registry.digest_mismatch` |
| outbox | `outbox.enqueued`（可选；高频可采样）,`outbox.dead`（可选低频） |
| security | **不写本表** → 见 `mkb_security_audit_events` |

> **扩展登记纪律（v1.2 校准）**：上表为 event_type **物理/合同 SSOT 最小闭集**。S14/S15 仅可提议；新增 type **必须** change-request 回填本表 + S15 DomainEventWriter 登记。未登记 type → 写入失败（`OBS_EVENT_PAYLOAD_INVALID`）。**禁止**各域 formal 私自发明 type 名。payload_json 服从全局 redaction（S16-T056）与各 type 有界 allowlist（S15-E01）。

**索引**

| 名 | 定义 | 类 |
|---|---|---|
| `ix_de_team_time` | (`team_uuid`,`occurred_at`,`event_uuid`) | 租户时间线 |
| `ix_de_trace` | (`trace_uuid`,`occurred_at`,`event_uuid`) | **trace 拉全链路** |
| `ix_de_task` | (`team_uuid`,`task_uuid`,`occurred_at`) | 主体 |
| `ix_de_execution` | (`team_uuid`,`execution_uuid`,`occurred_at`) | 主体 |
| `ix_de_process` | (`team_uuid`,`process_uuid`,`occurred_at`) | 主体 |
| `ix_de_type` | (`team_uuid`,`event_type`,`occurred_at`) | 过滤 |
| `ix_de_subject` | (`team_uuid`,`subject_kind`,`subject_uuid`,`occurred_at`) | 反查 |

**规则**

1. append-only：禁止 UPDATE 业务列；允许未来 S15 归档 DELETE（整段 retention）。  
2. 不得仅凭 event 恢复状态而不读业务表。  
3. `payload_json` 经 contracts 校验（`DomainEventPayload`）；非法不得入 TX。

#### 3.1.4 `mkb_ops_diagnostic_logs`（append-only · 非 SSOT · 短 retention）

> 对标 `smind_logs`，**降维**为 leaf-worker 诊断面。  
> **禁止** 承载唯一状态真相、唯一 proof、唯一 route 决策。

| 列 | 类型 | 约束 |
|---|---|---|
| `log_uuid` | TEXT | **PK** |
| `team_uuid` | TEXT | NULL（无 team 上下文可空） |
| `trace_uuid` | TEXT | NULL |
| `task_uuid` / `execution_uuid` / `process_uuid` | TEXT | NULL |
| `log_level` | TEXT | NOT NULL CHECK ∈ `debug,info,warn,error` |
| `log_code` | TEXT | NOT NULL（稳定机器码，如 `PROC_CLAIM_CONFLICT`） |
| `log_message` | TEXT | NOT NULL（≤1024） |
| `calling_module` | TEXT | NOT NULL（如 `runtime.claim`,`s06.structurizer`） |
| `calling_worker` | TEXT | NOT NULL DEFAULT `'mkb-leaf'` |
| `payload_json` | TEXT | NOT NULL DEFAULT `'{}'`（bounded；禁 secret/正文） |
| `payload_digest` | TEXT | NOT NULL |
| `occurred_at` | TEXT | NOT NULL |
| `payload_extra` | TEXT | NOT NULL DEFAULT `'{}'` |

**写入策略**：优先 **同 TX** 当与业务变更绑定；纯诊断（重试抖动、模型 HTTP 细节）允许 commit 后 best-effort insert（失败只打 stderr/metrics，不回滚业务）。

**索引**

| 名 | 定义 |
|---|---|
| `ix_diag_trace` | (`trace_uuid`,`occurred_at`) |
| `ix_diag_team_time` | (`team_uuid`,`occurred_at`) WHERE team NOT NULL |
| `ix_diag_level_time` | (`log_level`,`occurred_at`) WHERE level IN (`warn`,`error`) |
| `ix_diag_code` | (`log_code`,`occurred_at`) |
| `ix_diag_process` | (`process_uuid`,`occurred_at`) WHERE process NOT NULL |

**retention**：默认短于 domain_events（数值归 S15；建议诊断 7–30d，events 更长）。

#### 3.1.5 `mkb_security_audit_events`（append-only · 非 SSOT）

> 对标 python `audit_logs` 子集 + S02「认证/schema 失败不写业务表」。

| 列 | 类型 | 约束 |
|---|---|---|
| `audit_uuid` | TEXT | **PK** |
| `team_uuid` | TEXT | NULL（team-not-registered 时可空） |
| `trace_uuid` | TEXT | NULL |
| `request_id` | TEXT | NULL |
| `actor_kind` | TEXT | NOT NULL CHECK ∈ `anonymous,internal_token,system,operator` |
| `actor_fingerprint` | TEXT | NULL（token hash，非明文） |
| `action` | TEXT | NOT NULL（如 `task.create`,`gate.decide`,`team.access`） |
| `outcome` | TEXT | NOT NULL CHECK ∈ `allowed,denied` |
| `denial_code` | TEXT | NULL（denied 时 NOT NULL） |
| `http_status` | INTEGER | NULL |
| `target_kind` | TEXT | NULL |
| `target_uuid` | TEXT | NULL |
| `remote_addr_hash` | TEXT | NULL（可选；禁存原始 IP 若政策要求） |
| `summary` | TEXT | NOT NULL |
| `payload_json` | TEXT | NOT NULL DEFAULT `'{}'`（禁 token 原文/secret） |
| `payload_digest` | TEXT | NOT NULL |
| `occurred_at` | TEXT | NOT NULL |
| `payload_extra` | TEXT | NOT NULL DEFAULT `'{}'` |

**索引**

| 名 | 定义 |
|---|---|
| `ix_sec_time` | (`occurred_at`,`audit_uuid`) |
| `ix_sec_team_time` | (`team_uuid`,`occurred_at`) |
| `ix_sec_outcome` | (`outcome`,`occurred_at`) |
| `ix_sec_denial` | (`denial_code`,`occurred_at`) WHERE outcome=`denied` |
| `ix_sec_actor` | (`actor_fingerprint`,`occurred_at`) WHERE actor_fingerprint NOT NULL |
| `ix_sec_trace` | (`trace_uuid`,`occurred_at`) WHERE trace NOT NULL |

**规则**：`denied` 必须写本表；**不得** 因审计插入失败而“改写”业务成功语义——若与业务同请求且业务未写库，审计失败可导致请求 5xx（fail-closed admission 路径）。

---

### 3.2 `runtime`

#### 3.2.1 `mkb_tasks`

| 列族 | 列 | 约束摘要 |
|---|---|---|
| Identity | `team_uuid`, `task_uuid` | **PK (`team_uuid`,`task_uuid`)** |
| | `trace_uuid` | NOT NULL |
| | `schema_version` | NOT NULL |
| | `request_intent` | NOT NULL |
| | `creation_fingerprint` | NOT NULL |
| Audit link | `audit_bound` | 恒 1；由 TX-01 保证 audit 行存在 |
| Mutable desc | `title`, `description`, `priority` | `priority` CHECK ∈ `low,normal,high,urgent` DEFAULT `normal` |
| Lifecycle | `status` | CHECK ∈ `queued,running,cancelling,succeeded,failed,cancelled` |
| | `row_revision` | NOT NULL INTEGER CAS |
| | `current_generation` | NOT NULL INTEGER ≥ 1 |
| | `current_root_execution_uuid` | NULL |
| | `cancel_requested_at` | NULL |
| Scatter proj | `intake_snapshot_uuid`, `change_set_uuid` | NULL |
| | `cnt_total/required/active/succeeded/failed/cancelled/skipped` | INTEGER NOT NULL DEFAULT 0 |
| Summary | `result_ref`, `error_code`, `error_message`, `proof_ref` | NULL/TEXT |
| Time | `received_at`, `started_at`, `completed_at`, `updated_at`, `deleted_at` | |
| Soft-delete | `deleted_actor`, `deleted_reason` | NULL |
| | `deadline_at` | NULL |
| | `payload_extra` | DEFAULT `{}` |

**索引**

| 名 | 定义 | 类 |
|---|---|---|
| `ux_mkb_tasks_fingerprint` | UNIQUE(`team_uuid`,`task_uuid`,`creation_fingerprint`) — 或应用层：同 PK 异 fingerprint 冲突 | 幂等 |
| `ix_mkb_tasks_list` | (`team_uuid`, `created_at` DESC, `task_uuid` DESC) | 租户列表 |
| `ix_mkb_tasks_status` | (`team_uuid`, `status`, `updated_at`) | 状态 |
| `ix_mkb_tasks_intent` | (`team_uuid`, `request_intent`, `created_at`) | 过滤 |
| `ix_mkb_tasks_trace` | (`trace_uuid`) | 反查 |
| `ix_mkb_tasks_root_exec` | (`team_uuid`, `current_root_execution_uuid`) | 主体 |

#### 3.2.2 `mkb_task_audits`

| 列 | 约束 |
|---|---|
| `team_uuid`, `task_uuid` | **PK**；**FK → mkb_tasks** |
| `request_envelope_digest` | NOT NULL |
| `strict_payload_json` | NOT NULL（immutable 快照；非运行状态） |
| `caller_token_fingerprint` | NOT NULL（非明文 token） |
| `received_at` | NOT NULL |
| `payload_extra` | DEFAULT `{}` |

**索引**：PK 足够；`ix_mkb_task_audits_received` (`team_uuid`,`received_at`) 可选运维。

#### 3.2.3 `mkb_task_restarts`

| 列 | 约束 |
|---|---|
| `restart_uuid` | PK |
| `team_uuid` | NOT NULL |
| `restart_scope` | CHECK ∈ `atomic_intake_item,full_task` |
| `source_task_uuid` | NOT NULL |
| `source_generation` | INTEGER NOT NULL |
| `source_root_execution_uuid` | NULL |
| `intake_item_uuid` | NULL（atomic 时 NOT NULL 应用层） |
| `intake_revision_uuid` | NULL |
| `restart_task_uuid` | NULL（rejected 可空） |
| `target_generation` | NULL |
| `target_root_execution_uuid` | NULL |
| `causation_trace_uuid` | NOT NULL |
| `command_fingerprint` | NOT NULL |
| `admission_outcome` | CHECK ∈ `accepted,rejected` |
| `decision_code` | NOT NULL |
| `reason` | NULL |
| `requested_at`, `decided_at` | NOT NULL |
| `payload_extra` | DEFAULT `{}` |

**唯一（partial / 应用+索引）**

| 条件 | UNIQUE |
|---|---|
| accepted ∧ scope=atomic | (`team_uuid`,`restart_task_uuid`,`restart_scope`) WHERE accepted |
| accepted ∧ scope=full | (`team_uuid`,`source_task_uuid`,`source_generation`,`restart_scope`)；(`team_uuid`,`source_task_uuid`,`target_generation`,`restart_scope`) |

SQLite partial unique 示例：

```sql
CREATE UNIQUE INDEX ux_restart_atomic_accepted
  ON mkb_task_restarts(team_uuid, restart_task_uuid, restart_scope)
  WHERE admission_outcome = 'accepted' AND restart_scope = 'atomic_intake_item';

CREATE UNIQUE INDEX ux_restart_full_src_gen
  ON mkb_task_restarts(team_uuid, source_task_uuid, source_generation, restart_scope)
  WHERE admission_outcome = 'accepted' AND restart_scope = 'full_task';

CREATE UNIQUE INDEX ux_restart_full_tgt_gen
  ON mkb_task_restarts(team_uuid, source_task_uuid, target_generation, restart_scope)
  WHERE admission_outcome = 'accepted' AND restart_scope = 'full_task';
```

**二级索引**（对齐 S02）

- (`team_uuid`, `source_task_uuid`, `requested_at`, `restart_uuid`)
- (`team_uuid`, `restart_task_uuid`, `requested_at`, `restart_uuid`)
- (`team_uuid`, `intake_item_uuid`, `requested_at`, `restart_uuid`)
- (`team_uuid`, `restart_scope`, `admission_outcome`, `requested_at`, `restart_uuid`)
- (`causation_trace_uuid`)

#### 3.2.4 `mkb_executions`

| 列族 | 主要列 | 约束 |
|---|---|---|
| Identity | `execution_uuid` PK；`team_uuid`; `task_uuid`; `trace_uuid`; `generation` | FK 逻辑 → tasks |
| Tree | `root_execution_uuid`; `parent_execution_uuid`; `retry_of_execution_uuid`; `execution_role` | root 自洽 |
| Target | `target_kind`; `target_uuid`; `intake_snapshot_uuid`; `intake_snapshot_digest` | |
| Binding | `workflow_uuid`; `workflow_revision_uuid`; `compiled_digest`; `resolver_decision_digest`; `domain_binding_digest`; `s05_binding_digest` | NOT NULL（创建时） |
| Control | `status` CHECK 八态；`row_revision`; `phase_key`; `waiting_reason`; `waiting_ref`; `next_wake_at` | waiting 时 reason/ref 完整 |
| Focus | `current_process_uuid` | NULL |
| Scatter | `manifest_ref`; `manifest_digest`; counts… | |
| Aggregates | process/child/retry counters | NOT NULL defaults |
| Cancel | `cancel_requested_at`; `cancel_command_revision`; `cancel_converged_at` | |
| Result | `result_ref`; `publication_proof_ref`; `final_error_*` | |
| Summary | `terminal_summary_digest`; `summary_completed_at`; `phase_history_ref` | |
| Time | `created_at`…`updated_at` | |
| | `payload_extra` | |

**Execution 八态 CHECK**：`pending,ready,running,waiting,succeeded,failed,cancelled,compensating`（以 S03 正式拼写为准；实现前与 S03 字面 **逐字对齐**）。

**索引**

| 名 | 定义 | 类 |
|---|---|---|
| `ux_mkb_exec_task_gen_root` | UNIQUE(`team_uuid`,`task_uuid`,`generation`,`execution_uuid`) 应用：每 generation 一个 root | 幂等 |
| `ix_mkb_exec_task` | (`team_uuid`,`task_uuid`,`generation`,`created_at`) | 列表 |
| `ix_mkb_exec_status` | (`team_uuid`,`status`,`next_wake_at`) | 队列 |
| `ix_mkb_exec_root` | (`team_uuid`,`root_execution_uuid`) | 树 |
| `ix_mkb_exec_parent` | (`team_uuid`,`parent_execution_uuid`) | 树 |
| `ix_mkb_exec_workflow_rev` | (`workflow_revision_uuid`) | 反查 |
| `ux_mkb_exec_child_manifest` | UNIQUE(`root_execution_uuid`,`manifest_revision`,`target_uuid`) WHERE required child | 幂等 fan-out |

#### 3.2.5 `mkb_processes`

| 列族 | 主要列 | 约束 |
|---|---|---|
| Identity | `process_uuid` PK；`team_uuid`; `execution_uuid`; `task_uuid` | |
| Step | `workflow_step_uuid`; `step_key`; `process_key`; `process_contract_version` | |
| Materialization | `materialization_key`; `route_decision_digest`; `fan_out_item_key`; `requiredness` | **UNIQUE(`execution_uuid`,`workflow_step_uuid`,`materialization_key`)** |
| Spec | `process_spec_digest`; `input_manifest_ref`; `input_manifest_digest`; `control_snapshot_ref`; `proof_kind` | |
| State | `status` 八态；`row_revision`; `available_at`; `priority_rank`; `deadline_at` | |
| **Claim** | `claim_token_hash`; `lease_owner`; `lease_expires_at`; `fencing_generation`; `heartbeat_at` | claim 时非空 |
| Counters | `delivery_count`; `recovery_count`; `retry_count`; `max_retries`; `max_recoveries` | max 非空固化 |
| Retry | `next_retry_at`; `last_failure_retryability`; `backoff_policy_json` | |
| Outcome | `accepted_outcome_digest`; `output_manifest_ref`; `output_manifest_digest`; `proof_ref`; `proof_digest` | |
| Error | `error_class`; `error_code`; `error_message`; `error_details_ref`; `failure_disposition` | |
| Cleanup | `cleanup_eligible_at`; `cleanup_fence_digest` | |
| Time | `created_at`… | |
| | `payload_extra` | |

**Process 八态**：与 S03 逐字对齐（含 `ready,claimed,running,retry_wait,succeeded,failed,cancelled,…`）。

**索引**

| 名 | 定义 | 类 |
|---|---|---|
| `ux_mkb_proc_materialization` | UNIQUE(`execution_uuid`,`workflow_step_uuid`,`materialization_key`) | 幂等 |
| `ix_mkb_proc_claim_queue` | (`status`, `available_at`, `priority_rank`) WHERE status 可 claim | **队列** |
| `ix_mkb_proc_team_status` | (`team_uuid`,`status`,`available_at`) | 租户队列 |
| `ix_mkb_proc_execution` | (`team_uuid`,`execution_uuid`,`created_at`) | 主体 |
| `ix_mkb_proc_lease` | (`status`,`lease_expires_at`) WHERE claimed-like | recovery |
| `ix_mkb_proc_fence` | (`process_uuid`,`fencing_generation`) | 校验 |

#### 3.2.6 `mkb_outbox`

| 列 | 约束 |
|---|---|
| `outbox_id` | PK（UUIDv7） |
| `team_uuid` | NOT NULL |
| `kind` | NOT NULL（如 `wake_process`,`vectorize_construct`,`vector_purge_generation?`,`intake_schedule_child`,`gate_resume`,…）；**`vectorize_structure` 名可保留，v1 禁止消费**（S08-T003 / D05） |
| `topic` | NULL（可选细分） |
| `payload_json` | NOT NULL（**typed 经 contracts 校验后的 JSON**；禁非法体入队 T-O-153） |
| `payload_digest` | NOT NULL |
| `dedupe_key` | NOT NULL |
| `status` | CHECK ∈ `pending,in_flight,done,dead` |
| `attempts` | INTEGER NOT NULL DEFAULT 0 |
| `available_at` | NOT NULL |
| `lease_owner` | NULL |
| `lease_expires_at` | NULL |
| `last_error` | NULL |
| `created_at`; `updated_at` | NOT NULL |
| `payload_extra` | DEFAULT `{}` |

**唯一**：UNIQUE(`team_uuid`,`dedupe_key`)。

**索引**

| 名 | 定义 | 类 |
|---|---|---|
| `ux_mkb_outbox_dedupe` | UNIQUE(`team_uuid`,`dedupe_key`) | 幂等 |
| `ix_mkb_outbox_dispatch` | (`status`,`available_at`,`created_at`) WHERE status IN (`pending`,`in_flight`) | **队列** |
| `ix_mkb_outbox_team` | (`team_uuid`,`created_at`) | 租户 |
| `ix_mkb_outbox_kind` | (`kind`,`status`,`available_at`) | 运维 |

#### 3.2.7 `mkb_execution_gates`

| 列 | 约束 |
|---|---|
| `gate_uuid` | PK |
| `team_uuid`; `task_uuid`; `execution_uuid`; `generation` | NOT NULL |
| `gate_kind` | NOT NULL（如 `human_review`） |
| `status` | CHECK ∈ `open,released,rejected,superseded` |
| `gate_revision` | INTEGER NOT NULL DEFAULT 0 |
| `opened_at`; `terminal_at` | |
| `workflow_revision_uuid`; `binding_digest` | |
| `payload_extra` | |

**索引**：(`team_uuid`,`task_uuid`,`status`,`opened_at`)；(`execution_uuid`)；(`team_uuid`,`status`) WHERE open。

#### 3.2.8 `mkb_execution_gate_targets`

| 列 | 约束 |
|---|---|
| `gate_uuid` | PK/FK → gates（1:1） |
| `team_uuid` | NOT NULL |
| `target_digest` | NOT NULL |
| `review_target_json` | NOT NULL（immutable 复合 ReviewTarget 快照） |
| `clean_artifact_digest` | NOT NULL |
| `preflight_outcome_ref` | NULL |
| `intake_refs_json` | NOT NULL |
| `created_at` | NOT NULL |
| `payload_extra` | |

**索引**：PK；(`team_uuid`,`target_digest`)。

#### 3.2.9 `mkb_execution_gate_decisions`

| 列 | 约束 |
|---|---|
| `decision_uuid` | PK |
| `gate_uuid` | NOT NULL |
| `team_uuid` | NOT NULL |
| `expected_gate_revision` | NOT NULL |
| `action` | CHECK ∈ `approve,reject,reclean`（与 S05 最终 enum 对齐） |
| `actor_fingerprint` | NOT NULL |
| `idempotency_key` | NOT NULL |
| `target_digest` | NOT NULL |
| `decision_digest` | NOT NULL |
| `created_at` | NOT NULL |
| `payload_extra` | |

**唯一**：UNIQUE(`gate_uuid`,`idempotency_key`)；UNIQUE(`decision_uuid`)。  
**索引**：(`gate_uuid`,`created_at`)；(`team_uuid`,`created_at`)。

---

### 3.3 `registry`

#### 3.3.1 Workflow 七表

**`mkb_workflow_registry`**

| 列 | 约束 |
|---|---|
| `workflow_uuid` | PK |
| `workflow_key` | UNIQUE NOT NULL（创建后不可改） |
| `domain_key` | NOT NULL |
| `purpose_key`; `execution_role`; `selector_key`; `selector_priority` | |
| `read_exposure` | CHECK ∈ `internal,readable` |
| `registry_status` | CHECK ∈ `enabled,disabled,deprecated` |
| `active_revision_uuid` | NULL；enabled 时应用层非空 |
| `display_name`; `description` | |
| `created_at`; `updated_at`; `created_by_origin` | |
| `payload_extra` | |

索引：`ux_workflow_key`；(`registry_status`,`selector_priority`)；(`purpose_key`,`registry_status`)。

**`mkb_workflow_revisions`**

| 列 | 约束 |
|---|---|
| `workflow_revision_uuid` | PK |
| `workflow_uuid` | NOT NULL FK |
| `revision_number` | INTEGER NOT NULL |
| `schema_version`; `capability_registry_digest` | |
| `registration_*` provenance 列 | |
| `canonical_definition_digest`; `compiled_digest` | NOT NULL |
| `registered_at`; `activated_at`; `registration_trace_uuid` | |
| `payload_extra` | |

UNIQUE(`workflow_uuid`,`revision_number`)。  
索引：(`compiled_digest`)；(`workflow_uuid`,`registered_at`)。

**`mkb_workflow_steps`**

| 列 | 约束 |
|---|---|
| `workflow_step_uuid` | PK |
| `workflow_revision_uuid` | FK |
| `step_key` | |
| `step_kind` | CHECK ∈ `start,process,control,join,terminal` |
| `process_key`; `process_contract_version` | process 时非空 |
| `phase_key`; `requiredness`; `terminal_kind`; `order_hint`; `display_name` | |
| `payload_extra` | |

UNIQUE(`workflow_revision_uuid`,`step_key`)。

**`mkb_workflow_routes`**

| 列 | 约束 |
|---|---|
| `workflow_route_uuid` | PK |
| `workflow_revision_uuid` | FK |
| `route_key` | |
| `from_step_uuid`; `to_step_uuid` | 同 revision |
| `route_kind`; `outcome_selector`; `priority`; `guard_group_key` | |
| `join_mode`; `predecessor_requiredness` | |
| `payload_extra` | |

UNIQUE(`workflow_revision_uuid`,`route_key`)；UNIQUE(`workflow_revision_uuid`,`from_step_uuid`,`outcome_selector`,`priority`)。

**`mkb_workflow_bindings`**

| 列 | 约束 |
|---|---|
| `workflow_binding_uuid` | PK |
| `workflow_revision_uuid`; `workflow_step_uuid` | |
| `binding_kind` | CHECK ∈ `context,input,output,parameter` |
| `slot_name`; `value_type`; `schema_ref`; `required`; `multiplicity` | |
| `binding_source_kind` + source refs | |
| typed value 列六选一 | XOR CHECK |
| `payload_extra` | |

UNIQUE(`workflow_step_uuid`,`binding_kind`,`slot_name`)。

**`mkb_workflow_controls`**

| 列 | 约束 |
|---|---|
| `workflow_control_uuid` | PK |
| `workflow_revision_uuid` | |
| `scope_type` | CHECK ∈ `revision,step,route` |
| `workflow_step_uuid`; `workflow_route_uuid` | 按 scope XOR |
| timeout/lease/heartbeat/retry/cancel/concurrency 列 | 正整数 CHECK |
| `payload_extra` | |

索引：(`workflow_revision_uuid`,`scope_type`)。

**`mkb_workflow_guards`**

| 列 | 约束 |
|---|---|
| `workflow_guard_uuid` | PK |
| `workflow_revision_uuid` | |
| `scope_type`; `scope_key`; `guard_group_key`; `group_mode`; `order_index` | |
| `predicate_type`; `operand_kind`; `operand_ref`; `operator` | allowlist |
| `expected_type` + typed expected | XOR |
| `failure_code`; `failure_disposition` | |
| `payload_extra` | |

UNIQUE(`workflow_revision_uuid`,`guard_group_key`,`order_index`)。

#### 3.3.2 Definition registries

**公共模式**（下列表共用）：

- 全局（非 team 分区）或 code-owned；  
- UNIQUE(`*_key`,`definition_version`)；  
- `definition_digest` NOT NULL；同 version 异 digest → bootstrap fail；  
- `registered_at`; `payload_extra`；  
- 可选 `definition_body_json`（immutable；运行解释仍以 contracts/digest 为准）。

| 表 | 键列 | 额外要点 |
|---|---|---|
| `mkb_intake_semantic_definitions` | `semantic_key`,`definition_version` | `value_kind`; fingerprint/route flags |
| `mkb_intake_action_definitions` | `action_key`,`definition_version` | effect mask；from-state mask |
| `mkb_source_kind_definitions` | `source_kind`,`definition_version` | cardinality；capability eligibility digests。**D08**：eligibility 必须列出精确 acquire/clean keys（含 `clean.extract.web\|pdf_llm\|doc_llm`）；`registered_api` 行须绑定 provider-operation manifest digest。**禁止**把 provider 做成第五 kind |
| `mkb_preflight_profile_definitions` | `profile_key`,`definition_version` | check-set digest |
| `mkb_structure_schema_definitions` | `schema_key`,`schema_version` | kernel/extension schema digests；media contracts |
| `mkb_construction_schema_definitions` | `schema_key`,`schema_version` | structure schema range；channel contracts |

**索引**：各表 UNIQUE(key,version)；(`definition_digest`)。

#### 3.3.2b D08 校准：FilterMeta 语义键与 proposed provider/strategy 表

> **闭集纪律**：本节 **不**把 required 表数从 55 改为 58。下列表与列是 **D08-v0.1 提出的重排要求**；升 required 必须 D04 reopen + owner `T-O`。未 reopen 前，等价合同落在 `src/contracts/intake` + code-owned bootstrap digest（**禁止**用 `payload_extra` 冒充 schema SSOT）。

**SemanticDefinition 应登记的 FilterMeta 五维**（进现表 `mkb_intake_semantic_definitions`，不新建表）：

| `semantic_key` | 说明 |
|---|---|
| `realm` | 如 `tax_china` / `realestate_on_market` / `realestate` |
| `type` | 如税局文件类型、`sale_mode`、`listing` |
| `channel` | 栏目 / 物业类型 / buy\|rent\|sold |
| `source_name` | 站点或 agency 名 |
| `is_active` | `0\|1`；规则按 **operation version** |

CandidateMember 合同必须携带 `content_digest` 与 `meta_digest`（D08-T008）。可暂存于 `mkb_intake_candidate_pages` 的 sealed payload，但 contracts 形状一等，不得只写 extra。

**Proposed 表列（权威叙述在 D08 §4.4；此处仅钉物理意图）：**

- `mkb_intake_provider_definitions`：`(provider_key, definition_version)` + digest + `source_kind='registered_api'`  
- `mkb_intake_provider_operations`：`(provider_key, operation_key, definition_version)` + request/envelope/member/normalizer digest + cardinality + secret **slot 名**  
- `mkb_intake_clean_strategy_definitions`：`(strategy_key, version)` + channel + acquire/clean capability + llm/browser required + optional prompt pointer + `max_input_bytes`

#### 3.3.3 `mkb_prompt_hash_pointers`

| 列 | 约束 |
|---|---|
| `prompt_key` | NOT NULL |
| `prompt_version` | NOT NULL |
| `git_relative_path` | NOT NULL（相对 `data/prompts/`） |
| `content_sha256` | NOT NULL（文件字节 hash） |
| `registered_at` | NOT NULL |
| `payload_extra` | |

UNIQUE(`prompt_key`,`prompt_version`)；UNIQUE(`git_relative_path`,`content_sha256`)。  
**禁止** `body_text` 列。

---

### 3.4 `intake`

#### 3.4.1 十张 canonical

**`mkb_intake_sources`**

| 列 | 约束 |
|---|---|
| `team_uuid`, `intake_source_uuid` | **PK** |
| `source_kind`; `source_kind_definition_version`; `source_kind_definition_digest` | NOT NULL |
| `source_descriptor_ref`; `source_descriptor_digest` | |
| `connector_config_ref`; `secret_ref` | secret 仅 ref |
| `accepts_new_snapshots` | BOOL NOT NULL |
| `row_revision` | INTEGER NOT NULL |
| `created_at`; `payload_extra` | |

索引：(`team_uuid`,`source_kind`,`created_at`)；(`team_uuid`,`accepts_new_snapshots`)。

**`mkb_intake_snapshots`**（immutable）

| 列 | 约束 |
|---|---|
| `team_uuid`, `intake_snapshot_uuid` | PK |
| `intake_source_uuid` | NOT NULL |
| `observation_key`; `observation_fingerprint` | NOT NULL |
| `candidate_root_digest`; `completeness` CHECK ∈ `complete,partial` | |
| `authoritative_scope_ref`; `source_validator_evidence_ref` | |
| `preflight_outcome_ref`; `preflight_outcome_digest`; `s05_binding_digest` | |
| `observed_at`; `accepted_at`; `producer_execution_uuid` | |
| `raw_artifact_uuid` | NULL |
| `payload_extra` | |

UNIQUE(`team_uuid`,`intake_source_uuid`,`observation_key`) 或 fingerprint fence（实现选 observation fence 唯一）。  
索引：(`team_uuid`,`intake_source_uuid`,`accepted_at`)；(`producer_execution_uuid`)。

**`mkb_intake_items`**

| 列 | 约束 |
|---|---|
| `team_uuid`, `intake_item_uuid` | PK |
| `intake_source_uuid` | NOT NULL |
| `normalized_external_key` | NOT NULL |
| `lifecycle_state` | CHECK ∈ `active,deactivated,deleted` |
| `latest_revision_uuid`; `serving_revision_uuid` | NULL；deleted/deactivated 时 serving NULL |
| `row_revision` | CAS |
| `created_at`; `deactivated_at`; `deleted_at` | |
| `payload_extra` | |

UNIQUE(`team_uuid`,`intake_source_uuid`,`normalized_external_key`)。  
索引：(`team_uuid`,`lifecycle_state`,`updated_at` 若有)；(`team_uuid`,`serving_revision_uuid`)。

**`mkb_intake_revisions`**（immutable）

| 列 | 约束 |
|---|---|
| `team_uuid`, `intake_revision_uuid` | PK |
| `intake_item_uuid` | NOT NULL |
| `revision_ordinal` | INTEGER NOT NULL |
| `predecessor_revision_uuid` | NULL |
| `revision_fingerprint` | NOT NULL |
| `creation_action_key`; `creation_action_version` | |
| `source_snapshot_uuid` | NOT NULL |
| `created_at`; `payload_extra` | |

UNIQUE(`team_uuid`,`intake_item_uuid`,`revision_ordinal`)；UNIQUE(`team_uuid`,`intake_item_uuid`,`revision_fingerprint`)。  
索引：(`team_uuid`,`source_snapshot_uuid`)。

**`mkb_intake_artifacts`**（immutable）

| 列 | 约束 |
|---|---|
| `team_uuid`, `intake_artifact_uuid` | PK |
| `owner_snapshot_uuid`; `owner_revision_uuid` | **XOR** CHECK 恰一个非空 |
| `artifact_role`; `media_type` | NOT NULL |
| `digest_algorithm`; `content_digest`; `size_bytes` | NOT NULL |
| `logical_handle` | NOT NULL（`mkbobj:…`，非 path） |
| `stored_object_uuid` | NULL FK 逻辑 → stored_objects |
| `producer_execution_uuid`; `producer_process_uuid` | NULL |
| `retention_class` | NULL |
| `created_at`; `payload_extra` | |

索引：(`team_uuid`,`content_digest`)；(`owner_snapshot_uuid`)；(`owner_revision_uuid`)；(`stored_object_uuid`)。

**`mkb_intake_snapshot_memberships`**（immutable）

| 列 | 约束 |
|---|---|
| `team_uuid`, `intake_snapshot_uuid`, `member_ordinal` | PK 或 UNIQUE |
| `normalized_external_key` | NOT NULL |
| `intake_item_uuid`; `observed_revision_uuid` | nullable per decision |
| `decision_kind` | NOT NULL（enum 与 S04 最终 spelling 对齐） |
| `required` | BOOL |
| `decision_digest` | NOT NULL |
| `created_at`; `payload_extra` | |

UNIQUE(`team_uuid`,`intake_snapshot_uuid`,`normalized_external_key`)；UNIQUE(…,`member_ordinal`)。  
索引：(`team_uuid`,`intake_item_uuid`)；(`decision_kind`)。

**`mkb_intake_revision_semantics`**（immutable）

| 列 | 约束 |
|---|---|
| `team_uuid`, `intake_revision_uuid`, `semantic_key` | PK |
| `definition_version` | NOT NULL |
| `value_digest` | NOT NULL |
| scalar columns / `value_artifact_uuid` | kind XOR |
| `created_at`; `payload_extra` | |

索引：(`semantic_key`,`definition_version`)。

**`mkb_intake_item_transitions`**（append-only）

| 列 | 约束 |
|---|---|
| `transition_uuid` | PK |
| `team_uuid`; `intake_item_uuid` | NOT NULL |
| `action_key`; `action_version` | |
| `before_lifecycle`; `after_lifecycle` | |
| `before_latest`; `after_latest`; `before_serving`; `after_serving` | |
| `item_revision_before`; `item_revision_after` | |
| causation task/execution/process refs | |
| `proof_ref`; `proof_digest`; `policy_ref` | |
| `transition_fence` | NOT NULL |
| `occurred_at`; `payload_extra` | |

索引：(`team_uuid`,`intake_item_uuid`,`occurred_at`)；(`transition_fence`)。

#### 3.4.2 Supporting

**`mkb_intake_candidate_sets`**

| 列 | 约束 |
|---|---|
| `candidate_set_uuid` | PK |
| `team_uuid`; `intake_source_uuid`; `producer_execution_uuid` | NOT NULL |
| digests: source/capability/S05 binding/observation | |
| `staging_state` | CHECK ∈ `open,sealed,accepted,abandoned` |
| counts/bytes/pages 期望与观察 | |
| `root_digest`; `preflight_outcome_ref` | |
| `seal_at`; `expiry_at`; `accepted_snapshot_uuid` | |
| `row_revision`; `payload_extra` | |

UNIQUE(`team_uuid`,`producer_execution_uuid`) 或 fence 唯一（S05 binding）。  
索引：(`staging_state`,`expiry_at`)；(`team_uuid`,`intake_source_uuid`,`created_at`)。

**`mkb_intake_candidate_pages`**

| 列 | 约束 |
|---|---|
| `candidate_set_uuid`, `page_ordinal` | PK |
| `team_uuid` | NOT NULL |
| member range；`page_digest` | NOT NULL |
| `sealed_payload_ref`; staged artifact refs | |
| `payload_extra` | |

索引：(`candidate_set_uuid`)；(`page_digest`)。

**`mkb_intake_change_sets`**

| 列 | 约束 |
|---|---|
| `change_set_uuid` | PK |
| `team_uuid`; `intake_snapshot_uuid` | |
| `change_set_digest` | NOT NULL UNIQUE per team+snapshot |
| `created_at`; `payload_extra` | |

**`mkb_intake_change_set_facts`**

| 列 | 约束 |
|---|---|
| `fact_uuid` | PK |
| `change_set_uuid`; `team_uuid` | |
| `fact_kind`; `fact_ordinal` | |
| typed refs: item/revision/semantic/absence | |
| `fact_digest` | NOT NULL |
| `payload_extra` | |

UNIQUE(`change_set_uuid`,`fact_ordinal`)；索引 (`change_set_uuid`,`fact_kind`)。

**`mkb_intake_repair_intents` / `mkb_intake_cleanup_intents` / `mkb_intake_cleanup_proofs`**

| 表 | 关键列 | 索引 |
|---|---|---|
| repair_intents | `intent_uuid` PK；invariant_kind；target refs；status；causation；`payload_extra` | (`team_uuid`,`status`)；target |
| cleanup_intents | `intent_uuid` PK；policy；substrate set digest；holds；status | (`team_uuid`,`status`) |
| cleanup_proofs | `proof_uuid` PK；intent FK；substrate_kind；target；proof_digest；verified_at | (`intent_uuid`)；(`target_ref`) |

---

### 3.5 `generation`

#### 3.5.1 `mkb_generation_artifacts`（immutable）

| 列 | 约束 |
|---|---|
| `generation_artifact_uuid` | PK |
| `team_uuid` | NOT NULL |
| `artifact_type` | NOT NULL（闭集见下） |
| `artifact_ordinal` | INTEGER NOT NULL DEFAULT 0 |
| `task_uuid`; `execution_uuid`; `process_uuid`; `process_attempt` | |
| `intake_item_uuid`; `intake_revision_uuid` | |
| `clean_artifact_uuid`; `clean_artifact_digest` | |
| schema/profile/model/prompt key+version+digest 列 | |
| `process_fence` | |
| `logical_handle`; `media_type`; `size_bytes`; `digest_algorithm`; `content_digest` | NOT NULL |
| `stored_object_uuid` | |
| `validation_disposition` | CHECK ∈ `full_valid,invalid,partial_rejected` 等 |
| report/proof refs | |
| predecessor/repair causation | |
| `created_at`; `payload_extra` | |

**v1 `artifact_type` 最小闭集**（可扩展注册，不得无注册使用）：

- S06：`structure_document`, `retrieval_block_projection`, `structure_validation_report`
- S07：`construction_document`, `dual_channel_projection`（+ validation 面）

**索引**

| 名 | 定义 |
|---|---|
| `ix_gen_art_execution` | (`team_uuid`,`execution_uuid`,`artifact_type`,`created_at`) |
| `ix_gen_art_task` | (`team_uuid`,`task_uuid`,`created_at`) |
| `ix_gen_art_digest` | (`team_uuid`,`content_digest`) |
| `ix_gen_art_item_rev` | (`team_uuid`,`intake_item_uuid`,`intake_revision_uuid`) |
| `ix_gen_art_stored` | (`stored_object_uuid`) |

#### 3.5.2 `mkb_generation_pointers`（CAS mutable）

| 列 | 约束 |
|---|---|
| `team_uuid`, `execution_uuid`, `artifact_type` | **PK / UNIQUE** |
| `current_generation_artifact_uuid` | NOT NULL FK 逻辑 |
| `pointer_revision` | INTEGER NOT NULL CAS |
| `updated_at`; `payload_extra` | |

**规则**：仅 `full_valid` artifact 可被指向（应用层 + 可选触发器）。

索引：PK；(`current_generation_artifact_uuid`)。

#### 3.5.3 `mkb_generation_pointer_transitions`（append-only）

| 列 | 约束 |
|---|---|
| `transition_uuid` | PK |
| `team_uuid`; `execution_uuid`; `artifact_type` | |
| `before_artifact_uuid`; `after_artifact_uuid` | |
| `expected_pointer_revision`; `actual_pointer_revision` | |
| causation process/task | |
| `occurred_at`; `payload_extra` | |

索引：(`team_uuid`,`execution_uuid`,`artifact_type`,`occurred_at`)。

#### 3.5.4 `mkb_generation_invocations`（append-only）

| 列 | 约束 |
|---|---|
| `invocation_uuid` | PK |
| `team_uuid`; `execution_uuid`; `process_uuid`; `process_attempt` | |
| `invocation_ordinal` | |
| `invocation_kind` | CHECK ∈ `generation,repair` |
| model/prompt/schema/profile refs | |
| input/output/error digests | |
| token usage integers | |
| `occurred_at`; `payload_extra` | |

UNIQUE(`process_uuid`,`invocation_ordinal`)。  
索引：(`execution_uuid`,`occurred_at`)。

---

### 3.6 `object`

#### 3.6.1 `mkb_stored_objects`

| 列 | 约束 |
|---|---|
| `stored_object_uuid` | PK |
| `team_uuid` | NOT NULL |
| `digest_algorithm` | NOT NULL DEFAULT `sha256` |
| `content_digest` | NOT NULL |
| `size_bytes` | INTEGER NOT NULL |
| `media_type` | NULL |
| `storage_backend` | NOT NULL DEFAULT `local_fs` |
| `created_at` | NOT NULL |
| `tombstoned_at` | NULL |
| `payload_extra` | |

UNIQUE(`team_uuid`,`content_digest`,`size_bytes`)。  
索引：(`team_uuid`,`created_at`)；(`tombstoned_at`) WHERE NOT NULL。

#### 3.6.2 `mkb_object_references`

| 列 | 约束 |
|---|---|
| `reference_uuid` | PK |
| `team_uuid` | NOT NULL |
| `stored_object_uuid` | NOT NULL |
| `purpose` | CHECK ∈ purpose 闭集（S13-T016） |
| `owner_kind`; `owner_uuid` | NOT NULL |
| `expected_digest`; `expected_size` | NOT NULL |
| `created_at` | NOT NULL |
| `released_at` | NULL（NULL = live） |
| `payload_extra` | |

**purpose 闭集**：`intake_snapshot_artifact`,`intake_revision_artifact`,`clean_candidate`,`gate_evidence`,`generation_artifact`,`process_io`,`operator_hold`,`backup_hold`。

**索引**

| 名 | 定义 |
|---|---|
| `ix_obj_ref_live` | (`stored_object_uuid`) WHERE `released_at` IS NULL |
| `ix_obj_ref_owner` | (`team_uuid`,`owner_kind`,`owner_uuid`) |
| `ix_obj_ref_purpose` | (`purpose`,`released_at`) |
| `ix_obj_ref_gc` | (`released_at`,`stored_object_uuid`) WHERE released |

#### 3.6.3 `mkb_object_delete_proofs`

| 列 | 约束 |
|---|---|
| `delete_proof_uuid` | PK |
| `team_uuid`; `stored_object_uuid` | |
| `content_digest`; `size_bytes` | |
| `delete_fence_digest` | NOT NULL |
| `unlinked_at` | NOT NULL |
| `scanner_id` | NULL |
| `payload_extra` | |

索引：(`stored_object_uuid`)；(`team_uuid`,`unlinked_at`)。

---

### 3.7 `vector`（最终向量物理合同）

> **最终落点**：同库 `mkb_primary` → `mkb_vector_records.embedding`（native F32）。  
> **对标**：legacy-python `vec.db`（namespaces + records + vec0）；**不**对标 legacy-family「D1 队列 + 外置 Vectorize」。  
> **队列**：`mkb_outbox.kind`；**禁止** `mkb_vec_process`。  
> **正文**：禁止 `content_full`；embedding 输入 digest + 可选 source handle。  
> **存在 ≠ serving**（S12-T027 / S09）。

#### 3.7.1 `mkb_vector_namespaces`

| 列 | 类型 | 约束 |
|---|---|---|
| `namespace_uuid` | TEXT | **PK** |
| `team_uuid` | TEXT | NOT NULL |
| `namespace_key` | TEXT | NOT NULL（team 内稳定键；bootstrap 默认 `default`） |
| `display_name` | TEXT | NULL |
| `embedding_model` | TEXT | NOT NULL（逻辑 model id） |
| `dimension` | INTEGER | NOT NULL CHECK `dimension > 0`（v1 部署常量由 S08/S09 登记；行内必须一致） |
| `distance_metric` | TEXT | NOT NULL DEFAULT `'cosine'` CHECK ∈ `cosine,l2,inner_product` |
| `status` | TEXT | NOT NULL CHECK ∈ `active,disabled,deleted` |
| `index_generation` | INTEGER | NOT NULL DEFAULT 0（S09 rebuild 代数；非业务 generation） |
| `created_at` / `updated_at` | TEXT | NOT NULL |
| `deleted_at` | TEXT | NULL |
| `payload_extra` | TEXT | NOT NULL DEFAULT `'{}'` |

**唯一**：UNIQUE(`team_uuid`,`namespace_key`)。

**索引**：(`team_uuid`,`status`,`namespace_key`)；(`embedding_model`,`dimension`)。

**Bootstrap**：empty-DB 不强制预插 team namespace；**首次 vectorize 前** 确保 team 的 active `default` namespace 存在（同 model/dim）。model/dim 变更 → **新 namespace** 或 controlled migration（禁止 silent 改 dimension 覆盖旧向量）。

#### 3.7.2 `mkb_vector_records`（最终向量本体）

| 列族 | 列 | 类型 | 约束 |
|---|---|---|---|
| Identity | `vector_record_uuid` | TEXT | **PK**（UUIDv7；亦可等于稳定 dedupe 键派生） |
| Scope | `team_uuid` | TEXT | NOT NULL |
| | `namespace_uuid` | TEXT | NOT NULL（逻辑 FK → namespaces） |
| Business coords | `generation_artifact_uuid` | TEXT | NOT NULL（structure 或 construction 投影 generation） |
| | `generation_artifact_type` | TEXT | NOT NULL（如 `retrieval_block_projection`,`dual_channel_projection`） |
| | `block_or_unit_id` | TEXT | NOT NULL（generation-local 坐标；非全局 int 假设） |
| | `channel` | TEXT | NOT NULL DEFAULT `'original'` CHECK ∈ `original,summary`（可扩展注册） |
| Intake filter | `intake_item_uuid` | TEXT | NULL |
| | `intake_revision_uuid` | TEXT | NULL |
| | `task_uuid` / `execution_uuid` | TEXT | NULL |
| Embedding input | `content_digest_algorithm` | TEXT | NOT NULL DEFAULT `sha256` |
| | `content_digest` | TEXT | NOT NULL（embedding **输入** 文本 digest） |
| | `source_handle` | TEXT | NULL（`mkbobj:…` 可选；**禁止** path） |
| | `content_char_length` | INTEGER | NULL |
| | **禁止列** `content_full` / `content_text` | — | **不得存在** |
| Model | `embedding_model` | TEXT | NOT NULL（必须与 namespace 一致或显式兼容策略） |
| | `dimension` | INTEGER | NOT NULL（必须 = namespace.dimension） |
| **Vector body** | `embedding` | **F32_BLOB(dimension)** | NOT NULL（**最终向量物理存储**） |
| | `embedding_digest` | TEXT | NULL（可选：向量字节 digest，用于对账） |
| Publication | `publication_state` | TEXT | NOT NULL DEFAULT `'indexed'` CHECK ∈ `indexed,withdrawn`（**仍非 serving 资格**；serving = S04 lifecycle ∩ S09） |
| | `index_generation` | INTEGER | NOT NULL DEFAULT 0 |
| Soft-delete | `deleted_at` | TEXT | NULL（NULL=active） |
| Provenance | `outbox_dedupe_key` | TEXT | NULL |
| | `embedded_at` | TEXT | NOT NULL |
| | `created_at` / `updated_at` | TEXT | NOT NULL |
| | `payload_extra` | TEXT | NOT NULL DEFAULT `'{}'` |

**唯一（幂等 upsert）**

```text
UNIQUE (
  team_uuid,
  namespace_uuid,
  generation_artifact_uuid,
  block_or_unit_id,
  channel,
  embedding_model
) WHERE deleted_at IS NULL
```

（若引擎对 partial unique 支持不足：用全量 UNIQUE 含 `deleted_at` 哨兵，或应用层 tombstone+新行。）

**二级索引（关系）**

| 名 | 定义 | 用途 |
|---|---|---|
| `ux_vec_coord_active` | 上表 partial unique | 幂等 |
| `ix_vec_team_ns` | (`team_uuid`,`namespace_uuid`,`deleted_at`) | 租户扫描 |
| `ix_vec_generation` | (`team_uuid`,`generation_artifact_uuid`,`deleted_at`) | rebuild/delete by generation |
| `ix_vec_item_rev` | (`team_uuid`,`intake_item_uuid`,`intake_revision_uuid`) | 检索前置 filter |
| `ix_vec_task` | (`team_uuid`,`task_uuid`) | 运维 |
| `ix_vec_content_digest` | (`team_uuid`,`content_digest`) | 对账 |
| `ix_vec_publication` | (`team_uuid`,`publication_state`,`deleted_at`) | 运维 |

#### 3.7.3 Native ANN 索引（最终向量索引 · 强制）

> 算法参数（ef、lists 等）归 **S09**；D04 强制 **索引存在且可 probe**。

**逻辑 DDL（libSQL / Turso 方言；实现按引擎文档微调标识符）**：

```sql
-- 在 mkb_vector_records 建表且 dimension 与部署常量一致后：
CREATE INDEX IF NOT EXISTS vec_idx_mkb_vector_records_embedding
  ON mkb_vector_records (
    libsql_vector_idx(embedding)
  );
-- 若引擎要求单独 vector index 语法，等价目标：
--   支持 vector_top_k / 同库 ANN 查询；
--   readiness 必须能探测该 index 或 vector 能力 flag。
```

**Readiness 义务（S12 联合）**

1. Native vector 类型可写入 `embedding`；  
2. ANN index 已创建或引擎报告 vector index ready；  
3. 缺失 → `readiness=false`（默认配置）。

**查询路径（逻辑）**

```text
S10/S09:
  1) ANN: vector_top_k(embedding, query, k) → rowids / record uuids
  2) 关系 filter: team_uuid + deleted_at IS NULL + publication_state
  3) join Intake serving/lifecycle + generation current（业务资格）
  → 禁止跳过 2/3 仅凭 ANN 命中返回
```

#### 3.7.4 Vectorize 写入时序（与 outbox）

```text
TX business (TX-06 etc):
  proof + pointers + outbox(kind=vectorize_construct, dedupe_key, payload=exact generation refs)
  # vectorize_structure: reserved name / v1 forbid consumer (S08-v1.0)
  + domain_event(generation.artifact_accepted|...)
commit

dispatcher → vectorize worker:
  load dual_channel / block projection by handle+digest
  embed (S08/S11)
  TX:
    ensure namespace
    UPSERT mkb_vector_records (embedding F32, filters, digests)
    domain_event(vector.upserted)   -- 推荐同 TX
  fail → outbox retry / dead；不得写“假 serving”
```

**Rebuild**：按 `generation_artifact_uuid` soft-delete（`deleted_at`）或物理删后重 upsert；**不**改 Task/Intake 状态机。

#### 3.7.4b 双层 Filter（S11 / `T-O-192` / `T-O-197..198`）

> **分账**：Layer A = 向量**空间/推理隔离**（内部状态与流转）；Layer B = **业务检索 filter**。二者都是强制围栏；**B 不能替代 A**。

**Layer A — 空间 / adapter 隔离（内部）**

| 规则 | 强制 |
|---|---|
| 混用 | **禁止** 不同 `embedding_model`（含 version）写入同一可检索空间而不改 namespace |
| 写路径 | `namespace.(embedding_model, dimension)` 必须与 record 行一致；`adapter_kind`（或 binding 快照）记录；不匹配 → **拒绝写入** |
| 读路径 | query 的 model/version/dim/adapter 必须匹配目标 namespace；禁止静默跨空间 ANN |
| fallback | **禁止** silent 换另一 embedding 模型重试 |

推荐列：`adapter_kind TEXT NOT NULL`（v1.1 新写入强制；可 default `local_vllm`）。

**Layer B — 业务 filter（产品/上游，T-O-198）**

在 Layer A 通过后，检索与对账还必须能按 **业务范围** 过滤。最低集合：

| 维度 | 物理落点（最低） | 说明 |
|---|---|---|
| **team_uuid** | 所有 team-owned 表 / records **NOT NULL** | 全域租户围栏 |
| **intake source / item / revision** | `intake_item_uuid`、`intake_revision_uuid` 等已有坐标列；source 经 item 可反查或冗余 `intake_source_uuid` | 资产范围 |
| **上游分类 facet** | 可索引业务 filter 列或 **typed facet 结构**（禁止仅靠不可查询 blob 当唯一真相） | 例：上游 `industry-domain` + **map 映射** → 写入可过滤值；检索按 domain 裁剪 |
| 其它上游 facet | versioned facet key 注册后晋升列或规范化子表 | 扩展须 definition，禁自由 JSON 当 SSOT |

```text
retrieve:
  1) resolve namespace + Layer A space gate (model/dim/adapter)
  2) ANN candidates
  3) apply Layer B: team ∧ intake coords ∧ facets (industry-domain, …)
  4) S04 lifecycle / serving 资格（仍非「有向量=可服务」）
```

legacy `vec_filter_meta` / realm 仅为 B 层祖先；MKB 要求 **team 强制 + typed facet**，且 **不得** 用换 embedding 模型模拟业务分区。

#### 3.7.5 与 legacy 的显式删除清单

| Legacy | MKB |
|---|---|
| `smind_vec_process` 作队列+正文 | **forbid**；outbox + generation artifacts |
| Cloudflare Vectorize 最终索引 | **v1 forbid 作 SSOT**；同库 native |
| DO `buffered_vectors` WAL | 不需要独立表；进程内 batch + records TX |
| `content_full` 进 vec 表 | **forbid** |
| 有向量 = 可服务 | **forbid** |

---

### 3.8 S11 model / inference 三表（v1.1 reopen · `T-O-193`）

#### 3.8.1 `mkb_model_catalog`

| 列 | 类型 | 约束 |
|---|---|---|
| `model_uuid` | TEXT | PK（UUIDv7） |
| `model_key` | TEXT | NOT NULL（稳定逻辑键，如 `qwen3-vl-embedding`） |
| `model_version` | TEXT | NOT NULL |
| `modality` | TEXT | NOT NULL CHECK ∈ `embed,rerank,generate,multimodal_embed,…`（可扩展注册） |
| `provider_family` | TEXT | NOT NULL（如 `vllm_local`,`gemini`,`google_ranking`） |
| `default_dimension` | INTEGER | NULL（embed 类建议非空） |
| `definition_digest` | TEXT | NOT NULL |
| `status` | TEXT | NOT NULL CHECK ∈ `active,disabled,deprecated` |
| `display_name` | TEXT | NULL |
| `registered_at` | TEXT | NOT NULL |
| `payload_extra` | TEXT | NOT NULL DEFAULT `'{}'` |

**唯一**：UNIQUE(`model_key`,`model_version`)。  
**索引**：(`modality`,`status`)；(`definition_digest`)。  
**规则**：code-owned bootstrap 幂等；同 version 异 digest → fail readiness。

#### 3.8.2 `mkb_adapter_bindings`

| 列 | 类型 | 约束 |
|---|---|---|
| `binding_uuid` | TEXT | PK |
| `capability_key` | TEXT | NOT NULL（`embed`/`rerank`/`structured_generate`/`text_generate`） |
| `adapter_kind` | TEXT | NOT NULL（`local_vllm` / `remote_gemini` / …） |
| `model_key` | TEXT | NOT NULL |
| `model_version` | TEXT | NOT NULL |
| `priority` | INTEGER | NOT NULL DEFAULT 100（数字越小越优先） |
| `team_uuid` | TEXT | NULL（NULL=全局默认） |
| `enabled` | INTEGER | NOT NULL DEFAULT 1 CHECK ∈ 0,1 |
| `binding_digest` | TEXT | NOT NULL |
| `created_at` / `updated_at` | TEXT | NOT NULL |
| `payload_extra` | TEXT | NOT NULL DEFAULT `'{}'` |

**唯一**：UNIQUE(`capability_key`,`adapter_kind`,`model_key`,`model_version`,`team_uuid`) 或应用层等价（NULL team 用哨兵）。  
**索引**：(`capability_key`,`enabled`,`priority`)；(`adapter_kind`,`enabled`)。  
**v1 默认**：仅 **enabled** 的 `local_vllm` 绑定进入默认路由；`remote_gemini` 可登记为 disabled/theoretical。

#### 3.8.3 `mkb_inference_invocations`（append-only · 非 SSOT）

| 列 | 类型 | 约束 |
|---|---|---|
| `invocation_uuid` | TEXT | PK |
| `team_uuid` | TEXT | NULL |
| `trace_uuid` | TEXT | NULL |
| `task_uuid` / `execution_uuid` / `process_uuid` | TEXT | NULL |
| `capability_key` | TEXT | NOT NULL |
| `adapter_kind` | TEXT | NOT NULL |
| `model_key` / `model_version` | TEXT | NOT NULL |
| `request_digest` | TEXT | NOT NULL |
| `status` | TEXT | NOT NULL CHECK ∈ `succeeded,failed,cancelled` |
| `error_code` | TEXT | NULL |
| `input_tokens` / `output_tokens` / `total_tokens` | INTEGER | NULL |
| `latency_ms` | INTEGER | NULL |
| `generation_invocation_uuid` | TEXT | NULL（可选链到 S06/S07 账） |
| `occurred_at` | TEXT | NOT NULL |
| `payload_extra` | TEXT | NOT NULL DEFAULT `'{}'`（禁 prompt 正文/secret/向量正文） |

**索引**：(`team_uuid`,`occurred_at`)；(`trace_uuid`,`occurred_at`)；(`process_uuid`)；(`capability_key`,`occurred_at`)；(`model_key`,`model_version`,`occurred_at`)。  
**规则**：不替代业务 CAS；不定义 Task success。

---

## 4. VIEW 清单（只读）

> 全部 `CREATE VIEW`；禁止 `INSTEAD OF` 写业务；`S12-A22` 验收禁止 VIEW UPDATE。

| VIEW | 定义意图 | 消费者 |
|---|---|---|
| `mkb_v_tasks_active` | `mkb_tasks` WHERE `deleted_at IS NULL` | list 默认 |
| `mkb_v_processes_claimable` | processes 可 claim 且 `available_at` 到期 | claim 扫描 |
| `mkb_v_outbox_pending` | outbox `pending`/`in_flight` | dispatcher |
| `mkb_v_object_live_refs` | object_references `released_at IS NULL` | GC 保护 |
| `mkb_v_object_orphan_candidates` | stored_objects 无 live ref（grace 由应用过滤） | GC |
| `mkb_v_generation_current` | pointers ⋈ artifacts | 只读 current |
| `mkb_v_intake_items_serving` | items active 且 serving_revision NOT NULL | 检索前置（仍非最终资格） |
| `mkb_v_gates_open` | gates `open` | Task gate list |
| `mkb_v_domain_events_by_trace` | 便于文档化；实现可用参数化 SQL 等价 | 运维 timeline |
| `mkb_v_vectors_active` | records WHERE `deleted_at IS NULL` AND publication≠withdrawn | 对账/ANN 前置 filter |
| `mkb_v_vector_by_generation` | active 向量按 generation 计数 | rebuild 对账 |
| `mkb_v_vector_namespaces_active` | namespaces status=`active` AND deleted_at IS NULL | 解析默认空间 |
| `mkb_v_adapter_bindings_enabled` | bindings WHERE enabled=1 ORDER BY priority | inference 路由只读 |
| `mkb_v_model_catalog_active` | catalog status=`active` | bootstrap/readiness |

**`mkb_v_vectors_active` 逻辑列（最少）**

```sql
CREATE VIEW mkb_v_vectors_active AS
SELECT
  r.vector_record_uuid,
  r.team_uuid,
  r.namespace_uuid,
  n.namespace_key,
  n.distance_metric,
  r.generation_artifact_uuid,
  r.block_or_unit_id,
  r.channel,
  r.intake_item_uuid,
  r.intake_revision_uuid,
  r.content_digest,
  r.embedding_model,
  r.dimension,
  r.publication_state,
  r.embedded_at
  -- embedding 列：是否暴露给 VIEW 由实现决定；ANN 通常直接查基表
FROM mkb_vector_records r
JOIN mkb_vector_namespaces n ON n.namespace_uuid = r.namespace_uuid
WHERE r.deleted_at IS NULL
  AND r.publication_state = 'indexed'
  AND n.status = 'active'
  AND n.deleted_at IS NULL;
```

**禁止**：以 VIEW 作为 CAS 目标；以 VIEW / log / vector 行替代业务 SSOT。

---

## 5. 索引策略总则（四类强制）

| 类 | 模式 | 覆盖表例 |
|---|---|---|
| 租户列表 | `(team_uuid, created_at/updated_at, uuid)` | tasks, items, artifacts, executions |
| 状态/队列 | `(status, available_at, priority)` 或 team+status | processes, outbox, candidate_sets, gates |
| 主体反查 | execution/task/item/snapshot/source UUID | processes, memberships, generation, transitions |
| 幂等/唯一 | composite UNIQUE + partial unique | materialization, pointers, dedupe_key, external_key, restart |

**禁止**：无 `team_uuid` 前缀的全局 status 单列索引作为 **唯一** 访问路径；跨 team 扫描业务表。

---

## 6. 与 migration / readiness 的接合

1. Empty-DB：按单链 apply 全部模块 → bootstrap registry 行（workflow、semantic/action、source kind、structure/construction schema、prompt hash 指针）同 digest 幂等。  
2. Readiness=false：migration 未完、checksum drift、强制 definition 缺失、CW/vector 能力声明不匹配、object_root identity 不一致（S13）。  
3. Architecture test：domain 禁止 `import` driver；禁止 `smind_`；禁止第二 outbox 表名。

---

## 7. Gap analysis：legacy-family × leaf-worker × D04（v0.2 已收口）

> **目的**：保留对照证据；v0.2 已按推荐意见 **补齐** 可观测三表 + 向量物理合同。  
> **纪律**：legacy 仅 ReferenceAnchor（T-O-101）。

### 7.1 smind-console 全局表地图（已实装 ~30 表）

| 模块文件 | 表 | leaf-worker 相关性 |
|---|---|---|
| `01-identity` | `smind_users`, `smind_users_profile` | **OOS**（平台用户；OD-01） |
| `02-teams` | `smind_teams`, `smind_teams_keys`, `smind_teams_storage` | **部分**：最小 teams 保留；keys/storage quota 平台化 → S16/`17` 或 defer |
| `03-workflows` | `smind_workflows`, `smind_prompts` | **升级**：七表 + git prompt hash；禁 mutable 大 JSON workflow |
| `04-skills` | `smind_skills`, `smind_skill_tasks` | **OOS / 另构**：ProcessCapability 为 code registry |
| `05-files` | `smind_files*`, relations, folders, static | **升级分拆**：Intake 十表 + S13 object；禁 file 超级 status |
| `06-process-tracking` | `smind_clean_process`, `smind_rag_process`, `smind_vec_process` | **关键对照**（见下） |
| `07-cms` | `smind_cms_contents` | **OOS** |
| `08-messages` | inbox / messages | **OOS**（平台消息） |
| `09-conversations` | `smind_chats` | **OOS**（对话产品） |
| `10-templates` | templates* | **OOS** |
| `11-crm` | crm* | **OOS** |
| WIP projects | 15 表 | **OOS** |

**注意**：`smind_logs` **不在** console `db/*.sql` 模块清单中，但 **全 Worker 族广泛写入 D1**（dispatcher/vectorizer/structurizer/admin/contexter），console 用 `files/debug/audit-log` 按 `trace_uuid` 反查——即 **运维日志是跨 Worker 事实，却未进入 console 模块化 DDL 的一等公民文档**。这是 legacy 自身缺陷，也解释了“console 文件树里看不到 logs”与“线上却依赖 logs”的割裂。

### 7.2 为什么 D04-v0.1 没有 log 类表？（诚实原因 + 判定）

| 原因 | 说明 | 判定 |
|---|---|---|
| 职责外推到 S15 | `spec-index` 将 Observability & Reliability 标为 **S15 pending**；S03 写明 event/log/retention 归 S15 | 编排正确 **但过早真空** |
| 避免 log 变 SSOT | S12 `T-O-100`：queue/log/view 不是业务成功 SSOT | **正确**；仍可有 **非 SSOT 的 durable 可观测表** |
| 业务错误已部分嵌入 | `mkb_processes.error_*`、`mkb_tasks` summary、`mkb_generation_invocations`、gate decisions | **部分可观测**；缺跨实体 timeline |
| 对照 legacy | `smind_logs` + process error；python events/audit | **v0.2 已用三表吸收并升级** |

#### 7.2.1 数据库内如何观察？（v0.2）

| 观察需求 | v0.2 | 路径 |
|---|---|---|
| Task 状态 / 终态错误 | **能** | `mkb_tasks` |
| Execution/Process 树与失败 | **能** | executions ⋈ processes |
| claim/lease 卡死 | **能** | processes lease 索引 |
| outbox 毒消息 | **能** | `mkb_outbox` |
| gate / intake 因果 | **能** | gates* / transitions / change_set_facts |
| Generation 调用 | **能** | `generation_invocations` |
| **按 trace 全链路时间线** | **能** | **`mkb_domain_events`** |
| **诊断日志** | **能** | **`mkb_ops_diagnostic_logs`** |
| **安全/admission 审计** | **能** | **`mkb_security_audit_events`** |
| metrics 时序 | 不进业务库 | S15 → Prometheus/OTLP |

#### 7.2.2 可观测表状态（v0.2 已落地 §3.1.3–3.1.5）

| 表 | 对标 | SSOT? | 状态 |
|---|---|---|---|
| `mkb_domain_events` | workflow_events | 否 | **required · 同 TX** |
| `mkb_ops_diagnostic_logs` | smind_logs 降维 | 否 | **required** |
| `mkb_security_audit_events` | audit_logs 子集 | 否 | **required** |
| metrics 时序表 | — | — | **defer**；S15 scrape |

**写入纪律**：业务成功只看业务表 CAS；domain_events 插入失败 → 整 TX 失败；diagnostic 可 best-effort；payload 禁 secret/正文/唯一 proof；retention 数值归 S15。

### 7.3 最终向量落点（v0.1 缺口 → v0.2 已收）

| 原因（v0.1） | v0.2 处置 |
|---|---|
| S12 只冻最小合同 | 正确分层保留；D04 补物理 |
| 仅提纲 | **§3.7 完整 F32 + ANN + filter + namespace** |
| family 外置 Vectorize | **拒绝作 v1 SSOT**；同库 native |
| python vec0 模板 | **已吸收为 namespaces + records + index** |

#### 7.3.1 legacy 向量数据面 vs MKB 目标

```text
legacy-family:
  D1 smind_vec_process  ──(content_full, block, channel, status)──► 工作队列/元数据
  DO  buffered_vectors  ──(vec_uuid, vector_blob)──► 临时 WAL
  Cloudflare Vectorize  ──最终 ANN 索引 + id=vec_uuid──► 检索 SSOT-ish（业务外）

legacy-python:
  core.db  ──业务──►  loosely coupled
  vec.db   ── vector_records + vec0 virtual table ──► 最终向量同引擎

MKB (已冻方向 T-O-107/110):
  mkb_primary
    generation proof ──outbox vectorize──► mkb_vector_records(+native vector col)
                                         + native ANN index
    serving 资格仍由 Intake lifecycle + S09 publication 决定
```

#### 7.3.2 缺口关闭表

| 原缺口 | v0.2 落点 |
|---|---|
| 最终向量字节 | `mkb_vector_records.embedding` **F32_BLOB(dim)** |
| ANN 索引 DDL | `vec_idx_mkb_vector_records_embedding` + readiness |
| namespace | `mkb_vector_namespaces` |
| 禁 content_full | D04-P16 / §3.7.2 |
| soft-delete | `deleted_at` + `mkb_v_vectors_active` |
| publication 投影 | `publication_state`（仍≠serving） |
| 队列 | outbox `vectorize_*`；forbid vec_process |
| filter 列 | item/revision/generation/channel 等可索引列 |

### 7.4 全量对照：缺陷 / 正确裁剪 / v0.2

| 主题 | legacy 做法 | D04-v0.2 | 判定 |
|---|---|---|---|
| 用户/CRM/inbox/CMS/chat | console 大量表 | 无 | **正确裁剪**（OD-01） |
| clean/rag 双 process 表 | 有 | 统一 `mkb_processes` | **正确升级** |
| file 超级表 | `smind_files` | Intake 十表 + object | **正确升级** |
| 步骤错误列 | process.error_* | processes.error_* | **已覆盖** |
| 跨 Worker 业务日志 | `smind_logs` | **`mkb_ops_diagnostic_logs`** | **v0.2 已补** |
| 统一 domain 事件流 | python `workflow_events` | **`mkb_domain_events`（同 TX）** | **v0.2 已补** |
| 安全审计 | python `audit_logs` | **`mkb_security_audit_events`** | **v0.2 已补** |
| 向量工作单元队列 | `smind_vec_process` | **forbid**；`mkb_outbox.kind=vectorize_*` | **v0.2 写清** |
| 最终向量本体 | Vectorize / python vec0 | **`mkb_vector_records.embedding` F32** | **v0.2 已补** |
| 向量 namespace | python 有 | **`mkb_vector_namespaces`** | **v0.2 已补** |
| 向量 active view | python 有 | **`mkb_v_vectors_active` 等** | **v0.2 已补** |
| ANN 索引 | Vectorize / vec0 | **`vec_idx_mkb_vector_records_embedding`** | **v0.2 已补** |
| prompts | DB 正文 | hash 指针 + git | **正确升级** |
| storage quota | teams_storage | 无 | **defer** / S15 |
| 第二 outbox | 无 | 单 outbox | **正确** |

### 7.5 v0.2 收口清单（已落地本文）

| # | 动作 | 状态 |
|---|---|---|
| 1 | `mkb_domain_events` required + 同 TX | **done §3.1.3** |
| 2 | `mkb_ops_diagnostic_logs` required | **done §3.1.4** |
| 3 | `mkb_security_audit_events` required | **done §3.1.5** |
| 4 | `mkb_vector_namespaces` required | **done §3.7.1** |
| 5 | 强化 `mkb_vector_records` + 禁 content_full | **done §3.7.2** |
| 6 | ANN index SQL + readiness | **done §3.7.3** |
| 7 | VIEW active / by generation / namespaces | **done §4** |
| 8 | forbid vec_process；outbox 替代 | **done D04-P17 / §3.7.4** |
| 9 | 台账 52 张 | **done §2.2** |

---

## 8. Owner-gate 清单（已冻结）

| ID | 问题 | 冻结裁决 | Truth |
|---|---|---|---|
| `OG-D04-01` | claim 附属表？ | **否**；行内 fence | `T-O-165` |
| `OG-D04-02` | 第二 outbox？ | **否** | `T-O-164` |
| `OG-D04-03` | workflow body 落库？ | 可选列 + digest 强制 | `T-O-163` 台账细则 |
| `OG-D04-04` | ENUM 拼写 | 与 S03/S04 字面对齐；漂移 fail-closed | `T-O-175` |
| `OG-D04-05` | multi-space | **namespace 头表 + records**；默认 `default` | `T-O-169` |
| `OG-D04-06` | ChangeSet facts JSON？ | **否**；独立 facts 表 | `T-O-163` |
| `OG-D04-07` | 表数可砍？ | 强制集不可砍 | `T-O-163` |
| `OG-D04-08` | 可观测三表强制？ | **是 · required · 非 SSOT** | `T-O-166` |
| `OG-D04-09` | events 同 TX？ | **是 · 失败整 TX 失败** | `T-O-167` |
| `OG-D04-10` | content_full 进向量表？ | **否** | `T-O-168` |
| `OG-D04-11` | 同库 native ANN？ | **是**；外置 Vectorize 非 v1 SSOT | `T-O-168`/`T-O-170` |

全部 `accepted / frozen`（`T-O-179`）。

---

## 9. Domain verdict

### 9.1 Verdict

**`ACCEPTED / OWNER-FROZEN / GO`**：D04 作为 **数据库表结构与细节的真相层** 已闭合；`T-O-160..179` + S11 reopen `T-O-192..194`；v1.1 闭集 **55 表**。

### 9.2 强制结论

1. **55 张** `mkb_*` required 表 + 明文 forbid/defer；  
2. 单主库、单 outbox、claim 行内、VIEW 只读；  
3. 可观测三表 + **inference_invocations**；domain_events **同 TX**；  
4. **model_catalog + adapter_bindings** 独立表；  
5. 最终向量 = F32 + ANN；**跨 embedding_model 严禁混用**；  
6. 禁 vec_process / content_full / 外置 Vectorize v1 SSOT / log 当业务成功；  
7. 业务状态边归 S02–S07；物理闭集归 D04；typed 消息归 contracts。

### 9.3 下游

| 下游 | 承接 |
|---|---|
| S12 | migration 链；Ports 不变 |
| S09 | ANN/serving；model 围栏 |
| S11 | catalog/binding/invocation 语义；Inference≠Adapter |
| S15 | retention/alert/export |
| S08 | **S08-v1.0**：`lsrag.vectorize` 写 records；model/dim/adapter 一致；Layer B 抄写 S04；v1 禁消费 vectorize_structure |
| D03 | `data/database/` 落点 |
| 实现 | architecture tests：表前缀、禁混空间、禁第二 outbox |

### 9.4 一句话

D04 把单库 Turso 的 **表闭集、索引、可观测与模型/推理账、最终向量合同** 冻成可验收真相，并强制 **embedding 空间隔离**。

---

## 10. 修订历史

| 版本 | 日期 | 作者 | 状态 | 主要变更 |
|---|---|---|---|---|
| `D04-v0.1-draft` | `2026-08-11` | `Codex` | `designing` | 首版台账。 |
| `D04-v0.1.1-draft` | `2026-08-11` | `Codex` | `designing` | legacy 对照。 |
| `D04-v0.2-draft` | `2026-08-11` | `Codex` | `designing` | ops+vector 补齐；52 表。 |
| `D04-v1.0` | `2026-08-11` | `MKB owner + Codex` | `owner-frozen` | `T-O-160..179`。 |
| `D04-v1.1` | `2026-08-12` | `MKB owner + Codex` | **`owner-frozen / S11-reopen`** | +3 表至 55；`T-O-192..194`；embedding 隔离；§3.8。 |
| `D04-v1.1-cal-s11-r2` | `2026-08-12` | `MKB owner + Codex` | **`owner-frozen / S11-R2-calibrated`** | §3.7.4b 双层 filter：`T-O-197` 空间隔离 + `T-O-198` 业务 filter（team/intake/上游 facet）。 |
| `D04-v1.1-cal-d08` | `2026-08-13` | `MKB owner + Grok` | **`owner-frozen / D08-calibrated`** | §2.2.3 三表 proposed；§3.3.2b FilterMeta 五维 + provider/strategy 重排。**55 required 不变**。 |

---

## Appendix A — 表名速查（55 required · 字母序）

```text
mkb_adapter_bindings
mkb_construction_schema_definitions
mkb_domain_events
mkb_execution_gate_decisions
mkb_execution_gate_targets
mkb_execution_gates
mkb_executions
mkb_generation_artifacts
mkb_generation_invocations
mkb_generation_pointer_transitions
mkb_generation_pointers
mkb_inference_invocations
mkb_intake_action_definitions
mkb_intake_artifacts
mkb_intake_candidate_pages
mkb_intake_candidate_sets
mkb_intake_change_set_facts
mkb_intake_change_sets
mkb_intake_cleanup_intents
mkb_intake_cleanup_proofs
mkb_intake_item_transitions
mkb_intake_items
mkb_intake_repair_intents
mkb_intake_revision_semantics
mkb_intake_revisions
mkb_intake_semantic_definitions
mkb_intake_snapshot_memberships
mkb_intake_snapshots
mkb_intake_sources
mkb_model_catalog
mkb_object_delete_proofs
mkb_object_references
mkb_ops_diagnostic_logs
mkb_outbox
mkb_preflight_profile_definitions
mkb_processes
mkb_prompt_hash_pointers
mkb_schema_migrations
mkb_security_audit_events
mkb_source_kind_definitions
mkb_stored_objects
mkb_structure_schema_definitions
mkb_task_audits
mkb_task_restarts
mkb_tasks
mkb_teams
mkb_vector_namespaces
mkb_vector_records
mkb_workflow_bindings
mkb_workflow_controls
mkb_workflow_guards
mkb_workflow_registry
mkb_workflow_revisions
mkb_workflow_routes
mkb_workflow_steps
```

## Appendix B — 模块分工一页纸

```text
┌──────────────────── mkb_primary (Turso) ────────────────────┐
│ ops (5):      migrations, teams,                            │
│               domain_events, diagnostic_logs, security_audit│
│ runtime (9):  tasks, audits, restarts,                      │
│               executions, processes, outbox,                │
│               gates / targets / decisions                   │
│ registry(14): workflow×7, definitions, prompt hash          │
│ intake (15):  10 canonical + candidate/changeset/cleanup    │
│ generation(4):artifacts, pointers, transitions, invocations │
│ object (3):   stored_objects, refs, delete_proofs           │
│ vector (2):   namespaces + records.embedding(F32) + ANN idx │
└───────────────────────┬─────────────────────────────────────┘
                        │ bytes-first handles
                        ▼
                  data/objects/ (S13 FS)

可观测：  domain_events（同 TX） / diagnostic_logs / security_audit
向量路径：proof → outbox vectorize_* → UPSERT records.embedding
禁止：    smind_* / 第二 outbox / vec_process / content_full / log=SSOT
```

## Appendix C — 可观测查询速查（运维）

```sql
-- 1) 按 trace 拉业务时间线
SELECT occurred_at, event_type, severity, summary, task_uuid, process_uuid
FROM mkb_domain_events
WHERE trace_uuid = :trace
ORDER BY occurred_at, event_uuid;

-- 2) 同 trace 诊断错误
SELECT occurred_at, log_level, log_code, log_message, calling_module
FROM mkb_ops_diagnostic_logs
WHERE trace_uuid = :trace AND log_level IN ('warn','error')
ORDER BY occurred_at;

-- 3) 安全拒绝
SELECT occurred_at, action, denial_code, summary, team_uuid
FROM mkb_security_audit_events
WHERE outcome = 'denied' AND occurred_at >= :since
ORDER BY occurred_at DESC;

-- 4) 某 generation 的最终向量是否在库（非 serving）
SELECT COUNT(*), channel, embedding_model
FROM mkb_v_vectors_active
WHERE team_uuid = :team AND generation_artifact_uuid = :gen
GROUP BY channel, embedding_model;
```

## Appendix D — outbox.kind 最小闭集（vector 相关）

| kind | 载荷最小 | 消费效果 |
|---|---|---|
| `vectorize_construct` | team + construct generation refs + digests | **v1 主路径**：upsert dual-channel 向量（S08） |
| `vector_purge_generation` | team + generation_artifact_uuid | soft-delete 该 generation 向量（对齐 S08 purge mode） |
| `vectorize_structure` | （保留名） | **v1 forbid consumer**（S08-T003）；不得实现成功路径 |
| （其它 wake 类） | 见 S03/S12 | 非本附录展开 |

## Appendix E — NS1 narrow prompt catalog promotion

NS1 does not add a required table or a prompt-body table. It promotes the
existing `mkb_prompt_hash_pointers` row with the catalog metadata columns
`prompt_id`, `role`, `status`, and `granularity_set`; the existing
`prompt_version`, `git_relative_path`, and `content_sha256` remain the durable
identity/version/path/hash facts. Prompt bytes remain under the git-tracked
`data/prompts/**` tree. `body_text` remains forbidden.

The API passes only role-specific prompt IDs (`json_prompt_id` is required;
`markdown_prompt_id`, `clean_prompt_id`, and `summarizer_prompt_id` are optional).
Materialization resolves the active catalog rows and freezes the four selected
pointer facts into the execution snapshot/input manifest. Retry and in-flight
execution therefore cannot observe a later catalog version, and path/hash
drift fails closed. The JSON row alone owns the closed granularity set
`[0,1,2]`; Markdown is an optional workflow hop, not a new persistence domain.
