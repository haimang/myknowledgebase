# 调查面 `08` · publication 贯通、七意图与 Intake lifecycle — 深度评估

> **对象 / scope-fence**：admitted clean → structurize / construct / vectorize / publication / retrieval 贯通；七意图 applicability；rebuild / metadata / lifecycle 是否重 clean；single / scatter serving pointer；产品终态「可检索」必须含哪些 proof / query / facet。**本面不含**：生成算法 / cuts / g0 kernel（沿用，交生成面）；语义来源权威（面 `07`）；clean 变换实现（面 `04`）。
> **日期**：`2026-08-29`
> **作者**：`Grok analysis-fleet / review-fleet`（fleet / panel：`new-harvest-reference-anchor`）
> **文档性质**：`assessment / analysis`（单面 measure-first 深评；零决策——只 MARK 不裁决）
> **文档状态**：`draft`
> **流水线位置**：站② · 上游 = [[assessment-index]]（消费其冻结分母）
> **对照参考**：HEAD `1221aa1`；QNA v0.5 `T-O-376/381/386/389`（只 CITE）；`docs/baseline/qna-truth/S09.md` `T-O-242..244`；legacy-family clean dispatcher / rag vectorizer / rag dispatcher（ReferenceAnchor，`T-O-42`）；Elastic Aliases / OpenSearch Manage Aliases / Lucene `IndexWriterConfig.setSoftDeletesField` / Elastic near-real-time search / Elastic optimistic concurrency（访问日 `2026-08-29`）
> **上游权威输入**：
> - `docs/eval/new-harvest/assessment-index.md` — §2.2 `D-01/D-04/D-07/D-14/D-16..19/D-21/D-24`；§3.08；§7 已交付尾链
> - `docs/eval/new-harvest/pre-initial-planning-qna.md` — `T-O-376/381/386/389`（只 CITE，不扩冻）
> **下游消费者**：`docs/eval/new-harvest/planning-proposed.md` · `pre-charter-qna.md`（owner-gate 裁决）· 设计/执行制品

---

## 0. Verdict（结论先行）`[核心]`

- **0.1 一句话缺口 / 现状判断**：HEAD 已有 **single 尾链 + scatter child `index.validate_publication` + serving/pointer CAS**，且若干 e2e **调用** `retrieval:search`（inline/rebuild/reactivate/index.rebuild），但这些 POST **均无** `namespace_key`/`namespace_uuid`，当前公共解析 **必 422**（`src/contracts/api/models.py:505-509`；`retrieval_request.py:265-269`；README K1）——**调用 ≠ 命中，不是检索正例**。**四通道 live-to-vector 未接通**；API scatter 停在 `publication_ready`、source capability e2e 红且 monkeypatch；「可检索」仍缺 FilterMeta facet 终验；rebuild/metadata **复用 accepted clean 字节作输入，却仍走 inline decode+clean**。
- **0.2 Top blockers（最关键断点）**：
  1. `NH-RA08-B01`（S1）：`T-O-376/381` 的四通道真实 Process→可检索向量未成立；source capability e2e 停 `running`，且 `pipeline._http_fetcher` / `_browser_fetcher` monkeypatch（`T-O-378`）。
  2. `NH-RA08-B02`（S1）：API scatter e2e 只断言 `publication_ready`，**零** `retrieval:search`；Task succeeded / 成员 flag **不等于**可检索。
  3. `NH-RA08-B03`（S1）：检索公开 filter 仅 `intake_item_uuid|source_kind|channel`（`D-19`）；publication `layer_b_keys_echo_json` 硬编码 `["source_kind"]`；FilterMeta 五维 facet=0，与 `T-O-389` 产品终态不对齐。
- **0.3 总体方向建议**（非裁决）：**勿重做** tail / g0 / API scatter 图；把缺口收成「接通 + 终验」：四通道 default-root e2e 走到 `retrieval:search`；scatter 补同一 query；为七意图写出 **合法格 / 非法格** 而不是 28 格笛卡尔积；rebuild/metadata 钉 exact-clean 合同（是否再跑 clean Process 只 MARK）。
- **0.4 如何读本台账**：见上方头部「图例」；本面主题轴 = `尾链贯通 / 七意图 applicability / exact-clean vs 重 clean / serving pointer / 可检索 proof`。

---

## 1. 方法与证据基线 `[核心]`

> 读了哪些代码/文档/参考；什么算可采信；怎么复现。**先证可证性，再下判断。**

- **1.1 本仓证据（如何测量）**：HEAD `1221aa1` 的 Workflow 声明、intake runtime mixin、lifecycle 服务、retrieval SQL fence、公共路由、e2e/unit。每条关键结论 `path:line`。仓内 baseline `S09`/`S10`/`spec-index` 只作对照，与 HEAD 冲突显式登记。`docs/eval/new-harvest/initial-planning.md` 只作叙事/初判，**不是**真相。
- **1.2 外部 / 参考来源 + 置信**：
  | 渠道 | 来源 | 访问日 | 支撑的原子结论 | 限制 | 置信 |
  |------|------|--------|----------------|------|------|
  | HEAD | 本库代码/DDL/测试 | 2026-08-29 | 尾链、意图闭集、pointer CAS、检索 fence、测试水位 | 不得外推未跑路径 | 最高 |
  | BASELINE | `docs/baseline/qna-truth/S09.md` `T-O-242..244`；`spec-index.md` §3.9 | 2026-08-29 | PublicationProof ≠ serving；S09 不写 serving | 旧 Truth 若与 HEAD 实现形态冲突须登记 | 仓内文档锚 |
  | LEGACY | `context/legacy-family/smind-clean-dispatcher/flows/finalizer.ts` 等（只读，未 import/运行） | 2026-08-29 | publication 应是显式一步；purge 应排除 serving；R2 key / output_payload / 单 Index upsert **反例** | `T-O-42` 禁回流 CF/R2/SMCP | 参考 |
  | WEB | Elastic Aliases；OpenSearch Manage Aliases；Elastic NRT search；Lucene `setSoftDeletesField`；Elastic OCC | 2026-08-29 | 原子 alias swap、write-index 单写、refresh≠commit、soft-delete 无 undelete API、OCC 序列号 | **不得**证明 MKB 现状；不得引入 ES/OS/Lucene 引擎 | 外部机制 |
- **1.3 ★ 可复现命令清单（measure-first）**：
```bash
git -C /mnt/usb/workspace/myknowledgebase rev-parse --short HEAD
# 期望：1221aa1

uv run python - <<'PY'
from src.contracts.api.models import TaskCreateRequest
from src.services.registry import DEFAULT_SOURCE_KINDS, DEFAULT_SEMANTICS
from src.workflows.builtin_scatter import (
    BUILTIN_REGISTERED_API_SCATTER_CHILD_WORKFLOW,
    BUILTIN_REGISTERED_API_SCATTER_ROOT_WORKFLOW,
)
from src.workflows.lsrag_definition import (
    BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW,
    SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS,
)
from src.services.retrieval.models import _FILTER_KEYS
print("intents", TaskCreateRequest.model_fields["request_intent"].annotation)
print("source_kinds", len(DEFAULT_SOURCE_KINDS), sorted(DEFAULT_SOURCE_KINDS))
print("semantic_definitions", len(DEFAULT_SEMANTICS))
print("public_selector_keys", len(SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS))
print("retrieval_filter_keys", sorted(_FILTER_KEYS), len(_FILTER_KEYS))
print("single_purpose", BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW.purpose_key)
print("child_required", BUILTIN_REGISTERED_API_SCATTER_CHILD_WORKFLOW.required_process_keys)
print("root_purpose", BUILTIN_REGISTERED_API_SCATTER_ROOT_WORKFLOW.purpose_key)
PY

rg -n "request_intent|validate_publication|publication_ready|retrieval:search" \
  src/contracts/api/models.py src/workflows src/runtime/intake \
  src/services/intake_lifecycle src/services/retrieval api/public/routes.py tests/e2e

uv run pytest \
  tests/e2e/test_registered_api_scatter.py::test_registered_api_three_raw_provider_operations_map_seal_and_persist_semantics \
  tests/e2e/test_source_capability_paths.py::test_local_static_browser_and_pdf_sources_produce_distinct_frozen_acquisition_evidence \
  -q --tb=line
```
  本面 2026-08-29 复跑：上述两 case **1 passed / 1 failed**（与冻结 `D-24` 同型）；source capability 在 `tests/e2e/test_source_capability_paths.py:168` 对 `static` 断言 `succeeded`，实际停 `running`（`completed_at: None`，`counts.active=1`）；测试内 `_await_terminal` 时限 8s（`:59`）。合计墙钟约 43s。**不改写** index `D-24` 数字。
- **1.4 范围围栏**：本面**只**覆盖 publication 贯通、七意图 applicability、lifecycle/rebuild/metadata 与 serving pointer、可检索 proof。**不含**：cuts/g0 算法、五维权威派生（面 07）、clean strategy 实现（面 04）、runtime 选型（面 05）、upload 产品面（面 06）、graph algebra（面 01）、actual S05 digest（面 02）。

---

## 2. 当前结构分析（HEAD 实测 · measure-first）★ `[核心]`

> 按主题轴逐条测，每条钉 `path:line`。先冻结本面分母，再逐轴展开。

### 2.1 ★ 冻结分母（FROZEN denominators · HEAD）

> 引用 [[assessment-index]] §2.2 中属于本面的分母，并补本面专属分母。下游不得另估。

| 分母 | HEAD 实测值 | 证据锚（`path:line`） | 来源 |
|------|-------------|------------------------|------|
| `D-01` source kind | `4` | `src/services/registry.py:171-208` | index §2.2 |
| `D-04` registered API operation | `3` | `intake/api/registry.py:73-104`（index 冻结） | index §2.2 |
| `D-07` scatter Workflow identity | `2`（root + child） | `src/workflows/builtin_scatter.py:352-380,571-599` | index §2.2 |
| `D-14` public `/v1` route / object-upload | `28 / 0` | `api/public/routes.py:56-469`（本面复计 `@router.` = 28） | index §2.2 |
| `D-16` canonical intake SemanticDefinition | `10` | `src/services/registry.py:229-239` | index §2.2 |
| `D-17` FilterMeta+tags semantic key | `6` | `src/contracts/intake/semantics.py:12-63`；`registry.py:234-239` | index §2.2 |
| `D-18` 非 API 通道实际五维写入 | `0`；fallback `source_kind` blob | `src/runtime/intake/acceptance_snapshot.py:589-615` | index §2.2 |
| `D-19` public retrieval filter / FilterMeta facet | `3 / 0` | `src/services/retrieval/models.py:14-34`；`retrieval_request.py:324-361` | index §2.2 |
| `D-21` 默认组合根 browser_fetcher / clean_llm 注入 | `0 / 0` | `api/app.py:332-345`（index 冻结） | index §2.2 |
| `D-24` 三 provider e2e / source capability e2e | `1 passed / 1 failed` | 本面复跑同型；source `:168` 停 `running` | index §2.2 |
| `D-08-A` Task `request_intent` 闭集 | `7` | `src/contracts/api/models.py:278-286`；`src/runtime/task/task_create.py:37-46` | 本面新测 |
| `D-08-B` Workflow `purpose_key` 实际使用 | 全部图 = `intake.ingest`；Literal 另含未用的 `intake.rebuild` | `lsrag_definition.py:619`；`builtin_scatter.py:357,576`；`models.py:315` | 本面新测 |
| `D-08-C` 非 ingest 意图选图 | `source_kind=None` → fallback `inline_payload` 单图 | `config_snapshots.py:138-144,492-501,474-489`；`workflow_registry.py:91-103` | 本面新测 |
| `D-08-D` 公开 retrieval filter key | `3`：`intake_item_uuid,source_kind,channel` | `retrieval/models.py:14` | 本面新测（对齐 `D-19`） |
| `D-08-E` scatter e2e `retrieval:search` 断言 | `0` | `rg retrieval:search tests/e2e/test_registered_api_scatter.py` 无命中 | 本面新测 |
| `D-08-F` publication `layer_b_keys_echo` | 硬编码 `["source_kind"]` | `src/runtime/intake/vector_publish_commit.py:119` | 本面新测 |
| `D-08-G` single/child 共享 `index.validate_publication` | 是 | `lsrag_definition.py:204-213,641`；`builtin_scatter.py:432-441,586` | 本面新测 |

### 2.2 轴 A · 尾链贯通（HEAD 核验）

- **正例：single 图已声明 structurize→construct→vectorize→validate_publication。** `_STEPS` 在 `src/workflows/lsrag_definition.py:169-214`；路由 `vectorize.to_validate_publication` / `validate_publication.to_succeeded` 在 `:425-439`。`construct` 注释明确 metadata refresh 可从 acceptance **直达** construct（`:184-188`）。
- **正例：system-owned g0=clean。** `overlay_system_g0` 丢掉模型 g0，插入唯一 `granularity=0` 且 `original_content.body=clean`（`src/runtime/intake/generation_assemble.py:17-62`）。对齐 `T-O-386` 方向；本面不重开 cuts。
- **正例：scatter child 复用同一 publication Process。** child 步骤 `validate_publication` / `index.validate_publication` / `publication_proof`（`builtin_scatter.py:432-441`）；`required_process_keys` 含该 key（`:581-586`）。parent fan-in 要求每个 succeeded required child **恰好一条** `mkb_publication_proofs` 且 Process `step_key='validate_publication'`（`src/runtime/workflow/runtime_scatter.py:436-471`）。
- **正例：publication 同事务写 proof + pointer，再调 S04 serving CAS。** `_publish` 把 records 从 `withdrawn` 标 `indexed`、插入 `mkb_publication_proofs`、CAS `mkb_index_active_pointers`（`active_index_generation <` 新代），然后 `IntakePublicationCommand`（`vector_publish_commit.py:57-191`）。`publish_revision_tx` 再 CAS `serving_revision_uuid`（`lifecycle_publish.py:118-129`），并校验 proof 计数与 pointer 一致（`:83-116`）。与 baseline `T-O-242`「S09 不直写 serving」的落地形态 = **publication Process 调用 S04 服务**，不是 S09 SQL 更新 Item。
- **正例：检索读 fence 不是 ANN 命中即可。** `_fetch_candidate_rows` 要求 `publication_state='indexed'`、pointer `lifecycle_state='active'`、proof 完整谓词、`item.lifecycle_state='active'`、`serving_revision_uuid=r.intake_revision_uuid`（`retrieval_rank.py:38-76`）；rank 后再 `_revalidate_publication_fence`（`:339-433`）。
- **反例：尾链存在 ≠ 四通道接通。** source capability e2e 在 acquire 证据层就超时停 `running`（`test_source_capability_paths.py:166-168`），且 monkeypatch fetcher（`:99-101`）。默认组合根未注入 browser/clean_llm（`D-21`）。`T-O-376` 明文：0815-R7 inline 4/4 **不算**四通道接通。
- **反例：API 路径到 `publication_ready` 仍无 retrieval 终验。** `test_registered_api_scatter.py:319-321` 断言 `all(item["publication_ready"])`；同文件 **无** `retrieval:search`。`publication_ready` 是 snapshot membership 上「存在 active pointer 指向该 revision 的 proof」投影（`task_projections.py:77-83,132`），**不是** query 命中。

### 2.3 轴 B · 七意图闭集与 applicability（不是 28 格笛卡尔积）

- **闭集已登记。** 公共合同 Literal 七值（`src/contracts/api/models.py:278-286`）；Task create frozenset 同集（`task_create.py:37-46`）；guard `registered_request_intent` 同集（`src/contracts/workflow/models.py:264-271`）。未知 ingest 意图 → `INTAKE_INTENT_UNSUPPORTED`（`acquisition_ingest.py:47-48`）。
- **ingest 是唯一带 `SourceDescriptor` 的意图。** 四 kind 判别器（`models.py:107-178`）。`registered_api` 由 registry 映射 scatter root（`workflow_registry.py:91-92`）；其余 kind/profile 走 single 家族（`:93-103`）。
- **非 ingest 不选 source kind。** `prepare()` 仅当 payload 是 `IntakeIngestPayload` 才读 `source_kind`（`config_snapshots.py:138-144`）。`_source_profile` 对非 ingest 返回 `None`（`:500-501`）。`_workflow_purpose` 对七意图一律返回 `"intake.ingest"`（`:474-489`）。因此 rebuild/metadata/lifecycle/index.rebuild **全部复用 canonical inline 骨架**，靠 start/acquire 上的 intent guard 短路（`lsrag_definition.py:233-298,647-676`）。
- **合法格（产品合同，非施工笛卡尔积）**：

| 意图 | 合法输入 | 与 source kind 的关系 | 产品终态（HEAD 已实现的形态） | 非法格（应 fail-loud，不是「以后再做」） |
|------|----------|------------------------|--------------------------------|------------------------------------------|
| `intake.ingest` | 四 kind `SourceDescriptor` | kind **选图**：3 张 single 家族 + scatter | 成员 Item accepted + publication proof + serving + **本应** `retrieval:search` 命中 | 第五 kind；caller `workflow_key`；无 source；把 lifecycle payload 当 ingest |
| `intake.rebuild` | `intake_item_uuid` + 可选 expected revision | kind 是 frozen Item 事实，**不是**选择器 | 不新获取外源；从 accepted clean 再生代；serving 指向同一/新 generation | 对 deleted Item；无 clean artifact；带 source descriptor；当新 ingest |
| `intake.update_metadata` | item + 至少一枚已登记 semantics | 同上 | fingerprint 不变 → `no_change` 短路 succeeded；变则新 Revision、**跳过 structurize**、reuse summaries 再 publication | 未登记 semantic key；对 deleted；把 metadata 当重 clean/重 acquire |
| `intake.deactivate` | item | 同上 | lifecycle=`deactivated`；serving/pointer/vectors **同事务 withdrawn**；检索空 | 对已 deleted；当作物理删索引即成功 |
| `intake.reactivate` | deactivated item | 同上 | lifecycle=`active` 但 `serving_revision_uuid=NULL`；pointer/vectors 仍 withdrawn；检索仍空，直到新 publish | 把 reactivate 当「立即可检索」；隐式恢复旧 generation |
| `intake.delete` | active\|deactivated item | 同上 | lifecycle=`deleted`；cleanup intent；之后 rebuild 冲突 | 对已 deleted 再 lifecycle；delete 当可恢复 tombstone |
| `index.rebuild` | `scope=team\|intake_item` | **不是** kind 轴；排除 inactive | 复制已校验 projection，新 `index_generation`，不造 Revision、不重读源 | 用 index.rebuild 复活 deactivated；按四 kind 各做一遍；当 ingest |

- **HEAD 已有 fail-loud 碎片，但没有「非法格台账」。** 例：deleted → `intake-item-deleted`（`targets.py:153-154`）；inactive index.rebuild → `index-rebuild-item-not-active`（`:107-110`）；未知 intent → 422。**没有**把「七意图 × 四 kind 必须全做」写成运行时矩阵——那是规划反例，不是代码义务。
- **scatter child 不是第七+1 意图。** 它是 `execution_role=SCATTER_CHILD`（`builtin_scatter.py:576-577`），调用方不可选 `workflow_key`。

### 2.4 轴 C · rebuild / metadata 是否重 clean

- **正例：rebuild 输入是 accepted clean Artifact，不是二次外源获取。** `_acquire_rebuild` 读 frozen clean text，`rebuild_input_evidence.input_kind="accepted_clean_artifact"`，注释禁止伪造 S05 外源 acquisition（`acquisition_intents.py:25-54,90-93`）。preflight 走 `_validate_rebuild_preflight_evidence`，注释禁止把它当新的 inline/local/HTTP acquisition（`clean_preflight.py:706-714,540-541`）。
- **正例：metadata no-change 不进 LS-RAG。** fingerprint 相等则 `operation_mode="metadata_no_change"`，acquire 经 `metadata_no_change` guard 直达 succeeded（`acquisition_intents.py:137-199`；`lsrag_definition.py:290-297`）。e2e 断言 revision 计数不变、transition=`no_change`（`tests/e2e/test_intake_rebuild_metadata.py:180-211`）。
- **正例：metadata 有变更则跳过 structurize，reuse 冻结 S06/S07 六件套。** 图上 `accept_snapshot.metadata_refresh` → construct（`lsrag_definition.py:339-347`）。`construct_mode="metadata_refresh"` / `reuse_summaries`（`acceptance_lifecycle.py:155-161`；`types.py:43-53`）。construct 从 frozen receipts 重建，不发现「最新」construction（`generation_construct.py:995-1002`；`acquisition_intents.py:241-247`）。
- **正例：`index.rebuild` 明确不重 clean / 不造 Revision。** `index_rebuild_plan.py:23-32`。e2e **调用** `retrieval:search`（`tests/e2e/test_index_rebuild.py:174-188`），但 body 缺 namespace，当前合同 **必 422**——不得当 hydrate 正例。
- **反例：rebuild / 有变更的 metadata **仍走** decode+clean Process。** acquire 成功后无 intent 短路则 `acquire.to_decode`（`lsrag_definition.py:299-306`）。`_decode` 对 `text/plain` 再 canonicalize（`acquisition_ingest.py:642-648`）。`_clean` **无** rebuild 短路，调用 `dispatch_clean` 并把 `state["clean_text"]=result.text`（`clean_preflight.py:28-127`）。非 ingest 选中的图是 **inline** 的 `clean.extract.deterministic`（`lsrag_definition.py:112-117,633`），策略 `doc.deterministic` 会对 plain text 做空白归一（`intake/doc/__init__.py:11-30`；`intake/text.py:96-99`）。因此：**输入是 exact clean 字节，过程却可能再跑一刀 deterministic clean，且不是原通道 strategy。** 这是「何时禁止重 clean」尚未闭包的 HEAD 事实。
- **未测：registered_api Item 的 rebuild/metadata。** e2e 仅 inline（`test_intake_rebuild_metadata.py`、`test_intake_reactivate.py`）。API Item 若走 inline 骨架，会把 mapped clean 再当 `text/plain` 喂 `clean.extract.deterministic`。

### 2.5 轴 D · lifecycle 与 serving pointer（single 与 scatter 是否同一套 publication proof）

- **同一套 proof 表 + pointer 表。** DDL `mkb_publication_proofs` / `mkb_index_active_pointers`（`001_initial.sql:1532-1606`）。single `_publish` 与 scatter child 同 Process key。`publication_ready` SQL 不区分 single/scatter（`task_projections.py:77-83`）。
- **差别在 fan-in，不在 proof schema。** scatter parent 额外要求每个 required child 恰好一条 proof 且 `publication_proof_ref` 匹配（`runtime_scatter.py:436-471`）。child construct **没有** single 上那条 optional `accepted_intake_revision`（对比 `lsrag_definition.py:190-194` vs `builtin_scatter.py:416-422`），故 metadata refresh **不能**跑在 child 图上——API Item 的 metadata/rebuild 被设计成事后走 inline 骨架。
- **deactivate / delete 同事务撤 serving + pointer + vectors。** `lifecycle_apply.py:34-40,108-134`。unit：deactivate 幂等、pointer=`withdrawn`、vector=`withdrawn`（`tests/unit/test_intake_lifecycle.py:161-212`）。
- **reactivate 只恢复 lifecycle 真值，不恢复 serving。** 注释与断言（`lifecycle_apply.py:36-38`；unit `:237-298`）。e2e **意图**证明 deactivate 后 search 空、reactivate 后仍空、rebuild 后再命中（`tests/e2e/test_intake_reactivate.py:102-112,153-215`），但 search POST **无** namespace，当前 **必 422**——生命周期 CAS 的 unit 正例仍成立；**检索终验不是 HEAD 绿件**。这仍支持「Task succeeded ≠ 可检索」，但不得把该 e2e 标成 retrieval 正例。
- **delete 禁止 rebuild。** unit（`test_intake_lifecycle.py:352-383`）。**无** delete 的 default-root e2e + `retrieval:search` 排除证明。
- **exhausted-zero。** scatter 空 records 父 Task `succeeded`、counts 全 0、items `[]`（`test_registered_api_scatter.py:352-373`）。产品终态是「无成员成功」还是「可检索空集」，交 `G-NH-08`，本面只 MARK。

### 2.6 轴 E · 「可检索」必须含哪些 proof / query / facet

HEAD 已实现的 **最小读谓词**（`retrieval_rank.py:38-76` + `_PROOF_COMPLETE_SET_PREDICATE` in `retrieval/models.py:59-75`）要求：

1. vector row：`deleted_at IS NULL` ∧ `publication_state='indexed'` ∧ generation=active pointer；
2. namespace active 且 Layer A 四元组匹配；
3. durable `mkb_publication_proofs`：`proof_type='index.publication.v1'`、计数三元组相等、complete-set 子查询；
4. S04：`item.lifecycle_state='active'` ∧ `serving_revision_uuid` 非空且等于 record revision。

**仍不足称为 `T-O-376` 产品终态**，因为：

- 必须再有一次真实 `POST /v1/teams/{team}/retrieval:search` **带** `namespace_key` 或 `namespace_uuid` 且命中 `payload_content`。HEAD 现有 single/rebuild/reactivate/index.rebuild e2e **有调用、无 namespace**，当前 **必 422**（`models.py:505-509`；`retrieval_request.py:265-269`；`rg namespace_key tests/e2e` = 0；README K1）。API scatter **连调用都没有**。调用 ≠ 命中，与 scatter 无 search **同类缺口**；
- FilterMeta 五维 facet 公开面为 0（`D-19`）；filter `channel` 是向量 original/summary，与业务 `FilterMeta.channel` 撞名（面 07 / `G-NH-06`）；
- publication 只 echo `source_kind`（`vector_publish_commit.py:119`）；
- 非 API 五维写入为 stub（`D-18`，`acceptance_snapshot.py:598-599`）——面 07 拥有权威，本面消费：缺五维不得 pretend publication-complete（`T-O-389`）；
- monkeypatch / 503 / 空 `clean_text` / Task succeeded / `publication_ready` **均不得**当 DoD（`T-O-376/378`）。

### 2.7 与仓内 baseline 的冲突登记

| 叙事 / 旧 Truth | HEAD 实测 | 类型 | 证据 |
|-----------------|-----------|------|------|
| `T-O-242`：S09 不写 `serving_revision` | publication Process **调用** S04 `publish_revision_tx` 同 UoW 写 serving | 落地形态差异，权属仍在 S04 服务 | `vector_publish_commit.py:168-191`；`lifecycle_publish.py:118-129` |
| initial/index 预核查「测试未 retrieval query」 | **仍成立（合同漂移）**：上述 e2e **有** search 调用但 **无** namespace，当前必 422；API scatter 仍无 search。不得修正为「inline 已做」 | 高估检索终验 | `test_single_intake_pipeline.py:121-130`；`models.py:505-509`；README `:610` |
| 「七意图 × 四通道必须全做」 | 六意图按 Item 寻址，不是 kind 矩阵 | 规划反例 | `models.py:210-248`；`config_snapshots.py:138-144` |
| 0815-R7 inline 4/4 = 四通道接通 | `T-O-376` 禁止 | 高估 | QNA `:80` |

---

## 3. 借鉴锚定矩阵（Reference Anchor Matrix）★ `[核心]`

> 每个可借鉴点钉到 `path:line` / URL，给**借鉴 verdict**。这是「能借什么」的台账，不是设计决策。

| 借鉴点 | 来源锚（`path:line` / URL） | 借鉴 verdict | 借什么 / 不借什么 |
|--------|------------------------------|--------------|--------------------|
| single 尾链含显式 `validate_publication` | `src/workflows/lsrag_definition.py:196-214,425-439` | `✅借`（本仓已有） | 借：publication 是图内一步 + proof_kind。不借：重写 tail/g0。命中 `RA-08-HEAD-01` |
| system g0=clean | `generation_assemble.py:17-62` | `✅借` | 借：g0 original=admitted clean。不借：把 FilterMeta 塞进 g0。`RA-08-HEAD-02` |
| scatter child 同一 publication Process | `builtin_scatter.py:432-441,571-586`；`runtime_scatter.py:436-471` | `✅借` | 借：single/scatter **同一 proof schema**。不借：用 parent Task succeeded 代替 child proof。`RA-08-HEAD-03` |
| pointer CAS + serving CAS | `vector_publish_commit.py:123-191`；`lifecycle_publish.py:69-129` | `✅借` | 借：generation 单调 CAS；proof 不完整不得 serving。不借：ANN 命中当 publication。`RA-08-HEAD-04` |
| rebuild 从 accepted clean 起跳 | `acquisition_intents.py:25-84`；`clean_preflight.py:706-714` | `🔶部分借` | 借：禁止重 acquire。不把「仍走 decode+clean」当成已冻结的 exact-clean 合同。`RA-08-HEAD-05` |
| metadata 直达 construct / no-change 短路 | `lsrag_definition.py:339-347,290-297`；`acceptance_lifecycle.py:155-161` | `✅借` | 借：跳过 structurize；no-change 不造 Revision。`RA-08-HEAD-06` |
| deactivate 同事务撤 serving | `lifecycle_apply.py:108-134`；`test_intake_lifecycle.py:161-212` | `✅借` | 借：lifecycle 与 index 投影同 UoW withdrawn。`RA-08-HEAD-07` |
| reactivate 不恢复 serving；search 为空直到 rebuild | `test_intake_reactivate.py:166-215` | `✅借` | 借：Task succeeded ≠ 可检索 的活体证明。`RA-08-HEAD-08` |
| 检索 dual-fence | `retrieval_rank.py:38-76,339-421` | `✅借` | 借：publication-valid 谓词 + 再校验。不借：只测 fixture ANN。`RA-08-HEAD-09` |
| 七意图闭集 | `api/models.py:278-286`；`workflow/models.py:264-271` | `✅借` | 借：闭集 + unknown 422。不借：28 格全做。`RA-08-HEAD-10` |
| source capability 红 / monkeypatch | `test_source_capability_paths.py:59,99-101,166-168` | `⛔反例` | 避开：monkeypatch 冒充接线；8s 内停 running 当绿。`RA-08-HEAD-11` |
| scatter 无 retrieval:search | `test_registered_api_scatter.py:209-321` | `⛔反例` | 避开：`publication_ready` 当 DoD。`RA-08-HEAD-12` |
| rebuild 再跑 deterministic clean | `clean_preflight.py:28-127`；`lsrag_definition.py:299-306,112-117` | `⛔反例`（相对 exact-clean 目标） | 避开：把「输入是 clean 字节」说成「未重 clean」。`RA-08-HEAD-13` |
| layer_b 仅 `source_kind` | `vector_publish_commit.py:119`；`D-19` | `⛔反例`（相对 `T-O-389` 终态） | 避开：source_kind blob 冒充五维 facet。`RA-08-HEAD-14` |
| exhausted-zero 父 succeeded | `test_registered_api_scatter.py:352-364` | `🔶部分借` | 借：空集可 terminal。不把该 terminal 叫「可检索成功」。`RA-08-HEAD-15` |
| 非 ingest 一律 inline 骨架 | `config_snapshots.py:474-489`；`workflow_registry.py:95-103` | `🔶部分借` | 借：一套 tail。风险：API Item rebuild 错绑 deterministic clean。`RA-08-HEAD-16` |
| clean finalizer 以 R2 key / output_payload 推 `clean_completed` | `context/legacy-family/smind-clean-dispatcher/flows/finalizer.ts:105-129,209-221` | `⛔反例` | 不借：R2 key 当成功；hydration_hint 当 proof。可借：clean 完成后有 **显式** 下游 handoff。`RA-08-LEGACY-01` |
| differ：content **或** meta hash 变 → purge+RAG；双 hash 同且非 force → `no_update` | `smind-clean-dispatcher/services/differ.ts:110-186`（content `:129-141`；meta `:144-156`；双同 `:174-186`） | `🔶部分借` | 借：差分意图（正文或 meta 变都 purge）。不借：`action_branch` / SMCP `case_mode` / 随机 UUID child。`RA-08-LEGACY-02` |
| RAG finalizer：`output_payload` 并入 artifacts，`file_status='ready'` | `smind-rag-dispatcher/flows/finalizer.ts:66-104` | `⛔反例` | 不借：output payload 当 publication proof；无 retrieval query。`RA-08-LEGACY-03` |
| vectorizer 单绑定 `VECTORIZE_INDEX.upsert`；purge 尽力而为且 summary_channel_only 退化为全量 | `smind-skill-rag-vectorizer/core/vector_db.ts:48-73`；`src/purger_logic.ts:79-122,144-147` | `⛔反例` | 不借：无 alias/generation pointer；catch 后继续；单 Index 原地 upsert。可借：**purge 应使旧向量不可检索** 这一意图。`RA-08-LEGACY-04` |
| constructor/vectorizer success = `workflow_step_status='COMPLETED'` + 队列回调 | `smind-skill-rag-constructor/services/callbacker.ts:54-88`；`smind-skill-rag-vectorizer/src/callbacker.ts:47-92` | `⛔反例` | 不借：COMPLETED / output_payload 当 proof。`RA-08-LEGACY-05` |
| ES aliases 多 action 原子 swap；期间别名不双指 | https://www.elastic.co/docs/manage-data/data-store/aliases （访问 2026-08-29） | `🔶部分借` | 借：serving 指针原子切代。不借：ES `_aliases` API、多 index 别名、filter alias。限制：部分 action 失败仍 `acknowledged:true`+`errors:true`，须 `must_exist` 才整批失败。`RA-08-WEB-01` |
| OpenSearch Manage Aliases：原子 rename；一 alias 仅一 write index；无 write index 则拒写 | https://docs.opensearch.org/latest/api-reference/alias/aliases-api/ （访问 2026-08-29） | `🔶部分借` | 借：单写指针；切 write index 须原子。不借：OpenSearch 引擎、wildcard 即时别名。`RA-08-WEB-02` |
| Lucene/ES NRT：refresh 打开新 segment，**不是** commit；默认约 1s 内可见 | https://www.elastic.co/docs/manage-data/data-store/near-real-time-search （访问 2026-08-29） | `⛔反例`（对 MKB 读模型） | 不借：把「写入成功」当「立即可检索」或引入 refresh 间隔。MKB 读的是已提交 SQL fence。`RA-08-WEB-03` |
| Lucene soft-deletes：有值即视为删；**无 undelete API**，恢复必须 `softUpdateDocument` 重索引 | https://lucene.apache.org/core/10_4_0/core/org/apache/lucene/index/IndexWriterConfig.html `setSoftDeletesField`（Lucene 10.4.0，2026-02-26；访问 2026-08-29）。9.1.0 同句仍成立 | `🔶部分借` | 借：soft-delete ≠ 立即物理删；undelete 必须重发布。不借：liveDocs 位图、Lucene 引擎。映射 HEAD reactivate。`RA-08-WEB-04` |
| ES OCC：`if_seq_no`/`if_primary_term`；旧序列号不得覆盖新版本 | https://www.elastic.co/docs/reference/elasticsearch/rest-apis/optimistic-concurrency-control （访问 2026-08-29） | `🔶部分借` | 借：CAS 世代。不借：ES seqno 协议。映射 `row_revision` / `pointer_row_revision`。限制：无 seqno 的索引拒绝 OCC 参数。`RA-08-WEB-05` |
| S09 PublicationProof + ActiveIndexPointer 分账 | `docs/baseline/qna-truth/S09.md`（`T-O-242/243/244`）；`spec-index.md:498` | `✅借`（仓内） | 借：存在≠serving；禁仅 ANN。冲突见 §2.7。`RA-08-BASELINE-01` |

每条 `RA-*` 原子句与命中缺口：

| RA-ID | 正/反 | 置信 | 命中缺口 |
|-------|------|------|----------|
| `RA-08-HEAD-01..10` | 正（05 为部分） | HEAD 实测 | 支撑 `NH-RA08-B01..B04` 的已有 substrate，禁止重做 tail |
| `RA-08-HEAD-11` | 反 | HEAD 实测 + pytest | `NH-RA08-B01` |
| `RA-08-HEAD-12` | 反 | HEAD 实测 | `NH-RA08-B02` |
| `RA-08-HEAD-13` | 反 | HEAD 实测 | `NH-RA08-B04` |
| `RA-08-HEAD-14` | 反 | HEAD 实测 | `NH-RA08-B03` |
| `RA-08-HEAD-15` | 部分/反于可检索 DoD | HEAD 实测 | `NH-RA08-B06` / `G-NH-08` |
| `RA-08-HEAD-16` | 部分 | HEAD 实测 | `NH-RA08-B05` / `NH-RA08-B07` |
| `RA-08-LEGACY-01..05` | 01/03/04/05 反；02 部分 | 仓内只读 | 不借 R2/payload；借显式 publication 与 no-change |
| `RA-08-WEB-01..05` | 01/02/04/05 部分；03 反 | primary 2026-08-29 | 映射 pointer CAS / 禁 NRT 假绿 |
| `RA-08-BASELINE-01` | 正 | 仓内 frozen S09 | 与 HEAD 同 UoW 调用 S04 的形态差异见 §2.7 |

---

## 4. 缺口 / 断点台账 ★ `[核心]`

> 本面核心产出：缺什么、断在哪、多严重、证据何在。**编号稳定，供下游引用。**

| 编号 | 缺口 / 断点 | 严重度 | 证据（`path:line`） | 影响 |
|------|-------------|--------|----------------------|------|
| `NH-RA08-B01` | 四通道真实 Process→可检索向量未接通；source capability e2e 红；monkeypatch 冒充接线 | `S1` | `test_source_capability_paths.py:99-101,166-168`；`D-21`；`D-24`；`T-O-376/378/381` | 战役 completeness 不成立；0815-R7 不能顶替 |
| `NH-RA08-B02` | API scatter 无 `retrieval:search` 终验；inline 等 e2e 有调用但缺 namespace **必 422**；`publication_ready` / Task succeeded 被当成可检索 | `S1` | `test_registered_api_scatter.py:209-321`（无 search）；`test_single_intake_pipeline.py:121-130`（无 namespace）；`models.py:505-509` | 三 provider 绿灯假绿；inline 检索也不是正例（同类缺口） |
| `NH-RA08-B03` | 「可检索」缺 FilterMeta facet / 五维投影；layer_b 仅 `source_kind` | `S1` | `retrieval/models.py:14`；`vector_publish_commit.py:119`；`acceptance_snapshot.py:589-615`；`D-18/D-19`；`T-O-389` | 四通道过滤面不同构；面 07 权威无法被 publication/retrieval 消费 |
| `NH-RA08-B04` | rebuild/metadata 仍走 decode+`clean.extract.deterministic`，exact-clean 合同未闭 | `S1` | `clean_preflight.py:28-127,540-541`；`lsrag_definition.py:299-306,112-117`；`intake/text.py:96-99` | 可能改写 admitted clean / 换 strategy；违反「禁止重 clean」产品问题（见本面 `G-NH-19`；与面 02 `G-NH-12` Task restart 继承 **分号**，禁止共用） |
| `NH-RA08-B05` | 七意图非法格未形成稳定 fail-loud 台账；非 ingest 一律 inline 骨架 | `S2` | `config_snapshots.py:138-144,474-489`；`workflow_registry.py:95-103` | 规划易滑向 28 格；API Item rebuild 错绑 clean 能力 |
| `NH-RA08-B06` | exhausted-zero 父 Task `succeeded` 且无检索命中；终态未裁 | `S2` | `test_registered_api_scatter.py:352-373` | 指标/DoD 歧义；消费 `G-NH-08` |
| `NH-RA08-B07` | registered_api Item 的 rebuild / metadata / lifecycle / index.rebuild **无 e2e** | `S2` | `rg` 仅 inline：`test_intake_rebuild_metadata.py`、`test_intake_reactivate.py` | scatter 与 lifecycle 两套图的衔接未证明 |
| `NH-RA08-B08` | `intake.delete` 无 default-root e2e + retrieval 排除；仅 unit | `S2` | `test_intake_lifecycle.py:352-383`；e2e 目录无 delete search | 硬删/tombstone 可见性未在产品面封口 |
| `NH-RA08-B09` | `WorkflowDefinition.purpose_key` Literal 含未使用的 `intake.rebuild` | `S3` | `models.py:315` vs 所有 builtin `purpose_key="intake.ingest"` | 文档/类型误导；不阻断 |
| `NH-RA08-B10` | 默认检索 filter `channel` 与 FilterMeta `channel` 撞名 | `S2` | `retrieval/models.py:14`；`retrieval_request.py:354-355`；`T-O-389` | 跨面；权威在 `G-NH-06` / 面 07；本面 retrieval 终验会被它污染 |

跨面不变量草案号段 `NH-C-70..79` 见 §5.2。净新缝 `NH-N-08-*` 见 §6。

---

## 5. 跨功能系统一致性 ★ `[核心]`

- **5.1 整体形态一句话**：四通道在 **同一套** `index.validate_publication` → `mkb_publication_proofs` + `mkb_index_active_pointers` + S04 `serving_revision` 上发布；七意图是 **Item/scope 动词闭集**，不是 kind 矩阵；可检索 = 该指针谓词 **加上** 一次真实 `retrieval:search`（及未来 FilterMeta facet）。
- **5.2 功能间一致性契约（不变量 `NH-C-70..79`）**：

| 编号 | 不变量 | 跨哪些面/模块 | 违反后果 |
|------|--------|----------------|----------|
| `NH-C-70` | 可检索 ⇒ publication_proof 完整 ∧ pointer active ∧ serving=revision ∧ `retrieval:search` 命中正文 | `08` 拥有；`04` 供 admitted clean；`07` 供语义；`09` 供 replay | Task 绿、检索空或脏 |
| `NH-C-71` | Task succeeded / `publication_ready` / 503 / 空 clean / monkeypatch **不是**可检索 | `08/09` | 假绿（`T-O-376/378`） |
| `NH-C-72` | `intake.rebuild` / 有变更 metadata **禁止重 acquire 外源**；是否重跑 clean Process 见 `G-NH-19` | `08` 拥有；`03/04` 供 representation/clean | 外源漂移进 rebuild |
| `NH-C-73` | deactivate/delete 与 pointer/vector withdrawn **同一关系 UoW** | `08`；S04/S09 | 检索仍打到已停 Item |
| `NH-C-74` | reactivate **不得**恢复 `serving_revision` 或把旧 generation 标 active | `08` | 未审核旧向量复活 |
| `NH-C-75` | single 与 scatter child 共用同一 publication proof/pointer schema；差别只在 fan-in | `08/01/04` | 两套「已索引」定义 |
| `NH-C-76` | g0 original = `T-O-386` admitted clean；FilterMeta 永不进 g0 | `08` 消费；`07/04` 拥有输入 | 过滤维污染正文 |
| `NH-C-77` | 七意图闭集；非法格 fail-loud；禁止 28 格施工矩阵 | `08`；`01` 图；`09` 证明 | 范围爆炸 / 静默 skip |
| `NH-C-78` | `index.rebuild` 不造 IntakeRevision、不重读源、不切换 Layer A；只 CAS 新 generation | `08` | 用 rebuild 当 ingest/reactivate |
| `NH-C-79` | 读路径必须应用 S09 publication-valid 谓词后再 S04 eligibility；禁仅 ANN | `08/07/09`；baseline `T-O-244` | 旧代/已撤向量漏出 |

- **5.3 数据 / 控制流贯穿图**：

```text
ingest(kind) ─┬─ single: acquire→decode→clean→seal→preflight→accept
              │         ├─ [metadata_refresh guard] → construct (reuse S06/S07)
              │         └─ structurize→construct→vectorize→validate_publication
              │                    → proof + pointer CAS → S04 serving CAS
              └─ registered_api: scatter_root map/seal/accept
                                 → child: structurize→…→validate_publication
                                 → parent fan-in 要求每 required child 一条 proof

rebuild/update_metadata/lifecycle/index.rebuild
  → purpose 仍 intake.ingest，选 inline 骨架
  → start/acquire guards 短路：index.rebuild | deactivate | reactivate | delete | metadata_no_change
  → 否则 decode+clean（B04）→ accept_rebuild / accept_metadata → 同一 tail

retrieval:search
  → SQL: indexed ∧ pointer.active ∧ proof complete ∧ item.active ∧ serving=revision
  → 再校验 fence → pack（v1 context-only）
  → 今日 filters: item | source_kind | vector channel     ← 非 FilterMeta
```

- **5.4 与相邻面的消费 / 提供**（index §1.2）：
  - **消费面 04**：admitted clean body + evidence；本面不得重写 clean 变换。
  - **消费面 07**：五维 / context tags / facet 命名；本面不从 g0 猜五维。
  - **提供给面 09**：可检索 proof 层级、fake-green 清单、zero/fan-in/lifecycle CAS 窗口。
  - **不拥有**：upload（06）、runtime 注入（05）、graph merge（01）、actual S05（02）。

---

## 6. 净新契约 / 架构边界草案 `[核心]`

> 无先例可借（§3 标 🆕 或本仓仅有半截）处，从零草拟。**草案，非冻结。**

- **6.1 净新聚合 / 解耦点**：
  | 缝 | 为什么净新 | 草案落点 |
  |----|------------|----------|
  | `NH-N-08-01` 可检索 mega-proof | 外部引擎用 alias/refresh/ANN；本仓用 SQL dual-fence + 必须 query | §9 `NH-A-08-01` |
  | `NH-N-08-02` 七意图 applicability 闭集表 | 行业无「7 intent × 4 kind」先例；非法格是产品法不是笛卡尔积 | `G-NH-17`；§2.3 表 |
  | `NH-N-08-03` exact-clean replay 合同 | legacy 是再 purge+rewrite；HEAD 半截（输入 clean、过程仍 clean） | `G-NH-19` |
  | `NH-N-08-04` scatter 与 single 共用 proof 的 **检索** 终验 | child proof 已有；query 未接 | `NH-RA08-B02` |
- **6.2 净新契约叙述规格**（草案）：
  - **可检索（候选）**：给定 `team_uuid` + 查询串，`retrieval:search` 返回 `disposition=ok` 且至少一条 hit：`payload_content` 等于 admitted clean（或声明的 summary 通道）；hit 携带 `publication_proof_uuid`；item 处于 active+serving；**不得**返回 deactivated/deleted/withdrawn/旧 `index_generation`。FilterMeta facet 的键集由面 07 / `G-NH-05/06` 裁完后并入，本面不发明第五 filter。
  - **rebuild 输入（候选）**：command 只绑定 `intake_item_uuid` + frozen clean artifact digest；禁止 URL/handle/records 再获取。clean Process 是否 no-op / skip 由 `G-NH-19` 裁。
  - **非法格（候选）**：非 ingest 请求若带 `source` descriptor → schema 422；ingest 若带 lifecycle payload → 422；index.rebuild 对 inactive → 已有 409；对 28 格中「kind 选择器 × 生命周期动词」的组合 **不得**生成任务。
- **6.3 架构边界（与既有 / 相邻面）**：不新增搜索引擎；不引入 ES alias 物理实现；不把 `purpose_key=intake.rebuild` 自动冻成第二张图（Literal 已存在但是未用，是否启用只 MARK）；不重开 cuts。

---

## 7. Substrate-fit / 技术路线过滤 ★ `[核心]`

> **核心防线**：把每个「借来的机制」按本仓技术路线降级或重映射。

| 借鉴点 | 原机制（参考处） | 是否冲突本仓路线 / 约束 | 落地形态（降级 / 重映射 / 直采） |
|--------|------------------|--------------------------|-----------------------------------|
| ES/OS 原子 alias swap | Elastic Aliases；OpenSearch Manage Aliases | 冲突：云搜索集群、多 index 别名、filter alias | **重映射**为 `mkb_index_active_pointers` 行 CAS（已有）。不引入引擎 |
| OS/ES write index | 一 alias 仅一写索引，否则拒写 | 不冲突意图；冲突实现 | **重映射**为 `serving_revision_uuid` + pointer `lifecycle_state='active'` |
| Lucene/ES refresh / NRT | 打开新 segment，默认 ~1s 可见；refresh≠commit | 冲突：MKB 检索走已提交 SQL，不允许「近实时窗口」冒充 proof | **不采** refresh 间隔。写入成功必须过 publication UoW 才可见 |
| Lucene soft-delete | liveDocs / doc-values 软删；无 undelete | 部分：与 HEAD withdrawn 同类；undelete=重索引 对齐 reactivate | **重映射** `publication_state='withdrawn'` + 空 serving；禁止借 liveDocs |
| ES OCC seqno | `if_seq_no`/`if_primary_term` | 部分：分布式序列号 vs 本地 row_revision | **重映射** Item `row_revision`、pointer `pointer_row_revision` |
| legacy R2 key / COMPLETED payload | finalizer.ts；callbacker.ts | 冲突：CF/R2/SMCP/`T-O-42` | **反例**。proof 必须是 `mkb_publication_proofs` 行 |
| legacy 单 Index upsert | `VECTORIZE_INDEX.upsert` | 冲突：无 generation pointer | **反例**。必须新 `index_generation` + CAS |
| legacy purge_before_write | differ.ts | 部分：内容变才重写 | **重映射**为新 generation + 旧代 retirement；禁止尽力而为 catch |
| legacy no_update | differ.ts hashes match | 对齐 metadata_no_change | **直采意图**，不采 SMCP case_mode |
| HEAD 已有 publication step | lsrag/scatter 图 | 符合单体 FastAPI + Turso + 七表 | **直采**；勿重做 |

能跑但越界（CF Vectorize、R2、refresh API）→ 最多 `🔶部分借`。

---

## 8. 反例坑表 + 净新表 `[核心]`

### 8.1 反例坑表 ⛔

| 反例 | 来源锚 | 为什么不可借 |
|------|--------|--------------|
| R2 key / `cleaned_content_r2_key` 当 clean 成功 | `finalizer.ts:116-129` | 对象存在 ≠ admitted clean ≠ 可检索；违反 S13/S04 分账 |
| `output_payload` 合并进 artifacts 后 `file_status='ready'` | `rag-dispatcher/finalizer.ts:91-102` | 无 PublicationProof、无 pointer CAS、无 query |
| `workflow_step_status='COMPLETED'` 队列回调 | constructor/vectorizer callbacker | 回调成功 ≠ required-set 对账 |
| 单 `VECTORIZE_INDEX` 原地 upsert | `vector_db.ts:68-73` | 无代、旧向量可与新向量并存被搜到 |
| purge catch 后继续；`summary_channel_only` 退化为全量 | `purger_logic.ts:79-122` | 静默部分失败；违反 fail-loud |
| monkeypatch fetcher 冒充四通道 | `test_source_capability_paths.py:99-101` | `T-O-378` |
| `publication_ready` 或 Task succeeded 当可检索 | scatter e2e `:321`；zero `:354` | `T-O-376` |
| 28 格笛卡尔积施工 | 规划叙事 | 六意图不是 kind 选择器 |
| ES refresh 可见性窗口 | Elastic NRT 文档 | 把未 fence 的写入当成已发布 |
| 用 Lucene undelete | `setSoftDeletesField` javadoc：无 undelete API | 恢复必须重发布；对齐 HEAD reactivate，不要发明「翻回 liveDocs」 |

### 8.2 净新表 🆕

| 项 | 为什么无先例 | 草案落点 |
|----|--------------|----------|
| 七意图 × 四 kind 的 **合法/非法格** 产品表 | 搜索引擎只有 alias/lifecycle，没有 MKB 这套 Task intent 闭集 | `NH-N-08-02`；`G-NH-17` |
| SQL dual-fence + 强制 `retrieval:search` + FilterMeta facet 的 mega DoD | ES 用 alias+refresh；legacy 用 ready 状态 | `NH-N-08-01`；§9 |
| rebuild exact-clean：输入冻结、是否 skip clean Process | legacy 总是 purge+rewrite；HEAD 半截 | `NH-N-08-03`；`G-NH-19` |
| scatter child 与 inline Item 共用 proof 后的 **API 检索** 终验 | 无外部「scatter fan-in + SQL pointer」样板 | `NH-N-08-04` |

---

## 9. 验收格栅草案（防假绿）`[核心]`

> 草案——落地验收归下游执行计划，此处先封堵 fake-green。测试层：`单元 / 集成 / default-root e2e / retrieval-facet mega`。

| 功能 F | 收口目标（一句话可验证） | Test-ID（拟） | 测试层 | 防假绿要点 |
|--------|--------------------------|----------------|--------|------------|
| 四通道 ingest 可检索 | 每条 in-scope 路径真实文件/records → `retrieval:search` 命中 admitted clean | `NH-A-08-01` | default-root e2e + retrieval-facet mega | 禁 monkeypatch browser/http；禁 503 DoD；禁空 clean；0815-R7 不算 |
| API scatter 可检索 | 三 operation 各至少一 member：`publication_ready` **且** search 命中 member 正文 | `NH-A-08-02` | default-root e2e + retrieval | 现有 `:209-321` 不够；必须 POST `retrieval:search` |
| exhausted-zero | 空 collection 的 terminal 与检索空集分账（成功/no-change/失败由 `G-NH-08` 裁后测） | `NH-A-08-03` | 集成 + retrieval | 父 succeeded 不得写成「已索引」 |
| rebuild exact-clean | rebuild 后 search 正文 = **原** admitted clean digest；无新外源 acquire 行 | `NH-A-08-04` | 集成 + retrieval | 断言未调用 http/browser；clean Process skip/no-op 随 `G-NH-19` |
| metadata no-change | 无新 Revision、generation 不变、search 仍命中 | `NH-A-08-05` | e2e（已有雏形） | 不得为凑 Task 成功而跑 tail |
| metadata 变更 | 新 Revision、跳过 structurize、search 命中且语义变更可见（facet 随面 07） | `NH-A-08-06` | e2e + retrieval-facet mega | 不得重跑 promptB |
| deactivate | Task succeeded ∧ search `results==[]` ∧ serving NULL ∧ pointer withdrawn | `NH-A-08-07` | 单元已有 + e2e | 不得只查 lifecycle 列 |
| reactivate | Task succeeded ∧ search 仍空 ∧ serving 仍 NULL；须再建 publish 才命中 | `NH-A-08-08` | e2e 已有 inline；缺 API Item | 不得把 reactivate 当 cutover |
| delete | rebuild 409；search 空；tombstone 不翻回 | `NH-A-08-09` | 单元已有；缺 e2e | 不得只测 cleanup intent 存在 |
| index.rebuild | 新 generation；search 仍命中同一正文；未造 Revision | `NH-A-08-10` | e2e 已有 inline | 不得只比 pointer 整数 |
| 非法格 | 非 ingest+source、第五 kind、inactive index.rebuild 等 422/409 | `NH-A-08-11` | 单元/集成 | 不得 skip |
| FilterMeta facet | 公开 filter 能按面 07 裁定的键排除/命中（本面只消费） | `NH-A-08-12` | retrieval-facet mega | 今日 `D-19=0` 不得用 `source_kind` 冒充 |
| stale generation | pointer 切代后旧 `index_generation` 不得出现在 search | `NH-A-08-13` | 集成 | 对齐 WEB NRT 反例：可见性=fence 而非 refresh |

---

## 10. 优先级建造建议 + owner-gate 候选 `[核心]`

- **10.1 建造顺序（依赖序，分批不一次性深做）**：

| 顺序 | 工作簇 | 依赖 | 复用判定 |
|------|--------|------|----------|
| `P0-a` | 钉可检索 mega-proof 合同（query+proof+pointer+serving） | 面 07 facet 键未裁前先测无 facet 的 query | `✅复用` 检索 fence；`🆕` mega DoD |
| `P0-b` | API scatter 补 `retrieval:search`（三 operation） | `P0-a`；沿用 scatter 图 | `✅复用` child publication |
| `P0-c` | 四通道 default-root 接通（禁 monkeypatch） | 面 03/04/05 live runtime；`D-21` | `♻️重 substrate` 接线，不重 tail |
| `P1-a` | rebuild/metadata exact-clean 合同（是否 skip clean） | `G-NH-19`；面 04 | `♻️重 substrate` 图已有，handler 短路未有 |
| `P1-b` | 七意图非法格 fail-loud 表 + API Item lifecycle e2e | `G-NH-17` | `✅复用` CAS；`🆕` 矩阵文档 |
| `P1-c` | delete e2e + stale generation 排除 | `P0-a` | `✅复用` unit |
| `P2` | FilterMeta facet 终验 | 面 07 / `G-NH-05/06` | 本面只接检索，不拥有权威 |

- **10.2 owner-gate 候选（只 MARK 不裁决 → 上交 index §4 / 下游决策登记）**：

| gate-ID | 决策点 | 候选选项（不预设倾向） | 影响 |
|---------|--------|------------------------|------|
| `G-NH-05` | 非 API 五维权威来源与 unknown 法 | `caller required / kind-closed derivation / caller+derivation merge`；另裁 `unknown` | 无五维则 publication 不得 pretend complete（本面消费） |
| `G-NH-06` | FilterMeta `channel` 与向量 `channel` 公共命名 | `semantic_channel / source_channel / 重命名 vector channel / 其他无歧义方案` | `NH-A-08-12` 无法在撞名下诚实落地 |
| `G-NH-08` | exhausted-zero registered API 终态 | `typed no-op success / distinct no-change terminal / explicit empty failure` | zero e2e 今日 `succeeded`+空 items |
| `G-NH-17` | 七意图 applicability **非法格** 是否要专用 fail-loud 码/表 | `仅现有 schema 422/409 / 增补稳定错误码与测试矩阵 / 其他经证据支持方案` | `NH-RA08-B05`；防止 28 格回流 |
| `G-NH-19` | rebuild / 有变更 metadata 是否禁止再执行 clean Process | `跳过 decode+clean、只 replay frozen clean digest / 允许 idempotent deterministic no-op 但必须 byte-equal / 其他经证据支持方案` | `NH-RA08-B04`；API Item 错绑风险 |

本面 **不**重开 cuts，不裁 `G-NH-01..04,07,09,10`。新增 `G-NH-17/19` 只 MARK、无推荐赢家；index §4 v0.2 已登记二者（仍不裁决）。`G-NH-11/12` 留给面 02（seal 事务 / restart 继承）。

---

## 11. 核验记录 `[核心]`

> 对抗性自检：本文每个关键锚点是否真核验过；与任何叙事/记忆冲突处以实测为准并标「修正」。

| 锚点（host-ID） | 是否核验 | 方式（grep/read/run） | 备注 / 修正 |
|------------------|----------|------------------------|--------------|
| HEAD `1221aa1` | `✅` | `git rev-parse --short HEAD` | 与 index §2.2 一致 |
| `RA-08-HEAD-01` 尾链 | `✅` | read `lsrag_definition.py:161-214,425-448` | 行号以本次 read 为准 |
| `RA-08-HEAD-02` g0 | `✅` | read `generation_assemble.py:17-62` | |
| `RA-08-HEAD-03` scatter proof | `✅` | read `builtin_scatter.py:395-599`；`runtime_scatter.py:430-474` | |
| `RA-08-HEAD-04` pointer/serving CAS | `✅` | read `vector_publish_commit.py`；`lifecycle_publish.py` | 与 `T-O-242` 落地形态差异已登记 |
| `RA-08-HEAD-05/13` rebuild clean | `✅` | read `acquisition_intents.py`；`clean_preflight.py:28-127,706-714` | **修正**「rebuild 不重 clean」叙事：仍走 decode+clean |
| `RA-08-HEAD-07/08` lifecycle | `✅` | read `lifecycle_apply.py`；read `test_intake_lifecycle.py`；`test_intake_reactivate.py` | |
| `RA-08-HEAD-09` retrieval fence | `✅` | read `retrieval_rank.py:1-90,339-433` | |
| `RA-08-HEAD-10` 七意图 | `✅` | read `api/models.py:250-286`；`task_create.py:37-46`；`acquisition_ingest.py:32-48` | |
| `RA-08-HEAD-11` source e2e | `✅` | read 测试；`uv run pytest` 复跑失败 | static 停 running；monkeypatch `:99-101` |
| `RA-08-HEAD-12` scatter 无 search | `✅` | `grep retrieval:search` 该文件 **无命中**；`rg namespace_key tests/e2e` = 0；read `models.py:505-509` | **收回**「inline 已做」：inline/rebuild/reactivate/index.rebuild 有调用但缺 namespace **必 422**；与 scatter 无 search **同类缺口**（R1-I01） |
| `RA-08-HEAD-14` layer_b | `✅` | read `vector_publish_commit.py:119` | |
| `RA-08-HEAD-15` zero | `✅` | read `test_registered_api_scatter.py:352-364` | |
| `RA-08-HEAD-16` inline fallback | `✅` | read `config_snapshots.py:138-144,474-501`；`workflow_registry.py:78-104` | |
| `D-08-*` 分母脚本 | `✅` | `uv run python` 打印 7 intents / 4 kinds / 3 filters | 不改 `D-01..24` |
| `D-24` 复跑 | `✅` | pytest 两 case：1 passed / 1 failed | 消费冻结值；本面墙钟约 43s |
| `RA-08-LEGACY-01..05` | `✅` | read_file finalizer/differ/purger/callbacker/vector_db（未运行） | |
| `RA-08-WEB-01` | `✅` | web_search `Elasticsearch index alias atomic swap official` + open `elastic.co/docs/manage-data/data-store/aliases` | 访问日 2026-08-29；限制：部分失败仍 acknowledged |
| `RA-08-WEB-02` | `✅` | web_search OpenSearch write index + open `docs.opensearch.org/latest/api-reference/alias/aliases-api/` | 一 alias 仅一 write index |
| `RA-08-WEB-03` | `✅` | web_search Lucene/ES NRT + open Elastic near-real-time-search | refresh≠commit |
| `RA-08-WEB-04` | `✅` | web_search + open Lucene **10.4.0** `IndexWriterConfig.setSoftDeletesField`（访问 2026-08-29） | 「Currently there is no API support to un-delete」在 10.4.0 仍成立 |
| `RA-08-WEB-05` | `✅` | web_search CAS generation + open Elastic OCC | `if_seq_no` |
| `T-O-376/381/386/389` | `✅` | grep+read QNA 表 | 只 CITE |
| `T-P-NH-*` | `✅` 未当作 HEAD 事实 | 纪律 | 初判不引用为实现 |
| 面 07 权威细节 | 未整面重做 | 边界 | 只消费 `D-16..19` 与 `G-NH-05/06` |

三渠道事实核查：`[HEAD code] [legacy-family clean] [web-search]` 均已发生，对应 `RA-08-HEAD-*` / `RA-08-LEGACY-*` / `RA-08-WEB-*`。

---

## 12. 收尾 Verdict 与交接 `[核心]`

- **本面裁定**（分析结论，非 owner 决策）：publication **substrate 已在**（尾链、g0、proof、pointer、lifecycle CAS）；**检索终验未绿**（e2e search 缺 namespace 必 422；scatter 无 search）。**战役缺口是接通与终验**，不是重写 cuts/g0/scatter 图。最关键三 S1 = `NH-RA08-B01` 四通道未 live-to-vector、`NH-RA08-B02` 检索终验假绿、`NH-RA08-B03` FilterMeta facet 缺失。并行 S1 `NH-RA08-B04`：rebuild 仍可能重 clean。
- **交接下游**：缺口台账（§4）→ 规划；净新契约（§6）→ 设计；owner-gate 候选（§10.2，含消费 `G-NH-05/06/08` 与新 MARK `G-NH-17` 非法格 / `G-NH-19` reclean；index §4 尚未登记 11+，本轮不改 index）→ 决策登记；验收格栅（§9）→ 执行计划。面 09 消费本面 fake-green 与 CAS 窗口，不重画尾链。
- **冻结前置**：本分析保持 `draft`。要 `reviewed` 需：review-fleet 对账面 04/07 的 clean/facet 合同；每个 S1 仍有 HEAD 正反例；非法格表与 `G-NH-17/19` 未被本文裁决。要 `frozen` 还需跨面冲突关闭（尤其 `D-18/D-19` 与 publication echo）。

---

## 附录 A · 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-08-29 | Grok analysis-fleet / review-fleet | 初稿（measure-first + 借鉴矩阵 + 缺口台账）；三渠道 RA；消费 `D-01..24`；复跑 `D-24` 同型 1/1 |
| v0.2 | 2026-08-29 | Grok fix-fleet | 吸收已核实 review：R1-I01 收回 inline 检索正例（缺 namespace 必 422）；R2-I04 differ 补 meta_hash 分支；R3-I16 Lucene 改挂 10.4.0；R4-I01/I02 `G-NH-11/12` 重编号为 `G-NH-17`（非法格）/`G-NH-19`（reclean）。状态仍 `draft` |
