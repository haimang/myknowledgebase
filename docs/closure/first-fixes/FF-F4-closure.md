# [FF-F4 / 适配层安全与数据完整性] Closure

> 阶段: `first-fixes/FF-F4 — 适配层安全与数据完整性`
> 范围: `ObjectStore 路径边界 + ingestion basename + VectorStore rowid 不变量 + 软/硬删统一 + ObjectStore.delete + purge 对象清退 + 原子写/受控错误（F4-01..07）`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-06-01` · 作者: `Opus 4.8`
> 关联 charter: `docs/design/first-fixes/initial-planning-by-opus.md（§6.4 F4 台账 / §4 红线第 4 条 / §5 DAG）`
> 关联 design: `N/A（消费冻结结论 [Q1][Q7]，不新开 Q/A）`
> 关联 action-plan: `docs/action-plan/first-fixes/FF-F4-adapter-safety.md（§11 执行日志已回填）`
> 关联 evidence: `inline §2 + AP §11.3 四元组表`
> 关联 review: `docs/eval/first-code-review-plan/part-cr-3.md（R1/R3/R4/R5/R9/R6/R11）+ part-cr-5.md（R2）`

---

## 0. 一句话 verdict

> F4 收口：path traversal 双层封堵（store `_resolve_safe` 最终防线 + ingestion `_safe_filename` 源头），VectorStore rowid 单调不复用 + upsert 复用现有 rowid（R3 孤儿 / R4 重号静默删审计 / R9 软硬删不一致全消，一一对应在含软删全集恒成立），purge 接 object_store 删 uploads/static_files/artifacts 正文（R5 合规），就近补原子写（R6）+ get_text 受控异常（R11）；先红后绿 50 新用例（红基线 38 failed），全量 65→**115 passed**（exit 0）；close-type = closed-with-explicit-deferrals（真实 vec0/R12/R7/R8 显式推迟 F5/F3/F6）。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. rowid 单调来源用 `vector_records` MAX（非独立序列表）——成立前提是 `delete_chunk` 不硬删 vr 行；若 F5+ 引入 vr 硬删路径需改独立序列表。
> 2. 真实 vec0 KNN 下的孤儿/检索污染本轮 degraded 未验（[Q1]）→ F5 接 VectorIndex 后验证。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + test + run-time） |
|------|------|----------------------------------------|
| F4-01 ObjectStore object_key 边界校验（绝对/`..`/反斜杠拒 + is_relative_to 兜底） | ✅ | `1a568d3 + test_filesystem_store_paths(30, 攻击向量全拒) + 2026-06-01 03:26 UTC` |
| F4-02 ingestion filename basename 源头收口 | ✅ | `1a568d3 + test_ingestion_filename(10) + 2026-06-01 03:26 UTC` |
| F4-03 rowid 单调不复用 + upsert 复用现有 rowid（消 R3/R4） | ✅ | `1a568d3 + test_vector_store_rowid::test_upsert_no_orphan + 2026-06-01 03:26 UTC` |
| F4-04 软/硬删统一（保留审计可追溯，消 R9） | ✅ | `1a568d3 + test_soft_delete_audit_survives + test_resurrect_same_chunk_reuses_rowid + 2026-06-01 03:26 UTC` |
| F4-05 ObjectStore.delete + purge 接线删对象（R5 合规） | ✅ | `1a568d3 + test_purge_object_delete(3, 含 artifact 分支) + 2026-06-01 03:26 UTC` |
| F4-06 put_text 原子写 + get_text 受控异常（R6/R11） | ✅ | `1a568d3 + test_filesystem_store_io(4) + 2026-06-01 03:26 UTC` |
| F4-07 先红后绿测试（攻击向量 + 孤儿/重号红测） | ✅ | `pre-F4 HEAD 跑新测 38 failed（先红）→ 1a568d3 后 50 全绿（后绿）` |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| 路径遍历逃逸 0 成功 | `pytest tests/unit/test_filesystem_store_paths.py` | `30 passed`；`../escaped.txt /abs a/../../x ..\\win` 全 raise；合法 round-trip + dot 段放行 | put/get/exists/delete 四出入口 |
| HTTP filename 注入入口收口 | `pytest tests/unit/test_ingestion_filename.py` | `10 passed`；traversal→basename、含分隔符/空/`.`/`..` raise | file_initiate + static_initiate |
| rowid 一一对应不变量 | `pytest tests/unit/test_vector_store_rowid.py` | `3 passed`；同 chunk_id ×3 → 0 孤儿；软删 b 后 c 不复用 b rowid、b 审计幸存；resurrect 复用 rowid | upsert / delete_chunk / _next_embedding_rowid |
| purge 合规清退对象 | `pytest tests/integration/p1_kernel_closure/test_purge_object_delete.py` | `3 passed`；raw upload + chunk_text artifact 对象 `exists False`；无 object_store 向后兼容 | process_purge_requests + _collect_object_keys |
| 原子写 + 受控错误 | `pytest tests/unit/test_filesystem_store_io.py` | `4 passed`；无 .tmp 残留、覆盖原子、缺失抛 KeyError | put_text / get_text |
| 全量回归无破坏 | `python3 -m pytest tests/` | `115 passed`（exit 0；F4 前 65 + 新增 50） | 全仓 |
| 红基线（先红证据） | pre-F4 HEAD 跑 5 新测文件 | `38 failed, 11 passed`（安全/rowid blocker 全红） | [Q7] 铁律 |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| 路径遍历逃逸 0 成功 | 攻击向量用例全 raise + 不在 root 外落盘 | 30 用例全绿，防假绿断言 root 外无残留 | ✅ PASS |
| rowid 不变量成立 | 重复 upsert 0 孤儿 + 软删后新增不丢审计 | T03/T04 红→绿，一一对应断言通过 | ✅ PASS |
| purge 后对象不残留 | object_store.exists(key) False | raw + artifact 对象删除实测 False | ✅ PASS |
| 先红后绿真实性 | 修复前 blocker 测试必红 | pre-F4 38 failed（含全部安全/rowid blocker） | ✅ PASS |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| 真实 vec0 / sqlite-vec 加载（R2/G-CR3-02） | A（[Q1] 本轮 degraded OOS） | 退化 TEXT 表上 enforce rowid 不变量 | `FF-F5`：接 VectorIndex 接口时 | F5 |
| search namespace/embedding_model 过滤（R10） | C（handoff） | 未做（本 AP OOS） | `FF-F5-03` | F5 |
| embedding_dimension 真校验 + cosine 维度不等 raise（R7） | C（handoff） | store 写死 1536；cosine 截断 min(len) | `FF-F5`（接本地 1536 模型时） | F5 |
| 二进制 put_bytes/get_bytes（R8） | A（[Q3] 文本+HTML 增量 OOS） | 文档化文本-only（filesystem_store 头注释） | `FF-F6`（PDF 解禁时） | F6 |
| purge processing 重入（R12）/ vectorize 孤儿补偿（R13） | C（handoff） | 未做（一致性同 F3 reap 主题） | `FF-F3` 主题域 | F3 |
| rowid 单调来源 = vr MAX（非独立序列表） | B（主动 defer） | 成立前提 = delete 不硬删 vr 行（本 AP 已满足） | 若未来出现 vr 硬删路径，改独立序列表 | F5+ |
| 跨库 vec 写 + object 删非 core 事务覆盖 | B（主动 defer） | 注释标明；object 删幂等可重入 | 与既有 vec 行为一致；最终一致性留待生产化 | F3/运维 |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态 | ✅ — §1 全部为 **verified**（commit + test + run-time 四元组齐全，红→绿可证） |
| ✅ 证据为四元组，无裸 file:line | ✅ |
| scope diff 守卫（仅改 in-scope 文件，无越界） | ✅ — 改 6 源文件（filesystem_store/ingestion/store/purge/worker/management）+ 5 新测，均在 §3 工作总表与锚表内 |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ — §4 七项均标 A/B/C + 承接位置 + 责任方 |
| owner-test 项未经复测标 ⏸ | N/A — 本阶段无 owner-test 项（均本地可复现单测/集成） |

> **诚实附注**：
> 1. **两处测试自身缺陷自查修正（非掩盖 blocker）**：① `test_filesystem_store_paths` 原用 `root.parent`（共享 tmp 基目录），被红基线逃逸残留污染 → 改 root 为独立 base 子目录使防假绿断言隔离；② ingestion 拒绝列表误含 `foo/bar`（basename→`bar` 按 AP basename-strip 契约应被接受）→ 移出并新增 `test_file_initiate_strips_subpath_to_basename` 锁定语义。两者均不掩盖安全/rowid blocker（其红在 pre-F4 已独立成立）。
> 2. **F4-05 范围忠实超集**：AP §4.3 字面枚举 uploads/static_files，但 §0 目标「正文不残留磁盘」+ rag chunk_text 落 object_store（`workflow_rag/service.py:115`）要求一并删 artifacts；已纳入并加 `test_purge_deletes_chunk_text_artifact_object` 真测该分支，非假装覆盖。
> 3. **rowid 不变量在退化 TEXT 表上 enforce**（[Q1] degraded），逻辑独立于 vec0；F5 接真实 vec0 时不变量语义不变（rowid 单调不复用 + 同 chunk_id 复用）。
> 4. 全量 115 passed 含 F1/F2/F3 既有 65 用例无回归（worker/management 签名变更经 p2 控制面 + smoke 测试覆盖）。
