# new-harvest · Intake 四清洗通道构建 —— 初始构想（Initial Thoughts）

> **对象**：`after 0815-R7 live（NS1–NS9 波次收口后）→ new-harvest 相位`
> **日期**：`2026-08-29`
> **作者**：`GLM-5.3-Flash（Antigravity Pair Engineer，按业主 2026-08-29 指令起草）`
> **文档性质**：`eval/state-analysis × design 双模板联合输出`（外框为 `.adocs/templates/eval-state-analysis.md` 的状态对账脊，内芯为 `.adocs/templates/design.md` 的功能簇设计脊；两模板的共有脊——头部 / 性质声明 / TL;DR / 输入锚定 / 修订历史——合并于此）
> **文档状态**：`draft`
> **对照基线**：`README v1.2 @ d57a971`、`docs/closure/new-start/NS9-0815-R7-live-firing-closure.md`、`context/legacy-family/` 四仓现状
> **上游权威输入**：
> - [`NS9-0815-R7-live-firing-closure.md`](../closure/new-start/NS9-0815-R7-live-firing-closure.md)（R7 实弹 4/4 与两个内核修复）
> - [`context/legacy-family/`](../../../context/legacy-family/)（smind-admin / smind-clean-dispatcher / smind-skill-clean-universal / smind-skill-clean-dedicated-apis）
> - `src/contracts/intake/strategies.py`、`src/services/registry.py`、`src/workflows/lsrag_definition.py`、`src/runtime/intake/clean_preflight.py`、`intake/` 包全部源码
> **下游消费者**：`new-harvest action-plan`（待起草）、业主对 §B.9 QNA register 的拍板
> **业主原始四目标（本文的 scope 锚）**：
> 1. 按当前实现方式，完整、完全构建全部 4 个清洗通道 **[pdf, web, doc, api]**
> 2. 状态机等支持全面梳理，并与清洗通道真实接线
> 3. robust 的边缘场景处理、逻辑路由与错误处理
> 4. 全部 unit / e2e 测试工具，并参考 `.experiment/0815` 形成完整实验通路（**实验时间待定**）

---

## 0. 水位 / 健康一句话（TL;DR）

- **一句话现状**：MKB intake 的**合同面几乎完备、执行面只有一个半通道**——4 条来源通道（inline / local_object / http_resource / registered_api）全部有 frozen 合同、capability 清单、12 条 builtin workflow 与 11 步 durable 状态机；但真正能从字节走到 clean text 的只有 `clean.extract.deterministic`（text/HTML）与一个**用正则抠 PDF 字面量冒充文本层的** `clean.extract.pdf_text`；浏览器渲染、OCR、Vision、doc/pdf/web 三条 LLM 清洗通道全部停在"合同已落地 / runtime 未注入"，`api/app.py` 不注入 browser / OCR / vision / clean-LLM 任一运行时。
- **核心结论**：new-harvest 的真实工作量不是"写 4 个清洗器"，而是三件事——① 把 legacy-family 用血泪验证过的**清洗语义**（结构清洗、渲染、Vision、散射 ETL）搬到 MKB 已验证的**状态机底盘**上；② 补齐 legacy 与 MKB **共同的盲区**（charset、超时退避、加密/损坏文件预检、路由决策点）；③ 用 `.experiment/0815` 的 immutable-run 方法论把每条通道变成**可发车、可归因、可复跑**的实验单元。业主目标 2（状态机梳理与真实接线）是关键路径：D1/D3/D4 全部依赖它。

---

# 第一部分 · 当前状态评价（eval / state-analysis 脊）

## 1. 方法与对照基线

- **对照基线**：README v1.2（`d57a971`）声称的 intake 能力状态 + NS9 closure 的 live 证据。
- **证据来源**：全量源码精读（`intake/` 包 336 行 SSOT + `src/runtime/intake/` 9,951 行 + 合同/workflow/registry）；`context/legacy-family/` 四仓结构化梳理（另附 Explore 深查报告，关键结论已内联）；全量 pytest 基线（572 collected / 11 存量失败）。
- **可采信标准**：每个判定给出 文件:行号 锚点；"合同存在"与"runtime 可执行"分开评级，不允许用合同面冒充执行面。

## 2. 回看清单（交付快照）

### 2.1 交付价值台账（intake 清洗面逐单元评级）

| 单元 | 声称交付 | 真实落地（代码核） | 评级 | 锚点 |
|------|----------|--------------------|------|------|
| 来源合同 `DEFAULT_SOURCE_KINDS` | 4 来源通道 frozen | 合同、语义指纹、action 词表齐备 | **delivered** | `src/services/registry.py:170-203` |
| clean 策略注册表 | 10 策略 / 3 通道 | 注册表 + digest + fail-closed 解析齐备 | **delivered** | `src/contracts/intake/strategies.py:15-151` |
| 12 条 source-profile workflow | 每来源 profile 一条 frozen 工作流 | 静态绑定 clean process；revision 1–4 | **delivered（合同）** | `src/workflows/lsrag_definition.py:944-1060` |
| 11 步 durable 状态机 | acquire→…→validate_publication | claim/lease/fencing/retry/HITL/scatter/outbox 全落地，R7 实弹验证 | **delivered** | `src/runtime/workflow/`、`src/runtime/intake/core.py:377` |
| `clean.extract.deterministic` | text/JSON/HTML 确定性清洗 | 真实可用；HTML 保留段落换行（R7 live） | **delivered** | `intake/doc/__init__.py:18-39`、`intake/text.py` |
| `clean.extract.web`（静态） | HTML 结构清洗 | 真实可用：`HTMLParser` 封闭 tag/attr 策略 + 正文提取 | **delivered** | `intake/web/sanitize.py:12-50`、`intake/web/__init__.py:23-40` |
| `clean.extract.pdf_text` | PDF text-layer | **半占位**：`local-pdf-literal-text.v1` 用正则抠未压缩字面量；无 PDF 库、压缩流/CID 字体/ToUnicode 全部丢失，失败码还误用 `CLEAN_OCR_CAPABILITY_UNAVAILABLE` | **partial** | `src/runtime/intake/types.py:144-175` |
| `clean.extract.web_llm` / `pdf_llm` / `doc_llm` | LLM 清洗三分支 | 分发、prompt 冻结、CLI 通路在；**组合根不注入 clean-LLM**，local-inference 池直接 503 | **placeholder（合同）** | `intake/pdf/__init__.py:31-46`、`src/runtime/intake/clean_preflight.py:87-93,149-152` |
| `clean.ocr.local` | 本地 OCR | 只会报 `CLEAN_OCR_CAPABILITY_UNAVAILABLE` 的受控拒绝；decode 层对 image/* 故意产空文本 | **placeholder** | `intake/pdf/__init__.py:48-58`、`acquisition_ingest.py:620-629` |
| `clean.extract.vision` | 图像 Vision | 同上，受控拒绝 + `CLEAN_CAPABILITY_MISMATCH` 前置闸 | **placeholder** | `src/runtime/intake/clean_preflight.py:32-35` |
| `intake.acquire.http_browser` | 浏览器渲染获取 | state 会写 `browser_profile: injected-browser-renderer.v1`，但 `browser_fetcher` 端口恒为 None，**无任何渲染器存在** | **placeholder（合同）** | `acquisition_ingest.py:535-536`、`api/app.py:280`（未注入） |
| `clean.map.registered_api` | 3 provider 散射 ETL | chinatax/domain/realestate 契约+unpack+parse 齐备（调用方冻结输入） | **delivered（冻结输入）** | `intake/api/registry.py:16-40` |
| decode 层 canonicalizer | utf8-lf-nfc / JCS / magic 嗅探 | 真实可用；但 **HTML charset 纠正不在合同内** | **delivered（有缺口）** | `acquisition_ingest.py:636-646`、`types.py:174-209` |

### 2.2 Deferred / Carried-over 台账（每条带 reopen 触发器）

| 编号 | 项目 | 为什么 defer | reopen 触发器 | 携带至 |
|------|------|--------------|----------------|--------|
| D-01 | 浏览器渲染器 runtime（`http_browser` acquire 的真实实现） | 依赖选型未冻结（见 §B.9 Q2） | new-harvest W1 组合根接线 | new-harvest D2 |
| D-02 | clean-LLM 注入（`_clean_llm` 端口） | R4 之后 vLLM clean prompt 未定版 | promptA.clean 合同冻结 + 业主授权 | new-harvest D1/D2 |
| D-03 | 本地 OCR / Vision 模型绑定 | 需 VL 模型供给决策（容器现仅 Qwen3-VL-Embedding，无生成 VL） | §B.9 Q4 拍板 | new-harvest D1 |
| D-04 | 真实 PDF 解析库引入 | text-layer 半占位长期存在；库选型牵涉依赖策略 | §B.9 Q1 拍板 | new-harvest D1 |
| D-05 | HTML charset / 非 UTF-8 纠正 | decode 合同 `utf8-lf-nfc.v1` 未含 charset；改它动 decoded_digest→revision 指纹 | §B.9 Q5 拍板 | new-harvest D3 |
| D-06 | 11 个存量 e2e/intake 失败 | 属 R4 时代 harness 债（README §12.2 K1），与清洗通道改造耦合 | new-harvest W1 起顺手闭合 | new-harvest D4 |
| D-07 | Q 通道 megafile C 摘要耗时 / runner 按通道超时预算 | NS9 deferred ledger 遗留 | 后继 0815 波次 | new-harvest 之外 |

## 3. 对账诚实（本 flavor 灵魂段）

| 声称 | 真实 | 偏差类型 | 证据 | 影响 |
|------|------|----------|------|------|
| "PDF text-layer 确定性摄取 `已落地`" | 正则抠字面量只能处理**未压缩、简单字体**的 PDF；真实世界 PDF（FlateDecode 流、CID 字体）会走 `CLEAN_OCR_CAPABILITY_UNAVAILABLE` 拒绝 | **over-claim** | `src/runtime/intake/types.py:144-175` | R7 的 88 条向量全部来自 markdown/text 来源，PDF 通道从未被 live 证明过 |
| "OCR 清洗 `clean.ocr.local` 已注册" | 注册表/工作流/前置闸在，唯一实现是抛受控拒绝码 | **placeholder** | `intake/pdf/__init__.py:48-58` | local_object.image workflow 全链路只能产出稳定失败 |
| "browser_profile: injected-browser-renderer.v1" | 渲染器根本不存在，evidence 字段记录的是一个虚构 producer 名 | **fake-evidence 风险** | `acquisition_ingest.py:536` | 若不修，浏览器通道的审计证据从 day-1 就不诚实 |
| "失败码 `CLEAN_PDF_TEXT_LAYER_MISSING`" | 实际抛的是 `CLEAN_OCR_CAPABILITY_UNAVAILABLE`（语义：OCR 未配置），text-layer 缺失与 OCR 未配置是两种归因 | **错误码误用** | `types.py:158-162` | 上游无法按码路由降级策略 |
| "decode 合同 `utf8-lf-nfc.v1`" | 只对已正确解码的 `str` 做 NFC/LF 规范；**HTTP charset（gbk/gb2312/latin-1）从未被纠正**，`errors="replace"` 会静默产乱码 | **under-claim + 盲区** | `intake/web/__init__.py:21`（`decode("utf-8", errors="replace")`）、legacy 同盲区 | 中文 web 来源是本项目主粮，乱码会静默入库 |
| "10 策略注册表闭合" | 注册表闭合成立，但 10 策略中 6 个无 runtime | **合同≠done** | `strategies.py` × §2.1 | 合同面膨胀给了"能力很多"的错觉 |

- **诚实结论**：intake 清洗面的真实水位是"**1 个半通道 live、2 个通道合同完备待 runtime、1 个通道（PDF text-layer）以错误实现冒充已落地**"。README 对前三者的标注基本诚实，唯独 PDF text-layer 的 `已落地` 是 over-claim，必须在 new-harvest 里显式降级重做。

## 4. 归因 / 缺口分析

| 现象 | 归因（根源/缝/簇） | 根源位置 |
|------|---------------------|----------|
| PDF 文本层是正则假实现 | NS1 优先打通"能跑通的最短路径"，PDF 库依赖被推迟后没有记账进 deferred ledger | `types.py:144` |
| 6 个 clean 策略无 runtime 但 workflow 已注册 | 组合根（`create_app`）与 capability manifest 之间没有"部署事实探针"强制一致 | `api/app.py:280` vs `registry.py:176-202` |
| 渲染证据字段虚构 producer | evidence 字段是静态字符串拼接，没有从真实端口回填 | `acquisition_ingest.py:536` |
| charset 盲区两边同病 | legacy 无 TextDecoder 检测；MKB 沿用"HTTP 头说了算 + replace" | `intake/web/__init__.py:21` |
| R7 身份重放 FK 崩溃 | replay 决策点放在物化之后（NS9-FX2 已修）——**接线类 bug 的范式**：合同推进顺序与状态机物化顺序不一致 | `acceptance_snapshot.py`（已修 `d57a971`） |

## 5. Verdict（价值-债务 / 达成度 / 健康评级）

| 维度 | 评级 | 一句话 |
|------|------|--------|
| 交付价值（intake 清洗面） | ★★★☆☆ | 状态机底盘 + 合同面优秀，执行面单薄 |
| 累积债务 | ★★☆☆☆ | 6 策略无 runtime + 1 个假 text-layer + charset/超时盲区，全部有精确锚点、可排 DAG |
| 愿景/目标达成度 | ★★★☆☆ | "LS-RAG 全来源确定性摄取"只对 text/HTML/简单PDF 成立 |
| **综合健康** | ★★★☆☆ | 底盘可承载，水位真实但被合同面放大；new-harvest 是把水位做实的正确下一步 |

- **反镀金提醒**：不要在 clean 通道里新造第二套队列/调度（legacy 的 SMCP 层职责 MKB 状态机已覆盖）；不要为"支持 10 策略"而给每个策略都造 runtime——按业主四目标，PDF/Web/Doc/API 四通道的最小完整集优先，策略数可以少于注册表。

## 6. 前瞻交接

- **下一周期建议**：new-harvest 按 §B 的 D1–D4 执行，D2（状态机接线）先行两周做"组合根 + 部署事实探针 + 路由决策点"，随后 D1 四通道并行、D3 与各通道内联（不是独立尾段）、D4 从 W1 起与实现同速。
- **start-gate 前置（下一 charter day-1 必须满足）**：
  - §B.9 的 Q1–Q5 至少 Q1/Q2/Q3 拍板（它们决定 D1 的依赖与 D2 的路由形态）；
  - README 中 PDF text-layer 的 `已落地` 降级为 `partial（待重建）`，作为对账锚；
  - 存量 11 失败里与 intake 相关的 6 项纳入 D4 的首波回归基线。
- **需 owner 拍板的问题**：见 §B.9 QNA register。

---

# 第二部分 · new-harvest 功能簇设计（design 脊）

## B.0 背景与前置约束

- **项目定位回顾**：MKB 是内部 LS-RAG 服务：摄取 → 分层结构化 → 双通道向量 → 有栅栏检索；intake 是全部知识的唯一入口。
- **本次讨论的前置共识（继承冻结结论）**：
  - `intake/` 包是清洗变换 SSOT，runtime 只做 claim/fence/commit（`intake/__init__.py:1-6`）；
  - clean 策略注册表闭合、显式路由、无 payload 嗅探隐式路由（与 legacy v5.3.0 的"废弃 payload 嗅探"决策一致）；
  - fail-closed 纪律：清洗产出不可 admissible 即 `CLEAN_EMPTY` 终局，不做静默降级（R5–R9 一贯纪律）；
  - 状态机不动核心：NS1–NS9 冻结的 claim/lease/fencing/retry/HITL/revision 语义指纹是已验证资产，本设计**只接线、不重构**。
- **本设计必须回答的问题**：四通道各自的真实实现选型与依赖；路由决策点放在哪一层；组合根注入哪些 runtime；边缘场景的错误码/降级合同；实验通路如何复用 0815 方法论。
- **显式排除的讨论范围**：generation/structurize/construct/vectorize 各步内部逻辑（已 live）；检索面；前端；部署清单。

## B.1 讨论对象

### B.1.1 功能簇定义

- **名称**：`new-harvest · intake 四清洗通道`
- **一句话定义**：把 PDF / Web / DOC / API 四条来源通道从"合同完备、runtime 缺位"推进到"端到端 live 可验证"，包括真实解析实现、状态机真实接线、robust 边缘处理与实验通路。
- **边界描述**：**包含** acquire/decode/clean 三步的通道实现与 runtime 注入、clean 策略路由决策、错误码与降级合同、通道级测试与实验 run 家族；**不包含** 结构化生成（promptB/cuts）、向量化、检索、前端、生产部署。
- **关键术语对齐**：

| 术语 | 定义 | 备注 |
|------|------|------|
| 来源通道（channel） | `pdf / web / doc / api` 四条字节→clean text 的路径 | 对齐业主四目标 |
| clean 策略（strategy） | `CleanStrategyKey` 注册表中的一个冻结定义 | 10 个，含通道×模式矩阵 |
| 接线（wiring） | 组合根把真实 runtime 端口注入 `create_app`，使注册策略可执行 | 区别于"合同已落地" |
| 部署事实探针 | readiness/manifest 中对"该 clean 能力在本进程有 runtime"的显式布尔 | 防合同面冒充执行面 |
| 路由决策点 | 决定"这份字节走哪条 clean 策略"的时刻与依据 | 本设计的核心架构选择，见 §B.3.4 |
| 降级（downgrade） | 显式、有 evidence、可配置的策略替换（如 text-layer 缺失 → OCR） | 区别于静默 fallback |
| 实验 run 家族 | `.experiment/` 下 immutable-run + preflight + journal 的可发车单元 | 复用 0815 方法论 |

### B.1.2 参考调查报告

- `context/legacy-family/` 深查（本文 §B.4 内联关键结论）；
- `docs/eval/new-start/`（NS1–NS9 的 live 证据与 R7 归因方法）。

## B.2 在 MKB 中的定位

### B.2.1 角色

- intake 清洗通道是**唯一知识入口的执行层**：服务于 Task 调用方（public API）、durable 状态机（worker）、下游 generation plane。
- 依赖：`HttpAcquirer`（egress 策略/预算）、decode canonicalizer、clean 策略注册表、prompt 冻结面、推理 facade（LLM clean）、将要注入的 browser/OCR/vision runtime。
- 被依赖：`clean_preflight` → `seal_candidate_set` → structurize（cuts 组装要求 clean 原文纯净，见 R7 不变量"切片 body 严格从 clean_text 截取"）。

### B.2.2 交互矩阵

| 相邻功能簇 | 交互方向 | 耦合强度 | 说明 |
|------------|----------|----------|------|
| durable 状态机 | 被（状态机调用 clean 步骤） | 强 | clean 步骤是 11 步流程的第 3 步；dispatch pool 决定 LLM 通路 |
| 合同层（strategies/registry） | 依赖 | 强 | 策略定义 digest 进 evidence；加策略=改合同=需要版本纪律 |
| 推理 facade | 依赖 | 中 | LLM 清洗与 CLI 清洗共用冻结 prompt 面（`promptA.clean.v1`） |
| generation plane | 上游供给 | 强 | clean 原文纯净性是 cuts 组装的 0-drift 不变量 |
| 对象 CAS | 依赖 | 中 | raw/clean artifact 双写；R2 教训：CAS/DB 一致性必须保 fail-closed |
| HITL gate | 被依赖 | 弱 | `require_human_review` 的来源之一是清洗结果可疑（预览图/极短文本） |

### B.2.3 一句话定位陈述

> "在 MKB 里，new-harvest 清洗通道簇是**知识入口的执行层**，负责**把四类来源字节变成可 admissible 的 clean text 及其证据链**，对上游提供**每来源 profile 的 frozen workflow 与能力清单**，对下游要求**clean 原文纯净、证据可回溯、失败必须类型化且可归因**。"

## B.3 架构稳定性与未来扩展策略

### B.3.1 精简点（哪里可以砍）

| 被砍项 | 参考来源 / 诱因 | 砍的理由 | 重评条件 |
|--------|------------------|----------|----------|
| legacy 的独立编排层（dispatcher 队列 + SMCP 消息 + Restarter RPC） | `smind-clean-dispatcher/` | MKB durable 状态机已覆盖其全部职责且更强（fencing/lease/outbox） | never（除非拆微服务） |
| `WEB_BROWSER_PRINT_PDF` 策略的第一版 | strategies.py:67-77 | 依赖浏览器渲染器 + LLM 双 runtime，是四通道里最贵路径；先保 `rendered→web_llm` | 浏览器通道 live 且有真实 print-pdf 需求 |
| legacy 的 `atomic_bundle` prefix 型 slot + `summary.jsonl` 双写 | chinatax processor.ts:229-239 | MKB 的 intake member/child-file 契约与 outbox 已覆盖散射产物记账 | 散射 ETL 出现 MKB 侧消费瓶颈 |
| payload 嗅探类"聪明"路由 | legacy v5.3.0 废弃决定 + MKB `dispatch_clean` 现状 | 显式路由是两边用事故换来的共识 | never |

### B.3.2 接口保留点（哪里要留扩展空间）

| 扩展点 | 表现形式 | 第一版行为 | 演进方向 |
|--------|----------|------------|----------|
| `CleanLanguageModel` 端口 | `intake/types.py`（complete(prompt, text/blob, media_type)） | CLI（non-interactive）+ local-vLLM（local-inference）双实现 | 加结构化输出模式（对齐 R7 的 cuts schema 经验） |
| `BrowserFetch` / `HttpFetch` 端口 | `intake/web/__init__.py:11-25` | 真实渲染器实现此端口注入 | headless 池、渲染缓存 |
| OCR / Vision 端口 | 新增，形态对齐 `CleanLanguageModel` | 本地 VL 模型或 CLI | 模型可换、按页分片 |
| clean 策略注册表 | `strategies.py` 定义元组 | 新增策略=追加定义+digest 变更 | 策略版本并存（revision 指纹已隔离） |
| provider 注册表 | `intake/api/registry.py` | 3 provider 冻结输入 | 实时客户端模式（显式新 intent，不静默改语义） |

### B.3.3 完全解耦点

- **解耦对象**：清洗实现与状态机。clean 步骤只经 `dispatch_clean` 消费字节与端口，永不直接触碰 DB/流程状态（现状已如此，必须保持）。
- **解耦原因**：R7 的 FK 事故证明"合同推进顺序"与"物化顺序"错位是接线期最大风险源；清洗实现越纯粹，越容易测试与替换。
- **依赖边界**：`intake/` 包不 import `src/runtime/workflow/`；错误只以 `MkbError` 码面上升。

### B.3.4 聚合点（核心架构选择：路由决策点）

**取舍：选择"decode 后的单一路由决策点 + 静态 profile 兜底"而不是"纯静态 per-profile workflow"或"全动态路由"。**

- **现状事实**：12 条 builtin workflow 把 acquire/decode/clean **静态绑定**（`lsrag_definition.py:944-1060`），选错 profile 就得走错清洗器；同时 `dispatch_clean` 内部又按 media_type 做了第二层隐式纠偏（PDF 不被当 HTML 清洗，`intake/__init__.py:80-86`）。两层并存且语义有重叠。
- **建议形态**：保留来源 profile workflow（调用方显式选择，符合"显式路由"共识），但把"策略降级/升级"收敛为一个**显式的 route 决策步骤**（decode 之后、clean 之前）：输入 media_type + magic 嗅探 + text-layer 水位 + representation_kind，输出冻结的 strategy key + 决策证据；低水位 text-layer PDF 在此显式降级到 OCR（而不是像现在这样抛一个错误码误用的拒绝）。
- **为什么不能分散**：R7 经验——路由决策散落在 handler 的 if 链里（`clean_preflight.py:59-72`、`dispatch_clean`、`clean_pdf` 内部三处）导致 evidence 难对账、降级路径不可审计。
- **代价**：新增一个决策过程 = workflow 定义演进（revision +1）+ 状态机过程数 +1；需在 D2 中按 NS 系列的 workflow revision 兼容纪律落地。

## B.4 参考实现对比：legacy-family 四通道 vs MKB 现状

### B.4.1 PDF 通道

| 维度 | legacy（smind-skill-clean-universal） | MKB 现状 | new-harvest 倾向 |
|------|------|------|------|
| 主路径 | Gemini Vision 全量多模态提取（`cleaner_doc.ts:111-129`，20MB 前置拦截 :74-82） | 正则字面量 text-layer（假实现）+ 未接线的 LLM/OCR | **真 text-layer 库为主、Vision/OCR 为显式降级** |
| 扫描件 | 天然适配（Vision） | 直接拒绝 | text-layer 水位探测 → 显式降级 OCR/Vision |
| 加密/损坏 | 无预检，表现为 `AI_RESPONSE_INVALID` | 有 `%PDF-` 签名检查 | 预检升级：加密标志/损坏流 → 专属错误码 |
| 去噪（页眉页脚/页码） | prompt 承担（不可见） | 无 | text-layer 后处理规则化（确定性优先） |

### B.4.2 Web 通道

| 维度 | legacy | MKB 现状 | new-harvest 倾向 |
|------|------|------|------|
| 静态清洗 | HTMLRewriter 流式 + 封闭清单（`sanitizer.ts:33-42`） | Python HTMLParser **同款清单**（`sanitize.py:10-12`，直接继承遗产） | 保持，补 charset |
| 动态渲染 | Cloudflare Browser Rendering API 两分支（`cleaner_web.ts:99-134`） | 端口在、渲染器不存在 | 注入真实渲染器（Q2），evidence 回填真实 producer |
| AI 重写 | `WEB_CONTENT_CLEANUP_V1` prompt 分支 | `web_llm` 合同在、无注入 | 与 D2 一起接线；prompt 冻结面已备 |
| charset | **盲区**（无 TextDecoder 检测） | **同盲区**（`errors="replace"`） | HTTP 头→meta→嗅探三级纠正（Q5，进 decode 合同） |
| 超时/重定向/UA | 无 timeout；UA 伪装；非 200 一律 `URL_FETCH_FAILED` | EgressPolicy/预算在；`CLEAN_WEB_FETCH_INVALID` 体系更细 | 保留 MKB 体系，补显式 timeout 与重定向上限证据 |

### B.4.3 DOC 通道

| 维度 | legacy | MKB 现状 | new-harvest 倾向 |
|------|------|------|------|
| docx 解析 | **不存在**（全靠 Gemini prompt） | `clean.extract.doc_llm` 合同在、无注入 | 第一版：真实 docx 确定性解析（标题/段落/表格线性化）优先于 LLM；LLM 作降级 |
| 图片/Vision | Vision 天然覆盖 | 受控拒绝 | 绑定本地 VL（Q4）或首版继续受控拒绝并如实标注 |

### B.4.4 API 通道

| 维度 | legacy | MKB 现状 | new-harvest 倾向 |
|------|------|------|------|
| 契约 | zod 双向安检 + 字段重命名 + `unknown` 兜底 | Pydantic 严格契约 + fail-closed registry | 保持 MKB |
| 散射 | atomic_bundle + 双哈希（body/meta 分离）+ summary.jsonl | intake member + outbox（调用方冻结输入） | 保持；实时客户端作为显式新 intent 另立 |
| 空结果 | warn 或优雅 `empty_response` | 契约级处理 | 统一为类型化 `CLEAN_API_EMPTY_RESULT` + HITL 可选 |
| 限流/退避 | 定义了 `API_RATE_LIMITED` 但**无退避实现**；靠 key 轮询 + WAF 代理 | MKB 有 retry 状态机，通道内退避未定义 | provider 内显式退避 + 复用 worker retry 分类 |

### B.4.5 错误处理范式对比速查

| 维度 | legacy | MKB | 结论 |
|------|--------|-----|------|
| 错误码 | 三仓 43 个码，**2 个定义未用**、1 个响应形状不一致（universal vs dedicated 的 `CleanerResult`） | `MkbError` 单一体系，码面集中在 intake 层 | MKB 优；new-harvest 做一次**错误码审计**（定义未用/误用清零，R7 的 `CLEAN_OCR_CAPABILITY_UNAVAILABLE` 误用即先例） |
| 可重试 vs 终局 | 队列层几乎全部 ack 终局，重试靠人工 Restarter（MAX_RETRIES=5 + 30 分钟僵尸补偿） | worker retry policy 显式（max_retries/last_failure_retryability/backoff） | MKB 优；通道错误码须标注 retryability 分类 |
| 兜底 | 三级 catch + 失败回调尽力恢复 | `logger.exception`（NS9 补上）+ 类型化 outcome | 已对齐，保持 |
| 幂等 | confirm 幂等、非 pending 不重复入队 | intake identity replay（NS9-FX2 后指针解析） | 已对齐且更强 |

## B.5 In-Scope / Out-of-Scope

### B.5.1 In-Scope

- **[S1] PDF 通道重建** — 现有 text-layer 是假实现（§3 over-claim），必须真做：库解析 + 去噪 + 水位探测 + 显式降级。
- **[S2] Web 通道补全** — charset 纠正、浏览器渲染器注入、evidence 真实化、`web_llm` 接线。
- **[S3] DOC 通道建立** — docx 确定性解析（新能力面）+ `doc_llm` 接线 + image 通道的诚实处置（OCR/Vision 或显式不可用）。
- **[S4] API 通道加固** — provider 契约审计、空结果/限流退避类型化、散射 evidence 对账。
- **[S5] 状态机真实接线（D2 核心）** — 组合根注入四类 runtime；部署事实探针；路由决策点（§B.3.4）；workflow revision 演进。
- **[S6] 边缘场景与错误处理合同（D3）** — 错误码审计、retryability 分类、降级 evidence 规范、legacy 盲区清单逐项闭合或显式接受。
- **[S7] 实验通路（D4）** — fixture 语料库 + 通道级 unit/e2e + `.experiment/<date>-harvest/` run 家族（preflight/frozen cells/journal/attribution），**实验时间待定**，先具备可发车性。

### B.5.2 Out-of-Scope

- **[O1] generation plane 任何改动** — R7 已 live；重评条件：clean 输出合同变化导致 cuts 组装不兼容。
- **[O2] 实时 API 客户端** — 保持调用方冻结输入；重评条件：业主提出实时 provider 需求。
- **[O3] 生产部署/前端** — 与本簇无耦合；重评条件：另有 charter。
- **[O4] 存量 11 失败的全量清零** — 只闭合 intake 相关 6 项；检索/scatter 的 harness 债另有账（K1）。

### B.5.3 灰色地带

| 项目 | 判定 | 理由 | 后续落点 |
|------|------|------|----------|
| `WEB_BROWSER_PRINT_PDF` 策略 | defer | 双 runtime 依赖最贵 | §B.3.1，浏览器通道 live 后重评 |
| OCR/Vision 模型绑定 | in-scope（合同+端口）但模型供给 defer | 依赖 Q4 拍板 | D2 接端口，D1 后段接模型 |
| HTML charset 纠正是否改 decode 合同 | in-scope，但需 Q5 | 动 `decoded_digest` → revision 指纹语义 | Q5 拍板后进 decode canonicalizer v2 |
| DOC 确定性解析是否新增 strategy key | in-scope | 现注册表 doc 通道无非 LLM 确定性项（`doc.deterministic` 实际映射到通用 deterministic） | D1 内补注册表定义 |

## B.6 Tradeoff 辩证分析

1. **取舍 1：选择"真 text-layer 为主 + 显式降级"而不是"全 Vision"**
   - **为什么**：legacy 全 Vision 的代价是每页 AI token + 输出不确定性（temperature 0.8）；MKB 的 fail-closed 纪律要求 clean text 可回溯、可重放，确定性提取是一等公民。
   - **接受的代价**：需要引入并维护 PDF 解析依赖；扫描件走第二跳（降级链）。
   - **重评条件**：扫描件占比显著高于文本层 PDF 时。
2. **取舍 2：选择"decode 后单一路由决策点"而不是"全静态 workflow 绑定"**
   - **为什么**：PDF 的 text-layer 有无只有 decode 后才知道；静态绑定迫使调用方预知文件内部形态（不现实）或逼出隐式纠偏（现状）。
   - **接受的代价**：workflow revision +1、状态机多一个显式过程。
   - **重评条件**：never（这是把现状的隐式三层路由显式化的收敛，不是扩张）。
3. **取舍 3：选择"evidence 真实化"而不是"兼容现有虚构 producer 字符串"**
   - **为什么**：`browser_profile: injected-browser-renderer.v1` 在无渲染器时是假证据；R7 的教训是证据面必须诚实（fake-green 纪律）。
   - **接受的代价**：`http_browser` 在渲染器注入前必须显式 `CAPABILITY_NOT_DEPLOYED`，而不是伪成功。
   - **重评条件**：never。
4. **取舍 4：选择"先接线（D2）后并行铺通道（D1）"而不是"四通道齐头并进"**
   - **为什么**：Q-A5 的五次尝试证明，接线层的失败（FK、路由、证据）比清洗逻辑本身更难归因；先把组合根/探针/决策点立住，后面每条通道的失败都会是通道自己的失败。
   - **接受的代价**：D1 前两周进展体感慢。
   - **重评条件**：never。

### 风险与缓解

| 风险 | 触发条件 | 影响 | 缓解 |
|------|----------|------|------|
| PDF 库引入带来原生依赖/许可问题 | Q1 选型含 poppler 类 | 部署复杂化 | 纯 Python 库优先（pdfminer.six / pypdf），基准测试决定 |
| charset 纠正改变 revision 指纹 | Q5 通过 | 历史指纹不可比 | canonicalizer 版本 v2 与指纹版本字段化 |
| LLM 清洗输出不确定破坏 clean 纯净性 | web_llm/pdf_llm 接线后 | cuts 锚点失败率上升 | 沿用 R7 fail-closed + 采样温度约束 + evidence 记录 producer/温度 |
| 路由决策点与现有隐式纠偏双轨 | D2 实施期 | 行为漂移 | 决策点上线的同一 commit 删除 `dispatch_clean` 内的 media_type 隐式分支 |
| 存量 11 失败与新测试混淆水位 | D4 首波 | 假绿/假红 | 先固化基线清单（哪 11 个），修复计数以基线差分呈现 |

## B.7 In-Scope 功能详细列表

| 编号 | 功能名 | 描述 | 一句话收口目标 |
|------|--------|------|----------------|
| F1 | PDF 通道重建 | 真 PDF 库 text-layer + 去噪 + 水位探测 + 显式降级 OCR/Vision + 加密/损坏预检 | ✅ 加密/扫描/压缩流三类 PDF 各有类型化结局，文本层 PDF live 入库 |
| F2 | Web 通道补全 | charset 三级纠正、渲染器注入、`web_llm` 接线、fetch evidence 真实化 | ✅ gbk 页面、SPA 页面、LLM 重写三条路径各有 live 证据 |
| F3 | DOC 通道建立 | docx 确定性解析（标题/表格线性化）+ `doc_llm` 接线 + image 通道诚实处置 | ✅ docx→clean text live；image 来源结局类型化且 evidence 诚实 |
| F4 | API 通道加固 | 契约审计、空结果/限流类型化、退避、散射 evidence 对账 | ✅ 3 provider 全量 fixture 回归 + 空结果/429 路径有类型化结局 |
| F5 | 状态机接线 | 组合根注入 browser/LLM/OCR/Vision runtime；部署事实探针；路由决策点过程；workflow revision 演进 | ✅ `/ready` 对 10 策略逐一给出"部署/未部署"真实布尔；R7 回归不破 |
| F6 | 边缘场景合同 | 错误码审计清零、retryability 标注、降级 evidence 规范、legacy 盲区清单逐项闭合 | ✅ 每个错误码有消费者；每个盲区项"闭合/显式接受"二选一 |
| F7 | 实验通路 | fixture 语料库 + 通道 unit/e2e + `.experiment` run 家族（preflight/journal/attribution） | ✅ 任一通道可一键发车出记分（实验时间待业主定） |

### F5（关键路径）详述

- **输入**：`create_app(settings)` 的 Settings；现有端口（`browser_fetcher`、`_clean_llm`、OCR/Vision 新端口）。
- **输出**：注入完整 runtime 的组合根 + `/ready` 部署事实 + 路由决策过程。
- **核心逻辑**：Settings 增加每类 runtime 的 enable/endpoint 配置；未启用的能力在 manifest 标 `not_deployed` 且对应 workflow 在 admission 时显式拒绝（`CAPABILITY_NOT_DEPLOYED`），替代现在的"跑到一半 503"。
- **边界情况**：runtime 中途失联（probe 翻转）→ 现有 lease/recovery 机制接管，clean 步骤按 retryability 重试或终局。
- **一句话收口目标**：✅ **`local_object.image` 等 placeholder workflow 在未部署 runtime 时于 admission 即被诚实拒绝；部署后端到端成功**。

### F7（实验通路）详述

- **输入**：每通道 fixture 语料（正常/边缘各若干，含 legacy 盲区重现样本：gbk HTML、加密 PDF、扫描件、超大 docx、空 API 结果、429 响应）。
- **输出**：`.experiment/<date>-harvest/runs/NH-R1/` 形态的 immutable run（preflight gates、frozen cells、`runs.jsonl`、attribution 报告）。
- **核心逻辑**：完全复用 0815 方法论——R1 封条、preflight 必须全绿才可发车、journal 只追加、失败先归因后修复（NS9-FX1/FX2 即范式）。
- **边界情况**：live 推理依赖（vLLM/CLI）不可用 → preflight 跳过为 code-phase 并如实标注（现有 `skipped (code-phase)` 先例）。
- **一句话收口目标**：✅ **业主定日期后，`preflight.py` READY 即可发车，产出与 0815 同构的记分与归因链**。

### 非功能性要求

- **性能**：PDF text-layer ≥ 1MB/s/核量级（基准测试定标）；Web 渲染单页 ≤ 30s 预算。
- **可观测**：每通道每次清洗产出 evidence（strategy digest、producer、输入 digest、降级链）。
- **稳定**：错误码审计清零；retryability 显式；worker retry 分类对齐。
- **安全**：沿用 EgressPolicy/SSRF 栅栏；浏览器渲染属新增 egress 面，需同策略约束；**legacy wrangler.toml 明文密钥视为已泄露，绝不搬运**。
- **测试**：每通道 unit（含边缘 fixture）+ e2e（真实 Task 流转）+ 实验 run；全量基线差分报告。

## B.8 可借鉴的代码位置清单

### 来自 legacy-family

| 位置 | 内容 | 借鉴点 |
|------|------|--------|
| `smind-skill-clean-universal/core/sanitizer.ts:33-42` | 封闭 tag/attr 清单（含 colspan/rowspan 保表格） | 已被 `intake/web/sanitize.py` 继承，作为语义基准对照 |
| `smind-skill-clean-universal/services/cleaner_doc.ts:74-93` | 20MB 前置 + 读后二次校验（流式 size 缺失场景） | 双重校验范式 |
| `smind-skill-clean-dedicated-apis/providers/chinatax/processor.ts:150-163` | 单条失败仅跳过 + 文件名非法字符清洗 | 散射部分失败语义 |
| `smind-skill-clean-dispatcher/services/restarter.ts:177-231` | 30 分钟僵尸步骤扫描 | 对比 MKB lease/recovery，确认无需搬运 |
| `smind-skill-clean-dedicated-apis/core/errors.ts:31-69` | 错误码带 HTTP status hint | retryability 标注的参考形态 |

### 本仓库 precedent / 反例

| 位置 | 内容 | 借鉴/避开 |
|------|------|-----------|
| `src/runtime/intake/types.py:144-175` | 正则假 text-layer | **反例**：重建对象，保留其 `%PDF-` 签名预检思想 |
| `src/runtime/intake/acquisition_ingest.py:536` | 虚构 `browser_profile` producer | **反例**：evidence 必须来自真实端口 |
| `src/runtime/intake/acceptance_snapshot.py`（NS9-FX2 修复） | 物化顺序 vs 决策顺序 | 接线纪律：决策先于物化 |
| `.experiment/0815/runs/MKB-0815-R7/` | preflight/journal/attribution 全套 | 实验通路直接模板 |

## B.9 QNA / 决策登记

| Q ID | 问题 | 影响范围 | 当前建议 | 状态 |
|------|------|----------|----------|------|
| Q1 | PDF 解析库选型（pdfminer.six / pypdf / poppler CLI） | D1-F1、依赖策略 | pdfminer.six（纯 Python、布局感知）先行，基准不达标再评 poppler | open |
| Q2 | 浏览器渲染器实现（Playwright-Chromium 注入 / 容器内既有渲染服务复用） | D2-F5、D1-F2 | 先探明容器内 670 代理与既有渲染设施可复用性，再定 | open |
| Q3 | 路由决策点是否采纳（新增显式 route 过程 + workflow revision 演进） | D2 状态机改动量 | 采纳（§B.3.4） | open |
| Q4 | OCR/Vision 模型供给（本地 VL 生成模型 / 首版维持受控拒绝） | D1-F3 范围 | 端口先行，模型按业主 GPU 预算另批 | open |
| Q5 | charset 纠正进 decode 合同 v2（改 revision 指纹语义） | D3、历史指纹可比性 | 采纳，canonicalizer 版本字段化 | open |

### 设计完成标准（进入 frozen 前）

1. Q1/Q2/Q3 有业主答复或书面默认；
2. §2.1 台账中所有 `partial/placeholder` 行都有对应的 F1–F5 收口目标；
3. README PDF text-layer 的 over-claim 降级已合入。

## B.10 综述与 Value Verdict

### 功能簇画像

new-harvest 将把 MKB intake 从"合同面完备、执行面单薄"推进到"四通道端到端 live"。复杂度不在清洗逻辑本身（legacy 已给出大部分语义答案），而在**接线纪律**：路由决策点显式化、证据真实化、错误码闭环、runtime 部署事实与合同面对齐。状态机底盘（NS1–NS9 已 live 验证）无需重构，是本簇最大的既有资产。

| 评估维度 | 评级 | 说明 |
|----------|------|------|
| 对 MKB 核心定位贴合度 | 5/5 | 摄取是知识入口，四通道是"全来源确定性摄取"愿景的直接兑现 |
| 第一版性价比 | 4/5 | legacy 语义答案 + MKB 底盘现成，主要成本在接线与测试面 |
| 对后继演进的杠杆 | 5/5 | 路由决策点与部署事实探针是所有未来来源类型的基础设施 |
| 日用友好度 | 4/5 | 真实 PDF/docx 入库是业主日常最高频诉求 |
| 风险可控程度 | 4/5 | 风险集中在 Q1/Q2 选型与 revision 演进，均有明确缓解 |
| **综合价值** | **4.5/5** | 建议以本设计为纲起草 action-plan；start-gate 见 §6 |

---

## 附录

### A. 复现命令

```bash
# 当前水位复核
grep -n "local-pdf-literal-text" src/runtime/intake/types.py          # 假 text-layer
grep -n "browser_fetcher" api/app.py                                   # 组合根未注入
grep -n "CLEAN_OCR_CAPABILITY_UNAVAILABLE" src/runtime/intake/types.py # 错误码误用
sed -n '170,203p' src/services/registry.py                             # 4 来源通道合同
sed -n '940,1060p' src/workflows/lsrag_definition.py                   # 12 条 profile workflow
.venv/bin/pytest tests/ -q                                             # 572 collected / 11 存量失败
.venv/bin/python .experiment/0815/runs/MKB-0815-R7/preflight.py        # R7 状态（live-complete 后仍应 READY）
# legacy 对照
ls context/legacy-family/
```

### B. 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-08-29 | GLM-5.3-Flash | 初稿：状态对账（§1–6）+ new-harvest 设计（§B.0–B.10）+ QNA Q1–Q5 |
