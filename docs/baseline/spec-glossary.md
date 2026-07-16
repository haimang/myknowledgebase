# MKB Scope & Glossary

> **项目**：`myknowledgebase`（MKB）
>
> **文档角色**：跨规格词汇手册、命名边界与对齐登记册
>
> **权威输入**：D01-v1.3、S01-v1.4、S02-v1.2、S03-v1.2、S04-v1.1、S05-v1.0、S04-S05冻结QNA / `T-O-30..76`
>
> **状态**：`active / S05 complete / D01-S05 cross-spec alignment complete`
>
> **版本 / 日期**：`v1.1 / 2026-07-16`

## 0. 使用规则

本手册解决三个问题：同一个名词在 MKB 中只能表达什么、不能表达什么，以及旧词如何迁移。它不取代各 Domain Truth 的完整 schema、状态机和 API Contract。

词汇成熟度分为：

| 标记 | 含义 |
|---|---|
| `frozen` | 已由 owner 在 D01 或 S01-S03 冻结；本手册只转述，不改变原裁决 |
| `owner-directed / designing` | 名称由owner指定，但其exact职责仍在尚未完成的下游Spec中设计 |
| `reserved` | 仅保留命名空间；当前不得建表、暴露 API 或作为现有对象别名 |
| `derived` | 由权威真相编译、投影或构建，可重建，不反向成为 SSOT |
| `legacy-only` | 只用于代码考古、生产踩坑或reference rationale，禁止进入MKB canonical schema/runtime |
| `retired candidate` | 曾在未冻结设计中使用，已被新词取代 |

约束：

1. 新 schema、API 和事件必须使用本手册的 canonical term；无法归类时先更新词汇手册，不得临时复用 `file`、`document`、`artifact` 等宽泛名词。
2. Domain Truth 的 exact 定义优先于本手册摘要；发现冲突必须显式修订，禁止靠同义词绕过 Truth Gate。
3. D01与S01-S04已按S05-v1.0完成边界审计和版本化校准。历史QNA/legacy code anchor可保留旧词；当前正式Spec、schema、API与event不得继续把`Document`当canonical alias，也不得让S05重建独立runtime或Intake lifecycle。
4. 大写 CamelCase 表示业务类型；`snake_case_uuid` 表示持久化身份字段；自然语言中的普通名词不自动成为业务类型。
5. 在已经明确进入 Intake 语境的说明性 prose/diagram 中，可用 `Snapshot / Item / Revision / Membership / CandidateSet / ChangeSet` 作为对应完整类型的短写；schema、field、API、event、port 和首次定义仍必须使用完整 canonical term。`Source` 与 `Artifact` 因跨域碰撞风险不得采用此短写规则。

---

## 1. 系统与租户边界

| Canonical term | 成熟度 | 定义 | 禁止误用 |
|---|---|---|---|
| `MKB` | `frozen` | 本地 standalone leaf-worker 单体应用，对上游提供 Task Contract，在内部执行 LS-RAG workflow | 不等于 legacy Worker 集合，也不拥有用户、团队或计费平台 |
| `Team` / `team_uuid` | `frozen` | 上游预注册的最小租户、审计、分区和查询围栏；所有长期与运行身份均在 team scope 内解释 | 不等于完整组织/RBAC domain；不得省略后依赖“全局唯一 UUID”绕过隔离 |
| `MKB Contract` | `frozen` | MKB 对上游公开的协议，包括 Task create/read/control 与只读能力 | 不等于 03-nano 私有 RPC，也不暴露内部 Execution/Process mutation |
| `canonical identity` | `frozen` | 由权威表、唯一约束和 resolver 决定的业务身份 | 不能由日志、queue message、路径、digest 或 payload 临时推断 |
| `projection` | `frozen` | 由 durable truth 生成的查询/运行视图，可重建 | 不得反向成为状态机或资产 SSOT |
| `Readiness` | `frozen principle / S01 + S04-T043` | 进程已经通过schema、registry、reference和未完成migration检查，可以安全接收业务流量的启动门 | 不等于进程存活；drift时必须false，不能启动时猜修业务truth |

---

## 2. Runtime 与 Workflow 词汇

> 本节转述 D01/S01-S03 已冻结含义。S04 只引用这些运行对象，不重定义其生命周期。

| Canonical term | 成熟度 | 定义 | 稳定身份 | 明确不承担 |
|---|---|---|---|---|
| `Task` | `frozen` | 对外API ACK/CRUD/aggregate单元，持有RequestIntent、总状态、current root Execution指针与结果投影 | `(team_uuid, task_uuid)` | RAG工序细节、内部claim/retry、长期Intake资产状态 |
| `RequestIntent` / `request_intent` | `frozen / S01-v1.4` | Task对外资源动作的严格discriminator；v1为`intake.ingest/rebuild/update_metadata/deactivate/delete`与`index.rebuild` | request intent不是Workflow/Process分类；`task_type`不是兼容别名 |
| `TaskAudit` | `frozen / S01` | 与Task 1:1原子保存的immutable上游业务审查快照 | `(team_uuid, task_uuid)` | 不等于MKB Event/Log，也不由Task PATCH修改 |
| `TaskGeneration` | `frozen` | 同一 Task 在 full retry 下的有序 root execution generation | Task 内 generation ordinal/ref | 不等于 IntakeRevision；automatic Process retry 不创建 generation |
| `TaskItem` | `frozen / projection` | scatter generation与IntakeSnapshot/ChangeSet下的有界结果项，供API分页与聚合 | Task/generation/Intake item projection key | 不成为IntakeItem、Membership或canonical asset SSOT |
| `TaskRestart` | `frozen` | 独立、append-only的full retry/atomic IntakeItem rebuild因果与admission记录 | restart UUID + source/target refs | 不复制Task状态；其状态由关联Task join得出 |
| `Execution` | `frozen` | 一次 durable workflow run，是执行阶段唯一内部查询 UUID；single root 或 scatter root/child 均使用该对象 | `execution_uuid` | 对外 Task identity、具体工序 attempt、长期 Intake identity |
| `Process` | `frozen` | 一个 Workflow step 在某 Execution 中的 durable 工序实例，拥有 claim/lease/fencing/retry 与 I/O outcome | `process_uuid` | 长期资产身份；Process projection 可清理，但其证明引用必须保留 |
| `Workflow` | `frozen` | MKB 内部注册、声明式、关系 schema 为 SSOT 的执行定义 | workflow key + immutable revision | v1 不允许外部/agent CUD，也不是 Task 生命周期 |
| `WorkflowRevision` | `frozen` | 已注册 Workflow 的不可变定义版本；Execution 创建时固定绑定 | workflow revision UUID/key | registry 更新不得热改已存在 Execution |
| `CompiledWorkflowJSON` | `derived` | 由关系型 Workflow truth 确定性编译的只读声明式 JSON | compiler/schema/digest 标识 | 不得反向编辑或成为 Workflow SSOT |
| `ProcessCapabilityManifest` | `frozen / S03-v1.2` | 由MKB内部code registry持有的versioned Process contract，定义process key、typed ports/parameters、outcome/proof、side-effect和idempotency语义 | process key + contract version + digest | 不是外部skill manifest，不是第八张Workflow truth表，不承载一次Process状态 |
| `SkillWorkerManifest` | `deferred / S01-v1.4` | 未来防腐adapter可能向03-nano/skill-worker生态投影的外部能力声明 | 由MKB capability read model确定性派生；exact schema届时由adapter Spec冻结 | v1不存在该对象或生命周期；不得作为启动依赖、MKB domain SSOT、ProcessCapabilityManifest或RegistryManifest的别名 |
| `BindingSource` | `frozen / S03-v1.2` | Workflow binding中某个typed值的来源类别，如execution context、IntakeSnapshot、prior output、control value、registry ref或literal | binding row + exact source fields | 不等于IntakeSource；禁止再用裸`Source`作为业务类型名 |
| `RegistrationOrigin` | `frozen / S03-v1.2` | Workflow/definition由code、migration或bootstrap注册的provenance | module/commit/migration/fingerprint refs | 不等于IntakeSource或user identity |
| `ProcessCommand` | `frozen` | Engine 交给叶子工序的类型化输入、logical refs、digests 与 control envelope | command/delivery refs | 不携带任意 graph 或让 leaf 决定路由 |
| `ProcessOutcome` | `frozen` | 叶子工序返回的类型化结果、错误和 proof inputs | process + fencing token + outcome refs | transport ACK 不等于业务成功 |
| `PublicationProof` | `frozen contract / exact schema downstream` | 证明某 Execution/Process 的业务产物满足上线条件的类型化证据集合 | target + proof digest/version | queue empty、日志字符串、单个 vector ACK 均不是充分证明 |
| `Attempt` | `retired candidate` | MKB 新架构中不存在的第四层运行身份 | — | automatic retry 仍在同一 Process 上，通过计数/lease/delivery 记录表达 |

### 2.1 Runtime 控制方向

```text
external intent
  → Task
    → root Execution
      → child Execution(s) when scatter requires
        → Process(es)

control intent flows downward
status/proof aggregates upward
durable Intake truth survives every runtime object's retention
```

### 2.2 跨状态控制词

| Canonical term | 成熟度 | 定义 | 禁止误用 |
|---|---|---|---|
| `CAS` / compare-and-swap | `frozen principle` | 以expected revision/state/pointer/fence为前置条件的单一线性化写入 | 不等于应用层先读后写；失败方不能反转先提交结果 |
| `Fence` / `FencingToken` | `frozen principle` | 使旧claim、旧pointer或旧command在新代提交后失效的递增/不可伪造围栏 | UUID、queue delivery count或timestamp本身不自动成为fence |
| `Outbox` | `frozen principle` | 与业务truth同事务写入、commit后驱动wake/delivery的durable intent ledger | queue ACK不是outbox commit；outbox不拥有业务终态 |
| `DeterministicRecovery` | `frozen / S03 + S04-T044` | 只依据durable truth、idempotency key与fence补齐确定性projection/wakeup/intent的恢复行为 | 不要求独立Reconciler产品；不得从日志猜或合成业务truth |

---

## 3. Intake 词汇

### 3.1 命名空间原则

`Intake` 表示 MKB 获取、接受、规范化并管理外部输入事实的上层建筑。它比 `file` 或 `document` 更抽象：来源可以是 upload、object、URL、single API 或 scatter API；业务项可以有物理文件表示，也可以只由 API 指针与结构化 payload 表示。

`Intake*` 不自动等于“已成为知识”。其目标是把来源、观察、稳定项、不可变修订和具体表示变成可审计的 durable truth，为 LS-RAG 与未来 Knowledge 层提供可靠输入。

### 3.2 五个核心类型

#### `IntakeSource`

| 属性 | 词汇约束 |
|---|---|
| 成熟度 | `frozen / S04 T-O-30` |
| 定义 | 一个 team 内可持续识别的外部输入绑定，也是 external key 的命名空间 |
| 身份字段 | `intake_source_uuid`；业务唯一性规则待 S04 Round 2 |
| 典型 kind | exact v1 enum为`inline_payload/local_object/http_resource/registered_api`；single/scatter属于cardinality，不是kind |
| 拥有 | source descriptor、connector/config/secret references、single/scatter capability、lifecycle |
| 不拥有 | secret 明文、fetch attempt status、正文 bytes、Process state、Item revision content |

一次性 upload 仍可拥有 IntakeSource。该选择统一 provenance、team fence 与 single/scatter 模型，不意味着它必须长期可再次抓取。

#### `IntakeSnapshot`

| 属性 | 词汇约束 |
|---|---|
| 成熟度 | `frozen / S04 T-O-30..31` |
| 定义 | MKB 接受的某个 IntakeSource 的一次不可变观察结果；取代候选词 `Source Observation` |
| 身份字段 | `intake_snapshot_uuid` |
| 必须表达 | observed/accepted time、complete/partial、authoritative scope、validator、membership/collection summary、producer lineage |
| 可拥有IntakeArtifact | raw response、uploaded object snapshot、collection representation |
| 不包含 | 网络/鉴权/schema 失败尝试；这些属于 Execution/Process/Event |

`IntakeSnapshot` 不是 retry attempt。只有通过接收门的观察才形成 Snapshot；失败尝试不能伪装成一份“失败的来源事实”。

#### `IntakeItem`

| 属性 | 词汇约束 |
|---|---|
| 成熟度 | `frozen / S04 T-O-30..32` |
| 定义 | 一个 IntakeSource 内可独立修订、发布、失活、重建和审计的稳定业务项 |
| 身份字段 | `intake_item_uuid` |
| 默认 resolver scope | `(team_uuid, intake_source_uuid, normalized_external_key)`；exact normalizer key/version/digest由S05 definition锁定 |
| 持有 | lifecycle、latest revision pointer、serving revision pointer、policy reference |
| 不等于 | API request、文件路径、content hash、Snapshot membership、Execution、Revision |

IntakeItem 的语义刻意保持中性。它可以对应上传对象、URL 内容主体、single API 资源或 scatter API 中一个 atomic child。

#### `IntakeRevision`

| 属性 | 词汇约束 |
|---|---|
| 成熟度 | `frozen / S04 T-O-30/T-O-32..33` |
| 定义 | IntakeItem 的一次不可变业务语义状态 |
| 身份字段 | `intake_revision_uuid` |
| 拥有 | ordinal、predecessor、creation reason、canonical digests、schema/canonicalization refs、source provenance |
| 不等于 | WorkflowRevision、TaskGeneration、Process retry、embedding/index generation |
| mutation rule | 创建后不得原位改正文、context/filter metadata 或 lineage；canonical semantic change 追加 Revision，runtime/build/index generation 不制造 Revision |

Revision 回答“来源业务事实是否改变”；build generation 回答“同一事实如何被再次处理”。二者不得混用。

#### `IntakeArtifact`

| 属性 | 词汇约束 |
|---|---|
| 成熟度 | `frozen / S04 T-O-30` |
| 定义 | 承载 IntakeSnapshot 或 IntakeRevision 的不可变物理/逻辑表示 |
| 身份字段 | `intake_artifact_uuid` |
| owner | exact one direct owner：Snapshot 或 Revision；role 解释其用途 |
| 必须表达 | role、media type、digest、size、logical locator、producer/lineage、retention fence |
| 不等于 | Process log、任意 output JSON、LSRagBlock、ConstructionUnit、VectorRecord |

“Artifact”不是所有派生对象的父类。S13 管理 bytes/backend/GC，S04 管理 IntakeArtifact 的资产身份和 lineage。

### 3.3 支撑词

| Canonical term | 成熟度 | 定义 |
|---|---|---|
| `ExternalKey` / `external_key` | `frozen / S04+S05-v1.0` | 外部provider对某一业务项的稳定键，只能在team + IntakeSource namespace内解释；S05 source-specific pure normalizer输出normalized key、exact version/digest/evidence，缺失时不得随机UUID/content-hash fallback |
| `IntakeSnapshotMembership` | `frozen / T-O-31` | Snapshot 与 Item/Revision 之间的不可变集合事实，记录 seen/no-change/new-revision/absence 等 decision；不是上层业务资产 |
| `SnapshotCompleteness` | `frozen / T-O-31/T-O-35` | Snapshot 对声明 scope 的 `complete` 或 `partial` 事实；failure 不是第三种 Snapshot completeness |
| `AuthoritativeScope` | `frozen / T-O-31/T-O-35` | Snapshot 有权对哪个集合声明“本次完整”；只有 complete + authoritative 才可能依据 absence 推导失活 |
| `HTTPValidatorEvidence` | `frozen distinction / S05-v1.0` | ETag、Last-Modified等HTTP条件请求/一致性提示证据，不自动成为Revision identity、完整性证明或PreflightValidator |
| `Digest` | `frozen / S05-v1.0` | 带scope、SHA-256算法和canonicalization/schema/definition版本的内容或metadata摘要；JSON基线JCS，text基线UTF-8/LF/NFC；用于完整性/变更判断，不替代UUID、authority或identity |
| `IntakeSourceKindDefinition` | `frozen / S05-T004` | 内部注册、immutable versioned的source contract，绑定strict descriptor/config schemas、cardinality/completeness、capability eligibility、normalizer、budget与preflight eligibility |
| `AcquisitionEvidence` | `frozen / S05-T008` | 一次acquisition Process在exact Execution fence下形成的typed representation/media/encoding/redirect/page/budget证据；不是IntakeSnapshot或HTTP日志 |
| `IntakeCandidateMember` | `frozen / S05-T008` | CandidateSet内具有stable ordinal、ExternalKey evidence、canonical semantic tuples、Artifact/clean/validation refs的typed member；不是IntakeItem，需经S04 acceptance解析 |
| `CleanArtifactCandidate` | `frozen / S05-T008..10` | clean活动产出的staged typed descriptor，携带input/output digest、logical handle、capability/parser/model/prompt、producer fence、loss/quality与lineage；acceptance后才绑定canonical IntakeArtifact owner |
| `RevisionBasis` | `frozen / S05-T010` | source definition声明哪些确定性事实可参与IntakeRevision判断的versioned类别；v1基线为typed source semantics、deterministic canonical text或opaque representation，AI/OCR输出不能单独作为basis |
| `SemanticDefinition` | `frozen / T-O-33/T-O-36` | 内部注册、不可变版本化的语义维度定义，声明 value/schema kind、是否参与 Revision fingerprint 及其 typed route signal |
| `RevisionSemantic` | `frozen / T-O-36` | 某 IntakeRevision 对一个 exact SemanticDefinition version 的 canonical value digest/value-ref；normalized row 是 SSOT |
| `IntakeItemTransition` | `frozen / T-O-36/T-O-40` | IntakeItem 每次 lifecycle/pointer/action CAS 的 append-only 审计事实，绑定before/after state、action version、causation、fence与proof refs；对应`intake_item_transitions` | 不是Process状态、可变Item快照或普通Event文本 |
| `RevisionFingerprint` | `frozen principle / T-O-32..33/T-O-38` | 由该 Revision 绑定且参与 fingerprint 的 semantic definition/value tuples 确定性计算，用于幂等收敛 |
| `IntakeCandidateSet` | `frozen / S04+S05-v1.0` | S05在S04 acceptance前产出的typed观察候选，包含scope/completeness、staged Artifact refs、ExternalKeys、canonical semantic values、rejection/gap evidence与PreflightOutcome；不是accepted Snapshot |
| `CandidateSetPage` | `frozen / S04+S05-v1.0` | Large-scatter CandidateSet中具有stable ordinal、ordered member digests与SHA-256/JCS page digest的immutable staging分片；page不是独立Snapshot，缺页集合不得seal |
| `CandidateSetSeal` | `frozen / S04+S05-v1.0` | pages/root digest、count/bytes、dedupe、Artifact refs、scope、rejection/gap与source-exhaustion proof通过后形成的immutable acceptance资格；seal不等于accepted Snapshot或Task成功 |
| `PreflightAllowlistBinding` | `frozen / S05-T014..19` | 将exact selector/source-acquisition-clean适用面绑定到code-owned validator/check-set版本与digest的内部准入定义；allowlist只授予preflight通过后的自动资格 |
| `PreflightValidator` | `frozen / S05-T016..18` | 只读取当前Execution frozen acquisition/collection/clean evidence并返回`passed|blocked`的code-owned确定性检查器；不重新fetch/clean，无network/secret/path/state mutation权 |
| `PreflightValidatorManifest` | `frozen / S05-T027..28` | 随代码发布的minimal immutable registry manifest，记录identity、handler、applicability、input/output schemas、ordered check-set与implementation/manifest digests；无外部CRUD/plugin/runtime selfTest |
| `PreflightOutcome` | `frozen / S05-T015..18` | 绑定exact Execution/fence、candidate root、S05 binding、validator/check-set与ordered check evidence的durable`passed|blocked`事实；runtime/schema/evidence错误不是blocked Outcome |
| `ExecutionGate` | `frozen / S05-T020..24` | clean后/RAG前只有确实等待人工时创建的Execution-owned durable gate，状态为`open→released|rejected|superseded`；Process不持lease等待，Intake不拥有该状态 |
| `ExecutionReviewTarget` | `frozen / S05-T021` | gate绑定的exact复合审核对象，冻结team/task/Execution generation/fence、Workflow、Intake refs、CleanArtifact digest、PreflightOutcome/check-set与target digest |
| `ExecutionGateDecision` | `frozen / S05-T023..24` | append-only人工决定，必须校验authority、expected gate/Execution revision、fence与ReviewTarget digest，并与gate/Execution CAS及outbox同事务提交 |
| `S05Binding` / `s05_binding_digest` | `frozen / S05-T025..26` | Execution创建时锁定本次source/acquisition/clean/preflight exact refs的聚合binding；retry/recovery/human resume不得重新resolve active版本 |
| `CanonicalAcceptancePoint` | `frozen / T-O-38/T-O-43` | sealed CandidateSet原子成为Snapshot、Item/Revision decision、Membership、ChangeSet与child intent的唯一事务线性化点 | queue、IntakeArtifact write、Process log或分页staging都不是canonical acceptance |
| `IntakeChangeSet` | `frozen / T-O-38..39` | S04 从 durable comparison 生成的 immutable typed facts，描述 Item/Revision/semantic-key/no-change/absence 变化，但不指定 Process 名称 |
| `ActionDefinition` | `frozen / T-O-35/T-O-36/T-O-40` | 内部注册、不可变版本化的 Intake action/reason 定义，必须映射到受约束 core effect、precondition 和 typed route fact |
| `CoreEffect` | `frozen / T-O-40` | S04 状态机允许 action 组合的有限 pointer/lifecycle effect；新 action 不得自造任意字段 mutation |
| `PayloadExtra` / `payload_extra` | `frozen cross-database rule / S01-T040..41 + T-O-37` | 所有 MKB-owned 持久业务表必须存在的非空默认 `{}` 灵活 JSON object，只承接非权威开发期扩展；引擎/第三方私表不强改，关键语义必须晋升正式 schema 或注册定义 |
| `ReferenceAnchor` | `frozen / T-O-42` | 只提供行为考古、生产踩坑、设计 rationale 或反例支持的证据源；不形成 runtime/schema/API/data/acceptance 依赖。legacy-family 在 MKB 中只能处于此地位 |
| `GreenfieldBootstrap` | `frozen / T-O-47` | MKB从全新空数据库确定性、幂等创建自身schema、registry seed和readiness truth的过程；不读取legacy-family |
| `RegistryManifest` | `frozen / T-O-47` | 确定性注册SemanticDefinition、ActionDefinition及Workflow references的immutable versioned manifest与digest | 不等于ProcessCapabilityManifest或SkillWorkerManifest；同版本异digest必须fail-loud |
| `MKBSchemaEvolution` | `frozen / T-O-48` | MKB发布版本之间forward-only、版本化、可审计的自身schema演进 | 与legacy migration/compatibility无关；backfill不得重解释历史definition |
| `LatestRevision` | `frozen / T-O-34` | 最新 accepted IntakeRevision 候选，不保证已完成下游构建 |
| `ServingRevision` | `frozen / T-O-34` | 当前 proof-valid、允许下游读取/检索的 IntakeRevision；不等于未来 Knowledge publication |
| `Tombstone` | `frozen principle / T-O-35` | 已提交的 logical deletion/withdrawal fence，先阻止业务暴露，再等待物理清理收敛 |
| `RetentionFence` | `frozen / T-O-46` | 由latest/serving、rollback grace、active lineage、hold、cleanup intent及派生引用共同形成的物理删除禁止条件 | 不能由`payload_extra.retention`或单一时间戳替代 |
| `CleanupIntent` | `frozen / T-O-46` | 针对一个eligible target声明required substrate set、policy/reference snapshot与causation的durable清理要求 | 不拥有Process retry状态，不改变Item lifecycle |
| `CleanupProof` | `frozen / T-O-46` | 某一relationship/vector/artifact/derived substrate已按目标digest完成清理的可验证证据 | 单一substrate proof不等于整体physical purge complete |
| `PhysicalPurgeComplete` | `frozen / T-O-46` | 全部required CleanupProof均验证完成后的聚合事实 | 不反向恢复serving、不删除最小tombstone/audit skeleton |
| `DerivedGeneration` | `frozen distinction / T-O-32/T-O-45..46` | 同一IntakeRevision在Workflow/model/index变更或rebuild下产生的一次派生构建代次 | 不等于IntakeRevision或TaskGeneration；失败不得污染旧serving generation |
| `Lineage` / `Provenance` | `frozen principle` | 对来源、修订、生产运行、配置和派生对象的显式可查询关系；日志文本不构成 SSOT |

### 3.4 S04 端口词汇

| Canonical term | 成熟度 | 唯一职责 | 禁止误用 |
|---|---|---|---|
| `CandidateSetStagingPort` | `frozen boundary / S04-v1.1` | 接受IntakeCandidateSet page append、seal与abandon，并执行size/digest/Execution/S05 binding/preflight fence校验 | 不接受业务truth直写；sealed candidate仍不是IntakeSnapshot |
| `IntakeAcceptancePort` | `frozen boundary / S04-v1.1` | 将sealed candidate ref幂等提交为accepted IntakeSnapshot、IntakeChangeSet及同事务child scheduling intents | queue wake或Process success不能替代该线性化点 |
| `IntakeReadPort` | `frozen boundary / S04-v1.0` | 提供team-scoped Intake identities、membership、semantic与transition truth只读查询 | 不开放绕过state machine的mutation |
| `IntakeTransitionPort` | `frozen boundary / S04-v1.0` | 接收versioned action、expected pointers/state、proof/policy与causation，并执行受围栏CAS transition | 不执行物理Artifact/vector清理，不允许任意字段patch |
| `IntakeEligibilityPort` | `frozen boundary / S04-v1.0` | 验证exact team、IntakeItem lifecycle、ServingRevision与派生generation检索围栏 | vector row存在不等于eligible |
| `IntakeCleanupPort` | `frozen boundary / S04-v1.0` | 提供CleanupIntent读取、逐substrate CleanupProof提交与PhysicalPurgeComplete聚合读取 | 不拥有Process retry，也不改变IntakeItem lifecycle |
| `IntakeRegistryPort` | `frozen boundary / S04-v1.0` | 供bootstrap/internal compiler确定性注册并只读获取SemanticDefinition/ActionDefinition | 不提供外部CRUD，不接受同版本异digest覆写 |

### 3.5 Intake lifecycle 与 runtime 的分界

| 发生的事情 | 是否新建 Snapshot | 是否新建 Item | 是否新建 Revision | 是否新建运行对象 |
|---|---:|---:|---:|---:|
| 来源观察失败 | 否 | 否 | 否 | 是，记录失败 Outcome/Event |
| accepted complete/partial 观察 | 是 | 视 resolver | 视 revision decision | 是 |
| 同 external key 且业务语义不变 | 是 | 否 | 否 | 是，可 no-op 结束 |
| 同 external key 且业务语义改变 | 是 | 否 | 是 | 是，构建新 revision |
| force rebuild / 派生物修复 | 否或复用既有 provenance | 否 | 否 | 是，新 Task/Execution/build lineage |
| Workflow/model/embed upgrade | 否 | 否 | 否 | 是，新派生 generation/space |
| deactivate/delete | 否 | 否 | 否 | 是，执行独立资源 command并推进 Item lifecycle |

该矩阵、exact acceptance、三态lifecycle、ActionDefinition/CoreEffect、large-scatter recovery、retention/purge与greenfield governance已由`T-O-30..48`及S04-v1.1冻结；S05-v1.0进一步冻结candidate/preflight输入，但不改变矩阵。

---

## 4. LS-RAG 与派生资产词汇

| Canonical term | 成熟度 | 定义 | 与 Intake 的关系 |
|---|---|---|---|
| `DerivedAsset` | `frozen category / exact types downstream` | 从exact IntakeRevision经Workflow/Process构建的长期派生对象统称；具体类型必须使用LSRagBlock、ConstructionUnit、VectorRecord等领域名 | 不等于IntakeArtifact、Process output或KnowledgeItem；重建通常创建DerivedGeneration而非IntakeRevision |
| `ArtifactStorage` / `AssetStorage` | `pending S13` | 保存IntakeArtifact bytes及其他derived asset bytes/locators的基础设施职责名 | 不是业务identity类型；backend变化不得改变Intake UUID或logical refs |
| `LSRagBlock` | `pending S06` | layered structured content 中带稳定坐标的块 | 必须引用 exact IntakeRevision；不是 IntakeArtifact |
| `ConstructionUnit` | `pending S07` | original/summary 双通道及 meta fusion 的构造单元 | 从 IntakeRevision/Block 派生；exact schema 由 S07 |
| `OriginalChannel` | `pending S07` | 检索结果最终 payload 所回溯的原始内容通道 | 引用稳定坐标和 IntakeRevision |
| `SummaryChannel` | `pending S07` | 用于语义索引的摘要通道 | 只作索引表达；命中后回溯 OriginalChannel |
| `EmbeddingSpace` | `pending S08` | model/revision/dimension/metric/normalization 一致的向量空间 | 同一 IntakeRevision 可有多个派生 generation/space |
| `VectorRecord` | `pending S08-S09` | 与 Block/ConstructionUnit、embedding space 和 filter metadata 绑定的索引记录 | 必须引用 exact IntakeRevision；不是 Process row或 IntakeArtifact |
| `IndexGeneration` | `frozen lifecycle / exact schema pending S09` | 一组隔离构建、验证、CAS切换、grace后失效的vector index projection代次 | reindex不创建IntakeRevision；失败继续服务旧generation |
| `RetrievalEligibility` | `frozen fence / exact query pending S09-S10` | team、IntakeItem lifecycle、ServingRevision与IndexGeneration共同形成的查询围栏 | 不能仅由vector是否存在或Task成功决定 |

---

## 5. 为未来保留的 Knowledge 命名空间

| Reserved term | 成熟度 | 允许的未来语义 | 当前禁令 |
|---|---|---|---|
| `KnowledgeItem` | `reserved` | 由一个或多个 IntakeItem/Revision 经 promotion、fusion、curation 或 semantic identity resolution 形成的知识身份 | 不得作为 IntakeItem 的别名、重命名或 1:1 默认投影；当前不建表、不开放 API |
| `KnowledgeRevision` | `reserved` | KnowledgeItem 自己的不可变语义修订 | 不得拿来表示 IntakeRevision 或模型重建 generation |
| `KnowledgeArtifact` | `reserved` | 未来 Knowledge 层特有表示，是否需要尚未裁决 | 不得作为 IntakeArtifact 的泛化父类 |

保留命名空间的目的，是允许未来在“获取了什么”和“系统认定/融合成什么知识”之间建立明确语义边界，而不是承诺一定建设 Knowledge domain。

---

## 6. 旧词与歧义词治理

### 6.1 退役词映射

| 旧词 | 状态 | 新语境中的处理 |
|---|---|---|
| `file_uuid` | `legacy-only / ambiguous` | 无一对一映射。必须依据上下文拆为 IntakeSource、IntakeSnapshot、IntakeItem、IntakeRevision、IntakeArtifact 或 runtime UUID |
| `file` | `legacy-only as business identity` | 禁止作为表/业务类型；只有 `original_filename` 等明确物理属性可保留普通词义 |
| `Source` | `retired S04 shorthand` | 摄入资产类型必须写`IntakeSource`；Workflow值来源必须写`BindingSource`，注册来源必须写`RegistrationOrigin`；自然语言普通“来源”不受限 |
| `SourceObservation` / `Source Observation` | `retired candidate` | 由 `IntakeSnapshot` 取代 |
| `SourceManifest` | `retired aggregate shorthand` | Snapshot集合事实由`IntakeSnapshot + IntakeSnapshotMembership`表达；只读collection summary可作为derived view或IntakeArtifact representation |
| `Document` | `retired canonical alias` | D01/S01-S03正式Spec已校准；当前MKB schema/API/event必须依据语境写IntakeItem或具体LS-RAG类型，历史QNA可保留原词 |
| `DocumentVersion` | `retired canonical alias` | 当前MKB长期摄入语义使用`IntakeRevision`；不得作为wire/schema兼容别名 |
| `Artifact` | `too broad` | Intake 表示必须称 `IntakeArtifact`；Block/Vector 等保留自己的领域名；普通“产物”不能自动成为业务类型 |
| `parent file` | `legacy-only` | scatter 集合 parent 解析为 IntakeSource + IntakeSnapshot；业务 child 为 IntakeItem |
| `child file` | `legacy-only` | 根据上下文解析为 IntakeItem、SnapshotMembership 或 child Execution，禁止混用 |
| `atomic_id` | `legacy-only field name` | 作为 provider external key 的输入证据；新 canonical 字段为 source-scoped `external_key` |
| `clean/rag process table` | `legacy-only` | 统一为 S03 Process + typed Workflow step/capability；长期内容进入 Intake/LS-RAG 资产表 |
| `ConsumableTask` | `legacy-only` | legacy worker对单个step work item的称呼；MKB中依据语境拆为ProcessCommand或可claim的Process，不得作为外部Task别名 |

### 6.2 禁止的命名捷径

- 禁止用裸 `item_uuid`、`source_uuid`、`revision_uuid`、`artifact_uuid` 作为跨域持久化字段；必须使用完整前缀，例如 `intake_item_uuid`。
- 禁止以 digest、URL、path、R2 key、queue message ID 或 provider key 直接替代 MKB UUID。
- 禁止让同一个 `status` 同时表示 runtime progress、Intake lifecycle、serving eligibility 和 physical GC。
- 禁止将JSON payload当作关系、状态机、路由或身份真相；JSON可以是已验证输入、IntakeArtifact表示或derived compiled view。
- 禁止用 `latest` 暗示 `serving`，或用 `deleted` 暗示 bytes/vector 已物理清空。
- 禁止把 `Knowledge` 作为营销性前缀提前覆盖 Intake 事实。

---

## 7. UUID、字段与状态命名约定

### 7.1 UUID

| 对象 | Canonical field |
|---|---|
| Task | `task_uuid` |
| Execution | `execution_uuid` |
| Process | `process_uuid` |
| Workflow revision | `workflow_revision_uuid` |
| Intake source | `intake_source_uuid` |
| Intake snapshot | `intake_snapshot_uuid` |
| Intake item | `intake_item_uuid` |
| Intake revision | `intake_revision_uuid` |
| Intake artifact | `intake_artifact_uuid` |
| Preflight outcome | `preflight_outcome_uuid` |
| Execution gate | `execution_gate_uuid` |
| Gate decision | `gate_decision_uuid` |

边界可接受 UUIDv4/v7，MKB 内生 UUID 使用 UUIDv7，这是 S01 已冻结约束。任何 team-owned lookup 仍必须显式携带 `team_uuid`。

### 7.2 时间、摘要与引用

- 时间使用动作语义：`created_at`、`accepted_at`、`published_at`、`deactivated_at`、`deleted_at`；不得只用模糊 `updated_at` 解释状态转移。
- digest 字段必须指出 scope：`source_repr_digest`、`canonical_content_digest`、`context_meta_digest`、`filter_meta_digest`；每个摘要必须可追溯 algorithm/version。
- 运行对象引用长期资产时使用 logical UUID + optional expected digest/revision，不传本地绝对路径作为业务契约。
- 物理位置使用 `locator`/backend reference，由 S13 定义；`path` 只允许存在于本地 adapter 内部。

### 7.3 状态分域

| 状态族 | Owner | 示例边界 |
|---|---|---|
| Task aggregate state | S02 | 对外六态；不混入 clean/rag stage |
| Execution/Process runtime state | S03 | claim、running、retry、cancel、terminal |
| Execution human gate state | S05（状态投影仍由S03 Execution承接） | `open/released/rejected/superseded`只描述gate；Execution使用既有`waiting`，Intake无review state |
| Workflow phase/reason | S03 | 与 runtime state 正交 |
| IntakeItem lifecycle | S04 | `active/deactivated/deleted` 三态已由 `T-O-40` 冻结；业务原因由 versioned ActionDefinition 表达 |
| Revision serving/build projection | S04 + S03/S09 | latest、serving、proof/derived generation 分离 |
| IntakeArtifact/Vector physical state | S09/S13 | materialized、invalidated、purged等不得决定业务可见性 |

### 7.4 `payload_extra` 跨数据库契约

| 规则面 | 冻结约束 |
|---|---|
| Presence | 所有 MKB-owned canonical、runtime、registry、projection、staging、outbox、audit、repair 与业务 migration 表必须包含 `payload_extra` |
| Exclusions | schema migration bookkeeping、Turso/SQLite 引擎内部表、虚拟向量表、FTS shadow 表和第三方组件私有表继承 `S01-T041` 例外 |
| Logical type | 非空 JSON object，默认 `{}`；exact Turso type、JSON validity CHECK、size limit 和 serializer 由 S12 冻结 |
| Permitted use | 调试上下文、provider 非关键字段、尚在实验且不影响业务判断的扩展值 |
| Forbidden truth | identity、FK/relation、required state、CAS/fencing、proof、auth、idempotency、route condition、indexed filter、public contract、secret、无界正文和 bytes |
| Immutable rows | `payload_extra` 随宿主 Snapshot/Revision/Membership/definition/transition/audit row 一起不可变；修正必须追加新 truth |
| Mutable rows | 只能在宿主的正常 CAS + audit transaction 中修改，不能提供独立 patch 后门 |
| Fingerprint | 默认不参与 Snapshot seal、Revision fingerprint、semantic diff、route 或 proof；需要参与时必须先晋升 |
| Promotion | 某 key 一旦成为必填、可查询、可路由、可授权或影响状态，必须建立正式列或 versioned SemanticDefinition/ActionDefinition，显式迁移并停止把 extra key 当业务真相 |
| Governance | S12/S15 应统计 key/size/读取依赖；未注册 key 被 route/filter/state 读取时 fail-loud |

---

## 8. Cross-Spec Alignment Outcome

| 权威文档 | 校准结果 | 版本 / 状态 |
|---|---|---|
| `domain-truth/D01-task-execution-process-flow.md` | Intake/runtime分离；Preflight归Process、human gate归Execution waiting、S05 binding不热切；无第四层runtime identity | `D01-v1.3 / completed` |
| `domain-truth/S01-skill-worker-integration.md` | Intake词汇、polling action_required与Task-scoped gate decision；仍无直接Execution/Process写面 | `S01-v1.4 / completed` |
| `domain-truth/S02-task-api.md` | 六态不变；running+action_required、gate list/get/decide与required rejection collect-all | `S02-v1.2 / completed` |
| `domain-truth/S03-workflow-engine.md` | preflight capability、human_review wait reason、S05 binding与四窗口repair；七表/八态不变 | `S03-v1.2 / completed` |
| `domain-truth/S04-intake-asset-lifecycle.md` | CandidateSet exact producer contract、ExternalKey/digest与Preflight/acceptance顺序按S05补全；五类identity与十表SSOT不变 | `S04-v1.1 / completed` |
| `domain-truth/S05-intake-cleaning.md` | 四类source、typed acquisition/candidate/clean、canonicalization、mandatory preflight、ExecutionGate与binding词汇进入正式权威 | `S05-v1.0 / completed` |
| `qna-truth/S02.md`、`qna-truth/S03.md` | 保留owner问答历史原词，不作为当前schema/API词汇权威 | `historical / intentionally unchanged` |

所有后续实现与Spec遵守：

1. 当前canonical contract只使用本glossary和正式Domain Truth中的新词；
2. legacy-family只引用evidence/rationale，不建设compatibility adapter、importer、dual-read或数据翻译；
3. 历史QNA中的旧词按对应正式Spec解释，不反向恢复兼容alias；
4. 新增无法归类的领域词必须先登记glossary，再进入schema/API/event。

---

## 9. 修订历史

| 版本 | 日期 | 变更 |
|---|---|---|
| `v0.1` | `2026-07-15` | 建立实际词汇手册；汇总 frozen runtime/workflow 词汇；采用 owner 指定的五个 Intake 核心词；保留 Knowledge 命名空间；冻结旧词治理规则和 D01/S01-S03 延后迁移纪律。 |
| `v0.2` | `2026-07-15` | 接收 S04 Round 1 `T-O-30..35`；将五类 Intake identity、membership、Revision、latest/serving 与 tombstone 原则更新为 frozen；登记 versioned SemanticDefinition/ActionDefinition、IntakeCandidateSet/ChangeSet 与 CoreEffect 作为 Round 2 execution 词汇。 |
| `v0.3` | `2026-07-15` | 接收 S04 Round 2 `T-O-36..41`；冻结十表 relational truth、CandidateSet/ChangeSet、三态 lifecycle/CoreEffect/ActionDefinition；继承 `S01-T040/T041`，将所有 MKB-owned 持久业务表强制 `payload_extra` 及其例外、禁区、晋升和治理规则登记为跨系统基线。 |
| `v0.4` | `2026-07-15` | 接收 `T-O-42`：MKB 与 legacy-family 完全独立，legacy 仅为 ReferenceAnchor；登记 GreenfieldBootstrap/MKBSchemaEvolution，移除 payload_extra legacy-raw 用途，并将 Deferred Migration Register 更名为 MKB 内部 Cross-Spec Alignment Register。 |
| `v1.0` | `2026-07-15` | 接收S04 Q7-Q9 / `T-O-43..48`与S04-v1.0；冻结CandidateSet seal/acceptance、recovery、retention/cleanup、greenfield governance词汇；补登记RequestIntent、TaskAudit、ProcessCapabilityManifest、SkillWorkerManifest、BindingSource、RegistrationOrigin、S04 ports、IntakeItemTransition、CAS/Fence/Outbox/Readiness及legacy ConsumableTask；记录D01/S01-S03对齐完成。 |
| `v1.1` | `2026-07-16` | 接收S05 Q1-Q10 / `T-O-49..76`与S05-v1.0；冻结四类source kind、ExternalKey normalizer、SHA-256/JCS/NFC digest、四类typed output、PreflightValidator/Outcome、ExecutionGate/ReviewTarget/Decision与S05Binding；记录D01/S01-S04按S05完成边界校准。 |
