# NS1 — Non-interactive agentic production path · Progressive Owner-Gated Q&A

> **项目**：`myknowledgebase`（MKB）
>
> **范围**：`NS1`（new-start · 非交互 agentic 生产链：promptA/B/C 运输、B 交卷合同、失败产品面）
>
> **Q&A 位点**：`pre-charter / progressive deep-dive / eval truth formation`
>
> **提问**：`Grok` · **裁决**：`owner`
>
> **方法约束**：`.adocs/qna-progressive.md`；本 campaign **3×3×3**（三轮 × 每轮三题 × 每题三选项）；**无** second-opinion 槽位
>
> **上游架构真相**：`D01`、`D02-v1.0`、`D03`、`D05-v1.0 / T-O-202..210`、`D08-v0.1`、`S03`、`S04`、`S05-v1.1`、`S06-v1.1`、`S07-v1.1`、`S11`、`S14`；`spec-index` 下一空号 `T-O-337`
>
> **词汇权威**：`docs/baseline/spec-glossary.md`
>
> **工作笔记（非 Truth）**：`docs/eval/new-start/non-interactive-agentic-pipeline.md`、`agent-in-the-loop-repair.md`、`proposed-workflow-imagined.md`
>
> **问答结构**：Round 1–3 = `Q1–Q9` **全部冻结**（`T-O-337..351`）。**不生成 Round 4**。进入收口 / 执行方案。`T-O-352` 为后续业主修订（g=0 仅 summary 入向量）。
>
> **文档状态**：`locked / Q1–Q9 frozen / T-O-337..352 / ready for NS1 execution plan`
>
> **版本 / 日期**：`v0.4 / 2026-08-14`
>
> **下游消费者**：NS1 执行方案 / 后续 formal 回填（若 owner 要求 reopen 已冻 D/S 句）

> **★ 本 Campaign 证据授权**  
> NS1 仅授权消费：  
> 1. **已接受 baseline 真相**（`docs/baseline/**` 已冻 D/S 与 glossary/index）；  
> 2. **`context/legacy-family/`** 作为生产行为 ReferenceAnchor；  
> 3. **`context/legacy-prompt/`** 作为当时生产 Prompt 正文 ReferenceAnchor（非 runtime SSOT）；  
> 4. **本机 `claude -p` 实测**（`/tmp/claude-p-tests/test{1..5}.*`，2026-08-14）作为运输可行性证据。  
> **禁止**吸收 `context/legacy-specs/**`、`context/legacy-python/**`、`context/legacy-python-2/**` 为条款。  
> `docs/eval/new-start/` 三份分析是工作笔记，**不是** Truth；与本 QNA 冲突时以本文件 owner 答复为准。

> **Owner-originated application boundary（继承 `T-O-42`）**：MKB 与 `legacy-family` 完全独立。不建立 KV/SMCP/R2/Worker 兼容、dual-read 或 runtime dependency。吸收对象是 **schema 形状、prompt 身份语义、失败纪律**，不是栈。

> **Progressive 纪律**：
> 1. 先冻结可由本会话业主方向 + 上游已接受 Truth **唯一推导**的 foundational 真相（§1 pre-round），再提出 Round 1 三个 **仍不可推导** 的 foundational 问题；
> 2. 每题提供 **恰好三选项 A/B/C + 推荐 + 执行细节 + Reasoning + 证据**；业主回答前 **不**登记该题新 T-O；
> 3. Truth-ID append-only：自 `T-O-337` 起；不回收、不改写；
> 4. NS1 **不得** reopen S03 八态、S04 接受事务、D08 四域 parser、S08–S10 向量/检索、S14「DB 不存 prompt 正文」；物理不可实现则 fail-closed 或显式 change-request；
> 5. 本文件 **不含** second-opinion 栏；
> 6. **不**提前撰写尚未注入之轮的题目；Round 2 仅由中场评估 I 按已冻 `T-O` 注入。

> **Truth-ID 连续性**：全局下一空号为 `T-O-337`（`spec-index` S14/S16 回填声明）。NS1 pre-round 自 `T-O-337` 起。

---

## 0. 分轮状态总览

| 轮次 | 题号 | 层级 | 单一焦点 | second-opinion | 状态 |
|---|---|---|---|---|---|
| Pre-round freeze | — | foundational | NS1 围栏、三通道调用、A/B/C 身份、失败不人审、sibling 隔离、证据围栏 | waived | `frozen / T-O-337..342 · 随 Round 1 一并确认` |
| Evidence review | — | evidence | legacy-family clean/structurizer/constructor + `legacy-prompt` + 现 `lsrag_compiler` / `_structurize` + `claude -p` 实测 | waived | `completed / 2026-08-14` |
| Round 1 | `Q1–Q3` | foundational | B 交卷合同与权威；粒度闭集；root 聚合成败 | waived | `frozen / T-O-343..345 · owner 2026-08-14` |
| Mid-review I | — | truth formation | 评价 Round 1；注入 Round 2 | waived | `completed / 2026-08-14` |
| Round 2 | `Q4–Q6` | foundational | kernel 锚定证明；C 物料合同；catalog `prompt_id` 绑定 | waived | `frozen / T-O-346..348 · owner 2026-08-14` |
| Mid-review II | — | truth formation | 评价 Round 2；注入 Round 3 | waived | `completed / 2026-08-14` |
| Round 3 | `Q7–Q9` | foundational | catalog CRUD 变异；四角色 prompt_id；profile 挂载点 | waived | `frozen / T-O-349..351 · owner 2026-08-14` |
| Mid-review III | — | truth formation | 评价 Round 3；判定无需 Round 4 | waived | `completed / 2026-08-14` |
| Closure | — | delivery | §12 收口；下游执行方案 | — | `ready` |

---

## 1. ★ Truth-Gate 台账（append-only）

> Pre-round `T-O-337..342` 已随 Round 1 一并视为冻结（owner 接受 Q1–Q3 推荐，未否决围栏）。  
> Round 1–3 全部冻结：`T-O-337..351`。后续仅执行方案或显式 reopen。

| Truth-ID | 子类型 | 已锁定真相 | 来源 | 驱动后续题 | 下游约束 |
|---|---|---|---|---|---|
| `T-O-337` | `foundational / scope` | **NS1** 是 MKB 的 **非交互 agentic 生产链 campaign**：在不改写 S03/S04/D08/S08–S10 围栏的前提下，重钉 **promptA/B/C 的调用通道、B 交卷合同、clean/structure 失败产品面**。NS1 **不**拥有 Task/Execution/Process 状态机、Intake 接受事务、四域确定性 parser、embedding/index/serving。 | 本会话业主立项；D05 `T-O-208/210`；D08-T006 | Q1–Q3, Q6 | 禁止借 NS1 重开表闭集或第五类 source kind |
| `T-O-338` | `foundational / invocation channels` | 生产模型调用分三通道：**system** = 该轮 prompt 身份全文（`--system-prompt` / `--system-prompt-file`，**替换**默认 coding 身份，不用 append）；**user/`-p`** = 该轮物料（正文或链接，不含加工指令）；**`--json-schema`** 约束的是 **promptB 交卷** 的分层 JSON，不是 A 的纯文本，也不是 Claude 包装信封。 | 本会话业主口头；CLI reference；`claude -p` Test 2/5 | Q1, Q5 | A 无 schema；C 物料是否同形见 Q5 |
| `T-O-339` | `foundational / prompt trinity` | 生产 Prompt 身份闭集仍是 **promptA=Clean、promptB=Structurizer、promptC=Summarizer**（`prompt{A\|B\|C}.<variant>.<version>`）。正文只在 git；DB 仅 `content_hash`。B **不得**产权威 Summary；C **不得**改写 Original。缺 pointer / hash 不一致 = 配置失败，fail-closed。 | `T-O-208`；S14；S06-T029；本会话 | Q1–Q2, Q5 | 禁止无名 prompt 字符串、KV 第二正文、vectorize 冒充第四身份 |
| `T-O-340` | `foundational / no silent fallback` | **禁止**同一次 Process 内静默换模型/CLI/adapter 冒充成功。换工人必须是 **显式** 下一枪（独立 identity、独立 invocation 账）。运输失败走 S03 retry（同 binding、同 digest），**不是**换模型。 | `T-O-207/267`；S14-T009；S16-T049 | Q3 | 修理工机制若存在，不得藏进 `_structurize` |
| `T-O-341` | `foundational / failure product` | clean / structure **失败必须显式**（typed `error_code` + 本文件 Execution/Process failed）。**不以** `ExecutionGate` / `waiting(human_review)` 作为该失败的恢复手段。多文件时 **不因一份失败而取消或暂停 sibling**（collect-all，非 fail-fast）。 | 本会话业主口头；`runtime_scatter.py` collect-all 已实现 sibling 侧 | Q3 | 人审节点可留 historical；生产默认不得因结构失败而开门 |
| `T-O-342` | `foundational / evidence fence` | 本 campaign 唯一 legacy 证据：`legacy-family` 行为 + `legacy-prompt` 正文。现实现锚：`generation_construct.py` `_structurize` 丢弃模型 JSON、`lsrag_compiler.structurize` 以全文+断句编树。`claude -p` 五次绿灯只证明运输，不证明 schema/分层质量。 | Owner 授权；代码事实 2026-08-14 | Q1–Q2, Q4 | 零 legacy runtime；eval 笔记非 Truth |
| `T-O-343` | `foundational / B contract + current` | B 交卷唯一形状为 **`layered_content.v1`**（当时 Zod 同源：`context_meta` + `layered_content[]`）。模型 JSON 是候选。kernel **校验并投影** 后 CAS structure current。退役 `semantic_block`。digest/anchor 由 kernel 计算，模型不得填 span 当权威。g=0 `original_content.body` 若空，kernel **用 clean 全文确定性回填**。B 的 `llm_summary` 必须空/null。`LsragContractCompiler.structurize(clean_text)` **退出生产 current**（可留 fixture）。 | Round 1 / Q1 · owner 接受推荐 B · 2026-08-14 | Q4–Q5 | `--json-schema`、`adopt_layered_json`、promptB 迁入 |
| `T-O-344` | `foundational / granularity profile` | 每个 structurize **profile** 显式声明 `granularity_set`（进 `command_input_digest`）。首批：`generic={0,1,2}`、`legal={0,1}`、`realestate={0}`。未登记 variant 不得跑。少交/多交声明层 = **kernel 失败**；**禁止**按句或复制静默补层。此为对 `T-O-204` 的 **窄执行解释**（generic 仍三层；领域减层必须登记），不是废除 handbook。声明集合内的 g=0（含回填）必须进入向量候选（`T-O-205`；通道见 `T-O-352`：仅 summary）。 | Round 1 / Q2 · owner 接受推荐 B · 2026-08-14 | Q6, Q9 | profile 挂在 catalog 还是独立 id 见 Q9 |
| `T-O-345` | `foundational / aggregate fail-closed` | 维持 `T-O-341`。每个 child 独立跑完。失败 child 显式 failed，不开人审。全部 terminal 后，任一 **required** 失败/取消 → **root Task 失败**（现 `scatter-required-child-failed`）。**不** reopen `T-O-53`。单文件 Task：该 Execution 失败，不牵连其他 Task。生产默认 `auto_admitted`；`require_human_review` 不得因 B schema 失败置位。 | Round 1 / Q3 · owner 接受推荐 B · 2026-08-14 | — | scatter fan-in 本轮不改 |
| `T-O-346` | `foundational / kernel anchor` | g≥1 `original_content.body` 与 clean 均按 S05 配方规范化（UTF-8 / LF / NFC）后，body 必须是 clean 的 **精确子串**。命中按阅读序取 **第一次**；report 记 `occurrence_count`。找不到 = `STRUCTURE_ANCHOR_MISSING`（kernel 失败）。g=0 回填 span = 整份 clean。`layered_content.v1` **不收录** 模型 span 字段。禁止模糊/覆盖率/embedding 放宽。 | Round 2 / Q4 · owner 接受推荐 A · 2026-08-14 | — | `adopt_layered_json` 可编码 |
| `T-O-347` | `foundational / C material` | C 的 `-p` = kernel **已验收**（含 g=0 回填）的 layered JSON；只填 `llm_summary.*`；不得改 original / block_id / granularity。整包一次。`--json-schema` 可用同一份 `layered_content.v1`（此时 summary 必填）。**CAS current 仍是 S07** construction / dual-channel 投影，layered **不是** construction SSOT。 | Round 2 / Q5 · owner 接受推荐 A · 2026-08-14 | Q8 | 消费主体 = B.json 产物（`T-O-350`） |
| `T-O-348` | `foundational / prompt catalog id` | 接受 Q6-A 的「精确绑定、禁止猜测」，**修正入口形状**：API / Task **只接受 catalog `prompt_id`**，**禁止** caller 填写 `prompt_ref` / 路径 / identity 字符串。Prompt **本质**是 git 追踪的本地 `.md`。DB catalog **只**存 immutable `content_hash` + 相对路径指针（无 `body_text`）。运行时 `H(file)==content_hash` 失败则 fail-closed。Catalog 须有 **CRUD** 以登记/更新指针（变异语义见 Q7）。materialize 后冻结本次所用 hash，in-flight **不热切**。 | Round 2 / Q6 · owner 接受 A 并修正入口 · 2026-08-14 | Q7–Q9 | 窄解释 S14 PromptRef / RegistryPort |
| `T-O-349` | `foundational / catalog CRUD` | Catalog CRUD 只改 **指针目录**：Create/Read/List/Deactivate；Update = **新不可变版本**（新 `content_hash`+path，同 `prompt_id` 新 `version` 或新 id），旧行保留。CRUD **不写** md 正文。接口走内部 token，非公网 marketplace，非 agent 写。已 materialize 的 Execution **只认冻结 hash**。Delete = `retired`，不删 git、不删历史行。 | Round 3 / Q7 · owner 接受推荐 A · 2026-08-14 | — | 窄解释 S14 RegistryPort「非公网 CRUD」 |
| `T-O-350` | `foundational / four prompt roles` | Catalog **角色闭集四档**（不是第四个生产字母，是 B 拆成两跳）：`clean`=`promptA`；`markdown`=`promptB.md`；`json`=`promptB.json`；`summarizer`=`promptC`。文档 API：**必填** `json_prompt_id`（角色必须是 `json`，**不可跳过**）；`markdown_prompt_id` **可省=跳过 markdown 跳**；`clean_prompt_id` / `summarizer_prompt_id` **可省**，走该 role 的 catalog default。链路：`A → [B.md?] → B.json → C`。有 markdown 时 B.json 的 `-p` = markdown 正文；无则 = clean 正文。**C 只消费 B.json 经 kernel 验收后的 layered JSON**（`T-O-347`），不消费 markdown、不以 markdown 当结构 SSOT。B.md 只出 Markdown，**无** `--json-schema`。`--json-schema` / `T-O-343/346` 只约束 B.json。禁止单 id 猜角色。 | Round 3 / Q8 · owner 扩充推荐 A · 2026-08-14 | — | 工作流可多一跳 B.md；trinity 执行面变为四 role |
| `T-O-351` | `foundational / profile on json row` | `granularity_set`（及规范化配方 digest）是角色为 **`json`** 的 catalog 版本行的 **必填** 字段。解析 `json_prompt_id` 即得到闭集。API **不**收 `profile_id`。换闭集 = 新版本行（`T-O-349`）。`markdown` / `clean` / `summarizer` 行 **不**要求 `granularity_set`。 | Round 3 / Q9 · owner 接受推荐 A，并随 Q8 收窄到 json 行 · 2026-08-14 | — | kernel 只对 B.json 验收粒度 |
| `T-O-352` | `product / g0 summary-only vector` | **业主修订 `T-O-205`/`T-O-213`/`T-O-222`（2026-08-14）**：g=0 仍是 dual-channel construct 必在场（original 必须装回，供 Traceback/Inflation）。**向量候选只强制 g=0 summary**：g=0 original 不进入 required-set；g=0 summary 非空强制 required，禁止 empty-skip / live budget-skip 消灭。g≥1 两通道不变。此修订 **窄 reopen** S08 required-set 谓词，不废除 g=0 必入候选，也不废除 construct 双通道。 | 本会话业主口头 · 2026-08-14 | — | S08 compiler / vectorize / S09 expected-set |

---

## 2. 证据审查（ReferenceAnchor · 非 Truth）

### 2.1 证据地图

| 组件 | 路径 | 与 NS1 的关系 |
|---|---|---|
| Universal clean | `legacy-family/smind-skill-clean-universal/` | A：branch × `WEB_CONTENT_CLEANUP_V1` / `DOCUMENT_CONTENT_EXTRACTION_V1` |
| Dedicated APIs | `legacy-family/smind-skill-clean-dedicated-apis/` | **无 LLM prompt**；对照 D08 parser |
| Structurizer | `legacy-family/smind-skill-rag-structurizer/` | B：`designated_prompt` + Zod `layered_content` |
| Constructor / Summarizer | `legacy-family/smind-skill-rag-constructor/`（`services/summarizer.ts`） | C：整包填 `llm_summary`；当时无独立 summarizer skill |
| 当时正文 | `context/legacy-prompt/prompt{A,B,C}.*`（8 份） | 生产 instruction 实物 |
| 现图 | `src/workflows/lsrag_definition.py` | acquire→clean→accept→structurize→construct→vectorize |
| 现 B/C | `src/runtime/intake/generation_construct.py`、`lsrag_compiler.py` | **B 模型不进 current**；C 按 g2 句子摘要 |
| 现 stub | `data/prompts/prompt-{a,b,c}-*-v1.md` | 各两句，非生产正文 |
| CLI 实测 | `/tmp/claude-p-tests/` | `-p` / `--system-prompt` / `--output-format json` / `--json-schema` |

### 2.2 当时生产链（行为）

```text
clean-universal | dedicated-apis
    → 纯文本
rag-structurizer
    system = designated_prompt || RAG_STRUCTURIZER_V1_GENERAL
    user   = 整份 plainText
    out    = context_meta + layered_content[]（llm_summary 占位）
rag-constructor.summarizer
    system = designated_prompt || RAG:CONSTRUCTOR:GEMINI_SUMMARY:V2
    user   = 上游 JSON（多块时剥 g=0 body）
    out    = 同形 JSON，填 llm_summary
recorder → vectorizer
```

Structurizer Zod（`smind-skill-rag-structurizer/core/schemas_common.ts` `LayeredContentBlockSchema`）：每块 `block_id`、`granularity`、`original_content.{title,body}`、必填 `llm_summary.{title,body}`（可 null）；文档 `layered_content.min(1)`。

`legacy-prompt` 与该 Zod **并不只有一套方言**：`promptB.json.realestate.md` / `promptC.constructor.md` 对齐 `layered_content`；`promptB.json.structurizer.md` 是旧 `semantic_block` + B 内写 `semantic_understanding`；四份 `promptB.markdown.legal.*` 只出 Markdown，不是 JSON。

### 2.3 现实现链（代码事实）

```text
S05 acquire/decode/dispatch_clean → S04 accept
  → lsrag.structurize
       [optional live] structured_generate(promptB.default)  → 只记账
       LsragContractCompiler.structurize(clean_text)
         root + 单 paragraph 全文
         g0 = 全文；g1 = 同一全文；g2 = 正则断句
  → lsrag.construct
       live：对每个 projection block（含全部 g2）text_generate(promptC)
       或 deterministic_summaries
  → vectorize / publication
```

锚：`generation_construct.py` `_structurize`（live 调用后仍 `compiler.structurize`）；`lsrag_compiler.py` `_project_blocks`（`g0:document` / `g1:document` 同文，`g2:*` 句子）。

结论：**v1 冻了身份与围栏，没有冻当时的 prompt 正文，也没有把 `layered_content` 变成 current。** 现「分层」是断句。

### 2.4 运输实测（2026-08-14）

| 测 | 结果 |
|---|---|
| `claude -p` 纯文本 | `PING_OK` · exit 0 |
| `--system-prompt` 替换身份 | `MKB_SYS_OK 4` |
| `--output-format json` | `type=result`，正文在 `result` |
| system + json + `--json-schema` | `structured_output` 已解析对象；`num_turns=2`，`stop_reason=tool_use` |
| `grok` / `agy` | 二进制在场；**未**真机修 JSON。`agy --help` 无 `--system-prompt` |

### 2.5 已冻、本轮不得重开的合同

1. S04 是唯一 Snapshot/Item/Revision 写入点。  
2. D08：`intake/{api,web,pdf,doc}` 是变换 SSOT；API 三 provider 无 LLM。  
3. S06 kernel（坐标、original digest、coverage）不可 agent 修；repair 若存在必须新 artifact + 全量复验（`T-O-84`）。  
4. S07 整包 dual-channel 二元成败（`T-O-138`）；C 不改 original（`T-O-129`）。  
5. 默认双通道、g=0 必入向量**候选**（`T-O-203/205`）——**如何切出 g=1/2** 仍是本轮 Q2。  
6. 失败 retry 只引用 D01/S03（`T-O-207`）。

### 2.6 从授权证据抽出的开放轴（驱动 Round 1）

| 开放轴 | 为何不能 internally 默认 |
|---|---|
| **B 交卷形状与谁是 current** | 当时 Zod `layered_content`、旧 `semantic_block`、S06 `StructureDocument`、现 compiler 假树，四套并存。D05 要求 B 出 0/1/2 Original 骨架，但未钉 wire。选错则 `--json-schema` 与 kernel 整段返工。 |
| **粒度闭集** | D05 默认 {0,1,2}；法律正文只切 0/1；房产只切 0；现代码用句子冒充 2。领域能否少于三层，不可 internally 默认。 |
| **多文件失败后的 root 成败** | 业主已钉「显式失败、不人审、不挡 sibling」。`T-O-53` 仍写 required 异常阻塞整个 collection scope；现 scatter 全员 `required`，跑完后 root 仍 `scatter-required-child-failed`。「不挡继续」≠「父任务可以部分成功」。 |

---

## 3. Round 1 —— Foundational 三题（`Q1–Q3`）

> 本轮 second-opinion 模式：`waived`。  
> **Round 1 状态**：Owner **全部接受推荐 B**（Q1=B，Q2=B，Q3=B）· 2026-08-14 · 已冻结 `T-O-343..345`。

---

### Q1 — B 交卷的逻辑合同，以及谁成为 structure current

- **影响范围**：`--json-schema` 文件、S14 schema 登记、`lsrag_compiler` 生产职、`_structurize`、promptB 正文迁入、S07 对齐基准
- **为什么必须确认**：NS1 的第一刀是「让 B 的产出成为可验收 current」。形状不钉，P0 schema 无法冻；权威不钉，会继续「模型记账、compiler 编树」。
- **驱动输入**：`T-O-337..339`、`T-O-342`、§2.2–2.3、D05 `T-O-208/210`、S06-T029

#### 选项清单

| 选项 | 方案 | 含义 |
|---|---|---|
| **A** | **维持 compiler 为 current** | 生产权威仍是 `LsragContractCompiler.structurize(clean_text)`（全文树 + 断句投影）。模型/`claude -p` 可调用，只进 Invocation 账，**不**改 current。NS1 最多换运输，不换分层语义。 |
| **B** | **`layered_content` 交卷 + kernel 验收（推荐）** | B 的 `--json-schema` = 当时 Zod 同源的 `context_meta + layered_content[]`。模型 JSON 是**候选**。kernel **校验**（schema、至少一块 g=0、g≥1 原文可对上 clean）后 **投影** 为 generation-scoped structure/projection，再 CAS current。退役 `semantic_block` 方言。**禁止**模型填 span/digest；digest/anchor 由 kernel 算。g=0 的 `original_content.body` 若空，kernel **可用 clean 全文确定性回填**（原文隧道，非发明）。B 的 `llm_summary` 必须空/null，摘要只走 C。 |
| **C** | **模型直接出 S06 StructureDocument** | `--json-schema` = 节点树（`node_id` / parent / span / kind）。模型必须给出可验证 span。compiler 不再编树，只做 proof。 |

#### 当前建议 / 倾向

**推荐 B（`layered_content` 交卷 + kernel 验收）。**

#### 推荐执行细节（选 B 时）

1. 唯一 CLI/schema 文件：`layered_content.v1`（从 Structurizer Zod 抽出，去掉 catchall）。  
2. `_structurize`：`claude -p` + promptB + 该 schema → `adopt_layered_json(clean, json)` → 现有 artifact/pointer CAS。  
3. 旧 `structurize(clean_text)` **退出生产 current**，可留 fixture。  
4. `promptB.json.structurizer.md` 的 `semantic_understanding` **不得**进入 B 正文。  
5. 明确禁止：A 的「换运输不换权威」；C 的让模型编 span；flat wire 与 S06 tree 双 SSOT。

#### Supporting Reasoning

- **生产证明**：能跑的交卷形是 `layered_content`，不是节点树，也不是 `semantic_block`。  
- **代码证明**：A 就是现状，分层是假的（g0=g1）。  
- **反对 A**：与本会话「schema 是 B 完成后的分层 JSON」及 D05「B 做多粒度」冲突。  
- **反对 C**：span/UTF-8 边界是 kernel 职；当时 Worker 从未让模型出树。失败率会把 NS1 卡死。  
- **B**：模型管语义切块，kernel 管保真与坐标——对齐 `T-O-84` 与当时 Zod。g=0 回填收口当时「原文隧道」加了又删的摆动，并服务 `T-O-205`。

#### 问题（请业主裁决）

**Q1：B 交卷与 structure current 选 A / B / C？若选 B，是否确认：唯一 schema=`layered_content.v1`；退役 `semantic_block`；kernel 验收+投影+可选 g=0 回填；B 不得填权威 summary？**

- **业主回答**：接受推荐 **B** 全部执行细节（`layered_content.v1`；退役 `semantic_block`；kernel 验收+投影+g=0 回填；B 不得填权威 summary；compiler 编树退出生产 current）。→ **冻结为 `T-O-343`**
- **裁决状态**：`accepted / frozen`

---

### Q2 — 粒度闭集：D05 的 {0,1,2} 与当时领域切法如何共存

- **影响范围**：schema `granularity` 枚举、promptB 变体、kernel 是否合成缺层、S07/S08 期望的 unit 集合、法律/房产 profile
- **为什么必须确认**：`T-O-204` 写默认 {0,1,2}；当时法律 B 只有 0/1（且 g=0 原文常空），房产只有 0；现 compiler 用句子冒充 2。Q1 无论选哪条，不钉闭集就无法写「缺层算不算失败」。
- **驱动输入**：`T-O-204/205`、`T-O-339`、§2.2 `legacy-prompt`、`_project_blocks`

#### 选项清单

| 选项 | 方案 | 含义 |
|---|---|---|
| **A** | **全源强制 {0,1,2}，缺层 kernel 合成** | 任何 admitted clean 的 structure 必须同时具备 0/1/2。模型没切出的层由 kernel 补（全文复制和/或按句 g=2，即今日算法升级为「补层」）。领域 prompt 只影响切得「好不好」，不影响闭集。 |
| **B** | **Profile 声明闭集；缺层 fail-loud（推荐）** | 每个 structurize profile / promptB variant **显式**声明允许的粒度集合。generic 默认 {0,1,2}。法律可声明 {0,1}，房产可声明 {0}。模型少交声明层 = **kernel 失败**，不按句补。多交未声明层 = 失败。g=0 在声明集合内则必须在场（body 可按 Q1-B 回填）。 |
| **C** | **冻结当时生产闭集为 v1 全局** | 系统默认向当时实物看齐：能 0/1 即可；不要求 g=2。D05「默认三层」对 NS1 **暂不执行**；generic 也不强制 2。 |

#### 当前建议 / 倾向

**推荐 B（profile 声明闭集；缺层 fail-loud）。**

#### 推荐执行细节（选 B 时）

1. Structure profile 字段：`granularity_set` 闭集 + digest，进 `command_input_digest`。  
2. 首批：`generic → {0,1,2}`；`legal → {0,1}`；`realestate → {0}`。未登记 variant 不得跑。  
3. 禁止用句子/复制 **静默** 补未声明或已声明却缺失的层。  
4. `T-O-205`：声明集合内的 g=0，original 非空（含回填）必须进入向量候选。  
5. 选 B 视为对 `T-O-204` 的 **窄执行解释**（默认 generic 仍三层；领域须显式减层），不是废除 handbook。若 owner 认为必须正式 reopen D05，在答复中写明。

#### Supporting Reasoning

- **反对 A**：把今日假分层合法化；法律目录块会被句子打散，丢掉当时 structurizer 的产品价值。  
- **反对 C**：generic 长文失去段落层；与 handbook「默认三层」冲突面过大，且没有「谁允许减层」的登记点。  
- **B**：尊重当时领域切法，同时不让减层成为无登记的口头习惯；fail-loud 对齐禁 silent coerce。

#### 问题（请业主裁决）

**Q2：粒度闭集选 A / B / C？若选 B，是否确认：generic={0,1,2}、legal={0,1}、realestate={0}；缺层失败不合成；并接受这是对 `T-O-204` 的窄执行解释？**

- **业主回答**：接受推荐 **B** 全部执行细节（profile 声明闭集；generic={0,1,2}、legal={0,1}、realestate={0}；缺层失败不合成；窄执行解释 `T-O-204`）。→ **冻结为 `T-O-344`**
- **裁决状态**：`accepted / frozen`

---

### Q3 — sibling 已继续跑完之后，root / Task 算不算成功

- **影响范围**：scatter fan-in、`T-O-53/57`、Task `cnt_failed`、S02 聚合、是否 reopen 集合级连坐
- **为什么必须确认**：`T-O-341` 已钉显式失败、不人审、不挡 sibling。现实现跑完后，任一 `required` child 失败 → root `scatter-required-child-failed`。业主「不阻塞其他文件」有两种读法：只保证邻居跑完，或父任务也可以部分成功。这决定 fan-in 合同，不能 internally 默认。
- **驱动输入**：`T-O-341`、`T-O-53/57`、`runtime_scatter.py` `_maybe_converge_scatter_root_tx`、S05-T013

#### 选项清单

| 选项 | 方案 | 含义 |
|---|---|---|
| **A** | **恢复 v1 设计面：人审 + 整 scope 先阻塞** | 撤回 `T-O-341` 的「不人审恢复」。reviewable 结构/预检问题开 `ExecutionGate`；required 异常在 root 未放行前不推进 sibling RAG（`T-O-57`）。与本会话口头方向相反，作为正式否决项保留。 |
| **B** | **文件失败；sibling 跑完；root 仍失败（推荐）** | 维持 `T-O-341`。每个 child 独立跑完（含其 clean/B/C）。失败 child 显式 failed，不开门。全部 terminal 后，若存在 required 失败/取消，**root Task 失败**（现 `scatter-required-child-failed`）。**不** reopen `T-O-53`。单文件 Task 同理：该 Execution 失败，不牵连其他 Task。 |
| **C** | **文件失败；sibling 跑完；root 允许部分成功** | 维持 `T-O-341`。requiredness 可分 `required` / `optional`，或 fan-in 改为「有一份 publication 即可 succeeded + 计数失败」。成功 child 保持可服务。**须显式 reopen** `T-O-53`（及可能的 `T-O-57` 根闸语义）。 |

#### 当前建议 / 倾向

**推荐 B（隔离执行，聚合仍 fail-closed）。**

#### 推荐执行细节（选 B 时）

1. 不改 scatter 全员 `required`、不改 fan-in 失败码。  
2. 生产默认 `auto_admitted`；`require_human_review` 不得因 B schema 失败而置位。  
3. 单文件与 scatter child 同一失败面：typed Outcome，不 CAS 半成品 current。  
4. 明确禁止：A 把结构失败送回人审；C 在未 reopen 时把部分成功写成现状。  
5. 若业主日后要 C，另开 campaign，不塞进本轮执行细节。

#### Supporting Reasoning

- **业主已排除 A** 作为「现在的做法」；A 仅供正式改口。  
- **C 改变的是 Task 成功定义**，不是工人怎么叫。分析未给出部分成功的 serving/filter 合同，本轮采纳会把 NS1 拖进 S02/S09 重开。  
- **B** 精确实现「不挡其他文件继续」的已实现含义（collect-all），同时服从已冻集合 fail-closed，P1 可执行。

#### 问题（请业主裁决）

**Q3：失败聚合选 A / B / C？若选 B，是否确认：不人审恢复；sibling 必须跑完；任一 required child 失败则 root 失败；本轮不 reopen `T-O-53`？**

- **业主回答**：接受推荐 **B** 全部执行细节（不人审恢复；sibling 必须跑完；任一 required child 失败则 root 失败；本轮不 reopen `T-O-53`）。→ **冻结为 `T-O-345`**
- **裁决状态**：`accepted / frozen`

---

## 4. Round 1 题目与 Truth 映射（已冻结）

| 题 | 焦点 | Owner 选择 | Truth-ID | 状态 |
|---|---|---|---|---|
| Q1 | B 交卷合同 + structure current 权威 | **B** | `T-O-343` | `frozen` |
| Q2 | 粒度闭集与领域 profile | **B** | `T-O-344` | `frozen` |
| Q3 | sibling 跑完后的 root 成败 | **B** | `T-O-345` | `frozen` |

---

## 5. ★ 中场评估 I（Round 1 → Round 2）

> 轮间承重段：评价 Round 1 + 固化 `T-O` + 反方制衡 + 说明为何注入 Q4–Q6。

### 5.1 对 Round 1 的判定

三题均接受推荐 **B**，答复完整，无附带条件、无「部分接受」。

| 题 | 决断 | 关键性 |
|---|---|---|
| Q1 | `layered_content.v1` 成为 B 交卷；kernel 验收后才是 current | **本 campaign 主轴**。废止「模型记账、compiler 编树」。 |
| Q2 | 粒度由登记 profile 声明；缺层失败 | 使 Q1 的 schema 可写死 `granularity` 校验，而不与 `T-O-204` 硬撞。 |
| Q3 | 隔离跑完 + 聚合 fail-closed | 把「不挡其他文件」收窄为 collect-all，不把 NS1 拖进 S02 部分成功。 |

最关键的一手是 **Q1-B**：后面所有 CLI schema、`adopt_layered_json`、promptB 迁入都挂在这条上。Q2/Q3 是边界，不是第二套产品。

无 Round 1 残题。业主未单列否决 `T-O-337..342`；与 Q1–Q3 一致，pre-round 一并视为冻结。

### 5.2 本轮已锁定真相

§1 新增：`T-O-343`（B 合同 + current）、`T-O-344`（粒度 profile）、`T-O-345`（聚合 fail-closed）。  
已确认围栏：`T-O-337..342`。

### 5.3 诚实反方制衡

1. **`T-O-343` 与 S07 `T-O-132/135` 的张力**：S07 禁止把 flat `layered_content` 当 **construction SSOT**。Q1 把它定为 **B 的模型交卷形**。二者可以并存（layered = B I/O，current = kernel 投影后的 generation 产物），但 **C 吃哪一份** 尚未钉死。若 C 再把 layered 当 SSOT，会走回 Constructor/Structurizer 双维护。  
2. **g=0 回填** 已随 Q1-B 接受：kernel 写入的全文必须可与 clean digest 对账；不得被模型事后改写成「更干净的 g=0」。  
3. **`T-O-344` 窄解释 `T-O-204`** 尚未回填 D05 正文。执行可按 profile 走；handbook 句仍写「默认 {0,1,2}」。正式 reopen 不在本轮。  
4. **`T-O-345` 不改善「一批里坏一份、整批红」的运营体感**。这是刻意延期，不是已解决。  
5. **kernel 如何证明「原文在 clean 里」**（子串？span？模糊？）Q1 只说 kernel 算 anchor，算法未冻——不冻则 `adopt_layered_json` 无法编码。  
6. **`T-O-344` 的 profile 谁选**：generic/legal/realestate 已有闭集，没有绑定面。靠 media 猜测会违反 S05 三轴；靠 `designated_prompt` 字符串会违反 `T-O-339`。

### 5.4 为什么提出 Round 2

Round 2 = `Q4–Q6`，只补 Q1–Q3 钉死后仍不可推导的三点：

| 题 | 未定点 | 由哪条 `T-O` 驱动 |
|---|---|---|
| **Q4** | kernel 用什么规则把 `original_content.body` 锚定到 clean | `T-O-343`（验收+投影，算法空） |
| **Q5** | C 的 `-p` 物料是 layered JSON，还是只消费 kernel 投影 | `T-O-343` + `T-O-338/339` + S07 `T-O-132/138` |
| **Q6** | structurize profile / promptB variant 如何绑到本次 Execution | `T-O-344` + `T-O-337/339` |

不在本轮问：修理工 CLI、A 是否走 `claude -p`、法律 markdown 中间 Process、case 分析通道。那些要等 Q4–Q6 冻后再看是否仍不可推导。

---

## 6. Round 2 —— Kernel 证明 · C 物料 · Profile 绑定（`Q4–Q6`）

> 本轮 second-opinion 模式：`waived`。  
> **Round 2 状态**：Owner 接受 Q4=A、Q5=A；Q6=A **并修正入口为 catalog `prompt_id`** · 2026-08-14 · 已冻结 `T-O-346..348`。

---

### Q4 — Kernel 如何证明 g≥1 的 original 锚定在 clean 上（**驱动真相：`T-O-343`**）

- **影响范围**：`adopt_layered_json`、structure validation report、`STRUCTURE_*` 错误轴、法律引文/重复短句失败率
- **为什么必须确认**：`T-O-343` 要求 kernel 算 digest/anchor，模型 span 非权威。未规定「在 clean 里找到这段 body」的算法前，验收无法编码，Q1 不能落地。
- **驱动输入**：`T-O-343`、`T-O-342`、S05-T011（UTF-8/LF/NFC）、S06 kernel 不可 agent 修

#### 选项清单

| 选项 | 方案 | 含义 |
|---|---|---|
| **A** | **规范化后精确子串（推荐）** | 对 clean 与 `original_content.body` 做与 S05 一致的规范化（UTF-8、LF、NFC）。g≥1 的 body 必须是规范化 clean 的 **精确子串**。命中按阅读序取 **第一次**；写入 kernel span。找不到 = `STRUCTURE_ANCHOR_MISSING`（kernel 失败，不送人审）。空白/仅标点 = 失败。g=0 回填全文的 span 为整份 clean，不走搜索。 |
| **B** | **模型可选 span，kernel 复核** | B 可附带非权威 `start_byte/end_byte`。有则解码必须 **恰好等于** 所报 body 且落在 clean 内，否则失败。无则回退 A。模型不能只交 span 不交 body。 |
| **C** | **覆盖率 / 模糊匹配** | 允许去空白后匹配、最小覆盖比、或 token 重叠达标即过。报告记 `approximate`。 |

#### 当前建议 / 倾向

**推荐 A（规范化精确子串 + 首次命中）。**

#### 推荐执行细节（选 A 时）

1. 规范化配方进 structure profile digest，与 `T-O-344` 一并冻结。  
2. 重复出现同一 body：取首次命中，report 记 `occurrence_count`；**不**因此失败（法规套话常见）。  
3. 禁止用 embedding/编辑距离放宽。找不到就是 kernel 债，按 `T-O-341` 显式失败。  
4. Q1 已禁模型 span 当权威；选 A 则 schema **不收录** span 字段，避免双通道真相。

#### Supporting Reasoning

- **反对 B（作 v1 默认）**：多一套可错字段；与「模型不得填 span 当权威」摩擦；P1 变厚。  
- **反对 C**：静默 coerce，且无法复验 digest。  
- **A**：可测、与 S05 规范化同轴；首次命中避免「第一条」重复导致全盘失败。

#### 问题（请业主裁决）

**Q4：锚定证明选 A / B / C？若选 A，是否确认：NFC/LF 精确子串；首次命中；找不到即 kernel 失败；schema 不收模型 span？**

- **业主回答**：接受推荐 **A** 全部执行细节（NFC/LF 精确子串；首次命中；找不到即 kernel 失败；schema 不收模型 span）。→ **冻结为 `T-O-346`**
- **裁决状态**：`accepted / frozen`

---

### Q5 — C 的 `-p` 物料是什么（**驱动真相：`T-O-343` · `T-O-338` · `T-O-339`**）

- **影响范围**：promptC 正文、construct handler、S07 `T-O-132/138` 对齐、是否再维护一份 flat JSON
- **为什么必须确认**：`T-O-343` 把 layered 定为 **B 交卷**，不是自动定为 construction SSOT。S07 已禁止 flat layered 当构造真相，并要求整包 dual-channel（`T-O-138`）。C 若再以 layered 为权威，会与 S07 冲突；若只吃投影，则当时 `promptC.constructor.md` 不能原样当 system instruction。
- **驱动输入**：`T-O-343/338/339`、S07 `T-O-132/135/138`、`summarizer.ts` 整包回填

#### 选项清单

| 选项 | 方案 | 含义 |
|---|---|---|
| **A** | **C 吃已验收 layered，摘要后 kernel 映射（推荐）** | C 的 `-p` = kernel **已验收**（含 g=0 回填）的 layered JSON；system = promptC；只填 `llm_summary.*`，original 原样。`--json-schema` 可用 **同一份** `layered_content.v1`（摘要槽此时必填非空）。CAS current 仍是 S07 的 construction/dual-channel 投影，**不是** 又一份 flat 文件当 SSOT。`block_id` 对齐 B 验收后的稳定序。 |
| **B** | **C 只吃 kernel 投影单元** | layered 只活在 B 调用边界内。C 的 `-p` 是 generation-scoped units（coordinate + original title/body）。promptC 按 S07 合同重写，不再假设 `layered_content` 字段名。 |
| **C** | **保持按 block 多次 `text_generate`** | 对每个投影 unit 单独打 C（今日 `_live_summaries`，只是 unit 不再是句子）。与 `T-O-138` 整包一次冲突。 |

#### 当前建议 / 倾向

**推荐 A（C 吃已验收 layered；SSOT 仍是 S07 投影）。**

#### 推荐执行细节（选 A 时）

1. B 成功且 kernel 验收后，把 **回填后的** layered 字节作为 C 的物料（digest 进 construct command）。  
2. C 不得增删 block、不得改 original、不得改 `granularity`/`block_id`；违者 `CONSTRUCT_KERNEL_*`。  
3. 整包一次调用（或显式整包 plan），对齐 `T-O-138`。  
4. `content_full` / filter 仍按 S07：权威在 S04，不在 `context_meta` 模型字段。  
5. 禁止：把 C 的 stdout 直接当 serving；禁止 B 选项把 S07 合同整份推倒重写（可后续 reopen，不是 NS1 默认）。

#### Supporting Reasoning

- **反对 B 作默认**：当时 promptC 与 Zod 同形；NS1 要迁正文，不宜第一刀改 C 的 wire。  
- **反对 C**：已冻整包成败；且会回到「一层一枪」。  
- **A**：保留当时 Constructor 形状作 **运输**，S07 投影作 **真相**，消化 5.3 的张力而不 reopen S07。

#### 问题（请业主裁决）

**Q5：C 物料选 A / B / C？若选 A，是否确认：C 吃验收后 layered；只填 summary；current 仍是 S07 双通道投影；整包一次？**

- **业主回答**：接受推荐 **A** 全部执行细节（C 吃验收后 layered；只填 summary；current 仍是 S07 投影；整包一次）。→ **冻结为 `T-O-347`**
- **裁决状态**：`accepted / frozen`

---

### Q6 — structurize profile / promptB variant 如何绑定（**驱动真相：`T-O-344`**）

- **影响范围**：ProcessCommand、S14 登记、`BUILTIN_SOURCE_PROFILE_WORKFLOWS`、未知变体 fail-closed
- **为什么必须确认**：`T-O-344` 已有 `generic` / `legal` / `realestate` 闭集，未说本次 Execution 怎么选中其中一个。选错会变成 S05 禁止的「靠 media 猜」或 legacy 的 `designated_prompt` 任意串。
- **驱动输入**：`T-O-344`、`T-O-337/339`、S05-T002、S03 materialize 后不热切

#### 选项清单

| 选项 | 方案 | 含义 |
|---|---|---|
| **A** | **Command 精确绑定（推荐）** | `lsrag.structurize` 的 ProcessCommand **必填** `prompt_ref`（`promptB.<variant>.<version>` + hash）与 `structure_profile_ref`（含 `granularity_set` + digest）。Workflow revision / 已有 source-profile 图在 **materialize 时**写入这两项，之后不热切。未知 variant、profile 与 prompt 不一致、hash 漂移 = 配置失败。**禁止**从 `source_kind` / MIME / URL 推断 legal vs generic。 |
| **B** | **从 source / media 推断** | `registered_api`+房产 provider → realestate；`http_resource`+中文法规启发式 → legal；其余 generic。省去显式字段。 |
| **C** | **Caller 自由字符串** | 恢复 `designated_prompt` 式 payload 字符串；不在 registry 的 key 也可跑（或仅 warning）。 |

#### 当前建议 / 倾向

**推荐 A（Command 精确绑定，图上选，运行时不猜）。**

#### 推荐执行细节（选 A 时）

1. 首批 S14 身份：`promptB.default`（generic）、`promptB.legal`、`promptB.realestate`，各锁 `structure_profile_ref`。  
2. 现有 HTTP/PDF/OCR workflow 默认绑 `promptB.default`，直到另开法律/房产图。  
3. 绑定进入 `command_input_digest` 与 `s05_binding` 同纪律：retry 同 digest。  
4. 禁止 B/C：猜领域、任意 KV 串。

#### Supporting Reasoning

- **反对 B**：领域不是 source kind；启发式不可复验，违反 S05 三轴。  
- **反对 C**：正是 `T-O-339` 要删的无名 prompt。  
- **A**：Q2 的闭集才有落点；与 S03「一次 materialize」一致。

#### 问题（请业主裁决）

**Q6：profile/variant 绑定选 A / B / C？若选 A，是否确认：Command 必填 prompt_ref+profile_ref；图上选定；禁止按 media/URL 猜；未知即配置失败？**

- **业主回答**：接受推荐 **A** 的「精确绑定、禁止按 media/URL 猜、未知 fail-closed」，**修正入口**：
  1. Prompt 是 git 追踪的本地 `.md`；DB catalog 只登记 **immutable hash + 相对路径指针**，不存正文。
  2. Catalog 必须可 **CRUD**（登记/更新指针）；运行时 `H(file)==hash` 通过才放行。
  3. 处理文档的 API **只收 `prompt_id`**，经 catalog 指针加载路径；**禁止** caller 填 `prompt_ref` / 路径 / identity 字符串。
  → **冻结为 `T-O-348`**
- **裁决状态**：`accepted / frozen / amended`

---

## 7. Round 2 题目与 Truth 映射（已冻结）

| 题 | 焦点 | 驱动真相 | Owner 选择 | Truth-ID | 状态 |
|---|---|---|---|---|---|
| Q4 | kernel 锚定算法 | `T-O-343` | **A** | `T-O-346` | `frozen` |
| Q5 | C 物料 vs S07 SSOT | `T-O-343/338/339` | **A** | `T-O-347` | `frozen` |
| Q6 | 绑定入口 | `T-O-344` | **A + `prompt_id` 修正** | `T-O-348` | `frozen` |

---

## 8. ★ 中场评估 II（Round 2 → Round 3）

### 8.1 对 Round 2 的判定

| 题 | 决断 | 关键性 |
|---|---|---|
| Q4 | 精确子串 + 首次命中 | `adopt_layered_json` 可编码；P1 不再模糊 |
| Q5 | C 吃验收后 layered；SSOT 仍是 S07 | 消解 layered 运输 vs S07 真相，不 reopen S07 |
| Q6 | 精确绑定成立，**入口从 `prompt_ref` 改为 catalog `prompt_id`** | **本轮最关键修正**。不是推翻 A，是否定「caller 自带 identity+hash 字符串」 |

Q4/Q5 无附带条件。Q6 的修正与 `T-O-264`（正文 git、DB 仅 hash、运行时校验）同向，但与 S14 **RegistryPort = 非公网 CRUD**、**legacy console prompt CRUD 为反例**（`T-O-274`）以及「S05–S07 只持 PromptRef」有张力。必须在 Round 3 钉死：**CRUD 改的是什么、谁能写、update 是否原地改指针**。

### 8.2 本轮已锁定真相

§1 新增：`T-O-346`（锚定）、`T-O-347`（C 物料）、`T-O-348`（`prompt_id` catalog + hash 门闩）。

### 8.3 诚实反方制衡

1. **`prompt_id` 不是更短的 `prompt_ref`。** `PromptRef` 把 identity+hash 交给 caller，hash 可被写错或写旧。`prompt_id` 把解析权收回 catalog，hash 以登记行为准，再与磁盘对账。这比 Q6 原稿更 fail-closed。  
2. **CRUD 若变成「改同一行的 path/hash」**，in-flight Execution 会在重试时读到新指针，违反 `T-O-269` / materialize 不热切。CRUD 必须有 **版本/世代** 语义，不能是 KV 式覆盖。  
3. **S14 明文「非公网 CRUD」「禁 agent 写 registry」**。业主要的 CRUD 若做成 console 式改正文/deploy，就是 `T-O-274` 点名删除的债。NS1 只能把 CRUD 解释成 **指针目录**（谁登记哪份 git 文件），正文仍只经 git 变更。  
4. **`T-O-344` 的 `structure_profile_ref` 还没着落。** 入口只说了 `prompt_id`。profile 是 catalog 行上的字段，还是第二个 id，未推导。  
5. **API「提供 prompt_id」是单数。** A/B/C 三个身份是否共用一个 id、还是至少要 B、A/C 走默认，未推导。  
6. 修理工 / A 是否走 `claude -p` 仍未问；本轮先收 catalog，避免第三轮再开运输轴。

### 8.4 为什么提出 Round 3

Round 3 = `Q7–Q9`，只补 `T-O-348` 钉死后仍不可推导的三点。答完即 3×3×3 题号齐，可做收口评估（不再预设第四轮）。

| 题 | 未定点 | 由哪条 `T-O` 驱动 |
|---|---|---|
| **Q7** | catalog CRUD 的变异：新版本还是原地改；谁可写 | `T-O-348` vs S14 `T-O-269/270/274` |
| **Q8** | 文档 API 要几个 `prompt_id`、对应 A/B/C 哪几枪 | `T-O-348` + `T-O-339/347` |
| **Q9** | `granularity_set` 挂在 catalog 行上，还是单独 id | `T-O-344` + `T-O-348` |

---

## 9. Round 3 —— Catalog 变异 · API 入口集合 · Profile 挂载（`Q7–Q9`）

> 本轮 second-opinion 模式：`waived`。  
> **Round 3 状态**：Owner 接受 Q7=A、Q9=A；Q8=A **并扩充为四角色** · 2026-08-14 · 已冻结 `T-O-349..351`。

---

### Q7 — Prompt catalog CRUD 改的是什么（**驱动真相：`T-O-348`**）

- **影响范围**：S14 RegistryPort、D04 `mkb_prompt_hash_pointers`、内部 API、in-flight hash 冻结、G-12
- **为什么必须确认**：`T-O-348` 要求 CRUD，但未说 Update 是新不可变版本还是改同一 `prompt_id` 的指针。后者会热切 in-flight，并撞上 S14「非公网 CRUD / 禁 agent 写 / console CRUD 为反例」。
- **驱动输入**：`T-O-348`、`T-O-264/269/270/274`、S14 §1.4 RegistryPort

#### 选项清单

| 选项 | 方案 | 含义 |
|---|---|---|
| **A** | **指针目录 CRUD + 不可变版本（推荐）** | Create/Read/List/Deactivate 针对 catalog 行。Update = **登记新版本**（新 `content_hash`+path，或新 `prompt_id` / 同 id 新 `version`），旧版本行保留。已 materialize 的 Execution **只认当时冻结的 hash**。CRUD **不写正文**；正文只经 git 落地后再登记。接口走 **内部 token**（与现 Task API 同围栏），**不是**公网 marketplace，**不是** agent 写 registry。 |
| **B** | **原地改同一 `prompt_id` 的 path/hash** | Update 覆盖指针。之后新 Task 用新文件；已跑到一半的若再读盘且 hash 变了 → fail-closed。实现简单，破坏 `T-O-269`。 |
| **C** | **无 CRUD，仅 bootstrap / 改 git 后手工灌库** | 维持 S14 字面「非 CRUD」。与 `T-O-348` 业主要求相反。 |

#### 当前建议 / 倾向

**推荐 A（不可变版本的指针目录；内部 API；不写正文）。**

#### 推荐执行细节（选 A 时）

1. 一行最小字段：`prompt_id`、`role`（A/B/C）、`git_relative_path`、`content_sha256`、`version`、`status`、`granularity` 相关字段归属见 Q9。  
2. Update 成功 ⇒ 新版本行；旧 `prompt_id@version` 仍可被冻结 Execution 解析。  
3. Delete = `status=retired`，不删 git 文件、不删历史行。  
4. 运行路径只 `get(prompt_id)` → 读盘 → `H(file)==hash`。  
5. 明确禁止：B 的原地覆盖；C 的「没有登记面」；DB 存 `body_text`；agent/LLM 调 CRUD。

#### Supporting Reasoning

- **反对 B**：同 id 覆盖 = 热切 active，重试会换 prompt。  
- **反对 C**：否决业主已说的 CRUD。  
- **A**：同时满足「要 CRUD」「正文只在 git」「hash 门闩」「不热切」，并把 S14 CRUD 禁令收窄为 **禁公网/禁写正文/禁 agent**，允许内部指针目录。

#### 问题（请业主裁决）

**Q7：catalog CRUD 选 A / B / C？若选 A，是否确认：Update=新不可变版本；CRUD 不写 md 正文；内部 token；in-flight 只认冻结 hash？**

- **业主回答**：接受推荐 **A** 全部执行细节（Update=新不可变版本；CRUD 不写 md；内部 token；in-flight 只认冻结 hash）。→ **冻结为 `T-O-349`**
- **裁决状态**：`accepted / frozen`

---

### Q8 — 处理文档的 API 要带哪些 `prompt_id`（**驱动真相：`T-O-348` · `T-O-339` · `T-O-347`**）

- **影响范围**：S02 Task payload、clean/structurize/construct materialize、默认指针
- **为什么必须确认**：`T-O-348` 写「提供 `prompt_id` 作为入口」（单数）。A/B/C 是三个身份。未说明是只点 B，还是三枪都要 id。
- **驱动输入**：`T-O-348/339/347`、S02 extra=forbid

#### 选项清单

| 选项 | 方案 | 含义 |
|---|---|---|
| **A** | **至少 B；A/C 可省（推荐）** | 文档 ingest **必填** `structure_prompt_id`（角色必须是 promptB）。`clean_prompt_id` / `summary_prompt_id` 可选；省略则用 catalog 里该 role 的 **default** 指针（仍走 hash 校验）。LLM clean 才解析 A；确定性/API clean 忽略 A。C 用 `summary_prompt_id` 或 default。禁止只给一个 id 让系统猜角色。 |
| **B** | **三枪都必填** | 每次 ingest 必须同时给 A/B/C 三个 `prompt_id`，角色校验失败则 422。无 catalog default。 |
| **C** | **只收一个 `prompt_id`，角色自描述** | 一个 id；catalog 行上的 `role` 决定它是 A 还是 B 还是 C，其余两枪永远 default。无法一次点名法律 B + 专用 C。 |

#### 当前建议 / 倾向

**推荐 A（入口主 id 是 B；A/C 可省到 role default）。**

#### 推荐执行细节（选 A 时）

1. JSON 字段名闭集：`structure_prompt_id` required；`clean_prompt_id`、`summary_prompt_id` optional。  
2. id 在 catalog 不存在 / role 不匹配 / hash 失败 = 配置失败，不进人审。  
3. materialize 把三个 **解析后的 hash+path** 写入 command digest，之后不重读 default。  
4. 禁止 C：单 id 多职猜测。禁止 B 逼每一条确定性 inline 也填 A。

#### Supporting Reasoning

- **反对 B**：与 D08「多数 clean 无 LLM」不一致，调用面过重。  
- **反对 C**：一个 id 点不齐「法律 B + 专用摘要 C」。  
- **A**：符合「处理文档以 prompt_id 为入口」（主入口是结构变体），又不拆掉三身份。

#### 问题（请业主裁决）

**Q8：API `prompt_id` 集合选 A / B / C？若选 A，是否确认：必填 `structure_prompt_id`；A/C 可选且 default 仍走 catalog+hash；禁止单 id 猜角色？**

- **业主回答**：在推荐 **A**（主入口是结构变体；A/C 可有 default）之上 **扩充角色闭集**，不采用原稿「单一 `structure_prompt_id`」：
  1. 分类改为四档：`promptA = clean`；`promptB.md = markdown`；`promptB.json = json`；`promptC = summarizer`。
  2. summarizer 之前 **可以** 连续两跳 B：先 markdown，再 json。
  3. A 与 C 相对固定，**都可以有 catalog default**。
  4. `promptB.md` **可以跳过**（不提供 `markdown_prompt_id`）。
  5. `promptB.json` **不能跳过**；其产物是 C **直接消费的主体**（对齐 `T-O-347`）。
  → **冻结为 `T-O-350`**
- **裁决状态**：`accepted / frozen / expanded`

---

### Q9 — `granularity_set` 挂在哪里（**驱动真相：`T-O-344` · `T-O-348`**）

- **影响范围**：catalog 行 schema、`command_input_digest`、法律/房产闭集如何随 `prompt_id` 到达 kernel
- **为什么必须确认**：Q6 原稿要单独的 `structure_profile_ref`。业主改为只收 `prompt_id`。`T-O-344` 的闭集必须有唯一挂载点，否则 kernel 又只能猜。
- **驱动输入**：`T-O-344/348`、S05 三轴

#### 选项清单

| 选项 | 方案 | 含义 |
|---|---|---|
| **A** | **挂在 catalog 行上（推荐）** | 每个 B 角色的 catalog 版本行 **必有** `granularity_set`（及规范化配方 digest）。解析 `structure_prompt_id` 即得到 profile。API **不再**收独立 `profile_id`。换闭集 = 新版本行（随 Q7）。 |
| **B** | **API 另收 `profile_id`** | `prompt_id` 只指 md 文件；粒度闭集是第二本目录。Caller 必须成对提交，且两者兼容。 |
| **C** | **只写在 md frontmatter，运行时解析** | 文件头 YAML 声明粒度；DB 不存闭集。hash 仍校验全文（含 frontmatter）。catalog 与 kernel 对闭集没有独立 digest。 |

#### 当前建议 / 倾向

**推荐 A（一个 `prompt_id` 带上闭集）。**

#### 推荐执行细节（选 A 时）

1. `promptB.legal` 行：`granularity_set={0,1}`；`realestate={0}`；`default={0,1,2}`。  
2. 该集合进入 `command_input_digest`。  
3. 禁止 B：入口再次分裂成不可靠的第二指针。  
4. 禁止 C：闭集只活在文件里、DB 无登记，和「catalog 是解析权威」不一致。

#### Supporting Reasoning

- **反对 B**：业主刚否决不可靠指针，不宜再加 `profile_id`。  
- **反对 C**：frontmatter 可以，但必须在 **登记时** 抽进 catalog 并进 hash；不能每次运行现解析当 SSOT。若抽进行，C 就退化成 A 的编辑方式。  
- **A**：与 `T-O-348` 单入口一致，kernel 不再猜。

#### 问题（请业主裁决）

**Q9：粒度闭集挂载选 A / B / C？若选 A，是否确认：闭集是 B 类 catalog 行的必填字段；API 不再收 `profile_id`；换闭集走新版本？**

- **业主回答**：接受推荐 **A**（闭集挂 catalog 行；API 不收 `profile_id`；换闭集走新版本）。随 Q8 收窄：`granularity_set` **只强制**于角色 `json` 的行。→ **冻结为 `T-O-351`**
- **裁决状态**：`accepted / frozen`

---

## 10. Round 3 题目与 Truth 映射（已冻结）

| 题 | 焦点 | 驱动真相 | Owner 选择 | Truth-ID | 状态 |
|---|---|---|---|---|---|
| Q7 | catalog CRUD 变异 | `T-O-348` | **A** | `T-O-349` | `frozen` |
| Q8 | API prompt 角色与跳过规则 | `T-O-348/339/347` | **A 扩充为四角色** | `T-O-350` | `frozen` |
| Q9 | granularity 挂载点 | `T-O-344/348` | **A**（挂 json 行） | `T-O-351` | `frozen` |

---

## 11. ★ 中场评估 III（Round 3 → 收口）

### 11.1 对 Round 3 的判定

| 题 | 决断 | 关键性 |
|---|---|---|
| Q7 | 指针目录 + 不可变版本 | catalog 可编码，且不热切 |
| Q8 | 四角色；B 可两跳；json 不可跳；C 只吃 json | **本轮产品主轴**。把当时法律「markdown 再 JSON」收成正式 role，而不是 P4 猜想 |
| Q9 | 闭集挂在 `json` 行 | kernel 只对 B.json 做粒度门闩，不误绑 markdown |

三题均决断。Q8 是扩充不是否决 A：A/C 仍可 default；「主入口是结构」被精确成 **json 不可省、markdown 可省**。

### 11.2 本轮已锁定真相

`T-O-349`（CRUD 版本）、`T-O-350`（四角色与两跳 B）、`T-O-351`（闭集在 json 行）。

### 11.3 诚实反方制衡

1. **`T-O-339` 三身份 vs `T-O-350` 四 role**：没有第五个生产字母，但执行上 B 变成两枪。Workflow 必须有可跳过的 markdown 步；图比 `lsrag_definition.py` 现状多一跳。  
2. **B.md 失败** 按 `T-O-341` 是本文件 failed，不能「自动改走 skip markdown」。跳过只发生在 **未提供** `markdown_prompt_id`。  
3. **B.md 没有 schema**：质量只靠 prompt 正文；坏 markdown 会在 B.json / kernel 锚定（`T-O-346`）处爆。这是刻意的，不是漏问。  
4. **S14 trinity 命名**（`promptA.default.v1`）要映射到 catalog `role`+`prompt_id`；identity 字符串仍不是 API 入口。  
5. **内部 CRUD** 仍是对 S14「非公网 CRUD」的窄解释，formal S14 回填未做。

### 11.4 为什么不生成 Round 4

3×3×3 题号已齐。剩余项 **不挡住** 按已冻 T-O 写执行方案，显式 defer：

| Deferred | 为何可后置 |
|---|---|
| 各跳是否一律 `claude -p` / 修理工 | 运输实现；身份与合同已冻 |
| B.md 的 Process key / 证据类型名 | 执行方案命名即可，不改产品面 |
| legal.case「分析」通道 | 变体正文问题，不是 catalog 形状 |
| D05 / S14 正文回填 | change-request，不阻塞 NS1 编码 |

无新的 foundational 开放轴必须再开一轮。

---

## 12. 收口（全轮冻结）

**冻结判据**：方向钉死；§1 `T-O-337..351` 全冻结；无 OPEN 残题（上表为 defer，非 OPEN）。

**NS1 可执行口令（下游方案必须服从）**：

```text
API: json_prompt_id 必填
     markdown_prompt_id?  clean_prompt_id?  summarizer_prompt_id?
        │
        ▼
catalog prompt_id → path + hash → H(file)==hash
        │
        ▼
A(clean) → [B.md markdown?] → B.json (layered_content.v1 + kernel)
        → C(summarizer 吃验收后 JSON) → S07 current → vectorize
```

- 正文只在 git；DB 只指针+hash；CRUD 出新版本。  
- B.json 不可跳；C 只吃 B.json。  
- 失败显式；不人审；sibling 跑完；root 仍 fail-closed。  
- `structurize(clean_text)` 假树退出生产 current。

**交接**：本文件 §1 → NS1 执行方案 / planning CITE。下一步写执行方案，不再改 QNA 提问。

---

## 13. 使用约束（本文件）

- 业主答复已全部冻结。推翻须在本文件 **追加修订**，不回收 T-O。  
- **不**自动开 Round 4。

---

## 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| `v0.1` | `2026-08-14` | `Grok` | pre-round；Round 1 Q1–Q3 开放 |
| `v0.2` | `2026-08-14` | `Grok` | Q1–Q3 冻结 `T-O-343..345`；注入 Q4–Q6 |
| `v0.3` | `2026-08-14` | `Grok` | Q4–Q5=A；Q6=`prompt_id`；注入 Q7–Q9 |
| `v0.4` | `2026-08-14` | `Grok` | Q7/Q9=A；Q8 四角色两跳 B（`T-O-349..351`）；中场 III；收口；不生成 Round 4 |
