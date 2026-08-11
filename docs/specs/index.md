# MyKnowledgeBase Specification Index

> **项目**：`myknowledgebase`（MKB）
>
> **文档角色**：新一轮 specification 的唯一索引、范围上限与两级文件清单
>
> **版本 / 日期**：`v1.0 / 2026-08-10`
>
> **状态**：`specification-ready`
>
> **作者**：`MKB owner + Codex`
>
> **前序资料**：`docs/baseline/`仅作为已锁定Truth与历史证据来源；其讨论流程、文件拆分和未冻结提案不再支配本目录

## 0. 重启声明

`docs/baseline/`下的讨论已经失去收敛性。本目录从头建立MKB specification，但不重问baseline中已经锁定的产品与领域Truth。

本轮只有两个文件层级：

1. `owner-truth/`：只保存需要owner确认的foundational truth；
2. `execution-spec/`：保存如何实现foundational truth的完整技术设计，由Codex/工程设计自行负责。

本索引本身是唯一例外的根文件。`docs/specs/`内不再建立QNA目录、cross-domain中间层、独立gate文件、独立ADR文件或第三层spec。

### 0.1 本轮强制原则

1. Owner只回答foundational问题，不回答executional问题。
2. 已锁定的baseline Truth直接继承，不因迁入新目录而重新提问。
3. Execution设计必须优先由baseline Truth、legacy证据和工程约束推导；不能把技术选择上推给owner。
4. 不自动生成下一轮问题，不设固定题数，不以“完整”为理由扩充domain、文件或平台能力。
5. 每次提出推荐之前，必须先完成§2的Scope Impact Audit。
6. 新需求必须进入现有文件槽位；默认禁止新增owner-truth或execution-spec文件。
7. MKB只负责knowledge处理、转换、存储与获取；任何基于MKB的上游业务均为OOS。MKB内部流转状态和生命周期是工具内部真相，不是产品层功能。

---

## 1. 固定项目边界

### 1.1 架构与容量上限

| 维度 | 固定上限 | 约束 |
|---|---:|---|
| MKB应用 | `1` | 一个Python应用、一个发布单元；内部模块不等于新服务 |
| 已知上游类型 | `1` | internal orchestrator；首个已知调用方为`03-nano/orchestrator-core` |
| Owner Truth文件 | `4` | 只能在既有文件内修订；新增文件须由owner主动改变foundational范围 |
| Execution Spec文件 | `8` | 覆盖全部v1执行设计；新主题必须合并到现有文件 |
| UI/用户平台 | `0` | 不建设UI、membership、billing、session或用户所有权平台 |
| 部署拓扑 | `1` | 单体发布；adapter、worker loop或本地进程不自动成为新部署单元 |
| StateFamily | `6` | 直接继承D02-v1.0；不得因工序或阶段增加新状态族 |
| Compatibility/Migration产品 | `0` | legacy只作证据，不建设兼容、dual-read、importer或cutover产品 |

### 1.2 V1能力边界

V1只围绕以下闭环设计：

```text
internal document / Task contract
  → durable workflow execution
  → intake / acquisition / cleaning / admission
  → LS-RAG structure + construction
  → structured vector storage / index
  → upstream retrieval and vector-consumption interface
```

MKB必须自行持有完成上述闭环所需的工作流状态、资产生命周期、retry、recovery与cleanup truth；这些内部责任不构成产品层扩张。

以下内容默认不进入V1：

- UI、终端用户账号、组织成员、计费和复杂授权平台；
- generic agent platform、动态插件市场、任意Workflow authoring平台；
- 多应用拆分、微服务化或跨产品通用状态治理平台；
- legacy runtime/schema/API兼容和历史数据迁移产品；
- answer-generation，以及基于MKB的问答、agent、产品Workflow或任何其他上游业务；
- 知识编辑、协作审核或通用内容管理能力；
- 只为未来可能性增加的状态、抽象层、registry、扩展点或部署单元。

### 1.3 Foundational与Executional的边界

| Foundational：可以问owner | Executional：不得问owner |
|---|---|
| MKB负责什么、不负责什么 | 文件、模块、类、表、列、索引和DDL如何设计 |
| V1包含/不包含哪些产品能力 | Workflow图、Process粒度、算法和内部路由如何实现 |
| 外部调用方可观察到什么行为 | retry、lease、fence、outbox、事务和恢复机制如何实现 |
| 核心业务身份及其责任归属 | payload、schema、enum的内部表示与版本化方式 |
| 外部Contract的产品语义 | HTTP路径、错误码细节、分页和序列化细节 |
| 什么结果算V1成功或不可接受 | 性能调优、batch、cache、并发和容量参数 |
| 会改变产品范围的不可逆取舍 | Turso driver、存储backend、模型adapter的技术选择 |

若一个问题可以在不改变左列的情况下解决，它就是executional，由Execution Spec直接裁决。

---

## 2. Scope Expansion 防线

### 2.1 每次推荐前的强制审计

任何文档在写出“推荐方案”前，必须先填写以下块；不得事后补写：

```text
Scope Impact Audit
- New product responsibility: no | yes
- New externally visible behavior: no | yes
- New V1 capability: no | yes
- New domain identity or StateFamily: no | yes
- New deployment/runtime unit: no | yes
- New owner-truth file: no | yes
- New execution-spec file: no | yes
- Raises a fixed capacity ceiling: no | yes
- Can be solved inside an existing file and boundary: yes | no
- Classification: no expansion | bounded foundational delta | prohibited expansion
```

### 2.2 审计判定

| 分类 | 处理 |
|---|---|
| `no expansion` | 在现有Execution Spec内直接裁决并继续，不询问owner |
| `bounded foundational delta` | 只能写入对应Owner Truth；必须说明改变哪条既有边界、明确上限、代价和新增non-goal，再由owner回答 |
| `prohibited expansion` | 停止推荐并defer；不得通过“可扩展”“future-ready”或“先预留”绕过 |

只要新增文件、domain、StateFamily、部署单元或开放式平台能力，默认就是`prohibited expansion`。Owner主动提出新的产品责任时，才可将其重分类为`bounded foundational delta`。

### 2.3 Foundational问题准入

一个问题只有同时满足以下全部条件，才可以提交owner：

1. 不能从新Owner Truth或已锁定baseline Truth唯一推导；
2. 会改变产品责任、外部可见语义、V1能力边界或成功标准；
3. 至少存在两个产品结果实质不同、均可成立的选择；
4. 问题可以完全不用表、字段、算法、框架或部署细节来表达。

Owner问题必须是单一决策轴，并包含：已继承Truth、推荐、Scope Impact Audit、选择后果和明确non-goal。单次最多提交3个问题；没有真实foundational分歧时提交0个。不得因owner回答而自动生成下一轮。

### 2.4 Execution问题处理

Execution问题必须按以下顺序自行关闭：

1. 应用新Owner Truth；
2. 直接复用§4登记的baseline locked Truth；
3. 检查`legacy-family/`的生产行为和失败证据；
4. 在现有边界内选择最小、可测试、可逆的方案；
5. 将选择、理由、反例和验收写入对应Execution Spec。

Execution问题不得创建owner QNA。若最终发现确实改变foundational结果，只提交一个去除实现细节后的foundational delta。

---

## 3. 两级文件清单

### 3.1 目录树与硬上限

```text
docs/specs/
├── index.md
├── owner-truth/
│   ├── 01-product-boundary.md
│   ├── 02-domain-model.md
│   ├── 03-capability-and-external-contract.md
│   └── 04-v1-success-and-non-goals.md
└── execution-spec/
    ├── 01-service-and-task-api.md
    ├── 02-workflow-runtime.md
    ├── 03-intake-and-cleaning.md
    ├── 04-persistence-and-artifact-storage.md
    ├── 05-inference-and-registry.md
    ├── 06-lsrag-build.md
    ├── 07-vector-and-retrieval.md
    └── 08-operations-security-and-deployment.md
```

上述清单就是本轮全部spec容量。图、风险、ADR、测试矩阵、spike结论和reference anchors必须作为所属文件的章节存在，不新增spec文件。

### 3.2 Level 1 — Owner Truth文件簇

| ID | 文件 | 只冻结什么 | 明确不讨论 | Baseline直接输入 | 初始状态 |
|---|---|---|---|---|---|
| `OT-01` | `owner-truth/01-product-boundary.md` | 产品定位、唯一上游类型、单体边界、信任边界、V1责任与out-of-scope | API字段、内部模块、存储、进程和算法 | OD-01..12、`T-O-42`、S01-v1.5 | `pending consolidation` |
| `OT-02` | `owner-truth/02-domain-model.md` | Task/Execution/Process、Intake、LS-RAG资产的核心身份、所有权和跨域不变量 | 表结构、transition实现、route和DDL | D01-v1.4、S04-v1.2、D02-v1.0 | `pending consolidation` |
| `OT-03` | `owner-truth/03-capability-and-external-contract.md` | V1可调用能力、输入类型、可观察Task/结果语义、LS-RAG与retrieval产品边界 | endpoint、payload schema、Process key、模型和索引实现 | S01-v1.5、S02-v1.3、S05-v1.1、S06 `T-O-77..85` | `pending consolidation` |
| `OT-04` | `owner-truth/04-v1-success-and-non-goals.md` | V1完成定义、用户可观察成功/失败、质量底线、容量上限和明确non-goals | 测试框架、benchmark实现、metric字段和运维步骤 | 已冻结acceptance不变量、owner当前范围指令 | `pending consolidation` |

Owner Truth文件只允许以下固定结构：

1. Inherited Locked Truth；
2. Foundational Statements；
3. Hard Scope / Non-goals；
4. Open Foundational Decisions（可以为空）；
5. Owner Decisions；
6. Constraints on Execution Specs；
7. Revision History。

不得在Owner Truth中加入execution方案、表设计、算法比较或实现任务。既有baseline已经给出明确答案时，只做原义搬运和来源标注，不再请求owner确认一次。

### 3.3 Level 2 — Execution Spec文件簇

| ID | 文件 | 唯一执行责任 | 合并覆盖的旧范围 | 关键依赖 | 初始状态 |
|---|---|---|---|---|---|
| `ES-01` | `execution-spec/01-service-and-task-api.md` | 服务入口、Team/token边界、Task/Audit/Restart、公共API与幂等 | S01 + S02 | OT-01..03 | `pending` |
| `ES-02` | `execution-spec/02-workflow-runtime.md` | Task→Execution→Process、Workflow、状态、claim/retry/cancel/recovery | D01 + S03 + D02 runtime部分 | OT-02..03、ES-01 | `pending` |
| `ES-03` | `execution-spec/03-intake-and-cleaning.md` | Source/Snapshot/Item/Revision/Artifact、acquisition、clean、preflight/gate | S04 + S05 | OT-02..03、ES-01..02 | `pending` |
| `ES-04` | `execution-spec/04-persistence-and-artifact-storage.md` | Turso关系持久化、事务、outbox、schema evolution、对象/Artifact存储 | S12 + S13及S01-S05持久化义务 | OT-01..02、ES-01..03 | `pending` |
| `ES-05` | `execution-spec/05-inference-and-registry.md` | 本地/外部推理adapter、模型/Prompt/Schema registry、能力与版本绑定 | S11 + S14 | OT-01、OT-03、ES-04 | `pending` |
| `ES-06` | `execution-spec/06-lsrag-build.md` | Structurizer + Constructor、grounding、双通道、generation与proof | S06 + S07 | OT-02..03、ES-03..05 | `pending` |
| `ES-07` | `execution-spec/07-vector-and-retrieval.md` | embedding、vector generation/index、publication、retrieval/traceback/rerank | S08 + S09 + S10 | OT-03、ES-04..06 | `pending` |
| `ES-08` | `execution-spec/08-operations-security-and-deployment.md` | 单体拓扑、配置、security、observability、recovery operation与系统验收 | S15 + S16 + 原17/18 | OT-01、OT-04、ES-01..07 | `pending` |

Execution Spec固定结构：

1. Inherited Truth；
2. Scope / Non-scope；
3. Scope Impact Audit；
4. Architecture Decisions；
5. Contracts and Data；
6. State / Consistency / Failure；
7. Legacy retain / rewrite / drop；
8. Acceptance Evidence；
9. Remaining Technical Decisions and Defaults；
10. Revision History。

`Remaining Technical Decisions`不是owner问题清单；文件作者必须给出默认方案、验证方式和改变默认值的技术证据。

---

## 4. Baseline Locked Truth导入表

### 4.1 权威顺序

发生不一致时按以下顺序处理：

1. 本目录最新的Owner Truth；
2. 本节登记的baseline locked Truth；
3. 本目录Execution Spec；
4. `legacy-family/`和`legacy-python/`证据。

新Owner Truth只有明确写出“替代哪条baseline Truth”时才构成覆盖；否则baseline locked Truth继续有效。

### 4.2 直接继承清单

| Locked source | 直接继承的内容 | 写入新文件 |
|---|---|---|
| `docs/baseline/spec-index.md` OD-01..12 | leaf-worker、单体、上游、team/token、UUID、Turso方向、adapter-first、LS-RAG核心、无UI/平台 | OT-01、OT-03、ES-01/04/05/08 |
| `docs/baseline/domain-truth/S01-skill-worker-integration.md` v1.5 | standalone contract、最小Team Registry、Task/Audit入口、polling、内部token、未来adapter边界 | OT-01/03、ES-01 |
| `docs/baseline/domain-truth/D01-task-execution-process-flow.md` v1.4 | Task/Execution/Process三层身份、single/scatter、控制向下/proof向上 | OT-02、ES-02 |
| `docs/baseline/domain-truth/S02-task-api.md` v1.3 / `T-O-1..11` | Task六态、CAS、collect-all、cancel、retry/rebuild、readiness和lineage | OT-03、ES-01/02 |
| `docs/baseline/domain-truth/S03-workflow-engine.md` v1.3 / `T-O-12..29` | 声明式Workflow、Execution/Process八态、claim/fence/retry/recovery与typed outcome | ES-02/04/08 |
| `docs/baseline/domain-truth/S04-intake-asset-lifecycle.md` v1.2 / `T-O-30..48` | 五类Intake身份、immutable Revision、Candidate acceptance、serving/lifecycle/cleanup | OT-02、ES-03/04/07 |
| `docs/baseline/domain-truth/S05-intake-cleaning.md` v1.1 / `T-O-49..76` | 四类source、完整clean能力、typed evidence、mandatory preflight与ExecutionGate | OT-03、ES-03/05 |
| `docs/baseline/qna-truth/S06.md` `T-O-77..85` | immutable generation历史/current selection、versioned structure schema、kernel/extension/repair边界 | OT-03、ES-05/06 |
| `docs/baseline/domain-truth/D02-production-state-and-routing.md` v1.0 / `T-O-86..92` | 六StateFamily、state-vs-fact、唯一owner、跨域非法行为与fail-closed原则 | OT-02、全部Execution Spec |
| `docs/baseline/spec-glossary.md` v1.4 | 已冻结canonical vocabulary | 全部文件 |

### 4.3 不导入的旧内容

以下内容不属于locked product/domain Truth，不迁入新流程：

- 旧16子系统文件数量和逐一QNA编排；
- `3 + 3 + 3`提问机制、自动生成下一轮和execution owner-gate；
- baseline中的`OPEN/PROPOSED/CONFLICT/held/reframe`候选答案；
- 为旧文档治理建立的中间文档、状态台账或重复镜像工作；
- legacy的Cloudflare拓扑、wire、schema、UUID/status、storage和兼容假设。

若旧候选内容对Execution仍有价值，只能作为证据重新评估，不能因曾被写入baseline而获得Truth状态。

---

## 5. 工作顺序与依赖

### 5.1 固定顺序

| 阶段 | 工作 | Owner参与 |
|---|---|---|
| `P0` | 将baseline locked Truth原义归并到OT-01..04 | 只审阅真正的foundational delta；无delta则不提问 |
| `P1` | 完成ES-01 Service/Task与ES-02 Workflow Runtime | 不参与execution选择 |
| `P2` | 完成ES-03 Intake/Cleaning、ES-04 Persistence/Storage、ES-05 Inference/Registry | 仅当出现合格foundational delta时参与 |
| `P3` | 完成ES-06 LS-RAG Build与ES-07 Vector/Retrieval | 不参与算法、schema、模型或索引选择 |
| `P4` | 完成ES-08 Operations/Security/Deployment并做全系统验收对账 | 只确认OT-04中的产品成功标准，不审批执行细节 |

### 5.2 禁止的推进方式

- 不因某个Execution Spec尚未设计，就提前扩大Owner Truth问题；
- 不跨过依赖设计未来domain的exact schema；
- 不把实现未知包装成产品未知；
- 不为保持“可扩展性”预先设计未进入V1的plugin、multi-backend、multi-service或generic policy平台；
- 不创建新的全局状态、router、registry或projection来规避现有owner边界；
- 不要求全部文件一次性完美后才开始验证；每份Execution Spec达到`ready`即提供可验证contract。

---

## 6. 状态与完成定义

### 6.1 文件状态

Owner Truth：

```text
pending consolidation → owner-review-needed | no-new-decision → frozen
```

- `owner-review-needed`只允许存在合格的foundational问题；
- baseline原义归并不需要owner重复批准，可直接标记`no-new-decision → frozen`。

Execution Spec：

```text
pending → drafting → internally-consistent → ready → superseded
```

Execution Spec没有`owner-gate`状态。技术未知不能使owner成为默认审批者。

`ready`是文档生命周期状态：表示该ES的normative设计、默认裁决、状态机、链路、schema、port/protocol、failure boundary与HARD验证合同完整，且通过cross-spec audit。它不表示尚未构建的实现已经跑完acceptance，也不等于release promotion；实现只有实际通过对应HARD evidence后才可声明conforming。

Index：

```text
active → specification-ready → superseded
```

### 6.2 本轮完成条件

只有同时满足以下条件，本索引才进入`specification-ready`：

1. OT-01..04均已冻结，且没有execution内容混入；
2. ES-01..08均达到`ready`；
3. 每份Execution Spec都完整列出baseline继承来源和Scope Impact Audit；
4. 所有foundational问题均符合§2.3，且没有自动衍生问题；
5. 所有execution问题均在对应Spec内得到默认裁决或验证路径；
6. 没有新增文件、domain、StateFamily、部署单元或V1能力；
7. OT-04的产品成功标准可以由ES-01..08的验收证据闭合。

### 6.3 当前状态

| 项目 | 状态 |
|---|---|
| 新索引 | `specification-ready / v1.0` |
| Owner Truth文件 | `4/4 created and frozen`；OT-01..04均为`frozen / v1.0` |
| Execution Spec文件 | `8/8 ready / v1.0`；ES-01..08均完成最终cross-spec audit并冻结版本引用 |
| Owner logical table inventory | `113 mapped`；ES-01 4 + ES-02 9 + ES-03 34 + ES-05 18 + ES-06 21 + ES-07 24 + ES-08 3；另有ES-04 13张infrastructure tables，总计126张project-owned physical tables |
| HARD acceptance inventory | `722 verified`；ES-01 45 + ES-02 60 + ES-03 86 + ES-04 112 + ES-05 110 + ES-06 94 + ES-07 115 + ES-08 100；各文件从001连续、全局无duplicate/skip/waiver |
| Baseline locked Truth mapping | `closed`；§4.2全部来源已在ES-08-v1.0 §8.12逐项对账 |
| 新foundational问题 | `0 open`；OT-04 Q1已选择A并固化：有限代表性semantic retrieval usefulness是V1 release gate，exact验收设计归ES-07/08 |
| Scope expansion | `none` |

### 6.4 Final specification audit

| Audit dimension | Frozen result |
|---|---|
| Owner Truth | 4份、207个本体ID：OT-01 34 + OT-02 43 + OT-03 63 + OT-04 67；连续且全部映射 |
| State constitution | 6个且仅6个StateFamily；exact state set、合法边与唯一owner对齐D02-v1.0/OT-02-v1.0 |
| External/product boundary | 6个异步intent、1个同步semantic retrieval capability、33条产品route；无raw vector、final answer、callback或operator API |
| Execution catalogs | 4类source、8个Workflow、26个Process manifest；跨ES集合相等且无legacy alias |
| Persistence/atomicity | 113张owner tables + 13张infrastructure tables = 126张physical tables；55个named UoW，无missing/extra/duplicate |
| Verification contract | 722项HARD acceptance连续无缺号；16-document/32-query semantic gate只作为有限release evidence |
| Truth precedence | Owner Truth > baseline locked Truth > Execution Spec > legacy evidence；未发现冲突、反向覆盖或未归属owner write |
| Scope/capacity | 仍为4+8文件、1个Python应用/发布单元、既有能力上限；未增加domain、StateFamily、service、backend或产品责任 |

完整inclusive-ID trace、baseline闭包、inventory与审计边界见ES-08-v1.0 §8.12。该结论表示规范已经可实现、可验证；不表示实现、硬件测量或release acceptance已经运行。

---

## 7. 修订历史

| 版本 | 日期 | 变更 |
|---|---|---|
| `v0.1` | `2026-08-10` | 按owner要求废止baseline的旧讨论编排，在`docs/specs/`重新开始；建立4份Owner Truth与8份Execution Spec的固定两级清单，直接映射baseline locked Truth，禁止execution owner-gate和自动QNA，并增加推荐前Scope Impact Audit及项目容量硬上限。 |
| `v0.2` | `2026-08-10` | 创建OT-01 Product Boundary基础文件并完成baseline locked Truth原义导入；未生成QNA，未新增文件槽位、产品能力、domain、StateFamily或部署单元。 |
| `v0.3` | `2026-08-10` | 启动OT-01 foundational QNA Round 1；准入且仅准入baseline G-07 final-answer责任边界，登记推荐回答、Scope Impact Audit、reasoning、选择后果与non-goals；未采纳任何scope expansion。 |
| `v0.4` | `2026-08-10` | 冻结OT-01-v1.0：MKB收口为文档清洗、结构化、LS-RAG结构化向量存储及上游检索/消费工具；final answer与全部上游业务OOS；内部流转状态和生命周期继续由MKB自持。Q1关闭且无后续轮次。 |
| `v0.5` | `2026-08-10` | 创建OT-02 Domain Model基础文件并完成D01-v1.4、S04-v1.2、D02-v1.0冻结Truth导入；固化runtime/Intake/derived asset身份分账、六StateFamily与state-vs-fact边界；未生成QNA或新增domain、状态族、文件槽位与产品范围。 |
| `v0.6` | `2026-08-10` | 完成OT-02 foundational QNA准入：0题通过；runtime/Intake/StateFamily均已有冻结Truth，derived asset剩余exact kind/schema/transaction归既有Execution Spec。OT-02以`no-new-decision`冻结为v1.0，不生成下一轮。 |
| `v0.7` | `2026-08-10` | 创建OT-03 Capability and External Contract基础文件；原义归并S01-v1.5、S02-v1.3、S05-v1.1、S06 `T-O-77..85`及OT-01/02冻结Truth，固化有限调用能力、四类source、Task/result可观察语义和LS-RAG/retrieval截止线；排除S06未冻结内容与全部endpoint/payload/Process key、模型/索引实现；未启动或生成QNA。 |
| `v0.8` | `2026-08-10` | 启动OT-03 foundational QNA Round 1；准入且仅准入“上游消费向量是否包含raw vector read/export”，推荐保持vector substrate内部化、只公开semantic Retrieval Result，并登记完整Scope Impact Audit、reasoning、选择后果、non-goals及候选剔除审计；Q1等待owner回答，不生成第2/3题或后续轮次。 |
| `v0.9` | `2026-08-10` | 冻结OT-03-v1.0：Owner选择A并明确不提供最低等级raw vector；公共Contract只提供同步semantic Retrieval Result，raw vector read/list/export、VectorRecord CRUD、caller-supplied raw-vector query及通用vector database surface全部OOS。Q1关闭，closure审计0个新增问题，不生成Round 2。 |
| `v0.10` | `2026-08-10` | 创建OT-04 V1 Success and Non-goals基础文件；原义归并index固定容量、OT-01..03及baseline冻结acceptance不变量，固化端到端完成定义、caller-observable成功/失败、质量底线、容量上限和明确non-goals；测试框架、benchmark实现、metric字段、SLA数值及运维步骤全部下沉既有Execution Spec；未启动或生成QNA。 |
| `v0.11` | `2026-08-10` | 启动OT-04 foundational QNA Round 1；准入且仅准入“semantic retrieval usefulness是否属于V1完成门槛”，推荐以有限、代表性场景证明预期grounded evidence可被找回，exact corpus/metric/threshold/tool归ES-07/08；登记Scope Impact Audit、完整reasoning、选择后果、non-goals及候选剔除审计。Q1等待Owner回答，不生成第2/3题。 |
| `v0.12` | `2026-08-10` | 冻结OT-04-v1.0：Owner选择A，将有限、项目自有、代表性的semantic retrieval usefulness固化为V1 release gate；仅contract/schema/proof/traceback结构正确但无法找回预期knowledge不算V1成功。Exact corpus、query数量、metric、阈值、topK、模型、索引、ranking/rerank、回归机制与工具归ES-07/08；Q1关闭、不生成Round 2。至此4/4 Owner Truth均已冻结，Execution Spec仍为0/8，因此索引保持`active`而不提前进入`specification-ready`。 |
| `v0.13` | `2026-08-10` | 创建ES-01 Service and Task API v0.1并达到`internally-consistent`：冻结caller-neutral HTTP/JSON contract、Team接入投影、六种异步intent与同步retrieval截止线、Task/Audit/Restart wire、Task六态及五轴polling、原子事务、幂等/CAS、四张逻辑业务表、application ports和at-least-once内部消息；吸收legacy身份/scatter/restart经验并删除平台、callback与多Worker拓扑。ES-01仍等待ES-02..08完成后的cross-spec audit，不提前标记`ready`。 |
| `v0.14` | `2026-08-10` | 创建ES-02 Workflow Runtime v0.1并达到`internally-consistent`：冻结六平面Workflow、七张normalized Truth表、deterministic compiler、八个有限Workflow、Execution/Process八态、typed route/guard、claim/lease/fence、retry/recovery/cancel、single/scatter执行链、application ports和durable protocol；同步将S03-v1.3已冻结的Workflow list/get只读面补入ES-01-v0.2。两份文件仍等待ES-03..08及全量cross-spec audit，不提前标记`ready`。 |
| `v0.15` | `2026-08-10` | 创建ES-03 Intake and Cleaning v0.1并达到`internally-consistent`：冻结四类source descriptor、source/binding、18个Process capability、ExternalKey/canonicalization/RevisionFingerprint、十张canonical及supporting逻辑schema、Candidate/Item/Gate状态机、mandatory preflight→seal→accept、single/scatter/metadata/lifecycle/publication/Gate链路、ports/messages、failure/recovery/cleanup与78项acceptance；关闭D02移交的Membership decision和Gate action exact spelling。同步校准ES-02-v0.2的root preflight顺序、scatter child item-scoped preflight与最多一次acyclic reclean。前三份仍等待ES-04..08及全量cross-spec audit，不提前标记`ready`。 |
| `v0.16` | `2026-08-10` | 创建ES-04 Persistence and Artifact Storage v0.1并达到`internally-consistent`：冻结pyturso 0.7.0 embedded、单进程单persistence lane、WAL/FULL/BEGIN IMMEDIATE、统一physical schema与forward-only migration、named UoW、DB outbox/inbox/event、local Team-scoped CAS object store、bytes-first/reference/GC和quiesced backup/restore；登记ES-01..03共47张owner表及13张ES-04 infrastructure tables，提供factual automata、failure matrix、ports/protocols与86项HARD acceptance。四份文件仍等待ES-05..08、下游table mapping回填及全量cross-spec audit，不提前标记`ready`。 |
| `v0.17` | `2026-08-10` | 创建ES-05 Inference and Registry v0.1并达到`internally-consistent`：冻结finite code-owned Capability/Schema/Model/Prompt/InferenceProfile registry、ES-03全部18个Process manifest、Tesseract 5.5.2 local OCR、Gemini 3.6 Flash external structured inference、exact no-hot-switch binding与reserve-before-call GenerationInvocation；提供18张逻辑表、完整ports/protocols、factual automata、failure/ambiguity matrix与90项HARD acceptance。同步将18表与5个named UoW登记进ES-04-v0.2，使当前owner-table physical inventory达到65张。五份文件仍等待ES-06..08、下游registry/schema mapping回填及全量cross-spec audit，不提前标记`ready`。 |
| `v0.18` | `2026-08-10` | 创建ES-06 LS-RAG Build v0.1并达到`internally-consistent`：冻结`lsrag.structurize/construct`两个Process、8-component StructureSchema、deterministic SourceElement/tree/node/anchor/coverage、ConstructionUnit、passage original/summary与section/document summary、五类GenerationArtifact/current/coherent commit、extension-only repair、21张logical tables、Task-scoped metadata read、ports/protocols及86项HARD acceptance。同步校准ES-01-v0.3 artifact read、ES-05-v0.2两个manifest/四套Prompt/Profile/Schema bundle，以及ES-04-v0.3 21表/4 UoW，使owner-table inventory达到86张。六份文件仍等待ES-07..08及全量cross-spec audit，不提前标记`ready`。 |
| v0.19 | 2026-08-10 | 创建ES-07 Vector and Retrieval v0.1并达到internally-consistent：冻结gemini-embedding-2 text-768 EmbeddingSpace、六个Process、24张logical tables、VectorRecord/IndexGeneration/PublicationProof/dual pointer、filter reuse/withdraw/reindex/cleanup、embedded Turso exact cosine search、四strata recall、deterministic RRF、mandatory original traceback、唯一public RetrievalSearch/Result、115项HARD acceptance与16-document/32-query release gate。同步校准ES-01-v0.4、ES-02-v0.3、ES-03-v0.2、ES-04-v0.4、ES-05-v0.3、ES-06-v0.2，使owner-table inventory达到110。未新增raw vector、final answer、source、intent、Workflow、StateFamily、backend、服务或spec；七份文件仍等待ES-08与全量audit，不提前标记ready。 |
| v0.20 | 2026-08-10 | 创建ES-08 Operations, Security and Deployment v0.1并达到internally-consistent：冻结单OCI/单长期Python process、strict config/secret、simple-token rotation、TLS/ingress、SSRF/egress/browser sandbox、bounded runtime、health/readiness/shutdown、closed telemetry/metrics、finite local CLI、3张operational evidence表、backup/restore/retention/recovery、measured-envelope contract与100项HARD release acceptance。同步将3表与6个UoW登记ES-04-v0.5，使owner-table inventory达到113、physical总表126、全项目HARD acceptance达到722；回填ES-01/02/03/05/06/07的retention/security/resource槽位。未新增产品能力、StateFamily、Workflow、Process capability、provider、backend、服务、deployment unit、operator平台或spec；8份文件进入最终cross-spec audit，尚未提前标记ready。 |
| v1.0 | 2026-08-10 | 完成最终truth/contract/schema/state/UoW/acceptance审计并冻结全部ES为v1.0 ready：4份Owner Truth共207 ID、6 StateFamily、33产品routes、4 source、8 Workflow、26 Process、113 owner + 13 infrastructure tables、55 UoW及722项HARD acceptance均set-exact；ES-08 §8.12记录full trace。未发现规范级冲突或盲点，未新增文件、QNA、产品能力、状态族、服务、backend或部署单元；索引进入specification-ready。 |
