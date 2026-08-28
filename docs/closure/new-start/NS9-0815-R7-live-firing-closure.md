# [NS9 / 0815-R7 Live Firing & In-Firing Kernel Fixes] Closure

> 阶段: `v3-ready/NS9 — 0815-R7 实弹发车与发车中内核修复`
> 范围: `R7 四格实弹入库 + NS9-FX1 / NS9-FX2 收口`
> Close-type: `live-verified`
> 状态: `live-verified`
> 日期: `2026-08-28` · 作者: `Antigravity Pair Engineer`
> 关联 charter: `docs/plan/new-start/NS8-updates-before-0815-R7.md`（R7 方案）· 本文即 NS9 记录
> 关联 evidence: `.experiment/0815/runs/MKB-0815-R7/results/analysis.md`、`results/runs.jsonl`（R2 共账本 `-r7` 行）、`inspect/retrieval/`

---

## 0. 一句话 verdict

> NS9 执行了 NS8 交付后等待业主授权的 0815-R7 实弹：四格（N-A3 / N-A6 / N-A2 走 Claude NI，Q-A5 走 Qwen3.8-27B local-vLLM cuts 通道）全部结构化入库并生成双通道向量，既有 88 条 Serving 向量 0 漂移，总向量 88 → 174，显式 namespace 的 Layer A 检索 4/4 命中且无 422。发车过程用证据驱动修掉两个真实内核缺陷：NS9-FX1（vLLM guided grammar 拒绝 layered schema 的 `contains` 关键字）与 NS9-FX2（intake identity replay 在输出物化之后才决定 revision，导致悬空指针与下游 FK 失败），均以 RED-first 测试收口。

---

## 1. 工作项收口表

| Item | 状态 | 证据 |
|------|------|------|
| `R7 live firing 4/4` | ✅ | (commit `df1582e`+`d57a971` 上的实弹 + `results/analysis.md` §2 + `mkb_vector_records` 总量 174 实测 + run-time `2026-08-28T16:35Z`) |
| `NS9-FX1` | ✅ | (commit `df1582e` + test `tests/unit/test_ns8_chunking_and_vllm.py::test_ns9_t01/t02` + live 重放 400→200 + run-time `2026-08-28`) |
| `NS9-FX2` | ✅ | (commit `d57a971` + test `tests/e2e/test_intake_identity_replay.py` + FK 堆栈 `collect-r7-qa5-retry3-console.log` + run-time `2026-08-28`) |
| `worker 吞异常观测修复` | ✅ | (commit `d57a971` + `src/runtime/workflow/worker.py` server-side `logger.exception` + 本次归因即靠它) |
| `Layer A 检索验证` | ✅ | (`MKB-0815-R7/retrieve_r7.py` 4/4 HTTP 200、无 422、traceback resolved + `inspect/retrieval/*.json`) |
| `Serving 资产保护` | ✅ | (Q-A3=17, N-A5=21, N-A3=17, N-A2=33 保持不变；R7 增量 17+15+33+21=86 落在新 `-r7` 任务) |

## 2. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| `G-01 Preflight READY` | 14 闸门全绿 | 发车前/中/后各一次全 PASS | ✅ |
| `G-02 4/4 入库` | 四格 terminal succeeded | 4 个 `-r7` 任务 succeeded，含向量 | ✅ |
| `G-03 88 向量 0 漂移` | 旧四格计数不变 | 17/21/17/33 保持 | ✅ |
| `G-04 检索无 422` | 显式 namespace Layer A | 4/4 200 | ✅ |
| `G-05 修复不放宽 kernel` | fail-closed 判定不变 | `contains` 仅剥离 wire schema；replay 走 ConflictError 围栏；锚点序判定未动 | ✅ |

## 3. 诚实收口声明

- NS9-FX1/FX2 与 worker 日志均有 RED-first 测试（先复现后修复）；e2e 测试断言"指针必须解析、不得铸造新 revision"，不是假绿。
- Q-A5 成功行以 `correction: true` 追加纠正了 collect 客户端超时误记（任务本体 succeeded，见 analysis §2）；未回写历史行。
- 全量 pytest 561 passed / 11 failed：11 项为 README 已记录的存量失败，已在无本次改动的基线上复现确认，非本次引入。
- `STRUCTURE_ANCHOR_MISSING` 未修代码：fail-closed 判定正确（同文档首次尝试成功），属采样波动；重发解决。

## 4. Deferred / Carry-over

| 项 | 类型 | 承接位置 / 触发条件 | 责任方 |
|----|------|---------------------|--------|
| Q 通道 C 摘要慢（megafile，delivery 2 次约 28 分钟） | 观察 | 后继波次归因 local-vLLM construct 单次失败原因 | Pair Engineer |
| `A5` 样本 900s 客户端等待预算对 Q 通道不足 | 客户端测量 | 后继 run 的 runner 按通道区分 timeout | Pair Engineer |
| A1 / A4 扩展文档支持 | OOS | 0815 后继波次 | Architecture Team |

## 5. 下阶段 entry-gate

- Serving 库 174 条向量、4 个 `-r7` 任务 lineage 可回溯。
- R7 冻结命令与预检脚本保持原样，已可作后继波次的复跑基线。
- README 总体状态与能力表已同步至本次收口。

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| `r1` | 2026-08-28 | Antigravity Pair Engineer | R7 实弹 4/4 收口，NS9-FX1/FX2 修复与验证记录 |
