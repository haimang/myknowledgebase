# 调查面 `07` · 五维语义双账本、S06 projection 与 retrieval facets — 深度评估

> **对象 / scope-fence**：非 API ingest 的五维权威来源；ContextMeta tags；Revision semantics；与 g0 分账；S06 system-owned context overlay；vector/retrieval facet；metadata update 是否重写五维。
> **本面不含**：重开 cuts/g0 算法；publication serving pointer（面 `08` 消费本面投影）；把 channel 当作 original/summary 的向量面（必须 **分名**，不得吞掉 `FilterMeta.channel`）。
> **日期**：`2026-08-29`
> **作者**：`Grok analysis-fleet / review-fleet`（fleet / panel：`new-harvest-reference-anchor`）
> **文档性质**：`assessment / analysis`（单面 measure-first 深评；零决策——只 MARK 不裁决）
> **文档状态**：`draft`
> **流水线位置**：站② · 上游 = [[assessment-index]]（消费其冻结分母）
> **对照参考**：`T-O-386` / `T-O-389`（QNA v0.5 CITE）；`D08-T007` / `D08-A07`；`docs/baseline/spec-glossary.md` FilterMeta/ContextMeta；HEAD `1221aa1`
> **上游权威输入**：
> - `docs/eval/new-harvest/assessment-index.md` — §2.2 `D-16..D-19` / §3.07 / `G-NH-05` / `G-NH-06`
> - `docs/eval/new-harvest/pre-initial-planning-qna.md` — `T-O-386` / `T-O-389`（只 CITE，不扩冻）
> **下游消费者**：`docs/eval/new-harvest/planning-proposed.md` · `pre-charter-qna.md`（owner-gate 裁决）· 面 `08` publication / 面 `09` assurance

---

## 0. Verdict（结论先行）`[核心]`

- **0.1 一句话缺口 / 现状判断**：HEAD 已为 **registered_api** 交付严格 FilterMeta 五维 + 六元组 + S04 `mkb_intake_revision_semantics` 写入，并用 system-owned g0 钉 `g0.body=admitted clean`；但 **非 API 三通道仍以 `{"source_kind":...}` stub 冒充五维且仍可 acceptance-complete**，S06 不读 Revision 语义、公开检索 **FilterMeta facet key=0** 且 `channel` 已被向量层占用为 `original|summary`。`T-O-389` 是目标法，不是 HEAD 已实现事实。
- **0.2 Top blockers（最关键断点）**：
  1. `NH-RA07-B01` / `NH-RA07-B02`：非 API 无五维权威面；stub 不阻断 acceptance-complete（违反 `T-O-389`）。
  2. `NH-RA07-B03`：S06 `context_meta` 不从 S04 revision semantics 投影，缺则塞 `{}`，模型可幻觉 realm。
  3. `NH-RA07-B04` / `NH-RA07-B05`：公开检索无 FilterMeta facet；`channel` 名冲突；向量 sidecar 只写 `source_kind`。
- **0.3 总体方向建议**：沿用已交付的 API 六元组、S04 语义表、system g0 overlay、未知 retrieval key fail-closed 与 metadata-update「新 Revision + 继承 clean」骨架；把非 API 五维权威、acceptance 阻断、S06 system-owned context overlay、FilterMeta facet 投影与 **channel 分名**做成净新/重 substrate。**值从 caller / 闭集派生 / merge、以及 `unknown` 是否合法，只 MARK `G-NH-05`；业务 channel 与向量 original/summary 如何分名只 MARK `G-NH-06`。不替 owner 裁决。**
- **0.4 如何读本台账**：见上方头部「图例」；本面主题轴 = `双账本权威` / `S06 overlay` / `retrieval facet 与命名` / `metadata 更新语义`。

---

## 1. 方法与证据基线 `[核心]`

> 读了哪些代码/文档/参考；什么算可采信；怎么复现。**先证可证性，再下判断。**

- **1.1 本仓证据（如何测量）**：
  - HEAD 代码：`src/contracts/intake/semantics.py`、`src/services/registry.py`、`src/runtime/intake/acceptance_snapshot.py`、`src/runtime/intake/generation_assemble.py`、`src/runtime/intake/generation_construct.py`、`src/services/retrieval/{models,retrieval_request,retrieval_rank}.py`、`src/contracts/lsrag/layered_content.py`、`src/contracts/api/models.py`、`src/runtime/intake/acceptance_lifecycle.py`、`src/services/intake_lifecycle/targets.py`、`src/runtime/intake/vector_publish_commit.py`、`src/runtime/intake/vectorize.py`、`src/persistence/migrations/001_initial.sql`、`intake/api/providers/{chinatax,domain,realestate}.py`。
  - 测试：`tests/e2e/test_registered_api_scatter.py`、`tests/intake/test_api_chinatax.py`、`tests/unit/test_retrieval_service.py`、`tests/e2e/test_intake_rebuild_metadata.py`、`tests/unit/test_metadata_semantics.py`、`tests/unit/test_r5_assemble.py`。
  - 仓内基线：glossary FilterMeta ≠ clean_text；`D08-T007` / `D08-A07`；`T-O-62` 三账本。
  - 测量法：grep 关键词 → 再 `read_file` 钉 `path:line`（不以 PROMPT 行号为准）；`uv run python` 复跑共享分母脚本。
- **1.2 外部 / 参考来源 + 置信**：
  - **HEAD 实测**（最高）：本面全部 S1/S2 以 HEAD `path:line` 支撑。
  - **legacy-family clean**（ReferenceAnchor，`T-O-42`）：dedicated `*FilterMeta` / `*ContextMeta`、`meta_fuser.ts`、universal 不写 FilterMeta、vectorizer `vec_channel`。只借语义/失败法，不回流 runtime。
  - **公开网络 primary**（只证机制/限制，不得证 MKB 现状）；访问日 **2026-08-29**：
    | 搜索词 | 打开的 primary URL | 版本/发布 | 支持的原子结论 | 限制/失败 |
    |--------|---------------------|-----------|----------------|-----------|
    | `Qdrant payload index official documentation` | https://qdrant.tech/documentation/manage-data/payload/ ；https://qdrant.tech/documentation/manage-data/indexing/ | 官方 docs，页脚 © 2026 | payload 与向量并列；payload index 按字段建；未索引字段可被 strict mode 拒绝 | **不是本仓向量后端**；JSON payload 自由键与本仓闭集冲突 |
    | `pgvector metadata filtering JSONB official` | https://github.com/pgvector/pgvector README §Filtering（raw master，v0.8.6 安装说明同页） | README master / 标注 v0.8.6 | 过滤走 SQL `WHERE` + 列索引；ANN 默认 **后过滤** | 后过滤 recall 塌缩：HNSW `ef_search=40` 且命中 10% 时平均只剩 4 行 |
    | `OpenSearch faceted search nested aggregations official` | https://docs.opensearch.org/latest/tutorials/faceted-search/ ；https://docs.opensearch.org/latest/aggregations/bucket/nested/ | OpenSearch 官方 latest，nested 页 2026-08-24 | facet 必须 keyword 映射；`post_filter` 保 facet 选项；nested 防数组交叉污染 | 本仓无 ES/OS 栈；nested 对象不是 S04 权威 |
    | `Elasticsearch reserved field names metadata official` | https://www.elastic.co/guide/en/elasticsearch/reference/8.18/mapping-fields.html | ES 8.18 Guide | `_id/_index/_source/_routing` 等为系统元数据字段 | 根级占用业务名会 mapper_parsing_exception |
    | `faceted search filter schema reserved field name` | https://developers.cloudflare.com/ai-search/configuration/indexing/metadata/ | Last updated Aug 26, 2026 | 官方明示 reserved names：`timestamp, folder, filename` | **CF/R2/Vectorize 栈禁借**；只借「系统字段必须分名」失败法 |
    | `Supabase semantic search metadata filter official` | https://supabase.com/docs/guides/ai/semantic-search | 官方 docs，访问日 2026-08-29 | 过滤必须推进 SQL 函数；RPC 后再 `.eq()` 是后过滤 | JSONB `@>` 是弱类型，对本仓闭集过宽 |
    | `W3C PROV-DM provenance official` | https://www.w3.org/TR/prov-dm/ | W3C Recommendation 30 April 2013 | provenance 是关于实体的 **记录**，与数据本身分账 | 规范单源；不规定向量 facet 实现 |
  - 置信分层：`HEAD 实测 > 仓内文档锚 > 外部参考`。外部不得证明 MKB 当前状态。
- **1.3 ★ 可复现命令清单（measure-first）**：
```bash
git rev-parse HEAD
# 期望：1221aa1…

uv run python - <<'PY'
from src.services.registry import DEFAULT_SEMANTICS
from src.contracts.intake.semantics import FilterMeta, ContextMeta, SemanticTuple
from src.services.retrieval.models import _FILTER_KEYS
from src.contracts.api.models import InlineSourceDescriptor, LocalObjectSourceDescriptor, HttpSourceDescriptor
print("D-16", len(DEFAULT_SEMANTICS), [k for k,_ in DEFAULT_SEMANTICS])
print("D-17", list(FilterMeta.model_fields), list(SemanticTuple.model_fields["semantic_key"].annotation.__args__))
print("D-19", sorted(_FILTER_KEYS))
print("non_api_filter_fields",
      [k for k in InlineSourceDescriptor.model_fields if k in FilterMeta.model_fields],
      [k for k in LocalObjectSourceDescriptor.model_fields if k in FilterMeta.model_fields],
      [k for k in HttpSourceDescriptor.model_fields if k in FilterMeta.model_fields])
PY

nl -ba src/runtime/intake/acceptance_snapshot.py | sed -n '576,641p'
nl -ba src/runtime/intake/generation_assemble.py | sed -n '17,62p'
nl -ba src/runtime/intake/generation_construct.py | sed -n '329,343p;1092,1218p'
nl -ba src/services/retrieval/models.py | sed -n '14,34p'
nl -ba src/services/retrieval/retrieval_request.py | sed -n '324,361p'
nl -ba src/services/retrieval/retrieval_rank.py | sed -n '80,90p'
nl -ba src/runtime/intake/vector_publish_commit.py | sed -n '496,525p'
nl -ba src/persistence/migrations/001_initial.sql | sed -n '1503,1522p'

rg -n "filter_meta|FilterMeta|payload_filter_meta" \
  context/legacy-family/smind-skill-clean-universal \
  context/legacy-family/smind-skill-clean-dedicated-apis \
  context/legacy-family/smind-clean-dispatcher \
  context/legacy-family/smind-skill-rag-constructor/services/meta_fuser.ts

# 本面未整包重跑 pytest（index D-23/D-24 已冻）。相关已列测试：
# tests/e2e/test_registered_api_scatter.py::test_registered_api_three_raw_provider_operations_map_seal_and_persist_semantics
# tests/unit/test_retrieval_service.py::test_unknown_filter_and_invalid_rank_policy_fail_loudly
# tests/e2e/test_intake_rebuild_metadata.py
```
- **1.4 范围围栏**：本面**只**覆盖五维权威、S04 revision semantics、S06 context overlay、retrieval FilterMeta facet 与 channel 分名、metadata 更新的语义权威。cuts/g0 切法、publication serving pointer、是否重跑清洁分别交面 `08`；replay/mega 证明交面 `09`。不重开第五 source kind、不选向量引擎、不冻结 HTTP 路径。

---

## 2. 当前结构分析（HEAD 实测 · measure-first）★ `[核心]`

> 按主题轴逐条测，每条钉 `path:line`。先冻结本面分母，再逐轴展开。

### 2.1 ★ 冻结分母（FROZEN denominators · HEAD）
> 引用 [[assessment-index]] §2.2 中属于本面的分母，并补本面专属分母。下游不得另估。

| 分母 | HEAD 实测值 | 证据锚（`path:line`） | 来源 |
|------|-------------|------------------------|------|
| `D-16` canonical SemanticDefinition | `10` | `src/services/registry.py:229-239`；本次 `uv run python` 打印 `len(DEFAULT_SEMANTICS)=10` | `index §2.2` |
| `D-17` FilterMeta+tags semantic key | `6`（五维 + `context_tags`） | `src/contracts/intake/semantics.py:12-63`；`registry.py:234-239` | `index §2.2` |
| `D-18` 非 API 通道实际五维写入 | `0`；fallback 为 `source_kind` blob | `src/runtime/intake/acceptance_snapshot.py:589-615` | `index §2.2` |
| `D-19` public retrieval filter key / FilterMeta facet key | `3 / 0` | `src/services/retrieval/models.py:14`；`retrieval_request.py:324-361` | `index §2.2` |
| `D-07-F01` 非 API 公开 descriptor 上的 FilterMeta 字段 | `0`（`extra=forbid`；`payload_extra` 不得控状态） | `src/contracts/api/models.py:107-144`；`src/contracts/common/models.py:20-26` | 本面新测 |
| `D-07-F02` vectorize 实际写入的 facet_key | `1` = `source_kind` | `src/runtime/intake/vector_publish_commit.py:496-518`；`vectorize.py:319-324` | 本面新测 |
| `D-07-F03` structurize 模型输入 JSON 键 | `schema_version` + `clean` + `markdown`；**无** revision semantics | `src/runtime/intake/generation_construct.py:330-343` | 本面新测 |
| `D-07-F04` metadata_refresh 投影到 S07 的 header 键 | `s04.metadata_fingerprint` + `s04.context_metadata_digest` + `s04.filter_metadata_digest`（**不是五维字面**） | `src/runtime/intake/acceptance_lifecycle.py:384-409` | 本面新测 |
| `D-04` registered API operation（消费） | `3` | index `D-04`；`intake/api/providers/*.py` 均调 `semantic_tuples` | `index §2.2` |

`D-16` 十键字面（不得另估）：`source_representation, canonical_content, context_metadata, filter_metadata, realm, type, channel, source_name, is_active, context_tags`。

### 2.2 轴 `双账本 / S04 revision semantics`（HEAD 核验）

- **正例 · 合同已登记**：`FilterMeta` 五维 `realm,type,channel,source_name,is_active`；`ContextMeta` 复用五维 + `title` + `tags[]`；`semantic_tuples()` 固定写出 **恰好 6** 条（`semantics.py:12-63`）。`DEFAULT_SEMANTICS` 把五维登记为 **全部 intake** 的定义，而不仅是 API（`registry.py:229-239`，bootstrap 以 `fingerprint_participation=1` 写入，`registry.py:680-700`）。
- **正例 · API 真写入**：三 provider mapper 构造 `FilterMeta`/`ContextMeta` 并调用 `semantic_tuples`（`intake/api/providers/chinatax.py:49-94`、`domain.py:73-121`、`realestate.py:102-161`）。e2e 断言 revision 语义集合 ⊇ 六键（`tests/e2e/test_registered_api_scatter.py:287-296`）。unit 钉 chinatax 五维字面（`tests/intake/test_api_chinatax.py:47-62`）。
- **正例 · S04 表是权威账**：`mkb_intake_revision_semantics` 以 `(team, revision, semantic_key)` 主键存 typed 值 + `value_digest`，FK 到定义表（`001_initial.sql:1045-1078`）。指纹只吃 `fingerprint_participation=true` 的条目（`acceptance_snapshot.py:662-679`）。
- **反例 · 非 API 不展开五维**：`_initial_semantics_tx` **永远**写四条 bootstrap（`source_representation`/`canonical_content`/`context_metadata`/`filter_metadata`）；仅当 `isinstance(filter_meta, Mapping)` 才展开五维+tags，否则 `filter_metadata` = `{"source_kind": source_kind}`（`acceptance_snapshot.py:591-615`）。非 API 路径不把 `filter_meta` 放进 state（runtime grep 仅 snapshot/scatter/preflight-API）。这就是 `D-18=0`。
- **产品法 vs 代码**：`T-O-389` 要求四通道强制五维、禁止 stub 冒充、缺五维不得 pretend acceptance-complete。HEAD 仍把 stub 当合法 acceptance 输入。这是 **方向正确、代码缺失**，不是「QNA 已实现」。

### 2.3 轴 `非 API 五维权威来源`（HEAD 核验）

- 公开 ingest 三描述符 `InlineSourceDescriptor` / `LocalObjectSourceDescriptor` / `HttpSourceDescriptor` **没有** FilterMeta 字段（`api/models.py:107-130`）。`RegisteredApiSourceDescriptor` 也不直接收 FilterMeta——五维由 operation mapper **闭集派生**（`api/models.py:132-173` + provider files）。
- `StrictModel extra=forbid`（`common/models.py:20-21`）。`payload_extra` 明文「never controls state transitions」（`common/models.py:1-5,24-26`）。因此今日 **caller 无法经 typed 公共面提交非 API 五维**；塞进 `payload_extra` 也不会成为 S04 权威。
- `G-NH-05` 要回答的「caller required / kind-closed derivation / merge」在 HEAD **均未落地为非 API 合同**。API 侧已是 **operation 闭集派生**（chinatax `realm='tax_china'` 固定；REA `channel=parsed.channel or "unknown"`，`realestate.py:102-107`）。
- **`unknown` 现状（不裁决）**：HEAD API 已在缺值时写入字面 `"unknown"` / `"Unknown Agency"` / `"Unknown"`（`realestate.py:105-106`；legacy dedicated 同样，`chinatax/processor.ts:76-77`、`domain/processor.ts:87-90`、`realestate/processor.ts:80-81`）。这是 **已存在的实现习惯**，不是 owner 已冻的法。`T-O-389` 明文不锁派生算法。

### 2.4 轴 `S06 projection 与 g0 分账`（HEAD 核验）

- **正例 · system-owned g0**：`overlay_system_g0` 丢弃一切模型 g0，插入唯一 system g0，`original_content.body = normalize(clean)`（`generation_assemble.py:17-47`）。structurize 在非 cuts 路径调用它（`generation_construct.py:1214-1218`）。这对齐 `T-O-386`/`T-O-389` 的 g0 同一性，**切法未重开**。
- **反例 · context_meta 不是 system-owned**：缺 `context_meta` 或非 Mapping 时塞 **空对象 `{}`**（`generation_assemble.py:59-60`）。**不**读取 `mkb_intake_revision_semantics`。若模型已返回 `context_meta`，overlay **原样保留**（不覆盖为 S04 权威）。
- **反例 · structurize 输入看不见五维**：`_structurize_input_text` → `_bjson_user_material` 只序列化 `clean` + 可选 `markdown`（`generation_construct.py:330-343,1112`）。`generation_construct.py` 对 `filter_meta`/`revision_semantics` 的 grep 仅命中 `_title_from_layered` 读 layered JSON 的 title（`:58`）。
- Layered 合同 **要求** `context_meta` 对象存在，但 realm/type/channel/source_name **可缺、可 null**（`layered_content.py:16-28,117-127`）。CLI stub 直接产出 `"context_meta": {}`（`claude_cli.py:558-563`）。
- cuts 装配若 pack 带 `context_meta` 则拷贝，否则仍走 overlay 的 `{}` 兜底（`generation_assemble.py:171-174`）。
- **结论**：g0 正文分账已做；S06 **过滤/上下文账**仍可能是空对象或模型幻觉。这正是 `T-O-389`「S06 layered context_meta 读 revision 语义，不从 g0 解析」尚未落地的点。

### 2.5 轴 `retrieval facets 与 channel 名冲突`（HEAD 核验）

- 公开 `RetrievalFilter` 仅三键：`intake_item_uuid` / `source_kind` / `channel`，且 `channel` 的字面闭集是 `original|summary`（`api/models.py:408-411`；`retrieval_request.py:354-355`）。未知键 fail-closed（`retrieval_request.py:333-340`；`tests/unit/test_retrieval_service.py:456-460`）。
- rank SQL：`source_kind` 走 `LEFT JOIN mkb_intake_sources`；`channel` 过滤 `r.channel`（向量 dual-channel 列）；**不** JOIN `mkb_intake_revision_semantics`，**不** JOIN `mkb_vector_record_facets`（`retrieval_rank.py:80-122`）。
- S08 已有 sidecar 表 `mkb_vector_record_facets`，注释写明「normalized Layer-B facets, not payload_extra」「key/version/digest must have been resolved by S04」（`001_initial.sql:1503-1522`）。但 vectorize **只 upsert `facet_key='source_kind'`**（`vector_publish_commit.py:496-518`）。FilterMeta 五维 **未投影**。`D-19` 的「FilterMeta facet key=0」与 `D-07-F02=1`（仅 source_kind）同时成立：source_kind 不是 FilterMeta 五维。
- 向量记录列 `channel TEXT ... CHECK (channel IN ('original','summary'))`（`001_initial.sql:1444`）。与 `FilterMeta.channel`（业务维，如 `政策法规` / `residential` / `sold`）**同名不同义**。
- 本仓向量后端是 **local Turso/SQLite BLOB + SQL**（`001_initial.sql:1463-1464`「Stock SQLite compatible representation of Turso native F32_BLOB」），**不是** Elastic/Qdrant。外部 payload-index 文献只作机制类比。

### 2.6 轴 `metadata update 是否改五维 / 新 Revision / 重 clean`（HEAD 核验）

- 公共 payload：`IntakeUpdateMetadataPayload.semantics: dict[str, Any]`，最少 1 键（`api/models.py:220-224`）。resolver 按 **已登记 semantic_key** 冻结，不把键限制在非五维（`targets.py:47-64,203-248`）。因此 **允许改 `realm/type/channel/source_name/is_active/context_tags` 以及 blob 键 `filter_metadata`/`context_metadata`**——只要定义表里有。
- 指纹变化 → 新 Revision，`creation_action_key='update_metadata'`，并 **继承** 前序 `clean_text` artifact 的同一 stored object（`acceptance_lifecycle.py:213-278`）。指纹不变 → `no_change` 转移，不追加 Revision（`acquisition_intents.py:137-199`；e2e `test_intake_rebuild_metadata.py:180-211`）。
- **admission 继承 clean artifact（不是「图已 skip clean」）**：metadata 路径 freeze 既有 S06/S07 family 并 `metadata_refresh_mode=reuse summaries`（`acquisition_intents.py:201-220`）。S04 新 Revision **继承**前序 `clean_text` stored object（`acceptance_lifecycle.py:253-278`）。S07 投影只放 digest header，注释写明「Context/filter values remain authoritative only in S04」（`acceptance_lifecycle.py:388-409`）。
- **分账给面 08**：本面拥有「语义是否可变、是否新 Revision」；面 08 拥有「是否重跑清洁 / serving pointer」（index §1.2）。HEAD 实测：**改五维可以、新 Revision 可以、S04 继承 clean artifact**；**clean Process 仍执行**——有变更 metadata 走 `_acquire_rebuild`（`acquisition_intents.py:207-214`），图无 intent 短路则 `acquire.to_decode`（`lsrag_definition.py:299-306`），`_clean` 无 rebuild 短路并 `dispatch_clean`（`clean_preflight.py:28-127`）。**禁止**把「不 reclean」写成 HEAD 已实现；目标不变量见 `NH-C-66`，测量权威在面 `08` `NH-RA08-B04`。是否 skip vs byte-equal no-op **只 MARK**（面 08 `G-NH-19`），本面不裁。
- **一致性缺口**：merge 是 key-wise `base.update(replacement)`（`acceptance_lifecycle.py:378-380`）。调用方可只改 `realm` 而不改 `filter_metadata` JSON blob，造成 **单键账与 blob 账分叉**。API 初写时两者同源于一个 `FilterMeta` 对象；metadata 路径没有重算六元组。

### 2.7 轴 `声称 vs 实测`

| 叙事/声称 | HEAD 实测 | 失真 |
|-----------|-----------|------|
| 「10 semantic definitions 已登记 ⇒ 语义可检索」 | 登记是正例；非 API 不写五维；公开 facet 0 | 高估（index §2.4 已校正，本面钉死） |
| `T-O-389` 已把四通道五维做完 | QNA 是目标法；代码仍 stub | 冻结 ≠ 已实现 |
| `T-P-NH-7`「值来自 caller ∪ 派生」 | initial-planning **叙事**；HEAD 非 API 两者皆无 | 不得当 HEAD 事实 |
| metadata update 会重 clean / 已不 reclean | S04 **继承** clean stored object + S07 reuse summaries；**图仍执行** decode + `clean.extract.deterministic`（权威测量在面 `08` `NH-RA08-B04`） | 两边都过声称。本面只钉 artifact 继承；禁止写成 HEAD 已 exact-clean |
| 有 `mkb_vector_record_facets` 即有 FilterMeta facet | 只写 `source_kind` | 高估 |

---

## 3. 借鉴锚定矩阵（Reference Anchor Matrix）★ `[核心]`

> 每个可借鉴点钉到 `path:line` / URL，给**借鉴 verdict**。这是「能借什么」的台账，不是设计决策。

| 借鉴点 | 来源锚（`path:line` / URL） | 借鉴 verdict | 借什么 / 不借什么 |
|--------|------------------------------|--------------|--------------------|
| API 严格 FilterMeta + 六元组 | `semantics.py:12-63`；`chinatax.py:49-94` | `✅借` | 借字段名、min_length、六元组合同、与 clean_text 分账。不借「仅三 provider 才有五维」（已被 `T-O-389` 扩展）。 |
| S04 十定义 + revision 语义表 | `registry.py:229-239,680-700`；`001_initial.sql:1045-1078` | `✅借` | 借 typed 账本与指纹参与。不把登记当成四通道已写入。 |
| API e2e 持久化六键 | `tests/e2e/test_registered_api_scatter.py:287-296` | `✅借` | 借验收形状：revision_semantics 必须含六键。不把 Task succeeded 当可检索。 |
| system-owned g0 | `generation_assemble.py:17-47` | `✅借` | 借「丢模型 g0、body=clean」。不重开 cuts。不把空 `context_meta` 当成 overlay 完成。 |
| 未知 retrieval key fail-closed | `retrieval_request.py:333-340`；`test_retrieval_service.py:456-460` | `✅借` | 借 fail-closed。扩展 facet 时必须先登记键，禁止自由 JSON。 |
| metadata 新 Revision + 继承 clean artifact | `acceptance_lifecycle.py:213-278`；`acquisition_intents.py:137-220` | `✅借` | 借 CAS/指纹/**S04 继承 stored_object**。不借「HEAD 已 skip clean Process」。不借「可只改单键而留下陈旧 blob」。图是否再跑 clean 属面 `08`。 |
| 非 API stub `source_kind` blob | `acceptance_snapshot.py:591-615` | `⛔反例` | 避开：缺 Mapping 仍 acceptance。`T-O-389` 点名此 stub 不得冒充五维。 |
| 非 API descriptor 无五维面 | `api/models.py:107-130`；`common/models.py:20-26` | `⛔反例` | 避开：无 typed 入口却声称四通道语义完整。`payload_extra` 不得变权威。 |
| S06 输入无 revision 语义 + `{}` 兜底 | `generation_construct.py:330-343`；`generation_assemble.py:59-60`；`claude_cli.py:558-563` | `⛔反例` | 避开：空 context 或模型幻觉当 overlay。 |
| 公开 `channel=original\|summary` 占用业务名 | `src/services/retrieval/models.py:14`；`retrieval_request.py:354-355`；`001_initial.sql:1444` | `⛔反例` | 避开：同名吞掉 `FilterMeta.channel`。分名是 `G-NH-06`。 |
| facet 表只写 source_kind | `vector_publish_commit.py:496-518` | `🔶部分借` | 借 sidecar 表形态与「必须带 definition digest」。不把 source_kind 算 FilterMeta facet。 |
| dedicated `*FilterMeta` 五维 | `chinatax/schemas.ts:52-61`；`domain/processor.ts:86-95`；`realestate/processor.ts:68-83` | `🔶部分借` | **借字段名与 D08-T007 分账**（meta 不进正文）。不借 R2 child JSON、`payload_filter_meta` 列、隧道、silent skip。 |
| constructor `meta_fuser` JSON 列当权威 | `meta_fuser.ts:15-19,172-207` | `⛔反例` | 不借：`smind_files.payload_filter_meta` / relations JSON 当 SSOT；不借缺 `is_active` 默认 1。 |
| universal cleaner 不写 FilterMeta | `smind-skill-clean-universal` 仅 `schemas_common.ts:190-191` optional record；services/flows **零** `payload_filter_meta` 赋值 | `⛔反例` | 证明遗产非 API 也常缺五维。**不能当「可跳过」先例。** |
| vectorizer `vec_channel` vs FilterMeta.channel | `vectorizer/engine.ts:124-126`；`recorder.ts:159` `content_channel` | `🔶部分借` | 借「业务 channel 与 original/summary **分名**」。不借 CF Vectorize metadata blob、`team_uuid` 塞进 filter JSON。 |
| recorder 把 realm 注入 embedding 正文 | `recorder.ts:70-94` `buildContentFull` | `⛔反例` | 不借：把 FilterMeta 序列进 `content_full`。与 `T-O-389` / D08-A07 冲突。HEAD `content_full()` 已改成 digest header（`lsrag_compiler/models.py:168-190`）——这条是正确降级。 |
| domain operation **写死** `is_active: 1` | `smind-skill-clean-dedicated-apis/providers/domain/processor.ts:86-94` · `RA-07-LEGACY-06` | `🔶部分借` | **借**：`is_active` 必须按 **operation 版本**编码（D08-T007），不能全局「看见 status 就 1」。对照 `meta_fuser.ts:200-203` 缺省 1（已 ⛔）。不借 Worker 栈。 |
| admin UniversalFilterMeta 全 optional | `smind-admin/core/schemas_common.ts:56-63` | `⛔反例` | 不借 optional 五维。HEAD API FilterMeta 已 `min_length=1`。 |
| Qdrant payload + payload index | https://qdrant.tech/documentation/manage-data/payload/ ；https://qdrant.tech/documentation/manage-data/indexing/ | `🔶部分借` | 借「过滤字段要显式索引；未索引可 fail-fast」。不借 JSON 任意 payload，不引入 Qdrant。 |
| pgvector `WHERE` + 后过滤失败 | https://github.com/pgvector/pgvector README §Filtering | `🔶部分借` | 借「过滤进同一 SQL、列索引」。借失败法：ANN 后过滤 recall 塌缩。不引入 pgvector 扩展。 |
| Supabase：过滤推进 SQL 函数 | https://supabase.com/docs/guides/ai/semantic-search `#filtering-vector-search-by-metadata` | `🔶部分借` | 借「不可在向量 top-k 之后再滤」。不借 JSONB `@>` 弱类型。 |
| OpenSearch faceted search | https://docs.opensearch.org/latest/tutorials/faceted-search/ | `🔶部分借` | 借「facet 字段 keyword 化、查询面与文档面分映射」。不借 OS 栈、nested agg 产品化。 |
| ES 保留元数据字段 | https://www.elastic.co/guide/en/elasticsearch/reference/8.18/mapping-fields.html | `🔶部分借` | 借「系统字段与业务字段必须分名」。不借 `_source` 文档模型。 |
| CF AI Search reserved names + 截断 | https://developers.cloudflare.com/ai-search/configuration/indexing/metadata/ （Last updated 2026-08-26；访问 2026-08-29） | `⛔反例`（栈）/`🔶部分借`（分名失败法） | **不借 CF/R2/Vectorize**。失败条件：reserved `timestamp, folder, filename`；metadata **10 KiB envelope**；**每条 indexed string 仅前 64 UTF-8 bytes 可过滤**。 |
| W3C PROV-DM | https://www.w3.org/TR/prov-dm/ （REC 2013-04-30） | `🔶部分借` | 借「provenance 是关于实体的记录，不塞进数据正文」。不借 RDF/OWL 实现。规范单源。 |
| 非 API 五维权威合同 | 三渠道均无 substrate-fit 的「caller typed + 四 kind + S04 表 + 禁 stub」完整先例 | `🆕净新` | 见 §6 / `NH-N-07-01`。 |
| S06 从 S04 覆盖 context_meta 且不进 g0 | HEAD 只覆盖 g0；legacy fuser 从 JSON 列覆盖且可污染 | `🆕净新` | 见 `NH-N-07-02`。 |

---

## 4. 缺口 / 断点台账 ★ `[核心]`

> 本面核心产出：缺什么、断在哪、多严重、证据何在。编号稳定，供下游引用。

| 编号 | 缺口 / 断点 | 严重度 | 证据（`path:line`） | 影响 |
|------|-------------|--------|----------------------|------|
| `NH-RA07-B01` | 非 API 无五维权威来源：公开 descriptor 无 FilterMeta 字段，runtime 不派生 | `S1 阻断` | `api/models.py:107-130`；`acceptance_snapshot.py:589-615`；`D-18=0` | 四通道「可检索」不是同一过滤面；`G-NH-05` 未落地 |
| `NH-RA07-B02` | `{"source_kind"}` stub 仍可 acceptance-complete，冒充五维 | `S1 阻断` | `acceptance_snapshot.py:591-615`；`T-O-389` CITE | 假绿：有 Revision/向量但无 realm。acceptance 阻断条件缺失 |
| `NH-RA07-B03` | S06 不读 revision semantics；缺则 `context_meta={}`；有则保留模型值 | `S1 阻断` | `generation_assemble.py:59-60`；`generation_construct.py:330-343,1112`；`layered_content.py:117-127` | 模型幻觉 realm；与 g0 分账不完整 |
| `NH-RA07-B04` | 公开 retrieval 无 FilterMeta facet；`channel` 被向量 original/summary 占用 | `S1 阻断` | `retrieval/models.py:14`；`retrieval_request.py:354-355`；`api/models.py:408-411`；`D-19=3/0` | 无法按 realm/业务 channel 过滤；`G-NH-06` |
| `NH-RA07-B05` | `mkb_vector_record_facets` 只投影 `source_kind`，不投影五维 | `S1 阻断` | `vector_publish_commit.py:496-518`；`retrieval_rank.py:80-122` 不 JOIN facets | sidecar 空转；query-time 也不读 S04 五维 |
| `NH-RA07-B06` | 缺五维的通道仍可走 publication/vectorize（本面与面 08 交界） | `S1 阻断` | snapshot 无五维仍 insert revision（`acceptance_snapshot.py:189-225`）；e2e 非 API 无六键断言 | 「有向量」≠「有 FilterMeta」。须在 §9 防假绿 |
| `NH-RA07-B07` | metadata update 可改单键而不重算六元组/`filter_metadata` blob | `S2 重要` | `acceptance_lifecycle.py:378-380`；`targets.py:203-248` | 双账本内部不一致；检索若将来读单键、S07 只钉 blob digest 会分叉 |
| `NH-RA07-B08` | `unknown` 是否允许未锁；API/legacy 已写该字面 | `S2 重要` | `realestate.py:105-106`；legacy `chinatax/processor.ts:76-77`；`T-O-389` 不锁算法 | 闭集 vs 开放值；影响 facet 枚举与假完成 |
| `NH-RA07-B09` | structurize/CLI 可产出空或幻觉 `context_meta`，无 S04 对照 | `S2 重要` | `claude_cli.py:558-563`；`generation_assemble.py:59-60`（仅在缺/非 Mapping 时塞 `{}`，已有则原样保留） | 即使将来有五维账，S06 仍可能分叉，除非 system overlay |
| `NH-RA07-B10` | 四通道强制被误读成「同一派生算法」 | `S3 次要` | QNA `T-O-389`「值的派生算法本文件不锁」；API 已是 per-operation 派生 | 规划若强行一个 URL 解析器覆盖四 kind 会错位 |

---

## 5. 跨功能系统一致性 ★ `[核心]`

- **5.1 整体形态一句话**：S04 持有五维+tags 的 **权威账**；admitted clean / g0 original 是 **正文账**；S06 `context_meta` 必须是权威账的 system-owned 投影；S08/S10 facet 必须是同一权威账的检索投影；三者都不得从模型正文或 `source_kind` stub 发明。
- **5.2 功能间一致性契约（不变量 C1..Cn）**：

| 编号 | 不变量 | 跨哪些面/模块 | 违反后果 |
|------|--------|----------------|----------|
| `NH-C-60` | g0 original body **只等于** 该 Revision 的 admitted clean body（`T-O-386`） | `04` clean · `07` overlay · `08` construct | g0 随过滤标签漂移；digest/replay 崩 |
| `NH-C-61` | FilterMeta 五维 + context tags **永不**写入 `clean_text` / g0 / 向量 required original 正文 | `07` · `08` | 违反 D08-A07 / `T-O-389`；检索与知识互相污染 |
| `NH-C-62` | 四通道 acceptance-complete ⇒ `mkb_intake_revision_semantics` 含六键且五维非 stub | `07` · `08` · `09` | 假绿：有 Item 无可过滤语义 |
| `NH-C-63` | S06 layered `context_meta` 的 realm/type/channel/source_name/tags **权威来自** S04，不从 g0 解析、不以模型为准 | `07` · `08` | 模型幻觉成为服务面 |
| `NH-C-64` | 公开检索的业务过滤键是 FilterMeta 投影；向量 dual-channel 使用 **另一名字** | `07` · `08` · `09` | `channel=sold` 与 `channel=summary` 无法共存 |
| `NH-C-65` | `mkb_vector_record_facets` 若存在某 FilterMeta 键，其 value/definition_digest 必须等于该 serving revision 的 S04 行 | `07` · `08` | 去规范化漂移；query-time join 与 payload 不一致 |
| `NH-C-66` | metadata update 改参与指纹的语义 ⇒ 新 Revision 且 S04 **继承** clean artifact（**目标法**：不得把新 clean 当 admitted body）。HEAD 图仍可能再跑 deterministic clean——测量与 skip/no-op 裁决于面 `08` `NH-RA08-B04` / `G-NH-19` | `07` 拥有五维/新 Revision；`08` 拥有是否重跑清洁 | 把「不 reclean」写成 HEAD 已实现会让 proposed 关掉 08 的 exact-clean 缝 |
| `NH-C-67` | 单键五维与 `filter_metadata` blob 必须同事务同源，禁止只改其一 | `07` | 双账本内部分叉 |
| `NH-C-68` | 未知 **公开** retrieval 键 fail-closed；不得用 `payload_extra` 发明 facet | `07` · `09` | 自由表达式回流 |
| `NH-C-69` | 本面拥有五维权威/投影/facet；面 `08` 只消费，不从 clean/g0/模型猜五维（index §1.2） | `07`/`08` | 两面各写一套语义 |

- **5.3 数据 / 控制流贯穿图**：
```text
[caller descriptor | API raw member]
        |  G-NH-05 MARK: caller / derive / merge
        v
 FilterMeta + ContextMeta.tags     ⊥     admitted clean body
        |                                  |
        v                                  v
 S04 mkb_intake_revision_semantics     S06 g0.body = clean
        |                                  |  (overlay drops model g0)
        +---- system overlay context_meta -+
        |                                  |
        v                                  v
 S08 facets (copy of S04 keys)      dual-channel original|summary
        |                                  |  (MUST be differently named
        v                                  v   from FilterMeta.channel)
 S10 filters: FilterMeta facets  AND  vector-channel selector
        |
        v
 publication/serving (面 08)  —— 不得在此发明五维
```

- **5.4 与邻面的消费 / 提供**：
  - **提供给 08**：五维权威合同、S06 overlay 输入、facet 键清单、metadata 是否新 Revision / 是否继承 clean。
  - **提供给 09**：acceptance-complete 的语义阻断条件、retrieval-facet mega 的假绿封堵。
  - **消费 04**：admitted clean 身份（本面不拥有 clean 算法）。
  - **不拥有**：cuts 切法、serving pointer、是否 reclean。

---

## 6. 净新契约 / 架构边界草案 `[核心]`

> 无先例可借（§3 标 🆕）处，从零草拟契约与边界。**草案，非冻结。**

- **6.1 净新聚合 / 解耦点**：
  - `NH-N-07-01` **非 API 五维权威缝**：在公开 ingest 合同与 `_initial_semantics_tx` 之间新增「必填五维」闸。今日既无 caller 字段也无 kind 派生器。
  - `NH-N-07-02` **S06 system-owned context overlay**：类比 `overlay_system_g0`，在 admit 前用 S04 六键覆盖 `context_meta` 的权威字段；模型/cuts 带来的 realm 只可作非权威候选，不得胜出。
  - `NH-N-07-03` **retrieval 命名空间分裂**：业务 FilterMeta 键 vs 向量 dual-channel 键；facet 投影写 `mkb_vector_record_facets` 或 query-time JOIN S04（落地形态见 §7，不在此锁引擎）。
  - `NH-N-07-04` **acceptance-complete 语义闸**：缺六键或 `filter_metadata` 仍为 `source_kind` stub ⇒ 不得标 complete、不得 vectorize 当成功。
  - `NH-N-07-05` **metadata 六元组一致性**：更新任一 FilterMeta 键必须同事务重写对应 blob 与 `context_tags` 投影，或禁止部分更新。

- **6.2 净新契约叙述规格**（草案）：
  - **输入**：四 kind 的 admitted clean + （caller 元数据 ∧/∨ 闭集派生结果）。具体来源 **不锁**（`G-NH-05`）。
  - **输出**：`mkb_intake_revision_semantics` 六键；S06 `context_meta.{realm,type,channel,source_name,tags}` 与之逐字相等；g0.body 与五维无关。
  - **边**：缺任一 FilterMeta 维 → typed 4xx/409，**不是** stub。`unknown` 若被 owner 允许，必须是 **显式登记字面** 而非缺省空。
  - **检索**：公开 filters 可含 FilterMeta 键（登记后）；向量 original/summary 使用 **另一 key 名**（`G-NH-06` 选项并列）。
  - **metadata**：`semantics` 可含五维；成功且指纹变 ⇒ 新 Revision + 同 clean digest；S06 overlay 必须重投影；不自动 reclean。

- **6.3 架构边界（与既有 / 相邻面）**：
  - 权威表留在 S04，不把 JSON 列或 R2 member 当 SSOT（legacy 反例）。
  - 不把五维塞进 `content_full` 正文（legacy `buildContentFull` 反例；HEAD digest-header 已是正确方向）。
  - 不新增第五 source kind；不把 `payload_extra` 升级为 FilterMeta。
  - 面 08 只读投影；面 09 证明「有向量无 realm」为失败。

---

## 7. Substrate-fit / 技术路线过滤 ★ `[核心]`

> 把每个「借来的机制」按本仓技术路线降级或重映射。

| 借鉴点 | 原机制（参考处） | 是否冲突本仓路线 / 约束 | 落地形态（降级 / 重映射 / 直采） |
|--------|------------------|--------------------------|-----------------------------------|
| API FilterMeta 六元组 | HEAD `semantics.py` + 三 mapper | 不冲突；已是单体 FastAPI + 闭集 | **直采**，扩展到非 API 合同 |
| S04 语义表 | HEAD DDL + registry | 不冲突 | **直采** 为四通道权威 |
| system g0 overlay | HEAD `overlay_system_g0` | 不冲突；不重开 cuts | **直采** g0；**重 substrate** 出平行的 context overlay |
| 未知 filter fail-closed | HEAD retrieval | 不冲突 | **直采**；扩展登记键 |
| dedicated 五维字段名 | legacy `*FilterMeta` | 字段名不冲突；R2/CF/JSON 列冲突 `T-O-42` | **降级**：只借名字与「不进正文」；权威改写 S04 表 |
| `meta_fuser` JSON SSOT | `meta_fuser.ts:172-185` | 冲突：D1 JSON 列、缺省 is_active=1 | **不落地**；反例 |
| `vec_channel` 分名 | `engine.ts:126` | 分名思路不冲突；Vectorize metadata 冲突 | **重映射**为公开合同上的第二键名（具体字面 `G-NH-06` 不锁） |
| `buildContentFull` 注入 realm | `recorder.ts:70-94` | 冲突 `T-O-389` | **不落地**；HEAD digest header 已替代 |
| Qdrant payload index | qdrant.tech payload/indexing | 冲突：外部向量库、自由 JSON payload | **降级**为：在已有 `mkb_vector_record_facets` 上为闭集键建索引/写入；或 SQL JOIN S04 |
| Qdrant unindexed fail-fast | indexing.html「Block Queries That Filter on Unindexed Fields」 | 机制不冲突；产品冲突 | **重映射**到已有 `RETRIEVE_FILTER_INVALID` |
| pgvector WHERE + 后过滤坑 | pgvector README Filtering | 本仓已是 SQL 扫描+fence，无 HNSW 后过滤；但「先 top-k 再滤」仍是假绿 | **借失败法**：facet 必须进入候选 SQL，而不是 pack 之后再滤 |
| Supabase 过滤进函数 | supabase semantic-search | JSONB `@>` 过宽；PostgREST 后过滤是反例 | **重映射**：typed SQL 谓词；禁止检索后再滤 realm |
| OpenSearch facets | OS faceted-search tutorial | 无 OS 栈；keyword 映射可类比闭集 | **降级**：facet=登记键上的 eq 过滤，不做 agg UI |
| ES `_id` 保留字段 | ES 8.18 mapping-fields | 无 ES；同名冲突可类比 | **重映射**：不要让业务 `channel` 占用系统 `channel` |
| CF reserved names | developers.cloudflare.com/ai-search/.../metadata | **整栈禁**（R2/Workers/Vectorize） | 只保留「reserved 名单」失败法，**零代码回流** |
| W3C PROV-DM | TR/prov-dm REC 2013 | 不引入 RDF | **降级**：S04 行 = provenance record，与实体正文分账 |
| 非 API 权威合同 | 无先例 | 绿地 `T-O-42` | **净新** |

本仓过滤摘要：单体 Python 3.12 FastAPI、local Turso、S03 七表无环、eq-only 守卫、S13 bytes-first、禁 CF/R2/SMCP/动态 plugin/自由表达式。能跑但越界最多 `🔶部分借`。

---

## 8. 反例坑表 + 净新表 `[核心]`

### 8.1 反例坑表 ⛔

| 反例 | 来源锚 | 为什么不可借 |
|------|--------|--------------|
| 缺 FilterMeta 时写 `{"source_kind":...}` 仍 accept | `acceptance_snapshot.py:598` | `T-O-389` 点名禁止 stub 冒充五维 |
| 空 `context_meta={}` 当 overlay 成功 | `generation_assemble.py:59-60`；`claude_cli.py:561` | S06 与 S04 继续分叉；模型/stub 可幻觉 |
| 公开 `channel` = original/summary | `retrieval_request.py:354-355` | 吞掉 FilterMeta.channel |
| JSON 列 `payload_filter_meta` 当权威 | `meta_fuser.ts:15-19,177-185` | 非 S04 表；`T-O-42` 禁回流 |
| 缺 `is_active` 默认 1 | `meta_fuser.ts:200-204` | 把未知当成在架；D08-T007 要求按 operation 版本编码 |
| universal 不写五维 ⇒ 可跳过 | universal services/flows 零赋值 | 遗产缺口不能当产品法 |
| 把 realm/type/channel 拼进 embedding 正文 | `recorder.ts:70-94` | 污染 g0/向量原文；与双账本相反 |
| R2 atomic_bundle + child UUID 承载 FilterMeta | dedicated `processor.ts` `payload_filter_meta` + `r2_key` | 平台债；本仓 S13/S04 已有 typed 表 |
| CF AI Search / Vectorize 元数据信封 | Cloudflare docs | 栈禁；10KiB envelope、64-byte filterable 截断不适合闭集账本 |
| ANN 后过滤当 facet | pgvector README；Supabase「`.eq()` after rpc」 | 选择性过滤导致结果数 < k，假绿 |
| 用 `payload_extra` 传五维 | `common/models.py:1-5` | 明文不得控状态转移 |
| 把 QNA/T-P-NH-7 当 HEAD 已实现 | initial-planning 叙事 | 冻结 ≠ 代码 |

### 8.2 净新表 🆕

| 项 | 为什么无先例 | 草案落点 |
|----|--------------|----------|
| 非 API 四 kind 的五维权威合同 | API 有派生；caller 面 0；legacy 非 API 也缺；外部无「S04 表 + 禁 stub + 四 kind」 | `NH-N-07-01` / `G-NH-05` |
| S06 从 S04 覆盖 context_meta、同时保持 g0=clean | HEAD 只 overlay g0；legacy overlay 来自 JSON 列 | `NH-N-07-02` |
| 公开检索 FilterMeta facet + 与 vector-channel 分名 | HEAD facet 0；legacy 用 `vec_channel` 但绑 Vectorize | `NH-N-07-03` / `G-NH-06` |
| acceptance-complete 的五维阻断 | HEAD 无此闸 | `NH-N-07-04` / §9 |
| metadata 更新的六元组原子性 | HEAD key-wise merge | `NH-N-07-05` |

---

## 9. 验收格栅草案（防假绿）`[核心]`

> 草案——落地验收归下游。此处先封堵 fake-green。四通道强制 ≠ 四通道同一派生算法。

| 功能 F | 收口目标（一句话可验证） | Test-ID（拟） | 测试层 | 防假绿要点 |
|--------|--------------------------|----------------|--------|------------|
| 非 API 五维写入 | inline/http/local 各至少一条路径在 `mkb_intake_revision_semantics` 含六键，且 `filter_metadata` **不是** `{"source_kind":...}` | `NH-A-07-01` | `集成` | 禁止只测 API scatter 就宣称四通道 |
| acceptance 阻断 | 缺任一 FilterMeta 维 ⇒ 不得 `admission_result` 当 complete，不得插入「假六键」 | `NH-A-07-02` | `单元` + `集成` | 禁止 stub 当成功；禁止 503 当通道 DoD |
| S06 overlay | 结构化产物 `context_meta.realm/type/channel/source_name` 等于 S04 同行；g0.body 等于 clean 且不含五维 JSON | `NH-A-07-03` | `单元` | 禁止 CLI stub `{}` 绿；禁止模型自带 realm 覆盖 S04 |
| g0 同一性 | overlay 后 g0 唯一、body digest = clean digest | `NH-A-07-04` | `单元` | 已有 `test_r5_assemble` 可扩；不得改 cuts |
| 公开 facet | `filters` 能按至少 `realm` eq 过滤；未知键仍 422 | `NH-A-07-05` | `集成` | 禁止只测 `source_kind`/`intake_item_uuid` |
| 向量 channel 分名 | 业务 FilterMeta.channel 与 original/summary **可同时出现在同一请求语义中而不歧义** | `NH-A-07-06` | `单元` | 具体公开名字不锁（`G-NH-06`）；测的是无歧义 |
| retrieval-facet mega | 默认组合根四通道各 1 条：有向量 **且** 用 FilterMeta 键能召回/排除 | `NH-A-07-07` | `retrieval-facet mega` | **有向量无 realm = 失败**。禁止 monkeypatch 冒充 live 接线；禁止空 `clean_text` |
| metadata 改五维 | 改 realm 后新 Revision、clean digest 不变、S04 六键与 blob 一致、facet/S06 随 serving revision | `NH-A-07-08` | `集成` | 禁止只断言 Task succeeded；面 08 另测 serving |
| metadata 继承 clean artifact | 同 clean `stored_object_uuid` 被新 Revision 引用 | `NH-A-07-09` | `集成` | 本面只验 S04 继承。图是否再执行 clean Process 交面 `08` `NH-A-08-04` / `G-NH-19`，本面不宣称 skip |
| 未知公开键 | `filters.forbidden` 仍 `RETRIEVE_FILTER_INVALID` | `NH-A-07-10` | `单元` | 扩 facet 后回归，防自由键 |

**假绿封堵清单（必须写进下游执行）**：

1. monkeypatch browser/http ≠ live 接线。
2. 空正文 / 空 `context_meta` ≠ 成功。
3. Task succeeded ≠ 可检索。
4. 只测 API fixture ≠ 四通道。
5. 有 embedding 无 realm ≠ 完成（`T-O-389` + `T-O-376`）。
6. 503 / stub CLI ≠ 通道 DoD。

---

## 10. 优先级建造建议 + owner-gate 候选 `[核心]`

- **10.1 建造顺序（依赖序，分批不一次性深做）**：

| 顺序 | 工作簇 | 依赖 | 复用判定 |
|------|--------|------|----------|
| `P0-a` | 把 `_initial_semantics_tx` 的 stub 改成缺五维 fail-loud（acceptance 闸） | `T-O-389`；不改 g0 切法 | `♻️重 substrate` |
| `P0-b` | 非 API 五维权威面（typed 合同或 kind 派生器或 merge——**待 G-NH-05**） | `P0-a` 的失败形状 | `🆕净新` |
| `P0-c` | S06 system-owned `context_meta` overlay（读 S04，不进 g0） | `P0-a/b` 已有权威行 | `♻️重 substrate`（平行于 overlay g0） |
| `P0-d` | channel 分名 + 公开 FilterMeta facet 键登记 | `G-NH-06`；`P0-b` | `♻️重 substrate`（扩 `_FILTER_KEYS` + facet 写入） |
| `P0-e` | vectorize 投影五维到 `mkb_vector_record_facets` 或 SQL JOIN S04 | `P0-d` | `♻️重 substrate` |
| `P1-a` | metadata 六元组原子性 | `P0-b` | `♻️重 substrate` |
| `P1-b` | retrieval-facet mega（交面 09 收口） | `P0-d/e` + 面 08 serving | `🆕净新`（测试矩阵） |

- **10.2 owner-gate 候选（只 MARK 不裁决 → 上交 index §4 / 下游决策登记）**：

| gate-ID | 决策点 | 候选选项（不预设倾向） | 影响 |
|---------|--------|------------------------|------|
| `G-NH-05` | 非 API 五维权威来源与 `unknown` 法 | `caller required` / `kind-closed derivation` / `caller+derivation merge`；**另裁** `unknown`：`禁止该字面` / `允许但须显式登记` / `仅部分 kind 允许` | 公共 ingest 合同、S04 写入、S06 overlay、facet 枚举 |
| `G-NH-06` | FilterMeta `channel` 的公共查询命名 vs 向量 original/summary | `semantic_channel` / `source_channel` / `重命名 vector channel` / `其他无歧义方案` | API retrieval 合同、DDL `mkb_vector_records.channel`、兼容旧过滤器 |

**本面不对上表任一选项写推荐句。** 证据仅表明：HEAD API 已走闭集派生且 REA 已写 `"unknown"`；遗产用 `vec_channel`/`content_channel` 避开碰撞；公开检索今日占用了 `channel`。

---

## 11. 核验记录 `[核心]`

> 对抗性自检：本文每个关键锚点是否真核验过。

| 锚点（host-ID） | 是否核验 | 方式（grep/read/run） | 备注 / 修正 |
|------------------|----------|------------------------|--------------|
| `D-16` 10 semantics | `✅` | `read_file registry.py:229-239` + `uv run python` | 与 index 一致；HEAD `1221aa1` |
| `D-17` 6 keys | `✅` | `read_file semantics.py:12-63` | FilterMeta 5 + tags |
| `D-18` 非 API 写入 0 | `✅` | `read_file acceptance_snapshot.py:589-615`；grep runtime `filter_meta` | 仅 snapshot/scatter/API preflight |
| `D-19` 3/0 | `✅` | `read_file retrieval/models.py:14`；`retrieval_request.py:324-361` | `channel`∈{original,summary} |
| `D-07-F01` descriptor 0 | `✅` | `read_file api/models.py:107-144`；`common/models.py:20-26` | extra=forbid |
| `D-07-F02` facet=source_kind | `✅` | `read_file vector_publish_commit.py:496-518`；`vectorize.py:319-324` | |
| overlay g0 / `{}` | `✅` | `read_file generation_assemble.py:17-62` | 正例 g0 + 反例 context |
| structurize 输入 | `✅` | `read_file generation_construct.py:330-343,1092-1218` | 无 semantics |
| metadata 继承 clean | `✅` | `read_file acceptance_lifecycle.py:213-409`；`acquisition_intents.py:115-220,207-214`；对照面 08 `lsrag_definition.py:299-306` / `clean_preflight.py:28-127` | **修正**：S04 继承 artifact 为真；「HEAD 不 reclean」过声称——clean Process 仍执行 |
| API e2e 六键 | `✅` | `read_file test_registered_api_scatter.py:287-296` | 正例 |
| 未知 filter | `✅` | `read_file test_retrieval_service.py:456-460` | 正例 fail-closed |
| `T-O-386/389` | `✅` | `read_file pre-initial-planning-qna.md:90-93,671-721` | **CITE 目标法，非 HEAD 实现** |
| `D08-T007` | `✅` | `read_file D08-legacy-capabilities-migration.md:98,361` | 原范围三 provider；QNA 扩展四通道 |
| legacy dedicated FilterMeta | `✅` | `read_file chinatax/schemas.ts:52-83`；三 processor | 借字段名 |
| legacy meta_fuser | `✅` | `read_file meta_fuser.ts:1-243` | JSON 列权威=反例 |
| legacy universal 不写 | `✅` | `grep` universal services/flows 零命中；schema optional | 不能当可跳过 |
| legacy vec_channel | `✅` | `read_file engine.ts:110-126`；`recorder.ts:70-175` | 分名正例 + content_full 反例 |
| WEB Qdrant payload/index | `✅` | `web_search` + `open_page` 两 URL | 访问日 2026-08-29；非本仓后端 |
| WEB pgvector Filtering | `✅` | `open_page` raw README §Filtering | 后过滤失败法 |
| WEB OpenSearch facets/nested | `✅` | `open_page` 两官方页 | 不引入 OS |
| WEB ES metadata fields | `✅` | `open_page` 8.18 mapping-fields | 保留字段 |
| WEB CF reserved names | `✅` | `open_page` AI Search metadata | 栈禁，只借失败法 |
| WEB Supabase filter-in-SQL | `✅` | `open_page` semantic-search | 后过滤反例 |
| WEB PROV-DM | `✅` | `open_page` w3.org/TR/prov-dm | 规范单源 |
| index 分母未改写 | `✅` | `read_file assessment-index.md:181-201` | D-16..19 原样引用 |
| 未跑全量 pytest | `部分` | 本面以 read/grep/分母脚本为主 | 不假装全绿；水位沿用 `D-23/D-24` |

**修正记录**：PROMPT 行号提示与 HEAD 实测一致（`acceptance_snapshot` 576-641、`overlay` 17-62、`registry` 229-239 未漂移）。未把 `T-P-NH-7` 或 QNA 当代码事实。

---

## 12. 收尾 Verdict 与交接 `[核心]`

- **本面裁定**：面 07 为 **P0 / 🔴**。可复用 substrate 是 API 六元组、S04 表、system g0、未知键 fail-closed、metadata「新 Revision + **S04 继承 clean artifact**」。S1 阻断是非 API stub 仍能 complete、S06 不投影五维、公开检索无 FilterMeta facet 且 `channel` 撞名。外部/遗产可借 **字段名与分账失败法**，不可借 JSON/R2/CF payload 权威。`G-NH-05`/`G-NH-06` 只 MARK。**不**把 HEAD 写成已 skip clean Process。
- **交接下游**：缺口台账（§4）→ 规划；净新契约（§6）→ 设计；owner-gate 候选（§10.2）→ 决策登记；验收格栅（§9）→ 执行计划与面 09 mega。面 08 冻结前必须消费本面投影合同（index §8.1）。
- **冻结前置**（本 analysis 保持 `draft`，不标 reviewed/frozen）：
  1. review-fleet 交叉核对 §3 正反例与 §7 substrate-fit；
  2. 与面 08 对账 `NH-C-60..69`（尤其 reclean 与 serving）；
  3. owner 未裁决前不得把 `G-NH-05/06` 任一选项写成方案；
  4. HEAD 若改 `D-16..D-19` 须先修订 index。

**必须回答的五问（调查结论，非裁决）**：

1. **非 API 五维从哪来？`unknown`？** HEAD：**都没有**（caller 面 0、派生器 0）。API 已是 operation 闭集派生，且部分路径已写 `"unknown"`。选项见 `G-NH-05`，本面不选。
2. **业务 channel 与向量 channel 如何分名？** HEAD 未分名，已碰撞。遗产用 `content_channel`/`vec_channel`。选项见 `G-NH-06`，本面不选。
3. **S06 怎样覆盖模型 context 而不污染 g0？** 现状：g0 已 system overlay；`context_meta` 未 overlay。草案：平行的 system overlay，权威读 S04，g0 仍只含 clean（`NH-N-07-02`）。
4. **metadata update 改五维 / 新 Revision / 重 clean？** 可改已登记键；指纹变则新 Revision；S04 **继承** clean artifact。**图仍可能再跑 deterministic clean**（权威在面 `08` `NH-RA08-B04`）。blob 与单键一致性未做（`NH-RA07-B07`）。
5. **stub 为何不能冒充五维？acceptance-complete 阻断？** 因为 `filter_metadata={"source_kind"}` 不是五维元组，且不展开 `realm..context_tags` 行。阻断条件草案：六键缺失或 blob 等于 source_kind stub ⇒ 不得 complete、不得把后续向量当通道 DoD（`NH-A-07-02/07`）。

---

## 附录 A · 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | `2026-08-29` | `Grok analysis-fleet / review-fleet` | 初稿（measure-first + 三渠道正反例 + 缺口台账）；状态 `draft` |
| v0.2 | `2026-08-29` | Grok fix-fleet | 吸收已核实 review：R1-I02/R4-I05 删除「HEAD 不 reclean」过声称，改 S04 继承 + 图仍执行 clean（权威 08-B04）；R2 补 `RA-07-LEGACY-06` is_active 写死；R3-I15 WEB-07 补 10KiB/64-byte。状态仍 `draft` |

## 附录 B · Reference Anchor 卡片（稳定 ID）

每条含：结论原子句 / 来源与版本或访问日 / 正例或反例 / 置信 / substrate-fit / 命中缺口。

| ID | 结论原子句 | 来源 | 正/反 | 置信 | substrate-fit | 命中 |
|----|------------|------|-------|------|---------------|------|
| `RA-07-HEAD-01` | FilterMeta 五维 + 六元组是 API member 的 typed 合同 | HEAD `semantics.py:12-63` `1221aa1` | 正 | HEAD | `✅借` | — |
| `RA-07-HEAD-02` | 十个 SemanticDefinition 已对全部 intake 登记 | HEAD `registry.py:229-239` | 正 | HEAD | `✅借` | 登记≠写入 |
| `RA-07-HEAD-03` | API e2e 把六键写入 revision_semantics | HEAD `test_registered_api_scatter.py:296` | 正 | HEAD | `✅借` | — |
| `RA-07-HEAD-04` | system overlay 丢模型 g0 且 body=clean | HEAD `generation_assemble.py:17-47` | 正 | HEAD | `✅借` | `NH-C-60` |
| `RA-07-HEAD-05` | 未知 retrieval filter key fail-closed | HEAD `retrieval_request.py:333-340` | 正 | HEAD | `✅借` | `NH-C-68` |
| `RA-07-HEAD-06` | metadata 指纹变则新 Revision 且 S04 继承 clean artifact；图是否再跑 clean 不在本面宣称 | HEAD `acceptance_lifecycle.py:213-278`；对照 `lsrag_definition.py:299-306` | 正（继承）/限（Process 仍跑） | HEAD | `✅借` 继承；clean 执行交 08 | `NH-C-66` |
| `RA-07-HEAD-07` | 非 API 无 filter_meta 时写入 source_kind stub 且仍 accept | HEAD `acceptance_snapshot.py:591-615` | 反 | HEAD | `⛔反例` | `NH-RA07-B01/B02` |
| `RA-07-HEAD-08` | 非 API 公开 descriptor 无 FilterMeta 字段 | HEAD `api/models.py:107-130` | 反 | HEAD | `⛔反例` | `NH-RA07-B01` |
| `RA-07-HEAD-09` | structurize 输入只有 clean/markdown；overlay 缺 meta 则 `{}` | HEAD `generation_construct.py:330-343`；`generation_assemble.py:59-60` | 反 | HEAD | `⛔反例` | `NH-RA07-B03` |
| `RA-07-HEAD-10` | 公开 filters 三键且 channel=original\|summary；FilterMeta facet=0 | HEAD `retrieval/models.py:14`；`001_initial.sql:1444` | 反 | HEAD | `⛔反例` | `NH-RA07-B04` |
| `RA-07-HEAD-11` | vector facet 只写 source_kind | HEAD `vector_publish_commit.py:496-518` | 反 | HEAD | `🔶部分借`（表形态） | `NH-RA07-B05` |
| `RA-07-HEAD-12` | metadata merge 可只改单键 | HEAD `acceptance_lifecycle.py:378-380` | 反 | HEAD | `🔶部分借`（骨架） | `NH-RA07-B07` |
| `RA-07-LEGACY-01` | 三 provider 共用五维接口，meta 不进正文 | `chinatax/schemas.ts:52-83` 等 | 正 | legacy | `🔶部分借` | 借 D08-T007 字段 |
| `RA-07-LEGACY-02` | constructor 以 JSON 列为 FilterMeta 唯一真理源 | `meta_fuser.ts:15-19,172-207` | 反 | legacy | `⛔反例` | 不借 JSON SSOT |
| `RA-07-LEGACY-03` | universal cleaner 不生成 FilterMeta | universal services/flows 零写入 | 反 | legacy | `⛔反例` | 非 API 缺五维不是可跳过 |
| `RA-07-LEGACY-04` | 向量层用 `vec_channel`/`content_channel` 与业务 channel 分名 | `engine.ts:126`；`recorder.ts:159` | 正 | legacy | `🔶部分借` | `G-NH-06` |
| `RA-07-LEGACY-05` | 把 realm 等注入 embedding `content_full` | `recorder.ts:70-94` | 反 | legacy | `⛔反例` | `NH-C-61` |
| `RA-07-WEB-01` | payload 与向量分存；过滤字段需显式 payload index | qdrant payload + indexing 官方，访问 2026-08-29 | 正 | 外部 | `🔶部分借` | 机制类比 sidecar facet |
| `RA-07-WEB-02` | 未索引字段过滤可被 strict mode 拒绝 | qdrant indexing「Block Queries…」 | 正/限制 | 外部 | `🔶部分借` | 对齐 HEAD fail-closed |
| `RA-07-WEB-03` | ANN 后过滤会 recall 塌缩 | pgvector README Filtering；v0.8.6 页 | 反（失败法） | 外部 | `🔶部分借` | 禁止 top-k 后再滤 realm |
| `RA-07-WEB-04` | 过滤必须推进 SQL；RPC 后再 eq 会少结果 | supabase semantic-search 官方 | 正/限制 | 外部 | `🔶部分借` | |
| `RA-07-WEB-05` | facet 字段需 keyword；post_filter 保选项 | OpenSearch faceted-search 官方 | 正 | 外部 | `🔶部分借` | 不引入 OS |
| `RA-07-WEB-06` | 系统元数据字段名保留，根级占用失败 | ES 8.18 mapping-fields | 反（失败法） | 外部 | `🔶部分借` | `G-NH-06` |
| `RA-07-WEB-07` | reserved names + 10 KiB envelope + 每字符串仅前 64 UTF-8 bytes 可过滤 | CF AI Search metadata，2026-08-26，访问 2026-08-29 | 反（栈） | 外部 | `⛔反例` 栈 / `🔶` 分名 | 禁 CF |
| `RA-07-LEGACY-06` | domain 本 operation 写死 `is_active: 1`，无下架推导 | `domain/processor.ts:86-94` | 正/限 | legacy | `🔶部分借` | D08-T007 按 operation 编码 |
| `RA-07-WEB-08` | provenance 是关于实体的记录，与数据分账 | W3C PROV-DM REC 2013-04-30 | 正 | 外部（规范单源） | `🔶部分借` | `NH-C-61` |
