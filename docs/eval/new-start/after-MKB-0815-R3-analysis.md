# MKB-0815-R3 analysis with FF10 family method

> **仓内副本**：run SSOT 是 `.experiment/0815/runs/MKB-0815-R3/results/analysis.md`。本文件是给业主读的同文副本；改分析先改 run 目录再同步。

> **手法来源**：与 R2 同一家族模板 `.experiment/0815/runs/MKB-0815-R2/results/ff10-family-template.md`。
> **本文件角色**：R3 的 RCA + 对 v3/NS4 证据面的评价 + R4 前修复台账与施工说明。不是封条。R1 `results/analysis.md` 与 R2 `results/analysis.md` **不得改写**。

## 0. 文档状态与最终结论

| 项 | 值 |
|---|---|
| 文档编号 | `MKB-0815-R3-analysis-with-FF10-family` |
| 分析时间 | `2026-08-17 UTC` |
| 对象封存 | R3 `evidence/SEAL.json` `subjects-sealed`；SUBJECTS.md5 文件 MD5 `442752284761368a4b0fee1554c7e909` |
| 封存 HEAD（对象） | `d3a41955cbdd6a9fea70b24a2c816561f08cb793` |
| 发车 HEAD | `256298d` 预检复跑；分析时仓 `9abb9b2` |
| team | `01a00822-bc2b-7145-ad55-e9b5c3aa2c60`（沿用 R2） |
| 本枪 publish | **N-A5** / task `01a00b3a-3e20-71a3-81b4-0724743f8196` · 21 向量 |
| 保留 serving | Q-A3 / `01a00887-3cef-7379-92ea-3a6a38fd4188` · **仍 17 向量** |
| 文档终态 | `RCA COMPLETE / R3_READY SCORED / R4 PLAN DRAFTED / NOT SEALED` |
| 结论 token（建议，未封） | `conditional-ready` |

本报告的统一结论是：

1. R3 回答了 R2 §9 四个目标里的 **两个半**。Q-A3 索引还在（`PROVEN` 17 条）。**N-A5 在 NI + g1 v3 上 publish**（投影 `{0:1, 1:10}`，validation `full_valid`，无 g0 original 向量）。A5g2 闸按 `T-O-375` 已具备「N-A5 或 Q-A5 一格 publish」的前提，但本枪按冻结命令 **没有** 开 A5g2。
2. **g1 v3 没有完成它被派去的那件事。** R2 的 mismatch 假说是「工人多吐 g=2」。R3 的 N-A2 直方图是 `set=0`、`block_count=1`、`has_g0=1`——工人 **只交了 g0，连 g=1 都没有**。v3 把「出现 g=2 则失败」写成了可执行句，模型用「什么层都不切」满足了「不要输出 2」。`PROVEN` 形状，不再是 R2 的 `UNKNOWN`。
3. **中长文 g0 锚在 NI 上原样复现。** N-A3 仍是 `The g0 body is not the complete clean artifact`（17KB）。同文 Q-A3 仍是 R2 的 Qwen 成功化石，本枪按令 **没有** 重跑。Q-A5（8KB，与 N-A5 同文）在 Qwen 上 `STRUCTURE_ANCHOR_MISSING`，而 NI 同文 publish。不能再写「Qwen 普遍强于 NI」。
4. **NS4 一等证据面本枪可用。** 四次失败都有 `mkb_generation_stage_reports` 行。N-A6 是 `transport_failed` + `cli_structured_kind=empty_result`，R2 §10.2 的信封诊断第一次在 live 上分出「空」而不是笼统的 not-an-object。没有 `obs-insufficient`。
5. **期刊不是真相。** collect 在 Task 终态后用 stock `sqlite3` 读 pyturso 文件，五格 jsonl 都写成 `collect-exception`。真实终态在 Turso。记分以重建期刊 `MKB-0815-R3/results/runs.jsonl` + 库行为准。runner 已改为 `turso.connect`（`9abb9b2`）。
6. 检索运输仍绿：6/6 HTTP 200，无 Layer A 422。金标语义只对「现有语料能回答的问」可评：Q-MIXIN 打到 N-A5 closure 是真命中；Q-POOL / Q-V5R / Q-GLOSS 仍没有 A6/A2/A1 语料。

因此，R3 parent 必须永久保留：

```text
run_id                 MKB-0815-R3
parent                 MKB-0815-R2 / unsealed RCA / 不得改写
wave                   1/5 publish (N-A5 only)
product_terminal       N-A5 SUCCEEDED / four siblings RED
q_a3                   INTACT 17
n_a5                   PROVEN NI publish on g1 v3
mismatch               STILL RED (N-A2 set={0} not {0,1,2})
anchor                 STILL RED (N-A3 NI, Q-A5 Qwen)
cli_kind               PROVEN empty_result on N-A6
obs                    SUFFICIENT (4/4 fail reports)
retrieval_transport    PASS
retrieval_gold         PARTIAL (A5 mixin hit; missing A2/A6/A1)
kernel_relaxed         NO
silent_worker_swap     NO
journal                sqlite3 lie / turso truth
```

可接受的 continuation 是新 `run_id` `MKB-0815-R4`（新 `external_key` 后缀 `-r4`），不是回写本枪五条 Task，也不是 `rm` serving 库。

## 1. 调查权限、成本边界与方法

### 1.1 本轮实际操作

本文件是取证与文档输出。写分析时 **没有** 新创建 ingest Task，没有 `--rerun`，没有改 kernel。

此前 R3 已经发生的 live 操作（历史，不是本文件触发）：

| 项 | 实际值 |
|---|---|
| 预检 | 19/19 PASS，复跑 `2026-08-16T06:26:44Z` / HEAD `38d2c6e` |
| live ingest | 五格 `-r3`，`2026-08-16T15:39:21Z`–`16:23:06Z` |
| 金标检索 | 事后补跑 6×200 |
| 远端对象（本分析） | `0` 新 Task |

「写完整分析」= RCA + R4 台账冻结，**不**解释成发车 R4 或封条授权。

### 1.2 证据等级

- `PROVEN`：Turso 当前行、重建 `runs.jsonl`、对象库六件套、检索 JSON、源码、预检 JSON。
- `LEADING`：时序与实现只支持这一条主因；或 invocation 缺行但 report 形状完整。
- `UNKNOWN`：admit 失败未入库的 candidate JSON；N-A6 空信封的模型体内。
- `DECISION`：R4 设计选择，不冒充历史。

优先级：Turso 一等行 > 重建期刊 > R2 collect 原 jsonl（含 `collect-exception`）> 族方案叙述。R2 collect 的 `collect-exception` 行 **不是** 产品终态。

## 2. Provenance 与 sealed evidence

### 2.1 代码与提示词线路

| 资产 | 作用 | 本报告评价 |
|---|---|---|
| R1 封条 `conditional-ready` | 不得改写 | 保持（`PROVEN` MD5） |
| R2 Q-A3 serving | 唯一旧索引 | 17 向量仍 indexed（`PROVEN`） |
| NS4 013 + stage reports | 失败一等行 | 四失败格都有 report（`PROVEN`） |
| `cli_structured_kind` | 非 object 分型 | N-A6=`empty_result`（`PROVEN`） |
| catalog g1 **v3** | 闭集 `{0,1}`、禁 g=2 | N-A2 变成缺 g=1，不是多 g=2（`PROVEN`） |
| C 仍 v2 | `T-O-375` 不改 C | N-A5 C `full_valid`（`PROVEN`） |
| F5 `expected_dimension` | 问句 1024 | 6/6 200（`PROVEN`） |
| runner `sqlite3.connect` | 读 process 做 jsonl | 五格误记；已改 turso |

### 2.2 当前 R3 artifact

| Artifact | 位置 / 身份 |
|---|---|
| 预检 | `results/preflight.json` `passed=true` |
| 发车戳 | `results/launch_started_at.txt` |
| collect 日志 | `results/collect.log`（含 sqlite3 例外） |
| R2 原期刊 | R2 `results/runs.jsonl` 追加 5 行 `collect-exception` |
| **记分期刊** | `results/runs.jsonl`（Turso 重建，5 行） |
| team / 重建说明 | `results/_meta.json` |
| 对象清单 | `subjects/manifest.json` 18 项 |
| live 库 | R2 `runtime/mkb.turso.db`（**禁止当新库**） |
| N-A5 六件套 | 对象库 sha256（structure/projection/construct/dual 均 `full_valid`） |
| 金标 | `inspect/retrieval/Q-*.{request,response}.json` |

失败格 **没有** structure artifact。形状只信 stage report，不信「模型当时写了哪一段原文」。

## 3. 三个 root 必须分开

### 3.1 Root-0：发车前预检

19/19。证明：R1 封条、R3 对象、NS4 closure、g1 v3 合同、catalog v3、Turso 013、Q-A3 17、零 `-r3` 键、NI/Qwen/embed PING。

```text
lane_verdict      READY
product_terminal  NOT_STARTED
root cause        none
```

不得把预检绿写成 H2 绿。

### 3.2 Root-1：五格 live（本枪唯一产品 root）

五格都创建了 Task 并走到 markdown+structurize。1 publish / 4 红。这是本报告的主 root。

```text
lane_verdict      CONDITIONAL
product_terminal  N-A5 SUCCEEDED
siblings          4 RED
obs               4/4 reports
```

### 3.3 Root-2：期刊 / runner 读库（实验工具 root，不是产品码）

Task 已终态之后，`runner.py:sqlite3.connect` 抛 `file is not a database`。collect 记失败、不跑 retrieve。**产品 Task 不受影响。** 禁止把 Root-2 写成「五格都没跑」。

```text
lane_verdict      TOOL_RED
product_terminal  UNAFFECTED
fix               turso.connect (landed 9abb9b2)
```

禁止把 Root-2 的 `collect-exception` 与 Root-1 的 `STRUCTURE_*` 合成一条「R3 全红」。

## 4. 矩阵精确回放

### 4.1 Identity

| 轴 | 值 |
|---|---|
| domain | `documentation` |
| 提示词解析 | 无版本 → catalog 数值最新 = **g1 v3** |
| N 车道 | `priority=high` + `compression_channel=non-interactive` |
| Q 车道 | `priority=normal` + `compression_channel=local-inference` |
| 本枪后缀 | `-r3`（Q 另有车道后缀 `-qwen`，故 Q-A5 key=`…-qwen-r3`） |
| salvage | 不开 |
| extras | `--no-extras`；不开 A1/A4/A5g2/Q-A3 |

### 4.2 五枪总表

墙钟由 `received_at`–`completed_at` 计算。

| # | 格 | 墙钟 | 最远步 | Task | 码 | report | 池 |
|---|---|---:|---|---|---|---|---|
| 1 | N-A5 | 456s | publish | **succeeded** | 过程行残留 `CLAUDE_CLI_TRANSPORT_FAILED` 后恢复 | 无 fail report | NI,NI,NI,embed |
| 2 | N-A3 | 154s | structurize | failed | `STRUCTURE_ANCHOR_MISSING`（g0 非全文） | rejected · set=`0,1` · 9 块 · has_g0 | NI,NI |
| 3 | N-A6 | 834s | structurize | failed | `CLAUDE_CLI_OUTPUT_INVALID` | transport_failed · `empty_result` | NI,NI |
| 4 | N-A2 | 821s | structurize | failed | `STRUCTURE_GRANULARITY_SET_MISMATCH` | rejected · set=`0` · 1 块 · has_g0 | NI,NI |
| 5 | Q-A5 | 356s | structurize | failed | `STRUCTURE_ANCHOR_MISSING`（g0 非全文） | rejected · set=`0,1` · 11 块 · has_g0 | local,local |

markdown 5/5 succeeded。acquire…accept 5/5 succeeded。失败全集中在 B（structurize）。C 只在 N-A5 走到，`full_valid`。

### 4.3 唯一本枪成功格：N-A5

`PROVEN`：

- Task `succeeded`，`validate_publication` succeeded。
- prompt：structurize `json/promptB.documentation.g1.v3.md` v3；C `promptC.documentation.default` v2。
- `structure_document` 仍是 2 节点（root 容器 + 全文 paragraph，`end_byte=8109`）。与 R1 A5 / R2 Q-A3 相同，**不是** 8/14 假树判据。
- 真分层在 projection：`n=11`，`{0:1, 1:10}`。g1 original 99–1711 字，不是 g0 全文复制（g0 original 6924 字；封存 A5 正文 6925 字 / 8110 字节）。
- 向量：`g0+summary=1`；`g1+original=10`；`g1+summary=10`；**无** `g0+original`。符合 T-O-352。共 21。
- 六件套 validation 全是 `full_valid`。
- 池：markdown/structurize/construct = `non-interactive`，vectorize = `embed`。
- 第一次 CLI 运输失败：diagnostic `GEN_CLI_ENVELOPE` / `CLAUDE_CLI_TRANSPORT_FAILED`；随后同 process 成功。成功格不要求 fail report。过程行把首次 error_code 留在 `status=succeeded` 上，是记账污点，不是终态失败。

### 4.4 对照：R2 同格

| 格 | R2 第二枪 | R3 `-r3` |
|---|---|---|
| N-A5 | CLI 非对象 | **publish** |
| N-A3 | g0 锚失败 | g0 锚失败（同句） |
| N-A6 | mismatch（当时 `UNKNOWN` 是否吐 2） | **空信封** `empty_result`（换码） |
| N-A2 | mismatch（当时猜吐 2） | mismatch，report **set=0** |
| Q-A5 | g0 锚失败 | g0 锚失败 |
| Q-A3 | publish | 未开（按令） |

N-A5 是本枪相对 R2 唯一产品绿。N-A6 从「质量红」变成「运输红」。N-A2 第一次有形状。

### 4.5 未开闸门（DECISION 已在 `T-O-375`，执行遵守）

A1/A4/A5g2/Q-A3 同键未开。N-A5 已绿，A5g2 的 **门闩条件** 已满足，但本枪命令显式 `--no-extras`。这不是遗漏。

## 5. 根因

### 5.1 代码链（B 失败如何变成 typed 码 + 一等行）

```text
claude -p | LocalVllm structured_generate
  -> layered candidate
  -> LsragStructurizeService.admit
       g0.body != clean        -> STRUCTURE_ANCHOR_MISSING
                                  "The g0 body is not the complete clean artifact"
       body not substring      -> STRUCTURE_ANCHOR_MISSING
                                  "A layered body is not an exact clean substring"
       gran set != profile     -> STRUCTURE_GRANULARITY_SET_MISMATCH
  -> (NS4) stage report 同行
       admit 拒绝               disposition=rejected + histogram
       CLI 非 object            disposition=transport_failed + cli_structured_kind
  -> construct
       original mutated        -> CONSTRUCT_KERNEL_ORIGINAL_MUTATION
                                  （本枪未再出现）
```

CLI 在 admit 前若非 object → `CLAUDE_CLI_OUTPUT_INVALID` + kind。candidate 不入库。

### 5.2 分码归因

| 码 | 出现 | 等级 | 归因 |
|---|---|---|---|
| （无；publish） | N-A5 | `PROVEN` | 短 closure + NI + v3 能交 `{0,1}` 且 g0 全文。v3 在 **8KB 短文** 上有效。 |
| `STRUCTURE_ANCHOR_MISSING` / g0 非全文 | N-A3，Q-A5 | `PROVEN`（消息逐字） | 有 g0 也有 g1（9 块 / 11 块），但 g0.body ≠ clean。中长文（A3 17KB）与「同文换工人」（Q-A5 8KB Qwen）都会截断 g0。kernel 正确。 |
| `STRUCTURE_GRANULARITY_SET_MISMATCH` | N-A2 | `PROVEN`（report set=`0`） | profile `{0,1}`，候选 `{0}`。**不是** R2 猜的「吐 g=2」。v3 负例只打 g=2，没打「缺 g=1」。57KB qna 上工人停在步骤 3。 |
| `CLAUDE_CLI_OUTPUT_INVALID` / `empty_result` | N-A6 | `PROVEN` | 结构化通道空结果。无 candidate。834s 墙钟。不是 mismatch。 |
| `CLAUDE_CLI_TRANSPORT_FAILED` 残留 | N-A5 过程行 | `PROVEN` 诊断 + `LEADING` 重试 | 首次子进程失败后同步恢复。终态 succeeded。 |
| `CONSTRUCT_KERNEL_ORIGINAL_MUTATION` | — | 未出现 | F4 在走到 C 的格子上仍有效（N-A5）。 |
| `STRUCTURE_SUMMARY_INVALID` | — | 未出现 | F3 仍压住。 |
| `collect-exception` | R2 jsonl 五格 | `PROVEN` 工具 | 不是 kernel 码。见 Root-2。 |

### 5.3 为什么预检没发现

预检证明 v3 字面含「出现 granularity=2 则整包失败」，catalog 解析 v3，模型能 PING。它不跑 57KB B.json admit，也不验证「缺 g=1」会被工人当成合规。预检绿与 N-A2 红同时成立。

### 5.4 产品问题还是实验问题

Kernel 拒绝全部合理。v3 闭集写偏（禁超集、不禁真子集）是实验物料。N-A6 空信封是运输。runner sqlite3 是实验工具。问句维数本枪无需再修。

Q-A5 markdown invocation 的 `adapter_kind=claude_cli` 而 `dispatch_pool=local-inference`：`_cli_invocation_from_receipt` **写死** `adapter_kind="claude_cli"`。这是记账撒谎，**不是** salvage（池字段仍是 local）。`LEADING` 工具债。

### 5.5 失败 invocation 缺行

N-A3 / N-A2 / Q-A5：CLI 或 vLLM **交出了 object**，admit 拒绝。成功 callback 不跑，故没有 structurize invocation；CLI 例外分支也不走。只有 stage report。`T-O-375` 观测轴认 report，本枪 **够用**。R4 若要「失败 invocation 与 report 成对」，必须在 admit 拒绝分支补写 `status=failed` 的 invocation。N-A6 运输失败两条都有，对照清楚。

## 6. 车道深度判断

### 6.1 三条 generate 路

1. NI → `claude -p` → MiniMax（N 格）。本枪 N-A5 通、N-A3/A2/A6 红。
2. `local-inference` → vLLM Qwen（Q 格）。本枪只开 Q-A5，红。
3. salvage：未观察到。Q-A5 `generate_pools=["local-inference"]`，`lane_contaminated=false`。`PROVEN` 无换工人。

### 6.2 同一提示词、两个工人、同一短文

| 样本 | NI | Qwen |
|---|---|---|
| A5 8KB | **R3 publish** | R3 g0 锚失败（11 块，有 g0 有 g1） |
| A3 17KB | R3 仍 g0 锚失败（9 块） | R2 已 publish（本枪未重跑） |

`PROVEN`：A5 上 **MiniMax 能过、Qwen 不能**。R2 A3 上方向相反。写成「某车道已验证」必须带样本。禁止用 N-A5 洗白 NI 中长文，也禁止用历史 Q-A3 洗白 Q-A5。

### 6.3 为什么 N-A5 不能写成「v3 已成功」

四格仍红。N-A2 是 v3 自己的假说靶。把 N-A5 升级成 H2 通过，等于用短文成功洗白闭集。家族手法禁止。

### 6.4 为什么不能原样 replay v3

N-A2 的失败形状说明 v3 负例打错了边。再 `--rerun` 同一 v3 字节没有新假说。R4 必须改「集合必须 **恰好** `{0,1}`」的可执行负例（缺层与多层同时打），或承认 57KB qna 的 g1 切章本 run 失败并缩范围。

## 7. 当前 continuation 的实际缺口

### 7.1 admit 失败仍无 candidate 化石

直方图够给 mismatch 分型。g0 锚失败仍不知道截断了多少——report 不落原文（正确）。R4 不得为了看截断而把 body 写入 extra/report。

### 7.2 重建库会丢掉两份索引

现在 serving = Q-A3 17 + N-A5 21。`rm mkb.turso.db` 会同时丢掉 R2 与 R3 的唯一 publish。R4 `DECISION`：失败格用 `-r4` 追加。

### 7.3 金标语料仍不足

H3 六问依赖 A2/A4/A5/A1/A6。现在有 A3+A5。Q-MIXIN 可评。Q-POOL 期望 A6，现打到 A5 closure。Q-V5R 期望 A2。Q-GLOSS 期望 A1。扩语料前不得宣称 H3 通过。

### 7.4 A5g2 门闩 vs 命令

门闩条件已满足。冻结命令仍禁 extras。R4 若开 A5g2 必须 **另写一格**、另点头，不得夹带进 mismatch 修复枪。

## 8. 对上一轨的有效性评价

### 8.1 R2 目标（§9.3 `R3_READY`）

```text
Q-A3 serving intact                         YES
at least one of {N-A5, Q-A5} publish        YES (N-A5)
zero GRANULARITY_SET_MISMATCH on -r3 g1     NO (N-A2)
retrieval re-score no Layer A 422           YES
no kernel patch                             YES
Q cells not lane_contaminated               YES
```

`R3_READY` **未达成**。token 仍 `conditional-ready`。R2 把 mismatch 写成「吐 g=2」是 `LEADING` 错边；R3 证据把它改写成「缺 g=1」。

### 8.2 g1 v3（R3-B / R3-03）

```text
killed extra g=2 on N-A2                    NOT OBSERVED (no g=2 this gun)
killed missing g=1                          NO — 这正是 N-A2
enabled N-A5 NI publish                     LEADING (短文×工人×v3 交互；无 v2 对照枪)
killed N-A3 g0 anchor                       NO
killed Q-A5 g0 anchor                       NO
killed N-A6 empty envelope                  NO (非提示词)
```

总体：`PARTIAL EFFECTIVE`。对「不要切到 2」可能有效（本枪未见 g=2），对「必须切出 1」无效。

### 8.3 NS4 证据面

```text
stage report on admit reject                EFFECTIVE (N-A3/N-A2/Q-A5)
stage report + kind on CLI empty            EFFECTIVE (N-A6)
failed invocation on CLI empty              EFFECTIVE (N-A6)
failed invocation on admit reject           MISSING (3 格)
latency_ms                                  BROKEN (硬编码 0)
extra as proof                              NOT USED (正确)
ReadPort / 禁 dump                          本枪记分走 SQL/对象，未走 inspect_dump
```

`EFFECTIVE WHERE WIRED`；admit-fail invocation 与 latency 是债。

### 8.4 F3 / F4 / F5（跨 run 复查）

```text
F3 summary-null / date-object               STILL HOLD (本枪未再出现这两码)
F4 C original                               EXERCISED on N-A5 PASS
F5 query dim                                STILL HOLD 6/6 200
```

### 8.5 runner sqlite3

```text
source                                      EFFECTIVE BUG
live 5/5 journal lie                        PROVEN
fix turso.connect                           LANDED after the wave
reconstructed journal                       THIS DIRECTORY
```

## 9. R4 目标、真相约束与成功定义

### 9.1 目标

1. 保住 **Q-A3 + N-A5** 两份 serving（不无故重建库）。
2. 让 g1 工人在 A2 体量上不再因 **缺层** 触发 `GRANULARITY_SET_MISMATCH`（真子集与超集都要打）。
3. 保持观测轴：失败格必须有 stage report；admit 拒绝补 failed invocation。
4. 金标按篇记，不把 A5 语料上的 Mixin 命中说成全矩阵 H3 通过。
5. N-A3 g0 锚、N-A6 空信封 **登记为残差**，不把它们绑进「v4 闭集是否生效」的唯一闸——除非业主把范围扩成「中长文也必须绿」。

### 9.2 必须保持的 invariants

- 不放宽 `layered_content.v1` / admit kernel。
- 不改 stub，不静默 salvage。
- 不改 R1 结论三件套；不回写 R2/R3 已发生 jsonl/Task。
- documentation 提示词仍禁止大写 `MKB` 字面、禁止 `semantic_block`。
- Q 格必须显式 `local-inference`；N 格必须 NI。
- 证据不得只活在 `payload_extra`。
- 禁止 `rm` `mkb.turso.db` / `mkb.db`。

### 9.3 完成标准

```text
R4_READY
  = Q-A3 serving intact (17)
  + N-A5 serving intact (21)
  + zero GRANULARITY_SET_MISMATCH on this -r4 g1 set
  + retrieval re-score has no Layer A 422
  + no kernel patch
  + Q cells not lane_contaminated
  + every -r4 failure has a stage report
```

未达则 token 仍为 `conditional-ready`。若 Q-A3 或 N-A5 serving 消失且无替代 publish → `not-ready`。

N-A3 锚失败、N-A6 空信封 **单独记分**，不否决「闭集假说是否打中」；它们可以否决一个更宽的「NI 中长文 ready」叙事——本报告 **不** 把那条叙事写成 R4_READY。

## 10. R4-EVD：证据面补洞

### 10.1 `R4-EVD-01` — admit 拒绝也写 failed invocation

输入：CLI/vLLM 已得 object，`admit` 抛 `STRUCTURE_*`。  
输出：`mkb_generation_invocations` 一行 `status=failed`，`stage_key=structurize`，`error_code` 为产品码；stage report 仍写。  
验收：再打 N-A3 类失败时 invocation 与 report 成对。禁止把 candidate body 写入 extra。

### 10.2 `R4-EVD-02` — 成功重试不得留下首次 error_code

输入：N-A5 类「先运输失败后成功」。  
输出：succeeded process 的 `error_code` / `error_message` 为空。诊断可留在 sidecar。  
验收：单测或再出现重试时 `status=succeeded AND error_code IS NULL`。

### 10.3 `R4-EVD-03` — `latency_ms` 不得硬编码 0

输入：`generation_construct.py` 现写 `"latency_ms": 0`。  
输出：admit/CLI 失败 report 使用 `monotonic` 差值。  
验收：新失败行 `latency_ms > 0`（除非确为 0ms 夹具）。

### 10.4 `R4-JRN-01` — runner 只走 Turso

状态：`9abb9b2` 已落地。R4 预检必须断言 `sqlite3.connect` 不在 runner 读库路径。不再重做。

### 10.5 `R4-LANE-01` — invocation.adapter_kind 跟运输走

输入：Q markdown 池是 local，行上却是 `claude_cli`。  
输出：`_cli_invocation_from_receipt` 不再写死；按 `receipt["transport"]` 映射 `claude_cli` / `local_vllm`。  
验收：Q 格 markdown invocation.adapter_kind ≠ `claude_cli`（当池为 local-inference）。

## 11. R4-B：g1 恰好集

### 11.1 `R4-B-01` — 提示词 v4

**新建** `data/prompts/json/promptB.documentation.g1.v4.md`，不覆盖 v3。  
相对 v3 **只改闭集语义**，不重写步骤哲学、不加长中文说教：

- 首句改为：冻结集合 **恰好** `{0,1}`。只交 g=0、只交 g=1、出现 g=2，三者整包失败。
- 步骤 4 加一句：必须至少一块 g=1。禁止交完 g0 就停。
- 步骤 6.2 写成三条硬核：`set == {0,1}` **且** `count(g=0)==1` **且** `count(g=1)>=1`。
- 反例增加：`只交一块 granularity=0`；`只交 g=1 没有 g=0`。
- 正例 JSON 仍不得出现 `"granularity":2`。
- 仍禁止大写 `MKB`、`semantic_block`。

catalog：`DEFAULT_CATALOG_PROMPTS` g1 → v4；bootstrap retire v3。现库 `register_prompt` 与 R3 相同（retire+insert）。已 serving 的 N-A5 / Q-A3 快照钉旧 hash，不回写。

### 11.2 `R4-B-02` — 物料测试

`test_ns1_prompt_bodies`：v4 必须含「只交一块 granularity=0」或等价「缺 g=1 整包失败」；不得含 `"granularity":2` 正例。catalog `prompt_version=="v4"`。

### 11.3 `R4-B-03` — 重跑集

`N-A3, N-A6, N-A2, Q-A5` + `-r4`。  
**禁止** 重跑 N-A5 / Q-A3 同键。  
A5g2 / A1 / A4 默认 0；另令另枪。

## 12. R4-RET / R4-RES

### 12.1 `R4-RET-01`

不改维数逻辑。重打金标。验收：无 422。按篇记：Mixin 可对 A5；POOL/V5R/GLOSS 在缺篇时记 `corpus-miss`，不得记 `gold-fail-against-wrong-doc` 当运输失败。

### 12.2 `R4-RES-01` — 残差登记（不修则必须写明）

| 残差 | 为什么本枪不绑进 R4_READY |
|---|---|
| N-A3 NI g0 锚 | 17KB × MiniMax 已三枪同码；再加厚步骤 3 违反「不靠堆字放行」 |
| Q-A5 Qwen g0 锚 | 同文 NI 已绿；换工人不是闭集问题 |
| N-A6 empty_result | 运输空包；v4 改不了空信封 |

若业主要把三者纳入 ready，必须另开范围，不得偷偷写进闭集验收。

## 13. Exact scope control

### 13.1 allowlist

g1 v4 提示词 + catalog retire、admit-fail invocation、清掉成功行残留 error_code、report `latency_ms`、adapter_kind 映射、R4 runner 后缀、分析/台账、既有 turso 读库。

### 13.2 denylist

`src/contracts/lsrag/**` 放宽、stub、改 R1/R2 `results/analysis.md`、默认 `rm` serving 库、Mixin、改生产默认 binding、把 A5g2/A1/A4 塞进闭集修复枪、把 candidate body 写入 extra/report、为 N-A3 单独加厚三千字步骤。

### 13.3 tripwire

diff 若改 `layered_content.py` / `adopt.py` 拒绝条件 → 停。  
Q 格 `generate_pools` 含未声明 `non-interactive` → 该格作废。  
Q-A3 17 或 N-A5 21 消失且无替代 publish → `not-ready`。  
R4 jsonl 再出现 `collect-exception` 且库里 Task 已终态 → 工具回归，停封条。

## 14. Mandatory local test matrix

```text
tests/unit/test_ns1_prompt_bodies.py
tests/unit/test_ns1_prompt_catalog.py
tests/unit/test_ns4_stage_report_contract.py
tests/unit/test_structure_reject_histogram.py
tests/unit/test_claude_cli_port.py
tests/domain/test_r3_launch_lock.py          # runner 无 sqlite3.connect
tests/integration/test_r3_turso_evidence_ready.py
.experiment/0815/runs/MKB-0815-R3/preflight.py   # 新 R4 预检另立，不得要求零 -r3
```

不得用「再跑一遍五格」代替上述门。Live 重跑是 `R4-B-03`，需业主点头。

## 15. R4 执行工作台账

当前除已落地项外均为 `PLANNED / NOT EXECUTED`。

| ID | 工作项 | 输入证据 | 精确输出 | 验收 |
|---|---|---|---|---|
| `R4-00` | 冻结本分析 | 本文件、Turso、重建 jsonl | 本文落盘 | 本文件 |
| `R4-01` | admit-fail invocation | §5.5 三格缺行 | EVD-01 补丁 + 单测 | 失败双行 |
| `R4-02` | 成功行清 error_code | N-A5 残留 | EVD-02 | succeeded ⇒ code null |
| `R4-03` | report latency | 源码 `latency_ms: 0` | EVD-03 | 非零（非夹具） |
| `R4-04` | adapter_kind 映射 | Q-A5 markdown 撒谎 | LANE-01 | local 池 ≠ 假 claude_cli |
| `R4-05` | g1 v4 + catalog | N-A2 set=`0` | B-01/02 | 物料测绿 |
| `R4-06` | 带后缀重跑 4 格 | R4-05 + 现库 | 新 `-r4` Task | 零 mismatch |
| `R4-07` | 重打金标 | N-A5 ∪ Q-A3 ∪ 新 publish | `inspect/retrieval` | 无 422；按篇记 |
| `R4-08` | 封条或继续 RED | R4-06/07 | 新 run 或附录 | 不改 R1 |

### 15.1 Dependency DAG

```text
R4-00
  -> R4-01
  -> R4-02
  -> R4-03
  -> R4-04
  -> R4-05
R4-01 + R4-02 + R4-03 + R4-04 + R4-05
  -> WAIT_OWNER_LIVE
      -> R4-06 -> R4-07 -> R4-08
```

`WAIT_OWNER_LIVE` 之前不得创建新 ingest Task。

### 15.2 Commit discipline

建议窄提交：

1. `fix(evidence): write failed structurize invocation on admit reject`（R4-01）
2. `fix(evidence): clear process error_code after successful retry`（R4-02）
3. `fix(evidence): record stage-report latency`（R4-03）
4. `fix(0815): map markdown adapter_kind from transport`（R4-04）
5. `feat(prompts): documentation g1 v4 exact-set`（R4-05）
6. `docs(0815): freeze R3 FF10-family analysis`（本文）

禁止与 kernel 放宽混提。

## 16. 后续 live 前必须冻结的预算包

| 字段 | 计划上界 |
|---|---|
| 新格 | 最多 4（N-A3,N-A6,N-A2,Q-A5） |
| A5g2 / A1 / A4 | 默认 0 |
| 单格墙钟 | 维持：A5 15min，A3/A6 30min，A2 60min |
| 库 | 禁止删 `mkb.turso.db`；Q-A3 17 + N-A5 21 tripwire |
| 重试 | 每格 1 次；超时记 `timeout` |
| 停止 | 静默 NI salvage、Q-A3/N-A5 serving 丢失、jsonl 再 collect-exception 且库已终态 |

## 17. Release 与 preflight 边界

R4 计划改提示词、失败 invocation、latency、adapter_kind 与文档。若 diff 改 `validate_layered_content` / `adopt.py` 拒绝条件：停。

新预检必须：013 在、两份 serving 计数、runner 无 sqlite3 读库、g1 解析 v4、**允许** 已有 `-r3` 键。不得把「零 -r3」再当闸。

`--suffix -r4` 必须写成 `--suffix=-r4`。argparse 把 `--suffix -r4` 当成新 option（本枪已踩过）。

## 18. 登记但不执行

- documentation markdown flavor v1 仍无编号步骤。5/5 markdown 过，不是瓶颈。
- A1/A4 体量风险。
- A5g2 门闩已开，本枪/本 R4 默认不开。
- Lightning 仍未绑 generate。
- 检索 hit 的 `channel` 字段在 response JSON 里是 `None`（payload 仍是 original 正文）。不在本枪改检索投影。
- N-A5 structure_document 2 节点：继续按 projection 评 H2，不写成假树。

## 19. 风险、rollback 与 falsifier

| 风险 | 对策 |
|---|---|
| 再重建库丢掉双 publish | 后缀新键；tripwire 17+21 |
| 把 N-A5 2 节点写成假树 | 分层看 projection |
| 把 Q-MIXIN 命中写成 H3 全过 | 金标必须逐问对期望篇 |
| 把 v4 说成已修 N-A3 锚 | §12.2 残差表 |
| 用 salvage 救 Q | 扫描池字段 |
| 把 collect-exception 当产品码 | Root-2 纪律 |

Rollback：提示词回退到 R3 封存 `subjects/data/prompts/json/promptB.documentation.g1.v3.md`。证据面补丁回退会使 admit-fail 再缺 invocation，可接受为观测降级，不得回退 kernel。R1 封条不可 rollback。

Falsifier：若复现 N-A2 时 report `set` 含 2 且不含「缺 1」，§5.2「真子集」归因作废，改回 R2 超集叙事。若 Q-A5 `generate_pools` 含 `non-interactive` 且无声明，车道结论作废。

## 20. Final verdict

### 20.1 R3 归因

```text
H1 transport          PASS on N-A5 NI; N-A6 empty_result residual
H2 structure          PARTIAL
                      N-A5 projection 1+10 PROVEN real cut
                      N-A2 missing-g1 PROVEN
                      N-A3/Q-A5 g0-not-full PROVEN
H3 retrieval          TRANSPORT PASS / GOLD PARTIAL (A5 mixin only)
obs plane             SUFFICIENT (reports); invocation pair INCOMPLETE
silent swap           NO
kernel                NOT RELAXED
R1/R2 conclusions     UNTOUCHED
journal               TOOL BUG (fixed after wave)
```

### 20.2 v3 / NS4 评价

```text
g1 v3                 PARTIAL EFFECTIVE (forbids 2; permits missing 1)
NS4 reports           EFFECTIVE
NS4 fail invocation   PARTIAL (CLI only)
F3/F4/F5              HOLD
```

### 20.3 R4 方案评价

修复面由证据收在：v4 **恰好集**、admit-fail invocation、成功行 residual code、latency、adapter_kind、保住双 serving 后的 `-r4`。它没有要求改 kernel，也没有把 N-A5 单格成功写成族级 `ready`，也没有把 N-A3 锚失败绑死在闭集闸上。

业主要求的「R2 密度分析 + R4 台账 + 详细修复说明」的可接受输出是：

```text
freeze RCA in results/analysis.md
  + keep R2 analysis immutable
  + keep Q-A3 17 and N-A5 21
  + R4 live only after owner tick
```

本报告输出时的最终状态是：

**`R3 RCA COMPLETE / R3_READY FAIL (N-A2) / R4 PLAN DRAFTED / NOT SEALED / NO NEW INGEST`**。

## 22. R4 代码增强说明书（施工级）

§10–§15 写「改什么、怎么验收」。本节写 **改哪个函数、带什么字段、禁止写什么**。未写到的文件默认不动。

### 22.1 `R4-EVD-01` — admit 拒绝补 invocation

**允许改的文件**

| 文件 | 点 | 做什么 |
|---|---|---|
| `src/runtime/intake/generation_construct.py` | `_structurize` 在 `admit` / `adopt` 抛 `STRUCTURE_*` 的 `except` | `record_pending_generation_evidence(invocation=..., report=...)` |
| 同上 | 已有 CLI `except MkbError` 分支 | **保持**；不要重复插入 |
| `tests/unit/test_ns4_stage_report_tx.py` 或新测 | 单测 | mock admit 失败后 pending 含 failed invocation + report |

invocation 闭集字段（禁止 body）：

```python
{
  "invocation_uuid": uuid7(),
  "invocation_ordinal": 0,
  "process_attempt": command.fencing_generation,
  "capability_key": "structured_generate",
  "stage_key": "structurize",
  "input_digest": stable_digest({"clean_digest": state.get("clean_digest"), "stage": "structurize"}),
  "status": "failed",
  "error_code": exc.code,          # STRUCTURE_*
  "adapter_kind": "claude_cli" | "local_vllm",  # 按 channel
  "cli_structured_kind": None,     # admit 失败时已是 object
}
```

约束：

- 已有 object 时 **不要** 再写 `cli_structured_kind`。
- report 继续用现有 histogram；`latency_ms` 走 §22.3。
- 成功路径零行为变化。
- kernel 拒绝条件不改。

Q 车道：`generation_invocation` 已在 live 调用里建成且 `status=succeeded`。admit 失败时应 **改写为 failed** 再 stash，或另 stash 一条 failed。禁止成功 callback 与失败 stash 双写同一 uuid。推荐：admit 失败则 `generation_invocation["status"]="failed"; generation_invocation["error_code"]=exc.code` 后 `record_pending_generation_evidence`。

### 22.2 `R4-EVD-02` — 成功行清码

**允许改的文件**：`src/runtime/workflow/runtime_outcome.py` 成功落库，或 process 最终 `UPDATE`。

规则：`status='succeeded'` 的 process **必须** `error_code IS NULL AND error_message IS NULL`。首次 CLI 失败只进 diagnostic sidecar（已有 `GEN_CLI_ENVELOPE`）。

单测：模拟两次 generate、第一次抛运输错、第二次成功，读 process 行无 error_code。

禁止：为了清码而删除 diagnostic。

### 22.3 `R4-EVD-03` — latency

`generation_construct.py` 两处 `"latency_ms": 0`（约 1003、1050 行，admit-fail report）改为：

```python
"latency_ms": max(0, int((time.monotonic() - started) * 1000))
```

`_structurize` 入口附近已有/应设 `started = time.monotonic()`。夹具可传 0。禁止把墙钟写成 LLM 内部 thinking 时长的猜测。

### 22.4 `R4-LANE-01` — adapter_kind

`_cli_invocation_from_receipt` 现在写死 `adapter_kind="claude_cli"`。改为：

```python
transport = receipt.get("transport")
adapter = "local_vllm" if transport == "api_inference" else "claude_cli"
```

`local-inference` 的 markdown 走 `_live_markdown_text`，receipt.transport 已是 `api_inference`（见 `generation_construct.py` 约 541 行）。

禁止：用 adapter_kind 回写 `dispatch_pool`。池仍是 dispatch 的 SSOT。

### 22.5 `R4-B-01` — v4 提示词必须新文件

与 R3 v3 相同治理：

1. 新建 `promptB.documentation.g1.v4.md`，不改 v3 字节（N-A5 快照可能钉 v3 hash）。
2. `DEFAULT_CATALOG_PROMPTS` g1 → `v4` + 新路径。
3. 现库 `register_prompt` retire+insert；禁止只 bootstrap。
4. 正文相对 v3 **只加恰好集**，见 §11.1。
5. 测试见 §11.2。

### 22.6 `R4-B-03` — runner / 库

| 文件 | 改动 |
|---|---|
| R2 `collect.py` / `runner.py` | `--suffix=-r4`（等号形式） |
| 预检 | serving 计数 Q-A3=17 且 N-A5=21 则 pass |
| 格子 | 仅四格；`--no-extras` |

禁止 `rm` 库。禁止默认 FIRST_WAVE 再带 Q-A3。

### 22.7 明确不改的代码

| 路径 | 原因 |
|---|---|
| `src/contracts/lsrag/layered_content.py` 拒绝条件 | kernel 不放松 |
| `src/services/lsrag_compiler/adopt.py` 的 g0/substring/set 规则 | 同上；N-A2/N-A3 的码是对的 |
| `ns1_cli_mode=stub` | 禁止假绿 |
| `_can_salvage_local_inference` 放宽 | 禁止静默换工人 |
| R1 / R2 `results/analysis.md` | 已冻叙事 |
| 覆盖 N-A5 / Q-A3 的同 `external_key` | 丢掉索引 |
| 为看截断把 g0 body 写入 report | 违 T-O-366 / S16 |

### 22.8 与 §15 台账的对应

| 台账 | 本节 |
|---|---|
| R4-00 | 本分析已落盘 |
| R4-01 | §22.1 |
| R4-02 | §22.2 |
| R4-03 | §22.3 |
| R4-04 | §22.4 |
| R4-05 | §22.5 |
| R4-06 | §22.6 |
| R4-07 / R4-08 | live / 封条，无新生产代码 |

## 21. 执行日志回填

live 发车时序在族方案 `.experiment/0815/after-NS3-test-plan.md` **§14**。本文件不重抄，以免两份执行日志分叉。

R1 §10、R2 §11、R3 预检 §13 禁止改。

### 21.6 文档状态

`scored-short → rca-frozen（2026-08-17）`。  
封条：未做。需要封条时另点头，且必须先冻结本文件字节的 MD5。
