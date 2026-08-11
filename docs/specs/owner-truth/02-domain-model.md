# OT-02 — Domain Model

> **项目**：`myknowledgebase`（MKB）
>
> **文件 ID**：`OT-02`
>
> **文档性质**：`owner-truth / foundational only`
>
> **版本 / 日期**：`OT-02-v1.0 / 2026-08-10`
>
> **文档状态**：`frozen`
>
> **导入状态**：`baseline import complete / QNA admission closed with 0 questions`
>
> **Truth 状态**：`OT02-T001..T023 locked / inherited`；`no-new-decision`
>
> **上游索引**：`docs/specs/index.md`
>
> **上游 Owner Truth**：`OT-01-v1.0`

本文件只冻结 MKB 内部有哪些核心身份、每个身份拥有什么真相、这些身份之间如何保持边界，以及哪些对象才拥有 StateFamily。表、列、DDL、transition 实现、Workflow route、算法、backend 和代码组织不属于本文件。

---

## 1. Inherited Locked Truth

### 1.1 权威来源

| 来源 | 导入范围 | 导入纪律 |
|---|---|---|
| `docs/baseline/domain-truth/D01-task-execution-process-flow.md` `D01-v1.4` | Task/Execution/Process 三层身份、基数、所有权、single/scatter、control/proof 方向、runtime/asset 分账 | 只迁入领域身份与跨域不变量；claim、retry、cleanup 和 route 实现留给 ES-02 |
| `docs/baseline/domain-truth/S04-intake-asset-lifecycle.md` `S04-v1.2` | 五类 Intake 身份、Membership、immutable Revision、latest/serving、长期 lifecycle 与 runtime/asset 分账 | 只迁入身份、所有权和生命周期含义；十表、事务、CAS、outbox、retention 参数留给 Execution Spec |
| `docs/baseline/domain-truth/D02-production-state-and-routing.md` `D02-v1.0` | `T-O-86..92`、六个 StateFamily、state-vs-fact、唯一 owner、control/proof 方向和跨域非法行为 | exact state 集合属于已冻结宪法，直接继承；transition/route 算法不迁入 |
| `docs/baseline/spec-glossary.md` `v1.4` | canonical identity、ledger、pointer、proof 与 derived asset 名称 | frozen 名称沿用；`pending/reserved` 名称不得被本文件擅自转正 |
| `docs/specs/owner-truth/01-product-boundary.md` `OT-01-v1.0` | knowledge 工具边界与内部状态/lifecycle 自持原则 | 只允许 MKB 内部领域身份；不得引入任何上游产品层业务实体 |

### 1.2 覆盖对账

| Baseline Truth cluster | 本文件落点 | 迁移结果 |
|---|---|---|
| `D01-T001..T007` | `OT02-T001..T004` | owner-originated 三层 runtime backbone 被保留 |
| `D01-T008..T015` | `OT02-T005/T015`、`OT02-C001..C003` | 基数、树、血缘和身份独立性被保留 |
| `D01-T016..T021` | `OT02-T002..T006` | 三层责任、状态归约与控制传播被保留 |
| `D01-T025..T032` | `OT02-T007/T022/T023` | proof、retry identity 与 retention 分账被保留 |
| `D01-T034..T043` | `OT02-T007/T015/T017`、`OT02-C008/C009` | runtime/asset/gate/candidate 边界被保留 |
| `S04-T001..T010` | `OT02-T008..T016` | 五类 Intake identity、Membership、single/scatter 和 KnowledgeItem cutoff 被保留 |
| `S04-T015..T023` | `OT02-T018/T022/T023` | lifecycle、latest/serving 和 retrieval fence 含义被保留 |
| `S04-T033..T038/T048` | `OT02-T007/T022`、`OT02-C007/C008` | rebuild、purge、retention 与 gate 非混义边界被保留 |
| `T-O-86..92` | `OT02-T019..T021`、§2.2 | 六 StateFamily、state-vs-fact 和唯一 owner 宪法被完整保留 |

### 1.3 导入截止线

1. `OT02-T001..T023` 是 baseline frozen Truth 与 OT-01-v1.0 的原义归并，不是新推荐。
2. D01/S04 中的 logical table 数、字段、CAS、transaction、outbox、lease、route、retention 时长与 recovery 实现均不进入 Owner Truth。
3. D02 non-normative appendix、下游 handoff 和未冻结 exact kind 不是 Truth；不得从中生成实体、enum 或 owner 问题。
4. OT-01 使用“knowledge 工具”描述产品责任，不会自动创建名为 `KnowledgeItem` 的 v1 领域实体。
5. Baseline 已经冻结的身份、所有权和 StateFamily 不因迁入本文件而重新询问 owner。

---

## 2. Foundational Statements

### 2.1 Canonical identity 与所有权

| Truth ID | 已固化 foundational truth | Baseline provenance |
|---|---|---|
| `OT02-T001` | MKB 内部至少分为四个正交真相面：外部请求聚合、durable workflow runtime、长期 Intake 资产、LS-RAG 派生资产。跨面可以保存 typed reference 和 proof，但不得复用身份或合并所有权。 | `D01-v1.4`、`S04-v1.2` |
| `OT02-T002` | Task 是唯一外部请求起点和 ACK/CRUD/command/aggregate 边界，权威身份为 `(team_uuid, task_uuid)`。Task 不拥有具体 RAG 工序、claim/retry、Intake lifecycle 或派生资产状态。 | `D01-T002/T003/T008/T016` |
| `OT02-T003` | Execution 是 MKB 内部一次 durable workflow run 的身份，拥有目标、绑定的 workflow、tree lineage、总体控制、phase、fan-out/fan-in 与 terminal proof summary；它必须在 Process 清理后仍能解释该次运行。 | `D01-T004/T005/T017` |
| `OT02-T004` | Process 是某个 Execution 内一个具体、RAG-specific 工序实例的身份，拥有该工序的运行状态、typed input/output、claim/lease/fence、retry 与结果事实。Process 不是外部资源、Task type 或长期资产。 | `D01-T006/T007/T013/T014/T018` |
| `OT02-T005` | 一个 Task 可以保留多个历史 root Executions，但同一时刻最多一个 current/active root；single 使用一个 root，scatter 使用一个 root controller 加 `0..N` child Executions。每个 Process 只属于一个 Execution，一个 Execution 可拥有多个 Processes。 | `D01-T005/T009..T014`、`S04-T008` |
| `OT02-T006` | control intent 只允许 `Task → Execution → Process` 向下传播；typed Outcome、immutable asset/proof 与 summary 只允许 `Process/child Execution → Execution → Task` 向上归约。上层不得伪造下层成功，下层不得直接改写上层状态。 | `D01-T019/T020`、`T-O-88` |
| `OT02-T007` | TaskRestart、retry counter、ProcessOutcome、PreflightOutcome、ExecutionGate/Decision、TaskItem projection、phase、waiting reason 和 scheduling record 均不得成为第四层 runtime identity。ExecutionGate 与 IntakeCandidateSet 可以拥有各自已冻结的 StateFamily，但它们仍不是 Task/Execution/Process 的替代层。 | `D01-T027..T030/T038..T043`、`D02-v1.0` |
| `OT02-T008` | IntakeSource、IntakeSnapshot、IntakeItem、IntakeRevision、IntakeArtifact 是五类正交 canonical identity，各自拥有独立 UUID；禁止用 generic `file/document` row 或一个 UUID 同时承担多种职责。 | `S04-T001` |
| `OT02-T009` | IntakeSource 是 team-scoped 外部输入绑定和 ExternalKey namespace。URL、path、provider key、secret ref 或 digest 都只是属性/引用，不是可替代 Source 的全局身份。 | `S04-T002` |
| `OT02-T010` | IntakeSnapshot 是已经 acceptance 的 immutable observation。获取、认证、解析或清洗失败属于 runtime/evidence，不创建 `failed Snapshot`，也不把 Snapshot 改成 mutable current collection。 | `S04-T003` |
| `OT02-T011` | IntakeItem 是 `(team_uuid, intake_source_uuid, normalized_external_key)` 下稳定解析的长期业务项。重新扫描、重放或重新构建不会自动创建新 Item；deleted key 不得静默复用。 | `S04-T004` |
| `OT02-T012` | IntakeRevision 是某个 IntakeItem 的 immutable semantic state，只在 canonical 文档语义发生变化时追加。no-change、retry、rebuild、Workflow/model/embed/index 变化均不创建 IntakeRevision。 | `S04-T005/T010` |
| `OT02-T013` | IntakeArtifact 是某个 IntakeSnapshot 或 IntakeRevision 的 immutable representation，direct owner 必须二选一。Block、Vector、GenerationArtifact 和 Process log 都不是 IntakeArtifact。 | `S04-T006` |
| `OT02-T014` | IntakeSnapshotMembership 是 accepted collection 的 durable SSOT，表达 Snapshot 与 Item/Revision 的集合关系及 decision。single/scatter 共用同一资产模型；scatter parent 是 Source+Snapshot 上下文，不创建伪 parent Item。 | `S04-T007/T008` |
| `OT02-T015` | Execution tree 只描述一次运行的控制血缘；IntakeSource/Snapshot/Membership/Item/Revision graph 描述长期资产与集合 provenance。两者可以显式关联，但不得共用 relation、互相推导身份或级联替代。 | `D01-T012/T039` |
| `OT02-T016` | `KnowledgeItem` 当前只是 reserved identity。若未来确有 promotion/fusion/curation 需求，它必须拥有独立 provenance 和明确 owner；v1 不建 KnowledgeItem 表/API，也不得把 IntakeItem 直接改名为 KnowledgeItem。 | `S04-T009`、glossary v1.4 |
| `OT02-T017` | LS-RAG 的 GenerationArtifact/GenerationInvocation、Block、ConstructionUnit、Vector 与 index generation 属于派生资产或 typed fact 面，不是 Intake 身份、Process row 或新的 runtime 层。GenerationArtifact/Invocation 已确认不是 StateFamily；其他 exact kind/identity 未冻结前不得猜测。 | `D01-T035`、`D02 T-O-88/DR005`、glossary v1.4 |
| `OT02-T018` | `latest IntakeRevision`、`serving IntakeRevision`、`current GenerationArtifact` 和 `active index generation` 是由不同 owner 管理的 SelectionPointer。它们不得共享一个裸 `latest/current`，也不等于 lifecycle、runtime status 或业务成功。 | `S04-T015/T016`、D02 §0.4 |
| `OT02-T019` | MKB v1 有且只有六个 StateFamily，见 §2.2。新增工序、阶段、artifact、projection 或失败原因不得建立第七个 StateFamily。 | `T-O-88` |
| `OT02-T020` | phase、reason、Outcome、readiness、pointer、proof、completeness、decision、retryability 与 cleanup progress 都是 typed fact，不是 status。它们必须有 owner 和校验，但不得通过组合命名制造隐式状态机。 | `T-O-86/T-O-88`、D02 §0.4 |
| `OT02-T021` | 每个 StateFamily 只有一个 transition owner。其他域只能发送 command 或提交 typed fact/proof；API、queue、worker、projection、log、`payload_extra` 和物理文件均无权直接推进不属于自己的状态。 | `T-O-86/T-O-88/T-O-91` |
| `OT02-T022` | runtime lifecycle、Intake lifecycle、serving selection、derived/index generation 与 physical cleanup 是不同事实轴。Task/Execution 失败或取消不自动撤销 proof-valid serving；runtime retention 也不得级联删除长期 Intake/derived truth。 | `D01-T031/T032/T039`、`S04-T017/T021/T033..T038` |
| `OT02-T023` | 单个 IntakeItem 处理成功必须由绑定 exact IntakeRevision 的向量/filter publication proof 支持；Process/Execution/Task terminal、queue ACK、日志、文件存在或单个 vector ACK 都不能替代该 proof。 | `D01-T024/T025`、`S04-T016/T023`、D02 §0.5 |

### 2.2 v1 唯一 StateFamily

| StateFamily | 唯一 owner | Exact states | 不是它的内容 |
|---|---|---|---|
| Task aggregate | Task transition owner | `queued/running/cancelling/succeeded/failed/cancelled` | readiness、TaskItem outcome、action_required、soft-delete visibility |
| Execution control | Workflow Engine / Execution transition owner | `created/ready/running/waiting/succeeded/failed/cancelling/cancelled` | phase、waiting reason、terminal summary |
| Process control | Workflow Engine / Process transition owner | `ready/claimed/running/retry_wait/succeeded/failed/cancelling/cancelled` | ProcessOutcome、retryability、lease/fence、delivery/recovery count |
| IntakeItem lifecycle | Intake transition owner | `active/deactivated/deleted` | latest/serving pointer、Revision、runtime failure、cleanup progress |
| IntakeCandidateSet staging | S05 producer + S04 acceptance owner 的受限共同 contract | `open/sealed/accepted/abandoned` | producing Process status、Snapshot completeness、Membership decision |
| ExecutionGate | Gate transition owner | `open/released/rejected/superseded` | Execution waiting status、ReviewTarget、GateDecision、HTTP/UI action |

只有同时具备 canonical subject、唯一 transition owner、合法边和写入 guard 的集合才是 StateFamily。具体合法 transition、CAS、fence、route 和 persistence 由对应 Execution Spec 实现，但不得改变本表的 owner 或 exact state set。

---

## 3. Hard Scope / Non-goals

| Non-goal ID | 明确禁止进入 OT-02/v1 的模型 | 边界说明 |
|---|---|---|
| `OT02-N001` | User、Chat、Answer、Agent、产品 Workflow 或其他上游业务实体 | 依据 OT-01-v1.0，MKB 只拥有 knowledge 工具内部 domain |
| `OT02-N002` | generic `File`、`Document`、`Job` 或万能 Asset identity | 上游可以输入 document，但内部必须落入已冻结的 runtime/Intake/derived identities |
| `OT02-N003` | v1 `KnowledgeItem`、Knowledge promotion/fusion/curation domain | `KnowledgeItem` 保留但不实例化，不得成为 IntakeItem 别名 |
| `OT02-N004` | Attempt、clean job、rag job、vector job 或其他第四层 runtime identity | 完整运行身份只有 Execution；工序身份只有 Process |
| `OT02-N005` | 第七 StateFamily、global `production_status`、动态状态 registry 或状态治理平台 | 六 StateFamily 是固定上限 |
| `OT02-N006` | `reviewing/retrying/vector_ready/latest_unpublished` 等 stage-specific、原因型或组合 status | 使用已有 status + typed phase/reason/outcome/pointer/proof 表达 |
| `OT02-N007` | 复用 Task/Execution/Process/Intake/Vector UUID，或用路径、URL、digest、provider key 当 canonical identity | 关联必须使用 typed reference，不能牺牲身份正交性 |
| `OT02-N008` | 用同一个 `latest/current/status` 字段跨 owner 表达 Revision、Generation、index、runtime 和 lifecycle | 各 SelectionPointer 与 StateFamily 独立拥有 |
| `OT02-N009` | 将 runtime tree、Intake graph、derived asset graph 或 cleanup ledger 合并成一套多态模型 | 四个真相面只通过 typed refs/proofs 关联 |
| `OT02-N010` | 表数、字段、DDL、transition SQL、route 算法、backend、retention 数值或代码目录 | 全部属于 Execution Spec，不提交 owner QNA |

---

## 4. Open Foundational Decisions

### 4.1 Round 1 问题准入结果

**准入问题数量：`0`。**

OT-02 的全部 foundational 决策轴已经由 baseline locked Truth 唯一确定；未关闭的下游事项均为 executional。为满足题数而生成问题会违反 `docs/specs/index.md` §2.3，也会重新制造 owner 已明确拒绝的无限 QNA。

### 4.2 候选问题剔除审计

| 候选决策轴 | 准入判定 | 证据与处置 |
|---|---|---|
| Task/Execution/Process 是否采用其他分层 | `rejected / already frozen` | `D01-v1.4` 与 `OT02-T002..T007` 已冻结 owner-originated 三层 backbone |
| 五类 Intake identity 是否合并成 Document/File | `rejected / already frozen` | `S04-v1.2` 与 `OT02-T008..T015` 已禁止 generic File/Document identity |
| v1 是否增加 KnowledgeItem | `rejected / prohibited expansion` | `S04-T009`、`OT-01-v1.0`、`OT02-T016/N003` 已冻结当前不建 Knowledge domain |
| 是否增加第七 StateFamily 或 stage-specific status | `rejected / already frozen` | `D02-v1.0 / T-O-88` 与 §2.2 已冻结六个且仅六个 StateFamily |
| GenerationArtifact type、node/edge/anchor/block exact kind | `rejected / executional` | D02 `DR005` 与 S06-v0.7 明确归 S06/ES-06 高内聚设计，不得重新上提 owner |
| ConstructionUnit、VectorRecord、IndexGeneration exact identity/schema | `rejected / executional` | glossary 明确标记 exact schema pending S07-S09；只需继承 exact IntakeRevision lineage 与非 StateFamily 边界 |
| Generation bundle、retry、commit、pointer transaction | `rejected / executional or already derivable` | `T-O-77..85`、D01 runtime identity 与 D02 state-vs-fact 已给出约束；事务与恢复归 ES-02/04/06 |
| clean curation 或跨 generation 编辑身份 | `rejected / OOS or downstream execution` | OT-01 已排除 knowledge editing；S06-v0.7 要求可推导设计自行关闭，不得恢复旧 owner QNA |

### 4.3 Scope Impact Audit — 推荐处置

```text
Scope Impact Audit
- New product responsibility: no
- New externally visible behavior: no
- New V1 capability: no
- New domain identity or StateFamily: no
- New deployment/runtime unit: no
- New owner-truth file: no
- New execution-spec file: no
- Raises a fixed capacity ceiling: no
- Can be solved inside an existing file and boundary: yes
- Classification: no expansion
```

### 4.4 推荐处置

**不向 owner 提交问题；将 OT-02 标记为 `no-new-decision → frozen`。所有剩余 exact identity、kind、schema、transition 与 persistence 决策转入既有 Execution Spec，由工程侧给出默认方案与证据。**

### 4.5 完整 Reasoning

1. **Canonical runtime identity 已关闭**：D01-v1.4 不只提出名称，还冻结了 Task、Execution、Process 的身份、基数、所有权、single/scatter tree 以及 control/proof 方向。重新询问只能重复 owner-originated Truth。
2. **Canonical Intake identity 已关闭**：S04-v1.2 已冻结 Source/Snapshot/Item/Revision/Artifact 与 Membership 的正交关系、immutable Revision、latest/serving 和 lifecycle。File/Document、KnowledgeItem 或跨 Source 自动融合都已明确排除。
3. **状态模型已关闭**：D02-v1.0 是 owner-frozen 共有宪法，六个 StateFamily、唯一 owner 和 state-vs-fact 均已固定。phase、Outcome、pointer、proof 或下游 artifact kind 不能被包装成新的状态问题。
4. **Derived asset 的剩余空白不改变产品责任**：GenerationArtifact 的 immutable history/current selection 已由 `T-O-77..85` 冻结；Block、ConstructionUnit、VectorRecord 与 IndexGeneration 的 exact schema/kind 只决定内部表示和 lineage 落地，不新增产品能力、外部业务或 canonical Intake identity。
5. **Baseline 已显式完成责任移交**：D02-v1.0 与 S06-v0.7 明确要求 S06/S08/S09 自行关闭 exact kind、bundle、embedding/index cutoff，并写明技术设计不得重复上提 owner。把这些事项放进 OT-02 QNA 会直接违反该冻结结论。
6. **当前推荐是最小闭合**：23 条 inherited Truth 已足够约束 ES-01..08；工程仍有设计空间，但不能改变身份、owner、StateFamily 或 cross-domain invariants。冻结 OT-02 不会偷偷冻结表、字段、算法或 backend。
7. **没有诚实的竞争性 foundational 选项**：任何与现有模型真正不同的选项都会要求增加 Knowledge domain、第四层 runtime、合并 Intake identity 或第七状态族；这些不是等价可选方向，而是与已冻结 Truth 冲突的 scope expansion。

### 4.6 Closure

| 项目 | 结论 |
|---|---|
| 通过准入的 foundational 问题 | `0` |
| 新增 Owner Truth | `0` |
| 重复询问 baseline Truth | `0` |
| 上提 executional 问题 | `0` |
| 未解决 foundational 决策 | `0` |
| 后续 QNA 轮次 | `none` |
| OT-02 状态 | `frozen / v1.0` |

除非 owner 主动 reopen 并明确指出要替代的 `OT02-Txxx`，OT-02 不再生成问题。

---

## 5. Owner Decisions

| Decision cluster | 已有 owner 裁决 | 固化落点 | 后续处理 |
|---|---|---|---|
| Runtime backbone | Task/Execution/Process 三层切分由 owner 主动提出；Task 对外、Execution 总控、Process 工序 | `OT02-T002..T007` | 不再讨论 Attempt 或领域 job 分层 |
| Intake identity | Source/Snapshot/Item/Revision/Artifact 五类正交身份，Membership 是集合 SSOT | `OT02-T008..T015` | 不再使用 generic File/Document 模型 |
| Knowledge cutoff | MKB 是 knowledge 工具，但 v1 不创建 KnowledgeItem 或产品层业务实体 | `OT02-T016`、`OT02-N001/N003` | 新 Knowledge domain 必须 owner 主动 reopen |
| Derived asset cutoff | Generation/Block/Vector 与 Intake/runtime 身份分离；exact downstream kind 不由 OT-02 猜测 | `OT02-T017/T018/T023` | 由 OT-03/ES-06/ES-07 在现有边界内落地 |
| State constitution | v1 只有六个 StateFamily；其余生产信息全部按 typed fact 分账 | `OT02-T019..T021`、§2.2 | 不得把实现未知上提为新状态族 |
| Lifecycle separation | runtime、Intake、serving、generation 和 cleanup 分账；MKB 自持内部状态不等于产品层扩张 | `OT02-T022/T023` | Execution Spec 必须分别持有 owner 与 proof |

本节只登记既有裁决，不构成新的 owner approval 请求。

---

## 6. Constraints on Execution Specs

| Constraint ID | 必须由 Execution Spec 继承的约束 | 主要落点 |
|---|---|---|
| `OT02-C001` | Task、Execution、Process 必须保持三个独立身份；Task:Execution 为 `1:N`，Execution:Process 为 `1:N`，任一 Process 只属于一个 Execution。 | `ES-01/02` |
| `OT02-C002` | single 与 scatter 共用同一 runtime/asset 模型；scatter 使用 root+children 和 SnapshotMembership，禁止 singular current Process 或伪 parent Item。 | `ES-01/02/03` |
| `OT02-C003` | 所有身份必须继承 team fence 与 UUID 法则；Execution/Process、五类 Intake 与 derived asset identity 相互独立，不能因存储便利复用。 | 全部 ES |
| `OT02-C004` | 六个 StateFamily 的 exact set 与 owner 不得改变；transition、CAS、lease、fence 和 route 由现有 ES 自行设计，不创建第七族。 | `ES-01/02/03/08` |
| `OT02-C005` | phase/reason/outcome/readiness/pointer/proof/decision/cleanup 必须建模为有 owner 的 typed fact，不得塞入 status、日志、queue 或未晋升的 `payload_extra`。 | 全部 ES |
| `OT02-C006` | control 向下、Outcome/proof 向上；跨域 mutation 必须通过 owner port，projection 与物理存在均不得成为 SSOT。 | `ES-01/02/03/04/08` |
| `OT02-C007` | 五类 Intake identity、Membership、immutable Revision、latest/serving 分离及 lifecycle owner 必须保持；exact schema/transaction 由 ES-03/04 落地。 | `ES-03/04/07` |
| `OT02-C008` | runtime retention、Intake retention、derived generation 和 cleanup proof 分开；Process cleanup 不得破坏 Execution summary、Intake/derived truth 或审计因果。 | `ES-02/03/04/07/08` |
| `OT02-C009` | GenerationArtifact/Invocation 不是 StateFamily；Block/Vector 不是 IntakeArtifact 或 Process。ES-06/07 必须在此边界内冻结 exact derived asset kinds 和 identity。 | `ES-06/07` |
| `OT02-C010` | downstream open kind、route、DDL、driver、backend 与 recovery 参数必须由现有 Execution Spec 给出默认值和证据；不得回流为 OT-02 owner 问题。 | 全部 ES |

---

## 7. Revision History

| 版本 | 日期 | 状态 | 变更 |
|---|---|---|---|
| `OT-02-v0.1` | `2026-08-10` | `pending consolidation` | 创建 Domain Model 基础文件；原义归并 D01-v1.4、S04-v1.2、D02-v1.0 与 glossary v1.4 的冻结身份、所有权、六 StateFamily 和跨域不变量，并继承 OT-01-v1.0 的 knowledge 工具边界；建立 23 条 inherited Truth、10 条 hard non-goal 和 10 条 Execution constraint；未生成 QNA 或新增 domain/state/scope。 |
| `OT-02-v1.0` | `2026-08-10` | `frozen` | 完成 foundational QNA 准入审计：0个问题通过；runtime/Intake/StateFamily轴均已由baseline冻结，derived asset剩余exact kind/schema/transaction均按既有责任移交归Execution Spec。以`no-new-decision`直接冻结，不生成后续轮次。 |
