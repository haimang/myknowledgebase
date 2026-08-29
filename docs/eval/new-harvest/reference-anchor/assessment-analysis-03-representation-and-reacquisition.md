# 调查面 `03` · 表示、acquire/decode 与有限正向再获取 — 深度评估

> **对象 / scope-fence**：HTTP static / browser / print PDF；local/inline bytes；MIME sniff 与 declared/detected mismatch；PDF 文本层观察；image/opaque document；acquisition/decode evidence chain；有限、已声明、无环、正向 reacquire；decode 只观察。
> **本面不含**：clean 输出质量与 admitted clean 合同（面 `04`）；PDF/browser/OCR **库选型与进程隔离**（面 `05`）；图上如何画边（面 `01`，本面只提供 representation fact 最小闭集给守卫消费）。
> **日期**：`2026-08-29`
> **作者**：`Grok analysis-fleet / review-fleet`（fleet / panel：`new-harvest-reference-anchor`）
> **文档性质**：`assessment / analysis`（单面 measure-first 深评；零决策——只 MARK 不裁决）
> **文档状态**：`draft`
> **流水线位置**：站② · 上游 = [[assessment-index]]（消费其冻结分母）
> **对照参考**：HEAD `1221aa1`；`docs/eval/new-harvest/pre-initial-planning-qna.md` v0.5 `T-O-378/381/382/388`（只 CITE）；`docs/baseline/spec-glossary.md` `AcquisitionEvidence`；`docs/baseline/domain-truth/D08-legacy-capabilities-migration.md`；WHATWG MIME Sniffing Living Standard；ISO/DIS 32000 §9.10；Chrome DevTools Protocol `Page.printToPDF`；Playwright `page.pdf`；ECMA-376 Part 2 OPC；pypdf `GHSA-jfx9-29x2-rv3j` / PDF.js `CVE-2024-4367`
> **上游权威输入**：
> - `docs/eval/new-harvest/assessment-index.md` — §2.2 冻结分母 `D-02/D-09/D-13/D-20/D-21` / §3.03 本面登记
> - `docs/eval/new-harvest/pre-initial-planning-qna.md` — `T-O-378/381/382/388`（字面量 PDF 谎言；print_pdf 必须诚实；暗升禁止；声明式再获取允许）
> **下游消费者**：`docs/eval/new-harvest/planning-proposed.md` · `pre-charter-qna.md`（owner-gate 裁决）· 面 `01`/`02`/`04`/`05`/`09` 设计/执行制品
>
> **图例（本簇）**：借鉴 verdict = `✅借` / `🔶部分借` / `⛔反例` / `🆕净新`；复用判定 = `✅复用` / `♻️重substrate` / `🆕净新`；缺口严重度 = `S1 阻断` / `S2 重要` / `S3 次要`；置信 = `HEAD 实测 > 仓内文档锚 > 外部参考`。本文 **只 MARK 不裁决**。

---

## 0. Verdict（结论先行）`[核心]`

- **0.1 一句话缺口 / 现状判断**：HEAD 已有 MIME sniff、URL 脱敏、image 空文本观察、browser/static 端口分离等可复用观察底座，但 **表示事实尚未成为可守卫的最小闭集**：decode 仍用 `CLEAN_OCR_CAPABILITY_UNAVAILABLE`（422）冒充「无文本层」；`representation_kind` 只写 `rendered|transferred`、**从不产 `print_pdf`**；evidence 单槽覆盖、声明式 reacquire 边 = 0；docx/ZIP 被当 UTF-8 文本在 acquire 死亡或误标 `text/plain`。这与 `T-O-378/388` 的目标法直接冲突，属 P0/🔴。
- **0.2 Top blockers（最关键断点）**：
  1. `NH-RA03-B01`：无层 PDF 死在 decode 并盗用 OCR 码（`T-O-378` 仍为 HEAD 事实）。
  2. `NH-RA03-B02`：`print_pdf` 必须诚实，但 acquire 从不写该 kind，print-pdf 图与 preflight 猜测是死路径。
  3. `NH-RA03-B03`：acquisition/decode evidence 单值、无 history、无声明式再获取边（`D-13`），无法支撑 `T-O-388` 有限正向再获取与 digest 覆盖实际路径。
- **0.3 总体方向建议**（**非裁决**）：在既有 `_AcquiredContent` / `mkb.acquisition-evidence.v1` / sniff-verify 底座上 **重 substrate** 出 typed representation fact + history digest；decode 降为观察器；print_pdf 必须由 acquire 证据产出 PDF bytes。图边归面 `01`，seal 归面 `02`，工人合同归面 `04`，运行时供给归面 `05`。库选型 **不在本面冻结**。
- **0.4 如何读本台账**：见上方头部「图例」；本面主题轴 = `MIME sniff/verify` / `representation_kind 诚实` / `decode 观察 vs 能力码` / `opaque/office bytes` / `evidence history 与有限正向再获取`。

---

## 1. 方法与证据基线 `[核心]`

> 读了哪些代码/文档/参考；什么算可采信；怎么复现。**先证可证性，再下判断。**

- **1.1 本仓证据（如何测量）**：
  - HEAD：`src/runtime/intake/types.py`、`acquisition_ingest.py`、`clean_preflight.py`、`core.py`；`src/contracts/intake/strategies.py`；`src/contracts/workflow/models.py`；`src/runtime/workflow/runtime_materialize.py`；`src/workflows/lsrag_definition.py`；`src/services/{workflow_registry,config_snapshots}.py`；`src/runtime/http_acquisition.py`；`api/app.py`；`pyproject.toml`；`intake/{__init__,pdf,doc}/__init__.py`；`tests/unit/test_intake_source_capabilities.py`、`tests/unit/test_ns5_phase4.py`、`tests/e2e/test_source_capability_paths.py`。
  - 仓内 baseline：`docs/baseline/spec-glossary.md` `AcquisitionEvidence`；`D08-legacy-capabilities-migration.md` `D08-T003/T004/T009`。
  - QNA 只 CITE：`T-O-378/381/382/388`。`initial-planning.md` / thoughts 仅作「叙事/初判」，不当地实测。
  - 本面专属分母：`uv run python` 对 `_sniff_media_type` / `_extract_pdf_text` / `_representation_from_bytes` / 13 张 single 图 acquire 边计数实测（§2.1）。
- **1.2 外部 / 参考来源 + 置信**：

| 搜索词（2026-08-29） | 打开的 primary URL | 版本 / 发布日 | 支持的原子结论 | 限制 / 失败条件 | 置信 |
|----------------------|--------------------|---------------|----------------|------------------|------|
| `WHATWG MIME sniffing standard official` | https://mimesniff.spec.whatwg.org/ | Living Standard，Last Updated **17 July 2026** | `Content-Type` 常撒谎；HTML/XML **supplied type 优先**；未知类型可 pattern-match；ZIP 签名 `PK\x03\x04` → `application/zip` | 规范为浏览器 UA 平衡兼容与 XSS；**不得**把完整 UA sniff 当本仓安全策略；规范单源 | HEAD 外 / 高（规范） |
| `Chrome DevTools Protocol Page.printToPDF documentation` | https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-printToPDF | tot viewer，访问日 2026-08-29 | 官方能力：把 **已渲染页面打印为 PDF**，返回 base64/stream | `printBackground` 默认 false；`pageRanges` **quietly capped**，超范围 **ignored**，**仅当结果为零页才 error**；`transferMode`/`generateTaggedPDF` 标 Experimental；**不是** HTML fetch | 高 |
| `Playwright page.pdf official docs limitations` | https://playwright.dev/docs/api/class-page#page-pdf | Playwright docs，页面标注 Added before v1.9；访问日 2026-08-29 | 默认 **CSS print media**；颜色被改写；`headerTemplate`/`footerTemplate`：**脚本不执行、页面样式不可见**；headless **不能导航到 PDF 文档** | 本面 **禁止选定** Playwright；只借失败模式 | 高 |
| `ISO 32000 PDF text extraction ToUnicode official` | https://pdfa.org/pdf-standards/（ISO 32000 = PDF 2.0/1.7 映射）；https://archive.org/details/ISODIS32000E §9.10 | ISO/DIS 32000（PDF 1.7 草案文本，© ISO 2007）；ISO 32000-2:2020 目录含 9.10 | 文本提取须 **字符码→Unicode**（标准编码 / ToUnicode CMap / ActualText）；无映射则「字形能画、字符义不可知」 | DIS 非现行 2.0 正文；付费 ISO 正文未整本打开。提取 **不等于** 扫描像素 OCR | 中高（条款级） |
| `ECMA-376 DOCX OPC zip content types official` | https://ecma-international.org/publications-and-standards/standards/ecma-376/ | ECMA-376 5th ed. Part 2 OPC **December 2021**；ISO/IEC 29500 | DOCX = ZIP 物理包 + XML parts + `[Content_Types].xml` MIME 映射；**不是** UTF-8 纯文本 | 本面不选 docx 解析库 | 高（规范单源 + ISO 编号交叉） |
| `CVE PDF parser sandbox pypdf poppler mutool` | https://github.com/advisories/GHSA-jfx9-29x2-rv3j ；https://codeanlabs.com/blog/research/cve-2024-4367-arbitrary-js-execution-in-pdf-js/ | GHSA 发布 2025-10-22（pypdf `<6.1.3` LZW 内存耗尽，CVE-2025-62708）；CVE-2024-4367 PDF.js 任意 JS（2024-05-20） | **解析器本身是攻击面**：DoS / JS / 路径穿越；需要隔离与预算 | **禁止本面选定** pypdf/poppler/mutool；只作安全反例 | 高（advisory） |

- **1.3 ★ 可复现命令清单（measure-first）**：

```bash
# HEAD 与分母对齐（不得改写 index D-*）
git rev-parse HEAD   # 期望 1221aa1ba3bcc8d5be38f7d2529a052dcf93b256

nl -ba src/runtime/intake/types.py | sed -n '31,37p;144,220p'
nl -ba src/runtime/intake/acquisition_ingest.py | sed -n '65,90p;214,227p;403,676p'
nl -ba src/runtime/intake/clean_preflight.py | sed -n '46,71p;619,657p'
nl -ba src/runtime/intake/core.py | sed -n '39,75p'
nl -ba api/app.py | sed -n '330,345p'
nl -ba src/contracts/intake/strategies.py | sed -n '15,77p'
nl -ba src/contracts/workflow/models.py | sed -n '245,278p'
nl -ba src/runtime/workflow/runtime_materialize.py | sed -n '90,117p'
nl -ba pyproject.toml | sed -n '13,21p'
rg -n "representation_kind|print_pdf|CLEAN_OCR_CAPABILITY_UNAVAILABLE|_extract_pdf_text" \
  src/runtime/intake src/contracts/intake api/app.py

# 本面新测分母（2026-08-29 已跑；MkbError 字段为 code/message/status_code）
uv run python - <<'PY'
from src.runtime.intake.types import _sniff_media_type, _extract_pdf_text, _verified_media_type
from src.contracts.common.errors import MkbError
from src.runtime.intake.acquisition_ingest import IntakeAcquisitionIngestMixin
from src.workflows.lsrag_definition import BUILTIN_SOURCE_PROFILE_WORKFLOWS, BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW
samples = {
    "pdf": b"%PDF-1.4\n", "png": b"\x89PNG\r\n\x1a\n", "jpeg": b"\xff\xd8\xff\x00",
    "gif": b"GIF89a", "webp": b"RIFF....WEBP", "json": b'{"a":1}',
    "html": b"<!DOCTYPE html><html></html>", "plain": b"hello",
    "octet": bytes(range(128, 160)), "docx_pk": b"PK\x03\x04" + b"\x00"*20,
}
for k,v in samples.items():
    print(k, _sniff_media_type(v))
try:
    _extract_pdf_text(b"%PDF-1.4\n%EOF")
except MkbError as e:
    print("no-layer", e.args)
mixin = IntakeAcquisitionIngestMixin.__new__(IntakeAcquisitionIngestMixin)
mixin._acquisition_max_response_bytes = 8*1024*1024
try:
    mixin._representation_from_bytes(b"PK\x03\x04"+bytes(range(128,180)),
        declared_media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        capability="intake.acquire.local_object", source_kind="local_object", mode="logical_object")
except MkbError as e:
    print("docx-high", e.args)
defs = (BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW, *BUILTIN_SOURCE_PROFILE_WORKFLOWS)
print("graphs", len(defs), "acquire_steps_per", {len([s for s in d.steps if (s.process_key or '').startswith('intake.acquire')]) for d in defs})
PY

# 小集合测试（index 已列；本面不宣称 e2e 全绿）
uv run pytest tests/unit/test_intake_source_capabilities.py tests/unit/test_ns5_phase4.py -q
# e2e 名称含 monkeypatch，只作反例锚，不作为 live DoD
```

- **1.4 范围围栏**：本面**只**覆盖 representation / acquire / decode 观察 / 有限正向再获取的 **事实与失败法**；clean 成功合同、runtime 库/进程、图代数、S05 digest 字段生命周期、上传面 **不在此**。本面 **禁止选定** PDF/browser/OCR 引擎字面。

---

## 2. 当前结构分析（HEAD 实测 · measure-first）★ `[核心]`

> 按主题轴逐条测，每条钉 `path:line`。先冻结本面分母，再逐轴展开。

### 2.1 ★ 冻结分母（FROZEN denominators · HEAD）

> 引用 [[assessment-index]] §2.2 中属于本面的分母，并补本面专属分母。下游不得另估。

| 分母 | HEAD 实测值 | 证据锚（`path:line`） | 来源 |
|------|-------------|------------------------|------|
| `D-02` CleanStrategyKey | `10` | `src/contracts/intake/strategies.py:15-151` | index §2.2 |
| `D-08` guard predicate type / operator | `5 / eq-only` | `src/contracts/workflow/models.py:245-278` | index §2.2 |
| `D-09` representation-aware guard | `0` | `models.py:249-255`；`runtime_materialize.py:101-117`（context 只有 admission/intent/metadata/markdown） | index §2.2 |
| `D-13` acquisition/decode evidence history；声明式 reacquire edge | `单值 1+1`；`0` | `acquisition_ingest.py:89,660`；本面脚本：13 张 single 图每张 **恰好 1** 个 `intake.acquire.*` step | index §2.2 / 本面复测 |
| `D-20` 直接生产依赖 / PDF-browser-OCR 专用依赖 | `7 / 0` | `pyproject.toml:13-21`（fastapi/starlette/httpx/pydantic/pydantic-settings/pyturso/uvicorn；无 pdf/browser/ocr 包） | index §2.2 |
| `D-21` 默认组合根 `browser_fetcher` / `clean_llm` | `0 / 0` | `api/app.py:330-345`（`IntakePipeline(..., http_fetcher=http_acquirer, inference=..., claude_cli=...)`，**无** `browser_fetcher=` / `clean_llm=`） | index §2.2 |
| `D-03-F01` sniff 能识别的 media 返回值集合 | `9`：`application/pdf`、`image/png`、`image/jpeg`、`image/gif`、`image/webp`、`application/json`、`text/html`、`text/plain`、`application/octet-stream` | `types.py:174-199`；2026-08-29 脚本 | 本面新测 |
| `D-03-F02` 实际写出的 `representation_kind` | acquire HTTP：`rendered`（browser）\| `transferred`（else）；decode image：`image_evidence`；**`print_pdf` 生产次数 = 0** | `acquisition_ingest.py:535,630`；`rg representation_kind src/` 仅此两处赋值 | 本面新测 |
| `D-03-F03` ZIP/OPC（`PK\x03\x04`）sniff | **不识别**；零字节填充 PK → `text/plain` | 2026-08-29：`docx_pk -> text/plain` | 本面新测 |
| `D-03-F04` 无层 PDF / opaque 失败码 | 无层：`CLEAN_OCR_CAPABILITY_UNAVAILABLE` **422**（非 503）；坏签名：`DECODE_PDF_INVALID` 422；高位 ZIP/octet：`ACQUISITION_DECODE_UNSUPPORTED` 422 | `types.py:145-159`；`acquisition_ingest.py:561-564` | 本面新测 |
| `D-03-F05` 公开 profile 含 print-pdf？ | **否**。`SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS` 仅 `http_resource.{static,browser,pdf}`；`BUILTIN_BROWSER_PRINT_PDF_INTAKE_WORKFLOW` 存在但 **不在公开选择器** | `lsrag_definition.py:929-940,1048-1054` | 本面新测（对齐 `D-06` 6 张不可选） |

### 2.2 轴 MIME sniff / declared vs detected（HEAD 核验）

- `_sniff_media_type` 按魔数识别 PDF/PNG/JPEG/GIF/WEBP，否则尝试 `utf-8-sig`；失败则 `application/octet-stream`；成功则 JSON 或 HTML hint 或 `text/plain`（`types.py:174-199`）。这是 **正例**：不以声明为真理。
- `_verified_media_type` 对 **PDF mode、声明 PDF、声明 image** 与 detected 不一致 **fail-closed** `ACQUISITION_MEDIA_MISMATCH` 422（`types.py:209-217`）。octet-stream 时回退 `declared or detected`（`:218-220`）——声明 HTML、实为不可解码二进制时仍可能把 declared 当 verified，属半开窗口。
- WHATWG 对照：HTML/XML 的 **supplied** type 优先、ZIP 有独立 pattern。HEAD **没有** ZIP 行，也没有 `X-Content-Type-Options: nosniff` 分支。见 `RA-03-WEB-01`。

### 2.3 轴 HTTP / local / inline acquire

- HTTP 只接受 URL；`HttpAcquirer` 文档写明 callers **不得**注入 headers/cookies/proxy（`http_acquisition.py:1-6`）。生产 Accept 为固定闭集（`:245`）。URL 进 evidence 只经 `redacted_url_identity` SHA-256（`:41-81,109-118`）。**正例**。
- `acquisition_mode ∈ {static,browser,pdf}`（`contracts/api/models.py:128`；`acquisition_ingest.py:474-476`）。`pdf` mode **并不**走 print；`_expected_acquisition_capability` 把 `static|pdf` 都映射到 `intake.acquire.http_static`（`:221-226`）。
- browser 缺注入 → `ACQUISITION_BROWSER_CAPABILITY_UNAVAILABLE` **503**（`:477-485`）。这是 **能力未部署** 的正确族；与 decode 422 OCR 盗码形成对照。
- 默认组合根未注入 `browser_fetcher`（`api/app.py:330-345`；`core.py:67-70` 注释禁止 fallback 到 static，以免伪造 rendered）。live browser/print **物理不存在**（`D-21`）。
- e2e `test_source_capability_paths.py:99-101` **赋值** `pipeline._http_fetcher` / `_browser_fetcher`。按 `T-O-378`，monkeypatch **不是接线**。

### 2.4 轴 `representation_kind` 与 print_pdf 诚实

- HTTP extra_evidence：`"representation_kind": "rendered" if mode == "browser" else "transferred"`（`acquisition_ingest.py:533-536`）。`mode=="pdf"` 也是 `transferred`。**从不写 `print_pdf`**。
- `browser_profile` 在 browser 时为常量 `"injected-browser-renderer.v1"`（`:536`），与真实 renderer 版本无关。
- `clean_preflight._clean` **会认** `print_pdf`（`:46-62`），并把 `clean.extract.pdf_llm` 绑到 `web.browser_print_pdf`；但 acquire 永不生产该 kind → 该分支是死代码。`intake/__init__.py:78-81` 同样猜测。
- 策略登记：`WEB_BROWSER_PRINT_PDF` `channel="pdf"`，`browser_required=True`，`acquire_capabilities=("intake.acquire.http_browser",)`（`strategies.py:67-77`）。
- 存在 `BUILTIN_BROWSER_PRINT_PDF_INTAKE_WORKFLOW`：`http_browser` + `intake.decode.pdf` + `clean.extract.pdf_llm`（`lsrag_definition.py:1048-1054`），**不在** `SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS`。若强行跑且 browser 返回 HTML，`_decode` 会因 `media_type != application/pdf` 而期望 `intake.decode.text_json_html`，与绑定的 `intake.decode.pdf` 冲突 → `DECODE_CAPABILITY_MISMATCH` 409（`acquisition_ingest.py:606-608`）。
- `T-O-388`：「print_pdf 必须诚实产出 `representation_kind=print_pdf` 且 bytes 为 PDF」。HEAD **未满足**。

### 2.5 轴 PDF decode / 文本层观察

- `_extract_pdf_text`：要求 `%PDF-`；用正则捞未压缩 `(...) Tj` / `[...] TJ` 字面量；decoder 自称 `local-pdf-literal-text.v1`；成功时 **写死** `text_layer: "present"`（`types.py:144-171`）。注释自己承认「不是 permissive renderer」，加密/畸形/纯图会落到「local-OCR capability refusal」（`:100-106`）。
- 无字面量 → **抛** `CLEAN_OCR_CAPABILITY_UNAVAILABLE`，消息「local OCR is not configured」，HTTP **422**（`:154-159`）。同码在 `intake/pdf/__init__.py:48-50` 以 **503** 表示 OCR **未注入**。观察失败与能力未部署 **撞码且撞语义**。
- 2026-08-29 实测：`%PDF-1.4\n%EOF` 与含 `/Encrypt` 但无 Tj 的 blob 均走该 422 OCR 码；**不会**写出 `text_layer=absent`。
- ISO/DIS 32000 §9.10：提取是 **字符码→Unicode**（标准编码 / ToUnicode / ActualText），压缩流 + CMap 是正途；字面量扫描既不是规范提取，也不能观察扫描件。见 `RA-03-WEB-05`。
- `T-O-378` 仍为 HEAD 事实；`T-O-388` 要求 decode 做观察器、禁止再抛该 OCR 码。

### 2.6 轴 image / opaque / office

- PDF 与 `image/*` 走 binary latin-1 运输（`acquisition_ingest.py:556-559`）。image decode：**故意** `decoded = ""`，evidence `canonicalizer=binary-image-evidence.v1`，`representation_kind=image_evidence`（`:620-632`）。**正例：不制造文本**。随后 OCR/Vision 在 clean 以 503 拒绝（`test_intake_source_capabilities.py:197-208`；e2e image → `clean.ocr.local` + `CLEAN_OCR_CAPABILITY_UNAVAILABLE`，`test_source_capability_paths.py:220-272`）。此处 503 发生在 **clean**，与 decode 422 盗码不同。
- 非 PDF/image：强制 `data.decode("utf-8-sig")`，失败 → `ACQUISITION_DECODE_UNSUPPORTED` 422（`:561-564`）。docx 高位字节实测走该码，**进不了** `doc.document_understanding`。
- `PK\x03\x04` 在 UTF-8 合法时被 sniff 成 `text/plain`（`D-03-F03`）。ECMA-376 Part 2：Office 文档是 ZIP+XML OPC，**把 docx 当 UTF-8 文本解码是错的**（`RA-03-WEB-07`）。
- `ACQUISITION_EMPTY` 仅当 **非 binary 且 strip 后空**（`acquisition_ingest.py:65-66`）。带标签的 SPA 空壳 HTML **不会**停；没有 `shell_empty` / `main_text_absent` 观察。

### 2.7 轴 evidence 单槽、digest、preflight

- `_acquire` 写 **一个** `acquisition_evidence`（`:89`）；`_decode` 写 **一个** `decode_evidence`（`:660`）。无 list/history。再获取会覆盖。
- preflight `_validate_single_preflight_evidence` 用 **descriptor 的** `acquisition_mode` 反推 expected capability（`:629-636`）；browser 还要求 `representation_kind=="rendered"`（`:653-657`）。static→browser 若将来发生，preflight 仍认为起点 static 才合法。
- `decoded_digest` 绑定 **当前** canonicalizer+media+text（`:653-659`），不含 acquire 路径向量。`T-O-388` 要求 `s05_binding_digest` 覆盖 **实际走过的 acquire 路径**——本面只能提供 path facts；seal 时刻归面 `02`。

### 2.8 轴 有限正向再获取 vs 今日选图

- 13 张 single 图均为 **acquire → decode → clean** 单链；`acquire.to_decode` 无守卫（`lsrag_definition.py:299-306`）。脚本：每图 1 个 acquire Process，reacquire route = 0。
- `ConfigSnapshotService._source_profile` 仍用 `http_resource.{static,browser,pdf}` 与 `local_object.{pdf,image}` **选图**（`config_snapshots.py:492-516`）。这与 `T-O-387`「mode/media **不再选图**、图内起点或探测事实」冲突——冲突的图基数归面 `01`，本面记录：**今日没有「同 revision 第二条 acquire 边」可走**。
- Guard 谓词闭集无 representation（`D-09=0`）。即使有 observation，也 **进不了** route 决策。

### 2.9 轴 停止 / 前进矩阵（必须回答 #3）

| 输入形态 | HEAD 今日 | 与 `T-O-388` 目标差 |
|----------|-----------|---------------------|
| 静态 HTTP 真 HTML 正文 | acquire `transferred` → decode NFC → `clean.extract.web` | 可前进；无「空壳」观察 |
| 静态 SPA 空壳（有标签无主文） | **前进**（非 `ACQUISITION_EMPTY`）；不升 browser | 应在 **已声明边** 上正向再获取 browser；禁止暗升 |
| 空白/仅空白文本 | `ACQUISITION_EMPTY` 422 **停** | 可保留；不是 reacquire 信号 |
| `acquisition_mode=pdf` 真 `%PDF-` + 未压缩 Tj | `http_static` + `transferred` + 字面量文本 | 前进，但是假「真文本层」 |
| 扫描 PDF / Flate 文本 / 加密 | decode **抛 OCR 码 422 停**，到不了 `pdf.ocr` | 应 **观察** `text_layer=absent\|encrypted`，再由守卫选已声明 OCR 边 |
| local image | decode 空文本 `image_evidence` → clean OCR **503** | 观察正例；503 是能力未部署（`T-O-376` 禁止当通道 DoD） |
| docx/ZIP 高位字节 | acquire `ACQUISITION_DECODE_UNSUPPORTED` **停** | 应标 opaque/office binary，进入已声明 doc 边 |
| docx 碰巧 UTF-8 合法 PK | 误标 `text/plain` **前进** | 假表示；须 ZIP/OPC sniff |
| print_pdf | **无生产路径**；公开 profile 不可选 | acquire 必须产出 kind + PDF bytes |

### 2.10 必须回答（五问收口）

1. **representation fact 最小闭集（草案，非冻结）**：`source_kind`；**实际** `acquisition_capability`；起点 `acquisition_mode`；`representation_kind ∈ {transferred, rendered, print_pdf, image_evidence, opaque_binary}`（枚举待 `G-NH-03`）；`declared/detected/verified_media_type`；`raw_byte_digest/size`；`text_layer ∈ {present, absent, unknown, encrypted, not_applicable}`；decode `canonicalizer` 身份；rendered/print 的 **非恒定** renderer/profile 身份；**有序 acquire/decode history**。不含 strategy/process 选择（那是面 `04`/`01` 的消费）。
2. **多 history 如何 digest**：单值不够（`D-13`）。草案：每个成功 acquire/decode step 各一条 typed evidence；`representation_path_digest = H(ordered step_key × capability × raw_byte_digest × representation_kind)`；供面 `02` 在清洁边选定后写入 `s05_binding_digest`。覆盖≠覆盖未走边。
3. **停止/前进**：见 §2.9。关键：空壳与无层是 **前进到已声明下一边** 的观察，不是 decode 失败；能力未部署是 503 另一码。
4. **decode 失败可否当「应走 OCR」**：否。必须先有诚实 observation；OCR 未部署用独立 503。decode 失败只表示「这个 decoder 不能把该 bytes 变成 Unicode 正文」，不是工人选择器。
5. **`T-O-378` 盗码是否仍在**：是。`types.py:154-159` 仍抛 `CLEAN_OCR_CAPABILITY_UNAVAILABLE` 422。

---

## 3. 借鉴锚定矩阵（Reference Anchor Matrix）★ `[核心]`

> 每个可借鉴点钉到 `path:line` / URL，给**借鉴 verdict**（见图例）。**这是"能借什么"的台账，不是设计决策。**

| 借鉴点 | 来源锚（`path:line` / URL） | 借鉴 verdict | 借什么 / 不借什么 |
|--------|------------------------------|--------------|--------------------|
| MIME sniff + 关键撒谎 fail-closed | `types.py:174-220` · `RA-03-HEAD-01` | `✅借` | 借 detected≠declared 对 PDF/image 关闭；不借「octet 回退 declared」当普遍真理 |
| HTTP evidence / URL 脱敏 | `http_acquisition.py:41-118`；`acquisition_ingest.py:499-537` · `RA-03-HEAD-02` | `✅借` | 借 redacted identity + 固定 Accept；不借任意 header |
| image decode 不造文本 | `acquisition_ingest.py:620-632` · `RA-03-HEAD-03` | `✅借` | 借 `decoded=""` + `image_evidence`；不借把空文本当 admitted clean |
| browser 端口与 static 分离 | `core.py:67-70`；`acquisition_ingest.py:477-485` · `RA-03-HEAD-04` | `✅借` | 借禁止 fallback、缺注入 503；不借常量 `browser_profile` |
| PDF 字面量扫描自称 text layer | `types.py:31-34,144-171` · `RA-03-HEAD-07` | `⛔反例` | 不借正则 Tj 当「真文本层」；可借「未配置就 fail-closed」的意图，但必须换观察码 |
| 无层盗用 OCR 码 | `types.py:154-159` vs `intake/pdf/__init__.py:48-50` · `RA-03-HEAD-08` | `⛔反例` | 不借 422 OCR 码；clean 503 才是能力未部署 |
| `representation_kind` 无 print_pdf | `acquisition_ingest.py:535` vs `clean_preflight.py:46-62` · `RA-03-HEAD-09` | `⛔反例` | 不借「clean 猜测 kind」；print 必须在 acquire 证据里 |
| UTF-8 强制 / ZIP 当 plain | `acquisition_ingest.py:561-564`；本面脚本 · `RA-03-HEAD-11/14` | `⛔反例` | 不借「非 pdf/image = 文本」 |
| evidence 单槽 | `acquisition_ingest.py:89,660` · `RA-03-HEAD-12` | `⛔反例` | 不借覆盖式单值当 path digest |
| 默认组合根无 browser | `api/app.py:330-345` · `RA-03-HEAD-13` | `⛔反例`（相对 `T-O-381` live） | 不把未注入写成 rendered 成功 |
| e2e 注入 fetcher | `tests/e2e/test_source_capability_paths.py:99-101` · `RA-03-HEAD-17` | `⛔反例` | 不把 monkeypatch 当 live 接线（`T-O-378`） |
| static vs rendered vs print-pdf 三表示 | `cleaner_web.ts:245-302`；`action_registry.ts:91-137` · `RA-03-LEGACY-01` | `🔶部分借` | **借**：三种是 **表示** 不是三种 source kind（对齐 `D08-T009`）。**不借**：`action_branch`、CF API、print 绑死 Vision |
| `fetch_options` 任意 headers | `schemas_common.ts:148-150`；`cleaner_web.ts:69-73` · `RA-03-LEGACY-02` | `⛔反例` | 不借任意 UA/cookie/header |
| CF Browser Rendering content/pdf | `cleaner_web.ts:103,152-167` · `RA-03-LEGACY-03` | `⛔反例` | 不借 Cloudflare binding / cookie-banner 硬编码进运行时（`T-O-42`） |
| `browserPDF` 打印+Vision 同 branch；`browserPDF-geminiClean` **未** register 仍被 switch 接受 | `cleaner_web.ts:296-301`；`action_registry.ts:130-137`（无该键） · `RA-03-LEGACY-04` | `⛔反例` | 不借「打印即理解」；不借暗路由别名。print 是 acquire 表示，理解是 clean 边 |
| doc 整包进 Gemini，无本地观察 | `cleaner_doc.ts:68-122` · `RA-03-LEGACY-05` | `🔶部分借` | 借 MIME+size 预检。权威优先序：`inputMeta.mime` → `hint_mime_type` → `application/octet-stream`（`:68-69`）。**不借 hint_mime 权威**、不借无 text_layer 观察 |
| dispatcher 原样下发 `action_branch` | `smind-clean-dispatcher/services/mapper.ts:193-200` · `RA-03-LEGACY-06` | `⛔反例` | 不借 branch taxonomy（`T-O-377`） |
| WHATWG MIME sniff | https://mimesniff.spec.whatwg.org/ §1, §6.4, §7 · `RA-03-WEB-01` | `🔶部分借` | 借「header 可撒谎 + ZIP/PDF/image 魔数 + HTML/XML 信任 supplied」；不借完整 UA 算法当 MKB 安全内核 |
| CDP `Page.printToPDF` | https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-printToPDF · `RA-03-WEB-03` | `🔶部分借` | 借「print 产出 PDF bytes」协议语义与限制；**不选** Chrome 为运行时（交 `G-NH-04/10` + 面 05） |
| Playwright `page.pdf` 限制 | https://playwright.dev/docs/api/class-page#page-pdf · `RA-03-WEB-04` | `🔶部分借` | 借 print media / 改色 / header/footer 脚本不跑、不继承页样式。**不**把 `page.goto` 的「Headless mode doesn't support navigation to a PDF document」写成 print API 失败法（该句在 `page.goto` 段）。不选库 |
| ISO 32000 文本提取 | archive.org ISO/DIS 32000 §9.10 · `RA-03-WEB-05` | `🔶部分借` | 借 ToUnicode/加密/压缩流失败模式；不借把扫描件当「无 Tj」即可 OCR |
| ECMA-376 OPC | https://ecma-international.org/publications-and-standards/standards/ecma-376/ · `RA-03-WEB-07` | `🔶部分借` | 借「docx=zip+xml，不是 UTF-8 文本」；不选 OPC 实现库 |
| PDF 解析器 CVE | GHSA-jfx9-29x2-rv3j（CVE-2025-62708，patched **6.1.3**）**以及** follow-up `GHSA-m449-cwjh-6pw7`（CVE-2025-66019，patched **6.4.0**，~1GB/stream）；CVE-2024-4367 · `RA-03-WEB-08` | `⛔反例` | 不借 in-process 解析不可信 PDF。**6.1.3 不是终点**；默认上限在 6.4.0 才对齐 zlib。隔离/预算交面 05 |
| 诚实 print_pdf + history digest + 观察码分账 | 三渠道均无 substrate-fit 先例可直搬进 S03 七表 | `🆕净新` | 见 §6、§8.2 |

每条 `RA-*` 原子记录见附录 B。

---

## 4. 缺口 / 断点台账 ★ `[核心]`

> 本面核心产出：缺什么、断在哪、多严重、证据何在。**编号稳定，供下游引用。**

| 编号 | 缺口 / 断点 | 严重度 | 证据（`path:line`） | 影响 |
|------|-------------|--------|----------------------|------|
| `NH-RA03-B01` | 无文本层 PDF 在 decode 抛 `CLEAN_OCR_CAPABILITY_UNAVAILABLE` 422，观察失败冒充 OCR 未部署 | `S1 阻断` | `types.py:154-159`；对照 `intake/pdf/__init__.py:48-50`（503） | 扫描件到不了 `pdf.ocr`；违反 `T-O-378/388` |
| `NH-RA03-B02` | acquire 从不写 `representation_kind=print_pdf`；clean/preflight 猜测死代码 | `S1 阻断` | `acquisition_ingest.py:533-536`；`clean_preflight.py:46-62`；`strategies.py:67-77` | `T-O-381` 的 `web.browser_print_pdf` 格无法诚实接通 |
| `NH-RA03-B03` | evidence 单值 1+1，声明式 reacquire 边 0；digest 不含路径 | `S1 阻断` | `D-13`；`acquisition_ingest.py:89,660`；13 图各 1 acquire | 无法实现 `T-O-388` 有限正向再获取与路径封闭 |
| `NH-RA03-B04` | representation-aware guard = 0；route context 不读 decode/acquire facts | `S1 阻断` | `D-09`；`models.py:249-255`；`runtime_materialize.py:101-117` | 即使有观察，图也无法选边（与面 01 交界） |
| `NH-RA03-B05` | 非 PDF/image 强制 UTF-8；office/opaque 在 acquire 死亡 | `S1 阻断` | `acquisition_ingest.py:561-564`；本面 docx-high 实测 | `doc.document_understanding` 物理不可达 |
| `NH-RA03-B06` | `local-pdf-literal-text.v1` 不是真文本层观察器 | `S1 阻断` | `types.py:100-171`；ISO §9.10 | `T-O-378` 假实现；压缩/CID/加密全误判 |
| `NH-RA03-B07` | **消费** `NH-RA05-B01`：默认组合根 `browser_fetcher=0`；live rendered/print 不存在。本面只证表示层未接线 | `S1 阻断`（表示后果） | `D-21`；`api/app.py:330-345`（注入权威在面 `05`） | `T-O-376/381` 禁止 503 当通道 DoD |
| `NH-RA03-B08` | 公开 profile 仍用 mode 选图；print-pdf 图不可选 | `S2 重要` | `config_snapshots.py:504-506`；`lsrag_definition.py:929-940,1048-1054` | 与 `T-O-387` 叙事冲突；再获取无处可画（面 01 主责） |
| `NH-RA03-B09` | preflight 用起点 mode 校验 capability，不能容忍已声明再获取 | `S2 重要` | `clean_preflight.py:629-657` | 即使画边，封口会打回 |
| `NH-RA03-B10` | SPA 空壳无 typed 观察；`ACQUISITION_EMPTY` 只覆盖空白 | `S2 重要` | `acquisition_ingest.py:65-66` | 「空壳→browser」没有守卫事实 |
| `NH-RA03-B11` | ZIP/OPC 魔数未嗅探；PK 可被标 `text/plain` | `S2 重要` | `types.py:174-199`；`D-03-F03` | 假表示进入文本 decode |
| `NH-RA03-B12` | `browser_profile` 恒为 `injected-browser-renderer.v1` | `S2 重要` | `acquisition_ingest.py:536` | 伪造 renderer 版本；`T-O-378` 同类谎言 |
| `NH-RA03-B13` | source e2e 以 monkeypatch 冒充 browser/static 接线 | `S2 重要` | `test_source_capability_paths.py:99-101` | 假绿；面 09 横切，本面点名 |
| `NH-RA03-B14` | image decode 的 `decode_capability` 仍标 `intake.decode.text_json_html` | `S3 次要` | `acquisition_ingest.py:626-627` | 能力名撒谎，干扰 preflight expected_decode（`:658`） |

---

## 5. 跨功能系统一致性 ★ `[核心]`

- **5.1 整体形态一句话**：kind 选 **一张** 无环图（面 01）；acquire 是起点边，decode **只产出** representation facts；有限正向再获取写 history；清洁工人在表示已知之后绑定一次（面 02/04）；runtime 只供给能力、不发明 kind（面 05）。
- **5.2 功能间一致性契约（不变量 C1..Cn）**：

| 编号 | 不变量 | 跨哪些面/模块 | 违反后果 |
|------|--------|----------------|----------|
| `NH-C-20` | representation / acquire / decode **facts** 由面 03 拥有；面 04 只消费 typed representation，不得重新 fetch/decode | `03→04` | 双解码、假 clean 输入 |
| `NH-C-21` | decode 是观察器，不是工人选择器；无层 ≠ OCR 未部署 | `03/04/05` | 盗码、扫描件永不到 OCR |
| `NH-C-22` | `print_pdf` 必须由 **acquire 证据** 写出 kind 且 bytes 为 PDF；clean 不得猜测 | `03/04/05` | print 策略死键、HTML 进 pdf_llm |
| `NH-C-23` | 能力未部署用独立 5xx（browser/OCR/LLM）；观察缺失用 4xx **观察码** | `03/05/09` | 503 当通道 DoD 或 422 当 503 |
| `NH-C-24` | 再获取仅 **已声明、无环、正向** 边；每 acquire step 至多成功一次；禁止 try-all / 暗升 | `01/03/02` | 环、静默换表示（`T-O-378/340`） |
| `NH-C-25` | history digest 覆盖 **实际走过** 的 acquire/decode；单槽覆盖非法 | `03/02/09` | replay 与实际路径不一致 |
| `NH-C-26` | representation-aware guard 只读 durable facts（`G-NH-03` 住所） | `01/03/02` | 守卫读 handler 内存 → 不可重放 |
| `NH-C-27` | runtime adapter **不得**发明 `representation_kind`；只报告 renderer/parser 身份与 readiness | `05/03` | 假 rendered / 假 text_layer |
| `NH-C-28` | 默认组合根未注入 browser ≠ 允许 static fallback 伪造 rendered | `03/05` | `core.py` 已禁；测试 monkeypatch 仍可假绿 |
| `NH-C-29` | opaque/office bytes 是 binary representation，不是 UTF-8 文本 | `03/04/06` | docx 在 acquire 死亡或当 plain 前进 |

- **5.3 数据 / 控制流贯穿图**：

```text
caller typed source_kind + optional acquisition_mode (start)
        │
        ▼
[面01] kind 图：acquire_static ─┐
        │                      ├─(declared forward, acyclic)─► acquire_browser / acquire_print
        │                      │         ▲
        ▼                      │         │ 仅当 representation fact 命中已登记 guard
acquire Process ──► bytes + acquisition_evidence[i]
        │
        ▼
decode Process ──► observation: media / text_layer / image_evidence / opaque
                   decode_evidence[i]     （禁止抛 OCR-unavail）
        │
        ├─ need reacquire? ──► 只走图上已画边，append history，step 成功至多一次
        │
        ▼
representation fact 闭集 + path digest  ──► [面02] 晚绑定清洁边并封闭 s05 digest
        │
        ▼
[面04] 只消费 typed fact 做 admitted clean
        │
        ▼
[面05] 若边需要 browser/PDF/OCR：readiness 必须为真，否则 503 另一码
```

消费：面 01 消费「最小 fact 字段名」以登记 predicate；面 02 消费 history digest；面 04 消费 kind/media/text_layer；面 05 消费「需要哪种 runtime 能力」而非产品路由。本面 **不**替邻面设计图或 adapter。

---

## 6. 净新契约 / 架构边界草案 `[核心]`

> 无先例可借（§3 标 🆕）处，从零草拟契约与边界。**草案，非冻结。**

- **6.1 净新聚合 / 解耦点**：
  - `NH-N-03-01` **RepresentationFact** 最小闭集（§2.10 问 1）——今日散落在 `acquisition_evidence` 字典与 decode 局部字段。
  - `NH-N-03-02` **AcquireDecodeHistory**（有序、每 step 至多一条成功）+ `representation_path_digest`。
  - `NH-N-03-03` **观察码 vs 能力码** 分账：`text_layer=absent` 不是 `CLEAN_OCR_CAPABILITY_UNAVAILABLE`。新码字面 **不在本面冻结**。
  - `NH-N-03-04` **诚实 print acquire 协议**：输入 URL + 已声明 print 边 → 输出 PDF bytes + `representation_kind=print_pdf`。引擎未选。
  - `NH-N-03-05` **opaque/office binary 身份**：ZIP/OPC/octet 不得进 UTF-8 文本 decode。
  - `NH-N-03-06` **空壳观察**（可选字段）：与 clean 质量分账；是否进入闭集见 `G-NH-13`。

- **6.2 净新契约叙述规格**：
  - **输入**：已获取 bytes、declared media、capability、mode、（HTTP）redacted URL evidence。
  - **输出**：verified media；representation_kind；text_layer 观察；raw_byte_digest；decode canonicalizer；history append；**不**输出 clean_text、不选择 `CleanStrategyKey`。
  - **边条件**：无声明边不得再获取；print 边失败不得把 HTML 标成 print_pdf；缺 browser 注入必须 503 而非 rendered 假成功。
  - **权威住所候选**（只 MARK）：见 `G-NH-03`。

- **6.3 架构边界（与既有 / 相邻面）**：
  - 沿用：`mkb.acquisition-evidence.v1` schema_version、redacted URL、budget、binary latin-1 运输、image 空文本、browser/static 端口分离、HttpAcquirer 无 caller headers。
  - 重 substrate：`_extract_pdf_text` 观察出口、`representation_kind` 枚举、history、preflight expected capability。
  - 净新：print_pdf 生产、text_layer 观察类型、opaque sniff、path digest。
  - 不越界：不改 10 strategy 语义（04）；不选库（05）；不画 graph 边（01）；不改 DDL 除非面 02 的 digest 字段与 `G-NH-03` 要求同行。

---

## 7. Substrate-fit / 技术路线过滤 ★ `[核心]`

> **核心防线**：把每个"借来的机制"按**本仓技术路线 / 现实约束**降级或重映射。

| 借鉴点 | 原机制（参考处） | 是否冲突本仓路线 / 约束 | 落地形态（降级 / 重映射 / 直采） |
|--------|------------------|--------------------------|-----------------------------------|
| MIME sniff | WHATWG UA 算法 | 单体 Python、无浏览器 XSS 模型；不得自由表达式 | **降级**：保留 PDF/image 魔数 + 关键 mismatch fail-closed；**补** ZIP/OPC；不实现完整 HTML 标签表 |
| 三表示 | legacy `htmlCrawl` / `browserFetch` / `browserPDF` | 禁止第五 kind、禁止 `action_branch` | **重映射**：同一 `http_resource` 图内三条 acquire 表示边 |
| CF `/browser-rendering/{content,pdf}` | `cleaner_web.ts:103,152` | `T-O-42` 禁 CF | **不落地**；print 语义改走本地已声明 acquire（选型面 05） |
| 任意 `fetch_options.headers` | `schemas_common.ts:150` | eq-only、无秘密进 descriptor | **不落地**；HttpAcquirer 已禁 |
| print+Vision 同 branch | `browserPDF` switch | 三轴拆分、晚绑定 | **拆**：print=acquire 表示；understanding=`pdf.*` clean 边 |
| Gemini 整包 doc | `cleaner_doc.ts` | 无本地 observation；云模型 | **降级**：先 bytes+MIME 观察，再由面 04 决定是否 LLM |
| CDP `printToPDF` | Chrome 协议 | 本面禁选引擎；需隔离（`G-NH-10`） | **只借协议能力矩阵**；实现交面 05 |
| Playwright `page.pdf` | 官方限制 | 同上；print media 与 CSS 颜色改写 | **只借失败法** |
| ISO ToUnicode 提取 | §9.10 | 无 PDF 依赖（`D-20=0`）；解析器 CVE | **观察合同**先于库；库+沙箱交 05 |
| pypdf/PDF.js CVE | GHSA / CVE-2024-4367 | 不可信 PDF in-process | **反例**：默认假设 parser 敌对 |
| image 空文本 | HEAD `_decode` | 无冲突 | **直采** |
| URL redaction | HEAD HttpAcquirer | 无冲突 | **直采** |
| 单槽 evidence | HEAD state | 与 `T-O-388` 冲突 | **废弃覆盖语义**，改为 history |
| 字面量 PDF | HEAD types.py | 与 `T-O-378` 冲突 | **废弃作为 text_layer 权威** |

---

## 8. 反例坑表 + 净新表 `[核心]`

### 8.1 反例坑表 ⛔

| 反例 | 来源锚 | 为什么不可借 |
|------|--------|--------------|
| 正则捞 `(...) Tj` 称已落地文本层 | `types.py:144-171` | 压缩流/CID/加密/扫描件全盲；`T-O-378` |
| decode 抛 `CLEAN_OCR_CAPABILITY_UNAVAILABLE` 422 | `types.py:154-159` | 观察≠能力；同码 503 在 clean |
| clean 侧猜测 `print_pdf` | `clean_preflight.py:46-62` | 表示必须来自 acquire 证据 |
| `browser_profile` 常量 | `acquisition_ingest.py:536` | 假 renderer 身份 |
| static 失败自动升 browser | 产品禁令 `T-O-388`；HEAD 尚无自动升，但 e2e 可手工注入 | 无证据暗升 |
| 任意 headers/cookie | `cleaner_web.ts:69-73` | 描述符注入攻击面 |
| CF browser binding | `cleaner_web.ts:103,152` | `T-O-42` |
| print 与 vision 绑死 | `cleaner_web.ts:296-301` | 破坏晚绑定与三轴 |
| `action_branch` 下发 | `mapper.ts:198` | `T-O-377` |
| monkeypatch fetcher 当 live | `test_source_capability_paths.py:99-101` | `T-O-378`；面 09 防假绿 |
| 空 `clean_text` 当成功 | QNA `T-O-378/383`（clean 侧） | 本面：空 decode 文本可以是合法 **观察**（image），但不得当 admitted clean |
| in-process PDF 解析无沙箱 | GHSA-jfx9-29x2-rv3j；CVE-2024-4367 | DoS/JS/逃逸；交面 05 |
| docx UTF-8 decode | HEAD `:561-564` vs ECMA-376 | 错表示 |

### 8.2 净新表 🆕

| 项 | 为什么无先例 | 草案落点 |
|----|--------------|----------|
| RepresentationFact 最小闭集 + durable authority | HEAD 字典临时字段；legacy 无独立 fact 行；外部规范不定义 MKB 七表住所 | §6.1 `NH-N-03-01`；`G-NH-03` |
| Acquire/decode history + path digest | `D-13` 单值；无外部「S03 七表 history」可搬 | `NH-N-03-02` |
| 观察码 / 能力码分账 | HEAD 撞码；ISO 只定义提取语义不定义 HTTP 码 | `NH-N-03-03` |
| 诚实 print_pdf acquire | legacy 把 print 焊在 CF+Gemini；HEAD 不生产 kind | `NH-N-03-04`；`G-NH-04` 只供 runtime |
| opaque/office binary 表示 | WHATWG 有 zip sniff，HEAD 无；无 MKB 先例 | `NH-N-03-05` |
| 空壳观察是否进入 fact 闭集 | 无行业标准字段名可搬进 eq-only guard | `G-NH-13` |

---

## 9. 验收格栅草案（防假绿）`[核心]`

> 草案——落地验收归下游执行计划。测试层不可互换。

| 功能 F | 收口目标（一句话可验证） | Test-ID（拟） | 测试层 | 防假绿要点 |
|--------|--------------------------|----------------|--------|------------|
| sniff/verify | PDF/image 撒谎 → `ACQUISITION_MEDIA_MISMATCH`；ZIP 不得成 `text/plain` | `NH-A-03-01` | 单元 | 不用 Content-Type 单独当 verified |
| PDF 无层观察 | 无 ToUnicode/无解压文本 → typed `text_layer=absent`（或等价观察），**禁止** `CLEAN_OCR_CAPABILITY_UNAVAILABLE` | `NH-A-03-02` | 单元 | 不得用空字符串当 present；不得 422 OCR 码 |
| image 观察 | image decode 成功且 `decoded==""` 且 kind=`image_evidence` | `NH-A-03-03` | 单元 | 空文本 ≠ clean 成功 |
| opaque/docx | PK/高位 office bytes 不得 UTF-8 成功；须 binary/opaque | `NH-A-03-04` | 单元 | 禁止 PK+ASCII 当 plain 前进 |
| print_pdf 诚实 | acquire 证据含 `representation_kind=print_pdf` 且 `%PDF-` bytes | `NH-A-03-05` | 集成 | 禁止 clean 猜测；禁止 HTML 当 print |
| 有限再获取 | static 空壳仅在 **已声明** browser 边前进；无边则停；history 长度=2 | `NH-A-03-06` | 集成 | 禁止 try-all；禁止覆盖第一条 evidence |
| 能力未部署 | 无 browser 注入 → 503 `ACQUISITION_BROWSER_*`；不得写 rendered | `NH-A-03-07` | 集成 / default-root e2e | **禁止** monkeypatch 冒充 live |
| 盗码回归 | `types.py` decode 路径源码与单测均不得再抛 OCR-unavail | `NH-A-03-08` | 单元 | `test_intake_clean_dispatch.py:77` 今日只断言 `_clean` 不含该码，**不够** |
| 默认组合根 | 未注入 browser 的 app 不得对 browser/print 策略出向量 | `NH-A-03-09` | default-root e2e | 503 不是通道 DoD（`T-O-376`）；本面只证表示层失败诚实 |
| 假绿封口 | source capability e2e 若仍 patch fetcher，不得标 live | `NH-A-03-10` | 面 09 横切 | 检索/facet mega 不在本面 |

---

## 10. 优先级建造建议 + owner-gate 候选 `[核心]`

- **10.1 建造顺序（依赖序，分批不一次性深做）**：

| 顺序 | 工作簇 | 依赖 | 复用判定 |
|------|--------|------|----------|
| `P0-a` | 拆 decode 观察码 / 停止盗用 OCR 码；PDF 字面量降为「非权威 hint」 | `T-O-378/388`；面 04 消费观察 | `♻️重substrate` |
| `P0-b` | RepresentationFact 字段闭集 + 单条 evidence 校验（仍单槽可先） | `G-NH-03` 住所未裁前用 Process output 过渡须显式 MARK | `♻️重substrate` |
| `P0-c` | opaque/ZIP sniff + 禁止 UTF-8 误通 | `NH-RA03-B05/B11` | `♻️重substrate` |
| `P0-d` | history 列表 + path digest + preflight 改认实际路径 | 面 02 digest 封闭时刻 | `🆕净新` |
| `P1-a` | 诚实 print_pdf acquire 协议（**不**在本面选引擎） | 面 01 画边；面 05 runtime | `🆕净新` |
| `P1-b` | 空壳观察是否入闭集 | `G-NH-13` | `🆕净新` |
| `P2` | default-root 真 browser 接线验收 | 面 05 注入；面 09 mega | 本面只出 fact 合同 |

- **10.2 owner-gate 候选（只 MARK 不裁决 → 上交 [[assessment-index]] §4 / 下游决策登记）**：

| gate-ID | 决策点 | 候选选项（不预设倾向） | 影响 |
|---------|--------|------------------------|------|
| `G-NH-03` | representation route fact 的 durable authority | `Process output evidence` / `正式 representation fact row` / `其他 typed authority` | 守卫、replay、history 住所；与面 01 共用 |
| `G-NH-04` | PDF/browser/multimodal runtime 边界（本面 **只点到，不选**） | `扩既有 inference request/adapter` / `独立本地 adapter 但复用 pool` / `独立 capability supply` | print/真文本层/OCR **供给**；本面不冻结引擎 |
| `G-NH-13`（本面新 MARK） | 空壳 / 主文缺失是否进入 representation 闭集 | `typed fact（可供 eq guard）` / `仅 clean 质量信号（面 04）` / `其他经证据支持方案` | 决定 static→browser 再获取能否声明式 |

**无推荐赢家。** `G-NH-10` 隔离线由面 05 深挖，本面仅把解析器 CVE 记为安全反例。`G-NH-13` 只 MARK；index §4 v0.2 已登记本 gate（仍不裁决）。`G-NH-11` 留给面 02 seal 事务。默认根注入 **消费** `NH-RA05-B01`。

---

## 11. 核验记录 `[核心]`

> 对抗性自检：本文每个关键锚点是否真核验过；与任何叙事/记忆冲突处以实测为准并标「修正」。

| 锚点（host-ID） | 是否核验 | 方式（grep/read/run） | 备注 / 修正 |
|------------------|----------|------------------------|--------------|
| `RA-03-HEAD-01` sniff/verify | `✅` | read `types.py:174-220`；run sniff 脚本 | octet 回退 declared 是半开窗口，未写成「完全 fail-closed」 |
| `RA-03-HEAD-02` URL redaction | `✅` | read `http_acquisition.py:41-118`；read unit test `:57-92` | `HttpAcquisitionResult.evidence()` 无 `transport_profile`；profile 只在 str/bytes 注入分支 |
| `RA-03-HEAD-03` image 空文本 | `✅` | read `acquisition_ingest.py:620-632` | decode_capability 名仍是 `text_json_html`（B14） |
| `RA-03-HEAD-04` 端口分离 | `✅` | read `core.py:67-70`；`api/app.py:330-345` | 注释禁 fallback；组合根确认无 browser_fetcher |
| `RA-03-HEAD-07/08` 字面量+盗码 | `✅` | read `types.py:144-159`；run `_extract_pdf_text` 无层 | **确认仍为 422 OCR 码**；与 thoughts 叙事一致，非过时记忆 |
| `RA-03-HEAD-09` 无 print_pdf | `✅` | `rg representation_kind src/` 仅 535 与 630 赋值 | clean_preflight 是消费者不是生产者 |
| `RA-03-HEAD-11/14` docx/ZIP | `✅` | run `_representation_from_bytes` PK 高位/ASCII | 高位 → `ACQUISITION_DECODE_UNSUPPORTED`；ASCII PK → 误 `text/plain` |
| `D-13` reacquire=0 | `✅` | 13 张图脚本；`lsrag_definition.py:299-306` | 与 index 一致，未另估 |
| `D-20/D-21` | `✅` | read `pyproject.toml:13-21`；`api/app.py:330-345` | 未改数字 |
| `RA-03-LEGACY-01..06` | `✅` | read `cleaner_web.ts` `cleaner_doc.ts` `action_registry.ts` `mapper.ts` `schemas_common.ts` | **未** import/编译/运行 legacy |
| `RA-03-WEB-01` | `✅` | `web_search` + `web_fetch` mimesniff.spec.whatwg.org 2026-07-17 | 规范单源 MARK |
| `RA-03-WEB-03` | `✅` | `web_fetch` CDP tot Page.printToPDF | 能力+限制 |
| `RA-03-WEB-04` | `✅` | `web_fetch` playwright class-page | `page.pdf` 段：print media/改色/模板沙箱。**「Headless 不能导航 PDF」在 `page.goto` 段**，已从 WEB-04 原子句拆出 |
| `RA-03-WEB-05` | `✅` | archive.org ISO/DIS 32000 §9.10 行 32363+ | DIS 草案；PDF Association 页被 CDN 挑战，改用 pdfa.org/pdf-standards 搜索摘要 + DIS 正文 |
| `RA-03-WEB-07` | `✅` | `web_fetch` ecma-international.org ECMA-376 | Part 2 OPC 2021-12；LOC 页 Cloudflare 拦截，未用 LOC 作独立打开源 |
| `RA-03-WEB-08` | `✅` | `web_fetch` GHSA-jfx9 **以及** GHSA-m449 | **修正**：6.1.3 不是终点；follow-up patched 6.4.0 |
| `G-NH-03/04` | `✅` | read index §4 | 只 MARK，无赢家 |
| pytest 小集合 | `部分` | 本面以脚本测 sniff/decode；**未**在本次重跑 pytest（防超时冒充全绿） | 写入诚实：unit 命令列出但本次核验以 read+脚本为主 |
| `T-P-NH-*` / thoughts | `✅` 当叙事 | 未当 HEAD 事实 | 初判「从不写 print_pdf / 盗码」已被 HEAD 证实，不是规划已落地 |

**声称 vs 实测修正**：index 站①「print_pdf 从不生产、无层死在 decode」与 HEAD **对齐**，不是过时。QNA `T-O-378` 是谎言清单不是「decode 必须失败」的产品法（QNA `:776`）——本面按目标法写缺口，不把 HEAD 失败写成产品要求。

---

## 12. 收尾 Verdict 与交接 `[核心]`

- **本面裁定**（分析裁定，非 owner 产品裁决）：面 03 为 **P0/🔴**。可复用底座 = sniff 关键 mismatch、URL 脱敏、image 空文本、browser/static 分离、预算关闭。S1 阻断 = 盗码、无 print_pdf、无 history/再获取、无 representation guard、opaque UTF-8、字面量 PDF、默认根无 browser。representation 最小闭集与 history digest 为净新契约；print 与真文本层的 **供给** 交 `G-NH-04` + 面 05，本面不选库。
- **交接下游**：缺口台账（§4）→ 规划；净新契约（§6）→ 设计；owner-gate 候选（§10.2：`G-NH-03` / `G-NH-04` / `G-NH-13`）→ 决策登记；验收格栅（§9）→ 执行计划；不变量 `NH-C-20..29` → 面 01/02/04/05/09 对账。
- **冻结前置**：① 面 01 确认 guard 可消费的 fact 字段；② `G-NH-03` 住所已裁；③ 盗码与 print_pdf 生产有可测合同；④ 与面 05 的 runtime 边界不把本面协议写成库选型。在此之前本文保持 **`draft`**，禁止标 `frozen`/`reviewed`。

---

## 附录 A · 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-08-29 | Grok analysis-fleet / review-fleet | 初稿（measure-first + 三渠道锚定 + 缺口台账）；状态 `draft` |
| v0.2 | 2026-08-29 | Grok fix-fleet | 吸收已核实 review：R3-I01 `pageRanges` 改为 cap+ignore/零页才 error；R3-I02 goto 限制拆出 print 锚；R3-I03 并入 GHSA-m449；R2-I05 MIME 权威改为 `inputMeta.mime` 优先；R2 §5 补未注册别名与 REA passthrough；R3-I13 ECMA 着陆页降为线索；R4-I01 `G-NH-11`→`G-NH-13`；R4-I11/I12 B07 消费 05-B01、去掉模板占位 ID。状态仍 `draft` |

---

## 附录 B · Reference Anchor 原子记录

> 每条：结论原子句 / 来源与版本或访问日 / 正例或反例 / 置信 / substrate-fit / 命中缺口。

| ID | 结论原子句 | 来源 | 正/反 | 置信 | substrate-fit | 命中 |
|----|------------|------|-------|------|---------------|------|
| `RA-03-HEAD-01` | PDF/image 声明与 detected 不一致时 fail-closed `ACQUISITION_MEDIA_MISMATCH` | HEAD `types.py:209-217` · 2026-08-29 | 正 | HEAD 实测 | `✅借` | 支撑 sniff 底座 |
| `RA-03-HEAD-02` | HTTP evidence 只含 redacted URL identity，不含 raw query/userinfo | `http_acquisition.py:41-118`；unit `:57-85` | 正 | HEAD 实测 | `✅借` | — |
| `RA-03-HEAD-03` | image decode 不制造文本，标 `image_evidence` | `acquisition_ingest.py:620-632` | 正 | HEAD 实测 | `✅借` | 对照 B01 盗码 |
| `RA-03-HEAD-04` | browser fetcher 独立注入；缺则 503；禁止 fallback static | `core.py:67-70`；`acquisition_ingest.py:477-485` | 正 | HEAD 实测 | `✅借` | B07 是组合根未用该底座 |
| `RA-03-HEAD-05` | HttpAcquirer 不接受 caller headers/cookies | `http_acquisition.py:1-6,221-245` | 正 | HEAD 实测 | `✅借` | 对照 LEGACY-02 |
| `RA-03-HEAD-06` | 超预算 fail-closed `ACQUISITION_BUDGET_EXCEEDED` | `acquisition_ingest.py:570-578`；`test_ns5_phase4.py:79-91` | 正 | HEAD 实测 | `✅借` | — |
| `RA-03-HEAD-07` | PDF「文本层」= `%PDF-` + Tj 正则，decoder=`local-pdf-literal-text.v1` | `types.py:31-34,144-171` | 反 | HEAD 实测 | `⛔反例` | `NH-RA03-B06` |
| `RA-03-HEAD-08` | 无字面量时 decode 抛 `CLEAN_OCR_CAPABILITY_UNAVAILABLE` 422 | `types.py:154-159`；脚本 no-layer | 反 | HEAD 实测 | `⛔反例` | `NH-RA03-B01` |
| `RA-03-HEAD-09` | HTTP `representation_kind` 仅 `rendered\|transferred`，无 `print_pdf` | `acquisition_ingest.py:535` | 反 | HEAD 实测 | `⛔反例` | `NH-RA03-B02` |
| `RA-03-HEAD-10` | `browser_profile` 恒为 `injected-browser-renderer.v1` | `acquisition_ingest.py:536` | 反 | HEAD 实测 | `⛔反例` | `NH-RA03-B12` |
| `RA-03-HEAD-11` | 非 PDF/image UTF-8 失败 → `ACQUISITION_DECODE_UNSUPPORTED` | `acquisition_ingest.py:561-564`；docx-high 脚本 | 反 | HEAD 实测 | `⛔反例` | `NH-RA03-B05` |
| `RA-03-HEAD-12` | state 仅单份 `acquisition_evidence` / `decode_evidence` | `acquisition_ingest.py:89,660` | 反 | HEAD 实测 | `⛔反例` | `NH-RA03-B03` |
| `RA-03-HEAD-13` | 默认 `IntakePipeline` 未传 `browser_fetcher`/`clean_llm` | `api/app.py:330-345` | 反 | HEAD 实测 | `⛔反例`（相对 live 矩阵） | `NH-RA03-B07` |
| `RA-03-HEAD-14` | `PK\x03\x04` sniff 为 `text/plain`（UTF-8 合法时） | 脚本 `D-03-F03` | 反 | HEAD 实测 | `⛔反例` | `NH-RA03-B11` |
| `RA-03-HEAD-15` | 13 张 single 图各 1 acquire，reacquire 边 0；guard 无 representation | 脚本；`models.py:249-255` | 反 | HEAD 实测 | `⛔反例`（相对 `T-O-388`） | `NH-RA03-B03/B04` |
| `RA-03-HEAD-16` | preflight 用 descriptor mode 反推 capability | `clean_preflight.py:629-636` | 反 | HEAD 实测 | `⛔反例` | `NH-RA03-B09` |
| `RA-03-HEAD-17` | source e2e 赋值 `_http_fetcher`/`_browser_fetcher` | `test_source_capability_paths.py:99-101` | 反 | HEAD 实测 | `⛔反例` | `NH-RA03-B13` |
| `RA-03-HEAD-18` | 带标签空壳 HTML 可 acquire 成功，无 shell 观察 | `acquisition_ingest.py:65-66`；html-shell 脚本 | 反 | HEAD 实测 | `⛔反例` | `NH-RA03-B10` |
| `RA-03-LEGACY-01` | universal 六 branch 实为 static/rendered/print 三表示 × 是否 Gemini | `action_registry.ts:91-148`；`cleaner_web.ts:245-302` | 正（语义） | 仓内代码考古 | `🔶部分借` | 支撑闭集，不借 taxonomy |
| `RA-03-LEGACY-02` | `fetch_options` 为开放 record，crawl 合并任意 headers | `schemas_common.ts:148-150`；`cleaner_web.ts:69-73` | 反 | 仓内代码考古 | `⛔反例` | — |
| `RA-03-LEGACY-03` | browser 文本/PDF 直调 `api.cloudflare.com/.../browser-rendering/{content,pdf}` | `cleaner_web.ts:103,152-167` | 反 | 仓内代码考古 | `⛔反例` | `T-O-42` |
| `RA-03-LEGACY-04` | `browserPDF` 与未注册别名 `browserPDF-geminiClean` 同一 pipeline：打印后强制 Vision | `cleaner_web.ts:296-301`；registry **未** register 该键 | 反 | 仓内代码考古 | `⛔反例` | B02；暗路由 ≠ 闭集 |
| `RA-03-LEGACY-05` | doc 读取 `source_file` buffer；MIME 权威 `inputMeta.mime` 优先、hint 回退、缺则 octet-stream；整包 Gemini，无 text_layer 观察 | `cleaner_doc.ts:68-122` | 反（观察法）/部分（size cap） | 仓内代码考古 | `🔶部分借` | B05 |
| `RA-03-LEGACY-07` | REA query `.passthrough()` + 强制明文 `cookie`/`user_agent` | `realestate/schemas.ts:90-110` | 反 | 仓内代码考古 | `⛔反例` | D08-REF-05 / D08-X08/X09 |
| `RA-03-LEGACY-06` | dispatcher 把 `action_branch` 写入 workflow_payload 原样下发 | `mapper.ts:193-200` | 反 | 仓内代码考古 | `⛔反例` | 面 01 亦引用 |
| `RA-03-WEB-01` | HTTP `Content-Type` 常与正文不符；须有 sniff 规范；HTML/XML supplied 优先 | https://mimesniff.spec.whatwg.org/ §1, §7 · Living Standard 2026-07-17 · 访问 2026-08-29 | 正 | 规范单源 | `🔶部分借` | B11 对照 ZIP 表 §6.4 |
| `RA-03-WEB-02` | archive 模式含 `50 4B 03 04` → `application/zip` | 同上 §6.4 | 正 | 规范单源 | `🔶部分借` | `NH-RA03-B11` |
| `RA-03-WEB-03` | `Page.printToPDF` 把页面打印为 PDF（base64/stream）；非 HTML GET | https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-printToPDF · 访问 2026-08-29 | 正 | 官方协议 | `🔶部分借` | B02；不选 Chrome |
| `RA-03-WEB-04` | `page.pdf()` 默认 print media、改色；header/footer 脚本不跑、不继承页样式 | https://playwright.dev/docs/api/class-page#page-pdf · 访问 2026-08-29 | 正（限制） | 官方文档 | `🔶部分借` | print 失败法给面 05；goto 导航 PDF 限制另挂 `page.goto` |
| `RA-03-WEB-04b` | Headless **不能导航 PDF 文档**（非 print API） | 同页 `page.goto` 段 · 访问 2026-08-29 | 正（限制） | 官方文档 | `🔶部分借` | 不得塞进 `page.pdf` 锚 |
| `RA-03-WEB-05` | PDF 文本提取 = 字符码→Unicode（标准编码/ToUnicode/ActualText）；无映射则不知字符义 | ISO/DIS 32000 §9.10.1-9.10.2 · archive.org · 访问 2026-08-29 | 正 | 标准草案正文 | `🔶部分借` | B01/B06 |
| `RA-03-WEB-06` | 加密字典可限制提取；内容常在 Flate/LZW 流中 | ISO/DIS 32000 TOC 7.4 Filters / 7.6 Encryption；GHSA LZW DoS | 反（对字面量法） | 标准+advisory | `⛔反例`（对 HEAD 扫描） | B06 |
| `RA-03-WEB-07` | Office Open XML 由 OPC（ZIP 物理包 + 部件 MIME）定义；ISO/IEC 29500 | ECMA-376 **Part 2** 5th ed. December 2021（着陆页只作发现线索：https://ecma-international.org/publications-and-standards/standards/ecma-376/）· 访问 2026-08-29 | 正 | 规范条款（着陆页非 primary 正文） | `🔶部分借` | B05 |
| `RA-03-WEB-08` | PDF 解析器可 DoS（pypdf LZW CVE-2025-62708 patched 6.1.3 **不是终点**；follow-up CVE-2025-66019 patched 6.4.0）或 JS 执行（PDF.js CVE-2024-4367） | GHSA-jfx9-29x2-rv3j；GHSA-m449-cwjh-6pw7；Codean Labs 2024-05-20 | 反 | advisory/原始研究 | `⛔反例` | 面 05 隔离；本面不选库 |
| `RA-03-BASELINE-01` | `AcquisitionEvidence` = 一次 acquire 的 typed representation/media/encoding/budget 证据，不是 Snapshot | `spec-glossary.md:213` | 正 | 仓内 frozen 词 | `✅借`（词汇） | 与 HEAD 单槽不完全等同，冲突登记为 B03 |
| `RA-03-BASELINE-02` | web/pdf/doc 不同规则 = CleanStrategy 不是 source kind；print_pdf 是表示 | `D08-T009`；D08 `:166,233` | 正 | 仓内 **draft/owner-review**，不覆盖 QNA/HEAD | `🔶部分借` | 与 LEGACY-01 同向 |
| `RA-03-BASELINE-03` | 禁止吸收任意 headers、CF、silent skip | `D08-T004` | 反（禁借清单） | 仓内 **draft/owner-review** | `⛔反例` | 对齐 LEGACY-02/03 |

### 渠道事实核查登记

| 渠道 ID | 渠道 | 本面是否满足最低包 |
|---------|------|--------------------|
| HEAD 渠道满足性 | HEAD 正例≥1 反例≥1 + path:line | 满足（正 01-06，反 07-18） |
| LEGACY 渠道满足性 | clean 目录检索 + 借/不借 | 满足（`cleaner_web/doc`、`action_registry`、dispatcher `mapper`） |
| WEB 渠道满足性 | 竞争路线尽量双 primary + 至少一条限制 | 满足（MIME 规范单源已 MARK；print 用 CDP+Playwright 双源；解析器用 GHSA-jfx9 + GHSA-m449） |
