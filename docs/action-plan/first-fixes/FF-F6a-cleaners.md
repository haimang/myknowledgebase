# Nano-Agent 行动计划模板

> 服务业务簇: `first-fixes · F6 执行器去桩与能力补全（clean 部分）`
> 计划对象: `FF-F6a · Clean 执行器去桩（action registry 分派 + universal htmlCrawl 真实抓取清洗 + dedicated chinatax 真实 ETL；PDF/浏览器/多 provider/scatter 显式 degraded）`
> 类型: `refactor`（去桩重建：registry 替换 if/else 硬选 + 桩→真实实现，遵守 F3-02 执行器契约）
> 作者: `Opus 4.8`
> 时间: `2026-05-31`
> 文件位置: `packages/cleaners_universal/src/cleaners_universal/service.py` / `packages/providers_dedicated/src/providers_dedicated/service.py` / `packages/browser_runtime/src/browser_runtime/extract.py` / `packages/workflow_clean/src/workflow_clean/service.py`（+ 新建 action registry / provider registry 模块）
> 上游前序 / closure:
> - `FF-F1-time-tx-base.md`（时间与事务基座 keystone：clean 产物/事件时间走单一 SSOT；F1-04 autocommit + 多写 helper 包 BEGIN IMMEDIATE）
> - `FF-F2-conn-wiring.md`（连接与装配；不直接依赖产物，但 clean 执行器异常映射须与 F2 异常处理一致）
> - `FF-F3-kernel-recovery.md`（**F3-02 执行器契约 `execute(step,deps)->ExecutorResult` 是本 AP 全部去桩执行器的建造基准**；F3-03 确定性幂等键；clean 执行器不得自写终态/不 commit）
> - `FF-F4-adapter-safety.md` / `FF-F5-vector-authenticity.md`（F6 整簇依赖 F1–F5 substrate；本 AP 直接消费 F4 ObjectStore 边界与 F3-02 契约）
> 下游交接:
> - `FF-F6b-rag-executors.md`（rag 侧去桩 structurize/construct/vectorize；与本 AP 同属 F6，共用 F3-02 契约与 action registry 模式）
> - `FF-F6c-auth-config.md`（认证与 prompt_versions/provider_configs 配置载体；本 AP chinatax provider 的配置读取在 F6c 接线，本轮先用内置 registry 默认）
> - `FF-F7-test-integrity.md`（F7 端到端 capstone 消费本 AP 的真实 htmlCrawl/chinatax 链路；PDF/浏览器步骤标 xfail）
> 关联设计 / 调研文档:
> - `docs/design/first-fixes/initial-planning-by-opus.md`（§6.6 F6 [final] 绑定表 F6-01/02/03/08、§2.C [Q3] 定档、§4 红线第 2 条执行器契约、§5 DAG、§8 capstone B/C 步 + DoD、§10.A 派生图）
> - `docs/eval/first-code-review-plan/part-cr-6.md`（G-CR6-01 universal 全桩 / 02 dedicated 硬编码 chinatax / 04 action registry 丢失 / 09 scatter 缺，含 file:line + legacy ~10.6k 行对照）、`part-cr-4.md`（G-CR4-03 执行器自提交，clean 侧落点 R3）
> 冻结决策来源:
> - `docs/design/first-fixes/owner-gated-qna.md`（只读引用；本 action-plan 不填写 Q/A —— 仅引 [Q3] 去桩增量范围、[Q7] 先红后绿铁律）
> grounding 来源:
> - `eval-reference-anchor: docs/eval/first-code-review-plan/part-cr-6.md（R1/R2/R3/R4/R9，含主审实测 + 逐 action parity 矩阵 + legacy ~10.6k 行对照）+ part-cr-4.md（R3 clean 侧）`；§7 内置锚区据此摘录
> 关联 reference-anchor:
> - `见 §7 内置锚区（摘录自 part-cr-6 / part-cr-4；完整借鉴台账见真源 §7.3 指针）`
> 文档状态: `draft`

---

## 0. 执行背景与目标

> 用一到三段话说明：为什么现在要执行这份计划、它从哪些 frozen design / QNA / closure 继承输入、它要把哪些设计结论落成可交付物。
>
> **纪律**：如果仍有 owner / architect 需要回答的问题，不应在 action-plan 中开 Q/A；应回到 design / qna register 完成冻结。本文件只消费已冻结结论。

CR-6 审查确认 clean 流水线是"能让 step 链流过、但几乎不含真实 clean 能力"的占位实现（part-cr-6.md §0）：三个执行器包合计 31 行真实算法，legacy ~10.6k 行 clean 能力在 Python 侧迁移量近乎为零——`cleaners_universal` 对 url/api 只做 3 条正则去标签且**无真实抓取**（url 抓取藏在 `_load_raw_payload` 的裸 `urlopen` 里、无 User-Agent/重试/状态码校验、失败把 URL 字符串当正文），`providers_dedicated` 仅当 URI 含 `chinatax.gov.cn` 时给 payload 加 `[provider:chinatax]` 字符串前缀、**完全不发请求**，整个 action registry / `action_branch` 概念在创建侧与执行侧都不存在（`process_clean_step` 用一条 `provider or universal` 的 if/else 硬选）。这些是 owner 预判的"stub 即盲点 B"重灾区（G-CR6-01/02/04），且 clean 侧承接了 G-CR4-03 执行器自提交竞态。

本 AP 是 final plan（`initial-planning-by-opus.md`）§6.6 F6 簇按规模拆出的 clean 部分（§10.A 派生图 `FF-F6a-cleaners.md`，台账区间 F6-01/02/03/08），由冻结 QnA **[Q3] 定档为增量范围**：本轮只做 `htmlCrawl`（url HTML 抓取+清洗）+ `chinatax` 真实 ETL + action registry 分派；PDF/浏览器渲染/多 provider/scatter 一律**显式 degraded**（degraded 声明 + 测试 skip/xfail + 不留装成完成的桩）。它消费 §4 红线第 2 条"终态写入单一归属 + 执行器契约"——本 AP 全部去桩执行器必须建在 F3-02 交付的 `execute(step, deps) -> ExecutorResult` 契约上（只产结果、不写终态、不 commit），否则会逐个复刻 G-CR4-03 的职责撕裂。每个去桩项以 [Q7] 先红后绿铁律为退出证据（喂真实 HTML 样本断言去标签保正文，当前桩只 strip→红）。

- **服务业务簇**：`first-fixes · F6 执行器去桩与能力补全（clean 部分）`
- **计划对象**：`action registry + executor 分派抽象 + universal htmlCrawl 真实抓取清洗 + dedicated chinatax 真实 ETL；browserFetch/browserPDF/多 provider/scatter 显式 degraded`
- **本次计划解决的问题**：
  - `G-CR6-04 action registry 丢失：clean 服务用 if/else 硬选执行器，workflow_steps.action_branch 在创建侧从不写入，无法表达"用哪个 action"、无 list_actions 能力发现`
  - `G-CR6-01 universal cleaner 全桩：9 个 legacy action 真实现 0/7，url 抓取无真实 fetch（无 UA/重试/状态码校验，失败回退把 URL 当正文）、清洗仅 3 条正则`
  - `G-CR6-02 dedicated provider 硬编码 chinatax：仅加字符串前缀、不发请求、无 parse/hash/child files，domain/realestate 不存在`
  - `G-CR4-03（clean 侧 R3）执行器自提交 succeeded + 无幂等键：service.py:117-129 在 succeed_claim 前自置终态并 commit，过期租约竞态下重复落盘 artifact + 重复 rag step`
- **本次计划的直接产出**：
  - `action registry 模块（dict[branch]→handler）+ 分派抽象，替换 process_clean_step 的 if/else 硬选；执行器遵守 F3-02 ExecutorResult 契约（只产结果、不写终态/不 commit）`
  - `cleaners_universal.htmlCrawl：真实 HTTP 抓取（UA/超时/状态码校验/错误分类）+ 健壮 HTML→text 去标签保正文，替换正则桩；browserFetch/browserPDF 显式 degraded（声明 + xfail）`
  - `providers_dedicated provider registry + chinatax 真实 ETL（真发请求 → 解析 → 产 ExecutorResult artifacts）；domain/realestate 留接口显式 degraded`
  - `finalizer scatter/child files（多文档源）显式 degraded（[Q3] 本轮不支持，degraded 声明 + 单文档源正常）`
- **本计划不重新讨论的设计结论**：
  - `去桩范围=增量：file+url(htmlCrawl)+chinatax+registry；PDF/浏览器/多 provider/scatter 显式 degraded`（来源：`[Q3]`）
  - `执行器契约 execute(step,deps)->ExecutorResult，执行器不写终态/不 commit`（来源：`initial-planning-by-opus.md §4 红线第 2 条 / F3-02`）
  - `每个 blocker 修复以先红后绿回归测试为退出证据`（来源：`[Q7]`）

---

## 1. 执行综述

### 1.1 总体执行方式

本 AP 采用 **「先协议后实现、先骨架后能力、先声明降级后真实现」** 的执行方式，分 3 个 Phase：先在 F3-02 契约基座上建 action registry + 分派抽象（Phase 1，把 if/else 硬选换成可注册分派，并把 clean 执行器迁到 ExecutorResult 契约、去自提交），让"用哪个 action"可表达、终态归属正确；再做承重的两个净新高风险去桩——universal `htmlCrawl` 真实抓取清洗 + dedicated `chinatax` 真实 ETL（Phase 2，[Q3] 增量核心）；最后把 [Q3] 明确不支持的 browserFetch/browserPDF/多 provider/scatter 落成**显式 degraded**（Phase 3，degraded 声明 + skip/xfail + 不留装成完成的桩）。每个 Phase 的退出判据是「先红后绿」的有意义测试（喂真实样本断言语义），而非桩恒等输出。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | action registry + 分派抽象（迁 F3-02 契约） | M | 建 registry（branch→handler）替换 if/else 硬选；clean 执行器迁 ExecutorResult、去自提交（承接 G-CR4-03 clean 侧） | F3-02 契约（必须先到位） |
| Phase 2 | universal htmlCrawl + dedicated chinatax 真实去桩 | L | htmlCrawl 真抓取清洗（去标签保正文/错误超时）；chinatax provider registry + 真实 ETL（真发请求/解析） | Phase 1；F4 ObjectStore |
| Phase 3 | 显式 degraded（PDF/浏览器/多 provider/scatter） | S | browserFetch/browserPDF/domain/realestate/scatter 显式 degraded 声明 + skip/xfail + 留可扩展接口 | Phase 1/2 |

> 说明：上表 `规模` 是每个 Phase 的**描述性提示**（帮助阅读，工作量小则该 Phase 自然简短），**不是开工前的体量判定闸，也不改变本模板任何段落的取舍**。本模板是单一模板，不分 flavor、不分档。

### 1.3 Phase 说明

1. **Phase 1 — action registry + 分派抽象（迁 F3-02 契约）**
   - **核心目标**：用 registry（`dict[branch] → handler`）替换 `process_clean_step` 的 `provider or universal` if/else 硬选（G-CR6-04）；创建侧写入 `action_branch`、执行侧据此选 handler；同时把 clean 执行器迁到 F3-02 `ExecutorResult` 契约——删除自提交终态/自插下游 rag step/`conn.commit()`（G-CR4-03 clean 侧 R3）。
   - **为什么先做**：registry 是 Phase 2 真实 handler（htmlCrawl/chinatax）的挂载点；契约迁移是去桩的前提（去桩后的执行器必须遵守"只产结果"，否则每个新 handler 都会复刻自提交竞态）。先把骨架与契约立稳，Phase 2 才能把真实能力安全挂上去。
2. **Phase 2 — universal htmlCrawl + dedicated chinatax 真实去桩**
   - **核心目标**：把 [Q3] 增量范围的两个真实能力落地——`htmlCrawl`（真实 HTTP 抓取 + 健壮 HTML→text 去标签保正文 + 错误/超时分类）、`chinatax` provider（真发请求 → 解析 → 产 ExecutorResult artifacts）。这是本 AP 的承重交付。
   - **为什么放在这里**：依赖 Phase 1 的 registry 挂载点与 ExecutorResult 契约；真实能力一旦挂上即可被 F7 端到端 capstone 的 B/C 步消费。
3. **Phase 3 — 显式 degraded（PDF/浏览器/多 provider/scatter）**
   - **核心目标**：把 [Q3] 明确不支持的 browserFetch/browserPDF（universal）、domain/realestate（dedicated 多 provider）、finalizer scatter/child files 落成**显式 degraded**：注册为 degraded handler（调用即抛带 `reason` 的 `DegradedActionError`）、测试 skip/xfail 标注、SSOT 记账，**不留装成完成的桩**。
   - **为什么放在这里**：在 registry 与真实 handler 稳固后，统一把"不支持"显式钉死，避免再被误判为已实现（CR-6 R1/R2/R9 的盲点 B 反例）。

### 1.4 执行策略说明

> **纪律**：本节写执行策略，**不重述 §6 已引用的冻结决策的理由**（避免与 design/qna 重复，只写"怎么执行"，不写"为什么这么设计"）。

- **执行顺序原则**：registry+契约骨架（Phase 1）→ 真实能力（Phase 2）→ 显式降级（Phase 3）；先把"能挂、不自提交"立稳，再挂真实 handler，最后钉死不支持项。
- **风险控制原则**：净新高风险项（htmlCrawl/chinatax）拆有序子步，每子步配独立先红后绿测试；真实网络调用在测试中用本地 HTTP fixture / mock 注入（显式标注非交付），不依赖外网；执行器一律不写 core 终态/不 commit（grep gate 守护）。
- **测试推进原则**：短途（registry 分派单测 + htmlCrawl 去标签保正文单测）随 PR；spike（chinatax 集成、可 mock 网络）每 Phase 收口；端到端 clean→rag→search 语义归 F7 capstone（本 AP 提供真实 HTML/chinatax 样本与 xfail 标注）。详见 §8。
- **文档同步原则**：degraded 项在 SSOT（本 AP §2.2 + 设计 doc）显式声明清单；action registry 的 list_actions 自描述供后续管理面。
- **回滚 / 降级原则**：若 F3-02 契约未就绪，Phase 1 的 registry 可先落地、契约迁移分两批；htmlCrawl 抓取失败按错误分类抛可重试/不可重试异常交内核 fail_claim；browserFetch/browserPDF/多 provider/scatter 全程 degraded（不回退到"装成完成的桩"）。

### 1.5 本次 action-plan 影响结构图

```text
FF-F6a · Clean 执行器去桩
├── Phase 1: action registry + 分派抽象（迁 F3-02 契约）
│   ├── packages/workflow_clean/.../action_registry.py（🆕 dict[branch]→handler + list_actions）
│   ├── packages/workflow_clean/.../service.py:67-129（去 if/else 硬选；去自提交；返回 ExecutorResult）
│   └── packages/ingestion/.../service.py:204-216（创建侧写入 action_branch）
├── Phase 2: universal htmlCrawl + dedicated chinatax 真实去桩
│   ├── packages/cleaners_universal/.../service.py（♻️ 重建：htmlCrawl 真抓取清洗）
│   ├── packages/browser_runtime/.../extract.py:6-12（♻️ 重建：健壮 HTML→text 去标签保正文）
│   └── packages/providers_dedicated/.../service.py（♻️ 重建：provider registry + chinatax 真 ETL）
└── Phase 3: 显式 degraded
    ├── cleaners_universal: browserFetch/browserPDF → DegradedActionError（声明 + xfail）
    ├── providers_dedicated: domain/realestate → degraded 接口（声明 + skip）
    └── workflow_clean: finalizer scatter/child files → degraded（单文档源正常）
```

---

## 2. In-Scope / Out-of-Scope

> 把 action-plan 的执行边界集中写在这里。设计上的边界应来自 design/QNA；本节只说明本轮执行做什么、不做什么、何时重评。

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** action registry（`dict[branch] → handler`）+ executor 分派抽象，替换 `process_clean_step` 的 `provider or universal` if/else 硬选；创建侧（ingestion）写入 `action_branch`，执行侧据此选 handler；补 `list_actions` 能力发现（G-CR6-04 / F6-01）。
- **[S2]** clean 执行器迁 F3-02 `ExecutorResult` 契约：删除自提交终态（`status='succeeded'`）、自插下游 rag step（uuid4 key）、`UPDATE workflow_runs`、`conn.commit()`，改为返回 `ExecutorResult`（G-CR4-03 clean 侧 R3）。
- **[S3]** universal `htmlCrawl` 真实实现：HTTP 抓取（User-Agent / 超时 / 状态码校验 / 错误分类）+ 健壮 HTML→text（去标签保正文，非 3 条正则）（G-CR6-01 / F6-02）。
- **[S4]** dedicated provider registry + `chinatax` 真实 ETL（真发请求 → 解析 → 产 ExecutorResult artifacts），registry 可扩展（G-CR6-02 / F6-03）。

### 2.2 Out-of-Scope（本次 action-plan 明确不做 —— 显式 degraded，[Q3] 定档）

> 横切纪律（[Q3]）：凡"不支持"必须 ① 显式 degraded 声明 ② 测试 `skip`/`xfail` 明确标注 ③ **不得留装成完成的桩**（桩=看起来完成实则空，degraded=显式抛错+记账）。

- **[O1]** universal `browserFetch` / `browserFetch-geminiClean` / `browserPDF` / `browserPDF-geminiClean` / `geminiUnderstanding`（浏览器渲染 + PDF Vision + LLM 清洗）—— **显式 degraded**：注册为 degraded handler，调用即抛 `DegradedActionError(reason="browser/PDF/LLM not supported this round")`；测试 `xfail`。
- **[O2]** dedicated 多 provider（`domain` / `realestate`）—— **显式 degraded**：registry 留接口但 handler 抛 `DegradedActionError`；测试 `skip`。
- **[O3]** finalizer scatter / child files / differ（多文档源散射 + content_hash/meta_hash 差分）—— **显式 degraded**（[Q3] 本轮不支持多文档源）：单文档源标准交接正常，多文档源（child_files>0）抛 `DegradedActionError`；测试 `skip`。
- **[O4]** cleaned_text 落 ObjectStore（CR-6 R5，正文内联 sqlite_ref→对象存储）—— **延后**（non-blocking，与 F4 路径安全协调）；本 AP 保持现状 sqlite_ref，不在本轮改存储模型。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| action registry + 分派 + ExecutorResult 迁移 | `in-scope` | G-CR6-04 high blocker；真实 handler 挂载点；契约是去桩前提 | — |
| universal htmlCrawl 真抓取清洗 | `in-scope` | [Q3] 增量核心（url 源语义闭环）；G-CR6-01 critical | — |
| dedicated chinatax 真实 ETL | `in-scope` | [Q3] 增量核心（1 provider 样板）；G-CR6-02 critical | — |
| browserFetch/browserPDF/geminiUnderstanding | `out-of-scope（degraded）` | [Q3] 显式不支持（浏览器/PDF/LLM 重依赖） | 下一轮接 playwright/PDF 库/LLM |
| domain/realestate 多 provider | `out-of-scope（degraded）` | [Q3] 显式不支持（多 provider 各自重依赖） | 产品需要时按 registry 扩展 |
| finalizer scatter/child files | `out-of-scope（degraded）` | [Q3] 本轮不支持多文档源 | chinatax 等需散射多文档时 |
| cleaned_text 落 ObjectStore | `defer` | CR-6 R5 non-blocking；与 F4 协调 | F4 路径安全收口后 |

---

## 3. 业务工作总表

> 总索引；后面 §4 会按 Phase 展开。
>
> **硬地板（每个工作项必须三件齐全 —— 不可约三元组）**：`涉及文件（file:line 级）` + `收口目标` + `测试映射（Test-ID）`。**净新 / 高风险**工作项的 `工作内容` 在 §4 拆有序子步、§5 `具体功能预期` ≥5 条。

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| F6-01 | Phase 1 | action registry（branch→handler）+ 分派抽象 + 创建侧写 action_branch + list_actions | add + refactor | `workflow_clean/.../action_registry.py`（🆕）；`workflow_clean/service.py:80-82`（去 if/else 硬选）；`ingestion/service.py:204-216`（写 action_branch） | registry 可注册/分派；无 `provider or universal` if/else 硬选；创建侧写 action_branch；list_actions 可枚举 | `FF-F6a-T01` `FF-F6a-T02` | high |
| F6-01b | Phase 1 | clean 执行器迁 F3-02 ExecutorResult 契约（去自提交 / 去自插下游 / 去 commit） | refactor | `workflow_clean/service.py:101-129`（删自插 rag step + UPDATE step/run + commit） | 执行器只产 ExecutorResult；clean service 内 0 个 `status='succeeded'`/`conn.commit()`/`CURRENT_TIMESTAMP`（core 侧） | `FF-F6a-T03` | high |
| F6-02 | Phase 2 | universal htmlCrawl 真实抓取清洗（去标签保正文 / 错误超时分类） | refactor（桩→真实） | `cleaners_universal/service.py:6-9`（重建）；`browser_runtime/extract.py:6-12`（健壮 HTML→text） | url 源→干净正文（去标签/保正文）；抓取有 UA/超时/状态码校验/错误分类；browser/PDF degraded | `FF-F6a-T04` `FF-F6a-T05` `FF-F6a-T06` | high |
| F6-03 | Phase 2 | dedicated provider registry + chinatax 真实 ETL（真发请求/解析→ExecutorResult） | refactor（桩→真实） | `providers_dedicated/service.py:4-8`（重建为 registry + chinatax handler） | chinatax 真发请求 + 解析 + 产 artifacts；registry 可扩展；不发请求的字符串前缀桩删除 | `FF-F6a-T07` `FF-F6a-T08` | high |
| F6-08 | Phase 3 | finalizer scatter/child files（多文档源）显式 degraded | add（degraded 声明） | `workflow_clean/service.py:101-116`（多文档源分支抛 DegradedActionError） | 单文档源正常；多文档源（child_files>0）显式 degraded；不留装成完成的桩 | `FF-F6a-T09` | medium |
| F6a-DG | Phase 3 | browserFetch/browserPDF/domain/realestate 显式 degraded（注册 degraded handler） | add（degraded 声明） | `cleaners_universal/.../action_registry.py`（degraded 项）；`providers_dedicated/service.py`（domain/realestate） | 调用 degraded action 抛带 reason 的 DegradedActionError；测试 xfail/skip | `FF-F6a-T10` | low |

---

## 4. Phase 业务表格

> 每个 Phase 一张表，`测试映射` 列指向 §8 的 `Test-ID`。**`工作内容` 是承重列，分解度与净新度/风险成正比（硬地板第 4 件）**。

### 4.1 Phase 1 — action registry + 分派抽象（迁 F3-02 契约）

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| F6-01 | action registry + 分派 | **有序子步（净新高风险）：** **a)** 新建 `workflow_clean/action_registry.py`：`CleanActionRegistry` 持 `dict[branch_name, handler]`，`register(branch, handler)` / `get_handler(branch) -> handler`（未知 branch 抛 `UnknownActionError`，对齐 legacy `UNKNOWN_CLEANER_BRANCH`）/ `list_actions() -> list[ActionSpec]`（含 branch 名 + 是否 degraded，供能力发现）。**b)** handler 签名遵守 F3-02：`handle(step, deps) -> ExecutorResult`（`deps` 封 object_store/app_env，不含写 core 终态权限）。**c)** 创建侧（`ingestion/service.py:204-216`）建 clean step 时按 source_kind/source_uri 决定 `action_branch`（file→`htmlCrawl`-class text、url→`htmlCrawl`、chinatax host→`fetch-chinatax-articles`）并写入 `workflow_steps.action_branch`（payload_json 承载，schema 无该列时落 payload_json）。**d)** `process_clean_step`（`service.py:80-82`）改为读 step 的 action_branch → `registry.get_handler(branch)` → `handler.handle(step, deps)`，**删除** `provider_cleaned or clean_payload(...)` 的 if/else 硬选。**e)** 边界：action_branch 缺失时回退默认 branch（file 文本）并记 warning；未知 branch 抛 UnknownActionError 交 fail_claim（不可重试）。**f)** 注册表初始化集中在一处（universal + dedicated handler 在此挂载，Phase 2 填真实现）。 | `workflow_clean/action_registry.py`（🆕）；`workflow_clean/service.py:80-82`；`ingestion/service.py:204-216` | registry 分派工作；无 if/else 硬选；action_branch 写入 + 可枚举 | `FF-F6a-T01` `FF-F6a-T02` | registry 注册/分派单测过；grep 确认 service 无 `or clean_payload` 硬选；list_actions 枚举含 degraded 标记 |
| F6-01b | clean 执行器迁 ExecutorResult 契约 | **有序子步（高风险）：** **a)** `process_clean_step`（`service.py:67-129`）保留 `_load_raw_payload` + 经 registry 选 handler 产 cleaned 正文。**b)** **删除** `:101-116`（自插下游 rag step，uuid4 key）`:117-120`（UPDATE step succeeded + CURRENT_TIMESTAMP）`:121-128`（UPDATE run running/rag）`:129`（`conn.commit()`）。**c)** 改为返回 `ExecutorResult(artifacts=[cleaned_text artifact spec], downstream=[rag:structurize step spec], run_advance=(running, rag))`；下游 step_key 改确定性（`rag-struct:{clean_step_id}`，依赖 F3-03）。**d)** 边界/失败：handler 抛异常时执行器**不得有任何 core 副作用残留**（无自 commit）；终态/下游/run/commit 全交 F3-02 的 `succeed_claim(..., result=)`。**e)** 降级：若 F3-02 `succeed_claim` 扩参未就绪，本项 blocked 回退 F3（不保留自 commit 折中）。 | `workflow_clean/service.py:67-129`（删 :101-129 自提交段） | 执行器只产 ExecutorResult；0 自提交/自 commit | `FF-F6a-T03` | grep 确认 clean service 内 0 个 `status='succeeded'`/`conn.commit()`/`CURRENT_TIMESTAMP`（core 侧）；返回 ExecutorResult 被 worker 消费 |

### 4.2 Phase 2 — universal htmlCrawl + dedicated chinatax 真实去桩【承重】

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| F6-02 | universal htmlCrawl 真实抓取清洗 | **有序子步（净新高风险）：** **a) 抓取**：`cleaners_universal` 新增 `html_crawl(url, deps) -> str`：用 `urllib`/`httpx` 发 GET，带 `User-Agent: SourceMindBot/...`（对齐 legacy `cleaner_web.ts:67`）、超时（如 10s）。**b) 状态码校验**：非 2xx 抛 `UrlFetchError`（对齐 legacy `URL_FETCH_FAILED`，可重试分类）；连接/超时异常归 `UrlFetchError`。**c) 去标签**：解析 HTML（优先用 stdlib `html.parser` 或轻量解析器，去 `<script>`/`<style>`/注释/导航噪声），**保正文**（提取可见文本块、保段落换行），替换 `browser_runtime/extract.py` 的 3 条正则（正则桩对嵌套/属性/实体处理脆弱）。**d) 保正文断言面**：去标签后正文非空、不含残留标签、保留段落结构（供 T04/T05 断言）。**e) 错误/超时**：抓取失败按错误分类抛（不回退把 URL 当正文——删除现 `_load_raw_payload:48-49` 的 `return source_uri` 兜底，改为抛分类异常交内核）。**f) registry 挂载**：注册为 `htmlCrawl` branch handler，遵守 ExecutorResult 契约。**g) browser/PDF degraded**：`browserFetch`/`browserPDF`/`geminiUnderstanding` 注册为 degraded handler（抛 DegradedActionError），见 Phase 3。 | `cleaners_universal/service.py:6-9`（重建）；`browser_runtime/extract.py:6-12`（健壮 HTML→text）；`workflow_clean/service.py:41-49`（url 抓取移到 htmlCrawl handler，删裸 urlopen 兜底） | url→去标签保正文的干净正文；抓取有 UA/超时/状态码/错误分类；browser/PDF degraded | `FF-F6a-T04` `FF-F6a-T05` `FF-F6a-T06` | 喂真实 HTML 样本断言去标签保正文（现桩只 strip→红，修复→绿）；超时/4xx 抛分类异常；PDF 样本 xfail |
| F6-03 | dedicated provider registry + chinatax 真实 ETL | **有序子步（净新高风险）：** **a) registry 注册**：`providers_dedicated` 新建 `ProviderRegistry`（host/branch → provider handler）；注册 `chinatax`（host `chinatax.gov.cn` / branch `fetch-chinatax-articles`），删除现 `service.py:4-8` 的"加字符串前缀不发请求"桩。**b) 真实请求**：chinatax handler 发实际 HTTP 请求拉取数据（对齐 legacy `chinatax/processor.ts:103-127` fetcher），带超时 + 非 2xx 抛 `ApiRequestError`（对齐 legacy `API_REQUEST_FAILED`）。**c) 解析**：解析响应（JSON/HTML）→结构化 items（title/description/publisher/publish_date 等，对齐 legacy parser `:170-180`）；解析失败按条跳过 + warning（不整体崩）。**d) 产 ExecutorResult**：把解析结果组装为 cleaned 正文 / artifact spec，返回 ExecutorResult（**多 item 散射成多文档源属 scatter，本轮 degraded——见 F6-08**：本轮 chinatax 解析结果合并为单 artifact，多 child files 散射显式 degraded）。**e) 错误/超时**：网络失败抛 ApiRequestError（可重试）；解析空结果记 warning（对齐 legacy `:140` ALERT）。**f) 多 provider degraded**：domain/realestate 注册 degraded handler，见 Phase 3。 | `providers_dedicated/service.py:4-8`（重建为 registry + chinatax handler） | chinatax 真发请求 + 解析 + 产 artifacts；registry 可扩展；不发请求的桩删除；domain/realestate degraded | `FF-F6a-T07` `FF-F6a-T08` | chinatax 集成测试（mock 网络注入真实响应样本）断言真发请求 + 解析出结构化 items；无 `[provider:chinatax]` 字符串前缀残留 |

### 4.3 Phase 3 — 显式 degraded（PDF/浏览器/多 provider/scatter）

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| F6-08 | finalizer scatter/child files 显式 degraded | **枚举（degraded 声明）：** 单文档源标准交接（建一条 rag step）保持正常；当 provider/clean 产出 child_files>0（多文档源散射需求）时，抛 `DegradedActionError(reason="scatter/multi-document not supported this round")`，不静默吞、不留装成完成的桩；SSOT 记账多文档源本轮不支持。 | `workflow_clean/service.py:101-116`（多文档源分支） | 单文档源正常；多文档源显式 degraded | `FF-F6a-T09` | 单文档源建 1 rag step；多文档源输入触发 DegradedActionError（测试断言抛错带 reason） |
| F6a-DG | browser/PDF/多 provider degraded handler | **枚举（degraded 声明）：** registry 中 `browserFetch`/`browserFetch-geminiClean`/`browserPDF`/`browserPDF-geminiClean`/`geminiUnderstanding`（universal）与 `domain`/`realestate`（dedicated）注册为 degraded handler：`handle` 即抛 `DegradedActionError(reason=...)`；`list_actions` 标记 `degraded=True`；测试用 `xfail`(browser/PDF)/`skip`(多 provider) 标注；不留任何"看起来能跑实则空"的桩。 | `cleaners_universal/.../action_registry.py`（degraded 注册）；`providers_dedicated/service.py`（domain/realestate） | degraded action 抛带 reason 的错误；list_actions 标 degraded；测试 xfail/skip | `FF-F6a-T10` | 调用任一 degraded action 抛 DegradedActionError；list_actions 含 degraded 标记；grep 确认无装成完成的桩 |

---

## 5. Phase 详情

> 按 Phase 展开详细执行说明。**测试不在此展开**——每项指向 §8 测试台账的 `Test-ID`。净新 / 高风险 Phase `具体功能预期` ≥5 条，含边界与失败/降级路径。

### 5.1 Phase 1 — action registry + 分派抽象（迁 F3-02 契约）

- **Phase 目标**：用可注册 registry 替换 if/else 硬选（G-CR6-04），创建侧写 action_branch、执行侧据此分派；clean 执行器迁 F3-02 ExecutorResult 契约、去自提交（G-CR4-03 clean 侧）。
- **本 Phase 对应编号**：`F6-01` / `F6-01b`
- **本 Phase 新增文件**：`packages/workflow_clean/src/workflow_clean/action_registry.py`（🆕 `CleanActionRegistry` + `ActionSpec` + `UnknownActionError` + `DegradedActionError`）
- **本 Phase 修改文件**：`workflow_clean/service.py:80-82`（去 if/else 硬选）、`:101-129`（去自提交段，迁 ExecutorResult）；`ingestion/service.py:204-216`（写 action_branch）
- **本 Phase 删除文件**：无（删除的是 service.py 内自提交代码段，非文件）
- **具体功能预期**：
  1. `CleanActionRegistry.register/get_handler/list_actions` 工作；未知 branch 抛 `UnknownActionError`（不可重试），不再用 `provider or universal` 硬选。
  2. 创建侧（ingestion）按 source_kind/host 决定并写入 `action_branch`（url→htmlCrawl、chinatax host→fetch-chinatax-articles、file→文本 branch）。
  3. handler 签名遵守 F3-02 `handle(step, deps) -> ExecutorResult`，`deps` 不持有写 core 终态权限。
  4. clean 执行器删除 `status='succeeded'`/`UPDATE workflow_runs`/自插 rag step/`conn.commit()`，改返回 `ExecutorResult`；下游 step_key 确定性（`rag-struct:{clean_step_id}`）。
  5. **边界**：action_branch 缺失回退默认 + warning；未知 branch fail_claim 不可重试；handler 抛异常时执行器无 core 副作用残留（无自 commit）。
  6. **降级路径**：F3-02 `succeed_claim(result=)` 未就绪时本项 blocked 回退 F3，**禁止保留自 commit 折中**。
- **对应测试台账项**：`FF-F6a-T01` / `FF-F6a-T02` / `FF-F6a-T03`（详见 §8）
- **收口标准**：registry 分派单测过；grep 确认 service 无 `or clean_payload` 硬选 + 0 自提交/commit；ExecutorResult 被 worker 消费。
- **本 Phase 风险提醒**：迁契约触碰与 F3-02/F1-04 同一批多写路径——须确认 F3-02 `succeed_claim` 扩参已就绪再迁；schema 无 `action_branch` 列时用 payload_json 承载（不擅自改 schema）。

### 5.2 Phase 2 — universal htmlCrawl + dedicated chinatax 真实去桩【承重】

- **Phase 目标**：落地 [Q3] 增量两个真实能力——htmlCrawl 真抓取清洗（去标签保正文）+ chinatax 真实 ETL（真发请求/解析）。
- **本 Phase 对应编号**：`F6-02` / `F6-03`
- **本 Phase 新增 / 修改 / 删除文件**：`cleaners_universal/service.py:6-9`（重建 htmlCrawl）；`browser_runtime/extract.py:6-12`（健壮 HTML→text 替换 3 正则）；`providers_dedicated/service.py:4-8`（重建 provider registry + chinatax ETL，删字符串前缀桩）；`workflow_clean/service.py:41-49`（url 抓取移入 htmlCrawl handler，删裸 urlopen 兜底）
- **具体功能预期**：
  1. `htmlCrawl` 发真实 GET（User-Agent + 超时），非 2xx / 连接超时抛 `UrlFetchError`（可重试分类），**不回退把 URL 字符串当正文**。
  2. HTML→text 去 `<script>/<style>/注释/标签` 并**保正文**（保留段落结构、解码实体），结果非空且无残留标签——喂真实 HTML 样本断言（当前桩只 strip 整段 HTML 字符串→红）。
  3. `chinatax` provider 真发 HTTP 请求拉数据，非 2xx 抛 `ApiRequestError`；删除"仅加 `[provider:chinatax]` 前缀不发请求"桩。
  4. chinatax 响应解析为结构化 items（title/description/publisher/publish_date），逐条解析失败跳过 + warning（不整体崩）；空结果记 ALERT warning。
  5. 两个 handler 均返回 `ExecutorResult`（不写终态/不 commit）；chinatax 多 item 本轮合并单 artifact（多文档散射 degraded，见 F6-08）。
  6. **边界/失败**：网络/超时/解析异常按分类抛交内核 fail_claim；测试中真实网络用本地 fixture/mock 注入真实响应样本（显式标注非交付），不依赖外网。
- **对应测试台账项**：`FF-F6a-T04` / `FF-F6a-T05` / `FF-F6a-T06` / `FF-F6a-T07` / `FF-F6a-T08`（详见 §8）
- **收口标准**：真实 HTML 样本去标签保正文断言绿（修复前红）；htmlCrawl 超时/4xx 抛分类异常；chinatax 集成测试断言真发请求 + 解析出结构化 items；无字符串前缀桩残留；PDF 样本 xfail。
- **本 Phase 风险提醒**：真实抓取引入外部网络——测试一律 mock/fixture 注入（不打真实站点）；HTML 解析器选型须 stdlib 优先（避免引入重依赖与本地化障碍）；chinatax 真实接口可能变更，解析做容错 + 按条跳过。

### 5.3 Phase 3 — 显式 degraded（PDF/浏览器/多 provider/scatter）

- **Phase 目标**：把 [Q3] 明确不支持项落成显式 degraded（声明 + skip/xfail + 不留装成完成的桩）。
- **本 Phase 对应编号**：`F6-08` / `F6a-DG`
- **本 Phase 新增 / 修改 / 删除文件**：`workflow_clean/service.py:101-116`（多文档源 degraded）；`cleaners_universal/.../action_registry.py`（browser/PDF degraded 注册）；`providers_dedicated/service.py`（domain/realestate degraded）
- **具体功能预期**：
  1. 单文档源标准交接正常（建一条 rag step）；多文档源（child_files>0）抛 `DegradedActionError(reason="scatter/multi-document not supported")`。
  2. `browserFetch`/`browserPDF`/`geminiUnderstanding` 注册 degraded handler，调用即抛带 reason 的 `DegradedActionError`；测试 `xfail`。
  3. `domain`/`realestate` provider 注册 degraded handler，调用即抛 `DegradedActionError`；测试 `skip`。
  4. `list_actions` 对 degraded action 标 `degraded=True`，供能力发现区分"已实现 vs 显式不支持"。
  5. **边界**：degraded 错误带机器可读 `reason`（§8.5）；SSOT 记账 degraded 清单；grep 确认无"看起来能跑实则空返回"的桩残留。
- **对应测试台账项**：`FF-F6a-T09` / `FF-F6a-T10`（详见 §8）
- **收口标准**：调用任一 degraded action 抛 DegradedActionError；多文档源触发 degraded；list_actions 标 degraded；grep 无装成完成的桩。
- **本 Phase 风险提醒**：degraded ≠ 静默返回空——必须抛显式带 reason 的错误并测试断言抛错，否则会重蹈"桩被当成完成"（CR-6 R1/R2/R9 反例）。

---

## 6. 依赖的冻结设计决策（只读引用）

> 列出本 action-plan 依赖哪些 design / QNA / closure 结论。**不要在本节填写新 Q/A；只引 register 的 Q 编号，不复制内容、不改口。**

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| `[Q3]` 去桩增量范围 | `owner-gated-qna.md` Q3（G-F-3） | 本 AP 全部范围：只做 htmlCrawl(url)+chinatax+registry；PDF/浏览器/多 provider/scatter 全 §2.2 显式 degraded | 范围回到 design 重新定档；本 AP draft blocked |
| `[Q7]` 先红后绿铁律 | `owner-gated-qna.md` Q7（G-F-7） | §8 每项先红后绿（真实 HTML 样本断言去标签保正文，桩只 strip→红）；CI 断言强度门禁 | 退化为事后补弱断言→不得标 executed |
| `执行器契约 execute(step,deps)->ExecutorResult`（F3-02） | `initial-planning-by-opus.md` §4 红线第 2 条 / `FF-F3-kernel-recovery.md` F3-02 | 本 AP 全部去桩执行器遵守：只产结果、不写终态、不 commit（F6-01b 迁移、F6-02/03 handler 建在此契约上） | F3-02 未就绪→Phase 1 契约迁移 blocked，回退 F3；禁止保留自 commit 折中 |
| `事务原子性显式化`（F1-04） | `initial-planning-by-opus.md` §4 红线第 3 条 / `FF-F1-time-tx-base.md` | clean 执行器去 commit 后，终态落库交内核 succeed_claim 的显式 BEGIN IMMEDIATE 事务 | F1-04 未到位→succeed_claim 落库无原子性，blocked 回退 F1 |
| `时间 SSOT`（F1-01/03） | `initial-planning-by-opus.md` §4 红线第 1 条 | clean 删除 `CURRENT_TIMESTAMP`（第三时间格式，service.py:118/124），时间走 SSOT/DDL DEFAULT | F1 未到位→时间比较混格式，clean 顺带收口待 F1 |

---

## 7. 内置 Reference-Anchor 锚区

> 本段把本计划工作项要落到的既有代码、要避开的陷阱、以及威胁模型就地钉住。

### 7.1 锚表（本计划工作要落在哪些既有代码 / 新建点上）

> `处置`：`✅ 复用` / `♻️ 重 substrate` / `🆕 净新`。

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| A-1 | `packages/cleaners_universal/src/cleaners_universal/service.py:6-9` | `clean_payload`：url/api→`extract_text`，否则 `strip`——无 action 分支、无真实抓取（**stub**） | F6-02 重建为 htmlCrawl 真抓取清洗 | `♻️ 重 substrate` | CR-6 R1/S1 落点；9 行净新重建（universal 真实现 0/7） |
| A-2 | `packages/browser_runtime/src/browser_runtime/extract.py:6-12` | `extract_text`：3 条正则去 script/style/标签（**stub**） | F6-02 重建为健壮 HTML→text 去标签保正文 | `♻️ 重 substrate` | CR-6 R1；正则对嵌套/属性/实体脆弱 |
| A-3 | `packages/providers_dedicated/src/providers_dedicated/service.py:4-8` | `maybe_clean_with_provider`：chinatax host 单分支 + 字符串前缀，**不发请求**（**stub**） | F6-03 重建为 provider registry + chinatax 真 ETL | `♻️ 重 substrate` | CR-6 R2/S2；dedicated 真实现 0/3；9 行净新重建 |
| A-4 | `packages/workflow_clean/src/workflow_clean/service.py:80-82` | `process_clean_step`：`provider or universal` if/else 硬选执行器 | F6-01 替换为 registry 分派 | `♻️ 重 substrate` | CR-6 R4；无 action_branch 概念 |
| A-5 | `packages/workflow_clean/src/workflow_clean/service.py:101-129` | clean 执行器**自提交**：自插下游 rag step（uuid4 key, :101-116）+ UPDATE step succeeded（:118, CURRENT_TIMESTAMP）+ UPDATE run（:124）+ commit（:129） | F6-01b 删自提交、返回 ExecutorResult（遵守 F3-02） | `♻️ 重 substrate` | CR-6 R3 / G-CR4-03 clean 侧；与 FF-F3 A-5 同落点 |
| A-6 | `packages/workflow_clean/src/workflow_clean/service.py:41-49` | url 分支裸 `urlopen`（无 UA/重试/状态码校验，失败回退把 URL 当正文 :48-49） | F6-02 抓取移入 htmlCrawl handler，删裸 urlopen 兜底 | `♻️ 重 substrate` | CR-6 R1 实测脆弱点 |
| A-7 | `packages/ingestion/src/ingestion/service.py:204-216` | 建 clean step：`action='clean.start'` 一刀切，**action_branch 从不写入** | F6-01 创建侧写 action_branch | `✅ 复用` | CR-6 R4 创建侧 |
| A-8 | `packages/workflow_core/src/workflow_core/executor_contract.py` | F3-02 交付：`ExecutorResult` + `execute(step,deps)->ExecutorResult` 协议（**建造基准，读不改**） | 本 AP 全部去桩执行器建在此契约上 | `✅ 复用` | FF-F3 A-12 净新交付；本 AP 消费方，别重写 |
| A-9 | `packages/workflow_clean/src/workflow_clean/action_registry.py` | 将新建：`CleanActionRegistry` + `ActionSpec` + `UnknownActionError` + `DegradedActionError` + `list_actions` | F6-01 registry；F6a-DG degraded | `🆕 净新` | 对齐 legacy `clean-universal/services/action_registry.ts:52-178` |
| A-10 | `legacy-family/smind-skill-clean-universal/services/cleaner_web.ts:64-93` | legacy `handleHtmlCrawl`：fetch(UA/headers) + 状态码校验 + sanitizeHtml（**读不改的行为基线**） | F6-02 htmlCrawl 真实抓取参照 | `✅ 复用` | 只读对照；本地化无 CF Browser Rendering |
| A-11 | `legacy-family/smind-skill-clean-dedicated-apis/providers/chinatax/processor.ts:103-251` | legacy chinatax ETL：fetch→parse→hash→child files→summary（**读不改的行为基线**） | F6-03 chinatax 真 ETL 参照（child files/scatter 本轮 degraded） | `✅ 复用` | 只读对照；本轮只做 fetch+parse，scatter degraded |
| A-12 | `legacy-family/smind-clean-dispatcher/flows/finalizer.ts:96-306` | legacy finalizer scatter 模式（child_files>0 逐文件 diff + 触发 RAG）（**读不改的行为基线**） | F6-08 多文档源 degraded 的对照（本轮不实现 scatter） | `✅ 复用` | 只读对照；CR-6 R9；本轮 degraded |

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | **执行器自 commit 终态**（clean `service.py:118-129` 的 `status='succeeded'` + UPDATE run + `conn.commit()`）| 违 F3-02（终态归属内核 / planning §4 红线第 2 条 / G-CR4-03）；自提交导致与 succeed_claim 双写同一 step 终态、过期租约竞态下双重执行重复落盘。去桩后**严禁任一 handler/执行器保留自 commit**。 |
| ⛔2 | **留装成完成的桩**（如 browserFetch 返回空字符串/原样 payload、chinatax 加字符串前缀冒充 ETL、degraded action 静默返回空）| 违 [Q3] 横切纪律：不支持必须显式 DegradedActionError + 测试 skip/xfail + SSOT 记账；CR-6 R1/R2/R9 的盲点 B 根因正是"桩被当成完成"。 |
| ⛔3 | url 抓取失败**回退把 URL 字符串当正文**（现 `service.py:48-49 return source_uri`）| CR-6 R1：失败回退产出垃圾正文污染下游全部 chunk/embedding；htmlCrawl 须按错误分类抛异常交 fail_claim，不静默回退。 |
| ⛔4 | 用 `provider or universal` if/else 硬选执行器 / 创建侧不写 action_branch | CR-6 R4：无法表达"用哪个 action"、无 list_actions 能力发现（盲点 B + 断点 D）；必须 registry 分派 + 创建侧写 action_branch。 |
| ⛔5 | 引入 playwright/PDF 库/外部 LLM 等重依赖去实现 browser/PDF/LLM action | 违 [Q3]：本轮 browser/PDF/LLM 显式 degraded；引入重依赖会让 F6 膨胀失控（planning §9 风险"去桩范围爆炸"）。 |
| ⛔6 | 测试打真实外部站点（chinatax/任意 url） | 违测试稳定性：真实网络用本地 fixture/mock 注入真实响应样本（显式标注非交付），不依赖外网（[Q7] 可复现）。 |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：`docs/eval/first-code-review-plan/part-cr-6.md`（R1/R2/R3/R4/R9 + 逐 action parity 矩阵 + §3.2 stub 标定表 + legacy ~10.6k 行量化）、`part-cr-4.md`（R3 clean 侧 G-CR4-03）—— §7.1 是其与本 AP 相关子集的摘录；完整借鉴台账（含 legacy 双向 file:line）见真源。
- **安全 / 信任边界类工作项的威胁模型锚**：本 AP 的信任边界落点 = **执行器一次性语义（at-most-once）**（与 FF-F3/FF-F4 同属数据完整性边界，非经典认证/路径遍历——认证归 FF-F6c、路径遍历归 FF-F4）。威胁向量 = 过期租约竞态下的双重执行（重复 cleaned_text artifact + 重复 rag step），威胁模型落点：`part-cr-6.md` R3「为什么重要」（worker-A claim→lease 过期→reap→worker-B 重跑 process_clean_step→uuid4 key 不冲突→重复落盘）+ `part-cr-4.md` R3。F6-01b 去自提交 + F3-03 确定性 step_key（`rag-struct:{clean_step_id}`）即对此威胁建模——`FF-F6a-T03` 须含重放安全断言，不得只测 happy-path。**另**：htmlCrawl 发外部请求引入 SSRF 面（url 指向内网），本轮记账为 follow-up（交 FF-F6c/下一轮），本 AP 不标 executed 前须确认 SSRF 处置已记入下游。

---

## 8. 测试台账

> 本段一次性回答：本 AP 有哪些测试项、类型/层、新增还是沿用、映射哪个工作项与收口目标、怎么算 PASS。测试细节只在此写一次。

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| `FF-F6a-T01` | registry 注册/分派：注册 handler 后 `get_handler(branch)` 返回正确 handler；未知 branch 抛 `UnknownActionError` | 短途 | unit | `🆕 新增 tests/unit/test_clean_action_registry.py` | F6-01 → registry 分派工作 | `commit {sha} + test_clean_action_registry PASS + {YYYY-MM-DD HH:MM UTC}` |
| `FF-F6a-T02` | 无 if/else 硬选 + 创建侧写 action_branch + list_actions 枚举（含 degraded 标记）| 短途 | 契约（drift gate）| `🆕 新增 tests/unit/test_no_ifelse_dispatch.py（grep "or clean_payload"）+ test_action_branch_written.py` | F6-01 → 无硬选/可枚举 | `commit + gate 0 命中 + run-time` |
| `FF-F6a-T03` | clean 执行器去自提交：service 内 0 个 `status='succeeded'`/`conn.commit()`/`CURRENT_TIMESTAMP`（core 侧）；返回 ExecutorResult；**重放安全**（重复执行不产重复 artifact/rag step，确定性 step_key）| 短途 + spike | 契约 + 集成 | `🆕 新增 tests/unit/test_clean_no_self_commit.py（grep）+ tests/integration/test_clean_replay_safe.py` | F6-01b → 执行器只产结果/重放安全 | `commit + gate 0 命中 + test_clean_replay_safe PASS + run-time` |
| `FF-F6a-T04` | htmlCrawl 去标签保正文：喂真实 HTML 样本（含 script/style/嵌套标签/实体），断言输出**无残留标签 + 正文非空 + 保段落结构**（当前桩只 strip→红）| 短途 | unit | `🆕 新增 tests/unit/test_html_crawl_extract.py` | F6-02 → url→干净正文 | `commit + test_html_crawl_extract PASS（修复前 FAIL 截图）+ run-time` |
| `FF-F6a-T05` | htmlCrawl 抓取：真实响应注入（mock）断言带 User-Agent 发 GET + 2xx 正常；非 2xx / 超时抛 `UrlFetchError`（不回退把 URL 当正文）| 短途 | unit | `🆕 新增 tests/unit/test_html_crawl_fetch.py` | F6-02 → UA/超时/状态码/错误分类 | `commit + test_html_crawl_fetch PASS + run-time` |
| `FF-F6a-T06` | browserFetch/browserPDF/geminiUnderstanding degraded：调用抛 `DegradedActionError`（PDF 样本路径）| 短途 | unit | `🆕 新增 tests/unit/test_browser_pdf_degraded.py（xfail 标注 degraded）` | F6-02/F6a-DG → browser/PDF degraded | `commit + xfail（degraded reason）+ run-time` |
| `FF-F6a-T07` | chinatax 真实 ETL：mock 注入真实响应样本，断言**真发请求**（被调用）+ 解析出结构化 items（title/publisher 等）+ 产 ExecutorResult artifacts；无 `[provider:chinatax]` 前缀残留 | spike | 集成 | `🆕 新增 tests/integration/test_chinatax_etl.py（mock 网络）` | F6-03 → chinatax 真发请求/解析 | `commit + test_chinatax_etl PASS（修复前桩 FAIL）+ run-time` |
| `FF-F6a-T08` | provider registry 可扩展 + chinatax 错误分类：非 2xx 抛 `ApiRequestError`；解析失败按条跳过 + warning | 短途 | unit | `🆕 新增 tests/unit/test_provider_registry.py` | F6-03 → registry 可扩展/错误分类 | `commit + test_provider_registry PASS + run-time` |
| `FF-F6a-T09` | finalizer scatter degraded：单文档源建 1 rag step（正常）；多文档源（child_files>0）抛 `DegradedActionError` | 短途 | 集成 | `🆕 新增 tests/integration/test_finalizer_scatter_degraded.py（skip 标多文档源 degraded）` | F6-08 → 多文档源 degraded | `commit + test PASS + skip（degraded reason）+ run-time` |
| `FF-F6a-T10` | domain/realestate degraded + list_actions 标 degraded：调用 degraded provider 抛 `DegradedActionError`；list_actions 含 `degraded=True` | 短途 | unit | `🆕 新增 tests/unit/test_degraded_actions.py（skip 标多 provider）` | F6a-DG → 多 provider degraded/可发现 | `commit + test_degraded_actions PASS + skip + run-time` |

**列定义（填法约束）**：
- **类型**：`短途`（每 PR 快测）/ `spike`（阶段性 journey 验证）/ `mega` / `soak`。本 AP 端到端 clean→rag→search 语义归 F7 capstone（本 AP 无 mega/soak，退出层在 F7）。
- **层**：`unit` / `集成` / `契约`（drift gate）/ `回归` / `e2e`。
- **来源**：本 AP 全部 `🆕 新增`（clean 侧此前无有意义测试，仅桩固化输出，CR-8 G-CR8-R8）；端到端 capstone `🔱 fork` 见 §8.2 交 F7。
- **PASS 证据**：四元组 `commit + 测试名 + run-time(UTC)`；先红后绿项附"修复前 FAIL"证据（§8.5）。

### 8.2 复用台账（沿用 / fork 的既有用例明细）

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/integration/p3*`（clean 桩固化等值断言，CR-8 G-CR8-R8）| `🔱 fork → 语义属性断言` | 接真实 htmlCrawl/chinatax 后改为语义断言（去标签保正文 / 真发请求）；本 AP 标记需重写，实际重写归 F7-03 | 已存在，桩固化（无效绿）|
| `tests/e2e/test_first_fixes_capstone.py` B/C 步（file+url 双源 ingestion → clean htmlCrawl 真实清洗）| `🔱 fork（交 F7 建）` | 本 AP 提供真实 HTML/chinatax 样本 + PDF 步 xfail 标注 | F7 新建，本 AP 不在此跑 |

### 8.3 分层与跑法（各类型在哪跑、何时跑）

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | 本地 / 每 PR | unit·集成·契约 | 开发中持续（registry/htmlCrawl/chinatax 单测）|
| spike | journey 用例 | 集成（mock 网络）| 每 Phase 收口（chinatax ETL / clean 重放安全）|
| mega | 长程整合全链 | e2e 全链 | **F7 capstone 收口**（本 AP 提供样本，不在本 AP 跑）|
| soak | deterministic × N | live | 退出硬闸归 F3/F7（双重执行长稳）|

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖 端到端 clean→rag→search 语义命中（理由：跨 phase，需 F5 真实 embedding + F6b rag 去桩）→ 交 `FF-F7-test-integrity.md` capstone B/C/G 步；**本 AP 不假装覆盖**。
- 不覆盖 browser/PDF/多 provider/scatter 的真实能力（理由：[Q3] 显式 degraded）→ 本 AP 只测"调用抛 DegradedActionError"，真实能力交下一轮。
- 不覆盖 cleaned_text 落 ObjectStore（CR-6 R5，理由：[O4] 延后）→ 交 F4 协调后续。
- 不覆盖 htmlCrawl SSRF 防护（理由：本轮记账 follow-up）→ 交 FF-F6c / 下一轮安全。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 必带**四元组**证据；先红后绿项（T03/T04/T07）必附"修复前 FAIL"日志/截图（喂真实 HTML 样本时桩只 strip→红）；**计数 ≠ 价值**。
- `degraded` 项（T06 browser/PDF、T09 scatter、T10 多 provider）必带机器可读 `reason`（`DegradedActionError(reason=...)`），测试用 `xfail`/`skip` 显式标注，**不得静默返回空冒充完成**。
- 禁止 `status==200 / !="" / 桩恒等输出` 作为唯一断言（CR-8 假绿病因）；htmlCrawl 必须断言"无残留标签 + 保正文"，chinatax 必须断言"真发请求 + 解析出结构化字段"。
- **数据完整性边界**项（F6-01b 重放安全）测试须含**双重执行攻击向量**（过期租约竞态重跑 → 断言无重复 artifact/rag step），对应 §7.3 威胁模型，不得只测 happy-path。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| F3-02 执行器契约前置 | 本 AP 全部去桩执行器建在 `execute(step,deps)->ExecutorResult` 上；F3-02 未就绪则 Phase 1 契约迁移 blocked | high | 确认 FF-F3 F3-02 `succeed_claim(result=)` 已交付再迁；契约可先落地、clean handler 分批迁；禁止保留自 commit 折中 |
| F1-04 事务原子性前置 | clean 去 commit 后终态落库交内核显式 BEGIN IMMEDIATE 事务 | high | 与 FF-F1/FF-F3 同窗口；F1-04 未到位则 succeed_claim 落库无原子性，blocked 回退 F1 |
| 去桩范围爆炸 | F6 试图全量复刻 legacy ~10.6k 行（browser/PDF/多 provider/scatter）| high | [Q3] 增量限定 + 显式 degraded（§2.2）；引入重依赖为反例 ⛔5 |
| 真实抓取引入外部网络/不稳定 | htmlCrawl/chinatax 发外部请求，测试不稳定 | medium | adapter + 测试 mock/fixture 注入真实响应样本（显式标注非交付，⛔6）；不打真实站点 |
| htmlCrawl SSRF 面 | url 可指向内网，外部请求引入 SSRF | medium | 本轮记账 follow-up（§7.3）→ 交下一轮安全；本 AP executed 前确认已记入下游 |
| HTML 解析器选型 | 引入重解析库违本地化约束 | low | stdlib（`html.parser`）优先；保正文逻辑自实现 |
| 桩固化测试需重写 | 接真实实现后 p3 等值断言批量失败 | medium | 本 AP 标记需重写，实际重写交 F7-03（§8.2）|

### 9.2 约束与前提

- **技术前提**：F3-02 `ExecutorResult` 契约 + `succeed_claim(result=)` 已交付；F1-04 autocommit + 多写包 BEGIN IMMEDIATE 已到位；HTML 解析用 stdlib 优先。
- **运行时前提**：测试不依赖外网（真实网络一律 mock/fixture 注入）；htmlCrawl/chinatax 超时可配置。
- **组织协作前提**：与 FF-F3（同窗口推进 clean 执行器去自提交）、FF-F6b（共用 action registry 模式与契约）、FF-F6c（chinatax provider 配置载体 prompt_versions/provider_configs）协调。
- **上线 / 合并前提**：§8 全 PASS（先红后绿四元组齐全）；degraded 项 reason + skip/xfail 齐全；grep gate（无 if/else 硬选、无自 commit、无装成完成的桩）0 命中。

### 9.3 文档同步要求

- 需要同步更新的设计文档：`initial-planning-by-opus.md` §6.6 F6-01/02/03/08（执行后回填实际范围）；degraded 清单（browser/PDF/多 provider/scatter）记入 SSOT。
- 需要同步更新的说明文档 / README：clean 包 README 标注"当前仅支持 file 文本 + url htmlCrawl 静态抓取；browser/PDF/多 provider/scatter degraded"。
- 需要同步更新的测试说明：`tests/` 新增 clean 去桩单测/集成测试清单；degraded xfail/skip 标注说明。

### 9.4 完成后的预期状态

1. clean 执行器分派由 action registry（branch→handler）驱动，创建侧写 `action_branch`、执行侧据此选 handler，`list_actions` 可枚举能力（含 degraded 标记）；`provider or universal` if/else 硬选消除。
2. `htmlCrawl` 对 url 源真实抓取（UA/超时/状态码/错误分类）+ 健壮去标签保正文；`chinatax` provider 真发请求 + 解析产 ExecutorResult artifacts；桩（正则 strip + 字符串前缀）删除。
3. clean 执行器遵守 F3-02 契约：只产 ExecutorResult、不写 core 终态、不 commit；下游 rag step 用确定性 step_key，过期租约竞态下重放安全（无重复 artifact/rag step）。
4. browser/PDF/多 provider/scatter 落成**显式 degraded**：调用抛带 reason 的 DegradedActionError、测试 skip/xfail、SSOT 记账，无装成完成的桩。
5. clean 侧测试从桩固化等值断言（无效绿）转为语义属性断言（去标签保正文 / 真发请求 / 重放安全），先红后绿四元组齐全；端到端语义命中交 F7 capstone。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

> 收口 = §8 测试台账逐项 PASS，且每项映射回 §3 工作项的收口目标。

### 10.1 收口硬闸

本 AP 无 mega/soak 退出层（归 F7 capstone）；本 AP 的收口硬闸 = 全部短途/spike 项 PASS + 四元组齐全 + degraded reason 齐全：

1. registry 分派 + 无 if/else 硬选 + action_branch 写入 + list_actions 可枚举（由 `FF-F6a-T01` `FF-F6a-T02` 证明）。
2. clean 执行器去自提交 + 重放安全（无重复 artifact/rag step）（由 `FF-F6a-T03` 证明）。
3. htmlCrawl 真抓取 + 去标签保正文（修复前红）+ chinatax 真发请求/解析（由 `FF-F6a-T04` `FF-F6a-T05` `FF-F6a-T07` `FF-F6a-T08` 证明）。
4. browser/PDF/多 provider/scatter 显式 degraded（带 reason + skip/xfail，无装成完成的桩）（由 `FF-F6a-T06` `FF-F6a-T09` `FF-F6a-T10` 证明）。

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| registry 分派工作 / 无 if/else 硬选 / 可枚举 | F6-01 | `FF-F6a-T01` `FF-F6a-T02` | `commit + test + run-time` | `未观察`（draft）|
| 执行器只产 ExecutorResult / 重放安全 | F6-01b | `FF-F6a-T03` | `commit + test + run-time` | `未观察` |
| url→去标签保正文 / UA/超时/状态码/错误分类 | F6-02 | `FF-F6a-T04` `FF-F6a-T05` `FF-F6a-T06` | `commit + test + run-time` | `未观察` |
| chinatax 真发请求/解析 / registry 可扩展 | F6-03 | `FF-F6a-T07` `FF-F6a-T08` | `commit + test + run-time` | `未观察` |
| 多文档源 / 多 provider degraded（带 reason）| F6-08 / F6a-DG | `FF-F6a-T09` `FF-F6a-T10` | `commit + test + skip/xfail + run-time` | `未观察` |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | registry 分派 + htmlCrawl 真抓取清洗 + chinatax 真 ETL 落地；clean 执行器遵守 F3-02 契约；browser/PDF/多 provider/scatter 显式 degraded |
| 测试 | §8 测试台账全 PASS（先红后绿四元组齐全；degraded 项 reason + skip/xfail）|
| 文档 | degraded 清单记入 SSOT；clean 包 README 标注支持范围；§6.6 范围回填 |
| 风险收敛 | F3-02 契约依赖确认到位；去桩范围未爆炸（[Q3] 增量）；重放安全闭环 G-CR4-03 clean 侧；SSRF follow-up 已记账 |
| 可交付性 | clean 真实能力（file+url htmlCrawl + chinatax）可被 F7 capstone B/C 步消费；degraded 步骤 xfail 明示 |

### 10.4 NOT-成功识别

> 任一收口硬闸测试 `degraded / 未观察`（指意外失败，非 §2.2 显式 degraded 项）⇒ **不得标 `executed`**；按 closure 五态（`verified / observed-OK-at-closure / partial / 未观察 / deferred`）如实归类 + handoff，不 silent overclaim。特别地：若 htmlCrawl 去标签保正文未先红后绿、或 chinatax 仍是字符串前缀桩、或任一 degraded 项静默返回空冒充完成 → 判 NOT-成功。

---

## 11. 执行日志回填（仅 `executed` 状态使用）

> 文档状态非 `executed` 时本节省略（本 AP 为 `draft`）。
