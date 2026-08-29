# 调查面 `04` · clean capability activation 与 admitted clean 合同 — 深度评估

> **对象 / scope-fence**：10 `CleanStrategyKey`、9 Process capability、三 registered API operation、strategy ↔ process ↔ representation compatibility、promptA 义务、非空 admitted clean、provider parser / 双 digest、空成功 vs exhausted-zero 分账。**本面不含**：adapter / 模型 / 二进制部署（面 `05`）；S06 结构化算法（面 `08` 消费 admitted clean）；选图代数（面 `01`）；acquire/decode 表示诚实（面 `03` 拥有，本面只消费）。
> **日期**：`2026-08-29`
> **作者**：`Grok analysis-fleet / review-fleet`（fleet / panel：`new-harvest-reference-anchor`）
> **文档性质**：`assessment / analysis`（单面 measure-first 深评；零决策——只 MARK 不裁决）
> **文档状态**：`draft`
> **流水线位置**：站② · 上游 = [[assessment-index]]（消费其冻结分母）
> **对照参考**：`docs/eval/new-harvest/pre-initial-planning-qna.md` v0.5 `T-O-376..389`；`docs/baseline/domain-truth/D08-legacy-capabilities-migration.md` `D08-T002/T007`；`docs/baseline/spec-glossary.md` `CleanStrategy` / `promptA`；HEAD `1221aa1`
> **上游权威输入**：
> - `docs/eval/new-harvest/assessment-index.md` — §2.2 `D-02/D-03/D-04/D-06/D-21/D-22/D-23/D-24` / §3.04 / §7
> - QNA `T-O-378/381/383/386` — 一份 admitted clean；promptA 仅 `llm_required`；空正文非成功
> **下游消费者**：`docs/eval/new-harvest/planning-proposed.md` · `pre-charter-qna.md`（owner-gate 裁决）· 设计/执行制品 · 面 `05/08/09`

---

## 0. Verdict（结论先行）`[核心]`

- **0.1 一句话缺口 / 现状判断**：HEAD 已交付 10 strategy / 9 capability / 3 API operation 的 **纯函数闭集与 33 个 unit+intake 全绿**，但 **live 闭集未激活**：6 张 LLM/print-pdf/vision 图公开选不中、默认组合根未注入 `clean_llm`、`print_pdf` 表示从未生产、promptA 三套默认 id 字节互斥——总体方向是 **激活闭集 + 补 admitted-clean 合同**，禁止重写 `intake/`。
- **0.2 Top blockers（最关键断点）**：
  1. `NH-RA04-B01` — 6 张 unselectable 图挂着 `web_llm` / `pdf_llm` / `doc_llm` / vision / print-pdf，公开选图只覆盖确定性 + 图像 OCR（`D-06`）。
  2. `NH-RA04-B02` + `NH-RA04-B04` — 7 个 `llm_required` 策略在默认组合根无 `clean_llm`；即便注入，strategy 钉 `promptA.default` 而 snapshot/documentation 默认另两套 id，会 `PROMPT_HASH_MISMATCH`。
  3. `NH-RA04-B03` + `NH-RA04-B05` — `web.browser_print_pdf` 与 `pdf.document_understanding` **共用** `clean.extract.pdf_llm`；preflight 靠 `representation_kind==print_pdf` 反推，acquire **从不写** `print_pdf`，该格是死合同。
- **0.3 总体方向建议**：沿用 `intake/{web,pdf,doc,api}/` 纯函数与 registry；把 compatibility matrix 从 **闭集登记表生成**（禁止 10×representation 笛卡尔积）；补 admitted-clean 最小证据合同、空集合 vs 空 member 分账、promptA 绑定对齐（**不锁 id 字面**）。适配器/模型运输交面 `05`。
- **0.4 如何读本台账**：借鉴 verdict = `✅借` / `🔶部分借` / `⛔反例` / `🆕净新`；复用判定 = `✅复用` / `♻️重 substrate` / `🆕净新`；缺口 = `S1 阻断` / `S2 重要` / `S3 次要`。置信：`HEAD 实测 > 仓内文档锚 > 外部参考`。本面主题轴 = `identity 非一一映射` / `admitted-clean 最小合同` / `live reachability ≠ 函数存在` / `空成功 vs exhausted-zero` / `promptA 义务面`。

---

## 1. 方法与证据基线 `[核心]`

> 读了哪些代码/文档/参考；什么算可采信；怎么复现。**先证可证性，再下判断。**

- **1.1 本仓证据（如何测量）**：
  - HEAD：`src/contracts/intake/strategies.py`、`intake/__init__.py`、`intake/{web,pdf,doc,api}/`、`src/runtime/intake/clean_preflight.py`、`src/contracts/intake/semantics.py`、`src/workflows/lsrag_definition.py`、`src/services/{workflow_registry,config_snapshots,prompt_profiles,registry}.py`、`api/app.py`、`src/runtime/intake/{core,acquisition_ingest}.py`、`src/runtime/workflow/runtime_scatter.py`、`src/runtime/intake/generation_assemble.py`、`tests/unit/test_intake_{clean_dispatch,provider_registry}.py`、`tests/intake/test_{web,pdf,doc}_clean.py`。
  - QNA：`T-O-378/381/383/386`（CITE，不扩冻）。`T-P-NH-*` / `initial-planning.md` 仅标「叙事/初判」。
  - Baseline：`D08-T002/T007/T009`；glossary `CleanStrategy` / `promptA`。与 HEAD 冲突显式登记，不自动覆盖。
  - 禁止：把 monkeypatch / stub / 503 / 空 `clean_text` 写成 live 成功；把「函数存在」写成「通道接通」。
- **1.2 外部 / 参考来源 + 置信**：
  - legacy-family **只读**（未 import/编译/运行）：`smind-skill-clean-universal`、`smind-skill-clean-dedicated-apis`、`smind-clean-dispatcher`。置信：ReferenceAnchor，低于 HEAD。
  - 公开网络（访问日 **2026-08-29**）：见每条 `RA-04-WEB-*`。置信：机制/失败法；**不得**证明 MKB 当前状态。GUIDE 论文与 JSON Schema 2020-12 为核心；Prompt Provenance 为 **v0.1 draft**，不得当规范权威。
- **1.3 ★ 可复现命令清单（measure-first）**：
```bash
# 共享分母（与 index §2.1 同脚本；本面不得改写 D-02..D-24）
uv run python - <<'PY'
from intake import _REGISTERED_CLEAN
from intake.api.registry import REGISTERED_PROVIDER_OPERATIONS
from src.contracts.intake.strategies import CLEAN_STRATEGY_DEFINITIONS
from src.workflows.lsrag_definition import (
    BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW,
    BUILTIN_SOURCE_PROFILE_WORKFLOWS,
    SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS,
)
single = (BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW, *BUILTIN_SOURCE_PROFILE_WORKFLOWS)
public = set(SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS.values())
print("clean_strategies", len(CLEAN_STRATEGY_DEFINITIONS))
print("clean_process_capabilities", len(_REGISTERED_CLEAN))
print("provider_operations", len(REGISTERED_PROVIDER_OPERATIONS))
print("public_selector_keys", len(SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS))
print("unselectable_single_identities", sum(x.workflow_key not in public for x in single))
PY

# D-23 本面复测（2026-08-29）
uv run pytest \
  tests/unit/test_intake_provider_registry.py \
  tests/unit/test_intake_clean_dispatch.py \
  tests/intake/test_web_clean.py \
  tests/intake/test_pdf_clean.py \
  tests/intake/test_doc_clean.py --collect-only -q
# 收集 33；跑测 33 passed / 0 failed

# promptA 三文件哈希分叉
uv run python - <<'PY'
from pathlib import Path
import hashlib
for f in [
    "data/prompts/prompt-a-clean-v1.md",
    "data/prompts/clean/promptA.clean.v1.md",
    "data/prompts/clean/promptA.documentation.default.v1.md",
]:
    b = Path(f).read_bytes()
    print(f, len(b), hashlib.sha256(b).hexdigest())
PY
```
- **1.4 范围围栏**：本面**只**覆盖 clean strategy / capability / admitted-clean 合同 / 空成功法 / promptA 义务面 / live **reachability**。adapter 选型、browser/PDF 二进制、S11 请求协议（面 `05`）；acquire 从不写 `print_pdf` 的表示法（面 `03` 拥有，本面消费）；API **live 供应商 fetch** 不在范围（caller-frozen records，`T-O-381`）；S06/g0 切法不重开（面 `08` 消费本面 admitted clean）。

---

## 2. 当前结构分析（HEAD 实测 · measure-first）★ `[核心]`

> 按主题轴逐条测，每条钉 `path:line`。先冻结本面分母，再逐轴展开。

### 2.1 ★ 冻结分母（FROZEN denominators · HEAD）

> 引用 [[assessment-index]] §2.2 中属于本面的分母，并补本面专属分母。下游不得另估共享行。

| 分母 | HEAD 实测值 | 证据锚（`path:line`） | 来源 |
|------|-------------|------------------------|------|
| `D-02` CleanStrategyKey | `10` | `src/contracts/intake/strategies.py:15-151`；本面脚本 `clean_strategies 10` | `index §2.2` |
| `D-03` clean Process capability | `9`（8 single + 1 API map） | `intake/__init__.py:20-30` | `index §2.2` |
| `D-04` registered API operation | `3` | `intake/api/registry.py:73-104` | `index §2.2` |
| `D-06` public selector / unselectable single | `7 / 6` | `lsrag_definition.py:929-940,1003-1069` | `index §2.2` |
| `D-07` scatter identities | `2` | `builtin_scatter.py` scatter root+child | `index §2.2`（本面消费 API map） |
| `D-21` 默认组合根 browser_fetcher / clean_llm | `0 / 0` | `api/app.py:330-345`；`core.py:39-76` | `index §2.2` |
| `D-22` legacy universal / dedicated 分叉 | `6 / 3` | universal `action_registry.ts:91-149`；dedicated `action_registry.ts:59-79` | `index §2.2` |
| `D-23` 选定 clean/provider unit+intake | `33 passed / 0 failed` | 本面复测 2026-08-29：collect `6+5+5+10+7=33`，pytest 全绿 | `index §2.2`；**本面复测一致，不改数字** |
| `D-24` 三 provider e2e / source capability e2e | `1 passed / 1 failed` | 本面 **未** 复跑 e2e；沿用 index | `index §2.2` |
| `D-04-A` `llm_required=True` 策略数 | `7` | `strategies.py:57-149`（除 web/pdf_text/doc 三条确定性） | 本面新测 |
| `D-04-B` 钉 `promptA.default` 的策略数 | `7`（全部 `llm_required`） | `strategies.py:63-147` | 本面新测 |
| `D-04-C` 公开图覆盖的 LLM/print-pdf/vision 策略 | `1`（仅 `local_object.image` → `clean.ocr.local`） | `lsrag_definition.py:929-1000` vs `1003-1054` | 本面新测 |
| `D-04-D` 一 process_key 服务两 strategy | `2` 对：`clean.extract.pdf_llm`、`clean.ocr.local` | `strategies.py:67-138`；`clean_preflight.py:58-69` | 本面新测 |
| `D-04-E` promptA 三默认文件互斥哈希 | `3` 份不同 SHA-256（471 / 802 / 791 字节） | `data/prompts/prompt-a-clean-v1.md`；`clean/promptA.clean.v1.md`；`clean/promptA.documentation.default.v1.md` | 本面新测 |

### 2.2 轴 `identity：strategy ≠ process ≠ representation`（HEAD 核验）

- **10 个 strategy 是登记闭集，未知即 409**：`resolve_clean_strategy` 查 `_BY_KEY`，缺失抛 `CLEAN_STRATEGY_UNSUPPORTED` 409（`strategies.py:156-160`）。unit 闭集断言 10 键（`test_intake_provider_registry.py:131-143`）。
- **9 个 process capability 是另一闭集**：`_REGISTERED_CLEAN` 9 键（`intake/__init__.py:20-30`）。未知 `CLEAN_CAPABILITY_UNSUPPORTED` 409（`:54-55`）。
- **核心非一一映射（本面 identity 题）**：

| process_key | 服务的 strategy | 反推条件（HEAD） |
|-------------|-----------------|------------------|
| `clean.extract.pdf_llm` | `pdf.document_understanding` **与** `web.browser_print_pdf` | `representation==print_pdf` → print-pdf，否则 PDF DU（`clean_preflight.py:58-63`；`intake/__init__.py:78-81`） |
| `clean.ocr.local` | `pdf.ocr` **与** `doc.ocr` | `media_type==application/pdf` → pdf.ocr，否则 doc.ocr（`clean_preflight.py:65-69`） |
| 其余 6 个 single clean | 各 1 strategy | 表驱动 1:1（`clean_preflight.py:54-70`） |
| `clean.map.registered_api` | **不是** `CleanStrategyKey` | 三 `(provider,operation,version)`（`registry.py:73-104`） |

- **`web.browser_print_pdf` 的 `channel` 字段是 `pdf` 不是 `web`**（`strategies.py:67-76`）。D08-T009 / QNA 均要求 print-pdf 进 PDF 通道，勿当 HTML 消毒。
- **representation 在 clean 侧只认三值**：`print_pdf` / `rendered` / 其余折叠为 `static`（`clean_preflight.py:46-53`）。web handler 只接受 `static|rendered`（`intake/web/__init__.py:57-58`）。acquire 今日只写 `rendered|transferred`（`acquisition_ingest.py:535`，面 `03` 拥有）→ print-pdf 反推条件在 HEAD **物理不可达**。

### 2.3 轴 `合法 compatibility matrix 如何生成`（HEAD 核验）

> 合法格 **不是** `10 strategy × 任意 representation × 任意 capability` 笛卡尔积。生成规则：以 `CLEAN_STRATEGY_DEFINITIONS` 行 + `dispatch_clean` 通道守卫 + 公开 profile 键为生成器。

**生成器（草案，非冻结实现）**：

1. 对每个 `CleanStrategyDefinition` 取 `(strategy_key, channel, clean_capability, llm_required, browser_required, prompt_key, acquire_capabilities)`。
2. 校验 `definition.channel` 与 handler 通道、`definition.clean_capability == capability`，否则 `CLEAN_STRATEGY_CAPABILITY_MISMATCH` 409（web `:54-56`、pdf `:23-25`、doc `:54-55`）。
3. representation 过滤：web 仅 `static|rendered`；print-pdf 仅当 `representation_kind=print_pdf` 且 bytes 为 PDF；OCR/Vision 要求 `image/*` 或 PDF（OCR）。
4. API 行单独展开为 3 operation，**不**进入 strategy 枚举。
5. live 列 = 公开 selector 命中 **且** 所需端口在默认组合根注入 **且** representation 可被 acquire 生产。函数绿 ≠ live 绿。

| strategy | channel | process_key | llm | browser | prompt | 合法 acquire | 合法 representation | 公开图（`D-06`） | HEAD live（默认组合根） |
|----------|---------|-------------|-----|---------|--------|--------------|---------------------|------------------|-------------------------|
| `web.deterministic` | web | `clean.extract.web` | N | N | 无 | http_static / http_browser | static / rendered | `http_resource.static` / `.browser` | 函数可达；browser acquire 端口未注入（面 `03/05`） |
| `web.llm_rewrite` | web | `clean.extract.web_llm` | Y | N | `promptA.default` | 同上 | static / rendered | **unselectable** 两张 | 函数存在（unit mock）；图选不中 + 无 `clean_llm` + promptA 分叉 |
| `web.browser_print_pdf` | **pdf** | `clean.extract.pdf_llm` | Y | Y | `promptA.default` | http_browser | **必须** `print_pdf` | unselectable `http-browser-print-pdf` | **死合同**：acquire 从不写 `print_pdf` |
| `pdf.text_layer` | pdf | `clean.extract.pdf_text` | N | N | 无 | local_object / http_static | transferred PDF + 文本层 | `local_object.pdf` / `http_resource.pdf` | 函数可达；decode 字面量扫描属面 `03` 假实现（`T-O-378`） |
| `pdf.document_understanding` | pdf | `clean.extract.pdf_llm` | Y | N | `promptA.default` | 同上 | PDF bytes | unselectable `local-pdf-understanding` | 函数存在（注入 LLM）；图选不中 + 无端口 |
| `pdf.ocr` | pdf | `clean.ocr.local` | Y | N | `promptA.default` | 同上 | PDF bytes | **无独立公开图**；OCR 公开图是 image | 仅当已选 `clean.ocr.local` 且 media=PDF；公开 PDF 图绑的是 `pdf_text` |
| `doc.deterministic` | doc | `clean.extract.deterministic` | N | N | 无 | inline / local_object | 非 image | `inline_payload` / `local_object` | 函数可达 |
| `doc.document_understanding` | doc | `clean.extract.doc_llm` | Y | N | `promptA.default` | local_object | 文档 bytes/text | unselectable `doc-llm` | 函数存在；图选不中 |
| `doc.ocr` | doc | `clean.ocr.local` | Y | N | `promptA.default` | local_object | `image/*` | `local_object.image` **可选** | 图可选但默认无 `clean_llm` → 503；CLI 路径对 OCR **显式排除**（`clean_preflight.py:76`） |
| `doc.vision` | doc | `clean.extract.vision` | Y | N | `promptA.default` | local_object | `image/*` | unselectable `vision-rejected` | 图选不中；即使注入也排除 CLI |
| `clean.map.registered_api`（非 strategy） | api | 同左 | N | N | 无 | caller-frozen records | raw members | scatter root（kind 选图，非 7 selector） | parser/map e2e 绿（`D-24` 三 provider passed）；live 爬虫 OOS |

**非法格（必须 409/422，不得暗升）**：image + `doc.deterministic`（`doc/__init__.py:12-13`）；web strategy 配 pdf capability；未知 strategy；print-pdf 当 HTML；HTTP PDF 当 web sanitizer（已被 PDF-first 补丁挡住，见 2.7）。

### 2.4 轴 `每个 strategy 的 admitted clean / evidence 最小合同`（HEAD 核验）

产品法（`T-O-386`）：不论通道，S06/g0 只消费 **一份** admitted clean body（非空、content digest、strategy/capability evidence）。g0 original **必须等于** 该 body（`generation_assemble.py:17-43` overlay `original_content.body=clean`）。

HEAD 已实现的最小字段（草案合同，**不锁列名字面**）：

| 通道 | 非空正文 | content digest | strategy/capability evidence | 额外义务 |
|------|----------|----------------|------------------------------|----------|
| web deterministic | `CLEAN_EMPTY` 422（`web/__init__.py:28-29`） | runtime `stable_digest({"text"})`（`clean_preflight.py:126`） | `channel/representation/strategy/definition_version/strategy_definition_digest` | sanitizer 删除闭集元素（`sanitize.py:11-14`） |
| web llm_rewrite | 先 sanitizer 再 LLM；空 rewrite `CLEAN_EMPTY`（`:88-90`） | 同上 | 另加 `producer/prompt_key/prompt_version/prompt_content_sha256` | prompt 指针必须 `== definition.prompt_key/version` 否则 `PROMPT_HASH_MISMATCH` 503（`:86-87`） |
| pdf text_layer | 空 → `CLEAN_PDF_TEXT_LAYER_MISSING` 422（`pdf/__init__.py:29-31`），**不是**空成功 | 同上 | `mode=text_layer`；无 prompt | 不得降级到 understanding |
| pdf DU / print-pdf / pdf OCR | 空 → `CLEAN_EMPTY`（`:59-60`）；缺 LLM 503 | 同上 | `mode` + prompt hash + `input_blob_digest` | 缺 blob（OCR）`CLEAN_PDF_INPUT_MISSING` |
| doc deterministic | `CLEAN_EMPTY`（`doc/__init__.py:19-20`） | 同上 | strategy digest | image 禁止走此策略 409 |
| doc LLM / OCR / vision | 空 `CLEAN_EMPTY`（`:73-74,:96-97`） | 同上 | prompt hash | OCR/vision 无注入 503 且 **排除 CLI** |
| API member | `MappedProviderMember.clean_text` `min_length=1`（`semantics.py:44`） | **双 digest** content + meta（chinatax `providers/chinatax.py:90-91`） | parser/provider/operation + FilterMeta 五维 + **恰好 6** semantic tuples（`semantics.py:51`） | schema 失败 `CLEAN_MEMBER_SCHEMA_INVALID` 422，**整批失败**（`registry.py:132-148`）；不 silent skip |
| seal / preflight | 单文档空/空白 `PIPELINE_INPUT_INVALID` 或 admission `rejected/clean_candidate_empty`（`clean_preflight.py:345-347,544-547`） | candidate_root_digest 绑 clean_digest | clean_evidence.capability 必须以 `clean.` 开头（`:676-677`） | rebuild 只重放已接受 clean Artifact（`:707-715`） |

**promptA 义务**：仅 `llm_required=True` 进入 binding；确定性与 API map **仍是 clean**，用 strategy/mapper digest 代替 promptA hash（`T-O-386`；HEAD：确定性定义 `prompt_key=None`，`strategies.py:47-55,79-86,109-117`）。

### 2.5 轴 `promptA 三套默认 id 分叉`（HEAD 核验；不锁对齐方案）

| 位点 | 默认 id | 路径 | 本面测得 SHA-256 前缀 / 字节 |
|------|---------|------|------------------------------|
| strategy 表（全部 LLM 策略） | `promptA.default` `v1` | `prompt-a-clean-v1.md` | `f293d21c6166b3eb…` / 471 B（`strategies.py:63-147`；`registry.py:57,68`） |
| ConfigSnapshot `_DEFAULT_PROMPT_IDS` | `promptA.clean` | `clean/promptA.clean.v1.md` | `ab70f981d23b873b…` / 802 B（`config_snapshots.py:57-59,635`；`registry.py:67`） |
| documentation 域 profile / README | `promptA.documentation.default` | `clean/promptA.documentation.default.v1.md` | `7276f517045c1511…` / 791 B（`prompt_profiles.py:50`；`README.md:243`；`test_ns1_api_workflow.py:166`） |

三份正文 **不是同一字节**：documentation 保留 Markdown 结构；`promptA.clean` 禁止 Markdown；`promptA.default` 较短。runtime LLM 路径要求 `prompt.key == definition.prompt_key`（`web/__init__.py:86-87`）。若 Task 冻结 `prompt_selection.clean=promptA.documentation.default`，`_clean_prompt_material` 会把 `CleanPrompt.key` 设成 catalog id（`clean_preflight.py:183-188`），与 strategy 的 `promptA.default` 对不上 → `PROMPT_HASH_MISMATCH`。CLI 无 selection 时硬读 `prompt-a-clean-v1.md`（`:99-100`）。**对齐方案不在本面裁决**（QNA §10.2 已把「promptA 目录 id 三套对齐」标 **执行延期**，本面 **不再占用** owner-gate 号）。

### 2.6 轴 `API exhausted-zero 与 empty member 分账`（HEAD 核验）

| 情形 | HEAD 行为 | 产品法对照 |
|------|-----------|------------|
| **exhausted-zero**：`members=[]` 且 `collection_exhaustion_proof=caller_frozen_records.v1` | map 返回 `[]`（`intake/api/__init__.py:27-28`）；seal 允许 `member_count=0`（`clean_preflight.py:507-508`）；scatter join 把零成员当 **SUCCESS** 业务终态（`runtime_scatter.py:76-98`）；e2e `records=[]` → `status=succeeded`、counts 全 0、items `[]`（`test_registered_api_scatter.py:352-364`） | `S05-A11`：合法空集合仅在 exhausted proof 下 complete。**终态语义**（typed no-op / 无变更终态 / 显式空失败）= `G-NH-08`，本面只 MARK |
| **无 exhaustion proof 的空集合** | seal `SCATTER_EXHAUSTION_PROOF_REQUIRED` 422（`clean_preflight.py:439-444`；`test_intake_provider_registry.py:117-128`） | 不得假 complete |
| **empty member**：member 存在但 `clean_text` 空 | pydantic `min_length=1` → `CLEAN_MEMBER_SCHEMA_INVALID` 422，**整批 map 失败**，无 per-member skip（`semantics.py:44`；`registry.py:132-148`） | `T-O-378/383` 空正文不是成功；与 exhausted-zero **不是同一格** |
| **schema 失败 / 缺键** | 同样 422 + `rejection_evidence`；禁止 invented external_key（`test_intake_provider_registry.py:68-84`） | 对齐 `D08-T008` parser 失败 typed rejection |

API 三 operation 的 **live fetch 不在本面**（caller-frozen records）。本面只核 map/parser/digest/空合同。

### 2.7 轴 `live reachability / 已交付勿重做`（HEAD 核验）

- **正例（沿用，禁止重写 `intake/`）**：structural HTML sanitizer；PDF/doc typed fail；API 三 operation 严格 schema；`dispatch_clean` **PDF 优先于 `source_kind==http_resource`**，防 HTTP PDF 被当 HTML（`intake/__init__.py:68-90`；`test_intake_clean_dispatch.py:164-176`）。33 case 全绿（本面复测）。
- **反例（函数存在 ≠ 通道接通）**：
  - 公开 selector 只有 7 键（`workflow_registry.py:98-102` 只查 `SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS`）；6 张 LLM/print-pdf/vision 图 **已 bootstrap 但选不中**（`lsrag_definition.py:1003-1054`）。
  - 默认 `IntakePipeline(...)` **不传** `browser_fetcher=` / `clean_llm=`（`api/app.py:330-345`；`D-21=0/0`）。`grep clean_llm api/app.py` 无命中。
  - `local_object.image` **可选** 但 OCR `llm_required` 且 CLI 排除 → 默认 503 `CLEAN_OCR_CAPABILITY_UNAVAILABLE`。禁止把 503 当通道 DoD（`T-O-376/381`）。
  - decode 无层抛 `CLEAN_OCR_CAPABILITY_UNAVAILABLE`（`types.py:154-158`）是 **面 `03` 谎言清单**（`T-O-378`），本面消费：它让 `pdf.ocr` 在绑定前被盗用码杀死。

### 2.8 轴 `选图键如何挡住 LLM 策略`（HEAD 核验）

`ConfigSnapshotService._source_profile` 只从 kind/mode/media 派生：`http_resource.{static,browser,pdf}`、`local_object` / `.pdf` / `.image`、inline（`config_snapshots.py:492-516`）。**没有** `*_llm` / `print_pdf` / `vision` profile 键 → 即使图对象存在，调用方也无法合法点名（`T-O-379` 禁 `workflow_key`）。这是 **选图面与本面的交界**：本面登记「哪些 capability 已有纯函数但选不中」；如何并进 kind 图是面 `01` + `T-O-387`。

---

## 3. 借鉴锚定矩阵（Reference Anchor Matrix）★ `[核心]`

> 每个可借鉴点钉到 `path:line` / URL，给**借鉴 verdict**。正反例成对；无先例标 `🆕`。

| 借鉴点 / RA-ID | 来源锚（`path:line` / URL） | 借鉴 verdict | 借什么 / 不借什么 |
|--------|------------------------------|--------------|--------------------|
| `RA-04-HEAD-01` 未知 strategy 409 | `strategies.py:156-160`；`test_intake_provider_registry.py:131-143` · HEAD `1221aa1` · **正例** · 高 | `✅借` | 借闭集 registry + fail-closed。不借把 registry 当 live 证明。命中 `NH-C-38` |
| `RA-04-HEAD-02` HTML sanitizer + `CLEAN_EMPTY` | `intake/web/sanitize.py:11-14`；`web/__init__.py:25-29,88-90` · **正例** · 高 | `✅借` | 借结构 parser + 空正文 422。不借 regex 去标签。命中 `NH-RA04-B08`（缺 web 空测） |
| `RA-04-HEAD-03` API 非空 clean + 六元组 | `semantics.py:37-52`；`chinatax.py:48,83-94` · **正例** · 高 | `✅借` | 借 `min_length=1`、双 digest、FilterMeta 五维与 g0 分账。不借把 JSON member 当 admitted clean 本身。命中 `NH-C-31/37` |
| `RA-04-HEAD-04` PDF-first dispatch | `intake/__init__.py:68-90`；`test_intake_clean_dispatch.py:132-176` · **正例** · 高 | `✅借` | 借 HTTP PDF 不进 web sanitizer。不借 media_type 暗路由交差（仍须图声明 capability）。命中 `NH-C-36` |
| `RA-04-HEAD-05` 33 unit/intake 全绿 | 本面复测 2026-08-29 `33 passed / 0 failed` · **正例** · 高 | `✅借` | 借纯函数水位。不借 unit 绿当 default-root e2e。命中 `D-23` |
| `RA-04-HEAD-06` identity 非 1:1 | `strategies.py:67-76,99-107,130-138`；`clean_preflight.py:54-71` · **正例（结构）/ 反例（反推）** · 高 | `🔶部分借` | 借「process_key 可服务多 strategy」这一事实去生成 matrix。不借今日 representation 三值反推当晚绑定权威。命中 `NH-RA04-B05` `NH-C-30` |
| `RA-04-HEAD-07` 6 张 unselectable 图 | `lsrag_definition.py:1003-1054`；`workflow_registry.py:98-102` · **反例** · 高 | `⛔反例` | 避开「图在仓库里=可选」。命中 `NH-RA04-B01` |
| `RA-04-HEAD-08` promptA 三 id 三哈希 | `strategies.py:63`；`config_snapshots.py:58,635`；`prompt_profiles.py:50`；三文件不同 SHA · **反例** · 高 | `⛔反例` | 避开「catalog 有行=可绑 strategy」。不在本面锁对齐 id。命中 `NH-RA04-B04`（QNA 执行延期） |
| `RA-04-HEAD-09` print_pdf 死合同 | `acquisition_ingest.py:535` vs `clean_preflight.py:46-63` · **反例** · 高 | `⛔反例` | 避开用未生产的 representation 反推 strategy。表示生产属面 `03`。命中 `NH-RA04-B03` |
| `RA-04-HEAD-10` 默认根无 `clean_llm` | `api/app.py:330-345`；`core.py:45-76`；`D-21=0/0` · **反例** · 高 | `⛔反例` | 避开「handler 接受注入=已接线」。端口属面 `05`。命中 `NH-RA04-B02` |
| `RA-04-HEAD-11` exhausted-zero = SUCCESS | `runtime_scatter.py:76-98`；`test_registered_api_scatter.py:352-364` · **正例（typed complete）/ 终态待裁** · 高 | `🔶部分借` | 借「无 proof 不得 seal」。终态三选一交 `G-NH-08`。命中 `NH-RA04-B07` |
| `RA-04-HEAD-12` g0=clean overlay | `generation_assemble.py:17-43` · **正例** · 高 | `✅借` | 借 system g0 body=clean。不借在本面改 cuts。命中 `NH-C-31` 交面 `08` |
| `RA-04-HEAD-13` 公开 OCR 图仍 503 | `lsrag_definition.py:991-999`；`clean_preflight.py:76` CLI 排除 OCR/vision · **反例** · 高 | `⛔反例` | 避开「selector 有键=live」。命中 `NH-RA04-B02` |
| `RA-04-LEGACY-01` 6 分叉清单 | `smind-skill-clean-universal/services/action_registry.ts:91-149` · D08-T002 · **正例（分叉）** · 中 | `🔶部分借` | **借** 6 branch → 10 strategy 的语义拆分（acquire × clean）。**不借** `action_branch` taxonomy、Gemini 硬绑、CF fetch。命中 `NH-C-30` `D-22` |
| `RA-04-LEGACY-02` FilterMeta 五维 | dedicated `chinatax/schemas.ts:52-60`；`processor.ts:72-80` · D08-T007 · **正例** · 中 | `🔶部分借` | 借字段名与 D08-T007 分账（进 SemanticDefinition 不进 g0）。**不借** JSON/R2 child、`payload_filter_meta`、`is_active` 全局缺省。与面 07 对齐。命中 `NH-C-37` |
| `RA-04-LEGACY-03` `plainTextAvailable: true` 无非空检查 | `cleaner_web.ts:312-329`；`cleaner_doc.ts:139-151` · **反例** · 中 | `⛔反例` | **不借** empty success。HEAD `CLEAN_EMPTY` 是纠正。命中 `NH-C-33` |
| `RA-04-LEGACY-04` parse catch 后 `return null` | `chinatax/processor.ts:150-155`；`domain/processor.ts:168-173` · **反例** · 中 | `⛔反例` | **不借** per-member silent skip。HEAD 整批 422。命中 `NH-RA04-B07` 对照 |
| `RA-04-LEGACY-05` `empty_response` 仍返回成功形 | `realestate/processor.ts:185-192` · **反例** · 中 | `⛔反例` | 不借无 exhaustion proof 的空成功。对照 HEAD `SCATTER_EXHAUSTION_PROOF_REQUIRED` |
| `RA-04-LEGACY-06` finalizer 以 R2 key 推成功 | `smind-clean-dispatcher/flows/finalizer.ts:106-129` `cleaned_content_r2_key` → `file_status=clean_completed` · **反例** · 中 | `⛔反例` | 不借 object-key / payload 当 admitted clean。命中面 `08` 假绿 |
| `RA-04-LEGACY-07` Gemini `*-latest` + alias | `cloudflare_ai/providers/gemini.ts:47-61` `gemini-flash-lite-latest`；KV prompt alias · **反例** · 中 | `⛔反例` | 不借 latest 浮动模型/prompt。借「LLM 分支才调模型」与 `T-O-386` 一致 |
| `RA-04-LEGACY-08` dispatcher 原样下发 `action_branch` | `smind-clean-dispatcher/services/mapper.ts:193-200` · **反例** · 中 | `⛔反例` | 不借 branch 字符串当路由。命中 `T-O-377/379` |
| `RA-04-LEGACY-09` dedicated 3 operation 无 AI | `dedicated-apis/services/action_registry.ts:59-79` · **正例** · 中 | `🔶部分借` | 借「dedicated 从不 Gemini 洗」支撑 promptA 仅 LLM 策略。不借隧道/cookie/live 爬虫（隧道钉 `get_articles.ts:38,61-77`，见 LEGACY-11） |
| `RA-04-LEGACY-10` content/meta 双 hash | `chinatax/processor.ts:169-181`；`domain/processor.ts:187-199` · D08-T008 · **正例** · 中 | `✅借` | 借双 digest 身份。不借随机 `uuidv4()` child id（chinatax `:159`） |
| `RA-04-LEGACY-11` 税局隧道 + 固定 siteCode | `providers/chinatax/get_articles.ts:38,61-77` `BASE_URL=https://chinatax.sourcemind.com.cn/proxy/chinatax` | `⛔反例` | 不借 sourcemind 隧道 / 固定 siteCode。D08-T004/REF-02 |
| `RA-04-LEGACY-12` sanitizer 标签闭集 + 属性白名单 | `smind-skill-clean-universal/core/sanitizer.ts:33-42,79-110` | `🔶部分借` | 借 TAGS_TO_REMOVE / ATTRIBUTES_TO_KEEP 规则表（对照 D08-REF-08 / HEAD `intake/web/sanitize.py`）。不借 Workers `HTMLRewriter` |
| `RA-04-LEGACY-13` regex `stripHtmlTags` 当纯文本 SSOT | `cleaner_web.ts:46-54` | `⛔反例` | D08：regex 去标签不得回归；HEAD 已用结构 parser |
| `RA-04-LEGACY-14` snapshot slot 缺失 catch 后忽略 | `cleaner_web.ts:188-194,332-336` `tryWriteSnapshot` | `⛔反例` | 静默丢产物，与 admitted-clean evidence 合同冲突 |
| `RA-04-LEGACY-15` 税局空列表仍成功形 | `chinatax/processor.ts:138-140,241-250` `rawItems.length===0` 只 warn | `⛔反例` | D08-X07；processed_items 可 0，无 exhaustion proof |
| `RA-04-LEGACY-16` REA per-member skip（catch 之外） | `realestate/processor.ts:209` `if (!parsedItem.listing_id) return;` | `⛔反例` | 补强 skip 闭集（不止 catch `:284-287`） |
| `RA-04-LEGACY-17` 未注册别名 `browserPDF-geminiClean` 仍强制 Vision | `cleaner_web.ts:296-301` vs `action_registry.ts` **未** register 该键 | `⛔反例` | 暗路由 / 别名 ≠ 登记闭集 |
| `RA-04-WEB-01` 确定性解析与 VLM 分账 + provenance | GUIDE arXiv `2608.12133` 2026-08-12 https://arxiv.org/html/2608.12133 · 访问 2026-08-29 · **正例** · 中 | `🔶部分借` | 借：Parsing Agent **无 LLM** 抽文本；VLM 另段；schema 合同；`silent_skip` 计入质量缺陷。不借六 agent 云编排、HITL 产品、26-field 规则库。限制：语料保密、英语、VLM 超时失败。命中 `NH-C-32` |
| `RA-04-WEB-02` Tesseract 「empty page」是质量条件不是成功合同 | tessdoc ImproveQuality https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html · 访问 2026-08-29 · **失败条件** · 中 | `🔶部分借` | 借：过大边框会导致 “empty page”；引擎 **没有**「空字符串=成功」产品法。不借把 Tesseract 选成本仓 OCR 引擎（面 `05`）。命中 `NH-C-33` |
| `RA-04-WEB-03` OCRmyPDF 把 Empty page 当 skip 占位 | https://raw.githubusercontent.com/ocrmypdf/OCRmyPDF/main/src/ocrmypdf/_exec/tesseract.py （**unpinned `main`**，访问 2026-08-29 内容含 `_is_empty_page_error` / `[skipped page]`；main 可漂移） · **反例（对 MKB 空合同）** · 中 | `⛔反例` | **不借** 空 OCR 输出写成 skip/占位后整批继续。MKB 绑定后空正文必须 fail-loud（`T-O-383`）。可借「把 empty page 识别为 typed 条件」本身 |
| `RA-04-WEB-04` JSON Schema 实例结果是单一 boolean | JSON Schema 2020-12 Core §7.6 https://json-schema.org/draft/2020-12/json-schema-core.html · 2022-06-16 draft-bhutton-json-schema-01 · 访问 2026-08-29 · **规范单源** · 高（规范） | `🔶部分借` | 借：对 **一个** instance，assertions 产生单一 boolean；失败 schema 不保留 annotation。规范 **不**定义批处理部分成功。不借把 JSON Schema 当 member 身份模型。命中 empty-member 整批失败 |
| `RA-04-WEB-05` JSONL 批校验默认首败即停 | sourcemeta jsonschema CLI `docs/validate.markdown` https://github.com/sourcemeta/jsonschema/blob/main/docs/validate.markdown · 访问 2026-08-29 · **失败条件** · 中 | `🔶部分借` | 借：数据集默认在 **第一条失败** 停止；`--continue` 才报全失败行；**单条内部继续过第一错误是 spec 灰区**。对齐 HEAD 整批 422。不借 CLI 工具进运行时 |
| `RA-04-WEB-06` （**线索 / 🆕 对照**，非 prompt 身份规范）个人 GitHub v0.1 写 id+version+content hash；README 的 `latest.json` 是 **optional well-known**，与「禁止 latest」强度不同 | https://github.com/mizcausevic-dev/prompt-provenance-spec · 1 star / 0 forks · 访问 2026-08-29 · **低** | `🆕对照` | **不得**当可落地 prompt 规范。B04 的 S1 由 HEAD 三哈希支撑。权威用仓内 S14 identity+hash |
| `RA-04-BASELINE-01` D08 分叉与五维 | `D08-legacy-capabilities-migration.md:93,98` D08-T002/T007 · 仓内文档 · 中 | `✅借` | 借三轴拆 branch、五维语义。文档状态仍 `draft/owner-review`，不覆盖 QNA |
| `RA-04-BASELINE-02` D08-T009 列 9 策略、缺 `pdf.ocr` | 同文件 `:100` vs HEAD `D-02=10` · **冲突登记** · 高 | `⛔反例`（对「D08 已列全闭集」叙事） | 不把 D08-T009 当 10 strategy SSOT。HEAD 多 `pdf.ocr`。命中 `NH-RA04-B10` |

---

## 4. 缺口 / 断点台账 ★ `[核心]`

| 编号 | 缺口 / 断点 | 严重度 | 证据（`path:line`） | 影响 |
|------|-------------|--------|----------------------|------|
| `NH-RA04-B01` | 6 张已声明图（web_llm×2、pdf_llm、doc_llm、vision、print-pdf）不在公开 selector，`T-O-381` live 矩阵选不中 | `S1 阻断` | `lsrag_definition.py:929-940,1003-1054`；`workflow_registry.py:98-102` | LLM/print-pdf/vision 策略无法经合法三轴进入 Execution |
| `NH-RA04-B02` | **消费** `NH-RA05-B01`：默认组合根未注入 `clean_llm`/`browser_fetcher`。本面另钉 OCR/vision 排除 CLI 回退（策略侧） | `S1 阻断`（clean 侧后果） | `api/app.py:330-345`（权威在面 `05`）；`core.py:45-76`；`clean_preflight.py:76`；`D-21` | 7 个 `llm_required` 策略即使图可选也 503；禁止 503 当 DoD |
| `NH-RA04-B03` | **消费** `NH-RA03-B02`（表示从不写 `print_pdf`）的 clean 侧死合同：pdf_llm 反推依赖它才能绑 `web.browser_print_pdf`。供给侧交叉 `NH-RA05-B07` | `S1 阻断`（clean 侧） | `acquisition_ingest.py:535`；`clean_preflight.py:46-63`；`strategies.py:67-76` | `T-O-381` 的 print-pdf 格物理不可达 |
| `NH-RA04-B04` | promptA 三套默认 id **三份不同字节**；strategy 钉 `promptA.default`，snapshot/documentation 另钉 | `S1 阻断` | `strategies.py:63-147`；`config_snapshots.py:58,635`；`prompt_profiles.py:50`；三 prompt 文件哈希 | LLM clean 一接就可能 `PROMPT_HASH_MISMATCH`；对齐方案不锁 |
| `NH-RA04-B05` | process_key→strategy 反推不是晚绑定权威：同一 `clean.extract.pdf_llm` / `clean.ocr.local` 服务两 strategy | `S1 阻断` | `clean_preflight.py:54-71`；`intake/__init__.py:78-81` | 图只声明 process_key 时会静默选错工人，打脸 `T-O-382/383` |
| `NH-RA04-B06` | `pdf.ocr` 无独立公开图；公开 PDF 图绑 `pdf.text_layer`；无层在 decode 被盗用 OCR 码杀死 | `S2 重要` | `lsrag_definition.py:951-987` vs `strategies.py:99-107`；`types.py:154-158` | 扫描 PDF 无法晚绑 `pdf.ocr`（decode 观察属面 `03`） |
| `NH-RA04-B07` | exhausted-zero 今日 SUCCESS 0 items；empty member 整批 422；终态产品法未裁 | `S2 重要` | `runtime_scatter.py:76-98`；`semantics.py:44`；`api/__init__.py:27-28` | 指标/检索「成功」可能含零向量业务；交 `G-NH-08` |
| `NH-RA04-B08` | `CLEAN_EMPTY` 在 web/doc/pdf LLM 路径存在，但选定测试集无 `CLEAN_EMPTY` 字面断言 | `S3 次要` | grep `tests/**/*.py` 无 `CLEAN_EMPTY`；pdf 空层测的是 `CLEAN_PDF_TEXT_LAYER_MISSING` | 假绿风险低（handler 有 raise），验收格栅需补负例 |
| `NH-RA04-B09` | API map 已 e2e 绿，但「可检索向量」终验属面 `08/09`；本面不得把 scatter succeeded 当 retrieval DoD | `S2 重要` | `D-24`；`test_registered_api_scatter.py:309-321` `publication_ready` 非 retrieval query | 防跨面假绿 |
| `NH-RA04-B10` | 仓内 D08-T009 列举 9 策略、缺 `pdf.ocr`，与冻结 `D-02=10` 冲突 | `S3 次要` | `D08-legacy-capabilities-migration.md:100` vs `strategies.py:15-25` | 规划若 CITE D08 闭集会漏 OCR 格 |

---

## 5. 跨功能系统一致性 ★ `[核心]`

- **5.1 整体形态一句话**：四通道知识生产的 **第一环** 是同一份非空 admitted clean；strategy 是与 kind/acquire 正交的闭集工人；图必须声明工人边，runtime 只 fence，`intake/` 只变换。
- **5.2 功能间一致性契约（不变量 `NH-C-30..39`）**：

| 编号 | 不变量 | 跨哪些面/模块 | 违反后果 |
|------|--------|----------------|----------|
| `NH-C-30` | `CleanStrategyKey`、Process `clean.*`、representation、prompt/adapter **不是**同一身份；允许一对多但必须显式 | `01/03/04/05` | 静默换工人或笛卡尔积爆炸 |
| `NH-C-31` | 四通道 S06/g0 只消费一份 admitted clean body；g0 original = 该 body | `04/07/08` | 通道分叉 kernel 或 g0 漂移 |
| `NH-C-32` | promptA 仅 `llm_required=True` 强制进 binding；确定性/API map 仍是 clean | `04/05/08` | 强迫 chinatax 上模型或跳过第一环 |
| `NH-C-33` | 绑定后空/空白 `clean_text` 不是成功、不出向量 | `04/09` | empty success 假绿 |
| `NH-C-34` | exhausted-zero collection ≠ empty member ≠ 缺 exhaustion proof | `04/08/09` | 零集合与坏 member 混账 |
| `NH-C-35` | `web.browser_print_pdf.channel=pdf`，不得走 HTML sanitizer | `03/04` | HTTP 打印件被当网页 |
| `NH-C-36` | HTTP 获取的 PDF 不得因 `source_kind=http_resource` 进 web clean | `03/04` | 已有 PDF-first 补丁；回归即污染 |
| `NH-C-37` | FilterMeta 五维不进 `clean_text`/g0 | `04/07` | 检索面污染 traceback |
| `NH-C-38` | 未知 strategy/capability/operation → 409，禁止 duck-type | `04/09` | 暗升第五工人 |
| `NH-C-39` | unit 绿 / 函数存在 / 图对象存在 **都不**等于 live 通道接通 | `04/05/09` | 503 或 monkeypatch 冒充 DoD |

- **5.3 数据 / 控制流贯穿图**：
```text
SourceDescriptor (kind/mode/media)     面01 选图（7 public / 6 unselectable）
        │
        ▼
acquire → typed representation          面03 拥有 print_pdf/text_layer 观察
        │
        ▼
晚绑定清洁工人（T-O-382）              面02 seal；本面拥有 strategy 合同
        │  process_key ──┐
        │                ├── 非 1:1 ── pdf_llm / ocr.local
        ▼                └── promptA 仅 llm_required
intake.dispatch_clean（变换 SSOT）
        │
        ├─ web/pdf/doc → CleanResult.text 非空 + evidence
        └─ API map → N members 各非空 clean_text + 双 digest + 六元组
        │                 空集合+proof → exhausted-zero（G-NH-08）
        ▼
seal / preflight（空 → rejected）
        ▼
admitted clean Artifact ──────────────► 面08 S06/g0 overlay
FilterMeta ───────────────────────────► 面07 revision semantics（不进 g0）
ports clean_llm / browser ────────────► 面05 readiness
```

**消费 / 提供**：

| 方向 | 内容 |
|------|------|
| 本面消费面 `01` | 公开 vs unselectable 身份；kind 图如何声明多 clean 边（不在本面设计 merge） |
| 本面消费面 `03` | typed representation；`print_pdf` 是否被生产；decode 是否再盗用 OCR 码 |
| 本面提供面 `05` | 哪些 strategy 需要 LLM/browser/OCR 端口；CLI 排除 OCR/vision 的事实 |
| 本面提供面 `08` | admitted clean 最小字段；g0=body；API member clean_text |
| 本面提供面 `09` | 空成功/exhausted-zero/PROMPT_HASH_MISMATCH 负例清单 |
| 冲突候选 | `NH-RA04-B03` 与面 `03` 共用 print_pdf；`G-NH-08` 与面 `08/09` 共用终态；`G-NH-04` 运行时边界面 `05` 拥有 |

---

## 6. 净新契约 / 架构边界草案 `[核心]`

> 无先例可借（§3 标 🆕 或 HEAD 仅有碎片）处，从零草拟。**草案，非冻结。**

- **6.1 净新聚合 / 解耦点**：
  - `NH-N-04-01` **admitted-clean 最小证据合同**：跨 10 strategy + API map 的同一 body 合同（非空、digest、capability/strategy evidence、LLM 才含 prompt hash）。HEAD 字段散落在各 handler，无单一 schema 类型。
  - `NH-N-04-02` **compatibility matrix 生成器**：从 registry 行生成合法格 + live 列；禁止手写笛卡尔积。无外部先例要求「process_key 一对多 strategy」。
  - `NH-N-04-03` **空集合 / 空 member 分账账本**：exhausted-zero vs schema-invalid member vs 缺 proof。legacy 把三者都做成某种成功/skip。
  - `NH-N-04-04` **promptA 绑定覆盖规则**（不锁 id 字面）：strategy.prompt_key、snapshot 默认、documentation overlay 三者如何在 binding 时刻对上同一 `PromptRef`。
- **6.2 净新契约叙述规格**：
  - **输入**：typed representation + 已登记 strategy（或 API provider/operation/version）+ 可选 `PromptRef`。
  - **输出**：`admitted_clean { text min_length=1, content_digest, evidence }`；API 为 list，允许 length=0 **仅当** exhaustion proof 已在 acquire evidence。
  - **失败**：空正文 422；缺端口 503（不得当 DoD）；未知键 409；member schema 422 整批。
  - **不输出**：FilterMeta 序列化进 text；R2 key；`plainTextAvailable` 旗标冒充非空。
- **6.3 架构边界（与既有 / 相邻面）**：
  - 变换 SSOT 留在 `intake/`（`D08-T006`）；runtime 只 dispatch/fence。
  - 不在本面选择 PDF/OCR/browser 库（`G-NH-04` / 面 `05`）。
  - 不在本面并图（`T-O-387` / 面 `01`）。
  - 不为通道另写 S06 kernel（`T-O-386` / 面 `08`）。

---

## 7. Substrate-fit / 技术路线过滤 ★ `[核心]`

| 借鉴点 | 原机制（参考处） | 是否冲突本仓路线 / 约束 | 落地形态（降级 / 重映射 / 直采） |
|--------|------------------|--------------------------|-----------------------------------|
| 6 branch 分叉 | legacy `action_registry.ts:91-149` | `action_branch` 与 `T-O-377` 冲突；CF/Gemini 越界 | **重映射**为 acquire × strategy 表（已部分落地为 10 key） |
| FilterMeta 五维 | dedicated schemas | 不冲突；禁止进 g0 | **直采语义**，已在 `semantics.py`；四通道扩展属面 `07` |
| empty success / skip | `plainTextAvailable`；catch return null | 冲突 `T-O-378/383` | **反例**；HEAD `CLEAN_EMPTY` + 整批 422 |
| R2 key 成功 | dispatcher finalizer | 冲突 S13/local Turso、`T-O-42` | **反例** |
| Gemini latest | `gemini-flash-lite-latest` | 冲突 S14 精确 PromptRef / 禁浮动 alias | **反例** |
| GUIDE 确定性/VLM 分账 | arXiv 2608.12133 | 多 agent 云栈越界；schema+provenance 可映射 | **部分借**：分账与 silent_skip 缺陷；不借 HITL 产品 |
| Tesseract empty page | tessdoc | 不选引擎 | **部分借**失败条件；引擎选型面 `05` |
| OCRmyPDF skip 占位 | tesseract.py Empty page!! | 冲突空正文 fail-loud | **反例**（整批 skip） |
| JSON Schema boolean | 2020-12 Core §7.6 | 不冲突 | **直采**：单 member valid/invalid；批策略自定=整批失败 |
| sourcemeta JSONL 首败 | CLI `--continue` | 不引入该 CLI | **部分借**批失败法 |
| Prompt Provenance 个人仓 | SPEC.md v0.1，1 star | 非 IETF/W3C；不得当 prompt 规范 | **线索 / 🆕对照**；身份规则以 HEAD S14 为准 |

本仓过滤摘要：单体 Python 3.12 FastAPI、local Turso、S03 七表无环、eq-only 守卫、S13 bytes-first、`T-O-42` 绿地。能跑但越界（CF/R2/SMCP/动态 plugin）最多 `🔶部分借`。

---

## 8. 反例坑表 + 净新表 `[核心]`

### 8.1 反例坑表 ⛔

| 反例 | 来源锚 | 为什么不可借 |
|------|--------|--------------|
| empty success（`plainTextAvailable: true` 不查 length） | `cleaner_web.ts:321`；`cleaner_doc.ts:140` | `T-O-378/383` 空正文非成功 |
| per-member parse skip | `chinatax/processor.ts:152-155` | 丢失 rejection evidence；HEAD 整批 422 |
| `empty_response` 仍返回成功形 | `realestate/processor.ts:185-192` | 无 exhaustion proof 的假 complete |
| 以 R2 key / output payload 推 `clean_completed` | `finalizer.ts:116-129` | 对象存在 ≠ admitted clean |
| `action_branch` 当 taxonomy | `mapper.ts:198`；universal registry | `T-O-377/379` |
| Gemini 硬绑 + `*-latest` | `gemini.ts:47-61` | 浮动模型；禁 CF 栈 |
| 把 dedicated JSON 当 admitted clean / g0 | D08-T007 反面 | 五维必须分账 |
| OCRmyPDF `[skipped page]` 占位续跑 | OCRmyPDF tesseract.py | 绑定后必须 fail-loud |
| 用 SEO/厂商博客证 D-23 | （本面未采用） | `G-NH-RA-02` |
| 把 33 unit 绿写成四通道 live | `D-23` vs `T-O-381` | `NH-C-39` |

### 8.2 净新表 🆕

| 项 | 为什么无先例 | 草案落点 |
|----|--------------|----------|
| process_key 一对多 strategy 的 **声明式 matrix 生成** | legacy 用单一 branch 同时选抓取+模型；外部 DAG 不表达该 identity 分账 | `NH-N-04-02` / 面 `01` 图边 |
| admitted-clean 跨四通道同一 schema 类型 | HEAD 字段在各 handler 重复；GUIDE 规则库形态不适合 | `NH-N-04-01` §6.2 |
| exhausted-zero **产品终态** 三选一 | HEAD 已有 typed complete；规范不规定业务终态 | `G-NH-08` |
| promptA 三 id 对齐规则 | 无外部「三 catalog 默认互斥」先例；个人 GitHub 草案不足以为规范 | QNA 执行延期 / `NH-N-04-04` |

---

## 9. 验收格栅草案（防假绿）`[核心]`

| 功能 F | 收口目标（一句话可验证） | Test-ID（拟） | 测试层 | 防假绿要点 |
|--------|--------------------------|----------------|--------|------------|
| 闭集 registry | 10 strategy + 9 capability + 3 operation；未知 409 | `NH-A-04-01` | 单元 | 已有；禁止改 D-02 数字凑绿 |
| 非空 admitted clean | 各策略空输入 → typed 422，无向量 | `NH-A-04-02` | 单元 | 补 `CLEAN_EMPTY` 字面；禁止空串当成功 |
| PDF-first | HTTP PDF 永不进 web sanitizer | `NH-A-04-03` | 单元 | 已有；回归锁 |
| API empty member | 缺正文/缺键 → 整批 422 + rejection_evidence | `NH-A-04-04` | 单元 | 禁止 skip；与 zero collection 分测 |
| API exhausted-zero | 有 proof 的 `[]` 可 seal；无 proof 不可 | `NH-A-04-05` | 单元+集成 | 终态断言必须引用 `G-NH-08` 裁决后的期望 |
| identity 反推 | 同 `pdf_llm` 在 `print_pdf` vs 普通 PDF 绑不同 strategy；缺表示不得猜 | `NH-A-04-06` | 集成 | 禁止 handler 暗升 |
| promptA 指针 | strategy.prompt_key 与冻结 PromptRef 不一致 → `PROMPT_HASH_MISMATCH` | `NH-A-04-07` | 单元 | 已有 drift 测；须覆盖 documentation overlay |
| 公开图覆盖 | 7 selector 不能激活 6 张 LLM/print/vision 图 | `NH-A-04-08` | 集成 | 调用方禁 `workflow_key` |
| llm_required live | 默认组合根无 `clean_llm` 时 LLM 策略不得假成功 | `NH-A-04-09` | **default-root e2e** | 禁止 monkeypatch LLM；503 ≠ DoD |
| OCR 公开图 | `local_object.image` 无注入 → 503；注入后空输出 422 | `NH-A-04-10` | default-root e2e | CLI 排除 OCR 必须测到 |
| print-pdf 格 | 无 `representation_kind=print_pdf` 不得声称该 strategy live | `NH-A-04-11` | 集成 | 属面 `03` 生产表示后回归 |
| 四通道到向量 | 每格真实文件/冻结 records → 可检索（非本面独立 mega） | `NH-A-04-12` | retrieval-facet mega | 面 `08/09`；Task succeeded ≠ 可检索 |

---

## 10. 优先级建造建议 + owner-gate 候选 `[核心]`

- **10.1 建造顺序（依赖序，分批不一次性深做）**：

| 顺序 | 工作簇 | 依赖 | 复用判定 |
|------|--------|------|----------|
| `P0-a` | 冻结 compatibility matrix 生成规则（表驱动，非笛卡尔） | `D-02/03/04`；面 `01` 图边 | `✅复用` registry + `🆕` 生成器 |
| `P0-b` | admitted-clean 最小合同（含 API member）+ 空正文负例 | `T-O-386/378`；现 handler | `✅复用` `intake/`；`🆕` 统一 schema |
| `P0-c` | 公开 selector / kind 图纳入 LLM/print/vision 边 | 面 `01` `T-O-387`；本面 B01 | `♻️重 substrate` 图，不重写 clean 函数 |
| `P0-d` | promptA 绑定对齐（**执行延期**，不锁 id；QNA §10.2，不占新 gate） | QNA 执行项 | `♻️重 substrate` S14 |
| `P0-e` | 默认组合根注入 LLM/browser 端口 | 面 `05` `G-NH-04`；本面只列需求 | 端口 `🆕`/`♻️` 由 `05` 判 |
| `P1-a` | print_pdf 表示诚实后激活 `web.browser_print_pdf` | 消费面 `03` `NH-RA03-B02`；供给 `NH-RA05-B07` | `✅复用` pdf handler |
| `P1-b` | `G-NH-08` 裁决后改/锁 exhausted-zero 终态与验收 | 面 `08/09` | `✅复用` scatter zero 路径 |
| `P2` | retrieval mega 证明四通道 | 面 `08/09` | 不在本面施工 |

- **10.2 owner-gate 候选（只 MARK 不裁决 → 上交 index §4 / 下游决策登记）**：

| gate-ID | 决策点 | 候选选项（不预设倾向） | 影响 |
|---------|--------|------------------------|------|
| `G-NH-08` | exhausted-zero registered API 终态 | `typed no-op success` / `distinct no-change terminal` / `explicit empty failure` | scatter/Task/result/vector/metrics；本面 B07 |
| `G-NH-04` | PDF/browser/multimodal runtime 边界（本面 **只 MARK 需求**：7 个 llm_required + print-pdf browser） | `扩既有 inference request/adapter` / `独立本地 adapter 但复用 pool` / `独立 capability supply` | 面 `05` 拥有；本面 B02 解除依赖它 |
| `G-NH-08` 相关澄清（不另开除非 owner 要） | empty member 是否允许「部分成功」 | 今日 HEAD=整批失败；若 reopen 才需要新 gate。本面 **不**新增选项倾向 | 与 JSON Schema 灰区对照 |

promptA 三套 catalog 默认 id 对齐：**不占**新 `G-NH-*`（QNA §10.2 已标执行延期）。本面不锁 id 字面/正文版本。`G-NH-11` 留给面 02 seal 事务。

未在本面改写 `G-NH-01..10` 既有选项列表。

---

## 11. 核验记录 `[核心]`

| 锚点（host-ID） | 是否核验 | 方式（grep/read/run） | 备注 / 修正 |
|------------------|----------|------------------------|--------------|
| `D-02/03/04/06` | `✅` | `uv run python` 分母脚本 | 10/9/3/7+6；与 index 一致，未改写 |
| `D-23` | `✅` | pytest collect 33 + run 33 passed | **本面复测 2026-08-29** 与冻结值一致 |
| `D-24` | `未` 复跑 | 引用 index | e2e 超时风险；不假装全绿 |
| `D-21` clean_llm/browser | `✅` | read `api/app.py:330-345`；grep `clean_llm` 无命中 | 组合根未注入 |
| `RA-04-HEAD-01..13` | `✅` | read_file 后以本次行号为准 | 未抄 prompt 里可能漂移的行号 |
| promptA 三哈希 | `✅` | python hashlib 三文件 | 471/802/791 字节互斥 |
| `T-O-378/381/383/386` | `✅` | read QNA `:82-90,:469-524` | 只 CITE |
| `D08-T002/T007/T009` | `✅` | read D08 `:93-100` | T009 缺 pdf.ocr → B10 |
| legacy universal 6 分叉 | `✅` | read `action_registry.ts:91-149`；`cleaner_web.ts:228-329`；`cleaner_doc.ts:111-151` | 未运行 TS |
| legacy dedicated skip/empty | `✅` | read chinatax/domain/rea processor 标注行 | `return null` / `empty_response` |
| legacy dispatcher R2 | `✅` | read `finalizer.ts:106-129`；`mapper.ts:193-200` | |
| GUIDE 2608.12133 | `✅` | web_search + web_fetch HTML | 2026-08-12；访问 2026-08-29 |
| tessdoc ImproveQuality | `✅` | web_fetch | empty page = 过大边框 |
| OCRmyPDF tesseract.py | `✅` | web_fetch raw GitHub | skip 占位 = 对 MKB 反例 |
| JSON Schema 2020-12 §7.6 | `✅` | web_fetch core | 规范单源；boolean valid |
| sourcemeta validate.md | `✅` | web_fetch GitHub | JSONL 首败；`--continue` 灰区 |
| Prompt Provenance SPEC | `✅` | web_fetch GitHub；kineticgain.com **失败** | 标 draft；未用失败 URL 作锚 |
| NIST SP 800-88 / TrueSection / navi-sanitize | `✅` 检索后 **不用** | web_search | 媒体擦除 / 无障碍 PDF / Unicode 库，与本面 document-clean 合同不 substrate-fit，避免硬凑 |
| `initial-planning` `T-P-NH-10` | `部分` | 只作叙事对照 | 不当地为已冻结对齐方案 |

---

## 12. 收尾 Verdict 与交接 `[核心]`

- **本面裁定**：clean **变换闭集已交付**（10/9/3 + 33 绿），**激活与合同未闭合**。最大的三个 S1 是：公开图漏 LLM/print/vision（`NH-RA04-B01`）、默认根无推理端口且 promptA 三 id 互斥（`NH-RA04-B02/B04`）、print-pdf 与 process_key 一对多造成死合同/错绑（`NH-RA04-B03/B05`）。总体方向 = 激活闭集 + 补 admitted-clean 合同，**禁止重写 `intake/`**。
- **交接下游**：缺口台账（§4）→ 规划；净新契约（§6）→ 设计；owner-gate（§10.2 `G-NH-08/04/11`）→ 决策登记；验收格栅（§9）→ 执行计划。面 `05` 消费本面端口需求；面 `08` 消费 admitted clean；面 `03` 必须先让 `print_pdf` 与 decode 观察成为真事实。
- **冻结前置**：① review-fleet 复核三渠道锚与行号；② 与面 `01/03/05` 对账 B01/B03/B02；③ owner 未裁 gate 前不得把 exhausted-zero 终态或 promptA id 写进 frozen 设计；④ 本文件保持 `draft`，禁止标 `frozen`/`reviewed`。

---

## 附录 A · 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-08-29 | Grok analysis-fleet / review-fleet | 初稿（measure-first + 借鉴矩阵 + 缺口台账）；HEAD `1221aa1`；D-23 本面复测 33/0 |
| v0.2 | 2026-08-29 | Grok fix-fleet | 吸收已核实 review：R2-I02 FilterMeta 降 `🔶部分借`；R2-I08 双 hash 钉 `processor.ts:169-181`；R2 §5 补隧道/sanitizer/regex/空列表/skip/暗路由；R3-I04 WEB-06 降为线索；R3-I14 OCRmyPDF 标明 unpinned main；R4-I07 P1-a 改消费 `NH-RA03-B02`；R4-I01/QNA 撤销本面 `G-NH-11`（执行延期）；B02/B03 改为消费 05-B01/03-B02。状态仍 `draft` |

## 附录 B · 本面回答的五个强制问题（索引）

| # | 问题 | 落点 |
|---|------|------|
| 1 | 合法 compatibility matrix 如何生成？ | §2.3 生成器 + 表；禁止笛卡尔积 |
| 2 | 每个 strategy 的 admitted clean / evidence 最小合同？ | §2.4 表 |
| 3 | API exhausted-zero 与 empty member 如何分账？ | §2.6；`G-NH-08` |
| 4 | 哪些 capability 已有纯函数但选不中 / 未注入端口？ | §2.3 live 列；§2.7；B01/B02 |
| 5 | promptA 三套默认 id 分叉事实？ | §2.5；**不锁对齐方案**；QNA §10.2 执行延期 |
