# Nano-Agent 行动计划

> 服务业务簇: `MKB / new-harvest / intake-four-channel-live`
> 计划对象: `local parser / browser.render / browser.print_pdf / OCR / Vision / DU 真实供给 + isolation + readiness + SBOM`
> 类型: `new`（供给）+ `upgrade`（wiring / health / S11 request）
> 作者: `Grok workflow new-harvest-nh6-nh9-action-plans`
> 时间: `2026-08-29`
> 文件位置: `docs/plan/new-harvest/AP-NH6-local-runtime-supply-and-security.md`
> 上游前序 / closure:
> - `docs/eval/new-harvest/final-execution-plan.md` v1.0 `frozen` §7.6（唯一执行基线 · 台账 A/B/C/D）
> - DAG：`AP-NH1` `stop-or-go.md=GO` **且** `NH1-T06` 三次 smoke pytest PASS（smoke ≠ 本 AP DoD）；`AP-NH3` actual/表示诚实（`NH3-04/05` 观察/能力分码、print fact 合同）已落地
> - 与 `AP-NH4` / `AP-NH5` **尾部并行**；**不是** 10+3 live（那是 `AP-NH7`）
> 下游交接:
> - `AP-NH7` 10+3 vertical activation（join NH2+NH3+NH5+NH6；local_object 格另需 NH4）。Capstone **E** 的「到 query」属 NH7
> - `AP-NH9` runtime security / SBOM / crash 总验（`tests/e2e/test_new_harvest_runtime_security.py` 本 AP 先建节点；NH9-T10 🔱）
> 关联设计 / 调研文档:
> - `docs/eval/new-harvest/final-execution-plan.md` v1.0 §4.1 `S-NH-F6` / §4.2 `O-NH-06` / §6 DAG / §7.6 / §9 / §10 `R-F05/F06` / §11.A
> - `docs/eval/new-harvest/pre-charter-qna.md` v1.0 Q13/Q19/Q23 → `T-O-393/399/403`
> - `docs/eval/new-harvest/pre-initial-planning-qna.md` v0.5 `T-O-376/378`
> - `docs/baseline/domain-truth/S16-security-trust-boundary.md`（egress/SSRF；browser 每跳复核）
> - `docs/baseline/domain-truth/S11-inference-runtime.md`（无万能 blob invoke；本 AP 扩 multimodal request）
> 冻结决策来源:
> - `docs/eval/new-harvest/pre-charter-qna.md` v1.0（Q13/Q19/Q23 业主回答 🔒 FROZEN；只读引用；本 action-plan 不填写 Q/A）
> - `docs/eval/new-harvest/pre-initial-planning-qna.md`（`T-O-376/378`）
> grounding 来源:
> - HEAD `1221aa1` 实测 `path:line`（本 AP §7.1 备注独立核对行号）
> - `docs/eval/new-harvest/reference-anchor/assessment-analysis-05-runtime-adapters-readiness-and-security.md`（RA05 全文）
> - `docs/eval/new-harvest/reference-anchor/assessment-analysis-03-representation-and-reacquisition.md`（只消费 print/PDF **观察诚实**；生产供给在本 AP）
> 关联 reference-anchor:
> - 上列 RA05（主面）/ RA03（表示诚实，不选库）——正/反例参考系，**不是**新 Truth
> 文档状态: `executed`
> 台账 ID 区间（final §11.A `7.6 AP-NH6`）：`NH6-01..10 / NH6-A01..06 / NH6-T01..10`
> HEAD: `1221aa1`
> 代码分母: `1221aa1`（其后提交只改 `docs/`；`src/`/`api/`/`intake/`/`tests/` 行号以本文件独立 `read_file` 为准）

---

## 0. 执行背景与目标

HEAD `1221aa1` 已有可注入端口、三调度池、`ConcurrencyGate`、S16 `EgressPolicy`、`SupplyFence`、CLI 子进程与诚实拒 binary，但默认组合根 **未注入** `browser_fetcher`/`clean_llm`（`api/app.py:330-345`），生产依赖 **无** PDF/browser/OCR 包（`pyproject.toml:13-21`），`GenerateRequest` 仅 `input_text`（`src/contracts/inference/models.py:96-108`），`/ready` 九项不含 binary/pdf/ocr 且 inference probe 只是 `GET /v1/models` 名单（`src/runtime/health.py:16-25`；`src/llm_adapters/local_vllm.py:276-295`）。PDF 文本仍是同进程正则抠未压缩字面量，无层盗用 OCR 码（`src/runtime/intake/types.py:144-171`，`T-R-NH-06/26`）。NH1 `NH1-06`/`NH1-T06` 只证明形态 **smoke 可行**；NH3 `NH3-04/05` 只冻结观察/能力分码与 print fact 合同。本 AP 把冻结的 local capability ports vs S11 multimodal、无网 parser/hardened browser、render/print 分账，落成默认根真实供给、隔离、readiness 与 SBOM。

- **服务业务簇**：`MKB / new-harvest` · `S-NH-F6`
- **计划对象**：local parser / browser.render / browser.print_pdf / OCR / Vision / DU 真实供给 + isolation + readiness + SBOM
- **本次计划解决的问题**：
  - 默认根供给 = 0：`create_app()` 无 `browser_fetcher`/`clean_llm`，browser/print/OCR/Vision 物理 503（`T-R-NH-26`；`NH-RA05-B01`）
  - 请求协议不能运 bytes：S11 仅 `input_text`；CLI 拒 binary；vLLM string `content`（`NH6-A01`/`A02`/`A05`）
  - 隔离与诚实 readiness 缺失：同进程 PDF、无 sandbox、`/ready` 名单绿、e2e monkeypatch fetcher（`T-O-378/399`；`FG-NH-01/11`）
- **本次计划的直接产出**：
  - 供给身份注册表：parse / render / print / 确定性 OCR / model-bound OCR·Vision·DU 的 cap、version、limit、readiness key（库名 **不** 进 Truth）
  - 无网 isolated PDF parser：ToUnicode/压缩提取；typed absent/encrypted；kill；恶意样本不杀 API
  - 共享 hardened browser binary + 分 capability：render 验真实 DOM；print 验 `%PDF-`；non-root；生产禁 `--no-sandbox`；每跳 S16 egress
  - S11 multimodal request（PromptRef + model + digest/handle/受控 bytes）与确定性 OCR 分账
  - `ConcurrencyGate` 具名 cap、正负 readiness、pin/SBOM/CVE/waiver、`create_app()` 无 patch 可达
- **本计划不重新讨论的设计结论**：
  - 以 PromptRef+model identity+inference budget 划界：无 prompt 的 parser/browser/确定性 OCR = local ports；model-bound OCR/Vision/DU = S11 multimodal；CLI binary fail-closed；pool 数不锁（来源：Q13 / `T-O-393`）
  - parser/确定性 OCR = 无网 isolated subprocess；browser/print = hardened non-root，生产禁 `--no-sandbox`，走 S16 egress；pin/SBOM/CVE/负样本/readiness 为生产门；豁免仅 owner 具名（来源：Q19 / `T-O-399`）
  - 共享 hardened browser binary/navigation/egress，但 render/print 是两个 capability/profile/budget/readiness/evidence；分别验 DOM 与 `%PDF-`；淘汰常量 `injected-browser-renderer.v1`（来源：Q23 / `T-O-403`）
  - 假 PDF / OCR 盗码不得冒充完成（来源：`T-O-378`）；观察码改写在 NH3，本 AP 负责供给与隔离
  - 四通道 completeness 禁止把 503 当通道 DoD（来源：`T-O-376`）；本 AP 的 typed 503/readiness false 是 **缺供给诚实**，不是 NH7 live
  - L1/L2/L3/L4 不可互换；本 AP 无 L4 query 义务（来源：Q26 / `T-O-406`）
  - 零 CF/SMCP/R2、禁第五 kind / `workflow_key` / `action_branch`（来源：`T-O-377`；`O-NH-06`）

---

## 1. 执行综述

### 1.1 总体执行方式

**先钉供给身份与 readiness 键，再落 PDF 隔离提取，再落 browser 双能力，再扩 S11 multimodal 与 OCR 分类，最后把闸、健康、SBOM 与默认根接线收成可部署门。** 禁止先把 NH7 live query 写进本 AP；禁止用 NH1 smoke 顶 DoD；禁止锁死 Playwright/Chromium/poppler/tesseract **库名**为新 Truth（`T-O-393` 不锁库）。具体 pin 只进 SBOM/evidence。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | 供给身份 | `M` | parse/render/print/OCR/model caps、versions、limits、readiness keys | NH1 GO + NH3 观察/print 合同 |
| Phase 2 | PDF parser | `L` | 无网 subprocess；ToUnicode/compressed；kill；typed absent/encrypted | Phase 1 |
| Phase 3 | browser 双能力 | `XL` | 共享 binary；render DOM；print `%PDF-`；分 cap/profile/budget | Phase 1 |
| Phase 4 | S11 multimodal + OCR/Vision | `XL` | bytes/handle+PromptRef；确定性 vs model 分类；禁 cloud/latest | Phase 1 |
| Phase 5 | 闸 / 健康 / 供应链 / 接线 | `L` | backpressure 满载零调用；正负 probe；SBOM；`create_app()` 无 patch | Phase 2–4 |

> `规模` 是描述性提示，不是开工闸。Phase 2/3/4 在身份冻结后可并行实现，但 Phase 5 接线必须消费三者的 cap key。

### 1.3 Phase 说明

1. **Phase 1 — 供给身份**
   - **核心目标**：每个能力有独立 identity / limit / readiness key；共享治理实现 ≠ 合并契约身份（`NH-C-49`）。
   - **为什么先做**：后续 parser/browser/S11 若无名可探，readiness 会再次塌成 `inference_binding` 一团绿。
2. **Phase 2 — PDF parser**
   - **核心目标**：把 `types.py:144-171` 同进程正则从 **提取权威** 撤掉，换成无网 isolated subprocess 的真 ToUnicode/压缩提取；观察码沿用 NH3 分账。
   - **为什么放在这里**：身份键先于二进制；NH3 已禁止盗码，本 AP 才能换真引擎而不改观察法。
3. **Phase 3 — browser 双能力**
   - **核心目标**：同一 hardened binary + 导航/egress，注册 `browser.render` 与 `browser.print_pdf` 两个 cap；分别验 DOM / `%PDF-`。
   - **为什么放在这里**：与 parser 威胁模型不同（`NH-C-45`），不得共用一份「sandbox 故事」。
4. **Phase 4 — S11 multimodal + OCR/Vision**
   - **核心目标**：凡需 PromptRef+model budget 的走扩展后的 S11 request；确定性 OCR 走 local port；CLI 继续拒 binary。
   - **为什么放在这里**：协议扩与 local port 分账，避免把 PDF 解析伪装成 `GenerateRequest`。
5. **Phase 5 — 闸 / 健康 / 供应链 / 接线**
   - **核心目标**：具名 cap 满载零下游调用；`/ready` 组件 == 实际在场；每 binary/model 有 pin/license/SBOM/CVE/waiver；默认根无 monkeypatch 可达。
   - **为什么放在这里**：供给未真实存在时接线只会把 503 涂绿或把测试后赋 port 写成 live（`FG-NH-01/02/11`）。

### 1.4 执行策略说明

- **执行顺序原则**：身份注册 → parser 隔离提取与 browser 双能力与 S11 协议（三者可并行）→ 闸/ready/SBOM → `create_app()` 注入。禁止「先 e2e monkeypatch 再补生产注入」。禁止 NH7 live 路径充当本 AP 证明。
- **风险控制原则**：`R-F05` 供应链失败 → 具名 waiver 只延期、替代须 reopen，不准锁库名顶替。`R-F06` browser 降级 → S16 hard gate + T05。parser 无网 / browser 受控 egress **分账**，不得一份策略文件假装相同。
- **测试推进原则**：Phase 1 短途 L1 身份/键扫描；Phase 2 L2/L3 提取+隔离；Phase 3 L3 default-root DOM/PDF；Phase 4 L1/L2/L3 协议与 typed 错；Phase 5 L1 闸 + L2/L3 readiness + L1 SBOM。fault/race/security 是标签（T02/T05=S，T08=R，T07=fault，T09=soak），不是替代层。本 AP **无 L4**。
- **文档同步原则**：本 AP 保持 `draft`。执行后只允许回填 §11 与 `docs/evidence/new-harvest/AP-NH6/`；不得改 QNA / final / RA。库名与 CVE pin 只进 evidence/SBOM。
- **回滚 / 降级原则**：新 port 缺省 → typed 503 + 对应 readiness `ok:false`，禁止 silent 成功。撤回注入即回到 HEAD `1221aa1` 行为（browser 503、CLI 拒 binary）。**禁止**生产 `--no-sandbox`、cloud OCR、浮动 `latest` 作为降级。

### 1.5 本次 action-plan 影响结构图

```text
AP-NH6 local runtime supply / readiness / security
├── Phase 1: 供给身份
│   ├── capability registry（parse / render / print / ocr.det / s11.multimodal）
│   ├── src/runtime/config.py（config/readiness keys；无新业务表）
│   └── HealthAggregator 组件名预留（落地在 Phase 5）
├── Phase 2: PDF parser
│   ├── 无网 isolated subprocess + caps/kill
│   ├── 替换 types.py:144-171 提取权威（观察码消费 NH3-04）
│   └── fixtures compressed / CID / absent / encrypted
├── Phase 3: browser 双能力
│   ├── 共享 hardened binary + 导航 + S16 每跳 egress
│   ├── browser.render → 真实 DOM + 非常量 profile
│   └── browser.print_pdf → %PDF- + 独立 budget/readiness
├── Phase 4: S11 multimodal + OCR/Vision
│   ├── GenerateRequest / 新 sibling：bytes|handle + PromptRef（禁 payload_extra 偷运）
│   ├── local_vllm.py 运输 parts/image 而非 string content
│   └── 确定性 OCR local port vs model-bound S11；CLI 保持拒 binary
└── Phase 5: 闸 / 健康 / SBOM / 默认根
    ├── ConcurrencyGate 具名 cap（扩 multimodal/browser/parser 键；不默许第四无名 DispatchPool）
    ├── /ready 正负 probe == 实际在场
    ├── pin / license / SBOM / CVE / owner waiver
    └── api/app.py:330-345 create_app() 注入真实 port（T03/T04/T06/T09）
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** 供给身份：parse / render / print / 确定性 OCR / model-bound OCR·Vision·DU 的 cap、version、limit、readiness key（`NH6-01`）
- **[S2]** PDF 无网 isolated subprocess：ToUnicode/压缩真提取；typed absent/encrypted；资源 kill；恶意样本不杀 API（`NH6-02`）
- **[S3]** browser 共享 binary、分 capability：render 真实 DOM；print 真 `%PDF-`；non-root；禁生产 `--no-sandbox`；每跳 S16 egress（`NH6-03/04`）
- **[S4]** S11 multimodal request：PromptRef+model+media+digest/handle/受控 bytes；确定性 vs model 分类；empty/bad/timeout typed；禁 cloud/latest（`NH6-05/06`）
- **[S5]** 具名闸满载零下游调用；`/ready` 组件与在场一致；SBOM/CVE/waiver；`create_app()` 无测试 monkeypatch 可达；缺供给 typed 503/readiness false（`NH6-07..10`）
- **[S6]** Capstone **E** 的 **供给侧**（real binary/model、PromptRef、isolation/readiness）；固定安全面 `tests/e2e/test_new_harvest_runtime_security.py`

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** 10+3 live-to-retrieval / namespace query（`S-NH-F7`）→ `AP-NH7`。Capstone E「到 query」不在本 AP 假装覆盖
- **[O2]** 七意图 / exact-clean / no-op cleaner（`S-NH-F8`）→ `AP-NH8`
- **[O3]** campaign mega / crash 全窗 `W-NH-*` / closed-set（`S-NH-F9`）→ `AP-NH9`（本 AP 只建 security 文件中的 NH6 节点）
- **[O4]** 锁库名为 Truth；CF Browser Rendering / 云 OCR / R2 / SMCP（`O-NH-06`；`T-O-377`）
- **[O5]** 表示观察法/盗码改写（已交 `NH3-04`）；print fact 合同（已交 `NH3-05`）；本 AP 只供真实 bytes/profile
- **[O6]** existing-object upgrade、第五 kind、`workflow_key`、`action_branch`、raw GET、实验发车进 DoD

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| local parser / browser.render / browser.print_pdf / 确定性 OCR 供给 | `in-scope` | `S-NH-F6`；`T-O-393/399/403` | NH1 STOP 则本 AP 不得开工 |
| S11 multimodal request + model-bound OCR/Vision/DU | `in-scope` | Q13；运输层证伪 `T-P-NH-6` | 替代协议须 reopen Q13 |
| pin/SBOM/CVE/readiness/负样本 | `in-scope` | Q19 生产门 | owner 具名 waiver 只延期 |
| 库名（Playwright/pypdf/tesseract/poppler/…）写入 Truth | `out-of-scope` | `T-O-393` 不锁库；pin 进 SBOM | 新 owner-gate |
| 10+3 live query | `out-of-scope` | NH7；本 AP 无 L4 | 不得用 T03/T04 顶 NH7-T05/T06 |
| 观察码 vs 能力码分账 | `out-of-scope`（消费） | NH3-04 已裁；本 AP 不重开 | decode 再抛 OCR-unavail = NH3 回归 |
| CF Browser Rendering / 云 OCR | `out-of-scope` | `O-NH-06`；`T-O-377` | 禁止「临时方便」回流 |
| 第四无名 `DispatchPool` | `out-of-scope` | pool 数不锁，但禁止无名第四池；只扩具名 ConcurrencyGate key | 若要新池名须显式登记，不得 silently |
| 生产 `--no-sandbox` 默认 | `out-of-scope` | Q19 / `T-O-399` 隔离红线 | 新 owner-gate / reopen Q19；**不得**经 pin/SBOM/CVE/readiness 具名 waiver 改期待值 |
| campaign crash 全窗 | `out-of-scope` | NH9 | T02 只证 parser 杀不掉 API，不是 W-NH-* mega |

---

## 3. 业务工作总表

编号列使用冻结 `NH6-nn`（final §7.6 台账 A）。每个工作项含 file:line、收口目标、Test-ID。

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| `NH6-01` | Phase 1 | Supply identities | `add` | 新建 capability registry（建议 `src/runtime/supply/identities.py`）；`src/runtime/config.py:12-67` 增 keys；`src/runtime/health.py:16-25` 预留组件名 | parse/render/print/OCR/model 各有 cap、version、limit、readiness key；库名不进 Truth | `NH6-T09`（键在场）/ `NH6-T10`（pin 清单引用同一 identity） | `high` |
| `NH6-02` | Phase 2 | PDF text supply | `add` | `src/runtime/intake/types.py:100-171`（撤提取权威）；新建 isolated parser port；`claude_cli.py:320-337,423-440`（借 subprocess kill 形状，不借 text-only 运输） | 真 ToUnicode/压缩提取；absent/encrypted 分码；无网；kill；恶意样本不杀 API | `NH6-T01` / `NH6-T02` | `high` |
| `NH6-03` | Phase 3 | Render supply | `add` | `src/runtime/intake/core.py:45-70`（保端口分离）；`api/app.py:280-288,330-345`；`src/runtime/http_acquisition.py:182-208,221-255`（每跳 egress 供 browser 复用）；`acquisition_ingest.py:477-485,535-536` | SPA 真实 DOM；profile 非常量；non-root；S16 egress；timeout/cap | `NH6-T03` / `NH6-T05` | `high` |
| `NH6-04` | Phase 3 | Print supply | `add` | `src/runtime/intake/core.py:45-70`；`api/app.py:280-288,330-345`；`src/runtime/http_acquisition.py:182-208,221-255`；`src/runtime/intake/acquisition_ingest.py:477-485,535-536`（与 `NH6-03` 共享 binary/egress）；`src/runtime/config.py:12-67` 增 `browser.print_pdf` cap/budget/readiness keys；`src/runtime/health.py:16-25` 增 print readiness key；消费 `NH3-05` fact 合同 | 真 `%PDF-`；独立 budget；render 成功不得顶替 print | `NH6-T04` / `NH6-T05` | `high` |
| `NH6-05` | Phase 4 | Multimodal request | `update` | `src/contracts/inference/models.py:18,63-70,96-108`；`src/llm_adapters/local_vllm.py:207-216,276-295`；`src/runtime/inference/claude_cli.py:505-508`（保持拒 binary） | bytes/handle+PromptRef 可运；非 `input_text` only；禁 payload_extra 偷运 | `NH6-T06` | `high` |
| `NH6-06` | Phase 4 | OCR/Vision bindings | `add` | `intake/pdf/__init__.py:37-56`（能力 503 留 clean）；`intake/types.py:59-69` `CleanLanguageModel`；分类器落 Phase 1 registry | 无 prompt → local OCR port；有 PromptRef+model → S11；empty/bad/timeout typed；禁 cloud/latest | `NH6-T06` / `NH6-T07` | `high` |
| `NH6-07` | Phase 5 | Gates/backpressure | `update` | `api/app.py:244-266`；`src/runtime/inference/facade.py:102-132`；`src/runtime/workflow/dispatch.py:42-43,122-146`；♻️ `tests/unit/test_dispatch_embed_and_gates.py:259-294` | 具名 cap 满载 → BACKPRESSURE 且零下游调用；不默许第四无名池 | `NH6-T08` | `medium` |
| `NH6-08` | Phase 5 | Real readiness | `update` | `src/runtime/health.py:16-25,93-108`；`api/app.py:168-199,522-525`；替换 `local_vllm.py:276-295` 作为 **唯一** ready 证明 | 正负 fixture 与组件状态一致；缺项不是整体绿；models-list 不足 | `NH6-T09` | `high` |
| `NH6-09` | Phase 5 | Pin/SBOM/CVE | `add` | 新建 inventory（建议 `docs/evidence/new-harvest/AP-NH6/security/` + 机器可读 manifest）；`pyproject.toml:11,13-21` 对照 Proprietary | 每 binary/model 有 pin/license/SBOM/CVE/waiver；豁免仅 owner 具名 | `NH6-T10` / `NH6-T02` / `NH6-T05` | `high` |
| `NH6-10` | Phase 5 | Default root | `update` | `api/app.py:330-345`；`src/runtime/intake/core.py:45-75`；禁止测试赋值 `_browser_fetcher`（`tests/e2e/test_source_capability_paths.py:99-101` 反例） | `create_app()` 无需 monkeypatch 可达供给；缺供给 typed 503/readiness false，不得 silent | `NH6-T03` / `NH6-T04` / `NH6-T06` / `NH6-T09` | `high` |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — 供给身份

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH6-01` | Supply identities | **净新 / 高风险**：a) 登记五类 identity：`pdf.parse`、`browser.render`、`browser.print_pdf`、`ocr.deterministic`（无 PromptRef）、`s11.multimodal`（OCR/Vision/DU，需 PromptRef+model+budget）。b) 每条含 `capability_key`、`binary_or_model_identity` 槽、`version` 槽、`limits`（time/cpu/mem/bytes/concurrency）、`readiness_key`。c) 共享 `ConcurrencyGate`/`HealthAggregator`/`SupplyFence` **实现**，但 identity/limit/readiness **分账**（`T-O-393`）。d) **不**把 Playwright/Chromium/pypdf/tesseract/poppler/MuPDF 写入本表作 Truth；具体 pin 进 SBOM（`NH6-09`）。e) pool **个数不锁**；`DispatchPool` 今日闭集仍为 `local-inference`/`non-interactive`/`embed`（`dispatch.py:42-43`）；OCR/Vision/browser 今日 `unpooled`（`:122-146`）——本 AP 只允许扩 **具名** gate key，禁止第四无名池。f) CLI 继续 binary fail-closed，不当 OCR fallback。 | 新建 registry；`src/runtime/config.py:12-67`；`src/runtime/health.py:16-25`；`src/runtime/workflow/dispatch.py:42-43,122-146` | 每能力可被 probe/闸/SBOM 引用同一 key | `NH6-T09` / `NH6-T10` | registry 可枚举；无库名 Truth；无第四无名池 |

### 4.2 Phase 2 — PDF parser

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH6-02` | PDF text supply | **净新 / 高风险**：a) 实现 isolated **无网** subprocess（禁 DNS/HTTP/环境代理；受控 tmp；CPU/memory/time/output cap）。b) 提取须覆盖 ToUnicode / 压缩流（ISO 32000 §9.10 失败法：无映射 ≠ 扫描件 OCR）；**禁止** `types.py:144-171` 正则 Tj 当权威。c) 超时/超限 → terminate→kill（形状可借 `claude_cli.py:320-337,423-440`）。d) typed：`absent`（无可用 Unicode 层）/ `encrypted`（`/Encrypt` 且不可用层）/ corrupt 与 NH3-04 观察码对齐；**禁止**再抛 `CLEAN_OCR_CAPABILITY_UNAVAILABLE` 冒充无层。e) 恶意/超大/加密负样本不得打崩 API 进程；`/ready` 仍 200 **或** 至少进程存活。f) 不锁库名；若用 GPL/AGPL 引擎 **禁止链入** Proprietary 主进程（`pyproject.toml:11`），倾向 subprocess CLI。g) 夹具：compressed、CID、absent、encrypted。 | `src/runtime/intake/types.py:100-171`；新建 parser port/adapter；`claude_cli.py:320-337,423-440`（形状） | 真提取 + typed 分码 + 隔离 | `NH6-T01` / `NH6-T02` | T01/T02 PASS；盗码零；API 存活 |

### 4.3 Phase 3 — browser 双能力

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH6-03` | Render supply | **净新 / 高风险**：a) 以 non-root + sandbox 跑 hardened local browser（生产 argv **不得**含 `--no-sandbox`）。b) 导航与出站每跳走 S16 `EgressPolicy.check_url` / `validate_redirect`（`http_acquisition.py:221-255`；`security.py:368-414` `check_url` + `:433-439` `validate_redirect`）；**禁止** browser 自带 fetch 绕过（`NH-RA05-B12`）。c) render 输出真实 SPA DOM（非 screenshot 改名、非 lambda HTML）；`browser_profile` 为真实 binary/profile 身份，淘汰 `injected-browser-renderer.v1`（`acquisition_ingest.py:536`）。d) 独立 timeout/size/concurrency cap（与 print 分账）。e) 缺注入保持 `ACQUISITION_BROWSER_CAPABILITY_UNAVAILABLE` 503（`:477-485`），不得 fallback `http_fetcher`（`core.py:66-70`）。f) L3 经 `create_app()`，禁止测试后 `pipeline._browser_fetcher =`（`FG-NH-01`）。 | `core.py:45-70`；`api/app.py:280-345`；`http_acquisition.py:182-255`；`acquisition_ingest.py:477-536`；新建 browser runtime | SPA DOM + 非常量 profile + egress | `NH6-T03` / `NH6-T05` | T03 L3 PASS；T05 政策 PASS |
| `NH6-04` | Print supply | **净新 / 高风险**：a) **共享**同一 hardened binary/navigation/egress（`T-O-403`）。b) 注册独立 `browser.print_pdf` cap/profile/budget/readiness/evidence。c) 产出 bytes 必须以 `%PDF-` 起；独立 page/print 参数进 evidence。d) render 成功 **不得**顶替 print（DOM 绿 ≠ print 绿）。e) 消费 NH3-05：acquire 写 `representation_kind=print_pdf`；clean **禁止**猜测（`clean_preflight.py:46-62` 死键由 NH3 改，本 AP 供真 bytes）。f) CDP `Page.printToPDF` 失败法只借不锁库：零页才 error、pageRanges quietly cap——evidence 必须可审计。g) 部署以后可拆实例，不改 strategy/graph taxonomy。 | `core.py:45-70`；`api/app.py:280-345`；`http_acquisition.py:182-255`；`acquisition_ingest.py:477-536`（与 NH6-03 同 binary 落点）；`config.py:12-67` print cap/budget；`health.py:16-25` print readiness | 真 PDF + 独立 budget | `NH6-T04` / `NH6-T05` | `%PDF-`；render≠print；T05 PASS |

### 4.4 Phase 4 — S11 multimodal + OCR/Vision

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH6-05` | Multimodal request | **净新 / 高风险**：a) 扩 S11 合同：在既有 `GenerateRequest` 旁增加显式 multimodal 字段或 sibling 模型（`prompt_ref`/`prompt_digest`/`binding` + `media_type` + **digest+handle 或受控 bytes**）；`StrictModel` `extra=forbid` 保持。b) **禁止** `payload_extra` 偷运 `content`/`prompt`/`vector`（`models.py:63-70` 已禁，不得开例外）。c) adapter：`local_vllm.py:207-216` 不得再把 user 消息做成纯 string `content`；须能运 parts / 受控 media。d) `probe` 不得只用 `GET /v1/models` 当 multimodal ready（`:276-295`）。e) `claude_cli.py:505-508` **保持** `CLEAN_MEDIA_UNSUPPORTED`；不当 OCR/Vision fallback。f) bytes 走 S13 handle 或 bounded digest+bytes；path 不得进推理请求。g) `InferenceCapability` 今日无 vision/ocr（`models.py:18`）——若增能力字面必须进 registry/fence，不得 silently。 | `models.py:18,63-108`；`local_vllm.py:207-216,276-295`；`claude_cli.py:505-508`；`intake/types.py:59-69` | 协议能运 media；CLI 仍拒 binary | `NH6-T06` | T06 PASS；text-only 不能冒充 vision |
| `NH6-06` | Capability bindings | **净新 / 高风险**：a) 分类：无 PromptRef 的确定性 OCR → `ocr.deterministic` local port（无网 subprocess，同 parser 隔离线）。b) 需要 PromptRef+model identity+inference budget 的 OCR/Vision/DU → `s11.multimodal`。c) engine/model **pin**（禁止浮动 `latest`）。d) empty / bad bytes / timeout → typed 失败，空输出不得 admitted clean（Tesseract `Empty page!!` 失败法只借不锁库）。e) **禁云 OCR**。f) clean 侧缺注入仍用 503 能力码（`intake/pdf/__init__.py:48-50`）；decode 观察码不得回流该码。 | registry + OCR port；`intake/pdf/__init__.py:37-56`；`clean_preflight.py:75-107`（OCR/Vision 禁 CLI 兜底，保持） | 分类稳定；负例 typed | `NH6-T06` / `NH6-T07` | 分类扫描 + T07 PASS |

### 4.5 Phase 5 — 闸 / 健康 / 供应链 / 接线

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH6-07` | Gates/backpressure | **扩展既有**：a) 为 parser/render/print/multimodal 登记 **具名** `ConcurrencyGate` key（扩 `api/app.py:244-266` 的 `capability_limits`，今日为 embed/structured_generate/text_generate/cli）。b) 满载 `try_acquire` 返回 None → `INFERENCE_BACKPRESSURE`（或能力专用 BACKPRESSURE 码）且 **零**下游 binary/model 调用（`facade.py:102-132` 已保证 gate 满则零 model call）。c) 指标分 cap。d) 不把 OCR 偷塞进 generate 池假装「已复用」；不新增第四无名 `DispatchPool`。 | `api/app.py:244-266`；`facade.py:102-132`；`dispatch.py:42-43`；♻️ gate tests | 满载零调用 | `NH6-T08` | T08 PASS |
| `NH6-08` | Real readiness | **重 substrate**：a) `HealthAggregator.REQUIRED` 或并列组件加入 pdf/browser.render/browser.print/ocr/multimodal（今日九项无 binary，`health.py:16-25`）。b) 正样本 probe：真实 fixture 抽出文本 / DOM / `%PDF-` / 模型一次受控调用。c) 负样本：缺 binary、加密 PDF、空 OCR、SPA 超时。d) 组件 `ok` == 实际在场；缺项 ⇒ 该组件 false，**不得**整体绿。e) `inference_binding` 继续可探名单，但 **不足** 以证明 vision/parser/browser（`FG-NH-11`）。f) `/ready` 聚合逻辑保持「REQUIRED 全 ok 才 200」（`health.py:107-108`；`app.py:522-525`）；未声明启用的能力不得用「没测」当绿。 | `health.py:16-25,93-108`；`app.py:168-199,522-525`；`local_vllm.py:276-295` | 正负一致 | `NH6-T09` | T09 PASS；名单不足 |
| `NH6-09` | Pin/SBOM/CVE | **净新**：a) 机器可读 inventory：每个 binary/model 的 identity、version pin、license、SBOM 条目、CVE baseline、upgrade/rollback 指针。b) 仓标 Proprietary：GPL/AGPL **链入**主进程 = 失败；subprocess 是否可接受由 license 字段+owner 审查记录，不在 AP 锁库。c) waiver 仅 owner 具名（姓名/Truth 影响/到期/reopen）；不得覆盖 `T-O-376/378/381/383` **以及** `T-O-399` 隔离句（生产禁 `--no-sandbox`、parser 无网）。waiver **只延期** pin/SBOM/CVE/readiness 生产门，不得把 argv `--no-sandbox` 改口为合法。d) 无 pin 不得进生产依赖。 | evidence `security/` + domain 测试读取的 manifest；`pyproject.toml:11,13-21` | 清单完整或具名 waiver | `NH6-T10` | EXIT0；无匿名豁免 |
| `NH6-10` | Default root | **扩展既有**：a) `create_container`/`create_app()` 从 config 注入真实 `browser_fetcher`、parser port、`clean_llm`/OCR port（改 `api/app.py:330-345`）。b) **禁止**测试 monkeypatch 作为 success 路径（扫描赋值 `_http_fetcher/_browser_fetcher/_clean_llm`）。c) 启动/readiness 与注入一致。d) 缺供给 → typed 503 + 组件 false，**不得 silent**。e) T03/T04/T06/T09 证明无 patch 可达。 | `api/app.py:330-345`；`core.py:45-75` | 默认根可达或诚实未就绪 | `NH6-T03/T04/T06/T09` | 四测试无 patch PASS |

---

## 5. Phase 详情

### 5.1 Phase 1 — 供给身份

- **Phase 目标**：冻结五类 capability 的 identity/limit/readiness 键，作为后四 Phase 的唯一引用。
- **本 Phase 对应编号**：`NH6-01`
- **本 Phase 新增文件**：`src/runtime/supply/identities.py`（或等价 registry 模块）；config 键文档进 evidence，不进 Truth
- **本 Phase 修改文件**：`src/runtime/config.py:12-67`（增 keys）；`src/runtime/health.py:16-25`（组件名预留，probe 实现可在 Phase 5 接完）
- **本 Phase 删除文件**：无
- **具体功能预期**：
  1. 可枚举 `pdf.parse` / `browser.render` / `browser.print_pdf` / `ocr.deterministic` / `s11.multimodal`
  2. 每条有 version 槽与独立 limit（print 与 render 不得共用同一并发帽作为唯一帽）
  3. readiness key 与 cap 1:1
  4. registry 源码与文档 **零**「将采用 pypdf/playwright/tesseract」Truth 句
  5. 失败：未登记 cap 不得被闸/ready 默默归入 `inference_binding`
- **对应测试台账项**：`NH6-T09` / `NH6-T10`（详见 §8）
- **收口标准**：身份表可被 T09 组件名与 T10 inventory key 对上
- **本 Phase 风险提醒**：把「不锁 pool 数」读成「不改 GenerateRequest」是 `NH-C-49` 反例

### 5.2 Phase 2 — PDF parser

- **Phase 目标**：真实、隔离、可杀的 PDF 文本供给；观察码消费 NH3，不重开盗码讨论。
- **本 Phase 对应编号**：`NH6-02`
- **本 Phase 新增文件**：parser adapter/subprocess runner；`tests/e2e/test_nh6_pdf_parser.py`；`tests/e2e/test_nh6_parser_isolation.py`；`tests/fixtures/new_harvest/pdf/*`
- **本 Phase 修改文件**：`src/runtime/intake/types.py:100-171`（正则不得再当 `text_layer=present` 权威）
- **具体功能预期**：
  1. compressed/ToUnicode 样本抽出非空 Unicode
  2. CID 字体样本非空或 typed 失败（不得空字符串当 present）
  3. 无层 → `absent`，不抛 OCR-unavail
  4. 加密 → `encrypted`
  5. subprocess 无网（拒 DNS/HTTP）；超时 kill
  6. 资源炸弹不杀 API；`/ready` 200 或进程存活
- **对应测试台账项**：`NH6-T01` / `NH6-T02`
- **收口标准**：台账 D「PDF supply」谓词
- **本 Phase 风险提醒**：CVE PoC/exploit payload **禁止**入库（本 AP 只用资源炸弹/加密/畸形结构夹具）

### 5.3 Phase 3 — browser 双能力

- **Phase 目标**：共享 binary、分 cap；DOM 与 PDF 各自真实；安全政策可测。
- **本 Phase 对应编号**：`NH6-03` / `NH6-04`
- **本 Phase 新增文件**：browser runtime（render+print）；`tests/e2e/test_nh6_browser_render.py`；`tests/e2e/test_nh6_browser_print.py`；`tests/e2e/test_new_harvest_runtime_security.py`（本 AP 节点）；SPA fixture
- **本 Phase 修改文件**：`api/app.py:280-345`；`acquisition_ingest.py:535-536`（常量 profile 淘汰，与 NH3-05 衔接）
- **具体功能预期**：
  1. SPA fixture → 含应用主文的 rendered DOM，非静态壳
  2. print → `%PDF-` 且独立 budget 计数
  3. 同一请求上 render PASS 不能使 print 断言跳过
  4. 进程 non-root；生产启动 argv 无 `--no-sandbox`
  5. 每 redirect 再跑 egress；metadata/私网/字面 IP 默认拒
  6. 缺 port → 503 能力码，零 rendered 假成功
- **对应测试台账项**：`NH6-T03` / `NH6-T04` / `NH6-T05`
- **收口标准**：台账 D「browser supply」
- **本 Phase 风险提醒**：`R-F06`；官方 Playwright Docker root=`--no-sandbox` 是反例，不得当默认

### 5.4 Phase 4 — S11 multimodal + OCR/Vision

- **Phase 目标**：协议能运 media；分类稳定；负例 typed；CLI 诚实。
- **本 Phase 对应编号**：`NH6-05` / `NH6-06`
- **本 Phase 新增文件**：`tests/integration/test_nh6_multimodal_request.py`；`tests/e2e/test_nh6_multimodal_adapter.py`；`tests/unit/test_nh6_ocr_vision_errors.py`；`tests/integration/test_nh6_ocr_vision_port.py`
- **本 Phase 修改文件**：`src/contracts/inference/models.py:18,63-108`；`src/llm_adapters/local_vllm.py:207-216,276-295`
- **具体功能预期**：
  1. 请求含 PromptRef + media_type + digest/handle 或 bounded bytes
  2. 仅 `input_text` 的 Vision/DU 调用失败
  3. CLI complete(blob=PDF) 仍 422 `CLEAN_MEDIA_UNSUPPORTED`
  4. empty/bad/timeout 不成功；无 cloud endpoint；无 `latest` pin
  5. 确定性 OCR 不走 S11 generate
- **对应测试台账项**：`NH6-T06` / `NH6-T07`
- **收口标准**：台账 D「model supply」
- **本 Phase 风险提醒**：把 `CleanLanguageModel.complete(..., blob=)` 端口形状当成 live adapter

### 5.5 Phase 5 — 闸 / 健康 / 供应链 / 接线

- **Phase 目标**：默认根可部署且诚实；供应链可审计。
- **本 Phase 对应编号**：`NH6-07` / `NH6-08` / `NH6-09` / `NH6-10`
- **本 Phase 新增文件**：`tests/unit/test_nh6_backpressure_zero_calls.py`；`tests/e2e/test_nh6_readiness.py`；`tests/domain/test_nh6_sbom_inventory.py`；evidence security 清单与 S16 签收栏
- **本 Phase 修改文件**：`api/app.py:244-266,330-345`；`src/runtime/health.py:16-25`；gate tests fork
- **具体功能预期**：
  1. 满载零 parser/browser/adapter 调用
  2. 正 probe 与负 probe 和 `/ready` 组件一致
  3. models-list 200 不能单独把 multimodal/parser/browser 置绿
  4. inventory 每条有 pin/license/SBOM/CVE 或具名 waiver
  5. `create_app()` 无 patch 跑通 T03/T04/T06/T09
  6. 缺供给 silent success = 本 Phase FAIL
- **对应测试台账项**：`NH6-T08` / `NH6-T09` / `NH6-T10`（接线由 T03/T04/T06/T09 证）
- **收口标准**：台账 D「budget/readiness / supply trust / default wiring」+ `FG-NH-11` + S16 签收栏存在
- **本 Phase 风险提醒**：把 S16 签收栏填上假日期/假签名 = 伪造已签，禁止

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Q13 / `T-O-393` | `pre-charter-qna.md` §5 | Phase 1/4 分界；CLI fail-closed；不锁 pool | STOP/reopen Q13；禁止把 parser 塞进 S11 或反向 |
| Q19 / `T-O-399` | 同上 | Phase 2/3/5 隔离、禁 `--no-sandbox`、S16、SBOM 生产门 | 不得以「容器方便」降级。隔离红线（禁 `--no-sandbox` / parser 无网）须 reopen Q19；pin/SBOM/CVE/readiness 豁免仅 owner 具名延期 |
| Q23 / `T-O-403` | 同上 | Phase 3 共享 binary、分 cap；淘汰常量 profile | 不得用 render 顶 print 或拆成两种 strategy taxonomy |
| `T-O-376` | `pre-initial-planning-qna.md` | 503/诚实未部署不是通道 DoD；本 AP typed 503 只证明缺供给诚实 | 禁止把 T09 503 写成 NH7 live |
| `T-O-378` | 同上 | 假 PDF/盗码/monkeypatch/空 clean 禁 | 正则提取或 monkeypatch 绿 = FAIL |
| Q26 / `T-O-406` | `pre-charter-qna.md` | 最低层按台账 C；waiver 只延期 | 禁止 L1 顶 T03/T04 L3 |
| Q8 / `T-O-388` | `pre-initial-planning-qna.md` | print 必须诚实 PDF bytes（供给在本 AP，fact 合同在 NH3） | 不得 HTML 改名 print_pdf |
| `T-O-386` | 同上 | promptA 仅 LLM；确定性 OCR 无 prompt | 确定性 OCR 不得伪造 PromptRef |
| `T-O-377` / `O-NH-06` | QNA / final §4.2 | 零 CF/云 OCR/通用 JOIN | 发现回流立即 FAIL |
| `G-NH-04/10/15` | `pre-charter-qna.md` §8 | 已 CLOSED；本 AP 只执行，不重开选项 | 证伪 → reopen final，不准另选库当 Truth |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表（本计划工作要落在哪些既有代码 / 新建点上）

台账 B 六锚必须出现。`处置` 用 ✅ 复用 / ♻️ 重 substrate / 🆕 净新。

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| `NH6-A01` | `src/contracts/inference/models.py:96-108` | `GenerateRequest` 仅 `input_text`（另：`:18` 无 vision/ocr；`:63-70` 禁 payload_extra 偷运） | `NH6-05` 扩 multimodal | `♻️ 重 substrate` | 独立核对：字段 prompt_ref/prompt_digest/input_text/system_text |
| `NH6-A02` | `src/runtime/inference/claude_cli.py:505-508` | 非 `text/*` 或纯 blob → `CLEAN_MEDIA_UNSUPPORTED` 422 | `NH6-05/06` 保持；不当 OCR fallback | `✅ 复用` | 单测 `tests/unit/test_ns5_phase3.py:112-115` 已钉；形状 kill 见 `:320-337,423-440` |
| `NH6-A03` | `api/app.py:244-266,330-345` | ConcurrencyGate 三能力+cli；`IntakePipeline` **无** `browser_fetcher=`/`clean_llm=` | `NH6-07` 扩具名键；`NH6-10` 注入 | `♻️ 重 substrate` | `T-R-NH-26`；独立核对 332-345 关键字 |
| `NH6-A04` | `src/runtime/http_acquisition.py:182-208` | `HttpAcquirer`：生产不自动 redirect、禁环境代理 | `NH6-03/04` browser 每跳复核 | `✅ 复用` | 每跳实现续 `:221-255`；政策 `security.py:368-414`（`check_url`）+ `:433-439`（`validate_redirect`） |
| `NH6-A05` | `src/llm_adapters/local_vllm.py:276-295` | `probe` = `GET /v1/models` 且 `id==model_key` | `NH6-08` 实弹 probe；名单不足 | `🆕 净新`（probe 语义） | generate 仍 string content `:207-216` |
| `NH6-A06` | RA05 parser/browser/OCR official/advisory | capability+失败法；许可证/CVE；不锁库名 | `NH6-02/03/04/06/09` | `🆕 净新` local 隔离 | 只借失败法/许可证类别 |
| `NH6-H01` | `src/runtime/intake/core.py:45-70` | http/browser/clean_llm 分端口；禁 HTTP 冒充 rendered | `NH6-03/10` 保围栏 | `✅ 复用` | 端口在、默认 `None` |
| `NH6-H02` | `src/runtime/health.py:16-25` | REQUIRED 九项无 binary/pdf/ocr | `NH6-01/08` | `♻️ 重 substrate` | `_compute` `:93-108` 全 ok 才 ready |
| `NH6-H03` | `src/runtime/intake/types.py:144-171` | 同进程正则 PDF + 盗 OCR 码 | `NH6-02` 撤提取权威 | `♻️ 重 substrate` | **观察改写在 NH3**；本 AP 供给与隔离 |
| `NH6-H04` | `pyproject.toml:13-21` | 七依赖；无 PDF/browser/OCR | `NH6-09/10` | `🆕` 供给依赖只经 SBOM | license Proprietary `:11` |
| `NH6-H05` | `src/runtime/inference/facade.py:102-132` | 满闸零 model call | `NH6-07` | `✅ 复用` | 扩 key 不改「满则零调用」 |
| `NH6-H06` | `src/runtime/workflow/dispatch.py:42-43,122-146` | 三池；ocr/vision/browser `unpooled` | `NH6-01/07` | `♻️` 具名 gate，禁无名第四池 | `GENERATE_PROCESS_KEYS` 不含 ocr/vision |
| `NH6-H07` | `src/runtime/intake/acquisition_ingest.py:477-485,535-536` | 缺 browser 503；常量 profile | `NH6-03/04` | `♻️` 保 503 码；淘汰常量 | print kind 生产属 NH3+本供给 |
| `NH6-H08` | `intake/pdf/__init__.py:48-50` | OCR 未注入 503 能力码 | `NH6-06` 对照 | `✅ 复用` | 不得回流 decode |
| `NH6-N01` | `tests/e2e/test_nh6_pdf_parser.py` 等（§8） | 将新建测试与 fixtures | `NH6-T01..T10` | `🆕 净新` | 含固定路径 `test_new_harvest_runtime_security.py` |

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | `GenerateRequest` 不改就运 OCR/Vision | `NH6-A01`；`T-O-393`；`NH-C-49` |
| ⛔2 | CLI 拒 binary 当「已有 vision」或当 OCR fallback | `NH6-A02`；`clean_preflight.py:75-107` 已禁 CLI 兜底 OCR/Vision |
| ⛔3 | 默认根未注入却宣称通道 complete / 503 当 DoD | `NH6-A03`；`T-O-376`；`FG-NH-02` |
| ⛔4 | `/v1/models`、`import`、`which` 当 ready | `NH6-A05`；`FG-NH-11`；`T-R-NH-10` |
| ⛔5 | 同进程正则 PDF / 无层盗 OCR 码 | `types.py:155-159`（函数 `:144-171`）；`T-O-378`；提取权威在本 AP 替换 |
| ⛔6 | 测试后 `pipeline._browser_fetcher =` / lambda HTML | `tests/e2e/test_source_capability_paths.py:99-101`；`FG-NH-01` |
| ⛔7 | 常量 `injected-browser-renderer.v1` | `acquisition_ingest.py:536`；`T-O-403` |
| ⛔8 | render 成功顶替 print；HTML/screenshot 改名 `%PDF-` | Q23；RA03 `NH-C-22` |
| ⛔9 | 生产默认 `--no-sandbox` / root browser | Q19；RA05 WEB-08；`R-F06` |
| ⛔10 | parser 与 browser 共用一份网络策略 | Q19：parser 无网 / browser 受控 egress 分账 |
| ⛔11 | 云 OCR / CF Browser Rendering / Gemini alias / R2 | `O-NH-06`；`T-O-377`；RA05 LEGACY-04 |
| ⛔12 | GPL/AGPL **链入** Proprietary 主进程 | `pyproject.toml:11`；RA05 WEB-04/06 |
| ⛔13 | `payload_extra` 塞 image；浮动 `latest` | `models.py:63-70`；`T-O-399` pin |
| ⛔14 | 第四无名 `DispatchPool`；或把 unpooled 假装已在 generate 池 | `dispatch.py:42-43,122-146`；pool 数不锁 ≠ 无名池 |
| ⛔15 | NH1-T06 smoke / Protocol fake 当本 AP DoD | AP-NH1 §8.4；final §7.6 NOT-成功 |
| ⛔16 | 锁库名为新 T-O | `T-O-393`；writer 硬禁 |
| ⛔17 | 仓库内写 exploit/CVE PoC payload | 安全政策；T02 只用资源炸弹/加密/畸形夹具 |
| ⛔18 | S16 签收栏填假签名冒充已审 | 签收是文档门，不是伪造已签 |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：[`assessment-analysis-05-runtime-adapters-readiness-and-security.md`](../../eval/new-harvest/reference-anchor/assessment-analysis-05-runtime-adapters-readiness-and-security.md) —— §7.1 是与本 AP 相关子集；完整借鉴台账（`NH-RA05-B01..B12`、`NH-C-40..49`、`NH-N-05-01..05`）见真源。RA03 只消费 print/PDF **观察诚实**（`NH-RA03-B01/B02/B12`），生产供给不在 RA03。
- **上游 AP**：[`AP-NH1`](AP-NH1-foundation-contracts-and-proof-baseline.md) `NH1-06`/`NH1-T06`（smoke ≠ DoD；`stop-or-go.md=GO`）；[`AP-NH3`](AP-NH3-representation-history-and-s05-binding.md) `NH3-04/05`（观察/能力分码；print fact 合同；§8.4 明确供给交本 AP）。
- **安全 / 信任边界威胁模型锚**（不得留空）：
  1. **恶意 PDF DoS/RCE 打 API 主进程**：`types.py:144-171` 同进程；RA05 `NH-RA05-B06` / WEB-02；缓解 = `T-O-399` 无网 subprocess + T02。
  2. **不可信 URL 浏览器逃逸 + SSRF**：S16 `TM-04` / `S16-E08`（`docs/baseline/domain-truth/S16-security-trust-boundary.md`）；`NH-RA05-B12` browser 未接 egress；缓解 = non-root、禁 `--no-sandbox`、每跳 `EgressPolicy`（T05）。
  3. **许可证传染**：Proprietary vs GPL/AGPL 链入（RA05 WEB-04/06）；缓解 = T10 inventory + 禁链入。
  4. **假就绪 / 假接线**：models-list（A05）、monkeypatch（FG-NH-01）、503-as-DoD（FG-NH-02）。

---

## 8. 测试台账

### 8.1 测试清单（主表）

PASS 证据四元组统一：`commit SHA + pytest node PASS + Truth/Q + UTC`。状态在执行前一律 `未观察`。

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| `NH6-T01` | PDF compressed/CID/absent/encrypted 真提取 vs typed absent；盗码禁止 | spike/S | L2/L3 | `🆕 tests/e2e/test_nh6_pdf_parser.py` + fixtures | `NH6-02` → PDF 真提取/分码 | `commit SHA + fixture PASS + Q19 + UTC` |
| `NH6-T02` | parser 无网 / 资源 kill / 恶意样本 API 存活 | security | L2/S | `🆕 tests/e2e/test_nh6_parser_isolation.py` | `NH6-02/09` → 隔离 | `commit SHA + isolation PASS + T-O-399 + UTC` |
| `NH6-T03` | SPA render 真实 DOM/profile；`create_app()` 无 patch | live | L3 | `🆕 tests/e2e/test_nh6_browser_render.py` | `NH6-03/10` → DOM 真实 | `commit SHA + browser PASS + Q23 + UTC` |
| `NH6-T04` | print 真 `%PDF-` / 独立 budget；render 不得顶替 | live | L3 | `🆕 tests/e2e/test_nh6_browser_print.py` | `NH6-04/10` → PDF 真实 | `commit SHA + PDF PASS + Q23 + UTC` |
| `NH6-T05` | browser non-root / 禁 `--no-sandbox` / egress 每 redirect | security | L2/L3/S | `🆕 tests/e2e/test_new_harvest_runtime_security.py`（final §9.1） | `NH6-03/04/09` → 政策 | `commit SHA + policy PASS + Q19 + UTC` |
| `NH6-T06` | multimodal bytes/handle+PromptRef；非 `input_text` only | 集成 | L2/L3 | `🆕 tests/integration/test_nh6_multimodal_request.py` + e2e adapter | `NH6-05/06/10` → 协议运输 | `commit SHA + adapter PASS + Q13 + UTC` |
| `NH6-T07` | OCR/Vision empty/bad/timeout typed；禁 cloud/latest | fault | L1/L2 | `🆕 tests/unit/test_nh6_ocr_vision_errors.py` + `🆕 tests/integration/test_nh6_ocr_vision_port.py` | `NH6-06` → 空/错不成功 | `commit SHA + typed errors PASS + Q13 + UTC` |
| `NH6-T08` | backpressure 满载零下游调用 | race | L1/L2/R | `♻️ gate tests` + `🆕` full→zero | `NH6-07` → 满载零调用 | `commit SHA + metrics PASS + Q13 + UTC` |
| `NH6-T09` | readiness 正负一致；models-list 不足 | soak | L2/L3 | `🆕 tests/e2e/test_nh6_readiness.py` | `NH6-08/10` → 组件==在场 | `commit SHA + health PASS + Q19 + UTC` |
| `NH6-T10` | license/SBOM/CVE/waiver 完整 | contract | L1 | `🆕 tests/domain/test_nh6_sbom_inventory.py` | `NH6-09` → 每条 pin | `commit SHA + inventory EXIT0 + Q19 + UTC` |

#### `NH6-T01`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_nh6_pdf_parser.py::test_compressed_tounicode_extracts_text`；`::test_cid_font_extracts_unicode_or_typed`；`::test_absent_text_layer_typed_absent`；`::test_encrypted_typed_encrypted`；`::test_literal_regex_is_not_authority`；**强制 L3** `::test_create_app_parser_extracts_tounicode_without_patch` |
| 用途 | 证明 `NH6-02`；Q19；`T-O-378`；FG-NH-06（空正文不得成功）；**不是** NH3 观察单测的重复——本节点走 **真实 parser 供给** |
| 前置 | **删除「或 L2」**。L3 节点必须 `create_app()` default-root、零 monkeypatch、真 fixture；缺 parser binary → **FAIL 非 skip**。L2 真实 subprocess 可伴生，**不得**单独关闭 T01，也不得关闭台账 D「PDF supply」。夹具 `tests/fixtures/new_harvest/pdf/compressed_tounicode.pdf`、`cid_font.pdf`、`absent_text_layer.pdf`、`encrypted.pdf`；NH3-04 观察码已存在（absent/encrypted 字面消费 NH3，不得回流 OCR-unavail） |
| 步骤 | a) 送 compressed/ToUnicode PDF，取提取文本。b) 送 CID 样本。c) 送无层与加密样本。d) 断言 `types.py` 正则路径不再是 present 权威（源码或行为：无 Tj 的压缩样本仍能提取或走新引擎）。e) L3：`create_app()` 无 patch 走默认根 parser，提取 ToUnicode 正文。 |
| 断言细节 | compressed 文本非空且可复现；absent → 观察/错误码 `absent` 且 **零** `CLEAN_OCR_CAPABILITY_UNAVAILABLE`；encrypted → `encrypted`；空字符串不得 `text_layer=present`；decoder identity ≠ `local-pdf-literal-text.v1` 作为权威；L3 HTTP 非 503 当成功证明 |
| 负例 | 未压缩 Tj 正则当绿；无层 422 OCR；把 NH3 unit 顶本 L2/L3；只把文件放进 `tests/e2e/` 就算 L3；缺 binary skip |
| 跑法 | `uv run pytest tests/e2e/test_nh6_pdf_parser.py::test_create_app_parser_extracts_tounicode_without_patch tests/e2e/test_nh6_pdf_parser.py -q` |
| 层与来源 | L2/L3；`🆕`；标签 S。**L2 不得单独 PASS** |

#### `NH6-T02`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_nh6_parser_isolation.py::test_parser_subprocess_has_no_network`；`::test_resource_kill_on_timeout`；`::test_malicious_pdf_does_not_kill_api` |
| 用途 | 证明 `NH6-02/09`；`T-O-399`；威胁模型 7.3.1；FG-NH-13（不得用 `which pdftotext` 顶） |
| 前置 | 可观察子进程环境（net namespace / 拒绝列表 / 尝试 connect）；超限夹具（深层嵌套/超大输出，**非** exploit PoC）；并行持有 `create_app()` 的 `/ready` 客户端 |
| 步骤 | a) parser 运行中探测 DNS/HTTP，必须失败且主请求 typed fail 或仍隔离成功。b) 触发 time/output cap，断言子进程被 kill、主进程在。c) 送资源炸弹，GET `/ready`。 |
| 断言细节 | 子进程无成功外连；kill 后无僵尸（或测试内 wait 回收）；API 进程 PID 不变；`/ready` 200 **或** 进程存活（台账 D：至少进程存活）；错误 typed，非空 clean 成功 |
| 负例 | 主进程 segfault；in-process 解析；入库 CVE exploit payload |
| 跑法 | `uv run pytest tests/e2e/test_nh6_parser_isolation.py -q` |
| 层与来源 | L2；标签 S；`🆕` |

#### `NH6-T03`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_nh6_browser_render.py::test_spa_real_dom_nonconstant_profile`；`::test_create_app_without_patch_reaches_render` |
| 用途 | 证明 `NH6-03/10`；Q23；`FG-NH-01/02`；Capstone D/E 供给侧的 render 半边 |
| 前置 | `create_app()` default root；**零** `pipeline._browser_fetcher` 赋值；本地 SPA fixture（JS 渲染后主文不在初始 HTML）；缺 binary → **FAIL** 非 skip |
| 步骤 | a) 经默认根对 SPA URL 走 render cap。b) 断言返回 DOM 含 JS 注入的主文节点。c) 读 profile/evidence。d) 源码/测试扫描本文件无 monkeypatch fetcher。 |
| 断言细节 | DOM 非静态壳；`browser_profile` ≠ `injected-browser-renderer.v1` 且非 None；HTTP 非 503 当成功证明（缺供给必须本测试 FAIL，不是 skip）；无 `_browser_fetcher =` |
| 负例 | lambda `"<main>browser capability text</main>"`（HEAD `:101`）；screenshot 当 DOM；测试后赋 port |
| 跑法 | `uv run pytest tests/e2e/test_nh6_browser_render.py -q` |
| 层与来源 | L3 default-root；`🆕`；live |

#### `NH6-T04`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_nh6_browser_print.py::test_print_real_pdf_header`；`::test_independent_budget_from_render`；`::test_render_success_does_not_satisfy_print` |
| 用途 | 证明 `NH6-04/10`；Q23；`T-O-388` 供给侧 |
| 前置 | 同 T03 的 `create_app()` 无 patch；print cap 独立 limit 配置；可先跑一次 render |
| 步骤 | a) print 同一 SPA/URL。b) 检查 bytes。c) 对照 render 与 print 的 budget/concurrency 计数器。d) 故意只完成 render，断言 print 节点仍独立失败或独立成功，不得 skip。 |
| 断言细节 | `body.startswith(b"%PDF-")`；print evidence 含独立 profile/timeout/size；render 指标增加不得自动增加 print 成功计数；`representation_kind` 若本节点写 fact，必须 `print_pdf`（否则标「只验供给 bytes，fact 由 NH3-T04 验」且仍须 `%PDF-`） |
| 负例 | HTML 当 PDF；用 T03 PASS 跳过 T04；共享唯一并发帽导致 print 被 render 耗尽却报成功 |
| 跑法 | `uv run pytest tests/e2e/test_nh6_browser_print.py -q` |
| 层与来源 | L3；`🆕`；live |

#### `NH6-T05`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_new_harvest_runtime_security.py::test_browser_runs_non_root`；`::test_production_forbids_no_sandbox`；`::test_browser_egress_rechecks_each_redirect`；`::test_parser_process_network_denied` |
| 用途 | 证明 `NH6-03/04/09`；Q19；`R-F06`；S16-E08；**本文件是 final §9.1 固定安全面**，NH9-T10 将 🔱 |
| 前置 | 生产配置路径（非 debug 开关）启动 browser/parser；可注入 redirect URL（metadata / 私网 / 超预算）；T02 无网断言可复用但本节点必须覆盖 **browser** 每跳 |
| 步骤 | a) 读 browser 子进程 uid/argv。b) 断言 argv 无 `--no-sandbox`。c) 安排 ≥1 次 redirect，每跳必须调用 `EgressPolicy`（可用计数/审计）；最终跳到受限地址 → `SEC_EGRESS_DENIED` 或 `SEC_EGRESS_REDIRECT_DENIED`。d) parser 侧再确认无网（与 T02 互补，本节点挂在固定安全文件）。 |
| 断言细节 | uid ≠ 0（或明确 non-root 用户命名空间）；argv 扫描无 `--no-sandbox`；redirect 次数 ≤ `egress_max_redirects`（HEAD 默认 3，`config.py:63`）；每跳复核次数 ≥ hop 数；受限目标 422 族安全码 |
| 负例 | 测试专用 `--no-sandbox` 当生产 PASS；只测第一跳；把 HttpAcquirer 单测顶 browser 出站 |
| 跑法 | `uv run pytest tests/e2e/test_new_harvest_runtime_security.py::test_browser_runs_non_root tests/e2e/test_new_harvest_runtime_security.py::test_production_forbids_no_sandbox tests/e2e/test_new_harvest_runtime_security.py::test_browser_egress_rechecks_each_redirect tests/e2e/test_new_harvest_runtime_security.py::test_parser_process_network_denied -q`（**禁止**整文件 `-q` 吞掉 T08/NH9 后继节点） |
| 层与来源 | L2/L3；标签 S；`🆕`（路径冻结；本 AP 先建这四 node） |

#### `NH6-T06`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/integration/test_nh6_multimodal_request.py::test_bytes_and_handle_plus_promptref`；`::test_rejects_input_text_only_for_vision`；`::test_payload_extra_cannot_smuggle_media`；🆕 `tests/e2e/test_nh6_multimodal_adapter.py::test_adapter_transports_media_not_string_content`；`::test_cli_still_rejects_binary` |
| 用途 | 证明 `NH6-05/06/10`；Q13；Capstone **E 供给侧**；`FG-NH-01` |
| 前置 | 合同模型可 import；L3 节点 `create_app()` 无 patch；S13 handle 或 bounded bytes；CLI 路径仍注入 `claude_cli` |
| 步骤 | a) 构造 PromptRef+media_type+digest/handle 请求。b) 仅 `input_text` 调 Vision/DU。c) payload_extra 塞 content。d) adapter 发出的 HTTP body 含 parts/media 而非纯 string。e) CLI complete(blob=PDF)。 |
| 断言细节 | a 成功形状含 binding+prompt_digest+media digest；b typed fail；c ValidationError/`payload_extra` 禁键；d **L2 only**：integration 节点可用抓包/fake transport 证编码形状无「只 input_text」；e `CLEAN_MEDIA_UNSUPPORTED` 422。**L3** `test_nh6_multimodal_adapter.py` 必须经 `create_app()` 无 patch 打到已注入 adapter 的一次受控 media 调用（真实或已注入的 local adapter，**禁止** Protocol/fake complete 关闭 T06） |
| 负例 | Protocol stub complete 当 L3；base64 塞进 `input_text`；models-list 200 当本测试 PASS；用 L2 fake transport 单独关闭 T06 或 default wiring |
| 跑法 | `uv run pytest tests/integration/test_nh6_multimodal_request.py tests/e2e/test_nh6_multimodal_adapter.py -q` |
| 层与来源 | L2/L3；`🆕`。fake transport **锁在 L2**；L3 不可缺 `create_app()` |

#### `NH6-T07`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/unit/test_nh6_ocr_vision_errors.py::test_empty_output_typed_fail`；`::test_bad_bytes_typed_fail`；`::test_timeout_typed_fail`；`::test_forbids_cloud_ocr_and_latest_float`；`::test_deterministic_ocr_has_no_promptref`。**强制 L2** 🆕 `tests/integration/test_nh6_ocr_vision_port.py::test_empty_bad_timeout_typed_fail_zero_admitted_clean` |
| 用途 | 证明 `NH6-06`；Q13；`T-O-378/383` 空成功禁 |
| 前置 | 确定性 OCR port 与 S11 multimodal 分类可调用。L1 可用夹具/fake 时钟。**L2** 必须走真实 OCR port 或 PersistencePort UoW（empty/bad/timeout → typed error、零 admitted clean）；L1 不得单独 PASS |
| 步骤 | a) 空输出。b) 坏字节。c) 超时。d) 扫描配置/源码禁云 endpoint 与 `latest`。e) 确定性 OCR 调用无 PromptRef 字段。f) L2：经 port/UoW 跑 a–c，断言无 admitted clean 行。 |
| 断言细节 | 均 typed error（非 200 空字符串）；源码/config 无云 OCR URL；pin ≠ `latest`；确定性路径不读 `prompt_ref`；L2：`mkb` admitted clean COUNT=0 |
| 负例 | Empty page 当 admitted clean；cloud fallback；用 CLI 兜底 OCR；unit 全绿关闭 T07 |
| 跑法 | `uv run pytest tests/unit/test_nh6_ocr_vision_errors.py tests/integration/test_nh6_ocr_vision_port.py::test_empty_bad_timeout_typed_fail_zero_admitted_clean -q` |
| 层与来源 | L1/L2；fault；`🆕`。**L1 不得单独 PASS** |

#### `NH6-T08`

| 字段 | 要求 |
|---|---|
| 测试位置 | ♻️ `tests/unit/test_dispatch_embed_and_gates.py`（既有 embed/structured/text 满闸）；🆕 `tests/unit/test_nh6_backpressure_zero_calls.py::test_full_gate_zero_parser_calls`；`::test_full_gate_zero_browser_render_and_print_calls`；`::test_full_gate_zero_multimodal_adapter_calls`。**强制 L2** 🆕 `tests/e2e/test_new_harvest_runtime_security.py::test_backpressure_zero_downstream`（真实 port/UoW 或 default-root 满载零下游） |
| 用途 | 证明 `NH6-07`；Q13；满载零下游 |
| 前置 | `ConcurrencyGate` 将 parser/render/print/multimodal 限额设为 1 或测试值；下游 port 用计数包装。L2 节点不得只靠 unit 计数包装 |
| 步骤 | a) 占满具名 cap。b) 再请求同一 cap。c) 断言返回 BACKPRESSURE。d) 断言包装 port 调用次数不增加。e) L2：default-root 或真实 port 满载后再请求，下游 binary/adapter 调用次数不增加。 |
| 断言细节 | 第二次 `try_acquire` 失败或 API 503 `INFERENCE_BACKPRESSURE`（或登记的能力 BACKPRESSURE 码）；parser/browser/adapter call count 与满载前相同；既有三键回归仍 PASS。L2 node PASS 才关闭 T08 |
| 负例 | 排队空转仍调用 binary；无名第四池吞掉指标；unit 全绿关闭 T08 |
| 跑法 | `uv run pytest tests/unit/test_dispatch_embed_and_gates.py tests/unit/test_nh6_backpressure_zero_calls.py tests/e2e/test_new_harvest_runtime_security.py::test_backpressure_zero_downstream -q` |
| 层与来源 | L1/L2；标签 R；`♻️`+`🆕`。**L1 unit 不得单独 PASS** |

#### `NH6-T09`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_nh6_readiness.py::test_positive_probe_matches_presence`；`::test_missing_binary_component_not_overall_green`；`::test_models_list_insufficient_for_ready`；`::test_create_app_readiness_without_patch` |
| 用途 | 证明 `NH6-08/10`；Q19；`FG-NH-11`；soak 标签 = 正负反复与真实在场一致，**不是** L4 |
| 前置 | 可拆 binary（PATH/config 指向不存在路径）的负部署；正部署含真实 fixture；可 stub `GET /v1/models` 200 |
| 步骤 | a) 正部署：`GET /ready` 对应组件 ok 与实弹 probe 一致。b) 卸 parser 或 browser binary：该组件 false，整体不得绿。c) 仅 models-list 200、缺 browser/parser：multimodal/parser/browser 组件不得 ok。d) 全程无 monkeypatch fetcher。 |
| 断言细节 | 组件名与 `NH6-01` readiness key 对齐；整体 `status=ready` 当且仅当 REQUIRED（含已声明启用的供给组件）全 ok；`/ready` 503 表示诚实未就绪，**不得**当作 NH7 DoD；名单不足 |
| 负例 | 九项旧 REQUIRED 全绿掩盖缺 Chromium；skip 缺环境；测试后赋 port 再 GET `/ready` |
| 跑法 | `uv run pytest tests/e2e/test_nh6_readiness.py -q`（正负两环境；缺正环境 FAIL 非 skip） |
| 层与来源 | L2/L3；soak；`🆕` |

#### `NH6-T10`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/domain/test_nh6_sbom_inventory.py::test_every_binary_has_pin_license_sbom_cve_or_waiver`；`::test_waiver_requires_owner_name`；`::test_no_library_name_frozen_as_truth` |
| 用途 | 证明 `NH6-09`；Q19；`R-F05` |
| 前置 | 机器可读 inventory（建议 `docs/evidence/new-harvest/AP-NH6/security/sbom-inventory.json` 或 `src` 内 registry 导出）；与 `NH6-01` identity 对账 |
| 步骤 | a) 枚举 registry 每个 binary/model。b) 断言 pin/license/SBOM/CVE 字段非空或 waiver。c) waiver 含 owner、受影响 Truth、到期。d) 扫描本 AP 与 inventory 不得把单一库名标为 T-O。 |
| 断言细节 | EXIT0；无匿名 waiver；无 GPL/AGPL **link** 进主进程依赖（subprocess 须在 license 字段标明形态）；`latest` 禁止 |
| 负例 | 空清单当绿；把 README「可用 pypdf」写成 Truth |
| 跑法 | `uv run pytest tests/domain/test_nh6_sbom_inventory.py -q` |
| 层与来源 | L1 契约；`🆕` |

### 8.2 复用台账（沿用 / fork 的既有用例明细）

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/unit/test_dispatch_embed_and_gates.py:259-294` | `♻️ 沿用` 三键闸 + 本 AP T08 回归 | 0 或仅保证新 key 不破坏旧限额 | 已存在 PASS |
| `tests/unit/test_ns5_phase3.py::test_non_text_blob_is_rejected` | `♻️ 沿用` CLI 拒 binary | 0；T06 再钉一次生产路径 | 已存在 PASS |
| `tests/unit/test_ns6_phase3.py` ConcurrencyGate | `♻️ 沿用` 满闸零调用形状 | T08 扩到新 cap | 已存在 |
| `tests/e2e/test_nh1_runtime_smoke.py`（NH1-T06） | **不沿用为 DoD** | smoke ≠ 本 AP PASS | 上游门槛 GO |
| `tests/e2e/test_source_capability_paths.py:99-101` | `⛔ 反例` | 禁止 🔱 为 T03/T04 成功路径 | HEAD monkeypatch |
| `tests/integration/test_nh3_print_fact.py`（NH3-T04） | **消费合同、不顶 L3** | 本 AP T04 才是 default-root 真 PDF | NH3 L2 不得标 live |
| `tests/unit/test_nh3_pdf_observation.py`（NH3-T03） | **消费观察码** | 本 AP T01 换真引擎 | 盗码回归仍算 FAIL |

### 8.3 分层与跑法（各类型在哪跑、何时跑）

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `uv run pytest tests/unit/test_nh6_ocr_vision_errors.py tests/unit/test_nh6_backpressure_zero_calls.py tests/unit/test_dispatch_embed_and_gates.py tests/domain/test_nh6_sbom_inventory.py -q` | L1 | 每 PR；**不得**单独关闭 T07 |
| 集成 | `uv run pytest tests/integration/test_nh6_multimodal_request.py tests/integration/test_nh6_ocr_vision_port.py tests/e2e/test_nh6_pdf_parser.py tests/e2e/test_nh6_parser_isolation.py -q` | L2 | Phase 2/4 收口。parser 文件的 L2 节点可伴生；T01 **不得**仅由此行关闭 |
| default-root live | `uv run pytest tests/e2e/test_nh6_pdf_parser.py::test_create_app_parser_extracts_tounicode_without_patch tests/e2e/test_nh6_browser_render.py tests/e2e/test_nh6_browser_print.py tests/e2e/test_nh6_multimodal_adapter.py tests/e2e/test_nh6_readiness.py -q` | L3 | Phase 2/3/5；缺 parser/browser binary FAIL 非 skip |
| security | `uv run pytest tests/e2e/test_new_harvest_runtime_security.py::test_browser_runs_non_root tests/e2e/test_new_harvest_runtime_security.py::test_production_forbids_no_sandbox tests/e2e/test_new_harvest_runtime_security.py::test_browser_egress_rechecks_each_redirect tests/e2e/test_new_harvest_runtime_security.py::test_parser_process_network_denied tests/e2e/test_new_harvest_runtime_security.py::test_backpressure_zero_downstream -q` | L2/L3/S | Phase 3/5 硬闸。禁止整文件 `-q` |
| mega / L4 query | 本 AP 不跑 | — | 交 NH7 Capstone E 到 query；交 NH9 closed-set |
| soak | T09 正负反复 | L2/L3 | 退出硬闸之一 |

本 AP 台账 C 最低层不得自行降：T01 L2/L3、T02 L2、T03 L3、T04 L3、T05 L2/L3、T06 L2/L3、T07 L1/L2、T08 L1/L2、T09 L2/L3、T10 L1。

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖 10+3 live-to-retrieval 与 namespace query（理由：`S-NH-F7`；本 AP 无 L4）→ `AP-NH7`。**Capstone E**：本 AP 交付 real binary/model、PromptRef、isolation/readiness（T05/T06/T07/T09）；**到 query** 属 NH7-T07/T10，**不在本 AP 假装覆盖**。
- 不覆盖七意图 / exact-clean（理由：NH8）→ `AP-NH8`。
- 不覆盖 campaign mega / crash 全窗 `W-NH-CREATE/SEL/SEAL/PROCESS/PROM-CAT/GC-INGEST/FANIN/PUB/OUTBOX`（理由：NH9）→ `AP-NH9`。本 AP 只在 `tests/e2e/test_new_harvest_runtime_security.py` 写入 NH6 节点，供 NH9-T10 🔱。
- 不覆盖 PDF 观察码改写与 print fact 行合同（理由：已交 NH3-04/05）→ 回归盗码仍 FAIL，但不在本 AP 重做 fact schema。
- 不把库名冻成 Truth；不覆盖 CF Browser Rendering。
- 不覆盖 NH1 smoke 的「形态可行」重复当本 DoD。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 必带四元组；计数 ≠ 价值。
- 本 AP 适用 FG（必须在对应细则点名）：
  - `FG-NH-01`：T03/T04/T06/T09 成功路径零 `_http_fetcher/_browser_fetcher/_clean_llm` 赋值。
  - `FG-NH-02`：T09 的 503 是诚实未就绪，不是 NH7/本 AP 供给 DoD 的成功态。
  - `FG-NH-06`：T01/T07 空/空白提取不得成功。
  - `FG-NH-11`：T08/T09/T10 — import/which/models-list 不足。
  - `FG-NH-13`：T03/T04 不得用 L1 顶 L3。
  - `FG-NH-16`：experiment 不进 evidence。
  - `FG-NH-17`：不得改期待值掩盖缺 binary。
- `degraded` 必带机器可读 `reason`；缺环境 FAIL 非 skip。
- 安全项 T02/T05 必须含攻击向量：无网逃逸、redirect SSRF、root/no-sandbox、资源炸弹（非 exploit payload）。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| DAG：NH1 GO | `stop-or-go.md≠GO` 或 T06 非三次 PASS | high（外部） | 本 AP 不得开工；不可行 STOP ≠ 本 DoD |
| DAG：NH3 诚实表示 | 盗码/常量 profile 仍在 | high | 消费 NH3-04/05；本 AP 不重开观察法 |
| `R-F05` 供应链 | license/CVE/binary 不可部署 | high | T10；waiver 只延期；替代 reopen |
| `R-F06` browser 降级 | root / `--no-sandbox` / 绕 egress | high | T05 + S16 签收栏 |
| `FG-NH-01/11` 假绿 | monkeypatch / models-list | high | T03/T04/T06/T09 扫描与负 probe |
| 库名滑入 Truth | 实现者把 pin 写成 T-O | medium | T10 扫描；AP 正文禁锁库 |
| NH4/NH5 并行 | 本 AP 不依赖其完成 | low | 尾部并行；NH7 再 join |
| GPL 链入 | 为方便 link poppler/MuPDF | high | T10 禁链入；subprocess 须标明 |

### 9.2 约束与前提

- **技术前提**：HEAD `1221aa1` 端口三分、三池闸、EgressPolicy、CLI 拒 binary、SupplyFence 均在；NH1 GO；NH3 观察/print 合同可用。
- **运行时前提**：L3 使用 `create_app()` 默认根；缺 binary FAIL；parser 无网、browser 有网但 S16。
- **组织协作前提**：不重开 Q13/Q19/Q23；不新增 owner-gate；S16 review 签收栏在执行时由具名角色签署，本 AP 只留空栏。
- **上线 / 合并前提**：`NH6-T01..T10` 全 PASS；`FG-NH-11` 绿；S16 签收栏 **文件存在且字段完整可签**（执行完成前状态 `未观察`，禁止预填假签）。无新业务表义务；config/readiness keys 允许。

### 9.3 文档同步要求

- 需要同步更新的设计文档：本 AP 保持 draft；**禁止**改 QNA/final/RA
- 需要同步更新的说明文档 / README：执行阶段可更新 README 供给/readiness 诚实句；本轮文档战役不改生产 README 除非后续执行 AP
- 需要同步更新的测试说明：evidence `tests.txt` + `security/`

### 9.4 完成后的预期状态

1. 默认组合根注入真实 local ports 与 S11 multimodal 运输；缺供给 typed 失败 + 组件非绿。
2. PDF 提取来自无网 isolated subprocess；DOM 与 print PDF 分 cap 且各自真实。
3. `/ready` 正负与在场一致；models-list 不能单独证明 runtime。
4. 每 binary/model 有 pin/license/SBOM/CVE 或 owner 具名 waiver。
5. NH7 可消费供给做 10+3 live query；NH9 可 🔱 本 AP 安全文件。本 AP **不**宣称四通道可检索。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

收口 = §8 逐项 PASS，且每项映射回 §3 收口目标。**禁止**用「测试通过」四字替代下列谓词。

### 10.1 收口硬闸

所有退出层测试必须 **PASS 且四元组证据齐全**：

1. **PDF**：真 ToUnicode/压缩提取；absent/encrypted 分码；恶意样本不杀 API（`/ready` 仍 200 或至少进程存活）（由 `NH6-T01`/`NH6-T02` 证明）
2. **browser**：DOM 与 PDF **各自**真实；non-root sandbox + 每跳 egress；生产无 `--no-sandbox`（由 `NH6-T03`/`NH6-T04`/`NH6-T05` 证明）
3. **model**：bytes/handle+PromptRef；空/错不成功（由 `NH6-T06`/`NH6-T07` 证明）
4. **budget/readiness**：满载零调用；component 状态 == 实际在场；缺项不是整体绿（由 `NH6-T08`/`NH6-T09` 证明）
5. **supply trust**：每 binary/model 有 pin/license/SBOM/CVE/waiver（由 `NH6-T10` 证明）
6. **default wiring**：`create_app()` 无需 patch 可达供给（由 `NH6-T03`/`NH6-T04`/`NH6-T06`/`NH6-T09` 证明）
7. **`FG-NH-11`**：import/which/models-list 不得当 ready（由 T09/T10 证明）
8. **S16 review 签收栏**：`docs/evidence/new-harvest/AP-NH6/security/s16-egress-browser-review.md` 含 reviewer/owner/UTC 空栏与检查清单；**签收本身是文档门，不是伪造已签**

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

抄 final §7.6 台账 D，钉死谓词：

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| PDF supply：真提取、typed absent、恶意样本不杀 API | `NH6-02` | `NH6-T01` / `NH6-T02` | `commit SHA + fixture/isolation PASS + Q19 + UTC` | `未观察` |
| browser supply：DOM/PDF 各自真实，non-root sandbox+egress | `NH6-03` / `NH6-04` / `NH6-09` | `NH6-T03` / `NH6-T04` / `NH6-T05` | `commit SHA + profile+security PASS + Q19/Q23 + UTC` | `未观察` |
| model supply：bytes/handle+PromptRef，空/错不成功 | `NH6-05` / `NH6-06` | `NH6-T06` / `NH6-T07` | `commit SHA + adapter/typed errors PASS + Q13 + UTC` | `未观察` |
| budget/readiness：满载零调用；component 与实际在场一致 | `NH6-07` / `NH6-08` / `NH6-10` | `NH6-T08` / `NH6-T09` | `commit SHA + metrics/health PASS + Q13/Q19 + UTC` | `未观察` |
| supply trust：每 binary/model 有 pin/license/SBOM/CVE/waiver | `NH6-09` | `NH6-T10` | `commit SHA + inventory EXIT0 + Q19 + UTC` | `未观察` |
| default wiring：create_app 无需 patch 可达供给 | `NH6-10` | `NH6-T03` / `NH6-T04` / `NH6-T06` / `NH6-T09` | `commit SHA + startup+e2e logs PASS + Q19 + UTC` | `未观察` |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | 默认根真实 local parser/browser.render/browser.print_pdf/确定性 OCR + S11 multimodal 运输；隔离与分 cap 符合 `T-O-393/399/403` |
| 测试 | §8 `NH6-T01..T10` 全 PASS；退出项四元组齐全；`FG-NH-11` 绿 |
| 文档 | 本 AP 仍为 `draft` 直至执行回填；evidence 目录文件齐；S16 签收栏存在且未伪造签名 |
| 风险收敛 | `R-F05/F06` 要么关闭要么具名 waiver 延期；无生产 `--no-sandbox`、无云 OCR、无锁库 Truth |
| 可交付性 | NH7 可在无 monkeypatch 的默认根上激活依赖本供给的格；NH9 可 🔱 安全文件 |

**evidence pack 规定文件名**（final §9.3；本 AP 只规定，不伪造 SHA）：

```text
docs/evidence/new-harvest/AP-NH6/
  manifest.json
  tests.txt
  queries/readiness-positive-negative.json
  queries/gate-metrics.json
  migrations/README.md                 # 无新业务表；注明 N/A
  security/sbom-inventory.json
  security/pin-license-cve.md
  security/isolation-parser-browser.md
  security/s16-egress-browser-review.md  # 签收栏：reviewer / owner / UTC / 清单；禁止预填假签
  security/owner-waivers.md              # 无则写「无 waiver」
  closure.md
```

### 10.4 NOT-成功识别

> 任一退出硬闸测试 `degraded / 未观察` ⇒ **不得标 `executed`**。

抄 final §7.6 并补本 AP 特有假绿：

- import / `which` / `GET /v1/models` 当 runtime ready
- Protocol fake / stub `complete` 当 L3
- root 或生产 `--no-sandbox`
- 云 OCR / 浮动 `latest`
- 测试后赋 port / monkeypatch `_browser_fetcher`
- NH1-T06 smoke 三次成功当本 AP DoD
- 503 / 诚实未部署当 in-scope 通道 live（NH7 的事）
- 正则 Tj / 字面量 PDF 当文本层引擎
- render 成功顶替 print；常量 `injected-browser-renderer.v1`
- 空 OCR / 空提取当 admitted clean
- 第四无名 DispatchPool 或把 unpooled 假装已在 generate 池
- 锁 Playwright/pypdf/tesseract/poppler 为 Truth
- 伪造 S16 已签
- Capstone E 未到 query 却宣称 NH7 完成
- pytest skip 当 PASS

---

## 11. 执行日志回填（仅 `executed` 状态使用）

> 执行者：`Grok`
> 执行时间：`2026-08-30`（evidence UTC `2026-08-30T00:01:17Z`）
> 文档状态：`draft → executing → executed`
> 代码改动统计：实现提交 `63c4398`（54 files；无新业务 migration）

- **实际执行摘要**：
  - Phase 1（`NH6-01`）：五类 supply identity（`pdf.parse` / `browser.render` / `browser.print_pdf` / `ocr.deterministic` / `s11.multimodal`）分账 cap/limit/readiness；库名不进 registry。
  - Phase 2（`NH6-02`）：`IsolatedPdfParser` 无网 subprocess；decode 权威从 `_extract_pdf_text` 撤到 parser；absent/encrypted 分码。
  - Phase 3（`NH6-03/04`）：共享 Firefox/geckodriver；S16 prefetch + 闭代理；render DOM 与 print `%PDF-` 独立预算；淘汰常量 profile。
  - Phase 4（`NH6-05/06`）：`MultimodalGenerateRequest` + adapter parts；确定性 OCR 无 PromptRef；CLI 仍拒 binary。
  - Phase 5（`NH6-07..10`）：具名闸满载零调用；`/ready` 正负与 models-list 不足；SBOM；`create_app()` 注入真实 port。
- **Phase 偏差（计划 vs 实际）**：
  - `NH6-V01 (substrate-fit)`：`runtime_supply_readiness_required` 默认 false，离线/既有测试 `/ready` 仍走 BASE 九项；T09 以 flag=true 证明生产供给门。
  - `NH6-V02 (capability literal)`：未新增 `InferenceCapability` vision/ocr 字面；multimodal 复用 `text_generate` binding，闸键为 `s11.multimodal`。
  - `NH6-V03 (browser network)`：页面不直连源 URL；S16 prefetch 后 `data:` 执行 + 出站代理 127.0.0.1:9。
  - `NH6-V04 (matrix digest)`：`pdf.ocr`/`doc.ocr` 去 PromptRef（T-O-386）；live closed-set digest 刷新为 `57c19c6…`；NH1 GO 结论不变。
  - `NH6-V05 (print ToUnicode)`：主机 CJK 默认字体把 ASCII `1` 抽成 U+FFFD；print 强制 DejaVu Latin 字体。
- **阻塞与处理**：无 NH6 hard-gate blocker。S16 签收栏已建且留空。五个 namespace/rebuild 失败保持 NH8 红债。
- **测试发现**：NH6 hard suite `45 passed`；全仓 `799 collected / 794 passed / 5 successor-owned failed`。
- **后续 handoff**：GO 供给 → `AP-NH7` 10+3 live（query 仍缺则 NH7 FAIL）；安全面 → `AP-NH9` 🔱 `test_new_harvest_runtime_security.py`。

### 11.1 逐工作项状态

| 工作项 | 状态 | PR / commit | 实际落点 | 备注 |
|--------|------|-------------|----------|------|
| `NH6-01` | `✅ done` | `63c4398` | `src/runtime/supply/identities.py`; config/health keys | five identities |
| `NH6-02` | `✅ done` | `63c4398` | `src/runtime/supply/pdf_parser.py`; decode in `acquisition_ingest.py` | isolated pdftotext |
| `NH6-03` | `✅ done` | `63c4398` | `src/runtime/supply/browser.py` render; `api/app.py` inject | SPA DOM |
| `NH6-04` | `✅ done` | `63c4398` | same runtime `print_pdf`; independent cap | `%PDF-` |
| `NH6-05` | `✅ done` | `63c4398` | `MultimodalGenerateRequest`; `local_vllm.multimodal_generate` | parts not string |
| `NH6-06` | `✅ done` | `63c4398` | `deterministic_ocr.py`; `intake` OCR 503 vs local port | no cloud/latest |
| `NH6-07` | `✅ done` | `63c4398` | `ConcurrencyGate` named caps; facade `gate_capability` | zero downstream |
| `NH6-08` | `✅ done` | `63c4398` | `HealthAggregator.SUPPLY_REQUIRED`; `_probe` | FG-NH-11 |
| `NH6-09` | `✅ done` | `63c4398` | `docs/evidence/new-harvest/AP-NH6/security/sbom-inventory.json` | no waiver |
| `NH6-10` | `✅ done` | `63c4398` | `create_container` inject parser/browser/ocr/clean_llm | no success monkeypatch |

### 11.2 关键指标演进

| 指标 | NH5 baseline | NH6 | Δ |
|------|--------------|-----|---|
| default-root parser/browser ports | smoke only | production inject | `wired` |
| S11 request | `input_text` only | multimodal sibling | `closed` |
| `/ready` supply components | 0 | 5 named | `+5` |
| NH6 hard gates | `0` | `45 passed` | `+45` |
| repository collected | 753 | 799 | `+46` |
| successor-owned failures | 5 | 5 | `unchanged` |

### 11.3 红灯 / successor-owned failures

| 项 | 证据 | 判断 |
|----|------|------|
| index namespace ×3 | same 422 `RETRIEVE_SCHEMA_NAMESPACE_REQUIRED` | `C handoff → NH8` |
| reactivate namespace ×1 | same 422 | `C handoff → NH8` |
| rebuild STRUCTURE_PROFILE_INVALID ×1 | metadata/rebuild still reclean | `C handoff → NH8` |

### 11.4 文档状态

`draft → executing → executed（2026-08-30）`。
residual / follow-up → `AP-NH7` live-to-query；`AP-NH8` namespace/rebuild；`AP-NH9` security mega。

---

## 附录 · 修订历史

| 版本 | 日期 | 作者 | 说明 |
|------|------|------|------|
| `v0.1` | `2026-08-29` | Grok workflow new-harvest-nh6-nh9-action-plans | 由 final §7.6 派生；状态 `draft` |
| `v0.2` | `2026-08-29` | Grok fix-fleet | 吸收已核实 review：`--no-sandbox` 重评=reopen Q19 不得经 SBOM waiver；T01 强制 `create_app` L3 node 且缺 binary FAIL；T07 加 L2 port/UoW，L1 不得单独 PASS；T06 fake transport 锁 L2；`security.py` 政策锚 `368-414`+`433-439`；⛔5 OCR 盗码 `155-159` |
| `v0.3` | `2026-08-29` | Grok recon-fix | `NH6-04` §3/§4.3 补独立 `path:line`（print cap/readiness keys）；T05 跑法改为具名四 node；T08 补 security L2 `::test_backpressure_zero_downstream`，unit 不得单独 PASS |
| `v1.0` | `2026-08-30` | Grok | 执行回填 §11；状态 `executed` |
