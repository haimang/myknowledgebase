# D08 — Legacy Clean Capabilities → Intake Topology Migration

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 共有域**：legacy-family **清洗能力闭集** 与 `intake/{api,web,pdf,doc}` **拓扑对应、schema 重排、测试合同**
>
> **文档性质**：`shared-domain constitution / capability-migration truth`
>
> **文档状态**：`draft / owner-review`（**未** owner-freeze；不改写已冻 `T-O-*`；提出 D03/D04 窄 reopen 候选）
>
> **Truth 版本 / 日期**：`D08-v0.1 / 2026-08-13`
>
> **文件路径**：`docs/baseline/domain-truth/D08-legacy-capabilities-migration.md`
>
> **作者**：`MKB owner + Grok`（全量扫描 `context/legacy-family` 的 dedicated-apis + universal cleaners 后合成）
>
> **权威输入**：
> - 行为证据：`context/legacy-family/smind-skill-clean-dedicated-apis/**`、`smind-skill-clean-universal/**`（ReferenceAnchor only）
> - 已冻产品法：`S05-v1.1`（`T-O-49..76`）、`S04-v1.2`、`D03-v1.0`、`D04-v1.1`、`D05-v1.0`、`D07-v0.4`
> - 仓库落点：`intake/` 四域包；runtime 仅 Process 围栏
>
> **词汇权威**：`docs/baseline/spec-glossary.md`（本版同步登记 D08 词）
>
> **下游消费者**：`intake/` 实现、`src/contracts/intake`、D04 窄 reopen、D07 HARD 槽位、`tests/{unit,e2e,intake}`、S05/S03 capability 注册

> **与 S05 分账**：S05 冻结 **四类 source kind、typed evidence、preflight/gate、capability 与 kind 正交**。D08 冻结 **legacy 四域能力/分支的完整盘点、吸收/删除裁决、以及它们如何落到 `intake/` 树与 versioned registry**。S05 不因 D08 增加第五类 source kind，也不恢复 `action_branch` taxonomy。

> **与 D03 分账**：D03-T004 强制 `intake/` 顶级四域。D03 §4.3 曾写「禁止在 intake 内实现 clean」。**D08 正式 reopen 该句**：四域包是 **源适配 + 清洗变换** 的唯一实现点；`src/runtime` 只 claim/fence/commit。状态机与表权威仍不在 `intake/`。

> **与 D04 分账**：D04-v1.1 **55 表闭集不变**。D08 只 **重排 registry 要求** 并提出 3 张 **proposed** 表；升 required 必须显式 D04 reopen + owner `T-O`。

> **与 D07 分账**：本文件 §6 是 D08 HARD 权威；D07 只建槽位索引，不另写第二套断言。

> **Legacy 边界（T-O-42 / S05-T003）**：禁止运行时 import `legacy-family`；禁止 Cloudflare/R2/D1/SMCP/Gemini-on-Workers/隧道/cookie 进 CI 或默认路径。吸收对象是 **schema、parser、策略分叉、稳定键与双 digest**，不是 Worker 栈。

---

## 1. Domain 介绍

### 1.1 Domain 价值

D08 回答：legacy 已经生产验证的 **API / Web / PDF / Doc 清洗能力** 究竟有哪些、各自按什么规则分叉、MKB 为何一度只留下通道外壳、以及它们必须怎样落到 `intake/` 四域与 D04 registry，才能既满足 `S05-T001`（能力不得因实现缺口被删减），又不违反 `S05-T002`（禁止 branch 字符串当 source taxonomy）和 `T-O-42`（零 legacy 兼容）。

没有 D08，实现者会：

- 把三个 dedicated provider 压成一个 `title/body` duck-type mapper；  
- 把五条 web/PDF `action_branch` 压成一条 sanitize；  
- 用 e2e inline 绿假装四域已迁完；  
- 或者反向把隧道、cookie、Cloudflare Browser、`htmlCrawl-geminiClean` 原样搬进 runtime。

### 1.2 Scope fence

**D08 负责：**

- legacy 四域 **能力闭集 + 分支闭集** 的可复验盘点；  
- 每条能力的 **保留 / 改写 / 删除** 裁决；  
- 与 `intake/{api,web,pdf,doc}` 的 **树状对应** 与 Process capability 键；  
- D04 registry / `src/contracts` 的 **重排要求**（含 proposed 表）；  
- 本域 unit / per-domain / e2e 测试合同。

**D08 不负责：**

| 排除项 | 归属 |
|---|---|
| Task/Execution/Process 状态机 | D01 / S02 / S03 |
| IntakeSource/Item/Revision 身份 | S04 |
| Preflight/Gate 合法边 | S05 |
| 物理表闭集升格为 required | D04 owner reopen |
| LLM 传输与模型角色 | S11 / D06 |
| 签署仪式 | `18` / D07 全局门闩 |

### 1.3 Domain 完成定义

| # | 条件 | 本版状态 |
|---|---|---|
| 1 | §2 能力闭集与吸收裁决无歧义 | **met（草稿）** |
| 2 | §3–§4 树状对应覆盖全部 legacy 分支 | **met（草稿）** |
| 3 | D04/D03/S05 重排要求已回填邻域 | **met（草稿回填）** |
| 4 | §6 HARD 进入 D07 槽位 | **met（D07-v0.5）** |
| 5 | Owner freeze + `T-O`（若需改 D03/D04 冻结句） | **open** |

---

## 2. 真相层

> 域内 ID：`D08-T*`。本文件 **不** 领取新的全局 `T-O-*`（须 owner freeze）。与已冻 Truth 冲突时：**已冻 `T-O` / S05 / D04 表闭集优先**；D08 只把缺口写成 reopen 候选。

### 2.1 能力与吸收

| ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `D08-T001` | dedicated-apis 不是「一个 API cleaner」，而是 **3 个 provider × 各 1 个 operation** 的独立 ETL：`chinatax/fetch-chinatax-articles`、`domain/getAgencyListings`、`realestate/fetch-listings`。每个 operation 自带 request schema、envelope 拆包、member parser、idExtractor、FilterMeta、ContextMeta。 | action_registry + 三套 `providers/*/schemas.ts` | `intake/api` 必须按 **provider+operation 版本** 注册，禁止单一 duck-type 覆盖三套字段表 |
| `D08-T002` | universal cleaner 的生产分叉是 **6 条 action_branch**：`htmlCrawl`、`htmlCrawl-geminiClean`、`browserFetch`、`browserFetch-geminiClean`、`browserPDF`（含 `browserPDF-geminiClean` 别名）、`geminiUnderstanding`。它们不是 source kind。 | `smind-skill-clean-universal/services/action_registry.ts:91-148` + `cleaner_web.ts` / `cleaner_doc.ts` | MKB 拆成 **acquire capability × clean strategy**；禁止把 branch 名登记为 `source_kind` 或 workflow_key taxonomy |
| `D08-T003` | **必须吸收**（纯函数 / 策略）：字段映射、Zod 级 member schema、稳定业务键、content/meta 双 digest、FilterMeta 五维 + ContextMeta tags、web 消毒规则、静态/渲染/打印-PDF/文档理解策略分叉。 | S05-T001、S05 §7.4「保留原理」 | 缺任一项 = D08 能力缺口，不得用「通道已存在」宣告关闭 |
| `D08-T004` | **禁止吸收**（平台债）：Cloudflare Workers/HTMLRewriter 运行时、R2 `atomic_bundle`、SMCP/IoManager、Gemini-on-Workers 别名、chinatax 隧道 URL、Domain sandbox 实打、REA cookie/UA 透传、`fetch_options` 任意 headers、silent skip、随机 child UUID、空结果当成功、branch-name 路由。 | `T-O-42`、S05-T002/T003、S05-REF-L05、S05 §7.4「删除负债」 | 测试用 **fixture + 注入 HttpFetch/BrowserFetch/CleanLanguageModel**；缺注入 fail-closed |
| `D08-T005` | v1 source kind 仍只有 `inline_payload` / `local_object` / `http_resource` / `registered_api`。provider/operation 是 **`registered_api` 下的 versioned 注册**，不是第五类 kind。clean 策略是 capability，不是 kind。 | S05-T002、S05-T004、§3.3.4 | caller 不得点名 branch 字符串或自造 handler |
| `D08-T006` | `intake/{api,web,pdf,doc}` 是四域 **变换 SSOT**。`src/runtime/intake` 只把已获取字节 + capability/strategy key 交给 `intake.dispatch_clean`，再 fence Outcome。 | D03-T004 + 本文件对 D03 §4.3 的 reopen | services 不得再实现平行 cleaner；runtime 不得残留 HTML/provider 变换 |
| `D08-T007` | 三 provider 共用 **FilterMeta 五维**（`realm,type,channel,source_name,is_active`）+ **ContextMeta**（复用五维 + `title` + `tags[]`）。这是 registered_api member 的 **canonical semantic 面**，须进 `SemanticDefinition` / `IntakeCandidateMember`，不得只塞进 `clean_text`。 | 三套 `*FilterMeta` / `*ContextMeta` | `is_active` 规则 **按 operation 版本** 编码，禁止全局「看到 status 就 1」 |
| `D08-T008` | 稳定身份 = source-scoped ExternalKey（chinatax=`content_id`+year 证据；domain=`listing id`；REA=`listing_id`）。变更检测至少 **content_digest + meta_digest** 两维。禁止随机 UUID 作 atomic_id。 | S05-T006、S05-REF-L06、三套 processor hash | parser 失败 → typed rejection evidence，禁止 silent skip |
| `D08-T009` | Web/PDF/Doc 的「不同 intake 规则」= 不同 **CleanStrategy**，不是不同 source kind：`web.deterministic`、`web.llm_rewrite`、`web.browser_print_pdf`、`pdf.text_layer`、`pdf.document_understanding`、`doc.deterministic`、`doc.document_understanding`、`doc.ocr`、`doc.vision`。 | cleaner_web switch + cleaner_doc + S05 三轴 | 线上图必须 **声明** strategy 对应的 `clean.*` Process key；不得只靠 media_type 暗路由交差 |
| `D08-T010` | D04-v1.1 55 表 **不够表达** provider/operation/member-schema/clean-strategy 注册。缺口用 **3 张 proposed registry 表** 补；未 reopen 前允许 code-owned 镜像（`src/contracts` + bootstrap digest），但 **不得** 把 schema 藏进 `payload_extra`。 | D04-T004 闭集 + S05 §3.3.4 | 实现可先落地 contracts；升 required 表须 D04 reopen |
| `D08-T011` | 本域验收分三层：**unit**（parser/strategy 纯函数）、**per-domain**（`tests/intake` 走真实 `intake/` 入口 + mock I/O）、**e2e**（Task→acquire→clean→seal，fixture 而非 live vendor）。通道存在但 parser/strategy 未测 = 未交付。 | D07 剖面 + 本文件 §6 | P0-CI 必须含四域 unit+per-domain；e2e 至少一条 API fixture scatter + 一条 web strategy + 一条 PDF strategy |

### 2.2 与已冻 Truth 的衔接（不改写）

| 已冻 ID | D08 如何服从 |
|---|---|
| `S05-T001` | 下文闭集就是「不得删减」的能力面；D08 把它从原则写成可勾选条目 |
| `S05-T002` | branch 名只出现在 §7 锚与对照表左列，不进 source_kind / 对外 descriptor |
| `S05-T003` / `T-O-42` | 零 runtime/schema/API 兼容；fixture 是 MKB 自有 bytes |
| `S05-T008` | 产物仍是 AcquisitionEvidence / CandidateMember / CleanArtifactCandidate / CandidateSet |
| `S05-T009` | raw / source-semantic / clean-derived 分账；LLM 文本不能单独造 Revision |
| `S05-A35` | 扫描仍须零 Cloudflare/R2/D1/SMCP |

---

## 3. 总体方案陈述

1. **先盘点再映射**：以 legacy `action_registry` 为闭集，不允许「仓库里还有但 D08 没点名」的生产 branch。  
2. **三轴拆 branch**：`source_kind` × `acquire_capability` × `clean_strategy`（及 registered_api 的 `provider+operation`）。  
3. **四域落点固定**：`intake/api` 管 provider 注册与 member map；`intake/web` 管 HTML 消毒与 web strategy；`intake/pdf` 管 PDF 文本层/理解；`intake/doc` 管通用文档/OCR/Vision 与确定性文本。  
4. **schema 进 contracts + registry**：每个 operation 的 request/envelope/member schema 有 version+digest；FilterMeta 五维晋升 SemanticDefinition。  
5. **拉取与变换分离**：live HTTP 到税局/Domain/REA **不是** v1 CI 义务；**parser 必须**对冻结 raw fixture 可复现。Acquire 走已有 `intake.acquire.registered_api`（caller-frozen 或未来 secret-ref fetch），clean 走 `clean.map.registered_api` + 指定 operation。  
6. **缺策略 fail-closed**：未注册 strategy、未注入 LLM/browser、member schema 校验失败 → typed error，不得退回 duck-type。  
7. **D04 先提要求后升表**：先写 proposed DDL 语义；55 闭集保持，直到 owner reopen。  
8. **测试跟着闭集走**：每个保留的 operation / strategy 至少一条 unit + 一条 per-domain；e2e 覆盖 scatter 与至少两条 web/pdf strategy。

---

## 4. 具体执行方案清单

### 4.1 API 域：dedicated providers 闭集 → `intake/api`

**说明。** legacy 注册表只有三条生产 action。admin/console 没有第四个 cleaner provider。

| Legacy branch | Provider | Operation | 吸收（parser / 规范） | 删除（栈） | MKB 坐标 |
|---|---|---|---|---|---|
| `fetch-chinatax-articles` | `chinatax` | `get_articles` | 入参 `pageSize/pageNum/xxgkEffectLevel`（效力枚举闭集）；信封 `searchResultAll.searchTotal`；字段 `id→content_id`、`label→type`、`column→channel`、`title`、`content→description`、`url→link`、`pubName→publisher`、`pubDate/cwrq/xxgk_formulatedYear`、`xxgk_aging→effective_status`、`gov_doc`/`appendix`；`全文有效`⇒`is_active=1`；`realm=tax_china`；`source_name=chinatax.gov.cn`；body hash=`title+description+publisher+publish_date`；meta hash=`effective_status+effective_description`；ExternalKey=`content_id`（year 作 evidence，不得当唯一键） | `https://chinatax.sourcemind.com.cn/proxy/chinatax`、固定 siteCode 实打、WAF 隧道 | `registered_api` + `provider=chinatax@version` + `operation=get_articles@version` + `clean.map.registered_api` |
| `getAgencyListings` | `domain` | `get_agency_listings` | 入参 `agencyId` + listingStatusFilter/page；信封 listings 数组；扁平 `addressParts/priceDetails/geoLocation/advertiserIdentifiers/propertyTypes/media`；`headline/description`；`sale_mode`/`property_type=propertyTypes[0]`；agency 名来自 **versioned 对照表**（现表：`12106→McGrath Box Hill`、`37576→Buxton Balwyn Canterbury`，缺省 generic）；`realm=realestate_on_market`；`type=sale_mode`；`channel=property_type`；`is_active=1`（本 operation 无下架推导）；tags=suburb/state/postcode/bed/bath/car | `api.domain.com.au` sandbox、`X-Api-Key` 实打 | 同上，`provider=domain` / `operation=get_agency_listings` |
| `fetch-listings` | `realestate` | `get_listings` | 入参 **typed** `channel/page/pageSize` + versioned filter schema（**禁止** legacy `.passthrough()` 任意 query）；信封 `tieredResults` 拍平；`listing_id` 主键；描述去 `<br>`/标签；`sold` 或 status 含 sold/withdrawn ⇒ `is_active=0`；`realm=realestate`；`type=listing`；`channel=buy\|rent\|sold`；`source_name=agency_name`；tags=价格/户型/地址 | cookie + user_agent 由 caller 明文透传、`services.realestate.com.au` 实打 | 同上，`provider=realestate` / `operation=get_listings`；secret 只许 **registered secret ref** |

**真相层对应。** `D08-T001`、`T003`、`T004`、`T005`、`T007`、`T008`。

**执行台账。**

| 项 | 要求 |
|---|---|
| 包树 | `intake/api/providers/{chinatax,domain,realestate}/`：`schemas.py`（与 contracts 同源或由 contracts 生成）、`parse.py`（纯函数）、`semantics.py`（FilterMeta/ContextMeta/双 hash/key） |
| 注册 | `intake/api/registry.py`：`(provider_key, operation_key, definition_version) → parser`；未知键 `CLEAN_PROVIDER_OPERATION_UNSUPPORTED` |
| 运行时 | `clean_registered_api_members(..., provider, operation, definition_version)`；**禁止** `infer_provider` 猜字段当权威 |
| Acquire | v1 默认继续 **caller-frozen member records**（已有 scatter）。records 必须是 **raw envelope members**（未 parse）或声明 `representation=raw`；已 parse 的不得再走另一份 parser |
| Live fetch | **非 P0**。若未来开通：secret-ref + egress allowlist + 本 operation 的 request schema；仍不把隧道/cookie 写进代码常量 |

**小结。** API 缺口不是「没通道」，是 **三套 operation 规范没登记**。duck-type `map_provider_record` 在 D08 下视为 **过渡适配器**，不得作为 chinatax/domain/REA 的交付证明。

### 4.2 Web / PDF / Doc 域：universal branches → 三轴

**说明。** legacy 用一条 `action_branch` 同时选抓取器与是否上 Gemini。MKB 已把抓取放进 acquire；D08 要求 **clean 策略显式登记**。

| Legacy branch | Acquire（MKB） | CleanStrategy | 吸收 | 删除 | `intake/` 落点 |
|---|---|---|---|---|---|
| `htmlCrawl` | `intake.acquire.http_static` | `web.deterministic` | 消毒规则（见下）+ 结构/纯文本抽取；**不上 LLM** | CF `fetch` UA 伪装、`fetch_options` 任意 headers | `intake/web` + `clean.extract.web`（strategy=deterministic） |
| `htmlCrawl-geminiClean` | `http_static` | `web.llm_rewrite` | 先消毒，再注入 LLM 按 **promptA / `WEB_CONTENT_CLEANUP` 等价 hash** 重写 | Gemini-on-Workers、`TEXT_FLASH` 别名 | `intake/web` + `clean.extract.web`（strategy=llm_rewrite）或独立 `clean.extract.web_llm` |
| `browserFetch` | `intake.acquire.http_browser` | `web.deterministic` | 同一套消毒；输入是 **rendered HTML** | CF Browser Rendering `/content` API | `intake/web`；representation=`rendered` |
| `browserFetch-geminiClean` | `http_browser` | `web.llm_rewrite` | rendered HTML + LLM 重写 | 同上 Gemini 栈 | 同上 |
| `browserPDF` / `browserPDF-geminiClean` | **新 acquire 或 http_browser 的 print 表示** `representation=print_pdf` | `web.browser_print_pdf` | 网页打印为 PDF 后走 **PDF document understanding**（强制 LLM）；cookie-banner 隐藏是打印参数，不是 source kind | CF `/browser-rendering/pdf`、强制 Gemini Vision 别名 | acquire 产出 `application/pdf`；clean 进 `intake/pdf`（**不要**当 HTML 消毒） |
| `geminiUnderstanding` | `intake.acquire.local_object`（或已 acquire 的 file slot） | `doc.document_understanding` / `pdf.document_understanding` | 整包 bytes + MIME + 20MiB 上限 + prompt hash；PDF 走 `intake/pdf`，图/其它文档走 `intake/doc` | Gemini `DOCUMENT_UNDERSTANDING` 别名、R2 `source_file` slot 名 | MIME 分流；缺 LLM fail-closed |

**消毒规则（从 HTMLRewriter 改写，不依赖 Workers）。**

- **删除元素**：`script, style, svg, noscript, iframe, object, embed, nav, footer, header, aside, form, template`（及注释）。  
- **属性白名单**：仅 `href, src, alt, title, colspan, rowspan, lang, datetime`。  
- **结构抽取**：stdlib HTMLParser（已在 `intake/text.py`）；**禁止** regex 去标签作为 SSOT（S05-T011）。legacy `stripHtmlTags` 只作对照，不得回归。  
- 压缩比/长度进入 clean evidence，不进入 identity。

**PDF 子策略。**

| Strategy | 输入 | 行为 |
|---|---|---|
| `pdf.text_layer` | decode 已得文本层 | 确定性规范化；无层 → **不得**空成功 |
| `pdf.document_understanding` | blob + 注入 LLM | 文档理解；无 LLM → `CLEAN_LLM_UNAVAILABLE` |
| `pdf.ocr` | 扫描页/无文本层 | 走 `clean.ocr.local`；与 decode 失败码分账 |

**Doc 子策略。** `doc.deterministic`（本地 HTML/text）、`doc.document_understanding`、`doc.ocr`、`doc.vision`。图像 media **禁止**走 `clean.extract.deterministic`。

**真相层对应。** `D08-T002`、`T003`、`T004`、`T009`。

**执行台账。** `dispatch_clean` 以 **capability + strategy + media_type** 决策；`http_resource` **不得**压过 `application/pdf`。线上 HTTP static/browser 图声明 `clean.extract.web`；PDF 图声明 `clean.extract.pdf_llm`；`web.llm_rewrite` / `browser_print_pdf` 必须有独立 workflow 或 binding，不得只靠暗路由。

**小结。** 网页「不同 intake 规则」在 MKB 里是 **strategy 表**，不是再开 source kind。缺 `llm_rewrite` 与 `browser_print_pdf` 就是与 legacy 能力面的真实缺口。

### 4.3 与 `intake/` 拓扑的树状对应

```text
intake/                          # 变换 SSOT（D08 reopen D03 §4.3）
├── __init__.py                  # dispatch_clean(capability, strategy, …)
├── types.py                     # CleanResult / CleanMember / ports
├── text.py                      # NFC/LF、结构 HTMLParser（全渠共享原语）
│
├── api/
│   ├── registry.py              # provider+operation+version → parser
│   ├── __init__.py              # clean_registered_api_members
│   └── providers/
│       ├── chinatax/            # get_articles schema/parse/semantics
│       ├── domain/              # get_agency_listings …
│       └── realestate/          # get_listings …
│
├── web/
│   ├── sanitize.py              # 标签删除 + 属性白名单（改写 HTMLRewriter 规则）
│   └── __init__.py              # clean_web(strategy ∈ {deterministic, llm_rewrite})
│
├── pdf/
│   └── __init__.py              # clean_pdf(strategy ∈ {text_layer, document_understanding})
│
└── doc/
    └── __init__.py              # clean_deterministic / clean_document
                                 # strategy ∈ {deterministic, document_understanding, ocr, vision}

src/runtime/intake/              # 仅围栏：claim → dispatch_clean → Outcome
src/workflows/                   # 声明 acquire × clean capability；不写变换
src/contracts/intake/            # request/envelope/member/strategy 形状 SSOT
```

**Process 键（与树上叶子对齐，禁止 branch 名）。**

| 树节点 | Process / strategy key |
|---|---|
| api 注册表 | `clean.map.registered_api` + `provider`/`operation`/`definition_version`（binding，不是 key 字符串拼接 taxonomy） |
| web deterministic | `clean.extract.web` + `strategy=web.deterministic` |
| web LLM rewrite | `clean.extract.web` + `strategy=web.llm_rewrite`（或 `clean.extract.web_llm`） |
| pdf text layer | `clean.extract.pdf_llm` 仅当无 LLM 走 text_layer **须在 evidence.mode 显式**；推荐独立 `clean.extract.pdf_text` 若要避免键名误导 |
| pdf understanding | `clean.extract.pdf_llm` + `strategy=pdf.document_understanding` |
| print-pdf | acquire 表示 `print_pdf` → 上列 pdf understanding |
| doc deterministic | `clean.extract.deterministic` |
| doc LLM | `clean.extract.doc_llm` |
| ocr / vision | `clean.ocr.local` / `clean.extract.vision` |

**inline / local_object** 继续走 `doc.deterministic`，不假装 web。

### 4.4 D04 schema 回顾与重排

**现状（D04-v1.1）。** 与本域相关的 required 表：

| 表 | 已能表达 | 不能表达 |
|---|---|---|
| `mkb_source_kind_definitions` | 四类 kind、cardinality、capability eligibility digest | provider/operation、member 字段表 |
| `mkb_intake_semantic_definitions` | 语义键版本 | 未登记 FilterMeta 五维为正式键 |
| `mkb_intake_candidate_sets/pages` | seal/page/root | per-member content/meta 双 digest 列（现多在 page payload） |
| `mkb_intake_revision_semantics` | revision 语义值 | 未要求 realm/type/channel/source_name/is_active |
| `mkb_prompt_hash_pointers` | promptA hash | 未钉 web rewrite / doc extract 的 prompt key |
| `mkb_adapter_bindings` | LLM 能力绑定 | 未钉 clean strategy → 是否 require LLM |

**重排原则（不改 55 闭集）。**

1. **不**为 chinatax/domain/REA 各建业务表；member 仍经 CandidateSet pages + 验收后 S04 十表。  
2. **不**把 provider 做成第五 source kind。  
3. FilterMeta 五维 **晋升** 为 `mkb_intake_semantic_definitions` 的 code-owned 行（`realm`,`type`,`channel`,`source_name`,`is_active`），经 `mkb_intake_revision_semantics` 落 Revision。  
4. 双 digest 在 CandidateMember 合同中为 **一等字段**；可暂存 page payload，但 contracts 必须 typed，禁止只写 `payload_extra`。  
5. 下列 3 表为 **D08-proposed / 非 required**，直到 D04 reopen：

**Proposed `mkb_intake_provider_definitions`**

| 列 | 约束 |
|---|---|
| `provider_key`,`definition_version` | UNIQUE；如 `chinatax`/`domain`/`realestate` |
| `definition_digest` | NOT NULL；同 version 异 digest → bootstrap fail |
| `realm_default` | TEXT |
| `source_kind` | CHECK = `registered_api` |
| `display_name`; `registered_at`; `payload_extra` | |

**Proposed `mkb_intake_provider_operations`**

| 列 | 约束 |
|---|---|
| `provider_key`,`operation_key`,`definition_version` | UNIQUE |
| `request_schema_ref`,`request_schema_digest` | NOT NULL |
| `envelope_schema_ref`,`envelope_schema_digest` | NOT NULL |
| `member_schema_ref`,`member_schema_digest` | NOT NULL |
| `normalizer_key`,`normalizer_version`,`normalizer_digest` | NOT NULL |
| `cardinality` | CHECK ∈ `single,scatter` |
| `pagination_profile_ref` | NULL |
| `secret_slots_json` | 仅 slot 名，无密文 |
| `definition_digest`; `payload_extra` | |

**Proposed `mkb_intake_clean_strategy_definitions`**

| 列 | 约束 |
|---|---|
| `strategy_key`,`definition_version` | UNIQUE（`web.deterministic` 等） |
| `channel` | CHECK ∈ `api,web,pdf,doc` |
| `acquire_capability`; `clean_capability` | NOT NULL |
| `llm_required`; `browser_required` | BOOL |
| `prompt_key`,`prompt_version` | NULL 或指向 `mkb_prompt_hash_pointers` |
| `max_input_bytes` | 如 doc 20MiB |
| `definition_digest`; `payload_extra` | |

**`mkb_source_kind_definitions` 列要求重排（无新表）。** eligibility digest 必须覆盖 **精确** acquire/clean keys（含 `clean.extract.web|pdf_llm|doc_llm`），禁止只列 `clean.extract.deterministic`。`registered_api` 行须引用 provider-operation manifest digest（code 或 proposed 表）。

**真相层对应。** `D08-T010`、D04-P04（禁 payload_extra 承载 identity/schema）。

### 4.5 D03 / contracts 落点

| 路径 | D08 要求 |
|---|---|
| `src/contracts/intake/providers/` | 三 operation 的 request/envelope/member 模型；`extra=forbid` |
| `src/contracts/intake/strategies.py` | CleanStrategy 枚举与 binding |
| `src/contracts/intake/semantics.py` | FilterMeta / ContextMeta |
| `intake/*` | 只依赖 contracts + 注入 ports；不定义第二套跨层模型 |
| D03 §4.3 | **改为允许** intake 实现 clean 变换；仍禁止写 Snapshot/Revision、禁止对外 HTTP、禁止 import legacy-family |

### 4.6 测试能力定义（本域合同）

见 §6。分层：

| 层 | 目录 | 测什么 | 不测什么 |
|---|---|---|---|
| Unit | `tests/unit/` | dispatch 顺序、fail-closed、registry 拒未知、双 digest、key normalizer、D04/contracts 形状 | live HTTP、GPU |
| Per-domain | `tests/intake/test_{api,web,pdf,doc}_*.py` | **调用真实** `intake/` 入口；fixture raw JSON/HTML/PDF bytes；注入 mock LLM/fetch | 再实现一份 parser 当 expected blob |
| E2E | `tests/e2e/` | Task→acquire→clean→seal（及可选 accept）；断言 **process_key + strategy/provider evidence** | 税局/Domain/REA/CF 实网 |

---

## 5. 事实反例 + 风险台账

| ID | 反例 | 围栏 |
|---|---|---|
| `D08-X01` | `map_provider_record` 用 `title or name or headline` 当三 provider 交付 | HARD：chinatax fixture 无 `title` 只有 `label/content/xxgk_aging` 时必须 parse 成功 |
| `D08-X02` | `infer_provider` 见 `effective_status` 就标 chinatax | 权威只来自 binding 的 provider+operation |
| `D08-X03` | HTTP PDF 因 `source_kind=http_resource` 走 web 消毒 | dispatch 先 PDF/image |
| `D08-X04` | 用 `htmlCrawl-geminiClean` 当 workflow_key / source_kind | S05-T002；architecture 扫描禁止 |
| `D08-X05` | parser 失败 `return null`（legacy silent skip） | typed rejection；required member 阻止 root 自动 RAG |
| `D08-X06` | child `uuid.uuid4()` 当 ExternalKey | S05-T006 |
| `D08-X07` | 空 listings 当 complete 且无 exhaustion | S05-A11 |
| `D08-X08` | REA `.passthrough()` 任意 filters | extra=forbid + versioned filter schema |
| `D08-X09` | cookie/API key 进 descriptor 或日志 | S16 secret-ref；redact |
| `D08-X10` | 缺 LLM 仍「成功」空文本 | fail-closed 码 |
| `D08-X11` | e2e 只跑 inline HTML 就宣称四域迁完 | D08-A* 未绿不得关缺口 |
| `D08-X12` | 把 proposed 表未 reopen 就当已存在 DDL | readiness 不得依赖未 migration 的表 |

| 风险 | 缓解 |
|---|---|
| 55 表不够导致 schema 进 payload_extra | T010 + D04-P04；先 contracts |
| agency 对照表漂移 | versioned 表 + digest；改表升 operation version |
| promptA 与 web rewrite 双正文 | 只许 `data/prompts` + hash 指针 |
| D03「intake 不准 clean」与实现打架 | 本文件 reopen + D03 校准条 |

---

## 6. 测试与验收台账

> HARD 不发明第二套 S05-A*。下列为 **D08 增量**。证据未绿 ≠ 实现已交付。

| ID | HARD 断言 | 层 | 证据 |
|---|---|---|---|
| `D08-A01` | 注册表恰含 chinatax/get_articles、domain/get_agency_listings、realestate/get_listings 三 operation；未知键 fail-closed | unit | registry 测 |
| `D08-A02` | chinatax **raw** fixture（`id/label/column/content/xxgk_aging/...`）经 `intake.api` 得 `content_id/type/channel/description/effective_status`；`全文有效`⇒`is_active=1`；双 digest 稳定 | per-domain | `tests/intake/test_api_chinatax.py` |
| `D08-A03` | domain fixture 扁平化 address/price/geo/media；agency `12106`⇒McGrath；`realm=realestate_on_market` | per-domain | `tests/intake/test_api_domain.py` |
| `D08-A04` | REA fixture `tieredResults`→`listing_id`；描述无 HTML；sold/withdrawn⇒`is_active=0` | per-domain | `tests/intake/test_api_realestate.py` |
| `D08-A05` | 缺 ExternalKey / schema 失败 → rejection evidence，**不** silent skip | unit | 负例 |
| `D08-A06` | 合法空集合 + exhaustion proof → complete；无 proof → 不得 seal complete | unit / e2e | 对齐 S05-A11 |
| `D08-A07` | FilterMeta 五维 + ContextMeta tags 出现在 member.evidence / semantic tuples，不只在 clean_text | per-domain | |
| `D08-A08` | web deterministic：删除 script/nav 等 + 属性白名单；结构 parser；无 LLM 调用 | per-domain | `tests/intake/test_web_clean.py` |
| `D08-A09` | web llm_rewrite：先消毒再调用注入 LLM；无 LLM → `CLEAN_LLM_UNAVAILABLE` | per-domain | |
| `D08-A10` | rendered 表示走 browser port；缺 browser → `CLEAN_BROWSER_UNAVAILABLE` | per-domain | |
| `D08-A11` | print_pdf / HTTP PDF blob **不**经 HTML sanitizer；走 `intake.pdf` | unit + per-domain | 对齐既有 http-pdf 测 |
| `D08-A12` | pdf text_layer 无层不得空成功；understanding 无 LLM fail-closed | per-domain | `tests/intake/test_pdf_clean.py` |
| `D08-A13` | doc understanding / ocr / vision 分策略；图像不得走 deterministic | per-domain | `tests/intake/test_doc_clean.py` |
| `D08-A14` | runtime `_clean` 源码只 `dispatch_clean`；无 HTMLExtractor / provider parser | unit / architecture | |
| `D08-A15` | 线上 HTTP/PDF/doc-llm/API scatter 图 **声明** 对应 clean Process key | unit | workflow required_process_keys |
| `D08-A16` | e2e：caller-frozen **raw** chinatax/domain/REA 至少一条 scatter → map → seal；evidence.provider/operation 正确 | e2e | `tests/e2e/` |
| `D08-A17` | e2e：static HTML `web.deterministic` 与 PDF text_layer 或 understanding（mock LLM）均可 Task 终态可观测 | e2e | 可扩现有 source-capability e2e |
| `D08-A18` | 扫描：无 legacy-family import、无 chinatax.sourcemind / realestate.com.au / cloudflare.com/client 默认常量作为生产 URL SSOT | architecture | 对齐 S05-A35 |
| `D08-A19` | contracts：三 member schema `extra=forbid`；非法字段 422/typed | unit | |
| `D08-A20` | 同 raw + 同 operation version → 同 ExternalKey + 同双 digest（幂等） | unit | |

**Release 剖面。** `D08-A01..A15,A18..A20` ∈ **P0-CI**；`A16..A17` ∈ **P2-E2E**。无 P3 live vendor。

---

## 7. Reference-anchor 台账

| Ref | 文件锚 | 只证明的事实 | 裁决 |
|---|---|---|---|
| `D08-REF-01` | `smind-skill-clean-dedicated-apis/services/action_registry.ts:59-80` | 生产仅 3 action | **保留闭集**；改写成 provider+operation |
| `D08-REF-02` | `providers/chinatax/get_articles.ts:51-157` + `schemas.ts` | 隧道 fetch + xxgk 字段表 + Zod | **保留 parser/schema**；**删除** BASE_URL/隧道 |
| `D08-REF-03` | `providers/chinatax/processor.ts:72-250` | FilterMeta、双 hash、searchTotal、随机 UUID、空列表 warn | **保留** meta/hash/拆包；**删除** random UUID / 空成功 |
| `D08-REF-04` | `providers/domain/get_agency_listings.ts:60-174` + `processor.ts:36-115` | sandbox fetch、扁平化、agency 表 | **保留** parse/对照表版本化；**删除** live URL/key |
| `D08-REF-05` | `providers/realestate/get_listings.ts` + `schemas.ts:90-118` | cookie 透传、passthrough filters、tieredResults | **保留** 拍平/去 HTML/sold 规则；**删除** cookie 入 payload、passthrough |
| `D08-REF-06` | `smind-skill-clean-universal/services/action_registry.ts:91-148` | 6 branch + costType | **拆三轴**；删除 branch taxonomy |
| `D08-REF-07` | `cleaner_web.ts:65-310` | 三 pipeline + AI/非 AI 严格分叉 | **保留分叉**；删除 CF Browser/PDF API 与 Gemini 直呼 |
| `D08-REF-08` | `core/sanitizer.ts:33-130` | 删除标签 + 属性白名单 + HTMLRewriter | **保留规则**；改写为本地实现 |
| `D08-REF-09` | `cleaner_doc.ts:59-151` | 20MB、整包、单 branch | **保留** 上限/MIME 分流；策略表扩展 |
| `D08-REF-10` | `schemas_common.ts:148-215` | 任意 fetch_options；child_files + 双 hash | **删除** 任意 headers；**改写** child_files→CandidateMember |
| `D08-REF-11` | S05-REF-L04..L05 | registry 经验 vs silent skip 风险 | 与本表一致 |

---

## 8. Domain verdict

### 8.1 评价

legacy 四域的 **能力面是完整且已生产验证的**。baseline v1 与随后的 `intake/` 通道迁移吸收了 **正交能力键与 Process 围栏**，没有吸收 **operation schema / 策略分叉**。这不是 S05 允许删减能力，而是执行时把「不要搬 Worker」做成了「不要搬规范」。

D08 把规范重新列为 v1 义务，同时守住 T-O-42：fixture + 纯函数 + 注入端口。

### 8.2 对下游的约束

| 下游 | 约束 |
|---|---|
| `intake/` | 按 §4.3 树补 provider 包与 strategy；废止权威 duck-type |
| S05 | 不改四 kind；capability 表须能指向 strategy/operation binding |
| S03 | 图声明精确 clean key；禁止 branch 名 step |
| D03 | §4.3 clean 禁令以本文件为准 reopen |
| D04 | 3 表 proposed；语义键五维登记；55 暂不变 |
| D07 | 槽位 `D08` + E2E-16..18 |
| S11/S14 | web rewrite / doc extract 只引用 prompt hash |
| S16 | 无 cookie/key 进 descriptor |

### 8.3 未关闭边界

- live registered_api fetch（secret-ref）是否进 v1 默认路径：D08 = **非 P0**。  
- `clean.extract.pdf_text` 是否从 `pdf_llm` 拆键：推荐，不阻塞 parser 工作。  
- `browser_print_pdf` 的 acquire capability 新键 vs `http_browser` 表示：实现选一并登记 strategy。  
- D04 3 表何时升 required：owner reopen。

---

## 9. 修订历史

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| `D08-v0.1` | 2026-08-13 | draft / owner-review | 首版：四域闭集、树状对应、D04 proposed 三表、测试 HARD、邻域回填 |

---

## Appendix A — 当前实现对照（非验收豁免）

> 2026-08-13 实现见证回填；不改变 `D08-v0.1 / owner-review` 的权威状态。

| 项 | 2026-08-13 代码见证 | D08 判定 |
|---|---|---|
| provider-operation registry | `intake/api/registry.py` 恰含三个 v1 operation；未知键 fail-closed | 满足 A01/A05/A19/A20 |
| provider schema/parser | `intake/api/providers/{chinatax,domain,realestate}.py` + `src/contracts/intake/providers/`；raw schema `extra=forbid` | 满足 A02–A04 |
| strategy registry | `src/contracts/intake/strategies.py` 登记 web/pdf/doc 十个显式策略与 capability、端口、20 MiB、Prompt A binding | 满足 A08–A13 |
| 精确 Process 接线 | workflow 分别声明 `clean.extract.web[_llm]`、`clean.extract.pdf_text|pdf_llm`、`clean.extract.doc_llm`、`clean.map.registered_api` | 满足 A15 |
| Web 消毒 | `intake/web/sanitize.py` 使用结构 parser、闭集删除标签与属性白名单 | 满足 A08/A09 |
| PDF / OCR / Vision 分流 | HTTP PDF/print-PDF 优先进入 `intake.pdf`；PDF OCR 与 doc OCR/Vision 独立策略，无隐式降级 | 满足 A10–A13 |
| Runtime clean fence | `src/runtime/intake/clean_preflight.py` 只经 `dispatch_clean` 进入四域；无 runtime parser/HTML extractor | 满足 A14/A18 |
| 语义与 digest | member、scatter artifact、revision semantics 均携带双 digest、FilterMeta 五维与 ContextMeta tags | 满足 A07 |
| Prompt A | LLM clean 从冻结 ConfigSnapshot 指针读取正文并复核 SHA-256；正文不在 strategy/runtime 复制 | 满足 prompt hash 约束 |
| e2e / 回归 | 三 provider raw scatter→map→seal→child；static Web 与 PDF text-layer Task 路径；全量 pytest 绿 | 满足 A06/A16/A17；仍须 owner review 才能改文档权威状态 |
