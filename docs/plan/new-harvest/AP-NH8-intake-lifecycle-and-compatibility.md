# Nano-Agent 行动计划

> 服务业务簇: `MKB / new-harvest / intake-four-channel-live`
> 计划对象: 七意图 applicability + rebuild/metadata exact-clean 旁路 + deactivate/reactivate/delete/index.rebuild 的 query 法 + old-pin compat
> 类型: `upgrade`
> 作者: `Grok workflow new-harvest-nh6-nh9-action-plans`
> 时间: `2026-08-29`
> 文件位置: `src/contracts/api/models.py`；`src/contracts/workflow/models.py`；`src/runtime/intake/acquisition_intents.py`；`src/runtime/intake/clean_preflight.py`；`src/runtime/intake/acquisition_ingest.py`；`src/runtime/intake/index_rebuild_plan.py`；`src/runtime/task/task_create.py`；`src/runtime/task/task_commands.py`；`src/services/config_snapshots.py`；`src/services/intake_lifecycle/lifecycle_apply.py`；`src/services/intake_lifecycle/targets.py`；`src/workflows/lsrag_definition.py`；`tests/unit/test_nh8_intent_applicability.py`；`tests/e2e/test_intake_rebuild_metadata.py`；`tests/e2e/test_intake_reactivate.py`；`tests/e2e/test_index_rebuild.py`；`tests/e2e/test_nh8_delete_tombstone.py`；`tests/e2e/test_nh8_api_item_intents.py`；`tests/unit/test_workflow_revision_compatibility.py`；`tests/unit/test_nh8_lineage_matrix.py`
> 上游前序 / closure:
> - `AP-NH7` 10+3 vertical live-to-retrieval 已收口（DAG：NH8 依 NH7 + NH5；本 AP 不重铺正格）
> - `AP-NH5` `NH5-T08-B` process-absence **handoff 红灯**（HEAD 预期 ≠0；禁止 xfail）；本 AP **`NH8-T03`/`NH8-03`** 转绿（`NH8-T02` 只做 rebuild 同构，不得冒充 T08-B 关闭点）
> - `AP-NH3` `NH3-10` restart/rebuild **法律**（full_task exact；rebuild 不写新 actual；upgrade 入口=0）；本 AP 落地 guard 与 lineage 分账
> - `AP-NH2` `NH2-T06` old pin 共存 + telemetry；本 AP `NH8-07` 做有界 retire/rollback
> 下游交接:
> - `AP-NH9` closed-set / crash 全窗 / Capstone I–J；本 AP 只保证功能 query 法（Capstone H），不注入 W-NH-* kill
> 关联设计 / 调研文档:
> - `docs/eval/new-harvest/final-execution-plan.md` v1.0 `frozen` §7.8（本 AP 唯一执行基线）
> - `docs/eval/new-harvest/final-execution-plan.md` §4.2 / §6 / §9 / §11.A
> - `docs/eval/new-harvest/reference-anchor/assessment-analysis-08-publication-and-intake-lifecycle.md`（RA08 主面）
> - `docs/eval/new-harvest/reference-anchor/assessment-analysis-02-s05-two-stage-binding-and-recovery.md`（RA02 restart 只消费）
> 冻结决策来源:
> - `docs/eval/new-harvest/pre-charter-qna.md` v1.0：Q21/Q25/Q27 → `T-O-401` / `T-O-405` / `T-O-407`；Q14 → `T-O-394`；Q18 → `T-O-398`（只读引用；本 action-plan 不填写 Q/A）
> - `docs/eval/new-harvest/pre-initial-planning-qna.md` v0.5：`T-O-381` / `T-O-383`
> grounding 来源:
> - `eval-reference-anchor RA08` + HEAD `1221aa1` 独立 `read_file` + final §7.8 四台账
> 关联 reference-anchor:
> - [`assessment-analysis-08-publication-and-intake-lifecycle.md`](../../eval/new-harvest/reference-anchor/assessment-analysis-08-publication-and-intake-lifecycle.md)
> - [`assessment-analysis-02-s05-two-stage-binding-and-recovery.md`](../../eval/new-harvest/reference-anchor/assessment-analysis-02-s05-two-stage-binding-and-recovery.md)（restart 只消费；禁止与 `G-NH-19` 共用）
> 文档状态: `executed`

**台账 ID 区间（final §11.A / §7.8）**：`NH8-01..08` / `NH8-A01..06` / `NH8-T01..10`。禁止重编号、合并或删除这些 ID。

---

## 0. 执行背景与目标

HEAD `1221aa1` 已有七意图 Literal 闭集（`src/contracts/api/models.py:278-286`）、rebuild 从 accepted clean Artifact 入场（`acquisition_intents.py:25-93`）、lifecycle 同 UoW 撤 serving/pointer/vector（`lifecycle_apply.py:34-134`）、`index.rebuild` 不造 Revision（`index_rebuild_plan.py:23-50`）、以及 `full_task` 整行复制旧 `s05_binding_digest`（`task_commands.py:237-311`）。它**尚未**交付产品法：

1. 七意图合法/非法格没有稳定 public error 合同；非法组合若漏过 pydantic 仍可能建 Task（`T-R-NH-21`；`NH-RA08-B05`）。
2. rebuild / 有变更 metadata 读的是 frozen clean，图却仍 `acquire.to_decode`（`lsrag_definition.py:299-306`）并 `dispatch_clean`（`clean_preflight.py:28-127`）——输入 exact，过程再跑 inline `clean.extract.deterministic`（`T-R-NH-17`；`NH-RA08-B04`；`R-F11`）。
3. deactivate/reactivate/index.rebuild e2e **调用** `retrieval:search` 但 **无** `namespace_key`（HEAD 文件 0 命中），当前合同必 422（`src/contracts/api/models.py:505-510`；`src/services/retrieval/retrieval_request.py:265-270`）；且用 `sqlite3.connect` 直读 Turso（`FG-NH-05/12`）。reactivate 的 unit 正例成立（`NH-C-74`），检索终验不是 HEAD 绿件。
4. existing-object new-cleaner 在 DDL/七意图中无入口（`001_initial.sql:198-219` 仅 `full_task|atomic_intake_item`）；禁止借 rebuild/retry 偷换（`O-NH-03`；`T-O-401`；`R-F12`）。

本 AP 消费已冻结 `T-O-401/405/407/394/398`，把 applicability、exact-clean guard 旁路、lifecycle **query 法**、index 新 generation、API Item 同服务、old-pin 有界退役与 restart 分账落成可交付物。不重开 Q10–Q27，不把 GPT/Grok 推荐再选一次。`P-exact-clean` 已由 final 裁定 `REFINE`（intent guard 真正旁路，禁 no-op worker）。Capstone **H** 由本 AP 的 Test-ID 覆盖，不得悬空。

- **服务业务簇**：`new-harvest` / `S-NH-F8`
- **计划对象**：七意图 applicability + rebuild/metadata exact-clean 旁路 + deactivate/reactivate/delete/index.rebuild 的 query 法 + old-pin compat
- **本次计划解决的问题**：
  - 非法格仍可能被解释成 skip/no-op/系统错误，或滑向 7×4 施工（`T-O-405`；`FG-NH-15`）
  - rebuild/metadata 偷 reclean，digest/strategy 漂移（`T-O-407`；`R-F11`）
  - lifecycle/index 只改 DB 列、无 namespace 的 search 被当成可检索；reactivate 被当成恢复旧 serving（`NH-C-70/71/74`）
  - old pin 退役过早绞杀 in-flight；upgrade 混入 retry/rebuild（`R-F04`；`O-NH-03`）
- **本次计划的直接产出**：
  - 七意图合法/非法 applicability 表 + machine-readable code 闭集 + admission 零 Task/Process 审计
  - registered intent guard 旁路 acquire/decode/clean（process 计数=0；clean digest exact）
  - deactivate/reactivate/delete/index.rebuild 的 namespaced L4 query 证明（含 API Item）
  - old pin 可完结 + 新 Task kind-only + 有界 retire；lineage：full_task exact、index 不碰 S05、upgrade 入口=0
  - evidence pack 目录 `docs/evidence/new-harvest/AP-NH8/`（只登记文件名，不伪造 SHA）
- **本计划不重新讨论的设计结论**：
  - 422=形状/非法组合，409=状态/并发；非法格 admission fail-loud 且不建 Task/Process；禁止 7×4（来源：Q25 / `T-O-405`）
  - rebuild/changed-metadata 以 registered intent guard 旁路 acquire/decode/clean；禁 no-op cleaner；只 replay frozen admitted clean；changed metadata 仅重做 semantic consumers（来源：Q27 / `T-O-407`）
  - Process/`full_task` 复制 exact sealed actual；index.rebuild 不碰 S05；existing-object upgrade OOS（来源：Q21 / `T-O-401`）
  - generic 四字段非 unknown；metadata 切代继承 clean（来源：Q14 / `T-O-394`；由 NH5-08 / T08-A 交付，本 AP 不重做权威）
  - reactivate 不得恢复 `serving_revision` 或把旧 generation 标 active（来源：RA08 `NH-C-74`；Q25 生命周期 query 法）

---

## 1. 执行综述

### 1.1 总体执行方式

先冻结 **applicability + error code 闭集**（admission 拒绝、零 Task/Process），再在既有七表上用 **registered_request_intent guard** 把 rebuild/changed-metadata 从 acquire/decode/clean **画边旁路**（不新建 no-op cleaner、不改 cuts/g0），然后把 lifecycle/index 的证明从「DB 列 / 无 namespace 200」升级为 **Layer-A namespaced query 法**，最后用同一套服务覆盖 API Item，并以 old-pin 有界退役 + restart 分账矩阵收口。执行策略是「先合同后图、先旁路后 query、先 single 后 API、先共存后有界退役」。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | applicability | `M` | 合法输入/state/code；admission 拒绝；零 Task/Process | NH7 收口；NH5 facet/namespace 合同 |
| Phase 2 | exact-clean | `L` | rebuild guard 旁路；metadata no-change/changed；零 clean Process；digest exact | Phase 1；消费 `NH5-T08-B` 红灯与 `NH3-10` 法律 |
| Phase 3 | lifecycle query | `M` | deactivate/reactivate/delete + L4 empty/conflict；`NH-C-74` | Phase 1；NH1 namespace harness |
| Phase 4 | index | `M` | 新 generation；零 Revision/source/clean；旧代不命中 | Phase 1 |
| Phase 5 | API Item | `L` | 与 single 同服务；无 child kernel；七意图测试 | Phase 2–4 |
| Phase 6 | compat + lineage | `L` | old pin 完结；新 Task kind-only；upgrade 入口=0 | Phase 2；NH2-T06；NH3-T08 |

> `规模` 是描述性提示，不是开工体量闸。

### 1.3 Phase 说明

1. **Phase 1 — applicability**
   - **核心目标**：把 RA08 §2.3 合法/非法格写成 charter/API 合同，登记 code 闭集，admission 失败不 INSERT `mkb_tasks`/`mkb_processes`。
   - **为什么先做**：没有稳定非法格合同，后续旁路会被测成 skip/no-op；`FG-NH-15` 会把 28 格当施工义务。
2. **Phase 2 — exact-clean**
   - **核心目标**：intent guard 不 materialize acquire/decode/clean Process；replay frozen admitted clean；T08-B 红→绿。
   - **为什么放在这里**：合同先锁「什么叫非法」，再改图；否则会用 no-op cleaner 冒充 skip（`R-F11`）。
3. **Phase 3 — lifecycle query**
   - **核心目标**：withdraw 同 UoW 之后，namespaced search 空；reactivate 仍空直到新 publish；delete tombstone + rebuild 409。
   - **为什么放在这里**：旁路落地后 rebuild 才是合法的「新 publish」路径；否则 reactivate 后再 rebuild 会偷 reclean。
4. **Phase 4 — index**
   - **核心目标**：active scope 新 generation；不造 Revision；零 source/clean Process；旧代 search 不命中。
   - **为什么放在这里**：与 lifecycle 分账（index 不是 ingest/reactivate）；query 法与 Phase 3 共用 namespace harness。
5. **Phase 5 — API Item**
   - **核心目标**：registered_api 事后 Item 走 **同一** lifecycle/exact-clean 服务，不进 scatter child 图。
   - **为什么放在这里**：single 合同先绿，再证明 scatter 成员不是第二套 kernel（`NH-RA08-B07`）。
6. **Phase 6 — compat + lineage**
   - **核心目标**：old pin 跑完；新 Task 只 kind graph；`full_task` exact；upgrade 入口扫描=0。
   - **为什么放在这里**：图与 intent 稳定后才能退役旧 key；lineage 矩阵消费 NH3 法律 + 本 AP 旁路。

### 1.4 执行策略说明

- **执行顺序原则**：admission 合同 → guard 画边 → query 终验 → API 同法 → compat/lineage。禁止先写 no-op cleaner 再「字节相等」。禁止 NH9 第一次补这些功能。
- **风险控制原则**：`R-F11` 用 process-absence + digest exact 双闸；`R-F12` 用 upgrade 入口=0；`R-F04` 用 telemetry + 有界 retire，禁止直接删旧 `compiled_digest`。非法格零 Task 用 DB audit，不只看 HTTP。
- **测试推进原则**：L1 合同矩阵（T01）→ L2 process/digest（T02/T03/T09/T10）→ L3 default-root + L4 namespaced search（T04..T08）。短途每 PR；spike/集成每 Phase；mega 在本 AP 收口（T02/T03/T08）；soak/crash 交 NH9。
- **文档同步原则**：error code 闭集与 applicability 表写入本 AP §4.1 与 evidence `queries/intent-matrix.json`；不改 QNA / final。`M-NH-09` 与 compat retirement review 签收进 `closure.md`。
- **回滚 / 降级原则**：guard 路由优先于 handler if。若旁路导致 in-flight old pin 409 → 停退役、保留 enabled-unselected（`NH2-07`）。禁止 waiver 把 L4 降成「DB 列已 withdrawn」。文档保持 `draft` 直至独立执行回填。

### 1.5 本次 action-plan 影响结构图

```text
七意图 / exact-clean / publication lifecycle / old-pin
├── Phase 1: applicability
│   ├── TaskCreateRequest Literal 闭集 + _PAYLOAD_MODEL
│   ├── config_snapshots.prepare / IntakeTargetResolver（admission，INSERT 前）
│   └── 非法格 422/409 code + 零 Task/Process 审计
├── Phase 2: exact-clean
│   ├── lsrag_definition registered_request_intent 画边
│   ├── 旁路 acquire.to_decode / dispatch_clean（禁 no-op worker）
│   └── frozen clean replay；metadata no-change 短路；changed 只重做 semantic consumers
├── Phase 3: lifecycle query
│   ├── lifecycle_apply 同 UoW withdraw（已有，加 L4）
│   └── namespaced search 空集 / reactivate 不 restore / delete tombstone
├── Phase 4: index
│   ├── index_rebuild_plan 新 generation、零 Revision
│   └── 旧代 pointer/vector 不命中
├── Phase 5: API Item
│   ├── 事后 Item 复用 single 服务（无 child kernel）
│   └── 七意图 mega（一成员即可，不重铺 10+3）
└── Phase 6: compat + lineage
    ├── old pin 完结 + 有界 retire/rollback
    └── full_task exact；index 不碰 S05；upgrade 入口=0
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** 七意图合法/非法 applicability + machine-readable code 闭集；422/409 分家；非法格 admission 不建 Task/Process（`NH8-01` / `T-O-405`）
- **[S2]** rebuild exact-clean：intent guard 旁路 acquire/decode/clean；读 frozen artifact；digest exact（`NH8-02` / `T-O-401/407`）
- **[S3]** metadata no-change 短路；changed 新 Revision、inherit clean、只重做 semantic/tail 切代（`NH8-03` / `T-O-394/407`）；关闭 `NH5-T08-B`
- **[S4]** deactivate/reactivate/delete 的 query 法：withdraw 同 UoW；reactivate 不 restore serving；delete tombstone + rebuild 409（`NH8-04` / `NH-C-73/74`）
- **[S5]** `index.rebuild`：active scope、新 generation、无 Revision/source/clean、旧代不命中（`NH8-05` / `NH-C-78`）
- **[S6]** API Item 与 single 同服务、无 child kernel、七意图测试（`NH8-06`）
- **[S7]** old pin 跑完、新 Task kind-only、telemetry、有界 retire/rollback（`NH8-07` / `M-NH-04`）
- **[S8]** restart/rebuild/index/upgrade 分账矩阵：full_task exact；upgrade 入口=0（`NH8-08` / `T-O-401`）

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** `O-NH-03` existing-object new-cleaner/validator upgrade（`T-O-401`；未来须新 owner-gate）
- **[O2]** NH7 10+3 正格再铺（本 AP 消费已激活格；不重跑 10 strategy）
- **[O3]** NH9 crash 全窗（`W-NH-CREATE/SEL/SEAL/PROCESS/PROM-CAT/GC-INGEST/FANIN/PUB/OUTBOX`）；本 AP 只保证功能 query 法
- **[O4]** 第五 kind、`workflow_key`、`action_branch`、CF/SMCP/R2、raw GET、生产 `--no-sandbox`、experiment 发车（`O-NH-01/04/05`；`T-O-380`）
- **[O5]** 重写 tail/g0/cuts；按通道复制 publication tail（`O-NH-02`；`T-R-NH-15` 已交付，勿重做）
- **[O6]** 通用 Workflow JOIN/DSL；云 OCR/CF/R2/SMCP runtime（`O-NH-06`）
- **[O7]** 把 PDF/browser/OCR **库名**锁成新 Truth（`T-O-393` 不锁库）
- **[O8]** 四通道 live 供给本身（属 NH6/NH7）；本 AP 用已 publication 的 Item 证生命周期

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| 七意图非法格 + code 闭集 | `in-scope` | `T-O-405`；final §7.8 `NH8-01` | 无 |
| rebuild/metadata guard 旁路 | `in-scope` | `T-O-407`；关闭 T08-B | 无 |
| lifecycle/index **query 法** | `in-scope` | Capstone H；`NH-C-70/74/78` | 无 |
| API Item 同法 | `in-scope` | `NH8-06`；`NH-RA08-B07` | 无 |
| old-pin 有界退役 | `in-scope` | `NH8-07`；NH2 只做到共存 | 无 |
| existing-object new-cleaner | `out-of-scope` | `O-NH-03` / `T-O-401` | 新 owner-gate + restart identity |
| 10+3 正格 live | `out-of-scope` | `S-NH-F7` 属 NH7 | NH7 未收口则本 AP 不得用 503 顶 L3 |
| crash 全窗 | `out-of-scope` | `S-NH-F9` 属 NH9 | 本 AP 不注入 kill |
| no-op cleaner / byte-equal worker | `out-of-scope`（禁止） | `T-O-407`；`R-F11` | 不得重评进 NH v1 |
| 7×4 笛卡尔积施工 | `out-of-scope`（禁止） | `T-O-405`；`FG-NH-15` | 不得重评 |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| `NH8-01` | Phase 1 | 七意图 applicability | `add` | `src/contracts/api/models.py:210-286,328-360`；`src/runtime/task/task_create.py:37-46,88-128`；`src/services/config_snapshots.py:136-144,474-489,518-542`；`src/services/intake_lifecycle/targets.py:37-110,153-154` | 合法格可 admission；非法格 422/409 且 `mkb_tasks`/`mkb_processes` 计数=0 | `NH8-T01` | `high` |
| `NH8-02` | Phase 2 | Rebuild exact-clean | `update` | `src/workflows/lsrag_definition.py:112-117,233-306,647-682`；`src/runtime/intake/acquisition_intents.py:25-93`；`src/runtime/intake/clean_preflight.py:28-127,706-714` | intent guard 旁路；零 acquire/decode/clean Process；clean digest exact | `NH8-T02` | `high` |
| `NH8-03` | Phase 2 | Metadata no-change/changed | `update` | `src/runtime/intake/acquisition_intents.py:115-233`；`src/workflows/lsrag_definition.py:290-297,339-347`；`src/runtime/intake/acceptance_lifecycle.py`（NH5 已切代，本 AP 只旁路 Process） | no-change 不进 LS-RAG；changed 新 Revision、inherit clean、facet 切代；零 clean Process（T08-B 转绿） | `NH8-T03` | `high` |
| `NH8-04` | Phase 3 | deactivate/reactivate/delete | `update` | `src/services/intake_lifecycle/lifecycle_apply.py:34-134,231-246`；`tests/e2e/test_intake_reactivate.py`；🆕 `tests/e2e/test_nh8_delete_tombstone.py` | withdraw 同 UoW；reactivate 不 restore；delete tombstone；namespaced search 空/冲突 | `NH8-T04` / `NH8-T05` / `NH8-T06` | `high` |
| `NH8-05` | Phase 4 | index.rebuild | `update` | `src/runtime/intake/index_rebuild_plan.py:23-50`；`src/workflows/lsrag_definition.py:233-245,647-652`；`tests/e2e/test_index_rebuild.py` | 新 generation；零 Revision/source/clean；旧代不命中 | `NH8-T07` | `medium` |
| `NH8-06` | Phase 5 | API Item 同服务 | `update` | `src/services/intake_lifecycle/lifecycle_apply.py:34-134`（SQL 核 `:108-134`；`:36-38` 仅合同注释）；`src/workflows/lsrag_definition.py`（inline 骨架）；`src/workflows/builtin_scatter.py:416-441`（child **不**跑 metadata/rebuild） | API 事后 Item 与 single 同服务；无 child kernel；七意图可测 | `NH8-T08` | `high` |
| `NH8-07` | Phase 6 | Old/new retirement | `update` | `src/runtime/workflow/runtime_core.py:88-100,591-633`；`tests/unit/test_workflow_revision_compatibility.py`；`api/app.py` compatibility_definitions | old pin 跑完；新 Task kind-only；telemetry；有界 retire/rollback | `NH8-T09` | `high` |
| `NH8-08` | Phase 6 | Restart/rebuild matrix | `update` | `src/runtime/task/task_commands.py:237-311`；`src/persistence/migrations/001_initial.sql:198-219`；🆕 `tests/unit/test_nh8_lineage_matrix.py` | full_task exact actual；rebuild replay clean；index 不碰 S05；upgrade 入口=0 | `NH8-T10` | `high` |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — applicability

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH8-01` | 七意图 applicability | **高风险，有序子步：** a) 冻结合法格表（消费 RA08 §2.3，不发明 28 格）：`intake.ingest` 唯一带 `SourceDescriptor`、四 kind 选图；`intake.rebuild` 只绑 `intake_item_uuid`[+expected revision]；`intake.update_metadata` 绑 item+已登记 semantics；`intake.deactivate`/`reactivate`/`delete` 绑 item；`index.rebuild` 绑 `scope=team\|intake_item`。b) 非法格（admission fail-loud）：第八 intent；第五 kind；caller `workflow_key`；非 ingest 带 `source`；ingest 带 lifecycle payload；deleted Item 上 rebuild/metadata/lifecycle；inactive 上 `index.rebuild`；未登记 semantic key；把六事后意图当 kind 选择器。c) HTTP：422 仅请求形状/非法组合；409 仅目标状态/并发。登记 code 闭集见本格下方（Q25 授权本 AP 登记字面）。d) **admission 点**保持 `config_snapshots.prepare`（`task_create.py:88`）在 `INSERT mkb_tasks`（`:106-128`）**之前**；`IntakeTargetResolver` 保持只读（`targets.py:25-32`）。prepare/schema 失败 ⇒ 该 `task_uuid` 的 Task/Process 行=0。禁止把 deleted 检查挪到 acquire 回调之后。e) 非 ingest 仍可复用 inline 骨架（`config_snapshots.py:474-489` purpose 仍 `intake.ingest`；`workflow_registry.py:95-103`），但不得按 kind 生造 7×4 Task。f) 失败路径：pydantic extra=`forbid` 继续 `task-schema-invalid`；resolver `ConflictError` 保持 409。g) 审计：POST 非法格后经 PersistencePort `COUNT(*)`，禁止 sqlite3。 | `src/contracts/api/models.py:210-286,328-360`；`src/runtime/task/task_create.py:37-46,88-128`；`src/services/config_snapshots.py:136-144,474-489,518-542`；`src/services/intake_lifecycle/targets.py:37-110,153-154`；`src/contracts/workflow/models.py:264-271`；`api/app.py:502` | 合法格 201 并建恰好一个 Task；非法格 422/409 + 零行 | `NH8-T01` | 非法格零 Task/Process；无 7×4 |

**本 AP 登记的 machine-readable code 闭集**（Q25：字面由 action-plan 登记；类别已冻结）：

| HTTP | code | 适用格 | 是否允许已建 Task |
|------|------|--------|-------------------|
| 422 | `task-schema-invalid` | envelope extra、payload≠intent、第八 intent Literal 失败、第五 kind discriminator、非 ingest 出现 `source`、ingest 使用 lifecycle/index payload、caller `workflow_key` 字段 | 否（admission） |
| 422 | `workflow-intent-not-supported` | purpose 映射失败（`config_snapshots.py:488` 纵深） | 否 |
| 422 | `INTAKE_INTENT_UNSUPPORTED` | 未登记 intent 漏到 pipeline（`acquisition_ingest.py:48` 纵深） | 否（若已漏建，本 AP 须前移到 admission） |
| 422 | `SOURCE_KIND_INVALID` | 未登记 kind 漏过 schema（`acquisition_ingest.py:56`） | 否（前移 admission） |
| 422 | `INTAKE_SEMANTIC_KEY_UNREGISTERED` | metadata 含未登记 semantic key（本 AP **新登记**；不得 silent drop） | 否 |
| 422 | `METADATA_SEMANTICS_EMPTY` | semantics 空（HEAD 已有） | 否 |
| 404 | `intake-item-not-found` | 目标 Item 不存在（跨 team 同码，不泄漏） | 否 |
| 409 | `intake-item-deleted` | deleted 上 rebuild/metadata/deactivate/reactivate（`targets.py:153-154`；`lifecycle_apply.py:237-243`） | 否（prepare 阶段） |
| 409 | `index-rebuild-item-not-active` | inactive Item 上 `index.rebuild`（`targets.py:107-110`） | 否 |
| 409 | `intake-revision-unavailable` / `intake-revision-mismatch` | 无 accepted revision / revision 不属于该 Item | 否 |
| 409 | `intake-item-revision-conflict` | CAS stale（并发；**已 admission** 后合法 409） | 是（非非法格） |
| 409 | `REBUILD_TARGET_STALE` / `METADATA_TARGET_STALE` | frozen target 在执行前被改（并发） | 是（非非法格） |

禁止为每个 kind×intent 发明第三 HTTP 家族。禁止用 200 + skip/no-op 顶替上表。

### 4.2 Phase 2 — exact-clean

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH8-02` | Rebuild exact-clean | **高风险，有序子步：** a) 新增 `WorkflowGuardDefinition(guard_key="request_intent_rebuild", predicate_type="registered_request_intent", operator="eq", expected_value="intake.rebuild")`（守卫类型已在 `models.py:264-271` 闭集）。b) 仿 `start.to_index_rebuild`（`lsrag_definition.py:237-245`）增加 **高于** `start.to_acquire`（priority 10）的 rebuild 边：从 `start` 进入 **非** `acquire`/`decode`/`clean` 的 replay/accept 路径（推荐：`start` → `accept_snapshot` 或薄 `replay_frozen_clean` 步；process_key **不得** 为 `intake.acquire.*` / `intake.decode.*` / `clean.*`）。c) 把 `_acquire_rebuild` 读 frozen clean 的能力（`:25-93`，`input_kind="accepted_clean_artifact"`）迁出 acquire Process：admission 已 freeze target（`config_snapshots.py:528-530`），replay 只引用该 artifact/digest。d) **删除或对 rebuild 失效** `acquire.to_decode` 默认边（`:299-306`）。`_clean`（`clean_preflight.py:28-127`）对 rebuild **不可达**；禁止加 `if rebuild: return decoded` 的 no-op worker；禁止新 `clean.extract.noop`。e) 若仍走 preflight，只走 `_validate_rebuild_preflight_evidence`（`:706-714`），禁止当新 inline acquisition。f) 断言：该 Task `mkb_processes.process_key` 中 acquire/decode/clean 家族计数=0；clean `content_digest`/`stored_object_uuid` 与 frozen 输入 **字节级相等**。g) 不写新 source-worker actual（消费 `NH3-10`）。h) 失败：deleted/stale 仍 409，且不产生 clean Process。 | `src/workflows/lsrag_definition.py:112-117,233-306,647-682`；`src/runtime/intake/acquisition_intents.py:25-93`；`src/runtime/intake/clean_preflight.py:28-127,706-714`；`src/runtime/intake/acquisition_ingest.py:32-48` | rebuild 再生代/publication，但不 reclean | `NH8-T02` | 零 acquire/decode/clean Process ∧ digest exact |
| `NH8-03` | Metadata no-change/changed | **高风险，有序子步：** a) **no-change**：将 fingerprint 比较前移到 `prepare`/intent_context（今日在 `_acquire_metadata_update` `:137-199`，仍 materialize acquire）。admission 冻结 `metadata_disposition=no_change` 后，用已有 `metadata_no_change` 守卫从 **start**（或非 acquire 步）直达 `succeeded`；写 `no_change` transition；不进 LS-RAG；Revision/generation 不变。b) **changed**：禁止再经 `_acquire_rebuild`（`:207-214`）进入 decode+clean。intent guard `request_intent_metadata_refresh`（已有 `:653-657`）从 start/accept 直达 `accept_snapshot.metadata_refresh` → construct（`:339-347`）。c) 继承前序 clean `stored_object_uuid` + `content_digest`（NH5-08 / T08-A 已立法）；只重做消费新 semantics 的 construct/projection/publication；**不**跑 structurize、不发现「最新」construction（HEAD `:201-204` 已 freeze receipts——保留）。d) 零 acquire/decode/clean Process。此谓词 **关闭 `NH5-T08-B`**：原 handoff 节点计数必须从 ≠0 变为 0，禁止 xfail、禁止改期待值掩盖（`FG-NH-17`）。e) 未登记 semantic key → 422 `INTAKE_SEMANTIC_KEY_UNREGISTERED`，零 Task（交 `NH8-01`）。f) 新 cleaner 只影响未来 ingest；禁止借 metadata 换 strategy（`T-O-401/407`）。 | `src/runtime/intake/acquisition_intents.py:115-233`；`src/workflows/lsrag_definition.py:290-297,339-347,653-682`；`src/services/config_snapshots.py:531-533`；`tests/e2e/test_intake_rebuild_metadata.py`；`tests/e2e/test_nh5_metadata_semantic_refresh.py`（T08-B 节点转绿） | no-change 短路；changed 切代且正文不变 | `NH8-T03` | T08-B 绿；digest 不变；facet 切代 |

### 4.3 Phase 3 — lifecycle query

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH8-04` | deactivate/reactivate/delete | **高风险，有序子步：** a) 复用 `apply_tx` 同 UoW：Item CAS + `serving_revision_uuid=NULL` + pointer `withdrawn` + vector `withdrawn`（`lifecycle_apply.py:108-134`）。**不要**重写 CAS。b) **L4**：🔱 `test_intake_reactivate.py`——删除 `import sqlite3`/`sqlite3.connect`（`:5,:146,:161,:176,:217`），改 PersistencePort；`_search`（`:102-115`）必须带 Layer-A `namespace_key` 或 `namespace_uuid`（省略 → 422 `RETRIEVE_SCHEMA_NAMESPACE_REQUIRED`，不得当空结果正例）。deactivate 后 search `results==[]`。c) reactivate：lifecycle=`active` 但 serving 仍 NULL、pointer/vector 仍 withdrawn；search 仍空（`NH-C-74`）。**不得**把旧 generation 标 active。d) 新 publish（rebuild，走 Phase 2 旁路）之后 namespaced search 才命中 admitted clean。e) **delete**：lifecycle=`deleted`；cleanup intent 一次；tombstone 不翻回；随后 rebuild/metadata 409 `intake-item-deleted` 且 **不建** 新成功 Task（prepare 拒绝）。search 持续空。f) 幂等：同一 fence 不二次 transition（unit 已有，纳入回归）。g) 负例：只 assert `lifecycle_state` 列；无 namespace 200；Task succeeded 当空集。 | `src/services/intake_lifecycle/lifecycle_apply.py:34-134,231-246`；`tests/e2e/test_intake_reactivate.py:102-229`；`tests/unit/test_intake_lifecycle.py:161-212,237-298,352-383`；🆕 `tests/e2e/test_nh8_delete_tombstone.py`；`src/services/retrieval/retrieval_request.py:265-269` | pointer/serving/vector/query 与状态一致 | `NH8-T04` / `NH8-T05` / `NH8-T06` | query 空集直到新 publish；tombstone 409 |

### 4.4 Phase 4 — index

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH8-05` | index.rebuild | **有序子步：** a) 保持 `start.to_index_rebuild` 在任何 acquire 之前（`:237-245`）；process_key 仅 `index.rebuild`（HEAD e2e `:244` 已断言形状——保留并改为 Port 读取）。b) 只复制已校验 projection；**不** INSERT `mkb_intake_revisions`；不重读 URL/handle/records；不切换 Layer A（`:23-32` 注释冻结为合同）。c) 新 `index_generation` 单调 CAS；旧代行可保留（grace）但 **search 不得命中旧 generation**（读 fence = active pointer）。d) scope 仅 active Item（`:84-89,107-110`）；deactivated 不得被 index.rebuild 复活。e) 零 source/clean/acquire/decode Process。f) 🔱 `test_index_rebuild.py`：删 sqlite3；search 补 namespace；命中以 search body 为准。g) 不得用 pointer 整数 +1 顶替 query。 | `src/runtime/intake/index_rebuild_plan.py:23-50`；`src/workflows/lsrag_definition.py:233-245,647-652`；`src/services/intake_lifecycle/targets.py:83-121`；`tests/e2e/test_index_rebuild.py:61-244` | 新 generation 可检索；Revision 计数不变 | `NH8-T07` | 新 generation ∧ 零 Revision/source/clean ∧ 旧代不命中 |

### 4.5 Phase 5 — API Item

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH8-06` | Shared lifecycle | **高风险，有序子步：** a) 取 NH7 已 publication 的 **一个** registered_api member Item（禁止本 AP 重铺 10+3；若 NH7 未绿不得用 monkeypatch 造 member）。b) 对该 Item 依次合法：rebuild / update_metadata / deactivate / reactivate / delete / index.rebuild。c) 路由必须走 **inline 骨架 + 同一** `LifecycleApplyMixin` / `IntakeTargetResolver` / publication CAS，**不得** materialize `SCATTER_CHILD` 新 child 图（child construct 无 `accepted_intake_revision` optional，不能跑 metadata_refresh——`builtin_scatter.py:416-422` vs `lsrag_definition.py:190-194`）。d) exact-clean 与 query 法与 single 相同：零 clean Process；deactivate 后 namespaced search 空。e) 禁止为 API 复制第二套 kernel。f) 非法格（对 API Item 带 source 的 rebuild 等）仍走 `NH8-01`，零 Task。 | `src/services/intake_lifecycle/lifecycle_apply.py:34-134`（SQL `:108-134`）；`src/workflows/lsrag_definition.py:190-214,233-306`；`src/workflows/builtin_scatter.py:416-441,571-586`；🆕 `tests/e2e/test_nh8_api_item_intents.py` | single/API 同法 | `NH8-T08` | API 七意图 query 法成立；无 child kernel |

### 4.6 Phase 6 — compat + lineage

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH8-07` | Old/new retirement | **高风险，有序子步：** a) 消费 NH2-T06：旧 `compiled_digest` Execution 在 kind 图 active 后序列不变。b) 新 Task 只 kind-only resolver，不解析 `http_resource.static` 等旧 selector。c) telemetry：pin 命中旧 key/digest 时机器可读计数（NH2 已要求存在；本 AP 把计数纳入 retirement review）。d) **有界 retire**：仅当 telemetry 显示 in-flight 旧 pin=0（或 owner 具名延期）才允许把旧 key 从 `_active_workflow_keys` 移除；提供 rollback（重新注入 `compatibility_definitions`）。e) 未知 digest 仍零 Process（既有 `:175-192`）。f) 禁止为退役复制 13 profile 或热切 in-flight。 | `src/runtime/workflow/runtime_core.py:88-100,591-633`；`api/app.py` compatibility_definitions 注入；`tests/unit/test_workflow_revision_compatibility.py`；`src/workflows/builtin_lsrag.py:40-44` | old 可完结；新 Task 只 kind | `NH8-T09` | old pin 完成 ∧ 新 Task kind-only |
| `NH8-08` | Restart/rebuild matrix | **有序子步：** a) `full_task` 新 generation 复制 exact workflow/policy/**sealed actual**（扩展 `task_commands.py:293-311` 对 NH3 新 actual 列；禁止清 actual）。b) rebuild/metadata：不写新 source-worker actual；clean replay 分账（本 AP Phase 2）。c) `index.rebuild` 不碰 S05/Revision（不 UPDATE actual 列、不 INSERT revision）。d) 扫描：`restart_scope` CHECK 仍两值（`001_initial.sql:201-202`）；API/models/intent 无 `upgrade` 入口=0。e) 禁止把 upgrade 混入 retry/rebuild。 | `src/runtime/task/task_commands.py:237-311`；`src/persistence/migrations/001_initial.sql:198-219`；`src/contracts/api/models.py:278-286`；🆕 `tests/unit/test_nh8_lineage_matrix.py` | 四分账可证 | `NH8-T10` | full_task exact ∧ upgrade=0 ∧ index 不碰 S05 |

---

## 5. Phase 详情

### 5.1 Phase 1 — applicability

- **Phase 目标**：合法格可跑、非法格 admission 即死、零 silent skip。
- **本 Phase 对应编号**：`NH8-01`
- **本 Phase 新增文件**：`tests/unit/test_nh8_intent_applicability.py`；可选 `tests/e2e/test_nh8_intent_admission_http.py`（L2 合同若需走 public POST）
- **本 Phase 修改文件**：`src/contracts/api/models.py:210-286`（保持 Literal=7；payload 判别不变）；`src/runtime/task/task_create.py:88-128`（prepare 必须先于 INSERT）；`src/services/config_snapshots.py:518-542`；`src/services/intake_lifecycle/targets.py`（未登记 semantic → 新 code）
- **本 Phase 删除文件**：无
- **具体功能预期**：
  1. 七意图闭集与 `_PAYLOAD_MODEL` 1:1；payload 类型不匹配 → 422 `task-schema-invalid`。
  2. 非 ingest 请求含 `source` / ingest 含 `intake_item_uuid` 而无 source → 422，零 Task。
  3. 第五 kind、第八 intent、`workflow_key` 字段 → 422，零 Task。
  4. deleted Item rebuild → 409 `intake-item-deleted`，零 Task。
  5. inactive Item `index.rebuild` → 409 `index-rebuild-item-not-active`，零 Task。
  6. 未登记 semantic key → 422 `INTAKE_SEMANTIC_KEY_UNREGISTERED`，零 Task。
  7. 合法 ingest 仍 201 且恰好一行 Task；不得为非 ingest 按四 kind 各建一遍。
- **对应测试台账项**：`NH8-T01`
- **收口标准**：非法格零 Task/Process；code 闭集可机读。
- **本 Phase 风险提醒**：把 409 并发格（stale CAS）误标成「零 Task」会误杀合法 replay。`FG-NH-15`：测试矩阵必须按合法格，不得 7×4 全绿当完成。

### 5.2 Phase 2 — exact-clean

- **Phase 目标**：rebuild/metadata 真正旁路 acquire/decode/clean；T08-B 转绿。
- **本 Phase 对应编号**：`NH8-02` / `NH8-03`
- **本 Phase 新增文件**：无生产文件硬性新增（守卫/路由在既有 `lsrag_definition.py`）；测试节点见 §8
- **本 Phase 修改文件**：`src/workflows/lsrag_definition.py:233-306,647-682`；`src/runtime/intake/acquisition_intents.py:25-233`；`src/runtime/intake/clean_preflight.py:28-127`（rebuild 不可达，而非内部 no-op）；`tests/e2e/test_intake_rebuild_metadata.py`（删 sqlite3、补 namespace、process-absence）
- **本 Phase 删除文件**：无；禁止新增 no-op cleaner 模块
- **具体功能预期**：
  1. rebuild Task 的 Process 集合不含 `intake.acquire.*`、`intake.decode.*`、`clean.*`。
  2. rebuild 后 admitted clean digest/object uuid 与 frozen 输入相等；namespaced search 正文=原 clean。
  3. metadata no-change：无新 Revision、无 generation 切代、无 clean Process、search 仍命中。
  4. metadata changed：新 `intake_revision_uuid`；clean digest 不变；S06/facet=新 S04（消费 NH5）；无 structurize Process。
  5. `NH5-T08-B` 节点（或并入本文件的同一断言）计数=0 且 PASS。
  6. `_clean` 对 rebuild/metadata **控制流不可达**（架构扫描或覆盖）；不是「跑了但返回原文」。
  7. 失败/stale：409 且不留下新 clean artifact。
- **对应测试台账项**：`NH8-T02` / `NH8-T03`
- **收口标准**：零 clean Process ∧ digest exact；T08-B 绿。
- **本 Phase 风险提醒**：`R-F11` 最危险形态是新 `clean.extract.deterministic` 对 plain text 再归一化。NOOP 投影不足以表达 skip。

### 5.3 Phase 3 — lifecycle query

- **Phase 目标**：生命周期以检索空集/冲突为产品终态，不是 DB 列。
- **本 Phase 对应编号**：`NH8-04`
- **本 Phase 新增文件**：`tests/e2e/test_nh8_delete_tombstone.py`
- **本 Phase 修改文件**：`tests/e2e/test_intake_reactivate.py`（Port + namespace）；lifecycle 生产代码仅当 L4 暴露缺口时改（HEAD CAS 正例保留）
- **具体功能预期**：
  1. deactivate 后：Item `deactivated`、serving NULL、pointer/vector withdrawn、namespaced search `results==[]`。
  2. reactivate 后：Item `active`、serving 仍 NULL、pointer/vector 仍 withdrawn、search 仍 `[]`。
  3. rebuild（exact-clean）后 search 命中原 clean。
  4. delete 后 rebuild 409 `intake-item-deleted`；search 空；tombstone 再 reactivate 409。
  5. 省略 namespace 的 search 422，不得写成「空结果成功」。
  6. 同 fence 幂等；stale `expected_item_revision` 409。
- **对应测试台账项**：`NH8-T04` / `NH8-T05` / `NH8-T06`
- **收口标准**：query 与 pointer/serving/vector 一致。
- **本 Phase 风险提醒**：HEAD e2e 无 namespace 却 `assert 200` 是假绿（RA08）；Lucene undelete 反例——恢复必须重发布。

### 5.4 Phase 4 — index

- **Phase 目标**：index.rebuild 是 generation 切代，不是 ingest/reactivate。
- **本 Phase 对应编号**：`NH8-05`
- **本 Phase 新增 / 修改 / 删除文件**：🔱 `tests/e2e/test_index_rebuild.py`；生产 `index_rebuild_plan.py:23-50` 行为保持、测试升到 query 法
- **具体功能预期**：
  1. Revision 计数不变；`serving_revision_uuid` 不变。
  2. `active_index_generation` 单调 +1；process 仅 `index.rebuild`。
  3. namespaced search 命中同一正文。
  4. 过滤/断言旧 `index_generation` 不出现在 search hits。
  5. inactive 目标 409，零切代。
- **对应测试台账项**：`NH8-T07`
- **收口标准**：新 generation ∧ 零 Revision/source/clean ∧ 旧代不命中。
- **本 Phase 风险提醒**：HEAD 断言旧代 vector 行仍存在（`:231`）——行保留 ≠ 可检索；必须以 search fence 为准。

### 5.5 Phase 5 — API Item

- **Phase 目标**：scatter 成员与 single Item 生命周期同法。
- **本 Phase 对应编号**：`NH8-06`
- **本 Phase 新增文件**：`tests/e2e/test_nh8_api_item_intents.py`
- **本 Phase 修改文件**：仅当发现 child 图被误选时改 resolver/guards；默认不改 scatter child 定义
- **具体功能预期**：
  1. 事后 rebuild/metadata/lifecycle/index.rebuild 的 Execution `execution_role` 不是 `SCATTER_CHILD`。
  2. 与 single 相同的 process-absence / query 谓词。
  3. 不创建第二套 publication schema。
  4. 非法格仍零 Task。
  5. 不把 parent Task `publication_ready` 当 member 可检索（`FG-NH-04`）。
- **对应测试台账项**：`NH8-T08`
- **收口标准**：API 七意图 mega PASS；无 child kernel。
- **本 Phase 风险提醒**：非 ingest 选 inline 骨架会把 mapped clean 再喂 deterministic——Phase 2 旁路必须对 API Item 同样生效。

### 5.6 Phase 6 — compat + lineage

- **Phase 目标**：旧承诺可跑完；新承诺不热切；upgrade 不存在。
- **本 Phase 对应编号**：`NH8-07` / `NH8-08`
- **本 Phase 新增文件**：`tests/unit/test_nh8_lineage_matrix.py`
- **本 Phase 修改文件**：`tests/unit/test_workflow_revision_compatibility.py`；`task_commands.py:237-311`（复制 new actual 列，消费 NH3）
- **具体功能预期**：
  1. 旧 pin 序列与 `HISTORICAL_SINGLE_INTAKE_LSRAG_WORKFLOW_V1` 一致。
  2. 新 ingest Task workflow identity ∈ kind 闭集。
  3. telemetry 在旧 pin 命中时递增；retire 仅在 in-flight=0 或具名延期后；rollback 可重新注入 compat 定义。
  4. `full_task` 新 generation 的 `actual_binding_digest` 等于旧 sealed。
  5. rebuild 不 UPDATE actual；index 不碰 S05/Revision。
  6. `rg` 对 restart/intent 合同 `upgrade` 入口命中=0。
- **对应测试台账项**：`NH8-T09` / `NH8-T10`
- **收口标准**：old 完结；kind-only；upgrade=0。
- **本 Phase 风险提醒**：`R-F04` 过早删 key；`R-F12` 以 new generation 清 actual。

---

## 6. 依赖的冻结设计决策（只读引用）

> 只引 Q 编号与 T-O-ID，不复制业主长文、不改口、不开新 Q/A。

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Q25 / `T-O-405` / `G-NH-17` CLOSED | `pre-charter-qna.md` §Q25 | Phase 1 非法格 admission；code 闭集；禁 7×4 | 不得用 skip/no-op；回 QNA 而非本 AP 改口 |
| Q27 / `T-O-407` / `G-NH-19` CLOSED | 同上 §Q27 | Phase 2 guard 旁路；禁 no-op cleaner | 不得把 byte-equal worker 当 skip |
| Q21 / `T-O-401` / `G-NH-12` CLOSED | 同上 §Q21 | Phase 6 full_task exact；upgrade OOS；rebuild 不 bind 源工人 | 禁止新 generation 清 actual |
| Q14 / `T-O-394` / `G-NH-05` CLOSED | 同上 §Q14 | Phase 2 metadata 切代消费 NH5 权威；不自动 unknown | 语义缺口回 NH5，不在本 AP 填 unknown |
| Q18 / `T-O-398` / `G-NH-09` CLOSED | 同上 §Q18 | Phase 6 有界 Workflow；old pin | 不得扩通用引擎 |
| Q26 / `T-O-406` / `G-NH-18` CLOSED | 同上 §Q26 | 四层不可互换；waiver 只延期 | 不得用 L1 顶 L4 |
| `O-NH-03` | final §4.2 | existing upgrade 不在 NH v1 | 未来新 owner-gate |
| `NH-C-74` | RA08 §5.2 | reactivate 不 restore serving | 不得标可检索 |
| `NH3-10` | `AP-NH3` | 法律已写；本 AP 落地旁路与矩阵 | 不得在本 AP 改 T-O 含义 |
| `NH5-T08-B` | `AP-NH5` §8 | process-absence 红灯交接；本 AP 转绿 | 禁止 xfail 掩盖 |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表（本计划工作要落在哪些既有代码 / 新建点上）

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| `NH8-A01` | `src/contracts/api/models.py:278-286` | 七意图 Literal 闭集 + `_PAYLOAD_MODEL` `:262-269` | `NH8-01` 扩 applicability / code | `✅ 复用` | 不做 28 格；payload 判别 `:328-360` |
| `NH8-A02` | `src/runtime/intake/acquisition_intents.py:25-93` | rebuild 读 frozen accepted clean；禁伪造外源 S05 | `NH8-02` 复用输入法，迁出 acquire Process | `✅ 复用` | 现图仍 reclean；`:207-214` metadata 误调此函数，须拆 |
| `NH8-A03` | `src/runtime/intake/clean_preflight.py:28-127` | `_clean` 无 rebuild 短路，`dispatch_clean` | `NH8-02/03` guard 使其不可达 | `♻️ 重 substrate` | ⛔ 反例；禁 no-op worker |
| `NH8-A04` | `src/services/intake_lifecycle/lifecycle_apply.py:34-134` | withdraw/reactivate 同 UoW；reactivate 不 restore serving | `NH8-04` 复用 CAS，加 L4 query | `✅ 复用` | `:36-38` 即 `NH-C-74` |
| `NH8-A05` | `src/runtime/intake/index_rebuild_plan.py:23-50` | 新 generation；不造 Revision；不重读源 | `NH8-05` 复用，升 query 法 | `✅ 复用` | 台账摘录 `:23-32`；独立核验至 `:50` `next_state` |
| `NH8-A06` | `src/runtime/task/task_commands.py:237-311` | `full_task` 复制 exact workflow/config/`s05` | `NH8-08` 对 new actual 同样 exact；upgrade OOS | `♻️ 重 substrate` | `T-R-NH-23` 机制正例、值待 NH3 列 |
| — | `src/workflows/lsrag_definition.py:237-245,299-306,647-682` | index 已旁路；rebuild 仍 `acquire.to_decode` | `NH8-02` 画边模板 / 反例边 | `♻️ 重 substrate` | 正例：index guard；反例：`:299-306` |
| — | `src/services/config_snapshots.py:135` + `src/runtime/task/task_create.py:88,106` | `prepare()` 在 INSERT 前（`:88` 调用；`:106` INSERT；dataclass 在 `:86` 不是执行点） | `NH8-01` admission 点 | `✅ 复用` | 已建好，勿把 resolver 后移 |
| — | `src/services/retrieval/retrieval_request.py:265-270` | 无 namespace → 422 | T04–T08 L4 负例正用 | `✅ 复用` | 服务端正例；假绿在旧 e2e |
| — | 🆕 `tests/unit/test_nh8_intent_applicability.py` | 合法/非法矩阵 | `NH8-T01` | `🆕 净新` | |
| — | 🆕 `tests/e2e/test_nh8_delete_tombstone.py` | delete + rebuild 409 | `NH8-T06` | `🆕 净新` | |
| — | 🆕 `tests/e2e/test_nh8_api_item_intents.py` | API Item 七意图 | `NH8-T08` | `🆕 净新` | |
| — | 🆕 `tests/unit/test_nh8_lineage_matrix.py` | restart 分账 | `NH8-T10` | `🆕 净新` | 消费 NH3-T08 法律 |

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | 新增 no-op/deterministic cleaner 冒充 skip（返回原文再 assert byte-equal） | `T-O-407`；`R-F11`；仍留下 clean Process/actual |
| ⛔2 | 图仍跑 `clean.extract.deterministic`（`lsrag_definition.py:112-117,299-306` + `clean_preflight.py:28-127`） | `T-R-NH-17`；`NH-RA08-B04`；HEAD 半截「输入 clean、过程仍 clean」 |
| ⛔3 | metadata e2e `sqlite3.connect` + 无 namespace 却断言 200（`test_intake_rebuild_metadata.py:6,138,229-241`） | `FG-NH-05/12`；RA08：调用≠命中 |
| ⛔4 | reactivate 恢复旧 `serving_revision` / 把旧 generation 标 active | `NH-C-74`；Lucene 无 undelete |
| ⛔5 | 7 intents × 4 kind 造假矩阵 / 28 格施工 | `T-O-405`；`FG-NH-15`；`T-R-NH-21` |
| ⛔6 | existing upgrade 混入 `full_task` / rebuild / 第八 intent | `O-NH-03`；`T-O-401`；`R-F12/R-F16` |
| ⛔7 | Task `succeeded` / `publication_ready` / 仅 DB `lifecycle_state` 当可检索或已撤 | `T-O-376`；`NH-C-71`；`FG-NH-03/04` |
| ⛔8 | monkeypatch fetcher、503、空 clean 当 L3 | `T-O-378`；`FG-NH-01/02/06` |
| ⛔9 | 复制 13 profile / caller `workflow_key` / `action_branch` | `T-O-377/379/398`；`FG-NH-09` |
| ⛔10 | ES refresh/NRT 可见性；R2 key / COMPLETED payload 当 proof | RA08 WEB-03 / LEGACY-01；不引入引擎 |
| ⛔11 | T08-B xfail / 改期待值让 metadata 仍跑 clean 却全绿 | `FG-NH-17`；NH5 明文禁止 |
| ⛔12 | index.rebuild 当 ingest/reactivate；或按四 kind 各做一遍 | `NH-C-78`；`T-O-405` |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：[`assessment-analysis-08-publication-and-intake-lifecycle.md`](../../eval/new-harvest/reference-anchor/assessment-analysis-08-publication-and-intake-lifecycle.md) —— §7.1 是与本 AP 相关子集；完整借鉴台账见 RA08 §3（`RA-08-HEAD-05/10/13`；`NH-RA08-B04/B05/B07/B08`）。RA02 只消费 restart 三窗，禁止与 `G-NH-19` 共用 ID。
- **安全 / 信任边界类工作项的威胁模型锚**（不得留空）：

| 工作项 | 威胁 | 缓解 | 测试 |
|--------|------|------|------|
| `NH8-01` | 非法格建 Task 后 silent skip；跨 team 探测 Item | admission 在 INSERT 前；`intake-item-not-found` 不泄漏他队 | `NH8-T01` 攻击：第五 kind、`workflow_key` extra、他队 uuid、source-on-rebuild |
| `NH8-02/03` | reclean 换策略/digest；no-op 伪造 skip | guard 不 materialize clean Process | `NH8-T02/T03` process-absence + digest |
| `NH8-04` | 已停 Item 仍被检索；reactivate 复活未审向量 | 同 UoW withdraw + S10 dual-fence；不 restore serving | `NH8-T04/T05` namespaced empty |
| `NH8-05` | 旧 generation 漏出 | pointer CAS + search fence | `NH8-T07` 旧代不命中 |
| `NH8-07` | 退役绞杀 in-flight | digest pin + 有界 retire | `NH8-T09` |
| `NH8-08` | upgrade 偷换工人 | 入口=0 | `NH8-T10` scan |

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| `NH8-T01` | 七意图合法/非法 code；非法格零 Task/Process | 契约 | L1/L2 | 🆕 `tests/unit/test_nh8_intent_applicability.py` + public POST 422/409 | `NH8-01` → 非法格 admission 拒绝且零 Task/Process | `commit SHA + 422/409 PASS + Q25 + UTC` |
| `NH8-T02` | rebuild 零 acquire/decode/clean Process 且 clean digest exact；namespaced 命中原正文 | 集成/mega | L2/L4 | 🔱 **唯一 PASS node** `tests/e2e/test_intake_rebuild_metadata.py::test_rebuild_replays_frozen_clean_without_acquire_decode_clean`（删 sqlite3、补 namespace）。未清前 ⛔ | `NH8-02` → exact-clean | `commit SHA + process/query PASS + Q27 + UTC` |
| `NH8-T03` | metadata no-change 短路；changed 新 Revision + inherit clean + facet 切代；零 clean Process（**关闭 NH5-T08-B**） | 集成/mega | L2/L4 | 🔱 **具名** metadata process-absence node + T08-B 转绿。HEAD 整文件未清 sqlite3/namespace 前 ⛔ | `NH8-03` → exact-clean / T08-B 绿 | `commit SHA + revision/digest/facet PASS + Q27 + UTC` |
| `NH8-T04` | deactivate → namespaced search 空 | live | L3/L4 | 🔱 `tests/e2e/test_intake_reactivate.py` deactivate 段。未删 sqlite3、search 未带 namespace 前 **⛔ 不得列入跑法** | `NH8-04` → query empty | `commit SHA + withdraw/query PASS + Q25 + UTC` |
| `NH8-T05` | reactivate 后 search 仍空直到新 publish | live | L3/L4 | 🔱 **独立 node** `tests/e2e/test_intake_reactivate.py::test_reactivate_search_empty_until_rebuild`。未清 sqlite3/namespace 前 ⛔ | `NH8-04` → 不 restore | `commit SHA + pointer/query PASS + Q25 + UTC` |
| `NH8-T06` | delete tombstone；随后 rebuild 409；search 空 | live | L3/L4 | 🆕 `tests/e2e/test_nh8_delete_tombstone.py` | `NH8-04` → tombstone | `commit SHA + 409/query PASS + Q25 + UTC` |
| `NH8-T07` | index.rebuild 新 generation；零 Revision；旧代不命中 | live/compat | L3/L4 | 🔱 `tests/e2e/test_index_rebuild.py`。未删 sqlite3、search 未带 namespace 前 **⛔ 不得列入跑法** | `NH8-05` → 新 generation / 旧代不命中 | `commit SHA + generation/query PASS + Q25 + UTC` |
| `NH8-T08` | API Item 七意图同法；无 child kernel | mega | L3/L4 | 🆕 `tests/e2e/test_nh8_api_item_intents.py` | `NH8-06` → single/API 同法 | `commit SHA + API lifecycle PASS + Q25 + UTC` |
| `NH8-T09` | old pin 完结；新 Task kind-only；有界 retire/rollback | compat | L2/C | 🔱 `tests/unit/test_workflow_revision_compatibility.py` | `NH8-07` → old/new 共存并可退役 | `commit SHA + old/new sequence PASS + Q18 + UTC` |
| `NH8-T10` | full_task exact；rebuild replay；index 不碰 S05；upgrade 入口=0 | replay | L2/C | 🆕 `tests/unit/test_nh8_lineage_matrix.py` | `NH8-08` → restart 分账 | `commit SHA + lineage PASS + Q21/Q27 + UTC` |

本 AP 台账 C 最低层：T01 L1/L2；T02/T03 L2/L4；T04–T08 含 L3/L4；T09/T10 L2。不可降层（`T-O-406`）。Capstone **H** ← `NH8-T02..T08`。

#### `NH8-T01`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/unit/test_nh8_intent_applicability.py::test_legal_ingest_creates_exactly_one_task`；`::test_illegal_cells_fail_before_task_insert`；`::test_http_422_vs_409_code_closed_set`。L2 伴生可走 `create_app()` POST `/v1/teams/{team}/tasks`，但 **不得** 把纯 pydantic 单测顶替「零行」审计。 |
| 用途 | `NH8-01`；`T-O-405`；`FG-NH-15`；威胁：第五 kind / `workflow_key` / source-on-rebuild |
| 前置 | PersistencePort；真实 prepare()；禁止 sqlite3。合法格夹具用 inline ingest（不宣称 10+3 live）。 |
| 步骤 | a) 合法 ingest → 201，Port 计 Task=1。b) 矩阵非法格（第八 intent、第五 kind、`workflow_key` extra、rebuild+source、ingest+lifecycle payload、deleted rebuild、inactive index.rebuild、未登记 semantic key）。c) 每格记录 HTTP status+code。d) Port `COUNT` 该 `task_uuid` 的 `mkb_tasks` 与 `mkb_processes`。e) 确认非 ingest 未按四 kind 循环建 Task。 |
| 断言细节 | 422 格 code ∈ 闭集且 Task=0 Process=0。409 状态格（deleted/inactive）同样 Task=0。合法格恰好 1 Task。禁止 200 skip。 |
| 负例 | 7×4 全跑当完成；只 assert HTTP 不查表；把 stale CAS 409 写成零 Task 义务 |
| 跑法 | `uv run pytest tests/unit/test_nh8_intent_applicability.py -q` |
| 层与来源 | L1/L2；`🆕` |

#### `NH8-T02`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🔱 **唯一 PASS node** `tests/e2e/test_intake_rebuild_metadata.py::test_rebuild_replays_frozen_clean_without_acquire_decode_clean`（禁止「或拆出」可选）。该 node 必须 Port 计 rebuild task 的 acquire/decode/clean `process_key` 家族 = 0。**仅当**已删除 `import sqlite3`/`sqlite3.connect`、search 必带 namespace、命中以 search body 为准。HEAD 现函数 `:148-178` 只查 revision/generation，**不得**单独关 T02。L2 伴生：Port 列 `mkb_processes.process_key`。 |
| 用途 | `NH8-02`；`T-O-407`；`R-F11`；rebuild 同构 process-absence（metadata T08-B 由 **T03** 关闭） |
| 前置 | default-root `create_app()`；先合法 ingest 至 publication；Port 读 predecessor clean digest/object；Layer-A namespace。禁止 monkeypatch fetcher。禁止 Task succeeded 当命中。 |
| 步骤 | a) ingest 黄金正文。b) `intake.rebuild`。c) Port：acquire/decode/clean 家族 process_key 计数=0。d) clean `content_digest` 与 `stored_object_uuid` 等于 frozen 输入。e) namespaced search 命中 **原** admitted clean。f) 省略 namespace → 422。 |
| 断言细节 | HTTP 200 + `disposition=ok`；payload=原 clean；无 `clean.extract.deterministic` Process；无外源 acquire fact。 |
| 负例 | sqlite3 直读；无 namespace 200；跑 no-op cleaner 后 byte-equal；以 generation +1 顶替 digest；用现函数 rebuild 段绿掉 T02 而不计 process |
| 跑法 | `uv run pytest tests/e2e/test_intake_rebuild_metadata.py::test_rebuild_replays_frozen_clean_without_acquire_decode_clean -q`（文件须已无 sqlite3 且每 search 带 namespace；未清前 ⛔，本命令不得作为 PASS） |
| 层与来源 | L2/L4；`🔱` 唯一 node；HEAD 未清 sqlite3 前 ⛔ 不得宣称 PASS |

#### `NH8-T03`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🔱 **唯一 PASS node** `tests/e2e/test_intake_rebuild_metadata.py::test_metadata_no_change_changed_zero_acquire_decode_clean`（禁止用 HEAD 现函数 metadata 段单独关 T03）。以及 `tests/e2e/test_nh5_metadata_semantic_refresh.py::test_metadata_refresh_process_absence_handoff_to_nh8` **必须转绿**（计数=0）。**仅当**已删除 `import sqlite3`/`sqlite3.connect`、每 search 带 Layer-A namespace。T08-A digest/facet 仍由 NH5 拥有，本节点只加 process-absence=0 与「不 reclean」。 |
| 用途 | `NH8-03`；**关闭 NH5-T08-B**；`T-O-394/407`；`FG-NH-17` |
| 前置 | NH5-08 语义切代已能绿 T08-A；本 AP 不得改期待值掩盖仍跑 clean。search 带 namespace。文件已无 sqlite3。 |
| 步骤 | a) ingest。b) `update_metadata` 相同指纹 → no_change：Revision 计数不变、无 clean Process、search 仍命中。c) 改 realm（或等价参与指纹键）→ 新 Revision；clean digest/object 不变；facet/S06=新 S04。d) Port 计 acquire/decode/clean=0。e) T08-B 原 handoff 节点同断言 PASS。 |
| 断言细节 | no-change transition=`no_change`；changed：`lsrag.structurize` 不在 process 集；clean digest 字节相等。省略 namespace → 422。 |
| 负例 | 保留 T08-B 红灯当 NH8 DoD；xfail；经 `_acquire_rebuild` 再 `dispatch_clean`；HEAD 整文件 sqlite3-on-Turso / 无 namespace 200 当 PASS |
| 跑法 | **仅当** `test_intake_rebuild_metadata.py` 已无 `import sqlite3`/`sqlite3.connect` 且每 search 带 namespace：`uv run pytest tests/e2e/test_intake_rebuild_metadata.py::test_metadata_no_change_changed_zero_acquire_decode_clean tests/e2e/test_nh5_metadata_semantic_refresh.py::test_metadata_refresh_process_absence_handoff_to_nh8 -q`。否则 ⛔，整份 HEAD 文件 **不得**作为 PASS（与 T02 同闸） |
| 层与来源 | L2/L4；`🔱` 具名 node + 关闭 handoff；HEAD 未清 sqlite3 前 ⛔ |

#### `NH8-T04`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🔱 `tests/e2e/test_intake_reactivate.py::test_reactivate_restores_active_lifecycle_but_not_stale_serving_state` **deactivate 段**（`:153-166` 形状）。删 sqlite3；`_search` 补 namespace。**未删除 `import sqlite3`/`sqlite3.connect`、search body 未带 Layer-A namespace 之前，本 node 不得列入跑法。** |
| 用途 | `NH8-04`；`NH-C-73`；`FG-NH-03/05/12` |
| 前置 | default-root；ingest 至可检索；Port 读 namespace。文件已无 sqlite3；每 search 带 namespace（省略 → 422，不得当空集正例）。 |
| 步骤 | a) ingest + namespaced 命中。b) `intake.deactivate`。c) Port：lifecycle=deactivated、serving NULL、pointer/vector withdrawn。d) namespaced search `results==[]`。 |
| 断言细节 | Task 可 succeeded **且** search 空；二者同时成立才 PASS。省略 namespace 422。 |
| 负例 | 只查 `lifecycle_state`；无 namespace 当空集；sqlite3-on-Turso |
| 跑法 | **仅当**文件已无 `import sqlite3` 且 `_search` 带 namespace：`uv run pytest tests/e2e/test_intake_reactivate.py::test_reactivate_restores_active_lifecycle_but_not_stale_serving_state -q`。否则本 Test-ID 无 PASS 命令（§8.2 ⛔） |
| 层与来源 | L3/L4；`🔱`；未清前 ⛔ |

#### `NH8-T05`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🔱 **独立 PASS node** `tests/e2e/test_intake_reactivate.py::test_reactivate_search_empty_until_rebuild`（可从原函数 `:168-215` 拆出；禁止与 T04 共享同一 pytest id 作为唯一四元组）。未清 sqlite3/namespace 前不得列入跑法。 |
| 用途 | `NH8-04`；`NH-C-74`：reactivate **不得**恢复旧 serving |
| 前置 | T04 已 deactivate；同一 Item。文件已无 sqlite3；每 search 带 namespace。 |
| 步骤 | a) `intake.reactivate`。b) Port：lifecycle=active、serving 仍 NULL、pointer/vector 仍 withdrawn、transition after_serving=NULL。c) namespaced search 仍 `[]`。d) `intake.rebuild`（exact-clean）后 search 命中原正文。 |
| 断言细节 | reactivate Task succeeded ≠ 可检索。rebuild 后 hit。 |
| 负例 | reactivate 后 pointer=`active` 或 serving 被填回旧 uuid；无 namespace 200 |
| 跑法 | **仅当**文件已无 `import sqlite3` 且 search 带 namespace：`uv run pytest tests/e2e/test_intake_reactivate.py::test_reactivate_search_empty_until_rebuild -q`。否则 ⛔ |
| 层与来源 | L3/L4；`🔱` 独立 node；未清前 ⛔ |

#### `NH8-T06`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_nh8_delete_tombstone.py::test_delete_tombstone_rejects_rebuild_and_search_empty`；`::test_deleted_item_reactivate_409`。unit `tests/unit/test_intake_lifecycle.py::test_delete_creates_one_cleanup_intent_and_never_restores_tombstone` `♻️ 沿用` 不足 L4。 |
| 用途 | `NH8-04`；`NH-RA08-B08`；Capstone H delete |
| 前置 | default-root；ingest+publish；namespace；Port。 |
| 步骤 | a) delete。b) namespaced search 空。c) POST rebuild（新 task_uuid）→ 409 `intake-item-deleted`。d) Port：该新 uuid Task 计数=0。e) reactivate 同样 409。f) cleanup intent 恰好一次。 |
| 断言细节 | tombstone 不翻回；零成功 rebuild Task。 |
| 负例 | 只测 cleanup 行存在；delete 后再 index.rebuild 复活 |
| 跑法 | `uv run pytest tests/e2e/test_nh8_delete_tombstone.py -q` |
| 层与来源 | L3/L4；`🆕` |

#### `NH8-T07`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🔱 `tests/e2e/test_index_rebuild.py::test_scoped_index_rebuild_promotes_generation_without_new_intake_revision`。删 sqlite3（`:5,:120,:193`）；search `:177-191` 补 namespace；另加「旧 generation 不在 hits」。stale fence 节点 `::test_index_rebuild_stale_fence_fails_without_cutover_and_old_generation_remains_retrievable` `♻️ 沿用` 失败法。**未删除 sqlite3、search 未带 namespace 之前不得列入跑法。** |
| 用途 | `NH8-05`；`NH-C-78/79`；禁 NRT 假绿 |
| 前置 | ingest+publish；Port 读 generation/revision/process。文件已无 sqlite3；每 search 带 namespace。 |
| 步骤 | a) 记 generation=1 命中。b) `index.rebuild`。c) Revision 计数=1；process_key 仅 `index.rebuild`。d) namespaced search 仍命中同一正文。e) hits 的 generation/proof 指向新代；旧代不出现。f) inactive 目标 409。 |
| 断言细节 | 零 acquire/decode/clean/source Process；不 INSERT revision。 |
| 负例 | 只比 pointer 整数；无 namespace 200；用 index.rebuild 复活 deactivated；sqlite3 直读 |
| 跑法 | **仅当**文件已无 `import sqlite3` 且 search 带 namespace：`uv run pytest tests/e2e/test_index_rebuild.py::test_scoped_index_rebuild_promotes_generation_without_new_intake_revision -q`。否则 ⛔ |
| 层与来源 | L3/L4；`🔱`；未清前 ⛔ |

#### `NH8-T08`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_nh8_api_item_intents.py::test_registered_api_item_seven_intents_share_single_services` |
| 用途 | `NH8-06`；`NH-RA08-B07`；mega |
| 前置 | NH7 至少一 member 已 publication（真实 records，禁 monkeypatch）。本 AP 不重跑 10+3。default-root。namespace。 |
| 步骤 | a) 解析 member `intake_item_uuid`。b) rebuild：零 clean Process，search 正文不变。c) metadata 切代或 no-change 按指纹。d) deactivate → search 空。e) reactivate → 仍空。f) index.rebuild → 新 generation，仍空直到（若仍 deactivated 则 409；须先 rebuild/publish 路径与 single 一致）。g) delete → rebuild 409。h) Execution role ≠ `SCATTER_CHILD`。 |
| 断言细节 | 与 T02–T07 同谓词；无 child kernel。 |
| 负例 | parent `publication_ready` 当 member 命中；为 API 复制第二 publication 表 |
| 跑法 | `uv run pytest tests/e2e/test_nh8_api_item_intents.py -q` |
| 层与来源 | L3/L4；`🆕`；不可降层 |

#### `NH8-T09`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🔱 `tests/unit/test_workflow_revision_compatibility.py::test_v2_runtime_materializes_and_completes_unstarted_v1_execution`（`:106-168`）；`::test_unknown_historical_compiled_plan_fails_before_process_materialization`（`:175-192`）。🆕 同文件：`test_old_pin_completes_after_nh8_guards`；`test_new_task_kind_only_not_old_selector`；`test_bounded_retire_rolls_back_when_in_flight`。 |
| 用途 | `NH8-07`；`T-O-398`；`M-NH-04`；`R-F04` |
| 前置 | NH2 kind 图 + compat 定义仍注入。真实 UoW。 |
| 步骤 | a) 旧 pin 在新守卫图下跑完，process 序列锁死。b) 新 Task kind-only。c) telemetry 命中旧 pin 可观测。d) 模拟 in-flight>0 时 retire → 必须失败或 no-op，rollback 后 pin 仍可跑。e) in-flight=0 后有界移除旧 key，未知 digest 零 Process。 |
| 断言细节 | `compiled_digest` 不变；新 identity ∈ kind 闭集。 |
| 负例 | 删除旧 key 导致 in-flight 409 当成功退役 |
| 跑法 | `uv run pytest tests/unit/test_workflow_revision_compatibility.py -q` |
| 层与来源 | L2/C；`🔱` + `🆕` nodes |

#### `NH8-T10`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/unit/test_nh8_lineage_matrix.py::test_full_task_copies_exact_sealed_actual`；`::test_rebuild_does_not_write_source_actual_or_clean_process`；`::test_index_rebuild_does_not_touch_s05_or_revision`；`::test_upgrade_entrance_scan_is_zero`。可 🔱 NH3-T08 节点作回归，但本文件必须独立覆盖四分账。 |
| 用途 | `NH8-08`；`T-O-401/407`；`R-F12` |
| 前置 | NH3 actual 列已存在；sealed Execution fixture。 |
| 步骤 | a) `full_task` retry。b) rebuild Task。c) index.rebuild Task。d) AST/`rg` 扫描 API Literal、DDL CHECK、`restart_scope` 无 `upgrade`。 |
| 断言细节 | 新 generation actual digest 相等；rebuild 无新 actual UPDATE、无 clean Process；index 无 revision INSERT、S05 列不变；upgrade 命中=0。 |
| 负例 | 新 generation NULL actual；rebuild 当 upgrade；第八 intent |
| 跑法 | `uv run pytest tests/unit/test_nh8_lineage_matrix.py -q` |
| 层与来源 | L2/C；`🆕` |

### 8.2 复用台账（沿用 / fork 的既有用例明细）

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/e2e/test_intake_rebuild_metadata.py` | `🔱 fork` T02/T03 | 删 sqlite3；search 补 namespace；加 process-absence=0；命中以 search body 为准 | HEAD：`import sqlite3` `:6`、直读 `:138+`、search 无 namespace `:229-241` 却 200 → 相对服务端必 422；**未改前 ⛔ 不得 🔱 宣称绿** |
| `tests/e2e/test_nh5_metadata_semantic_refresh.py::test_metadata_refresh_process_absence_handoff_to_nh8` | `🔱` 转绿 | 期待值保持计数=0（HEAD 红；NH8 后必须绿）。禁止 xfail | NH5 handoff 红灯 |
| `tests/e2e/test_intake_reactivate.py` | `🔱 fork` T04/T05。**未删 sqlite3、`_search` 未带 namespace 前 ⛔ 不得宣称绿、不得列入 T04/T05 跑法** | 删 sqlite3；`_search` 加 namespace；T05 拆独立 `::test_reactivate_search_empty_until_rebuild` | HEAD 无 namespace 却 200、有 sqlite3（`:5,:102-115,:146+`） |
| `tests/e2e/test_index_rebuild.py` | `🔱 fork` T07。**未删 sqlite3、search 未带 namespace 前 ⛔ 不得宣称绿、不得列入跑法** | 删 sqlite3；namespace；旧代不命中 | HEAD search 无 namespace 却 200；process=`index.rebuild` 形状可留 |
| `tests/unit/test_intake_lifecycle.py` | `♻️ 沿用` | 0；CAS/幂等/tombstone unit 回归，**不够 L4** | 已存在 PASS |
| `tests/unit/test_workflow_revision_compatibility.py` | `🔱 fork` T09 | + retire/rollback + kind-only | NH2-T06 起跑线 |
| `tests/unit/test_task_api_contract.py` | `♻️ 沿用` `task-schema-invalid` 形状 | 0；T01 引用 code | 已存在 |
| `tests/unit/test_task_projections.py` generation 节点 | `♻️ 沿用` NH3-T08 形状 | 本 AP T10 另建矩阵，不删 NH3 节点 | 依赖 NH3 |
| `tests/e2e/test_single_intake_pipeline.py:121-130` | **不沿用为 L4 正例** | 无 namespace | RA08 反例 |

### 8.3 分层与跑法（各类型在哪跑、何时跑）

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `uv run pytest tests/unit/test_nh8_intent_applicability.py tests/unit/test_nh8_lineage_matrix.py tests/unit/test_workflow_revision_compatibility.py tests/unit/test_intake_lifecycle.py -q` | L1/L2 | 每 PR |
| spike/集成 | T02/T03 process-absence + digest | L2 | Phase 2 收口 |
| default-root | T04–T08 `create_app()` | L3 | Phase 3–5 收口 |
| mega | T02/T03/T08 namespaced query | L4 | **本 AP 收口** |
| soak / crash | 无本 AP 专属 soak | — | 交 NH9；不假装覆盖 W-NH-PUB kill |

测试分层遵守 `T-O-406`：fault/race/security 是标签不是替代层。

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖 10 strategy + 3 operation 全矩阵 live-to-vector（理由：`S-NH-F7`）→ `AP-NH7`；本 AP T08 只用一 member。
- 不覆盖 crash/race 全窗注入（理由：`S-NH-F9`；本 AP 只保证功能 query 法）→ `AP-NH9` `W-NH-PUB/OUTBOX/...`。
- 不覆盖 existing-object new-cleaner（理由：`O-NH-03`）→ 未来 owner-gate。
- 不覆盖 raw GET / upload GC 交错（理由：`S-NH-F4`）→ `AP-NH4`/`AP-NH9`。
- 不覆盖 browser/OCR 真实供给（理由：`S-NH-F6`）→ `AP-NH6`。
- **不在本 AP 假装覆盖** Capstone I/J 与 closed-set manifest 全量回放。
- Capstone **H** 由 `NH8-T02..T08` 覆盖，不交给 NH9 补功能。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 必带四元组：`commit SHA + pytest node PASS + Truth/Q + UTC`。计数 ≠ 价值。
- 本 AP 适用 FG（必须在对应测试点名）：
  - `FG-NH-03/04`：T02–T08 禁止 Task succeeded / `publication_ready` 顶替 hit/empty
  - `FG-NH-05`：所有 search 无 namespace 不得 200
  - `FG-NH-06`：种植路径 admitted clean 非空
  - `FG-NH-12`：禁止 sqlite3 直读 Turso（T02–T07 🔱 文件必须清掉）
  - `FG-NH-13`：T04–T08 不得降成 unit
  - `FG-NH-15`：T01 按合法格，禁止 7×4 造假
  - `FG-NH-17`：T08-B 禁止改期待值/xfail
  - `FG-NH-01/02`：T08 禁 monkeypatch/503 当 member 成功
- `degraded` 必带机器可读 `reason`。pre-existing 失败必带 git 证据。
- 安全项含攻击向量：见 §7.3（`workflow_key`、第五 kind、跨 team uuid、reclean、旧代漏出、upgrade 入口）。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| DAG：NH7 未收口 | 无真实 publication Item 则 T04–T08 不能诚实 L3 | `high` | 本 AP 不得开工替代；禁 503/monkeypatch 顶 L3 |
| `NH5-T08-B` 仍红且被 xfail | 假绿 exact-clean | `high` | T03 硬闸；`FG-NH-17` |
| `R-F11` rebuild 偷 reclean | no-op/deterministic worker | `high` | process-absence + digest；架构不可达 `_clean` |
| `R-F12` full_task 清 actual | 以 new generation 为由 | `high` | T10 字节级相等 |
| `R-F04` old pin 绞杀 | 退役过早 | `high` | telemetry + 有界 retire + rollback |
| `R-F14` Task/flag 顶替 query | 沿用旧 e2e 无 namespace | `high` | T04–T08 强制 namespace + body |
| `R-F16` scope 滑向 upgrade | 临时需求第八 intent | `high` | OOS 硬围栏；T10 scan=0 |
| HEAD e2e sqlite3/namespace | 🔱 文件未改就宣称绿 | `high` | §8.2 ⛔ 直到删除 sqlite3 |
| `M-NH-09` 未签收 | exact-clean 迁移无 review | `medium` | evidence `closure.md` 签收硬闸 |

### 9.2 约束与前提

- **技术前提**：NH1 namespace harness 与 Port 证明基线；NH2 kind-only + old pin 共存；NH3 `NH3-10` 法律与 actual 列；NH5 T08-A 切代 + T08-B 红灯交接；NH7 至少可提供已 publication Item（single 与一 API member）。
- **运行时前提**：default-root `create_app()`；Layer-A namespace 经 Port 读出；L4 成功路径零 monkeypatch。
- **组织协作前提**：不重开 Q10–Q27；不新增 owner-gate；`M-NH-09` 与 compat retirement review 由执行期签收。
- **上线 / 合并前提**：`NH8-T01..T10` 全 PASS + evidence pack 目录齐；文档状态仍 `draft` 直至独立执行回填（本轮禁止标 executed）。

### 9.3 文档同步要求

- 需要同步更新的设计文档：执行期 evidence 回指本 AP code 闭集；**不改** QNA / final / reference-anchor
- 需要同步更新的说明文档 / README：可选指向 README K1 namespace；不在本 AP 改 README
- 需要同步更新的测试说明：evidence pack `docs/evidence/new-harvest/AP-NH8/` 文件名见 §10.3

### 9.4 完成后的预期状态

1. 七意图非法格在 admission 以稳定 code fail-loud，且不留下 Task/Process 行。
2. rebuild/changed-metadata 不再 materialize acquire/decode/clean Process；frozen clean digest exact；`NH5-T08-B` 绿。
3. deactivate/reactivate/delete/index.rebuild 的产品终态可由 namespaced `retrieval:search` 证明；reactivate 不恢复旧 serving。
4. API Item 与 single 同服务；old pin 可完结；upgrade 入口=0。
5. Capstone H 不再悬空；crash 全窗仍交 NH9。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

### 10.1 收口硬闸

所有 `mega + 退出层` 测试项必须 **PASS 且四元组证据齐全**。DoD：`NH8-T01..T10` 全 PASS；`M-NH-09` 及 compat retirement review 签收：

1. **applicability**：非法格 admission 拒绝且零 Task/Process（由 `NH8-T01` 证明）
2. **exact-clean**：rebuild/metadata 零 clean Process，artifact/digest exact；T08-B 绿（由 `NH8-T02`/`NH8-T03` 证明）
3. **lifecycle**：pointer/serving/vector/query 与状态一致；reactivate 不 restore；single/API 同法（由 `NH8-T04`..`NH8-T08` 证明）
4. **index rebuild**：新 generation、零 Revision/source/clean、旧代不命中（由 `NH8-T07` 证明）
5. **compat**：old pin 完成、新 Task 只 kind graph（由 `NH8-T09` 证明）
6. **restart law**：full_task exact；upgrade 入口=0；rebuild/index 分账（由 `NH8-T10` 证明）

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS 标准（可判定谓词） | PASS 证据（四元组）| 状态 |
|----------|--------|---------|-------------------------|---------------------|------|
| 非法格 admission 拒绝且零 Task/Process | `NH8-01` | `NH8-T01` | 每非法格 HTTP∈{422,409} 且 code∈闭集；该 `task_uuid` 的 `mkb_tasks` COUNT=0 且 `mkb_processes` COUNT=0 | `27fc3ca + 422/409 PASS + Q25 + 2026-08-30T04:53:13Z` | `PASS` |
| rebuild 零 acquire/decode/clean Process，digest exact | `NH8-02` | `NH8-T02` | process_key 家族计数=0；clean digest/object uuid 等于 frozen 输入；namespaced search payload=原 clean | `27fc3ca + process/query PASS + Q27 + 2026-08-30T04:53:13Z` | `PASS` |
| metadata 零 clean Process；no-change 短路；changed 切代 inherit | `NH8-03` | `NH8-T03` | no-change 无新 Revision；changed 新 Revision ∧ digest 不变 ∧ T08-B 计数=0 PASS | `27fc3ca + revision/digest/facet PASS + Q27 + 2026-08-30T04:53:13Z` | `PASS` |
| deactivate 后 query empty | `NH8-04` | `NH8-T04` | serving NULL ∧ pointer/vector withdrawn ∧ namespaced `results==[]` | `27fc3ca + withdraw/query PASS + Q25 + 2026-08-30T04:53:13Z` | `PASS` |
| reactivate 仍 empty 直到新 publish | `NH8-04` | `NH8-T05` | reactivate 后 serving 仍 NULL ∧ search `[]`；rebuild 后命中 | `27fc3ca + pointer/query PASS + Q25 + 2026-08-30T04:53:13Z` | `PASS` |
| delete tombstone / rebuild 409 | `NH8-04` | `NH8-T06` | rebuild POST 409 `intake-item-deleted` ∧ 新 Task COUNT=0 ∧ search `[]` | `27fc3ca + 409/query PASS + Q25 + 2026-08-30T04:53:13Z` | `PASS` |
| 新 generation、零 Revision/source/clean、旧代不命中 | `NH8-05` | `NH8-T07` | revision COUNT 不变；process 仅 `index.rebuild`；search hits 不含旧 generation | `27fc3ca + generation/query PASS + Q25 + 2026-08-30T04:53:13Z` | `PASS` |
| API Item 七意图同法、无 child kernel | `NH8-06` | `NH8-T08` | role≠`SCATTER_CHILD`；与 T02–T07 同谓词 | `27fc3ca + API lifecycle PASS + Q25 + 2026-08-30T04:53:13Z` | `PASS` |
| old pin 完成、新 Task 只 kind graph | `NH8-07` | `NH8-T09` | 旧序列不变；新 identity∈kind 闭集；in-flight>0 时 retire 失败可 rollback | `27fc3ca + old/new sequence PASS + Q18 + 2026-08-30T04:53:13Z` | `PASS` |
| full_task exact；upgrade 入口=0；rebuild/index 分账 | `NH8-08` | `NH8-T10` | actual digest 相等；upgrade scan=0；index 不 UPDATE S05、不 INSERT revision | `27fc3ca + lineage PASS + Q21/Q27 + 2026-08-30T04:53:13Z` | `PASS` |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | §10.1 六条谓词成立；Capstone H 可证 |
| 测试 | §8 `NH8-T01`..`NH8-T10` 全 PASS（退出硬闸项四元组齐全）；最低层不低于台账 C |
| 文档 | 本 AP 仍 `draft` 直至执行回填；evidence pack 目录存在且 SHA 真实 |
| 风险收敛 | `R-F11/F12/F04` 由 T02/T03/T10/T09 关闭；`M-NH-09` + retirement review 签收 |
| 可交付性 | NH9 只做 closed-set/crash/security 总验，不第一次补七意图/exact-clean |

**Evidence pack 目录**（final §9.3；本 AP 只规定文件名，不伪造 SHA）：`docs/evidence/new-harvest/AP-NH8/`

1. `manifest.json`：commit、Truth/Q（Q21/Q25/Q27/`T-O-401/405/407`）、work `NH8-01..08`、test `NH8-T01..10`、UTC
2. `tests.txt`：node IDs、exit code、duration、environment
3. `queries/intent-matrix.json`、`queries/rebuild-process-absence.json`、`queries/metadata-digest.json`、`queries/lifecycle-search.json`、`queries/index-generation.json`、`queries/api-item.json`、`queries/lineage.json`
4. `migrations/`：若本 AP 无 schema 变更则记录「无 DDL」+ 仍遵守 `restart_scope` 两值 forward-only proof
5. `security/`：非法格攻击向量、跨 team 404、`workflow_key` 拒绝、upgrade scan=0、无 namespace 422
6. `closure.md`：台账 D 六目标 PASS/FAIL、NOT-success 扫描、`M-NH-09` 签收、compat retirement review

### 10.4 NOT-成功识别

> 任一退出硬闸测试 `degraded / 未观察` ⇒ **不得标 `executed`**。按 closure 五态如实归类，不 silent overclaim。

下列任一成立即 **NOT-成功**（final §7.8 + 本 AP 假绿）：

1. **no-op cleaner** / 仅 assert byte-equal 却仍有 clean Process
2. **仅 DB 状态**（`lifecycle_state`/`publication_ready`）无 namespaced query
3. **reactivate 恢复旧 serving** 或旧 generation active
4. **28 格 / 7×4** 施工或测试造假矩阵（`FG-NH-15`）
5. **existing upgrade** 混入 retry/rebuild/第八 intent
6. sqlite3 直读 Turso（`FG-NH-12`）
7. 无 namespace 的 search 200（`FG-NH-05`）
8. Task succeeded 当可检索或当空集正例（`FG-NH-03`）
9. T08-B xfail / 改期待值（`FG-NH-17`）
10. monkeypatch / 503 当 API member 成功（`FG-NH-01/02`）
11. 用 L1 schema 测试顶替 L4 query（`FG-NH-13`）
12. 实验发车 / 0815-R7 进 DoD（`T-O-380`；`FG-NH-16`）

---

## 11. 执行日志回填（仅 `executed` 状态使用）

> 执行者：`Grok`
> 执行时间：`2026-08-30`
> 文档状态：`draft → executing → executed`
> 代码改动统计：`19 文件修改 / 3 新建 / schema bump 0`（实现 `27fc3ca`；admission 起步 `a575210`）

- **实际执行摘要**：P1 闭集 admission；P2 start-route replay/no-change + T08-B 转绿；P3–P5 namespaced lifecycle/index/API；P6 old-pin retire/rollback + lineage scan。
- **Phase 偏差**：
  - rebuild 仍经 `replay_frozen_clean → selected_clean → seal → preflight → accept_snapshot → construct`，未直达 accept（substrate-fit；process_key 家族仍为 0）。
  - scatter member clean 是 JSON envelope，replay 解包 `clean_text`（substrate-fit）。
  - 公开二次 delete 对 tombstone 为 409 零 Task，不是同 fence 服务层 no-op（与非法格 deleted 合同一致）。
- **阻塞与处理**：preflight 曾要求 decode/clean evidence → 改为 frozen-artifact lineage。API rebuild digest fence 曾把 `clean_digest` 当 CAS sha256 → 识别 envelope。
- **测试发现**：hard-gate `29 passed / 0 failed` ~206s。ingest selected-output 回归 7 passed。
- **后续 handoff**：`AP-NH9` closed-set / crash / Capstone I–J。不得第一次补七意图/exact-clean。

### 11.1 逐工作项状态

| 工作项 | 状态 | PR | 实际落点 | 备注 |
|--------|------|----|----------|------|
| `NH8-01` | ✅ done | `27fc3ca` | `targets.py` / `test_nh8_intent_applicability.py` | T01 |
| `NH8-02` | ✅ done | `27fc3ca` | `kind_family.py` / `acquisition_intents.py` | T02 |
| `NH8-03` | ✅ done | `27fc3ca` | `payload_extra` disposition / T08-B | T03 |
| `NH8-04` | ✅ done | `27fc3ca` | reactivate + delete tombstone e2e | T04–T06 |
| `NH8-05` | ✅ done | `27fc3ca` | `test_index_rebuild.py` Port+namespace | T07 |
| `NH8-06` | ✅ done | `27fc3ca` | `test_nh8_api_item_intents.py` | T08 |
| `NH8-07` | ✅ done | `27fc3ca` | retire/rollback tests | T09 |
| `NH8-08` | ✅ done | `27fc3ca` | `test_nh8_lineage_matrix.py` | T10 |

### 11.4 文档状态

`draft → executing → executed（2026-08-30）`。
residual → `AP-NH9`。

---

## 附录 · 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| `v0.1` | `2026-08-29` | Grok workflow new-harvest-nh6-nh9-action-plans | 由 final §7.8 派生；消费 Q21/Q25/Q27 与 RA08/RA02；关闭 NH5-T08-B 交接 |
| `v0.2` | `2026-08-29` | Grok fix-fleet | 吸收已核实 review：T02 唯一 PASS node=`::test_rebuild_replays_frozen_clean_without_acquire_decode_clean` 禁「或拆出」；T04/T05/T07 未清 sqlite3/namespace 前 ⛔ 不得进跑法；T05 独立 node；admission 锚 `config_snapshots.py:135`+`task_create.py:88,106`；`lifecycle_apply.py:34-134`；namespace raise `265-270` |
| `v0.3` | `2026-08-29` | Grok recon-fix | 头部钉 `NH5-T08-B` 关闭点=`NH8-T03`；T03 PASS 改为具名 node + 与 T02 同 sqlite3/namespace ⛔ 闸，禁止整份 HEAD rebuild 文件无条件跑法 |
| `v1.0` | `2026-08-30` | Grok | 执行回填 §11；文档状态 `executed`；T01–T10 PASS `27fc3ca` |
