# Non-interactive agentic pipeline

> **项目**：`myknowledgebase`（MKB）
>
> **文档性质**：`eval / new-start`（探索记录，**不是** frozen domain-truth）
>
> **文档状态**：`draft / owner-review`
>
> **日期**：`2026-08-14`
>
> **作者**：`Grok`（本会话实测 + 与业主约定对齐）
>
> **权威输入**：
> - 业主口头约定（本会话）：promptA–C 改为 system instruction；`-p` 只放物料或链接；`--json-schema` 是 promptB 交卷的分层分粒度 JSON
> - Claude Code CLI reference：<https://code.claude.com/docs/en/cli-reference>
> - Claude Code headless / `-p`：<https://code.claude.com/docs/en/headless>
> - 已冻产品分账：`docs/baseline/domain-truth/D05-layered-semantic-rag-handbook.md`（`T-O-208` / `T-O-210`）
> - 本机实测：`claude` 2.1.229 · `/tmp/claude-p-tests/test{1..5}.*`
>
> **本文不改写**：S03 状态机、S04 接受事务、S05 四类 source kind、D08 四域变换 SSOT、S14 prompt hash 指针纪律。

---

## 0. 一句话

用本机 `claude -p` 做无人值守三次调用：`--system-prompt` 分别是 promptA / B / C；`-p` 只放待处理正文或链接；`--json-schema` 只约束 **promptB 完成后** 的分层分粒度 JSON。S05 获取/封口/准入与 S04 接受仍然在 Claude 之外。

---

## 1. 对这条管线的认知

### 1.1 与 baseline v1 的关系

D05 冻结的生产链不变：

```text
promptA@clean → promptB@structurize → promptC@construct → gate → vectorize
```

三身份语义也不变：

| 身份 | 规范名 | 必须做到 | 明确不做 |
|---|---|---|---|
| promptA | CleanPrompt | 源证据 → 可结构的 clean 正文；保真、去噪、不加事实 | 不做 0/1/2 structure；不产权威 summary；不写向量 |
| promptB | StructurePrompt | 在 **已清洗** 正文上切粒度 0/1/2 Original 骨架 | 不洗源 HTML；不填 dual-channel summary；不改 clean 权威 |
| promptC | SummaryPrompt | 为应有 unit 填 grounded SummaryChannel | 不改写 Original；不跳过 g=0 |

变的是 **模型怎么被调用**，不是 **A/B/C 各自负责什么**。

旧路径：MKB `S11` facade（`structured_generate` / `text_generate`）读冻结 `PromptRef`，把 prompt 正文和物料拼进同一套 inference request。

新路径：三次独立的 Claude Code 非交互进程。身份在 system 通道，物料在 user 通道，B 的形状由 CLI `--json-schema` 卡住。

### 1.2 三通道拆开

| CLI 通道 | 放什么 | 不放什么 |
|---|---|---|
| `--system-prompt` 或 `--system-prompt-file` | 该轮的 promptA / B / C 全文 | 待处理正文、URL、上一轮 JSON |
| `-p` / stdin | 这一轮物料：正文，或指向正文的链接 | 清洗/结构化/摘要指令 |
| `--output-format json --json-schema` | **仅 promptB**：已清洗完成、按层按粒度切开的 JSON 合同 | promptA 的纯文本形状；promptC 的摘要通道形状（除非另开一轮 schema） |

`--system-prompt` **整段替换** Claude Code 默认身份（工具说明、安全说明、编码惯例一并丢掉）。这正是无人值守管线要的：A/B/C 是加工工人，不是仓库里的 coding assistant。

`--append-system-prompt` 不适用本模式：它会把默认 Claude Code 身份留下来。

### 1.3 三次调用

```text
源内容或链接
    │
    │  --system-prompt = promptA
    │  -p              = 原文 / URL
    ▼
clean 正文
    │
    │  --system-prompt = promptB
    │  -p              = 上一轮 clean 正文
    │  --json-schema   = 分层分粒度 StructureSchema
    ▼
structure JSON（g=0 全文 / g=1 章 / g=2 段 · Original 骨架）
    │
    │  --system-prompt = promptC
    │  -p              = 这份 structure JSON
    ▼
在已有分层上补 grounded Summary，不改 Original
```

物料前移规则：

1. A 的 `-p` 是源证据（或链接）。
2. B 的 `-p` 是 A 的 clean 正文，不是生 HTML。
3. C 的 `-p` 是 B 的 `structured_output`，不是源、也不是 clean 纯文本。
4. `--json-schema` 卡在 **B 之后**。A 默认只要可进入 B 的正文；C 吃 B 已经切好的树。

链接与工具：

- `-p` 里是**已经在参数或 stdin 中的字节**时，应用 `--tools ""`，禁止模型乱跑。
- `-p` 里是**链接**时，该轮必须显式允许取链工具（例如 WebFetch / Read），并在 system 里写明只取该链接、不改写身份。`--bare --tools ""` 取不到远程字节。
- stdin 上限 10MB；更大物料先落 S13 / 本地文件，`-p` 只传路径或 handle。

### 1.4 推荐调用形

脚本/CI 用 `--bare`：不读 hooks、plugins、CLAUDE.md、keychain。文档写明 `--bare` 将来会成为 `-p` 默认。本机 `--bare` 能通，是因为环境已有 `ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL`；官方 Anthropic 订阅 OAuth 在 `--bare` 下不会被读到。

```bash
# A：system = 清洗身份；-p = 物料
claude --bare -p "$CONTENT_OR_URL" \
  --system-prompt-file data/prompts/prompt-a-clean-v1.md \
  --tools "" --max-turns 1

# B：system = 结构化身份；schema = 分层分粒度合同
claude --bare -p "$CLEAN_TEXT" \
  --system-prompt-file data/prompts/prompt-b-structure-v1.md \
  --output-format json \
  --json-schema "$STRUCTURE_SCHEMA" \
  --tools "" \
  | jq '.structured_output'

# C：system = 摘要身份；-p = B 的 JSON
claude --bare -p "$STRUCTURE_JSON" \
  --system-prompt-file data/prompts/prompt-c-summary-v1.md \
  --tools ""
```

B 的结果取 `.structured_output`（已解析对象），不要自己从 markdown 里抠 JSON。包装层的 `.result` 是同一份 JSON 的字符串。

`--max-turns 1` 适合 A 的纯文本轮。B 加 `--json-schema` 时 CLI 会走内部 structured-output 工具，实测会出现 `num_turns: 2` 和 `stop_reason: tool_use`；B 不要用 `max-turns 1` 卡死。

### 1.5 JSON schema 在本模式中的位置

本模式的 schema **不是** Claude 包装信封（`type/result/session_id/usage`），而是 B 交卷的业务形状：清洗完成后的分层分粒度结构。

对应 D05 / 现有 compiler 心智：

```text
promptA                  →  clean bytes / 正文
promptB + StructureSchema →  g=0/1/2 Original 骨架
promptC                   →  Summary 通道完备
ContentFullRecipe         →  embed 输入（确定性，仍不是 Prompt）
```

现有内存形状可作 schema 起草起点（尚未改成 CLI `--json-schema` 文件）：

- `StructureDocument` + `RetrievalBlock.granularity ∈ {0,1,2}`（`src/services/lsrag_compiler.py`）
- registry 键 `lsrag.structure.default@v1`
- D05 例：`GenerationScopedCoordinateV1` / 每 unit 的 original 通道

C 之后才要求 dual-channel 完备。本模式 **不** 把 dual-channel 塞进 B 的 schema。

---

## 2. 本机测试结果

测试日：`2026-08-14`。工作目录：`/tmp/claude-p-tests`。五次均 **exit 0**，stderr 为空。

### 2.1 环境

| 项 | 实测值 |
|---|---|
| 二进制 | `/root/.local/bin/claude` · native **2.1.229**（commit `10b3e93beb60`） |
| `claude auth status` | `loggedIn: true` · `authMethod: oauth_token` · `apiProvider: firstParty` |
| 实际推理端点 | `ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic` |
| 实际模型 | `ANTHROPIC_MODEL=MiniMax-M3`（`modelUsage` 键为 `MiniMax-M3`） |
| 脚本模式 | `--bare --max-turns 1 --tools "" --effort low` |
| 认证注意 | `--bare` 不读 OAuth/keychain；本机靠环境 token 打到 MiniMax 兼容端。不是 `api.anthropic.com` |

### 2.2 用例

**Test 1 · 基础 `-p`**

```bash
claude -p "Reply with exactly this token and nothing else: PING_OK" \
  --bare --max-turns 1 --tools "" --effort low
```

stdout：`PING_OK`

**Test 2 · `--system-prompt` 替换默认身份**

系统提示要求每条回复以 `MKB_SYS_OK` 开头。用户问 `2+2`。

stdout：`MKB_SYS_OK 4`

结论：替换后的 system instruction 生效，不是默认 coding assistant。

**Test 3 · `--output-format json`**

用户要求只回 `JSON_OK`。单行 JSON，关键字段：

| 字段 | 值 |
|---|---|
| `type` | `result` |
| `subtype` | `success` |
| `is_error` | `false` |
| `result` | `JSON_OK` |
| `stop_reason` | `end_turn` |
| `num_turns` | `1` |
| `modelUsage` | `MiniMax-M3` |
| `total_cost_usd` | `0.001839…` |
| `duration_ms` | `5418` |

另有 `session_id`、`usage`、`uuid`。脚本用 `jq -r '.result'` 取正文。

**Test 4 · `--system-prompt` + `--output-format json`**

`result` = `"MKB_SYS_OK 2 plus 2 equals 4."`

结论：身份替换与 JSON 包装可同时用。

**Test 5 · 再加 `--json-schema`**

schema：`{clean_text, token}`（探测 CLI 合同，**不是** 生产 StructureSchema）。system 自称 promptA 保真清洗。

返回同时有：

- `result`：schema 的 JSON **字符串**
- `structured_output`：已解析对象  
  `{ "clean_text": "<p>Hello <b>world</b> from MKB.</p>", "token": "cleaned-fragment-1" }`

`num_turns: 2`，`stop_reason: tool_use`。schema 路径会走内部 structured-output 工具，不是纯单轮文本。

生产 B 应读 `.structured_output`，并在 MKB 侧再跑现有 structure kernel / digest，不把模型对象直接当 S06 current。

### 2.3 从测试得到的操作结论

1. 本机 `claude -p` 作为非交互工人可用。
2. `--system-prompt` 足以承载 A/B/C 身份。
3. `--output-format json` 给出可脚本化信封（结果、会话、用量、费用估计）。
4. `--json-schema` 给出可直接消费的 `structured_output`，适合作为 B 的交卷门闩。
5. 当前模型是 MiniMax-M3，不是 Anthropic 官方模型；行为与延迟以本次为准。
6. `--bare` 适合管线；生产包装必须显式提供 token / base URL，不能假设交互登录在脚本里仍然有效。

---

## 3. 预期对我们内部流程的改动

本文只记**预期改动方向**。未改代码，也未 reopen 已冻 `T-O-*`。落地前要 owner 确认 §5。

### 3.1 仍然留在 MKB 内（不要交给 `claude -p`）

| 步骤 | 权威 | 原因 |
|---|---|---|
| Task / Execution / Process 围栏、retry、lease | S01–S03 | CLI 进程不是第二套状态机 |
| 四类 source 的 acquire / decode / ExternalKey / CandidateSet seal / preflight / gate | S05 + D08 | 链接只是 A 的物料形态之一；获取证据、双 digest、空集证明仍要 typed |
| Snapshot / Item / Revision 接受 | S04 | handler 成功 ≠ accepted Intake |
| 确定性 structure kernel、projection、digest、validation report | S06 | 模型 JSON 是候选，kernel 才是 current |
| ConstructToVectorizeGate、dual-channel 完备、g=0 在场 | S07 / `T-O-206` | 不因换工人而跳过门闩 |
| vectorize / publication / retrieval | S08–S10 | 不是第四个生产 Prompt |
| prompt 正文 git + DB 仅 hash 指针 | S14 / D03 | 即使改走 CLI，仍禁止 DB 存第二份可编辑正文 |
| 对象落盘与 verify-on-read | S13 | CLI stdout 不是 artifact SSOT |

### 3.2 预期要换的调用缝

今天 live 路径（`src/runtime/intake/generation_construct.py`、`generation_live.py`）：

- S06：`_live_structured_generate(..., prompt_key="promptB.default", schema_key="lsrag.structure.default")`
- S07：`_live_text_generate(..., prompt_key="promptC.default")` 按 block 循环
- S05 LLM clean：`dispatch_clean` + 冻结 `CleanPrompt`（`promptA.default.v1`）

预期改成：上述三处不再把 prompt 正文喂给 S11 `structured_generate` / `text_generate`，改为 spawn `claude -p`：

| 现 Process | 新工人 | system | `-p` | schema |
|---|---|---|---|---|
| `clean.extract.*`（llm / vision / ocr 需要模型时） | `claude -p` | promptA | 已获取的解码正文，或经允许的链接 | 无（正文）；确定性策略仍走 `intake/`，不经 Claude |
| `lsrag.structurize` | `claude -p` | promptB | A 的 clean 正文 | **有**：分层分粒度 StructureSchema |
| `lsrag.construct` Summarizer | `claude -p` | promptC | B 的 structure JSON | 可选；默认不占用 B 的 schema |

S11 facade 可以降为：embed / rerank / 非 A-B-C 推理。A/B/C 的 invocation ledger 仍要写（session_id、usage、modelUsage、content_hash、exit code），只是 transport 从 HTTP adapter 变成 CLI 子进程。

### 3.3 Prompt 资产

| 现状 | 预期 |
|---|---|
| `data/prompts/prompt-{a,b,c}-*-v1.md` 是极短占位（各两句） | 扩成真正可替换默认身份的 system instruction：保真/禁止项、输入通道约定、输出合同 |
| 身份 `promptA.default.v1` 等已在 S14 bootstrap | 保留 identity + `content_sha256`；CLI `--system-prompt-file` 必须指向同一 git 路径，hash 不一致 fail-closed |
| D05 约定路径 `data/prompts/intake/clean/**` 与 `data/prompts/lsrag/{structure,construct}/**` | 现文件在 `data/prompts/` 根下；搬家或保留均可，但 identity→path→hash 只能有一份 |
| LLM clean strategy 绑 `promptA.default` / `v1`（`src/contracts/intake/strategies.py`） | 继续按 strategy 决定**要不要**叫 Claude；deterministic / registered_api parser **不**叫 |

### 3.4 Workflow 与 admission 图

`src/workflows/lsrag_definition.py` 的步骤顺序不必改：

`acquire → decode → clean → seal → preflight → accept → [human] → structurize → construct → vectorize → publication`

改的是 **clean / structurize / construct 叶 handler 内部** 的模型运输，不是图拓扑。

lifecycle 捷径（rebuild / deactivate / reactivate / delete / metadata 无变化）仍在 acquire 后提前终结，不进 A/B/C。

`metadata_refresh` + `reuse_summaries=true` 仍可显式空 C；不因此重跑 A/B。

### 3.5 证据与失败

每次 `claude -p` 至少冻结：

- 所用 prompt identity + content_hash
- 完整 argv 摘要（不含 secret）
- exit code、stdout digest、`--output-format json` 整包（或 `structured_output` digest）
- `session_id`、`usage`、`modelUsage`、`total_cost_usd`、`duration_ms`
- schema digest（B 必须）

失败归类继续只引用 D01/S03（`T-O-207`）：

- CLI 不存在 / 非 0 / 空 stdout / `is_error: true` → Process failed 或 retryable，视是否瞬时
- prompt 文件与冻结 hash 不一致 → 配置/依赖失败，非业务 `blocked`
- B 的 `structured_output` 过不了 MKB StructureSchema / kernel → 叶失败，不得把半棵树写成 current
- 链接轮未授权取链工具 → 输入错误，fail-closed

不要为 Claude CLI 新建第四套 retry 账本。

### 3.6 测试合同预期

在现有 `tests/e2e/test_generation_pipeline_contracts.py`、`tests/unit/test_prompt_hash_mismatch.py` 之外，eval 阶段至少加：

1. **假 CLI**：注入可断言 argv 的 stub（system-prompt-file 路径、`-p` 物料、`--json-schema` 在场），不打外网。
2. **hash mismatch**：改 prompt 文件字节但不改 pointer → 不得 spawn。
3. **B schema 拒绝**：stub 返回缺 g=0 或改写 original 的 JSON → structurize 失败，不写 current。
4. **真机烟测**（本文件 §2 一类）：可人工，不进默认 P0-CI；CI 默认无 MiniMax/Anthropic 网络。

确定性 compiler 与 D08 四域 unit 测试保持绿灯；换运输层不得让 `intake/` parser 退化。

### 3.7 明确不在第一刀

- 不把 acquire/decode 交给 Claude。
- 不把 registered_api 三 provider parser 换成模型。
- 不把 vectorize 做成 promptD。
- 不把 `--json-schema` 同时套在 A 和 C 上冒充“一个 schema 走完全链”。
- 不在交互 `claude` 会话里跑生产（必须 `-p`，建议 `--bare`）。

---

## 4. 与已冻 Truth 的冲突面（先记下来，不擅自 reopen）

| 已冻句 | 本模式的张力 | 处理 |
|---|---|---|
| D05：调用点是 `runtime.inference` + prompt 正文 | 调用点变成 `claude -p` 子进程 | 产品语义可保持；S05/S06/S07/S11 的“实现调用点”句要回填 |
| S11 不拥有 promptA/B/C 产品语义，但提供 generate 门面 | A/B/C 可能不再走该门面 | embed/rerank 仍走 S11；A/B/C 运输要写清归属（S11 扩 CLI port，或 S05/S06/S07 自管 spawn） |
| `--system-prompt` 丢掉默认安全/工具说明 | 与 S16 工具围栏叠加 | 生产必须 `--tools` 白名单；链接轮单独开最小工具集 |
| 现 prompt 正文过短，不足以当整段 system | 直接 `--system-prompt-file` 会得到弱工人 | 先改 prompt 正文，再接线 |

未 owner 签字前，本文 **不** 视为 D05/S11 已改。

---

## 5. 待业主确认

1. B 的 `--json-schema` 是新写一份 CLI 用 schema 文件，还是从 `lsrag.structure.default@v1` / `StructureDocument` 生成？
2. C 是否也要独立 schema（SummaryChannel only），还是先纯文本再由 S07 kernel 挂回 unit？
3. `-p` 传链接时，取链是 MKB acquire（推荐，证据完整），还是 Claude 自取（仅 eval）？
4. 生产模型绑定：继续 MiniMax-M3 兼容端，还是切官方 Anthropic？`--bare` 下的密钥从哪来？
5. S11 是否增加 `ClaudeCliPort`，还是三个 generation handler 直接 spawn？

---

## 6. 下一步（未执行）

1. 把 promptA/B/C 写成可独立替换默认身份的 system instruction，并保持 S14 hash。
2. 冻结 B 的 StructureSchema 文件（g=0/1/2 Original，summary 槽可空）。
3. 用 stub CLI 把 S06 structurize live 路径接到 `claude -p`，读 `structured_output`，再进现有 kernel。
4. 同样接 A（仅 llm strategy）和 C。
5. 真机再跑一条：短 HTML → A 正文 → B 分层 JSON → C 摘要，对照 D05 例核验。
