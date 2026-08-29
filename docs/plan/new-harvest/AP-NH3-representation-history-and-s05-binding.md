# Nano-Agent 行动计划

> 服务业务簇: `MKB / new-harvest / intake-four-channel-live`
> 计划对象: `typed RepresentationFact / AcquireDecodeHistory + policy/actual S05 分账 + seal CAS + full_task exact`
> 类型: `migration` + `upgrade`
> 作者: `Grok workflow new-harvest-nh1-nh5-action-plans`
> 时间: `2026-08-29`
> 文件位置: `docs/plan/new-harvest/AP-NH3-representation-history-and-s05-binding.md`
> 上游前序 / closure:
> - `docs/eval/new-harvest/final-execution-plan.md` v1.0 `frozen` §7.3（唯一执行基线；台账 A/B/C/D）
> - DAG：`AP-NH1` chosen-shape 必须 PASS（fail → STOP/reopen，`T-O-398`）；`AP-NH2` kind graph / merge / representation predicates 已声明边
> 下游交接:
> - `AP-NH6` local runtime supply（print/browser/OCR 真实供给；本 AP 只冻结诚实表示与 typed fail）
> - `AP-NH7` 10+3 vertical 消费 fact/history/actual
> - `AP-NH8` rebuild/metadata intent-guard 旁路落地（本 AP `NH3-10` 写法律，guard 实现交 NH8）
> - `AP-NH9` W-NH-SEL/SEAL mega 与 closed-set
> 关联设计 / 调研文档:
> - `docs/eval/new-harvest/final-execution-plan.md` v1.0 §4 / §6 / §7.3 / §9 / §10 / §11.A
> - `docs/eval/new-harvest/pre-charter-qna.md` v1.0 Q10/Q12/Q20/Q21/Q22/Q27
> - `docs/eval/new-harvest/pre-initial-planning-qna.md` v0.5 `T-O-378/383/388`
> 冻结决策来源:
> - `docs/eval/new-harvest/pre-charter-qna.md` v1.0：`T-O-390` / `T-O-392` / `T-O-400` / `T-O-401` / `T-O-402` / `T-O-407`（只读引用；本 action-plan 不填写 Q/A）
> - `docs/eval/new-harvest/pre-initial-planning-qna.md` v0.5：`T-O-378` / `T-O-383` / `T-O-388`
> grounding 来源:
> - HEAD `1221aa1` 独立 `read_file` 核验
> - eval-reference-anchor RA02 / RA03（主面）+ RA08 rebuild 仍 reclean 缺口（只消费）
> - final §7.3 台账 ID 区间 `NH3-01..10 / NH3-A01..07 / NH3-T01..08`
> 关联 reference-anchor:
> - [`docs/eval/new-harvest/reference-anchor/assessment-analysis-02-s05-two-stage-binding-and-recovery.md`](../../eval/new-harvest/reference-anchor/assessment-analysis-02-s05-two-stage-binding-and-recovery.md)
> - [`docs/eval/new-harvest/reference-anchor/assessment-analysis-03-representation-and-reacquisition.md`](../../eval/new-harvest/reference-anchor/assessment-analysis-03-representation-and-reacquisition.md)
> - [`docs/eval/new-harvest/reference-anchor/assessment-analysis-08-publication-and-intake-lifecycle.md`](../../eval/new-harvest/reference-anchor/assessment-analysis-08-publication-and-intake-lifecycle.md)（`NH-RA08-B04` 只消费）
> 文档状态: `draft`

---

## 0. 执行背景与目标

HEAD `1221aa1` 把 `domain_binding_digest` 写入名为 `s05_binding_digest` 的 NOT NULL 列且零 UPDATE（`T-R-NH-04/22`）；acquire/decode 只有会被覆盖的单槽 evidence（`T-R-NH-05`）；decode 用字面量 PDF 扫描并把无层盗码为 OCR 未部署（`T-R-NH-06`）。`P-S05-schema` 已 `CORRECT`：旧列逻辑隔离，新 actual 显式 state/digest/seal，旧行永久 `unverifiable`。本 AP 把冻结的 typed history 权威、诚实表示、声明式再获取、policy/actual 分账、同 UoW seal CAS 与 `full_task` exact 复制落成可迁移 schema 与可复验 L1/L2 证明，不重开 Q10–Q27，不把 GPT/Grok 推荐当尚未冻结的选项。

- **服务业务簇**：`new-harvest` · `S-NH-F3`
- **计划对象**：RepresentationFact / AcquireDecodeHistory / actual S05 sealed-once SSOT / full_task exact
- **本次计划解决的问题**：
  - 单槽 JSON 覆盖无法证明有限正向路径，guard/seal/replay 没有 durable 权威（`T-O-392`）
  - 字面量 PDF、OCR 盗码、常量 print profile、ZIP 当 `text/plain` 把假表示送进清洁（`T-O-378/388/402`）
  - 旧 `s05_binding_digest` 冒充 actual；route 与 seal 无同 UoW；`full_task` 只复制伪值；rebuild 过程仍 reclean（`T-O-390/400/401/407`）
- **本次计划的直接产出**：
  - `M-NH-02` typed append-only fact/history 行，与对应 Process Outcome 同 UoW
  - MIME/OPC/opaque 分账、PDF 观察码、诚实 print fact、声明式 reacquire history
  - `M-NH-01` policy/actual 分账 + seal CAS + 下游只读 actual + 三窗/`full_task` exact；upgrade 入口 = 0
- **本计划不重新讨论的设计结论**：
  - 旧列逻辑隔离且不得 backfill；新 `actual_binding_digest/state/seal_generation` 是 sealed-once SSOT（来源：Q10 / `T-O-390`；`P-S05-schema CORRECT`）
  - fact/history 与 Outcome 同 UoW；同 step 二次成功拒绝（来源：Q12 / `T-O-392`）
  - durable facts 在先；route Outcome + actual seal + clean eligibility 同一 UoW（来源：Q20 / `T-O-400`）
  - Process/`full_task` 复制 exact sealed actual；existing-object upgrade OOS（来源：Q21 / `T-O-401`）
  - decode observer 三态；仅 `absent` 可命中已声明 browser 边（来源：Q22 / `T-O-402`）
  - rebuild/metadata 真正旁路 clean 的 **法律** 在本 AP 写死，**guard 落地在 NH8**（来源：Q27 / `T-O-407`）

---

## 1. 执行综述

### 1.1 总体执行方式

**先 durable 行，再诚实表示，再声明式再获取，再 S05 分账与 seal，最后钉 replay 法律。** 不先改读者语义却继续写单槽 JSON；不把旧列改 nullable 当 actual。每 Phase 先 schema/合同与 L1，再挂 Outcome UoW 的 L2，fault 窗只注入 W-SEL/SEAL，不降层到「单元改列别名」。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | durable rows | `L` | RepresentationFact + AcquireDecodeHistory；同 UoW append；同 step 二次成功拒绝 | NH1 PASS；NH2 图边/谓词已声明 |
| Phase 2 | 诚实表示 | `L` | MIME/OPC/opaque 分账；PDF 观察/能力分码；honest print fact | Phase 1 |
| Phase 3 | 声明式再获取 | `L` | 读 fact、走 NH2 已声明边、append history；无边/重复/try-all 失败 | Phase 1+2；NH2 正向边 |
| Phase 4 | S05 分账 | `XL` | 隔离旧列；nullable actual+state+seal；CAS 同 UoW；传播只读 actual | Phase 1–3；NH1 S05 spike |
| Phase 5 | replay 法律 | `L` | 三窗；`full_task` exact copy；rebuild 不写新 actual；upgrade 入口=0 | Phase 4 |

> 上表 `规模` 是描述性提示，不是开工闸。

### 1.3 Phase 说明

1. **Phase 1 — durable rows**
   - **核心目标**：把表示权威从可覆盖字典迁到 typed 行，并与 Outcome 线性化。
   - **为什么先做**：没有行就没有 path digest、seal 输入和 crash 可恢复的 history（`T-O-392`；`M-NH-02`）。
2. **Phase 2 — 诚实表示**
   - **核心目标**：bytes 观察诚实；无层不是 OCR 未部署；print 必须是 PDF bytes。
   - **为什么放在这里**：再获取与 seal 只能消费 durable 观察，不能消费 handler 猜测。
3. **Phase 3 — 声明式再获取**
   - **核心目标**：绑定前只走 NH2 已声明正向边，history 长度与 digest 可证。
   - **为什么放在这里**：边在 NH2；本 AP 只 append 与拒绝未声明路径。
4. **Phase 4 — S05 分账**
   - **核心目标**：policy 与 actual 两本账；seal 单 CAS；下游零 domain 冒充。
   - **为什么放在这里**：digest 必须聚合已提交的有序 history（`T-O-390/400`；`M-NH-01`）。
5. **Phase 5 — replay 法律**
   - **核心目标**：三窗分测；新 generation 仍 exact；rebuild 不绑源工人。
   - **为什么放在这里**：没有 sealed actual 就无法测「复制 exact」与「禁止清 actual」。

### 1.4 执行策略说明

- **执行顺序原则**：schema/行权威 → 观察诚实 → 声明边消费 → 列分账/CAS → replay 矩阵。禁止先改读者再补写 history。
- **风险控制原则**：旧行永久 `unverifiable`；禁止 64-hex 非空当 actual（`R-F02`/`FG-NH-08`）。NH1 spike 失败 STOP，禁止静默换 duplication（`T-O-398`）。existing-object upgrade 入口保持 0（`O-NH-03`/`T-O-401`）。
- **测试推进原则**：L1 观察/sniff/migration SQL → L2 UoW/rollback/CAS/fault → 本 AP **最低层以台账 C 为准（最高 L2/F）**，不把 L1 顶 L2，也不把本 AP 的 e2e 文件目录误标为 L3 default-root。L3/L4 交 NH6/NH7/NH9。
- **文档同步原则**：S05/D04/glossary 只 append calibration 指针，不改冻结 QNA。evidence pack 只规定文件名，不伪造 SHA。
- **回滚 / 降级原则**：migration forward-only；物理 rename 待兼容证明。失败不得把旧列改解释。seal 冲突保持 `ConflictError` 409，不降成覆盖写。

### 1.5 本次 action-plan 影响结构图

```text
AP-NH3 representation-history-and-s05-binding
├── Phase 1: durable rows
│   ├── src/persistence/migrations/018_* (M-NH-02 fact/history)
│   ├── src/contracts/intake/representation.py（字段闭集/version）
│   └── src/runtime/workflow/runtime_outcome.py:88-137（append 线性点）
├── Phase 2: 诚实表示
│   ├── src/runtime/intake/types.py:174-220（sniff 扩展 ZIP/OPC）
│   ├── src/runtime/intake/types.py:144-171（替换 literal PDF 权威）
│   └── src/runtime/intake/acquisition_ingest.py:533-536（禁常量 print profile）
├── Phase 3: 声明式再获取
│   ├── NH2 已声明边（只读消费）
│   └── AcquireDecodeHistory ordinal + path digest
├── Phase 4: S05 分账
│   ├── src/persistence/migrations/019_* (M-NH-01 actual columns)
│   ├── mkb_executions actual_binding_* CAS
│   └── ProcessCommand / Snapshot / Gate / child 只读 actual
└── Phase 5: replay 法律
    ├── src/runtime/task/task_commands.py:237-311（exact copy 新列）
    ├── 三窗 W-NH-SEL / W-NH-SEAL / sealed retry
    └── rebuild 不写新 actual；upgrade 入口=0（落地 NH8）
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** `S-NH-F3`：typed history、representation、reacquire、actual S05/restart（`T-O-388/390/392/400..402`）
- **[S2]** `M-NH-02` RepresentationFact + AcquireDecodeHistory，与对应 acquire/decode Process Outcome 同 UoW
- **[S3]** MIME/OPC/opaque 分账、PDF 观察/能力分码、honest print fact（无 browser 时 typed fail）
- **[S4]** 声明式正向再获取：只走 NH2 已声明边；history 可证；禁 try-all / 暗升
- **[S5]** `M-NH-01` policy/actual 分账：旧 `s05_binding_digest` 逻辑隔离；新 nullable actual + 显式 state/seal_generation；旧行 `unverifiable`
- **[S6]** selected-route Outcome + actual seal CAS + clean eligibility 同一 Outcome UoW；commit 后才 dispatch
- **[S7]** 传播链只读 actual 或明确 unsealed；`full_task` exact copy；rebuild 法律（不绑源工人）；upgrade 入口扫描 = 0
- **[S8]** 本 AP 台账 C 最低层证明（L1 / L2 / L2-F）；evidence pack 目录约定

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** `O-NH-01`：第五 kind、caller `workflow_key`、`action_branch`、live connector/cookie/tunnel
- **[O2]** `O-NH-02`：cuts/g0 算法、按通道复制 tail、前端/answer generation
- **[O3]** `O-NH-03`：existing-object new-cleaner/validator upgrade（`T-O-401`；未来须新 owner-gate）
- **[O4]** `O-NH-04`：raw object GET/list/presign/browser
- **[O5]** `O-NH-05`：experiment 发车/评分
- **[O6]** `O-NH-06`：通用 Workflow JOIN/DSL/自由表达式/loader；云 OCR/CF/R2/SMCP/Workers
- **[O7]** NH6 真实 browser/PDF parser/OCR 生产供给与 `--no-sandbox` 部署（本 AP 只要求缺供给时 typed fail）
- **[O8]** NH8 `registered_request_intent` guard 旁路 acquire/decode/clean 的图改线（本 AP 只写法律与「无 upgrade 入口」扫描）
- **[O9]** NH7 10+3 live-to-retrieval、NH9 mega/L3/L4；把本 AP `tests/e2e/test_nh3_seal_crash_windows.py` 标成 L3

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| typed fact/history 行 + Outcome 同 UoW | `in-scope` | `S-NH-F3`；Q12 / `T-O-392`；`M-NH-02` | 无；推翻须新 Truth |
| ZIP/OPC sniff + PDF 观察分码 + honest print 合同 | `in-scope` | `T-O-378/388/402/403`；OCR/print **供给**属 NH6 | 库选型不在本 AP |
| 声明式 reacquire（消费 NH2 边） | `in-scope` | `T-O-388`；边的画出在 NH2 | NH2 未交付则本 Phase 3 阻塞 |
| policy/actual 分账 + seal CAS | `in-scope` | Q10/Q20；`M-NH-01`；`P-S05-schema CORRECT` | 物理 rename 待兼容证明 |
| `full_task` 复制 new actual；rebuild 不写新 actual | `in-scope` | Q21 / `T-O-401`；`T-R-NH-23` | 无 |
| existing-object new-cleaner upgrade | `out-of-scope` | `O-NH-03` / `T-O-401` | 新 owner-gate + restart identity |
| 把旧列改 nullable 后当 actual | `out-of-scope` | `T-O-390`；`FG-NH-08` | 禁止重评为本 AP 成功 |
| Temporal/Cadence history store | `out-of-scope` | `O-NH-06`；RA02 ⛔ | 无 |
| rebuild guard 旁路实现 | `defer / depends-on-design` | 法律在 `NH3-10`；落地 NH8 / `T-O-407` | NH8 开工 |
| default-root live print/OCR | `out-of-scope` | `S-NH-F6` 属 NH6；本 AP 最低层 L2 | NH6/NH7 |

---

## 3. 业务工作总表

> 编号列使用 final 台账 A 的 `NH3-nn`（禁止改成只剩 `P1-01`）。每个工作项含不可约三元组：file:line / 收口目标 / Test-ID。

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| `NH3-01` | Phase 1 | RepresentationFact | `migrate` | 🆕 `src/persistence/migrations/018_nh3_representation_fact_history.sql`；🆕 `src/contracts/intake/representation.py`；`src/runtime/workflow/runtime_outcome.py:88-137`（`NH3-A03`） | 每成功 acquire/decode 一步恰好一行 typed fact，与对应 Outcome 同 commit；Process/Snapshot 只存 UUID/digest 引用 | `NH3-T01` | `high` |
| `NH3-02` | Phase 1 | AcquireDecodeHistory | `add` | 同上 migration；`src/runtime/intake/acquisition_ingest.py:89,579-676`（覆盖点，`NH3-A01`） | 按 Execution/step/ordinal append-only；同 step 二次成功拒绝；rollback 零残行；path digest 稳定可恢复读 | `NH3-T01` | `high` |
| `NH3-03` | Phase 2 | MIME/opaque/OPC | `update` | `src/runtime/intake/types.py:174-220`（`NH3-A02` 正例 sniff）；`src/runtime/intake/acquisition_ingest.py:553-564` | ZIP/OPC 不得成 `text/plain`；declared/verified 分账；PDF/image 撒谎 422 `ACQUISITION_MEDIA_MISMATCH` | `NH3-T02` | `medium` |
| `NH3-04` | Phase 2 | Text-layer observation | `update` | `src/runtime/intake/types.py:100-171`（`NH3-A02` 反例）；`intake/pdf/__init__.py:48-50`（能力码对照） | 无层 → `text_layer=absent` 观察码，**禁止** decode 抛 `CLEAN_OCR_CAPABILITY_UNAVAILABLE`；present/absent/encrypted/corrupt 可分 | `NH3-T03` | `high` |
| `NH3-05` | Phase 2 | Honest print result | `add` | `src/runtime/intake/acquisition_ingest.py:533-536`；`src/runtime/intake/clean_preflight.py:46-71`（禁猜） | acquire 产出 `representation_kind=print_pdf` 且 bytes 以 `%PDF-` 起；profile 非常量；无 browser → typed fail | `NH3-T04` | `high` |
| `NH3-06` | Phase 3 | Declared forward path | `update` | NH2 已声明边（只读）；`src/runtime/workflow/runtime_materialize.py:101-117`；`src/contracts/workflow/models.py:249-255` | 已声明边 history 长度=2、两路径 digest 不同、同路径稳定；无边 409；重复 step 拒绝；禁 try-all | `NH3-T05` | `high` |
| `NH3-07` | Phase 4 | Policy/actual split | `migrate` | `src/persistence/migrations/001_initial.sql:245-246`；🆕 `019_nh3_actual_s05_binding.sql`；`src/runtime/task/task_create.py:179-180,337-340`（`NH3-A04`） | 旧列逻辑隔离；legacy/unsealed/sealed 可 SQL 区分；旧值不得写入新 actual；`rg` 新 domain/wire 对旧列零 actual 读者 | `NH3-T06` | `high` |
| `NH3-08` | Phase 4 | Seal CAS | `update` | `src/runtime/workflow/runtime_outcome.py:88-137`（`NH3-A03`） | route Outcome + actual unsealed→sealed CAS + clean eligibility 同 UoW；中途 crash 无半封；异 digest `ConflictError` 409 | `NH3-T07` | `high` |
| `NH3-09` | Phase 4 | Actual-only chain | `update` | `src/runtime/workflow/runtime_core.py:888-917`；`src/runtime/workflow/runtime_materialize.py:555-591`；`src/runtime/intake/acceptance_snapshot.py:140-151`；`src/runtime/intake/clean_preflight.py:376,395,479,498`；`src/services/scatter_intake.py:582-603` | ProcessCommand/Candidate/Snapshot/Gate/child 只读 actual 或明确 unsealed；unsealed 拒 clean；零 domain 冒充 | `NH3-T07` | `high` |
| `NH3-10` | Phase 5 | 三窗与 full_task | `update` | `src/runtime/task/task_commands.py:237-311`（`NH3-A05`）；`src/runtime/intake/acquisition_intents.py:25-54`；`src/persistence/migrations/001_initial.sql:198-219` | seal 前 crash 仍 unsealed；seal 后 retry exact；`full_task` 新 generation 的 actual digest **等于** 旧 sealed；rebuild 不写新 actual；upgrade 入口=0 | `NH3-T08` | `high` |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — durable rows

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH3-01` | RepresentationFact | a) 冻结字段闭集与 `schema_version`（至少含：execution/process/step_key、capability、`representation_kind`、declared/detected/verified media、raw_byte_digest/size、`text_layer` 或 `main_text_presence`、canonicalizer/observer 身份与 version、profile 非恒定身份）。b) 成功 Outcome 路径在 `runtime_outcome.py:88-137` 同一 `tx` 内 INSERT fact（可经 `outcome_committer` 扩展，不得事后补写）。c) Process output / Snapshot 只存 fact UUID + content digest，禁止把 JSON blob 当第二 SSOT。d) 注册 projection：guard 只读闭集字段，缺键/未知 fail-closed。e) 失败 Outcome 不写成功 fact。f) 回滚 UoW → 零 fact 行。 | 🆕 `018_nh3_representation_fact_history.sql`；🆕 `src/contracts/intake/representation.py`；`src/runtime/workflow/runtime_outcome.py:88-137`；`src/services/artifacts.py`（`OutcomeArtifactCommitter`） | 权威行存在且与 Outcome CAS 同命运 | `NH3-T01` | 成功一步一行；rollback 无残行 |
| `NH3-02` | AcquireDecodeHistory | a) 按 `(execution_uuid, step_key, ordinal)` append-only。b) 同 step 已有成功行 → 第二次成功拒绝（409/Conflict，不 UPDATE 覆盖）。c) `representation_path_digest = H(ordered step_key × capability × raw_byte_digest × representation_kind × observer_version)`。d) recovery 经 `PersistencePort`/`UnitOfWork.fetch*` 读有序行，禁止 sqlite3 直读。e) 删除/停止对 `state["acquisition_evidence"]` / `state["decode_evidence"]` 的覆盖权威（`acquisition_ingest.py:89,660`）；旧键最多作兼容投影。 | `src/runtime/intake/acquisition_ingest.py:89,579-676,660`；同上 migration | history 可证路径顺序 | `NH3-T01` | 二次成功拒绝；path digest 稳定 |

### 4.2 Phase 2 — 诚实表示

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH3-03` | MIME/opaque/OPC | a) 保留 PDF/image 魔数 mismatch fail-closed（`types.py:209-217`）。b) `PK\x03\x04` → ZIP/OPC，不得因 UTF-8 合法被标 `text/plain`。c) 裸 UTF-8 JSON/HTML/plain 仍走文本。d) 高位 office/opaque 不得 `utf-8-sig` 成功前进（替换 `acquisition_ingest.py:561-564`）。e) declared 与 verified 分账写入 fact；不以 Content-Type 单独当 verified。 | `src/runtime/intake/types.py:174-220`；`src/runtime/intake/acquisition_ingest.py:541-564` | opaque 进不了文本 decode | `NH3-T02` | ZIP≠plain；mismatch 422 |
| `NH3-04` | PDF observation | a) 废除 `_extract_pdf_text` 把无 Tj 当 OCR 未部署（`types.py:154-159`）。b) 观察出口闭集：`present` / `absent` / `encrypted` / `corrupt`（无 `%PDF-` 或无法解析 → corrupt；`/Encrypt` 且无可用层 → encrypted）。c) 无层是 **观察码** 写入 fact，decode 成功（作为观察），**不是** `CLEAN_OCR_CAPABILITY_UNAVAILABLE` 422。d) 该 OCR 码仅保留给 clean 侧能力未部署（`intake/pdf/__init__.py:48-50` 的 503 族）。e) observer 身份/version 进 fact 与 path digest。f) 空字符串不得当 `present`。OCR 真实供给属 NH6。 | `src/runtime/intake/types.py:31-34,100-171`；`src/runtime/intake/acquisition_ingest.py:611-619` | 无盗码 | `NH3-T03` | decode 源码与单测均不再抛 OCR-unavail |
| `NH3-05` | Honest print | a) print 边产出 `representation_kind=print_pdf` 且 body 以 `%PDF-` 起。b) `browser_profile` 必须是真实 capability/profile 身份，禁止常量 `injected-browser-renderer.v1`（删除 `acquisition_ingest.py:536`）。c) 独立 budget/evidence；render 成功不得顶替 print。d) `_clean` **禁止**用 representation 反推 `web.browser_print_pdf`（`clean_preflight.py:46-71`）；未声明/未封禁 print 不得猜。e) 无 print/browser 注入 → typed 能力失败（503 族），不得写 rendered 假成功。L2 可用返回真 PDF bytes 的测试 port，但不得标 L3 live（`FG-NH-01`）。 | `src/runtime/intake/acquisition_ingest.py:474-536`；`src/runtime/intake/clean_preflight.py:46-71` | print 诚实 | `NH3-T04` | 真 PDF + 非常量 profile；无供给 typed fail |

### 4.3 Phase 3 — 声明式再获取

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH3-06` | Declared forward path | a) route/guard 读 durable fact projection，不读 handler 内存。b) 仅当 NH2 已声明正向边且 fact 满足 eq 谓词（如 `main_text_presence=absent`）才 materialize 下一 acquire。c) 第二次成功 acquire append history ordinal=2，不覆盖 ordinal=1。d) 无声明边 → 409/route_false，保持原 history。e) 同 step 重复成功拒绝。f) 禁止 try-all-acquire、while-until-nonempty、handler 暗升 static→browser。g) `unknown` fail-closed，不命中 browser 边（`T-O-402`）。h) preflight 不得再用起点 `acquisition_mode` 否定已声明再获取（`clean_preflight.py:629-657` 必须改读 history 末步 capability）。 | `src/runtime/workflow/runtime_materialize.py:93-117,119-168`；NH2 kind 图；`src/runtime/intake/clean_preflight.py:629-657` | 有限路径可证 | `NH3-T05` | history=2；digest 分叉；无边失败 |

### 4.4 Phase 4 — S05 分账

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH3-07` | Policy/actual split | a) 保留 `domain_binding_digest` 为 policy。b) 新增 nullable `actual_binding_digest` + 显式 `actual_binding_state`（至少 `legacy_unverifiable` / `unsealed` / `sealed`）+ `seal_generation`。c) 旧物理 `s05_binding_digest` 从新 domain/wire/ProcessCommand/Snapshot/Gate/child **逻辑隔离**；repository 只以 `legacy_policy_alias_digest` 暴露。d) 旧行一律 `legacy_unverifiable`，**禁止**用 domain hash backfill actual。e) 新 ingest Execution 创建时 actual 为 `unsealed` + NULL digest，不得再写 `s05_binding_digest=domain`（删除 `task_create.py:180` 的盗用赋值作为新路径权威）。f) 物理 rename/retire 不在本 AP（待兼容证明）。g) 读者审计：新代码路径不得把旧列当 actual。 | `src/persistence/migrations/001_initial.sql:245-246`；🆕 `019_nh3_actual_s05_binding.sql`；`src/runtime/task/task_create.py:179-180,337-340` | 三态可 SQL 区分 | `NH3-T06` | 零 backfill；零新 actual 读者读旧列 |
| `NH3-08` | Seal CAS | a) 前置：acquire/decode facts 已在更早 Outcome 提交。b) selected-route Outcome、actual `unsealed→sealed` 单 CAS、clean Process eligibility 在 **同一** `runtime_outcome.py:88-137` `tx`。c) actual digest 聚合有序 history + selected route identity + clean `process_key`/strategy（禁止再哈希整个 config snapshot 冒充）。d) commit 之后才 outbox/dispatch clean。e) 同 route/digest replay 返回原 seal；异 route/digest → `ConflictError` 409。f) v1 禁止 route 与 seal 两提交。g) crash 在本 UoW 提交前：仍 unsealed，可在已声明边重算（W-SEL）；提交后禁止重选（W-SEAL）。 | `src/runtime/workflow/runtime_outcome.py:88-137,130-137` | 单 CAS 无半封 | `NH3-T07` | 同 UoW；异 digest 409 |
| `NH3-09` | Actual-only chain | a) `ProcessCommand.binding_digest` 对 clean 及之后必须指向 **sealed actual**（替换 `runtime_core.py:914` 只填 domain）。b) CandidateSet / Snapshot / Gate target / scatter child 未封复制 unsealed 标记，已封只复制 actual digest。c) 改 `runtime_materialize.py:559,590` 读者：扫描必须改读 actual。d) unsealed 不得 materialize 成功 clean（fail-loud）。e) traceback/proof 引用 actual，不得引用 legacy alias。 | `src/runtime/workflow/runtime_core.py:888-917`；`src/runtime/workflow/runtime_materialize.py:555-591`；`src/runtime/intake/acceptance_snapshot.py:140-151`；`src/runtime/intake/clean_preflight.py:376,395,479,498`；`src/services/scatter_intake.py:582-603` | 传播链无伪值 | `NH3-T07` | 跨表审计零 domain 冒充 |

### 4.5 Phase 5 — replay 法律

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH3-10` | 三窗与 full_task | a) **W-SEL（seal 前 crash）**：facts 已写、actual 仍 unsealed；恢复可在已声明边重算；零向量。b) **W-SEAL 后 Process retry**：复制 exact sealed actual 与 selected `process_key`；禁止 handler 换工人。c) **`full_task`**：即使 `current_generation+1` 新 Execution 行，也 **exact copy** `actual_binding_digest/state/seal_generation` 以及 policy/workflow pin（扩展 `task_commands.py:293-311`，今日只复制旧 `s05_binding_digest`）。禁止「新 generation 即清 actual」。d) **rebuild/metadata 法律**：不 acquire 外源、不 bind 源通道工人、不写新 actual；只引用 frozen admitted clean（`acquisition_intents.py:25-54` 的输入法保留，过程 reclean 的旁路落地 NH8）。e) `index.rebuild` 不碰 S05。f) `restart_scope` 仍仅 `full_task\|atomic_intake_item`（`001_initial.sql:198-219`）；**upgrade 入口扫描 = 0**，不扩第八 intent。 | `src/runtime/task/task_commands.py:237-311`；`src/runtime/intake/acquisition_intents.py:25-54,90-93`；`src/persistence/migrations/001_initial.sql:198-219`；`src/workflows/lsrag_definition.py:234-240` | 三窗可分；upgrade 不存在 | `NH3-T08` | exact copy；rebuild 无新 actual；upgrade=0 |

---

## 5. Phase 详情

### 5.1 Phase 1 — durable rows

- **Phase 目标**：typed append-only 行成为表示唯一权威，并与 Outcome 同命运。
- **本 Phase 对应编号**：`NH3-01` / `NH3-02`
- **本 Phase 新增文件**：`src/persistence/migrations/018_nh3_representation_fact_history.sql`；`src/contracts/intake/representation.py`；`src/runtime/intake/representation_history.py`（append/unique/path-digest 辅助）；`tests/integration/test_nh3_fact_history_uow.py`
- **本 Phase 修改文件**：`src/runtime/workflow/runtime_outcome.py:88-137`；`src/runtime/intake/acquisition_ingest.py:89,579-676,660`；`src/services/artifacts.py`（如 committer 需挂 fact）
- **本 Phase 删除文件**：无
- **具体功能预期**：
  1. 一次成功 decode 提交后，经 Port 查询 fact 行数 = 1，history 行数 = 1，且 `process_uuid` 与 Outcome 行一致。
  2. 在 `validate_and_commit` 之后、Process CAS 之前注入失败 → 两表行数均为 0。
  3. 同 `step_key` 第二次成功 → `ConflictError`/等价 409，原行 digest 不变。
  4. Process `payload_extra` / output JSON 不含完整 fact 正文，只含 UUID/digest。
  5. 未知 projection 键 → guard fail-closed，不选边。
  6. 失败 disposition 不插入成功 fact（可有失败事件，但不充当 path digest 输入）。
- **对应测试台账项**：`NH3-T01`（详见 §8）
- **收口标准**：每 success step 一行且 rollback 无残行；二次成功拒绝。
- **本 Phase 风险提醒**：`R-F03` 双 SSOT。若 output JSON 与 row 并存且读者仍吃 JSON，视为本 Phase 失败。

### 5.2 Phase 2 — 诚实表示

- **Phase 目标**：bytes 观察诚实；观察码与能力码分账；print 合同可测。
- **本 Phase 对应编号**：`NH3-03` / `NH3-04` / `NH3-05`
- **本 Phase 新增 / 修改 / 删除文件**：`src/runtime/intake/types.py:31-34,100-220`；`src/runtime/intake/acquisition_ingest.py:474-564,611-632`；`src/runtime/intake/clean_preflight.py:46-71`；🆕 `tests/unit/test_nh3_sniff_opc_opaque.py`；🆕 `tests/integration/test_nh3_print_fact.py`；♻️ `tests/unit/test_ns5_phase4.py` / `tests/unit/test_intake_source_capabilities.py` / `tests/unit/test_intake_clean_dispatch.py`（断言迁移）
- **具体功能预期**：
  1. `PK\x03\x04` + ASCII 不得 verified=`text/plain`。
  2. 声明 `application/pdf`、实为 HTML → 422 `ACQUISITION_MEDIA_MISMATCH`。
  3. `%PDF-` 无文本层 → fact `text_layer=absent`，**不**抛 `CLEAN_OCR_CAPABILITY_UNAVAILABLE`。
  4. 含 `/Encrypt` 无可用层 → `encrypted`；坏签名 → `corrupt`/`DECODE_PDF_INVALID`，二者均非 OCR 盗码。
  5. `rg CLEAN_OCR_CAPABILITY_UNAVAILABLE src/runtime/intake/types.py` = 0。
  6. print 测试 port 返回 `%PDF-` + 非恒定 profile；无 port → 503 族，state 无 `rendered` 假成功。
  7. `_clean` 源码不再用 `representation_kind==print_pdf` 选择 `WEB_BROWSER_PRINT_PDF`。
- **对应测试台账项**：`NH3-T02` / `NH3-T03` / `NH3-T04`
- **收口标准**：无盗码、无常量 profile、print 真 PDF。
- **本 Phase 风险提醒**：不要把 L2 注入 print port 写成 NH6 live。OCR 供给仍 503 是诚实负例，不是通道 DoD（`T-O-376` 属 NH7）。

### 5.3 Phase 3 — 声明式再获取

- **Phase 目标**：绑定前有限、已声明、无环正向再获取可被 history 证明。
- **本 Phase 对应编号**：`NH3-06`
- **本 Phase 新增 / 修改 / 删除文件**：`src/runtime/workflow/runtime_materialize.py:93-168`；`src/runtime/intake/clean_preflight.py:619-704`；🆕 `tests/integration/test_nh3_declared_reacquire.py`
- **具体功能预期**：
  1. 已声明 static→browser 且 `main_text_presence=absent` → 两步 acquire 都成功，history length=2。
  2. 两条不同已声明路径 → path digest 不等；同一路径重放 digest 相等。
  3. 无声明边的空壳 → 停在第一步，HTTP/业务码 409 族，不调用 browser port。
  4. 同 step 再成功 → 拒绝，history 仍为 2。
  5. try-all 或 handler 内改 mode → 架构测试失败（源码/行为均不得存在）。
  6. `main_text_presence=unknown` 不命中 browser 边。
- **对应测试台账项**：`NH3-T05`
- **收口标准**：两路径 digest 不同，同路径稳定，重复 step 拒绝，未声明边 409。
- **本 Phase 风险提醒**：依赖 NH2 边；若图上仍每 kind 仅 1 acquire，本 Phase 不得用 13 张复制图伪造「第二条边」。

### 5.4 Phase 4 — S05 分账

- **Phase 目标**：两本账可区分；seal 一次；传播链不再贩卖 domain 伪值。
- **本 Phase 对应编号**：`NH3-07` / `NH3-08` / `NH3-09`
- **本 Phase 新增 / 修改 / 删除文件**：🆕 `src/persistence/migrations/019_nh3_actual_s05_binding.sql`；`src/runtime/task/task_create.py:179-180,337-340`；`src/runtime/workflow/runtime_outcome.py:88-137`；`src/runtime/workflow/runtime_core.py:888-917`；`src/runtime/workflow/runtime_materialize.py:555-591`；`src/runtime/intake/acceptance_snapshot.py:140-151`；`src/runtime/intake/clean_preflight.py:376-498`；`src/services/scatter_intake.py:582-603`；`src/contracts/runtime/models.py:13-29`；🆕 `tests/unit/test_nh3_s05_migration.py`；🆕 `tests/e2e/test_nh3_seal_crash_windows.py`（**层 = L2/F**，目录名不升层）
- **具体功能预期**：
  1. 迁移后三类行可被 SQL 分开：legacy 旧列非空 ∧ actual NULL/state=`legacy_unverifiable`；新 unsealed actual NULL ∧ state=`unsealed`；sealed 非空 ∧ state=`sealed`。
  2. 迁移脚本不得 `UPDATE ... SET actual_binding_digest = s05_binding_digest` 或 `= domain_binding_digest`。
  3. 新 Task create 不再执行 `s05_binding_digest=prepared.domain_binding_digest` 作为 actual 权威。
  4. seal 与 route 同 `tx`：commit 前 kill → 无 sealed 行、无 clean eligibility、无 selected-route durable。
  5. 第二次不同 digest seal → `ConflictError` 409；相同 digest replay 幂等。
  6. clean Command 在 unsealed 时 fail-loud；sealed 后 Command 携带 actual 而非 domain。
  7. Gate/child/Snapshot 已封字段等于 actual，不等于 domain。
- **对应测试台账项**：`NH3-T06` / `NH3-T07`
- **收口标准**：三态可分；single-CAS；跨表审计零 domain 冒充。
- **本 Phase 风险提醒**：`R-F02` backfill；`FG-NH-08` 64-hex 形状相同。`rg` 新读者是 DoD 硬闸，不是附赠扫描。

### 5.5 Phase 5 — replay 法律

- **Phase 目标**：三窗分测；retry 不热切；upgrade 不存在。
- **本 Phase 对应编号**：`NH3-10`
- **本 Phase 新增 / 修改 / 删除文件**：`src/runtime/task/task_commands.py:237-311`；🔱 `tests/unit/test_task_projections.py`；🆕 `tests/unit/test_nh3_lineage_matrix.py`
- **具体功能预期**：
  1. seal 前崩溃：恢复后 `actual_binding_state='unsealed'`，允许在已声明边重选。
  2. seal 后 Process retry：`actual_binding_digest` 字节级相等，`process_key` 不变。
  3. `full_task`：`current_generation` +1，新 Execution 的 actual digest **等于** 旧 sealed；policy/workflow pin 同时 exact。
  4. rebuild Task：无新 source acquire worker 的 actual 写入；不把 `rebuild_from_accepted_clean_artifact` 写成外源 S05。
  5. `restart_scope` 字面仍只有两个；源码/DDL/API 无 `upgrade` intent/scope。
  6. 禁止实现「新 generation 清空 actual 以便换工人」。
- **对应测试台账项**：`NH3-T08`
- **收口标准**：exact copy；rebuild 无 source worker actual；upgrade 入口=0。
- **本 Phase 风险提醒**：`R-F12`。RA08 `NH-RA08-B04` 过程仍 reclean——本 AP 只立法，不得假装 NH8 已旁路。

---

## 6. 依赖的冻结设计决策（只读引用）

> 只引 Q 编号与 T-O-ID，不复制业主长文、不改口、不开新槽。

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Q10 / `T-O-390` | `pre-charter-qna.md` §1 Q10；§5 台账 | Phase 4 分账、隔离旧列、禁 backfill；`NH3-07/09` | 保持 `draft` blocked；回 QNA 追加，不在 AP 改口 |
| Q12 / `T-O-392` | 同上 Q12 | Phase 1 行权威与同 UoW；`NH3-01/02` | 禁止用单槽 JSON 顶替 |
| Q20 / `T-O-400` | 同上 Q20 | Phase 4 seal 线性化；`NH3-08`；W-SEL/SEAL | 禁止两提交「补偿」方案 |
| Q21 / `T-O-401` | 同上 Q21 | Phase 5 `full_task` exact；upgrade OOS；`NH3-10` | 禁止新 generation 清 actual |
| Q22 / `T-O-402` | 同上 Q22 | Phase 2/3 observer 三态；仅 absent 命中 browser 边 | 禁止 LLM/质量分路由 |
| Q23 / `T-O-403` | 同上 Q23 | Phase 2 print 独立 capability/profile；禁常量 profile | print 供给仍交 NH6 |
| Q27 / `T-O-407` | 同上 Q27 | `NH3-10` 写 rebuild 法律；实现交 NH8 | 禁止本 AP 建 no-op cleaner |
| Q8 / `T-O-388` | `pre-initial-planning-qna.md` | 有限声明式再获取；decode 观察；print 诚实 | 禁止暗升/try-all |
| Q4/Q6 / `T-O-378` | 同上 | 假 PDF / OCR 盗码不得冒充完成 | 观察/能力必须分码 |
| Q3 / `T-O-383` | 同上 | 绑定后不换工人；seal 后 crash 不得重选 | 与 `T-O-400` 共同约束 W-SEAL |
| Q18 / `T-O-398` | `pre-charter-qna.md` Q18 | 有界 substrate；NH1 失败 STOP | 禁止退回 duplication |
| Q26 / `T-O-406` | 同上 Q26 | 本 AP 最低层 = 台账 C；fault 不是替代层 | waiver 只延期不降层 |
| `P-S05-schema CORRECT` | `final-execution-plan.md` §3 | 旧行永久 unverifiable；显式 state | 禁止「改列解释」 |
| `T-R-NH-22/23` | final §2.2 | HEAD 仍 domain=s05；`full_task` 已 exact 复制旧列 | 本 AP 必须 migration + 改复制目标 |

---

## 7. 内置 Reference-Anchor 锚区

> HEAD `1221aa1` 行号于 2026-08-29 独立 `read_file` 核验；与 custom prompt / final §7.3 台账 B **无漂移**。补充行号在备注标明。

### 7.1 锚表（本计划工作要落在哪些既有代码 / 新建点上）

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| `NH3-A02` | `src/runtime/intake/types.py:174-220` | `_sniff_media_type` + `_verified_media_type`：魔数 sniff；PDF/image mismatch 422 | `NH3-03` 保留 fail-closed，扩展 ZIP/OPC | `✅ 复用` | 正例部分；`:218-220` octet 回退 declared 需收紧 |
| `NH3-A03` | `src/runtime/workflow/runtime_outcome.py:88-137` | Outcome + artifact commit + Process CAS + `_route_after_terminal_process_tx` 同一 `tx` | `NH3-01/02/08` fact append 与 seal CAS 必须挂这里 | `✅ 复用` | `:89-92` 已写明 caller mutation 不得在 fence 外存活 |
| `NH3-A05` | `src/runtime/task/task_commands.py:237-311` | `full_task` 新 generation 整行复制 workflow/config/`s05_binding_digest` | `NH3-10` 对 **new actual 列** 同样 exact copy | `♻️ 重 substrate` | 机制正例、值错误（复制的是伪 s05）；`T-R-NH-23` |
| `NH3-A07` | 🆕 `src/persistence/migrations/018_*.sql` + `019_*.sql`；🆕 `src/contracts/intake/representation.py` | 关系型 fact/history 与 actual 列；不引入 Temporal | `NH3-01/02/07` | `🆕 净新` | 外部只借「写入后再 resume 不重选」；见 §7.3 |
| `NH3-A02+` | `src/runtime/intake/types.py:209-217` | PDF/image declared≠detected → `ACQUISITION_MEDIA_MISMATCH` | `NH3-03` 回归必须保留 | `✅ 复用` | 已建好，别删 |
| — | `src/runtime/intake/acquisition_intents.py:25-54` | rebuild 读 frozen accepted clean，禁止伪造外源 S05 | `NH3-10` 法律输入法 | `✅ 复用` | 过程仍 reclean 是 RA08 缺口，落地 NH8 |
| — | `src/runtime/workflow/runtime_materialize.py:119-168` | `_typed_route_context_tx` 从 durable 行投影，缺键 fail-closed | `NH3-06` 扩展 representation projection | `✅ 复用` | 今日无 representation 键（`:101-117`） |
| — | `intake/pdf/__init__.py:48-50` | OCR 未注入 → `CLEAN_OCR_CAPABILITY_UNAVAILABLE` **503** | `NH3-04` 能力码对照：此码留在 clean，不进 decode | `✅ 复用` | 观察≠能力 |
| — | `src/persistence/ports.py:10-27` | `UnitOfWork.fetchone/fetchall`；`PersistencePort.transaction` | 全部 L2 查询 | `✅ 复用` | 禁 sqlite3 直读（`FG-NH-12`） |

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| `NH3-A01` | `src/runtime/intake/acquisition_ingest.py:579-676`：`:579-594` 构造 acquire evidence；`:597-676` `_decode`。`:89` 覆盖写单槽 `acquisition_evidence`；`:660` 覆盖写单槽 `decode_evidence`；再获取会丢掉第一步 | `T-O-392/388`；`T-R-NH-05`；RA03 `NH-RA03-B03`；D-13 应对两键分账，不得把 660 算进 `acquisition_evidence`。不得把单槽 JSON 冒充 history |
| `NH3-A01+` | `:535-536` `representation_kind` 仅 `rendered\|transferred`，永不 `print_pdf`；`browser_profile="injected-browser-renderer.v1"` | `T-O-388/403`；`NH-RA03-B02/B12` |
| `NH3-A02` ⛔ | `src/runtime/intake/types.py:144-171` literal `(...) Tj` 扫描；无层抛 `CLEAN_OCR_CAPABILITY_UNAVAILABLE` 422（`:154-159`）；decoder 自称 `local-pdf-literal-text.v1` 且写死 `text_layer=present` | `T-O-378`；`T-R-NH-06`；`NH-RA03-B01/B06`。ISO ToUnicode 才是提取语义，本 AP 先换观察出口 |
| `NH3-A04` | `src/runtime/task/task_create.py:179-180` `s05_binding_digest=domain_binding_digest`；`:337-340` 缺省再回落到 domain；`001_initial.sql:245-246` NOT NULL | `T-O-390`；`T-R-NH-04/22`；`FG-NH-08`。禁止 backfill |
| `NH3-A06` | `src/runtime/intake/clean_preflight.py:46-71` 用 representation 反推 strategy；`:108-121` `dispatch_clean` 表外 remap；`:629-657` 用起点 mode 校验 capability | `T-O-382/383/388`；RA02 `NH-RA02-B06`。未封禁 clean |
| — | `src/runtime/workflow/runtime_materialize.py:559,590` Gate 传播 `s05_binding_digest` | 机制可留、值必须改读 actual（`NH3-09`） |
| — | `src/runtime/workflow/runtime_core.py:914` `binding_digest=process["domain_binding_digest"]` | clean Command 无法证明绑后工人 |
| — | `src/runtime/intake/acceptance_snapshot.py:151`；`clean_preflight.py:395,498`；`scatter_intake.py:602-603` 复制 domain 别名进名为 s05 的列 | `NH-RA02-B05` |
| — | `src/runtime/intake/acquisition_ingest.py:561-564` 非 PDF/image 强制 UTF-8 | `NH-RA03-B05`；docx 物理不可达 |
| — | `src/contracts/workflow/models.py:249-255` representation-aware guard = 0 | `NH-RA03-B04`；无 fact 则再获取无法合法 |
| — | `tests/e2e/test_source_capability_paths.py:99-101` monkeypatch fetcher | `T-O-378`；`FG-NH-01`；本 AP 不得沿用为 DoD |
| — | 把旧列改 nullable / 非空 64-hex ⇒ actual | `T-O-390`；final NOT-成功 |
| — | Temporal Event History / Cadence GetVersion / Kafka EOS 口头 exactly-once | RA02 §7/§8；`O-NH-06` |
| — | existing-object upgrade / 第八 intent / `restart_scope` 扩值 | `O-NH-03`；`001_initial.sql:198-219` 仅两值 |
| — | 两提交 seal（route 先、seal 后或相反） | `T-O-400`；会产生无名态，W-SEAL 无法测 |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：
  - RA02（主面）：[`assessment-analysis-02-s05-two-stage-binding-and-recovery.md`](../../eval/new-harvest/reference-anchor/assessment-analysis-02-s05-two-stage-binding-and-recovery.md) — `NH-RA02-B01..B07` 列名盗用 / 无未封闭态 / Command 无 actual / 无 seal 事务 / 传播伪值 / handler 暗调 / evidence 单值。
  - RA03（主面）：[`assessment-analysis-03-representation-and-reacquisition.md`](../../eval/new-harvest/reference-anchor/assessment-analysis-03-representation-and-reacquisition.md) — `NH-RA03-B01..B06/B11/B12` 盗码、print 不诚实、单槽 history、opaque UTF-8、常量 profile。
  - RA08（邻面，只消费）：[`assessment-analysis-08-publication-and-intake-lifecycle.md`](../../eval/new-harvest/reference-anchor/assessment-analysis-08-publication-and-intake-lifecycle.md) `NH-RA08-B04` — rebuild 输入是 frozen clean，**过程仍** decode+`clean.extract.deterministic`。本 AP `NH3-10` 写「不 bind / 不写新 actual / 不重 acquire」法律；guard 旁路落地 NH8，禁止在本 AP 用 no-op cleaner 冒充 skip。
- **外部借鉴 verdict（不进 §7.1 混用）**：
  - `🔶部分借` Stripe 幂等：同 digest replay / 异 digest 409；不借 TTL。
  - `🔶部分借` WHATWG sniff：保留魔数 + 补 ZIP；不实现完整 UA 表。
  - `⛔反例` Temporal/Cadence 当引擎；CF Browser Rendering；`action_branch`；legacy restarter 热切。
  - `🆕净新` 七表 Execution 上 unsealed→sealed-once + 关系型 history。
- **安全 / 信任边界威胁模型（不得空）**：

  | 威胁 | 攻击 / 失败窗 | 对应 Truth / FG | 本 AP 控制 | 测试 |
  |------|----------------|-----------------|------------|------|
  | **binding 热切** | route 已提交、actual 仍 unsealed 时恢复重选工人；或 seal 后 handler `dispatch_clean` 换 `process_key` | `T-O-383/400`；W-NH-SEL/SEAL | 同 UoW 单 CAS；commit 后才 dispatch；unsealed 拒 clean | `NH3-T07` |
  | **假 lineage** | domain/任意 64-hex 冒充 actual；旧列 backfill；Gate/child 继续贩卖伪值 | `T-O-390`；`FG-NH-08`；`R-F02` | 显式 state；legacy unverifiable；读者审计 | `NH3-T06` + `NH3-T07` 传播节点 |
  | **半封 clean 派遣** | Outcome 成功但 actual 未封即派 clean；crash 留下可热切窗口 | `T-O-400`；`R-F03` | eligibility 进同一 `tx`；fault 注入 W-SEAL | `NH3-T07` |
  | **表示伪造** | 无层盗 OCR 码；常量 print profile；ZIP 当 plain；monkeypatch 当 live | `T-O-378/388`；`FG-NH-01` | 观察/能力分码；禁常量；L2 不升 L3 | `NH3-T02/T03/T04` |
  | **upgrade 偷换工人** | 借 `full_task` 新 generation 或 rebuild 清 actual | `T-O-401/407`；`R-F12/R-F11` | exact copy；upgrade 入口=0 | `NH3-T08` |

  不可信 PDF 的 in-process 解析 DoS/RCE 隔离属 NH6/`T-O-399`；本 AP 只要求观察出口诚实，不选 parser 库。

---

## 8. 测试台账

> 最低层以 final 台账 C「层」列为准。fault 是标签不是替代层。PASS 证据四元组形态：`commit SHA + pytest node PASS + Truth/Q + UTC`（执行期回填 SHA，本 AP 不伪造）。

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| `NH3-T01` | fact/history append 同 UoW；rollback 无残行；同 step 二次成功拒绝 | 集成/F | L2 | 🆕 `tests/integration/test_nh3_fact_history_uow.py` | `NH3-01/02` → durable facts | `commit SHA + node PASS + Q12/T-O-392 + UTC` |
| `NH3-T02` | sniff/OPC/opaque；declared/verified 分账；mismatch 422 | 短途 | L1 | 🆕 `tests/unit/test_nh3_sniff_opc_opaque.py` | `NH3-03` → durable facts（表示身份） | `commit SHA + fixture suite PASS + Q12 + UTC` |
| `NH3-T03` | PDF observation 不盗码；present/absent/encrypted/corrupt | 短途 | L1/L2 | ♻️ PDF 单测 + 🆕 观察矩阵 | `NH3-04` → representation honesty | `commit SHA + present/absent/encrypted PASS + Q13/T-O-378 + UTC` |
| `NH3-T04` | honest print fact：真 `%PDF-` + 非常量 profile；无 browser typed fail | 集成 | L2 | 🆕 `tests/integration/test_nh3_print_fact.py` | `NH3-05` → representation honesty | `commit SHA + PDF/profile PASS + Q23/T-O-403 + UTC` |
| `NH3-T05` | declared reacquire history=2；路径 digest；重复拒绝；无边失败 | 集成 | L2 | 🆕 `tests/integration/test_nh3_declared_reacquire.py` | `NH3-06` → finite path | `commit SHA + path digest PASS + Q8/Q22 + UTC` |
| `NH3-T06` | legacy/unsealed/sealed 可 SQL 区分；旧值不得写入新 actual；读者扫描 | migration | L2 | 🆕 `tests/integration/test_nh3_s05_migration.py` + 🆕 `tests/domain/test_nh3_actual_readers_scan.py` | `NH3-07` → actual truth | `commit SHA + migration query PASS + Q10/T-O-390 + UTC` |
| `NH3-T07` | route+seal 同 UoW；W-SEL/SEAL；传播只读 actual | fault | L2/F | 🆕 `tests/e2e/test_nh3_seal_crash_windows.py` | `NH3-08/09` → actual truth + propagation | `commit SHA + W-SEL/SEAL PASS + Q20/T-O-400 + UTC` |
| `NH3-T08` | `full_task` exact；rebuild 不写新 actual；upgrade 入口=0 | replay/C | L2 | 🔱 `tests/unit/test_task_projections.py` + 🆕 lineage matrix | `NH3-10` → retry law | `commit SHA + generation matrix PASS + Q21/Q27 + UTC` |

### 8.2 复用台账（沿用 / fork 的既有用例明细）

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/unit/test_ns5_phase4.py::test_pdf_rejects_latin1_garbage` | `♻️ 沿用` 并改期待 | 无层/非 Unicode 不得再匹配 `CLEAN_OCR` 盗码 | 已存在；今日允许 `CLEAN_OCR`（反例） |
| `tests/unit/test_intake_clean_dispatch.py::test_runtime_clean_step_delegates_to_intake` | `♻️ 沿用` | 保留「`_clean` 不含 OCR 盗码」；**不够**，须由 `NH3-T03` 覆盖 decode 路径 | 已存在 PASS，但只扫 `_clean` |
| `tests/unit/test_intake_source_capabilities.py::test_browser_ocr_and_vision_are_explicit_controlled_capability_failures` | `♻️ 沿用` | OCR/Vision **clean** 503 仍是能力码正例 | 已存在；与 decode 观察分账 |
| `tests/unit/test_task_projections.py::test_generation_restart_and_lineage_are_task_scoped_summaries`（`:156`；体内 `:175-201` 不是独立 node） | `🔱 fork` | + 断言新 Execution `actual_binding_digest` 等于 previous sealed；不得只断言 `current_generation==2` | 已存在；今日只测 scope=`full_task` |
| `tests/e2e/test_source_capability_paths.py` | `⛔ 不沿用为 DoD` | monkeypatch fetcher | 反例；`FG-NH-01` |
| `tests/unit/test_dispatch_*.py` 仅 INSERT `s05_binding_digest` | `⛔ 不足` | `NH-RA02-B11` 有列无断言 | 必须由 `NH3-T06` 取代 |

### 8.3 分层与跑法（各类型在哪跑、何时跑）

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `uv run pytest tests/unit/test_nh3_*.py tests/domain/test_nh3_actual_readers_scan.py -q` | L1 | 每 PR |
| 集成 UoW | `uv run pytest tests/integration/test_nh3_*.py -q` | L2 | 每 PR / Phase 收口（含 T06 migrate） |
| fault | `uv run pytest tests/e2e/test_nh3_seal_crash_windows.py -q` | L2/F | Phase 4 收口；**不是** L3 default-root |
| replay | `uv run pytest tests/unit/test_nh3_lineage_matrix.py tests/unit/test_task_projections.py::test_generation_restart_and_lineage_are_task_scoped_summaries -q` | L2 | Phase 5 收口 |
| mega/soak/L3/L4 | 本 AP 不跑 | — | 交 NH7/NH9 |

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖 default-root 真实 Chromium print / PDF parser / OCR 供给（理由：`T-O-393/399/403` 属 `S-NH-F6`）→ `AP-NH6`。
- 不覆盖 10+3 live-to-retrieval 与 namespace query（理由：`T-O-376/381` 属 NH7/NH9；本 AP 无 L3/L4 义务）→ `AP-NH7` / `AP-NH9`。
- 不覆盖 rebuild intent-guard 真正旁路 decode+clean 的图改线（理由：`T-O-407` 属 NH8；本 AP 只证「不写新 actual / upgrade=0」）→ `AP-NH8`。
- 不覆盖 W-NH-PROCESS/FANIN/PUB/OUTBOX 全窗 mega（理由：RA09 / NH9）→ `AP-NH9`。
- 不把 `tests/e2e/test_nh3_seal_crash_windows.py` 的目录名当成 L3 完成。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 必带四元组；计数 ≠ 价值。
- 本 AP 适用 FG（必须在对应细则点名）：`FG-NH-01`（T04 不得标 live）、`FG-NH-06`（空 clean 非本 AP 成功）、`FG-NH-08`（T06/T07）、`FG-NH-12`（T01/T06/T07 禁 sqlite3）、`FG-NH-13`（不得用 L1 顶 T01/T07 的 L2）、`FG-NH-17`（不得改期待值掩盖盗码）。
- `degraded` 必带机器可读 reason；pre-existing 失败必带 git 证据。
- 安全项 T07 必须含攻击向量：两提交、异 digest 覆盖、unsealed 派 clean。

#### `NH3-T01`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/integration/test_nh3_fact_history_uow.py::test_success_step_appends_one_fact_and_history_row`；`::test_rollback_leaves_zero_fact_rows`；`::test_second_success_on_same_step_rejected` |
| 用途 | 证明 `NH3-01/02`；FG-NH-12；durable facts；NOT-成功「单槽 JSON 冒充 history」 |
| 前置 | 真实 `PersistencePort.transaction()`；fixture Execution/Process running；**禁止** `sqlite3.connect` 读 Turso 文件 |
| 步骤 | a) 创建 acquire 成功 Outcome 并 commit。b) Port 查询 fact/history 行。c) 在 committer 后、CAS 前 raise，断言 rollback。d) 同 step 再提交成功 Outcome。 |
| 断言细节 | HTTP 不涉及；DB：成功后 fact=1 history=1 且 `ordinal=1`；rollback 后两表 0；二次成功 → `ConflictError` 409，原 `raw_byte_digest` 不变；output manifest 仅 UUID/digest |
| 负例 | 事后补写 history（Outcome 已 succeeded 再 INSERT）必须失败；覆盖 UPDATE 必须不存在 |
| 跑法 | `uv run pytest tests/integration/test_nh3_fact_history_uow.py -q` |
| 层与来源 | L2；`🆕` |

#### `NH3-T02`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/unit/test_nh3_sniff_opc_opaque.py::test_pk_magic_is_zip_not_text_plain`；`::test_utf8_html_still_text_html`；`::test_declared_pdf_html_body_mismatch_422`；`::test_high_bit_office_bytes_not_utf8_success` |
| 用途 | 证明 `NH3-03`；RA03 `NH-A-03-01/04` |
| 前置 | 纯函数调用 `_sniff_media_type` / `_verified_media_type` / `_representation_from_bytes`；夹具：`PK\x03\x04`+ASCII、裸 UTF-8 `<html>`、`%PDF-` 与 HTML 对调 |
| 步骤 | a) sniff 各夹具。b) verified 分账写入（declared 保留、verified 独立）。c) mismatch 路径。 |
| 断言细节 | ZIP/OPC verified ∈ `{application/zip, application/vnd.openxmlformats-officedocument.*}` 而非 `text/plain`；mismatch `MkbError.code=="ACQUISITION_MEDIA_MISMATCH"` 且 HTTP 422；declared 字段仍记录谎言值但不等于 verified |
| 负例 | 仅靠 `Content-Type: text/plain` 让 PK 前进；octet 回退把 HTML 声明当成 verified PDF |
| 跑法 | `uv run pytest tests/unit/test_nh3_sniff_opc_opaque.py -q` |
| 层与来源 | L1；`🆕` |

#### `NH3-T03`

| 字段 | 要求 |
|---|---|
| 测试位置 | ♻️ 改 `tests/unit/test_ns5_phase4.py::test_pdf_rejects_latin1_garbage`；🆕 `tests/unit/test_nh3_pdf_observation.py::test_present_text_layer`；`::test_absent_does_not_raise_ocr_unavailable`；`::test_encrypted_observation`；`::test_corrupt_signature`；源码扫描 `::test_decode_path_source_excludes_ocr_capability_code` |
| 用途 | 证明 `NH3-04`；`T-O-378`；FG-NH-17（不得把盗码改成「期望 422 OCR」继续绿） |
| 前置 | PDF 夹具：含未压缩 Tj 的最小 `%PDF-`；仅 `%PDF-1.4\n%EOF`；含 `/Encrypt` 无 Tj；非 PDF 字节 |
| 步骤 | a) 观察 present。b) 无层走 decode 观察出口。c) encrypted/corrupt。d) `inspect.getsource` decode 路径。 |
| 断言细节 | present → `text_layer=="present"` 且文本非空；absent → 不 raise `CLEAN_OCR_CAPABILITY_UNAVAILABLE`，fact 观察码 `absent`；decode 源码零该字符串；clean 侧 `intake/pdf/__init__.py` 仍可保留 503 能力码 |
| 负例 | 空字符串当 present；无层 422 OCR；把 503 能力码改写到 decode |
| 跑法 | `uv run pytest tests/unit/test_nh3_pdf_observation.py tests/unit/test_ns5_phase4.py::test_pdf_rejects_latin1_garbage -q` |
| 层与来源 | L1/L2；`♻️` + `🆕` |

#### `NH3-T04`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/integration/test_nh3_print_fact.py::test_print_fact_is_real_pdf_bytes_and_nonconstant_profile`；`::test_missing_browser_typed_fail_does_not_write_rendered` |
| 用途 | 证明 `NH3-05`；`T-O-388/403`；FG-NH-01（本节点 L2，**不得**标 live） |
| 前置 | L2 注入 print port **返回真实 `%PDF-` bytes** 与可变 profile 字符串（如 `chromium.print_pdf:<version>`）；对照未注入 port 的 pipeline。禁止 patch `_browser_fetcher` 后声称 L3 |
| 步骤 | a) 走已声明 print acquire。b) 读 fact/history。c) 卸 port 再跑。d) 源码断言无 `injected-browser-renderer.v1`。 |
| 断言细节 | `representation_kind=="print_pdf"`；`raw`/`output_bytes.startswith(b"%PDF-")`；profile ≠ `"injected-browser-renderer.v1"` 且非 None；无 port → 503 `ACQUISITION_BROWSER_CAPABILITY_UNAVAILABLE` 或 print 专用 typed 码，state 无 rendered 成功 fact |
| 负例 | HTML 当 print；clean 猜测 `print_pdf`；常量 profile |
| 跑法 | `uv run pytest tests/integration/test_nh3_print_fact.py -q` |
| 层与来源 | L2；`🆕` |

#### `NH3-T05`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/integration/test_nh3_declared_reacquire.py::test_declared_static_to_browser_history_len_2`；`::test_two_paths_differ_same_path_stable`；`::test_undeclared_edge_409`；`::test_repeat_step_rejected`；`::test_unknown_main_text_does_not_take_browser_edge` |
| 用途 | 证明 `NH3-06`；`T-O-388/402`；finite path |
| 前置 | NH2 已编译的 kind 图夹具（含 static→browser 声明边与不含该边的对照图）；durable fact `main_text_presence=absent`；真实 UoW |
| 步骤 | a) 第一步 static acquire+decode 写 fact。b) guard 命中已声明 browser 边。c) 第二步 append。d) 对照无边/unknown/重复。 |
| 断言细节 | history `COUNT(*)==2`；两条路径 `representation_path_digest` 不等；同路径两次独立 Execution digest 相等；无边 → 409 且 browser port 调用次数=0；重复 step → 拒绝且 COUNT 仍 2 |
| 负例 | try-all；覆盖第一步 evidence；handler 改 `acquisition_mode` |
| 跑法 | `uv run pytest tests/integration/test_nh3_declared_reacquire.py -q` |
| 层与来源 | L2；`🆕` |

#### `NH3-T06`

| 字段 | 要求 |
|---|---|
| 测试位置 | L2 🆕 `tests/integration/test_nh3_s05_migration.py::test_legacy_unsealed_sealed_sql_distinguishable`；`::test_migration_does_not_copy_domain_into_actual`；`::test_new_create_does_not_write_domain_as_actual`。scan 🆕 `tests/domain/test_nh3_actual_readers_scan.py::test_architecture_scan_zero_actual_readers_of_legacy_column` |
| 用途 | 证明 `NH3-07`；`T-O-390`；`FG-NH-08`；`R-F02` |
| 前置 | 空库经真实 `PersistencePort.migrate()`；插入 HEAD 形状旧行（`s05_binding_digest=domain` NOT NULL）；再插入新 unsealed/sealed 行。查询只经 Port。L2 落 `tests/integration/`（仓内 UoW 惯例），禁止仅 unit 目录冒充 migrate |
| 步骤 | a) migrate。b) 三类 SELECT（Port）。c) 读 migration SQL 文本禁止 backfill 赋值。d) domain scan：`rg` 新 domain/wire（`src/contracts/`、`src/runtime/task/`、`src/runtime/workflow/`、`src/runtime/intake/acceptance_snapshot.py`、`src/services/scatter_intake.py`）对旧列作 **actual 读者** 命中=0。 |
| 断言细节 | legacy：`actual_binding_digest IS NULL` ∧ `actual_binding_state='legacy_unverifiable'`；unsealed：NULL + `'unsealed'`；sealed：64-hex + `'sealed'` 且 **≠** `domain_binding_digest`（除非偶然碰撞，夹具禁止相等）；scan artifact 写入 evidence `migrations/` |
| 负例 | `UPDATE actual=s05_binding_digest`；新 create 仍 `s05=domain` 当权威 |
| 跑法 | `uv run pytest tests/integration/test_nh3_s05_migration.py tests/domain/test_nh3_actual_readers_scan.py::test_architecture_scan_zero_actual_readers_of_legacy_column -q` |
| 层与来源 | L2（migrate+Port）+ L1 scan 同 Test-ID；`🆕` |

#### `NH3-T07`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_nh3_seal_crash_windows.py::test_w_sel_crash_before_seal_leaves_unsealed`；`::test_w_seal_route_and_actual_same_uow`；`::test_mid_uow_crash_no_half_seal`；`::test_different_digest_conflict_error`；`::test_propagation_readers_see_only_actual_or_unsealed` |
| 用途 | 证明 `NH3-08/09`；W-NH-SEL/SEAL；`T-O-400/383`；`FG-NH-08`；propagation 收口 |
| 前置 | 真实 UoW；facts 已先行 commit；可注入的 Outcome 事务钩子（kill/raise）。**层标注 L2/F**，不调用 `create_app()` 冒充 L3 |
| 步骤 | a) W-SEL：facts 在、seal 前 raise → state unsealed、无 clean process ready、零向量行。b) 同 UoW 成功 → route selected + actual sealed + eligibility 同行可见。c) CAS 后、dispatch 前不需要第二提交。d) 异 digest 再 seal。e) 查询 Command/Candidate/Snapshot/Gate/child。 |
| 断言细节 | 成功：三条件同 commit；crash：`actual_binding_state!='sealed'` 且无 clean eligibility 行；异 digest → `ConflictError` status=409；传播列 ≠ `domain_binding_digest`；unsealed 调 `_clean` fail-loud |
| 负例 | route 先 commit seal 后 commit；用 domain 64-hex 填 actual；unsealed 派 clean |
| 跑法 | `uv run pytest tests/e2e/test_nh3_seal_crash_windows.py -q` |
| 层与来源 | L2/F；`🆕` |

#### `NH3-T08`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🔱 `tests/unit/test_task_projections.py::test_generation_restart_and_lineage_are_task_scoped_summaries` 加 `actual_binding_digest` 断言（不得只断言 `current_generation==2`）；🆕 `tests/unit/test_nh3_lineage_matrix.py::test_full_task_copies_exact_sealed_actual`；`::test_process_retry_keeps_actual`；`::test_rebuild_does_not_write_new_actual`；`::test_upgrade_restart_scope_and_intent_absent` |
| 用途 | 证明 `NH3-10`；`T-O-401/407`；`R-F12`；NOT-成功「full_task 清 actual」 |
| 前置 | 先有 sealed Execution；`RetryRequest` 走真实 `task_commands.retry`；rebuild 走 `_acquire_rebuild` 路径的 UoW fixture |
| 步骤 | a) seal。b) Process retry。c) `full_task` 新 generation。d) rebuild Task。e) 扫描 DDL/API/models 无 upgrade scope/intent。 |
| 断言细节 | 新 generation `actual_binding_digest == previous.actual_binding_digest` 且 state 仍 `sealed`；`workflow_revision_uuid`/`compiled_digest`/`domain_binding_digest` exact；rebuild：无新 `actual` UPDATE、无外源 acquire fact 冒充；`CHECK (restart_scope IN ('atomic_intake_item', 'full_task'))` 仍两值；`rg upgrade` 在 restart/intent 合同命中=0 |
| 负例 | 新 generation 把 actual 置 NULL；rebuild 写 source worker actual；新增 `restart_scope='upgrade'` |
| 跑法 | `uv run pytest tests/unit/test_nh3_lineage_matrix.py tests/unit/test_task_projections.py::test_generation_restart_and_lineage_are_task_scoped_summaries -q` |
| 层与来源 | L2；`🔱` + `🆕` |

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| NH1 STOP | chosen-shape / S05 spike 失败 | `high`（DAG 硬门） | 本 AP 不得开工替代方案；reopen `T-O-398` |
| NH2 边未交付 | 无声明正向边则 T05 无法诚实 | `high` | Phase 3 阻塞；禁止复制 13 profile（`FG-NH-09`） |
| `R-F02` 旧 s05 backfill | migration 按 64-hex 判断 | `high` | 显式 state + T06 禁 copy |
| `R-F03` 双 SSOT | output JSON 与 row 并存 | `high` | 引用-only 架构测试挂 T01 |
| `R-F12` full_task 清 actual | 以 new generation 为由 | `high` | T08 字节级相等 |
| `R-F11` rebuild 偷 reclean | HEAD 过程仍 clean | `medium`（法律本 AP，实现 NH8） | T08 不写新 actual；不声称旁路已落地 |
| 半封派遣 | 两提交 | `high` | T07 W-SEAL |
| L2 目录名 e2e | 误标 L3 | `medium` | §8.3 钉层；`FG-NH-13` |
| print/OCR 供给 | 本 AP 无真实 binary | `low`（OOS） | typed fail；交 NH6 |

### 9.2 约束与前提

- **技术前提**：NH1 proof baseline PASS；NH2 kind-only resolver 与 representation predicates 已注册；Turso schema 可 forward-only migrate。
- **运行时前提**：L2 测试用 PersistencePort；不要求 default-root browser。
- **组织协作前提**：不重开 Q10–Q27；物理 rename 另兼容证明；S05 §4.6 erratum 由 calibration 文档 append（本 AP 不改 QNA）。
- **上线 / 合并前提**：`NH3-T01..T08` 全 PASS + `rg` 读者扫描 + evidence pack 目录齐；文档状态仍 `draft` 直至独立执行回填（本轮禁止标 executed）。

### 9.3 文档同步要求

- 需要同步更新的设计文档：S05/D04/glossary **append-only calibration 指针**（`LegacyS05AliasDigest` / `ActualS05Binding` 已在 glossary；本 AP 执行时回指 migration 文件名）
- 需要同步更新的说明文档 / README：无强制；禁止改 QNA / final-execution-plan / RA
- 需要同步更新的测试说明：evidence pack `docs/evidence/new-harvest/AP-NH3/`（见 §10）

### 9.4 完成后的预期状态

1. 每个成功 acquire/decode 步骤有且仅有一行 fact，与 Outcome 同 commit；单槽 JSON 不再是权威。
2. Execution 可表达 unsealed；sealed actual 与 domain policy 可分；旧行 unverifiable。
3. 下游 clean Command / Gate / child 只看见 actual 或明确 unsealed；unsealed 不能成功清洁。
4. `full_task` 新 generation 复制 exact sealed actual；仓库无 upgrade 入口。
5. 表示层无 OCR 盗码、无常量 print profile；ZIP 不再伪装 plain。NH6/NH8 仍各自未交付供给与旁路。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

### 10.1 收口硬闸

所有台账 C 项必须 **PASS 且四元组证据齐全**。本 AP 无 L3/L4 退出项；L2/F 的 T07 视为退出硬闸。

1. **durable facts**：每成功 acquire/decode 一步恰好一行 fact 且与对应 Process Outcome 同一 commit；rollback 后 `RepresentationFact` 与 `AcquireDecodeHistory` 行数为 0；同 step 第二次成功被拒绝且原行不变（由 `NH3-T01` 证明；观察夹具由 `NH3-T02/T03` 支撑）。
2. **finite path**：对已声明的两条不同正向路径，`representation_path_digest` 不同；同一路径重放 digest 稳定；重复 step 拒绝；未声明边 409 且不调用下一 acquire port（由 `NH3-T05` 证明）。
3. **actual truth**：SQL 可区分 legacy_unverifiable / unsealed / sealed；seal 与 selected-route Outcome 同 UoW 且仅一次 CAS；异 digest `ConflictError` 409；中途 crash 无半封（由 `NH3-T06` + `NH3-T07` 证明）。
4. **propagation**：对 sealed Execution，ProcessCommand / CandidateSet / Snapshot / Gate / scatter child 的 binding 字段等于 `actual_binding_digest` 或显式 unsealed 标记，**不等于** `domain_binding_digest`；unsealed 拒 clean（由 `NH3-T07` 传播节点证明）。
5. **retry law**：`full_task` 新 generation 行的 `actual_binding_digest` **等于** 旧 sealed 值；rebuild 不写入新 actual、无外源 source worker；`restart_scope`/intent 无 upgrade 入口（由 `NH3-T08` 证明）。
6. **representation honesty**：decode 路径零 `CLEAN_OCR_CAPABILITY_UNAVAILABLE`；print fact 为 `%PDF-` bytes 且 profile 非常量（由 `NH3-T03` + `NH3-T04` 证明）。
7. **读者扫描**：`rg` 新 domain/wire 对旧 `s05_binding_digest` 零 actual 读者（由 `NH3-T06` scan 节点证明；final DoD 硬闸）。

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| 每成功 step 一行 fact 且 rollback 无残行 | `NH3-01/02` | `NH3-T01`（T02/T03 支撑夹具） | `commit SHA + pytest node PASS + Q12 + UTC` | `未观察` |
| 两路径 digest 不同，同路径稳定，重复 step 拒绝，未声明边 409 | `NH3-06` | `NH3-T05` | `commit SHA + history rows/hash PASS + Q8/Q22 + UTC` | `未观察` |
| 旧/unsealed/sealed 可分；旧值不得写入新 actual | `NH3-07` | `NH3-T06` | `commit SHA + migration query PASS + Q10 + UTC` | `未观察` |
| seal 同 UoW 且 single-CAS；crash 无半封 | `NH3-08` | `NH3-T07` | `commit SHA + W-SEL/SEAL PASS + Q20 + UTC` | `未观察` |
| 下游只见 actual 或 unsealed，零 domain 冒充 | `NH3-09` | `NH3-T07` 传播节点 | `commit SHA + cross-table audit PASS + Q10/Q20 + UTC` | `未观察` |
| full_task 复制 exact；rebuild 无 source worker actual；upgrade 无入口 | `NH3-10` | `NH3-T08` | `commit SHA + lineage matrix PASS + Q21/Q27 + UTC` | `未观察` |
| 无盗码、无常量 profile、print 真 PDF | `NH3-04/05` | `NH3-T03/T04` | `commit SHA + evidence rows PASS + Q8/Q23 + UTC` | `未观察` |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | §10.1 七条谓词全部为真；`M-NH-01`/`M-NH-02` 已 migrate；upgrade 入口=0 |
| 测试 | `NH3-T01..T08` 全 PASS；退出硬闸项四元组齐全；层不低于台账 C |
| 文档 | evidence pack 目录存在且文件名如下；本 AP 仍待执行回填，不把 draft 标 executed |
| 风险收敛 | `R-F02/03/12` 有对应 FAIL 测试；NH8 reclean 旁路标为 residual 而非本 AP PASS |
| 可交付性 | NH6 可消费 print/PDF 观察合同；NH8 可消费 rebuild 法律；NH9 可注入 W-SEL/SEAL |

**evidence pack**（final §9.3；本 AP 只规定文件名与内容，不伪造 SHA）：`docs/evidence/new-harvest/AP-NH3/`

1. `manifest.json`：commit、Truth/Q、`NH3-01..10`、`NH3-T01..08`、UTC
2. `tests.txt`：上表全部 pytest node、exit code、duration、environment
3. `queries/`：fact/history 计数、三态 SQL、传播链 audit、path digest
4. `migrations/`：018/019 before/after schema、legacy 行样本、证明无 backfill
5. `security/`：W-SEL/SEAL 注入记录；本 AP 无 SBOM 义务（binary 属 NH6）
6. `closure.md`：台账 D 逐目标 PASS/FAIL 与 NOT-success 扫描

PASS 证据四元组形态：`commit SHA + pytest node PASS + Truth/Q + UTC`。

### 10.4 NOT-成功识别

> 任一退出硬闸测试 `degraded / 未观察` ⇒ **不得标 `executed`**。

抄 final §7.3 并补本 AP 假绿：

- 把旧 `s05_binding_digest` 改 nullable 后当作 actual 已完成
- 用 `domain_binding_digest` backfill `actual_binding_digest`
- 单槽 `acquisition_evidence` JSON 冒充 history
- route 与 seal 两提交
- `full_task` 因新 generation 清空 actual
- 非空 64-hex ⇒ actual（`FG-NH-08`）
- decode 无层仍抛 `CLEAN_OCR_CAPABILITY_UNAVAILABLE` 但测试改期待值继续绿（`FG-NH-17`）
- 常量 `injected-browser-renderer.v1` 仍在但测试只断言 kind 字符串
- L1 sniff 绿顶替 T01/T07 的 UoW（`FG-NH-13`）
- sqlite3 直读 Turso 当 rollback 证明（`FG-NH-12`）
- monkeypatch browser 后把 T04 标 live（`FG-NH-01`）
- rebuild 仍跑 deterministic clean 却声称 exact-clean 已落地（那是 NH8；本 AP 若如此宣称即失败）
- 新增 upgrade intent/scope
- NH1 spike 失败后继续本 AP 或静默换 duplication

---

## 11. 执行日志回填（仅 `executed` 状态使用）

文档状态为 `draft`，本节按模板占位；执行完成后改用 `respond-execution-log` 厚版回填。residual（NH6 供给、NH8 guard 旁路、NH9 mega）交后继 AP，**不回填本阶段**。

- **实际执行摘要**：未执行。
- **Phase 偏差**（逐条带分类）：未执行。
- **阻塞与处理**：未执行。预期阻塞 = NH1/NH2 未闭合。
- **测试发现**（含全绿计数 + 新暴露事实）：未执行。
- **后续 handoff**：未执行。预定交接 NH6/NH8/NH9。

---

## 附录 · 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| `v0.1` | `2026-08-29` | Grok workflow | 由 final §7 派生 |
| `v0.2` | `2026-08-29` | Grok fix-fleet | 吸收已核实 review：`NH3-A01` 把 `:660` 标为 `decode_evidence` 覆盖；T06 L2 落到 `tests/integration/` 且 scan node 写入跑法；T08 🔱 钉 `::test_generation_restart_and_lineage_are_task_scoped_summaries`；T02 来源只标 🆕 |
