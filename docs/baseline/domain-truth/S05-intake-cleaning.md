
# S05 — Intake & Cleaning

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 子系统**：`D3 摄入资产 / S05 Intake & Cleaning`
>
> **日期**：`2026-07-18`
>
> **作者 / 裁决者**：`MKB owner + Codex`
>
> **文档性质**：`domain truth / formal subsystem specification`
>
> **文档状态**：`accepted / D02-state-calibrated`（S05 域内已接受；全系统 truth layer 尚未 frozen）
>
> **Truth 版本**：`S05-v1.1`
>
> **上游权威输入**：形成QNA时的`D01-v1.2/S01-v1.3/S02-v1.1/S03-v1.1/S04-v1.0`、冻结的`qna-truth/S05.md v1.0`（Q1–Q10 / `T-O-49..76`）；发布后对齐版本为`D01-v1.4/S01-v1.5/S02-v1.3/S03-v1.3/S04-v1.2`
>
> **词汇权威**：`docs/baseline/spec-glossary.md`
>
> **事实证据**：`legacy-family/` 仅作为 production-pitfall / behavior-archeology / design-counterexample `ReferenceAnchor`，另有 RFC、Unicode、W3C PROV、Airbyte、Great Expectations、Kubernetes、LangGraph、Argo 与 Temporal 一手资料
>
> **下游消费者**：`S06-S09`、`S11-S16`、跨系统拓扑 `17`、验收冻结 `18`

> **Owner-originated 约束**：MKB v1 必须覆盖 legacy-family 已生产验证的 inline/local、网页静态与浏览器获取、PDF、registered API single/scatter/pagination、OCR 与 Vision/model-assisted clean 能力；但不得复制 legacy 的 file 身份、SMCP wire、Cloudflare/R2/D1 依赖、branch-name 路由、silent skip 或 callback 成功语义。

> **准入约束**：allowlist 只授予“mandatory preflight 通过后可以自动进入 RAG”的资格。PreflightValidator 是只读 frozen evidence 的确定性检查器，不重新 fetch/clean，不拥有状态推进权。只有确实需要人工输入的路径才创建 Execution-owned durable gate。

> **跨文档审计声明**：S05已与D01-v1.4/S01-v1.5/S02-v1.3/S03-v1.3/S04-v1.2完成双向状态校准。本文不增加第四层运行身份、不复制S03状态机、不把human review写回Intake truth，也不提前冻结S12物理表数量；Task polling、human waiting、CandidateSet acceptance与same-Execution resume均已有唯一权威归属。

> **D02状态校准声明**：D02-v1.0已镜像CandidateSet与ExecutionGate状态、相关正交Outcome及`T-O-86..92`校准纪律；本版不改变四类source、capability surface、mandatory preflight、allowlist或ExecutionGate语义。Acquisition result、CandidateSet staging、PreflightOutcome、ExecutionGate和Execution status继续分账；S05 exact capability key是S03 manifest identity，早期coarse process family不构成alias。clean curation与mass-scatter discard/loss归S05/S06/S02，gate action exact enum归S05/S12；它们是下游设计而非D02 owner-gate，不进入S05-v1.1。

> **S06校准声明**：`S06-v1.0`消费 exact admitted clean Artifact + Revision，不重新 fetch/clean，不写 Intake lifecycle。v1 完整 clean curation / inspection 编辑闭环 **不因 S06 扩展为生产主路径**（`T-O-93`）；S05 既有 Gate 最小面可保留。S06 ProcessCommand materialize 后 selected clean 冻结；S05 不得在 S06 retry 中热切 binding。S06 success 不替代 S04 serving。

> **S12校准声明**：`S12-v1.0` 兑现 Gate decision 原子事务（TX-08）、outbox resume、binding 持久化；不新增 S05 状态机。

---

> **S13校准声明**：`S13-v1.0` 冻结 v1 本地 `object_root` + `ObjectStorePort`、`mkbobj:v1` handle、team-scoped CAS、bytes-first、同库 catalog/ref/purpose、verify-on-read、周期 GC 与 identity readiness。本文件业务语义不变；对象 I/O 必须经 S13 Port，禁止 path/R2 key 进入契约。

## 1. Domain 介绍

### 1.1 Domain 价值

S05 是 MKB 将外部输入转化为“可验证、可接受、可审计的 Intake 候选”的执行域。它统一管理 source definition、获取、解码、source-specific mapping、确定性 canonicalization、内容清洗、single/scatter 集合封口、mandatory preflight 以及 clean 后、RAG 前的人机准入。

S05 解决九个核心问题：

1. source kind、获取策略与 clean 策略正交注册，避免组合字符串爆炸；
2. inline、local、HTTP 与 registered API 使用严格 typed descriptor，不让 file/path/URL 冒充通用身份；
3. declared、detected、verified media 与 encoding evidence 分账，不盲信扩展名或响应头；
4. raw representation、source-grounded semantics 与 clean-derived output 分账，避免模型输出制造业务 Revision；
5. single/scatter 共用 typed CandidateSet page/seal，坏 member、空集合与分页完整性不再静默；
6. ExternalKey、canonical value、member/page/root digest 均由 exact versioned definition 决定；
7. allowlist 仍必须经过 code-owned PreflightValidator，自动放行不会伪造 human gate；
8. 人工审核是 Execution durable waiting state，绑定 exact Intake、Artifact、Outcome、generation 与 fence；
9. retry/recovery/resume 锁定 exact S05 binding，不能热切 active implementation。

### 1.2 在整体拓扑中的位置

```text
S01/S02 Task Contract
  │ request intent + exact Intake target
  ▼
S03 WorkflowRevision / ProcessCommand
  │ exact Execution/Process fence + capability binding
  ▼
S05 Intake & Cleaning
  ├── SourceKindDefinition + typed descriptor
  ├── acquire / decode / map / canonicalize / clean
  ├── AcquisitionEvidence + CandidateMember + CleanArtifactCandidate
  ├── CandidateSet pages / seal
  ├── mandatory PreflightValidator + Outcome
  └── typed candidate/preflight refs
          │
          ▼
S04 CandidateSet acceptance
  │ Snapshot + Membership + Item/Revision + IntakeChangeSet
  ▼
S03 typed admission route
  ├── passed+allowlisted → S06-S09
  └── human required → S05 ExecutionGate / ReviewTarget / Decision
                         └── same Execution resumes → S06-S09
```

S05 的 handler 成功、HTTP 2xx、对象落盘、queue ACK、Process succeeded、CandidateSet sealed 或人工点击都不是 accepted Intake truth。只有 S04 acceptance transaction 可以创建 `IntakeSnapshot`、`IntakeItem`、`IntakeRevision` 与 `IntakeSnapshotMembership`。

### 1.3 Source、capability 与 runtime 三轴

```text
IntakeSourceKindDefinition
  └── descriptor/config schema + identity/cardinality/completeness rules

Acquisition/Clean Capability
  └── ProcessCapabilityManifest + handler + typed input/output/proof

Execution binding
  └── exact source/acquisition/clean/preflight refs + s05_binding_digest
```

三轴不可互相代替：

- `http_resource` 是 source kind；static HTTP、browser、PDF download 是 acquisition capabilities；
- `registered_api` 是 source kind；single/scatter/pagination 是 cardinality/completeness capabilities；
- OCR、Vision/model-assisted extraction 是 clean capabilities，不是 source kind；
- Workflow 决定本次 Process route；S05 definition 不读取 compiled Workflow 后自行编排。

### 1.4 工作平面

| 平面 | S05 责任 | Durable evidence / state | Cutoff |
|---|---|---|---|
| Source definition | source kind、strict descriptor/config、normalizer、capability eligibility | immutable versioned registry definition | 不创建 Intake identity |
| Acquisition / I/O | inline/object/HTTP/API 读取、redirect/page/stream budget | S03 Process state + AcquisitionEvidence | storage backend/secret lifecycle归S13/S16 |
| Decode / canonical | media/encoding/envelope validation、canonical value/digest | typed validation evidence + version refs | 不接受 Snapshot/Revision |
| Observation integrity | member、scope、completeness、rejection、page/root seal | CandidateSet staging state | accepted collection归S04 |
| Clean / provenance | parser/browser/PDF/OCR/Vision输出、loss/quality/lineage | CleanArtifactCandidate + ProcessOutcome | structure/embed/publish归S06-S09 |
| Preflight | 对 frozen evidence 执行 exact check-set | PreflightOutcome + check evidence | 不重新获取/清洗，不选择 Workflow route |
| Human review | clean 后、RAG 前 durable waiting 与 exact decision | ExecutionGate/ReviewTarget/Decision | 不写 Intake lifecycle，不占用 Process lease |

### 1.5 Scope fence

S05 负责：

- 四类 v1 source kind 与 typed input contract；
- acquisition/decode/clean capability的引用、约束和输出 contract；
- ExternalKey normalizer、media/encoding、stream/size/page/redirect budget；
- AcquisitionEvidence、IntakeCandidateMember、CleanArtifactCandidate 与 paged IntakeCandidateSet；
- raw/source-semantic/clean-derived 分账与 versioned canonical digest；
- mandatory preflight、allowlist exact binding 与 minimal PreflightValidator registry；
- Execution-owned human gate、composite ReviewTarget、decision transaction 与 same-Execution resume；
- exact S05 binding、不热切规则、最小 crash recovery 与 acceptance evidence。

S05 不负责：

| 排除项 | 权威归属 | S05 边界 |
|---|---|---|
| Task API、六态、cancel、full retry、causal restart | `S01-S02` | 新实现升级只能请求 S02 restart/new Execution generation |
| Workflow graph、Process 状态、claim/retry/recovery engine | `S03` | 使用 ProcessCommand/Outcome、waiting 与统一 repair |
| Intake identity、Snapshot/Revision acceptance、serving/lifecycle | `S04` | 只提交候选、Outcome、gate refs |
| Block/Construction/Embedding/Index | `S06-S09` | 输出 exact Revision/Artifact lineage 需求 |
| model/prompt registry 与推理 provider | `S11/S14` | clean binding只引用 exact logical refs |
| exact Turso DDL、事务、queue/outbox driver | `S12` | 冻结逻辑职责和原子性，不冻结表数 |
| bytes backend、logical locator、atomic write、GC | `S13` | 只持有handle/digest/size与引用保护要求 |
| metric/alert/runbook、等待SLA/timeout policy | `S15` | 输出typed evidence/event，不建设运营平台 |
| secret、egress、review authority、allowlist管理权限 | `S16` | 只保存logical policy/secret/actor refs |
| 动态脚本/agent rule/plugin、shadow/canary/global readiness | future reopen | v1仅code-owned registry、CI与bootstrap静态校验 |

### 1.6 Domain 完成定义

实现层必须同时满足：

1. §2 全部 Truth ID 可映射到 contract、schema、service 和 test；
2. 四类 source descriptor、四类 typed output 与 exact digest/canonicalization golden tests 通过；
3. single/scatter、partial/complete、page/seal、rejection/gap 与合法空集测试通过；
4. allowlist 无 validator、validator blocked、validator runtime failure 和 passed 自动路由全部 fail-safe；
5. human gate 只在等待人工时创建，并通过 stale/fence/CAS/outbox 故障注入；
6. retry/recovery/resume 不热切 binding，同 version 异 digest fail-loud；
7. 空库 bootstrap、registry/handler/allowlist static consistency 与 acceptance fixtures 通过；
8. dependency/config/DDL/API/event/startup 扫描证明零 legacy runtime dependency；
9. §6 强制验收矩阵全部通过。

---

## 2. 真相层

### 2.1 真相层纪律

本节是 S05 的 SSOT。来源分为：

- `OWNER-QNA`：冻结的 S05 Q1–Q10 / `T-O-49..76`；
- `UPSTREAM`：D01/S01-S04 已接受的 runtime、Workflow 和 Intake truth；
- `REFERENCE-ANCHOR`：legacy-family 与外部一手资料证明的行为、踩坑和设计分母；
- `ACCEPTED-VERDICT`：不改变 owner 决策、为实现提供的正式精化。

`T-O-67` 已被撤回；`T-O-66/T-O-68/T-O-69` 只保留 QNA 修订台账声明的核心。本文以 `T-O-70..76` 对 Q7–Q10 的最终收敛为准。ReferenceAnchor 无权定义 MKB runtime/schema/API/acceptance。

### 2.2 Source 与 capability 真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S05-T001` | v1必须覆盖inline/local、网页static/browser、PDF、registered API single/scatter/pagination、local OCR与Vision/model-assisted clean。 | `T-O-49` | 能力不得因legacy实现缺口被任意删减。 |
| `S05-T002` | v1 source kind只有`inline_payload/local_object/http_resource/registered_api`；browser/PDF/OCR/Vision/scatter是capability或cardinality。 | `T-O-50` | 禁止以组合branch字符串充当source taxonomy。 |
| `S05-T003` | MKB完全本地、greenfield；legacy-family只提供ReferenceAnchor。 | `T-O-51` | 无Cloudflare/R2/D1/SMCP/legacy ID或wire兼容。 |
| `S05-T004` | `IntakeSourceKindDefinition`内部注册、immutable versioned，绑定descriptor/config schemas、cardinality、completeness、capability eligibility、normalizer、budget和preflight eligibility。 | `T-O-59` | caller不得自造kind或注入handler。 |
| `S05-T005` | identity descriptor、operational config和secret refs严格分账；正文、绝对路径、credential、任意headers/fetch options不得进入identity。 | `T-O-59/T-O-61` | 所有schema默认`extra=forbid`。 |
| `S05-T006` | ExternalKey由source-specific纯函数normalizer产生，携带exact version/digest/evidence；无stable key时fail，不得随机UUID/content-hash fallback。 | `T-O-60` | Item解析仍由S04 team+source namespace执行。 |
| `S05-T007` | media分declared/detected/verified，encoding保留label/BOM/detector/error证据；stream/解压/redirect/page/time budget在消费期间执行。 | `T-O-59/T-O-61` | 禁止read-all-then-check与只信扩展名/Content-Type。 |

### 2.3 Typed output、canonicalization 与 collection 真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S05-T008` | S05只产出`AcquisitionEvidence`、`IntakeCandidateMember`、`CleanArtifactCandidate`和paged`IntakeCandidateSet`四类typed对象。 | `T-O-62` | 不返回opaque child_files或万能artifact payload。 |
| `S05-T009` | raw representation、source-grounded canonical semantics和clean-derived output必须分账。 | `T-O-62/T-O-63` | AI/OCR/model输出不能单独制造IntakeRevision。 |
| `S05-T010` | Revision basis只允许`typed_source_semantics/deterministic_canonical_text/opaque_representation`等versioned definition声明。 | `T-O-63` | definition变更不反向重解释历史Revision。 |
| `S05-T011` | v1 digest基线为显式SHA-256；JSON用JCS，text用UTF-8/LF/NFC，HTML用结构parser；digest输入包括schema/canonicalizer/normalizer/definition版本。 | `T-O-63` | 禁止NFKC默认折叠、regex strip或无版本hash。 |
| `S05-T012` | CandidateSet page与root digest按稳定排序和JCS envelope确定性计算；同fence同ordinal同digest幂等，异digest冲突。 | `T-O-64` | 未seal、缺页、计数/字节/重复/Artifact读取异常不得accept。 |
| `S05-T013` | rejected/gap evidence不可丢弃；partial可以保存可信事实，但complete要求required rejection为0和source-exhausted proof。 | `T-O-64` | partial或required anomaly仍可被root preflight阻断RAG。 |

### 2.4 Preflight 与 allowlist 真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S05-T014` | allowlist只是conditional auto-admission；所有allowlisted路径都必须执行mandatory preflight。 | `T-O-52` | API/网页曾经稳定不构成绕过验证的理由。 |
| `S05-T015` | preflight聚合source/acquisition、collection/member和clean/artifact typed evidence；任一required anomaly必须阻断相应scope。 | `T-O-52/T-O-55` | missing artifact不得由人工override伪造成功。 |
| `S05-T016` | 每条allowlist绑定exact code-owned `validator_key/version/check_set_version`；PreflightValidator只读本Execution frozen evidence。 | `T-O-65/T-O-70` | 无validator不得自动放行；validator不得network/secret/path/state mutation。 |
| `S05-T017` | Validator业务结果只有`passed|blocked`；runtime/schema/evidence错误复用S03 Process retry/failed。 | `T-O-70/T-O-71` | 错误不降格成blocked后让人工批准。 |
| `S05-T018` | `passed+allowlisted`保存Outcome后直接继续RAG且不建gate；non-allowlisted或reviewable blocked才进入human path。 | `T-O-71` | 禁止为自动路径伪造released gate/decision。 |
| `S05-T019` | S05只冻结registration/binding、validation outcome/evidence、human gate/target、decision四组durable职责；exact表数和DDL归S12。 | `T-O-72` | 已撤回九表强制，不得在实现时偷偷恢复。 |

### 2.5 Human review 真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S05-T020` | Human review是Execution-owned durable gate，发生在clean之后、RAG之前；Intake不拥有review state，Process不得持lease等待。 | `T-O-53/T-O-54` | Process先terminal，Execution投影为`waiting`。 |
| `S05-T021` | ReviewTarget必须绑定team/task/execution/generation/fence/Workflow binding、Intake refs、exact clean Artifact digest、PreflightOutcome/check-set与target digest。 | `T-O-55/T-O-58` | 裸artifact UUID或“当前最新版”不可批准。 |
| `S05-T022` | single和scatter均允许root/child gate；root required evidence未通过不推进child，真正需要判断的child各自建gate。 | `T-O-56/T-O-70` | 不新增review专用parent/child模型。 |
| `S05-T023` | Gate只有`open→released|rejected|superseded`；Decision append-only，并以authority、revision、fence和target digest校验。 | `T-O-57/T-O-75` | stale/conflict/late decision拒绝，不覆盖旧decision。 |
| `S05-T024` | Decision、gate CAS、Execution projection与outbox必须原子提交；批准后恢复同一Execution。 | `T-O-54/T-O-57/T-O-75` | 不创建新Task，不重跑已完成clean Process。 |

### 2.6 Binding、registration 与 recovery 真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S05-T025` | Execution锁定本次实际使用的source/acquisition/clean/preflight exact refs与`s05_binding_digest`。 | `T-O-73` | retry/recovery/human resume不得重新resolve active。 |
| `S05-T026` | 同key/version异manifest或implementation digest必须fail-loud；新版本只影响新Execution。 | `T-O-73` | 已有Task升级走S02 causal restart/new generation。 |
| `S05-T027` | Validator随MKB代码发布，manifest只含identity、handler、applicability、input/output schema、ordered check-set与digests。 | `T-O-74` | v1无外部CRUD、DB脚本、agent rule、plugin或dynamic loader。 |
| `S05-T028` | golden fixtures归CI/S05 acceptance；bootstrap只做handler/schema/digest/check key/allowlist binding静态一致性。 | `T-O-74` | 无runtime selfTest、shadow/canary或全局readiness状态机。 |
| `S05-T029` | v1只强制四个恢复窗口：Outcome→transition、gate→Execution projection、decision→outbox、late/stale decision。 | `T-O-76` | 复用S03/S12 repair，不建设S05 Reconciler。 |
| `S05-T030` | waiting默认durable indefinite且永不自动approve；timeout/retention/GC/metrics/alerts/runbook留S13/S15。 | `T-O-76` | open gate引用的evidence/artifact在终结前受引用保护。 |

### 2.7 Universal `payload_extra` 真相

| 规则面 | 强制约束 |
|---|---|
| Presence | 所有S05涉及的MKB-owned canonical、runtime、registry、staging、outcome、gate、decision、audit、outbox与repair物理表必须有非空默认`{}`的`payload_extra`。 |
| 禁止承载 | identity、source kind、descriptor核心字段、ExternalKey、digest、状态、fence、route、proof、authority、secret、正文、物理路径。 |
| 升格规则 | 一旦扩展字段参与identity、validation、route、approval、proof、filter或retention，必须通过正式schema/definition version升格。 |
| S12例外 | S12纯schema bookkeeping表是否需要该字段由S12明确裁决；业务表不得借此例外逃逸。 |

### 2.8 S05 状态、结果与准入事实分账

| 事实族 | Exact values | Owner | 是否推进自己的状态边 | 与S03的关系 |
|---|---|---|---:|---|
| AcquisitionEvidence result | `succeeded/rejected/failed` | S05 capability | 否，immutable outcome | retryability经Outcome交S03 |
| CandidateSet staging | `open/sealed/accepted/abandoned` | S04 staging contract；S05只append/seal/abandon | 是 | producing Process仍使用S03八态 |
| PreflightOutcome | `passed/blocked` | S05 validator | 否，immutable business outcome | Engine消费后选auto/human/failure route |
| ExecutionGate | `open/released/rejected/superseded` | S05 control truth | 是，CAS+Decision | Execution只投影`waiting(human_review)`或恢复/终结 |
| Execution status | S03八态 | S03 | 是 | S05不得直接自造状态边 |
| Task action_required | bounded projection | S02 | 否 | open Gate时Task保持running |

runtime/schema/evidence错误只形成Process failure/retry evidence，不生成`blocked`；Gate `released`也不等于Process、Execution、Task或Intake成功。

---

## 3. Contract schema 与数据不变量

### 3.1 Schema 总则

1. 本节冻结 logical records、正式字段和不变量，不冻结 Turso exact SQL type、index、trigger或物理表数量；
2. UUID、timestamp、digest、enum、version、logical ref均使用严格类型；输入模型默认`extra=forbid`；
3. 所有跨记录引用强制team fence、Execution generation与fencing token；
4. 所有definition/manifest immutable versioned；同key/version同digest幂等、异digest失败；
5. 所有正文/bytes通过S13 logical handle传递，禁止塞入row、queue、log或`payload_extra`；
6. secret只保存S16 logical ref，compiled view和audit不得泄漏解密值；
7. staged对象不是canonical Intake truth，S04 acceptance后才绑定canonical owner。

### 3.2 `IntakeSourceKindDefinition`

| 字段组 | 必须字段 / 约束 |
|---|---|
| Identity | `source_kind_key`、`definition_version`、`definition_digest`、`status` |
| Schemas | `descriptor_schema_ref/digest`、`config_schema_ref/digest`，均strict |
| Collection | `cardinality(single|collection)`、`scope_profile_ref`、`completeness_profile_ref` |
| Capability | allowed acquisition/decode/clean capability key/version ranges |
| Media/budget | declared/detected/verified media rules、encoding profile、stream/decompressed bytes、redirect/page/time budgets |
| Identity resolver | `external_key_normalizer_ref/version`、singleton key、duplicate policy |
| Security | secret slot specs、egress/auth policy refs；不保存secret |
| Admission | preflight profile、allowlist eligibility、required evidence classes |
| Extension | `payload_extra`，不得影响上述语义 |

### 3.3 四类 source descriptor

#### 3.3.1 `inline_payload`

必填：staged logical representation ref、declared media/encoding、correlation ref、digest、size。调用方正文必须先通过 S13 staging port 获得handle；不得把body写入 IntakeSource row、Task payload、queue或`payload_extra`。

#### 3.3.2 `local_object`

必填：logical object ref、declared media；可选 filename hint、expected digest/size。绝对路径禁止进入contract；路径和文件名均不构成identity。

#### 3.3.3 `http_resource`

必填：canonical URI、method/profile ref、expected media、redirect/cache/validator policy refs。canonicalization至少规范scheme/host/default port、移除fragment、拒绝userinfo；query与trailing slash规则由source definition版本化。禁止caller提供任意headers/cookies/fetch options；auth只能引用registered secret slot。

#### 3.3.4 `registered_api`

必填：provider/operation exact versions、typed query scope ref+digest、pagination/completeness profile、secret refs、request/envelope/member schemas。caller不得提交任意URL、代码或raw parameters；single/scatter由definition的cardinality和scope contract决定。

### 3.4 `AcquisitionEvidence`

| 字段组 | 必须字段 |
|---|---|
| Runtime fence | team、task、Execution/generation/fence、Process/attempt |
| Definition binding | source kind/version/digest、acquisition capability/version/digest |
| Request evidence | sanitized request profile digest、started/completed time、attempt ordinal |
| Representation | logical handle、raw byte digest/algorithm、size、declared/detected/verified media |
| Encoding | label/BOM/detector/profile、decoder error/replacement count |
| HTTP/API | status、final URI evidence、redirect chain digest、validator refs、page/cursor evidence |
| Budget | bytes/decompressed bytes/time/redirect/page usage与limit verdict |
| Result | `succeeded|rejected|failed` typed code；failed不得伪装empty success |
| Extension | `payload_extra` |

### 3.5 `IntakeCandidateMember`

必填：

- stable ordinal；
- raw external-key evidence；
- normalized external key、normalizer key/version/digest；
- `required` flag；
- source member raw/canonical digests；
- versioned semantic tuples；
- staged Artifact descriptors；
- clean candidate ref；
- validation/rejection evidence refs；
- `payload_extra`。

同一 CandidateSet 内 normalized key必须唯一。duplicate按exact source definition fail或显式归并；不得依赖并发完成顺序决定ordinal。

### 3.6 `CleanArtifactCandidate`

| 字段组 | 必须字段 |
|---|---|
| Target | candidate/member ref、input artifact/evidence digest |
| Output | logical handle、format/media、digest/algorithm、size |
| Capability | clean capability/profile、parser/model/prompt exact logical refs |
| Producer | Execution/Process/attempt/fence |
| Quality | language/page/segment stats、anchors、loss flags、quality signals/verdict |
| Lineage | raw input→clean activity→clean output derivation refs |
| Time/extension | `created_at`、`payload_extra` |

OCR/Vision/model输出必须保留producer和quality/loss evidence；其变化默认属于derived rebuild，不等同于source semantic change。

### 3.7 Paged `IntakeCandidateSet`

#### Head

必须包含 team/source、Execution/fence、source/capability/binding digests、observation identity/fingerprint、scope/authoritative scope、completeness、expected/observed/accepted/rejected/duplicate counts、expected pages/members/bytes、root digest、PreflightOutcome ref、expiry与`payload_extra`。

#### Page

必须包含 candidate UUID、page ordinal、member range、ordered member digests、page digest、Execution fence与`payload_extra`。

```text
page_digest =
  SHA256(JCS(page immutable envelope + ordered member digests))

root_digest =
  SHA256(JCS(head immutable acceptance fields + ordered page digests))
```

#### Seal

seal必须验证：

- page ordinal连续、无缺页/重复页；
- member ordinal稳定、normalized key无冲突；
- count/bytes与head一致且未超budget；
- required Artifact handle/digest可读；
- rejection/gap manifest immutable且可复验；
- `complete`具有source-specific exhaustion proof；
- preflight Outcome绑定相同root/binding/fence。

`open→sealed→accepted`与`open→abandoned`由S04 staging contract管理；sealed可幂等重放acceptance，accepted/abandoned均不回到open。S05只能append/seal/abandon，不能写accepted。

### 3.8 Minimal Preflight records

以下是逻辑职责，不是固定物理表清单。

#### `PreflightAllowlistBinding`

```text
binding_key/version/digest
selector schema + exact selector value digest
source/acquisition/clean applicability
validator_key/version/implementation_digest
check_set_key/version/digest
override policy ref
activation state + audit refs
payload_extra
```

#### `PreflightValidatorManifest`

```text
validator_key/version
handler_key
applicability schema/ref
input_schema_ref/digest
output_schema_ref/digest
ordered check keys + check_set_digest
implementation_digest
manifest_digest
payload_extra
```

#### `PreflightOutcome`

```text
outcome_uuid
team/task/execution/generation/fence
candidate_root_digest + s05_binding_digest
allowlist binding ref (nullable for non-allowlisted)
validator/check-set exact refs
result = passed | blocked
ordered check evidence refs
outcome_digest
created_at
payload_extra
```

Validator runtime/schema/evidence错误是Process failure/retry evidence，不生成伪造的`blocked` Outcome。

### 3.9 Human gate、target 与 decision

#### `ExecutionGate`

```text
gate_uuid
team/task/execution/generation
gate_kind
status = open | released | rejected | superseded
gate_revision
expected_execution_revision/fence
review_target_uuid/digest
opened_at/terminal_at
causation/audit refs
payload_extra
```

#### `ExecutionReviewTarget`

必须冻结 team、task、Execution/generation/fence、WorkflowRevision/binding、gate kind、IntakeSource/CandidateSet及acceptance后Snapshot/Item/Revision refs、exact CleanArtifact digest、PreflightOutcome/check-set、允许的decision actions与target digest。

#### `ExecutionGateDecision`

```text
decision_uuid + idempotency_key
gate_uuid + expected_gate_revision
decision action
actor/principal/authority refs
review_target_digest
reason/evidence refs
causation/correlation
created_at
payload_extra
```

Decision append-only。提交必须同事务完成authority/target/fence校验、insert decision、CAS gate、CAS Execution projection与outbox append。

### 3.10 Execution S05 binding

Execution最少锁定：

- source kind definition key/version/digest；
- acquisition/decode capability key/version/digest；
- clean capability/profile key/version/digest；
- ExternalKey normalizer/canonicalizer refs；
- Preflight allowlist/validator/check-set refs（若适用）；
- model/prompt logical refs（若clean capability使用）；
- 聚合`s05_binding_digest`。

automatic retry、crash recovery与human resume只读取该binding。新active version不影响已有Execution；同version异digest立即隔离并fail-loud。

### 3.11 Bootstrap minimum

启动静态校验仅包括：

1. source kind/capability/validator manifest key/version/digest唯一；
2. handler存在且与manifest input/output schema一致；
3. normalizer/canonicalizer/check keys可解析；
4. allowlist只引用已存在的exact validator/check-set；
5. 同version同digest no-op，同version异digest fail readiness；
6. golden fixtures在CI/acceptance完成，不在production bootstrap执行外部I/O。

### 3.12 V1 capability registry minimum

以下是v1必须注册并实现的最小capability surface。Key表达单一执行职责；Workflow组合这些key，禁止重新拼成`htmlCrawl-geminiClean`一类branch name。每个key均通过S03 `ProcessCapabilityManifest`锁定contract version、strict ports、proof、side-effect与retry policy。

| Capability key | Process family | 输入 → 输出 | 必须覆盖 |
|---|---|---|---|
| `intake.acquire.inline` | acquisition | inline staged descriptor → AcquisitionEvidence | text/HTML/JSON logical handle |
| `intake.acquire.local_object` | acquisition | local logical object descriptor → AcquisitionEvidence | stream read、digest/media/encoding/budget |
| `intake.acquire.http_static` | acquisition | HTTP descriptor + policy/secret refs → AcquisitionEvidence | conditional request、redirect、size/time budget |
| `intake.acquire.http_browser` | acquisition | HTTP descriptor + browser profile → rendered AcquisitionEvidence | deterministic browser profile、rendered representation lineage |
| `intake.acquire.registered_api` | acquisition | provider/operation/query scope → page/envelope evidence | 多provider/channel、single/scatter、cursor/link pagination |
| `intake.decode.text_json_html` | decode/canonicalize | representation evidence → canonical source values | UTF-8/LF/NFC、strict JSON+JCS、structure HTML |
| `intake.decode.pdf` | decode | PDF representation → page/text/image evidence | page count、text layer、embedded image refs、loss evidence |
| `clean.extract.deterministic` | clean | decoded HTML/text/PDF evidence → CleanArtifactCandidate | structural extraction、boilerplate/loss/anchor report |
| `clean.ocr.local` | clean | image/scanned-page evidence → CleanArtifactCandidate | 本机OCR、page/anchor/confidence/quality evidence |
| `clean.extract.vision` | clean | image/page evidence + exact model/prompt refs → CleanArtifactCandidate | Vision/model-assisted extraction与producer lineage |
| `clean.map.registered_api` | map/clean | typed API envelope/member → CandidateMember/CleanArtifactCandidate | provider schema、ExternalKey、semantic tuples、rejection evidence |
| `intake.collection.seal` | collection integrity | ordered members/pages → CandidateSetSeal | stable order、counts/bytes、page/root digest、exhaustion proof |
| `intake.preflight_validate` | admission evidence | frozen acquisition/collection/clean refs → PreflightOutcome | exact validator/check-set，`passed|blocked` |

同一Workflow可以按source/profile选择其中子集，但四类source和Owner冻结的网页/PDF/API/OCR/Vision能力必须至少各有一条可执行、可验收路径。Capability缺失或manifest/handler/digest不一致时对应binding fail-closed，不做运行时fallback。

---

## 4. 业务流转与接口 Contract

### 4.1 Single intake

```text
Task accepted
  → Execution锁定WorkflowRevision + s05_binding
  → resolve SourceKindDefinition
  → acquire representation
  → verify media/encoding/budgets
  → normalize ExternalKey
  → canonicalize source semantics
  → clean and write staged Artifact
  → build one CandidateMember + CandidateSet
  → run mandatory PreflightValidator
  → seal CandidateSet
  → S04 acceptance transaction
  → admission route
       allowlisted + passed → continue RAG
       non-allowlisted + passed → open human gate
       reviewable blocked → open human gate
       non-reviewable blocked / failure → fail or remediate
```

合法空single必须由source contract明确；获取失败、decode失败或missing Artifact不能变成空complete candidate。

### 4.2 Scatter intake

```text
root Execution
  → acquire/paginate collection under exact scope
  → validate envelope + exhaustion
  → normalize/dedupe/stably order members
  → write CandidateSetPage(s)
  → aggregate required/rejected/gap evidence
  → root preflight + seal
  → S04 atomic acceptance
       Snapshot + Membership + Item/Revision decisions + ChangeSet/outbox
  → S03 schedules required child Executions
       child clean/preflight
       only review-needed child opens gate
  → root aggregate follows S02/S03 policy
```

root required evidence未通过时不得先推进children。S05不创建child Task，也不建立review专用parent/child表。

### 4.3 Preflight execution

PreflightValidator通过typed read-only port读取 frozen context：

```text
validate(
  execution_binding,
  acquisition_evidence_refs,
  candidate_root/page/member refs,
  clean_artifact refs,
  expected check_set
) -> passed | blocked + ordered check evidence
```

禁止：

- live HTTP/API/browser fetch；
- 重新decode、canonicalize或clean；
- secret/path/network访问；
- 写 Intake、Execution、gate、outbox；
- catch runtime error并返回passed；
- 缺validator时fallback成功。

### 4.4 Admission matrix

| Allowlist | Validator / evidence结果 | Artifact可审核 | 下一步 |
|---|---|---|---|
| 是 | `passed` | 任意 | 持久化Outcome，直接继续RAG；无gate |
| 是 | `blocked` | 是且policy允许 | 创建human gate，Execution→waiting |
| 是 | `blocked` | 否 | fail/remediate；人工不得伪造Artifact |
| 否 | `passed` | 是 | 创建human gate，Execution→waiting |
| 否 | `blocked` | 是且policy允许 | 创建human gate或按Workflow失败 |
| 任意 | validator runtime/schema/evidence error | 任意 | S03 Process retry/failed；不是human decision |

### 4.5 Human decision

```text
Process terminal
  → create ReviewTarget + open Gate
  → CAS Execution to waiting + outbox
  → authorized human reads exact frozen target
  → submit decision with expected gate revision + target digest
  → transaction:
       validate authority/team/fence/digests
       append decision
       CAS gate terminal
       CAS Execution projection
       append outbox
  → resume same Execution or terminate per decision
```

`approve_override`只能在binding policy明确允许且Artifact/evidence完整时使用；`request_reclean`必须走S03 route或S02 causal restart语义，不能原位改写旧Artifact/Outcome。

### 4.6 Version upgrade 与 restart

- 新registry version只供新Execution解析；
- retry、repair、human resume继续使用原`s05_binding_digest`；
- Owner要求已有Task使用新validator/clean implementation时，通过S02 `task_restarts`创建因果链和新Execution generation；
- 新generation不得与旧generation复用gate、Outcome或target digest；
- v1不提供live migration、canary、drain、rollback platform。

### 4.7 最小 recovery matrix

| Crash window | Durable事实 | 恢复动作 | 禁止动作 |
|---|---|---|---|
| Outcome已提交，route transition未完成 | Outcome + Execution fence | S03/S12按idempotency重放transition/outbox | 重跑validator并热切版本 |
| Gate已提交，Execution waiting projection缺失 | open Gate + target + expected revision | repair CAS projection/outbox | 创建第二个同scope gate |
| Decision/gate terminal已提交，outbox缺失 | decision + terminal gate + Execution revision | 重放缺失outbox/wakeup | 重写decision或新Execution |
| late/stale decision抵达 | terminal/superseded gate或revision mismatch | typed conflict并留audit | 接受旧target或last-write-wins |

waiting可无限期持久化且永不自动approve。具体提醒、超时、retention、GC、metric、alert与runbook由S13/S15冻结。

### 4.8 Internal ports

| Port | 调用方 → 实现方 | 强制Contract |
|---|---|---|
| `SourceDefinitionResolver` | S05 Process → registry | exact kind/version/digest；team-safe config |
| `LogicalRepresentationReader/Writer` | S05 → S13 | handle/digest/size/fence；无absolute path |
| `SecretResolver` | S05 capability → S16 | declared slot + secret ref；no-log |
| `CandidateSetStagingPort` | S05 → S04 | append page/seal/abandon；idempotency/fence/root digest |
| `PreflightEvidenceReader` | Validator → S05/S04 projections | typed read-only exact refs；无live I/O |
| `ExecutionGatePort` | S03 route → S05/S12 records | create/read/decide exact target；CAS/outbox |
| `WorkflowRuntimePort` | S05 outcome/gate → S03 | typed facts only；不自行选route |

### 4.9 Typed errors

| Code family | 典型条件 | Retry / route |
|---|---|---|
| `SOURCE_DEFINITION_*` | unknown/version drift/schema mismatch | fail-loud；不fallback |
| `ACQUISITION_TRANSIENT_*` | timeout/5xx/rate limit | S03 policy retry |
| `ACQUISITION_PERMANENT_*` | auth denied/unsupported media/policy deny | failed或human remediation |
| `MEDIA_ENCODING_*` | verified type conflict/decoder errors over limit | blocked或failed |
| `EXTERNAL_KEY_*` | missing/duplicate/normalizer drift | seal blocked |
| `CANDIDATE_INTEGRITY_*` | page/count/digest/Artifact mismatch | abandon/fail |
| `PREFLIGHT_BLOCKED` | typed check不通过 | admission matrix |
| `PREFLIGHT_RUNTIME_*` | handler/schema/evidence read error | retry/failed，不能human approve |
| `GATE_STALE_*` | revision/fence/target/authority冲突 | reject + audit |
| `S05_BINDING_DRIFT` | same version different digest | quarantine/fail readiness or Execution |

---

## 5. 实施切片、依赖与反例

### 5.1 推荐实施切片

| Slice | 内容 | 完成判据 |
|---|---|---|
| `S05-I1` | 四类SourceKindDefinition、descriptor模型、registry bootstrap | strict schemas + drift tests |
| `S05-I2` | logical I/O、media/encoding/budget evidence | inline/local/HTTP fixtures |
| `S05-I3` | registered API single/scatter/pagination、ExternalKey normalizer | complete/partial/exhaustion tests |
| `S05-I4` | canonicalization与四类typed output、CandidateSet page/seal | golden/property/fault tests |
| `S05-I5` | parser/browser/PDF/OCR/Vision clean与provenance/quality | representative capability fixtures |
| `S05-I6` | minimal PreflightValidator registry、allowlist、Outcome | passed/blocked/error route tests |
| `S05-I7` | ExecutionGate/Target/Decision与same-Execution resume | CAS/outbox/stale tests |
| `S05-I8` | binding/restart边界、四窗口recovery、cross-spec acceptance | chaos + legacy-dependency scan |

### 5.2 架构依赖纪律

```text
S05 definitions/capabilities
  → S03 Process runtime
  → S13 logical I/O + S16 policy/secret
  → S04 CandidateSet staging/acceptance
  → S03 route
  → S06-S09 downstream build
```

- queue只负责wake-up，不能成为CandidateSet、Outcome、gate或decision SSOT；
- S05不得直接更新Task status、Execution route、Intake lifecycle或serving pointer；
- S04不得重新实现fetch/clean/normalizer；
- S12可以合并逻辑职责到更少物理表，但不能丢失append-only、CAS、team fence和typed列；
- S13物理对象存在不构成Artifact/Candidate成功；
- S16 policy/authority失败必须fail-closed。

### 5.3 主要风险

| Risk | 级别 | 控制 |
|---|---|---|
| source/acquisition/clean再次组合成branch枚举爆炸 | P0 | 三轴registry + manifest-bound schema |
| allowlist被误读为绕过validation | P0 | mandatory validator FK/binding + negative tests |
| silent skip导致scatter伪complete | P0 | rejection manifest + exhaustion proof + seal |
| AI/OCR输出污染Revision identity | P0 | source semantic/derived split |
| human decision批准错误generation/artifact | P0 | composite target digest + CAS/fence |
| retry/resume热切implementation | P0 | Execution exact binding |
| preflight扩张为通用policy/plugin平台 | P1 | §1.5 scope fence + reopen requirement |
| `payload_extra`承载关键schema | P1 | promotion rule + schema lint |
| staged object被当作accepted truth | P0 | S04 acceptance唯一线性化点 |

### 5.4 禁止反例

以下实现一律拒绝：

1. 用`file_uuid/document_uuid`统一表示API指针、网页、PDF、member和clean产物；
2. 把`browser-pdf-vision`拼为action字符串并各自维护schema；
3. 只信扩展名/Content-Type或整包读完后才检查size；
4. API member解析失败后catch-and-skip仍声明complete；
5. 用随机UUID、`unknown` digest或第一个child替代ExternalKey/collection truth；
6. clean output写失败但Process仍返回success；
7. PreflightValidator重新请求网络、读取secret或修改状态；
8. allowlisted+passed也创建released gate和虚构human decision；
9. 把human gate state写进IntakeItem/Revision或让Process持lease等待；
10. 把九张preflight表、plugin、canary、timeout scheduler当作v1必需；
11. retry/human resume重新resolve active validator；
12. 将正文、secret、绝对路径、identity/state/proof塞进`payload_extra`。

---

## 6. 强制验收矩阵

### 6.1 Acceptance scenarios

| ID | Scenario | 必须结果 |
|---|---|---|
| `S05-A01` | fresh DB bootstrap | definitions/handlers/bindings确定性注册；二次no-op |
| `S05-A02` | same version different digest | readiness fail-loud |
| `S05-A03` | inline payload | body先staging，descriptor无正文 |
| `S05-A04` | local object | logical ref有效，absolute path拒绝 |
| `S05-A05` | static HTTP success | declared/detected/verified media与raw digest完整 |
| `S05-A06` | redirect/stream/decompress over budget | 消费期间终止，无complete candidate |
| `S05-A07` | browser/PDF acquisition | acquisition与clean capability分账 |
| `S05-A08` | local OCR / Vision clean | producer/model/prompt/loss/quality lineage完整 |
| `S05-A09` | registered API single | strict envelope/member schema与stable key |
| `S05-A10` | scatter pagination complete | exhaustion proof + stable ordering + root digest |
| `S05-A11` | provider合法空集合 | 只有profile证明exhausted才complete |
| `S05-A12` | required member malformed | rejection evidence保留，root不得自动进RAG |
| `S05-A13` | duplicate normalized key | 按definition fail/merge，结果确定性 |
| `S05-A14` | same page replay same digest | idempotent |
| `S05-A15` | same page replay different digest | conflict + abandon/fail |
| `S05-A16` | missing page/count/Artifact | seal拒绝 |
| `S05-A17` | JSON/text/HTML golden canonicalization | SHA-256/JCS/NFC/structure parser结果稳定 |
| `S05-A18` | cleaner/model版本变化，source semantics未变 | 不制造IntakeRevision |
| `S05-A19` | allowlist缺validator/check-set | activation/start fail；不fallback |
| `S05-A20` | allowlisted + passed | Outcome存在，继续RAG，无gate/decision |
| `S05-A21` | allowlisted + blocked reviewable | open gate + Execution waiting |
| `S05-A22` | blocked且missing Artifact | 不允许human approve |
| `S05-A23` | validator runtime/schema error | S03 retry/failed，不转human blocked |
| `S05-A24` | non-allowlisted + passed | open human gate |
| `S05-A25` | approve exact target | decision/gate/Execution/outbox原子，恢复same Execution |
| `S05-A26` | stale generation/fence/target decision | typed conflict + audit，无状态变化 |
| `S05-A27` | duplicate decision idempotency key | 同结果幂等；异内容冲突 |
| `S05-A28` | Outcome→transition crash | 只重放transition，不重跑/热切validator |
| `S05-A29` | gate→waiting crash | repair projection，不建duplicate gate |
| `S05-A30` | decision→outbox crash | 重放outbox，不重写decision |
| `S05-A31` | new validator version after Execution start | retry/resume继续旧binding |
| `S05-A32` | existing Task要求升级 | S02 causal restart/new generation，旧gate失效 |
| `S05-A33` | long-lived open gate | 不自动approve；Artifact/evidence引用受保护 |
| `S05-A34` | payload_extra注入identity/proof/secret | schema/lint拒绝 |
| `S05-A35` | runtime/config/DDL/API scan | 零legacy/Cloudflare/R2/D1/SMCP dependency |

### 6.2 必须留存的验收证据

1. source/validator/capability manifest、digest与bootstrap报告；
2. 四类descriptor JSON schema及negative fixtures；
3. media/encoding/redirect/stream/page budget测试；
4. ExternalKey normalizer与canonicalization golden/property报告；
5. registered API single/scatter/exhaustion/rejection fixtures；
6. CandidateSet page/root digest、seal与fault injection报告；
7. clean Artifact provenance、loss/quality与Revision-basis报告；
8. allowlist/validator passed/blocked/runtime-error矩阵；
9. gate/target/decision/CAS/outbox并发与crash报告；
10. binding drift、retry/resume与S02 causal restart报告；
11. logical responsibility→S12 physical DDL mapping；
12. runtime dependency/config/DDL/API/event/startup legacy scan。

---

## 7. Reference-anchor 台账

### 7.1 权威文档锚

| Reference | 使用方式 |
|---|---|
| `docs/baseline/qna-truth/S05.md v1.0` | Q1-Q10 owner回答、`T-O-49..76`、修订台账与final closure |
| `docs/baseline/domain-truth/D01-task-execution-process-flow.md` | Task/Execution/Process、single/scatter runtime身份 |
| `docs/baseline/domain-truth/S01-skill-worker-integration.md` | standalone boundary、strict Task contract、payload_extra |
| `docs/baseline/domain-truth/S02-task-api.md` | Task聚合、causal restart/new Execution generation |
| `docs/baseline/domain-truth/S03-workflow-engine.md` | WorkflowRevision、Process state/retry、waiting、proof/outbox/recovery |
| `docs/baseline/domain-truth/S04-intake-asset-lifecycle.md` | 五类Intake身份、CandidateSet staging/acceptance、Artifact/Revision边界 |
| `docs/baseline/spec-glossary.md` | canonical cross-domain词汇 |

### 7.2 Legacy code evidence anchors

| Ref ID | 文件锚 | 只证明的事实 / MKB verdict |
|---|---|---|
| `S05-REF-L01` | `legacy-family/smind-skill-clean-universal/services/action_registry.ts:91-148` | 多web/PDF/model clean能力；MKB拆分source/acquisition/clean三轴。 |
| `S05-REF-L02` | `legacy-family/smind-skill-clean-universal/flows/processor.ts:56-118` | strict SMCP envelope与required output经验；MKB只继承typed port原理。 |
| `S05-REF-L03` | `legacy-family/smind-skill-clean-universal/services/cleaner_doc.ts:59-151`; `cleaner_web.ts:65-337` | MIME、整包读取、raw snapshot best-effort与loss缺口；MKB fail-closed evidence。 |
| `S05-REF-L04` | `legacy-family/smind-skill-clean-dedicated-apis/services/action_registry.ts:52-104` | provider code registry生产经验；MKB内部versioned注册。 |
| `S05-REF-L05` | `legacy-family/smind-skill-clean-dedicated-apis/providers/domain/processor.ts:135-272`; `providers/chinatax/processor.ts:110-250`; `providers/realestate/processor.ts:133-317` | scatter并发、silent skip、empty success与随机child identity风险。 |
| `S05-REF-L06` | `legacy-family/smind-clean-dispatcher/services/differ.ts:94-191` | stable atomic key +多digest价值；MKB升级为ExternalKey+versioned semantics。 |
| `S05-REF-L07` | `legacy-family/smind-clean-dispatcher/flows/processor.ts:380-402`; `flows/finalizer.ts:71-89,96-269` | callback/finalize fallback、unknown digest与非原子下游注入；MKB采用seal+acceptance+outbox。 |

### 7.3 外部一手资料

| Reference | 支持边界 |
|---|---|
| [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html) | HTTP representation、metadata、validator语义；header不等于identity。 |
| [RFC 9530](https://www.rfc-editor.org/rfc/rfc9530.html) | content/repr digest分账与算法语义。 |
| [IANA Media Types](https://www.iana.org/assignments/media-types/media-types.xhtml) | verified media的规范命名基础。 |
| [WHATWG Encoding](https://encoding.spec.whatwg.org/) | encoding label、BOM、decoder error证据。 |
| [Unicode UAX #15](https://unicode.org/reports/tr15/) | NFC与NFKC语义边界。 |
| [RFC 8785 JCS](https://www.rfc-editor.org/rfc/rfc8785.html) | JSON确定性serialization。 |
| [RFC 8288](https://www.rfc-editor.org/rfc/rfc8288.html) | pagination link relation；不单独证明completeness。 |
| [W3C PROV-DM](https://www.w3.org/TR/prov-dm/) | raw/clean activity/entity与collection provenance分账。 |
| [Airbyte AbstractSource](https://github.com/airbytehq/airbyte-python-cdk/blob/main/airbyte_cdk/sources/abstract_source.py) | source-specific code check与read分离。 |
| [Great Expectations](https://docs.greatexpectations.io/docs/core/run_validations/create_a_validation_definition/) | validation definition、run result与action分账。 |
| [Kubernetes Validating Admission Policy](https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/) | policy/binding/result分离与低副作用validation。 |
| [LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) / [Argo Suspend](https://argoproj.github.io/argo-workflows/walk-through/suspending/) | durable human pause/resume原理。 |
| [Temporal Python SDK](https://github.com/temporalio/sdk-python) | deterministic replay支持运行binding不可热切的设计分母。 |

### 7.4 证据使用判定

- **保留原理**：显式capability/provider registry、typed logical I/O、strict provider schema、stable business key、多维digest、single/scatter并行；
- **全局升级**：四类source kind、三轴binding、typed evidence、deterministic CandidateSet、mandatory preflight、Execution-owned human gate、本地logical storage；
- **删除负债**：branch-name组合、schema旁路、read-all、silent skip、random child UUID、first-child shortcut、unknown digest、virtual Artifact、callback/queue成功；
- **禁止继承**：任何legacy code、wire、table、UUID/status、R2/D1/Worker binding、bootstrap数据或acceptance fixture。

---

## 8. Domain verdict

### 8.1 Verdict

**`ACCEPTED / GO`**：S05 的source/capability模型、四类typed input/output、canonicalization与CandidateSet完整性、mandatory preflight、最小allowlist/validator注册、Execution-owned human gate、exact binding及v1恢复边界已全部通过owner gate并进入正式候选真相。

### 8.2 强制结论

1. S05是Intake获取/清洗/候选构建域，不是file converter或第二套Workflow engine；
2. source kind、acquisition capability、clean capability和Workflow route必须正交；
3. raw representation、source semantics与clean derived output严格分账；
4. ExternalKey、canonicalization、member/page/root digest必须versioned且确定性；
5. CandidateSet sealed不是accepted Intake；S04 transaction仍是唯一collection线性化点；
6. allowlist永不绕过preflight，每条自动资格都绑定exact code-owned validator；
7. validator只读frozen evidence；runtime错误走S03 retry/failed；
8. 自动通过不建gate，human gate只存在于真正等待人工的Execution；
9. ReviewTarget/Decision必须绑定exact generation/fence/Artifact/Outcome并以CAS+outbox恢复同一Execution；
10. v1冻结四组durable职责而非物理表数，不建设plugin/canary/timeout/observability平台；
11. retry/recovery/resume不热切S05 binding；升级已有Task走S02 causal restart；
12. MKB保持greenfield、本地、legacy reference-only。

### 8.3 下游必须继续冻结的边界

| 下游 | 必须承接、但不由S05冒充冻结的内容 |
|---|---|
| `S06` | clean Artifact→structure_document/projection exact contract（已由S06-v1.0冻结） |
| `S07-S09` | Construction/Embedding/Index exact contract与publication proof |
| `S11/S14` | model/prompt/provider registry、fallback、cost与determinism policy |
| `S12` | 四组职责的exact Turso DDL/index/transaction/outbox/repair与capacity benchmark |
| `S13` | local logical handle/backend/atomic write、staging/orphan/reference-protected GC |
| `S15` | typed event/metric/trace、review SLA/timeout/alert/runbook与retention数值 |
| `S16` | secret/egress/allowlist/review authority与cross-team authorization |

如只落地本文interface与不变量，无需reopen S05；如要增加新source kind、让agent/外部用户定义validator、动态脚本/plugin、validator live I/O、自动timeout/approve、hot migration/canary或把human state迁入Intake，必须显式reopen。

### 8.4 一句话结论

S05 以严格、确定、可复验的source与clean contract把任意外部输入收敛为可接受的Intake候选，并用mandatory preflight、exact Execution binding与最小durable human gate保证只有证据完整、版本一致且获准的数据才能进入RAG。

---

## 9. 修订历史

| 版本 | 日期 | 作者 | 状态 | 主要变更 |
|---|---|---|---|---|
| `S05-v1.0` | `2026-07-16` | `MKB owner + Codex` | `accepted` | 吸收Q1-Q10与`T-O-49..76`最终修订；冻结四类source kind、typed input/output、canonicalization/CandidateSet、mandatory preflight、最小allowlist/validator、ExecutionGate/ReviewTarget/Decision、exact binding、四窗口recovery与greenfield ReferenceAnchor边界。 |
| `S05-v1.1` | `2026-07-18` | `MKB owner + Codex` | `accepted / D02-state-calibrated` | 保持S05 truth与v1 scope不变；分离Acquisition result、CandidateSet staging、PreflightOutcome、Gate与Execution状态；明确S05 exact capability key优先于早期coarse family；修正CandidateSet合法边表述，curation/loss policy按D02-v1.0移交S05/S06/S02。 |
| `S05-v1.1-cal` | `2026-08-11` | `MKB owner + Codex` | `accepted / S13-calibrated` | 接收S06-v1.0：S06消费admitted clean且input digest后冻结；完整clean curation产品不因S06扩为v1主路径；Gate最小面可保留。 |
| `S05-v1.1-cal-s12` | `2026-08-11` | `MKB owner + Codex` | `accepted / S13-calibrated` | 接收S12-v1.0：TX-08/outbox；S05语义不变。 |
| `S05-v1.1-cal-s13` | `2026-08-11` | `MKB owner + Codex` | `accepted / S13-calibrated` | 接收S13-v1.0：staging port/handle/gate evidence 引用保护落地。 |
