# D03 — Repository Layout & Module Division Constitution

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 共有域**：跨全部子系统的 **仓库目录宪法、模块分工与依赖方向**
>
> **文档性质**：`shared-domain constitution / repository architecture truth`
>
> **文档状态**：`accepted / owner-frozen`（域内已接受；全系统 truth layer 尚未统一 frozen）
>
> **Truth 版本 / 日期**：`D03-v1.0 / 2026-08-11`
>
> **作者 / 裁决**：`MKB owner` 发起并批准；`Codex` 规范化与跨 Spec 对齐
>
> **权威输入**：Owner 目录宪法裁决 `OD-D03-01..12`；legacy-family Workflow/SMCP ReferenceAnchor；`D01-v1.4`、`D02-v1.0`、`S01–S07-v1.0`、`S12-v1.0`、`S13-v1.0`；冻结 Truth `T-O-141..159`
>
> **词汇权威**：`spec-glossary.md v1.9`
>
> **下游消费者**：实现仓库脚手架、architecture tests、`17` topology（运行挂载）、各 Sxx 实现落点、CI 路径约定

> **Owner-originated 声明**：目录宪法由 **业主发起并强制**；不是从 legacy 包结构“翻译”而来。legacy-family 仅用于理解 **Workflow 定义 vs Runtime 引擎** 的分账，禁止复制 Worker/包边界为 MKB 目录真相。

> **与 `17` 分账**：D03 冻结 **仓库内放什么、谁可 import 谁**；`17` 冻结 **进程、环境变量、挂载路径、多实例** 等运行拓扑。二者冲突时：路径**名字与职责**以 D03 为准，**部署实例如何指向 data/** 以 17 为准。

> **与业务 Spec 分账（产品 vs 类型）**：
> - **产品/状态/不变量/算法叙事**：仍以 `docs/baseline` 各 Domain Spec（D01–D02、S01–S16）为准；D03 **不**改写状态机合法边或产品 scope。
> - **Typed schema / 消息体形状 / 运行期类型解释**：**唯一 SSOT = `src/contracts/`**（本宪法约束）。系统内 **禁止** 第二套并行 typed 真相（禁止 services 私有 pydantic 模型当跨层合同、禁止 Spec 旁路手写重复 schema 并在运行期双解）。
> - **冲突裁决**：若 baseline 叙述与 contracts 中已登记的 typed schema **在形状/字段/校验规则上冲突**，**以 D03 约束的 contracts 为解释与执行 SSOT**；须随后回填 Spec 消除文档漂移（不得长期双源）。
> - **目录落点**：代码/数据/测试路径以 D03 为准。

> **与 `spec-index` 阶段纪律**：index 曾写“本阶段不产出代码目录细节”。**D03 为 Owner 发起的有限例外**，仅冻结仓库宪法与协议 SSOT 落点，不开放随意实现排期。

> **冻结声明**：Owner 2026-08-11 批准本文件为真相层一部分。§2 全域 `T-O-141..159` 与域内 `D03-T*` 一一对应，**append-only**；变更须显式 reopen D03。

> **D08 校准（2026-08-13）**：`D08-v0.1` **reopen §4.3「禁止在 intake 内实现 clean」**。`intake/{api,doc,pdf,web}` 是四域 **源适配 + 清洗变换** 的唯一实现点（`D08-T006`）。`src/runtime` 只围栏；S04 表权威仍不在 intake。D03-T004 顶级四域目录 **不改**。完整树与禁止事项以 D08 §4.3 为准。

---

## 1. Domain 介绍

### 1.1 Domain 价值

D03 回答：在 **单体 leaf-worker（OD-06）** 仓库中，如何用 **稳定顶级目录与模块分工** 落实：

1. S01 对外合同面与内部运维面分离；  
2. S03 **声明式 Workflow 程序** 与 **Runtime 引擎** 分账（Workflow ≠ Runtime）；  
3. **`src/contracts/` 作为全仓 typed 协议层**（类比 TypeScript Zod / legacy SMCP+域内 schemas）：**按域分册** 的强制 schema + 校验；业务流转、内部消息、API 载荷非法即失败抛弃；  
4. S05 多源 intake 适配作为 **一等顶级栏目**；  
5. S11 LLM adapters、S12 persistence、S13 object storage 的适配落点；  
6. S12/S13/S14 运行时 substrate 与 **可版本控制的 prompts** 落点；  
7. 测试与对外静态资源、文档真相的边界；  
8. v1 **禁止** frontend 业务依赖。

没有 D03，实现期易出现：`services` 吞掉 intake、workflows 变成第二状态机、**跨层自由 dict 通信**、对象盘与 git 资源混淆、public API 扩权、Port 纪律被 `pathlib`/driver 直接击穿。

### 1.2 Scope fence

**D03 负责：**

- `MKB_root/` 顶级目录闭集与职责；  
- 关键子目录职责与 **禁止事项**；  
- **依赖方向**（import 图）与 architecture test 可验收规则；  
- git 跟踪 vs gitignore 的目录级纪律（尤其 `data/`、prompts）；  
- **`src/contracts/` 作为全系统 typed schema 唯一 SSOT 的落点与强制校验纪律**；  
- 与 Sxx 子系统的 **落点映射表**（非完整实现清单）。

**D03 不负责：**

| 排除项 | 归属 |
|---|---|
| Task/Execution/Process 状态机 | D01 / S02 / S03 |
| 声明式 Workflow **产品/编排语义**（非 typed 形状 SSOT） | S03 |
| Intake identity / Generation **产品不变量**（状态、指针、proof 叙事） | S04–S07 |
| 上述域的 **typed 消息/命令/结果形状的运行期解释** | **`src/contracts/`（本宪法）** |
| Turso/对象具体 driver 参数、备份排程 | S12 / S13 / S15 / `17` |
| frontend 产品 | **v2**；v1 仅预留空目录或 README |
| 包发布/多 distribution | 禁止；单体一个发布单元 |

### 1.3 已确认的业主强制裁决（审查输入）

| ID | 业主裁决（2026-08-11） | 冻结 Truth |
|---|---|---|
| `OD-D03-01` | **`intake/` 必须为顶级栏目**，不得收进 `services/` | `T-O-144` |
| `OD-D03-02` | 持久化/对象适配：**`src/persistence` + `src/storage` + `data/objects`** | `T-O-145` |
| `OD-D03-03` | **prompts 必须 git 跟踪**（正文版本管理） | `T-O-146` / `T-O-155` |
| `OD-D03-04` | 测试根目录 **`tests/`** | `T-O-147` |
| `OD-D03-05` | 公开资源根 **`public/`** | `T-O-148` |
| `OD-D03-06` | Workflows **不是** runtime 替代品 | `T-O-143` |
| `OD-D03-07` | 协议目录 **`src/contracts/`** | `T-O-152` |
| `OD-D03-08` | contracts **按域分册** | `T-O-152` |
| `OD-D03-09` | 任何消息体必校验；非法 **报错并抛弃** | `T-O-152` / `T-O-153` |
| `OD-D03-10` | contracts typed schema = **全系统唯一 SSOT**；运行期唯一解释 | `T-O-152` / `T-O-154` |
| `OD-D03-11` | prompts：git 正文 + DB **hash 指针**；hash 真值校验 | `T-O-146` / `T-O-155` |
| `OD-D03-12` | 收紧消息体范围、Workflow slot/handle、intake 边界 | `T-O-143` / `T-O-154` |

### 1.4 Domain 完成定义

1. §2 `T-O-141..159` 已冻结并可映射到脚手架与 architecture tests；  
2. 目标树与依赖方向无歧义；  
3. contracts 为 typed 唯一 SSOT；prompts = git 正文 + DB hash；  
4. `spec-index` / glossary 已回填；  
5. §6 HARD 验收可在实现期执行（非本文件冒充已实现）。

---

## 2. 真相层（已冻结）

> 全局 Truth-ID：`T-O-141..159`（接续 S07 `T-O-140`）。域内 `D03-T*` 为同文引用别名，**不**构成第二编号空间的改写权。

### 2.1 Owner / 域内 Truth 台账（append-only）

| Truth-ID | 域内 ID | 已锁定真相 | 来源 | 下游约束 |
|---|---|---|---|---|
| `T-O-141` | `D03-T001` | D03 是 MKB **仓库目录与模块分工宪法**；不拥有业务状态机与 DDL。 | Owner + index 分账 | 实现脚手架必须服从 |
| `T-O-142` | `D03-T002` | v1 为 **单一发布单元** 的单体仓库；禁止按 legacy Worker 复制多包 runtime 依赖。 | OD-06、T-O-42 | 无 multi-package 发布 |
| `T-O-143` | `D03-T003` | **Workflow 定义 ≠ Runtime 引擎**：声明式管线程序（工序能力、顺序/拓扑意图、**logical slot / handle 绑定**、参数绑定、有限控制挂点）存放于定义目录；claim/outbox/Process 推进/重试只属于 `src/runtime/`（及 S12 兑现）。定义目录 **禁止** 实现状态机或 next-step 调度；定义中的 I/O **不得**以 path/bucket/r2_key 作跨层身份（对齐 S13）。 | Owner + S03 + S13 | 见 §2.2 |
| `T-O-144` | `D03-T004` | **`intake/` 为仓库顶级栏目**（与 `src/` 并列）；承载多源 intake **适配实现**（api/doc/pdf/web…）。**禁止** 将 intake 适配收编进 `src/services/` 作为唯一落点。 | Owner | S05 源侧代码落点 |
| `T-O-145` | `D03-T005` | 必须显式存在：`src/persistence/`（S12 Ports/adapter）、`src/storage/`（S13 ObjectStorePort/adapter）、`data/objects/`（S13 object_root 默认相对落点）。Domain/services **禁止** 直接 `import` DB driver 或对 object_root 裸 pathlib 写。 | Owner 接受 Q-C 推荐 | S12/S13 纪律 |
| `T-O-146` | `D03-T006` | **Prompt 文本权威树 = `data/prompts/**` 且必须 git 跟踪**（版本管理载体）。数据库 **不得** 再存 prompt 正文副本作为第二真相；库内仅存 **prompt content hash（及可选 path/key 指针）**。持有/运用 prompt 时必须用 hash 做唯一真值校验（文件内容 hash 与指针一致才可用）。`data/database/` 运行库文件、`data/objects/` 字节、密钥默认 gitignore。 | Owner OD-D03-03/11 | S14 可登记 hash；无双正文 |
| `T-O-147` | `D03-T007` | 测试根目录名为 **`tests/`**，至少含 `e2e/`、`unit/`、`domain/`（HARD/golden）。 | Owner | CI 路径 |
| `T-O-148` | `D03-T008` | 公开静态/可分发资源根为 **`public/`**（非 `asset`/`assets`）；语义=对外可用资源。**禁止** 把 S13 运行时对象盘或业务 SSOT 放进 `public/`。 | Owner | 与 data/objects 分账 |
| `T-O-149` | `D03-T009` | `api/public/` 仅 S01 Task 合同面；`api/internal/` 仅 health/readiness/metrics 等运维面；v1 **无** 公网 object/construct CRUD/浏览器。 | S01、S07-T024、OD-01 | API 扩权 gate |
| `T-O-150` | `D03-T010` | `src/services/` = **原子 Process/domain capability 实现**（无私有 retry 状态机）；编排与 claim 不在此包。 | S03/S05–S10 | |
| `T-O-151` | `D03-T011` | `src/llm_adapters/` = S11 **Adapter 对接层**；不得拥有 Workflow 图或 Intake 真相写面。**Inference 门面**落在 `src/runtime/inference/`（S11-v1.0 / `T-O-189/196`），属 Runtime 细化，**不**新增顶级目录。services 禁止 import llm_adapters。 | S11 | |
| `T-O-152` | `D03-T012` | **`src/contracts/` = 全系统 Typed Schema 唯一 SSOT + 强制校验层**（业主命名；类比 Zod）。按域分册定义：业务流转、内部消息、API、outbox/事件、ProcessCommand/Outcome、Workflow 定义文档形状、handle/digest 等 **一切结构化消息体 schema**。**禁止双源真相**：不得在 services/runtime/api 另建平行 schema 作为跨层合同；S06/S07 等 Spec 中的 schema 叙述若与 contracts **冲突，以 contracts 为解释与执行 SSOT**，并回填 Spec。运行期 **唯一解释 SSOT** = 经 contracts 校验得到的 **typed 对象实例**（不得再按原始 dict 二次解释）。任何跨边界结构化消息必须校验通过；非法 → 报错并抛弃。允许纯校验/编解码；禁止 I/O/DB/LLM/状态推进。 | Owner OD-D03-07..10 | 见 §2.3 / §2.4 |
| `T-O-153` | `D03-T017` | **Fail-closed 抛弃语义**：校验失败 → typed `ContractValidationError`；**丢弃消息体**；不 partial apply；API→4xx；工序→fail-loud；outbox 不得入队非法体。禁止 silent coerce。 | Owner OD-D03-09 | |
| `T-O-154` | `D03-T018` | **结构化消息体范围**：须经 contracts 的是跨 `api`/`runtime`/`services`/`intake`/`persistence` 边界传递的 **结构化逻辑载荷**（JSON/RPC/Command/Outcome/API/outbox/事件/已解析业务对象）。**不**把下列当作“自由 dict 合同”绕过：① 对象 **原始字节流**（S13 Port 内 digest/size 校验）；② 模型 **未 parse 的原始 token 流**（必须在进入跨层业务前 parse 进 contracts）。 | 核查建议 + Owner 同意 | 对齐 S11/S13 |
| `T-O-155` | `D03-T019` | **Prompt 双层存储无冲突**：git 持有正文；DB 持有 **hash 指针**；运用时 `hash(file bytes)==stored_hash` 否则 fail-closed。禁止 DB 存第二份可漂移正文。 | Owner OD-D03-11 | S14 登记 hash |
| `T-O-156` | `D03-T013` | `docs/baseline/**` 为 specification/truth **唯一文档树**；实现不得在 `src/` 维护第二套业务真相 SSOT。 | 既有 baseline | |
| `T-O-157` | `D03-T014` | `frontend/` 仅 **v2 预留**；v1 构建/运行路径 **不得** 依赖 frontend 交付业务能力。 | Owner 提案 | |
| `T-O-158` | `D03-T015` | 强制依赖方向见 §3.3；违反则 architecture test 失败。 | 本草案 | CI |
| `T-O-159` | `D03-T016` | `data/config/` 可跟踪非秘密默认配置；密钥与环境私密 **禁止** 进 git（环境/密钥管理归 S16/`17`）。 | 安全默认 | S16 |

### 2.2 Workflow 定义（D03 采用的规范表述）

> 与业主确认的理解一致，写入 D03 以免目录命名回潮。

**Workflow（定义）**：可版本化的 **声明式管线程序**——声明工序 capability、顺序/拓扑意图、**logical I/O 槽位契约**（slot 名 + handle/digest 绑定意图，**禁止** r2_key/path 作跨层身份）、非文件参数绑定、以及有限控制策略挂点。它描述 **“应如何连接”**，**不**承载 **“正在执行”**。

**Runtime（引擎）**：加载/解释 Workflow 定义，结合 Task/Execution/Process 状态、claim/fence、outbox、对象与关系 substrate，推进工序实例并处理失败/重试的 **执行系统**。

**SMCP/生产考古结论（ReferenceAnchor，非 wire 继承）**：定义在 catalog JSON；dispatcher 物化 I/O、写 process 行、发 STEP 消息；skill 只执行单步；callback 推进程序计数器。故 **workflows 目录绝不能替代 runtime**。

### 2.3 `src/contracts/` — Typed Protocol Layer（规范表述）

> 业主纠正：目录可命名 **`contracts`**；作用对标 Zod；单体下 **分域**；**凡消息体必校验，非法即报错抛弃**。

#### 2.3.1 legacy-family 协议层考古（ReferenceAnchor · 非 wire 继承）

微服务体系下，协议实际是 **两层**：

| 层 | 典型文件 | 内容 |
|---|---|---|
| **共享跨服务协议（SMCP）** | 各 worker 的 `core/schemas_smcp.ts`（多包 **复制** 同一“宪法”） | 跨 Worker 异步消息 envelope：`authority` / `workflow` / `io_payload` / `control_payload` / `input|output|error`；意图：`WORKFLOW_START`、`STEP_START`/`RESTART`、`STEP_CALLBACK` |
| **服务内域 schemas** | 各 worker 的 `core/schemas_common.ts`、provider `schemas.ts` | 该服务私有：Env、DB 行形状、WorkflowDefinition 本地视图、业务 artifact（如 layered JSON）、RPC restart 等 |

SMCP 自称「Worker 之间通信的宪法与单一事实来源」（`schemas_smcp.ts` 头注释），用 Zod **在边界强制 parse**。  
痛点（反例）：SMCP 被 **复制** 到十余个包，版本漂移（如 callback 是否必带 authority）；`schemas_common` 与 SMCP 字段名偶发不一致。

**MKB 单体结论：**

1. **保留**「边界 Zod 级强制校验」与「共享信封 + 域内载荷」分层思想；  
2. **删除** 多包复制 SMCP wire 与 R2 key 合同；  
3. **改为** 单仓 `src/contracts/` **分域源码树**，一处定义、全仓 import，避免复制漂移。

#### 2.3.2 是什么 / 不是什么

| 是 | 不是 |
|---|---|
| 全仓 **typed schema 唯一 SSOT** + 强制 validate | 可选工具库、空 DTO 目录 |
| **按域分册** 的请求/响应/事件/Command/Outcome 合同 | services 内私有平行 schema 当跨层合同 |
| 运行期 **唯一解释** 用的 typed 对象来源 | 对同一载荷用 raw dict 二次解读 |
| 非法消息 **立即失败并抛弃** | silent coerce / 半处理后补洞 |
| 纯函数校验与编解码 | I/O、DB、LLM、状态机 |

#### 2.3.3 唯一 SSOT 与冲突裁决（Owner HARD · OD-D03-10）

1. **唯一 SSOT**：一切结构化消息/类型的 **schema 定义与校验规则** 只存在于 `src/contracts/`（分域）。  
2. **禁止双源**：不得在 `services/`、`runtime/`、`api/`、`intake/` 维护第二套“也算合同”的 schema 副本并用于跨层传递。  
3. **运行期解释**：业务代码只消费 **contracts 校验后的 typed 对象**；禁止“校验完仍按原始 dict 字段自由读写当真相”。  
4. **与 baseline Spec**：Spec 描述产品不变量与状态机；**typed 形状以 contracts 为准**。冲突时 **执行 contracts**，并开 Spec 回填消除文档漂移（不得靠“Spec 另说”在运行期分叉）。  
5. **与 S06/S07 Schema Registry**：registry 可存 **schema_key/version/content_digest** 指向 contracts 中不可变定义；**不得**在 registry 再存一份与 contracts 不一致的 shape 正文。digest 必须能复验 contracts 内容。

#### 2.3.4 强制传递与消息体范围（Owner HARD）

**必须**经 contracts 校验的 **结构化消息体** 包括（不限于）：

- HTTP API 请求/响应体；  
- 内部 RPC / 进程内跨模块调用的结构化参数与返回值；  
- ProcessCommand / ProcessOutcome；  
- transactional outbox / 事件 payload；  
- 从 `workflows/` 加载的 Workflow 定义文档；  
- intake 适配产出的结构化 candidate/descriptor；  
- 跨 service 传递的业务结果对象。

**范围排除（仍须在各自 Port 内做完整性校验，但不是“自由 dict 业务合同”）：**

| 排除 | 校验位置 |
|---|---|
| 对象存储 **原始字节流** | S13 Port：size/digest/stream |
| 模型 **未结构化** 的原始生成流 | S11 adapter 边界；**进入业务前**必须 parse 为 contracts 类型 |

```text
raw structured body
  → contracts.<domain>.parse
  → Ok(typed)  → 唯一允许进入业务的解释形态（SSOT 实例）
  → Err        → 立刻报错 + 抛弃 body（D03-T017）
```

---


## 3. 总体方案陈述

1. 采用 **扁平顶级栏目** + **`src/` 内部分层**，匹配单体发布。  
2. **intake 顶级**，强调多源适配一等公民，且不与 services 混装。  
3. **workflow 定义 / runtime / services / adapters** 四分裂，落实 Workflow≠Runtime。  
4. **`contracts/` 为 typed schema 唯一 SSOT**（分域；强制校验；非法抛弃；运行期唯一解释）。  
5. **persistence + storage + data/objects** 兑现 S12/S13 Port 纪律。  
6. **prompts：git 正文 + DB hash 指针**；用 hash 校验真值。  
7. **tests/** 三分（unit/e2e/domain）。  
8. **public/** 对外资源；**docs/baseline** 产品真相叙事。  
9. **frontend/** v2 only。  
10. 依赖单向、可 architecture-test；状态机产品叙事在 Spec，**类型解释在 contracts**。

---

## 4. 具体执行方案清单

### 4.1 目标目录树（v1 规范形状）

```text
MKB_root/
├── docs/
│   └── baseline/                 # 真相层 SSOT（已存在）
│       ├── domain-truth/
│       ├── qna-truth/
│       ├── spec-glossary.md
│       └── spec-index.md
├── data/                         # 运行时与可版本配置根
│   ├── config/                   # 非秘密默认配置（可 git）
│   ├── database/                 # 运行库落点；*.db 等 gitignore
│   ├── objects/                  # S13 object_root；对象字节 gitignore
│   ├── prompts/                  # ★ 必须 git 跟踪（Owner）
│   └── logs/                     # 可选；默认 gitignore 内容
├── api/
│   ├── public/                   # S01 Task 合同 only
│   └── internal/                 # health / readiness / metrics
├── src/
│   ├── runtime/                  # Engine：claim/outbox/process runner（S02/S03+S12 环）
│   │   └── inference/            # S11 门面：分能力 API、闸、transport policy（非 adapter）
│   ├── contracts/                # ★ Typed Protocol Layer 分域（见 4.2b）；消息必校验
│   │   └── inference/            # S11 typed request/result/usage
│   ├── workflows/                # ★ 仅声明式 Workflow 定义/seed（见 4.2）
│   ├── services/                 # 原子 capability 实现（S05 业务段、S06–S10…）
│   ├── llm_adapters/             # S11 Adapter 对接 only（LocalVllm / optional Gemini）
│   ├── persistence/              # S12 Ports + Turso/libSQL adapter
│   └── storage/                  # S13 ObjectStorePort + local FS adapter
├── intake/                       # ★ 顶级：源适配 only（S05 源侧）
│   ├── api/
│   ├── doc/
│   ├── pdf/
│   └── web/                      # 可按 source kind 扩展，不改顶级名
├── tests/
│   ├── unit/
│   ├── e2e/
│   └── domain/                   # HARD / golden / 跨域不变量
├── venv/                         # Python 虚拟环境
├── public/                       # 对外可用静态/公开资源（非运行时 SSOT）
└── frontend/                     # v2 预留；v1 无业务依赖
```

**对应真相**：`D03-T001..016`。

**小结**：在业主原提案上，固定补齐 `data/objects`、`persistence`、`storage`，测试名 `tests/`，公开资源 `public/`，intake 顶级。

### 4.2 `src/workflows/` 职责钉死（Workflow ≠ Runtime）

| 允许 | 禁止 |
|---|---|
| 声明式 Workflow 程序定义（JSON/YAML/内部 DSL 等，格式由 S03 定） | claim / lease / fence / retry 循环 |
| seed、fixture、示例管线 | 直接调用 LLM 或写 object_root |
| 与 S03 compiler 输入对齐的静态图/平面字段 | 维护 `job`/`process` 运行状态 |
| 文档化 slot 名与 capability key 引用 | `findNextStep` 式调度逻辑 |

**Runtime 独有**：`src/runtime/` 加载定义 → 结合 S12 状态 → materialize Command/I/O handles → 调 `services` → 写 Outcome/outbox。

**对应真相**：`D03-T003`。

**小结**：目录名可保留 `workflows/`（业主原词），**语义强制为定义侧**；若后续易误解，允许 rename 为 `workflow_defs/` 而不改变职责（须 D03 修订）。

### 4.2b `src/contracts/` — 分域 Typed Protocol Layer（强制）

**对应真相**：`D03-T012`、`D03-T017`、`OD-D03-07..09`。

#### 4.2b.1 为何分域（相对 legacy 微服务）

| legacy 微服务 | MKB 单体 |
|---|---|
| `schemas_smcp.ts` 复制到每个 worker = 共享跨服务协议 | **`contracts/common` + `contracts/runtime` 等** 单一源 |
| 每服务 `schemas_common.ts` = 服务内协议 | **`contracts/<domain>/`** 按业务域分册，被多模块 import |
| 复制导致版本漂移 | 一处修改、全仓编译期可见 |

#### 4.2b.2 推荐分域目录（v1 最小闭集 · 名称可微调）

```text
src/contracts/
  common/           # 原语：UUID、Digest、TeamId、错误信封、分页游标…
  api/              # S01 对外 Task API 请求/响应；internal health 形状
  runtime/          # Task/Execution/Process 命令与结果、claim/outbox 消息体
  workflow/         # 声明式 Workflow 定义文档的 schema（加载 workflows/ 时校验）
  intake/           # S04/S05：descriptor、acquire/clean candidate、preflight/gate 消息
  lsrag/            # S06/S07：structure/construction Command·Outcome·artifact 元数据形状
  vector/           # S08–S10：vectorize intent、检索请求/响应（随 Spec 充实）
  inference/        # S11：adapter 请求/响应（模型调用边界）
  storage/          # S13：handle、stat、promote 结果等对象合同
  persistence/      # S12：如需要暴露的仓储 DTO（可选；多数经 runtime/domain）
  __init__ / registry  # 可选：schema 注册与 version 清单
```

**规则：**

- 新跨边界消息 **必须** 先落入某一域册；禁止“匿名 dict 协议”。  
- 跨域复用只通过 `common/` 或显式 import，禁止循环依赖（`contracts` 域间依赖只能 common ← domain，domain 互引用须无环）。  
- **产品/状态不变量**以对应 Sxx Spec 为准；**typed 形状与运行期解释**以 contracts 为唯一 SSOT；冲突时 **执行 contracts** 并回填 Spec。  
- Structure/Construction 等 schema 的 **content_digest** 必须覆盖 contracts 中对应不可变定义，禁止 registry 另存冲突正文。

#### 4.2b.3 每域应规定的 typed 消息类别（强制清单）

每个 `contracts/<domain>/` 至少按需覆盖（有则必须 schema 化）：

| 类别 | 说明 | 示例 |
|---|---|---|
| **Inbound Request** | 进入该域的命令/请求 | `TaskCreateRequest`, `ProcessCommandV1` |
| **Outbound Response** | 离开该域的同步响应 | `TaskGetResponse`, `HealthResponse` |
| **Event / Outbox Payload** | 异步投递体 | `VectorizeConstructIntentV1` |
| **Error** | 域内 typed 错误细节（可挂 common 错误信封） | `ContractValidationError`, `ConstructBindingError` |
| **Value Objects** | 稳定小对象 | `MkbObjectHandle`, `ContentDigest`, `SchemaRef` |
| **Definition Docs**（若适用） | 静态定义文件形状 | `WorkflowProgramV1` |

#### 4.2b.4 传递与抛弃（Owner HARD）

```text
receive raw message body
  → contracts.<domain>.parse(body)   # 或 safe_parse
  → Ok(typed)  → 唯一允许进入业务的形态；此后只认 typed，不认 raw dict
  → Err(e)     → 立即报错；抛弃 body；不写业务状态；不 partial apply
```

| 通道 | 失败处置 |
|---|---|
| `api/public` | HTTP 4xx + typed error body；不创建 Task |
| `api/internal` | 4xx/503 按类；不假装 healthy |
| runtime 内部调度 | 拒绝执行该步；Process/Task 按 S02/S03 记失败 |
| outbox 投递前 | 不得入队非法 payload |
| workflow 文件加载 | readiness/注册失败，不得用坏定义跑引擎 |
| intake 适配输出 | 不得写入下游未校验结构 |

**禁止**：校验失败后“尽量继续”、用默认值填满当成功、把非法字段塞进 `payload_extra` 躲校验。

#### 4.2b.5 允许 / 禁止

| 允许 | 禁止 |
|---|---|
| pydantic/msgspec/jsonschema 等 | 业务状态迁移、workflow 调度 |
| 校验错误路径（field path） | 打开 DB/对象/LLM |
| schema version + digest 字段 | 未校验 dict 作为跨模块公共 API |
| 被 api/runtime/services/intake/tests import | `contracts` 依赖 api/runtime/services（防环） |

#### 4.2b.6 与 legacy SMCP 平面的映射（思想 · 非字段兼容）

| SMCP 平面 | MKB contracts 落点（示意） |
|---|---|
| authority_payload | `common` / `runtime` 中的 team/invoker 上下文类型 |
| workflow_payload + intents | `runtime` + `workflow`（定义 vs 运行引用分开） |
| io_payload | `storage` handle + `runtime` 槽位绑定类型（无 r2_key wire） |
| control_payload | `runtime` 控制命令类型（mode 等；语义归 S03/S07） |
| input/output/error | 各域 Inbound/Outbound/Error |
| 服务内 schemas_common | 对应 `contracts/intake|lsrag|vector|…` |

**小结**：`contracts/` = 单体下的 **分域 SMCP+域 schema 统一体**；校验不过则 **报错并抛弃**。

### 4.3 `intake/` 顶级（强制）

```text
intake/
  api/    # registered API 等源适配
  doc/    # 文档类本地/对象源适配
  pdf/    # PDF 源适配
  web/    # HTTP/static/browser 相关源适配
```

| 允许 | 禁止 |
|---|---|
| 按源 kind 的 **源 I/O 适配**（fetch/decode/stream） | 写 IntakeSnapshot/Revision 权威表（须经 S04 ports） |
| **四域清洗变换**（provider parser、web/pdf/doc strategy；D08） | 在 `src/services` 或 `src/runtime` 再实现平行 cleaner |
| 产出必须先 **contracts/intake** 校验再交给 runtime | structurize/construct/vectorize（非 intake 职责） |
| 被 runtime 在 acquire/**clean** 工序调用 | 独立对外 HTTP 产品面（对外仍 `api/public` Task） |
| legacy 规范的纯函数改写（schema/parser/strategy） | runtime import `legacy-family`；live 隧道/cookie/CF 常量 |

**对应真相**：`D03-T004`。

### 4.4 `src/services/` vs 适配层

```text
src/services/          # 原子业务能力：clean.* / lsrag.* / index.* 等 handler 实现
src/persistence/       # 只谈关系库 Ports + adapter
src/storage/           # 只谈对象 Ports + adapter
src/llm_adapters/      # 只谈模型供应商
```

services **通过 ports** 使用 persistence/storage/llm，不反向依赖 `api/`。

**对应真相**：`D03-T005`、`D03-T010`、`D03-T011`。

### 4.5 `data/` git 纪律与 Prompt hash 指针

| 路径 | git | 说明 |
|---|---|---|
| `data/prompts/**` | **必须跟踪** | **Prompt 正文唯一载体**（版本管理）；变更走 git |
| `data/config/**` | 跟踪非秘密默认 | 密钥禁止 |
| `data/database/**` | 仅骨架；`*.db`/wal 等 ignore | 运行库；**prompt 行只存 hash/指针** |
| `data/objects/**` | 仅骨架；对象字节 ignore | S13 |
| `data/logs/**` | ignore 内容 | 可选 |

**Prompt 持有/运用协议（与 DB 无冲突）：**

```text
git: data/prompts/<path>     → 正文 bytes
DB:  prompt_ref = { path_or_key, content_hash }   → 仅指针
use: read file → sha256(bytes) == content_hash ?
       yes → 注入模型/工序
       no  → fail-closed（指针失效或工作区脏）
```

- **不**在 DB 存第二份可独立编辑的 prompt 正文。  
- S14 registry（若有）登记 **hash + 元数据**，不另立正文 SSOT。  
- Process binding 锁定的是 **hash**（及 schema），不是“最新文件”。

**对应真相**：`D03-T006`、`D03-T016`、`D03-T019`。

### 4.6 `api/` / `public/` / `tests/` / `docs/` / `frontend/`

- **api/public**：S01 only。  
- **api/internal**：readiness/health/metrics。  
- **public/**：对外可引用的静态资源（如默认图标、公开示例文件等）；**不是** object_root；**禁止** 密钥/token/隐私数据。  
- **tests/**：unit / e2e / domain。  
- **docs/baseline**：truth SSOT。  
- **frontend/**：v2。

**对应真相**：`D03-T007..009`、`D03-T013..014`。

### 4.3 依赖方向（强制）

```text
api/public|internal
    → src/contracts            # 先校验再进业务
    → src/runtime
        → src/contracts
        → src/services
            → src/contracts
            → src/persistence | src/storage | src/llm_adapters | intake/*
        → src/workflows        # 只读加载定义（加载后的配置亦应经 schema 校验）
intake/* → src/contracts        # 适配器输出进入业务前校验

src/contracts  ──x──►  api | runtime | services | persistence | storage | llm
     （协议层不依赖上层，避免环）

禁止环与逆流（示例）：
  services → api
  intake → api.public 业务写
  llm_adapters → services 业务状态
  workflows → persistence 写状态
  contracts → runtime/services（反向）
  任意实现 → legacy-family 运行时 import
  services/runtime → 直接 pathlib 写 data/objects 或直连 driver
     （必须经 storage/persistence Port）
  跨层传递未校验 dict 作为合同
```

**对应真相**：`D03-T015`、`D03-T012`。

### 4.4 与子系统落点映射（实现索引）

| 子系统 | 主要代码落点 | 数据/资源落点 |
|---|---|---|
| S01 | `api/public/` + **`contracts` 请求/响应 schema** | — |
| S02/S03 | `src/runtime/` + `src/workflows/`（定义）+ **Command/Outcome schemas in contracts** | S12 表 |
| S04 | `src/services/` + **identity/command 协议类型** | S12 intake 模块 |
| S05 | `intake/*` + `src/services/` + **源 descriptor/结果 schema** | — |
| S06/S07 | `src/services/` + **structure/construction 协议类型** | generation → storage+S12 |
| S08–S10 | `src/services/` + **vector/retrieval 消息 schema** | vector 模块 S12 |
| S11 | `src/llm_adapters/` + **adapter I/O schema（可选同层或 contracts）** | — |
| S12 | `src/persistence/` | `data/database/` |
| S13 | `src/storage/` + **handle/digest 值对象** | `data/objects/` |
| S14 | registry 加载；文本 | `data/prompts/`、`data/config/` |
| S15 | `api/internal/` + runtime 钩子 | `data/logs/` |
| S16 | 横切；无单独强制顶级名 | 密钥不进 git |
| **横切协议** | **`src/contracts/`** | — |

---

## 5. 事实反例、风险与围栏

### 5.1 Legacy 反例（目录/组织）

| Legacy 事实 | D03 禁令 |
|---|---|
| 10+ Worker 包 = 分布式运行时 | 单体目录，禁止复制为多发布单元 |
| Workflow JSON 被误当成“引擎在定义里” | 定义只在 `workflows/`；引擎只在 `runtime/` |
| skill 内隐式路径/成功=R2 | I/O 经 storage Port；成功=业务 proof |
| console UI 与 worker 同仓职责纠缠 | frontend v2；v1 无 UI 业务依赖 |

### 5.2 风险台账

| 风险 | 缓解 |
|---|---|
| `workflows/` 名被实现成脚本状态机 | D03-T003 + architecture grep 禁 claim/retry 符号 |
| 低估 contracts 成空 DTO，边界自由 dict | D03-T012；边界强制 parse；CI 禁跨层裸 dict 合同 |
| schema 与 Spec 漂移 | schema version/digest；与 baseline 双向校准 |
| prompts 进 git 泄漏密钥 | 仅文本模板；密钥走环境；review |
| `public/` 被当成对象存储 | 与 `data/objects` 文案+测试隔离 |
| intake 顶级导致绕过 S04 | intake 禁止写权威 identity；验收扫描 |
| data/ 误提交巨大 objects | gitignore + CI 体积门 |

### 5.3 明确禁止清单（HARD）

1. 将 `intake/` 移入 `services/` 作为唯一结构。  
2. 在 `workflows/` 实现 Process 状态机或私有 retry。  
3. services 直连 DB driver / 裸写 object_root。  
4. `api/public` 暴露 object/construct 浏览器或精修 API。  
5. v1 运行依赖 `frontend/`。  
6. runtime import `legacy-family` / `legacy-python`。  
7. 把运行时 objects 或 DB 文件强制提交进 git（与 prompts 策略相反）。  
8. 跨 `api`/`runtime`/`services`/`intake` 边界使用 **未校验 dict** 作为通信合同。  
9. 在 `contracts/` 内发起 I/O、DB、LLM 或状态推进。  
10. 在 services/runtime 另建与 contracts **并行** 的跨层 schema 真相（双源）。  
11. DB 存储可漂移的 prompt **正文** 副本（只允许 hash 指针）。  
12. 校验通过后仍以 raw dict 为准、忽略 typed 对象（破坏运行期唯一解释 SSOT）。

---

## 6. 测试与验收台账（脚手架期）

| ID | HARD 场景 | 证据 |
|---|---|---|
| `D03-A01` | 顶级存在 `intake/` 且不在 `src/services/intake` 作为唯一源 | 树扫描 |
| `D03-A02` | 存在 `src/persistence`、`src/storage`、`data/objects` | 树扫描 |
| `D03-A03` | `data/prompts` 被 git 跟踪（至少示例 prompt） | `git ls-files` |
| `D03-A04` | 测试根为 `tests/{unit,e2e,domain}` | 树扫描 |
| `D03-A05` | 存在 `public/`；不存在将 object_root 指到 public 的默认配置 | 配置检查 |
| `D03-A06` | architecture：services 不 import api | import linter |
| `D03-A07` | architecture：workflows 无 claim/outbox/retry 实现符号 | grep/AST |
| `D03-A08` | architecture：services 不直接 import libsql/turso driver（仅 persistence） | import linter |
| `D03-A09` | architecture：无 legacy-family 运行时 import | 扫描 |
| `D03-A10` | `api/public` 路由集合 ⊆ S01 合同 | OpenAPI/路由测试 |
| `D03-A11` | `contracts` 存在实质 schema 模块（非空包） | 树 + 导入测试 |
| `D03-A12` | public API handler 对 body 调用 contracts 校验 | 代码约定/测试 |
| `D03-A13` | ProcessCommand 进入 service 前已经校验 | 单元/架构测试 |
| `D03-A14` | `contracts` 不 import runtime/services/persistence/storage | import linter |
| `D03-A15` | 不存在第二套跨层 schema 包与 contracts 并行当合同 | 架构扫描 |
| `D03-A16` | prompt 运用路径执行 hash 校验；DB 无 prompt 正文列（或测试夹具证明仅 hash） | 集成测试 |
| `D03-A17` | 非法 API body 不创建 Task/不写业务行 | 契约测试 |

---

## 7. Reference-anchor 台账

| Anchor | 用途 | 裁决 |
|---|---|---|
| legacy `smind_workflows.steps_definition` + console converter | 声明式 Workflow 是数据文档 | **保留语义**：定义≠引擎；**删除** CF/D1/SMCP wire |
| SMCP `io_payload` / `control_payload` / STEP_* | I/O 与控制平面分账 | **保留分账思想**；MKB 用 S03/S13 ports 表达 |
| clean/rag dispatcher orchestrator | Runtime 解释 rank、写 process、队列推进 | **映射**到 `src/runtime/`；不进 `workflows/` |
| skill `io_manager` | 单步只认槽位 | **映射**到 services + storage |
| skill `schemas_smcp.ts` + Zod | 边界强制校验 envelope | **保留纪律**：边界强制 schema；**删除** SMCP wire；落点 `src/contracts/` |
| 现有 `docs/baseline/**` | 真相文档树 | **保留** 为 docs 落点 |

---

## 8. Domain verdict

### 8.1 Verdict

**`ACCEPTED / FROZEN (domain)`**：Owner 2026-08-11 批准 D03 进入真相层。仓库目录宪法、**contracts typed 唯一 SSOT**、**prompts git+hash**、Workflow≠Runtime、intake 顶级、Port 落点与消息 fail-closed 纪律均已冻结为 `T-O-141..159`。

### 8.2 实现期非 reopen 细节（不改变 Truth）

| 项 | 默认 |
|---|---|
| `workflows/` 目录名 | 保留；职责钉死为定义侧 |
| contracts 实现库 | pydantic / msgspec / 等价；不冻库名 |
| 分域子目录 | §4.2b.2 最小闭集，可增域 |
| `public/` HTTP 挂载 | 可选只读；禁密钥 |
| `data/config` git | 非秘密默认可跟踪 |

### 8.3 下游义务

1. 脚手架与 architecture tests 服从 §4/§6；  
2. S14 实现 prompt 时仅登记 **hash 指针**；  
3. S06/S07 registry 仅存 **digest 指向 contracts** 定义，禁止冲突正文；  
4. `17` 挂载 `data/objects`、`data/database`；  
5. 变更目录宪法必须 **reopen D03** 并 append 新 T-O。

---

## 9. 修订历史

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| `D03-v0.1-draft` | `2026-08-11` | `superseded` | 首稿；误将协议层写成空 DTO |
| `D03-v0.2-draft` | `2026-08-11` | `superseded` | 协议层=Zod 级强制校验（当时目录名 dataclass） |
| `D03-v0.3-draft` | `2026-08-11` | `superseded` | contracts 分域；消息必校验抛弃 |
| `D03-v0.4-draft` | `2026-08-11` | `superseded` | contracts 唯一 SSOT；prompts git+hash；消息范围收紧 |
| `D03-v1.0` | `2026-08-11` | `accepted / frozen` | Owner 冻结为真相层；登记 `T-O-141..159`；回填 index/glossary |
| `D03-v1.0-cal-d08` | `2026-08-13` | `accepted / D08-calibrated` | reopen §4.3：intake 四域承载 clean 变换；T-O-144 顶级目录不变 |

---

## 附录 A — 与业主原提案对照

| 原提案 | 草案 |
|---|---|
| `data/{config,database,prompts}` | 保留 + **`objects/`** + 可选 `logs/` |
| `api/{internal,public}` | 保留；职责钉死 S01 vs 运维 |
| `src/{runtime,contracts,workflows,services,llm_adapters}` | 保留 + **`persistence`/`storage`** |
| `intake/*` 顶级 | **强制保留顶级** |
| `test/` | → **`tests/`** |
| `asset/` | → **`public/`** |
| `frontend/` v2 | 保留预留 |
| `docs/` | 锚定 `docs/baseline` 为 truth |

## 附录 B — 一页依赖示意

```text
                 public/   docs/baseline   data/prompts(git 正文) ←hash→ DB 指针
                    │            │                │
api/* ──► contracts(校验) ──► runtime ──► services ──┬──► persistence ──► data/database
                         │         │         │       ├──► storage     ──► data/objects
                         │         │         ├──► llm_adapters
                         │         │         └──► intake/* (顶级)
                         │         └──► workflows/ (定义只读)
                         └──◄── 全仓边界消息必须过闸
api/internal ──► contracts ──► runtime (health/ready)
tests/* ──► contracts + 各层
```
