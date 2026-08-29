# Nano-Agent 行动计划

> 服务业务簇: `MKB / new-harvest / intake-four-channel-live`
> 计划对象: `kind-family 图 + registered selected-output CONTROL + kind-only resolver + old-pin compat`
> 类型: `upgrade`
> 作者: `Grok workflow new-harvest-nh1-nh5-action-plans`
> 时间: `2026-08-29`
> 文件位置: `src/contracts/workflow/models.py`；`src/runtime/workflow/runtime_materialize.py`；`src/runtime/workflow/runtime_core.py`；`src/runtime/workflow/runtime_scatter.py`；`src/runtime/workflow/helpers.py`；`src/workflows/lsrag_definition.py`；`src/workflows/builtin_lsrag.py`；`src/workflows/builtin_scatter.py`；`src/services/workflow_registry.py`；`src/services/config_snapshots.py`；`src/runtime/intake/core.py`；`api/app.py`；`src/contracts/api/models.py`；`tests/unit/test_nh2_kind_only_resolver.py`；`tests/unit/test_nh2_representation_guards.py`；`tests/unit/test_nh2_workflow_compiler.py`；`tests/unit/test_workflow_registry.py`；`tests/unit/test_workflow_revision_compatibility.py`；`tests/integration/test_nh2_selected_output_control.py`；`tests/integration/test_nh2_legal_edges_reachable.py`；`tests/domain/test_nh2_architecture_scan.py`
> 上游前序 / closure:
> - `docs/plan/new-harvest/AP-NH1-foundation-contracts-and-proof-baseline.md`（`NH1-T04` selected-output CONTROL 切片 PASS；任一承重 spike 失败则 STOP/reopen，本 AP 不得开工）
> 下游交接:
> - `docs/plan/new-harvest/AP-NH3-representation-history-and-s05-binding.md`（消费本 AP 已登记谓词与 kind 图；生产 history 行与 actual S05 seal）
> - 并行窗：`AP-NH4` / `AP-NH5`（本 AP 不等它们；它们也不等本 AP）
> - 后继 join：`AP-NH7` 激活 10+3 前须本 AP kind-only + 合法边可达
> 关联设计 / 调研文档:
> - `docs/eval/new-harvest/final-execution-plan.md` v1.0 `frozen` §7.2（唯一执行基线）
> - `docs/eval/new-harvest/reference-anchor/assessment-analysis-01-workflow-graph-and-kind-family.md`
> - `docs/eval/new-harvest/reference-anchor/assessment-analysis-03-representation-and-reacquisition.md`（guard 消费 fact；本 AP 只声明谓词）
> 冻结决策来源:
> - `docs/eval/new-harvest/pre-charter-qna.md` v1.0：Q11/Q12/Q18/Q22 → `T-O-391` / `T-O-392` / `T-O-398` / `T-O-402`（只读引用；本 action-plan 不填写 Q/A）
> - `docs/eval/new-harvest/pre-initial-planning-qna.md` v0.5：Q4/Q7/Q8 → `T-O-384` / `T-O-387` / `T-O-388`；围栏 `T-O-377` / `T-O-379` / `T-O-382`
> grounding 来源:
> - `docs/eval/new-harvest/final-execution-plan.md` v1.0 §7.2 台账 A/B/C/D + HEAD `1221aa1` 实测 + RA01/RA03
> 关联 reference-anchor:
> - [`assessment-analysis-01-workflow-graph-and-kind-family.md`](../../eval/new-harvest/reference-anchor/assessment-analysis-01-workflow-graph-and-kind-family.md)（主面）
> - [`assessment-analysis-03-representation-and-reacquisition.md`](../../eval/new-harvest/reference-anchor/assessment-analysis-03-representation-and-reacquisition.md)（邻面：fact 权威；本 AP 只消费形状）
> 文档状态: `draft`

**台账 ID 区间（final §11.A / §7.2）**：`NH2-01..08` / `NH2-A01..06` / `NH2-T01..07`。禁止重编号、合并或删除这些 ID。

---

## 0. 执行背景与目标

HEAD `1221aa1` 已有可复用的七表无环编译器、eq-only 登记守卫、caller 面无 `workflow_key` 字段、以及按 `compiled_digest` pin 的 compat revision。它**不能**在不复制 publication tail 的前提下表达 selected-output merge，也**没有** kind 家族图：13 张 profile 线性图由 `_source_profile_workflow` 三槽替换复制而来，`acquisition_mode` / `media_type` 仍参与选 7 个 public key，6 张 live 图 caller 选不中（`T-R-NH-01` / `T-R-NH-03`）。

冻结 Truth 要求：选图键只剩四类 `source_kind`（三张 single-root + scatter 对）；同一 immutable revision 预声明该 kind 全部合法 acquire/decode/clean 边；用 registered selected-output CONTROL 把多候选投影成一份共享 tail；representation 谓词 eq-only、缺键/unknown fail-closed；旧 pin Execution 按旧 digest 跑完。NH1 必须先证明 CONTROL 切片可行（`NH1-T04`）；本 AP 把该切片升级为生产图代数，并完成 kind family、resolver 与 compat。本 AP **不等** NH3 的 actual 列与 history 行——只声明守卫谓词与投影键。

- **服务业务簇**：`MKB / new-harvest / intake-four-channel-live`
- **计划对象**：kind-family 图 + registered selected-output CONTROL + kind-only resolver + old-pin compat
- **本次计划解决的问题**：
  - 七表只有 `human_review_gate` / `scatter_children_join` 两种 CONTROL，单 input 单 binding，无法 XOR 汇合多 clean 候选而不复制 tail
  - 选图仍是 7 public profile key（mode/media 参与），6 张 live 图不可达，与 `T-O-387` 冲突
  - 无 representation-aware guard；factory 每图固定三槽，无法画同 revision 多 acquire 正向边
- **本次计划的直接产出**：
  - 生产级 `selected-output` CONTROL（optional candidate ports、exactly-one、登记 fallback 进 compiled digest）
  - 三张 single-root kind 图 + 保持独立的 scatter root/child；一份共享 publication/generation tail 源
  - public `resolve_for_source` 只认 `source_kind`；旧 key 保持 enabled-unselected 供 pin 查找
  - L1/L2 测试台账 `NH2-T01..T07` 与 evidence pack 目录约定
- **本计划不重新讨论的设计结论**：
  - v1 使用 registered selected-output CONTROL，候选端口 optional，只投影 durable selection（来源：Q11 / `T-O-391`）
  - 选图键 = 四 `source_kind`；mode/media 不再选图（来源：Q7 / `T-O-387`）
  - 有界 Workflow substrate 留在 NH1–NH3；禁 JOIN/DSL/自由表达式；NH1 证伪即 STOP，禁 duplication（来源：Q18 / `T-O-398`）
  - `main_text_presence` 三态 eq-only；仅 `absent` 走已声明 browser 边；`unknown` fail-closed（来源：Q22 / `T-O-402`）
  - caller 禁 `workflow_key`；禁 `action_branch`（来源：`T-O-379` / `T-O-377`）

---

## 1. 执行综述

### 1.1 总体执行方式

本 AP 采用 **「先代数后身份、先声明后停暗通道、先共存后扫描」**：Phase 1 把 NH1-T04 的 CONTROL 切片升级进七表运行时（不改 unique-binding 围栏）；Phase 2 只登记 representation 谓词与投影键（不生产 history）；Phase 3 用共享 tail 源重建 3+scatter kind 图并预声明多边；Phase 4 把 public resolver 改成 kind-only 并拆除三槽 factory / 暗 dispatch；Phase 5 保证旧 pin 与新图共存，再用架构扫描锁红线。不重开 Q11/Q18 选项，不把 Temporal/CWL/Airflow 写成落地栈。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | CONTROL 代数 | `L` | 生产 `SelectedOutputControl`：optional ports、exactly-one、零/双 fail-loud | NH1-T04 PASS |
| Phase 2 | representation guard | `M` | 登记三态/媒体谓词，eq-only，缺键/unknown fail-closed | Phase 1 |
| Phase 3 | kind family 定义 | `XL` | 3 single + scatter；共享 tail；多 acquire/decode/clean 前向边 | Phase 1–2 |
| Phase 4 | resolver + 停暗 dispatch | `L` | kind-only public resolve；停三槽 factory；未声明 process 409 | Phase 3 |
| Phase 5 | compat + 红线扫描 | `L` | old/new 共存；architecture scan EXIT 0 | Phase 4；kind 激活前完成 compat review |

> 说明：上表 `规模` 是描述性提示，不是开工闸，也不改变本模板段落取舍。

### 1.3 Phase 说明

1. **Phase 1 — CONTROL 代数**
   - **核心目标**：把 selected-output 做成第三个 registered CONTROL，保持「每 required input 一 binding」。
   - **为什么先做**：kind 图的多 clean 边若无处汇合，只能复制 tail（`FG-NH-09`）；NH1 只证明切片，生产分发仍只有两种 CONTROL（`runtime_materialize.py:505-514`）。
2. **Phase 2 — representation guard**
   - **核心目标**：让图能消费 `main_text_presence` 等 eq 谓词；本 AP 不写 history 行。
   - **为什么放在这里**：再获取边（Phase 3）需要已登记守卫，否则 static→browser 只能 handler 暗升。
3. **Phase 3 — kind family 定义**
   - **核心目标**：三张 kind 图引用同一 tail 源；scatter 保持 root/child；合法边全部预声明且无环。
   - **为什么放在这里**：代数与谓词齐备后才能停 13 profile factory，而不先把 duplication 写成终态。
4. **Phase 4 — resolver + 停暗 dispatch**
   - **核心目标**：public 选图只认 `source_kind`；图外 `process_key` 409。
   - **为什么放在这里**：先有 kind 图可解析，再切入口；否则会把流量切到空 registry。
5. **Phase 5 — compat + 红线扫描**
   - **核心目标**：旧 `compiled_digest` 事件序列不变；新 Task 不解析旧 selector key；扫描零 `workflow_key` 入参 / 零 `action_branch` / 零自由表达式 / tail 源唯一。
   - **为什么放在这里**：kind 定义激活前必须完成 compat review（台账 D DoD 硬闸）；扫描是退出门。

### 1.4 执行策略说明

- **执行顺序原则**：先扩展 CONTROL/guard 编译期+运行时（不破坏 unique binding），再换 identity 与 resolver；compat 定义与新图同一 PR 可注册，但 **public 切流发生在 Phase 4 且以 Phase 5 review 为激活闸**。
- **风险控制原则**：`R-F01` 若 NH1 CONTROL 切片失败 → 本 AP 不开工、不改去 duplication。`R-F04` 禁止从 `_active_workflow_keys` 或 registry 删除仍可能被 pin 的旧 key。`R-F10` 三 kind 必须引用同一 tail 源模块，禁止 per-strategy deepcopy。
- **测试推进原则**：每个 Phase 先 L1 编译器/守卫/扫描，再 L2 UoW（CONTROL 投影、resolver、旧 pin 序列）。本 AP 最低层以台账 C 为准，不把 T05/T06 降成纯 unit。无 L3 default-root live、无 L4 retrieval（交 NH7/NH9）。
- **文档同步原则**：执行期同步 kind 图 identity 清册与 `M-NH-03`/`M-NH-04` 变更说明，写入 evidence pack；不改 QNA / final。
- **回滚 / 降级原则**：新 kind 图可先 register 为未切流；resolver 切换可回退到「仍加载旧 key 但不 public 选中」。禁止回退成 13 张复制图当 kind family。禁止用 `scatter_children_join` 或 `human_review_gate` 顶替 merge。

### 1.5 本次 action-plan 影响结构图

```text
AP-NH2 kind-family + selected-output CONTROL
├── Phase 1: CONTROL 代数
│   ├── src/contracts/workflow/models.py（CONTROL 登记 / optional ports / digest 信封）
│   └── src/runtime/workflow/runtime_materialize.py::_enter_control_tx（第三 CONTROL；禁 scatter wait）
├── Phase 2: representation guard
│   ├── WorkflowGuardDefinition.predicate_type 闭集扩展（仍 eq-only）
│   └── _guard_matches + _typed_route_context_tx（投影键；不生产 history）
├── Phase 3: kind family 定义
│   ├── src/workflows 三张 single-root kind 图 + scatter 保持
│   ├── 共享 publication/generation tail 源（禁止 _source_profile_workflow 复制）
│   └── 多 acquire/decode/clean 前向边 → CONTROL → 单 tail
├── Phase 4: resolver + 停暗 dispatch
│   ├── workflow_registry.resolve_for_source（kind-only）
│   ├── config_snapshots._source_profile（不再用 mode/media 选 key）
│   └── intake/core.py process_key 必须出现在 pinned revision
└── Phase 5: compat + 红线
    ├── runtime_core._assert_execution_binding（compiled_digest pin + enabled-unselected 旧 key）
    ├── builtin compatibility_definitions + retirement telemetry
    └── tests/domain/test_nh2_architecture_scan.py（T-O-377/379/398）
```

---

## 2. In-Scope / Out-of-Scope

> 设计边界来自冻结 QNA 与 final §4；本节只说明本轮执行做什么、不做什么。范围主面 = `S-NH-F2`。

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** 生产登记 `selected-output` merge CONTROL：optional candidate ports、durable selection 投影、exactly-one、零/双 fail-loud、登记 fallback 进入 compiled digest（`S-NH-F2` / `NH2-01` / `T-O-391`）
- **[S2]** 登记 representation 谓词（至少 `main_text_presence` 三态）与 route projection；eq-only；缺键/未知 fail-closed（`NH2-02` / `T-O-392` / `T-O-402`）
- **[S3]** 三张 single-root kind 图 + scatter root/child；共享一份 publication/generation tail 源；同 revision 多 acquire/decode/clean 前向边接入 CONTROL（`NH2-03` / `NH2-04` / `T-O-387` / `T-O-388`）
- **[S4]** public resolver kind-only；停三槽 factory 与图外暗 dispatch；旧 pin 共存与红线扫描（`NH2-05..08` / `T-O-379` / `T-O-398`）

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** 第五 source kind、caller `workflow_key`、`action_branch` taxonomy（`O-NH-01` / `T-O-377` / `T-O-379`）
- **[O2]** 通用 JOIN/DSL/自由表达式/动态 loader；云 OCR / CF / R2 / SMCP runtime（`O-NH-06` / `T-O-398`）
- **[O3]** actual S05 列、seal UoW、RepresentationFact/AcquireDecodeHistory 行生产（NH3 / `S-NH-F3`）；本 AP 只声明谓词
- **[O4]** live runtime 二进制与 10+3 激活（NH6 / NH7）；七意图 / campaign mega（NH8 / NH9）；cuts/g0 重开与按通道复制 tail（`O-NH-02`）
- **[O5]** existing-object new-cleaner upgrade（`O-NH-03` / `T-O-401`）；raw object GET（`O-NH-04`）；experiment 发车（`O-NH-05`）
- **[O6]** 把 `scatter_children_join` 复用成 XOR；改「每 required input 一 binding」去搞 one-of 自由 binding；`WorkflowStepKind.JOIN` 第三通道

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| selected-output CONTROL 生产化 | `in-scope` | `S-NH-F2`；`T-O-391`；NH1-T04 只证明切片 | NH1-T04 失败 → STOP，不在本 AP 换 duplication |
| kind-only resolver + 3+scatter 图 | `in-scope` | `T-O-387` / `T-O-379` | 仅新 owner Truth 可改图基数 |
| representation 谓词登记与投影 | `in-scope` | `T-O-402` / `T-O-392`；RA03 邻面消费 | 谓词字面除 `main_text_presence` 外属执行登记，不得变自由表达式 |
| history 行 / actual S05 seal | `out-of-scope` | `S-NH-F3` / NH3；本 AP 不等 actual 列 | NH3 开工条件 = 本 AP kind 图 + 谓词已登记 |
| scatter AND fan-in 语义保持 | `in-scope`（保持，不改成 merge） | `T-O-387` scatter 不并 mega；`T-O-391` 禁复用 fan-in | never（除非推翻 Q11） |
| 通用 JOIN / DSL / loader | `out-of-scope` | `O-NH-06` / `T-O-398` | 新 owner-gate；本战役不 reopen |
| caller `workflow_key` / `action_branch` | `out-of-scope` | `O-NH-01` | never |
| 10+3 live 接通 / runtime 供给 | `out-of-scope` | NH6/NH7；本 AP 只保证边在图上可达 | NH7 join 本 AP T01/T05 |
| existing-object upgrade | `out-of-scope` | `O-NH-03` / `T-O-401` | 未来须新 owner-gate |

---

## 3. 业务工作总表

> 编号列使用 final 台账 A 的 `NH2-nn`。每个工作项具备不可约三元组：`file:line` / 收口目标 / Test-ID。

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| NH2-01 | Phase 1 | SelectedOutputControl | `add` | `src/contracts/workflow/models.py:36-37,113-120,373-525`；`src/runtime/workflow/runtime_materialize.py:222-232,435-441,505-514`；`src/runtime/workflow/helpers.py:30-47` | CONTROL 对 optional candidate 做 exactly-one 投影；零/双 fail-loud；未 materialize 不等待；fallback/version 进入 compiled digest；unique-binding 围栏保持 | `NH2-T02` | `high` |
| NH2-02 | Phase 2 | Representation predicates | `update` | `src/contracts/workflow/models.py:245-278`；`src/runtime/workflow/runtime_materialize.py:86-117,119-168` | 至少 `main_text_presence` 三态已登记且 eq-only；present 不走 browser 边；absent 走已声明边；unknown/缺键 fail-closed；非 eq 409；不写 history 行 | `NH2-T03` | `high` |
| NH2-03 | Phase 3 | 3 single+scatter definitions | `migrate` | `src/workflows/lsrag_definition.py:85-118,181-195,775-926,929-1070`；`src/workflows/builtin_lsrag.py:35-44`；`src/workflows/builtin_scatter.py:154-156` | public identity = 三张 single-root kind 图 + scatter 对；三 kind 的 generation/publication 子图哈希相等且同源；scatter 不并入 mega、不把 merge 塞进 fan-in | `NH2-T05` / `NH2-T07` | `high` |
| NH2-04 | Phase 3 | 多 acquire/decode/clean 边 | `add` | `src/contracts/workflow/models.py:337-340,389-432,496-497`；kind 图定义（Phase 3 新/改文件） | 合法边均为不同 `step_key`、正向、无环；每 acquire 步声明至多成功一次；候选 clean 经 CONTROL 接入共享 tail；自环/环/重复 step_key 拒注册 | `NH2-T04` / `NH2-T05` | `high` |
| NH2-05 | Phase 4 | kind-only public resolve | `update` | `src/services/workflow_registry.py:78-140`；`src/services/config_snapshots.py:138-144,492-516`；`src/contracts/api/models.py:107-178,273-297` | `resolve_for_source` 不把 `acquisition_mode`/`media_type` 当选图键；4 kind 各唯一图；未知 kind 422、缺图 503；caller 合同无 `workflow_key` | `NH2-T01` / `NH2-T05` | `high` |
| NH2-06 | Phase 4 | 停三槽 factory/暗 dispatch | `remove`/`update` | `src/workflows/lsrag_definition.py:881-926`；`src/runtime/intake/core.py:356-386`；`src/runtime/intake/clean_preflight.py:629-636` | active kind 图不再由三槽替换复制；materialize/handler 只跑 pinned revision 已声明 `process_key`；未声明 409 | `NH2-T05` / `NH2-T07` | `high` |
| NH2-07 | Phase 5 | old/new coexistence | `update` | `src/runtime/workflow/runtime_core.py:88-100,591-633`；`api/app.py:297-304`；`src/workflows/builtin_lsrag.py:40-44`；`src/workflows/lsrag_definition.py:1073-1080` | 旧 plans 仍按 `compiled_digest` 跑完；新 Task 不解析旧 selector key；未知 digest 不插 Process；retirement telemetry 可观测 | `NH2-T06` | `high` |
| NH2-08 | Phase 5 | 禁止面扫描 | `add` | `tests/domain/test_nh2_architecture_scan.py`（🆕）；对照 `src/contracts/api/models.py:107-178`；`src/contracts/workflow/models.py:245-258`；`tests/domain/test_architecture.py:1-16` | 扫描 EXIT 0：公共 API 无 `workflow_key` 入参；`src/`/`api/`/`intake/` 零 `action_branch`；guard 无自由表达式；三 kind tail 源唯一 | `NH2-T07` | `medium` |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — CONTROL 代数

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| NH2-01 | SelectedOutputControl | **净新高风险，有序子步：** a) 在 CONTROL 分发登记第三 `control_key`（沿用 NH1-04 冻结字面；若 spike 未钉则登记 `selected_output`），其 semantics/version 进入 `_compiled_workflow_digest` 信封（`helpers.py:30-47`）。b) 每个 candidate 绑到 CONTROL **不同、显式命名** 的 input port，且 `WorkflowPortDefinition.required=False`（`models.py:113-120`）；保持「每 input 一 binding」（`models.py:496-497`）与 DDL `ux_workflow_binding_slot`（`001_initial.sql:1770-1771`）。c) `_enter_control_tx`（`runtime_materialize.py:484-514`）新增分支：只读已提交 route/selection proof，**禁止重跑** `_guard_matches`。d) 计已 `SUCCEEDED` 的 candidate：0 且无登记 fallback → fail-loud；0 且有该 CONTROL 版本登记的 fallback port → 投影 fallback；1 → 投影到唯一 canonical output；≥2 → 完整性失败。e) 未 materialize 的 optional prior_output 走现成 skip（`435-441`），**不得** `status=waiting` / `waiting_reason=scatter_children`。f) **禁止**调用 `_enter_scatter_children_join_tx`（`runtime_scatter.py:24-109`）或启用 `WorkflowStepKind.JOIN` / `ALL_REQUIRED`。g) 下游 seal/tail 对 canonical output 仍一条 required binding。h) 失败路径：未知 `control_key` 仍 409 `workflow-control-unsupported`；CONTROL 自身 succeeded/failed/cancelled 终端覆盖保持编译器要求（`models.py:466-474`）。 | `models.py:36-37,113-120,373-525`；`runtime_materialize.py:222-232,435-441,505-514`；`runtime_scatter.py:24-109`；`helpers.py:30-47` | 生产 CONTROL 可注册、可 replay、可进 digest；零/一/双与未 materialize 行为与 `T-O-391` 一致 | `NH2-T02` | 见 §10.2 `merge exactly-one`；`FG-NH-09` 不得用复制图冒充 |

### 4.2 Phase 2 — representation guard

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| NH2-02 | Representation predicates | **净新/高风险，有序子步：** a) 扩展 `WorkflowGuardDefinition.predicate_type` 闭集（`models.py:249-255`）至少纳入 `main_text_presence`；`expected_value` 闭集 `{present, absent, unknown}`（`T-O-402`）。媒体/表示类谓词若登记，同样走代码闭集，不得自由字符串。b) `operator` 保持 `Literal["eq"]`（`256`）；合约拒绝 `ne/lt/in_registered_set` 等 DDL 已有但合约未开的算子（`001_initial.sql:638-640`，`NH-RA01-B11`）。c) `_guard_matches`（`86-117`）为新谓词增加 `context_key`；缺键 → `results[guard]=False` 且不选边（现成 `110-113`）。d) 扩展 `_typed_route_context_tx`（`119-168`）从 **NH1 冻结的 fact-read 接口** 投影；本 AP **不**创建 RepresentationFact 表、**不** append history（NH3）。测试用 fixture 行满足该接口。e) `unknown` 与缺键均不得命中 `expected_value=absent` 的 browser 边。f) 禁止从 Process `output_manifest` JSON、`payload_extra`、handler 内存读守卫（`T-O-392`）。g) 失败路径：未知 `predicate_type` 注册失败；runtime 未知谓词 409 `workflow-guard-unsupported`；非 eq 409。 | `models.py:245-278`；`runtime_materialize.py:86-117,119-168` | 图可声明表示边；缺事实不暗升 | `NH2-T03` | `present` 不走 browser；`absent` 走已声明边；`unknown`/缺键 fail-closed |

### 4.3 Phase 3 — kind family 定义

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| NH2-03 | 3 single+scatter definitions | **XL / 高风险，有序子步：** a) 抽出 **一份** publication/generation tail 源（自 `seal_candidate_set`/`structurize` 起的共享步骤+路由+binding，含现成 optional construct 端口 `lsrag_definition.py:181-195`），三种 single kind 图 **引用** 该源，禁止 `_source_profile_workflow` deepcopy + 三槽替换（`881-926`）作为 active factory（`FG-NH-09` / `R-F10`）。b) 建立三张 `execution_role=single_root` kind 图，identity 键为 `inline_payload` / `local_object` / `http_resource`（具体 `workflow_key` 字面属执行，须进 compiled 清册）；`registered_api` **维持** `builtin_scatter.py` root/child，不并 mega、不在 fan-in 上挂 selected-output。c) 每张 kind 图只画该 kind 合法 acquire/decode/clean 边（对照 `strategies.py:15-151` 与 `T-O-381` 矩阵；非法跨 kind 边不画）。d) 将 HEAD 6 张 unselectable（`1003-1054`：vision / doc-llm / web-llm / browser-web-llm / pdf-understanding / print-pdf）**并进**对应 kind revision 成为看得见的步骤，不再作为 public selector key。e) `BUILTIN_WORKFLOWS` / `api/app.py:297-304` additional_definitions 改为 kind 图 + scatter；旧 13 profile 定义迁入 compat/enabled-unselected（Phase 5）。f) 编译注册：无环、unique route、required process_keys 与步骤一致。g) 失败路径：跨 kind 边注册失败；tail 源分叉（三图 generation/publication 子图哈希不等）视为本项失败。 | `lsrag_definition.py:85-118,181-195,775-926,929-1070`；`builtin_lsrag.py:35-44`；`builtin_scatter.py:154-156,352-380` | public 闭集 = 3+scatter；共享 tail；6 张 hidden 图不再是「另一张可选程序」 | `NH2-T05` / `NH2-T07` | 见 §10.2 `kind-only` + `one shared tail` |
| NH2-04 | 多 acquire/decode/clean 边 | **净新/高风险，有序子步：** a) 同 kind 内每个 acquire/decode/clean 候选使用 **不同 `step_key`**（禁止自边 `models.py:389-390`）。http_resource 至少：`acquire_static`（起点）、`acquire_browser`（再获取）、`acquire_print`（再获取；capability 登记为已有 `intake.acquire.http_browser` 或 NH1 冻结的 print 字面——**本 AP 不选引擎**）。local_object 至少覆盖 pdf/text/image 的 decode 观察步与对应 clean 候选。inline 至少 inline acquire + text decode + deterministic clean。b) 边必须正向、无环（`418-432`）；再获取不得回到同一 `step_key`。c) 声明「每 acquire 步至多成功一次」：编译器拒自环/重复 `step_key`（`337-340`）；同 step 第二次成功拒绝属 NH3 history 法，本 AP 只保证图形状不提供重入边。d) 各 clean 候选 output 绑到 CONTROL optional ports，再由 canonical output 接共享 seal/tail。e) decode 步只作为观察器出口（守卫读投影），不在 handler 里暗升 browser/OCR。f) 失败路径：环/自环/重复 step_key → `WorkflowDefinition` 校验 `ValueError`，registry 拒收；try-all-acquire 边集视为非法。 | `models.py:337-340,389-432,496-497`；Phase 3 kind 图 | 合法边可编译；非法图拒注册 | `NH2-T04` / `NH2-T05` | 环/重复拒注册；合法边经 public resolve 出现在 kind revision steps 中 |

### 4.4 Phase 4 — resolver + 停暗 dispatch

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| NH2-05 | kind-only public resolve | **高风险，有序子步：** a) `resolve_for_source`（`workflow_registry.py:78-104`）对 `intake.ingest` 只认四 `source_kind`：`registered_api` → scatter root；其余三 kind → 对应 single-root kind 图。**删除** `source_profile or source_kind` 再查 `SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS`（`98-103`）的路径。b) `ConfigSnapshotService._source_profile`（`492-516`）与 `prepare`（`138-144`）不再把 `acquisition_mode`/`media_type` 映射成 workflow key；二者只作为起点 fact 进入 Execution context（供 Phase 2 守卫，不选图）。c) `TaskCreateRequest` / `SourceDescriptor`（`api/models.py:107-178,273-297`）保持无 `workflow_key` 字段。d) 分码：schema 外 kind / 非法 discriminator → 422；已知 kind 但 registry 无 enabled kind 图 → 503 `REGISTRY_NOT_FOUND`。e) 内部 `resolve_by_key` 保留给 bootstrap/compat/readiness（`122-140`），**不得**出现在 public Task 入参或 `prepare` 的 caller 可选路径。f) 失败路径：`http_resource.static` 与 `http_resource.browser` 解析到 **同一** kind `workflow_key`；`local_object.pdf` 与 `local_object.image` 同理。 | `workflow_registry.py:78-140`；`config_snapshots.py:138-144,492-516`；`api/models.py:107-178,273-297` | 4 kind 唯一选图；mode/media 改变不改 key | `NH2-T01` / `NH2-T05` | public resolver 不消费 mode/media 作为选图键 |
| NH2-06 | 停三槽 factory/暗 dispatch | **高风险，有序子步：** a) active kind 图停止调用 `_source_profile_workflow`（`881-926`）作为生成器；该函数若保留只服务历史 compat 快照，不得再产出新 active revision。b) registry / kind 图显式列出该 kind 全部 live `process_key`（与 `required_process_keys` 一致）。c) `IntakePipeline._material_for` dispatch 表（`core.py:356-386`）仍可按 `process_key` 找 handler，但 materialize 前校验 `command.process_key` ∈ pinned revision 已声明步骤；handler 不得改派未声明工人。d) `clean_preflight.py:629-636` 禁止再用 descriptor `acquisition_mode` 反推「期望 acquire capability」去否定已声明再获取路径（完整 preflight 诚实性交 NH3，本项至少：不得因起点 mode 把已声明 browser/print 步打成非法）。e) 未声明 `process_key` → 409（新码或沿用 `PIPELINE_CAPABILITY_UNSUPPORTED` / `workflow-*`，须机器可读且测试锁码）。f) 失败路径：测试插入图外 `clean.extract.vision` 到 inline kind Execution → 409 且零该 Process 成功行。 | `lsrag_definition.py:881-926`；`core.py:356-386`；`clean_preflight.py:629-636` | 暗升/暗选工人关闭 | `NH2-T05` / `NH2-T07` | 图声明 = 唯一可跑 process 闭集 |

### 4.5 Phase 5 — compat + 红线扫描

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| NH2-07 | old/new coexistence | **高风险，有序子步：** a) 旧 13 profile 定义与既有 `BUILTIN_EXECUTION_COMPATIBILITY_WORKFLOWS`（`builtin_lsrag.py:40-44`；`lsrag_definition.py:1073-1080`）继续注入 `WorkflowRuntime(..., compatibility_definitions=...)`（`api/app.py:297-304`）。b) 旧 `workflow_key` 保持 **enabled-unselected**：仍进入 `_active_workflow_keys`（`runtime_core.py:88-95`），避免 `_assert_execution_binding` 因 `workflow_key not in self._active_workflow_keys` 对 in-flight 409（`608-614`，`NH-RA01-B08`）。**不要**把旧 key 塌缩进新 kind key 后删除旧 identity。c) runtime 只按 Execution 存储的 `compiled_digest` 取 plan（`591-621`）；未知 digest → `workflow-compiled-plan-unavailable` 且 **不插** Process（现成负例 `test_workflow_revision_compatibility.py:175-192`）。d) 新 Task 走 kind-only resolver，不得解析 `http_resource.static` 等旧 selector key。e) retirement telemetry：当 pin 命中旧 key/digest 时记机器可读计数/事件（不在本 AP 做有界退役——那是 NH8-07 / `M-NH-04` 后半）。f) 失败路径：激活 kind 图后跑旧 v1 序列，process_key 顺序与 `test_v2_runtime_materializes_and_completes_unstarted_v1_execution`（`:106-168`）同类断言一致。 | `runtime_core.py:88-100,591-633`；`api/app.py:297-304`；`builtin_lsrag.py:40-44` | 旧 pin 事件序列不变；新 Task kind-only | `NH2-T06` | 见 §10.2 `compat`；`R-F04` |
| NH2-08 | 禁止面扫描 | 新增 domain 扫描（AST/`rg` 风格，参照 `tests/domain/test_architecture.py:1-16` 不 import 应用）：a) `api/` + `src/contracts/api/` 请求模型无 `workflow_key` 字段。b) `src/`、`api/`、`intake/` 生产代码零 `action_branch` 标识符。c) `WorkflowGuardDefinition.operator` 仅为 `eq`；测试注入 JSONata/JS/SQL/FEEL/`when` 字符串作 predicate 必须注册失败。d) 三 kind 图 generation/publication 子图哈希相等且 tail 源模块唯一（import 同一符号，而不是三份拷贝）。e) CONTROL 闭集不含把 `scatter_children_join` 当作 selected-output 的别名。 | 🆕 `tests/domain/test_nh2_architecture_scan.py`；对照 `models.py:245-258`；`api/models.py:107-178` | 扫描 EXIT 0 | `NH2-T07` | 见 §10.2 `redlines` |

---

## 5. Phase 详情

### 5.1 Phase 1 — CONTROL 代数

- **Phase 目标**：把 `T-O-391` 的 selected-output CONTROL 从 NH1 切片升级为生产原语，且不打开 one-of binding 或 scatter wait。
- **本 Phase 对应编号**：`NH2-01`
- **本 Phase 新增文件**：CONTROL 生产实现可落在 `runtime_materialize.py` 新方法（例如 `_enter_selected_output_tx`）；若 NH1-04 已给出模块，则升级该模块而非平行复制。
- **本 Phase 修改文件**：`src/contracts/workflow/models.py`（CONTROL 版本进入可编译信封所需的声明，不改 unique-binding）；`src/runtime/workflow/runtime_materialize.py:484-514`；`src/runtime/workflow/helpers.py:30-47`（digest 信封含 CONTROL semantics）。
- **本 Phase 删除文件**：无
- **具体功能预期**：
  1. 注册含两个 optional candidate port、一个 required canonical output 的 CONTROL 步骤时，`WorkflowDefinition` 校验通过；同一 candidate port 两条 binding 仍 `ValueError`（`496-497`）。
  2. 仅一条 candidate Process `SUCCEEDED` 时，下游 required 输入拿到该 prior_output 的 ref/digest，另一 candidate 无 Process 行或非成功。
  3. 零条成功且无登记 fallback → Execution/CONTROL fail-loud，**不**进入 `waiting`；零条成功且 CONTROL 版本声明 fallback → 投影 fallback，且 fallback 身份出现在 compiled digest 材料中。
  4. 两条成功 → 完整性失败（CWL `the_only_non_null` 失败法的重映射，不引入 CWL 引擎）。
  5. 未 materialize 的 optional 不阻塞（沿用 `435-441`）；CONTROL **不得**调用 `runtime_scatter.py:24-109` 的 collect-all wait。
  6. 失败/降级：未知 `control_key` → 409 `workflow-control-unsupported`；CONTROL 缺 succeeded/failed/cancelled 路由 → 编译失败。
- **对应测试台账项**：`NH2-T02`
- **收口标准**：exactly-one 套件 PASS；unique-binding 围栏测试仍红（故意双 binding 被拒）。
- **本 Phase 风险提醒**：`R-F01` — 若必须改 DDL unique 才能工作，视为 chosen shape 被证伪，STOP 回 Q11，而不是「顺手 one-of」。

### 5.2 Phase 2 — representation guard

- **Phase 目标**：图能 eq-only 消费 `main_text_presence`；缺事实 fail-closed；不生产 NH3 行。
- **本 Phase 对应编号**：`NH2-02`
- **本 Phase 新增 / 修改 / 删除文件**：修改 `models.py:245-278`、`runtime_materialize.py:86-168`；无删除。
- **具体功能预期**：
  1. `main_text_presence=present` 时，声明 `eq absent` 的 browser 再获取路由不入选。
  2. `=absent` 时，已声明 browser 边入选（若优先级/其它守卫允许）。
  3. `=unknown` 或 context 缺键 → 不选该边，不暗升。
  4. `operator != eq` 的定义无法通过 `WorkflowGuardDefinition`。
  5. 未知 `predicate_type` 无法注册；runtime 遇到未映射谓词 409。
  6. 投影只走 fact-read 接口；测试若把事实只放进 Process output JSON，守卫必须仍 fail-closed。
- **对应测试台账项**：`NH2-T03`
- **收口标准**：T03 五态（present/absent/unknown/missing/non-eq）全覆盖。
- **本 Phase 风险提醒**：不要把 LLM/quality score 登记为谓词（`T-O-402`）。不要提前创建 history 表冒充 NH3。

### 5.3 Phase 3 — kind family 定义

- **Phase 目标**：3+scatter 成为新 Task 的唯一 public 选图闭集；多边无环接入 CONTROL；一份 tail 源。
- **本 Phase 对应编号**：`NH2-03` / `NH2-04`
- **本 Phase 新增文件**：共享 tail 源模块（例如 `src/workflows/lsrag_shared_tail.py` 或等价单一符号）；三张 kind 图定义模块（可仍住 `lsrag_definition.py`，但必须引用单一 tail 源）。
- **本 Phase 修改文件**：`lsrag_definition.py:85-118,181-195,775-1070`；`builtin_lsrag.py:35-44`；`api/app.py:297-304` additional_definitions。
- **本 Phase 删除文件**：不物理删除旧 13 定义（Phase 5 需要）；停止把它们当作 active public factory。
- **具体功能预期**：
  1. bootstrap 后 public ingest 可解析的 single-root identity 数为 3，加上 scatter root（+ child 非 public ingest 选图）。
  2. 三 kind 图从共享 tail 源展开后，generation/publication 子图哈希相等。
  3. `http_resource` 图 steps 同时包含 static/browser/print 相关 acquire 步与 web/pdf 清洁候选；`local_object` 同时包含 pdf/doc/image 相关 decode/clean 候选。
  4. 原 unselectable 6 张的 `process_key` 出现在对应 kind 图 steps 中，但其旧 `workflow_key` 不能被 `resolve_for_source` 选中。
  5. 自环、互环、重复 `step_key` 的定义 `model_validate` 失败。
  6. scatter root 仍使用 `scatter_children_join`（`builtin_scatter.py:154-156`），该 CONTROL 不出现在 single-root kind 图的 merge 位置。
  7. 失败：把 13 张克隆图改名当 kind family → T07 tail 唯一性失败。
- **对应测试台账项**：`NH2-T04` / `NH2-T05` / `NH2-T07`
- **收口标准**：合法边 caller 可达；共享 tail 谓词成立。
- **本 Phase 风险提醒**：`R-F10` tail 分叉；`NH-RA01-B08` 过早塌缩 key。

### 5.4 Phase 4 — resolver + 停暗 dispatch

- **Phase 目标**：入口只认 kind；图外工人 409。
- **本 Phase 对应编号**：`NH2-05` / `NH2-06`
- **本 Phase 新增 / 修改 / 删除文件**：修改 `workflow_registry.py:78-104`、`config_snapshots.py:138-144,492-516`、`core.py:356-386`、`clean_preflight.py:629-636`；`_source_profile_workflow` 降为 compat-only。
- **具体功能预期**：
  1. 同一 `source_kind=http_resource` 下 `acquisition_mode` ∈ {static, browser, pdf} 解析到同一 `workflow_key`/`compiled_digest`（active kind 图）。
  2. 同一 `local_object` 下 pdf/image/缺 media 不改变 kind key。
  3. `registered_api` 仍解析 scatter root。
  4. 非法 `source_kind` → 422；缺 kind 图 → 503。
  5. 公共模型 dump/schema 不含 `workflow_key`。
  6. 图未声明的 `process_key` 即使存在于 Python dispatch dict 也 409。
- **对应测试台账项**：`NH2-T01` / `NH2-T05` / `NH2-T07`
- **收口标准**：kind-only 谓词 + 未声明 409。
- **本 Phase 风险提醒**：未知 profile 今日 503（`workflow_registry.py:101-102`）不得继续当「选图失败」的万能码；须 422/503 分码（`FG-NH-02` 只禁止把 503 当 **in-scope 成功** DoD，负例 503 仍合法）。

### 5.5 Phase 5 — compat + 红线扫描

- **Phase 目标**：旧 pin 不被绞杀；红线机器可检。
- **本 Phase 对应编号**：`NH2-07` / `NH2-08`
- **本 Phase 新增 / 修改 / 删除文件**：修改 `runtime_core.py` 仅当 enabled-unselected 加载集需要显式纳入旧 key；新增 `tests/domain/test_nh2_architecture_scan.py`；扩展 `tests/unit/test_workflow_revision_compatibility.py`。
- **具体功能预期**：
  1. 旧 compiled_digest Execution 在 kind 图成为 active 后，process_key 序列与 pin 当时一致。
  2. 新 Task 解析不到旧 selector key。
  3. 未知 digest 零 Process。
  4. 扫描：无 caller `workflow_key`、零 `action_branch`、eq-only、tail 源唯一。
  5. telemetry 在旧 pin 命中时递增（测试可断言 metric/event 存在，不要求退役）。
- **对应测试台账项**：`NH2-T06` / `NH2-T07`
- **收口标准**：compat 谓词 + scan EXIT 0；kind 激活前书面 compat review 记入 evidence `closure.md`。
- **本 Phase 风险提醒**：`R-F04` 删除旧 key 会 409 in-flight。

---

## 6. 依赖的冻结设计决策（只读引用）

> 只引 Q 编号与 T-O-ID，不复制业主长文、不改口、不开新 Q/A。

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Q11 → `T-O-391` | `pre-charter-qna.md` §5 | Phase 1 CONTROL 形态：optional ports、exactly-one、禁 scatter wait | 本 AP 不得改选 one-of / duplication；回 NH1 STOP |
| Q12 → `T-O-392` | 同上 | Phase 2 守卫只读登记投影；本 AP 不把 Process JSON 当权威 | 不得在本 AP 发明第二 SSOT |
| Q18 → `T-O-398` | 同上 | substrate 留 NH；禁 JOIN/DSL/表达式；NH1 证伪即停 | 禁止实施中换 duplication |
| Q22 → `T-O-402` | 同上 | `main_text_presence` 三态；仅 absent 走 browser；unknown fail-closed | 不得用质量分/LLM 路由 |
| Q4 → `T-O-384` | `pre-initial-planning-qna.md` §1 | 同 revision 预声明边；选后才 seal（seal 在 NH3）；禁暗调未声明 process | 不得表外 `dispatch_clean` |
| Q7 → `T-O-387` | 同上 | 图基数 3 single + scatter；mode/media 不选图 | 不得保留 7+6 public 选图 |
| Q8 → `T-O-388` | 同上 | 有限正向再获取；decode 观察；禁环/try-all | 不得同 step 自环当再获取 |
| `T-O-377` | 同上 | 四 kind；禁 `action_branch` | T07 扫描失败不得标完成 |
| `T-O-379` | 同上 | caller 禁 `workflow_key`；三轴取值 | public 合同出现该字段即失败 |
| `T-O-382` | 同上 | 晚绑定闭集规则；禁无证据暗升 | NH2-06 409 未声明工人 |
| Q21 → `T-O-401` | `pre-charter-qna.md` | full_task exact；existing upgrade OOS；compat 不热切 | 不得借 kind 迁移清 actual |
| `T-R-NH-01/02/03` | `final-execution-plan.md` §2.1 | 分母 13/7/6、无 merge、mode 选图是 HEAD 事实 | 以 HEAD 6 张 unselectable 为准，不写 5 |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表（本计划工作要落在哪些既有代码 / 新建点上）

> `处置`：`✅ 复用` / `♻️ 重 substrate` / `🆕 净新`。行号以 HEAD `1221aa1` 本次 `read_file` 为准。

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| NH2-A01 | `src/contracts/workflow/models.py:373-525` | 编译器：unique route（378-380）、自边禁（389-390）、无环 DFS（418-432）、单 binding（496-497）、required unbound 失败（523-525） | NH2-01 保围栏；NH2-04 拒环/重复 | `♻️ 重 substrate` | 扩 CONTROL **不得**放松 unique-binding。optional 已存在：`36-37` `OPTIONAL`；`113-120` `required: bool = True`。`step_key` 唯一：`337-340` |
| NH2-A02 | `src/runtime/workflow/runtime_materialize.py:49-83,86-117,119-168` | 路由确定性；缺键 fail-closed（110-113）；typed context 从 durable Task/CandidateSet/transition 投影 | NH2-01 扩 CONTROL 分发；NH2-02 加 fact 投影键 | `♻️ 重 substrate` | ledger 写 `:101-168`；本次核实路由决策从 `:49` 起。optional skip `:435-441` 只证明未访问≠事故，**不是** merge |
| NH2-A03 | `src/workflows/lsrag_definition.py:881-1070` | `_source_profile_workflow` 三槽工厂（881-926）；7 public key（929-940）；6 unselectable（1003-1054）；tuple 闭包 1057-1070 | NH2-03/06 停 factory；NH2-03 并入 6 张边 | `♻️ 重 substrate` | ledger `:881-1069`；HEAD tuple 止于 **1070**。`FG-NH-09` 反例 |
| NH2-A04 | `src/services/config_snapshots.py:492-516` | `_source_profile` 用 mode/media 选 7 profile；`prepare:138-144` 传入 `resolve_for_source` | NH2-05 改为起点 fact，不选 key | `♻️ 重 substrate` | `T-R-NH-03`。未知 mode 今日可导致 503 |
| NH2-A05 | `src/runtime/workflow/runtime_core.py:591-625` | `_assert_execution_binding`：按 `compiled_digest` 取 plan，不取当前 active 图 | NH2-07 old pin 必须保持 | `✅ 复用` | 加载映射 `:88-100`；active key 检查 `:608-614` 是塌缩风险（`NH-RA01-B08`）。step 不一致续至 `:626-633`。未知 plan 负例已在 `tests/unit/test_workflow_revision_compatibility.py:175-192` |
| NH2-A06 | RA01 `RA-01-WEB-03..07` | SFN 无 Default fail-loud；CWL `the_only_non_null`；Airflow AND-join 级联 skip；Camunda XOR join 不并数据 | NH2-01 失败法；禁止借引擎 | `🆕 净新`（本仓 CONTROL） | 外部只借 **失败法**。见 §7.3 |
| — | `src/services/workflow_registry.py:78-104` | `resolve_for_source` 仍 `profile or source_kind` → 13 key | NH2-05 | `♻️ 重 substrate` | 内部 `resolve_by_key:122-140` 仅 bootstrap/compat |
| — | `src/contracts/workflow/models.py:245-278` | 5 种 predicate、operator 仅 `eq`；0 条 representation-aware | NH2-02 | `♻️ 重 substrate` | `D-09=0` |
| — | `src/runtime/workflow/runtime_scatter.py:24-109` | scatter collect-all wait / 零成员 SUCCESS | NH2-01 ⛔ 不复用 | `✅ 复用`（scatter 自身） | XOR 不得走这条 |
| — | `src/contracts/api/models.py:107-178,273-297` | SourceDescriptor / TaskCreateRequest **无** `workflow_key` | NH2-05/08 保持 | `✅ 复用` | 正例：caller 面已禁 key |
| — | `src/runtime/intake/core.py:356-386` | process_key → handler 字典 | NH2-06 加「必须在 pinned 图上」 | `♻️ 重 substrate` | 未声明 409 |
| — | `src/persistence/migrations/001_initial.sql:1770-1771,638-640,583` | binding unique；DDL operator 宽于合约；`mkb_workflow_controls` 无 merge 语义列 | NH2-01 不改 unique；NH2-02 不放宽合约 | `✅ 复用` / ⛔ 勿对齐 DDL 放宽 | `M-NH-03` 若需 CONTROL 版本元数据，不得改成 one-of |
| — | `tests/unit/test_workflow_registry.py:31-80` | 同 key 追加 revision、不改 v1 行 | NH2-T01 🔱 | `✅ 复用` | |
| — | `tests/unit/test_workflow_revision_compatibility.py:106-192` | 旧 pin 跑完；未知 digest 零 Process | NH2-T06 🔱 | `✅ 复用` | |
| — | `tests/domain/test_architecture.py:1-16` | 不 import 应用的源码扫描风格 | NH2-T07 🔱 风格 | `✅ 复用` | 新建 `test_nh2_architecture_scan.py` |
| — | `src/contracts/intake/strategies.py:15-151` | 10 `CleanStrategyKey` 与 acquire/clean capability | NH2-03/04 合法边闭集 | `✅ 复用` | 本 AP 不改策略语义 |
| — | `api/app.py:297-304` | additional_definitions = scatter + 12 profile；compat 注入 | NH2-03/07 | `♻️ 重 substrate` | 切换 additional_definitions 时必须仍加载旧 key |

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | `src/workflows/lsrag_definition.py:929-940` 7 public selector + `:1003-1054` 6 张 unselectable 当作「已覆盖 live 矩阵」 | `T-R-NH-01`；`NH-RA01-B06`。6 张能 bootstrap / `resolve_by_key` ≠ caller 可达 |
| ⛔2 | `src/services/config_snapshots.py:492-516` 继续用 mode/media 选 key | `T-R-NH-03` / `T-O-387` |
| ⛔3 | `runtime_materialize.py:505-514` 无 selected-output；把 `scatter_children_join`（`runtime_scatter.py:24-109`）当 XOR | `T-O-391`；Airflow AND-join 失败法（`RA-01-WEB-06`）；未选中边永不来 |
| ⛔4 | `_source_profile_workflow`（`881-926`）复制 tail 冒充 kind family | `FG-NH-09` / `R-F10` / `T-O-387` |
| ⛔5 | 改 `each workflow input port may have only one binding`（`496-497`）搞 one-of 自由 binding | Q11 已否；DDL `ux_workflow_binding_slot` |
| ⛔6 | 把 `human_review_gate` CONTROL 实现（`runtime_materialize.py:513-534`）类比为 selected-output 完成 | `NH-RA01-B09`；CONTROL 只钉该 runtime 分支。`src/workflows/lsrag_definition.py:366-383` 是 `accept_snapshot.human_review` **BRANCH 路由**，不是 `control_key=human_review_gate` 实现 |
| ⛔7 | `WorkflowStepKind.JOIN` / `ALL_REQUIRED`（`models.py:32,64-67`，HEAD 0 使用）当 merge | JOIN 是 AND fan-in；第三通道禁止（`T-O-398`） |
| ⛔8 | CWL `when` / SFN JSONata / FEEL / Python `@task.branch` 当守卫 | `RA-01-WEB-05`；`S03-T012`；`T-O-398` |
| ⛔9 | 从 `_active_workflow_keys` 删除旧 profile key 或要求 compat 必须换新 kind key | `NH-RA01-B08`；`runtime_core.py:94-95,608-614`；`R-F04` |
| ⛔10 | 守卫读 Process output JSON / 常量 `injected-browser-renderer.v1` | `T-O-392`；RA03 反例 |
| ⛔11 | 未知 profile 503 当正路径 DoD；或 public API 调通 `resolve_by_key` 当完成 | `FG-NH-02`；台账 D NOT-成功 |
| ⛔12 | 本 AP 生产 history 行或 actual S05 列 | 属 NH3；DAG 明确不等 actual 列 |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：
  - 主面：`docs/eval/new-harvest/reference-anchor/assessment-analysis-01-workflow-graph-and-kind-family.md`（`NH-RA01-B01..B12`；`RA-01-WEB-01..07`；`NH-N-01-01..05`）
  - 邻面：`docs/eval/new-harvest/reference-anchor/assessment-analysis-03-representation-and-reacquisition.md`（`NH-RA03-B04` 无 representation guard；`NH-RA03-B10` 空壳观察；本 AP 只声明 `main_text_presence` 谓词，不生产行）
- **外部借鉴 verdict（不进 §7.1 混用）**：`RA-01-WEB-03` 🔶借「无命中 fail-loud」不借 JSONata；`RA-01-WEB-04` 🔶借 `the_only_non_null` 失败法不借 `pickValue` 表达式；`RA-01-WEB-05` ⛔ `when`；`RA-01-WEB-06` ⛔ AND-join 默认；`RA-01-WEB-07` 🔶 XOR join 不并数据；Temporal 只借「选择进 history / 旧 pin replay」，⛔ 引擎。
- **安全 / 信任边界威胁模型**（不得留空；对应 NH2-05/01/08）：

| 威胁 | 信任边界 | 攻击者能力 | 本 AP 控制 | 测试 |
|------|----------|------------|------------|------|
| 调用方点名图/工人 | public Task 合同 → resolver | 在 payload/overrides 注入 `workflow_key` / `process_key` / `action_branch` | 模型无该字段（HEAD 已无 key）；resolver 忽略/拒非 kind 坐标；T07 扫描 | `NH2-T01` / `NH2-T07` |
| 自由表达式注入 | guard 注册 | 提交 JS/SQL/JSONata/FEEL/`when` | predicate 闭集 + `eq` only；注册失败 | `NH2-T03` / `NH2-T07` |
| CONTROL 等待未选中边 | runtime CONTROL | 使未 materialize 候选造成永久 wait（DoS） | optional absent；禁 scatter wait | `NH2-T02` |
| 暗 dispatch 未声明工人 | handler / preflight | 图外 `process_key` 仍执行 | pinned revision 闭集校验 409 | `NH2-T05` / `NH2-T07` |
| 旧 pin 热切 | Execution binding | 部署新 kind 图后改写 in-flight 程序 | digest pin + enabled-unselected 旧 key | `NH2-T06` |
| 选图 503 冒充完成 | public resolve | 把 registry 空洞当接通 | 分码 422/503；正路径必须选中 kind 图 | `NH2-T01`；`FG-NH-02` |

---

## 8. 测试台账

> 分层遵守 `T-O-406`：L1 unit / L2 integration·UoW。本 AP 台账 C 最低层不得自行降低。fault/race/security 是标签不是替代层。本 AP 无 L3/L4 义务。

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| `NH2-T01` | 4 `source_kind` 唯一选图；mode/media 不再改变 key；unknown 422/503 分码 | 短途 | L1/L2 | 🆕 `tests/unit/test_nh2_kind_only_resolver.py`；🔱 `tests/unit/test_workflow_registry.py` | `NH2-05` → kind-only | `commit SHA + pytest node PASS + Q7/Q18 + UTC` |
| `NH2-T02` | merge 一选一；零/双失败；optional 未 materialize 不等待 | spike | L1/L2 | 🆕 `tests/integration/test_nh2_selected_output_control.py`（NH1-T04 仅前置 GO 门） | `NH2-01` → exactly-one CONTROL | `commit SHA + CONTROL suite PASS + Q11 + UTC` |
| `NH2-T03` | representation guard fail-closed | 短途 | L1/L2 | 🆕 `tests/unit/test_nh2_representation_guards.py` + 🆕 `tests/integration/test_nh2_representation_guards.py` | `NH2-02` → deterministic route | `commit SHA + present/absent/unknown PASS + Q22 + UTC` |
| `NH2-T04` | forward/no-cycle/每 step 一次；自环/环/重复 step_key 拒注册 | 短途 | L1 | ♻️ `WorkflowDefinition.validate_definition`（HEAD 无现成 cycle pytest）；🆕 `tests/unit/test_nh2_workflow_compiler.py` | `NH2-04` → 非法图拒注册 | `commit SHA + cycle/duplicate reject PASS + Q8 + UTC` |
| `NH2-T05` | 合法 acquire/decode/clean 边经 public resolve 可达；原 6 张 unselectable 不得经 caller 选中 | 集成 | L2 | 🆕 `tests/integration/test_nh2_legal_edges_reachable.py` | `NH2-03/05` → 合法边全可达 | `commit SHA + matrix edge PASS + T-O-381 + UTC` |
| `NH2-T06` | old pin 与 new graph 共存；新 Task 不解析旧 selector key | compat/C | L2 | 🔱 `tests/unit/test_workflow_revision_compatibility.py` | `NH2-07` → 旧序列不变 | `commit SHA + old sequence PASS + Q18 + UTC` |
| `NH2-T07` | 禁 caller `workflow_key` / `action_branch` / 自由表达式；tail 源唯一 | architecture | L1 | 🆕 `tests/domain/test_nh2_architecture_scan.py` | `NH2-08` → redlines EXIT 0 | `commit SHA + scan EXIT0 + T-O-377 + UTC` |

#### `NH2-T01`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🆕 `tests/unit/test_nh2_kind_only_resolver.py`：`test_four_kinds_resolve_unique_graphs`；`test_mode_and_media_do_not_change_workflow_key`；`test_unknown_source_kind_is_422`；`test_missing_kind_graph_is_503`。🔱 `tests/unit/test_workflow_registry.py`：扩展既有 `test_registry_appends_v2_without_mutating_or_rebinding_v1` 的 registry fixture，新增 `test_resolve_for_source_kind_only_ignores_profile` |
| 用途 | 证明 `NH2-05`；`FG-NH-09`（不是 7 profile）；`FG-NH-02`（503 只作缺图负例） |
| 前置 | `SqlitePersistence` + `WorkflowRegistryService.bootstrap`；真实 UoW；禁止 sqlite3 直读。Task 合同用 `TaskCreateRequest` 构造，不手写 `workflow_key` |
| 步骤 | a) bootstrap kind 图 + scatter。b) 对 `inline_payload` / `local_object` / `http_resource` / `registered_api` 调 `resolve_for_source("intake.ingest", source_kind)`。c) 对 `http_resource` 分别带 static/browser/pdf 起点 fact 再 resolve。d) 对 `local_object` 分别带 pdf/image/缺 media。e) 构造非法 `source_kind`。f) 清空某 kind 的 enabled 行后再 resolve |
| 断言细节 | 四 kind 得到四个互异 identity（scatter root ≠ 三 single）。c/d 的 `workflow_key` 与 `compiled_digest` **不随** mode/media 变化。非法 kind：HTTP/schema 422 或 `TaskCreateRequest` ValidationError（测试同时覆盖服务层若被直接调用）。缺图：`MkbError.code == "REGISTRY_NOT_FOUND"` 且 status 503。`resolve_for_source` 源码路径不再读取 `SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS` 作为 public 选择 |
| 负例 | `source_profile="http_resource.static"` 不得选出与 kind 图不同的旧 key；payload 含 `workflow_key` → 422 extra-forbid |
| 跑法 | `uv run pytest tests/unit/test_nh2_kind_only_resolver.py tests/unit/test_workflow_registry.py::test_resolve_for_source_kind_only_ignores_profile -q` |
| 层与来源 | L1/L2；`🆕` + `🔱` |

#### `NH2-T02`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🆕 `tests/integration/test_nh2_selected_output_control.py::test_exactly_one_projects_canonical_output`；`::test_zero_hit_fails_loud_without_fallback`；`::test_double_hit_fails_integrity`；`::test_unmaterialized_optional_is_absent_not_wait`；`::test_registered_fallback_enters_compiled_digest`；`::test_does_not_call_scatter_join_wait`。NH1-T04 是前置 GO 门（`tests/unit/test_nh1_selected_output_control.py` 与 `tests/integration/test_nh1_merge_control.py` 下零/一/双/缺 fact node），**不是**本 Test-ID 的 pytest 参数 |
| 用途 | 证明 `NH2-01` / `T-O-391`；NOT-成功：human_review 类比、scatter join 复用、复制 13 profile |
| 前置 | 真实 PersistencePort/UoW；最小 immutable 图（两 clean candidate + CONTROL + 共享 dummy tail）。CONTROL 候选 port `required=False`。禁止 monkeypatch CONTROL 为「任选第一个成功」 |
| 步骤 | a) 注册图并创建 Execution。b) 只让 candidate A 成功 → 读下游 Process input manifest / binding，canonical ref == A。c) 两候选都不 materialize 且无 fallback → Execution/CONTROL 失败，`mkb_executions.status` 非 `waiting`，`waiting_reason` 不是 `scatter_children`。d) A 与 B 都 SUCCEEDED → 完整性错误码（锁具体 `MkbError.code`）。e) 声明 fallback 的 CONTROL 版本：零命中投影 fallback，且 `_compiled_workflow_digest` 材料含 fallback/version。f) 探测代码路径：selected-output 分支不得进入 `_enter_scatter_children_join_tx` |
| 断言细节 | HTTP 非本项必须；DB：成功路径恰好 1 条 canonical 下游 materialize；失败路径零下游 seal/tail Process。digest：改 fallback 声明 → compiled_digest 变化。unique-binding：给同一 CONTROL port 两条 binding → 注册 `ValueError` |
| 负例 | 把 candidate ports 设 `required=True` 导致未选中边编译失败——必须被本套件拒绝为错误建模。双命中不得「任选一个」变绿 |
| 跑法 | `uv run pytest tests/integration/test_nh2_selected_output_control.py -q`。T02 **只**以该文件为生产套件；NH1-T04 仅作前置 GO 门，不得写成 pytest node 参数 |
| 层与来源 | L1/L2；`🔱` + `🆕`；标签 spike |

#### `NH2-T03`

| 字段 | 内容 |
|---|---|
| 测试位置 | L1 🆕 `tests/unit/test_nh2_representation_guards.py`：`test_present_does_not_take_browser_edge`；`test_absent_takes_declared_browser_edge`；`test_unknown_fail_closed`；`test_missing_key_fail_closed`；`test_non_eq_operator_rejected`；`test_unknown_predicate_type_rejected`；`test_guard_ignores_process_output_json`。L2 🆕 `tests/integration/test_nh2_representation_guards.py::test_missing_or_unknown_main_text_does_not_materialize_browser_acquire` |
| 用途 | 证明 `NH2-02` / `T-O-402`；防假绿：编译通过但 runtime 无 representation context；`FG-NH-13`（L1 不得顶 L2） |
| 前置 | L1：直接构造 `WorkflowGuardDefinition` + 调用 `_guard_matches`（禁止抽出纯函数顶替 L2）。L2：真实 UoW 注册微型图；fixture 经 fact-read 接口写入 `main_text_presence`，**不**写 NH3 正式表（若表尚不存在，用 NH1 冻结接口的测试双）。禁止 sqlite3 直读 Turso |
| 步骤 | a) 注册含 `eq absent` browser 边与 unguarded 失败/停边的微型图。b) context `present` → `_route_decision` 的 `routes` 不含 browser。c) `absent` → 含已声明 browser。d) `unknown` → 不含。e) 缺键 → 不含且 `guard_results[k] is False`。f) `operator="ne"` model_validate 失败。g) 仅在 Process output JSON 放 `absent`、投影接口为空 → 仍 fail-closed。h) L2：缺键/unknown 时经 Port 断言 `mkb_processes` **零** `intake.acquire.http_browser` 行 |
| 断言细节 | L1：非 eq / 未知谓词 `ValidationError` 或 409 `workflow-guard-unsupported`；`results` 字典写入 False 而非缺省 True。L2：无边被选时 `mkb_processes` 零 `intake.acquire.http_browser` 行；present 时该 process_key 行数为 0，absent 时为 1 |
| 负例 | `expected_value="maybe"` 不可注册；LLM score 字段即使出现在 context 也不得被未登记谓词消费；纯函数布尔值顶替 UoW Process 行 |
| 跑法 | `uv run pytest tests/unit/test_nh2_representation_guards.py tests/integration/test_nh2_representation_guards.py::test_missing_or_unknown_main_text_does_not_materialize_browser_acquire -q` |
| 层与来源 | L1/L2；`🆕`；L1 不可单独关闭 T03 |

#### `NH2-T04`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🆕 `tests/unit/test_nh2_workflow_compiler.py`：`test_self_edge_rejected`；`test_cycle_rejected`；`test_duplicate_step_key_rejected`；`test_duplicate_binding_to_same_port_rejected`；`test_reacquire_requires_distinct_step_keys`。♻️ SUT = `WorkflowDefinition.model_validate` / `_validate_graph` / `_validate_bindings`（HEAD **没有**现成 cycle pytest；`tests/unit/test_lsrag_compiler.py` 是 S06 生成编译器，**不要**误用） |
| 用途 | 证明 `NH2-04` / `T-O-388` / `S03-T011` |
| 前置 | 纯 unit，无 DB。从最小合法 kind 图 fixture 变异 |
| 步骤 | a) `from_step_key == to_step_key` → `ValueError` 匹配 `cannot be self-edges`。b) A→B→A 环 → `must be acyclic`。c) 两步同一 `step_key` → `step_key values must be unique`。d) 同一 input 两 binding → `only one binding`。e) 两个不同 `step_key` 的 acquire 正向边合法通过 |
| 断言细节 | 异常类型 `ValueError`，消息与 `models.py:390,432,340,497` 一致。合法双 acquire 图 `model_validate` 成功且 adjacency 无回边 |
| 负例 | 把「同 step retry」画成图上的再获取必须失败 |
| 跑法 | `uv run pytest tests/unit/test_nh2_workflow_compiler.py -q` |
| 层与来源 | L1；`♻️` SUT + `🆕` nodes |

#### `NH2-T05`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🆕 `tests/integration/test_nh2_legal_edges_reachable.py`：`test_kind_graphs_declare_all_legal_edges`；`test_former_unselectable_six_not_selected_by_public_resolver`；`test_public_resolve_does_not_require_resolve_by_key`；`test_undeclared_process_key_is_409` |
| 用途 | 证明 `NH2-03/05/06`；`T-O-381` 边在图上（**不**要求 live 跑通，那是 NH7）；NOT-成功：6 张 hidden bootstrap |
| 前置 | migrate + `WorkflowRegistryService.bootstrap` + 真实 UoW。对照 `CLEAN_STRATEGY_DEFINITIONS`（`strategies.py:47-151`）生成 expected process_key 集合。L2，禁止只读 Python 常量而不查 registry 行 |
| 步骤 | a) public `resolve_for_source` 得三 kind + scatter root identity。b) 查 `mkb_workflow_steps`（经 PersistencePort）收集 `process_key`。c) 断言 http kind 含 `intake.acquire.http_static`、`intake.acquire.http_browser`、print 相关步、`clean.extract.web` / `web_llm` / `pdf_llm` 等该 kind 合法键；local kind 含 pdf/ocr/vision/doc_llm 等；inline 含 deterministic。d) 对旧 6 key 调 public resolve（不给 `resolve_by_key`）不得返回这些 key。e) `resolve_by_key` 仍可能 bootstrap 成功——**本测试不得把该成功当作 PASS 条件**。f) 对 inline Execution 强制跑未声明 `process_key` → 409 |
| 断言细节 | expected ⊆ declared steps。public identity 集合与旧 13 key 交集为空（旧 key 可 enabled-unselected 但 resolver 不返回）。409 后 `mkb_processes` 无该 process_key 的 succeeded 行 |
| 负例 | 仅 assert `len(BUILTIN_WORKFLOWS) >= 13`；仅 `resolve_by_key(print-pdf)` 200 |
| 跑法 | `uv run pytest tests/integration/test_nh2_legal_edges_reachable.py -q` |
| 层与来源 | L2；`🆕`；`FG-NH-13` 禁止用纯 unit 顶替本项 |

#### `NH2-T06`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🔱 `tests/unit/test_workflow_revision_compatibility.py::test_v2_runtime_materializes_and_completes_unstarted_v1_execution`（既有 `:106-168`）；`::test_unknown_historical_compiled_plan_fails_before_process_materialization`（既有 `:175-192`）。🆕 同文件：`test_old_pin_sequence_unchanged_after_kind_family_activation`；`test_new_task_does_not_resolve_old_selector_key` |
| 用途 | 证明 `NH2-07` / `T-O-398`；`R-F04`；NOT-成功：只测「还能 register 旧定义」 |
| 前置 | 既有 `_seed_v1_execution` + `HISTORICAL_SINGLE_INTAKE_LSRAG_WORKFLOW_V1`。第二场景：runtime additional_definitions 换成 kind 图，但仍注入旧 key 为 active/compat。真实 UoW |
| 步骤 | a) 复跑 v1 pin 在 vN active 下完整成功，process_key 序列锁死（既有断言：acquire.inline → decode → deterministic → seal → … → validate_publication）。b) 激活 kind 图后对同一 pin 再跑，序列与 compiled_digest **不变**。c) 新 ingest Task（kind-only prepare）的 workflow_key ≠ `http_resource.static` 等旧 selector。d) 未知 digest：零 Process 行 |
| 断言细节 | `workflow_revision_uuid` / `compiled_digest` 与 seed 一致。新 Task identity 属于 kind 闭集。`waiting`/`409 workflow-binding-mismatch` 不得在旧 pin 成功路径出现 |
| 负例 | 删除旧 key 后再跑 pin 导致 409——该负例应作为 **回归失败**（产品不允许），或单独标为「错误配置」而非 DoD |
| 跑法 | `uv run pytest tests/unit/test_workflow_revision_compatibility.py -q` |
| 层与来源 | L2；`🔱` + `🆕` nodes；compat/C |

#### `NH2-T07`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🆕 `tests/domain/test_nh2_architecture_scan.py`：`test_public_api_has_no_workflow_key_parameter`；`test_zero_action_branch_in_runtime_surface`；`test_guard_operator_eq_only_no_free_expression`；`test_three_kind_graphs_share_one_tail_source`；`test_selected_output_not_aliased_to_scatter_join` |
| 用途 | 证明 `NH2-08` / `T-O-377` / `T-O-379` / `T-O-398`；`R-F10`；安全威胁模型攻击面 |
| 前置 | 不 import 应用（与 `tests/domain/test_architecture.py` 相同）。扫描 `api/`、`src/contracts/api/`、`src/`、`intake/`。可用 ast + 文本 |
| 步骤 | a) AST 扫描 Pydantic/请求模型字段名，禁止 `workflow_key` 出现在 public/internal Task 入参模型。b) 生产代码（排除 `docs/`、本测试、引用反例的注释白名单须极窄且不得在 `src/` 赋值）零标识符 `action_branch`。c) `WorkflowGuardDefinition` 源码 `operator: Literal["eq"]`；尝试动态构造自由表达式守卫失败。d) 三 kind 图模块 import 同一 tail 符号；或对 compiled dump 计算 generation/publication 子图哈希相等。e) `selected_output`（或 NH1 冻结字面）实现函数不得调用 `_enter_scatter_children_join_tx` |
| 断言细节 | pytest EXIT 0。哈希报告写入 evidence `security/redline-scan.txt`（执行期产生，本 AP 不伪造 SHA）。内部 `resolve_by_key` 允许存在，但不得被 public 路由引用 |
| 负例 | 文档中出现 `action_branch` 作为反例叙述 **不**导致失败；`src/` 新引入则失败 |
| 跑法 | `uv run pytest tests/domain/test_nh2_architecture_scan.py -q` |
| 层与来源 | L1；`🆕`；architecture / security 标签 |

### 8.2 复用台账（沿用 / fork 的既有用例明细）

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/unit/test_workflow_registry.py::test_registry_appends_v2_without_mutating_or_rebinding_v1` | `♻️ 沿用` + 🔱 增 kind-only 用例 | 0 改动旧断言；新增 resolve 用例 | HEAD 已存在 |
| `tests/unit/test_workflow_revision_compatibility.py::test_v2_runtime_materializes_and_completes_unstarted_v1_execution` | `🔱 fork` 语义：激活 kind 后仍须 PASS | 加 kind-family 激活场景 | HEAD 已存在，PASS |
| `tests/unit/test_workflow_revision_compatibility.py::test_unknown_historical_compiled_plan_fails_before_process_materialization` | `♻️ 沿用` | 0 改动 | HEAD 已存在 |
| NH1-T04 selected CONTROL spike nodes | `🔱 fork → 生产` | 升级为 NH2-T02 套件；不得删零/双命中 | 依赖 NH1 PASS |
| `tests/domain/test_architecture.py` | `🔱 风格 fork` | 不改 D03 扫描；新建 NH2 文件 | HEAD 已存在 |
| `tests/unit/test_intake_source_capabilities.py::test_source_profiles_resolve_to_distinct_executable_workflow_capabilities` | kind 图激活 **之后**，期待值改为 4 kind 唯一 identity（`T-O-387`）；激活前旧 7-profile 断言必须保持红。禁止为让本文件先绿而改期待（`FG-NH-17` / `T-O-406`：waiver 不得改期待值） | 映射到 T01/T05 回归；激活前本文件红 ≠ T01 FAIL | HEAD 断言 7 profile（`local_pdf` / `http_static` / `http_browser` 等不同 `process_key`），属将过时 |

### 8.3 分层与跑法（各类型在哪跑、何时跑）

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `uv run pytest tests/unit/test_nh2_*.py tests/integration/test_nh2_representation_guards.py tests/domain/test_nh2_architecture_scan.py -q` | L1（T04/T07）+ L1/L2（T01/T03） | 每 PR |
| spike | `uv run pytest tests/integration/test_nh2_selected_output_control.py -q` | L2 UoW | Phase 1 收口与本 AP 收口（NH1-T04 仅 GO 门） |
| 集成 | `uv run pytest tests/integration/test_nh2_legal_edges_reachable.py -q` | L2 | Phase 3–4 收口 |
| compat | `uv run pytest tests/unit/test_workflow_revision_compatibility.py -q` | L2 | Phase 5；kind 激活前硬闸 |
| mega / soak / L3 / L4 | 本 AP 不跑 | — | 交 NH7/NH9 |

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖 history 行 append、actual S05 seal/CAS、同 step 第二次成功拒绝的 **行级** 证明 → `AP-NH3`。
- 不覆盖 PDF/browser/OCR 真实 binary、default-root L3、无 monkeypatch live → `AP-NH6` / `AP-NH7`。
- 不覆盖 10+3 走到可检索向量、L4 facet → `AP-NH7` / `AP-NH9`。
- 不覆盖旧 key 有界退役/回滚演练的完整 NH8 路径 → `AP-NH8-07`（本 AP 只做共存 + telemetry）。
- 不覆盖 `exhausted_zero`、七意图矩阵、upload → 对应 AP。
- **不在本 AP 假装覆盖** live print_pdf 诚实 bytes（RA03）；本 AP 只保证 print 步在 http kind 图上 **声明可达**。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 必带四元组 `commit SHA + pytest node PASS + Truth/Q + UTC`；计数 ≠ 价值。
- 本 AP 适用 FG：
  - `FG-NH-09`：复制 tail/13 profile ≠ kind family（T01/T05/T07）
  - `FG-NH-02`：503 不得当正路径 DoD（T01 缺图负例才 503）
  - `FG-NH-13`：不得用 L1 顶替 T03/T05/T06 的 L2（T03 禁止抽出纯函数顶 UoW）
  - `FG-NH-12`：不得 sqlite3 直读 Turso
  - `FG-NH-17`：kind 图激活前禁止改 7-profile 期待值保绿；waiver 不得改期待值（`T-O-406`）
- `degraded` 必带机器可读 `reason`；pre-existing 失败必带 git 证据，不 silent overclaim。
- 安全项必须含攻击向量：注入 `workflow_key`、自由表达式、未声明 `process_key`、CONTROL wait（§7.3）。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| NH1-T04 / `R-F01` | CONTROL 切片不可行 | `high`（硬依赖） | 本 AP **不得开工**；STOP/reopen Q11；禁止 duplication |
| `R-F04` old pin 绞杀 | 退役旧 key 或 active 检查失败 → in-flight 409 | `high` | enabled-unselected；T06；telemetry；退役交 NH8 |
| `R-F10` tail 复制 | vertical 按策略拷贝 publication | `high` | 单一 tail 源 + T07 哈希 |
| `NH-RA01-B08` | compat 要求 active key，kind 塌缩冲突 | `high` | 不塌缩删除旧 key |
| 谓词/事实双 SSOT | 守卫读 JSON 而非投影 | `medium` | T03 JSON 负例；权威行交 NH3 |
| DDL operator 宽于合约 | 未来误开 `ne/lt` | `medium` | T07/T03 锁 `eq` |
| NH3 尚未有 fact 表 | Phase 2 投影无行 | `medium` | NH1 冻结 fact-read 接口 + fixture；不等 actual 列 |
| `R-F16` scope 滑向通用引擎 | JOIN/DSL/表达式 | `medium` | `O-NH-06`；T07 |

### 9.2 约束与前提

- **技术前提**：HEAD 七表编译器、optional ports、digest pin、eq-only 守卫保持。不修改 unique-binding 代数。
- **运行时前提**：本 AP 不要求 default-root 具备 browser/OCR 供给。
- **组织协作前提**：NH1 evidence pack 给出 CONTROL `control_key` 字面与 fact-read 接口版本。kind 图 **激活前** 完成 compat review（签署进 `docs/evidence/new-harvest/AP-NH2/closure.md`）。
- **上线 / 合并前提**：`NH2-T01..T07` 全 PASS；禁止在扫描红时切 public resolver。

### 9.3 文档同步要求

- 需要同步更新的设计文档：执行期 `M-NH-03`（CONTROL）/ `M-NH-04`（kind/compat 清册）说明写入 evidence，**不改** QNA/final
- 需要同步更新的说明文档 / README：仅当 public 选图行为变化需操作说明；本 AP 起草时不预写新 README
- 需要同步更新的测试说明：本文件 §8；evidence `tests.txt`

### 9.4 完成后的预期状态

1. 新 ingest Task 只解析到 3 single-root kind 图之一或 scatter root；mode/media 不改 `workflow_key`。
2. 同 kind 多候选 clean/acquire 经 selected-output CONTROL 汇入 **一份** 共享 tail；三 kind tail 源唯一。
3. 表示守卫 eq-only 可声明；缺键/unknown 不暗升；history 行仍由 NH3 生产。
4. 旧 `compiled_digest` Execution 事件/process 序列保持；未知 digest 不插 Process。
5. 架构扫描 EXIT 0；`resolve_by_key` 不是 public 完成条件。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

### 10.1 收口硬闸

所有台账 C 项必须 **PASS 且四元组证据齐全**。kind definitions **激活前** 完成 compat review。

1. **kind-only**：`resolve_for_source` 不再读取 `acquisition_mode` / `media_type` 作为 **选图** 键；它们只可作为起点 fact。4 kind 各映射唯一图。非法 kind → 422；缺 enabled kind 图 → 503。由 `NH2-T01` / `NH2-T05` 证明。
2. **one shared tail**：三张 single kind 图的 generation/publication **子图哈希相等**，且引用同一源符号；不得 per-strategy 复制 tail。由 `NH2-T02`（CONTROL 后单 tail）+ `NH2-T07` definition scan 证明。
3. **deterministic route**：fact 缺失或 `main_text_presence=unknown` **不选** 对应边；非 eq / 未知谓词拒注册或 409；自环/环/重复 `step_key` 拒注册。由 `NH2-T03` / `NH2-T04` 证明。
4. **compat**：旧 `compiled_digest` 的 in-flight Execution **事件/process 序列不变**；新 Task 不解析旧 selector key；未知 digest 零 Process。由 `NH2-T06` 证明。
5. **redlines**：T07 scan **EXIT 0**（无 caller `workflow_key` 入参、零 `action_branch`、零自由表达式守卫、tail 源唯一、CONTROL 非 scatter join）。由 `NH2-T07` 证明。

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| kind-only：public resolver 不消费 mode/media 作为选图键；合法边经 public resolve 全可达 | `NH2-05` / `NH2-03` | `NH2-T01` / `NH2-T05` | `commit SHA + node PASS + Q7/Q18/T-O-381 + UTC` | `未观察` |
| one shared tail：kind 图不复制 per-strategy tail；CONTROL 后单 canonical 下游 | `NH2-01` / `NH2-03` | `NH2-T02` + T07 scan | `commit SHA + CONTROL suite PASS + compiled subgraph digest report + Q11 + UTC` | `未观察` |
| deterministic route：缺 fact / unknown 不选边；环/重复拒注册 | `NH2-02` / `NH2-04` | `NH2-T03` / `NH2-T04` | `commit SHA + unit logs PASS + Q22/Q8 + UTC` | `未观察` |
| compat：old Execution 按旧 compiled digest 跑完；新 Task kind-only | `NH2-07` | `NH2-T06` | `commit SHA + process sequence PASS + Q18 + UTC` | `未观察` |
| redlines：零 caller key / action_branch / free expression；scan EXIT 0 | `NH2-08` / `NH2-06` | `NH2-T07` | `commit SHA + scan EXIT0 + T-O-377 + UTC` | `未观察` |

PASS 证据四元组形态（执行期填写，本 AP 不伪造 SHA）：`commit SHA + pytest node PASS + Truth/Q + UTC`。

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | §10.1 五条谓词全部为真；unique-binding 围栏仍在；scatter fan-in 语义未改成 XOR |
| 测试 | `NH2-T01..T07` 全 PASS（退出硬闸项四元组齐全）；最低层不低于台账 C |
| 文档 | evidence pack `docs/evidence/new-harvest/AP-NH2/` 含下列**将产生**的文件（执行时写入，现不得预填假 SHA）：`manifest.json`；`tests.txt`；`queries/resolver-kind-only.json`；`queries/compiled-tail-digest.json`；`queries/old-pin-process-sequence.json`；`security/redline-scan.txt`；`migrations/M-NH-03-control.md`；`migrations/M-NH-04-kind-compat.md`；`closure.md` |
| 风险收敛 | `R-F01` 未触发（NH1 已 PASS）；`R-F04` 无 in-flight 409；`R-F10` 哈希相等 |
| 可交付性 | public 切流可合并；NH3 可消费已登记谓词与 kind 图；NH7 可依赖边可达性（仍须自己做 L3/L4） |

### 10.4 NOT-成功识别

> 任一退出硬闸测试 `degraded / 未观察` ⇒ **不得标 `executed`**。

下列情形 **一律不算完成**（final §7.2 + 本 AP 特有）：

1. 6 张 hidden 图能 bootstrap / `resolve_by_key` 成功。
2. 公共 API 调通 `resolve_by_key` 当 kind-only 完成。
3. 用 `human_review_gate` 类比证明 merge。
4. 复用 `scatter_children_join` 等待语义当 XOR。
5. 复制 13 profile / 复制 publication tail 当 kind family（`FG-NH-09`）。
6. 改 unique-binding 围栏做 one-of。
7. 把 503 / monkeypatch / 单 unit 顶替 T05/T06 L2。
8. 本 AP 写了 history 行或 actual S05 却声称 NH3 已交付。
9. NH1-T04 失败后静默换 duplication 继续本 AP。

---

## 11. 执行日志回填（仅 `executed` 状态使用）

> 文档状态为 `draft`，本节省略实填。执行完成后改用 `respond-execution-log` 厚版回填。

- **实际执行摘要**：`{待执行}`
- **Phase 偏差**（逐条带分类）：`{待执行}`
- **阻塞与处理**：`{待执行}`
- **测试发现**（含全绿计数 + 新暴露事实）：`{待执行}`
- **后续 handoff**：`{待执行}` → NH3 fact/history/S05；NH7 10+3 live

---

## 附录 · 修订历史

| 版本 | 日期 | 作者 | 说明 |
|------|------|------|------|
| v0.1 | 2026-08-29 | Grok workflow | 由 final §7 派生 |
| v0.2 | 2026-08-29 | Grok fix-fleet | 吸收已核实 review：T02 跑法去掉不可 collect 的「NH1-T04 生产 node」；T03 删除「抽出纯函数」并强制 L2 UoW 零 browser Process 行；7-profile 期待值仅 kind 激活后改写并点名 `FG-NH-17`；⛔6 CONTROL 只钉 `runtime_materialize.py:513-534` |
