# S04 — Intake Asset Lifecycle

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 子系统**：`D3 摄入资产 / S04 Intake Asset Lifecycle`
>
> **日期**：`2026-07-15`
>
> **作者 / 裁决者**：`MKB owner + Codex`
>
> **文档性质**：`domain truth / formal subsystem specification`
>
> **文档状态**：`accepted`（S04 域内已接受；全系统 truth layer 尚未 frozen）
>
> **Truth 版本**：`S04-v1.0`
>
> **上游权威输入**：形成QNA时的`D01-v1.1/S01-v1.2/S02-v1.0/S03-v1.0`，冻结的`qna-truth/S04.md v1.1`（Q1–Q9 / `T-O-30..48`）；发布后对齐版本为`D01-v1.2/S01-v1.3/S02-v1.1/S03-v1.1`
>
> **词汇权威**：`docs/baseline/spec-glossary.md`
>
> **事实证据**：`legacy-family/` 仅作为 production-pitfall / behavior-archeology / design-counterexample `ReferenceAnchor`，另有 W3C PROV、CloudEvents、RFC 9530/9110、Apache Iceberg 与 S3 Versioning 一手资料
>
> **下游消费者**：`S05-S10`、`S12-S16`、跨系统拓扑 `17`、验收冻结 `18`

> **Owner-originated 约束**：`IntakeSource`、`IntakeSnapshot`、`IntakeItem`、`IntakeRevision`、`IntakeArtifact` 是 S04 的五类 canonical identity。`Intake` 只表示外部输入的获取、接受和长期治理，不提前宣称其已经成为 `Knowledge`。

> **应用边界**：MKB 是完全独立的 greenfield application。`legacy-family` 不构成代码、数据、协议、schema、UUID/status、storage、bootstrap、运行或验收兼容关系，只允许作为 ReferenceAnchor。

> **跨文档审计声明**：S04已与D01/S01-S03的Task/Execution/Process、single/scatter、retry/rebuild、proof、cancel、Workflow routing和cleanup边界完成逻辑对账。D01-v1.2/S01-v1.3/S02-v1.1/S03-v1.1已完成Intake vocabulary校准，不改变三层runtime identity。

---

## 1. Domain 介绍

### 1.1 Domain 价值

S04 是 MKB 摄入资产的 durable truth layer。它把“外部来源、本次被接受的观察、观察中的稳定业务项、业务项的不可变语义修订、承载观察或修订的表示”拆成五类正交身份，并控制哪个修订可以进入下游服务面。

S04 解决七个核心问题：

1. upload、URL、single API 与 scatter API 不再被歧义的 `file/document` 身份压扁；
2. 来源观察集合与稳定业务项历史分别建模，不再由 mutable parent/child row 同时承担；
3. 同一业务项的 canonical semantic change 追加 Revision，而 rebuild/model/index generation 不污染业务修订；
4. latest candidate 与 serving revision 分离，失败候选不会覆盖健康服务版本；
5. single/scatter 共用一套 Snapshot/Membership truth，large scatter 仍只有一个 acceptance 线性化点；
6. deactivate/delete、rebuild/reindex 与 physical purge 分账，并以 retention/reference/cleanup proof 防止误删；
7. 空数据库可以确定性 bootstrap、演进和验收，且整个生命周期不依赖 legacy-family。

### 1.2 在整体拓扑中的位置

```text
S01/S02 Task Contract
  │ intake.* intent / stable Intake target
  ▼
S03 Workflow Engine
  │ ProcessCommand / ProcessOutcome / PublicationProof
  ▼
S05 source adapters + validation + canonicalization
  │ validated IntakeCandidateSet
  ▼
S04 Intake Asset Lifecycle
  ├── five canonical identities
  ├── IntakeSnapshotMembership collection truth
  ├── SemanticDefinition / RevisionSemantic
  ├── ActionDefinition / IntakeItemTransition
  ├── atomic acceptance + typed IntakeChangeSet
  ├── serving/lifecycle CAS
  ├── bounded recovery + cleanup proof contract
  └── deterministic bootstrap/readiness
         │
         ├── typed route facts → S03
         ├── exact Revision lineage → S06-S09
         ├── retrieval eligibility fence → S09-S10
         ├── transaction/outbox/policy persistence → S12
         ├── bytes/locator/orphan/GC → S13
         └── evidence/metric/alert/hold → S15-S16
```

### 1.3 Canonical identity graph

```text
Team
  └─ IntakeSource
       ├─ IntakeSnapshot (0..N, immutable accepted observations)
       │    ├─ IntakeArtifact (0..N, snapshot-owned)
       │    └─ IntakeSnapshotMembership (0..N)
       │          ├─ IntakeItem
       │          └─ observed IntakeRevision / no-change / absence decision
       └─ IntakeItem (0..N, stable source-scoped subjects)
            ├─ IntakeRevision (1..N, immutable semantic states)
            │    ├─ RevisionSemantic (1..N)
            │    └─ IntakeArtifact (0..N, revision-owned)
            ├─ latest_revision_uuid
            └─ serving_revision_uuid (nullable, proof-gated)

IntakeRevision
  ├─ LSRagBlock / ConstructionUnit       [S06-S07]
  ├─ VectorRecord / IndexGeneration      [S08-S09]
  └─ future promotion/fusion             [future Knowledge domain]
```

`Snapshot → Membership` 回答“某次 accepted observation 看见了什么”；`Item → Revision` 回答“一个稳定业务项如何随时间变化”。Execution tree 只描述一次运行，不能替代任一资产关系。

### 1.4 Scope fence

S04 负责：

- 五类 Intake identity、ownership、cardinality、team fence 和 canonical UUID；
- source-scoped `ExternalKey` resolution；
- accepted Snapshot、completeness、authoritative scope、validator 与 immutable membership；
- immutable Revision、predecessor、fingerprint、semantic definition binding 与 provenance；
- Snapshot/Revision-owned IntakeArtifact identity、digest、logical locator 和 retention fence；
- latest/serving pointer、Item 三态 lifecycle、CoreEffect、ActionDefinition 和 transition audit；
- IntakeCandidateSet acceptance、IntakeChangeSet、child scheduling intent 的事务线性化要求；
- large-scatter staging/seal/capacity fence 与受限 deterministic recovery；
- deactivate/delete/rebuild-reindex/physical-purge 分账和 cleanup proof requirements；
- schema/registry bootstrap、MKB schema evolution、readiness 与 S04 acceptance gate。

S04 不负责：

| 排除项 | 权威归属 | S04 边界 |
|---|---|---|
| Task HTTP、六态、cancel/full retry/atomic rebuild admission | `S01-S02` | 提供稳定 Intake target、resource result与长期状态引用 |
| Workflow graph、Execution/Process states、claim/retry/recovery | `S03` | 输出 typed facts/effects/ref；不选择或执行 Process route |
| fetch/upload/parse/clean、connector kind、canonicalization算法 | `S05` | 定义 IntakeCandidateSet 接收 contract 与 accepted truth |
| Block/ConstructionUnit/Embedding/Vector exact schema与算法 | `S06-S09` | 要求全部派生对象引用 exact IntakeRevision |
| retrieval/rerank算法 | `S10` | 提供 team + lifecycle + serving revision eligibility fence |
| Turso exact SQL type/index/trigger、queue/outbox driver | `S12` | 冻结 logical tables、约束和事务语义 |
| IntakeArtifact bytes、backend、atomic write、physical path与GC实现 | `S13` | 持有IntakeArtifact logical identity/owner/digest/locator |
| retention具体天数、event/metric/alert/runbook | `S14-S15` | 冻结 policy/reference/proof 输入及必须留存的 evidence |
| secret、hold授权、跨 team permission | `S16` | 只保存 secret/policy logical ref，禁止明文 |
| Knowledge promotion/fusion/curation | future domain | 保留命名空间和 Intake provenance，不预建表 |

### 1.5 Domain 完成定义

实现层必须同时满足：

1. §2 全部 Truth ID 可映射到 schema、service、contract 与 test；
2. 十张 canonical truth tables 及 §3.3 supporting ledgers 的 PK/FK/unique/CHECK/CAS/payload_extra 约束落地；
3. single/scatter、complete/partial/authoritative absence、Revision no-op/change、serving proof 与 lifecycle matrix 通过 golden tests；
4. large-scatter page/seal/acceptance、crash windows、outbox replay、orphan/repair 通过故障注入；
5. deactivate/delete/reindex/purge 与 retention/reference/cleanup proofs 无状态混义；
6. 空库 bootstrap 第一次成功、第二次 no-op，schema/registry drift fail readiness；
7. dependency/config/DDL/API/event/startup scan 证明零 legacy runtime dependency；
8. §6 强制验收矩阵全部通过。

---

## 2. 真相层

### 2.1 真相层纪律

本节是 S04 的 SSOT。来源分为：

- `OWNER-QNA`：冻结的 S04 Q1–Q9 / `T-O-30..48`；
- `UPSTREAM`：D01/S01-S03 已接受的 runtime truth；
- `REFERENCE-ANCHOR`：legacy-family 或外部一手资料证明的行为、失败窗口和设计分母；
- `ACCEPTED-VERDICT`：不改变 owner 决策、为落地提供的正式精化。

ReferenceAnchor 无权定义 MKB runtime/schema/API/acceptance；若证据叙事与 `T-O-30..48` 冲突，以 owner truth 为准。

### 2.2 Identity 与 collection 真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S04-T001` | IntakeSource、IntakeSnapshot、IntakeItem、IntakeRevision、IntakeArtifact是五类正交canonical identity，各有完整UUID。 | `T-O-30` | 禁止generic file/document row或UUID复用。 |
| `S04-T002` | IntakeSource 是 team-scoped 外部输入绑定，也是 ExternalKey namespace；secret 只保存 logical ref。 | `T-O-30/T-O-32` | 裸 provider key、URL/path/digest 不构成全局身份。 |
| `S04-T003` | IntakeSnapshot只表示已经acceptance的immutable observation；fetch/parse/auth failure只属于runtime/evidence。 | `T-O-30/T-O-31` | 禁止“failed IntakeSnapshot”或mutable current collection row。 |
| `S04-T004` | IntakeItem 是 `(team_uuid, intake_source_uuid, normalized_external_key)` 下稳定解析的业务项。 | `T-O-30/T-O-32` | replay/rescan 不得无条件生成新 Item；deleted key 不静默复用。 |
| `S04-T005` | IntakeRevision 是 Item 的 immutable semantic state；每个 Revision 只有一个 predecessor和递增 ordinal。 | `T-O-30/T-O-32` | canonical semantic change append；原位覆盖禁止。 |
| `S04-T006` | IntakeArtifact 是 Snapshot 或 Revision 的 immutable representation，direct owner 必须 XOR；Block/Vector/Process log 不是 IntakeArtifact。 | `T-O-30/T-O-36` | S13 locator不成为 identity；Artifact不能成为万能产物父类。 |
| `S04-T007` | IntakeSnapshotMembership 是 accepted collection SSOT，记录 seen/new-revision/no-change/absence decision。 | `T-O-31/T-O-36` | TaskItem、Execution count或relation JSON不得替代。 |
| `S04-T008` | single通常产生一个membership；scatter产生0..N memberships。scatter parent是IntakeSource+IntakeSnapshot上下文，不伪造parent IntakeItem。 | `T-O-31` | 一个Task；root controller + 0..N child Executions。 |
| `S04-T009` | future KnowledgeItem必须拥有独立promotion/fusion identity和provenance；当前不得作为IntakeItem别名。 | `T-O-31` | v1不建Knowledge表/API。 |

### 2.3 Revision 与 semantic extensibility 真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S04-T010` | 只有 canonical business semantics 变化才追加 IntakeRevision；no-change、rebuild、Workflow/model/embed/index升级不创建 Revision。 | `T-O-32` | business revision 与 runtime/build/index generation 分账。 |
| `S04-T011` | 内建最小 semantic dimensions 为 source representation、canonical content、context metadata、filter metadata。 | `T-O-33/T-O-47` | exact digest算法/canonicalizer由S05版本化。 |
| `S04-T012` | SemanticDefinition 以 `(semantic_key, definition_version)` 内部注册、immutable；声明value/schema kind、fingerprint participation与typed route signal。 | `T-O-33/T-O-36` | 无外部CRUD；追加维度不改历史定义。 |
| `S04-T013` | RevisionSemantic 绑定 exact definition version；RevisionFingerprint由参与fingerprint的有序definition/value tuples确定性计算。 | `T-O-33/T-O-36/T-O-38` | 读取历史不得join当前最新版后重解释。 |
| `S04-T014` | `payload_extra` 默认不参与identity、observation fence、fingerprint、diff、route、proof或filter。 | `T-O-37/T-O-39` | 进入关键语义前必须晋升正式列或versioned definition。 |

### 2.4 Serving、lifecycle 与 transition 真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S04-T015` | Item分别维护CAS保护的latest与nullable serving Revision pointer。 | `T-O-34` | latest不自动等于serving。 |
| `S04-T016` | 只有type-specific PublicationProof通过且expected state/pointer一致时，才能CAS切换serving；失败候选不污染旧serving。 | `T-O-34/T-O-41` | queue ACK、日志、单vector ACK无发布权。 |
| `S04-T017` | Item core lifecycle只有`active/deactivated/deleted`；deactivated/deleted的serving必须为null。 | `T-O-40` | Snapshot/Revision不复制runtime或lifecycle state。 |
| `S04-T018` | CoreEffect集合固定为`ACCEPT_LATEST/SET_SERVING/CLEAR_SERVING/SET_ACTIVE/SET_DEACTIVATED/SET_DELETED/NO_CHANGE`。 | `T-O-40` | 新ActionDefinition只能组合受允许effect，不能任意写列。 |
| `S04-T019` | ActionDefinition内部注册、immutable versioned；声明from-state、precondition/proof policy、CoreEffect、route fact与idempotency scope。 | `T-O-35/T-O-40` | 外部caller不得自造action key。 |
| `S04-T020` | Item mutation必须同事务完成team/state/pointer/proof/action校验、Item CAS、append transition ledger和outbox。 | `T-O-41` | queue只wake-up；running Execution不热切definition/workflow。 |
| `S04-T021` | deactivate可逆且先clear serving；reactivate只恢复active，不自动恢复旧serving；delete写durable tombstone且普通路径终止。 | `T-O-35/T-O-40/T-O-45` | Task cancel不撤销serving；v1不提供deleted restore。 |
| `S04-T022` | 只有complete + authoritative Snapshot可在声明scope内依据absence policy产生absence_deactivate。 | `T-O-35/T-O-38` | partial/timeout/provider error/parser skip/非权威空集不得全量下架。 |
| `S04-T023` | retrieval使用双围栏：关系层校验team/lifecycle/exact serving revision，index/filter层携带team/item/revision/generation。 | `T-O-34/T-O-35` | 任一tombstone或pointer mismatch都拒绝返回。 |

### 2.5 Acceptance、routing 与 recovery 真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S04-T024` | S05先在事务外生成validated IntakeCandidateSet；失败候选不形成IntakeSnapshot。 | `T-O-38` | network/parser/IntakeArtifact I/O不得占用canonical transaction。 |
| `S04-T025` | acceptance transaction原子提交IntakeSnapshot、IntakeItem/IntakeRevision decision、IntakeSnapshotMembership、IntakeChangeSet与child scheduling intent；任一失败全部回滚。 | `T-O-38` | acceptance是唯一collection线性化点。 |
| `S04-T026` | `(team, source, observation identity/fingerprint)` + candidate root digest构成幂等fence；同identity异digest冲突。 | `T-O-38/T-O-43` | 不产生平行accepted observations。 |
| `S04-T027` | S04只输出绑定definition versions的typed IntakeChangeSet；S03绑定的WorkflowRevision决定Process route。 | `T-O-39` | 禁止S04硬编码full/context Process名。 |
| `S04-T028` | Large-scatter先paged staging，全部page/root digest、count、dedupe、IntakeArtifact refs、scope/completeness校验后seal。 | `T-O-43` | sealed pages immutable；unsealed不可accept。 |
| `S04-T029` | 显式`max_members_per_snapshot/max_candidate_bytes/transaction_budget`；超限在Snapshot创建前fail-loud。 | `T-O-43` | v1不静默拆分authoritative Snapshot。 |
| `S04-T030` | recovery只依据durable candidate/snapshot/outbox/fence/ledger执行幂等补齐、重放、隔离或cleanup。 | `T-O-44` | 日志/queue/payload_extra无合成truth权限。 |
| `S04-T031` | missing IntakeArtifact fail-closed并产生repair intent；DB rollback后的orphan IntakeArtifact按owner/digest/grace清理。 | `T-O-44` | 禁止virtual IntakeArtifact伪造成功。 |
| `S04-T032` | Reconciler只修projection/wakeup/intent，不创建从未提交的Snapshot/Revision/proof；repair保存causation/fence/audit。 | `T-O-44` | 不建设第二套业务状态机。 |

### 2.6 Retention、reindex 与 purge 真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S04-T033` | `deactivate/delete/rebuild-reindex/physical_purge`是四类互不替代的MKB intent。 | `T-O-45` | purge不reset Task，reindex不改变Item lifecycle。 |
| `S04-T034` | rebuild/reindex不创建IntakeRevision；新derived/index generation build→validate→CAS switch→grace→purge old。 | `T-O-45/T-O-46` | build失败继续服务旧generation。 |
| `S04-T035` | retention fence至少保护latest/serving、rollback grace、active runtime/restart lineage、hold、cleanup intent和派生引用。 | `T-O-46` | eligibility由正式policy/reference决定，不读payload_extra。 |
| `S04-T036` | IntakeSnapshot/IntakeSnapshotMembership、noncurrent IntakeRevision、IntakeArtifact、Block、Vector可使用不同retention class。 | `T-O-46` | 具体时长归S12-S15配置，资格语义不可变。 |
| `S04-T037` | 每个relationship/vector/artifact/derived substrate拥有独立cleanup intent/proof；全部required proofs完成才声明physical purge complete。 | `T-O-46` | partial failure继续retry，不反向恢复serving。 |
| `S04-T038` | IntakeSource/IntakeItem tombstone与IntakeItemTransition保留最小identity、causation、digest、purge proof skeleton。 | `T-O-45/T-O-46` | v1无ordinary restore、break-glass resurrection或tombstone hard delete。 |

### 2.7 Greenfield governance 真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S04-T039` | MKB唯一初始数据面是空数据库；bootstrap不读取legacy-family，也无importer/dual-read/compatibility/cutover。 | `T-O-42/T-O-47` | legacy只能出现在ReferenceAnchor文档。 |
| `S04-T040` | schema bootstrap与registry seed版本化、确定性、幂等；同版本同digest no-op，同版本异digest fail-loud。 | `T-O-47` | 已注册definition version不可原位修改。 |
| `S04-T041` | 内容只可在readiness后经正常Task/Intake Contract进入；生产seed/SQL/fixture不得伪造serving truth。 | `T-O-47` | test factory也必须满足相同domain invariants。 |
| `S04-T042` | MKB schema evolution forward-only、版本化、可审计；backfill不得重解释历史definition binding。 | `T-O-48` | schema bookkeeping继承payload_extra例外。 |
| `S04-T043` | 启动只读验证schema/registry/workflow refs/约束/未完成migration；漂移拒绝readiness，不猜测修复业务truth。 | `T-O-48` | readiness不是自动migration成功的假设。 |
| `S04-T044` | acceptance覆盖fresh install至零legacy dependency的完整矩阵。 | `T-O-48` | 测试断言MKB Contract，不复刻legacy wire/schema/status。 |

### 2.8 Universal `payload_extra` 真相

| 规则面 | 强制约束 |
|---|---|
| Presence | 所有MKB-owned canonical、runtime、registry、projection、staging、outbox、audit、repair与业务migration表必须存在非空默认`{}`的`payload_extra`。 |
| Exclusions | schema migration bookkeeping、Turso/SQLite内部表、virtual vector、FTS shadow与第三方私表不强改。 |
| Forbidden truth | identity、FK/relation、required state、CAS/fencing、proof、auth、idempotency、route/filter、public contract、secret、正文和bytes。 |
| Immutable host | 随Snapshot/Revision/Membership/definition/transition/audit宿主行不可变，修正必须追加新truth。 |
| Mutable host | 只能随宿主正常CAS+audit transaction更新，无独立patch后门。 |
| Promotion | key一旦必填、可查询、可路由、可授权或影响状态，必须晋升正式列或versioned definition并迁移。 |

---

## 3. Relational schema 与数据不变量

### 3.1 Schema 总则

下述是 logical schema contract；S12可选择Turso/SQLite exact type、index、partial index、trigger和repository布局，但不得改变职责、identity、immutability或事务边界。

所有team-owned表以`team_uuid`参与PK/FK/unique/query fence。MKB内生UUID使用UUIDv7。所有digest必须同时携带algorithm/canonicalization/schema version或引用对应definition version。

### 3.2 十张 canonical truth tables

| 表 | 必需列族 | 主约束 / 不变量 |
|---|---|---|
| `intake_sources` | `team_uuid, intake_source_uuid, source_kind, source_descriptor_ref, connector_config_ref, secret_ref, accepts_new_snapshots, row_revision, created_at, payload_extra` | PK/team fence；secret不得明文；descriptor/config使用logical ref；source admission mutation需CAS+audit。 |
| `intake_snapshots` | `team_uuid, intake_snapshot_uuid, intake_source_uuid, observation_key, observation_fingerprint, candidate_root_digest, completeness, authoritative_scope_ref, validator_kind/value, observed_at, accepted_at, producer_execution_uuid, raw_artifact_uuid?, payload_extra` | immutable；source内observation fence唯一；`completeness∈{complete,partial}`；failure不是row。 |
| `intake_items` | `team_uuid, intake_item_uuid, intake_source_uuid, normalized_external_key, lifecycle_state, latest_revision_uuid?, serving_revision_uuid?, row_revision, created_at, deactivated_at?, deleted_at?, payload_extra` | `(team,source,normalized_external_key)`唯一；三态CHECK；deactivated/deleted时serving null；pointer必须同team/item。 |
| `intake_revisions` | `team_uuid, intake_revision_uuid, intake_item_uuid, revision_ordinal, predecessor_revision_uuid?, revision_fingerprint, creation_action_key/version, source_snapshot_uuid, created_at, payload_extra` | immutable；`(team,item,ordinal)`与`(team,item,fingerprint)`唯一；predecessor同item且ordinal连续。 |
| `intake_artifacts` | `team_uuid, intake_artifact_uuid, owner_snapshot_uuid?, owner_revision_uuid?, artifact_role, media_type, digest_algorithm, content_digest, size_bytes, logical_locator, producer_execution/process refs?, retention_class_ref, created_at, payload_extra` | owner XOR；immutable；`logical_locator`非绝对路径；digest/size必填。 |
| `intake_snapshot_memberships` | `team_uuid, intake_snapshot_uuid, member_ordinal, normalized_external_key, intake_item_uuid?, observed_revision_uuid?, decision_kind, required, decision_digest, created_at, payload_extra` | immutable；snapshot内key/ordinal唯一；decision与nullable refs组合CHECK；absence仅complete-authoritative。 |
| `intake_semantic_definitions` | `semantic_key, definition_version, value_kind, schema_ref/version, fingerprint_participation, route_fact_key?, canonicalizer_ref/version, definition_digest, registered_at, payload_extra` | internal immutable registry；key+version唯一；同version异digest拒绝。 |
| `intake_revision_semantics` | `team_uuid, intake_revision_uuid, semantic_key, definition_version, value_digest, scalar_kind/value columns?, value_artifact_uuid?, created_at, payload_extra` | immutable；revision+semantic key唯一；exact definition FK；typed scalar或artifact ref按kind约束。 |
| `intake_action_definitions` | `action_key, definition_version, allowed_from_mask, required_proof_kind?, precondition_class, core_effect_mask, route_fact_key, idempotency_scope, definition_digest, registered_at, payload_extra` | internal immutable registry；effect仅来自封闭集合；同version异digest拒绝。 |
| `intake_item_transitions` | `team_uuid, transition_uuid, intake_item_uuid, action_key/version, before/after lifecycle, before/after latest, before/after serving, item_revision_before/after, causation_task/execution/process refs, proof_ref/digest?, policy_ref/version?, transition_fence, occurred_at, payload_extra` | append-only；与Item CAS同事务；before/after必须匹配ActionDefinition和CoreEffect。 |

`intake_sources.accepts_new_snapshots` 只是IntakeSource admission fence，不是第二套复杂lifecycle；需要更丰富的IntakeSource治理时必须在S05/S16显式reopen，而不能借`payload_extra`加隐藏状态。

### 3.3 Supporting durable ledgers

这些表服务于acceptance、delivery、repair与cleanup，不是新的Intake asset identity，也不创建第二套Execution/Process状态机：

| 逻辑职责 | 推荐表 | 必需语义 |
|---|---|---|
| IntakeCandidateSet head | `intake_candidate_sets` | candidate UUID、team/source、producer Execution fence、definition-set digest、observation identity、expected pages/members/bytes、root digest、staging state、seal/expiry、payload_extra |
| Candidate pages | `intake_candidate_pages` | candidate UUID、page ordinal、member count、page digest、IntakeArtifact/value refs、immutable sealed payload reference、payload_extra |
| IntakeChangeSet / facts | `intake_change_sets` + physical fact rows/view | snapshot/ref/digest、typed item/revision/semantic/absence facts、definition bindings；不得存Process名 |
| Scheduling outbox | `intake_scheduling_outbox` | causation、WorkflowRevision、Snapshot/Item/Revision refs、IntakeChangeSet digest、idempotency fence、delivery projection、payload_extra |
| Repair intent | `intake_repair_intents` | invariant kind、target refs、observed fence、allowed repair kind、causation、resolved evidence、payload_extra；runtime retry归S03 |
| Cleanup intent | `intake_cleanup_intents` | target/retention policy、required substrate set/digest、hold/reference snapshot、requested causation、completion projection、payload_extra |
| Cleanup proof | `intake_cleanup_proofs` | cleanup intent、substrate kind、target ref/digest、proof kind/digest、producer Execution/Process、verified_at、payload_extra |

物理实现可以为IntakeChangeSet facts或candidate page entries拆分子表；S12必须证明其仍是typed、normalized、可索引且不以opaque JSON承载核心判断。

### 3.4 Registry bootstrap minimum

首版registry manifest至少确定性注册：

| Registry | Required definitions |
|---|---|
| Semantic | `source_representation`、`canonical_content`、`context_metadata`、`filter_metadata` |
| Action | `accept_revision`、`publish_revision`、`deactivate`、`reactivate`、`delete`、`absence_deactivate` |

每项包含key/version/schema或value kind、effect/fingerprint/route语义和definition digest，并验证其引用的S03 WorkflowRevision/guard存在且digest匹配。

### 3.5 状态与约束矩阵

#### Item lifecycle

| Action | From | To | Pointer effect | 必要围栏 |
|---|---|---|---|---|
| accept revision | active/deactivated | 不变 | latest→candidate | expected latest + fingerprint |
| publish/replace | active | active | serving→proof target | expected serving + proof + policy |
| deactivate | active | deactivated | serving→null | expected state/pointer + causation |
| reactivate | deactivated | active | serving保持null | expected state + policy |
| delete | active/deactivated | deleted | serving→null + tombstone | expected state + causation |
| no-change | active/deactivated | 不变 | pointers不变 | Snapshot/member idempotency |

#### IntakeCandidateSet staging

```text
open ──all pages + validation──> sealed ──canonical transaction──> accepted
  └──────── timeout/invalid/size fence ─────────────────────────> abandoned

sealed + retry → same acceptance transaction
accepted + retry → return same IntakeSnapshot
abandoned → never creates IntakeSnapshot
```

staging state不替代Process status；它只表示候选集合是否具备进入canonical transaction的资格。

---

## 4. 业务流转与接口 Contract

### 4.1 Single intake

```text
Task(intake.ingest)
  → root Execution targets IntakeSource binding/new-source intent
  → S05 fetch/upload/clean produces one-member IntakeCandidateSet
  → seal + acceptance transaction
       create accepted IntakeSnapshot
       resolve/create stable IntakeItem
       append or reuse IntakeRevision
       append IntakeSnapshotMembership + IntakeChangeSet + outbox
  → S03 evaluates typed facts
  → build/validate derived assets
  → PublicationProof
  → Item CAS sets serving revision
  → Task aggregate succeeds from root proof
```

一次性upload也拥有IntakeSource，以统一team fence、provenance和replay；它不必具备可重复fetch能力。

### 4.2 Scatter intake

```text
one Task(intake.ingest)
  → root controller Execution targets IntakeSource
  → S05 paged IntakeCandidateSet(0..N)
  → all pages verified + sealed
  → one canonical acceptance transaction
       Snapshot + N Memberships
       Item/Revision/no-change/absence decisions
       IntakeChangeSet + child scheduling intents
  → commit
  → queue wake-up
  → 0..N child Executions target exact IntakeItem/Revision
  → proof-valid children may publish independently
  → root collect-all over committed required membership set
```

root child count是projection；fan-in分母来自accepted IntakeSnapshot/IntakeChangeSet required set。parent Task failure/cancel不回滚已proof-valid child。

### 4.3 Acceptance transaction

1. 校验IntakeCandidateSet为sealed、team/IntakeSource/producer Execution fence/current definitions一致；
2. 对observation identity + root digest执行幂等/冲突检查；
3. 插入immutable IntakeSnapshot；
4. 按IntakeSource-scoped normalized ExternalKey resolve/create IntakeItem；
5. 绑定exact SemanticDefinition versions计算RevisionFingerprint；
6. no-change引用既有IntakeRevision，change追加IntakeRevision+semantic rows并CAS latest；
7. 写seen IntakeSnapshotMembership；仅complete-authoritative计算absence decisions；
8. 写typed IntakeChangeSet与child scheduling outbox；
9. commit后才wake queue；
10. 任一步失败全部回滚，事务外IntakeArtifact进入orphan治理。

### 4.4 Serving publication

```text
immutable candidate Revision
  → derived generation build
  → type-specific validate/proof
  → validate team + active Item + expected latest/serving + policy
  → same transaction:
       CAS Item.serving_revision_uuid
       append IntakeItemTransition
       append publication/invalidation outbox
  → new revision retrieval-eligible
```

Item为deactivated/deleted、proof target不是该Item Revision、expected pointer过期或proof不完整时必须fail-closed。

### 4.5 Deactivate、delete、rebuild/reindex 与 purge

| Intent | 改IntakeRevision | 改lifecycle/serving | 新runtime generation | 物理删除 |
|---|---:|---:|---:|---:|
| deactivate | 否 | active→deactivated，serving null | 是，资源command | 异步invalidation，可按policy保留 |
| delete | 否 | →deleted，serving null+tombstone | 是，资源command | 异步cleanup，受retention/hold/proof围栏 |
| rebuild/reindex | 否 | 仅proof后切derived/index generation；Item pointer按业务需要保持 | 是 | grace后删旧generation |
| physical_purge | 否 | 不改变 | 可由S03 maintenance Process执行 | 只删eligible substrate并写proof |

### 4.6 Deterministic recovery matrix

| Durable observation | 唯一合法动作 |
|---|---|
| pages不全或seal超时 | abandoned；按retention清staging；无Snapshot |
| sealed IntakeCandidateSet且无IntakeSnapshot | 重跑相同fenced acceptance transaction |
| IntakeSnapshot/IntakeChangeSet/outbox已commit但未wake | replay outbox；不重建Snapshot/Revision |
| duplicate delivery/child replay | child intent/process idempotency + fence收敛 |
| IntakeArtifact已写但DB rollback | S13按owner ref/digest/grace清orphan |
| DB引用缺失IntakeArtifact | fail-closed，repair intent；禁止virtual IntakeArtifact |
| Item pointer与transition ledger不一致 | 依据最后valid fenced transition修projection或隔离告警 |

### 4.7 Internal domain ports

| Port | Caller / consumer | Contract |
|---|---|---|
| `CandidateSetStagingPort` | S05→S04 | page append、seal、abandon；严格size/digest/fence |
| `IntakeAcceptancePort` | S03/S05→S04 | sealed candidate ref→accepted IntakeSnapshot/IntakeChangeSet/idempotent result |
| `IntakeReadPort` | S02/S03/S05-S10 | team-scoped IntakeSource/IntakeSnapshot/IntakeItem/IntakeRevision/IntakeArtifact/IntakeSnapshotMembership read |
| `IntakeTransitionPort` | S03 proof/resource command→S04 | action version、expected pointers/state、proof/policy、causation→CAS transition |
| `IntakeEligibilityPort` | S09-S10 | exact team/item/serving revision/lifecycle fence验证 |
| `IntakeCleanupPort` | S09/S12/S13/S15 | cleanup intent读取、substrate proof提交、aggregate completion读取 |
| `IntakeRegistryPort` | bootstrap/internal compiler | deterministic semantic/action register + readonly list/get |

S04不在本spec新增public CRUD URI。外部mutation继续通过S01/S02 versioned Task Contract；canonical Intake read surface的URI、分页与授权在S02/S16对齐后落地，但不得暴露definition CUD、direct pointer patch或hard delete后门。

### 4.8 Typed errors

| Error key | 语义 |
|---|---|
| `intake-source-not-found` | team scope内IntakeSource不存在或不可接受新IntakeSnapshot |
| `intake-item-not-found` | team scope内IntakeItem不存在 |
| `intake-observation-conflict` | 相同observation identity对应不同root digest |
| `intake-candidate-not-sealed` | acceptance请求未达到sealed |
| `intake-candidate-size-exceeded` | member/byte/transaction fence超限 |
| `intake-definition-drift` | definition version/digest不匹配 |
| `intake-revision-conflict` | ordinal/fingerprint/predecessor违反唯一历史 |
| `intake-transition-conflict` | expected lifecycle/pointer/row revision CAS失败 |
| `intake-publication-proof-invalid` | proof缺失、target不符或验证失败 |
| `intake-authoritative-scope-invalid` | absence decision无complete-authoritative资格 |
| `intake-artifact-missing` | canonical truth引用的IntakeArtifact不可读 |
| `intake-retention-fenced` | hold/reference/grace/lineage阻止cleanup |
| `intake-bootstrap-drift` | schema/registry同版本异digest或引用缺失 |

错误必须携带team、stable target、causation与可安全公开的current revision/fence，不泄漏secret、absolute path或跨team存在性。

---

## 5. 实施切片、风险与反例

### 5.1 推荐实施切片

1. `S04-E01`：五类identity、membership、semantic/action registries与transition repositories；
2. `S04-E02`：deterministic RegistryManifest/bootstrap/readiness verifier；
3. `S04-E03`：IntakeCandidateSet staging/page/seal/size fence；
4. `S04-E04`：single/scatter canonical acceptance transaction与typed IntakeChangeSet/outbox；
5. `S04-E05`：Item lifecycle/serving CAS、proof validation与retrieval eligibility；
6. `S04-E06`：recovery scanner/repair intents/orphan contract；
7. `S04-E07`：retention references、cleanup intents/proofs与generation-switch integration；
8. `S04-E08`：cross-domain API/read models、acceptance matrix和legacy dependency scan。

### 5.2 架构依赖纪律

```text
domain/intake
  depends on: UUID/clock/digest/typed contract abstractions
  does not depend on: HTTP, queue driver, Turso driver, filesystem, vector engine,
                      model runtime, legacy package/schema/status

application/intake
  orchestrates: acceptance, transition, recovery, cleanup aggregation

adapters
  implement: Turso repositories, local storage, queue/outbox, telemetry
```

### 5.3 主要风险

| Risk | 等级 | 强制围栏 |
|---|---|---|
| source-scoped key归一化漂移产生双Item | P0 | versioned normalizer + unique fence + conflict audit |
| large scatter事务过大或partial truth | P0 | page/seal/size budget + one canonical commit |
| latest误当serving暴露失败候选 | P0 | separate pointers + proof CAS + query dual fence |
| complete/partial混义造成批量误下架 | P0 | explicit completeness + authoritative scope + policy |
| IntakeArtifact/DB跨介质断点 | P0 | bytes-first + digest/owner + orphan/repair，不伪造 |
| reindex/purge混义造成检索空窗或误删 | P0 | generation isolation + retention refs + substrate proofs |
| payload_extra成为影子schema | P1 | promotion rule + read-dependency scan + fail-loud |
| registry drift导致历史重解释 | P0 | immutable versions + RegistryManifest digest + readiness reject |
| tombstone删除导致external key复用/审计断链 | P1 | minimal permanent skeleton，v1禁止hard delete |
| legacy实现渗入runtime | P0 | dependency/config/DDL/API/event/startup scan |

### 5.4 禁止反例

| Counterfactual | 裁决 |
|---|---|
| 用`file_uuid`或`document_uuid`同时表示IntakeSource/Item/Revision和运行目标 | 禁止；使用完整Intake identities。 |
| scatter root伪造parent IntakeItem，children放JSON数组 | 禁止；IntakeSource+Snapshot+Membership是集合truth。 |
| 每次fetch/rebuild/model升级都创建Revision | 禁止；仅canonical semantic change。 |
| 直接把latest candidate设为serving | 禁止；必须type-specific proof-valid CAS。 |
| partial/timeout/空响应推导全量absence | 禁止；仅complete-authoritative scope。 |
| 新semantic/action key只写payload_extra让代码解释 | 禁止；必须注册immutable definition。 |
| Reconciler从日志/queue/IntakeArtifact猜IntakeSnapshot或proof | 禁止；只修已提交truth的projection/wakeup/intent。 |
| purge成功后reset Task pending或恢复serving | 禁止；四类intent职责分离。 |
| bootstrap直接seed一批serving Item | 禁止；内容必须走正常Task/Intake Contract。 |
| 以legacy schema/status作为兼容或验收目标 | 禁止；legacy只作ReferenceAnchor。 |

---

## 6. 强制验收矩阵

### 6.1 Acceptance scenarios

| ID | 场景 | 必须结果 |
|---|---|---|
| `S04-A01` | 空DB首次bootstrap | schema+constraints+registries成功，readiness true，无legacy输入 |
| `S04-A02` | 同版本同manifest再次bootstrap | no-op，row/digest不变化 |
| `S04-A03` | 同版本registry digest不同 | fail-loud，readiness false，无原位覆盖 |
| `S04-A04` | cross-team IntakeSource/IntakeItem/IntakeRevision lookup | 不可见且无存在性泄漏 |
| `S04-A05` | single one-member intake | 一Snapshot/一membership/稳定Item/正确Revision decision |
| `S04-A06` | scatter N members | 一Snapshot、N memberships、恰好required child intents |
| `S04-A07` | zero-member complete-authoritative | typed zero result与合法absence policy，不悬挂running |
| `S04-A08` | partial Snapshot缺少旧Item | 不产生absence deactivation |
| `S04-A09` | complete-authoritative缺少旧Item | 产生typed absence action并按policy transition |
| `S04-A10` | 同observation/digest重放 | 返回同Snapshot，无重复Revision/membership/intent |
| `S04-A11` | 同observation异digest | `intake-observation-conflict`并保留审计 |
| `S04-A12` | 语义tuple相同 | no-change，不建Revision，membership引用既有Revision |
| `S04-A13` | fingerprint参与值变化 | append新Revision，predecessor/ordinal/definitions正确 |
| `S04-A14` | 新semantic definition发布 | 新Revision可绑定新version；历史Revision解释不变 |
| `S04-A15` | candidate构建失败 | old serving继续，latest/serving按已提交truth保持 |
| `S04-A16` | proof-valid publish | Item/transition/outbox同事务CAS，检索双围栏放行 |
| `S04-A17` | stale pointer/proof publish | 冲突或proof invalid，无pointer改变 |
| `S04-A18` | deactivate | serving立即null，异步projection残留也不可检索 |
| `S04-A19` | reactivate | active但serving仍null，需重新proof publish |
| `S04-A20` | delete | durable tombstone，普通ingest/rebuild不复活 |
| `S04-A21` | Task cancel且已有published child | published child保留，未完成work停止，无隐式withdrawal |
| `S04-A22` | pages缺失/timeout | candidate abandoned，无Snapshot |
| `S04-A23` | member/bytes超限 | accept前fail-loud，不生成partial Snapshots |
| `S04-A24` | sealed后acceptance崩溃 | 重放收敛到一个Snapshot |
| `S04-A25` | commit后wake丢失 | outbox replay补wake，不重复truth |
| `S04-A26` | IntakeArtifact bytes orphan | grace后清理，不出现canonical引用 |
| `S04-A27` | canonical IntakeArtifact缺失 | fail-closed + repair intent，无virtual IntakeArtifact |
| `S04-A28` | recovery重复100次 | Snapshot/Revision/child/proof行数不增长 |
| `S04-A29` | reindex新generation失败 | old generation持续服务 |
| `S04-A30` | reindex验证成功 | CAS切generation，grace后旧代eligible cleanup |
| `S04-A31` | purge存在hold/reference | `intake-retention-fenced`，无substrate删除 |
| `S04-A32` | 某substrate proof失败 | aggregate未complete，retry且serving不恢复 |
| `S04-A33` | 全部cleanup proofs完成 | physical purge complete，最小tombstone/audit仍可查 |
| `S04-A34` | payload_extra round-trip | 所有适用表存在；核心logic不读取未晋升key |
| `S04-A35` | schema/registry/workflow ref drift | startup readiness false，不自动猜修 |
| `S04-A36` | legacy dependency scan | runtime/config/DDL/API/event/startup零依赖 |

### 6.2 必须留存的验收证据

1. 十张canonical + supporting ledgers logical→physical DDL mapping；
2. PK/FK/unique/CHECK/XOR/CAS/payload_extra约束报告；
3. RegistryManifest、digest和bootstrap idempotency fixtures；
4. ExternalKey normalizer与RevisionFingerprint golden/property report；
5. single/scatter/absence/IntakeChangeSet/route fixtures；
6. serving/lifecycle transition exhaustive与并发CAS报告；
7. large-scatter page/seal/size/transaction fault injection；
8. outbox/recovery/orphan/repair幂等报告；
9. retention/reference/cleanup proof与generation switch报告；
10. startup drift/readiness与MKB schema evolution演练；
11. runtime dependency/config/DDL/API/event/startup legacy scan报告。

---

## 7. Reference-anchor 台账

### 7.1 权威文档锚

| Reference | 使用方式 |
|---|---|
| `docs/baseline/qna-truth/S04.md v1.1` | Q1-Q9 owner回答、`T-O-30..48`与final closure |
| `docs/baseline/domain-truth/D01-task-execution-process-flow.md` | Task/Execution/Process身份、single/scatter runtime树 |
| `docs/baseline/domain-truth/S01-skill-worker-integration.md` | standalone、UUID、Task接收、payload_extra规则 |
| `docs/baseline/domain-truth/S02-task-api.md` | Task聚合、items、cancel/retry/rebuild因果 |
| `docs/baseline/domain-truth/S03-workflow-engine.md` | WorkflowRevision、typed route、proof、recovery与Process cleanup |
| `docs/baseline/spec-glossary.md` | canonical Intake与cross-domain词汇 |

### 7.2 Legacy code evidence anchors

| Ref ID | 文件锚 | 只证明的事实 / MKB verdict |
|---|---|---|
| `S04-REF-L01` | `legacy-family/smind-console/db/05-files.sql:22-70,210-256` | file/relation混合identity、runtime、artifact与payload债务；MKB拆分。 |
| `S04-REF-L02` | `legacy-family/smind-admin/ingestion/apis.ts:91-115`; `urls.ts:87-114` | random file UUID与payload藏source；MKB建立IntakeSource namespace。 |
| `S04-REF-L03` | `legacy-family/smind-skill-clean-dedicated-apis/core/schemas_common.ts:111-132`; `providers/domain/processor.ts:177-228` | stable atomic key与多digest生产经验。 |
| `S04-REF-L04` | `legacy-family/smind-clean-dispatcher/services/differ.ts:94-191` | content/meta no-op/full/context diff原理；MKB升级为versioned semantics。 |
| `S04-REF-L05` | `legacy-family/smind-clean-dispatcher/flows/finalizer.ts:107-269` | scatter后加、无独立accepted manifest的断点；MKB原生Snapshot acceptance。 |
| `S04-REF-L06` | `legacy-family/smind-console/functions/api/files/[uuid]/artifacts.ts:37-183` | 从Process payload反扫/virtual artifact债务；MKB显式IntakeArtifact owner/digest。 |
| `S04-REF-L07` | `legacy-family/smind-console/db/06-process-tracking.sql:195-273` | vector/process/asset混义；MKB exact Revision lineage。 |
| `S04-REF-L08` | `legacy-family/smind-skill-rag-vectorizer/src/purger_logic.ts:67-152` | purge/reindex/task-reset混义风险；MKB四intent分账。 |
| `S04-REF-L09` | `legacy-family/smind-admin/management/static.ts:113-139` | logical delete与physical cleanup分层但缺proof；MKB补cleanup ledger。 |
| `S04-REF-L10` | `legacy-family/smind-console/functions/api/files/list.ts:69-181` | parent/child表UNION和scope模拟债务；MKB统一Item/team fence。 |

### 7.3 外部一手资料

| Reference | 支持边界 |
|---|---|
| [W3C PROV-DM](https://www.w3.org/TR/prov-dm/) | entity/activity/revision/collection membership与显式provenance；不规定MKB schema。 |
| [CloudEvents 1.0.2](https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md) | source+id上下文支持source-scoped key类比；不是MKB API。 |
| [RFC 9530](https://www.rfc-editor.org/rfc/rfc9530.html) | content与representation digest分账；digest不等于identity。 |
| [Apache Iceberg Specification](https://iceberg.apache.org/spec/) | immutable manifests/snapshots与atomic pointer的工程分母；不复制格式。 |
| [RFC 9110 DELETE](https://www.rfc-editor.org/rfc/rfc9110.html#name-delete) | resource association解除与存储销毁可分层。 |
| [Amazon S3 Versioning](https://docs.aws.amazon.com/AmazonS3/latest/userguide/versioning-workflows.html) | delete marker/current visibility与旧版本保留的分层证据。 |

### 7.4 证据使用判定

- **保留原理**：team scope、stable external key、多digest、diff/scatter/provenance、logical-first deletion；
- **全局升级**：五类Intake身份、accepted Snapshot、immutable Revision/definitions、proof serving、native large-scatter、cleanup proof、greenfield bootstrap；
- **删除负债**：file/relation current row、random child UUID、日志反扫Artifact、vector/process混义、purge reset、Cloudflare/D1/R2/Worker callback绑定；
- **禁止继承**：任何legacy代码、表、ID、status、wire、storage locator、bootstrap数据或验收输出。

---

## 8. Domain verdict

### 8.1 Verdict

**`ACCEPTED / GO`**：S04 的五类Intake identity、single/scatter collection truth、immutable semantic revisions、ten-table relational SSOT、serving/lifecycle state machine、large-scatter acceptance/recovery、MKB-only retention/reindex/purge以及greenfield bootstrap/evolution/acceptance已全部完成owner-gate并进入正式候选真相。

### 8.2 强制结论

1. Intake不是file/document别名，也不自动等于Knowledge；
2. IntakeSource/IntakeSnapshot与IntakeItem/IntakeRevision是两条正交事实轴；IntakeSnapshotMembership是集合SSOT；
3. Revision只由canonical semantic change产生，runtime/build/index generation独立；
4. latest与serving分离，publication必须proof-valid CAS；
5. Item三态、CoreEffect与versioned ActionDefinition共同提供“封闭安全核心+可治理语义扩展”；
6. IntakeCandidateSet acceptance是唯一collection线性化点，queue/log/IntakeArtifact无成功权；
7. large scatter受显式容量围栏，recovery不得合成未提交truth；
8. deactivate/delete/rebuild-reindex/physical-purge严格分账；
9. cleanup按substrate proof收敛，v1长期保留tombstone/audit skeleton且不开放deleted restore；
10. MKB空库确定性bootstrap并仅演进自身schema，legacy-family永久reference-only。

### 8.3 下游必须继续冻结的边界

| 下游 | 必须承接、但不由S04冒充冻结的内容 |
|---|---|
| `S05` | IntakeSource kind/descriptor、ExternalKey normalization、fetch/clean/canonicalization、IntakeCandidateSet exact contract与digest算法 |
| `S06-S08` | Block/Construction/Embedding exact schema、generation与proof生产 |
| `S09-S10` | IndexGeneration schema、proof-switch、retrieval filter/query implementation |
| `S12` | exact Turso DDL/index/trigger/transaction/outbox/scanner/migration与capacity benchmark |
| `S13` | local Intake/derived asset backend/locator/atomic write/orphan/GC实现 |
| `S14-S15` | retention durations/policies、registry deployment、event/metric/alert/runbook |
| `S16` | secret/hold/admin/read authorization与cross-team防护 |

如只落地本文interface与不变量，无需reopen S04；如要增加Knowledge domain、外部registry CUD、第四种Item state、普通deleted restore、tombstone hard delete、无限/分代Snapshot visibility或legacy兼容，必须显式reopen。

### 8.4 一句话结论

S04 将所有外部输入统一提升为可审计的Intake身份、观察、集合、修订和表示真相，并以proof-gated serving、原子scatter、受限恢复和cleanup proof保证MKB从空库开始也能长期、独立、可靠地治理摄入资产。

---

## 9. 修订历史

| 版本 | 日期 | 作者 | 状态 | 主要变更 |
|---|---|---|---|---|
| `S04-v1.0` | `2026-07-15` | `MKB owner + Codex` | `accepted` | 吸收Q1-Q9与`T-O-30..48`；冻结五类Intake identity、十表schema、semantic/action registries、IntakeCandidateSet acceptance、三态/serving CAS、large-scatter recovery、retention/reindex/purge、greenfield bootstrap/schema evolution/acceptance及ReferenceAnchor边界。 |
