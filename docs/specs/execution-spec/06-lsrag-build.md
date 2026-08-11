# ES-06 — LS-RAG Build

> **项目**：`myknowledgebase`（MKB）
>
> **文件 ID**：`ES-06`
>
> **文档性质**：`execution-spec / implementation authority`
>
> **版本 / 日期**：`ES-06-v1.0 / 2026-08-10`
>
> **文档状态**：`ready`
>
> **Truth 输入**：`OT-01-v1.0`、`OT-02-v1.0`、`OT-03-v1.0`、`OT-04-v1.0`
>
> **Baseline 输入**：`D01-v1.4`、`D02-v1.0 / D02-DR005..006`、`S06 T-O-77..85`
>
> **上游 Execution Spec**：`ES-01-v1.0`、`ES-02-v1.0`、`ES-03-v1.0`、`ES-04-v1.0`、`ES-05-v1.0`
>
> **下游 consumer 校准**：`ES-07-v1.0`
>
> **上游索引**：`docs/specs/index.md`

本文件是 MKB 单体内部 Structurizer、Constructor、source grounding、original/summary 双通道、GenerationArtifact 历史/current selection 与 LS-RAG build proof 的唯一 Execution Spec。它把一个 exact accepted IntakeRevision 与 clean Artifact 转换为可由 ES-07 消费的 immutable、typed、source-grounded RetrievalBlockProjection；它不拥有 Intake truth、Workflow route、模型/provider、vector/index、retrieval ranking、内容编辑或最终答案。

---

## 1. Inherited Truth

### 1.1 权威输入

| 来源 | ES-06 继承 | 不得改变 |
|---|---|---|
| `OT-01-v1.0` | 一个 Python 应用/发布单元；MKB 只处理、转换、存储和获取 knowledge；LS-RAG 是核心闭环 | 不建设内容产品、通用 agent、上游业务或额外服务 |
| `OT-02-v1.0` | exact Intake identity、Task→Execution→Process、六个 StateFamily、derived asset 与 SelectionPointer 分账 | 不建 Generation/Block 状态机，不把 Block/GenerationArtifact 变成 IntakeArtifact 或 runtime 层 |
| `OT-03-v1.0` | Structurizer+Constructor、original/summary、traceback；immutable generation/invocation；per-type current；exact schema/kernel/extension | 不开放 artifact CUD、raw vector/final answer，不私建 retry 或 latest binding |
| `OT-04-v1.0` | source fidelity、silent-loss 禁止、full validation、lineage、crash/replay/cancel 收敛 | 文件存在、模型返回、局部校验或 pointer 单独存在均不构成成功 |
| `D01-v1.4` | Process 是 leaf work；Execution 是完整运行身份；derived asset 独立于 runtime | 不引入 Attempt、generation job 或 callback SSOT |
| `D02-v1.0` | state/fact/pointer/proof 正交；S06 exact artifact/node/anchor/block 由本文件关闭 | exact kind 不进入 D02 StateFamily；route 仍归 ES-02 |
| `S06 T-O-77..85` | immutable artifact/invocation、current CAS、Task-scoped read、versioned schema、kernel/extension repair、统一 retry | 不导入 S06 Q4–Q6 的 held/returned 草稿为 Owner Truth |
| ES-07-v1.0 | exact projection consumer、one block/one vector、four-strata retrieval与mandatory original traceback | ES-07不得rechunk/改anchor；publication失败不回写S06 truth |

### 1.2 Truth 到交付物映射

| Truth cluster | 本文件落点 |
|---|---|
| `OT02-T008..T018/T023`、`OT02-C008/C009` | §4.4–4.9 exact derived kinds、identity、lineage、pointer；§5 logical schema |
| `OT03-T026..T031`、`OT03-C011..C013` | §4 全链路、§5 API/ports/protocol、§6 repair/current consistency |
| `OT04-T021..T030`、`OT04-C008/C009` | §4.5–4.10 coverage/proof、§6 failure/recovery、§8 acceptance |
| `T-O-77..79` | §4.9 GenerationArtifact ledger/current/read；§5.2–5.4/5.11 |
| `T-O-80..82` | §4.3 exact StructureSchemaDefinition；§4.7 full validator |
| `T-O-83..85` | §4.7 extension-only repair；§6.3–6.6 no private retry/fallback |
| `D02-DR005/006` | §4.5/4.6 exact node/anchor/block；§6.1 no StateFamily；rebuild/retry不原位编辑 |

### 1.3 唯一 ownership

| Concern | Owner | ES-06 interaction |
|---|---|---|
| Task/Audit/Restart 与公共 auth/envelope | ES-01 | 提供 Task-scoped artifact read projection；不写 Task |
| Workflow、Execution、Process、claim/retry/cancel/route | ES-02 | 只消费两个 exact ProcessCommand 并提交 typed Outcome/proof |
| IntakeSource/Item/Revision/Artifact、clean、preflight/Gate | ES-03 | 只读 exact accepted Revision 与 selected clean Artifact；不回写或重清洗 |
| transaction、outbox、object bytes/reference | ES-04 | 使用 named UoW 与 logical object handles；不使用物理路径 |
| Capability/Schema/Model/Prompt/Profile、Invocation | ES-05 | ES-06 拥有语义定义，ES-05 存 exact registry/binding/call evidence |
| Structure、Construction、GenerationArtifact/current | ES-06 | 唯一语义与 mutation owner |
| embedding、vector/index、publication、retrieval/rerank | ES-07 | 只消费 exact accepted generation commit/projection |
| 配置、secret、资源包络、scanner/runbook | ES-08 | 可收紧预算和运营动作，不得改变 schema/repair/current 语义 |

### 1.4 证据使用边界

Legacy Structurizer/Constructor 仅提供以下 ReferenceAnchor：ordered layered structure、original/summary 两个检索通道、共享 traceback coordinate、typed I/O 和 source content 保留具有生产价值。以下 legacy 行为不是 Truth：flat `layered_content`、单文件覆盖、R2/D1/Worker 拓扑、模型生成 original text、JSON 截取/补逗号/补 context、KV Prompt、branch fallback、callback success、`file_uuid+block_id+granularity` 跨代坐标以及 parent/child metadata 混写。

S06 Q4–Q6 中未冻结的 clean curation、人工 patch、same-Execution 用户 retry 与一次性 GenerationCommit 提案不作为 Owner 输入。本文件只在现有边界内做有限执行裁决：无内容编辑；automatic retry 仍归 ES-02；V1 正常路径在 final full validation 时原子选择一个 coherent artifact bundle，但该事务设计不新增 Owner 承诺或公共 retry 能力。

---

## 2. Scope / Non-scope

### 2.1 Scope

1. `lsrag.structurize`、`lsrag.construct` 两个且仅两个 ProcessCapabilityManifest；
2. 一个完整、内部注册、immutable、versioned 的 StructureSchemaDefinition bundle；
3. exact source cutoff、SourceElement manifest、tree/node/anchor/coverage contract；
4. deterministic ConstructionUnit partition、original passage 与 passage/section/document summary 投影；
5. original/summary 共用 generation-local coordinate 和 exact source traceback；
6. strict shape→binding→kernel→extension→semantic/source→bundle validation；
7. extension-only、每 candidate 最多一次、全量复验的 agent repair；
8. GenerationArtifact/validation/repair immutable ledger、per-type current pointer 与 coherent generation commit；
9. Task-scoped list/get/current 元数据读面与 ES-07 internal projection read；
10. 21 张 logical owner tables、named UoW、typed commands/outcomes/events；
11. bounded window/merge/summary plan、failure/recovery/cancel/cleanup 规则和验收证据。

### 2.2 Non-scope

- 不定义新 request intent、source kind、Workflow、StateFamily、服务、部署单元或 public write capability；
- 不提供 clean curation、artifact edit/promote/delete/download、CMS、人工 structure patch 或跨 generation diff/mapping；
- 不生成或修改 IntakeRevision、clean Artifact、canonical metadata、filter authority 或 Item lifecycle；
- 不拥有 provider SDK、model、Prompt registry 物理实现、Invocation retry 或 token accounting；
- 不生成 embedding/raw vector，不选择 vector backend、active index、ranking/rerank 或 Retrieval Result；
- 不开放 generic Schema/Prompt/agent/plugin surface；
- 不提供 final answer、chat、session、citation presentation 或上游业务逻辑；
- 不以 fallback flat chunker、schema loosening、模型修补 kernel 或 silent discard 保证成功；
- 不读取 `latest` Revision/clean/schema/model/prompt/profile/current artifact；
- 不复制 legacy Cloudflare/R2/D1/Queue/callback contract。

### 2.3 完成定义

ES-06的`ready`是规范状态：以下义务已被完整定义并通过cross-spec audit，不表示它们已在尚未构建的实现上运行。任何实现要声明符合ES-06-v1.0并进入release，必须同时满足：

1. 两个 Process manifest 与 ES-02 catalog、ES-05 registry set-exact；
2. StructureSchemaDefinition 的 shape/kernel/extension/validators 和全部 consumer support 可重建同 digest；
3. 任意 full-valid StructureDocument 都有单 root、acyclic、ordered、complete、non-overlap source coverage；
4. 每个 passage unit 有 exact original block 和 grounded summary block；section/document summary 可回溯全部 descendant source；
5. every invocation/output/repair/candidate 有 durable causation；invalid artifact 不可 current；
6. final commit 的五类 artifact 同 source、schema、Execution 与 generation，pointer CAS 与 Process success 不可分裂；
7. crash、duplicate、stale fence、retry、cancel、missing object 和 repair failure 均 fail-closed 且历史不断；
8. Task-scoped read 不泄漏 Execution/Process/fence/path/raw provider output；
9. ES-04/05/07 完成 physical/registry/consumer cross-spec calibration；
10. §8 全部 HARD acceptance 和 evidence bundle 通过。

### 2.4 核心术语

| Term | Exact meaning |
|---|---|
| SourceElementManifest | 对 exact clean Artifact 的 immutable、ordered、loss-aware element/fragment/anchor 清单 |
| StructureDocument | 由 generation-local node tree 与 exact source anchors 构成的 original structure artifact |
| ConstructionDocument | 对 StructureDocument 进行 deterministic unit partition并附加 governed summaries 的 artifact |
| RetrievalBlockProjection | ES-07 唯一可消费的 ordered block/coordinate/traceback artifact；不含 vector |
| GenerationArtifact | 一份 immutable logical file及其 exact binding/causation/validation disposition |
| GenerationCommit | 五类 full-valid artifact 的 coherent accepted bundle fact；不是 StateFamily 或 serving pointer |
| CurrentPointer | `(team,execution,artifact_type)` 的 CAS selection；不等于 latest Revision 或 active index |
| Deterministic kernel | identity、binding、tree/order、coordinate、source fidelity、coverage、original bytes 与 proof |
| Governed extension | schema 登记且允许模型产生/修复的 normalized title 与 summary sentence/citation 字段 |
| Passage pair | 同一 ConstructionUnit 的 `original` 与 `summary` 两个 RetrievalBlock，共享 pair/anchor coordinate |

---

## 3. Scope Impact Audit

```text
Scope Impact Audit
- New product responsibility: no
- New externally visible behavior: no (only the already-frozen Task-scoped read is specified)
- New V1 capability: no
- New domain identity or StateFamily: no
- New deployment/runtime unit: no
- New owner-truth file: no
- New execution-spec file: no (this is the fixed ES-06 slot)
- Raises a fixed capacity ceiling: no
- Can be solved inside an existing file and boundary: yes
- Classification: no expansion
```

Exact artifact/node/anchor/block kinds、21 张 owner tables、四个 Prompt/Profile 和数值预算只实现 OT-03 已冻结的 Structurizer+Constructor+双通道能力。它们不增加 source、intent、public product、provider、service、StateFamily 或 spec 数量；section/document summary 只是在同一既有 LS-RAG 构建责任内形成有限三层投影。

---

## 4. Architecture Decisions

### 4.1 单体内部模块与依赖

```text
lsrag.domain
  ├─ schema_contract
  ├─ source_elements / anchors / coverage
  ├─ structure_tree / construction / projection
  └─ generation_artifact / validation / current_selection

lsrag.application
  ├─ structurize_handler
  ├─ construct_handler
  ├─ generation_commit_service
  └─ artifact_query_service

lsrag.adapters
  ├─ ES-03 accepted-input reader
  ├─ ES-05 registry + inference ports
  ├─ ES-04 object + UoW repositories
  └─ ES-01 HTTP projection / ES-07 internal projection reader
```

Domain/application 不导入 provider SDK、Turso driver、filesystem path、HTTP router、Workflow repository 或 vector backend。Handler 只接收一个 ProcessCommand；不得调用 `next_step`、修改 Task/Execution/Process、读取 caller token 或直接发布 index。

### 4.2 两个 exact Process capability

| Process key / v1 handler | Typed input | Typed output | Side effect / retry |
|---|---|---|---|
| `lsrag.structurize` / `lsrag_structurize_v1` | exact accepted Item+Revision、selected clean Artifact+anchor/loss evidence、StructureSchema ref、structurize Prompt/Profile refs、budget plan | full-valid SourceElementManifest、StructureDocument、ValidationReport artifact refs + `StructureProofV1` | `non_replayable` external inference；known retryability由manifest→ES-02；unknown dispatch不得私自重发 |
| `lsrag.construct` / `lsrag_construct_v1` | exact structurize outputs、same clean/Revision/schema、construct/repair Prompt/Profile refs、construction budget | coherent GenerationCommit、ConstructionDocument、RetrievalBlockProjection、final ValidationReport refs + `LsragBuildProofV1` | `non_replayable` inference + transactional sink；final commit用sink-owned idempotency；retry只由ES-02 |

共同规则：

1. contract version 为 `1`，ProcessCommand 必须含 manifest digest、schema/profile/prompt/model exact refs、current claim fence和完整 input digest；
2. `lsrag.construct` 只能消费其 Workflow predecessor Outcome 中的 exact artifact UUID/digest，不能按 current/latest 查询；
3. known provider/schema/semantic failure以 typed failed Outcome交回 ES-02；handler内部没有 backoff、sleep、重新 dispatch 或 route；
4. 一个 Process retry保留 Process identity并创建新的 Invocation/GenerationArtifact；`retry_count`只是 ES-02 fact，不是 Attempt identity；
5. success proof 不含 next step；ES-02 根据 compiled route 唯一 materialize `vector.embed`。

### 4.3 Exact StructureSchemaDefinition 与 inference bundle

#### 4.3.1 Schema authority

ES-06 语义拥有一个 definition：`schema_key=lsrag.structure`、`schema_version=1`。ES-05 使用既有 `schema_definitions/schema_definition_components/schema_consumer_support` 存储；definition canonical digest覆盖下列全部 components，缺一即不是同一版本：

| Component key | Role |
|---|---|
| `mkb.lsrag.source-element-manifest.v1` | ordered source elements、fragments、anchor evidence、loss/coverage basis |
| `mkb.lsrag.structure-document.v1` | envelope、node tree、anchors、bindings、coverage proof |
| `mkb.lsrag.construction-document.v1` | construction units、summary sentences/citations、partition proof |
| `mkb.lsrag.retrieval-block-projection.v1` | block kinds/channels、pair coordinate、ordered traceback |
| `mkb.lsrag.generation-validation-report.v1` | validation stage、finding、artifact/bundle proof |
| `mkb.lsrag.structure-proposal.v1` | window/global model proposal；只可引用 engine element/node proposal keys |
| `mkb.lsrag.summary-proposal.v1` | passage/section/document summary sentences与citation keys |
| `mkb.lsrag.extension-repair.v1` | exact allowed JSON pointers及replacement values；禁止 kernel |

Definition 同时登记：strict JSON/relational shape、closed enums、kernel path set、extension path set、validator key/version/digest、canonicalization recipe、limit profile、consumer support。Same key/version/same digest 幂等，异digest启动 readiness failure；升级只新增 version。ES-02 compile与ES-07 consumer必须声明 exact digest support，历史 artifact 永远按自身 ref解释。

#### 4.3.2 Prompt / Profile bundle

| Prompt key/version | Profile key/version | Model | 允许输出 |
|---|---|---|---|
| `lsrag.structurize.window/1` | `lsrag.structurize.window/1` | `gemini-3.6-flash/1` | 对固定 ordered leaves给出compatible closed leaf kind、parent及局部container hierarchy；不得写 original text/ID/anchor |
| `lsrag.structurize.merge/1` | `lsrag.structurize.merge/1` | same exact model | 对连续 window roots增加有限全局 section hierarchy；不得删除、重复或重排 child |
| `lsrag.construct.summary/1` | `lsrag.construct.summary/1` | same exact model | passage/section/document summary sentences，每句引用允许的 source/unit keys |
| `lsrag.extension.repair/1` | `lsrag.extension.repair/1` | same exact model | 只返回 validator给出的 extension JSON pointers 与replacement；最多一次 |

所有 Prompt 使用 ES-05 有限模板 grammar，source body作为typed content part而非插值。Tool、search、code、Files API、provider retry、caller override与 fallback均关闭。Profile锁定 input/output schema、validator、budgets、one-candidate、no sampling、medium thinking和 exact model；任何变化创建新 Profile/Workflow revision，不热切 existing Execution。

### 4.4 RAG admission cutoff 与 SourceElementManifest

#### 4.4.1 Cutoff

唯一 cutoff 是 ES-02 将 `lsrag.structurize` ProcessCommand 及其 `command_digest` durable materialize 的提交点。Command必须锁定：

```text
team/task/current-generation/root/execution/process/fence
intake_item_uuid + intake_revision_uuid + revision_fingerprint
clean_artifact_uuid + content_digest + size + media/schema
anchor_manifest + loss_flags + quality evidence digests
schema + capability + model + prompt + profile exact refs/digests
budget profile + complete input digest
```

materialize 前只有 ES-03 的既有 Gate/reclean 路径可以改变 selected clean candidate；materialize 后 ES-06 永久读取 command 中的 exact input。Retry/recovery不得读取 later clean/current/latest。若需要重新清洗或重建，当前 Task按原语义收敛后走既有 causal rebuild/new Execution，不在 ES-06 编辑。

#### 4.4.2 Deterministic source normalization

Object reader先完成 team/owner/digest/size验证，再将 clean Artifact解析为 canonical UTF-8 stream。Normalizer：

1. 优先消费 ES-03 anchor manifest中的 ordered elements；纯文本无element时按 paragraph/line/page-break稳定切分；
2. 原始 element kind 只映射到 `text/heading/paragraph/list_item/table_cell/code_block/quote/media/caption/page_break` source hints；未知非空kind fail-loud；
3. 超过 `2,048` Unicode scalar或`8 KiB` UTF-8 的text element按 sentence→line→scalar边界稳定分片；不得丢字、改字或模型分片；
4. 每个manifest row记录canonical coordinate与`element_role=indexable|boundary|ignorable`：indexable fragment有byte span/content digest，page break是boundary，只有schema登记reason/evidence的whitespace/layout/loss span可为ignorable；
5. `source_element_key=e_` + base32(SHA-256(clean digest + ordered source coordinate + fragment ordinal))前26字符；
6. manifest按element/fragment ordinal排序并计算element/root/coverage digest；相同输入与recipe必须 byte-identical；
7. empty或只有registered ignorable spans的文档以 `no-indexable-content`失败，不生成空成功。

SourceElementManifest 是 `source_element_manifest` GenerationArtifact。它引用 clean bytes，不复制或改写 canonical truth；its object只保存 element/anchor/proof结构。

### 4.5 Exact StructureDocument：tree、node、anchor、coverage

#### 4.5.1 Closed node kinds

| Class | Node kinds | Rule |
|---|---|---|
| root | `document` | 恰一、parent null、sibling ordinal 0 |
| container | `section`、`list`、`table`、`table_row`、`figure_group` | 至少一个descendant leaf；无primary source bytes |
| leaf | `heading`、`paragraph`、`list_item`、`table_cell`、`code_block`、`quote`、`media`、`caption` | 恰一 source fragment；全局 reading ordinal连续 |

不提供 `other/custom/plugin` kind。Normalizer产生全部leaf identity/bytes/order；模型只能在schema compatibility matrix内指定leaf kind、增加container及leaf parent assignment，不能生成/删除/复制/拆分leaf。`heading/list_item/table_cell/code_block/quote/media/caption` source hint只能映射同名leaf；`text/paragraph`只可映射`heading|paragraph|code_block|quote`。`page_break`只作为source boundary evidence，不成为可检索node。

#### 4.5.2 Tree coordinate

每个 StructureDocument 的 node identity只在该 generation内稳定：

```text
node_key = "n_" + base32(
  SHA-256(schema_digest || structure_artifact_uuid ||
          parent_coordinate || node_kind || sibling_ordinal ||
          ordered_descendant_or_leaf_anchor_digest)
)[0:26]
```

Engine在完整树验证后按root preorder赋值；模型不得提交 `node_key`。每个非root node恰一parent；`depth`从0连续，`sibling_ordinal`从0无洞，leaf `reading_ordinal`从0无洞且严格保持SourceElement顺序。Identity不承诺跨Generation相同，禁止以node key做diff、patch或latest查找。

#### 4.5.3 Closed anchor kinds

| Kind | Exact coordinate | Use |
|---|---|---|
| `text_span` | clean Artifact UUID/digest + canonical UTF-8 byte `[start,end)` | 文本 primary coverage；边界必须落在UTF-8 code point |
| `element_span` | clean Artifact UUID/digest + source element key + local byte `[start,end)` | JSON/HTML/table等元素内 exact coordinate |
| `page_region` | source page ordinal + page Artifact/evidence digest + integer bbox `(x0,y0,x1,y1)` in `[0,1_000_000]` | OCR/media supporting grounding；必须带loss/quality evidence |

每个anchor另含 `anchor_key`、ordinal、`coverage_role=primary|supporting`、source IntakeArtifact/ref digest和evidence digest。每个leaf恰一text/element primary，page_region只能supporting；media只有在ES-03 clean结果已经提供caption/OCR等canonical text span时才可进入可检索tree，并同时保留page_region。Required media没有canonical text时以`non-text-without-clean-text`阻断build，不伪造text span、不用summary代替original。Anchor key同样由exact coordinate canonical hash产生。

#### 4.5.4 Full structure invariants

Validator必须证明：

1. one root、all nodes reachable、acyclic、closed kinds、合法parent/child matrix、depth/sibling/preorder一致；
2. every indexable source fragment恰一leaf，every leaf恰一indexable fragment，reading order与source ordinal相同；boundary/ignorable row不得成为leaf；
3. primary text/element spans有界、非空、无overlap；所有required content bytes恰好覆盖一次，且每个required source element恰一leaf；
4. 未覆盖bytes只能出现在 manifest登记的 `whitespace/layout/loss-evidence` ignorable spans，带reason/digest；
5. supporting region必须归同一source/page且坐标合法；OCR/Vision derived region不能升级为exact text claim；
6. original leaf payload只能由verified clean bytes slice产生，digest必须重算相等；
7. model proposal引用集合与engine leaf集合set-equal，leaf kind满足source-hint compatibility，且不能 reorder/drop/duplicate；
8. normalized title若存在只属于extension，不改变heading original或tree coordinate；
9. node/anchor/coverage/root digests可从normalized rows确定性重建；
10. 任一失败归类为kernel/source-proof invalid，不允许agent repair。

### 4.6 Constructor、双通道与 RetrievalBlockProjection

#### 4.6.1 Deterministic ConstructionUnit partition

Constructor按leaf reading order做一次确定性partition：

1. unit只包含连续leaf，不重叠、不回序，每个leaf恰属一个unit；
2. target `1,600` Unicode scalar，soft minimum `400`，hard maximum `3,200`且UTF-8最多`16 KiB`；
3. 达target后优先在section/list/table边界结束；未达minimum可跨相邻同section leaf；不得跨document；
4. 上游 fragment已保证单leaf可放入hard max；若仍超限说明schema/recipe drift并失败，禁止截断；
5. `unit_key=u_` + hash(schema/structure artifact/first-last reading ordinal/ordered leaf keys)；
6. unit original payload是从首primary span start到末primary span end的 exact clean byte slice；无text的media unit使用clean manifest登记的caption/OCR text与page evidence，不能由summary冒充original；
7. context path由ancestor original heading slices确定性生成；canonical filters只按 exact IntakeRevision metadata ref复制引用，模型不能新增/merge/覆盖。

#### 4.6.2 Summary graph

Summary generation固定三层：

| Level | Inputs | Required output / grounding |
|---|---|---|
| `passage` | 一个ConstructionUnit exact original + context path | 1..8 sentences；每句引用该unit内至少一个 source element key |
| `section` | 一个section的ordered passage summaries，最多64个child；超出按连续group递归汇总 | 1..8 sentences；引用descendant unit keys，不能引用外部unit |
| `document` | ordered top-level section/passage summaries | 恰一个document summary；引用descendant unit keys |

Batch最多16个目标、`64 KiB` verified input、每target summary最多`768` Unicode scalar/`4 KiB`。Batch plan在首次call前完整物化并以digest锁定；call按 `(level,target_ordinal,batch_ordinal)`稳定顺序执行。每个call独立 GenerationInvocation，遗漏/重复/unknown target或citation即extension invalid。Summary不改变original、tree、unit、anchor、metadata或coordinate。

#### 4.6.3 Exact block kinds/channels

| `block_kind` | Allowed channel | Cardinality |
|---|---|---|
| `passage` | `original`、`summary` | 每unit恰一original+一summary，组成passage pair |
| `section` | `summary` only | 每个含至少一个unit的section恰一；large section的中间rollup只留ConstructionDocument内部，不投影为额外block |
| `document` | `summary` only | 每projection恰一 |

`pair_key=p_`由construction artifact+unit key产生；passage original/summary共享pair、unit、primary anchor set与source span。`block_key=b_`由projection artifact+block kind+channel+target key产生。Section/document summary保存descendant unit range与ordered anchor binding；不存在巨大“section original”复制，也不存在无original traceback的summary。

RetrievalBlock只含 text、kind/channel、ordinal、tree path、unit/target refs、anchor refs、canonical context/filter refs、summary invocation ref、content/proof digest和预算统计；不含 embedding/vector、backend ID、score、serving status或final answer。ES-07只能按 projection read port消费，不可重新切块、重写original或另造坐标。

### 4.7 Validation 与 extension-only repair

#### 4.7.1 固定 validation order

```text
1 strict shape / closed enum / size
2 exact team-source-schema-profile-model-prompt binding
3 deterministic kernel: identity/tree/order/coordinate/original/partition
4 governed extension: normalized title/summary/citations only
5 semantic + source proof: coverage/lineage/grounding/loss/metadata authority
6 final bundle coherence and object/reference verification
```

每次运行从step 1开始；finding按stage→code→JSON pointer稳定排序，report digest由完整finding set计算。第一失败stage决定 artifact `validation_disposition`：`shape_invalid/binding_invalid/kernel_invalid/extension_invalid/semantic_invalid/source_proof_invalid/bundle_invalid`；全通过为`full_valid`。这是immutable outcome fact，不是status。

#### 4.7.2 Kernel 与 extension path

Kernel包括所有 envelope identity/binding、source elements、artifact/clean/revision refs、node/parent/kind/order/depth、anchors、coverage、unit partition、block coordinate/kind/channel、original content/digest、metadata authority、proof和current membership。任何 kernel finding：

- 保存已形成的 candidate Artifact、ValidationReport 与 Invocation；
- repair transport call count必须为0；
- 返回 typed failure给 ES-02，由其 error policy决定 Process retry/fail。

Governed extension仅允许：

```text
/nodes/*/normalized_title
/construction_summaries/*/sentences/*/text
/construction_summaries/*/sentences/*/citation_source_element_keys
```

Extension invalid时每个candidate最多一次repair pass：validator提供 exact allowed pointers与finding，不向agent开放任意patch；repair输出必须set-equal这些或其允许子集，任何额外pointer立即kernel-policy violation。Repair创建新Invocation、新logical object、新GenerationArtifact、`repaired_from_artifact_uuid`与changed-field ledger；original candidate immutable。

Repair后从step 1完整复验。成功才可派生新projection并参与commit；失败不再repair，交回ES-02。不得extract braces、补逗号、补字段、局部复验、放宽schema、删除失败unit或切换profile/model。

### 4.8 Bounded structurize plan

为避免 legacy “整份plainText一次call”与provider隐式截断，plan固定：

1. clean canonical stream最大`64 MiB`，source elements/fragments最多`262,144`，tree nodes最多`393,216`，depth最多`32`；超过即`lsrag-source-budget-exceeded`；
2. window最多`64 KiB` original bytes或`256` leaves，保持连续、不重叠；最多`2,048` windows；
3. engine先固定leaf identity/bytes/order，window call只产生compatible leaf kind/parent与container proposal；每window output最多`1 MiB`/`1,024`containers；
4. global merge每call fan-in最多`64` ordered roots，只允许创建section containers和连续parent grouping；最多3层；
5. 所有window/merge invocation plan在dispatch前持久化为 input digest的一部分；无动态“再试一次”或provider truncation；
6. 一个known failed call使本次Process failed；已有Invocation与artifact/object history保留，ES-02 retry从exact command重建完整plan；
7. no partial resume：不能跳过failed window，也不能把不同Process retry的window outputs拼成一个accepted artifact；
8. concurrency遵守ES-05 `process=1`，在单Process内顺序dispatch；全局/team backpressure由ES-05/08执行。

这些值是安全围栏而非吞吐SLA。ES-08可在实测后收紧；放大必须新Profile/Workflow revision并通过memory/token/failure evidence，不能热改。

### 4.9 GenerationArtifact、current pointer 与 coherent commit

#### 4.9.1 五个 exact artifact types

| artifact_type | Logical content | Current eligibility |
|---|---|---|
| `source_element_manifest` | elements/fragments/anchor/loss/coverage basis | final bundle成员且full-valid |
| `structure_document` | exact tree/nodes/anchors/coverage | final bundle成员且full-valid |
| `construction_document` | units、summary graph、partition/grounding proof | final bundle成员且full-valid |
| `retrieval_block_projection` | ordered blocks/pairs/traceback | final bundle成员且full-valid |
| `generation_validation_report` | final complete validation/bundle report | report自身shape/binding valid且covered bundle full-valid |

每次 generation、Process retry或repair只要形成logical output，就创建一个GenerationArtifact；一个record只对应一个immutable object handle/digest。Raw provider response由ES-05 Invocation output账保护，不重复伪装成第六 artifact type。Artifacts可full-valid但非current；invalid永远只留history。

#### 4.9.2 Pointer 与 bundle规则

每个 `(team_uuid,execution_uuid,artifact_type)`最多一个current row，指向同Execution、same accepted Revision/clean/schema且`full_valid`的Artifact。Pointer不含路径，`pointer_revision`从1递增；任何改变append transition并记录before/after、expected revision、commit、Process/fence与proof。

V1 `lsrag.construct`完成时使用一个 `lsrag_generation_accept_v1` UoW：

```text
verify current Process/fence + exact command/input digest
verify five artifact types set-equal and every artifact full-valid/live
verify same team/task/execution/revision/clean/schema/generation coordinate
insert immutable GenerationCommit + five membership rows
CAS all five current pointers (null→artifact, or exact same replay)
append five pointer transitions
accept ES-02 ProcessOutcome + route/next materialization/outbox
append domain events
COMMIT
```

任一步失败whole rollback，因此不存在pointer已切但Process未成功、五类指向不同代或next Process读取半bundle。Same commit digest replay返回原receipt；任一既有pointer不同、member digest不同或stale fence均conflict，不覆盖。Schema保留完整transition能力以满足T-O-78，但V1正常workflow不会在已成功Execution内做第二次不同commit；用户retry语义继续由ES-01/02既有Task generation/rebuild决定，而不是本文件新增API。

ES-07只消费 ProcessOutcome中的 exact `generation_commit_uuid + retrieval_block_projection artifact UUID/digest`；不得枚举current猜输入。S06 current不是serving/active index pointer。

### 4.10 完整执行链与原子边界

#### 4.10.1 Structurize

```text
receive/verify current ProcessCommand + fence
→ load exact accepted Revision/clean Artifact and verified bytes
→ deterministic SourceElementManifest + window/merge plan
→ for each planned call:
     ES-05 reserve Invocation before dispatch
     dispatch once; record output/outcome/token
→ strict proposal parse (no coercion)
→ engine builds leaves/containers, assigns node/anchor coordinates
→ full structure validation
→ promote immutable objects
→ lsrag_structurize_finish_v1:
     GenerationArtifacts + reports + object refs
     ES-02 Outcome acceptance + exact construct materialization/outbox
→ commit
```

Invalid output仍通过`lsrag_artifact_finalize_v1`登记artifact/report/ref后提交 failed Outcome；登记失败不得把模型输出当作不存在，scanner必须从Invocation output/object reservation恢复账或标P0 integrity incident。

#### 4.10.2 Construct

```text
verify exact predecessor artifact refs/digests + current fence
→ deterministic ConstructionUnit partition
→ materialize summary batch plan
→ reserve/send/record every summary Invocation once
→ build immutable candidate ConstructionDocument + Projection
→ full validation
→ if and only if extension invalid and policy allows:
     one repair Invocation → new ConstructionArtifact/Projection
     record changed fields → validate from step 1
→ promote final report object
→ lsrag_generation_accept_v1 atomic five-artifact/current/Outcome/wake commit
```

Cancel/deadline在每次dispatch前、object promotion前与UoW前检查。Cancel赢后不dispatch新call、不commit current；已经返回的call仍写Invocation outcome，已形成output仍写Artifact history。已接受commit后cancel不能撤销或删除truth，ES-02按forward-stop收敛。

### 4.11 ES-07 exact consumer handshake

ES-07-v1.0关闭本文件此前移交的consumer槽位：

1. ES-05 schema_consumer_support登记ES-07对mkb.lsrag.retrieval-block-projection.v1 exact digest的consume支持；
2. vector.embed只能按GenerationCommit+Projection UUID/digest读取，不得枚举S06 current；
3. 每个projection block在一个EmbeddingSpace中恰有一个VectorRecord；重复文本也保持不同block coordinate；
4. block正文进入embedding recipe可以增加title/prefix，但不得trim/truncate/rewrite block content或改content digest；
5. passage/original、passage/summary、section/summary、document/summary exact映射ES-07四个recall strata；
6. passage pair/unit/anchor refs原样进入IndexGeneration membership与retrieval provenance；
7. section/document summary expansion只按本文件summary citations映射source elements/units，不生成新block或坐标；
8. summary matched result必须附本文件exact original passage与anchors；缺失是active index/query integrity failure；
9. target Revision filter rows来自ES-03 canonical filters，RetrievalBlock context/filter refs只作lineage校验，不取得metadata mutation权；
10. embedding/index/publication/retrieval失败不删除、回滚或改写GenerationCommit、五类current pointers或artifact history。

该handshake不把VectorRecord、IndexGeneration、score或serving status加入S06 schema；二者继续由ES-07持有。

---

## 5. Contracts and Data

### 5.1 总体 schema 规则

ES-06 21张tables全部遵守ES-04：STRICT、UUIDv7、UTC RFC3339、lower-hex SHA-256、canonical JSON object、team复合fence、`ON DELETE RESTRICT`、非空`payload_extra`。Logical object使用handle+digest+size且有live `object_reference`；核心identity/binding/state-equivalent fact/pointer/proof不得只存JSON。Artifact/commit/report/tree/construction/projection/repair rows无delete/update repository；只有current pointer CAS mutation。

### 5.2 Generation artifact ledger：5 tables

#### 5.2.1 generation_artifacts

```text
team_uuid, generation_artifact_uuid PK
task_uuid, task_generation, root_execution_uuid, execution_uuid
producer_process_uuid, producer_fencing_generation, process_retry_count
artifact_type
intake_item_uuid, intake_revision_uuid, clean_artifact_uuid
structure_schema_key/version/digest
capability_key/version/digest, profile_key/version/digest nullable
model_key/version/digest nullable, prompt_key/version/digest nullable
logical_object_handle, content_digest, size_bytes, media_type
validation_disposition
causation_kind, predecessor_artifact_uuid nullable, repaired_from_artifact_uuid nullable
artifact_ordinal, input_set_digest, artifact_envelope_digest
created_at, payload_extra
```

`artifact_type`只允许§4.9.1五值；`validation_disposition`只允许`full_valid/shape_invalid/binding_invalid/kernel_invalid/extension_invalid/semantic_invalid/source_proof_invalid/bundle_invalid`。Artifact immutable；`UNIQUE(team,execution,artifact_type,artifact_ordinal)`、`UNIQUE(team,generation_artifact_uuid,content_digest)`。Repair必须同type/same binding并填`repaired_from`；非repair为空。Nullable profile/model/prompt只允许pure deterministic source/report artifact。

#### 5.2.2 generation_artifact_inputs

```text
team_uuid, generation_artifact_uuid, input_ordinal PK
input_kind, input_owner_uuid, input_artifact_type nullable
input_schema_ref nullable, input_digest, input_size_bytes nullable
relationship_kind, required
created_at, payload_extra
```

`input_kind`固定为`intake_revision/intake_artifact/generation_artifact/invocation_output/schema_definition/validation_report`；owner必须same Team或global schema。Ordered set digest必须等于artifact envelope的`input_set_digest`。

#### 5.2.3 generation_artifact_invocations

```text
team_uuid, generation_artifact_uuid, invocation_ordinal PK
invocation_uuid, relationship_kind
invocation_request_digest, invocation_outcome_digest nullable
created_at, payload_extra
UNIQUE(team_uuid, invocation_uuid, generation_artifact_uuid, relationship_kind)
```

Relationship只允许`produced_by/validated_with/repaired_by/derived_from`。FK必须解析到ES-05 exact same Team/Process/binding Invocation；artifact无模型调用时允许零行。

#### 5.2.4 generation_validation_reports

```text
team_uuid, validation_report_uuid PK
report_artifact_uuid UNIQUE
subject_kind, subject_artifact_uuid nullable, subject_artifact_set_digest nullable
validator_key/version/digest
structure_schema_key/version/digest
stage_set_digest, finding_set_digest
shape_verdict, binding_verdict, kernel_verdict, extension_verdict
semantic_verdict, source_proof_verdict, bundle_verdict
overall_verdict, first_failure_stage nullable
validated_object_set_digest, validated_at, payload_extra
```

`subject_kind=artifact|artifact_set`；artifact时填写subject artifact UUID，final bundle validation时填写尚未提交的canonical artifact-set digest，二者XOR，从而不制造Report↔Commit循环FK。Stage verdict=`passed|failed|not_applicable`；overall=`full_valid|invalid`。Full-valid要求所有applicable stage passed、finding set无error。Report artifact自身以strict shape/binding guard验证，不递归要求一份“验证report的report”。

#### 5.2.5 generation_validation_findings

```text
team_uuid, validation_report_uuid, finding_ordinal PK
stage, severity, code, json_pointer
subject_ref, expected_digest nullable, actual_digest nullable
repair_classification, safe_detail
finding_digest, payload_extra
```

排序必须稳定；severity=`error|warning|info`，repair classification=`kernel_forbidden|extension_allowed|not_repairable`。`safe_detail`有界且不得含source body、prompt、provider raw response、secret/path/stack。

### 5.3 Current selection 与 commit：4 tables

#### 5.3.1 generation_artifact_current_pointers

```text
team_uuid, execution_uuid, artifact_type PK
generation_artifact_uuid UNIQUE within execution/type
generation_commit_uuid
pointer_revision
selected_by_process_uuid, selected_by_fencing_generation
validation_report_uuid, selected_at, payload_extra
```

FK验证same team/execution/type、artifact full-valid、commit membership及live object。Mutation仅compare-and-set；不提供generic update/delete。

#### 5.3.2 generation_artifact_pointer_transitions

```text
team_uuid, pointer_transition_uuid PK
execution_uuid, artifact_type
before_artifact_uuid nullable, after_artifact_uuid
expected_pointer_revision, resulting_pointer_revision
generation_commit_uuid, process_uuid, fencing_generation
validation_report_uuid, causation_uuid, transition_digest
transitioned_at, payload_extra
```

Append-only；初次选择before null/revision0→1。Same transition digest replay幂等，different after/conflicting revision失败。

#### 5.3.3 generation_commits

```text
team_uuid, generation_commit_uuid PK
task_uuid, task_generation, root_execution_uuid, execution_uuid
construct_process_uuid, fencing_generation
intake_item_uuid, intake_revision_uuid, clean_artifact_uuid
structure_schema_key/version/digest
artifact_set_digest, validation_report_uuid
input_command_digest, build_coordinate_digest, commit_digest
committed_at, payload_extra
```

Immutable；`UNIQUE(team,construct_process_uuid,input_command_digest,commit_digest)`。Commit不含status/current/serving字段；存在即代表本UoW accepted的coherent bundle fact。

#### 5.3.4 generation_commit_artifacts

```text
team_uuid, generation_commit_uuid, artifact_type PK
generation_artifact_uuid
content_digest, membership_ordinal
payload_extra
UNIQUE(team_uuid, generation_commit_uuid, membership_ordinal)
UNIQUE(team_uuid, generation_commit_uuid, generation_artifact_uuid)
```

每commit必须set-exact五类且ordinal按§4.9.1固定0..4；所有member同binding/full-valid，member set canonical digest等于commit。

### 5.4 Structure：5 tables

#### 5.4.1 structure_documents

```text
team_uuid, structure_document_uuid PK
generation_artifact_uuid UNIQUE
source_manifest_artifact_uuid
root_node_key, node_count, leaf_count, max_depth
source_element_count, indexable_element_count, boundary_element_count, ignorable_element_count
required_byte_count, covered_byte_count, ignored_byte_count
node_set_digest, anchor_set_digest, coverage_digest, document_digest
payload_extra
```

Counts非负，三类element count之和等于source element count，`leaf_count=indexable_element_count`且`required=covered`；root必须在same document。Document UUID等于artifact UUID或一一确定性映射，不形成独立跨generation业务身份。

#### 5.4.2 structure_source_elements

```text
team_uuid, structure_document_uuid, source_element_key PK
source_manifest_artifact_uuid
element_ordinal, fragment_ordinal, source_kind_hint, element_role
canonical_byte_start nullable, canonical_byte_end nullable
unicode_scalar_count, utf8_byte_count, content_digest nullable
source_element_evidence_ref/digest
ignore_reason_code nullable, element_coordinate_digest
payload_extra
```

`UNIQUE(document,element_ordinal,fragment_ordinal)`与`UNIQUE(document,element_coordinate_digest)`。`element_role=indexable|boundary|ignorable`：indexable必须有非空UTF-8 span/content digest并恰一leaf；boundary只允许page break等zero-content coordinate；ignorable必须有nonempty ignored span、registered reason/evidence且无leaf。Node/anchor只能FK同document的indexable element，因而logical manifest与normalized tree不存在悬空key。

#### 5.4.3 structure_nodes

```text
team_uuid, structure_document_uuid, node_key PK
node_kind, node_class
parent_node_key nullable, sibling_ordinal, depth, preorder_ordinal
reading_ordinal nullable, source_element_key nullable
normalized_title nullable
descendant_first_reading_ordinal nullable, descendant_last_reading_ordinal nullable
node_coordinate_digest, payload_extra
```

`UNIQUE(document,preorder_ordinal)`；leaf reading/source key必填且各自unique，container/root为空。Parent composite FK same document。Normalized title是唯一node extension字段。

#### 5.4.4 structure_source_anchors

```text
team_uuid, structure_document_uuid, anchor_key PK
source_element_key, anchor_ordinal
anchor_kind, coverage_role, anchor_precision
clean_artifact_uuid, clean_content_digest
text_byte_start/end nullable
element_key nullable, element_byte_start/end nullable
source_page_ordinal nullable, source_page_artifact_uuid nullable
bbox_x0/y0/x1/y1 nullable
source_evidence_ref/digest, loss_quality_ref/digest nullable
coordinate_digest, payload_extra
```

Kind-specific XOR严格执行；`UNIQUE(document,source_element_key,anchor_ordinal)`。Byte与bbox range、UTF-8 boundary、same source/page由validator+constraint共同保证。

#### 5.4.5 structure_node_anchor_bindings

```text
team_uuid, structure_document_uuid, node_key, anchor_key PK
binding_ordinal, binding_role
payload_extra
UNIQUE(document,node_key,binding_ordinal)
```

Binding role=`primary|supporting`；只有leaf可直接绑定，container coverage从descendants确定性聚合。

### 5.5 Construction：3 tables

#### 5.5.1 construction_documents

```text
team_uuid, construction_document_uuid PK
generation_artifact_uuid UNIQUE
structure_document_artifact_uuid
partition_recipe_key/version/digest
summary_profile_ref/digest
unit_count, passage_summary_count, section_summary_count, document_summary_count
unit_set_digest, summary_set_digest, construction_digest
payload_extra
```

Exact structure input一经绑定不可变；document summary count恰1。

#### 5.5.2 construction_units

```text
team_uuid, construction_document_uuid, unit_key PK
unit_ordinal, first_leaf_reading_ordinal, last_leaf_reading_ordinal
first_node_key, last_node_key, primary_section_node_key nullable
source_byte_start, source_byte_end
unicode_scalar_count, utf8_byte_count
context_path_ref/digest, canonical_metadata_ref/digest
pair_key, original_content_digest, partition_proof_digest
payload_extra
```

`UNIQUE(document,unit_ordinal/pair_key)`；ordinals从0连续，ranges相邻、不重叠，全部leaf恰覆盖一次。Metadata ref必须same IntakeRevision authority。

#### 5.5.3 construction_unit_nodes

```text
team_uuid, construction_document_uuid, unit_key, member_ordinal PK
structure_node_key
payload_extra
UNIQUE(document,structure_node_key)
```

只允许leaf，member ordinal与reading order一致；该unique证明每leaf恰一unit。

### 5.6 Retrieval projection：3 tables

#### 5.6.1 retrieval_block_projections

```text
team_uuid, retrieval_block_projection_uuid PK
generation_artifact_uuid UNIQUE
construction_document_artifact_uuid, structure_document_artifact_uuid
projection_recipe_key/version/digest
block_count, original_block_count, summary_block_count
block_set_digest, traceback_proof_digest, projection_digest
payload_extra
```

Projection是vector前的immutable logical truth，不含index/serving fields。

#### 5.6.2 retrieval_blocks

```text
team_uuid, retrieval_block_projection_uuid, block_key PK
block_ordinal, block_kind, channel
target_kind, target_key, pair_key nullable, unit_key nullable
tree_path_ref/digest, context_metadata_ref/digest, filter_metadata_ref/digest
content_text_ref, content_digest, unicode_scalar_count, utf8_byte_count
source_first_unit_ordinal, source_last_unit_ordinal
summary_invocation_uuid nullable, summary_citation_set_digest nullable
block_coordinate_digest, payload_extra
```

Allowed kind/channel matrix见§4.6.3；passage pair恰两行且anchor set相等。Original的content ref解析到verified exact source slice；summary必须有Invocation/citation。`UNIQUE(projection,block_ordinal)`、`UNIQUE(projection,block_coordinate_digest)`。

#### 5.6.3 retrieval_block_anchor_bindings

```text
team_uuid, retrieval_block_projection_uuid, block_key, binding_ordinal PK
structure_document_uuid, anchor_key
source_element_key, citation_role
payload_extra
UNIQUE(projection,block_key,anchor_key,citation_role)
```

Citation role=`coverage|claim_citation|supporting_region`。Summary claim citations必须subset coverage；original passage coverage必须set-equal其unit primary anchors。

### 5.7 Repair ledger：1 table

#### 5.7.1 generation_repair_changes

```text
team_uuid, repaired_artifact_uuid, change_ordinal PK
source_artifact_uuid, repair_invocation_uuid
json_pointer, extension_field_kind
before_value_digest nullable, after_value_digest
finding_code, allowed_pointer_set_digest, change_digest
payload_extra
UNIQUE(team_uuid,repaired_artifact_uuid,json_pointer)
```

Only extension paths可写。Before null只允许补required extension；after不得null。Row与artifact均immutable，完整changed set digest进入repaired artifact envelope。

### 5.8 Typed wire contracts

#### 5.8.1 LsragStructurizeCommandV1

```json
{
  "schema_version": "mkb.lsrag-structurize-command.v1",
  "process_command_ref": "exact ES-02 command/fence",
  "subject": {
    "intake_item_uuid": "UUID",
    "intake_revision_uuid": "UUID",
    "revision_fingerprint": "sha256",
    "clean_artifact_uuid": "UUID",
    "clean_content_digest": "sha256"
  },
  "evidence": {
    "anchor_manifest_ref": "logical-ref",
    "anchor_manifest_digest": "sha256",
    "loss_quality_ref": "logical-ref",
    "loss_quality_digest": "sha256"
  },
  "bindings": {
    "structure_schema": "exact key/version/digest",
    "window_prompt_profile": "exact refs",
    "merge_prompt_profile": "exact refs"
  },
  "budget_profile": "lsrag-build-default/1",
  "input_digest": "sha256",
  "payload_extra": {}
}
```

#### 5.8.2 StructureProofV1 / LsragBuildProofV1

`StructureProofV1`含 exact subject/schema/input、source manifest/structure/report Artifact refs+digests、node/leaf/anchor/coverage counts、all-stage verdict、Invocation set digest与proof digest。`LsragBuildProofV1`在此基础上含 GenerationCommit、五member refs/digests、unit/block/pair/summary counts、traceback/bundle/current transition set digest。二者均不含raw content、path、token、provider response、next step或success authority；ES-02按manifest验证后才接受Outcome。

### 5.9 Task-scoped artifact read contract

ES-01 HTTP adapter承载三个既有frozen read：

| Route | Exact behavior |
|---|---|
| `GET /v1/teams/{team}/tasks/{task}/generation-artifacts` | 按Task generation/intake item/type/disposition分页列history；稳定排序`created_at DESC, artifact_uuid DESC` |
| `GET /v1/teams/{team}/tasks/{task}/generation-artifacts/{artifact_uuid}` | 返回safe immutable metadata、lineage、validation summary、`is_current`；不返回bytes |
| `GET /v1/teams/{team}/tasks/{task}/generation-artifacts:current` | 必填`generation`与`intake_item_uuid`，可选type；返回该Task可达Execution的per-type current set |

Query默认limit50/max200，opaque keyset cursor绑定filter digest。Owner chain必须验证Team→Task→generation→root/child Execution→Item→Artifact；跨Team/不可达统一404。Response允许artifact UUID/type、content digest/size/media、schema ref、source Item/Revision/clean refs、validation summary、created time和safe causation refs；删除Execution/Process/fence、logical handle/path、model/prompt、Invocation/raw output、source body和internal finding detail。POST/PUT/PATCH/DELETE不存在；对同route family返回`405 generation-artifact-read-only`。这不是artifact browser/export，且没有download URL。

### 5.10 Application ports

```python
class LsragStructurizePort(Protocol):
    async def execute(self, command: LsragStructurizeCommandV1) -> ProcessOutcomeV1: ...

class LsragConstructPort(Protocol):
    async def execute(self, command: LsragConstructCommandV1) -> ProcessOutcomeV1: ...

class StructureSchemaContractPort(Protocol):
    async def resolve_exact(self, ref: StructureSchemaRefV1) -> StructureSchemaContractV1: ...
    async def verify_consumer(self, ref: StructureSchemaRefV1, consumer: ConsumerRefV1) -> None: ...

class GenerationArtifactCommandPort(Protocol):
    async def finalize_candidate(self, command: FinalizeArtifactCandidateV1) -> ArtifactReceiptV1: ...
    async def accept_generation(self, command: AcceptGenerationBundleV1) -> GenerationCommitReceiptV1: ...

class GenerationArtifactQueryPort(Protocol):
    async def list_for_task(self, query: TaskArtifactListQueryV1) -> CursorPage[SafeArtifactViewV1]: ...
    async def get_for_task(self, query: TaskArtifactGetQueryV1) -> SafeArtifactViewV1: ...
    async def current_for_task(self, query: TaskArtifactCurrentQueryV1) -> CurrentArtifactSetV1: ...

class GenerationProjectionReadPort(Protocol):
    async def get_commit(self, ref: GenerationCommitRefV1) -> GenerationCommitV1: ...
    async def stream_blocks(self, ref: ProjectionRefV1) -> AsyncIterator[RetrievalBlockV1]: ...

class InferenceExecutionPort(Protocol): ...       # ES-05
class VerifiedObjectReadWritePort(Protocol): ...  # ES-04
class ProcessOutcomeOwnerPort(Protocol): ...      # ES-02
class UnitOfWorkPort(Protocol): ...               # ES-04
```

无 `update_artifact/delete_artifact/promote_candidate/edit_structure/retry_generation` port。Pointer mutation只能作为`accept_generation`内部步骤。

### 5.11 Internal durable protocols

| Message/event | Producer→consumer | Required guard |
|---|---|---|
| `lsrag.artifact-finalized.v1` | ES-06→audit/projection | artifact UUID/type/digest/disposition + exact causation；不是success trigger |
| `lsrag.generation-committed.v1` | ES-06→ES-02/07 projection | commit/member/proof digests；同UoW已有ProcessOutcome/next wake，event不决定route |
| `lsrag.current-pointer-transitioned.v1` | ES-06→audit | before/after/revision/commit digest；append-only |
| `lsrag.integrity-repair-requested.v1` | ES-08 scanner→ES-06 | observed owner refs/digests、repair reason；只能补登记可证明事实或fail incident |

Messages使用ES-04 `mkb.internal-message.v1` envelope、at-least-once inbox/outbox与same-effect UoW。没有callback endpoint；event、queue ACK、object promotion都不能替代GenerationCommit/ProcessOutcome。

### 5.12 Named transaction profiles

| Transaction key | Atomic writes | Guard/result |
|---|---|---|
| `lsrag_artifact_finalize_v1` | artifact+inputs+invocation links+validation report/findings+object refs+event | current Process/fence或scanner proven causation；immutable same digest replay |
| `lsrag_structurize_finish_v1` | source/structure rows+artifacts/reports/refs + ES-02 Outcome/route/construct Process/outbox | structure full-valid、current fence、no partial next step |
| `lsrag_generation_accept_v1` | construction/projection rows+final artifacts/report+commit/members+5 pointers/transitions + ES-02 Outcome/route/vector Process/outbox/events | exact five full-valid coherent set、pointer CAS、current fence；whole rollback |
| `lsrag_candidate_failure_v1` | invalid artifacts/reports/repair changes/refs + failed Outcome/event | history durable before runtime failure acceptance |

Large object bytes先按ES-04 reservation/promote协议完成；UoW只登记verified handle/ref。每条SQL fault injection后都必须证明全回滚或same receipt replay。

---

## 6. State / Consistency / Failure

### 6.1 StateFamily boundary 与 factual automata

ES-06不新增StateFamily。GenerationArtifact disposition、ValidationReport verdict、GenerationCommit存在性和CurrentPointer revision都是typed immutable/current facts。

```text
logical output formed
  → exactly one immutable Artifact record with terminal disposition
      ├─ invalid → history only
      └─ full_valid → eligible, but not current by itself

no accepted bundle
  → five full-valid coherent artifacts + current Process fence
  → atomic GenerationCommit + five pointer CAS + Process succeeded
```

Artifact没有`draft/approved/published/deleted`状态；Commit没有pending/failed状态；Pointer不是lifecycle或serving。Invalid candidate不可promote，full-valid candidate也不能绕过bundle/Process guard自行current。

### 6.2 核心不变量

1. Every S06 artifact绑定exact Team/Task generation/Execution/Process/Revision/clean/schema；无裸digest/latest/path解析。
2. Every formed model output有GenerationInvocation；every formed logical candidate有GenerationArtifact；日志不能替代。
3. Structure leaves与source fragments一一对应、order不变、required bytes exact-once coverage。
4. Tree/anchor/unit/block coordinate由engine计算且generation-local；模型/ES-07不能自造。
5. Original block来自verified clean bytes；summary永不覆盖或充当original。
6. Every summary sentence有本target内citation；every summary block有complete original traceback。
7. Model不能写canonical metadata/filter/team/lifecycle；filters只引用exact IntakeRevision authority。
8. Kernel finding repair call=0；extension repair creates new invocation/artifact and full revalidation。
9. Current pointer只指向full-valid commit member；五pointer与Process success同transaction。
10. S06 current不等于Item serving或active index；ES-07 publication failure不回写S06 truth。
11. Process retry不混用不同retry的partial windows/summaries；history保留。
12. Cancel、cleanup、schema upgrade、soft delete不改写accepted artifact/commit/transition skeleton。

### 6.3 Concurrency 与 CAS

- Artifact idempotency键=`process_uuid + process_retry_count + artifact_type + artifact_ordinal + input_set_digest`；same envelope/digest返回原row，different digest为integrity conflict；
- Invocation ordinal由ES-05在Process范围单调分配；duplicate reservation同request digest返回原Invocation，不允许重复send；
- Pointer CAS predicate含team/execution/type/expected revision/before artifact/current Process fence；五次update在同transaction；
- Two runners同fence不可能合法：ES-02 claim token/fence先挡；若仍竞争，commit unique/CAS只允许同digest replay；
- Structurize success UoW与construct materialization原子；construct success UoW与vector Process materialization原子，消除lost wake-up；
- Reader在一个DB snapshot加载commit+members+pointer set+object refs；任一缺失返回integrity error，不拼装partial view。

### 6.4 Failure disposition

| Failure | Artifact/current/Process result |
|---|---|
| clean object missing/digest mismatch | 无新artifact/current；integrity incident；Process failed/non-retryable until repair |
| schema/profile/model/prompt missing或digest drift | 无provider call；binding failure；readiness/Process fail-loud |
| provider known timeout/error | Invocation outcome retained；无伪artifact；typed retryability交ES-02 |
| dispatch started、outcome unknown | Invocation=`indeterminate`；不自动重发；Process按non-replayable recovery失败 |
| strict response parse失败 | raw Invocation output retained；invalid candidate Artifact/report若logical bytes已形成；不coerce |
| tree/order/anchor/coverage/kernel失败 | invalid history；repair count0；ES-02 retry/fail |
| summary extension失败 | invalid history；至多一次repair；仍失败则ES-02 retry/fail |
| semantic/source/bundle proof失败 | invalid history；无current；不得删除bad member后缩小成功范围 |
| object promote成功、canonical UoW失败 | bytes orphan；无usableartifact；scanner按reservation/invocation恢复或GC |
| pointer/commit UoW任一写失败 | 全回滚；Process非success；旧pointer保持 |
| Process success提交后response/wake丢失 | duplicate handler/outbox replay返回same commit并重新投递，不再调用模型 |
| ES-07后续失败 | S06 commit/current保持；Task是否失败由ES-02 aggregate；旧serving不污染 |

### 6.5 Recovery 与 reconciliation

Scanner只做有证据的semantic recovery：

1. Invocation有terminal output且无Artifact：验证exact Process/input/object/schema后补执行同一`artifact_finalize`，否则P0 incident；
2. Artifact/report存在但normalized child rows缺失：若同UoW不可能发生则判database corruption，不从模型raw output猜写；
3. Commit存在但pointer/member/Process Outcome不闭合：正常schema下不可能；readiness false、隔离写入，按transaction log/immutable rows证明后走owner UoW；
4. Process succeeded且无commit/proof：不得合成success，向ES-02提交drift evidence并保持Task非success；
5. Current pointer target object missing/corrupt：不回退到前一artifact、不切latest；阻断ES-07 consumption并触发ES-04 integrity procedure；
6. Duplicate event/outbox只重投projection，不改变artifact/current。

Scanner不能重新调用模型、修 summary、重建tree、放宽schema、选“最近有效artifact”或创建无causation commit。

### 6.6 Retry、repair 与 cancel

- Provider SDK retry=0；handler private retry=0；ES-02 Process max retry是唯一automatic retry budget；
- Extension repair不是Process retry：它是profile声明的一次新Invocation+Artifact pass，且只针对当前candidate extension；
- 每个新的Process retry candidate最多一次repair，总call上限由`(max_retries+1) × planned calls/repair budget`静态计算并进command digest；
- Retry复用exact Revision/clean/schema/profile，不复用partial candidate，也不读取current；
- Deadline/cancel在call间生效；不能中断已发送provider call并假装未计费，其outcome/indeterminate必须入账；
- Cancel赢时不commit current；already accepted generation truth保留，不rollback；
- 用户full retry/rebuild只通过ES-01/02现有因果语义产生new Task generation/Execution，本文件无用户generation retry command。

### 6.7 Retention 与 cleanup

Current commit、五member objects、structure/construction/projection normalized rows、validation proof及ES-07 live lineage在引用有效期间不得释放。Invalid artifact大bytes只有terminal、非current/非serving、无history/hold/backup/outbox/invocation recovery引用后满7天，才可按ES-08-v1.0 release object reference；保留artifact UUID/type/digest/size/binding/disposition、Invocation/token、validation summary、repair causation和pointer transition skeleton。Process cleanup不删除上述truth。

Cleanup eligibility必须满足Execution terminal、非current/非serving lineage、无open hold/backup/outbox/invocation recovery、retention到期和ES-04 delete fence。普通public Delete永不存在。

### 6.8 Security 与 bounded disclosure

- Source/prompt/model output只进入bounded object store，不进log/event/error/finding safe detail；
- Prompt把source作为typed part，固定instruction在前；source内指令不改变schema/tool/egress；
- Model无tool/search/file access，不能读取secret/path、跨Team object或registry write port；
- 所有查询先验证token/Team/Task ownership再lookup artifact；跨Team与未知统一404；
- Summary/normalized title仍可能包含source敏感内容，public artifact metadata不返回内容；retrieval内容的授权/filter归ES-07；
- Absolute path、logical handle、claim token/fence、provider request ID、stack/SQL不出public surface。

---

## 7. Legacy Retain / Rewrite / Drop

| Legacy evidence | Retain | Rewrite | Drop |
|---|---|---|---|
| Structurizer ordered layered content | ordered structure与层次对retrieval有价值 | exact rooted tree、engine leaves、versioned schema、coverage proof | flat `layered_content`、numeric granularity当tree |
| Constructor original/summary rows | 两通道与共享traceback coordinate | passage pair + section/document summary + exact generation/source anchors | model-generated original、mutable JSON、裸block_id |
| `file_uuid+block_id+granularity` traceback | summary hit必须回到original | team/revision/generation/projection/unit/anchor typed coordinate | 跨代碰撞、路径/latest猜测 |
| Prompted JSON generation | structured output可用于container/summary extension | strict schema、no coercion、exact Prompt/Profile、Invocation ledger | brace extraction、comma cleanup、missing context fill、fallback branch |
| metadata/context fusion | context帮助summary与retrieval | canonical context/filter refs由Revision authority复制 | parent/child随意merge、注入team/is_active、模型生成filter |
| R2 upload + callback | immutable object与完成通知的需求 | ES-04 local CAS object + DB UoW/outbox + typed Outcome | R2/D1/Worker/Queue/callback success SSOT |
| per-block recorder | block级别lineage和两通道映射 | normalized projection/block/anchor tables、bundle proof | recorder直接混写vector/runtime status |

实现、测试、配置或migration不得import legacy package、schema、Prompt、wire type、R2 key或callback。Fixture可以人工重建相同业务场景，但不要求相同JSON/byte输出。

---

## 8. Acceptance Evidence

以下94项全部为`HARD`；实现任一失败即conformance/release blocked。

### 8.1 Schema、registry 与 process contract

| ID | Scenario | Required evidence |
|---|---|---|
| ES06-A001 | StructureSchema bundle install | 8 components+kernel/extension/validators canonical digest稳定 |
| ES06-A002 | same version same digest | idempotent same receipt |
| ES06-A003 | same version different digest | readiness false、零Execution binding |
| ES06-A004 | missing component/validator | compile/readiness fail-loud |
| ES06-A005 | consumer support mismatch | ES-02 compile在运行前拒绝 |
| ES06-A006 | exact Process catalog | 恰`lsrag.structurize/construct`，与ES-02/05 set-equal |
| ES06-A007 | manifest ports/proof | typed input/output/proof、non_replayable/error/resource exact |
| ES06-A008 | exact Prompt/Profile set | window/merge/summary/repair四套，无generic fallback |
| ES06-A009 | existing Execution after registry upgrade | 继续旧digest，不读latest |
| ES06-A010 | schema public CUD attempt | route/port不存在或405，零registry mutation |

### 8.2 Cutoff、source elements 与 grounding

| ID | Scenario | Required evidence |
|---|---|---|
| ES06-A011 | Process materialization cutoff | command锁定Revision/clean/evidence/all bindings/input digest |
| ES06-A012 | clean changes after cutoff | retry仍读原artifact；不切latest |
| ES06-A013 | same input normalization | manifest bytes/keys/root digest byte-identical |
| ES06-A014 | oversize element | sentence→line→scalar分片，无drop/duplicate |
| ES06-A015 | unknown element kind | fail-loud，不映射other |
| ES06-A016 | text anchor | UTF-8 half-open边界、slice digest精确 |
| ES06-A017 | element anchor | element/local span exact且same clean artifact |
| ES06-A018 | page region / nontext media | normalized bbox/page evidence/loss precision保留；无canonical text的required media阻断build |
| ES06-A019 | required content gap | source-proof invalid、无current |
| ES06-A020 | overlap/duplicate coverage | kernel invalid、repair call 0 |
| ES06-A021 | registered ignorable span | reason/digest存在且required=covered |
| ES06-A022 | empty indexable content | typed failure、无empty success/projection |

### 8.3 Structure tree 与 windowing

| ID | Scenario | Required evidence |
|---|---|---|
| ES06-A023 | valid mixed document | one root、all reachable、closed kinds、ordered leaves |
| ES06-A024 | cycle/multiple root/orphan | kernel invalid、无repair/current |
| ES06-A025 | model drops/duplicates leaf | set-equality guard失败 |
| ES06-A026 | model reorders leaf | reading/source order guard失败 |
| ES06-A027 | model submits IDs/original | strict response reject |
| ES06-A028 | generation-local identity | same artifact rebuild samekeys；newartifact无跨代identity承诺 |
| ES06-A029 | window boundaries | contiguous、non-overlap、budget内、plan digest稳定 |
| ES06-A030 | global merge | only contiguous root grouping，无leaf mutation |
| ES06-A031 | source/window/node limit | pre-dispatch typed budget failure，无provider truncation |
| ES06-A032 | failed middle window | no partial accepted structure；Invocation history完整 |
| ES06-A033 | retry after failed window | exact input重做，不混拼旧partial outputs |
| ES06-A034 | normalized title | extension only，不改变node/anchor/coordinate |

### 8.4 Construction、summary 与 projection

| ID | Scenario | Required evidence |
|---|---|---|
| ES06-A035 | unit partition | all leaves exact-once、contiguous、ordered、bounded |
| ES06-A036 | boundary preference | fixed recipe golden vectors稳定 |
| ES06-A037 | original passage | exact verified clean slice digest，不含model rewrite |
| ES06-A038 | passage pair | every unit恰original+summary且pair/anchors相同 |
| ES06-A039 | section summary | references only descendant units；complete traceback |
| ES06-A040 | document summary | exactly one、all citation keys in document |
| ES06-A041 | summary target missing/extra | extension invalid，不silent fill/drop |
| ES06-A042 | citation outside target | semantic/source proof invalid |
| ES06-A043 | summary budget overflow | extension invalid或provider hard reject，无truncate |
| ES06-A044 | metadata authority | context/filter refs equal exactRevision；model值无法写入 |
| ES06-A045 | block kind/channel matrix | passage dual；section/document summary only；无custom |
| ES06-A046 | stable block coordinate | deterministic within projection、unique、generation scoped |
| ES06-A047 | ES-07 attempts rechunk | consumer contract rejects coordinate/schema drift |
| ES06-A048 | no vector fields | projection schema无embedding/vector/backend/score/current index |

### 8.5 Validation、repair 与 history

| ID | Scenario | Required evidence |
|---|---|---|
| ES06-A049 | validation order | shape→binding→kernel→extension→semantic/source→bundle固定 |
| ES06-A050 | finding determinism | same candidate finding order/set/report digest相同 |
| ES06-A051 | kernel finding | repair Invocation count 0；invalid history retained |
| ES06-A052 | extension repair allowed | newInvocation+newArtifact+predecessor+changed rows |
| ES06-A053 | repair touches kernel | immediate policy violation、无current |
| ES06-A054 | repair adds unknown pointer | strict reject |
| ES06-A055 | repair full revalidation | 从shape重新运行全部stage |
| ES06-A056 | repair second failure | no second repair；ES-02 retry/fail |
| ES06-A057 | malformed JSON/coercion bait | 不截取brace、不补comma/default/context |
| ES06-A058 | every formed output | Invocation/Artifact/object/causation closure完整 |
| ES06-A059 | provider failure before output | Invocation outcome存在；不伪造Artifact |
| ES06-A060 | unknown dispatch outcome | indeterminate、no automatic resend |

### 8.6 Commit、pointer 与 concurrency

| ID | Scenario | Required evidence |
|---|---|---|
| ES06-A061 | valid final build | exactly five types、same binding、commit/current/Outcome atomic |
| ES06-A062 | missing/extra artifact type | bundle reject、all pointers unchanged |
| ES06-A063 | invalid member | commit reject、invalid只留history |
| ES06-A064 | cross-Execution/source/schema member | ownership/binding reject |
| ES06-A065 | fault at every accept SQL | whole rollback；无partial pointer/Process success |
| ES06-A066 | same commit replay | same receipt、zero new calls/rows except delivery evidence |
| ES06-A067 | different replay | integrity conflict、old current preserved |
| ES06-A068 | stale Process fence | zero artifact selection/Outcome/next wake mutation |
| ES06-A069 | two runner race | one same-digest winner或conflict，无double commit |
| ES06-A070 | pointer transition | before/after/revisions/commit/proof完整append |
| ES06-A071 | current object missing | no fallback toprevious/latest；retrieval blocked |
| ES06-A072 | S06 vs serving | ES-07 failure不撤销S06 commit，也不伪造serving |

### 8.7 API、recovery、security 与 scope

| ID | Scenario | Required evidence |
|---|---|---|
| ES06-A073 | Task artifact list | bounded stable cursor、filters、history+is_current正确 |
| ES06-A074 | artifact get | Task ownership链验证，safe metadata only |
| ES06-A075 | current query scatter | generation+Item消歧，返回per-type set且不泄漏Execution |
| ES06-A076 | cross-Team/unknown | uniform 404，无existence leak |
| ES06-A077 | public mutation/download | absent/405，零bytes/CUD exposure |
| ES06-A078 | commit response lost | replay返回原commit且不再调用模型 |
| ES06-A079 | orphan promoted bytes | scanner恢复可证ledger或grace GC，不伪造success |
| ES06-A080 | impossible partial normalized rows | readiness false/P0，不从raw output猜修 |
| ES06-A081 | cancel between calls | no newdispatch/current；completed call入Invocation账 |
| ES06-A082 | cancel after commit | immutable truth保留；ES-02 forward-stop收敛 |
| ES06-A083 | Process cleanup | artifact/commit/proof/lineage/read仍完整 |
| ES06-A084 | secret/path/body scan | response/event/log/finding/payload_extra零泄漏 |
| ES06-A085 | dependency scan | domain/application无SDK/Turso/path/vector/legacy import |
| ES06-A086 | fixed architecture | no newservice/StateFamily/intent/source/spec/plugin |

### 8.8 ES-07 consumer closure

| ID | Scenario | Required evidence |
|---|---|---|
| ES06-A087 | projection consumer registry | ES-07 exact schema/digest consume support，no range/latest |
| ES06-A088 | vector build closure | projection block set=VectorRecord set，一block一record |
| ES06-A089 | embedding input inspection | prefix/title可派生；block body/content digest无trim/truncate/rewrite |
| ES06-A090 | four strata mapping | four exact block kind/channel组合set-equal，无extra block |
| ES06-A091 | passage summary retrieval | pair/unit/anchor exact original traceback |
| ES06-A092 | hierarchy summary retrieval | citations→source elements→units→original anchors exact且bounded |
| ES06-A093 | filter authority | ES-07只消费target Revision canonical filters，不改S06 metadata refs |
| ES06-A094 | downstream failure isolation | embed/index/publication/query失败后commit/current/artifact history不变 |

### 8.9 必须交付的 evidence bundle

1. 21-table logical schema、constraint/index manifest与ES-04 physical mapping diff；
2. StructureSchema 8-component canonical bundle、meta-validation与ES-05/07 exact consumer handshake；
3. 两个Process manifest与四套Prompt/Profile registry exact-set报告；
4. source normalizer/fragment/key/anchor/coverage golden与property vectors；
5. tree/root/acyclic/order/kind/coordinate exhaustive negative matrix；
6. 64MiB/window/merge/limit/token/output bound benchmark与failure evidence；
7. construction partition、passage pair、section/document summary、traceback fixtures；
8. validation order、kernel-no-repair、extension-one-repair/full-revalidation report；
9. Invocation→Artifact→report→commit→pointer→Process Outcome causation closure；
10. named UoW statement-by-statement fault injection、duplicate/stale-fence/race matrix；
11. Task-scoped read auth/cursor/redaction/OpenAPI negative tests；
12. cancel/retry/recovery/orphan/missing-object/cleanup end-to-end records；
13. Owner Truth/baseline/ES-01..05/07 trace matrix；
14. zero legacy/provider/storage/vector dependency与scope-ceiling scan。

---

## 9. Remaining Technical Decisions and Defaults

### 9.1 已裁决 defaults

| Topic | V1 default | 改变门槛 |
|---|---|---|
| Process catalog | structurize + construct only | 不可在V1增加；新key需既有scope内cross-spec revision |
| Artifact types | exact five | 新type需证明不是raw provider/vector/index/编辑产物并校准pointer/consumer |
| Node kinds | 1 root + 5 container + 8 leaf | schema new version + full tree/consumer migration evidence |
| Anchor kinds | text_span/element_span/page_region | schema new version + source fidelity/consumer evidence |
| Block kinds/channels | passage original+summary；section/document summary | semantic benchmark与ES-07 compatibility；不得取消original traceback |
| Source max | 64MiB clean canonical bytes | ES-08 memory/token/failure benchmark；可收紧，不热改 |
| Fragment | 2,048 scalars / 8KiB | coverage/embedding/semantic regression evidence |
| Window | 64KiB or 256 leaves；2,048 max | model/context/token benchmark + newProfile |
| Merge | fan-in64、max3 levels | tree quality/budget evidence + newProfile |
| Unit | target1600、min400、max3200 scalars/16KiB | ES-07 embedding/semantic benchmark + newrecipe version |
| Summary | 16 targets/64KiB batch、768 scalars/target | quality/token evidence + newProfile |
| Repair | extension only、one per candidate | kernel永不可repair；budget变化需newProfile |
| Identity | generation-local hashed coordinates | 跨generation identity/editing是OOS，不可普通配置开启 |
| Current commit | exact-five atomic with Process Outcome | 不得拆为partial pointer；future change需cross-owner consistency proof |
| Artifact public read | metadata-only Task-scoped | bytes/download/edit/export仍OOS |

### 9.2 下游既有槽位输入

| Input / status | Owner | ES-06要求 |
|---|---|---|
| Embedding profile与supported block contract / closed | ES-07 | text-768 space exact支持projection与四strata；不重切/改anchor |
| Vector/index generation与publication / closed | ES-07 | consume exact commit；一block一vector；publication失败不改S06 current |
| Retrieval/traceback / closed | ES-07 | summary hit返回本文件pair/unit/anchor到original；不泄漏raw vector |
| Resource envelope/alerts/retention / `closed by ES-08-v1.0` | ES-08 | reference profile实测、closed alert/metrics、invalid bytes 7d与60秒cleanup scanner；只能收紧且不改变Truth |
| Semantic release corpus/metric / `closed by ES-07/08` | ES-07/08 | 16-document/32-query gate使用双通道与traceback并纳入signed release evidence |

ES-07 consumer design与ES-08资源/release evidence均已闭合；exact projection仍必须fail-closed消费。不得让ES-06预建generic vector schema或提高产品范围。

### 9.3 Rejected alternatives

| Alternative | Rejection |
|---|---|
| Flat chunks / `layered_content` JSON | 无真实tree、coverage与typed coordinate，无法证明source fidelity |
| Model writes original content | 派生文本会冒充source truth，破坏traceback |
| One giant model call | 无bounded plan，依赖provider截断且不可证明完整性 |
| Hidden per-window retry/resume | 复制ES-02 retry、混代partial outputs、成本不可审计 |
| Generic JSON repair/sanitizer | 将invalid output伪装为truth，可触碰kernel |
| Human structure editor/curation | 形成CMS/knowledge editing产品，Owner明确OOS |
| Cross-generation node IDs/diff | 引入revision/editor语义，没有V1需求 |
| Per-artifact independent current commit | 可产生跨type混代和false success |
| “latest valid artifact” recovery | 绕过exact pointer与causation，历史不可解释 |
| Summary-only vector projection | 失去original召回与source-grounded回退 |
| Original-only projection | 不满足已冻结original/summary与layered LS-RAG价值 |
| Section full-original duplicate blocks | 大对象重复且不可bounded；section summary已有complete traceback |
| Metadata fuser/model filters | 越权改变Revision authority和Team eligibility |
| S06 direct vector/index write | 混合ES-07 publication owner并使S06成功冒充serving |
| Public artifact download/CUD | 变成内容管理/export产品，超出T-O-79受限read |

### 9.4 Closure

ES-06没有需要Owner回答的问题。Exact artifact/node/anchor/block kind、window/unit budget、bundle事务与repair budget均已被OT02/03明确下沉为executional design；本文件已在固定LS-RAG能力内给出有限默认、failure boundary与改变证据。ES-04/05 physical/registry、ES-07 exact consumer、ES-08运行化与最终cross-spec audit均已闭合，不构成新capability、StateFamily或scope。

---

## 10. Revision History

| Version | Date | Status | Change |
|---|---|---|---|
| `ES-06-v0.1` | `2026-08-10` | `internally-consistent / awaiting cross-spec audit` | 冻结两个exact Process、完整StructureSchema bundle、deterministic SourceElement/tree/anchor/coverage、ConstructionUnit与passage original/summary+section/document summary、五类GenerationArtifact/current/coherent commit、extension-only repair、21张logical tables、Task-scoped metadata read、ports/protocols、failure/recovery与86项HARD acceptance。未导入S06未冻结Q4–Q6为Owner Truth，未新增产品能力、StateFamily、服务、source、intent、provider、vector/index、内容编辑或spec文件。 |
| ES-06-v0.2 | 2026-08-10 | internally-consistent / awaiting cross-spec audit | 与ES-07-v0.1校准exact consumer：冻结一block一vector、四strata映射、embedding不改正文、summary/hierarchy mandatory original traceback、filter authority及downstream failure isolation，新增8项acceptance至94。21张表和LS-RAG语义不变，未吸收vector/index ownership或扩大产品范围。 |
| ES-06-v1.0 | 2026-08-10 | ready | 完成OT-01..04、D01/D02、S06及ES-01..05/07/08最终对账；2个LS-RAG Process、8-component schema、5类GenerationArtifact、21张owner tables与94项HARD acceptance均已set-exact。未新增内容编辑、vector ownership、状态族、服务或spec文件。 |
