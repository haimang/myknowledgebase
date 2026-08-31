# new-harvest NH1–NH9 串行执行 todo-list

> 执行基线：`docs/eval/new-harvest/final-execution-plan.md` v1.0
> 真相层：`docs/eval/new-harvest/pre-charter-qna.md` v1.0（`T-O-390..407`）
> 执行顺序：`NH1 → NH2 → NH3 → NH4 → NH5 → NH6 → NH7 → NH8 → NH9 → CROSS-NH`
> 阻塞纪律：任一 todo 只有在其 `blocked-by` 全部完成后才可进入；任一 AP 只有在本 AP 的代码制作、独立审查、最低测试层、执行日志、closure 与 commit 全部完成后，才解锁下一 AP。NH1 `STOP` 时整条 DAG 停止并 reopen frozen truth/final，禁止进入 NH2。

## 状态约定

- `[ ]` blocked/pending
- `[-]` in progress
- `[x]` completed with evidence
- `[!]` STOP / blocked by a failed hard gate

每个 `[代码制作]` todo 均执行：重拉 AP 指定上下文与 reference-anchor → 追溯真相层 → 按工作项实现 → 运行该 Phase 的短途测试。每个 `[代码审查，测试与文档回填]` todo 均执行：独立 diff/code review → AP 全层测试与修复循环 → 生成 evidence → 按 `.adocs/templates/code-execution-log.md` append AP §11 → 按 `.adocs/templates/closure.md` 输出 `docs/closure/new-harvest/` closure → 分阶段 commit。

## NH1 — foundation contracts and proof baseline

- [x] `NH1-CODE-P1` [代码制作] Phase 1 可信 harness（`NH1-02/03`；`NH1-T02/T03`）。`blocked-by: none`
- [x] `NH1-CODE-P2` [代码制作] Phase 2 执行分母与矩阵（`NH1-01/07/08`；`NH1-T01/T07`）。`blocked-by: NH1-CODE-P1`
- [x] `NH1-CODE-P3` [代码制作] Phase 3 chosen-shape spike（`NH1-04/05/06`；`NH1-T04/T05/T06`）。`blocked-by: NH1-CODE-P2`
- [x] `NH1-CODE-P4` [代码制作] Phase 4 foundation pack 与 NH2–NH6 versioned interfaces（`NH1-09`）。`blocked-by: NH1-CODE-P3`
- [x] `NH1-CLOSE` [代码审查，测试与文档回填] `NH1-T01..T07`、GO/STOP、日志、evidence、closure、commit。`blocked-by: NH1-CODE-P4`

## NH2 — workflow kind family and merge

- [x] `NH2-CODE-P1` [代码制作] Phase 1 CONTROL 代数（`NH2-01`；`NH2-T02`）。`blocked-by: NH1-CLOSE=GO`
- [x] `NH2-CODE-P2` [代码制作] Phase 2 representation guard（`NH2-02`；`NH2-T03`）。`blocked-by: NH2-CODE-P1`
- [x] `NH2-CODE-P3` [代码制作] Phase 3 kind family 定义与多边（`NH2-03/04`；`NH2-T04/T05/T07`）。`blocked-by: NH2-CODE-P2`
- [x] `NH2-CODE-P4` [代码制作] Phase 4 kind-only resolver + 停暗 dispatch（`NH2-05/06`；`NH2-T01/T05/T07`）。`blocked-by: NH2-CODE-P3`
- [x] `NH2-CODE-P5` [代码制作] Phase 5 compat + 红线扫描（`NH2-07/08`；`NH2-T06/T07`）。`blocked-by: NH2-CODE-P4`
- [x] `NH2-CLOSE` [代码审查，测试与文档回填] `NH2-T01..T07`、日志、evidence、closure、commit。`blocked-by: NH2-CODE-P5`

## NH3 — representation history and S05 binding

- [x] `NH3-CODE-P1` [代码制作] Phase 1 durable rows（`NH3-01/02`；`NH3-T01`）。`blocked-by: NH2-CLOSE`
- [x] `NH3-CODE-P2` [代码制作] Phase 2 诚实表示（`NH3-03/04/05`；`NH3-T02/T03/T04`）。`blocked-by: NH3-CODE-P1`
- [x] `NH3-CODE-P3` [代码制作] Phase 3 声明式再获取（`NH3-06`；`NH3-T05`）。`blocked-by: NH3-CODE-P2`
- [x] `NH3-CODE-P4` [代码制作] Phase 4 policy/actual S05 分账与 seal UoW（`NH3-07/08/09`；`NH3-T06/T07`）。`blocked-by: NH3-CODE-P3`
- [x] `NH3-CODE-P5` [代码制作] Phase 5 replay 法律（`NH3-10`；`NH3-T08`）。`blocked-by: NH3-CODE-P4`
- [x] `NH3-CLOSE` [代码审查，测试与文档回填] `NH3-T01..T08`、日志、evidence、closure、commit。`blocked-by: NH3-CODE-P5`

## NH4 — public upload and object lifecycle

- [x] `NH4-CODE-P1` [代码制作] Phase 1 bounded write（`NH4-01`；`NH4-T01/T07`）。`blocked-by: NH3-CLOSE`（DAG 仅要求 NH1 GO；本清单按用户要求串行线性化）
- [x] `NH4-CODE-P2` [代码制作] Phase 2 catalog + upload_pending UoW（`NH4-02`；`NH4-T01`）。`blocked-by: NH4-CODE-P1`
- [x] `NH4-CODE-P3` [代码制作] Phase 3 authenticated public API fence（`NH4-03/07`；`NH4-T01/T03`）。`blocked-by: NH4-CODE-P2`
- [x] `NH4-CODE-P4` [代码制作] Phase 4 idempotency + local_object ingest handoff（`NH4-04/05`；`NH4-T02/T04`）。`blocked-by: NH4-CODE-P3`
- [x] `NH4-CODE-P5` [代码制作] Phase 5 GC + security negatives（`NH4-06/08`；`NH4-T05/T06/T07`）。`blocked-by: NH4-CODE-P4`
- [x] `NH4-CLOSE` [代码审查，测试与文档回填] `NH4-T01..T07`、日志、evidence、closure、commit。`blocked-by: NH4-CODE-P5`

## NH5 — semantic ledger and retrieval facets

- [x] `NH5-CODE-P1` [代码制作] Phase 1 strict semantic input（`NH5-01`；`NH5-T01/T02`）。`blocked-by: NH4-CLOSE`（DAG 仅要求 NH1 GO；本清单按用户要求串行线性化）
- [x] `NH5-CODE-P2` [代码制作] Phase 2 acceptance gate + atomicity（`NH5-02/03`；`NH5-T02/T03`）。`blocked-by: NH5-CODE-P1`
- [x] `NH5-CODE-P3` [代码制作] Phase 3 S06 overlay（`NH5-04`；`NH5-T04`）。`blocked-by: NH5-CODE-P2`
- [x] `NH5-CODE-P4` [代码制作] Phase 4 channel naming + facet projection/query（`NH5-05/06/07`；`NH5-T05/T06/T07`）。`blocked-by: NH5-CODE-P3`
- [x] `NH5-CODE-P5` [代码制作] Phase 5 metadata semantic cutover（`NH5-08`；`NH5-T08-A`；`T08-B` handoff 红灯保留给 NH8）。`blocked-by: NH5-CODE-P4`
- [x] `NH5-CLOSE` [代码审查，测试与文档回填] `NH5-T01..T08` 的本 AP 硬闸、日志、evidence、closure、commit。`blocked-by: NH5-CODE-P5`

## NH6 — local runtime supply and security

- [x] `NH6-CODE-P1` [代码制作] Phase 1 supply identities（`NH6-01`；`NH6-T09/T10`）。`blocked-by: NH5-CLOSE`（同时满足 NH1 GO + NH3 closure）
- [x] `NH6-CODE-P2` [代码制作] Phase 2 isolated PDF parser（`NH6-02`；`NH6-T01/T02`）。`blocked-by: NH6-CODE-P1`
- [x] `NH6-CODE-P3` [代码制作] Phase 3 browser render/print 双能力（`NH6-03/04`；`NH6-T03/T04/T05`）。`blocked-by: NH6-CODE-P2`
- [x] `NH6-CODE-P4` [代码制作] Phase 4 S11 multimodal + OCR/Vision bindings（`NH6-05/06`；`NH6-T06/T07`）。`blocked-by: NH6-CODE-P3`
- [x] `NH6-CODE-P5` [代码制作] Phase 5 gates/readiness/SBOM/default wiring（`NH6-07..10`；`NH6-T08/T09/T10`）。`blocked-by: NH6-CODE-P4`
- [x] `NH6-CLOSE` [代码审查，测试与文档回填] `NH6-T01..T10`、S16 签收栏、日志、evidence、closure、commit。`blocked-by: NH6-CODE-P5`

## NH7 — clean capability activation

- [x] `NH7-CODE-P1` [代码制作] Phase 1 activation manifest + admitted-clean contract（`NH7-01/02`；`NH7-T01/T10`）。`blocked-by: NH6-CLOSE`（NH2/NH3/NH4/NH5/NH6 join 已满足）
- [x] `NH7-CODE-P2` [代码制作] Phase 2 promptA alignment（`NH7-03`；`NH7-T02`）。`blocked-by: NH7-CODE-P1`
- [x] `NH7-CODE-P3` [代码制作] Phase 3 deterministic/PDF live-to-retrieval（`NH7-04/05`；`NH7-T03/T04`）。`blocked-by: NH7-CODE-P2`
- [x] `NH7-CODE-P4` [代码制作] Phase 4 browser/print live-to-retrieval（`NH7-06/07`；`NH7-T05/T06`）。`blocked-by: NH7-CODE-P3`
- [x] `NH7-CODE-P5` [代码制作] Phase 5 multimodal + registered API + exhausted_zero（`NH7-08/09`；`NH7-T07/T08/T09/T10`）。`blocked-by: NH7-CODE-P4`
- [x] `NH7-CODE-P6` [代码制作] Phase 6 first-publication product closure（`NH7-10`；cross-query `NH7-T03..T10`）。`blocked-by: NH7-CODE-P5`
- [x] `NH7-CLOSE` [代码审查，测试与文档回填] `NH7-T01..T10` L1–L4、10+3 manifest、日志、evidence、closure、commit。`blocked-by: NH7-CODE-P6`

## NH8 — intake lifecycle and compatibility

- [x] `NH8-CODE-P1` [代码制作] Phase 1 seven-intent applicability/error contract（`NH8-01`；`NH8-T01`）。`blocked-by: NH7-CLOSE`
- [x] `NH8-CODE-P2` [代码制作] Phase 2 rebuild/metadata exact-clean bypass（`NH8-02/03`；`NH8-T02/T03`；关闭 NH5-T08-B）。`blocked-by: NH8-CODE-P1`
- [x] `NH8-CODE-P3` [代码制作] Phase 3 lifecycle query law（`NH8-04`；`NH8-T04/T05/T06`）。`blocked-by: NH8-CODE-P2`
- [x] `NH8-CODE-P4` [代码制作] Phase 4 index.rebuild（`NH8-05`；`NH8-T07`）。`blocked-by: NH8-CODE-P3`
- [x] `NH8-CODE-P5` [代码制作] Phase 5 API Item shared lifecycle（`NH8-06`；`NH8-T08`）。`blocked-by: NH8-CODE-P4`
- [x] `NH8-CODE-P6` [代码制作] Phase 6 old-pin compat + lineage（`NH8-07/08`；`NH8-T09/T10`）。`blocked-by: NH8-CODE-P5`
- [x] `NH8-CLOSE` [代码审查，测试与文档回填] `NH8-T01..T10` L1–L4、M-NH-09/retirement review、日志、evidence、closure、commit。`blocked-by: NH8-CODE-P6`

## NH9 — closed-set assurance

- [x] `NH9-CODE-P1` [代码制作] Phase 1 closed-set generator（`NH9-01`；`NH9-T01`）。`blocked-by: NH8-CLOSE`
- [x] `NH9-CODE-P2` [代码制作] Phase 2 replay + fail-loud（`NH9-02/03`；`NH9-T02/T03`）。`blocked-by: NH9-CODE-P1`
- [x] `NH9-CODE-P3` [代码制作] Phase 3 crash windows（`NH9-04`；`NH9-T04/T05`）。`blocked-by: NH9-CODE-P2`
- [x] `NH9-CODE-P4` [代码制作] Phase 4 object race + scatter（`NH9-05/06`；`NH9-T05/T06/T07`）。`blocked-by: NH9-CODE-P3`
- [x] `NH9-CODE-P5` [代码制作] Phase 5 compat + retrieval-facet mega（`NH9-07/08`；`NH9-T03/T08/T09`）。`blocked-by: NH9-CODE-P4`
- [x] `NH9-CODE-P6` [代码制作] Phase 6 security/evidence/experiment isolation（`NH9-09/10/11`；`NH9-T10/T11`；experiment 不入 DoD）。`blocked-by: NH9-CODE-P5`
- [x] `NH9-CLOSE` [代码审查，测试与文档回填] `NH9-T01..T11`、`FG-NH-01..17`、capstone A–J、日志、evidence、closure、commit。`blocked-by: NH9-CODE-P6`

## Cross-NH campaign closure

- [x] `CROSS-NH-REVIEW` [跨阶段代码审查] 检查 NH1–NH9 contract/migration/runtime/public/retrieval/lifecycle 的跨阶段耦合、owner `T-O-390..407` 与 foundational truth 零漂移。`blocked-by: NH9-CLOSE`
- [x] `CROSS-NH-TEST` [跨阶段测试与修复] 执行完整测试集、固定 capstone 文件、race/crash/security/compat/mega；持续测试↔修复直到无 in-scope 失败。`blocked-by: CROSS-NH-REVIEW`
- [x] `CROSS-NH-CLOSE` [最终文档回填与提交] 输出 consolidated closure、核对九份 AP 日志/closure/evidence/commit 四元组、最终提交并报告。`blocked-by: CROSS-NH-TEST`

## NHX1 — coherent debt retirement and governance

> 执行基线：`docs/plan/new-harvest/AP-NHX1-coherent-debt-retirement-and-governance.md`
> 真相层：`docs/eval/new-harvest/pre-NHX1-qna.md`（`T-O-408..422`，frozen）
> 严格 DAG：`NHX1-P1 → NHX1-P2 → NHX1-P3 → NHX1-P4 → NHX1-P5 → NHX1-P6 → NHX1-P7 → NHX1-P8 → NHX1-P9 → NHX1-FINAL-CLOSE`
> 阻塞纪律：任一 Phase 仅在前序 Phase 的工程 EXIT、证据四元组、执行日志与分簇 commit 全部完成后进入。`NHX1-T22-E` 可在 Phase 6 达到 `ready-for-owner-gate` 后把工程链交给 Phase 7；`NHX1-T22-O` 未具名签收时 Phase 9 join 与 final closure 保持 blocked，不得以 skip、stub 或 deferred 代替。

- [x] `NHX1-P1` [代码制作/测试/日志/提交] Truth denominator、pre-fix/rev1 fixtures、honest harness、anti-fake-green executor（`P1-01..04`；`NHX1-T01/T02/T03/T30`）。`blocked-by: none` · evidence `000e1be / 17 passed / 2026-08-31T01:49:46Z`
- [x] `NHX1-P2` [代码制作/测试/日志/提交] Canonical schema、ports、registries，025+ expand-only（`P2-01..05`）。`blocked-by: NHX1-P1=PASS` · evidence `c9874ca / 65 passed / 2026-08-31T02:07:52Z`
- [x] `NHX1-P3` [代码制作/测试/日志/提交] Intake identity、Observation/ItemEpoch、lifecycle（`P3-01..05`；`NHX1-T04..T08`）。`blocked-by: NHX1-P2=PASS` · evidence `b6769e1 / 38 passed / 2026-08-31T02:56:34Z`
- [x] `NHX1-P4` [代码制作/测试/日志/提交] Workflow rev2/rev1 compat、ProcessingBinding、Outcome/replay/outbox owner（`P4-01..06`；`NHX1-T09..T14`）。`blocked-by: NHX1-P3=PASS` · evidence `386f829 / 40 passed / 2026-08-31T03:34:15Z`
- [x] `NHX1-P5` [代码制作/测试/日志/提交] Object session/journal、evidence、CAS-first、publication snapshot、physical cleanup（`P5-01..06`；`NHX1-T15..T20`）。`blocked-by: NHX1-P4=PASS` · evidence `ff104a9 / 92 passed / 2026-08-31T04:38:50Z`
- [x] `NHX1-P6` [代码制作/测试/日志/提交] Deployment roles、capability manifest、readiness、production/security engineering gate（`P6-01..04`；`NHX1-T21/T22-E/T25`）。`blocked-by: NHX1-P5=PASS` · evidence `d4ea697 / 61 passed / T22-E ready-for-owner-gate / 2026-08-31T04:58:17Z`
- [x] `NHX1-P7` [代码制作/测试/日志/提交] Public discovery/views、operator control、signals/errors（`P7-01..04`；`NHX1-T23..T25`）。`blocked-by: NHX1-P6 engineering EXIT PASS; NHX1-T22-O may remain pending` · evidence `f90289d / 44 passed / 2026-08-31T05:40:40Z`
- [-] `NHX1-P8` [代码制作/测试/日志/提交] Shadow/cutover、compat drain、retirement/forward rollback（`P8-01..03`；`NHX1-T26` join compat tests）。`blocked-by: NHX1-P7=PASS`
- [ ] `NHX1-P9` [assurance/测试/review/日志/提交] Compiler-derived L1–L4、deterministic races、real subprocess crash、persisted upgrade、full repo/evidence/third review（`P9-01..04`；`NHX1-T27..T30`）。`blocked-by: NHX1-P8=PASS + NHX1-T22-O=PASS`
- [ ] `NHX1-FINAL-CLOSE` [最终本地审查/静态检查/closure/提交] 使用 `.adocs/templates/closure.md` 生成并补全 NHX1 closure，回写最终收口分析与证据四元组。`blocked-by: NHX1-P9=PASS`
