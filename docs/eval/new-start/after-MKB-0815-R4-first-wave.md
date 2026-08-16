# after MKB-0815-R4 · 首轮 live 记分

> **日期**：`2026-08-17`
> **性质**：`eval / run-score`（不是 closure，不改写 R1/R3 RCA）
> **方法**：`.experiment/0815/runs/MKB-0815-R4/RUN.md`

## 一句话

四格 `-r4` 全红。`R4_READY` **未达成**（N-A2 仍 `GRANULARITY_SET_MISMATCH`，report `set=0`）。Q-A3 17 与 N-A5 21 仍在。检索 6/6 200。证据面修复 **生效**：四格都有 stage report + failed invocation；latency 非零；Q-A5 markdown `adapter_kind=local_vllm`。期刊这次读库成功。token 仍 `conditional-ready`。

## 产品表

| 格 | 终态 | 码 | report |
|---|---|---|---|
| N-A3 | failed | `STRUCTURE_ANCHOR_MISSING`（g0 非全文） | rejected · set=`0,1` · 9 块 · 98s |
| N-A6 | failed | `CLAUDE_CLI_OUTPUT_INVALID` | transport_failed · `empty_result` · 449s |
| N-A2 | failed | `STRUCTURE_GRANULARITY_SET_MISMATCH` | rejected · set=`0` · 1 块 · 271s · **v4 未改形状** |
| Q-A5 | failed | `STRUCTURE_ANCHOR_MISSING`（g0 非全文） | rejected · set=`0,1` · 11 块 · 259s · 池 local |

N-A3/N-A2 structurize invocation 钉的是 `g1.v4.md`。v4 恰好集字面在，工人仍只交 g0。

## 观测

四格失败 invocation 与 report 成对。无 `obs-insufficient`。Q 格未串 NI。

## 不做

不改 kernel，不重跑 N-A5/Q-A3，不开 A1/A4/A5g2，不改写 R1。
