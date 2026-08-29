# 调查面 `05` · PDF/browser/multimodal runtime 供给、readiness 与安全 — 深度评估

> **对象 / scope-fence**：PDF parser process isolation；browser binary/driver；print PDF 供给；multimodal request/adapter/model 运输；资源池/预算/readiness；依赖与许可证；安全边界（恶意 PDF / 浏览器逃逸）。**本面不含**：改变 clean strategy 或路由 taxonomy（交由面 `04`/`01`）；不定产品路由；不冻结具体库/模型/HTTP 路径。
> **日期**：`2026-08-29`
> **作者**：`Grok analysis-fleet / review-fleet`（fleet / panel：`new-harvest-reference-anchor`）
> **文档性质**：`assessment / analysis`（单面 measure-first 深评；零决策——只 MARK 不裁决）
> **文档状态**：`draft`
> **流水线位置**：站② · 上游 = [[assessment-index]]（消费其冻结分母）
> **对照参考**：HEAD `1221aa1`；`docs/baseline/domain-truth/S11-inference-runtime.md`；`S16-security-trust-boundary.md`；`D08-legacy-capabilities-migration.md`；`context/legacy-family` 仅 ReferenceAnchor（`T-O-42`）；公开 primary sources（访问日 `2026-08-29`）
> **上游权威输入**：
> - `docs/eval/new-harvest/assessment-index.md` — §2.2 `D-20/D-21/D-22/D-23`；§3.05；`G-NH-04` / `G-NH-10`
> - `docs/eval/new-harvest/pre-initial-planning-qna.md` v0.5 — `T-O-376` / `T-O-378` / `T-O-381`（只 CITE，不扩冻、不把 QNA 当已实现）
> - `docs/eval/new-harvest/initial-planning.md` — `T-P-NH-6`（叙事/初判，**不是**真相）
> **下游消费者**：`docs/eval/new-harvest/planning-proposed.md` · `pre-charter-qna.md`（owner-gate 裁决）· 设计/执行制品
>
> **图例**：借鉴 verdict = `✅借` / `🔶部分借` / `⛔反例` / `🆕净新`；复用判定 = `✅复用` / `♻️重 substrate` / `🆕净新`；缺口严重度 = `S1 阻断` / `S2 重要` / `S3 次要`；置信 = `HEAD 实测 > 仓内文档锚 > 外部参考`。
> **邻面冻结前置**：本面冻结前应消费面 `03` representation protocol 与面 `04` clean port。截至本文件落盘，`docs/eval/new-harvest/reference-anchor/` 内 **无** `assessment-analysis-03-*` / `assessment-analysis-04-*`；下文对邻面合同只 MARK「待对账」，不替邻面设计。

---

## 0. Verdict（结论先行）`[核心]`

- **0.1 一句话缺口 / 现状判断**：HEAD 已有 **可注入端口、三调度池、ConcurrencyGate、EgressPolicy、SupplyFence、CLI 子进程与诚实拒 binary**，但默认组合根 **未注入** `browser_fetcher`/`clean_llm`，生产依赖 **无** PDF/browser/OCR 专用包，`GenerateRequest`/`LocalVllmAdapter` **不能运输 PDF/image bytes**，readiness **不证明** 二进制/模型/许可证在场——`T-P-NH-6`「复用现有推理面即可」在 **请求协议层被证伪**；「不新开第四调度池」仍只是 owner 选项，不是已证实机制。
- **0.2 Top blockers（最关键断点）**：
  1. `NH-RA05-B01` / `NH-RA05-B02`：默认进程既无 browser/PDF/OCR 供给，也无专用依赖 → `T-O-376`/`T-O-381` 的 browser / 真 PDF 文本层 / OCR / Vision / print-PDF 在默认组合根上物理不可 live。
  2. `NH-RA05-B03` / `NH-RA05-B04`：S11 `GenerateRequest` 仅 `input_text`；Claude CLI 对 blob/`application/pdf` 抛 `CLEAN_MEDIA_UNSUPPORTED`；OCR/Vision 虽走 `CleanLanguageModel.complete(..., blob=)` 合同，但生产 adapter **没有** binary 运输。
  3. `NH-RA05-B05` / `NH-RA05-B06`：`/ready` 的 `inference_binding` 默认不探、探也只是 `GET /v1/models` 名单；PDF 解码在 **同进程正则** 上跑恶意输入；无 browser sandbox、无隔离线裁决。
- **0.3 总体方向建议（不裁决）**：PDF parser、browser/print、OCR/Vision 的 **供给身份必须与 strategy 分账**（无论 `G-NH-04` 哪一选项）。调度层只 **MARK**「扩既有 inference request/adapter / 独立本地 adapter 但复用 pool / 独立 capability supply」三选，**无推荐赢家**；请求协议与隔离线另开 `G-NH-04` / `G-NH-10` / `G-NH-15`。**禁止**把流行库名冻进本文件，也 **禁止**把「独立 capability supply」读成本文已选。
- **0.4 如何读本台账**：主题轴 = `供给注入` / `请求协议与模型运输` / `调度池与预算` / `readiness 诚实性` / `隔离与许可证` / `print-PDF vs page-render`。

---

## 1. 方法与证据基线 `[核心]`

> 先证可证性，再下判断。`T-O-376..389` 与 `T-P-NH-*` **不是** HEAD 已实现。

- **1.1 本仓证据（如何测量）**：
  - 冻结分母：`docs/eval/new-harvest/assessment-index.md` §2.2 `D-20=7/0`、`D-21=0/0`、`D-22=6/3`、`D-23=33 passed`（本面不另估）。
  - HEAD grep + `read_file`：`pyproject.toml`、`api/app.py`、`src/runtime/intake/{core,clean_preflight,acquisition_ingest,types}.py`、`src/contracts/inference/models.py`、`src/runtime/inference/{facade,claude_cli,supply}.py`、`src/llm_adapters/local_vllm.py`、`src/runtime/{health,security,http_acquisition,workflow/dispatch,config,metrics}.py`、`intake/{types,pdf,doc,web}`、`src/contracts/intake/strategies.py`。
  - 本面新测脚本：`GenerateRequest` 字段、`DispatchPool` 名集、`pool_kind`、`HealthAggregator.REQUIRED`、组合根关键字、CLI 拒 binary、vLLM `content` 形状（§2.1）。
  - 小集合 pytest：`test_non_text_blob_is_rejected` + 两则 `test_pdf_clean`（2026-08-29，3 passed）。**未**重跑 index `D-23`/`D-24` 全量。
- **1.2 外部 / 参考来源 + 置信**：

| 搜索词 | Primary URL | 版本/发布 | 访问日 | 支持的原子结论 | 限制/失败条件 |
|--------|-------------|-----------|--------|----------------|----------------|
| `pypdf license Apache official` | https://pypdf.readthedocs.io/en/latest/meta/faq.html ；https://pypi.org/project/pypdf/ | FAQ 标 BSD-3-Clause；PyPI 6.16.2 license expression `BSD-3-Clause`（2026-08-23） | 2026-08-29 | 类别「纯 Python PDF 库」许可证为 **BSD-3**，**不是**检索词里的 Apache | 加密/AES 需 extra；CVE-2025-66019 等 DoS |
| `CVE-2024 PDF parser` / NVD | https://github.com/advisories/GHSA-m449-cwjh-6pw7 ；NVD CVE-2025-66019 | pypdf `<6.4.0` LZW 可耗至约 1GB/stream；patched `6.4.0` | 2026-08-29 | 进程内 PDF 解析必须假设恶意样本可打 CPU/RAM | NVD 页本次抓取空壳；以 GHSA 为权威 |
| `pdfminer.six license MIT official` | https://github.com/pdfminer/pdfminer.six/blob/master/LICENSE | MIT；release `20251230` 修 CVE-2025-64512 pickle CMap | 2026-08-29 | 另一纯 Python 文本抽取路线 = MIT | 历史上 pickle CMap 可任意代码执行 |
| `poppler pdftotext sandbox untrusted PDF` | https://lists.freedesktop.org/archives/poppler/2017-April/012176.html ；https://securitylab.github.com/advisories/GHSL-2025-054_poppler/ ；CVE-2026-10118 | Poppler **GPL**；CVE-2025-52886 UAF；CVE-2026-10118 Splash heap overflow | 2026-08-29 | 链接进专有仓有 GPL 传染风险；untrusted PDF 需要沙箱 | gitlab README 本次被 Anubis 拦截；fossies README 401 |
| `MuPDF license AGPL Artifex official` | https://mupdf.readthedocs.io/en/latest/license.html | MuPDF 1.28.3 GNU AGPL + 商业许可 | 2026-08-29 | 链入/SaaS 触发 AGPL 源码披露 | 商业许可是规避路径，本仓未买、本文不选 |
| `Playwright docker security no-sandbox official` | https://playwright.dev/docs/docker ；https://github.com/microsoft/playwright/blob/main/LICENSE | Docker 文档对 v1.62.0-noble；LICENSE Apache-2.0 | 2026-08-29 | root 会关 Chromium sandbox；untrusted 站点要非 root + seccomp | 官方镜像「不建议用来访问 untrusted websites」 |
| `Chrome Page.printToPDF paperWidth official` | https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-printToPDF | CDP tot `Page.printToPDF` | 2026-08-29 | print-PDF 与 screenshot 同属 Page 域；`paperWidth` **Defaults to 8.5 inches**；`printBackground` 默认 false；`transferMode`/`generateTaggedPDF` Experimental | CDP 页 **无** `paperWidth<=0` 失败句；该失败条件未给出 Chromium 源 URL，本轮删除 |
| `Tesseract empty output return code official` | https://tesseract-ocr.github.io/tessdoc/ ；OCRmyPDF `tesseract.py` 对 `Empty page!!` | Apache-2.0；空页 stderr `Empty page!!`，exit 不一定非 0 | 2026-08-29 | OCR 空输出 **不是**成功；readiness 不能只看 binary 存在 | tessdoc FAQ 未把 return code 钉成稳定 ABI |
| `vLLM OpenAI compatible multimodal` | https://docs.vllm.ai/en/latest/features/multimodal_inputs.html ；openai_compatible_server Chat API | latest preview 2026-08-29 | 2026-08-29 | 线上 multimodal 走 `content[]` + `image_url`/`data:` URI，**不是**纯 string `input_text` | `--allowed-media-domains` 防 SSRF；HTTP 拉图默认 5s |
| `OpenAI vision image input official` | https://developers.openai.com/api/docs/guides/images-vision | 官方 Vision 指南 | 2026-08-29 | 协议要 `input_image` / `image_url` / base64 data URL | 小字/旋转/非拉丁 OCR 会错；CAPTCHA 被拦 |
| `Cloudflare Workers CPU memory limits official` | https://developers.cloudflare.com/workers/platform/limits/ | last updated 2026-07-28 | 2026-08-29 | isolate **128 MB**；超限 Error 1102 | 本仓禁止回流 CF 栈；只作「browser 必须独立供给」反例 |

- **1.3 ★ 可复现命令清单（measure-first）**：
```bash
# 共享分母 D-20（不得改写）
nl -ba pyproject.toml | sed -n '5,28p'
# 默认组合根 D-21
nl -ba api/app.py | sed -n '244,266p;319,345p;168,199p'
nl -ba src/runtime/intake/core.py | sed -n '39,75p'
# 请求协议 / CLI / adapter
nl -ba src/contracts/inference/models.py | sed -n '18,21p;96,118p'
nl -ba src/runtime/inference/claude_cli.py | sed -n '289,340p;423,440p;490,519p'
nl -ba src/llm_adapters/local_vllm.py | sed -n '207,247p;276,297p'
# 池 / readiness / egress
nl -ba src/runtime/workflow/dispatch.py | sed -n '12,43p;122,172p'
nl -ba src/runtime/health.py | sed -n '16,25p'
nl -ba src/runtime/security.py | sed -n '319,414p'
# 本面新测
uv run python - <<'PY'
from src.contracts.inference.models import GenerateRequest, InferenceCapability
from src.runtime.workflow.dispatch import DispatchPool, pool_kind, GENERATE_PROCESS_KEYS
from src.runtime.health import HealthAggregator
print("fields", sorted(GenerateRequest.model_fields))
print("blob", [f for f in GenerateRequest.model_fields if f in {"blob","image","media_type","parts"}])
print("caps", InferenceCapability.__args__)
print("pools", DispatchPool.__args__)
print("required", HealthAggregator.REQUIRED)
for k in ["clean.ocr.local","clean.extract.vision","intake.acquire.http_browser","clean.extract.pdf_llm"]:
    print(k, pool_kind(k))
print("generate_keys", sorted(GENERATE_PROCESS_KEYS))
PY
# 诚实拒 binary / 缺 LLM fail-closed
uv run pytest tests/unit/test_ns5_phase3.py::test_non_text_blob_is_rejected \
  tests/intake/test_pdf_clean.py::test_pdf_without_llm_or_text_fails_closed \
  tests/intake/test_pdf_clean.py::test_pdf_ocr_is_a_distinct_explicit_strategy -q --tb=line
```
- **1.4 范围围栏**：本面**只**覆盖 runtime 供给/readiness/安全/许可证/隔离候选；**不含** representation 观察法（面 03）、strategy 闭集与 admitted clean（面 04）、upload CAS（面 06）、assurance mega（面 09）。禁止第五 source kind、CF/R2/SMCP、动态 plugin、自由表达式。

---

## 2. 当前结构分析（HEAD 实测 · measure-first）★ `[核心]`

### 2.1 ★ 冻结分母（FROZEN denominators · HEAD）

| 分母 | HEAD 实测值 | 证据锚（`path:line`） | 来源 |
|------|-------------|------------------------|------|
| `D-20` 直接生产依赖 / PDF-browser-OCR 专用 | `7 / 0` | `pyproject.toml:13-21`（fastapi/starlette/httpx/pydantic/pydantic-settings/pyturso/uvicorn）；无 pypdf/playwright/ocr | `index §2.2` |
| `D-21` 默认组合根 `browser_fetcher` / `clean_llm` 注入 | `0 / 0` | `api/app.py:332-345` 关键字无二者；`src/runtime/intake/core.py:45-51` 端口存在但默认 `None` | `index §2.2` |
| `D-22` legacy universal / dedicated 分叉 | `6 / 3` | 本面只消费：universal 6 branch 含 browser/PDF/Gemini；dedicated 3 无 browser/PDF parser | `index §2.2` |
| `D-23` 选定 clean/provider unit+intake 水位 | `33 passed / 0 failed` | 本面不重跑全量；2026-08-29 复跑 3 条相关 unit = passed | `index §2.2` |
| `D-02` CleanStrategyKey | `10` | `src/contracts/intake/strategies.py:15-25` | `index §2.2`（喂 05，不另估） |
| `D-05-F01` `GenerateRequest` blob/image/parts 字段 | `0` | `models.py:96-108` 字段 = `prompt_ref,prompt_digest,input_text,system_text` + 继承 `binding/invocation/payload_extra/team_uuid` | 本面新测 |
| `D-05-F02` CLI 非 `text/*` / 纯 blob 支持 | `0`（显式拒绝） | `claude_cli.py:505-508` `CLEAN_MEDIA_UNSUPPORTED` | 本面新测 |
| `D-05-F03` `DispatchPool` 闭集 | `3`：`local-inference` / `non-interactive` / `embed` | `dispatch.py:42-43,91-94` | 本面新测 |
| `D-05-F04` `HealthAggregator.REQUIRED` 覆盖 browser/pdf/ocr/binary | `0 / 9` | `health.py:16-25` 九项均无 browser/pdf/ocr | 本面新测 |
| `D-05-F05` `InferenceCapability` 闭集 | `4`：embed/rerank/structured_generate/text_generate；**无** vision/ocr | `models.py:18` | 本面新测 |
| `D-05-F06` `pool_kind(clean.ocr.local)` / `clean.extract.vision` / `http_browser` | `unpooled` / `unpooled` / `unpooled` | `dispatch.py:122-146`；`GENERATE_PROCESS_KEYS` 含 `pdf_llm/doc_llm/web_llm` **不含** ocr/vision | 本面新测 |
| `D-05-F07` 默认 enabled generate binding 是否 VL | `0` | `registry.py:126-132` generate = `unsloth/Qwen3.8-27B-NVFP4` + Nemotron Lightning；VL 仅 embed key `Qwen3-VL-Embedding-2B` | 本面新测 |
| `D-05-F08` `inference_probe_enabled` 默认 | `false` | `config.py:40-41`；仅 `live_inference` 或显式 probe 才走 `probe_binding`（`app.py:183-189`） | 本面新测 |

### 2.2 轴 A · 端口与组合根供给（HEAD 核验）

- 组合根 **故意** 把 browser 与 HTTP 分开：`IntakeCoreMixin` 注释写明不得 fallback 到 static HTTP，以免伪造 rendered provenance（`core.py:66-70`）。这是正例端口形状。
- `api/app.py:332-345` 的 `IntakePipeline(...)` 注入 `http_fetcher`、`inference`、`claude_cli`，**没有** `browser_fetcher=` / `clean_llm=`。默认部署上 browser acquire 走 `ACQUISITION_BROWSER_CAPABILITY_UNAVAILABLE` 503（`acquisition_ingest.py:477-485`）。
- `clean_preflight.py:75-107`：OCR/Vision **禁止** CLI 兜底（`cli_clean_supported = process_key not in {ocr, vision}`）；text LLM 策略在未注入 `clean_llm` 时可降到 `ClaudeCliCleanLanguageModel`。因此「有 claude_cli」≠「OCR/Vision 已接线」。
- `intake/pdf/__init__.py:37-56` 与 `intake/doc/__init__.py:58-72`：OCR/understanding **同一** `CleanLanguageModel.complete(..., blob=, media_type=)` 端口；缺注入 → `CLEAN_LLM_UNAVAILABLE` / `CLEAN_OCR_CAPABILITY_UNAVAILABLE` 503。QNA §2.2 叙事「OCR/Vision 不是独立引擎」描述的是 **端口形状**，不是 live 能力。
- e2e `tests/e2e/test_source_capability_paths.py:99-101` 把 `_browser_fetcher` monkeypatch 成返回 HTML 字符串。这是假绿（`T-O-378`），不能当 browser 供给证据。

### 2.3 轴 B · 请求协议与模型运输（HEAD 核验）→ `T-P-NH-6` 证伪点

- `GenerateRequest`（`models.py:96-108`）只有 `input_text`/`system_text`。`StrictModel` `extra=forbid`（`contracts/common/models.py:20-24`）。`payload_extra` 禁 `prompt/content/vector`（`models.py:63-70`），adapter **从不**读它来传图。
- `LocalVllmAdapter.generate` 把 user 消息做成 `{"role":"user","content": request.input_text}`（`local_vllm.py:207-216`）——string content，无 `image_url` / parts。
- S11-E02 明文「无万能 `invoke(model, blob)`」（`S11-inference-runtime.md:161`）；S11-T002 能力闭集四项（同文件 `:88-91`）。S11-E02 embed 行写「texts[] 或 multimodal parts」，但 HEAD `EmbeddingRequest` 只有 `texts: list[str]`（`models.py:78-82`）——文档与代码不对齐，登记为仓内冲突，不以 S11 覆盖 HEAD。
- `ClaudeCliCleanLanguageModel.complete`（`claude_cli.py:497-519`）：非 `text/*` media 或「有 blob 无 text」→ `CLEAN_MEDIA_UNSUPPORTED` 422。单元测试 `test_ns5_phase3.py:112-115` 用 `%PDF-1.4` 固定这条负能力。
- 结论：**复用现有 pool ≠ 请求协议可不扩。** `T-P-NH-6`「OCR / Vision / promptA 运输复用已有推理面」在运输层 **证伪**。调度层「不新开第四 `DispatchPool` 名」仍可 MARK（见 2.4），不得偷换成「现有 GenerateRequest 已够」。

### 2.4 轴 C · 调度池、闸与预算（HEAD 核验）

- 三池名闭集：`local-inference` / `non-interactive` / `embed`（`dispatch.py:42-43`）。`ConcurrencyGate` 在组合根按 embed / structured_generate / text_generate / **cli** 限额（`app.py:244-261`）。`InferenceFacade` 自己的 `capability_limits` **不含** `cli`（`app.py:257-261`），CLI 走共享 `inference_gate` 的 `"cli"` key。
- `GENERATE_PROCESS_KEYS` 含 `clean.extract.{web,doc,pdf}_llm` 以及 structurize/construct/transcribe（`dispatch.py:20-28`）。`clean.ocr.local`、`clean.extract.vision`、`intake.acquire.http_browser` 的 `pool_kind` = **`unpooled`**。
- 因此「第四调度池」今天 **还不存在**；OCR/Vision/browser acquire **也还没进现有三池**。把它们并入 `local-inference` 是一种选项，不是现状。
- 字符预算 `DISPATCH_LOCAL_CHAR_BUDGET=16000`（`dispatch.py:18`）针对 generate 文本，**不是** 20MiB PDF blob 预算（strategy `max_input_bytes=20MiB`，`strategies.py:45`）。

### 2.5 轴 D · Readiness 诚实性（HEAD 核验）

- `HealthAggregator.REQUIRED`（`health.py:16-25`）：schema_migration / registry_bootstrap / db_primary / write_path_ready / native_vector / object_root / **inference_binding** / obs_tables / sec_token_loaded。**没有** browser、pdf parser、ocr binary、vision model。
- `_probe`（`app.py:168-199`）：`inference_binding` 默认等于 `registry_ok`；仅当 `inference_probe_enabled or live_inference` 才对 **active bindings** 调 `probe_binding`。`LocalVllmAdapter.probe` = `GET {base}/v1/models` 且 `id == model_key`（`local_vllm.py:276-295`）。这证明 **目录里有模型名**，不证明 generate-with-image、不证明能消化恶意 PDF、不证明 Chromium/Tesseract 在场。
- `S11-T014`「readiness：local binding 可探测」（S11 `:101`）说的是 **已登记 inference binding**，不是 PDF/browser 供给。用 `/v1/models` 200 冒充四通道 live，属于假绿。
- README K5 已诚实记录 browser/OCR/Vision 未注入（`README.md:614`）。

### 2.6 轴 E · PDF 解码、print-PDF、安全边界（HEAD 核验）

- `_extract_pdf_text`（`types.py:144-171`）是 `local-pdf-literal-text.v1` 正则抠未压缩字面量；无字面量抛 `CLEAN_OCR_CAPABILITY_UNAVAILABLE` 422（盗用 OCR 码，`T-O-378`）。注释承认不是 permissive renderer（`types.py:100-106`）。**同进程、无 sandbox、无加密探测字段。**
- acquire 只写 `representation_kind: rendered|transferred`（`acquisition_ingest.py:535-536`），**从不**写 `print_pdf`。`clean_preflight.py:46-62` 却用 `print_pdf` 把 `clean.extract.pdf_llm` 解成 `web.browser_print_pdf`。print 供给在 runtime 上是死键（产品表示属面 03；本面钉 **没有 print-to-PDF 二进制路径**）。
- HTTP 出站有 `EgressPolicy` fail-closed（`security.py:319-414`；`http_acquisition.py:1-7`）：禁 userinfo、metadata host、默认禁 literal IP/private、redirect≤3、DNS 后再校验。这是 **URL fetch** 围栏，**不**覆盖 in-process PDF 或 browser 渲染器自己的出站。
- Claude CLI 是 `asyncio.create_subprocess_exec`、无 shell、stdin 运正文、超时 terminate→kill（`claude_cli.py:289-337,423-440`）。这是 **可借的隔离形状**，今日只服务 text CLI，不服务 PDF parser/browser。
- `SupplyFence`（`supply.py:98-136`）禁 silent 换 endpoint/adapter。与 G-10 / `S16-T012` 一致。不能替代「二进制在不在」。
- `web.browser_print_pdf` 定义 `browser_required=True` 且 channel=`pdf`（`strategies.py:67-76`）。缺 browser 供给则该格不能 live（`T-O-381`）。

### 2.7 必须回答的五问（本面合同）

| # | 问题 | HEAD 结论 | 对 `T-P-NH-6` / gate |
|---|------|-----------|----------------------|
| 1 | 「复用现有 pool」是只不增调度池，还是连请求协议也不扩？ | 今日三池名闭集；OCR/Vision **未入池**。请求协议 **不能** 运 blob。 | 运输层 **证伪** `T-P-NH-6`；「不增第四池名」仍 OPEN（`G-NH-04`） |
| 2 | readiness 如何证明 binary 能力真实在场？ | 现状：registry + 可选 `/v1/models` 名单。需要的是 **负向样本**（加密 PDF、扫描件、恶意 PDF、无文本层、SPA、sandbox 逃逸、空 OCR）+ 许可证/模型 identity，不是 `which chromium` / import 成功 | `NH-RA05-B05`；验收 §9 |
| 3 | 恶意 PDF / 浏览器逃逸的隔离线在哪？ | HEAD：PDF **in-process**；browser **不存在**；CLI 已是 subprocess。候选只 MARK：`in-process` / `isolated subprocess` / `sidecar-local`，且 **逐能力裁**（`G-NH-10`） | 不裁决 |
| 4 | print-to-PDF 是否必须与 page-render 同一 browser 供给？ | CDP 上二者同属 Page 域；legacy 用 CF `/content` 与 `/pdf` 两个 HTTP 但仍是同一 Browser Rendering 产品。本仓无供给。 | `G-NH-15` MARK 同供给 / 分供给；不选驱动 |
| 5 | 现有 Claude CLI / InferenceFacade 能否运输 PDF bytes？ | **不能。** `GenerateRequest.input_text`；vLLM string `content`；CLI `CLEAN_MEDIA_UNSUPPORTED` | `NH-RA05-B03/B04` |

---

## 3. 借鉴锚定矩阵（Reference Anchor Matrix）★ `[核心]`

> 每条含：结论原子句 / 来源与版本或访问日 / 正例或反例 / 置信 / substrate-fit / 命中缺口。

| 借鉴点 | 来源锚（`path:line` / URL） | 借鉴 verdict | 借什么 / 不借什么 |
|--------|------------------------------|--------------|--------------------|
| `RA-05-HEAD-01` 端口三分：http / browser / clean_llm | `core.py:45-51,66-70`；`acquisition_ingest.py:477-485` | `✅借` | **借**：browser 缺失必须 fail-loud，禁止用 HTTP 伪造 rendered。**不借**：把 503 当 `T-O-376` DoD |
| `RA-05-HEAD-02` 三池 + ConcurrencyGate | `dispatch.py:42-43`；`app.py:244-266`；`facade.py:102-132` | `🔶部分借` | **借**：有界闸、BACKPRESSURE、不增第四池名的 **选项空间**。**不借**：误认 OCR 已在 generate 池 |
| `RA-05-HEAD-03` HTTP egress 宪法 | `security.py:319-414`；`S16-T038..T043` | `✅借` | **借**：fail-closed SSRF。**不借**：当作 PDF/browser 进程隔离 |
| `RA-05-HEAD-04` CLI 诚实拒 binary | `claude_cli.py:505-508`；`test_ns5_phase3.py:112-115` | `✅借` | **借**：不把 PDF header 当文本成功。**不借**：把拒斥当成「已有 vision」 |
| `RA-05-HEAD-05` SupplyFence 禁 silent swap | `supply.py:118-136` | `✅借` | **借**：binding-only 出站。**不借**：名单 probe 当能力证明 |
| `RA-05-HEAD-06` CLI subprocess terminate/kill | `claude_cli.py:320-337,423-440` | `🔶部分借` | **借**：无 shell、超时杀子进程的 **形状**。**不借**：今日 CLI 只能运 text |
| `RA-05-HEAD-07` `CleanLanguageModel` 已声明 blob | `intake/types.py:59-69`；`intake/pdf/__init__.py:43-55` | `🔶部分借` | **借**：clean 端口已预留 blob。**不借**：生产 adapter 已实现 |
| `RA-05-HEAD-08` 缺 LLM/OCR fail-closed | `intake/pdf/__init__.py:37-50`；`test_pdf_clean.py:42-45,70-79` | `✅借` | **借**：typed 503/空成功禁。**不借**：503=战役完成 |
| `RA-05-HEAD-N01` 组合根未注入 | `api/app.py:332-345` | `⛔反例`（现状） | 默认进程无 browser/clean_llm → `NH-RA05-B01` |
| `RA-05-HEAD-N02` GenerateRequest 仅文本 | `models.py:96-108`；`local_vllm.py:207-216` | `⛔反例` | 证伪「协议不扩」→ `NH-RA05-B03` |
| `RA-05-HEAD-N03` pyproject 无专用依赖 | `pyproject.toml:13-21` | `⛔反例` | 默认进程不可能 live PDF-layer/browser/OCR → `NH-RA05-B02` |
| `RA-05-HEAD-N04` readiness 无 binary 项 | `health.py:16-25`；`app.py:183-189`；`local_vllm.py:276-295` | `⛔反例` | `NH-RA05-B05` |
| `RA-05-HEAD-N05` 同进程字面量 PDF | `types.py:100-171` | `⛔反例` | 无隔离、无加密观察、盗用 OCR 码 → `NH-RA05-B06`；表示谎言交面 03 |
| `RA-05-HEAD-N06` 从不产 print_pdf | `acquisition_ingest.py:535-536` vs `clean_preflight.py:46-62` | `⛔反例` | 无 print 供给 → `NH-RA05-B07` |
| `RA-05-HEAD-N07` OCR/Vision unpooled | `dispatch.py:20-28,122-146` | `⛔反例`（相对 T-P-NH-6 叙事） | 既非第四池、也未复用三池 → `NH-RA05-B08` |
| `RA-05-HEAD-N08` e2e monkeypatch browser | `test_source_capability_paths.py:99-101` | `⛔反例` | 假接线；`T-O-378` |
| `RA-05-LEGACY-01` inline bytes 进多模态 | `context/legacy-family/smind-skill-clean-universal/cloudflare_ai/providers/gemini.ts:213-217` | `🔶部分借` | **借**：`text` + `inlineData{mimeType,data}` 才是真实 binary 协议。**不借**：Gemini 别名、AI Gateway、API key **轮询**（钉 `gemini.ts:88-101` `getApiKey` 轮询 `GEMINI_API_KEYS` / 2ND / 3RD） |
| `RA-05-LEGACY-02` 缺能力要 fail-loud + 20MiB | `cleaner_doc.ts:40,73-82,125-128` | `🔶部分借` | **借**：size cap、未知 branch 抛错。**不借**：`plainTextAvailable=true` 无非空检查；`action_branch` |
| `RA-05-LEGACY-03` browser 是独立供给 | `cleaner_web.ts:99-123,152`；`smind-console/functions/lib/browser-renderer.ts:1,64-86` | `🔶部分借` | **借**：content vs pdf 都要独立 browser 产品；同一 Chromium 可 `page.pdf`。**不借**：`@cloudflare/puppeteer`、Workers binding |
| `RA-05-LEGACY-04` CF/R2/Gemini 硬绑 | `action_registry.ts:91-148`；`wrangler.toml:6-41` | `⛔反例` | `T-O-42`/`T-O-377`：零 CF/R2/SMCP runtime |
| `RA-05-WEB-14` Worker isolate 128 MB（**WEB 规范，不是 legacy 代码**） | `https://developers.cloudflare.com/workers/platform/limits/` Last updated Jul 28, 2026；访问 2026-08-29；Memory per isolate = 128 MB；超限 Error 1102 | `⛔反例` | 证明 browser/PDF **必须独立供给**；**不**把 128 MB 当本仓预算模型；**不借** Workers 栈 |
| `RA-05-WEB-01` 纯 Python PDF 许可证（BSD） | pypdf FAQ + PyPI BSD-3-Clause | `🔶部分借` | **借**：许可证类别对照。**不借**：选定 pypdf |
| `RA-05-WEB-02` 进程内 PDF DoS | GHSA-m449-cwjh-6pw7 / CVE-2025-66019（patched **6.4.0**，~1GB/stream） | `⛔反例`（失败模式） | 无输出上限/隔离则恶意 PDF 可吃 RAM |
| `RA-05-WEB-03` pdfminer.six MIT + pickle CVE | GitHub LICENSE MIT；release 修 CVE-2025-64512 | `🔶部分借` | **借**：许可证+历史任意代码执行失败法。**不借**：库选型 |
| `RA-05-WEB-04` Poppler GPL 传染 | freedesktop poppler list 2017-04：call Poppler ⇒ GPL | `⛔反例`（对专有仓 **链入**） | subprocess 是否隔离法律风险 = owner 法务，不在本文裁决 |
| `RA-05-WEB-05` Poppler 内存破坏 CVE | GHSL-2025-054 CVE-2025-52886；CVE-2026-10118 Splash overflow | `⛔反例` | untrusted PDF + 渲染后端需要 sandbox |
| `RA-05-WEB-06` MuPDF AGPL | mupdf.readthedocs.io/license.html 1.28.3 | `⛔反例`（对专有仓链入/SaaS） | 商业许可存在，本文不买不选 |
| `RA-05-WEB-07` Playwright Apache-2.0 | GitHub LICENSE Apache-2.0 | `🔶部分借` | **借**：许可证友好于专有仓。**不借**：官方 Docker 默认 root=无 sandbox |
| `RA-05-WEB-08` Playwright/Chromium sandbox 警告 | playwright.dev/docs/docker | `⛔反例`（`--no-sandbox` 当生产） | untrusted crawl 必须非 root + seccomp；镜像声明不适合 untrusted |
| `RA-05-WEB-09` CDP printToPDF | chromedevtools Page.printToPDF `paperWidth` | `🔶部分借` | **借**：print 是 browser 的 **另一方法**，不是第二套云 API。**不借**：冻结 CDP 客户端库 |
| `RA-05-WEB-10` Tesseract Apache + 空页 | tessdoc Apache-2.0；`Empty page!!` 非成功 | `🔶部分借` | **借**：空 OCR ≠ admitted clean。**不借**：云 OCR；不把 `which tesseract` 当 readiness |
| `RA-05-WEB-11` vLLM multimodal ≠ string prompt | docs.vllm.ai multimodal_inputs + Chat API Vision | `🔶部分借` | **借**：parts/`image_url`/data URI；`--allowed-media-domains` 防 SSRF。**不借**：换供应商、让 vLLM 自己去拉任意 URL |
| `RA-05-WEB-12` OpenAI vision **厂商文档**对照（**不是**规范单源） | https://developers.openai.com/api/docs/guides/images-vision 访问 2026-08-29 | `🔶部分借` | **借**：限制清单（small text / rotation / non-English / CAPTCHA block）。协议形态以 **vLLM OpenAI-compatible**（`RA-05-WEB-11`）为对照源。**不借**：切换到 OpenAI 云 |
| `RA-05-WEB-13` PyMuPDF 路径穿越 | CERT VU#504749 / CVE-2026-3029 | `⛔反例` | 即便选 MuPDF 族，嵌入文件元数据不可当写路径 |

**渠道配对**：每个 S1 至少一条支持机制 + 一条限制。无适用的「本仓已有 live PDF 引擎」先例 → 供给层标 `🆕`（见 §8.2），不硬凑。

---

## 4. 缺口 / 断点台账 ★ `[核心]`

| 编号 | 缺口 / 断点 | 严重度 | 证据（`path:line`） | 影响 |
|------|-------------|--------|----------------------|------|
| `NH-RA05-B01` | 默认组合根未注入 `browser_fetcher` / `clean_llm` | `S1` | `api/app.py:332-345`；`core.py:45-51` | browser / LLM-clean / OCR-via-LLM 稳定 503；违反 `T-O-376`「禁止诚实未部署」若把 503 当 DoD |
| `NH-RA05-B02` | 生产依赖无 PDF/browser/OCR 专用包 | `S1` | `pyproject.toml:13-21`；`D-20=7/0` | 默认进程不可能 live 真文本层/浏览器/OCR 引擎 |
| `NH-RA05-B03` | `GenerateRequest` + vLLM adapter 不能运 PDF/image bytes | `S1` | `models.py:96-108`；`local_vllm.py:207-216` | 证伪 `T-P-NH-6` 运输句；understanding/OCR 无法走 S11 facade |
| `NH-RA05-B04` | Claude CLI 拒非 text / 纯 blob | `S1` | `claude_cli.py:505-508`；`clean_preflight.py:76` | CLI 兜底不能覆盖 `pdf.ocr` / `doc.vision` |
| `NH-RA05-B05` | readiness 不覆盖 binary/模型实弹/许可证 | `S1` | `health.py:16-25`；`app.py:183-189`；`local_vllm.py:276-295` | `/ready` 绿不能证明四通道 live |
| `NH-RA05-B06` | PDF 解码同进程、无隔离、无加密/恶意样本合同 | `S1` | `types.py:100-171` | 恶意 PDF 与 API 同命运共享；GPL/CVE 一旦引入库会直接打主进程 |
| `NH-RA05-B07` | 无 print-to-PDF 供给；acquire 不产 `print_pdf` | `S1` | `acquisition_ingest.py:535-536`；`strategies.py:67-76` | `web.browser_print_pdf` 与 `T-O-381`/`T-O-388` 不可达（表示合同待与面 03 对账） |
| `NH-RA05-B08` | OCR/Vision/browser acquire 为 unpooled，与「复用三池」叙事不对齐 | `S2` | `dispatch.py:20-28,122-146` | 即便不增第四池，也需显式把这些 process_key 编入池或保持 unpooled 并另做预算 |
| `NH-RA05-B09` | 默认 generate binding 非 VL；VL 只出现在 embed key | `S2` | `registry.py:111-132` | 扩协议也不等于现模型能看图；probe 名单更不能证明 vision |
| `NH-RA05-B10` | e2e 用 lambda 冒充 browser | `S2` | `test_source_capability_paths.py:99-101` | 假绿；属面 09 横切，本面提供 runtime 事实 |
| `NH-RA05-B11` | 许可证×隔离 未裁决（GPL 链入 vs subprocess vs sidecar） | `S2` | `pyproject.toml:11` Proprietary；WEB-04/06 | 选型未冻前不能把任何 native 库写进 pyproject |
| `NH-RA05-B12` | browser 出站未接 S16 EgressPolicy | `S2` | `http_acquisition.py:182-208`（仅 `HttpAcquirer`）；`api/app.py:280-288` 只把 EgressPolicy 绑到 HTTP 获取 | 将来 browser 若自带 fetch，可能绕过 SSRF 围栏 |

---

## 5. 跨功能系统一致性 ★ `[核心]`

- **5.1 整体形态一句话**：面 03 产出诚实 representation；面 04 选 admitted clean 策略；**面 05 只保证对应供给真实在场、可预算、可隔离、失败响**——三者身份不得合并。
- **5.2 功能间一致性契约（不变量 `NH-C-40..49`）**：

| 编号 | 不变量 | 跨哪些面/模块 | 违反后果 |
|------|--------|----------------|----------|
| `NH-C-40` | runtime 供给 ≠ clean strategy taxonomy | 04 拥有 strategy；05 拥有 adapter/二进制 | 按库名发明新 strategy 或按 strategy 绑死 CF 别名 |
| `NH-C-41` | 缺二进制/模型必须 fail-loud；**禁止** 503 当 in-scope 通道 DoD | 05/08/09；`T-O-376` | 「诚实未部署」假完成 |
| `NH-C-42` | `http_fetcher` / `browser_fetcher` / `clean_llm` 独立端口 | 03 acquire；04 clean；05 注入 | HTTP 冒充 rendered；CLI 冒充 OCR |
| `NH-C-43` | 不得把 binary 静默 decode 成 text 当成功 | 05 CLI/S11；04 empty 法 | PDF header 变成 admitted clean |
| `NH-C-44` | binary readiness = 负向样本 + identity，不是 which/import/`/v1/models` | 05/09 | `/ready` 假绿 |
| `NH-C-45` | PDF parser 隔离线与 browser 隔离线 **分别**裁（`G-NH-10`） | 05 安全 | 用一个 sandbox 故事覆盖两类威胁 |
| `NH-C-46` | print-PDF 产出必须是 PDF bytes；与 page-render 是否共享二进制是供给问题不是 strategy 问题 | 03 表示；05 供给；04 `web.browser_print_pdf` | 伪造 `rendered` 或 HTML 当 print |
| `NH-C-47` | 零 CF/R2/SMCP/Workers AI/Gemini alias 回流 | `T-O-42`/`377`；05/04 | 绿地破裂 |
| `NH-C-48` | 许可证（GPL/AGPL 链入 vs 宽松许可 vs 商业双牌）与隔离形态同票，不单独冻库名 | 05；`pyproject` Proprietary | 专有仓误链 AGPL/GPL |
| `NH-C-49` | 复用调度池 **不蕴含** 复用请求协议 | 05/S11；`G-NH-04` | `T-P-NH-6` 被执行成「不改 GenerateRequest」 |

- **5.3 数据 / 控制流贯穿图**：
```text
[Source bytes / URL]
        |  http_fetcher (EgressPolicy)          [有]
        |  browser_fetcher + printToPDF         [无供给]
        v
[representation — 面 03 拥有]
        |  decode: local-pdf-literal-text.v1    [假/同进程]
        v
[strategy bind — 面 04 拥有]
        |  clean_llm.complete(blob, media_type) [端口有, 生产 adapter 无]
        |  Claude CLI text only                 [拒 PDF]
        |  InferenceFacade GenerateRequest      [仅 input_text]
        v
[admitted clean → S06/g0 — 非本面]
```

- **5.4 邻面对账（待）**：面 03 应提供「何种 representation 才允许进 OCR/print」；面 04 应提供「`CleanLanguageModel` 最小合同」。本面不重写二者。冲突候选：QNA 写 OCR 与 LLM 同一端口 vs S11「无万能 blob invoke」——留给 review-fleet / 面 09，**不在此裁**。

---

## 6. 净新契约 / 架构边界草案 `[核心]`

> 草案，非冻结。不写库名、不写 HTTP 路径、不写 purpose 字符串。

- **6.1 净新聚合 / 解耦点**：
  - `NH-N-05-01`：**Binary multimodal request**（扩既有 Inference 请求 **或** 独立 adapter 请求）。最小字段方向：binding + prompt identity + `media_type` + bytes-or-handle + digest；禁止 `payload_extra` 偷运 content。
  - `NH-N-05-02`：**Capability readiness probes**（browser / pdf-parser / ocr / vision-generate），与 `inference_binding` 分账。
  - `NH-N-05-03`：**Untrusted-input isolation substrate**（PDF 与 browser 分开配置）。
  - `NH-N-05-04`：**Print-to-PDF acquire supply**（产出 PDF bytes + 可审计 browser profile，不是常量 `"injected-browser-renderer.v1"`）。
  - `NH-N-05-05`：**License/SBOM/binary inventory**（部署声明：包或 sidecar 身份、许可证、CVE 基线）。

- **6.2 净新契约叙述规格**：
  - **输入**：已密封 representation handle + strategy 所需 capability token（非 caller 点名模型）。
  - **输出**：admitted 文本 **或** typed 失败码（缺供给 / 隔离杀进程 / 空 OCR / 加密不可读 / sandbox 拒绝）。
  - **边**：超时、字节帽、并发闸、子进程 kill、egress（若 browser 出站）。
  - **禁止**：空 `clean_text` 当成功；`/v1/models` 当 vision；monkeypatch 当 e2e。

- **6.3 架构边界（与既有 / 相邻面）**：
  - 业务只经 `runtime.inference` 或显式独立 port；`services/` 仍禁 `llm_adapters`（S11-T001）。
  - 独立 capability supply 若复用 `ConcurrencyGate`，必须登记 capability key，不得静默挤占 embed。
  - 对象 bytes 仍走 S13 handle；推理请求不得带 path。

---

## 7. Substrate-fit / 技术路线过滤 ★ `[核心]`

> 本面灵魂：流行库 ≠ 可进 `pyproject`。过滤约束 = 单体 Python 3.12 FastAPI、local Turso、S03 七表无环、eq-only 守卫、S13 bytes-first、`T-O-42` 绿地、禁 CF/R2/SMCP/动态 plugin/自由表达式、仓库 `Proprietary`。

| 借鉴点 | 原机制（参考处） | 是否冲突本仓路线 / 约束 | 落地形态（降级 / 重映射 / 直采） |
|--------|------------------|--------------------------|-----------------------------------|
| pypdf 文本抽取 | 纯 Python，BSD-3 | 许可证友好；**进程内**则吃 CVE-2025-66019 类 DoS | 最多 `🔶`：须配输出/内存帽 + 负向测试；**不直采进 pyproject**（未裁 `G-NH-10`） |
| pdfminer.six | MIT 文本层 | 许可证友好；历史 pickle CMap RCE | 同左；禁止 pickle 资源路径 |
| Poppler `pdftotext` | GPL 库/CLI | **链入**与 Proprietary 冲突（官方 list 声明） | 若用：倾向 **subprocess CLI** 而非 link；仍须 sandbox；**不冻结** |
| MuPDF / PyMuPDF | AGPL + 商业 | AGPL 链入/SaaS 披露；CVE-2026-3029 写路径 | 链入 `⛔`；sidecar+商业许可是另一选项，**不选** |
| Playwright/Chromium | Apache-2.0 + 浏览器二进制 | 依赖体积/驱动；Docker root 关 sandbox | `🔶`：本地 sidecar-ish 二进制；**禁止**生产 `--no-sandbox` 当默认 |
| 系统 Chrome + CDP printToPDF | CDP 1-3 | 需冻结 browser profile；非 pyproject 包 | `🔶`：共享 / 分供给 **并列**；未裁 `G-NH-15`。CDP 只证明 `Page.printToPDF` 返回 PDF bytes，**不**证明本仓必须共享 Chromium |
| Tesseract | Apache-2.0 本地 OCR | 需 traineddata；空页非成功 | `🔶`：subprocess + 空输出失败；**云 OCR `⛔`**（非 local） |
| 扩 S11 GenerateRequest 为 parts | vLLM/OpenAI vision 协议 | 符合「业务只调 facade」；须改 contracts+adapter+probe | `G-NH-04` 选项 A；**不**因此换供应商 |
| 独立 `CleanLanguageModel` 实现 | HEAD 已有 Protocol | 符合 intake 端口；须自己做闸/预算 | `G-NH-04` 选项 B/C |
| CF Browser Rendering / Gemini / R2 | legacy | `T-O-42` 硬冲突 | `⛔` |
| Workers 128MB 当预算 | CF limits | 拓扑冲突；内存不够 PDF/browser | `⛔` 作预算模型；只借「必须独立供给」 |
| 云 OCR | 各类 SaaS | 非 local、密钥面、egress | `⛔` |

---

## 8. 反例坑表 + 净新表 `[核心]`

### 8.1 反例坑表 ⛔

| 反例 | 来源锚 | 为什么不可借 |
|------|--------|--------------|
| 默认组合根未注入却宣称通道 complete | `api/app.py:332-345`；`T-O-376` | 诚实未部署 |
| monkeypatch browser / 空 `clean_text` / 503-as-DoD | `test_source_capability_paths.py:99-101`；`T-O-378` | 假绿 |
| 字面量 PDF 当文本层引擎 | `types.py:144-171` | 假实现；无隔离 |
| GenerateRequest 不改就运 OCR | `models.py:96-108`；`T-P-NH-6` | 协议不能运 bytes |
| `/v1/models` 当 vision/PDF readiness | `local_vllm.py:276-295` | 只证明名字在目录 |
| `--no-sandbox` 默认跑 untrusted URL | Playwright Docker 官方 | 逃逸面 |
| 把 Poppler/MuPDF **链接**进 Proprietary 主进程 | Poppler GPL list；MuPDF AGPL 文档 | 许可证传染 |
| CF AI Gateway、Gemini `DOCUMENT_UNDERSTANDING` 别名、R2 `source_file`、Workers 超时 | `gemini.ts`；`wrangler.toml`；CF limits | `T-O-42` |
| 云 OCR | tessdoc 以外的 SaaS | 非 local |
| 用 `payload_extra` 塞 image | `models.py:63-70` | 明确禁 content/prompt；扩展袋不是 multimodal 合同 |

### 8.2 净新表 🆕

| 项 | 为什么无先例 | 草案落点 |
|----|--------------|----------|
| 本仓 **local** 的 PDF/browser/OCR **生产供给** | HEAD 零专用依赖；legacy 全是 CF/Gemini；外部库皆须过许可证+隔离过滤 | `NH-N-05-01..05` / `G-NH-04`/`10`/`11` |
| binary readiness 负向样本栅栏 | 现有 probe 只有模型名单与 DB/CAS | §6.1 `NH-N-05-02`；§9 |
| 逐能力隔离线（PDF ≠ browser） | S16 有 egress/subprocess CLI，无 untrusted PDF/browser 产品法 | `G-NH-10` |
| print-to-PDF 本地供给 | HEAD 无；legacy 是 CF `/pdf` | `NH-N-05-04`；`G-NH-15` |

---

## 9. 验收格栅草案（防假绿）`[核心]`

> 草案。落地验收归下游。禁止 monkeypatch browser/http 冒充 live；禁止空正文；禁止 Task succeeded 当可检索。

| 功能 F | 收口目标（一句话可验证） | Test-ID（拟） | 测试层 | 防假绿要点 |
|--------|--------------------------|----------------|--------|------------|
| 组合根注入声明 | 默认 app 对 in-scope 策略要么注入真实 port，要么 **不能** 用 503 关闭 `T-O-381` 格子 | `NH-A-05-01` | `default-root e2e` | 禁止测试里赋值 `_browser_fetcher` |
| PDF 文本层引擎 | 压缩流/CID 样本抽出非空文本；无层样本 **观察** 而非盗用 OCR 码 | `NH-A-05-02` | `集成` | 禁止字面量正则当绿；与面 03 对账 |
| 恶意/加密 PDF | 加密、zip 炸弹、已知 CVE PoC **不得** 打崩 API 进程；失败 typed | `NH-A-05-03` | `集成` | 不是 `which pdftotext` |
| Browser render | 真实 SPA fixture 得到 rendered HTML；缺二进制 readiness≠ready | `NH-A-05-04` | `default-root e2e` | 禁止 lambda HTML |
| print-to-PDF | 输出 `%PDF-` bytes 且 `representation_kind=print_pdf` | `NH-A-05-05` | `集成` | 禁止把 screenshot/HTML 改名 |
| OCR 空页 | 空白扫描件 → 非 admitted clean（对齐 `T-O-378`/`383`） | `NH-A-05-06` | `单元+集成` | Tesseract `Empty page!!` 不得当成功 |
| Vision/PDF bytes 运输 | 生产路径能把 PDF/image bytes 交给 **已登记** 模型并拿回收回；CLI 路径仍拒 binary 或显式新合同 | `NH-A-05-07` | `集成` | 禁止只测 Protocol stub |
| Readiness 分项 | `/ready` 在缺 Chromium/缺 OCR data/缺 vision binding 时 **not ready** 或分组件 false | `NH-A-05-08` | `集成` | 禁止只探 `/v1/models` |
| 并发闸 | OCR/vision/browser 占用计入已登记 cap，满则 BACKPRESSURE、零模型调用 | `NH-A-05-09` | `单元` | 对标 `ConcurrencyGate` |
| 许可证/SBOM | 引入的每个原生/子进程二进制有许可证记录与 CVE 基线 | `NH-A-05-10` | `单元/清单` | 不把 GPL 链入悄悄写进 lock |
| 四通道终态 | 真文件→真 Process→可检索向量（与面 08/09 mega 衔接） | `NH-A-05-11` | `retrieval-facet mega` | 本面只保证供给；不代替 publication 证明 |

---

## 10. 优先级建造建议 + owner-gate 候选 `[核心]`

- **10.1 建造顺序（依赖序，分批不一次性深做）**：

| 顺序 | 工作簇 | 依赖 | 复用判定 |
|------|--------|------|----------|
| `P0-a` | 钉供给身份：browser / pdf-parser / ocr-or-vision 三条 capability token 与 fail-loud 码分账 | 面 03/04 合同（待对账） | `♻️重 substrate`（已有 port/error 码） |
| `P0-b` | owner 裁 `G-NH-04`/`G-NH-10`/`G-NH-15`（本面只 MARK） | `P0-a` | n/a（决策） |
| `P0-c` | 请求协议：扩 S11 **或** 独立 adapter（按 gate） | `G-NH-04` | `🆕净新` 或 `♻️` |
| `P0-d` | 隔离与许可证落地（逐能力） | `G-NH-10` | `🆕净新` |
| `P0-e` | 组合根注入 + readiness 负向探针 | `P0-c/d` | `♻️重 substrate`（HealthAggregator） |
| `P1-a` | print-to-PDF 供给接到 acquire | `G-NH-15`；消费面 03 `NH-RA03-B02` | `🆕净新` |
| `P1-b` | 把 OCR/vision/browser 编入池或显式 unpooled 预算 | `D-05-F06` | `♻️` 或保持 unpooled |
| `P2` | default-root e2e 去 monkeypatch；与面 09 mega | `P0-e` | `✅复用` 测试骨架 |

- **10.2 owner-gate 候选（只 MARK 不裁决 → 上交 index §4 / 下游决策登记）**：

| gate-ID | 决策点 | 候选选项（不预设倾向） | 影响 |
|---------|--------|------------------------|------|
| `G-NH-04` | PDF/browser/multimodal runtime 边界 | `扩既有 inference request/adapter` / `独立本地 adapter 但复用 pool` / `独立 capability supply` | S11 contracts、池、readiness、intake 注入 |
| `G-NH-10` | 外部依赖与隔离接受线（**逐能力裁**） | `in-process` / `isolated subprocess` / `sidecar-local`（PDF parser 与 browser **不必**同一选项） | pyproject、CVE 面、主进程命运、许可证 |
| `G-NH-15` | print-to-PDF 与 page-render 是否同一 browser 供给 | `同一本地 browser 二进制、不同 CDP 方法` / `分供给（独立 print 服务）` / `其他经证据支持的本地形态` | acquire 实现、资源预算、sandbox 配置 |

禁止在本文选定 pypdf / playwright / tesseract / poppler / mupdf 等为「将采用」。`G-NH-15` 只 MARK、无推荐赢家；index §4 v0.2 已登记本 gate（仍不裁决）。`G-NH-11` 留给面 02 seal 事务。print 死键 **消费** `NH-RA03-B02`；本面 `NH-RA05-B07` 只保留供给侧。

---

## 11. 核验记录 `[核心]`

| 锚点（host-ID） | 是否核验 | 方式（grep/read/run） | 备注 / 修正 |
|------------------|----------|------------------------|--------------|
| `D-20` `pyproject.toml:13-21` | `✅` | read + python 计 7 依赖 | 与 index 一致；未另估 |
| `D-21` `api/app.py:332-345` | `✅` | read + `'browser_fetcher=' in app_src` = False | 行号未漂 |
| `GenerateRequest` blob=0 | `✅` | python `model_fields` | `D-05-F01` |
| CLI 拒 PDF | `✅` | read `claude_cli.py:505-508` + pytest `test_non_text_blob_is_rejected` passed | 2026-08-29 |
| 三池 / unpooled OCR | `✅` | python `pool_kind` | 修正叙事「OCR 已在 generate 池」 |
| Health REQUIRED | `✅` | read `health.py:16-25` | metrics 另含 `concurrent_writes`，REQUIRED 不含；不改 D 分母 |
| `probe` = `/v1/models` | `✅` | read `local_vllm.py:276-295` | |
| PDF 字面量 | `✅` | read `types.py:144-171` | 无 encrypted 字段 |
| print_pdf 死键 | `✅` | read acquire 535-536 vs preflight 46-62 | |
| legacy gemini inlineData | `✅` | read `gemini.ts:213-217` | 未 import/运行 |
| legacy browser-renderer `page.pdf` | `✅` | read `browser-renderer.ts:74-86` | |
| legacy wrangler CF/R2 | `✅` | read `wrangler.toml:1-41` | 含明文密钥样式，只作反例 |
| dedicated `action_registry` 3 叉 | `✅` | read `:59-79` | 无 PDF/browser，不硬凑 |
| WEB pypdf BSD + CVE | `✅` | web_search + open FAQ/GHSA | 检索词写 Apache，实测 BSD-3——记下以免选型误传 |
| WEB Playwright docker + LICENSE | `✅` | open playwright.dev/docs/docker + GitHub LICENSE | |
| WEB CDP printToPDF | `✅` | open chromedevtools 1-3/Page | |
| WEB Tesseract Apache | `✅` | open tessdoc | 空页 return code 无单一官方 ABI → 置信不足处已标 |
| WEB vLLM multimodal + SSRF | `✅` | open multimodal_inputs.html | |
| WEB OpenAI vision 限制 | `✅` | open developers.openai.com images-vision | 对照用，不切供应商 |
| WEB CF 128MB | `✅` | open workers/platform/limits | |
| WEB Poppler GPL | `✅` | web_search 官方 list；gitlab README 被 bot 墙 | 标「规范邮件列表」；fossies 401 |
| WEB MuPDF AGPL | `✅` | open mupdf license.html | |
| 面 03/04 analysis 落盘 | `✅`（负） | `list_dir` reference-anchor 目录本轮创建前不存在邻面文件 | MARK 待对账 |
| `T-P-NH-6` | `✅` | read initial-planning `:73` | **叙事**；运输层证伪 |
| `T-O-376/378/381` | `✅` | read QNA `:80-85` | 只 CITE；非 HEAD 事实 |
| pytest 3 条 | `✅` | `uv run pytest ...` 2026-08-29 **3 passed** | 未重跑 D-23 33 条 |
| index `D-23`/`D-24` | 未本面复跑 | — | 遵守「不另估」 |

**声称 vs 实测修正**：

| 叙事 | HEAD | 失真 |
|------|------|------|
| `T-P-NH-6` 复用推理面即可运 OCR/Vision | 协议与 CLI 均拒/不能运 bytes | 证伪（运输）；池名不增仍 OPEN |
| QNA「OCR/Vision 是同一 LLM 端口」= 已能 live | 端口形状有；生产 adapter/组合根/模型均无 | 高估 |
| S11 embed「multimodal parts」 | `EmbeddingRequest.texts: list[str]` only | 文档超前于代码 |
| 「有 InferenceFacade 即有 vision」 | capability 闭集无 vision；generate binding 非 VL | 高估 |
| Playwright 官方镜像可直接爬 untrusted | 文档明确不推荐；root 关 sandbox | 外部误用 |

---

## 12. 收尾 Verdict 与交接 `[核心]`

- **本面裁定**：面 05 为 `P0 / 🔴`。可复用 substrate = 端口分离、三池闸、egress、SupplyFence、CLI subprocess、诚实拒 binary、缺注入 fail-closed。净新/重 substrate = binary 运输协议、PDF/browser/OCR **真实供给**、负向 readiness、逐能力隔离与许可证。`T-P-NH-6` 不得再作为「不改 S11 请求也能运 PDF」的依据。
- **交接下游**：缺口台账（§4）→ 规划；净新契约（§6）→ 设计；owner-gate（§10.2 `G-NH-04/10/11`）→ `pre-charter-qna.md`；验收格栅（§9）→ 执行计划。邻面 03/04 分析落盘后对账 `NH-C-40/42/46`。
- **冻结前置**：① 面 03/04 至少 draft 对账 representation 与 clean port；② owner 裁隔离/协议边界（本文件不得代裁）；③ 任一引入依赖必须带许可证+CVE+负向样本，而不是 feature list；④ 本文保持 `draft`，禁止标 `frozen`/`reviewed`。

---

## 附录 A · 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-08-29 | Grok analysis-fleet / review-fleet | 初稿（measure-first + 三渠道正反例 + substrate-fit + 缺口台账）；状态 `draft` |
| v0.2 | 2026-08-29 | Grok fix-fleet | 吸收已核实 review：R4-I06 §0.3 去掉 G-NH-04 选项 C 倾向；R4-I10 §7 共享/分供给并列；R2-I03 LEGACY-05 改 `RA-05-WEB-14`；R2 §5 钉 gemini key 轮询行；R3-I05 删 OpenAI「规范单源」；R3-I06 删无 URL 的 `paperWidth<=0`；R4-I01 `G-NH-11`→`G-NH-15`。状态仍 `draft` |

## 附录 B · 本面 ID 速查

| 类型 | ID |
|------|-----|
| HEAD+ | `RA-05-HEAD-01` … `RA-05-HEAD-08` |
| HEAD- | `RA-05-HEAD-N01` … `RA-05-HEAD-N08` |
| LEGACY | `RA-05-LEGACY-01` … `RA-05-LEGACY-04` |
| WEB | `RA-05-WEB-01` … `RA-05-WEB-14` |
| 缺口 | `NH-RA05-B01` … `NH-RA05-B12` |
| 不变量 | `NH-C-40` … `NH-C-49` |
| 净新缝 | `NH-N-05-01` … `NH-N-05-05` |
| owner-gate | `G-NH-04`、`G-NH-10`、`G-NH-15`（只 MARK） |
| 验收草案 | `NH-A-05-01` … `NH-A-05-11` |
