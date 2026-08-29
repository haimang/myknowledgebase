# new-harvest · Intake 四域清洗通道 — 现状对账与功能簇设计

> **结构来源(dogfood)**：`eval-state-analysis`（对账诚实 / 交付快照 / deferred / 前瞻交接）+ `design`（功能簇边界 / 架构稳定性 / In-Out / Tradeoff / 功能详列 / QNA）
>
> **功能簇**：`new-harvest`（Intake 四域清洗通道完整接线：`intake/{pdf,web,doc,api}`）
> **对象**：`after NS9 / 0815-R7 live-verified（HEAD `196ce62`）→ 转向 intake harvest`
> **日期**：`2026-08-29`
> **作者**：`Grok`（panel：none）
> **讨论者**：`Grok`（本会话；业主尚未裁决）
> **文档性质**：`eval / state-analysis` + `design prelude`（现状快照 + 功能簇设计草案；**不是** closure / verdict / charter / action-plan；**冻结零决策**）
> **文档状态**：`draft`
> **对照基线**：`S05-v1.1` · `D08-v0.1` · `S04-v1.2` · `D01`/`S03` · README 2026-08-28 @ `d57a971` 能力表 · HEAD `196ce62`
> **关联调查 / 权威输入**：
> - `docs/baseline/domain-truth/S05-intake-cleaning.md`（四类 source、三轴 binding、preflight/gate）
> - `docs/baseline/domain-truth/D08-legacy-capabilities-migration.md`（legacy 四域闭集与 `intake/` 树）
> - `docs/baseline/domain-truth/S04-intake-asset-lifecycle.md`（五类 Intake identity）
> - `docs/closure/new-start/NS9-0815-R7-live-firing-closure.md`（上一战役 live 收口）
> - `docs/closure/new-start/deferred-items-ledger.md`（`NS5-VF97` / `NS6-VF97` browser/OCR/Vision）
> - `context/legacy-family/smind-skill-clean-universal/**`、`smind-skill-clean-dedicated-apis/**`、`smind-clean-dispatcher/**`（ReferenceAnchor only）
> - `.experiment/0815/`（实验族形态参考，**不是**本阶段 live 发车令）
> **关联 QNA / 决策登记**：尚无 `new-harvest-qna.md`；本文件 §D.9 只列 OPEN，不自冻
> **下游消费者**：后续 `pre-initial-planning-qna` / `planning-initial` / `docs/plan/new-harvest/`（均未写）

> **本文不改写**：S03 状态机权威、S04 十表 identity、S05 四类 source kind、D08 吸收/删除裁决、NS1–NS9 closure、0815 R1–R7 分析。legacy-family 禁止 runtime import（`T-O-42` / `S05-T003`）。

---

## 0. 水位 / 健康一句话（TL;DR）

- **一句话现状**：四域清洗 **不是空目录**——`intake/{web,pdf,doc,api}` 已有策略表、parser、消毒器、`dispatch_clean` 与 fail-closed 码；默认组合根 **只接线了确定性路径**（inline/HTML/PDF text-layer/caller-frozen API），browser / OCR / Vision / 文档·网页 LLM 仍是「合同已落地 / 运行时未注入」。
- **核心结论**：new-harvest 不该再开第五套 source taxonomy，也不该把 Cloudflare Workers 栈搬回来。它应沿着 **已经选对的三轴**（`source_kind × acquire_capability × clean_strategy`）把四域从「能拒绝」补成「能收获」：本地注入真实端口、把边缘路由与错误码做成闭集、把 unit/per-domain/e2e 接到一条 **0815 形态的实验族**（发车时间业主另定）。上一战役（NS1–NS9 / 0815-R7）证明的是 **LS-RAG 生成与 quoted cuts**；本战役要证明的是 **源怎么变成可接受的 clean Artifact**。

---

# A. 现状对账（eval-state-analysis）

## A.1 方法与对照基线

- **对照基线**：S05-T001「不得因实现缺口删减」的能力面；D08-T001..T011 的吸收/删除与测试 HARD；README §1.1 / §6 的状态词；D08 Appendix A（2026-08-13 实现见证，**不是**今日验收豁免）。
- **证据来源**：HEAD 源码（`intake/**`、`src/runtime/intake/**`、`src/workflows/lsrag_definition.py`、`api/app.py`）、`tests/intake/**`、`tests/e2e/test_source_capability_paths.py`、legacy `action_registry.ts` / `cleaner_web.ts` / `cleaner_doc.ts` / 三套 provider processor。未在本会话重跑全量 pytest。
- **可采信证据**：`file:line` + 现存测试名。D08 Appendix A 的「全量 pytest 绿」以当时 worktree 为准，**不得**覆盖 README 当前 `561 passed / 11 failed`。
- **复现入口**：见附录 A。

### A.1.1 上一战役留下什么、没留下什么

| 已关闭（生成面） | 对 harvest 的含义 |
|---|---|
| NS1–NS3 生产链、三池、叶服务抽出 | harvest 继续走同一 Process/dispatch 骨架，不另起 worker |
| NS4 一等证据面 + Turso 硬切 | clean 失败必须进 stage-report / typed `error_code`，禁止 silent skip |
| NS5–NS6 fail-closed / 打假绿 | 通道存在 ≠ 交付；测试不得用 mock 当 live |
| NS7–NS9 系统写 g0 + quoted cuts + R7 4/4 | **下游**已可吃 clean；**上游**源适配仍薄。R7 语料几乎全是 inline documentation |

0815 族测的是「真模型能不能把 **已清洗的文档 markdown** 切成可检索分层知识」。new-harvest 测的是「真网页 / 真 PDF / 真文档 / 真 API fixture 能不能变成 **那份已清洗正文**」。两条实验族共享 runner 纪律，不共享格子。

---

## A.2 回看清单（交付快照）

### A.2.1 交付价值台账

| 单元 | 声称交付 | 真实落地（代码核） | 评级 | 锚点 |
|------|----------|--------------------|------|------|
| `intake/` 四域树 | D08：变换 SSOT | 包存在；`dispatch_clean` 按 capability/strategy/media 分流 | `delivered`（拓扑） | `intake/__init__.py:33-132` |
| Web 消毒 + 结构抽取 | D08-A08 | stdlib HTMLParser 删除闭集标签、属性白名单、段落换行 | `delivered`（确定性） | `intake/web/sanitize.py:11-15` · `intake/text.py:17-56` |
| Web LLM rewrite | D08-A09 | 先消毒再调注入 LLM；缺 LLM → `CLEAN_LLM_UNAVAILABLE` | `placeholder`（运行时） | `intake/web/__init__.py:82-88` |
| Browser acquire/clean | D08-A10 · S05-T001 | 图与码都有；组合根 **不注入** `_browser_fetcher` | `placeholder` | `api/app.py:332-345` 无 `browser_fetcher=` · `acquisition_ingest.py:477-485` |
| PDF text-layer | D08-A12 | 本地字面量抽取；无层 → 不得空成功，码写成 OCR 不可用 | `partial` | `src/runtime/intake/types.py:144-171` |
| PDF understanding / OCR | D08-A12/A13 | 策略登记 + 注入 LLM 路径；默认 503 | `placeholder` | `intake/pdf/__init__.py:33-56` |
| Doc deterministic | inline/local HTML/text | `clean_deterministic` 已接线默认 inline 图 | `delivered` | `intake/doc/__init__.py:11-30` · `lsrag_definition.py:113` |
| Doc LLM / OCR / Vision | S05-T001 | 图存在；OCR e2e **断言失败关闭** | `placeholder` | `tests/e2e/test_source_capability_paths.py:220-258` |
| API 三 operation parser | D08-A01..A04 | chinatax/domain/realestate 版本化 registry + extra=forbid | `delivered`（parser） | `intake/api/registry.py:73-104` |
| API live fetch / pagination | S05-T001 pagination | v1 仅 caller-frozen `records[]`；无供应商客户端 | `missing`（按产品选择，D08 非 P0） | README K6 · `acquisition_ingest.py:230-241` |
| Source-profile 工作流 | 12 条精确 clean key | **公开可选**仅 7 条（inline/local/local-pdf/local-image/http-static/browser/pdf）+ scatter；web-llm/doc-llm/pdf-llm/print-pdf/vision 图已 bootstrap **但调用方不能点名 workflow_key** | `partial`（图在、入口封） | `config_snapshots.py:492-516` · `workflow_registry.py:86-103` · `lsrag_definition.py:929-1069` |
| 默认组合根注入 | 「本地可跑」 | `HttpAcquirer` 已注入；browser/clean_llm **未注入** | `partial` | `api/app.py:280-345` |
| 0815 实验通路 | 生成面 live 4/4 | 存在；对象是 documentation inline，不是四域源 | `delivered`（他族） | `.experiment/0815/runs/MKB-0815-R7/` |

评级纪律：`delivered` = 默认部署可跑或 parser 对 fixture 可复现；`partial` = 有实现但能力/精度明显窄于声称；`placeholder` = 合同+fail-closed，缺注入即 503；`missing` = 无代码路径。

### A.2.2 Deferred / Carried-over 台账（每条带 reopen 触发器）

| 编号 | 项目 | 为什么 defer | reopen 触发器 | 携带至 |
|------|------|--------------|----------------|--------|
| `D-01` | browser / OCR / Vision 组合根未接线 | NS5/NS6 O3；`NS5-VF97` / `NS6-VF97` | 本战役 owner 授权本地 runtime | **new-harvest P0** |
| `D-02` | 文档/网页 LLM 清洗未注入 | 同上；clean 走 stub/CLI 仅 structurize 主路径被 0815 打过 | promptA 与 S11 运输授权 | **new-harvest P1** |
| `D-03` | PDF 解码器是字面量扫描；无层在 decode 就死，不进 OCR 图 | 基线为 fail-closed 文本层 | 扫描件/压缩流/CID 字体在实验中红 | **new-harvest P1 PDF** |
| `D-04` | registered_api 无供应商客户端 / 无分页拉取 | D08 明确非 P0；caller-frozen | 产品要求实时连接器 | 默认真 deferred；本战役只补 **fixture 分页/空集/拒绝** 合同 |
| `D-05` | D04 三张 proposed registry 表未升 required | 55 表闭集；code-owned 镜像已够跑 | owner D04 reopen `T-O` | 本战役 **不升表**，继续 contracts digest |
| `D-06` | e2e sqlite3-on-Turso harness | `NS1-V11` | harness charter | **不进** new-harvest DoD |
| `D-07` | A1/A4 扩展文档、billing、cloud 推理 | 0815 OOS / NS2 O* | 各自 charter | 不进 |
| `D-08` | 0815 生成面残差（Q 通道慢、A5 timeout） | NS9 carry-over | 后继 0815 波次 | **不进** harvest；实验 runner 可借用纪律 |

---

## A.3 对账诚实（本 flavor 灵魂段）

| 声称 | 真实 | 偏差类型 | 证据 | 影响 |
|------|------|----------|------|------|
| 「`intake/` 下 4 个占位通道」 | 四域 **有实现**：消毒、parser、strategy 闭集、dispatch、per-domain 测试 | `under-claim`（口语） | `tests/intake/test_{web,pdf,doc}_clean.py` + 三 provider 测 | 若当空壳重写，会毁掉已选对的拓扑 |
| 「四域已迁完 / D08 HARD 全绿」 | D08 Appendix A 是 2026-08-13 见证；默认 app **仍不注入** browser/LLM | `frozen≠done` / `over-claim`（若沿用 Appendix） | `api/app.py:332-345` | 用旧 closure 当 harvest DoD 会假绿 |
| README「browser/OCR/Vision/doc-LLM/web-LLM = 合同已落地 / 未接线」 | 与代码一致 | 对齐 | README §1.1 · e2e OCR 失败关闭 | 本战役主缺口 |
| S05-T001「必须覆盖 pagination」 | 无 page/cursor 拉取；只有 caller 一次性 `records[]` + `caller_frozen_records.v1` | `frozen≠done` | `clean_preflight.py:439-444` | harvest 若宣称「API 通道完整」而不声明 caller-frozen，即 over-claim |
| PDF text-layer「已落地」 | `%PDF-` 后正则捞 `()` 字面量；压缩流/字体映射/图片页会无层 | `partial` | `types.py:144-171` `decoder=local-pdf-literal-text.v1` | 真实 PDF 会大量掉进 OCR 503 |
| 「HTTP PDF 不会当 HTML 洗」 | `acquisition_mode=pdf` 或 sniff `%PDF-` 时走 pdf；**HTTP 没有 image profile**，静态 URL 若返回 PNG 仍会跑 `clean.extract.web` | `partial` | `intake/__init__.py:68-70` · `config_snapshots.py:504-506` | harvest 须补 HTTP image 拒绝或独立 profile |
| 「print-pdf 策略已登记」 | acquire 只写 `representation_kind=rendered\|transferred`，**从不写 `print_pdf`**；`web.browser_print_pdf` 死键 | `placeholder` | `acquisition_ingest.py:533-536` vs `clean_preflight.py:46-62` | 不接线 acquire 表示，print-pdf 图无意义 |
| 「promptA 冻结指针已够 LLM clean」 | catalog 三套默认 id 互斥：strategy=`promptA.default`、NS1 文档域=`promptA.documentation.default`、snapshot `_DEFAULT_PROMPT_IDS`=`promptA.clean`；对不上则 `PROMPT_HASH_MISMATCH` | `over-claim`（若当可跑） | `strategies.py:63-147` · `prompt_profiles.py:50` · `config_snapshots.py:57-59` | 接线 LLM clean 前必须先统一 id |
| 「无文本层 PDF 会落到 OCR 图」 | `_extract_pdf_text` 无字面量时在 **decode** 抛 `CLEAN_OCR_CAPABILITY_UNAVAILABLE`（422），**到不了** `clean.ocr.local` | `over-claim` | `types.py:154-159` | 扫描件不会进入 OCR 策略，只是解码失败 |
| 「缺 LLM 不得空成功」 | 缺注入 503；空文本 422 | 对齐 D08-X10 | `intake/pdf/__init__.py:37-60` | 保留 |
| e2e「browser 源 succeeded」 | 测试 **手动** `pipeline._browser_fetcher = lambda ...` | `fake-zero`（若当成生产 browser） | `test_source_capability_paths.py:100-101` | 证明图与 evidence 形状，**不**证明有浏览器 |
| D08-A14 runtime 无平行 parser | `_clean` 只 `dispatch_clean` | 对齐 | `clean_preflight.py:108-121` | 保留；harvest 禁止把变换写回 mixin |
| 0815-R7 4/4 证明 intake 完整 | R7 格子是 **inline documentation** | `over-claim`（若挪用） | `MKB-0815-R7/RUN.md` | 生成面 ≠ 收获面 |

- **诚实结论**：当前 intake 处于 **「骨架诚实、收获面未接通」**。确定性 web/doc 与三 provider parser 是真交付；需要端口的策略是真占位；PDF 文本层是窄实现。new-harvest 的工作是 **接线与加固**，不是推倒重来，也不是把 0815 的 cuts 成功当成四域已收获。

---

## A.4 归因 / 缺口分析

| 现象 | 归因（根源/缝/簇） | 根源位置 |
|------|---------------------|----------|
| 默认进程 browser/OCR/LLM clean 全 503 | 组合根只注入 `HttpAcquirer` + inference facade（给 structurize/embed），**没有** clean 专用 port | `api/app.py:280-345` · `IntakeCoreMixin.__init__` |
| 「通道在、能力无」 | D08 把 Worker 栈删除做成了「先留 fail-closed」；后续战役全去打 g1 | deferred ledger `NS5-VF97` |
| PDF 一碰扫描件就死 | 解码器不是 PDF 引擎；无层错误码借用 OCR 不可用 | `types.py:155-158` |
| API 看起来完整 | parser 完整 ≠ acquire 完整；live/pagination 被有意识裁掉 | D08-T004 · README K6 |
| 测试绿、生产不能洗网页 | per-domain 注入 mock fetch/LLM；e2e 给 pipeline 打补丁 | `tests/intake/*` · e2e monkeypatch |
| 路由分支多、运行时暗路由少 | 图已按 profile 声明 process_key；真正危险是 **media 与 capability 打架**（已有 PDF-first 补丁）与 **representation=print_pdf 依赖 acquire evidence** | `clean_preflight.py:46-71` |

根因簇 **S-H1**：组合根注入矩阵不完整。  
根因簇 **S-H2**：PDF/OCR 本地引擎未选。  
根因簇 **S-H3**：实验族只覆盖 inline 文档，没有源适配格子。  
根因簇 **S-H4**：S05 pagination 真相与 D08「非 P0 live fetch」之间未在 qna 再冻结一次，文档读者会以为 API 通道「没做完」。
根因簇 **S-H5**：LLM/print-pdf/vision 图已注册，但 `_source_profile` 闭集不含它们，调用方禁止点名 `workflow_key`（`workflow_registry.py:86-88`）——「有图」≠「可被 Task 选中」。
根因簇 **S-H6**：promptA 三套默认 id 未对齐；0815 格子走 deterministic，从未打到这条闸。

---

## A.5 Verdict（价值-债务 / 达成度 / 健康评级）

| 维度 | 评级 | 一句话 |
|------|------|--------|
| 交付价值 | **中高（骨架）/ 低（收获）** | 三轴拓扑、parser、消毒、fail-closed 码值得保留；能进生产的源几乎只有 inline + 简单 HTML/PDF 字面量 + 冻结 API records |
| 累积债务 | **中** | 债务集中在未注入端口与 PDF 引擎，不是状态机翻车 |
| 愿景/目标达成度 | **对照 S05-T001：部分** | static web / deterministic doc / API map 近；browser/OCR/Vision/LLM/pagination 远 |
| **综合健康** | **可开战，不必先重构** | HEAD 足够作为 harvest 施工面；禁止借 0815 假绿 |

- **反镀金提醒**：不要把 Playwright 生态、通用爬虫、供应商 SDK、第五 source kind、YAML 工作流、Mixin 拆分写进本战役。不要为「完整」去实现 Cloudflare Browser Rendering 兼容层。不要在 harvest 里重开 quoted cuts。

---

## A.6 前瞻交接（给 design / 下一周期）

- **下一周期建议**：以 **new-harvest** 为功能簇，按当前 `intake.dispatch_clean` 实现方式 **补全四域可运行策略**，把状态机已有围栏与真实端口对齐，用闭集错误码覆盖边缘路由，并先落地 **实验族骨架**（发车日 TBD）。
- **start-gate 前置（下一 charter day-1 必须满足）**：
  - 本文已对照 HEAD；不把 D08 Appendix A 当今日绿灯。
  - 业主确认：live vendor fetch **默认仍不做**；browser/OCR/LLM 以 **本地注入** 为目标。
  - 不改 S03/S04 状态枚举；不升 D04 三表。
  - 0815 serving 库与 R7 格子 **禁止**当 harvest 对象（可作「生成面仍绿」的回归闸，若跑实验）。
- **需 owner 拍板的问题**：见 §D.9（OPEN）。未拍板前，设计按下节建议施工，不冻结。

---

## A.7 [profile] Spike / Test 水位

| Spike / 单元 | 上一基线（D08 声称） | 本次 HEAD | D | W | E | 备注 |
|--------------|----------------------|-----------|---|---|---|------|
| Web deterministic | A08 绿 | per-domain 在 | ✓ | ✓ | 仅注入 fetch 的 e2e | 无真浏览器 |
| Web llm_rewrite | A09 绿（mock） | unit/per-domain fail-closed + mock LLM | ✓ | ✓ | — | 无 live promptA |
| Browser | A10 | 503 默认；e2e monkeypatch | ✓ | ✓ | monkeypatch | 假绿风险 |
| PDF text-layer | A12 | 字面量；简单 fixture e2e | ✓ | 窄 | 简单 PDF | 真实 PDF 未测 |
| PDF LLM/OCR | A12 | mock LLM unit | ✓ | ✓ | — | |
| Doc det/LLM/OCR/Vision | A13 | unit + OCR e2e 失败关闭 | ✓ | ✓ | 拒绝路径 | |
| API parser 三套 | A01–A04 | tests/intake + scatter e2e | ✓ | ✓ | fixture scatter | 无 live |
| 空集合 exhaustion | A06 | seal 要求 `caller_frozen_records.v1` | ✓ | ✓ | e2e 有 | 不是分页耗尽 |
| 实验族（源适配） | 无 | 无 | — | — | — | **本战役新建** |

- **水位裁定**：parser/消毒/拒绝码 = 可测；收获 live = 几乎未测。new-harvest 的测试债是 **真端口与真字节**，不是再写一套 dispatch 单测。

---

# B. Legacy-family 清洗通道盘点（ReferenceAnchor）

> 权威闭集以 D08 为准。本节只保留 **会改变 harvest 设计** 的分叉、边缘与反例。禁止把 SMCP / R2 / D1 / Gemini-on-Workers / 隧道 URL 当实现。

## B.1 生产闭集（不要发明第四个 API、第七条 web branch）

### B.1.1 Dedicated APIs — 3 action

来源：`smind-skill-clean-dedicated-apis/services/action_registry.ts:59-80`。

| Legacy `action_branch` | Provider | 生产行为 | 边缘 / 负债（⛔ 不抄） | MKB 已吸收 |
|---|---|---|---|---|
| `fetch-chinatax-articles` | chinatax | 隧道 HTTP → `searchResultAll.searchTotal` → member ETL → 双 hash → child JSON | 隧道 URL；parser 失败 `return null`（silent skip）；`uuidv4()` 当 child id；空列表只 `warn` | parser/字段/FilterMeta/`全文有效`⇒`is_active`；**禁止** skip/随机 UUID/空成功 |
| `getAgencyListings` | domain | sandbox GET → listings 扁平化 → agency 对照表 | `X-Api-Key` 实打；`uuidv4` | 扁平化 + `12106→McGrath` 版本化表 |
| `fetch-listings` | realestate | cookie/UA 透传 → `tieredResults` 拍平 | `.passthrough()` 任意 query；cookie 进 payload；空结果 `status: empty_response` 当成功元数据；`ReaApiParamsSchema` **存在但 processor 没用** | listing_id、去 HTML、sold⇒`is_active=0`；**禁止** passthrough/cookie |

三 provider 共同点（比「要不要 live 客户端」更关键）：

- **一页一 job**：`pageNum` / `pageNumber` 由调用方传入，worker **不**自动翻页。这是 legacy 真实 pagination 模型，不是「worker 内 while next」。
- 空集合 / 空页：**warn 后 COMPLETED**（⛔；MKB 要 exhaustion proof 才 complete）。
- 单 member parse 失败：**skip**（⛔；MKB typed rejection，不得假装 complete）。
- 身份是业务键 `atomic_id`（content_id / listing id）；UUID 只是存储 id。content/meta **双 SHA-256**。
- Domain sandbox URL 写死；REA 密钥不在 worker、cookie 进 payload；chinatax 走 WAF 隧道——全部 ⛔。

Dispatcher 侧（`smind-clean-dispatcher/flows/orchestrator.ts`）按 `workflow.steps[].rank` **线性**派 skill worker，callback 成功即下一步。MKB **不得**复制 callback 成功语义：S05 handler 成功 ≠ S04 accepted。

生产闭集 **只** 来自两个 skill `action_registry`。Dispatcher / admin / console **不**增加 cleaner branch。三层分账（harvest 保持，不把 dispatcher 栈搬回来）：

| 层 | 做什么 | 不做什么 |
|---|---|---|
| Dispatcher | rank 步进、callback、hash differ、scatter 子文件 | 不 fetch、不洗 |
| Universal | 单文件 web/pdf/doc 洗成一份 `clean_text` | **从不 scatter**（`child_files: []`） |
| Dedicated | 一页 API → N 个 atomic JSON | **从不 AI 洗** |

### B.1.2 Universal — 注册表恰 6 条

来源：`smind-skill-clean-universal/services/action_registry.ts:91-148` + `cleaner_web.ts:245-310`。

| Legacy branch | 抓取 | 是否 AI | 清洗 | costType |
|---|---|---|---|---|
| `htmlCrawl` | `fetch` + UA 伪装 + **任意** `fetch_options.headers` | 否 | sanitize → **regex** `stripHtmlTags` | compute |
| `htmlCrawl-geminiClean` | 同上 | 是 | sanitize → Gemini `WEB_CONTENT_CLEANUP_V1` | ai_token |
| `browserFetch` | CF Browser Rendering `/content` | 否 | sanitize → regex strip | compute |
| `browserFetch-geminiClean` | 同上 | 是 | sanitize → Gemini | ai_token |
| `browserPDF` / `browserPDF-geminiClean` | CF `/browser-rendering/pdf` | **强制** AI | Gemini Vision 读打印 PDF | ai_token |
| `geminiUnderstanding` | R2 `source_file` slot，20MiB | 是 | Gemini DOCUMENT_UNDERSTANDING | ai_token |

**不是生产 branch：** `browserPDF-geminiClean` 只在 `cleaner_web.ts:296-302` 的 switch 与 `browserPDF` 同路径，**未** `register()`。经 registry 走会 `UNKNOWN_CLEANER_BRANCH`。D08-T002 把它写成「别名」过宽；harvest **不要**为它单开 strategy。Console 还残留 `['default']` / `['domain','chinatax']` 等 **未注册** 名字，属 UI 漂移，禁止当闭集。

Router（`flows/router.ts:66-80`）用 **branch 名前缀** 选 payload schema；未知前缀 **warn 后跳过校验**——这是 MKB 必须关掉的暗路由。

**Universal 空 HTML 仍 SUCCESS、写出空 `clean_text`。** 这是 ⛔：MKB 已用 `CLEAN_EMPTY` 拒绝。不要把「空正文当成功」借回来。

消毒规则（`core/sanitizer.ts:33-42`，**要借规则、不借 HTMLRewriter**）：

- 删：`script, style, svg, noscript, iframe, object, embed, nav, footer, header, aside, form, template`
- 留属性：`href, src, alt, title, colspan, rowspan, lang, datetime`

MKB 已用 stdlib parser 重写（`intake/web/sanitize.py`）。legacy 非 AI 路径的 **regex 去标签**（`cleaner_web.ts:46-53`）是 S05-T011 反例，**不得回归**。

## B.2 逻辑路由分支（legacy → 三轴）

```text
action_branch
    ├─ 选抓取器（fetch / CF browser content / CF print-PDF / R2 file）
    └─ 选是否上 Gemini
```

MKB 拆成：

```text
source_kind ∈ {inline_payload, local_object, http_resource, registered_api}
    × acquire_capability ∈ {inline, local_object, http_static, http_browser, registered_api}
    × representation ∈ {static, rendered, print_pdf, transferred, …}
    × clean_strategy ∈ 10 键闭集（strategies.py）
    × registered_api 再 × (provider, operation, definition_version)
```

这是 harvest **必须遵守** 的实现方式。禁止再登记 `htmlCrawl-geminiClean` 为 workflow_key 或 source_kind（D08-X04）。

## B.3 边缘场景闭集（legacy 踩过、harvest 必须有 typed 码）

| 场景 | Legacy 行为 | MKB 今日 | harvest 目标 |
|---|---|---|---|
| 未知 branch | `UNKNOWN_CLEANER_BRANCH` / `API_ACTION_NOT_SUPPORTED` | `CLEAN_STRATEGY_UNSUPPORTED` / `CLEAN_PROVIDER_OPERATION_UNSUPPORTED` | 保持 fail-closed |
| 缺浏览器 | CF API 失败当 fetch 失败 | `ACQUISITION_BROWSER_CAPABILITY_UNAVAILABLE` / `CLEAN_BROWSER_UNAVAILABLE` | 默认组合根仍 503，**直到注入** |
| 缺 LLM | 生产上几乎总有 Gemini | 503 `CLEAN_LLM_UNAVAILABLE` 等 | 注入后仍禁止降级到空文本 |
| HTML 空正文 | 可能写出空 clean_text | `CLEAN_EMPTY` 422 | 保持 |
| PDF 无文本层 | 走 Vision | 字面量无匹配 → `CLEAN_OCR_CAPABILITY_UNAVAILABLE` 422 | **拆码**：decode 无层 vs OCR 未配置 vs OCR 失败 |
| 扫描件/图片 | `geminiUnderstanding` | 图像禁止 deterministic | 注入 OCR/Vision 或稳定拒绝 |
| HTTP 拿到 PDF | 取决于 branch，不看字节 | PDF media **压过** http_resource HTML 洗 | 保持；补 Content-Type 撒谎 vs sniff |
| member schema 失败 | **skip + warn** | 422 `CLEAN_MEMBER_SCHEMA_INVALID` | 保持；scatter 不得假装 complete |
| 空 listings / 空 HTML | dedicated warn 后成功；universal 空 `clean_text` 仍 SUCCESS | 无 exhaustion 不得 seal complete；单文件 `CLEAN_EMPTY` | **不要**借空成功 |
| API 分页 | 调用方传 page，**一页一 job**，worker 不循环 | caller-frozen `records[]` + `caller_frozen_records.v1` | 这其实已经对齐 legacy；live 翻页不是遗产缺口 |
| 重复 external_key | 靠随机 UUID 躲开 | `SCATTER_MEMBER_KEY_DUPLICATE` | 保持 |
| 任意 headers/cookie | 进 payload | 调用方不得提交；egress 无自定义头 | 保持 |
| 超 20MiB 文档 | FILE_PARSING_ERROR | `CLEAN_INPUT_TOO_LARGE` | 保持；与 `acquisition_max_response_bytes` 对齐证据 |
| SPA 无静态 HTML | htmlCrawl 得到壳 | 必须走 browser 图，不得暗升级 | **显式** mode=browser，禁止 static 失败后自动 browser |
| Cookie banner 挡住打印 | CF PDF 参数里藏 | 无 | 若做 print-pdf，banner 策略是 **打印参数** 不是 source kind |

## B.4 借鉴 verdict（substrate-fit）

| 点 | verdict | 说明 |
|---|---|---|
| 三 provider 字段表 / 双 digest / FilterMeta 五维 | ✅ 借（已借） | 继续当 API 域 SSOT |
| 6 条 **已注册** web/doc 分叉 | 🔶 部分借 | 借分叉，改写成 strategy 表；`browserPDF-geminiClean` 未注册，不单开 |
| dedicated 一页一 job | ✅ 借（语义） | harvest 的 caller-frozen records 就是这个模型 | 翻页循环不是遗产能力 |
| 消毒标签/属性闭集 | ✅ 借（已借） | 本地 parser |
| regex stripHtmlTags | ⛔ 反例 | S05-T011 |
| silent skip / uuid4 / 空成功 | ⛔ 反例 | S05-T006 / D08-X05..X07 |
| CF Browser / HTMLRewriter / R2 / SMCP callback | ⛔ 反例 | T-O-42 |
| Gemini 别名与 Workers AI Gateway | ⛔ 反例 | 运输走 S11 已有 vLLM / Claude CLI |
| dispatcher rank 线性图 | ⛔ 反例 | MKB 已有 S03 图 + fence |
| 未知 branch 跳过 schema | ⛔ 反例 | extra=forbid |
| 20MiB 文档上限 | ✅ 借（已借） | strategy.max_input_bytes |

---

# C. 当前 MKB 路由与状态机（施工面真值）

## C.1 三轴已在代码里

**10 条 CleanStrategy**（`src/contracts/intake/strategies.py:46-151`）：

| strategy | channel | acquire | clean capability | LLM | browser |
|---|---|---|---|---|---|
| `web.deterministic` | web | http_static / http_browser | `clean.extract.web` | 否 | 否 |
| `web.llm_rewrite` | web | 同上 | `clean.extract.web_llm` | 是 | 否 |
| `web.browser_print_pdf` | **pdf** | http_browser | `clean.extract.pdf_llm` | 是 | 是 |
| `pdf.text_layer` | pdf | local_object / http_static | `clean.extract.pdf_text` | 否 | 否 |
| `pdf.document_understanding` | pdf | 同上 | `clean.extract.pdf_llm` | 是 | 否 |
| `pdf.ocr` | pdf | 同上 | `clean.ocr.local` | 是 | 否 |
| `doc.deterministic` | doc | inline / local_object | `clean.extract.deterministic` | 否 | 否 |
| `doc.document_understanding` | doc | local_object | `clean.extract.doc_llm` | 是 | 否 |
| `doc.ocr` | doc | local_object | `clean.ocr.local` | 是 | 否 |
| `doc.vision` | doc | local_object | `clean.extract.vision` | 是 | 否 |

API **不是** 第 11 条 strategy，而是 `clean.map.registered_api` + `(provider, operation, definition_version)`。

## C.2 主链状态机（harvest 碰得到的段）

```text
Task (S02) queued → running
  Execution (S03) 冻结 workflow_key/revision + config snapshot + prompt digest
    Process claim/lease/fence/outbox
      acquire  → AcquisitionEvidence          [S05]
      decode   → decoded_text + decode_evidence
      clean    → CleanArtifactCandidate       [intake.dispatch_clean]
      seal     → CandidateSet (staging open)  [S04 port，尚未 accepted]
      preflight→ PreflightOutcome（只读 frozen evidence）
      accept   → Snapshot/Item/Revision       [唯 S04 可写 Intake truth]
      [human_review gate]                     [S03 waiting，不写 Item]
      → structurize/construct/vectorize …     [本战役默认不改]
```

合法边 harvest **不得改写**：

- Process 成功 ≠ Snapshot。
- Preflight 不得重新 fetch/clean。
- allowlist 自动放行不得伪造 human gate。
- retry 不得热切 strategy/prompt hash。
- 同指纹二次 ingest：accept replay（NS9-FX2 已修指针时序）；harvest 不得再引入悬空 revision。

生命周期旁路（已有，harvest 只回归、不扩展）：rebuild / metadata / deactivate / reactivate / delete / index.rebuild。OCR 图的 decode 槽是信封坐标，图像 bytes 直达 clean——保持，不要改成「先当文本 decode」。

## C.3 工作流选择（谁决定走哪条清洗通道）

`SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS`（`lsrag_definition.py:929-939`）是 **调用方可见的 source 形状 → 图**，不是 branch 名：

| 调用方形状 | workflow_key 后缀 | acquire | decode | clean |
|---|---|---|---|---|
| inline_payload | 默认 single-intake | inline | text_json_html | deterministic |
| local_object | local-object | local_object | text_json_html | deterministic |
| local_object + PDF | local-pdf | local_object | pdf | pdf_text |
| http static | http-static | http_static | text_json_html | web |
| http browser | http-browser | http_browser | text_json_html | web |
| http pdf | http-pdf | http_static | pdf | pdf_text |
| local image | local-ocr | local_object | text_json_html（信封） | ocr.local |
| （内部图）vision-rejected / doc-llm / web-llm / pdf-llm / print-pdf | 已注册 | 见源 | 见源 | 见源 |
| registered_api | scatter root+child | registered_api | map | child 再 LS-RAG |

**公开入口（已实现，须保持「调用方不能点名图」）**：`ConfigSnapshotService._source_profile`（`config_snapshots.py:492-516`）只看 `source_kind` × `acquisition_mode` × 声明 `media_type`，映射到 `SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS`。`WorkflowRegistryService` **禁止**调用方提交 workflow_key（`workflow_registry.py:86-88`）。

**已 bootstrap 但不可选**（`lsrag_definition.py:1003-1054`，不在 profile map）：

| workflow_key | clean | 为何死 |
|---|---|---|
| `…vision-rejected…` | `clean.extract.vision` | 无 public profile |
| `…doc-llm…` | `clean.extract.doc_llm` | 同上 |
| `…http-web-llm…` / `…http-browser-web-llm…` | `clean.extract.web_llm` | 同上；即便选中，还要 LLM/CLI 且 prompt id 要对上 strategy |
| `…local-pdf-understanding…` | `clean.extract.pdf_llm` | 同上 |
| `…http-browser-print-pdf…` | `clean.extract.pdf_llm` + 期望 `print_pdf` | acquire **从不**写 `representation_kind=print_pdf`（只写 `rendered`/`transferred`） |

今日危险是：静态 HTTP 图永远 `clean.extract.web`，即使站点是 SPA。harvest **禁止** static 失败后自动升 browser（那会伪造 `representation_kind=rendered`）。LLM/print-pdf 必须经 **扩 profile 闭集**（新 `acquisition_mode` 或显式但 typed 的 strategy 字段），不能打开「调用方填 workflow_key」。

## C.4 `_clean` 运行时路由（已实现，须保持）

`clean_preflight.py:27-71` + `intake/__init__.py:68-132`：

1. PDF capability 或 `media_type=application/pdf` **先于** `http_resource` HTML。
2. `print_pdf` representation → `web.browser_print_pdf`（进 pdf 通道，不是 sanitizer）——**但 acquire 今日从不产生该 representation**，此分支是死代码。
3. OCR：PDF → `pdf.ocr`，图像 → `doc.ocr`。扫描 PDF 在 **decode** 就以 OCR-unavailable 失败，不会进本分支。
4. 图像不得 `clean.extract.deterministic`。HTTP 静态图若返回 `image/*`，公开 profile 仍是 `http_resource.static` → `clean.extract.web`（漏洞）。
5. 缺 strategy → 409，不猜。
6. CLI 兜底（`clean_preflight.py:86-107`）理论上能驱动 `web_llm`/`pdf_llm`/`doc_llm`，**前提是图被选中**；OCR/Vision 明确排除 CLI。默认 `ns1_cli_mode=stub` 不能当作这些通道已接线。

组合根今日：`http_fetcher=HttpAcquirer`，`browser_fetcher=None`，`clean_llm=None`。LLM clean 仅当 `_claude_cli` 存在且 strategy `llm_required` 时，才用 `ClaudeCliCleanLanguageModel` 兜底（`clean_preflight.py:86-107`）。**OCR/Vision 明确不走 CLI 兜底**。这是 harvest 接线的挂钩，不要另起一套 mixin 内嵌模型调用。

## C.5 错误码闭集（今日已有，harvest 扩展须登记）

| 码 | 何时 | HTTP |
|---|---|---|
| `CLEAN_CAPABILITY_UNSUPPORTED` | 非四域 capability | 409 |
| `CLEAN_STRATEGY_UNSUPPORTED` / `CLEAN_STRATEGY_CAPABILITY_MISMATCH` | 键不存在或与 process_key 不一致 | 409 |
| `CLEAN_EMPTY` / `CLEAN_PDF_TEXT_LAYER_MISSING` / `CLEAN_HTML_INVALID` | 变换无正文 | 422 |
| `CLEAN_LLM_UNAVAILABLE` / `CLEAN_OCR_CAPABILITY_UNAVAILABLE` / `CLEAN_VISION_CAPABILITY_UNAVAILABLE` / `CLEAN_BROWSER_UNAVAILABLE` / `CLEAN_HTTP_UNAVAILABLE` | 缺注入 | 503 |
| `CLEAN_INPUT_TOO_LARGE` / `CLEAN_PDF_INPUT_MISSING` / `CLEAN_IMAGE_MISSING` / `CLEAN_WEB_INPUT_INVALID` | 输入 | 422 |
| `PROMPT_HASH_MISMATCH` | promptA 指针/字节不对 | 503 |
| `CLEAN_PROVIDER_OPERATION_UNSUPPORTED` / `CLEAN_MEMBER_SCHEMA_INVALID` / `CLEAN_ENVELOPE_SCHEMA_INVALID` | API | 409/422 |
| `SCATTER_MEMBER_KEY_DUPLICATE` / `SCATTER_EXHAUSTION_PROOF_REQUIRED` | 集合 | 422 |
| `ACQUISITION_*` / `PREFLIGHT_*` / `CANDIDATE_SET_FENCE` | 围栏 | 409/422/503 |

Harvest 应 **新增而非复用错码** 的候选：`DECODE_PDF_NO_TEXT_LAYER`（与 OCR 未配置分账）、`ACQUISITION_MEDIA_MISMATCH`（声明 HTML 实为 PDF 已部分由 sniff 处理，需 evidence）、`CLEAN_STRATEGY_NOT_BOUND`（调用方点名的 strategy 与冻结图不一致）。

---

# D. new-harvest 功能簇设计（design）

## D.0 背景与前置约束

- **项目定位回顾**：MKB 是内部 LS-RAG 叶子工作器。调用方以 Team 为租户提交异步 Task；S05 把外部输入变成可接受的 clean 候选；S04 线性化 identity；S06+ 才结构化。Harvest 停在「可验证的 clean Artifact + 仍可走完下游的证据」，不以检索命中为本战役主评分（实验族可把 publish 当可选闸）。
- **本次讨论的前置共识**：
  - 四类 source kind 不变（S05-T002）。
  - `intake/` 是变换 SSOT，runtime 只 fence（D08-T006）。
  - 零 legacy runtime（T-O-42）。
  - 生成面 NS9 已 live-verified；本战役换面，不回写 0815。
- **本设计必须回答的问题**：
  - 四域「完整」在当前实现方式下的可验证含义是什么？
  - 状态机还缺哪几条边，哪些其实已经有、只是没注入？
  - 边缘路由与错误处理的闭集是什么？
  - 测试与 `.experiment` 通路如何对标 0815 而不提前发车？
- **显式排除**：structurize/cuts 算法、cloud 推理、真计费、前端、D04 升表、sqlite3-on-Turso harness、供应商实时 SDK（除非 qna 改裁）。

## D.1 讨论对象

### D.1.1 功能簇定义

- **名称**：`new-harvest`
- **一句话定义**：在现有三轴与 `dispatch_clean` 上，把 pdf/web/doc/api 四域从 fail-closed 占位补成默认可运行（或诚实不可运行）的收获通道，并配齐状态机接线、边缘路由与 0815 形态实验族。
- **边界描述**：包含 acquire/decode/clean/seal/preflight 与四域端口注入、错误闭集、unit/per-domain/e2e/实验骨架；**不包含** 新 source kind、legacy Worker 兼容、cuts/g0 装配、检索金标主评分。
- **关键术语对齐**：

| 术语 | 定义 | 备注 |
|------|------|------|
| 通道 channel | `web` / `pdf` / `doc` / `api` 四域包 | 不是 source_kind |
| 策略 strategy | `CleanStrategyKey` 闭集 | 禁止 branch 名 |
| 收获 harvest | 源 bytes → 可 seal 的 clean 正文 + typed evidence | 尚未等于 accepted Intake |
| 接线 wire | 组合根注入真实 port，使默认 `create_app()` 能走该 strategy | mock 测试不算接线 |
| 占位 placeholder | 合同+拒绝码在，默认进程 503 | README 已用此词 |
| 实验族 | `.experiment/<family>/` + 每枪 `RUN.md` | 发车 ≠ 文档冻结 |

### D.1.2 参考调查报告

- D08 §4.2–§4.3 — 树状对应与 HARD
- S05 §1.3 / §2 — 三轴与不得删减
- 本文 A–C — HEAD 对账与 legacy 分叉
- `.experiment/0815/after-NS3-test-plan.md` — 族/枪分文件、预检、禁止回写

## D.2 在 MKB 中的定位

### D.2.1 角色

- **角色**：源适配与清洗运行时 owner（不是协议层、不是生成内核）。
- **服务谁**：内部编排器提交的 Task；下游 S06 消费 exact clean Artifact；实验族消费可复现格子。
- **依赖**：S03 图与 Process fence、S04 acceptance、S11/S14 promptA hash、S13 CAS、S16 egress。
- **被谁依赖**：structurize 以后整条链；0815 族若改测「真网页」也依赖本簇。

### D.2.2 与其他功能簇的交互矩阵

| 相邻功能簇 | 交互方向 | 耦合强度 | 说明 |
|------------|----------|----------|------|
| S03 Workflow | harvest 读图 / 写 ProcessOutcome | 强 | 不改状态枚举；可加 binding 字段 |
| S04 Intake identity | seal 后交给 accept | 强 | 不在 intake/ 写 Snapshot |
| S11 Inference | clean LLM/OCR 走注入 port 或既有 facade | 中 | 禁止在四域包里写死 vLLM URL |
| S14 Prompt registry | promptA.* + hash | 强 | 与 documentation g1 v5 分身 |
| NS2 三池 | LLM clean 占 local-inference 或 NI | 中 | OCR/browser 是否占池要 qna |
| 0815 实验族 | 纪律借鉴；格子不共享 | 弱 | 新族 `new-harvest` |
| S06–S10 | 可选 e2e 走到 publish | 弱 | 非本簇主 DoD |

### D.2.3 一句话定位陈述

> 在 MKB 里，`new-harvest` 是 **源收获运行时**，负责 **把四类 source 变成可审计的 clean 候选并诚实失败**，对上游提供 **精确 strategy/operation 的 Process 接线**，对下游要求 **S04 仍是唯一 acceptance 写者、S11 仍是唯一模型运输**。

## D.3 架构稳定性与未来扩展策略

### D.3.1 精简点（哪里可以砍）

| 被砍项 | 诱因 | 砍的理由 | 重评条件 |
|--------|------|----------|----------|
| Cloudflare Browser / HTMLRewriter / R2 / SMCP | legacy 完整栈 | T-O-42 | never（换产品形态另开） |
| 供应商实时客户端 | 「API 通道完整」冲动 | D08 非 P0；密钥/WAF/分页是另一战役 | 产品强制实时连接器 |
| 自动 static→browser 升级 | SPA 体验 | 伪造 rendered 证据 | never |
| 第五 source kind / action_branch 登记 | 对照表好写 | S05-T002 | never |
| 通用爬虫/站点登录/cookie jar | 网页难抓 | S16 禁止任意 headers | 独立 egress charter |
| 在 harvest 重做 cuts | 刚打完 R7 | 面已换 | 后继 0815 波次 |

### D.3.2 接口保留点

| 扩展点 | 形式 | 第一版行为 | 未来 |
|--------|------|------------|------|
| `HttpFetch` / `BrowserFetch` / `CleanLanguageModel` | `intake.types` Protocol | 组合根注入；缺则 503 | Playwright / 本地 Chromium / 专用 OCR 适配器 |
| `CleanStrategyDefinition` | contracts + digest | 10 键闭集 | 加键必须升 definition_version + 图 |
| Provider registry | `(provider, operation, version)` | 3 个 v1 | 新 operation = 新 version，禁止 duck-type |
| promptA 指针 | ConfigSnapshot | `promptA.default` / documentation.default | 按域变体，不把正文塞进 strategy |
| 实验族 RUN.md | `.experiment/new-harvest/runs/` | 骨架 + fixture 预检 | owner 点头后才 live |

### D.3.3 完全解耦点

- **解耦对象**：四域纯函数变换 vs Process 围栏 vs 模型运输 vs 实验发车。
- **解耦原因**：D08-T006；0815 已证明「实验脚本读库」与「内核」混写会假绿。
- **依赖边界**：`intake/*` 不得 import `api.app` / Turso；实验脚本不得在 collect 里改 kernel。

### D.3.4 聚合点

- **聚合对象**：capability → strategy → port 的 **唯一 dispatch**。
- **聚合形式**：继续 `dispatch_clean` + `_clean` 薄封装。
- **为什么不能分散**：D08-X03 HTTP PDF 当 HTML；暗路由是 legacy 主债。

## D.4 参考实现 / 内部 precedent 对比

> 模板的 mini-agent / codex / claude-code 槽改为本仓真实 precedent。

### D.4.1 legacy-family

- **实现概要**：两个 skill worker + dispatcher；`action_branch` 同时选抓取与是否 AI。
- **亮点**：生产验证过的字段表、消毒闭集、web 三流水线、20MiB 文档。
- **值得借鉴**：分叉表、FilterMeta、双 digest、未知 branch 失败。
- **不照抄**：栈、silent skip、regex strip、callback=accepted、任意 headers。

### D.4.2 当前 MKB HEAD（内部 precedent）

- **实现概要**：三轴 + 四域包 + 12 张 source-profile 图 + fail-closed 注入。
- **亮点**：PDF-first dispatch、prompt hash、scatter exhaustion proof、NS9 identity replay。
- **值得借鉴**：**就按这个方式把端口补全**。
- **不照抄**：把 e2e monkeypatch 当成接线；把 PDF 字面量当成 PDF 引擎。

### D.4.3 0815 实验族

- **实现概要**：族方案 / 不可变 RUN / preflight 14 闸 / collect 冻结命令 / 禁止回写前枪 / serving 资产 tripwire。
- **亮点**：发车与设计分离；格子矩阵；分析与封条分文件。
- **值得借鉴**：原样借纪律与目录形态。
- **不照抄**：documentation g1 格子、cuts schema、R7 发车命令。

### D.4.4 横向对比速查表

| 维度 | legacy-family | MKB HEAD | 0815 族 | new-harvest 倾向 |
|------|---------------|----------|---------|------------------|
| 路由键 | action_branch | process_key + strategy | 格 ID（N-A3…） | 保持 MKB 键；实验用新格 ID |
| 收获完整性 | 生产可用、身份乱 | 骨架完整、端口空 | 不测收获 | **接线 + 闭集失败** |
| 失败 | skip / warn / callback | typed MkbError | stage-report | 保持 typed；补分账码 |
| 实验 | 无不可变 run | pytest | 成熟 | **新族，发车 TBD** |

## D.5 In-Scope / Out-of-Scope

### D.5.1 In-Scope（本设计确认要支持）

- **[S1]** 按当前方式完整构建四域清洗通道 — 业主目标 1；S05-T001 不得删减的 **可运行** 解释（本地端口，不是 CF）。
- **[S2]** 状态机支持梳理并与清洗通道真实接线 — 业主目标 2；图已有，缺的是组合根与选图契约。
- **[S3]** robust 边缘场景、逻辑路由、错误处理 — 业主目标 3；把 B.3 / C.5 做成测试闭集。
- **[S4]** 全部 unit / per-domain / e2e 工具，并对标 0815 形成实验通路（时间 TBD）— 业主目标 4。
- **[S5]** 默认组合根注入矩阵文档化：何者必须注入、缺省码、ready 探针是否暴露（clean 端口不必挡 `/ready`，除非 qna 要求）。

### D.5.2 Out-of-Scope

- **[O1]** chinatax/domain/REA **实时** HTTP 客户端 — D08 非 P0；重评：产品连接器 charter。
- **[O2]** D04 三表升 required — 55 闭集；重评：owner T-O。
- **[O3]** 改 S03/S04 状态枚举或 Mixin 治理 — NS3 已 defer；重评：megafile 后继。
- **[O4]** 0815 生成面残差与新 cuts — 面已换；重评：R8+。
- **[O5]** 浏览器农场、登录态、验证码、任意 cookie — S16；重评：独立。
- **[O6]** 实验 live 发车日 — 业主 TBD；本设计只交骨架与格子定义。

### D.5.3 边界清单

| 项目 | 判定 | 理由 | 后续落点 |
|------|------|------|----------|
| Playwright/Chromium 本地注入 | `in-scope`（实现可选，合同必须） | 无注入则 browser 仍占位 | qna 选运行时 |
| 本地 OCR 引擎（或复用 VL 模型） | `in-scope` 合同；引擎选型 qna | S05-T001 | qna |
| PDF 库替换字面量扫描 | `in-scope` | 否则「PDF 通道完整」over-claim | P1 |
| API fixture 多页 + 拒绝成员 | `in-scope` | 不是 live pagination 拉取 | P2 |
| API live fetch | `out-of-scope` | D08 | 连接器 charter |
| promptA 走 vLLM vs CLI | `in-scope` 运输；默认跟现有三池 | 不新发明第四池 | qna |
| `/ready` 因缺浏览器变 503 | `defer` | 会让纯 inline 部署不能接 Task | qna |
| 实验发车 | `defer` | 时间 TBD | RUN.md + owner 令 |

## D.6 Tradeoff 辩证分析与价值判断

### D.6.1 核心取舍

1. **取舍 1**：我们选择 **沿 `dispatch_clean` 补端口** 而不是 **重写四域或搬回 action_branch**
   - **为什么**：HEAD 拓扑已对齐 D08；推倒会丢掉 parser/消毒/PDF-first。
   - **代价**：要忍受 mixin 仍偏大；OCR 图 decode 槽语义别扭。
   - **重评**：若 dispatch 出现第三处 media 暗路由。

2. **取舍 2**：我们选择 **「完整」= 默认可跑或默认可预测地 503 + 证据** 而不是 **「完整」= 与 legacy 生产同构的抓取能力**
   - **为什么**：T-O-42；cookie/隧道/CF 不是 v1。
   - **代价**：SPA/反爬站点本战役仍可能只能 browser 本地手工注入。
   - **重评**：业主要实时连接器。

3. **取舍 3**：我们选择 **禁止 static→browser 自动升级** 而不是 **尽力抓到正文**
   - **为什么**：representation_kind 是 provenance；自动升级是假 rendered。
   - **代价**：调用方必须选对 profile。
   - **重评**：never（可加 **显式** fallback policy 新 strategy，不能暗升）。

4. **取舍 4**：我们选择 **API 本战役补齐 fixture 合同（空集/重复/坏 member/多页 records）但不做 live fetch** 而不是 **三 SDK**
   - **为什么**：parser 已是真交付；live 是另一安全面。
   - **代价**：S05-T001 pagination 字面未满。
   - **重评**：qna 必须写清「caller-frozen pagination」是否满足 T001。

5. **取舍 5**：我们选择 **实验族先交骨架、发车 TBD** 而不是 **本文件附带发车令**
   - **为什么**：0815 已证明无主令的 live 会把设计写成 closure。
   - **代价**：本阶段没有 live 收获分数。
   - **重评**：owner 指定窗口。

6. **取舍 6**：我们选择 **PDF 文本层换成可维护的本地库，OCR 仍显式策略** 而不是 **无层一律 LLM**
   - **为什么**：legacy 把一切丢给 Gemini Vision 又贵又不审计；MKB 已分账。
   - **代价**：要引入受控依赖（须进 pyproject，不能藏）。
   - **重评**：库许可证/体积业主否决则保持字面量 + 诚实窄口径。

### D.6.2 风险与缓解

| 风险 | 触发 | 影响 | 缓解 |
|------|------|------|------|
| 把 monkeypatch e2e 当接线 | 急于宣称 browser 绿 | 假绿 | DoD：默认 `create_app()` 无 monkeypatch |
| PDF 库引入攻击面 | 解析恶意 PDF | 进程风险 | 预算+超时+隔离；失败 typed |
| LLM clean 与 structurize 争池 | 同跑 harvest+0815 | 调度饿死 | 复用 NS2 池；实验错峰 |
| promptA 与 g1 v5 混绑 | 图选错 prompt | 脏 clean | strategy 钉 prompt_key；hash 闸 |
| 实验读 sqlite3 开 Turso | 抄 0815 R2 旧 runner | 假红/假绿 | 强制 turso.connect（R3 已改） |
| 范围膨胀到「能洗全网」 | SPA/登录 | 无边 | O5 硬砍 |

### D.6.3 本次 tradeoff 能带来的价值

- **对我们**：结束「通道在但没人敢交真 URL」的夹生；施工面清楚。
- **对 MKB 演进**：S06 终于能吃到非 inline 的真 clean；0815 族可升级为源适配 dogfood。
- **对稳定性杠杆**：错误闭集 + 禁止暗升级，比再加模型更能防止 provenance 撒谎。

## D.7 In-Scope 功能详细列表

### D.7.1 功能清单

| 编号 | 功能名 | 描述 | 一句话收口目标 |
|------|--------|------|----------------|
| F1 | Web 通道完整接线 | deterministic 保持；llm_rewrite 注入；browser acquire 注入；禁止暗升级 | ✅ 默认 app 对 static HTML 不注入也能洗；rendered 有注入则洗、无注入则 503 且码稳定 |
| F2 | PDF 通道完整接线 | 文本层引擎诚实；understanding/OCR 注入；print-pdf 走 pdf 通道 | ✅ 有文本层的 PDF 不依赖 LLM；无层不空成功；HTTP PDF 永不进 sanitizer |
| F3 | Doc 通道完整接线 | deterministic 保持；doc-llm/ocr/vision 注入或稳定拒绝 | ✅ 图像永不走 deterministic；缺引擎 503 分码 |
| F4 | API 通道合同完整 | 三 parser 保持；坏 member/空集/重复/多页 fixture | ✅ 无 silent skip；无 proof 不 complete；仍无供应商客户端 |
| F5 | 状态机与选图接线 | 调用方如何选 profile/strategy；binding digest 含 strategy；retry 不热切 | ✅ 冻结 Execution 的 clean key 与运行时 dispatch 一致 |
| F6 | 边缘路由与错误闭集 | B.3 场景每条有码、有测、无隐式降级 | ✅ 路由表可当 HARD；architecture 扫描无 branch 名 |
| F7 | 测试工具 | unit + tests/intake + e2e 无 monkeypatch 的默认路径 + 注入路径 | ✅ D08-A* 按今日 HEAD 重测；假绿项除名 |
| F8 | 实验通路 | `.experiment/new-harvest/` 族方案 + 首枪 RUN 骨架 + preflight | ✅ 有预检就能发；发车日空着 |

### D.7.2 详细阐述

#### F1: Web 通道

- **输入**：已 acquire 的 HTML，或 URL + `representation=static|rendered`。
- **输出**：`CleanResult` + sanitizer evidence + strategy digest。
- **调用者**：`_clean` via `clean.extract.web` / `web_llm`。
- **核心逻辑**：sanitize（闭集）→ 结构抽取 →（可选）promptA rewrite。Browser 只在 **acquire** 使用 `_browser_fetcher`；clean 默认消费已解码 HTML，避免二次抓取漂移。
- **边界**：
  - 无 HTML 且无 URL → `CLEAN_WEB_INPUT_INVALID`
  - rendered 且无 browser → 503，**不得**改打 static fetch
  - rewrite 空串 → `CLEAN_EMPTY`，不得回退未重写文本（除非未来 qna 允许显式 `allow_passthrough`，默认否）
  - script/nav 文本不得泄漏进 clean
- **收口**：✅ 静态路径零新依赖可跑；rendered/LLM 以注入为界诚实。

#### F2: PDF 通道

- **输入**：blob 或 decode 文本层。
- **输出**：clean 文本；`evidence.mode ∈ {text_layer, document_understanding, ocr}`。
- **核心逻辑**：有可提取文本层 → `pdf.text_layer`；显式 understanding/OCR 才上模型。print-pdf 的 acquire 必须给出 `representation_kind=print_pdf` + PDF bytes。
- **边界**：
  - 无 `%PDF-` → `DECODE_PDF_INVALID`
  - 无层 → **新码** 与 `CLEAN_OCR_CAPABILITY_UNAVAILABLE` 分账
  - HTTP `text/html` 但 sniff 为 PDF → 走 pdf（已有）并记 media mismatch evidence
  - 不得因 understanding 失败而静默改 text_layer
- **收口**：✅ 「PDF 通道完整」= 文本层真提取 + 其余策略可注入；不是「所有 PDF 都能读」。

#### F3: Doc 通道

- **输入**：text/html/plain 或 image bytes。
- **输出**：deterministic 或 LLM/OCR/Vision 文本。
- **边界**：image + deterministic → 409；blob 超 20MiB → 422；Vision 与 OCR **分 strategy**（已有测试）。
- **收口**：✅ 与 F1 相同的注入纪律。

#### F4: API 通道

- **输入**：caller-frozen raw members + 精确 provider binding。
- **输出**：`CleanMember[]`（双 digest、FilterMeta 五维、semantic tuples）。
- **核心逻辑**：保持三 parser；补：合法空列表+proof、非法空、重复键、缺字段、乱序 ordinal、未知 provider。
- **边界**：不 fetch；不 pagination HTTP；多页 = 调用方已拼好的 records + exhaustion proof 语义（「这就是全部」）。
- **收口**：✅ parser 域完整；连接器域明确不在本簇。

#### F5: 状态机接线

- **输入**：Task payload.source + 冻结 workflow revision。
- **输出**：Process 链上每个 clean/acquire key 与 descriptor 一致。
- **核心逻辑**：
  1. 选图继续走 `_source_profile` 闭集（调用方不能点名图）。要启用 LLM/print-pdf/vision，必须 **扩展 profile 键**（例如 `http_resource.static_llm` / `local_object.pdf_understand` / `http_resource.print_pdf`），写入 `SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS`，并给 descriptor 加 **typed、extra=forbid** 的 mode/strategy 字段。
  2. acquire 若声明 print-pdf，必须写出 `representation_kind=print_pdf` 且 bytes 为 PDF。
  3. 物化后 `s05_binding_digest` 含 strategy + provider/operation + **单一** promptA hash。
  4. 统一 promptA 默认 id：strategy 表、snapshot `_DEFAULT_PROMPT_IDS`、documentation 域三者必须可对上，否则 LLM clean 一接就 `PROMPT_HASH_MISMATCH`。
  5. preflight 校验 clean_capability 与图声明一致（今日只 check `startswith("clean.")`，过宽）。
  6. HITL/rebuild 路径不重新 clean。无文本层 PDF 应能 **路由到 OCR 图或 typed 拒绝**，而不是在 decode 盗用 OCR 不可用码。
- **边界**：缺 browser 的 browser 图在 **acquire** 失败，不要建到 clean 再失败（证据更干净）。HTTP 非 PDF 的 image 必须 fail-closed，不得当 HTML 洗。
- **收口**：✅ 一张「descriptor → profile → workflow_key → process_keys → 缺端口码」表可测；未入 profile map 的图不得宣称「通道完整」。

#### F6: 边缘与错误

把 B.3 每行变成 `tests/intake` 或 unit 负例；architecture 扫描禁止 `htmlCrawl` 等字符串进 workflow_key。Dispatch 顺序加注释闸（已有 PDF-first）。新增码进错误字典，禁止复用 OCR 码表达「无文本层」。

#### F7: 测试工具

分层保持 D08 §4.6：

| 层 | 证明什么 | 禁止 |
|---|---|---|
| unit | dispatch 顺序、未知键、digest 幂等、错误码分账 | 起浏览器 |
| per-domain `tests/intake` | 真实 `intake/` 入口 + fixture bytes + mock port | 再实现 parser 当 expected |
| e2e | **默认 create_app** 的成功/503；另测 **显式注入** 的成功 | 把注入写进「默认绿」 |
| architecture | 无 legacy import、无 branch 名、runtime 无平行 cleaner | |

#### F8: 实验通路（时间 TBD）

对标 0815 的 **形态**，换 **格子**：

```text
.experiment/new-harvest/
  family-plan.md                 # 族：为什么、假设、纪律、不碰什么
  runs/MKB-NH-R0/                # 骨架枪，默认不 live
    RUN.md                       # 对象/矩阵/预检/冻结命令（命令先写、先注释）
    preflight.py                 # fixture hash、strategy 注册、serving 可选保护
    collect.py                   # 复用 0815 runner 纪律：turso、禁止 rm 库
    subjects/                    # 冻结 HTML/PDF/image/API raw fixture
    results/                     # 空，直到发车
```

族级假设草案（发车时才评分）：

| ID | 假设 | 失败意味着 |
|---|---|---|
| H-W | static HTML → deterministic clean 可 seal | 消毒/抽取仍有洞 |
| H-B | 注入 browser 后 rendered ≠ static 证据 | provenance 撒谎 |
| H-P | 带文本层 PDF 不需 LLM | 解码器不可用 |
| H-A | 三 provider fixture scatter map 幂等 | parser 回归 |
| H-F | 缺端口 503 + stage-report，无空成功 | 又回到 silent skip |

**不在 R0 做**：真税局/Domain/REA、真任意公网 SPA、与 R7 同库混写格子。若借用 R2 `mkb.turso.db`，必须另后缀且 tripwire 保护 174 向量——**建议 harvest 用独立库**，避免和生成面资产绞死。

### D.7.3 非功能性要求与验证策略

- **性能**：确定性洗应在秒级（文档上限 20MiB / HTTP 默认 8MiB）；LLM/OCR 走既有超时与池，不在本簇发明无限等待。
- **可观测性**：clean evidence 必含 `channel/strategy/definition_digest`；失败进 NS4 stage-report；禁止把原文/HTML 写入 extra。
- **稳定性**：retry 同 binding；取消不留下半套 CandidateSet 当 accepted。
- **安全**：无自定义出站头；URL 身份哈希；secret 不进 descriptor；PDF 库失败不得带文件路径回公共错误。
- **测试覆盖**：F1–F6 每条边界至少一红一绿；F8 预检脚本 exit 0 即可，不要求 live。
- **验证策略**：默认 app 矩阵 + 注入矩阵两张表；实验预检；ruff 0。全量 pytest 存量 11 fail 不得冒充本簇引入。

## D.8 可借鉴的代码位置清单

### D.8.1 来自 legacy-family（ReferenceAnchor）

| 文件:行 | 内容 | 借鉴点 | 备注 |
|---------|------|--------|------|
| `smind-skill-clean-universal/services/action_registry.ts:91-148` | 6 branch 闭集 | 分叉枚举 | ⛔ 不要抄成 source_kind |
| `cleaner_web.ts:245-310` | switch 三组流水线 | AI/非 AI 严格分叉 | 改写成 strategy |
| `core/sanitizer.ts:33-42` | 删标签/留属性 | 规则 | 已本地化 |
| `cleaner_doc.ts:40,59-93` | 20MiB + 整包 | 上限 | 已有 |
| `smind-skill-clean-dedicated-apis/services/action_registry.ts:59-80` | 3 action | 闭集 | 已 registry |
| `providers/chinatax/processor.ts:72-80,147-159` | FilterMeta + skip + uuid4 | 借 FilterMeta；⛔ skip/uuid | |

### D.8.2 来自 0815 实验族

| 文件 | 内容 | 借鉴点 |
|------|------|--------|
| `.experiment/0815/after-NS3-test-plan.md` | 族/枪分文件 | F8 骨架 |
| `runs/MKB-0815-R7/RUN.md` | 预检、冻结命令、tripwire | 纪律 |
| `runs/MKB-0815-R2/collect.py` + R3 turso 读库 | 发车器 | 借 runner，不借格子 |
| `docs/eval/new-start/after-MKB-0815-R3-analysis.md` | 期刊不是真相 | harvest 分析以库为准 |

### D.8.3 本仓库 precedent / 反例

| 文件:行 | 问题 / precedent | 我们借鉴或避开 |
|---------|------------------|----------------|
| `intake/__init__.py:68-70` | PDF-first | ✅ 保持并加测 |
| `api/app.py:332-345` | 未注入 browser/clean_llm | 本簇主施工点 |
| `tests/e2e/test_source_capability_paths.py:100-101` | monkeypatch browser | ⛔ 不得当接线证明 |
| `src/runtime/intake/types.py:144-171` | 字面量 PDF | 窄口径或换库 |
| `clean_preflight.py:86-107` | CLI 仅非 OCR/Vision 兜底 | ✅ 挂钩 |
| `lsrag_definition.py:929-1069` | 12 张图 | ✅ 选图 SSOT |
| `docs/baseline/.../D08` Appendix A | 过期「全绿」 | ⛔ 不当今日验收 |

## D.9 QNA / 决策登记与设计收口

### D.9.1 需要冻结的 owner / architect 决策（全部 OPEN）

| Q ID | 问题 | 影响范围 | 当前建议 | 状态 | 答复来源 |
|------|------|----------|----------|------|----------|
| `NH-Q1` | S05-T001 的 pagination 是否可用「caller 提交本页/全量 records + exhaustion proof」满足，live 分页拉取另开连接器战役？ | API 范围、是否超 cap | **是**。遗产 dedicated **也是一页一 job、调用方传 pageNum**，worker 从不 while-next；live 翻页不是在补 legacy 缺口 | `open` | 待 qna |
| `NH-Q2` | browser 本地 runtime 选什么？（Playwright 进程 / 预留 port / 本波只保持 503） | 依赖、CI | **注入 Protocol + 可选 Playwright**；CI 默认可 503 | `open` | |
| `NH-Q3` | OCR/Vision 引擎？复用 Qwen-VL / 专用 OCR / 本波只 503 | S11 binding | **合同先完整，默认 503，授权后再绑 VL** | `open` | |
| `NH-Q4` | promptA 运输：vLLM `text_generate` / Claude CLI / 两者按池 | 与 0815 争用 | **复用三池，不第四池** | `open` | |
| `NH-Q5` | LLM rewrite 失败可否回退 deterministic 文本？ | 失败语义 | **否**（fail-closed） | `open` | |
| `NH-Q6` | PDF 文本层是否引入第三方库？ | 依赖/许可证 | **倾向引入窄库**；否决则文档改称「字面量层」 | `open` | |
| `NH-Q7` | 缺 browser/OCR 时 `/ready` 是否仍 ready？ | 部署 | **仍 ready**；新 Task 在 acquire/clean 503 | `open` | |
| `NH-Q8` | LLM/print-pdf/vision 如何进入 `_source_profile` 闭集？（新 `acquisition_mode` vs 显式 `clean_strategy` 字段；**禁止**开放 workflow_key） | API 合同 + 图 | **扩 profile 键 + typed 字段，extra=forbid** | `open` | |
| `NH-Q9` | 实验族是否允许共用 0815 Turso 库？ | 资产风险 | **独立库** | `open` | |
| `NH-Q10` | 实验发车窗口 | F8 | **TBD，本文不写令** | `open` | |
| `NH-Q11` | promptA 默认 id 以谁为准？`promptA.default`（strategy 表）/ `promptA.clean`（snapshot）/ `promptA.documentation.default`（NS1 域） | LLM clean 一接就可能 hash 闸 | **strategy 表与 snapshot 对齐为同一 id；documentation 域只在 domain=documentation 时覆盖** | `open` | |
| `NH-Q12` | 无文本层 PDF：decode 失败 vs 自动改走 OCR 图？ | 扫描件路径 | **显式 profile 才走 OCR；decode 无层用新码，不盗用 OCR-unavailable** | `open` | |

### D.9.2 设计完成标准（进入 frozen 前）

1. 业主在 qna 回答 NH-Q1..Q12 中所有影响执行路径的题（至少 Q1–Q8、Q11–Q12）。
2. F1–F8 验收句可映射到未来 action-plan 测试 ID。
3. 与 S05/D08 无未登记冲突；若改 T001 解释，必须新 T-O。
4. 本文状态仍可为 `reviewed`；`frozen` 仅在 qna 锁死后由 planning 引用。

### D.9.3 下一步行动

- **可解锁**：`docs/eval/new-harvest/` 下 qna（pre-initial）→ `planning-initial` → 一份或多份 `docs/plan/new-harvest/*.md` action-plan。
- **需要同步**：README 能力表在接线后才改状态词；D08 Appendix A 标 superseded-as-of-HEAD。
- **进入 qna 的问题**：§D.9.1 全表。

### D.9.4 建议执行切分（不是 action-plan，只是设计侧 DAG）

```text
NH0  qna 冻结 Q1–Q8
  │
  ├─ NH1  组合根注入矩阵 + 错误码分账 + 选图契约（F5/F6 骨架）
  │     └─ 默认 app 负例 e2e（browser/OCR 503 无 monkeypatch）
  ├─ NH2  Web：browser port + llm_rewrite 真注入（F1）
  ├─ NH3  PDF：文本层引擎 + 分码 + understanding/ocr 注入挂钩（F2）
  ├─ NH4  Doc：与 NH3 共享 OCR/LLM port（F3）
  ├─ NH5  API fixture 合同加固（F4）——可与 NH1 并行
  └─ NH6  tests/intake+e2e 对账 + 实验族 R0 骨架（F7/F8）
```

并行约束：NH2/NH3/NH4 依赖 NH1 的注入形状；NH6 贯穿。禁止在 NH0 前写「browser live 已交付」。

## D.10 综述总结与 Value Verdict

### D.10.1 功能簇画像

new-harvest 不是新项目。它是把 D08 已经画在树上的四域，从「能拒绝的占位」推进到「按当前 dispatch 方式可收获」。复杂度不在状态机——S03/S04/S05 边基本在——而在 **端口、把已 bootstrap 却不可选的图接进 `_source_profile`、禁止暗升级、对齐 promptA id、以及用 0815 纪律证明收获面**。API 域的 parser 已经比 web/pdf/doc 的运行时更完整；真正的空洞是 browser 注入、公开不可选的 LLM/print-pdf/vision 图、以及诚实的 PDF 文本层。

### D.10.2 Value Verdict

| 评估维度 | 评级 (1-5) | 一句话说明 |
|----------|------------|------------|
| 对 MKB 核心定位的贴合度 | 5 | 叶子工作器首先得能收获源 |
| 第一版实现的性价比 | 4 | 沿现拓扑补端口，不搬栈 |
| 对未来演进的杠杆 | 4 | 非 inline 语料终于能进 LS-RAG |
| 对开发者日用友好度 | 3 | 调用方必须选对 profile，换来 provenance |
| 风险可控程度 | 4 | 最大风险是假绿与范围膨胀，均已点名 |
| **综合价值** | **4** | 该开战；先 qna 再接线；实验发车另令 |

---

# 附录

## 附录 A. 复现命令

```bash
# 四域包与策略闭集
rg -n "CleanStrategyKey|dispatch_clean|REGISTERED_PROVIDER" intake src/contracts/intake

# 组合根是否注入 browser / clean_llm（今日应看不到 browser_fetcher=）
rg -n "browser_fetcher|clean_llm|HttpAcquirer" api/app.py src/runtime/intake/core.py

# per-domain
# .venv/bin/pytest -q tests/intake tests/unit/test_intake_provider_registry.py tests/e2e/test_source_capability_paths.py tests/e2e/test_registered_api_scatter.py

# legacy 闭集
rg -n "this.register\(" context/legacy-family/smind-skill-clean-universal/services/action_registry.ts \
  context/legacy-family/smind-skill-clean-dedicated-apis/services/action_registry.ts

# 0815 形态参考（不要当 harvest 发车）
sed -n '1,80p' .experiment/0815/after-NS3-test-plan.md
```

## 附录 B. 默认 app 能力矩阵（HEAD `196ce62`，harvest 开工对照）

| 路径 | 默认 create_app | 注入后 | 今日主失败码 |
|---|---|---|---|
| inline text/html | 可跑 | — | — |
| http static HTML | 可跑（HttpAcquirer + 消毒） | — | egress / 空正文 |
| http browser | 不可跑 | 可跑 | `ACQUISITION_BROWSER_CAPABILITY_UNAVAILABLE` |
| http/local PDF 字面量层 | 窄可跑 | 换引擎后加宽 | 无层在 **decode** 即 `CLEAN_OCR_CAPABILITY_UNAVAILABLE`（待分账） |
| PDF understanding / OCR 图 | **公开不可选** | 先扩 profile 再注入 | 图在入口外 |
| local image OCR | 可选然后 503（e2e 已证） | 注入 LLM/OCR | `CLEAN_OCR_CAPABILITY_UNAVAILABLE` |
| Vision / web-llm / doc-llm / print-pdf | **公开不可选** | 扩 profile + 注入 + acquire 写 `print_pdf` | 图在入口外；print-pdf representation 未生产 |
| HTTP 返回 image/* | 会误走 web deterministic | 拒绝或新 profile | 无 image HTTP profile |
| registered_api fixture | 可跑 | — | schema / duplicate / no proof |
| registered_api live | 不存在 | OOS | — |

## 附录 C. 讨论记录摘要

- **分歧（预判，尚未业主）**：API「完整」是否包含 live fetch。
  - **A**：S05-T001 字面含 pagination → 本战役做客户端。
  - **B**：D08 非 P0 + README K6 → caller-frozen 即本簇完整。
  - **本文倾向 B**，必须进 NH-Q1。

## 附录 D. 版本历史

| 版本 | 日期 | 修改者 | 主要变更 |
|------|------|--------|----------|
| v0.1 | 2026-08-29 | Grok | 初稿：HEAD 对账 + legacy 分叉 + new-harvest 设计草案；零决策冻结 |
| v0.2 | 2026-08-29 | Grok | 补正：LLM/print-pdf/vision 图公开不可选；acquire 从不写 `print_pdf`；promptA 三套默认 id；无层 PDF 死在 decode；HTTP 无 image profile |
| v0.3 | 2026-08-29 | Grok | legacy 闭集钉死：registry 恰 6+3；`browserPDF-geminiClean` 未注册；dedicated 一页一 job；universal 空正文成功是反例；console 残留假 branch 名 |
