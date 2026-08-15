# MKB Scope & Glossary

> **项目**：`myknowledgebase`（MKB）
>
> **文档角色**：跨规格词汇手册、命名边界与对齐登记册
>
> **权威输入**：D01–D08、S01–S16
>
> **状态**：`active / S14-S16-v1.1 calibrated / D08-calibrated`
>
> **版本 / 日期**：`v2.9 / 2026-08-13`

## 0. 使用规则

本手册解决三个问题：同一个名词在 MKB 中只能表达什么、不能表达什么，以及旧词如何迁移。它不取代各 Domain Truth 的完整 schema、状态机和 API Contract。

词汇成熟度分为：

| 标记 | 含义 |
|---|---|
| `frozen` | 已由 owner 在 D01 或 S01-S06 QNA 的已接受 Truth 中冻结；本手册只转述，不改变原裁决 |
| `owner-directed / designing` | 名称由owner指定，但其exact职责仍在尚未完成的下游Spec中设计 |
| `reserved` | 仅保留命名空间；当前不得建表、暴露 API 或作为现有对象别名 |
| `derived` | 由权威真相编译、投影或构建，可重建，不反向成为 SSOT |
| `legacy-only` | 只用于代码考古、生产踩坑或reference rationale，禁止进入MKB canonical schema/runtime |
| `retired candidate` | 曾在未冻结设计中使用，已被新词取代 |

约束：

1. 新 schema、API 和事件必须使用本手册的 canonical term；无法归类时先更新词汇手册，不得临时复用 `file`、`document`、`artifact` 等宽泛名词。
2. Domain Truth 的 exact 定义优先于本手册摘要；发现冲突必须显式修订，禁止靠同义词绕过 Truth Gate。
3. D01与S01-S05已按D02完成既有Truth的状态边界审计；D02-v1.0冻结共有域ledger角色、六StateFamily、六项镜像块和citation/semantic drift协议。历史QNA/legacy code anchor可保留旧词；当前正式Spec、schema、API与event不得继续把`Document`当canonical alias，也不得让S05重建独立runtime或Intake lifecycle。D02 non-normative Appendix中的`OPEN/PROPOSED/CONFLICT`仍不是frozen词汇。
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
| `RequestIntent` / `request_intent` | `frozen / S01-v1.5` | Task对外资源动作的严格discriminator；v1为`intake.ingest/rebuild/update_metadata/deactivate/delete`与`index.rebuild` | request intent不是Workflow/Process分类；`task_type`不是兼容别名 |
| `TaskAudit` | `frozen / S01` | 与Task 1:1原子保存的immutable上游业务审查快照 | `(team_uuid, task_uuid)` | 不等于MKB Event/Log，也不由Task PATCH修改 |
| `TaskGeneration` | `frozen` | 同一 Task 在 full retry 下的有序 root execution generation | Task 内 generation ordinal/ref | 不等于 IntakeRevision；automatic Process retry 不创建 generation |
| `TaskItem` | `frozen / projection` | scatter generation与IntakeSnapshot/ChangeSet下的有界结果项，供API分页与聚合 | Task/generation/Intake item projection key | 不成为IntakeItem、Membership或canonical asset SSOT |
| `TaskRestart` | `frozen` | 独立、append-only的full retry/atomic IntakeItem rebuild因果与admission记录 | restart UUID + source/target refs | 不复制Task状态；其状态由关联Task join得出 |
| `Execution` | `frozen` | 一次 durable workflow run，是执行阶段唯一内部查询 UUID；single root 或 scatter root/child 均使用该对象 | `execution_uuid` | 对外 Task identity、具体工序 attempt、长期 Intake identity |
| `Process` | `frozen` | 一个 Workflow step 在某 Execution 中的 durable 工序实例，拥有 claim/lease/fencing/retry 与 I/O outcome | `process_uuid` | 长期资产身份；Process projection 可清理，但其证明引用必须保留 |
| `Workflow` | `frozen` | MKB 内部注册、声明式、关系 schema 为 SSOT 的执行定义 | workflow key + immutable revision | v1 不允许外部/agent CUD，也不是 Task 生命周期 |
| `WorkflowRevision` | `frozen` | 已注册 Workflow 的不可变定义版本；Execution 创建时固定绑定 | workflow revision UUID/key | registry 更新不得热改已存在 Execution |
| `CompiledWorkflowJSON` | `derived` | 由关系型 Workflow truth 确定性编译的只读声明式 JSON | compiler/schema/digest 标识 | 不得反向编辑或成为 Workflow SSOT |
| `ProcessCapabilityManifest` | `frozen / S03-v1.3` | 由MKB内部code registry持有的versioned Process contract，定义process key、typed ports/parameters、outcome/proof、side-effect和idempotency语义 | process key + contract version + digest | 不是外部skill manifest，不是第八张Workflow truth表，不承载一次Process状态 |
| `SkillWorkerManifest` | `deferred / S01-v1.5` | 未来防腐adapter可能向03-nano/skill-worker生态投影的外部能力声明 | 由MKB capability read model确定性派生；exact schema届时由adapter Spec冻结 | v1不存在该对象或生命周期；不得作为启动依赖、MKB domain SSOT、ProcessCapabilityManifest或RegistryManifest的别名 |
| `BindingSource` | `frozen / S03-v1.3` | Workflow binding中某个typed值的来源类别，如execution context、IntakeSnapshot、prior output、control value、registry ref或literal | binding row + exact source fields | 不等于IntakeSource；禁止再用裸`Source`作为业务类型名 |
| `RegistrationOrigin` | `frozen / S03-v1.3` | Workflow/definition由code、migration或bootstrap注册的provenance | module/commit/migration/fingerprint refs | 不等于IntakeSource或user identity |
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

### 2.3 状态族与正交事实

| Canonical term | 成熟度 | 定义 | 禁止误用 |
|---|---|---|---|
| `StateFamily` | `frozen / D02 T-O-88` | 由一个domain唯一拥有、具有自身合法边与写入guard的一组状态；v1只有Task、Execution、Process、IntakeItem、CandidateSet与ExecutionGate六个StateFamily | 不得建立第七个、跨owner的`production_status`或stage-specific/组合状态；D02 Appendix或下游开放设计不因本词条自动冻结 |
| `D02 State Ledger` | `frozen / D02 T-O-86..92` | MKB共有域状态宪法与镜像ledger，保存上层形状、非法行为及下游已冻结状态Truth的可核对六项镜像块 | 不是runtime identity、数据库、route engine或所有domain的执行总Spec；non-normative Appendix不得生成contract |
| `StateContractMirrorBlock` | `frozen / D02 T-O-91` | 下游状态Truth回填D02的唯一Markdown单元，固定包含权威来源、所有权、exact状态/边或not-a-state声明、跨域输入输出、非法行为、校准影响 | 不复制完整schema、算法、DDL、API、风险或实现计划 |
| `CitationDrift` | `frozen / D02 T-O-92` | source version、章节或链接变化而语义完全不变的引用漂移，可在同一校准变更中机械修正 | 不得用此标签掩盖name、owner、enum、合法边或分类变化 |
| `SemanticDrift` | `frozen / D02 T-O-92` | canonical name、owner、enum、合法边、state-vs-fact或非法行为发生差异 | 必须显式登记并在同一校准工作单元双向更新；新分支在关闭前fail-closed |
| `ControlStatus` | `frozen distinction` | 回答一个runtime identity当前能否claim、推进、等待、取消或终结；Task/Execution/Process各有exact enum | 不等于业务phase、Outcome、readiness或资产lifecycle |
| `BusinessPhase` / `phase_key` | `frozen / S03` | 由bound route与active Process set确定性归约的Execution业务焦点，如cleaning/structurizing；terminal保留last phase | 不创建stage-specific状态机，不进入Task status |
| `WaitingReason` | `frozen / S03` | Execution处于waiting时必须绑定的typed durable trigger类别与ref | 不等于新状态；无ref的generic pending非法 |
| `BusinessOutcome` | `frozen distinction` | Process、preflight、acquisition或membership产生的immutable typed判断，经过owner guard后才能影响route/state | handler返回或Outcome值本身不自动成为current status |
| `StagingState` | `frozen distinction / S04-S05` | 候选集合在canonical acceptance前的资格生命周期；v1 CandidateSet为open/sealed/accepted/abandoned | 不等于Process status或IntakeSnapshot state |
| `SelectionPointer` | `frozen principle / exact families owned downstream` | 通过CAS选择一个exact immutable target的指针族，如latest Revision、serving Revision或GenerationArtifact current | 不得用裸latest/current混用不同owner，也不等于lifecycle |
| `ResultReadiness` | `frozen / S02` | Task result endpoint的`not_ready/ready/terminal_failed/terminal_cancelled`响应事实 | 不得作为第七个Task状态 |
| `FailureDisposition` | `frozen distinction / S03` | terminal/guard失败后的分类、隔离或下一处理方式 | `quarantined/remediating`不得偷偷变成第九个Execution/Process状态 |

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
| `ExternalKey` / `external_key` | `frozen / S04-v1.2+S05-v1.1` | 外部provider对某一业务项的稳定键，只能在team + IntakeSource namespace内解释；S05 source-specific pure normalizer输出normalized key、exact version/digest/evidence，缺失时不得随机UUID/content-hash fallback |
| `IntakeSnapshotMembership` | `frozen / T-O-31` | Snapshot 与 Item/Revision 之间的不可变集合事实，记录 seen/no-change/new-revision/absence 等 decision；不是上层业务资产 |
| `SnapshotCompleteness` | `frozen / T-O-31/T-O-35` | Snapshot 对声明 scope 的 `complete` 或 `partial` 事实；failure 不是第三种 Snapshot completeness |
| `AuthoritativeScope` | `frozen / T-O-31/T-O-35` | Snapshot 有权对哪个集合声明“本次完整”；只有 complete + authoritative 才可能依据 absence 推导失活 |
| `HTTPValidatorEvidence` | `frozen distinction / S05-v1.1` | ETag、Last-Modified等HTTP条件请求/一致性提示证据，不自动成为Revision identity、完整性证明或PreflightValidator |
| `Digest` | `frozen / S05-v1.1` | 带scope、SHA-256算法和canonicalization/schema/definition版本的内容或metadata摘要；JSON基线JCS，text基线UTF-8/LF/NFC；用于完整性/变更判断，不替代UUID、authority或identity |
| `IntakeSourceKindDefinition` | `frozen / S05-T004` | 内部注册、immutable versioned的source contract，绑定strict descriptor/config schemas、cardinality/completeness、capability eligibility、normalizer、budget与preflight eligibility |
| `ProviderDefinition` | `owner-directed / D08-v0.1` | `registered_api` 下 versioned provider 头（如 `chinatax`/`domain`/`realestate`）；**不是**第五类 source kind，也不是 `action_branch` |
| `ProviderOperation` | `owner-directed / D08-v0.1` | 某 provider 的精确 operation（request/envelope/member schema + normalizer + cardinality）；坐标 `(provider, operation, definition_version)`；不等于 live URL |
| `CleanStrategy` | `owner-directed / D08-v0.1` | 与 source kind 正交的清洗策略（`web.deterministic`/`web.llm_rewrite`/`web.browser_print_pdf`/`pdf.text_layer`/`pdf.document_understanding`/`doc.*`）；禁止组合 branch 名当 taxonomy |
| `FilterMeta` | `owner-directed / D08-v0.1` | registered_api member 的五维筛选面：`realm,type,channel,source_name,is_active`；晋升 SemanticDefinition；不等于 clean_text |
| `ContextMeta` | `owner-directed / D08-v0.1` | 复用 FilterMeta 五维 + `title` + `tags[]`，供 prompt/检索上下文；不等于 StructureDocument |
| `ContentDigest` / `MetaDigest` | `owner-directed / D08-v0.1` | member 正文维与效力/状态维的双 SHA-256；禁止随机 UUID 替代 ExternalKey |
| `action_branch` | `legacy-only` | legacy Worker 用组合字符串同时选 provider 与是否上 Gemini；**禁止**进入 MKB source_kind / workflow_key / 对外 descriptor |
| `AcquisitionEvidence` | `frozen / S05-T008` | 一次acquisition Process在exact Execution fence下形成的typed representation/media/encoding/redirect/page/budget证据；不是IntakeSnapshot或HTTP日志 |
| `IntakeCandidateMember` | `frozen / S05-T008` | CandidateSet内具有stable ordinal、ExternalKey evidence、canonical semantic tuples、Artifact/clean/validation refs的typed member；不是IntakeItem，需经S04 acceptance解析 |
| `CleanArtifactCandidate` | `frozen / S05-T008..10` | clean活动产出的staged typed descriptor，携带input/output digest、logical handle、capability/parser/model/prompt、producer fence、loss/quality与lineage；acceptance后才绑定canonical IntakeArtifact owner |
| `RevisionBasis` | `frozen / S05-T010` | source definition声明哪些确定性事实可参与IntakeRevision判断的versioned类别；v1基线为typed source semantics、deterministic canonical text或opaque representation，AI/OCR输出不能单独作为basis |
| `SemanticDefinition` | `frozen / T-O-33/T-O-36` | 内部注册、不可变版本化的语义维度定义，声明 value/schema kind、是否参与 Revision fingerprint 及其 typed route signal |
| `RevisionSemantic` | `frozen / T-O-36` | 某 IntakeRevision 对一个 exact SemanticDefinition version 的 canonical value digest/value-ref；normalized row 是 SSOT |
| `IntakeItemTransition` | `frozen / T-O-36/T-O-40` | IntakeItem 每次 lifecycle/pointer/action CAS 的 append-only 审计事实，绑定before/after state、action version、causation、fence与proof refs；对应`intake_item_transitions` | 不是Process状态、可变Item快照或普通Event文本 |
| `RevisionFingerprint` | `frozen principle / T-O-32..33/T-O-38` | 由该 Revision 绑定且参与 fingerprint 的 semantic definition/value tuples 确定性计算，用于幂等收敛 |
| `IntakeCandidateSet` | `frozen / S04-v1.2+S05-v1.1` | S05在S04 acceptance前产出的typed观察候选，包含scope/completeness、staged Artifact refs、ExternalKeys、canonical semantic values、rejection/gap evidence与PreflightOutcome；不是accepted Snapshot |
| `CandidateSetPage` | `frozen / S04-v1.2+S05-v1.1` | Large-scatter CandidateSet中具有stable ordinal、ordered member digests与SHA-256/JCS page digest的immutable staging分片；page不是独立Snapshot，缺页集合不得seal |
| `CandidateSetSeal` | `frozen / S04-v1.2+S05-v1.1` | pages/root digest、count/bytes、dedupe、Artifact refs、scope、rejection/gap与source-exhaustion proof通过后形成的immutable acceptance资格；seal不等于accepted Snapshot或Task成功 |
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
| `CandidateSetStagingPort` | `frozen boundary / S04-v1.2` | 接受IntakeCandidateSet page append、seal与abandon，并执行size/digest/Execution/S05 binding/preflight fence校验 | 不接受业务truth直写；sealed candidate仍不是IntakeSnapshot |
| `IntakeAcceptancePort` | `frozen boundary / S04-v1.2` | 将sealed candidate ref幂等提交为accepted IntakeSnapshot、IntakeChangeSet及同事务child scheduling intents | queue wake或Process success不能替代该线性化点 |
| `IntakeReadPort` | `frozen boundary / S04-v1.2` | 提供team-scoped Intake identities、membership、semantic与transition truth只读查询 | 不开放绕过state machine的mutation |
| `IntakeTransitionPort` | `frozen boundary / S04-v1.2` | 接收versioned action、expected pointers/state、proof/policy与causation，并执行受围栏CAS transition | 不执行物理Artifact/vector清理，不允许任意字段patch |
| `IntakeEligibilityPort` | `frozen boundary / S04-v1.2` | 验证exact team、IntakeItem lifecycle、ServingRevision与派生generation检索围栏 | vector row存在不等于eligible |
| `IntakeCleanupPort` | `frozen boundary / S04-v1.2` | 提供CleanupIntent读取、逐substrate CleanupProof提交与PhysicalPurgeComplete聚合读取 | 不拥有Process retry，也不改变IntakeItem lifecycle |
| `IntakeRegistryPort` | `frozen boundary / S04-v1.2` | 供bootstrap/internal compiler确定性注册并只读获取SemanticDefinition/ActionDefinition | 不提供外部CRUD，不接受同版本异digest覆写 |

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

该矩阵、exact acceptance、三态lifecycle、ActionDefinition/CoreEffect、large-scatter recovery、retention/purge与greenfield governance已由`T-O-30..48`冻结并由S04-v1.2承接；S05-v1.1进一步冻结candidate/preflight输入，但不改变矩阵。

---

## 4. LS-RAG 与派生资产词汇

> **高等级 handbook**：`domain-truth/D05-layered-semantic-rag-handbook.md`（**`D05-v1.0 frozen` / `T-O-202..210`**）。  
> **裁决等级**：`D*` > `S*`。  
> **typed 形状**：`src/contracts/`（D03）。  
> **失败重试**：不在 D05；见 **D01 / S03** `max_retries`。

### 4.0 产品核心词（D05-v1.0 / T-O-202..210）

| Canonical term | 成熟度 | 定义 | 边界 |
|---|---|---|---|
| `LS-RAG` | `frozen / D05-v1.0` | GenerationScopedCoordinate 为轴；**默认双通道**；**默认粒度 0/1/2**；g=0 **summary** 必入向量候选（g=0 original 留在 construct）；construct 合法后 vectorize；召回 Traceback + ContextTier | 不自建 max_retries；不新增 StateFamily |
| `LSRagProductionChain` | `frozen / D05-v1.0` | Intake→structurize→construct→**(gate)**→vectorize→publication→Retrieve | 禁跳过 construct |
| `DualChannel` | `frozen / D05-v1.0` | **LS-RAG 根本**：Original+Summary 默认可索引、共坐标 | 非可选插件 |
| `Granularity0` / `FullDocumentLayer` | `frozen / D05-v1.0` | **粒度 0**：整份文档根层全文检索单元；**必须**进入向量候选 | 生产 g=0；inflation 目标 |
| `Granularity1` / `SectionLayer` | `frozen / D05-v1.0` | **粒度 1**：一级章节/一级标题下连贯正文 | 例：预算报告「二、收入预算」整章 |
| `Granularity2` / `ParagraphLayer` | `frozen / D05-v1.0` | **粒度 2**：章内段落/条款/列表项组 | 例：「（三）非税收入」单段 |
| `DefaultGranularitySet` | `frozen / D05-v1.0` | v1 默认 **`{0,1,2}`** | 更细层须 profile 注册 |
| `GenerationScopedCoordinate` | `frozen / D05-v1.0` | generation + unit_id（+ granularity 元数据） | 禁裸三元组跨代 |
| `promptA` / `CleanPrompt` | `frozen / D05-v1.0` | **生产 Prompt 身份 A**：清洗；identity=`promptA.<variant>.<version>`；DB=`content_hash` 指针 | 锚定 S05 clean.*；正文 `data/prompts/intake/clean/**` |
| `promptB` / `StructurePrompt` | `frozen / D05-v1.0` | **生产 Prompt 身份 B**：结构化多粒度 original；`promptB.<variant>.<version>` + hash | 锚定 `lsrag.structurize`；legacy 例 `RAG_STRUCTURIZER_V1_GENERAL` |
| `promptC` / `SummaryPrompt` / `SummarizerPrompt` | `frozen / D05-v1.0` | **生产 Prompt 身份 C**：整包填 Summary 通道；`promptC.<variant>.<version>` + hash | 锚定 `lsrag.construct` Summarizer；legacy 例 `RAG:CONSTRUCTOR:GEMINI_SUMMARY:V2` |
| `PromptIdentity` | `frozen / D05-v1.0` | `prompt{A\|B\|C}.variant.version` 闭集角色 + 变体 + 代次 | 运行须 hash 校验；禁无名散落字符串 |
| `PromptRef` | `frozen / D05-v1.0` | `{ identity, content_hash, path? }`；进入 ProcessCommand digest | DB 不存第二份正文（D03） |
| `ConstructToVectorizeGate` | `frozen / D05-v1.0` | full_valid construct + dual-channel 完备 + g=0 在场后才可 vectorize | 原料门闩 |
| `VectorizationUnit` | `frozen / D05-v1.0` | team×coord×channel×content_full_digest×LayerA/B | 非 Process row |
| `ContentFull` | `frozen / D05-v1.0` | Recipe 输出 embed 文本；非 identity；非向量表列 | D04 禁列 |
| `Traceback` | `frozen / D05 + S10-v1.0 / T-O-258` | summary 命中→同 generation-scoped original→PayloadContent；status 可观测 | 与 HitContent 分账 |
| `DocumentInflation` | `frozen / D05 + S10-v1.0 / T-O-258/261` | 非 g=0 命中后有界附加 FullDocument original | 默认 roots=3 / 8k chars |
| `HitContent` / `PayloadContent` | `frozen / D05-v1.0` | 命中正文 vs 交付正文 | 禁静默伪装 |
| `TracebackStatus` | `frozen / D05-v1.0` | `not_needed\|resolved\|failed\|degraded` | 默认可观测 degraded |
| `RetrievalResult` | `frozen / D05 + S10-v1.0 / T-O-254/261` | 含 granularity、分账、traceback、context_tier、ann/rerank scores | Eligibility 围栏；无 raw vector |
| `ContextTier` | `frozen / D05-v1.0` | `focus_fragment` / `document_root` / assembly | 前端多等级上下文 |
| `PublicationProof` | `frozen / D05 + S09-v1.0 / T-O-242` | 类型化上线证据；`index.publication.v1`；S04 serving CAS 输入 | ≠ 向量存在；≠ Handoff；≠ `publication_state`  alone |
| `ContextMetaProjection` | `frozen / D05-v1.0` | 叙事 meta 投影 | 非 filter SSOT |
| `FilterMetaAuthority` | `frozen / D05-v1.0` | S04+team 过滤权威 | child 不串 parent |

### 4.1 派生资产与通道（S06/S07 + D05）

| Canonical term | 成熟度 | 定义 | 与 Intake 的关系 |
|---|---|---|---|
| `DerivedAsset` | `frozen category` | 从 exact IntakeRevision 经 Workflow/Process 构建的长期派生对象统称 | ≠ IntakeArtifact；重建通常新 generation |
| `StructureDocument` | `frozen / S06 / T-O-94` | original structure truth：single-root tree + anchors + proofs | 不含权威 summary |
| `RetrievalBlockProjection` | `frozen / S06 / T-O-94` | 检索投影；generation-scoped blocks | 不得反向改 tree |
| `LSRagBlock` | `frozen / S06` | Projection 内带坐标的块 | 经 structure generation 追溯 |
| `ConstructionUnit` | `frozen / S07 / T-O-132` | 与 projection 1:1 的双通道单元 | 非独立 Process 成败 |
| `OriginalChannel` | `frozen / S07 / T-O-128/129` | 可复验原文通道 | 禁模型写 |
| `SummaryChannel` | `frozen / S07 / T-O-128/138` | 语义摘要通道 | 不在 S06 kernel；v1 整包 dual-channel 完备才 CAS |
| `ConstructionDocument` | `frozen / S07 / T-O-135` | 整包 envelope artifact | 与 DualChannelProjection 分账 |
| `DualChannelProjection` | `frozen / S07 / T-O-135` | 按 coordinate 枚举双通道记录 | S08 消费面 |
| `ConstructionSchemaDefinition` | `frozen / S07 / T-O-135` | construction contract key/version/digest | readiness 前注册 |
| `ContentFullRecipe` | `frozen / S07 / T-O-137` | 确定性 ContentFull 配方 | S08 可重算 |
| `ConstructMode` | `frozen / S07 / T-O-137/139` | `full_construct` \| `metadata_refresh` | 非 step-name |
| `EmbeddingSpace` / `VectorNamespace` | `frozen / D04+S11+S08` | model/dim/metric 一致的向量空间（Layer A） | 粒度/通道不是 namespace |
| `VectorRecord` | `frozen / D04+S08-v1.0` | `mkb_vector_records` 行：坐标+channel+embedding+Layer B 抄写 | 须绑 generation；非 Process row |
| `LsragVectorizeCapability` | `frozen / S08-v1.0 / T-O-221` | Process key **`lsrag.vectorize`**；mode=`from_construct`\|`purge_generation` | **废止**生产键 `lsrag.vectorize_index` |
| `VectorizeCommand` / `VectorizeOutcome` | `frozen / S08-v1.0 / T-O-225` | typed Command + digest；成功仅 `disposition=full_valid` | 禁 outbox done 冒充成功 |
| `VectorizeHandoffV1` | `frozen / S08-v1.0 / T-O-230` | Outcome 写证明交接包（generation/namespace/model/counts） | **非** PublicationProof |
| `VectorizeRequiredSet` | `frozen / S08-v1.0 / T-O-222` | 应索引 unit×channel 整包二元成败；g=0 强制 | 禁 partial success |
| `IndexGeneration` | `frozen / S09-v1.0 / T-O-243` | `(team, item, namespace)` 单调投影代数；行级标记 + Active 路由 | reindex 不新建 IntakeRevision |
| `ActiveIndexPointer` | `frozen / S09-v1.0 / T-O-243` | CAS 保护的 item×namespace active 代数（≈ read alias） | ≠ serving_revision / S06 current |
| `PublicationValidPredicate` | `frozen / S09-v1.0 / T-O-244` | team∧not deleted∧indexed∧ns active∧Layer A∧active gen∧intake pins | 之后才 S04 eligibility；禁仅 ANN |
| `IndexValidatePublication` | `frozen / S09-v1.0 / T-O-241` | Process `index.validate_publication`；Handoff binding + records 整包对账 | 禁 Handoff-only / partial |
| `IndexRebuild` | `frozen / S09-v1.0 / T-O-243` | Process `index.rebuild`；build→validate→CAS→grace→purge old | 不创建 IntakeRevision |
| `RetrievalEligibility` | `frozen fence / S09-S10 / T-O-249/257` | team ∩ lifecycle ∩ ServingRevision ∩ IndexGeneration ∩ publication-valid；S10 硬管道应用 | 不能仅由 vector 存在决定 |
| `IndexTopKPolicy` | `frozen / S09-v1.0 / T-O-245` | default topK=10；hard `max_topk`（建议 100）；metric 默认 cosine | score/rerank 归 S10 |
| `RetrievalSearchPort` | `frozen / S10-v1.0 / T-O-248` | 同步 `retrieval.search`；无 Task/Execution/Process | 非 Process capability |
| `RetrievalBundle` | `frozen / S10-v1.0 / T-O-261/262` | disposition + results[] + pack? + diagnostics | 非 chat；无 answer v1 |
| `RankPolicy` | `frozen / S10-v1.0 / T-O-259` | return_k=10；recall_k=20；threshold 默认 0.0；rerank ON 诚实 fallback | ≤ max_topk；禁 dummy 分 |
| `PackView` | `frozen / S10-v1.0 / T-O-261` | 预算内 ContextTier 组装；pack_max_hits=5 / chars=12k | results[] 仍权威 |
| `RetrieveErrorFamily` | `frozen / S10-v1.0 / T-O-262` | `RETRIEVE_*` / `RETRIEVE_DEPENDENCY_*` / 推理映射 | 禁主用 PUBLISH_* |
| `FinalVectorBody` | `frozen / D04` | `mkb_vector_records.embedding` F32 | 禁外置 Vectorize 作 v1 SSOT |
| `VectorizeOutboxKind` | `frozen / D04+S08` | 主路径 `vectorize_construct`；`vectorize_structure` **v1 forbid consumer** | 单 outbox；禁 vec_process 表 |
| `VectorSpaceIsolation` (Layer A) | `frozen / S11+S08` | model/adapter/dim 一致性 fail-closed | 禁跨空间 ANN |
| `BusinessRetrievalFilter` (Layer B) | `frozen / S11+S08 / T-O-229` | team + intake + **S04 已解析 facet 抄写** | S08 **零 wire map**；禁用换模型模拟分区 |
| `FacetDefinition` / `FacetMap` | `reserved product / exact S04`（T-O-198 预留） | wire→canonical facet（如 industry-type→industry_domain） | **不在 S08 定义** |

### 4.2 S06 已冻结工作词

| Canonical term | 成熟度 | 定义 | 边界 |
|---|---|---|---|
| `GenerationArtifact` | `frozen / T-O-77..79 / S06-v1.0` | generation/repair/retry 的 immutable 派生产物记录 | 非 Intake/runtime/serving 身份；非 StateFamily |
| `GenerationInvocation` | `frozen / T-O-77` | 每次模型调用的 durable token/因果账 | 非 Attempt |
| `GenerationArtifactCurrentPointer` | `frozen / T-O-78 / T-O-96` | `(team, execution, artifact_type)` 唯一 full-valid CAS selection | v1 types：structure_document / retrieval_block_projection / structure_validation_report |
| `StructureSchemaDefinition` | `frozen / T-O-80..82 / T-O-95` | 内部注册 immutable Contract；首版 key=`mkb.structure_document` version=`1` | readiness 前必须注册 |
| `DeterministicKernel` | `frozen / T-O-83` | 不可 agent 修补的结构真相 | 见 S06-v1.0 §3.7.3 |
| `GovernedExtension` | `frozen / T-O-83..84` | schema 声明可 repair 的扩展面 | 非 HITL 入口 |
| `StructureNodeKind` | `frozen v1 closed set / S06-v1.0` | document/section/paragraph/list/list_item/table/table_row/table_cell/code/quote/media_ref/heading | 新 kind → 新 schema version |
| `SourceAnchorKind` | `frozen v1 forms / S06-v1.0` | `text_span` 与/或 `element_span`（schema version 声明） | 无 anchor = kernel fail |
| `lsrag.structurize` | `frozen capability key / S06-v1.0` | S06 首版 Process capability | S03 manifest identity |

### 4.2 D03 仓库与协议层词汇（`T-O-141..159`）

| Canonical term | 成熟度 | 定义 | 边界 |
|---|---|---|---|
| `RepositoryLayout` | `frozen / D03-v1.0 / T-O-141` | MKB 单体仓库顶级目录与模块分工宪法 | 不拥有业务状态机/DDL |
| `ContractsLayer` / `src/contracts/` | `frozen / T-O-152` | 全系统 **typed schema 唯一 SSOT** + 强制校验层；按域分册 | 运行期只认校验后的 typed 对象；冲突以 contracts 为准 |
| `ContractValidationError` | `frozen / T-O-153` | 消息体未通过 contracts 校验时的失败类型 | 必须抛弃消息体；禁 silent coerce |
| `PromptGitTree` | `frozen / T-O-146` | `data/prompts/**` git 跟踪的 prompt 正文树 | 版本管理载体 |
| `PromptHashPointer` | `frozen / T-O-155` | DB 中仅存的 prompt 内容 hash（及可选 path/key） | 禁止 DB 存第二份可漂移正文；运用时 hash 校验 |
| `WorkflowDefinitionDir` | `frozen / T-O-143` | `src/workflows/`：声明式 Workflow 定义落点 | **不是** Runtime；禁 claim/retry |
| `RuntimeEngineDir` | `frozen / T-O-143` | `src/runtime/`：Engine/claim/outbox/Process 推进 | 解释 Workflow 定义 |
| `IntakeAdapterDir` | `frozen / T-O-144` | 顶级 `intake/`：多源源适配 | 非 services 内唯一落点；不写 S04 权威 identity |

### 4.3 D04 物理 schema 词汇（`T-O-160..179`）

| Canonical term | 成熟度 | 定义 | 边界 |
|---|---|---|---|
| `PhysicalSchemaConstitution` / `D04` | `frozen / D04-v1.0 / T-O-160` | Turso 主库物理表闭集、列约束、索引与只读 VIEW 宪法 | 不拥有业务状态机合法边 |
| `MkbTableClosedSet` | `frozen / T-O-194` | v1 **55** 张 `mkb_*` required（D04-v1.1 §2.2；原 52+S11 三表） | 增减须 reopen D04 |
| `DomainEventLedger` / `mkb_domain_events` | `frozen / T-O-166..167` | 业务变迁 append-only 时间线；**非** 状态 SSOT；与业务同 TX | 禁仅凭 event 当业务成功 |
| `OpsDiagnosticLog` / `mkb_ops_diagnostic_logs` | `frozen / T-O-166` | 诊断级日志表（smind_logs 降维） | 非 SSOT；可 best-effort |
| `SecurityAuditEvent` / `mkb_security_audit_events` | `frozen / T-O-177` | admission/安全拒绝审计 | 不进业务表的拒绝写此表 |
| `VectorNamespace` / `mkb_vector_namespaces` | `frozen / T-O-169` | 向量空间头：model/dim/metric/status | records 必须引用 |
| `FinalVectorBody` | `frozen / T-O-168` | `mkb_vector_records.embedding` native F32 为 v1 最终向量本体 | 禁 content_full；禁外置 Vectorize 作 v1 可写 SSOT |
| `VectorizeOutboxKind` | `frozen / T-O-169` | outbox `vectorize_*` 替代 vec_process 队列 | 禁 `mkb_vec_process` |
| `NativeAnnIndex` | `frozen / T-O-170` | 同库 ANN 索引（如 libsql_vector_idx on embedding） | 算法参数归 S09；index 存在归 D04/S12 readiness |

### 4.4 S11 推理运行时词汇（`T-O-180..201`）

| Canonical term | 成熟度 | 定义 | 边界 |
|---|---|---|---|
| `InferenceRuntime` / `src/runtime/inference/` | `frozen / S11-v1.0 / T-O-189/196` | 分能力推理门面：binding、闸、transport policy、写 invocation | **不是** adapter；不推进业务状态机 |
| `LlmAdapter` / `src/llm_adapters/` | `frozen / T-O-182/189` | 模型供应商对接层（LocalVllm 默认；Gemini 可选） | 禁被 services 直连 |
| `InferenceCapability` | `frozen / T-O-184/190` | `embed` / `rerank` / `structured_generate` / `text_generate` | 禁万能 run(blob) |
| `VectorSpaceIsolation` (Layer A) | `frozen / T-O-192/197` | namespace+model+version+dim+adapter 一致 | 内部流转围栏 |
| `BusinessRetrievalFilter` (Layer B) | `frozen / T-O-198` | team + intake 坐标 + 上游 facet（如 industry-domain） | 不替代 Layer A |
| `TransportRetryPolicy` | `frozen / T-O-199` | 可重试类有界指数退避；不计入 Process retry_count | 禁 429 换模型 |
| `InferenceBackpressure` | `frozen / T-O-200` | 并发闸满 → retryable 错误 | 与 claim 正交 |
| `VectorizeDurability` | `frozen / T-O-201` | outbox + 幂等 records；可重 embed；禁丢意图；无 v1 WAL 表 | embed≠业务成功 |

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
- 禁止跨模块传递未通过 `src/contracts/` 校验的自由 `dict` 作为通信合同（`T-O-152/153`）。
- 禁止在 DB 中另存可漂移的 prompt 正文副本；仅允许 hash 指针（`T-O-155`）。

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
| ExecutionGate state | S05（Execution control仍由S03承接） | `open/released/rejected/superseded`只描述gate；Execution使用既有`waiting`，Intake无review state |
| Workflow phase/reason | S03 | 与 runtime state 正交 |
| IntakeItem lifecycle | S04 | `active/deactivated/deleted` 三态已由 `T-O-40` 冻结；业务原因由 versioned ActionDefinition 表达 |
| Revision serving/build projection | S04 + S03/S09 | latest、serving、proof/derived generation 分离 |
| Physical convergence facts | S04/S09/S13 | physical existence、CleanupIntent/Proof与index generation事实另账；IntakeArtifact没有万能业务lifecycle，这些事实不得决定Item业务可见性 |

### 7.4 `payload_extra` 跨数据库契约

| 规则面 | 冻结约束 |
|---|---|
| Presence | 所有 MKB-owned canonical、runtime、registry、projection、staging、outbox、audit、repair 与业务 migration 表必须包含 `payload_extra` |
| Exclusions | schema migration bookkeeping、Turso/SQLite 引擎内部表、虚拟向量表、FTS shadow 表和第三方组件私有表继承 `S01-T041` 例外 |
| Logical type | 非空 JSON object，默认 `{}`；exact Turso type、JSON validity CHECK、size limit 和 serializer 由 `S12-v1.0` 冻结 |
| Permitted use | 调试上下文、provider 非关键字段、尚在实验且不影响业务判断的扩展值 |
| Forbidden truth | identity、FK/relation、required state、CAS/fencing、proof、auth、idempotency、route condition、indexed filter、public contract、secret、无界正文和 bytes |
| Immutable rows | `payload_extra` 随宿主 Snapshot/Revision/Membership/definition/transition/audit row 一起不可变；修正必须追加新 truth |
| Mutable rows | 只能在宿主的正常 CAS + audit transaction 中修改，不能提供独立 patch 后门 |
| Fingerprint | 默认不参与 Snapshot seal、Revision fingerprint、semantic diff、route 或 proof；需要参与时必须先晋升 |
| Promotion | 某 key 一旦成为必填、可查询、可路由、可授权或影响状态，必须建立正式列或 versioned SemanticDefinition/ActionDefinition，显式迁移并停止把 extra key 当业务真相 |
| Governance | S12/S15 应统计 key/size/读取依赖；未注册 key 被 route/filter/state 读取时 fail-loud |

### 7.5 Persistence 词汇（S12-v1.0）

| Canonical term | 成熟度 | 定义 | 禁止误用 |
|---|---|---|---|
| `mkb_primary` | `frozen / S12` | 单一 Turso 业务主库逻辑名 | 第二可写业务库 |
| `PersistencePort` / `UnitOfWork` | `frozen / S12` | domain 访问持久化的唯一合同 | domain 直连 driver |
| `TransactionalOutbox` | `frozen / S12 / T-O-105` | 与业务同事务的 durable wake 行 | queue ACK=业务成功 |
| `ClaimFence` | `frozen / S12 / T-O-105` | Process claim 世代/租约校验令牌 | 无 fence 写 Outcome |
| `SchemaMigrationChain` | `frozen / S12 / T-O-106` | 单一线性 migration + checksum | 多 head / silent IF NOT EXISTS 进化 |
| `BytesFirstRegistration` | `frozen / S12 / T-O-107` | 先不可变字节+digest，再 TX 登记 handle | row-first 假 handle |
| `NativeVectorRecord` | `frozen / S12 T-O-110 + D04 T-O-168` | 同库派生向量行；**最终本体** `mkb_vector_records.embedding` F32 + namespaces | 存在≠serving；禁 content_full；禁外置 Vectorize 作 v1 可写 SSOT |
| `ConcurrentWrites` | `frozen default-on / S12 / T-O-107` | Turso 默认启用的并发写能力面 | 无协调多进程写文件 |

### 7.6 Object Storage 词汇（S13-v1.0）

| Canonical term | 成熟度 | 定义 | 禁止误用 |
|---|---|---|---|
| `ObjectStorePort` | `frozen / S13` | domain 访问对象字节的唯一合同（stream/promote/verified read/stat） | domain 直连 pathlib/S3/R2 SDK |
| `LogicalObjectHandle` / `mkbobj:v1` | `frozen / S13 / T-O-123` | opaque handle：`mkbobj:v1:<team_uuid>:<stored_object_uuid>` | 含 path/digest/bucket/key；对外公网 URL |
| `StoredObject` | `frozen / S13` | catalog 中的 content-addressed 字节记录（team+sha256+size） | 业务 Artifact identity 本身 |
| `ObjectReference` | `frozen / S13 / T-O-119` | owner→stored object 的 live 保护边；purpose 闭集 | 扫盘 mtime 当引用 |
| `ObjectReferencePurpose` | `frozen closed set / S13 / T-O-121` | intake_snapshot/revision_artifact、clean_candidate、gate_evidence、generation_artifact、process_io、operator/backup_hold | 自由字符串 purpose |
| `BytesFirstRegistration` | `frozen / S12+S13` | 先 promote 得 digest，再 TX 登记 handle/ref | row-first 假 handle |
| `OrphanObject` | `frozen / S13` | 已 promote 但无 live ref 的 bytes；grace 后可 GC | 当作业务成功 |
| `MissingObject` | `frozen / S13` | live ref 指向缺失/损坏 bytes；incident | 当作 orphan 静默删 |
| `ObjectRoot` / `identity.json` | `frozen / S13 / T-O-124` | 本地 CAS 根与 deployment binding | 与 DB 解绑错挂 |
| `TeamScopedCAS` | `frozen / S13 / T-O-118` | 仅同 team 内 digest dedup 的物理布局 | 跨 team 全局 dedup |


### 7.7 Config / Registry 词汇（S14-v1.1 / T-O-263..286）

| Canonical term | 成熟度 | 定义 | 禁止误用 |
|---|---|---|---|
| `ConfigLayer` L0–L4 | `frozen / S14-v1.1 / T-O-277` | L0 git defaults → L1 profile → L2 env/topology+secret 值 → L3 allowlisted override → L4 frozen snapshot | env 改 prompt 正文/model definition_digest/schema/workflow revision |
| `ConfigSnapshot` / L4 | `frozen / S14-v1.1` | Execution `resolve_for_new_execution` **一次**构造的不可变配置视图；Process 只读 | mid-flight 可变 bag；Process 再 merge L0–L3 |
| `config_snapshot_digest` | `frozen / S14` | `H(canonical(L4 materials))`；域 `binding_digest` **必嵌入** | 与 domain digest「或」二选一悬空 |
| `binding_digest` / `domain_binding_digest` | `frozen / S14+S03` | 域绑定材料规范哈希；含 config_snapshot_digest / PromptRef / model / schema / semantic knobs | 把 OpsKnob 偷偷塞进 digest |
| `RegistryPort` | `frozen / S14` | list/get/readiness/`resolve_for_new_execution` | 公网 CUD；agent write；v1 外部 HTTP list |
| `RegistryBootstrap` / `GreenfieldBootstrap` | `frozen / S14 / T-O-275/280` | catalog/binding/prompt 指针 **幂等灌入写权威** | S11 平行 INSERT 同表作第二 SSOT |
| `ProvenanceEnvelope` | `frozen / S14 / T-O-282` | model+prompt+schema+params 最小可追溯字段集 | log/OTel 当唯一 SSOT；含 secret/正文/messages/向量全文 |
| `PromptRef` | `frozen / D05+S14` | identity + content_hash（+path?） | prompt 正文；KV key；裸字符串静默透传 |
| `flag_bundle_digest` | `frozen / S14` | feature_flags 规范哈希；默认 OFF | 远程 flag SSOT；flag 触发 auto model fallback |
| `params_profile_id` / `params_digest` | `frozen / S14-T058` | 参数 profile 身份与 digest；空=`sha256:empty_profile_v1` | 未登记 profile 静默透传 |
| `SemanticKnob` / `OpsKnob` | `frozen / S14 / T-O-281` | Semantic 进 binding_digest；Ops 不进；`security.*`/`obs.*` **强制 Ops** | 未知 security 前缀当 Semantic |
| `OverrideAllowlist` | `frozen / S14 / T-O-279` | Task/Execution 可覆盖键窄表；未知键 `CONFIG_OVERRIDE_REJECTED` | 覆盖 model/prompt/schema/adapter/secret/绝对 path |
| `CONFIG_*` | `frozen / S14 / T-O-285` | 配置/registry 错误族；digest/hash mismatch **非** transient | 用 429 掩盖 trust fail |

### 7.8 Observability 词汇（S15-v1.1 / T-O-287..311）

| Canonical term | 成熟度 | 定义 | 禁止误用 |
|---|---|---|---|
| `DomainEventLedger` / `mkb_domain_events` | `frozen / D04+S15` | 业务域事件物理表；与 mutation 同 TX | log 当唯一失败证据；event 当 CAS |
| `DomainEventWriter` | `frozen / S15` | 经 UoW 同 TX 写 domain_events 的唯一端口 | raw SQL 旁路；未登记 `event_type` |
| `EventTypeRegistry` | `frozen / D04+S15` | `event_type` 闭集登记（D04 表 + S15 Writer）；新增须 change-request | 各域 formal 私造 type 名 |
| `OpsDiagnosticLog` / `mkb_ops_diagnostic_logs` | `frozen / D04+S15` | 运维诊断日志表；失败不回滚业务 | 当业务状态 SSOT |
| `ObservabilityReadPort` | `frozen / S15 / T-O-308` | timeline/dead/audit/health/metrics 只读面；内网+token | 省略 team 的跨租户读；写面伪装 |
| `AlertBinding` / `ALERT_*` | `frozen / S15 / T-O-304` | 必告警闭集 + runbook 字段（含 `ALERT_SEC_*`） | Task 业务 webhook 混用 |
| `RetentionPolicy` | `frozen / S15 / T-O-302` | 三表分层天数与批 DELETE；export 失败禁删 | Process cleanup 级联删 events |
| `DeadLetterView` | `frozen / S15 / T-O-309` | outbox dead 可查询投影 + 告警 | 第二 DLQ 业务表 SSOT；无审计 redrive |
| `HealthAggregator` | `frozen / S15 / T-O-305` | `/ready` 组件聚合；含 `sec_token_loaded`；not ready=503 | 单一恒 ok `/health` 混充 ready |
| `BackupScheduler` | `frozen / S15` | 唯一 cron 调 S13 backup 协议 | S13/S15 双 cron |
| `OBS_*` | `frozen / S15 / T-O-310` | 可观测错误族；domain_events 失败 → 整 TX 失败 | silent swallow；events best-effort |

### 7.9 Security 词汇（S16-v1.1 / T-O-312..336）

| Canonical term | 成熟度 | 定义 | 禁止误用 |
|---|---|---|---|
| `InternalToken` / `ActiveTokenSet` | `frozen / S16 / T-O-327/328` | ops mint shared-secret；at-rest hash；双活≤2；重叠窗默认 24h | JWT 用户平台 claims；team API key 授权 |
| `actor_fingerprint` | `frozen / S16` | `H(token)`；成功校验后的 actor 标识 | 明文 token 入 log/audit/DB |
| `EndpointClass` | `frozen / S16 / T-O-329` | Business/Operator/Repair/Live/Ready/Metrics 鉴权分级 | 用户 RBAC 角色；公网匿名 metrics |
| `AdmissionDecision` | `frozen / S16` | allow/deny + `SEC_*`；Business invalid **先于**资源读 | 当 Task 状态 |
| `EgressPolicy` / `EgressPolicyEngine` | `frozen / S16 / T-O-332` | 出站 fail-closed；DNS→IP；redirect≤3；硬拒私网/metadata | open proxy；allowlist 绕硬拒 |
| `SecretResolver` / `SecretSlot` | `frozen / S16 / T-O-333` | 逻辑 slot→值；env(+file)；原子激活 | catalog/git/DB 存明文 key |
| `SupplyFence` | `frozen / S16 / T-O-335` | 仅 binding exact identity 调模型 | 请求体任意 endpoint；silent swap |
| `SecurityAuditEvent` / `mkb_security_audit_events` | `frozen / D04+S16` | admission/安全拒绝专用表；S16 写语义 / S15 retention | 并入 domain_events；明文 secret |
| `RedactionPolicy` | `frozen / S16-T056` | envelope/log/obs 字段脱敏规则权威；S15 sync-from | 各域私自放宽 |
| `sec_token_loaded` | `frozen / S16+S15` | readiness 组件：ActiveTokenSet 非空 | 无 token 却 ready |
| `SEC_*` | `frozen / S16 / T-O-336` | 安全域 typed 错误（含 rate/supply/egress） | 用业务 CAS 码掩盖 admission deny |


---

## 8. Cross-Spec Alignment Outcome

| 权威文档 | 校准结果 | 版本 / 状态 |
|---|---|---|
| `domain-truth/D01-task-execution-process-flow.md` | 三层状态所有权；S12 仅物理兑现 | `D01-v1.4 / S12-calibrated` |
| `domain-truth/S01-skill-worker-integration.md` | Task+Audit 原子由 S12 兑现 | `S01-v1.5 / S12-calibrated` |
| `domain-truth/S02-task-api.md` | 六态 CAS 由 S12 兑现 | `S02-v1.3 / S12-calibrated` |
| `domain-truth/S03-workflow-engine.md` | claim/outbox 物理由 S12；状态边仍 S03 | `S03-v1.3 / S12-calibrated` |
| `domain-truth/S04-intake-asset-lifecycle.md` | TX-05 accept；vector≠lifecycle | `S04-v1.2 / S12-calibrated` |
| `domain-truth/S05-intake-cleaning.md` | TX-08 gate decision | `S05-v1.1 / S12-calibrated` |
| `domain-truth/S06-lsrag-structurizer.md` | TX-06 generation；bytes-first | `S06-v1.0 / S12-calibrated` |
| `domain-truth/S12-turso-persistence.md` | 单主库、TX/outbox/claim、CW+vector、模块；object 表物理 | `S12-v1.0 / S13-calibrated` |
| `domain-truth/S13-artifact-storage.md` | local CAS、Port、ref/GC、backup 协议 | `S13-v1.0 / accepted` |
| `domain-truth/D02-production-state-and-routing.md` | 六 StateFamily；S12 物理非 SSOT | `D02-v1.0 / S12-calibrated` |
| `qna-truth/S12.md` | `T-O-97..110` 全冻；无 Round 4 | `S12-QNA-v1.0 / locked` |
| `qna-truth/S13.md` | `T-O-111..125` 全冻；无 Round 4 | `S13-QNA-v1.0 / locked` |
| `domain-truth/S08-embedding-vectorization.md` | vectorize 写侧；RequiredSet；Layer B 抄写 | `S08-v1.0 / accepted` |
| `domain-truth/S09-vector-index.md` | publication/ActiveIndexPointer/可服务谓词 | `S09-v1.0 / accepted` |
| `domain-truth/S10-lsrag-retrieval.md` | dual-fence；context-only Bundle | `S10-v1.0 / accepted` |
| `domain-truth/S11-inference-runtime.md` | resolve 权威；bootstrap 写归 S14 | `S11-v1.1 / S14-calibrated` |
| `domain-truth/S14-config-prompt-model-registry.md` | L0–L4/registry/provenance；bootstrap 写权威 | `S14-v1.1 / accepted` |
| `domain-truth/S15-observability-reliability.md` | retention/metric/alert/ready/operator | `S15-v1.1 / accepted` |
| `domain-truth/S16-security-trust-boundary.md` | token/egress/audit/redaction | `S16-v1.1 / accepted` |
| `qna-truth/S14.md` | `T-O-263..286` 证据层 | `locked / formal accepted` |
| `qna-truth/S15.md` | `T-O-287..311` 证据层 | `locked / formal accepted` |
| `qna-truth/S16.md` | `T-O-312..336` 证据层 | `locked / formal accepted` |
| `qna-truth/_s14-s16-campaign-audit.md` | 全真相层战役审计 | `2026-08-12 / campaign complete` |
| `qna-truth/S06.md` | S06 formal Spec 证据层 | `locked / S06-v1.0` |
| `qna-truth/D02.md` | `T-O-86..92` | `frozen` |
| `domain-truth/D07-v1-acceptance-truth.md` | 验收 HARD 台账 | `D07-v0.5 / draft` |
| `domain-truth/D08-legacy-capabilities-migration.md` | 四域能力闭集与 intake 树 | `D08-v0.1 / draft` |

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
| `v1.2` | `2026-07-18` | 记录D02-v0.2既有Truth校准输出（开放提案仍未冻结）与S06 `T-O-77..85`：登记StateFamily/ControlStatus/BusinessPhase/Outcome/Staging/Selection/Readiness等正交词汇；登记GenerationArtifact/Invocation/StructureSchemaDefinition/kernel/extension；更新D01-S05版本与S06暂停门，开放kind不标为frozen。 |
| `v1.3` | `2026-07-19` | 接收D02 QNA Round 1 `T-O-86..89`与D02-v0.3：将StateFamily从derived升级为owner-frozen六族宪法；登记D02 State Ledger共有域角色、下游执行cutoff与Truth镜像义务；不提前冻结Q4-Q6的exact镜像块或治理协议。 |
| `v1.4` | `2026-08-10` | 接收D02-v1.0与QNA `T-O-90..92`：冻结四层ledger结构、StateContractMirrorBlock、CitationDrift/SemanticDrift及同轮双向校准；登记D02 campaign关闭和S06 hold解除，开放S06 kind仍保持designing。 |
| `v1.5` | `2026-08-11` | 接收S06-v1.0与`T-O-93..96`：冻结StructureDocument/RetrievalBlockProjection、generation账本、mkb.structure_document@1 node_kind闭集与anchor形态；summary仍归S07；HITL完整管线 out-of-scope。 |
| `v1.6` | `2026-08-11` | 接收S12-v1.0与`T-O-97..110`：登记mkb_primary、UnitOfWork、Outbox、ClaimFence、migration链、bytes-first、NativeVectorRecord、ConcurrentWrites；更新D01–S06/S12 alignment。 |
| `v1.7` | `2026-08-11` | 接收S13-v1.0与`T-O-111..125`：登记ObjectStorePort、mkbobj、StoredObject、ObjectReference/Purpose、Orphan/Missing、ObjectRoot、TeamScopedCAS；更新D01–S06/S12 alignment 为 S13-calibrated。 |
| `v1.8` | `2026-08-11` | 接收S07-v1.0与`T-O-126..140`：冻结ConstructionUnit/OriginalChannel/SummaryChannel、ConstructionDocument/DualChannelProjection、ConstructionSchema、ContentFullRecipe、ConstructMode；整包二元成败；summary 仍不在 S06 kernel。 |
| `v1.9` | `2026-08-11` | 接收D03-v1.0与`T-O-141..159`：登记RepositoryLayout、ContractsLayer、ContractValidationError、PromptGitTree、PromptHashPointer、WorkflowDefinitionDir、RuntimeEngineDir、IntakeAdapterDir。 |
| `v2.0` | `2026-08-11` | 接收D04-v1.0与`T-O-160..179`：登记PhysicalSchemaConstitution、MkbTableClosedSet、DomainEventLedger、OpsDiagnosticLog、SecurityAuditEvent、VectorNamespace、FinalVectorBody、VectorizeOutboxKind、NativeAnnIndex。 |
| `v2.1` | `2026-08-12` | 接收S11-v1.0与`T-O-180..201`：InferenceRuntime/LlmAdapter/能力面/双层filter/TransportRetry/Backpressure/VectorizeDurability；MkbTableClosedSet→55。 |
| `v2.6` | `2026-08-12` | 接收S08-v1.0与`T-O-211..230`：LsragVectorizeCapability、VectorizeCommand/Outcome/Handoff、RequiredSet；Layer B 抄写分账；vectorize_structure v1 forbid；FacetMap reserved→S04。 |
| `v2.7` | `2026-08-12` | 接收 S14–S16 v1.1：登记 ConfigSnapshot/RegistryPort/ProvenanceEnvelope、ObservabilityReadPort/HealthAggregator、InternalToken/EndpointClass/EgressPolicy/SupplyFence/sec_token_loaded 等；权威输入扩至 S01–S16。 |
| `v2.8` | `2026-08-12` | **S14–S16 战役审计**：扩展 ConfigLayer/binding_digest/OverrideAllowlist/CONFIG_*、EventTypeRegistry/OBS_*/DomainEventLedger、AdmissionDecision/actor_fingerprint/RedactionPolicy/SEC_*；alignment 补 S08–S11；同步 index v0.61。 |
| `v2.9` | `2026-08-13` | 接收 **D08-v0.1**：登记 ProviderDefinition/ProviderOperation/CleanStrategy/FilterMeta/ContextMeta/双 digest；`action_branch` 标 legacy-only；alignment 补 D07/D08。 |
