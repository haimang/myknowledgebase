# ES-02 — Workflow Runtime

> **项目**：`myknowledgebase`（MKB）
>
> **文件 ID**：`ES-02`
>
> **文档性质**：`execution-spec / implementation authority`
>
> **版本 / 日期**：`ES-02-v1.0 / 2026-08-10`
>
> **文档状态**：`ready`
>
> **Truth 输入**：`OT-01-v1.0`、`OT-02-v1.0`、`OT-03-v1.0`、`OT-04-v1.0`
>
> **Baseline 输入**：`D01-v1.4`、`D02-v1.0`、`S02-v1.3`、`S03-v1.3 / T-O-12..29`
>
> **上游 Execution Spec**：`ES-01-v1.0`
>
> **Cross-spec calibration**：`ES-03-v1.0`、`ES-05-v1.0`、`ES-07-v1.0`
>
> **上游索引**：`docs/specs/index.md`

本文件是 MKB 单体内部声明式 Workflow、Execution/Process runtime、route/guard、claim/lease/fence、自动 retry、fan-out/fan-in、cancel、semantic recovery 与 Process cleanup eligibility 的唯一 Execution Spec。它不拥有 Task aggregate、Intake/derived/vector truth或物理持久化driver；跨域推进只能通过owner port和typed fact/proof。

---

## 1. Inherited Truth

### 1.1 权威输入

| 来源 | ES-02继承 | 不得改变 |
|---|---|---|
| `OT-01-v1.0` | 一个Python应用/发布单元、内部状态自持、LS-RAG完整链路 | 不拆Dispatcher/Worker服务，不依赖legacy或上游平台 |
| `OT-02-v1.0` | Task/Execution/Process、root+children、control向下/proof向上、六StateFamily | 不建Attempt/child Task/第七StateFamily，不合并runtime与asset身份 |
| `OT-03-v1.0` | 六intent、polling、cancel/retry/rebuild、mandatory preflight/gate、proof success | 不公开runtime CUD，不允许Process绕过proof或自行route |
| `OT-04-v1.0` | crash/replay/cancel/scatter收敛、无假成功、summary-before-cleanup | 不以queue/log/file/HTTP结果作为成功 |
| `D01-v1.4` | 三层身份、single/scatter execution tree、Process工序职责 | Execution是唯一完整运行身份；Process统一一表 |
| `D02-v1.0` | Execution/Process exact states、owner、typed facts、drift fail-closed | status、phase、Outcome、wait、proof不得混义 |
| `S02-v1.3` | Task六态、generation、collect-all、forward-stop cancel、restart因果 | ES-02只能向ES-01提交aggregate proposal |
| `S03-v1.3` | 六平面Workflow、七表SSOT、typed DAG、command/outcome、claim/fence/recovery | 不将Workflow退化为JSON step list或开放authoring |
| ES-07-v1.0 | 六个exact vector/index capability、rebuild plan/item、filter/publication/withdraw proof | 只校准typed route/fan-out；不拥有vector/index truth |

### 1.2 适用Truth映射

| Truth cluster | 落点 |
|---|---|
| `OT01-T001/T002/T007/T008/T015`、`OT01-C001/C003/C008/C009` | §2边界、§4单体engine、§7 legacy |
| `OT02-T001..T007/T015/T017..T023`、`OT02-C001..C006/C008/C010` | §4.5/4.6状态机、§5 runtime schema、§6一致性 |
| `OT03-T003/T005/T009/T017..T024/T027..T030`、`OT03-C005/C006/C009..C013/C015` | §4默认workflow、§5协议、§6proof/recovery |
| `OT04-T001..T008/T011..T019/T021..T030`、`OT04-C003/C010..C014` | §4执行链、§6故障、§8验收 |
| `T-O-12..29` / `S03-T001..T054` | §4声明式program、七表、两态机、retry/recovery/cleanup |

### 1.3 唯一ownership

| Concern | Owner | ES-02 interaction |
|---|---|---|
| Task aggregate | ES-01 | 发送`TaskAggregateProposalV1`；禁止直接写`tasks` |
| Execution control | ES-02 | 唯一transition owner |
| Process control | ES-02 | 唯一transition/claim/outcome owner |
| Intake/Candidate/Gate | ES-03 | 只调用accept/gate/lifecycle ports并消费typed fact |
| Registry/capability/model | ES-05 | 编译时exact-bind；运行不切latest |
| Structure/derived | ES-06 | 通过Process capability与proof交互 |
| Vector/index | ES-07 | 通过Process capability与PublicationProof交互 |
| UoW/outbox/event/storage | ES-04 | 实现本文件repository/transaction ports |
| Recovery operation/observability | ES-08 | 驱动scanner、metric、alert；不能自创transition |

---

## 2. Scope / Non-scope

### 2.1 Scope

1. 六平面、版本化、内部注册的Workflow Definition；
2. 七张normalized Workflow truth表、deterministic compiler和active revision resolver；
3. `executions`与`processes`两张runtime state表；
4. Execution/Process两个StateFamily的完整状态机；
5. typed route/guard、Process materialization、claim/lease/fencing；
6. ProcessCommand/ProcessOutcome内部协议与completion guard；
7. single、scatter、metadata、lifecycle、index rebuild执行链；
8. automatic retry、lease recovery、deadline、cancel、fan-in；
9. progress invariant、semantic repair与cleanup eligibility。

### 2.2 Non-scope

- 不创建/修改Task、Audit、Restart公共事实；
- 不拥有IntakeSource/Snapshot/Item/Revision/Artifact、CandidateSet或Gate状态；
- 不定义clean/LS-RAG/vector业务算法或物理storage；
- 不提供外部Workflow Create/Update/Delete、agent authoring、dynamic plugin或任意脚本guard；
- 不建立Attempt、clean/rag/vector job、child Task、per-vector Process；
- 不复制Cloudflare Worker/Queue/DO/SMCP callback拓扑；
- 不以compiled JSON、queue、event、log或projection替代七表/两表Truth。

### 2.3 完成定义

ES-02的`ready`是规范状态：以下义务已被完整定义并通过cross-spec audit，不表示它们已在尚未构建的实现上运行。任何实现要声明符合ES-02-v1.0并进入release，必须满足：

1. 七表Workflow定义可原子注册、静态验证、deterministic compile并重建同digest；
2. 两个StateFamily的合法/非法边穷举通过；
3. 每个eligible Process在durable spec/outbox提交后才可claim；
4. duplicate delivery、stale fence、retry/recovery/cancel race均收敛；
5. single/scatter及六intent default workflow均有terminal proof路径；
6. 每个nonterminal Execution满足progress invariant；
7. Process cleanup前后Task/lineage/proof语义等价；
8. 与ES-01/03..08完成cross-spec schema与protocol audit。

### 2.4 核心术语

| 术语 | Exact含义 |
|---|---|
| Workflow | 六平面声明式程序，不只是DAG |
| WorkflowRevision | immutable七表行集合与compiled digest |
| ProcessCapabilityManifest | ES-05发布、工序专属、versioned typed contract |
| Execution | 一次durable workflow run；完整retry的新身份 |
| Process | 某Execution内一个eligible工序实例；automatic retry身份不变 |
| RouteDecision | immutable typed decision evidence，不是状态 |
| Fence | 每次合法claim/recovery递增的写入代次；stale runner无提交权 |
| Delivery/Recovery/Retry | transport重投、lease恢复、业务重试三套独立计数 |

---

## 3. Scope Impact Audit

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

七张Workflow表、Execution/Process两表、内部workflow read面和exact process keys均是baseline frozen Truth的执行化；它们位于单体内部，不增加外部request intent、产品功能、状态族或部署单元。

---

## 4. Architecture Decisions

### 4.1 Engine结构与六平面

```text
Resource / Context
Authority / Admission
Process Capability
I/O / Dataflow
Orchestration / Control
Outcome / Evidence / Observation
```

WorkflowRevision必须覆盖六平面。Graph只表达Orchestration/Control；resource binding、authority fence、typed ports、retry/cancel controls、outcome/proof guard均是一等关系Truth。Engine模块依赖方向：

```text
workflow.domain
  ← workflow.application
      ← scheduler / runner adapters
      → ES-01 Task owner port
      → ES-03/05/06/07 capability ports
      → ES-04 UoW/outbox/event ports
```

Leaf handler只接收一个ProcessCommand并返回一个ProcessOutcome；它看不到完整Workflow、Task repository或next-step API。

### 4.2 Workflow治理与编译

#### 4.2.1 注册规则

- v1定义只可由code/migration/bootstrap bundle注册；
- `workflow_key`永久唯一，变化用新revision；
- active revision已激活后所有child row immutable；
- external read仅提供list与compiled detail get；CUD route不存在；
- agent/tool/caller不能提交workflow key、revision、graph或handler；
- registry `enabled/disabled/deprecated`是governance fact，不是D02生产StateFamily。

#### 4.2.2 Compiler pipeline

```text
strict row models
→ same-revision FK/wiring
→ capability port/parameter/proof compatibility
→ one-start + acyclic + reachability + terminal coverage
→ control inheritance/range
→ guard operator/type/reference
→ secret/path/free-expression scan
→ canonical semantic sort/serialization
→ definition digest + compiled digest
→ atomic revision rows + active pointer switch
```

Canonical sort使用table kind→semantic key→priority/order；display description不进入运行digest。Compiled metadata必须包含compiler version、capability registry digest、definition digest和compiled digest。Cache丢失时必须从七表重建完全相同bytes。

#### 4.2.3 Read-only surface

| Method / route | 语义 |
|---|---|
| `GET /v1/workflows` | bounded list；按purpose/role/governance过滤 |
| `GET /v1/workflows/{workflow_key}` | registry summary + active compiled detail |
| `GET /v1/workflows/{workflow_key}/revisions/{revision_number}` | immutable historical compiled detail |

业务token有效即可读；响应不含secret、物理path、runtime UUID、handler implementation或平台authority。所有Workflow POST/PUT/PATCH/DELETE均`405 workflow-read-only`。

### 4.3 v1默认Workflow catalog

| Workflow key | Role / intent | Required execution chain |
|---|---|---|
| `intake.ingest.single.v1` | root_single / ingest | acquire branch→decode/clean branch→preflight→collection.seal→accept_snapshot→optional gate→structurize→construct→vector.embed→index.stage_generation→index.validate_publication |
| `intake.ingest.scatter-root.v1` | root_scatter / ingest | acquire.registered_api→clean.map.registered_api→preflight→seal→accept_snapshot→optional root gate→materialize child set→fan_in |
| `intake.ingest.scatter-child.v1` | scatter_child / internal | exact accepted Revision/member Artifact→applicable clean branch→item-scoped preflight→optional item gate→structurize→construct→vector.embed→index.stage_generation→index.validate_publication |
| `intake.rebuild.v1` | root_single / rebuild | exact existing Revision→structurize→construct→vector.embed→index.stage_generation→index.validate_publication |
| `intake.update-metadata.v1` | root_maintenance | metadata.apply→branch(noop / filter update / new semantic Revision→full LS-RAG)→publication validate as required |
| `intake.deactivate.v1` | root_maintenance | lifecycle.deactivate→index.withdraw_serving→cleanup.plan→logical-fence proof |
| `intake.delete.v1` | root_maintenance | lifecycle.delete→index.withdraw_serving→cleanup.plan→tombstone/cleanup-intent proof |
| `index.rebuild.v1` | root_maintenance + bounded children / index rebuild | root plan_scope→frozen item fan-out→child reuse-or-reembed route→validate publication→collect-all active-generation proofs |

Catalog是有限code-owned program，不是通用workflow platform。Exact ProcessCapabilityManifest分别由ES-03、ES-06、ES-07/ES-05注册；缺失任一required manifest时对应Workflow不得激活。

Gate的`reclean`不是loop或Process retry。Single、scatter-root与scatter-child定义最多一条编译期显式、acyclic remediation branch，沿原S05 binding再执行一次适用clean→preflight；materialization key包含`remediation_ordinal=1`。第二个Gate不得暴露reclean；approve/approve_override继续下游，reject形成required failure fact。Workflow compiler必须验证该有限路径和allowed-actions一致。

### 4.4 Exact process key registry consumed by ES-02

| Owner | Required v1 keys |
|---|---|
| ES-03 | `intake.acquire.inline`、`intake.acquire.local_object`、`intake.acquire.http_static`、`intake.acquire.http_browser`、`intake.acquire.registered_api`、`intake.decode.text_json_html`、`intake.decode.pdf`、`clean.extract.deterministic`、`clean.ocr.local`、`clean.extract.vision`、`clean.map.registered_api`、`intake.collection.seal`、`intake.preflight_validate`、`intake.accept_snapshot`、`intake.metadata.apply`、`intake.lifecycle.deactivate`、`intake.lifecycle.delete`、`intake.cleanup.plan` |
| ES-06 | `lsrag.structurize`、`lsrag.construct` |
| ES-07 | `vector.embed`、`index.stage_generation`、`index.validate_publication`、`index.update_filters`、`index.withdraw_serving`、`index.rebuild_generation` |

旧`lsrag.vectorize_index`只作为legacy/coarse说明，v1 registry不得注册该alias。六个exact vector/index Process各有独立typed input/output/retry/proof；vector.embed、stage、validation明确分开，避免embedding ACK冒充publication。

### 4.5 Process control状态机

```text
materialize → ready → claimed → running
                 │        │        ├─→ succeeded
                 │        │        ├─→ retry_wait → ready
                 │        │        ├─→ failed
                 │        │        └─→ cancelling → cancelled
                 │        └─ expired lease → ready | failed
                 └─ cancel → cancelling → cancelled
```

| From→To | Guard / effect |
|---|---|
| —→ready | eligible route；unique materialization；spec+outbox同提交 |
| ready→claimed | available/deadline/concurrency/revision CAS；new random token hash、fence+1、lease |
| claimed→running | current raw token/fence；started evidence |
| claimed/running→ready | lease expired；safe replay/verified sink；recovery budget；fence+1、recovery_count+1 |
| claimed/running→failed | indeterminate/non-replayable side effect或recovery exhausted |
| running→retry_wait | current fence；retryable failure；budget；retry_count+1、due time |
| retry_wait→ready | durable due；无cancel；无lease |
| running→succeeded | current fence；Outcome schema/output/proof/idempotency guard全通过 |
| running→failed | non-retryable、proof/schema invalid、retry budget exhausted |
| ready/claimed/running/retry_wait→cancelling | accepted cancel；invalidate old fence；no new claim/outcome |
| cancelling→cancelled | stop/compensation/side-effect verification complete；无active lease |

禁止terminal回边、ready→succeeded、retry_wait→running、queue ACK→success及stale fence mutation。Accepted Outcome重放仅返回原truth。

### 4.6 Execution control状态机

```text
created → ready → running ↔ waiting
   │         │        │         │
   ├─────────┴────────┴─────────┼─→ failed
   └─────────┬────────┬─────────┴─→ cancelling → cancelled
             └────────────────────→ succeeded (from running/waiting only)
```

| From→To | Guard |
|---|---|
| create→created | identity/tree/task generation/workflow resolver transaction |
| created→ready | exact Workflow/S05 binding、initial route、first durable Process/child intent |
| created→failed/cancelling | binding integrity failure或Task cancel |
| ready→running | first claim/route advance |
| ready→waiting | typed durable wait存在 |
| ready→failed/cancelling | config/guard failure或cancel |
| running↔waiting | active work与typed trigger之间切换 |
| running/waiting→succeeded | required routes/children terminal且intent proof valid |
| running/waiting→failed | required non-retryable/exhausted/integrity failure，且aggregation收敛 |
| running/waiting→cancelling | cancel propagation |
| cancelling→cancelled | all descendants fenced/terminal；late commit impossible |

Terminal immutable。Full Task retry由ES-01创建新generation和新root；旧Execution不复活。

### 4.7 Phase、wait与Outcome分账

Canonical phase：

```text
resolving_source | cleaning | scattering | preflight_admission |
awaiting_human_review | structurizing | constructing |
vectorizing | staging_index | validating_publication | fan_in |
updating_metadata | deactivating | deleting | purging | rebuilding_index
```

Phase是deterministic focus fact，不是status。Waiting reason只有`retry_due/process_join/scatter_children/durable_prerequisite/human_review`，且必须有typed `wait_ref`; `retry_due`还必须有`next_wake_at`。ProcessOutcome固定`outcome_status=succeeded|failed|cancelled`与`retryability=retryable|non_retryable|indeterminate`，也是immutable fact而非StateFamily。

scatter_children的历史spelling覆盖所有“由immutable expected set materialized的child Executions”，包括ingest ChangeSet与ES-07 IndexRebuildPlan；它不是source kind、phase或新StateFamily。wait_ref必须区分change_set或index_rebuild_plan typed union。

### 4.8 Typed route / guard

Workflow graph必须single start、acyclic、required step reachable、terminal coverage完整。Route selector只允许`always/succeeded/failed/cancelled/skipped`；operator只允许`eq/ne/lt/lte/gt/gte/exists/not_exists/in_registered_set/digest_eq/schema_valid/proof_valid`。禁止Python、SQL、regex code或free expression。

Evaluation输入为exact revision/digest、current step/Outcome、immutable domain facts、Execution control；输出为selected route keys、guard results、decision input digest、expected set ref、next eligible steps/terminal与decision digest。Unselected step不创建Process；decision作为append-only event/evidence保存。Route evaluation、next Process/child materialization和outbox必须同事务或可证明等价。

### 4.9 Single与maintenance执行链

#### 4.9.1 Single ingest/rebuild

```text
ES-01 task.start-requested
→ dedupe task+generation
→ resolve/bind WorkflowRevision
→ create root Execution(created)
→ bind immutable ingress subject
→ materialize first Process + outbox
→ Execution ready；ES-01 Task queued→running proposal
→ claim/run/Outcome/route循环
→ mandatory preflight binds frozen candidate root/binding/fence
→ collection seal validates the same PreflightOutcome
→ accept exact Snapshot/Item/Revision（ingest）
→ optional Gate：Process terminal，Execution waiting，无lease
→ structurize→construct→embed→stage index→validate publication
→ Execution terminal summary/proof
→ ES-01 Task aggregate proposal
```

Rebuild从exact existing Revision开始，不重跑acquisition/clean且不创建Revision。Full Task retry复制来源root exact WorkflowRevision/compiled digest/S05 binding；新独立Task按current active resolver选择。

#### 4.9.2 Metadata/lifecycle/index

- Metadata apply返回`no_change/filter_change/semantic_revision` typed outcome；no-change走type-specific noop proof，filter change只更新filter并验证，semantic revision走完整LS-RAG；
- Deactivate/delete先由ES-03 lifecycle owner提交逻辑状态/serving fence，再由ES-07撤出正常检索并写cleanup intent；Task成功不等待physical bytes删除；
- Index rebuild只操作受控scope，新IndexGeneration通过validation/active pointer proof后成功；不创建IntakeRevision。

#### 4.9.3 Index rebuild bounded fan-out

index.rebuild.v1仍是既有八个Workflow之一，不新增child Workflow key。一个WorkflowRevision包含root与child两种由Execution subject固定的entry branch：

    root Execution
      → index.rebuild_generation(mode=plan_scope)
      → IndexRebuildPlan exact ordered item set
      → materialize one child Execution per plan item
      → root waiting(scatter_children, plan ref)
      → collect-all fan-in

    child Execution(route=reuse_vectors)
      → index.rebuild_generation(mode=build_item)
      → index.validate_publication
      → one Item publication proof

    child Execution(route=reembed)
      → vector.embed
      → index.stage_generation
      → index.validate_publication
      → one Item publication proof

Root/child都绑定同一exact WorkflowRevision/compiled digest。Child subject必须含plan UUID/digest、item ordinal、Item/Revision、source generation/projection、route kind及expected Item/pointer revisions；start guard禁止root进入child branch或child重新plan。Caller不能选择mode/route/space。

Child uniqueness固定为(root_execution_uuid, plan_digest, item_ordinal, intake_item_uuid, target_revision_uuid)。Crash后按plan set-diff补齐；不重新枚举scope、不替换stale Revision、不以已有child count改变分母。一个Item/revision scope也创建one-item plan+one child，保持同一语义。

Fan-in使用collect-all：每个proof-valid child可独立切换；failed/conflicted sibling不回滚它。Root只有在全部required child terminal且全部required publication proof有效时succeeded；mixed outcome为failed并透明汇总counts/items。Team/source scope沿用10000 item hard ceiling，超出在plan Process typed reject。

### 4.10 Scatter执行链

```text
one Task
→ root_scatter Execution
→ registered API acquire/map/preflight/seal/accept
→ accepted Snapshot/Membership/ChangeSet required set
→ optional root Gate
→ idempotently materialize exactly N child Executions
→ each child binds exact Item/Revision and child Workflow
→ children execute independently and may publish early
→ root waiting(scatter_children, ChangeSet ref)
→ collect-all fan-in
→ root succeeded | failed | cancelling→cancelled
→ Task aggregate proposal
```

Child uniqueness=`(root_execution_uuid, change_set_digest, intake_item_uuid, intake_revision_uuid)`。Expected set只能来自committed ChangeSet；crash后做set-diff补齐，不以现有child count改分母。Healthy siblings不fail-fast；proof-valid child不会因root/Task失败或取消被回滚。Zero-required必须有typed terminal policy/proof，不能用queue empty假成功。

### 4.11 Claim、retry、deadline与cancel

#### 4.11.1 Claim

候选排序：`priority_rank DESC → available_at ASC → deadline_at ASC NULLS LAST → created_at ASC → process_uuid ASC`。Claim事务以status/revision/available/deadline/lane concurrency CAS选中Process，生成256-bit random raw token（只返回runner）并仅存SHA-256 hash，`fencing_generation+1`，写lease和delivery outbox。

#### 4.11.2 三账与backoff

| Cause | Identity | Counter |
|---|---|---|
| duplicate/redelivery | all unchanged | `delivery_count+1` |
| expired lease recovery | all unchanged；new fence | `recovery_count+1` |
| business retry | same Process/Execution | `retry_count+1` |
| full Task retry | new root/Processes | Task generation+1 |

Backoff：fixed=`initial`; linear=`min(max,initial*retry_count)`；exponential=`min(max,initial*multiplier^(retry_count-1))`；jitter用`process_uuid+retry_count` deterministic seed。Handler不得sleep/retry。

#### 4.11.3 Deadline/timeout

Task `deadline_at`是latest claim time；过期ready Process转failed `deadline-exceeded-before-start`。Running Process由resolved timeout和capability retry policy处理，不被非安全强杀。Deadline/timeout不purge、不回滚proof-valid资产。

#### 4.11.4 Cancel

ES-01 cancel message使root/descendants进入cancelling，停止新materialization/claim，fence active Process并执行cooperative stop/verify/compensate。全部安全收敛后发送cancellation-converged proposal。Success/cancel最终仍由ES-01 Task CAS first-commit-wins；已发布资产保留。

### 4.12 Semantic recovery与cleanup

每个nonterminal Execution必须至少有：ready/due Process、current-fenced active Process、typed durable wait、或cancelling descendants。Scanner发现四者皆无即`stranded-execution` invariant failure。

| Drift | Repair |
|---|---|
| ready/due无wake | 幂等补outbox，不建新Process |
| retry_wait due | 同transition CAS→ready |
| lease expired | fence旧runner，按side-effect/max_recoveries→ready或failed |
| terminal Process未route | exact revision+Outcome重算同decision并补materialization |
| preflight/gate四窗口断点 | 依据committed Outcome/Gate/Decision补transition/outbox；不伪造decision |
| ChangeSet child缺失 | uniqueness set-diff补齐 |
| join/fan-in已满足仍waiting | 同aggregate path推进 |
| cancelling未收敛 | 继续fence/stop/verify，不能直接cancelled |
| terminal summary/pointer缺失 | 从durable facts重建后CAS补齐 |
| revision/digest/proof冲突 | failed + integrity quarantine evidence；禁止猜latest |

Cleanup eligibility：Execution terminal、summary/proof完整、无active/retry/cancel/compensation/outbox/lease、current pointer清空且terminal满90天。ES-02只写eligibility/fence；ES-04以`process_detail_retention_v1`做最多500 rows/64MiB的bounded cleanup，ES-08负责60秒scanner与operation evidence。不得级联Task/Audit/Restart/Execution/Intake/derived/vector/event/log；清理前后public Task/items/generation/restart/lineage/proof canonical digest必须相同。

---

## 5. Contracts and Data

### 5.1 逻辑类型

沿用ES-01 UUID/time/JSON/digest约定。所有九张MKB-owned业务表均有`payload_extra NOT NULL DEFAULT '{}'`且核心代码不以其决定route/status/proof。Compiled cache、engine/FTS/vector私表不受业务表规则影响。

### 5.2 七张Workflow Truth表

#### 5.2.1 `workflow_registry`

| Columns | Constraints |
|---|---|
| `workflow_uuid, workflow_key` | UUIDv7 PK；key global UNIQUE、immutable |
| `domain_key, purpose_key, execution_role` | domain=`ls_rag`；purpose/role registered enums |
| `selector_key, selector_priority` | deterministic resolver；tie invalid |
| `read_exposure, registry_status` | exact enum `internal|readable`；exact enum `enabled|disabled|deprecated` |
| `active_revision_uuid` | nullable same-workflow ref；enabled必填 |
| `display_name, description` | display-only，不入运行digest |
| `created_at, updated_at, created_by_origin, payload_extra` | origin=`code/migration/bootstrap` |

Indexes：`UNIQUE(workflow_key)`、`(purpose_key,execution_role,registry_status,selector_priority,workflow_key)`。

#### 5.2.2 `workflow_revisions`

| Columns | Constraints |
|---|---|
| `workflow_revision_uuid, workflow_uuid, revision_number` | PK；`UNIQUE(workflow_uuid,revision_number)` |
| `schema_version, compiler_version, capability_registry_digest` | exact supported binding |
| `registration_source_kind/module/source_commit_digest/migration_key` | reproducible provenance |
| `registration_fingerprint` | same content replay key |
| `canonical_definition_digest, compiled_digest` | full runtime semantics |
| `registered_at, activated_at, registration_trace_uuid, payload_extra` | activated is evidence, not active SSOT |

Activated revision与所有children immutable；same number different fingerprint conflict。

#### 5.2.3 `workflow_steps`

`workflow_step_uuid PK`、`workflow_revision_uuid FK`、`step_key`、`step_kind=start|process|control|join|terminal`、`process_key/version?`、`phase_key?`、`requiredness=required|optional`、`terminal_kind=success|failure|cancelled|noop?`、`order_hint`、`display_name`、`payload_extra`。`UNIQUE(revision,step_key)`；process字段只在process step必填；每revision恰一start且至少一terminal。

#### 5.2.4 `workflow_routes`

`workflow_route_uuid PK`、revision、`route_key`、same-revision from/to step、`route_kind=normal|branch|fan_out|join|terminal`、`outcome_selector`、`priority`、`guard_group_key?`、`join_mode=none|all_required|all_terminal`、`predecessor_requiredness`、`payload_extra`。禁止self-edge；`UNIQUE(revision,route_key)`和`UNIQUE(revision,from_step,outcome_selector,priority)`。

#### 5.2.5 `workflow_bindings`

`workflow_binding_uuid PK`、revision/step、`binding_kind=context|input|output|parameter`、`slot_name`、`value_type`、`schema_ref/digest?`、`required`、`multiplicity=one|many`、source kind、same-revision source step/port或registry ref、typed literal columns、`payload_extra`。`UNIQUE(step,binding_kind,slot_name)`；literal恰一typed value；无opaque JSON/secret/path。

#### 5.2.6 `workflow_controls`

`workflow_control_uuid PK`、revision、scope revision/step/route、typed scope ref、`timeout_ms/lease_duration_ms/heartbeat_interval_ms`、`max_retries/retry_policy/backoff_*`、`max_recoveries/indeterminate_side_effect_policy`、`cancel_mode/cancel_grace_ms`、`case_mode/purge_mode/failure_policy`、`concurrency_limit/fan_out_limit/deadline_mode`、`payload_extra`。CHECK heartbeat<lease、数值非负、resolved max_recoveries非空。Precedence=`safe default<revision<step<selected route<Task deadline/priority tightening`。

#### 5.2.7 `workflow_guards`

`workflow_guard_uuid PK`、revision、scope route/terminal/proof、`scope_key`、`guard_group_key`、`group_mode=all|any`、`order_index`、`predicate_type/operand_kind/operand_ref/operator`、typed expected columns、`failure_code`、`failure_disposition=route_false|process_failed|execution_failed`、`payload_extra`。无nested group、script或inline unversioned set。

### 5.3 Workflow FK与immutability

所有child表必须以复合FK证明引用对象处于同一revision；`workflow_registry.active_revision_uuid`必须引用自身workflow。Registration事务结束后无child update/delete repository；ES-04以FK、partial unique、immutable trigger或restricted repository提供defense-in-depth。

### 5.4 `executions`

| Column group | Exact columns |
|---|---|
| Identity | `execution_uuid PK, team_uuid, task_uuid, trace_uuid, generation` |
| Tree | `root_execution_uuid, parent_execution_uuid?, retry_of_execution_uuid?, execution_role` |
| Immutable subject | `subject_kind, subject_source_uuid?, subject_item_uuid?, subject_revision_uuid?, subject_index_scope_ref?, subject_digest` |
| Accepted output | `accepted_snapshot_uuid?, accepted_change_set_digest?, accepted_item_uuid?, accepted_revision_uuid?` |
| Workflow binding | `workflow_uuid, workflow_revision_uuid, compiled_digest, resolver_decision_digest, capability_registry_digest` |
| Domain binding | `domain_binding_ref/digest, s05_binding_digest?` |
| Control | `status, revision, phase_key?, waiting_reason?, wait_ref?, next_wake_at?` |
| Focus | `current_process_uuid?, final_process_key?` |
| Scatter manifest | `manifest_revision?, manifest_digest?, expected/required/skipped_child_count` |
| Aggregate | process/child active/succeeded/failed/cancelled counts；delivery/recovery/retry totals |
| Cancel | `cancel_requested_at?, cancel_command_revision?, cancel_converged_at?` |
| Result/error | typed `result_ref/digest, publication_proof_ref/digest, final_error_*` |
| Summary | `terminal_summary_digest?, summary_completed_at?, phase_history_ref?` |
| Time/extension | created/ready/started/completed/updated；`payload_extra` |

`subject_kind`只允许`task_input/intake_source/intake_item_revision/intake_lifecycle_item/index_scope`，且CHECK要求对应typed列组合。Accepted output只能由ES-03 owner port成功结果一次性CAS填充，不能覆盖subject。

Constraints/indexes：

```text
PK (execution_uuid)
FK (team_uuid, task_uuid) -> tasks
FK root/parent/retry_of -> executions
UNIQUE (team_uuid, task_uuid, generation) WHERE parent_execution_uuid IS NULL
UNIQUE (root_execution_uuid, accepted_change_set_digest, accepted_item_uuid, accepted_revision_uuid)
INDEX (team_uuid, task_uuid, generation, created_at)
INDEX (root_execution_uuid, parent_execution_uuid, status)
INDEX (status, next_wake_at, updated_at)
INDEX (subject_item_uuid, subject_revision_uuid, created_at)
```

Waiting必须reason+ref；terminal必须completed/summary，succeeded必须proof；child task/generation/root/parent一致。`current_process_uuid`只引用本Execution且不表示active set。

### 5.5 `processes`

| Column group | Exact columns |
|---|---|
| Identity | `process_uuid PK, execution_uuid, team_uuid, task_uuid, root_execution_uuid` |
| Step/capability | `workflow_step_uuid/key, process_key, contract_version, phase_key, requiredness` |
| Materialization | `materialization_key, route_decision_digest, fan_out_item_key?` |
| Immutable spec | `process_spec_digest, input_manifest_ref/digest, control_snapshot_ref/digest, proof_kind` |
| State/schedule | `status, revision, available_at, priority_rank, deadline_at` |
| Claim | `claim_token_hash?, lease_owner?, lease_expires_at?, fencing_generation, heartbeat_at?` |
| Counters | `delivery_count, recovery_count, retry_count, max_retries, max_recoveries` |
| Retry | `next_retry_at?, last_failure_retryability?, backoff_policy_ref/digest` |
| Outcome | `accepted_outcome_digest?, output_manifest_ref/digest?, proof_ref/digest?` |
| Error | `error_class/code/message/details_ref?, failure_disposition?` |
| Cancel | `cancel_requested_at?, cancellation_evidence_ref/digest?` |
| Cleanup | `cleanup_eligible_at?, cleanup_fence_digest?` |
| Time/extension | created/claimed/started/completed/updated；`payload_extra` |

Constraints/indexes：

```text
PK (process_uuid)
FK execution_uuid -> executions
UNIQUE (execution_uuid, workflow_step_uuid, materialization_key)
INDEX (status, available_at, priority_rank DESC, deadline_at, process_uuid)
INDEX (lease_expires_at, status)
INDEX (execution_uuid, created_at, process_uuid)
INDEX (team_uuid, task_uuid, status)
CHECK counters >= 0 AND retry_count <= max_retries AND recovery_count <= max_recoveries
```

Claim字段只在claimed/running/cancelling可存在；ready/retry_wait/terminal无有效lease。Succeeded必须Outcome/output及manifest-required proof；failed有structured error；cancelled有convergence evidence。Terminal事实immutable，只可单调追加cleanup evidence。

### 5.6 Compiled workflow contract

`mkb.workflow-compiled.v1`包含workflow/revision/digests、sorted steps/routes/bindings/controls/guards，不含runtime UUID、secret/path或actual input。Cache key=`workflow_revision_uuid+compiled_digest`；compiled artifact可存ES-04 artifact cache，但不是第八张Truth表。

### 5.7 ProcessCapabilityManifest

ES-02编译/运行消费ES-05的`mkb.process-capability-manifest.v1`：`process_key/contract_version/handler_key`、allowed phases、typed input/output ports、parameter specs、Outcome schema、proof kind/schema、side-effect class、idempotency recipe、retry error policy和resource access。Execution/Process均bind exact key/version/digest；缺失或digest drift fail-loud，不切latest。

### 5.8 ProcessCommand

```json
{
  "schema_version": "mkb.process-command.v1",
  "identity": {
    "team_uuid": "...", "task_uuid": "...", "trace_uuid": "...",
    "root_execution_uuid": "...", "execution_uuid": "...", "process_uuid": "..."
  },
  "workflow": {
    "workflow_revision_uuid": "...", "compiled_digest": "sha256:...",
    "step_key": "...", "process_key": "...", "contract_version": "...", "phase_key": "..."
  },
  "resources": {},
  "inputs": {},
  "parameters": {},
  "control": {},
  "claim": {
    "delivery_uuid": "...", "claim_token": "secret-on-wire",
    "fencing_generation": 4, "lease_expires_at": "..."
  },
  "integrity": {
    "process_spec_digest": "sha256:...", "command_digest": "sha256:...", "issued_at": "..."
  }
}
```

Resources/inputs/parameters只包含manifest允许的typed logical refs/handles；无physical path、secret value、complete Workflow或Task mutation capability。Runner执行前验证schema、digest、token/fence、deadline。

### 5.9 ProcessOutcome

`mkb.process-outcome.v1`包含相同identity/workflow correlation、claim token/fence、`outcome_status`、typed output handles/schema/digest、proof ref/digest、failure retryability+structured error、started/completed time、bounded metrics、outcome digest/idempotency key。禁止next step、route override、Task/Execution terminal、absolute path或raw secret。

Outcome接受事务：验证identity/revision/spec/fence→manifest output/proof guard→Process transition→route decision→Execution aggregate→next materialization/outbox→event→commit。任何一步失败不得接受部分Outcome。

### 5.10 Application ports

```python
class WorkflowRegistryPort(Protocol):
    async def register(self, bundle: WorkflowBundleV1) -> RegisteredRevision: ...
    async def resolve(self, query: WorkflowResolveQueryV1) -> WorkflowBindingV1: ...

class ExecutionEnginePort(Protocol):
    async def start_task(self, message: TaskStartRequestedV1) -> None: ...
    async def request_cancel(self, message: TaskCancelRequestedV1) -> None: ...
    async def aggregate(self, execution_uuid: UUID) -> ExecutionView: ...

class ProcessSchedulerPort(Protocol):
    async def claim(self, request: ClaimRequestV1) -> ClaimedProcess | None: ...
    async def start(self, command: StartClaimV1) -> ProcessCommandV1: ...
    async def heartbeat(self, heartbeat: HeartbeatV1) -> LeaseView: ...
    async def submit(self, outcome: ProcessOutcomeV1) -> OutcomeReceiptV1: ...

class SemanticRecoveryPort(Protocol):
    async def scan(self, shard: ScanShardV1) -> RepairBatchResult: ...

class IntakeRuntimePort(Protocol): ...
class GateRuntimePort(Protocol): ...
class CapabilityRegistryPort(Protocol): ...
class DerivedAssetPort(Protocol): ...
class VectorPublicationPort(Protocol): ...
class TaskAggregateOwnerPort(Protocol): ...  # ES-01 implementation
class UnitOfWorkPort(Protocol): ...           # ES-04 implementation
```

### 5.11 Durable messages/events

| Message/event | Producer→consumer | Key guard |
|---|---|---|
| `task.start-requested.v1` | ES-01→ES-02 | unique Task generation root |
| `task.cancel-requested.v1` | ES-01→ES-02 | command/generation idempotency |
| `process.wake-requested.v1` | Engine→runner lane | Process exists+ready/due；wake非Truth |
| `process.outcome-submitted.v1` | runner→Engine | current token/fence+outcome digest |
| `execution.child-materialize-requested.v1` | root→Engine | ChangeSet member uniqueness |
| `gate.open/resolved.v1` | ES-03↔ES-02 | exact Execution fence/target/revision |
| `task.aggregate-proposed.v1` | ES-02→ES-01 | root/generation/proof/status edge |
| `workflow.repair-requested.v1` | ES-08 scanner→ES-02 | drift evidence+same transition path |

所有消息at-least-once；outbox由ES-04持久化。Domain events保存route/Outcome/transition/repair证据但不替代current projection。

---

## 6. State / Consistency / Failure

### 6.1 Runtime不变量

1. 每Task generation恰一root；每Process恰一Execution。
2. Workflow binding、subject和accepted output分账且不可热切。
3. 只有eligible route materialize Process；skip只留decision evidence。
4. Process spec/outbox commit前runner不可见。
5. 当前fence唯一；stale Outcome永不提交。
6. delivery/recovery/retry三账不混。
7. Execution succeeded必须满足required Process/children与type proof。
8. Human wait无active Process lease且有exact Gate ref。
9. Cancel阻止新materialization/claim，直到descendants收敛才terminal。
10. Nonterminal Execution始终满足progress invariant。

### 6.2 Failure disposition

| Failure class | Process effect | Execution effect |
|---|---|---|
| transient allowlisted | retry_wait if budget | running/waiting |
| non-retryable business | failed | required path最终failed；optional按policy |
| contract/schema/proof invalid | failed/integrity | failed，quarantine evidence |
| lease safe replay | recovery→ready | unchanged |
| lease indeterminate/non-replayable | failed `indeterminate-side-effect` | required path failed |
| recovery exhausted | failed `recovery-exhausted` | required path failed |
| deadline before claim | failed | aggregate by requiredness |
| cancel | cancelling→cancelled | descendants收敛后cancelled |
| missing/digest drift | no execution or failed | fail-loud，不fallback |

### 6.3 Side-effect safety

Manifest的`side_effect_class`为`pure/idempotent_by_key/transactional_sink/non_replayable`。Pure/idempotent可在新fence恢复；transactional sink必须通过sink-owned idempotency/publication key查询确认；non_replayable或无法确认的写入一律indeterminate failed。Idempotency key必须包含stable business publication identity，不能只含易变delivery UUID。

### 6.4 Concurrency与backpressure

- Claim必须同时满足global lane、capability、Workflow control与fan-out limit，取最严格值；
- concurrency slot不是状态，crash后从lease/claim Truth恢复；
- fan-out分批只影响wake，不改变committed expected set；
- deadline/priority只影响调度，不改变route/proof；
- runner没有权限自行创建next Process或延长max budget。

### 6.5 Terminal summary与cleanup

Execution terminal summary至少含workflow/capability digests、route/process/child counts、retry/recovery/delivery totals、phase history、error、Intake/derived/vector refs、PublicationProof、ChangeSet和时间。Summary digest完成前不得Process cleanup。Cleanup后Execution、Task、items/restart/lineage/proof仍可完整解释。

### 6.6 Drift protocol

Citation drift更新引用；semantic drift（状态、owner、edge、state-vs-fact、cutoff）必须同时更新Owner Truth/D02/相关ES，未校准前新分支fail-closed。Exact Process key、manifest digest、Workflow revision或proof conflict不能自动选择closest/latest。

---

## 7. Legacy Retain / Rewrite / Drop

| Legacy practice | Retain | Rewrite | Drop |
|---|---|---|---|
| Clean/RAG dispatcher step rows | durable-before-dispatch、step identity、input/output/error/retry | unified Process table + outbox/fence | clean/rag分表、`pending/completed/retrying` aliases |
| Mapper/IO renderer | declared input mapping、多平面command | typed ports/bindings + ProcessCommand | arbitrary JSON template、physical path、full context dump |
| Callback progression | Outcome驱动next step | local Outcome submission+transactional route | callback/HTTP response作为success |
| RAG case-mode skip | controlled branch需求 | typed guards/routes与decision evidence | step-name substring、implicit fallback |
| Queue/DO dual dispatch | async并发与crash风险证据 | one in-process scheduler lane + committed outbox | Cloudflare Queue/DO bindings与waitUntil window |
| Restarter | same-step retry、max budget、history诊断 | automatic retry/recovery + full Task generation | public force-stage restart、queue-first DB-later |
| Scatter relations | complete member set、siblings并行 | accepted ChangeSet root+children collect-all | child Task、first-child hint、parent passive completion |
| Stuck pending helper | recovery行为必要 | deterministic progress scanner/same transition service | 未接线函数冒充可靠性、generic Reconciler产品 |

---

## 8. Acceptance Evidence

本节60项全部为`HARD`；实现任一失败即conformance/release blocked，且不得以queue成功、manual repair或部分Workflow通过替代。

### 8.1 Workflow definition/compiler

| ID | Scenario | HARD assertion |
|---|---|---|
| `ES02-A001` | 注册合法bundle | 七表原子提交、active pointer正确 |
| `ES02-A002` | registration逐点失败 | 无partial child/pointer/cache |
| `ES02-A003` | same fingerprint replay | 同revision，不增行 |
| `ES02-A004` | same revision number different content | conflict，pointer不变 |
| `ES02-A005` | cross-revision wiring | DB/compiler reject |
| `ES02-A006` | cycle/self-edge/unreachable/no terminal | reject |
| `ES02-A007` | route tie/script/SQL/free expression | reject |
| `ES02-A008` | capability/port/digest mismatch | reject/fail-loud |
| `ES02-A009` | compile 1,000次 | canonical bytes/digest identical |
| `ES02-A010` | cache delete | 七表重建同digest |
| `ES02-A011` | external Workflow CUD/task override | 405/strict reject，无truth变化 |
| `ES02-A012` | registry revision activation | old Execution unchanged；new independent Task uses new revision |

### 8.2 Process state/claim/outcome

| ID | Scenario | HARD assertion |
|---|---|---|
| `ES02-A013` | Process状态边穷举 | 只允许§4.5 |
| `ES02-A014` | eligible materialization crash | Process/spec/outbox all-or-none |
| `ES02-A015` | 100 concurrent claims | one token/fence winner |
| `ES02-A016` | duplicate delivery | no new Process/business write；delivery count可增 |
| `ES02-A017` | stale token/fence Outcome | reject，truth unchanged |
| `ES02-A018` | accepted Outcome replay | idempotent same receipt |
| `ES02-A019` | output/proof schema invalid | Process/Execution不得success |
| `ES02-A020` | retryable failure | same Process retry_wait，retry_count+1 |
| `ES02-A021` | due retry | retry_wait→ready→new claim/fence |
| `ES02-A022` | non-retryable/max exhausted | Process failed，Execution可归约 |
| `ES02-A023` | safe lease expiry | recovery_count+1、retry不变、old fence invalid |
| `ES02-A024` | indeterminate lease expiry | failed，不自动重跑 |
| `ES02-A025` | recovery budget exhausted | failed recovery-exhausted，无wake |
| `ES02-A026` | deadline before claim | failed deadline-exceeded-before-start |

### 8.3 Execution/single/scatter

| ID | Scenario | HARD assertion |
|---|---|---|
| `ES02-A027` | Execution状态边穷举 | 只允许§4.6；terminal immutable |
| `ES02-A028` | single ingest | one root贯穿clean→publication；proof上卷 |
| `ES02-A029` | rebuild | exact Revision；无acquisition/新Revision |
| `ES02-A030` | clean skip | registered guard/evidence；无fake Process |
| `ES02-A031` | mandatory preflight runtime error | Process retry/failed；无Gate |
| `ES02-A032` | preflight passed+allowlisted | direct route；无fake Gate |
| `ES02-A033` | human review | Process terminal；Execution waiting+Gate ref；无lease |
| `ES02-A034` | Gate approve/override/reject/reclean/stale | same Execution resume/fail或最多一次acyclic remediation；stale conflict，无hot switch/loop |
| `ES02-A035` | ChangeSet N required | exactly N unique children；各自绑定accepted Revision并在LS-RAG前执行item-scoped clean/preflight |
| `ES02-A036` | partial child materialization crash | recovery补齐且不重复 |
| `ES02-A037` | child failure with siblings active | collect-all；siblings continue |
| `ES02-A038` | all terminal mixed | root failed；proof-valid child remains ready |
| `ES02-A039` | all proof-valid | root/Task success proposal and exact counts |
| `ES02-A040` | zero-required | typed terminal proof；不靠queue empty |

### 8.4 Cancel/recovery/cleanup

| ID | Scenario | HARD assertion |
|---|---|---|
| `ES02-A041` | cancel/success race 1,000次 | one durable winner，无双终局 |
| `ES02-A042` | late Outcome after cancel | stale fence reject |
| `ES02-A043` | cancel with published child | child retained；no purge |
| `ES02-A044` | ready wake lost | scanner补wake，不建Process |
| `ES02-A045` | terminal→next crash | exact decision补materialization |
| `ES02-A046` | waiting without reason/ref | invariant fail+evidence |
| `ES02-A047` | recovery repeated 100次 | row/outcome/child/business effect不增 |
| `ES02-A048` | digest/proof conflict | failed quarantine；不猜latest |
| `ES02-A049` | cleanup fence任一未闭合 | no eligible/delete |
| `ES02-A050` | cleanup全部满足 | pointer clear、summary complete、eligible proof |
| `ES02-A051` | before/after Process cleanup | Task/items/generation/lineage/proof等价 |
| `ES02-A052` | compiled/command/outcome leak scan | 无secret/path/platform data/full Workflow in command |

### 8.5 ES-07 rebuild route calibration

| ID | Scenario | Expected |
|---|---|---|
| ES02-A053 | index rebuild team/source/item/revision scope | one immutable plan；item set/order/digest exact |
| ES02-A054 | root crash during child materialization | plan set-diff补exact children，无duplicate/re-enumeration |
| ES02-A055 | reuse child route | build_item→validate；vector.embed/stage Process count 0 |
| ES02-A056 | reembed child route | vector.embed→stage→validate；build_item Process count 0 |
| ES02-A057 | caller/root/child mode confusion | manifest/start guard typed reject，无route guessing |
| ES02-A058 | stale plan item fence | child conflict terminal；不替换latest或重枚举 |
| ES02-A059 | mixed child outcomes | collect-all root failed；proof-valid sibling publication保留 |
| ES02-A060 | all child proofs valid | root succeeded with exact plan/count/proof aggregate |

### 8.6 Evidence package

1. 七表与两runtime表的physical DDL mapping、FK/unique/check/immutability报告；
2. compiler static validation与canonical digest golden fixtures；
3. default Workflow catalog compiled snapshots；
4. ProcessCapabilityManifest compatibility matrix；
5. Execution/Process exhaustive state property tests；
6. claim/fence/retry/recovery/cancel并发和failure injection；
7. single/scatter/metadata/lifecycle及root-plan/child-route index rebuild golden journeys；
8. semantic recovery matrix与cleanup equivalence；
9. legacy retain/rewrite/drop对照及零runtime dependency scan。

---

## 9. Remaining Technical Decisions and Defaults

以下均为execution默认，不提交Owner：

| Topic | v1 default | 变更证据 |
|---|---|---|
| Workflow registration | startup migration/bootstrap；bundle fingerprint幂等 | compiler/transaction tests |
| Compiler | pure deterministic Python；canonical JSON+SHA-256 | cross-run golden bytes |
| Scheduler | same-process DB/outbox polling lane；at-least-once | lost/duplicate wake tests |
| Claim batch | 16；单事务逐行CAS | contention/load evidence可调 |
| Global runtime concurrency | default 8；per-capability/Workflow取更小限制 | ES-08实测安全包络，不是产品SLA |
| Lease | default 60s；heartbeat 15s | workload p99/GC pause测量；heartbeat始终<lease |
| Max recoveries | default 3，materialization时固化 | indeterminate/recovery exhaustion tests |
| Business retry | default transient-only max 3；1s exponential、max60s、10% deterministic jitter | capability error evidence可收紧 |
| Runner timeout | capability manifest mandatory；default ceiling 15min | ES-05/08 model/IO measurement |
| Priority map | urgent=400/high=300/normal=200/low=100 | 调度公平性测试；不改变语义 |
| Route loops | v1禁止；retry不画graph loop | compiler gate |
| Compiled cache | in-memory + optional ES-04 artifact cache | cache deletion rebuild test |
| Physical Process cleanup | enabled only after terminal 90d；batch≤500 rows/64MiB；其余时间只计算eligibility | ES-08-v1.0 retention/runbook + ES-04-v1.0 UoW；equivalence/fault evidence |
| Workflow read | internal-token read-only，page default50/max200 | no CUD/secret leak tests |

---

## 10. Revision History

| 版本 | 日期 | 状态 | 变更 |
|---|---|---|---|
| `ES-02-v0.1` | `2026-08-10` | `internally-consistent / awaiting cross-spec audit` | 继承D01-v1.4、D02-v1.0、S02-v1.3与S03-v1.3冻结Truth，完整冻结六平面Workflow、七张normalized定义表、deterministic compiler、八个有限Workflow、Execution/Process两张runtime表及两个八态StateFamily、typed route/guard、ProcessCommand/Outcome、claim/lease/fence、三账retry/recovery、single/scatter、Gate、cancel、semantic repair和cleanup eligibility；以`vector.embed/index.stage_generation/index.validate_publication`取代旧coarse vectorize alias。未新增产品能力、runtime身份、StateFamily、部署单元或spec文件。 |
| `ES-02-v0.2` | `2026-08-10` | `internally-consistent / awaiting cross-spec audit` | 与S04-v1.2/S05-v1.1及ES-03-v0.1校准：root ingest链固定为mandatory preflight→seal→accept；scatter child在LS-RAG前执行exact accepted Item/Revision clean与item-scoped preflight；Gate reclean只允许同一S05 binding下一个编译期显式、acyclic、最多一次的remediation branch，并补齐acceptance。未新增Process key、状态、intent、Workflow、部署单元或产品能力。 |
| ES-02-v0.3 | 2026-08-10 | internally-consistent / awaiting cross-spec audit | 与ES-07-v0.1校准既有index.rebuild.v1：index.rebuild_generation以closed plan_scope/build_item mode复用，root冻结scope并bounded fan-out，child按reuse或reembed exact route执行后collect-all；新增8项route/fence/fan-in acceptance。仍为八个Workflow、既有六个ES-07 Process key、两个runtime StateFamily和一个发布单元，未新增产品能力。 |
| ES-02-v1.0 | 2026-08-10 | ready | 完成OT-01..04、D01/D02、S02/S03及ES-01/03/05/07/08最终对账；8个Workflow、26个Process manifest、Execution/Process两族状态、9张owner tables与60项HARD acceptance均已set-exact。未新增状态族、Workflow、Process、服务或spec文件。 |
