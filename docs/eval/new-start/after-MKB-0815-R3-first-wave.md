# after MKB-0815-R3 · 首轮 live 记分

> **对象**：`MKB-0815-R3` 冻结五格 `-r3`
> **日期**：`2026-08-16`
> **作者**：`Grok`
> **文档性质**：`eval / run-score`（不是 closure，不改写 R1）
> **文档状态**：`scored / conclusions-unsealed`
> **方法**：`.experiment/0815/runs/MKB-0815-R3/RUN.md`
> **库证**：R2 `runtime/mkb.turso.db` 一等行；重建期刊 `MKB-0815-R3/results/runs.jsonl`

## 一句话

N-A5 在 g1 v3 上 **publish**（21 向量）。Q-A3 17 条仍在。检索 6/6 无 Layer A 422。N-A2 仍 `GRANULARITY_SET_MISMATCH`（只有 g0）。产品轴 **未** 达 `R3_READY`，token 仍 `conditional-ready`。四次失败都有 stage report，观测轴够用。

## 产品表

| 格 | 终态 | 码 | 向量 |
|---|---|---|---:|
| N-A5 | succeeded | — | 21 |
| N-A3 | failed | `STRUCTURE_ANCHOR_MISSING` | 0 |
| N-A6 | failed | `CLAUDE_CLI_OUTPUT_INVALID` / `empty_result` | 0 |
| N-A2 | failed | `STRUCTURE_GRANULARITY_SET_MISMATCH`（set=`0`） | 0 |
| Q-A5 | failed | `STRUCTURE_ANCHOR_MISSING` | 0 |
| Q-A3（旧） | succeeded（未重跑） | — | 17 |

## 观测表（数行，不数 extra）

| 格 | stage report | failed invocation |
|---|---|---|
| N-A5 | 无（成功） | 无；diagnostic 记了一次随后恢复的 CLI 运输失败 |
| N-A3 | rejected · set `0,1` · 9 块 | 无（有 markdown 成功行） |
| N-A6 | transport_failed · `empty_result` | 有 |
| N-A2 | rejected · set `0` · 1 块 | 无 |
| Q-A5 | rejected · set `0,1` · 11 块 | 无 |

无 `obs-insufficient`。Q-A5 池为 `local-inference`。

## 期刊

collect 收尾用 sqlite3 读 Turso 文件失败，jsonl 写成 `collect-exception`。真实 Task 已终态。runner 已改为 `turso.connect`。记分以重建期刊 + 库行为准。

## 不做什么

不改 kernel，不改 C，不开 A1/A4/A5g2，不重跑 Q-A3 同键，不改写 R1 封条。
