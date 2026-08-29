# new-harvest initial-planning 状态分析、评审与后续建议

> **对象**：`initial-planning.md v0.1 draft` 与其上游 `pre-initial-planning-qna.md v0.5 frozen`
> **日期**：`2026-08-29`
> **作者**：`GPT`（panel：`none`）
> **文档性质**：`eval / state-analysis`（本文是现状快照 + 前瞻交接；不是 closure / verdict / charter）
> **文档状态**：`reviewed`
> **对照基线**：仓库 HEAD `1221aa1`；`docs/baseline/**` accepted truth；当前 `intake/`、Workflow、S04/S13、publication/retrieval 实现
> **上游权威输入**：
> - [`initial-planning.md`](initial-planning.md) v0.1
> - [`pre-initial-planning-qna.md`](pre-initial-planning-qna.md) v0.5 `frozen`
> - `docs/baseline/domain-truth/{S03,S04,S05,S13,D04,D05,D08}*.md`
> - HEAD 代码、针对性 unit/intake/e2e 复跑、`context/legacy-family/` clean 实现考古
> **下游消费者**：owner 对真相修订的决定；`planning-proposed`；new-harvest executional QNA / spikes

---

## 0. 水位 / 健康一句话（TL;DR）

- **一句话现状**：`AMBER-RED / 条件通过`——这是一份方向成熟、对自身 provisional 性质诚实的 initial 草案，但它低估了 Workflow 表达力、两阶段 S05 binding、真实多模态运输和语义检索面的改造深度；可进入事实回灌轮，不能据此直接冻结 AP 或开工。
- **核心结论**：
  1. **业务目标和主方向基本到位。** “通道是验收格，不是施工边界”、kind 家族、绑定前有限再获取、同一 admitted clean、上传只产生 S13 handle、FilterMeta 与 g0 分账，这组产品法整体值得保留。
  2. **七簇切法有辨识度，但不是最终施工切法。** 簇 1–6 大体成立；“簇 7 失败法与证明”应改成贯穿每个 AP 的 assurance thread，最后只保留闭集收口，不应把失败法推迟到 NH5。
  3. **执行深度尚不足。** 最大漏项不是某个 PDF 库，而是当前七表无法直接表达“多个 acquire/decode/clean 分支汇到一个固定输入”的 one-of binding；route guard 也读不到 decode evidence。`T-O-384/388` 因此至少要求一份明确的 graph/binding 方案（大概率涉及引擎/持久化扩展），不是简单合并既有 profile identity。
  4. **冻结真相中有一处必须修、一组必须澄清。** `s05_binding_digest` “选 clean 边后才封闭”与已冻 S05/D04/glossary 的“Execution 创建时 NOT NULL 且含 actual clean/preflight refs”存在真实冲突；QNA §9.5.2 #4 将它只解释成与 S03-T017 的时序和解，审查不完整。应以 append-only 新 Truth 明确两阶段 binding，并同步校准 baseline 与 DDL。
  5. **当前代码并非 clean 空壳。** 10 策略 registry、web/doc/pdf 纯函数、三 provider 严格映射、双 digest、五维语义、scatter child publication 已经落地；真正缺的是默认组合根、真实 PDF/browser/multimodal adapter、可达路由、非 API 语义权威和无补丁闭集证明。后续计划必须以“保留并接活”为主，而不是重写 clean。

### 0.1 进门裁定

| 下一动作 | 裁定 | 说明 |
|---|---|---|
| 以本文和 initial 为输入，发起 executional QNA / spike | **GO** | 正是 initial → proposed 之间应做的事实回灌 |
| 直接把 initial 原样提升为 `planning-proposed` 并冻结 DAG/AP | **NO-GO** | 必须先吸收 §4–§6 的阻断项 |
| 直接派生 `AP-NH1…AP-NH5` 并施工 | **NO-GO** | 图 binding、S05 digest、运行时和语义输入合同尚未可执行 |
| 修订真相与 start-gate 后进入 `planning-proposed` | **CONDITIONAL GO** | 不需要推翻整套产品法，但必须改基数、时序、AP 边界和 DoD |

---

## 1. 方法与对照基线

### 1.1 对照基线

- **文档基线**：initial 自宣告为站①、冻结零决策，工作项只要求 first-cut（`initial-planning.md:3-10,194-197`；模板 `.adocs/templates/planning-initial.md:109-117`）。因此本文不会因它“没有具体 step_key/库名”本身扣分，而只追究：是否识别了真正挡施工的合同、是否把它们放对 phase/gate、是否错误声称事实已经核准。
- **冻结基线**：QNA `T-O-376..389` 是 owner-gated 产品法；但 “frozen” 不等于与更早 baseline/HEAD 自动一致。本文按 state-analysis 纪律重新对账。
- **代码基线**：当前 HEAD，而非 D08 Appendix A 的目标态。负面事实以可复现的代码闭集、DDL 和测试为准。
- **legacy 基线**：`context/legacy-family/` 仅是 ReferenceAnchor；只核查其实际行为与已吸收语义，绝不把其 Worker/R2/SMCP/Cloudflare/Gemini 栈当可复用实现。

### 1.2 证据来源与核查方法

| 证据面 | 核查内容 | 主要锚点 |
|---|---|---|
| Workflow 定义/注册/运行时 | 图基数、固定 step、guard、binding、无环、兼容 revision | `src/workflows/lsrag_definition.py:881-1080`; `src/contracts/workflow/models.py:245-278,373-443,476-525`; `src/runtime/workflow/runtime_materialize.py:49-168` |
| S05 binding/持久化 | `s05_binding_digest` 创建、传播、读方与 NOT NULL | `src/persistence/migrations/001_initial.sql:225-250`; `src/runtime/task/task_create.py:167-181,304-370`; `src/runtime/workflow/runtime_core.py:888-915` |
| 表示/acquire/decode | browser、print PDF、PDF 文本层、opaque doc、evidence | `src/runtime/intake/acquisition_ingest.py:403-676`; `src/runtime/intake/types.py:144-220`; `api/app.py:332-345` |
| clean 当前实现 | 10 策略、九 process capability、三 provider map | `src/contracts/intake/strategies.py:15-164`; `intake/__init__.py:20-132`; `intake/{web,pdf,doc}/`; `intake/api/` |
| 上传/S13 | public route、purpose、catalog、GC | `api/public/routes.py:29-469`; `src/contracts/storage/models.py:16-29`; `src/persistence/migrations/001_initial.sql:837-873`; `src/services/object_gc.py:133-161` |
| 语义与 retrieval | 五维写入、stub、S06 projection、公开 filters | `src/runtime/intake/acceptance_snapshot.py:576-641`; `src/runtime/intake/generation_construct.py:329-343`; `src/runtime/intake/generation_assemble.py:17-62`; `src/services/retrieval/models.py:14-34` |
| legacy clean | universal 分叉、dedicated ETL、空成功/skip、FilterMeta | `context/legacy-family/smind-skill-clean-{universal,dedicated-apis}/**`; `smind-clean-dispatcher/services/mapper.ts` |
| 动态验证 | clean unit/intake、registered API e2e、source capability e2e | 见 §7 与附录 A |

### 1.3 本评审的限制

- 未运行全仓 572+ 用例；只运行与 new-harvest 直接相关的 39 个选定 case，并单独复跑两个承重 e2e。
- 未选择 PDF/browser/OCR 库，也未修改产品代码；这些属于下游 executional 决策。
- e2e 的 `disk I/O error` 属仓库已登记 Turso harness 缝，不将它误判为 API mapper 业务失败；但它仍意味着闭集证明当前不绿（`README.md:606-615`）。

---

## 2. 回看清单（评审快照）

### 2.1 initial-planning 价值台账

| 单元 | 草案声称/设计 | 真实落地或核查结论 | 评级 | 锚点 |
|---|---|---|---|---|
| 文档角色诚实性 | first-cut、冻结零决策、需事实核查 | 自宣告清楚，未把库名/step_key 冒充冻结；符合站①模板 | `delivered` | `initial-planning.md:3-10,39-81,194-197,512-524` |
| foundational truth 映射 | CITE `T-O-376..389` 并转成 scope/DAG | 主体转述准确；但继承了图数误差，并漏掉 S05/D04 的真实冲突 | `partial` | `initial-planning.md:43-62`; QNA `74-95`; §4.1 |
| “通道 ≠ 施工簇” | 七簇按产品法底物切分 | 判断基本正确，能防四条 AP 重复改同一 kind 图；簇 7 应改为横切 assurance | `partial+` | `initial-planning.md:327-341,498-508` |
| 图与晚绑定 | kind graph、guard、digest、再获取同一 revision | 产品方向可取；当前 engine 缺 route fact 与 one-of binding，工作量被低估 | `partial` | `initial-planning.md:198-207,345-370`; code §4.2 |
| 表示/clean | 真 PDF、browser、print PDF、10+3 live | 缺口识别不全；遗漏 opaque office document 和 multimodal transport contract；同时低估已完成 pure clean/API map | `partial` | `initial-planning.md:218-230,373-415`; code §4.3/4.4 |
| 公共上传 | S13 handle，两步 ingest，幂等/GC | 身份方向正确；缺 catalog-without-ref、grace race、streaming/auth/size/CAS 冲突设计 | `partial` | `initial-planning.md:209-216,418-436`; code §4.4 |
| 语义分账 | 四通道五维入 Revision、不进 g0 | 方向正确；遗漏 ingest typed semantic 输入、S06 system overlay、public facet/filter 及 `channel` 名冲突 | `partial` | `initial-planning.md:231-239,440-457`; code §4.4 |
| publication/生命周期 | 复用尾链、七意图、走到 retrieval | API scatter 与已选 single profile 已有真实尾链；计划没有把“检索命中 + 五维过滤”写成逐格 DoD | `partial` | `initial-planning.md:461-477`; `tests/e2e/test_registered_api_scatter.py:209-321` |
| 失败法与测试 | NH5 无 monkeypatch 闭集证明 | 退出方向正确；把失败测试主要放最后会延迟暴露 engine/adapter 设计错误 | `partial` | `initial-planning.md:240-247,273-281,481-494` |
| DAG/AP 切分 | NH1→NH3→NH4→NH5；NH2 等 NH1 后并行；五份 AP | NH2 无产品依赖必须等待 NH1；NH1/NH3 均过大，NH3 不宜把 browser、PDF、multimodal 合为一枪 | `placeholder` | `initial-planning.md:155-190`; §4.5 |
| legacy 借用边界 | 借语义不借栈；拒绝 `action_branch`/空成功 | 总方向准确；没有把已吸收量、silent per-member skip 和虚构 summary key 全量计入工作量 | `partial+` | `initial-planning.md:31,358,383,406,428,450,488`; §4.3 |

### 2.2 当前代码能力快照（不是规划声称）

| 能力单元 | 当前真实水位 | 评级 | 关键证据 |
|---|---|---|---|
| 10 个 clean strategy 定义 | 10 键、capability/LLM/browser/budget 均 versioned | `delivered-contract` | `src/contracts/intake/strategies.py:15-151` |
| web/doc/pdf clean 纯函数 | deterministic、LLM、OCR/Vision/PDF 路径均有 typed 实现；依赖注入测试通过 | `partial-live` | `intake/web/__init__.py:25-104`; `intake/pdf/__init__.py:12-74`; `intake/doc/__init__.py:11-113` |
| registered_api 三 operation | 严格 schema/map、非空 member clean、双 digest、五维/semantic tuples、scatter child publication 已通 | `delivered/需 retrieval 终验` | `intake/api/registry.py:73-148`; `src/contracts/intake/semantics.py:12-63`; `tests/e2e/test_registered_api_scatter.py:209-321` |
| public 可选 single graphs | 7 个 profile key；创建时按 kind×mode×声明 media 选图 | `legacy-current` | `src/workflows/lsrag_definition.py:929-940`; `src/services/config_snapshots.py:492-516` |
| 未公开可选 single graphs | **6 个**，不是 QNA/initial 多处写的 5 个；总 single-root identity 为 13（base inline + tuple 12） | `unreachable` | `src/workflows/lsrag_definition.py:1003-1069`; 附录 A 命令 |
| 晚绑定与再获取 | 当前无 decode 后 clean guard、无第二 acquire/decode 链、无 actual-path digest | `missing` | `src/runtime/workflow/runtime_materialize.py:101-168`; `src/runtime/intake/clean_preflight.py:629-686` |
| browser / print PDF | 端口形状存在，默认组合根未注入；evidence 常量无法证明 renderer 版本；从不产 `print_pdf` | `placeholder/missing` | `src/runtime/intake/core.py:39-75`; `api/app.py:332-345`; `src/runtime/intake/acquisition_ingest.py:474-538` |
| PDF 真文本层 | 正则扫描 PDF literal；无层在 decode 阶段盗用 OCR-unavailable | `placeholder` | `src/runtime/intake/types.py:144-171` |
| opaque doc 二进制 | 非 PDF/图片被当非 binary 并强制 UTF-8，docx 等无法到 document understanding | `missing` | `src/runtime/intake/acquisition_ingest.py:553-564` |
| 上传 | public API 与 upload purpose 均不存在；CAS/目录/GC 内核存在 | `missing surface / delivered kernel` | `api/public/routes.py:29-469`; `src/contracts/storage/models.py:16-29`; `src/storage/local_store.py:71-105` |
| 非 API 五维语义 | `filter_metadata={"source_kind":...}` stub；五维 definition 已登记但未写 | `placeholder` | `src/runtime/intake/acceptance_snapshot.py:589-615`; `src/services/registry.py:229-239` |
| g0=clean | 系统丢弃模型 g0，并把完整 clean 写成唯一 g0 original | `delivered` | `src/runtime/intake/generation_assemble.py:17-62` |
| S06/retrieval 语义消费 | structurize 输入只有 clean+markdown；模型 context_meta 未被 revision semantics 覆盖；公开 filter 仅 item/source_kind/vector-channel | `missing` | `src/runtime/intake/generation_construct.py:329-343`; `src/runtime/intake/generation_assemble.py:51-60`; `src/services/retrieval/models.py:14-34` |

### 2.3 Deferred / Carried-over 台账（每条带 reopen 触发器）

| 编号 | 项目 | 为什么现在不能直接冻结 | reopen / 关闭触发器 | 携带至 |
|---|---|---|---|---|
| `D-NH-01` | 两阶段 S05 binding 真相与 schema | QNA 与 S05/D04/glossary/DDL 实际冲突 | 新 append Truth 明确 policy binding、actual binding、seal CAS、retry/recovery；baseline 同步校准 | pre-proposed executional QNA |
| `D-NH-02` | guarded one-of binding / branch convergence | 现模型每个输入只能有一个固定上游输出 | spike 用一张最小 kind 图证明 `decode→N clean→one seal` 与 `static→decode→browser→decode→clean` 可编译/运行/恢复 | NH0/NH1A |
| `D-NH-03` | route fact/evidence chain | guard context 不读 decode/acquire evidence，state 只有单个 evidence | 冻结 typed representation fact schema、durable source、history digest 与 preflight 校验 | NH0/NH1A |
| `D-NH-04` | real browser/PDF/multimodal runtime | 仓库无依赖/adapter；现 S11 generate 与 CLI 都是 text-only | 每类真实 adapter 有最小默认组合 smoke、readiness、预算与安全隔离证据 | capability APs |
| `D-NH-05` | 五维语义权威与 retrieval facet | ingest 无字段；模型 context 可漂；public `channel` 已占 vector channel | owner 决定值来源/unknown 法/字段名；实现 acceptance→S06→retrieval 的闭环 | semantic AP |
| `D-NH-06` | upload catalog/GC/读取边界 | 只有 byte store；public read 在 QNA 详述与 Truth 摘要间含糊 | upload service 能 catalog orphan、replay、并发、GC；owner 明确是否有 public read | upload AP |
| `D-NH-07` | 图身份/兼容 revision 清册 | initial 使用“7+5/12”错误分母，未含 6 个不可选和旧 pinned revisions | 输出 13 single identities + scatter + compatibility revision 的迁移/保留/退役表 | planning-proposed |
| `D-NH-08` | 逐格 DoD | “10+3 live”未展开 source/acquire/representation/strategy/semantic/retrieval 组合 | 闭集矩阵每格有 fixture、success terminal、publication proof、retrieval hit/必要 facet、失败反例 | planning-proposed/NH5 |
| `D-NH-09` | `.experiment` 发车 | owner 明确未冻结日期 | owner 单独发车；永不作为 NH 实现完成的替代证据 | 后续实验令 |

---

## 3. 对账诚实（声称 vs 真实）

| 声称 | 真实 | 偏差类型 | 证据 | 影响 |
|---|---|---|---|---|
| HEAD 是“7 公开 + 5 选不中 / 12 张图” | 代码是 7 个公开 selector key、**6 个**不可选 identity；相关 single-root identity 共 **13** | `under-count` | `src/workflows/lsrag_definition.py:929-940,1003-1069`; 附录 A | 迁移清册、兼容图和测试分母少一项 |
| `_source_profile_workflow` 只替换 3 个 process key | 正确；但这不等于加多分支只改该 helper | `under-claim complexity` | `src/workflows/lsrag_definition.py:881-926`; `src/contracts/workflow/models.py:476-525` | 需改 binding/route/materialization，而不只是 graph factory |
| human_review 已证明晚绑定同构 | 只证明 guard 可选已画 route；human review 不需要把多个 alternative output 汇到一个下游 input，且 CONTROL runtime 只支持 human/scatter join | `over-claim analogy` | `src/runtime/workflow/runtime_materialize.py:505-514`; `src/contracts/workflow/models.py:482-525` | 不能把它当 NH1 可行性证明 |
| `s05_binding_digest` 推迟封闭只是实现后果，不是产品法冲突 | S05/D04/glossary 明写 Execution 创建时锁 actual refs、列 NOT NULL；HEAD 也创建即写 domain digest | `truth-conflict` | `docs/baseline/domain-truth/S05-intake-cleaning.md:225-230,466-478`; `docs/baseline/domain-truth/D04-turso-physical-schema.md:615-623`; `docs/baseline/spec-glossary.md:231`; `src/persistence/migrations/001_initial.sql:245-246`; `src/runtime/task/task_create.py:167-181` | 必须新 Truth + schema evolution；不可在 AP 中悄悄改语义 |
| NH2 在 NH1 后才能并行 | 上传只依赖 Team auth、S13 catalog/CAS/GC，与 kind graph/clean route 无产品依赖 | `false-dependency` | initial `160-175`; `storage/ports.py:10-24`; `object_gc.py:133-161` | 不必要延长关键路径；NH2 可 day-0 与 engine spike 并行 |
| NH3 是“让 10+3 工人产出 clean” | 大量工人函数与 API map 已存在且 33 个相关 unit/intake case 全绿；缺的是 reachability、real adapter、prompt/binding 与默认组合 | `under-claim delivered` | `intake/__init__.py:20-132`; §7 | 若按“重写工人”施工会制造重复代码和回归 |
| “组合根无 clean_llm”足以概括 LLM 缺口 | text LLM 可借 Claude CLI；但 CLI 明确拒绝非 text，Inference Generate request 也只有 `input_text`；OCR/Vision/二进制理解没有现成运输 | `oversimplification` | `src/runtime/intake/clean_preflight.py:76-120`; `src/runtime/inference/claude_cli.py:490-519`; `src/contracts/inference/models.py:96-118` | `T-P-NH-6` 未经 spike，不应默认“复用现有端口即可” |
| 表示诚实主要是 PDF/browser/HTTP media | docx/opaque office bytes 也会因 UTF-8 decode 在 clean 前失败，未进入草案清册 | `missing-case` | `src/runtime/intake/acquisition_ingest.py:553-564`; `intake/doc/__init__.py:33-113` | doc.document_understanding 仍物理不可达 |
| NH4-01 写五维，NH4-02 保证不进 g0 即可 | ingest 无 typed 五维输入；S06 不读 revision semantics；模型 `context_meta` 会被保留；public filters 不含五维且 `channel` 已代表 original/summary | `over-claim` | `src/contracts/api/models.py:181-207`; `src/runtime/intake/generation_construct.py:329-343`; `src/runtime/intake/generation_assemble.py:51-60`; `src/services/retrieval/models.py:14-34` | NH4 至少是 L/high，不是 M/med |
| PDF/browser/OCR 选型放在 Out-of-Scope/O6 | 它们只是 **initial 文档暂不冻结**，却是 campaign 完成 `T-O-381` 的必要 in-scope 执行决定 | `scope-mislabel` | `initial-planning.md:133-142,251-270`; QNA `85,805-818` | 容易被后续 AP 误读成可 defer 出战役 |
| 测试最后在 NH5 证明即可 | engine binding、actual digest、adapter 安全若到末期才 e2e，会产生多轮图 revision 返工 | `late-verification` | initial `172-178,240-247`; 当前 source e2e `test_source_capability_paths.py:71-218` 仍失败 | 每个 capability AP 必须自带 unit+integration+default-root e2e；NH5 只做闭集总验 |
| API 三 operation 属 NH3 待“做 live” | 三 operation 已有真实 Process、语义持久化和 child publication-ready e2e | `under-claim` | `tests/e2e/test_registered_api_scatter.py:209-321` | API 应是 preservation/regression lane，新增工作主要是 retrieval 终验与统一新 binding |
| g0/尾链是 NH4 待建设 | g0=clean 和现有 publication tail 已落地；NH 应接线和校验，不重写 | `under-claim` | `src/runtime/intake/generation_assemble.py:17-62`; `src/workflows/lsrag_definition.py:161-218,425-448` | 有助于缩小 NH4 算法范围，但需补语义投影 |
| legacy 只提供分叉/FilterMeta/空成功反例 | 基本正确；还应点名 per-member silent skip、phantom `summary.jsonl`、random UUID、直接供应商 fetch/cookie/header | `incomplete-legacy-audit` | §4.3 | 若只禁栈不禁这些成功语义，会把 legacy 债借回 |

- **诚实结论**：initial 不是“方向错”，而是“把产品法写清了，却把使产品法可编码的引擎代数和运行时运输藏在几个 M/L 工作项里”。它对 stage 身份很诚实，对代码底层约束仍不够诚实。下一轮必须将这些发现登记为 `T-R`/execution truths，而不是在 proposed 中原样接受 provisional DAG。

---

## 4. 归因 / 缺口分析

### 4.1 冻结真相层审查：保留、校准还是修正

先直接回答“真相层与代码是否严重冲突”：**有严重实现冲突，但不能把所有差距都叫真相错误。** `T-O-381/384/388/389` 本来就在定义 HEAD 尚未达到的目标，因此 browser、kind graph、reacquire、五维缺失属于预期的 design-to-code delta；真正的 **truth-to-truth / truth-to-schema 冲突** 是两阶段 `s05_binding_digest` 与 S05/D04/glossary/DDL 的创建时 actual-binding 法。另有图基数 `5→6` 的事实错误，以及 upload read、zero collection、semantic facet 三处需要澄清的语义缝。处理次序必须是“先修真相冲突，再按真相改代码”，不能让旧代码反向否决正确产品方向，也不能以 owner frozen 掩盖冲突。

| Truth | 建议 | 辩证判断 | 必要动作 |
|---|---|---|---|
| `T-O-376` completeness | **保留** | 禁 503 假完成、要求真实 Process→publication→retrieval 是正确反镀金门 | 将“真实向量”落实成逐格 proof + retrieval hit，不以 Task succeeded 代替 |
| `T-O-377/379` 四 kind + 三轴 + 禁 caller workflow_key | **保留** | 与 current strict descriptor 和 legacy 去 taxonomy 一致 | 明确 strategy key 与 process key 非一一映射，actual binding 必须记两者 |
| `T-O-378` honesty | **保留** | HEAD 反例均真实；还应补 opaque doc 和 fabricated browser profile | 扩反例清单，不改原则 |
| `T-O-380` 测试/实验分账 | **保留** | 正确；experiment 不应成为功能 DoD | 无需修订 |
| `T-O-381` live matrix | **保留，补矩阵解释** | 闭集有价值；但要区分“10 strategy identity”“9 process capability”“3 API operations”，避免笛卡尔积误读 | 在 proposed 给合法 compatibility matrix；明确 exhausted zero collection 与 empty member 的不同结局 |
| `T-O-382/383` bind-before/fail-after | **保留** | 防 silent downgrade 与 try-all，产品法清晰 | 冻结 route fact/evidence 与 seal CAS 的执行合同 |
| `T-O-384/387/388` 同 revision、kind graph、有限再获取 | **保留意图；必须新增校准 Truth** | kind family 优于 profile 爆炸；但现 engine 无 one-of binding，且两阶段 digest 与旧 truth 冲突 | 新 append Truth 解决两阶段 binding；完成 graph-expressiveness spike 后才冻结具体 execution 方案 |
| `T-O-385` upload identity | **保留，澄清 public read** | bytes-first、upload≠Item 正确；与 CAS/GC 内核契合 | 明确 upload 是否唯一 public object 动作；若不开放 raw read，修正文中 Q1 “上传/读取”字面 |
| `T-O-386` single admitted clean | **保留** | 与现 clean handlers、API map、g0 代码和 legacy dedicated 无 AI 分账一致 | 让 deterministic/API actual binding 使用 strategy/mapper digest；不要伪造 promptA |
| `T-O-389` dual ledger | **保留，补 authority/facet 执行真相** | 不把过滤维塞进 clean/g0 是正确的 | 冻结 ingest 语义来源、unknown 法、S06 system overlay、public facet 名称/查询能力 |

#### 必须修正的 Truth：两阶段 S05 binding

QNA 的和解只处理了 “Workflow revision 创建时冻结” 与 “clean edge 后选” 的关系（`pre-initial-planning-qna.md:760-769`），没有处理下列更早冻结事实：

- `S05-T025`：Execution 锁本次 **实际** source/acquisition/clean/preflight refs 与 digest（`S05-intake-cleaning.md:225-230`）；
- glossary：`s05_binding_digest` 在 Execution **创建时**锁 actual refs（`spec-glossary.md:231`）；
- D04：`mkb_executions.s05_binding_digest` `NOT NULL（创建时）`（`D04-turso-physical-schema.md:615-623`）；
- 物理 DDL 确实 `NOT NULL`（`src/persistence/migrations/001_initial.sql:245-246`）；
- HEAD 用 `domain_binding_digest` 填充它，而 ProcessCommand 又只携带 domain binding（`task_create.py:167-181,337-368`; `runtime_core.py:888-915`）。

**推荐的 append-only 校准形态**（字段字面仍可在 execution QNA 冻结）：

1. Execution 创建时冻结 `workflow/revision/compiled_digest` + **S05 policy/envelope digest**：合法 acquire/decode/clean/preflight manifests、route policy 与版本；这是非空、immutable。
2. 表示路径走完、clean edge 决定时，以 CAS 一次封闭 **actual S05 binding digest**：实际 acquisition chain、decode facts、strategy key、process key、prompt/adapter（若有）、preflight manifest。
3. 未封闭不是假 digest；schema 需要 nullable actual 列或明确的 binding state/sealed_at，禁止拿 domain digest 冒充 actual S05。
4. clean 及后续 ProcessCommand 必须携带 actual S05 digest；acquire/decode 只能携带 policy digest。现单一 `binding_digest` 需要分名或强类型。
5. retry/recovery：已封闭则原值重放；封闭前恢复重放同 revision/policy 与 durable representation facts，不重新解析 active registry；Task causal restart 的新 generation 规则另定。
6. IntakeSnapshot/CandidateSet/Gate/Proof 只接受 sealed actual digest；不能继续 `stable_digest({"binding": domain_binding_digest})`（`clean_preflight.py:373-407,476-510`）。

这不是文案润色，而是 truth + forward-only schema evolution + runtime transaction 的联合变更。

### 4.2 当前 Workflow substrate 与 frozen graph law 的五条承重缝

| 缝 | 当前事实 | 为什么挡施工 | 必须形成的 execution truth |
|---|---|---|---|
| `W1 one-of binding` | 每个 target input 只允许一个 binding，且 `PRIOR_OUTPUT` 固定一个 source step（`models.py:482-525`） | `decode→cleanA/B/C→seal` 时，seal 的 `clean_candidate` 无法从“实际执行的任一 clean”取值；二次 decode 同理 | 扩展 versioned one-of/selected-output binding，或引入有 typed port 的 merge/control；禁止复制整个 publication tail 规避 |
| `W2 route facts` | predicate 闭集只有 admission/intent/metadata/markdown；runtime context 只从 Task/Candidate/transition/audit 取值（`models.py:245-278`; `runtime_materialize.py:101-168`） | decode 的 text layer、media、shell/print need 无法进入 guard | 冻结 representation fact schema、durable authority、predicate→fact mapping、missing fail-closed |
| `W3 control/merge` | runtime CONTROL 只支持 `human_review_gate` 和 `scatter_children_join`（`runtime_materialize.py:505-514`） | initial 将 human_review 当同构证明，但它没有 selected-output merge 语义 | spike 决定纯 guarded route 是否足够；若需 merge control，必须注册并进入七表/compiled digest |
| `W4 reacquire state` | state/preflight 只有一个 `acquisition_evidence`、一个 `decode_evidence`，expected acquire 由 descriptor mode 反推（`clean_preflight.py:622-686`） | static→browser/print 后会覆盖而非保留路径，preflight 仍认为 static 才合法 | acquisition/decode evidence chain、每 step identity、path digest、actual final representation 与 seal 时序 |
| `W5 migration` | 每个旧 profile 有 active + compatibility revision；runtime 只执行加载的 reviewed definitions（`lsrag_definition.py:1057-1080`; `runtime_core.py:594-634`） | 删除/改 key 会使 pinned Execution 无 interpreter；“并入”不是物理删除 | 新 kind identities + old identity compatibility/retirement table；in-flight/retry smoke |

**裁定**：NH1 当前估为若干 `M/L` 不可信。它至少是 `XL/high` substrate migration，且必须拆成 “引擎表达力/两阶段 binding” 与 “kind graph rollout” 两个 AP 或两个 closure gate。

### 4.3 legacy-family clean 精准核查

#### 4.3.1 universal cleaner：可借与不可借

| 实现事实 | 精确确认 | 对 MKB 的意义 |
|---|---|---|
| 六个产品分叉 | registry 登记 `htmlCrawl`、`htmlCrawl-geminiClean`、`browserFetch`、`browserFetch-geminiClean`、`browserPDF`、`geminiUnderstanding`（`action_registry.ts:91-149`）；cleaner 另接受未登记 alias `browserPDF-geminiClean`（`cleaner_web.ts:295-301`） | **借 acquire×strategy 分轴**；不借 branch 字符串/alias 漂移 |
| 静态/浏览器获取 | 静态直接 `fetch` 且允许 payload headers；浏览器/打印 PDF 直打 Cloudflare API（`cleaner_web.ts:65-93,99-134,142-207`） | 证明 capability 的业务外延；runtime、任意 header、CF token/endpoint 全部禁止吸收 |
| HTML 规则 | `HTMLRewriter` 删除 chrome/脚本并留有限属性（`core/sanitizer.ts:31-130`）；non-AI 再用 regex 去标签（`cleaner_web.ts:40-54`） | MKB 已把规则吸收到 stdlib structural sanitizer/parser；不应复制 regex/Worker API |
| LLM 分账 | 只有 `*-geminiClean` 和 browser PDF / document understanding 调模型（`cleaner_web.ts:244-301`; `cleaner_doc.ts:98-129`） | 支持 `T-O-386`：deterministic 仍是 clean，promptA 只在 LLM strategy |
| 输出成功语义 | web/doc 无非空检查，仍写 `clean_text` 并返回 `plainTextAvailable: true`（`cleaner_web.ts:312-329`; `cleaner_doc.ts:131-151`） | 是明确反例；MKB 当前 `CLEAN_EMPTY` 应保留 |
| I/O/身份 | 输入输出由 SMCP slot + R2 key 管理（`io_manager.ts:92-155,191-263`） | 只借 typed slot 思想；不借 R2/SMCP、key=成功 |
| 路由安全 | router 按 branch 前缀选 schema，未知特征会 warn 后跳过验证（`flows/router.ts:61-100`） | `T-O-384` 禁表外 branch/自由表达式是必要的 |

#### 4.3.2 dedicated API cleaner：已经吸收的价值与必须删除的债

| 实现事实 | legacy 证据 | HEAD 对账 |
|---|---|---|
| 3 provider × 1 operation | `action_registry.ts:59-79` | 已成为 exact `(provider,operation,version)` registry：`intake/api/registry.py:73-125` |
| FilterMeta 五维 + ContextMeta tags | chinatax `processor.ts:72-97`；domain `86-114`；REA `68-127` | 已成为 strict `FilterMeta/ContextMeta/SemanticTuple`：`src/contracts/intake/semantics.py:12-63` |
| content/meta 双 hash | 三 provider processor 都分 body/meta 计算 hash | HEAD parser 输出 canonical content/meta digest，并进入 member evidence：`intake/api/__init__.py:46-90` |
| per-member parser error | chinatax/domain `catch→warn→return null`（各 `processor.ts:147-155` / `165-173`）；REA catch 后继续（`204-286`） | HEAD strict descriptor/member schema与 map fail-loud，不 silent skip：`api/models.py:145-171`; `intake/api/registry.py:128-148` |
| 空集合/坏 envelope | chinatax/domain 仅 warn 后成功；REA 非数组直接返回空 success + 未写入的 `summary.jsonl` 字面（`realestate/processor.ts:183-192`） | HEAD 要 exhaustion proof；zero collection 可 typed success/no-item，但该精确 disposition 尚需写进 execution truth |
| child identity | legacy 每 member `uuidv4()`，文件 key/summary key 当结果 | HEAD 用 canonical external key、snapshot/change set/child Execution；不借随机 UUID/R2 key 成功语义 |
| live supplier fetch | legacy 直连 tunnel/Domain/REA cookie | HEAD 只接 caller-frozen records，符合 QNA OOS；不得因 legacy 有客户端就扩大 NH |

#### 4.3.3 对 legacy 的最终裁定

`initial-planning` 对“借语义不借栈”的方向是对的，但应把 legacy clean 状态写成三类，而不是笼统“参考”：

1. **已吸收且应冻结保护**：provider schema/operation、stable key、parser、双 digest、FilterMeta/ContextMeta、web sanitize 规则、acquire×strategy 分叉；
2. **仍需接活但不需重写**：browser/print PDF/document understanding/OCR/Vision 的真实 adapter 和默认组合；
3. **必须持续禁止**：`action_branch`、prefix schema dispatch、任意 headers/cookie、SMCP/R2/CF runtime、per-member skip、empty success、phantom key、random child identity。

### 4.4 七个业务簇的逐簇评价

| 初始簇 | 内聚判断 | 代码事实 | 调整建议 |
|---|---|---|---|
| 1 图与晚绑定信封 | **方向成立，但过宽** | 同时跨 Workflow schema、route evaluator、Process materialization、Execution DDL、S05 evidence | 拆 `1A 引擎/binding substrate` 与 `1B kind graph rollout`；1A closure 后才允许 1B |
| 2 表示与再获取 | **成立，清册不完整** | PDF/浏览器之外还有 opaque doc；evidence 不是 history；browser port 过窄 | 增加 `opaque_document`/typed browser result/acquisition chain；与 1A 共冻 interface |
| 3 清洁工人与 admitted clean | **成立，但名称应改** | pure handlers 与 API mapper 已大量落地，主要缺 live adapter/reachability/binding | 改成“clean capability activation 与合同收敛”；禁止重写现有 pure transforms |
| 4 公共上传 | **高度内聚、可独立** | CAS/catalog/GC 内核存在，public service 缺失 | 从 NH1 后置改成 day-0 并行；加入 catalog orphan、grace race、streaming、auth、read boundary |
| 5 语义分账 | **成立且比草案更深** | API 五维已写；非 API 无输入；S06/retrieval 未消费 | 拆三个 exit：acceptance authority、S06 projection、retrieval facet；与能力 vertical slice 同步验收 |
| 6 publication/生命周期 | **成立，主要是贯通/验证** | 尾链与 g0 已在；API child publication 已证；source e2e 不绿 | 不新写 kernel；明确七意图 applicability matrix、retrieval hit 与 old revision compatibility |
| 7 失败法与证明 | **不应作为业务簇** | failure/CAS 是每个模块的成功定义，不是最后一层 | 改为贯穿 NH1–NH4 的 assurance thread；NH5 只做全矩阵、故障注入和 closure evidence |

**推荐的簇模型**：保留 1–6 作为产品/技术簇，把 7 改成横切线程；另外单列“外部 runtime/packaging readiness”作为执行工作流，因为它跨 browser、PDF、多模态，不能塞在一个 `NH3-02` 中。

### 4.5 相位、DAG 与 AP 深度评价

#### initial DAG 的三个主要问题

1. **NH2 假依赖 NH1。** 上传不需要 kind graph，可以和 truth/spike/engine 同时开；只在 local-object integration e2e 前会合。
2. **NH1 与 NH3 之间存在被隐藏的双向接口。** graph guard 需要 representation fact；真实 PDF/opaque doc/browser adapter 又决定 fact schema。先完整做 NH1、后做 NH3 会反复发新 revision。应先 spike/freeze interface，再分别施工。
3. **NH3 是一个“超级相位”。** 真 PDF parser、local browser、print PDF、text LLM、multimodal OCR/Vision、opaque docs 与 10+3 matrix 的依赖/风险完全不同，不应由一个 AP-NH3 管完。

#### 推荐的修订 DAG（供 proposed 裁定，不在本文冻结）

```text
NH0 真相修正 + 三个可行性 spike
 ├─▶ NH1A Workflow/binding substrate ─▶ NH1B kind graph + route policy ─┐
 ├─▶ NH2 公共上传（可 day-0 并行）──────────────────────────────────────┤
 └─▶ NH4A 五维输入权威/检索 facet 合同 ────────────────────────────────┤
                                                                        ▼
             capability vertical slices（每片自带 clean→semantic→vector→retrieval）
             NH3A deterministic/static + 真 PDF text
             NH3B browser render + print PDF
             NH3C document-understanding/OCR/Vision multimodal
             API 三 operation = preservation/regression lane
                                                                        │
                                                                        ▼
             NH4B 七意图/semantic projection 贯通 ─▶ NH5 闭集与故障证明
```

#### 建议 AP 切分

| 建议 AP | 责任边界 | 退出判据摘要 |
|---|---|---|
| `AP-NH0` | truth 校准 + graph/multimodal/semantic 三 spike | §6 start-gate 证据齐，owner 决策落盘 |
| `AP-NH1A` | guard fact、one-of binding、two-stage S05 binding、evidence chain、schema migration/recovery | 最小图编译 + crash/retry/recovery 绿 |
| `AP-NH1B` | 四 kind resolver/graphs、旧 profile compatibility/retirement | 13 identity 清册闭合，old pinned + new graph 都可运行 |
| `AP-NH2` | authenticated upload、catalog orphan、replay/conflict、GC/read boundary | 同字节并发 replay；upload≠Item；grace 内 ingest 不被删 |
| `AP-NH3A` | deterministic web/doc、真 PDF text、opaque doc representation | real bytes/default root→retrieval；坏文件 typed fail |
| `AP-NH3B` | browser content + print PDF | 本地真实 renderer，无 monkeypatch，evidence/预算/readiness 完整 |
| `AP-NH3C` | doc/PDF understanding、OCR、Vision | 真实 multimodal adapter 与模型 binding；三策略分别可达且不互相降级 |
| `AP-NH4` | 五维 acceptance authority、S06 system projection、public retrieval facets、七意图 | 四通道五维可查询；g0 不变；metadata/lifecycle 不重 clean |
| `AP-NH5` | 全闭集、故障/竞态/兼容证明、实验骨架 | §6.3 matrix 全绿；发车日仍空 |

若 owner 坚持较少 AP，可在 spike 证明共同 adapter/部署面后合并 NH3B/C；**不能**在证明前以“相位 1:1 五份 AP”作为组织约束。

### 4.6 细节掌控与 gate 分类

initial 的 13 个 `G-NH-*` 能看出作者知道细节尚未定，但把三种不同性质混成了一个 OPEN 列表：

- **开工阻断 gate**：PDF parser/隔离、browser runtime、multimodal transport、one-of binding、两阶段 digest、FilterMeta 权威/查询面、upload catalog/GC；
- **AP 内可定的实现细节**：具体 step_key、predicate 字面、HTTP path 字面、purpose 字符串；
- **不阻塞战役的 owner 调度**：experiment 发车日、AP 数量。

`G-NH-1/2/3/7/8` 实际挡施工；`G-NH-4/5/6` 的字面可后定但其合同不能后定；`G-NH-11/12` 不应放入 start-gate。另需新增：

1. `G-NH-BINDING`：selected-output binding/merge 采用何种 versioned algebra；
2. `G-NH-S05-2P`：policy digest 与 actual digest 的字段/封闭/CAS/retry 法；
3. `G-NH-REP-EVIDENCE`：多次 acquire/decode evidence chain 的 typed shape；
4. `G-NH-OPAQUE-DOC`：office/opaque binary 如何 verify/decode/交给 multimodal cleaner；
5. `G-NH-FACET`：FilterMeta `channel` 与 vector `channel=original|summary` 的公共字段分名；
6. `G-NH-ZERO`：exhaustion-proven zero collection 是 typed no-op success、无变化终态还是显式 empty terminal。

---

## 5. Verdict（价值、债务与可执行性）

| 维度 | 评级 | 一句话 |
|---|---|---|
| foundational 产品方向 | `A- / high` | 大部分 truth 推荐，能有效阻止假接线、profile 爆炸和 legacy taxonomy 回流 |
| initial 的阶段诚实性 | `A-` | 清楚说明冻结零决策、first-cut、需 proposed 裁定，没有冒充 action-plan |
| 业务簇划分 | `B` | 1–6 有内聚；簇 7 应横切；runtime readiness 需独立工作流 |
| HEAD 事实精度 | `B-` | 多数反例正确，但图基数错一、漏 opaque doc/one-of binding/S06 facet 等承重事实 |
| 执行细节掌控 | `C+` | 看见库/端口/prompt，却没看见 binding algebra、two-phase schema、evidence history 与 query facet |
| DAG/AP 可执行深度 | `C / no-go as-is` | NH1/NH3 过大，NH2 假依赖，验证过晚，规模估计偏低 |
| 累积实现债务 | `high` | 不是算法债，而是 graph/schema/runtime/semantic interface 四条高耦合债 |
| 愿景/目标达成度（当前代码） | `partial` | API 与 deterministic/published tail 有实绩；四通道 10+3 默认 live-to-vector 远未达到 |
| **综合健康** | `AMBER-RED / conditional` | 可继续规划，不能继续假定；先 truth repair + spike，再 proposed |

- **反镀金提醒**：不要为了服从“五相位/五 AP”制造整齐水位；不要重写已经通过的 API mapper/g0/tail；不要用 monkeypatch、stub LLM、Task succeeded、publication_ready 单独替代“默认组合 + retrieval hit + facet + failure law”的闭集证据。

---

## 6. 前瞻交接

### 6.1 下一周期建议

下一周期应命名为 **“new-harvest pre-proposed fact resolution”**，而不是直接写 AP。它只做三件事：

1. append-only 修正/澄清 truth；
2. 用最小 code spike 证明 frozen graph law 在当前 engine 上可实现；
3. 把 spike 结果和本评审的 `T-R` 回灌 `planning-proposed`，重排 DAG/AP/规模/DoD。

### 6.2 start-gate 前置（进入 planning-proposed freeze 前必须满足）

| Gate | 必须提交的证据 | 失败时怎么处理 |
|---|---|---|
| `SG-0 Truth consistency` | 新 Truth/erratum 解决 two-phase S05；更正 7+6/13 基数；澄清 upload read、zero collection、semantic facet | 不得声称 QNA “无实际冲突” |
| `SG-1 Graph expressiveness` | 最小 immutable kind graph：一次 guarded reacquire、第二 decode、N clean 选一、single seal；compile/runtime/retry/recovery 全绿 | 若需大规模 engine 重写，owner 重评 Q4/Q7/Q8 bundle 或单列 engine campaign |
| `SG-2 Binding persistence` | forward migration + policy/actual binding columns/state + CAS seal + ProcessCommand 分账 + candidate/snapshot/gate proof | 禁止用 placeholder/hash-of-domain 冒充 actual S05 |
| `SG-3 Runtime feasibility` | 真实 PDF parser、真实 local browser content+PDF、真实 multimodal request/adapter 各一条 smoke；依赖、license、资源、readiness、安全边界记录 | 任一不可行就回 owner 调整 strategy/runtime，不以 503 收口 |
| `SG-4 Semantic authority` | 非 API 五维字段/派生/unknown policy、Revision write、S06 overlay、retrieval facet wire 设计 | 没有权威值来源则不得把 `T-O-389` 写成 NH4 中等工作项 |
| `SG-5 Upload law` | auth、stream budget、catalog orphan、same-byte replay、concurrent conflict、GC grace、public read 决定 | 不得只在 route 中直接调用 `promote` |
| `SG-6 Acceptance matrix` | 10 strategy + 3 API operation 的合法组合表，含输入 fixture、actual capability、expected terminal、semantic/facet、publication/retrieval、negative case | 不得用“10+3 全表”一句话代替分母 |
| `SG-7 Test baseline` | 修掉 source capability timeout；Turso harness 不再用 sqlite3 直读或明确隔离；相关 suite 可重复绿 | 不在红 baseline 上新增“闭集绿”声称 |

### 6.3 建议的 acceptance matrix 维度

每个格子至少记录：

```text
source_kind
× initial acquire edge
× observed representation facts
× optional declared reacquire path
× selected CleanStrategyKey + process_key
× prompt/adapter identity（仅 llm_required）
× admitted clean digest + actual s05 binding digest
× FilterMeta/ContextMeta revision semantics
× publication proof
× retrieval unique-hit + applicable semantic facet
× expected bad-input / replay / race disposition
```

禁止按 `4 source_kind × 10 strategy` 生造非法笛卡尔积；应由 `CLEAN_STRATEGY_DEFINITIONS.acquire_capabilities` 与 kind registry 生成合法格子（`src/contracts/intake/strategies.py:46-151`; `src/services/registry.py:171-208`）。

### 6.4 需 owner 拍板的问题

1. 是否接受新增两阶段 S05 binding Truth，并同步修订 S05/D04/glossary，而不是继续宣称现有和解已足够？
2. 若最小 spike 证明 one-of binding 需要扩展 Workflow 七表/DDL，是否授权 new-harvest 包含该 engine substrate；还是把它拆成前置 campaign？
3. 非 API 五维的权威输入是什么：ingest 必填 typed metadata、按 kind 的有限派生，还是二者合并？`unknown` 是否允许，何时属于假五维？
4. OCR/Vision/document-understanding 是否允许扩展 S11 为 multimodal generate request/adapter；若不允许，具体本地 runtime 属于哪个既有 pool？
5. `T-O-385` 的 public object surface 是 upload-only，还是还要求 authenticated read？若 upload-only，应修正 Q1 详述中的“上传/读取”。
6. exhaustion-proven empty API collection 是否接受当前“typed success、0 child、0 vector”法？建议接受，但必须明确它不违反“空 clean body 不成功”。

---

## 7. Spike / Test 水位评级

> 这里的 `D/W/E` 分别表示 deterministic contract、默认组合 wiring、end-to-end retrieval 证据；不是测试数量评分。

| Spike / 单元 | 当前结果 | D | W | E | 备注 |
|---|---|---|---|---|---|
| 选定 clean/provider unit + intake | `33 passed / 0 failed` | `high` | `low-med` | `low` | pure functions、strict provider、injected LLM 路径可信；不证明默认 runtime |
| registered API 三 operation e2e | `1 passed`（单独复跑，20.72s） | `high` | `high` | `med-high` | 三 provider map、语义、child publication-ready；测试未调用 retrieval query |
| source local/static/browser/pdf e2e | `failed`（单独复跑，22.08s） | `med` | `low` | `low` | 测试自身 monkeypatch browser；static Task 在 8s 窗仍 running（`test_source_capability_paths.py:99-101,157-218`） |
| 组合选择集 | `36 passed / 3 failed`（97.67s） | `med-high` | `low-med` | `low-med` | 两个 failure 是已知 sqlite3-on-Turso `disk I/O error`，另一个是 source timeout；闭集不能称绿 |
| graph late-bind/reacquire spike | `不存在` | `none` | `none` | `none` | 是 SG-1 阻断项 |
| upload public e2e | `不存在` | `kernel only` | `none` | `none` | CAS/GC 内核不能代替 public surface |
| semantic facet e2e | `不存在` | `API write only` | `none` | `none` | public filters 还不是 FilterMeta 五维 |

- **水位裁定**：`contract 高于 wiring，wiring 高于闭集证据`。API 是现成资产；single-source 四通道仍是合同/局部实现水位。initial 的 NH5 测试方向正确，但测试必须前移到每个 AP，且 source capability 的当前红灯应登记为 campaign 内 blocker，而非“最后再证明”。

---

## 8. 债务评分台账

| 编号 | 债务 | 内聚 | 紧急 | 复杂 | 风险 | 价值 | 建议顺序 |
|---|---|---|---|---|---|---|---|
| `DEBT-01` | two-stage S05 truth/schema/command/evidence | H | H | H | H | H | 1 |
| `DEBT-02` | guarded one-of binding 与 route fact authority | H | H | H | H | H | 1（并列） |
| `DEBT-03` | acquisition/decode evidence history + reacquire preflight | H | H | H | H | H | 2 |
| `DEBT-04` | multimodal/browser/PDF real adapter 与 readiness | M | H | H | H | H | 2（spike 并行） |
| `DEBT-05` | 五维 ingest authority→S06 overlay→retrieval facet | H | H | H | H | H | 2（合同并行） |
| `DEBT-06` | public upload catalog/orphan/GC race | H | M | M | H | H | 2（独立并行） |
| `DEBT-07` | 13 graph identity + compatibility migration 清册 | H | H | M | H | M | 3 |
| `DEBT-08` | promptA 三 identity 对齐 | H | H | M | H | H | 3 |
| `DEBT-09` | source e2e timeout / Turso harness | M | H | M | M | H | 3 |
| `DEBT-10` | exact acceptance matrix 与生命周期 applicability | H | M | M | M | H | 4 |

- **closure 判据 / DAG**：`DEBT-01+02` 先于 kind graph；`03+04+05+06` 可在接口冻结后并行；`07+08` 在 graph/capability rollout 前闭；`09` 必须在声称新 e2e 前闭；`10` 汇总所有 AP，不替代各 AP 自验。

---

## 附录

### A. 复现命令

```bash
# 模板、讨论与冻结真相
nl -ba .adocs/templates/eval-state-analysis.md
nl -ba docs/eval/new-harvest/initial-planning.md
nl -ba docs/eval/new-harvest/pre-initial-planning-qna.md

# 图数与不可选 identity：当前输出 13 / 7 / 6
uv run python - <<'PY'
from src.workflows.lsrag_definition import (
    BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW,
    BUILTIN_SOURCE_PROFILE_WORKFLOWS,
    SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS,
)
graphs = (BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW, *BUILTIN_SOURCE_PROFILE_WORKFLOWS)
public = set(SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS.values())
print(len(graphs), len(SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS), len([g for g in graphs if g.workflow_key not in public]))
for graph in graphs:
    if graph.workflow_key not in public:
        print(graph.workflow_key)
PY

# Workflow 表达力与 S05 digest
nl -ba src/contracts/workflow/models.py | sed -n '245,278p;373,443p;476,525p'
nl -ba src/runtime/workflow/runtime_materialize.py | sed -n '49,168p;505,514p'
rg -n "s05_binding_digest|domain_binding_digest" \
  src/persistence/migrations/001_initial.sql src/runtime/task src/runtime/workflow \
  src/runtime/intake src/services

# 当前 clean 与 legacy clean 对账
nl -ba src/contracts/intake/strategies.py | sed -n '15,164p'
nl -ba intake/__init__.py | sed -n '20,132p'
rg -n "action_branch|plainTextAvailable|empty_response|return null|payload_filter_meta" \
  context/legacy-family/smind-skill-clean-universal \
  context/legacy-family/smind-skill-clean-dedicated-apis \
  context/legacy-family/smind-clean-dispatcher

# public upload / semantic / retrieval 负证据
rg -n "@router\..*(upload|object)|multipart" api/public/routes.py
nl -ba src/contracts/storage/models.py | sed -n '16,29p'
nl -ba src/runtime/intake/acceptance_snapshot.py | sed -n '576,641p'
nl -ba src/runtime/intake/generation_construct.py | sed -n '329,343p'
nl -ba src/services/retrieval/models.py | sed -n '14,34p'

# 动态测试
uv run pytest \
  tests/unit/test_intake_provider_registry.py \
  tests/unit/test_intake_clean_dispatch.py \
  tests/intake/test_web_clean.py \
  tests/intake/test_pdf_clean.py \
  tests/intake/test_doc_clean.py

uv run pytest \
  tests/e2e/test_registered_api_scatter.py::test_registered_api_three_raw_provider_operations_map_seal_and_persist_semantics

uv run pytest \
  tests/e2e/test_source_capability_paths.py::test_local_static_browser_and_pdf_sources_produce_distinct_frozen_acquisition_evidence
```

### B. 关键 file:line 证据索引

| 结论 | file:line |
|---|---|
| profile graph 固定 acquire/decode/clean | `src/workflows/lsrag_definition.py:881-926` |
| 7 public + 6 unselectable；compat revisions | `src/workflows/lsrag_definition.py:929-940,1003-1080` |
| caller 不能点 workflow；按 profile 解析 | `src/services/workflow_registry.py:78-104`; `src/services/config_snapshots.py:492-516` |
| guard 闭集/缺表示事实 | `src/contracts/workflow/models.py:245-278`; `src/runtime/workflow/runtime_materialize.py:101-168` |
| one input / one binding | `src/contracts/workflow/models.py:482-525` |
| Execution s05 digest NOT NULL 且创建即写 | `src/persistence/migrations/001_initial.sql:225-250`; `src/runtime/task/task_create.py:167-181,337-368` |
| ProcessCommand 仍用 domain binding | `src/runtime/workflow/runtime_core.py:888-915` |
| PDF literal placeholder | `src/runtime/intake/types.py:144-171` |
| browser/print/opaque doc 表示缺口 | `src/runtime/intake/acquisition_ingest.py:474-594` |
| default root 未注入 browser/clean multimodal | `api/app.py:332-345` |
| text-only inference/CLI | `src/contracts/inference/models.py:96-118`; `src/runtime/inference/claude_cli.py:490-519` |
| non-API semantic stub | `src/runtime/intake/acceptance_snapshot.py:576-615` |
| g0=clean 已实现 | `src/runtime/intake/generation_assemble.py:17-62` |
| S06 不读 revision semantics | `src/runtime/intake/generation_construct.py:329-343,1092-1229` |
| retrieval filters 非 FilterMeta 五维 | `src/services/retrieval/models.py:14-34`; `src/services/retrieval/retrieval_request.py:324-361` |
| upload route/purpose 缺失 | `api/public/routes.py:29-469`; `src/contracts/storage/models.py:16-29` |
| API 三 operation 已写语义并 publication-ready | `tests/e2e/test_registered_api_scatter.py:209-321` |
| current source e2e monkeypatch 与红灯 | `tests/e2e/test_source_capability_paths.py:71-218`; `README.md:606-615` |

### C. 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|---|---|---|---|
| v0.1 | 2026-08-29 | GPT | initial/QNA/HEAD/legacy clean 全量对账；给出 truth 修正、簇/DAG/AP 调整、start-gate 与测试证据 |
