# Agent-in-the-loop repair

> **项目**：`myknowledgebase`（MKB）
>
> **文档性质**：`eval / new-start`（探索记录，**不是** frozen domain-truth）
>
> **文档状态**：`draft / owner-review`
>
> **日期**：`2026-08-14`
>
> **作者**：`Grok`（本会话实测 + 业主约定）
>
> **姊妹文档**：`docs/eval/new-start/non-interactive-agentic-pipeline.md`（A/B/C 三次 `claude -p` 主链）
>
> **权威输入**：
> - 业主口头约定（本会话）：清洗/结构化失败显式标记并抛错，不挡其他文件；人审不是恢复手段
> - 业主口头约定（本会话）：`claude -p`（MiniMax）主处理；验证失败后可用 `grok -p` / `agy -p` + 专用修复 system-instruction 试修 JSON
> - S06 已冻 repair 缝：`T-O-83/84/85`、`S06-E05`（kernel 不可 agent 修；extension repair → 新 artifact + 全量复验；`repair_budget`）
> - 本机 CLI：`claude` 2.1.229、`grok` 1.0.3、`agy`（本机 `--help`）
> - 真机调用实测仅覆盖 `claude -p`（`/tmp/claude-p-tests/test{1..5}.*`）
>
> **本文不改写**：S03 状态机、S04 接受事务、S05 四类 source kind、D08 四域 parser、S14 hash 指针。人审闸若要从生产默认路径拿掉，须另开 owner 变更，不在本文偷改。

---

## 0. 一句话 verdict

**有条件 GO。** 用 MiniMax 走 `claude -p` 做主链；B 的 schema/形状验证失败后，再开一轮**显式** `grok -p`（首选）或 `agy -p`，注入专用修复 system-instruction，产出新 artifact 并走**同一份** StructureSchema + kernel。这不是静默换模型，也不是 human-in-the-loop。fidelity/kernel 失败不修，直接 failed；兄弟姐妹继续。

---

## 1. 方案要解决什么

主链见姊妹文档：promptA/B/C 是 `--system-prompt`，`-p` 只放物料或链接，`--json-schema` 卡在 promptB 的分层分粒度 JSON。

随之而来的操作事实：

| 工人 | 本机二进制 | 本会话确认的模型/能力叙事 | 角色 |
|---|---|---|---|
| `claude -p` | `/root/.local/bin/claude` 2.1.229 | `ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic`，`MiniMax-M3` | **主处理**：便宜、够用，跑 A/B/C 第一枪 |
| `grok -p` | `/root/.local/bin/grok` 1.0.3 | 业主：Grok 4.6，能力更强 | **第一修理工**：专用修复 instruction |
| `agy -p` | `/root/.local/bin/agy` | 业主：Gemini 3.7 Flash，能力显著 | **可选第二修理工**；system 注入口未齐 |

baseline v1 曾准备两条失败出路：内容回退（generic block / 放宽 schema，**已禁**）和 human gate（S05 `ExecutionGate`，业主现判**不必要**）。本方案用 **agent-in-the-loop repair** 填那条缝：出错仍显式失败；形状债可以再请更强工人修一次；不等人，不挡别的文件。

命名澄清：

- **不是** HITL。没有 `waiting(human_review)`，没有人工改 JSON。
- **不是** silent fallback。第一枪失败已经落账；修理工是另一条 Process/attempt、另一份 prompt 身份、另一个 CLI。
- **就是** S06 已允许的 governed extension repair，运输层换成多 CLI。

---

## 2. 已经测试验证的内容

分两层写：真机调用（有 stdout / exit code），和本机能力探测（`--help` / `which`）。后者**不能**当成修理工已打通。

### 2.1 环境（2026-08-14）

| 项 | 值 |
|---|---|
| 平台 | linux-arm64 |
| `claude auth status` | `loggedIn: true` · `oauth_token` · `firstParty` |
| `claude` 实际推理 | MiniMax 兼容端 · 模型 **MiniMax-M3**（JSON 里 `modelUsage.MiniMax-M3`） |
| `claude doctor` | native 2.1.229 · Remote Control 不可用（自定义 `ANTHROPIC_BASE_URL`） |
| 脚本开关 | `--bare --max-turns 1 --tools "" --effort low`（schema 轮不要卡 `max-turns 1`） |
| 产物目录 | `/tmp/claude-p-tests/test{1..5}.{out,err}` |
| secret | 环境里有 `ANTHROPIC_AUTH_TOKEN`；本文不抄写 |

`--bare` 不读 OAuth/keychain。本次 `claude -p` 能通，是因为环境 token + MiniMax base URL。生产脚本必须显式提供，不能假设交互登录在 CI 里还在。

### 2.2 `claude -p` 真机五次（全部 exit 0，stderr 空）

**Test 1 · 基础 print**

```bash
claude -p "Reply with exactly this token and nothing else: PING_OK" \
  --bare --max-turns 1 --tools "" --effort low
```

stdout：`PING_OK`。非交互工人可用。

**Test 2 · `--system-prompt` 整段替换**

系统提示要求每条回复以 `MKB_SYS_OK` 开头。用户问 `2+2`。

stdout：`MKB_SYS_OK 4`。

默认 coding assistant 身份可以被换掉。A/B/C 以及后文的 **repair instruction** 都走这条通道。

**Test 3 · `--output-format json`**

用户要求只回 `JSON_OK`。单行信封：

| 字段 | 实测 |
|---|---|
| `type` / `subtype` | `result` / `success` |
| `is_error` | `false` |
| `result` | `JSON_OK` |
| `stop_reason` | `end_turn` |
| `num_turns` | `1` |
| `modelUsage` | `MiniMax-M3` |
| `total_cost_usd` | `0.001839…` |
| `duration_ms` | `5418` |

另有 `session_id`、`usage`、`uuid`。脚本取正文：`jq -r '.result'`。

**Test 4 · system-prompt + json 同时开**

`result` = `"MKB_SYS_OK 2 plus 2 equals 4."`。身份替换和 JSON 包装不互斥。

**Test 5 · 再加 `--json-schema`**

探测 schema：`{clean_text, token}`（**不是** 生产 StructureSchema）。

返回同时有：

- `result`：schema 的 JSON **字符串**
- `structured_output`：已解析对象

`num_turns: 2`，`stop_reason: tool_use`。schema 路径会走内部 structured-output 工具。生产 B / repair 应读 `.structured_output`，再交给 MKB kernel，不要把模型对象直接写成 current。

**从五次得到的、repair 也要用的操作结论**

1. `--system-prompt` 足以承载主身份和修复身份。
2. `--json-schema` 给出可直接消费的 `structured_output`，B 与 repair **必须共用同一份 schema**。
3. 当前主链模型是 MiniMax-M3，不是 Anthropic 官方模型。
4. schema 轮不要用 `--max-turns 1` 卡死。

### 2.3 `grok` / `agy`：已确认在场，未做真机 `-p`

```text
/root/.local/bin/grok   →  grok 1.0.3 (1a29d5bc12)
/root/.local/bin/agy    →  本机已安装（--help 可用）
```

| 能力 | `claude -p` | `grok -p` | `agy -p` |
|---|---|---|---|
| 非交互 `-p` / `--print` | 已实测 | `--help` 有 | `--help` 有 |
| 替换 system prompt | `--system-prompt` 已实测 | `--system-prompt-override`（compat 别名 `--system-prompt`） | **`--help` 无此项** |
| `--output-format json` | 已实测 | `--help` 有 | `--help` 有 |
| `--json-schema` | 已实测（出 `structured_output`） | `--help`：设置后约束 JSON，并 imply `--output-format json` | `--help` 有；stream-json 时只约束最终结果 |
| `--bare` / 禁工具 | `--bare --tools ""` 已实测 | 未核 | `--disable-slash-commands` 有；system 注入口未核 |
| 真机模型应答 | MiniMax-M3 五次成功 | **未跑** | **未跑** |
| 信封字段是否与 Claude 同构 | 见 Test 3/5 | **未知** | **未知** |

因此：修理工编排在**接口层**可以设计；`grok -p` 的 system 注入口与 Claude 对齐得最好。`agy` 若当第二修理工，必须先补 system 注入（`--agent`、文件，或确认隐藏旗标）。把修理说明拼进 `-p` 会打乱「system = 身份、`-p` = 物料」，只作权宜。

本会话**没有**用坏 JSON 真打 `grok -p` / `agy -p` 修复轮。§8 把这列为落地前必做烟测。

### 2.4 失败纪律（业主本会话确认，非新代码）

对照实现与设计后，业主拍板：

1. 清洗/结构化失败：**显式标记 + 抛错**。
2. 不静默回退（generic block、放宽 schema、silent skip、empty success）。
3. **人审不是恢复手段**。
4. **不挡其他文件**继续跑。

实现现状（避免把愿望写成已交付）：

- 已对齐：`MkbError` → `ProcessOutcome.failed` / 瞬时码才 `retryable_failure`；无 generic fallback；scatter child 是独立 Execution，collect-all 不 fail-fast 杀 sibling。
- 未对齐：图上仍有 `human_review_gate`；scatter 成员全是 `required`，任一 child 失败则 root 以 `scatter-required-child-failed` 整单失败。

本方案只依赖「sibling 继续」；root 是否部分成功仍是未决 loss policy，见姊妹文档与 §7。

---

## 3. 流程图

### 3.1 单文件主链 + 修复环

```text
                    S05 acquire / decode
                              │
                              ▼
                 ┌─────────────────────────┐
                 │ claude -p + promptA     │
                 │ -p = 正文或链接         │
                 └────────────┬────────────┘
                              │ clean 正文
                              ▼
                 ┌─────────────────────────┐
                 │ claude -p + promptB     │
                 │ --json-schema = 分层    │
                 │ 分粒度 StructureSchema  │
                 └────────────┬────────────┘
                              │ structured_output
                              ▼
                    MKB schema + kernel 复验
                              │
              ┌───────────────┼──────────────────┐
              │ 全过                         失败 │
              ▼                                  ▼
     promptC（claude -p）              分类错误（§4.2）
     dual-channel / gate                    │
              │                    ┌────────┴────────┐
              ▼                    │ shape/schema    │ fidelity/kernel
         vectorize …               │ （可修）         │ （不修）
                                   ▼                 ▼
                      ┌─────────────────────┐   本文件 Process failed
                      │ grok -p + promptB-  │   显式 error_code
                      │ repair              │   sibling 继续
                      │ -p = 坏 JSON        │
                      │    + 验证报告       │
                      │ 同一份 json-schema  │
                      └──────────┬──────────┘
                                 │ 新 artifact
                                 ▼
                           从零全量复验
                      ┌──────────┴──────────┐
                      │ 通过                │ 仍失败
                      ▼                     ▼
                   进 C           （可选）agy -p 再一枪
                                          或直接 failed
```

### 3.2 多文件隔离

```text
scatter / 多文件
    ├─ file-1  MiniMax B ──验证过──► C
    ├─ file-2  MiniMax B ──shape 失败──► grok repair ──过──► C
    ├─ file-3  MiniMax B ──kernel 失败──► failed（不修）
    └─ file-4  MiniMax B ──验证过──► C
         ▲
         └── file-2/3 的失败不取消、不暂停 1 和 4
```

file-2 进修理工时，1/4 照跑第一枪。修理工是**该文件自己的下一枪**，不是集合闸。

### 3.3 和现有 Workflow 步骤怎么叠

图拓扑保持：

```text
acquire → decode → clean → seal → preflight → accept
       → [human_review 仅遗留；本方案默认不走]
       → structurize → (可选 structure_repair) → construct
       → vectorize → publication
```

改的是叶内部运输，不是步骤顺序：

| 现 Process | 第一枪工人 | 失败后 |
|---|---|---|
| `clean.extract.*`（需模型时） | `claude -p` + promptA | 本方案 **v1 不修 A**（A 失败 = 本文件 failed）。确定性 / API parser 仍走 `intake/` |
| `lsrag.structurize` | `claude -p` + promptB + schema | shape 失败 → repair Process；kernel 失败 → failed |
| `lsrag.construct` | `claude -p` + promptC | 本方案 v1 不把 C 送修理工；C 失败按现 S07 门闩 |
| `lsrag.vectorize` 及之后 | 不变 | 不引入 promptD |

`structure_repair` 建议做成 **独立 Process key**（例如 `lsrag.structure_repair`），不要藏在 `lsrag.structurize` 里换模型重试。这样 invocation、prompt hash、CLI 二进制、repair_budget 都能单独审计。

---

## 4. 修复合同

### 4.1 三通道（与主链同一分账）

| 通道 | 主链 B | 修复轮 |
|---|---|---|
| system | promptB（结构化身份） | **promptB-repair**（只修形状，不改身份） |
| `-p` | clean 正文 | **坏 JSON + 验证报告**（code、缺字段、kernel 未过项）。不回放生 HTML |
| `--json-schema` | StructureSchema | **同一份** StructureSchema，禁止放宽 |

promptB-repair 必须写死：

- 只调整 JSON 形状与声明过的 extension 指针
- 不改写 Original 正文，不加事实
- 不删 g=0，不发明 filter 键
- 过不了就返回最小失败对象或空，由编排标 failed；禁止「修到能过」而丢掉保真

身份建议：`promptB.repair.v1`，S14 同样 git 正文 + `content_hash`。不要把修理段落 append 进 promptB。

### 4.2 可修 / 不可修

| 验证失败类 | 例 | 是否送修理工 |
|---|---|---|
| 形状 / schema | 非对象、缺 required、多字段、粒度不是 0/1/2、指针断裂、`structured_output` 缺失 | **是** |
| CLI / 运输 | `claude` 非 0、空 stdout、`is_error` | **否**（S03 retryable 或 failed；换模型不能当运输重试） |
| prompt hash | 正文与冻结指针不一致 | **否**（配置失败） |
| kernel / fidelity | original 对不上 clean anchors、覆盖不全、发明句子、缺 g=0 | **否**（直接 failed） |
| 预算 | `repair_budget` 已耗尽 | **否** |

判断必须在 MKB 侧做（schema validator + 现有 structure kernel），不能让修理工自己宣称「我已经修好」。

### 4.3 预算与账本

沿用 `S06-E05`：

- `repair_budget` 默认 **1**（只请 Grok）。业主要瀑布时上限 **2**（Grok → agy），禁止循环。
- 每次 repair = 新 immutable GenerationArtifact + Invocation。
- 修完 **从零** 跑同一份 schema + semantic + source proof；只有 full-valid 才能 CAS current。
- 账本至少记：CLI 二进制与版本、模型、prompt identity+hash、schema digest、validation digest、session_id、usage、exit code、predecessor artifact。
- 修失败：本文件 `ProcessOutcome.failed`，`error_code` 保留首次验证码和末次修复码；sibling 不受影响。

瞬时 `GENERATION_INFERENCE_FAILED` 仍只走 S03 `max_retries`（同 CLI、同 prompt、同 digest）。**换 CLI 不是 retry，是 repair。**

### 4.4 明确禁止

1. 在同一次 `lsrag.structurize` 里静默 `claude` 失败再 `grok`。
2. 修复轮用另一份更松的 schema。
3. 修复轮回头做第二次清洗或补摘要。
4. kernel 债送修理工。
5. 修失败进 human gate。
6. 修理工变成热路径后不回头治 promptB / MiniMax，只加长瀑布。

---

## 5. 与现有内部流程的整合

### 5.1 仍留在 MKB、不交给任何 `-p`

S01–S04 围栏与接受；S05 acquire/decode/ExternalKey/seal/preflight；D08 四域确定性变换；S06 kernel / projection / digest；S07 ConstructToVectorizeGate；S08–S10 向量与检索；S13 对象；S14 prompt/schema 指针。

`claude` / `grok` / `agy` 只是叶运输。stdout 不是 Snapshot，也不是 current structure。

### 5.2 建议动的代码缝

| 位置 | 现况 | 整合 |
|---|---|---|
| `src/runtime/intake/generation_construct.py` `_structurize` | live 时 `_live_structured_generate(promptB)`，kernel 仍编权威树 | 第一枪改 `claude -p`；验证分 shape vs kernel；shape 失败 materialize `structure_repair`，不 CAS |
| 新 handler `lsrag.structure_repair` | 无 | spawn `grok -p`（或预算内 `agy -p`）；读 structured_output；**从零** kernel；成功才 CAS |
| `src/runtime/intake/generation_live.py` | S11 facade | 增加 CLI port，或三 handler 自管 spawn；invocation 字段扩 CLI 二进制 |
| `src/services/registry.py` `DEFAULT_PROMPTS` | A/B/C 三条 | 增加 `promptB.repair.v1` |
| `src/workflows/lsrag_definition.py` | `structurize → construct` | 中间加 repair 分支；失败叶走 `_terminal_routes`；默认不进 `human_review` |
| `src/contracts/intake/strategies.py` | LLM strategy 绑 `promptA.default` | A 仍只 MiniMax；repair 不绑到 clean strategy |

确定性 compiler 继续当权威形状。模型 JSON 永远是候选。

### 5.3 scatter / 多文件

现实现：child 独立跑完，再 fan-in；required child 失败则 root `scatter-required-child-failed`。

本方案最低要求：**repair 在 child 内做完再参与 fan-in**。sibling 看不到邻居的修理工。

若业主要「一批里坏一份、root 仍成功」，须另改 requiredness / loss policy。那是 Task 聚合问题，不是修理工问题。未改之前，修失败的 child 仍会让 root 失败——但失败发生在修理工也用尽之后，且其他 child 已经跑完。

### 5.4 测试合同（落地时）

1. **假 CLI**：断言第一枪 argv 是 `claude` + promptB；shape 失败第二枪是 `grok` + promptB-repair + 同一 schema；`-p` 含验证报告。
2. **kernel 失败不 spawn grok**。
3. **hash mismatch** 不得 spawn 任一 CLI。
4. **repair 仍缺 g=0** → failed，不 CAS。
5. **sibling**：一 child 进 repair 时另一 child 已成功 publication。
6. **真机烟测**（非默认 P0-CI）：人为破坏 MiniMax JSON → `grok -p` 修回 → kernel 过。`agy` 在 system 口确认前不进默认瀑布。

---

## 6. 风险

| 风险 | 为何重要 | 缓解 |
|---|---|---|
| 被做成 silent fallback | S14/S16 禁自动换模型 | 独立 Process、独立 prompt、账本强制 CLI 字段 |
| 修理工美化假树 | Grok 更强，更容易把发明写圆 | kernel 债不送修；复验对照 clean anchors |
| `agy` 无 system 旗标 | 身份会漏进 `-p` | v1 只认 Grok；agy 列为探测项 |
| 信封不同构 | grok/agy 的 json 未必有 `structured_output` | 每 CLI 一个薄 adapter；业务只认规范化后的对象 |
| 修理工变热路径 | 费用与延迟翻到 Grok | 计量 repair 率；超阈回头改 promptB，不加第三瀑布 |
| 人审图仍在 | 默认路径可能被 `require_human_review` 拐走 | 生产默认关；与本方案解耦 |

---

## 7. 待业主确认

1. `repair_budget` 默认 1（仅 Grok）还是 2（Grok → agy）？
2. root Task：sibling 跑完即可，还是允许部分成功？
3. `structure_repair` 独立 Process key，还是挂在 structurize 的显式第二 attempt（仍禁止静默换模型）？
4. A / C 失败 v1 是否一律不修？
5. 生产 Grok / Gemini 的密钥与 `--bare` 等价物放哪？

---

## 8. 下一步（未执行）

1. 写 `promptB.repair.v1` 正文（只修形状）。
2. 冻结与 B 共用的 StructureSchema 文件。
3. stub 测通 `structurize → structure_repair → kernel`。
4. 真机：坏 JSON → `grok -p --system-prompt-override … --json-schema …`，核信封字段。
5. 再决定 agy 是否进入预算，先补它的 system 注入口。

---

## 9. Verdict

| 面 | 判定 |
|---|---|
| 产品方向 | **接受**。用更强 CLI + 专用修复 instruction 替代人审和内容回退，与「显式失败、不挡其他文件」一致。 |
| 与已冻 S06 | **兼容**，若且唯若：独立 repair 轮、新 artifact、同一 schema、全量复验、`repair_budget`、kernel 不修。 |
| 与已冻「禁 silent fallback」 | **兼容**，若账本区分「第一枪 MiniMax」和「修理工 Grok/agy」，禁止同 Process 内暗换。 |
| 主链运输 | **已短验证**：`claude -p` + system-prompt + json + json-schema 五次绿灯（MiniMax-M3）。 |
| 修理工运输 | **未短验证**：仅确认 `grok`/`agy` 在场与旗标；无坏 JSON 真修。 |
| 实现状态 | **未接线**。workflow 仍含 human gate；scatter root 仍会因 required child 失败整单失败。 |
| 总评 | **有条件 GO / eval-ready**。可以按本文写 prompt、schema 和 stub 集成。未完成 §8.4 真机修理工烟测、未冻结 §7 之前，不得宣称生产已换到 agent-in-the-loop repair。 |

**一句话**：MiniMax 是生产工人，Grok（及以后的 agy）是挂号修理工；修理工只动形状，kernel 说了算，坏一份不挡别份。
