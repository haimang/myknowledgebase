# Nano-Agent 行动计划

> 服务业务簇: `MKB / new-harvest intake-four-channel-live`
> 计划对象: `Chosen-shape validation + 可信 proof baseline（Q10–Q13 / Q18–Q20 / Q26）`
> 类型: `new`
> 作者: `Grok workflow new-harvest-nh1-nh5-action-plans`
> 时间: `2026-08-29`
> 文件位置: `docs/plan/new-harvest/AP-NH1-foundation-contracts-and-proof-baseline.md`（本文件只规定将新建/将修改的 `tests/` 与 **最小可证伪** spike 切片路径；**本轮文档不改生产代码**）
> 上游前序 / closure:
> - `docs/eval/new-harvest/final-execution-plan.md` v1.0 `frozen` §7.1（唯一执行基线 · 台账 A/B/C/D）
> - `docs/eval/new-harvest/pre-charter-qna.md` v1.0 `frozen` · Q10/Q11/Q12/Q13/Q18/Q19/Q20/Q26 · `T-O-390/391/392/393/398/399/400/406`
> - `docs/eval/new-harvest/pre-initial-planning-qna.md` v0.5 `frozen` · `T-O-376/378/381/383`
> 下游交接:
> - `AP-NH2`（kind family / merge CONTROL 生产合同；依本 AP 接口包）
> - `AP-NH3`（typed history / actual S05 生产 migration；依本 AP 接口包）
> - `AP-NH4` / `AP-NH5`（NH1 后并行；消费分母/矩阵/error 包，不消费未证伪的 CONTROL/S05 切片）
> - `AP-NH6`（runtime 生产供给；仅在本 AP `stop-or-go.md=GO` 且 `NH1-T06` 三次 smoke pytest PASS 之后。typed 不可行只写 `STOP`，**不是** T06 PASS）
> - 任一承重 spike 证伪 → **STOP / reopen** `T-O` + final；**禁止**静默换 duplication（`T-O-398`）
> 关联设计 / 调研文档:
> - `docs/eval/new-harvest/final-execution-plan.md` v1.0 §4 / §6 / §7.1 / §9 / §10 `R-F01/F13/F14` / §11.A
> - `docs/eval/new-harvest/assessment-index.md` §2.1 冻结分母命令 · §2.2 `D-01..D-07`
> 冻结决策来源:
> - `docs/eval/new-harvest/pre-charter-qna.md` v1.0（Q10–Q13 / Q18–Q20 / Q26 业主回答 🔒 FROZEN；只读引用；本 action-plan 不填写 Q/A）
> - `docs/eval/new-harvest/pre-initial-planning-qna.md`（`T-O-376/378/381/383`）
> grounding 来源:
> - HEAD `1221aa1` 实测 `path:line`（本 AP §7.1 备注独立核对行号）
> - `docs/eval/new-harvest/reference-anchor/assessment-analysis-01-workflow-graph-and-kind-family.md`
> - `docs/eval/new-harvest/reference-anchor/assessment-analysis-02-s05-two-stage-binding-and-recovery.md`
> - `docs/eval/new-harvest/reference-anchor/assessment-analysis-05-runtime-adapters-readiness-and-security.md`
> - `docs/eval/new-harvest/reference-anchor/assessment-analysis-09-assurance-replay-concurrency-and-compatibility.md`
> 关联 reference-anchor:
> - 上列 RA01 / RA02 / RA05 / RA09（正/反例参考系，**不是**新 Truth）；§7.3 指回真源
> 文档状态: `draft`
> 台账 ID 区间（final §11.A `7.1 AP-NH1`）：`NH1-01..09 / NH1-A01..06 / NH1-T01..07`
> HEAD: `1221aa1`

---

## 0. 执行背景与目标

new-harvest 的产品法已在 QNA 冻结，但 HEAD `1221aa1` **尚未实施** chosen shape：七表仍是单 port 单 binding、CONTROL 只有 `human_review_gate` / `scatter_children_join`、`s05_binding_digest` 在创建时被填成 `domain_binding_digest`、默认组合根无 browser/PDF/OCR 供给。同时既有 e2e 用 `sqlite3.connect` 打开 `persistence_backend="turso"` 文件、检索省略 `namespace_key` 却期待 200——证明基线本身不可信（`T-R-NH-16/22/26`；`FG-NH-05/12`）。

本 AP 是全链 **首门**（final §6 DAG）：先修 harness 谎言，再量冻结分母，再对 owner-chosen 的 selected-output CONTROL、S05 unsealed→sealed-once、runtime 边界做 **可证伪 spike**。类型是 `new`（harness + spike + inventory），**不是** NH2/NH3/NH6 的生产交付。spike 代码可以进入 `tests/` 与 `src/` 的最小切片，但必须标明「**仅当 spike PASS 才允许 NH2/NH3/NH6 把切片升级为生产合同**」。任一承重 spike FAIL → STOP / reopen `T-O` + final，禁止退回 13 张图复制（`T-O-398`）。

- **服务业务簇**：`MKB / new-harvest`
- **计划对象**：Chosen-shape validation + 可信 proof baseline
- **本次计划解决的问题**：
  - 测试谎言：Turso 设置下 sqlite3 直读、检索无 namespace、`status=running` 超时当绿（`T-O-406` / `FG-NH-05/12`）
  - 执行分母未机器锁死：HEAD 4/10/9/3/13/7/6/2 与 16 条 compat 计划必须与 RA `D-01..D-07` diff=0
  - chosen shape 未证伪：selected-output CONTROL、policy/actual S05 分账、local-binary vs S11 multimodal 是否可在七表 + 现 UoW 上落地
- **本次计划的直接产出**：
  - 可信 L2 harness（PersistencePort recovery + Layer-A namespace fixture）
  - 分母 / 合法·非法矩阵 / promptA 三 id 清单
  - CONTROL / S05 / runtime 三次承重 spike 的 PASS **或** typed 不可行 STOP 包
  - `docs/evidence/new-harvest/AP-NH1/` foundation pack（含 NH2–NH6 versioned input/output/error；**不实现**下游 AP）
- **本计划不重新讨论的设计结论**：
  - policy/actual 分账；旧 `s05_binding_digest` 逻辑隔离、不得 backfill；新 actual 为 sealed-once SSOT（来源：Q10 / `T-O-390`）
  - v1 registered `selected-output` CONTROL；optional candidate ports；exactly-one；禁 scatter wait / one-of binding / 整图复制（来源：Q11 / `T-O-391`）
  - fact/history 权威形态在接口包中声明；NH1 只 spike 投影点（来源：Q12 / `T-O-392`）
  - runtime 按 PromptRef+model budget 分界；不锁库名、不锁 pool 数（来源：Q13 / `T-O-393`）
  - 有界 substrate 留在 NH1–NH3；证伪即 stop，禁退回 duplication（来源：Q18 / `T-O-398`）
  - parser 无网 subprocess；browser 生产禁 `--no-sandbox`；pin/SBOM/CVE 为生产前置（来源：Q19 / `T-O-399`）
  - selected-route Outcome 与 actual seal 同 UoW；禁两提交（来源：Q20 / `T-O-400`）
  - L1/L2/L3/L4 不可互换；本 AP 最低层以台账 C 为准（来源：Q26 / `T-O-406`）
  - 四通道 completeness / 假实现禁令 / live 矩阵 / 绑定后 fail-loud（来源：`T-O-376/378/381/383`）

---

## 1. 执行综述

### 1.1 总体执行方式

**先修测试谎言（harness），再量分母与合法矩阵，再 spike chosen shape，最后归档接口包。** 禁止先写生产 CONTROL 注册或 `M-NH-01` 生产 migration（那是 NH2/NH3）。Phase 3 的 spike 只允许最小可证伪切片；失败必须 fail-loud 进入 foundation pack 并 halt DAG，不得把 503 / skip / 单 unit 写成「先做 NH6 再看」。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | 可信 harness | `M` | PersistencePort recovery；Layer-A namespace fixture；去掉 sqlite3-on-Turso 与 422-on-success | `-` |
| Phase 2 | 执行分母与矩阵 | `M` | 锁死 4/10/9/3/13/7/6/2 + 16 compat；合法/非法矩阵；promptA 三 id 清单 | Phase 1（证明手段可信后再量） |
| Phase 3 | chosen-shape spike | `XL` | selected-output CONTROL；S05 legacy/unsealed/sealed CAS；runtime 三次实弹 smoke | Phase 1+2 |
| Phase 4 | foundation pack | `M` | 按 ✅/♻️/🆕/⛔ 归档；发布 NH2–NH6 versioned 接口；失败 STOP | Phase 1–3 |

> `规模` 是描述性提示，不是开工闸。

### 1.3 Phase 说明

1. **Phase 1 — 可信 harness**
   - **核心目标**：后续一切「绿」必须经真实 `PersistencePort`/`UnitOfWork` 与带 `namespace_key` 的检索面；否则分母和 spike 都是假绿。
   - **为什么先做**：`T-O-406` 把 L2 真 UoW 与 L4 namespace 锁成 charter；RA09 已实测 scatter recovery 在 `sqlite3.connect` 处 `disk I/O error`，inline e2e 检索省略 namespace。
2. **Phase 2 — 执行分母与矩阵**
   - **核心目标**：机器锁死 HEAD 分母与两张合法矩阵，并列出 promptA 三 id/hash/readers，供 NH2/NH7 消费。
   - **为什么放在这里**：分母在谎言 harness 上测量无意义；矩阵不依赖 CONTROL 生产图。
3. **Phase 3 — chosen-shape spike**
   - **核心目标**：证伪或确认 Q11/Q10/Q13 的 chosen branch 能在七表 + 现 Outcome UoW 上表达；**不**把 CONTROL/S05/runtime 写成已上线。
   - **为什么放在这里**：分母给出「复制 13 张图」的代价对照；harness 给出可检查的 CAS/query。
4. **Phase 4 — foundation pack**
   - **核心目标**：把 PASS/FAIL 收成 versioned 接口与 STOP 判定，解锁或阻断 NH2–NH6。
   - **为什么放在这里**：接口包是下游唯一输入；禁止「部分绿继续 NH2」。

### 1.4 执行策略说明

- **执行顺序原则**：harness → inventory/matrix → 三次承重 spike（CONTROL / S05 / runtime 可在 Phase 3 内顺序；CONTROL 失败则 S05 投影点仍做完但 **不得**宣称 merge 可行）→ pack。禁止并行开工生产 kind 图或生产 DDL。
- **风险控制原则**：`R-F01`（merge 不可行）与 `T-O-398` 同闸：证伪即 reopen，不准 duplication。`R-F13/F14`：L1 不得顶 L3/L4；Task `succeeded` 不得顶 query。spike 环境缺失 → fail-loud 记入 pack，**禁止 pytest skip 当 PASS**。
- **测试推进原则**：Phase 1/2 短途 L1 + 承重 L2（T02/T03）；Phase 3 spike 按台账最低层（T04 L1/L2、T05 L2、T06 L3）；Phase 4 只归档，不另发明第五层。fault/race/security 是标签（T05 带 F，T06 带 S），不是替代层。
- **文档同步原则**：本 AP 保持 `draft`。执行后只允许回填 §11 与 evidence pack；不得改 QNA / final / RA。接口包写入 `docs/evidence/new-harvest/AP-NH1/`，不回写 Truth。
- **回滚 / 降级原则**：spike 切片不得注册进 `BUILTIN_WORKFLOWS` / 生产 `001_initial.sql`。若须撤回，删除 `src/**/*spike*` 与 `tests/**/test_nh1_*` 即可使 HEAD 行为回到 `1221aa1`。**禁止**把失败 spike 降级成「先做 NH6」。

### 1.5 本次 action-plan 影响结构图

```text
AP-NH1 chosen-shape validation + proof baseline
├── Phase 1: 可信 harness
│   ├── tests/e2e/test_registered_api_scatter.py（删 sqlite3 直读）
│   ├── tests/e2e/test_nh1_fanin_recovery_port.py（PersistencePort/UoW）
│   ├── tests/e2e/test_single_intake_pipeline.py（retrieval 必带 namespace_key）
│   └── tests/e2e/test_nh1_retrieval_namespace.py（省略→422；带 key→hit）
├── Phase 2: 执行分母与矩阵
│   ├── tests/unit/test_nh1_denominator_inventory.py（D-01..D-07 + 16 compat）
│   ├── tests/unit/test_nh1_legal_matrix.py（10+3 合法格 / 七意图非法格）
│   └── promptA 三 id/hash/readers 清单（M-NH-07 输入）
├── Phase 3: chosen-shape spike（非生产）
│   ├── selected-output CONTROL 最小切片（禁 scatter wait / 禁 one-of）
│   ├── S05 legacy/unsealed/sealed 同 UoW CAS 切片（禁 backfill）
│   └── runtime 三次实弹 + 加密 PDF 负例（不锁库名；smoke ≠ NH6 DoD）
└── Phase 4: foundation pack
    ├── docs/evidence/new-harvest/AP-NH1/（manifest/tests/queries/migrations/security/closure）
    └── interfaces/ nh2..nh6 versioned input/output/error
```

---

## 2. In-Scope / Out-of-Scope

> 执行边界来自 final §4 与本 AP 台账；本节不重开 Q10–Q27。

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S-NH-F1]** chosen graph/binding/fact/runtime smoke 与可信 test baseline（final §4.1；Truth `T-O-390..393/398..400/406`）
- **[S1]** PersistencePort/UoW recovery harness；删除 scatter fan-in 测试中的 sqlite3-on-Turso 直读（`NH1-02` / `NH1-T02` / `FG-NH-12`）
- **[S2]** Layer-A namespace fixture；检索省略 key→422、带 key→disposition=ok + hit（`NH1-03` / `NH1-T03` / `FG-NH-05`）
- **[S3]** 冻结执行分母：脚本断言 `4/10/9/3/13/7/6/2`，并枚举 16 条 compat / old key/revision/digest（`NH1-01` / `NH1-T01`；ledger 子步 `4/10/9/3/13/2/16` 中的 `16` = compat 计划）
- **[S4]** 两张合法矩阵（10 strategy + 3 operation；七意图 applicability；非法格有 disposition；禁 7×4）（`NH1-07` / `NH1-T07`）
- **[S5]** promptA 三 id/hash/readers 与旧 snapshot refs，输出 `M-NH-07` 变更/兼容清单（`NH1-08`）
- **[S6]** selected-output CONTROL **spike**（optional candidate ports、durable selection 投影、exactly-one、零/双/缺 fact/环）（`NH1-04` / `NH1-T04`）——**不是** NH2 生产图
- **[S7]** S05 schema/seal **spike**（legacy / unsealed / sealed 可 SQL 区分；同 seal replay；异 seal `ConflictError`；禁 backfill）（`NH1-05` / `NH1-T05`）——**不是** NH3 生产 migration
- **[S8]** runtime 形态 **smoke**（真实 PDF text / SPA render+print / binary model request；负例加密 PDF；记录 pin/limits/license/CVE/error）（`NH1-06` / `NH1-T06`）——**smoke 成功 ≠ NH6 DoD**
- **[S9]** foundation pack + NH2–NH6 versioned 接口；失败即 stop（`NH1-09`）

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O-NH-01]** live connector/cookie/tunnel、第五 source kind、caller `workflow_key`、`action_branch`
- **[O-NH-02]** cuts/g0 算法重开、按通道复制 publication tail、前端/answer generation
- **[O-NH-03]** existing-object new-cleaner/validator upgrade（`T-O-401`；须未来新 owner-gate）
- **[O-NH-04]** raw object GET/list/presign/browser（`T-O-396`）
- **[O-NH-05]** experiment 发车/评分；骨架非 DoD（`T-O-380`）
- **[O-NH-06]** 通用 Workflow JOIN/DSL/自由表达式/动态 loader；云 OCR/CF/R2/SMCP/Workers runtime
- **[O1]** NH2 生产 kind 图、kind-only public resolver 切换、旧 13 key 退役
- **[O2]** NH3 生产 `M-NH-01`/`M-NH-02` migration、typed history 权威行落生产 DDL
- **[O3]** NH6 生产隔离/SBOM 闭环、把任一 PDF/browser 库名写入 `pyproject.toml`
- **[O4]** NH7 10+3 live-to-vector；NH8 七意图生产 error 面；NH9 closed-set mega
- **[O5]** 生产默认 `--no-sandbox`；raw GET；把 `s05_binding_digest` 原地改解释为 actual

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| harness 去 sqlite3 / 补 namespace | `in-scope` | `S-NH-F1` + `T-O-406`；否则后续绿不可信 | 无；本 AP 硬闸 |
| 分母 4/10/9/3/13/7/6/2 与 16 compat | `in-scope` | `T-R-NH-01/03`；index `D-01..D-07` | HEAD 变则先修订 assessment-index，不在 AP 内改分母 |
| selected-output CONTROL spike | `in-scope` | Q11 `T-O-391`；证伪闸 `T-O-398` | spike FAIL → STOP/reopen，不改选 duplication |
| S05 生产 migration `M-NH-01` | `out-of-scope` | 属 NH3；本 AP 只 spike 三类行 + 同 UoW CAS | NH1-T05 PASS 后由 NH3 执行 |
| kind 家族 3+scatter 生产切流 | `out-of-scope` | 属 NH2；本 AP 只冻结接口与分母对照 | NH1-T04 PASS 后由 NH2 执行 |
| PDF/browser 库名与 pool 个数 | `out-of-scope` | Q13 `T-O-393` 不锁库名/pool | NH6 在 smoke 可行后另选，仍须 pin/SBOM/CVE |
| 10+3 live / 七意图生产 / campaign mega | `out-of-scope` | NH7/NH8/NH9；`S-NH-F7..F9` | 不得用本 AP smoke/unit 顶替 |
| raw GET / existing upgrade / 通用 JOIN | `out-of-scope` | `O-NH-03/04/06` | 未来须新 owner-gate |
| 第五 kind / caller `workflow_key` | `out-of-scope` | `O-NH-01`；HEAD resolver 已禁 key（正例，保围栏） | 不得 reopen |

---

## 3. 业务工作总表

> 编号列使用 final 台账 A 的 `NH1-nn`（禁止改成只剩 `P1-01`）。每个工作项含不可约三元组：file:line / 收口目标 / Test-ID。

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| `NH1-01` | Phase 2 | 冻结执行分母 | `add` | `src/services/registry.py:171-208`；`src/contracts/intake/strategies.py:15-151`；`intake/__init__.py:20-30`；`intake/api/registry.py:73-104`；`src/workflows/lsrag_definition.py:929-1069`；`src/workflows/builtin_scatter.py:352-380,571-599`；`src/workflows/builtin_lsrag.py:40-44`；新建 `tests/unit/test_nh1_denominator_inventory.py` | 机器断言与 RA `D-01..D-07` diff=0：kinds=4、strategies=10、capabilities=9、ops=3、single=13、public=7、unselectable=6、scatter=2；并枚举 16 条 compat old key/revision/digest | `NH1-T01` | `medium` |
| `NH1-02` | Phase 1 | PersistencePort recovery | `update` | `tests/e2e/test_registered_api_scatter.py:7,26-33,264-273,327-347,366-373`；`src/persistence/ports.py:10-27`；`src/persistence/turso/port.py:145`；正例 `tests/integration/test_ns5_turso_mainchain.py:106-125`；新建 `tests/e2e/test_nh1_fanin_recovery_port.py` | fan-in crash 后经真实 UoW 恢复父 Execution；该测试文件无 `import sqlite3`、无对 Turso 文件的 `sqlite3.connect` | `NH1-T02` | `high` |
| `NH1-03` | Phase 1 | Retrieval namespace | `update` | `tests/e2e/test_single_intake_pipeline.py:121-130,382-394`；`src/services/retrieval/retrieval_request.py:265-270`（取值 `:263-264`）；正例 `tests/integration/test_ns5_turso_mainchain.py:118-138`；新建 `tests/e2e/test_nh1_retrieval_namespace.py` | 省略 namespace → HTTP 422 `RETRIEVE_SCHEMA_NAMESPACE_REQUIRED`；带 Layer-A key → 200 + `disposition=ok` + 非空 hit/proof；无 `status=running` 超时当绿；该 🔱 文件无 Turso 下 `sqlite3.connect` | `NH1-T03` | `high` |
| `NH1-04` | Phase 3 | Merge CONTROL spike | `add` | 反例 `src/contracts/workflow/models.py:496-497`；`src/runtime/workflow/runtime_materialize.py:505-514`；围栏 `src/contracts/workflow/models.py:245-258,389-443`；optional port `src/contracts/workflow/models.py:113-120`；optional skip `src/runtime/workflow/runtime_materialize.py:435-441`；DDL unique `src/persistence/migrations/001_initial.sql:1770-1771`；新建 `tests/unit/test_nh1_selected_output_control.py`、`tests/integration/test_nh1_merge_control.py`；最小切片 `src/runtime/workflow/selected_output.py`（**SPIKE-ONLY**） | 零/一/双候选、缺 fact、环均 fail-loud 或 exactly-one；不复制 tail；不重跑 guard；不 wait 未 materialize 分支；**未**写入 `BUILTIN_WORKFLOWS` | `NH1-T04` | `high` |
| `NH1-05` | Phase 3 | S05 schema/seal spike | `add` | 反例 `src/runtime/task/task_create.py:179-180,337-340`；`src/persistence/migrations/001_initial.sql:245-246`；正例 `src/runtime/workflow/runtime_outcome.py:88-137`；`src/contracts/common/errors.py:92-94`；Command 反例 `src/runtime/workflow/runtime_core.py:888-917`；新建 `tests/integration/test_nh1_s05_seal_cas.py`；最小切片 `src/runtime/binding/actual_s05_spike.py`（**SPIKE-ONLY**） | 三类行可 SQL 区分（legacy alias / unsealed / sealed）；同 seal replay；异 digest → `ConflictError` 409；旧 64-hex 不得当 sealed actual；**未**改生产 `001_initial.sql` | `NH1-T05` | `high` |
| `NH1-06` | Phase 3 | Runtime smoke | `add` | 反例 `api/app.py:330-345`；`pyproject.toml:13-21`；`src/runtime/intake/core.py:45-51,66-70`；`src/runtime/intake/types.py:144-171`；`src/contracts/inference/models.py:96-108`；`src/runtime/health.py:16-26`；新建 `tests/e2e/test_nh1_runtime_smoke.py` | 三次实弹 pytest PASS（真实 binary/process 成功）并有加密 PDF 负例；记录 pin/limits/license/CVE/isolation；环境缺失 fail-loud 而非 skip；typed 不可行只进 `runtime-infeasible.md` + `stop-or-go.md=STOP`，**不是** T06 PASS；**不**把库名写入生产依赖 | `NH1-T06` | `high` |
| `NH1-07` | Phase 2 | 两张合法矩阵 | `add` | `src/contracts/intake/strategies.py:15-151`；`intake/api/registry.py:73-104`；`src/contracts/api/models.py:278-286`；`src/contracts/workflow/models.py:264`；新建 `tests/unit/test_nh1_legal_matrix.py` | registry 生成 10 strategy + 3 op 合法格；七意图非法格有 disposition/code；禁止 7×4 笛卡尔积 | `NH1-T07` | `medium` |
| `NH1-08` | Phase 2 | Prompt inventory | `add` | `src/contracts/intake/strategies.py:63-147`；`src/services/registry.py:54-79`；`src/services/config_snapshots.py:57-59`；`src/services/prompt_profiles.py:49-50`；`data/prompts/prompt-a-clean-v1.md`；`data/prompts/clean/promptA.clean.v1.md`；`data/prompts/clean/promptA.documentation.default.v1.md` | 列出三 promptA id/hash/readers 与旧 snapshot refs；输出 `M-NH-07` 变更/兼容清单（**不锁对齐方案**） | `NH1-T01`（清单稳定性） | `medium` |
| `NH1-09` | Phase 4 | Foundation pack | `add` | 新建 `docs/evidence/new-harvest/AP-NH1/`（见 §10.3 文件名）；消费 Phase 1–3 产物 | pack 含 NH2–NH6 versioned input/output/error；`stop-or-go.md=GO` 当且仅当 `NH1-T01..T07` 全 PASS；证伪 FAIL 只 halt DAG（不是把 FAIL 写入台账 C PASS 列）；无「部分绿继续」 | `NH1-T01`..`NH1-T07` 归档 | `high` |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — 可信 harness

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH1-02` | PersistencePort recovery | **高风险 / 🔱 整文件 Port 化**：a) 从 `tests/e2e/test_registered_api_scatter.py` **整文件**删除 `import sqlite3` 以及对 `tmp_path/"mkb.sqlite3"` 的 `sqlite3.connect`（今日 `:7` import、`:26-33` 把 `persistence_backend="turso"` 却用 sqlite3、`:264-273` 属 `test_registered_api_three_raw_provider_operations_map_seal_and_persist_semantics` 的 process 直读、`:327-347` crash 注入、`:366-373` membership 计数）。删除模块 import 要求同文件其它用例一并改 Port，不得只改 recovery 函数却声称整文件无 sqlite3。b) crash 注入与事后查询改走 `PersistencePort.transaction()` → `UnitOfWork.execute/fetchone`（`src/persistence/ports.py:10-27`）；Turso 后端必须走 `TursoPersistence.transaction`（`src/persistence/turso/port.py:145`），模式对齐 `tests/integration/test_ns5_turso_mainchain.py:106-125`。c) 新建 `tests/e2e/test_nh1_fanin_recovery_port.py`：子 Process 已 terminal、父 Execution `waiting/scatter_children` 时经 UoW 把 Task 打回 `running` 并唤醒 repair，断言父 exactly-once `succeeded` 且 `proof_ref` 非空。d) 负例：scatter 整文件 **与** 新文件源码扫描均不得出现 `sqlite3.connect` / `import sqlite3`。e) **不**借此机会重写全仓其它 e2e 的 sqlite3（`test_ns2_dispatch_lanes.py` 等交 NH9 `FG-NH-12` 扫尾）。未 Port 化的 scatter recovery **不得**当 T02 证据。 | `tests/e2e/test_registered_api_scatter.py:7,26-33,264-273,327-347,366-373`；`src/persistence/ports.py:10-27`；新建 `tests/e2e/test_nh1_fanin_recovery_port.py` | 在 `persistence_backend="turso"` 下 recovery 不再 `disk I/O error`；产品 fan-in 修复经 Port 可观察 | `NH1-T02` | 无 sqlite3 直连 Turso 路径；repair 一次完成；required child 失败不能被 sibling 掩盖（既有 scatter 失败收集仍回归） |
| `NH1-03` | Retrieval namespace | **高风险 / 🔱**：a) 修正 `tests/e2e/test_single_intake_pipeline.py` 两处 `retrieval:search` body（`:121-130` 与 `:382-394`），补 Port 读出的 `namespace_key`（或 `namespace_uuid`）。b) 删除该文件 Turso 设置下的 sqlite3 直读（`:6` import、`_assert_d04_full_chain` `:150`、live-profile `:401-416`），改 `PersistencePort.transaction()`。c) Layer-A fixture：经 PersistencePort 读 `mkb_vector_namespaces` 的 active `namespace_key`（正例 `tests/integration/test_ns5_turso_mainchain.py:118-138`），禁止硬编码假 key。d) 新建 `tests/e2e/test_nh1_retrieval_namespace.py`：同一黄金文档，省略 namespace 断言 422 + `RETRIEVE_SCHEMA_NAMESPACE_REQUIRED`（服务端 raise 块 `src/services/retrieval/retrieval_request.py:265-270`；取值 `:263-264`）；带 key 断言 200、`disposition=="ok"`、hit 正文与 `traceback_status=="resolved"`。e) 超时窗口内若 Task 仍 `status=running` → 失败，不得当绿。f) 不得用 Task `succeeded` 或 `publication_ready` 顶替 hit（`FG-NH-03/04`）。g) T03 PASS 节点不得再执行 `sqlite3.connect`。`local_mock_settings`（`tests/local_runtime.py:10-21`，默认 turso 的 CI waiver）不得当 T03 default-root L4 组合根，除非另开带期限的 owner waiver（且不得覆盖 `T-O-376/378/381/383`）。 | `tests/e2e/test_single_intake_pipeline.py:6,121-130,150,382-416`；`src/services/retrieval/retrieval_request.py:265-270`；新建 `tests/e2e/test_nh1_retrieval_namespace.py` | 省略必 422；带 key 必真实命中；🔱 文件无 sqlite3 直读 | `NH1-T03` | 无 422-on-success；无 running 超时当绿；L2/L4 最低层满足 |

### 4.2 Phase 2 — 执行分母与矩阵

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH1-01` | 冻结执行分母 | **♻️ 沿用 index 脚本**：a) 把 `assessment-index.md` §2.1 冻结分母命令搬进 `tests/unit/test_nh1_denominator_inventory.py`（import `DEFAULT_SOURCE_KINDS` / `CLEAN_STRATEGY_DEFINITIONS` / `_REGISTERED_CLEAN` / `REGISTERED_PROVIDER_OPERATIONS` / `BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW`+`BUILTIN_SOURCE_PROFILE_WORKFLOWS` / `SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS` / scatter root+child）。b) 断言 `4/10/9/3/13/7/6/2` 与 RA `D-01..D-07` 逐项相等。c) 另数 `BUILTIN_EXECUTION_COMPATIBILITY_WORKFLOWS`（`builtin_lsrag.py:40-44` = 2 historical + 13 NS1 pre-markdown + 1 scatter pre-markdown = **16**），输出 old `workflow_key` / `revision_number` / `compiled_digest` 清单。d) 负例：不得把 13 profile 写成 kind family（`FG-NH-09`）；diff≠0 则 FAIL，禁止改期待值。 | 见 §3 `NH1-01` 行 | 分母机器锁死；compat 16 条可归档 | `NH1-T01` | 与 RA 分母 diff=0；16 条 old key 可被 NH2 compat 消费 |
| `NH1-07` | 两张合法矩阵 | **✅/🆕**：a) 从 `CLEAN_STRATEGY_DEFINITIONS` 生成 10 格 strategy 矩阵（channel / capability / llm_required / browser_required / prompt_key）。b) 从 `REGISTERED_PROVIDER_OPERATIONS` 生成 3 operation 格。c) 从 `TaskCreateRequest.request_intent` 七值（`src/contracts/api/models.py:278-286`）生成 applicability：仅 `intake.ingest` 按 kind 分叉，其余 intent 非法格必须有 disposition/code，**禁止** 7 intents × 4 kinds 笛卡尔积（`FG-NH-15`；`T-R-NH-21`）。d) 矩阵 digest 稳定；非法格不得标 live。 | `strategies.py:15-151`；`intake/api/registry.py:73-104`；`src/contracts/api/models.py:278-286`；新建 `tests/unit/test_nh1_legal_matrix.py` | 合法格闭集 + 非法格 fail-loud 表 | `NH1-T07` | 10+3 合法；非法格有 disposition；无 7×4 |
| `NH1-08` | Prompt inventory | **✅/♻️**：a) 枚举三套 promptA 默认 id：`promptA.default`（`strategies.py:63-147` + `registry.py:57,68` → `data/prompts/prompt-a-clean-v1.md`）、`promptA.clean`（`config_snapshots.py:58` → `clean/promptA.clean.v1.md`）、`promptA.documentation.default`（`prompt_profiles.py:50` → `clean/promptA.documentation.default.v1.md`）。b) 计算三文件 SHA-256 与读者（strategy 表 / snapshot 默认 / documentation profile）。c) 列出旧 snapshot 可能冻结的 prompt refs。d) 输出 `M-NH-07` 变更/兼容清单：**不对齐方案做选择**（QNA 已把 id 对齐标执行延期）；只证明三哈希互斥，防止 NH7 一接 LLM 就 `PROMPT_HASH_MISMATCH` 却无清单。 | 见 §3 `NH1-08` 行 | 三 id 三哈希清单进 evidence | `NH1-T01` | 三 SHA 互斥可复现；readers 点名；无「catalog 有行=可绑 strategy」 |

### 4.3 Phase 3 — chosen-shape spike

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH1-04` | Merge CONTROL spike | **净新 / 高风险**：a) 在 **测试图**（不得写入 `BUILTIN_WORKFLOWS`）上注册 CONTROL `control_key` 字面仅用于 spike（建议 `selected_output`），候选端口 `required=False`（`WorkflowPortDefinition.required`，`models.py:118-120`），下游 seal/tail 仍单 binding 接 CONTROL 的单一 output port——从而 **保** `models.py:496-497` 与 `ux_workflow_binding_slot`（`001_initial.sql:1770-1771`）围栏，**不**做 one-of binding。b) 选边结果必须先作为 durable selection（route/selection proof 行或 test UoW 写入的 selection digest）存在；CONTROL 运行时 **只投影** 该 proof，禁止再执行 guard、禁止调用 `scatter_children_join` 等待语义（`runtime_materialize.py:505-512`）。c) 单命中：下游 port 拿到该 candidate 的 manifest digest。d) 零命中：fail-loud（除非该 CONTROL **版本** 登记 fallback，fallback 进入 compiled digest）。e) 双命中：完整性失败，不得「任选一个」。f) 缺 representation fact：表示类谓词 fail-closed（本 spike 只证明投影点拒绝缺 fact，不实现 NH2 生产谓词闭集）。g) 环/自边：继续由现编译器拒绝（`models.py:389-390,432`）。h) 最小切片 `src/runtime/workflow/selected_output.py` 文件头标注 `SPIKE-ONLY · AP-NH1 · production upgrade = AP-NH2 after NH1-T04 PASS`。i) 失败路径：若七表无法在不改 unique 约束的前提下投影 exactly-one → 记 typed 不可行并 **STOP**，禁止改去复制 13 张 tail（`FG-NH-09`）。 | 见 §3 `NH1-04` 行 | spike 证明 CONTROL 可行 **或** 明确证伪 | `NH1-T04` | exactly-one；不复制 tail；不重跑 guard；零/双 fail-loud |
| `NH1-05` | S05 schema/seal spike | **净新 / 高风险**：a) **禁止** 改生产 `001_initial.sql`。测试库 `migrate()` 之后用 spike helper 增加 **测试会话内** 可空 `actual_binding_digest` / `actual_binding_state` / `seal_generation`（或等价三列），旧 `s05_binding_digest` 只以 `legacy_policy_alias_digest` 暴露。b) 建三类样本：legacy 行 = 今日 HEAD 形状（`s05=domain` NOT NULL，无 actual state，`task_create.py:179-180`）；unsealed = policy 已冻、actual NULL + state=`unsealed`；sealed = actual 非空 + state=`sealed` + generation=1。c) unsealed→sealed 必须与 Outcome commit **同一** `UnitOfWork`（复用 `runtime_outcome.py:88-137` 线性化点）；commit 后才允许后续 clean dispatch。d) 同 seal/digest replay 返回原 sealed 行，不双写。e) 异 route/digest 第二次 seal → `ConflictError`（`errors.py:92-94`，HTTP 409）。f) 禁止用 domain 64-hex backfill actual（`FG-NH-08`）。g) 传播只读 actual：spike 断言 Snapshot/Gate 读方在 sealed 后不得再复制 legacy alias 当 actual。h) `src/runtime/binding/actual_s05_spike.py` 标注 `SPIKE-ONLY · production migration = AP-NH3 M-NH-01 after NH1-T05 PASS`。i) full_task exact 继承只 **记录接口**（`T-O-401`），本 AP 不实现 restart 生产路径。 | 见 §3 `NH1-05` 行 | 三类可分；同 UoW CAS；异 seal 冲突 | `NH1-T05` | SQL 三类可区分；二次异 digest ConflictError；旧 64-hex ≠ sealed |
| `NH1-06` | Runtime smoke | **净新 / 高风险**：a) 新建 L3 default-root e2e `tests/e2e/test_nh1_runtime_smoke.py`，经 `create_app()`，**禁止** monkeypatch `_http_fetcher/_browser_fetcher/_clean_llm`（`FG-NH-01`）。b) 实弹 1：真实 PDF **text layer** 字节进入 local parser port（不是 `GenerateRequest.input_text`，`inference/models.py:96-108`）。c) 实弹 2：本地 fixture SPA → render + print-to-PDF（print 产出必须是 `%PDF-` bytes，不得伪造 `rendered` HTML）。d) 实弹 3：binary model request（Vision/DU 形状：PromptRef + media + digest/handle），证明 text-only facade 不够。e) 负例：加密/无层 PDF → typed 错误，**不得**空正文成功（`FG-NH-06`：空/空白 `clean_text` 不得 `succeeded`）、不得盗用 `CLEAN_OCR_CAPABILITY_UNAVAILABLE` 冒充「已观察无层」（HEAD `types.py:154-158` 是反例，smoke 必须露出该谎言）。f) 记录：binary pin、resource limits、license、CVE baseline、isolation 形态（parser 无网 / browser non-root / 生产禁 `--no-sandbox`）。g) **不锁库名、不锁 pool 数**；不得把任何 PDF/browser/OCR 包写入生产 `pyproject.toml`。h) 环境缺失（无 binary/模型）→ 测试 **FAIL**（非 skip，`FG-NH-02`）；写出 `runtime-infeasible.md` 并触发 NH1-09 `stop-or-go.md=STOP`。不可行 = AP 未完成 / DAG halt，**禁止**写入 T06 PASS 列或「runtime 形态可行」收口行。i) 三次 pytest PASS **不等于** NH6 live DoD（`FG-NH-11`：import/which/models-list 仍不够生产）。 | 见 §3 `NH1-06` 行 | 三次 smoke pytest PASS；证伪只 STOP | `NH1-T06` | 有 pin/SBOM/负例；无 skip-as-PASS；无库名冻结；T06 PASS ≠ infeasible.md |

### 4.4 Phase 4 — foundation pack

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH1-09` | Foundation pack | a) 收集 T01–T07 的 pytest node、exit code、UTC、HEAD SHA。b) 按 ✅/♻️/🆕/⛔ 归档每个锚的处置（§7）。c) 发布 NH2–NH6 versioned input/output/error 文件（§10.3）；接口只冻结已证伪或已 CITE 的形状，**不实现**下游。d) 任一承重 spike（T04/T05/T06）FAIL 或 typed 不可行 → `stop-or-go.md` 写 `STOP` 并指出须 reopen 的 `T-O`；**禁止**部分绿继续 NH2。e) 不伪造已产生的 SHA。 | `docs/evidence/new-harvest/AP-NH1/` | 下游可消费的 versioned 包 + 明确 GO/STOP | `NH1-T01`..`NH1-T07` | pack 文件齐；GO 当且仅当 T01–T07 全 PASS |

---

## 5. Phase 详情

### 5.1 Phase 1 — 可信 harness

- **Phase 目标**：把 recovery 与 retrieval 的证明手段修到 `T-O-406` 的 L2 真 UoW / L4 namespace，使后续分母与 spike 的绿可信。
- **本 Phase 对应编号**：`NH1-02` / `NH1-03`
- **本 Phase 新增文件**：`tests/e2e/test_nh1_fanin_recovery_port.py`；`tests/e2e/test_nh1_retrieval_namespace.py`
- **本 Phase 修改文件**：`tests/e2e/test_registered_api_scatter.py`（**整文件**去掉 sqlite3 直读与 crash 注入）；`tests/e2e/test_single_intake_pipeline.py`（两处 search 补 `namespace_key`；删除 `:150`/`:401` `sqlite3.connect`）
- **本 Phase 删除文件**：无（只删测试内 sqlite3 用法，不删用例）
- **具体功能预期**：
  1. `persistence_backend="turso"` 时，fan-in recovery 经 `persistence.transaction()` 读写 `mkb_executions` / `mkb_tasks`，不再 `sqlite3.connect(database_path)`。
  2. 子已 terminal、父 `waiting` 的崩溃窗修复 exactly-once，父 `succeeded` 且 `proof_ref` 非空。
  3. `test_registered_api_scatter.py` 与 `test_nh1_fanin_recovery_port.py` 源码均不含 `import sqlite3`。
  4. `retrieval:search` 省略 namespace → 422 `RETRIEVE_SCHEMA_NAMESPACE_REQUIRED`（这是 **服务端正例**，raise 块 `retrieval_request.py:265-270`；测试必须覆盖负例）。
  5. 带 Layer-A key 的 search → 200、`disposition=ok`、hit 正文匹配、traceback resolved。
  6. T03 🔱 文件不得再 `sqlite3.connect`；超时仍 `running` → 测试 FAIL；不得把 HTTP 200 但空 results 写成命中；不得 sqlite3 失败时改断言期待值（`FG-NH-17`）。
- **对应测试台账项**：`NH1-T02` / `NH1-T03`（详见 §8）
- **收口标准**：harness 可信谓词（§10.1 第 1 条）
- **本 Phase 风险提醒**：全仓其它 e2e 仍有 sqlite3（`test_ns2_dispatch_lanes.py` 等）；本 Phase **不**宣称 `FG-NH-12` campaign 级清零，只清 NH1 recovery（scatter 整文件）与 T03 retrieval 证明路径。

### 5.2 Phase 2 — 执行分母与矩阵

- **Phase 目标**：锁死 HEAD 分母、两张合法矩阵、promptA 三 id 冲突面，给 NH2/NH7/NH8 可 diff 的基线。
- **本 Phase 对应编号**：`NH1-01` / `NH1-07` / `NH1-08`
- **本 Phase 新增 / 修改 / 删除文件**：新建 `tests/unit/test_nh1_denominator_inventory.py`、`tests/unit/test_nh1_legal_matrix.py`；不改 registry 生产数据
- **具体功能预期**：
  1. 分母命令与 index §2.1 同构，断言 `D-01..D-07`。
  2. 16 条 compat workflow 的 key/revision 可序列化。
  3. 10+3 合法格由 registry **生成**而非手抄。
  4. 七意图非法格有稳定 disposition，无 7×4 表。
  5. 三 promptA 文件 SHA 互斥，读者点名 strategy / snapshot / documentation。
  6. 失败：分母漂移 → FAIL（改测试期待值 = `FG-NH-17`）。
- **对应测试台账项**：`NH1-T01` / `NH1-T07`
- **收口标准**：inventory 与 matrix digest 稳定
- **本 Phase 风险提醒**：13 single + 7 public 容易被误写成「已有 kind 家族」；本 Phase 只测量，不切流。

### 5.3 Phase 3 — chosen-shape spike

- **Phase 目标**：在不破坏七表围栏、不写生产 migration、不锁库名的前提下，证伪或确认 Q11/Q10/Q13 chosen branch。
- **本 Phase 对应编号**：`NH1-04` / `NH1-05` / `NH1-06`
- **本 Phase 新增文件**：`tests/unit/test_nh1_selected_output_control.py`；`tests/integration/test_nh1_merge_control.py`；`tests/integration/test_nh1_s05_seal_cas.py`；`tests/e2e/test_nh1_runtime_smoke.py`；`src/runtime/workflow/selected_output.py`（SPIKE-ONLY）；`src/runtime/binding/actual_s05_spike.py`（SPIKE-ONLY）
- **本 Phase 修改文件**：无生产 builtin / 无生产 DDL。若 runtime 需要一处 CONTROL 分发挂钩，仅允许在 `runtime_materialize.py` 对 **未登记生产 key** 的未知 CONTROL 给出可测试的 spike 分支，且默认生产路径仍只接受 `human_review_gate` / `scatter_children_join`（今日 `:505-514`）。
- **本 Phase 删除文件**：无
- **具体功能预期**（净新高风险 ≥5，含失败）：
  1. 测试图编译：optional 多 candidate port + 单 CONTROL output + 单 tail binding **通过**；给同一 process input 两条 prior_output binding **仍拒绝**（保围栏）。
  2. 一候选成功：CONTROL 投影该 digest；tail 不被复制。
  3. 零候选：fail-loud（无登记 fallback）或走登记 fallback（fallback 进入 compiled digest）。
  4. 双候选非空：完整性失败，不任选。
  5. 缺 fact：不得匹配表示守卫；不得暗升。
  6. 环/自边：registration `ValueError`（现编译器）。
  7. CONTROL 不调用 scatter wait；不重跑 guard。
  8. S05 三类行 SQL 可区分；unsealed→sealed 与 Outcome 同 UoW。
  9. 同 seal replay；异 seal `ConflictError`；domain 64-hex 查询不得返回 `state=sealed`。
  10. PDF text / SPA print / binary model 三次实弹成功 **或** 每条 typed 不可行；加密 PDF 负例；无 `--no-sandbox` 作为生产默认建议。
  11. 失败/降级：任一条承重预期无法在有界切片内满足 → STOP/reopen，禁止 duplication / 两提交 / 锁库名绕过。
- **对应测试台账项**：`NH1-T04` / `NH1-T05` / `NH1-T06`
- **收口标准**：§10.1 第 2–4 条谓词
- **本 Phase 风险提醒**：`R-F01` merge 不可行阻塞全 DAG；`R-F05` 供应链不可部署必须 typed 报告；执行者不得把 SPIKE 模块 import 进 `BUILTIN_WORKFLOWS`。

### 5.4 Phase 4 — foundation pack

- **Phase 目标**：把 Phase 1–3 收成可交接的 GO/STOP 与 versioned 接口。
- **本 Phase 对应编号**：`NH1-09`
- **本 Phase 新增 / 修改 / 删除文件**：仅 `docs/evidence/new-harvest/AP-NH1/`（执行期产生；本 AP 只规定文件名）
- **具体功能预期**：
  1. `manifest.json` 列出 work/test IDs、Truth/Q、commit、UTC。
  2. `interfaces/` 含 NH2–NH6 的 input/output/error schema 或等价 Markdown 合同。
  3. `stop-or-go.md` 二元：GO 当且仅当 T01–T07 全 PASS。
  4. FAIL 时指出 reopen 的 `T-O-390/391/393/398` 之一，禁止换方案叙事。
- **对应测试台账项**：`NH1-T01`..`NH1-T07` 归档
- **收口标准**：§10.1 第 5 条
- **本 Phase 风险提醒**：不得伪造 SHA；不得把 draft AP 标 executed。

---

## 6. 依赖的冻结设计决策（只读引用）

> 只引 Q 编号 + T-O-ID 与对本计划的影响。不复制业主长文，不改口，不填新 Q/A。GPT/Grok 槽不是 Truth。

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Q10 `T-O-390` | `docs/eval/new-harvest/pre-charter-qna.md` §5 | `NH1-05`/`NH1-T05` 必须能区分 legacy alias / unsealed / sealed；旧列不得 backfill | 无法区分 → STOP；禁止原地翻义 |
| Q11 `T-O-391` | 同上 | `NH1-04`/`NH1-T04` = registered selected-output CONTROL；optional ports；exactly-one；禁 scatter wait / one-of | 不可表达 → STOP/reopen；禁 duplication |
| Q12 `T-O-392` | 同上 | 接口包声明 fact/history 权威形态；NH1 **只 spike 投影点**（缺 fact fail-closed） | 不在本 AP 落生产 history DDL（NH3） |
| Q13 `T-O-393` | 同上 | `NH1-06` 分 local binary vs S11 multimodal；不锁库名/pool | 形态不可行 → typed STOP，不锁替代库 |
| Q18 `T-O-398` | 同上 | 本 AP 是 stop-gate；失败 reopen；不外置通用引擎 | 证伪不得继续 NH2 |
| Q19 `T-O-399` | 同上 | smoke 必须记录 isolation/license/CVE；生产 `--no-sandbox` 禁 | 缺记录 = T06 FAIL |
| Q20 `T-O-400` | 同上 | seal spike 必须同 UoW；禁两提交 | 两提交窗口出现 → T05 FAIL / STOP |
| Q26 `T-O-406` | 同上 | harness 修到 L2 真 UoW；retrieval 带 namespace；不可用 L1 顶 L3 | 降层/改期待值 = 不得收口 |
| `T-O-376` | `pre-initial-planning-qna.md` | 禁止 503 当通道 DoD；smoke 成功仍非四通道接通 | 不得宣称 NH7 完成 |
| `T-O-378` | 同上 | 假 PDF / OCR 盗码 / monkeypatch / 空 clean 不得冒充完成 | T06 负例必须抓住 |
| `T-O-381` | 同上 | 10+3 是 live 闭集分母；本 AP 只生成矩阵不激活 | 激活属 NH7 |
| `T-O-383` | 同上 | 绑定后不换工人；异 seal ConflictError；空正文非成功 | T05/T06 失败法 |
| `T-O-386` | 同上 | promptA 仅 LLM；`NH1-08` 清点三 id 冲突 | 不对齐方案做选择 |
| `T-O-401` | pre-charter Q21 | existing upgrade OOS；full_task exact 只进接口备注 | 本 AP 不实现 restart 生产 |
| `T-R-NH-01/03/08/16/18/22/26` | final §2 | HEAD 分母、selector、prompt 冲突、假绿、S05 盗用、supply=0 | 与 RA 冲突则先修 index，不改期待值 |

---

## 7. 内置 Reference-Anchor 锚区

> 行号以本 AP 作者在 HEAD `1221aa1` 独立 `read_file` 为准。相对专用 PROMPT 的漂移已在备注标出。

### 7.1 锚表（本计划工作要落在哪些既有代码 / 新建点上）

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| `NH1-A02` | `src/runtime/workflow/runtime_outcome.py:88-137` | Outcome 与 caller `validate_and_commit` 同 UoW；Process fence CAS | `NH1-05` 线性化点：actual seal 扩进此事务 | `✅ 复用` | actual **尚未**接入；禁止另开第二提交 |
| `NH1-A06` | RA01 §6/§9；RA02 §6/§9；RA05 §6/§9 | 净新 contract / 验收格栅草案 | `NH1-04/05/06/09` spike 与接口包形状 | `🆕 净新` | 🔶参考系不是 Truth；不引外部 runtime 栈 |
| `NH1-H01` | `src/contracts/workflow/models.py:389-443` | 禁自边；DFS 无环；start 可达；unreachable 拒绝 | `NH1-04` 保围栏；环负例 | `✅ 复用` | PROMPT 行号命中；不扩表达式 |
| `NH1-H02` | `src/contracts/workflow/models.py:245-258` | 5 个 `predicate_type`；`operator` **仅 `eq`** | `NH1-04` 保围栏；NH1 不扩谓词字面 | `✅ 复用` | `D-08` |
| `NH1-H03` | `src/services/workflow_registry.py:78-104` | `resolve_for_source`：caller 只给 purpose + kind/profile，**不能**选 `workflow_key` | 全 AP redline；接口包写明禁 key | `✅ 复用` | 已建好，别重写为 key 选择器 |
| `NH1-H04` | `src/persistence/ports.py:10-27` | `UnitOfWork` + `PersistencePort.transaction` | `NH1-02/03/05` 唯一合法读口 | `✅ 复用` | 禁止测试 import 驱动 |
| `NH1-H05` | `src/persistence/turso/port.py:145` | Turso 真事务入口 | `NH1-02` recovery 必须走这里 | `✅ 复用` | 与 sqlite 直读对打 |
| `NH1-H06` | `src/contracts/workflow/models.py:113-120` | `WorkflowPortDefinition.required` 默认 True | `NH1-04` 候选端口必须 `required=False` | `✅ 复用` | Grok 槽非 Truth；业主冻结的是 optional ports |
| `NH1-H07` | `src/runtime/workflow/runtime_materialize.py:435-441` | optional prior_output 未成功则 `continue` | `NH1-04` 只借 skip，不借当作 merge | `♻️ 重 substrate` | RA01：未访问 ≠ 事故 |
| `NH1-H08` | `tests/integration/test_ns5_turso_mainchain.py:106-138` | 经 Port 查向量 + `namespace_key` 再 search | `NH1-02/03` fork 正例 | `✅ 复用` | 已存在 PASS 模式 |
| `NH1-H09` | `src/runtime/intake/core.py:45-51,66-70` | http/browser/clean_llm 三分端口；禁 HTTP 冒充 rendered | `NH1-06` 边界 | `✅ 复用` | 端口在、生产未注入 |
| `NH1-H10` | `src/contracts/common/errors.py:92-94` | `ConflictError` → HTTP 409 | `NH1-05` 异 seal | `✅ 复用` | |
| `NH1-N01` | `tests/unit/test_nh1_denominator_inventory.py` | 将新建分母测试 | `NH1-01` | `🆕 净新` | |
| `NH1-N02` | `tests/e2e/test_nh1_fanin_recovery_port.py` | 将新建 Port recovery | `NH1-02` | `🆕 净新` | |
| `NH1-N03` | `tests/e2e/test_nh1_retrieval_namespace.py` | 将新建 namespace 正负例 | `NH1-03` | `🆕 净新` | |
| `NH1-N04` | `tests/unit/test_nh1_selected_output_control.py`；`tests/integration/test_nh1_merge_control.py` | 将新建 CONTROL spike 测试 | `NH1-04` | `🆕 净新` | |
| `NH1-N05` | `src/runtime/workflow/selected_output.py` | 将新建 SPIKE-ONLY 投影 | `NH1-04` | `🆕 净新` | 禁止注册进 builtin |
| `NH1-N06` | `tests/integration/test_nh1_s05_seal_cas.py`；`src/runtime/binding/actual_s05_spike.py` | 将新建 S05 spike | `NH1-05` | `🆕 净新` | 禁止改 `001_initial.sql` |
| `NH1-N07` | `tests/e2e/test_nh1_runtime_smoke.py` | 将新建 L3 smoke | `NH1-06` | `🆕 净新` | 不锁库名 |
| `NH1-N08` | `tests/unit/test_nh1_legal_matrix.py` | 将新建矩阵测试 | `NH1-07` | `🆕 净新` | |
| `NH1-N09` | `docs/evidence/new-harvest/AP-NH1/` | 将新建 evidence 目录 | `NH1-09` | `🆕 净新` | 执行期才有 SHA |

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| `NH1-A01` | `src/contracts/workflow/models.py:496-497`：`each workflow input port may have only one binding`；DDL `001_initial.sql:1770-1771` `ux_workflow_binding_slot` | 无 selected merge。**保围栏**，用 CONTROL 多 optional input + 单 output，**禁** one-of 自由 binding（Q11 `T-O-391`） |
| `NH1-A03` | `src/runtime/task/task_create.py:179-180`（fallback `:337-340`）：`s05_binding_digest=(prepared.domain_binding_digest)`；`001_initial.sql:245-246` NOT NULL | 列名盗用；`T-R-NH-22`。spike 必须把旧列当 legacy alias，禁 backfill（Q10 `T-O-390`；`FG-NH-08`） |
| `NH1-A04` | `tests/e2e/test_registered_api_scatter.py:7,26-33,264-273,327-347,366-373`：Turso 设置下 sqlite3 直读 | RA09 实测 `disk I/O error`。`FG-NH-12`。PROMPT 列了 `:26-33,366-367`；实测还含 `:7` import、`:264` process 直读、`:327` crash 注入 |
| `NH1-A05` | `api/app.py:330-345` 未注入 `browser_fetcher`/`clean_llm`；`pyproject.toml:13-21` 七依赖无 PDF/browser/OCR | `T-R-NH-26`；`D-20/D-21`。smoke 非 live DoD；503 非 DoD（`T-O-376`） |
| `NH1-X01` | `src/runtime/workflow/runtime_materialize.py:505-514`：CONTROL 仅 `scatter_children_join` / `human_review_gate` | scatter join 是 collect-all，**不是** XOR selected-output。禁复用 wait 语义（Q11） |
| `NH1-X02` | `tests/e2e/test_single_intake_pipeline.py:121-130` 与 `:382-394`：`retrieval:search` **无** `namespace_key` 却断言 200；同文件 `:150`/`:401` `sqlite3.connect` | `FG-NH-05`/`FG-NH-12`。服务端 raise 块 `retrieval_request.py:265-270` 会 422（正例；取值 `:263-264`）；假绿在测试 |
| `NH1-X03` | `src/services/config_snapshots.py:500-516`：`http_resource.{static,browser,pdf}` / `local_object.pdf|image` 仍选 7 profile | `T-R-NH-03`；与 `T-O-387` 冲突。NH1 只测量，NH2 才切 kind resolver |
| `NH1-X04` | `src/runtime/intake/types.py:144-171`：同进程正则抠 PDF 字面量；无层抛 `CLEAN_OCR_CAPABILITY_UNAVAILABLE` | `T-O-378` 盗码；无隔离。smoke 负例必须露出，不选库名「修好」 |
| `NH1-X05` | `src/contracts/inference/models.py:96-108`：`GenerateRequest.input_text` only | 不能运 PDF/image bytes。实弹 3 必须走 multimodal 形状或 typed 不可行 |
| `NH1-X06` | `src/runtime/health.py:16-26`：`REQUIRED` 九项无 browser/pdf/ocr | `/ready` 绿 ≠ runtime 在场（`FG-NH-11`）。RA 写 `health.py:16-25`；实测 tuple 止于 `:26` |
| `NH1-X07` | `src/runtime/workflow/runtime_core.py:888-917`：`ProcessCommand.binding_digest` ← `domain_binding_digest`，无 s05 字段 | 不能证明绑后不换工人。seal spike 必须让 command 能指向 actual |
| `NH1-X08` | 复制 13 profile / 整条 publication tail 冒充 kind family 或 merge | `FG-NH-09`；`T-O-398` 禁退回 duplication |
| `NH1-X09` | 生产默认 browser `--no-sandbox`；parser 与 browser 共用一份网络策略 | Q19 `T-O-399`；RA05 Playwright Docker 反例 |
| `NH1-X10` | mock Protocol、503、单 unit、任意 64-hex、修测试期待值、smoke 当 live DoD | final §7.1 NOT-成功；`FG-NH-01/02/08/13/17` |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：
  - RA01 `docs/eval/new-harvest/reference-anchor/assessment-analysis-01-workflow-graph-and-kind-family.md` — merge/CONTROL/单 binding；`NH-RA01-B01`；§7 substrate-fit 禁 CWL 表达式 / Temporal 引擎 / `action_branch`
  - RA02 `docs/eval/new-harvest/reference-anchor/assessment-analysis-02-s05-two-stage-binding-and-recovery.md` — stolen s05 列；`NH-RA02-B01..B04`；Outcome UoW 可借、值不可借
  - RA05 `docs/eval/new-harvest/reference-anchor/assessment-analysis-05-runtime-adapters-readiness-and-security.md` — default supply=0；隔离/license/CVE；**不冻库名**
  - RA09 `docs/eval/new-harvest/reference-anchor/assessment-analysis-09-assurance-replay-concurrency-and-compatibility.md` — sqlite3 / namespace 假绿；`NH-RA09-B04/B10`
- **安全 / 信任边界威胁模型**（不得留空；本 AP 安全项 = `NH1-06` + T02 的信任边界）：
  1. **恶意 PDF DoS/RCE**：HEAD 在 API 进程内解析（`types.py:144-171`）。Q19 要求 PDF parser 无网 isolated subprocess。T06 必须记录隔离形态；不得把 in-process 解析当生产接受线。
  2. **不可信 URL 浏览器逃逸 + SSRF**：browser 供给今日为 0；若 smoke 拉起 Chromium，必须 non-root、生产禁 `--no-sandbox`、出站走 S16 egress（与 parser 无网 **分账**）。
  3. **许可证传染**：仓标 Proprietary（`pyproject.toml:11`）。AGPL/GPL 链入主进程不可接受；本 AP **不选库**，只把 license 字段写入 smoke 报告。
  4. **测试面信任**：sqlite3 直读 Turso 既是假红也是假绿（可绕过 Port 的 RLS/CAS）。T02 是安全相关的证明边界，不是「图方便」。
  5. **攻击向量用例（§8.5）**：加密 PDF；省略 namespace 的检索；向 CONTROL 注入第二 binding；用 domain digest 查询冒充 sealed actual。

**§7.3 外部借鉴 verdict（不进 §7.1 混用）**：CWL `pickValue`/`when` = `⛔反例`（表达式）；BPMN XOR join = `🔶部分借`（split/join 分账，不并数据）；Temporal pin = `🔶部分借`（重映射到 revision digest，不引引擎）；Playwright `--no-sandbox` Docker = `⛔反例`；sqlite3-on-Turso = `⛔反例`；Outcome CAS = `✅借`。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| `NH1-T01` | 分母/compat inventory 稳定；promptA 三哈希可复现 | 短途 | L1 unit/契约 | `🆕 tests/unit/test_nh1_denominator_inventory.py` | `NH1-01/NH1-08` → inventory | `commit SHA + tests/unit/test_nh1_denominator_inventory.py::test_nh1_denominators_match_d01_d07 PASS + T-R-NH-01 + UTC` |
| `NH1-T02` | fan-in recovery 无 sqlite3 直读 | spike | L2 集成 | `🔱 tests/e2e/test_registered_api_scatter.py`（整文件 Port 化）+ `🆕 tests/e2e/test_nh1_fanin_recovery_port.py` | `NH1-02` → recovery | `commit SHA + test_registered_api_scatter.py::test_registered_api_scatter_auto_zero_and_fanin_recovery PASS + test_nh1_fanin_recovery_port.py::test_fanin_crash_repairs_via_persistence_port PASS + Q26 + UTC` |
| `NH1-T03` | namespace search 真实命中 | spike | L2/L4 | `🔱 tests/e2e/test_single_intake_pipeline.py`（补 namespace **且**删 sqlite3）+ `🆕 tests/e2e/test_nh1_retrieval_namespace.py` | `NH1-03` → query | `commit SHA + test_nh1_retrieval_namespace.py::test_search_with_layer_a_key_hits_content PASS + test_single_intake_pipeline.py 两节点 PASS（无 sqlite3）+ T-R-NH-16 + UTC` |
| `NH1-T04` | selected CONTROL exactly-one | spike | L1/L2 | `🆕 tests/unit/test_nh1_selected_output_control.py` + `tests/integration/test_nh1_merge_control.py` | `NH1-04` → merge | `commit SHA + 零/一/双 node PASS + Q11 + UTC` |
| `NH1-T05` | unsealed/seal/replay/conflict | spike/F | L2 | `🆕 tests/integration/test_nh1_s05_seal_cas.py` | `NH1-05` → S05 | `commit SHA + crash/CAS nodes PASS + Q10/Q20 + UTC` |
| `NH1-T06` | PDF/browser/multimodal 实弹 | spike/S | L3 | `🆕 tests/e2e/test_nh1_runtime_smoke.py` | `NH1-06` → feasible | `commit SHA + 3 smoke PASS + Q13/Q19 + UTC` |
| `NH1-T07` | legal/illegal matrix 生成 | 短途 | L1 契约 | `🆕 tests/unit/test_nh1_legal_matrix.py` | `NH1-07` → manifest | `commit SHA + matrix digest PASS + Q17/Q25 CITE + UTC` |

> T06：环境缺失时 **fail-loud**（pytest FAIL，非 skip）。`runtime-infeasible.md` + `stop-or-go.md=STOP` 只作为 **AP 未完成 / DAG halt** 记录，**不得**出现在本表 PASS 列或 §10.2「runtime 形态可行」行。证伪分支与 DoD 拆开：DoD = `NH1-T01..T07` 全 PASS。

#### `NH1-T01`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🆕 `tests/unit/test_nh1_denominator_inventory.py::test_nh1_denominators_match_d01_d07`；`::test_nh1_compatibility_inventory_has_16_old_pins`；`::test_nh1_prompt_a_three_ids_have_distinct_sha256` |
| 用途 | 证明 `NH1-01`/`NH1-08`；FG-NH-09（13 profile ≠ kind family）；T-R-NH-01/03/08 |
| 前置 | 无 DB；纯 import HEAD 模块；禁止 monkeypatch 改 `len(CLEAN_STRATEGY_DEFINITIONS)` |
| 步骤 | a) 执行 index §2.1 同构计数。b) 断言 kinds=4、strategies=10、capabilities=9、ops=3、single=13、public=7、unselectable=6、scatter=2。c) 断言 `len(BUILTIN_EXECUTION_COMPATIBILITY_WORKFLOWS)==16` 并序列化 key/revision。d) hashlib 三 promptA 文件，断言三 SHA 互斥并记录 readers。 |
| 断言细节 | 计数字面量与 RA `D-01..D-07` 逐项 `==`；compat=16；三 SHA 不等；输出 JSON 可写入 `docs/evidence/new-harvest/AP-NH1/queries/inventory.json` |
| 负例 | 人为改期待值为 5 kinds → 本测试必须仍对 HEAD FAIL（不得为「绿」改分母） |
| 跑法 | `uv run pytest tests/unit/test_nh1_denominator_inventory.py -q` |
| 层与来源 | L1 契约；`🆕` |

#### `NH1-T02`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🔱 **整文件 Port 化** `tests/e2e/test_registered_api_scatter.py`（含 `::test_registered_api_scatter_auto_zero_and_fanin_recovery` **与** `::test_registered_api_three_raw_provider_operations_map_seal_and_persist_semantics` 的 `:264-273`）；🆕 `tests/e2e/test_nh1_fanin_recovery_port.py::test_fanin_crash_repairs_via_persistence_port`；`::test_recovery_module_does_not_import_sqlite3` |
| 用途 | 证明 `NH1-02`；`FG-NH-12`；W-NH-FANIN |
| 前置 | `create_app()`；真实 PersistencePort（Turso 设置下不得 sqlite3 打开该文件）；auth `Authorization: Bearer …`；禁止 `sqlite3.connect` |
| 步骤 | a) 提交 scatter Task，等待 children terminal。b) 经 `async with persistence.transaction() as tx` 把 Task 置 `running`、root Execution 置 `waiting/scatter_children`。c) 唤醒 worker/repair。d) 查询父 Execution/Task 终态。e) ast/源码扫描 **scatter 整文件与新文件** 无 `import sqlite3`。 |
| 断言细节 | 父 `status=="succeeded"`；`proof_ref` 非空；repair 不创建第二 root Execution；HTTP 非 500 disk I/O；两文件源码无 sqlite3 |
| 负例 | 若仍 `sqlite3.connect(tmp_path/"mkb.sqlite3")` 且 backend=turso → 本测试必须失败（不得改成 skip）。未改的 scatter recovery **不得**当 T02 证据 |
| 跑法 | `uv run pytest tests/e2e/test_registered_api_scatter.py::test_registered_api_scatter_auto_zero_and_fanin_recovery tests/e2e/test_nh1_fanin_recovery_port.py::test_fanin_crash_repairs_via_persistence_port tests/e2e/test_nh1_fanin_recovery_port.py::test_recovery_module_does_not_import_sqlite3 -q` |
| 层与来源 | L2；`🔱` 整文件 Port 化 + `🆕` Port 用例 |

#### `NH1-T03`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🔱 `tests/e2e/test_single_intake_pipeline.py::test_single_intake_publishes_grounded_retrieval_context` 与 `::test_live_profile_uses_frozen_binding_for_vector_write_and_query`（检索体必须含 Port 读出的 Layer-A key；删除 `:150`/`:401` `sqlite3.connect`）；🆕 `tests/e2e/test_nh1_retrieval_namespace.py::test_search_without_namespace_returns_422`；`::test_search_with_layer_a_key_hits_content` |
| 用途 | 证明 `NH1-03`；`FG-NH-05`；`FG-NH-12`；兼防 `FG-NH-03`（Task succeeded ≠ hit） |
| 前置 | default-root app；Layer-A namespace 由 PersistencePort 从 `mkb_vector_namespaces` 读出；真实 UoW；禁止编造 namespace 字符串当命中。T03 PASS 节点不得执行 `sqlite3.connect`。`local_mock_settings`（默认 turso 的 CI waiver）不得当 T03 L4 组合根，除非另开带期限的 owner waiver（且不得覆盖 `T-O-376/378/381/383`） |
| 步骤 | a) ingest 黄金文档至 publication。b) Port 读取 active `namespace_key`。c) POST search 省略 namespace。d) POST search 带 key + 相同 query。e) 若 Task 在超时窗仍 `running` → FAIL。f) 源码扫描 🔱 文件无 `import sqlite3` / `sqlite3.connect`。 |
| 断言细节 | c) HTTP 422，error code `RETRIEVE_SCHEMA_NAMESPACE_REQUIRED`（`retrieval_request.py:265-270`）。d) HTTP 200，`disposition=="ok"`，`results` 非空，hit `payload_content` 匹配，`traceback_status=="resolved"`。省略 namespace 的 200 必须失败 |
| 负例 | 空 key / 空白 key → 422 `RETRIEVE_SCHEMA_NAMESPACE_INVALID`；用 Task `succeeded` 且不调用 search → 本 Test-ID FAIL；Turso 设置下 sqlite3 直读 → 本 Test-ID FAIL |
| 跑法 | `uv run pytest tests/e2e/test_nh1_retrieval_namespace.py tests/e2e/test_single_intake_pipeline.py::test_single_intake_publishes_grounded_retrieval_context tests/e2e/test_single_intake_pipeline.py::test_live_profile_uses_frozen_binding_for_vector_write_and_query -q` |
| 层与来源 | L2/L4；`🔱` + `🆕` |

#### `NH1-T04`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🆕 `tests/unit/test_nh1_selected_output_control.py::test_compile_optional_candidate_ports_exactly_one_output`；`::test_second_binding_on_same_input_still_rejected`；`::test_cycle_still_rejected`；🆕 `tests/integration/test_nh1_merge_control.py::test_single_candidate_projects`；`::test_zero_candidates_fail_loud`；`::test_double_hit_fail_loud`；`::test_missing_fact_fail_closed`；`::test_does_not_wait_on_scatter_join` |
| 用途 | 证明 `NH1-04`；Q11 `T-O-391`；`FG-NH-09` |
| 前置 | L1 无 DB；L2 真 UoW 持久化 selection proof；测试图不进 builtin registry |
| 步骤 | a) 编译含两个 optional candidate port 的 CONTROL 图。b) 试图给同一 process input 绑两条 prior_output（必须仍 ValueError）。c) UoW 写入 exactly-one selection 再投影。d) 零写入 / 双写入 / 缺 fact。e) 断言 CONTROL 代码路径不调用 `scatter_children_join`。 |
| 断言细节 | 单命中：output digest == 该 candidate manifest digest；零：typed error（非 200/succeeded）；双：完整性错误；缺 fact：fail-closed；compiled digest 含 CONTROL version；无第二份 publication tail 步骤 |
| 负例 | 把 `scatter_children_join` 当 merge；one-of binding；复制 13 图各跑 tail |
| 跑法 | `uv run pytest tests/unit/test_nh1_selected_output_control.py tests/integration/test_nh1_merge_control.py -q` |
| 层与来源 | L1/L2；`🆕` |

#### `NH1-T05`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🆕 `tests/integration/test_nh1_s05_seal_cas.py::test_legacy_unsealed_sealed_sql_distinct`；`::test_seal_same_uow_as_outcome`；`::test_same_seal_replay`；`::test_different_digest_conflict_error`；`::test_domain_hex_is_not_sealed_actual` |
| 用途 | 证明 `NH1-05`；Q10/Q20；`FG-NH-08`；fault 标签（crash 在 seal 前 vs 后） |
| 前置 | 真实 PersistencePort；测试会话内 spike 列；**不**改生产 DDL；facts 已 durable 再 seal |
| 步骤 | a) INSERT 三类 Execution 样本。b) SQL 按 state/列可空性区分。c) 在 Outcome UoW 内 CAS unsealed→sealed。d) 同 digest 再 seal。e) 不同 digest 再 seal。f) 用 domain 64-hex 查询 actual。g) 模拟 UoW 中途失败（rollback）后 actual 仍 unsealed。 |
| 断言细节 | legacy：`s05_binding_digest` 非空且 actual state 非 sealed；unsealed：actual NULL + state=unsealed；sealed：actual 非空 + generation≥1；replay 不增加 generation；异 digest raise `ConflictError` status 409；domain hex 不得使 `actual_binding_state=="sealed"`；rollback 后无半封行 |
| 负例 | `UPDATE s05_binding_digest = domain` 当封闭；route 提交后另开事务 seal |
| 跑法 | `uv run pytest tests/integration/test_nh1_s05_seal_cas.py -q` |
| 层与来源 | L2；`🆕`；标签 F |

#### `NH1-T06`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_nh1_runtime_smoke.py::test_pdf_text_layer_local_port`；`::test_spa_render_and_print_pdf`；`::test_binary_model_request_shape`；`::test_encrypted_pdf_is_typed_failure`；`::test_records_pin_license_cve_isolation` |
| 用途 | 证明 `NH1-06` 形态可行；Q13/Q19；`FG-NH-01/02/06/11`；**smoke 成功 ≠ NH6 DoD**；**FAIL/infeasible ≠ T06 PASS** |
| 前置 | `create_app()` default root；零 monkeypatch fetcher；本地 fixture 文件；环境缺失 → **FAIL**（非 skip）。`runtime-infeasible.md` 只记录 DAG halt，不得当作本 Test-ID PASS |
| 步骤 | a) 送带文本层 PDF 到 local parser port。b) 本地 SPA fixture render + print，断言 print bytes 以 `%PDF-` 开头。c) 构造 multimodal request（PromptRef+media+digest/handle），断言 text-only `GenerateRequest` 不能静默成功。d) 加密 PDF 负例。e) 把 pin/limits/license/CVE/isolation 写入 security/。 |
| 断言细节 | 成功路径无 503 当 DoD（`FG-NH-02`）；admitted `clean_text` 达 min-length，空/空白正文不得 `succeeded`（`FG-NH-06`）；加密 PDF typed error；报告含 parser 无网 / browser non-root / 无生产 `--no-sandbox`；**不**出现选定库名作为 Truth |
| 负例 | skip 当 PASS；monkeypatch browser；`which chromium` / `import pypdf` / `/v1/models` 当 ready；payload_extra base64 偷运 bytes |
| 跑法 | `uv run pytest tests/e2e/test_nh1_runtime_smoke.py -q`（缺环境也必须跑到 FAIL） |
| 层与来源 | L3；`🆕`；标签 S |

#### `NH1-T07`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🆕 `tests/unit/test_nh1_legal_matrix.py::test_registry_emits_10_strategy_and_3_ops`；`::test_seven_intent_illegal_cells_have_disposition`；`::test_forbids_7x4_cartesian` |
| 用途 | 证明 `NH1-07`；`T-O-397/405` CITE；`T-R-NH-07/21`；`FG-NH-15` |
| 前置 | 纯 registry import |
| 步骤 | a) 从定义生成 strategy 10 格 + operation 3 格。b) 生成七意图 applicability。c) 断言不存在 28 格全合法表。d) 稳定 digest。e) 把 10+3 合法格与七意图非法格 **预埋/写入** `tests/fixtures/new_harvest/closed_set_manifest.v1.json`（final §9.1 固定路径；闭集生成仍属 NH9）。字段名锁死：`strategy_cells`（10）/ `op_cells`（3）/ `intent_illegal` + canonical `digest`。 |
| 断言细节 | `len(strategy_cells)==10`；`len(op_cells)==3`；非法格每格有 `disposition` 与 error code 槽；`intake.ingest` 才按 kind 分叉；manifest 文件存在且上述四字段 digest 可复现。NH9 生成器只 append 82 work ID / windows / FG，**禁止**改这四个字段的 canonical 字节。 |
| 负例 | 手抄 7×4=28 全绿表；把 exhausted_zero 写成 succeeded； silently 丢掉 §9.1 路径 |
| 跑法 | `uv run pytest tests/unit/test_nh1_legal_matrix.py -q` |
| 层与来源 | L1 契约；`🆕` |

### 8.2 复用台账（沿用 / fork 的既有用例明细）

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/e2e/test_registered_api_scatter.py`（整文件，含 recovery 与 `:264-273` 另一函数） | `🔱` 整文件 Port 化 + 🆕 Port 用例 | 删模块 `import sqlite3`；crash 注入/断言改 Port | 存在但 Turso 下红（disk I/O）；未 Port 化不得当 T02 证据 |
| `tests/e2e/test_single_intake_pipeline.py` 两处检索 + sqlite3 直读 | `🔱 fork` 补 Layer-A `namespace_key` **且**删 `sqlite3.connect` | body 加 Port 读出的 key；`:150`/`:401` 改 PersistencePort | 存在；缺 namespace 相对 HEAD 服务端必 422；sqlite3-on-Turso 不得当 T03 PASS |
| `tests/integration/test_ns5_turso_mainchain.py:106-138` | `♻️ 沿用` 模式 | 0 改动；NH1 新测试模仿其 Port 读法 | 已存在，PASS 模式 |
| `src/runtime/workflow/runtime_outcome.py:88-137` | `♻️ 沿用` 线性化 | spike 扩 actual CAS，不另开 saga | 代码已在；actual 未接 |
| `tests/unit/test_intake_provider_registry.py` 等 33 绿 | `♻️ 沿用` 分母对照 | 0 改动 | 不得当 L3 |

### 8.3 分层与跑法（各类型在哪跑、何时跑）

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `uv run pytest tests/unit/test_nh1_denominator_inventory.py tests/unit/test_nh1_legal_matrix.py -q` | L1 | 开发中持续 |
| spike L2 | `uv run pytest tests/e2e/test_registered_api_scatter.py::test_registered_api_scatter_auto_zero_and_fanin_recovery tests/e2e/test_nh1_fanin_recovery_port.py tests/e2e/test_nh1_retrieval_namespace.py tests/e2e/test_single_intake_pipeline.py tests/integration/test_nh1_merge_control.py tests/integration/test_nh1_s05_seal_cas.py -q` | L2 | Phase 1/3 收口 |
| spike L3 | `uv run pytest tests/e2e/test_nh1_runtime_smoke.py -q` | L3 default-root | Phase 3；缺环境 FAIL 非 skip |
| mega | 本 AP **无** campaign mega | — | 交 NH9；T03 的 L4 只覆盖 namespace 命中黄金文档 |
| soak | 本 AP 不要求 soak ×N | — | 交 NH9 W-NH-FANIN 组合 |

本 AP 台账 C 最低层不得自行降：T01 L1、T02 L2、T03 L2/L4、T04 L1/L2、T05 L2、T06 L3、T07 L1。

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖 10+3 全格 live-to-vector（理由：属 `S-NH-F7`）→ `AP-NH7`
- 不覆盖生产 kind 切流与 old-pin 全跑完（理由：属 NH2）→ `AP-NH2`
- 不覆盖生产 S05 migration 与 typed history 权威行（理由：属 NH3）→ `AP-NH3`
- 不覆盖 public upload+stat（理由：属 NH4；本 AP 只 CITE 接口包）→ `AP-NH4`
- 不覆盖五维 facet（理由：属 NH5）→ `AP-NH5`
- 不覆盖生产 SBOM/隔离闭环与 readiness 入 `/ready`（理由：属 NH6；smoke ≠ DoD）→ `AP-NH6`
- 不覆盖全仓 sqlite3 清零与 race mega（理由：属 NH9 `FG-NH-12`）→ `AP-NH9`（scatter 与 T03 pipeline 除外，二者是本 AP T02/T03 证明路径）
- 不覆盖加密 PDF 的生产 parser 选型（理由：Q13 不锁库名）→ `AP-NH6` 在 T06 可行之后
- 不覆盖 10+3 live 闭集生成（理由：属 NH9）；T07 **必须**把矩阵 digest 预埋到 final §9.1 路径 `tests/fixtures/new_harvest/closed_set_manifest.v1.json`，禁止 silently 丢掉该路径。NH9 capstone 再生成 live closed-set

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 必带四元组 `commit SHA + pytest node PASS + Truth/Q + UTC`；计数 ≠ 价值。
- `degraded` 必带机器可读 `reason`；pre-existing 失败必带 git 证据，不 silent overclaim。
- 本 AP 适用 FG（必须在对应细则点名）：`FG-NH-01`（T06）、`FG-NH-02`（T06；503/未部署不得当 T06 PASS）、`FG-NH-03/04`（T03）、`FG-NH-05`（T03）、`FG-NH-06`（T06 空/空白 admitted clean 不得 succeeded）、`FG-NH-08`（T05）、`FG-NH-09`（T01/T04）、`FG-NH-11`（T06）、`FG-NH-12`（T02 **与** T03）、`FG-NH-13`（全）、`FG-NH-15`（T07）、`FG-NH-17`（禁改期待值）。
- 安全项攻击向量：加密 PDF；无 namespace 检索；第二 binding；domain hex 冒充 sealed。
- T06 skip ≠ PASS；T06 typed FAIL / `infeasible.md` ≠ PASS；T04 单 unit 绿 ≠ merge 可行（必须 L2 投影）；T05 改列别名 ≠ seal。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| `R-F01` chosen merge 不可行 | 零/双命中或 compile 失败 | `high` | STOP/reopen `T-O-391/398`，不准 duplication |
| `R-F05` runtime 供应链失败 | license/CVE/binary 不可部署 | `high` | T06 typed 不可行 + STOP；owner waiver **仅延期** 且本 AP 不得用 waiver 降层 |
| `R-F13` L1 替代 L3/L4 | 环境困难 | `high` | `T-O-406`；T06 缺环境 FAIL |
| `R-F14` Task/flag 顶替 query | 沿用旧 e2e | `high` | T03 强制 namespace + hit |
| `R-F02` 旧 s05 被误 backfill | 按 64-hex 判断封闭 | `high` | T05 三类区分；禁 backfill |
| 依赖 Phase 1 | Phase 2/3 的绿建立在 Port/namespace 上 | `high` | 顺序硬约束 |
| RA/index 分母 | 若 HEAD 已变 | `low`（冻结于 `1221aa1`） | 先修订 index，不改测试期待值 |

### 9.2 约束与前提

- **技术前提**：HEAD `1221aa1`；七表编译器与 Outcome UoW 保持可复用；生产 DDL 本 AP 只读。
- **运行时前提**：L2 测试有真实 PersistencePort；L3 smoke 需要本地 fixture；缺 binary 则 FAIL。
- **组织协作前提**：无新 owner-gate；证伪必须 reopen QNA/final，不得 AP 内改口。
- **上线 / 合并前提**：本 AP 文档 `draft`；代码执行不在本文档回合。SPIKE 模块不得随「部分绿」合并进 builtin。

### 9.3 文档同步要求

- 需要同步更新的设计文档：无（禁止改 QNA/final/RA）
- 需要同步更新的说明文档 / README：执行期可在 evidence pack 指向 README K1 namespace 说明，不在本 AP 改 README
- 需要同步更新的测试说明：`docs/evidence/new-harvest/AP-NH1/tests.txt`

### 9.4 完成后的预期状态

1. Recovery 与 retrieval 证明路径不再依赖 sqlite3-on-Turso 或无 namespace 200。
2. 分母与两张矩阵、promptA 三 id 清单可被 NH2/NH7 机器消费。
3. CONTROL/S05/runtime **要么** 被证伪并 STOP，**要么** 以 SPIKE 切片 + versioned 接口交给 NH2/NH3/NH6——二者都不是「已上线」。
4. `docs/evidence/new-harvest/AP-NH1/interfaces/` 存在 NH2–NH6 input/output/error。
5. DAG 后续节点仅在 `stop-or-go.md = GO` 时解锁。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

### 10.1 收口硬闸

所有退出层测试必须 **PASS 且四元组证据齐全**。禁止「部分绿继续 NH2」。**证伪分支**（承重 spike FAIL / typed 不可行）写入 `stop-or-go.md=STOP` 并 reopen 对应 `T-O` + final（`T-O-398`），**不得**写入台账 C PASS 列。

1. **harness 可信**：`tests/e2e/test_registered_api_scatter.py` 与 `tests/e2e/test_nh1_fanin_recovery_port.py` 源码无 `import sqlite3` 且无对 Turso 文件的 `sqlite3.connect`；fan-in crash 后经 `PersistencePort.transaction()` 父 Execution `succeeded` 且 `proof_ref` 非空；`tests/e2e/test_single_intake_pipeline.py` 无 `sqlite3.connect`；`retrieval:search` 省略 namespace 的响应为 HTTP 422 而非 200；带 Layer-A key 的 search HTTP 200 且 `disposition=="ok"` 且 `results` 非空；不存在把 Task `status=running` 超时写成 PASS 的断言。（由 `NH1-T02`/`NH1-T03` 证明）
2. **CONTROL 可行**：存在一张测试图，optional 多 candidate port + 单 CONTROL output + 单 tail binding 可编译；单命中时下游 digest 等于该 candidate；零命中 fail-loud（或仅登记 fallback）；双命中 fail-loud；CONTROL 不复制 publication tail、不重跑 guard、不等待未 materialize 分支、不调用 `scatter_children_join`。（由 `NH1-T04` 证明）
3. **S05 可行**：同一测试库中 SQL 能选出 legacy / unsealed / sealed 三类互斥行；unsealed→sealed 与 Outcome 在同一 `UnitOfWork`（rollback 则 actual 仍 unsealed）；同 digest replay 不双封；异 digest 第二次 seal raise `ConflictError`；以旧 `s05_binding_digest` 的 64-hex 查询不得得到 `actual_binding_state='sealed'`（`FG-NH-08`）。（由 `NH1-T05` 证明）
4. **runtime 形态可行**：三次实弹（PDF text layer local port / SPA render+print 产出 `%PDF-` / binary model request）**每条 pytest PASS** 且留下成功记录；加密 PDF 为 typed 失败而非空/空白 `clean_text` 成功（`FG-NH-06`）；报告含 pin/limits/license/CVE/isolation。缺 binary/503 保持 FAIL，禁止 skip、禁止当 DoD（`FG-NH-02`）。typed 不可行只进 `runtime-infeasible.md` + `stop-or-go.md=STOP`（AP 未完成 / DAG halt），**不得**填本行四元组。（由 `NH1-T06` 证明）
5. **下游接口冻结**：`docs/evidence/new-harvest/AP-NH1/interfaces/` 含 NH2–NH6 的 versioned input/output/error 文件；`manifest.json` 列出 work/test/Truth/UTC。（由 `NH1-T01`/`NH1-T07` + `NH1-09` review 证明）

**DoD 硬闸**（逐字回到 final §7.1）：`NH1-T01..T07` 全 PASS。任何 chosen shape 被证伪 → `stop-or-go.md=STOP` 并 reopen final，**不是**该 Test-ID PASS。

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| harness 可信：无 disk I/O sqlite3 直读、无 422-on-success、无 running 超时当绿 | `NH1-02`/`NH1-03` | `NH1-T02`/`NH1-T03` | `commit + pytest node PASS + Q26/T-R-NH-16 + UTC` | `未观察` |
| chosen graph 可行：exactly-one 且不复制 tail/重跑 guard | `NH1-04` | `NH1-T04` | `commit + 零/一/双 node PASS + Q11 + UTC` | `未观察` |
| chosen S05 可行：old/unsealed/sealed 可分，二次异 seal 冲突 | `NH1-05` | `NH1-T05` | `commit + CAS nodes PASS + Q10/Q20 + UTC` | `未观察` |
| runtime 形态可行：真实 binary/process 成功并有负例 | `NH1-06` | `NH1-T06` | `commit + 3 smoke PASS + Q13/Q19 + UTC` | `未观察` |
| 下游接口冻结：NH2–NH6 versioned I/O/error | `NH1-01`/`NH1-07`/`NH1-08`/`NH1-09` | `NH1-T01`/`NH1-T07` | `commit + matrix digest PASS + interface files + UTC` | `未观察` |
| 执行分母 diff=0 | `NH1-01` | `NH1-T01` | `commit + 脚本/pytest EXIT0 + T-R-NH-01 + UTC` | `未观察` |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | SPIKE 切片可证伪且未注册进生产 builtin/DDL；接口包发布；GO/STOP 二元 |
| 测试 | §8 `NH1-T01..T07` 全 PASS；退出项四元组齐全。证伪 FAIL 只 halt DAG，不得写入 PASS 列 |
| 文档 | 本 AP 仍为 `draft` 直至执行回填；evidence 目录文件齐（见下） |
| 风险收敛 | `R-F01/F13/F14` 要么关闭要么转为 STOP reopen；无静默 duplication |
| 可交付性 | NH2–NH6 能只读消费 `docs/evidence/new-harvest/AP-NH1/interfaces/` |

**evidence pack 规定文件名**（final §9.3；本 AP 只规定，不伪造 SHA）：

```text
docs/evidence/new-harvest/AP-NH1/
  manifest.json
  tests.txt
  stop-or-go.md
  queries/inventory.json
  queries/matrix-legal.json
  queries/matrix-illegal.json
  queries/promptA-inventory.json
  queries/namespace-search.json
  migrations/s05-spike-before-after.md
  security/runtime-smoke-sbom.md
  security/isolation-license-cve.md
  security/runtime-infeasible.md          # 仅当 T06 typed 不可行（DAG halt；不是 T06 PASS）
  interfaces/nh2-selected-output-control.v1.json
  interfaces/nh2-kind-resolver-fence.v1.json
  interfaces/nh3-s05-actual-seal.v1.json
  interfaces/nh3-representation-projection.v1.json
  interfaces/nh4-object-surface-cite.v1.json      # CITE T-O-385/396/404，不实现
  interfaces/nh5-semantic-channel-cite.v1.json    # CITE T-O-394/395，不实现
  interfaces/nh6-runtime-ports.v1.json
  closure.md
```

接口 JSON 最小键：`version`、`owner_ap`、`consumers`、`input`、`output`、`errors[]`（code/http/when）、`truth_cite[]`、`spike_status`（`pass|fail|infeasible`）、`upgrade_gate`（例如 `NH1-T04 PASS`）。

### 10.4 NOT-成功识别

> 任一退出硬闸测试 `degraded / 未观察` ⇒ **不得标 `executed`**。

抄 final §7.1 并补本 AP 特有假绿：

- mock `Protocol` 当 L2/L3 成功
- 503 / 诚实未部署当 in-scope DoD
- 仅 L1 unit 绿宣称 CONTROL/S05/runtime 可行
- 复制 13 张图 / 复制 publication tail 当 merge 或 kind family
- 任意 64-hex（domain digest）当 sealed actual
- 修改测试期待值掩盖 422/running/disk I/O
- smoke 三次成功当 NH6 live DoD
- pytest `skip` 当 T06 PASS
- typed 不可行报告 / `infeasible.md` / 503 / 缺 binary 当 T06 PASS 或「runtime 形态可行」DoD
- sqlite3 直读 Turso 当 recovery 证明
- 无 `namespace_key` 的 200 当检索成功
- Task `succeeded` / `publication_ready` / `status=running` 超时当可检索
- monkeypatch `_browser_fetcher/_http_fetcher/_clean_llm` 当接线
- 生产 CONTROL 已注册 / 生产 S05 已 migration（本 AP 范围外，写成已上线即 overclaim）
- 选定 pypdf/playwright/tesseract 等库名当 Truth

---

## 11. 执行日志回填（仅 `executed` 状态使用）

> 文档状态为 `draft`，本节省略执行事实。下列为模板占位，执行完成后改用 `respond-execution-log` 厚版回填。residual 交后继 AP，不回填为本阶段完成。

- **实际执行摘要**：`{EXECUTION_SUMMARY}`（未执行）
- **Phase 偏差**（逐条带分类）：`{PHASE_VARIANCE}`
- **阻塞与处理**：`{BLOCKERS_AND_RESOLUTION}`
- **测试发现**（含全绿计数 + 新暴露事实）：`{TEST_FINDINGS}`
- **后续 handoff**：GO → NH2/NH4/NH5 并行；STOP → reopen `T-O` + final，禁止 duplication

---

## 附录 · 修订历史

| 版本 | 日期 | 作者 | 说明 |
|------|------|------|------|
| `v0.1` | `2026-08-29` | Grok workflow | 由 final §7 派生 |
| `v0.2` | `2026-08-29` | Grok fix-fleet | 吸收已核实 review：T06 PASS 与证伪 STOP 拆开；T02 整文件 Port 化并列入跑法；T03 删 sqlite3+补 namespace 并列入跑法；T07 预埋 `closed_set_manifest.v1.json`；点名 `FG-NH-06`；namespace 422 锚改为 `retrieval_request.py:265-270` |
| `v0.3` | `2026-08-29` | Grok recon-fix | T07 锁死 manifest 字段 `strategy_cells`/`op_cells`/`intent_illegal`/`digest`；NH9 生成器不得改 10+3 canonical 字节 |
