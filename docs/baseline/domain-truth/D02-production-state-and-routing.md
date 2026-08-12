# D02 — Production State Constitution & Domain State Ledger

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 共有域**：跨 `D2-D6 / S01-S09` 的生产状态所有权、状态契约镜像与一致性校准
>
> **文档性质**：`shared-domain constitution / normative state ledger`
>
> **文档状态**：`frozen / owner-approved / campaign closed`
>
> **Truth 版本 / 日期**：`D02-v1.0 / 2026-08-10`
>
> **作者**：`MKB owner + Codex`
>
> **冻结来源**：`qna-truth/D02.md v1.0`；`T-O-86..92`
>
> **权威输入**：`D01-v1.4`、`S01-v1.5`、`S02-v1.3`、`S03-v1.3`、`S04-v1.2`、`S05-v1.1`、`S06-v1.0`、`S12-v1.0`（`T-O-97..110`）
>
> **词汇权威**：`spec-glossary.md v1.4`
>
> **下游消费者**：`S06-S16`、System Topology、Acceptance/Truth Freeze、实现计划与验收

> **冻结边界**：D02-v1.0只冻结共有状态宪法、六个StateFamily的规范镜像、跨域非法行为和镜像/漂移协议。具体业务流程、route算法、exact业务kind、API与DDL仍归对应下游Truth层。D02已冻结不代表整个`docs/baseline/`已完成最终Truth Freeze。

> **阅读权威**：§0-§3、§5-§6为规范正文；§4是non-normative调查附录，不得直接生成enum、route、API、DDL或验收断言。附录与正文冲突时，以最新owner-frozen正文及其权威下游源Truth为准。

---

## 0. Constitution Core（规范）

### 0.1 D02拥有与不拥有的权威

D02是MKB共有域状态宪法和可核查镜像ledger。它只拥有四类规范权威：

1. 哪些对象拥有StateFamily以及唯一owner；
2. status与phase、reason、Outcome、readiness、pointer、proof等正交事实的分账规则；
3. 控制向下、proof/summary向上及跨域不得抢写的共同不变量；
4. 下游状态Truth如何镜像、发现漂移并完成双向校准。

D02不拥有：

- 某个业务域具体如何运行、分支、fan-out/fan-in或选择下一Process；
- S06-S09 exact artifact/node/process/index kind；
- 公共API、物理表数、DDL、driver、retention数值或运营平台；
- 名为`ProductionStateProjection`的公共产品、runtime identity或反向写面；
- 为未来扩展预建的第七状态族、动态状态registry或治理服务。

### 0.2 冻结Truth

| Truth | 冻结内容 | 强制影响 |
|---|---|---|
| `T-O-86` | D02是共有域状态宪法，冻结上层形状、所有权与非法行为 | D02不得吞并下游业务Spec；下游不得违反共有宪法 |
| `T-O-87` | 命中D02的下游冻结Truth必须与D02双向校准并镜像 | 只放链接或只改一边均不算完成 |
| `T-O-88` | v1只有六个StateFamily，其余生产信息按typed fact分账 | 禁止global、stage-specific、组合状态或第七StateFamily |
| `T-O-89` | 具体执行/路由归对应下游Truth层，冻结后再回填D02 | D02不替S03/S06-S09决定Workflow、Process或route算法 |
| `T-O-90` | D02采用短Core、分域Ledger、Conflict/Drift Register、non-normative Appendix四层单文件结构 | Appendix不能成为第二真相 |
| `T-O-91` | 下游只回填六项最小状态契约镜像块 | 不复制完整schema、算法、DDL、API或实施计划 |
| `T-O-92` | citation drift机械校准；semantic drift显式gate并同轮双向更新 | 冲突期间沿用最后一致Truth且新分支fail-closed |

### 0.3 v1唯一六个StateFamily

| StateFamily | 唯一owner | Exact states | 权威源 |
|---|---|---|---|
| Task aggregate | S02 | `queued/running/cancelling/succeeded/failed/cancelled` | S02-v1.3 §2.3/§4.2 |
| Execution control | S03 | `created/ready/running/waiting/succeeded/failed/cancelling/cancelled` | S03-v1.3 §2.6/§4.9 |
| Process control | S03 | `ready/claimed/running/retry_wait/succeeded/failed/cancelling/cancelled` | S03-v1.3 §2.5/§4.8 |
| IntakeItem lifecycle | S04 | `active/deactivated/deleted` | S04-v1.2 §2.4/§3.5/§4.5 |
| IntakeCandidateSet staging | S04/S05 contract | `open/sealed/accepted/abandoned` | S04-v1.2 §2.5/§3.5；S05-v1.1 §3.7 |
| ExecutionGate | S05 | `open/released/rejected/superseded` | S05-v1.1 §2.5/§3.9/§4.5 |

只有具备唯一owner、合法transition与写入guard的集合才称为StateFamily。新增状态诉求必须回到owner domain证明现有状态机无法表达合法控制边；不得直接扩展D02。

### 0.4 正交typed facts

| Fact family | Owner | 例子 | 明确不是 |
|---|---|---|---|
| Task查询/聚合事实 | S02 | result readiness、TaskItem outcome、`action_required`、soft-delete visibility | Task status |
| Execution业务坐标 | S03 | `phase_key`、`waiting_reason`、terminal summary、active-set summary | Execution status |
| Process结果与调度账 | S03 | ProcessOutcome、retryability、retry/recovery/delivery count、lease/fence | Process status |
| Intake observation/decision | S04 | Source admission fence、Snapshot completeness/authority、Membership decision、ChangeSet | Snapshot或Item附加状态机 |
| Selection/publication | S04/S06/S09 | latest/serving/current/active pointer、PublicationProof | lifecycle或业务成功的替代物 |
| Cleaning/admission结果 | S05 | AcquisitionEvidence、PreflightOutcome、ReviewTarget、GateDecision | Process或Gate current status |
| S06 generation事实 | S06 | GenerationArtifact、GenerationInvocation、per-type current pointer、validation proof | 第七StateFamily |
| Physical convergence | S04/S09/S13 | CleanupIntent/Proof、substrate existence、retention eligibility | 业务可见性SSOT |

这些事实必须有typed schema、唯一owner和校验；“不是状态”不意味着可以放进`payload_extra`、日志或queue中充当隐式Truth。

### 0.5 共同控制方向

```text
external command
  → Task intent
    → Execution control
      → Process command / claim / cancel

typed Outcome + immutable asset/proof
  → Process transition guard
    → Execution summary/transition guard
      → Task aggregate/result readiness

durable Intake/S06/S09 truth survives runtime cleanup
```

冻结不变量：

1. control intent只向下传播；下层只提交typed Outcome/proof，不反向改写上层状态；
2. 各StateFamily只由owner transition service推进，跨域只能发command或提交typed fact；
3. queue delivery、HTTP返回、日志、projection、`payload_extra`和“文件存在”均不是业务状态或成功证明；
4. terminal状态不可原地复活；合法retry/rebuild通过已冻结generation或新Task因果表达；
5. Task terminal不自动回滚已proof-valid Intake/serving资产；runtime失败也不能偷偷改变IntakeItem lifecycle；
6. phase、reason、Outcome、readiness、pointer与proof可以并列查询，但组合投影不得反向成为SSOT；
7. 未冻结的exact kind、route或DDL必须fail-closed，不得从附录或legacy命名猜测。

### 0.6 共有非法行为

- 跨owner合并状态或建立裸`production_status`；
- 创建`reviewing/retrying/vector_ready/latest_unpublished`等stage-specific或组合状态；
- 把`phase_key`、Outcome、readiness、pointer、proof或cleanup进度命名为通用`status`；
- 用未注册alias制造双真相，例如用`pending/scheduled`替代exact state；
- Process、queue consumer、API controller或projection直接推进非本owner状态；
- 从log、queue ACK、mutable latest、`payload_extra`或物理文件反推业务Truth；
- 下游修改状态/边/owner/cutoff后只改源Spec而不回填D02；
- D02以“共有域”为名替下游冻结业务算法、kind全集、API或DDL。

---

> **S13校准声明**：`S13-v1.0` 冻结 v1 本地 `object_root` + `ObjectStorePort`、`mkbobj:v1` handle、team-scoped CAS、bytes-first、同库 catalog/ref/purpose、verify-on-read、周期 GC 与 identity readiness。本文件业务语义不变；对象 I/O 必须经 S13 Port，禁止 path/R2 key 进入契约。

## 1. Domain State Ledger（规范）

### 1.1 镜像块格式与更新触发

依据`T-O-91`，每个镜像块只保存六项：权威来源、状态所有权、exact状态/合法边或`not a state machine`声明、跨域输入输出、非法行为、校准影响。

只有以下语义变化触发D02共同校准：新增/删除/改名状态、改变合法边或owner、改变state-vs-fact分类、新增影响route/control的正交fact、改变跨域cutoff，或发现镜像错误。普通文字润色、实现优化及domain内部非状态字段不触发。

### 1.2 Task aggregate mirror

| 镜像项 | 冻结值 |
|---|---|
| 权威来源 | S02-v1.3 §2.2-§2.6、§4.2；`T-O-1..11`；D02 `T-O-88` |
| 状态所有权 | S02 Task transition service；外部只能create/PATCH允许字段/command，S03只提交可聚合summary/proof |
| exact状态与合法边 | create→`queued`；queued→running/cancelling；running→succeeded/failed/cancelling；cancelling→cancelled；failed/cancelled经full retry→queued且创建新generation/root；succeeded rebuild创建新Task |
| 跨域输入输出 | 输入为RequestIntent、current root Execution summary与type-specific proof；输出为caller-visible aggregate、readiness及bounded action_required |
| 非法行为 | 无`waiting/retrying/reviewing/partially_succeeded/deleted`状态；soft-delete、TaskItem mixed outcome和result readiness不得污染六态 |
| 校准影响 | S01 polling/API、S03 aggregation、S04/S05资产与gate投影必须继承；父Task失败/取消不得隐藏已proof-valid child |

### 1.3 Execution control mirror

| 镜像项 | 冻结值 |
|---|---|
| 权威来源 | D01-v1.4；S03-v1.3 §2.6/§2.9/§4.9；`T-O-25..27`；D02 `T-O-88` |
| 状态所有权 | S03 Engine/Execution transition service；leaf Process、Task API与Gate handler均不得直写 |
| exact状态与合法边 | create→`created`；created→ready/failed/cancelling；ready→running/waiting/failed/cancelling；running↔waiting；running/waiting→succeeded/failed/cancelling；cancelling→cancelled；terminal不可回active |
| 跨域输入输出 | 输入为bound Workflow truth、Process Outcome/proof、child set和Gate decision；输出为Process materialization/control、terminal summary及Task aggregate输入 |
| 非法行为 | waiting必须有typed reason+durable ref；human wait不得持active Process lease；phase不是状态；terminal前必须完成required proof与summary |
| 校准影响 | S02只读取aggregate，S04/S05只提交资产/decision fact，S06-S09只通过Process contract参与；exact业务route仍归下游 |

Execution的冻结waiting reason是`retry_due/process_join/scatter_children/durable_prerequisite/human_review`。`phase_key`是业务焦点坐标：created可空，ready/running/waiting必须确定，cancelling/terminal保留last/focus；它不是第九状态。

### 1.4 Process control mirror

| 镜像项 | 冻结值 |
|---|---|
| 权威来源 | D01-v1.4；S03-v1.3 §2.4-§2.5/§4.7-§4.8；`T-O-20..24`；D02 `T-O-88` |
| 状态所有权 | S03 Process transition/claim service；leaf handler只接收ProcessCommand并提交带current fence的ProcessOutcome |
| exact状态与合法边 | materialize→`ready`；ready→claimed；claimed→running；claimed/running经fenced recovery→ready或failed；running→retry_wait/succeeded/failed/cancelling；retry_wait→ready/cancelling；ready/claimed→cancelling；cancelling→cancelled；terminal不可回active |
| 跨域输入输出 | 输入为eligible route、typed refs、lease/fence与cancel；输出为typed Outcome、artifact/proof refs及可验证副作用摘要 |
| 非法行为 | 禁止ready→succeeded、retry_wait→running、stale fence mutation、queue ACK→success；delivery/recovery/retry不得混成新Process或Attempt |
| 校准影响 | S05-S09 exact capability由各域冻结后绑定S03 manifest；D02不决定工序粒度或next step |

ProcessOutcome的`outcome_status=succeeded/failed/cancelled`及`retryability=retryable/non_retryable/indeterminate`是immutable结果事实，不是Process current state。

### 1.5 IntakeItem lifecycle mirror

| 镜像项 | 冻结值 |
|---|---|
| 权威来源 | S04-v1.2 §2.4/§3.5-§3.6/§4.4-§4.5；`T-O-34..35/T-O-40..41/T-O-45..46`；D02 `T-O-88` |
| 状态所有权 | S04 Intake transition service；Task/Execution/Process/S09不得直写lifecycle |
| exact状态与合法边 | create→`active`；active→deactivated/deleted；deactivated→active/deleted；deleted为v1 terminal；accept_revision/publish_revision/no-change不创建新lifecycle state |
| 跨域输入输出 | 输入为accepted Snapshot/Membership/ChangeSet、versioned ActionDefinition、expected state/pointer与proof；输出为lifecycle truth、latest/serving pointer及cleanup intent |
| 非法行为 | deleted不可ordinary restore；deactivated必须先reactivate并另行proof-valid publish；runtime failure/cancel不得偷偷deactivate/delete；physical purge不得决定业务可见性 |
| 校准影响 | S02 result与S10 retrieval必须依赖canonical lifecycle+serving proof，而非父Task terminal或vector existence |

`latest_revision_uuid`、`serving_revision_uuid`、S06 GenerationArtifact current pointer和S09 active generation pointer是不同owner的SelectionPointer；不得用裸`latest/current`混用。

### 1.6 IntakeCandidateSet staging mirror

| 镜像项 | 冻结值 |
|---|---|
| 权威来源 | S04-v1.2 §2.5/§3.5/§4.3；S05-v1.1 §2.3/§3.7/§4.1-§4.3；`T-O-38..39/T-O-43..44/T-O-59..65`；D02 `T-O-88` |
| 状态所有权 | S05 producer写open pages并请求seal；S04 canonical acceptance service独占sealed→accepted；abandon由受围栏的staging transition完成 |
| exact状态与合法边 | create→`open`；open→sealed/abandoned；sealed→accepted；accepted/abandoned terminal；sealed duplicate只可幂等重放acceptance |
| 跨域输入输出 | 输入为producer Execution fence、pages/root/count/digest、Artifact refs、scope/completeness与PreflightOutcome；输出为accepted Snapshot/ChangeSet/child intents或abandon fact |
| 非法行为 | open不得accept；sealed不得追加/替换页面或热切validator；abandoned不得建Snapshot；Candidate state不得替代producing Process status |
| 校准影响 | S03 scatter/join、S04 Snapshot acceptance、S05 preflight与S06 exact input必须继承同一线性化点 |

### 1.7 ExecutionGate mirror

| 镜像项 | 冻结值 |
|---|---|
| 权威来源 | S05-v1.1 §2.5/§3.9/§4.5；`T-O-53..58/T-O-73/T-O-75..76`；D02 `T-O-88` |
| 状态所有权 | S05 Gate transition service拥有Gate；S03拥有对应Execution waiting/resume；Decision以append+CAS+outbox提交 |
| exact状态与合法边 | need-review→`open`；open→released/rejected/superseded；三者terminal且不可reopen |
| 跨域输入输出 | 输入为exact ReviewTarget、Artifact/evidence digest、Execution fence与authority；输出为immutable GateDecision和same-Execution wake/failure/branch fact |
| 非法行为 | passed自动路径不建伪gate；HTTP/UI点击不等于release；stale target/fence不得提交；Gate状态不得写入IntakeItem或Task status |
| 校准影响 | S02只投影bounded action_required并提供Task-scoped command；S03在waiting(human_review)时不得让Process持lease |

### 1.8 正交事实镜像摘要

| Typed fact | Exact值/当前边界 | Owner | State machine? |
|---|---|---|---|
| Task result readiness | `not_ready/ready/terminal_failed/terminal_cancelled` | S02 | `no` |
| TaskItem outcome | `active/succeeded/failed/cancelled/skipped` | S02 projection | `no` |
| Execution waiting reason | `retry_due/process_join/scatter_children/durable_prerequisite/human_review` | S03 | `no` |
| ProcessOutcome | `succeeded/failed/cancelled` + retryability | S03 contract | `no` |
| Snapshot completeness | `complete/partial`；failure不形成Snapshot | S04 | `no` |
| Membership decision | `seen/new-revision/no-change/absence`语义族；exact DB spelling归S04 | S04 | `no` |
| AcquisitionEvidence result | `succeeded/rejected/failed` | S05 | `no` |
| PreflightOutcome result | `passed/blocked`；runtime/schema/evidence error走Process failure | S05 | `no` |
| GenerationArtifact current selection | per Execution + artifact type的full-valid CAS pointer | S06 | `no` |
| Publication/Cleanup proof | exact target/digest/version的immutable evidence | owner domain | `no` |

---

## 2. Conflict & Drift Register（规范）

### 2.1 冻结处理协议

依据`T-O-92`：

1. 发现canonical name、owner、enum、合法边、state-vs-fact或非法行为不一致时，先登记双方精确版本/Truth；
2. 只更新版本号、章节或链接且语义不变属于citation drift，可机械修正；
3. 上述语义内容变化属于semantic drift，必须显式reopen受影响Truth；
4. 不以文件更新时间、较新版本或“实现已经如此”自动决定语义权威；
5. 裁决后在同一校准工作单元更新下游源Truth、D02镜像与双方revision history；
6. 关闭前沿用最后一致Truth，对新增分支/enum/alias/route fail-closed；
7. v1使用人工checklist与全文搜索，不建设自动同步器、schema generator或状态治理平台。

### 2.2 D02-v1.0下游移交登记

| ID | 事项 | Owner domain | D02已冻结的防线 | 状态 |
|---|---|---|---|---|
| `D02-DR001` | Execution immutable subject与运行后accepted output binding的exact字段/DDL | S03/S04 | subject、output与pointer必须分账；不得热切一个万能target | `deferred / non-blocking` |
| `D02-DR002` | embedding generation与index write的exact Process key/事务cutoff | S08/S09 | `vectorizing_indexing`只可作phase；未冻结前不得冒充exact capability | `deferred / non-blocking` |
| `D02-DR003` | IntakeSource `accepts_new_snapshots`的reopen权限与治理 | S04/S16 | 它是typed admission fence，不新增Source lifecycle或failed Snapshot | `deferred / non-blocking` |
| `D02-DR004` | Membership decision及Gate action的exact持久enum/CHECK | S04/S05 | 现有语义与状态族不变；不得从prose猜DDL spelling | `deferred / non-blocking` |
| `D02-DR005` | S06 artifact type/bundle、node/edge/anchor/block exact kind | S06 | GenerationArtifact/Schema foundation不是StateFamily；开放kind不得进入runtime contract | `closed by S06-v1.0`：`structure_document`/`retrieval_block_projection`/`structure_validation_report`；`mkb.structure_document@1` node_kind闭集；generation-local coordinates（`T-O-94..95`） |
| `D02-DR006` | clean curation、mass-scatter discard/loss、user generation retry | S05/S06/S02 | 必须复用现有六StateFamily与causal new Task/Execution；不得原位编辑RAG artifact | `closed for S06 v1`：完整HITL/用户generation精修 out-of-scope（`T-O-93/96`）；mass-scatter loss仍归Workflow requiredness；未来HITL须reopen |
| `D02-DR007` | S12-S15物理表、retention、recovery扫描与运营实现 | S12-S15 | 物理事实不得成为业务状态SSOT；恢复只依赖durable truth/fence/outbox | `partial / S12+S13-v1.0`：关系主库+对象local CAS/ref/GC/readiness已冻；S14-S15数值/runbook与R2仍defer |

D02-v1.0不存在未关闭的D02宪法冲突。上表是明确的下游责任移交，不是待D02继续提问的owner-gate。

### 2.3 Reopen触发器

仅以下情况reopen D02：

- 提议第七个StateFamily，或修改六族任一owner；
- 修改exact状态集合、合法边或state-vs-fact分类；
- 修改跨域控制方向、proof归约、terminal不可复活等共有不变量；
- 下游冻结结果无法满足当前镜像块，且不是单纯citation drift；
- 发现两个已冻结下游Truth无法同时实现。

具体业务schema、算法、性能参数、内部字段或实现选择本身不触发D02 reopen。

---

## 3. Domain Cutoff & Downstream Handoff（规范）

### 3.1 路由责任

D02不冻结某一业务域的next-step算法。相关下游Truth层决定其Workflow、Process capability、typed route input和acceptance guard；冻结后按`T-O-91/T-O-92`回填本ledger。Process、queue、API、projection与Appendix均不得成为隐式router。

### 3.2 S06门处理

D02此前对S06 Q4-Q6设置的前置门已随D02-v1.0解除；**S06-v1.0** 已冻结并回填本ledger：

- GenerationArtifact / Invocation / per-type current pointer 仍为正交 typed facts，非 StateFamily；
- 自动生产路径 + Command/input digest freeze（`T-O-93`）；
- structure_document 树 + anchors + generation-local coordinates + 分账 projection（`T-O-94`）；
- 首版 concrete schema 随 Spec bootstrap（`T-O-95`）；
- 唯一 accepted + 仅自动 retry；用户 generation 精修 defer（`T-O-96`）；
- 完整 HITL 不在 S06 v1；不得新增 reviewing 类 StateFamily。

### 3.3 后续共同校准流程

```text
downstream issue discovered
  → classify: domain detail | D02-triggering semantic change
  → domain detail: downstream decides and records
  → D02-triggering: register drift and reopen affected Truth
  → freeze downstream source Truth
  → update six-field D02 mirror block in same calibration unit
  → run exact-state/edge/alias/version search
```

不再为纯技术实现或文档组织自动生成owner QNA。只有无法由既有Truth唯一推导、且会改变产品范围、外部可见语义、重大成本/风险或不可逆数据行为的分歧，才升级owner-gate。

---

## 4. Non-normative Investigation Appendix

> 本节保留D02-v0.1-v0.3调查中有复核价值的矩阵摘要。它只用于理解、设计输入和发现冲突，不是exact enum、route、API、DDL或验收Truth。

### A.1 调查成熟度标签

| 标签 | 历史含义 | v1使用方式 |
|---|---|---|
| `FROZEN` | 已有owner/domain Truth | 应映射到§0-§1规范正文 |
| `DERIVED` | 由冻结Truth唯一推导 | 可作为解释，但不得扩张源Truth |
| `PROPOSED` | 调查建议 | 必须交还owner domain，不进入实现contract |
| `OPEN` | exact名称/组合/责任未冻结 | fail-closed，不从prose猜测 |
| `CONFLICT` | 两份候选解释不能同时实现 | 按§2登记和校准 |

### A.2 三层runtime兼容摘要

| Task | Root Execution | Process集合 | 调查解释 |
|---|---|---|---|
| queued | created/ready | 无或ready | root建立或等待首次claim |
| running | ready/running/waiting | active/terminal混合 | 正常执行、join或human wait |
| cancelling | cancelling | cancelling/terminal | forward-stop收敛 |
| succeeded | succeeded | required terminal+proof-valid | 合法终态 |
| failed | failed | required terminal mixed | 自动恢复耗尽后的合法终态 |
| cancelled | cancelled | descendants fenced/terminal | 已发布资产不隐式回滚 |
| terminal | active current root/Process | 任意 | invariant violation |

### A.3 Intake admission摘要

```text
Source descriptor
  → AcquisitionEvidence
  → typed clean Artifact/Candidate pages
  → PreflightOutcome
  → CandidateSet sealed
  → S04 canonical acceptance
  → optional ExecutionGate or downstream production
```

- `complete + authoritative`才可能产生absence decision；partial只接受可信seen facts；
- preflight `passed/blocked`是业务Outcome，runtime/schema/evidence error走Process retry/failure；
- allowlisted+passed自动继续且不建Gate；需要人工动作时才创建Gate并让Execution waiting；
- CandidateSet accepted不自动等于Revision serving或index publication成功。

### A.4 canonical场景摘要

| 场景 | 合法表达 | 禁止捷径 |
|---|---|---|
| no-change ingest | Snapshot/Membership decision + route no-op或显式rebuild | 创建`unchanged`状态 |
| human admission | Gate open + Execution waiting(human_review) | Task/Item `reviewing` |
| automatic retry | 同一Process running→retry_wait→ready | 新Attempt或Task `retrying` |
| full Task retry | 同Task新generation/root，failed/cancelled→queued | 复活旧Execution tree |
| succeeded content rebuild | 新Task + 新Execution tree | succeeded→running back-edge |
| deactivate/delete | S04 lifecycle CAS + cleanup intent/proof | cancel Task等于资产删除 |
| reindex | 同IntakeRevision上的新index generation | 新建IntakeRevision或`vector_ready`状态 |

### A.5 kind/capability调查边界

- RequestIntent、Workflow purpose、Execution phase、Process capability、Artifact type、node kind、route kind是不同分类轴；
- source kind固定为`inline_payload/local_object/http_resource/registered_api`时，single/scatter、browser/PDF/OCR/Vision仍是正交capability/cardinality；
- S05已冻结exact clean/acquisition/preflight capability；S06-S09 exact kind继续由各自Spec冻结；
- `vectorizing_indexing`可暂作Execution focus phase，不得据此推导S08/S09必须共享一个Process；
- S06 node kind只描述artifact内部schema，不得决定runtime next step。

### A.6 Legacy证据边界

`legacy-family/`只证明生产行为、失败模式、LS-RAG结构消费和历史补丁成本。MKB是独立greenfield应用，不继承legacy API、wire、schema、UUID、status、storage、queue或部署拓扑。Legacy evidence可支持下游选择默认方案，但不能覆盖owner-frozen Truth或自动制造兼容义务。

---

## 5. Acceptance & Freeze Record（规范）

### 5.1 冻结验收

| 检查项 | 结果 |
|---|---|
| D02 QNA Q1-Q6完成，Truth ID连续 | `passed / T-O-86..92` |
| 六个且仅六个StateFamily有唯一owner、exact状态与合法边镜像 | `passed` |
| phase/reason/Outcome/readiness/pointer/proof与status分账 | `passed` |
| D01/S01-S05权威版本与镜像一致 | `passed` |
| D02不承担下游route、kind、API或DDL | `passed` |
| 下游剩余项均有owner、fail-closed行为和reopen条件 | `passed` |
| 镜像更新单元与citation/semantic drift协议冻结 | `passed / T-O-91..92` |
| S06 D02前置门可解除且未偷冻S06业务答案 | `passed` |
| 长篇调查内容明确降为non-normative | `passed` |

### 5.2 Freeze verdict

`D02-v1.0`正式冻结。它是后续状态命名、所有权、合法边、state-vs-fact分类和跨域校准的共有域入口；除§2.3触发器外不得隐式reopen。

本冻结不表示：

- S06-S16已经accepted或frozen；
- System Topology、Acceptance Matrix或全baseline Truth Freeze已经完成；
- 下游开放exact kind、route、DDL或实现参数已被D02决定。

### 5.3 下游验收义务

每份后续Spec至少验证：

1. 没有引入第七StateFamily或stage-specific status；
2. 没有跨owner写状态或从projection/log/payload猜Truth；
3. Process Outcome、artifact/proof与状态推进之间存在owner guard；
4. terminal/back-edge、cancel、retry、rebuild和cleanup符合本宪法；
5. 命中D02的冻结变化已在同一校准工作单元回填镜像块。

---

## 6. Reference & Revision History（规范）

### 6.1 权威引用

| 文档 | 用途 |
|---|---|
| `qna-truth/D02.md v1.0` | `T-O-86..92`的owner裁决来源与campaign closure |
| `domain-truth/D01-task-execution-process-flow.md v1.4` | Task/Execution/Process身份、控制方向和runtime cutoff |
| `domain-truth/S02-task-api.md v1.3` | Task aggregate exact状态、readiness、TaskItem、retry/rebuild |
| `domain-truth/S03-workflow-engine.md v1.3` | Execution/Process exact状态、phase/reason、claim/retry/recovery |
| `domain-truth/S04-intake-asset-lifecycle.md v1.2` | IntakeItem lifecycle、CandidateSet acceptance、pointers/cleanup |
| `domain-truth/S05-intake-cleaning.md v1.1` | Candidate producer、PreflightOutcome与ExecutionGate |
| `qna-truth/S06.md v0.9` | S06 Q1–Q6 / `T-O-77..85`、`T-O-93..96` |
| `domain-truth/S06-lsrag-structurizer.md v1.0` | S06 正式 Spec：generation 账本、structure contract、自动路径 |
| `domain-truth/S12-turso-persistence.md v1.0` | S12 正式 Spec：单主库、TX/outbox/claim、CW+vector |
| `spec-glossary.md` | canonical状态与正交事实词汇 |
| `spec-index.md` | baseline编排、状态与freeze checklist |

### 6.2 修订历史

| 版本 | 日期 | 作者 | 状态 | 主要变更 |
|---|---|---|---|---|
| `D02-v0.1` | `2026-07-18` | `MKB owner + Codex` | `investigation draft` | 首次汇总Intake、Task/Execution/Process、clean/RAG/vectorize/publication的状态族、路由与kind冲突。 |
| `D02-v0.2` | `2026-07-18` | `MKB owner + Codex` | `calibration applied / not frozen` | 完成D01-v1.4、S01-v1.5、S02-v1.3、S03-v1.3、S04-v1.2、S05-v1.1及S06-v0.6状态边界回填。 |
| `D02-v0.3` | `2026-07-19` | `MKB owner + Codex` | `Round 1 Truth frozen / Round 2 gate` | 冻结`T-O-86..89`：共有域宪法、六StateFamily、下游执行cutoff与Truth镜像义务。 |
| `D02-v1.0` | `2026-08-10` | `MKB owner + Codex` | `frozen` | Owner要求直接收口；冻结`T-O-90..92`，采用四层结构、六项镜像块与双向漂移协议；将剩余问题移交下游、waive Round 3并关闭D02 campaign。 |
| `D02-v1.0-cal` | `2026-08-11` | `MKB owner + Codex` | `frozen / S06-calibrated` | 回填S06-v1.0：关闭DR005/DR006中S06可决部分；§3.2记录generation/pointer/structure contract；不改变六StateFamily。 |
| `D02-v1.0-cal-s12` | `2026-08-11` | `MKB owner + Codex` | `frozen / S12-calibrated` | 回填S12-v1.0：物理机制服务六StateFamily；vector/outbox非SSOT；DR007部分关闭。 |
| `D02-v1.0-cal-s13` | `2026-08-11` | `MKB owner + Codex` | `frozen / S13-calibrated` | 接收S13-v1.0：physical convergence 对象侧合同；DR007 部分关闭。 |
