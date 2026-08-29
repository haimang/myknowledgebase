# new-harvest — Pre-initial-planning · Progressive Owner-Gated Q&A

> **项目**：`myknowledgebase`（MKB）
>
> **范围（scope）**：`new-harvest`（intake 四域清洗通道：`pdf` / `web` / `doc` / `api`）。本文件只冻结 **foundational** 真相，供后续 `planning-initial` CITE。不冻结 PDF 库、浏览器二进制、charset 合同版本号、实验发车日、workflow 步骤命名等执行细节。
>
> **qna 位点**：`pre-initial-planning`
>
> **角色配置**：提问 `Grok` · second-opinion `none` · 裁决 `owner`
>
> **second-opinion 模式（逐轮）**：本 campaign **全程 `retired`**
>
> **方法约束**：`.adocs/templates/qna-progressive.md`；每轮恰好 3 个 foundational 问题；下一轮仅由中场评估按已冻 `T-O` 注入。Round 1–3 均已冻结。Round 4 foundational **不注入**（业主整包接受 Round 3 推荐包装，见 §8 / 中场评估 III）。
>
> **上游架构真相**：`T-O-42` / `S05-T001..T003`（`T-O-49..51`）/ D08-T002·T004·T006 / `T-O-340` / S03 图 route / S04 唯一 acceptance / NS1–NS9 围栏
>
> **词汇权威**：`docs/baseline/spec-glossary.md`
>
> **工作笔记（非 Truth）**：
> - [`initial-thoughts-by-grok.md`](initial-thoughts-by-grok.md)（v0.3）
> - [`initial-thoughts-by-GLM53f.md`](initial-thoughts-by-GLM53f.md)（v0.1）
> 与本文件冲突时以 **本文件业主答复** 为准。v0.1 本题 Q1 推荐 B（「诚实未部署」）**已被业主否决**，不得再当倾向。
>
> **下游消费者**：`planning-initial` §2（仅 CITE 已冻 `T-O`）
>
> **文档状态**：`frozen`（Round 1–3 全轮冻结；无 OPEN 残题；Round 4 foundational 不注入）
>
> **版本 / 日期**：`v0.5 / 2026-08-29`

> **★ 本 Campaign 证据授权**  
> 1. 已接受 baseline（`docs/baseline/**`；D08 Appendix A 不得当今日绿灯）。  
> 2. HEAD 代码事实。  
> 3. `context/legacy-family/` 仅 ReferenceAnchor（`T-O-42`）。  
> 4. **业主 2026-08-29 口径**：Round 1 整包接受推荐冻结为 `T-O-376` / `T-O-381..383`；Round 2 整包接受推荐冻结为 `T-O-384..386`；Round 3 整包接受推荐冻结为 `T-O-387..389`。本文件 foundational QNA **收口**。

> **Owner-originated application boundary（继承 `T-O-42` / `S05-T003`）**：不搬 SMCP / R2 / D1 / Cloudflare Browser / Gemini-on-Workers。吸收语义与纪律，不是栈。

> **Progressive 纪律**：
> 1. 提议围栏可由已冻 Truth **唯一推导**；**completeness 谓词不再 internally 默认**——以业主 2026-08-29 口径为准，由 Q1 正式冻结。  
> 2. Round 1 只问冻结该口径后仍不可默认的 foundational 分叉。每题四元组：详细解读 / 方案清单 / 推荐说明 / 证据与反证。  
> 3. 推荐只钉产品法，不写库选型 / DAG / 测试文件名。  
> 4. 业主回答前不登记该题新 `T-O`。  
> 5. Truth-ID 自 `T-O-376` append-only。  
> 6. 无 second-opinion 栏。  
> 7. Round 3 由中场评估 II 注入并已冻结（`Q7–Q9` → `T-O-387..389`）。Round 4 foundational **确认不注入**。

> **Truth-ID 连续性**：NS1=`337..352`；NS2=`353..361`；NS4=`362..375`；本文件提议围栏自 **`T-O-376`**。v0.1 对 `T-O-376` 的「NH 不做到向量」**作废**，由本节重写。

> **v0.1 作废声明**：v0.1 Q1-A/B（接线完整 / 主路径诚实 + 允许未部署）与业主心理预期相悖。其后 Q2「admission 冻死 process_key、LLM 可继续选不中」、Q3「缺端口 503 当产品法」均建立在错误 completeness 上，**整组作废**。v0.2 重问。

---

## 0. 分轮状态总览

| 轮次 | 题号 | 层级 | 单一焦点 | second-opinion | 状态 |
|------|------|------|----------|----------------|------|
| Pre-round fence | — | foundational | 战役身份、零 legacy 栈、三轴坐标、实验发车日不进本文件 | `retired` | `frozen / T-O-376..380 · 随 Round 1 一并确认` |
| Evidence review | — | evidence | 业主口径 × HEAD 缺口闭集 | `retired` | `completed / 2026-08-29` |
| **Round 1** | `Q1–Q3` | foundational | **live 闭集**；**动态路由权威**；**全链路失败/幂等/竞态法** | `retired` | `frozen / T-O-381..383 · owner 接受推荐 B/B/A · 2026-08-29` |
| Mid-review I | — | truth formation | 评价 Round 1；注入 Round 2 | `retired` | `completed / 2026-08-29` |
| **Round 2** | `Q4–Q6` | foundational | **声明式图如何承载晚绑定**；**上传身份 vs S13**；**promptA 与四通道 clean 合同** | `retired` | `frozen / T-O-384..386 · owner 接受推荐 A/A/A · 2026-08-29` |
| Mid-review II | — | truth formation | 评价 Round 2；注入 Round 3 | `retired` | `completed / 2026-08-29` |
| **Round 3** | `Q7–Q9` | foundational | **图基数（几张 immutable revision）**；**晚绑定信封是否含再获取**；**FilterMeta 与 g0 分账** | `retired` | `frozen / T-O-387..389 · owner 接受推荐 A/A/A · 2026-08-29` |
| Mid-review III | — | truth formation | 评价 Round 3；全量冲突审查；收口 | `retired` | `completed / 2026-08-29` |
| Round 4 foundational | — | — | **确认不注入**（推荐包装已接受，见 §8） | — | `not-injected / closed` |
| 收口 | — | freeze | 全轮 foundational 冻结；交接 planning-initial | `retired` | `frozen / 2026-08-29` |

Round 1 业主整包接受推荐：**Q1-B / Q2-B / Q3-A**。  
Round 2 业主整包接受推荐：**Q4-A / Q5-A / Q6-A**。  
Round 3 业主整包接受推荐：**Q7-A / Q8-A / Q9-A**。

---

## 1. ★ Truth-Gate 台账（append-only）`[核心·锁死]`

> **已冻结（2026-08-29）**。Round 1–3 业主整包接受推荐。本 campaign foundational 台账 **收口**。planning-initial §2 可 CITE 本表。号码 append-only；推翻须本文件修订并新 append。

| Truth-ID | 子类型 | 已锁定真相（一句话） | 来源 | 驱动了哪些后续题 | 下游约束 |
|----------|--------|----------------------|------|------------------|----------|
| `T-O-376` | `foundational / completeness` | **new-harvest completeness = 四通道全部接通，禁止「诚实未部署」。** 每条 in-scope 路径必须用真实文件走真实 intake、真实 Process，并产出真实、可检索的向量。公共 Task/Team/检索等 API 可调用；Intake 生命周期 CRUD 到位；对象上传到位；失败幂等与竞态落地；边缘场景可测；路由可动态配置；unit + e2e 覆盖该闭集。NH **不重写** cuts/g0 算法，但 **必须把每条接通路径送到现有 publication/retrieval 链**。0815-R7 的 inline 4/4 **不**算四通道接通。 | 业主 2026-08-29；Round 1 一并确认 | Q1, Q4–Q9 | 禁止再把 503 当通道 DoD |
| `T-O-377` | `foundational / fence` | 继承 `T-O-42` / `S05-T003`：零 Cloudflare/R2/D1/SMCP runtime。source kind 仍只有四类（`S05-T002`）。`intake/` 是变换 SSOT（D08-T006）。禁止 `action_branch` taxonomy。 | 已冻 Truth；Round 1 一并确认 | Q4, Q5, Q7 | 接通 ≠ 搬 Worker 栈 |
| `T-O-378` | `foundational / honesty` | PDF 字面量扫描不得称已落地；无层今日死在 decode 且盗用 OCR 码；e2e monkeypatch 不是接线；空 `clean_text` 不是成功。 | HEAD；Round 1 一并确认 | Q4, Q6, Q8 | 假实现必须在 NH 内换成真路径。decode 观察法见 `T-O-388`（本条是 HEAD 谎言清单，不是「decode 必须失败」） |
| `T-O-379` | `foundational / three-axis` | 坐标仍是 `source_kind × acquire × clean_strategy`（API 再 × provider/operation/version）。**不得**让调用方点名 `workflow_key`。 | S05 §1.3；`workflow_registry.py:86-88`；Round 1 | Q4, Q7, Q8 | 动态路由不得等于开放 workflow_key。取值时刻：kind 选图（`T-O-387`）；acquire 为起点+可再获取（`T-O-388`）；strategy 晚绑定（`T-O-382`/`384`） |
| `T-O-380` | `foundational / experiment-schedule` | unit/e2e 属于 completeness。**.experiment 发车日**仍不在本文件冻结。 | 业主原四目标第 4 条；Round 1 | — | 发车日延期见 §10.2，不构成本文件 OPEN 残题 |
| `T-O-381` | `foundational / live-matrix` | **Q1-B。** live 闭集 = 10 个 `CleanStrategyKey` + `clean.map.registered_api` 三 operation，均须真实文件/URL/冻结 records 走到可检索向量。含 `web.llm_rewrite`、browser acquire、真 PDF 文本层、`pdf.document_understanding`/`pdf.ocr`、`web.browser_print_pdf`、`doc.document_understanding`/`doc.ocr`/`doc.vision`。公共 **对象上传** 必须落地。Task 七意图纳入。禁止未部署 503 收口任一 in-scope 策略。不含 live 供应商爬虫、第五 source kind、cuts 重开、前端。 | Round 1 / Q1 · owner 接受 B · 2026-08-29 | Q4, Q5, Q6, Q7, Q9 | 公开选图闭集必须覆盖该矩阵 |
| `T-O-382` | `foundational / late-bind` | **Q2-B。** 清洁工人在 **真实表示已知之后** 按 **可配置闭集规则** 绑定；绑定结果进 evidence 与后续 digest。调用方仍不能点名 `workflow_key`。禁止无证据暗升。此为绑定前的显式决策，不是 `T-O-340` 意义上的静默换工人。绑定之后适用 `T-O-383`。 | Round 1 / Q2 · owner 接受 B · 2026-08-29 | Q4, Q7, Q8 | 与 S03 七表共存的落地形态由 `T-O-384` 钉死 |
| `T-O-383` | `foundational / fail-loud-after-bind` | **Q3-A。** 路由一旦绑定工人，该 Execution **不再换**清洁工人。内容失败 = 显式失败、**不出向量**。同一 Task 指纹重放返回原视图；变则冲突。同一 intake 键 + 同 digest = replay（指针必须解析）。并发 = typed ConflictError。空正文不是成功。上传必须服从同一套幂等/冲突法。 | Round 1 / Q3 · owner 接受 A · 2026-08-29 | Q4, Q5, Q8 | 「路径能出向量」≠「每个坏文件必须出向量」 |
| `T-O-384` | `foundational / declarative-late-bind` | **Q4-A。** 晚绑定住在 **同一 immutable Workflow revision**：该 revision **预声明** Q1 闭集里全部 live clean 边（一张，或按 source kind 有限几张——**张数由 Q7 钉**）。表示已知之后，仅用 **已登记** guard/control 选择其中一条。`s05_binding_digest` 在 **选边 Outcome 提交后** 封闭；同 Execution retry/recovery **不热切图**。禁止 handler 或表外策略包暗调未出现在本 revision 的 `process_key`。不是 `T-O-340` 静默换工人，也不是 decode 后再 resolve 另一张 revision。 | Round 2 / Q4 · owner 接受 A · 2026-08-29 | Q7, Q8 | 张数已由 `T-O-387` 钉为 kind 家族。守卫谓词可扩展登记，不得自由表达式（`S03-T012`）；图必须无环（`S03-T011`） |
| `T-O-385` | `foundational / upload-identity` | **Q5-A。** 公共上传只创造 **S13 handle + digest + size**（对 S13「无公网 object API」的 **窄 reopen**：受鉴权 Port 暴露，对象存在仍 ≠ 业务成功）。**不**创造 IntakeSource/Item/Revision。随后必须另一次 `intake.ingest` + `local_object`。同一 team、同一 sha256+size → replay 同一 handle。无 ingest 的对象按 S13 orphan/GC。purpose 须进入闭集，**字符串本身不在本文件冻结**。 | Round 2 / Q5 · owner 接受 A · 2026-08-29 | — | 上传幂等服从 `T-O-383`；S04 身份仍只由 acceptance 产生 |
| `T-O-386` | `foundational / clean-contract` | **Q6-A。** 不论通道，S06/g0 只消费 **一份** admitted clean body（非空、content digest、strategy/capability evidence）。g0 original **必须等于** 该 body。promptA 仅 `llm_required=True` 的策略强制进入 binding；确定性策略与 `clean.map.registered_api` **不**调用模型，但 **仍是 clean**。这是对 `T-O-210` 的 **窄执行解释**（第一环=得到 admitted clean，模型子环仅 LLM 策略），不是废除 handbook，也禁止为通道另写 structurize kernel。 | Round 2 / Q6 · owner 接受 A · 2026-08-29 | Q9 | FilterMeta/ContextMeta 不得塞进 g0；分账已由 `T-O-389` 钉 |
| `T-O-387` | `foundational / graph-cardinality` | **Q7-A。** 选图键是四类 `source_kind`。三张 single-root 图：`inline_payload` / `local_object` / `http_resource`；`registered_api` **维持** scatter_root + scatter_child，不并入 mega。每张 kind 图预声明该 kind **全部** live clean 边及该 kind 合法 acquire/decode 边。`acquisition_mode` / `media_type` **不再选图**（图内起点或探测事实）。调用方仍不能点名 `workflow_key`。配置变更 = 新 revision + guarded pointer（`S03-T007`）。闭合 `T-O-384` 括号。 | Round 3 / Q7 · owner 接受 A · 2026-08-29 | — | 非法跨 kind 边不画。今日选不中的 5 张图必须并进对应 kind revision |
| `T-O-388` | `foundational / reacquire-envelope` | **Q8-A。** `acquisition_mode` 是 **起点边**，不是唯一允许跑过的 acquire。绑定清洁工人 **之前**，同一 revision 可走 **有限条已声明、无环、正向** 的再获取；每个已声明 acquire 步骤至多成功一次，写入 acquisition evidence。decode 是观察器：无文本层 → typed 事实，**禁止**再抛 `CLEAN_OCR_CAPABILITY_UNAVAILABLE` 冒充 OCR 未部署。print_pdf 必须诚实产出 `representation_kind=print_pdf` 且 bytes 为 PDF。清洁工人仍只绑一次，之后 `T-O-383`。`s05_binding_digest` 在 **清洁边选定后** 封闭，覆盖实际走过的 acquire 路径。禁止无证据暗升与 try-all-acquire。 | Round 3 / Q8 · owner 接受 A · 2026-08-29 | — | 依赖 `T-O-387` 的 kind 图（http_resource 含 static/browser/print 边）。不是 `S03-T011` 业务环，也不是 `T-O-340` 静默换工人 |
| `T-O-389` | `foundational / semantic-ledger` | **Q9-A。** g0 original **只等于** `T-O-386` 的 admitted clean body，禁止把 FilterMeta 序列化进 `clean_text`/g0。FilterMeta 五维（`realm,type,channel,source_name,is_active`）+ context tags 作为 **S04 revision semantics** 对 **四通道强制**。S06 layered `context_meta` 读 revision 语义，不从 g0 解析。web/pdf/doc 不得以 `{"source_kind"}` stub 冒充五维；缺五维不得 pretend acceptance-complete。值的派生算法（调用方 typed 元数据 / 闭集派生）**本文件不锁**。不重开 cuts。 | Round 3 / Q9 · owner 接受 A · 2026-08-29 | — | 扩展 D08-T007 到四通道，不废除 API 样板；对齐 `T-O-62` 三账本 |

本 campaign foundational 续号止于 `T-O-389`。不再为 Round 4 预留。

---

## 2. 证据审查（ReferenceAnchor · 非 Truth）

### 2.1 业主口径如何推翻 v0.1

| v0.1 说法 | 业主 2026-08-29 | 后果 |
|-----------|-----------------|------|
| Q1-B：browser/OCR/LLM「允许诚实未部署」 | **不存在任何诚实未部署的空间** | Q1 必须重写；503 不再是通道收口 |
| Q1-B：NH 主路径停在 clean | **真实 process + 真实 vector** | completeness 含现有 structurize→publication 走通，不是重开 cuts 设计 |
| Q2-A：admission 冻死 key，闭集外图可继续不可选 | **全部接通 + 路由可动态配置** | 7-key 闭集与硬编码选图不再够 |
| Q3-A：缺端口 503 当产品法 | 端口必须在；失败是文件/竞态/幂等，不是「没部署」 | Q3 从「未部署」改为「全链路失败法」 |
| 公共 API「已够」 | **全部 API 可调用、CRUD 完整、文件上传落地** | 缺对象上传端点 = completeness 缺口，不是 OOS |

### 2.2 HEAD 对照：业主口径下的缺口闭集（Q1 的分母）

**清洗策略 10 键**（`src/contracts/intake/strategies.py:15-25`）：`web.deterministic` / `web.llm_rewrite` / `web.browser_print_pdf` / `pdf.text_layer` / `pdf.document_understanding` / `pdf.ocr` / `doc.deterministic` / `doc.document_understanding` / `doc.ocr` / `doc.vision`。另加 API `clean.map.registered_api`（三 operation）。

**公开选图只有 7 键**（`src/workflows/lsrag_definition.py:929-940`）：inline / local / local-pdf / local-image / http-static / http-browser / http-pdf。`config_snapshots.py:504-516` 只认 `acquisition_mode ∈ {static,browser,pdf}`。  
**已 bootstrap 但选不中**（同文件 `1003-1054`）：vision / doc-llm / web-llm / pdf-llm / print-pdf。

**组合根未注入**（`api/app.py:332-345`）：有 `http_fetcher`、`claude_cli`；**无** `browser_fetcher`、`clean_llm`。OCR/Vision 不是独立引擎，而是同一 LLM 端口（`intake/pdf/__init__.py` / `intake/doc/__init__.py`）。

**PDF 主路径是假实现**（`src/runtime/intake/types.py:144-158`）：`local-pdf-literal-text.v1`；无字面量 → decode 抛 `CLEAN_OCR_CAPABILITY_UNAVAILABLE`，到不了 `clean.ocr.local`。

**print-pdf 死键**（`acquisition_ingest.py:535-536` 只写 `rendered|transferred`；`clean_preflight.py:46-62` 要 `print_pdf`）。

**HTTP 无 image profile**（`config_snapshots.py:504-506`）：静态 URL 返回 PNG 仍会走 `http_resource.static` → `clean.extract.web`。

**对象上传：公共 API 不存在。** `api/public/routes.py` 有 Team/Task/gate/retrieval/generation-artifact 读面；**零** `/objects` 或 upload。README §6.1：`local_object` 需要已存在 handle，「公共 API 没有对象上传端点」。`ObjectStorePort.promote`（`src/storage/ports.py:12`）仅内部/测试注入。业主「文件上传全部落地」= **净新公共面**，否则 pdf/doc 的 local_object 路径无法被外部用真实文件打到向量。

**Task 意图面已登记**（`src/contracts/api/models.py:278-286`）：`intake.ingest` / `rebuild` / `update_metadata` / `deactivate` / `reactivate` / `delete` / `index.rebuild`。Team CRUD + Task create/get/patch/delete/cancel/retry + gate decide + retrieval 已在 `api/public/routes.py`。业主「CRUD 完整」= 这些意图对 **四通道真实对象** 全走通并测到，而不是再发明第七意图。

**幂等/竞态已有内核，未覆盖新路径。** Task 创建用 `creation_fingerprint` 双检（`task_create.py:70-104`）。Intake 同指纹 replay 刚修（NS9-FX2）。Gate 有 `idempotency_key`（`task_projections.py:313-319`）。L3 **禁止**覆盖 `workflow_key`（`config_snapshots.py:70-72, 794-795`）。今日 **没有** 可动态配置的清洁路由；`profile_id` 覆盖只认 `clean.web.v1` / `clean.document.v1` / `clean.default.v1`（`config_snapshots.py:56, 798-801`），与 `CleanStrategyKey` 闭集不对齐。

**e2e 现状。** `tests/e2e/test_source_capability_paths.py` 对 browser **monkeypatch** 端口；OCR 断言失败关闭。这与业主「真实文件 → 真实 vector」相反，不能当 NH DoD。

### 2.3 本轮不得重开

S03 八态、S04 十表 identity、四类 source kind、D08 三 provider 闭集、cuts/g0 拒绝谓词、`T-O-340` 禁 **静默** 换工人（显式、可配置的路由决策不是静默，见 Q2）。

### 2.4 口径冻结后仍开放的三轴

| 开放轴 | 为何不能 internally 默认 |
|--------|--------------------------|
| **live 闭集边界** | 「四通道全部接通」在代码里可指 7 个公开 profile、10 个 strategy、或再加 live 供应商。不钉闭集，规划会少做 print-pdf/vision/上传。 |
| **动态路由权威** | 业主要「路由可动态配置」。今日是硬编码 7-key。配置落在 descriptor / 策略表 / decode 后决策，三者产品法不同。 |
| **全链路失败与竞态** | 端口必须在之后，失败只剩内容/冲突/空结果。替代到另一策略直到出向量，还是绑定后 fail-loud，会改变「真实 vector」的含义。 |

---

## 3. Round 1 —— Foundational 三题（`Q1–Q3`）

> 本轮 second-opinion：`retired`。v0.1 同号题目作废。  
> **Round 1 状态**：Owner **整包接受推荐**（Q1=B，Q2=B，Q3=A）· 2026-08-29 · 已冻结 `T-O-381..383`（围栏 `T-O-376..380` 一并确认）。

---

### Q1 — 「四通道全部接通」的 live 闭集是什么

- **影响范围**：planning-initial 的 In/Out 整表；10 策略与 7 profile 的命运；对象上传是否本战役公共 API；completeness 是否含走到向量
- **为什么必须确认**：业主已否决「诚实未部署」。不把「全部接通」写成闭集，执行阶段会把 print-pdf、vision、上传、lifecycle 再偷成 OOS。
- **驱动输入**：提议 `T-O-376`；§2.2 缺口闭集

#### 对问题的详细解读

业主口径已经排除「主路径 live、其余 503」。本题不再问「要不要完整」，而问 **完整的外延**：哪些路径、哪些 API、哪些生命周期，算进 NH 必须 live-to-vector 的闭集。

「通道」在业主口中是 `pdf/web/doc/api`。在代码里它展开为：

- 10 个 `CleanStrategyKey` + `clean.map.registered_api`；  
- 4 个 source kind × acquire 模式（inline / local_object / http static·browser·pdf / registered_api）；  
- 图上已有但选不中的 LLM/print-pdf/vision；  
- 公共上传（今日缺失）；  
- Task 七意图 + Team/Task/gate/retrieval CRUD。

「真实 vector」= 该路径的 Task 能 `succeeded`，且 publication 后检索按 Layer A 打到本次产物。不是再设计 cuts。不是 0815 inline 格子冒充。

「全部 API 可调用」不是把内部 `promote` 继续当上传；`local_object` 没有公共写入面则 pdf/doc 真实文件进不来。

本题 **不**冻结上传协议字段、PDF 库、浏览器实现。

#### 可选的方案清单

| 选项 | 方案 | 含义（产品法） |
|------|------|----------------|
| **A** | **否决项：7 个公开 profile 接到向量即可** | 只接通今日 `_source_profile` 能选中的 7 条；LLM/print-pdf/vision 可继续选不中；上传可继续内部装载。**即 v0.1 Q1-A/B 的残骸，业主已否。** |
| **B** | **登记策略 × 四通道 × 公共面 全 live-to-vector（推荐）** | 闭集 = §推荐说明中的矩阵。每条必须真实文件（或真实 URL / 冻结 API records）走完整 Process 并产出可检索向量。对象上传成为公共 API。七个 Task 意图对四通道对象可调用。禁止任何 in-scope 策略以未部署收口。不含第五 source kind、不含三供应商实时爬取客户端（records 仍可由调用方提交，但通道本身必须 live）。 |
| **C** | **无上界** | 在 B 之上再含：live 税局/Domain/REA 连接器、新 source kind、任意站点登录/cookie。 |

#### 当前建议 / 倾向（Grok）

**推荐 B。**（不再推荐任何「未部署」变体。）

#### 推荐方案的详细说明

选 B 时，NH 允许声称「四通道已完整建设」当且仅当下列 **闭集** 均 live-to-vector（或对生命周期意图达到其产品终态）：

1. **web**：`web.deterministic`、`web.llm_rewrite`；`http_resource` 的 static 与 **browser** 获取。  
2. **pdf**：`pdf.text_layer`（**真解析**，禁止字面量冒充）、`pdf.document_understanding`、`pdf.ocr`；HTTP PDF 与 local PDF；`web.browser_print_pdf` 作为已登记策略必须可走通（含 acquire 诚实表示）。  
3. **doc**：`doc.deterministic`（text/html/plain）、`doc.document_understanding`、`doc.ocr`、`doc.vision`；local 文件经 **公共上传** 进入。  
4. **api**：chinatax / domain / realestate 三 operation 的 map → scatter child → 各 child 向量；空集/重复/坏 member 有类型化结局且不 silent skip。  
5. **公共面**：Team CRUD；Task 七意图；gate；retrieval；**对象上传/读取**（补今日缺口）；generation-artifact 读面保持。  
6. **测试**：闭集每条有 unit + **无 monkeypatch 默认进程** 的 e2e 走到向量（或生命周期终态）。  
7. **明确仍不是 B**：第五 source kind；供应商侧实时翻页爬虫；cuts 算法重开；前端。

#### 支持推荐 / 反对其他方案的证据与 Reasoning

- **反对 A**：与业主「不存在诚实未部署」直接冲突。HEAD 恰好是 A 的现状：7 键（`lsrag_definition.py:929-940`）+ 组合根不注入（`api/app.py:332-345`）+ 无上传（`api/public/routes.py` 无 objects）。选 A = 宣布 NH 已接近完成，与「完整建设」相反。  
- **反对 C**：把 D08 已删的隧道/cookie/sandbox 实打接回来，违反 `T-O-42`。业主要的是 **本系统** 四通道接通，不是变成三家网站的爬虫。  
- **B**：把业主句子翻译成可验收闭集，并覆盖 HEAD 真实缺口（选不中的 5 张图、假 PDF 层、死键 print-pdf、HTTP image、上传 API、LLM/browser 未注入）。「走到向量」用现有 `lsrag.vectorize` / `index.validate_publication` / `retrieval:search`（`api/public/routes.py:452`），不重开生成面设计。  
- **API records**：B 仍允许调用方提交冻结 records——这是通道契约，不是「未接通」。未接通的是 map 之后 child 必须真的 publish 向量，以及空/坏 member 不得假成功。

#### 问题（请业主裁决）

**Q1：四通道全部接通的 live 闭集选 A / B / C？若选 B，是否确认：10 个 CleanStrategyKey + registered_api 三 operation 均须真实文件/URL/records 走到可检索向量；公共对象上传必须落地；Task 七意图纳入；禁止再用未部署 503 收口任一 in-scope 策略；不含 live 供应商爬虫与第五 kind？**

- **业主回答**：接受推荐 **B** 全部确认句。→ **冻结为 `T-O-381`**（completeness 谓词同时确认 `T-O-376`）
- **裁决状态**：`accepted / frozen`

---

### Q2 — 全部策略均 live 之后，路由如何「动态配置」

- **影响范围**：descriptor 形状；profile 闭集；是否允许看见字节后再选策略；L3/overrides 能否碰清洁工人
- **为什么必须确认**：业主要求「所有边缘场景，路由可动态配置」。今日路由是硬编码 7-key，且禁 `workflow_key` 覆盖。全部接通后，扫描件 vs 文本 PDF、SPA vs 静态 HTML 必须有 **可配置** 的选择法，否则闭集 live 了调用方仍只能打中 7 条。
- **驱动输入**：提议 `T-O-376`（须 Q1 冻结）+ `T-O-379`；§2.2 选图与 L3 禁令

#### 对问题的详细解读

v0.1 Q2 问「要不要为了修选不中而推迟绑定」。那是建立在「部分策略可以不部署」上的。v0.2 前提是 **工人都在场**。剩下的 foundational 问题是：**谁、凭什么、在哪一时刻指定工人，以及这套规则能否配置。**

今日：

- 调用方只交 `source_kind` + `acquisition_mode` + 声明 `media_type`（`models.py:108-128`）。  
- 代码映射到一张图（`config_snapshots.py:492-516`）。  
- 调用方不能点名 workflow（`workflow_registry.py:86-88`）。  
- L3 把 `workflow_key` 列为 forbidden（`config_snapshots.py:70-72`）。  
- `profile_id` 覆盖与 strategy 表不对齐（`config_snapshots.py:798-801` vs `strategies.py:15-25`）。

「动态配置」合法读法有三：改登记表/配置而不改调用方；看见真实字节后按 **可配置规则** 选工人；调用方直接点策略。第三种打破 `T-O-379`。第一种配不了「有无文本层」（只在 decode 后知道，`types.py:144-158`）。第二种匹配边缘场景，但是否改 Execution 冻结时刻，必须业主钉。

本题不规定规则引擎实现、不规定是否单独加一个 Process 步骤。

#### 可选的方案清单

| 选项 | 方案 | 含义（产品法） |
|------|------|----------------|
| **A** | **Admission 仍冻 exact process_key；「动态」= 改代码拥有的 profile 登记** | 调用方表面仍是 kind/mode/media。要增加可达路径只能扩登记。看见字节后 **不得** 改工人。扫描件必须调用方一开始就走 OCR profile。 |
| **B** | **单一可配置决策：在表示已知之后绑定工人（推荐）** | Execution 保证清洁工人在 **表示（media/文本层水位/渲染结果）已知之后** 才绑定，绑定结果进 evidence 与后续 digest。决策规则 **可配置**（登记的策略表/策略包，不是调用方字符串、不是 handler 里无证据 if）。调用方仍不能点 `workflow_key`。配置可表达「无文本层 → pdf.ocr」「HTML 空壳 → browser」这类边缘。 |
| **C** | **调用方点名 clean_strategy / workflow_key** | 动态 = 每次请求指定工人。打破现行「不能点名图」与 L3 禁令。 |

#### 当前建议 / 倾向（Grok）

**推荐 B。**

#### 推荐方案的详细说明

选 B 时：

1. 全部策略 live（Q1-B）是前提：决策是在 **在场的工人里选**，不是选一个会 503 的名字。  
2. 绑定时刻晚于「真实表示已知」（decode / 文本层探测 / 已获取 HTML）。在此之前图可以只保证 acquire/decode。  
3. 规则是配置出来的闭集，变更有 version/digest，进 Execution 冻结事实；禁止无证据暗升（今日 `browser_profile: injected-browser-renderer.v1` 无论端口是否存在都会写上，`acquisition_ingest.py:535-536`，属反例）。  
4. 调用方仍然只交 typed source；不开放 workflow_key。  
5. 与 `T-O-340`：这不是静默换工人，而是 **尚未绑定工人之前的一次显式、可配置决策**。绑定之后适用 Q3。

#### 支持推荐 / 反对其他方案的证据与 Reasoning

- **反对 A**：与业主「路由可动态配置」「所有边缘场景」冲突。文本层有无不是调用方在 Task 创建时能诚实声明的（HEAD 用正则猜，`types.py:144-158`）。A 会迫使调用方猜 OCR vs text-layer，猜错则整链失败——在 Q1 已要求「真实文件得到真实 vector」的前提下不可接受。  
- **反对 C**：`workflow_registry.py:86-88` 与 L3 禁 `workflow_key` 是为防 branch 字符串回流（`S05-T002`）。C 把动态配置做成每次请求的自由选图，taxonomy 立刻爆炸。  
- **B**：满足「动态配置」而不破坏三轴。工人都 live 之后，decode 后选择 OCR **不是** v0.1 的「未部署降级」，而是配置好的合法边。GLM 的 route 决策点是本产品法的一种落地形态，本题不锁形态。

#### 问题（请业主裁决）

**Q2：路由动态配置选 A / B / C？若选 B，是否确认：调用方仍不能点名 workflow_key；工人在真实表示已知之后按 **可配置闭集规则** 绑定；绑定结果必须进 evidence；禁止无证据暗升？**

- **业主回答**：接受推荐 **B** 全部确认句。→ **冻结为 `T-O-382`**
- **裁决状态**：`accepted / frozen`

---

### Q3 — 工人绑定之后，全链路失败、幂等与竞态的产品法

- **影响范围**：无层/加密/空正文；同 `task_uuid` 重放；同 `external_key` 再摄入；并发 create；「必须出向量」是否等于「换工人直到成功」
- **为什么必须确认**：业主要求上传、失败幂等、竞态全部落地，且路径必须拿到真实 vector。端口将全部在场，v0.1 的「未部署 503」不再适用。若不钉绑定后的失败法，「动态路由」会滑成无限换工人冒充成功。
- **驱动输入**：Q1 闭集、Q2 绑定时刻；`task_create.py` 指纹；NS9-FX2 replay；`CLEAN_EMPTY`

#### 对问题的详细解读

Q1 说每条 **路径** 必须能被真实文件打到向量。这不是说 **每个文件** 都必须出向量（加密 PDF、空页、冲突重放仍应失败）。

Q2 说工人如何被配置选中。Q3 说 **选中之后** 还允许什么：

1. 内容失败（空抽取、损坏、加密）；  
2. 幂等（同一 `task_uuid`+指纹重放；同一 intake `external_key` 再来）；  
3. 竞态（并发 create / 并发 accept）；  
4. 是否允许绑定后再换下一个 live 策略，直到某次出向量。

今日已有：Task 指纹双检（`task_create.py:70-104`）；指纹冲突 `task-identity-conflict`；intake replay（NS9-FX2）；gate `idempotency_key`；空正文 `CLEAN_EMPTY`。业主要的是这些法在 **新接通的四通道真实对象** 上全部成立并被测试，而不是另发明「最后写赢」或「空也 publish」。

第 4 点是唯一真分叉：B 选项会把「路径能出向量」做成「文件必须出向量」。

#### 可选的方案清单

| 选项 | 方案 | 含义（产品法） |
|------|------|----------------|
| **A** | **绑定后 fail-loud；幂等/竞态走现有 CAS 并覆盖新路径（推荐）** | 配置路由一旦绑定工人，该 Execution 不再换清洁工人。内容失败 = Task/Process 显式失败，**不出向量**。同一 Task 指纹重放返回原视图。同一 intake 键 + 同 digest = replay（指针必须解析）。并发冲突 = typed ConflictError。空正文不是成功。上传与四通道必须都受这些法约束。 |
| **B** | **绑定后仍可再换 live 策略，直到产出向量或策略耗尽** | 「真实 vector」优先于「声明的工人」。例如 text-layer 失败自动再跑 OCR、再跑 understanding。须留下完整替代链 evidence。 |
| **C** | **空结果或竞态可部分成功** | 空 listings/空 HTML 仍 succeeded；并发 last-writer-wins 无冲突码。否决项（遗产行为）。 |

#### 当前建议 / 倾向（Grok）

**推荐 A。**

#### 推荐方案的详细说明

选 A 时：

1. Q1 的「路径走到向量」= **该路径被正确选中且内容可抽取时** 必须 publish；不是每个坏文件都 publish。  
2. Q2 的动态配置负责把扫描件送到 OCR **之前**；送到之后失败就是失败。  
3. 幂等：`task_uuid`+`creation_fingerprint` 不变则 replay（`task_create.py:82-85`）；变则 `task-identity-conflict`。Intake 身份 replay 保持 NS9-FX2：不得悬空 revision。  
4. 竞态：CAS/rowcount/ConflictError，禁止静默覆盖 serving。  
5. 上传 API 必须加入同一幂等/冲突面，不能「先写对象再失败 Task」留下无身份孤儿当成功。  
6. C 正式否决，防止把 legacy 空成功借回。

选 A **不**与 Q2-B 冲突：动态配置发生在绑定前；A 约束绑定后。

#### 支持推荐 / 反对其他方案的证据与 Reasoning

- **反对 B**：在全部策略 live 之后，B 等于同 Execution 内遍历工人直到出向量，与 `T-O-340` 的「换工人必须是显式下一枪」冲突，也会让 serving 血统无法从一次绑定读出。扫描件应在 Q2 规则里 **一开始** 就进 OCR，而不是 pdf_text 失败后再转。  
- **反对 C**：`CLEAN_EMPTY`（`intake/web/__init__.py:28-29`）与 D08 反 silent skip。空成功会把无知识写进向量，直接打脸「真实 vector」。  
- **A**：把业主点名的幂等/竞态解释为 **现有 CAS 法必须覆盖新通道与上传**，而不是新发明成功语义。与 R7「证据面诚实」一致：失败就是失败，replay 就是 replay。

#### 问题（请业主裁决）

**Q3：工人绑定之后选 A / B / C？若选 A，是否确认：不再换清洁工人；内容失败不出向量；Task/intake 重放与并发冲突保持 fail-closed CAS；空正文不是成功；上传必须服从同一套幂等/冲突法？若选 B，须同时接受「同 Execution 内显式替代链」，并说明如何与 `T-O-340` 共存。**

- **业主回答**：接受推荐 **A** 全部确认句。不采用同 Execution 替代链。→ **冻结为 `T-O-383`**
- **裁决状态**：`accepted / frozen`

---

## 4. ★ 中场评估 I（Round 1 → Round 2）`[核心·锁死]`

- **4.1 对 Round 1 的判定**：三题均决断，且均为推荐项。最关键的一手是 **Q1-B**：把战役从「能拒绝的占位」改写成 **live-to-vector 闭集**，后面两题才有意义。Q2-B 把「动态配置」钉在 **表示已知之后绑定**，而不是开放 workflow_key。Q3-A 堵住「工人都在场之后遍历策略直到出向量」。无遗留 OPEN。
- **4.2 本轮已锁定真相**：`T-O-376..380` 围栏确认；`T-O-381` live 矩阵；`T-O-382` 晚绑定；`T-O-383` 绑定后 fail-loud + CAS/replay。
- **4.3 诚实反方制衡**：
  - Q1-B 与 S13「v1 无公网 object API」（`S13-artifact-storage.md:67-68`）**字面冲突**——上传必须进闭集，但身份落在 S13 还是 S04 未钉。
  - Q2-B 与 S03「Execution 创建时 durable 绑定 exact revision / `s05_binding_digest`，retry 不热切」（`S03-T017` / `S03-T053`）以及「route 禁止自由表达式」（`S03-T012`）尚未和解——晚绑定的 **声明式落点** 未钉。
  - Q1-B 要求全部策略走到 structurize，但 D05 `T-O-208/210` 写 promptA@clean，而 HEAD 确定性/API map **不**绑 promptA（`strategies.py:52-55` vs `57-65`）。四通道「clean」是否同一 LS-RAG 合同未钉。
- **4.4 为什么提出 Round 2（注入 Q4–Q6 + 驱动真相）**：
  - **Q4** 由 `T-O-382` 驱动：晚绑定已冻，但 **可配置规则住在哪套声明式真相**（S03 七表 route/guard vs 表外策略包 vs 拆 Execution）未定；不钉则无法保持「声明式 workflow、无自由表达式」。
  - **Q5** 由 `T-O-381` + `T-O-383` 驱动：公共上传是闭集义务，且必须服从同一幂等/冲突法；S13 明文不拥有公网 upload 产品、S04 才拥有 Intake 身份。
  - **Q6** 由 `T-O-381` + `T-O-208/210` 驱动：每条路径必须进现有 publication 链，须钉 **clean 产物是否仍是单一 admissible body**、以及 promptA 对确定性/API 是否强制。
  库选型、charset 版本、实验 `run_id` 仍不进 Round 2。

---

## 5. Round 2 —— 声明式图、上传身份、LS-RAG clean 合同（`Q4–Q6`）

> 本轮 second-opinion 模式：`retired`。  
> **Round 2 状态**：Owner **整包接受推荐**（Q4=A，Q5=A，Q6=A）· 2026-08-29 · 已冻结 `T-O-384..386`。  
> **每题标驱动真相。** 执行形态（是否多一个 step_key、上传 HTTP 路径、PDF 库）不在本题冻结。

---

### Q4 — 晚绑定如何住进声明式 Workflow，而不破坏 immutable Execution（**驱动真相：`T-O-382`** · 次驱动 `T-O-379` / `S03-T012` / `S03-T017` / `S03-T038` / `S03-T053`）

- **影响范围**：Workflow 七表（steps/routes/guards/bindings）；`s05_binding_digest` 何时封闭；是否允许 runtime 按 media 调 `dispatch_clean`
- **为什么必须确认**：`T-O-382` 要求表示已知之后才绑定工人，且规则可配置。S03 要求：route 只有登记的 selector/guard、禁止自由表达式（`S03-T012`）；Execution 创建即绑定 exact revision 与 `s05_binding_digest`，retry 不热切（`S03-T017` / `S03-T053`）；single 用 **同一个 root Execution** 贯穿 ingress→publication（`S03-T038`）。三者未和解，规划会要么写成 Python if 链（回到 legacy `action_branch`），要么拆成两次 Execution（打断 LS-RAG 主链）。
- **驱动输入**：`T-O-382`；`src/contracts/workflow/models.py:245-258`；`lsrag_definition.py` 已有 CONTROL `human_review` + BRANCH guards；`task_create.py:176-180` 在 Task 创建时写入 `s05_binding_digest`

#### 对问题的详细解读

HEAD 的「声明式」已经是：**Python 模块编译进七张表**，不是 YAML 运行时。`WorkflowGuardDefinition` 只允许闭集 predicate（admission 结果、request_intent、markdown 是否在场），operator 只有 `eq`（`models.py:245-258`）。Admission 后的 BRANCH（`admission_auto_admitted` 等，`lsrag_definition.py:346-382`）证明：**图可以预先画出多条边，用登记 guard 选一条**，而不在 handler 里写自由表达式。

`T-O-382` 的新需求是：clean 的那条边取决于 **decode 之后才有的表示**（文本层水位、是否 rendered）。这比「intent 在 Task 创建时已知」更晚。

遗产 clean-dispatcher 用 `action_branch` 字符串在 **workflow step JSON** 里选 worker（`smind-clean-dispatcher` mapper 拷贝 `step.action_branch`）——正是 D08/S05 禁止回流的 taxonomy。NH 要动态，但不能把 branch 名当 source。

本题钉 **晚绑定的真相住所**，不钉 step_key 命名、不钉是否新增一个 process_key。

#### 可选的方案清单

| 选项 | 方案 | 含义（产品法） |
|------|------|----------------|
| **A** | **同一 revision 内预声明全部 live clean 边；登记 guard 在表示已知后选择（推荐）** | 一张（或按 source kind 有限几张）immutable 图列出 Q1 闭集里所有清洁 Process 为 **静态步骤**。decode（或等价探测）之后，**已登记** 的 guard/control 在这些边上做确定性选择。规则的 version/digest 编进 compiled revision。`s05_binding_digest` 在 **选边 Outcome 提交后** 封闭（同 Execution、同 revision，不热切图）；retry 仍用该封闭 digest。禁止 handler 按 media 暗调未出现在本 revision 的 process_key。 |
| **B** | **表外策略包 + 通用 `dispatch_clean` 一步** | 图只留一个 clean 步骤；真正工人由策略包在 runtime 决定。配置可动态，但 route 真相不在七表。与 `S03-T012`「禁止自由表达式」和 `S03-T009`「职责不得合并回 JSON」冲突面最大。 |
| **C** | **decode 完成后再 resolve 另一张 Workflow revision / 新 Execution** | 晚绑定 = 换程序。打破 `S03-T038` 单 root 贯穿，也让 retry 难以继承 exact revision（`S03-T018`）。接近遗产「下一步再派另一个 skill worker」。 |

#### 当前建议 / 倾向（Grok）

**推荐 A。**

#### 推荐方案的详细说明

选 A 时：

1. 动态配置的载体是 **S03 已有的 steps/routes/guards**（可扩展 **登记过的** predicate，例如「text_layer_present」），不是调用方字符串，也不是 mixin 里的第三套 if。  
2. 所有 Q1 闭集工人必须在该 revision **看得见**（作为 process 步骤），否则 guard 无法合法指向它们——这正是今日 5 张图选不中的根因在声明式层的对应物。  
3. Execution 在 Task 创建时仍绑定 **这张** revision（满足 T017）；清洁 **哪一条边** 在表示已知后才成为事实，并写入 evidence + 封闭 `s05_binding_digest`（满足 T-O-382 与 T-O-383：之后不再换边）。  
4. 与 human_review CONTROL 同构：先有一个决策点，再 BRANCH 到已画出的下游。

#### 支持推荐 / 反对其他方案的证据与 Reasoning

- **反对 B**：`S03-T012` 禁止 Python/SQL/自由表达式；`models.py:245-246` 把 guard 写成「no free expression surface」。通用一步 + 表外包 = 把 `action_branch` 换个文件名。legacy router 按 branch 前缀选 schema 还会 **warn 后跳过校验**——NH 不能再开这条缝。  
- **反对 C**：`S03-T038` 要求 ingress→clean→acceptance→LS-RAG 同一 root Execution。decode 后换 revision 等于把清洁工人做成第二次 binding，retry/recovery 会热切（`S03-T053` 明文禁止）。  
- **A**：HEAD 已用登记 guard 做 admission 分流（`lsrag_definition.py:346-382`）；只需把「表示」做成同类登记谓词。compiled digest 仍 byte-identical（`S03-T007`）。配置变更 = **新 revision + guarded pointer**，不是热切运行中 Execution。

#### 问题（请业主裁决）

**Q4：晚绑定的声明式住所选 A / B / C？若选 A，是否确认：同一 immutable revision 预声明全部 live clean 边；仅用登记 guard/control 选择；`s05_binding_digest` 在选边后封闭且 retry 不热切图；禁止表外/handler 暗调未声明的 process_key？**

- **业主回答**：接受推荐 **A** 全部确认句。→ **冻结为 `T-O-384`**
- **裁决状态**：`accepted / frozen`

---

### Q5 — 公共上传的法律身份：S13 字节还是 S04 Intake（**驱动真相：`T-O-381`** · 次驱动 `T-O-383` / S13-v1.1 / S04）

- **影响范围**：公共 API 是否出现 objects 面；`local_object` 如何被外部喂真实文件；上传失败是否留下 IntakeItem
- **为什么必须确认**：`T-O-381` 把 **公共对象上传** 写进 live 闭集；`T-O-383` 要求上传服从同一幂等/冲突法。S13 明文：**不负责公网 upload 产品**、完成定义含「无公网 object API」（`S13-artifact-storage.md:67-68`）。S04 才拥有 IntakeSource/Item/Revision。不钉身份，上传会要么偷偷当 Intake，要么变成无主 CAS 孤儿。
- **驱动输入**：`T-O-381`；README §6.1 无上传端点；`ObjectStorePort.promote`（`src/storage/ports.py:12`）；inline 已在 Task 创建前 promote（`task_create.py:70-72` 注释）；S13 purpose 闭集无 `caller_upload`

#### 对问题的详细解读

今日 `local_object` 只接受已有 `mkbobj:v1:…` handle（`models.py:116-121`）。真实 PDF/docx/图片若不能经公共面进入 CAS，Q1 的 doc/pdf 通道对调用方仍是假接通。

S13 的宪法是 **bytes-first**：promote → digest → 主库 catalog/ref；**对象存在 ≠ 业务成功**（`S13-artifact-storage.md:29, 36-37`）。S04 的宪法是：只有 acceptance 才创造 Snapshot/Item/Revision。

遗产 admin 是：presign R2 → confirm HEAD → 再 `pending_cleaning` 入队。身份是 `smind_files` 行，不是 MKB 的五类 Intake。可借「字节先于业务身份」，不可借 file 行当 Item。

本题钉上传 **创造什么身份**，不钉 HTTP 路径或 multipart 形状。

#### 可选的方案清单

| 选项 | 方案 | 含义（产品法） |
|------|------|----------------|
| **A** | **上传只创造 S13 handle（窄 reopen「无公网 API」）；Intake 身份仅 ingest Task 才有（推荐）** | 公共上传 = 鉴权后的 `promote`：返回 handle+digest+size。不创建 IntakeSource/Item。随后 `intake.ingest` + `local_object` 走现契约。幂等按 **内容 digest + team**（CAS 已 unique）；重复上传同一字节 replay 同一 handle（`T-O-383`）。无 ingest 的对象按 S13 orphan/GC。这是对 S13「无公网 object API」的 **窄 reopen**：允许 **受鉴权** 的 Port 暴露，仍不让对象存在定义业务成功。 |
| **B** | **上传即创建 IntakeSource/Item** | 文件一进门就是业务身份。失败清洗会留下 Item。与 S04「只有 acceptance 写 Item」冲突，也让未 ingest 的字节进入 serving 叙事。 |
| **C** | **没有独立上传面；字节只能活在某次 ingest Task 体内（inline 扩二进制）** | 不 reopen S13 公网面。大 PDF 必须塞进 Task 创建（受 `MKB_MAX_REQUEST_BYTES` 1MiB 默认帽，`README` §6.1）。与「文件上传全部落地」字面不合，且无法复用 handle 做 rebuild。 |

#### 当前建议 / 倾向（Grok）

**推荐 A。**

#### 推荐方案的详细说明

选 A 时：

1. 上传产品属于 **S13 Port 的受鉴权暴露**，不属 S04。  
2. 法律对象：CAS handle + digest；purpose 须进入闭集（今日无 `caller_upload`，扩展须登记——本题只要求「有 owner + live ref」，不锁 purpose 字符串）。  
3. Intake 五类身份仍只由 ingest/acceptance 产生（S04）。  
4. 幂等：同一 team、同一 sha256+size → 同一 handle（与 `mkb_stored_objects` unique 一致），不新建幽灵对象。  
5. 未随后 ingest 的对象 = S13 orphan，不进入检索。  
6. 选 A 视为 **窄 reopen** S13「无公网 object API」完成定义第 7 条，不废除 bytes-first、verify-on-read、GC。

#### 支持推荐 / 反对其他方案的证据与 Reasoning

- **反对 B**：S04 五类身份的线性化点是 acceptance，不是磁盘出现。B 会让失败 OCR 留下 Item，污染 lifecycle CRUD。  
- **反对 C**：公共 API 无 objects（`api/public/routes.py` 全表无 upload）；inline 上限与真实 PDF 矛盾。C 等于不兑现 `T-O-381` 的上传义务。  
- **A**：与现 inline「先 promote 再进 Task UoW」（`task_create.py:70-72`）同构，只是把 promote 从「仅服务端」改成「调用方可调用」。CAS unique `(team_uuid, sha256, size)` 已是幂等分母（S13-E05）。遗产 presign+confirm 也是字节先于 cleaning。

#### 问题（请业主裁决）

**Q5：公共上传身份选 A / B / C？若选 A，是否确认：上传只返回 S13 handle+digest、不创造 IntakeItem；随后必须另一次 ingest Task；重复字节 replay 同一 handle；并接受这是对 S13「无公网 object API」的窄 reopen？**

- **业主回答**：接受推荐 **A** 全部确认句。接受窄 reopen。→ **冻结为 `T-O-385`**
- **裁决状态**：`accepted / frozen`

---

### Q6 — 四通道接通后，clean 对 LS-RAG 仍是不是同一份合同（**驱动真相：`T-O-381`** · 次驱动 `T-O-208` / `T-O-210` / `T-O-378`）

- **影响范围**：promptA 是否对确定性/API 强制；g0=`clean` 隧道是否覆盖 PDF/API/web；scatter member 的 clean 是否各走一遍 trinity
- **为什么必须确认**：`T-O-381` 要求每条路径进入 **现有** publication 链。D05 规范链是 promptA@clean → promptB@structurize → promptC@construct → vectorize（`T-O-210`）。HEAD 却把 promptA 只挂在 `llm_required=True` 的策略上（`strategies.py:52-55` 确定性 web **无** prompt_key；`57-65` llm_rewrite 才有 `promptA.default`）。遗产 dedicated **从不** AI 洗。若不钉，规划会把 API map 做成「第三种知识」、或反过来强迫 chinatax 走 Gemini 式 rewrite，两者都破坏 LS-RAG。
- **驱动输入**：`T-O-381`；D05 `T-O-208/210`；NS1 `T-O-339`；R7 g0=clean 不变量；scatter child 自己 structurize（`builtin_scatter.py`）

#### 对问题的详细解读

LS-RAG 理论在本仓已冻的核心是：

- 知识生产有且仅有三身份：A 洗、B 结构、C 摘要（`T-O-208`）。  
- g0 original 必须能等于 **admitted clean**（R7 / NS9 不变量；`T-O-378` 空 clean 禁止）。  
- 向量发生在 construct full_valid 之后（`T-O-206`）。

四通道「接通」容易误读成四种不同的结构内核。正确约束应是：**通道只改变如何得到 clean body，不改变 B/C/kernel。**

分叉在 A 的义务：

- 确定性 web/PDF 文本层/API parser **没有模型**，强制 promptA 要么变成空转身份，要么偷偷改成 LLM rewrite（扩大 Q1 闭集的运行成本，且 dedicated 遗产无 AI）。  
- 若说它们「不是 clean」，则 T-O-210 的第一环对 API/PDF 文本层不成立，g0 隧道没了权威输入。

本题钉 **clean 合同同一性 + promptA 义务面**，不钉 promptA 正文版本。

#### 可选的方案清单

| 选项 | 方案 | 含义（产品法） |
|------|------|----------------|
| **A** | **同一 admitted clean 合同；promptA 仅 `llm_required` 策略强制（推荐）** | 不论通道，S06 只消费一份 admissible clean body（+ digest/evidence）。g0 必须等于该 body。确定性策略与 `clean.map.registered_api` **不**调用模型，但 **仍是 clean**：产出进同一 artifact 合同。promptA hash 只在 LLM 策略进入 `s05_binding_digest`。API 每个 scatter child 独立 clean→B→C→向量（已是 scatter 图）。禁止为通道另写 structurize kernel。 |
| **B** | **所有接通路径强制 promptA 模型调用** | 连 PDF 文本层、chinatax parser 之后也必须再跑 promptA rewrite。对齐 D05 字面「promptA@clean」，但与 D08「dedicated 从不 AI 洗」、以及确定性可复验 digest 冲突。 |
| **C** | **API/确定性输出不是 D05 clean；B 直接吃 raw/parser 文本** | 通道各自跳过 A。g0 隧道对这类路径无定义。破坏 trinity，且让「四通道 clean」名不副实。 |

#### 当前建议 / 倾向（Grok）

**推荐 A。**

#### 推荐方案的详细说明

选 A 时：

1. **一个** clean 合同：非空 body、content digest、strategy/capability evidence。这是 structurize 的唯一原文。  
2. promptA 是 **LLM 清洁策略的身份**，不是「所有通道都必须打一次模型」。确定性与 API map 用策略 digest 代替 promptA hash 进入 binding。  
3. 这是对 `T-O-210` 的 **窄执行解释**：第一环永远是「得到 admitted clean」，其中模型子环仅 `llm_required`。不是废除 handbook。  
4. g0=`clean` 对 PDF/API/web 同样成立；空 body 仍失败（`T-O-378`/`T-O-383`）。  
5. 禁止按通道分叉 S06 kernel（保持 NS3 叶无 I/O + 现 cuts）。

#### 支持推荐 / 反对其他方案的证据与 Reasoning

- **反对 B**：`CLEAN_STRATEGY_DEFINITIONS` 已把 `llm_required` 写成策略事实（`strategies.py:47-55` vs `57-65`）。B 等于取消确定性主路径，与 Q1「真 PDF 文本层」和遗产 dedicated 无 Gemini 相反；也会让同一 chinatax 法规每次 ingest 因温度得不到同一 digest，打脸 `T-O-383` replay。  
- **反对 C**：R7 不变量是切片来自 clean_text。若 API 没有 clean 合同，g0 与 traceback 失去 SSOT。`T-O-210` 第一环被跳过。  
- **A**：对齐 D08 分账（universal 才 AI，dedicated 只 ETL）、D05 三身份（B/C 不进 clean）、以及 HEAD scatter child 已从 member `clean_text` 进入 LS-RAG。promptA 三套默认 id 的对齐属执行，本轮不锁。

#### 问题（请业主裁决）

**Q6：clean 对 LS-RAG 的合同选 A / B / C？若选 A，是否确认：所有通道产出同一份 admitted clean body 供 B/C/g0；promptA 仅 LLM 策略强制；API map 与确定性策略仍是 clean 而非跳过 A；不为通道另写 structurize kernel；并接受这是对 `T-O-210` 的窄执行解释？**

- **业主回答**：接受推荐 **A** 全部确认句。接受对 `T-O-210` 的窄执行解释。→ **冻结为 `T-O-386`**
- **裁决状态**：`accepted / frozen`

---

## 6. ★ 中场评估 II（Round 2 → Round 3）`[核心·锁死]`

- **6.1 对 Round 2 的判定**：三题均决断，且均为推荐项。最关键的一手是 **Q4-A**：把 `T-O-382` 晚绑定钉进 S03 七表（同一 immutable revision、预声明边、登记 guard、选边后封闭 digest），而不是表外 `dispatch_clean` 或换 revision。Q5-A 把 `T-O-381` 的上传义务解释为 **S13 窄 reopen**，保住 S04「只有 acceptance 才有 Item」。Q6-A 保住 LS-RAG 单一 admitted clean / g0 隧道，同时不强迫确定性/API 打 promptA 模型。无 OPEN 残题。
- **6.2 本轮已锁定真相**：`T-O-384` 声明式晚绑定；`T-O-385` 上传=S13 handle；`T-O-386` 四通道同一 clean 合同 + promptA 仅 `llm_required`。
- **6.3 诚实反方制衡**：
  - Q4-A 自己留下括号「一张或按 source kind 有限几张」——**图基数未钉**。HEAD 仍是 `_source_profile_workflow` 每张图 **一个** acquire、**一个** decode、**一个** clean（`lsrag_definition.py:307-314, 913-924`），公开 7 键、另 5 张选不中（`929-940` vs `1003-1054`）。守卫谓词闭集看不见表示（`models.py:245-258`；runtime 缺键 fail-closed，`runtime_materialize.py:110-113`）。不钉张数，规划会做成一张非法边巨型图，或继续 12 张 profile、晚绑定落空。
  - Q2-B 例示「HTML 空壳 → browser」。Q4-A / `T-O-384` 只锁了 **clean 边** 的声明式住所；**获取轴**是否允许在同一 revision 里再走一条已画出的 acquire 边，未钉。S03-T011 禁止业务环（`S03-workflow-engine.md:176`；编译器无环，`models.py:389-432`）。HEAD acquire 从不写 `print_pdf`（`acquisition_ingest.py:535`）。遗产 `action_branch` 在登记时一次性选定抓取器（`action_registry.ts:91-148`）。三者未和解。
  - Q6-A 钉 g0=admitted clean body，但 **FilterMeta/ContextMeta** 的住所未钉。D08-T007 / D08-A07 要求五维进 SemanticDefinition，**不得只塞进 `clean_text`**。S04 已登记 `realm/type/channel/source_name/is_active/context_tags`（`registry.py:229-239`）。HEAD 只在 API `filter_meta` 在场时展开五维；web/pdf 落到 stub `{"source_kind": ...}`（`acceptance_snapshot.py:591-610`）。S06 layered `context_meta` 仍要 realm/type/channel（`layered_content.py:17-28, 121`）。不钉会把检索语义写进 g0，或让 web/pdf「可检索」没有五维。
  - Q5-A 与 purpose 字符串、HTTP 形状仍是执行，**不再占用 foundational 题**。promptA 三套默认 id 对齐同理。
- **6.4 为什么提出 Round 3（注入 Q7–Q9 + 驱动真相）**：
  - **Q7** 由 `T-O-384` 驱动（次驱动 `T-O-379` / `T-O-381`）：晚绑定已有声明式住所，但 **有几张 immutable 图** 未定。
  - **Q8** 由 `T-O-382` + `T-O-384` + `T-O-383` 驱动（次驱动 `T-O-378` / `T-O-379` / `S03-T011`）：表示已知之后，晚绑定信封是 **只选 clean**，还是允许 **有限条已声明的正向再获取**。
  - **Q9** 由 `T-O-386` + `T-O-381` 驱动（次驱动 `T-O-62` / D08-T007 / `T-O-352`）：g0 已等于 clean body；FilterMeta 必须与 g0 **分账**，且四通道是否都要五维。
  - 库选型、charset 版本、实验 `run_id`、purpose 字符串、具体 `step_key` / predicate 枚举名 **仍不进 Round 3**。

---

## 7. Round 3 —— 图基数、再获取信封、语义分账（`Q7–Q9`）

> 本轮 second-opinion 模式：`retired`。  
> **Round 3 状态**：Owner **整包接受推荐**（Q7=A，Q8=A，Q9=A）· 2026-08-29 · 已冻结 `T-O-387..389`。  
> **每题标驱动真相。** 执行形态（几条 step_key、守卫 `expected_value` 字面、FilterMeta 从 URL 还是调用方填）不在本题冻结。

---

### Q7 — 晚绑定住进声明式图之后，immutable revision 有几张（**驱动真相：`T-O-384`** · 次驱动 `T-O-379` / `T-O-381` / `S03-T007` / `S03-T038`）

- **影响范围**：`workflow_registry` 解析键；`_source_profile` 是否继续用 kind×mode×media 选图；一张图上要预声明多少条 acquire/clean 边；scatter 是否被折进巨型单图
- **为什么必须确认**：`T-O-384` 写「一张，或按 source kind 有限几张」——括号就是本题。张数会改变：调用方 typed 面还剩什么、Q8 的再获取能不能画在同一张无环图上、非法边（chinatax 洗 PDF、HTML 走 OCR）由谁挡住。
- **驱动输入**：`T-O-384`；`lsrag_definition.py:881-924, 929-1054`；`config_snapshots.py:492-516`；`workflow_registry.py:84-103`；`S03-T011` 无环；scatter 已是独立 `execution_role`

#### 对问题的详细解读

HEAD 的声明式图 **不是**「一张程序、多条 clean 边」。`_source_profile_workflow` 用替换三个 `process_key` 克隆同一骨架：acquire → decode → **单** clean（`lsrag_definition.py:307-314, 913-924`）。公开可选只有 7 个 profile 键（`929-940`）；LLM / vision / print-pdf 另 5 张 bootstrap 了但 `SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS` 选不中（`1003-1054`）。解析器从 `source_kind` + `acquisition_mode` + `media_type` 映射到其中一张（`config_snapshots.py:504-516`），调用方不能点名 `workflow_key`（`workflow_registry.py:86-88`）。

`T-O-384` 要求 **每张被选中的 revision 看得见该闭集里合法的全部 clean 工人**。这立刻分出三种产品法：

1. **按 source kind 有限家族**：`inline_payload` / `local_object` / `http_resource` 各一张 single-root 图（`registered_api` 维持已有 scatter_root + scatter_child）。kind 在 Task 创建时已知，选图；mode/media/文本层是图内 typed 事实。  
2. **一张 mega 单根图**（scatter 除外）：所有 kind 的边画在同一 revision，guard 看 `source_kind`。  
3. **维持/扩张 profile 家族**（今日 7+5）：kind×mode×media 继续选图，每张图只预声明 **该 profile 合法** 的 clean 边。

本题钉 **有几张 immutable 程序、选图键是什么**。不钉 step 命名、不把 scatter 折进 single-root（`S03-T013`：API scatter child 仍是 Execution）。

与 Q8 的耦合（必须对业主讲清）：若选 **C**（static 与 browser 仍是两张互不相通的图），则 Q8 无法在同一 revision 里画 static→browser 正向边，Q8 只能选 B。若选 Q8-A，Q7 必须至少粗到「`http_resource` 一张图含两种 acquire」。推荐包装是 **Q7-A + Q8-A**。

#### 可选的方案清单

| 选项 | 方案 | 含义（产品法） |
|------|------|----------------|
| **A** | **按 source_kind 的有限家族（推荐）** | 四类 kind → 四套程序：三张 single-root（inline / local_object / http_resource）+ 已有 scatter_root/child。每张 **预声明该 kind 合法的全部 live clean 边**（以及该 kind 合法的 acquire/decode 边）。Task 创建只按 kind 解析图，仍禁止点名 `workflow_key`。`acquisition_mode` / `media_type` 不再是选图键，而是图内起点或探测事实。配置变更 = 新 revision + guarded pointer（`S03-T007`）。 |
| **B** | **一张 mega single-root（scatter 仍独立）** | 所有非 scatter 边在同一 revision。guard 必须挡住跨 kind 非法边。compiled digest 最大；一张图的变更会碰所有通道。 |
| **C** | **维持 profile 家族（kind×mode×media）** | 接近 HEAD：http.static / http.browser / local.pdf 仍是不同 `workflow_key`。每张图预声明该 profile 的 live clean 边（例如 local.pdf 含 text_layer / understanding / ocr）。调用方 mode/media 继续选图。 |

#### 当前建议 / 倾向（Grok）

**推荐 A。**

#### 推荐方案的详细说明

选 A 时：

1. **选图权威 = source_kind**（创建时已知，满足 `T-O-379`）。清洁工人与（若 Q8-A）后续 acquire **不**靠再开一张图。  
2. `http_resource` 一张图必须看得见 static / browser / print 表示所需的已登记 acquire 边，以及 `web.deterministic` / `web.llm_rewrite` / `web.browser_print_pdf`（进 pdf 通道的 print 边，D08-T009）。  
3. `local_object` 一张图必须看得见 pdf/doc/image 的 decode 与 `pdf.*` / `doc.*` 全部 live 边；media 是 acquire/decode 后的 typed 事实，不是选图键。  
4. `inline_payload` 一张图走 inline acquire + 该 kind 合法 clean 边。  
5. `registered_api` **不**并入 mega：scatter 基数已冻（`S05-T002`）。  
6. 非法边（HTML 走 `pdf.ocr`、local 图走 `http_browser`）根本不画，而不是靠运行时 if。  
7. 今日 5 张选不中的图必须 **并进** 对应 kind 的 revision，成为看得见的步骤——这正是 `T-O-381` × `T-O-384` 在图上的对应物。

#### 支持推荐 / 反对其他方案的证据与 Reasoning

- **反对 B**：S03 允许 BRANCH，但 mega 把 chinatax scatter 之外的全部非法组合留给守卫。今日守卫闭集没有 `source_kind` 谓词（`models.py:249-255`）。可以扩展登记，但一张图变更=全通道新 revision，违背「通道只改变如何得到 clean」（Q6-A）的隔离。`S03-T038` 要的是 **一次 Execution 贯穿**，不是 **全世界一张图**。  
- **反对 C**：C 让 `http_resource.static` 与 `.browser` 继续两张程序。Q2-B 已用「HTML 空壳 → browser」当可配置规则；跨 revision 再绑定是 Q4-C，已被否。C 也把 `media_type` 继续当选图键：HTTP PNG 今日无 image profile（`config_snapshots.py:504-506`），正是 profile 爆炸的现场。local PDF 的 text vs OCR **同一 media**，C 反正要在 local.pdf 一张图里晚绑定——那 kind 家族只是把该逻辑升一层。  
- **A**：对齐 Q4-A 原文「按 source kind 有限几张」、三轴（kind 选图，acquire/strategy 图内绑定）、以及 D08 把 6 条 `action_branch` 拆成 kind 内的 capability×strategy（`D08-legacy-capabilities-migration.md:158-166`；遗产登记一次选定抓取器，`action_registry.ts:91-148`——借拆轴，不借「一张 branch 一张 worker」）。  
- **遗产对照**：universal 6 分支其实是 **同一 skill 内** 用 branch 字符串选 acquire+AI；MKB 禁止回流该 taxonomy（`T-O-377`）。A 用有限几张 **声明式 revision** 取代 branch 名，而不是再登记 12 个 workflow_key 冒充 profile。

#### 问题（请业主裁决）

**Q7：immutable revision 基数选 A / B / C？若选 A，是否确认：选图键是四类 source_kind（scatter 仍独立）；每张 kind 图预声明该 kind 全部 live clean 边；`acquisition_mode`/`media_type` 不再选图；调用方仍不能点名 `workflow_key`？若选 C，须同时接受 Q8 不能在 static 图里再获取 browser（除非把该边画进 static 图——那已滑向 A）。**

- **业主回答**：接受推荐 **A** 全部确认句。→ **冻结为 `T-O-387`**
- **裁决状态**：`accepted / frozen`

---

### Q8 — 晚绑定信封：可否在绑定清洁工人之前，走已声明的再获取（**驱动真相：`T-O-382` / `T-O-384` / `T-O-383`** · 次驱动 `T-O-378` / `T-O-379` / `S03-T011`）

- **影响范围**：`acquisition_mode` 是冻死的唯一 acquire，还是起点；print_pdf 如何成为诚实表示；无文本层 PDF 是死在 decode 还是成为守卫事实；SPA 空壳的产品法
- **为什么必须确认**：`T-O-382` 要在 **表示已知之后** 绑清洁工人，例示含「HTML 空壳 → browser」。`T-O-384` 只允许 **本 revision 已画出的边**。`T-O-383` 禁止 **绑定后** 再换清洁工人，但没说绑定前能不能再获取一次。`S03-T011` 禁止业务环。HEAD decode 无字面量即抛 `CLEAN_OCR_CAPABILITY_UNAVAILABLE`（`types.py:154-158`），表示「缺失」从未成为守卫事实。
- **驱动输入**：Q2-B 例示；`acquisition_ingest.py:535`；`clean_preflight.py:46-62`；`types.py:144-171`；`models.py:432`；D08 print_pdf 是 acquire 表示 + PDF understanding（`D08-legacy-capabilities-migration.md:166, 233`）

#### 对问题的详细解读

三轴里 acquire 是一轴（`S05-intake-cleaning.md:105-110`）。今日调用方在 descriptor 上写 `acquisition_mode ∈ {static, browser, pdf}`（`models.py:124-128`），创建时选图。这把 acquire **冻在 Task 创建**。

晚绑定要的「表示」有一类 **必须再获取才能知道**：静态 HTML 是 SPA 空壳、站点其实要 print-pdf、声明 text/html 但字节是 `%PDF-`（后两者更多是 decode/media 嗅探，不一定再获取）。Q2-B 把「HTML 空壳 → browser」写成可配置规则；业主已接受。遗产则在 `action_branch` **事前** 选定 htmlCrawl vs browserFetch vs browserPDF（`action_registry.ts:94-137`），运行中不升。Grok 工作笔记 v0.3 曾写「禁止 static 失败后自动 browser」——那是 **暗升** 禁令，不是「图上已画的正向边」禁令。

另一类表示 **不必再获取**：PDF 有无文本层、图像 vs PDF。HEAD 把「无层」做成 decode 失败并盗用 OCR 码（`T-O-378`）。`T-O-382` 要绑 OCR，decode 就必须 **观察** 到 `text_layer=absent`，而不是死在 decode。这条对 Q8-A/B **共用**，不是分叉。

分叉只剩：**绑定清洁工人之前，图可否再走一条已声明的、正向的、不同 `step_key` 的 acquire。** 不能回到同一个 `acquire` 步骤（禁止自边，`models.py:389-390`；禁止环，`432`；`S03-T011` 禁止业务 loop）。不能 try-all-acquire 直到出正文（那是 Q3-B 对获取轴的翻版，与 `T-O-383` 精神冲突）。

本题钉信封，不钉「空壳」的具体谓词名。

#### 可选的方案清单

| 选项 | 方案 | 含义（产品法） |
|------|------|----------------|
| **A** | **绑定前允许有限条已声明的正向再获取（推荐）** | `acquisition_mode` 是 **起点边**，不是唯一允许跑过的 acquire。同一 revision 可画出例如 static-acquire → decode →（空壳/需 print）→ browser-acquire → decode → 绑 clean。每条边至多一次、无环、有 evidence。清洁工人仍只绑一次，之后 `T-O-383`。print_pdf 是已声明 acquire 表示，不得再伪造 `rendered`。 |
| **B** | **acquire 在 Task 描述符冻死；晚绑定只选 clean** | 调用方选 static 就只静态获取。空壳 = `CLEAN_EMPTY`（`intake/web/__init__.py:28-29`），不出向量。要 browser / print-pdf 必须一开始就选对应 mode。PDF 无层仍可在 **同一字节** 上晚绑 OCR（decode 只观察）。 |
| **C** | **否决项：暗升或环路 try-acquire** | handler 里 static 失败改调 browser；或环回同一 acquire 直到非空。无声明边、无 evidence，或违反无环。 |

#### 当前建议 / 倾向（Grok）

**推荐 A。**

#### 推荐方案的详细说明

选 A 时：

1. **共用确认（A 与 B 都要）**：decode 是观察器，不是拒绝器。无文本层 → typed 事实（如 `text_layer=absent`），**禁止**再抛 `CLEAN_OCR_CAPABILITY_UNAVAILABLE` 冒充 OCR 未部署（`T-O-378`）。空正文仍不是成功（`T-O-383`）——那是 **clean 绑定之后** 的法，不是 decode 的法。  
2. 再获取只能走 **本 revision 已画出的正向边**（`T-O-384`），写入 acquisition evidence（表示、capability、digest）。禁止无证据写 `browser_profile: injected-browser-renderer.v1`（今日反例，`acquisition_ingest.py:535-536`）。  
3. 有限：每个已声明 acquire 步骤至多成功一次；不得「换获取直到非空」。守卫选不中下一条边 → 按已绑定或无法绑定 fail-loud。  
4. print-pdf：必须真正产出 `representation_kind=print_pdf` 且 bytes 为 PDF（`clean_preflight.py:46-62` 的期望终于可满足）；随后晚绑 `web.browser_print_pdf` → `intake/pdf`（D08-T009），不是 HTML 消毒。  
5. 与三轴：acquire 轴仍在，只是 **取值时刻** 从「Task 创建」改为「绑定前的最后一次已声明获取」。调用方仍不点名 `workflow_key`。  
6. 依赖 Q7-A（或等价地把再获取边画进同一张图）。若业主选 Q7-C 且不把 browser 边画进 static 图，则本题只能改选 B。

#### 支持推荐 / 反对其他方案的证据与 Reasoning

- **反对 B**：与已冻 Q2-B 例示直接冲突。调用方在创建时 **不知道** 静态响应是不是空壳（正如不知道 PDF 有没有层）。B 把 SPA 推回「猜 mode」，猜错则整链失败，在 `T-O-376` live-to-vector 下不可接受。遗产事前选 branch 正是这个猜（`action_registry.ts:94-128`）；NH 拆轴就是为了不猜。  
- **反对 C**：暗升 = 无证据换表示，`T-O-378` / `T-O-384` 已禁。环路 = `S03-T011` 已禁。try-all-acquire 直到非空 = Q3-B 对获取轴，业主已否。  
- **A**：把 Q2-B 的「空壳 → browser」落成 **声明式正向边**，不是 mixin if。无环编译器可静态证明（`models.py:418-432`）。admission 后的 CONTROL `human_review` 已证明「决策点 → 已画出的下游」（`lsrag_definition.py:151-153, 366-374`）；本题是同一模式前移到表示已知处。  
- **HEAD 反例必须修**：`representation_kind` 只写 `rendered|transferred`（`acquisition_ingest.py:535`）；decode 无层即失败（`types.py:154-171` 还把 `text_layer: present` 写死）。不修则 `web.browser_print_pdf` 与 `pdf.ocr` 两条 live 路径物理不可达。

#### 问题（请业主裁决）

**Q8：晚绑定信封选 A / B / C？若选 A，是否确认：`acquisition_mode` 是起点；绑定清洁工人前可走有限条已声明、无环、正向的再获取；每边至多一次并进 evidence；decode 只观察（无层 ≠ OCR 未部署）；绑定后仍适用 `T-O-383`；禁止暗升与 try-all-acquire？若选 B，须同时接受 Q2-B「空壳 → browser」只能由调用方一开始选 browser，不再是图内规则。**

- **业主回答**：接受推荐 **A** 全部确认句。→ **冻结为 `T-O-388`**
- **裁决状态**：`accepted / frozen`

---

### Q9 — FilterMeta / ContextMeta 与 g0=clean body 如何分账（**驱动真相：`T-O-386` / `T-O-381`** · 次驱动 `T-O-62` / D08-T007 / `T-O-352`）

- **影响范围**：S04 revision semantics 是否四通道都写五维；检索过滤是否依赖它们；g0 original 是否允许夹带元数据；web/pdf 今日 stub 的命运
- **为什么必须确认**：`T-O-386` 钉 **一份** admitted clean body，且 g0 original 等于该 body。D08-T007 / D08-A07 钉 FilterMeta 五维是 **canonical semantic 面**，不得只进 `clean_text`。S06 layered `context_meta` 仍有 realm/type/channel/source_name（`layered_content.py:17-28`）。`T-O-352`：g0 original 留在 construct 供 traceback，向量只强制 g0 summary。若把五维塞进 clean_text，g0 与检索语义互相污染；若 web/pdf 继续 stub，四通道「可检索」不是同一套过滤面。
- **驱动输入**：`semantics.py:12-51`；`registry.py:229-239`；`acceptance_snapshot.py:576-614`；`S05-T008/T009`（`T-O-62`）；glossary FilterMeta ≠ clean_text

#### 对问题的详细解读

LS-RAG 已冻的分账是：

- 生产链：admitted clean → structurize（promptB）→ construct（promptC / dual-channel）→ 向量（`T-O-210` / `T-O-352`）。  
- g0 original = admitted clean body（`T-O-386`），供 traceback / inflation，**不**进向量 required-set。  
- S05 输出四类 typed 对象；raw representation、source-grounded semantics、clean-derived output **分账**（`T-O-62` / `S05-T009`）。

FilterMeta（`realm, type, channel, source_name, is_active`）+ ContextMeta tags 是 **S04 revision semantics**，不是 clean 算法。API 三 provider 已经 `semantic_tuples()` 写出六元组（`semantics.py:55-63`）。acceptance 仅当 `filter_meta` 是 mapping 时展开五维；否则 `filter_metadata` JSON stub 为 `{"source_kind": ...}`（`acceptance_snapshot.py:591-610`）。web/pdf/doc 走 stub。`DEFAULT_SEMANTICS` 却已为 **全部** intake 登记了五维键（`registry.py:229-239`）。

本题钉 **双账本是否四通道强制**，不钉 realm 从 URL 推导还是调用方必填（执行）。

#### 可选的方案清单

| 选项 | 方案 | 含义（产品法） |
|------|------|----------------|
| **A** | **双账本、四通道都写五维；永不进 g0（推荐）** | g0 original = `T-O-386` 的 admitted clean body，禁止把 FilterMeta 序列化进 clean_text。五维 + context tags 作为 S04 revision semantics 落在 **所有** 通道（API 已做；web/pdf/doc 必须从 stub 升级到同构元组）。S06 layered `context_meta` 读 revision 语义，不从 g0 解析。缺五维不得 pretend 已 acceptance-complete。值的来源（调用方 typed 元数据 / 闭集派生）执行阶段定。 |
| **B** | **FilterMeta 仅 API；web/pdf/doc 保持 stub** | 字面遵守 D08-T007「三 provider」。收获页的检索过滤不是五维。`DEFAULT_SEMANTICS` 对非 API 继续空转。 |
| **C** | **把 FilterMeta 写入 clean_text / g0** | 一份正文同时当知识与过滤面。违反 D08-A07「不只进 clean_text」、`T-O-62` 分账、以及 `T-O-386` g0 同一性。 |

#### 当前建议 / 倾向（Grok）

**推荐 A。**

#### 推荐方案的详细说明

选 A 时：

1. **两本账**：clean body（g0 original / S06 唯一原文）⊥ FilterMeta+ContextMeta（S04 revision semantics / 检索过滤 / layered `context_meta` 的权威输入）。  
2. 四通道同一语义合同：五维 + tags 都要在 acceptance 时写进 `mkb_intake_revision_semantics`。API 已是样板（`chinatax.py` / `domain.py` / `realestate.py` 调 `semantic_tuples`）。  
3. 空/缺五维 = 语义不完整，不得靠把 JSON 塞进 `filter_metadata` blob 冒充（今日 stub 是缺口，不是法）。  
4. g0 summary 仍按 `T-O-352` 强制向量；summary **不是** FilterMeta 的藏身所。  
5. 不重开 cuts：NH 仍不改 g0 切法，只保证切的是 clean body、过滤读的是 revision 语义。

#### 支持推荐 / 反对其他方案的证据与 Reasoning

- **反对 B**：`T-O-381` 要四通道走到 **可检索** 向量。S06 合同对全部 structurize 输出要求同一 `context_meta` 键集（`layered_content.py:121`）。B 让 web/pdf 的 Layered 元数据无 S04 权威，模型会从正文幻觉 realm——正是 D08-A07 要防的。`DEFAULT_SEMANTICS` 已登记五维给全部 intake，B 等于让登记空转。  
- **反对 C**：D08-T007 原文「不得只塞进 `clean_text`」（`D08-legacy-capabilities-migration.md:98`）。glossary：FilterMeta **不等于** clean_text。C 还会让 g0 original 随过滤标签漂移，破坏 `T-O-386` digest 与 `T-O-383` replay。  
- **A**：对齐 `T-O-62` 三账本、D08-A07、Q6-A、以及 acceptance 已经为 API 走过的路径。遗产 dedicated 把 FilterMeta 放在 member 对象而不是正文（三套 `*FilterMeta`）；借分账，不借隧道/skip。

#### 问题（请业主裁决）

**Q9：语义分账选 A / B / C？若选 A，是否确认：g0 original 只等于 admitted clean body；FilterMeta 五维 + context tags 作为 S04 revision semantics 对四通道强制；禁止写入 clean_text/g0；web/pdf/doc 不得再以 `{"source_kind"}` stub 冒充五维；值的具体派生算法本轮不锁？**

- **业主回答**：接受推荐 **A** 全部确认句。→ **冻结为 `T-O-389`**
- **裁决状态**：`accepted / frozen`

---

## 8. 第 4 轮 foundational QNA：确认不注入

> 中场评估 II 的预判：若业主整包接受 Q7-A / Q8-A / Q9-A，则不需要 Round 4。业主已整包接受。本条由预判改为 **确认**。

- **判定**：不注入 Round 4 foundational QNA。  
- **原因**：推荐包装已把产品法定死（闭集、三轴、声明式晚绑定、kind 图、再获取信封、上传身份、clean/g0 合同、五维分账）。余项见 §10.2 执行延期表。  
- **曾列的 Round 4 触发条件均未发生**（未选 mega+吞 scatter、未跨图再获取、未改写 Q2-B、未把元数据写入 g0）。

---

## 9. ★ 中场评估 III（Round 3 → 收口）`[核心·锁死]`

- **9.1 对 Round 3 的判定**：三题均决断，且均为推荐项。最关键的一手是 **Q7-A + Q8-A 成对**：kind 选图使 `http_resource` 一张无环图能画出 static→browser 正向边，从而把已冻 Q2-B「空壳 → browser」落成声明式边，而不是换 revision（Q4-C，已否）或暗升（`T-O-378`）。Q9-A 把 `T-O-386` 的 g0 与 D08 五维收成双账本。无 OPEN 残题。
- **9.2 本轮已锁定真相**：`T-O-387` kind 家族图基数；`T-O-388` 绑定前有限正向再获取 + decode 观察；`T-O-389` FilterMeta 四通道强制且永不进 g0。
- **9.3 诚实反方制衡**（执行风险，**不是**新的 foundational 分叉）：
  - kind 图会变宽：`http_resource` 必须同时看得见 static/browser/print 与三条 web 策略；`local_object` 必须同时看得见 pdf/doc/image。守卫谓词闭集今日看不见表示（`models.py:245-258`）——`T-O-384` 已授权扩展登记，规划必须把谓词当代码登记，不是自由表达式。  
  - `s05_binding_digest` 从 Task 创建推迟到清洁边选定（HEAD 在 `task_create.py:180` 即写入）。这是晚绑定的实现后果，须按 §9.5.2 与 `S03-T017`/`T053` 和解，不得在规划里再冻一份「创建时已含清洁工人」的 digest。  
  - FilterMeta 值从哪来（调用方必填 vs URL/文件派生）未锁。缺值不得 acceptance-complete（`T-O-389`），但填值算法属执行。  
  - 再获取「有限」的上限若被做成隐式 while，会滑回 Q3-B。产品法已禁 try-all；规划必须把边画成静态 DAG。
- **9.4 收口或 Round 4**：收口。Round 4 **不注入**。见 §8。
- **9.5 全量冲突审查**：见下一节。审查对象 = 本文件 §1 的 `T-O-376..389` 加被它们显式 CITE 的上游（`T-O-42` / `T-O-62` / `T-O-208` / `T-O-210` / `T-O-340` / `T-O-352` / `S03-T007/T011/T012/T013/T017/T038/T053` / `S05-T002` / D08-T007 / S13 完成定义第 7 条）。

---

## 9.5 ★ 全量冲突审查（收口前 MUST）

> 目的：确认冻结细节 **没有实际产品法冲突**。表面时序差、窄 reopen、窄执行解释，若已在后冻 T-O 里写明顺序与边界，则记为 **和解**，不记为冲突。

### 9.5.1 审查结论

**未发现实际冲突。** 发现 8 处需要规划遵守的 **和解关系**（时序 / 窄 reopen / 窄解释）。无一处要求修订已冻 T-O 正文，无一处要求 Round 4。

### 9.5.2 和解关系（不是冲突）

| # | 表面张力 | 为什么不是实际冲突 | 规划必须遵守的顺序 / 边界 |
|---|----------|--------------------|---------------------------|
| 1 | `T-O-379` 三轴含 acquire vs `T-O-387` 不再用 mode 选图 vs `T-O-388` mode 只是起点 | 三轴仍是坐标：**kind 选图、acquire/strategy 在图内取值**。`T-O-379` 从未把 acquire 冻在 Task 创建；Q2-B / `T-O-382` 已把清洁工人推迟到表示已知之后。`T-O-388` 只是把同一法扩到获取轴。 | 调用方仍交 typed `source_kind` + 可选起点 `acquisition_mode`；**不得**把 mode 当 `workflow_key`。最终 acquire capability 以封闭后的 `s05_binding_digest` 为准。 |
| 2 | `T-O-383` 绑定后不换工人 vs `T-O-388` 可再获取 | 再获取发生在 **清洁工人绑定之前**。绑定后仍 fail-loud、不换清洁工人、不 try-all-acquire。 | digest 封闭时刻 = 清洁边选定（`T-O-384` + `T-O-388`），覆盖实际走过的 acquire 路径。封闭后再获取 = 违规。 |
| 3 | `T-O-340` 禁静默换工人 vs 晚绑定 / 再获取 | `T-O-382` 已定性：这是绑定 **前** 的显式、可配置、进 evidence 的决策，不是静默换。`T-O-384` 要求边必须预先画在 revision 上。 | 无声明边的 handler 升级（今日写假 `browser_profile`）仍属 `T-O-378` 反例，必须删除。 |
| 4 | `S03-T017` Execution 创建绑 revision vs `T-O-384` digest 选边后封闭 vs HEAD 创建时已写 `s05_binding_digest`（`task_create.py:176-180`） | `S03-T017` 冻的是 **workflow/revision/compiled digest**，创建即绑、retry 不热切 **图**。`S03-T053` 要求最终引用 **actual** S05 acquisition/clean binding 与 `s05_binding_digest`，retry 不可热切 **已封闭** 的 digest。晚绑定把「actual clean」推迟到表示已知，不是换另一张 revision（那是已否的 Q4-C）。未封闭 ≠ 已绑清洁工人。 | 创建时：exact workflow revision + compiled digest。运行中：选边后 **一次** 封闭 `s05_binding_digest`。retry/resume 重放封闭值。禁止用后一次选边覆盖已封闭 digest。 |
| 5 | `S03-T011` 无环 vs `T-O-388` 再获取 | 再获取是 **不同 `step_key` 的正向边**（禁止自边 `models.py:389-390`，禁止环 `432`）。不是回到同一个 `acquire` 步骤。 | 规划必须把 static-acquire 与 browser-acquire 画成两个步骤。while/retry 获取不是图。 |
| 6 | `S03-T038` 单 root 贯穿 vs kind 家族多张图 vs scatter | 每个 Task 仍是 **一个** root Execution 绑 **一张** revision 贯穿 ingress→publication。家族是 registry 里的有限几张程序，不是一次运行换图。scatter 仍是 root+child（`S03-T013`/`T039`，`T-O-387` 明文不并入 mega）。 | 禁止 decode 后 `resolve_by_key` 另一张图。 |
| 7 | S13「无公网 object API」（完成定义第 7 条）vs `T-O-381` 必须上传 vs `T-O-385` 窄 reopen | `T-O-385` 是对第 7 条的 **窄 reopen**：受鉴权 Port 暴露 handle，**不**让对象存在定义业务成功，**不**创造 S04 身份。bytes-first / CAS / GC / verify-on-read 仍在。 | 上传 ≠ ingest。无后续 ingest 的对象走 orphan/GC。purpose 字面执行阶段登记。 |
| 8 | `T-O-208`/`T-O-210` promptA@clean vs `T-O-386` 仅 `llm_required` 强制模型 vs D08-T007 仅三 provider vs `T-O-389` 四通道五维 | `T-O-386` 是业主接受的 **窄执行解释**：第一环永远是 admitted clean；模型子环仅 LLM 策略。确定性/API 仍是 clean，不是跳过 A。`T-O-389` **扩展** D08-T007 到四通道（五维进 revision semantics，不进 g0），不废除 API 样板，也不改 `T-O-352`（g0 original 留 construct，向量只强制 summary）。 | 禁止为通道另写 structurize kernel。禁止把 FilterMeta 写入 clean_text。禁止用 g0 summary 藏过滤维。 |

### 9.5.3 已排除的假冲突

| 假冲突 | 排除理由 |
|--------|----------|
| `T-O-376`「每条路径必须出向量」vs `T-O-383`「坏文件不出向量」 | Q3 已分账：路径能出 ≠ 每个文件必须出。 |
| `T-O-378`「无层今日死在 decode」vs `T-O-388` decode 观察 | `T-O-378` 是 HEAD 谎言清单（必须换真路径），不是「decode 必须失败」的产品法。 |
| `T-O-381` 公共上传 vs `T-O-385` 不创造 Item | 两步：S13 字节 → S04 ingest。completeness 要的是上传面，不是上传即 Item。 |
| `T-O-384`「一张或有限几张」vs `T-O-387` kind 家族 | `T-O-384` 正文把张数交给 Q7；`T-O-387` 闭合括号。append-only，不改写 `T-O-384`。 |
| `T-O-376` 不重写 cuts/g0 vs `T-O-386`/`389` 钉 g0 输入 | 不改切法；只钉切的是 clean body、过滤读 revision 语义。 |

### 9.5.4 审查后仍开放、但 **不是** foundational

全部列入 §10.2。不得借「冲突未解」重开 Q10。

---

## 10. 收口（全轮冻结）

- **冻结判据**：方向钉死；§1 `T-O-376..389` 全冻结；Q1–Q9 无 OPEN；Round 4 确认不注入；冲突审查无实际冲突。  
- **本文件状态**：`frozen`。  
- **交接**：§1 Truth-Gate 台账 → `planning-initial` §2 CITE。下一步是 **planning-initial**，不是 action-plan，不是 Round 4 QNA。  
- **v0.1 Q1–Q3** 保持作废，不得 CITE。

### 10.1 冻结产品法一览（供 planning 入口）

1. 四通道全部 live-to-vector；禁止诚实未部署；上传/CRUD/幂等/竞态/动态路由/unit+e2e 属于 completeness（`T-O-376`/`381`）。  
2. 零 CF/SMCP 栈；四类 source kind；禁 `action_branch`；禁调用方点名 `workflow_key`（`T-O-377`/`379`）。  
3. 清洁工人在表示已知之后、按可配置闭集规则绑定；绑定后 fail-loud、不换工人（`T-O-382`/`383`）。  
4. 晚绑定住在同一 immutable revision 的已声明边；digest 选边后封闭（`T-O-384`）。  
5. 选图 = source_kind 家族；scatter 独立（`T-O-387`）。  
6. 绑定前允许有限正向再获取；decode 观察；禁暗升/环/try-all（`T-O-388`）。  
7. 上传 = S13 handle 窄 reopen；Item 只由 ingest（`T-O-385`）。  
8. 一份 admitted clean / g0；promptA 仅 LLM 策略；四通道五维与 g0 分账（`T-O-386`/`389`）。

### 10.2 显式延期（execution / pre-charter · 登记后不得冒充 OPEN foundational）

| 延期项 | 权威 | 去向 |
|--------|------|------|
| `.experiment` 发车日 | `T-O-380` | planning-initial 调度，或不进本战役 |
| PDF 真文本层库、OCR/Vision 运行时、浏览器二进制 | 本文件范围栏 | planning-initial 执行节 |
| charset / canonical digest 合同版本 | 本文件范围栏 | 执行 |
| promptA 目录 id 三套对齐 | `T-O-386` 不锁正文版本 | 执行 |
| 上传 HTTP 路径、multipart、S13 `purpose` 字面 | `T-O-385` | 执行（须登记进 purpose 闭集） |
| 守卫 `predicate_type` / `expected_value` 字面 | `T-O-384` 授权扩展登记 | 代码登记，不是自由表达式 |
| 具体 `step_key`、是否多一个 CONTROL | `T-O-384`/`388` | 执行；必须无环、正向 |
| L3 `profile_id` 允许名单改写 | `T-O-379` 已禁 `workflow_key` | 执行；规则住在 compiled revision |
| FilterMeta 值派生（调用方 vs URL/文件） | `T-O-389` | 执行；缺值不得 acceptance |
| PDF 页在 **一个** Item 的 clean body 内如何拼接 | `T-O-376` 不重开 cuts/scatter | 执行 |

---

## 11. 使用约束（本文件特化）

- Round 1 已冻：live 闭集 / 晚绑定时刻 / 绑定后失败法。  
- Round 2 已冻：声明式晚绑定住所 / 上传法律身份 / clean 对 LS-RAG 的同一性。  
- Round 3 已冻：kind 家族图基数 / 绑定前再获取信封 / FilterMeta 与 g0 分账。  
- 全轮冻结后只引 `Q 编号 + 业主回答` 与 §1 `T-O-*`。  
- 执行细节见 §10.2，不进本文件修订，除非推翻真相（须新 append）。

---

## 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-08-29 | Grok | 初稿：Q1 完整口径允许未部署（**业主否决**） |
| v0.2 | 2026-08-29 | Grok | **Reframe**：业主「全部接通、live-to-vector、上传/CRUD/幂等/竞态、路由可动态配置」。作废 v0.1 Q1–Q3。重写 Q1 live 闭集、Q2 动态路由、Q3 绑定后失败法。`T-O-376` 正文替换 |
| v0.3 | 2026-08-29 | Grok | Round 1 业主整包接受 Q1-B/Q2-B/Q3-A；冻结 `T-O-376..383`；中场评估 I；注入 Round 2 Q4–Q6（声明式晚绑定 / 上传身份 / clean 合同） |
| v0.4 | 2026-08-29 | Grok | Round 2 业主整包接受 Q4-A/Q5-A/Q6-A；冻结 `T-O-384..386`；中场评估 II；注入 Round 3 Q7–Q9（图基数 / 再获取信封 / FilterMeta 与 g0 分账）；§8 分析：**接受推荐包装则不需要 Round 4 foundational** |
| v0.5 | 2026-08-29 | Grok | Round 3 业主整包接受 Q7-A/Q8-A/Q9-A；冻结 `T-O-387..389`；中场评估 III；全量冲突审查（无实际冲突、8 处和解）；确认不注入 Round 4；**整份 QNA 收口 `frozen`** |
