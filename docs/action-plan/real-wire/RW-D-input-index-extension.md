# 行动计划 · RW-D — 输入面与索引扩展（PDF/二进制 + 真实 vec0，gated 延后）

> 服务业务簇: `real-wire / 输入面与索引扩展（二进制对象存储 + PDF 解析 + 真实 vec0 KNN）`
> 计划对象: `RW-D phase（final-execution-plan §6.D，台账 RWD-01..05）`
> 类型: `new + migration`（put_bytes/PDF 净新；vec0 替 BruteForce 重 substrate）
> 作者: `Opus 4.8`
> 时间: `2026-06-01`
> 文件位置: `packages/storage_objects/ · apps/api/routes/ · packages/workflow_clean/ · packages/vector_sqlite_vec/ · tests/`
> 上游前序 / closure:
> - `docs/action-plan/real-wire/RW-A-provider-base.md`（VectorIndex 接口/工厂）
> - `docs/eval/real-wire/final-execution-plan-by-opus.md` §6.D（SCOPE↓ 延后）
> 下游交接:
> - `（生产化轮 / 后续输入面 charter）`
> 关联设计 / 调研文档:
> - `docs/eval/real-wire/reference-anchor-by-opus.md`（轴 D 锚定矩阵）
> 冻结决策来源:
> - `docs/eval/real-wire/pre-charter-qna.md`（frozen；Q-RW-4 本轮不接 PDF / Q-RW-5 延后 vec0）
> grounding 来源:
> - `eval-reference-anchor 轴 D`（R2 二进制签名思路 + rowid 不变量 + 多级过滤 + vec0 退化表 + 反例）
> 关联 reference-anchor:
> - `docs/eval/real-wire/reference-anchor-by-opus.md`（§7.3 指回真源）
> 文档状态: `executed（vec0 scaffolding；2026-06-01, commit ae8d3cf; closure: docs/closure/real-wire/RW-D-closure.md）— vec0 真做(写+skip 测, 真跑 macOS); PDF 仍 deferred(Q-RW-4)`

---

## 0. 执行背景与目标

> **⚠️ 本 AP 为 `draft (deferred)`**：冻结 qna 已裁决 **Q-RW-4 本轮不接 PDF/二进制**、**Q-RW-5 延后真实 vec0**（维持暴力 cosine）。本 AP 据 final §6.D 提前**铺好骨架与 grounding**，但**不在本轮开工**。重评条件见 §2.3 / §6。

RW-D 扩展两个面：**输入面**（`ObjectStore` 二进制 + PDF 解析）与**索引面**（真实 `Vec0VectorIndex` 替 `BruteForceVectorIndex`）。reference-anchor 轴 D 已确认：HEAD 的 `ObjectStore` **仅文本、无 put_bytes**（`filesystem_store.py:38` put_text，无 bytes 方法），上传端点 `content` 为 `str`（`ingestion.py:25,42`）；R2 二进制签名思路（`r2.ts:117-154`）可借落地为本地 FS 原子写；PDF 的 Browser Rendering+Vision（`cleaner_web.ts:142-207`）**⛔ 不可借**，改本地 pypdf/pdfminer；真实 vec0 是 `schema.py` 退化逻辑（`apply_vec_schema:48` + `vec_schema_migrations`）的**反向**——扩展可载时虚表替 TEXT、接口不变；rowid 不变量（`store.py` `_next_embedding_rowid`）须在虚表层复核。维度锁 1024（RW-A 已迁）。

- **服务业务簇**：`real-wire / 输入面与索引扩展`
- **计划对象**：`RW-D phase（RWD-01..05）`
- **本次计划解决的问题（解锁后）**：
  - `ObjectStore` 无二进制支持（`filesystem_store.py` 仅 put_text）；上传端点不收 bytes。
  - PDF 源无法处理（`browserPDF*` degraded，`action_registry.py:90-95`）。
  - 暴力 cosine 在大规模语料下成性能瓶颈（当前未到瓶颈）。
- **本次计划的直接产出（解锁后）**：
  - `ObjectStore.put_bytes/get_bytes` + 二进制上传端点 + MIME 贯穿。
  - 本地 PDF 解析（pypdf/pdfminer）+ `browserPDF` 去 degraded + PDF 端到端 capstone。
  - `Vec0VectorIndex`（sqlite-vec 扩展）替 BruteForce + vec0↔暴力 cosine 一致性回归。
- **本计划不重新讨论的设计结论**：
  - 本轮不接 PDF/二进制（来源：`Q-RW-4`）。
  - 延后真实 vec0、维持暴力 cosine（来源：`Q-RW-5`）。
  - 维度 1024（来源：`Q-RW-1`，RW-A 已迁）。
  - vec0 退化+迁移表 + fail-loud（来源：`[Q1]`）。

---

## 1. 执行综述

### 1.1 总体执行方式

**解锁后**：输入面与索引面可并行（互不依赖）。输入面先 put_bytes（substrate）→ PDF 解析 → PDF capstone；索引面 Vec0VectorIndex 替换 + 一致性回归。先红后绿（PDF 解析正确 / vec0↔暴力 cosine 不串味）。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | ObjectStore 二进制 + 上传端点 | M | put_bytes/get_bytes + 二进制上传 + MIME 贯穿 | RW-A；Q-RW-4 重评 |
| Phase 2 | 本地 PDF 解析 + 去 degraded | L | pypdf/pdfminer 解析 + browserPDF 去 degraded + PDF capstone | Phase 1；Q-RW-3(G-RW-3) |
| Phase 3 | 真实 vec0 + 一致性回归 | L | Vec0VectorIndex 替 BruteForce + vec0↔暴力 cosine 回归 | RW-A；Q-RW-5 重评 |

### 1.3 Phase 说明

1. **Phase 1 — ObjectStore 二进制**：核心目标=put_bytes/get_bytes + 二进制上传；为什么先做=PDF 解析依赖二进制存取。
2. **Phase 2 — PDF 解析**：核心目标=本地 PDF 库 + 去 degraded + capstone；放这里=依赖 Phase 1 二进制。
3. **Phase 3 — 真实 vec0**：核心目标=Vec0VectorIndex 替换 + 一致性回归；放这里=独立于输入面，可并行。

### 1.4 执行策略说明

- **执行顺序原则**：输入面（put_bytes→PDF）与索引面（vec0）并行；各自先红后绿。
- **风险控制原则**：put_bytes 沿用 `_resolve_safe` 信任边界；vec0 接口不变、一致性回归守不串味。
- **测试推进原则**：PDF 解析正确性 + vec0↔暴力 cosine 一致性为退出硬闸，详见 §8。
- **文档同步原则**：上传端点 API surface 更新；vec0 接入说明。
- **回滚 / 降级原则**：vec0 扩展不可载时回落 BruteForce（[Q1] 退化已有）；PDF 解析失败 fail-loud。

### 1.5 本次 action-plan 影响结构图

```text
RW-D 输入面与索引扩展（gated）
├── Phase 1: ObjectStore 二进制
│   ├── packages/storage_objects/filesystem_store.py:38（+put_bytes/get_bytes）
│   └── apps/api/routes/ingestion.py:25,42（content:str→支持 bytes + mime 贯穿）
├── Phase 2: PDF 解析
│   ├── packages/workflow_clean/action_registry.py:90-95（browserPDF 去 degraded）
│   └── 本地 pypdf/pdfminer 解析器（新建）
└── Phase 3: 真实 vec0
    ├── packages/vector_sqlite_vec/vector_index.py:23（Vec0VectorIndex 实现接口）
    └── packages/vector_sqlite_vec/schema.py:48（vec0 虚表替 TEXT 退化的反向）
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（解锁后明确要做）

- **[S1]** `ObjectStore.put_bytes/get_bytes`（本地 FS + 原子写 + `_resolve_safe`）+ 二进制上传端点 + MIME 贯穿。
- **[S2]** 本地 PDF 解析（pypdf/pdfminer）+ `browserPDF` 去 degraded + PDF 端到端 capstone。
- **[S3]** `Vec0VectorIndex`（sqlite-vec 扩展加载）替 BruteForce + rowid 不变量虚表层复核。
- **[S4]** vec0↔暴力 cosine 一致性回归（换索引不串味）。

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** 多模态 Vision 理解（无本地多模态；Browser Rendering ⛔）。
- **[O2]** 真实 LLM/embedding —— RW-C。
- **[O3]** 维度 schema 改动（锁 1024）。
- **[O4]** 托管向量库 / Durable Objects 队列（Vectorize/DO ⛔；用 sqlite-vec + F3 worker）。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| put_bytes + PDF 解析 | deferred | Q-RW-4 本轮不接 PDF | 语料含必须处理的 PDF / 业务需二进制上传 |
| Vec0VectorIndex | deferred | Q-RW-5 延后；暴力 cosine 未瓶颈 | 暴力 cosine 撞性能瓶颈 / 生产化轮 |
| Browser Rendering + Vision | out-of-scope | Cloudflare 托管 ⛔；无本地多模态 | 产品需求 + 本地多模态可得 |
| 维度改动 | out-of-scope | 锁 1024（TR-2）| — |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| RWD-01 | Phase 1 | `put_bytes/get_bytes` + 二进制上传端点 + MIME 贯穿 | add | `filesystem_store.py:38`、`ingestion.py:25,42` | 二进制存取 + 上传 + MIME 贯穿 | RWD-T01 | medium |
| RWD-02 | Phase 2 | 本地 PDF 解析（pypdf/pdfminer）+ browserPDF 去 degraded | add | `action_registry.py:90-95`、PDF 解析器（新建）| PDF 文本可解析；degraded 撤除 | RWD-T02 | high |
| RWD-03 | Phase 2 | PDF 端到端 capstone（上传→解析→clean→rag→vector→search）| add | `tests/e2e/...（新建）` | PDF 端到端通过 | RWD-T03 | medium |
| RWD-04 | Phase 3 | `Vec0VectorIndex`（sqlite-vec 扩展）替 BruteForce + rowid 复核 | migrate | `vector_index.py:23`、`schema.py:48` | vec0 KNN + 接口不变 + rowid 不变量 | RWD-T04 | high |
| RWD-05 | Phase 3 | vec0↔暴力 cosine 一致性回归 | add | `tests/...` | 同查询两实现结果一致 | RWD-T05 | medium |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — ObjectStore 二进制 + 上传端点

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| RWD-01 | put_bytes/上传端点 | a) `FileSystemObjectStore.put_bytes(key, data: bytes)`/`get_bytes`，沿用 `_resolve_safe`(`:17`)信任边界 + 原子写（temp+os.replace，借 put_text `:41-48` 范式）；b) 借 `r2.ts:117-154` 二进制+contentType 签名**思路**（R2 binding 不借）；c) 上传端点 `ingestion.py:25,42` `content:str` 扩为支持 bytes（base64/multipart）+ `mime_type`(`:19`)贯穿至存储；d) 边界：路径穿越仍经 `_resolve_safe` 拒绝；空/超大 fail-loud | `filesystem_store.py:38`、`ingestion.py:25,42` | 二进制存取 + 上传 + MIME 贯穿 | RWD-T01 | put/get bytes 往返 + 路径穿越拒绝 + MIME 贯穿 |

### 4.2 Phase 2 — 本地 PDF 解析 + 去 degraded

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| RWD-02 | PDF 解析 | a) 本地解析器（pypdf/pdfminer，离线依赖）抽 PDF 文本；b) `action_registry.py:90-95` 的 `browserPDF-geminiClean` 由 `register_degraded`→真实 handler（本地解析）；c) **⛔ 不借** Browser Rendering+Vision（`cleaner_web.ts:142-207`）；d) 边界：损坏 PDF/加密 PDF/无文本层（扫描件）fail-loud + reason（无本地 Vision，扫描件不强解）| `action_registry.py:90-95`、PDF 解析器（新建）| PDF 文本可解析；degraded 撤除 | RWD-T02 | 正常 PDF 解析 + 损坏/加密 fail-loud |
| RWD-03 | PDF capstone | 上传 PDF（put_bytes）→ 解析 → clean → rag → vector(1024) → search 端到端 | `tests/e2e/...（新建）` | PDF 端到端通过 | RWD-T03 | A–H 步全绿 |

### 4.3 Phase 3 — 真实 vec0 + 一致性回归

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| RWD-04 | Vec0VectorIndex | a) 实现 `VectorIndex` 协议(`vector_index.py:23`)的 sqlite-vec 版（vec0 虚表 KNN）；b) 是 `schema.py:48` 退化逻辑的**反向**——扩展可载时虚表替 TEXT，**接口不变**；c) rowid 不变量（`store.py` `_next_embedding_rowid` 单调）在虚表层复核；d) 多级过滤（team→namespace→model）在 vec0 KNN 后仍套用；e) 扩展不可载回落 BruteForce（[Q1] 退化已有）；f) 维度 1024（vec0 `float[1024]`，RW-A 已迁）| `vector_index.py:23`、`schema.py:48` | vec0 KNN + 接口不变 + rowid 不变量 | RWD-T04 | vec0 KNN 正确 + 回落 BruteForce + rowid 单调 |
| RWD-05 | 一致性回归 | 同查询、同语料下 `Vec0VectorIndex` 与 `BruteForceVectorIndex` top-k 结果一致（换索引不串味）；先红后绿 | `tests/...` | 两实现结果一致 | RWD-T05 | 一致性断言 + 边界（并列分/空集）|

---

## 5. Phase 详情

### 5.1 Phase 1 — ObjectStore 二进制 + 上传端点

- **Phase 目标**：put_bytes/get_bytes + 二进制上传 + MIME 贯穿。
- **本 Phase 对应编号**：`RWD-01`
- **本 Phase 修改文件**：`filesystem_store.py:38`、`ingestion.py:25,42`
- **具体功能预期**：
  1. `put_bytes/get_bytes` 沿用 `_resolve_safe` + 原子写。
  2. 上传端点收 bytes（base64/multipart）+ mime_type 贯穿。
  3. 路径穿越仍拒绝。
  4. 空/超大 fail-loud。
- **对应测试台账项**：`RWD-T01`
- **收口标准**：往返 + 穿越拒绝 + MIME 贯穿。
- **本 Phase 风险提醒**：二进制路径仍是信任边界——必经 `_resolve_safe`。

### 5.2 Phase 2 — 本地 PDF 解析 + 去 degraded

- **Phase 目标**：本地 PDF 解析 + browserPDF 去 degraded + capstone。
- **本 Phase 对应编号**：`RWD-02` / `RWD-03`
- **本 Phase 新增文件**：PDF 解析器、`tests/e2e/`PDF capstone
- **具体功能预期**：
  1. pypdf/pdfminer 抽文本。
  2. browserPDF degraded→真实 handler。
  3. ⛔ 不借 Browser Rendering+Vision。
  4. 损坏/加密/扫描件 fail-loud（无本地 Vision）。
  5. PDF 端到端 capstone A–H。
- **对应测试台账项**：`RWD-T02` / `RWD-T03`
- **收口标准**：正常解析 + 异常 fail-loud + capstone 绿。
- **本 Phase 风险提醒**：扫描件无文本层——不强解，fail-loud + reason。

### 5.3 Phase 3 — 真实 vec0 + 一致性回归

- **Phase 目标**：Vec0VectorIndex 替 BruteForce + 一致性回归。
- **本 Phase 对应编号**：`RWD-04` / `RWD-05`
- **本 Phase 修改文件**：`vector_index.py:23`、`schema.py:48`
- **具体功能预期**：
  1. vec0 虚表 KNN 实现 VectorIndex 协议。
  2. 退化反向：扩展可载替 TEXT，接口不变。
  3. rowid 不变量虚表层复核。
  4. 多级过滤 KNN 后套用。
  5. 扩展不可载回落 BruteForce。
  6. vec0↔暴力 cosine top-k 一致。
- **对应测试台账项**：`RWD-T04` / `RWD-T05`
- **收口标准**：vec0 KNN + 回落 + 一致性回归绿。
- **本 Phase 风险提醒**：换索引串味——一致性回归守底；rowid 虚表层须复核单调。

---

## 6. 依赖的冻结设计决策（只读引用）

> **⚠️ deferred**：本 AP 整体延后。Q-RW-4/5 已冻结为「本轮不做」，重评条件见 §2.3。

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| `Q-RW-4` 本轮不接 PDF/二进制 | `pre-charter-qna.md`（frozen=延后）| Phase 1/2 延后 | 语料含 PDF 则重评启用 |
| `Q-RW-5` 延后真实 vec0 | `pre-charter-qna.md`（frozen=延后）| Phase 3 延后 | 暴力 cosine 撞瓶颈则重评 |
| `Q-RW-1` 维度 1024 | `pre-charter-qna.md`（frozen）| vec0 `float[1024]`；PDF 链 embed 1024 | — |
| `[Q1]` vec0 degraded + 接口 + fail-loud | `owner-gated-qna.md` | RWD-04 退化反向；接口已留 | — |
| RW-A 完成（VectorIndex 接口/工厂/1024）| 前置 AP | RWD-04 挂接口；put_bytes 维度无关 | RW-A 未完成则 blocked |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| D-1 | `packages/storage_objects/.../filesystem_store.py:17,38-48` | `_resolve_safe` + put_text 原子写 | RWD-01 put_bytes 范式 | ♻️ 重 substrate | 沿用信任边界 + 原子写 |
| D-2 | `apps/api/.../routes/ingestion.py:19,25,42` | 上传端点 content:str + mime_type | RWD-01 扩 bytes | ✅ 复用 | initiate/confirm 状态机已有 |
| D-3 | `packages/workflow_clean/.../action_registry.py:90-95` | `browserPDF*` register_degraded | RWD-02 去 degraded | ♻️ 重 substrate | degraded→真实 handler |
| D-4 | `packages/vector_sqlite_vec/.../vector_index.py:23` | `VectorIndex` Protocol | RWD-04 实现接口 | ✅ 复用 | 接口已留口 |
| D-5 | `packages/vector_sqlite_vec/.../schema.py:48` | `apply_vec_schema` + 退化 + `vec_schema_migrations` | RWD-04 退化反向 | ✅ 复用 | 扩展可载替 TEXT |
| D-6 | `packages/vector_sqlite_vec/.../store.py:_next_embedding_rowid` | rowid 单调不变量 | RWD-04 虚表层复核 | ✅ 复用 | 接 vec0 时复核 |
| D-7 | `packages/vector_sqlite_vec/.../store.py:search(多级过滤)` | team→namespace→model 过滤 | RWD-04 KNN 后套用 | ✅ 复用 | 已就位 |
| D-8 | `legacy/.../clean-universal/core/r2.ts:117-154` | R2 put 多态二进制签名 | RWD-01 签名思路 | 🔶 部分借 | 借思路，R2 binding 不借 |
| D-9 | `legacy/.../services/cleaner_web.ts:142-207` | PDF Browser Rendering+Vision | RWD-02 反例 | ⛔ 反例 | 不可借；本地 pypdf/pdfminer |
| D-10 | `legacy/.../vectorizer/{vectorizer_do.ts,core/vector_db.ts}` | Vectorize/DO 托管 | RWD-04 反例 | ⛔ 反例 | 不可借；sqlite-vec + F3 worker |

### 7.2 反例 ledger ⛔

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | PDF 走 Browser Rendering + Vision（`cleaner_web.ts:142-207`）| 托管渲染/视觉不可得；本地 pypdf/pdfminer，扫描件不强解 |
| ⛔2 | Vectorize/DO 托管向量库+队列 | 不可移；sqlite-vec(vec0) + F3 worker 轮询 |
| ⛔3 | 二进制路径绕过 `_resolve_safe` | 路径穿越；put_bytes 必经信任边界 |
| ⛔4 | 换 vec0 后结果与暴力 cosine 串味 | 检索漂移；一致性回归守底（RWD-05）|
| ⛔5 | vec0 维度≠1024 | 撞 schema；vec0 float[1024]（RW-A 已迁）|

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：`docs/eval/real-wire/reference-anchor-by-opus.md`（轴 D）—— §7.1 摘录；TR 过滤见真源 §5。
- **安全 / 信任边界**：二进制上传是信任边界——威胁模型锚 = `_resolve_safe`(`filesystem_store.py:17`) + 反例 ⛔3。**RWD-01 必须含路径穿越攻击向量用例**（绝对路径/`..`/反斜杠拒绝），否则不得标 executed。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| RWD-T01 | put/get bytes 往返 + 路径穿越拒绝（攻击向量）+ MIME 贯穿 | 短途 | unit·安全 | 🆕 新增 `test_object_store_bytes.py` | RWD-01 → 二进制存取 | `commit + test + run-time` |
| RWD-T02 | PDF 正常解析 + 损坏/加密/扫描件 fail-loud | 短途 | unit | 🆕 新增 `test_pdf_parse.py` | RWD-02 → PDF 解析 | `commit + test + run-time` |
| RWD-T03 | PDF 端到端 capstone（上传→解析→…→search）| spike | e2e | 🆕 新增 `tests/e2e/test_pdf_capstone.py` | RWD-03 → PDF 端到端 | `commit + e2e PASS + run-time` |
| RWD-T04 | vec0 KNN 正确 + 扩展不可载回落 BruteForce + rowid 单调 | 短途 | 集成·契约 | 🆕 新增 `test_vec0_index.py` | RWD-04 → vec0 接口不变 | `commit + test + run-time` |
| RWD-T05 | vec0↔暴力 cosine top-k 一致（含并列/空集边界）| 短途 | 回归 | 🆕 新增 `test_vec0_bruteforce_parity.py` | RWD-05 → 不串味 | `commit + test + run-time` |

### 8.2 复用台账

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| 既有 `_resolve_safe` 路径穿越测（F4）| 🔱 fork → bytes 版 | + bytes 路径断言 | 已存在，PASS |
| 既有 BruteForce 检索测 | ♻️ 沿用 | 0 改动（作 parity 基准）| 已存在 |
| `schema.py` vec0 退化测 | ♻️ 沿用 | 0 改动 | 已存在 |

### 8.3 分层与跑法

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | 本地 / 每 PR | unit·集成·契约·安全·回归 | 开发中 |
| spike | PDF capstone | e2e | Phase 2 收口 |
| mega / soak | 本轮 N/A | — | — |

### 8.4 测试缺口

- 不覆盖扫描件 OCR（理由：无本地 Vision/多模态）→ 后续轮；扫描件 fail-loud，不假装支持。
- 不覆盖 vec0 大规模性能基准（理由：本轮重正确性非性能）→ 生产化轮。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 带四元组。
- 安全项（put_bytes）必须含路径穿越攻击向量用例。
- vec0 一致性回归必须含边界（并列分/空集），不只测 happy-path。
- degraded（扫描件/扩展不可载）必带机器可读 reason。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| Q-RW-4/5 未触发重评 | 本轮不做 | —（deferred）| 待重评条件 |
| PDF 解析依赖 | pypdf/pdfminer 离线装否 | medium | 依赖确认；扫描件 fail-loud |
| 路径穿越 | 二进制绕过信任边界 | high | `_resolve_safe` + 攻击向量用例 |
| vec0 串味 | 换索引结果漂移 | high | 一致性回归 + 回落 BruteForce |
| sqlite-vec 扩展 | 离线装否 | medium | 不可载回落 BruteForce（[Q1]）|

### 9.2 约束与前提

- **技术前提**：RW-A 完成；pypdf/pdfminer + sqlite-vec 可得（离线）。
- **运行时前提**：维度 1024；vec0 `float[1024]`。
- **组织协作前提**：owner 触发重评（语料含 PDF / 性能瓶颈）。
- **上线 / 合并前提**：PDF capstone 绿 + vec0↔暴力 cosine 一致 + 路径穿越拒绝。

### 9.3 文档同步要求

- 需更新：上传端点 API surface（二进制/MIME）。
- 需新增：vec0 接入说明 + 一致性回归说明。

### 9.4 完成后的预期状态（解锁后）

1. `ObjectStore` 支持二进制；上传端点收 bytes + MIME 贯穿。
2. PDF 源可解析（本地）；browserPDF degraded 撤除；扫描件 fail-loud。
3. `Vec0VectorIndex` 替 BruteForce，接口不变，rowid 不变量守住。
4. vec0↔暴力 cosine 一致——换索引不串味。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

### 10.1 收口硬闸（解锁后）

1. put/get bytes 往返 + 路径穿越拒绝（`RWD-T01`）。
2. PDF 解析正确 + 异常 fail-loud（`RWD-T02`）。
3. vec0 KNN + 回落 + rowid 单调（`RWD-T04`）。
4. vec0↔暴力 cosine 一致（`RWD-T05`）。

### 10.2 收口映射表

| 收口目标 | 工作项 | Test-ID | PASS 证据 | 状态 |
|----------|--------|---------|-----------|------|
| 二进制存取 | RWD-01 | RWD-T01 | — | deferred |
| PDF 解析 | RWD-02 | RWD-T02 | — | deferred |
| PDF 端到端 | RWD-03 | RWD-T03 | — | deferred |
| vec0 接口不变 | RWD-04 | RWD-T04 | — | deferred |
| 不串味 | RWD-05 | RWD-T05 | — | deferred |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | put_bytes + PDF 解析 + vec0 替换 |
| 测试 | §8 全 PASS（PDF capstone + vec0 parity + 路径穿越）|
| 文档 | 上传 API surface + vec0 说明 |
| 风险收敛 | 路径穿越拒绝 + 不串味 + degraded fail-loud |
| 可交付性 | PDF 源 + 生产 KNN 可用 |

### 10.4 NOT-成功识别

> **本 AP 当前=deferred**：Q-RW-4/5 重评条件触发前不开工。解锁后任一退出硬闸 `degraded/未观察` ⇒ 不得标 executed。

---

## 11. 执行日志回填（executed — vec0 scaffolding；PDF 延后）

> 文档状态：`executed（vec0 部分）`（2026-06-01，commit `ae8d3cf`）。owner v1.1 裁决覆盖 Q-RW-5：**vec0 本轮真做**（写+skip 测，真实 KNN 真跑 owner macOS）；**PDF（RWD-01/02/03）仍延后**（Q-RW-4，owner 后续 charter 指定 parser 库）。全量 279 passed + 2 skipped + 1 xfailed；门禁 52 文件 0 弱。

**工作记录（逐项）**

- **RWD-04 `Vec0VectorIndex`**：`vector_sqlite_vec/vector_index.py` — 实现 `VectorIndex` 协议（`backend="vec0"`）；候选式契约下建内存 vec0 虚表（`CREATE VIRTUAL TABLE ... USING vec0(embedding float[dim] distance_metric=...)`）→ 插候选 → `embedding MATCH ? ORDER BY distance LIMIT k` → distance→score 转换（cosine: `1-d`；l2: `-d`）对齐 BruteForce 排序（larger=better）；`inner_product` 非 vec0 原生 → 降级 cosine（warning，与 BruteForce 降级纪律一致）。
- **`sqlite_vec_available()`**：探测扩展可载性（离线 Linux=False；macOS 装后=True）。扩展不可载时 `Vec0VectorIndex.query` **fail-loud** `RuntimeError(sqlite_vec_unavailable)`——不静默退化（退化由 `schema.py` [Q1] 决定回 BruteForce/TEXT）。
- **工厂槽**：`make_vector_index("vec0")` → `Vec0VectorIndex`（由 RW-A 的 `_deferred` 占位改为真实返回）。
- **RWD-05 一致性回归**：`test_vec0_bruteforce_parity_cosine`（20 随机 1024-d 向量，vec0 与 BruteForce cosine top-5 chunk_id 顺序一致）+ 空候选——`@pytest.mark.skipif(not sqlite_vec_available())` gate，离线 skip、**真跑 owner macOS**。
- **测试**：`tests/unit/test_rw_d_vec0.py` 7 项（协议/工厂槽/分数转换 cosine+l2/metric 降级/不可用 fail-loud = 5 本环境验；parity+空候选 = 2 skip→macOS）。

- **PDF 延后（RWD-01/02/03）**：`ObjectStore.put_bytes`/本地 PDF 解析/PDF capstone **未做**——Q-RW-4 裁决本轮不接，owner 在后续 provider/embedding 实装章节指定 PDF parser 库。
- **Phase 偏差 / 限制**：`Vec0VectorIndex` 是 `VectorIndex.query` **候选式协议**的合规实现（内存 vec0 索引 over candidates），证明真实 sqlite-vec KNN + 与 BruteForce 一致性。**未做**：把持久 `chunk_embedding_index` 改为 vec0 原生存储（`serialize_float32`）+ `store.search` 直接查持久 vec0 表（替代当前 TEXT-JSON 读路径 + 候选加载）——此「持久 vec0 store 集成」需 store 读写格式重构 + macOS 实跑验证，列 carry-over。
- **阻塞与处理**：sqlite-vec 扩展离线 Linux 不可载（无 numpy/无扩展二进制）→ 真实 KNN 与 parity 本环境不可跑；按 owner「写+fake/skip 测」裁决，代码写实、parity skip-gate 到 macOS，closure 标 `未观察(本环境不可跑)`，不谎报。
- **测试发现**：279 passed（+5，从 274 基线）+ 2 skipped（vec0 parity，macOS gate）+ 1 xfailed；无 import 循环。
- **后续 handoff**：① owner macOS 跑 RWD-05 parity（去 skip）；② 持久 vec0 store 集成（store 读写 vec0 格式 + 直接表 KNN）；③ PDF（provider/embedding charter，owner 指定 parser 库）。
