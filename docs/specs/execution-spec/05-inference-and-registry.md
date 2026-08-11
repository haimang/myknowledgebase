# ES-05 — Inference and Registry

> **项目**：myknowledgebase（MKB）
>
> **文件 ID**：ES-05
>
> **文档性质**：execution-spec / implementation authority
>
> **版本 / 日期**：ES-05-v1.0 / 2026-08-10
>
> **文档状态**：ready
>
> **Truth 输入**：OT-01-v1.0、OT-02-v1.0、OT-03-v1.0、OT-04-v1.0
>
> **Baseline 输入**：S03-v1.3、S04-v1.2、S05-v1.1、S06 T-O-77..85、D02-v1.0；S11/S14 没有 frozen 文件
>
> **上游 Execution Spec**：ES-02-v1.0、ES-03-v1.0、ES-04-v1.0、ES-06-v1.0、ES-07-v1.0
>
> **上游索引**：docs/specs/index.md

本文件是 MKB v1 推理 adapter 与内部 registry 的唯一 Execution Spec。它负责 ProcessCapabilityManifest、strict Schema、Model、Prompt、InferenceProfile 的 code-owned immutable registration，负责 local OCR、external generative/vision与text embedding adapter的 exact binding、调用协议、对应Invocation账、token/error evidence和provider isolation。

本文件不把 Model、Prompt、Schema 或 capability变成外部产品，不提供动态plugin、playground、tenant override、agent authoring或热切换。StructureSchemaDefinition 的业务语义和 exact LS-RAG shape仍由 ES-06 持有；EmbeddingSpace、EmbeddingInvocation、vector/index/retrieval语义归ES-07。ES-05只登记ES-07已冻结的exact embedding ModelDefinition、Process/Schema compatibility和Gemini adapter capability，不预建generic model/vector surface。

---

## 1. Inherited Truth

### 1.1 权威输入

| 来源 | 本文件直接继承 | 本文件不得改变 |
|---|---|---|
| OT-01-v1.0 | MKB是单体knowledge工具；adapter-first；模型选择属execution | 不建设AI平台、agent产品、Prompt产品或新服务 |
| OT-02-v1.0 | 六个且仅六个StateFamily；GenerationArtifact/Invocation是derived fact而非runtime identity/state | 不给Model、Prompt、Invocation、registry建立第七StateFamily |
| OT-03-v1.0 | OCR/Vision/model-assisted clean在V1能力内；exact Schema绑定；无external Schema CUD | 不增加聊天、answer generation、任意模型调用或raw vector API |
| OT-04-v1.0 | exact definition/model/Prompt/schema/capability drift fail-loud；provider替换不改变产品Contract | 不用“某provider返回成功”替代typed proof/quality/full validation |
| S03-v1.3 | ProcessCapabilityManifest fields、typed ports、proof、retry/idempotency/resource access和Execution exact binding | handler不选route、不推进Execution/Task、不热切manifest |
| S04-v1.2 | immutable definition版本、registry bootstrap、same-version drift fail readiness、payload_extra规则 | 模型升级不制造IntakeRevision或重解释历史 |
| S05-v1.1 | 四类source、local OCR、Vision/model clean、exact model/prompt refs、producer/loss/quality lineage | OCR/Vision输出不能单独制造Revision，缺能力不fallback |
| S06 T-O-77..85 | 每次模型调用有durable GenerationInvocation；artifact/history/current/schema/kernel/extension/full-revalidation宪法 | 不原位覆盖artifact，不修kernel，不建私有retry状态机 |
| D02-v1.0 | StateFamily唯一owner、typed fact、SelectionPointer与Outcome正交 | Registry status、invocation outcome/token不是业务状态 |
| ES-02-v1.0 | finite exact Process catalog、ProcessCommand/Outcome、claim/fence/retry唯一owner | ES-05 adapter无私有retry/next-step/terminal权限 |
| ES-03-v1.0 | exact S05 binding、clean contracts与publication owner boundary | 不改变source taxonomy、Candidate/Item/Gate状态或acceptance顺序 |
| ES-04-v1.0 | embedded registry persistence、object refs、named UoW、outbox与126-table physical profile | 不直连driver/path，不在DB transaction内做模型/OCR/embedding I/O |
| ES-06-v1.0 | 两个LS-RAG Process、8-component StructureSchema、四套Prompt/Profile与exact ES-07 consumer | 只登记exact definitions/bindings；不改变tree/artifact/current语义 |
| ES-07-v1.0 | 六个vector/index Process、gemini-embedding-2 text-768 space、15个wire schemas与retrieval consumer support | 只登记exact model/capability/schema/manifest；embedding ledger与vector/retrieval语义仍归ES-07 |

S11/S14 在旧 baseline 只作为未来槽位出现，没有 frozen truth 文件。本文件只关闭上表已经明确移交的 execution义务；不把旧QNA候选、legacy provider列表或console Prompt功能升级为产品Truth。

### 1.2 Truth 到交付物映射

| Truth cluster | 本文件落点 |
|---|---|
| S03-T015 / ProcessCapabilityManifest | §4.2、§5.2、§5.8 capability registry/ports |
| S03-T017/T053 / no hot switch | §4.5、§5.6、§6.2 exact binding |
| S05-T001/T009/T025 | §4.3/4.6、§5.5/5.7、§6.6 OCR/Vision lineage |
| S05-T028 / bootstrap | §4.8、§5.2..5.6、§8 registry evidence |
| T-O-77 / Invocation | §4.7、§5.7、§6.3/6.4 invocation protocol |
| T-O-80..82 / Schema | §4.4、§5.3、§5.8 compatibility handshake |
| T-O-83..85 / repair/retry | §4.6、§6.5、§8 negative tests |
| OT04-C006 | §6、§8 model/Prompt/schema/capability drift and replacement evidence |

### 1.3 唯一 ownership

| Concern | 唯一 owner | 跨域权限 |
|---|---|---|
| Process capability contract registry | ES-05 CapabilityRegistryOwner | ES-02 compiler/readiness只读；各ES提供自己process contract内容 |
| Contract/response schema registry | ES-05 SchemaRegistryOwner | schema semantic owner提交code-owned bundle；consumer只resolve exact ref |
| StructureSchemaDefinition semantics | ES-06 | ES-05只存exact definition artifact/ref、components与compatibility，不改kernel/extension意义 |
| Model definition/provider adapter | ES-05 ModelRegistryOwner/InferenceAdapter | ES-03/06只绑定logical model/profile refs，不调用provider SDK |
| Prompt definition/render | ES-05 PromptRegistryOwner | ES-03/06定义purpose/variables/evaluation fixture，外部无CUD |
| Inference profile resolution | ES-05 InferenceRegistryOwner | Workflow/source/structure profile必须引用exact version，不读latest |
| GenerationInvocation | ES-05 InvocationLedgerOwner | current-fenced Process可reserve/call/complete；ES-06按ref建立Artifact causation |
| Process retry/claim/fence/status | ES-02 | ES-05只返回typed outcome/error/indeterminate，不自己重试或改状态 |
| Clean candidate/evidence | ES-03 | ES-05返回inference evidence；ES-03决定candidate与preflight，不制造Revision |
| GenerationArtifact/schema validation/current pointer | ES-06 | ES-05不创建/切换artifact pointer |
| Secret/egress/rate/concurrency/telemetry | ES-08 | ES-05声明logical slots、safe evidence与limits；不保存secret值 |

### 1.4 技术与 legacy 证据

| 证据 | 可保留 | 必须替换/删除 |
|---|---|---|
| Gemini model/version docs | stable explicit model IDs、structured output、multimodal/PDF input | `latest` alias、preview/experimental model、provider tool/agent功能 |
| Gemini structured output docs | JSON Schema约束可降低syntax drift | provider schema只支持subset且不保证semantic truth，仍需本地full validation |
| Tesseract docs | local LSTM OCR、TSV/hOCR可产生word confidence与coordinates | shell invocation、unversioned binary/tessdata、仅plain text无anchor |
| legacy ai_schemas | provider-neutral typed request/response、token usage | generic `any` body、provider metadata耦合、unknown token写0 |
| legacy Gemini adapter | model role mapping、system prompt、JSON response schema | hardcoded latest model、KV prompt热读、round-robin key、full-buffer、raw response进error |
| legacy PromptManager/console | prompt key/version和变量清单有价值 | tenant override、TTL hot reload、generic fallback、UI/CRUD/deploy/playground |
| legacy action registry | explicit handler map与strict schemas | branch-name组合、dynamic action、provider fallback、Cloudflare bindings |

技术参考：

- https://ai.google.dev/gemini-api/docs/models
- https://ai.google.dev/gemini-api/docs/models/gemini-3.6-flash
- https://ai.google.dev/gemini-api/docs/structured-output
- https://ai.google.dev/gemini-api/docs/document-processing
- https://ai.google.dev/gemini-api/docs/deprecations
- https://pypi.org/project/google-genai/
- https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html
- https://github.com/tesseract-ocr/tesseract/releases

---

## 2. Scope / Non-scope

### 2.1 Scope

ES-05只负责：

1. 18个ES-03 + 2个ES-06 + 6个ES-07 ProcessCapabilityManifest的exact internal registry；
2. strict JSON Schema definition、digest、validator contract与producer/consumer compatibility声明；
3. finite ModelDefinition、ModelCapability、PromptDefinition、PromptVariable与InferenceProfile；
4. code/migration/bootstrap-only registration、same-version idempotency/drift、governance事实与readiness；
5. local Tesseract OCR 5.5.2 adapter、fixed tessdata与TSV/hOCR/text证据；
6. external Gemini Developer API adapter、stable gemini-3.6-flash structured/multimodal inference与gemini-embedding-2 text embedding；
7. exact model/prompt/schema/profile binding、prompt rendering、request canonicalization与input/output digest；
8. 每个真实generative/vision call的GenerationInvocation reservation/outcome/token/error/causation账；
9. provider-neutral InferenceCommand/Outcome、ports、error taxonomy、budget/deadline/idempotency；
10. provider replacement contract、bootstrap/CI fixture与failure/recovery证据。

### 2.2 Non-scope

- 不提供public Model/Prompt/Schema/Capability CRUD、list、playground、deploy、test-run或admin UI；
- 不提供dynamic plugin、arbitrary provider、OpenAI-compatible通用gateway、agent/tool/function calling、search、code execution或Files API；
- 不提供chat/completion通用endpoint、final answer、conversation/session/memory、tenant persona或业务Prompt；
- 不允许caller选择provider/model/prompt/schema/sampling参数、上传Prompt或提交arbitrary JSON Schema；
- 不使用`latest` alias、active-model猜测、Prompt KV热更新、TTL cache路由、silent fallback或cross-provider fallback；
- 不在adapter内进行隐藏retry、repair loop、schema loosening、JSON提取/coercion或“best effort”补字段；
- 不把provider 2xx、schema-shaped JSON、token usage或OCR text当作clean/Generation/Task/publication成功；
- 不在本文件冻结LS-RAG exact node/block/anchor结构、GenerationArtifact types、embedding/index/rerank或retrieval算法；
- 不建设fine-tuning、training、evaluation platform、prompt optimization、model hosting、GPU scheduler或cost/billing产品；
- 不兼容legacy KV keys、model aliases、Cloudflare AI Gateway、metadata、D1/R2 wire或Prompt记录。

### 2.3 完成定义

ES-05的`ready`是规范状态：以下义务已被完整定义并通过cross-spec audit，不表示它们已在尚未构建的实现上运行。任何实现要声明符合ES-05-v1.0并进入release，必须同时满足：

1. registry bundle在fresh DB确定性安装、二次no-op、same-version drift fail readiness；
2. ES-03全部18个、ES-06全部2个与ES-07全部6个Process manifest key/ports/proof/handler exact注册并compile compatible；
3. local OCR与external Vision路径在代表性fixture上产生typed anchor/loss/quality/invocation evidence；
4. 每次provider network call都预先有对应ledger reservation：generative/vision使用GenerationInvocation，embedding使用ES-07 EmbeddingInvocation；最终均有terminal outcome或可恢复missing-outcome evidence；
5. retry/resume/recovery始终复用Execution绑定的exact manifest/model/prompt/schema/profile digest；
6. provider output经过本地strict shape、semantic、source-proof验证后才可成为downstream candidate/artifact；
7. timeout/crash/429/5xx/content block/schema invalid/usage unknown均有typed disposition且无adapter私有retry；
8. secret、raw credential、absolute path、full source/output正文不进入DB/error/log/wire；
9. generative/vision provider替换通过新增definition/profile/Workflow binding且不改变Process/public contract；embedding替换还必须新增EmbeddingSpace并遵守ES-07明确禁止live mixed-space的cutover boundary；
10. ES-06/07 exact capabilities/schema/model/profile已回填，并通过全量cross-spec audit。

### 2.4 核心术语

| 术语 | Exact 含义 |
|---|---|
| Capability manifest | Process key的versioned typed执行合同；不是外部skill/plugin或runtime状态 |
| Schema definition | MKB code-owned immutable JSON/semantic contract ref；不是caller schema或字段清单即truth |
| Model definition | logical model key/version到一个exact local/external implementation的immutable映射 |
| Prompt definition | immutable system instruction template+变量contract+content digest；不是mutable文案 |
| Inference profile | exact model+prompt+input/output schema+参数+budget+purpose的immutable bundle |
| Execution binding | Execution materialization时冻结的exact refs/digests；同Execution不重新resolve |
| GenerationInvocation | 一次真实generative/vision provider call的durable请求/成本/因果事实；不是Attempt或StateFamily |
| Local OCR invocation | deterministic local engine execution；保留engine/tessdata/profile/input/output evidence，不计provider token |
| Provider success | transport+provider返回可解析结果；仍不等于domain/full-validation成功 |
| Structured output | provider按schema生成JSON；本地validator仍是最终contract authority |

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

Local OCR与Vision/model-assisted clean已经由OT-03/S05冻结，LS-RAG推理与exact registry已由T-O-77..85要求。Model/Prompt/Schema/Capability definitions与Invocation是实现这些既有能力的internal definition/fact，不是新增产品身份或状态。固定一个local engine和一个external provider，关闭dynamic plugin、多provider、Prompt产品与agent tools，明确降低而非提高范围上限。

---

## 4. Architecture Decisions

### 4.1 模块与依赖方向

~~~text
code-owned registry bundles
  → registry bootstrap/validator
      → ES-04 immutable tables + bundle manifest

ES-02 compiler/resolver
  → CapabilityRegistryReadPort
  → SchemaRegistryPort.assert_compatible

ES-03 / ES-06 Process handler
  → exact InferenceProfile ref from Execution binding
  → InferenceService
      → PromptRenderer + local schema validator
      → InvocationLedgerPort
      → LocalTesseractAdapter | GeminiAdapter
      → ES-04 ObjectWrite/Read ports
  → typed evidence/Outcome back to ES-02
~~~

固定内部模块：

- `registry.domain`：finite definition identities、digest、compatibility与governance rules；
- `registry.application`：bundle install、resolve exact、compile/readiness validation；
- `inference.application`：command validation、prompt render、invocation reserve/outcome、local validation；
- `inference.adapters.tesseract`：唯一local OCR implementation；
- `inference.adapters.gemini`：唯一external generative/vision/text-embedding implementation；
- `inference.projections`：safe registry/readiness/token/cost metrics，不是产品API。

Domain/application不得导入provider SDK HTTP types、subprocess、filesystem path、secret value、Turso driver、Workflow router或Task repository。Provider adapters不得访问domain repositories，只消费已经resolve的exact command和bounded streams。

### 4.2 ProcessCapability registry

#### 4.2.1 Manifest authority

Registry只接受`mkb.process-capability-manifest.v1`，字段与ES-02 §5.7完全一致：process key/contract version/handler、allowed phases、typed ports、parameters、Outcome/proof、side effect、idempotency、retry error policy与resource access。Manifest canonical digest覆盖所有child rows，按port/parameter/error/resource稳定排序。

V1规则：

1. process key稳定、contract version显式；same key/version/same digest no-op，异digest fail readiness；
2. handler key必须存在于code-owned static map，signature与ports exact一致；
3. manifest没有active/latest pointer；WorkflowRevision直接引用key+version+digest；
4. governance `deprecated`只阻止新Workflow registration，旧Execution可继续；`disabled`阻止新binding和新provider invocation，旧Executionfail-loud、不fallback；
5. manifest升级创建新version并要求新WorkflowRevision；不原位改变旧Execution；
6. capability key不是request intent、Workflow、source kind或plugin。

#### 4.2.2 ES-03 exact catalog

以下18项全部以contract version `1`注册；logical contract由ES-03 §4.4拥有，ES-05拥有registry spelling与handler existence：

| Process key | Handler key | Side effect | Inference binding |
|---|---|---|---|
| intake.acquire.inline | intake_acquire_inline_v1 | idempotent_by_key | none |
| intake.acquire.local_object | intake_acquire_local_object_v1 | idempotent_by_key | none |
| intake.acquire.http_static | intake_acquire_http_static_v1 | idempotent_by_key | none |
| intake.acquire.http_browser | intake_acquire_http_browser_v1 | idempotent_by_key | none |
| intake.acquire.registered_api | intake_acquire_registered_api_v1 | idempotent_by_key | none |
| intake.decode.text_json_html | intake_decode_text_json_html_v1 | pure | none |
| intake.decode.pdf | intake_decode_pdf_v1 | pure | none |
| clean.extract.deterministic | clean_extract_deterministic_v1 | pure | none |
| clean.ocr.local | clean_ocr_local_v1 | idempotent_by_key | `ocr.tesseract.default/1` exact |
| clean.extract.vision | clean_extract_vision_v1 | idempotent_by_key | `vision.clean.gemini/1` exact |
| clean.map.registered_api | clean_map_registered_api_v1 | pure | none |
| intake.preflight_validate | intake_preflight_validate_v1 | pure | none |
| intake.collection.seal | intake_collection_seal_v1 | transactional_sink | none |
| intake.accept_snapshot | intake_accept_snapshot_v1 | transactional_sink | none |
| intake.metadata.apply | intake_metadata_apply_v1 | transactional_sink | none |
| intake.lifecycle.deactivate | intake_lifecycle_deactivate_v1 | transactional_sink | none |
| intake.lifecycle.delete | intake_lifecycle_delete_v1 | transactional_sink | none |
| intake.cleanup.plan | intake_cleanup_plan_v1 | transactional_sink | none |

#### 4.2.3 ES-06 exact catalog

以下2项以contract version `1`注册；业务contract由ES-06 §4.2/§5.8拥有，ES-05拥有registry spelling、handler existence与inference binding：

| Process key | Handler key | Side effect | Inference binding |
|---|---|---|---|
| lsrag.structurize | lsrag_structurize_v1 | non_replayable | `lsrag.structurize.window/1` + `lsrag.structurize.merge/1` exact |
| lsrag.construct | lsrag_construct_v1 | non_replayable | `lsrag.construct.summary/1` + optional-once `lsrag.extension.repair/1` exact |

两个manifest输入均要求current ES-02 Process fence、exact accepted Revision/clean Artifact、`lsrag.structure/1` digest和完整command digest。Structurize输出`StructureProofV1`；Construct输出`LsragBuildProofV1`。Known error retryability交ES-02；dispatch outcome unknown按non-replayable fail-loud。Final GenerationCommit的transactional sink idempotency由ES-06/04 named UoW验证，不改变真实模型call不可私自重发的side-effect分类。

#### 4.2.4 ES-07 exact catalog

以下6项以contract version 1注册；业务contract由ES-07 §4.5/§5.3拥有，ES-05拥有registry spelling、handler existence及exact schema/binding compatibility：

| Process key | Handler key | Side effect | Exact binding |
|---|---|---|---|
| vector.embed | vector_embed_v1 | non_replayable_external | embedding.gemini-2.text-768/1 |
| index.stage_generation | index_stage_generation_v1 | transactional_sink | IndexStageCommandV1 / IndexGenerationCandidateV1 |
| index.validate_publication | index_validate_publication_v1 | transactional_sink | PublicationCommandV1 / PublicationResultV1 |
| index.update_filters | index_update_filters_v1 | transactional_sink | FilterUpdateCommandV1 / IndexGenerationCandidateV1 |
| index.withdraw_serving | index_withdraw_serving_v1 | transactional_sink | IndexWithdrawalCommandV1 / ProofV1 |
| index.rebuild_generation | index_rebuild_generation_v1 | transactional_sink | discriminated plan_scope/build_item contract |

vector.embed输入绑定exact ES-06 GenerationCommit/Projection和EmbeddingSpace；输出只含VectorBuildManifest proof，不含vector bytes。其真实network send由ES-07 EmbeddingInvocation ledger reserve-before-call，adapter retry为0。其他五个handler没有provider网络调用。

index.rebuild_generation manifest的mode是closed discriminated union：plan_scope生成frozen ordered plan，build_item只消费一个plan item。它不是generic action dispatcher。六个manifest均不携带next Process；ES-02 compiled route唯一推进。

当前manifest总数exact为26。不得注册coarse lsrag.vectorize_index、第三个LS-RAG repair Process、generic inference.run、vector CRUD、retrieval Task或legacy alias。

### 4.3 两个且仅两个 v1 inference adapters

#### 4.3.1 LocalTesseractAdapter

固定runtime：

| Item | v1 value |
|---|---|
| Engine | Tesseract OCR 5.5.2 exact binary |
| Engine mode | `--oem 1` LSTM |
| Outputs | UTF-8 text + TSV + hOCR；均作为immutable logical objects |
| Languages | registered profile明确列出；首版`eng+chi_sim`，tessdata文件digest exact |
| Page segmentation | profile exact `psm`，不得caller自由传；default 3 |
| Invocation | argv array直接spawn，无shell；isolated temp dir；deadline/memory/CPU/output budget |
| Network | none |
| Determinism | binary+tessdata+profile+input digest构成binding；相同binding视为可重算，不保证跨CPU byte-identical |

Adapter只接收已验证的image/scanned-page object stream。它将输入写入ES-08受控temporary workspace，使用argv执行，不从filename/media猜参数。TSV/hOCR解析产生page/line/word coordinates、confidence、language/profile evidence；plain text单独保存。Exit code 0仍需三份输出、UTF-8、coordinate bounds与digest validation。

#### 4.3.2 GeminiAdapter

固定runtime：

| Item | v1 value |
|---|---|
| Provider | Gemini Developer API |
| SDK | `google-genai==2.13.0` exact pin |
| Models | stable explicit gemini-3.6-flash与gemini-embedding-2；禁止任何latest alias |
| API surface | GenerateContent structured/multimodal + EmbedContent text-only |
| Tools | none：search、URL context、code execution、function calling、Files API全部disabled |
| Output | one text/JSON candidate；response schema exact |
| Thinking | profile显式`medium`；不依赖provider mutable default |
| Sampling | 不发送已deprecated temperature/top_p/top_k；不允许caller覆盖 |
| Retry | SDK/transport automatic retry=0；每个network send必须对应一个Invocation |
| Inputs | text或single page/image/PDF fragment inline，per-call decoded bytes最大8MiB |
| Secrets | ES-08 `SecretPolicyPort`按logical slot临时解析；不落库/日志/command |

Gemini 3.6 Flash是当前GA stable explicit ID，支持text/image/PDF和structured output。模型生命周期仍可能结束，因此Definition保存provider model ID、model metadata digest与observed lifecycle evidence；deprecation通过新Model/Profile/Workflow version迁移未来Execution，绝不在旧Execution内换模型。

GeminiAdapter同时实现ES-07 TextEmbeddingAdapterPort，但不持有EmbeddingSpace、Invocation或VectorRecord repository。EmbedContent只接受ES-07已经构造的1..16个独立text Content、exact model ID、output_dimensionality=768和deadline；不发送task_type、multimodal bytes或caller参数。ES-07在network send前后写自己的EmbeddingInvocation ledger，因此GenerationInvocation表不伪装embedding账。

不使用Files API，避免引入remote file lifecycle与cleanup。ES-03先将大PDF确定性解码为bounded pages/segments；每次Vision调用只传exact logical object。Base64/SDK request允许bounded内存展开，但8MiB hard input budget与Process concurrency共同限制峰值。

### 4.4 Strict schema registry

Schema registry只承载MKB已知的有限kind：

| schema_kind | Semantic owner | 用途 |
|---|---|---|
| process_input | owning ES | ProcessCommand typed input port |
| process_output | owning ES | ProcessOutcome business payload |
| proof | owning ES | completion proof |
| prompt_variables | ES-05 + purpose owner | render variables |
| inference_response | purpose owner | provider structured output与local parse |
| structure | ES-06 | complete StructureSchemaDefinition envelope |
| retrieval_internal | ES-07 | internal vector/retrieval message；不对caller开放raw vector |
| external_contract | ES-01 + ES-07 | retrieval.search request/result；只登记schema，不开放registry API |

Definition identity=`schema_key + schema_version + schema_digest`。Dialect固定MKB JSON Schema 2020-12 subset；必须有root object、`additionalProperties=false`、bounded depth/property/array/string/number limits、explicit required、no remote `$ref`、no dynamic anchor、no executable/custom keyword。Local validator是authority；provider只接收其支持的投影`provider_schema_digest`，投影不得弱化本地required/type/enum；无法等价投影则该Model/Profile不能注册。

Structure schema除shape artifact外还必须绑定kernel schema、extension schema、semantic validator manifest与source-proof contract。ES-05只校验component存在/digest/consumer compatibility；exact tree/node/block/anchor与repair cutoff由ES-06冻结。

ES-06现已固定`lsrag.structure/1`，其definition component set必须exact包含：`mkb.lsrag.source-element-manifest.v1`、`mkb.lsrag.structure-document.v1`、`mkb.lsrag.construction-document.v1`、`mkb.lsrag.retrieval-block-projection.v1`、`mkb.lsrag.generation-validation-report.v1`、`mkb.lsrag.structure-proposal.v1`、`mkb.lsrag.summary-proposal.v1`、`mkb.lsrag.extension-repair.v1`。Registry同时保存ES-06 kernel/extension path-set digest、validator digest与ES-07 consumer support；缺少、增加或same-version drift任一component均使readiness false。

ES-07 exact schema set为15项：

    mkb.embedding-content-command.v1
    mkb.embedding-content-outcome.v1
    mkb.vector-embed-command.v1
    mkb.vector-build-manifest.v1
    mkb.index-stage-command.v1
    mkb.index-generation-candidate.v1
    mkb.index-publication-command.v1
    mkb.index-publication-result.v1
    mkb.index-filter-update-command.v1
    mkb.index-withdrawal-command.v1
    mkb.index-withdrawal-proof.v1
    mkb.index-rebuild-command.v1
    mkb.index-rebuild-plan.v1
    mkb.retrieval-search.v1
    mkb.retrieval-result.v1

其中embedding outcome中的vector array只允许ES-07 internal consumer support；public retrieval result schema显式禁止vector/model/provider/path/Process/fence。ES-07还必须以consume模式登记mkb.lsrag.retrieval-block-projection.v1 exact digest。15项缺失、多余、same-version drift或public/internal support倒置均使readiness false。

### 4.5 Model / Prompt / Profile exact binding

#### 4.5.1 ModelDefinition

ModelDefinition冻结：logical key/version/digest、adapter key/version/digest、provider kind/model ID或local binary identity、supported modalities/capabilities、context/input/output limits、structured-output subset、tool policy、token accounting contract、determinism class、lifecycle evidence、secret slot schema与egress policy。无active/latest model pointer。

首版definitions：

- `tesseract-ocr/5.5.2-mkb1`：local OCR，绑定binary build digest与`eng/chi_sim` tessdata digests；
- `gemini-3.6-flash/1`：external generative+vision，绑定Gemini adapter v1、stable ID与observed capability digest。
- gemini-embedding-2/1：external text embedding，绑定同一Gemini adapter v1、stable ID、128..3072 provider dimension range与ES-07固定768 consumer contract。

#### 4.5.2 PromptDefinition

Prompt使用`mkb-prompt-template-v1`有限grammar：literal UTF-8 text + `{{variable_name}}` placeholder；不允许condition、loop、include、expression、function、remote fetch或arbitrary template engine。Definition冻结system instruction logical object ref/digest、variable schema、allowed purpose/capability、input-part contract、output schema、safety/tool instruction与evaluation fixture set digest。

大段source/body不做字符串模板插值，而作为独立typed content part传入。Variable值按type进行context escape与size限制；缺变量、额外变量、delimiter collision或render digest不符即fail，禁止空值fallback。

首版Prompt definitions：

- `clean.vision.extract/1`：只从exact page/image提取source-grounded text/anchors/loss/quality，禁止补写未见内容；
- `lsrag.structurize.window/1`：只对engine-fixed ordered leaves给出compatible closed kind/parent并增加局部container hierarchy；
- `lsrag.structurize.merge/1`：只对连续window roots增加有限global section hierarchy；
- `lsrag.construct.summary/1`：只生成passage/section/document summary sentences和target-local citations；
- `lsrag.extension.repair/1`：只返回validator提供的governed extension pointer replacements，一次且无kernel权限。

四个LS-RAG Prompt的变量、typed content parts、response schema、allowed Process和fixture digest均来自ES-06-v1.0 §4.3；不存在generic fallback Prompt、constructor自由Prompt或caller override。

#### 4.5.3 InferenceProfile

Profile是以下tuple的immutable digest：

~~~text
purpose key/version
model key/version/digest
prompt key/version/digest (nullable only local OCR)
input schema ref/digest
response schema ref/digest
local validator key/version/digest
provider schema projection digest nullable local
explicit parameters/tool policy/safety policy
input/output/token/time/resource budgets
retry error policy ref/digest
quality/loss/anchor evidence contract
~~~

首版profile：

| Profile | Binding | Purpose |
|---|---|---|
| ocr.tesseract.default/1 | tesseract + eng/chi_sim + OEM1/PSM3 + TSV/hOCR/text schemas | clean.ocr.local |
| vision.clean.gemini/1 | gemini-3.6-flash + clean.vision.extract/1 + strict clean response schema | clean.extract.vision |
| lsrag.structurize.window/1 | gemini-3.6-flash + exact window Prompt + structure-proposal schema/budgets | lsrag.structurize window plan |
| lsrag.structurize.merge/1 | gemini-3.6-flash + exact merge Prompt + structure-proposal schema/budgets | lsrag.structurize global merge |
| lsrag.construct.summary/1 | gemini-3.6-flash + exact summary Prompt + summary-proposal schema/budgets | lsrag.construct summaries |
| lsrag.extension.repair/1 | gemini-3.6-flash + exact repair Prompt + repair schema + one-pass policy | lsrag.construct extension repair |

Workflow/source definition引用exact profile；Execution binding复制所有component refs/digests。Profile governance变化只影响未来binding；retry/resume/recovery/reclean不resolve registry。

Embedding不伪装为generative InferenceProfile：ES-07 embedding_spaces是model+dimension+metric+document/query recipe的唯一兼容边界，vector.embed manifest直接绑定其exact ref/digest。ES-05只验证该space引用的gemini-embedding-2 ModelDefinition、Gemini adapter capability与input/output schemas存在且digest匹配。

### 4.6 Inference execution pipeline

~~~text
current-fenced ProcessCommand
  → validate capability/profile/input refs against immutable Execution binding
  → resolve exact schema/model/prompt/profile; digest compare
  → open verified input objects; enforce bytes/media/count budgets
  → render prompt deterministically; store request-manifest digest
  → ES-04 UoW append GenerationInvocation reservation
  → resolve secret or local executable just-in-time
  → exactly one adapter execution/network send outside DB transaction
  → persist raw output/evidence bytes first through ES-04 object store
  → local parse + strict schema + purpose semantic/source guard
  → append one InvocationOutcome with token/error/evidence refs
  → return typed InferenceOutcome to owning Process handler
  → ES-03/06 creates candidate/artifact/validation proof
  → ES-02 accepts ProcessOutcome and owns retry/route
~~~

Adapter success与domain validation分账。Provider schema-valid只说明JSON shape候选；clean需要ES-03 anchors/loss/quality/preflight，LS-RAG需要ES-06 kernel/extension/semantic/source proof full validation。

OCR是local adapter execution，不消耗provider token，但仍产生engine invocation evidence；T-O-77要求的GenerationInvocation严格覆盖generative/vision model calls。为统一lineage，本文件也使用同一ledger记录OCR并以`usage_known=null, token counts=null, accounting_kind=not_applicable`区分，不能伪写0 tokens。

### 4.7 Invocation durability 与 call accounting

#### 4.7.1 Reserve-before-call

每次可能产生真实provider计费/输出的send之前，必须先commit immutable`generation_invocations`：exact Process fence、purpose、profile/model/prompt/schema refs/digests、ordered input refs/digests、rendered request manifest digest、invocation ordinal、deadline与causation。Commit失败则禁止send。

同一`process_uuid + fencing_generation + invocation_ordinal`最多一个reservation。Adapter transport不得内部retry；每个send必须有新ordinal/new invocation UUID。ES-02 Process retry_count不是Invocation identity。

#### 4.7.2 One immutable outcome

每个Invocation最多一条`generation_invocation_outcomes`：

| outcome_kind | 含义 | Process disposition |
|---|---|---|
| succeeded | transport/provider/raw output/local parse均完成；仍需domain validation | handler继续domain validation |
| rejected | provider safety/content/policy明确拒绝，无可用output | manifest policy通常non-retryable或Gate evidence |
| failed | 已知未得到valid provider output；typed error | 按allowlisted error retryable/nonretryable |
| indeterminate | timeout/disconnect/crash使send/charge/result不可确认 | retryable only byES-02；新Invocation，保留可能重复成本证据 |

Token usage必须有`usage_known`。Known时prompt/completion/total按provider原值并校验非负/关系；unknown时counts全null，不得`?? 0`。Local OCR使用`accounting_kind=not_applicable`且counts null。Cost estimate是ES-08 metric/projection，不是billing truth。

#### 4.7.3 Crash without outcome

Scanner发现reservation超过deadline+60秒且无outcome时：

1. 验证Process fence已失效或无active adapter call；
2. append `indeterminate` outcome和safe recovery evidence；
3. 通过ES-02 owner port提交typed retryable failure；
4. 绝不把旧Invocation改为success、复用latest profile或覆盖成本记录。

如果同一进程仍持current fence且transport明确未send，可写`failed/not_dispatched`；必须有transport hook evidence，不能靠日志猜测。

### 4.8 Registry bootstrap / governance

Registration pipeline：

~~~text
load signed-in-build finite registry bundle
  → canonicalize/sort definitions and children
  → strict self-schema + digest validation
  → schema reference closure and provider-schema projection check
  → capability handler/signature/port/proof/error/resource check
  → model adapter/capability/limit/tool-policy check
  → prompt variable/render/output-schema check
  → profile component/purpose/budget compatibility check
  → Workflow/source/validator/Structure consumer handshake
  → one ES-04 registry install UoW
  → same bundle version+digest no-op; different digest fail
~~~

Production startup只做静态、本地、无provider I/O的readiness validation。Golden/evaluation fixtures在CI/release evidence运行；startup不发模型请求、不执行OCR、不做shadow/canary或全局AI health StateFamily。

Governance facts有限为`enabled/deprecated/disabled`，单向：

~~~text
enabled → deprecated → disabled
enabled ──────────────→ disabled
~~~

Definition content永远immutable；governance transition append event/ledger且不改变definition digest。Deprecated/disabled definition仍可读取历史。Provider临时不可用是operational readiness/metric，不改变registry status。

---

## 5. Contracts and Data

### 5.1 总体 schema 规则

ES-05全部18张业务/registry表遵守ES-04 physical profile：UUIDv7、UTC RFC3339、64 lower-hex SHA-256、canonical JSON object、STRICT、team复合fence、`ON DELETE RESTRICT`与非空`payload_extra`。Global code-owned definitions不带Team data；Invocation及其inputs/outputs/outcome必须team-owned。

Definitions的`definition_digest/manifest_digest/profile_digest`不包含mutable governance status/transition time，但覆盖全部语义字段与child rows。Status只能由RegistryOwner UoW按§4.8单向变化并append domain event；同key/version的语义列永远不能UPDATE。

所有logical object handle均须以ES-04 object reference ledger保护：schema/prompt/model evidence使用`registry_definition_payload` purpose；Invocation input/output使用`generation_invocation_input/output` purpose。只保存handle而无reference不算有效definition/outcome。

### 5.2 Process capability registry：6 tables

#### 5.2.1 process_capability_manifests

| Column group | Exact columns / constraints |
|---|---|
| Identity | process_key、contract_version composite PK；manifest_digest unique by key |
| Handler | handler_key、handler_version、handler_implementation_digest |
| Runtime | allowed_phase_set_ref/digest、outcome_schema_key/version/digest、proof_kind、proof_schema_key/version/digest |
| Semantics | side_effect_class、idempotency_recipe_key/version/digest |
| Governance | registry_status、registered_at、registration_origin、deprecated_at、disabled_at |
| Extension | payload_extra immutable except governance UoW round-trip |

~~~text
side_effect_class IN pure/idempotent_by_key/transactional_sink/non_replayable
registry_status IN enabled/deprecated/disabled
UNIQUE(process_key, contract_version, manifest_digest)
same key/version different manifest_digest = readiness failure
~~~

`allowed_phase_set_digest`由§5.2.2的sorted rows计算，只可包含ES-02 finite registry值，不得引入新phase。

#### 5.2.2 process_capability_phases

~~~text
process_key, contract_version FK manifest
phase_key
phase_ordinal INTEGER >=0
phase_binding_digest
payload_extra
PK(process_key, contract_version, phase_key)
UNIQUE(process_key, contract_version, phase_ordinal)
~~~

每个phase_key必须存在于ES-02 canonical phase registry；handler不能声明或动态返回新phase。

#### 5.2.3 process_capability_ports

~~~text
process_key, contract_version FK manifest
direction CHECK(input|output)
port_name
value_kind
schema_key, schema_version, schema_digest nullable only scalar/ref kind
required boolean
multiplicity CHECK(one|many)
ordinal >=0
port_digest
payload_extra
PK(process_key, contract_version, direction, port_name)
UNIQUE(process_key, contract_version, direction, ordinal)
~~~

Value kind固定为typed_scalar、logical_ref、object_ref、typed_object、proof_ref；无bytes、path、secret、arbitrary_json。

#### 5.2.4 process_capability_parameters

~~~text
process_key, contract_version FK manifest
parameter_name
value_kind
schema_key/version/digest nullable
required boolean
has_default boolean
default_text/integer/real/boolean/ref exactly one when has_default
minimum/maximum numeric nullable
allowed_set_ref/digest nullable
parameter_digest
payload_extra
PK(process_key, contract_version, parameter_name)
~~~

Parameter只接受compiler从Workflow/Profile解析的typed值；ProcessCommand caller不能覆盖。Secret value不是parameter，只能是registered secret slot ref。

#### 5.2.5 process_capability_error_policies

~~~text
process_key, contract_version FK manifest
error_class
error_code
retryability CHECK(retryable|non_retryable|indeterminate)
safe_for_replay boolean
requires_recovery_check boolean
failure_disposition
policy_digest
payload_extra
PK(process_key, contract_version, error_class, error_code)
~~~

Unknown error默认`indeterminate + not safe for replay`，不得以generic transient fallback重试。ES-02将policy snapshot写入Process spec；本表不推进Process。

#### 5.2.6 process_capability_resource_access

~~~text
process_key, contract_version FK manifest
access_ordinal >=0
resource_kind
operation CHECK(read|append|cas|publish|release)
purpose_key
required boolean
access_digest
payload_extra
PK(process_key, contract_version, access_ordinal)
UNIQUE(process_key, contract_version, resource_kind, operation, purpose_key)
~~~

Resource kind为closed registry中的Task-context、Intake、Generation、Vector/Index或Object purpose；不接受table、path、URL、secret或generic repository权限。

### 5.3 Schema registry：3 tables

#### 5.3.1 schema_definitions

~~~text
schema_key TEXT
schema_version TEXT
schema_kind CHECK(process_input|process_output|proof|prompt_variables|inference_response|structure|retrieval_internal)
dialect CHECK(mkb-json-schema-2020-12-subset-v1)
schema_object_handle TEXT
schema_content_digest TEXT(64 lower hex)
canonicalization_key/version/digest
validator_key/version/implementation_digest
max_depth, max_properties, max_array_items, max_string_bytes INTEGER >0
semantic_owner_key TEXT
definition_digest TEXT(64 lower hex)
registry_status CHECK(enabled|deprecated|disabled)
registered_at, deprecated_at nullable, disabled_at nullable
registration_origin CHECK(code|migration|bootstrap)
payload_extra TEXT canonical object
PK(schema_key, schema_version)
UNIQUE(schema_key, definition_digest)
~~~

Schema object immutable、root必须object且闭合unknown fields。`semantic_owner_key`只能是现有ES domain key，不提供外部namespace。Same version异digest fail readiness。

#### 5.3.2 schema_definition_components

~~~text
schema_key, schema_version FK schema_definitions
component_role CHECK(shape|deterministic_kernel|governed_extension|semantic_validator|source_proof|provider_projection)
component_ordinal >=0
component_ref_kind CHECK(schema|validator_manifest|proof_contract|object)
component_key, component_version, component_digest
required boolean
component_set_digest
payload_extra
PK(schema_key, schema_version, component_role, component_ordinal)
UNIQUE(schema_key, schema_version, component_role, component_key, component_version)
~~~

`structure` definition恰有shape/kernel/extension/semantic_validator/source_proof required components；provider_projection可按model adapter多条存在。非structure schema不得伪造kernel/extension语义。

#### 5.3.3 schema_consumer_support

~~~text
consumer_key, consumer_version
consumer_implementation_digest
schema_kind
schema_key, schema_version, schema_digest FK exact definition
support_mode CHECK(produce|consume|validate|project)
compatibility_contract_ref/digest
declared_at
payload_extra
PK(consumer_key, consumer_version, schema_key, schema_version, support_mode)
~~~

ES-02 compiler/readiness要求所有producer→consumer edges存在exact declarations，且definition digest、mode与port兼容。Range/`>=version`/latest声明禁止；新增schema version必须新增support row。

### 5.4 Model registry：2 tables

#### 5.4.1 model_definitions

| Column group | Exact columns / constraints |
|---|---|
| Identity | model_key、model_version PK；definition_digest |
| Adapter | adapter_key/version/implementation_digest；provider_kind=local_tesseract/google_gemini |
| Exact implementation | provider_model_id nullable external；binary_version/build_digest nullable local；model_metadata_ref/digest |
| Limits | max_input_bytes、max_input_items、max_context_tokens nullable、max_output_tokens nullable、max_concurrency |
| Policy | determinism_class、tool_policy=none、token_accounting_kind、secret_slot_schema_ref/digest nullable、egress_policy_ref/digest nullable |
| Lifecycle evidence | provider_stage、observed_at、deprecation_evidence_ref/digest nullable |
| Governance | registry_status、registered/deprecated/disabled times、origin |
| Extension | payload_extra |

~~~text
local_tesseract => provider_model_id/secret/egress null; binary fields required
google_gemini => exact provider_model_id/secret/egress required; binary fields null
provider_stage IN local_pinned/stable
registry_status IN enabled/deprecated/disabled
UNIQUE(model_key, definition_digest)
~~~

No preview/latest/experimental provider_stage。Model metadata snapshot只作注册证据，不作为runtime dynamic resolver。

#### 5.4.2 model_capabilities

~~~text
model_key, model_version FK model_definitions
capability_key CHECK(ocr|generate_structured|vision_structured|pdf_fragment_structured|embed_text)
input_modality CHECK(text|image|pdf_fragment)
output_modality CHECK(text|json|tsv|hocr|vector_internal)
provider_schema_subset_ref/digest nullable external structured
capability_limits_ref/digest
capability_digest
payload_extra
PK(model_key, model_version, capability_key, input_modality, output_modality)
~~~

Tesseract至少注册image→text/tsv/hocr；gemini-3.6-flash注册text/image/pdf_fragment→json；gemini-embedding-2只注册text→vector_internal，capability limits固定ES-07 dimension/recipe compatibility。Audio、video、image generation、tools与chat不在本表v1 allowlist。vector_internal绝不能被external/public schema consumer引用。

### 5.5 Prompt registry：2 tables

#### 5.5.1 prompt_definitions

~~~text
prompt_key TEXT
prompt_version TEXT
template_grammar CHECK(mkb-prompt-template-v1)
system_template_object_handle TEXT
template_content_digest TEXT(64 lower hex)
variable_schema_key/version/digest FK exact schema
allowed_purpose_key
allowed_process_key/contract_version
input_part_contract_ref/digest
output_schema_key/version/digest FK exact schema
safety_instruction_ref/digest
tool_policy CHECK(none)
evaluation_fixture_set_ref/digest
definition_digest TEXT(64 lower hex)
registry_status CHECK(enabled|deprecated|disabled)
registered_at, deprecated_at nullable, disabled_at nullable
registration_origin CHECK(code|migration|bootstrap)
payload_extra
PK(prompt_key, prompt_version)
UNIQUE(prompt_key, definition_digest)
~~~

Template、variable/output schemas和fixture set共同进入definition digest。Prompt不含secret、tenant/team override、remote include或model ID；model由InferenceProfile绑定。

#### 5.5.2 prompt_variables

~~~text
prompt_key, prompt_version FK prompt_definitions
variable_name
value_kind CHECK(text|integer|boolean|enum|logical_ref_metadata)
required boolean
max_bytes nullable
allowed_set_ref/digest nullable
render_context CHECK(system_literal|metadata_literal)
ordinal >=0
variable_digest
payload_extra
PK(prompt_key, prompt_version, variable_name)
UNIQUE(prompt_key, prompt_version, ordinal)
~~~

Source正文、image/PDF bytes不作为variable；它们通过separate content part进入request manifest。所有variable必须在template恰好按contract出现，未声明placeholder使registration失败。

### 5.6 inference_profiles

~~~text
profile_key TEXT
profile_version TEXT
purpose_key TEXT
allowed_process_key, allowed_process_contract_version
model_key, model_version, model_digest FK exact model
prompt_key, prompt_version, prompt_digest nullable only local OCR
input_schema_key/version/digest
response_schema_key/version/digest
validator_key/version/implementation_digest
provider_schema_projection_ref/digest nullable local
parameter_set_ref/digest
tool_policy CHECK(none)
safety_policy_ref/digest nullable external
input_budget_bytes, input_item_limit, output_budget_bytes INTEGER >0
input_token_budget, output_token_budget INTEGER >0 nullable local
timeout_ms INTEGER >0
thinking_level CHECK(medium) nullable local
retry_error_policy_ref/digest
quality_contract_ref/digest
loss_contract_ref/digest
anchor_contract_ref/digest
profile_digest TEXT(64 lower hex)
registry_status CHECK(enabled|deprecated|disabled)
registered_at, deprecated_at nullable, disabled_at nullable
registration_origin
payload_extra
PK(profile_key, profile_version)
UNIQUE(profile_key, profile_digest)
~~~

`ocr.tesseract.default/1`：prompt/provider projection/token/thinking/safety均null；parameter set冻结OEM1/PSM3/languages及tessdata digests。`vision.clean.gemini/1`：所有external fields必填，input budget=8MiB、item limit=1、timeout默认120s、one candidate、tool none。

### 5.7 Invocation ledger：4 tables

#### 5.7.1 generation_invocations

| Column group | Exact columns / constraints |
|---|---|
| Identity | team_uuid、generation_invocation_uuid PK；invocation_kind、invocation_ordinal |
| Runtime owner | task_uuid、execution_uuid、process_uuid、fencing_generation、process_spec_digest |
| Binding | profile/model/prompt/input-schema/response-schema exact keys/versions/digests |
| Request | request_manifest_ref/digest、rendered_prompt_digest nullable OCR、input_set_digest |
| Provider/local | adapter key/version/digest、provider_request_idempotency_ref nullable、secret_slot_ref nullable |
| Budget | deadline_at、timeout_ms、input/output/token budgets |
| Causation | invocation_purpose、repair_of_artifact_uuid nullable、causation/correlation UUIDs |
| Time | reserved_at、dispatch_started_at nullable |
| Extension | payload_extra immutable |

~~~text
invocation_kind IN local_ocr/generation/vision_generation/extension_repair
UNIQUE(team_uuid, process_uuid, fencing_generation, invocation_ordinal)
UNIQUE(team_uuid, generation_invocation_uuid, request_manifest_digest)
dispatch_started_at may only move null→timestamp in guarded dispatch UoW
repair_of_artifact_uuid required only extension_repair
~~~

Invocation request在send前immutable。`dispatch_started_at`是transport handoff的monotonic fact，不是状态；set与outbox/event不需要跨network transaction。

#### 5.7.2 generation_invocation_inputs

~~~text
team_uuid, generation_invocation_uuid FK invocation
input_ordinal INTEGER >=0
input_role CHECK(source_text|source_image|source_pdf_fragment|schema|context|artifact_to_repair)
logical_object_handle
object_reference_uuid
media_type
content_digest TEXT(64 lower hex)
size_bytes INTEGER >=0
source_anchor_manifest_ref/digest nullable
redaction_policy_ref/digest
input_digest
payload_extra
PK(team_uuid, generation_invocation_uuid, input_ordinal)
~~~

Ordered inputs与request manifest完全一致；每个handle有live object reference、same team/owner/purpose。No URL、path、inline body或secret。

#### 5.7.3 generation_invocation_outputs

~~~text
team_uuid, generation_invocation_uuid FK invocation
output_ordinal INTEGER >=0
output_role CHECK(provider_response|parsed_primary|ocr_text|ocr_tsv|ocr_hocr|validation_report|safety_evidence)
logical_object_handle
object_reference_uuid
media_type
schema_key/version/digest nullable for opaque provider evidence
content_digest TEXT(64 lower hex)
size_bytes INTEGER >=0
output_digest
created_at
payload_extra
PK(team_uuid, generation_invocation_uuid, output_ordinal)
UNIQUE(team_uuid, generation_invocation_uuid, output_role)
~~~

Profile声明required output roles。OCR success必须有ocr_text/ocr_tsv/ocr_hocr；Gemini structured success必须有provider_response、parsed_primary和validation_report。Rejected/failed可保留provider_response/safety evidence，但不能有usable `parsed_primary`。

#### 5.7.4 generation_invocation_outcomes

| Column group | Exact columns / constraints |
|---|---|
| Identity | team_uuid+generation_invocation_uuid PK/FK；outcome_kind |
| Provider evidence | provider_request_id_hash nullable、provider_model_observed、finish_reason、安全/政策evidence ref/digest |
| Outputs | output_set_digest、primary_output_ordinal nullable；exact rows在generation_invocation_outputs |
| Validation | parse_verdict、schema_verdict、semantic_precheck_verdict、validation_evidence_ref/digest |
| Usage | accounting_kind、usage_known nullable、prompt/completion/total tokens nullable；provider_usage_ref/digest nullable |
| Error | error_class/code/message_safe/details_ref/digest、retryability |
| Timing | dispatch_completed_at、latency_ms、recorded_at |
| Integrity | outcome_digest、payload_extra |

~~~text
outcome_kind IN succeeded/rejected/failed/indeterminate
succeeded => profile-required output rows + primary ordinal + parse/schema passed + no error
rejected/failed/indeterminate => typed error; primary ordinal null
accounting_kind=provider_tokens AND usage_known=1 => token counts nonnull/nonnegative
accounting_kind=provider_tokens AND usage_known=0 => token counts all null
accounting_kind=not_applicable => local OCR, usage_known and all token counts null
UNIQUE(team_uuid, generation_invocation_uuid, outcome_digest)
~~~

Outcome immutable。`semantic_precheck_verdict=passed`只表示ES-05 purpose-level安全/contract precheck，不能替代ES-03 clean evidence/preflight或ES-06 full validation。

### 5.8 Internal contracts

#### 5.8.1 SchemaRefV1

~~~json
{
  "schema_key": "clean.vision.response",
  "schema_version": "1",
  "schema_digest": "<64-lower-hex>",
  "dialect": "mkb-json-schema-2020-12-subset-v1"
}
~~~

Ref缺任一字段无效；registry返回definition/content/component digests后consumer必须重新比对。禁止`latest`、version range或只传key。

#### 5.8.2 InferenceCommandV1

~~~json
{
  "schema_version": "mkb.inference-command.v1",
  "identity": {
    "team_uuid": "...", "task_uuid": "...", "execution_uuid": "...",
    "process_uuid": "...", "fencing_generation": 3, "invocation_ordinal": 0
  },
  "purpose": "clean_vision",
  "binding": {
    "profile": {"key": "vision.clean.gemini", "version": "1", "digest": "..."},
    "model": {"key": "gemini-3.6-flash", "version": "1", "digest": "..."},
    "prompt": {"key": "clean.vision.extract", "version": "1", "digest": "..."},
    "input_schema": {"key": "...", "version": "1", "digest": "..."},
    "response_schema": {"key": "...", "version": "1", "digest": "..."}
  },
  "inputs": [{"ordinal": 0, "role": "source_image", "logical_ref": "...", "digest": "...", "size_bytes": 123}],
  "variables": {},
  "control": {"deadline_at": "...", "timeout_ms": 120000, "idempotency_key": "..."},
  "causation": {"trace_uuid": "...", "correlation_uuid": "...", "causation_uuid": "..."}
}
~~~

Command由handler从ProcessCommand+Execution binding构造，不来自public caller。它不含API key、provider URL、physical path、raw bytes、arbitrary parameters、route/next step或Task status。

#### 5.8.3 InferenceOutcomeV1

~~~text
schema_version = mkb.inference-outcome.v1
same identity + generation_invocation_uuid
outcome_kind
exact binding echo + request/outcome digests
typed output rows/refs/digests and primary output only when succeeded
parse/schema/semantic-precheck evidence
accounting_kind + usage_known + nullable token counts
typed provider/local error + retryability
timing + safe provider request-id hash
~~~

Handler只有在InvocationOutcome已commit后才能返回。ES-02 ProcessOutcome引用Invocation+evidence，不内嵌provider response或secret。

#### 5.8.4 RegistryBundleV1

Bundle固定包含sorted schema definitions/components/support、capability manifests/children、model definitions/capabilities、prompt definitions/variables和profiles，以及expected external Workflow/source/validator refs。Bundle header含schema version、bundle key/version/digest、application build digest、minimum DB migration、member counts/digests和registration origin。

Install是ES-04 `registry_bundle_install_v1` named UoW：all definitions/children/refs + registry_bundle_manifest + domain event全有或全无。Bundle不含secret、provider response、Team override或runtime pointer。

### 5.9 Application ports

~~~python
class CapabilityRegistryReadPort(Protocol):
    async def resolve_exact(self, ref: CapabilityRefV1) -> ProcessCapabilityManifestV1: ...
    async def validate_handler_set(self) -> CapabilityValidationReportV1: ...

class SchemaRegistryPort(Protocol):
    async def resolve_exact(self, ref: SchemaRefV1) -> SchemaDefinitionV1: ...
    async def assert_compatible(self, request: CompatibilityRequestV1) -> CompatibilityReceiptV1: ...
    async def validate(self, ref: SchemaRefV1, value_ref: LogicalObjectRefV1) -> SchemaValidationV1: ...

class ModelRegistryPort(Protocol):
    async def resolve_exact(self, ref: ModelRefV1) -> ModelDefinitionV1: ...

class PromptRegistryPort(Protocol):
    async def resolve_exact(self, ref: PromptRefV1) -> PromptDefinitionV1: ...
    async def render(self, command: PromptRenderCommandV1) -> RenderedPromptV1: ...

class InferenceProfileRegistryPort(Protocol):
    async def resolve_exact(self, ref: InferenceProfileRefV1) -> InferenceProfileV1: ...

class InferenceServicePort(Protocol):
    async def invoke(self, command: InferenceCommandV1) -> InferenceOutcomeV1: ...

class InvocationLedgerPort(Protocol):
    async def reserve(self, command: InvocationReservationV1) -> GenerationInvocationV1: ...
    async def mark_dispatched(self, command: InvocationDispatchV1) -> DispatchReceiptV1: ...
    async def append_outcome(self, outcome: InvocationOutcomeDraftV1) -> InferenceOutcomeV1: ...

class LocalOcrAdapterPort(Protocol):
    async def execute_once(self, request: LocalOcrRequestV1) -> LocalOcrAdapterResultV1: ...

class GenerativeAdapterPort(Protocol):
    async def execute_once(self, request: GenerativeRequestV1) -> GenerativeAdapterResultV1: ...

class RegistryBootstrapPort(Protocol):
    async def install(self, bundle: RegistryBundleV1) -> RegistryInstallReceiptV1: ...
    async def validate_readiness(self) -> RegistryReadinessReportV1: ...
~~~

没有generic `register(kind,json)`、dynamic import、provider factory、Prompt write port、raw SDK client或caller-configured inference port。Registry写面只接受compiled application bundle。

Adapter runtime必须注入ES-08-v1.0的exact `SecretPolicyPort`、`SafeEgressTransportPort`、`AdmissionPort`与`TelemetryPort`。Gemini SDK只能在`SafeEgressTransportPort`提供的fixed-host/no-proxy/no-retry transport boundary内发送；adapter不得读取secret文件、创建raw HTTP client、绕过semaphore或把telemetry当Invocation truth。Local OCR不使用egress，但同样经`AdmissionPort`取得bounded child slot。

### 5.10 Internal durable protocols

| Protocol/event | Producer → consumer | Exact guard |
|---|---|---|
| registry.bundle-installed.v1 | RegistryOwner → readiness/compiler | bundle version/digest + schema head |
| registry.definition-governance-changed.v1 | RegistryOwner → compiler/ops | exact kind/key/version + allowed edge |
| inference.invocation-reserved.v1 | InvocationLedger → adapter runner | current Process fence + request digest |
| inference.invocation-outcome-recorded.v1 | InvocationLedger → owning handler | same invocation/request/binding digest |
| inference.invocation-indeterminate.v1 | Recovery scanner → ES-02 owner | expired reservation + no outcome + fence evidence |
| registry.drift-detected.v1 | readiness → ES-08 | safe key/version/expected/actual digest only |
| model.deprecation-observed.v1 | release evidence → ops | model definition ref + official evidence；不切running binding |

消息通过ES-04 outbox/inbox；Invocation执行本身不由generic external queue触发。Outbox payload若引用registry/inference object必须有ES-04 reference。

---

## 6. State / Consistency / Failure

### 6.1 StateFamily boundary 与 factual automata

ES-05不新增StateFamily。Registry governance、Invocation dispatch/outcome、token、provider health都是typed fact：

#### 6.1.1 Definition governance fact

~~~text
enabled → deprecated → disabled
enabled ──────────────→ disabled
~~~

- Definition语义row与children始终immutable；只允许status/time projection按单向edge CAS；
- Deprecated只阻止新Workflow/profile binding，已绑定Execution仍可执行；
- Disabled阻止新binding与新invocation；已绑定Execution返回typed `binding-disabled`并由ES-02收敛，不换fallback；
- Provider health outage不是governance edge，恢复后相同exact binding可按ES-02 retry继续。

#### 6.1.2 Invocation facts

~~~text
no invocation
  ──reserve UoW──> immutable request, dispatch_started_at=null, no outcome
reserved
  ├──guarded mark dispatch + one call──> dispatch_started_at set
  └──proved not dispatched────────────> failed/not_dispatched outcome
dispatched, no outcome
  ├──verified response/parse──────────> succeeded outcome
  ├──explicit provider rejection─────> rejected outcome
  ├──known error/no usable output────> failed outcome
  └──ambiguous timeout/crash─────────> indeterminate outcome

one outcome is terminal and immutable for that Invocation
~~~

这个自动机由row presence/monotonic timestamp表达，不是私有retry状态。Retry属于Process，由ES-02新fence/ordinal创建新Invocation。

### 6.2 Binding 与 registry invariants

1. Workflow step、Process spec、Execution domain binding、InferenceCommand和Invocation必须携带同一exact capability/profile/model/prompt/schema refs/digests。
2. 同Execution retry/resume/recovery/Gate reclean不得resolve active/latest或读取mutable environment model alias。
3. Same key/version/different digest在registration/startup/runtime任何一处都fail-loud；不得以缓存旧值继续新binding。
4. Definition governance status不进入definition digest，但每次new binding必须读取并验证enabled；running binding读取exact content并按deprecated/disabled规则处理。
5. Schema producer、consumer与validator均须有exact compatibility row；missing range或digest mismatch在Workflow compile/readiness拒绝。
6. Provider schema投影只能等价或更窄，local MKB schema/semantic validator永远是authority。
7. Prompt render必须由exact template+variables产生唯一digest；source content作为separate input part，不受template parser解释。
8. Model/Prompt/profile upgrade只影响new WorkflowRevision/new Execution；不创建IntakeRevision、不重解释历史Invocation/Artifact。
9. Adapter每个real send恰一precommittedInvocation；SDK hidden retry、fallback或second candidate均为integrity failure。
10. Invocation outcome在raw output bytes持久化、digest验证和local parse后才能commit succeeded。
11. Usage unknown保存null；token/cost metric不能作为成功、retry或billing entitlement truth。
12. OCR/Vision output只是derived candidate；ES-03/06 owner验证通过前不能写canonical Revision/current pointer/publication。
13. Secret value只在adapter调用栈存在；DB只保存logical slot ref，safe evidence最多保存credential generation ref/digest。
14. Registry/API/Prompt/response中不得出现absolute path、provider key、raw authorization header、full source body或unknown executable code。
15. ES-05 scanner只提交typed recovery evidence给ES-02/08，不直写Process/Task/Artifact pointer。

### 6.3 Local OCR execution chain

~~~text
clean.ocr.local Process claimed/current-fenced
  → resolve exact ocr.tesseract.default/1 from Execution binding
  → validate binary 5.5.2 + build digest + tessdata manifest
  → open verified input image/page object
  → reserve local_ocr Invocation + input reference
  → create isolated bounded temp workspace
  → write verified input; spawn argv without shell
  → enforce deadline/CPU/memory/output bytes; capture exit/stderr safely
  → verify UTF-8 text + TSV + hOCR, coordinates/confidence/page bounds
  → store three output objects bytes-first
  → append succeeded/failed/indeterminate InvocationOutcome
  → ES-03 constructs CleanArtifactCandidate + loss/quality/anchor evidence
  → submit typed ProcessOutcome to ES-02
  → cleanup temp workspace; durable objects remain reference-governed
~~~

Nonzero exit、signal、timeout、missing output、invalid UTF-8/TSV/hOCR或coordinate越界均不能返回success。OCR低confidence是typed quality evidence；是否blocked由ES-03 preflight/profile决定，不由adapter自动换Vision。只有compiled Workflow已明确绑定OCR→quality decision→Vision Process时，才可走该有限route；它不是adapter fallback。

### 6.4 External Gemini execution chain

~~~text
clean.extract.vision or ES-06 model Process claimed/current-fenced
  → resolve exact profile/model/prompt/schema from immutable Execution binding
  → verify registry enabled/deprecated rule and adapter implementation digest
  → open/verify exact input object(s), media and 8MiB hard budget
  → render prompt + provider schema projection; canonical request manifest
  → reserve Invocation + ordered input rows + references in one UoW
  → resolve Gemini credential slot via ES-08 SecretPolicyPort
  → guarded dispatch_started_at UoW
  → exactly one SDK transport send, no tools/files/retry
  → classify HTTP/provider/safety/finish response
  → persist raw candidate + usage/safety evidence objects bytes-first
  → parse one JSON object; local jsonschema + purpose precheck
  → persist canonical parsed object/validation evidence
  → append immutable InvocationOutcome
  → return typed result to ES-03/06; clear credential/request buffers
~~~

Response中model name必须与definition允许的observed ID一致；provider silently serving其他ID、multiple candidates、tool call、non-JSON trailing text、unsupported schema behavior或usage inconsistency均fail-loud。Provider response body不进入exception/log；只保存受控object和safe digest/ref。

### 6.5 Invocation crash / ambiguity matrix

| Crash / failure window | Durable truth | Recovery / disposition | Forbidden |
|---|---|---|---|
| registry resolve前 | none | Process按typed binding error失败 | fallback model/prompt |
| Invocation reserve前 | none | safe same Process attempt retry before send | network call |
| reserve commit后、dispatch mark前 | request exists、no dispatch evidence | current runner可mark+send；expired且proved unsent写failed | 直接删row |
| dispatch mark commit后、send前crash | dispatched intent、actual send未知 | indeterminate after fence/deadline | 猜not sent、复用same invocation |
| request sent、response前timeout | possible charge/result | indeterminate，ES-02可新Invocation retry | adapter hidden retry |
| response收到、raw store前crash | result lost、call已发生 | indeterminate | 从日志重建output |
| raw object promote后、outcome前 | orphan/raw evidence object | recovery若有exact local transport spool+digest可finish；否则indeterminate，orphan retention | 假succeeded |
| outcome UoW中失败 | no outcome/reference commit | raw object orphan；same invocation outcome可在exact evidence下重试commit | second network send under same invocation |
| outcome commit后、handler response前 | full invocation truth | readback返回same outcome；handler/Process submission idempotent | duplicate outcome |
| Process fence lost during call | call may finish, stale Process | recordInvocation outcome/history，ES-02拒绝stale ProcessOutcome | 丢token记录或推进route |
| service hard kill | rows/objects survive | scanner按deadline/fence分类；no memory truth | 清空unfinished rows |

### 6.6 Validation / artifact / repair boundary

#### 6.6.1 Clean inference

Gemini/Tesseract output按以下顺序处理：transport → bytes/media → parse → ES-05 strict response schema → purpose precheck → ES-03 CleanArtifactCandidate anchors/loss/quality → item/root preflight → candidate acceptance。前层success不能越过后层；模型输出不进入RevisionFingerprint，除非source-grounded canonical semantics已由ES-03 exact definition/acceptance规则明确采纳并有source proof。

#### 6.6.2 LS-RAG generation

ES-06模型输出即使invalid，只要形成logical output也必须创建immutable GenerationArtifact并引用Invocation。Full validation顺序由ES-06固定为shape→binding→deterministic kernel→governed extension→semantic/source proof。只有full-valid artifact可CAS current；ES-05只提供exact inference/Schema evidence，不决定pointer。

#### 6.6.3 Governed extension repair

~~~text
invalid extension + exact StructureSchema says repair_allowed
  → ES-06 builds repair command with exact source artifact/digest
     + allowed JSON pointers + max one profile-bounded pass
  → ES-05 exact repair profile/model/prompt/schema Invocation
  → new output object + new GenerationArtifact + Invocation causation
  → ES-06 validates complete artifact from zero
  → full-valid may CAS current; invalid returns typed failure to ES-02
~~~

Kernel失败不调用repair。Repair response触碰kernel、未授权pointer或省略unchanged source proof立即invalid。ES-05没有repair loop；每个调用由ES-06 handler显式发起且受ES-02 Process control budget。

### 6.7 Failure taxonomy

| Error class / code family | Retryability | Evidence / behavior |
|---|---|---|
| REGISTRY_MISSING / VERSION_MISMATCH / DIGEST_DRIFT | non-retryable integrity | readiness/Process fail；不fallback |
| REGISTRY_DEPRECATED | allowed existing only | metric/evidence；new binding reject |
| REGISTRY_DISABLED | non-retryable | invocation不send；existing Process fail |
| SCHEMA_UNSUPPORTED / PROJECTION_NOT_EQUIVALENT | non-retryable contract | registration/compile fail |
| PROMPT_VARIABLE_INVALID / RENDER_DIGEST_MISMATCH | non-retryable integrity | noInvocation/send if detected before reserve |
| INPUT_MISSING / DIGEST_MISMATCH / MEDIA_INVALID | non-retryable integrity | object incident/owner repair，no send |
| INPUT_BUDGET_EXCEEDED | non-retryable policy | no send，typed evidence |
| SECRET_UNAVAILABLE | retryable only if transient classified | no secret leakage；Invocation failed/not_dispatched if reserved |
| LOCAL_RESOURCE_EXHAUSTED | retryable | kill/cleanup local child，typed limits |
| OCR_INPUT_UNSUPPORTED / OUTPUT_INVALID | non-retryable | preserve engine evidence；no candidate success |
| PROVIDER_RATE_LIMIT / 429 | retryable | one call only；honor bounded retry-after viaES-02 next_retry |
| PROVIDER_5XX / NETWORK_CONNECT | retryable if known no response | one failed outcome |
| PROVIDER_TIMEOUT / DISCONNECT_AFTER_SEND | indeterminate | recordpossible charge；ES-02 decides retry |
| PROVIDER_AUTH / PERMISSION / MODEL_NOT_FOUND | non-retryable config | readiness/alert；no alternate model |
| PROVIDER_CONTENT_BLOCKED | non-retryable business/policy | rejected outcome；ES-03 may exposebounded Gate only if compiled policy allows |
| PROVIDER_MODEL_DRIFT / TOOL_CALL / MULTI_CANDIDATE | non-retryable integrity | fail-loud/quarantine evidence |
| RESPONSE_PARSE / RESPONSE_SCHEMA_INVALID | manifest-defined bounded retryable | raw output preserved；no coercion |
| SEMANTIC_PRECHECK_INVALID | non-retryable for same output | domain owner receives invalid evidence |
| USAGE_UNKNOWN | not an error alone | counts null；success may proceed ifoutput valid |

Unknown exceptions被映射为`INFERENCE_UNKNOWN/indeterminate/non-safe`，不得显示stack/provider body或默认retryable。

### 6.8 Concurrency / budgets / backpressure

- Global Gemini calls默认4、per Team默认2、per Process一次1；Local OCR默认2；由ES-08-v1.0 bounded semaphore实现且值进入profile/control snapshot；
- Admission先检查Process deadline、profile budget与queue capacity；等待concurrency不得持DB transaction、object stream或secret；
- Gemini input decoded bytes最大8MiB、one media item、rendered system prompt最大32KiB、variables总计8KiB、raw response最大4MiB、timeout120s；
- Tesseract单页input最大32MiB/100MP，output每kind最大64MiB、timeout90s；PDF必须由ES-03逐页解码，不让Tesseract/Gemini处理unbounded collection；
- Token budgets由profile+model limits取更小者；provider usage超预算是post-call policy incident且output不得被接受；
- Rate-limit retry-after由ES-02 `next_retry_at`有界处理，adapter不sleep/retry；
- Prompt/schema/model definition object可按exact digest进行只读内存cache；cache key必须含key/version/digest，drift清除并fail，不允许TTL latest refresh；
- Shutdown停止新Invocation reserve，等待bounded active adapters；到grace后terminate local child/cancel HTTP，尚无outcome者由scanner标indeterminate。

### 6.9 Cleanup / retention / recovery

1. Registry definitions与bundle被Workflow/Execution/Artifact/Invocation引用时不得物理删除；V1普通cleanup只可drop cache，不删definition。
2. GenerationInvocation request/outcome/token/error skeleton永久跟随Task/Generation history retention；raw model output可在ES-06 artifact/proof与retention允许后释放，但digest、usage、error、causation保留。
3. Prompt/schema object references在definition存在期间live；governance disabled不自动释放。
4. Temporary OCR/input/base64/provider buffers在adapter finally中清理；crash后ES-08 60秒workspace scanner只清理无live PID/reservation且满1小时的temp，不从temp恢复truth。
5. Invocation无outcome scanner只append可证明的failed/indeterminate outcome；不能重发network call或制造Artifact。
6. Provider deprecation scanner/CI只产生release evidence和future migration action；running Execution不自动切换。
7. Registry cache丢失可从DB+object registry exact重建；DB/object缺失则readiness fail，不从application defaults静默重seed覆盖。

---

## 7. Legacy Retain / Rewrite / Drop

| Legacy evidence | Retain | Rewrite in MKB | Drop |
|---|---|---|---|
| shared IAiProvider schemas | provider-neutral generate structured concept、typed usage | exact InferenceCommand/Outcome、schema/profile refs、usage_known | arbitrary body/metadata、responseText-only、unknown usage=0 |
| Gemini provider adapters | system instruction、multimodal、structured JSON、usage extraction | one stable model ID、one adapter、local validation、one call/Invocation | `gemini-*-latest`、model alias fallback、tools、raw response in exception |
| API key helper | secret来自environment binding的原则 | ES-08 logical secret slot、generation evidence、least privilege | comma-separated keys、module-global round robin、secret error text |
| Prompt KV/getPrompt | logical prompt key和separate system prompt | immutable code-owned PromptDefinition+digest+object ref | runtime KV latest、missing prompt fallback、hot reload |
| PromptManager | task→prompt purpose mapping、required variables | exact InferenceProfile/Workflow binding | tenant override、TTL cache、force refresh、generic fallback |
| console Prompt CRUD/playground | fixtures可帮助离线验证的需求 | source-controlled fixtures + CI evidence | UI、CRUD、deploy、playground、prompt product |
| action registry | explicit finite handler map、strict schema | versioned ProcessCapabilityManifest + code handler digest | dynamic action/plugin、branch-name routing、legacy alias |
| Tesseract/legacy OCR | local OCR capability与confidence/coordinate需求 | pinned binary+tessdata+profile、TSV/hOCR/text lineage | unversioned host binary、shell、plain text only、silent empty |
| Cloudflare AI Gateway metadata | trace/team attribution需求 | internal Invocation/trace/team lineage | Gateway/Worker binding、5-field platform limit、user/file SaaS identity |

Legacy只作ReferenceAnchor。新registry bundle、fixtures、model/prompt content、IDs与outputs全部greenfield；不复制legacy Prompt正文、KV key、model alias、provider request、token metadata或acceptance字节。

---

## 8. Acceptance Evidence

所有HARD项必须自动化。Provider-dependent tests使用受控Gemini test credential与固定fixture，记录model observed ID、SDK/adapter version、registry bundle/schema digest与Invocation refs；不能用mock替代最终provider contract evidence。CI可以使用recorded sanitized fixture做多数回归，但release gate必须有有限live canary。

### 8.1 Registry / schema

| ID | Level | Scenario | Required evidence |
|---|---|---|---|
| ES05-A001 | HARD | fresh registry install | 18表definitions/children/bundle一次原子安装，readiness true |
| ES05-A002 | HARD | second identical install | same bundle version/digest no-op，无duplicate/event drift |
| ES05-A003 | HARD | same version different digest | install/serve fail-loud，旧definition不变 |
| ES05-A004 | HARD | partial bundle fault | 每个insert fault均whole rollback，无half registry |
| ES05-A005 | HARD | definition immutability | semantic column update/delete无repository/SQL路径 |
| ES05-A006 | HARD | governance legal edges | enabled→deprecated/disabled、deprecated→disabled成功并留event |
| ES05-A007 | HARD | governance illegal edges | disabled/deprecated逆向或content修改CAS拒绝 |
| ES05-A008 | HARD | historical read | deprecated/disabled exact definition仍可按历史ref读取 |
| ES05-A009 | HARD | no latest resolver | code/schema/query无latest/version-range/active-model lookup |
| ES05-A010 | HARD | schema subset meta-validation | remote ref/dynamic/executable/unbounded/unknown root被拒绝 |
| ES05-A011 | HARD | strict unknown fields | every representative instance额外字段均local reject |
| ES05-A012 | HARD | canonical schema digest | key order/whitespace等价，semantic change digest不同 |
| ES05-A013 | HARD | provider projection equivalence | required/type/enum被弱化时registration失败 |
| ES05-A014 | HARD | structure components | missing shape/kernel/extension/semantic/source-proof任一拒绝 |
| ES05-A015 | HARD | exact consumer support | missing/different schema version/digest compile readiness失败 |
| ES05-A016 | HARD | no range compatibility | `>=`、wildcard、fallback consumer declaration strict reject |
| ES05-A017 | HARD | object reference closure | schema/prompt/evidence handle无live reference不能register/readiness |
| ES05-A018 | HARD | payload_extra discipline | 18表均round-trip；未晋升key不影响resolve/render/validation |
| ES05-A019 | HARD | Team boundary | global definitions无Team data；Invocation inputs/outcomes跨Team FK拒绝 |
| ES05-A020 | HARD | registry startup no I/O | readiness不调用provider/OCR/network，不生成Invocation |

### 8.2 Capability / binding / Prompt

| ID | Level | Scenario | Required evidence |
|---|---|---|---|
| ES05-A021 | HARD | ES-03 catalog completeness | exactly 18 process keys，与ES-03列表set-equal，无alias |
| ES05-A022 | HARD | manifest child digest | port/parameter/error/resource任一变化改变manifest digest |
| ES05-A023 | HARD | handler existence/signature | missing handler或typed signature drift使readiness false |
| ES05-A024 | HARD | phase/proof compatibility | illegal phase、missing proof或Outcome schema compile失败 |
| ES05-A025 | HARD | resource least privilege | handler请求未登记resource/operation被拒绝 |
| ES05-A026 | HARD | unknown error policy | maps to indeterminate/non-safe，不自动retry |
| ES05-A027 | HARD | deprecated capability | no newWorkflow registration；old exact Execution仍resolve |
| ES05-A028 | HARD | disabled capability | no newbinding/invocation；oldExecution typed fail，无fallback |
| ES05-A029 | HARD | Execution exact binding | Process/Profile/Model/Prompt/Schema refs/digests全部相等 |
| ES05-A030 | HARD | retry after registry upgrade | oldExecution继续旧binding，新Execution可用newversion |
| ES05-A031 | HARD | same-version runtime drift | cache/DB/object任一digest不符立即fail，不用cached/latest |
| ES05-A032 | HARD | prompt variable validation | missing/extra/wrong-type/oversize变量在Invocation前拒绝 |
| ES05-A033 | HARD | prompt grammar | condition/loop/include/expression/function/unknown placeholder拒绝 |
| ES05-A034 | HARD | source part separation | source正文不被template解析或记录为Prompt variable |
| ES05-A035 | HARD | deterministic render | same template+variables产生same bytes/digest |
| ES05-A036 | HARD | no generic fallback | prompt/model/schema missing时无default prompt/model/coercion |

### 8.3 Local OCR adapter

| ID | Level | Scenario | Required evidence |
|---|---|---|---|
| ES05-A037 | HARD | binary identity | exact Tesseract 5.5.2/build digest，不匹配readiness false |
| ES05-A038 | HARD | tessdata identity | eng/chi_sim files与manifest digest exact，missing/drift fail |
| ES05-A039 | HARD | argv/no shell | injection filename/metadata不能改变argv或执行shell |
| ES05-A040 | HARD | verified input | missing/corrupt/wrong media/budget input不spawn OCR |
| ES05-A041 | HARD | three outputs | validfixture产生text+TSV+hOCR logical objects及refs/digests |
| ES05-A042 | HARD | coordinate/confidence | word/page bounds、ordinal、confidence schema/quality evidence正确 |
| ES05-A043 | HARD | bilingual fixture | registered eng/chi_sim pages产生可追溯text/anchors，不silent empty |
| ES05-A044 | HARD | unsupported language/profile | strict binding failure，不猜language或换Vision |
| ES05-A045 | HARD | nonzero/invalid output | typed failed outcome，无CleanArtifactCandidate success |
| ES05-A046 | HARD | timeout/resource limit | child terminated、temp清理、typed retryability evidence |
| ES05-A047 | HARD | OCR accounting | usage_known null/accounting not_applicable/token counts null |
| ES05-A048 | HARD | no automatic fallback | low confidence只留quality fact；route only ifWorkflow precompiled |

### 8.4 Gemini adapter

| ID | Level | Scenario | Required evidence |
|---|---|---|---|
| ES05-A049 | HARD | exact dependency/model | google-genai 2.13.0 + gemini-3.6-flash stable exact |
| ES05-A050 | HARD | latest/preview rejected | alias、preview、experimental model definition不能register |
| ES05-A051 | HARD | tools/files disabled | request无tools/search/code/function/URL context/Files API |
| ES05-A052 | HARD | fixed parameters | one candidate、medium thinking、no deprecated sampling/caller override |
| ES05-A053 | HARD | one send per Invocation | transport instrumentation证明无SDK/internal retry |
| ES05-A054 | HARD | secret safety | credential仅`SecretPolicyPort`临时解析，不在DB/command/log/error/object |
| ES05-A055 | HARD | bounded inline image | valid≤8MiB image structured response成功并留source digest |
| ES05-A056 | HARD | bounded PDF fragment | exact fragment成功；full/unbounded PDF被ES-03/profile挡住 |
| ES05-A057 | HARD | input budget | oversized/multiple media在reserve/send前拒绝 |
| ES05-A058 | HARD | structured output | provider JSON后仍经jsonschema/local purpose validation |
| ES05-A059 | HARD | trailing/non-JSON output | raw evidence保存，failed outcome，无coercion/JSON scraping |
| ES05-A060 | HARD | schema-shaped semantic lie | local/source validation阻断downstream success |
| ES05-A061 | HARD | content block | rejected outcome+safe evidence；无empty success |
| ES05-A062 | HARD | 429/5xx | adapter不retry；typed policy交ES-02，one Invocation |
| ES05-A063 | HARD | timeout/disconnect | indeterminate、usage null、possible charge evidence |
| ES05-A064 | HARD | provider model drift/tool call | nonretryable integrity failure，no output acceptance |
| ES05-A065 | HARD | usage known | exact nonnegative counts/total relation持久化，不从text估算 |
| ES05-A066 | HARD | usage absent | usage_known false、counts null，不写0 |

### 8.5 Invocation / failure / repair

| ID | Level | Scenario | Required evidence |
|---|---|---|---|
| ES05-A067 | HARD | reserve-before-call | DB reserve fault时transport send count=0 |
| ES05-A068 | HARD | reservation idempotency | same Process/fence/ordinal same digest返回sameInvocation |
| ES05-A069 | HARD | reservation conflict | same identity different request digest拒绝、no send |
| ES05-A070 | HARD | dispatch-before-send | every observed network/local execution hasdispatch timestamp |
| ES05-A071 | HARD | one immutable outcome | duplicate same digest readback，different digest conflict |
| ES05-A072 | HARD | crash sweep | §6.5每个window收敛为no call、known outcome或indeterminate |
| ES05-A073 | HARD | raw-store rollback | outcome不成功，object为orphan且无downstream Artifact |
| ES05-A074 | HARD | outcome response loss | readback returns same outcome，no second provider call |
| ES05-A075 | HARD | stale Process fence | Invocation历史保留，ES-02拒绝stale Outcome/route |
| ES05-A076 | HARD | scanner unknown call | expired dispatched/no-outcome append indeterminate，不重发 |
| ES05-A077 | HARD | proved not dispatched | only transport proof允许failed/not_dispatched |
| ES05-A078 | HARD | model upgrade and Revision | model/profile变化不创建IntakeRevision |
| ES05-A079 | HARD | invalid generation history | ES-06 retains Artifact+Invocation but current pointer不切 |
| ES05-A080 | HARD | kernel repair forbidden | kernel failure transport call count forrepair=0 |
| ES05-A081 | HARD | extension repair | onlyallowed pointers、newInvocation/newArtifact、full revalidation |
| ES05-A082 | HARD | repair/retry exhaustion | no private loop/fallback/schema loosening；ES-02 Processfailed |

### 8.6 Architecture / scope / replacement

| ID | Level | Scenario | Required evidence |
|---|---|---|---|
| ES05-A083 | HARD | domain dependency | domain/application无SDK/subprocess/path/secret/Turso import |
| ES05-A084 | HARD | finite adapters | runtime只有Tesseract与Gemini adapter，无dynamic provider factory |
| ES05-A085 | HARD | no public registry/inference API | route/OpenAPI/ports无Model/Prompt/Schema CUD、chat/completion |
| ES05-A086 | HARD | no legacy dependency | 无KV Prompt、Cloudflare Gateway、legacy alias/schema/wire/import |
| ES05-A087 | HARD | generative/vision provider replacement compile | new exact model/profile + newWorkflow可通过sameProcess contract |
| ES05-A088 | HARD | old execution isolation | replacement后oldExecution不切换且历史仍按旧refs解释 |
| ES05-A089 | HARD | bounded concurrency | global/team/process limits与queue saturation fail/backpressure可证 |
| ES05-A090 | HARD | safe evidence scan | secret/path/body/raw provider response/stack不进日志/error/event |
| ES05-A091 | HARD | ES-06 capability set | exactly 2 LS-RAG keys，与ES-02/06 set-equal，无repair/coarse alias |
| ES05-A092 | HARD | LS-RAG manifest binding | exact schema/Prompt/Profile/input/output/proof/error/resource rows可compile |
| ES05-A093 | HARD | StructureSchema components | `lsrag.structure/1` exactly 8 components + kernel/extension/validator digests |
| ES05-A094 | HARD | StructureSchema drift | missing/extra/same-version-different digest使readiness false |
| ES05-A095 | HARD | LS-RAG Prompt set | exactly window/merge/summary/repair四项，无generic/caller override |
| ES05-A096 | HARD | LS-RAG Profile set | four exact Gemini bindings、one candidate、zero adapter retry |
| ES05-A097 | HARD | construct repair budget | optional once仅由ES-06extension finding触发；kernel call count 0 |
| ES05-A098 | HARD | old LS-RAG Execution isolation | registry升级后仍解析command exact refs，不切latest |
| ES05-A099 | HARD | ES-07 capability set | exactly 6 vector/index keys，与ES-02/07 set-equal，无coarse/vector CRUD alias |
| ES05-A100 | HARD | ES-07 manifest binding | exact command/output/proof/side-effect/error/resource rows compile |
| ES05-A101 | HARD | embedding ModelDefinition | gemini-embedding-2 stable exact ID、adapter/dimension capability digest |
| ES05-A102 | HARD | Gemini embedding adapter | 1..16独立text Content、dimension768、automatic retry0 |
| ES05-A103 | HARD | EmbeddingSpace compatibility | model/space/recipe/schema refs exact；same-version drift readiness false |
| ES05-A104 | HARD | ES-07 schema set | exactly 15 keys，missing/extra/different digest fail readiness |
| ES05-A105 | HARD | schema visibility | vector outcome只允许internal consumer；public result forbids raw vector/model/path |
| ES05-A106 | HARD | projection consumer support | ES-07 consume exact ES-06 projection schema/digest |
| ES05-A107 | HARD | embedding ledger ownership | GenerationInvocation新增0；每个call由ES-07 EmbeddingInvocation记录 |
| ES05-A108 | HARD | provider wrong count/dimension/nonfinite | typed rejected outcome，无fallback/coercion |
| ES05-A109 | HARD | total Process registry | exact 26 manifests，ES-03/06/07分组set-equal |
| ES05-A110 | HARD | old execution/release isolation | registry新增embedding定义不改变既有exact bindings |

### 8.7 Evidence bundle

ES-05 evidence bundle固定包含：

1. 18-table schema/constraint/index manifest和ES-04 physical mapping；
2. registry bundle determinism、drift、governance与reference closure报告；
3. 18个ES-03 + 2个ES-06 + 6个ES-07 Process manifest set/port/proof/handler compatibility report；
4. schema meta-validation、`lsrag.structure/1` 8-component closure、provider projection equivalence与consumer handshake report；
5. Prompt grammar/render/injection/golden fixture与四套LS-RAG Prompt/Profile exact-set报告；
6. Tesseract binary/tessdata/fixture/limit/failure evidence；
7. Gemini GenerateContent/EmbedContent live canary、SDK/model/request/structured output/vector dimension/token evidence；
8. Invocation reserve/send/outcome/crash/recovery矩阵；
9. kernel/extension/no-fallback/no-hot-switch negative tests；
10. architecture、secret/path/body leak与zero-legacy-dependency scan。
11. ES-07 15-schema exact-set、EmbeddingSpace/model compatibility与public/internal consumer visibility report。

---

## 9. Remaining Technical Decisions and Defaults

### 9.1 已裁决 defaults

| Topic | v1 default | 改变默认值所需证据 |
|---|---|---|
| Local OCR | Tesseract 5.5.2, OEM1, PSM3 | 新binary+tessdata通过全部OCR/quality/regression evidence |
| OCR languages | eng + chi_sim exact traineddata digests | project-owned fixture与image/capacity证据；new profile version |
| External provider | Gemini Developer API only | 新provider不是V1内普通配置；未来需明确范围复审 |
| External model | stable gemini-3.6-flash explicit ID | deprecation/quality evidence + newModel/Profile/Workflow version |
| Embedding model | stable gemini-embedding-2 explicit ID；ES-07 dimension768 | new Model/EmbeddingSpace + full reembed/retrieval regression |
| SDK | google-genai 2.13.0 exact pin | dependency/API diff + allGemini/Invocation tests |
| Local JSON validator | jsonschema 4.26.0 Draft202012Validator + MKB subset precheck | validator conformance/diff + fullschema fixtures |
| Provider tools/files | all disabled | 本轮不开放；需要产品能力时foundational review |
| Sampling | none sent; medium thinking explicit; one candidate | model API/quality evidence + newProfile version |
| Adapter retries | zero | 不可改变；ES-02是唯一retry owner |
| Gemini input/output | 8MiB decoded / 4MiB raw output | memory/provider/quality benchmark，仍须bounded |
| Gemini timeout | 120s | latency/failure evidence + Process lease compatibility |
| OCR input/timeout | 32MiB or 100MP / 90s | fixture/resource benchmark |
| Concurrency | Gemini global4/team2/process1；OCR global2 | ES-08 measured envelope，不得无界 |
| Prompt grammar | literal + typed placeholders only | 新grammar需security/determinism proof，不开放code/include |
| No-outcome grace | deadline + 60s | transport/shutdown evidence；不能小于active-call ambiguity window |
| Registry evolution | append version + newWorkflow binding | definition immutability不可改变 |

### 9.2 下游既有槽位输入

| Input / status | Owner | ES-05处理 |
|---|---|---|
| StructureSchema exact bundle / `closed by ES-06-v1.0` | ES-06 | 已登记`lsrag.structure/1` exact 8 components、kernel/extension/validators/support |
| LS-RAG Prompt/Profile / `closed by ES-06-v1.0` | ES-06 | 已登记window/merge/summary/repair四套exact bundle，无新provider |
| LS-RAG Process manifests / `closed by ES-06-v1.0` | ES-06 | 已追加`lsrag.structurize/construct`并与ES-02 catalog校准 |
| Embedding model/space与vector/retrieval schemas / closed by ES-07-v1.0 | ES-07 | 已登记gemini-embedding-2、6 manifests、15 schemas与projection consumer support；embedding invocation仍由ES-07专属ledger裁决 |
| Secret/egress/dependency lock/concurrency/metrics / `closed by ES-08-v1.0` | ES-08 | read-only finite file slots；Gemini仅Google exact host:443；hash-locked image/dependencies；4/2/1与OCR2 semaphore；closed metrics/runbook，只能收紧 |

这些是当前8文件依赖顺序中的execution输入，不是owner问题。ES-06/07/08输入均已闭合；ES-08没有新增spec、service、StateFamily、adapter、provider或外部能力。

### 9.3 Rejected alternatives

| Alternative | Rejection |
|---|---|
| Generic OpenAI-compatible/model gateway | 扩大provider与语义矩阵，掩盖capability差异 |
| Multiple external providers/fallback chain | 同Execution可能换binding，成本/质量/历史不可解释 |
| `latest` model alias | provider可hot swap，直接违反exact binding |
| Preview/experimental model | 生命周期与contract不满足critical truth |
| Prompt KV/database editor/hot reload | 同version漂移、运行中换Prompt、引入产品/UI |
| Tenant prompt override | 引入上游业务/persona与组合爆炸 |
| Provider Files API | 新remote asset lifecycle/cleanup/retention；bounded inline pages已足够 |
| Tools/search/code/function calling | 增加agent行为和外部副作用，MKB无需 |
| SDK automatic retry | 每次真实call/token不可逐一入Invocation账，复制ES-02 retry |
| JSON scraping/coercion/schema loosening | 将invalid模型输出伪装为truth |
| Unknown usage=0 | 丢失成本/审计真相 |
| OCR low quality自动Vision fallback | 隐藏route/binding变化；只能由compiledWorkflow显式决定 |
| Invocation status StateFamily | reservation/outcome facts已充分，新增第七族违规 |
| Generic registry table + arbitrary kind | 形成开放平台/extension point，违背finite registry边界 |

### 9.4 Closure

ES-05没有需要owner回答的问题。Provider、model、Prompt grammar、schema validator、OCR/embedding engine、retry与budget均是OT03-C015明确下沉的executional选择。ES-06/07 exact definitions、ES-08 security/resource slots与最终cross-spec audit均已闭合，不改变产品边界或adapter上限。

---

## 10. Revision History

| 版本 | 日期 | 状态 | 变更 |
|---|---|---|---|
| ES-05-v0.1 | 2026-08-10 | internally-consistent / awaiting cross-spec audit | 冻结finite code-owned Capability/Schema/Model/Prompt/InferenceProfile registries、18个ES-03 manifest、Tesseract 5.5.2 local OCR、Gemini 3.6 Flash external structured inference、exact no-hot-switch binding、reserve-before-call GenerationInvocation与token/error/indeterminate账；提供18张逻辑表、ports/protocols、factual automata、执行链/故障矩阵与90项HARD acceptance。无新产品责任、public registry/inference能力、StateFamily、部署单元、dynamic provider/plugin或spec文件。 |
| ES-05-v0.2 | 2026-08-10 | internally-consistent / awaiting cross-spec audit | 接收ES-06-v0.1 exact registry输入：追加`lsrag.structurize/construct`两个manifest、`lsrag.structure/1`八component bundle、window/merge/summary/repair四套Prompt/Profile及8项acceptance，使当前manifest总数为20、acceptance为98；仍复用既有18张registry/Invocation表与Gemini adapter。未新增provider、产品API、StateFamily、服务或spec。 |
| ES-05-v0.3 | 2026-08-10 | internally-consistent / awaiting cross-spec audit | 接收ES-07-v0.1 exact registry输入：追加6个vector/index manifest、gemini-embedding-2 ModelDefinition/text→vector_internal capability、15项schema与ES-06 projection consumer support，使manifest总数26、acceptance 110；Gemini仍是同一adapter，embedding call由ES-07独立ledger持有，18张ES-05表不变。未新增provider、public raw-vector、StateFamily、服务或spec。 |
| ES-05-v1.0 | 2026-08-10 | ready | 完成OT-01..04、S03..06及ES-02/03/04/06/07/08最终对账；26个Process manifest、finite registry、exact inference/embedding binding、18张owner tables与110项HARD acceptance均已set-exact。未新增provider、plugin、public inference/vector能力、状态族、服务或spec文件。 |
