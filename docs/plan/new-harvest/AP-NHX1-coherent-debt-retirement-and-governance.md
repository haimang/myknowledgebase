# MKB new-harvest NHX1 行动计划

> 服务业务簇: `MKB / new-harvest / coherent-debt-retirement`
> 计划对象: `二轮审查全部有效欠账 + 应内聚 deferred 的单阶段串行治理与修复`
> 类型: `upgrade`（含 refactor / migration / remove；不拆成多个阶段级 AP）
> 作者: `GPT`
> 时间: `2026-08-31`
> 文件位置: `src/`、`intake/`、`api/`、`tests/`、`docs/evidence/new-harvest/AP-NHX1/`、`docs/closure/new-harvest/AP-NHX1-coherent-debt-retirement-and-governance.md`
> 上游前序 / closure:
> - `docs/code-review/new-harvest/NH1-NH9-2nd-pass-review-VF-ledger.md`（52 VF；50 项未了结债务分母）
> - `docs/eval/new-harvest/pre-NHX1-qna.md` v1.0 `frozen`（Q28–Q42 → `T-O-408..422`）
> - `docs/eval/new-harvest/after-2nd-pass-review-coherent-fixes-design.md`（目标架构与coverage；执行包装由本AP收敛为单一NHX1）
> 下游交接:
> - `docs/evidence/new-harvest/AP-NHX1/`（manifest/tests/queries/migrations/security/closure 六类证据）
> - 第3轮独立代码审查 + `docs/closure/new-harvest/AP-NHX1-coherent-debt-retirement-and-governance.md`
> 关联设计 / 调研文档:
> - `docs/closure/new-start/deferred-items-ledger.md`（NH及直接NS carry-over）
> - `docs/eval/new-harvest/final-execution-plan.md`（原 `T-O-376..407` 与L1–L4）
> - `docs/baseline/domain-truth/S03-workflow-engine.md`、`S04-intake-asset-lifecycle.md`、`S13-artifact-storage.md`、`S15-observability-reliability.md`、`S16-security-trust-boundary.md`
> 冻结决策来源:
> - `docs/eval/new-harvest/pre-NHX1-qna.md` Q28–Q42 / `T-O-408..422`（只读；本AP不再开Q/A）
> - `docs/eval/new-harvest/pre-charter-qna.md` Q10–Q27 / `T-O-390..407`
> - `docs/eval/new-harvest/pre-initial-planning-qna.md` Q1–Q9 / `T-O-376..389`
> grounding 来源:
> - HEAD `ba099ee305577cca2281a669afbca364111f200b` 的代码/DDL/OpenAPI实测；§7内置锚区为本AP直接grounding真源
> 关联 reference-anchor:
> - 见 §7 内置 Reference-Anchor；安全威胁模型另指 `docs/baseline/domain-truth/S16-security-trust-boundary.md:438-465`
> 文档状态: `executing`
> 计划 ID: `NHX1-P1-01..P9-04`；测试 ID: `NHX1-T01..NHX1-T30`

**执行硬纪律**：这是一个 `NHX1` 阶段、九个严格串行 Phase 的行动计划。依赖链只有
`Phase 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9`；任一 Phase 的工程EXIT测试未PASS或证据四元组不齐，后继一律blocked。唯一外部例外是 `NHX1-T22-O`（真实环境/S16 owner attestation）：Phase 6 自动化子闸 `NHX1-T22-E` 可先达到 `ready-for-owner-gate` 并串行交给Phase 7，NHX1-T22整体仍非PASS且必须在Phase 9 join前补齐。不得把“DAG”解释成并行施工，也不得把Phase拆成可独立close的多个AP。

---

## 0. 执行背景与目标

NH1–NH9 第2轮统一台账在 HEAD `ba099ee` 上确认：`15 true-bug + 18 partial-delivery + 17 true-deferred` 共50项未了结债务；另 `VF27` 为保留的fail-loud设计、`VF52` 已驳回但需回归守卫。冻结QNA已把这些缺口收敛为四类durable token（ObservationReservation、ItemEpoch、WorkflowRevisionPin、ObjectUploadSession/Reference）与15条owner Truth。业主选择一个 `NHX1` 阶段内串行完成，不允许再按critical hotfix或跨阶段defer。

本AP消费、而不重问 `T-O-408..422`。它先冻结分母/旧库fixture，再扩schema；随后依次改intake、workflow、object/evidence、runtime roles、read/control/observability；最后做compat drain与graph-derived assurance。每个承重修改必须先有修前RED或静态drift，且在本Phase短途绿后才解锁下一Phase。production模型/binary/S16未签时，按 `T-O-419` 整个NHX1保持blocked，不允许`closed-with-deferred`。

- **服务业务簇**：`MKB / new-harvest`
- **计划对象**：二轮审查后完整还债、deferred内聚、迁移兼容、leaf-worker读控面、真实runtime与闭集证明
- **本次计划解决的问题**：
  - Source/Observation/Snapshot/Item/Task身份混用与跨Task竞态（VF1–VF12）
  - workflow revision、Outcome终态、route/replay/processing binding与dead owner断裂（VF13–VF21/VF42/VF43/VF45/VF47）
  - upload session、pre-catalog CAS、evidence可变、stage正文、cleanup/GC物理不收敛（VF22–VF28）
  - supply/readiness/leaf role、discovery/read/debug/control、metrics/error与assurance欠交付（VF29–VF51）
- **本次计划的直接产出**：
  - migration `025+`、v2 contracts/services/runtime及forward-only cutover/retirement工具
  - 四通道统一Observation/ItemEpoch/session/replay法；rev2 workflow与old-pin exact兼容
  - public safe discovery/strict views、operator debug/control、role-specific readiness与真实10+3 production gate
  - `NHX1-T01..NHX1-T30` 全测试台账、逐测试防假绿、graph-derived manifest、process-kill/old-DB/full-repo证据包
- **本计划不重新讨论的设计结论**：
  - Observation显式分账、Item单epoch、full retry零外部重抓（Q28–Q30 / `T-O-408..410`）
  - rev2+rev1 exact、ProcessingBinding union、session owner、append-only correction（Q31–Q34 / `T-O-411..414`）
  - public/operator分权、四role、物理cleanup、canonical errors（Q35–Q38 / `T-O-415..418`）
  - prod无stub且owner gate阻断closure；existing-object upgrade保持OOS；tombstone保key；critical dead终结owner（Q39–Q42 / `T-O-419..422`）

---

## 1. 执行综述

### 1.1 总体执行方式

执行方式为：**先分母与旧事实、后schema；先authority、后wire；先新writer、后迁consumer；先shadow验证、后删旧；最后才做全链assurance**。九Phase严格串行。Phase 1冻结coverage、pre-fix DB/rev1 fixture和修前RED；Phase 2只扩schema/ports/registries，不切业务writer；Phase 3–7依次闭合intake、workflow、object/evidence、runtime role、read/control；Phase 8执行dual-read/write验证与legacy drain；Phase 9从compiler/manifest生成测试分母并完成真实crash、full repo、owner gate和第三轮审查。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | Truth denominator / fixtures / harness | `L` | 冻结50项coverage、旧库+rev1 fixture、当前RED、adapter-aware harness与anti-fake-green checker | `-` |
| Phase 2 | Canonical schema / ports / registries | `XL` | migration 025+：Observation、session/cleanup、evidence v2、ops owner；read_snapshot、shadow与code-owned registries | Phase 1 EXIT |
| Phase 3 | Intake identity / ItemEpoch / lifecycle | `XL` | admission reservation、single/scatter acceptance、failed retry、7×3 applicability、rebuild cardinality | Phase 2 EXIT |
| Phase 4 | Workflow revision / replay / Outcome | `XL` | rev2+old pin、ProcessingBinding、terminal fence、current-hop routing、exact retry、outbox owner | Phase 3 EXIT |
| Phase 5 | Object / evidence / physical convergence | `XL` | upload session+journal、CAS-first envelope、immutable evidence、publication manifest、cleanup/GC终态 | Phase 4 EXIT |
| Phase 6 | Capability / role / readiness / security | `XL` | api/worker/maintenance/all、ProcessCapabilityManifest、truthful readiness；10+3自动化达到NHX1-T22-E，owner签收NHX1-T22-O带到Phase 9 | Phase 5 EXIT |
| Phase 7 | Discovery / control / observability / errors | `XL` | strict public catalog/views/lists、operator debug/control、receipts、signals/alerts/error registry | Phase 6 EXIT |
| Phase 8 | Cutover / compat drain / retirement | `L` | shadow mismatch=0、新writer唯一、rev1/legacy/cleanup排空、rollback drill、删除死形状 | Phase 7 EXIT |
| Phase 9 | Graph-derived assurance / closure | `XL` | compiler-derived L1–L4、race soak、subprocess crash、old DB、full repo、evidence executor、第三轮review | Phase 8 EXIT + owner live/S16 gate |

### 1.3 Phase 说明

1. **Phase 1 — Truth denominator / fixtures / harness**
   - **核心目标**：让每个VF/deferred、每个修前反例和每个旧数据坐标可机器判定，修复前先稳定RED。
   - **为什么先做**：没有pre-fix fixture/coverage，rev2/migration与测试极易只在空库假绿。
2. **Phase 2 — Canonical schema / ports / registries**
   - **核心目标**：只做forward expand和typed接口；所有后续writer共享一套identity/version/session/evidence法。
   - **为什么放在这里**：Phase 3–7不可各自发明表、counter、code或owner字段。
3. **Phase 3 — Intake identity / ItemEpoch / lifecycle**
   - **核心目标**：先把业务对象和admission线性化，确保后续workflow/object读取稳定坐标。
   - **为什么放在这里**：workflow retry、object reserve与public read均依赖Observation/ItemEpoch。
4. **Phase 4 — Workflow revision / replay / Outcome**
   - **核心目标**：修复执行状态机、图版本与causal replay，禁止terminal推进和old actual/new bytes混合。
   - **为什么放在这里**：对象/evidence commit必须被正确Outcome owner线性化。
5. **Phase 5 — Object / evidence / physical convergence**
   - **核心目标**：字节、session、业务ref、evidence与physical delete各有durable owner并能crash收敛。
   - **为什么放在这里**：必须消费Phase 3/4稳定的Task/Observation/Process/Item坐标。
6. **Phase 6 — Capability / role / readiness / security**
   - **核心目标**：把“图需要什么、哪种role部署什么、当前能否接活、production是否签收”分账。
   - **为什么放在这里**：真实worker应只消费已经稳定的workflow/object/evidence contract。
7. **Phase 7 — Discovery / control / observability / errors**
   - **核心目标**：在authority稳定后冻结wire，给上游/前端/operator足够而不越权的读控面。
   - **为什么放在这里**：过早写API会再次投影错误字段或旧状态。
8. **Phase 8 — Cutover / compat drain / retirement**
   - **核心目标**：验证new/old双轨一致，切new writer，排空old pin/ref/open job后再删除旧入口。
   - **为什么放在这里**：所有consumer与operator读面已在Phase 7就绪，才能证明零使用。
9. **Phase 9 — Graph-derived assurance / closure**
   - **核心目标**：以当前compiled graph和capability manifest生成闭集，做真实process crash、persisted upgrade、full repo与evidence执行。
   - **为什么放在这里**：assurance不允许第一次实现功能；失败必须回到owner Phase修复并重跑后继链。

### 1.4 执行策略说明

- **执行顺序原则**：严格 `P1→P2→…→P9`；每Phase只在自己的authority边界施工，跨Phase接口变更回退Phase 2重新审查。
- **风险控制原则**：expand-only migration；legacy evidence不UPDATE；cutover前可关new admission，cutover后禁止旧writer复活；security/operator/purge独立review。
- **测试推进原则**：每工作项先RED/静态drift → Phase短途 → Phase EXIT mega/soak；Phase 9再跑graph-derived/full。详见§8，任何skip/xfail/degraded不解锁后继。
- **文档同步原则**：每Phase执行时append `docs/evidence/new-harvest/AP-NHX1/{phase}/`；不改历史review/closure；Truth只能引用QNA。
- **回滚 / 降级原则**：Phase 2–7切换前用feature gate/shadow；一旦v2 evidence/new Task写入，回滚=停admission+前滚修复，禁止恢复旧writer或改写v2事实。production supply缺件只允许blocked，禁止降为stub。

### 1.5 本次 action-plan 影响结构图

```text
NHX1 coherent debt retirement（单阶段 / 串行DAG）
└── Phase 1 denominator + old fixtures + honest harness
    └── Phase 2 schema/ports/registries (025+ expand)
        └── Phase 3 intake: Source → Observation → Snapshot → ItemEpoch
            └── Phase 4 workflow: rev pin → route → Outcome → exact replay → outbox owner
                └── Phase 5 object/evidence: session → refs → manifest → cleanup → GC proof
                    └── Phase 6 runtime: capability manifest → role → readiness → real supply
                        └── Phase 7 wire/ops: catalog → strict views → debug/control → signals/errors
                            └── Phase 8 cutover: shadow → new writer → drain → retire/rollback drill
                                └── Phase 9 assurance: graph cells → race/crash/upgrade → full repo → closure
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** `VF1..VF51` 的50项未了结债务全部修复或通过删除无用形状完成治理；`VF27`保留设计但补reserved-session竞态；`VF52`保留body-cap回归。
- **[S2]** `NH-VF3.r/4.r/9.r/10/13/14.r/21/27.r/29/36/37/38/39/41.r/42` 全部在本AP落到Phase/Test-ID。
- **[S3]** SourceIdentity/ObservationReservation、单ItemEpoch、failed observation retry、四通道admission与7 intent×3 state完整矩阵。
- **[S4]** rev1 exact fixture+rev2、ProcessingBinding 10+3、terminal Outcome/current-hop route、exact full retry、critical/advisory outbox owner。
- **[S5]** ObjectUploadSession/promotion journal、session reserve/consume、append-only evidence/correction、CAS-first stage、publication manifest/read snapshot、physical cleanup/GC。
- **[S6]** `api/workflow_worker/maintenance/all`、ProcessCapabilityManifest、single/concurrent writer画像、supervisor readiness、真实10+3、安全/process tree。
- **[S7]** public safe workflow/capability/Task/Item/Namespace读面；operator Process/Stage/Fact/Diagnostic/cleanup/outbox读控面；CommandReceipt与canonical errors。
- **[S8]** migration expand/shadow/cutover/drain/contract、old pin/legacy alias/unused enum退役与forward-only rollback drill。
- **[S9]** L1/L2/L3/L4、race/crash/security/upgrade/full-repo不可互换测试；每Test-ID独立防假绿；真实evidence executor与第三轮review。

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** existing-object新cleaner/validator upgrade；禁止借retry/rebuild暗换（Q40 / `T-O-420`）。
- **[O2]** raw object GET/export/list/presign、R2/remote adapter（`T-O-396`）。
- **[O3]** 第五source kind、live connector/cookie/tunnel、caller workflow key、action_branch（`T-O-377/379`）。
- **[O4]** 通用Workflow JOIN/DSL/自由表达式/动态loader（`T-O-398`）。
- **[O5]** external vector engine、answer generation、cuts/g0算法重开、前端实现。
- **[O6]** experiment发车/评分；仅验证其不进入NHX1 closure（`T-O-380`）。
- **[O7]** 任意SQL/raw payload公共debug；operator也只允许typed command和registered redacted projection（`T-O-415`）。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| workflow/capability只读目录 | `in-scope` | `T-O-415`；发现不等于选图 | 推翻caller禁workflow key须新Truth |
| process/stage/fact payload | `in-scope / operator-only` | debug所需且受S16隔离 | 公开任何字段须安全QNA |
| process restart/outbox requeue/repair/stop | `in-scope / operator-only` | 替代人工SQL，`T-O-422` | 任意mutation永不开放 |
| physical Intake purge | `in-scope` | `T-O-417`；logical-only无法长期治理 | retention数值可配置，reference-first不重评 |
| 真模型/binary/S16签收 | `in-scope + owner gate` | `T-O-419` | 未签即NHX1 blocked |
| multi-writer数据库实现 | `out-of-scope substrate` | 本AP修truthful profile/readiness，不引入新DB | 需要真实并发backend charter |
| unused pointer building/retiring | `remove` | NH-VF36；无writer不应冒充能力 | 新index设计重开 |
| v1 public clean_strategy | `compat-only` | actual由late-bound ProcessingBinding拥有 | v1 retirement后删除 |
| deleted external key | `永久保留` | `T-O-421` | recreate须新owner command |
| existing-object upgrade | `out-of-scope` | `T-O-420` | 独立upgrade charter |

---

## 3. 业务工作总表

> 每项的详细步骤见§4/§5；测试定义只在§8展开。新文件以 `(new)` 标记，既有落点均以 HEAD `ba099ee` 行号为准。

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| P1-01 | Phase 1 | 50债务/Truth/工作项coverage manifest | `add` | `docs/code-review/new-harvest/NH1-NH9-2nd-pass-review-VF-ledger.md:402-650`（只读）；`tests/fixtures/new_harvest_nhx1/coverage.v1.json` (new) | 每VF/deferred恰好一个工作项/Test-ID，无丢号/多owner | NHX1-T01 | high |
| P1-02 | Phase 1 | pre-fix DB + rev1 exact fixture | `add` | `src/workflows/kind_family.py:239-253`；`src/services/workflow_registry.py:152-210`；`tests/fixtures/new_harvest_nhx1/pre-fix-024.db` (new)；`tests/fixtures/new_harvest_nhx1/rev1-manifest.json` (new) | 可从真实pre-fix persisted形状升级，不靠空库 | NHX1-T02/NHX1-T09 | high |
| P1-03 | Phase 1 | adapter-aware harness与已知RED基线 | `refactor` | `src/persistence/ports.py:10-27`；`tests/unit/test_ns6_phase2.py:263-289`；现有e2e `sqlite3.connect`调用点 | inspector只走PersistencePort；现RED被固定、不得xfail | NHX1-T03/NHX1-T30 | high |
| P1-04 | Phase 1 | anti-fake-green/evidence command骨架 | `add` | `tests/domain/test_nh9_evidence_pack_checker.py:22-130`；`tests/domain/test_nhx1_evidence_pack.py` (new) | checker执行命令/校验commit、profile、digest、层级，不信PASS字符串 | NHX1-T01/NHX1-T30 | high |
| P2-01 | Phase 2 | Observation/attempt/ItemEpoch schema | `migrate` | `src/persistence/migrations/001_initial.sql:894-980`；`src/persistence/migrations/025_nhx1_observation_item_epoch.sql` (new) | Source/Observation/Snapshot/Item identity与CAS可由DDL表达 | NHX1-T02/NHX1-T04/NHX1-T05 | high |
| P2-02 | Phase 2 | object session/promotion/deletion schema | `migrate` | `src/persistence/migrations/021_nh4_upload_pending.sql:8-64`；`src/persistence/migrations/026_nhx1_object_sessions_cleanup.sql` (new) | session、staging/promotion、deletion job与exact ref owner可持久化 | NHX1-T02/NHX1-T15/NHX1-T16/NHX1-T20 | high |
| P2-03 | Phase 2 | evidence v2/correction/publication manifest | `migrate` | `src/persistence/migrations/018_nh2_selected_output_control.sql:6-35`；`src/persistence/migrations/019_nh3_representation_fact_history.sql:1-75`；`src/persistence/migrations/024_nh_review_invariants.sql:1-53`；`src/persistence/migrations/027_nhx1_evidence_v2.sql` (new) | immutable assertions与mutable projection分面；legacy verdict可追加 | NHX1-T02/NHX1-T10/NHX1-T17/NHX1-T19 | high |
| P2-04 | Phase 2 | outbox owner/receipt/registry projection schema | `migrate` | `src/persistence/migrations/001_initial.sql:140-380`；`src/persistence/migrations/028_nhx1_ops_contracts.sql` (new) | outbox/command owner generation、receipt、catalog projection有typed坐标 | NHX1-T02/NHX1-T14/NHX1-T24/NHX1-T25 | high |
| P2-05 | Phase 2 | read snapshot、migration state与shadow ports | `add` | `src/persistence/ports.py:10-27`；`src/persistence/migration_runner.py:81-163`；`src/persistence/sqlite_port.py:90-111`；`src/persistence/turso/port.py:135-205` | expand/backfill cursor、read_snapshot、shadow mismatch可实现且幂等 | NHX1-T02/NHX1-T19/NHX1-T26 | high |
| P3-01 | Phase 3 | Observation reservation与Task admission同UoW | `add` | `src/runtime/task/task_create.py:68-150,452-480`；`src/services/observation_reservations.py` (new) | 四kind并发至多一个winner，非法请求零Task/残留reservation | NHX1-T04 | high |
| P3-02 | Phase 3 | single Snapshot/Revision/ItemEpoch acceptance | `refactor` | `src/runtime/intake/acquisition_ingest.py:88-170,229-264`；`src/runtime/intake/acceptance_snapshot.py:139-245,397-453` | 每Observation独立Snapshot；head CAS；no-change显式；无悬挂ChangeSet | NHX1-T05 | high |
| P3-03 | Phase 3 | scatter先采纳identity + failed observation retry | `refactor` | `src/runtime/intake/acquisition_ingest.py:283-483`；`src/services/scatter_intake.py:143-221` | envelope只带稳定Observation；failed同key经attempt CAS恢复 | NHX1-T06 | high |
| P3-04 | Phase 3 | 7 intent×3 lifecycle/deleted key/late callback | `update` | `src/services/intake_lifecycle/targets.py:37-217`；`src/services/intake_lifecycle/lifecycle_apply.py:55-147`；`src/services/intake_lifecycle/lifecycle_publish.py:40-132` | 非法格admission 409零Task；tombstone保key；旧epoch不穿透 | NHX1-T07 | high |
| P3-05 | Phase 3 | index rebuild cardinality与noop result | `update` | `src/runtime/intake/index_rebuild_plan.py:245-288`；`src/runtime/task/task_views.py:61-94` | frozen target任一stale全Task fail；初始空才typed noop | NHX1-T08 | medium |
| P4-01 | Phase 4 | checked-in rev1 + rev2 registry/capability compat | `update` | `src/workflows/kind_family.py:239-253`；`src/services/workflow_registry.py:152-227`；`tests/fixtures/new_harvest_nhx1/rev1-manifest.json` (new)；`src/workflows/kind_family_v1_compat.py` (new) | persisted rev1启动/retry不503；新Task只选rev2 | NHX1-T09 | high |
| P4-02 | Phase 4 | ProcessingBinding union + selected fact公式 | `refactor` | `src/contracts/intake/strategies.py:15-212`；`intake/api/registry.py:35-129`；`src/runtime/binding/actual_s05.py:16-136`；`src/runtime/workflow/runtime_materialize.py:842-920` | 10+3各自registry可解析；selection使用真实fact digest | NHX1-T10 | high |
| P4-03 | Phase 4 | terminal Outcome fence与worker错误分族 | `refactor` | `src/runtime/workflow/runtime_outcome.py:38-180,487-541`；`src/runtime/workflow/runtime_materialize.py:400-490`；`src/runtime/workflow/worker.py:80-140` | terminal owner拒绝迟到Outcome/新Process；domain failure不留running | NHX1-T11 | critical |
| P4-04 | Phase 4 | current-hop route reachability | `refactor` | `src/runtime/workflow/runtime_materialize.py:50-124`；`src/workflows/kind_family.py:448-586` | route只看当前hop compiled candidates；无整图guard特判 | NHX1-T12 | high |
| P4-05 | Phase 4 | frozen full retry/resume与typed context | `refactor` | `src/runtime/task/task_commands.py:237-353`；`src/runtime/intake/acquisition_ingest.py:558-701` | durable acquire后retry零外部调用；无frozen input typed拒绝 | NHX1-T13 | critical |
| P4-06 | Phase 4 | outbox owner/dead terminal policy | `refactor` | `src/runtime/workflow/runtime_outbox.py:343-428`；`src/runtime/workflow/runtime_repair.py:74-141` | critical dead同UoW终结owner；advisory显式；requeue保留predecessor | NHX1-T14 | high |
| P5-01 | Phase 5 | upload session contract/service/API | `refactor` | `src/contracts/api/objects.py:12-24`；`src/services/object_upload.py:33-180`；`api/public/routes.py:120-169` | same命令同session、同bytes新命令独立；exact cancel/stat receipt | NHX1-T15 | high |
| P5-02 | Phase 5 | promotion journal与GC deletion job | `refactor` | `src/storage/local_store.py:72-150,186-259`；`src/services/object_gc.py:134-317` | promote/catalog与quarantine/tombstone任一crash可恢复/销毁 | NHX1-T16 | critical |
| P5-03 | Phase 5 | evidence immutability/correction/formula versions | `refactor` | `src/runtime/workflow/selected_output.py:53-124`；`src/runtime/workflow/runtime_materialize.py:872-920`；`src/persistence/migrations/024_nh_review_invariants.sql:22-51` | SQL不可改identity；旧错值有verdict/correction；formula可重算 | NHX1-T17 | high |
| P5-04 | Phase 5 | CAS-first stage envelope与递归拒密 | `refactor` | `src/runtime/intake/core.py:398-440`；`src/contracts/common/models.py:24-36,110-144`；`src/services/config_snapshots.py:408-478` | stage/audit无正文/secret；只存Team-scoped refs/digests | NHX1-T18 | high |
| P5-05 | Phase 5 | publication manifest与read_snapshot retrieval | `add` | `src/persistence/ports.py:10-27`；`src/runtime/intake/vector_publish_commit.py:130-210`；`src/services/retrieval/retrieval_rank.py:26-154,311-450` | pointer/proof/manifest/record在一致读中验证，TOCTOU fail-closed | NHX1-T19 | high |
| P5-06 | Phase 5 | cleanup executors/physical purge/holds | `add` | `src/services/intake_lifecycle/lifecycle_apply.py:125-147,265-305`；`src/services/index_retirement.py:1-34`；`src/services/cleanup_jobs.py` (new) | 三substrate均terminal；exact refs释放；hold可见阻塞；bytes收敛 | NHX1-T20 | critical |
| P6-01 | Phase 6 | explicit deployment roles/lifespan | `refactor` | `src/runtime/config.py:12-70`；`api/app.py:586-658`；`src/runtime/roles.py` (new) | 每role只启动所属loop；all为显式组合 | NHX1-T21 | high |
| P6-02 | Phase 6 | ProcessCapabilityManifest与claim过滤 | `add` | `src/contracts/workflow/models.py:379-430`；`src/runtime/intake/core.py:359-396`；`src/runtime/workflow/capability_registry.py` (new) | required process都有handler/role/supply/replay law；unknown拒绝 | NHX1-T21/NHX1-T22 | high |
| P6-03 | Phase 6 | role readiness/CW/supervisor signals | `refactor` | `src/runtime/health.py:15-121`；`src/persistence/turso/port.py:176-205`；`src/runtime/workflow_supervisor.py:20-83` | required=false/true诚实；failure threshold使worker not-ready | NHX1-T21/NHX1-T25 | high |
| P6-04 | Phase 6 | prod 10+3 supply与process-tree安全 | `update` | `src/runtime/config.py:40-95`；`api/app.py:450-489`；`src/runtime/supply/browser.py:220-292`；`src/runtime/supply/deterministic_ocr.py:45-193`；`src/runtime/supply/pdf_parser.py:90-150` | prod零stub；真实identity/readiness；no-sandbox/egress/kill与pool fence | NHX1-T22 | critical |
| P7-01 | Phase 7 | strict public workflow/capability/Task catalog | `add` | `api/public/routes.py:228-330`；`src/contracts/api/models.py:640-667`；`src/services/workflow_catalog.py` (new) | OpenAPI strict；caller可发现但不能提交workflow key | NHX1-T23 | high |
| P7-02 | Phase 7 | Item/Namespace/list filters与single/waiting投影 | `update` | `src/runtime/task/task_views.py:34-94,202-235`；`src/runtime/task/task_projections.py:17-125`；`src/services/retrieval/retrieval_request.py:375-431` | cold-start可经API得namespace；single outcome/phase/reason正确 | NHX1-T23 | medium |
| P7-03 | Phase 7 | operator debug/control/CommandReceipt | `add` | `api/internal/routes.py:11-161`；`src/services/observability.py:246-465`；`src/services/operator_control.py` (new) | debug有界redacted；restart/stop/requeue/repair CAS+audit+receipt | NHX1-T24 | high |
| P7-04 | Phase 7 | diagnostics/metrics/alerts/error registry | `refactor` | `src/runtime/metrics.py:80-229`；`src/contracts/common/errors.py:70-109`；`src/runtime/workflow_supervisor.py:42-83` | catalog-emitter-alert-runbook零孤儿；v2 code统一且legacy alias可读 | NHX1-T25 | high |
| P8-01 | Phase 8 | shadow验证与new-admission cutover | `migrate` | `src/services/nhx1_cutover.py` (new)；`src/runtime/task/task_create.py:68-150`；`api/app.py:586-602` | mismatch=0后才切v2；旧writer不可复活；cutover可观测 | NHX1-T26 | critical |
| P8-02 | Phase 8 | rev1/evidence/alias pin inventory与retire | `remove` | `api/app.py:427-440`；`src/services/workflow_registry.py:152-227`；`src/services/evidence_verification.py` (new) | zero pin/ref/outbox/restart+retention后disable旧入口，历史仍可解释 | NHX1-T09/NHX1-T17/NHX1-T26 | high |
| P8-03 | Phase 8 | cleanup drain、dead enum/old writer删除与rollback drill | `remove` | `src/services/cleanup_jobs.py` (new)；`src/persistence/migrations/027_nhx1_evidence_v2.sql` (new)；`src/services/nhx1_cutover.py` (new) | open jobs=0；无old writer/reader；停admission+前滚演练通过 | NHX1-T20/NHX1-T26 | high |
| P9-01 | Phase 9 | graph-derived closed-set manifest/L1–L4 | `add` | `src/contracts/workflow/models.py:379-430`；`src/runtime/workflow/capability_registry.py` (new)；`tests/fixtures/new_harvest_nhx1/manifest.v1.json` (new) | 每reachable edge/10+3/intent均有正负cell和最低层 | NHX1-T27 | high |
| P9-02 | Phase 9 | deterministic race soak | `add` | `tests/e2e/test_nhx1_race_soak.py` (new)；`tests/e2e/test_nh4_upload_replay_race.py:21-300`；`tests/e2e/test_new_harvest_crash_windows.py:91-390` | identity/epoch/outcome/session/outbox多序列effect-once | NHX1-T28 | high |
| P9-03 | Phase 9 | subprocess crash + persisted upgrade mega | `add` | `tests/e2e/test_nhx1_subprocess_crash.py` (new)；`tests/fixtures/new_harvest_nhx1/pre-fix-024.db` (new) | hook之外真实kill/restart；旧库升级/old pin/retry/cleanup收敛 | NHX1-T29 | critical |
| P9-04 | Phase 9 | full repo/evidence executor/第三轮review/closure | `add` | `tests/domain/test_nhx1_evidence_pack.py` (new)；`docs/evidence/new-harvest/AP-NHX1/` | current commit全仓无排除绿；30 tests四元组；零in-scope debt | NHX1-T30 | critical |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — Truth denominator / fixtures / harness

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P1-01 | Coverage manifest | a) 解析VF1–52分类与历史deferred；b) 把每项绑定唯一work/Test/Truth；c) 反查无漏号/重复owner；d) 冻结manifest digest；e) 生成Phase/closure查询视图 | `docs/code-review/new-harvest/NH1-NH9-2nd-pass-review-VF-ledger.md:402-650`；`tests/fixtures/new_harvest_nhx1/coverage.v1.json` (new) | 50债务+VF27/VF52 guards均有唯一落点 | NHX1-T01 | coverage checker EXIT0，计数15/18/17/2一致 |
| P1-02 | Pre-fix fixtures | a) 从pre-fix schema/registry构造真实DB；b) 保存rev1 canonical/compiled digest；c) 写fixture metadata/commit；d) 防止当前builder重算伪fixture；e) 加checksum gate | `src/workflows/kind_family.py:239-253`；`src/services/workflow_registry.py:152-210`；`tests/fixtures/new_harvest_nhx1/pre-fix-024.db` (new)；`tests/fixtures/new_harvest_nhx1/rev1-manifest.json` (new) | 可复现upgrade 503与legacy evidence形状 | NHX1-T02/NHX1-T09 | fixture在修前触发预期RED，且checksum固定 |
| P1-03 | Honest persistence harness | a) 枚举e2e中raw sqlite直读；b) 新增PersistenceInspectorPort；c) 迁用例；d) 固定stale-fence RED；e) 禁止xfail/skip改绿 | `src/persistence/ports.py:10-27`；`tests/unit/test_ns6_phase2.py:263-289`；`tests/e2e/test_ns2_dispatch_lanes.py:80-141`；`tests/e2e/test_human_review_gate.py:120`；`tests/e2e/test_ns1_pipeline.py:115` | Turso测试不再用sqlite3-on-Turso；current RED可证伪 | NHX1-T03/NHX1-T30 | raw driver扫描零违规；known RED修前可复现 |
| P1-04 | Evidence executor / fake-green rules | a) 定义命令清单与层级；b) 实际执行并捕获exit/UTC/profile；c) 校验commit/digest；d) 检测skip/xfail/monkeypatch/PASS字符串；e) 输出machine-readable report | `tests/domain/test_nh9_evidence_pack_checker.py:22-130`；`tests/domain/test_nhx1_evidence_pack.py` (new) | 历史文件存在/PASS文本不能冒充执行证据 | NHX1-T01/NHX1-T30 | 注入假SHA/假PASS/skip时checker必须RED |

### 4.2 Phase 2 — Canonical schema / ports / registries

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P2-01 | Observation + ItemEpoch DDL | a) 新Observation/Attempt表；b) unique source+key/state checks；c) Snapshot FK；d) 明确row_revision=ItemEpoch；e) legacy projection/backfill verdict；f) indexes | `src/persistence/migrations/001_initial.sql:894-980`；`src/persistence/migrations/025_nhx1_observation_item_epoch.sql` (new) | DDL能表达reservation/attempt/accepted坐标，旧行不伪造attempt | NHX1-T02/NHX1-T04/NHX1-T05 | 空库+pre-fix库迁移绿；约束攻击RED |
| P2-02 | Object session/cleanup DDL | a) upload session/staging/promotion状态；b) exact pending ref FK；c) reserved Task owner；d) deletion/cleanup jobs；e) proof/predecessor/indexes；f) legacy pending verdict | `src/persistence/migrations/021_nh4_upload_pending.sql:8-64`；`src/persistence/migrations/026_nhx1_object_sessions_cleanup.sql` (new) | handle/session/ref/job分账，crash状态有名 | NHX1-T02/NHX1-T15/NHX1-T16/NHX1-T20 | DDL state matrix、FK、unique/transition攻击全绿 |
| P2-03 | Evidence v2 DDL | a) selection assertion v2/fact digest；b) verification/correction/supersedes；c) publication manifest；d) vector identity/projection分面；e) immutable triggers；f) formula version | `src/persistence/migrations/018_nh2_selected_output_control.sql:6-35`；`src/persistence/migrations/019_nh3_representation_fact_history.sql:1-75`；`src/persistence/migrations/024_nh_review_invariants.sql:1-53`；`src/persistence/migrations/027_nhx1_evidence_v2.sql` (new) | 旧事实只获verdict，新事实append-only且可重算 | NHX1-T02/NHX1-T10/NHX1-T17/NHX1-T19 | direct SQL update/delete全部按分类拒绝 |
| P2-04 | Ops owner/receipt/catalog schema | a) outbox owner/policy/generation；b) command receipt；c) capability/catalog projection；d) error alias/version；e) signal ownership；f) indexes/retention class | `src/persistence/migrations/001_initial.sql:140-380`；`src/persistence/migrations/028_nhx1_ops_contracts.sql` (new) | control/ops不再靠payload猜owner或HTTP status猜结果 | NHX1-T02/NHX1-T14/NHX1-T24/NHX1-T25 | schema roundtrip + owner/ref integrity全绿 |
| P2-05 | Ports + migration state/shadow | a) `read_snapshot()`；b) migration phase/cursor；c) dual writer mismatch record；d) shadow reader；e) idempotent resume；f) adapter parity | `src/persistence/ports.py:10-27`；`src/persistence/migration_runner.py:81-163`；`src/persistence/sqlite_port.py:90-111`；`src/persistence/turso/port.py:135-205` | expand/backfill/validate/cutover可停可续且跨adapter一致 | NHX1-T02/NHX1-T19/NHX1-T26 | 中断重跑不重复/不漏；shadow mismatch可观测 |

### 4.3 Phase 3 — Intake identity / ItemEpoch / lifecycle

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P3-01 | Admission reservation | a) 解析v1/v2 observation key；b) 同UoW adopt Source+reserve Observation+Task/root；c) exact replay receipt；d) active/conflict paths；e) rollback零残留 | `src/runtime/task/task_create.py:68-150,452-480`；`src/services/observation_reservations.py` (new) | 并发同Observation至多一个201；其它为stable replay/409 | NHX1-T04 | 四kind顺序/并发矩阵与DB计数全绿 |
| P3-02 | Single acceptance + epoch | a) 不再按external key复用Snapshot；b) fingerprint/attempt fence；c) Revision adopt/no-change；d) latest CAS；e) ChangeSet回读失败即rollback；f)传新epoch | `src/runtime/intake/acceptance_snapshot.py:139-245,397-453` | 新Observation新Snapshot，head不LWW，ChangeSet无假UUID | NHX1-T05 | changed/no-change/concurrent均满足数量+lineage断言 |
| P3-03 | Scatter + failed retry | a) material前resolve durable identity；b) envelope仅stable UUID/ref；c)失败attempt terminal；d)typed retry CAS；e)child继承exact coords；f)accepted replay | `src/runtime/intake/acquisition_ingest.py:283-483`；`src/services/scatter_intake.py:143-221` | retry不再SOURCE_MISSING，失败key有合法恢复出口 | NHX1-T06 | scatter fail→retry→accept完整e2e绿，零随机UUID漂移 |
| P3-04 | Lifecycle/applicability | a) 固化7×3矩阵；b) require_active；c)同态新命令409、同command replay；d)deleted key early reject；e)callback expected epoch；f)cancel first-wins | `src/services/intake_lifecycle/targets.py:37-217`；`src/services/intake_lifecycle/lifecycle_apply.py:55-147`；`src/services/intake_lifecycle/lifecycle_publish.py:40-132` | 非法格零Task；delete/reactivate不被迟到accept/publish穿透 | NHX1-T07 | 21格+race全部绿，transition前后值真实 |
| P3-05 | Rebuild cardinality/noop | a) 冻结target set/count；b)执行重检任一stale整体fail；c)禁止continue；d)初始空typed noop；e)投影counts/mode；f)metrics分类 | `src/runtime/intake/index_rebuild_plan.py:245-288`；`src/runtime/task/task_views.py:61-94` | success count=冻结count，noop/failed可读，不假success | NHX1-T08 | stale subset不能succeeded；empty只在初始空成立 |

### 4.4 Phase 4 — Workflow revision / replay / Outcome

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P4-01 | rev1 exact + rev2 | a) fixture loader；b)当前kind升rev2；c)bootstrap验证rev1/rev2/capability；d)new resolver只选rev2；e)old plan load；f)pin inventory | `src/workflows/kind_family.py:225-253`；`src/services/workflow_registry.py:152-227`；`api/app.py:427-440` | 已有库不503，new/old各走exact revision | NHX1-T09 | persisted rev1启动、执行、retry与new rev2全绿 |
| P4-02 | ProcessingBinding + selection | a) union schema；b)10 strategy/3 op resolver；c)actual formula v2；d)selection从fact读取；e)same seal replay；f)projection/catalog | `src/contracts/intake/strategies.py:15-212`；`intake/api/registry.py:35-129`；`src/runtime/binding/actual_s05.py:16-136`；`src/runtime/workflow/selected_output.py:53-124` | registered API不冒充第11策略，digest代数唯一 | NHX1-T10 | 13 cells均可解析且selection重算一致 |
| P4-03 | Outcome terminal/worker errors | a) Process+Execution+Task generation active check；b)current_process fence；c)committer后CAS；d)materialize rowcount；e)Fence/Lease/Domain错误分族；f)独立fence diagnostic | `src/runtime/workflow/runtime_outcome.py:38-180,487-541`；`src/runtime/workflow/runtime_materialize.py:400-490`；`src/runtime/workflow/worker.py:80-140` | terminal后零业务写/零新Process；domain失败terminal | NHX1-T11 | late same/different outcome与策略mismatch全绿 |
| P4-04 | Current-hop reachability | a) compiler产hop matrix；b)runtime只取from-step candidates；c)删除plan-wide guard hack；d)unknown/absent fail-closed；e)strategy constraint验证；f)digest入rev2 | `src/runtime/workflow/runtime_materialize.py:50-124`；`src/workflows/kind_family.py:448-586` | browser/reacquire/print/clean边仅按当前hop决定 | NHX1-T12 | 每声明边正例、每无边负例，无全图误杀 |
| P4-05 | Exact full retry | a)识别frozen acquire；b)选择resume step；c)复制typed context；d)禁止fetch/API enumerator；e)无input typed reject；f)receipt/lineage | `src/runtime/task/task_commands.py:237-353`；`src/runtime/intake/acquisition_ingest.py:558-701` | upstream变化不改变retry bytes/actual，metadata no-change不丢 | NHX1-T13 | mutate source后call_count=0且结果exact；no-input拒绝 |
| P4-06 | Outbox owner/dead | a)enqueue写owner/policy；b)dead CAS；c)critical owner terminalize；d)advisory event；e)requeue新generation/predecessor；f)repair识别dead | `src/runtime/workflow/runtime_outbox.py:343-428`；`src/runtime/workflow/runtime_repair.py:74-141`；`src/services/operator_control.py` (new) | poison不再让owner永久ready；original dead evidence保留 | NHX1-T14 | critical/advisory/requeue/stale generation矩阵全绿 |

### 4.5 Phase 5 — Object / evidence / physical convergence

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P5-01 | Upload session API | a) idempotency/session token；b)receiving+staging_id；c)stream/prepared/promoted/committed；d)strict response/receipt；e)stat/cancel by session；f)cross-team fence | `src/contracts/api/objects.py:12-24`；`src/services/object_upload.py:33-180`；`src/services/object_upload_ttl.py:40-92`；`api/public/routes.py:120-169` | 同命令effect-once；同bytes独立会话互不取消 | NHX1-T15 | replay/cancel/TTL/consume/session auth全绿 |
| P5-02 | Promotion/GC job | a)journal reconcile receiving/prepared/promoted；b)CAS inventory归因；c)deletion selected/quarantined/tombstoned/destroyed；d)restore/destroy分支；e)missing bytes integrity；f)scanner metrics | `src/storage/local_store.py:72-150,186-259`；`src/services/object_gc.py:134-189,218-366` | 任一crash后无invisible final/quarantine | NHX1-T16 | process kill后文件+DB状态最终收敛 |
| P5-03 | Evidence plane | a)writer统一formula；b)legacy verify；c)correction assertion；d)immutable triggers；e)vector identity split；f)operator evidence status | `src/runtime/workflow/selected_output.py:53-124`；`src/runtime/workflow/runtime_materialize.py:872-920`；`src/persistence/migrations/024_nh_review_invariants.sql:22-51` | 普通SQL不能伪造verified事实，旧错值不被改写 | NHX1-T17 | SQL攻击、重算、legacy verdict/correction全绿 |
| P5-04 | CAS-first envelope/security | a) raw/clean/records先CAS；b)stage只refs/digests/facts；c)公共nested递归拒密；d)URL safe identity；e)audit redaction；f)legacy reader drain marker | `src/runtime/intake/core.py:398-440`；`src/contracts/common/models.py:24-36,110-144`；`src/services/config_snapshots.py:408-478` | DB/CAS metadata不复制sentinel secret/body | NHX1-T18 | 全链攻击后DB/audit/envelope扫描零泄漏 |
| P5-05 | Publication manifest/read snapshot | a)ordered vector identity manifest；b)proof/pointer引用；c)read_snapshot；d)命中membership验证；e)background full auditor；f)invalid fail-closed | `src/runtime/intake/vector_publish_commit.py:130-210`；`src/persistence/ports.py:10-27`；`src/services/retrieval/retrieval_rank.py:26-154,311-450` | mutable row/TOCTOU不能骗过retrieval proof | NHX1-T19 | 并发篡改/withdraw下query零假hit |
| P5-06 | Cleanup convergence | a)冻结owner graph；b)三executor；c)retention/hold；d)exact ref release；e)GC job handoff；f)status/retry/proof | `src/services/intake_lifecycle/lifecycle_apply.py:125-147,265-305`；`src/services/index_retirement.py:1-34`；`src/services/cleanup_jobs.py` (new) | logical delete后refs/jobs/bytes在policy内terminal | NHX1-T20 | search立即zero；retention后refs/bytes zero或typed blocked |

### 4.6 Phase 6 — Capability / role / readiness / security

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P6-01 | Deployment roles | a) role config；b)composition ownership；c)role loop start/stop；d)all组合；e)lease owner identity；f)shutdown | `src/runtime/config.py:12-70`；`api/app.py:586-658`；`src/runtime/roles.py` (new) | api不claim、worker不跑GC、maintenance不执行业务 | NHX1-T21 | 四role正负loop/readiness测试全绿 |
| P6-02 | Capability manifest | a)编译required process；b)handler/contract/role/supply/replay元数据；c)registry拒unknown；d)claim filter；e)catalog projection；f)digest/version | `src/contracts/workflow/models.py:379-430`；`src/runtime/intake/core.py:359-396`；`src/runtime/workflow/capability_registry.py` (new) | 图声明与部署供给可比对，unknown无法bootstrap | NHX1-T21/NHX1-T22 | 每required process恰一实现/owner，缺件不claim |
| P6-03 | Honest readiness | a)按role合成required；b)CW profile；c)supply probe；d)supervisor threshold；e)cache fingerprint；f)signals | `src/runtime/health.py:15-121`；`src/persistence/turso/port.py:176-205`；`src/runtime/workflow_supervisor.py:20-83` | 配置required=false/true与overall一致，不再false仍ready | NHX1-T21/NHX1-T25 | 正负矩阵与故障恢复全绿 |
| P6-04 | Production 10+3/security | a)prod禁stub；b)真实parser/browser/OCR/model identity；c)actual args no-sandbox；d)egress/limits；e)process-group kill；f)bounded pool/heartbeat | `src/runtime/config.py:40-95`；`api/app.py:450-489`；`src/runtime/supply/browser.py:220-292`；`src/runtime/supply/deterministic_ocr.py:45-193`；`src/runtime/supply/pdf_parser.py:90-150` | 13 cells具备真实可claim供给；缺owner签收时blocked | NHX1-T22 | 非stub L3/L4 + S16负样本 + kill/backpressure绿 |

### 4.7 Phase 7 — Discovery / control / observability / errors

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P7-01 | Public catalog/Task strict view | a)response models；b)workflow/kind/strategy/op/capability endpoints；c)Task actual/observation/phase/retryable；d)cursor/version；e)禁select fields；f)OpenAPI | `api/public/routes.py:228-330`；`src/contracts/api/models.py:640-667`；`src/services/workflow_catalog.py` (new) | upstream可发现、轮询、解释，不能选图 | NHX1-T23 | OpenAPI无空schema/additionalProperties；禁字段422 |
| P7-02 | Item/Namespace/list projection | a)team-scoped lists；b)source_kind/external/status filters；c)cold-start namespace；d)single root outcome；e)waiting reason；f)cross-team防枚举 | `src/runtime/task/task_views.py:34-94,202-235`；`src/runtime/task/task_projections.py:17-125`；`src/services/retrieval/retrieval_request.py:375-431` | 前端无SQL完成intake→search与status解释 | NHX1-T23 | cold-start journey与single/scatter/waiting矩阵绿 |
| P7-03 | Operator debug/control | a)Process/Stage/Fact/Selection/Cleanup reads；b)registered redaction；c)restart/stop/requeue/repair/resume；d)expected generation；e)receipt；f)audit | `api/internal/routes.py:11-161`；`src/services/observability.py:246-465`；`src/services/operator_control.py` (new) | operator可恢复而不能任意SQL/改terminal行 | NHX1-T24 | auth/CAS/stale/replay/secret负例全绿 |
| P7-04 | Signals/error registry | a)canonical error definitions/aliases；b)event/metric/alert/runbook五元组；c)补emitter或删dead metric；d)supervisor/GC/admission signals；e)diagnostic read；f)retention | `src/runtime/metrics.py:80-229`；`src/contracts/common/errors.py:70-109`；`src/services/observability.py:73-246`；`src/runtime/workflow_supervisor.py:20-83` | catalog-emitter-alert零孤儿，前端直接读retryable | NHX1-T25 | static双向扫描+runtime emission/alert/error alias全绿 |

### 4.8 Phase 8 — Cutover / compat drain / retirement

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P8-01 | Shadow→cutover | a)dual-write mutable authority/projection；b)shadow compare；c)mismatch gate；d)new admission切换；e)health/metric；f)stop-admission rollback | `src/services/nhx1_cutover.py` (new)；`src/runtime/task/task_create.py:68-150`；`api/app.py:586-602` | mismatch=0才切；cutover可停可续，旧writer不复活 | NHX1-T26 | 中断/重启/rollback drill与adapter parity绿 |
| P8-02 | Legacy inventory/retire | a)统计rev1/alias/evidence verdict/outbox/restart；b)zero-use gates；c)disable旧selector/writer；d)保留reader/manifest；e)retention；f)证据 | `api/app.py:427-440`；`src/services/workflow_registry.py:152-227`；`src/services/evidence_verification.py` (new) | 新writer唯一，old历史仍可读/重放，零误删 | NHX1-T09/NHX1-T17/NHX1-T26 | 有pin时retire rollback；zero后成功且old read绿 |
| P8-03 | Cleanup drain/remove dead shape | a)完成open jobs；b)删除unused enum/writers；c)全仓reader scan；d)contract migration；e)forward rollback演练；f)文档inventory | `src/services/cleanup_jobs.py` (new)；`src/persistence/migrations/027_nhx1_evidence_v2.sql` (new)；`src/services/nhx1_cutover.py` (new) | open job=0，无old writer/reader/dead capability | NHX1-T20/NHX1-T26 | scan零命中、migrations checksum、cold restart绿 |

### 4.9 Phase 9 — Graph-derived assurance / closure

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P9-01 | Compiler-derived closed set | a)从rev2/capability/error/intent registries生成cells；b)标最低层；c)正负route；d)digest；e)coverage join；f)禁止手写缩减 | `src/contracts/workflow/models.py:379-430`；`src/runtime/workflow/capability_registry.py` (new)；`tests/fixtures/new_harvest_nhx1/generate_manifest.py` (new) | 每reachable edge、10+3、7 intent/state均有Test-ID | NHX1-T27 | generator重复运行字节稳定，coverage 100% |
| P9-02 | Race soak | a)barrier枚举identity/epoch/outcome/session/outbox；b)多seed；c)DB owner/effect断言；d)无sleep判定；e)failure capture；f)N次 | `tests/e2e/test_nhx1_race_soak.py` (new)；`tests/e2e/test_nh4_upload_replay_race.py:21-300`；`tests/e2e/test_new_harvest_crash_windows.py:91-390` | 多ordering下effect-once/fail-loud且无hang | NHX1-T28 | 固定N/seed全绿；任一未知态FAIL |
| P9-03 | Process crash/upgrade mega | a)真实子进程app/worker；b)kill指定窗；c)cold restart；d)pre-fix DB migration；e)old/new retry；f)file/DB reconcile | `tests/e2e/test_nhx1_subprocess_crash.py` (new)；`tests/fixtures/new_harvest_nhx1/pre-fix-024.db` (new) | hook外真实恢复、旧库升级、物理收敛均成立 | NHX1-T29 | 每窗冷启terminal/安全pending，无孤儿/假proof |
| P9-04 | Full/evidence/review/closure | a)ruff/type/schema；b)全pytest无排除；c)执行30 Test-ID命令；d)核SHA/UTC/profile；e)第三轮review；f)closure/ledger回填 | `tests/domain/test_nhx1_evidence_pack.py` (new)；`docs/evidence/new-harvest/AP-NHX1/` (new)；`docs/closure/new-harvest/AP-NHX1-coherent-debt-retirement-and-governance.md` (new) | 零in-scope debt、零假绿、owner gate齐 | NHX1-T30 | checker EXIT0 + third review无未解释critical/high |

---

## 5. Phase 详情

### 5.1 Phase 1 — Truth denominator / fixtures / harness

- **Phase目标**：在任何生产改动前，把问题分母、旧数据、旧图和测试真实性冻结为可执行入口。
- **本Phase对应编号**：P1-01..P1-04
- **本Phase新增文件**：`tests/fixtures/new_harvest_nhx1/coverage.v1.json`、`pre-fix-024.db`、`rev1-manifest.json`、`tests/domain/test_nhx1_truth_and_coverage.py`、`tests/domain/test_nhx1_harness_integrity.py`、`tests/domain/test_nhx1_evidence_pack.py`
- **本Phase修改文件**：`src/persistence/ports.py:10-27`；`tests/e2e/test_ns2_dispatch_lanes.py:80-141`；`tests/e2e/test_human_review_gate.py:120`；`tests/e2e/test_ns1_pipeline.py:115`；`tests/unit/test_ns6_phase2.py:263-289`；不改生产业务writer
- **具体功能预期**：
  1. VF1–52、第一轮NH deferred、直接NS carry-over与Q28–42均被machine manifest引用。
  2. manifest强制15 true-bug、18 partial、17 absorbed deferred、2 n/a计数。
  3. pre-fix fixture保存schema migration ledger、rev1 canonical/compiled digest与代表性legacy rows，不从当前builder反向生成。
  4. `test_stale_fencing_fail_does_not_kill_new_generation` 在修前仍RED并被登记，不得xfail或删断言。
  5. Turso e2e inspection全部经port，raw `sqlite3.connect(settings.resolved_database_path)`列为架构违规。
  6. evidence checker遇到伪SHA、只写PASS、skip/xfail、层级降级或非当前commit必须失败。
- **对应测试台账项**：NHX1-T01/NHX1-T02/NHX1-T03/NHX1-T30
- **收口标准**：coverage/fixture/harness/checker短途全绿；业务修前反例按预期RED；Phase 2才可开工。
- **本Phase风险提醒**：不能为了让Phase EXIT全绿而把“预期RED”改成xfail；NHX1-T03的PASS是“RED被正确捕获并登记”，不是bug已修。

### 5.2 Phase 2 — Canonical schema / ports / registries

- **Phase目标**：以forward-only migration建立所有后续Phase共享的durable形状，尚不切public writer。
- **本Phase对应编号**：P2-01..P2-05
- **本Phase新增/修改文件**：`src/persistence/migrations/025_nhx1_observation_item_epoch.sql`、`026_nhx1_object_sessions_cleanup.sql`、`027_nhx1_evidence_v2.sql`、`028_nhx1_ops_contracts.sql` (all new)；`src/persistence/ports.py:10-27`；`src/persistence/migration_runner.py:81-163`；`src/persistence/sqlite_port.py:90-111`；`src/persistence/turso/port.py:135-205`；new observation/session/evidence/ops contract modules
- **具体功能预期**：
  1. 旧库迁移不伪造当时不存在的Observation attempt、actual、session或evidence；使用legacy verdict。
  2. 所有state/check/unique/FK在SQLite和Turso adapter下等价。
  3. immutable evidence与mutable projection分类可由schema inventory checker验证。
  4. backfill cursor/phase durable，任意中断可幂等继续。
  5. `read_snapshot()`为retrieval提供一致读，不暴露driver给service。
  6. shadow mismatch具备低基数metric/diagnostic，任何非零阻断cutover。
  7. migration只新增025+；001/018–024 checksum不得修改。
- **对应测试台账项**：NHX1-T02/NHX1-T04/NHX1-T05/NHX1-T10/NHX1-T14/NHX1-T15/NHX1-T17/NHX1-T19/NHX1-T20/NHX1-T24/NHX1-T25/NHX1-T26
- **收口标准**：空库、pre-fix库、中断重跑、adapter parity、DDL attack全部PASS；Phase 3前public行为仍兼容。
- **本Phase风险提醒**：不要在migration中UPDATE旧evidence成新公式；不要同时切writer，避免schema和业务错误难归因。

### 5.3 Phase 3 — Intake identity / ItemEpoch / lifecycle

- **Phase目标**：让四通道admission、Observation、Snapshot、Revision与Item mutation具有唯一owner和恢复出口。
- **本Phase对应编号**：P3-01..P3-05
- **本Phase新增/修改文件**：`src/runtime/task/task_create.py:68-150,452-480`；`src/services/observation_reservations.py` (new)；`src/runtime/intake/acquisition_ingest.py:88-170,229-483`；`src/runtime/intake/acceptance_snapshot.py:139-245,397-453`；`src/services/scatter_intake.py:143-221`；`src/services/intake_lifecycle/targets.py:37-217`；`src/services/intake_lifecycle/lifecycle_apply.py:55-147`；`src/services/intake_lifecycle/lifecycle_publish.py:40-132`；`src/runtime/intake/index_rebuild_plan.py:245-288`；`src/runtime/task/task_views.py:61-94`
- **具体功能预期**：
  1. v2四通道显式observation key；v1兼容派生严格服从T-O-408。
  2. reservation与Task/root同UoW，unique冲突映射canonical 409且零残留。
  3. 不同Observation产生不同Snapshot；相同内容可复用Revision但必须记录no-change fact。
  4. ItemEpoch覆盖latest/serving/lifecycle，所有callback expected epoch；旧callback永不穿越delete/reactivate。
  5. failed Observation只能typed retry开新attempt，accepted永远terminal。
  6. 7×3非法格在Task前拒绝；same command replay与新no-op分开。
  7. index rebuild冻结分母，执行期skip任何target即整Task失败；初始空才noop。
- **对应测试台账项**：NHX1-T04–NHX1-T08
- **收口标准**：Phase 3全部e2e/race PASS；DB计数、transition、receipt、retrieval zero均可证；旧identity writer关闭。
- **本Phase风险提醒**：Observation接受失败后Snapshot可保留“已观察未采纳”事实，不能为追求清洁而删历史；避免把保守CAS冲突改为LWW。

### 5.4 Phase 4 — Workflow revision / replay / Outcome

- **Phase目标**：建立不可变图版本、正确actual binding、terminal monotonic和exact causal replay。
- **本Phase对应编号**：P4-01..P4-06
- **本Phase新增/修改文件**：`src/workflows/kind_family.py:225-253,448-586`；`src/workflows/kind_family_v1_compat.py` (new)；`src/services/workflow_registry.py:152-227`；`src/contracts/intake/strategies.py:15-226`；`intake/api/registry.py:35-129`；`src/runtime/binding/actual_s05.py:16-136`；`src/runtime/workflow/selected_output.py:53-124`；`src/runtime/workflow/runtime_materialize.py:50-124,400-490,842-920`；`src/runtime/workflow/runtime_outcome.py:38-180,487-541`；`src/runtime/workflow/worker.py:80-140`；`src/runtime/task/task_commands.py:237-353`；`src/runtime/workflow/runtime_outbox.py:343-428`；`src/runtime/workflow/runtime_repair.py:74-141`
- **具体功能预期**：
  1. rev1 exact定义永久可解释old pin，rev2承载所有新canonical变化。
  2. 10 strategies与3 operations分别由registry校验并聚合到typed actual。
  3. selected-output v2从durable fact取digest；route+seal+eligibility同Outcome UoW。
  4. terminal Execution/Task generation/current_process任一不匹配即拒绝Outcome，零后继Process。
  5. worker只把Fence/Lease conflict当stale，Domain conflict提交typed terminal failure。
  6. current-hop reachability完全来自compiler；删除plan-wide guard启发式。
  7. full retry从frozen artifact resume，复制metadata disposition等typed context；source call count为零。
  8. critical outbox dead同步终结owner；requeue保留dead predecessor且stale generation拒绝。
- **对应测试台账项**：NHX1-T09–NHX1-T14
- **收口标准**：persisted upgrade、route matrix、late Outcome、exact retry、dead owner全部PASS；Phase 5才可改commit/evidence路径。
- **本Phase风险提醒**：Outcome UoW中任何额外commit都会重开split-brain；不得用捕获所有ConflictError恢复稳定性。

### 5.5 Phase 5 — Object / evidence / physical convergence

- **Phase目标**：使字节、session、ref、事实、publication与物理删除在任意crash后都有可恢复状态。
- **本Phase对应编号**：P5-01..P5-06
- **本Phase新增/修改文件**：`src/contracts/api/objects.py:12-24`；`src/services/object_upload.py:33-180`；`src/services/object_upload_ttl.py:40-92`；`src/storage/local_store.py:72-150,186-259`；`src/services/object_gc.py:134-189,218-366`；`src/runtime/workflow/selected_output.py:53-124`；`src/runtime/intake/core.py:398-440`；`src/contracts/common/models.py:24-36,110-144`；`src/runtime/intake/vector_publish_commit.py:130-210`；`src/services/retrieval/retrieval_rank.py:26-154,311-450`；`src/services/cleanup_jobs.py` (new)
- **具体功能预期**：
  1. session token拥有exact pending，handle只代表bytes；同bytes多session隔离。
  2. receiving/prepared/promoted/committed/consumed/cancelled/expired/failed均可读且CAS转换。
  3. promote-before-catalog与tombstone-before-destroy均由durable job在冷启动收敛。
  4. selection/artifact/vector/publication identity不可普通SQL改写；旧错值保留并获verdict/correction。
  5. stage/audit只存refs/digests/facts；nested secret、signed URL、absolute path与正文sentinel不落库。
  6. publication manifest在read snapshot内约束retrieval命中，mutable state绕过无效。
  7. delete后立即search zero；retention后所有可释放ref/bytes收敛，hold以typed blocked展示。
- **对应测试台账项**：NHX1-T15–NHX1-T20
- **收口标准**：session/evidence/security/TOCTOU/cleanup/crash全绿；对象目录、quarantine、open cleanup无未知态。
- **本Phase风险提醒**：跨DB/FS不可假装原子；必须用journal/job恢复，不得把final CAS inventory当可随意删除目录扫描。

### 5.6 Phase 6 — Capability / role / readiness / security

- **Phase目标**：让workflow需求、role部署、claim资格、readiness和production签收分别可证。
- **本Phase对应编号**：P6-01..P6-04
- **本Phase新增/修改文件**：`src/runtime/config.py:12-105`；`src/runtime/roles.py` (new)；`api/app.py:215-271,427-489,586-658`；`src/runtime/workflow/capability_registry.py` (new)；`src/runtime/health.py:15-121`；`src/persistence/turso/port.py:176-205`；`src/runtime/workflow_supervisor.py:20-83`；`src/runtime/supply/browser.py:220-292`；`src/runtime/supply/deterministic_ocr.py:45-193`；`src/runtime/supply/pdf_parser.py:90-150`
- **具体功能预期**：
  1. api role零Process claim/maintenance loop；worker只claim所部署capability；maintenance不运行业务handler。
  2. all role是显式组合并通过相同contract，不是唯一部署模式。
  3. 每个required process恰有一个handler contract、role、supply、side-effect/replay law；unknown bootstrap fail。
  4. readiness required集合由role/profile生成；CW/supply/supervisor false真实影响overall。
  5. prod profile拒stub/fake OCR/固定handler作为closure；10+3使用pinned identity。
  6. browser实际args禁no-sandbox、non-root、每跳egress；parser/OCR无网且process group可kill。
  7. owner live/S16未签则`ready-for-owner-gate/blocked`，不得改变测试期待。
- **对应测试台账项**：NHX1-T21/NHX1-T22/NHX1-T25
- **收口标准**：四role和prod正负矩阵绿；NHX1-T22-E达到`ready-for-owner-gate`即可串行进入Phase 7；NHX1-T22-O未签时NHX1-T22整体不PASS且不解锁Phase 9 final closure。
- **本Phase风险提醒**：Phase 6代码可以完成但NHX1仍被外部gate阻塞；不得使用skip把外部缺件改成PASS。

### 5.7 Phase 7 — Discovery / control / observability / errors

- **Phase目标**：在不开放选图/raw debug/任意SQL的前提下，让上游、前端和operator完成发现、解释与恢复。
- **本Phase对应编号**：P7-01..P7-04
- **本Phase新增/修改文件**：`api/public/routes.py:109-576`；`api/internal/routes.py:11-161`；`src/contracts/api/models.py:640-667`；`src/runtime/task/task_views.py:34-94,202-235`；`src/runtime/task/task_projections.py:17-125`；`src/services/workflow_catalog.py` (new)；`src/services/operator_control.py` (new)；`src/services/observability.py:73-246,282-465`；`src/runtime/metrics.py:80-229`；`src/contracts/common/errors.py:70-109`
- **具体功能预期**：
  1. public catalog列source kind、workflow revision、10+3、required/deployed capabilities与availability。
  2. Task create schema仍零workflow/process/branch selector；恶意字段422。
  3. Task view可答Observation、actual、revision、item、phase/wait reason、result mode、retryable。
  4. Item/Namespace list支持team/filter/cursor；cold-start仅用API完成search。
  5. operator read有界且redacted；payload必须registered projection+digest。
  6. restart/stop/requeue/repair/cleanup resume带expected generation、idempotency和receipt，stale命令零effect。
  7. 每个metric/alert有emitter/runbook/test，或删除definition；error v2统一并保legacy alias。
- **对应测试台账项**：NHX1-T23–NHX1-T25
- **收口标准**：OpenAPI strict、cold-start、operator auth/control、signal/error双向扫描全部PASS；前端/operator无需SQL。
- **本Phase风险提醒**：debug数据面最易泄密；任何新增字段必须回到S16威胁模型和NHX1-T18攻击sentinel复跑。

### 5.8 Phase 8 — Cutover / compat drain / retirement

- **Phase目标**：从兼容双轨收敛到唯一v2 writer，同时保留旧事实解释和可演练的forward rollback。
- **本Phase对应编号**：P8-01..P8-03
- **本Phase新增/修改/删除文件**：`src/services/nhx1_cutover.py` (new)；`src/runtime/task/task_create.py:68-150`；`api/app.py:427-440,586-602`；`src/services/workflow_registry.py:152-227`；`src/services/evidence_verification.py` (new)；`src/services/cleanup_jobs.py` (new)；old writer/alias/unused pointer-state sites由Phase 8 inventory定位后逐文件登记删除
- **具体功能预期**：
  1. shadow mismatch持续为0并有观察窗口，才切new admission。
  2. cutover后任何old writer调用fail-loud且有signal；old reader仅服务legacy事实。
  3. rev1 pin、pending outbox、restart window、object refs、open cleanup、legacy verdict均可机器inventory。
  4. 有任何pin/ref/job时retire必须rollback；zero+retention后才disable/delete入口。
  5. legacy列/表不在解释窗口前物理删除；unused枚举/死metric等无consumer形状可删。
  6. rollback drill只能停admission并前滚；不得恢复old writer或UPDATE v2 evidence。
- **对应测试台账项**：NHX1-T09/NHX1-T17/NHX1-T20/NHX1-T26
- **收口标准**：new writer唯一、old read/old retry仍exact、inventory zero gate与rollback drill PASS，cold restart健康。
- **本Phase风险提醒**：过早contract migration不可逆；delete动作必须由zero-use证据和备份/retention双门驱动。

### 5.9 Phase 9 — Graph-derived assurance / closure

- **Phase目标**：证明当前系统而非历史claim满足所有Truth，并输出可执行、不可伪造的closure证据。
- **本Phase对应编号**：P9-01..P9-04
- **本Phase新增/修改文件**：`tests/fixtures/new_harvest_nhx1/generate_manifest.py`、`manifest.v1.json`、`race-seeds.v1.json`；`tests/e2e/test_nhx1_closed_set.py`、`test_nhx1_race_soak.py`、`test_nhx1_subprocess_crash.py`；`tests/domain/test_nhx1_evidence_pack.py`；`docs/evidence/new-harvest/AP-NHX1/`；第三轮review与closure (all new)；fork anchors见§8.2
- **具体功能预期**：
  1. closed-set由rev2 compiler/capability/error/intent registry生成，不手写缩分母。
  2. 每reachable edge有正例，每undeclared/illegal edge有零副作用负例；13 processing cells到L4或合法终态。
  3. race使用barrier/seed/state断言，不以sleep/HTTP status判定。
  4. crash至少一层真实kill API/worker/maintenance进程并冷启动；hook仅定位窗口。
  5. pre-fix DB从024前状态迁移到当前，old pin/retry/read与new Task均通过。
  6. full pytest在当前commit、无排除/xfail/adapter违规下绿；ruff/type/schema同绿。
  7. evidence checker实际运行NHX1-T01–NHX1-T30命令，校验commit/UTC/profile/digest/层；第三轮review无未解释critical/high。
  8. owner live/S16 gate具名；否则NHX1保持blocked且不生成closed verdict。
- **对应测试台账项**：NHX1-T27–NHX1-T30（并join NHX1-T01–NHX1-T26）
- **收口标准**：§10所有硬闸PASS且四元组齐；coverage未了结=0；输出evidence/closure并将AP状态改为executed。
- **本Phase风险提醒**：Phase 9第一次发现功能缺口时必须回到owner Phase修复，并重跑从该Phase到9的完整后继链；禁止在测试里放宽期待。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Q28 / `T-O-408` | `pre-NHX1-qna.md` | P2/P3：显式Observation、同UoW reservation、v1兼容 | STOP Phase 2，回QNA；不得以external key代替 |
| Q29 / `T-O-409` | 同上 | P2/P3/P5：单ItemEpoch贯穿accept/publish/lifecycle | STOP Phase 2；禁止新增平行counter |
| Q30 / `T-O-410` | 同上 | P4：full retry frozen resume、零外部调用 | STOP Phase 4；不得降为refetch |
| Q31 / `T-O-411` | 同上 | P1/P4/P8：rev1 fixture、rev2、新旧pin/retire | STOP Phase 1；不得改persisted rev1 |
| Q32 / `T-O-412` | 同上 | P2/P4/P7/P9：ProcessingBinding 10+3 union | STOP Phase 2；不得造第11 strategy |
| Q33 / `T-O-413` | 同上 | P2/P5：session/idempotency/ref/journal | STOP Phase 2；handle不得充session |
| Q34 / `T-O-414` | 同上 | P2/P5/P8：verification/correction/immutable split | STOP Phase 2；禁止UPDATE旧evidence |
| Q35 / `T-O-415` | 同上 | P7：public safe discovery + operator debug/control | STOP Phase 7；public仍禁workflow selector/raw debug |
| Q36 / `T-O-416` | 同上 | P6：四deployment roles及readiness | STOP Phase 6；不得用FastAPI title冒充role |
| Q37 / `T-O-417` | 同上 | P2/P5/P8：retention cleanup与physical convergence | STOP Phase 2；不得logical-only close |
| Q38 / `T-O-418` | 同上 | P2/P7/P8：v2 error registry+legacy aliases | STOP Phase 2；不得无兼容批量改v1 |
| Q39 / `T-O-419` | 同上 | P6/P9/DoD：prod禁stub，owner gate阻断closure | NHX1保持blocked；绝不改期待或defer-complete |
| Q40 / `T-O-420` | 同上 | §2 OOS：无existing-object upgrade | 发现upgrade实现立即回滚/删除；另开charter |
| Q41 / `T-O-421` | 同上 | P3/P5/P8：tombstone保key、同key409 | STOP Phase 3；不得partial unique隐式recreate |
| Q42 / `T-O-422` | 同上 | P2/P4/P7：outbox critical/advisory owner法 | STOP Phase 2；不得dead只告警或无限重试 |
| `T-O-376/381/383/406` | pre-initial/pre-charter QNA | P6/P9：四通道10+3、fail-loud、L1–L4不可互换 | 任一受waiver覆盖则NHX1 NOT-success |
| `T-O-390..405/407` | pre-charter Q10–Q27 | actual/fact/upload/intent/exact-clean等既有边界 | 冲突时回QNA，AP不得重解释 |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表（本计划工作要落在哪些既有代码 / 新建点上）

| 锚 ID | `path:line` | 落点（这是什么） | 本 AP 用途（对应工作项） | 处置 | 备注 |
|-------|-------------|-------------------|---------------------------|------|------|
| A-01 | `src/contracts/api/models.py:153-188,241-248` | 四source descriptor仅有external key | P2-01/P3-01：加v2 observation contract | ♻️ 重 substrate | 不新增第五kind |
| A-02 | `src/persistence/migrations/016_ns6_source_external_key.sql:1-20` | Source `(team,kind,key)` unique | P2-01：保留Source identity，另建Observation | ✅ 复用 | 禁把index改成observation unique |
| A-03 | `src/persistence/migrations/001_initial.sql:915-980` | Snapshot/Item/Revision DDL | P2-01/P3-02/P3-04 | ♻️ 重 substrate | 001 checksum不改，只加025+ |
| A-04 | `src/runtime/task/task_create.py:68-150,452-480` | Task指纹双检+registered observation独立预查 | P3-01 admission UoW | ♻️ 重 substrate | 删除TOCTOU预查owner法 |
| A-05 | `src/runtime/intake/acquisition_ingest.py:88-170,229-264,283-483` | single/scatter acquire identity与stage material | P3-02/P3-03/P5-04 | ♻️ 重 substrate | material前必须stable identity |
| A-06 | `src/runtime/intake/acceptance_snapshot.py:139-245,288-350,397-453` | Snapshot复用、blind head、refs/ChangeSet | P3-02/P5-01/P5-06 | ♻️ 重 substrate | 主要竞态/owner修复点 |
| A-07 | `src/services/intake_lifecycle/targets.py:37-217` | intent target冻结与active检查 | P3-04/P3-05 | ✅ 复用+收紧 | 7×3 admission SSOT |
| A-08 | `src/services/intake_lifecycle/lifecycle_apply.py:55-155,265-305` | lifecycle CAS+cleanup intent | P3-04/P5-06 | ♻️ 重 substrate | ItemEpoch precedent；补executors |
| A-09 | `src/services/intake_lifecycle/lifecycle_publish.py:40-140` | proof/pointer/Item CAS | P3-04/P5-05 | ✅ 复用+传epoch | 不重写publication owner |
| A-10 | `src/runtime/intake/index_rebuild_plan.py:245-288` | stale target `continue` | P3-05 | ♻️ 重 substrate | 禁partial success |
| A-11 | `src/workflows/kind_family.py:225-253,448-586` | rev1 kind graphs与HTTP route | P4-01/P4-04/P9-01 | ♻️ 重 substrate | 当前图升rev2；rev1 fixture另存 |
| A-12 | `src/services/workflow_registry.py:152-227` | immutable register/mismatch/insert revision | P4-01/P8-02 | ✅ 复用 | 正确内核，勿放宽digest |
| A-13 | `src/contracts/intake/strategies.py:15-46,157-226` | 10策略registry | P4-02/P6-02/P9-01 | ✅ 复用+typed union | 不加第11 strategy |
| A-14 | `intake/api/registry.py:35-129` | 3 provider operation registry/digest | P4-02/P9-01 | ✅ 复用 | 与策略分账 |
| A-15 | `src/runtime/binding/actual_s05.py:16-136` | actual seal/strategy字符串 | P4-02 | ♻️ 重 substrate | 扩binding family/version，不破seal-once |
| A-16 | `src/runtime/workflow/selected_output.py:53-124` | canonical selection公式 | P4-02/P5-03 | ✅ 复用 | 生产writer必须调用同一函数 |
| A-17 | `src/runtime/workflow/runtime_materialize.py:50-124,400-490,842-920` | route hack、Process materialize、selection错值 | P4-02..P4-04 | ♻️ 重 substrate | UPDATE Execution必须检查rowcount |
| A-18 | `src/runtime/workflow/runtime_outcome.py:38-180,287-393,487-541` | Outcome/lease/fail owner | P4-03/P4-06 | ♻️ 重 substrate | terminal Execution fence缺失 |
| A-19 | `src/runtime/workflow/worker.py:80-140` | 所有ConflictError当stale | P4-03 | ♻️ 重 substrate | 分Fence/Lease/Domain families |
| A-20 | `src/runtime/task/task_commands.py:237-353` | full retry复制actual但从root重启 | P4-05 | ♻️ 重 substrate | exact resume，不refetch |
| A-21 | `src/runtime/workflow/runtime_outbox.py:343-428` | dead/event/8-attempt | P4-06/P7-03 | ♻️ 重 substrate | 原dead row保留，新增owner/predecessor |
| A-22 | `src/runtime/workflow/runtime_repair.py:74-141` | ready Process/Execution补wake | P4-06 | ♻️ 重 substrate | 必须识别dead predecessor |
| A-23 | `src/contracts/api/objects.py:12-24` | handle-only public object contract | P5-01 | ♻️ 重 substrate | 加session/receipt，不加raw GET |
| A-24 | `src/services/object_upload.py:33-180` | promote早于Team/catalog、随机hold | P5-01/P5-02 | ♻️ 重 substrate | 以session journal重排 |
| A-25 | `src/services/object_upload_ttl.py:40-92` | TTL全扫、cancel最新hold | P5-01 | ♻️ 重 substrate | reserved session不TTL |
| A-26 | `src/storage/local_store.py:72-150,186-259` | staging/promote/quarantine/reap | P5-02 | ✅ 复用+session API | CAS布局不改，journal补owner |
| A-27 | `src/services/object_gc.py:134-189,218-366` | candidate/quarantine/tombstone/fence | P5-02/P5-06 | ✅ 复用+job | tombstoned quarantine需destroy |
| A-28 | `src/persistence/migrations/018_nh2_selected_output_control.sql:6-35` | selected-output v1表 | P2-03/P5-03 | 读不改 | v2新assertion，不改旧row |
| A-29 | `src/persistence/migrations/019_nh3_representation_fact_history.sql:1-75` | fact/history typed authority | P2-03/P5-03 | ✅ 复用 | 已建好别重写 |
| A-30 | `src/persistence/migrations/024_nh_review_invariants.sql:1-53` | 部分immutable triggers | P2-03/P5-03 | ♻️ 扩展 | 补selection/artifact/vector identity |
| A-31 | `src/runtime/intake/core.py:398-440` | early stage复制完整state | P5-04 | ♻️ 重 substrate | 改CAS refs；晚阶段已有drop precedent |
| A-32 | `src/contracts/common/models.py:24-36,110-144` | PayloadExtra仅JSON/size；safe validator独立 | P5-04 | ✅ 复用+基类调用 | nested source必须统一执行 |
| A-33 | `src/persistence/ports.py:10-27` | 只有write transaction，无read snapshot | P2-05/P5-05/P1-03 | ♻️ 扩展 | 服务不import driver |
| A-34 | `src/persistence/migration_runner.py:81-163` | checksum/linear migration | P1-02/P2-05/P8-01 | ✅ 复用 | 001/018–024不得改checksum |
| A-35 | `src/runtime/config.py:12-105` | 无role、stub/supply/CW defaults | P6-01/P6-03/P6-04 | ♻️ 重 substrate | prod profile单独冻结 |
| A-36 | `api/app.py:215-271,427-489,586-658` | supply probe/composition/lifespan全loop | P4-01/P6-01..P6-04 | ♻️ 重 substrate | 按role裁剪，all保持兼容 |
| A-37 | `src/runtime/health.py:15-121` | required set/overall | P6-03 | ♻️ 重 substrate | configured required必须进入overall |
| A-38 | `src/persistence/turso/port.py:176-205` | CW required却报告false | P6-03 | ✅ 复用事实 | profile决定required，不伪造true |
| A-39 | `src/runtime/workflow_supervisor.py:20-83` | failures仅内存 | P6-03/P7-04 | ♻️ 重 substrate | readiness+diagnostic+metric |
| A-40 | `src/runtime/supply/browser.py:220-292` | actual browser args/egress prefs | P6-04 | ✅ 复用+攻击测试 | 守卫必须钉actual args |
| A-41 | `api/public/routes.py:109-576` | public surface无catalog/lists strict models | P7-01/P7-02 | ♻️ 扩展 | 不接受workflow selector |
| A-42 | `src/runtime/task/task_views.py:34-94,202-235` | Task字段少、waiting折running | P7-01/P7-02 | ♻️ 重 projection | 六态保留，补phase/reason |
| A-43 | `src/runtime/task/task_projections.py:17-125` | single item无child→active | P7-02 | ♻️ 修复 | single/scatter明确分支 |
| A-44 | `api/internal/routes.py:11-161` | operator guard+只读端点 | P7-03 | ✅ 复用guard+扩展 | control仍token+内网+audit |
| A-45 | `src/services/observability.py:73-246,282-465` | DiagnosticSink/timeline/dead list | P7-03/P7-04 | ✅ 复用+接线 | default不回raw payload |
| A-46 | `src/runtime/metrics.py:80-229` | closed catalog、多dead series | P7-04 | ♻️ 整理 | 每series emitter或删除 |
| A-47 | `src/contracts/common/errors.py:70-109` | arbitrary mixed error code | P7-04 | ♻️ 重 substrate | v2 registry+legacy aliases |
| A-48 | `tests/unit/test_ns6_phase2.py:263-289` | 当前stale-fence红灯 | P1-03/P4-03 | 🔱 fork | 保留新世代不被杀的原断言 |
| A-49 | `tests/e2e/test_new_harvest_crash_windows.py:91-433` | hook级CREATE/Outcome/SEL/SEAL/FANIN/PUB/OUTBOX/PROM-CAT | P9-03 | 🔱 fork | 不能替代真实process kill |
| A-50 | `tests/e2e/test_new_harvest_closed_set.py:153-630` | 负格与10+3手写cells | P9-01/P9-04 | 🔱 fork | 改为compiler-derived并保持L4 |
| A-51 | `tests/domain/test_nh9_evidence_pack_checker.py:22-130` | 文件/PASS字符串checker | P1-04/P9-04 | 🔱 fork | NHX1 checker必须执行命令 |
| A-52 | `tests/e2e/test_nh4_upload_replay_race.py:21-300` | upload/GC/TTL/ingest交错 | P5-01/P5-02/P9-02 | 🔱 fork | 加session owner与barrier断言 |

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据） |
|----|-------------|----------------|
| ⛔1 | external key继续兼任Observation | `T-O-408`；会重现Snapshot压缩/永久409 |
| ⛔2 | 另造多个Item epoch或局部blind rowcount | `T-O-409`；跨字段callback仍无共同owner |
| ⛔3 | full retry复制actual后重新HTTP/API acquire | `T-O-410`；old actual/new bytes假exact |
| ⛔4 | 同revision接受新digest或UPDATE persisted rev1 | `T-O-411`；破坏old pin/evidence |
| ⛔5 | `registered_api.map`当第11 CleanStrategy | `T-O-412`；破坏10+3 taxonomy |
| ⛔6 | handle充当session，cancel最新/全部pending | `T-O-413`；无法隔离调用所有权 |
| ⛔7 | migration原地“修正”legacy evidence | `T-O-414`；事后值冒充当时事实 |
| ⛔8 | public开放Process raw payload或operator任意SQL | `T-O-415` + S16；泄密/越权/第二状态机 |
| ⛔9 | FastAPI title或Container存在当leaf-worker role | `T-O-416`；loop/readiness owner仍隐式 |
| ⛔10 | logical-only永久open cleanup或delete立即级联unlink | `T-O-417`；前者不收敛、后者破坏retention/recovery |
| ⛔11 | v1 error无alias批量改名，或继续新增混合code | `T-O-418` |
| ⛔12 | stub/glyph/fixture/skip当prod 10+3 PASS | `T-O-419`；NHX1必须blocked |
| ⛔13 | 借retry/rebuild偷existing-object upgrade | `T-O-420`；OOS硬禁 |
| ⛔14 | physical purge后自动释放deleted external key | `T-O-421`；行为随scanner时间漂移 |
| ⛔15 | dead只告警、无限重试或repair绕过predecessor | `T-O-422` |
| ⛔16 | 修改001/018–024 checksum | migration runner `:121-145` 会拒绝，且改写历史 |
| ⛔17 | raw sqlite3读取Turso文件当e2e evidence | adapter语义不等价；Phase 1架构scan硬拒 |
| ⛔18 | hook/事后SQL当唯一crash证明 | 不能证明进程/FS/DB冷启动恢复；NHX1-T29必须真实kill |
| ⛔19 | 每strategy手写一格代替compiler-derived edge分母 | 会漏route/media/negative；NHX1-T27硬拒 |
| ⛔20 | 文件含`PASS`、历史test count或字段存在即fixed | NHX1-T01/NHX1-T30 evidence executor必须实际运行/recompute |
| ⛔21 | Phase 9直接补功能或放宽期待 | 必须回owner Phase并重跑后继链；否则NOT-success |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立reference-anchor**：无单独NHX1 anchor文件；§7.1是本AP grounding真源。上游问题分母见VF-ledger，决策真源见冻结QNA，二者不替代本锚区的HEAD file:line。
- **威胁模型主源**：`docs/baseline/domain-truth/S16-security-trust-boundary.md:438-465`（TM-01..10入口）、`:650-715`（egress/SSRF）、`:746-798`（debug/supply trust）、`:799-880`（error/audit/redaction）。
- **对象删除边界**：`docs/baseline/domain-truth/S13-artifact-storage.md:263-296,320-337` —— reference-first、hold、grace、delete fence、proof；P5-01/P5-02/P5-06不得绕过。
- **operator/observability边界**：`docs/baseline/domain-truth/S15-observability-reliability.md:220-248,637-671` —— S15不拥有业务状态机；repair语义仍由S03/S12 CAS；operator token+内网+team filter。
- **本AP强制攻击向量**：
  - TM-NHX1-01：跨Team observation/session/item/namespace/outbox枚举与token重放；
  - TM-NHX1-02：nested `payload_extra` secret/path/signed URL与stage正文sentinel持久化；
  - TM-NHX1-03：SSRF、redirect rebinding、browser no-sandbox/root、parser/OCR网络与process-tree逃逸；
  - TM-NHX1-04：stale operator restart/requeue/stop跨generation误伤与receipt replay；
  - TM-NHX1-05：GC/cleanup在新ref/hold、tombstone/quarantine、promote/catalog间竞态误删；
  - TM-NHX1-06：恶意/漂移workflow/capability/error/evidence manifest与migration checksum篡改；
  - TM-NHX1-07：高基数metric、diagnostic drop、raw payload debug与audit write failure。
- **执行门**：P5/P6/P7安全项未把上述向量映射到NHX1-T15–NHX1-T25时，AP保持draft；Phase 9不得用happy-path替代。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么） | 类型 | 层 | 来源 | 映射（工作项 → 收口目标） | PASS证据（四元组） |
|---------|-------------------|------|----|------|---------------------------|--------------------|
| NHX1-T01 | Truth/coverage/anti-fake-green manifest | 短途 | 契约/domain | 🆕 `test_nhx1_truth_and_coverage.py` | P1-01/P1-04 → 50债务零漏项 | commit + nodes PASS + T-O-408..422 + UTC |
| NHX1-T02 | pre-fix DB迁移与schema/fixture完整性 | spike | 集成/upgrade | 🆕 `test_nhx1_persisted_upgrade.py` | P1-02/P2-01..05 → 非空库forward migration | commit + upgrade nodes PASS + Q31/Q34 + UTC |
| NHX1-T03 | adapter-aware harness与修前RED保真 | 短途 | 契约/回归 | 🔱 `test_ns6_phase2.py` + 新architecture scan | P1-03 → 零sqlite3-on-Turso/零xfail掩盖 | commit + scan/baseline PASS + T-O-406 + UTC |
| NHX1-T04 | 四kind Observation admission/replay/concurrency | soak | L2/L3/R | 🆕 `test_nhx1_observation_identity.py` | P3-01/P2-01 → effect-once reservation | commit + matrix PASS + T-O-408 + UTC |
| NHX1-T05 | Snapshot/no-change/ItemEpoch并发 | soak | L2/L4/R | 🆕 `test_nhx1_item_epoch.py` | P3-02 → 新Snapshot、head CAS、serving正确 | commit + DB/query PASS + T-O-409 + UTC |
| NHX1-T06 | scatter stable identity与failed observation retry | spike | L3/L4 | 🔱 registered-api scatter/review-fixes | P3-03 → retry可恢复、零SOURCE_MISSING | commit + journey PASS + T-O-408/410 + UTC |
| NHX1-T07 | 7 intent×3 lifecycle + deleted key + late callback | soak | L2/L3/R | 🔱 `test_nh8_api_item_intents.py` + new matrix | P3-04 → 非法格零Task、epoch fence | commit + 21-cell/race PASS + T-O-409/421 + UTC |
| NHX1-T08 | index rebuild frozen cardinality/noop projection | spike | L2/L3 | 🔱 rebuild tests | P3-05 → no silent skip/typed noop | commit + cardinality PASS + T-O-409/415 + UTC |
| NHX1-T09 | persisted rev1→rev2/old pin/retirement | mega | upgrade/C | 🔱 `test_workflow_revision_compatibility.py` | P4-01/P8-02 → exact compat/zero-pin retire | commit + upgrade/sequence PASS + T-O-411 + UTC |
| NHX1-T10 | ProcessingBinding 10+3 + selected fact/formula | 短途 | unit/集成 | 🔱 selected-output/lineage tests | P4-02/P2-03 → typed union/digest可重算 | commit + 13-cell/formula PASS + T-O-412/414 + UTC |
| NHX1-T11 | terminal Outcome/current process/worker error family | soak | L2/R | 🔱 crash windows/ns6 stale-fence | P4-03 → terminal零推进/domain fail终结 | commit + outcome race PASS + T-O-410/422 + UTC |
| NHX1-T12 | current-hop route/reacquire reachability | spike | compiler/L3 | 🔱 representation guard tests | P4-04 → 每hop只走声明边 | commit + edge matrix PASS + T-O-411/412 + UTC |
| NHX1-T13 | full retry frozen resume与外部call-count=0 | mega | L3/L4 | 🆕 `test_nhx1_exact_replay.py` | P4-05 → old input/actual exact | commit + changed-upstream journey PASS + T-O-410 + UTC |
| NHX1-T14 | outbox critical/advisory dead + requeue lineage | soak | L2/operator/R | 🆕 `test_nhx1_outbox_owner.py` | P4-06/P2-04 → critical owner terminal | commit + poison/requeue PASS + T-O-422 + UTC |
| NHX1-T15 | upload session replay/cancel/TTL/reserve/consume | soak | L2/L3/R/S | 🔱 `test_nh4_upload_replay_race.py` | P5-01/P2-02 → exact session isolation | commit + session matrix PASS + T-O-413 + UTC |
| NHX1-T16 | promotion/catalog + quarantine/tombstone crash | mega | L2/process-crash | 🔱 crash windows/object GC + real kill | P5-02 → 无invisible CAS/quarantine | commit + cold-restart PASS + T-O-413/417 + UTC |
| NHX1-T17 | evidence SQL攻击、legacy verdict/correction、formula drift | 短途 | 集成/security | 🆕 `test_nhx1_evidence_plane.py` | P5-03/P2-03 → evidence不可伪造 | commit + attack/recompute PASS + T-O-414 + UTC |
| NHX1-T18 | CAS-first envelope + nested secret/path/URL attacks | mega | L2/L3/S | 🔱 inline staging/runtime security | P5-04 → DB/CAS metadata零正文秘密 | commit + sentinel scan PASS + T-O-414/415 + UTC |
| NHX1-T19 | publication manifest/read snapshot/TOCTOU retrieval | mega | L2/L4/R | 🔱 facet retrieval + new attack | P5-05/P2-05 → proof/manifest一致命中 | commit + query/TOCTOU PASS + T-O-414 + UTC |
| NHX1-T20 | delete cleanup三executor/holds/physical bytes convergence | soak | L3/L4/R | 🆕 `test_nhx1_cleanup_convergence.py` | P5-06/P8-03 → logical zero+physical terminal | commit + cleanup/query/file PASS + T-O-417/421 + UTC |
| NHX1-T21 | 四deployment roles/capability claim/readiness | spike | L2/L3 | 🆕 `test_nhx1_roles_readiness.py` | P6-01..03 → role owner与overall真实 | commit + role matrix PASS + T-O-416 + UTC |
| NHX1-T22 | prod非stub 10+3、S16、process-tree kill/backpressure | live gate | L3/L4/S | 🔱 NH6/NH7 runtime tests | P6-02/P6-04 → NHX1-T22-E工程可运行；NHX1-T22-O owner签收 | commit + live profile PASS + T-O-419 + owner UTC |
| NHX1-T23 | public OpenAPI/catalog/Task/Item/Namespace cold-start | mega | contract/L3/L4 | 🆕 `test_nhx1_public_contracts.py` | P7-01/P7-02 → 无SQL发现与解释 | commit + OpenAPI/journey PASS + T-O-415/418 + UTC |
| NHX1-T24 | operator debug/control/auth/CAS/receipt/redaction | soak | L2/L3/S | 🆕 `test_nhx1_operator_controls.py` | P7-03/P2-04 → 可恢复不可越权 | commit + control attack PASS + T-O-415/422 + UTC |
| NHX1-T25 | signal catalog↔emitter↔alert↔runbook + error aliases | 短途 | unit/集成 | 🆕 `test_nhx1_signals_errors.py` | P7-04/P6-03 → 零孤儿/可判retry | commit + static/runtime PASS + T-O-418/419 + UTC |
| NHX1-T26 | shadow/cutover/drain/retirement/rollback drill | mega | upgrade/C/R | 🆕 `test_nhx1_cutover.py` | P8-01..03 → new writer唯一/old exact | commit + interrupted cutover PASS + T-O-411/414 + UTC |
| NHX1-T27 | compiler-derived closed set every edge/10+3/intent L1–L4 | mega | L1–L4 | 🔱 closed-set generator/e2e | P9-01 → coverage 100% | commit + manifest/query PASS + T-O-408..422 + UTC |
| NHX1-T28 | identity/epoch/outcome/session/outbox deterministic race soak | soak | L2/L3/R | 🆕 `test_nhx1_race_soak.py` | P9-02 → N×seed effect-once | commit + soak log PASS + race Truths + UTC |
| NHX1-T29 | real subprocess crash + pre-fix DB upgrade/old-pin mega | mega | process-crash/upgrade | 🆕 `test_nhx1_subprocess_crash.py` | P9-03 → cold-start收敛 | commit + kill/restart/upgrade PASS + T-O-410/411/413/417/422 + UTC |
| NHX1-T30 | full repo/evidence executor/第三轮审查/closure | 退出硬闸 | 全层 | 🆕 NHX1 evidence checker + full suite | P9-04/P1-04 → 零债务/零假绿 | current commit + all commands PASS + owner gates + UTC |

### 8.1.1 各 Test-ID 详细规格（含逐项防假绿）

#### `NHX1-T01` — Truth / coverage / evidence-executor 合同

| 字段 | 内容 |
|------|------|
| 测试位置 | 🆕 `tests/domain/test_nhx1_truth_and_coverage.py::{test_all_vf_and_deferred_have_one_owner,test_truth_ids_frozen_and_unique,test_each_work_item_has_test,test_fake_pass_is_rejected}` |
| 前置 | 冻结QNA v1.0；coverage manifest；本AP P/Test列表 |
| 步骤 | 解析VF-ledger分类、历史deferred、Q28–42、§3工作项与§8 Test-ID；建立双向映射并重算manifest digest；向临时evidence注入假SHA/PASS/skip。 |
| PASS断言 | 52 VF恰一次；分类15/18/17/2；50债务均有work/test；Q/Truth 15/15；假证据全部被checker拒绝。 |
| 防假绿侦测 | **禁止**只统计表格行数；必须验证ID语义映射、Test-ID存在、当前commit与命令exit。删一VF、重复owner、写“PASS”但无exit均应RED。 |
| 跑法 | `uv run pytest -q tests/domain/test_nhx1_truth_and_coverage.py` |
| 层/来源 | 契约/domain；🆕；Phase 1 EXIT |

#### `NHX1-T02` — Pre-fix persisted migration

| 字段 | 内容 |
|------|------|
| 测试位置 | 🆕 `tests/integration/test_nhx1_persisted_upgrade.py::{test_prefx_024_database_migrates_forward,test_migration_resume_is_idempotent,test_legacy_rows_are_not_fabricated}` |
| 前置 | checksum固定的pre-fix DB、rev1 manifest；migration 025+ |
| 步骤 | 复制fixture；验证旧digest/错selected/legacy refs；执行迁移；在各migration/backfill barrier中断并重跑；对SQLite/Turso分别inspect。 |
| PASS断言 | 025+各一次；checksum正确；legacy facts未被UPDATE成v2；verdict/compat行存在；第二次migrate no-op；schema/indices一致。 |
| 防假绿侦测 | **空库migrate不算PASS**；fixture必须含旧rev1与错误evidence；禁止当前builder生成“旧”fixture；禁止只断表存在。 |
| 跑法 | `uv run pytest -q tests/integration/test_nhx1_persisted_upgrade.py` |
| 层/来源 | 集成/upgrade；🆕；P1/P2硬闸 |

#### `NHX1-T03` — Harness真实性与已知RED守卫

| 字段 | 内容 |
|------|------|
| 测试位置 | 🆕 `tests/domain/test_nhx1_harness_integrity.py`；🔱 `tests/unit/test_ns6_phase2.py::test_stale_fencing_fail_does_not_kill_new_generation` |
| 前置 | PersistenceInspectorPort；修前RED ledger |
| 步骤 | AST扫描e2e禁止用raw sqlite打开Turso DB；检查pytest markers无新增xfail/skip；Phase 1记录stale-fence修前failure signature；Phase 4后复跑原node。 |
| PASS断言 | adapter违规=0；预期RED fingerprint与ledger一致；最终原node PASS且仍断言新世代running/未被旧fail杀死。 |
| 防假绿侦测 | 改期待为“抛Conflict即可”、删除状态断言、加xfail/skip、只跑新替代test均FAIL。Phase 1的“捕获RED”不得被写成bug已修。 |
| 跑法 | `uv run pytest -q tests/domain/test_nhx1_harness_integrity.py tests/unit/test_ns6_phase2.py::test_stale_fencing_fail_does_not_kill_new_generation`（Phase 1前半允许第二node预期RED并单独留证；Phase 4 EXIT必须全绿） |
| 层/来源 | 契约+回归；🔱 |

#### `NHX1-T04` — 四kind Observation reservation

| 字段 | 内容 |
|------|------|
| 测试位置 | 🆕 `tests/e2e/test_nhx1_observation_identity.py::{test_four_kinds_exact_observation_replay,test_concurrent_observation_reservation_single_winner,test_different_observation_same_source}` |
| 前置 | migration 025；v2 public descriptors；worker可停/可控barrier |
| 步骤 | 对inline/local/http/API各创建同key同fingerprint、同key异fingerprint、新key同source；并发双create；检查Task/Observation/Execution/Snapshot行。 |
| PASS断言 | exact replay同coordinates/receipt；异fingerprint409；并发一个201其余replay/409；新observation独立Snapshot；零500/残留reservation。 |
| 防假绿侦测 | **HTTP码 alone不算**；必须断DB计数/owner/attempt state。用不同task_uuid逃避同observation、worker跑完后才并发、串行模拟均FAIL。 |
| 跑法 | `uv run pytest -q tests/e2e/test_nhx1_observation_identity.py` |
| 层/来源 | L2/L3/R；🆕；T-O-408 |

#### `NHX1-T05` — Snapshot/no-change/ItemEpoch

| 字段 | 内容 |
|------|------|
| 测试位置 | 🆕 `tests/e2e/test_nhx1_item_epoch.py::{test_changed_observation_creates_snapshot_and_revision,test_same_content_new_observation_records_no_change,test_concurrent_head_cas_one_winner,test_delete_fences_late_accept_and_publish}` |
| 前置 | NHX1-T04；ItemEpoch writer；retrieval namespace |
| 步骤 | 同source连续观察不同/相同content；并发accept不同content；在accept/publish barrier执行delete/reactivate；查询Snapshot/Revision/ChangeSet/Item/pointer/search。 |
| PASS断言 | 每Observation一Snapshot；同content可复用Revision但有no-change fact；head仅一winner；late callback零Item/pointer/vector变化；旧serving不泄漏。 |
| 防假绿侦测 | Task succeeded、items=1或最新head存在不算；必须断两Snapshot、ChangeSet UUID可回读、epoch变化和search结果。LWW被当成功即FAIL。 |
| 跑法 | `uv run pytest -q tests/e2e/test_nhx1_item_epoch.py` |
| 层/来源 | L2/L4/R；🆕 |

#### `NHX1-T06` — Scatter identity / failed retry

| 字段 | 内容 |
|------|------|
| 测试位置 | 🔱 `tests/e2e/test_registered_api_scatter.py` + 🆕 `tests/e2e/test_nhx1_scatter_retry.py` |
| 前置 | NHX1-T04；registered operation manifest；child workflow rev2 |
| 步骤 | acquisition后accept前注入失败；保留Observation failed attempt；调用typed retry；并发同key；检查root/child manifest中的Source/Observation UUID并最终query。 |
| PASS断言 | retry不出现`INTAKE_SOURCE_MISSING`；stable UUID在envelope/DB一致；只新增attempt不重建Source；accepted后children/query正确。 |
| 防假绿侦测 | monkeypatch state UUID、换observation key、清库重跑、只断Task不再running均FAIL；必须在同persisted DB和原key恢复。 |
| 跑法 | `uv run pytest -q tests/e2e/test_nhx1_scatter_retry.py tests/e2e/test_registered_api_scatter.py` |
| 层/来源 | L3/L4；🔱+🆕 |

#### `NHX1-T07` — 7 intent × 3 lifecycle + epoch races

| 字段 | 内容 |
|------|------|
| 测试位置 | 🔱 `tests/e2e/test_nh8_api_item_intents.py` + 🆕 `tests/e2e/test_nhx1_intent_state_matrix.py` |
| 前置 | active/deactivated/deleted fixtures；CommandReceipt |
| 步骤 | 21格逐HTTP调用；same command replay；new same-action command；delete/reactivate与late accept/publish；cross-team item。 |
| PASS断言 | 合法格达到产品终态；非法格409且Task/Process=0；replay标replayed；deleted同keyingest409；old epoch callback零effect。 |
| 防假绿侦测 | 仅Pydantic 422、创建Task后failed、同态201/noop、只测7 intent不乘状态、用新item避race均FAIL。 |
| 跑法 | `uv run pytest -q tests/e2e/test_nhx1_intent_state_matrix.py tests/e2e/test_nh8_api_item_intents.py` |
| 层/来源 | L2/L3/R；🔱+🆕 |

#### `NHX1-T08` — Rebuild cardinality / typed noop

| 字段 | 内容 |
|------|------|
| 测试位置 | 🔱 `tests/e2e/test_index_rebuild.py`、`test_intake_rebuild_metadata.py` + 🆕 cardinality nodes |
| 前置 | 多Item frozen target set；barrier可使一项stale |
| 步骤 | admission后变更/删除一个target；执行team rebuild；另测初始空scope与active single item；读取Task result/counts/mode/metrics。 |
| PASS断言 | stale任一项使全Task typed failed且零partial pointer；初始空返回`index_rebuild_noop`；非空success processed=frozen count。 |
| 防假绿侦测 | `continue`后Task succeeded、只看HTTP 200、把执行期全stale当initial noop、忽略processed count均FAIL。 |
| 跑法 | `uv run pytest -q tests/e2e/test_nhx1_rebuild_cardinality.py tests/e2e/test_index_rebuild.py` |
| 层/来源 | L2/L3；🔱+🆕 |

#### `NHX1-T09` — Rev1→rev2 persisted compatibility

| 字段 | 内容 |
|------|------|
| 测试位置 | 🔱 `tests/unit/test_workflow_revision_compatibility.py` + NHX1-T02 fixture |
| 前置 | checked-in rev1 exact；rev2 active；pre-fix DB |
| 步骤 | bootstrap旧库；完成unstarted/running rev1 Execution与full retry；创建新Task；尝试有pin retire；排空后retire；冷启。 |
| PASS断言 | 无`REGISTRY_DIGEST_MISMATCH`；old sequence/digest exact；new只rev2；有pin retire rollback；zero后retire但old manifest仍可读。 |
| 防假绿侦测 | 仅空库register rev2、把persisted rev1 UPDATE成新digest、删除old Task、只断bootstrap 200均FAIL。 |
| 跑法 | `uv run pytest -q tests/unit/test_workflow_revision_compatibility.py tests/integration/test_nhx1_persisted_upgrade.py` |
| 层/来源 | upgrade/compat mega；🔱 |

#### `NHX1-T10` — ProcessingBinding 10+3 / selected fact

| 字段 | 内容 |
|------|------|
| 测试位置 | 🔱 selected-output/representation lineage tests + 🆕 `tests/integration/test_nhx1_processing_binding.py` |
| 前置 | rev2 graph；10 strategy registry；3 provider operation registry |
| 步骤 | 逐13 cell物化/选择；读取fact row、selection assertion、actual binding；独立调用canonical formula重算；注入unknown capability/operation。 |
| PASS断言 | 每cell binding family/key/version/digest可registry解析；fact digest≠manifest alias且重算相等；unknown bootstrap/materialize fail。 |
| 防假绿侦测 | 只断字段存在/64hex、把manifest再hash当fact、将API map计第11 strategy、跳Process直插selection均FAIL。 |
| 跑法 | `uv run pytest -q tests/integration/test_nhx1_processing_binding.py tests/integration/test_nh2_selected_output_control.py tests/integration/test_nh3_fact_history_uow.py` |
| 层/来源 | unit/集成；🔱+🆕 |

#### `NHX1-T11` — Terminal Outcome / worker error family

| 字段 | 内容 |
|------|------|
| 测试位置 | 🔱 `tests/e2e/test_new_harvest_crash_windows.py`、`tests/unit/test_ns6_phase2.py` + 🆕 terminal nodes |
| 前置 | active/failed/cancelled Execution；claimed Process；domain strategy mismatch |
| 步骤 | terminalize owner后提交same/different late Outcome；并发cancel；让materialize UPDATE rowcount=0；触发DomainConflict与FenceConflict。 |
| PASS断言 | terminal状态/Process/next Process/counts零变化；same late返回replayed/fenced；domain mismatch使Process/Task failed而非running；新世代不受旧fail影响。 |
| 防假绿侦测 | 只期待Conflict exception、不检查后继行；手工改DB后不走Outcome；把DomainConflict也吞掉；删旧stale-fence断言均FAIL。 |
| 跑法 | `uv run pytest -q tests/e2e/test_nhx1_terminal_outcome.py tests/unit/test_ns6_phase2.py::test_stale_fencing_fail_does_not_kill_new_generation tests/unit/test_ns6_phase2.py::test_cancel_prevents_succeeded_task` |
| 层/来源 | L2/R；🔱+🆕 |

#### `NHX1-T12` — Current-hop reachability

| 字段 | 内容 |
|------|------|
| 测试位置 | 🔱 `tests/integration/test_nh2_legal_edges_reachable.py`、`test_nh2_representation_guards.py` + 🆕 hop matrix |
| 前置 | rev2 compiled hop manifest |
| 步骤 | 对HTTP static/browser/reacquire/print及local media每个from-step生成present/absent/unknown与policy；执行route decision并验证selected edge。 |
| PASS断言 | 只选择当前hop声明edge；absent无edge typed fail；unknown fail-closed；browser/reacquire不会因图上别处guard被误杀。 |
| 防假绿侦测 | 每strategy一格、只检查graph contains guard、直接调用clean handler、忽略from-step/negative均FAIL。 |
| 跑法 | `uv run pytest -q tests/integration/test_nhx1_route_reachability.py tests/integration/test_nh2_legal_edges_reachable.py tests/integration/test_nh2_representation_guards.py` |
| 层/来源 | compiler/L3；🔱+🆕 |

#### `NHX1-T13` — Exact full retry

| 字段 | 内容 |
|------|------|
| 测试位置 | 🆕 `tests/e2e/test_nhx1_exact_replay.py::{test_http_full_retry_zero_refetch,test_api_full_retry_zero_reenumeration,test_metadata_no_change_context_survives,test_no_frozen_input_rejects}` |
| 前置 | counting HTTP/API adapter；首次失败发生在downstream；frozen artifact |
| 步骤 | 首次acquire后改变HTTP body/API records；执行full retry；记录adapter calls、artifact/fact/actual；另在acquire前失败测试拒绝。 |
| PASS断言 | retry期间external call count=0；bytes/fact/actual/config/context exact；metadata no-change route不丢；无input返回canonical nonretryable。 |
| 防假绿侦测 | upstream返回相同bytes、mock不计calls、只比actual digest、把新observation当retry、清库后重建均FAIL。 |
| 跑法 | `uv run pytest -q tests/e2e/test_nhx1_exact_replay.py` |
| 层/来源 | L3/L4 mega；🆕 |

#### `NHX1-T14` — Outbox dead owner / requeue

| 字段 | 内容 |
|------|------|
| 测试位置 | 🆕 `tests/integration/test_nhx1_outbox_owner.py`；🔱 `tests/unit/test_ns6_phase2.py::test_poison_outbox_increments_dead_metric_with_task_trace` |
| 前置 | critical/advisory kind manifests；poison consumer；operator token |
| 步骤 | 达到attempt budget；检查dead+owner同TX；advisory分支；requeue新generation；stale owner/requeue；repair扫描。 |
| PASS断言 | critical owner typed failed、advisory owner不变；原dead保留；requeue有predecessor/receipt；stale零effect；repair不绕过。 |
| 防假绿侦测 | 只看dead event/metric、人工SQL改owner、原dead→pending、无限retry、repair另造wake但owner仍ready均FAIL。 |
| 跑法 | `uv run pytest -q tests/integration/test_nhx1_outbox_owner.py tests/unit/test_ns6_phase2.py::test_poison_outbox_increments_dead_metric_with_task_trace` |
| 层/来源 | L2/operator/R；🆕+🔱 |

#### `NHX1-T15` — ObjectUploadSession identity

| 字段 | 内容 |
|------|------|
| 测试位置 | 🔱 `tests/e2e/test_nh4_upload_replay_race.py` + 🆕 `tests/e2e/test_nhx1_object_sessions.py` |
| 前置 | migration 026；session-aware public API |
| 步骤 | same idempotency replay；two idempotency same bytes；cancel A；TTL B；reserve C by Task；consume C；cross-team/stale token；检查refs/sessions/receipts。 |
| PASS断言 | replay同session；A取消不动B；reserved C不TTL；consume只转C；cross-team deny；所有command disposition明确。 |
| 防假绿侦测 | 只断same handle、pending总数最终0、按最新hold猜、串行不并发、直接DB调用绕public auth均FAIL。 |
| 跑法 | `uv run pytest -q tests/e2e/test_nhx1_object_sessions.py tests/e2e/test_nh4_upload_replay_race.py` |
| 层/来源 | L2/L3/R/S；🔱+🆕 |

#### `NHX1-T16` — Promotion/catalog 与 quarantine/tombstone crash

| 字段 | 内容 |
|------|------|
| 测试位置 | 🔱 `tests/e2e/test_new_harvest_crash_windows.py::test_w_nh_prom_cat_crash_no_usable_handle`、`tests/unit/test_object_gc.py` + 🆕 `tests/e2e/test_nhx1_object_crash_recovery.py` |
| 前置 | session journal；deletion job；可kill的maintenance child process；真实object root |
| 步骤 | 分别kill receiving/prepared/promoted/catalog-commit、quarantined/tombstoned/destroy前；冷启scanner；枚举DB session/job/catalog/ref与objects/staging/quarantine文件。 |
| PASS断言 | 每窗最终committed/consumed或expired/destroyed/typed integrity；无catalog外final、无tombstoned quarantine、无catalog指向缺bytes。 |
| 防假绿侦测 | fault hook返回后在同进程继续不算冷启；只断public handle不可用、不扫描final文件；事后SQL清理；忽略quarantine均FAIL。 |
| 跑法 | `uv run pytest -q tests/e2e/test_nhx1_object_crash_recovery.py tests/e2e/test_new_harvest_crash_windows.py::test_w_nh_prom_cat_crash_no_usable_handle tests/unit/test_object_gc.py` |
| 层/来源 | L2/process-crash；🔱+🆕 |

#### `NHX1-T17` — Evidence plane攻击与纠正

| 字段 | 内容 |
|------|------|
| 测试位置 | 🆕 `tests/integration/test_nhx1_evidence_plane.py::{test_all_evidence_identity_updates_abort,test_legacy_selection_gets_correction_not_update,test_formula_versions_recompute,test_vector_state_cannot_bypass_identity}` |
| 前置 | migration 027；pre-fix错误selection fixture；v2 writer |
| 步骤 | 对fact/history/selection/artifact/vector/publication/delete proof逐UPDATE/DELETE；先改projection state再改identity；运行verifier/correction；重算v1/v2 formula。 |
| PASS断言 | identity攻击abort；允许的projection CAS成功；旧row bytes不变、旁路verdict/correction存在；新writer digest等于canonical重算。 |
| 防假绿侦测 | 只检查trigger名字/字段存在、只攻击content_digest、直接修旧row、64hex即视正确、忽略state绕过均FAIL。 |
| 跑法 | `uv run pytest -q tests/integration/test_nhx1_evidence_plane.py` |
| 层/来源 | 集成/S；🆕 |

#### `NHX1-T18` — CAS-first envelope / secret persistence攻击

| 字段 | 内容 |
|------|------|
| 测试位置 | 🔱 `tests/e2e/test_inline_ingress_staging.py`、`tests/e2e/test_new_harvest_runtime_security.py` + 🆕 `tests/e2e/test_nhx1_stage_secret_redlines.py` |
| 前置 | public v1/v2 models；CAS-first stage writer；operator debug read |
| 步骤 | 注入nested `api_token/password/authorization`、absolute path、userinfo/signed URL、raw/clean sentinel；覆盖四source与retry；扫描Task audit、Execution/Process payload、stage CAS JSON、events/diagnostics/debug response。 |
| PASS断言 | unsafe public request 422零Task；合法正文只在受ref CAS；所有metadata/debug无sentinel/secret/path；digest/ref可回读；cross-team ref拒绝。 |
| 防假绿侦测 | 只测root payload_extra validator、只扫DB不扫CAS、redact response但原DB仍泄漏、替换sentinel后不验证业务可运行均FAIL。 |
| 跑法 | `uv run pytest -q tests/e2e/test_nhx1_stage_secret_redlines.py tests/e2e/test_inline_ingress_staging.py tests/e2e/test_new_harvest_runtime_security.py` |
| 层/来源 | L2/L3/S；🔱+🆕 |

#### `NHX1-T19` — Publication manifest / retrieval snapshot

| 字段 | 内容 |
|------|------|
| 测试位置 | 🔱 `tests/e2e/test_nh5_facet_retrieval.py`、`tests/unit/test_nh5_facet_sql_not_postfilter.py` + 🆕 `tests/e2e/test_nhx1_publication_manifest.py` |
| 前置 | read_snapshot port；publication manifest/proof/pointer；active namespace |
| 步骤 | publish多record generation；query命中；在read barrier并发withdraw/identity attack/pointer cutover；破坏manifest membership；运行background auditor。 |
| PASS断言 | 同snapshot内pointer/proof/manifest/record一致；invalid/missing member fail-closed/zero hit；正常facet/traceback正确；auditor产生typed signal。 |
| 防假绿侦测 | 只断query有hit、只信publication_state、应用层post-filter、无并发barrier、直接插vector跳publication均FAIL。 |
| 跑法 | `uv run pytest -q tests/e2e/test_nhx1_publication_manifest.py tests/e2e/test_nh5_facet_retrieval.py tests/unit/test_nh5_facet_sql_not_postfilter.py` |
| 层/来源 | L2/L4/R；🔱+🆕 |

#### `NHX1-T20` — Cleanup/physical convergence

| 字段 | 内容 |
|------|------|
| 测试位置 | 🆕 `tests/e2e/test_nhx1_cleanup_convergence.py`；🔱 `tests/e2e/test_nh8_delete_tombstone.py`、`tests/e2e/test_vector_purge_generation.py` |
| 前置 | Item含raw/clean/generation/vector refs；retention clock；operator/backup hold；maintenance role |
| 步骤 | public delete；立即query；推进clock/scanner；分别注入hold、executor失败、重启；读取cleanup status/proofs；枚举refs/files/vector/generation。 |
| PASS断言 | delete后立即zero serving；三executor各有terminal proof；无hold时ref/bytes收敛；有hold时typed blocked且解除后继续；replay no-op。 |
| 防假绿侦测 | search zero当物理完成、只删vector、仅统计cleanup intent存在、手工unlink、忽略hold/失败重试均FAIL。 |
| 跑法 | `uv run pytest -q tests/e2e/test_nhx1_cleanup_convergence.py tests/e2e/test_nh8_delete_tombstone.py tests/e2e/test_vector_purge_generation.py` |
| 层/来源 | L3/L4/R；🆕+🔱 |

#### `NHX1-T21` — Deployment roles / capability claim / readiness

| 字段 | 内容 |
|------|------|
| 测试位置 | 🆕 `tests/e2e/test_nhx1_roles_readiness.py`；🔱 `tests/unit/test_ns6_default_ready.py`、`tests/e2e/test_nh6_readiness.py` |
| 前置 | 四role profiles；fake/real probes；supervisor failure injector |
| 步骤 | 启动api/worker/maintenance/all；枚举running tasks/loops；提交Task并观察claim；切CW/supply/registry/supervisor component；恢复后重探。 |
| PASS断言 | role只启动授权loop；worker只claim已部署capability；required false/true影响overall正确；连续失败worker not-ready；恢复可ready。 |
| 防假绿侦测 | Container字段存在、FastAPI title、component列表含false但overall仍ready、claim队列为空所以“没越权”、只测all role均FAIL。 |
| 跑法 | `uv run pytest -q tests/e2e/test_nhx1_roles_readiness.py tests/unit/test_ns6_default_ready.py tests/e2e/test_nh6_readiness.py` |
| 层/来源 | L2/L3；🆕+🔱 |

#### `NHX1-T22` — Production 10+3 / S16 live gate

| 字段 | 内容 |
|------|------|
| 测试位置 | 🔱 NH6 parser/browser/OCR/multimodal与NH7 10+3 L3/L4 tests；🆕 `tests/e2e/test_nhx1_production_profile.py` |
| 前置 | prod role/profile；真实pinned binaries/models/data；owner S16签收窗口 |
| 步骤 | 验证profile零stub；对13 cells执行真实source→Process→publication→search；恶意PDF/URL、no-sandbox/root、redirect、network、timeout/process-tree kill、backpressure；记录identity/SBOM/CVE/signoff。 |
| PASS断言 | `NHX1-T22-E`：每cell真实capability identity与L4 hit/合法zero，安全负例fail-closed，超时杀全process group，pool满下游call=0；`NHX1-T22-O`：owner签UTC/identity。NHX1-T22仅在E+O同时满足时PASS。 |
| 防假绿侦测 | stub/glyph fixture、monkeypatch handler、import/which/models-list、503/skip、同源伪造PDF、只到Task succeeded/publication_ready、无owner签名均FAIL。 |
| 跑法 | `uv run pytest -q tests/e2e/test_nhx1_production_profile.py tests/e2e/test_nh6_parser_isolation.py tests/e2e/test_new_harvest_runtime_security.py tests/e2e/test_nh7_*retrieval.py tests/e2e/test_nh7_multimodal_lanes.py`（执行计划须展开glob为固定node清单后才留证） |
| 层/来源 | live L3/L4/S；🔱+🆕；NHX1-T22-E可标ready-for-owner并进入Phase 7，NHX1-T22-O为Phase 9 join硬闸 |

#### `NHX1-T23` — Public discovery / strict contracts / cold start

| 字段 | 内容 |
|------|------|
| 测试位置 | 🆕 `tests/e2e/test_nhx1_public_contracts.py` + OpenAPI schema snapshot |
| 前置 | catalog/read models；business token；两个Team；至少一namespace |
| 步骤 | 从零状态只用public API列workflow/capability/kind/10+3、建Task、poll actual/phase、列Item/Namespace、search；检查OpenAPI；提交workflow/process selector与cross-team cursor。 |
| PASS断言 | cold-start成功且无需SQL；Task actual/observation/retryable可读；business responses strict无`additionalProperties:true`/空schema；selector422；cross-team deny。 |
| 防假绿侦测 | 路径存在/200即PASS、测试内读DB找namespace、SDK用硬编码workflow key、OpenAPI只校request不校response、operator token冒充business均FAIL。 |
| 跑法 | `uv run pytest -q tests/e2e/test_nhx1_public_contracts.py` |
| 层/来源 | contract/L3/L4；🆕 |

#### `NHX1-T24` — Operator debug / control / receipt

| 字段 | 内容 |
|------|------|
| 测试位置 | 🆕 `tests/e2e/test_nhx1_operator_controls.py` |
| 前置 | internal network+operator token；failed/dead/waiting/cleanup fixtures；secret sentinel |
| 步骤 | 无/错/business token访问；读取Process/Stage/Fact/cleanup/dead；restart/stop/requeue/repair/resume exact replay、stale generation、cross-team；查security audit/receipt。 |
| PASS断言 | auth矩阵正确；debug有界redacted+digest；control first-wins/CAS；restart新attempt不改terminal row；receipt applied/replayed/noop/rejected；audit完整。 |
| 防假绿侦测 | 直接service调用绕router、仅2xx不查state/audit、terminal row原地ready、返回raw payload、用team_uuid当授权、重复命令多effect均FAIL。 |
| 跑法 | `uv run pytest -q tests/e2e/test_nhx1_operator_controls.py` |
| 层/来源 | L2/L3/S；🆕 |

#### `NHX1-T25` — Signals / alerts / errors

| 字段 | 内容 |
|------|------|
| 测试位置 | 🆕 `tests/integration/test_nhx1_signals_errors.py`；🔱 observability/readiness tests |
| 前置 | OperationalSignalDefinition与ErrorDefinition registries；fault injectors |
| 步骤 | 静态双向扫描catalog↔emitters↔alerts↔runbooks↔tests；触发admission deny、supervisor loop fail、GC/upload TTL/outbox dead/repair/diag drop；验证v1 aliases/v2 canonical。 |
| PASS断言 | 零孤儿series/alert；每故障实际emit低基数sample/event/diag；alert evaluator触发；v2 code+retryable稳定；v1 alias可读；UUID label被drop。 |
| 防假绿侦测 | metric名字在目录即PASS、手工set metric、ALERT字面无evaluator/runbook、只测happy path、批量改旧code、吞DiagnosticSink失败均FAIL。 |
| 跑法 | `uv run pytest -q tests/integration/test_nhx1_signals_errors.py tests/unit/test_observability.py tests/unit/test_observability_contracts.py tests/unit/test_readiness_composition.py` |
| 层/来源 | unit/集成；🆕+🔱 |

#### `NHX1-T26` — Cutover / drain / retirement / rollback

| 字段 | 内容 |
|------|------|
| 测试位置 | 🆕 `tests/e2e/test_nhx1_cutover.py` |
| 前置 | pre-fix DB；dual writers/readers；migration state；rev1/open refs/jobs fixtures |
| 步骤 | shadow期注入match/mismatch；中断backfill/cutover；切new admission；调用old writer；有pin/ref/job时retire；排空后retire；执行停admission+前滚rollback；冷启。 |
| PASS断言 | mismatch阻断；resume idempotent；cutover后new writer唯一；old writerfail-loud；有use retire rollback；zero后成功；old历史read/retry exact；cold ready。 |
| 防假绿侦测 | 只测new Task、清空旧数据后迁移、修改fixture、忽略mismatch metric、恢复old writer当rollback、用in-flight=0代替全inventory均FAIL。 |
| 跑法 | `uv run pytest -q tests/e2e/test_nhx1_cutover.py tests/integration/test_nhx1_persisted_upgrade.py` |
| 层/来源 | upgrade/C/R mega；🆕 |

#### `NHX1-T27` — Compiler-derived closed set / L1–L4

| 字段 | 内容 |
|------|------|
| 测试位置 | 🆕 generator/`tests/e2e/test_nhx1_closed_set.py`；🔱 `test_new_harvest_closed_set.py` |
| 前置 | rev2 compiler、capability/error/intent registries；NHX1-T01 coverage；prod-compatible role |
| 步骤 | 生成每from-step/reachable edge、13 processing cells、7×3 intents、negative/supply/receipt cells与最低层；逐cell运行对应test/query；重算digest。 |
| PASS断言 | graph/capability→cells双向100%；每正格达到最低层，13 knowledge格L4 hit/合法zero；负格零Task/zero hit；manifest重复生成字节相同。 |
| 防假绿侦测 | 手写每strategy一格、只跑10+3不跑routes/states、L1顶L4、Task success顶query、manifest有ID无执行、删失败cell保绿均FAIL。 |
| 跑法 | `uv run pytest -q tests/domain/test_nhx1_truth_and_coverage.py tests/e2e/test_nhx1_closed_set.py` |
| 层/来源 | L1–L4 mega；🆕+🔱 |

#### `NHX1-T28` — Deterministic race soak

| 字段 | 内容 |
|------|------|
| 测试位置 | 🆕 `tests/e2e/test_nhx1_race_soak.py`；🔱 existing identity/upload/GC/outcome races |
| 前置 | named barriers而非sleep；固定seed列表与迭代N；adapter matrix |
| 步骤 | 对Observation reserve、Item head/delete、Outcome/cancel、session cancel/TTL/consume、GC/new ref、outbox dead/requeue枚举关键ordering；每seed冷清理验证。 |
| PASS断言 | N×seed全effect-once/fail-loud；无hang/unknown state/双proof/丢bytes；winner/loser均typed；DB invariant每轮成立。 |
| 防假绿侦测 | `sleep()`碰运气、只跑单seed/单adapter、捕获异常但不查DB、重试直到绿、降低N、把flaky标rerun均FAIL。 |
| 跑法 | `uv run pytest -q tests/e2e/test_nhx1_race_soak.py --nhx1-seeds-file tests/fixtures/new_harvest_nhx1/race-seeds.v1.json` |
| 层/来源 | L2/L3/R soak；🆕+🔱 |

#### `NHX1-T29` — Real subprocess crash / old DB mega

| 字段 | 内容 |
|------|------|
| 测试位置 | 🆕 `tests/e2e/test_nhx1_subprocess_crash.py` |
| 前置 | app/worker/maintenance可分role子进程；barrier IPC；pre-fix DB/object root；fixed timeout |
| 步骤 | 在reservation、Outcome commit、promotion/catalog、quarantine/tombstone、outbox dead、cutover各窗SIGKILL；重启对应role；同时跑旧库migration/old pin/full retry/cleanup；检查FS+DB+API。 |
| PASS断言 | 每窗cold restart到成功/typed failure/safe pending；无terminal推进、invisible bytes、假proof、lost owner；old/new执行exact；超时硬FAIL。 |
| 防假绿侦测 | in-process hook/exception、事后SQL修复、只重启service对象不重启进程、忽略FS、延长timeout掩盖hang、只测空DB均FAIL。 |
| 跑法 | `uv run pytest -q tests/e2e/test_nhx1_subprocess_crash.py` |
| 层/来源 | process-crash/upgrade mega；🆕 |

#### `NHX1-T30` — Full repo / evidence executor / third review

| 字段 | 内容 |
|------|------|
| 测试位置 | 🆕 `tests/domain/test_nhx1_evidence_pack.py`；full `uv run pytest -q`；独立第三轮review |
| 前置 | NHX1-T01–NHX1-T29 PASS；owner live/S16 signoff；current clean commit；evidence dirs |
| 步骤 | 执行ruff/type/schema/full pytest及NHX1-T01–NHX1-T29固定命令；记录exit/stdout digest/UTC/profile/commit；核每work/Truth/test/风险；运行fake-green scans；第三轮独立review并写closure。 |
| PASS断言 | 全仓无排除绿；30 Test-ID四元组齐；current commit匹配；zero skip/xfail/adapter违规/fake PASS；owner gate齐；第三轮无未解释critical/high；50债务closed。 |
| 防假绿侦测 | 历史910/910或62 passed、只读tests.txt、命令未执行、dirty/不同commit、部分suite、skip/xfail、修改期待、review未独立、owner签名缺失均FAIL。 |
| 跑法 | `uv run ruff check api intake src tests`；仓库类型/schema命令（执行前在evidence manifest固定）；`uv run pytest -q`；`uv run pytest -q tests/domain/test_nhx1_evidence_pack.py` |
| 层/来源 | 全层退出硬闸；🆕；closure唯一入口 |

### 8.2 复用台账（沿用 / fork 的既有用例明细）

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/unit/test_ns6_phase2.py::test_stale_fencing_fail_does_not_kill_new_generation` | 🔱 fork/保留原node | 对齐新FenceConflict契约但保留新世代不死断言 | HEAD RED；P4后必须绿，禁xfail |
| `tests/unit/test_workflow_revision_compatibility.py` | 🔱 | 注入pre-fix rev1 fixture/rev2/pin inventory | 既有focused绿，但未覆盖rev1 digest漂移升级 |
| `tests/e2e/test_new_harvest_crash_windows.py` | 🔱 | 保留hook窗；NHX1-T16/NHX1-T29加真实进程/FS断言 | 既有多node绿；PROM-CAT不查final file |
| `tests/e2e/test_new_harvest_closed_set.py` | 🔱 | cells改compiler-derived；保留负格与L4 | 既有手写每strategy一格，覆盖不足 |
| `tests/e2e/test_nh4_upload_replay_race.py` | 🔱 | 加session owner/idempotency/barrier | 既有handle/GC race；无session隔离 |
| `tests/e2e/test_nh8_api_item_intents.py` | 🔱 | 扩7×3、zero Task、receipt、epoch races | 既有一条API item journey |
| `tests/e2e/test_nh5_facet_retrieval.py` | 🔱 | 加publication manifest/read snapshot/TOCTOU | 既有facet L4正例 |
| `tests/e2e/test_new_harvest_runtime_security.py` | 🔱 | actual args/process tree/prod profile/owner signoff | 既有security nodes；部分fixture形状 |
| `tests/e2e/test_inline_ingress_staging.py` | 🔱 | 移除raw sqlite inspection，扩全stage sentinel scan | 既有inline正文去audit；early stages仍复制state |
| `tests/unit/test_object_gc.py` / `test_nh4_upload_ttl_gc.py` | 🔱 | durable deletion/session job与cold restart | 既有reference-first正例；post-tombstone窗缺失 |
| `tests/domain/test_nh9_evidence_pack_checker.py` | 🔱 | NHX1 checker实际执行命令，不仅查文件字符串 | HEAD checker不执行命令 |
| `tests/e2e/test_nh1_nh9_review_fixes.py` | ♻️ 沿用+补断言 | 作为regression，不得单独证明全VF | 7个focused修复绿，覆盖声明曾过宽 |

### 8.3 分层与跑法（各类型在哪跑、何时跑）

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | 当前Phase对应unit/integration/contract固定node | L1/L2/契约 | 每个工作项提交前；每Phase持续 |
| Phase EXIT | 该Phase所有Test-ID完整命令 | 该Phase最低层 | 严格解锁下一个Phase |
| spike/mega | NHX1-T06/NHX1-T08/NHX1-T09/NHX1-T13/NHX1-T19/NHX1-T23/NHX1-T26/NHX1-T27 | L2–L4/upgrade | 对应Phase末 |
| soak | NHX1-T04/NHX1-T05/NHX1-T07/NHX1-T11/NHX1-T14/NHX1-T15/NHX1-T20/NHX1-T24/NHX1-T28 | R/S | 对应Phase EXIT + 最终重跑 |
| process-crash | NHX1-T16/NHX1-T29 | 真子进程/FS/DB | Phase 5/9 EXIT |
| live owner gate | NHX1-T22-E自动化 / NHX1-T22-O签收 | L3/L4/S | Phase 6 E完成后进入Phase 7；Phase 9 final前E+O均须PASS |
| full closure | NHX1-T30 | 全层 | 仅Phase 9；当前commit一次性执行 |

每个Phase解锁命令将在执行前写入 `docs/evidence/new-harvest/AP-NHX1/manifest.json`，不得用glob导致未来新增test未经审查自动进入/退出分母。NHX1-T22展示的glob只是计划阅读缩写，执行证据必须展开为固定node清单。

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖 existing-object新cleaner/validator upgrade（`T-O-420`）→ 独立future upgrade charter；NHX1测试必须反向断言无该intent/旁路。
- 不覆盖 raw object download/export、remote object adapter → S13未来QNA；NHX1-T15/NHX1-T16只验证现local CAS/session/ref。
- 不覆盖第五kind/live provider connector → future intake charter；registered API仍以typed frozen records测试。
- 不覆盖通用Workflow DSL/JOIN/loader → future workflow-platform charter；NHX1-T27只由现有有界compiler生成。
- 不覆盖 external vector engine、UI实现、experiment评分。NHX1-T23证明API契约，非前端；NHX1-T30证明experiment不入closure。
- multi-writer数据库substrate不在本AP新增；NHX1-T21只证明single/concurrent profile truth与required readiness。
- 这些OOS不得变成“测试跳过”；对应test应验证API/registry无入口或manifest明确unsupported。

### 8.5 防假绿专章（全 Test-ID 强制侦测）

#### 8.5.1 全局保真法

1. 每个PASS必须四元组：`current commit SHA + 具名命令/node EXIT0 + 对应Truth/工作项 + UTC/profile`。
2. `skip/xfail/rerun-until-pass/degraded/未观察` 均不解锁Phase；owner外部gate只能使NHX1 blocked。
3. HTTP 2xx、Task succeeded、字段存在、64hex、表/文件存在、metric/alert名字、历史test count都不是承重PASS。
4. 数据/竞态测试必须断言DB owner/rowcount/digest/FS/proof/query，而非只断exception或response。
5. race使用barrier+固定seed，crash使用真process kill；sleep/hook只能辅助，不能替代。
6. L1/L2/L3/L4不可互换；每Test-ID最低层由主表锁死。
7. evidence executor必须从当前clean commit实际运行命令；stdout/manifest/commit不匹配即FAIL。

#### 8.5.2 逐 Test-ID 假绿探针矩阵

| Test-ID | 必须命中的真实性探针 | 明确禁止的替代物 | Detector / 失败条件 |
|---------|----------------------|--------------------|-------------------|
| NHX1-T01 | ID双向映射+语义owner+manifest digest | 表格行数/PASS文字 | 删除/重复任一VF后checker RED |
| NHX1-T02 | pre-fix非空DB+旧digest+中断resume | 空库migrate/当前builder伪fixture | fixture checksum/legacy row断言 |
| NHX1-T03 | AST零raw sqlite+原stale断言 | xfail/skip/换新test | marker/import/断言扫描 |
| NHX1-T04 | DB reservation/Task/attempt计数 | 只看201/409、串行模拟 | barrier+owner unique查询 |
| NHX1-T05 | 2 Snapshot/no-change fact/epoch/query | Task success/items=1 | lineage+head+serving+search断言 |
| NHX1-T06 | 同DB同keyfailed→retry | 换key/清库/改内存UUID | persisted UUID/envelope对账 |
| NHX1-T07 | 21格、非法零Task、late callback | 只测7 intent/Pydantic 422 | Task/Process count + transition/epoch |
| NHX1-T08 | frozen count=processed；stale整体fail | `continue`后success/执行期noop | target-set digest/count断言 |
| NHX1-T09 | persisted rev1执行+new rev2+retire gate | 空库/register成功/UPDATE旧digest | sequence/digest/pin inventory |
| NHX1-T10 | 13 registry cells+formula独立重算 | 字段存在/manifest alias/11th strategy | resolver+digest equality/inequality |
| NHX1-T11 | terminal前后全行集不变/domain终结 | 只断Conflict/手工SQLterminal | Process数/current/status/counts diff |
| NHX1-T12 | from-step edge正负全矩阵 | 图含guard/每strategy一格 | compiler hop manifest coverage |
| NHX1-T13 | upstream变更+external call count=0 | upstream仍同bytes/不计calls | counting adapter+artifact digest |
| NHX1-T14 | dead+owner同TX+predecessor | event/metric alone/原row复活 | transaction snapshot+lineage |
| NHX1-T15 | two sessions same bytes隔离 | same handle/pending最终0 | session/ref owner逐行断言 |
| NHX1-T16 | cold restart+FS inventory | hook-only/public handle unavailable | child PID kill+objects/quarantine scan |
| NHX1-T17 | 真SQL UPDATE/DELETE攻击+旧row bytes不变 | trigger名/64hex | before/after bytes+abort/correction |
| NHX1-T18 | DB+CAS+API response全sentinel扫描 | 只root validator/只response redaction | recursive persistence scan |
| NHX1-T19 | read snapshot内manifest membership | query有hit/publication_state | concurrent barrier+proof recompute |
| NHX1-T20 | 三executor proof+refs/files收敛 | search zero/intent存在 | owner graph/ref/file/status断言 |
| NHX1-T21 | 四role loop/claim/overall负例 | title/Container/all-only | task registry+claim+component matrix |
| NHX1-T22 | 非stub identity+L4+owner signoff | stub/glyph/import/which/503/skip | profile scan+call evidence+签名 |
| NHX1-T23 | strict response schema+cold-start no SQL | path200/硬编码namespace | OpenAPI schema+AST no DB+journey |
| NHX1-T24 | auth+CAS+receipt+audit+redaction | direct service/2xx/raw payload | route-level cross-team/stale/replay |
| NHX1-T25 | catalog↔emitter↔alert↔runbook双向 | 名字存在/手工set | static graph+runtime fault emission |
| NHX1-T26 | mismatch阻断+old data+interrupt+forward rollback | new Task works/清旧数据/old writer rollback | migration state/pin/ref/cold restart |
| NHX1-T27 | compiler-derivededge/state/13cell最低层 | 手写格/L1顶L4/删失败cell | manifest↔compiler↔executed evidence join |
| NHX1-T28 | 固定N×seed/barrier/DB invariant | sleep/flaky rerun/单seed | seed manifest+iteration log+timeout |
| NHX1-T29 | SIGKILL真实进程+old DB+FS/DB/API | exception/hook/同进程restart | PID/exit/cold bootstrap/file inventory |
| NHX1-T30 | current commit全命令实际EXIT0+第三审查 | 历史计数/tests.txt/PASS/部分suite | command executor+SHA/UTC/profile/review gate |

#### 8.5.3 假绿处置

- 任一Detector命中：对应Test-ID=`FAIL(fake-green)`，其Phase与全部后继保持blocked。
- 禁止通过修改test expectation、移除cell/seed、降低最低层、扩大timeout、添加skip/xfail来处理；必须修生产/fixture/harness根因。
- `pre-existing` 仅允许带 `git merge-base + 首个失败commit + 当前复现` 三证据；仍不解锁NHX1。
- Phase 9发现假绿须回到所属Phase，修复后从该Phase EXIT开始顺序重跑到NHX1-T30。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| R-NHX1-01 串行周期长 | 9 Phase无并行，任一返工放大关键路径 | high | Phase EXIT短途/证据先行；变更小批提交；失败回owner Phase后顺序重跑，不跨Phase偷修 |
| R-NHX1-02 migration伪造历史 | backfill新actual/session/evidence到legacy | critical | 025+ expand-only；legacy_verdict；NHX1-T02/NHX1-T17 SQL/bytes证据；migration独立review |
| R-NHX1-03 rev1 fixture不真实 | 用当前builder反推旧图导致upgrade假绿 | critical | fixture来源commit/checksum；NHX1-T02/NHX1-T09校验旧digest与persisted row |
| R-NHX1-04 ItemEpoch冲突增多 | 单epoch较保守，合法并发败者上升 | medium | typed conflict+receipt+重读；先正确后测吞吐；不得退回LWW |
| R-NHX1-05 cross-FS/DB无原子事务 | promote/catalog、quarantine/tombstone crash | critical | durable session/deletion job；NHX1-T16/NHX1-T29真kill；不可见文件inventory |
| R-NHX1-06 evidence/manifest体量 | append-only correction与publication manifest增加存储 | medium | 分层retention/compact projection；事实不删；后台bounded audit；容量metric |
| R-NHX1-07 operator写面越权 | restart/requeue/stop误伤新generation或跨Team | critical | token+内网+team+expected generation+audit+receipt；NHX1-T24攻击矩阵 |
| R-NHX1-08 debug/正文/secret泄漏 | stage/operator surface扩张 | critical | CAS-first、registered redaction、无raw GET、全存储sentinel扫描NHX1-T18/NHX1-T24 |
| R-NHX1-09 role配置漂移 | api/worker/maintenance部署错误导致重复loop或缺owner | high | role manifest、启动互斥、lease owner、role-specific ready；NHX1-T21 |
| R-NHX1-10 readiness误绿 | configured required未进入overall或supervisor静默 | high | generated required set、negative probes、failure threshold、signals；NHX1-T21/NHX1-T25 |
| R-NHX1-11 production外部gate | 真模型/binary/S16签收不可由代码保证 | critical | T-O-419：ready-for-owner但NHX1 blocked；NHX1-T22/NHX1-T30拒skip/stub |
| R-NHX1-12 public v2兼容 | strict schema/error/session字段影响现client | high | v1 alias/compat window、dual contract tests、catalog version；NHX1-T23/NHX1-T26 |
| R-NHX1-13 physical purge不可逆 | 错owner graph/retention导致误删 | critical | snapshot owner graph、hold、grace、double fence、proof、backup/restore drill；NHX1-T20/NHX1-T29 |
| R-NHX1-14 dead owner误杀 | advisory误标critical或stale generation | high | per-kind manifest+generation CAS；NHX1-T14；default unknown kind fail bootstrap |
| R-NHX1-15 fake-green回潮 | 历史PASS、hook、字段存在、部分suite替代产品证明 | critical | §8.5逐test detector+command executor+第三轮review；NHX1-T01/NHX1-T30 |
| R-NHX1-16 race测试flaky | sleep/时序依赖造成偶然绿红 | high | named barriers、fixed seeds/N、hard timeout、DB invariant；NHX1-T28 |
| R-NHX1-17 full repo harness | sqlite3-on-Turso等pre-existing使最终阻塞 | high | Phase 1先Port化；NHX1-T03/NHX1-T30不接受甩锅或排除 |
| R-NHX1-18 dirty worktree/并行文件 | 现有未跟踪review/design属于用户资产 | medium | 只改本AP授权文件和执行期明确目标；提交前path-scoped diff；不清理其它untracked |
| R-NHX1-19 scope偷渡upgrade/DSL/raw GET | “还全部deferred”被误解为扩产品 | high | §2 OOS+T-O-420+NHX1-T01 coverage/architecture scan；发现即STOP |

### 9.2 约束与前提

- **技术前提**：HEAD `ba099ee`；migrations 001–024 checksum不可改；新DDL从025开始；所有服务依赖Persistence/Object/Inference ports而非driver/path。
- **运行时前提**：NHX1-T22/NHX1-T30需要真实prod-compatible parser/browser/OCR/model及S16 owner窗口；缺件不允许执行态close。
- **组织协作前提**：migration、public contract、operator control、security/physical delete各需独立review；第三轮reviewer不得只看closure claim。
- **上线 / 合并前提**：每Phase path-scoped diff干净、Phase EXIT全PASS、evidence四元组已append；最终NHX1-T01–NHX1-T30与owner gate齐。
- **数据前提**：pre-fix fixture与生产inventory必须先备份/只读；任何destructive contract/purge只在Phase 8/retention gate后。
- **串行前提**：禁止跳过Phase或把后Phase工作“提前顺手修”；若跨Phase接口必改，回Phase 2 revision并重跑后继。

### 9.3 文档同步要求

- 需要同步更新的设计文档：`docs/eval/new-harvest/after-2nd-pass-review-coherent-fixes-design.md`（9 AP包装改为单NHX1串行Phase；决策状态引用T-O-408..422）。
- 需要同步更新的todo：`docs/plan/new-harvest/todo-list.md` append NHX1 P1→P9 gated链；不得改历史NH1–NH9完成记录。
- 需要同步更新的deferred ledger：`docs/closure/new-start/deferred-items-ledger.md` append“absorbed by AP-NHX1”与最终disposition；OOS项仍保留。
- 需要同步更新的API/ops说明：OpenAPI schema、role deployment、CommandReceipt/error registry、operator runbooks、cleanup/production gate。
- 需要同步更新的测试说明：`docs/evidence/new-harvest/AP-NHX1/manifest.json`、`tests.txt`、fake-green report与固定命令清单。
- 需要输出的closure：`docs/closure/new-harvest/AP-NHX1-coherent-debt-retirement-and-governance.md`，只在NHX1-T30和第三轮review通过后创建/标closed。

### 9.4 完成后的预期状态

1. 四通道从public admission到retrieval共享Source/Observation/ItemEpoch/session/replay法，无silent LWW、跨lifecycle迟到写或失败key死锁。
2. workflow rev2与rev1 exact共存并可有界retire；terminal Outcome单调，full retry零外部重抓，outbox dead有owner终态/受控requeue。
3. object/evidence/reference/cleanup在任一crash后收敛；stage无正文/secret复制；legacy事实有verdict而不被改写；delete最终物理收敛。
4. leaf-worker具备四role、truthful readiness、可发现capability与真实production gate；public/frontend/operator无需SQL完成发现、解释和typed恢复。
5. 当前commit的graph-derived L1–L4/race/crash/upgrade/full-repo证据齐，50项欠账为0，第三轮review无未解释critical/high。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

### 10.1 收口硬闸

1. **Phase链完整**：Phase 1–9每个EXIT均按顺序PASS，无跨Phase跳跃（NHX1-T01–NHX1-T30 evidence时间序列证明）。
2. **Coverage**：15 true-bug、18 partial、17 absorbed deferred全部verified；VF27设计守卫与VF52 body-cap回归仍绿（NHX1-T01/NHX1-T30）。
3. **Identity/lifecycle**：四kind Observation、ItemEpoch、7×3、failed retry、rebuild cardinality全绿（NHX1-T04–NHX1-T08）。
4. **Workflow/replay**：pre-fix rev1升级、rev2、13 binding、terminal Outcome、hop routes、zero-refetch、outbox owner全绿（NHX1-T09–NHX1-T14）。
5. **Object/evidence**：session、真实crash、SQL attack、secret sentinel、publication TOCTOU、三executor/physical purge全绿（NHX1-T15–NHX1-T20）。
6. **Runtime/ops**：四role、capability claim/readiness、真实10+3/S16、strict public、operator control、signals/error全绿（NHX1-T21–NHX1-T25）。
7. **Cutover**：shadow mismatch=0，new writer唯一，old pin/ref/job排空门与forward rollback drill通过（NHX1-T26）。
8. **Assurance**：compiler-derived cells 100%、race fixed N、subprocess crash/old DB、full repo/evidence executor通过（NHX1-T27–NHX1-T30）。
9. **Production owner gate**：NHX1-T22有真实model/binary/S16具名UTC/identity；缺任一则NHX1=blocked。
10. **第三轮review**：无未解释critical/high；新finding必须完成fix+重跑所属Phase→NHX1-T30，不能只登记defer。
11. **证据四元组**：30 Test-ID均有current commit+命令/node EXIT0+Truth/work+UTC/profile，checker实际验证。
12. **OOS零偷渡**：无existing upgrade/raw GET/fifth kind/DSL/external vector/experiment score进入DoD。

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS证据（四元组） | 状态 |
|----------|--------|---------|---------------------|------|
| 分母/fixture/harness真实 | P1-01..04 | NHX1-T01–NHX1-T03 | current commit + coverage/upgrade/harness nodes + T-O-408..422 + UTC | 未观察 |
| v2 schema/ports可前滚 | P2-01..05 | NHX1-T02/NHX1-T04/NHX1-T05/NHX1-T10/NHX1-T14/NHX1-T15/NHX1-T17/NHX1-T19/NHX1-T20/NHX1-T24/NHX1-T25/NHX1-T26 | commit + migration/attack/shadow nodes +相关Truth + UTC | 未观察 |
| Intake identity/lifecycle闭合 | P3-01..05 | NHX1-T04–NHX1-T08 | commit + e2e/race/query + T-O-408/409/421 + UTC | 未观察 |
| Workflow/replay/outbox闭合 | P4-01..06 | NHX1-T09–NHX1-T14 | commit + upgrade/route/outcome/replay/dead + T-O-410..412/422 + UTC | 未观察 |
| Object/evidence/cleanup闭合 | P5-01..06 | NHX1-T15–NHX1-T20 | commit + session/crash/SQL/security/query/purge + T-O-413/414/417 + UTC | 未观察 |
| Roles/readiness/production闭合 | P6-01..04 | NHX1-T21/NHX1-T22/NHX1-T25 | commit + role/live/security/signal + T-O-416/419 + owner UTC | 未观察 |
| Public/operator/obs/error闭合 | P7-01..04 | NHX1-T23–NHX1-T25 | commit + OpenAPI/cold-start/control/signal + T-O-415/418/422 + UTC | 未观察 |
| Cutover/retirement收敛 | P8-01..03 | NHX1-T09/NHX1-T17/NHX1-T20/NHX1-T26 | commit + inventory/drain/rollback/cold-start + T-O-411/414/417 + UTC | 未观察 |
| Graph/race/crash/full closure | P9-01..04 | NHX1-T27–NHX1-T30 | current commit + manifest/soak/kill/full/review + all Truth + UTC | 未观察 |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | §3全部P1-01..P9-04达到收口目标；50项债务零remaining；OOS零偷渡 |
| 测试 | §8 NHX1-T01–NHX1-T30全部PASS；Phase EXIT顺序、最低层、逐项假绿Detector与四元组齐 |
| 数据/迁移 | 025+空库/pre-fix库/中断/冷启通过；new writer唯一；old事实可解释；无非法改写/未知孤儿 |
| 安全 | TM-NHX1-01..07攻击向量全绿；public/operator分权；真实prod/S16签收齐 |
| 文档 | design/todo/deferred/API/runbook/evidence/第三轮review/closure全部同步且引用冻结Truth |
| 风险收敛 | §9 critical/high风险均有执行证据；无expired waiver、silent degraded或pre-existing甩锅 |
| 可交付性 | NHX1-T30 checker EXIT0，第三轮无critical/high，owner gate齐，AP/closure方可标`executed/closed` |

### 10.4 NOT-成功识别

任一以下情况成立，NHX1不得标`executed`或closure `closed`：

1. 任一Phase EXIT未PASS却进入后继；或把九Phase拆成独立“部分closed”规避总目标。
2. 任一NHX1-T01–NHX1-T30为skip/xfail/degraded/未观察/非current commit，或四元组缺项。
3. 使用空库、hook-only、sleep race、HTTP 2xx、Task succeeded、字段/表/文件存在、PASS字符串、历史测试计数替代承重断言。
4. 修改test expectation、删cell/seed、降L3/L4为L1、扩大timeout、rerun-until-pass来消除失败。
5. legacy evidence/rev1被UPDATE重写；cutover rollback恢复old writer；migration修改001/018–024 checksum。
6. full retry重新fetch/reenumerate；terminal Execution接受Outcome；dead critical owner仍ready/queued；repair绕过dead predecessor。
7. handle继续充session、cancel/TTL/consume按最新/全部；promoted final或tombstoned quarantine不可归因。
8. logical delete只做到search zero但refs/cleanup/bytes未收敛；或立即级联绕retention/hold/proof。
9. public暴露workflow selector/raw debug/任意control，operator缺token/team/fence/audit；secret/body sentinel任一持久化。
10. prod仍使用stub/glyph/fake handler、import/which/models-list、503或skip；S16/owner签名缺失却写closed。
11. existing-object upgrade、raw GET、第五kind、DSL、external vector、experiment评分进入工作或DoD。
12. graph-derived manifest与实际compiler/capability/Test evidence不一致，或手写缩减分母。
13. full repo有排除/adapter违规/未解释失败；第三轮review尚有critical/high未修。
14. Phase 9第一次发现功能bug后仅登记defer而未回owner Phase修复并重跑后继链。

---

## 附录 A · VF1–VF52 执行覆盖矩阵

| VF | 台账归属 | Owner工作项 | Test-ID | 执行态目标 |
|----|----------|-------------|---------|------------|
| VF1 | true-bug | P3-02 | NHX1-T05 | 不同Observation不压旧Snapshot，ChangeSet无悬挂 |
| VF2 | true-bug | P3-02 | NHX1-T05 | latest head由ItemEpoch CAS，零LWW |
| VF3 | partial | P3-01 | NHX1-T04 | reservation+Task同UoW，并发单winner |
| VF4 | partial | P3-03 | NHX1-T06 | failed Observation有typed retry出口 |
| VF5 | true-bug | P3-03 | NHX1-T06 | scatter先stable identity后freeze envelope |
| VF6 | partial | P4-05 | NHX1-T13 | full retry零HTTP refetch |
| VF7 | true-bug | P4-05 | NHX1-T13 | typed metadata context exact复制 |
| VF8 | true-bug | P3-04 | NHX1-T07 | deleted同keyadmission 409零Task |
| VF9 | partial | P3-04 | NHX1-T07 | deactivated ingest拒绝、transition真实 |
| VF10 | true-bug | P3-04 | NHX1-T07 | late callback受ItemEpoch fence |
| VF11 | partial | P3-04 | NHX1-T07 | 7×3非法格零Task/Process |
| VF12 | partial | P3-05 | NHX1-T08 | rebuild无silent skip，empty才noop |
| VF13 | true-bug | P4-03 | NHX1-T11 | terminal Execution拒绝迟到Outcome/推进 |
| VF14 | absorbed deferred | P3-04/P4-03 | NHX1-T07/NHX1-T11 | cancel first-wins，queued/cancelling不投failed |
| VF15 | true-bug | P4-03/P4-04 | NHX1-T11/NHX1-T12 | domain mismatch终结，route可达性前置 |
| VF16 | true-bug | P4-04 | NHX1-T12 | current-hop执法，删除整图guard误杀 |
| VF17 | true-bug | P4-01/P8-02 | NHX1-T09/NHX1-T26 | rev1 exact+rev2，升级不503 |
| VF18 | true-bug | P4-02/P5-03 | NHX1-T10/NHX1-T17 | selection使用真实fact digest |
| VF19 | partial | P5-03 | NHX1-T17 | evidence identity不可SQL改写 |
| VF20 | partial | P4-02 | NHX1-T10 | registered operation与clean strategy分账 |
| VF21 | partial | P4-01/P5-03 | NHX1-T09/NHX1-T17 | path/formula versioned，legacy可解释 |
| VF22 | partial | P5-01 | NHX1-T15 | hold按session cancel/consume |
| VF23 | partial | P5-02 | NHX1-T16 | pre-catalog final CAS有journal/reconcile |
| VF24 | partial | P5-02 | NHX1-T16 | tombstoned quarantine冷启destroy |
| VF25 | absorbed deferred | P5-06 | NHX1-T20 | artifact/source/generation/vector物理收敛 |
| VF26 | partial | P5-01 | NHX1-T15 | local object仅合法session/business ref |
| VF27 | n/a design guard | P5-01 | NHX1-T15 | 未占用pending可TTL，reserved Task不可TTL |
| VF28 | true-bug | P5-04 | NHX1-T18 | nested拒密+CAS-first stage，零正文泄漏 |
| VF29 | absorbed deferred | P6-03 | NHX1-T21 | CW required画像真实进入role readiness |
| VF30 | absorbed deferred | P6-04/P9-04 | NHX1-T22/NHX1-T30 | 真10+3+owner gate，stub不得close |
| VF31 | true-bug | P6-04 | NHX1-T22 | no-sandbox守卫钉actual args |
| VF32 | absorbed deferred | P6-02/P6-03 | NHX1-T21/NHX1-T22 | supply manifest决定claim/readiness |
| VF33 | absorbed deferred | P6-02/P7-01 | NHX1-T21/NHX1-T23 | capability manifest+只读目录，仍禁选图 |
| VF34 | partial | P7-01 | NHX1-T23 | Task投影kind/mode/policy/actual/item/observation |
| VF35 | absorbed deferred | P7-02 | NHX1-T23 | Item/Namespace lists与source filter/cold-start |
| VF36 | true-bug | P7-02 | NHX1-T23 | single item从root outcome投影 |
| VF37 | absorbed deferred | P7-02 | NHX1-T23 | waiting保六态但有phase/reason |
| VF38 | partial | P7-03 | NHX1-T24 | public error+operator Process/Stage/Fact debug |
| VF39 | absorbed deferred | P7-04 | NHX1-T25 | DiagnosticSink生产接线与读取 |
| VF40 | absorbed deferred | P7-04 | NHX1-T25 | metric/alert emitter-runbook零孤儿 |
| VF41 | absorbed deferred | P7-04 | NHX1-T25 | admission/TTL/cancel/repair低敏signals |
| VF42 | absorbed deferred | P6-03/P7-04 | NHX1-T21/NHX1-T25 | supervisor failures进ready/diag/alert |
| VF43 | partial | P4-06/P7-03 | NHX1-T14/NHX1-T24 | dead终结owner+typed requeue/repair/restart/stop |
| VF44 | absorbed deferred | P7-03 | NHX1-T24 | mutation receipt区分applied/replayed/noop |
| VF45 | partial | P7-04 | NHX1-T25 | lifecycle/rebuild/metadata disposition与metric正确 |
| VF46 | absorbed deferred | P7-02 | NHX1-T23 | noop/exhausted_zero可读 |
| VF47 | absorbed deferred | P4-03/P7-04 | NHX1-T11/NHX1-T25 | stale fence业务回滚+独立diagnostic |
| VF48 | absorbed deferred | P6-01 | NHX1-T21 | leaf-worker成为显式deployment role |
| VF49 | true-bug | P1-03/P9-03 | NHX1-T03/NHX1-T29 | 修红测+真实process crash/legal edge |
| VF50 | partial | P1-01/P9-04 | NHX1-T01/NHX1-T30 | 第一轮名义fix均有专项反例/证据 |
| VF51 | absorbed deferred | P7-04 | NHX1-T25 | v2 error registry+legacy alias结束双轨 |
| VF52 | stale-rejected guard | P9-04 | NHX1-T30 | 保留request body stream cap回归，不做错误修复 |

## 附录 B · 历史 deferred / carry-over 承接

| 历史ID / 集合 | Owner工作项 | Test-ID | 最终处置 |
|----------------|-------------|---------|----------|
| NH-VF3.r | P5-04 | NHX1-T18 | acquire/decode/clean正文改CAS refs |
| NH-VF4.r | P5-05 | NHX1-T19 | publication manifest+read snapshot |
| NH-VF9.r | P3-04/P3-05 | NHX1-T07/NHX1-T08 | 7×3与rebuild cardinality闭合 |
| NH-VF10 | P3-03/P4-05 | NHX1-T06/NHX1-T13 | attempt与exact full replay分账 |
| NH-VF13 / NH-VF38 | P5-01/P5-02 | NHX1-T15/NHX1-T16 | session promotion journal消除orphan |
| NH-VF14.r / S16 | P6-04 | NHX1-T22 | 真模型/binary/security owner gate |
| NH-VF21 / NH-VF39 | P4-01/P8-02 | NHX1-T09/NHX1-T26 | rev2+old pin retirement |
| NH-VF27.r | P6-04/P9-03 | NHX1-T22/NHX1-T29 | process-group kill+lease cold recovery |
| NH-VF29 | P9-04 | NHX1-T30 | current full repo无排除硬闸 |
| NH-VF36 | P8-03 | NHX1-T26 | 删除无writer的building/retiring形状 |
| NH-VF37 | P6-03/P7-04 | NHX1-T21/NHX1-T25 | typed conflict+诚实single-writer profile |
| NH-VF41.r / NH-VF42 | P1-04/P9-04 | NHX1-T01/NHX1-T30 | 执行型evidence checker/测试治理 |
| NS1-V11/NS2-O7/NS5-VF86/NS6-VF86 | P1-03 | NHX1-T03/NHX1-T30 | adapter-aware harness，去sqlite3-on-Turso |
| NS5-T60 | P9-01/P9-04 | NHX1-T27/NHX1-T30 | generation→vector→retrieval L4 mega |
| NS5-VF30.r/37.r/97 + NS6-VF97 | P6-04 | NHX1-T22 | PDF/model/browser/OCR/Vision production profile |
| NS5-VF66.r/NS6-VF25.r | P5-02 | NHX1-T16 | object directory/CAS orphan reconciliation |
| NS5-VF36 | P5-04 | NHX1-T18 | raw/clean envelope authority分离 |
| NS5/NS6-VF62 | P6-04 | NHX1-T22/NHX1-T28 | heartbeat/fence后bounded pool并发 |
| NS5-VF91.r | P6-03 | NHX1-T21/NHX1-T30 | CW profile/adapter证据 |
| NS6-VF11.r | P6-04/P9-03 | NHX1-T22/NHX1-T29 | process-tree termination |
| NS6-VF20 | P2-05/P5-05 | NHX1-T19 | retrieval read snapshot |
| NS6-VF4.r | P1-01/P2-03 | NHX1-T01/NHX1-T17 | 全schema evidence/projection inventory |
| NS6-VF15.r | P3-02/P4-05 | NHX1-T05/NHX1-T13 | replay/adoption统一法 |
| NS6-VF36.r | P7-04 | NHX1-T25 | bounded diagnostic queue/drop signal |
| NS6-T01-hotfix | P9-03 | NHX1-T29 | 真子进程barrier替代BEGIN sleep门 |
| experiment | — | NHX1-T30负向guard | 继续OOS，不进closure |

## 附录 C · 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| `v0.1` | `2026-08-31` | `GPT` | 消费Q28–Q42/T-O-408..422，收敛为单一NHX1九Phase串行DAG；定义P1-01..P9-04、NHX1-T01..NHX1-T30、逐测试详细规格/假绿探针、风险与DoD |

> 执行日志 §11 仅在文档状态进入 `executed` 时按 `.adocs/templates/code-execution-log.md` append；draft阶段不伪造执行结果。

---

## 11. 执行日志回填（append-only）

> 执行者：`Codex`
> 执行时间：`2026-08-31`
> 文档状态：`draft → executing`
> 当前代码改动统计：`Phase 1：12 个生产/测试文件修改，11 个文本 fixture/tool 新建，1 个 binary DB fixture 新建；schema bump 0`

- **实际执行摘要**：Phase 1 已按 `P1-01..P1-04` 完成 denominator、pre-fix/rev1 fixture、adapter-aware harness 与 execution-backed evidence checker；后继 Phase 尚未施工。
- **Phase 偏差（计划 vs 实际）**：
  - `D-P1-01 (substrate-fit)`：P1 先落 `PersistenceInspectorPort.read_snapshot()`，以便四个既有 e2e 在同一 adapter handle 上读取；P2 将沿同一 contract 扩展 migration/shadow 语义，未切业务 writer。
  - `D-P1-02 (fixture-shape)`：rev1 manifest 冻结三份 kind-family canonical definition；pre-fix DB 另含真实 registry graph、legacy selected-output v1、legacy upload-pending 与 failed Execution，避免空库/当前 builder 假绿。
- **阻塞与处理**：
  - `P1-03` 指定 stale-fence node 在基线与当前 Phase 1 commit 均稳定 RED，failure signature 为 `ConflictError/stale-process-fence`；按计划登记到 `known-red.v1.json`，保持原状态断言，交 `P4-03/NHX1-T11` 修绿。
- **测试发现**：Phase 1 EXIT 固定命令 `17 passed`；全仓 ruff `All checks passed`；known RED 为预期 `1 failed`，无 skip/xfail/degraded。
- **后续 handoff**：仅解锁 Phase 2 expand-only schema/ports；001/018–024 checksum、rev1 manifest 与 legacy evidence bytes 为只读基线。

### 11.1 Phase 1 — Truth denominator / fixtures / harness

| 工作项 | 状态 | PR / commit | 实际落点 | 备注 |
|--------|------|-------------|----------|------|
| `P1-01` | `✅ done` | `9542f50` | `tests/fixtures/new_harvest_nhx1/coverage.v1.json`；`tests/domain/test_nhx1_truth_and_coverage.py` | 52 VF、50 debt、2 guards、15 Truth 与历史 deferred 双向可重算；digest `325f05f6…` |
| `P1-02` | `✅ done` | `9542f50` + `000e1be` | `rev1-manifest.json`；`pre-fix-024.db`；`test_nhx1_persisted_upgrade.py` | fixture SHA-256 `de069bfd…`；24 migrations；三 rev1 graph + 非空 legacy rows |
| `P1-03` | `✅ done` | `9542f50` | `src/persistence/ports.py`；SQLite/Turso adapters；四个 e2e | e2e raw `sqlite3.connect` 扫描零违规；known RED 如实登记，未宣称 bug 已修 |
| `P1-04` | `✅ done` | `9542f50` | `tests/nhx1_evidence.py`；`tests/domain/test_nhx1_evidence_pack.py` | 实际执行命令并校验 full SHA/UTC/profile/digest/layer；假 PASS/SHA/skip/xfail/降层均 RED |

### 11.2 Phase 1 证据四元组与时序

| 时点 | 步骤 | 决策 / 产出 |
|------|------|-------------|
| `2026-08-31T01:49:46Z` | `NHX1-T01/T02/T03/T30 Phase-1 subset` | commit `000e1be8707580c6c4ab984fc17e721a29a53c9a` + 固定 pytest command + `17 passed` + profile `test/sqlite+turso` |
| `2026-08-31T01:49:46Z` | static gate | commit `000e1be8707580c6c4ab984fc17e721a29a53c9a` + `uv run ruff check api intake src tests` + EXIT0 + profile `local` |
| `2026-08-31T01:50:35Z` | 修前 RED 保真 | commit `000e1be8707580c6c4ab984fc17e721a29a53c9a` + original stale-fence node + expected EXIT1/`stale-process-fence` + `T-O-422/P4-03` handoff |

### 11.3 Phase 1 文档状态

`draft → executing（2026-08-31）`。Phase 1 工程 EXIT 完成；residual `stale-process-fence` 不是本 Phase 假绿或 deferred，严格 handoff → `Phase 4 / P4-03 / NHX1-T11`。

### 11.4 Phase 2 — Canonical schema / ports / registries

> 执行时间：`2026-08-31T02:07:52Z`
> 代码改动统计：`10 文件；4 migration bump（025–028）；28 个 additive table/ledger shape，既有 001/018–024 零改动`

- **实际执行摘要**：
  - `P2-01`：新增 Observation/Attempt/Snapshot link/acceptance fact 与单一 ItemEpoch transition authority；Task/Execution 仅加 nullable v2 coordinates，不 backfill 假事实。
  - `P2-02`：新增 ObjectUploadSession、promotion journal、deletion/cleanup job 与 exact session ref coordinate；legacy upload pending 保持原 bytes/owner 并无伪 session。
  - `P2-03`：新增 typed ProcessingBinding、selection assertion v2、verification/correction、publication manifest/member；新 evidence 表 14 个 append-only trigger 生效，legacy selected-output 不 UPDATE。
  - `P2-04`：outbox 增 owner/generation/criticality/budget/predecessor；新增 CommandReceipt、capability/error/alias/signal durable projection与 code-owned registry bootstrap。
  - `P2-05`：`read_snapshot()` 已在 P1 建立；本 Phase 增 durable migration cursor、shadow mismatch/cutover state 与 idempotent resume service。
- **Phase 偏差（计划 vs 实际）**：
  - `D-P2-01 (substrate-fit)`：Snapshot↔Observation 使用 additive link table而非重建 `mkb_intake_snapshots` 加强制 FK，避免修改001或在旧行上伪造 observation；新 writer 在P3只写 link。
  - `D-P2-02 (ordering)`：error/outbox code-owned definition在P2投影，实际 public error enforcement与dead-owner transition仍严格留在P7/P4。
- **阻塞与处理**：expanded `unit+integration+domain` 回归仅命中 P1 已登记的 stale-fence known RED；无新增失败。该 RED 不由P2修改期待，继续交P4。
- **测试发现**：固定 Phase-2 EXIT `65 passed`；SQLite/Turso parity、非空024升级、重复migrate、冷启cursor resume、shadow mismatch阻断、append-only/invalid-state攻击均绿；ruff全绿。
- **后续 handoff**：Phase 3 只能消费025的Observation/ItemEpoch contract；不得修改025–028 checksum或提前启用P4/P5/P7 writer。

| 工作项 | 状态 | PR / commit | 实际落点 | 备注 |
|--------|------|-------------|----------|------|
| `P2-01` | `✅ done` | `2ccfebb` | `025_nhx1_observation_item_epoch.sql` | T-O-408/409；legacy count零伪造 |
| `P2-02` | `✅ done` | `2ccfebb` | `026_nhx1_object_sessions_cleanup.sql` | T-O-413/417；session/ref/job分账 |
| `P2-03` | `✅ done` | `2ccfebb` | `027_nhx1_evidence_v2.sql` | T-O-412/414；v2 append-only、legacy bytes不变 |
| `P2-04` | `✅ done` | `2ccfebb` + `c9874ca` | `028_nhx1_ops_contracts.sql`；`governance.py`；`governance_registry.py` | T-O-418/422；registry digest fence |
| `P2-05` | `✅ done` | `c9874ca` | `nhx1_migration.py`；`test_nhx1_schema_expand.py` | cursor/revision/mismatch durable，adapter parity |

| 时点 | 步骤 | 决策 / 产出 |
|------|------|-------------|
| `2026-08-31T02:07:52Z` | Phase 2 EXIT | commit `c9874cadfaf0bd96a71475b5eb359ee987d2fce1` + fixed 13-file pytest command + `65 passed` + profile `sqlite+turso` |
| `2026-08-31T02:07:52Z` | static/checksum gate | commit `c9874cadfaf0bd96a71475b5eb359ee987d2fce1` + ruff EXIT0 + 001/018–024 path diff empty + profile `local` |

### 11.5 Phase 2 reopen correction — no-change ItemEpoch law

- **发现时点**：Phase 3 acceptance writer 首次消费 `mkb_intake_acceptance_facts` 时发现 025 把 `no_change` 错误约束为 epoch+1。
- **处置**：按 DAG 回退重开 P2；未进入 live 的 025 CHECK 修为三条互斥公式：`changed → +1`、`no_change → same epoch`、`observed_not_adopted → no Item coordinates`。没有通过绕过 fact writer、虚增 epoch 或修改测试期待处理。
- **证据**：commit `2908e8f`；clean detached worktree；固定 Phase-2 command `64 passed`、零 skip/xfail；ruff EXIT0；修订后 025 SHA-256 `6b947f86e8752788091e1d2a0138f155d761a5b60682a416a4e514cbba76f601`。
- **环境差异**：第一次 clean-worktree 扩大命令中的历史 `test_r3_turso_evidence_ready.py` 因仓库外 `R2` copy 不存在而 skip；它不是P2分母，最终固定命令移除该R3环境证据节点，并保留本Phase自有 SQLite/Turso parity node，最终证据零skip。
- **DAG 恢复**：修正后的 P2 EXIT 重新PASS，Phase 3 恢复 `in_progress`。

### 11.6 Phase 3 — Intake identity / ItemEpoch / lifecycle

> 执行时间：`2026-08-31T02:56:34Z`
> 代码改动统计：`15 个文件；ObservationReservation/admission matrix 新增；Task/ingest/acceptance/scatter/rebuild writer 收紧；schema bump 0`

- **实际执行摘要**：
  - `P3-01`：v2 显式 observation key；SourceIdentity 与 ObservationReservation 分账；Task/root/Attempt 在同一 UoW；same key exact replay 复用原 Task，异 fingerprint 稳定 409，并发双建单 winner。
  - `P3-02`：每次 Observation 使用新 Snapshot；same semantic content 复用 Revision 并追加 `no_change` fact；changed content 以现有 `row_revision` 作为唯一 ItemEpoch CAS；acceptance/scatter 写 durable link/fact/epoch transition。
  - `P3-03`：acquire 前读取 durable Source/Observation 坐标，失败采集转 `failed` attempt；typed retry 只新增 attempt generation，未新建 Source/Snapshot。
  - `P3-04`：7 intent × 3 lifecycle matrix 在 admission 闸前执行；deactivated/deleted ingest、deleted key 与 stale callback fail-closed。
  - `P3-05`：rebuild scope 保持 frozen target；实际 identity/latest drift 整体失败；active-but-not-serving/reactivate 维持可解释 typed no-op，非初始空集伪装。
- **Phase 偏差（计划 vs 实际）**：
  - `D-P3-01 (substrate-fit)`：对尚未存在 Item 的并行 Observation 不采用“按最新 UUID LWW”；acceptance 等待 durable item 后按 expected epoch/revision fingerprint 判定，避免 UUID 漂移和静默覆盖。
  - `D-P3-02 (compat)`：existing `index.rebuild` 在 reactivate 后 serving pointer withdrawn 的场景保留 success/no-op 兼容；只有 frozen `latest`/lifecycle identity drift 才整体失败。
- **阻塞与处理**：无新增 blocker；P1 known stale-fence RED 仍仅交 P4，不在 P3 吞掉 `ConflictError`。
- **测试发现**：Phase 3 固定 EXIT `38 passed`；`ruff check api intake src tests` EXIT0；旧 identity/scatter/NH8 lifecycle 回归均通过；没有 skip/xfail。
- **后续 handoff**：Phase 4 消费 `observation_uuid/current_attempt_generation/expected_item_epoch`，负责 terminal Outcome、rev2/old pin、exact replay 与 outbox owner；不得在 P4 重建另一套 identity counter。

| 工作项 | 状态 | PR / commit | 实际落点 | 备注 |
|--------|------|-------------|----------|------|
| `P3-01` | `✅ done` | `6da19ea` | `observation_reservations.py`；`task_create.py`；`test_nhx1_observation_identity.py` | T-O-408；单 winner/replay/409 |
| `P3-02` | `✅ done` | `6da19ea` | `acceptance_snapshot.py`；`acceptance_scatter.py`；`test_nhx1_item_epoch.py` | T-O-409；changed/no_change facts 与 epoch CAS |
| `P3-03` | `✅ done` | `6da19ea` + `b6769e1` | `acquisition_ingest.py`；`test_nhx1_scatter_retry.py` | T-O-408/410；同 Source + attempts 1→2 |
| `P3-04` | `✅ done` | `6da19ea` | `admission_matrix.py`；`targets.py`；`test_nhx1_intent_state_matrix.py` | T-O-409/421；21 cells |
| `P3-05` | `✅ done` | `6da19ea` + `b6769e1` | `index_rebuild_plan.py`；`test_nhx1_rebuild_cardinality.py` | T-O-409；stale whole-fail/no-op distinction |

| 时点 | 步骤 | 决策 / 产出 |
|------|------|-------------|
| `2026-08-31T02:56:34Z` | Phase 3 EXIT | commit `b6769e10222bc9329d470adda50604e085b64cbd` + fixed 10-file pytest command + `38 passed` + profile `test/sqlite+turso` |
| `2026-08-31T02:56:34Z` | static gate | commit `6da19ea`/`b6769e1` + `uv run ruff check api intake src tests` + EXIT0 + profile `local` |

### 11.7 Phase 4 — Workflow revision / replay / Outcome

> 执行时间：`2026-08-31T03:34:15Z`
> 代码改动统计：`28 文件；rev1 frozen manifest 3 graphs；rev2 activation；typed binding/selection、Outcome fence、exact retry、outbox owner/requeue；schema bump 0`

- **实际执行摘要**：
  - `P4-01`：kind-family 当前定义统一升 immutable revision 2；ba099ee rev1 canonical/compiled manifest 作为独立 compatibility loader，persisted rev1 可在 rev2 active 时物化。
  - `P4-02`：10 clean strategy 与 3 provider operation 使用 `ProcessingBinding` typed union；seal assertion 写 family/key/version/digest；selected-output 读取 RepresentationFact.digest，和 manifest digest 分离。
  - `P4-03`：terminal Execution/Process 对迟到或不同 Outcome fail-closed；materialization 检查 Execution CAS rowcount；stale failure 不得杀新 generation；worker 将 domain conflict 终结为 typed failure。
  - `P4-04`：reacquire guard 只按当前 `decode_web_static` hop 判断，去除全图 plan guard 误杀；既有 declared/undeclared edge regression 保留。
  - `P4-05`：full Task retry 仅接受已 accepted Observation 的 verified raw artifact；新 Execution 复用 observation/snapshot/graph/manifest/context；HTTP external call count 保持 0；无 frozen input API 409。
  - `P4-06`：outbox 写入 owner/generation/criticality/budget/dead code；critical dead 同事务终结 Execution/Task；advisory 不误杀；requeue 新 delivery 保留 `retry_of_outbox_id` 与 CommandReceipt。
- **Phase 偏差（计划 vs 实际）**：
  - `D-P4-01 (compat substrate)`：未改写 001/018–024 或 persisted rev1，采用 checked-in `src/workflows/kind_family_v1_manifest.json`；现有 workflow key 保持 wire 兼容，仅 revision coordinate 由 registry 管理。
  - `D-P4-02 (fallback evidence)`：旧 synthetic runtime fixtures 没有 RepresentationFact 时保留显式 legacy-derived digest 兼容路径；生产有 fact 时强制 v2 selection assertion，未把 fallback 宣称为 verified fact。
- **阻塞与处理**：Phase 1 known stale-fence node 已在本 Phase 修绿，原“新 generation remains running”断言保留；无 skip/xfail/degraded。
- **测试发现**：Phase 4 固定 EXIT `40 passed`；全 repo `ruff` EXIT0；rev1/rev2、binding/fact digest、terminal fence/domain failure、declared route、exact replay、outbox owner/dead/requeue 均绿。
- **后续 handoff**：Phase 5 允许消费 ProcessingBinding/evidence v2 与 outbox owner，但不得原地 UPDATE legacy evidence/rev1；object session/journal、CAS-first 和 cleanup 才能推进 physical convergence。

| 工作项 | 状态 | PR / commit | 实际落点 | 备注 |
|--------|------|-------------|----------|------|
| `P4-01` | `✅ done` | `386f829` | `kind_family.py`；`kind_family_v1_compat.py`；`kind_family_v1_manifest.json` | T-O-411；rev1 exact + rev2 active |
| `P4-02` | `✅ done` | `386f829` | `actual_s05.py`；`runtime_materialize.py`；`governance.py` | T-O-412/414；10+3 typed union、fact digest |
| `P4-03` | `✅ done` | `386f829` | `runtime_outcome.py`；`worker.py`；`runtime_materialize.py` | T-O-410/422；terminal/domain/stale fence |
| `P4-04` | `✅ done` | `386f829` | `runtime_materialize.py`；`test_nh3_declared_reacquire.py` | T-O-411/412；current-hop reachability |
| `P4-05` | `✅ done` | `386f829` | `task_commands.py`；`acquisition_ingest.py`；`acceptance_snapshot.py`；`test_nhx1_exact_replay.py` | T-O-410；zero refetch |
| `P4-06` | `✅ done` | `386f829` | `runtime_core.py`；`runtime_outbox.py`；lifecycle/scatter enqueue writers；`test_nhx1_outbox_owner.py` | T-O-422；owner terminal/requeue lineage |

| 时点 | 步骤 | 决策 / 产出 |
|------|------|-------------|
| `2026-08-31T03:34:15Z` | Phase 4 EXIT | commit `386f829bfdf9754dca4a5024cbbb08357fb41c6c` + fixed 11-file pytest command + `40 passed` + profile `test/sqlite+turso` |
| `2026-08-31T03:34:15Z` | static gate | commit `386f829bfdf9754dca4a5024cbbb08357fb41c6c` + `uv run ruff check api intake src tests` + EXIT0 + profile `local` |

### 11.8 Phase 5 — Object / evidence / physical convergence

> **执行时间**：`2026-08-31T04:38:50Z`
> **代码改动统计**：`25 文件；8 个新建；migration 029；对象会话/推广日志/evidence/manifest/cleanup/GC 与 CAS-first 读写收口`

- **实际执行摘要**：
  - `P5-01`：显式 `Idempotency-Key` 绑定 team-scoped opaque `ObjectUploadSession` token；同命令 replay 返回同 token，同 bytes 的不同命令保持独立 session；legacy 无 key 保留旧 digest replay 和 pending hold 兼容；reserve/consume/cancel/stat 均按精确 session CAS。
  - `P5-02`：上传 session 与 promotion journal 持久化 promoted/catalog-committed 状态；quarantine reconcile 仅在 catalog tombstone 后物理销毁，避免 live bytes 被扫描器误删。
  - `P5-03`：migration `029_nhx1_evidence_identity_guards` 为 generation/intake artifact identity 与 delete 加 SQL 不可变/append-only 触发器；legacy verification 保留 verdict，correction 追加独立事实。
  - `P5-04`：raw/decoded/clean/collection 在执行时按 CAS handle hydration，envelope/stage/audit 递归移除正文、secret、path 与 URL；不把 sentinel body 复制进 durable projection。
  - `P5-05`：vector publish 写 ordered publication manifest/member set；retrieval 走 `read_snapshot()` 并在 manifest 存在时严格 membership 验证，TOCTOU 篡改 fail-closed。
  - `P5-06`：新增五 substrate cleanup job/step/proof executor，按 reference-first 释放；hold 进入 typed blocked，retention 后各 substrate 产生 terminal proof，再交 object GC。
- **Phase 偏差（计划 vs 实际）**：
  - `D-P5-01 (legacy-compat)`：显式 session 语义只对带 `Idempotency-Key` 的新命令公开；无 key 的 NH4 调用保留 digest replay 与每调用 pending hold，避免破坏既有客户端，同时不把 legacy handle 误充 session token。
  - `D-P5-02 (schema-expand)`：artifact identity 保护以新增 migration `029` 实现，未修改 `001` 或 `018–024` 历史 DDL/checksum；legacy evidence 只新增 verifier/correction 行。
- **阻塞与处理**：Phase 5 首轮兼容回归发现旧 NH4 并发无 key 期望 `[200,201]`；按 T-O-413 将无 key 兼容路径恢复为 deterministic digest replay，并为第二调用保留独立 pending hold，随后目标回归通过。无 skip/xfail/degraded。
- **测试发现**：Phase 5 固定 EXIT `92 passed`；`uv run ruff check api intake src tests` EXIT0；对象会话、crash/GC、evidence SQL attack、CAS redline、publication TOCTOU、cleanup hold/convergence 与 NH4/NH5/NH6/NH7 回归均通过。
- **后续 handoff**：Phase 6 只消费已稳定的 session/evidence/manifest/cleanup owner；新增 role/capability/readiness 必须保持 API claim、worker claim、maintenance GC 的 ownership 分离，并将真实 10+3/S16 gate 标记为 owner-pending，不得用 stub 替代。

| 工作项 | 状态 | PR / commit | 实际落点 | 备注 |
|--------|------|-------------|----------|------|
| `P5-01` | `✅ done` | `ff104a9` | `object_upload.py`; `object_upload_ttl.py`; `objects.py`; public routes; `test_nhx1_object_sessions.py` | T-O-413；session replay/isolation/reserve/consume |
| `P5-02` | `✅ done` | `ff104a9` | promotion journal migration; `object_gc.py`; `test_nhx1_object_crash_recovery.py` | T-O-413/417；tombstone-gated physical destroy |
| `P5-03` | `✅ done` | `ff104a9` | migration `029`; `test_nhx1_evidence_plane.py`; retrieval identity guard | T-O-414；legacy verdict/correction and SQL fence |
| `P5-04` | `✅ done` | `ff104a9` | `core.py`; `acquisition_ingest.py`; `clean_preflight.py`; `test_nhx1_stage_secret_redlines.py` | T-O-414/415；CAS-first recursive redaction |
| `P5-05` | `✅ done` | `ff104a9` | `vector_publish_commit.py`; retrieval ports/rank/pack/request; `test_nhx1_publication_manifest.py` | T-O-414/415；manifest membership/read snapshot |
| `P5-06` | `✅ done` | `ff104a9` | `cleanup_jobs.py`; cleanup/GC tests | T-O-417/421；holds, proofs, retention convergence |

| 时点 | 步骤 | 决策 / 产出 |
|------|------|-------------|
| `2026-08-31T04:38:50Z` | Phase 5 EXIT | commit `ff104a9` + fixed 25-file pytest command + `92 passed` + profile `test/sqlite+turso` |
| `2026-08-31T04:38:50Z` | static gate | commit `ff104a9` + `uv run ruff check api intake src tests` + EXIT0 + profile `local` |

### 11.9 Phase 6 — Capability / role / readiness / security

> **执行时间**：`2026-08-31T04:58:17Z`
> **代码改动统计**：`11 文件；2 个新建 runtime registry；27 process capability rows；schema bump 0`

- **实际执行摘要**：
  - `P6-01`：新增 `DeploymentRole`/`DeploymentRoleSpec`，明确 `api`、`workflow_worker`、`maintenance`、`all` 的 loop ownership；lifespan 按 role 启停 supervisor、GC、upload-TTL、index-retirement、retention，`all` 只作为显式组合。
  - `P6-02`：新增 code-owned `ProcessCapabilityManifest`/`ProcessCapabilityRegistry`，从当前 builtin graph 收集 27 个 required process；每项含 handler、role、supply、side-effect、replay law 与 digest；app bootstrap 将其 durable 投影到 `mkb_process_capability_definitions`，unknown workflow/process fail-closed。
  - `P6-03`：readiness 保留 liveness 与 role-specific required set 分离；worker/all 的 supervisor 连续失败达到阈值即 not-ready；API/maintenance 不因未部署 worker/browser/model 而伪装成 claim owner；ready response 返回 role、owned loops、manifest digest、claimable keys。
  - `P6-04`：production profile 拒绝 deterministic NS1 stub/disabled supply，要求 subprocess、runtime supply readiness 与 pinned multimodal；worker claim 在 required supply 缺失时过滤对应 process。既有 S16 浏览器、parser、OCR、egress、backpressure 负向测试作为工程 gate。
- **Phase 偏差（计划 vs 实际）**：
  - `D-P6-01 (compat-substrate)`：为兼容 focused synthetic workflow tests，`WorkflowRegistryService` 仅在 app composition 注入 code-owned registry 时强制 capability validation；生产/实际 app 始终启用闭集，隔离单元可显式注册 synthetic process。
  - `D-P6-02 (owner-gate)`：真实模型、binary 与 S16 具名签收不在本地环境；按 T-O-419 将 `NHX1-T22-E` 标为 `ready-for-owner-gate`，不改写为 PASS，不阻止工程链进入 Phase 7，但保留 Phase 9 join 阻塞。
- **阻塞与处理**：无工程失败；`NHX1-T22-O` 是唯一外部 owner blocker，未使用 skip/xfail/stub 代替。
- **测试发现**：Phase 6 固定 EXIT `61 passed`；`uv run ruff check api intake src tests` EXIT0；role loop、claim filtering、durable capability bootstrap、readiness failure threshold、10+3闭集与 S16 supply/security 回归全部通过。
- **后续 handoff**：Phase 7 消费 role/capability availability，但不得开放 workflow selector/raw payload；operator control 必须使用 command receipt、expected generation、redaction/audit。T22-O 继续作为 owner gate 记录，不能在 Phase 7 中被降级。

| 工作项 | 状态 | PR / commit | 实际落点 | 备注 |
|--------|------|-------------|----------|------|
| `P6-01` | `✅ done` | `d4ea697` | `src/runtime/roles.py`; `api/app.py`; `test_nhx1_roles_readiness.py` | T-O-416；四role loop ownership |
| `P6-02` | `✅ done` | `d4ea697` | `capability_registry.py`; `governance_registry.py`; `workflow_registry.py`; capability gate test | T-O-412/419；27 process manifest/claim filter |
| `P6-03` | `✅ done` | `d4ea697` | `config.py`; `health.py`; `metrics.py`; `api/app.py` | T-O-416/422；role-specific readiness/failure threshold |
| `P6-04` | `🟡 partial` | `d4ea697` | prod profile validator; existing NH6 runtime supply/security tests | T-O-419；工程 gate ready，真实 owner attestation pending |

| 时点 | 步骤 | 决策 / 产出 |
|------|------|-------------|
| `2026-08-31T04:58:17Z` | Phase 6 engineering EXIT | commit `d4ea6978e345d4bef2cd8c65cc989612c38cf2d6` + fixed 16-file pytest command + `61 passed` + profile `test/sqlite+turso` |
| `2026-08-31T04:58:17Z` | T22-E gate | missing-supply/production-stub negative checks PASS；state `ready-for-owner-gate` |
| `2026-08-31T04:58:17Z` | T22-O gate | real model/binary/S16 owner attestation absent；state `pending`，must join Phase 9 final |
