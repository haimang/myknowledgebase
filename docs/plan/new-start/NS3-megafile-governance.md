# Nano-Agent 行动计划

> 服务业务簇: `MKB / NS3 capability-boundary extraction`
> 计划对象: 从 `IntakeGenerationConstructMixin` 按 S06/S07 能力边界抽出叶服务；在 services 内拆分 `lsrag_compiler` 导航包；用 architecture 守卫锁死错误拆法
> 类型: `refactor`
> 作者: `Grok`
> 时间: `2026-08-15`
> 文件位置: `docs/plan/new-start/NS3-megafile-governance.md`
> 上游前序 / closure:
> - `docs/plan/new-start/NS2-pipeline-priority.md`（`executed`）
> - `docs/closure/new-start/NS2-pipeline-priority-closure.md`（`closed-with-explicit-deferrals`）
> 下游交接:
> - NS3 阶段 final closure（本 AP §10；落盘 `docs/closure/new-start/NS3-megafile-governance-closure.md`）
> - S04 acceptance TX 瘦身（`_accept_snapshot` 334L）另开 charter，本 AP 不碰
> - 去 Mixin / YAML 工作流 / Command 总线：永久 OOS，除非 owner 正式 reopen S03/D03
> 关联设计 / 调研文档:
> - `docs/eval/new-start/megafile-analysis-after-NS2-by-gemini.md`（eval / draft；**地图，不是 charter**）
> - 本会话 Grok 独立评估（业主指令：按该评估执行，不以 Gemini 五行数支柱为上游）
> - `docs/baseline/domain-truth/D03-repository-layout.md`（`T-O-142/143/150/151/152/154`）
> - `docs/baseline/domain-truth/S03-workflow-engine.md`（`S03-T002/T003/T005/T021`）
> - `docs/baseline/domain-truth/S06-lsrag-structurizer.md`（`S06-E01`）
> - `docs/baseline/domain-truth/S07-lsrag-constructor.md`（`S07-E01`）
> 冻结决策来源:
> - D03 / S03 / S06 / S07 已冻 Truth（只读引用；本 action-plan 不填写 Q/A）
> - NS2 `T-O-353..361`（本轮不改口）
> - 本会话业主指令（2026-08-15）：megafile eval 可以当地图；拆分以 S06/S07 服务落点为准；禁止 YAML 工作流和去 Mixin 专相；禁止 LOC hard-gate
> grounding 来源:
> - 本 AP §7 内置锚区（对照当前 NS2 后 `src/` / `tests/`）
> 关联 reference-anchor:
> - 见 §7 内置锚区
> 文档状态: `executing`

---

## 0. 执行背景与目标

NS2 已把三池 admit/claim、车道 salvage、embed FIFO 落到 `dispatch.py` + `mkb_processes` 列上，并明确复用 Mixin 组合根（NS2 A-6）。Gemini 在 NS2 后提交了一份 megafile 水位报告，把「>500 行」当成债务、建议再切三个 intake Mixin、YAML 工作流、去 Mixin 与 Command 框架。独立复测确认：**生产热点判断有一半对，拆法与本库治理冲突**。

当前真实热点不是 `pipeline.py`（36 行组合根），也不是 `lsrag_definition.py`（S03 声明图），而是 `src/runtime/intake/generation_construct.py`（1,367 行）把 S06 structurize、S07 construct、markdown 转录、NS2 salvage/通道、TX callback 堆在同一个 Mixin 里。S06-E01 / S07-E01 早已指定叶能力落在 `src/services/lsrag_structurize/` 与 `src/services/lsrag_construct/`；compiler 已是无 I/O 的纯核（`lsrag_compiler.py`），只是文件大。

本计划把这条已冻落点落成可合并的服务提取 + 稳定导入面 + 每 Phase 独立测试台账。成功标准是 **能力边界落地与行为 0 差**，不是把 >500 行文件减到 12 个。

- **服务业务簇**：`NS3`
- **计划对象**：S06/S07 叶服务提取 + compiler 包内拆分 + 错误拆法守卫
- **本次计划解决的问题**：
  - `generation_construct.py` 同时拥有推理 I/O、salvage 车道、S06/S07 内核编排与 TX 提交，无法对叶能力做无 I/O 单测
  - S06-E01 / S07-E01 指定的 service 目录尚未存在；runtime Mixin 越权承担叶算法
  - 若按行数切片（新 Mixin / YAML / Command），会破坏 D03/S03 与刚关上的 NS2 闸
- **本次计划的直接产出**：
  - `src/services/lsrag_structurize/` 与 `src/services/lsrag_construct/`（无 I/O、无 llm_adapters）
  - `src/services/lsrag_compiler/` 包（IR 留在 services；公开 import 稳定）
  - Mixin 退回 ProcessStageHandler 适配器：通道/salvage/CLI·live I/O/promote/TX
  - architecture 守卫：禁止 YAML 工作流、禁止 `contracts/lsrag/models.py` 大杂烩、禁止再为 S06/S07 加 intake Mixin、禁止去 Mixin / TxHandler
  - 每 Phase 独立测试 + §8 全量台账 + NS3 closure
- **本计划不重新讨论的设计结论**：
  - v1 是单体 + 单一 `ProcessStageHandler`（`T-O-142`）；Mixin 组合根保留（NS2 A-6）
  - Workflow 定义 ≠ Runtime；定义 SSOT 是七表 + 代码注册，禁止 DAG JSON / YAML（`T-O-143` / `S03-T002/T003/T005`）
  - `services/` = 原子叶能力，无私有 retry 状态机；禁 import `llm_adapters`（`T-O-150` / `T-O-151`）
  - contracts 只承载跨层消息；compiler IR 不是自动合同（`T-O-152` / `T-O-154`）
  - Process 只吃 `ProcessCommand`、吐 `ProcessOutcome`（`S03-T021`）
  - salvage 闭集与车道留在 Mixin（NS2 A-19 / A-20 / `T-O-355`）
  - 派发态只活在 `mkb_processes` 列；本轮无新表、不改 admit/claim（`T-O-360` / `T-O-173`）

### 0.1 NS2 后文件分类（本 AP 的拆分尺子）

| 类别 | 代表 | 本 AP 处置 |
|---|---|---|
| A. 声明图 | `lsrag_definition.py:1-1081`、`builtin_scatter.py` | **不拆**。S03 要的数据体积。 |
| B. 类型 SSOT | `contracts/workflow/models.py`、`contracts/api/models.py`、`contracts/lsrag/layered_content.py` | **不拆**。D03 就要集中。 |
| C. 组合根 | `pipeline.py:18-27`、`runtime.py:14-22`、`api/app.py`、`generation.py:14-18` | **不拆、不去 Mixin**。 |
| D. 纯核 | `lsrag_compiler.py`、`dispatch.py`、`workflow/helpers.py` | 只在 P4 做 **包内导航拆分**；IR 不进 contracts。 |
| E. 运行时 Mixin 混了 I/O+TX+叶算法 | `generation_construct.py` | **本 AP 唯一拆分对象**（按 S06/S07，不按行数）。 |
| F. 超长 TX（他域） | `acceptance_snapshot.py::_accept_snapshot` 334L | **OOS**。无 S04 charter 不拆事务。 |
| G. 测试体积 | `test_workflow_runtime.py`、`test_dispatch_claim.py` | **不设 <300L 闸**。`test_dispatch_claim` 增长是 NS2 覆盖，不是 seed 债。 |

---

## 1. 执行综述

### 1.1 总体执行方式

**先锁错误拆法，再按能力迁服务，最后才拆 compiler 导航包。** 样板是 NS2 的 `dispatch.py`：抽出无 I/O 的纯核，handler 继续拥有通道、salvage 与 TX callback。禁止先切三个新 Mixin、禁止先动 `WorkflowRuntime` MRO、禁止先拆 `lsrag_definition.py`。P2 与 P3 都改 `generation_construct.py`，必须串行。每 Phase 收口前跑该 Phase 完整独立测试集；P5 才跑 mega / NS2 soak / 全短途回归。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | 分类守卫 | `S` | architecture 锁死错误拆法；Mixin 根与 NS2 调度面冻结 | `-` |
| Phase 2 | S06 structurize 叶服务 | `L` | `lsrag_structurize` 承接 adopt/validate 编排；Mixin 只留 I/O+TX | Phase 1 |
| Phase 3 | S07 construct 叶服务 | `L` | `lsrag_construct` 承接 reconstruct/construct/validate；salvage 仍在 Mixin | Phase 2 |
| Phase 4 | compiler 包内拆分 | `M` | `src/services/lsrag_compiler/` 导航包；公开 import 0 差 | Phase 2+3 |
| Phase 5 | 回归、文档、收口 | `L` | NS1/NS2 金样 + soak + 窄回填 + closure | Phase 4 |

### 1.3 Phase 说明

1. **Phase 1 — 分类守卫**
   - **核心目标**：后续任何 PR 若走 Gemini 拆法，CI 立刻红。
   - **为什么先做**：P2/P3 会新建目录、改 Mixin。没有守卫，提取过程容易滑回「再加 Mixin」。
2. **Phase 2 — S06 structurize 叶服务**
   - **核心目标**：`_structurize` 的内核（normalize/adopt/validate/report）离开 Mixin。
   - **为什么放在这里**：比 construct 更线性；P3 的 reconstruct 依赖稳定的 S06 交出物。
3. **Phase 3 — S07 construct 叶服务**
   - **核心目标**：`_construct` / reconstruct 的内核离开 Mixin；C 摘要 I/O 与 salvage 留下。
   - **为什么放在这里**：必须改同一文件，且要复用 P2 的绑定/无 I/O 约定。
4. **Phase 4 — compiler 包内拆分**
   - **核心目标**：大文件变成可导航包，**行为与公开符号不变**。
   - **为什么放在这里**：此时消费者已是两个服务 + 薄 Mixin，不再从 1,300 行 Mixin 里直接长调用。
5. **Phase 5 — 回归、文档、收口**
   - **核心目标**：证明提取没有改产品语义；写出诚实 closure。
   - **为什么放在这里**：接线完成后才有完整旅程。

### 1.4 执行策略说明

- **执行顺序原则**：守卫 → S06 服务 → S07 服务 → compiler 包 → mega。禁止倒序。P2/P3 禁止并行（同一 Mixin 文件）。
- **风险控制原则**：服务层零 I/O（已有 `test_services_do_not_reach_api_concrete_persistence_or_inference_transport`）。TX callback 仍由 Mixin 持有，禁止把 `BEGIN` 拆出 `core.py:121-129` 的 commit 路径。NS2 salvage/车道一字不改。
- **测试推进原则**：每 Phase 先短途（新服务纯函数 + 守卫）→ 该 Phase 的 handler 接线测 → 该 Phase 指定 e2e。P5 才跑 NS1 mega、NS2 lanes、dispatch soak。
- **文档同步原则**：不改 pre-NS1 QNA。S06/S07 仅 Phase 5 **窄回填**「路径已落地」。不把 Gemini `D-MEGA-*` 写入 `deferred-items-ledger.md`。
- **回滚 / 降级原则**：每 Phase 可独立 `git revert`。无 DDL。回滚 = 删新包、Mixin 恢复直调 compiler。禁止用「行数下降」当成功。

### 1.5 本次 action-plan 影响结构图

```text
NS3-megafile-governance
├── Phase 1: 分类守卫
│   ├── tests/domain/test_architecture.py     + 错误拆法守卫
│   ├── src/runtime/workflow/runtime.py       只读：7 Mixin 根冻结
│   └── src/runtime/intake/pipeline.py        只读：组合根冻结
├── Phase 2: S06 structurize 叶服务
│   ├── src/services/lsrag_structurize/       🆕 binder / admit / service
│   ├── generation_construct._structurize     ♻️ 改为调服务
│   └── generation_live / claude_cli          ✅ I/O 留 Mixin
├── Phase 3: S07 construct 叶服务
│   ├── src/services/lsrag_construct/         🆕 binder / reconstruct / admit / service
│   ├── _construct / _reconstruct_*           ♻️ 内核迁出
│   └── _complete_construct_summaries         ✅ I/O + salvage 留下
├── Phase 4: compiler 包
│   ├── src/services/lsrag_compiler.py        删除（改为包）
│   └── src/services/lsrag_compiler/          🆕 models/adopt/validate/payloads/compiler
└── Phase 5: 回归 / 文档 / 收口
    ├── tests/e2e/test_ns1_pipeline.py        ♻️ 金样
    ├── tests/e2e/test_ns2_dispatch_lanes.py  ♻️ NS2
    ├── S06/S07 路径窄回填
    └── docs/closure/new-start/NS3-megafile-governance-closure.md
```

### 1.6 执行 DAG

```text
                    ┌─────────────┐
                    │  Phase 1    │
                    │  分类守卫   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Phase 2    │
                    │  S06 服务   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Phase 3    │
                    │  S07 服务   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Phase 4    │
                    │  compiler包 │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Phase 5    │
                    │  mega/收口  │
                    └─────────────┘
```

硬边：P2 不得新建 intake Mixin；P3 不得把 salvage 迁进 services；P4 不得创建 `src/contracts/lsrag/models.py`；P5 不得在 P2–P4 未绿时标 `executed`。P2 未绿禁止开 P3。

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** architecture 守卫：禁 YAML 工作流、禁 `contracts/lsrag/models.py`、禁为 S06/S07 新增 intake Mixin、禁 TxHandler/TransactionalCommand 框架、冻结 `WorkflowRuntime` / `IntakePipeline` MRO
- **[S2]** 新建 `src/services/lsrag_structurize/`：binder + admit（wrap compiler）+ service facade；无 I/O
- **[S3]** 改写 `IntakeGenerationConstructMixin._structurize` 为：选通道 / 取 candidate（live|CLI|state）→ 调服务 → promote + TX callback
- **[S4]** 新建 `src/services/lsrag_construct/`：binder + reconstruct（再证 S06/S07 bytes）+ admit（`compiler.construct` / `validate_construction`）+ service facade
- **[S5]** 改写 `_construct` / `_reconstruct_structure_contract` 的内核调用 / `_reconstruct_metadata_refresh_contract` 的再证段 / `_reconstruct_construct_contract` 的 construct+比对段；I/O 与 salvage 留 Mixin
- **[S6]** 将 `lsrag_compiler.py` 收成 `src/services/lsrag_compiler/` 包，`__init__.py` 重导出既有公开名
- **[S7]** 每 Phase 独立测试集 + P5 mega/soak/domain + S06/S07 路径窄回填 + NS3 closure

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** 去 Mixin / 组合式重写 `WorkflowRuntime` 或 `IntakePipeline`
- **[O2]** YAML / Fluent WorkflowBuilder / 把 `lsrag_definition.py` 资源化
- **[O3]** Transactional Command / 第二套 UnitOfWork 框架（已有 `src/persistence/ports.py:11-16` + `callback(tx, refs)`）
- **[O4]** 把 12 个 compiler IR 灌进 `src/contracts/lsrag/models.py`
- **[O5]** 在 `runtime/intake/` 再切 `construct_markdown.py` / `construct_executor.py` / `construct_contract_builder.py` 三个 Mixin
- **[O6]** 拆 `api/app.py`、`contracts/api/models.py`、`contracts/workflow/models.py`、`lsrag_definition.py`、`builtin_scatter.py`
- **[O7]** 拆 `_accept_snapshot` / scatter `commit` / `repair_once`（无对应域 charter）
- **[O8]** 改 NS2 admit/claim/三池/salvage 闭集/车道表
- **[O9]** 把 markdown 转录抽成第三个服务（它仍是 process handler：`core.py:341`）
- **[O10]** 单测文件压到 <300 行；通用 Object Mother
- **[O11]** 真实 LLM / GPU soak；billing/cloud（仍是 NS2 defer）
- **[O12]** 把 Gemini `D-MEGA-*` 登记进 `deferred-items-ledger.md`

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| `generation_construct` 按 S06/S07 抽服务 | `in-scope` | 唯一混了 I/O+叶算法的热点；S06-E01/S07-E01 已指定落点 | 无 |
| compiler 包内拆分 | `in-scope` | 纯核导航；公开符号不变 | 若 P2/P3 后无人再直依私有方法，仍做 |
| Mixin 组合根 | `out-of-scope` | `T-O-142` + NS2 A-6 | owner 正式 reopen D03 |
| YAML 工作流 | `out-of-scope` | `S03-T002/T005` | reopen S03 |
| `_accept_snapshot` 334L | `out-of-scope` | 单 TX；属 S04 | S04 charter |
| 测试 Factory | `defer` | 非本轮产品接缝；允许 P2/P3 测试内局部 helper | 仅当新服务测试无法自描述合法绑定时 |
| `contracts/lsrag/structure/` 新 Command 类型 | `out-of-scope` | Command 已是 `ProcessCommand`；wire 已是 `layered_content` | 出现新的跨层信封且 contracts 没有对应类型 |
| LOC 减 60% / >1000 归零 | `out-of-scope` | 业主否决行数闸 | 永不作为本 AP 成功条件 |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| P1-01 | Phase 1 | 错误拆法 architecture 守卫 | `add` | `tests/domain/test_architecture.py:356-475` | CI 拒绝 YAML 工作流 / `contracts/lsrag/models.py` / 新 S06-S07 intake Mixin / TxHandler | NS3-T01–T06 T08 | `medium` |
| P1-02 | Phase 1 | 组合根与 NS2 面冻结断言 | `add` | `runtime.py:14-22`；`pipeline.py:18-27`；`dispatch.py:20-38` | MRO 与 generate process_key 集不变 | NS3-T04 T05 T07 | `low` |
| P2-01 | Phase 2 | `lsrag_structurize` 包 | `add` | 🆕 `src/services/lsrag_structurize/{__init__,binder,admit,service}.py` | 无 I/O 服务可单测 admit | NS3-T10–T14 | `high` |
| P2-02 | Phase 2 | `_structurize` 改调服务 | `refactor` | `generation_construct.py:882-1106`；`generation_live.py:171-183`；`core.py:342` | Mixin 不再直接 `adopt_layered_json_with_report` | NS3-T15–T22 T24 T25 | `high` |
| P2-03 | Phase 2 | P2 独立测试集 | `add` | 🆕 `tests/unit/test_lsrag_structurize_service.py` + fork 既有 | P2 短途+指定 e2e 全绿后才允许 P3 | NS3-T10–T25 | `high` |
| P3-01 | Phase 3 | `lsrag_construct` 包 | `add` | 🆕 `src/services/lsrag_construct/{__init__,binder,reconstruct,admit,service}.py` | 无 I/O 再证 + construct | NS3-T30–T33 T45 T46 | `high` |
| P3-02 | Phase 3 | `_construct` / reconstruct 改调服务 | `refactor` | `generation_construct.py:167-246,600-879,1108-1367`；`generation_artifacts.py:398-419` | salvage/I/O 仍在 Mixin；内核在服务 | NS3-T34–T40 T44 | `high` |
| P3-03 | Phase 3 | P3 独立测试集 | `add` | 🆕 `tests/unit/test_lsrag_construct_service.py` + fork | P3 短途+指定 e2e 全绿后才允许 P4 | NS3-T30–T48 | `high` |
| P4-01 | Phase 4 | compiler 收成包 | `migrate` | `src/services/lsrag_compiler.py` → 🆕 `src/services/lsrag_compiler/` | 既有 `from src.services.lsrag_compiler import …` 0 差 | NS3-T50–T58 | `medium` |
| P4-02 | Phase 4 | P4 独立测试集 | `add` | 🔱 `test_lsrag_compiler.py` / `test_adopt_layered_json.py` / `test_layered_schema.py` | 包拆后 compiler 金样全绿 | NS3-T50–T58 | `medium` |
| P5-01 | Phase 5 | mega / soak / 全短途回归 | `update` | §8.3 命令 | NS1+NS2+generation 金样与 soak 仍绿 | NS3-T60–T66 T70 T71 | `high` |
| P5-02 | Phase 5 | S06/S07 路径窄回填 | `update` | S06:438-445；S07:256-265 | 只记「目录已落地」，不改产品句 | NS3-T67 | `low` |
| P5-03 | Phase 5 | NS3 closure | `add` | 🆕 `docs/closure/new-start/NS3-megafile-governance-closure.md` | 五态 + 非 LOC 成功声明 | NS3-T68 T69 T72–T75 | `medium` |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — 分类守卫

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P1-01 | 错误拆法守卫 | a) 扫描 `src/workflows/**/*.yaml|yml` 必须为 0。b) 禁止存在 `src/contracts/lsrag/models.py`。c) 禁止在 `src/runtime/intake/` 新增类名匹配 `*(Structurize\|Construct\|Markdown\|Executor)Mixin`（现有 `IntakeGenerationConstructMixin` 白名单）。d) 禁止生产代码出现 `class TransactionalCommand` / `class TxHandler`。e) 既有 `test_services_do_not_reach_api_concrete_persistence_or_inference_transport`（`:356-376`）与 `test_workflows_contain_declarations_not_claim_outbox_or_retry_implementation`（`:406-413`）保持。 | `tests/domain/test_architecture.py:336-475` | 守卫失败即红 | NS3-T01 T02 T03 T06 T08 | domain 新测绿 |
| P1-02 | 组合根冻结 | a) 断言 `WorkflowRuntime` 基类闭集仍为 Core/Outcome/Materialize/Scatter/Gates/Outbox/Repair（`runtime.py:14-22`）。b) 断言 `IntakePipeline` 仍组合既有 7 个 stage mixin + `ProcessStageHandler`（`pipeline.py:18-27`）。c) 断言 `dispatch.GENERATE_PROCESS_KEYS` 仍含 `lsrag.structurize` / `lsrag.construct` / `lsrag.transcribe_markdown`（`dispatch.py:20-28`）。d) 本 Phase **零生产逻辑改动**。 | `runtime.py:14-22`；`pipeline.py:18-27`；`generation.py:14-18`；`dispatch.py:20-38` | 冻结可测 | NS3-T04 T05 T07 | unit+domain 绿；`git diff src` 为空 |

### 4.2 Phase 2 — S06 structurize 叶服务

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P2-01 | 服务包 | a) 新建 `src/services/lsrag_structurize/`。b) `binder.py`：从已读出的 primitive（`clean_text`、`clean_artifact_uuid`、`clean_digest`、`layered_candidate`、`granularity_set`、两个 artifact uuid）得到不可变 `StructurizeBinding`；缺字段 fail-closed。c) `admit.py`：调用既有 `LsragContractCompiler.normalize_layered_candidate`（`lsrag_compiler.py:259-277`）+ `adopt_layered_json_with_report`（`:393`）+ `validate_structure`（`:657`）；返回 structure/projection/accepted_candidate/report。d) `service.py`：唯一公开 facade `admit(binding) -> result`。e) **禁止** import `src.runtime` / `src.llm_adapters` / HTTP / DB driver。f) **禁止** 新的 ProcessCommand 平行类型；Command 仍是 `contracts.runtime.models.ProcessCommand`；wire candidate 仍走 `validate_layered_content`（`layered_content.py:66`）。g) 不要建 `src/contracts/lsrag/structure/` 空包凑路径。 | 🆕 四文件；对照 `intake_lifecycle/service.py:1-10` 的包形状，但 **不要** 再引入 Mixin | 纯函数可单测 | NS3-T10–T14 | 服务测试不建 DB |
| P2-02 | Mixin 接线 | a) `_structurize`（`:882-1106`）保留：读 clean（经 artifacts `:48-54`）、分配 uuid、`_compression_channel`（`:93-109`）、live（`generation_live.py:171`）或 CLI（`:336`）或 state candidate（`:305`）。b) 得到 candidate 后改调 `LsragStructurizeService.admit`。c) Mixin **删除** 对 `compiler.normalize_layered_candidate` / `adopt_layered_json_with_report` 的直接编排。d) promote（`generation_artifacts.py:56-68`）与 `callback`（`:1043-1053`）仍在 Mixin，同一 `core.py:121-129` commit 路径。e) 不改 `core.py:342` 的 process_key 分发。f) 不把 salvage 闭集（`:44-61`）搬进服务。 | `generation_construct.py:882-1106`；`generation_artifacts.py:56-68,99`；`generation_live.py:171` | handler 变薄但契约不变 | NS3-T15–T22 T24 T25 | Mixin 源码不再出现 `adopt_layered_json_with_report` |
| P2-03 | P2 独立测试 | a) 新建 `tests/unit/test_lsrag_structurize_service.py` 覆盖 binder/admit 成败。b) fork `test_lsrag_compiler.py` / `test_adopt_layered_json.py` / `test_layered_schema.py`（0 行为差）。c) fork `test_ns1_generation_cli.py` 的 B.json 路径，断言仍经 Mixin I/O。d) 跑 `tests/e2e/test_ns1_pipeline.py` 作为 P2 出闸（不是本 AP 最终 mega）。e) architecture：无新 intake Mixin。 | 🆕 服务单测；既有 compiler/cli/e2e | P2 可独立证明 | NS3-T10–T25 | §4.2 映射全绿 |

### 4.3 Phase 3 — S07 construct 叶服务

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P3-01 | 服务包 | a) 新建 `src/services/lsrag_construct/`。b) `binder.py`：`full_construct` vs `metadata_refresh`（`generation_artifacts.py:187` 的语义，但函数收纯字段，不读 DB）。c) `reconstruct.py`：再证 S06 handoff（今日 `_reconstruct_structure_contract` 的 compiler 段 `:413-419`）以及「bytes == `construction_payload` / digest 匹配」（今日 `:875-878`）。读对象字节仍由 Mixin/`_read_frozen_generation_asset`（`:152`）完成，服务只收已读 bytes。d) `admit.py`：wrap `compiler.construct`（`:744`）+ `validate_construction`（`:814`）+ `layered_summary_map`（`:553`，在 **已有 completed JSON** 上映射，不打模型）。e) `service.py` facade。f) 同样零 I/O。 | 🆕 五文件 | 再证与 construct 可无 DB 单测 | NS3-T30–T33 T45 T46 | 服务测试注入 bytes/candidate |
| P3-02 | Mixin 接线 | a) `_construct`（`:1108-1367`）保留 mode 分支、uuid、promote、callback（`:1270`）。b) `full_construct`：Mixin 仍跑 `_complete_construct_summaries`（`:167-246`）——此处含 live/CLI/deterministic/salvage，**整段留 Mixin**。c) 得到 `summaries` 后改调 construct 服务 `admit`。d) `_reconstruct_structure_contract`（`generation_artifacts.py:398-419`）的 adopt 段改调 construct 或 structurize 服务的 reconstruct；读 artifact 留下。e) `_reconstruct_metadata_refresh_contract`（`:600-817`）：I/O/读成员留 Mixin；再证/construct 内核进服务。f) `_reconstruct_construct_contract`（`:818-879`）同样切分。g) `_can_salvage_local_inference`（`:131-143`）与 `_salvage_summary_via_cli`（`:148`）一字不改语义。 | 上表行号 | C 运输与 salvage 回归 0 差 | NS3-T34–T40 T44 T47 | Mixin 不再直接 `compiler.construct(` |
| P3-03 | P3 独立测试 | a) 🆕 `tests/unit/test_lsrag_construct_service.py`。b) 🔱 `test_dispatch_generation.py`（salvage/车道必须仍绿）。c) 🔱 `test_compression_channel.py` salvage 段。d) ♻️ `test_generation_pipeline_contracts.py`。e) P2 测试集重跑（禁止 P3 打红 P2）。f) `test_ns1_pipeline.py` 再出闸。 | 新+旧测试 | P3 可独立证明 | NS3-T30–T48 | §4.3 映射全绿且 P2 集仍绿 |

### 4.4 Phase 4 — compiler 包内拆分

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P4-01 | 收成包 | a) 新建 `src/services/lsrag_compiler/`。b) `models.py` ← IR dataclass（今日 `:61-169`）。c) `adopt.py` ← `normalize_layered_candidate` / `adopt_*` / `_adopt_layered_json`（`:259-551`）。d) `validate.py` ← `validate_structure` / `validate_construction`（`:657-838`）。e) `payloads.py` ← digest/payload/parse（`:176-247,876-1119`）。f) `compiler.py` ← `LsragContractCompiler` 编排（`:249,306,553,608,637,744,839`）。g) `__init__.py` 重导出今日所有公开名（`LsragContractCompiler`、全部 Document/Projection、全部 `*_payload` / `parse_*` / `deterministic_summaries` / `summary_plan`）。h) **删除** `src/services/lsrag_compiler.py`（与包不能并存）。i) **禁止** `src/contracts/lsrag/models.py`。j) 禁止改算法、禁止改 digest 配方。 | `lsrag_compiler.py` 全文件；所有 `from src.services.lsrag_compiler import` 调用方（construct Mixin、两新服务、测试） | import 路径不变 | NS3-T50 T54 T55 T56 T58 | `python -c "from src.services.lsrag_compiler import LsragContractCompiler, StructureDocument"` |
| P4-02 | P4 独立测试 | a) 既有 `test_lsrag_compiler.py` / `test_adopt_layered_json.py` / `test_layered_schema.py` **0 改断言语义**。b) 新测：公开 `__all__` 闭集。c) 重跑 P2+P3 测试集。d) architecture：无 `contracts/lsrag/models.py`；compiler 包子树仍无 HTTP/DB。 | 既有 compiler 三测 + 守卫 | 导航拆分不改核 | NS3-T50–T58 | P2+P3+P4 集全绿 |

### 4.5 Phase 5 — 回归、文档、收口

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P5-01 | mega/soak | a) `tests/e2e/test_ns1_pipeline.py`。b) `tests/e2e/test_ns2_dispatch_lanes.py`。c) `tests/e2e/test_generation_pipeline_contracts.py`。d) `tests/unit/test_dispatch_admit_soak.py`。e) `uv run pytest tests/unit tests/domain`。f) `uv run ruff check src tests api`。 | 既有金样 | 提取不改产品 | NS3-T60–T66 T70 T71 T73–T75 | 全绿四元组 |
| P5-02 | 窄回填 | S06-E01 表补一句「`src/services/lsrag_structurize/` 已落地；Command 仍为 ProcessCommand」。S07-E01 对 `lsrag_construct` 同样一句。不改 T-O、不改 QNA。 | `S06-lsrag-structurizer.md:438-445`；`S07-lsrag-constructor.md:256-265` | 路径与代码一致 | NS3-T67 | 附录级 |
| P5-03 | closure | 按 `.adocs/closure.md` 写 NS3 closure。成功声明必须写「能力边界落地」，**禁止**写「>500 文件减少 N」。`D-MEGA-*` 不进 deferred ledger。 | 🆕 closure | owner 30 秒可读 | NS3-T68 T69 T72 | close-type 合法 |

---

## 5. Phase 详情

### 5.1 Phase 1 — 分类守卫

- **Phase 目标**：错误拆法进不了 main。
- **本 Phase 对应编号**：`P1-01` / `P1-02`
- **本 Phase 新增文件**：无生产文件；只加 `tests/domain/test_architecture.py` 内测试函数
- **本 Phase 修改文件**：`tests/domain/test_architecture.py:336-475` 之后追加守卫
- **本 Phase 删除文件**：无
- **具体功能预期**：
  1. `src/workflows/` 下出现 `.yaml`/`.yml` → domain 测试失败。
  2. 创建 `src/contracts/lsrag/models.py` → 失败。
  3. 在 `src/runtime/intake/` 新增 `IntakeConstructExecutorMixin` 之类 → 失败；现有 `IntakeGenerationConstructMixin` 仍合法。
  4. `WorkflowRuntime.__mro__` 仍含七个 Mixin，缺一失败。
  5. `IntakePipeline` 仍声明 `ProcessStageHandler`。
  6. 生产树出现 `class TxHandler` / `class TransactionalCommand` → 失败。
  7. 本 Phase 不修改 `src/`。
- **对应测试台账项**：`NS3-T01` … `NS3-T08`
- **收口标准**：domain 新守卫绿；`git diff --stat src` 为空。
- **本 Phase 风险提醒**：守卫过宽会误伤既有 Mixin（`IntakeGenerationConstructMixin` 必须白名单）。

### 5.2 Phase 2 — S06 structurize 叶服务

- **Phase 目标**：structurize 叶算法可在无 facade/CLI/DB 下单测；handler 仍负责运输。
- **本 Phase 对应编号**：`P2-01` … `P2-03`
- **本 Phase 新增文件**：`src/services/lsrag_structurize/{__init__,binder,admit,service}.py`；`tests/unit/test_lsrag_structurize_service.py`
- **本 Phase 修改文件**：`generation_construct.py:882-1106`
- **本 Phase 删除文件**：无
- **具体功能预期**：
  1. `admit` 在合法 layered candidate + clean 上产出与今日 compiler 路径 byte-identical 的 structure/projection payload。
  2. 缺 candidate / 非法 profile / clean digest 不匹配 → 原错误码（`STRUCTURE_CANDIDATE_MISSING` / `STRUCTURE_PROFILE_INVALID` / `STRUCTURE_BINDING_CLEAN_DIGEST`）。
  3. 服务模块 AST 无 `src.runtime` / `src.llm_adapters` / HTTP / driver import。
  4. live 通道仍只从 Mixin 调 `_live_structured_generate`（`generation_live.py:171`）。
  5. NI 通道仍只从 Mixin 调 `_cli_layered_candidate`（`:336`）。
  6. `callback` 仍写 schema_digest 校验 + invocation 记录（`:1043-1053`），与 promote 同一次 Process commit。
  7. `core.py:342` 仍分发到同一 Mixin 方法名。
  8. 失败路径不得 silent 用确定性结构顶上（保持 NS1「无 candidate 即失败」）。
- **对应测试台账项**：`NS3-T10` … `NS3-T25`
- **收口标准**：P2 测试集全绿；Mixin 源码无 `adopt_layered_json_with_report`。
- **本 Phase 风险提醒**：digest 配方稍有移动就会打红 generation 金样。服务必须调用 **同一个** compiler 方法，禁止重写 adopt。

### 5.3 Phase 3 — S07 construct 叶服务

- **Phase 目标**：construct 叶算法可无 I/O 单测；NS2 salvage 行为 0 差。
- **本 Phase 对应编号**：`P3-01` … `P3-03`
- **本 Phase 新增文件**：`src/services/lsrag_construct/{__init__,binder,reconstruct,admit,service}.py`；`tests/unit/test_lsrag_construct_service.py`
- **本 Phase 修改文件**：`generation_construct.py:167-246`（**不改控制流**，只改其后 `compiler.construct` 调用点）、`:600-879`、`:1108-1367`；`generation_artifacts.py:398-419`
- **本 Phase 删除文件**：无
- **具体功能预期**：
  1. `full_construct`：Mixin 填完 summaries 后，服务 `construct` 结果与今日一致（含 dual-channel required-set）。
  2. `metadata_refresh`：仍走 `_reconstruct_metadata_refresh_contract` 的读路径；内核再证进服务。
  3. `_reconstruct_construct_contract`：bytes 不匹配仍 409 `CONSTRUCT_TO_VECTORIZE_GATE`。
  4. `normal` + local 失败仍 salvage 一次 CLI（`test_dispatch_generation.py:160`）。
  5. `low` 失败 0 次 CLI（`:207`）。
  6. `_complete_construct_summaries` 仍根据 `_summary_transport`（`:111-129`）选择 live/CLI/deterministic。
  7. 服务在缺 summary / original 被改写时 fail-closed（compiler 既有码）。
  8. P2 测试集在 P3 后仍全绿。
- **对应测试台账项**：`NS3-T30` … `NS3-T48`
- **收口标准**：P3 集 + P2 集全绿；Mixin 源码无裸 `compiler.construct(`。
- **本 Phase 风险提醒**：把 `_complete_construct_summaries` 搬进服务会迫使 services import facade，直接打红 `test_architecture.py:356`。禁止。

### 5.4 Phase 4 — compiler 包内拆分

- **Phase 目标**：1,161 行核可导航；对外符号与 digest 不变。
- **本 Phase 对应编号**：`P4-01` / `P4-02`
- **本 Phase 新增 / 修改 / 删除文件**：🆕 包内 6 文件；删除 `src/services/lsrag_compiler.py`
- **具体功能预期**：
  1. 既有 import 语句无需修改即可工作（包 `__init__.py` 重导出）。
  2. `test_lsrag_compiler.py` 六条用例 0 改语义通过。
  3. adopt / layered schema 测通过。
  4. P2/P3 服务仍 `from src.services.lsrag_compiler import LsragContractCompiler`。
  5. 不存在 `src/contracts/lsrag/models.py`。
  6. 包内模块同样受 services 边界守卫约束。
- **对应测试台账项**：`NS3-T50` … `NS3-T58`
- **收口标准**：compiler 金样 + P2/P3 集全绿。
- **本 Phase 风险提醒**：同名 `.py` 与目录不能并存。必须先加包、改重导出、再删单文件，同一 commit 完成。

### 5.5 Phase 5 — 回归、文档、收口

- **Phase 目标**：产品语义与 NS2 调度合同保持；文档与 closure 诚实。
- **本 Phase 对应编号**：`P5-01` … `P5-03`
- **本 Phase 新增 / 修改 / 删除文件**：S06/S07 各一句；🆕 closure
- **具体功能预期**：
  1. NS1 stub 金样 succeeded，图步齐全。
  2. NS2 四车道行上 `dispatch_pool` / `admitted` 仍可见。
  3. soak 三池不超卖。
  4. closure 写明「非行数治理」；无 `D-MEGA-*` ledger 条目。
- **对应测试台账项**：`NS3-T60` … `NS3-T75`
- **收口标准**：§10 硬闸全 PASS 且四元组齐全方可标 `executed`。
- **本 Phase 风险提醒**：不得把 VF V11 turso I/O 写成 NS3 失败。

---

## 6. 依赖的冻结设计决策（只读引用）

> 本 AP 不改口、不新开 Q。业主 2026-08-15 指令只选择「执行哪张地图」，不改写下列 Truth。

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| `T-O-142` | D03：单体单一发布单元 | 保留一个 `ProcessStageHandler` 类型 | 停工 |
| `T-O-143` | D03：Workflow ≠ Runtime | 不改 `lsrag_definition.py` 为 YAML | 停工 |
| `T-O-150` | D03：services = 原子叶能力 | P2/P3 新包落在 `src/services/` | 停工 |
| `T-O-151` | D03：services 禁 llm_adapters | 服务零推理 I/O | 违反则 architecture 红、回滚 |
| `T-O-152` / `T-O-154` | D03：contracts 只解释跨层消息 | IR 留 compiler 包；不建 `contracts/lsrag/models.py` | 停工 |
| `S03-T002/T003/T005` | S03：六平面 + 七表 + 内部注册 | 禁 YAML/Fluent | 停工 |
| `S03-T021` | S03：叶只吃 Command 吐 Outcome | 不另造叶状态机 | 停工 |
| `S06-E01` | S06:438-445 | 目录名必须是 `lsrag_structurize` | 改名即偏离 |
| `S07-E01` | S07:256-265 | 目录名必须是 `lsrag_construct` | 改名即偏离 |
| NS2 A-6 | NS2 AP §7.1 | Mixin 根不改 | 停工 |
| NS2 A-19 / A-20 | `generation_construct.py:44-61,93-216` | salvage/通道留 Mixin | 回归红则回滚 P3 |
| `T-O-353..361` | NS2 业主冻结 | 不改三池/claim/DDL | 停工 |
| `T-O-173` | D04-P04 | 不把提取态写入 `payload_extra` | 停工 |
| 本会话业主指令 | 2026-08-15 | 按本评估执行；禁 LOC 闸 | 本 AP 保持 draft |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表（本计划工作要落在哪些既有代码 / 新建点上）

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| A-1 | `src/runtime/intake/generation_construct.py:64-65` | `IntakeGenerationConstructMixin` | P2/P3 改方法，不改类名 | `♻️ 重 substrate` | 白名单；禁止再切子 Mixin |
| A-2 | `src/runtime/intake/generation_construct.py:44-61` | salvage 错误闭集 | 不改 | `✅ 复用` | NS2 A-19 |
| A-3 | `src/runtime/intake/generation_construct.py:93-109` | `dispatch_pool` 为通道 SSOT | 不改 | `✅ 复用` | NS2 合同 |
| A-4 | `src/runtime/intake/generation_construct.py:111-129` | C transport 选择 | P3 留 Mixin | `✅ 复用` | |
| A-5 | `src/runtime/intake/generation_construct.py:131-146` | `normal` 才 salvage | 不改 | `✅ 复用` | NS2-T37 攻击向量 |
| A-6 | `src/runtime/intake/generation_construct.py:148-165` | salvage CLI | 不改 | `✅ 复用` | |
| A-7 | `src/runtime/intake/generation_construct.py:167-246` | `_complete_construct_summaries` I/O+salvage | P3 **禁止迁服务** | `✅ 复用` | 含 live/CLI/deterministic |
| A-8 | `src/runtime/intake/generation_construct.py:249-264` | bjson 物料 / structurize 输入文本 | P2 可随 binder 纯调用 | `✅ 复用` | 无 I/O |
| A-9 | `src/runtime/intake/generation_construct.py:336-388` | `_cli_layered_candidate` | P2 I/O 留下 | `✅ 复用` | |
| A-10 | `src/runtime/intake/generation_construct.py:390-443` | `_cli_layered_summary` | P3 I/O 留下 | `✅ 复用` | |
| A-11 | `src/runtime/intake/generation_construct.py:444-516` | `_live_markdown_text` | 不抽服务 | `✅ 复用` | O9 |
| A-12 | `src/runtime/intake/generation_construct.py:517-598` | `_transcribe_markdown` + TX callback | 不抽服务 | `✅ 复用` | process handler |
| A-13 | `src/runtime/intake/generation_construct.py:600-817` | `_reconstruct_metadata_refresh_contract` | P3：I/O 留、再证走服务 | `♻️ 重 substrate` | 216L |
| A-14 | `src/runtime/intake/generation_construct.py:818-879` | `_reconstruct_construct_contract` | P3 切分 | `♻️ 重 substrate` | bytes 比对 `:875-878` |
| A-15 | `src/runtime/intake/generation_construct.py:882-1106` | `_structurize` | P2 主战场 | `♻️ 重 substrate` | 224L |
| A-16 | `src/runtime/intake/generation_construct.py:1043-1053` | structurize TX callback | 必须留 Mixin | `✅ 复用` | 与 `core.py:121` 同事务 |
| A-17 | `src/runtime/intake/generation_construct.py:1108-1367` | `_construct` | P3 主战场 | `♻️ 重 substrate` | 260L |
| A-18 | `src/runtime/intake/generation_construct.py:1270` | construct TX callback | 留 Mixin | `✅ 复用` | |
| A-19 | `src/runtime/intake/generation.py:14-18` | generation 三 Mixin facade | 不改 MRO | `✅ 复用` | 已建好别重写 |
| A-20 | `src/runtime/intake/generation_artifacts.py:56-68` | `_promote_generation_member` | P2/P3 继续用 | `✅ 复用` | S13 promote |
| A-21 | `src/runtime/intake/generation_artifacts.py:99-126` | validation report payload | 可由服务返回字段、Mixin 组装 | `✅ 复用` | |
| A-22 | `src/runtime/intake/generation_artifacts.py:187` | `_construct_mode` | P3 binder 语义对齐 | `✅ 复用` | |
| A-23 | `src/runtime/intake/generation_artifacts.py:398-419` | `_reconstruct_structure_contract` compiler 段 | P3 迁服务 | `♻️ 重 substrate` | 读 artifact 留下 |
| A-24 | `src/runtime/intake/generation_artifacts.py:518-532` | ConstructToVectorizeGate | 不改成功面 | `✅ 复用` | `T-O-206` |
| A-25 | `src/runtime/intake/generation_live.py:171-183` | live structured generate | P2 I/O | `✅ 复用` | |
| A-26 | `src/runtime/intake/generation_live.py:304-312` | live C summary | P3 I/O | `✅ 复用` | |
| A-27 | `src/runtime/intake/core.py:121-129` | `run` + 单次 commit | 不拆 TX | `✅ 复用` | |
| A-28 | `src/runtime/intake/core.py:316-351` | process_key 分发表 | 不改 key | `✅ 复用` | `:342-343` S06/S07 |
| A-29 | `src/runtime/intake/pipeline.py:18-27` | IntakePipeline 组合根 | P1 冻结 | `✅ 复用` | 不是 8,786 行文件 |
| A-30 | `src/runtime/workflow/runtime.py:14-22` | WorkflowRuntime 7 Mixin | P1 冻结 | `✅ 复用` | NS2 A-6 |
| A-31 | `src/runtime/workflow/dispatch.py:20-38` | generate/embed 分类 | 不改 | `✅ 复用` | NS2 纯函数样板 |
| A-32 | `src/runtime/workflow/dispatch.py:120,146` | `pool_kind` / `choose_pool` | 不改 | `✅ 复用` | |
| A-33 | `src/runtime/workflow/helpers.py:17` | `canonical_outcome_digest` | 不改 | `✅ 复用` | 抽纯函数样板 |
| A-34 | `src/services/lsrag_compiler.py:61-169` | compiler IR dataclass | P4 → `models.py` | `♻️ 重 substrate` | **不要**进 contracts |
| A-35 | `src/services/lsrag_compiler.py:249-277` | `LsragContractCompiler` + normalize | P2 调用；P4 搬家 | `✅ 复用` | 禁重写 |
| A-36 | `src/services/lsrag_compiler.py:362-551` | adopt / `_adopt_layered_json` | P2/P4 | `✅ 复用` | 135L 热点留在核内 |
| A-37 | `src/services/lsrag_compiler.py:553-635` | summary map / fill | P3 在已完成 JSON 上调用 | `✅ 复用` | |
| A-38 | `src/services/lsrag_compiler.py:657-838` | validate structure/construction | P2/P3 | `✅ 复用` | |
| A-39 | `src/services/lsrag_compiler.py:744-812` | `construct` | P3 | `✅ 复用` | |
| A-40 | `src/services/lsrag_compiler.py:895-1108` | payload/parse | P4 → `payloads.py` | `♻️ 重 substrate` | 配方锁定 |
| A-41 | `src/contracts/lsrag/layered_content.py:66` | wire 校验 | P2 candidate 入服务前/内调用 | `✅ 复用` | 已是 contracts |
| A-42 | `src/contracts/lsrag/__init__.py:1-9` | 现有 lsrag 合同面 | 不扩成 models.py | `✅ 复用` | |
| A-43 | `src/contracts/runtime/models.py`（`ProcessCommand`） | 叶命令 SSOT | 不另造 | `✅ 复用` | S03-T021 |
| A-44 | `src/persistence/ports.py:11-16` | `UnitOfWork` | 不另造 Command | `✅ 复用` | |
| A-45 | `src/workflows/lsrag_definition.py:162-198` | md/structurize/construct/vectorize 步 | 不改图 | `✅ 复用` | 类别 A |
| A-46 | `src/services/intake_lifecycle/service.py:1-10` | 服务包先例 | 只借目录形状 | `✅ 复用` | **不要**再抄 Mixin |
| A-47 | `src/runtime/workflow/dispatch.py:1-18` | 无 I/O 策略模块先例 | P2/P3 服务写法对标这里 | `✅ 复用` | 最佳样板 |
| A-48 | `tests/domain/test_architecture.py:356-376` | services 边界 | P1 扩展 | `✅ 复用` | |
| A-49 | `tests/domain/test_architecture.py:406-413` | workflows 禁 runtime 符号 | P1 YAML 守卫旁路 | `✅ 复用` | |
| A-50 | `tests/domain/test_architecture.py:461-475` | NS2 无新表 | P5 回归 | `✅ 复用` | 本 AP 也不加表 |
| A-51 | `tests/unit/test_lsrag_compiler.py:35-175` | compiler 金样 6 条 | P2/P4 🔱 | `✅ 复用` | 0 改语义 |
| A-52 | `tests/unit/test_adopt_layered_json.py:32-165` | adopt + C 整包 | P2/P4 | `✅ 复用` | |
| A-53 | `tests/unit/test_dispatch_generation.py:70-236` | 通道 + salvage | P3 硬回归 | `✅ 复用` | |
| A-54 | `tests/unit/test_ns1_generation_cli.py:15-95` | B.json / C 一次整包 | P2/P3 | `✅ 复用` | |
| A-55 | `tests/e2e/test_ns1_pipeline.py:86` | NS1 金样 | P2/P3 出闸 + P5 mega | `♻️ 沿用` | |
| A-56 | `tests/e2e/test_ns2_dispatch_lanes.py:93` | 四车道 | P5 | `♻️ 沿用` | 证明没碰调度 |
| A-57 | `tests/e2e/test_generation_pipeline_contracts.py:25` | 成员独立 + 每通道 vectorize | P3/P5 | `♻️ 沿用` | |
| A-58 | `tests/unit/test_dispatch_admit_soak.py` | 32×32 不超卖 | P5 | `♻️ 沿用` | |
| A-59 | `src/runtime/intake/acceptance_snapshot.py` `_accept_snapshot` 334L | S04 超长 TX | **别碰** | `✅ 复用` | O7 |
| A-60 | `src/services/lsrag_structurize/` | 将新建 | P2-01 | `🆕 净新` | S06-E01 名 |
| A-61 | `src/services/lsrag_construct/` | 将新建 | P3-01 | `🆕 净新` | S07-E01 名 |
| A-62 | `src/services/lsrag_compiler/` | 将新建包 | P4-01 | `🆕 净新` | 替换单文件 |
| A-63 | `docs/closure/new-start/NS3-megafile-governance-closure.md` | 将新建 | P5-03 | `🆕 净新` | |

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | 再切 `construct_markdown.py` / `construct_executor.py` / `construct_contract_builder.py` 三个 Mixin | Gemini 方案；本评估否决；P1-01 守卫 |
| ⛔2 | YAML / Fluent WorkflowBuilder / 外置 `lsrag_definition` | `S03-T002/T005`；该文件是 typed 图不是字典债 |
| ⛔3 | 去 Mixin 重写 `WorkflowRuntime` / `IntakePipeline` | NS2 A-6；`T-O-142`；逻辑类体积 ≠ 文件债 |
| ⛔4 | 新造 `TransactionalCommand` / 第二 UoW | `ports.py:11` + `callback(tx, refs)` 已存在 |
| ⛔5 | `src/contracts/lsrag/models.py` 倾倒 12 个 IR | `T-O-152/154`；S06 路径是 `structure/` 且 Command 已存在 |
| ⛔6 | 把 salvage / `_complete_construct_summaries` 搬进 services | 会 import facade，打红 `:356`；破坏 NS2-T36/T37 |
| ⛔7 | 拆 `_accept_snapshot` 或为行数拆 TX | S04 原子性；无 charter |
| ⛔8 | 改 `dispatch.py` / `claim_next` / 011 列 | NS2 已闭；本 AP 0 调度语义 |
| ⛔9 | 以「>1000 归零 / >500 减 60% / 消灭 >200 行方法」收口 | 业主否决；与本 AP §5 反镀金同句 |
| ⛔10 | 把 `D-MEGA-*` 写入 deferred ledger | NS2 从未承诺 megafile；那是 OOS 不是 defer |
| ⛔11 | 服务层重写 adopt/construct 算法 | digest 漂移；必须 **调用** compiler |
| ⛔12 | 先删 `lsrag_compiler.py` 再加包却分两个 commit | 中间树不可 import |
| ⛔13 | 单测压到 <300 行 / 通用 Object Mother | 会藏 D01/S03 不变量 |
| ⛔14 | 把 `pipeline.py` 写成「8,786 行文件」来驱动拆分 | 那是 MRO 加总，文件约 36 行 |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：无。§7.1 即本 AP grounding 真源。Gemini eval 只作反例输入，不摘进锚表当落点。
- **安全 / 信任边界类工作项的威胁模型锚**：
  - 叶服务无 I/O → 不能经 HTTP 漏 token；由 `test_architecture.py:356-376` + 本 AP `NS3-T14/T55/T75` 锁死。
  - salvage 仍是套餐攻击面：`low` 不得升 NI（`generation_construct.py:131-143` + 既有 `NS2-T37` / 本 AP `NS3-T39`）。
  - 不新增 public route；`test_public_routes_do_not_expose_ui_workflow_or_oauth_surface`（`:416-427`）+ `NS3-T74`。
  - 不把 prompt 正文写入服务返回值；继续 hash 指针（`T-O-155`）。
  - S16 信任边界文件：`docs/baseline/domain-truth/S16-security-trust-boundary.md`（本轮不改写；无新外发面）。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| NS3-T01 | `src/workflows` 无 yaml/yml | 短途 | 契约 | 🆕 `test_architecture.py` | P1-01 → 禁 DSL 外置 | commit + test + run-time |
| NS3-T02 | 不存在 `src/contracts/lsrag/models.py` | 短途 | 契约 | 同上 | P1-01 P4-01 | commit + test + run-time |
| NS3-T03 | `runtime/intake` 无新增 S06/S07 Mixin 类 | 短途 | 契约 | 同上 | P1-01 P2-02 P3-02 | commit + test + run-time |
| NS3-T04 | `WorkflowRuntime` 七 Mixin MRO 冻结 | 短途 | 契约 | 同上 | P1-02 | commit + test + run-time |
| NS3-T05 | `IntakePipeline` 组合根冻结 | 短途 | 契约 | 同上 | P1-02 | commit + test + run-time |
| NS3-T06 | 生产代码无 `TxHandler`/`TransactionalCommand` | 短途 | 契约 | 同上 | P1-01 | commit + test + run-time |
| NS3-T07 | P1 不改 `src/`（守卫 Phase 的 git 断言可手工；测试断言 generate keys 仍在） | 短途 | unit | 🔱 `test_dispatch_policy.py` | P1-02 | commit + test + run-time |
| NS3-T08 | services 仍禁 llm_adapters/HTTP/driver | 短途 | domain | ♻️ `test_architecture.py:356` | P1-01 P2-01 P3-01 | commit + test + run-time |
| NS3-T10 | binder：缺 clean/profile/candidate fail-closed | 短途 | unit | 🆕 `test_lsrag_structurize_service.py` | P2-01 | commit + test + run-time |
| NS3-T11 | binder：非法 granularity（无 g0 / 非 0-2）原码 | 短途 | unit | 同上 | P2-01 | commit + test + run-time |
| NS3-T12 | admit：合法 candidate → structure/projection 与直调 compiler 一致 | 短途 | unit | 同上 + 对照 `test_lsrag_compiler.py:35` | P2-01 | commit + test + run-time |
| NS3-T13 | admit：无 candidate / summaries 非 null → 原 STRUCTURE_* 码 | 短途 | unit | 同上 | P2-01 | commit + test + run-time |
| NS3-T14 | `lsrag_structurize` AST 无 runtime/llm_adapters/HTTP/driver | 短途 | 契约 | 🆕 或并入 architecture | P2-01 | commit + test + run-time |
| NS3-T15 | Mixin `_structurize` 仍 promote 三成员 + callback 写 invocation | 短途 | unit | 🔱 `test_ns1_generation_cli.py` / 新 handler 测 | P2-02 | commit + test + run-time |
| NS3-T16 | live 通道仍调用 facade，不经服务 | 短途 | unit | 🔱 `test_dispatch_generation.py` 结构可仿 | P2-02 | commit + test + run-time |
| NS3-T17 | NI 通道仍调用 CLI stub | 短途 | unit | 🔱 `test_ns1_generation_cli.py:15` | P2-02 | commit + test + run-time |
| NS3-T18 | `test_lsrag_compiler.py` 六条 0 差 | 短途 | unit | ♻️ | P2-03 P4-02 | commit + test + run-time |
| NS3-T19 | `test_adopt_layered_json.py` 0 差 | 短途 | unit | ♻️ | P2-03 P4-02 | commit + test + run-time |
| NS3-T20 | `test_layered_schema.py` 0 差 | 短途 | unit | ♻️ | P2-03 | commit + test + run-time |
| NS3-T21 | structure digest 与提取前金样相同 | 短途 | unit | 🆕 对照 payload digest | P2-02 | commit + test + run-time |
| NS3-T22 | Mixin 源码无 `adopt_layered_json_with_report` | 短途 | 契约 | 🆕 rg/AST | P2-02 | commit + gate + run-time |
| NS3-T23 | P2 出闸：`test_ns1_pipeline.py` | spike | e2e | ♻️ | P2-03 | commit + test + run-time |
| NS3-T24 | P2 后 T03 仍绿（无新 Mixin） | 短途 | domain | ♻️ P1 | P2-02 | commit + test + run-time |
| NS3-T25 | `core.py` 仍把 `lsrag.structurize` 分到 `_structurize` | 短途 | 契约 | 🆕 或 AST | P2-02 | commit + test + run-time |
| NS3-T30 | reconstruct：合法 S06 handoff 再证通过 | 短途 | unit | 🆕 `test_lsrag_construct_service.py` | P3-01 | commit + test + run-time |
| NS3-T31 | reconstruct：bytes ≠ payload → `CONSTRUCT_TO_VECTORIZE_GATE` | 短途 | unit | 同上 | P3-01 P3-02 | commit + test + run-time |
| NS3-T32 | admit：缺 summary fail-closed | 短途 | unit | 对照 `test_lsrag_compiler.py:175` | P3-01 | commit + test + run-time |
| NS3-T33 | admit：full_valid dual-channel + required-set | 短途 | unit | 对照 `test_lsrag_compiler.py:120` | P3-01 | commit + test + run-time |
| NS3-T34 | `metadata_refresh` 仍可读冻结成员并再证 | 短途 | unit | 🔱 metadata 相关既有测 | P3-02 | commit + test + run-time |
| NS3-T35 | `_complete_construct_summaries` 仍在 Mixin（源码扫描 `claude_cli`/`_live_layered`） | 短途 | 契约 | 🆕 | P3-02 | commit + gate + run-time |
| NS3-T36 | Mixin 源码无裸 `compiler.construct(` | 短途 | 契约 | 🆕 | P3-02 | commit + gate + run-time |
| NS3-T37 | `_reconstruct_construct_contract` 语义保留 | 短途 | unit | 🔱 generation contracts | P3-02 | commit + test + run-time |
| NS3-T38 | construct 仍 promote construction/dual/report | 短途 | unit | 🔱 `test_generation_pipeline_contracts.py` 前置 | P3-02 | commit + test + run-time |
| NS3-T39 | `low` 失败 0 次 CLI（攻击向量） | 短途 | unit | ♻️ `test_dispatch_generation.py:207` | P3-02 → §7.3 | commit + test + run-time |
| NS3-T40 | `normal` local 失败 salvage 一次 | 短途 | unit | ♻️ `test_dispatch_generation.py:160` | P3-02 | commit + test + run-time |
| NS3-T41 | compiler construct 金样仍绿 | 短途 | unit | ♻️ `test_lsrag_compiler.py` | P3-03 | commit + test + run-time |
| NS3-T42 | generation pipeline e2e 成员独立 | spike | e2e | ♻️ `test_generation_pipeline_contracts.py:25` | P3-03 | commit + test + run-time |
| NS3-T43 | NS1 C 整包一次（`test_ns1_generation_cli.py:15`） | 短途 | unit | ♻️ | P3-03 | commit + test + run-time |
| NS3-T44 | P3 后 T03 仍绿 | 短途 | domain | ♻️ | P3-02 | commit + test + run-time |
| NS3-T45 | `full_construct` vs `metadata_refresh` binder 分叉 | 短途 | unit | 🆕 | P3-01 | commit + test + run-time |
| NS3-T46 | original 被改写 → `CONSTRUCT_KERNEL_ORIGINAL_MUTATION` | 短途 | unit | 🔱 `test_adopt_layered_json.py:133` | P3-01 | commit + test + run-time |
| NS3-T47 | vectorize 前 gate 仍要求 full_valid | 短途 | unit | ♻️ artifacts gate 测 / e2e | P3-02 | commit + test + run-time |
| NS3-T48 | P3 出闸：`test_ns1_pipeline.py` + **重跑 P2 集** | spike | e2e | ♻️ | P3-03 | commit + test + run-time |
| NS3-T50 | `from src.services.lsrag_compiler import LsragContractCompiler, StructureDocument, structure_payload` 成功 | 短途 | unit | 🆕 | P4-01 | commit + test + run-time |
| NS3-T51 | `test_lsrag_compiler.py` 全绿 | 短途 | unit | ♻️ | P4-02 | commit + test + run-time |
| NS3-T52 | `test_adopt_layered_json.py` 全绿 | 短途 | unit | ♻️ | P4-02 | commit + test + run-time |
| NS3-T53 | `test_layered_schema.py` 全绿 | 短途 | unit | ♻️ | P4-02 | commit + test + run-time |
| NS3-T54 | 仍无 `contracts/lsrag/models.py` | 短途 | 契约 | ♻️ T02 | P4-01 | commit + test + run-time |
| NS3-T55 | compiler 包子树无 I/O import | 短途 | domain | ♻️ `:356` | P4-01 | commit + test + run-time |
| NS3-T56 | 两叶服务仍只 import 公开名 | 短途 | unit | 🆕 | P4-01 | commit + test + run-time |
| NS3-T57 | payload roundtrip `parse(structure_payload(doc))` 等价 | 短途 | unit | 🔱 compiler 测或新断言 | P4-01 | commit + test + run-time |
| NS3-T58 | 不存在与包冲突的 `src/services/lsrag_compiler.py` | 短途 | 契约 | 🆕 | P4-01 | commit + gate + run-time |
| NS3-T60 | mega：NS1 stub 金样 | mega | e2e | ♻️ `test_ns1_pipeline.py` | P5-01 | commit + test + run-time |
| NS3-T61 | mega：NS2 四车道 | mega | e2e | ♻️ `test_ns2_dispatch_lanes.py` | P5-01 | commit + test + run-time |
| NS3-T62 | mega：generation 成员合同 | mega | e2e | ♻️ `test_generation_pipeline_contracts.py` | P5-01 | commit + test + run-time |
| NS3-T63 | soak：admit 不超卖 | soak | unit | ♻️ `test_dispatch_admit_soak.py` | P5-01 | commit + soak + run-time |
| NS3-T64 | `pytest tests/unit tests/domain` | 短途 | 回归 | ♻️ | P5-01 | commit + test + run-time |
| NS3-T65 | architecture 全守卫（含 P1） | 短途 | domain | ♻️+🆕 | P5-01 | commit + test + run-time |
| NS3-T66 | `ruff check src tests api` | 短途 | 契约 | ♻️ | P5-01 | commit + ruff + run-time |
| NS3-T67 | S06/S07 各一句路径回填 | 短途 | 文档 | 🆕 | P5-02 | commit + 人工检 |
| NS3-T68 | closure 存在且 close-type 合法、硬闸五态 | 短途 | 文档 | 🆕 | P5-03 | commit + 人工检 |
| NS3-T69 | closure **没有** LOC 成功句 / 无 `D-MEGA` ledger | 短途 | 文档 | 🆕 | P5-03 | commit + 人工检 |
| NS3-T70 | compression/salvage 全套仍绿 | 短途 | 回归 | ♻️ `test_compression_channel.py` + dispatch_generation | P5-01 | commit + test + run-time |
| NS3-T71 | NS2 claim 短途仍绿 | 短途 | 回归 | ♻️ `tests/unit/test_dispatch_*.py` | P5-01 | commit + test + run-time |
| NS3-T72 | 无 yaml 工作流（终态） | 短途 | 契约 | ♻️ T01 | P5-03 | commit + test + run-time |
| NS3-T73 | Mixin 根终态与 P1 相同 | 短途 | 契约 | ♻️ T04 T05 | P5-03 | commit + test + run-time |
| NS3-T74 | 无新 public route | 短途 | 契约 | ♻️ `:416` | P5-03 → §7.3 | commit + test + run-time |
| NS3-T75 | 两新服务 + compiler 包无 HTTP（攻击：服务外联漏密钥） | 短途 | domain | ♻️ `:356` | P5-03 → §7.3 | commit + test + run-time |

### 8.2 复用台账（沿用 / fork 的既有用例明细）

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/domain/test_architecture.py` | `🔱 fork` | + T01–T06/T08 守卫 | 已存在，PASS |
| `tests/unit/test_lsrag_compiler.py` | `♻️ 沿用` | 0 语义改动 | 已存在，P2/P4 必绿 |
| `tests/unit/test_adopt_layered_json.py` | `♻️ 沿用` | 0 | 已存在 |
| `tests/unit/test_layered_schema.py` | `♻️ 沿用` | 0 | 已存在 |
| `tests/unit/test_dispatch_generation.py` | `♻️ 沿用` | 0（salvage 必须仍打 Mixin） | 已存在，P3 硬闸 |
| `tests/unit/test_compression_channel.py` | `♻️ 沿用` | 0 | NS2 后 PASS |
| `tests/unit/test_ns1_generation_cli.py` | `🔱 fork` | 若需断言服务被调用，只加 spy，不改旅程 | 已存在 |
| `tests/unit/test_dispatch_policy.py` | `♻️ 沿用` | 0 | 已存在 |
| `tests/unit/test_dispatch_claim.py` 及 `test_dispatch_*.py` | `♻️ 沿用` | 0 | NS2 后 PASS |
| `tests/unit/test_dispatch_admit_soak.py` | `♻️ 沿用` | 0 | NS2 后 PASS |
| `tests/e2e/test_ns1_pipeline.py` | `♻️ 沿用` | 0 | P2/P3 出闸 + P5 mega |
| `tests/e2e/test_ns2_dispatch_lanes.py` | `♻️ 沿用` | 0 | P5 |
| `tests/e2e/test_generation_pipeline_contracts.py` | `♻️ 沿用` | 0 | P3/P5 |
| `tests/unit/test_workflow_runtime.py` | `♻️ 沿用` | 0；**不**抽 Factory | 已存在 |

### 8.3 分层与跑法（各类型在哪跑、何时跑）

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 P1 | `uv run pytest tests/domain/test_architecture.py tests/unit/test_dispatch_policy.py -q` | domain·unit | P1 每提交 |
| 短途 P2 | `uv run pytest tests/unit/test_lsrag_structurize_service.py tests/unit/test_lsrag_compiler.py tests/unit/test_adopt_layered_json.py tests/unit/test_layered_schema.py tests/unit/test_ns1_generation_cli.py tests/domain/test_architecture.py -q` | unit·契约 | P2 每提交 |
| spike P2 | `uv run pytest tests/e2e/test_ns1_pipeline.py -q` | e2e | **P2 出闸** |
| 短途 P3 | `uv run pytest tests/unit/test_lsrag_construct_service.py tests/unit/test_dispatch_generation.py tests/unit/test_compression_channel.py tests/unit/test_lsrag_structurize_service.py tests/unit/test_lsrag_compiler.py tests/domain/test_architecture.py -q` | unit·契约 | P3 每提交 |
| spike P3 | `uv run pytest tests/e2e/test_ns1_pipeline.py tests/e2e/test_generation_pipeline_contracts.py -q` | e2e | **P3 出闸** |
| 短途 P4 | `uv run pytest tests/unit/test_lsrag_compiler.py tests/unit/test_adopt_layered_json.py tests/unit/test_layered_schema.py tests/unit/test_lsrag_structurize_service.py tests/unit/test_lsrag_construct_service.py tests/domain/test_architecture.py -q` | unit·契约 | **P4 出闸** |
| mega | `uv run pytest tests/e2e/test_ns1_pipeline.py tests/e2e/test_ns2_dispatch_lanes.py tests/e2e/test_generation_pipeline_contracts.py -q` | e2e | **本 AP 收口** |
| soak | `uv run pytest tests/unit/test_dispatch_admit_soak.py -q` | unit 并发 | **退出硬闸** |
| 回归 | `uv run pytest tests/unit tests/domain -q && uv run ruff check src tests api` | 全短途 | Phase 5 |

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖真实 Spark / Claude 质量对比 → 交模型选型；**不假装覆盖**。
- 不覆盖 `_accept_snapshot` 334L 拆分 → 交 S04 charter。
- 不覆盖去 Mixin / YAML 工作流 → 不交后继，除非 owner reopen D03/S03。
- 不覆盖通用测试 Factory / 单测行数闸 → 不交。
- 不覆盖 VF V11 pyturso I/O → 仍交 `NS1-V11` / harness。
- 不覆盖 billing/cloud/GPU 真机 soak → 仍交 NS2 deferred。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 必带四元组。P2/P3 的「与 compiler 一致」必须比对 **payload digest / 错误码**，禁止只断言「服务返回了对象」。
- 服务测试 **禁止** 为了绿去 mock compiler 的 adopt/construct 成功；应使用真实 `LsragContractCompiler` + 最小合法 candidate。
- Handler 测试若 spy 服务，仍须走完 promote/错误码，避免「调用了服务就算过」。
- `degraded` 必带 `reason`；turso I/O 标 `pre-existing` + NS1 引用。
- 安全项 T39 / T75 必须保留攻击向量（low salvage、服务外联）。
- **禁止**用「文件变短」替代任何 Test-ID。

### 8.6 用例详述（每个 Test-ID 的场景 / 步骤 / 期望）

**NS3-T01。** 扫描 `src/workflows` 递归。命中 `.yaml`/`.yml` 失败。期望 0。

**NS3-T02。** `Path("src/contracts/lsrag/models.py").exists()` 为 False。

**NS3-T03。** AST 扫描 `src/runtime/intake/*.py` 的 `ClassDef`。允许已存在的 `IntakeGenerationConstructMixin` 等（测试内写死允许名单 = 本 AP 开工日已有 Mixin）。新增匹配 `Structurize|Construct|Markdown|Executor` 且以 `Mixin` 结尾的类名 → 失败。

**NS3-T04。** `WorkflowRuntime.__mro__` 的名字集必须包含 `WorkflowCoreMixin`、`WorkflowOutcomeMixin`、`WorkflowMaterializeMixin`、`WorkflowScatterMixin`、`WorkflowGatesMixin`、`WorkflowOutboxMixin`、`WorkflowRepairMixin`。

**NS3-T05。** `IntakePipeline.__mro__` 包含 `IntakeCoreMixin`、`IntakeAcquisitionMixin`、`IntakeIndexRebuildMixin`、`IntakeCleanPreflightMixin`、`IntakeAcceptanceMixin`、`IntakeGenerationMixin`、`IntakeVectorPublishMixin`、`ProcessStageHandler`。

**NS3-T06。** 扫描 `src/` `api/` 的 `ClassDef` 名 ∈ `{TxHandler, TransactionalCommand}` → 失败。

**NS3-T07。** `pool_kind("lsrag.structurize")` / `lsrag.construct` / `lsrag.transcribe_markdown` 仍为 `generate`（沿用 `test_dispatch_policy.py`）。

**NS3-T08。** 现有 architecture 服务边界测试继续 PASS；P2/P3 新包纳入同一扫描。

**NS3-T10。** 分别省略 `clean_text`、`layered_candidate`、`granularity_set` 调 binder。期望 `MkbError`，码与今日 Mixin 一致。

**NS3-T11。** `granularity_set=(1,2)`（无 g0）→ `STRUCTURE_PROFILE_INVALID`。

**NS3-T12。** 用 `test_lsrag_compiler.py:_compiled` 同款最小正文 + 合法 layered JSON。服务 `admit` 的 `structure_payload` / `projection_digest` 必须等于直调 compiler 的结果。

**NS3-T13。** candidate 缺省；或 summary 非 null 进入 S06 admit。期望 `STRUCTURE_CANDIDATE_MISSING` 或 `STRUCTURE_SUMMARY_INVALID`（与 compiler/layered_content 一致）。

**NS3-T14。** 对 `src/services/lsrag_structurize/` 跑与 `:356` 相同的 import 规则。

**NS3-T15。** 组装最小 `IntakePipeline`（stub CLI、无 live）。预置 `layered_content_candidate`。跑 `_structurize`。期望返回 material 含 structure/projection/validation 三成员；callback 可在测试事务里执行且写得动 invocation 或至少不抛 `REGISTRY_NOT_FOUND`（夹具需 seed schema 行，对照今日 cli 测）。

**NS3-T16。** `dispatch_pool=local-inference` 且注入 fake facade。断言 facade 被调用、`LsragStructurizeService.admit` 收到的 candidate 来自 facade 输出。

**NS3-T17。** `dispatch_pool=non-interactive` + `DeterministicNs1Stub`。断言 CLI 被调用一次，服务收到 stub candidate。

**NS3-T18–T20。** 原文件原断言，0 改。

**NS3-T21。** 同一输入下服务产出的 `structure_document_digest` 等于 `test_lsrag_compiler.py:35` 路径。

**NS3-T22。** `rg adopt_layered_json_with_report src/runtime/intake/generation_construct.py` 0 命中。

**NS3-T23。** 现有 NS1 e2e 金样 succeeded。

**NS3-T24 / T25。** T03 重跑；AST 确认 `dispatch["lsrag.structurize"]` 仍绑定 `_structurize`。

**NS3-T30。** 把 T12 的 structure/projection payload 交给 reconstruct。期望通过。

**NS3-T31。** 把 construction bytes 改一个字节。期望 `CONSTRUCT_TO_VECTORIZE_GATE`。

**NS3-T32 / T33。** 与 compiler `:175` / `:120` 同场景，经服务调用。

**NS3-T34。** metadata_refresh：提供冻结 structure/projection + headers。服务 admit 不要求新的 C 摘要运输。

**NS3-T35。** `rg _complete_construct_summaries src/runtime/intake/generation_construct.py` 仍有定义；`src/services/lsrag_construct` 无 `claude_cli` / `InferenceFacade` 字符串。

**NS3-T36。** `rg "compiler.construct\(" src/runtime/intake/generation_construct.py` 0 命中。

**NS3-T37–T38。** 走完 construct handler，三成员 artifact 仍在。

**NS3-T39 / T40。** 原 `test_dispatch_generation.py` 两条，0 改。

**NS3-T41–T43。** 原测 0 改。

**NS3-T45。** binder 对 `construct_mode=metadata_refresh` 不要求 `layered_content_constructed`；`full_construct` 要求 summaries 来源字段。

**NS3-T46。** 对照 adopt 测：改 original 再 construct → `CONSTRUCT_KERNEL_ORIGINAL_MUTATION`。

**NS3-T47。** 无 full_valid 不得通过 gate（既有断言）。

**NS3-T48。** NS1 e2e + 整个 P2 pytest 文件列表。

**NS3-T50。** 单测 import 公开名。

**NS3-T51–T53。** 原测。

**NS3-T54 / T58。** 路径存在性。

**NS3-T55。** architecture 扫到新包。

**NS3-T56。** 两服务源码只 from `src.services.lsrag_compiler` 导入 `__all__` 内名字，不 from `.adopt` 等私有模块（允许 compiler 包内部互引）。

**NS3-T57。** `parse_structure_payload(structure_payload(doc))` 字段等价。

**NS3-T60–T66。** 见跑法。

**NS3-T67。** S06/S07 指定行出现「已落地」且不改 Truth 表编号。

**NS3-T68 / T69。** closure 文件；`rg` closure 与 deferred ledger 无 `D-MEGA`、无「>500 减少」。

**NS3-T70 / T71。** NS2 短途全文件。

**NS3-T72–T75。** 终态守卫 + 无新路由 + 服务无 HTTP。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| digest 漂移 | 服务重写 adopt/construct 会导致金样全红 | `high` | 只 wrap，禁止复制算法 |
| salvage 被「顺手」搬走 | services 一旦 import CLI 即架构红 + 套餐攻击面失控 | `high` | T35/T39；P3 工作内容写死留下 |
| 同文件串行冲突 | P2/P3 都改 `generation_construct.py` | `high` | 禁止并行；P2 绿才开 P3 |
| compiler 包切换窗口 | `.py` 与目录不能并存 | `medium` | 同一 commit 完成 P4-01 |
| 守卫误伤既有 Mixin | T03 过宽 | `medium` | 白名单开工日已有类名 |
| 把 retrieval Mixin 包当样板 | 新服务再堆 Mixin | `medium` | 对标 `dispatch.py` 不是 `RetrievalService` |
| NS1 e2e 夹具脆 | handler 签名微变导致出闸红 | `medium` | 不改 `_structurize`/`_construct` 签名 |
| 文档写成行数胜利 | 违背业主指令 | `low` | T69 审 closure |
| VF V11 | turso 读库 I/O | `low` | 甩锅 NS1；不挡 executed |

### 9.2 约束与前提

- **技术前提**：无 DDL；Process 八态不扩；`ProcessCommand`/`ProcessOutcome` 不改字段。
- **运行时前提**：与 NS2 相同（单库、三池、stub CLI 可跑 e2e）。
- **组织协作前提**：业主接受「本 AP 不是行数治理」；S04 TX 另开。
- **上线 / 合并前提**：每 Phase 独立可合并；P4 必须单 commit 完成包切换。无需 migration 顺序。

### 9.3 文档同步要求

- 需要同步更新的设计文档：`S06-lsrag-structurizer.md` §4.1 一句；`S07-lsrag-constructor.md` §4.1 一句
- 需要同步更新的说明文档 / README：无
- 需要同步更新的测试说明：本 AP §8 即测试说明；closure 回引
- **禁止** 更新：`deferred-items-ledger.md` 增加 `D-MEGA-*`；Gemini eval 升格为 charter

### 9.4 完成后的预期状态

1. `lsrag.structurize` / `lsrag.construct` 的叶算法分别住在 `src/services/lsrag_structurize/` 与 `src/services/lsrag_construct/`，均可无 DB/无 LLM 单测。
2. `IntakeGenerationConstructMixin` 仍存在，只负责通道、salvage、CLI/live I/O、promote 与 TX callback；`_transcribe_markdown` 仍在 Mixin。
3. `src/services/lsrag_compiler` 是包，公开 import 与 digest 配方不变。
4. `WorkflowRuntime` / `IntakePipeline` MRO、NS2 三池与 salvage 合同、S03 工作流定义文件均未改。
5. architecture 守卫使 YAML 工作流、contracts IR 倾倒、新 S06/S07 Mixin、TxHandler 无法静默合入。
6. closure 以能力边界与测试四元组收口，不以行数榜收口。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

### 10.1 收口硬闸

所有 `mega + soak + 退出层` 测试项必须 **PASS 且四元组证据齐全**：

1. NS1 金样仍 succeeded（`NS3-T60` / `NS3-T23` / `NS3-T48`）。
2. NS2 四车道与 soak 不回归（`NS3-T61` / `NS3-T63` / `NS3-T71`）。
3. generation 成员合同仍立（`NS3-T62` / `NS3-T42`）。
4. 两叶服务无 I/O，salvage 仍在 Mixin，`low` 不可升 NI（`NS3-T14` / `NS3-T35` / `NS3-T39` / `NS3-T75`）。
5. 错误拆法守卫终态仍绿（`NS3-T01–T06` / `NS3-T65` / `NS3-T72` / `NS3-T73`）。
6. compiler 公开 import 与金样 0 差（`NS3-T50–T53` / `NS3-T18`）。
7. closure 诚实且非 LOC（`NS3-T68` / `NS3-T69`）。

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| 错误拆法进不了 CI | P1-01 | NS3-T01–T06 T08 | commit + test + run-time | `未观察` |
| Mixin 根与 generate keys 冻结 | P1-02 | NS3-T04 T05 T07 T73 | commit + test + run-time | `未观察` |
| S06 服务无 I/O 且 digest 一致 | P2-01 P2-02 | NS3-T10–T22 T24 T25 | commit + test + run-time | `未观察` |
| P2 出闸 NS1 | P2-03 | NS3-T23 | commit + test + run-time | `未观察` |
| S07 服务再证/construct 正确 | P3-01 | NS3-T30–T33 T45 T46 | commit + test + run-time | `未观察` |
| salvage/I/O 仍在 Mixin | P3-02 | NS3-T35 T36 T39 T40 | commit + test + run-time | `未观察` |
| P3 出闸 + P2 不回退 | P3-03 | NS3-T41–T44 T47 T48 | commit + test + run-time | `未观察` |
| compiler 包公开面 0 差 | P4-01 P4-02 | NS3-T50–T58 | commit + test + run-time | `未观察` |
| 产品金样与 NS2 调度 | P5-01 | NS3-T60–T66 T70 T71 | commit + test + run-time | `未观察` |
| 文档与诚实 closure | P5-02 P5-03 | NS3-T67–T69 T72 T74 T75 | commit + 人工检 + test | `未观察` |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | S06/S07 叶服务落地；Mixin 为适配器；compiler 包公开符号不变；NS2 调度/salvage 0 差 |
| 测试 | §8 测试台账全 PASS（退出硬闸项四元组齐全）；每 Phase 出闸测在进入下一 Phase 前已绿 |
| 文档 | S06/S07 各一句路径回填；closure 存在且禁止 LOC 胜利句 |
| 风险收敛 | digest、salvage、包切换三项高风险均有对应 Test-ID；无新攻击面 |
| 可交付性 | 无 migration；可按 Phase revert；本 AP 可标 `executed` |

### 10.4 NOT-成功识别

> 任一退出硬闸测试 `degraded / 未观察` ⇒ **不得标 `executed`**；按 closure 五态如实归类 + handoff，不 silent overclaim。

下列情形即使测试绿也 **不得** 标成功：

- 用新 intake Mixin 或 YAML 工作流「完成」拆分。
- closure 以「>1000 行归零」为完成句。
- P3 把 salvage 放进 services 但靠 mock 把 T08 藏过去。
- P4 改了 digest 配方却只改测试期望。

---

## 11. 执行日志回填

> 执行者：`Grok`
> 执行时间：`2026-08-15`
> 文档状态：`draft → executing`
> 模板：`.adocs/code-execution-log.md`

### 11.1 逐工作项状态

| 工作项 | 状态 | 实际落点（file:line） | 备注 |
|--------|------|------------------------|------|
| P1-01 | `✅ done` | `tests/domain/test_architecture.py` NS3 守卫 | YAML / contracts models / 新 Mixin / TxHandler |
| P1-02 | `✅ done` | 同文件 T04/T05/T07 | MRO 与 generate keys 源码冻结 |
| P2-01 | `✅ done` | `src/services/lsrag_structurize/{binder,admit,service}.py` | 无 I/O；wrap compiler |
| P2-02 | `✅ done` | `generation_construct.py` `_structurize` | 改调 `LsragStructurizeService.admit` |
| P2-03 | `✅ done` | `tests/unit/test_lsrag_structurize_service.py` | T10–T25 + NS1 e2e 出闸 |
| P3-01 | `✅ done` | `src/services/lsrag_construct/{binder,reconstruct,admit,service}.py` | 再证 + construct wrap |
| P3-02 | `✅ done` | `generation_construct.py` / `generation_artifacts.py` | 无裸 `compiler.construct(`；salvage 留下 |
| P3-03 | `✅ done` | `tests/unit/test_lsrag_construct_service.py` | P3 短途 + NS1/generation e2e |
| P4-01 | `✅ done` | `src/services/lsrag_compiler/` 包；删除单文件 | 公开 import 0 差 |
| P4-02 | `✅ done` | `tests/unit/test_lsrag_compiler_package.py` | 金样 + 包面测试 |

### 11.2 时序执行日志

| 时点 | 步骤 | 决策 / 产出 |
|------|------|-------------|
| P1-T0 | 拉取 architecture / runtime.py / pipeline.py / intake Mixin 名单 | 守卫用 AST，不 import 应用模块 |
| P1-T1 | 落地 NS3-T01–T07 | T03 初版扫到 dataclass，收窄为 `*Mixin` |
| P1-T2 | `uv run pytest tests/domain/test_architecture.py tests/unit/test_dispatch_policy.py` | PASS |
| P2-T0 | 拉取 `_structurize` / compiler adopt / artifacts promote | 保持 normalize→adopt 双步 |
| P2-T1 | 新建 `lsrag_structurize` + 改 Mixin | Mixin 不再出现 `adopt_layered_json_with_report` |
| P2-T2 | P2 短途 + `test_ns1_pipeline.py` | 短途 45 passed；NS1 e2e 1 passed |
| P3-T0 | 拉取 `_construct` / reconstruct / `compiler.construct` | I/O 与 salvage 留下 |
| P3-T1 | 新建 `lsrag_construct` 并接线 | Mixin 无 `compiler.construct(` |
| P3-T2 | P3 短途 + NS1 + generation e2e | 短途全绿；e2e 2 passed |

- **Phase 1 偏差**：T04/T05 不用 `WorkflowRuntime.__mro__` 运行时 import，改 AST 读基类（substrate-fit：architecture 测试禁止拉应用依赖）。
- **Phase 2 偏差**：无产品语义偏差；binder 对缺 candidate 用 409，与 Mixin `_layered_state_candidate` 对齐。
- **阻塞与处理**：无。
- **测试发现**：P1 23 passed；P2 短途 45 passed；NS1 e2e 1 passed。
