# [RW-D / 真实 vec0 + 索引扩展] Closure

> 阶段: `real-wire/RW-D — 输入面与索引扩展（本轮=真实 vec0 sqlite-vec；PDF 延后）`
> 范围: `RWD-04 Vec0VectorIndex · RWD-05 vec0↔暴力 cosine 一致性回归；RWD-01/02/03 PDF 延后`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-06-01` · 作者: `Opus 4.8`
> 关联 charter: `docs/eval/real-wire/final-execution-plan-by-opus.md`（§6.D）
> 关联 design: `docs/eval/real-wire/reference-anchor-by-opus.md`（轴 D）
> 关联 action-plan: `docs/action-plan/real-wire/RW-D-input-index-extension.md`
> 关联 evidence: `inline §2`
> 关联 review: `inline（独立审查 → §5）`

---

## 0. 一句话 verdict

> RW-D 按 owner v1.1 裁决（Q-RW-5 覆盖为本轮真做）交付 **`Vec0VectorIndex`（真实 sqlite-vec KNN，实现 VectorIndex 协议，distance→score 对齐 BruteForce）+ 一致性回归**；本环境验：协议/工厂槽/分数转换/metric 降级/不可用 fail-loud（5 passed）；真实 KNN 与 vec0↔BruteForce parity **离线 Linux 不可跑 → skipif gate 真跑 owner macOS（2 skipped，未观察）**。PDF（RWD-01/02/03）按 Q-RW-4 延后。279 passed + 2 skipped + 1 xfailed，门禁 0 弱。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. 真实 vec0 KNN + parity **未在本环境验证**（无 sqlite-vec 扩展）——macOS 跑 skip 测。
> 2. **持久 vec0 store 集成未做**：`store.search` 仍走 TEXT-JSON 候选加载 + BruteForce；持久 `chunk_embedding_index` 改 vec0 原生存储 + 直接表 KNN 是 carry-over。
> 3. PDF/二进制输入未做（Q-RW-4 延后）。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + test + run-time） |
|------|------|----------------------------------------|
| RWD-04 `Vec0VectorIndex`（协议 + KNN + 分数转换） | ✅（scaffolding）| commit `ae8d3cf` + `test_rw_d_vec0.py::test_vec0_satisfies_protocol`/`_distance_to_score_cosine_and_l2`/`_metric_degrade_to_cosine` PASS |
| RWD-04 工厂 vec0 槽 | ✅ | `…::test_factory_vec0_slot` PASS |
| RWD-04 不可用 fail-loud（不静默退化） | ✅ | `…::test_vec0_unavailable_fail_loud_on_offline` PASS（离线 Linux 路径） |
| RWD-05 vec0↔暴力 cosine 一致性回归 | ⏸ 未观察 | `…::test_vec0_bruteforce_parity_cosine` **skipped**（sqlite-vec 不可载）→ owner macOS 跑 |
| 真实 vec0 KNN 执行 | ⏸ 未观察 | 离线 Linux 无扩展；`query` fail-loud；macOS 验 |
| RWD-01/02/03 PDF/二进制 | ⏸ deferred | Q-RW-4 本轮不接；owner 后续 charter 指定 parser 库 |
| 持久 vec0 store 集成 | ⏸ deferred | store 读写格式重构 + macOS 跑 |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| RW-D 单测 | `python3 -m pytest tests/unit/test_rw_d_vec0.py -v` | `5 passed, 2 skipped` | RWD-04 本环境 + RWD-05 macOS-gate |
| 全量回归 | `python3 -m pytest` | `279 passed, 2 skipped, 1 xfailed`（基线 274） | 全仓 |
| 断言强度门禁 | `python3 tools/scripts/check_assert_strength.py` | `52 文件 0 弱` | 防假绿 |
| vec0 协议合规 | `isinstance(Vec0VectorIndex(), VectorIndex)` | True | RWD-04 |
| 扩展探测 | `sqlite_vec_available()` | False（离线 Linux） | 环境真相 |
| import 无循环 | `python3 -c "import provider_runtime, vector_sqlite_vec"` | OK | — |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| vec0 实现协议合规 + 工厂槽 | isinstance VectorIndex + make_vector_index('vec0') | PASS | ✅ PASS |
| 分数转换对齐 BruteForce 排序 | cosine:1-d / l2:-d（larger=better） | 转换测 PASS | ✅ PASS |
| 不可用 fail-loud（不静默退化 ⛔1） | 扩展不可载 → RuntimeError(sqlite_vec_unavailable) | PASS | ✅ PASS |
| vec0↔暴力 cosine top-k 一致（不串味） | 同查询同语料 top-5 chunk_id 顺序一致 | **未跑**（无扩展） | ⏸ PENDING（skipif → macOS） |
| PDF 端到端 | 上传→解析→…→search | 未做 | ⏸ deferred（Q-RW-4） |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| RWD-05 真实 parity 验证 | C | skipif gate（离线不可跑） | owner macOS 装 sqlite-vec 跑（去 skip） | owner |
| 持久 vec0 store 集成 | B | Vec0VectorIndex 就绪；store.search 仍 TEXT-JSON+BruteForce | store 读写改 serialize_float32 + 直接表 KNN（macOS 验） | 下游 |
| PDF/二进制（RWD-01/02/03） | C | 未做 | provider/embedding charter（owner 指定 parser 库；Q-RW-4） | owner + 下游 |
| 多模态 Vision（扫描件 OCR） | A | OOS（无本地多模态；Browser Rendering ⛔） | 产品需求 + 本地多模态可得 | — |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态 | ✅ —— RWD-04 协议/工厂/分数/降级/不可用 = **verified**（本环境，commit+test+run-time）；真实 KNN + RWD-05 parity = **未观察**（无 sqlite-vec 扩展，skipif→macOS）。 |
| ✅ 证据为四元组 | ✅ —— commit `ae8d3cf` + 具名 test + 2026-06-01 10:47 UTC |
| scope diff 守卫 | ✅ —— 改动落在 vector_sqlite_vec（vector_index/__init__）+ provider_runtime/factory + tests；无越界；PDF 未碰（延后） |
| deferred 已三分类且有承接位置 | ✅ —— §4 标 A/B/C，均带承接位置 |
| owner-test/未观察项标 ⏸ | ✅ —— parity + 真实 KNN 标 ⏸ 未观察（skipif），无「我跑通了 vec0」式宣称 |

> **诚实说明**：本环境（离线 Linux，无 sqlite-vec 扩展）**未运行真实 vec0 KNN**——`Vec0VectorIndex` 代码写实、协议合规、分数转换/降级/fail-loud 已验，但真实 KNN 与「vec0↔暴力 cosine 一致性」是 **skipif-gated，待 owner macOS 运行**。`Vec0VectorIndex` 是 `VectorIndex.query` 候选式协议的合规实现（内存 vec0 索引）；**持久 vec0 store 集成**（store 读写 vec0 原生格式 + 直接表 KNN）未做，列 carry-over。不宣称 vec0 已在生产路径生效。

---

## 6. Handoff / 下阶段 entry-gate 预核对

| 入口条件 | 状态 | 备注 |
|----------|------|------|
| `Vec0VectorIndex` 协议合规 + 工厂槽 | ✅ | 接口与 BruteForce 一致，drop-in |
| 一致性回归用例就绪（skipif gate） | ✅ | owner macOS 去 skip 即跑 |
| sqlite-vec 运行时（macOS） | ⏸ | 离线 Linux 不可载 |
| store 持久 vec0 集成 | ⏸ | carry-over（读写格式重构） |
| PDF parser 库 | ⏸ | owner 后续 charter 指定 |

**下阶段 kickoff checklist**：
- [ ] owner macOS 装 sqlite-vec → 跑 `test_rw_d_vec0.py`（2 skip 转 pass）确认 parity
- [ ] 持久 vec0 store 集成（serialize_float32 存储 + 直接表 KNN + rowid 不变量虚表层复核）
- [ ] PDF：provider/embedding charter 定 parser 库 → RWD-01/02/03

---

## 7. Cross-cut 不变量（0-drift 确认）

| 不变量 | 状态 | 证据 |
|--------|------|------|
| 维度 1024（vec0 表 float[1024]） | ✅ 保持 | Vec0VectorIndex 按 `len(embedding)`=1024 建表；RWA-09 继承 |
| 换索引不串味（接口隔离 TR-1） | ✅ 保持（设计）/ ⏸（实测） | 协议一致；parity 实测待 macOS |
| degraded/不可用 fail-loud + reason（TR-4） | ✅ 保持 | `sqlite_vec_unavailable` RuntimeError；metric 降级 warning |
| [Q1] vec0 退化接口缝复用 | ✅ 保持 | Vec0 与 BruteForce 同 `VectorIndex` 协议；schema.py 退化逻辑不动 |
| 离线默认不依赖 ML/扩展（TR-6） | ✅ 保持 | 默认 bruteforce；vec0 仅 opt-in 且不可载 fail-loud |

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| r1 | 2026-06-01 | Opus 4.8 | RW-D 初闭合（closed-with-explicit-deferrals；vec0 实现 verified，真实 KNN+parity 未观察→macOS，持久 vec0 store 集成 + PDF deferred） |
