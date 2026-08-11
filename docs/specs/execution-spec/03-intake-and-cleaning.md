# ES-03 — Intake and Cleaning

> **项目**：myknowledgebase（MKB）
>
> **文件 ID**：ES-03
>
> **文档性质**：execution-spec / implementation authority
>
> **版本 / 日期**：ES-03-v1.0 / 2026-08-10
>
> **文档状态**：ready
>
> **Truth 输入**：OT-01-v1.0、OT-02-v1.0、OT-03-v1.0、OT-04-v1.0
>
> **Baseline 输入**：S04-v1.2、S05-v1.1、D02-v1.0
>
> **上游 Execution Spec**：ES-01-v1.0、ES-02-v1.0
>
> **Cross-spec calibration**：ES-04-v1.0、ES-07-v1.0
>
> **上游索引**：docs/specs/index.md

本文件是 MKB v1 Intake 与 Cleaning 执行域的唯一 Execution Spec。它拥有四类 source descriptor、source binding、acquisition/decode/clean、typed evidence、CandidateSet、五类 canonical Intake identity、mandatory preflight、ExecutionGate、Item lifecycle、acceptance/publication/cleanup command 以及相应逻辑数据库 schema、内部接口和协议。

Task aggregate 与公共 HTTP adapter 由 ES-01 持有；Workflow、Execution、Process 与 route 由 ES-02 持有；物理 DDL、事务 driver、outbox 和对象 backend 由 ES-04 持有；模型/Prompt/Process registry 由 ES-05 持有；derived/vector/index proof 分别由 ES-06/07 持有。ES-03 不创建第四层 runtime identity，也不持有产品业务。

---

## 1. Inherited Truth

### 1.1 权威输入

| 来源 | 本文件直接继承 | 本文件不得改变 |
|---|---|---|
| OT-01-v1.0 | MKB 只处理、转换、存储和获取 knowledge；内部状态/lifecycle 由 MKB 自持 | 不引入 CMS、人工审核产品、上游业务或 final answer |
| OT-02-v1.0 | 五类 Intake identity；六个且仅六个 StateFamily；proof 向上、control 向下 | 不增加 File/Document/Attempt/ReviewItem 身份或第七 StateFamily |
| OT-03-v1.0 | 四类 source；冻结 acquisition/clean 能力；mandatory preflight；受控 Gate；无 raw-vector surface | 不增加任意 connector、dynamic plugin、caller validator 或新 request intent |
| OT-04-v1.0 | strict/proof-backed end-to-end success；single/scatter、failure 与 representative retrieval gate | acquisition/clean 成功不得冒充 Task 或 retrieval 成功 |
| S04-v1.2 | 五类 Intake identity、十张 canonical truth tables、Revision/serving/lifecycle、Candidate acceptance 与 cleanup proof | 不把 Snapshot failure、latest、review、purge 或 runtime phase拼成 Intake 状态 |
| S05-v1.1 | 四类 source、13 个 acquisition/clean/preflight capability、typed evidence、preflight/Gate 与 exact binding | 不复制 legacy branch、silent skip、callback success 或外部 plugin |
| D02-v1.0 | Item 三态、CandidateSet 四态、Gate 四态及 state-vs-fact 宪法 | exact edge、owner 和 typed fact 分类不得漂移 |
| ES-01-v1.0 | 六个 intent wire、source_descriptor 槽位、Gate Task-scoped facade、atomic rebuild | ES-03 不增加公共 route 或直接公开 Intake mutation |
| ES-02-v1.0 | exact Process keys、Workflow binding、ProcessCommand/Outcome、preflight→seal→accept与index rebuild fan-out | ES-03 handler 不选 next step、不直写 Execution/Task |
| ES-07-v1.0 | PublicationProof、active index pointer、filter reuse、same-Revision reindex与logical withdrawal | ES-03仍唯一拥有Item lifecycle/latest/serving；只在atomic owner UoW协作 |

### 1.2 Truth 到交付物映射

| Truth cluster | 本文件落点 |
|---|---|
| S04-T001..T014 | §4.2、§4.5、§5.3 canonical identity/semantic schema |
| S04-T015..T023 | §4.7、§4.9、§5.3、§6 serving/lifecycle/dual fence |
| S04-T024..T032 | §4.6、§4.8、§4.9、§5.4/5.6、§6 acceptance/recovery |
| S04-T033..T044 | §4.8、§5.6、§6、§8 cleanup/bootstrap/greenfield evidence |
| S04-T045..T048 | §4.2..4.8、§5.4/5.5 S05 binding/preflight/Gate |
| S05-T001..T013 | §4.2..4.6、§5.2/5.4 source/evidence/canonicalization |
| S05-T014..T024 | §4.6..4.9、§5.5 mandatory preflight/Gate |
| S05-T025..T030 | §4.3、§4.9、§5.4/5.5、§6 binding/recovery |
| D02 Intake mirrors | §4.7 exact states/edges、§6.1 state/fact lint |

### 1.3 唯一 ownership

| Concern | 唯一 owner | 跨域权限 |
|---|---|---|
| IntakeSource/Snapshot/Item/Revision/Artifact/Membership | ES-03 Intake owner services | 其他 ES 只提交 typed command/proof 或读取 exact ref |
| IntakeCandidateSet | ES-03 staging/acceptance services | producer 可 append/seal/abandon；只有 acceptance owner 可 sealed→accepted |
| IntakeItem lifecycle/latest/serving | ES-03 IntakeTransitionService | ES-07提交validated publication candidate，final Proof与双pointer同UoW；Task/runtime不得直写 |
| Acquisition/Clean evidence | ES-03 capability handlers | ES-02 只验证 ProcessOutcome envelope |
| PreflightOutcome | ES-03 validator | ES-02 只消费 immutable outcome 做 route |
| ExecutionGate/ReviewTarget/Decision | ES-03 GateTransitionService | ES-01 仅 Task-scoped facade；ES-02 仅以 owner port推进 Execution |
| Task/Audit/Restart | ES-01 | ES-03 不改 aggregate |
| Workflow/Execution/Process | ES-02 | ES-03 返回 Outcome/fact，不选 route |
| Physical transaction/object/outbox | ES-04 | 本文件冻结逻辑原子性、schema与handle contract |
| Capability/model/prompt/schema registry | ES-05 | ES-03提供所需 manifests 与 exact refs |
| Derived generation | ES-06 | ES-03只提供 accepted Revision 与 clean Artifact |
| Vector/index/publication proof | ES-07 | ES-03验证candidate，final proof与Item/index transitions同UoW |
| Secret/authority/egress/limits | ES-08 | ES-03只消费 logical policy/secret/actor refs |

### 1.4 本文件关闭的 D02 移交

本文件在不修改 D02 状态语义的前提下关闭两个 executional spelling：

1. Membership decision exact enum 固定为 seen_new_revision、seen_no_change、absent_deactivated、absent_no_change；
2. Gate decision action exact enum 固定为 approve、approve_override、reject、reclean。

它们是 immutable outcome/action，不是新增 StateFamily。任何新增 spelling 必须先在本文件证明无法由现有值表达，并按 D02 drift 协议校准；不得借 payload_extra 注入。

---

## 2. Scope / Non-scope

### 2.1 Scope

ES-03 只负责：

1. inline_payload、local_object、http_resource、registered_api 四类 strict descriptor；
2. source identity/config/secret/body 分账与 IntakeSource resolve/create；
3. 18 个 ES-02 已登记 Process capability 的 exact typed input/output/proof；
4. acquisition、media/encoding/budget、ExternalKey、canonicalization 与 clean lineage；
5. AcquisitionEvidence、CandidateMember、CleanArtifactCandidate 和 paged CandidateSet；
6. mandatory preflight、allowlist binding、PreflightOutcome 与 admission fact；
7. 五类 canonical Intake identity、十表 SSOT、RevisionFingerprint、Membership/ChangeSet；
8. CandidateSet 四态、IntakeItem 三态、ExecutionGate 四态的 owner transition；
9. latest/serving 双 pointer、PublicationProof CAS、metadata/deactivate/delete/absence/cleanup plan；
10. single/scatter、rebuild、metadata、lifecycle、Gate、recovery 的执行链；
11. 所有逻辑数据库 record、application port 与 durable message contract。

### 2.2 Non-scope

- 不提供第五码 source、任意 URL/API connector、任意 header/cookie、动态 ETL、plugin、agent rule 或 caller-supplied code；
- 不建设 file manager、document CMS、内容编辑器、人工审核 UI、协作/审批产品或 Knowledge promotion/fusion；
- 不提供 IntakeSource/Item/Revision/Artifact public CRUD、direct pointer patch、deleted restore 或 hard delete；
- 不创建 failed/pending Snapshot、draft/failed Revision、reviewing Item、cleaning Artifact 等组合状态；
- 不让 model/OCR/Vision/clean output 单独制造 IntakeRevision；
- 不定义 Workflow graph、Process claim/retry、模型 provider、LS-RAG schema、embedding/index 或 retrieval；
- 不把 body/bytes、secret、absolute path、runtime payload 或核心关系放入 JSON extension；
- 不支持 legacy API/wire/table/status/UUID/storage/callback/bootstrap 数据；
- 不将 queue ACK、HTTP 2xx、object existence、sealed CandidateSet、Gate click 或 Process success当作 accepted/published success。

### 2.3 完成定义

ES-03的`ready`是规范状态：以下义务已被完整定义并通过cross-spec audit，不表示它们已在尚未构建的实现上运行。任何实现要声明符合ES-03-v1.0并进入release，必须同时满足：

1. 四类 public descriptor 与 normalized internal descriptor 有 strict schema/golden fixtures；
2. 18 个 Process manifest 均可由 ES-05 注册并被 ES-02 compiler exact-bind；
3. §5 全部逻辑表映射到 ES-04 physical DDL 且约束无损；
4. 三个 StateFamily 的 exact edge、owner、CAS 与非法边穷举通过；
5. single/scatter/preflight/seal/accept/publication/lifecycle/Gate 全链路 proof-backed；
6. failure injection 证明不存在 partial Snapshot、partial Item transition、duplicate Gate decision 或 serving 空窗；
7. ES-01/02/04/05/06/07/08 全部协议经最终 cross-spec audit；
8. §8 所有 HARD acceptance 自动化通过。

### 2.4 核心术语

| 术语 | Exact 含义 |
|---|---|
| Source descriptor | caller-neutral、strict 的输入描述；不是 IntakeSource identity row |
| IntakeSource binding | definition、descriptor identity、config/secret refs 和 execution fence 的 immutable exact binding |
| ExternalKey | source namespace 内的稳定 member identity tuple 的版本化归一化结果 |
| CandidateSet | transaction 外构建、可 seal 的 staging collection；不是 Snapshot |
| IntakeSnapshot | canonical acceptance 成功后才存在的 immutable observation |
| Revision basis | 由 exact SemanticDefinition 决定是否产生 IntakeRevision 的 source-grounded tuple |
| Clean artifact | raw/canonical input的派生表示；不是 Revision identity |
| PreflightOutcome | passed/blocked immutable业务事实；runtime error不是 blocked |
| ExecutionGate | clean后、RAG前，绑定 exact target 的 durable human wait control |
| PublicationProof | ES-07 对 exact Item/Revision/generation 的 type-specific durable proof |

---

## 3. Scope Impact Audit

~~~text
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
~~~

本文件只把 S04-v1.2、S05-v1.1、D02-v1.0 和 ES-01/02 已冻结内容落成 exact execution contract。新增的 enum spelling、schema 列、digest recipe、table mapping、port、message 与有限 budget 都是 ES-03 槽位内实现选择；不增加 source、intent、public capability、domain identity、StateFamily、服务或文件。

---

## 4. Architecture Decisions

### 4.1 单体内部模块与依赖

~~~text
ES-01 HTTP/Task adapter
  → intake ingress normalizer
  → ES-02 Workflow/Process runtime
       → source capability handlers
       → candidate/preflight application services
       → canonical intake owner services
       → gate owner service
            → ES-04 UoW/object/outbox ports
            → ES-05 capability/model registry ports
            → ES-08 secret/policy/authority ports

accepted Revision/CleanArtifact
  → ES-06 derived build
  → ES-07 vector/index proof
  → ES-03 publication owner CAS
~~~

固定模块：

- intake.domain：五类 identity、semantic/action definitions、Item/Candidate/Gate transition rules；
- intake.application：source bind、candidate staging、acceptance、metadata/lifecycle/publication、Gate decision；
- intake.capabilities：18 个 leaf handlers；每个只消费 ProcessCommand 并返回 ProcessOutcome；
- intake.adapters：HTTP/browser/PDF/OCR/model、logical object、repository、outbox 的实现；
- intake.projections：Task items/gates 与 eligibility 只读投影，无 mutation 权。

Domain/application不得导入 HTTP request、Turso driver、filesystem path、queue implementation、legacy DTO 或上游业务 schema。

### 4.2 四类 source 与 exact descriptor

#### 4.2.1 固定 taxonomy

| Source kind | Cardinality | Identity descriptor | 合法 acquisition |
|---|---|---|---|
| inline_payload | single | external_resource_uuid 或 one-off Task identity | intake.acquire.inline |
| local_object | single | logical_object_ref + optional external_resource_uuid | intake.acquire.local_object |
| http_resource | single | canonical URI + source profile + optional external_resource_uuid | http_static 或 http_browser |
| registered_api | single/collection | provider+operation+typed scope digest + optional external_resource_uuid | intake.acquire.registered_api |

Browser、PDF、OCR、Vision、pagination、single/scatter均不是 source kind。Source kind、acquisition、decode/clean 与 cardinality 是四个正交轴。

#### 4.2.2 Public descriptor union

所有 variant 共同包含：

| Field | Rule |
|---|---|
| schema_version | 固定 mkb.source-descriptor.v1 |
| source_kind | 四值 discriminator |
| declared_media_type | IANA-style lower-case；unknown必须显式 application/octet-stream |
| config_profile_ref | 只能引用 code-owned registered profile；可空仅限 inline/local default |
| secret_slot_bindings | registered slot→logical secret ref；不含 secret value |
| payload_extra | object；不参与 identity/route/proof |

Variant exact fields：

| Variant | Required | Optional | Strictly forbidden |
|---|---|---|---|
| inline_payload | content_encoding=text或base64、content、declared_media_type | declared_charset | logical/absolute path、credential、caller capability |
| local_object | logical_object_ref、declared_media_type | filename_hint、expected_digest、expected_size_bytes | absolute path、正文、arbitrary backend |
| http_resource | canonical_uri、http_profile_ref、expected_media_types | validator_policy_ref、secret slot refs | userinfo、fragment、arbitrary method/header/cookie/fetch option |
| registered_api | provider_key/version、operation_key/version、query_scope_ref/digest、pagination_profile_ref、completeness_profile_ref | registered secret slot refs | raw URL、raw params、code、unregistered schema |

API adapter先对 inline content 做bounded decode并通过 ES-04 staging port写入content-addressed logical object，再把 Task immutable payload正规化为 handle/digest/size；正文不进入Task row、queue、log或payload_extra。Task creation fingerprint使用正规化后的descriptor，重复正文收敛到同digest。

#### 4.2.3 IntakeSource resolution

Source identity digest固定为：

~~~text
SHA256(JCS({
  recipe: "mkb-source-identity-v1",
  team_uuid,
  source_kind,
  source_kind_definition_version,
  identity_descriptor
}))
~~~

identity_descriptor规则：

- 有 external_resource_uuid 时，以该UUID为稳定上游关联，并同时校验kind-specific identity fields；同UUID异identity digest冲突；
- inline且无external_resource_uuid时使用Task UUID形成one-off Source；
- local使用logical_object_ref；
- HTTP使用versioned canonical URI + identity profile；
- registered API使用provider/operation exact versions + query_scope_digest。

Resolve/create以 team + source_identity_digest 唯一；同digest重放返回同IntakeSource。同上游UUID或同source key出现definition/descriptor drift必须fail-loud，不能静默建第二Source。Caller永远不能提交intake_source_uuid。

### 4.3 Exact S05 binding

ES-02 将 root Execution 从 created 推进到 ready 前，必须通过 IntakeExecutionBindingPort 原子完成：

1. 解析 code-owned SourceKindDefinition exact key/version/digest；
2. strict validate并正规化descriptor，resolve/create IntakeSource；
3. 解析 acquisition、decode、clean、normalizer、canonicalizer、preflight、allowlist和必要model/prompt exact refs；
4. 校验所有 ProcessCapabilityManifest、handler、schema、secret slot与policy引用；
5. 计算 s05_binding_digest 并写 immutable intake_execution_bindings；
6. 保留 root Execution 创建时已冻结的 task_input subject，仅将 Execution.domain_binding_ref/digest 与 s05_binding_digest CAS 固定；
7. 由 ES-02 materialize first Process。

Binding envelope canonical fields按kind→capability role→key/version→digest排序，以 SHA-256(JCS) 计算。retry、recovery、human resume与bounded reclean只能使用该binding；active registry变化只影响新Execution。同key/version异digest直接隔离并失败。

### 4.4 Exact Process capability catalog

每个 manifest 使用 mkb.process-capability-manifest.v1，禁止alias、optional unknown port或handler自行route。

| Process key | Strict input → typed output | Proof / side effect | Idempotency 与 failure |
|---|---|---|---|
| intake.acquire.inline | normalized inline handle → AcquisitionEvidence | staged representation readable proof | content digest；I/O mismatch non-retryable |
| intake.acquire.local_object | logical object descriptor → AcquisitionEvidence | streamed digest/media/budget proof | handle+expected digest；transient reader可retry |
| intake.acquire.http_static | registered HTTP descriptor → AcquisitionEvidence | request profile/final URI/redirect/validator/bytes proof | registered read-only GET/HEAD profile；timeout/429/5xx retryable |
| intake.acquire.http_browser | HTTP descriptor+browser profile → rendered AcquisitionEvidence | rendered representation+browser profile lineage | exact profile/input digest；crash retryable，policy deny permanent |
| intake.acquire.registered_api | provider operation/scope → page/envelope evidence | cursor/link/exhaustion/rejection evidence | read-only registered operation；provider-classified retry |
| intake.decode.text_json_html | representation evidence → canonical source values | canonicalizer/schema/media proof | pure/content-addressed；schema/media permanent |
| intake.decode.pdf | PDF evidence → page/text/image evidence | page count/text layer/image/loss proof | pure/content-addressed；corrupt PDF permanent |
| clean.extract.deterministic | decoded evidence → CleanArtifactCandidate | anchors/loss/quality/lineage proof | pure/content-addressed |
| clean.ocr.local | image/page evidence → CleanArtifactCandidate | OCR engine/profile/page/confidence proof | content-addressed；resource transient可retry |
| clean.extract.vision | image/page evidence+exact model/prompt → CleanArtifactCandidate | invocation/model/prompt/quality lineage | ES-05 invocation idempotency；provider policy分类 |
| clean.map.registered_api | typed envelope/member → member/clean candidates | provider schema/key/semantic/rejection proof | provider+operation+member identity |
| intake.preflight_validate | frozen root candidate或accepted-item clean evidence → PreflightOutcome | ordered check evidence；no live I/O | same scope/root/binding/check-set返回同Outcome；runtime error走Process failure |
| intake.collection.seal | candidate+PreflightOutcome → CandidateSetSeal | root/count/exhaustion/artifact/preflight proof | open CAS；同digest幂等，异digest冲突 |
| intake.accept_snapshot | sealed candidate → IntakeAcceptanceResult | Snapshot/ChangeSet/acceptance proof | observation+root fence；canonical transaction |
| intake.metadata.apply | exact Item+CAS+metadata → MetadataApplyResult | no_change/filter_change/semantic_revision proof | command/fingerprint+Item revision CAS |
| intake.lifecycle.deactivate | exact Item+CAS → LifecycleTransitionResult | transition+serving-cleared proof | action fence+Item revision CAS |
| intake.lifecycle.delete | exact Item+CAS → LifecycleTransitionResult | tombstone+serving-cleared proof | action fence+Item revision CAS |
| intake.cleanup.plan | exact Item/transition+policy → CleanupPlanResult | cleanup intent+required substrate digest | target+policy+causation fence |

Acquisition/clean handler只能写ES-04 staging object与自身typed evidence；accept/metadata/lifecycle/cleanup handler只能调用ES-03 owner port。任何handler都不能接收Task repository、Execution transition、Workflow graph、next step或raw secret。

### 4.5 ExternalKey、canonicalization 与 RevisionFingerprint

#### 4.5.1 ExternalKey recipe

~~~text
normalized_external_key =
  "ek1:" + normalizer_key + ":" +
  SHA256(JCS(typed stable source identity tuple))
~~~

Raw identity tuple、normalizer key/version/digest与normalized value均保存为evidence。inline/local/HTTP single source使用注册的singleton tuple；registered_api必须从provider member schema的稳定业务字段生成。随机UUID、content digest、array ordinal、filename或first-child fallback全部禁止。

同一CandidateSet中normalized key唯一。duplicate policy只有fail或merge_identical：merge仅在raw identity tuple、semantic tuple和artifact digest全部一致时允许；否则candidate integrity failure。

#### 4.5.2 Canonicalization recipes

| Value | Recipe | Digest input |
|---|---|---|
| JSON | RFC8785/JCS、strict schema | recipe/schema/canonicalizer version + canonical bytes |
| Text | UTF-8 decode、LF、Unicode NFC | encoding evidence + canonicalizer version + bytes |
| HTML | versioned structural parser、DOM semantic extraction | parser/profile/schema versions + canonical structure |
| Opaque bytes | no semantic decode；仅definition明确允许 | media/profile + raw digest；不得由content hash冒充ExternalKey |
| Metadata | exact context/filter schema + JCS | schema version/digest + canonical object |

默认不做NFKC、不用regex strip HTML、不信filename/extension/Content-Type单一证据。declared、detected、verified media和encoding label/BOM/detector/error count分别留证。

#### 4.5.3 Semantic definitions

首版 exact definitions：

| semantic_key | value kind | fingerprint | route fact |
|---|---|---:|---|
| source_representation | artifact_ref | no | representation_changed |
| canonical_content | artifact_ref或typed_scalar | yes | content_changed |
| context_metadata | typed_json | yes | context_changed |
| filter_metadata | typed_json | yes | filter_changed |

RevisionFingerprint：

~~~text
SHA256(JCS({
  recipe: "mkb-revision-fingerprint-v1",
  tuples: ordered by semantic_key [
    semantic_key,
    definition_version,
    definition_digest,
    value_kind,
    value_digest
  ] where fingerprint_participation=true
}))
~~~

相同fingerprint为no-change；clean/model/OCR/Workflow/embed/index version变化不参与该fingerprint。filter-only变化仍追加IntakeRevision，但允许复用内容derived substrate并走ES-07 filter update+publication验证；content/context变化走完整LS-RAG。

### 4.6 Typed evidence、collection 与 preflight

#### 4.6.1 三层表示

| Plane | Owner/record | 是否Revision basis |
|---|---|---:|
| Raw representation | AcquisitionEvidence + snapshot-owned IntakeArtifact | no |
| Source-grounded canonical semantics | CandidateSemantic → RevisionSemantic | 由definition决定 |
| Clean-derived output | CleanArtifactCandidate，accepted后revision-owned IntakeArtifact | no，作为ES-06输入 |

Model、Vision、OCR或summary只能改变clean-derived output。若source-grounded canonical tuple缺失，不能用model猜测补齐。

#### 4.6.2 Candidate integrity

Candidate page/member ordinal由source稳定排序决定，不得按并发完成顺序。Exact digest：

~~~text
member_digest = SHA256(JCS(member immutable identity/semantic/artifact/rejection envelope))
page_digest   = SHA256(JCS(page fields + ordered member digests))
root_digest   = SHA256(JCS(head acceptance fields + ordered page digests))
~~~

Candidate anomaly kind固定为：

source_not_exhausted、pagination_gap、member_rejected、duplicate_key、
artifact_missing、budget_exceeded、schema_invalid、media_invalid、encoding_loss。

Anomaly另有required=true/false、scope、typed code/evidence ref。partial可以保存可信seen member；complete必须具备source-exhausted proof且required anomaly为0。合法空集也必须有exhaustion proof。任意缺页、count/byte mismatch、不可读Artifact或unknown digest都不能seal。

#### 4.6.3 Mandatory preflight order

唯一顺序：

~~~text
pages/members/evidence frozen by expected-set fence
  → intake.preflight_validate
  → immutable PreflightOutcome binds root/binding/fence
  → intake.collection.seal recomputes and validates same digest
  → intake.accept_snapshot
~~~

PreflightValidator只能通过PreflightEvidenceReader读取frozen refs；无network、secret、path、object mutation、clean、route或gate写权限。结果只允许passed/blocked。handler crash、schema drift、evidence read error必须返回Process failed/retryable disposition，绝不写blocked。root_candidate Outcome负责seal/acceptance fence；accepted_item Outcome负责scatter child或post-accept reclean的RAG admission，不回写CandidateSet状态。

Admission：

| Allowlist / Outcome | Reviewable | Exact route fact |
|---|---:|---|
| allowlisted + passed | 任意 | auto_admit；不创建Gate |
| allowlisted + blocked | yes且override policy允许 | human_review |
| allowlisted + blocked | no | admission_failed |
| non-allowlisted + passed | yes | human_review |
| non-allowlisted + blocked | yes且policy允许 | human_review或admission_failed，由compiled guard固定 |
| 任意runtime/schema/evidence error | 任意 | Process retry/failed；无Gate |

S04 canonical acceptance发生在seal之后；Gate发生在acceptance之后、LS-RAG之前。accepted Snapshot/Revision不代表RAG admission或serving。

### 4.7 三个 StateFamily 与正交事实

#### 4.7.1 IntakeCandidateSet staging

~~~text
create → open → sealed → accepted
            └────────→ abandoned
~~~

| Edge | Owner / guard / effect |
|---|---|
| create→open | StagingService；unique candidate UUID+producer fence+binding；head建立 |
| open→sealed | SealService；完整pages/count/bytes/dedupe/artifact/exhaustion/preflight/root验证；CAS |
| open→abandoned | StagingService；timeout/invalid/size/cancel且尚未seal；CAS+reason |
| sealed→accepted | AcceptanceService；canonical transaction成功并绑定Snapshot/ChangeSet |

accepted/abandoned terminal；sealed后不可append/replace/hot-switch，重复accept只返回同Snapshot。Candidate status不是Process status；preflight result、completeness和anomaly也不是status。

#### 4.7.2 IntakeItem lifecycle

~~~text
create → active → deactivated → active
             └───────────────→ deleted
       active ───────────────→ deleted
~~~

| Action key | From | To | Core effects |
|---|---|---|---|
| create_item | not_exists | active | SET_ACTIVE + ACCEPT_LATEST |
| accept_revision | active/deactivated | unchanged | ACCEPT_LATEST |
| publish_revision | active | active | SET_SERVING |
| deactivate | active | deactivated | CLEAR_SERVING + SET_DEACTIVATED |
| reactivate | deactivated | active | SET_ACTIVE；serving保持null |
| delete | active/deactivated | deleted | CLEAR_SERVING + SET_DELETED |
| absence_deactivate | active | deactivated | CLEAR_SERVING + SET_DEACTIVATED |

deleted为v1 terminal。accept/publish/no-change不产生新lifecycle state。latest与serving均为CAS selection pointer，不是状态。

create_item不是第四个Item状态；not_exists是创建前置条件，首个提交态仍只有active。Item insert、ordinal-1 Revision、create_item transition与Membership必须在同一acceptance transaction成立，transition的before lifecycle/pointers为null、item_revision_before=0。

Reappearance规则固定：只有最近一次进入deactivated的action为absence_deactivate且当前complete observation再次seen时，acceptance transaction可先reactivate再apply revision decision；人工deactivate不会被普通ingest自动反转。reactivate后不恢复旧serving，必须重新取得PublicationProof。

#### 4.7.3 ExecutionGate

~~~text
need-review → open → released
                    ├→ rejected
                    └→ superseded
~~~

| Decision action | Gate edge | Guard / Execution effect |
|---|---|---|
| approve | open→released | passed non-allowlisted或普通review target；same Execution resume |
| approve_override | open→released | blocked但artifact/evidence完整且binding policy明确允许；记录override proof |
| reject | open→rejected | required scope提交failure fact；scatter siblings继续collect-all |
| reclean | open→superseded | target允许且remediation budget未用；same Execution进入一个compiled、acyclic、最多一次的clean→preflight remediation branch |

Gate terminal不可reopen。reclean不是Process retry，也不改写旧Artifact/Outcome；它产生新immutable CleanArtifactCandidate/PreflightOutcome，必要时形成新Gate。默认每Execution最多一次，第二个Gate不再暴露reclean。若compiled Workflow无该branch，allowed_actions不得包含reclean。

Gate status、Decision action、Execution waiting、Task action_required和Intake lifecycle严格分账。

#### 4.7.4 Membership exact decision

| decision_kind | Seen? | Revision ref | Item effect |
|---|---:|---|---|
| seen_new_revision | yes | 本Snapshot新建Revision | create Item或CAS latest |
| seen_no_change | yes | 既有exact Revision | no Revision；可按reappearance规则reactivate |
| absent_deactivated | no | null | complete-authoritative policy使active Item deactivated |
| absent_no_change | no | null | 已deactivated或policy不要求新transition；留collection fact |

absence只允许complete + authoritative scope。partial、timeout、provider error、parser skip、非权威空集合不得生成任何absent decision。

### 4.8 执行链路

#### 4.8.1 Ingress normalization 与 source bind

~~~text
ES-01 strict intake.ingest
→ inline body staged if applicable
→ immutable Task/Audit/outbox commit
→ ES-02 creates root Execution(created)
→ ES-03 resolves SourceDefinition + IntakeSource + s05 binding
→ immutable task_input subject remains unchanged；domain binding fixed
→ first Process materialized; Execution ready
~~~

Source binding失败只使Execution/Task失败；不得留下Snapshot/Item/Revision。已成功写入但未引用的staging object进入ES-04 orphan治理。

#### 4.8.2 Single ingest

~~~text
acquire
→ decode/canonicalize
→ deterministic/OCR/Vision clean as exact Workflow requires
→ one CandidateMember/page/root
→ mandatory preflight
→ seal
→ canonical acceptance
     Snapshot + Membership + Item/Revision decision + ChangeSet/outbox
→ admission
     auto_admit | Gate waiting
→ ES-06 structurize/construct
→ ES-07 embed/stage/validate publication
→ ES-03 publication CAS sets serving
→ root proof → Task aggregate
~~~

single必须有一个seen membership，除非SourceKindDefinition显式允许complete empty；acquisition/decode/missing artifact failure不得伪装empty。

#### 4.8.3 Scatter ingest

~~~text
registered API root acquire/paginate
→ envelope/member validation + stable ExternalKey/order
→ CandidatePage(s), rejection/gap/exhaustion evidence
→ root mandatory preflight
→ seal
→ one canonical acceptance transaction
     one Snapshot + N seen/absence Memberships
     Item/Revision decisions + typed ChangeSet
     required child scheduling intents
→ optional root Gate
→ ES-02 materializes exact required child set
→ each child binds accepted Item/Revision
→ child runs applicable clean + item-scoped mandatory preflight + optional Gate
→ admitted child independently builds/publishes
→ root collect-all
~~~

fan-in分母只来自committed ChangeSet required facts。child创建不产生child Task；健康child不因sibling失败而取消；proof-valid child不因root失败/cancel回滚。

#### 4.8.4 Rebuild 与 metadata

intake.rebuild读取exact existing Item/Revision，拒绝deleted、stale expected Revision或latest猜测；不执行acquisition/clean、不创建Snapshot/Revision，直接交ES-06/07创建新derived/index generation。active Item在完整PublicationProof后可切serving；deactivated Item只产生validated-but-not-served rebuild proof并保持serving null，Task不得把它投影为retrieval-ready。

intake.update_metadata：

| Diff result | Canonical effect | Downstream |
|---|---|---|
| no_change | 无Revision；写typed noop proof | Task可按type-specific proof完成 |
| filter_change | append Revision，以新Revision-owned logical Artifact refs复用同content-addressed bytes，复制content/context semantics并替换filter | ES-07 update_filters + publication validation；不重跑LS-RAG |
| semantic_revision | append Revision，context/content-affecting semantic变化 | 完整ES-06/07 build |

active Item可在PublicationProof后切serving；deactivated Item只更新latest并保持serving null；deleted拒绝。canonical_metadata必须分别通过binding指定的context/filter schema，禁止payload_extra驱动diff。

#### 4.8.5 Deactivate、delete、publication 与 cleanup

~~~text
deactivate/delete Process
→ ES-03 validates team/action/version/expected Item revision/pointers
→ same transaction:
     Item CAS + append transition + serving null + outbox
→ ES-07 withdraws serving/index visibility
→ cleanup.plan creates bounded cleanup intent
→ Task succeeds on logical-fence/tombstone proof
→ physical cleanup converges asynchronously under ES-04/08 policy
~~~

Publication：

~~~text
ES-07 PublicationCandidate(exact team/item/revision/index generation + validation material)
→ ES-03 validates lifecycle + expected latest/serving/Item row revision + proof schema/digest
→ ES-07 validates expected active index pointer/generation revision
→ one ES-04 intake_publication_v1 transaction:
     IndexValidationReport + PublicationProof
     ActiveIndexPointer CAS + transition
     Item serving CAS + transition
     Process Outcome + outbox
→ retrieval dual fence becomes eligible
~~~

首次/新Revision publication改变serving值；same-Revision reindex保持serving_revision_uuid数值不变，但publish_revision transition、Item row_revision、index pointer revision和proof都必须前进，使新generation选择可审计。失败publication对Item serving与active index pointer均whole rollback，不污染旧serving。Task cancel不撤销已published result。Delete不等待physical purge；purge不改Task/Item状态。

#### 4.8.6 Human Gate

~~~text
accepted Intake + preflight admission fact
→ ES-03 creates immutable ReviewTarget + open Gate
→ ES-02 Execution owner CAS to waiting(human_review) + outbox
→ ES-01 exposes bounded Task-scoped projection
→ exact decision command
→ one UoW:
     authority/team/target/revision/fence/idempotency validation
     append Decision
     Gate CAS terminal
     ES-02 owner CAS resume/fail/remediation fact
     outbox append
→ same Execution resumes or converges
~~~

Open Gate不持Process lease且默认durable indefinite、永不自动approve。Gate release/reject/reclean不修改Snapshot、Revision、Item lifecycle或serving pointer。

### 4.9 原子边界

| Boundary | Must commit together | Forbidden partial result |
|---|---|---|
| Source bind | source resolve/create、execution binding、ES-02 domain-binding CAS、first scheduling intent | immutable subject mutation、unbound ready Execution或duplicate Source |
| Candidate append | page/member/evidence refs、page digest、head counters CAS | half page或counter drift |
| Preflight | Outcome、ordered check evidence、outbox/Process outcome receipt | passed无evidence |
| Seal | expected pages/count/bytes/artifacts/preflight/root validation + state CAS | sealed unknown root |
| Acceptance | Snapshot、Artifact canonical ownership、Item/Revision/Semantics、Membership、ChangeSet/facts、transitions、child intents/outbox、Candidate accepted | partial collection truth |
| Metadata/lifecycle/publication | action/proof/policy guard、Item CAS、transition、outbox | pointer change无ledger/proof |
| Gate open | ReviewTarget、Gate、ES-02 waiting CAS、outbox | open Gate但Execution active无wait |
| Gate decision | Decision、Gate CAS、ES-02 control CAS、outbox | released Gate无wake或duplicate Decision |
| Cleanup proof | verified substrate proof、intent aggregate CAS、event | physical_complete缺required proof |

ES-04必须以同一local write transaction实现跨owner UoW；application service只能调用owner transition method，不能绕过owner用裸repository update。

---

## 5. Contracts and Data

### 5.1 逻辑类型与总约束

沿用 ES-01 的 UUID、UTC timestamp、canonical JSON、SHA-256、boolean、counter/revision 约定。MKB 内生 identity 使用 UUIDv7。所有 team-owned FK、unique、query均包含team fence；跨team lookup对外按不存在处理，内部留safe security event。

所有下列 ES-03-owned 业务表必须有 payload_extra NOT NULL DEFAULT {}，且核心代码不得从中读取 identity、state、fence、route、proof、authority、secret、正文、bytes或filter。Registry、Snapshot、Revision、Membership、evidence、Decision、transition等immutable host的payload_extra也immutable；mutable host只能随正常CAS transaction更新。

Digest值必须同时绑定algorithm与canonicalization/schema/definition version。所有 logical ref 是opaque、typed、team-scoped handle；禁止absolute path、backend bucket/key、signed URL或credential。

### 5.2 Public 与 normalized intake payload

#### 5.2.1 Public ingest

~~~json
{
  "source_descriptor": {
    "schema_version": "mkb.source-descriptor.v1",
    "source_kind": "http_resource",
    "canonical_uri": "https://example.invalid/resource",
    "http_profile_ref": "http-static-default-v1",
    "expected_media_types": ["text/html"],
    "validator_policy_ref": "http-validator-default-v1",
    "secret_slot_bindings": {},
    "payload_extra": {}
  },
  "clean_profile_ref": "clean-web-default-v1",
  "canonical_metadata": {
    "context": {},
    "filters": {}
  },
  "external_resource_uuid": null
}
~~~

四个variant由source_kind discriminator严格校验，unknown field拒绝。inline public variant允许content，但进入Task transaction前必须转换为：

~~~json
{
  "schema_version": "mkb.normalized-source-descriptor.v1",
  "source_kind": "inline_payload",
  "representation_ref": "logical-object-ref",
  "content_digest": "64-lowercase-hex",
  "size_bytes": 123,
  "declared_media_type": "text/plain",
  "declared_charset": "utf-8",
  "payload_extra": {}
}
~~~

normalized descriptor与其digest进入Task fingerprint；public原始body在请求生命周期结束后不可被Task/runtime重读。

#### 5.2.2 Metadata payload

canonical_metadata固定为context和filters两个object，均由resolved SourceKindDefinition绑定的exact JSON Schema校验。unknown metadata key是否允许只由该schema决定；schema没有声明的字段不得落入payload_extra规避验证。

### 5.3 十张 canonical Intake truth tables

#### 5.3.1 intake_sources

| Column group | Exact columns |
|---|---|
| Identity | team_uuid, intake_source_uuid PK |
| Definition | source_kind, source_kind_definition_version, source_kind_definition_digest |
| Stable binding | external_resource_uuid nullable, source_identity_digest, source_descriptor_ref, source_descriptor_digest |
| Runtime config refs | connector_config_ref nullable, connector_config_digest nullable, secret_binding_ref nullable, secret_binding_digest nullable |
| Admission | accepts_new_snapshots boolean |
| CAS/time | row_revision, created_at, updated_at |
| Extension | payload_extra |

Constraints：

~~~text
UNIQUE(team_uuid, source_identity_digest)
UNIQUE(team_uuid, source_kind, external_resource_uuid) WHERE external_resource_uuid IS NOT NULL
source_kind IN fixed four values
row_revision >= 1
secret/config/descriptor refs are logical; no plaintext/path
~~~

同external_resource_uuid异identity/definition digest冲突。accepts_new_snapshots只是admission fence，不是Source lifecycle；修改只能由source owner CAS并写intake_source_transitions。

#### 5.3.2 intake_snapshots

| Column group | Exact columns |
|---|---|
| Identity/owner | team_uuid, intake_snapshot_uuid PK, intake_source_uuid |
| Observation fence | observation_key, observation_fingerprint, candidate_root_digest |
| Collection | completeness, authoritative_scope_ref nullable, authoritative_scope_digest nullable, exhaustion_proof_ref nullable, exhaustion_proof_digest nullable |
| Evidence | source_validator_evidence_ref/digest, preflight_outcome_uuid/digest, s05_binding_digest |
| Producer | producer_task_uuid, producer_execution_uuid, producer_fence_digest |
| Artifacts | raw_artifact_uuid nullable |
| Time | observed_at, accepted_at |
| Extension | payload_extra |

Snapshot immutable；completeness只允许complete/partial，failure不建row。

~~~text
UNIQUE(team_uuid, intake_source_uuid, observation_key)
UNIQUE(team_uuid, intake_source_uuid, observation_fingerprint, candidate_root_digest)
complete authoritative absence requires scope + exhaustion proof
preflight/candidate/binding/fence digests must agree
~~~

#### 5.3.3 intake_items

| Column group | Exact columns |
|---|---|
| Identity/owner | team_uuid, intake_item_uuid PK, intake_source_uuid |
| Stable key | normalized_external_key, external_key_normalizer_key/version/digest |
| Lifecycle | lifecycle_state |
| Selection | latest_revision_uuid nullable, serving_revision_uuid nullable |
| CAS/time | row_revision, created_at, updated_at, deactivated_at nullable, deleted_at nullable |
| Extension | payload_extra |

~~~text
UNIQUE(team_uuid, intake_source_uuid, normalized_external_key)
lifecycle_state IN active/deactivated/deleted
deactivated/deleted => serving_revision_uuid IS NULL
latest/serving FK target same team+item
deleted key is permanently reserved in v1
~~~

#### 5.3.4 intake_revisions

| Column group | Exact columns |
|---|---|
| Identity/owner | team_uuid, intake_revision_uuid PK, intake_item_uuid |
| Chain | revision_ordinal, predecessor_revision_uuid nullable |
| Semantics | revision_fingerprint, fingerprint_recipe_version |
| Creation | creation_action_key/version, source_snapshot_uuid, producer_execution_uuid |
| Time/extension | created_at, payload_extra |

Revision immutable。

~~~text
UNIQUE(team_uuid, intake_item_uuid, revision_ordinal)
UNIQUE(team_uuid, intake_item_uuid, revision_fingerprint)
ordinal starts 1 and predecessor is null only for 1
ordinal n predecessor must be same item ordinal n-1
~~~

#### 5.3.5 intake_artifacts

| Column group | Exact columns |
|---|---|
| Identity | team_uuid, intake_artifact_uuid PK |
| Direct owner | owner_snapshot_uuid nullable, owner_revision_uuid nullable |
| Role/type | artifact_role, media_type, schema_ref nullable, schema_digest nullable |
| Integrity | digest_algorithm, content_digest, size_bytes |
| Storage | logical_locator, retention_class_ref |
| Producer | producer_execution_uuid nullable, producer_process_uuid nullable, producer_fence_digest nullable |
| Time/extension | created_at, payload_extra |

owner_snapshot_uuid XOR owner_revision_uuid必须恰一非空。artifact_role固定为raw_representation、source_envelope、member_payload、canonical_content、decoded_page、clean_derived、ocr_output、vision_output。Artifact immutable；logical_locator不能是绝对路径。Block、Vector、Process log不是IntakeArtifact。

#### 5.3.6 intake_snapshot_memberships

| Column group | Exact columns |
|---|---|
| Identity | team_uuid, intake_snapshot_uuid, member_ordinal |
| Member key | normalized_external_key, candidate_member_uuid nullable |
| Canonical refs | intake_item_uuid, observed_revision_uuid nullable |
| Absence basis | absence_basis_revision_uuid nullable |
| Decision | decision_kind, required boolean, decision_digest |
| Evidence/time | decision_evidence_ref/digest, created_at, payload_extra |

~~~text
PK(team_uuid, intake_snapshot_uuid, member_ordinal)
UNIQUE(team_uuid, intake_snapshot_uuid, normalized_external_key)
decision_kind IN seen_new_revision/seen_no_change/absent_deactivated/absent_no_change
seen_* => observed_revision_uuid NOT NULL and candidate_member_uuid NOT NULL
absent_* => observed_revision_uuid IS NULL and candidate_member_uuid IS NULL and required=false
absent_* only when Snapshot complete + authoritative
~~~

Membership immutable，是collection SSOT。TaskItem、child count或JSON relation不得替代。

#### 5.3.7 intake_semantic_definitions

| Exact columns | Constraints |
|---|---|
| semantic_key, definition_version | composite PK |
| value_kind, schema_ref nullable, schema_version nullable, schema_digest nullable | typed scalar/json/artifact contract |
| fingerprint_participation, route_fact_key nullable | formal semantics |
| canonicalizer_ref/version/digest | exact recipe |
| definition_digest, registered_at, registration_origin | same version same digest idempotent |
| payload_extra | immutable |

Registry只由code/migration/bootstrap写；外部CUD不存在。初始四个definition按§4.5.3注册。

#### 5.3.8 intake_revision_semantics

| Column group | Exact columns |
|---|---|
| Identity | team_uuid, intake_revision_uuid, semantic_key |
| Definition | definition_version, definition_digest, value_kind |
| Digest | value_digest |
| Typed value | value_text nullable, value_integer nullable, value_real nullable, value_boolean nullable, value_json nullable, value_artifact_uuid nullable |
| Time/extension | created_at, payload_extra |

PK为team+revision+semantic_key；exact definition FK。按value_kind恰一个typed value列非空；value_artifact_uuid必须属于同Revision。历史读取按绑定version解释，不join current registry重解释。

#### 5.3.9 intake_action_definitions

| Exact columns | Constraints |
|---|---|
| action_key, definition_version | composite PK |
| allowed_from_mask, required_proof_kind nullable, precondition_class | exact guard |
| core_effect_mask, route_fact_key, idempotency_scope | effect只能来自封闭CoreEffect集合 |
| definition_digest, registered_at, registration_origin | immutable/idempotent |
| payload_extra | immutable |

首版注册create_item、accept_revision、publish_revision、deactivate、reactivate、delete、absence_deactivate；其中后六项是baseline registry minimum，create_item负责把D02 create→active边与首Revision ledger化。CoreEffect只允许ACCEPT_LATEST、SET_SERVING、CLEAR_SERVING、SET_ACTIVE、SET_DEACTIVATED、SET_DELETED、NO_CHANGE。publish_revision允许before/after serving Revision相同，仅用于ES-07 proof-valid same-Revision reindex；此时必须有different IndexGeneration proof、Item row revision +1和active index pointer transition，不能作为无效果touch。

#### 5.3.10 intake_item_transitions

| Column group | Exact columns |
|---|---|
| Identity/owner | team_uuid, transition_uuid PK, intake_item_uuid |
| Action | action_key, action_definition_version/digest |
| Before | before_lifecycle nullable仅create_item, before_latest_revision_uuid nullable, before_serving_revision_uuid nullable, item_revision_before |
| After | after_lifecycle, after_latest_revision_uuid nullable, after_serving_revision_uuid nullable, item_revision_after |
| Causation | task_uuid, execution_uuid, process_uuid nullable, command_uuid nullable |
| Guard/proof | proof_ref/digest nullable, policy_ref/version/digest nullable, transition_fence |
| Time/extension | occurred_at, payload_extra |

append-only，与Item insert/CAS同事务；item_revision_after=item_revision_before+1。create_item固定before_lifecycle=null、before pointers=null、item_revision_before=0；其他action的before_lifecycle必填。before/after必须符合exact ActionDefinition/CoreEffect。publish_revision的same serving值只在proof声明reindex且ES-07 pointer before/after generation不同、target Revision相同、双transition同UoW时合法。UNIQUE(team_uuid,intake_item_uuid,transition_fence)保证重放幂等。

### 5.4 Source、evidence 与 staging tables

#### 5.4.1 intake_source_kind_definitions

Exact columns：

~~~text
source_kind_key, definition_version PK
definition_digest, registry_status
descriptor_schema_ref/digest, normalized_descriptor_schema_ref/digest
config_schema_ref/digest
cardinality, scope_profile_ref/digest, completeness_profile_ref/digest
allowed_capability_set_ref/digest
media_encoding_profile_ref/digest, budget_profile_ref/digest
external_key_normalizer_key/version/digest
singleton_key_tuple_ref/digest nullable, duplicate_policy
context_schema_ref/digest, filter_schema_ref/digest
secret_slot_schema_ref/digest, egress_policy_ref/digest
preflight_profile_ref/digest, allowlist_eligible
registered_at, registration_origin, payload_extra
~~~

registry_status=enabled/disabled/deprecated是governance fact，不是StateFamily。Key只允许四种source kind；同key/version异digest fail-loud。

#### 5.4.2 intake_execution_bindings

~~~text
team_uuid, execution_uuid PK
intake_source_uuid, source_kind_key/version/digest
normalized_descriptor_ref/digest
acquisition_capability_key/version/digest
decode_capability_key/version/digest nullable
clean_capability_set_ref/digest
external_key_normalizer_key/version/digest
canonicalizer_set_ref/digest
preflight_profile_ref/digest
allowlist_binding_key/version/digest nullable
validator_key/version/implementation_digest
check_set_key/version/digest
model_prompt_binding_ref/digest nullable
s05_binding_digest
bound_at, payload_extra
~~~

immutable；execution/team/source一致。一个Execution恰一个binding；reclean仍使用该binding允许的有限capability set。

#### 5.4.3 intake_acquisition_evidence

| Column group | Exact columns |
|---|---|
| Identity/fence | team_uuid, acquisition_evidence_uuid PK, task_uuid, execution_uuid, process_uuid, fencing_generation |
| Binding | source_uuid, source_kind/version/digest, capability_key/version/digest |
| Request | sanitized_request_profile_digest, process_retry_ordinal, started_at, completed_at |
| Representation | logical_handle nullable, raw_digest nullable, size_bytes nullable, declared/detected/verified_media nullable |
| Encoding | encoding_label/BOM/detector/profile nullable, decoder_error_count, replacement_count |
| HTTP/API | response_status nullable, final_uri_evidence_ref/digest nullable, redirect_chain_digest nullable, validator_ref nullable, page_cursor_evidence_ref/digest nullable |
| Budget | consumed/compressed/decompressed bytes, redirect/page/time usage, budget_profile_ref/digest, budget_verdict |
| Result | result_kind, result_code, retryability, evidence_digest |
| Extension | payload_extra |

result_kind只允许succeeded/rejected/failed。Succeeded必须有readable handle/digest/size与verified media；failed不得带complete/empty success proof。UNIQUE(process_uuid,fencing_generation,evidence_digest)用于Outcome重放。process_retry_ordinal只是ES-02 Process retry_count快照，不是Attempt identity或新状态。

#### 5.4.4 intake_clean_artifact_candidates

~~~text
team_uuid, clean_candidate_uuid PK
candidate_set_uuid, candidate_member_uuid nullable
input_artifact_ref/digest, output_logical_handle, output_media_type
output_digest_algorithm, output_content_digest, output_size_bytes
clean_capability_key/version/digest, clean_profile_ref/digest
parser_ref/version/digest nullable
model_ref/version/digest nullable, prompt_ref/version/digest nullable
generation_invocation_ref/digest nullable
producer_execution_uuid, producer_process_uuid, producer_fence_digest
language/page/segment counts, anchor_manifest_ref/digest
loss_flags_ref/digest, quality_signals_ref/digest, quality_verdict
lineage_ref/digest, remediation_ordinal
created_at, payload_extra
~~~

immutable。remediation_ordinal为0或1，不是Attempt identity；它只区分初始clean和一次bounded gate reclean。

#### 5.4.5 intake_candidate_sets

~~~text
team_uuid, candidate_set_uuid PK
intake_source_uuid, producer_task_uuid, producer_execution_uuid, producer_fence_digest
source_definition_key/version/digest, capability_set_digest, s05_binding_digest
observation_key, observation_fingerprint
scope_ref/digest, authoritative_scope_ref/digest nullable
completeness
expected_page_count, expected_member_count, expected_bytes
observed_member_count, accepted_member_count, rejected_member_count, duplicate_member_count
root_digest nullable
preflight_outcome_uuid/digest nullable
staging_status, row_revision
opened_at, sealed_at nullable, accepted_at nullable, abandoned_at nullable
abandon_reason_code nullable, expires_at
accepted_snapshot_uuid nullable, accepted_change_set_uuid nullable
payload_extra
~~~

status只允许open/sealed/accepted/abandoned并按§4.7.1。UNIQUE(team,source,observation_key,producer_execution_uuid)；accepted必须有Snapshot/ChangeSet，abandoned不得有。

#### 5.4.6 intake_candidate_pages

~~~text
team_uuid, candidate_set_uuid, page_ordinal PK
first_member_ordinal, last_member_ordinal, member_count, byte_count
ordered_member_digest_ref, page_digest
source_page_evidence_ref/digest
staged_payload_ref/digest
producer_execution_uuid, producer_fence_digest
created_at, payload_extra
~~~

Page append-only。相同candidate+ordinal+digest重放幂等，异digest冲突并使open candidate只能abandon。

#### 5.4.7 intake_candidate_members

~~~text
team_uuid, candidate_member_uuid PK
candidate_set_uuid, page_ordinal, member_ordinal
raw_external_key_evidence_ref/digest
normalized_external_key, normalizer_key/version/digest
required
source_raw_digest, source_canonical_digest
member_digest
clean_candidate_uuid nullable
validation_verdict, rejection_evidence_ref/digest nullable
created_at, payload_extra
~~~

UNIQUE(candidate_set_uuid,member_ordinal)与UNIQUE(candidate_set_uuid,normalized_external_key)。Member immutable；validation_verdict=accepted/rejected，不是StateFamily。

#### 5.4.8 intake_candidate_semantics

~~~text
team_uuid, candidate_member_uuid, semantic_key PK
definition_version, definition_digest, value_kind, value_digest
typed value columns equal to intake_revision_semantics
created_at, payload_extra
~~~

只有acceptance transaction可将validated candidate semantic复制/引用为immutable RevisionSemantic；definition drift拒绝。

#### 5.4.9 intake_candidate_artifact_refs

~~~text
team_uuid, candidate_member_uuid, artifact_role, artifact_ordinal PK
staged_logical_handle, media_type, schema_ref/digest nullable
digest_algorithm, content_digest, size_bytes
producer_evidence_ref/digest, retention_class_ref
created_at, payload_extra
~~~

Artifact role必须属于§5.3.5集合。Acceptance只提升required且可读、digest一致的staged refs；未提升对象进入orphan policy。

#### 5.4.10 intake_candidate_anomalies

~~~text
team_uuid, anomaly_uuid PK
candidate_set_uuid, candidate_member_uuid nullable, page_ordinal nullable
anomaly_kind, required, scope_kind, typed_code
evidence_ref/digest
created_at, payload_extra
~~~

anomaly_kind只允许§4.6.2九值。Rows immutable；complete seal要求required anomaly count=0。

### 5.5 Preflight 与 Gate tables

#### 5.5.1 preflight_validator_manifests

~~~text
validator_key, validator_version PK
handler_key, applicability_schema_ref/digest
input_schema_ref/digest, output_schema_ref/digest
ordered_check_set_ref, check_set_key/version/digest
implementation_digest, manifest_digest
registry_status, registered_at, payload_extra
~~~

Code-owned immutable registry；无外部CUD、script、agent rule或dynamic loader。

#### 5.5.2 preflight_allowlist_bindings

~~~text
binding_key, binding_version PK
selector_schema_ref/digest, selector_value_digest
source_kind_key/version, acquisition_capability_key/version
clean_profile_ref/digest
validator_key/version/implementation_digest
check_set_key/version/digest
override_policy_ref/version/digest
registry_status, definition_digest
registered_at, registered_by_origin, payload_extra
~~~

registry_status为enabled/disabled/deprecated governance fact。Enabled binding必须引用exact enabled validator/check-set；缺失时readiness false，不fallback。

#### 5.5.3 preflight_outcomes

~~~text
team_uuid, preflight_outcome_uuid PK
task_uuid, execution_uuid, generation, execution_fence_digest
scope_kind, candidate_set_uuid, candidate_root_digest, s05_binding_digest
intake_item_uuid nullable, intake_revision_uuid nullable
clean_artifact_uuid nullable, clean_artifact_digest nullable
allowlist_binding_key/version/digest nullable
validator_key/version/implementation_digest
check_set_key/version/digest
result_kind
outcome_digest
created_at, payload_extra
~~~

scope_kind只允许root_candidate/accepted_item；root_candidate不得带Item/Revision且seal只接受该scope，accepted_item必须带exact Item/Revision/CleanArtifact。result_kind只允许passed/blocked；immutable。UNIQUE(execution_uuid,scope_kind,candidate_root_digest,check_set_digest,clean_artifact_digest)。同一input fence同Outcome幂等、不同result/digest为validator integrity conflict。Runtime/schema/evidence error不写row。

#### 5.5.4 preflight_check_evidence

~~~text
team_uuid, preflight_outcome_uuid, check_ordinal PK
check_key, check_version, check_digest
required, verdict, typed_code
target_ref/digest, evidence_ref/digest
created_at, payload_extra
~~~

verdict=passed/blocked；ordered evidence digest必须等于Outcome的输入。无mutable “fix”字段。

#### 5.5.5 execution_review_targets

~~~text
team_uuid, review_target_uuid PK
task_uuid, execution_uuid, generation, execution_fence_digest
workflow_revision_uuid, workflow_compiled_digest, s05_binding_digest
gate_kind
intake_source_uuid, candidate_set_uuid nullable, intake_snapshot_uuid nullable
intake_item_uuid nullable, intake_revision_uuid nullable
clean_artifact_uuid, clean_artifact_digest
preflight_outcome_uuid, preflight_outcome_digest, check_set_digest
allowed_actions_mask, override_policy_ref/digest nullable
remediation_ordinal
target_digest
created_at, payload_extra
~~~

Target immutable；所有ref同team/generation/fence。target_digest覆盖全部字段。Public detail仅返回安全摘要、opaque Gate UUID、revision、target digest和allowed actions，不返回Execution/Process/fence/secret/path。

#### 5.5.6 execution_gates

~~~text
team_uuid, gate_uuid PK
task_uuid, execution_uuid, generation
gate_kind, status, gate_revision
expected_execution_revision, execution_fence_digest
review_target_uuid, review_target_digest
opened_at, terminal_at nullable
terminal_decision_uuid nullable, terminal_resolution_ref/digest nullable
causation_uuid, correlation_uuid
payload_extra
~~~

status=open/released/rejected/superseded；open→terminal only。UNIQUE(execution_uuid,gate_kind,review_target_digest)防重复。released/rejected必须有Decision；superseded必须有reclean Decision或system terminal_resolution evidence；open两者均不得有。

#### 5.5.7 execution_gate_decisions

~~~text
team_uuid, decision_uuid PK
gate_uuid, idempotency_key
expected_gate_revision, decision_action
actor_ref, authority_ref, authority_evidence_digest
review_target_digest
reason, evidence_ref/digest nullable
decision_fingerprint
causation_uuid, correlation_uuid
created_at, payload_extra
~~~

decision_action=approve/approve_override/reject/reclean。UNIQUE(team_uuid,gate_uuid,idempotency_key)；同fingerprint重放返回原结果，异fingerprint冲突。Decision append-only。

### 5.6 ChangeSet、source audit、scheduling、repair 与 cleanup

#### 5.6.1 intake_change_sets

~~~text
team_uuid, change_set_uuid PK
intake_snapshot_uuid UNIQUE, candidate_set_uuid UNIQUE
producer_execution_uuid, workflow_revision_uuid, s05_binding_digest
required_fact_count, optional_fact_count, seen_count, absence_count
change_set_digest
created_at, payload_extra
~~~

#### 5.6.2 intake_change_facts

~~~text
team_uuid, change_set_uuid, fact_ordinal PK
fact_kind
intake_source_uuid, intake_snapshot_uuid
intake_item_uuid nullable, intake_revision_uuid nullable
membership_ordinal nullable
semantic_definition_set_digest nullable
required, route_fact_key, fact_digest
created_at, payload_extra
~~~

fact_kind固定为new_item_revision、new_revision、no_change、reactivated、absence_deactivated、absence_no_change。不得存Process key；ES-02 WorkflowRevision根据typed route fact决定后续。

#### 5.6.3 intake_source_transitions

~~~text
team_uuid, source_transition_uuid PK
intake_source_uuid
before_accepts_new_snapshots, after_accepts_new_snapshots
source_revision_before, source_revision_after
reason_code, causation_uuid, policy_ref/digest
transition_fence
occurred_at, payload_extra
~~~

append-only且与Source CAS同事务。它只审计admission fence，不创造Source lifecycle。

#### 5.6.4 intake_scheduling_intents

~~~text
team_uuid, scheduling_intent_uuid PK
task_uuid, root_execution_uuid, workflow_revision_uuid
intake_snapshot_uuid, change_set_uuid, change_set_digest
intake_item_uuid nullable, intake_revision_uuid nullable
required, materialization_key
message_type, message_schema_version
idempotency_fence
created_at, delivered_at nullable, delivery_count
payload_extra
~~~

UNIQUE(root_execution_uuid,materialization_key)。ES-04可将其与generic outbox同物理表实现，但必须保留typed列、business uniqueness和ChangeSet FK；delivery projection不是业务success。

#### 5.6.5 intake_repair_intents

~~~text
team_uuid, repair_intent_uuid PK
invariant_kind, target_kind, target_ref/digest
observed_fence_digest, allowed_repair_kind
causation_uuid, requested_at
resolved_at nullable, resolution_evidence_ref/digest nullable
payload_extra
~~~

allowed_repair_kind只允许projection_rebuild、outbox_replay、pointer_ledger_repair、artifact_reference_recheck。不得创建从未提交的Snapshot/Revision/proof；resolved_at是monotonic completion fact，不是StateFamily。

#### 5.6.6 intake_cleanup_intents

~~~text
team_uuid, cleanup_intent_uuid PK
target_kind, target_ref/digest
retention_policy_ref/version/digest
required_substrate_set_ref/digest
hold_reference_snapshot_ref/digest
requested_task_uuid, requested_execution_uuid, requested_process_uuid
required_proof_count, verified_proof_count
completion_digest nullable, completed_at nullable
created_at, payload_extra
~~~

#### 5.6.7 intake_cleanup_proofs

~~~text
team_uuid, cleanup_intent_uuid, substrate_kind, target_ref PK
target_digest, proof_kind, proof_ref/digest
producer_execution_uuid, producer_process_uuid
verified_at, payload_extra
~~~

substrate_kind固定为relationship、intake_artifact、derived_artifact、vector_record、index_generation、staging_object。Intent只有全部required proof验证后才写completion；partial failure继续retry且不恢复serving。Tombstone、transition、Task/Audit/Restart/lineage不在普通purge集合。

### 5.7 Typed wire contracts

#### 5.7.1 CandidateSetSeal

mkb.candidate-set-seal.v1至少包含candidate/team/source/execution fence、expected page/member/byte counts、ordered page digests、root digest、completeness/scope/exhaustion proof、preflight outcome ref/digest、s05 binding digest与seal proof digest。

#### 5.7.2 IntakeAcceptanceResult

~~~json
{
  "schema_version": "mkb.intake-acceptance-result.v1",
  "candidate_set_uuid": "UUID",
  "intake_snapshot_uuid": "UUID",
  "change_set_uuid": "UUID",
  "change_set_digest": "sha256",
  "counts": {
    "seen_new_revision": 1,
    "seen_no_change": 0,
    "absent_deactivated": 0,
    "absent_no_change": 0,
    "required_children": 1
  },
  "accepted_refs": [],
  "acceptance_proof_ref": "logical-ref",
  "acceptance_proof_digest": "sha256",
  "payload_extra": {}
}
~~~

accepted_refs是bounded typed ref summary；完整成员经ChangeSet分页读取，不能把large scatter塞入ProcessOutcome。

#### 5.7.3 MetadataApplyResult

mkb.metadata-apply-result.v1固定result_kind=no_change/filter_change/semantic_revision，包含Item、before/after row revision、before/after latest Revision、new Revision/semantic digest nullable、route facts和proof。它不包含next Process。

#### 5.7.4 Publication command/result

mkb.intake-publication-command.v1包含team/item/revision、expected lifecycle/item row revision/latest/serving、expected active index generation/pointer revision、canonical PublicationCandidate/validation material及digest、derived/index generation exact refs、publish mode、policy binding和causation。Candidate不是已经持久化的final proof。Result包含final PublicationProof ref/digest、Item transition ref/digest、active index pointer transition ref/digest、new serving Revision、new index generation、两个after revisions和eligibility fence digest。

publish mode只允许valid_and_serving或validated_not_served。前者要求active Item、target Revision=expected latest、双pointer/transition同UoW；后者只允许deactivated Item rebuild并保持serving/index pointers null。Deleted永远拒绝。Same-Revision reindex要求expected serving=target Revision、before/after index generation不同且Item/active-pointer revisions均+1。

#### 5.7.5 Public Gate decision

~~~json
{
  "schema_version": "mkb.gate-decision.v1",
  "decision_uuid": "UUIDv4-or-v7",
  "idempotency_key": "1..200 chars",
  "expected_gate_revision": 1,
  "target_digest": "64-lowercase-hex",
  "action": "approve",
  "reason": "1..2000 chars",
  "actor_evidence": {
    "actor_ref": "opaque-ref",
    "authority_ref": "opaque-ref",
    "evidence_digest": "64-lowercase-hex"
  },
  "payload_extra": {}
}
~~~

ES-08 authority port验证actor/authority；ES-03不建设user/role表。action必须存在于ReviewTarget.allowed_actions。

### 5.8 Application ports

~~~python
class IntakeExecutionBindingPort(Protocol):
    async def bind_ingest(self, command: BindIngestExecutionV1) -> IntakeExecutionBindingV1: ...
    async def load_exact(self, execution_uuid: UUID, expected_digest: Digest) -> IntakeExecutionBindingV1: ...

class SourceDefinitionResolverPort(Protocol):
    async def resolve(self, query: SourceDefinitionQueryV1) -> SourceKindDefinitionV1: ...

class IntakeSourceOwnerPort(Protocol):
    async def resolve_or_create(self, command: ResolveSourceV1) -> IntakeSourceV1: ...
    async def set_admission(self, command: SetSourceAdmissionV1) -> IntakeSourceV1: ...

class CandidateSetStagingPort(Protocol):
    async def open(self, command: OpenCandidateSetV1) -> CandidateSetV1: ...
    async def append_page(self, command: AppendCandidatePageV1) -> CandidateSetV1: ...
    async def seal(self, command: SealCandidateSetV1) -> CandidateSetSealV1: ...
    async def abandon(self, command: AbandonCandidateSetV1) -> CandidateSetV1: ...

class PreflightValidationPort(Protocol):
    async def validate(self, command: ValidatePreflightV1) -> PreflightOutcomeV1: ...

class IntakeAcceptancePort(Protocol):
    async def accept(self, command: AcceptCandidateSetV1) -> IntakeAcceptanceResultV1: ...

class IntakeReadPort(Protocol):
    async def get_source(self, key: SourceKey) -> IntakeSourceView: ...
    async def get_snapshot(self, key: SnapshotKey) -> IntakeSnapshotView: ...
    async def get_item(self, key: ItemKey) -> IntakeItemView: ...
    async def get_revision(self, key: RevisionKey) -> IntakeRevisionView: ...
    async def list_memberships(self, query: MembershipQueryV1) -> CursorPage[MembershipView]: ...

class IntakeTransitionOwnerPort(Protocol):
    async def apply_metadata(self, command: ApplyMetadataV1) -> MetadataApplyResultV1: ...
    async def transition(self, command: IntakeTransitionCommandV1) -> IntakeTransitionResultV1: ...
    async def cas_serving_with_index(self, command: AtomicPublicationCommandV1, uow: UnitOfWork) -> PublicationResultV1: ...

class IntakeEligibilityPort(Protocol):
    async def verify_serving(self, query: ServingEligibilityQueryV1) -> ServingEligibilityProofV1: ...

class ExecutionGateOwnerPort(Protocol):
    async def open(self, command: OpenExecutionGateV1) -> GateViewV1: ...
    async def decide(self, command: DecideExecutionGateV1) -> GateDecisionResultV1: ...

class ExecutionGateControlPort(Protocol):
    async def enter_wait(self, command: EnterHumanWaitV1, uow: UnitOfWork) -> ExecutionControlView: ...
    async def apply_decision(self, fact: GateDecisionFactV1, uow: UnitOfWork) -> ExecutionControlView: ...

class IntakeCleanupPort(Protocol):
    async def plan(self, command: PlanCleanupV1) -> CleanupIntentV1: ...
    async def submit_proof(self, proof: CleanupProofV1) -> CleanupAggregateV1: ...

class LogicalObjectPort(Protocol): ...       # ES-04
class ProcessCapabilityRegistryPort(Protocol): ...  # ES-05
class ModelInvocationPort(Protocol): ...     # ES-05
class PublicationProofReaderPort(Protocol): ...     # ES-07
class SecretPolicyPort(Protocol): ...        # ES-08
class ReviewAuthorityPort(Protocol): ...     # ES-08
class UnitOfWorkPort(Protocol): ...          # ES-04
~~~

只有owner service获得对应repository mutation。Leaf capability、HTTP facade、ES-02 Engine、ES-07 publisher均只能调用port，不得取得裸status/pointer update。

所有HTTP/API acquisition只可调用ES-08-v1.0的`SafeEgressTransportPort`；browser acquisition只可调用其`BrowserSandboxPort`，且browser内部网络仍受同一safe-egress policy。Credential/allowlist通过`SecretPolicyPort`解析，resource slot通过`AdmissionPort`获取；ES-03不得持有raw HTTP client、socket、proxy、browser launch、secret path/value或自行实现第二套limiter。

### 5.9 Internal durable protocols

所有消息使用mkb.internal-message.v1 envelope并继承ES-01/02的message UUID、team/task/trace、causation/correlation、schema version与payload_extra规则。

| Message/event | Producer→consumer | Required typed payload | Idempotency / guard |
|---|---|---|---|
| intake.source-bound.v1 | ES-03→ES-02 | Execution、Source、binding ref/digest | one binding per Execution |
| intake.candidate-sealed.v1 | ES-03→ES-02 | candidate/root/preflight/binding/fence | candidate CAS+root digest |
| intake.snapshot-accepted.v1 | ES-03→ES-02 | Snapshot/ChangeSet/proof/counts | candidate accepted Snapshot unique |
| intake.child-materialize-requested.v1 | ES-03→ES-02 | ChangeFact Item/Revision/required/materialization key | ChangeSet fact uniqueness |
| intake.item-transitioned.v1 | ES-03→ES-02/07 | action、before/after pointers/lifecycle、transition digest | transition fence |
| intake.serving-changed.v1 | ES-03/07 atomic UoW→read projections | exact old/new serving、old/new index generation、PublicationProof、eligibility digest | Item row revision + index pointer revision |
| gate.opened.v1 | ES-03→ES-02/01 | Gate opaque ref、target digest、expected Execution revision | unique target per Execution |
| gate.resolved.v1 | ES-03→ES-02/01 | terminal status、decision action/digest、route fact | Gate revision+Decision idempotency |
| intake.cleanup-requested.v1 | ES-03→ES-04/06/07/08 | target、required substrates、policy/hold digest | cleanup intent UUID+target |
| intake.cleanup-proofed.v1 | substrate owner→ES-03 | intent/substrate/target/proof digest | composite proof key |
| intake.repair-requested.v1 | ES-08 scanner→ES-03 | invariant/target/fence/allowed repair | repair intent uniqueness |
| intake.artifact-orphaned.v1 | ES-03/04→ES-04 | staging handle/digest/owner reservation/grace | object digest+reservation |

消息不携带正文、bytes、absolute path、secret、full Workflow、raw ProcessCommand或unbounded member list。At-least-once delivery只负责wake-up；consumer总是重读owner truth并验证fence。

---

## 6. State / Consistency / Failure

### 6.1 核心不变量

1. v1恰有四类source、五类canonical Intake identity和三个由本文件执行的StateFamily；不得出现别名或组合状态；
2. Snapshot只在acceptance transaction成功后存在；不存在failed/pending/draft Snapshot；
3. Candidate sealed不等于Snapshot accepted，Snapshot accepted不等于RAG admitted，Revision latest不等于serving；
4. 只有source-grounded、fingerprint-participating semantics变化才创建Revision；
5. raw representation、canonical semantics、clean-derived output与vector/index generation各有owner/ref，不可互换；
6. 每个Item key在Source namespace中永久唯一；deleted key不复用；
7. deactivated/deleted的serving永远为null；publish只允许active且proof-valid；
8. complete-authoritative才可产生absence；partial和错误永不全量下架；
9. allowlist永不绕过preflight；runtime/schema/evidence错误永不变成blocked；
10. auto-admit不建Gate；human wait无Process lease；Gate decision不写Intake状态；
11. retry/recovery/reclean不热切Workflow或S05 binding，不原位覆盖evidence/artifact/history；
12. queue/log/object existence/payload_extra均无合成truth或transition权。

State/fact lint必须拒绝以下列值或同义alias：snapshot_failed、revision_pending、item_reviewing、artifact_ready、candidate_processing、gate_approved、deleted_purging、clean_retrying。查询可以并列展示各轴，不得拼成新status。

### 6.2 Concurrency 与 CAS

| Race | Winner rule | Loser behavior |
|---|---|---|
| 同Source identity并发resolve | unique source_identity_digest | 读取winner；descriptor drift则conflict |
| page append vs seal | Candidate row revision + status CAS | sealed后append冲突，不回open |
| 同observation acceptance | source observation unique + root digest | 同digest返回同Snapshot，异digest隔离 |
| concurrent revision acceptance | Item row revision + predecessor/ordinal unique | reload；同fingerprint no-change，异fingerprint按observation顺序重试或冲突 |
| publish vs new latest | expected Item/latest/serving CAS | stale proof拒绝，旧serving不变 |
| deactivate/delete vs publish | first committed Item CAS wins | loser读取current state并fail-safe |
| absence vs seen acceptance | authoritative observation serialization per Source | 不允许两个并行Snapshot以不确定顺序下架/复活 |
| Gate double decision | gate revision + idempotency fingerprint | 同内容幂等，异内容409 |
| Gate decision vs cancel | ES-02 Execution owner first-commit-wins | stale decision拒绝；不能复活cancelling/terminal |
| cleanup vs new reference/hold | reference snapshot digest + proof recheck | fence变化使proof失效并重算eligibility |

每个IntakeSource的canonical acceptance按observation order key线性化。并行acquisition/clean允许，但acceptance不得根据完成速度重排同Source observation。

### 6.3 Failure disposition

| Failure class | Process retryability | Candidate/Intake effect | Public-safe code family |
|---|---|---|---|
| network timeout/429/5xx | retryable per manifest | 无Snapshot；staging可复用exact evidence fence | acquisition-transient |
| auth/policy deny | non_retryable，或等待上游修复后新Task | 无Snapshot/Gate | acquisition-denied |
| unsupported/corrupt media | non_retryable | anomaly/evidence；不得伪complete | media-invalid |
| decoder/OCR local resource crash | retryable if side-effect safe | old evidence immutable；new claim/fence | clean-transient |
| model provider transient | ES-05 policy | invocation留证；无fake CleanArtifact | inference-transient |
| ExternalKey missing/drift | non_retryable | seal拒绝/abandon；无Item | external-key-invalid |
| page/count/root mismatch | non_retryable integrity | abandon/quarantine；无Snapshot | candidate-integrity |
| preflight blocked | business outcome，不是runtime failure | 可auto fail或human Gate | preflight-blocked |
| preflight handler/schema/read error | retryable或non_retryable | 不写Outcome/Gate | preflight-runtime |
| acceptance conflict | non_retryable integrity | winner truth保留；无parallel Snapshot | intake-observation-conflict |
| publication proof stale/invalid | non_retryable当前command | old serving保留 | intake-publication-proof-invalid |
| lifecycle CAS stale | non_retryable command conflict | current Item不变 | intake-transition-conflict |
| Gate stale/authority deny | non_retryable command | Gate/Execution不变；留audit | gate-decision-conflict |
| canonical Artifact missing | fail-closed | repair intent；禁止virtual Artifact | intake-artifact-missing |
| retention/hold fence | retryable cleanup later | 不删substrate | intake-retention-fenced |

Structured error必须含typed code、retryability、safe target ref、causation/request ID与current revision/fence摘要；不得含secret、raw URL credential、body、absolute path、SQL、stack、driver或跨team存在性。

### 6.4 Deterministic recovery

| Durable observation | 唯一合法恢复 |
|---|---|
| inline/object staged但Task未commit | ES-04按reservation/digest/grace清orphan |
| Execution created但S05 binding缺失 | 重跑exact bind UoW；不得materialize未绑定Process |
| Acquisition evidence存在但Process Outcome未接受 | current fence校验后重交同Outcome；stale fence拒绝 |
| Candidate pages不全/超时 | open→abandoned；按retention清staging；无Snapshot |
| PreflightOutcome存在但seal缺失 | 重算same root/binding/fence并重放seal；不重跑validator |
| sealed Candidate无Snapshot | 重跑same fenced acceptance transaction |
| Snapshot/ChangeSet已commit但wake丢失 | replay scheduling intent/outbox；不重建Snapshot/Revision |
| partial child materialization | ES-02按ChangeSet set-diff补齐 |
| Gate open但Execution wait projection缺失 | 由same Gate target/revision修ES-02 projection/outbox |
| Decision/Gate terminal但wake缺失 | 重放same gate.resolved outbox；不写第二Decision |
| Item pointer/transition ledger漂移 | 按last valid fenced transition修projection或隔离 |
| canonical DB ref缺Artifact | fail-closed + repair intent；不从log猜locator |
| DB rollback留下对象 | ES-04按reservation/owner/digest/grace清理 |
| cleanup proof部分完成 | 重试缺失substrate；不反向改变Item/serving |

Recovery重复任意次数必须保持Snapshot、Revision、Membership、Decision、Transition、ChangeFact和business effect cardinality不变。Repair只能修projection/wake/intent/ref-check，不能合成从未提交的canonical truth。

### 6.5 Cancel 与 terminal cutoff

- Cancel使ES-02停止新Process/materialization并fence active handler；
- open Candidate可abandon；sealed Candidate若acceptance尚未开始可以保持sealed供安全recovery或按明确cancel policy清理，但不得伪accepted；
- acceptance transaction已commit则Snapshot/Revision事实保留；
- open Gate在Execution cancel收敛时以system causation open→superseded，写immutable terminal resolution evidence而不是伪造human Decision；late human decision冲突；
- proof-valid serving结果不回滚，不因parent Task cancelled而deactivate/delete；
- cleanup与cancel独立；cancel不是purge。

ES-03 Process succeeded只证明其manifest output/proof成立。Task succeeded仍需ES-02 root summary和type-specific terminal proof；ingest success最终要求exact Revision publication，metadata/lifecycle intent使用各自proof。

### 6.6 Retention 与 physical cleanup

Retention eligibility至少检查：

1. latest/serving pointer；
2. active/cancelling Execution与restart lineage；
3. open Gate/ReviewTarget/evidence引用；
4. rollback/grace window；
5. legal/operational hold与reference snapshot；
6. derived/vector/index owner refs；
7. pending repair/cleanup/outbox；
8. canonical tombstone/audit skeleton。

Snapshot/Membership、Revision/IntakeArtifact的canonical skeleton、Decision/transition/proof按ES-08-v1.0保留deployment lifetime。Open Gate evidence indefinite；promoted orphan至少24小时；invalid/noncurrent大bytes只有terminal、非current/非serving、无history/hold/backup/outbox/recovery引用后满7天才可release；Candidate/retention/cleanup scanner为60秒bounded keyset。ES-03仍只冻结eligibility/proof，physical cleanup complete不改变Item lifecycle、Task status或历史Decision。

### 6.7 Bootstrap、registry drift 与 readiness

Fresh DB bootstrap顺序：

~~~text
ES-04 schema migrations
→ source/semantic/action/preflight registry bundles
→ ES-05 ProcessCapabilityManifests
→ ES-02 Workflow bundles
→ cross-reference/digest/handler/schema check
→ read-only readiness
~~~

同version同digest no-op；同version异digest fail-loud。Readiness必须检查：

- four source definitions complete；
- seven action + four semantic definitions complete；
- all required validators/check sets/allowlist refs valid；
- 18 Process manifests与handler/schema/proof compatibility；
- ES-02 workflows遵守preflight→seal→accept；
- no unfinished migration、definition drift或legacy dependency。

Bootstrap不执行network/model self-test，不seed生产content/serving truth，不自动修业务row。Golden fixtures属于CI/acceptance。

### 6.8 Security 与 bounded disclosure

- HTTP/API/browser egress只能由SourceDefinition绑定ES-08 `public-document-v1|registered-api-v1` exact policy，并经每跳DNS/public-address/redirect guard；
- secret按ES-08 finite file slot临时解析，仅传exact adapter origin，不写DB/message/log/artifact/child argv；
- URI audit必须移除userinfo、credential query和sensitive header；
- public Gate projection必须redact raw artifact/body、internal IDs、model secret、path与unbounded check evidence；
- all reads team-scoped；Gate decision authority就是valid global internal token，不增加actor RBAC；内部admin诊断只有ES-08本地closed CLI且不属于产品Contract；
- model/vision输入只能为manifest允许的logical object，prompt注入内容不能变成route/authority；
- arbitrary archive recursion、decompression、redirect、page/member、body和metadata size均受§9有限budget。

---

## 7. Legacy Retain / Rewrite / Drop

| Legacy anchor | Retain principle | Rewrite in ES-03 | Drop |
|---|---|---|---|
| smind-admin ingestion/apis.ts、urls.ts | strict provider/action input与team-scoped ingest需求 | source descriptor→Task→IntakeSource binding | random File UUID、平台plan/phone gate、queue rollback |
| smind-skill-clean-universal action_registry.ts | 网页/browser/PDF/model clean能力真实存在 | 正交SourceDefinition + exact Process manifests | browserFetch-geminiClean组合branch |
| cleaner_doc.ts / cleaner_web.ts | MIME、browser、PDF与model处理经验 | streamed budget、declared/detected/verified media、typed lineage | read-all、Cloudflare API绑定、best-effort slot ignore |
| dedicated-apis provider processors | provider schema、stable member key、scatter并行 | registered API exact definition、ExternalKey、paged CandidateSet | random child UUID、silent skip、empty/first-child shortcut |
| clean-dispatcher differ.ts | stable atomic key、content/meta diff价值 | ExternalKey + versioned semantic tuples + RevisionFingerprint | file relation current row、force branch |
| clean-dispatcher finalizer.ts | scatter后fan-out与member级工作 | atomic Snapshot/ChangeSet + committed child intents | opaque child_files、Promise completion order、callback success |
| legacy object/artifact payload | raw/clean表示需要长期追溯 | typed IntakeArtifact owner/digest/logical locator | payload反扫、virtual artifact、R2/D1 key |

Legacy只提供行为/失败模式证据。运行代码、imports、config、DDL、wire、status、UUID、storage locator、bootstrap、fixtures和acceptance均必须零legacy依赖。

---

## 8. Acceptance Evidence

本节86项全部为`HARD`；实现任一失败即conformance/release blocked，且不得以provider响应、物理文件存在或manual acceptance替代。

### 8.1 Source、binding 与 registry

| ID | Scenario | HARD assertion |
|---|---|---|
| ES03-A001 | source kind registry scan | 恰含四类，无alias/组合kind |
| ES03-A002 | unknown descriptor field/source kind | strict 422；零Task下游/Intake row |
| ES03-A003 | inline body ingest/replay | body先staging；Task只存handle/digest；同内容收敛 |
| ES03-A004 | local object absolute path | reject；logical ref有效时stream读取 |
| ES03-A005 | HTTP URI userinfo/fragment/arbitrary header | reject；canonical URI golden稳定 |
| ES03-A006 | registered API raw URL/raw params/code | reject；只接受registered provider/operation/scope |
| ES03-A007 | same source identity replay/concurrent | 一个IntakeSource；同上游UUID异identity冲突 |
| ES03-A008 | SourceDefinition same version different digest | bind/readiness fail-loud，无hot overwrite |
| ES03-A009 | Process manifest inventory | 恰含ES-02列出的18 keys；无coarse/legacy alias |
| ES03-A010 | registry升级后retry/resume | existing Execution仍使用原s05_binding_digest |
| ES03-A011 | cross-team Source/Item/Revision/Gate lookup | 不可见且无存在性泄漏 |
| ES03-A012 | descriptor/binding/log/message leak scan | 无secret value、body、absolute path、backend detail |

### 8.2 Acquisition、canonicalization 与 clean

| ID | Scenario | HARD assertion |
|---|---|---|
| ES03-A013 | inline text/HTML/JSON | AcquisitionEvidence与normalized digest完整 |
| ES03-A014 | local stream exceeds raw/decompressed budget | 消费期间停止；无complete candidate |
| ES03-A015 | static HTTP conditional success | status/final URI/redirect/validator/media证据完整 |
| ES03-A016 | redirect/time/decompress over budget | typed failure；不read-all后补判 |
| ES03-A017 | browser acquisition | exact browser profile与rendered lineage；source kind仍http_resource |
| ES03-A018 | PDF decode | page/text/image/loss evidence稳定；PDF不是source kind |
| ES03-A019 | JSON/text/HTML canonical golden vectors | JCS、UTF-8/LF/NFC、structural HTML digest确定 |
| ES03-A020 | local OCR | page/anchor/confidence/profile proof完整；OCR不是Revision basis |
| ES03-A021 | Vision/model clean | exact model/prompt/invocation/quality lineage；无secret leak |
| ES03-A022 | registered API single | strict envelope/member schema与stable ExternalKey |
| ES03-A023 | paginated scatter complete | stable order、exhaustion、counts/page/root digests一致 |
| ES03-A024 | provider合法空集合 | 只有profile exhaustion proof才可complete |
| ES03-A025 | malformed required member | rejection evidence保留；不能complete auto-admit |
| ES03-A026 | duplicate normalized key | exact fail或identical merge；不依赖并发顺序 |
| ES03-A027 | clean/model版本变化但source semantics相同 | 不创建IntakeRevision |

### 8.3 CandidateSet、preflight 与 acceptance

| ID | Scenario | HARD assertion |
|---|---|---|
| ES03-A028 | same page ordinal+digest replay | 幂等，counts不增长 |
| ES03-A029 | same page ordinal different digest | conflict；candidate不可seal |
| ES03-A030 | missing page/count/Artifact | seal拒绝，无Snapshot |
| ES03-A031 | page/root digest重复计算1,000次 | canonical bytes/digest完全相同 |
| ES03-A032 | execution order inspection | 必须preflight→seal→accept；逆序编译/运行拒绝 |
| ES03-A033 | allowlist缺validator/check-set | readiness/bind fail；不fallback |
| ES03-A034 | allowlisted+passed | Outcome存在，auto_admit，无Gate/Decision |
| ES03-A035 | allowlisted+blocked且reviewable | accepted Intake + open Gate + Execution waiting |
| ES03-A036 | blocked且Artifact/evidence不完整 | no Gate override；admission failed |
| ES03-A037 | validator runtime/schema/evidence error | Process retry/failed；无blocked Outcome/Gate |
| ES03-A038 | non-allowlisted+passed | open Gate，Task仍running |
| ES03-A039 | partial collection缺旧Item | 无absent membership/deactivation |
| ES03-A040 | complete-authoritative缺旧Item | exact absent decision与policy transition |
| ES03-A041 | member/bytes/transaction budget exceeded | open→abandoned；无partial Snapshot |
| ES03-A042 | sealed后append/hot-switch/reopen | 全部冲突；state/history不变 |
| ES03-A043 | sealed acceptance crash/replay | 收敛到一个Snapshot/ChangeSet/child set |
| ES03-A044 | same observation different root digest | intake-observation-conflict；winner不变 |

### 8.4 Canonical Intake、metadata、lifecycle 与 publication

| ID | Scenario | HARD assertion |
|---|---|---|
| ES03-A045 | single accepted member | 一Snapshot/一Membership/稳定Item/正确Revision |
| ES03-A046 | scatter N seen + M absence | 一Snapshot、N+M immutable Memberships、exact ChangeSet；每个required child在LS-RAG前有item-scoped clean/preflight |
| ES03-A047 | first seen member | seen_new_revision、ordinal1、predecessor null、create_item transition从not_exists提交为active |
| ES03-A048 | same semantic fingerprint | seen_no_change，无Revision，latest不变 |
| ES03-A049 | canonical content/context变化 | append Revision，predecessor/definitions/fingerprint正确 |
| ES03-A050 | filter-only metadata change | 新Revision、复用content derived、只走filter publication链 |
| ES03-A051 | context semantic metadata change | 新Revision并走完整LS-RAG |
| ES03-A052 | absence-deactivated Item reappears | reactivate+decision原子；serving仍null |
| ES03-A053 | manually deactivated Item reappears | 保持deactivated；可更新latest但不serving |
| ES03-A054 | valid publication candidate | final Proof+Item/index CAS/transitions+outbox；dual fence eligible |
| ES03-A055 | stale/latest mismatch/invalid proof | 无pointer变化；旧serving持续 |
| ES03-A056 | deactivate | active→deactivated、serving立即null、withdraw intent |
| ES03-A057 | delete | →deleted tombstone、serving null、ordinary path terminal |
| ES03-A058 | deleted ExternalKey再次出现 | acceptance冲突；不得新Item或restore |
| ES03-A059 | intake.rebuild | exact existing Revision；无Snapshot/Revision/clean |
| ES03-A060 | Task cancel after child publication | published child/Revision保留，无隐式deactivate/purge |

### 8.5 Gate、recovery、cleanup 与 architecture

| ID | Scenario | HARD assertion |
|---|---|---|
| ES03-A061 | exact approve | Decision+Gate+Execution+outbox原子；same Execution resume |
| ES03-A062 | approve_override | 仅policy允许且证据完整；override proof可审计 |
| ES03-A063 | required child reject | Gate rejected；siblings继续；collect-all后root可failed |
| ES03-A064 | reclean | 第一次supersede并走bounded branch；第二次action不可见/拒绝 |
| ES03-A065 | stale/double/conflicting Gate decision | same fingerprint幂等；其他409且无反转 |
| ES03-A066 | Gate open/decision各断点fault injection | repair同truth/outbox，不建duplicate target/gate/decision |
| ES03-A067 | long-lived open Gate | 不自动approve；evidence/artifact GC受reference fence |
| ES03-A068 | acceptance transaction逐点fault injection | Snapshot/Item/Revision/Membership/ChangeSet/outbox all-or-none |
| ES03-A069 | commit后wake丢失/重复 | outbox replay；canonical rows/children不重复 |
| ES03-A070 | orphan object与missing canonical Artifact | orphan grace清理；missing fail-closed+repair，无virtual Artifact |
| ES03-A071 | recovery scanner重复100次 | canonical/decision/transition/business counts不增长 |
| ES03-A072 | cleanup有hold/partial/all proofs | fenced；partial不complete；全部required才complete |
| ES03-A073 | fresh DB bootstrap twice | 首次注册；二次same digest no-op；无生产content |
| ES03-A074 | schema/registry/Workflow order drift | readiness false；不猜latest/自动修truth |
| ES03-A075 | payload_extra critical key injection | schema/lint/repository dependency gate拒绝 |
| ES03-A076 | legacy dependency scan | runtime/config/DDL/API/event/startup零legacy/Cloudflare/R2/D1/SMCP依赖 |
| ES03-A077 | exact state/alias/schema scan | 仅Candidate四态、Item三态、Gate四态；无第七StateFamily |
| ES03-A078 | port/message/leak cross-spec test | owner mutation只经port；message bounded且无body/secret/path/full Workflow |

### 8.6 ES-07 publication calibration

| ID | Scenario | HARD assertion |
|---|---|---|
| ES03-A079 | first/new Revision publication | Item serving与active index pointer、双transition、proof同UoW |
| ES03-A080 | same-Revision reindex | serving值相同；Item/index revisions +1且generation替换 |
| ES03-A081 | deactivated rebuild | validated_not_served proof；serving/index pointers保持null |
| ES03-A082 | deleted publication | rejected；Item/index/proof均无mutation |
| ES03-A083 | stale Item或index pointer CAS | whole rollback；旧双pointer持续 |
| ES03-A084 | filter-only publication | new Revision serving + reused content/vector lineage exact |
| ES03-A085 | publish vs deactivate/delete race | CAS one winner；最终dual fence不返回ineligible Item |
| ES03-A086 | serving-changed event | old/new Revision+generation+proof与两个after revisions exact |

### 8.7 必须交付的证据包

1. 四类descriptor OpenAPI/JSON Schema及negative fixtures；
2. source/semantic/action/preflight/process registry manifests与digest snapshots；
3. ExternalKey、JCS/text/HTML、RevisionFingerprint golden/property vectors；
4. media/encoding/stream/decompress/redirect/page/member budget报告；
5. inline/local/HTTP/browser/PDF/API/OCR/Vision representative capability fixtures；
6. Candidate page/root、rejection/gap/exhaustion、preflight/seal fault matrix；
7. 十张canonical + supporting schema logical→ES-04 physical DDL mapping；
8. PK/FK/unique/CHECK/XOR/CAS/immutability/payload_extra inspection；
9. Candidate/Item/Gate exhaustive state transition property tests；
10. single/scatter/metadata/rebuild/deactivate/delete、new/same-Revision dual-pointer publication端到端记录；
11. Gate authority/idempotency/CAS/outbox/reclean crash report；
12. acceptance/publication/recovery/cleanup并发与fault-injection报告；
13. owner-truth/baseline/ES-01/02 trace matrix；
14. legacy/import/config/DDL/API/event/startup architecture scan。

---

## 9. Remaining Technical Decisions and Defaults

本节没有Owner问题。以下是有限v1默认；只有实测证据表明无法满足同一Truth时，才可在ES-03/08内版本化修订。所有数值是安全围栏，不是吞吐/SLA承诺。

| Topic | v1 default | 变更门槛 |
|---|---|---|
| Inline public content | max 1 MiB；text或base64二选一 | 与ES-01 request/staging fault tests一致 |
| Request body | max 8 MiB | ES-01/08可下调；不得绕过staging |
| Raw representation | max 64 MiB per member | representative PDF/web/API evidence |
| Decompressed content | max 256 MiB、ratio max 100:1、nested archive disabled | zip-bomb/security tests |
| HTTP | registered read-only GET/HEAD；redirect max 5；wall 60s | source profile可更低，不开放arbitrary method |
| Browser | one local deterministic profile；wall 120s；network由egress allowlist | ES-08 resource/security evidence |
| Registered API | max 1,000 pages、10,000 members per Snapshot | complete/exhaustion/transaction benchmarks |
| Candidate page | max 500 members；stable key order | ES-04 transaction/load evidence |
| Candidate total | max 10,000 members或256 MiB staged bytes，先到者 | 超限fail-loud，不静默拆Snapshot |
| Canonical acceptance | max 10,000 ChangeFacts/transaction | real driver atomicity benchmark |
| Candidate expiry | open default 24h；sealed按acceptance/recovery policy保护 | ES-08 retention/runbook |
| Metadata | context+filters canonical JSON各max64 KiB | schema/filter benchmark |
| Digest | SHA-256；JCS/text-v1/html-struct-v1/revision-v1 | breaking recipe用新version，不改历史 |
| ExternalKey duplicate | fail；只允许definition声明merge_identical | deterministic merge property tests |
| Absence | default disabled；仅definition明确complete+authoritative+policy时启用 | negative absence matrix |
| Preflight | every ingest mandatory；validator只读 | 不可关闭或allowlist绕过 |
| Human wait | indefinite、no auto-approve | ES-08只定义提醒/retention，不改变决策 |
| Reclean | max 1 per Execution；compiled acyclic branch | 若需更多必须先证明不会变成编辑/loop产品 |
| Deleted key | permanent reservation；no restore/hard delete | foundational reopen才可改变 |
| Publication | old serving retained until proof-valid CAS | 无queue/log/partial proof替代 |
| Physical tables | ES-04可安全合并outbox/registry storage | 必须证明本文件typed columns/constraints/owner不丢失 |

### 9.1 下游绑定闭合状态

以下不是开放问题；当前均已由既有Execution Spec给出exact实现：

- physical SQL type/index/transaction budget：ES-04-v1.0；
- logical object backend、atomic write、reservation、orphan/GC：ES-04-v1.0；
- model/prompt/provider exact binding和GenerationInvocation：ES-05-v1.0；
- secret resolver、egress policy、valid-token review authority：ES-08-v1.0；
- retention duration、60秒scanner、metrics/alerts/runbook：ES-08-v1.0。

这些闭包和最终cross-spec audit均已完成，未生成新文件、QNA、service、platform、source kind、StateFamily或产品能力。

---

## 10. Revision History

| 版本 | 日期 | 状态 | 变更 |
|---|---|---|---|
| ES-03-v0.1 | 2026-08-10 | internally-consistent / awaiting cross-spec audit | 继承OT-01..04、S04-v1.2、S05-v1.1、D02-v1.0和ES-01/02，冻结四类source descriptor、source/binding、18个Process capability、ExternalKey/canonicalization/RevisionFingerprint、十张canonical及supporting逻辑schema、Candidate/Item/Gate状态机、preflight→seal→accept顺序、single/scatter/metadata/lifecycle/publication/Gate链路、ports/messages、failure/recovery/cleanup与78项acceptance；关闭D02移交的Membership decision和Gate action exact spelling。参考legacy能力与踩坑但删除其File identity、组合branch、silent skip、callback与平台依赖。未新增产品责任、StateFamily、部署单元或spec文件。 |
| ES-03-v0.2 | 2026-08-10 | internally-consistent / awaiting cross-spec audit | 与ES-07-v0.1校准PublicationProof边界：intake_publication_v1原子提交Item serving与active index pointer及双transition，允许proof-valid same-Revision reindex在serving值不变时推进两类revision；补齐deactivated validated-not-served、filter reuse、lifecycle race、event与8项acceptance。仍为原34张表、Item三态和既有action/intent，无新StateFamily或产品能力。 |
| ES-03-v1.0 | 2026-08-10 | ready | 完成OT-01..04、S04/S05/D02及ES-01/02/04/05/07/08最终对账；4类source、18个本域Process、3个本域StateFamily、34张owner tables与86项HARD acceptance均已set-exact。未新增source、身份、状态族、服务或spec文件。 |
