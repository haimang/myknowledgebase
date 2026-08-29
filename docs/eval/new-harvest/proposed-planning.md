# new-harvest —— proposed-planning（planning · 站② proposed）by GPT

> **stage**：`proposed`（planning 链站②；`NH-RA` 评估流水线站③·收窄/重锚）
> **作者**：`GPT`（panel：`none`；消费 `new-harvest-reference-anchor` analysis/review/fix fleet 制品）· **时间**：`2026-08-29`
> **本链 scope-fence**：阶段族 `new-harvest` 下 `intake-four-channel-live` 链；把 `inline_payload / local_object / http_resource / registered_api` 四类来源经真实 acquire/decode、已登记 clean、S04 acceptance、既有 LS-RAG publication/retrieval 接成可证明闭集。
> **文档性质（自宣告）**：**取代 [`initial-planning.md`](initial-planning.md)**，作 `pre-charter-qna.md` 前唯一精炼工作基线；本文冻结零决策，只 CITE `T-O`、析出 `T-R`、给出 gated DAG/AP，不替 owner 回答 §8。
> **上游权威输入**：[`pre-initial-planning-qna.md`](pre-initial-planning-qna.md) v0.5 frozen；[`initial-planning.md`](initial-planning.md) v0.1 draft；[`assessment-index.md`](assessment-index.md) v0.2；[`reference-anchor/`](reference-anchor/) 九面分析；HEAD `1221aa1`。
> **下游消费者**：`planning-final`（站③）+ `docs/eval/new-harvest/pre-charter-qna.md`（owner-gate 裁决）+ 后续 `docs/plan/new-harvest/AP-NH*.md`。
> **文档状态**：`draft`
> **phase / AP 命名**：从 `NH1` 开始；本态拟派生 `AP-NH1`…`AP-NH9`。工作项 `NH{n}-{nn}`；测试 `NH-A-{face}-{nn}` 沿用 assessment 稳定 ID，新增横切 gate 以 `FG-NH-*`、崩溃窗以 `W-NH-*` 标识。
> **零推荐声明**：§8 只登记待裁问题、影响和所需裁决制品；不列候选赢家，不给 owner 推荐答案。

---

## 0. TL;DR `[核心]`

- **核心论点**：new-harvest 不是“补四个 cleaner”，也不是把 13 张 profile 线性图机械压成 3 张图；它是一次有明确保留面的 substrate 收敛：保留七表无环/pin/CAS、10 strategy/9 capability/3 API operation、S04/S13、system g0、publication tail 与 lifecycle；净新增 selected-output 汇合、typed representation history、actual S05 两阶段封闭、公共上传缝、真实本地 runtime supply、非 API 五维权威与 retrieval facet，并把四层证明嵌入每个 AP。
- **本态相对 initial 的 supersession**：从“5 相位 = 5 AP、NH1→NH3→NH4→NH5，失败法最后补”改为“`AP-NH1` 承重合同/证明基线 → `AP-NH2/NH3` 图与 binding substrate；`AP-NH4/NH5` 可并行；`AP-NH6` runtime；`AP-NH7` vertical activation；`AP-NH8` lifecycle/compat；`AP-NH9` 总闭合”，并让 assurance 从 NH1 横贯 NH9（← `T-R-NH-02/04/09/16/18/19`）。
- **本态新增 reference-checked 真相**：21 条 `T-R-NH-*`。对 initial 14 条 `T-P`：4 条 `KEEP`、9 条 `REFRAME`、1 条 `CLOSED`；最大关闭项是 `T-P-NH-13`——两阶段 actual S05 不是普通实现后果，而是必须显式处理的 truth-to-schema 冲突。
- **水位判断**：事实输入足以写 proposed；owner-gate 尚未裁、九面 analysis 仍为 `draft`，因此本文可以 `draft/reviewed`。§8 承重问题与 S05 truth erratum 未关闭前不得形成 planning-final；planning-final 必须把 NH1 写成 chosen-shape 的首个 stop/reopen gate，NH1 exit 未通过前不得施工 NH2–NH9。
- **反镀金总则**：函数存在、图能 bootstrap、Task `succeeded`、`publication_ready`、503、monkeypatch、无 namespace 的 search 调用、`.experiment` 骨架，均不是通道完成。

### 0.1 进门 / 出门裁定

| 动作 | 本态裁定 | 原因 |
|---|---|---|
| 以九面事实编写本 proposed | `GO` | index 明定下一站；HEAD 仍为 `1221aa1`，分母未漂移 |
| 再做同范围 reference-anchor | `NO` | 已有 HEAD/legacy/WEB 正反例、substrate-fit、gap、contract、test grid；仅需在本态交叉归并 |
| 在 owner-gate 未裁时冻结 planning-final | `NO-GO` | graph merge、S05、runtime、semantic/upload 产品边界仍会改变 schema/API/DAG |
| 直接按 initial 五 AP 施工 | `NO-GO` | `T-P-NH-1/2/13` 已被证伪或重构 |
| 重写 `intake/`、g0、publication tail、S13 CAS | `NO-GO` | 已交付资产；只允许围绕 gap 重 substrate 或接线 |

---

## 1. Reference anchors / 输入与依据 `[核心]`

### 1.1 输入台账

| 输入 | 类型 | 提供了什么 | 锚点 |
|---|---|---|---|
| `pre-initial-planning-qna.md` v0.5 | `qna / frozen` | `T-O-376..389` foundational 产品法；planning 不扩冻 | [`pre-initial-planning-qna.md`](pre-initial-planning-qna.md) |
| `initial-planning.md` v0.1 | `initial-plan` | `T-P-NH-1..14`、五相位 first-cut、待裁工作项 | [`initial-planning.md:64`](initial-planning.md#22-暂定前提provisional--待-proposed-证实证伪) |
| GPT initial critique | `eval / reviewed` | one-of binding、S05 冲突、opaque doc、facet、AP/DAG 重切与 SG-0..7 | [`thoughts-on-initial-planning-by-GPT.md`](thoughts-on-initial-planning-by-GPT.md) |
| assessment index v0.2 | `assessment / index` | HEAD 冻结分母、9 面 ownership、18 个 canonical owner-gate、勿重做清单 | [`assessment-index.md`](assessment-index.md) |
| 面 01 | `reference-anchor` | graph algebra、kind identity、selected-output merge、old pin | [`assessment-analysis-01-workflow-graph-and-kind-family.md`](reference-anchor/assessment-analysis-01-workflow-graph-and-kind-family.md) |
| 面 02 | `reference-anchor` | policy/actual S05、seal CAS、ProcessCommand、recovery 三窗 | [`assessment-analysis-02-s05-two-stage-binding-and-recovery.md`](reference-anchor/assessment-analysis-02-s05-two-stage-binding-and-recovery.md) |
| 面 03 | `reference-anchor` | representation fact、MIME/opaque/PDF、history/reacquire、print honesty | [`assessment-analysis-03-representation-and-reacquisition.md`](reference-anchor/assessment-analysis-03-representation-and-reacquisition.md) |
| 面 04 | `reference-anchor` | 10/9/3 clean 闭集、admitted-clean、promptA、zero/member 分账 | [`assessment-analysis-04-clean-capability-and-admitted-clean.md`](reference-anchor/assessment-analysis-04-clean-capability-and-admitted-clean.md) |
| 面 05 | `reference-anchor` | PDF/browser/multimodal supply、binary protocol、readiness/security/license | [`assessment-analysis-05-runtime-adapters-readiness-and-security.md`](reference-anchor/assessment-analysis-05-runtime-adapters-readiness-and-security.md) |
| 面 06 | `reference-anchor` | upload、bounded write、catalog/hold、CAS/GC/read boundary | [`assessment-analysis-06-public-upload-and-object-lifecycle.md`](reference-anchor/assessment-analysis-06-public-upload-and-object-lifecycle.md) |
| 面 07 | `reference-anchor` | 五维双账本、S06 overlay、retrieval facet、channel collision | [`assessment-analysis-07-semantic-ledger-and-retrieval-facets.md`](reference-anchor/assessment-analysis-07-semantic-ledger-and-retrieval-facets.md) |
| 面 08 | `reference-anchor` | publication/retrieval、七意图、exact-clean、single/scatter proof | [`assessment-analysis-08-publication-and-intake-lifecycle.md`](reference-anchor/assessment-analysis-08-publication-and-intake-lifecycle.md) |
| 面 09 | `reference-anchor` | fail-loud/replay/race/compat、四层 proof、fake-green grid | [`assessment-analysis-09-assurance-replay-concurrency-and-compatibility.md`](reference-anchor/assessment-analysis-09-assurance-replay-concurrency-and-compatibility.md) |
| HEAD | `code / measured` | 所有 `T-R` 的现状权威；基线 commit 未漂移 | `1221aa1`；各 `T-R` 的 `file:line` |

### 1.2 正例 / 反例 / 可参考对象过滤结果

| 面 | HEAD 正例（保留） | HEAD / legacy 反例（禁止复制） | 外部/legacy 可参考对象如何降级进本仓 |
|---|---|---|---|
| 01 graph | 七表无环、登记 guard、compiled digest pin、compat definitions | 单 input 无汇合、13 profile 克隆、mode/media 选图；legacy `action_branch` | 只借声明式 choice/join 的失败法；不引入 Temporal/SFN/CWL/BPMN runtime |
| 02 binding | Task fingerprint、Process fence、Outcome 同 UoW、Candidate seal | domain digest 冒充 actual；legacy restart 热切 branch/先发队列 | 只借 durable choice 后不重选、at-least-once 下 CAS/幂等；不引 event-history 引擎 |
| 03 representation | MIME mismatch、URL 脱敏、image 空文本观察、browser/static 端口分离 | PDF 字面量扫描、OCR 盗码、单槽 evidence、docx UTF-8、常量 renderer | 只借 MIME/OPC/PDF/print 协议和安全失败法；库与隔离留 gate |
| 04 clean | 10 strategy、9 capability、3 operation；33 tests；strict API map；g0=clean | 6 图选不中、prompt 三哈希、legacy empty/silent skip/R2 success | 借 branch 语义和 FilterMeta 字段，不借 branch taxonomy、CF/Gemini/R2 |
| 05 runtime | 注入端口、三池/ConcurrencyGate、EgressPolicy、SupplyFence、CLI 拒 binary | 默认根 0/0、binary 协议缺失、同进程假 PDF、`/ready` 假证明 | 可参考 parser/browser/OCR/vision 的能力与限制；不得因流行度冻结库或栈 |
| 06 upload | team CAS、verify-on-read、catalog unique、GC quarantine/recheck | public upload=0、purpose=0、`promote(bytes)` 直接暴露、legacy presign/R2 | 借 resumable/checksum/lease 机制；身份仍为本仓 digest/size/catalog |
| 07 semantics | API 六元组、S04 semantic table、system g0、unknown filter fail-closed | 非 API stub、模型 context 权威、facet=0、legacy JSON/R2 metadata SSOT | 借 facet/provenance/字段分账；不引 Qdrant/ES/CF payload 栈 |
| 08 publication | single/child 共用 tail、proof、pointer/serving CAS、lifecycle withdraw | `publication_ready`/Task success、无 namespace search、reclean、legacy output key success | 借 alias cutover/OCC/soft-delete 失败法；仍落 SQL pointer/CAS |
| 09 assurance | fingerprint、Gate/Process/object CAS、compat pin、fan-in failure | monkeypatch、sqlite3-on-Turso、source `running`、缺关键负测 | 借 replay/version/fault-window 方法；不引 Kafka/Temporal/DST runtime |

### 1.3 证据使用纪律

1. `T-R` 以 HEAD `file:line` 为现状权威；analysis 的 `RA-*` 负责正反例、限制与 substrate-fit，不反向证明 HEAD。
2. 九面仍为 `draft`；本态引用稳定 gap/RA/Test-ID，不把其 owner-gate 候选写成已冻法。
3. canonical gate 编号只认 `assessment-index.md` v0.2 的 `G-NH-01..13,15..19`。面 04/05/08 的少量旧交接字样不传播；`G-NH-14` 故意空号。
4. 外部来源只贡献机制/失败法；零 CF/R2/SMCP/动态插件/自由表达式回流。

---

## 2. 规划真相台账（Planning Truth Register · 站②）★ `[核心]`

### 2.1 继承 foundational truth（CITE，不自冻）

| Truth-ID | 本态使用的一句话约束 | 来源 |
|---|---|---|
| `T-O-376` | 四通道真实 Process→可检索；503、0815-R7、假接线不算完成 | QNA v0.5 |
| `T-O-377` | 四 source kind；`intake/` 为变换 SSOT；零 CF/SMCP；禁 `action_branch` | QNA v0.5 |
| `T-O-378` | 表示/测试诚实：假 PDF、盗码、monkeypatch、空 clean 均不得冒充完成 | QNA v0.5 |
| `T-O-379` | 三轴 = kind × acquire × strategy；caller 禁 `workflow_key` | QNA v0.5 |
| `T-O-380` | unit/e2e 属 completeness；`.experiment` 发车日 OPEN | QNA v0.5 |
| `T-O-381` | 10 strategy + 3 API operation live-to-vector；上传、七意图纳入 | QNA v0.5 |
| `T-O-382` | 真实表示已知后，在闭集内晚绑工人，并进 evidence/digest | QNA v0.5 |
| `T-O-383` | 绑定后不换工人；内容失败不出向量；replay/conflict/upload 同法 | QNA v0.5 |
| `T-O-384` | 同一 immutable revision 预声明 live 边，只用登记 guard/control；选边后 seal | QNA v0.5 |
| `T-O-385` | 公共上传只造 S13 handle/digest/size，不造 Item；随后独立 ingest | QNA v0.5 |
| `T-O-386` | 四通道同一 admitted clean→S06/g0；promptA 仅 LLM；不复制 kernel | QNA v0.5 |
| `T-O-387` | public 选图只看 source kind；三 single-root + scatter root/child | QNA v0.5 |
| `T-O-388` | 绑定前仅有限、声明式、无环正向再获取；print_pdf 必须诚实 | QNA v0.5 |
| `T-O-389` | 五维+tags 四通道强制进 S04、不进 g0；stub 不得 complete | QNA v0.5 |

### 2.2 新增 reference-checked truth（本态析出）★

| Truth-ID | 类型 | 真相内容（一句话） | 来源（HEAD + RA） | 证实/证伪 initial T-P | 触发的 AP/DAG 调整 |
|---|---|---|---|---|---|
| `T-R-NH-01` | `HEAD denominator` | HEAD 是 13 single-root、7 public、6 unselectable、2 scatter；不是 12/7+5 | `lsrag_definition.py:929-940,1003-1069`; `RA-01-HEAD-09` | 证伪 initial 的基数叙事；重构 `T-P-NH-1/2` | NH1 固定迁移清册；NH2 做 kind identity |
| `T-R-NH-02` | `HEAD / graph` | 单 target input 仅一 binding，runtime 无 selected-output merge；human review 不证明多分支汇合 | `workflow/models.py:496-497`; DDL `001_initial.sql:1770-1771`; `NH-RA01-B01/B09` | 证伪“只并 profile 即可”；重构 `T-P-NH-1/2/3` | NH1 先 spike；NH2 单列 graph algebra |
| `T-R-NH-03` | `HEAD / selector` | public resolver 仍以 mode/media 选 7 profile，6 live 图 caller 选不中 | `src/services/config_snapshots.py:500-516`; `src/services/workflow_registry.py:94-103`; `NH-RA01-B03..B07` | 重构 `T-P-NH-1/14` | NH2 owns kind resolver/compat，不交给能力 AP |
| `T-R-NH-04` | `truth conflict / schema` | `s05_binding_digest` 创建时被写成 domain digest，NOT NULL 且无 UPDATE；这不是 actual S05 | `task_create.py:179-180`; DDL `:245-246`; `NH-RA02-B01..B04/B08` | **证伪 `T-P-NH-13`** | NH1 做 migration/seal spike；NH3 实施 policy/actual 分账；truth erratum 成前置 |
| `T-R-NH-05` | `HEAD / evidence` | acquire/decode evidence 各单槽、reacquire 边 0、representation guard 0，无法 digest 实际路径 | `acquisition_ingest.py:579-593,597-676`; `NH-RA03-B03/B04` | 深化 `T-P-NH-9` | NH3 新增 durable history/fact；NH2 只消费 typed fields |
| `T-R-NH-06` | `HEAD / representation` | PDF 是 literal regex；无层盗 OCR 码；从不产 print_pdf；opaque/OPC 可能死于 UTF-8 | `src/runtime/intake/types.py:144-199`; `src/runtime/intake/acquisition_ingest.py:533-564`; `NH-RA03-B01/B02/B05/B06/B11` | 证实 `T-P-NH-4/5`，新增 opaque case | NH3 冻 representation；NH6 供真实 parser/browser；NH7 做 vertical proof |
| `T-R-NH-07` | `HEAD / delivered` | 10 strategy、9 clean capability、3 API operation 的纯函数闭集已在，选定 33 tests 绿 | `strategies.py:15-151`; `intake/__init__.py:20-132`; `RA-04-HEAD-05` | 重构 `T-P-NH-14` 与 initial NH3 | NH7 只 activation/contract，不重写 `intake/`；API 为 preservation lane |
| `T-R-NH-08` | `HEAD / prompt` | 7 个 LLM strategy 钉 promptA，但三套默认 id/正文/哈希互斥 | `src/contracts/intake/strategies.py:57-147`; `src/services/config_snapshots.py:57-59`; `src/services/prompt_profiles.py:50`; `NH-RA04-B04` | 证实 `T-P-NH-10` | NH1 登记迁移；NH7 在 live 前对齐并回归 |
| `T-R-NH-09` | `HEAD / runtime` | 默认根 browser/clean_llm=0；生产依赖无 PDF/browser/OCR；S11/CLI 不能运 binary | `api/app.py:330-345`; `pyproject.toml:13-21`; `inference/models.py:96-108`; `claude_cli.py:505-508`; `NH-RA05-B01..B04` | **证伪 `T-P-NH-6` 的“现协议可复用”部分** | NH6 独立 runtime AP；NH1 保留选型/协议 spike；不以池名替代协议 |
| `T-R-NH-10` | `cross-source / security` | readiness 只探模型名单；PDF/browser/原生依赖必须逐能力处理隔离、license、CVE 与负样本 | `src/runtime/health.py:16-25`; `src/llm_adapters/local_vllm.py:276-295`; `NH-RA05-B05/B06/B11/B12` | 深化 `T-P-NH-4/5/6` | NH6 必含 supply identity/readiness/security/SBOM，不只是注入函数 |
| `T-R-NH-11` | `HEAD / upload` | S13 CAS/verify/catalog/GC 内核可用，但 public upload route=0、caller-upload purpose=0 | `api/public/routes.py:56-452`; `storage/models.py:17-27`; `NH-RA06-B01/B02` | 证实并深化 `T-P-NH-8` | NH4 可在 NH1 后独立并行；不依赖 kind graph施工完成 |
| `T-R-NH-12` | `HEAD / upload lifecycle` | `promote(bytes)` 不写 catalog/ref、全内存；未 catalog 对 GC 不可见，catalog 无 ref 又等同 orphan | `src/storage/ports.py:10-24`; `src/storage/local_store.py:71-105`; `src/services/object_gc.py:146-161`; `NH-RA06-B03..B05` | 重构 `T-P-NH-8` | NH4 增 bounded-write + catalog/hold + GC race，不只是 HTTP route |
| `T-R-NH-13` | `HEAD / semantics` | registered_api 已写严格五维+tags 六元组；非 API 三 kind 实际写入 0，stub 仍可 complete | `src/contracts/intake/semantics.py:12-63`; `src/runtime/intake/acceptance_snapshot.py:589-615`; `NH-RA07-B01/B02` | 重构 `T-P-NH-7` | NH5 建权威输入/派生缝和 acceptance gate；API 仅回归 |
| `T-R-NH-14` | `HEAD / projection` | S06 不读 S04 semantics；public FilterMeta facet=0；`channel` 与 original/summary 撞名 | `generation_construct.py:330-343`; `generation_assemble.py:51-60`; `retrieval/models.py:14-34`; `NH-RA07-B03..B05` | 新事实，证伪 initial NH4 的中等深度 | NH5 同时 owns S06 overlay、facet、public naming；NH7/8 消费 |
| `T-R-NH-15` | `HEAD / delivered` | system g0、single/child publication tail、proof、pointer/serving CAS、lifecycle withdraw 已在 | `generation_assemble.py:17-62`; `lsrag_definition.py:169-214`; `vector_publish_commit.py:57-191`; `NH-C-70..79` | 证实“不重开生成面”，重构 `T-P-NH-1/3` | NH7/8 接通和验收，禁止重写 tail/g0/scatter |
| `T-R-NH-16` | `HEAD / fake green` | 现有 single/rebuild search 缺 namespace 必 422；API scatter 无 search；source e2e monkeypatch 且停 running | `src/contracts/api/models.py:505-509`; `src/services/retrieval/retrieval_request.py:265-269`; `tests/e2e/test_source_capability_paths.py:99-101,166-168`; `NH-RA08-B01/B02` | 证伪 initial 对既有 e2e 水位的隐含乐观 | NH1 先修 proof baseline；NH7/9 强制真实 query |
| `T-R-NH-17` | `HEAD / lifecycle` | rebuild/changed-metadata 从 frozen clean 入场但仍执行 inline decode+deterministic clean | `lsrag_definition.py:299-306`; `clean_preflight.py:28-127`; `NH-RA08-B04` | 新事实；initial `NH4-04` 深度不足 | NH8 单列 exact-clean + seven-intent AP |
| `T-R-NH-18` | `HEAD / assurance` | fingerprint、无环、Gate/Process/object CAS、compat pin 大半在；actual/上传/四通道/mega 的闭集证明仍红 | `task_create.py:67-104`; `runtime_outcome.py:46-117`; `NH-RA09-B01..B08` | 重构 `T-P-NH-3/11` | NH1 建 proof baseline；每 AP 自验；NH9 只总闭合 |
| `T-R-NH-19` | `test law` | unit/integration/default-root/retrieval-facet 四层不可互换；fault/race 是横切维度 | `NH-C-88`; `NH-A-09-01..20` | 证伪“NH5 最后补证明”；重构 `T-P-NH-1/2/3` | assurance thread 横贯 NH1–NH9；每 AP exit 带四层适用项 |
| `T-R-NH-20` | `substrate-fit` | legacy/web 没有可直接搬的 MKB 同构栈；可借的是语义、失败法、原子切换与隔离约束 | 九面 §3/§7；`T-O-42/377` | 证实全部“借语义不借栈”围栏 | 每工作项强制 `✅/♻️/🆕/⛔`；零 vendor-stack migration |
| `T-R-NH-21` | `HEAD / intent algebra` | 七意图不是 7×4 笛卡尔积：只有 ingest 以 kind 选图，其余按 Item/scope 寻址 | `src/contracts/api/models.py:278-286`; `src/services/config_snapshots.py:138-144,474-501`; `NH-RA08-B05` | 重构 `T-P-NH-1/2/3` | NH8 建合法/非法 intent 表，不制造 28 条通道计划 |

---

## 3. 辨证审核（Δ 裁定 initial）+ 调整溯因 ★ `[核心]`

- **§3.0 裁定对象**：[`initial-planning.md`](initial-planning.md) v0.1，全链 supersede；`pre-initial-planning-qna.md` 不被裁定，只 CITE。

### 3.1 `T-P-NH-1..14` 逐项裁定

| item-ID | 裁定 | 来源前序 | 重分配 phase | 复用 | 驱动真相 | 理由 / 新证据 |
|---|---|---|---|---|---|---|
| `T-P-NH-1` 五相位 DAG | `REFRAME` | initial §2.2/§6 | NH1–NH9 | `♻️` | `T-R-NH-02/04/09/12/14/17/19` | 五个相位混合 substrate、产品面和证明；上传无须等图，runtime/semantic 也不能藏在 NH3/4 |
| `T-P-NH-2` 五 AP 1:1 | `REFRAME` | initial §2.2 | 9 AP | `♻️` | `T-R-NH-02/18/19` | graph、binding、runtime、upload、semantics 的 owner/迁移/风险边界不同；仍不按四通道拆 AP |
| `T-P-NH-3` 七簇 | `REFRAME` | initial Appendix A | 8 功能责任面 + 1 assurance AP | `♻️` | `T-R-NH-18/19/21` | 簇 7 改横切；graph/S05 分责，representation/runtime 分责；publication 只接通 |
| `T-P-NH-4` 真 PDF，库不先选 | `KEEP` | initial §2.2 | NH3 contract + NH6 supply | `♻️/🆕` | `T-R-NH-06/10` | 假实现确认；parser、隔离、license 必须同票但在 owner gate 后施工 |
| `T-P-NH-5` browser 注入 | `REFRAME` | initial §2.2 | NH3 contract + NH6 supply + NH7 e2e | `♻️/🆕` | `T-R-NH-06/09/10` | 不只是组合根参数：还含 binary/driver、egress、sandbox、profile、print/readiness |
| `T-P-NH-6` 复用现推理面/不增池 | `REFRAME` | initial §2.2 | NH1 spike + NH6 | `♻️/🆕` | `T-R-NH-09/10` | 现请求/CLI 不能运 bytes；pool 数与 request protocol 分账，均待 owner 裁 |
| `T-P-NH-7` caller∪派生 | `REFRAME` | initial §2.2 | NH5 | `♻️/🆕` | `T-R-NH-13/14` | “必须有权威”已证，权威来源、unknown、merge 仍由 owner gate；还需 S06/facet |
| `T-P-NH-8` upload purpose | `REFRAME` | initial §2.2 | NH4 | `♻️/🆕` | `T-R-NH-11/12` | purpose 只是一个点；成功事务、bounded stream、catalog/hold、GC/read 才是产品缝 |
| `T-P-NH-9` registered eq guard | `KEEP` | initial §2.2 | NH1 spike + NH2/3 | `♻️` | `T-R-NH-02/05` | 闭集/eq/fail-closed 保留；新增 durable fact authority 与 selected-output consumer |
| `T-P-NH-10` promptA 对齐 | `KEEP` | initial §2.2 | NH1 inventory + NH7 activation | `♻️` | `T-R-NH-08` | 三份正文/哈希实测不同；不在本文选择 canonical id |
| `T-P-NH-11` 实验骨架在 NH5 | `REFRAME` | initial §2.2 | NH9 non-DoD lane | `♻️` | `T-O-380`; `T-R-NH-19` | 骨架只能在闭集证据后准备；发车日仍不进退出条件 |
| `T-P-NH-12` charset 变更另发版本 | `KEEP` | initial §2.2 | deferred / AP 内 reopen trigger | `✅` | `T-O-383`; initial evidence | 本轮 RA 未给出升版必要性；禁止暗改 canonical digest 语义 |
| `T-P-NH-13` S05 推迟只是实现后果 | `CLOSED` | initial §2.2 | truth erratum + NH1/NH3 | `🆕` | `T-R-NH-04` | glossary/S05/D04/DDL 与晚封闭真实冲突；必须 append-only 处理，不得在 AP 偷改 |
| `T-P-NH-14` 所有 kind activation 同一 AP | `REFRAME` | initial §2.2 | NH6 supply + NH7 activation | `✅/♻️/🆕` | `T-R-NH-07/09/15` | pure handlers 保持一处；runtime supply 单列；通道仍只作为 NH7 验收 lane |

### 3.2 initial 工作包重分配

| initial 工作包 | 裁定 | 新落点 | 驱动真相 | 说明 |
|---|---|---|---|---|
| `NH1-01..06` graph/guard/decode/S05/reacquire | `REFRAME` | `AP-NH1` spike；`AP-NH2` graph；`AP-NH3` fact+binding | `T-R-NH-02..06` | 原包跨三种 ownership 和至少两组 migration，不能一枪施工 |
| `NH2-01..04` upload | `REFRAME` | `AP-NH4` | `T-R-NH-11/12` | 保留“两步身份”；增加 stream、catalog/hold、GC/read/race |
| `NH3-01..08` representation+worker | `REFRAME` | `AP-NH3` contract；`AP-NH6` supply；`AP-NH7` activation | `T-R-NH-06..10` | 纯函数勿重写；真实 parser/browser/multimodal 供给是独立高风险面 |
| `NH4-01..04` semantics+publication+lifecycle | `REFRAME` | `AP-NH5` semantics；`AP-NH7` first publication；`AP-NH8` lifecycle | `T-R-NH-13..17/21` | publication substrate 已在；facet、query、exact-clean/intent 分账 |
| `NH5-01..04` proof/experiment | `REFRAME` | NH1–NH8 每 AP exit + `AP-NH9` total closure | `T-R-NH-18/19` | 失败法前移；NH9 不替代 AP 自验；实验不是 completeness |

### 3.3 本态核心转向

**从“先造图、后接工人、最后测”转为“先证明可表达/可迁移，再按 ownership 并行建设，最后以 vertical slice + 四层 proof 合流”**（← `T-R-NH-02/04/07/15/19`）。

---

## 4. 范围与非范围（In/Out-Scope · sized 仍 gated）`[核心]`

### 4.1 In-Scope

| 编号 | 范围 | 规模水位 | gate / truth |
|---|---|---|---|
| `S-NH-01` | graph feasibility、kind identity、selected-output 汇合、旧 pin 共存 | `XL / high` | `T-O-384/387`; `G-NH-02/09` |
| `S-NH-02` | typed representation/history、有限 reacquire、actual S05 两阶段 binding/recovery | `XL / high` | `T-O-382/384/388`; `G-NH-01/03/11/12/13` |
| `S-NH-03` | 受鉴权 public upload、bounded CAS write、catalog/hold、GC、可选 read 分支 | `L / high` | `T-O-385`; `G-NH-07/16` |
| `S-NH-04` | non-API 五维 authority、S06 overlay、FilterMeta facet、命名与 metadata 原子性 | `L / high` | `T-O-389`; `G-NH-05/06` |
| `S-NH-05` | local PDF/browser/print/OCR/Vision/document-understanding supply、readiness、安全、license | `XL / very-high` | `T-O-376/381`; `G-NH-04/10/15` |
| `S-NH-06` | 10 strategy + 3 operation activation 到 admitted clean→publication→retrieval | `XL / high` | `T-O-376/381/386`; `G-NH-08` |
| `S-NH-07` | 七意图合法/非法格、exact-clean、single/scatter lifecycle、compat migration | `L / high` | `T-O-381`; `G-NH-17/19` |
| `S-NH-08` | 四层 proof、replay/conflict/crash/race、default-root 和 retrieval-facet mega | `XL / high` | `T-O-378/380/383`; `G-NH-18` |

### 4.2 Out-of-Scope / 延后

| 编号 | 排除项 | 原因 / reopen trigger |
|---|---|---|
| `O-NH-01` | live chinatax/domain/REA connector、cookie/tunnel/任意 header | `T-O-377/381`；另开 connector campaign 才 reopen |
| `O-NH-02` | 第五 source kind、caller workflow_key、legacy action_branch | frozen fence；仅新 owner Truth 可 reopen |
| `O-NH-03` | cuts/g0 算法、按通道复制 structurize/construct kernel | `T-O-376/386`; generation campaign 才 reopen |
| `O-NH-04` | 前端、chat/answer generation | 非 intake-four-channel scope |
| `O-NH-05` | `.experiment` 发车与评分 | `T-O-380`; owner 另令；NH9 只允许不影响 DoD 的骨架 |
| `O-NH-06` | live 外部云 OCR/browser/R2/CF/Gemini/SMCP 栈 | `T-O-42/377`; 本链只允许 owner 裁后的 local supply |
| `O-NH-07` | charset/canonicalizer 暗改 | 未有 reference-checked reopen；若必要须新 contract version + 新 digest |
| `O-NH-08` | 把九面 analysis 标 frozen | 本链消费其事实，不越权改变 assessment 状态；review/freeze 走该流水线自己的 gate |

---

## 5. 跨阶段贯穿主题（threaded themes）`[核心]`

| 主题 | 贯穿法 | 禁止项 |
|---|---|---|
| Truth / owner gate | S05 冲突 append-only 登记；所有物理/产品选择先过 §8 | AP 内偷改 baseline；把 analysis 候选当 owner 答案 |
| Identity | kind、acquire、representation、strategy、process、prompt、adapter、actual binding 分账 | `action_branch`、process_key 反推所有身份、caller workflow_key |
| Evidence | acquire/decode history append；selected route 与 actual seal 可追溯 | 单槽覆盖、常量 renderer、domain digest 冒充 actual |
| Admitted clean | `intake/` 变换 SSOT；非空 body + digest + strategy/capability evidence | 重写已绿 handler；空 flag/R2 key/Task success 代替 body |
| 双账本 | S04 semantic authority；g0 只等于 clean；S06/facet 为 system projection | 模型 context、stub、正文拼 meta 成权威 |
| Publication | 复用 tail/proof/pointer/serving；每条路径强制 query | 重写 cuts；`publication_ready` 代替 search |
| Security / supply | capability identity、budget、readiness、license、CVE、negative fixture 同交付 | `which`/import/模型名单当 ready；无 sandbox 的默认生产路径 |
| Assurance | 四层不可互换；每 AP 同时交正例、负例、replay/race 适用项 | 把全部失败测试推到 NH9；monkeypatch/503 假绿 |
| Migration | old key/revision/Execution/data 均列 inventory；forward-only；不热切 | 删除旧图让 in-flight 409；把旧伪 s05 当新 actual |

### 5.1 Migration inventory（逻辑编号；物理 migration 号由 action-plan 按 HEAD 顺序分配）

| ID | 迁移对象 | 最小义务 | owned by |
|---|---|---|---|
| `M-NH-01` | policy/actual S05 状态与 digest | 合法 unsealed；一次 seal；旧行兼容标记；forward-only | NH1/NH3 |
| `M-NH-02` | representation/acquire-decode history | typed row或 owner 裁定的 durable authority；有序 path digest | NH3 |
| `M-NH-03` | selected-output merge/guard/control schema | 依 `G-NH-02` 裁决；保持登记、eq-only、无环 | NH1/NH2 |
| `M-NH-04` | 13 single→kind family 与 compat catalog | 旧 compiled digest 可运行；新 resolver 不再 mode/media 选图 | NH2/NH8 |
| `M-NH-05` | upload catalog/session/hold/purpose | upload success、GC、replay 同一事实；不造 S04 identity | NH4 |
| `M-NH-06` | semantic six-tuple/facet/public filter | 单键/blob 同事务；命名兼容；索引/sidecar 回填法 | NH5 |
| `M-NH-07` | promptA catalog/config snapshot | 三 id 的 owner 裁定结果、旧 PromptRef 可解析、hash 不漂 | NH1/NH7 |
| `M-NH-08` | retrieval test/contract namespace | 所有 e2e 使用合法 Layer-A namespace；旧歧义 filter 有迁移说明 | NH1/NH5 |
| `M-NH-09` | lifecycle exact-clean / API Item compat | rebuild/metadata 不热切原 strategy；API child 与事后 Item 同法 | NH8 |

---

## 6. DAG（关键路径 + 并行窗）+ 调整溯因 `[核心]`

> `planning-proposed → pre-charter-qna → planning-final → action-plan` 的治理顺序不变，不另占 `AP-NH0`：§8 owner-gate 与 S05 truth erratum 在 planning-final 前关闭；AP-NH1 对 owner 已裁形态做最小可行性验证。NH1 若证伪任何承重选择，立即停止后续 AP、reopen 对应 gate 与 planning-final，不允许实施中静默换方案。AP 编号从 NH1 开始。

```text
[pre-charter: §8 owner decisions + S05 append-only truth repair]
                                  │
                                  ▼
[planning-final: 冻结 chosen branch、stop/reopen law 与 AP-NH1]
                                  │
                                  ▼
AP-NH1 承重合同 / chosen-shape spike / proof baseline
       │
       ├── spike fail ──▶ STOP + reopen gate / planning-final
       │
       ├──────────────▶ AP-NH4 public upload ───────────────────────┐
       ├──────────────▶ AP-NH5 semantic ledger + retrieval facets ─┤
       ▼                                                           │
AP-NH2 graph algebra + kind family                                 │
       ▼                                                           │
AP-NH3 representation history + two-stage S05                      │
       ├──────────────▶ AP-NH6 runtime supply/readiness/security ───┤
       │                                                           │
       └──────────────────────────────────────────────────────────┐ │
                                                                  ▼ ▼
                       AP-NH7 capability activation vertical slices
                                      │
                                      ▼
                       AP-NH8 lifecycle / exact-clean / compat
                                      │
                                      ▼
                       AP-NH9 closed-set assurance / closure evidence

Join-NH7 = NH2 + NH3 + NH5 + NH6；其中 local_object 公共入口格另需 NH4。
Join-NH8 = NH7 每个适用格已有 admitted clean + S04 semantics + publication/query 证据。
Join-NH9 = NH4/NH8 全部完成；任何 waiver 必须 owner 可见且不能覆盖 T-O-376/378/381/383。
```

### 6.1 AP 依赖与并行窗

| AP | 必需前驱 | 可并行窗 | 加入点 / 被谁消费 |
|---|---|---|---|
| `AP-NH1` | pre-charter owner decisions + S05 truth repair + planning-final 授权 | 无 | 验证 chosen shapes；给 NH2–NH6 提供合同和可信 test baseline |
| `AP-NH2` | NH1 graph/merge/fact-shape spike 通过 | NH4、NH5 | NH3/NH7/NH8 |
| `AP-NH3` | NH2 selected-route identity；NH1 migration spike | NH4、NH5 | NH6/NH7/NH8/NH9 |
| `AP-NH4` | NH1 upload transaction contract；`G-NH-07/16` 已裁 | NH2、NH3、NH5，及 NH6 的非对象部分 | NH7 local_object lane、NH9 GC/race |
| `AP-NH5` | NH1 semantic/retrieval contract；`G-NH-05/06` 已裁 | NH2、NH3、NH4；NH6 前半 | NH7/8/9 |
| `AP-NH6` | NH3 representation/binary contract；runtime/isolation gates 已裁且 NH1 smoke通过 | NH4、NH5 | NH7 |
| `AP-NH7` | NH2+NH3+NH5+NH6；`G-NH-08` 已裁；local-object public lane另需 NH4 | 无大并行；lane 内可按 capability 独立跑 | NH8/NH9 |
| `AP-NH8` | NH7 + NH5；`G-NH-17/19` 已裁；compat inventory来自 NH1/NH2 | NH9 的只读矩阵准备 | NH9 |
| `AP-NH9` | NH4+NH8 + 所有 AP exit evidence | 无 | campaign closure evidence / experiment readiness（非发车） |

### 6.2 DAG 调整溯因

| DAG 变更 | 相对 initial | 驱动真相 | 说明 |
|---|---|---|---|
| 新增 NH1 proof/spike 前门 | initial 直接从 graph 施工 | `T-R-NH-02/04/16/18` | 当前 merge/S05/harness 都未证明，先防大改后返工 |
| graph 与 representation/S05 分成 NH2/NH3 | initial 全塞 NH1 | `T-R-NH-02/04/05` | ownership 与 migration 不同；NH1 先冻接口解除循环依赖 |
| upload 前移并独立并行 | initial 依赖 NH1 | `T-R-NH-11/12` | upload 内核不依赖 kind 图；仅 local_object vertical join 需要二者 |
| semantic/retrieval 前移并行 | initial 在 worker live 后 | `T-R-NH-13/14/16` | authority/API contract 可先建；否则 vertical slice 无诚实终态 |
| runtime supply 独立 AP | initial 藏在 NH3-02 | `T-R-NH-09/10` | binary、部署、安全、license/readiness 是独立高风险闭集 |
| capability 以 vertical slice 合流 | initial “10+3 worker”水平大包 | `T-R-NH-07/15/16` | 每 lane 必须从真实输入走到 retrieval，不把函数绿当 live |
| lifecycle/compat 后置但独立 | initial NH4 一项 | `T-R-NH-17/21` | exact-clean、七意图、old pin 是独立产品法，不是 ingest 尾注 |
| assurance 横贯，NH9 只总收口 | initial NH5 最后证明 | `T-R-NH-18/19` | 每 AP 必须自带 failure/replay/DoD，NH9 不第一次发现功能缺口 |

---

## 7. 逐 phase / action-plan 工作台账 `[核心]`

> `S/M/L/XL` 是相对复杂度，不是日历承诺。每项绑定 reference verdict、HEAD 锚、复用类型与真相；owner gate 未裁时，工作项只能进入 action-plan 草拟，不能选物理方案。

### 7.0 AP 内部 DAG（表中工作项不是无序 backlog）

| AP | 内部执行顺序（`→` 串行；`∥` 可并行） | join / stop 条件 |
|---|---|---|
| `AP-NH1` | `NH1-01 → (NH1-02 ∥ NH1-03 ∥ NH1-08)；NH1-01 → (NH1-04 ∥ NH1-05 ∥ NH1-06)；(02..08) → NH1-07 → NH1-09` | 三 spike、两项 harness、两张 matrix 全有 evidence；任一 chosen shape 被证伪即 stop/reopen |
| `AP-NH2` | `(NH2-01 ∥ NH2-02) → NH2-03 → (NH2-04 ∥ NH2-05 ∥ NH2-06) → NH2-07 → NH2-08` | kind graph/resolver、merge、handler fence 与 old-pin 共同通过；不能只交一张新图 |
| `AP-NH3` | `NH3-01 → NH3-02；(NH3-03 ∥ NH3-04 ∥ NH3-05) → NH3-06；NH3-07 → NH3-08；(NH3-02 ∥ NH3-06 ∥ NH3-08) → NH3-09 → NH3-10` | representation path 与 selected route 都进入 actual seal，三窗 replay 终结 |
| `AP-NH4` | `NH4-01 → NH4-02 → NH4-03；NH4-02 → (NH4-04 ∥ NH4-06 ∥ NH4-07)；NH4-03 → NH4-05；(03..07) → NH4-08` | public upload UoW、replay、ingest handoff、GC/read/security 同时闭合 |
| `AP-NH5` | `NH5-01 → NH5-02 → NH5-03 → NH5-04；NH5-01 → NH5-05 → NH5-06 → NH5-07；(NH5-03 ∥ NH5-04 ∥ NH5-07) → NH5-08` | S04 authority、S06 overlay、facet/query、metadata 原子性对同一 Revision 一致 |
| `AP-NH6` | `NH6-01 → (NH6-02 ∥ NH6-03 ∥ NH6-05)；NH6-03 → NH6-04；NH6-05 → NH6-06；(NH6-02..06) → (NH6-07 ∥ NH6-08 ∥ NH6-09) → NH6-10` | 每项 supply 同时具真实正例、负例、budget、readiness、license 后才注入 default root |
| `AP-NH7` | `(NH7-01 ∥ NH7-02 ∥ NH7-03) → (NH7-04 ∥ NH7-05 ∥ NH7-06 ∥ NH7-07 ∥ NH7-08 ∥ NH7-09) → NH7-10` | 每个合法 lane 独立到 retrieval；一 lane 不得用另一 lane 的成功顶替 |
| `AP-NH8` | `NH8-01 → (NH8-02 ∥ NH8-03 ∥ NH8-04 ∥ NH8-05)；(NH8-02..05) → NH8-06；(NH8-01 ∥ NH8-06) → NH8-07 → NH8-08` | 七意图 single/API、exact-clean、pointer 与 old-pin/actual S05 共同闭合 |
| `AP-NH9` | `NH9-01 → (NH9-02 ∥ NH9-03 ∥ NH9-04 ∥ NH9-05 ∥ NH9-06 ∥ NH9-07 ∥ NH9-08 ∥ NH9-09) → NH9-10；NH9-11 独立且不入 join` | 所有 hard FG 通过、证据包不可变；实验骨架无论成功与否都不改变 closure |

### 7.1 `AP-NH1` · 承重合同、最小可行性 spike 与 proof baseline

**职责**：把“是否可施工”从叙事变成最小证据；修掉会污染所有后续 AP 的 test harness；按 owner 裁定产出 graph/representation/S05/runtime 的稳定接口与 migration inventory。NH1 不声称任何通道 live。

**入口**：§8 影响 NH1/NH2/NH3/NH6 的 gate 已形成 owner decision record；S05 truth conflict 已 append-only 修订；planning-final 已冻结 chosen branch、bounded-spike scope 与 stop/reopen law；HEAD/分母仍为 `1221aa1` 或 index 已先修订。

| 编号 | 工作项（详细设计） | reference 轴 + HEAD 锚 + 避坑 | 复用 | 规模 | 依赖 / 真相 |
|---|---|---|---|---|---|
| `NH1-01` | 冻结执行分母与 migration inventory：4 kind、10 strategy、9 capability、3 operation、13 single、2 scatter、16 compat plan；输出 old-key/revision/compiled-digest/active Execution 清册 | `assessment-index §2.2`; `lsrag_definition.py:929-1080`; `RA-01-HEAD-04/09`；⛔不得继续写 7+5/12 | `✅` | `S` | `T-R-NH-01/03` |
| `NH1-02` | 修复 persistence 测试缝：所有 Turso 状态检查经 `PersistencePort`/服务读，不再 `sqlite3.connect()` 同一文件；fan-in recovery 保留真实 UoW | `test_registered_api_scatter.py:26-33,327,366-367`; README K1；`NH-RA09-B10` | `♻️` | `M` | `T-R-NH-16/18/19` |
| `NH1-03` | 修复 retrieval test contract：建合法 Layer-A namespace fixture，所有 search body 显式带 `namespace_key` 或 `namespace_uuid`，并断言 HTTP 状态、disposition、hit 与 proof，而不是只调用 | `src/contracts/api/models.py:505-509`; `src/services/retrieval/retrieval_request.py:265-269`; `NH-RA08-B02`; `NH-RA09-B04` | `♻️` | `M` | `T-R-NH-16` |
| `NH1-04` | 建最小 immutable graph spike：两个预声明 candidate clean、一个 representation guard、一次 selected-output 汇合、一个共享 seal/tail；覆盖无命中/双命中/缺 fact/环/未知 predicate | `workflow/models.py:245-278,373-525`; `runtime_materialize.py:101-168,505-514`; `NH-N-01-01..04` | `♻️/🆕` | `L` | `G-NH-02/03/09`; `T-R-NH-02/05` |
| `NH1-05` | 建 S05 migration/seal spike：代表性旧 Execution、new unsealed、一次 seal、第二次冲突、seal 前后 crash/retry；验证 policy 与 actual 可区分且 ProcessCommand 可证明指向 actual | DDL `001_initial.sql:225-250`; `task_create.py:167-181`; `runtime_core.py:888-917`; `NH-N-02-01..04` | `♻️/🆕` | `L` | `G-NH-01/11/12`; `T-R-NH-04` |
| `NH1-06` | 为 owner 已裁 runtime 形态做 bounded smoke：真实 PDF text fixture、真实 SPA render+print、真实 image/PDF binary transport各一；记录 dependency identity、资源帽、失败码、license/CVE，不把 smoke 算 live | `pyproject.toml:11-21`; `inference/models.py:96-108`; `NH-N-05-01..05`; ⛔禁止 Protocol stub/`/v1/models` 冒充 | `🆕` | `L` | `G-NH-04/10/15`; `T-R-NH-09/10` |
| `NH1-07` | 生成两张合法矩阵：`strategy↔capability↔representation↔kind` 与七意图 applicability；非法格携 typed expected disposition，不做 10×任意表示或 7×4 笛卡尔积 | `src/contracts/intake/strategies.py:15-151`; `src/contracts/api/models.py:278-286`; `RA-04 §2.3`; `RA-08 §2.3` | `✅/🆕` | `M` | `T-R-NH-07/21`; `G-NH-08/17` |
| `NH1-08` | 建 prompt/config migration inventory：三套 promptA id、正文 hash、消费方、旧 ConfigSnapshot/PromptRef；只记录 owner/执行裁定结果，不在 AP 自选 canonical id | `src/contracts/intake/strategies.py:57-147`; `src/services/config_snapshots.py:57-59`; `src/services/prompt_profiles.py:50`; `NH-RA04-B04` | `✅/♻️` | `S` | `T-R-NH-08` |
| `NH1-09` | 形成 foundation evidence package：spike 代码/测试与生产改动分账；列出可以复用、必须重 substrate、净新、被证伪的方案；给 NH2–NH6 输出版本化接口 | 九面 §6/§7/§9；`G-NH-RA-04..07` | `🆕` | `M` | all `T-R` |

**NH1 exit / hard gate**：

- `NH-A-01-04` selected-output spike、`NH-A-02-02/03/06/08` S05 状态/封闭/崩溃/command 全绿；这里只证明 substrate，不证明四通道。
- API fan-in recovery 不再因 sqlite3-on-Turso 红；search fixture 不再因 namespace 422；source runner 在超时前必须到真实 terminal（可为诚实未部署的 typed failure，但不得停 `running`）。
- runtime 三 smoke 有真实二进制/进程证据；它们不能被列入 `T-O-381` live matrix。
- NH1 evidence package 验证 planning-final chosen branch；NH1 未通过前，NH2–NH6 均不得进入 production implementation。
- 任一 spike 证明 owner 已裁形态不可行时，停止 DAG，回到 `pre-charter-qna` reopen 对应 gate 并修订 planning-final；不得在实现中静默换选项。

### 7.2 `AP-NH2` · Workflow graph algebra、kind family 与 resolver/compat

**职责**：让 S03 七表能够声明“同一 kind revision 内多 acquire/decode/clean candidate，经闭集事实选择并汇到一份下游输入”，同时完成 source-kind-only 选图与旧 pin 共存。NH2 不拥有 representation 内容、actual S05 字段或 runtime adapter。

| 编号 | 工作项（详细设计） | reference 轴 + HEAD 锚 + 避坑 | 复用 | 规模 | 依赖 / 真相 |
|---|---|---|---|---|---|
| `NH2-01` | 按 `G-NH-02` 的 owner 裁定实现 selected-output graph primitive/control；输入、双命中、零命中、失败传播、output proof 均登记且版本化 | `src/contracts/workflow/models.py:476-525`; `src/persistence/migrations/001_initial.sql:1770-1771`; `NH-RA01-B01`; ⛔不得复制整条 tail 伪装 merge | `♻️/🆕` | `L` | NH1-04; `T-O-384` |
| `NH2-02` | 扩登记 predicate 闭集以消费 NH1/NH3 typed fact；继续 `eq` only、缺键 false、未知 predicate registration fail | `src/contracts/workflow/models.py:249-256`; `src/runtime/workflow/runtime_materialize.py:101-117`; `NH-C-03/09` | `♻️` | `M` | `G-NH-03/13`; `T-R-NH-05` |
| `NH2-03` | 建三张 single-root kind definition（inline/local/http）和独立 scatter root/child；每张图只含该 kind 合法边，publication tail 只保留一份定义来源 | `lsrag_definition.py:881-926,929-1069`; `NH-C-04/06/07` | `♻️` | `XL` | NH1 matrix; `T-O-387` |
| `NH2-04` | 把同 kind 的 static/browser/print、PDF/doc/image 等 acquire/decode/clean 候选以不同 step/route 预声明；每 acquire step 至多成功一次，所有 path 无环 | `src/contracts/workflow/models.py:389-432`; `NH-RA01-B04/B07`; `NH-C-02` | `♻️/🆕` | `L` | NH1 fact schema; `T-O-384/388` |
| `NH2-05` | resolver 改为 public 只消费 `source_kind`；`acquisition_mode/media_type` 仅成为图内起点/fact，不再派生 workflow key；caller 仍禁 workflow_key | `src/services/workflow_registry.py:78-104`; `src/services/config_snapshots.py:492-516`; `NH-RA01-B03/B05` | `♻️` | `M` | `T-O-379/387` |
| `NH2-06` | 停用“三槽替换复制整图”作为 active kind factory；process_key/strategy identity 从 registry/matrix 显式绑定，禁止 handler 表外 `dispatch_clean` 选择未声明工人 | `lsrag_definition.py:913-925`; `clean_preflight.py:46-121`; `NH-RA02-B06` | `♻️` | `L` | `T-O-382/384`; NH1-07 |
| `NH2-07` | 实施 old-key/new-kind coexistence：旧 key/revision保持 enabled-unselected 或 owner 裁定形态；runtime 仍按 compiled digest 找 plan，未知 digest 不插 Process | `runtime_core.py:591-625`; `lsrag_definition.py:1073-1080`; `NH-RA01-B08`; `NH-A-09-16/17` | `✅/♻️` | `L` | `G-NH-09`; `M-NH-04` |
| `NH2-08` | 架构守卫：公共模型无 workflow_key；源码无 `action_branch`；新自由表达式/JS/SQL/JSONata/FEEL registration 失败 | `src/contracts/api/models.py:107-178`; `src/contracts/workflow/models.py:245-278`; `NH-A-01-07/08` | `✅` | `S` | `T-O-377/379` |

**NH2 exit / hard gate**：`NH-A-01-01..08` 全绿；新 kind selector 可达所有声明边但不能执行未部署 capability；旧 pinned Execution 在新 active definitions 存在时仍跑旧 process sequence；不得以 13 张复制图或 6 张 `resolve_by_key` 成功代替 kind family。

### 7.3 `AP-NH3` · RepresentationFact/history、有限 reacquire 与 two-stage actual S05

**职责**：把字节/媒体/文本层/opaque/print 等观察变成 durable、可守卫、可重放事实，并在 selected route 后一次封闭 actual S05；NH3 不选择具体 parser/browser/model。

| 编号 | 工作项（详细设计） | reference 轴 + HEAD 锚 + 避坑 | 复用 | 规模 | 依赖 / 真相 |
|---|---|---|---|---|---|
| `NH3-01` | 实施 owner 裁定的 RepresentationFact authority：verified media、representation kind、text-layer observation、raw digest、observer/profile identity、budget、step identity；schema 严格版本化 | `acquisition_ingest.py:579-676`; `NH-N-03-01`; `NH-C-20/26/27` | `♻️/🆕` | `L` | NH1-04; `G-NH-03` |
| `NH3-02` | 建 AcquireDecodeHistory：按实际成功 step append，不覆盖；每步至多一条成功；计算有序 path digest，并能由 guard/recovery 重读 | `acquisition_ingest.py:89,660`; `NH-RA03-B03`; `NH-N-03-02` | `🆕` | `L` | NH2 selected routes; `M-NH-02` |
| `NH3-03` | 加固 sniff/verify：保留 PDF/image mismatch fail-closed，补 ZIP/OPC/opaque；非 PDF/image binary 不再强制 UTF-8；声明 media 与 verified media 分账 | `src/runtime/intake/types.py:174-220`; `src/runtime/intake/acquisition_ingest.py:553-564`; `NH-RA03-B05/B11` | `♻️` | `M` | `T-R-NH-06` |
| `NH3-04` | 将 literal PDF extractor 降级/移除为 text-layer authority；decode 对“无层/不可观察/加密”产 typed observation，不再抛 OCR capability code | `src/runtime/intake/types.py:144-171`; `NH-RA03-B01/B06`; `NH-C-21/23` | `♻️` | `M` | NH6 提供真实 parser；`T-O-378/388` |
| `NH3-05` | 定义 print acquire result：只有实际产 `%PDF-` bytes 且 evidence 带真实 browser/profile identity 才可写 `print_pdf`；clean 不得猜 representation | `acquisition_ingest.py:533-536`; `clean_preflight.py:46-63`; `NH-C-22` | `🆕` | `M` | `G-NH-15`; NH6 supply |
| `NH3-06` | 执行有限 forward reacquire：只沿 NH2 已声明边；append history；无边、环、第二次同 step、try-all 均 fail-loud | `NH-C-24/25`; `NH-A-03-06`; `src/contracts/workflow/models.py:389-432` | `♻️/🆕` | `L` | NH2-04; `G-NH-13` |
| `NH3-07` | 实施 policy/actual S05 分账与合法 unsealed 状态；旧伪值不得自动升格为 actual；提供明确 legacy observation/migration 语义 | `task_create.py:179-180`; DDL `:245-246`; `NH-C-10..12`; `M-NH-01` | `🆕` | `L` | `G-NH-01`; truth erratum |
| `NH3-08` | 在 owner 裁定的线性化点一次 seal actual digest：覆盖 selected route、完整 acquire/decode path、strategy/process/contract、适用 preflight/prompt ref；第二次写 conflict | `runtime_outcome.py:88-137`; `NH-N-02-02`; `NH-A-02-03/04` | `♻️/🆕` | `L` | `G-NH-11`; NH3-02/06 |
| `NH3-09` | 传播与消费：ProcessCommand、CandidateSet、Snapshot、Gate、scatter child、publication traceback 只读封闭 actual；未封闭不得 clean/acceptance-complete | `runtime_core.py:888-917`; `acceptance_snapshot.py:137-157`; `clean_preflight.py:373-399`; `NH-RA02-B03/B05` | `♻️` | `L` | NH3-07/08 |
| `NH3-10` | 实施三窗 replay：seal 前 crash、seal 后 Process retry、causal restart；每窗按 owner 裁定继承/清空法，禁止 resolve active worker 或覆盖 actual | `task_commands.py:293-311`; `NH-A-02-05/06/11`; `NH-C-13/17` | `♻️/🆕` | `L` | `G-NH-12` |

**NH3 exit / hard gate**：`NH-A-03-01..08`、`NH-A-02-02..09/11` 适用项全绿；两条实际 acquire path 得不同 actual digest、同 path 重算一致；decode observation 与 runtime capability error 分码；旧 Execution 不因新列/新事实无法读取。真 parser/browser live 仍由 NH6/NH7 证明。

### 7.4 `AP-NH4` · Public upload、bounded CAS 与 object lifecycle

**职责**：建立 `T-O-385` 的受鉴权字节入口与合法“已上传未 ingest”状态；只产 S13 handle/digest/size，不拥有 Source/Item/Revision。

| 编号 | 工作项（详细设计） | reference 轴 + HEAD 锚 + 避坑 | 复用 | 规模 | 依赖 / 真相 |
|---|---|---|---|---|---|
| `NH4-01` | 扩 ObjectStorePort 为有界流/分块写语义：逐块计 size/sha256，超 cap/expected digest mismatch 时无 usable catalog；不靠抬 1MiB JSON body cap | `src/storage/ports.py:10-24`; `src/runtime/config.py:26,58`; `NH-RA06-B05/B09` | `♻️/🆕` | `L` | `T-O-385`; `M-NH-05` |
| `NH4-02` | 实施 authenticated upload service/UoW：CAS bytes + catalog + owner 裁定的 pending/hold 状态满足后才返回 handle；响应不含 path/filename | `src/storage/local_store.py:71-105`; `src/services/object_gc.py:146-161`; `NH-N-06-01/02` | `✅/♻️/🆕` | `L` | `G-NH-16` |
| `NH4-03` | 增 public surface：鉴权/team scope、bounded content、可选 expected digest/declared media；HTTP/multipart/path 字面在 action-plan 服从已裁合同 | `api/public/routes.py:56-452` route=0; `NH-RA06-B01` | `🆕` | `M` | `G-NH-07`; `T-O-376/385` |
| `NH4-04` | replay/conflict：同 team+digest+size 返回同一 usable handle；并发双传不造双 live row；不同 team 隔离；tombstone 后行为 typed | DDL unique `014_*:17-20`; `local_store.py:84-105`; `NH-C-51/53` | `✅/♻️` | `M` | `T-O-383/385` |
| `NH4-05` | upload→local_object ingest handoff：ingest 只接 handle/digest/size，经 `read_verified`；upload UoW 与 Task UoW 分离；成功 upload 后三张 S04 identity 表仍零增量 | `acquisition_ingest.py:413-455`; `NH-C-50/55/58` | `✅/♻️` | `M` | NH3 read contract |
| `NH4-06` | GC lifecycle：hold 内不选、release+grace 后可 quarantine/tombstone；GC 与 ingest/ref 交错时 TX2 recheck/restore；未 catalog staging 可扫描清理 | `src/services/object_gc.py:133-245`; `tests/unit/test_ns6_gc_toctou.py:68-89`; `NH-RA06-B03/B04` | `✅/♻️` | `L` | `G-NH-16`; `T-R-NH-12` |
| `NH4-07` | 按 `G-NH-07` 裁决实现或明确拒绝 raw read；任何允许的 read 必须 auth/team/handle/digest fence，业务 artifact metadata route 不等同 raw bytes | `api/public/routes.py:226-294`; `src/storage/local_store.py:107-122`; `NH-C-59` | `♻️/🆕` | `M` | `G-NH-07` |
| `NH4-08` | 安全边界：filename 不入 CAS path，Content-Type 只是声明，路径穿越/未鉴权读/超 cap/digest mismatch 均负测；不引 presign/R2/object browser | `local_store.py:38-39`; `RA-06-WEB-04`; `T-O-42` | `✅/♻️` | `M` | `T-O-377/385` |

**NH4 exit / hard gate**：`NH-A-06-01..16` 适用项全绿；公共调用真实字节→handle→随后独立 local_object Task，upload 后检索为零、ingest 后才可检索；GC/replay/concurrent upload 有 deterministic disposition；内部 `promote` 或测试预置不得算 public upload。

### 7.5 `AP-NH5` · 五维 semantic authority、S06 overlay 与 retrieval facets

**职责**：建立四 kind 的 S04 语义权威及 system-owned S06/retrieval 投影；不从 clean/g0/model 猜五维，不重开 cuts。

| 编号 | 工作项（详细设计） | reference 轴 + HEAD 锚 + 避坑 | 复用 | 规模 | 依赖 / 真相 |
|---|---|---|---|---|---|
| `NH5-01` | 按 `G-NH-05` 裁决扩 public ingest typed contract/closed derivation/merge 入口；五维+tags schema strict，extra 禁止；unknown 行为由裁决显式表达 | `src/contracts/api/models.py:107-144`; `src/contracts/intake/semantics.py:12-63`; `NH-N-07-01` | `🆕` | `L` | `T-O-389`; `G-NH-05` |
| `NH5-02` | acceptance semantic gate：四 kind 缺任一 required semantic 或仍为 `{source_kind}` stub 时不得 complete/新 Revision/vectorize；registered_api 六元组保持回归 | `acceptance_snapshot.py:589-615`; `NH-RA07-B01/B02/B06` | `♻️` | `M` | `T-R-NH-13` |
| `NH5-03` | S04 写入原子性：六键 definition/value/digest 同 UoW；`filter_metadata` blob 与单键行同源；metadata update 禁只改单键 | `acceptance_lifecycle.py:378-380`; `targets.py:203-248`; `NH-RA07-B07` | `♻️` | `L` | `NH-C-62/67` |
| `NH5-04` | 建 system-owned S06 `context_meta` overlay：从该 Revision S04 行覆盖 realm/type/channel/source_name/tags；模型值不获权威；g0 overlay 保持原实现 | `generation_assemble.py:17-62`; `generation_construct.py:330-343`; `NH-N-07-02` | `♻️` | `M` | `T-O-386/389` |
| `NH5-05` | 按 `G-NH-06` 裁决拆业务 semantic channel 与 vector original/summary public semantics；提供兼容/拒绝策略，禁止同名歧义 | `retrieval/models.py:14`; `retrieval_request.py:354-355`; `NH-RA07-B04` | `♻️` | `M` | `G-NH-06`; `M-NH-06/08` |
| `NH5-06` | 把 FilterMeta+tags 投影到 `mkb_vector_record_facets` 或 owner/design 裁定的 typed query path；definition digest 与 serving Revision S04 行一致 | `vector_publish_commit.py:496-518`; `retrieval_rank.py:80-122`; `NH-RA07-B05` | `♻️` | `L` | `NH-C-65/68` |
| `NH5-07` | 扩 public retrieval filter registry/SQL candidate fence：闭集 eq；未知 key 422；facet 在候选 SQL 生效，不在 top-k 后过滤 | `retrieval/models.py:14-34`; `retrieval_request.py:324-361`; `RA-07-WEB-*` | `✅/♻️` | `M` | `T-O-389` |
| `NH5-08` | metadata semantic refresh：新 Revision 继承 exact clean artifact；S06/facet 随 serving revision 切换；是否执行 clean Process 交 NH8/`G-NH-19`，本项不冒充已 skip | `acceptance_lifecycle.py:213-409`; `NH-C-66` | `✅/♻️` | `M` | `G-NH-19`; NH8 |

**NH5 exit / hard gate**：`NH-A-07-01..10` 全绿；四 kind 的 representative acceptance 均有非 stub 六键；S06 context 与 S04 逐字对账、g0 body digest 不变；public filter 可命中/排除并保持未知键 fail-closed。没有 runtime 的路径可用 integration fixture验证语义，但不得标 live-to-vector。

### 7.6 `AP-NH6` · Local runtime supply、readiness、budget 与安全隔离

**职责**：按 owner 裁定的边界交付真实 PDF parser、browser render/print、OCR/Vision/document-understanding binary transport；runtime 只供能力，不发明 kind/strategy/representation。

| 编号 | 工作项（详细设计） | reference 轴 + HEAD 锚 + 避坑 | 复用 | 规模 | 依赖 / 真相 |
|---|---|---|---|---|---|
| `NH6-01` | 定义 capability supply identity/catalog：PDF parse、browser render、browser print、OCR、vision/document generate 分账；每项绑定版本、binary/model、limits、readiness | `src/runtime/workflow/dispatch.py:20-43`; `NH-C-40/42/44` | `♻️/🆕` | `M` | `G-NH-04/10/15` |
| `NH6-02` | 实施真实 PDF text-layer supply：压缩流/CID/ToUnicode fixture 可抽文本；无层/加密/损坏产 typed observation/failure；移除 literal regex 的权威地位 | `src/runtime/intake/types.py:100-171`; `NH-A-05-02/03`; `RA-03-WEB-05/06` | `🆕` | `L` | NH3-04; `G-NH-10` |
| `NH6-03` | 实施真实 browser content supply：受 S16 egress/SSRF、redirect、byte/time cap 与 sandbox；输出真实 renderer profile，SPA fixture 得 rendered DOM | `http_acquisition.py:182-208`; `api/app.py:280-288`; `NH-RA05-B12` | `🆕` | `L` | `G-NH-04/10` |
| `NH6-04` | 实施 print-to-PDF supply：按 owner 裁定与 page-render 的关系，输出 `%PDF-` bytes、profile、budget、page/timeout evidence；不把 screenshot/HTML 改名 | `NH-N-05-04`; `NH-A-05-05`; `RA-03-WEB-03/04` | `🆕` | `L` | `G-NH-15`; NH3-05 |
| `NH6-05` | 实施 binary multimodal request/adapter：prompt identity + media_type + bytes-or-S13 handle + digest；`payload_extra` 不运 content；CLI 继续诚实拒 binary或依裁决新增明确合同 | `inference/models.py:63-108`; `claude_cli.py:505-508`; `NH-N-05-01` | `♻️/🆕` | `XL` | `G-NH-04`; `T-R-NH-09` |
| `NH6-06` | 交付 OCR/Vision/document-understanding binding：模型/engine identity、trained data/weights、空输出、bad media、timeout、resource exceeded 均 typed；禁止云 OCR/浮动 latest | `clean_preflight.py:76`; `NH-RA05-B04/B09`; `T-O-42` | `🆕` | `L` | `G-NH-04/10` |
| `NH6-07` | 并发/预算：把新 capability 纳入 owner 裁定的 pool/gate 形态；满载返回 BACKPRESSURE 且零下游调用；browser/parser 与 inference 分别计量 | `api/app.py:244-266`; `facade.py:102-132`; `NH-RA05-B08` | `♻️` | `M` | `G-NH-04` |
| `NH6-08` | readiness/health：逐 capability 实弹 probe 和负样本；缺 binary/model/data/sandbox/license 时 component false；`/v1/models`/import/which 不足 | `src/runtime/health.py:16-25`; `src/llm_adapters/local_vllm.py:276-295`; `NH-N-05-02` | `♻️/🆕` | `M` | `T-R-NH-10` |
| `NH6-09` | supply chain：dependency lock、binary inventory、license/SBOM、CVE baseline、升级/rollback、隔离 kill/restart；PDF 与 browser 威胁模型分别记录 | `pyproject.toml:11-21`; `NH-C-45/48`; `NH-A-05-10` | `🆕` | `L` | `G-NH-10` |
| `NH6-10` | 默认组合根注入已交付 supply，配置缺失时 fail-loud；正例 default-root 不允许测试后赋 `_browser_fetcher/_clean_llm` | `api/app.py:330-345`; `test_source_capability_paths.py:99-101`; `NH-A-05-01` | `♻️` | `M` | NH6-02..09 |

**NH6 exit / hard gate**：`NH-A-05-01..10` 全绿；真实 parser/browser/print/binary adapter 在 default app 可探测并受预算；恶意/加密 PDF 与 untrusted URL 不打崩 API 进程；license/SBOM 无缺口。此时只证明供给 live，完整知识路径仍由 NH7 证明。

### 7.7 `AP-NH7` · 10+3 capability activation vertical slices

**职责**：用 NH2–NH6 substrate 激活合法矩阵，每个 lane 从真实输入/冻结 records 走到 admitted clean、S04 semantics、S06/g0、publication proof、带 namespace 的 retrieval hit。通道是验收行，不是复制 handler/graph 的施工边界。

| 编号 | 工作项（详细设计） | reference 轴 + HEAD 锚 + 避坑 | 复用 | 规模 | 依赖 / 真相 |
|---|---|---|---|---|---|
| `NH7-01` | 从 `CLEAN_STRATEGY_DEFINITIONS` + API registry 生成合法 activation matrix；校验 strategy≠process≠representation≠adapter；非法组合 409/422 | `strategies.py:15-160`; `intake/__init__.py:20-90`; `RA-04 §2.2/2.3` | `✅/🆕` | `M` | NH1-07; `T-R-NH-07` |
| `NH7-02` | 统一 admitted-clean schema/evidence：非空 text、content digest、strategy/capability/version；仅 LLM 加 PromptRef/hash；API member 加双 digest+六元组 | `intake/web/__init__.py:25-104`; `intake/pdf/__init__.py:12-74`; `intake/doc/__init__.py:11-113`; `src/contracts/intake/semantics.py:37-52` | `✅/♻️` | `M` | `T-O-386`; `NH-N-04-01` |
| `NH7-03` | 完成 promptA owner/执行裁定的 catalog/config 对齐与旧 PromptRef 兼容；drift 必须 `PROMPT_HASH_MISMATCH`，不得 silent fallback | `clean_preflight.py:183-188`; `NH-RA04-B04` | `♻️` | `M` | `M-NH-07` |
| `NH7-04` | deterministic lane：inline/doc deterministic、HTTP static web deterministic；HTTP PDF 仍 PDF-first；空 HTML/空 doc fail，无模型调用 | `intake/__init__.py:68-90`; `test_intake_clean_dispatch.py:164-176` | `✅/♻️` | `M` | NH2/3/5 |
| `NH7-05` | PDF text lane：public upload或HTTP PDF→verified bytes→真 text-layer observation→`pdf.text_layer`→retrieval；无层不得进入该 worker | `strategies.py:79-87`; `NH-A-03-02`; `NH-A-05-02` | `♻️` | `M` | NH3/4/5/6 |
| `NH7-06` | browser lane：HTTP static shell/declared route→真实 browser representation→`web.deterministic`或`web.llm_rewrite`（按已冻图/规则）→retrieval；无暗升 | `strategies.py:47-66`; `NH-A-03-06/07`; `NH-A-05-04` | `♻️` | `L` | `G-NH-13`; NH2/3/5/6 |
| `NH7-07` | print-PDF lane：HTTP→真实 print_pdf evidence/PDF bytes→`web.browser_print_pdf`→同一 PDF clean channel→retrieval；禁止 HTML sanitizer | `strategies.py:67-77`; `clean_preflight.py:46-63`; `NH-C-35/46` | `♻️` | `L` | NH3/5/6 |
| `NH7-08` | multimodal lane：PDF DU/PDF OCR/doc DU/doc OCR/doc vision 各自合法 representation、真实 binary transport与绑定；空输出不换 worker、不出向量 | `strategies.py:88-149`; `NH-A-05-06/07`; `NH-C-33` | `♻️` | `XL` | NH2/3/5/6 |
| `NH7-09` | registered_api preservation lane：3 operation 使用 caller-frozen records、strict map/parser、empty member整批失败、zero collection 服从 owner裁定；child publication 后逐 member search | `intake/api/registry.py:73-148`; `test_registered_api_scatter.py:209-373`; `NH-A-04-04/05` | `✅/♻️` | `L` | `G-NH-08`; NH5 |
| `NH7-10` | 每 lane 写 first-publication proof：S04 six tuple、g0 body=clean、S06 context overlay、pointer/serving、namespace query、适用 facet 命中与排除 | `vector_publish_commit.py:57-191`; `retrieval_rank.py:38-76`; `NH-A-07-07`; `NH-A-08-01/02` | `✅/♻️` | `L` | NH5; `T-R-NH-15/16` |

**NH7 exit / hard gate**：合法 10 strategy + 3 operation 每格至少一正例及规定负例；default-root success 无 monkeypatch、无 503、无空 clean；每个应产知识的格有真实 retrieval hit+traceback+semantic facet；exhausted-zero 按 owner 决定的 terminal 验收且不得伪造“已索引内容”。

### 7.8 `AP-NH8` · 七意图、exact-clean、publication lifecycle 与 compatibility migration

**职责**：让已接通 Item 在 rebuild/metadata/lifecycle/index.rebuild 下保持 exact clean、semantic/pointer 一致及旧 pin 可运行；不把六个事后意图按 kind 复制。

| 编号 | 工作项（详细设计） | reference 轴 + HEAD 锚 + 避坑 | 复用 | 规模 | 依赖 / 真相 |
|---|---|---|---|---|---|
| `NH8-01` | 固化七意图合法输入/状态/终态/非法格表；只有 ingest 读取 SourceDescriptor/kind，其他按 Item或scope；错误码/矩阵形态服从 `G-NH-17` | `src/contracts/api/models.py:278-286`; `src/services/config_snapshots.py:138-144,474-501`; `NH-N-08-02` | `✅/🆕` | `M` | `T-R-NH-21`; `G-NH-17` |
| `NH8-02` | rebuild exact-clean：只绑定 frozen accepted clean artifact/digest，不重读 URL/handle/records；clean Process 行为服从 `G-NH-19`，结果必须 byte/digest exact | `acquisition_intents.py:25-93`; `clean_preflight.py:28-127,706-714`; `NH-RA08-B04` | `♻️` | `L` | `G-NH-19`; `M-NH-09` |
| `NH8-03` | metadata no-change 保持零新 Revision/generation；changed metadata 新 Revision继承 clean、跳 structurize/reuse summaries、重投 S04/S06/facet | `acceptance_lifecycle.py:137-409`; `lsrag_definition.py:290-347` | `✅/♻️` | `L` | NH5-08; `NH-C-66/72` |
| `NH8-04` | deactivate/delete 同 UoW撤 serving/pointer/vector；reactivate 不恢复旧 serving，直到显式 publish/rebuild；所有状态用 retrieval negative proof | `lifecycle_apply.py:34-40,108-134`; `NH-C-73/74` | `✅/♻️` | `M` | `T-O-381` |
| `NH8-05` | index.rebuild 只造新 generation，不造 Revision、不读源/clean、不切 Layer A；stale generation从 search排除 | `index_rebuild_plan.py:23-32`; `NH-A-08-10/13` | `✅` | `M` | `NH-C-78/79` |
| `NH8-06` | registered_api Item 走与 single Item 相同的 rebuild/metadata/deactivate/reactivate/delete/index.rebuild 产品法；不把 child graph当第二 lifecycle kernel | `builtin_scatter.py:416-441`; `NH-RA08-B07` | `♻️` | `L` | `NH-C-75`; NH7-09 |
| `NH8-07` | 完成 old 13 keys/compat revisions/new kind graphs 的 coexist/retirement：旧 Execution 按旧 compiled digest终结；新 Task只走kind resolver；退役有观测与回滚点 | `runtime_core.py:591-625`; `builtin_lsrag.py:40-44`; `NH-A-09-16/17` | `✅/♻️` | `L` | `G-NH-09`; `M-NH-04` |
| `NH8-08` | actual S05 与 lifecycle/rebuild 对账：同 Execution retry不换，new generation/rebuild按 `G-NH-12/19` 的不同语义，不把两类 restart 合并 | `task_commands.py:293-311`; `NH-C-17`; `NH-RA08-B04` | `♻️` | `M` | `G-NH-12/19` |

**NH8 exit / hard gate**：`NH-A-08-03..13` 与 `NH-A-09-16/17` 全绿；七意图每个合法格有产品终态、每个承重非法格 fail-loud；rebuild/metadata clean digest exact；deactivate/reactivate/delete/search 关系闭合；旧 pin 与新 kind graph 同时可运行。

### 7.9 `AP-NH9` · Closed-set assurance、race/crash proof 与 closure evidence

**职责**：汇总而不替代 NH1–NH8 的 AP 自验；运行完整合法矩阵、跨面 crash/replay/race/security/compat 证明，产出可供 planning-final/closure 使用的不可变 evidence package。实验只可建空日期骨架。

| 编号 | 工作项（详细设计） | reference 轴 + HEAD 锚 + 避坑 | 复用 | 规模 | 依赖 / 真相 |
|---|---|---|---|---|---|
| `NH9-01` | 从 registry/matrix 自动生成 closed-set test manifest；每格记录输入fixture、selected path/strategy、actual S05、semantic tuple、proof/query、负例、test layer | `strategies.py:15-151`; `NH-N-09-01`; §9.3 | `🆕` | `L` | NH1-07; `T-R-NH-19` |
| `NH9-02` | Task/intake replay/conflict/concurrent create：同 fingerprint原视图，异 fingerprint 409，双飞无双根/双 object ref | `task_create.py:67-140`; `NH-A-09-01..03` | `✅/♻️` | `M` | `T-O-383` |
| `NH9-03` | fail-loud matrix：空 HTML/PDF/OCR/model输出、bad media、bad API member、unknown strategy/predicate/filter、missing supply；失败后检索零命中 | `clean_preflight.py:544-547`; `NH-A-09-04/05/12/19` | `✅/♻️` | `L` | `T-O-378/383` |
| `NH9-04` | crash-window injection：selection前、Outcome/seal线性化点、Process outcome、publication pointer/serving、outbox redelivery；每窗断言 effect-once而非宣称 delivery exactly-once | `runtime_outcome.py:46-182`; `runtime_outbox.py:131-139`; `NH-N-09-02` | `♻️/🆕` | `XL` | `G-NH-11`; `T-R-NH-18` |
| `NH9-05` | upload race：并发同字节、upload→ingest与GC交错、hold release、quarantine新ref restore、tombstone后重传；永不造假 Item | `src/services/object_gc.py:189-240`; `NH-A-09-14/15` | `✅/♻️` | `L` | NH4 |
| `NH9-06` | scatter/fan-in：zero、bad member、one child fail、siblings complete、crash-after-child；parent/product retrieval 结果服从 owner terminal且不被 sibling `publication_ready` 顶替 | `runtime_scatter.py:320-474`; `NH-A-09-06..08` | `✅/♻️` | `L` | `G-NH-08` |
| `NH9-07` | old pin×new kind×actual S05 compat 联合套件；unknown compiled digest零 Process；旧行伪 s05不能通过新 actual 断言 | `runtime_core.py:591-625`; `NH-A-09-10/11/16/17` | `✅/♻️` | `L` | NH3/NH8 |
| `NH9-08` | retrieval-facet mega：每个应产知识格带合法 namespace，命中 admitted clean/summary约定、traceback、proof、serving、semantic facet；stale/deactivated/deleted均排除 | `retrieval_rank.py:38-76,339-433`; `NH-A-09-18` | `✅/♻️` | `XL` | NH5/NH7/NH8 |
| `NH9-09` | security/readiness closure：缺 binary/model/data、恶意 PDF、untrusted URL、budget/backpressure、license/SBOM/CVE；正/负 readiness 与 runtime outcome 一致 | `NH-A-05-03/08/09/10`; `NH-C-44/45/48` | `♻️` | `L` | NH6 |
| `NH9-10` | 生成 immutable closure evidence：测试命令/commit/fixture digests/migration revisions/known waivers；任何 waiver 标 affected T-O，不能把 S1 隐成后续优化 | `assessment-index G-NH-RA-06`; `NH-C-88` | `🆕` | `M` | all APs |
| `NH9-11` | 可选 `.experiment` 骨架只登记 matrix/run schema/preflight，日期与分数保持空；不得被 closure report计作能力证据 | `T-O-380`; `NH-RA09-B16` | `♻️` | `S` | owner另令 |

**NH9 exit / campaign closure gate**：§9 的所有 hard `FG-NH-*` 通过；四层适用测试不可互换；`T-O-381` 合法 live matrix 全绿；无未解释 S1 blocker；任何 owner-approved waiver 明确缩小 campaign truth，而不是改测试期望。实验发车不在 exit 内。

---

## 8. Owner decision gates —— 精炼 OPEN（仅问题台账）`[核心]`

> 本节不提供候选答案、倾向或赢家。owner 决策必须另落 `pre-charter-qna.md` / append-only Truth；本文只记录“必须回答什么、为什么改变工程、最迟何时回答”。`G-NH-14` 故意空号：promptA 三 catalog 对齐是已知执行项，不在此伪造 owner 产品 gate。

| gate-ID | 待 owner 裁决的问题 | 为什么必须由 owner 裁 | 阻塞 / 改变的制品 | 最迟裁决点 | 状态 |
|---|---|---|---|---|---|
| `G-NH-01` | policy binding 与 actual S05 binding 的长期 schema、字段命名及合法 unsealed 状态应如何表达？旧伪值如何被解释？ | 改变 frozen glossary/S05/D04 语义、DDL 与读写兼容 | `M-NH-01`; NH1-05; NH3-07..10 | pre-charter / planning-final 前 | `OPEN` |
| `G-NH-02` | selected-output 在 Workflow 七表中以什么声明式、版本化形态汇合，并如何定义零命中/双命中？ | 改变 graph algebra、DDL/runtime 与 migration；不是局部 step 命名 | `M-NH-03`; NH1-04; NH2-01/03 | pre-charter / planning-final 前 | `OPEN` |
| `G-NH-03` | representation route fact 与 acquire/decode history 的 durable authority 放在哪里，谁拥有 schema 与 replay 读法？ | 决定 guard、digest、recovery 和查询一致性 | `M-NH-02`; NH2-02; NH3-01/02 | pre-charter / planning-final 前 | `OPEN` |
| `G-NH-04` | PDF/browser/OCR/Vision/document-understanding 的 runtime 与现有 inference boundary 如何分工，binary request 由哪一契约承载？ | 改变 S11/ports/pools/deploy/readiness；现协议已证不足 | NH1-06; NH6-01/05..08 | pre-charter / planning-final 前 | `OPEN` |
| `G-NH-05` | 非 API 三 kind 的五维权威从何取得、冲突如何合并、何时允许或禁止显式 `unknown`？ | 改变 public ingest contract、acceptance eligibility 与 facet 枚举 | NH5-01..03; NH7/8 semantic DoD | pre-charter / planning-final 前；不得晚于 NH5 freeze | `OPEN` |
| `G-NH-06` | 业务 FilterMeta channel 与 vector original/summary channel 在 public contract、内部列和兼容层中如何无歧义命名？ | 改变 retrieval API、DDL/投影、旧客户端兼容 | `M-NH-06/08`; NH5-05..07 | pre-charter / planning-final 前；不得晚于 NH5 freeze | `OPEN` |
| `G-NH-07` | public object surface 的边界到哪里：上传、状态确认、原始字节读取与业务 artifact read 各自是否公开？ | 改变安全/鉴权/DoS/GC/API scope；QNA 只冻 upload 必须存在 | NH4-03/07/08 | pre-charter / planning-final 前；不得晚于 NH4 freeze | `OPEN` |
| `G-NH-08` | 有 exhaustion proof 的 registered API 零集合应处于什么 Task/result/publication/retrieval 终态？ | 改变 Task 指标、fan-in、调用方语义和 DoD，不能由测试作者决定 | NH1-07; NH7-09; NH9-06 | pre-charter / planning-final 前；不得晚于 NH7 freeze | `OPEN` |
| `G-NH-09` | selected-output/kind-family 所需 Workflow substrate 属于 new-harvest 内部 AP，还是一个必须先完成的外部前置？若外置，交接/版本门是什么？ | 改变 campaign scope、关键路径和 AP ownership | NH1/NH2；planning-final DAG | pre-charter / planning-final 前 | `OPEN` |
| `G-NH-10` | 对 PDF parser、browser、OCR/Vision 等每项 untrusted/native dependency，允许的隔离、部署、license 与风险接受线是什么？ | 安全/法务/运维不可由库作者或测试自行决定 | NH1-06; NH6-02..09 | pre-charter 先冻风险接受线；具体依赖入 lock 前复核符合性 | `OPEN` |
| `G-NH-11` | actual S05 seal 与 selected-route Outcome 的线性化关系和事务边界是什么？若存在两次提交，崩溃窗如何定义？ | 决定“写入前可重选、写入后不可重选”的可证明时刻 | NH1-05; NH3-08/10; W-NH-SEL/SEAL | pre-charter / planning-final 前 | `OPEN` |
| `G-NH-12` | Task causal restart 对已封闭 actual S05、已接受 clean 与新 generation 分别继承什么、清空什么？不同 intent 是否有不同法？ | retry、rebuild、升级三者若混同会热切或重 clean | NH3-10; NH8-02/08; compat tests | pre-charter / planning-final 前；不得晚于 NH3 freeze | `OPEN` |
| `G-NH-13` | HTML 空壳/主文缺失等信号是否属于可供 eq guard 使用的 representation fact；其 observer 与版本权威是什么？ | 决定 static→browser 是否能声明式前进，且不能由 cleaner 暗升 | NH2-02/04; NH3-01/06; NH7-06 | pre-charter / planning-final 前 | `OPEN` |
| `G-NH-15` | page render 与 print-to-PDF 的供给、binary/profile、sandbox 与预算关系如何划分？ | 决定 capability identity、部署数量、证据与资源隔离 | NH1-06; NH3-05; NH6-03/04 | pre-charter / planning-final 前 | `OPEN` |
| `G-NH-16` | upload 成功事务必须写入哪些 catalog/reference/hold 状态，何时释放，如何与 GC 区分合法 pending 和 orphan？ | 决定数据可达性、泄漏/误删风险与 `T-O-385` 成功定义 | `M-NH-05`; NH4-02/04..06 | pre-charter / planning-final 前；不得晚于 NH4 freeze | `OPEN` |
| `G-NH-17` | 七意图非法格需要怎样的稳定 public disposition/error-code 合同，以及该合同是否进入 charter？ | 改变 public compatibility、测试矩阵与调用方处理 | NH1-07; NH8-01; §9.4 | pre-charter / planning-final 前；不得晚于 NH8 freeze | `OPEN` |
| `G-NH-18` | unit/integration/default-root/retrieval-mega 四层不可互换的 completeness 义务是否写入 charter，waiver 由谁审批和记录？ | 决定 NH9 证据是否有治理约束，防止后续以较低层替代 | 全 AP exit；§9 | pre-charter / planning-final 前 | `OPEN` |
| `G-NH-19` | rebuild 与 changed-metadata 是否可以再次执行任何 clean Process；若可以，允许的 byte/digest 差异是什么？ | 决定 exact-clean、不热切 strategy、API Item 与旧 Revision 一致性 | NH5-08; NH8-02/03/08 | pre-charter / planning-final 前；不得晚于 NH8 freeze | `OPEN` |

### 8.1 非 owner-gate 的执行延期项（不得挤占 gate 号）

- promptA 三 catalog id/正文/hash 的具体对齐与 data migration；由 `M-NH-07` 在 owner 已冻的 identity 规则下执行。
- 具体 `step_key`、predicate 字面、HTTP path/multipart、S13 purpose 字符串、测试文件名、物理 migration 编号。
- charset/canonicalizer 是否升新 contract version；没有新证据/Truth 时保持 deferred，禁止暗改。
- PDF 页拼接、OCR page ordering、browser print 参数等算法细节；必须服从 admitted-clean 与 digest 合同，但不自动升成 owner 产品 gate。
- `.experiment` 发车日；由 `T-O-380` 继续保持 OPEN，不列为 NH completion gate。

---

## 9. 测试计划、DoD 与防假绿 gate `[核心]`

### 9.1 四层测试法（层级不可互换）

| 层 | 证明对象 | 允许的替身 | 不证明什么 |
|---|---|---|---|
| `L1 unit/contract` | schema、registry、digest、predicate、pure transform、error code | deterministic fixture / fake clock / in-memory pure port | 不证明 DB UoW、默认组合根、真实 binary/runtime、检索 |
| `L2 integration/UoW` | DDL/migration、CAS、route materialization、history/seal、catalog/GC、S04/facet | 本地真实 PersistencePort/ObjectStore；受控 fixture bytes/records | 不证明默认 app 已注入生产 supply，不证明 public retrieval |
| `L3 default-root e2e` | `create_app()` 默认组合、auth/public route、真实本地 binary/model/process、Task terminal | caller-frozen API records；本地 fixture server/file | 成功路径禁止 monkeypatch/fake adapter；单独仍不等于可检索 |
| `L4 retrieval-facet mega` | namespace+proof+pointer+serving+query+traceback+facet 的产品终态 | 已冻输入 fixture；不得替换 retrieval service | 不由 Task success、publication flag、直接 SQL row 顶替 |

**横切标签**：`F=fault injection`、`R=replay/race`、`C=compat`、`S=security`。这些标签必须附着于 L1–L4 之一，不是可替代的“第五层”。

### 9.2 AP 级测试包与收口责任

| AP | 必跑核心 Test-ID / 测试包 | 收口证明 | 禁止顶替 |
|---|---|---|---|
| NH1 | `NH-A-01-04`; `NH-A-02-02/03/06/08`; current 33 clean tests；fan-in recovery；namespace search contract | graph/S05 最小可行，test harness 可信 | smoke ≠ live；修 test expectation ≠ 修产品 |
| NH2 | `NH-A-01-01..09`; `NH-A-09-16/17` 的 graph 部分 | source-kind-only、merge、guard、old pin | 6 unselectable 图、复制 tail、`resolve_by_key` |
| NH3 | `NH-A-02-01..11`; `NH-A-03-01..10` 的 contract/integration 部分 | durable fact/history、reacquire、actual seal/replay | 单槽 evidence、64-hex domain digest、OCR 盗码 |
| NH4 | `NH-A-06-01..16`; `NH-A-09-14/15` | public upload→handle≠Item、replay/GC/race | internal promote、Task inline staging、presign |
| NH5 | `NH-A-07-01..10` | non-API six tuple、S06 overlay、facet/filter | API-only fixture、source_kind stub、模型 context |
| NH6 | `NH-A-05-01..10` | real supply/readiness/security/license | Protocol stub、monkeypatch、import/which/models-list |
| NH7 | `NH-A-04-01..12`; `NH-A-05-11`; `NH-A-07-07`; `NH-A-08-01/02` | 合法 10+3 vertical live-to-retrieval | 33 unit、Task success、publication_ready、503 |
| NH8 | `NH-A-08-03..13`; `NH-A-09-16/17` | 七意图、exact-clean、stale exclusion、compat | 28 格笛卡尔积、只查 lifecycle DB 列 |
| NH9 | `NH-A-09-01..20` + 全量合法矩阵 | replay/race/crash/security/mega 总闭合 | `.experiment`、waiver 隐藏 S1、较低测试层 |

### 9.3 10 strategy + 3 operation 合法 live matrix（初步测试设计）

> 最终 manifest 由 registry 生成；下表是必须存在的承重格，不授权非法笛卡尔积。每一成功格除注明 zero 外都要求：nonempty admitted clean → actual S05 → S04 six tuple → g0 exact body → publication proof/pointer → namespace search hit → applicable facet。

| 格 | 合法来源 / representation | 正例 fixture 与期待 | 必测反例 |
|---|---|---|---|
| `web.deterministic/static` | `http_resource` + transferred HTML | 结构 sanitizer 后非空正文可检索 | 空壳且无已声明 forward edge；HTTP PDF 不得进 web sanitizer |
| `web.deterministic/rendered` | `http_resource` + rendered DOM | 真实 SPA renderer profile，非空正文可检索 | 缺 browser supply；static fallback 冒充 rendered |
| `web.llm_rewrite/static-or-rendered` | HTTP HTML + 已冻 PromptRef | sanitizer→LLM，prompt/evidence 完整 | prompt hash drift；空 rewrite；模型 unavailable |
| `web.browser_print_pdf` | HTTP + honest print_pdf/PDF bytes | print acquire→PDF clean→可检索 | HTML/screenshot 改名；无 `%PDF-`；clean 猜 representation |
| `pdf.text_layer` | local/http PDF + `text_layer=present` | 压缩/CID/ToUnicode fixture 抽取非空 | scan/no-layer；literal `Tj` 假阳性；encrypted corrupt |
| `pdf.document_understanding` | local/http PDF bytes | binary adapter→非空 clean | text-only CLI；缺 blob；空模型输出 |
| `pdf.ocr` | PDF bytes + no text layer + declared route | OCR→非空、有 engine/model identity | decode 先抛 OCR-unavailable；空白页当成功；绑定后换 DU |
| `doc.deterministic` | inline/local text-like non-image | canonical deterministic clean 可检索 | image/docx binary 强送 UTF-8；空正文 |
| `doc.document_understanding` | local opaque/OPC bytes | binary document adapter→非空 | OPC 误 sniff text/plain；text-only adapter |
| `doc.ocr` | local image evidence | OCR→非空，media/engine evidence | image 走 deterministic；空 OCR；未部署 503 当 DoD |
| `doc.vision` | local image evidence | vision adapter→非空、PromptRef 完整 | CLI fallback；unknown media；空/幻觉 context 变权威 |
| API `chinatax.get_article.v1` | registered_api frozen records | strict map、双 digest、六元组、child search hit | 缺键/empty member/silent skip |
| API `domain.get_registration.v1` | registered_api frozen records | 同上 | schema coercion/phantom member/重复 identity |
| API `realestate.get_listing.v1` | registered_api frozen records | 同上 | missing listing id skip；隐式 unknown；empty_response success |
| API exhausted-zero | `records=[]` + valid exhaustion proof | terminal、counts、vector/search 按 `G-NH-08` 裁决 | 无 proof 的 `[]`；把 zero 写作“已有可检索内容” |

### 9.4 七意图 applicability / 产品终态测试

| intent | 合法输入 | 必证终态 | 关键非法/负例 |
|---|---|---|---|
| `intake.ingest` | 四 kind descriptor | 新 Item/Revision、semantics、publication、query（zero 除外） | 无 source、第五 kind、caller workflow_key、lifecycle payload |
| `intake.rebuild` | existing Item + frozen clean | 不读外源；clean exact；new generation/query | deleted/no clean artifact；带 source；热切 active strategy |
| `intake.update_metadata` | Item + registered semantics | no-change 零 Revision；changed 新 Revision且 clean exact、facet切代 | unknown key、只改 blob/单键、reclean 漂字节 |
| `intake.deactivate` | active Item | serving/pointer/vector withdrawn；search empty | 只改 lifecycle 列；旧 generation 仍命中 |
| `intake.reactivate` | deactivated Item | lifecycle active但 serving仍空；search empty直到 republish | 直接恢复旧 serving/generation |
| `intake.delete` | active/deactivated Item | tombstone、serving撤、search empty、rebuild conflict | 二次 delete 偷成功；可恢复旧 vector |
| `index.rebuild` | active team/item scope | 新 index generation、同正文 query、不造 Revision | inactive item、重 acquire/clean、切 Layer-A |

### 9.5 Crash / replay / race window 目录

| Window-ID | 注入点 | 必须证明的结果 | 主要 AP/Test-ID |
|---|---|---|---|
| `W-NH-CREATE` | fingerprint 第一次检查与 INSERT/第二次检查之间 | 同指纹 replay原视图；异指纹409；无双 Execution/object ref | NH1/NH9 · `NH-A-09-01..03` |
| `W-NH-SEL` | representation 已写、selected route 未 durable | 恢复可在已声明边重算；仍 unsealed；零向量 | NH3/NH9 · `NH-A-02-06`; `09-10` |
| `W-NH-SEAL` | selected Outcome 与 actual seal 边界 | 严格服从 `G-NH-11` 的线性化法；不得出现 Outcome 已选但 worker 可热切的无名态 | NH1/NH3/NH9 |
| `W-NH-PROCESS` | Process handler 成功、Outcome CAS 前后 | redelivery effect-once；不同 outcome conflict；actual/process_key 不变 | NH3/NH9 · `NH-A-02-05`; `09-11` |
| `W-NH-PROM-CAT` | upload bytes promote 与 catalog/hold UoW | 失败只留可回收 staging/orphan；不得返回 usable handle或造 Item | NH4/NH9 · `NH-A-06-05..08` |
| `W-NH-GC-INGEST` | GC quarantine 与 ingest/live-ref 交错 | 新 ref restore；hold/grace 生效；无 live bytes 丢失 | NH4/NH9 · `NH-A-06-06/07`; `09-15` |
| `W-NH-FANIN` | children terminal、parent仍 waiting | repair一次完成；required child失败不能被 sibling掩盖 | NH1/NH9 · `NH-A-09-07/08` |
| `W-NH-PUB` | vector rows、proof、pointer、serving CAS之间 | proof不完整不可见；旧 generation不命中；重放不双切 | NH8/NH9 · `NH-A-08-13` |
| `W-NH-OUTBOX` | commit后重复 delivery | consumer幂等、无重复业务副作用；只承诺效果一次 | NH9 · `runtime_outbox.py:131-139` |

### 9.6 防假绿 hard gates

| Gate-ID | 禁止的假绿 | 机器可检的通过条件 | 失败后果 |
|---|---|---|---|
| `FG-NH-01` | default-root success 测试 monkeypatch `_http_fetcher/_browser_fetcher/_clean_llm` | L3 success 路径扫描无赋值/patch；只通过 app 配置注入真实 supply | 该 capability 不得标 live |
| `FG-NH-02` | 503/未部署当 in-scope DoD | 每个 T-O-381 正格 L3+L4 成功；503 只出现在独立负例 | 阻断 NH7/NH9 |
| `FG-NH-03` | Task `succeeded` 当可检索 | L4 必须返回预期 hit/content/proof/traceback | 阻断该格 closure |
| `FG-NH-04` | `publication_ready` 当 query | 每个 member 实际 POST search 且命中 | 阻断 API lane |
| `FG-NH-05` | 无 namespace 的 retrieval 调用 | 所有 e2e body 有合法 namespace且 HTTP 2xx/disposition ok | 阻断全 L4 |
| `FG-NH-06` | 空/空白 clean 或 legacy success flag | admitted clean schema min-length；失败后 vector/search=0 | 阻断 capability |
| `FG-NH-07` | `{source_kind}` stub/空 context 当五维 | S04 六键非 stub；S06 overlay逐字相等；facet可查 | 阻断 acceptance/publication |
| `FG-NH-08` | domain digest/任意64hex 冒充 actual S05 | unsealed可区分；actual digest能因路径/worker变化；command读actual | 阻断 graph/binding closure |
| `FG-NH-09` | 复制 tail/13 profile 算 selected merge/kind family | public resolver只用kind；一图多声明边；单共享 tail；old pin另证 | 阻断 NH2 |
| `FG-NH-10` | internal `promote`/Task inline staging 当 public upload | 经 authenticated public route上传；DB证明零 Item直到独立 ingest | 阻断 NH4/local_object lane |
| `FG-NH-11` | import/which/models-list 当 runtime ready | real positive+negative probe、binary/model/profile identity、budget | 阻断 NH6 |
| `FG-NH-12` | sqlite3 直读 Turso 当 recovery proof | 测试只经 PersistencePort/UoW；无 disk I/O error | 阻断 fan-in/recovery closure |
| `FG-NH-13` | unit/fixture 代替 L3/L4 | manifest记录层级；每个格满足规定最小层 | 阻断对应 AP exit |
| `FG-NH-14` | 只测 API 代表四通道 | inline/local/http/API 各自 representative + 所有合法 strategy 格 | 阻断 campaign closure |
| `FG-NH-15` | 7 intents × 4 kind 造假矩阵 | manifest依据合法 applicability；非法格单独 fail-loud | 阻断 NH8 |
| `FG-NH-16` | `.experiment`、0815-R7、live vendor 当 NH evidence | closure manifest 不计这些结果；发车日字段为空 | 阻断证据包签收 |
| `FG-NH-17` | waiver 通过修改期待值掩盖 S1 | waiver含 owner、Truth影响、到期/reopen，且不得覆盖 foundational T-O | 阻断 planning-final closure |

### 9.7 Campaign DoD（初步）

1. `AP-NH1..NH9` 各自 exit gate 通过；无“NH9 再补”的未验功能。
2. `T-O-381` 合法 10+3 matrix 全部完成规定 L1–L4；非法格有 fail-loud 证明。
3. 三 single kind + scatter root/child 是新 Task 唯一公共选图闭集；old pinned Execution 仍可跑完。
4. 每个已产知识格可从 retrieval hit 回溯 serving Revision、publication proof、S04 semantics、admitted clean、actual S05、acquire/decode history。
5. upload、Task/intake、Process/Outcome、publication、GC 的 replay/race/crash windows 有 deterministic 结果。
6. runtime supply 有真实依赖/identity/readiness/negative sample/license/SBOM，默认进程 success 无 monkeypatch。
7. rebuild/metadata/lifecycle/index.rebuild 对 single/API Item 均满足 exact-clean、pointer/facet/query 合同。
8. `.experiment` 发车不在 DoD；任何尚未发车不降低完成度，任何已发车结果也不能顶替上述证明。

---

## 10. 风险登记 `[核心]`

| 风险 | 触发 | 影响 | 缓解 / hard response |
|---|---|---|---|
| `R-NH-01` owner gate 迟于 schema/code | AP 先选物理形态 | migration返工或事实冲突 | planning-final 前按 §8 最迟点阻断；不得默认答案 |
| `R-NH-02` selected-output 方案破坏七表 | 用 handler if/自由表达式绕过 | replay/注册不可证 | NH1 spike + NH2 registration/negative tests；失败回 owner gate |
| `R-NH-03` old pin 被 kind migration 绞杀 | 删除旧 key/plan或热切 active | in-flight 409/换程序 | `M-NH-04` inventory、compat联合套件、分阶段 retirement |
| `R-NH-04` actual S05 迁移把旧伪值当真 | backfill domain digest | lineage永久错误 | 旧行显式 legacy/unverifiable 语义；禁止自动升格；truth先行 |
| `R-NH-05` representation/history 与 graph 互相返工 | 两 AP各自发明字段 | guard/digest漂移 | NH1 先冻结 versioned interface；NH2只消费，NH3拥有事实 |
| `R-NH-06` runtime 选择被库流行度驱动 | 未审 license/CVE/sandbox | 安全/法务/部署阻断 | `G-NH-10` + NH1 smoke + NH6 SBOM/negative readiness |
| `R-NH-07` 多模态请求偷运 bytes | 使用 `payload_extra`/base64 text | budget/identity/audit失真 | explicit binary contract + digest/handle；架构测试禁 content extra |
| `R-NH-08` upload 刚成功即被 GC或永不回收 | 无 hold/catalog事务 | 数据丢失或磁盘泄漏 | `G-NH-16`、W-PROM-CAT/W-GC-INGEST、scanner/restore测试 |
| `R-NH-09` 五维权威与模型 context 双写 | S06保留模型值 | facet/内容/traceback分叉 | S04 SSOT + system overlay + atomic six-tuple tests |
| `R-NH-10` public `channel` 兼容破坏 | 同名承载两语义 | query歧义/旧客户端错误 | `G-NH-06` 裁决前不冻API；迁移/unknown-key fail-closed |
| `R-NH-11` 已绿 `intake/` 被重写 | 误读“worker未live” | 33 tests回归、重复逻辑 | NH7只补统一contract/activation；pure transforms preservation suite |
| `R-NH-12` publication tail 被复制到各 lane | 按通道独立实现 | proof/serving法分叉 | NH2单共享tail；NH7只接线；架构测试统计重复结构 |
| `R-NH-13` exact-clean 被 deterministic no-op漂移 | rebuild再走inline clean | digest/lineage变更 | `G-NH-19`明确；NH8字节级对照与零外源证据 |
| `R-NH-14` test修复只改期待值 | 把422/running当正常 | 假绿扩大 | NH1要求HTTP/disposition/hit/terminal；FG-NH-05/12/17 |
| `R-NH-15` 资源饥饿/不公平 | browser/OCR抢占embed或无pool | backpressure/延迟失控 | capability gate/metrics/zero-call-on-full tests；部署预算证据 |
| `R-NH-16` 范围滑向live全网连接器 | SPA登录/反爬需求混入 | 无边延期 | O-NH-01硬围栏；只用本地fixture server和caller-frozen records |
| `R-NH-17` AP并行改同一权威 | NH2/NH3/NH5各改route/state | merge冲突与不变量分裂 | §6 ownership/join gate；跨面字段只有一个owner |
| `R-NH-18` NH9成为失败垃圾桶 | 前序AP跳过负测 | 末期系统性返工 | 每AP exit不可waive；NH9只汇总/故障组合，不首测功能 |

---

## 11. 后继解锁 `[核心]`

- **解锁的下游价值**：四类 SourceDescriptor 在统一 kind/actual-binding 产品法下产生可追溯 knowledge；真实 PDF/web/doc 与 caller-frozen API records 具同一 admitted-clean/semantic/publication/retrieval 终态；公共上传与 Item 身份解耦；rebuild/metadata/lifecycle 可复用 exact clean；旧 Execution 不被迁移绞杀。
- **planning-final 前置**：§8 owner decision records 与 S05 append-only truth repair 已落盘；planning-final 冻结 chosen branch、AP-NH1 bounded-spike 范围和“证伪即 stop/reopen”法。NH1 结果在执行后回灌：通过则解锁 NH2–NH9，失败则 reopen gate 与 planning-final。
- **拟派生 action-plan**：`AP-NH1`…`AP-NH9`。每份须继承本文稳定 work-ID、Truth-ID、migration-ID、Test-ID/FG/W-ID，不得重新编号后丢 traceability。
- **实验关系**：NH closure 只解锁 `.experiment` 的技术 readiness；是否创建 run、何时发车、用什么评分由 owner 另令。
- **本链下一跳**：`proposed-planning` → `pre-charter-qna`（裁 §8）→ `planning-final` critique/freeze → 逐 AP action-plan；不得从本文 draft 直接施工。

### 11.1 Action-plan 输出合同

每份 `AP-NHn` 至少包含：

1. 明确 scope/ownership/non-goals 与前驱 Join；
2. 精确 production/test/schema 文件清单和 HEAD `file:line`；
3. owner decision record 与所选物理方案（只在 owner 已裁后出现）；
4. forward migration、旧数据/old pin兼容、失败/恢复路径；
5. 正例、反例、replay/race/crash window 与四层适用测试；
6. `FG-NH-*` 检查、可复现命令、evidence artifact；
7. exit gate、rollback/stop condition、向下游交付的版本化 contract。

---

## 12. 交叉引用与修订历史 `[可选]`

- **foundational**：[`pre-initial-planning-qna.md`](pre-initial-planning-qna.md)
- **被 supersede**：[`initial-planning.md`](initial-planning.md)
- **critique**：[`thoughts-on-initial-planning-by-GPT.md`](thoughts-on-initial-planning-by-GPT.md)
- **assessment 编排**：[`assessment-index.md`](assessment-index.md)
- **reference-anchor**：[`reference-anchor/`](reference-anchor/)
- **模板**：`.adocs/templates/planning-proposed.md`
- **下游（待创建）**：`pre-charter-qna.md`、`planning-final.md`、`docs/plan/new-harvest/AP-NH1.md`…`AP-NH9.md`

| 版本 | 日期 | 作者 | 主要变更 |
|---|---|---|---|
| `v0.1` | `2026-08-29` | GPT | 初稿：21 条 T-R；逐项裁定 14 条 T-P；9 AP DAG；18 owner 问题（零答案）；四层测试、10+3/七意图/crash matrix、17 个防假绿 hard gate |

---

## 附录 A · Face → Truth → AP → Test traceability

| face | 主 Truth | 主 AP | 主要验收 ID |
|---|---|---|---|
| 01 graph/kind | `T-R-NH-01..03` | NH1/NH2/NH8 | `NH-A-01-*`; `NH-A-09-16/17` |
| 02 S05 | `T-R-NH-04` | NH1/NH3/NH9 | `NH-A-02-*`; `NH-A-09-10/11` |
| 03 representation | `T-R-NH-05/06` | NH1/NH3/NH6/NH7 | `NH-A-03-*` |
| 04 clean | `T-R-NH-07/08` | NH1/NH7/NH9 | `NH-A-04-*` |
| 05 runtime | `T-R-NH-09/10` | NH1/NH6/NH7/NH9 | `NH-A-05-*`; `NH-A-09-12/13/19` |
| 06 upload | `T-R-NH-11/12` | NH4/NH7/NH9 | `NH-A-06-*`; `NH-A-09-14/15` |
| 07 semantics | `T-R-NH-13/14` | NH5/NH7/NH8/NH9 | `NH-A-07-*`; `NH-A-09-18` |
| 08 publication/lifecycle | `T-R-NH-15..17/21` | NH1/NH7/NH8/NH9 | `NH-A-08-*` |
| 09 assurance | `T-R-NH-18/19` | 全 AP；NH9 汇总 | `NH-A-09-*`; `FG-NH-*`; `W-NH-*` |

## 附录 B · 已交付 / 勿重做 quick fence

| 已交付资产 | 本链允许的 delta | 禁止动作 |
|---|---|---|
| strict SourceDescriptor + caller禁workflow_key | resolver改kind-only、fact/graph接线 | 开 caller workflow_key、第五 kind |
| 10 strategy / 9 capability / 3 API map | 统一 admitted-clean、prompt/binding、live activation | 重写 pure handlers/provider parsers |
| 七表无环/guard/pin/compat | selected merge、representation predicate、kind migration | JSON step-list、自由表达式、action_branch |
| Task/Gate/Process CAS/replay | actual S05/upload/new path覆盖 | 新状态机、口头 exactly-once |
| S13 CAS/catalog/verify/GC fence | upload/bounded-write/hold/public boundary | R2/presign/path身份、upload即Item |
| S04 semantic table / API six tuple | non-API authority、overlay、facet | JSON/R2/model context作SSOT |
| system g0 + LS-RAG tail + proof/pointer | vertical接线、query/facet/exact-clean | 重开cuts、按通道复制tail |
| lifecycle服务/CAS | 七意图非法格、API Item、retrieval终验 | 只查Task/DB状态宣称产品完成 |
