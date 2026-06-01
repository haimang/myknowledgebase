# [FF-F5 / 向量真实性与检索] Closure

> 阶段: `first-fixes/FF-F5 — 向量真实性与检索`
> 范围: `Embedder adapter + 本地语义 embedding（替伪向量）+ vec0 degraded 定档（fail-loud + VectorIndex 接口）+ search namespace/model 过滤 + distance_metric 生效（F5-01..04）`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-06-01` · 作者: `Opus 4.8`
> 关联 charter: `docs/design/first-fixes/initial-planning-by-opus.md（§6.5 F5 绑定表 / §2.C 定档 / §5 DAG）`
> 关联 design: `N/A（消费冻结结论 [Q1][Q2][Q7]，不新开 Q/A）`
> 关联 action-plan: `docs/action-plan/first-fixes/FF-F5-vector-authenticity.md（§11 执行日志已回填）`
> 关联 evidence: `inline §2 + AP §11.3 四元组表`
> 关联 review: `docs/eval/first-code-review-plan/part-cr-7.md（G-CR7-01 伪向量）+ part-cr-3.md（G-CR3-02 vec0 退化 / G-CR3-10 search 过滤）`

---

## 0. 一句话 verdict

> F5 收口：SHA-256 伪向量替换为本地确定性语义 embedding（`LocalEmbedder` feature-hashing 词袋，1536 维，共词余弦更高；写/查共用同实例），vec0 degraded 显式定档（退化路径 fail-loud `logger.warning` 含机器可读 reason + `VectorIndex` 接口抽象，暴力 cosine 收敛其下），search 增 namespace_id/embedding_model 过滤 + distance_metric 读 namespace 配置生效；先红后绿 22 用例（语义排序红基线实测 SHA 下 3 对全未排第一），全量 115→**137 passed**（exit 0）；close-type=closed-with-explicit-deferrals（真实 vec0 / 神经 embedding / 外部 API 显式推迟）。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. 「本地小模型」是**确定性词袋 feature-hashing 非神经模型**——只捕捉词面/字面重叠的相关，不捕捉同义性（car≈automobile）；真实神经 embedding 需 ML 依赖离线不可得 → 技术债 handoff。
> 2. vec0 本轮 degraded（暴力 cosine，性能随数据量线性劣化）是 [Q1] 设计定档；P4/P5 若有 vector/retrieval 假绿 ✅ 须 F7-05 重定级为 degraded。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + test + run-time） |
|------|------|----------------------------------------|
| F5-01 Embedder adapter + 本地 1536 维语义 embedding（替伪向量，写/查同实例，维度强约束） | ✅ | `7a70408 + test_f5_embedder(9) + test_f5_vector_authenticity(2) + 2026-06-01 03:38 UTC` |
| F5-02 vec0 degraded 定档：退化路径 fail-loud 告警 + VectorIndex 接口 | ✅ | `7a70408 + test_f5_vec_degraded + test_f5_vector_index_contract(7) + 2026-06-01 03:38 UTC` |
| F5-03 search namespace_id/embedding_model 过滤 + distance_metric 生效 | ✅ | `7a70408 + test_f5_search_filter(3) + 2026-06-01 03:38 UTC` |
| F5-04 先红后绿回归（向量真实性 + degraded 告警 + 过滤反例） | ✅ | `语义排序红基线实测（SHA 3 对全未排第一）→ 7a70408 后 22 全绿` |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| 向量真实性（先红后绿核心） | `pytest tests/integration/p4_rag_pipeline/test_f5_vector_authenticity.py` | `2 passed`；3 对样本目标 chunk 全排第一、margin ≥0.1；对照 fake 不全中 | LocalEmbedder + VectorStore.search |
| 语义排序红基线 | 覆盖前用 SHA `embed_text` 跑 3 对样本 | `top=dog/tax/dog`（目标全未第一），margin +0.023/+0.016/+0.019（噪声） | [Q7] 先红证据 |
| Embedder 维度/语义/fixture | `pytest tests/unit/test_f5_embedder.py` | `9 passed`；1536 / dims!=1536 raise / 共词余弦高于无关 +0.1 / fake 不相关 | embedder adapter 边界 |
| vec0 degraded fail-loud | `pytest tests/unit/test_f5_vec_degraded.py` | `1 passed`；caplog 捕获 warning 含 `sqlite_vec_unavailable_degraded_to_bruteforce` | schema 退化路径 |
| VectorIndex 契约 | `pytest tests/unit/test_f5_vector_index_contract.py` | `7 passed`；cosine/inner_product/l2 排序 + 未知 metric 降级告警 | vector_index 接口 |
| search 过滤 + metric | `pytest tests/unit/test_f5_search_filter.py` | `3 passed`；跨 model 不串味 + namespace 过滤 + metric 读配置生效 | store.search / _resolve_metric |
| 全量回归 + 全链 | `python3 -m pytest tests/` | `137 passed`（exit 0；115+22）；p5 url→worker→rag→search 全链通过 | 全仓 + 写/查 model 一致 |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| 向量真实性 spike（T01）+ 先红证据 | 相关 query 目标 chunk 排第一 + 分差显著；HEAD 伪向量下先红 | 真实 embedder 3 对全第一 margin≥0.1；SHA 红基线已留证 | ✅ PASS |
| degraded 告警（T03） | 退化路径 logger.warning 含机器可读 reason | caplog 命中 `sqlite_vec_unavailable_degraded_to_bruteforce` | ✅ PASS |
| 跨 namespace/model 不混算（T05）+ 维度校验（T02） | 过滤反例用例齐全 | model/namespace 过滤不串味；dims!=1536 raise | ✅ PASS |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| 真实神经 embedding（捕捉同义性，超越词面） | C（handoff） | 本地词袋 feature-hashing 仅捕捉词面/字面重叠 | 下一轮生产化 / [Q2] 子选项 C（adapter 已留口） | 下一轮 |
| 真实 sqlite-vec / vec0 接入（O1, R2/G-CR3-02） | A（[Q1] degraded OOS） | 暴力 cosine + VectorIndex 接口就位（局部可替换） | 生产化 / 数据量增大 KNN 成瓶颈 | 下一轮 |
| 外部 API embedding 后端（O2, [Q2] 子选项 C） | A（OOS） | adapter 接口已留口，本轮不实现远程后端 | 需更高语义质量且接受网络/计费 | 下一轮 |
| 维度 ≠1536 / 改 schema（O3） | A（[Q2] 强约束 OOS） | adapter 边界强制 1536，免触 schema | 选型需 ≠1536 维模型（牵动 F4/迁移） | 下一轮 |
| embedding 重试退避 / token usage（O4） | B（主动 defer） | 未做（非语义真实性核心） | 下一轮可靠性强化 | 下一轮 |
| distance_metric l2/inner_product 生产校验 | B（主动 defer） | 已实现三 metric 排序 + 单测；生产语义校准未做 | 接真实 vec0 时 | 下一轮 |
| vector/retrieval gate closure 重定级 degraded | C（handoff） | 本 AP fail-loud + 接口就位；P4/P5 假绿待撤 | `FF-F7-05` closure 重定级 | F7 |
| 端到端 clean→rag→search 语义命中 capstone 步 F/G | C（handoff） | 依赖 F6 真实 structurize/construct | `FF-F7` capstone | F7 |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态 | ✅ — §1 全部 **verified**（commit + test + run-time 四元组齐全，T01 先红后绿可证） |
| ✅ 证据为四元组，无裸 file:line | ✅ |
| scope diff 守卫（仅改 in-scope 文件，无越界） | ✅ — 改 embedder/__init__/search/schema/store/vector_index(新)/workflow_rag，均在 §3 工作总表 + §7.1 锚表内 |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ — §4 八项均标 A/B/C + 承接位置 + 责任方 |
| owner-test 项未经复测标 ⏸ | N/A — 无 owner-test 项 |

> **诚实附注**：
> 1. **「本地小模型」的忠实落地是确定性词袋 feature-hashing（非神经网络）**：环境离线无 numpy/sentence-transformers，无法加载真实神经模型。本实现满足 [Q2] 的核心意图（真实、离线、零计费、可复现、1536 维、**语义相关非 SHA 噪声**），但其「语义」源于词面/字面 n-gram 重叠，不等同神经 embedding 的同义性捕捉。**不假装是神经模型**——真实神经 embedding 列 §4 技术债 handoff。T01 的语义断言基于词面相关样本，真实有效（SHA 红基线对照证明 bug 真实）。
> 2. **vec0 degraded 是设计定档（[Q1]）非未达成**：与 closure 五态的「未观察」区分——degraded 标注是预期态。本 AP 已 fail-loud 告警（撤销静默退化假绿根因）+ VectorIndex 接口（未来 vec0 局部替换）。
> 3. **写/查一致性已强制**：`embed_text` 与 `search.py` 均经 `default_embedder()`（同一 LocalEmbedder 单例），杜绝「查询命中自身」掩盖（⛔3 / part-cr-7 R1）；p5 全链通过证写入 embedding_model 与查询过滤名一致。
> 4. 全量 137 passed 含 F1-F4 既有 115 用例无回归。
