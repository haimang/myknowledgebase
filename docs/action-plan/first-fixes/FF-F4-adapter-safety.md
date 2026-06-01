# Nano-Agent 行动计划模板

> 服务业务簇: `first-fixes · F4 适配层安全与数据完整性`
> 计划对象: `FF-F4 · ObjectStore 路径安全 + VectorStore rowid 不变量 + purge 对象清退`
> 类型: `modify`
> 作者: `Opus 4.8`
> 时间: `2026-05-31`
> 文件位置: `packages/storage_objects/src/storage_objects/filesystem_store.py` / `packages/vector_sqlite_vec/src/vector_sqlite_vec/store.py` / `packages/workflow_core/src/workflow_core/purge.py` / `packages/ingestion/src/ingestion/service.py`
> 上游前序 / closure:
> - `与 F3（内核恢复与一次性语义）并行执行；不依赖 F3 产物，但 F4-05 purge 接线与 F3 的 purge 重入修复（G-CR3-12，归 F3/§3.2）位于同文件，需协调改动窗口`
> 下游交接:
> - `FF-F5-vector-authenticity.md（F5 依赖本 AP 修复的 rowid 一一对应不变量；真实 embedding 向量化 upsert 必须站在 F4-03 的复用 rowid 语义之上，否则 replay/重跑会放大孤儿）`
> 关联设计 / 调研文档:
> - `docs/design/first-fixes/initial-planning-by-opus.md`（§6.4 F4 台账 / §4 红线第 4 条适配层边界 / §5 DAG / §8 capstone H/J 步 / §8 DoD）
> - `docs/eval/first-code-review-plan/part-cr-3.md`（R1/R3/R4/R5/R9/R6/R11/S5）、`part-cr-5.md`（R2 路径遍历源头）
> 冻结决策来源:
> - `docs/design/first-fixes/owner-gated-qna.md`（只读引用；本 action-plan 不填写 Q/A —— 仅引 [Q7] 先红后绿铁律）
> grounding 来源:
> - `eval-reference-anchor: docs/eval/first-code-review-plan/part-cr-3.md（R1~R11，含主审实测）+ part-cr-5.md（R2）`；§7 内置锚区据此摘录
> 关联 reference-anchor:
> - `见 §7 内置锚区（摘录自 part-cr-3 / part-cr-5；完整借鉴台账见真源 §7.3 指针）`
> 文档状态: `draft`

---

## 0. 执行背景与目标

> 用一到三段话说明：为什么现在要执行这份计划、它从哪些 frozen design / QNA / closure 继承输入、它要把哪些设计结论落成可交付物。
>
> **纪律**：如果仍有 owner / architect 需要回答的问题，不应在 action-plan 中开 Q/A；应回到 design / qna register 完成冻结。本文件只消费已冻结结论。

CR-3 是八簇审查中迄今最严重的一簇（part-cr-3.md §0）：对象存储存在**可被认证用户经 HTTP `filename` 触达的真实路径遍历漏洞**（主审实测 `../escaped.txt` 逃逸成功、绝对路径丢弃 root），VectorStore 的 rowid 分配在两条生产常见路径下破坏数据/审计完整性（孤儿 rowid 累积 + 软删后重号 `INSERT OR REPLACE` 静默删除审计记录），purge 流程从不接触对象存储导致被清退文档的正文永久残留磁盘（合规缺陷）。这些都是 critical/high blocker，且适配层本应是安全/能力边界（C5 纪律：调用方确实经适配层，但适配层本身未兑现其承诺的边界，part-cr-3 §4 C5）。

本 AP 是 final plan（`initial-planning-by-opus.md`）§6.4 F4 簇的 1:1 派生（§10.A 派生图：`FF-F4-adapter-safety.md`，台账区间 F4-01..07），消费 §4 红线第 4 条「适配层边界强制：ObjectStore/VectorStore 是安全边界，object_key 规范化、rowid 一一对应在适配层内强制，不依赖调用方自律」。F4 与 F3 并行（§5 DAG：适配层 vs 内核，不同 substrate），是 F5 的前序（F5 真实向量化 upsert 依赖 rowid 不变量）。本 AP 把 CR-3 R1/R3/R4/R5 四个 blocker + 就近捆绑 R6/R9/R11 落成可交付物，并以 [Q7] 先红后绿铁律为每项的退出证据。

- **服务业务簇**：`first-fixes · F4 适配层安全与数据完整性`
- **计划对象**：`ObjectStore 路径边界校验 + ingestion basename 收口 + VectorStore rowid 单调不复用 + 软/硬删统一 + ObjectStore.delete + purge 接线`
- **本次计划解决的问题**：
  - `路径遍历漏洞（R1/G-CR3-01 + R2/G-CR5-02）：FileSystemObjectStore 对 object_key 零校验，HTTP filename 直拼 object_key，认证用户可跨 team 越权 + 任意文件读写`
  - `rowid 不变量破坏（R3/G-CR3-03 孤儿累积 + R4/G-CR3-04 重号静默删除审计记录）：违反 vec.sql:56-57「embedding_rowid 一一对应」硬约束`
  - `软/硬删不一致（R9/G-CR3-09）+ purge 不清对象（R5/G-CR3-05 合规清退）+ 非原子写（R6/G-CR3-06）+ get_text 错误处理（R11/G-CR3-11）`
- **本次计划的直接产出**：
  - `filesystem_store.py：object_key 边界校验（拒绝绝对路径/含 .. 段，resolve 后断言 is_relative_to(root)）+ delete + 原子写 + get_text 错误处理`
  - `store.py：rowid 单调不复用（独立序列或基于 vector_records 含软删 MAX）+ upsert 复用现有 rowid + 软/硬删统一`
  - `ingestion/service.py：filename basename 收口（纵深防御）；purge.py：接 object_store 删对象`
  - `先红后绿测试：路径遍历拒绝（..//绝对路径攻击向量）+ rowid 不变量（重复 upsert 0 孤儿 / 软删后新增不丢审计）`
- **本计划不重新讨论的设计结论**：
  - `全 phase 先红后绿铁律（每 blocker 修复以「当前 HEAD FAIL、修复后 PASS」回归为退出证据；安全项测试含攻击向量用例）`（来源：`[Q7]`）
  - `vec0 本轮 degraded（暴力 cosine，真实 vec0 移出本轮）`—— 本 AP 在退化的 TEXT 表 + chunk_embedding_index 上修 rowid 不变量，不接真实 vec0（来源：`[Q1]`，归 F5）

---

## 1. 执行综述

### 1.1 总体执行方式

本 AP 采用 **「先封安全边界 → 再修数据完整性 → 后接合规清退与就近捆绑」** 的分层推进：Phase 1 先封住可被 HTTP 触达的路径遍历（双层防御：store 最终防线 + ingestion 入口纵深防御），Phase 2 修 VectorStore rowid 不变量这一最承重的数据/审计完整性项，Phase 3 补 ObjectStore.delete + purge 接线（合规清退）并就近捆绑原子写/错误处理。每个 Phase 的退出判据是一条「修复前红、修复后绿」的有意义测试（[Q7]），安全项与 rowid 不变量项的红测在当前 HEAD 已由 part-cr-3 主审实测复现（必须红）。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | `路径遍历封堵（安全边界）` | `S` | `store object_key 边界校验 + ingestion filename basename 收口（双层纵深防御）` | `-` |
| Phase 2 | `VectorStore rowid 不变量与删除一致性` | `M` | `rowid 单调不复用 + upsert 复用现有 rowid + 软/硬删统一，消除孤儿累积与重号静默删除` | `-`（可与 Phase 1 并行） |
| Phase 3 | `对象清退与就近捆绑` | `S` | `ObjectStore.delete + purge 接线删对象 + 原子写 + get_text 错误处理` | `Phase 1（delete 复用 Phase 1 的 key 边界校验）` |

> 说明：上表 `规模` 是每个 Phase 的**描述性提示**（帮助阅读，工作量小则该 Phase 自然简短），**不是开工前的体量判定闸，也不改变本模板任何段落的取舍**。本模板是单一模板，不分 flavor、不分档。

### 1.3 Phase 说明

1. **Phase 1 — `路径遍历封堵（安全边界）`**
   - **核心目标**：`封住 R1/R2 路径遍历漏洞——store 内对 object_key 做规范化 + 边界断言（最终防线），ingestion 对 filename 做 basename 收口（入口纵深防御）`
   - **为什么先做**：`这是唯一的 critical 安全漏洞且可被认证用户经 HTTP 直接触达（part-cr-3 §0 第 1 点），优先级最高；后续 F4-05 delete 也复用本 Phase 的 key 边界校验`
2. **Phase 2 — `VectorStore rowid 不变量与删除一致性`**
   - **核心目标**：`使 chunk_embedding_index.rowid ↔ vector_records.embedding_rowid 一一对应不变量成立、rowid 不复用、不静默删除软删审计记录`
   - **为什么放在这里**：`F4-03 是本 AP 净新高风险最承重项（数据/审计完整性核心），与 Phase 1 无依赖可并行；F5 真实向量化依赖此修复，故必须在本 AP 内完成`
3. **Phase 3 — `对象清退与就近捆绑`**
   - **核心目标**：`store 增 delete（复用 Phase 1 边界校验）+ purge 接 object_store 删对象（合规清退）；就近捆绑 put_text 原子写、get_text 错误处理`
   - **为什么放在这里**：`delete 必须站在 Phase 1 的 key 边界校验之上（删除路径同样是信任边界，不可绕过校验）；原子写/错误处理是同文件就近修复，一并收口`

### 1.4 执行策略说明

> **纪律**：本节写执行策略，**不重述 §6 已引用的冻结决策的理由**（避免与 design/qna 重复，只写"怎么执行"，不写"为什么这么设计"）。

- **执行顺序原则**：`先安全（Phase 1）后完整性（Phase 2）再清退（Phase 3）；Phase 1↔2 无依赖可并行，Phase 3 的 delete 依赖 Phase 1 的 key 校验函数`
- **风险控制原则**：`F4-03（rowid）改动 store 写路径核心，先写红测复现孤儿 [1,2]/b survived?=0，小步改 _next_embedding_rowid + upsert + delete 三处后再跑回归；安全项以攻击向量用例验证逃逸被封堵`
- **测试推进原则**：`单元测试（store/filesystem 路径遍历拒绝 + rowid 不变量）随 phase 提交；集成测试（purge 删对象端到端）在 Phase 3 收口；capstone H/J 步在 F7 整合（短途→spike→mega，详见 §8 测试台账）`
- **文档同步原则**：`本 AP 不改 vec.sql schema（rowid 不变量在适配层 enforce）；purge 接线后同步 §3.2 R12 重入归属说明（归 F3）；closure 不在 F7 前标 ✅`
- **回滚 / 降级原则**：`安全项无降级（路径遍历必须封堵）；rowid 改动若与现存退化 TEXT 表数据冲突，当前为 P 阶段无生产数据，可重建库；purge 删对象失败 fail-loud 不静默吞`

### 1.5 本次 action-plan 影响结构图

> 用树状结构快速展示：本计划会影响哪些模块、目录、运行链路、服务边界、测试层或文档资产。
>
> 这一节不是文件系统快照，而是**影响结构图**；推荐按业务链路或执行路径写。

```text
FF-F4 适配层安全与数据完整性
├── Phase 1: 路径遍历封堵（安全边界）
│   ├── packages/storage_objects/.../filesystem_store.py（put_text/get_text/exists 加 key 校验）
│   └── packages/ingestion/.../service.py（file_initiate/static_initiate filename basename 收口）
├── Phase 2: VectorStore rowid 不变量与删除一致性
│   ├── packages/vector_sqlite_vec/.../store.py（_next_embedding_rowid / upsert_chunk / delete_chunk）
│   └── chunk_embedding_index ↔ vector_records 一一对应不变量（适配层 enforce，不改 vec.sql）
└── Phase 3: 对象清退与就近捆绑
    ├── packages/storage_objects/.../filesystem_store.py（新增 delete + 原子写 + get_text 错误处理）
    └── packages/workflow_core/.../purge.py（接收 object_store，查 object_key 逐个删）
```

---

## 2. In-Scope / Out-of-Scope

> 把 action-plan 的执行边界集中写在这里。设计上的边界应来自 design/QNA；本节只说明本轮执行做什么、不做什么、何时重评。

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** `F4-01 store object_key 边界校验（拒绝绝对路径/含 .. 段；resolved=(root/key).resolve() 断言 is_relative_to(root) 否则 raise）`
- **[S2]** `F4-02 ingestion filename basename 收口（纵深防御，file_initiate/static_initiate）`
- **[S3]** `F4-03 VectorStore rowid 单调不复用 + upsert 复用现有 rowid（消除 R3 孤儿累积 + R4 重号静默删除审计）`
- **[S4]** `F4-04 软/硬删统一策略，保留审计可追溯（R9）`
- **[S5]** `F4-05 ObjectStore.delete + purge 接线删对象（R5 合规清退）`
- **[S6]** `F4-06 就近捆绑：put_text 原子写 temp+os.replace（R6）、get_text 错误处理（R11）`
- **[S7]** `F4-07 先红后绿测试：路径遍历拒绝（..//绝对路径攻击向量）+ rowid 不变量（重复 upsert 0 孤儿 / 软删后新增不丢审计）`

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** `真实 vec0 / sqlite-vec 加载（R2/G-CR3-02）—— 本轮 degraded（[Q1]），归 F5；本 AP 在退化 TEXT 表上修 rowid`
- **[O2]** `search 增 namespace/embedding_model 过滤（R10/G-CR3-10）—— 归 F5（F5-03）`
- **[O3]** `embedding_dimension 写实际长度 + cosine 维度不等 raise（R7/S5）—— 与真实 embedding 维度强相关，归 F5`
- **[O4]** `二进制 put_bytes/get_bytes（R8）—— [Q3] 增量本轮仅 file 文本 + url HTML，PDF degraded，归 F6；本 AP 仅文档化文本-only`
- **[O5]** `purge 中途崩溃 processing 重入（R12）、vectorize 崩溃孤儿补偿（R13）—— 一致性/重入归 F3（与 reap/lease 同主题）`

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| `路径遍历封堵（R1/R2）` | `in-scope` | `唯一 critical 安全漏洞，HTTP 可达，适配层边界红线` | `-` |
| `rowid 不变量（R3/R4）` | `in-scope` | `数据/审计完整性 critical，F5 前序` | `-` |
| `真实 vec0 加载（R2/G-CR3-02）` | `out-of-scope` | `[Q1] 本轮 degraded，归 F5` | `生产化阶段接真实 vec0` |
| `search namespace/model 过滤（R10）` | `out-of-scope` | `检索语义层，归 F5-03` | `F5 执行窗口` |
| `embedding_dimension 真校验 + cosine raise（R7）` | `out-of-scope` | `与真实 embedding 维度耦合，归 F5` | `F5 接本地 1536 维模型时` |
| `purge processing 重入（R12）` | `defer / depends-on-design` | `重入/lease 一致性同 F3 主题（reap）` | `F3 内核恢复执行窗口` |
| `二进制能力（R8）` | `out-of-scope` | `[Q3] 本轮文本 + HTML 增量，PDF degraded` | `F6 PDF source 解禁时` |

---

## 3. 业务工作总表

> 总索引；后面 §4 会按 Phase 展开。编号建议 `P1-01 / P1-02 / P2-01`，便于 review、handoff 与 closure 引用。
>
> **硬地板（每个工作项必须三件齐全 —— 不可约三元组）**：
> 1. **`涉及文件（file:line 级）`** —— 落在哪段既有代码 / 新建哪个文件（与 §7 锚区对应）。
> 2. **`收口目标`** —— 一句话、可验证的"做完长什么样"。
> 3. **`测试映射`** —— 指向 §8 测试台账的 `Test-ID`（证明此项做到了）。
>
> 缺任一即该项**欠规格**。**安全 / 信任边界类**工作项，其 `涉及文件` 须含或指向威胁模型落点（§7.3），不得留空。
>
> **第 4 件（条件 · 与净新度/风险成正比）`分解步骤`**：**净新 / 高风险**工作项，其 §4 `工作内容` 必须拆成有序子步（a/b/c）+ 边界情况，§5 `具体功能预期` ≥5 条；**扩展既有 / ♻️复用 / 沿用** 项一句话或枚举即可（不注水）。

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| F4-01 | Phase 1 | `ObjectStore object_key 边界校验（安全边界，威胁模型落点见 §7.3）` | `update` | `filesystem_store.py:11-14（put_text）, :16-17（get_text）, :19-20（exists）` | `绝对路径/含 .. 段 key 被 raise 拒绝；resolved 断言 is_relative_to(root)；逃逸用例全部被封堵` | `FF-F4-T01` | `medium`（安全） |
| F4-02 | Phase 1 | `ingestion filename basename 收口（纵深防御源头，威胁模型源头链见 §7.3）` | `update` | `ingestion/service.py:17（object_key 拼接）, :15/:30（file_initiate/static_initiate 入参 filename）` | `filename 经 os.path.basename + 拒绝空/含 / \\ .. 后才进 object_key；HTTP 注入入口收口` | `FF-F4-T02` | `low` |
| F4-03 | Phase 2 | `VectorStore rowid 单调不复用 + upsert 复用现有 rowid` | `update` | `store.py:126-130（_next_embedding_rowid）, :32（rowid 分配）, :39-67（upsert 双写）` | `重复 upsert 同 chunk_id 复用现有 rowid → 0 孤儿；rowid 基于含软删行单调不复用 → 软删后新增不重号不静默删审计` | `FF-F4-T03, FF-F4-T04` | `high`（数据/审计完整性核心） |
| F4-04 | Phase 2 | `软/硬删统一策略，保留审计可追溯` | `update` | `store.py:69-89（delete_chunk）, :109-124（delete_chunks）` | `delete_chunk 软硬删一致（不再硬删 index 留空洞）；软删 vector_records 的「可追溯」不被抹除` | `FF-F4-T04` | `medium` |
| F4-05 | Phase 3 | `ObjectStore.delete + purge 接线删对象（合规清退）` | `add` | `filesystem_store.py（新增 delete，复用 F4-01 校验）；purge.py:29（签名）, :90-91（vec 删除处接 object 删）` | `store.delete(key) 删对象且经边界校验；purge 查 uploads/static_files object_key 逐个删，被清退文档正文不残留` | `FF-F4-T05` | `low` |
| F4-06 | Phase 3 | `put_text 原子写 temp+os.replace + get_text 错误处理` | `update` | `filesystem_store.py:11-14（put_text）, :16-17（get_text）` | `put_text 写 temp 后 os.replace 原子 rename；get_text 缺失 key 经 try/except 分类处理不抛裸异常` | `FF-F4-T06` | `low` |
| F4-07 | Phase 1+2 | `先红后绿：路径遍历拒绝 + rowid 不变量回归测试` | `add` | `tests/unit/test_filesystem_store_paths.py（新）、tests/unit/test_vector_store_rowid.py（新）` | `当前 HEAD 红（逃逸成功/孤儿 [1,2]/b survived?=0），修复后绿；含攻击向量用例` | `FF-F4-T01, FF-F4-T03, FF-F4-T04` | `low` |

---

## 4. Phase 业务表格

> 每个 Phase 一张表，完整列出工作项、目标、涉及文件与对应测试台账项。`测试映射` 列指向 §8 的 `Test-ID`。
>
> **`工作内容` 是承重列，分解度与净新度/风险成正比（硬地板第 4 件）**。

### 4.1 Phase 1 — `路径遍历封堵（安全边界）`

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| F4-01 | `ObjectStore object_key 边界校验` | `a) 抽出 _resolve_safe(key) 私有方法：先快速拒绝——空 key、绝对路径（os.path.isabs 或 Path(key).is_absolute()）、含 .. 段（key.split('/') 任一段 == '..'）即 raise（如 ValueError("unsafe object_key")）；b) 计算 resolved = (self.root / key).resolve()，断言 resolved.is_relative_to(self.root.resolve())，否则 raise（捕获 .. 经 resolve 后逃逸 + 符号链接绕过）；c) put_text/get_text/exists 三处统一改为先 _resolve_safe(key) 得安全 path 再操作（消除 :12/:17/:20 三处裸 self.root / object_key）；d) 边界情况：key 含合法子目录（raw/team/upload/file.txt）放行；key 含 ./ 经 resolve 归一后仍在 root 内放行；Windows 反斜杠路径段一并拒绝（防 \\..\\ 绕过）` | `filesystem_store.py:11-14, :16-17, :19-20`（part-cr-3 R1 / §3.2 标定「真实现含 critical 安全缺陷」） | `所有逃逸 key（../escaped.txt、../../etc/passwd、/abs/path、a/../../x）被 raise；合法 key 正常读写` | `FF-F4-T01` | `攻击向量用例全部被拒（逃逸 0 成功）；合法 happy-path 不回归；§7.3 威胁模型落点封堵` |
| F4-02 | `ingestion filename basename 收口` | `a) file_initiate 中在拼接前 filename = os.path.basename(filename)（剥离任何路径分量）；b) 拒绝清洗后为空 / 仍含 / \\ .. 的值（raise ValueError）；c) static_initiate 经 file_initiate 复用同收口；d) 与 F4-01 协同——控制面为第一道、store 为最终防线，双层纵深防御（part-cr-5 R2 修法）` | `ingestion/service.py:17`（object_key 拼接）、`:15`（file_initiate）、`:30`（static_initiate）；HTTP 源头 `apps/api/.../routes/ingestion.py:18 FileInitiateBody.filename`（零校验 str） | `POST /ingestion/file/initiate {"filename":"../../../etc/passwd"} 不再污染 object_key；basename 后只剩文件名` | `FF-F4-T02` | `filename 含 ../ 或绝对路径被入口收口；object_key 始终为 raw/team/upload/<basename>` |

### 4.2 Phase 2 — `VectorStore rowid 不变量与删除一致性`

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| F4-03 | `rowid 单调不复用 + upsert 复用现有 rowid` | `a) rowid 分配策略：_next_embedding_rowid 不再用 chunk_embedding_index 的 MAX(rowid)+1（会被硬删导致重号，R4 根因）；改为单调不复用——基于 vector_records 含软删行的 MAX(embedding_rowid)+1，或独立序列表（vec_rowid_seq）原子自增，确保已分配 rowid 永不回收；b) upsert 同 chunk_id 复用：upsert_chunk 先 SELECT vector_records.embedding_rowid WHERE chunk_id=?（含软删行），命中则复用该 rowid（不分配新值），未命中才 _next_embedding_rowid（消除 R3 孤儿）；c) index 双写改为先 DELETE chunk_embedding_index WHERE rowid=旧值 再 INSERT（或确认复用 rowid 的 INSERT OR REPLACE 命中同 rowid 覆盖），杜绝孤儿 [1,2] 累积；d) 边界——首次 upsert（无现有行）正常分配；重复 upsert ×3 同 chunk_id → rowid 恒定、孤儿 0；软删 b 后 upsert 新 chunk c → c 拿到不复用的新 rowid，b 的软删记录（deleted_at + embedding_rowid）不被 INSERT OR REPLACE 冲突抹除（消除 R4「b survived?=0」）；e) 与 F4-04 协同——若 delete_chunk 改为不硬删 index，则复用路径不再遇空洞` | `store.py:126-130`（_next_embedding_rowid，R4 根因 MAX+1 基于会被硬删的 index）、`:32`（rowid 分配三元）、`:39-67`（vector_records + chunk_embedding_index 双写 INSERT OR REPLACE）；不变量真源 `vec.sql:56-57` 注释「一一对应」 | `重复 upsert 0 孤儿；软删后新增不重号、不静默删审计；chunk_embedding_index.rowid ↔ vector_records.embedding_rowid 一一对应恒成立` | `FF-F4-T03（孤儿）, FF-F4-T04（重号/审计）` | `主审实测的 [1,2,3]→孤儿[1,2]、b survived?=0 两条红测转绿；一一对应不变量断言通过` |
| F4-04 | `软/硬删统一策略，保留审计可追溯` | `a) 统一 delete_chunk 策略：当前 vector_records 软删（置 deleted_at）但 chunk_embedding_index 硬删（DELETE，R9 不一致根因）；改为软硬删一致——保留 index 行（与 vr 软删对齐）或两者皆按一致语义处理，使软删 vr 的「可追溯」不被硬删 index 抵消；b) 与 F4-03 rowid 不复用配合：删除不再制造可被重号占用的空洞；c) 边界——delete_chunks 批量软删幂等（已软删跳过，沿用 :120 现有幂等）；purge 路径（先软删后由 F4-05 删对象）审计链完整` | `store.py:69-89`（delete_chunk 软/硬删混用）、`:109-124`（delete_chunks 批量） | `软删后 index 与 vr 状态一致；审计记录（deleted_at 软删行）不被后续写入抹除` | `FF-F4-T04` | `软删 b 后 b 的 vector_records 软删行可追溯；与 F4-03 重号测试同绿` |

### 4.3 Phase 3 — `对象清退与就近捆绑`

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| F4-05 | `ObjectStore.delete + purge 接线删对象` | `a) filesystem_store 增 delete(object_key)：经 F4-01 的 _resolve_safe 校验后 unlink，缺失对象幂等不报错（missing_ok）；b) purge.py process_purge_requests 签名/调用接收 object_store；在 vec delete_chunks（:90-91）同处，查目标 document 的 uploads.object_key 与 static_files.object_key，逐个 object_store.delete，使被 purge 文档的 raw 上传 + chunk 正文不残留磁盘（part-cr-3 R5 修法）；c) 边界——object_key 为 None/缺失对象跳过；删对象失败 fail-loud 记 audit 不静默吞` | `filesystem_store.py`（新增 delete，复用 F4-01 校验）；`purge.py:29`（process_purge_requests 签名）、`:90-91`（vec 删除处接 object 删） | `purge 后 raw/team/upload/file 与 chunk 对象被删；合规清退完整` | `FF-F4-T05` | `purge 端到端断言对象不存在（object_store.exists False）；delete 经边界校验` |
| F4-06 | `put_text 原子写 + get_text 错误处理` | `a) put_text 写 temp 文件后 os.replace(temp, target) 原子 rename（消除 R6 半文件）；b) get_text 缺失 key 改 try/except FileNotFoundError 分类处理（取代裸抛 / search 侧 exists→get 的 TOCTOU），返回明确信号或 raise 受控异常供调用方分类（part-cr-3 R11）` | `filesystem_store.py:11-14`（put_text 非原子 write_text）、`:16-17`（get_text 裸 read_text） | `写中途崩溃不留半文件；缺失对象不抛裸 FileNotFoundError` | `FF-F4-T06` | `原子写单测（temp+replace）；缺失 key 受控异常单测` |

---

## 5. Phase 详情

> 按 Phase 展开详细执行说明。**测试不在此展开**——每项指向 §8 测试台账的 `Test-ID`。
>
> **`具体功能预期` 的展开度与净新度/风险成正比（硬地板第 4 件）**：净新 / 高风险 Phase ≥5 条，含**边界与失败/降级路径**。

### 5.1 Phase 1 — `路径遍历封堵（安全边界）`

- **Phase 目标**：`封住 R1（store 零校验）+ R2（ingestion filename 直拼）路径遍历，双层纵深防御使认证用户无法经 HTTP filename 越权或任意文件读写`
- **本 Phase 对应编号**：`F4-01` / `F4-02`
- **本 Phase 新增文件**：`tests/unit/test_filesystem_store_paths.py`（F4-07 红测）
- **本 Phase 修改文件**：`filesystem_store.py:11-20`（put_text/get_text/exists 加 _resolve_safe）、`ingestion/service.py:15-37`（file_initiate/static_initiate basename 收口）
- **本 Phase 删除文件**：`无`
- **具体功能预期**：
  1. `_resolve_safe(key) 拒绝绝对路径（is_absolute）—— 主审实测「绝对路径 key 因 Path(root)/'/abs' 语义直接丢弃 root」必须被拒`
  2. `_resolve_safe(key) 拒绝含 .. 段 —— 主审实测「put_text('../escaped.txt') 写到 root 之外」必须被拒`
  3. `resolved.is_relative_to(self.root.resolve()) 断言失败即 raise —— 兜底捕获 resolve 后逃逸与符号链接绕过`
  4. `put_text/get_text/exists 三处统一走 _resolve_safe，消除三处裸 self.root / object_key（:12/:17/:20）`
  5. `ingestion file_initiate 对 filename 做 os.path.basename + 拒绝空/含分隔符，static_initiate 复用，object_key 始终为 raw/team/upload/<basename>`
  6. `边界/失败路径：合法子目录 key（raw/.../file.txt）与 ./ 归一后仍在 root 内的放行；Windows 反斜杠段一并拒绝；清洗后空 filename raise`
- **对应测试台账项**：`FF-F4-T01`（store 逃逸拒绝）/ `FF-F4-T02`（ingestion 源头收口）（详见 §8）
- **收口标准**：`攻击向量用例（../、../../etc/passwd、/abs、a/../../x）逃逸 0 成功；合法 happy-path 不回归；HTTP 注入入口收口`
- **本 Phase 风险提醒**：`is_relative_to 需 Python 3.9+；若环境更低需改用 os.path.commonpath 比对——执行前确认运行时版本`

### 5.2 Phase 2 — `VectorStore rowid 不变量与删除一致性`

- **Phase 目标**：`使 chunk_embedding_index.rowid ↔ vector_records.embedding_rowid 一一对应不变量在适配层成立，rowid 不复用、不静默删除软删审计记录`
- **本 Phase 对应编号**：`F4-03`（净新高风险）/ `F4-04`
- **本 Phase 新增文件**：`tests/unit/test_vector_store_rowid.py`（F4-07 红测）
- **本 Phase 修改文件**：`store.py:126-130`（_next_embedding_rowid 改 rowid 来源）、`:32`（分配点）、`:39-67`（upsert 双写）、`:69-89`（delete_chunk 软硬删统一）、`:109-124`（delete_chunks）
- **本 Phase 删除文件**：`无`
- **具体功能预期**：
  1. `_next_embedding_rowid 不再用 chunk_embedding_index MAX(rowid)+1（R4 根因：index 被硬删致重号）；改基于 vector_records 含软删行 MAX(embedding_rowid)+1 或独立序列表，已分配 rowid 永不回收`
  2. `upsert_chunk 先 SELECT 现有 chunk_id 的 embedding_rowid（含软删行），命中复用、未命中才分配 —— 消除 R3 孤儿（重复 upsert 同 chunk_id rowid 恒定）`
  3. `index 双写：复用 rowid 时 DELETE 旧 index 行再 INSERT（或 INSERT OR REPLACE 命中同 rowid 覆盖），保证孤儿 0`
  4. `delete_chunk 软硬删统一（R9）：不再 vr 软删 + index 硬删混用，使软删 vr 的可追溯不被抹除，且不留可被重号占用的空洞`
  5. `边界/失败路径：首次 upsert 正常分配；upsert ×3 同 chunk_id → rowid 恒定、孤儿 0；软删 b 后 upsert 新 c → c 拿不复用新 rowid、b 软删记录不被 INSERT OR REPLACE 冲突抹除（消除「b survived?=0」）；delete_chunks 批量已软删幂等跳过`
  6. `一一对应不变量断言：任意操作序列后 chunk_embedding_index 的每个 rowid 在 vector_records 有对应 embedding_rowid（含/不含软删按统一策略），反之无孤儿`
- **对应测试台账项**：`FF-F4-T03`（重复 upsert 0 孤儿）/ `FF-F4-T04`（软删后新增不丢审计 + 软硬删一致）（详见 §8）
- **收口标准**：`主审实测的孤儿 [1,2] 与 b survived?=0 两条红测转绿；一一对应不变量断言通过；F5 可在此 rowid 语义上安全做真实向量化`
- **本 Phase 风险提醒**：`改 store 写路径核心，需逐操作序列回归；当前为退化 TEXT 表（[Q1] degraded），不变量在适配层 enforce 而非 vec0；P 阶段无生产数据，必要时重建库`

### 5.3 Phase 3 — `对象清退与就近捆绑`

- **Phase 目标**：`补 ObjectStore.delete + purge 接线删对象（R5 合规清退），就近捆绑原子写（R6）与 get_text 错误处理（R11）`
- **本 Phase 对应编号**：`F4-05` / `F4-06`
- **本 Phase 新增 / 修改 / 删除文件**：`filesystem_store.py（新增 delete + 改 put_text/get_text，复用 Phase 1 _resolve_safe）；purge.py:29,90-91（接收 object_store 并删对象）`（file:line）
- **具体功能预期**：
  1. `filesystem_store.delete(object_key) 经 _resolve_safe 校验后 unlink，缺失对象幂等（missing_ok）`
  2. `purge.process_purge_requests 接收 object_store，在 vec delete_chunks 同处查 uploads/static_files 的 object_key 逐个删`
  3. `put_text 写 temp + os.replace 原子 rename，崩溃不留半文件`
  4. `get_text 缺失 key try/except 分类处理，不抛裸 FileNotFoundError`
  5. `边界/失败路径：object_key None/缺失跳过；删对象失败 fail-loud 记 audit 不静默吞；delete 同样经边界校验（删除路径亦信任边界）`
- **对应测试台账项**：`FF-F4-T05`（purge 删对象端到端）/ `FF-F4-T06`（原子写 + 错误处理）（详见 §8）
- **收口标准**：`purge 后被清退文档的 raw 上传与 chunk 对象 exists False；原子写与受控异常单测通过`
- **本 Phase 风险提醒**：`purge.py 同文件存在 F3/§3.2 的 R12 processing 重入修复，需协调改动窗口避免冲突`

---

## 6. 依赖的冻结设计决策（只读引用）

> 列出本 action-plan 依赖哪些 design / QNA / closure 结论。**不要在本节填写新 Q/A；只引 register 的 Q 编号。**

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| `[Q7] 全 phase 先红后绿铁律` | `owner-gated-qna.md Q7（FROZEN）` | `F4-07 每 blocker 修复以「当前 HEAD FAIL、修复后 PASS」回归为退出证据；安全项 + rowid 项的红测在 HEAD 已由 part-cr-3 主审实测复现，必须红；安全项测试含攻击向量用例（§8.5）` | `若放宽 test-first 则回退 design；本 AP 保持 draft` |
| `[Q1] vec0 本轮 degraded（暴力 cosine，真实 vec0 移出本轮）` | `owner-gated-qna.md Q1（FROZEN）` | `本 AP 在退化 TEXT 表 + chunk_embedding_index 上 enforce rowid 不变量，不接真实 vec0；vec0 加载归 F5` | `若 owner 改判本轮接 vec0，则 rowid 不变量改在 vec0 虚表层 enforce，本 AP 需重评` |

---

## 7. 内置 Reference-Anchor 锚区

> **本段固定植入每份 AP**（业主指令）。它把本计划工作项要落到的既有代码、要避开的陷阱、以及安全项的威胁模型**就地钉住**——实现时 0 跳转、grounding 0 泄漏。

### 7.1 锚表（本计划工作要落在哪些既有代码 / 新建点上）

> `处置` 用 README §4.4 **复用判定**图例：`✅ 复用`（直接改写/扩展既有）/ `♻️ 重 substrate`（在既有基底上重建）/ `🆕 净新`。

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| A-1 | `filesystem_store.py:11-14` | `put_text：path = self.root / object_key（零校验，主审实测 ../escaped.txt 逃逸）` | `F4-01 加 _resolve_safe 边界校验 / F4-06 改原子写` | `✅ 复用` | `威胁模型落点（写）；R1 critical 安全` |
| A-2 | `filesystem_store.py:16-17` | `get_text：(self.root / object_key).read_text（零校验 + 裸 FileNotFoundError）` | `F4-01 边界校验 / F4-06 错误处理` | `✅ 复用` | `威胁模型落点（读）；R1+R11` |
| A-3 | `filesystem_store.py:19-20` | `exists：(self.root / object_key).exists（零校验）` | `F4-01 边界校验` | `✅ 复用` | `R1；search 侧 TOCTOU 源` |
| A-4 | `filesystem_store.py（无 delete）` | `当前无 delete 接口（R5）` | `F4-05 新增 delete（复用 _resolve_safe）` | `🆕 净新` | `legacy r2.ts:194 deleteR2Object 对照` |
| A-5 | `ingestion/service.py:17` | `object_key = f"raw/{team_id}/{upload_id}/{filename}"（filename 原样拼接）` | `F4-02 basename 收口` | `✅ 复用` | `威胁模型源头链；R2 注入入口` |
| A-6 | `apps/api/.../routes/ingestion.py:18` | `FileInitiateBody.filename: str（HTTP body，零校验）` | `F4-02 源头读不改的参考点` | `读不改的参考点` | `攻击者完全可控字段；威胁模型攻击向量源` |
| A-7 | `store.py:126-130` | `_next_embedding_rowid：MAX(rowid)+1 基于会被硬删的 chunk_embedding_index（R4 根因）` | `F4-03 改 rowid 来源（单调不复用）` | `✅ 复用` | `重号静默删除审计的直接根因` |
| A-8 | `store.py:32,39-67` | `upsert_chunk：rowid 分配 + vector_records/chunk_embedding_index 双 INSERT OR REPLACE` | `F4-03 复用现有 rowid + index 改写` | `✅ 复用` | `主审实测孤儿 [1,2]` |
| A-9 | `store.py:69-89` | `delete_chunk：vr 软删 + index 硬删（R9 不一致）` | `F4-04 软硬删统一` | `✅ 复用` | `喂养 R3/R4` |
| A-10 | `purge.py:29,90-91` | `process_purge_requests：仅动 SQLite + VectorStore.delete_chunks，不碰 object_store（R5）` | `F4-05 接收 object_store 删对象` | `✅ 复用` | `合规清退接线点` |
| A-11 | `vec.sql:56-57` | `注释「chunk_embedding_index.rowid = vector_records.embedding_rowid 一一对应」硬约束` | `F4-03 不变量真源（读不改）` | `读不改的参考点` | `不变量断言依据` |
| A-12 | `tests/unit/test_filesystem_store_paths.py / test_vector_store_rowid.py` | `路径遍历 + rowid 不变量红测` | `F4-07 新建` | `🆕 净新` | `当前 tests/unit 为空（F7-04 提及）` |

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | `直接 self.root / object_key 不校验（put/get/exists/delete 任一处）` | `主审实测 ../escaped.txt 逃逸成功、绝对路径丢弃 root；store 是最后防线必须校验（part-cr-3 R1）` |
| ⛔2 | `MAX(rowid)+1 复用 rowid（基于会被硬删的 chunk_embedding_index）` | `R4 根因：软删 b（index rowid 2 硬删）后 upsert c → MAX(1)+1=2 重号 → INSERT OR REPLACE 静默删 b 审计行（b survived?=0，part-cr-3 R4）` |
| ⛔3 | `upsert 同 chunk_id 不复用现有 rowid（每次分配新 rowid）` | `R3 孤儿累积：同 chunk_id upsert ×3 → index rowids [1,2,3]、孤儿 [1,2]，违反 vec.sql:56-57（part-cr-3 R3）` |
| ⛔4 | `delete_chunk vr 软删 + index 硬删混用` | `R9 软硬删不一致，制造 R3 孤儿镜像 + R4 重号空洞；软删的可追溯被硬删抵消（part-cr-3 R9）` |
| ⛔5 | `仅依赖 store 或仅依赖 ingestion 单层防御` | `纵深防御：control-plane 第一道 + store 最终防线，缺任一则 G-CR3-01 可达（part-cr-5 R2 修法「控制面 basename 收口 + 存储层 basename 收口为最终防线」）` |
| ⛔6 | `退化路径/删对象失败静默吞` | `CR-3 假绿教训（R2 静默退化 = 假绿）；purge 删对象失败须 fail-loud` |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：`docs/eval/first-code-review-plan/part-cr-3.md（R1~R16，含主审 4 个 critical 亲测复现）+ part-cr-5.md（R2 路径遍历源头）` —— §7.1 是其与本 AP 工作项相关子集的摘录；完整 finding 台账（含严重度、legacy 对照、实测证据）见真源。
- **安全 / 信任边界类工作项的威胁模型锚**（F4-01 / F4-02，**不得留空**）：
  - **威胁模型落点（store 边界）**：`§7.1 锚 A-1/A-2/A-3（filesystem_store.py:11-20 put/get/exists 零校验）+ A-4（新增 delete 同为边界）`。
  - **威胁模型源头链**：`A-6（routes/ingestion.py:18 FileInitiateBody.filename，HTTP body 零校验，攻击者完全可控）→ A-5（ingestion/service.py:17 object_key = f"raw/{team_id}/{upload_id}/{filename}" 原样拼接）→ A-1（filesystem_store.put_text 直接 self.root / object_key 落盘）`。
  - **攻击向量**：`认证用户 POST /ingestion/file/initiate {"filename": "../../../../etc/passwd"}（或绝对路径 /abs/path）→ filename 未经 basename/normpath/拒绝 .. 注入 object_key → file_confirm 时 put_text 写到 object root 之外的进程可写路径（配置/SQLite db/代码），或经 ../ 跨 team UUID 前缀覆写/读取他队对象`。
  - **危害**：`① 跨 team 越权（打穿 legacy 基于 Team UUID 的 SaaS 隔离模型）；② 任意文件读/写（构成 RCE/数据泄露面）`（part-cr-3 R1「认证用户可达的任意文件读写 + 跨 team 越权」、part-cr-5 R2「确认该路径遍历真实可由 HTTP 触发，非理论风险」）。
  - **缓解（双层纵深防御）**：`第一道 = ingestion control-plane filename basename + 拒绝分隔符（F4-02）；最终防线 = store object_key 规范化 + is_relative_to(root) 断言（F4-01）`。
  - **威胁模型已在上游做过**：是（part-cr-3 R1 主审实测逃逸 + part-cr-5 R2 可达性证明），本 AP §7.3 指回真源，未在 AP 内新开威胁分析。

---

## 8. 测试台账

> **本段固定植入每份 AP**（业主指令）。**测试细节只在此写一次**（§4/§5 只引 Test-ID）。

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| `FF-F4-T01` | `路径遍历拒绝：put_text/get_text/exists/delete 对 ../escaped.txt、../../etc/passwd、/abs/path、a/../../x（攻击向量）全部 raise；合法 raw/team/upload/file.txt 放行` | `短途` | `unit` | `🆕 新增 tests/unit/test_filesystem_store_paths.py` | `F4-01 → 逃逸 0 成功、合法放行` | `commit {sha} + test_filesystem_store_paths PASS + {YYYY-MM-DD HH:MM UTC}` |
| `FF-F4-T02` | `ingestion filename 源头收口：file_initiate({"filename":"../../../etc/passwd"}) 后 object_key 仅含 basename（raw/team/upload/passwd），含分隔符/空 filename raise` | `短途` | `unit` | `🆕 新增 tests/unit/test_ingestion_filename.py` | `F4-02 → HTTP 注入入口收口` | `commit {sha} + test_ingestion_filename PASS + run-time` |
| `FF-F4-T03` | `rowid 不变量·孤儿：同 chunk_id upsert ×3 → chunk_embedding_index 无孤儿 rowid（修复前红：孤儿 [1,2]）` | `短途` | `unit` | `🆕 新增 tests/unit/test_vector_store_rowid.py` | `F4-03 → 重复 upsert 0 孤儿` | `commit {sha} + test_vector_store_rowid::test_upsert_no_orphan PASS + run-time` |
| `FF-F4-T04` | `rowid 不变量·重号/审计：upsert a,b → delete_chunk(b) 软删 → upsert 新 c → b 软删审计记录幸存（修复前红：b survived?=0）+ 软硬删一致` | `短途` | `unit` | `🆕 新增 tests/unit/test_vector_store_rowid.py` | `F4-03+F4-04 → 软删后新增不丢审计` | `commit {sha} + test_vector_store_rowid::test_soft_delete_audit_survives PASS + run-time` |
| `FF-F4-T05` | `purge 删对象端到端：ingestion 建 upload+confirm 写对象 → purge → object_store.exists(raw key) False（修复前红：对象残留）` | `spike` | `集成` | `🆕 新增 tests/integration/test_purge_object_delete.py` | `F4-05 → 合规清退完整` | `commit {sha} + test_purge_object_delete PASS + run-time` |
| `FF-F4-T06` | `原子写 + 错误处理：put_text 经 temp+os.replace（断言无残留 temp）；get_text 缺失 key 受控异常（非裸 FileNotFoundError）` | `短途` | `unit` | `🆕 新增 tests/unit/test_filesystem_store_io.py` | `F4-06 → 原子写 + 受控错误` | `commit {sha} + test_filesystem_store_io PASS + run-time` |

**列定义（填法约束）**：
- **类型**：`短途`（每 PR 快测）/ `spike`（阶段性 journey 验证）/ `mega` / `soak`。
- **层**：`unit` / `集成` / `契约` / `回归` / `e2e` / `live(D1 forensic)`。
- **来源**：`🆕 新增`（点名将新建的 test 文件）/ `♻️ 沿用` / `🔱 fork`。
- **PASS 证据**：四元组 `commit + 测试/查询名 + run-time(UTC)`。

### 8.2 复用台账（沿用 / fork 的既有用例明细）

> 显式列出本 AP **不新建、而站在既有测试上**的部分。

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `（无）tests/unit 当前为空（final §6.7 F7-04「填充 tests/unit 当前空」）` | `🆕 全部新增` | `本 AP 全部为新建用例` | `无既有可沿用` |
| `capstone H 步（purge 断言对象删）/ J 步（路径遍历注入被拒）` | `🔱 fork → F7 capstone` | `+ 本 AP 的对象删除断言 + 路径注入拒绝断言` | `capstone 在 F7 整合（final §8），本 AP 提供其 H/J 步所需修复` |

### 8.3 分层与跑法（各类型在哪跑、何时跑）

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | 本地 / 每 PR | unit（路径遍历·rowid·原子写） | 开发中持续 |
| spike | journey 用例（purge 删对象端到端） | 集成 | 每 Phase 收口 |
| mega | 长程整合全链（capstone A–J） | live 全链 | **F7 整合（本 AP 提供 H/J 步修复）** |
| soak | deterministic × N | live(D1) | **退出硬闸（本 AP 无 soak 项）** |

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖 `真实 vec0 KNN 下的孤儿向量参与检索污染`（理由：`[Q1] 本轮 degraded，本地 JOIN 暂掩盖；F5 接 VectorIndex 接口后验证`）→ 交后继 `FF-F5-vector-authenticity.md`；**不在本 AP 假装覆盖**。
- 不覆盖 `purge 中途崩溃 processing 重入（R12）/ vectorize 崩溃孤儿补偿（R13）`（理由：`一致性/重入同 F3 reap 主题`）→ 交 `FF-F3-kernel-recovery.md`。
- 不覆盖 `embedding_dimension 真校验 + cosine 维度不等 raise（R7）`（理由：`与真实 embedding 维度耦合`）→ 交 `FF-F5`。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 必带**四元组**证据；**计数 ≠ 价值**（对齐 closure 诚实收口）。
- `degraded` 必带机器可读 `reason`；`pre-existing` 失败必带 **git 证据甩锅**，不 silent overclaim。
- **安全 / 信任边界**项的测试必须含**攻击向量用例**（对应 §7.3 威胁模型），不得只测 happy-path：
  - `FF-F4-T01` 必含 `../escaped.txt`、`../../etc/passwd`、`/abs/path`、`a/../../x`、`..\\win\\path`（Windows 段）等逃逸用例，且**当前 HEAD 必须红**（主审实测 `../escaped.txt` 逃逸成功）。
  - `FF-F4-T02` 必含 HTTP body `{"filename":"../../../etc/passwd"}` 注入用例，断言 object_key 不被污染。
  - `FF-F4-T03/T04` rowid 不变量项**当前 HEAD 必须红**（主审实测孤儿 `[1,2]`、`b survived? 0`）；不得仅断言"upsert 不报错"等弱断言。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| `is_relative_to 版本依赖` | `Path.is_relative_to 需 Python 3.9+` | `low` | `执行前确认运行时版本；低版本改用 os.path.commonpath 比对` |
| `F4-03 改 store 写路径影响面` | `rowid 分配/复用/删除三处联动，回归风险` | `high` | `先写红测复现，小步改 + 逐操作序列回归（FF-F4-T03/T04）` |
| `purge.py 与 F3 同文件冲突` | `F4-05 接线 vs F3 R12 重入修复同 process_purge_requests` | `medium` | `与 F3 协调改动窗口（§5 DAG 已标 F4∥F3）` |
| `退化 TEXT 表上 enforce 不变量` | `[Q1] 本轮非 vec0 虚表，rowid 在适配层 enforce` | `low` | `不变量逻辑独立于 vec0；F5 接 vec0 时不变量语义不变` |
| `现存库数据与新 rowid 策略冲突` | `若已有退化库含旧 rowid` | `low` | `P 阶段无生产数据，必要时重建库` |

### 9.2 约束与前提

- **技术前提**：`Python 3.9+（is_relative_to）；sqlite3 标准库；当前 vec.db 为退化 TEXT 表（[Q1] degraded）`
- **运行时前提**：`FileSystemObjectStore 落本地 FS；P 阶段无生产数据`
- **组织协作前提**：`与 F3 协调 purge.py 改动窗口（并行 phase）`
- **上线 / 合并前提**：`安全项（F4-01/02）逃逸用例红→绿 + rowid 不变量（F4-03/04）红→绿，方可合并；closure 不在 F7 前标 ✅`

### 9.3 文档同步要求

- 需要同步更新的设计文档：`无 schema 改动（不动 vec.sql）；rowid 不变量在适配层 enforce`
- 需要同步更新的说明文档 / README：`storage_objects 文档化「文本-only」（R8 out-of-scope）+ delete 接口`
- 需要同步更新的测试说明：`tests/unit 从空 → 填充 path/rowid/io 用例（对齐 F7-04）`

### 9.4 完成后的预期状态

> 用 3-5 条说明本 action-plan 完成后系统会变成什么状态。

1. `FileSystemObjectStore 成为真正的安全边界：object_key 经规范化 + is_relative_to(root) 断言，绝对路径/含 .. 逃逸全部被拒；ingestion filename 经 basename 双层收口，G-CR3-01/G-CR5-02 路径遍历封堵`
2. `VectorStore rowid 一一对应不变量成立：重复 upsert 0 孤儿（R3 消除）、软删后新增不重号不静默删审计（R4 消除）、软硬删一致（R9 消除）`
3. `purge 真正清退对象：被 purge 文档的 raw 上传与 chunk 正文从磁盘删除（R5 合规缺陷消除）`
4. `put_text 原子写、get_text 受控错误处理（R6/R11 就近捆绑收口）`
5. `F5 可在稳固的 rowid 不变量上接真实 embedding 向量化；capstone H（purge 删对象）/ J（路径遍历注入被拒）步获得本 AP 修复支撑`

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

> 收口 = §8 测试台账逐项 PASS，且每项映射回 §3 工作项的收口目标。

### 10.1 收口硬闸

所有 `mega + soak + 退出层` 测试项必须 **PASS 且四元组证据齐全**（本 AP 退出层 = 安全项 + rowid 不变量短途 + purge 集成）：

1. `路径遍历逃逸 0 成功（攻击向量用例全拒）`（由 `FF-F4-T01`、`FF-F4-T02` 证明）
2. `rowid 一一对应不变量成立：重复 upsert 0 孤儿 + 软删后新增不丢审计`（由 `FF-F4-T03`、`FF-F4-T04` 证明）
3. `purge 后被清退文档对象不残留`（由 `FF-F4-T05` 证明）

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| `逃逸用例全拒、合法放行` | `F4-01` | `FF-F4-T01` | `commit + test_filesystem_store_paths + run-time` | `未观察` |
| `HTTP filename 注入入口收口` | `F4-02` | `FF-F4-T02` | `commit + test_ingestion_filename + run-time` | `未观察` |
| `重复 upsert 0 孤儿` | `F4-03` | `FF-F4-T03` | `commit + test_upsert_no_orphan + run-time` | `未观察` |
| `软删后新增不丢审计 + 软硬删一致` | `F4-03/F4-04` | `FF-F4-T04` | `commit + test_soft_delete_audit_survives + run-time` | `未观察` |
| `purge 删对象合规清退` | `F4-05` | `FF-F4-T05` | `commit + test_purge_object_delete + run-time` | `未观察` |
| `原子写 + 受控错误处理` | `F4-06` | `FF-F4-T06` | `commit + test_filesystem_store_io + run-time` | `未观察` |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | `路径遍历封堵（双层）+ rowid 不变量成立 + purge 删对象 + 原子写/错误处理，R1/R3/R4/R5/R9/R6/R11 全收口` |
| 测试 | §8 测试台账全 PASS（退出硬闸项四元组齐全；安全项 + rowid 项先红后绿可证）|
| 文档 | `storage_objects 文本-only + delete 接口文档化；tests/unit 从空填充` |
| 风险收敛 | `F4-03 写路径回归通过；purge.py 与 F3 改动窗口已协调` |
| 可交付性 | `F5 可在 rowid 不变量上构建；capstone H/J 步获修复支撑` |

### 10.4 NOT-成功识别

> 任一退出硬闸测试 `degraded / 未观察` ⇒ **不得标 `executed`**；按 closure 五态如实归类 + handoff，不 silent overclaim。

- 若 `FF-F4-T01/T02` 任一攻击向量用例未在当前 HEAD 复现为红（即修复前未先红），视为测试无效，不得据其判 PASS。
- 若 `FF-F4-T03/T04` 未复现主审实测的孤儿 `[1,2]` / `b survived? 0`，同上无效。
- 真实 vec0 KNN 下的孤儿污染、purge 重入（R12）属 `deferred`（交 F5/F3），如实记账不假装覆盖。

---

## 11. 执行日志回填（`executed` — 2026-06-01）

> 文档状态: `draft → executed`。执行人 Opus 4.8（主轨直接执行，未用收尾子代理）。提交 `1a568d3`。全量 `python3 -m pytest tests/` → **115 passed**（exit 0；F4 前 65 → 新增 50 用例）。

### 11.1 环境
- 系统 python3 含 fastapi/pydantic/starlette/httpx；缺 numpy/uvicorn/bs4/lxml/requests/sentence_transformers/sqlite_vec（F4 不依赖）。
- Python 3.12 → `Path.is_relative_to` 可用（§9.1 风险解除，无需降级到 commonpath）。
- 退化模式：`chunk_embedding_index` 为普通表 `(rowid INTEGER PRIMARY KEY, embedding TEXT)`（`_fallback_vec_sql`）；`vector_records.embedding_rowid` 有 UNIQUE 约束、`chunk_id` 为 PK——正是 R4「INSERT OR REPLACE 撞 embedding_rowid UNIQUE 静默删审计行」的机理。

### 11.2 逐工作项
- **F4-01 ObjectStore 边界校验**：`filesystem_store._resolve_safe(key)`——拒空/blank、绝对路径（`startswith('/')` 或 `Path(key).is_absolute()`）、含 `..` 段、反斜杠（防 `..\\` 绕过）；再 `(root/key).resolve()` 断言 `is_relative_to(root.resolve())` 兜底符号链接/归一化逃逸。put/get/exists/delete 四处统一走它（消除裸 `self.root / object_key`）。
- **F4-02 ingestion basename 收口**：新增 `_safe_filename(filename)`——`os.path.basename` 剥离路径分量后拒空/`.`/`..`/含 `/`/`\\`。`file_initiate` 调用它，`static_initiate` 经 `file_initiate` 复用；`original_filename` 也存清洗后值。basename-strip 契约：`../../../etc/passwd`→`passwd`、`foo/bar.txt`→`bar.txt`（被接受，非拒绝），与控制面/最终防线双层纵深防御协同。
- **F4-03 rowid 单调不复用 + upsert 复用**：`_next_embedding_rowid` 改 `MAX(embedding_rowid)+1 FROM vector_records`（含软删行，非会被硬删的 index——R4 根因消除）。`upsert_chunk` rowid 分配三态：显式传入 > 同 chunk_id 现有行（含软删）复用 > 分配新值（消 R3 孤儿）。
- **F4-04 软/硬删统一**：`delete_chunk` 移除 `DELETE FROM chunk_embedding_index`，仅软删 `vector_records`（置 deleted_at），保留 index 行——一一对应在含软删全集恒成立、审计不被抹除（R9）。`search` 已按 `vr.deleted_at IS NULL` 过滤，软删 index 行不被检索命中。
- **F4-05 ObjectStore.delete + purge 接线**：`filesystem_store.delete(key)` 经 `_resolve_safe` 后 `unlink(missing_ok=True)`。`purge.process_purge_requests(conn, vec_conn, object_store=None)`（默认 None 向后兼容现有调用与 T07 回滚测试）；新增 `_collect_object_keys` 查 uploads（经 source→document）/static_files/artifacts（`storage_backend='object_store'`）的 object_key 逐个删。worker:43 与 management:156 调用点传入 object_store。
- **F4-06 原子写 + 错误处理**：`put_text` 同目录 `tempfile.mkstemp` 落盘后 `os.replace` 原子 rename，失败清理 temp 不留残留；`get_text` 缺失 key 抛受控 `KeyError`（非裸 `FileNotFoundError`）。

### 11.3 先红后绿（50 新用例，全 PASS · 四元组证据）
> 红基线：在 pre-F4 HEAD 跑新测 → **38 failed**（含全部安全/rowid blocker 红），证明先红成立；修复后全绿。

| Test-ID | 文件::用例 | 红基线 | PASS 证据 |
|---------|-----------|--------|-----------|
| FF-F4-T01 | `test_filesystem_store_paths.py`（put/get/exists/delete × 7 攻击向量 + 合法/dot 段） | `../escaped.txt` 逃逸成功写 root 外（实测红） | `1a568d3 + test_filesystem_store_paths(30) PASS + 2026-06-01 03:26 UTC` |
| FF-F4-T02 | `test_ingestion_filename.py`（traversal→basename + 拒绝 6 向量 + static + subpath） | filename 原样污染 object_key（红） | `1a568d3 + test_ingestion_filename(10) PASS + 2026-06-01 03:26 UTC` |
| FF-F4-T03 | `test_vector_store_rowid.py::test_upsert_no_orphan` | 同 chunk_id ×3 → 孤儿 `[1,2]`（红） | `1a568d3 + test_upsert_no_orphan PASS + 2026-06-01 03:26 UTC` |
| FF-F4-T04 | `test_vector_store_rowid.py::test_soft_delete_audit_survives` + `test_resurrect_same_chunk_reuses_rowid` | 软删 b 后 upsert c → `b survived?=0`（红） | `1a568d3 + test_soft_delete_audit_survives PASS + 2026-06-01 03:26 UTC` |
| FF-F4-T05 | `test_purge_object_delete.py`（raw 对象 + chunk_text artifact + 向后兼容） | purge 不删对象, 正文残留（红） | `1a568d3 + test_purge_object_delete(3) PASS + 2026-06-01 03:26 UTC` |
| FF-F4-T06 | `test_filesystem_store_io.py`（原子写无残留 + 覆盖 + 缺失受控异常） | get_text 裸 FileNotFoundError（红） | `1a568d3 + test_filesystem_store_io(4) PASS + 2026-06-01 03:26 UTC` |

- 全量回归：`python3 -m pytest tests/` → **115 passed**（exit 0；65 + 50）。
- 两处**测试自身缺陷**自查修正（非掩盖 blocker）：① 路径测 `root.parent` 原指向共享 tmp 基目录，被红基线逃逸残留污染 → 改 root 为独立 base 子目录；② ingestion 拒绝列表误含 `foo/bar`（basename→`bar` 按 AP 契约应被接受）→ 移出并新增 `test_file_initiate_strips_subpath_to_basename` 锁定 basename-strip 语义。

### 11.4 偏差与 handoff
- **rowid 单调来源选 `vector_records` MAX 而非独立序列表**（AP §4.2 给了两个选项）：因 `delete_chunk` 改为不硬删 vr 行，软删行保留 embedding_rowid → MAX 始终前进、永不回收，无需新表（满足 §9.3「不动 vec.sql / 无 schema 改动」）。若未来出现 vr 硬删路径，需改独立序列表——记为前提。
- **purge 删对象超出 AP §4.3 字面枚举（uploads/static_files）纳入 artifacts**：因 §0 目标「正文不残留磁盘」+ rag 把 chunk_text 经 `put_text` 落盘（`workflow_rag/service.py:115`），忠实兑现合规目标；已加 `test_purge_deletes_chunk_text_artifact_object` 真测该分支。
- **deferred（如实记账，不假装覆盖）**：真实 vec0 KNN 孤儿污染（[Q1] degraded → F5）、purge processing 重入 R12（一致性同 F3 主题）、embedding_dimension 真校验 R7（→ F5）、二进制 put_bytes R8（[Q3] → F6）。
- 跨库 vec 写 + object_store 删均非 core BEGIN IMMEDIATE 覆盖（注释标明，与既有 vec 行为一致）；object 删在 vec 删同处、非事务，purge 重试可重入（delete missing_ok 幂等）。
