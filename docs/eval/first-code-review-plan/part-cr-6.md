# Nano-Agent 代码审查报告 — CR-6 · Clean 流水线

> 审查对象: `CR-6 Clean 流水线`
> 审查类型: `code-review`
> 审查时间: `2026-05-31`
> 审查人: `Claude sub-agent (CR-6)`
> 审查范围:
> - `packages/workflow_clean/src/workflow_clean/service.py`(129 行)
> - `packages/cleaners_universal/src/cleaners_universal/service.py`(9 行)
> - `packages/providers_dedicated/src/providers_dedicated/service.py`(9 行)
> - `packages/browser_runtime/src/browser_runtime/extract.py`(13 行)
> 对照真相:
> - `legacy-family/smind-skill-clean-universal/`(通用 cleaner,~3.4k 行)
> - `legacy-family/smind-skill-clean-dedicated-apis/`(专用 API cleaner,~3.7k 行)
> - `legacy-family/smind-clean-dispatcher/`(编排器,~4.5k 行)
> - `docs/refactor/core.sql`(artifacts/workflow_steps schema)、`docs/eval/.../index.md`(口径)
> 文档状态: `changes-requested`

---

## 0. 总结结论

- **整体判断**:`CR-6 Clean 流水线是一条"能让 demo 跑通、但几乎不含真实 clean 能力"的占位实现。三个执行器(cleaners_universal / providers_dedicated / browser_runtime)整体是桩,legacy ~10k 行 clean 能力在 Python 侧基本未迁移;且 clean 侧承接了 CR-4 G-CR4-03 的"执行器自提交 + 无幂等键"链路缺陷,在过期租约竞态下会重复落盘下游 step 与 artifact。`
- **结论等级**:`changes-requested`(实质接近 blocked)
- **是否允许关闭本轮 review**:`no`
- **本轮最关键的 1-3 个判断**:
  1. **clean action parity ≈ 0/9 真实现**:legacy 9 个通用 action(htmlCrawl / htmlCrawl-geminiClean / browserFetch / browserFetch-geminiClean / browserPDF / browserPDF-geminiClean / geminiUnderstanding)+ 3 个 dedicated provider action(chinatax / domain / realestate)在 Python 侧无一被真实现:无 fetch、无浏览器渲染、无 PDF Vision、无 Gemini、无 sanitizer、无 child files/scatter、无 action registry。仅有正则去标签 + chinatax 字符串前缀的硬编码桩(盲点 B 重灾区)。
  2. **执行器自提交 succeeded + 无幂等键(承接 G-CR4-03)**:`service.py:118/129` 在 worker `succeed_claim` 之前就把 step 置 `succeeded`、INSERT 下游 rag step、推进 run 并 `conn.commit()`。下游 step / artifact 用 `uuid4()` 无幂等键。过期租约下双 worker 重复执行会重复落盘 artifact + 重复创建 rag step(blocker)。
  3. **action registry 抽象整体丢失(盲点 B + 断点 D)**:legacy 有 `ActionRegistry` + `getHandler(branchName)` + `list_actions` RPC 自描述;Python `process_clean_step` 用一条 `provider_cleaned or clean_payload(...)` 的 if/else 硬编码选择执行器,`workflow_steps.action_branch` 概念在创建侧根本未写入(ingestion 建 step 时 `action='clean.start'` 一刀切),无法表达"用哪个 action"。

---

## 1. 审查方法与已核实事实

- **对照文档**:
  - `docs/eval/first-code-review-plan/index.md`(§1 B/D/L 口径、C1–C5、§7 owner 口径:stub 即盲点 B)
  - `docs/eval/smind-family-strucure-analysis-by-GPT.md` §3.6(legacy clean-universal action 族)
  - `docs/refactor/core.sql`(artifacts / workflow_steps schema)
- **核查实现(Python)**:
  - `packages/workflow_clean/src/workflow_clean/service.py`(全文,129 行)
  - `packages/cleaners_universal/src/cleaners_universal/service.py`(9 行)
  - `packages/providers_dedicated/src/providers_dedicated/service.py`(9 行)
  - `packages/browser_runtime/src/browser_runtime/extract.py`(13 行)
  - `apps/worker/src/smind_worker/main.py`(派发与 succeed/fail claim 链路)
  - `packages/ingestion/src/ingestion/service.py:204-216`(clean step 创建侧 stage/action)
  - `packages/workflow_rag/src/workflow_rag/service.py:15-53`(下游如何读 cleaned_text artifact)
  - `packages/workflow_core/src/workflow_core/retry.py:7-35`(`succeed_claim`)
- **核查实现(legacy 校准)**:
  - clean-universal:`services/action_registry.ts`、`flows/processor.ts`、`services/cleaner_web.ts`、`services/cleaner_doc.ts`
  - clean-dedicated-apis:`services/action_registry.ts`、`providers/chinatax/processor.ts`(scatter/child files)
  - clean-dispatcher:`flows/{orchestrator,finalizer}.ts`、`services/{mapper,differ}.ts`、`core/validator.ts`
- **执行过的验证**:
  - `grep` 派发分支 stage 命名(`startswith("clean")` vs `startswith("rag:")`)与创建侧 stage 字符串(`'clean'` / `'rag:structurize'`)对账。
  - `grep` `workflow_events` 在 clean 路径出现情况(C4)。
  - 静态读取 `succeed_claim` 与 `process_clean_step` 的 commit 顺序,推断双重执行落盘后果。
- **复用 / 对照的既有审查**:
  - `index.md` 附录 B G-CR4-03(执行器自提交)— **采纳并在 clean 侧细化**(本报告补 artifact/rag-step 幂等键缺失的具体后果)。
  - A1 / G-CR4 stage 命名疑点 — **独立复核后澄清为非断点**(见 R6)。
  - CR-3 R1(路径遍历)、CR-3 R6(非原子写)— 作为线索,核实 clean 主路径**未触达** ObjectStore 写(见 R5)。

### 1.1 已确认的正面事实

- clean step 与下游 rag step 的 **stage 命名实际匹配**:ingestion 建 step `stage='clean'`,worker `"clean".startswith("clean")` 为真;finalizer 建 `stage='rag:structurize'`,worker `startswith("rag:")` 为真。clean→rag 交接在命名层面贯通(A1 在 clean 侧不成立,见 R6)。
- clean→rag 数据交接走 **artifact 表 + `cleaned_text` 类型**(`service.py:84-100` 写,`workflow_rag/service.py:52-53` 读),链路对得上,artifact_id 通过下游 step 的 `payload_json` 传递。
- `_load_raw_payload`(`service.py:14-64`)对 file/static/url/api 四类源**各有分支**,不是单分支,且 url 分支做了 `URLError` 兜底——比 providers_dedicated 的单分支完整。
- 失败路径有兜底:worker `main.py:54-56` 捕获异常并 `fail_claim`,不会静默吞掉(C2 部分通过)。

### 1.2 已确认的负面事实

- 三个执行器包合计 31 行,**无任何真实 clean 能力**:无 HTTP fetch 重试/User-Agent、无浏览器渲染、无 PDF 解析、无 Gemini/LLM、无 HTML sanitizer(去广告/去脚本仅靠 3 条正则)、无 child files/scatter、无差分(differ)、无 io slot 渲染。
- `providers_dedicated.maybe_clean_with_provider` 是**硬编码单分支**:仅当 URI 含 `chinatax.gov.cn` 时给 payload 加 `[provider:chinatax]` 前缀字符串,**完全不调用任何 API**,legacy chinatax 的 fetch→parse→hash→child files→summary 全部缺失;domain / realestate 两个 provider 在 Python 侧根本不存在。
- **无 action registry / list_actions**:legacy 双 worker 都有 `ActionRegistry` + RPC 自描述能力发现;Python 侧零实现,`workflow_steps.action_branch` 在创建侧从未写入。
- **执行器自提交**:`service.py:118` 在 worker `succeed_claim` 之前就把 step 置 `succeeded` 并 commit;下游副作用无幂等键。
- clean 路径**不落 `workflow_events`**(C4 fail):`grep` 确认 `workflow_clean` 包内零 `workflow_event` 写入;仅 worker `succeed_claim` 间接落 step_attempts,但 clean 自身的开始/产物事件无记录。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | 四个被审文件全文读;legacy 7 个 TS 关键文件全文读;双向 file:line 见 §2.1/parity 矩阵。 |
| 本地命令 / 测试 | `no` | 仅静态 grep 对账,未跑测试(测试有效性归 CR-8)。双重执行后果为基于代码顺序的推断,已在 R3 标注"推断"。 |
| schema / contract 反向校验 | `yes` | 对照 `core.sql` artifacts(`storage_backend` CHECK)与 workflow_steps(无 action_branch 列约束)。 |
| live / deploy / preview 证据 | `n/a` | 无。 |
| 与上游 design / QNA 对账 | `yes` | 采纳 G-CR4-03,并独立复核 A1 stage 命名,澄清 clean 侧不成立。 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | universal cleaner 9 个 action 整体未实现(纯正则桩) | critical | B/scope-drift | yes | 实现 fetch/browser/PDF/LLM action 族或显式声明降级范围 |
| R2 | dedicated provider 硬编码 chinatax 单分支,无 API/scatter/child files | critical | B/scope-drift | yes | 实现 provider registry + 至少 chinatax 真 ETL,或显式裁掉 |
| R3 | 执行器自提交 succeeded + 下游副作用无幂等键(承接 G-CR4-03) | critical | L/correctness | yes | 移除执行器内自提交,副作用加幂等键 |
| R4 | action registry / list_actions 抽象整体丢失,执行器用 if/else 硬选 | high | B+D/scope-drift | yes | 引入 action_branch 字段 + registry 分派 |
| R5 | cleaned text 落 artifact.metadata_json(sqlite_ref)而非 ObjectStore | high | B/delivery-gap | no | 大文本应落 ObjectStore;明确 storage_backend 策略 |
| R6 | (澄清项)A1 stage 命名在 clean 侧不成立 | low | n/a | no | 关闭 A1 对 clean 的怀疑,移交 CR-8 复核 rag 侧 |
| R7 | clean step 全程不落 workflow_events(C4) | medium | C4/correctness | no | clean 开始/成功/失败补 event |
| R8 | clean 主路径异常无分类、不落 step_attempts 细节 | medium | C2/correctness | no | 错误分类 + 失败 attempt 记录 |
| R9 | finalizer 仅"标准交接",scatter/差分/child files 全缺 | high | B/scope-drift | no | 实现散射模式或声明不支持多文档源 |

---

### R1. universal cleaner 9 个 action 整体未实现(纯正则桩)

- **严重级别**:`critical`
- **类型**:`B/scope-drift`(stub 即盲点 B,owner §7 口径)
- **是否 blocker**:`yes`
- **事实依据**:
  - Python:`cleaners_universal/service.py:6-9` 全部逻辑 = `if source_kind in {"url","api"}: return extract_text(payload) else: return payload.strip()`;`browser_runtime/extract.py:6-12` = 3 条正则去 script/style/标签 + 折叠空白。
  - legacy:`clean-universal/services/action_registry.ts:91-148` 注册 6 个 branch(htmlCrawl / htmlCrawl-geminiClean / browserFetch / browserFetch-geminiClean / browserPDF / geminiUnderstanding,cleaner_web 另含 `browserPDF-geminiClean` 共 7 分支);`cleaner_web.ts:65-207` 含 `fetch`(带 User-Agent/headers/状态码校验)、Cloudflare Browser Rendering `content`、Browser Rendering `pdf` + Gemini Vision、`sanitizeHtml`(`core/sanitizer.ts` 去广告去脚本);`cleaner_doc.ts:59-152` 含 20MB 大小校验 + Gemini documentUnderstanding。
- **为什么重要**:
  - clean 阶段是 file/url 源进入 RAG 前的**唯一标准化关口**。Python 侧对 url/api 只做正则去标签——**无真实抓取**(url 分支的 `urlopen` 在 `_load_raw_payload` 里且 10s 超时、`errors="ignore"` 解码、失败回退成把 URL 字符串当正文),SPA/动态页、PDF、需 LLM 降噪的页面全部产出垃圾或空文本,污染下游全部 chunk/embedding。
- **审查判断**:
  - 这是 owner 预判的重灾区,确认成立。legacy ~3.4k 行通用 cleaner 在 Python 侧迁移量 ≈ 31 行正则,**9 个 action 真实现 0 个**。设计文档未声明"砍掉浏览器/LLM 能力",故记为无意丢失的盲点 B,而非有意简化。
- **建议修法**:
  - 至少实现 htmlCrawl(真 fetch + 健壮 HTML→text)与 geminiUnderstanding(PDF)两条主干;其余按本地化约束(无 CF Browser Rendering)显式在设计 doc 声明降级与替代方案(如 headless playwright)。在报告/SSOT 标注"当前仅支持静态文本抽取"。

### R2. dedicated provider 硬编码 chinatax 单分支,无 API/scatter/child files

- **严重级别**:`critical`
- **类型**:`B/scope-drift`
- **是否 blocker**:`yes`
- **事实依据**:
  - Python:`providers_dedicated/service.py:4-8` 全文 = `if "chinatax.gov.cn" not in canonical_uri: return None; return f"[provider:chinatax] {payload.strip()}"`。**不发任何 HTTP 请求**,只给已有 payload 加字符串前缀。
  - legacy:`clean-dedicated-apis/services/action_registry.ts:59-80` 注册 **3 个 provider action**(`fetch-chinatax-articles` / `getAgencyListings` / `fetch-listings`);`providers/chinatax/processor.ts:103-251` 是完整 ETL:fetch→parse→`calculateHash`(content_hash + meta_hash)→逐条写 `atomic_bundle` child file→生成 `summary.jsonl`→返回 `child_files[]`。domain / realestate 各有独立 processor 目录。
- **为什么重要**:
  - 专用 API 源(chinatax/domain/realestate)的全部价值在于**调用外部 API 抓取结构化数据并散射成多个原子子文件**。Python 桩不抓取、不散射、不算 hash、不产 child files——对这类源**等于没有 clean 能力**;domain/realestate 两个 provider 在 Python 侧完全不存在(缺失)。
- **审查判断**:
  - 与 index 附录 A4 一致。3 个 provider action 真实现 0 个。硬编码单分支 + 仅字符串前缀,是典型盲点 B(stub)。
- **建议修法**:
  - 引入 provider registry(URI/host → handler),实现 chinatax 真 ETL(fetch + parse + hash + child files + summary)作为参考实现;domain/realestate 至少留接口。配合 R9 的 scatter。

### R3. 执行器自提交 succeeded + 下游副作用无幂等键(承接 G-CR4-03,clean 侧落点)

- **严重级别**:`critical`
- **类型**:`L/correctness`
- **是否 blocker**:`yes`
- **事实依据**:
  - `workflow_clean/service.py:83`(artifact_id = `str(uuid4())`)、`:101-116`(INSERT 下游 rag step,id/step_key 用 `uuid4()`)、`:117-120`(`UPDATE workflow_steps SET status='succeeded'`)、`:121-128`(UPDATE run → running/rag)、`:129`(`conn.commit()`)——**全部在 worker 调用 `succeed_claim` 之前**。
  - worker `main.py:48` 调 `process_clean_step`(内部已 commit + 置 succeeded),`:53` 再调 `succeed_claim`;`succeed_claim`(`retry.py:7-26`)又一次 `UPDATE workflow_steps SET status='succeeded'` 并 INSERT step_attempts。职责撕裂:**两处都在改同一 step 的终态**。
  - artifact 无业务幂等键(纯 uuid4);下游 rag step `step_key` = `f"rag-struct-{uuid4().hex}"`,与 `workflow_steps UNIQUE(workflow_run_id, step_key)` 配合——但因 uuid4 每次不同,**唯一约束形同虚设,挡不住重复**。
- **为什么重要**:
  - 联动 CR-4 G-CR4-01(`reap_expired_claims` 死代码)/ G-CR4-02(lease_expires_at 畸形):一旦租约误判过期被重捞,**第二个 worker 会重新跑一遍 `process_clean_step`**,再 INSERT 一条新 artifact(uuid4 不冲突)+ 一条新 rag step(step_key 含 uuid4 不冲突),并再次推进 run。结果:**重复 cleaned_text artifact + 重复下游 rag 分支**,下游 `_latest_artifact` 按 created_at DESC 取最新尚可自洽,但重复 rag step 会被双双 claim,造成重复 structurize/向量化(放大 CR-3 R3 孤儿 rowid)。
- **审查判断**:
  - clean 侧确证 G-CR4-03 的具体落盘后果。执行器**不应**自行置 step 终态,这是 worker/`succeed_claim` 的职责;且下游副作用必须有确定性幂等键。区分事实与推断:commit 顺序与 INSERT 列为**事实**;双重执行的触发依赖 CR-4 的 lease 缺陷,为**推断**(条件成立时必然发生)。
- **建议修法**:
  - `process_clean_step` 只产出 artifact + 下游 step,**不**改自身 step 状态、**不** commit,把终态与提交交给 `succeed_claim`(单一事务边界)。下游 rag step 的 step_key 改为**确定性**(如 `rag-struct:{clean_step_id}`),artifact 用 `(workflow_run_id, artifact_type, source_id)` 维度做幂等(`INSERT ... ON CONFLICT DO NOTHING` 或先查后写),使重放安全。

### R4. action registry / list_actions 抽象整体丢失,执行器用 if/else 硬选

- **严重级别**:`high`
- **类型**:`B+D/scope-drift`
- **是否 blocker**:`yes`
- **事实依据**:
  - legacy:两个 skill worker 各有 `ActionRegistry`(`getHandler(branchName)` + `getCapabilities()`/`list_actions` RPC),dispatcher `mapper.ts:181-252` 透传 `workflow_payload.action_branch` 选择 handler。
  - Python:`workflow_clean/service.py:81-82` = `provider_cleaned = maybe_clean_with_provider(...); cleaned = provider_cleaned or clean_payload(source_kind, payload)` —— 用 URI 是否含 chinatax 来"二选一",无 branch 概念。
  - 创建侧:`ingestion/service.py:208` 建 step 时 `action='clean.start'` 一刀切,**`workflow_steps.action_branch` 从不写入**(schema 也未含该列,见 core.sql workflow_steps 仅 step_key/stage/action)。
- **为什么重要**:
  - 没有 action_branch,系统**无法表达"这个源该用 htmlCrawl 还是 browserPDF 还是 geminiUnderstanding"**,clean 策略不可配置、不可发现(无 list_actions 供管理面展示)。这既是能力盲点 B(registry 缺失),也是链路断点 D(创建侧→执行侧的 action 选择信息流断裂)。
- **审查判断**:
  - 与 R1/R2 同根:因为执行器是桩,registry 自然也未建。属应有未有的盲点 B。
- **建议修法**:
  - 在 workflow_steps(或 payload_json)引入 action_branch;clean 服务用 registry(dict[branch]→handler)分派;补一个能力发现入口供管理面。

### R5. cleaned text 落 artifact.metadata_json(sqlite_ref)而非 ObjectStore

- **严重级别**:`high`
- **类型**:`B/delivery-gap`
- **是否 blocker**:`no`
- **事实依据**:
  - `service.py:84-100`:artifact `storage_backend='sqlite_ref'`、`metadata_json = json.dumps({"text": cleaned, ...})` —— **cleaned 全文内联进 core.db 的 metadata_json**,不写 ObjectStore。
  - core.sql:artifacts 设计 `storage_backend DEFAULT 'object_store'`,`object_key` 字段专为对象存储设计;`sqlite_ref` 是合法值但语义上应是"小引用",非承载大正文。
  - 对比下游:rag 的 chunk_text 走 `object_store.put_text`(`workflow_rag/service.py:110`)——下游用了 ObjectStore,**clean 产物却没用**,不一致。
  - legacy:`finalizer.ts:116-117` 把 `cleaned_content_r2_key` 写进 file artifacts,正文落 R2(对象存储)。
- **为什么重要**:
  - 大型 cleaned 正文塞进 core.db 的 JSON 列,会让 core.db 膨胀、违背"正文落对象存储、core.db 存元数据/状态"的分层意图(C5 适配层纪律边缘)。好的一面是绕过了 CR-3 R1 路径遍历(因为根本没写 ObjectStore)——但代价是产物存储模型与设计漂移。
- **审查判断**:
  - 是有意为之的简化(用 sqlite_ref 避开对象存储),但与设计/legacy 漂移,记 delivery-gap。非 blocker(功能可跑),但需在 SSOT 对齐存储策略。
- **建议修法**:
  - cleaned_text 落 ObjectStore(复用 rag 同款 `put_text`),artifact 存 object_key + content_hash + size_bytes;同时推动 CR-3 R1/R6 的路径校验与原子写修复。

### R6. (澄清项)A1 stage 命名在 clean 侧不成立

- **严重级别**:`low`
- **类型**:`n/a`(澄清/撤销疑点)
- **是否 blocker**:`no`
- **事实依据**:
  - ingestion 建 clean step:`stage='clean'`(`ingestion/service.py:208`);worker `main.py:47` `step["stage"].startswith("clean")` → True。
  - clean 建下游 rag step:`stage='rag:structurize'`(`service.py:106`);worker `main.py:49` `startswith("rag:")` → True。
- **为什么重要**:
  - 附录 A1 怀疑 `startswith("clean")`(无冒号)vs `startswith("rag:")`(有冒号)命名不一致导致某类 step 永不被路由。clean 侧实测:clean step stage 恰为 `'clean'`(无冒号也匹配),rag step stage 为 `'rag:structurize'`(有冒号也匹配),**两条都贯通**。
- **审查判断**:
  - clean→rag 交接在命名层面无断点。A1 对 clean 侧的怀疑**撤销**。注意:`startswith("clean")` 无冒号偏宽松,未来若引入 `cleanup`/`cleanse` 等 stage 会误匹配,属轻度脆弱性,移交 CR-8 与 rag 侧一并核。
- **建议修法**:
  - 统一 stage 前缀约定(建议都带冒号 `clean:` / `rag:`),worker 用精确前缀匹配。非紧急。

### R7. clean step 全程不落 workflow_events(C4)

- **严重级别**:`medium`
- **类型**:`C4/correctness`
- **是否 blocker**:`no`
- **事实依据**:
  - `grep workflow_event` 在 `workflow_clean` 包内**零命中**;`service.py` 全程只写 artifacts / workflow_steps / workflow_runs,无 `append_workflow_event`。
  - 设计硬约束(index §1 C4):"所有 workflow step 必须可观测"。legacy 各 flow 大量 `logger.info(... log_code ...)` 记录 STEP 生命周期。
- **为什么重要**:
  - clean 是耗时/易失败的外部 I/O 阶段,无 event 则无法观测"开始抓取/抓取失败/产物大小/用了哪个 action",运维与排障盲。
- **审查判断**:
  - C4 在 clean 路径**fail**。succeed_claim 间接落了 step_attempts,但 clean 自身语义事件缺失。
- **建议修法**:
  - clean 开始/成功/失败各 `append_workflow_event`(含 action_branch、产物字节数、耗时)。

### R8. clean 主路径异常无分类、不落 step_attempts 细节(C2)

- **严重级别**:`medium`
- **类型**:`C2/correctness`
- **是否 blocker**:`no`
- **事实依据**:
  - worker `main.py:54-56` 宽 `except Exception` → `fail_claim(..., error_message=str(exc))`,error_code 由 CR-4 侧恒为 `EXECUTOR_FAILURE`(G-CR4-08)。
  - legacy `cleaner_web.ts`/`processor.ts` 抛带 ErrorCode 的 `SkillException`(URL_FETCH_FAILED / UNKNOWN_CLEANER_BRANCH / MESSAGE_VALIDATION_FAILED 等),可区分可重试/不可重试。
- **为什么重要**:
  - clean 失败原因多样(网络超时 vs 未知 branch vs 文件超限),无分类则 retry 策略一刀切,且无法判定"不可重试"(如 unknown branch 重试无意义)。
- **审查判断**:
  - 与 G-CR4-08 同根,clean 侧无任何自有错误分类。异常未被静默吞(有 fail_claim),故 C2 部分通过,但分类缺失。
- **建议修法**:
  - clean 抛带分类的异常类型;worker/`fail_claim` 据此写 error_code 与 retryable。

### R9. finalizer 仅"标准交接",scatter/差分/child files 全缺

- **严重级别**:`high`
- **类型**:`B/scope-drift`
- **是否 blocker**:`no`(取决于是否需要多文档源)
- **事实依据**:
  - Python:`service.py:101-128` 只创建**一条**下游 rag step(标准交接),无 child files 概念、无 differ、无 scatter。
  - legacy:`finalizer.ts:96-306` 支持 `isScatterMode`(child_files.length>0 → 逐子文件 `calculateDiff` + `upsertFileRelations` + 对每个变更子文件单独 `sendWorkflowStartToRagDispatcher`),并支持 force 模式把 no_update 升级为 full_update;`differ.ts` 做 content_hash/meta_hash 差分决策。
- **为什么重要**:
  - chinatax 等 provider 一次抓取产出 N 个原子文件(scatter),legacy 对每个子文件独立差分 + 独立触发 RAG,实现增量更新与去重。Python 无此能力 → 专用 API 源即使将来实现抓取,也无法正确散射成多文档。
- **审查判断**:
  - 与 R2 联动的能力盲点 B。当前因 provider 本身是桩(R2),scatter 缺失暂未暴露;一旦实现 R2 则此项升为 blocker。
- **建议修法**:
  - 实现 child_files → 多下游 step 的散射 + 基于 hash 的差分(differ),对齐 legacy finalizer。

---

## 3. In-Scope 逐项对齐审核

### 逐 action 完整 parity 矩阵 — universal cleaner

| legacy action(branch) | legacy 实现位置 | Python 实现位置 | 判定 | 双向 file:line |
|------------------------|-----------------|-----------------|------|----------------|
| `htmlCrawl` | `cleaner_web.ts:248-255`(fetch + sanitizeHtml + stripHtmlTags) | 仅正则去标签(无 fetch:url 抓取在 `_load_raw_payload` 用 urlopen,无 UA/重试/状态码校验) | **盲点B**(部分骨架/无真抓取与降噪) | legacy `services/cleaner_web.ts:65-93,248-255` ↔ py `browser_runtime/extract.py:6-12` + `workflow_clean/service.py:45-49` |
| `htmlCrawl-geminiClean` | `cleaner_web.ts:256-269`(fetch + Gemini textGeneration) | 无 | **盲点B**(缺失) | legacy `cleaner_web.ts:256-269` ↔ py 无 |
| `browserFetch` | `cleaner_web.ts:272-279`(CF Browser Rendering content) | 无(无浏览器渲染) | **盲点B**(缺失) | legacy `cleaner_web.ts:99-134,272-279` ↔ py 无 |
| `browserFetch-geminiClean` | `cleaner_web.ts:280-293`(browser + Gemini) | 无 | **盲点B**(缺失) | legacy `cleaner_web.ts:280-293` ↔ py 无 |
| `browserPDF` | `cleaner_web.ts:296-302` + `handleBrowserPdfPipeline:142-207`(CF PDF + Gemini Vision) | 无(无 PDF 解析) | **盲点B**(缺失) | legacy `cleaner_web.ts:142-207,296-302` ↔ py 无 |
| `browserPDF-geminiClean` | `cleaner_web.ts:296-302`(同 browserPDF case) | 无 | **盲点B**(缺失) | legacy `cleaner_web.ts:296-302` ↔ py 无 |
| `geminiUnderstanding` | `cleaner_doc.ts:111-129`(20MB 校验 + Gemini documentUnderstanding) | 无 | **盲点B**(缺失) | legacy `cleaner_doc.ts:59-152` ↔ py 无 |
| sanitizeHtml(去广告/去脚本) | `core/sanitizer.ts`(被各 branch 调用) | 3 条正则(script/style/标签) | **盲点B**(有意简化但远弱) | legacy `cleaner_web.ts:84,124` ↔ py `browser_runtime/extract.py:8-11` |
| `list_actions` / getCapabilities(RPC 自描述) | `action_registry.ts:176-178` | 无 | **盲点B**(缺失) | legacy `services/action_registry.ts:81-178` ↔ py 无 |

**universal action 真实现:0 / 7 个 branch(htmlCrawl 仅有正则降级骨架,不达等价)。**

### 逐 provider parity 矩阵 — dedicated apis

| legacy provider action | legacy 实现位置 | Python 实现位置 | 判定 | 双向 file:line |
|------------------------|-----------------|-----------------|------|----------------|
| `fetch-chinatax-articles` | `providers/chinatax/processor.ts:103-251`(fetch+parse+hash+child files+summary) | `providers_dedicated/service.py:4-8`(仅加 `[provider:chinatax]` 前缀,不发请求) | **盲点B**(stub) | legacy `chinatax/processor.ts:103-251` + `services/action_registry.ts:60-65` ↔ py `providers_dedicated/service.py:4-8` |
| `getAgencyListings`(domain) | `providers/domain/*` | 无 | **盲点B**(缺失) | legacy `services/action_registry.ts:67-72` ↔ py 无 |
| `fetch-listings`(realestate) | `providers/realestate/*` | 无 | **盲点B**(缺失) | legacy `services/action_registry.ts:74-79` ↔ py 无 |
| provider registry / list_actions | `services/action_registry.ts:52-105` | 无(host 字符串 if 判断) | **盲点B**(缺失) | legacy `action_registry.ts:52-105` ↔ py `providers_dedicated/service.py:5` |

**dedicated provider action 真实现:0 / 3 个。**

### dispatcher 能力对照表

| legacy dispatcher 能力 | legacy 位置 | Python 落点 | 判定 |
|------------------------|-------------|-------------|------|
| 编排状态机 / findNextStep / dispatchStep | `flows/orchestrator.ts:44-211` | 无独立编排;ingestion 直接建单条 clean step,clean 服务建单条 rag step | **盲点B+断点D**(无多步工作流定义,硬接两步) |
| io_payload 渲染(声明式 I/O slot) | `services/mapper.ts:181-252` + `io_renderer.ts` | 无(直接读 source/artifact) | **盲点B**(缺失,本地化为直接 DB 读) |
| input_payload 模板解析(`{file.payload...}`) | `services/mapper.ts:51-168` | 无 | **盲点B**(缺失) |
| finalizer 标准交接(触发下游 RAG) | `flows/finalizer.ts:271-305` | `service.py:101-128`(建 rag step) | **等价**(语义对得上,DB step 替代 queue) |
| finalizer scatter 模式 / child files | `finalizer.ts:108,195-269` | 无 | **盲点B**(缺失,见 R9) |
| differ 差分(content_hash/meta_hash) | `services/differ.ts:86-221` | 无 | **盲点B**(缺失) |
| force/restart 模式(no_update→full_update) | `finalizer.ts:101,231-237` + `differ.ts:160-173` | 无(restart 走 CR-4 G-CR4-05,总从 clean 重跑) | **盲点B**(缺失) |
| SMCP 消息校验(validator/zod) | `core/validator.ts:35-79` | 无(无消息层,直接 DB) | **有意简化**(队列→DB claim,语义可接受) |
| 失败回滚(markWorkflowAsFailed) | `finalizer.ts:308-335` | worker `fail_claim`(CR-4) | **部分等价**(无 file_status→clean_failed 的领域态) |

### 逐项对齐结论表

| 编号 | 计划项 / 设计项 | 审查结论 | 说明 |
|------|------------------|----------|------|
| S1 | universal cleaner action 族(7 branch) | `missing` | 真实现 0,仅正则降级骨架(R1) |
| S2 | dedicated provider action 族(3 provider) | `missing` | 硬编码 chinatax 字符串前缀,不发请求(R2) |
| S3 | action registry / list_actions | `missing` | 无 registry、无 action_branch 写入(R4) |
| S4 | clean planner 选执行器 | `partial` | 仅 `provider or universal` if/else(R4) |
| S5 | 产物落 ObjectStore + artifact 元数据 | `partial` | artifact 有;但正文内联 sqlite_ref 而非 ObjectStore(R5) |
| S6 | finalizer 创建下游 rag step | `done` | 标准交接成立,stage 命名匹配(R6) |
| S7 | scatter / child files / differ | `missing` | 全缺(R9) |
| S8 | 执行器/claim 职责分离(单一事务边界) | `missing` | 执行器自提交 succeeded + 无幂等键(R3) |
| S9 | clean step 可观测(workflow_events,C4) | `missing` | clean 路径零 event(R7) |
| S10 | 错误分类 / step_attempts(C2) | `partial` | 有 fail_claim,无分类(R8) |

### 3.1 对齐结论

- **done**: `1`(S6)
- **partial**: `3`(S4 / S5 / S10)
- **missing**: `6`(S1 / S2 / S3 / S7 / S8 / S9)
- **stale**: `0`
- **out-of-scope-by-design**: `0`

> 这更像"**用 30 行桩把 clean 阶段占位填上、让 ingestion→clean→rag 的 step 链能流过**",而非 clean 流水线 completed。真实 clean 能力(抓取/渲染/PDF/LLM/scatter/differ/registry)系统性缺失,且承接了内核侧的自提交竞态缺陷。

### 3.2 stub / 真实现标定表(必交)

| 包 | 公开符号 | 标定 | 依据 |
|----|----------|------|------|
| `workflow_clean` | `process_clean_step(conn, step_id, object_store)` | **部分** | 真实建 artifact + 下游 step,链路通;但自提交+无幂等键(R3)、无 registry(R4)、无 scatter(R9)、产物存储漂移(R5)、不落 event(R7)。`service.py:67-129` |
| `workflow_clean` | `_load_raw_payload`(内部) | **部分** | file/static/url/api 四分支真实读取;url 用 urlopen 无 UA/重试,失败回退把 URL 当正文(脆弱)。`service.py:14-64` |
| `cleaners_universal` | `clean_payload(source_kind, payload)` | **stub** | 仅 `extract_text` 或 `strip`,无任何 action 分支。`service.py:6-9` |
| `providers_dedicated` | `maybe_clean_with_provider(canonical_uri, payload)` | **stub** | 硬编码 chinatax host 单分支 + 字符串前缀,不发请求。`service.py:4-8` |
| `browser_runtime` | `extract_text(payload)` | **stub** | 3 条正则去标签,无浏览器、无渲染、无 fetch。`extract.py:6-12` |
| `cleaners_universal` | (action registry / list_actions) | **缺失** | legacy 有,Python 无符号 |
| `providers_dedicated` | (provider registry / domain/realestate handler) | **缺失** | legacy 有,Python 无符号 |
| `workflow_clean` | (scatter / differ / finalizer 多步编排) | **缺失** | legacy `finalizer.ts`/`differ.ts` 有,Python 无符号 |

**量化盲点**:legacy clean 能力 ≈ 3.4k(universal)+ 3.7k(dedicated)+ 4.5k(dispatcher)≈ **10.6k 行**;Python 侧 in-scope 实现 = `workflow_clean` 129 + `cleaners_universal` 9 + `providers_dedicated` 9 + `browser_runtime` 13 ≈ **160 行**(其中真实 clean 算法 ≈ 31 行)。action 真实现:**universal 0/7、dedicated 0/3**;dispatcher 能力真实现 ≈ 1 项(标准交接)。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | C1 事务边界(执行器内 commit) | `违反` | `service.py:129` 执行器内 `conn.commit()` 自行提交,与 worker `succeed_claim` 双重置终态(R3),非单一事务边界。 |
| O2 | C2 异常处理 | `部分违反` | worker 有 `except Exception`→fail_claim(未静默吞),但无错误分类(R8),clean 服务自身不捕获不分类。 |
| O3 | C3 跨库一致性 | `遵守` | clean 仅写 core.db(artifacts/steps/runs),不碰 vec.db,无跨库操作;一致性问题在下游 rag(CR-7)。 |
| O4 | C4 可观测性(workflow_events) | `违反` | clean 路径零 event(R7),违反"所有 step 必须可观测"硬约束。 |
| O5 | C5 适配层纪律 | `部分违反` | clean 主路径不写 ObjectStore(规避了直接碰文件),但正文内联 core.db sqlite_ref(R5)偏离对象存储分层意图;url 分支用裸 `urlopen` 而非统一 HTTP 适配(轻度)。 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**:`changes-requested`(实质接近 blocked)
- **是否允许关闭本轮 review**:`no`
- **关闭前必须完成的 blocker**:
  1. **R3**:移除执行器自提交,把 step 终态/提交交回 `succeed_claim`(单一事务边界);下游 rag step 用确定性 step_key、artifact 加业务幂等键,使重放安全(联动 CR-4 G-CR4-03)。
  2. **R1**:universal cleaner 至少实现 htmlCrawl(真 fetch + 健壮抽取)与 geminiUnderstanding(PDF),其余 action 在 SSOT 显式声明降级与本地化替代;否则 clean 阶段对 url/SPA/PDF 源产出垃圾文本污染全链路。
  3. **R2**:dedicated provider 引入 registry + 至少 chinatax 真 ETL,或在设计 doc 显式裁掉专用 API 源;当前硬编码字符串前缀等于无能力。
  4. **R4**:引入 action_branch + registry 分派(创建侧写入、执行侧据此选 handler),恢复 action 选择与 list_actions 能力发现。
- **可以后续跟进的 non-blocking follow-up**:
  1. R5 cleaned_text 落 ObjectStore(配合 CR-3 R1/R6 路径校验与原子写)。
  2. R9 scatter / child files / differ(随 R2 落地后升级为 blocker)。
  3. R7 clean step 补 workflow_events;R8 错误分类 + retryable。
  4. R6 统一 stage 前缀约定(移交 CR-8 与 rag 侧一并核)。
- **建议的二次审查方式**:`same reviewer rereview`(R1/R2/R4 涉及大量新增能力,需重核 parity 矩阵与幂等键修法)
- **实现者回应入口**:`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应,不要改写 §0–§5。`

> 本轮 review 不收口,等待实现者按 §6 响应并再次更新代码。clean 流水线当前是"step 链能流过的占位实现",真实 clean 能力(legacy ~10.6k 行)迁移量近乎为零,且承接内核自提交竞态缺陷,不应标记为 completed。
