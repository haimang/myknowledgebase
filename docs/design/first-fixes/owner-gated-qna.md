# first-fixes · Owner-Gated Q&A（7 gate 收敛清单）

> **状态：`FROZEN`（冻结于 2026-05-31）** —— 业主已对 Q1–Q7 全部裁决（均同意 Opus 推荐路线，见各题 `业主回答`）。本清单为下游 final 规划与 action-plan 的唯一裁决口径；引用方只看 `Q 编号 + 业主回答`。如需推翻须在本文追加修订说明，不得在别处改口。
>
> 范围：`docs/design/first-fixes/initial-planning-by-opus.md` §7.A 的 7 个 owner decision gate（G-F-1 ~ G-F-7）
> 目的：把会决定 first-fixes 各 phase（尤其 F5/F6 体量）的业主决策收敛到一份单一清单，作为 `proposed → final` 的关闭依据。各下游 action-plan 引用本文 `Q` 编号为唯一口径。
> 使用方式：业主只在每题 **业主回答** 处填写；填写后即成为下游 final 规划与 action-plan 的唯一裁决来源。

---

## 角色声明（身份反转 + 单声部变体）

本 QNA 显式采用**身份反转**且**本轮不征求 GPT second opinion**：

- **Opus（本文作者）= 提问人**：负责每题的 `影响范围 / 为什么必须确认 / 当前建议 / Reasoning`，以及 `Opus 的问题分解` 与 `Opus 的推荐路线`。
- **GPT second opinion**：**本轮不设**。模板中 `Opus的对GPT推荐线路的分析` 槽位标 `（本轮无 GPT second opinion，N/A）`，按模板纪律保留结构、不删字段。
- **业主 = 裁决人**：只在 `业主回答` 作答；一旦填写即为下游唯一口径。

> 字段映射：模板三段 `Opus的…` 中——`对问题的分解` 与 `最终回答（=推荐路线）` 由 Opus 以**提问人**身份填写；`对GPT推荐线路的分析` 因无 GPT 标 N/A。

### gate ↔ Q 编号映射

| gate | Q | 决策簇 | 主要门控的 phase / 工作项 |
|------|---|--------|---------------------------|
| G-F-1 | Q1 | 向量层真实性 | F5-02（vec0） |
| G-F-2 | Q2 | 向量层真实性 | F5-01（embedding） |
| G-F-3 | Q3 | 业务能力去桩范围 | F6-02/03/04/05/08（cleaners/providers/structurize/construct/scatter） |
| G-F-6 | Q4 | 业务能力去桩范围 | F3-05（restart 精细粒度） |
| G-F-4 | Q5 | 认证面 | F6-07（API key） |
| G-F-5 | Q6 | 认证面 | auth 密码兼容（§3.2 O3） |
| G-F-7 | Q7 | 修复方法论 | 全 phase（先红后绿铁律） |

---

## 1. 向量层真实性（决定 F5 体量与 RAG 是否真有意义）

### Q1 — vec0 真实接入 sqlite-vec，还是先显式 degraded？（来源：G-F-1 / part-cr-3.md G-CR3-02）

- **影响范围**：`packages/vector_sqlite_vec/{engine,schema,store}.py`；F5-02；部署运维（是否需在环境安装 sqlite-vec 扩展）。
- **为什么必须确认**：当前代码从不加载 sqlite-vec，`CREATE VIRTUAL TABLE ... USING vec0` 永远失败 → 静默退化成普通 `TEXT` 表 + Python 暴力 cosine 全表扫描（已实测）。"真接 vec0"需要运维侧装扩展 + 代码 `enable_load_extension`，"先 degraded"则保留暴力实现但必须 fail-loud 告警。两条路的工程量、性能、部署前提完全不同，且决定 F5-02 是 M 还是更大。
- **当前建议 / 倾向**：MVP 阶段先 **显式 degraded**（保留暴力 cosine，但退化路径必须 `logger.warning` 告警、且抽象出 `VectorIndex` 接口），生产化再接真实 vec0。
- **Reasoning**：这个问题之所以出现，是因为系统"看起来有向量索引"（schema 写了 vec0 虚拟表），实际从未生效却无人察觉——根因是退化是**静默**的。无论你选哪条路，**第一要务是让退化不再静默**（否则下次又被假绿）。推荐先 degraded 的理由有三：① 真接 vec0 引入"部署环境必须装 sqlite-vec 扩展"这一硬运维前提，在 MVP 阶段会拖慢迭代、且本地/CI 环境一致性难保证；② 暴力 cosine 在数据量小时**结果正确**（只是慢），对验证整条 RAG 链是否跑通已足够；③ 抽象出 `VectorIndex` 接口后，未来从暴力切到 vec0 是局部替换，不影响上层。如果不拍板：F5-02 无法定型，且 closure 不知道该把 vector gate 标成 "degraded" 还是 "done"。
- **Opus 的问题分解**：
  - 子选项 A：MVP degraded（暴力 cosine + 强制告警 + `VectorIndex` 抽象），生产再接 vec0。
  - 子选项 B：本轮直接接真实 vec0（声明部署装扩展 + `enable_load_extension` + load）。
  - 子选项 C：degraded 但**连暴力 cosine 都先不优化**，只保证语义正确性测试能过（最省），性能债显式记账。
  - 共同硬约束（无论选哪个）：退化/降级路径必须 fail-loud（禁止静默），且 closure 据实定级。
- **Opus的对GPT推荐线路的分析**：`（本轮无 GPT second opinion，N/A）`
- **Opus 的推荐路线（最终回答）**：选 **A**。先 degraded + 强制告警 + `VectorIndex` 接口抽象；把"接真实 vec0"作为生产化阶段的独立工作项延后。这样 F5-02 收敛为"消除静默退化 + 接口化"的 M 级工作，不被运维前提绑架。
- **问题**：vec0 是否本轮就接真实 sqlite-vec 扩展，还是先做"显式 degraded（暴力 cosine + 强制告警 + 接口抽象）、生产化再接 vec0"？如果选 degraded，请确认接受"检索性能在数据量增大后线性劣化"这一显式技术债。
- **业主回答**：owner 同意 opus 的推荐路线。**裁决=选项 A**：本轮先 degraded（保留暴力 cosine + 退化路径强制 `logger.warning` 告警 + 抽象 `VectorIndex` 接口），生产化阶段再接真实 vec0；**接受**"检索性能随数据量线性劣化"为显式技术债。

### Q2 — 真实 embedding provider 选型 + 是否容许外部网络调用？（来源：G-F-2 / part-cr-7.md G-CR7-01）

- **影响范围**：`packages/rag_vectorizer/embedder.py`；F5-01；整条 RAG 检索的语义有效性；测试策略；运行成本/外部依赖。
- **为什么必须确认**：当前 `embed_text` 用 SHA-256 哈希生成伪向量，与文本语义**零关联**（已实测）——这意味着即便其他全修好，检索返回的也只是哈希噪声。要让 RAG 真正有意义，必须接入真实 embedding。但"真实 embedding"有三条路（外部 API / 本地小模型 / 仍 mock 但显式标注），各自的成本、网络依赖、测试可复现性、与 legacy（Workers AI）的对齐度都不同，必须业主定。
- **当前建议 / 倾向**：用 `Embedder` adapter 接口隔离；**默认接本地小模型**（如 sentence-transformers 类，离线、无计费、可复现）；测试用确定性 mock 但**显式标注为非交付向量**。
- **Reasoning**：问题根源是交付了一个"占位实现"却没标注，导致它被当成真功能。选型的核心权衡是"语义质量 vs 依赖/成本/可复现性"：① 外部 API（OpenAI/Gemini）语义最好，但引入网络依赖、计费、密钥管理，且测试不稳定（每次调用要么花钱要么 mock）；② 本地小模型语义够用、离线、零计费、测试可复现，代价是模型体积和首次加载；③ 继续 mock 则等于不修。推荐本地小模型，是因为它在"让 RAG 真有意义"和"不绑架测试/部署"之间最平衡，且 adapter 接口让未来切外部 API 只是换实现。如果不拍板：F5-01 无法选型，且 search 的语义测试（F5-04）无法定义"什么算命中"。
- **Opus 的问题分解**：
  - 子选项 A：本地小模型（默认离线，adapter 接口，测试用标注 mock）。
  - 子选项 B：外部 API（OpenAI/Gemini，语义最佳，需密钥 + 计费 + 网络）。
  - 子选项 C：adapter 接口 + **可配置后端**，默认本地、生产可切外部（A 的超集，工程量略大）。
  - 维度约束：当前 schema 硬编码 `embedding_dimension=1536`（CHECK + vec0 float[1536]）——选的模型维度必须是 1536，或需同步改 schema（牵动 F4/迁移）。**这是选型的隐藏约束，务必一并考虑。**
- **Opus的对GPT推荐线路的分析**：`（本轮无 GPT second opinion，N/A）`
- **Opus 的推荐路线（最终回答）**：选 **A**（若希望生产灵活则选 C）。本地小模型 + adapter；并**优先选 1536 维模型**以免触动 schema 硬编码；测试用确定性 mock 但断言语义相关性时用真实小模型跑少量样本。
- **问题**：embedding 用哪条路——本地小模型（默认离线）/ 外部 API / adapter+可配置后端？如果确认，请同时回答：是否要求所选模型维度=1536（以避免改动 schema 的 `embedding_dimension` 硬编码与 vec0 维度）？
- **业主回答**：owner 同意 opus 的推荐路线。**裁决=选项 A**：用 `Embedder` adapter 接口隔离，默认接**本地小模型**（离线、零计费、可复现）；**要求所选模型维度=1536**，避免触动 schema `embedding_dimension` 硬编码与 vec0 维度；测试用确定性 mock 但显式标注为非交付向量、语义相关性断言用真实小模型跑少量样本。

---

## 2. 业务能力去桩范围（决定 F6 是数天还是数周）

### Q3 — clean/rag 执行器去桩范围：全量复刻 legacy 还是增量限定？（来源：G-F-3 / part-cr-6.md、part-cr-7.md）

- **影响范围**：F6-02（universal cleaner）、F6-03（dedicated provider）、F6-04（structurize）、F6-05（construct）、F6-08（scatter/child files）；整体工期（数天 vs 数周）。
- **为什么必须确认**：审查确认 clean/rag 执行器几乎全是桩——legacy ~17k 行能力（universal cleaner 的 htmlCrawl/browserFetch/browserPDF/Gemini 等 9 action、dedicated provider registry、structurizer 的 AI 结构化、constructor 的 summary+layer-json）在 Python 侧仅数十行真实算法。是"全量复刻 legacy 全部能力"还是"先支持有限 source 类型 + 显式声明降级"，直接决定 F6 是一周内能收还是数周的大工程，也决定哪些 source（url/PDF/API provider）在本轮能用。
- **当前建议 / 倾向**：**增量**——本轮先做 `file`（纯文本）+ `url`（HTML 抓取+清洗）两类 source、`structurize/construct` 的基础真实实现（非朴素分段，但不追 legacy 全部 AI 策略），dedicated provider 先做 1 个真实 ETL（chinatax）作样板，浏览器渲染/PDF/多 provider/scatter **显式声明为本轮不支持**并记账。
- **Reasoning**：问题出现的根因是上一轮把"占位桩"当成"已完成"。现在的真实风险是反向的——如果一口气全量复刻 legacy 17k 行，F6 会膨胀成数周的大工程，把整个 first-fixes 拖死。推荐增量的依据：① 端到端要先"语义上真能跑通一条最简链"（文本/HTML → 真实结构化 → 真实 embedding → 真实检索），证明架构成立，比一次性铺满所有 source 类型更重要；② 浏览器渲染、PDF 解析、多 provider 各自是独立的重依赖（playwright/pdf 库/各家 API），适合在基础链稳固后逐个增量；③ 关键是**把"不支持"显式写出来**（degraded 声明 + 测试跳过标注），而不是再次留桩装成完成。如果不拍板：F6 的 5 个 refine 工作项无法定规模，down stream action-plan 无法排期。
- **Opus 的问题分解**：
  - 子选项 A（增量，推荐）：file(文本)+url(HTML)+基础 structurize/construct+1 provider 样板；其余显式 degraded。约数天~1 周。
  - 子选项 B（全量）：复刻 legacy 全部 clean action + 全 provider + 完整 AI structurize + summary/layer-json + scatter。数周,引入 playwright/PDF/多 LLM 依赖。
  - 子选项 C（最小）：仅 file(文本)端到端真跑通,url/PDF/provider 全 degraded —— 最快验证架构,但能处理的真实输入极少。
  - 横切要求（无论选哪个）：凡"不支持"必须 ① 显式 degraded 声明 ② 测试用 `skip`/`xfail` 明确标注 ③ 不得留装成完成的桩。
- **Opus的对GPT推荐线路的分析**：`（本轮无 GPT second opinion，N/A）`
- **Opus 的推荐路线（最终回答）**：选 **A**。以"file+url 两类 source 的语义闭环"为本轮 F6 的交付定义,structurize/construct 做"真实但不追 legacy 全策略"的实现,provider/PDF/浏览器/scatter 显式 degraded 并记入下一轮。这样 F6 可控且端到端语义可验证。
- **问题**：clean/rag 去桩本轮做到哪——增量(file+url+基础结构化+1 provider,其余显式降级)/ 全量复刻 legacy / 最小(仅 file 文本闭环)？如果选增量或最小,请确认接受"被降级的 source 类型(如 PDF、浏览器渲染、多 provider)在本轮明确标注为不支持"。
- **业主回答**：owner 同意 opus 的推荐路线。**裁决=选项 A（增量）**：本轮交付 `file`(纯文本)+`url`(HTML 抓取+清洗)两类 source 的语义闭环 + `structurize/construct` 的真实(非朴素分段、但不追 legacy 全部 AI 策略)实现 + dedicated provider 先做 1 个真实 ETL(chinatax)样板；**确认接受** PDF/浏览器渲染/多 provider/scatter 在本轮显式标注为不支持(degraded 声明 + 测试 skip/xfail + 不留装成完成的桩)并记入下一轮。

### Q4 — restart 精细粒度：本轮做按失败阶段恢复，还是先 clean 全量重启？（来源：G-F-6 / part-cr-4.md G-CR4-05）

- **影响范围**：`workflow_core/restart.py`；F3-05；restart 的实际可用性。
- **为什么必须确认**：当前 restart 无论 workflow 失败在哪个阶段,**总是从 clean 头重跑**,且 `mode` 参数是死参(只写日志不影响行为)。legacy 支持按失败 step/阶段精细重启(recovery 模式)。是本轮就做精细重启,还是先接受"clean 全量重启"+ 文档声明,决定 F3-05 的规模。
- **当前建议 / 倾向**：本轮做 **recovery 模式**(按 run 的 `current_stage` / 最后失败 step 决定重启锚点),`force` 全量重启延后。
- **Reasoning**：问题根源是 restart 实现了一个粗糙版本却保留了 legacy 的完整参数面(mode/target_step_id),造成"看起来支持精细重启实则不支持"。权衡在于:① clean 全量重启对"在 rag 阶段失败的 workflow"意味着把已成功的 clean 阶段也重跑——浪费,且若 clean 不幂等还可能出错;② recovery 模式工程量不大(读 run 当前阶段 + 从对应 step 重排),但能避免上述浪费。推荐做 recovery 的理由是它和 F3 的"每 step 可 claim/重试/重启"语义一致,且规模可控(M)。如果不拍板:F3-05 悬空,且 restart 这个运维能力实际不可靠。
- **Opus 的问题分解**：
  - 子选项 A（推荐）：本轮做 recovery（按 current_stage/失败 step 锚点重启）,force 全量延后。
  - 子选项 B：先只修"clean 全量重启能真正生效"(即修 G-CR4-04 时间 bug 让被重启 step 能就绪)+ 文档声明只支持全量,精细重启延后。
  - 子选项 C：本轮做完整 mode 面(recovery + force_recovery + kickstart),对齐 legacy。
  - 注:无论选哪个,G-CR4-04(restart 写畸形 available_at 致 step 永不就绪)都必须先修 —— 否则 restart 任何模式都不生效。
- **Opus的对GPT推荐线路的分析**：`（本轮无 GPT second opinion，N/A）`
- **Opus 的推荐路线（最终回答）**：选 **A**。先确保 restart 真能生效(修 available_at),再做 recovery 模式按阶段锚点重启;force/kickstart 全量面延后。与 F6 增量策略同节奏。
- **问题**：restart 本轮做到哪——recovery 模式(按失败阶段恢复)/ 仅修复 clean 全量重启使其生效 + 声明 / 完整对齐 legacy mode 面？
- **业主回答**：owner 同意 opus 的推荐路线。**裁决=选项 A**：先修 G-CR4-04(restart 写畸形 available_at 致 step 永不就绪)使 restart 真能生效，再做 **recovery 模式**(按 run 的 `current_stage`/最后失败 step 决定重启锚点)；`force`/`kickstart` 全量面延后，与 F6 增量策略同节奏。

---

## 3. 认证面（contract surface 决策）

### Q5 — 团队 API key 认证是否纳入本轮？（来源：G-F-4 / part-cr-5.md G-CR5-01）

- **影响范围**：`packages/auth` + `apps/api` + `api_keys` 表；F6-07；对外认证 contract surface。
- **为什么必须确认**：`api_keys` 表零访问——团队 API key 认证整簇缺失,legacy 有 `validate_api_key` + `findTeamByApiKeyHash` 全链路。当前所有端点仅靠 session-token 鉴权(可用,但缺 API key 这类"程序化/集成"认证方式)。是否本轮补,决定 F6-07 是否启动,也影响对外集成能力。
- **当前建议 / 倾向**：**纳入本轮**(实现 API key 校验中间件 + create_api_key),因为 legacy 已有、属认证完整性。
- **Reasoning**：问题根源是 schema 定义了 `api_keys` 表但没有任何代码读写它。权衡:① 若产品近期需要"外部系统用 API key 调用"(集成/自动化),则缺它是硬伤,且越晚补越要改认证中间件;② 若近期只有人工 session 登录场景,可延后。推荐纳入的理由是认证面属于"早定早稳"的 contract surface,后期插入认证维度容易牵动所有端点。如果不拍板:F6-07 悬空,且若产品后续要集成会返工。
- **Opus 的问题分解**：
  - 子选项 A（推荐）：本轮纳入(API key 校验 + create + team 归属),补齐 legacy 认证面。
  - 子选项 B：延后,本轮仅 session-only;在 docs 显式标注 api_keys 表为"预留未接线"(避免再被当成已实现)。
  - 关联:与 Q6(密码兼容)同属认证面,建议一并裁决以稳定 auth contract。
- **Opus的对GPT推荐线路的分析**：`（本轮无 GPT second opinion，N/A）`
- **Opus 的推荐路线（最终回答）**：倾向 **A**,但**取决于产品是否近期需要程序化集成**——若纯人工登录场景且时间紧,B(延后 + 显式标注)也可接受,关键是不再留"装成实现的零访问表"。
- **问题**：团队 API key 认证本轮是否纳入(实现校验 + create_api_key)？如果延后,请确认同意"在 docs 显式标注 api_keys 为预留未接线",避免再次被误判为已实现。
- **业主回答**：owner 同意 opus 的推荐路线。**裁决=选项 A（本轮纳入）**：实现 API key 校验中间件 + create_api_key + team 归属，补齐 legacy 认证面（F6-07 启动）。

### Q6 — 是否保留 legacy 密码兼容？（来源：G-F-5 / part-cr-5.md G-CR5-03）

- **影响范围**：`packages/auth/service.py`；§3.2 O3；老用户登录能力。
- **为什么必须确认**：审查发现密码哈希与 legacy 不兼容,但代码里有"legacy 兼容"的声明(不成立)。是否需要让 legacy 系统迁移来的老用户用旧密码登录,决定要不要实现 legacy 哈希解析回退;若不需要,应删掉那段不成立的兼容声明。
- **当前建议 / 倾向**：**不保留**(新系统无 legacy 用户迁移需求),删除不成立的兼容声明,统一用 PBKDF2。
- **Reasoning**：问题根源是代码声称兼容 legacy 密码但实现是错的。权衡很简单:① 如果有真实的 legacy 用户库要迁移过来登录,就必须正确实现 legacy 哈希(hmac-sha512 解析)的回退验证;② 如果是全新系统/无存量用户,这段兼容是纯负担且是错的,应删除。推荐不保留,因为 smind-family 是重构新系统,大概率无存量密码需迁移。如果不拍板:auth 留着一段"声称兼容但实际不兼容"的死代码,误导后续。
- **Opus 的问题分解**：
  - 子选项 A（推荐）：不保留,删兼容声明,统一 PBKDF2。
  - 子选项 B：保留,正确实现 legacy 哈希回退验证(仅当有存量用户需迁移)。
  - 判定依据:**是否存在需要迁移登录的 legacy 用户库**——这是纯事实问题,业主一句话可定。
- **Opus的对GPT推荐线路的分析**：`（本轮无 GPT second opinion，N/A）`
- **Opus 的推荐路线（最终回答）**：选 **A**(除非确有 legacy 存量用户要迁移登录)。
- **问题**：是否存在需要用旧密码登录的 legacy 存量用户？如果没有,确认"不保留 legacy 密码兼容、删除该声明、统一 PBKDF2"；如果有,则改为正确实现 legacy 哈希回退。
- **业主回答**：owner 同意 opus 的推荐路线。**裁决=选项 A（不保留）**：无需迁移登录的 legacy 存量用户；删除不成立的 legacy 密码兼容声明，统一 PBKDF2。

---

## 4. 修复方法论（贯穿全 phase 的执行纪律）

### Q7 — 修复期间是否采用 test-first（先红后绿）？（来源：G-F-7 / part-cr-8.md G-CR8-01/02）

- **影响范围**：全部 F1–F7 phase；F7 测试重建；执行节奏；验收标准。
- **为什么必须确认**：上一轮的根本教训是"测试结构性假绿"——20 个测试全是弱断言/桩固化/夹具掩盖,让全部 blocker 显绿通过。修复这些 blocker 时,如果不强制"每个修复先有一条在当前 HEAD FAIL、修复后 PASS 的回归",极可能再次出现"改了但没真验证"。是否把 test-first 设为铁律,影响每个 phase 的退出判据和节奏。
- **当前建议 / 倾向**：**采用**(先红后绿铁律,见 planning §4)——每个 blocker 修复前先写一条能复现该 bug 的测试(当前必须红),修复后转绿,作为该工作项的退出证据。
- **Reasoning**：问题之所以出现,正是因为上一轮测试无法证明任何正确性(假绿)。test-first 在这里不是教条偏好,而是**针对"假绿"这一具体病因的对症措施**:一条"修复前必须红"的测试,能同时证明 ①bug 真实存在(红)②修复真的有效(绿)③未来不回归(留作回归)。代价是前期写测试稍慢,但相对"改完不知道有没有真修好、下次又假绿"的返工,这点成本可忽略。如果不拍板:F7 的测试重建缺乏强制纪律,可能又退化成事后补几个弱断言。
- **Opus 的问题分解**：
  - 子选项 A（推荐）：全 phase test-first 铁律(每 blocker 先红后绿,作退出证据)。
  - 子选项 B：仅对 critical blocker 强制 test-first,其余事后补测。
  - 子选项 C：不强制,沿用事后补测(风险:重蹈假绿)。
  - 附加纪律(无论选哪个):F7 前禁止新增"手写正确数据绕过被测路径"的夹具;CI 加断言强度门禁(禁止仅 status==200/!="" 作唯一断言)。
- **Opus的对GPT推荐线路的分析**：`（本轮无 GPT second opinion，N/A）`
- **Opus 的推荐路线（最终回答）**：选 **A**。这是直接针对上一轮假绿病因的纪律,成本低、收益高,且让每个 phase 有客观、可复现的退出证据。
- **问题**：修复期间是否设"先红后绿"为全 phase 铁律(每个 blocker 修复以"先红后绿回归测试"为退出证据)？如果只想对部分强制,请指明范围(如仅 critical)。
- **业主回答**：owner 同意 opus 的推荐路线。**裁决=选项 A（全 phase 铁律）**：每个 blocker 修复以"先红后绿回归测试"(当前 HEAD FAIL、修复后 PASS)为退出证据；F7 前禁止新增"手写正确数据绕过被测路径"的夹具；CI 加断言强度门禁(禁止仅 status==200/!="" 作唯一断言)。

---

## 5. 裁决后续动作

- 业主在以上 7 题 `业主回答` 填写后,本 QNA 即可冻结;Opus 据此把 `proposed → final`:§7.A 的 7 个 OPEN gate 转为 §7.B gate-closure map(每 gate 绑定对应 Q 的裁决),并把 F1–F7 phase 1:1 派生为下游 action-plan(planning §10.A)。
- 关键依赖提示:**Q1+Q2 决定 F5、Q3+Q4 决定 F6/F3-05 体量** —— 这四题是工期与范围的主要杠杆,优先裁决。
