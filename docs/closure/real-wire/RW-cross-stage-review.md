# real-wire RW A-D · 跨阶段代码审查 + qna 对账（by Opus 4.8）

> 对象: `real-wire RW-A/B/C/D 全部执行代码（commits 4bdc30f / 1dcf5b3 / fec0bb3 / ae8d3cf）`
> 日期: `2026-06-01` · 作者: `Opus 4.8`
> 文档性质: `cross-phase review + qna 对账`（不是单阶段 closure；4 份单阶段 closure 见同目录 RW-{A,B,C,D}-closure.md）
> 基线: first-fixes 收口（234 passed）→ RW A-D 后 **279 passed + 2 skipped + 1 xfailed**

---

## 0. TL;DR

> RW A-D 全部串行收口（无跨阶段越界）。**RW-A/B 真实可执行且全本地验证**（mock 基座 + 1024 迁移 + prompt SSOT + 语义链去桩 + mock capstone）；**RW-C/D 交付可被真实接线的脚手架/实现**，真实 MLX 推理与真实 vec0 KNN **本离线 Linux 不可跑 → 据实标未观察、skipif gate 真跑 owner macOS**。与冻结 qna 7 题 + reframe 全部对账一致。1 处 footgun（vec0 Setting 未接 store）+ 若干 carry-over 已登记。

---

## 1. 全量测试与门禁

| 验证 | 命令 | 结果 |
|------|------|------|
| 全量回归 | `python3 -m pytest -p no:cacheprovider` | `279 passed, 2 skipped, 1 xfailed`（基线 234，净 +45） |
| 断言强度门禁 | `tools/scripts/check_assert_strength.py` | `52 文件 0 弱断言` |
| 维度 1536 残留 | `grep -rn 1536 …` | 仅 2 条迁移历史注释；0 生效字面 |
| 密钥泄漏 | `grep sk-… packages apps`（非测试） | 无；`.env` 未 tracked，`redact_secret` 脱敏 |
| import 循环 | 同导全部 touched 包 | 无循环 |

- **跳过项（未观察，非失败）**：`test_rw_d_vec0.py` 2 项（vec0↔暴力 cosine parity + 空候选）—— sqlite-vec 扩展离线 Linux 不可载，skipif gate 真跑 owner macOS。

---

## 2. qna 裁决对账（冻结 Q-RW-1..7 + reframe → 实际交付）

| Q | 冻结裁决 | 实际交付 | 一致? |
|---|----------|----------|-------|
| Q-RW-1 | 维度 1024（覆盖 1536）；embedding 仅本地 MLX | 全库 1024（vec.sql×2+docs/refactor/vec.sql+schema+store+embedder）；写侧守卫 fail-loud；`LocalEmbedder`(1024) 默认 + `RealMLXEmbedder` 占位 | ✅ |
| Q-RW-2 | LLM provider adapter 延后；本轮 mock+接口+路由 | `LLMProvider` 协议 + `MockLLMProvider` + 工厂 + `semantic_mode/llm_provider` 路由；`RealMLXLLMProvider` 占位（推理 deferred） | ✅ |
| Q-RW-3 | prompt 本地文件 + SQLite-SSOT + hash 对账（不用 KV） | `prompts/*.md` + `prompt_renderer`(render/seed/sync) + `prompt_versions` SSOT + sha256 digest 对账 fail-loud；正文本地原创 | ✅ |
| Q-RW-4 | 本轮不接 PDF | RWD-01/02/03 未做，登记 deferred；handoff provider/embedding charter | ✅ |
| Q-RW-5 (v1.1) | vec0 本轮真做（写+skip 测，真跑 macOS） | `Vec0VectorIndex`（真实 sqlite-vec KNN）+ 工厂槽 + parity skipif-gate→macOS | ✅ |
| Q-RW-6 | 计费框架定、数值延后（本地无外部账单） | 默认 mock 零外网零计费；真实 provider+护栏数值 deferred 至 provider charter | ✅ |
| Q-RW-7 | `.env`+构造注入；外部 key 预留；key 不进仓/日志 | Settings key 字段预留 None + `.gitignore .env` + `.env.example` + 构造注入 + `redact_secret`（攻击向量用例验 repr 不含 key） | ✅ |
| reframe | 本轮=mock+占位+接口+mock↔real 路由+测 mock | RW-A/B 真做 mock 链；RW-C/D 脚手架+占位+真实实现（不可跑部分未观察） | ✅ |

**对账结论**：7 题 + reframe **全部一致**，无 over-claim。所有「真实推理/真实 KNN/真实质量」均按裁决 deferred 或标未观察，未谎报 verified。

---

## 3. 跨阶段不变量（0-drift）

| 不变量 | 状态 | 证据 |
|--------|------|------|
| 维度 1024 全库 + 跨包 | ✅ | `DIMENSION==EMBEDDING_DIMENSION==1024`；grep 0 生效 1536 |
| 写/查同 embedder（TR-3 ⛔3） | ✅ | 写(workflow_rag)/查(management)均经 `make_embedder` 同 name |
| 默认 mock/rule 不打外网（TR-5/TR-6） | ✅ | Settings 默认 mock/local-hash/bruteforce/rule |
| degraded/延后 fail-loud + 机器可读 reason（TR-4） | ✅ | MockResponseMissing/PromptError/ProviderDeferredError/sqlite_vec_unavailable/UnknownProviderError |
| 密钥不进仓/日志（Q-RW-7/F6c⛔1） | ✅ | `.env` ignored + redact + 构造注入 |
| 接口隔离 mock/live 同协议（TR-1） | ✅ | Mock/RealMLX/FakeLive 均 isinstance LLMProvider；Vec0/BruteForce 同 VectorIndex |
| 防假绿（计数≠价值） | ✅ | `assert_used_real_chain` spy 真调；门禁 0 弱；mock 标 non-delivery-quality |
| 无跨阶段越界 | ✅ | 每阶段 todo 循环独立；改动 scope 与各 AP 一致 |

---

## 4. 审查发现 + 债务台账

| # | 发现 | 级别 | 处置 |
|---|------|------|------|
| X1 | **`Settings.vector_index="vec0"` 未接 store.search**：工厂 `make_vector_index('vec0')` 返 `Vec0VectorIndex`，但 `store.search` 仍硬建 `BruteForceVectorIndex` → 设 vec0 不生效（静默用 BruteForce） | 🟡 footgun | 登记 carry-over（持久 vec0 store 集成）；RW-D closure §4 已记；macOS 集成时一并接 store |
| X2 | 真实 MLX 推理 + 真实 vec0 KNN 本环境未观察 | 🟡 未观察 | 占位/skipif fail-loud；owner macOS 验（RW-C/RW-D closure handoff） |
| X3 | executor-级 semantic_mode=llm 需 prompt 已 seed + mock responses_path（否则 fail-loud） | 🟢 by-design | render/Mock 未命中 fail-loud（[Q7] 不静默）；capstone 演示 seed 流程 |
| X4 | PDF 输入面未做 | 🟢 deferred | Q-RW-4 裁决；provider/embedding charter |
| X5 | `make_embedder` 每次新建 LocalEmbedder 实例（非单例） | 🟢 无害 | LocalEmbedder 无状态；写查同 name 即一致（TR-3 满足） |

- **无 🔴 blocking 项**。X1 是唯一需在 macOS 集成期消化的 footgun，已显式登记防静默。

---

## 5. Verdict

| 维度 | 评级 | 一句话 |
|------|------|--------|
| 交付价值 | 高（mock 骨架完整）| RW-A/B 让「可被真实接线的语义管线」mock 下端到端跑通且被测；RW-C/D 备好真实接线脚手架/实现 |
| 累积债务 | 低-中 | 真实推理/KNN/store 集成/PDF 全部显式 deferred 带承接位置；1 footgun 已登记 |
| qna 一致性 | 满分 | 7 题 + reframe 全对账，无 over-claim |
| 综合健康 | 🟢 | 279 passed + 门禁 0 弱；诚实标注未观察项 |

- **反镀金提醒**：未在本轮强造真实 MLX/vec0「假跑通」；未把 deferred 项粉饰为 verified；未越界做 PDF。

---

## 6. 后继 handoff（provider charter / macOS 运行轮）

1. **owner macOS**：装 sqlite-vec → 跑 `test_rw_d_vec0.py`（2 skip 转 pass）确认 vec0↔暴力 parity；装 MLX → 实装 `RealMLX*.complete/embed`（占位 fail-loud 转真实）。
2. **持久 vec0 store 集成**（X1）：`store` 读写 vec0 原生格式（`serialize_float32`）+ `store.search` 直接查持久 vec0 表 + 接 `Settings.vector_index`；rowid 不变量虚表层复核。
3. **provider charter**：定具体 MLX 模型（LLM + 1024 维 embedding）+ 计费/速率护栏数值（Q-RW-6）+ 外部 key 需求（Q-RW-7）。
4. **PDF**：owner 指定 parser 库 → RWD-01/02/03。
5. live smoke：owner-triggered lane（默认 skip，不进默认 CI）。

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| r1 | 2026-06-01 | Opus 4.8 | RW A-D 跨阶段审查 + qna 对账初稿（279 passed；7 题全一致；X1 footgun 登记） |
