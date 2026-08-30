# Nano-Agent 行动计划

> 服务业务簇: `MKB / new-harvest / closed-set-assurance`
> 计划对象: `closed-set manifest 证明 + crash/race/compat/security mega + evidence pack 不可变收口`
> 类型: `upgrade`（横切 assurance；**禁止第一次实现功能缺口**）
> 作者: `Grok workflow new-harvest-nh6-nh9-action-plans`
> 时间: `2026-08-29`
> 文件位置: `tests/fixtures/new_harvest/closed_set_manifest.v1.json`；`tests/fixtures/new_harvest/generate_closed_set_manifest.py`；`tests/unit/test_nh9_closed_set_manifest.py`；`tests/e2e/test_intake_identity_replay.py`；`tests/e2e/test_new_harvest_crash_windows.py`；`tests/e2e/test_new_harvest_closed_set.py`；`tests/e2e/test_new_harvest_runtime_security.py`；`tests/domain/test_nh9_evidence_pack_checker.py`；`docs/evidence/new-harvest/AP-NH1`…`AP-NH9/`（本轮文档不改生产代码）
> 上游前序 / closure:
> - `docs/eval/new-harvest/final-execution-plan.md` v1.0 `frozen` §7.9（唯一执行基线 · 台账 A/B/C/D）+ DAG §6 + 测试 §9 + 派生 §11.A
> - join：`AP-NH1` `stop-or-go.md=GO` 且 `NH1-T01..T07` PASS；`AP-NH2` `NH2-T01..T07`；`AP-NH3` `NH3-T01..T08`；`AP-NH4` `NH4-T01..T07`；`AP-NH5` `NH5-T01..T08`；`AP-NH6` `NH6-T01..T10`；`AP-NH7` `NH7-T01..T10`；`AP-NH8` `NH8-T01..T10`；九份 evidence pack
> - 本 AP 撰写时 `docs/plan/new-harvest/` 已入库 `AP-NH1`…`AP-NH5`；`AP-NH6`…`AP-NH8` 工作/测试/NOT-成功以 final §7.6–7.8 为冻结分母。后入库的 NH6–NH8 AP 只被 join，**不得**把其功能缺口第一次写进本 AP
> 下游交接:
> - Campaign closure / capstone I+J；无后继 new-harvest AP。实验发车服从 `T-O-380`，**不**由本 AP 解锁
> 关联设计 / 调研文档:
> - `docs/eval/new-harvest/final-execution-plan.md` v1.0 §4.2 OOS / §6 DAG / §7.9 / §9 / §10 `R-F13..F16` / §11.A
> - `docs/eval/new-harvest/proposed-planning.md` `FG-NH-01..17` 与 `W-NH-*` 目录（只 CITE 检查法，不是新 Truth）
> 冻结决策来源:
> - `docs/eval/new-harvest/pre-charter-qna.md` v1.0 Q26 → `T-O-406`；Q10/Q17/Q18/Q19/Q20/Q21/Q24/Q27 → `T-O-390/397/398/399/400/401/404/407`（只读引用；本 action-plan 不填写 Q/A）
> - `docs/eval/new-harvest/pre-initial-planning-qna.md` v0.5 `T-O-376/378/380/381/383/389`
> grounding 来源:
> - HEAD `1221aa1` 实测 `path:line`（§7.1 行号以本文件独立 `read_file` 为准）
> - `docs/eval/new-harvest/reference-anchor/assessment-analysis-09-assurance-replay-concurrency-and-compatibility.md`（RA09 全文）
> 关联 reference-anchor:
> - [`assessment-analysis-09-assurance-replay-concurrency-and-compatibility.md`](../../eval/new-harvest/reference-anchor/assessment-analysis-09-assurance-replay-concurrency-and-compatibility.md)（主面）
> - 邻面 RA01–RA08 只消费 gap ID / 失败法，不重写功能设计
> 文档状态: `executed`
> 台账 ID 区间（final §11.A `7.9 AP-NH9`）：`NH9-01..11 / NH9-A01..07 / NH9-T01..11`
> HEAD: `1221aa1`（代码分母）；文档 HEAD `76b20a0`

**禁止重编号、合并或删除上述 ID。无 `NH9-T12`。`NH9-11` 是工作项，**不单列 Test-ID**；experiment **不进 DoD**。`NH9-T11` PASS 只映射 `NH9-10` pack checker。`NH9-11` 仅负向谓词：`in_closure_join=false`、closure PASS 列表不含 experiment/0815/vendor 分数（缺分数不得使 T11 FAIL；有分数不得使 T11 PASS）。骨架文件可以存在，但 **不是** T11 EXIT0 条件。**

---

## 0. 执行背景与目标

new-harvest 产品法（`T-O-376/381/383/406`）要求四通道 live-to-retrieval、绑定后 fail-loud、四层测试不可互换。HEAD `1221aa1` 已有可复用的 Task 指纹 replay（`task_create.py:67-140`）、Process Outcome CAS（`runtime_outcome.py:46-182`）、scatter Snapshot fan-in（`runtime_scatter.py:277-483`；`:293-311` Snapshot/ChangeSet 分母，`:320-346` zero 恢复）、retrieval dual fence（`retrieval_rank.py:38-76,339-433`），但 **闭集证明未成立**：source e2e 仍 monkeypatch 且停 `running`（`test_source_capability_paths.py:99-101,166-168`）；identity replay 仍 `sqlite3.connect`（`test_intake_identity_replay.py:15,100-124`）；`CLEAN_EMPTY` / `task-identity-conflict` 在 `tests/` **零命中**；崩溃窗 `W-NH-*` 未逐窗有 node；九份 evidence pack 与 `FG-NH-01..17` 全绿清单不存在。

本 AP 是 DAG **末节点**（final §6）：join NH4/NH8/全部 evidence，只做 closed-set 生成、交叉窗口、compat/security mega 与不可变收口。**第一次发现本应属于 NH6/7/8 的功能缺口 = 本 AP 失败**（`R-F15`）：在 §8.4 点名交回对应上游 AP 并标 campaign blocked，**禁止**在本 AP 加 `NH6-08` 类功能工作。waiver 只能具名延期，不得降层、不得覆盖 `T-O-376/378/381/383`（`T-O-406`）。`.experiment` 骨架服从 `T-O-380`，**不进** closure join。

- **服务业务簇**：`MKB / new-harvest`
- **计划对象**：closed-set manifest 证明 + crash/race/compat/security mega + immutable evidence pack
- **本次计划解决的问题**：
  - 合法格/负格/82 work IDs/层级未冻结为可哈希 manifest（`T-O-381/406`；NH1-T07 只预埋矩阵 digest）
  - 横切 replay/crash/race/compat/security 未按 `W-NH-*` 与 `FG-NH-01..17` 收成可判定证明（RA09；`T-O-383/400/404`）
  - 九 AP 四元组证据与 waiver 未不可变封存；experiment/0815/vendor 易被误当 DoD（`T-O-380`；`FG-NH-16`）
- **本次计划的直接产出**：
  - 冻结 `tests/fixtures/new_harvest/closed_set_manifest.v1.json`（含 82 work IDs、10+3、七意图、层、负格、digest）
  - capstone I/J 测试面：`test_new_harvest_crash_windows.py` / `test_new_harvest_closed_set.py` / `test_new_harvest_runtime_security.py`
  - `docs/evidence/new-harvest/AP-NH9/` + 九包 checker（`NH9-T11`）
- **本计划不重新讨论的设计结论**：
  - L1 unit、L2 integration/UoW、L3 default-root e2e、L4 retrieval-facet mega 不可互换；fault/race/security 非替代层；waiver 仅具名延期、须到期 reopen，不得覆盖 `T-O-376/378/381/383`（来源：Q26 / `T-O-406`）
  - unit/e2e 属于 completeness；**.experiment 发车日不冻、不进 DoD**（来源：`T-O-380`）
  - 绑定后不换工人；内容失败显式失败、不出向量；同指纹 replay / 异指纹 409（来源：Q3 / `T-O-383`）
  - NH9 不第一次补功能、不降层（来源：final §5 / §7.9 / `R-F15`）

---

## 1. 执行综述

### 1.1 总体执行方式

横切 assurance、**先合同后注入、先负例后 mega、只 join 不施工功能**。Phase 1 用 registries + NH1-T07 预埋文件生成并冻结 closed-set digest。Phase 2 把 Task/intake replay 与 bad-input 零向量钉成 Port 化证明。Phase 3 按 `W-NH-*` 逐窗注入 crash（🔱 上游已规定节点，不重写 seal/fan-in/publication 实现）。Phase 4 扩 upload/GC 交错全排列与 scatter zero/child/query。Phase 5 联合 old-pin × kind 图 × legacy alias 不当 actual，并跑每 knowledge 格 L4 mega（🔱 NH7 正格，禁止跳 ingest 直插向量）。Phase 6 收 runtime 安全门与九包四元组；experiment 只落空骨架。任一层发现功能缺口 → STOP 本 AP 并交回上游，禁止就地实现。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | Closed-set generator | `L` | 读 registries + NH1-T07 预埋；覆盖 82 works / 10+3 / 七意图 / 层；冻结 digest | NH1-T07 预埋路径存在；NH1–NH8 台账 ID 已冻结 |
| Phase 2 | Replay + fail-loud | `L` | same replay / 409 / double-flight；empty/bad/unknown → query 0；Port 化 | Phase 1；NH1-T02 Port 纪律 |
| Phase 3 | Crash windows | `XL` | `W-NH-CREATE/SEL/SEAL/PROCESS/FANIN/PUB/OUTBOX` 逐窗 node、effect-once | Phase 2；🔱 NH3-T07 / NH1-T02 / NH8 publication |
| Phase 4 | Object race + scatter | `L` | upload/GC 全排列；exhausted_zero / bad member / child fail / fan-in repair + query | Phase 3；🔱 NH4-T05/T06 / NH7-T09 |
| Phase 5 | Compat + retrieval mega | `XL` | old pin 可完结；legacy alias 不当 actual；每 knowledge 格 namespace+facet+proof | Phase 1 manifest；🔱 NH2-T06 / NH3-T06 / NH7 正格 / NH5-T07 |
| Phase 6 | Security + evidence + experiment | `L` | isolation/readiness/SBOM/CVE/backpressure；九包四元组；experiment 日期/分数空且不进 join | Phase 5；🔱 NH6-T02/T05/T08/T09；全部 evidence |

> 说明：上表 `规模` 是描述性提示，**不是开工前的体量判定闸**。

### 1.3 Phase 说明

1. **Phase 1 — Closed-set generator**
   - **核心目标**：机器生成并冻结 manifest，使 T01 可判定「82 / 10+3 / 七意图 / 层」而无手抄笛卡尔积。
   - **为什么先做**：后续 mega/fault 的行来自 manifest；digest 漂移必须在注入窗口前锁死（`T-O-381/406`）。
2. **Phase 2 — Replay + fail-loud**
   - **核心目标**：`T-O-383` 的身份法与空/坏/unknown 零向量可在 Port 上证明。
   - **为什么放在这里**：crash 注入若建立在 sqlite3-on-Turso 或假接线之上，整窗都是假绿（`FG-NH-12/01`）。
3. **Phase 3 — Crash windows**
   - **核心目标**：proposed §9.5 九窗中的 CREATE/SEL/SEAL/PROCESS/FANIN/PUB/OUTBOX 各有 deterministic node，无双 effect / 热切。
   - **为什么放在这里**：身份法成立后才能区分 replay 与崩溃修复；SEL/SEAL 🔱 NH3，FANIN 🔱 NH1，PUB 🔱 NH8，本 AP 只交叉证明。
4. **Phase 4 — Object race + scatter**
   - **核心目标**：PROM-CAT/GC 交错不丢 bytes、不假 Item；zero/child 语义与 query 一致。
   - **为什么放在这里**：对象窗与 fan-in 依赖 Phase 3 的 CAS 夹具，但产品断言属 NH4/NH7，禁止重写 GC/scatter 内核。
5. **Phase 5 — Compat + retrieval mega**
   - **核心目标**：capstone A 的 old pin + capstone C–H 的每格 L4；失败格零命中。
   - **为什么放在这里**：正格必须已经在 NH7/NH8 接通；本 AP 只按 manifest 查询，不重写 lane。
6. **Phase 6 — Security + evidence + experiment**
   - **核心目标**：capstone J：`FG-NH-01..17` 全绿、九包四元组、无过期 waiver；experiment 空字段且不进 join。
   - **为什么放在这里**：安全门与 pack 是 closure 最后一闸；把实验分数当 PASS = `FG-NH-16` 失败。

### 1.4 执行策略说明

- **执行顺序原则**：generator → 身份/负例 → 崩溃窗 → 对象/scatter 交错 → compat/L4 mega → 安全/证据。禁止先跑 mega 再补 manifest。禁止在 NH9 实现 strategy/intent/route。
- **风险控制原则**：`R-F15` 最高优先：功能缺口交回 NH6/7/8。`R-F13` 禁止 L1 顶 L3/L4。`R-F14` 禁止 Task/`publication_ready` 顶 query。发现缺口写入 `docs/evidence/new-harvest/AP-NH9/closure.md` 的 `campaign_blocked` 与上游 AP ID，本 AP 保持 `draft` 不得标 executed。
- **测试推进原则**：T01 短途契约 → T02/T03/T08 L2 → T04/T05/T06 fault/race soak → T07/T09 L3/L4 mega → T10 security soak → T11 pack checker。分层锁死台账 C；waiver 只延期。
- **文档同步原则**：执行期只写 evidence pack 与 manifest fixture；不改 QNA/final/RA/assessment-index。本轮文档回合不改 `src/`/`api/`/`intake/`/`tests/`（AP 规定将改的测试路径，执行期才落地）。
- **回滚 / 降级原则**：禁止降层、禁止改期待值掩盖 S1（`FG-NH-17`）、禁止 experiment/0815/live vendor 顶替。manifest digest 变更必须重跑 T01 并更新九包 `manifest.json` 的 digest 引用，不得手工改测试金值保绿。

### 1.5 本次 action-plan 影响结构图

```text
closed-set assurance / immutable closure
├── Phase 1: Closed-set generator
│   ├── registries → 10 strategy + 3 operation + 七意图 applicability
│   ├── NH1-T07 预埋 tests/fixtures/new_harvest/closed_set_manifest.v1.json
│   └── 82 work IDs + L1–L4 层 + 负格 + 冻结 digest
├── Phase 2: Replay + fail-loud
│   ├── task_create.py:67-140 fingerprint / ConflictError 409
│   ├── test_intake_identity_replay.py Port 化（删 sqlite3）
│   └── empty/bad/unknown → 零向量 query
├── Phase 3: Crash windows
│   ├── W-NH-CREATE / PROCESS（本 AP 夹具 + Outcome CAS）
│   ├── W-NH-SEL / SEAL 🔱 NH3-T07
│   ├── W-NH-FANIN 🔱 NH1-T02
│   └── W-NH-PUB 🔱 NH8 · W-NH-OUTBOX runtime_outbox.py:131-139
├── Phase 4: Object race + scatter
│   ├── W-NH-PROM-CAT / W-NH-GC-INGEST 🔱 NH4-T05/T06 全排列
│   └── exhausted_zero / child fail / query 🔱 NH7-T09 + scatter e2e
├── Phase 5: Compat + retrieval mega
│   ├── old pin / unknown digest 🔱 NH2-T06
│   ├── legacy alias 不当 actual 🔱 NH3-T06
│   └── 每 knowledge 格 namespace+facet+proof 🔱 NH7 正格 / NH5-T07
└── Phase 6: Security + evidence + experiment
    ├── test_new_harvest_runtime_security.py 🔱 NH6-T02/T05/T08/T09
    ├── 九份 docs/evidence/new-harvest/AP-NHn/ 四元组 checker
    └── experiment schema：日期/分数空，in_closure_join=false
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** `S-NH-F9`：closed-set、race/crash/security/compat/retrieval mega（`T-O-383/406`）
- **[S2]** Closed-set generator：读 registries + NH1-T07 预埋；合法格 path/actual/semantic/query/negative；冻结 digest；覆盖 **82 work IDs** + 10+3 + 七意图（`NH9-01` / `NH9-T01`）
- **[S3]** Task/intake/concurrent create replay 与 409；identity 测试 **Port 化**（`NH9-02` / `NH9-T02`；`T-O-383`）
- **[S4]** Bad-input 矩阵：empty/bad media/member、unknown keys、missing supply → 负向 query 0（`NH9-03` / `NH9-T03`；`T-O-378/383`）
- **[S5]** `W-NH-*` 崩溃窗逐窗 node 与 effect-once（`NH9-04` / `NH9-T04`/`T05`；`T-O-400/406`）
- **[S6]** Upload/GC 交错全排列（`NH9-05` / `NH9-T06`；`T-O-404`）与 scatter zero/member/child/fan-in+query（`NH9-06` / `NH9-T07`；`T-O-397`）
- **[S7]** Old pin + new graph + unknown digest + legacy alias 不当 actual（`NH9-07` / `NH9-T08`；`T-O-390/398/401`）
- **[S8]** 每 knowledge 格 L4 mega：namespace + proof + facet；stale/lifecycle 排除（`NH9-08` / `NH9-T09`；`T-O-376/389/406`）
- **[S9]** Runtime security closure：missing deps / malicious PDF/URL / backpressure / SBOM/CVE/waiver（`NH9-09` / `NH9-T10`；`T-O-399/406`）
- **[S10]** Immutable evidence pack + `FG-NH-01..17` 全绿（`NH9-10` / `NH9-T11`）。experiment 骨架日期/分数空且不进 join（`NH9-11`，**无 Test-ID / 不进 DoD**）

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** `O-NH-01` live connector/cookie/tunnel、第五 kind、caller `workflow_key`、`action_branch`
- **[O2]** `O-NH-02` cuts/g0 算法重开、按通道复制 tail、前端/answer generation
- **[O3]** `O-NH-03` existing-object new-cleaner/validator upgrade（`T-O-401`）
- **[O4]** `O-NH-04` raw object GET/list/presign/browser
- **[O5]** `O-NH-05` experiment 发车/评分；骨架非 DoD（`T-O-380`）
- **[O6]** `O-NH-06` 通用 Workflow JOIN/DSL/自由表达式/loader；云 OCR/CF/R2/SMCP runtime
- **[O7]** **任何新 strategy / 新 intent / 新 public route**
- **[O8]** 第一次实现 NH6 供给、NH7 lane、NH8 exact-clean/guard、NH3 seal、NH4 upload 内核
- **[O9]** 引入 Temporal/Kafka/TigerBeetle DST 运行时（RA09 `NH9-A07` 只借失败法）
- **[O10]** 口头 exactly-once delivery；把 Kafka EOS 栈写入本仓

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| closed-set manifest + 82/10+3/七意图 | `in-scope` | final §7.9 `NH9-01`；§9.2 J | 推翻 `T-O-381/406` 须新 Truth |
| W-NH-* 交叉证明 | `in-scope` | §7.9 `NH9-04`；proposed §9.5 | 无 |
| L4 每格 query+facet+proof | `in-scope` | `NH9-08`；`T-O-376/389` | 正格未接通 → 交回 NH7，本 AP blocked |
| 九包四元组 checker | `in-scope` | `NH9-10`；§9.3 | 无 |
| experiment schema 空字段 | `in-scope`（非 DoD） | `NH9-11`；`T-O-380` | 发车日另册 |
| 新 strategy / intent / public route | `out-of-scope` | final §4.2；本 PROMPT OOS | 新 owner-gate |
| PDF/browser/OCR 库选型与接线 | `out-of-scope` | `S-NH-F6` / NH6；`T-O-393` 不锁库 | 本 AP 只 🔱 NH6 测试 |
| 10+3 lane 实现 | `out-of-scope` | `S-NH-F7` / NH7 | 缺口交回 NH7 |
| rebuild intent-guard / no-op cleaner | `out-of-scope` | `S-NH-F8` / NH8；`T-O-407` | 缺口交回 NH8 |
| Temporal Worker Versioning | `out-of-scope` | RA09 substrate-fit 失败；`T-O-398` 留本仓 pin | 无 |
| L1 替代 L3/L4 | `out-of-scope` | `T-O-406`；`R-F13`；`FG-NH-13` | waiver 只延期 |
| 0815-R7 inline 4/4 当四通道 | `out-of-scope` | `T-O-376`；`FG-NH-16` | 无 |

---

## 3. 业务工作总表

> 编号 = final 台账 A `NH9-01`…`NH9-11`。每个工作项保持不可约三元组：file:line / 收口目标 / Test-ID。

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| `NH9-01` | Phase 1 | Closed-set generator | `add` | `src/contracts/intake/strategies.py:15-26,46-`（10 `CleanStrategyKey`）；`intake/api/registry.py:73-104`（3 ops）；`src/contracts/api/models.py:278-286`（七意图）；NH1-T07 预埋 `tests/fixtures/new_harvest/closed_set_manifest.v1.json`；🆕 `tests/fixtures/new_harvest/generate_closed_set_manifest.py`；🆕 `tests/unit/test_nh9_closed_set_manifest.py` | manifest 含 82 works、全部合法格/负格/层级，digest 可复现 | `NH9-T01` | `high` |
| `NH9-02` | Phase 2 | Task/intake/concurrent create | `update` | `src/runtime/task/task_create.py:67-140`（`NH9-A01`）；`src/contracts/common/errors.py:92-94`；🔱 `tests/e2e/test_intake_identity_replay.py:1-125`（删 `:15`/` :100-124` sqlite3）；🆕 concurrent create node；`src/persistence/ports.py:10-27`。`test_inline_ingress_staging.py` **⛔ 不得当 T02 PASS**（HEAD sqlite3-on-Turso） | same replay 原视图；different 409；double-flight 无双根；object refs 不双造 | `NH9-T02` | `high` |
| `NH9-03` | Phase 2 | Bad-input matrix | `add`/`update` | `intake/web/__init__.py:28-29`；`intake/pdf/__init__.py:59-60`；`src/runtime/intake/clean_preflight.py:544-548`；`src/services/retrieval/retrieval_request.py:265-270`；🆕/♻️ 负向 query 节点 | empty/bad/unknown/missing supply → typed fail 且 retrieval 0 命中 | `NH9-T03` | `high` |
| `NH9-04` | Phase 3 | W-window injection | `add`/`update` | 🆕 `tests/e2e/test_new_harvest_crash_windows.py`；`runtime_outcome.py:46-182`（`NH9-A02`）；🔱 NH3-T07 `tests/e2e/test_nh3_seal_crash_windows.py`；🔱 NH1-T02 `tests/e2e/test_nh1_fanin_recovery_port.py`；`runtime_outbox.py:131-139`；`src/services/index_retirement.py:1-10,97` | 九窗中 CREATE/SEL/SEAL/PROCESS/FANIN/PUB/OUTBOX deterministic、无双 effect/热切 | `NH9-T04` / `NH9-T05` | `high` |
| `NH9-05` | Phase 4 | Upload/GC races | `update` | 🔱 NH4-T05 `tests/unit/test_ns6_gc_toctou.py:68-89`；🔱 NH4-T06 `tests/unit/test_nh4_upload_ttl_gc.py`；`src/services/object_gc.py:189-240`；🔱 NH4-T02 replay race | parallel upload / pending TTL / quarantine+newref / tombstone/reupload 全排列不丢 bytes、不假 Item | `NH9-T06` | `high` |
| `NH9-06` | Phase 4 | zero/member/child/fanin | `update` | `src/runtime/workflow/runtime_scatter.py:277-483`（`NH9-A03`；`:293-311` 分母、`:320-346` zero、`:430-474` 单 proof）；🔱 `tests/e2e/test_registered_api_scatter.py:318-326,484-499`（须已 Port 化且补 namespaced query 后才可 🔱；未清前 ⛔ 不得进 T07 跑法）；🔱 NH7-T09 | exhausted_zero 零产物；bad member fail；child fail 父 failed 且 sibling 不得使父检索成功；crash repair + query | `NH9-T07` / `NH9-T05` | `high` |
| `NH9-07` | Phase 5 | Old pin+actual | `update` | 🔱 NH2-T06 `tests/unit/test_workflow_revision_compatibility.py:105-192`；🔱 NH3-T06；`src/runtime/workflow/runtime_core.py:608-621` | old graph 可完结；new Task kind-only；unknown digest 零 Process；legacy alias 不当 actual | `NH9-T08` | `high` |
| `NH9-08` | Phase 5 | Retrieval-facet mega | `add` | 🆕 `tests/e2e/test_new_harvest_closed_set.py`；`src/services/retrieval/retrieval_rank.py:38-76,339-433`（`NH9-A04`）；🔱 NH7-T03..T08 正格；🔱 NH5-T07 facet SQL | 每 knowledge 格真实 ingest 后 namespace+trace+facet 命中；stale/lifecycle 排除；失败格零命中 | `NH9-T09` / `NH9-T03` | `high` |
| `NH9-09` | Phase 6 | Runtime closure | `update` | 🔱 `tests/e2e/test_new_harvest_runtime_security.py`（**NH6 已建**隔离/egress/backpressure/readiness 节点；本 AP 只加不重叠的战役汇总断言）；🔱 NH6-T02/T05/T08/T09；§7.3 威胁模型 | isolation/readiness/SBOM/CVE/backpressure 全门；无 root/`--no-sandbox` | `NH9-T10` | `high` |
| `NH9-10` | Phase 6 | Immutable pack | `add` | 🆕 `tests/domain/test_nh9_evidence_pack_checker.py`；`docs/evidence/new-harvest/AP-NH{1..9}/`（final §9.3 六类文件） | 每 AP 四元组齐、waiver 合规、UTC/commit 固定；`FG-NH-01..17` 全绿清单 | `NH9-T11` | `medium` |
| `NH9-11` | Phase 6 | Readiness skeleton | `add` | 🆕 `.experiment/new-harvest/readiness.schema.json`（或 manifest 内 `experiment` 对象）；不写入 closure join 清单 | matrix/run schema 允许存在；日期/分数空；`in_closure_join=false` | **无独立 Test-ID**（负向：缺分数不得使 `NH9-T11` FAIL；有分数不得使 T11 PASS） | `low` |

**82 work IDs 闭集（T01 必须逐 ID 相等，禁止只数 82）**：`NH1-01..09`（9）+ `NH2-01..08`（8）+ `NH3-01..10`（10）+ `NH4-01..08`（8）+ `NH5-01..08`（8）+ `NH6-01..10`（10）+ `NH7-01..10`（10）+ `NH8-01..08`（8）+ `NH9-01..11`（11）= **82**。

---

## 4. Phase 业务表格

### 4.1 Phase 1 — Closed-set generator

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH9-01` | Closed-set generator | **净新/高风险，有序子步：** a) 读 `CLEAN_STRATEGY_DEFINITIONS` / `CleanStrategyKey` 十值（`strategies.py:15-26`）与 `REGISTERED_PROVIDER_OPERATIONS` 三元组（`registry.py:73-104`）。b) 读七意图 Literal（`models.py:278-286`）生成 applicability：**禁止** 7×4 笛卡尔积（`FG-NH-15`）；非法格必须有 `disposition`+error code。c) 读 NH1-T07 已预埋的 `tests/fixtures/new_harvest/closed_set_manifest.v1.json`，断言 10+3 合法格 digest 与 NH1 预埋一致，不得 silently 丢掉该路径。d) 写入全部 **82** work ID、每格预期 `path` / `actual_binding` / `semantic` / `query` / `negative`、每格最低层 `L1|L2|L3|L4`、九窗 `W-NH-*`、`FG-NH-01..17`。**禁止**改 NH1-T07 预埋的 `strategy_cells` / `op_cells` / `intent_illegal` + 10+3 canonical `digest` 字节（只 append 82/windows/FG）。e) canonical JSON + SHA-256 冻结顶层 `digest`；生成器必须幂等（两次运行字节相等）。f) `experiment.launch_date`/`scores` 必须 JSON `null`，`in_closure_join=false`。g) 负格：empty/unknown/illegal-intent/missing-supply 标明「query 期望 0」。 | 🆕 `tests/fixtures/new_harvest/generate_closed_set_manifest.py`；`tests/fixtures/new_harvest/closed_set_manifest.v1.json`；registries 上列行 | 可哈希闭集；非法格非 live | `NH9-T01` | digest EXIT0；len(work_ids)==82 且集合相等 |

### 4.2 Phase 2 — Replay + fail-loud

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH9-02` | Task/intake/concurrent create | **🔱 扩证明，不改指纹算法：** a) same fingerprint 二次 POST 返回原 Task 视图、`replayed=True`、不第二套 Execution/object ref（`task_create.py:67-85,101-104`；inline 正例 `:85-88`）。b) 同 `(team,task)` 异 fingerprint → `ConflictError("task-identity-conflict")` HTTP 409（`:83-84,102-103,139-140`；`errors.py:92-94`）。**今日 `tests/` 零命中，必须补。** c) double-flight：两协程同 identity；一成功一 409 或 replay，`COUNT(mkb_executions WHERE parent IS NULL)`=1。d) intake 同 `external_key`+同内容 replay 指针可解析。e) **整文件 Port 化** `test_intake_identity_replay.py`：删除 `import sqlite3`（`:15`）与 `sqlite3.connect`（`:100-124`），改 `PersistencePort.transaction()`（`ports.py:10-27`）。f) 并发/冲突断言同样只经 Port，禁止 sqlite3-on-Turso。g) `test_inline_ingress_staging.py` **⛔ 不得当 T02 PASS**（HEAD 仍 `sqlite3.connect` + `persistence_backend="turso"`）。 | `task_create.py:67-140`；`test_intake_identity_replay.py`；🆕 concurrent node | 无双根、无 last-writer-wins | `NH9-T02` | 并行 PASS；源码无 sqlite3 |
| `NH9-03` | Bad-input matrix | **✅/♻️ handler + 🆕 负向 query：** a) 空 HTML/空 PDF 文本 → `CLEAN_EMPTY` 422（`web/__init__.py:28-29`；`pdf/__init__.py:59-60`）或 preflight `clean_candidate_empty`（`clean_preflight.py:544-548`）；Process 非 succeeded。b) bad media / API empty member：schema `min_length=1` 拒，**禁止** skip 后 root succeeded（对打 RA09 dedicated catch skip）。c) unknown filter/intent/strategy keys → 422/409，不建非法 Task/Process（七意图非法格交 NH8-T01 回归）。d) missing supply（未注入 browser/OCR）→ typed 不可用码；**此格不是 live DoD**（`FG-NH-02`）。e) 所有失败格 POST namespaced search → `results==[]` 且无向量行（Port 计数）。f) 禁止 decode 盗用 `CLEAN_OCR_CAPABILITY_UNAVAILABLE` 当空成功的对立面却仍出向量。 | handler 上列；🆕 `tests/e2e/test_new_harvest_closed_set.py` 负格节点与/或 unit | 失败不出向量 | `NH9-T03` | 负向 query PASS |

### 4.3 Phase 3 — Crash windows

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH9-04` | W-window injection | **XL / 每窗一 node，禁止口头 exactly-once：** a) **`W-NH-CREATE`**：在第一次 identity 检查成功与 INSERT 之间 kill/raise（`task_create.py:67-92` 双事务注释）；恢复后同指纹 replay 或单根，无双 object ref。b) **`W-NH-SEL`/`W-NH-SEAL`**：🔱 NH3-T07 五节点（`test_nh3_seal_crash_windows.py`）；本文件可再导出同名包装 node，**不得**重写 seal 实现。SEL：facts 已写、actual unsealed、零向量。SEAL：route+actual+eligibility 同 UoW；中途无半封；异 digest 409（`T-O-400`）。c) **`W-NH-PROCESS`**：handler 已成功、Outcome CAS 前/后注入（`runtime_outcome.py:46-117`）：同 digest replay `return False`；异 digest `stale-process-outcome`；`rowcount!=1` → `stale-process-fence`；actual/`process_key` 不变。d) **`W-NH-FANIN`**：🔱 NH1-T02 Port recovery；子已终、父 waiting → 一次 repair 父 succeeded+`proof_ref`；禁止 sqlite3（scatter `:327` 今日反例）。e) **`W-NH-PUB`**：🔱 NH8 publication/index.rebuild：vector/proof/pointer/serving 切中崩溃不得双 serving；不完整 proof 对 `retrieval_rank.py:38-76,339-433` dual fence 不可见。f) **`W-NH-OUTBOX`**：重复 delivery `vectorize` consumer **无业务副作用**（`runtime_outbox.py:131-139`）；向量行不因 ACK 倍增。g) 效果一次 = 闭集 CAS 效果，**禁止**宣称 exactly-once delivery（RA09 `RA-09-WEB-04`）。 | 🆕 `tests/e2e/test_new_harvest_crash_windows.py` + 🔱 上游节点 | 每窗可复现；无热切 | `NH9-T04` / `NH9-T05` | fault report 九窗（余下 PROM-CAT/GC 见 T06） |

### 4.4 Phase 4 — Object race + scatter

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH9-05` | Upload/GC | **🔱 NH4-T05/T06 交错全排列，不重写 GC：** a) parallel 同 team+digest+size → 同一 handle（🔱 NH4-T02）。b) live `upload_pending` 使 `collect_candidates` 不选中。c) TTL release 后过 grace 才 quarantine。d) quarantine 中新 pending/ingest ref → `LIVE_REFERENCE` restore（`object_gc.py:189-240`；`test_ns6_gc_toctou.py:68-89`）。e) tombstone 后再传 = 新生命周期，不得复活已删 Item（upload 本就不造 Item）。f) 全排列：upload∥GC、ingest∥GC、TTL∥ingest、quarantine∥newref。g) **禁止** grace=0 赌竞态。 | NH4 测试文件；`object_gc.py:189-240` | 不丢 bytes、不假 Item | `NH9-T06` | interleavings PASS |
| `NH9-06` | zero/member/child/fanin | **🔱 NH7-T09 + scatter，加 query：** a) exhausted_zero：独立 `result_disposition`，零 child/Revision/vector/proof，retrieval empty，fingerprint 可 replay（`T-O-397`）。b) bad member → 拒收，root 不得 succeeded。c) child fail：父 `scatter-required-child-failed`（`:484-499`）；**禁止** sibling `publication_ready` 使父检索成功（`FG-NH-04`）。d) fan-in crash repair 🔱 T05/NH1-T02。e) 每场景 namespaced query：成功格命中、失败/zero 格 0。f) 不把 `publication_ready` 当 query。 | `runtime_scatter.py:277-483`；scatter e2e（未 Port/query 前 ⛔）；NH7-T09 节点 | zero/child 语义与 query 一致 | `NH9-T07` / `NH9-T05` | result+query PASS |

### 4.5 Phase 5 — Compat + retrieval mega

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH9-07` | Old pin+actual | **🔱 NH2-T06 + NH3-T06：** a) 旧 compiled_digest Execution 在 kind 图激活后 process_key 序列不变（`test_workflow_revision_compatibility.py:105-168`）。b) 新 Task kind-only，不解析旧 selector key。c) unknown digest → `workflow-compiled-plan-unavailable` 且零 Process（`:608-621` 与 compat `:175-192`）。d) 旧列 `s05_binding_digest` / domain 64-hex **不得**使 `actual_binding_state='sealed'`（`FG-NH-08`）。e) 不跑 Temporal Event History。 | NH2-T06 / NH3-T06 文件 | old pin 可完结；alias 非 actual | `NH9-T08` | sequence + SQL 三态 PASS |
| `NH9-08` | Retrieval-facet mega | **XL / 🔱 NH7 正格，不重写 lane：** a) 按 manifest **每个 knowledge 正格**：真实 default-root ingest（零 monkeypatch，`FG-NH-01`）。b) **禁止**跳过 ingest `INSERT` `mkb_vector_records`。c) admitted clean 非空（`FG-NH-06`）。d) POST `/retrieval:search` 必带 Layer-A `namespace_key`（`retrieval_request.py:265-270`；`FG-NH-05`）。e) 命中含 content + traceback resolved + NH5 facet（realm/semantic_channel 等；`FG-NH-07`）；SQL fence 在 rank 前（`retrieval_rank.py:38-76,339-433`），禁止 Python post-filter。f) stale generation / deactivated / deleted / 非 serving revision 排除。g) 失败格走 T03 零命中。h) 发现某格不能 query → §8.4 交回 NH7，campaign blocked，**不在本 AP 补 worker**。 | 🆕 `tests/e2e/test_new_harvest_closed_set.py` | 每正格 L4 可检索 | `NH9-T09` / `NH9-T03` | manifest query PASS |

### 4.6 Phase 6 — Security + evidence + experiment

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH9-09` | Runtime closure | **♻️ 🔱 NH6 测试 + 战役 security 面：** a) missing deps → component 不可用，**不得** `/ready` 绿当供给在场（`FG-NH-11`）。b) 恶意 PDF/URL：parser 无网、kill 后 API 存活（🔱 NH6-T02）；browser 非 root、生产零 `--no-sandbox`、S16 egress（🔱 NH6-T05）。c) backpressure 满载零下游调用（🔱 NH6-T08 的 **L2** `::test_backpressure_zero_downstream`；**不得**用 NH6 unit 单独关闭）。d) readiness 正负一致（🔱 NH6-T09）。e) SBOM/CVE/pin/waiver 清单存在且 waiver 不覆盖 foundational T-O。f) 固定路径 `tests/e2e/test_new_harvest_runtime_security.py` **NH6 已建**；本 AP 只 🔱 那些 node +（可选）不重叠战役汇总，**禁止** 🆕 同名产品 node。g) 缺隔离/接线 = NH6 功能缺口 → 交回，不在本 AP 写 parser。 | 🔱 `test_new_harvest_runtime_security.py`（NH6 已建）+ NH6-T02/T05/T08/T09 | 安全门全过 | `NH9-T10` | security pack PASS |
| `NH9-10` | Immutable pack | **🆕 checker：** a) 枚举 `docs/evidence/new-harvest/AP-NH1`…`AP-NH9` 九目录。b) 每包至少：`manifest.json`（commit、Truth/Q、work/test IDs、UTC）、`tests.txt`、`queries/`、`migrations/`、`security/`、`closure.md`（final §9.3）。c) 每 Test-ID 四元组：`commit SHA + pytest/query ID PASS + Truth/Q + UTC`。d) `FG-NH-01..17` 全绿清单写入本包 `security/fg-nh-01-17.md`。e) waiver：owner、affected Truth/AP/gate、理由、到期/reopen；无过期项；不得覆盖 `T-O-376/378/381/383`。f) **不**把 `NH9-11` 分数或 0815 runs 列入 PASS 集合（`FG-NH-16`）。 | 🆕 `tests/domain/test_nh9_evidence_pack_checker.py`；九目录 | 不可变收口 | `NH9-T11` | checker EXIT0 |
| `NH9-11` | Readiness skeleton | **S / 非 DoD：** a) 在 manifest 或 `.experiment/new-harvest/readiness.schema.json` 放 matrix/run schema（**允许**存在，不是 T11 EXIT0）。b) preflight 字段允许存在。c) `launch_date`/`scores` 必须空/`null`。d) closure 文件 `in_closure_join=false` 且 PASS 列表不含 experiment/0815/vendor 分数。e) **不得**因缺 schema/分数使 T11 FAIL；也**不得**因有分数使 T11 PASS。f) **禁止** `::test_nh9_11_schema_exists_with_empty_dates_scores` 列入 T11 DoD 节点。 | schema（非 T11 EXIT0） | 骨架隔离 | 无独立 Test-ID | 空日期/分数；不进 join |

---

## 5. Phase 详情

### 5.1 Phase 1 — Closed-set generator

- **Phase 目标**：冻结战役闭集合同，使后续测试有唯一行空间。
- **本 Phase 对应编号**：`NH9-01`
- **本 Phase 新增文件**：`tests/fixtures/new_harvest/generate_closed_set_manifest.py`；更新/冻结 `tests/fixtures/new_harvest/closed_set_manifest.v1.json`；`tests/unit/test_nh9_closed_set_manifest.py`
- **本 Phase 修改文件**：无生产代码。消费 `strategies.py:15-26`、`registry.py:73-104`、`models.py:278-286`（只读）
- **本 Phase 删除文件**：无
- **具体功能预期**：
  1. `work_ids` 集合 == 上列 82 个 ID，顺序稳定。
  2. `strategies.length==10` 且 key 集合 == `CleanStrategyKey`。
  3. `operations.length==3` 且 (provider,operation) 集合 == chinatax/domain/realestate 三 op。
  4. 七意图全列出；仅 `intake.ingest` 按 kind 分叉；不存在 28 格全合法表。
  5. 每合法 knowledge 格有 `min_layer` ∈ {L1,L2,L3,L4} 且知识正格 `min_layer` 含 L3+L4。
  6. 负格 `query_expected_hits=0`。
  7. `digest` = canonical bytes SHA-256；二次生成相等。
  8. `experiment.in_closure_join===false`。
- **对应测试台账项**：`NH9-T01`
- **收口标准**：T01 EXIT0；manifest 路径即 final §9.1 固定路径
- **本 Phase 风险提醒**：手抄 82 或 7×4 = `FG-NH-15` 失败；丢掉 NH1 预埋路径 = NH1-T07 交接破坏

### 5.2 Phase 2 — Replay + fail-loud

- **Phase 目标**：身份法与失败零向量可在 Port 上回归。
- **本 Phase 对应编号**：`NH9-02` / `NH9-03`
- **本 Phase 新增 / 修改 / 删除文件**：修改 `tests/e2e/test_intake_identity_replay.py`（删 sqlite3）；新增 concurrent/conflict 与负向 query 节点（可落 `tests/e2e/test_new_harvest_closed_set.py` 或独立 `tests/e2e/test_nh9_task_identity_conflict.py`）
- **具体功能预期**：
  1. 同指纹 replay HTTP 200、同一 `task_uuid`、不新增 root Execution。
  2. 异指纹 409 `task-identity-conflict`，原行 fingerprint 不变。
  3. 双飞无双根。
  4. intake replay `latest_revision_uuid` 经 Port 可 JOIN 到 revision 行，COUNT=1。
  5. 空正文 / unknown key / bad member → 无向量行、search 0。
  6. 两测试文件源码无 `import sqlite3` / `sqlite3.connect`。
- **对应测试台账项**：`NH9-T02` / `NH9-T03`
- **收口标准**：race + negative query 四元组
- **本 Phase 风险提醒**：只测 inline 200 不测 409 = 台账仍缺（RA09 `D-09-10`）

### 5.3 Phase 3 — Crash windows

- **Phase 目标**：capstone I 的 CREATE/SEL/SEAL/PROCESS/FANIN/PUB/OUTBOX。
- **本 Phase 对应编号**：`NH9-04`
- **本 Phase 新增 / 修改 / 删除文件**：🆕 `tests/e2e/test_new_harvest_crash_windows.py`；🔱 不改 NH3/NH1/NH8 生产实现
- **具体功能预期**：
  1. 每窗至少 1 个具名 pytest node（见 §8 T04/T05）。
  2. crash 后经 PersistencePort 恢复，禁止 sqlite3。
  3. SEL 后仍 unsealed、零向量；SEAL 后 retry 不换 `process_key`。
  4. PROCESS 异 outcome 409；OUTBOX 重投不倍增向量。
  5. FANIN 一次父成功；PUB 切中无双 serving。
  6. 文档/断言禁止「exactly-once delivery」字样作为 PASS 理由。
- **对应测试台账项**：`NH9-T04` / `NH9-T05`
- **收口标准**：fault report 列出全部 W-NH-*（PROM-CAT/GC 可在 T06 交叉引用）
- **本 Phase 风险提醒**：把 NH3-T07 目录名 `e2e/` 标成 L3 = `FG-NH-13`；目录不升层

### 5.4 Phase 4 — Object race + scatter

- **Phase 目标**：对象字节与 scatter 终态在交错下仍服从产品法。
- **本 Phase 对应编号**：`NH9-05` / `NH9-06`
- **本 Phase 新增 / 修改 / 删除文件**：扩 NH4/scatter 测试节点或在 crash_windows/closed_set 增加排列；不改 `object_gc.py` 产品语义（若缺 pending 行为 = NH4 缺口）
- **具体功能预期**：
  1. 四类对象交错全覆盖。
  2. live pending 不可 tombstone；quarantine+newref restore；字节相等。
  3. exhausted_zero 无向量；child fail 父检索空。
  4. query 使用 namespace。
- **对应测试台账项**：`NH9-T06` / `NH9-T07` / `NH9-T05`
- **收口标准**：DB/proof/query 三方一致
- **本 Phase 风险提醒**：sibling `publication_ready` 当父成功 = `FG-NH-04`

### 5.5 Phase 5 — Compat + retrieval mega

- **Phase 目标**：交叉证明 Capstone A（主责 `NH2-T06`，辅 `NH3-T06`）与 C–H（主责 NH7/NH5/NH8）；本 AP 不改主功能。
- **本 Phase 对应编号**：`NH9-07` / `NH9-08`
- **本 Phase 新增 / 修改 / 删除文件**：🆕 `tests/e2e/test_new_harvest_closed_set.py`；🔱 NH2/NH3/NH5/NH7 节点
- **具体功能预期**：
  1. old pin 序列锁死；新 Task 非旧 selector。
  2. unknown digest 零 Process。
  3. legacy/unsealed/sealed SQL 可分；domain hex ≠ sealed actual。
  4. 每 knowledge 正格：HTTP 200、`disposition=ok`、hit、traceback resolved、facet 过滤。
  5. 无 monkeypatch 赋值 `_http_fetcher/_browser_fetcher/_clean_llm`（扫描 T09 文件，`FG-NH-01`）。
  6. 失败/非法格 0 hit。
- **对应测试台账项**：`NH9-T08` / `NH9-T09` / `NH9-T03`
- **收口标准**：mega report 按 manifest 逐格 PASS
- **本 Phase 风险提醒**：T09 跳 ingest 直插向量 = 本 AP NOT-成功；正格不通 = 交回 NH7

### 5.6 Phase 6 — Security + evidence + experiment

- **Phase 目标**：capstone J 与安全签收；实验隔离。
- **本 Phase 对应编号**：`NH9-09` / `NH9-10` / `NH9-11`
- **本 Phase 新增 / 修改 / 删除文件**：🔱 `tests/e2e/test_new_harvest_runtime_security.py`（NH6 已建；本 AP 可加不重叠汇总 node）；🆕 `tests/domain/test_nh9_evidence_pack_checker.py`；🆕 evidence 目录与 experiment schema
- **具体功能预期**：
  1. T10 含攻击向量，不只 happy-path。
  2. 九包文件齐、四元组齐、无过期 waiver。
  3. `FG-NH-01..17` 逐条机器可读 PASS。
  4. experiment 日期/分数空；T11 不因空分数 FAIL，也不把分数当 PASS。
  5. 无未解释 S1。
- **对应测试台账项**：`NH9-T10` / `NH9-T11`
- **收口标准**：security signoff + pack checker EXIT0
- **本 Phase 风险提醒**：import/which/models-list 当 ready = `FG-NH-11`；0815 jsonl 当 NH evidence = `FG-NH-16`

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Q26 / `T-O-406` | `pre-charter-qna.md` | 四层不可互换；waiver 只延期；T01/T11 锁层与 pack | 降层或改期待值 → 本 AP FAIL；reopen Q26 |
| `T-O-380` | `pre-initial-planning-qna.md` | `NH9-11` 不进 DoD / join | 把实验分数写入 T11 PASS → `FG-NH-16` |
| Q3 / `T-O-383` | 同上 | T02/T03/T04 fail-loud、replay、409 | 热切或空成功 → FAIL |
| Q1 / `T-O-376` / `T-O-381` | 同上 | T09 每正格 live-to-query；503 非 DoD | 正格不通交回 NH7 |
| `T-O-378` | 同上 | T03 空/猴补丁/盗码 | 修期待值掩盖 = `FG-NH-17` |
| Q10 / `T-O-390` | `pre-charter-qna.md` | T08 legacy alias 不当 actual | backfill actual → 交回 NH3 |
| Q17 / `T-O-397` | 同上 | T07 exhausted_zero | 写成 succeeded+向量 → FAIL |
| Q18 / `T-O-398` | 同上 | T08 old pin；禁 Temporal 引擎 | 退回 13 profile → `FG-NH-09` |
| Q19 / `T-O-399` | 同上 | T10 隔离/禁 no-sandbox | 交回 NH6 |
| Q20 / `T-O-400` | 同上 | T04 SEL/SEAL 同 UoW | 两提交 → 交回 NH3 |
| Q21 / `T-O-401` | 同上 | T08 upgrade 入口=0；exact copy | existing upgrade → OOS |
| Q24 / `T-O-404` | 同上 | T06 pending 同 UoW / GC | 交回 NH4 |
| Q9 / `T-O-389` | `pre-initial-planning-qna.md` | T09 facet 五维 | stub 五维 → 交回 NH5 |
| Q27 / `T-O-407` | `pre-charter-qna.md` | T09 lifecycle 排除依赖 NH8 exact-clean | T08-B 仍红 → 交回 NH8 |
| `G-NH-18` CLOSED | `pre-charter-qna.md` §8 | 本 AP 不新开 owner-gate | 禁止在本文填 Q/A |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表（本计划工作要落在哪些既有代码 / 新建点上）

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| `NH9-A01` | `src/runtime/task/task_create.py:67-140` | 先解析 fingerprint；exact replay 原视图；异指纹 `task-identity-conflict`；IntegrityError 回收并发 | `NH9-02` 扩新路径负测 | `✅ 复用` | 独立核对：`:67-85` 第一事务 replay；`:89-104` 第二事务 recheck；`:130-141` unique 冲突 → 409 或 replay。conflict 测试今日缺 |
| `NH9-A02` | `src/runtime/workflow/runtime_outcome.py:46-182` | Outcome digest 校验；terminal 同 digest 幂等；异 digest 409；成功须 output+proof；`rowcount!=1` → `stale-process-fence`；retry_wait 分支 | `NH9-04` PROCESS 窗 | `✅ 复用` | 独立核对至 `:182` enqueue retry。actual 新接属 NH3，本 AP 只注入 |
| `NH9-A03` | `src/runtime/workflow/runtime_scatter.py:277-483` | `_maybe_converge_scatter_root_tx`：`:293-311` Snapshot/ChangeSet 分母；`:320-346` zero-member 补 terminal；malformed fail-integrity；required child fail/cancel；`:430-474` publication proof 恰好一条 | `NH9-06` / T05 FANIN | `♻️ Port/query` | sqlite 反例在 scatter e2e `:327`；NH1-T02 必须先 Port 化；join 入口 zero SUCCESS 仍是 `:76-98` |
| `NH9-A04` | `src/services/retrieval/retrieval_rank.py:38-76,339-433` | 初扫 WHERE：namespace + indexed + active pointer + complete proof + serving revision；`_revalidate_publication_fence` 按提交坐标再查一遍 | `NH9-08` mega | `✅ 复用` | facets 来自 NH5；本 AP 禁止 post-filter |
| `NH9-A05` | `tests/e2e/test_source_capability_paths.py:99-101,166-168` | `:99-101` 赋值 `_http_fetcher`/`_browser_fetcher`；`:58-68` 8s 窗；`:166-168` 断言 `succeeded`（RA09 复跑 `local=running`） | ⛔ 反例；T09/T10 禁止复制 | `🆕 L3` 只允许真实 default-root | **不修期待值**把 `running` 写成 PASS |
| `NH9-A06` | legacy catch/empty/R2 finalizer（RA09 §8.1：dedicated `processor.ts` catch skip；`cleaner_web.ts` `plainTextAvailable:true`；`finalizer.ts` 凭 R2 key 成功） | silent success | `NH9-03` 负格 | `🆕 negative grids` | **零 runtime 回流**；只借失败法 |
| `NH9-A07` | RA09 Temporal Safe Deployments / Kafka delivery-semantics / TigerBeetle DST | replay/EOS/fault 限度 | 失败法参考：pin+旧史、闭集效果一次、黑盒测不到协议不变量 | `🔶 参考` | **不引外部引擎**；本仓 CAS/fixtures |
| `NH9-N01` | 🆕 `tests/fixtures/new_harvest/generate_closed_set_manifest.py` + `closed_set_manifest.v1.json` | 闭集生成器 / 冻结 fixture | `NH9-01` | `🆕 净新` | 路径 final §9.1 已锁 |
| `NH9-N02` | 🆕 `tests/unit/test_nh9_closed_set_manifest.py` | T01 | `NH9-01` | `🆕` | |
| `NH9-N03` | 🆕 `tests/e2e/test_new_harvest_crash_windows.py` | T04/T05 | `NH9-04` | `🆕` | 固定路径 |
| `NH9-N04` | 🆕 `tests/e2e/test_new_harvest_closed_set.py` | T03/T09 | `NH9-03/08` | `🆕` | 固定路径 |
| `NH9-N05` | 🔱 `tests/e2e/test_new_harvest_runtime_security.py`（NH6 先建） | T10 | `NH9-09` | `🔱` | 固定路径；禁止再 🆕 同名产品 node |
| `NH9-N06` | 🆕 `tests/domain/test_nh9_evidence_pack_checker.py` | T11 | `NH9-10` | `🆕` | `NH9-11` 不进 T11 EXIT0 |
| `NH9-N07` | `tests/e2e/test_intake_identity_replay.py:15,71-125` | NS9-FX2；今日 sqlite3 直读 | `NH9-02` Port 化 | `♻️ 重 substrate` | 独立核对 `:100-124` 三查询 |
| `NH9-N08` | `src/persistence/ports.py:10-27` | `UnitOfWork`/`PersistencePort` | T02/T04/T05/T06 唯一 DB 缝 | `✅ 复用` | 已建好，别绕过 |
| `NH9-N09` | `src/runtime/workflow/runtime_outbox.py:131-139` | vectorize consumer 无业务副作用 | `W-NH-OUTBOX` | `✅ 复用` | |
| `NH9-N10` | `src/services/object_gc.py:189-240` | 无抢先 tombstone；TX2 见 live-ref | `W-NH-GC-INGEST` | `✅ 复用` | 🔱 NH4 |
| `NH9-N11` | `src/services/index_retirement.py:1-10` | 切后 grace，再核活指针 | `W-NH-PUB` | `✅ 复用` | 🔱 NH8 |
| `NH9-N12` | `src/services/retrieval/retrieval_request.py:265-270` | 缺 namespace → 422 `RETRIEVE_SCHEMA_NAMESPACE_REQUIRED` | T03/T09 负例 | `✅ 复用` | `FG-NH-05` |
| `NH9-N13` | `intake/web/__init__.py:28-29` | `CLEAN_EMPTY` | T03 | `✅ 复用` | `tests/` 今日 0 命中 |

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | e2e 成功路径 `pipeline._browser_fetcher = lambda`（`test_source_capability_paths.py:99-101`） | `T-O-378`；`FG-NH-01`；`NH9-A05` |
| ⛔2 | source e2e 8s 窗 `running` 当进度或改期待值为非 `succeeded` 仍 PASS（`:58-68,166-168`） | RA09 复跑失败；`FG-NH-17` |
| ⛔3 | `sqlite3.connect` 打开 Turso/sqlite 文件当 recovery/replay 绿（scatter `:7,327,366`；identity `:100`） | `FG-NH-12`；README K1 |
| ⛔4 | domain digest / 任意 64-hex 冒充 sealed actual（`task_create.py:179-180`） | `T-O-390`；`FG-NH-08`；功能属 NH3，本 AP 只负测 |
| ⛔5 | Task `succeeded` / `publication_ready` 当可检索（scatter `:496-499`） | `FG-NH-03/04`；`R-F14` |
| ⛔6 | 无 `namespace_key` 的 search 200 | `retrieval_request.py:265-270` 会 422；`FG-NH-05` |
| ⛔7 | 跳过 ingest 直接 INSERT 向量后 POST search | 本 PROMPT T09 硬禁；`T-O-376` |
| ⛔8 | L1/unit/fixture 顶 L3/L4 | `T-O-406`；`R-F13`；`FG-NH-13` |
| ⛔9 | 503 / 诚实未部署当 in-scope 正格 DoD | `T-O-376`；`FG-NH-02` |
| ⛔10 | `.experiment` / 0815-R7 / live vendor 分数进 closure | `T-O-380`；`FG-NH-16` |
| ⛔11 | waiver 改期待值或覆盖 `T-O-376/378/381/383` | `T-O-406`；`FG-NH-17` |
| ⛔12 | 口头 exactly-once delivery / 引入 Kafka 事务或 Temporal Worker Versioning | RA09 `RA-09-WEB-04/05`；`NH9-A07` |
| ⛔13 | dedicated catch skip / `plainTextAvailable:true` / R2 key 即成功 | `NH9-A06`；禁止回流 |
| ⛔14 | 本 AP 第一次补 parser/lane/guard/upload 内核 | `R-F15`；final §7.9 NOT-成功 |
| ⛔15 | 7 intents × 4 kinds 全绿表 | `FG-NH-15` |
| ⛔16 | 只测 API 代表四通道 | `FG-NH-14` |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：[`assessment-analysis-09-assurance-replay-concurrency-and-compatibility.md`](../../eval/new-harvest/reference-anchor/assessment-analysis-09-assurance-replay-concurrency-and-compatibility.md) —— §7.1 是与本 AP 相关子集；完整借鉴台账见 RA09 §3。邻面功能 S1 只消费 `NH-RA0X-B*`，不重开设计。
- **安全 / 信任边界类工作项的威胁模型锚**（不得留空；对应 `NH9-02/04/05/09`）：
  - **T-NH9-S1 身份双花**：并发 create last-writer-wins 或双 root Execution/object ref → 缓解：`task_create.py:67-140` CAS + T02 double-flight。
  - **T-NH9-S2 崩溃热切**：SEL 后重选工人、SEAL 两提交、PROCESS 异 outcome 覆盖 → `T-O-383/400`；T04 🔱 NH3-T07。
  - **T-NH9-S3 检索越权/假命中**：无 namespace、过期 generation、已 deactivate Item、不完整 proof → `retrieval_rank.py` dual fence + T09 负格。
  - **T-NH9-S4 对象 TOCTOU**：GC 删 live pending / 半写当成功 → `object_gc.py:189-240` + T06；`T-O-404`。
  - **T-NH9-S5 运行时逃逸**：恶意 PDF 杀进程、SSRF、root/`--no-sandbox` → T10 🔱 NH6-T02/T05；`T-O-399`。
  - **T-NH9-S6 证明伪造**：sqlite3 直读、monkeypatch、INSERT 向量、改期待值、实验分数 → `FG-NH-01/12/16/17`；T02/T09/T11。

---

## 8. 测试台账

> 测试细节只在此写一次。PASS 证据四元组形态：`commit SHA + pytest node PASS + Truth/Q + UTC`（执行期填写，本 AP 不伪造 SHA）。

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| `NH9-T01` | manifest 覆盖 82 works / 10+3 / 七意图 / 层 | 短途 / 契约 | L1 | 🆕 `tests/unit/test_nh9_closed_set_manifest.py` | `NH9-01` → closed-set coverage | `SHA + manifest EXIT0 + Q26 + UTC` |
| `NH9-T02` | Task/intake replay/conflict/concurrent | soak / race | L2/L3 | 🔱 `test_intake_identity_replay.py` + 🆕 concurrent；**Port 化**。staging e2e **⛔** | `NH9-02` → replay/fault | `SHA + parallel PASS + T-O-383 + UTC` |
| `NH9-T03` | empty/bad/unknown 零向量 | spike / fault | L1/L3/L4 | 🆕/♻️ `test_new_harvest_closed_set.py` 负格 + handler | `NH9-03` → product closure 负向 | `SHA + negative query PASS + Q3 + UTC` |
| `NH9-T04` | CREATE/SEL/SEAL/PROCESS windows | mega / fault | L2/F | 🆕 `test_new_harvest_crash_windows.py`；🔱 NH3-T07 | `NH9-04` → replay/fault | `SHA + window suite PASS + Q20 + UTC` |
| `NH9-T05` | FANIN/PUB/OUTBOX windows | mega / fault | L2/L4/F | 同文件；🔱 NH1-T02 / NH8 / outbox | `NH9-04/06` → repair/proof | `SHA + repair/proof PASS + Q26 + UTC` |
| `NH9-T06` | upload/GC interleavings | soak / race | L2/L3/R | 🔱 NH4-T05/T06 全排列 | `NH9-05` → object/scatter | `SHA + interleavings PASS + Q24 + UTC` |
| `NH9-T07` | zero/member/child failure | mega | L3/L4 | 🔱 NH7-T09 + 🆕 closed_set query。HEAD scatter 未清 sqlite3/`publication_ready`/handler 赋值前 **⛔** | `NH9-06` → object/scatter | `SHA + result/query PASS + Q17 + UTC` |
| `NH9-T08` | old pin/new graph/legacy alias | spike / compat | L2/C | 🔱 NH2-T06 + NH3-T06 | `NH9-07` → compat | `SHA + sequence PASS + Q10/Q18 + UTC` |
| `NH9-T09` | every live lane retrieval/facet | mega | L4 | 🆕 `test_new_harvest_closed_set.py`；🔱 NH7 正格 | `NH9-08` → product closure | `SHA + manifest query PASS + Q26 + UTC` |
| `NH9-T10` | security/readiness/backpressure | soak / security | L2/L3/S | 🔱 NH6 已建 security/isolation/readiness node（不 🆕 同产品断言） | `NH9-09` → security closure | `SHA + security pack PASS + Q19 + UTC` |
| `NH9-T11` | evidence pack completeness | 短途 / contract | L1 | 🆕 `tests/domain/test_nh9_evidence_pack_checker.py` | **仅** `NH9-10` → evidence immutability。`NH9-11` **无** Test-ID | `SHA + pack checker EXIT0 + T-O-406 + UTC` |

无 `NH9-T12`。`NH9-11` 不单列 Test-ID，**不得**把 schema 存在性做成 T11 pytest node。

### Capstone A–J → Test-ID（不得悬空）

每步有且仅有一个功能主 AP；NH9 只交叉证明。`NH8-T09` 属 H/compat 尾，不是 A 主功能。

| 步 | 主 AP / 主 Test-ID | NH9 交叉 Test-ID | 🔱 |
|---|---|---|---|
| A | NH2 `NH2-T06`（辅 `NH3-T06`） | `NH9-T08` | `NH2-T06` / `NH3-T06` |
| B | NH4 `NH4-T01`/`NH4-T03` | `NH9-T06` | `NH4-T01`/`T03`/`T05`/`T06` |
| C | NH7 `NH7-T03`/`NH7-T04` | `NH9-T09` | `NH7-T03`/`T04` |
| D | NH7 `NH7-T05`/`NH7-T06` | `NH9-T09` | `NH7-T05`/`T06` |
| E | NH7 `NH7-T07` | `NH9-T09` | `NH7-T07` |
| F | NH7 `NH7-T08`/`NH7-T09` | `NH9-T07` + `NH9-T09` | `NH7-T08`/`T09` |
| G | NH5 `NH5-T07` | `NH9-T09` | `NH5-T07` |
| H | NH8 `NH8-T02`..`NH8-T08` | `NH9-T09` | `NH8-T02`..`T08`（exact-clean 关闭点=`NH8-T03`） |
| I | NH9 `NH9-T02`/`T04`/`T05`/`T06` | —（本 AP 主责） | NH3-T07 / NH1-T02 / NH4-T05/T06 |
| J | NH9 `NH9-T01`/`NH9-T11` | —（本 AP 主责） | pack / FG node |

### 8.1.1 各 Test-ID 细则

#### `NH9-T01`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🆕 `tests/unit/test_nh9_closed_set_manifest.py::test_manifest_digest_stable`；`::test_work_ids_are_exact_82`；`::test_strategies_ops_intents_match_registries`；`::test_illegal_cells_not_cartesian_28`；`::test_layers_l1_l4_recorded`；`::test_experiment_fields_empty_and_not_in_join` |
| 用途 | 证明 `NH9-01`；Q26；`FG-NH-13/15/16` |
| 前置 | 纯 import registries + 读 fixture；可调用生成器后比较字节 |
| 步骤 | a) 加载 `tests/fixtures/new_harvest/closed_set_manifest.v1.json`。b) 断言 `work_ids` 集合等于 §3 的 82 ID。c) 断言 10 strategy / 3 op / 7 intent。d) 非法格有 disposition；无 28 全合法。e) 每正格 `min_layer`。f) 重算 canonical digest。g) experiment 空且 `in_closure_join is false`。h) 生成器只 append 82/windows/FG，**不得**改 NH1-T07 预埋字段 `strategy_cells` / `op_cells` / `intent_illegal` 与其 canonical `digest` 字节。 |
| 断言细节 | `len(work_ids)==82` **且** `set(work_ids)==FROZEN_82`；顶层 digest 匹配文件字段；`strategy_cells`/`op_cells`/`intent_illegal`/`digest` 与 NH1-T07 预埋逐字相容（不得删路径、不得改 10+3 canonical 字节） |
| 负例 | 手改期待值为 81/83；7×4 表；experiment 填假日期当 PASS |
| 跑法 | `uv run pytest tests/unit/test_nh9_closed_set_manifest.py -q` |
| 层与来源 | L1 契约；`🆕` |

#### `NH9-T02`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🔱 `tests/e2e/test_intake_identity_replay.py::test_identity_replay_reuses_revision_and_keeps_pointer_resolved`（**整文件 Port 化**）；🆕 `::test_identity_replay_queries_via_persistence_port`（若拆分）；🆕 `tests/e2e/test_nh9_task_identity_conflict.py::test_same_fingerprint_replays_original_view`；`::test_different_fingerprint_409_task_identity_conflict`；`::test_concurrent_double_flight_single_root`。**不**把 `tests/e2e/test_inline_ingress_staging.py` 列入测试位置 |
| 用途 | 证明 `NH9-02`；`T-O-383`；`FG-NH-12`；RA09 `NH-A-09-01..03` |
| 前置 | `create_app()`；真实 PersistencePort；auth Bearer；**禁止** `sqlite3.connect`；Turso 设置下必须走 Port |
| 步骤 | a) 同 payload 二次 Task POST。b) 同 UUID 改 payload。c) asyncio/线程双飞同 identity。d) 同 external_key 同内容二次 ingest。e) ast 扫描本 Test-ID 文件无 `import sqlite3`。 |
| 断言细节 | a) 200 + 同一 task 视图 + root Execution COUNT=1。b) 409 `task-identity-conflict`，原 fingerprint 不变。c) 成功∪replay∪409，无双 INSERT 成功。d) Port：`latest_revision_uuid` 存在且 revision COUNT=1。e) 源码无 sqlite3 |
| 负例 | 仍用 `:100-124` sqlite3 三查询当 PASS；把 409 改成 200 期待值；用 staging e2e 的 sqlite3 直读当 T02；未 Port 化的 identity 整文件列入跑法 |
| 跑法 | `uv run pytest tests/e2e/test_nh9_task_identity_conflict.py::test_same_fingerprint_replays_original_view tests/e2e/test_nh9_task_identity_conflict.py::test_different_fingerprint_409_task_identity_conflict tests/e2e/test_nh9_task_identity_conflict.py::test_concurrent_double_flight_single_root -q`。**仅当** `test_intake_identity_replay.py` 已删除 `import sqlite3`/`sqlite3.connect` 才追加该文件具名 Port 化 node。未 Port 化前 ⛔ 不得列入跑法 |
| 层与来源 | L2/L3；`🔱` + `🆕`；race 标签。L3 节点必须 `create_app()` 且无 monkeypatch。HEAD identity 文件未清 sqlite3 前 ⛔ |

#### `NH9-T03`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_new_harvest_closed_set.py::test_empty_html_clean_empty_zero_hits`；`::test_empty_pdf_text_zero_hits`；`::test_unknown_filter_key_422_zero_hits`；`::test_bad_api_member_zero_hits`；`::test_missing_supply_typed_fail_not_live_dod`；♻️ handler unit 可伴生但**不得顶** L4 零命中 |
| 用途 | 证明 `NH9-03`；`T-O-378/383`；`FG-NH-02/06` |
| 前置 | default-root；namespaced search；失败路径允许无供给；**禁止** 503 当正格 DoD |
| 步骤 | a) 提交空 HTML/空文本 PDF。b) 断言 CLEAN_EMPTY 或 clean_candidate_empty / Task failed。c) Port 计 `mkb_vector_records` 增量=0。d) search 带 namespace → results 空。e) unknown filter key 422。f) missing OCR/browser：typed 码，**单独标负例**，不得写入 10+3 正格 PASS。 |
| 断言细节 | HTTP 非 200 成功知识；search `disposition=ok` 且 `results==[]` 或 4xx；无空 `clean_text` succeeded |
| 负例 | 空串当 succeeded；decode 盗 OCR 码但仍出向量；缺供给 503 写入 T09 正格 |
| 跑法 | `uv run pytest tests/e2e/test_new_harvest_closed_set.py::test_empty_html_clean_empty_zero_hits tests/e2e/test_new_harvest_closed_set.py::test_empty_pdf_text_zero_hits tests/e2e/test_new_harvest_closed_set.py::test_unknown_filter_key_422_zero_hits tests/e2e/test_new_harvest_closed_set.py::test_bad_api_member_zero_hits tests/e2e/test_new_harvest_closed_set.py::test_missing_supply_typed_fail_not_live_dod -q` |
| 层与来源 | L1/L3/L4；`🆕/♻️`；fault 标签 |

#### `NH9-T04`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_new_harvest_crash_windows.py::test_w_nh_create_between_identity_and_insert`；`::test_w_nh_process_outcome_cas_effect_once`；`::test_w_nh_process_different_outcome_conflict`。🔱 必须列入跑法：`tests/e2e/test_nh3_seal_crash_windows.py::test_w_sel_crash_before_seal_leaves_unsealed`；`::test_w_seal_route_and_actual_same_uow`；`::test_mid_uow_crash_no_half_seal`；`::test_different_digest_conflict_error`（NH3-T07；**层 L2/F，目录不升 L3**） |
| 用途 | 证明 `NH9-04` a/c；Q20；`T-O-400/383` |
| 前置 | 真实 UoW；可注入的事务钩子；facts 已先行（SEL/SEAL）；禁止 sqlite3；禁止 `create_app` 冒充把 T04 标 L3 |
| 步骤 | a) CREATE：identity 命中后、INSERT 前 raise，再 replay。b) 跑 NH3-T07 SEL/SEAL 四节点。c) PROCESS：成功 CAS；重复同 digest；异 digest 409；rowcount  fence。 |
| 断言细节 | 单 root；SEL 后 `actual_binding_state!='sealed'` 且向量 0；SEAL 三条件同 commit；PROCESS `stale-process-outcome` / `stale-process-fence` |
| 负例 | route 与 seal 两提交仍绿；口头「应该 exactly-once」无断言 |
| 跑法 | `uv run pytest tests/e2e/test_new_harvest_crash_windows.py::test_w_nh_create_between_identity_and_insert tests/e2e/test_new_harvest_crash_windows.py::test_w_nh_process_outcome_cas_effect_once tests/e2e/test_new_harvest_crash_windows.py::test_w_nh_process_different_outcome_conflict tests/e2e/test_nh3_seal_crash_windows.py -q` |
| 层与来源 | L2/F；`🆕` + `🔱` NH3-T07 |

#### `NH9-T05`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_new_harvest_crash_windows.py::test_w_nh_fanin_parent_waiting_repairs_once`；`::test_w_nh_pub_incomplete_proof_not_visible`；`::test_w_nh_outbox_redelivery_no_extra_vector_upsert`。🔱 列入跑法：`tests/e2e/test_nh1_fanin_recovery_port.py::test_fanin_crash_repairs_via_persistence_port`（NH1-T02；源码无 sqlite3）。PUB 🔱 NH8-T07 或本文件包装：切 generation 中杀进程后 dual fence 只见完整 proof |
| 用途 | 证明 `NH9-04/06` FANIN/PUB/OUTBOX；Q26；`FG-NH-12/04` |
| 前置 | Port-ized scatter；NH1-T02 PASS 是硬前置；outbox 可重复 enqueue |
| 步骤 | a) 子 terminal、父 waiting，Port 唤醒 repair。b) 断言父 succeeded、`proof_ref` 非空、无第二 root。c) 发表切中注入：不完整 proof 的 search 0。d) outbox ACK 两次，向量 COUNT 不 +2。e) child fail 场景 query 父空（可与 T07 共享）。 |
| 断言细节 | 无 `disk I/O error`；无 sqlite3 import；serving 不双切；consumer 无副作用 |
| 负例 | 复制 scatter `:327` sqlite3 注入；sibling publication_ready 当父可检索 |
| 跑法 | `uv run pytest tests/e2e/test_new_harvest_crash_windows.py::test_w_nh_fanin_parent_waiting_repairs_once tests/e2e/test_new_harvest_crash_windows.py::test_w_nh_pub_incomplete_proof_not_visible tests/e2e/test_new_harvest_crash_windows.py::test_w_nh_outbox_redelivery_no_extra_vector_upsert tests/e2e/test_nh1_fanin_recovery_port.py::test_fanin_crash_repairs_via_persistence_port -q` |
| 层与来源 | L2/L4/F；`🆕` + `🔱` e2e |

#### `NH9-T06`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🔱 `tests/unit/test_ns6_gc_toctou.py::test_gc_restore_when_live_reference_arrives_during_quarantine`；`::test_gc_restore_when_upload_pending_arrives_during_quarantine`；`::test_collect_candidates_skips_live_upload_pending`（NH4-T05）。🔱 `tests/unit/test_nh4_upload_ttl_gc.py`（NH4-T06）。🆕 同战役或 `tests/e2e/test_nh4_upload_replay_race.py` 扩：`test_interleave_parallel_upload_and_gc`；`test_interleave_ttl_and_ingest`；`test_tombstone_then_reupload_new_handle_zero_item`；`test_w_nh_prom_cat_crash_no_usable_handle` |
| 用途 | 证明 `NH9-05`；Q24；`W-NH-PROM-CAT`/`W-NH-GC-INGEST`；`R-F07` |
| 前置 | NH4 台账 C PASS（功能已在）；fake clock 允许；HTTP 交错用 create_app |
| 步骤 | a) 回归 NH4-T05/T06。b) 全排列：parallel upload；pending 存活；TTL∥ingest；quarantine∥newref；tombstone∥reupload。c) PROM-CAT：promote 成功 catalog 前 crash → 无 handle、无 Item、staging 可清。 |
| 断言细节 | live pending 不可删；restore 字节相等；upload 后 Item COUNT 增量=0；tombstone 后再传不复活旧 Item |
| 负例 | grace=0；internal `promote()` 冒充 public（`FG-NH-10`） |
| 跑法 | `uv run pytest tests/unit/test_ns6_gc_toctou.py::test_gc_restore_when_live_reference_arrives_during_quarantine tests/unit/test_ns6_gc_toctou.py::test_gc_restore_when_upload_pending_arrives_during_quarantine tests/unit/test_ns6_gc_toctou.py::test_collect_candidates_skips_live_upload_pending tests/unit/test_nh4_upload_ttl_gc.py::test_ttl_without_ingest_releases_then_grace_tombstone tests/unit/test_nh4_upload_ttl_gc.py::test_staging_incomplete_never_catalogued_is_reaped tests/e2e/test_nh4_upload_replay_race.py::test_interleave_parallel_upload_and_gc tests/e2e/test_nh4_upload_replay_race.py::test_interleave_ttl_and_ingest tests/e2e/test_nh4_upload_replay_race.py::test_tombstone_then_reupload_new_handle_zero_item tests/e2e/test_new_harvest_crash_windows.py::test_w_nh_prom_cat_crash_no_usable_handle -q` |
| 层与来源 | L2/L3/R；`🔱` NH4；soak 标签（deterministic 排列 ×N） |

#### `NH9-T07`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🔱 NH7-T09 冻结 node（PASS 必须列入跑法）：`tests/e2e/test_nh7_exhausted_zero.py::test_disposition_exhausted_zero_not_indexed_success`；`::test_exhaustion_proof_retrieval_empty`；`::test_same_fingerprint_replay_same_disposition`；`::test_noop_terminal_alone_is_not_product_zero`。🆕 **本 AP 唯一 PASS 主文件** query 节点：`tests/e2e/test_new_harvest_closed_set.py::test_exhausted_zero_namespace_search_empty`；`::test_required_child_failed_parent_not_retrievable`；`::test_bad_member_root_not_succeeded_zero_hits`。HEAD `test_registered_api_scatter.py::test_registered_api_scatter_auto_zero_and_fanin_recovery` / `::test_registered_api_scatter_collects_child_failure_before_parent_terminal` 未同时满足 (1) 无 sqlite3 (2) 无 handler 赋值当成功证明 (3) auto-zero 以 disposition+namespaced empty 为准 (4) child-fail 父 namespaced search 0 之前 = **⛔ 不得列入测试位置或跑法** |
| 用途 | 证明 `NH9-06`；Q17；`FG-NH-01/03/04/12` |
| 前置 | NH7-T09 功能已在；search 带 namespace。HEAD scatter 未达上列四条件时不得当 T07 PASS |
| 步骤 | a) 合法零集合 → exhausted_zero proof、无 child/vector。b) bad member 拒。c) 一 child fail，父 failed 码稳定。d) 对 a/c namespaced search。 |
| 断言细节 | zero：Task 可 complete 但 **非** indexed success；search 0。child fail：error `scatter-required-child-failed`；父 query 0，即使 sibling publication_ready。bad member：root 非 succeeded |
| 负例 | counts 全 0 的 succeeded 当知识成功；只 assert sibling outcomes；`publication_ready` 当 query；sqlite3 直读；测试替换 `workflow_worker.handler` 当绿 |
| 跑法 | `uv run pytest tests/e2e/test_nh7_exhausted_zero.py::test_disposition_exhausted_zero_not_indexed_success tests/e2e/test_nh7_exhausted_zero.py::test_exhaustion_proof_retrieval_empty tests/e2e/test_nh7_exhausted_zero.py::test_same_fingerprint_replay_same_disposition tests/e2e/test_nh7_exhausted_zero.py::test_noop_terminal_alone_is_not_product_zero tests/e2e/test_new_harvest_closed_set.py::test_exhausted_zero_namespace_search_empty tests/e2e/test_new_harvest_closed_set.py::test_required_child_failed_parent_not_retrievable tests/e2e/test_new_harvest_closed_set.py::test_bad_member_root_not_succeeded_zero_hits -q` |
| 层与来源 | L3/L4 mega；`🆕` query + `🔱` NH7-T09；HEAD scatter 未清 = ⛔ |

#### `NH9-T08`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🔱 `tests/unit/test_workflow_revision_compatibility.py::test_v2_runtime_materializes_and_completes_unstarted_v1_execution`；`::test_unknown_historical_compiled_plan_fails_before_process_materialization`；`::test_old_pin_sequence_unchanged_after_kind_family_activation`；`::test_new_task_does_not_resolve_old_selector_key`（NH2-T06）。🔱 NH3-T06：`tests/integration/test_nh3_s05_migration.py::test_legacy_unsealed_sealed_sql_distinguishable`；`::test_migration_does_not_copy_domain_into_actual`；`tests/domain/test_nh3_actual_readers_scan.py::test_architecture_scan_zero_actual_readers_of_legacy_column` |
| 用途 | 证明 `NH9-07`；Q10/Q18；`T-O-390/398/401`；`FG-NH-08/09` |
| 前置 | kind 图已激活（NH2）；actual 列已 migration（NH3）；真实 UoW |
| 步骤 | a) 复跑 old pin 序列。b) 新 Task kind-only。c) 未知 digest 零 Process。d) SQL 三类 binding；domain hex 查询不得 sealed。e) 扫描无 upgrade intent。 |
| 断言细节 | process_key 序列与 seed 一致；新 identity ∈ kind 闭集；`mkb_processes` 在 unknown digest 后 COUNT=0；`actual_binding_state='legacy_unverifiable'` 对旧列 |
| 负例 | 只测「还能 register 旧定义」；legacy alias 当 actual；跑 Temporal |
| 跑法 | `uv run pytest tests/unit/test_workflow_revision_compatibility.py tests/integration/test_nh3_s05_migration.py tests/domain/test_nh3_actual_readers_scan.py::test_architecture_scan_zero_actual_readers_of_legacy_column -q` |
| 层与来源 | L2/C；`🔱` compat |

#### `NH9-T09`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_new_harvest_closed_set.py::test_every_legal_knowledge_cell_namespace_facet_proof`（参数化 manifest 正格）。🔱 **不重写** NH7-T03..T08 lane 实现，只 join 其 PASS 并按格查询。facet SQL 回归 🔱 `tests/e2e/test_nh5_facet_retrieval.py` / `tests/unit/test_nh5_facet_sql_not_postfilter.py`（NH5-T07） |
| 用途 | 证明 `NH9-08`；Q26；`T-O-376/389`；`FG-NH-01/03/04/05/06/07/14` |
| 前置 | NH7-T01..T10 与 NH5-T07 全 PASS；default-root 真实 supply（NH6）；Layer-A namespace 由 Port 读出；**禁止** monkeypatch fetcher/LLM；**禁止** 直接 INSERT 向量 |
| 步骤 | a) 读 manifest 正格。b) 每格走该格已规定的 ingest（🔱 NH7 文件/夹具，不新写 worker）。c) 断言 admitted clean 非空。d) 等 publication proof/pointer/serving。e) POST search：`namespace_key` + facet。f) 断言 hit/content/traceback/facet。g) 对照格排除。h) stale/deactivate/delete 格 0 hit。i) ast 扫描本文件无 `_browser_fetcher =` 赋值。 |
| 断言细节 | HTTP 200 `disposition=ok`；results 含期望 item；traceback resolved；facet 键来自 S04 非 stub；失败格 0。任一正格不能 query → **本 Test-ID FAIL** 且 §8.4 点名 NH7，不得在本文件补 strategy |
| 负例 | 跳 ingest INSERT `mkb_vector_records`；Task succeeded 当 PASS；无 namespace 200；只测 API 三 op 宣称四通道 |
| 跑法 | `uv run pytest tests/e2e/test_new_harvest_closed_set.py::test_every_legal_knowledge_cell_namespace_facet_proof tests/e2e/test_nh5_facet_retrieval.py tests/unit/test_nh5_facet_sql_not_postfilter.py -q`（另依赖 NH7-T03..T08 已绿，不在本命令重写 lane） |
| 层与来源 | L4 mega；`🆕` + `🔱` NH7/NH5；**不可降层** |

#### `NH9-T10`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🔱 **主责=NH6** 已建 node（本 AP **不** 🆕 同产品断言）：`tests/e2e/test_nh6_parser_isolation.py::test_parser_subprocess_has_no_network`；`::test_resource_kill_on_timeout`；`::test_malicious_pdf_does_not_kill_api`；`tests/e2e/test_new_harvest_runtime_security.py::test_browser_runs_non_root`；`::test_production_forbids_no_sandbox`；`::test_browser_egress_rechecks_each_redirect`；`::test_parser_process_network_denied`；`::test_backpressure_zero_downstream`（**不得**用 NH6 unit 单独关闭 backpressure 门）；`tests/e2e/test_nh6_readiness.py::test_positive_probe_matches_presence`；`::test_missing_binary_component_not_overall_green`；`::test_models_list_insufficient_for_ready`；`::test_create_app_readiness_without_patch`。可选不重叠战役汇总：`::test_campaign_security_signoff_aggregates_nh6_gates`（只核 NH6 node 已列入 `tests.txt`，不复制 parser/egress 实现）。禁止 🆕 `test_malicious_pdf_does_not_kill_api` / `test_parser_has_no_network` 等同名产品 node |
| 用途 | 证明 `NH9-09`；Q19；`T-O-399`；`FG-NH-11`；§7.3 T-NH9-S5 |
| 前置 | NH6-T01..T10 PASS；生产配置禁 `--no-sandbox`；正负 probe fixture |
| 步骤 | a) 复跑 NH6-T02/T05/T08/T09 **具名** node。b) 可选战役汇总只索引这些 node。c) 扫描本 AP 新增测试无 `which chromium` / `import pypdf` / models-list 当 PASS。d) waiver 文件若存在则检查到期与 Truth 围栏。 |
| 断言细节 | API 在恶意样本后仍 2xx/typed 4xx；无网；非 root；零 `--no-sandbox` 生产旗；满载 metrics 下游调用=0（以 security L2 node 为准）；readiness 与实弹 probe 一致 |
| 负例 | import/which/models-list 当 ready；Protocol fake；cloud OCR；浮动 `latest`；测试后赋 port（NH6 NOT-成功，交回）；用 `tests/unit/test_nh6_backpressure_zero_calls.py` 单独关 T10 |
| 跑法 | `uv run pytest tests/e2e/test_nh6_parser_isolation.py::test_parser_subprocess_has_no_network tests/e2e/test_nh6_parser_isolation.py::test_resource_kill_on_timeout tests/e2e/test_nh6_parser_isolation.py::test_malicious_pdf_does_not_kill_api tests/e2e/test_new_harvest_runtime_security.py::test_browser_runs_non_root tests/e2e/test_new_harvest_runtime_security.py::test_production_forbids_no_sandbox tests/e2e/test_new_harvest_runtime_security.py::test_browser_egress_rechecks_each_redirect tests/e2e/test_new_harvest_runtime_security.py::test_parser_process_network_denied tests/e2e/test_new_harvest_runtime_security.py::test_backpressure_zero_downstream tests/e2e/test_nh6_readiness.py::test_positive_probe_matches_presence tests/e2e/test_nh6_readiness.py::test_missing_binary_component_not_overall_green tests/e2e/test_nh6_readiness.py::test_models_list_insufficient_for_ready tests/e2e/test_nh6_readiness.py::test_create_app_readiness_without_patch -q`。禁止整文件 `-q`。unit backpressure **不得**列入本命令 |
| 层与来源 | L2/L3/S；`🔱` NH6 已建固定路径。backpressure PASS = security L2 node，unit 不得单独关闭 |

#### `NH9-T11`

| 字段 | 内容 |
|---|---|
| 测试位置 | 🆕 `tests/domain/test_nh9_evidence_pack_checker.py::test_nine_packs_have_six_artifacts`；`::test_each_test_id_has_four_tuple`；`::test_fg_nh_01_to_17_all_green`；`::test_no_expired_waiver_and_no_foundational_override`；`::test_experiment_not_in_closure_join`。**禁止** `::test_nh9_11_schema_exists_with_empty_dates_scores` 列入本 Test-ID |
| 用途 | 证明 **仅** `NH9-10`；`T-O-406/380`；`FG-NH-16/17`。`NH9-11` 骨架 **不是** T11 EXIT0 |
| 前置 | 九目录已由各 AP 执行期写入（本 AP 执行末期才绿）；checker 只读文件，不造假 SHA |
| 步骤 | a) 枚举 `AP-NH1`…`AP-NH9`。b) 每包六类文件存在。c) 解析 `tests.txt`/`closure.md` 对应该 AP 台账 C 每个 Test-ID 的四元组。d) `::test_fg_nh_01_to_17_all_green` **必须**引用各 AP evidence `tests.txt` 中已规定的反假绿 node（无 fetcher 赋值扫描、无 sqlite3、无 namespace 422、T09 每格 query、T10 非 models-list）；`security/fg-nh-01-17.md` 只作索引，**不得**当唯一 PASS 证据。e) waiver JSON：owner、Truth、到期 > now 或已 reopen；禁止 affected 含覆盖 `T-O-376/378/381/383`。f) closure 文件 grep `.experiment` / `0815` / vendor score **不得**出现在 PASS 列表。 |
| 断言细节 | checker EXIT0 当且仅当 pack 六类+四元组+FG node 证据+waiver 围栏成立。**缺 experiment schema/分数 ≠ FAIL**。**非空分数 ≠ PASS**。缺四元组 FAIL |
| 负例 | 9 个 unit 计数当 pack；把 NH9-11 schema 存在性当 T11 DoD；手写 17 行绿 markdown 当 FG PASS；伪造 SHA |
| 跑法 | `uv run pytest tests/domain/test_nh9_evidence_pack_checker.py::test_nine_packs_have_six_artifacts tests/domain/test_nh9_evidence_pack_checker.py::test_each_test_id_has_four_tuple tests/domain/test_nh9_evidence_pack_checker.py::test_fg_nh_01_to_17_all_green tests/domain/test_nh9_evidence_pack_checker.py::test_no_expired_waiver_and_no_foundational_override tests/domain/test_nh9_evidence_pack_checker.py::test_experiment_not_in_closure_join -q` |
| 层与来源 | L1 contract；`🆕`；映射 **仅** `NH9-10` |

### 8.2 复用台账（沿用 / fork 的既有用例明细）

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/e2e/test_intake_identity_replay.py` | `🔱` 整文件 Port 化。**未删除 `import sqlite3`/`sqlite3.connect` 前 ⛔ 不得列入 T02 跑法** | 删 sqlite3；断言改 Port | HEAD PASS 但 `FG-NH-12` 违规；未 Port 化不得当 T02 |
| `tests/e2e/test_inline_ingress_staging.py` replay 200 | **⛔ 不得当 T02 PASS**（HEAD `:8` `import sqlite3`、`:29` turso、`:101` `sqlite3.connect`） | 产品法可沿用，但 0 改动直读 **禁止** 列入 T02 跑法/测试位置 | HEAD 存在且 `FG-NH-12` |
| `tests/e2e/test_nh3_seal_crash_windows.py` NH3-T07 | `🔱` 列入 T04 跑法 | 0 改实现 | 依赖 NH3 PASS；L2/F |
| `tests/e2e/test_nh1_fanin_recovery_port.py` NH1-T02 | `🔱` 列入 T05 | 0 | 依赖 NH1；无 sqlite3 |
| `tests/e2e/test_registered_api_scatter.py` zero/child | 未 Port 化、未补 namespaced query、仍 sqlite3/`publication_ready`/handler 赋值前 = **⛔ 不得进 T07 跑法**。Port+query 后才可 🔱 | 删 sqlite3；禁 handler 赋值当绿；auto-zero 用 disposition+empty search；child-fail 父 search 0 | HEAD fan-in 红（disk I/O）；`:321` `publication_ready`；`:352-364` succeeded；`:488` 替换 handler |
| `tests/unit/test_ns6_gc_toctou.py` / `test_nh4_upload_ttl_gc.py` | `🔱` 全排列 | 加 interleave 节点 | 依赖 NH4 |
| `tests/unit/test_workflow_revision_compatibility.py` | `🔱` NH2-T06 | 0 或已由 NH2 加 kind 节点 | HEAD 2 passed（markdown 史，非 kind） |
| NH3-T06 migration/scan | `🔱` T08 legacy alias | 0 | 依赖 NH3 |
| NH5-T07 facet e2e | `🔱` T09 | 0 重写 | 依赖 NH5 |
| NH6-T02/T05/T08/T09 | `🔱` T10 | 0 实现 | 依赖 NH6 AP/证据 |
| NH7-T03..T09 | `🔱` T07/T09 | 不重写 lane | 依赖 NH7 |
| NH8 publication/lifecycle | `🔱` T05 PUB / T09 H | 0 | 依赖 NH8；T08-B 须已绿 |
| `test_source_capability_paths.py:99-101` | `⛔` 不 fork 成功路径 | 0 | HEAD 反例 |

### 8.3 分层与跑法（各类型在哪跑、何时跑）

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `uv run pytest tests/unit/test_nh9_closed_set_manifest.py tests/domain/test_nh9_evidence_pack_checker.py -q` | L1 | 每 PR（T11 在证据齐后） |
| spike / compat | `uv run pytest tests/e2e/test_nh9_task_identity_conflict.py tests/unit/test_workflow_revision_compatibility.py -q` | L2 | Phase 2/5 |
| fault mega | `uv run pytest tests/e2e/test_new_harvest_crash_windows.py tests/e2e/test_nh3_seal_crash_windows.py tests/e2e/test_nh1_fanin_recovery_port.py -q` | L2/F | Phase 3 收口 |
| soak / race | T02 concurrent + T06 全排列 | L2/L3/R | 退出硬闸 |
| mega L4 | `uv run pytest tests/e2e/test_new_harvest_closed_set.py -q` | L4 | **本 AP 收口** |
| security soak | T10 固定路径 + NH6 四测 | L2/L3/S | **本 AP 收口** |

本 AP 台账 C 最低层不得自行降：T01 L1；T02 L2/L3；T03 含 L4 负向；T04 L2/F；T05 含 L4；T06 L2/L3；T07 L3/L4；T08 L2/C；T09 **L4**；T10 L2/L3/S；T11 L1。

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖 PDF/browser/OCR/Vision **供给实现**（理由：`S-NH-F6`）→ `AP-NH6`。T10 只 🔱。若缺隔离/接线，**campaign blocked**，点名 `NH6-02..10`，**禁止**本 AP 写 parser。
- 不覆盖 10+3 **lane 接通**（理由：`S-NH-F7`）→ `AP-NH7`。T09 只 query。正格无 hit → 点名对应 `NH7-04..09`。
- 不覆盖 rebuild intent-guard / no-op cleaner 消除（理由：`T-O-407`；NH5-T08-B 交接）→ `AP-NH8`。若 T08-B 仍红，点名 `NH8-03` / `NH8-T03`（rebuild 红灯另点 `NH8-02`）。
- 不覆盖 public upload 内核 / pending DDL（理由：`S-NH-F4`）→ `AP-NH4`。T06 只交错。
- 不覆盖 actual S05 列与 seal 实现（理由：`S-NH-F3`）→ `AP-NH3`。T04 🔱 NH3-T07。
- 不覆盖 kind 图 / CONTROL 实现 → `AP-NH2`。
- 不覆盖 experiment 发车与评分 → `O-NH-05` / `T-O-380`；`NH9-11` 非 DoD。
- 不覆盖 raw GET / 第五 kind / existing upgrade / 新 strategy/intent/route。
- **撰写时缺口消费**：已读 AP-NH1 §8.4/§10.4、AP-NH2、AP-NH3、AP-NH4、AP-NH5。NH6–NH8 AP 文件当时未入库，其 NOT-成功以 final §7.6–7.8 为准（NH6：import/which/models-list…；NH7：33 unit/503/Task succeeded…；NH8：no-op cleaner/28 格/upgrade 混入）。后入库 AP 的 §8.4 若列出功能缺口，本 AP **不得**吸收为 NH9 工作项。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 必带四元组；计数 ≠ 价值。
- 本 AP 适用 **全部** `FG-NH-01..17`（战役退出法）。对应细则：T09→01/03/04/05/06/07/14；T02→12；T03→02/06；T08→08/09；T10→11；T01/T11→13/15/16/17；T07→03/04。
- `degraded` 必带机器可读 `reason`；pre-existing 失败必带 git 证据。
- 安全项 T02/T04/T06/T10 必须含 §7.3 攻击向量。
- T09 不得跳 ingest 直插向量。T11 不把 experiment 分数当 PASS。
- 发现功能缺口：`closure.md` 写 `campaign_blocked: true` + 上游 AP/工作项 ID，本 AP **不得**标 executed。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| `R-F15` NH9 垃圾桶化 | 前 AP 跳负测，末期返工/补功能 | `high` | 每上游 DoD 硬闸；本 AP 首测到功能缺口即 blocked |
| `R-F13` L1 替代 L3/L4 | 环境困难/耗时 | `high` | `T-O-406`；waiver 只延期 |
| `R-F14` Task/flag 顶替 query | 沿用旧 e2e | `high` | T09 强制 namespace L4 |
| `R-F16` scope 滑向 upgrade/connector | 临时需求 | `medium` | OOS 硬围栏；新 owner-gate |
| DAG 上游未绿 | NH1–NH8 任一台账 C 未 PASS | `high` | 本 AP 不得开工 mega；保持 draft |
| `R-F07` upload 误删 | GC 交错 | `high` | T06 🔱 NH4；缺口交 NH4 |
| `R-F11` rebuild 偷 reclean | T08-B 仍红 | `high` | 交 NH8，不在本 AP 写 no-op |
| `R-F04` old pin 绞杀 | kind 激活后 409 | `medium` | T08 🔱 NH2/NH8 |
| RA09 Temporal 误借 | 引入外部引擎 | `low` | `NH9-A07` 只借失败法 |
| experiment 误进 join | 有人填分数 | `medium` | T11 负向断言；`FG-NH-16` |

### 9.2 约束与前提

- **技术前提**：HEAD `1221aa1` 代码分母；NH1–NH8 功能已按各自台账落地。本 AP 不改生产 DDL/pyproject/生产配置。
- **运行时前提**：L3/L4 需要 NH6 真实 binary/model 与 default-root 注入；缺供给 → T09 正格 FAIL（交回 NH6/NH7），禁止 skip 当 PASS。
- **组织协作前提**：无新 owner-gate。NH6–NH8 AP 后入库时，本文件只 join 其 Test-ID 路径，不改冻结 T-O。
- **上线 / 合并前提**：`NH9-T01..T11` 全 PASS；`FG-NH-01..17` 全绿；无未解释 S1/过期 waiver。文档状态已 `executed`。

### 9.3 文档同步要求

- 需要同步更新的设计文档：无（禁止改 QNA/final/RA）
- 需要同步更新的说明文档 / README：执行期 evidence 可指向 README K1 namespace，不在本 AP 改 README
- 需要同步更新的测试说明：本文件 §8；`docs/evidence/new-harvest/AP-NH9/tests.txt`

### 9.4 完成后的预期状态

1. `closed_set_manifest.v1.json` digest 稳定，含 82 work IDs、10+3、七意图、层与负格。
2. 九窗 `W-NH-*` 均有 pytest node；无 sqlite3-on-Turso recovery 绿。
3. 每 knowledge 正格可经 namespace+facet+proof 检索；失败格 0 hit。
4. 九份 evidence pack 四元组齐；`FG-NH-01..17` 清单全绿；无过期 waiver。
5. experiment 骨架存在但日期/分数空，**未**进入 campaign DoD。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

### 10.1 收口硬闸

所有 `mega + soak + 退出层` 必须 **PASS 且四元组证据齐全**。下列谓词抄 final §7.9 台账 D，可判定、不是「测试通过」。

1. **closed-set coverage**：manifest 含 82 works、全部合法格/负格/层级（由 `NH9-T01` 证明；证据形态 manifest digest）。
2. **replay/fault**：所有 W-window deterministic、无双 effect/热切（由 `NH9-T02`/`T04`/`T05` 证明；证据形态 fault report）。九窗 node 必须存在：`W-NH-CREATE/SEL/SEAL/PROCESS/FANIN/PUB/OUTBOX/PROM-CAT/GC-INGEST`（后两窗由 T06 交叉证明）。
3. **object/scatter**：races 不丢 bytes/不假 Item，zero/child 语义正确（由 `NH9-T06`/`T07` 证明；证据形态 DB/proof/query）。
4. **compat**：old pin 可完结，legacy alias 不当 actual（由 `NH9-T08` 证明；证据形态 execution audit）。
5. **product closure**：每应产知识格 query+trace+facet，失败格零命中（由 `NH9-T03`/`T09` 证明；证据形态 mega report）。
6. **security closure**：isolation/readiness/SBOM/CVE/backpressure 全门通过（由 `NH9-T10` 证明；证据形态 security signoff）。
7. **evidence immutability**：每 AP 四元组齐、waiver 合规、UTC/commit 固定（由 `NH9-T11` 证明；证据形态 evidence pack）。另：`FG-NH-01..17` 全绿清单进 evidence；无过期 waiver。

**DoD 硬闸**（逐字回到 final §7.9）：`NH9-T01..T11` 全 PASS；`FG-NH-01..17` 全绿；无未解释 S1/过期 waiver。`NH9-11` experiment **不是**硬闸。

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| closed-set coverage：manifest 含 82 works、全部合法格/负格/层级 | `NH9-01` | `NH9-T01` | `commit SHA + test_nh9_closed_set_manifest.py PASS + Q26 + UTC`；证据形态 manifest digest | `未观察` |
| replay/fault：所有 W-window deterministic、无双 effect/热切 | `NH9-02`/`NH9-04` | `NH9-T02`/`T04`/`T05` | `commit SHA + parallel/window/repair PASS + T-O-383/Q20/Q26 + UTC`；fault report | `未观察` |
| object/scatter：races 不丢 bytes/不假 Item，zero/child 语义正确 | `NH9-05`/`NH9-06` | `NH9-T06`/`T07` | `commit SHA + interleavings/result/query PASS + Q24/Q17 + UTC`；DB/proof/query | `未观察` |
| compat：old pin 可完结，legacy alias 不当 actual | `NH9-07` | `NH9-T08` | `commit SHA + sequence PASS + Q10/Q18 + UTC`；execution audit | `未观察` |
| product closure：每应产知识格 query+trace+facet，失败格零命中 | `NH9-03`/`NH9-08` | `NH9-T03`/`T09` | `commit SHA + negative/manifest query PASS + Q3/Q26 + UTC`；mega report | `未观察` |
| security closure：isolation/readiness/SBOM/CVE/backpressure 全门通过 | `NH9-09` | `NH9-T10` | `commit SHA + security pack PASS + Q19 + UTC`；security signoff | `未观察` |
| evidence immutability：每 AP 四元组齐、waiver 合规、UTC/commit 固定；FG-NH-01..17 全绿 | `NH9-10` | `NH9-T11` | `commit SHA + pack checker EXIT0 + T-O-406 + UTC`；evidence pack | `未观察` |
| experiment 骨架隔离（非 DoD） | `NH9-11` | **无 Test-ID**；T11 仅负向：closure PASS 列表不含 experiment/0815/vendor 分数 | 缺 schema/分数不得使 T11 FAIL；有分数不得使 T11 PASS | `未观察`（**不作为 executed 硬闸**） |

PASS 证据四元组形态（执行期填写）：`commit SHA + pytest node PASS + Truth/Q + UTC`。

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | 无新 strategy/intent/route；只 join 上游功能。§10.1 七条谓词为真 |
| 测试 | `NH9-T01..T11` 全 PASS；退出硬闸项四元组齐全；最低层不低于台账 C |
| 文档 | `docs/evidence/new-harvest/AP-NH9/` 含：`manifest.json`；`tests.txt`；`queries/closed-set-digest.json`；`queries/mega-cells.json`；`queries/negative-zero-hits.json`；`queries/crash-windows.json`；`migrations/`（join 指针或空证明）；`security/fg-nh-01-17.md`；`security/sbom-cve-waiver.md`；`security/runtime-security.txt`；`closure.md` |
| 风险收敛 | `R-F13..F16` 未以假绿关闭；无未解释 S1；无过期 waiver |
| 可交付性 | campaign DoD = 九 AP 台账 C 全 PASS + 台账 D 逐项四元组 + capstone A–J + 无过期 waiver。实验发车不在 DoD |

### 10.4 NOT-成功识别

> 任一退出硬闸测试 `degraded / 未观察` ⇒ **不得标 `executed`**。

抄 final §7.9 并补本 AP 假绿：

1. **NH9 第一次补功能**（parser/lane/guard/upload/seal/kind 实现）
2. **降低测试层**（L1 顶 L3/L4；fault/race/security 当第五层）
3. **experiment / 0815 / live vendor 顶替** completeness（`T-O-380`；`FG-NH-16`）
4. **口头 exactly-once**（无 CAS 断言）
5. **修期待值掩盖 S1**（`FG-NH-17`；含把 `running` 写成可接受终态）
6. monkeypatch 当 L3（`FG-NH-01` / `NH9-A05`）
7. sqlite3 直读 Turso 当 recovery/replay（`FG-NH-12`）
8. Task succeeded / `publication_ready` 当可检索（`FG-NH-03/04`）
9. 跳过 ingest 直接 INSERT 向量（T09 硬禁）
10. 503 / 诚实未部署当正格 DoD（`FG-NH-02`）
11. domain/legacy alias 当 actual（`FG-NH-08`）
12. 7×4 假矩阵（`FG-NH-15`）
13. 只测 API 代表四通道（`FG-NH-14`）
14. import/which/models-list 当 ready（`FG-NH-11`）
15. no-op cleaner / existing upgrade 混入（属 NH8；本 AP 若实现即失败）
16. 新 public route / 新 strategy / 新 intent
17. 把 `NH9-11` 或 T12 写成 DoD

---

## 11. 执行日志回填（仅 `executed` 状态使用）

> 执行者：`Grok`
> 执行时间：`2026-08-30`
> 文档状态：`draft → executing → executed`
> 代码改动统计：P1–P6 分 commit；实现收口 `f7db57c`；PROM-CAT hook 1 行

- **实际执行摘要**：P1 冻结 82/windows/FG；P2 Port 化 replay + fail-loud zeros；P3 CREATE/PROCESS/FANIN/PUB/OUTBOX 并 wrap NH3-T07/NH1-T02；P4 PROM-CAT/GC 交错 + scatter query；P5 old-pin + 13 正格 mega；P6 NH6 安全 join + pack checker。
- **Phase 偏差**：
  - public replay 信号是 HTTP 200 vs 201，不是 JSON `replayed`（substrate-fit）。
  - 失败 ingest 无 Layer-A namespace；T03 用 control seed + facet isolation（substrate-fit）。
  - T07 不把 HEAD scatter handler 文件当 PASS；closed_set 用 handler 仅作 child-fail 注入，query 才是绿。
  - `.experiment` gitignore；骨架可存在，不进 join（计划偏差 / T-O-380）。
- **阻塞与处理**：无上游功能缺口交回。T04 具名 SEL/SEAL 在 crash_windows wrap；T08 架构扫描别名 `test_architecture_scan_zero_actual_readers_of_legacy_column`。
- **测试发现**：T01–T10 各 AP 跑法 PASS。T09 16 passed ~215s。T10 12 passed ~88s。T11 本包。
- **后续 handoff**：`CROSS-NH` 耦合审查与全量回归。experiment 发车另册（`T-O-380`）。S16 不伪造。

### 11.1 逐工作项状态

| 工作项 | 状态 | PR | 实际落点 | 备注 |
|--------|------|----|----------|------|
| `NH9-01` | ✅ done | `8754df3` | closed-set manifest + T01 | digest 保持 NH1 |
| `NH9-02` | ✅ done | `50c2246` | identity conflict + Port replay | T02 |
| `NH9-03` | ✅ done | `50c2246` | closed_set 负格 | T03 |
| `NH9-04` | ✅ done | `8196a0a` | crash_windows CREATE/PROCESS/FANIN/PUB/OUTBOX | T04/T05 |
| `NH9-05` | ✅ done | `6390d9b` | upload interleave + PROM-CAT | T06 |
| `NH9-06` | ✅ done | `6390d9b` | exhausted_zero / child-fail query | T07 |
| `NH9-07` | ✅ done | `6fbb1a7` | NH2/NH3 compat wrap | T08 |
| `NH9-08` | ✅ done | `6fbb1a7` | 13 legal-cell mega | T09 |
| `NH9-09` | ✅ done | `f7db57c` | NH6 T10 join | T10 |
| `NH9-10` | ✅ done | this pack | evidence checker | T11 |
| `NH9-11` | ✅ done | manifest experiment | 非 DoD | 无独立 Test-ID |

### 11.4 文档状态

`draft → executing → executed（2026-08-30）`。
residual → `CROSS-NH`。

---

## 附录 · 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| `v0.1` | `2026-08-29` | Grok workflow new-harvest-nh6-nh9-action-plans | 由 final §7.9 派生；RA09 + HEAD `1221aa1` 独立核对；join NH1–NH5 §8.4/§10.4 与 §7.6–7.8 冻结 ID |
| `v0.2` | `2026-08-29` | Grok fix-fleet | 吸收已核实 review：T11 只映射 NH9-10，去掉 schema-exists DoD node，FG 必须引用 tests.txt 反假绿 node；T02 去掉 staging sqlite3 文件；T03/T06 跑法改为显式 path::node；T07 删除 HEAD scatter 假绿节点并抄入 NH7-T09 四 node；T09 补 facet SQL unit；T10 抄入 NH6 T02/T05/T08/T09 path::node；fan-in 锚 `runtime_scatter.py:277-483` |
| `v0.3` | `2026-08-29` | Grok recon-fix | Capstone 表改为「主 AP + NH9 交叉」；T08-B 仍红点名 `NH8-03`/`NH8-T03`；T02 未 Port 化 identity 文件不得进跑法；T10 只 🔱 NH6 已建 node（禁同名 🆕，unit 不得关 backpressure）；T01 锁死 10+3 字段名 |
| `v1.0` | `2026-08-30` | Grok | 执行回填 §11；文档状态 `executed`；T01–T11 PASS `f7db57c` |
