# new-harvest NHX1 — Pre-charter Q&A · singular（单轮一次性业主决策册）

> **范围（scope）**：一次性关闭 `NHX1` 开工前全部 15 个 owner/architect 决策；`NHX1` 以一个阶段容纳二轮审查后的完整还债工作，并在阶段内部按冻结 DAG 串行执行。
> **qna 位点**：`pre-charter`
> **角色配置（自填）**：提问 `GPT` · second-opinion `none` · 裁决 `owner`
> **second-opinion 模式**：`retired`（按业主要求不设置、不渲染 second-opinion 槽位）
> **Q 编号**：续接同一 new-harvest campaign 的 `Q1–Q27`；本文使用 `Q28–Q42`，稳定 append、不回收。
> **Truth-ID 冻结**：续接 `T-O-376..407`；Q28–Q42 的业主回答已依次冻结为 `T-O-408..422`，append-only、不回收。
> **上游输入**：`docs/eval/new-harvest/after-2nd-pass-review-coherent-fixes-design.md` · `docs/code-review/new-harvest/NH1-NH9-2nd-pass-review-VF-ledger.md` · `docs/closure/new-start/deferred-items-ledger.md` · HEAD `ba099ee305577cca2281a669afbca364111f200b`
> **下游消费者**：NHX1 design 修订稿 · NHX1 单一 action-plan / 串行 DAG · todo-list · migration/compat plan · closure/evidence pack
> **文档状态**：`frozen`（15/15 owner decisions closed；Truth-Gate 已注入）
> **文档版本**：`v1.0 / 2026-08-31`
> **Owner 冻结授权**：业主整包同意 Q28–Q42 的全部推荐方案，即逐题选择 **A** 并接受每题全部确认句；无补充改写。

---

## 0. 使用方式与问题分母

本文把设计中的 `CF-D02..CF-D16` 一一映射为 15 个问题。`CF-D01` 已由业主在本轮冻结：不做 hotfix，以一个 `NHX1` 阶段容纳全部工作，并在阶段内串行执行。因此不重复提问。

| Q | 原决策 | 主题 | Truth-ID | 影响的 NHX1 串行节点 |
|---|--------|------|-----------------|------------------------|
| Q28 | CF-D02 | Source / Observation 分账 | T-O-408 | N1 schema → N2 intake |
| Q29 | CF-D03 | ItemEpoch / CAS owner | T-O-409 | N1 schema → N2 intake |
| Q30 | CF-D04 | full retry 是否重新 acquire | T-O-410 | N2 intake → N3 workflow |
| Q31 | CF-D05 | workflow rev1 → rev2 / old pin | T-O-411 | N1 schema → N3 workflow → N7 retirement |
| Q32 | CF-D06 | registered API processing taxonomy | T-O-412 | N1 schema → N3 workflow → N6 catalog |
| Q33 | CF-D07 | upload handle 与 session owner | T-O-413 | N1 schema → N4 object |
| Q34 | CF-D08 | legacy evidence 修复法 | T-O-414 | N1 schema → N4 evidence → N7 retirement |
| Q35 | CF-D09 | public read / operator debug-control 分权 | T-O-415 | N6 read-control-observability |
| Q36 | CF-D10 | leaf-worker deployment role | T-O-416 | N5 capability-role-readiness |
| Q37 | CF-D11 | logical delete 后物理收敛 | T-O-417 | N4 object → N7 convergence |
| Q38 | CF-D12 | 错误码结束双轨 | T-O-418 | N6 API/SDK/ops |
| Q39 | CF-D13 | 真 supply / S16 与 NHX1 closure | T-O-419 | N5 runtime → N8 assurance |
| Q40 | CF-D14 | existing-object 新 cleaner upgrade | T-O-420 | scope / N3 / N8 |
| Q41 | CF-D15 | deleted Item external key 复用法 | T-O-421 | N2 intake → N7 retention |
| Q42 | CF-D16 | outbox dead 与 owner 终结法 | T-O-422 | N3 workflow → N6 control |

证据纪律：本文引用 HEAD 的代码、DDL、冻结 QNA/plan 与当前 OpenAPI 行为。review finding 只用于确定问题分母；推荐结论必须能由下列 file:line 直接复核。业主已整包接受推荐 A，逐题 `业主回答` 与 §7 Truth-Gate 是下游唯一 owner 口径。

---

## 1. Intake 身份、并发与 replay

### Q28 — SourceIdentity 与一次 Observation 应如何分账（来源：`CF-D02`、VF1/VF3/VF4/VF5/VF8）

- **影响范围**：四个 public source descriptor；Task admission；Source/Snapshot/Item/Revision；registered API scatter；失败重试；idempotency 与 migration。
- **为什么必须确认**：当前 `external_key` 同时承担长期 Source/Item identity 和一次 observation key。只补 fingerprint 或 unique error，无法同时回答“同来源新内容”“同观察精确重放”“失败观察恢复”“并发双建”四种产品语义。
- **当前建议 / 倾向（GPT）**：选 **A**。

#### [对问题的详细解读]

长期 Source 应回答“这是哪个来源/对象”；Observation 应回答“调用方这一次观察是什么”。一个 URL、local object 业务键或 inline external key 可以被观察多次，每次观察可能产生新 Snapshot；同一个 observation key 则只能有一个被接受的事实结果。

当前 public schema 对四种 source 都只有 `external_key`，没有 observation identity（`src/contracts/api/models.py:153-188`）。DDL 其实已经给 Snapshot 定义了 `(team, source, observation_key)` 唯一键（`src/persistence/migrations/001_initial.sql:915-940`），但 single intake 把 `normalized_external_key` 直接写进该键，并在命中后复用旧 Snapshot（`src/runtime/intake/acceptance_snapshot.py:139-170`）。registered API 又在 Task 业务 UoW 之前单独查询已有 Snapshot（`src/runtime/task/task_create.py:97-111,452-480`），所以 admission 与 reservation 没有同一线性化点。

本题必须冻结三件事：v2 observation key 是否显式出现在 public contract；失败 observation 能否复用同 key；v1 没有该字段时如何兼容。

#### [可选的方案清单]

| 选项 | 方案 | 产品与工程含义 |
|------|------|----------------|
| **A（推荐）** | **显式 `ObservationReservation` 分账** | v2 四种 source 均提交 `observation_key`；Task admission 与 reservation 同 UoW。状态为 `reserved/acquired/accepted/failed/abandoned`，attempt append-only。accepted exact replay返回原坐标，异 fingerprint冲突；failed 可用 typed retry CAS 开新 attempt。v1 single 以 `task_uuid` 派生兼容 key，v1 registered API 暂沿用旧 external-key 语义并标 deprecated。 |
| **B** | **继续用 external key，仅增强 fingerprint/锁** | 相同 source key 仍只能有一个 Snapshot；新内容只能冲突或覆盖。失败 recovery、重复观察和 Source 生命周期继续耦合。 |
| **C** | **完全用 Task UUID 作为 observation，不开放业务 observation key** | 可以避免并发同 key，但调用方跨 Task/网络重放无法表达同一次业务观察；registered API watermark/collection identity消失。 |

#### [推荐方案的详细说明]

选择 A 后，SourceIdentity 仍为 `(team, source_kind, normalized_external_key)`；ObservationIdentity 为 `(team, intake_source_uuid, observation_key)`。admission 同一事务创建或采用 Source、占用 Observation、创建 Task/root Execution，并写 command receipt。并发请求只有一个 winner。

Observation 接受后永久绑定 Snapshot；失败不删除历史，而是以 `retry_failed_observation + expected_attempt_generation` 开新 attempt。不同 observation 可观察到相同内容：允许新 Snapshot引用同一 Revision，并写显式 `no_change` ChangeSet；不能通过复用旧 Snapshot假装本次观察不存在。

scatter 在 stage envelope/child manifest 冻结前取得 durable Source/Observation UUID，避免当前“先写随机 UUID、callback 再采用旧 UUID”的时序。v1 兼容只解决旧 wire，不允许新 writer继续把 external key当 observation。

#### [支持推荐方案的证据 / Reasoning，或反对其他方案的真相]

- public 四类 source 只有 `external_key`（`src/contracts/api/models.py:153-188`）；没有独立 observation token，B/C 都需要隐式猜测。
- Source 已由 `(team, source_kind, normalized_external_key)` 部分唯一索引定义长期 identity（`src/persistence/migrations/016_ns6_source_external_key.sql:1-20`），Snapshot 另有 observation unique（`src/persistence/migrations/001_initial.sql:915-940`）；数据库形状本身支持分账，当前 writer 没有遵守。
- single acquire 在独立事务先查 identity并把旧 Snapshot UUID带入内存（`src/runtime/intake/acquisition_ingest.py:129-137,229-264`），acceptance随后无 fingerprint 比较复用（`src/runtime/intake/acceptance_snapshot.py:139-145`）。B只加一处判断会继续保留两事务窗口。
- registered API precheck位于 Task INSERT 事务之前（`src/runtime/task/task_create.py:68-111,452-480`），证明“先查后插”不是 reservation。
- Item 本身已有 `(team, source, normalized_external_key)` 唯一键（`src/persistence/migrations/001_initial.sql:944-964`）；继续把相同键再充当 Observation没有新增信息，只制造耦合。
- 反对 C：Task UUID只描述传输命令，不描述供应商 collection/watermark 等业务 observation；相同业务观察换 Task UUID会被当成新观察。

#### 问题（请业主裁决）

**Q28：Source / Observation 分账选择 A / B / C？若选 A，是否同时确认：v2 四通道显式提交 observation key；reservation 与 Task/root 同 UoW；accepted 同 key仅 exact replay，异 fingerprint冲突；failed 同 key只能通过 typed retry新建 attempt；v1 single用task UUID派生、v1 registered API暂保旧兼容并弃用？**

- **业主回答**：🔒 **FROZEN：选择 A。** SourceIdentity 与 ObservationReservation 分账；v2 四通道显式提交 observation key，reservation 与 Task/root 同 UoW；accepted 同 key仅 exact replay、异 fingerprint冲突；failed 只经 typed retry新增 attempt；v1 single以Task UUID派生兼容key，v1 registered API暂保旧external-key兼容并弃用。→ `T-O-408`
- **裁决状态**：`accepted / frozen`

---

### Q29 — Item 的跨 Task CAS 应使用一个 ItemEpoch 还是多个 counter（来源：`CF-D03`、VF2/VF10）

- **影响范围**：accept Revision、latest/serving pointer、deactivate/reactivate/delete、metadata/rebuild、late callback、public revision/ETag 与 migration。
- **为什么必须确认**：当前 lifecycle/publish 已有 row_revision CAS，但 acceptance blind-update latest，publication caller又没有传已支持的 expected revision。若不先冻结唯一 epoch owner，各 action-plan会各加一枚局部 fence。
- **当前建议 / 倾向（GPT）**：选 **A**。

#### [对问题的详细解读]

Item 有三组可变真相：`latest_revision_uuid`、`serving_revision_uuid`、`lifecycle_state`。它们不是互不相关的字段：delete 必须阻止迟到 accept/publish，new Revision必须阻止旧 publish，reactivate也必须要求新的 serving proof。因此需要一个能让所有 mutation彼此看见的 generation。

现表已有 `row_revision`（`src/persistence/migrations/001_initial.sql:944-961`）。lifecycle正确地把 expected row revision和 lifecycle state放进同一 UPDATE（`src/services/intake_lifecycle/lifecycle_apply.py:86-123`）；publication也支持 expected revision和 active/latest fence（`src/services/intake_lifecycle/lifecycle_publish.py:69-132`）。但 acceptance更新 latest没有 expected revision（`src/runtime/intake/acceptance_snapshot.py:191-195`），vector publication构造 command时也没传 `expected_item_revision`（`src/runtime/intake/vector_publish_commit.py:168-190`）。问题是 owner law缺失，不是数据库没有 counter。

#### [可选的方案清单]

| 选项 | 方案 | 产品与工程含义 |
|------|------|----------------|
| **A（推荐）** | **现 `row_revision` 冻结为单一逻辑 `ItemEpoch`** | latest、serving、lifecycle及所有canonical mutation均CAS并递增；Execution/input冻结expected epoch。冲突更保守但语义唯一。 |
| **B** | **拆成 lifecycle/head/serving 三个 epoch** | 允许更多并发，但每个跨字段操作必须冻结多个counter并定义偏序；迁移、API ETag和重试复杂度显著增加。 |
| **C** | **不冻结统一epoch，只给当前缺口逐SQL加rowcount** | 短期改动小；callback之间没有共享owner语义，下一轮仍会出现漏传/漏查。 |

#### [推荐方案的详细说明]

选择 A 后，不额外创建第二个 lifecycle counter。现有 `row_revision` 的 contract提升为 ItemEpoch：任何改变 latest、serving、lifecycle或其权威关系的 transaction都必须以 expected epoch CAS并递增一次。Task/Execution在 admission冻结 epoch；acceptance成功后的新 epoch通过 durable result传给publication，不能继续使用创建时的旧值。

并发不同内容时，至多一个 acceptance成为 latest；败者的 Observation/Snapshot可以保留为“已观察但未采纳”，但不能 last-writer-wins。delete/reactivate后，所有旧 Execution携带的 epoch失效，迟到 callback只能得到 typed conflict。

#### [支持推荐方案的证据 / Reasoning，或反对其他方案的真相]

- DDL已经存在单一 `row_revision`并把非active serving指针清空写成同表 invariant（`src/persistence/migrations/001_initial.sql:944-961`），A复用现有权威，不增加双计数漂移。
- lifecycle的 UPDATE 同时比较 `row_revision` 与 `lifecycle_state`（`src/services/intake_lifecycle/lifecycle_apply.py:107-123`），证明单 epoch模式已经是正向 precedent。
- publication的 UPDATE 同时比较 active、row revision、latest revision（`src/services/intake_lifecycle/lifecycle_publish.py:118-132`），说明 serving也属于同一 Item aggregate。
- acceptance blind UPDATE（`src/runtime/intake/acceptance_snapshot.py:191-195`）正是 VF2 last-writer-wins 的根因；C只能依赖每位实现者记得补条件。
- `IntakePublicationCommand` 已有 `expected_item_revision`字段（`src/services/intake_lifecycle/models.py:52-77`），但生产 caller未传（`src/runtime/intake/vector_publish_commit.py:168-190`）；优先闭合一个现成 contract 比再造B稳。
- 反对 B：head变化会影响 serving合法性，lifecycle变化又影响二者；拆counter后仍需要一个组合epoch或多列CAS，并未真正解耦。

#### 问题（请业主裁决）

**Q29：Item 并发 owner 选择 A / B / C？若选 A，是否确认现 `row_revision` 即逻辑 ItemEpoch，latest/serving/lifecycle每次canonical mutation都CAS并递增，所有Task/Execution callback必须携带expected epoch，冲突败者不得静默覆盖？**

- **业主回答**：🔒 **FROZEN：选择 A。** 现 `row_revision` 冻结为单一逻辑 ItemEpoch；latest、serving、lifecycle及其它canonical mutation均以expected epoch CAS并递增，所有Task/Execution callback必须携带该fence，冲突败者不得静默覆盖。→ `T-O-409`
- **裁决状态**：`accepted / frozen`

---

### Q30 — full Task retry 是 exact replay 还是一次新的外部观察（来源：`CF-D04`、VF6/VF7、`T-O-401`）

- **影响范围**：Task retry API；HTTP/API/local/inline acquire；Observation attempt；actual S05；metadata disposition；restart lineage与错误契约。
- **为什么必须确认**：当前 retry复制 old workflow/actual/manifest，却清空 Task snapshot后从 start重跑；HTTP handler会再次 fetch URL。它同时声称“exact actual”和“重新观察外部世界”，两种承诺不能共存。
- **当前建议 / 倾向（GPT）**：选 **A**。

#### [对问题的详细解读]

retry 与 refresh 是两种产品动作。retry承诺重做同一失败工作，因此必须复用同一 external input；refresh承诺重新看外部世界，因此可能得到新bytes、新representation facts和新actual binding。把两者放在 `full_task` 一个按钮里，会让调用方无法知道结果属于旧观察还是新观察。

当前 Task retry确实复制 prior `workflow_revision_uuid/compiled_digest` 与 actual seal字段（`src/runtime/task/task_commands.py:293-318`），但随后把 Task的 snapshot/change set清空并 enqueue新root（`src/runtime/task/task_commands.py:327-350`）。新root从 start进入 HTTP acquire，handler直接调用 fetcher（`src/runtime/intake/acquisition_ingest.py:558-598`）。`T-O-401` 已冻结 full_task exact；本题要决定如何让实现与 Truth一致，以及“早于durable acquire失败”怎么办。

#### [可选的方案清单]

| 选项 | 方案 | 产品与工程含义 |
|------|------|----------------|
| **A（推荐）** | **full retry只从 frozen Observation/artifact resume** | 已有durable acquire/fact时零外部调用；复制typed Execution context与exact graph/actual/formula。没有可验证frozen input时拒绝full retry，caller创建新observation。 |
| **B** | **把full retry定义为fresh reacquire** | 清空actual并使用当前active workflow，相当于refresh/new observation；必须承认它不再是同一承诺。 |
| **C** | **维持当前hybrid：复制actual但重新fetch** | 改动最小，但旧actual可绑定新bytes；HTTP/API变化时产生不可解释结果。 |

#### [推荐方案的详细说明]

选择 A 后，Process retry在 acquire **尚未成功提交 fact/artifact** 时可以在同 ObservationAttempt 内重试transport，first durable acquisition wins；一旦 acquire已提交，任何 downstream retry或 full Task retry只读frozen artifact。full retry的新 Execution复制 exact workflow/policy/actual/formula和typed context（包括 `metadata_disposition`），从最早可重放的 durable step materialize，而不是无条件从 start。

若失败发生在任何frozen input形成前，API返回 `FULL_REPLAY_INPUT_UNAVAILABLE`、`retryable=false` 或提供“创建新observation”的link；不能暗中把 refresh伪装成retry。真正refresh由Q28的新 observation key完成。

#### [支持推荐方案的证据 / Reasoning，或反对其他方案的真相]

- retry复制 exact workflow和actual（`src/runtime/task/task_commands.py:293-318`），与 A/T-O-401一致；B若复用同命令会改变既有 contract。
- 同一代码又清空 snapshot/change set并唤醒新root（`src/runtime/task/task_commands.py:327-350`），证明当前未建立resume coordinate。
- HTTP acquire无任何“retry时读旧artifact”分支，直接调用 `fetcher(url)`（`src/runtime/intake/acquisition_ingest.py:558-598`）；C在URL内容变化时必然读到新bytes。
- actual seal比较 clean step/process/strategy并保持sealed（`src/runtime/workflow/runtime_outcome.py:450-469`）；拿旧seal约束新representation不是exact replay。
- `T-O-401` 已冻结 Process retry与同Task full_task复制 exact workflow/policy/sealed actual（`docs/eval/new-harvest/pre-charter-qna.md:323-348`）。A修代码对齐Truth；B必须正式推翻该Truth并把命令改名为refresh。
- 反对“没有frozen input也重抓一次”：没有任何 durable事实能证明两次fetch是同一Observation；fail-loud比生成假exact更诚实。

#### 问题（请业主裁决）

**Q30：full Task retry选择 A / B / C？若选 A，是否确认：durable acquire前仅允许同attempt的Process transport retry；acquire提交后所有retry零外部调用；full retry复制exact graph/policy/actual/formula/typed context并从frozen artifact resume；没有frozen input时拒绝retry并要求新observation？**

- **业主回答**：🔒 **FROZEN：选择 A。** durable acquire前只允许同ObservationAttempt的Process transport retry；acquire提交后所有retry零外部调用；full Task retry复制exact graph/policy/actual/formula/typed context并从frozen artifact resume；没有verified frozen input时拒绝retry并要求创建新Observation。→ `T-O-410`
- **裁决状态**：`accepted / frozen`

---

## 2. Workflow revision 与 processing taxonomy

### Q31 — kind-family workflow 应如何从漂移的 rev1 演进（来源：`CF-D05`、VF17/VF21、NH-VF21/NH-VF39）

- **影响范围**：registry bootstrap；builtin definitions；persisted DB upgrade；old Execution retry/recovery；formula version；retirement与migration。
- **为什么必须确认**：registry正确地拒绝同 revision异 digest，但 builtin kind family在代码变化后仍写 `revision_number=1`。若不选定版本/兼容法，任何修复图的改动都可能使已有库启动503。
- **当前建议 / 倾向（GPT）**：选 **A**。

#### [对问题的详细解读]

Workflow revision不是发布标签，而是已持久化执行事实。一个 Execution pin了 revision UUID、canonical/compiled digest；代码升级必须仍能解释该图。当前 `_compose` 生成的所有 kind family definition固定 revision 1（`src/workflows/kind_family.py:239-253`），而 registry在已存在同号行且 digest不同的时候明确抛 `REGISTRY_DIGEST_MISMATCH`（`src/services/workflow_registry.py:171-197`）。DDL也唯一约束 `(workflow_uuid, revision_number)` 与 registration fingerprint（`src/persistence/migrations/001_initial.sql:1752-1760`）。

本题要冻结：当前修复后的图使用新revision还是改写旧revision；old definition放在哪里；什么时候可以retire。

#### [可选的方案清单]

| 选项 | 方案 | 产品与工程含义 |
|------|------|----------------|
| **A（推荐）** | **checked-in rev1 exact compat + 当前图升rev2** | bootstrap先验证/注册rev1 exact，再注册rev2并只让新Task选rev2；old Execution继续pin rev1。zero pin/outbox/restart window+retention后才retire。formula/capability变化也升对应version。 |
| **B** | **放宽registry，允许同revision digest漂移** | 升级容易，但revision失去身份意义，旧Execution无法证明实际图。 |
| **C** | **migration直接更新persisted rev1 digest/steps** | 表面保持一个版本，实质改写历史；old Outcome/actual/proof失去可验证性。 |

#### [推荐方案的详细说明]

选择 A 后，仓库保存一份来自 pre-fix/已发布状态的 rev1 canonical fixture和definition loader；它不是当前Python builder重新计算的近似物。当前修复图使用 revision 2，新的 route/guard/control/capability/formula version进入 canonical/compiled digest。bootstrap在切 active revision前验证 rev1 persisted row、rev2 code manifest和capability manifest。

retirement是显式状态机：新Task已只写rev2；rev1 active Execution、retry lineage、pending/in-flight outbox、retention窗口均为零，才将rev1/旧profile key设为retired。不得删除解释历史所需的manifest。

#### [支持推荐方案的证据 / Reasoning，或反对其他方案的真相]

- builtin当前固定revision 1但会通过dict去重改变guards canonical（`src/workflows/kind_family.py:231-253`）；同号漂移不是理论风险。
- registry注释与实现都要求新增immutable revision、old Execution保留pin（`src/services/workflow_registry.py:178-197`）；A沿用既有正确设计。
- DDL双唯一索引把revision number和fingerprint作为稳定identity（`src/persistence/migrations/001_initial.sql:1757-1760`）；B/C需要破坏或绕过承重约束。
- composition root已经区分active definitions与compatibility definitions（`api/app.py:427-440`），说明保留old pin有现成接缝。
- `T-O-401` 要求同Task retry exact pin（`docs/eval/new-harvest/pre-charter-qna.md:323-348`）；B/C会使“exact”在代码升级后变成假话。
- 反对“等in-flight=0就改rev1”：历史Task/restart/evidence仍引用旧digest，in-flight=0不等于解释义务为零。

#### 问题（请业主裁决）

**Q31：workflow演进选择 A / B / C？若选 A，是否确认：保存checked-in rev1 exact fixture；当前修复图升revision 2；新Task只选rev2，old Execution/retry继续exact rev1；任何canonical/capability/formula变化必须升版；仅在zero pin/outbox/restart window和retention满足后retire旧入口？**

- **业主回答**：🔒 **FROZEN：选择 A。** 保存checked-in rev1 exact fixture；NHX1修复图升revision 2，新Task只选rev2，old Execution/retry继续exact rev1；任何canonical、capability或formula变化必须升版；仅在zero pin、outbox、restart window与retention门全部满足后retire旧入口。→ `T-O-411`
- **裁决状态**：`accepted / frozen`

---

### Q32 — registered API map 属于 CleanStrategy 还是独立 operation binding（来源：`CF-D06`、VF20、10+3闭集）

- **影响范围**：actual S05 schema/digest；10 strategy + 3 operation目录；capability manifest；scatter root/child；Task actual projection与测试分母。
- **为什么必须确认**：代码把 `clean.map.registered_api` 映射成闭集外字符串 `registered_api.map`，但 CleanStrategy enum/definitions只有10项且无任何策略消费 registered API acquire capability。直接“补进列表”会改写已冻结10+3 taxonomy。
- **当前建议 / 倾向（GPT）**：选 **A**。

#### [对问题的详细解读]

10个 CleanStrategy描述表示已知后选择哪类clean worker；3个 registered API operation描述 provider/operation/version 的mapper contract。两者都属于实际 processing binding，但不是同一个命名空间。

CleanStrategy enum明确只有10项（`src/contracts/intake/strategies.py:15-26`），definition要求 `clean_capability`并描述web/pdf/doc（`src/contracts/intake/strategies.py:28-46`）。registered API虽有 acquire capability集合（`src/contracts/intake/strategies.py:178-183`），没有对应 CleanStrategyDefinition；实际S05 helper却返回 `registered_api.map`（`src/runtime/binding/actual_s05.py:16-34`）。另一方面，仓库已经有三项 versioned ProviderOperationDefinition及各自 digest（`intake/api/registry.py:35-117`）。

#### [可选的方案清单]

| 选项 | 方案 | 产品与工程含义 |
|------|------|----------------|
| **A（推荐）** | **`ProcessingBinding` typed union** | actual binding写 `binding_family=clean_strategy / registered_api_operation`，再写key/version/digest；两族共享seal/replay接口，但分别由10策略registry和3 operation registry校验。 |
| **B** | **新增第11个 `registered_api.map` CleanStrategy** | 实现简单，但把provider operation塞进web/pdf/doc clean taxonomy，10+3闭集变为11+3或重复计数。 |
| **C** | **registered API不写actual binding** | 保持10项纯净，但API通道失去实际处理身份、replay/leaf-worker解释链不完整。 |

#### [推荐方案的详细说明]

选择 A 后，Execution actual v2不再只有 `actual_clean_strategy` 一个字符串，而是持久化 binding family、binding key、definition version/digest以及selected process/route。clean路径引用 `CleanStrategyDefinition`；registered API路径引用 `(provider, operation, definition_version)` 的 ProviderOperationDefinition。

actual aggregate、Task view、catalog和assurance都按union投影：10 strategy仍是10；3 operation仍是3；共同闭集为13个 processing cells。`clean.map.registered_api`仍可作为内部Process capability，但不再制造一个无registry的“第11策略”。

#### [支持推荐方案的证据 / Reasoning，或反对其他方案的真相]

- CleanStrategy enum只有10项（`src/contracts/intake/strategies.py:15-26`），且所有strategy均属于web/pdf/doc channel（`src/contracts/intake/strategies.py:28-38`）。
- `SOURCE_KIND_ACQUIRE_CAPABILITIES`含registered API，但没有CleanStrategyDefinition使用该capability（`src/contracts/intake/strategies.py:157-212`）；B会新增一套与现结构不同的特殊定义。
- S05 helper硬编码闭集外 `registered_api.map`（`src/runtime/binding/actual_s05.py:19-34`），说明当前字符串union已经存在但没有type/version/digest。
- Provider operation registry已提供三项独立schema/normalizer/digest权威（`intake/api/registry.py:35-117`）；A复用它，不再复制definition。
- scatter图与pipeline确实执行 `clean.map.registered_api`（`src/workflows/builtin_scatter.py:105,364`；`src/runtime/intake/core.py:380`），所以C会留下实际worker不可解释。
- `T-O-381` 冻结的是10 strategy + 3 operation（`docs/eval/new-harvest/pre-initial-planning-qna.md:191-214`）；A保持分母，B改变分母。

#### 问题（请业主裁决）

**Q32：registered API actual binding选择 A / B / C？若选 A，是否确认actual v2采用 `ProcessingBinding(clean_strategy | registered_api_operation)` typed union，两族各引用自身versioned registry/digest，共享seal/replay但保持10 strategy + 3 operation分账？**

- **业主回答**：🔒 **FROZEN：选择 A。** actual v2采用 `ProcessingBinding` typed union，分为 `clean_strategy` 与 `registered_api_operation`；两族分别引用自身versioned registry/digest，共享seal/replay contract，并保持10 strategy + 3 operation分账。→ `T-O-412`
- **裁决状态**：`accepted / frozen`

---

## 3. Object ownership 与 evidence 修复法

### Q33 — public upload 的 byte handle 与调用会话所有权是否分离（来源：`CF-D07`、VF22/VF23/VF26/VF27）

- **影响范围**：upload/stat/cancel contract；idempotency；pending TTL；local_object admission/consume；promotion journal；GC与前端。
- **为什么必须确认**：handle由Team+digest表示相同字节，但每次upload创建随机hold owner；public response/cancel只携带handle。多个会话共享字节时，调用方无法指明自己要取消或消费哪一条hold。
- **当前建议 / 倾向（GPT）**：选 **A**。

#### [对问题的详细解读]

内容寻址handle回答“是哪份字节”，不回答“哪次upload调用拥有它”。同字节重放可能是同一网络命令，也可能是两个独立业务会话：前者应返回同一结果，后者应拥有两个独立TTL/cancel权。

当前 `PublicObjectView` 和 cancel request只有handle（`src/contracts/api/objects.py:12-21`）。upload每次生成新的 `hold_owner=uuid7()`（`src/services/object_upload.py:104-126`），但没有把owner返回；cancel只能按时间释放最新pending（`src/services/object_upload_ttl.py:62-82`），ingest acceptance则一次释放该对象全部public pending（`src/runtime/intake/acceptance_snapshot.py:318-335`）。

#### [可选的方案清单]

| 选项 | 方案 | 产品与工程含义 |
|------|------|----------------|
| **A（推荐）** | **durable `ObjectUploadSession` + opaque session token** | handle只代表bytes；session由team+idempotency key唯一，拥有exact pending ref。upload/stat/cancel/ingest reserve/consume按session CAS；同命令replay同session，新命令同bytes可建独立session。 |
| **B** | **每个Team+digest只允许一条pending hold** | API简单，但多个调用者共用TTL/cancel；一个取消会影响另一个，无法表达独立业务会话。 |
| **C** | **继续只用handle，把cancel定义为取消该digest全部pending** | 语义明确但破坏隔离；任何知道handle的同Team调用者可释放他人会话。 |

#### [推荐方案的详细说明]

选择 A 后，upload request增加idempotency key；response增加opaque session token和command disposition。服务先验证Team并创建带 `staging_id` 的 receiving session，再stream/fsync、CAS prepared(digest,size)、promote、同UoW提交catalog+exact pending ref+committed session，最后才返回。

Task admission用session token把 `committed` CAS为 `reserved_by_task(task,generation)`；reserved session不被TTL释放。acceptance只把该session的pending ref转换为snapshot/revision业务ref；Task terminal未消费则reconciler释放。session token存hash、Team-fenced，不包含path/digest secret。

#### [支持推荐方案的证据 / Reasoning，或反对其他方案的真相]

- public contract只返回/接收handle（`src/contracts/api/objects.py:12-21`），现调用方不可能指定hold owner。
- upload为每次调用生成随机owner（`src/services/object_upload.py:104-126`）；DDL unique也包含owner UUID，事实上允许同bytes多hold（`src/persistence/migrations/021_nh4_upload_pending.sql:40-48`）。B/C会丢掉数据库已经表达的会话基数。
- cancel用 `ORDER BY created_at DESC LIMIT 1` 猜owner（`src/services/object_upload_ttl.py:73-80`），同一请求重放可能依次释放不同hold，不是幂等命令。
- acceptance按stored object释放全部pending（`src/runtime/intake/acceptance_snapshot.py:330-335`），一个ingest可消费其它会话。
- TTL无条件扫描所有超时pending（`src/services/object_upload_ttl.py:40-60`），Task排队时没有reservation状态，证明session必须进入admission UoW。
- promote发生在Team校验和catalog之前（`src/services/object_upload.py:55-71`）；A的durable session同时给pre-catalog crash一个可恢复journal，B/C没有该坐标。

#### 问题（请业主裁决）

**Q33：upload ownership选择 A / B / C？若选 A，是否确认：handle只代表bytes；session token代表一次调用和pending owner；同idempotency key replay同session，新命令同bytes可建独立session；cancel/TTL/reserve/consume均按session CAS；usable handle只在catalog+exact pending+committed session后返回？**

- **业主回答**：🔒 **FROZEN：选择 A。** object handle只代表bytes，opaque session token代表一次upload调用与exact pending owner；同idempotency key replay同session，新命令即使同bytes也可建独立session；cancel、TTL、Task reserve与consume均按session CAS；仅在catalog、exact pending ref与committed session同UoW完成后返回usable handle。→ `T-O-413`
- **裁决状态**：`accepted / frozen`

---

### Q34 — 已失实或可变的 legacy evidence 应原地修、旁路纠正还是忽略（来源：`CF-D08`、VF18/VF19/VF21、NH-VF4.r）

- **影响范围**：selected output、RepresentationFact/History、path digest、GenerationArtifact、vector identity、publication proof、retrieval与migration。
- **为什么必须确认**：当前生产selection把 output manifest digest冒充 representation fact digest；部分evidence可普通SQL更新。若直接UPDATE历史，修复后的值不是“当时写入的事实”；若完全忽略，又无法告诉operator/retrieval哪些旧证据可信。
- **当前建议 / 倾向（GPT）**：选 **A**。

#### [对问题的详细解读]

Evidence 的职责是证明当时发生了什么，不是保存“当前最想看到的正确值”。已经写错的evidence有三种可能：仍可从同一UoW的其它immutable事实确定性重算；无法重算但可判失实；完全缺少当时事实。三者不能都靠UPDATE成新值。

当前 materializer把 `representation_fact_digest` 直接设成 `output_manifest_digest`（`src/runtime/workflow/runtime_materialize.py:872-888`），而正式selection公式把fact digest作为独立输入（`src/runtime/workflow/selected_output.py:53-124`）。selected-output表又以 `(execution, control_step)` 唯一（`src/persistence/migrations/018_nh2_selected_output_control.sql:6-31`），没有correction generation。024只保护fact/history和indexed `content_digest`（`src/persistence/migrations/024_nh_review_invariants.sql:22-51`），GenerationArtifact及vector其它identity列仍可改（`src/persistence/migrations/001_initial.sql:1270-1331,1437-1478`）。

#### [可选的方案清单]

| 选项 | 方案 | 产品与工程含义 |
|------|------|----------------|
| **A（推荐）** | **append-only verification ledger + versioned correction assertion** | 旧行不改；写 `verified/invalid/legacy_unverifiable` verdict。可确定重算时新增v2 assertion并 `supersedes` 旧行；新formula升version。mutable projection与immutable identity分表/分列保护。 |
| **B** | **migration原地UPDATE旧evidence为新公式** | 查询最干净，但历史被改写；无法证明值来自当时UoW还是事后推断。 |
| **C** | **只修新writer，旧evidence不标状态** | 实现最小，但operator/retrieval仍可能把旧错值当verified proof。 |

#### [推荐方案的详细说明]

选择 A 后，建立 evidence verification ledger，按evidence kind/UUID/formula version记录 verdict、reason、verifier version、checked_at和可选correction UUID。selection/path/publication等公式由唯一versioned函数实现。可从durable RepresentationFact重算的旧selection写v2 correction assertion；不能重算的标 `legacy_unverifiable`，不得参加新publication或声称verified retry。

EvidencePlane（facts/history/selection assertions/artifact identity/publication/delete proof）append-only；Task/Execution/Item pointer、outbox、vector availability属于ProjectionPlane，可CAS更新。vector的embedding/model/content identity与publication state拆开，避免“先改state再改digest”绕trigger。

#### [支持推荐方案的证据 / Reasoning，或反对其他方案的真相]

- 当前错误赋值是确定的：`representation_fact_digest = output_manifest_digest`（`src/runtime/workflow/runtime_materialize.py:875-888`），而canonical helper要求独立fact digest（`src/runtime/workflow/selected_output.py:88-124`）。
- selected-output v1没有fact-digest列且每control只能一行（`src/persistence/migrations/018_nh2_selected_output_control.sql:6-31`）；要保留历史并纠正，必须新version/assertion generation，不能挤进旧行。
- 024对RepresentationFact/History有no-update/no-delete（`src/persistence/migrations/024_nh_review_invariants.sql:22-44`），说明append-only已是冻结方向；B反而破坏它。
- vector trigger只在OLD state为indexed时保护content digest（`src/persistence/migrations/024_nh_review_invariants.sql:46-51`）；embedding/model/artifact坐标不受保护，证明“加一个trigger”不足以定义整个EvidencePlane。
- GenerationArtifact有大量identity/digest字段但没有immutable trigger（`src/persistence/migrations/001_initial.sql:1270-1331`）；C会让“新writer正确”仍无法约束DB evidence。
- 反对B：事后UPDATE无法区分“修正当时事实”和“用当前规则重解释历史”，会破坏old-pin exact与审计可采信性。

#### 问题（请业主裁决）

**Q34：legacy evidence修复选择 A / B / C？若选 A，是否确认：旧evidence永不原地改；统一写verification verdict；可确定重算时追加versioned correction/supersedes；不可重算标legacy_unverifiable；新publication/retry只消费verified且formula匹配的evidence；identity与mutable projection分面？**

- **业主回答**：🔒 **FROZEN：选择 A。** 旧evidence永不原地改写；统一追加verification verdict；可确定重算时写versioned correction/supersedes，不可重算标 `legacy_unverifiable`；新publication/retry只消费verified且formula匹配的evidence；immutable identity与mutable projection严格分面。→ `T-O-414`
- **裁决状态**：`accepted / frozen`

---

## 4. Leaf-worker 读面、部署角色与长期运维契约

### Q35 — workflow discovery、业务读面与 operator debug/control 应如何分权（来源：`CF-D09`、VF33–VF39/VF43/VF44/VF46）

- **影响范围**：leaf-worker上游；public OpenAPI/SDK；Task/Item/Namespace列表；Process/Stage/Fact诊断；retry/restart/stop/requeue/repair；S15权限与redaction。
- **为什么必须确认**：当前上游无法发现workflow/capability/namespace，Task view看不到actual binding；operator只有timeline和dead-outbox读取，没有正式repair/control。若不先冻结public/internal边界，实现者可能选择“继续隐藏”或“把完整内部payload公开”两个极端。
- **当前建议 / 倾向（GPT）**：选 **A**。

#### [对问题的详细解读]

“caller不能指定 `workflow_key`”和“caller不能知道系统支持什么”不是同一条法律。上游需要发现四个source kind、10 strategy、3 operation、active revision、required/deployed capability及availability，才能分类、构建合法请求和解释503；但 Task create仍应只交typed source/policy，由server选图。

同样，public业务调用方需要看到自己的Task实际走了哪种kind/mode/binding、卡在什么phase、是否可重试；Process input/output、representation facts、event payload和repair命令则属于operator面，必须继续受token+internal-network保护。

当前 public routes覆盖Team/Task/object/gate/retrieval，但没有workflow/capability/intake-item/namespace/process目录（`api/public/routes.py:109-576`）。Task view只投影基础字段/counts（`src/runtime/task/task_views.py:34-94`）；`waiting`又被折叠成public `running`（`src/runtime/task/task_views.py:202-215`）。internal router有全局operator guard（`api/internal/routes.py:11-14`），但现端点只有prompt、timeline、dead list、security audit（`api/internal/routes.py:17-161`）。

#### [可选的方案清单]

| 选项 | 方案 | 产品与工程含义 |
|------|------|----------------|
| **A（推荐）** | **public safe discovery/业务view + internal debug/control双面** | authenticated public提供workflow/capability目录、Task actual/phase、Item/Namespace lists与CommandReceipt；不接受workflow key。operator提供Process/Stage/Fact/diagnostic/dead owner及typed repair/restart/stop/requeue，全部redacted/audited/CAS。 |
| **B** | **全部只放internal/operator面** | 安全边界最窄，但leaf-worker上游和普通前端仍无法冷启动发现/解释，只能靠离线文档或人工转述。 |
| **C** | **把完整workflow topology、Process/Fact payload和control都开放public** | 调试方便，但扩大secret/body/topology暴露与误操作面，破坏S15/S16分权。 |

#### [推荐方案的详细说明]

选择 A 后，public authenticated目录至少提供 source kinds、active/compatible workflow revisions、processing policies、10 strategies、3 operations、required/deployed capabilities和availability；`TaskCreateRequest`仍没有 `workflow_key/process_key/branch`。

public Task strict view增加 observation、source kind、declared acquisition mode、processing policy、actual binding family/key、workflow revision、snapshot/item、phase/waiting reason、result disposition、redacted error与retryable。Team-scoped Item/Namespace list提供cold-start discovery；所有cursor绑定filter digest。

operator read/control提供 Process、StageReport、RepresentationFact/History、Selection/Actual、Diagnostic、CleanupJob、Outbox owner；默认只回registered redacted projection和payload digest。control使用expected revision/generation、idempotency key、CommandReceipt和security audit，永不开放任意SQL/raw CAS read。

#### [支持推荐方案的证据 / Reasoning，或反对其他方案的真相]

- public route列表没有任何workflow/capability/namespace/intake-item/process discovery（`api/public/routes.py:109-576`）；B会保留已验证的leaf-worker断点。
- Task route未声明response model并返回裸dict/Response（`api/public/routes.py:228-330`），尽管已有 `TaskView` model（`src/contracts/api/models.py:640-662`）；当前OpenAPI GET/list是 `additionalProperties: true`，A要求wire与已有model对齐。
- Task `_view`没有source kind、actual、workflow revision、snapshot/item或phase（`src/runtime/task/task_views.py:61-94`）；这些是已发生事实，不是caller选图权。
- `waiting`被折成`running`（`src/runtime/task/task_views.py:202-215`）；保留六态没有问题，但必须补phase/reason才能解释fanin/retry/gate。
- operator router已经有token+internal-network统一guard（`api/internal/routes.py:11-14`），A可以安全扩展而无需发明第三套auth。
- timeline故意只回payload digest（`src/services/observability.py:389-412`），证明完整debug应是单独registered surface，不应选择C直接放开。
- internal dead-outbox只有GET（`api/internal/routes.py:133-146`），A用typed control替代人工SQL；B只读仍不能恢复。

#### 问题（请业主裁决）

**Q35：leaf-worker读控面选择 A / B / C？若选 A，是否确认：public authenticated面提供安全catalog、Task actual/phase、Item/Namespace lists和CommandReceipt，但Task create仍禁workflow key；Process/Stage/Fact/Diagnostic/payload与repair/restart/stop/requeue只在operator面，以redaction+expected fence+audit约束？**

- **业主回答**：🔒 **FROZEN：选择 A。** public authenticated面提供安全workflow/capability catalog、Task actual/phase、Item/Namespace lists与CommandReceipt，但Task create继续禁止workflow key；Process、Stage、Fact、Diagnostic、registered payload及repair/restart/stop/requeue只在operator面，以redaction、expected fence与audit约束。→ `T-O-415`
- **裁决状态**：`accepted / frozen`

---

### Q36 — “leaf-worker”应是单体名称、同binary角色，还是独立代码服务（来源：`CF-D10`、VF29/VF32/VF42/VF48）

- **影响范围**：application lifespan；worker/GC/retention ownership；readiness；deployment；horizontal scaling；supervisor failure与capability availability。
- **为什么必须确认**：当前FastAPI标题叫leaf worker，但每个进程总会启动workflow supervisor、GC、upload TTL、retirement和retention。没有role字段，readiness也只有一套required set。继续扩control/maintenance会加重单体隐式所有权。
- **当前建议 / 倾向（GPT）**：选 **A**。

#### [对问题的详细解读]

Deployment role回答“这个进程被授权做什么”，不同于workflow execution role。API-only进程应提供read/admission但不claim Process或跑GC；workflow worker应按capability claim；maintenance应拥有GC/retention/cleanup。小型部署仍可使用 `all`，但这是显式选择。

当前 `lifespan` 无条件启动workflow supervisor和retention，并按feature flag启动三类maintenance scanner（`api/app.py:586-647`）；`create_app`只把产品标题写成“MKB leaf worker”（`api/app.py:655-658`）。Settings没有deployment role（`src/runtime/config.py:12-70`）。HealthAggregator只有一个required tuple（`src/runtime/health.py:15-50`），无法表达API与worker不同的就绪条件。

#### [可选的方案清单]

| 选项 | 方案 | 产品与工程含义 |
|------|------|----------------|
| **A（推荐）** | **同一binary显式 `api / workflow_worker / maintenance / all` role** | composition按role启动组件、注册capability和计算readiness；小部署用all，生产可拆。DB contract/代码库保持一套。 |
| **B** | **继续单进程monolith，leaf-worker只是名称** | 改动最少；API扩容会重复启动worker/GC，maintenance owner和故障影响面继续隐式。 |
| **C** | **立即拆成多个独立binary/代码服务** | 隔离最强，但复制composition/config/release，超出本轮对contract与角色治理的必要范围。 |

#### [推荐方案的详细说明]

选择 A 后，Settings增加deployment role和worker capability allowlist。`api`启动HTTP/admission/reads；`workflow_worker`启动supervisor和所部署capability adapters；`maintenance`启动object/upload/cleanup/index/retention scanners；`all`组合前三者供开发和单节点部署。

每个role有独立required components：API需要DB/schema/registry/object/auth/read model；worker还需其claimable Process所需的supply；maintenance需要对应storage/scanner。目录投影“workflow requires什么”和“当前role部署什么”。supervisor `consecutive_failures`超过阈值时worker readiness=false并发diagnostic/metric/alert，API liveness不被伪装成全系统ready。

#### [支持推荐方案的证据 / Reasoning，或反对其他方案的真相]

- 当前每个app实例无条件创建并运行workflow supervisor（`api/app.py:467-489,586-605`），API水平扩展会自然增加worker owner数量；B把该行为当偶然实现。
- 同一lifespan还启动GC、upload lifecycle、index retirement、observability retention（`api/app.py:605-647`），maintenance ownership没有独立边界。
- 标题是唯一“leaf worker”实体（`api/app.py:655-658`）；没有role contract，印证VF48。
- `HealthAggregator`只有一套required set（`src/runtime/health.py:15-50`）；role-specific readiness必须先有role。
- Turso配置默认要求concurrent writes但adapter明确报告false（`src/runtime/config.py:21-27`; `src/persistence/turso/port.py:176-205`），现测试仍期待overall ready（`tests/unit/test_ns6_default_ready.py:15-39`）；A允许single-writer/worker role诚实声明，B继续混用画像。
- supervisor异常只留 `last_error/consecutive_failures` 内存字段（`src/runtime/workflow_supervisor.py:36-77`）；A给这些状态明确readiness owner。
- 反对C：现有Container/ports已经支持注入；按role裁剪lifespan可取得主要隔离收益，无需复制代码服务。

#### 问题（请业主裁决）

**Q36：deployment选择 A / B / C？若选 A，是否确认同一binary提供 `api/workflow_worker/maintenance/all` 显式role，各role只启动所属loop、注册所部署capability并计算独立readiness，小型部署可用all，未来拆实例不改变contract？**

- **业主回答**：🔒 **FROZEN：选择 A。** 同一binary提供 `api`、`workflow_worker`、`maintenance`、`all` 显式deployment role；各role只启动所属loop、注册所部署capability并计算独立readiness，小型部署可用all，未来拆实例不得改变contract与DB owner。→ `T-O-416`
- **裁决状态**：`accepted / frozen`

---

### Q37 — Intake logical delete 后，NHX1 是否必须完成物理引用与字节收敛（来源：`CF-D11`、VF24/VF25、NH-VF13/NH-VF38）

- **影响范围**：Item delete；cleanup intent/executor；Snapshot/Revision/Generation/Vector refs；retention；object GC；operator status和closure。
- **为什么必须确认**：当前delete建立cleanup intent但只按 `owner_uuid=item_uuid` 释放引用；实际artifact refs由Snapshot/Revision拥有。cleanup声明三类substrate，却只有index generation retirement executor。若继续logical-only，磁盘与open cleanup会永久增长。
- **当前建议 / 倾向（GPT）**：选 **A**。

#### [对问题的详细解读]

Logical delete负责立即停止serving；physical convergence负责在retention/recovery窗口后释放所有业务ref、软退vector/generation并让无主CAS进入GC。两者不能在同一HTTP事务立即递归删除，但长期治理阶段也不能永远只做第一半。

当前delete确实withdraw serving/vector，并创建cleanup intent（`src/services/intake_lifecycle/lifecycle_apply.py:125-147,275-305`）。但释放SQL只匹配 `owner_uuid=intake_item_uuid`（`src/services/intake_lifecycle/lifecycle_apply.py:136-141`）；acceptance写的refs owner却是 Snapshot/Revision（`src/runtime/intake/acceptance_snapshot.py:288-327`）。cleanup intent声明 `derived_generation/intake_artifact/vector_projection` 三substrate（`src/services/intake_lifecycle/lifecycle_apply.py:288-304`），现成retirement只处理 `vector_projection_soft_delete`（`src/services/index_retirement.py:26-34`）。

#### [可选的方案清单]

| 选项 | 方案 | 产品与工程含义 |
|------|------|----------------|
| **A（推荐）** | **durable cleanup job + retention + exact ref release + purge proof** | delete即时logical fence；后台按Snapshot/Revision/Generation/Vector owner图收敛。每substrate有executor/status/retry；最后释放object refs、GC quarantine/destroy并写proof。 |
| **B** | **永久logical-only，字节与artifact refs无限保留** | 实现简单、恢复最保守；不满足长期磁盘/隐私/cleanup治理，open intent无终态。 |
| **C** | **delete请求中立即级联删除所有行和字节** | 回收最快，但破坏retention、replay、审计和crash recovery；半删风险最大。 |

#### [推荐方案的详细说明]

选择 A 后，Item delete UoW只做第一阶段：ItemEpoch/lifecycle/serving/vector fence、immutable transition和cleanup job。job冻结owner graph与required substrate set，按 `intake_artifact → derived_generation → vector_projection → object_reference → object_gc` 或经设计验证后的顺序串行推进；每步idempotent、带expected fence和proof。

retention期内业务不可serve，但证据/rollback policy允许保留。到期后逐owner释放：Snapshot source/raw refs、Revision clean refs、Generation artifacts、vector projections；operator/backup hold继续阻止GC。final状态必须能从API回答 `pending/blocked/running/completed/failed` 与blocked reason。tombstoned+quarantined字节由durable deletion job完成destroy，不能被reconcile跳过。

#### [支持推荐方案的证据 / Reasoning，或反对其他方案的真相]

- delete释放条件使用Item UUID（`src/services/intake_lifecycle/lifecycle_apply.py:136-141`），而真实refs owner是Snapshot/Revision UUID（`src/runtime/intake/acceptance_snapshot.py:288-327`）；B会保留live refs，GC永远看不到orphan。
- cleanup intent已声明三substrate（`src/services/intake_lifecycle/lifecycle_apply.py:275-305`），说明产品模型预期异步收敛，不支持C立即级联。
- index retirement明确声明只拥有vector projection、不碰generation artifact bytes（`src/services/index_retirement.py:1-11,26-34`）；缺的是其它executor，不是一个万能delete SQL。
- Object GC只删除已经无live refs的catalog object（`src/services/object_gc.py:134-167,339-366`）；A尊重reference-first法，C会绕过。
- quarantine reconcile只恢复live catalog，tombstoned行被跳过（`src/services/object_gc.py:169-189`）；A要求job记录quarantined→tombstoned→destroyed并在重启后收尾。
- 反对B：现cleanup intent若永远open，不仅是磁盘成本，也会作为GC cleanup fence持续阻断对象回收。

#### 问题（请业主裁决）

**Q37：delete物理收敛选择 A / B / C？若选 A，是否确认：HTTP delete只做即时logical fence；NHX1必须实现有retention的durable cleanup job、三类substrate executor、exact owner ref release、GC deletion proof和operator状态；open hold可阻塞，但不能无executor永久open？**

- **业主回答**：🔒 **FROZEN：选择 A。** HTTP delete只提交即时logical fence；NHX1必须实现带retention的durable cleanup job、`derived_generation/intake_artifact/vector_projection` executors、exact owner ref release、GC deletion proof与operator状态；open hold可以显式阻塞，但cleanup不得因缺executor永久open。→ `T-O-417`
- **裁决状态**：`accepted / frozen`

---

### Q38 — public/operator 错误码应如何结束 SCREAMING_SNAKE 与 kebab-case 双轨（来源：`CF-D12`、VF51）

- **影响范围**：ErrorEnvelope；HTTP status；SDK/retryability；Task/Process/outbox persisted error；legacy compatibility；metrics与runbook。
- **为什么必须确认**：当前 `MkbError` 接受任意code字符串；同一业务面混用两种命名。直接批量改名会破坏v1客户端，继续混用又让前端无法建立稳定switch/retry policy。
- **当前建议 / 倾向（GPT）**：选 **A**。

#### [对问题的详细解读]

错误码不仅是文案标签，还应稳定定义 category、HTTP status、retryable、public message和operator action。现在 `MkbError` 只截断任意字符串并输出，没有registry校验（`src/contracts/common/errors.py:70-94`）。例如 task/service使用 `task-identity-conflict`、`stage-output-conflict` 等kebab-case（`src/runtime/task/task_create.py:80-86`; `src/services/artifacts.py:91-121`），同一系统又大量使用 `OBJECT_*`、`RETRIEVE_*`、`CLEAN_*`。

NH8测试甚至需要同时维护两种闭集（`tests/unit/test_nh8_intent_applicability.py:17-34`）。本题要决定v2 canonical格式、v1兼容方式以及新code是否必须注册。

#### [可选的方案清单]

| 选项 | 方案 | 产品与工程含义 |
|------|------|----------------|
| **A（推荐）** | **v2 canonical error registry，统一 `UPPER_SNAKE_CASE`；v1 alias兼容** | 每个code登记status/category/retryable/public message/legacy aliases。新端点与v2 projection只发canonical；v1在既有route维持alias或协商映射，不再新增kebab code。 |
| **B** | **保留双轨，按模块自行命名** | 无breaking migration，但SDK/前端继续维护散落列表，retryability靠猜。 |
| **C** | **一次性把所有v1错误改为UPPER_SNAKE且不留alias** | 内部最整齐，但立即破坏现客户端、测试、persisted error和runbook。 |

#### [推荐方案的详细说明]

选择 A 后，建立code-owned ErrorDefinition registry；构造public/operational error必须解析registry项，禁止任意新字符串。canonical code使用 `UPPER_SNAKE_CASE`，包含固定HTTP status、category（validation/conflict/dependency/fence/integrity/security等）、retryability与安全message模板。

v1现有route可继续发legacy alias，或在明确的schema/version协商下返回canonical+legacy alias；persisted旧code通过alias映射读取，不UPDATE历史。Task view和CommandReceipt直接提供 `retryable`，前端不再从status或字符串推断。

#### [支持推荐方案的证据 / Reasoning，或反对其他方案的真相]

- `MkbError.code` 是任意字符串，`as_dict`只做长度截断（`src/contracts/common/errors.py:70-89`），没有authoritative registry；B会继续扩散。
- `ConflictError`只固定HTTP 409，不定义retryability或code family（`src/contracts/common/errors.py:92-99`）。
- 同一Task路径已有lower-case `team-not-active/task-identity-conflict`（`src/runtime/task/task_create.py:74-86`），object/retrieval/clean则使用uppercase（如 `src/services/object_upload.py:99-100`; `src/services/retrieval/retrieval_request.py:104-122`; `src/contracts/intake/strategies.py:186-207`）。
- NH8闭集显式混合两种命名（`tests/unit/test_nh8_intent_applicability.py:17-34`），证明双轨已经进入contract/test，不适合C无兼容改名。
- persisted Task/Process/outbox都有error code字段；A用alias reader保持历史可解释，C原地改历史会破坏evidence law。
- 反对B：“模块自治”对内部异常可行，对public machine-readable contract不可行；同义冲突会直接转化为SDK分支和错误重试。

#### 问题（请业主裁决）

**Q38：错误码治理选择 A / B / C？若选 A，是否确认：v2 canonical code统一UPPER_SNAKE并必须登记status/category/retryable/message；v1/persisted旧code通过legacy alias兼容、不改历史；新代码禁止新增未注册kebab-case；Task/receipt直接投影retryable？**

- **业主回答**：🔒 **FROZEN：选择 A。** v2 canonical error code统一 `UPPER_SNAKE_CASE`，必须登记status、category、retryable与public message；v1/persisted旧code通过legacy alias兼容且不改历史；新代码禁止新增未注册kebab-case；Task/CommandReceipt直接投影retryable。→ `T-O-418`
- **裁决状态**：`accepted / frozen`

---

## 5. Production closure 与显式 scope reopen

### Q39 — 真模型、真实 runtime supply 与 S16 未签时，NHX1 能否宣告完成（来源：`CF-D13`、VF30/VF32、NH-VF14.r、S16）

- **影响范围**：10 strategy + 3 operation completeness；production profile；PDF/browser/OCR/Vision/DU/LLM；readiness；L3/L4证据；owner sign-off与NHX1 closure状态。
- **为什么必须确认**：业主要求把应内聚的deferred纳入NHX1，但真实模型凭据、binary和S16签名可能依赖外部窗口。必须先决定“工程ready”和“阶段closed”是否可以分开，避免再次用stub/fixture将owner gate写成完成。
- **当前建议 / 倾向（GPT）**：选 **A**。

#### [对问题的详细解读]

NHX1可以在代码层完成adapter、role profile、readiness、security fence、真实测试入口和evidence collector；但只有真实binary/model/data/egress环境才能证明production路径。若外部条件暂缺，工程工作可以达到 `ready-for-owner-gate`，阶段却仍应是 `blocked-by-owner`，而不是 `closed-with-deferred`。

当前默认 `ns1_cli_mode="stub"`、`multimodal_enabled=False`、`runtime_supply_readiness_required=False`（`src/runtime/config.py:40-63`）；composition在stub模式直接注入 `DeterministicNs1Stub`（`api/app.py:456-480`）。所谓deterministic OCR身份明确是 `glyph5x7` worker（`src/runtime/supply/deterministic_ocr.py:62-84`），不能代表通用生产OCR。supply probe只有配置要求时才运行（`api/app.py:215-271`）。

#### [可选的方案清单]

| 选项 | 方案 | 产品与工程含义 |
|------|------|----------------|
| **A（推荐）** | **真实supply与S16是NHX1 final closure硬闸** | 工程可完成到ready-for-owner-gate；缺真实模型/binary/签名时NHX1状态blocked，不得closed。prod profile禁stub，10+3均需真实L3/L4与pinned identity/security证据。 |
| **B** | **代码/fixture绿即可close，真实supply继续defer** | 交付速度快，但重复NH1–NH9的主要欠账；“完整接线”仍无法在生产成立。 |
| **C** | **把model-bound/browser/OCR路径从NHX1 scope删除** | 可诚实缩小范围，但正式推翻 `T-O-376/381/399/406` 与业主本轮“容纳全部工作”的目标。 |

#### [推荐方案的详细说明]

选择 A 后，NHX1定义 `test/dev/prod` profile。stub、fixture OCR和fake handler只能在test profile；prod要求每个claimable capability拥有pinned binary/model/data identity、readiness实弹、资源/egress限制、SBOM/CVE/negative evidence。10 strategy + 3 operation的L3/L4必须由prod-compatible profile运行到retrieval或其合法终态。

外部凭据或S16签名不由实现者伪造：相关节点完成后标 `ready-for-owner-gate`，owner实际验证并签UTC/identity后才转green。任何未签项使NHX1整体保持blocked；closure必须明确列出阻塞，不得把skip或stub PASS计入分母。

#### [支持推荐方案的证据 / Reasoning，或反对其他方案的真相]

- 默认配置明确使用stub、关闭multimodal、且不要求runtime supply readiness（`src/runtime/config.py:40-63`）；B会把默认开发画像误称production完成。
- composition实际构造 `DeterministicNs1Stub`（`api/app.py:456-480`），不是仅文档上的备用入口。
- OCR engine自报 `ocr.deterministic.glyph5x7.v1`（`src/runtime/supply/deterministic_ocr.py:62-84`）；它可证明隔离/port，不可证明任意文档OCR质量。
- supply probes仅在 `runtime_supply_readiness_required` 时执行（`api/app.py:215-271`），所以“组件对象存在”不等于prod ready。
- browser当前no-sandbox检查针对即将提交的args是需要继续强化的代码位点（`src/runtime/supply/browser.py:220-260`）；冻结security Truth要求non-root、禁no-sandbox、S16 egress、pin/SBOM/CVE/负样本/readiness（`docs/eval/new-harvest/pre-charter-qna.md:269-294`）。
- 四通道完整闭集已冻结为10 strategy + 3 operation真实走到retrieval（`docs/eval/new-harvest/pre-initial-planning-qna.md:191-214`），四层测试又被冻结为不可互换、waiver只能延期不能降层（`docs/eval/new-harvest/pre-charter-qna.md:463-488`）；B/C需正式推翻已有Truth。
- 反对“owner gate不是工程bug所以可close”：阶段目标包含production closure；缺外部授权可以解释blocked，不能改变完成谓词。

#### 问题（请业主裁决）

**Q39：NHX1 production closure选择 A / B / C？若选 A，是否确认：prod profile禁stub；10+3须真实L3/L4、pinned identity与security evidence；工程可标ready-for-owner-gate，但缺真实模型/binary/S16具名签收时NHX1只能blocked、不能closed或以deferred冒充完成？**

- **业主回答**：🔒 **FROZEN：选择 A。** prod profile禁止stub；10 strategy + 3 operation必须具备真实L3/L4、pinned identity与security evidence；工程节点可标 `ready-for-owner-gate`，但缺真实模型、binary或S16具名签收时NHX1只能blocked，不能closed或以deferred冒充完成。→ `T-O-419`
- **裁决状态**：`accepted / frozen`

---

### Q40 — NHX1 是否正式 reopen “已有对象使用新 cleaner/validator”能力（来源：`CF-D14`、`T-O-401`、`O-NH-03`）

- **影响范围**：NHX1 scope；public/operator intent；workflow/actual S05；Item/Revision lineage；retention；migration；closed-set与DAG规模。
- **为什么必须确认**：它在旧campaign被明确排除并要求新owner-gate。业主现在希望吸收大量deferred，但“已有对象换实现”不是单纯补bug；它会新增产品命令和血统法。必须明确保持OOS还是本次正式reopen，不能由实现者借retry/rebuild偷渡。
- **当前建议 / 倾向（GPT）**：选 **A**，保持NHX1聚焦二轮有效债务；若业主明确需要该产品能力，可选B并接受完整扩张。

#### [对问题的详细解读]

现有 `full_task` retry语义是exact graph/policy/actual；`intake.rebuild`只应从frozen admitted clean重做下游；`index.rebuild`只重建索引。这三者都不能合法表达“用当前新cleaner重新处理旧对象”。真正upgrade需要明确选择输入（旧raw/representation还是重新acquire）、当前workflow/policy、new actual binding、生成新Revision还是替换旧Revision、serving cutover和rollback。

当前 public Task intent严格只有7项，没有upgrade入口（`src/contracts/api/models.py:319-352`）。`T-O-401` 已明确已有对象新cleaner不纳入NH v1，未来支持须新owner-gate（`docs/eval/new-harvest/pre-charter-qna.md:323-348`）；final plan也把它列为 `O-NH-03`（`docs/eval/new-harvest/final-execution-plan.md:173-180`）。本文正是可以正式reopen的owner-gate，因此需一次性裁决。

#### [可选的方案清单]

| 选项 | 方案 | 产品与工程含义 |
|------|------|----------------|
| **A（推荐）** | **保持OOS；NHX1只修exact retry/rebuild与未来新ingest** | 不新增第8 intent；把已登记的产品扩张留给独立upgrade charter。NHX1仍关闭所有二轮bug/partial/true-deferred。 |
| **B** | **本次正式reopen，新增operator-only `intake.upgrade_processing`** | 新Task/Execution读取retained raw/representation，不重访外部source；使用current active workflow/policy、unsealed new actual，产生新Revision/lineage，以ItemEpoch+publication proof切换serving；独立rollback/retention/L1–L4。NHX1 DAG与分母相应扩大。 |
| **C** | **复用现有 `:retry` 或 `intake.rebuild` 暗换cleaner** | 不改public intent，但破坏exact retry与frozen-clean rebuild；血统和actual含义失真。 |

#### [推荐方案的详细说明]

选择 A 后，NHX1完成Q30的exact replay、Q31的rev2 compat以及新ingest使用当前revision；不会让旧Item自动热切。目录可披露“upgrade unsupported”，operator不能用repair/retry绕过。

若业主选择B，本题即构成对 `T-O-401/O-NH-03` 的正式append修订：入口只能operator-only显式命令，输入必须是已保留且verified的raw/representation，禁止重新fetch；新Execution不继承old actual，按current rev/policy晚绑定；成功产生新Revision并通过ItemEpoch/publication proof切换，旧serving在成功前保持。B不是简单把一个局部任务塞进N3，而会扩张N1 schema、N2 lifecycle、N3 workflow、N4 retention、N6 control和N8 assurance。

#### [支持推荐方案的证据 / Reasoning，或反对其他方案的真相]

- public intent只有7项（`src/contracts/api/models.py:319-352`），不存在upgrade identity；C只能伪装成其它业务动作。
- full Task retry复制exact workflow/actual（`src/runtime/task/task_commands.py:293-318`），C借retry换cleaner直接违约。
- 冻结 `T-O-401` 明确区分Process/full retry、rebuild/metadata、index rebuild和future upgrade（`docs/eval/new-harvest/pre-charter-qna.md:323-348`）。
- final scope明确 `O-NH-03` 需要新owner-gate（`docs/eval/new-harvest/final-execution-plan.md:173-180`）；A保持已有边界，B则必须承认完整reopen成本。
- Q29 ItemEpoch/Q31 rev2/Q34 evidence法能为B提供必要基础，但不能替代“是否交付该产品能力”的owner决定。
- 反对C：它会让同一个API既表示exact replay又表示implementation migration，caller和审计无法判别。

#### 问题（请业主裁决）

**Q40：existing-object新cleaner能力选择 A / B / C？若选A，确认NHX1不新增upgrade intent；若选B，是否完整确认上述operator-only `intake.upgrade_processing` 法——retained verified input、零外部refetch、current rev/policy、new unsealed actual、新Revision、ItemEpoch+proof cutover、旧serving成功前保持，并接受NHX1 DAG/测试分母扩张？C是否明确禁止？**

- **业主回答**：🔒 **FROZEN：选择 A。** NHX1不新增existing-object processing upgrade intent；继续服从 `T-O-401/O-NH-03`，新cleaner/validator只影响未来新ingest。禁止借 `:retry`、`intake.rebuild` 或其它既有intent暗换cleaner；未来若支持须另开显式owner-gated upgrade charter。→ `T-O-420`
- **裁决状态**：`accepted / frozen`

---

## 6. Tombstone identity 与 dead-letter owner 法

### Q41 — deleted Item 的 external key 应永久保留、隐式重建还是显式recreate（来源：`CF-D15`、VF8/VF9/VF10）

- **影响范围**：Source/Item unique；delete/retention；新ingest admission；lineage；public errors；physical purge与未来restore能力。
- **为什么必须确认**：当前查询跳过deleted Item，但数据库unique仍占槽，导致新Task可能先201再在acceptance撞空更新。修bug可以选择早拒绝，也可以定义recreate；这是产品身份法，不应由一条SQL临时决定。
- **当前建议 / 倾向（GPT）**：选 **A**。

#### [对问题的详细解读]

delete可以删除serving和物理artifact，但不一定释放业务identity。若相同 `(team, kind, external_key)` 自动创建新Item，历史lineage和“被删除对象是否重新出现”会变得隐式；若永远保留tombstone，调用方必须使用新external key或未来显式recreate命令。

当前 Item unique覆盖所有行，不因deleted过滤（`src/persistence/migrations/001_initial.sql:944-964`）。identity resolver查询Item时排除 `deleted_at`，随后却会找到仍存在的Source（`src/runtime/intake/acquisition_ingest.py:235-255`）；acceptance `INSERT OR IGNORE` 后按新UUID blind update（`src/runtime/intake/acceptance_snapshot.py:174-195`）。lifecycle target则明确把deleted视为不可 rebuild/update（`src/services/intake_lifecycle/targets.py:158-170`）。系统没有Item restore/recreate intent（`src/contracts/api/models.py:319-352`）。

#### [可选的方案清单]

| 选项 | 方案 | 产品与工程含义 |
|------|------|----------------|
| **A（推荐）** | **tombstone永久保留external-key identity；新ingest早期409** | physical purge只清artifact/ref，不删Source/Item/transition identity。同key新Task在admission前拒绝；需要新对象时caller使用新key。 |
| **B** | **physical purge后同key可隐式创建全新Item** | 使用方便，但旧/新对象是否同一业务实体由时间/retention隐式决定，lineage与审计不稳定。 |
| **C** | **NHX1新增显式operator `intake.recreate`** | 可受控复用key，但需定义旧新Item lineage、权限、retention完成门和新的applicability/receipt/test。 |

#### [推荐方案的详细说明]

选择 A 后，delete tombstone是永久identity reservation；Q37 cleanup只释放artifact/generation/vector/object refs，不删除Source/Item/transition行。admission在创建Task前解析包括deleted在内的identity；命中deleted返回canonical 409和原tombstone safe coordinates，零新Task/Process/Observation reservation。

deactivated也不能靠ingest隐式reactivate，必须先走 `intake.reactivate`；同态命令只有exact command replay返回第一次receipt，新命令为409。若未来确有合规recreate需求，再以独立owner QNA定义C，而不根据“物理字节已删”自动开放。

#### [支持推荐方案的证据 / Reasoning，或反对其他方案的真相]

- Item unique不带 `deleted_at IS NULL` 条件（`src/persistence/migrations/001_initial.sql:944-964`），当前数据库已经倾向A的永久identity。
- resolver排除deleted Item但仍采用旧Source（`src/runtime/intake/acquisition_ingest.py:235-255`），造成应用语义和unique约束分裂；A通过admission对齐二者。
- acceptance用 `INSERT OR IGNORE` 加新UUID update（`src/runtime/intake/acceptance_snapshot.py:174-195`），解释了为什么B不能只靠“让insert成功”：必须设计partial unique或recreate lineage。
- lifecycle resolver明确拒绝deleted target（`src/services/intake_lifecycle/targets.py:158-170`），且7 intent contract没有restore/recreate（`src/contracts/api/models.py:319-352`）。A与当前产品面最一致。
- Q37 physical cleanup只应处理substrate，不应顺带改变业务identity；把key释放绑在retention完成上会让B的行为依赖后台时机。
- 反对B：同一请求在purge前409、purge后201，产品结果取决于scanner时间，无法稳定重放。

#### 问题（请业主裁决）

**Q41：deleted external key选择 A / B / C？若选 A，是否确认tombstone永久保留Source/Item identity，physical purge不释放key，同key新ingest在admission 409且零Task；deactivated需显式reactivate；未来recreate只能另开显式owner命令，不能由retention时机隐式触发？**

- **业主回答**：🔒 **FROZEN：选择 A。** deleted tombstone永久保留Source/Item external-key identity，physical purge不释放key；同key新ingest在admission返回409且零Task/Process；deactivated Item须显式reactivate；未来recreate只能另开owner-gated显式命令，不能由retention/scanner时机隐式触发。→ `T-O-421`
- **裁决状态**：`accepted / frozen`

---

### Q42 — outbox 永久 dead 时，是否必须同步终结 owning Task/Execution（来源：`CF-D16`、VF43、VF39/VF40/VF42）

- **影响范围**：outbox schema/delivery；Task/Execution terminal law；repair/requeue；supervisor/readiness；operator API；metrics/alerts与evidence。
- **为什么必须确认**：当前delivery第8次失败会变dead，只写event/metric；owner可能仍ready/queued且无error。repair scanner又会从ready状态重新造wake intent。若不冻结critical/advisory policy，dead-letter是告警还是业务终态只能靠每个kind临时猜。
- **当前建议 / 倾向（GPT）**：选 **A**。

#### [对问题的详细解读]

Outbox不是业务真相，但某些delivery是业务状态继续前进的唯一触发器。`wake_execution`、`gate_decision`、critical cutover handoff若永久dead，owner保持ready/queued会形成“看似可运行、实际永不前进”的无名态。另一方面，纯通知/advisory delivery dead不应错误杀死已完成业务。因此每个kind必须显式声明terminal policy。

当前 `_release_outbox` 在attempts≥8时把row设为dead（`src/runtime/workflow/runtime_outbox.py:411-428`）；dead处理仅追加 `outbox.dead` event和metric（`src/runtime/workflow/runtime_outbox.py:343-399`），没有owner坐标/terminalization。operator只有GET dead list（`api/internal/routes.py:133-146`）；repair会为ready Process/Execution补新wake（`src/runtime/workflow/runtime_repair.py:74-124`），但不解释已有dead predecessor。

#### [可选的方案清单]

| 选项 | 方案 | 产品与工程含义 |
|------|------|----------------|
| **A（推荐）** | **每个outbox kind登记 `critical/advisory` terminal policy** | row持久化owner kind/UUID/generation。critical变dead时同UoW将owner投影typed failed并写event/metric；advisory明确不影响owner。operator requeue/abandon用expected generation，创建新delivery并保留dead predecessor。 |
| **B** | **所有dead只告警，owner状态不变** | 状态机简单，但critical owner可永久ready/queued；恢复依赖人工SQL或不透明repair。 |
| **C** | **永不dead，无限重试** | 不需owner terminal policy，但poison message永久占队列、制造噪声/资源泄漏，也无法给caller最终结局。 |

#### [推荐方案的详细说明]

选择 A 后，ProcessCapability/OutboxKind manifest登记每种delivery的owner schema、attempt budget、criticality、dead error code和合法requeue条件。enqueue时把owner kind/UUID/generation持久化，不再靠解析payload猜owner。

critical row达到dead阈值时，在同一事务CAS dead row、检查owner仍是该generation的nonterminal状态、将Execution/Task投影为typed failure并写domain event；若owner已terminal则dead成为历史evidence，不反向改状态。advisory row只写明确 `ADVISORY_DELIVERY_DEAD`。

operator `:requeue` 不把原row改回pending，而是写新delivery generation、`retry_of_outbox_id`与CommandReceipt；原因未修或owner generation已变化时拒绝。`repair`必须识别dead predecessor，不能无条件另造看似新的wake。

#### [支持推荐方案的证据 / Reasoning，或反对其他方案的真相]

- 当前固定第8次变dead（`src/runtime/workflow/runtime_outbox.py:411-428`），已有bounded retry，C会推翻现有资源法。
- dead处理只写event/metric（`src/runtime/workflow/runtime_outbox.py:343-399`），没有Task/Execution UPDATE；B正是当前“dead但owner活着”的缺口。
- owner trace目前还要从payload反查Execution/Task（`src/runtime/workflow/runtime_outbox.py:359-377`），说明schema没有稳定owner coordinate；A把它前置持久化。
- operator surface只有dead GET（`api/internal/routes.py:133-146`），没有requeue/abandon；B意味着只能靠DB操作恢复。
- repair为ready Process/Execution补wake（`src/runtime/workflow/runtime_repair.py:74-124`），不检查dead predecessor；若不冻结policy，会反复生成delivery而不结束poison owner。
- 反对“一律critical”：有些outbox只是advisory/可重建signal；A按manifest分类，既不漏杀也不误杀。

#### 问题（请业主裁决）

**Q42：outbox dead选择 A / B / C？若选 A，是否确认：每个kind必须登记critical/advisory、owner坐标、attempt budget和dead code；critical dead与owner typed failure同UoW且generation-fenced；advisory明确不终结owner；requeue创建新delivery并保留dead predecessor，repair不得绕过dead历史？**

- **业主回答**：🔒 **FROZEN：选择 A。** 每个outbox kind必须登记critical/advisory、owner坐标、attempt budget与dead code；critical dead与owner typed failure同UoW且generation-fenced，advisory明确不终结owner；requeue创建新delivery并保留dead predecessor，repair不得绕过dead历史。→ `T-O-422`
- **裁决状态**：`accepted / frozen`

---

## 7. ★ Truth-Gate 台账（冻结产物 · owner-gated truth · 供 NHX1 CITE）`[核心]`

> **冻结完成。** 业主已逐题接受 Q28–Q42 推荐 A 的全部确认句；下表 `T-O-408..422` 是下游唯一 owner-gated 口径。详细边界仍以来源 Q 的冻结回答为准，planning/action-plan不得缩写掉其硬条件。

| Truth-ID | 子类型 | 来源 Q | 决策主题 | 状态 | 冻结后真相内容（一句话下游唯一口径） |
|----------|--------|--------|----------|------|--------------------------------------|
| `T-O-408` | execution/identity | Q28 | Source / Observation 分账 | `frozen` | SourceIdentity与ObservationReservation分账；v2显式observation key且与Task/root同UoW，accepted仅exact replay、failed仅typed retry，v1按冻结兼容法过渡。 |
| `T-O-409` | execution/concurrency | Q29 | ItemEpoch / CAS owner | `frozen` | 现row_revision即唯一ItemEpoch；latest/serving/lifecycle等canonical mutation及所有callback必须expected-epoch CAS，禁止静默覆盖。 |
| `T-O-410` | execution/replay | Q30 | full retry / external acquire | `frozen` | durable acquire后所有retry零外部调用，full Task retry exact复制graph/policy/actual/formula/context并从frozen artifact恢复；无frozen input则拒绝并新建Observation。 |
| `T-O-411` | execution/compat | Q31 | workflow revision / compat | `frozen` | 保存rev1 exact fixture，NHX1修复图升rev2且新Task只选rev2；old pin exact共存，canonical/capability/formula变化必升版，满足zero-use+retention后才retire。 |
| `T-O-412` | execution/binding | Q32 | ProcessingBinding taxonomy | `frozen` | actual v2使用clean_strategy与registered_api_operation typed union，各引自身versioned registry/digest，共享seal/replay并保持10+3分账。 |
| `T-O-413` | execution/object | Q33 | ObjectUploadSession | `frozen` | handle只代表bytes，session token拥有exact upload/pending；idempotency、cancel、TTL、reserve、consume均session-CAS，catalog+pending+committed后才返回usable handle。 |
| `T-O-414` | execution/evidence | Q34 | legacy evidence correction | `frozen` | legacy evidence禁原地改写；追加verification verdict及versioned correction/supersedes，不可重算即legacy_unverifiable；新publication/retry只消费verified同formula evidence。 |
| `T-O-415` | execution/contract | Q35 | public/operator read-control split | `frozen` | public authenticated面提供安全catalog与业务view但仍禁caller选workflow；Process/Fact/debug/control仅operator面并受redaction、expected fence、audit约束。 |
| `T-O-416` | execution/deployment | Q36 | deployment roles / readiness | `frozen` | 同binary提供api/workflow_worker/maintenance/all显式role；各role只启动所属loop、注册capability并计算独立readiness，拆实例不改contract。 |
| `T-O-417` | execution/retention | Q37 | delete physical convergence | `frozen` | delete先logical fence；NHX1必须以retention cleanup job、三substrate executor、exact ref release、GC proof与operator状态完成物理收敛，禁止无executor永久open。 |
| `T-O-418` | execution/error-contract | Q38 | canonical error registry | `frozen` | v2 error统一UPPER_SNAKE registry并冻结status/category/retryable/message；v1/旧persisted code仅alias兼容、不改历史，新代码禁未注册kebab-case。 |
| `T-O-419` | execution/completeness | Q39 | production supply closure gate | `frozen` | prod禁stub且10+3须真实L3/L4、pinned identity与security evidence；缺真实模型/binary/S16签收时NHX1只能blocked，不能closed/deferred-complete。 |
| `T-O-420` | execution/scope | Q40 | existing-object processing upgrade | `frozen` | NHX1不支持existing-object新cleaner/validator upgrade，禁止借retry/rebuild暗换；新实现只影响未来ingest，未来能力须独立owner-gated charter。 |
| `T-O-421` | execution/identity | Q41 | deleted external-key identity | `frozen` | deleted tombstone永久保留Source/Item external-key identity，physical purge不释放key；同key新ingest admission 409零Task，未来recreate须显式owner命令。 |
| `T-O-422` | execution/recovery | Q42 | outbox dead owner policy | `frozen` | 每个outbox kind登记critical/advisory及owner/budget/dead code；critical dead同UoW generation-fenced终结owner，advisory不终结，requeue保留dead predecessor且repair不得绕过。 |

---

## 8. 使用约束与冻结记录

### 8.1 冻结后使用纪律

1. design/planning/action-plan/closure只引用 `Q28..Q42 + T-O-408..422`；不得在下游重抄一个删减硬条件的“简化答案”。
2. `T-O-408..422` 与原 `T-O-376..407` 同属append-only owner truth；本文不修改既有Q1–Q27答案。
3. Q40已选择A，因此 `T-O-401/O-NH-03` 保持有效；NHX1不得以“全部deferred都吸收”为由偷渡existing-object upgrade。
4. Q39已选择A；外部模型/binary/S16尚未具名签收时，下游只能把NHX1标为blocked，不得重分类为closed-with-deferred。
5. 原设计中的9个AP包装应在下游修订为一个NHX1阶段内的串行节点；这是QNA冻结后的planning handoff，不冒充本文件已经完成的action-plan工作。
6. 未来推翻任一答案只能在本文追加修订记录并分配新Truth，不得静默改旧回答或复用旧Truth-ID。

### 8.2 本次 owner batch answer

```text
业主同意 Q28–Q42 的全部推荐方案；逐题选择 A，接受每题全部确认句；无补充改写。
```

该批量答复已规范化写入每题 `业主回答`，并压缩为 §7 的15条Truth。逐题答案负责完整语义，Truth表负责下游引用；二者冲突时以逐题冻结回答为完整边界，Truth不得作扩张解释。

---

## 9. ★ 冻结完成核对与冲突审查

| 核对项 | 结果 | 说明 |
|--------|------|------|
| Q28–Q42 题数 / 答案 | ✅ `15/15` | 全部选择A并接受全部确认句；零OPEN question |
| Truth-Gate | ✅ `15/15` | `T-O-408..422` 已注入并标frozen；无ID碰撞 |
| second-opinion | ✅ `retired` | 按业主要求全文无second-opinion槽位，不阻塞冻结 |
| `T-O-401` retry/upgrade | ✅ 无冲突 | T-O-410细化exact replay；T-O-420选择A继续排除existing-object upgrade |
| `T-O-381` 10+3 | ✅ 无冲突 | T-O-412保持10 strategy + 3 operation分账；T-O-419强化真实closure |
| `T-O-379` caller选图禁令 | ✅ 无冲突 | T-O-415开放read-only discovery，但Task create仍禁workflow key |
| `T-O-399/406` security/test | ✅ 无冲突 | T-O-419保留真实supply、S16与L1–L4硬闸，不允许waiver降层 |
| `T-O-404` upload UoW | ✅ 收紧 | T-O-413在catalog+pending基础上增加exact session owner，不放宽usable条件 |
| `T-O-405` admission fail-loud | ✅ 收紧 | T-O-408/409/421把Observation、ItemEpoch、deleted key统一收至admission/CAS |
| 下游NHX1 design/action-plan | ➡️ handoff | 须据Truth把原9 AP包装重排为单一NHX1串行节点；尚未在本QNA中冒充完成 |

**冻结 verdict**：QNA 的问题、答案和Truth-Gate已完整关闭，文档状态为 `frozen`。NHX1 planning/action-plan可开始消费这些Truth，但在design recut与单一串行DAG落盘前不得进入代码实现。

---

## 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| `v0.1` | `2026-08-31` | `GPT` | 续接Q1–Q27，一次性提出Q28–Q42；每题含四元组、A/B/C、HEAD file:line证据；second-opinion retired；预留T-O-408..422 |
| `v1.0` | `2026-08-31` | `GPT / owner` | Owner整包接受Q28–Q42推荐A；逐题写入FROZEN答案；注入T-O-408..422；完成与T-O-376..407冲突审查并冻结QNA |
