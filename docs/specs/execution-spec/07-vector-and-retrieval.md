# ES-07 — Vector and Retrieval

> **项目**：myknowledgebase（MKB）
>
> **文件 ID**：ES-07
>
> **文档性质**：execution-spec / implementation authority
>
> **版本 / 日期**：ES-07-v1.0 / 2026-08-10
>
> **文档状态**：ready
>
> **Truth 输入**：OT-01-v1.0、OT-02-v1.0、OT-03-v1.0、OT-04-v1.0
>
> **Baseline 输入**：D01-v1.4、D02-v1.0、S04-v1.2、S06 T-O-77..85；S08/S09/S10 没有 frozen 文件
>
> **上游 Execution Spec**：ES-01-v1.0、ES-02-v1.0、ES-03-v1.0、ES-04-v1.0、ES-05-v1.0、ES-06-v1.0
>
> **上游索引**：docs/specs/index.md

本文件是 MKB v1 embedding、VectorRecord、IndexGeneration、publication、eligibility、同步 semantic retrieval、original/summary traceback 与 deterministic rerank 的唯一 Execution Spec。它只消费 ES-06 已接受的 exact GenerationCommit 与 RetrievalBlockProjection，将其发布为 proof-valid serving knowledge，并通过 ES-01 已冻结的唯一 retrieval.search 入口返回 structured、grounded、traceable、reranked Retrieval Result。

本文件不提供 raw vector read/list/export、VectorRecord CRUD、caller-supplied query vector、generic vector database、final answer、chat、agent 或上游业务。Vector 是单体内部 substrate；公开结果只包含知识文本、source anchor、provenance、排名依据和 publication snapshot。

---

## 1. Inherited Truth

### 1.1 权威输入

| 来源 | ES-07 继承 | 不得改变 |
|---|---|---|
| OT-01-v1.0 | MKB只做knowledge处理、转换、存储和获取；一个Python应用/发布单元 | 不建设问答产品、内容产品、向量产品或额外服务 |
| OT-02-v1.0 | 六个且仅六个StateFamily；derived fact、pointer、proof与runtime state分账 | 不给EmbeddingInvocation、VectorRecord、IndexGeneration或query增加StateFamily |
| OT-03-v1.0 | 同步retrieval.search；LS-RAG双通道、Traceback、Reranker、结构化向量闭环；无raw vector | 不增加异步retrieval、raw-vector primitive、answer generation或公共index管理 |
| OT-04-v1.0 | proof-gated publication、双eligibility fence、代表性semantic usefulness是release gate | 不以vector ACK、文件、日志、latest或schema正确冒充成功 |
| D01-v1.4 | Process是leaf work；Execution/Process claim、retry、route归ES-02 | adapter和publisher不私建job/attempt/retry/callback状态 |
| D02-v1.0 | state/fact/pointer/proof正交；VectorRecord、IndexGeneration是derived identity/fact | generation phase、validation outcome和query receipt不进入状态族 |
| S04-v1.2 | latest/serving分离；proof-valid CAS；失败候选不污染旧serving；deactivate/delete逻辑先行 | 物理vector存在不能授予检索资格；reindex不得制造IntakeRevision |
| S06 T-O-77..85 | immutable generation/history、exact schema binding、full validation、统一retry | 不切latest猜输入，不修改S06 artifact，不放宽schema或私下repair |
| ES-01-v1.0 | 唯一POST retrieval:search；不创建Task/Audit/Execution/Process；caller不能选backend/model | ES-07只实现该route的read port与exact request/result |
| ES-02-v1.0 | 六个ES-07 Process key及既有Workflow route | Outcome不携带next step；所有retry/cancel/fence归engine |
| ES-03-v1.0 | Item lifecycle/latest/serving唯一owner；filter-only新Revision；PublicationProof后CAS | ES-07不直写Item truth，只参与named atomic UoW |
| ES-04-v1.0 | pyturso 0.7.0 embedded、单DB/单persistence lane、WAL/FULL、named UoW | 不引入Vectorize、Pinecone、Qdrant、第二DB或跨服务事务 |
| ES-05-v1.0 | code-owned registry、exact binding、无hidden retry、Gemini adapter substrate | embedding定义回填ES-05；调用事实由ES-07专属ledger持有 |
| ES-06-v1.0 | exact commit/projection、三类block/four strata、stable unit/pair/anchor coordinate | 不rechunk、不改original、不重写anchor、不枚举current猜输入 |

S08/S09/S10在旧baseline只有主题槽位而没有frozen truth文件。本文件只关闭OT-03/04和S04已经冻结的义务；旧QNA、legacy阈值、Cloudflare拓扑、Vectorize index和Contexter payload均不是authority。

### 1.2 Truth 到交付物映射

| Truth cluster | 本文件落点 |
|---|---|
| OT03-T004/T031/T032、OT03-C014/C016 | §4.8–4.12、§5.2 public request/result、无raw-vector面 |
| OT03-T021、OT04-T008/T019 | §4.4–4.7 generation/validation/publication/withdrawal |
| OT04-T009/T020/T023/T027 | §4.8–4.12 dual fence、traceback、rerank、empty/error |
| OT04-T035、OT04-C015 | §4.13、§8.8 finite semantic benchmark |
| S04-T015/T016/T023 | §4.6、§6.2/6.3 atomic serving/index CAS与query fence |
| S04-T021/T036/T037 | §4.7、§6.6 logical-first withdrawal与独立cleanup proof |
| ES06 exact projection | §4.2/4.3、§5.5–5.7 vector lineage与不可rechunk consumer |
| ES02 exact capability catalog | §4.5、§5.3 typed Process contracts |
| ES04 persistence profile | §4.1、§5.4–5.11 24 owner tables与named UoW |

### 1.3 唯一 ownership

| Concern | 唯一 owner | ES-07 interaction |
|---|---|---|
| HTTP auth/envelope、Task/Audit | ES-01 | ES-07实现RetrievalSearchPort；route不写Task/Audit |
| Workflow/Execution/Process、claim/retry/cancel/route | ES-02 | 消费current-fenced命令并提交typed Outcome |
| Source/Item/Revision/lifecycle/latest/serving | ES-03 | 只读exact truth；publication UoW通过owner port做CAS |
| DB/transaction/outbox/object/backup | ES-04 | logical repositories与named UoW；不直连路径/driver |
| Registry/model/provider adapter | ES-05 | 回填exact embedding model/space schemas；不热切binding |
| Structure/GenerationCommit/Block/Anchor | ES-06 | 只读exact commit/projection；不得衍生另一套block坐标 |
| EmbeddingInvocation/VectorRecord/IndexGeneration | ES-07 | 唯一语义、schema与mutation owner |
| PublicationProof/active index pointer | ES-07 + ES-03 atomic boundary | ES-07造proof/index pointer；ES-03验证并切serving |
| Retrieval policy/recall/traceback/rerank/result | ES-07 | 唯一算法与contract owner |
| Secret、egress、resource envelope、metrics/runbook/release orchestration | ES-08 | ES-07声明需求与安全guard；ES-08测量和执行 |

### 1.4 技术与 legacy 证据

| 证据 | Retain | Rewrite / Drop |
|---|---|---|
| legacy rag-vectorizer | 文档embedding与vector upsert需要独立证据；model/dimension必须显式 | 删除Cloudflare Worker/Vectorize/DO WAL、per-vector job state、隐藏retry、silent empty skip和truncation |
| legacy contexter topK | query embedding、bounded recall、hydrate-by-ID、summary到original映射 | 删除weak file_uuid/block_id/granularity坐标、missing original时silent summary-only |
| legacy contexter topN | vector recall后做second-stage rerank | 删除BGE远程依赖、1024字符截断、失败时dummy 0.5与原序fail-open |
| legacy internal_retrieve | source/item filter、bounded context与不返回raw vector | 删除platform realm/user字段、random context ID、正文silent drop和answer-oriented contract |
| Gemini Embeddings | stable explicit model、可选dimension、document/query官方格式、空间不兼容需全量重嵌入 | 不用latest alias、task_type猜测、multimodal embedding、自动截断或混合旧空间 |
| Turso embedded vector | vector32、vector_distance_cos与单DB精确SQL | V1不依赖新旧Turso文档中支持边界不一致的ANN/virtual index |

技术参考：

- https://ai.google.dev/gemini-api/docs/embeddings
- https://ai.google.dev/api/embeddings
- https://github.com/tursodatabase/turso/blob/main/docs/manual.md
- https://docs.turso.tech/features/ai-and-embeddings

---

## 2. Scope / Non-scope

### 2.1 Scope

ES-07只负责：

1. 六个exact Process capability：vector.embed、index.stage_generation、index.validate_publication、index.update_filters、index.withdraw_serving、index.rebuild_generation；
2. 一个code-owned Gemini embedding model和一个768维、float32、cosine、normalized EmbeddingSpace；
3. exact document/query formatting、no-truncation embedding call、reservation/outcome ledger与VectorBuildManifest；
4. one RetrievalBlock → one immutable VectorRecord，且保留commit/projection/block/unit/pair/anchor lineage；
5. embedded Turso vector32 BLOB与exact cosine scan；V1没有第二vector backend或ANN index；
6. immutable IndexGeneration、membership、canonical filter projection、full validation report；
7. PublicationProof、active index generation pointer及与ES-03 serving pointer同事务CAS；
8. filter-only generation reuse、logical-first withdrawal、reindex plan/candidate、grace/cleanup proof；
9.唯一同步semantic retrieval request/result、typed empty/error语义和query invocation/receipt evidence；
10. team+lifecycle+serving Revision+active generation+filter的dual fence；
11. 四strata recall、source-grounded expansion、RRF rerank、dedupe、diversity与context budget；
12. 24张logical owner tables、application ports、internal durable protocols、named UoW；
13. finite project-owned semantic retrieval benchmark与全部failure/recovery/acceptance evidence。

### 2.2 Non-scope

- 不增加request intent、source kind、Workflow key、StateFamily、服务、进程或发布单元；
- 不公开EmbeddingSpace、VectorRecord、IndexGeneration的list/get/export/CRUD；
- 不接受caller-supplied raw vector、metric、model、dimension、backend、SQL、physical index名或reranker；
- 不提供generic similarity endpoint、hybrid search DSL、FTS产品、query history产品或recommendation API；
- 不生成final answer、摘要回答、citation presentation、chat、session、agent或上游业务结果；
- 不重新clean、structurize、construct、chunk、summarize、改original或改source anchor；
- 不使用Cloudflare Vectorize、D1、DO、Queue、Pinecone、Qdrant、Milvus、Elasticsearch或第二数据库；
- 不在V1依赖ANN、DiskANN、HNSW、FTS、remote reranker或第三个模型provider；
- 不在adapter内hidden retry、silent skip、silent truncation、score fabrication、fallback order或missing-traceback降级；
- 不读取latest Revision、latest GenerationArtifact、latest model/profile或物理vector存在性决定serving；
- 不把代表性benchmark扩大为通用领域/语言/规模准确率SLA或在线evaluation平台；
- 不让physical cleanup阻塞logical withdrawal，也不让cleanup failure反向恢复serving。

### 2.3 完成定义

ES-07的`ready`是规范状态：以下义务已被完整定义并通过cross-spec audit，不表示它们已在尚未构建的实现上运行。任何实现要声明符合ES-07-v1.0并进入release，必须同时满足：

1. ES-06 projection schema/digest、ES-05 embedding binding和六个Process manifest set-exact；
2. 每个projection block恰有一个同Team/space/input digest的finite normalized VectorRecord，无skip/truncation；
3. IndexGeneration的block/vector/filter/lineage集合通过全量validation并产生type-specific PublicationProof；
4. active Item的serving Revision与active index generation在同一named UoW CAS；失败候选不改变旧pointer；
5. deactivated/deleted Item先由ES-03失去逻辑eligibility，任何残留vector均不可返回；
6. retrieval在一个一致DB snapshot内执行完整dual fence、filter、distance、hydrate、traceback与rerank；
7. 每个hit有exact original evidence、anchor、Revision、GenerationCommit、IndexGeneration与score explanation；
8. query无Task/Audit/Execution/Process/outbox副作用，且永不返回raw vector/model secret/path/provider body；
9. provider/DB/schema/space/pointer/traceback异常fail-closed并产生safe typed evidence；
10. §8全部HARD acceptance和finite semantic benchmark通过，并由ES-08纳入release gate。

### 2.4 核心术语

| Term | Exact meaning |
|---|---|
| EmbeddingSpace | immutable model+dimension+normalization+metric+document/query recipe的兼容边界 |
| EmbeddingInvocation | 一次真实EmbedContent外部调用的reservation与terminal factual outcome；不是Process retry |
| VectorRecord | exact RetrievalBlock在exact EmbeddingSpace中的immutable float32 representation及lineage |
| VectorBuildManifest | vector.embed对一个exact projection全部预期block/vector闭包的immutable proof input |
| IndexGeneration | 一个Item/Revision的immutable searchable membership与filter snapshot；不是状态 |
| PublicationProof | exact generation通过count/digest/space/filter/traceback/eligibility验证的type-specific durable fact |
| ActiveIndexPointer | 每个Team+Item当前可serving generation的CAS selection；nullable target表示已撤出 |
| Serving snapshot | 同一DB snapshot内全部eligible Item serving/index pointer的canonical digest |
| Evidence unit | ES-06 ConstructionUnit及其passage original/summary pair；rerank dedupe的最小单位 |
| Retrieval hit | 一个matched representation加至少一个exact original evidence/traceback的structured结果 |

---

## 3. Scope Impact Audit

    Scope Impact Audit
    - New product responsibility: no
    - New externally visible behavior: no; exact shape only implements frozen retrieval.search
    - New V1 capability: no
    - New request intent/source kind/Workflow: no
    - New domain identity or StateFamily: no StateFamily; only required derived facts
    - New deployment/runtime unit: no
    - New database/backend: no
    - New owner-truth or execution-spec file slot: no; this is fixed ES-07
    - Raises a fixed capacity ceiling: no
    - Can be solved inside an existing file and boundary: yes
    - Classification: no expansion

24张owner tables、六个Process contract、一个EmbeddingSpace和一个deterministic reranker只实现OT-03已经冻结的vector/retrieval闭环。Exact scan、数值budget和benchmark是既有能力内的有限技术裁决；它们不增加public vector primitive、provider、service、StateFamily、source、intent或Owner承诺。若精确扫描超出ES-08实测安全包络，V1降低admission ceiling或fail readiness，而不是自动引入ANN集群。

---

## 4. Architecture Decisions

### 4.1 单体内部模块与技术基线

    vector.domain
      ├─ embedding_space / input_recipe
      ├─ vector_record / build_manifest
      ├─ index_generation / filter_projection
      ├─ publication / active_pointer / withdrawal
      └─ retrieval_policy / evidence_group / rerank

    vector.application
      ├─ embed_handler / stage_handler / validate_publisher
      ├─ filter_update_handler / withdraw_handler / rebuild_handler
      ├─ retrieval_search_service
      └─ reconciliation / cleanup_planner

    vector.adapters
      ├─ ES-05 Gemini EmbedContent adapter
      ├─ ES-06 projection and traceback reader
      ├─ ES-03 eligibility and publication owner port
      ├─ ES-04 Turso repositories / UoW
      └─ ES-01 RetrievalSearchPort facade

依赖方向固定为domain ← application ← adapters。Domain/application不导入HTTP router、provider SDK、pyturso driver、filesystem path、Task repository或Workflow graph。所有DB mutation走ES-04 persistence lane；provider网络调用绝不发生在DB transaction内。

V1物理向量实现固定为pyturso 0.7.0 embedded Turso中的float32 vector BLOB，并使用vector_distance_cos做精确扫描。选择精确扫描的原因是：

1. 与一个应用、一个DB、一个persistence lane的冻结拓扑完全一致；
2. exact scan的正确性和备份语义可由当前embedded engine直接证明；
3. libSQL ANN与新Turso embedded engine的支持面不应在未完成capability probe时混为一个承诺；
4. Owner没有吞吐/延迟SLA，V1优先可证明的正确性与fail-closed边界；
5. 将来若采用ANN，必须新增retrieval policy/index profile version并用exact scan作recall oracle；不能same-version替换。

### 4.2 Exact EmbeddingSpace 与 input recipe

首版且唯一active定义：

| Field | Exact value |
|---|---|
| space_ref | embedding.gemini-2.text-768/1 |
| provider/model | google-gemini / gemini-embedding-2 |
| capability | text embedding only |
| output dimension | 768 |
| storage | IEEE-754 float32 little-endian BLOB |
| normalization | provider output must be finite and L2 norm in 0.98..1.02 |
| metric | cosine distance; similarity = 1 - distance |
| max model input | 8192 tokens; MKB preflight budgets are stricter |
| document recipe | title: TITLE | text: BLOCK_CONTENT；无title时title: none |
| query recipe | task: search result | query: QUERY |
| canonicalization | UTF-8、NFC、CRLF/CR→LF；只trim query边界，不改block body |
| batching | 每call 1..16个独立Content；output count/order必须exact |
| retry | adapter 0次；ES-02可用新fence/Invocation做Process retry |

TITLE由ES-06 exact tree path中的normalized heading按source order连接，NFC后折叠control whitespace，最多512 Unicode scalars；BLOCK_CONTENT是RetrievalBlock exact content，绝不截断、摘要或改写。Document embedding input最多4096 scalars/24KiB UTF-8；ES-06 block超限使consumer compatibility失败而不是truncate。

QUERY在请求校验后NFC、换行归一、trim两端；正文1..2048 Unicode scalars且UTF-8最多16KiB。空白-only、NUL、invalid Unicode或超限返回422，绝不发送provider。

gemini-embedding-2与任何旧模型空间不兼容。Model、dimension、recipe、normalization或metric任一改变都必须新建EmbeddingSpace version、重嵌入全部目标block、重建IndexGeneration并重新publication；不得混查、填零、pad/truncate或same-version替换。

### 4.3 Projection consumption 与 vector build

vector.embed只接收exact：

    team_uuid
    task_uuid / execution_uuid / process_uuid / fencing_generation
    intake_source_uuid / intake_item_uuid / intake_revision_uuid
    generation_commit_uuid / commit_digest
    retrieval_block_projection_artifact_uuid / projection_digest
    structure_schema_ref / digest
    embedding_space_ref / digest

固定算法：

1. 通过ES-06 InternalProjectionReader按UUID+digest读取，不枚举current；
2. 验证Team、Item、Revision、Execution、commit、五artifact bundle与consumer schema digest；
3. 按block_ordinal读取全部block，集合必须exact等于projection manifest；
4. 为每个block构造document input并计算input_digest；空正文、超限或非法字节立即拒绝整个build；
5. 按ordinal切成最多16个Content的batch；每个外部call先reserve EmbeddingInvocation；
6. call返回后验证output count、ordinal、dimension、finite、norm与vector digest，再写immutable outcome和VectorRecord；
7. duplicate delivery以process fence+batch ordinal+input set digest命中同一reservation/outcome；不同digest拒绝；
8. 全部block完成后计算ordered vector-set digest并一次性写VectorBuildManifest及members；
9. 任一block失败都不创建complete manifest；已有VectorRecord保留为orphan candidate，后续按lineage复用或grace清理；
10. success Outcome只返回manifest UUID/digest、count、space和projection refs，不含vector bytes。

每个RetrievalBlock恰对应一个VectorRecord。即使两个block文本相同，也不跨block合并identity，因为block coordinate、pair、anchor与future cleanup不同；同一record可以被多个后续IndexGeneration membership复用，但不得跨Team复用。

### 4.4 IndexGeneration、filter projection 与 exact search substrate

IndexGeneration按Team+Item隔离，是完成后一次写入的immutable candidate：

    IndexGeneration
      binds exact target IntakeRevision
      binds exact source GenerationCommit / RetrievalBlockProjection
      binds exact EmbeddingSpace
      contains exact ordered VectorRecord memberships
      contains canonical filter snapshot
      carries generation digest and predecessor lineage

index.stage_generation消费VectorBuildManifest，验证one block/one vector closure后写generation、input、membership与filter rows。Generation只有完整candidate row，不存在building/ready/failed状态；build进度由ES-02 Process及EmbeddingInvocation facts表达。Validation report记录valid/invalid disposition，ActiveIndexPointer表达selection。

Canonical filter projection来自目标IntakeRevision的filters对象及其exact filter_schema_ref/digest：

- 支持object深度最多4、最多64个scalar leaf path；
- scalar只允许string、integer/number、boolean、null；array最多64个scalar且类型同质；
- path使用RFC 6901 JSON Pointer canonical form；
- 每个值同时保存type tag、canonical value和value_digest；
- object/array本身不直接比较；array展开为同path的ordinal rows；
- schema不允许的key/type、NaN/Infinity、超深、超量均阻断generation；
- payload_extra、context metadata、secret和正文不能成为filter；
- generation-level filter snapshot适用于该Item全部vector，不复制成caller可写vector metadata。

精确search只扫描当前ActiveIndexPointer指向generation的membership，并在SQL join阶段同时验证Team、Item lifecycle、serving Revision、publication proof和filter。核心形态是：

    SELECT generation, vector_record, block, vector_distance_cos(stored_vector, query_vector) AS distance
      FROM active_index_generation_pointers
      JOIN intake_items
      JOIN index_generations
      JOIN publication_proofs
      JOIN index_generation_memberships
      JOIN vector_records
      JOIN vector_record_payloads
     WHERE team = requested_team
       AND item.lifecycle = active
       AND item.serving_revision = generation.target_revision
       AND active_pointer.generation = generation.id
       AND publication_proof.disposition = valid_and_serving
       AND requested scope/filter clauses match
     ORDER BY distance ASC, vector_record_uuid ASC
     LIMIT bounded_recall

查询参数通过typed binding传入；不得拼接SQL path/operator/value。V1不创建ANN/FTS shadow table。vector function capability、dimension mismatch和nonfinite结果在startup/readiness与每次publication validation双重检查。

### 4.5 六个 exact Process capability 与完整执行链

| Process key | Exact input | Exact output/proof | Handler side-effect class |
|---|---|---|---|
| vector.embed | exact S06 commit/projection + target space | VectorBuildManifestV1 | non_replayable_external |
| index.stage_generation | exact vector manifest + target Revision/filter | IndexGenerationCandidateV1 | transactional_sink |
| index.validate_publication | exact candidate + expected Item/pointer revisions | PublicationResultV1 | transactional_sink |
| index.update_filters | MetadataApplyResult filter_change + predecessor valid generation | IndexGenerationCandidateV1 with reused vectors | transactional_sink |
| index.withdraw_serving | exact lifecycle transition + serving-null fence | IndexWithdrawalProofV1 | transactional_sink |
| index.rebuild_generation | closed mode plan_scope or build_item + index.rebuild scope | IndexRebuildPlanV1 or IndexGenerationCandidateV1 | transactional_sink |

普通ingest/rebuild child：

    ES-06 GenerationCommit
      → vector.embed
      → index.stage_generation
      → index.validate_publication
      → atomic PublicationProof + active index pointer + Item serving CAS

Filter-only metadata：

    ES-03 MetadataApplyResult(filter_change, new Revision)
      → index.update_filters
         reuse predecessor projection and VectorRecords
         rebuild exact target-Revision filter snapshot
      → index.validate_publication
      → atomic new generation + serving/index pointer CAS

Deactivate/delete：

    ES-03 lifecycle transition clears serving first
      → index.withdraw_serving
      → CAS active index pointer to null + WithdrawalProof
      → cleanup intent may converge later

Public index.rebuild：

    index.rebuild_generation(mode=plan_scope)
      → immutable plan/items frozen from requested team/source/item/revision scope
      → ES-02 bounded fan-out one child per item
          same space/profile:
            index.rebuild_generation(mode=build_item, reuse exact vectors)
              → index.validate_publication
          same active space but vector reuse is not valid:
            vector.embed
              → index.stage_generation
              → index.validate_publication
      → ES-02 collect-all root proof

同一个manifest使用discriminated mode，不是generic action：plan_scope只冻结集合；build_item只为plan中的一个exact Item/Revision创建candidate。Caller不能选择mode、space或reuse。Team/source范围最多采用ES-03已冻结的10000-item fan-out ceiling；超过时Task typed reject，不隐式分页成多个Task。

Index rebuild target selection固定：

- team/source scope枚举所有非deleted Item；active且serving非null时target=exact serving Revision，active但serving null或deactivated时target=exact latest Revision；
- item scope应用同一规则；deleted或latest null拒绝；
- revision scope只在该Revision等于上述Item当前target时接受；historical/noncurrent Revision返回conflict，绝不把serving倒退；
- 每个target必须已有full-valid ES-06 commit/projection及一个可用source generation/vector set；缺少任一required substrate使plan_scope整体rejected，不silent skip；
- active EmbeddingSpace始终与current retrieval policy相同；record payload/lineage完整且recipe相同走reuse_vectors，否则按integrity/policy走reembed；该route只由release binding和validated substrate计算；
- plan item保存选择时的lifecycle、latest/serving、Item row revision与active pointer revision；child publication再次CAS。

### 4.6 Full validation 与 PublicationProof

index.validate_publication固定按下列顺序全量验证；任一步失败都写invalid report/findings，保持旧serving/index pointer不变：

1. identity：Team/Item/Revision、Execution/Process fence、generation UUID/digest exact；
2. source：S06 commit/projection full-valid、artifact存在、schema consumer digest supported；
3. set closure：expected block set = vector set = membership set，count与ordered digest exact；
4. vector：每个BLOB 768维float32、finite、norm 0.98..1.02、content/input/vector digest exact；
5. lineage：每个record回到exact block/unit/pair/anchor；summary citation有original target；
6. filters：target Revision/schema/value set与generation filter rows count/digest exact；
7. eligibility：Item lifecycle、latest/serving expected value与row revision符合publish mode；
8. engine：vector32 decode、self distance约0、cosine ordering fixture与tie-break deterministic；
9. traceback：每种block kind/channel至少一个及hashed sample最多256个做full hydrate；
10. query fixture：generation-local smoke queries不能泄漏其他Team/Revision且返回结构可hydrate；
11. proof：计算validation report digest、eligibility fence digest与publication proof digest；
12. CAS：只在同一named UoW写valid proof、active pointer transition、ES-03 serving transition、Process Outcome/outbox。

PublicationProof至少绑定：

    team / source / item / target Revision
    source content Revision when reused
    GenerationCommit / RetrievalBlockProjection
    EmbeddingSpace / VectorBuildManifest
    IndexGeneration / predecessor generation
    expected and actual block/vector/filter counts and digests
    validation report / validator implementation digest
    publish mode / eligibility fence digest
    Item row revision before/after
    active index pointer revision before/after
    task / execution / process / fence / occurred_at

publish_mode只有valid_and_serving或validated_not_served。Active Item正常publication必须valid_and_serving；deactivated Item rebuild可产validated_not_served，保持serving与active index pointer均为null；deleted Item一律拒绝。

### 4.7 Pointer CAS、filter reuse、withdrawal 与 reindex

ActiveIndexPointer的key固定为Team+Item；target nullable。它与IntakeItem serving pointer必须遵循：

- 首次发布：null → new generation，同时serving null → target Revision；
- 新Revision：old generation → new generation，同时serving old Revision → target Revision；
- same-Revision reindex：old generation → new generation，serving Revision值不变但Item row revision和proof transition前进；
- withdrawal：old generation → null；ES-03 serving已先变null；
- deactivated validation：不选择generation，不改变pointer；
- stale expected pointer/row revision：整个UoW rollback，返回conflict/retryable给ES-02；
- invalid candidate：绝不触碰pointer；
- duplicate same command/fence/digest：返回已提交proof；
- same idempotency fence different digest：integrity conflict。

Filter-only变化创建新IntakeRevision，但内容语义与ES-06 substrate复用。index.update_filters必须证明before/after content/context semantic digest相等、change kind exact为filter_change、predecessor proof有效、全部VectorRecord与projection digest不变；只创建新generation/input/membership/filter rows和新publication proof。任何content/context变化都拒绝reuse并走完整LS-RAG。

Index rebuild不创建IntakeRevision。Same-space rebuild复用immutableVectorRecord并创建新generation membership；space/recipe变化必须重嵌入。新generation先完整validate，CAS后旧generation进入grace；grace内旧record仍可由旧history引用但不再eligible。Cleanup只在无active pointer、无serving lineage、无rebuild plan、无hold且grace到期后写VectorCleanupProof。

### 4.8 Retrieval request admission 与 snapshot

retrieval.search执行顺序固定：

1. ES-01完成Team token认证并传入trusted team_uuid；
2. ES-07 strict-validate request、canonicalize query、scope和where clauses；
3. resolve release-pinned RetrievalPolicy与EmbeddingSpace exact ref/digest；不读latest；
4. reserve query EmbeddingInvocation，调用一次EmbedContent，持久化terminal outcome；
5. 通过ES-04 persistence lane开启一个read transaction/snapshot；
6. 解析所有eligible pointers并计算serving_snapshot_digest；
7. 在同一snapshot内执行filter、四strata exact recall、hydrate、traceback、rerank和budget assembly；
8. transaction结束后原子写immutable RetrievalQueryReceipt与hit evidence digest；
9. 返回result；若receipt不能持久化，则不返回semantic hits而返回503。

Embedding call发生在read snapshot之前，避免网络I/O持有DB transaction。V1 release只允许一个active EmbeddingSpace；readiness验证所有active generations与retrieval policy一致，因此无需跨不兼容空间合并。若发现mixed space、pointer drift或unsupported generation，整次query返回503 retrieval-binding-incompatible，不能跳过一部分Item。

Query路径不创建Task、TaskAudit、Execution、Process、outbox或callback。它会写内部EmbeddingInvocation和RetrievalQueryReceipt事实，用于provider成本、完整性与安全审计；这些不是异步work或公共query-history产品。

### 4.9 Public filter grammar

请求只有两个有限约束面：

1. scope：可选intake_source_uuids最多32个、intake_item_uuids最多128个；两者同时出现时取AND；
2. where：最多16个clause，op只允许eq、in、exists。

eq恰一个typed scalar value；in有1..32个同类型scalar；exists没有value。path必须是以斜线开头的canonical JSON Pointer，最多256字符，并至少在目标scope某个exact filter schema中注册。Clause在某generation schema中不存在或类型不兼容时该generation不匹配；若所有目标schema都不支持path，整个请求422。多个clause始终AND；同path的in内部OR。

不支持range、regex、prefix、contains、script、nested query、boolean expression tree、raw JSONPath、SQL、full-text或caller-defined function。该grammar只消费ES-03已存在的canonical filters，不新增业务metadata含义。

### 4.10 四strata recall 与 deterministic rerank

固定RetrievalPolicy ref为retrieval.rrf-grounded-v1/1：

| Parameter | Exact default |
|---|---:|
| top_k | 10；caller 1..20 |
| recall_per_stratum | min(max(4 × top_k, 20), 80) |
| similarity gate | cosine similarity ≥ 0.35 |
| RRF constant | 60 |
| passage original weight | 1.00 |
| passage summary weight | 1.00 |
| section summary weight | 0.75 |
| document summary weight | 0.50 |
| hierarchy expansion | 每summary hit最多8个cited evidence units |
| per-Item first-pass soft cap | 3 |
| context budget | default 12000、caller 1000..32000 Unicode scalars |
| max original evidence per hit | 3 |

四个recall strata分别是passage/original、passage/summary、section/summary、document/summary。每个stratum独立按distance升序、vector UUID升序取bounded candidates；低于similarity gate的不进入rerank。

Candidate映射到EvidenceUnit：

- passage block直接映射自身ConstructionUnit；
- section/document summary按ES-06 summary citations映射被引用SourceElement覆盖的ConstructionUnit；
- 一个summary引用过多unit时，按citation count降序、unit source ordinal升序取前8；
- 缺citation、coordinate不存在或无法hydrate original pair是active index integrity violation，整次query 503，不silent skip。

每个EvidenceUnit的融合分数：

    rrf_score = Σ(channel_weight / (60 + one_based_rank))

同unit在一个stratum只使用最佳rank；同时保留所有contributing ranks与max cosine similarity。排序固定为rrf_score降序、max_similarity降序、Item UUID升序、unit ordinal升序。

Context assembly先做每Item最多3个的diversity pass，再按原排序填充剩余位；同passage pair只出现一次。每个hit选贡献最高的block作matched_representation，同时附1..3个exact original passage evidence。超过context budget的候选不截断正文，跳到下一个可完整容纳候选；若首个合法hit也超budget则返回422 context-budget-too-small而不是partial text。

该Reranker是明确的second-stage deterministic ranker，不调用生成模型、远程cross-encoder或新provider。改变weight、gate、RRF constant、expansion、dedupe或budget必须新增RetrievalPolicy version并通过§4.13 regression；不能热改。

### 4.11 Grounding、Traceback 与 result disclosure

每个returned hit必须同时有：

1. matched representation的kind/channel/text与content digest；
2. 一个或多个original evidence，正文逐字来自ES-06 passage original block；
3. stable source anchors：text_span、element_span或page_region exact union；
4. Team-scoped IntakeSource/Item/ServingRevision；
5. source GenerationCommit、RetrievalBlockProjection、IndexGeneration与PublicationProof refs/digests；
6. evidence unit/pair/block coordinate；
7. semantic similarity、stratum ranks、RRF score与closed rerank reason codes；
8. snapshot digest和policy version。

summary hit绝不能只返回summary；必须附original evidence。Public payload不返回float array、vector BLOB/digest可逆表示、query embedding、model/provider、physical table/index/path、secret、Process/fence、raw provider response或internal error body。

### 4.12 Empty 与 error semantics

| Condition | HTTP / outcome | Semantics |
|---|---|---|
| valid request但scope内没有eligible knowledge | 200 empty | empty_reason=no_eligible_knowledge |
| 有eligible knowledge但所有candidate低于gate | 200 empty | empty_reason=no_semantic_match |
| query/scope/filter/budget invalid | 422 | stable validation problem |
| token Team与path Team不一致 | 403/404按ES-01 anti-enumeration | 不暴露存在性 |
| embedding provider timeout/failure | 503 | retrieval_dependency_failed；无fake result |
| mixed/unsupported space或registry drift | 503 | retrieval_binding_incompatible |
| active pointer/proof/serving mismatch | 503 | retrieval_snapshot_invalid |
| missing/corrupt vector/block/original/anchor | 503 | retrieval_integrity_failure |
| persistence busy beyondbounded deadline | 503 | retrieval_temporarily_unavailable |
| unexpected internal error | 500 safe problem | receipt记录safe error key；不回provider/body/path |

200 empty仍返回request UUID、policy ref、serving snapshot digest、eligible item/generation counts和空hits，证明它是一次正常检索结果而不是静默异常。任何integrity/binding/provider failure均不得伪装成empty。

### 4.13 Finite semantic release benchmark

OT04-T035由一个项目自有、immutable manifest驱动的有限fixture闭合：

- 16份代表性knowledge文档，覆盖text/markdown/pdf、heading/list/table、original/summary/hierarchy和四类source的至少一个实例；
- 32个固定query：16个direct/paraphrase/hierarchy positive、8个filter/lifecycle/Team isolation、8个unrelated negative；
- 每个positive声明exact expected Item、Revision-independent source anchor identity和一个或多个acceptable original evidence keys；
- release run固定top_k=5、context budget=12000、当前EmbeddingSpace/RetrievalPolicy；
- vector recall@20对expected evidence为100%；
- final grounded recall@5对positive为100%，primary expected evidence MRR@5至少0.75；
- original traceback exact-anchor accuracy为100%；
- filter、deactivated/deleted、wrong-Team leakage为0；
- unrelated negative全部返回no_semantic_match且无hit；
- 任一model/space/recipe/index/policy/reranker/schema实现digest变化必须全量重跑；
- manifest、输入artifact、expected set、实际result和metric report均digest固定并由ES-08作为release evidence。

这些数值只约束该有限项目fixture，不是任意领域、语言、规模或query风格的产品SLA。若0.35 gate不能同时通过positive与negative，必须新建policy version并以该fixture加新增失败fixture校准；不得same-version改阈值，也不得删除困难query使结果通过。

---

## 5. Contracts and Data

### 5.1 总体 schema 与 persistence 规则

ES-07拥有24张logical tables。全部业务表遵循ES-04 physical profile：

- 主业务identity使用UUID v7，外部resource UUID允许v4/v7；时间为UTC RFC3339微秒并在DB保存canonical integer/text；
- 所有Team-owned PK/UNIQUE/FK/index都显式包含team_uuid；
- semantic fact row插入后不可update；除30天后receipt+hits整组retention删除与proof-gated vector payload删除外，immutable skeleton不可delete；SelectionPointer只允许owner CAS；
- payload_extra为immutable empty-compatible object，核心代码不得从中读取identity、filter、route、proof、score、authority、secret、vector或正文；
- JSON使用JCS canonical bytes与SHA-256 digest；float score持久化使用IEEE-754 binary64并拒绝NaN/Infinity；
- vector_blob是内部BLOB；只允许VectorRepository和DistanceSearchAdapter读取，普通projection/日志/HTTP serializer无列权限；
- 所有owner table必须登记ES-04 table manifest、FK dependency、backup/restore、retention和integrity scanner；
- registry same key/version/same digest幂等，same key/version/different digest使readiness false；
- schema migration不重解释历史space/vector/generation/receipt。

24张表的exact集合为：

    embedding_spaces
    retrieval_policy_definitions
    embedding_invocations
    embedding_invocation_inputs
    embedding_invocation_outcomes
    vector_records
    vector_record_payloads
    vector_build_manifests
    vector_build_members
    index_generations
    index_generation_inputs
    index_generation_memberships
    index_generation_filter_values
    index_validation_reports
    index_validation_findings
    publication_proofs
    active_index_generation_pointers
    active_index_generation_transitions
    index_withdrawal_proofs
    vector_cleanup_proofs
    index_rebuild_plans
    index_rebuild_plan_items
    retrieval_query_receipts
    retrieval_query_hits

### 5.2 Public retrieval wire contract

#### 5.2.1 RetrievalSearchV1

POST /v1/teams/{team_uuid}/retrieval:search的body使用mkb.retrieval-search.v1：

    {
      "schema_version": "mkb.retrieval-search.v1",
      "query": "How is serving publication validated?",
      "scope": {
        "intake_source_uuids": ["..."],
        "intake_item_uuids": ["..."]
      },
      "where": [
        {"path": "/department", "op": "eq", "value": "engineering"},
        {"path": "/visibility", "op": "in", "values": ["internal", "shared"]}
      ],
      "top_k": 10,
      "context_budget_scalars": 12000
    }

Exact规则：

| Field | Required | Constraint |
|---|---|---|
| schema_version | yes | literal mkb.retrieval-search.v1 |
| query | yes | normalized后1..2048 scalars、UTF-8最多16KiB |
| scope | no | extra forbid；两个UUID array各自去重并canonical排序 |
| where | no | 0..16 clauses；eq/in/exists closed union |
| top_k | no | integer 1..20；default 10 |
| context_budget_scalars | no | integer 1000..32000；default 12000 |

整个schema additionalProperties=false。请求不能携带Team、query vector、embedding/model/profile、metric、threshold、index generation、raw SQL、include_raw_vector、answer Prompt或provider参数。Path Team只来自URL与认证上下文。

#### 5.2.2 RetrievalResultV1

200 body使用mkb.retrieval-result.v1：

    {
      "schema_version": "mkb.retrieval-result.v1",
      "request_uuid": "...",
      "outcome": "hits",
      "empty_reason": null,
      "retrieval_policy": {"key": "retrieval.rrf-grounded-v1", "version": 1, "digest": "..."},
      "serving_snapshot_digest": "...",
      "eligible_item_count": 4,
      "eligible_generation_count": 4,
      "hits": [
        {
          "rank": 1,
          "evidence_key": "...",
          "matched_representation": {
            "block_kind": "passage",
            "channel": "summary",
            "text": "...",
            "content_digest": "..."
          },
          "original_evidence": [
            {
              "evidence_key": "...",
              "text": "...",
              "content_digest": "...",
              "anchors": [{"kind": "text_span", "anchor_key": "...", "start": 120, "end": 284}]
            }
          ],
          "provenance": {
            "intake_source_uuid": "...",
            "intake_item_uuid": "...",
            "intake_revision_uuid": "...",
            "generation_commit_uuid": "...",
            "retrieval_block_projection_uuid": "...",
            "index_generation_uuid": "...",
            "publication_proof_uuid": "..."
          },
          "scores": {
            "semantic_similarity": 0.81,
            "fusion_score": 0.0317,
            "channel_ranks": [{"stratum": "passage_summary", "rank": 2}],
            "reason_codes": ["summary_match", "original_traceback", "rrf_fused"]
          }
        }
      ],
      "budget": {
        "requested_scalars": 12000,
        "used_scalars": 1480,
        "truncated_hit_count": 0
      }
    }

outcome只允许hits或empty。hits要求1..top_k条；empty要求hits为空且empty_reason为no_eligible_knowledge或no_semantic_match。每个hit必须有1..3个original_evidence；anchor使用ES-06三个exact kind的discriminated union。Page region可以含page、x、y、width、height和coordinate_space；element span含element key range；text span含canonical scalar offsets。所有坐标必须来自ES-06，不做显示层转换。

Reason code closed set：

    original_match
    passage_summary_match
    section_summary_match
    document_summary_match
    multi_channel_agreement
    hierarchy_traceback
    original_traceback
    rrf_fused
    diversity_deferred

Public score不承诺跨policy/model版本可比较；它只解释本次snapshot内排序。Problem response复用ES-01 RFC7807-safe envelope，detail不得含query原文、filter值、provider body、SQL、路径或vector。

### 5.3 Typed Process contracts

#### 5.3.1 VectorEmbedCommandV1 / VectorBuildManifestV1

mkb.vector-embed-command.v1包含§4.3 exact identity/binding、expected projection block count/digest、EmbeddingSpace ref/digest和Process fence。禁止inline block body、vector、provider credential或latest selector。

mkb.vector-build-manifest.v1包含manifest UUID/digest、Team/Item/Revision、commit/projection/space、expected/actual block/vector counts、ordered block/vector set digest、EmbeddingInvocation set digest、producer Process/fence和created_at；不含vector bytes。

#### 5.3.2 IndexStageCommandV1 / IndexGenerationCandidateV1

mkb.index-stage-command.v1引用exact VectorBuildManifest、target Revision、filter schema/value digest、expected predecessor pointer/row revision和generation recipe ref。

mkb.index-generation-candidate.v1包含generation UUID/digest、input kind、target/source content Revision、commit/projection/space、vector/filter counts/digests、predecessor、producer fence和candidate proof ref。它不声称valid或serving。

#### 5.3.3 PublicationCommandV1 / PublicationResultV1

mkb.index-publication-command.v1引用candidate UUID/digest、expected Item lifecycle/latest/serving/row revision、expected active pointer target/revision与requested publish mode。

mkb.index-publication-result.v1 closed union：

- published：PublicationProof、validation report、active pointer transition、Item serving transition refs；
- validated_not_served：PublicationProof、validation report，pointer/serving transition均null；
- rejected：validation report/findings、safe reason、retryability，PublicationProof null；
- conflict：observed pointer/row revisions的safe digest与retryability。

只有published或validated_not_served可以作为Process success proof；rejected/conflict如何映射Process Outcome由manifest error policy和ES-02统一裁决。

#### 5.3.4 FilterUpdateCommandV1

mkb.index-filter-update-command.v1包含MetadataApplyResult ref/digest、before/after Revision、content/context/filter semantic digests、predecessor PublicationProof/generation、expected Item/pointer revisions。Output是IndexGenerationCandidateV1，且input_kind固定filter_reuse。

#### 5.3.5 IndexWithdrawalCommandV1 / ProofV1

Command包含exact ES-03 lifecycle transition、before generation/revision、after lifecycle、serving-null fence、expected pointer revision与Process fence。Proof包含old generation、pointer transition old→null、lifecycle transition、cleanup eligibility digest和occurred_at；不声称physical vector已删。

#### 5.3.6 IndexRebuildCommandV1 / PlanV1

Command是closed union：

- plan_scope：Task的team/source/item/revision scope、reason digest、target release binding；
- build_item：plan UUID/digest、plan item ordinal、exact Item/Revision/source generation与reuse/reembed route。

Plan output包含immutable ordered item set、membership digest、target space/policy、per-item route、count和producer fence。build_item output是IndexGenerationCandidateV1。Unknown mode、plan外Item或caller-selected space拒绝。

### 5.4 Registry tables：2

#### 5.4.1 embedding_spaces

| Column group | Exact columns |
|---|---|
| Identity | space_key, space_version composite PK |
| Binding | provider_key/version/digest, model_key/version/digest, model_id |
| Shape | modality, dimension, scalar_type, byte_order, normalization, metric |
| Recipes | document_recipe_key/version/digest, query_recipe_key/version/digest, canonicalizer_key/version/digest |
| Limits | max_model_tokens, max_input_scalars, max_input_bytes, max_batch_size |
| Compatibility | structure_schema_ref/digest, supported_block_contract_digest |
| Governance | definition_digest, registered_at, registration_origin, payload_extra |

modality固定text；首版exact row为embedding.gemini-2.text-768/1。Model ID可以内部读取但不进入public result。Same version drift fail readiness。

#### 5.4.2 retrieval_policy_definitions

| Column group | Exact columns |
|---|---|
| Identity | policy_key, policy_version composite PK |
| Binding | embedding_space_ref/digest, supported_projection_schema_ref/digest |
| Recall | strata_set_digest, recall_formula, similarity_gate, metric |
| Rerank | rrf_constant, channel_weight_json/digest, hierarchy_expansion_limit, diversity_soft_cap |
| Result | top_k_default/max, context_default/min/max, original_evidence_max |
| Validator | implementation_key/version/digest, benchmark_manifest_ref/digest |
| Governance | definition_digest, registered_at, registration_origin, payload_extra |

首版exact row为retrieval.rrf-grounded-v1/1。Float canonical serialization由definition schema固定；same-version float drift也fail readiness。

### 5.5 Embedding invocation ledger：3

#### 5.5.1 embedding_invocations

| Column group | Exact columns |
|---|---|
| Identity | team_uuid, embedding_invocation_uuid PK |
| Owner | owner_kind process或retrieval_request, task/execution/process/fencing_generation nullable, retrieval_request_uuid nullable |
| Binding | purpose document_build或query, space_key/version/digest, provider/model refs/digests |
| Request | input_count, ordered_input_set_digest, request_options_digest, deadline_at |
| Idempotency | reservation_key, producer_command_uuid nullable |
| Time | reserved_at, missing_outcome_after |
| Extension | payload_extra |

owner_kind=process时Task/Execution/Process/fence全必填且request UUID null；retrieval_request反之。UNIQUE(team_uuid,reservation_key)；row immutable。

#### 5.5.2 embedding_invocation_inputs

| Exact columns | Constraints |
|---|---|
| team_uuid, embedding_invocation_uuid, input_ordinal | composite PK；ordinal从0连续 |
| source_kind, source_projection_uuid nullable, source_block_uuid nullable | document绑定block；query全部null |
| canonical_input_digest, scalar_count, utf8_bytes | 不保存query/block正文 |
| title_digest nullable, content_digest | document title可null；query content_digest是canonical query digest |
| payload_extra | immutable |

Query原文不进入ledger、日志、metric label或error；document正文由ES-06 authority持有，不在本表复制。

#### 5.5.3 embedding_invocation_outcomes

| Column group | Exact columns |
|---|---|
| Identity | team_uuid, embedding_invocation_uuid PK/FK |
| Outcome | disposition succeeded/rejected/failed/indeterminate, safe_code, retryability |
| Response | output_count nullable, ordered_output_digest nullable, dimension nullable, norm_min/max nullable |
| Usage | input_tokens nullable, billed_units nullable, provider_request_ref_hash nullable |
| Evidence | response_schema_digest nullable, adapter_implementation_digest, outcome_digest |
| Time | completed_at |
| Extension | payload_extra |

一Invocation最多一个terminal outcome。Provider usage缺失保存null，不填0；provider request ref只保存不可逆hash。Raw response、credential和vector不在outcome。

### 5.6 Vector build tables：4

#### 5.6.1 vector_records

| Column group | Exact columns |
|---|---|
| Identity | team_uuid, vector_record_uuid PK |
| Source | intake_item_uuid, source_content_revision_uuid, generation_commit_uuid, projection_uuid/digest |
| Block | retrieval_block_uuid/key, block_ordinal, block_kind, channel, construction_unit_uuid nullable, pair_key nullable |
| Space/input | space_key/version/digest, title_digest nullable, block_content_digest, embedding_input_digest |
| Invocation | embedding_invocation_uuid, output_ordinal |
| Vector metadata | dimension, scalar_type, vector_size_bytes, vector_digest, l2_norm |
| Causation | producer_execution_uuid, producer_process_uuid, fencing_generation, created_at |
| Extension | payload_extra |

UNIQUE(team_uuid,projection_uuid,retrieval_block_uuid,space_key,space_version)。Dimension固定匹配space；vector_size_bytes=dimension×4；所有值finite。该immutable metadata表无public repository/serializer。

#### 5.6.2 vector_record_payloads

| Exact columns | Constraints |
|---|---|
| team_uuid, vector_record_uuid PK/FK | 一条live VectorRecord恰一payload |
| vector_blob BLOB NOT NULL | 长度=dimension×4；内部float32 little-endian |
| payload_digest, stored_at | exact匹配VectorRecord vector_digest |

该表是唯一physical vector payload host。Active/grace/live-lineage record必须有payload；VectorRepository和exact search内部join才可读取。Cleanup在vector_cleanup_finalize_v1中原子删除payload row并写CleanupProof，永不删除或改写immutable vector_records metadata；missing live payload是integrity failure。

#### 5.6.3 vector_build_manifests

| Column group | Exact columns |
|---|---|
| Identity | team_uuid, vector_build_manifest_uuid PK |
| Target | intake_item_uuid, intake_revision_uuid, source_content_revision_uuid |
| Source | generation_commit_uuid/digest, projection_uuid/digest, structure_schema_ref/digest |
| Space | space_key/version/digest |
| Closure | expected_block_count, actual_vector_count, ordered_block_set_digest, ordered_vector_set_digest |
| Invocation | invocation_set_digest, invocation_count |
| Producer | task/execution/process UUID, fencing_generation, manifest_digest, created_at |
| Extension | payload_extra |

只有全集合完成才插row。UNIQUE(team_uuid,process_uuid,fencing_generation,projection_uuid,space digest)。

#### 5.6.4 vector_build_members

| Exact columns | Constraints |
|---|---|
| team_uuid, vector_build_manifest_uuid, member_ordinal | composite PK；ordinal连续 |
| retrieval_block_uuid, vector_record_uuid | 同projection/space/Team；各自unique |
| block_content_digest, embedding_input_digest, vector_digest | 与source/record exact |
| payload_extra | immutable |

Member ordered digest必须重算等于manifest；缺一、多一、重排或跨Team均使manifest invalid。

### 5.7 Index generation 与 filter tables：4

#### 5.7.1 index_generations

| Column group | Exact columns |
|---|---|
| Identity | team_uuid, index_generation_uuid PK |
| Target | intake_source_uuid, intake_item_uuid, target_revision_uuid, source_content_revision_uuid |
| Source | generation_commit_uuid/digest, projection_uuid/digest, space_key/version/digest |
| Recipe | generation_recipe_key/version/digest, input_kind full_embed/filter_reuse/index_rebuild_reuse |
| Closure | vector_count, vector_set_digest, filter_value_count, filter_set_digest, generation_digest |
| Lineage | predecessor_generation_uuid nullable, rebuild_plan_uuid nullable |
| Producer | task/execution/process UUID, fencing_generation, created_at |
| Extension | payload_extra |

Generation immutable；不存在status。UNIQUE(team_uuid,intake_item_uuid,generation_digest)提供同输入重放幂等。

#### 5.7.2 index_generation_inputs

| Exact columns | Constraints |
|---|---|
| team_uuid, index_generation_uuid PK/FK | 一generation恰一input record |
| input_kind | 与generation一致 |
| vector_build_manifest_uuid/digest nullable | full_embed必填 |
| reused_generation_uuid/digest nullable | filter/index reuse必填 |
| metadata_apply_result_ref/digest nullable | filter_reuse必填 |
| target_filter_schema_ref/digest, target_filter_value_digest | 全部必填 |
| payload_extra | immutable |

full_embed与reuse字段XOR；reused generation必须已有valid PublicationProof或是同rebuild plan显式允许的validated source。

#### 5.7.3 index_generation_memberships

| Exact columns | Constraints |
|---|---|
| team_uuid, index_generation_uuid, membership_ordinal | composite PK；ordinal连续 |
| retrieval_block_uuid, vector_record_uuid | generation内各自unique |
| block_kind, channel, construction_unit_uuid nullable, pair_key nullable | 与ES-06/record exact |
| membership_digest | 对coordinate+record+content+vector digest |
| payload_extra | immutable |

没有eligible/status列；eligibility由active pointer+serving fence产生。Reuse只新增membership row，不复制vector BLOB。

#### 5.7.4 index_generation_filter_values

| Exact columns | Constraints |
|---|---|
| team_uuid, index_generation_uuid, filter_path, value_ordinal | composite PK |
| filter_schema_ref/digest | target Revision exact binding |
| value_kind | string/integer/number/boolean/null |
| value_text/value_integer/value_real/value_boolean | 按kind恰一；null时全部null |
| value_digest, filter_entry_digest | canonical |
| payload_extra | immutable |

每generation的ordered row digest exact等于filter_set_digest。建立Team+path+kind+typed-value+generation的普通B-tree indexes；不建立caller-controlled expression index。

### 5.8 Validation、publication 与 pointer tables：5

#### 5.8.1 index_validation_reports

| Column group | Exact columns |
|---|---|
| Identity | team_uuid, index_validation_report_uuid PK |
| Subject | index_generation_uuid/digest |
| Validator | validator_key/version/implementation_digest, policy_ref/digest |
| Result | disposition valid/invalid, check_count, finding_count, expected/actual counts/digests |
| Engine | vector_capability_probe_digest, traceback_sample_digest, smoke_query_digest |
| Producer | execution/process/fence, report_digest, completed_at |
| Extension | payload_extra |

每generation+validator implementation最多一份terminal report；重跑必须新validator version或new generation。

#### 5.8.2 index_validation_findings

| Exact columns | Constraints |
|---|---|
| team_uuid, report_uuid, finding_ordinal | composite PK |
| check_key, severity error或warning, safe_code | closed registry |
| subject_kind, subject_ref_hash, expected_digest nullable, actual_digest nullable | 不含正文/vector/path |
| finding_digest, payload_extra | immutable |

任何error使report invalid；warning集合也进入report digest，不能丢弃。

#### 5.8.3 publication_proofs

| Column group | Exact columns |
|---|---|
| Identity | team_uuid, publication_proof_uuid PK |
| Target | source/item/target_revision/source_content_revision |
| Derived | generation_commit/projection/vector_build/index_generation refs/digests |
| Validation | report_uuid/digest, space/policy refs/digests, count/filter/traceback proof digests |
| Eligibility | publish_mode, disposition valid_and_serving或validated_not_served, eligibility_fence_digest |
| CAS | expected/actual Item row revisions, expected/actual active pointer revisions, transition_set_digest nullable |
| Causation | task/execution/process/fence, proof_digest, published_at |
| Extension | payload_extra |

Proof immutable。valid_and_serving要求transition_set_digest非null，且同transaction恰有一个Item transition和一个active-index transition以该proof为cause，重算集合digest必须相等；validated_not_served要求digest为null且没有transition。该单向FK/causation设计避免Proof与transition形成循环引用。

#### 5.8.4 active_index_generation_pointers

| Exact columns | Constraints |
|---|---|
| team_uuid, intake_item_uuid | composite PK |
| target_index_generation_uuid nullable, target_revision_uuid nullable | 同时null或同时非null |
| selection_proof_kind publication或withdrawal, selection_proof_uuid/digest |
| pointer_revision | 每次CAS +1 |
| updated_at, payload_extra | mutable host；payload_extra不参与语义 |

Non-null target必须有valid_and_serving PublicationProof；null target必须有WithdrawalProof或初始化proof。读取不得自行fallback前一generation。

#### 5.8.5 active_index_generation_transitions

| Column group | Exact columns |
|---|---|
| Identity | team_uuid, pointer_transition_uuid PK, intake_item_uuid |
| Before | before_generation/revision nullable, pointer_revision_before |
| After | after_generation/revision nullable, pointer_revision_after |
| Cause | action publish/replace/reindex/withdraw, proof_kind/ref/digest |
| Runtime | task/execution/process/fence nullable按cause |
| Time | occurred_at, payload_extra |

before/after pair同时null或非null；revision_after=before+1。UNIQUE(team,item,proof_kind,proof_ref)保证重放。

### 5.9 Withdrawal、cleanup 与 rebuild tables：4

#### 5.9.1 index_withdrawal_proofs

| Exact columns | Constraints |
|---|---|
| team_uuid, withdrawal_proof_uuid PK | identity |
| intake_item_uuid, before_revision_uuid, before_generation_uuid | exact old serving |
| lifecycle_transition_uuid/digest, after_lifecycle | deactivated或deleted |
| serving_null_fence_digest, pointer_transition_uuid/digest | logical fence |
| cleanup_eligibility_digest, task/execution/process/fence | causation |
| proof_digest, withdrawn_at, payload_extra | immutable |

Proof不含physical_deleted=true之类字段；物理清理由独立proof表达。

#### 5.9.2 vector_cleanup_proofs

| Exact columns | Constraints |
|---|---|
| team_uuid, vector_cleanup_proof_uuid PK | identity |
| subject_kind generation/vector_set/vector_record, subject_ref/digest | closed union |
| eligibility_snapshot_digest, grace_policy_ref/digest, hold_set_digest | 删除前条件 |
| deleted_row_count, deleted_byte_count, retained_lineage_digest | 结果 |
| cleanup_intent_ref/digest, execution/process/fence | causation |
| proof_digest, completed_at, payload_extra | immutable |

不得删除PublicationProof、transition、manifest/member skeleton、query receipt或仍被任一generation/plan/hold引用的record。

#### 5.9.3 index_rebuild_plans

| Column group | Exact columns |
|---|---|
| Identity | team_uuid, index_rebuild_plan_uuid PK |
| Scope | scope_kind/team-source-item-revision, scope_ref nullable, reason_digest |
| Binding | target_space/policy refs/digests, generation_recipe_ref/digest |
| Set | item_count, ordered_item_set_digest |
| Producer | task/execution/process/fence, plan_digest, created_at |
| Extension | payload_extra |

计划只冻结当时eligible/latest policy选出的exact set；后续Item变化由child expected pointer fence检测，不重新枚举或悄悄替换。

#### 5.9.4 index_rebuild_plan_items

| Exact columns | Constraints |
|---|---|
| team_uuid, plan_uuid, item_ordinal | composite PK；0..count-1连续 |
| intake_source_uuid, intake_item_uuid, target_revision_uuid | exact |
| source_generation_uuid/digest, source_projection_uuid/digest | source |
| route_kind reuse_vectors或reembed, target_space_ref/digest | code-owned |
| expected_item_row_revision, expected_pointer_revision | child fence |
| item_entry_digest, payload_extra | immutable |

UNIQUE(plan,item)。Child只能消费自己ordinal；stale child产生typed conflict，不切换别的Revision。

### 5.10 Retrieval evidence tables：2

#### 5.10.1 retrieval_query_receipts

| Column group | Exact columns |
|---|---|
| Identity | team_uuid, retrieval_request_uuid PK |
| Request | canonical_query_digest, query_scalar_count/bytes, scope_digest, where_digest, top_k, context_budget |
| Binding | policy_key/version/digest, space_key/version/digest, query_embedding_invocation_uuid |
| Snapshot | serving_snapshot_digest, eligible_item_count, eligible_generation_count |
| Outcome | disposition hits/empty/error, empty_reason nullable, safe_error_code nullable, hit_count, hit_set_digest |
| Budget/timing | used_scalars, omitted_candidate_count, duration_ms, completed_at |
| Evidence | receipt_digest, payload_extra |

Receipt在30天audit retention内immutable且不保存query/filter原值；到期后只能由ES-04-v1.0 `retrieval_evidence_retention_v1`按Team bounded batch删除receipt+hits。hits/empty/error字段按disposition受CHECK约束。Duration是运行事实，不是SLA。

#### 5.10.2 retrieval_query_hits

| Exact columns | Constraints |
|---|---|
| team_uuid, retrieval_request_uuid, hit_rank | composite PK；rank从1连续 |
| evidence_key, matched_block_uuid, matched_channel/kind | identity |
| item/revision/generation/publication refs | exact snapshot provenance |
| semantic_similarity, fusion_score, channel_rank_set_digest | finite |
| original_evidence_set_digest, anchor_set_digest, reason_code_set_digest | grounding |
| hit_evidence_digest, payload_extra | immutable |

本表不复制hit文本、anchor坐标或vector；它保存可回读authority的proof refs/digests。30天内不可update/单独delete；retention UoW整组删除。没有public query-history API。

### 5.11 Application ports

    class EmbeddingSpaceRegistryPort(Protocol):
        async def resolve_exact(self, ref: SpaceRef) -> EmbeddingSpace: ...
        async def assert_release_binding(self, ref: SpaceRef, digest: Digest) -> None: ...

    class TextEmbeddingAdapterPort(Protocol):
        async def embed(self, command: EmbedContentCommandV1) -> EmbedContentOutcomeV1: ...

    class ProjectionReaderPort(Protocol):
        async def get_exact_projection(self, team: UUID, commit: Ref, projection: Ref) -> ProjectionV1: ...
        async def hydrate_block_and_traceback(self, team: UUID, block: Ref) -> GroundedBlockV1: ...

    class VectorBuildPort(Protocol):
        async def embed_projection(self, command: VectorEmbedCommandV1) -> VectorBuildManifestV1: ...

    class IndexGenerationPort(Protocol):
        async def stage(self, command: IndexStageCommandV1) -> IndexGenerationCandidateV1: ...
        async def update_filters(self, command: FilterUpdateCommandV1) -> IndexGenerationCandidateV1: ...
        async def rebuild(self, command: IndexRebuildCommandV1) -> IndexRebuildOutcomeV1: ...

    class PublicationPort(Protocol):
        async def validate_and_publish(self, command: PublicationCommandV1) -> PublicationResultV1: ...
        async def withdraw(self, command: IndexWithdrawalCommandV1) -> IndexWithdrawalProofV1: ...

    class IntakeEligibilityPort(Protocol): ...      # ES-03 exact read authority
    class IntakeTransitionOwnerPort(Protocol): ...  # ES-03 exact publication CAS authority

    class ExactVectorSearchPort(Protocol):
        async def recall(self, snapshot: ReadSnapshot, command: RecallCommandV1) -> tuple[RecallCandidateV1, ...]: ...

    class RetrievalSearchPort(Protocol):
        async def search(self, auth: TeamAuthContext, request: RetrievalSearchV1) -> RetrievalResultV1: ...

    class VectorCleanupPort(Protocol):
        async def prove_and_cleanup(self, command: VectorCleanupCommandV1) -> VectorCleanupProofV1: ...

任何port都不返回裸DB connection、path、provider SDK object、vector给HTTP facade或Task repository。Only ExactVectorSearchPort在vector module内部接收query vector transient value。

ES-07先调用ES-03-v1.0 `IntakeEligibilityPort.verify_serving(ServingEligibilityQueryV1)`读取proof，再把validated candidate交`IntakeTransitionOwnerPort.cas_serving_with_index(AtomicPublicationCommandV1, uow)`；后者是Item serving与active index pointer双CAS的唯一跨owner入口。ES-07不得为同名port另造方法、直接读取可变Item row或取得裸serving update权限。

### 5.12 Internal durable protocols

| Protocol | Producer → Consumer | Payload minimum | Delivery / dedupe |
|---|---|---|---|
| mkb.vector-build-manifest.v1 | vector.embed → ES-02 route/index.stage | exact manifest ref/digest | Process Outcome + fence |
| mkb.index-generation-candidate.v1 | stage/filter/rebuild → validate | generation ref/digest | Process Outcome + fence |
| mkb.index-publication-proof.v1 | ES-07 → ES-03/ES-01 Task result | proof/ref/digest + Item/Revision | atomic DB fact/outbox |
| mkb.index-withdrawal-proof.v1 | ES-07 → cleanup/runtime summary | logical fence/proof | atomic DB fact/outbox |
| mkb.index-rebuild-plan.v1 | root planner → ES-02 fan-out | ordered item set/ref/digest | durable plan + child dedupe |
| intake.serving-changed.v1 | ES-03 → read projections/ES-07 scanner | before/after Revision + proof digest | existing ES-03 outbox |
| index.publication-committed.v1 | atomic UoW → projections/scanner | generation/pointer/serving/proof refs | outbox inbox dedupe |
| index.cleanup-eligible.v1 | scanner → cleanup Process | subject + eligibility snapshot | at-least-once |

retrieval.search是同步port call，没有message、outbox、Task或callback。Protocol payload均不含vector、正文、secret、provider body或next Process；ES-02 compiled route是唯一next-step authority。

### 5.13 Named transaction profiles

| UoW key | Atomic writes | External I/O |
|---|---|---|
| embedding_invocation_reserve_v1 | invocation + input rows | none |
| embedding_invocation_complete_v1 | terminal outcome + document VectorRecords for that call | none |
| vector_build_finalize_v1 | manifest + all members + Process Outcome/wake | none |
| index_generation_stage_v1 | generation + input + memberships + filters + Process Outcome/wake | none |
| intake_publication_v1 | validation report/findings + PublicationProof + active pointer/transition + ES-03 Item serving/transition + Process Outcome + outbox | none |
| index_withdraw_v1 | WithdrawalProof + pointer/transition + Process Outcome + outbox | none |
| index_rebuild_plan_v1 | plan + items + Process Outcome/fan-out wake | none |
| retrieval_receipt_finalize_v1 | receipt + hit evidence rows | none |
| vector_cleanup_finalize_v1 | eligible physical deletes + CleanupProof + Process Outcome/outbox | none |

Filter reuse generation使用index_generation_stage_v1。Provider EmbedContent发生在reserve与complete两个UoW之间；exact vector scan发生在只读snapshot内，receipt finalize在snapshot关闭后。任何named UoW都不得包住网络I/O。

---

## 6. State / Consistency / Failure

### 6.1 StateFamily boundary 与 factual automata

ES-07不增加StateFamily。六个既有StateFamily仍是Task、Execution、Process、IntakeCandidateSet、IntakeItem lifecycle、ExecutionGate。以下均为事实或SelectionPointer：

    EmbeddingInvocation
      reservation exists, no outcome
        → succeeded | rejected | failed | indeterminate terminal outcome

    Vector build
      no complete manifest
        → immutable complete VectorBuildManifest

    IndexGeneration
      immutable candidate
        → immutable valid report → optional PublicationProof/selection
        → immutable invalid report → never selectable

    ActiveIndexPointer
      null ↔ selected generation
      selected old → selected new
      every edge is CAS + immutable transition

    Retrieval request
      transient synchronous work
        → immutable hits | empty | error receipt

EmbeddingInvocation的pending不是业务state；它只是reservation存在而terminal outcome尚缺。Scanner只能补indeterminate fact/repair intent，不把它升级为Attempt或Invocation StateFamily。IndexGeneration也没有building/valid/active status列。

### 6.2 核心不变量

1. 一个projection block在一个space中恰有一个VectorRecord identity；不skip、不truncate；
2. VectorRecord Team、projection、block、content、input、space、Invocation和vector digest全部闭合；
3. 完整VectorBuildManifest集合与projection block set exact相等；
4. IndexGeneration membership与manifest/reuse source exact相等；
5. ActiveIndexPointer只指向valid_and_serving proof绑定的generation；
6. Item serving Revision与active generation target Revision必须相等；
7. Item非active或serving null时任何vector都不可retrieval；
8. Query Team既在relation join又在generation/filter/vector key中出现；
9. Retrieval policy space与所有active generation space set-exact；
10. Summary hit必须有original evidence和exact anchor；
11. Public result永不含raw vector、query embedding或final answer；
12. Publication、withdrawal、cleanup、query empty/error不可互相冒充；
13. 失败candidate不改旧serving/index pointer；
14. filter-only reuse不改变content/projection/vector digest；
15. rebuild不创建IntakeRevision；
16. same key/version registry drift和unsupported schema均fail readiness；
17. Provider/DB/integrity异常不能转成empty或低分fake hit；
18. Process success proof不携带route，Task success仍由ES-02 aggregate。

### 6.3 Concurrency、linearization 与 snapshot

| Operation | Linearization point |
|---|---|
| Embedding call ownership | embedding_invocation_reserve_v1 unique reservation commit |
| Vector build complete | VectorBuildManifest+members commit |
| Index candidate exists | generation/input/membership/filter commit |
| Publication | intake_publication_v1 commit |
| Withdrawal | index_withdraw_v1 pointer-null commit；normal eligibility更早在ES-03 serving-null commit消失 |
| Rebuild set | IndexRebuildPlan/items commit |
| Retrieval visibility | one ES-04 read snapshot containing serving/index/proof/vector truth |
| Query evidence | retrieval_receipt_finalize_v1 commit |
| Physical cleanup | vector_cleanup_finalize_v1 commit |

Publication锁/CAS顺序固定：IntakeItem → ActiveIndexPointer → candidate generation/report。相反顺序禁止，避免deadlock。Same-Revision reindex也必须CAS Item row revision，使serving proof变化可观测。

Query在一个snapshot内完成pointer解析、distance scan、hydrate、traceback与rerank；不得在多个autocommit read之间拼结果。Embedding在snapshot前生成，但space是release-pinned；如果snapshot发现binding不一致则503，不重用该vector跨space。

### 6.4 Failure disposition

| Failure | Durable disposition | Serving effect |
|---|---|---|
| invalid/empty/oversize block | Invocation不发出；Process rejected evidence | 旧serving不变 |
| provider reject/timeout | failed/rejected outcome | 旧serving不变 |
| crash after reservation before/after call | scanner写indeterminate；ES-02决定新retry | 旧serving不变 |
| output count/dimension/norm invalid | rejected outcome；不建manifest | 旧serving不变 |
| partial vector persistence | outcome/records可留；无manifest不可stage | 旧serving不变 |
| filter schema/value invalid | invalid Process outcome | 旧serving不变 |
| validation error | invalid report/findings，无proof | 旧serving不变 |
| stale Item/pointer fence | whole publication rollback，typed conflict | 旧serving不变 |
| crash in publication UoW | whole commit or rollback | 不出现半切pointer |
| lifecycle clears serving then withdraw crash | retrieval已被Item fence阻断；scanner重投withdraw | safe unavailable for that Item |
| active pointer target missing/corrupt | readiness/query integrity failure | 不fallback旧代 |
| query provider failure | error receipt/503 | 不返回fake hit |
| query trace missing | error receipt/503 | 不skip corrupt hit |
| receipt persistence failure | 503，无semantic response | serving truth不变 |
| cleanup partial failure | noCleanupProof或failed Process | 不恢复serving |

### 6.5 Recovery 与 reconciliation

同一single-writer maintenance loop执行bounded scanner：

1. missing EmbeddingInvocation outcome超过deadline：写indeterminate terminal outcome并唤醒相应Process recovery；
2. VectorRecord存在但无live manifest/generation/hold且grace到期：创建cleanup intent；
3. complete manifest无stage Process：只唤醒ES-02 lost-wake recovery，不自行route；
4. valid generation无publication Process：只唤醒current execution；
5. non-null active pointer的proof/Item serving不一致：readiness false、normal retrieval fail；不自动猜修复target；
6. Item serving null但active pointer非null：根据exact lifecycle transition重投withdraw command；
7. valid_and_serving proof缺pointer/Item transition：这是atomicity corruption，stop readiness；
8. old generation grace到期：在完整reference/hold scan后产生cleanup eligibility；
9. rebuild plan child缺失：ES-02按plan ordered set补materialize，unique child key去重；
10. query receipt不完整：receipt UoW本身原子；不存在partial hit set，orphan query Invocation只转indeterminate。

Scanner不调用provider、不发布candidate、不改变Item lifecycle、不选latest、不创建新Revision，也不根据日志/文件猜业务truth。

### 6.6 Retry、cancel、rebuild 与 cleanup

- 只有ES-02可以重试六个Process；每次retry使用新fencing generation，外部embedding call使用新Invocation；
- Provider没有可证明的idempotency时，indeterminate call绝不原位重发；新Process retry可能产生额外计费，但不会重复canonical VectorRecord/manifest；
- Retrieval query没有内部automatic retry；依赖失败直接返回typed 503，由caller决定是否重发新request；
- Task cancel阻止未开始的新embed/stage/publish work；已committed PublicationProof不回滚，未选candidate保持历史；
- index.rebuild always new Task；不原位复活旧Task/Process，不创建Revision；
- logical withdrawal不等待vector delete；physical cleanup是独立Process/proof；
- current generation、grace generation、publication lineage、active rebuild plan、semantic benchmark fixture或legal hold任一引用存在时不得cleanup；
- Vector payload删除后保留vector_records immutable metadata skeleton的identity/source/space/vector digest/size与CleanupProof；只删除vector_record_payloads row。Active/grace/live lineage不得缺payload。

### 6.7 Security、privacy 与 disclosure

- Team来自认证上下文；请求body中的任何Team字段均schema拒绝；
- SQL、filter、vector binding全部参数化；JSON Pointer必须registry-resolved，不拼identifier；
- query/filter原文只存在请求内存，ledger只保存digest/长度；日志最多request UUID/safe code；
- embedding provider收到最小query或block text，不发送Team UUID、source credential、internal path、Task描述或filter metadata；
- credential仅通过ES-08 secret slot注入adapter，不进入DB、payload_extra、exception或result；
- vector BLOB仅内部repository可访问，禁止通用ORM dump、debug endpoint、backup browser公共暴露；
- public result只返回同Team eligible知识；wrong-Team采用ES-01 anti-enumeration；
- hit正文可能敏感，调用者已是Team-level trusted internal orchestrator；V1不新增终端用户ACL平台；
- query embedding与stored vector不得进入metrics label、trace span、structured log或error；
- exact provider/model不进入public payload，避免把execution binding升级为产品contract。

### 6.8 Retention 与 backup semantics

EmbeddingInvocation reservation/outcome、manifest、generation、validation、publication/pointer transition与withdrawal skeleton按ES-08-v1.0保留deployment lifetime。Query receipt/hit不保存query或正文，固定保留30天后由`retrieval_evidence_retention_v1`整组删除；active incident/hold使其继续保留。Active/grace vector BLOB和全部live lineage必须进入ES-04 consistent backup；restore后先做space/vector function、pointer/proof、block/anchor与digest全检，readiness通过前不提供retrieval。

Old/invalid vector BLOB至少24小时grace，且hold/reference/current/serving/plan条件全部满足后才可清理；cleanup不能删除PublicationProof或使历史Task result无法解释。Backup不能把vector BLOB导出为public raw-vector能力。

---

## 7. Legacy Retain / Rewrite / Drop

| Legacy practice | Decision | V1 replacement |
|---|---|---|
| query与document用同一embedding family | retain principle | one exact EmbeddingSpace with separate official recipes |
| bounded topK vector recall | retain | four exact strata + finite recall formula |
| hydrate vector IDs后取正文 | retain | normalized block/anchor authority，vector table不复制public正文 |
| summary hit映射original | retain and strengthen | mandatory exact pair/unit/source anchor；missing即503 |
| second-stage rerank | retain and rewrite | deterministic RRF，不用remote BGE或dummy score |
| metadata filter | retain and constrain | Revision-owned canonical typed equality filter projection |
| Cloudflare Vectorize/D1/DO/Queue | drop | one embedded Turso DB/persistence lane |
| per-vector processing_status/job | drop | ES-02 Process + immutable Invocation/manifest facts |
| embedder hidden retry/backoff | drop | adapter 0 retry；ES-02唯一retry owner |
| heuristic token truncate | drop | strict scalar/byte preflight，超限reject |
| empty block silent skip | drop | full build rejection，无partial manifest |
| Vectorize upsert ACK as success | drop | full validation + PublicationProof + atomic dual pointer CAS |
| weak file_uuid/block_id/granularity coordinate | drop | ES-06 generation-local block/unit/pair/anchor refs |
| missing original returns summary only | drop | whole query integrity failure |
| reranker failure returns0.5/original order | drop | no remote reranker；any invariant failure fail-closed |
| realm/user/platform ACL metadata | drop | Team boundary + canonical source filter only |
| answer/context ID assembly | rewrite | structured RetrievalResult/evidence key；不生成answer/session |
| intent embedding cache/raw vector fetch | drop | no raw-vector API/cache product；query vector ephemeral |

Legacy是风险与实践证据，不是兼容输入。V1不导入legacy rows、IDs、index、threshold、API payload或历史vector，也不建设dual-read/cutover产品。

---

## 8. Acceptance Evidence

本节115项全部为HARD。实现任一失败即conformance/release blocked；不能用manual waiver、allowlist、provider成功率或“大部分query正确”绕过。

### 8.1 Registry、binding 与 embedding

| ID | Level | Scenario | Required evidence |
|---|---|---|---|
| ES07-A001 | HARD | fresh registry bootstrap | exact one active space与one policy安装，digest与code manifest一致 |
| ES07-A002 | HARD | second bootstrap | same rows/digests，zero mutation |
| ES07-A003 | HARD | same version drift | readiness false，safe diff指出definition key |
| ES07-A004 | HARD | unsupported projection schema | Workflow compile/readiness拒绝，不尝试embed |
| ES07-A005 | HARD | document recipe fixture | title/body canonical bytes与expected digest exact |
| ES07-A006 | HARD | query recipe fixture | normalized query与official prefix digest exact |
| ES07-A007 | HARD | CRLF/NFC variants | canonical equivalent产生相同input digest |
| ES07-A008 | HARD | empty/whitespace query | 422且provider calls=0 |
| ES07-A009 | HARD | oversize query | 422且无truncate/provider call |
| ES07-A010 | HARD | oversize block | Process rejected、manifest absent、无truncate |
| ES07-A011 | HARD | batch 16 inputs | 16 distinctContent→16 orderedoutputs |
| ES07-A012 | HARD | provider aggregates/wrong count | rejected outcome、无VectorBuildManifest |
| ES07-A013 | HARD | dimension不是768 | rejected outcome、VectorRecord absent |
| ES07-A014 | HARD | NaN/Infinity/bad norm | rejected outcome与safe finding |
| ES07-A015 | HARD | model/recipe/metric change | requires new space version；mixed same-version启动失败 |

### 8.2 Invocation、VectorRecord 与 manifest closure

| ID | Level | Scenario | Required evidence |
|---|---|---|---|
| ES07-A016 | HARD | real provider call | reservation及inputs commit先于network evidence |
| ES07-A017 | HARD | document invocation owner | exact Task/Execution/Process/fence，request owner null |
| ES07-A018 | HARD | query invocation owner | request UUID exact，Task/Execution/Process null |
| ES07-A019 | HARD | duplicate reservation same digest | same Invocation返回，无第二call |
| ES07-A020 | HARD | duplicate reservation different digest | integrity conflict，无call |
| ES07-A021 | HARD | provider usage absent | nullable usage，禁止填0 |
| ES07-A022 | HARD | crash after reservation | deadline scanner写indeterminate；不原位重发 |
| ES07-A023 | HARD | one projection block | one record with exact block/space/input/vector lineage |
| ES07-A024 | HARD | duplicate text in two blocks | two record identities，coordinate各自正确 |
| ES07-A025 | HARD | cross-Team same content | no shared record或FK |
| ES07-A026 | HARD | partial batch/build failure | no complete manifest/index candidate |
| ES07-A027 | HARD | full build | member count/set/digest exact等于projection |
| ES07-A028 | HARD | missing/extra/reordered member | finalize拒绝 |
| ES07-A029 | HARD | stale Process fence | record/manifest mutation拒绝，Outcome不提交 |
| ES07-A030 | HARD | success Outcome | contains manifest proof only，无vector bytes/next step |

### 8.3 Generation、filter 与 exact vector search

| ID | Level | Scenario | Required evidence |
|---|---|---|---|
| ES07-A031 | HARD | normal stage | immutable generation/input/membership/filter rows原子提交 |
| ES07-A032 | HARD | duplicate stage same digest | same generation，zero duplicate members |
| ES07-A033 | HARD | same idempotency different digest | integrity conflict |
| ES07-A034 | HARD | generation status inspection | schema无building/ready/active status列 |
| ES07-A035 | HARD | filter scalar types | string/integer/number/boolean/null canonical round-trip |
| ES07-A036 | HARD | filter scalar array | ordinals、typed index与set digest exact |
| ES07-A037 | HARD | filter unknown/type mismatch | generation rejected，不进入payload_extra |
| ES07-A038 | HARD | filter depth/value limits | bounded reject，无partial rows |
| ES07-A039 | HARD | context metadata as filter | rejected；只有filters object可投影 |
| ES07-A040 | HARD | filter-only change | new Revision generation；same projection/vector digests |
| ES07-A041 | HARD | content/context changed reuse attempt | rejected并要求full LS-RAG route |
| ES07-A042 | HARD | vector capability probe | vector32 decode/self-distance/order/tie fixture通过 |
| ES07-A043 | HARD | exact scan plan | onlyactive pointer memberships，普通B-tree filter，无ANN依赖 |
| ES07-A044 | HARD | distance ties | vector UUID tie-break跨重复运行一致 |
| ES07-A045 | HARD | caller injects SQL/path/operator | 422/parameterized query，无schema/SQL泄漏 |

### 8.4 Validation、publication、withdrawal 与 rebuild

| ID | Level | Scenario | Required evidence |
|---|---|---|---|
| ES07-A046 | HARD | valid candidate | 12-step report valid，counts/digests/lineage/filters exact |
| ES07-A047 | HARD | one missing vector | invalid report，PublicationProof absent |
| ES07-A048 | HARD | wrong Revision/Team/space | invalid report与safe finding |
| ES07-A049 | HARD | broken summary traceback | invalid report，不能publication |
| ES07-A050 | HARD | active first publication | proof+index pointer+Item serving+transitions same commit |
| ES07-A051 | HARD | new Revision publication | both pointers原子从old切new |
| ES07-A052 | HARD | same-Revision reindex | generation替换、Item row/proof revision前进 |
| ES07-A053 | HARD | invalid candidate while old serves | old serving/index未变化 |
| ES07-A054 | HARD | stale Item row revision | whole UoW rollback，typed conflict |
| ES07-A055 | HARD | stale index pointer revision | whole UoW rollback，typed conflict |
| ES07-A056 | HARD | duplicate publication command | same proof/transition，无双切换 |
| ES07-A057 | HARD | deactivated rebuild | validated_not_served proof；both pointers null |
| ES07-A058 | HARD | deleted rebuild | rejected，无proof/pointer mutation |
| ES07-A059 | HARD | deactivate/delete | serving先null；残留vector立刻不可retrieval |
| ES07-A060 | HARD | withdraw crash/replay | scanner收敛one null transition/one proof；不恢复serving |

### 8.5 Rebuild、cleanup 与 concurrency

| ID | Level | Scenario | Required evidence |
|---|---|---|---|
| ES07-A061 | HARD | team/source/item/revision rebuild scope | exact current target rules、immutable plan<=10000；historical/missing substrate whole reject |
| ES07-A062 | HARD | plan membership changes later | child usesfrozen set并以stale fence冲突，不重新枚举 |
| ES07-A063 | HARD | same-space rebuild child | vectors reused、new generation/proof、Revision不变 |
| ES07-A064 | HARD | new-space rebuild child | reembed→stage→validate；no mixed vectors |
| ES07-A065 | HARD | duplicate fan-out materialization | one child per plan item |
| ES07-A066 | HARD | partial rebuild failures | collect-all透明；successful children proof保留 |
| ES07-A067 | HARD | old generation after CAS | no longereligible；grace lineage仍可读 |
| ES07-A068 | HARD | cleanup before grace | rejected，无blob/row deletion |
| ES07-A069 | HARD | cleanup with active/history/plan/hold ref | rejected且列出safe reference class |
| ES07-A070 | HARD | eligible cleanup | one CleanupProof，deleted/retained counts可重算 |
| ES07-A071 | HARD | cleanup partial crash | no false complete；retry按subject/proof key收敛 |
| ES07-A072 | HARD | publication lock ordering | concurrent publish/reindex无deadlock/double success |
| ES07-A073 | HARD | publish vs lifecycle race | CAS first commit wins；最终dual fence一致 |
| ES07-A074 | HARD | cleanup vs new generation ref | reference CAS/transaction阻止use-after-delete |
| ES07-A075 | HARD | restore backup | vector/pointer/proof digest全检前readiness false |

### 8.6 Retrieval admission、eligibility 与 empty/error

| ID | Level | Scenario | Required evidence |
|---|---|---|---|
| ES07-A076 | HARD | successful query | Task/Audit/Execution/Process/outbox新增均为0 |
| ES07-A077 | HARD | query evidence | one query Invocation + one immutable receipt/hit set |
| ES07-A078 | HARD | query/filter privacy | DB/log/trace无原文，只有digest/length |
| ES07-A079 | HARD | Team scope | everyjoin/key includes Team；wrong-Team hits=0 |
| ES07-A080 | HARD | Item deactivated/deleted | hits=0即使vector仍存在 |
| ES07-A081 | HARD | serving Revision mismatch | 503 snapshot invalid，不fallback |
| ES07-A082 | HARD | active generation mismatch | 503 snapshot invalid，不fallback |
| ES07-A083 | HARD | unsupported/mixed space | 503 binding incompatible，无partial Item result |
| ES07-A084 | HARD | scope source+item | AND semantics与canonical dedupe exact |
| ES07-A085 | HARD | eq/in/exists filter | typed matching及heterogeneous schema semantics exact |
| ES07-A086 | HARD | path unsupported by all targets | 422 |
| ES07-A087 | HARD | no eligible knowledge | 200 empty/no_eligible_knowledge + snapshot evidence |
| ES07-A088 | HARD | eligible but below gate | 200 empty/no_semantic_match |
| ES07-A089 | HARD | provider/DB/integrity error | typed 5xx，绝不伪装empty |
| ES07-A090 | HARD | receipt persistence failure | 503且不返回semantic hits |

### 8.7 Recall、traceback、rerank 与 disclosure

| ID | Level | Scenario | Required evidence |
|---|---|---|---|
| ES07-A091 | HARD | four strata | each usesbounded recall formula/gate/tie-break |
| ES07-A092 | HARD | passage original hit | exact same original evidence/anchors returned |
| ES07-A093 | HARD | passage summary hit | summary matched + exact paired original returned |
| ES07-A094 | HARD | section summary hit | cited units bounded expansion + original traceback |
| ES07-A095 | HARD | document summary hit | cited units bounded expansion + original traceback |
| ES07-A096 | HARD | missing citation/pair/anchor | whole query 503，不skip/summary-only |
| ES07-A097 | HARD | same unit multi-channel | onehit，RRF sums best ranks并给agreement reason |
| ES07-A098 | HARD | RRF numeric fixture | score/order与golden decimals/tie-break exact |
| ES07-A099 | HARD | per-Item diversity pass | first pass cap3，second pass deterministic fill |
| ES07-A100 | HARD | duplicate pair | one evidence unit only |
| ES07-A101 | HARD | context budget | complete hit only，无正文截断 |
| ES07-A102 | HARD | budget too small for first hit | 422，不返回partial evidence |
| ES07-A103 | HARD | result provenance | Revision/commit/projection/generation/proof chain可重算 |
| ES07-A104 | HARD | public score explanation | similarity/RRF/channel ranks/closed reasons完整 |
| ES07-A105 | HARD | disclosure scan | no raw vector/query embedding/model/path/secret/final answer |

### 8.8 Failure、recovery 与 finite semantic gate

| ID | Level | Scenario | Required evidence |
|---|---|---|---|
| ES07-A106 | HARD | adapter hidden retry probe | one reservation对应至多one provider request |
| ES07-A107 | HARD | lost wake after manifest/candidate | ES-02 scanner重投route，无duplicate fact |
| ES07-A108 | HARD | active pointer corrupt target | readiness/query fail，no latest/previous fallback |
| ES07-A109 | HARD | same-version policy weight/gate drift | readiness false |
| ES07-A110 | HARD | 16-document fixture build | full publication、all lineage/proofs valid |
| ES07-A111 | HARD | vector recall metric | 32-query manifest中positive expected recall@20=100% |
| ES07-A112 | HARD | final relevance metric | positive grounded recall@5=100%、MRR@5>=0.75 |
| ES07-A113 | HARD | traceback metric | exact original anchor accuracy=100% |
| ES07-A114 | HARD | isolation/negative metric | leakage=0且all unrelated query no_semantic_match |
| ES07-A115 | HARD | model/space/index/policy change | full fixture rerun required；missing report blocksrelease |

### 8.9 必须交付的 evidence bundle

1. ES-05 registry manifest diff：六个Process、EmbeddingSpace、schemas与profile set-exact；
2. ES-04 24-table physical mapping、DDL/constraint/index manifest与fresh/bootstrap drift report；
3. document/query canonicalization golden fixtures；
4. provider mock/cassette：success/reject/timeout/wrong count/dimension/nonfinite/no usage；
5. projection→VectorRecord→manifest set-closure report；
6. filter schema/value flattening与typed query property tests；
7. vector32 capability、distance/tie exact SQL fixtures；
8. 12-step IndexValidationReport golden bundle；
9. publication/withdrawal/reindex transaction trace与crash matrix；
10. concurrency evidence：publish/publish、publish/lifecycle、cleanup/rebuild races；
11. dual-fence Team/lifecycle/serving/generation negative suite；
12. four-strata recall、RRF、hierarchy expansion、diversity与budget golden outputs；
13. result disclosure/redaction snapshot tests；
14. scanner/recovery/indeterminate/cleanup convergence traces；
15. immutable 16-document/32-query semantic benchmark manifest与metric report；
16. backup/restore vector/proof integrity report；
17. scope audit证明无raw-vector/final-answer/ANN/第二DB/新服务/第七StateFamily。

---

## 9. Remaining Technical Decisions and Defaults

### 9.1 已裁决 defaults

| Decision | V1 exact default | Change evidence |
|---|---|---|
| Embedding model | gemini-embedding-2 stable ID | official lifecycle + full reembed/semantic regression |
| Dimension | 768 | storage/cost/relevance benchmark + new space version |
| Metric | cosine distance | full generation/retrieval benchmark + new space/policy |
| Normalization | finite output norm 0.98..1.02 | provider/spec evidence + new space |
| Batch size | 16 distinctContent per call | provider quota/cost/crash evidence |
| Vector backend | embedded Turso vector32 BLOB | single-unit operability + backup + exact oracle evidence |
| Search | exact scan; noANN | ANN capability/recall oracle/resource evidence + new index policy |
| Similarity gate | 0.35 | fixed semantic fixture + new policy version |
| Recall | four strata，20..80 each | recall/cost evidence + new policy |
| Rerank | weighted RRF k=60 | semantic fixture + deterministic golden + new policy |
| Hierarchy expansion | max8 units/hit | relevance/context evidence |
| Public top_k | default10，max20 | measured resource and usefulness evidence |
| Context budget | default12000，1000..32000 scalars | payload/resource/fixture evidence |
| Active space count | exactly1 per release | incompatible-space migration proof |
| Query retry | zero internal retries | explicit future product/latency evidence；caller remains owner |

### 9.2 Provisional ceilings 与 measured binding

Owner没有吞吐、延迟、并发或容量SLA。为使exact scan在ES-08测量前fail-safe，V1初始技术guard为：

| Guard | Provisional hard value | Behavior at limit |
|---|---:|---|
| active vector memberships / Team | 50000 | newpublication拒绝并保持旧serving |
| active vector memberships / process DB | 200000 | readiness/admission closed for growth |
| concurrent retrievals / process | 4 | bounded queue后503 busy |
| retrieval total deadline | 10 seconds | 503，no hidden retry |
| provider embedding batch | 16 inputs | split deterministically |
| public top_k | 20 | 422 above |
| recall candidates total | 320 | four × max80 |
| rebuild plan items | 10000 | Task rejected above |

ES-08-v1.0已冻结`mkb-r1` reference profile、15分钟warm-up+30分钟steady/fault measurement和≥20%headroom规则。每个可部署build必须在目标硬件、真实pyturso build、代表性vector size和并发下验证这些ceiling；测得更低值时effective config必须降低。提高任何值需要new signed resource/backup/recovery/query correctness evidence，但不形成Owner SLA。超出guard不触发新服务、ANN集群、分片或第二DB。

### 9.3 Embedding space replacement boundary

V1只运行一个release-pinned active EmbeddingSpace；普通index.rebuild只能在该space内reuse或重新embed，不能选择或激活另一space。Model ID、dimension、recipe、normalization或metric改变时：

1. 必须新增ModelDefinition、EmbeddingSpace与RetrievalPolicy version，历史定义不改；
2. 必须全量重新embed目标projection并重建generation，不能reuse旧vector或混合score；
3. 必须通过完整publication、backup/restore与§4.13 semantic regression；
4. 必须在未来ES-07/08 minor revision中先冻结并验证quiesced all-active-set cutover方案；
5. 在该方案完成前，新space不得成为active，旧space继续服务或系统fail readiness；
6. public RetrievalSearch/Result contract保持不变，不制造IntakeRevision，也不开放migration/raw-vector产品。

当前V1明确不实现live/rolling embedding-space migration、dual-query、mixed-space merge或分批可见cutover。这一限制避免为假设性升级扩张状态、表、Workflow和运维产品；provider确需替换时属于有真实证据的后续execution revision，不需要Owner重新回答，除非外部能力/成功语义发生变化。

### 9.4 Rejected alternatives

| Alternative | Rejection reason |
|---|---|
| Cloudflare Vectorize / remote vector DB | 新backend/服务/transaction boundary且legacy绑定，无Owner需求 |
| libSQL ANN immediately | 当前embedded support boundary未闭合；精确scan足以建立correctness oracle |
| caller raw vector query/read/export | 直接违反Owner选择A与OT03-T032 |
| generic vector CRUD | 把MKB扩成vector database产品 |
| remote BGE/cross-encoder reranker | 增加provider、失败面、调用账与延迟；V1 deterministic RRF足够有限验收 |
| Gemini generative reranker | 同步query需新generative invocation/failure contract且可能生成非grounded判断 |
| FTS/hybrid search | 新索引/grammar/quality面；Owner只冻结semantic vector result |
| one global topK across channels | summary/original某通道可能挤出；不能证明双通道闭环 |
| no similarity gate | irrelevant query永远返回假相关知识，违反grounded empty语义 |
| legacy 0.65阈值照搬 | 模型/space不同且无本项目fixture证据 |
| silent skip corrupt candidate | 隐藏active index corruption和source loss |
| return summary when original missing | 违反mandatory traceback |
| rerank failure original order/dummy score | 伪造解释依据 |
| cache/persist query vectors | 增加敏感substrate/retention，V1无复用需求 |
| merge incompatible spaces | cosine不可比较且会产生rolling drift |
| vector row existence as eligibility | 绕过serving/publication双围栏 |

### 9.5 Closure

ES-07没有需要Owner回答的问题。Model、dimension、metric、storage、filter grammar、publication transaction、threshold、topK、ranking/rerank、benchmark数量和容量guard均是OT03/04明确下沉的executional design，本文件已在固定retrieval能力内给出有限默认、失败边界与改变证据。

本文件没有预留raw-vector、final-answer、hybrid search、ANN service或generic query language。六个manifest/EmbeddingSpace/schema已回填ES-05，24表/UoW已回填ES-04，rebuild/publication已校准ES-02/03，资源/secret/egress/metrics/runbook/release gate已由ES-08-v1.0闭合；八文件最终cross-spec audit已完成。

这些都是固定8文件内的实现闭包，不是新capability、Owner QNA或scope expansion。

---

## 10. Revision History

| 版本 | 日期 | 状态 | 变更 |
|---|---|---|---|
| ES-07-v0.1 | 2026-08-10 | internally-consistent / awaiting cross-spec audit | 继承OT-01..04、D01/D02、S04/S06及ES-01..06，冻结gemini-embedding-2 text-768 EmbeddingSpace、24张logical tables、六个Process contract、VectorRecord/IndexGeneration/PublicationProof/active pointer、filter-only reuse、withdraw/reindex/cleanup、embedded Turso exact cosine search、四strata recall、deterministic RRF、mandatory original traceback、public RetrievalSearch/Result、115项HARD acceptance与16-document/32-query semantic release gate。未新增raw-vector、final-answer、source、intent、Workflow、StateFamily、backend、服务、部署单元或spec文件。 |
| ES-07-v1.0 | 2026-08-10 | ready | 完成OT-01..04、S04/S06及ES-01..06/08最终对账；6个vector/index Process、24张owner tables、proof-valid dual pointer、唯一semantic Retrieval Result、115项HARD acceptance与16-document/32-query gate均已set-exact。未新增raw vector、final answer、ANN/第二DB、状态族、服务或spec文件。 |
