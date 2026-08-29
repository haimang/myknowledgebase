# 调查面 `02` · 两阶段 S05 binding、evidence seal 与 recovery — 深度评估

> **对象 / scope-fence**：policy/envelope binding vs actual acquisition/clean/preflight binding；`s05_binding_digest` 写入时刻；seal CAS；ProcessCommand 携带什么 digest；CandidateSet/Snapshot/Gate/Proof 传播；retry / recovery / Task causal restart 各重放什么；未封闭 actual binding 的合法状态。**本面不含**：图形状 / kind identity（面 `01`）；representation 观察语义（面 `03`）；上传 CAS（面 `06`）；横切测试清单汇总（面 `09`，但本面必须列出本面最小 failure/replay 窗）。
> **日期**：`2026-08-29`
> **作者**：`Grok analysis-fleet / review-fleet`（fleet / panel：`new-harvest-reference-anchor`）
> **文档性质**：`assessment / analysis`（单面 measure-first 深评；零决策——只 MARK 不裁决）
> **文档状态**：`draft`
> **流水线位置**：站② · 上游 = [[assessment-index]]（消费其冻结分母）
> **对照参考**：HEAD `1221aa1`；QNA v0.5 `T-O-376..389`（只 CITE）；`docs/baseline/spec-glossary.md` `S05Binding`；`S05-T025/T026`；`S03-T017/T053`；`D04` Execution binding 列族；legacy-family clean dispatcher / universal / dedicated（`T-O-42` ReferenceAnchor）；Temporal / Cadence / AWS Step Functions / Kafka / Stripe 官方文档（机制/失败法，不证 MKB 现状）
> **上游权威输入**：
> - `docs/eval/new-harvest/assessment-index.md` — §2.2 冻结分母 `D-12/D-13` / §1.2 边界 / §3.02 本面登记 / §4 `G-NH-01`
> - `docs/eval/new-harvest/pre-initial-planning-qna.md` — `T-O-382/383/384/388` 与 §9.5.2 和解 #4（CITE，不扩冻）
> **下游消费者**：`docs/eval/new-harvest/planning-proposed.md` · `pre-charter-qna.md`（owner-gate 裁决）· 设计/执行制品
> **邻面对账**：冻结前应消费面 `01` selected-route 与面 `03` evidence。本轮复测 `docs/eval/new-harvest/reference-anchor/` **已有** `assessment-analysis-01-workflow-graph-and-kind-family.md` 与 `assessment-analysis-03-representation-and-reacquisition.md`（皆 `draft`）。§5 改为 **消费** `NH-RA01-B01/B04` 与 `NH-RA03-B03`；冲突候选仍 OPEN（本面不裁）。

---

## 0. Verdict（结论先行）`[核心]`

- **0.1 一句话缺口 / 现状判断**：HEAD 已有可复用的 **policy binding**（exact workflow revision / compiled digest / config snapshot / `domain_binding_digest`）与 **Task fingerprint / Process fence / Outcome 同 UoW 路由** substrate；但名为 `s05_binding_digest` 的列在创建时被填成 `domain_binding_digest`，DDL `NOT NULL` 无法表达「尚未选边」，ProcessCommand 从不读 actual S05，传播链复制的是政策别名——与 glossary/`S05-T025`/`D04` 的「创建时锁定 actual source/acquisition/clean/preflight」以及 QNA `T-O-384/388` 的「选边后一次封闭」构成 **真实 truth-to-schema / 列名盗用冲突**，不是和解完的假象。
- **0.2 Top blockers（最关键断点）**：
  1. `NH-RA02-B01`（S1）：`s05_binding_digest = domain_binding_digest` 在 Task 创建写入（列名盗用，不是可复用别名）。
  2. `NH-RA02-B02`（S1）：Execution 列 `NOT NULL` + 零 `UPDATE` 路径 → 无法表达未封闭 actual binding，也无法在选边 Outcome 后封闭。
  3. `NH-RA02-B03`（S1）：ProcessCommand 只有 `binding_digest ← domain_binding_digest`；clean Process 不能证明「绑定后不再换工人」。
- **0.3 总体方向建议**：把 **policy 账本**（图/revision/config/domain）与 **actual S05 账本**（走过的 acquire 路径 + 选中的 clean/preflight）分成两本账；未封闭必须有合法状态；封闭必须一次 CAS 且覆盖实际路径。**schema/命名形态只 MARK `G-NH-01` 三选项，本文不裁。** 外部只借「选择写入 durable history 后 resume 不重选 / 选择前 crash 允许重选 / at-least-once 下 exactly-once 是幻觉」；不借 Temporal/Cadence/SFN 引擎、不借 legacy `action_branch`。
- **0.4 如何读本台账**：见上方头部「图例」；本面主题轴 = `policy vs actual` / `seal 时刻与 CAS` / `传播读方` / `三窗 replay（封闭前 retry / 封闭后 retry / Task causal restart）` / `未封闭合法状态`。

---

## 1. 方法与证据基线 `[核心]`

> 读了哪些代码/文档/参考；什么算可采信；怎么复现。**先证可证性，再下判断。**

- **1.1 本仓证据（如何测量）**：
  - HEAD：`src/runtime/task/task_create.py`、`task_commands.py`；`src/persistence/migrations/001_initial.sql` Execution/Process/Gate/Snapshot/CandidateSet/PublicationProof；`src/runtime/workflow/runtime_core.py` `_command_from_process` / `_assert_execution_binding`；`runtime_materialize.py` route/gate；`runtime_outcome.py` retry/recovery/route；`src/contracts/runtime/models.py` `ProcessCommand`；`src/services/config_snapshots.py`；`src/runtime/intake/clean_preflight.py` / `acceptance_snapshot.py` / `acquisition_ingest.py`；`src/services/scatter_intake.py`；`src/workflows/lsrag_definition.py` `_source_profile_workflow`；`src/contracts/workflow/models.py` 单绑定。
  - 仓内 baseline：`spec-glossary.md` `S05Binding`；`S05-intake-cleaning.md` `S05-T025/T026` §3.10；`S03-workflow-engine.md` `S03-T017/T053`；`D04-turso-physical-schema.md` Execution binding 列族；`D01-T042`。
  - QNA：只 CITE `T-O-382/383/384/388` 与 §9.5.2 #4；**不把 QNA「未发现实际冲突」写成 HEAD 已和解**（index §2.4 已校正该失真）。
  - 测试：`rg s05_binding_digest tests/` —— 仅 fixture INSERT，无「选边后 digest 不随 retry 变」断言。
- **1.2 外部 / 参考来源 + 置信**：
  | 搜索词 | 打开的 primary URL | 版本/发布日 | 访问日 | 支持的原子结论 | 限制 / 失败条件 |
  |--------|-------------------|-------------|--------|----------------|-----------------|
  | `Temporal workflow replay history event workflowTaskCompleted official` | https://docs.temporal.io/workflows ；https://docs.temporal.io/references/events ；https://docs.temporal.io/encyclopedia/event-history/event-history-typescript | Temporal docs，页面标 2026-08 | `2026-08-29` | Event History 是 crash 后状态的 source of truth；Activity 结果写入 history 后 replay 不重跑；Worker 在 Workflow Task 中途 crash → `WorkflowTaskTimedOut` 后新 Task **重放代码** | 不得把 Temporal replay 引擎当本仓机制；非确定性分支（随机数）在 replay 会失配 |
  | `Cadence deterministic replay version marker official` | https://cadenceworkflow.io/docs/go-client/workflow-versioning ；https://cadenceworkflow.io/docs/go-client/workflow-non-deterministic-error | Cadence 官方 Go client docs | `2026-08-29` | `GetVersion` 首次把 version 记为 history **marker**，之后 replay 永远返回该值；无 marker 的代码变更 → non-deterministic error | Cadence 是 event-sourced workflow 代码版本法，不是 MKB 七表；activity 内部改实现不写 history |
  | `AWS Step Functions execution history Choice state official` | https://docs.aws.amazon.com/step-functions/latest/dg/state-choice.md ；https://docs.aws.amazon.com/step-functions/latest/apireference/API_HistoryEvent.html | AWS Step Functions DG + API Reference | `2026-08-29` | Choice 是声明式状态；history 含 `ChoiceStateEntered` / `ChoiceStateExited`；无匹配且无 `Default` → 转换失败 | Express workflow 不提供同样的 GetExecutionHistory；Choice 不支持 `End` |
  | `idempotency key compare-and-swap state transition crash recovery` + Stripe official | https://docs.stripe.com/api/idempotent_requests | Stripe API Reference | `2026-08-29` | 同 key 重放返回首次结果（含 500）；并发同 key 不同执行 → 不保存结果，可 retry；参数变则 error | key 约 24h 过期后当新请求；GET/DELETE 不需要 |
  | `exactly-once illusion at-least-once processing original paper or official` | https://docs.confluent.io/kafka/design/delivery-semantics.html （Confluent 官方 Kafka design；Apache Kafka 同源语义） | Confluent Kafka design docs | `2026-08-29` | 默认 at-least-once；许多系统声称 exactly-once 但不覆盖 producer/consumer 失败；真正 EOS 需要事务+对端配合 | 不得把 Kafka 事务栈搬进 MKB；本仓应对应「CAS + 幂等 key + 同 tx」而非 broker EOS |
  | Temporal patching | https://docs.temporal.io/patching | Temporal Patching | `2026-08-29` | 部署时正在跑的 execution replay **不走新 patch 分支**；marker 位置错 → non-determinism | Worker Versioning / patch API 越界，最多借「已记录选择不可被新代码改写」 |
- **1.3 ★ 可复现命令清单（measure-first）**：
```bash
git rev-parse --short HEAD   # 期望 1221aa1

rg -n "s05_binding_digest|domain_binding_digest" \
  src/persistence/migrations/001_initial.sql src/runtime/task src/runtime/workflow \
  src/runtime/intake src/services src/contracts/runtime/models.py

nl -ba src/runtime/task/task_create.py | sed -n '67,104p;167,187p;337,368p'
nl -ba src/runtime/workflow/runtime_core.py | sed -n '888,917p;591,636p'
nl -ba src/runtime/workflow/runtime_materialize.py | sed -n '546,593p'
nl -ba src/runtime/intake/clean_preflight.py | sed -n '28,120p;373,399p;600,616p'
nl -ba src/persistence/migrations/001_initial.sql | sed -n '241,250p;301,345p;391,405p;915,928p;1110,1120p'

rg -n "action_branch|STEP_RESTART|plainTextAvailable" \
  context/legacy-family/smind-clean-dispatcher \
  context/legacy-family/smind-skill-clean-universal \
  context/legacy-family/smind-skill-clean-dedicated-apis

rg -n "s05_binding_digest" tests

uv run python - <<'PY'
from pathlib import Path
import re
pc = Path("src/contracts/runtime/models.py").read_text()
m = re.search(r"class ProcessCommand.*?(?=\nclass )", pc, re.S).group(0)
print("ProcessCommand.s05_field", "s05_binding_digest" in m)
print("ProcessCommand.binding_digest", "binding_digest:" in m)
sql = Path("src/persistence/migrations/001_initial.sql").read_text().splitlines()
print("ddl_s05_lines", [i+1 for i,l in enumerate(sql) if "s05_binding_digest" in l])
src_hits = []
for p in Path("src").rglob("*.py"):
    for i,l in enumerate(p.read_text().splitlines(),1):
        if "s05_binding_digest" in l:
            src_hits.append(f"{p}:{i}")
print("py_s05_sites", len(src_hits))
for h in src_hits: print(h)
PY
```
- **1.4 范围围栏**：本面**只**覆盖 binding 生命周期、seal、传播、三窗 recovery；图代数/kind 家族交面 `01`；representation/reacquire 观察器交面 `03`；upload CAS 交面 `06`；横切 mega/fake-green 总表交面 `09`。公开网络只证外部机制，**不得**证明 MKB 当前状态。

---

## 2. 当前结构分析（HEAD 实测 · measure-first）★ `[核心]`

> 按主题轴逐条测，每条钉 `path:line`。先冻结本面分母，再逐轴展开。

### 2.1 ★ 冻结分母（FROZEN denominators · HEAD）

> 共享分母引用 [[assessment-index]] §2.2，不得另估。本面新测分母另表，命令见 §1.3。

| 分母 | HEAD 实测值 | 证据锚（`path:line`） | 来源 |
|------|-------------|------------------------|------|
| `D-12` Execution actual S05 digest 字段 | `1`，`NOT NULL`，创建时由 domain digest 填入 | `001_initial.sql:245-246`；`task_create.py:167-181,337-368` | `index §2.2` |
| `D-13` acquisition/decode evidence history | 单值 `1+1`；声明式 reacquire edge `0` | `acquisition_ingest.py:597-676`；`clean_preflight.py:622-686`；graph routes | `index §2.2` |
| `D-10` 单 target input 可声明 source binding 数 | `1` | `src/contracts/workflow/models.py:482-525` | `index §2.2`（面 01 主责，本面消费） |
| `D-02-01` ProcessCommand 独立 s05 字段 | `0`（仅 `binding_digest`） | `src/contracts/runtime/models.py:13-29` | 本面新测 |
| `D-02-02` ProcessCommand.binding_digest 来源 | 恒为 `process["domain_binding_digest"]` | `runtime_core.py:888-917`；claim SELECT 只 join `e.domain_binding_digest`（`runtime_core.py:357-358,384-385,397-398,578`） | 本面新测 |
| `D-02-03` Execution `s05_binding_digest` 创建后 UPDATE | `0` | `rg UPDATE.*s05_binding_digest src` 无命中；写点仅 `task_create.py:180` 与 `task_commands.py:306` INSERT | 本面新测 |
| `D-02-04` DDL 含 `s05_binding_digest` 的表 | `3`：`mkb_executions` NOT NULL；`mkb_intake_snapshots` **nullable**；`mkb_intake_candidate_sets` NOT NULL | `001_initial.sql:246,927,1119` | 本面新测 |
| `D-02-05` Snapshot 写入点数 | `2`，值 = `command.binding_digest`（domain） | `acceptance_snapshot.py:137-151`；`scatter_intake.py:159-173` | 本面新测 |
| `D-02-06` CandidateSet 写入点数 | `2`，值 = `stable_digest({"binding": command.binding_digest})` | `clean_preflight.py:373-395,476-498` | 本面新测 |
| `D-02-07` Gate 复制 Execution.s05 点数 | `2`（review_target.workflow_binding + gate.binding_digest 哈希材料） | `runtime_materialize.py:555-560,586-591` | 本面新测 |
| `D-02-08` Process 行 / PublicationProof 的 s05 列 | `0` / `0` | `001_initial.sql:301-345`；`1532-1558` | 本面新测 |
| `D-02-09` scatter child Execution 的 s05 来源 | `command.binding_digest`（domain），不是 root 行的独立 actual | `scatter_intake.py:582-603` | 本面新测 |
| `D-02-10` 图工厂每张 profile 的 clean 步骤数 | `1`（编译期钉死 `clean_process_key`） | `lsrag_definition.py:111-118,881-926` | 本面新测 |
| `D-02-11` Process retry 是否重跑 registry resolve | `否`（同 process 行 `retry_wait→ready`，保留 `process_key`/`process_spec_digest`） | `runtime_outcome.py:145-182,237-254` | 本面新测 |
| `D-02-12` 测试对「选边后 digest 稳定」的断言 | `0`（仅 fixture 填列） | `tests/unit/test_*.py` 12 处 INSERT 列名 | 本面新测 |

### 2.2 轴 `policy binding`（HEAD 核验 · 正例）

- Task 创建对 `creation_fingerprint` **双检**：先只读事务查既有 Task，指纹不同 → `ConflictError("task-identity-conflict")`；业务 UoW 插入前再检一次，唯一约束冲突同样按指纹 replay/冲突分账（`task_create.py:67-86,89-141`）。这证明 **policy 身份**已有 at-least-once 下的幂等窗，可复用，不证明 actual S05。
- Execution 创建即冻结 **图身份 + 配置**：`workflow_uuid` / `workflow_revision_uuid` / `compiled_digest` / `config_snapshot_ref` / `config_snapshot_digest` / `domain_binding_digest` 全 `NOT NULL`（`001_initial.sql:241-250`）。`domain_binding_digest` 由 config snapshot digest + compiled digest + intent + override + semantic knobs 算出（`config_snapshots.py:254-263`），是 **envelope/policy** digest。
- `_assert_execution_binding` 用 Execution 已存 `compiled_digest` 解析 reviewed plan，**禁止**对当前 active 图热切（`runtime_core.py:591-636`）。这兑现 `S03-T017`「创建时绑 exact revision，retry 不热切 **图**」。
- Process 物化把 `workflow_revision_uuid`、`process_key`、`contract_version`、`config_snapshot_digest`、`route_decision_digest` 编进 `process_spec_digest`（`runtime_materialize.py:290-307`），行上保留 `process_key`（`327-353`）。**同 Execution 内 Process retry 不重新 materialize 另一步**（`runtime_outcome.py:145-182`）。

### 2.3 轴 `actual S05 列名与写入时刻`（HEAD 核验 · 反例 / 冲突）

- 创建路径把 **同一个** `prepared.domain_binding_digest` 写入 `domain_binding_digest` **和** `s05_binding_digest`（`task_create.py:179-180`）。`_insert_root_execution` 在缺省时 `resolved_s05_digest = s05_binding_digest or binding_digest`（`task_create.py:337-340`），再一次把政策 digest 填进 S05 列。
- 全仓 `src/` **没有** `UPDATE ... s05_binding_digest`。选边后封闭在 HEAD **物理不存在**。
- DDL：`mkb_executions.s05_binding_digest TEXT NOT NULL`（`001_initial.sql:245-246`）。合法状态机无法表示「Execution 已创建、actual 尚未选边」。对比：`mkb_intake_snapshots.s05_binding_digest` **可空**（`927`），说明 schema 作者并非处处强制创建时 actual——但 Execution 这条权威列强制了。
- glossary 仍写「Execution**创建时**锁定本次 source/acquisition/clean/preflight exact refs」（`spec-glossary.md:231`）。`S05-T025`：「Execution 锁定本次**实际使用**的 source/acquisition/clean/preflight exact refs 与 `s05_binding_digest`」（`S05-intake-cleaning.md:229`）。`D04`：「Binding … `s05_binding_digest` | NOT NULL（**创建时**）」（`D04-turso-physical-schema.md:622`）。`D01-T042` 同文（`D01-task-execution-process-flow.md:253`）。
- QNA `T-O-384` 要求 digest 在 **选边 Outcome 提交后** 封闭（QNA `:88`）；`T-O-388` 要求封闭覆盖 **实际走过的 acquire 路径**（QNA `:92`）。QNA §9.5.2 #4 把张力解释为「`S03-T017` 冻图、`S03-T053` 冻已封闭 actual」（QNA `:765`），并在 §9.5.1 写「未发现实际冲突」（`:756`）。**这只和解了 T017 与晚绑定的图时序，没有消掉 glossary/`S05-T025`/`D04`/DDL 的创建时 actual 法。** index §2.4 已把「QNA 已完成无实际冲突审查」标为高估。本面维持该校正：**冲突仍在**。

**对必须问题 4 的实测回答**：当前 `s05_binding_digest = domain_binding_digest` 是 **谎言（盗用列名）**，不是可复用别名。别名会在读方声明「此列=policy」；HEAD 读方（Gate target、CandidateSet 列名、Snapshot 列名、D04 文档）都把它当 **S05 actual**。

### 2.4 轴 `ProcessCommand 与 handler 选工人`（HEAD 核验）

- `ProcessCommand` 字段闭集无 `s05_binding_digest`，只有 `binding_digest`（`models.py:13-29`）。
- `_command_from_process` 要求 `domain_binding_digest` 非空，赋值 `binding_digest=process["domain_binding_digest"]`（`runtime_core.py:888-917`）。claim 查询从不 SELECT `e.s05_binding_digest`。
- `_clean` 用 `command.process_key` + 本地 `state["acquisition_evidence"].representation_kind` **表外 remap** 到 `CleanStrategyKey`，再 `dispatch_clean(...)`（`clean_preflight.py:46-71,108-121`）。例：`clean.extract.pdf_llm` 在 `representation=="print_pdf"` 时改走 `WEB_BROWSER_PRINT_PDF`，否则 `PDF_DOCUMENT_UNDERSTANDING`（`:58-63`）。这正是 QNA Q4-B「表外策略包 + 通用 `dispatch_clean`」的 HEAD 实例，已被业主以 `T-O-384` 否决。
- 图工厂 `_source_profile_workflow` 每张 profile **一个** `clean_process_key`，编译进单一步骤 `clean`（`lsrag_definition.py:111-118,913-925`）。工人在 **选图时** 已钉死，不是表示已知后的图内选边。

**对必须问题 5 的实测回答**：ProcessCommand 只用 domain binding 时，clean Process **不能**证明「绑定后不再换工人」。它只能证明：这次 claim 带着冻结的 **config/workflow policy** 与图编译时的 **那个** `process_key`。handler 仍可按 representation 换 strategy；retry 再进 `_clean` 会再跑同一张 map。`T-O-383` 的「不再换工人」在 HEAD 没有 durable 证人。

### 2.5 轴 `传播：CandidateSet / Snapshot / Gate / Proof`

- CandidateSet INSERT 把 `s05_binding_digest` 写成 `stable_digest({"binding": command.binding_digest})`（`clean_preflight.py:395,498`）——对 **domain** digest 再包一层，不是 actual acquire/clean refs 的聚合（对照 `S05` §3.10，`S05-intake-cleaning.md:466-476`）。
- Snapshot 直接写 `command.binding_digest`（`acceptance_snapshot.py:151`；scatter 同，`scatter_intake.py:173`）。
- Gate：`review_target.workflow_binding.s05_binding_digest = current_execution["s05_binding_digest"]`（`runtime_materialize.py:555-560`）；gate 行 `binding_digest` 哈希含该值（`:586-591`）。**传播机制是正例**（digest 一旦在 Execution 行上就会被复制）；**值是反例**（复制的是创建时政策别名）。
- Process `proof_ref/proof_digest` 与 `mkb_publication_proofs` **没有** s05 列（`001_initial.sql:344-345,1532-1558`）。Proof 不能独立见证 actual binding。
- scatter child Execution 的 `s05_binding_digest` 取 `command.binding_digest`（`scatter_intake.py:602-603`），与 root 的政策 digest 对齐，仍非 actual。

### 2.6 轴 `seal CAS 与 route Outcome 是否同事务`

- Process 成功路径：`outcome_committer.validate_and_commit`（业务 artifact/proof）与 Process 行 CAS `running→succeeded`、随后 `_route_after_terminal_process_tx` **同一 `tx`**（`runtime_outcome.py:88-137`）。注释写明 caller-owned mutation 与 fence/CAS 必须同 UoW（`:89-92`）。这是 **可复用的同事务 substrate**。
- CandidateSet 从 `open` CAS 到 `sealed` 有独立栅栏（`clean_preflight.py:600-616`，`rowcount != 1 → CANDIDATE_SET_FENCE`）。这是 **集合 seal**，不是 actual S05 binding seal。
- **HEAD 不存在**「选边 Outcome 提交 ∧ 封闭 `s05_binding_digest`」这一事务。问题「seal 与 route outcome 是否必须同事务」在产品法上仍 OPEN，交 `G-NH-11`；HEAD 只证明：若要做，现成 UoW/CAS 能承载，而不是已经做了。

### 2.7 轴 `三窗 replay`（封闭前 / 封闭后 / causal restart）

HEAD **没有未封闭窗**（创建即写伪 s05）。按现码能测到的重放行为：

| 窗 | HEAD 实际重放什么 | 不重放什么 | 与目标产品法的差距 |
|----|-------------------|------------|--------------------|
| Process retry（同 Execution、同 process 行） | 同一 `process_key` / `process_spec_digest` / `config_snapshot_*`；`retry_count++`，`fencing_generation` 不变（`runtime_outcome.py:145-182`） | 不重新 `prepare()` registry；不 UPDATE s05 | 若工人尚未经声明式选边封闭，retry 仍进 handler 表外 map（`clean_preflight.py:54-71`） |
| Lease recovery | `fencing_generation++`，`recovery_count++`，同 process 行回到 `ready`（`runtime_outcome.py:287-368`）；`safe_replay=false` 则 fail-loud | 不换 `process_key` | 恢复的是 **步骤**，不是 actual binding 的封闭值 |
| 封闭后 retry（目标） | 无独立实现 | — | `T-O-384/388` 要求重放 **已封闭 digest**，禁止后一次选边覆盖 |
| Task causal restart / 新 generation | 新 Execution 行复制 **previous** 的 workflow/config/**s05**（`task_commands.py:293-311`）；`S03-T018`/`S05-T026` 语义：升级走新 generation | 不重新 resolve active workflow（正例） | 复制的 s05 仍是政策别名；新 generation 会 **重新跑整图**，若晚绑定存在，等于在新 Execution 上再选一次——这是升级窗，不是同 Execution resume |

**对必须问题 3 的草案回答（不冻结）**：

1. **封闭前 retry / crash**：允许在已声明边上重新做选择（选择尚未写入 durable actual）；必须重放 **policy**（revision/config/domain），不得热切图。对应 Temporal「`WorkflowTaskTimedOut` 发生在选择写入 history 之前 → 新 Task 重跑决策代码」（§3 WEB）。
2. **封闭后 retry / human resume / lease recovery**：重放封闭后的 actual digest 与已物化 `process_key`；禁止再 resolve active clean/acquire；禁止 handler 换 `process_key`。
3. **Task causal restart**：新 generation 继承 **policy** 是否继承 **actual** 是产品缝（`S03-T018` 说 full retry 继承 exact revision；`S05-T026` 说用新实现必须新 generation）。**不在本面裁决**；只要求两本账分开复制，禁止把未封闭 actual 假装已锁。

### 2.8 轴 `未封闭 actual 的合法状态`（只列候选）

**对必须问题 1**：HEAD 今日用「非空伪值」冒充已封闭，**没有**合法未封闭状态。候选（并列，不冻结，交 `G-NH-01`）：

| 候选 | 含义 | HEAD 暗示 |
|------|------|-----------|
| A. 保留 policy 列 + **新增** actual 列（nullable 或显式 unsealed token） | `domain_binding_digest` 继续创建即填；actual 另列，选边后一次写 | 最贴近「两本账」；要改 DDL/读方 |
| B. 现列改为 nullable actual + 显式 sealed state（Execution phase/flag/status 正交字段） | 未封闭 = NULL + unsealed；封闭 = 非空 + sealed | Snapshot 列已经 nullable（`001_initial.sql:927`）提供局部类比，**不是**推荐 |
| C. 双 digest 列 + 显式 unsealed state（policy NOT NULL + actual nullable + state） | A+B 组合 | 表达力最强，迁移最重 |
| D. 其他经证据支持：独立 binding 行/CAS 对象，Execution 只持 ref | 把 actual 从 Execution 宽列拆出 | 接近 CandidateSet 已有 `s05_binding_digest` 列，但今日值错 |

禁止把「继续用 domain 填 s05」当作候选——那是当前谎言，不是方案。

### 2.9 对参考 / 既有叙事的失真校正（本面）

| 叙事/参考声称 | HEAD 实测 | 失真类型 | 证据 |
|---|---|---|---|
| QNA §9.5.1「未发现实际冲突」；initial `T-P-NH-13`「推迟封闭只是实现后果」 | glossary/`S05-T025`/`D04`/DDL 仍要求创建时 actual；HEAD 创建即写 domain | 高估和解 | QNA `:756,765`；`spec-glossary.md:231`；`001_initial.sql:245-246`；`task_create.py:180` |
| 列名 `s05_binding_digest` 已表示 actual S05 | 值 = domain；无 acquire/clean/preflight refs | 列名盗用 | `task_create.py:179-180`；`config_snapshots.py:254-263` |
| Gate 携带 s05 ⇒ actual 已封闭 | 只证明传播，不证明语义 | 类比过度 | `runtime_materialize.py:555-560` |
| Process retry 不热切 ⇒ 工人已锁 | 锁的是图步骤的 `process_key`，handler 仍 remap strategy | 高估 | `runtime_outcome.py:145-182`；`clean_preflight.py:54-71` |
| CandidateSet.s05 是 S05 binding 聚合 | `stable_digest({"binding": domain})` | 名实不符 | `clean_preflight.py:395` vs `S05-intake-cleaning.md:466-476` |

`docs/eval/new-harvest/initial-planning.md` / thoughts 中的 `T-P-NH-*` 是待核 first-cut，**不是**本面真相。

---

## 3. 借鉴锚定矩阵（Reference Anchor Matrix）★ `[核心]`

> 每个可借鉴点钉到 `path:line` / URL，给**借鉴 verdict**。每条 `RA-*`：结论原子句 / 来源 / 正例或反例 / 置信 / substrate-fit / 命中缺口。

| 借鉴点 | 来源锚（`path:line` / URL） | 借鉴 verdict | 借什么 / 不借什么 |
|--------|------------------------------|--------------|--------------------|
| Task 指纹双检 + 唯一冲突分账 | `task_create.py:67-104,130-141` · `RA-02-HEAD-01` | `✅借` | 借：policy 身份的 at-least-once 幂等。不借：把 fingerprint 当 actual S05。命中：可复用 substrate，非缺口。置信：HEAD 实测 |
| Execution 创建冻结图/config/domain | `001_initial.sql:241-250`；`config_snapshots.py:254-263` · `RA-02-HEAD-02` | `✅借` | 借：`S03-T017` policy 冻结。不借：把同一 digest 写入 s05 列。缺口：`NH-RA02-B01` |
| 按 compiled digest 断言 plan，不热切 active | `runtime_core.py:591-636` · `RA-02-HEAD-03` | `✅借` | 借：resume 不换图。不借：当作 actual clean 已锁 |
| Gate 复制 Execution 行上 digest | `runtime_materialize.py:555-591` · `RA-02-HEAD-04` | `🔶部分借` | 借：digest 一旦在行上就会被传播的模式。不借：今日被传播的伪值。缺口：`NH-RA02-B09` |
| Process Outcome 与 route 同 UoW + fence CAS | `runtime_outcome.py:88-137` · `RA-02-HEAD-05` | `✅借` | 借：seal 若要做，可落在此 UoW。不借：今日已封闭 actual。命中 `G-NH-11` |
| CandidateSet `open→sealed` CAS | `clean_preflight.py:600-616` · `RA-02-HEAD-06` | `🔶部分借` | 借：集合 seal 栅栏。不借：该 seal 的 s05 列语义 |
| Process retry 保留 process 行 | `runtime_outcome.py:145-182` · `RA-02-HEAD-07` | `🔶部分借` | 借：失败停在 step。不借：handler 内换 strategy |
| Causal restart 复制 previous binding | `task_commands.py:293-311` · `RA-02-HEAD-08` | `🔶部分借` | 借：新 generation 不 resolve active 图。不借：连伪 s05 一起复制冒充 actual |
| 创建时 s05=domain | `task_create.py:179-180,337-340` · `RA-02-HEAD-09` | `⛔反例` | 不借列名盗用。缺口 `NH-RA02-B01` |
| Execution s05 NOT NULL | `001_initial.sql:245-246` · `RA-02-HEAD-10` | `⛔反例` | 相对目标法：无法表达未封闭。缺口 `NH-RA02-B02` |
| ProcessCommand 无 s05、只用 domain | `models.py:13-29`；`runtime_core.py:888-917` · `RA-02-HEAD-11` | `⛔反例` | 不能证明绑后不换工人。缺口 `NH-RA02-B03` |
| 零 UPDATE s05 | 写点仅 `task_create.py:180` INSERT 与 `task_commands.py:306` 复制；`src/` 无 `UPDATE ... s05_binding_digest` · `RA-02-HEAD-12` | `⛔反例` | 无晚封闭路径。缺口 `NH-RA02-B04` |
| Snapshot/Candidate 写 domain 别名 | `acceptance_snapshot.py:151`；`clean_preflight.py:395` · `RA-02-HEAD-13` | `⛔反例` | 传播链污染。缺口 `NH-RA02-B05` |
| handler `dispatch_clean` remap | `clean_preflight.py:46-71,108-121` · `RA-02-HEAD-14` | `⛔反例` | Q4-B 已否。缺口 `NH-RA02-B06` |
| 单值 acquire/decode evidence、无 reacquire 边 | `acquisition_ingest.py:579-593,597-676`；`D-13` · `RA-02-HEAD-15` | `⛔反例` | 无法 digest 有限再获取链。缺口 `NH-RA02-B07`（与面 03 对账） |
| 图工厂编译期单 clean key | `lsrag_definition.py:111-118,881-926` · `RA-02-HEAD-16` | `⛔反例` | 选图=选工人，与 `T-O-382` 相反。交面 01 图表达力 |
| 测试只 fixture 填 s05 | `tests/unit/test_dispatch_*.py` 等 · `RA-02-HEAD-17` | `⛔反例` | 假绿：有列无断言。缺口 `NH-RA02-B11` |
| glossary 创建时锁 actual | `spec-glossary.md:231` · `RA-02-BASELINE-01` | `⛔反例`（相对 `T-O-384`） | 仓内 frozen 词汇与新 QNA 冲突，必须显式登记，不自动覆盖 |
| `S05-T025/T026` actual + 不热切 | `S05-intake-cleaning.md:229-230,466-478` · `RA-02-BASELINE-02` | `🔶部分借` | 借：封闭后不热切、升级走 causal restart。不借：把「锁定」冻死在 **创建时** |
| `S03-T017` vs `S03-T053` | `S03-workflow-engine.md:181,242` · `RA-02-BASELINE-03` | `🔶部分借` | 借：两句本来就可以分账（图 vs actual）。不借：HEAD 用一列混写。QNA #4 只覆盖这一对 |
| D04「NOT NULL 创建时」 | `D04-turso-physical-schema.md:622` · `RA-02-BASELINE-04` | `⛔反例`（相对晚绑定） | schema 宪法与 `T-O-384` 冲突；改 DDL 需显式 reopen，本面不锁列名 |
| dispatcher 把 `action_branch` 写入消息 | `smind-clean-dispatcher/services/mapper.ts:195-200` · `RA-02-LEGACY-01` | `⛔反例` | 不借：无 digest 的 branch 热切、`action_branch` taxonomy（`T-O-377`/`D08-T004`） |
| Restarter 显式 `STEP_START` / `STEP_RESTART` | `restarter.ts:802-850` · `RA-02-LEGACY-02` | `🔶部分借` | 借：重启必须带意图；失败停在 step。不借：先发队列再写库（`:812-814,852-854`）、force 完成步再 `STEP_START` 新 UUID |
| Restarter 重读 **当前** `workflow.steps_definition` | `restarter.ts:478-483,740-758` · `RA-02-LEGACY-03` | `⛔反例` | 重启可拿到新 branch 定义 = 热切。不借 |
| Universal router 按 `action_branch` 运行中分发 | `smind-skill-clean-universal/flows/router.ts:42-59,95-99` · `RA-02-LEGACY-04` | `⛔反例` | 运行中换 branch；未知前缀 **warn 后跳过 schema**。不借 |
| Dedicated member catch 后 skip，任务仍成功 | `providers/realestate/processor.ts:284-287`；`providers/chinatax/processor.ts:150-154` · `RA-02-LEGACY-05` | `⛔反例` | 不借 silent skip / 部分失败当成功 |
| `plainTextAvailable: true` 无非空检查 | `cleaner_web.ts:320-321` · `RA-02-LEGACY-06` | `⛔反例` | 空成功；与 `T-O-383` 冲突。不借 |
| Temporal Event History + replay | https://docs.temporal.io/workflows · `RA-02-WEB-01` | `🔶部分借` | 借：选择/Activity 结果写入 durable history 后 resume **不重做**。不借：从零 replay 工作流代码的引擎、SDK、cloud |
| Crash 在 WorkflowTask 完成前 | https://docs.temporal.io/encyclopedia/event-history/event-history-typescript · `RA-02-WEB-02` | `🔶部分借` | 借：选择 **写入前** crash → 新 Task 重跑决策（对应封闭前窗）。不借：10s Workflow Task timeout 字面 |
| Temporal patch / Cadence `GetVersion` marker | https://docs.temporal.io/patching ；https://cadenceworkflow.io/docs/go-client/workflow-versioning · `RA-02-WEB-03` | `🔶部分借` | 借：version/choice **首次写入后不可被新代码改写**；无 marker 当 DefaultVersion。不借：GetVersion API、Worker Versioning。**两源独立产品线**（Cadence 官方 + Temporal 官方） |
| Cadence 改 workflow 定义 → non-deterministic | https://cadenceworkflow.io/docs/go-client/workflow-non-deterministic-error · `RA-02-WEB-04` | `⛔反例`（失败法） | 借失败法：resume 时代码/边顺序变了必须 fail-loud。不借 decision-task 栈 |
| AWS Choice + history entered/exited | https://docs.aws.amazon.com/step-functions/latest/dg/state-choice.md ；https://docs.aws.amazon.com/step-functions/latest/apireference/API_HistoryEvent.html · `RA-02-WEB-05` | `🔶部分借` | 借：声明式 Choice；选择进入/退出写入 execution history；无 Default 且无匹配 → **error**（未决 choice 不是成功）。不借：ASL JSON、AWS 控制面。与 Temporal **独立** primary |
| Kafka at-least-once vs 声称 EOS | https://docs.confluent.io/kafka/design/delivery-semantics.html · `RA-02-WEB-06` | `🔶部分借` | 借：默认 at-least-once；「exactly-once」需要事务+对端；许多声称不覆盖失败窗。不借：Kafka 事务/EOS 配置 |
| Stripe Idempotency-Key | https://docs.stripe.com/api/idempotent_requests · `RA-02-WEB-07` | `🔶部分借` | 借：同 key 返回首次结果（含失败）；并发冲突不保存、允许 retry；参数变则拒绝。不借：24h TTL 字面、支付 API。对应 Task fingerprint / Process fence |

**渠道满足 `G-NH-RA-03`**：HEAD 正例（`RA-02-HEAD-01..08`）与反例（`09..17`）成对；legacy 有借/不借；WEB 对「选择如何 durable」用 Temporal 与 AWS SFN 两独立 primary，并对 Cadence 限制条件、Kafka 声称 EOS、Stripe 并发冲突做失败核查。

---

## 4. 缺口 / 断点台账 ★ `[核心]`

| 编号 | 缺口 / 断点 | 严重度 | 证据（`path:line`） | 影响 |
|------|-------------|--------|----------------------|------|
| `NH-RA02-B01` | Execution.`s05_binding_digest` 创建时 = `domain_binding_digest`（列名盗用） | `S1 阻断` | `task_create.py:179-180,337-340`；`config_snapshots.py:254-263` | 所有自称 S05 的读方都在读政策 digest；`T-O-384` 无法落地 |
| `NH-RA02-B02` | `NOT NULL` + 零 UPDATE → 无未封闭合法状态、无选边后封闭 | `S1 阻断` | `001_initial.sql:245-246`；仅 `task_create.py:180` 与 `task_commands.py:306` 写入 | 无法表达「图已绑、工人未选」；与 `T-O-382` 时序互斥 |
| `NH-RA02-B03` | ProcessCommand 无独立 s05；`binding_digest` 仅 domain | `S1 阻断` | `models.py:13-29`；`runtime_core.py:888-917,357-358` | clean Process 不能证明绑后不换工人（`T-O-383`） |
| `NH-RA02-B04` | 不存在 actual binding seal 事务 | `S1 阻断` | 对比 `runtime_outcome.py:88-137` 有 Outcome CAS 但无 s05 写 | 晚绑定没有线性化点 |
| `NH-RA02-B05` | Snapshot/Candidate/scatter-child 复制 domain 别名进名为 s05 的列 | `S1 阻断` | `acceptance_snapshot.py:151`；`clean_preflight.py:395,498`；`scatter_intake.py:173,602-603` | 污染 S04 观察与 child Execution；acceptance 不能当 actual 证人 |
| `NH-RA02-B06` | handler 表外 `dispatch_clean` / strategy remap | `S1 阻断` | `clean_preflight.py:46-71,108-121`；对照 QNA Q4-B 已否 `:383-403` | 即使将来图多画 clean 边，handler 仍可暗调未声明 `process_key` 的策略 |
| `NH-RA02-B07` | **消费** `NH-RA03-B03`：evidence history 单值，digest 覆盖不了有限再获取链。本面只记 binding 后果 | `S1 阻断`（binding 侧） | `D-13`；`acquisition_ingest.py:579-593`；`clean_preflight.py:622-686`；表示权威在面 `03` | `T-O-388`「封闭覆盖实际走过的 acquire 路径」无材料 |
| `NH-RA02-B08` | 仓内 frozen 词汇/DDL 与 `T-O-384` 真实冲突（QNA 审查不完整） | `S1 阻断` | `spec-glossary.md:231`；`S05-intake-cleaning.md:229-230`；`D04-turso-physical-schema.md:622`；QNA `pre-initial-planning-qna.md:756,765` vs index §2.4 | 若不先登记冲突，规划会偷偷改语义或反向用旧 DDL 否决产品法 |
| `NH-RA02-B09` | Gate 传播机制正确、值错误 | `S2 重要` | `runtime_materialize.py:555-591` | human resume 会把伪 s05 编进 target digest |
| `NH-RA02-B10` | **消费** `NH-RA01-B01/B04`：图编译期单 clean 步骤、无选边事件可封。本面只记 seal 无输入 | `S2 重要`（binding 后果） | `lsrag_definition.py:111-118,881-926`；图权威在面 `01` | selected-route identity 归 01；seal 时刻归 02（`NH-C-09`/`NH-C-19`） |
| `NH-RA02-B11` | 无「真实选边后 digest 不随 retry 变」测试 | `S2 重要` | `tests/unit/test_dispatch_ddl.py:69` 等 12 处仅 INSERT 列名；无 digest 稳定性断言 | 改别名即可单元绿，集成假绿 |
| `NH-RA02-B12` | PublicationProof/Process 行不携带 actual s05 | `S3 次要` | `001_initial.sql:344-345,1532-1558` | 终态向量 proof 无法回溯工人；可经 Execution 间接读，一旦列撒谎则全链撒谎 |

---

## 5. 跨功能系统一致性 ★ `[核心]`

- **5.1 整体形态一句话**：一次 Intake Execution 先冻结 **policy**（哪张 immutable 图、哪份 config），在表示已知后于同一 revision 内选出 **actual** acquire/clean/preflight，一次封闭 digest，之后同 Execution 的 retry/recovery/human resume 只重放封闭值；换实现必须新 generation。
- **5.2 功能间一致性契约（不变量 `NH-C-10..19`）**：

| 编号 | 不变量 | 跨哪些面/模块 | 违反后果 |
|------|--------|----------------|----------|
| `NH-C-10` | policy binding ≠ actual S05 binding；禁止用 domain digest 冒充 s05 | `02` 拥有；`01/09` 消费 | 列名盗用复发（`NH-RA02-B01`） |
| `NH-C-11` | Execution 创建即绑 exact workflow revision/compiled digest（`S03-T017`）；actual digest 不得早于选边 Outcome | `01` 图；`02` seal 时刻 | 创建时锁工人 或 decode 后换 revision（Q4-C 已否） |
| `NH-C-12` | 未封闭 actual 必须有合法 durable 状态（具体形态 `G-NH-01`） | `02/09` | NULL 被 NOT NULL 堵住，只能写伪值 |
| `NH-C-13` | 封闭后 retry/recovery/human resume 不得重新 resolve active acquire/clean/preflight | `02/09`；S05-T025 | 热切工人，破坏 `T-O-383` |
| `NH-C-14` | 封闭 digest 覆盖 **实际走过的** acquire 路径 + 选中 clean（`T-O-388`） | `02` 拥有 digest；`03` 拥有 evidence 事实 | 单值 evidence 无法证明再获取 |
| `NH-C-15` | 进入 clean Process 的 command 必须能证明工人已封闭，否则 fail-loud | `02/04` | handler `dispatch_clean` 暗换 |
| `NH-C-16` | Snapshot/CandidateSet/Gate/child Execution 复制的必须是封闭后 actual，不得是 policy 别名 | `02/04/08` | S04/S05 证人链撒谎 |
| `NH-C-17` | 换 implementation/version → S02 causal restart 新 generation；同 version 异 digest fail-loud（`S05-T026`） | `02/01/09` | 旧 Task 被 registry 热切 |
| `NH-C-18` | handler 不得 dispatch 本 revision 未声明的 `process_key`（`T-O-384`） | `02/01/04` | Q4-B 回流 |
| `NH-C-19` | selected-route identity 由面 `01` 拥有；evidence 事实由面 `03` 拥有；本面只拥有 **何时封闭、如何重放** | `01/02/03` | 三面各发明一份 digest 公式 |

- **5.3 数据 / 控制流贯穿图**：
```text
Task.create
  ├─ fingerprint CAS（policy 身份）                    [HEAD ✅]
  ├─ ConfigSnapshot.prepare → domain_binding_digest    [HEAD ✅ policy]
  ├─ INSERT Execution
  │    workflow/revision/compiled/config NOT NULL      [HEAD ✅ S03-T017]
  │    s05_binding_digest := domain_binding_digest     [HEAD ⛔ 谎言]
  │    目标：s05 actual = UNSEALED                     [缺失 NH-N-02-01]
  └─ wake
       acquire Process ──► 单值 evidence               [D-13；面 03]
       decode Process ──► 单值 decode evidence         [D-13]
       （目标）登记 guard 选 clean 边                  [面 01；HEAD 无]
       clean Process
            ProcessCommand.binding_digest = domain     [HEAD ⛔ B03]
            handler map process_key → strategy         [HEAD ⛔ B06]
       seal CandidateSet（集合 seal，s05=domain 包一层）[HEAD 🔶]
       （目标）同 tx：route Outcome + actual s05 CAS    [G-NH-11]
       preflight / gate：复制 Execution.s05            [HEAD 传播✅ 值⛔]
       publication proof：无 s05 列                    [B12]

Retry/recovery 同 Execution ── 重放 process 行，不改 s05     [HEAD 部分]
Causal restart 新 generation ── 复制 previous 两列 digest   [HEAD 复制谎言]
```

- **5.4 邻面消费 / 提供**：
  - **消费面 01**：selected-route identity（哪条 route/guard 赢了）必须是 seal 输入。引用 `NH-RA01-B01`（selected-output merge 无法表达）与 `NH-RA01-B04`；本面 `NH-RA02-B10` 是该事实的 **binding 后果**，不另开图设计。冲突候选仍 OPEN：单 input binding（`D-10`）是否挡 merge（`G-NH-02`，面 01 主责）。
  - **消费面 03**：acquire/decode evidence 闭集与再获取链如何进入 digest。引用 `NH-RA03-B03`（evidence history / 无 reacquire 边）与 `NH-C-22/C-25`。`NH-RA02-B07`/`NH-C-14` 在 03 未 owner-freeze 前不得当已实现。
  - **提供给 04/08/09**：seal 合同、ProcessCommand 必须携带的 closed digest、三窗 replay 规范、防假绿最小窗。
  - **不提供**：图形状、representation 谓词字面、PDF 引擎、upload purpose。

---

## 6. 净新契约 / 架构边界草案 `[核心]`

> 无先例可借（§3 标 🆕）处，从零草拟。**草案，非冻结。不锁 DDL/列名/HTTP/purpose/step_key。**

- **6.1 净新聚合 / 解耦点**：
  | 缝 | ID | 为什么净新 |
  |----|-----|------------|
  | 两阶段 actual S05 状态机（unsealed → sealed once） | `NH-N-02-01` | Temporal/SFN 有 history 事件；本仓是七表+列 digest，无 event-sourced workflow。合法未封闭状态在 HEAD/legacy 都不存在 |
  | seal 输入闭集（digest 覆盖范围） | `NH-N-02-02` | S05 §3.10 列出 refs 种类，但未覆盖「晚绑定 + 有限再获取链」；D-13 单值不够 |
  | 三窗 replay 合同 | `NH-N-02-03` | HEAD 只有「永远已填」一窗；legacy restart 热切 branch |
  | ProcessCommand 对 actual 的可证明携带 | `NH-N-02-04` | 今日只有 domain；外部幂等 key 不规定 command schema |

- **6.2 净新契约叙述规格**（存在性，不锁物理列）：
  1. **Seal 输入闭集（最小，草案）**：selected route identity（面 01）；实际走过的 acquire 步骤/capability 与其 evidence digest 有序列表（面 03）；选中的 clean `process_key` + contract_version + strategy identity；preflight profile/validator 若本路径适用；`llm_required` 时 prompt 指针 digest（`T-O-386` 已把 promptA 范围钉在策略类，**字面不在此冻**）。禁止把整个 config snapshot 再哈希一次冒充 actual。
  2. **Digest 覆盖范围**：上述闭集的确定性聚合；必须随再获取链长度变化；封闭后同材料再算得同一值。
  3. **未封闭状态的存在性**：Execution 在选边前必须能被读成「policy 已冻、actual 未封」。具体用 nullable 列 / 显式 state / 双列 —— `G-NH-01`。
  4. **一次封闭**：同一 Execution generation 只允许 unsealed→sealed 成功一次；第二次写 = ConflictError。禁止用后一次选边覆盖。
  5. **Command**：clean 及之后的 ProcessCommand 必须携带（或能确定性指向）已封闭 actual；未封闭不得 materialize clean（或 materialize 后 fail-loud）。
  6. **传播**：CandidateSet/Snapshot/Gate target/child Execution 只复制 **封闭后** 值；未封闭不得假装 complete acceptance。

- **6.3 架构边界（与既有 / 相邻面）**：
  - 不改 S03 七表职责合并回 JSON（`S03-T009`）。
  - 不引入 Temporal/Cadence history store、不引入 `action_branch`、不引入第五 source kind。
  - 不在本面设计 representation 谓词（面 01/03）。
  - schema 演进必须显式 reopen D04「创建时 NOT NULL」句，而不是 AP 里悄悄改语义。

---

## 7. Substrate-fit / 技术路线过滤 ★ `[核心]`

| 借鉴点 | 原机制（参考处） | 是否冲突本仓路线 / 约束 | 落地形态（降级 / 重映射 / 直采） |
|--------|------------------|--------------------------|-----------------------------------|
| Task fingerprint / Execution policy freeze | HEAD `task_create.py` / DDL | 不冲突 | **直采** policy 账本 |
| Outcome 同 tx CAS | HEAD `runtime_outcome.py:88-137` | 不冲突 | **直采** 作为 seal 线性化点候选 |
| Gate 复制 digest | HEAD `runtime_materialize.py:555+` | 值错，机制不冲突 | **重 substrate**：换值，不换复制点 |
| Temporal Event History replay | Temporal docs | 冲突：event-sourced 云引擎、动态 worker、非七表 | **降级**：只保留「选择写入 durable 行后 resume 不重选」 |
| Cadence GetVersion marker | Cadence docs | 冲突：workflow 代码双路径 + marker event | **降级**：封闭 digest = 本仓「marker」；代码升级走新 generation 而非在同一 history 分叉 |
| AWS Choice + history | SFN docs | 冲突：ASL/AWS 控制面；自由 JSONPath | **降级**：声明式 Choice ↔ 已登记 guard；entered/exited ↔ route Outcome + seal；无 Default 失败 ↔ 未匹配 fail-loud |
| Stripe idempotency key | Stripe API | 不引入 Stripe；24h TTL 不适合 Execution | **重映射**：Task fingerprint / Process fence / seal CAS；并发 = typed ConflictError |
| Kafka EOS | Confluent/Kafka design | 冲突：broker 事务、跨 topic | **降级**：承认 at-least-once；用 CAS+幂等冒充 exactly-once 必须把失败窗写进测试，不得口头 EOS |
| legacy STEP_RESTART 意图 | `restarter.ts:850` | 队列/R2/SMCP 越界 | **部分借**意图枚举；**不借**栈与热切 definition |
| legacy `action_branch` | mapper/router | 明确禁（`T-O-377`/`D08-T004`） | **反例**，零回流 |

能跑但越界（CF/R2/SMCP/动态 plugin/自由表达式）→ 最多 `🔶部分借`。本面无「把 Temporal 当引擎」选项。

---

## 8. 反例坑表 + 净新表 `[核心]`

### 8.1 反例坑表 ⛔

| 反例 | 来源锚 | 为什么不可借 |
|------|--------|--------------|
| 用政策 digest 填 actual 列 | `task_create.py:180` | 列名盗用；验收会绿、产品法会假 |
| 创建时 NOT NULL 假装「已绑工人」 | DDL `:246`；glossary `:231` | 消灭未封闭窗 |
| handler `dispatch_clean` 当路由 | `clean_preflight.py:108`；QNA Q4-B | 表外策略，业主已否 |
| `action_branch` 热切 / 运行中换 branch | `mapper.ts:198`；`router.ts:42-59` | taxonomy 禁令；无 digest |
| Restarter 重读 active workflow JSON | `restarter.ts:478-483` | resume 换工人 |
| 队列成功再写库 | `restarter.ts:812-814` | 与本仓「commit 前不可执行 / 同 tx CAS」相反 |
| member catch skip 仍标成功 | dedicated `processor.ts:284-287` | 假绿；破坏 fail-loud |
| `plainTextAvailable: true` | `cleaner_web.ts:321` | 空正文当成功（`T-O-383`） |
| Temporal/Cadence 当运行时 | WEB | `T-O-42` 绿地；单体 FastAPI + local Turso |
| 口头 exactly-once | Kafka 官方警告 | at-least-once 下必须测崩溃窗 |
| 把 QNA「无实际冲突」当已修 schema | QNA `:756` | index §2.4 已标高估 |

### 8.2 净新表 🆕

| 项 | 为什么无先例 | 草案落点 |
|----|--------------|----------|
| 七表 Execution 上的两阶段 actual S05 状态 | 外部引擎用 event history；legacy 用可变 branch 字符串；HEAD 用伪 NOT NULL | `NH-N-02-01` / `G-NH-01` |
| 覆盖有限再获取链的 binding digest 公式 | S05 §3.10 假设单次 actual refs；D-13 单值 | `NH-N-02-02`；待面 03 evidence 闭集 |
| 封闭前/后/causal 三窗分测合同 | HEAD 无未封闭窗；外部 timeout 数字不可搬 | `NH-N-02-03` / §9 |
| ProcessCommand 对 sealed actual 的证明义务 | 今日无此字段 | `NH-N-02-04`（存在性，不锁字段名） |

---

## 9. 验收格栅草案（防假绿）`[核心]`

> 草案。落地验收归下游。必须区分 `单元 / 集成 / default-root e2e / retrieval-facet mega`。

| 功能 F | 收口目标（一句话可验证） | Test-ID（拟） | 测试层 | 防假绿要点 |
|--------|--------------------------|----------------|--------|------------|
| policy 冻结仍在 | 新 Execution 的 workflow/compiled/config/domain 在 create 后不变，retry 不 resolve active 图 | `NH-A-02-01` | 单元 + 集成 | 不得用 monkeypatch 换 `_assert_execution_binding` |
| 未封闭可表达 | 选边前读取 actual 得到「未封闭」合法态，而不是 domain 伪值 | `NH-A-02-02` | 集成 | 禁止把 NOT NULL 非空当已封闭 |
| 选边后一次封闭 | 选边 Outcome 提交后 actual digest 非空且 CAS 成功；第二次写冲突 | `NH-A-02-03` | 集成 | **单元改列别名 ≠ 本条**；必须有真实 route Outcome |
| digest 覆盖路径 | 两条不同已声明 acquire 路径 → 不同 digest；同路径重算相同 | `NH-A-02-04` | 集成 | 依赖面 03 evidence；单值 fixture 不算 |
| 封闭后 Process retry | 同 Execution retry 不改变 actual digest、不改变 clean `process_key` | `NH-A-02-05` | 集成 | 禁止只 assert process 行还在 |
| 封闭前 crash | 选择未写入时 resume 允许在已声明边上再选；写入后不允许 | `NH-A-02-06` | 集成 | 对照 WEB：timeout 在 completed 前 vs 后 |
| handler 禁暗调 | 图上不存在的 `process_key`/strategy 必须 fail-loud | `NH-A-02-07` | 单元 + 集成 | 现 `_clean` remap 必须被此条抓住 |
| Command 可证明 | clean ProcessCommand 能指出封闭 actual；未封闭不得成功 clean | `NH-A-02-08` | 集成 | 不得只检查 `binding_digest` 64 hex |
| 传播一致性 | Snapshot/Candidate/Gate/child 的 s05 列（或后继名）等于封闭值，不等于 domain | `NH-A-02-09` | 集成 | 今日 HEAD 会失败——这是特征不是 bug 隐瞒 |
| default-root e2e | 默认组合根真实选边后，digest 在 Process retry 前后相同；空 `clean_text` 失败；禁 503 当 DoD | `NH-A-02-10` | default-root e2e | 禁 monkeypatch browser/http；禁 fixture-only |
| causal restart | 新 generation 不热切旧 actual；升级路径显式 | `NH-A-02-11` | 集成 | 与同 Execution retry 分测 |
| retrieval mega | 本面不拥有；只要求 publication proof 能回溯封闭 binding | `NH-A-02-12` | retrieval-facet mega | 交面 08/09；本面列出义务 |

本面最小 failure/replay 窗（供面 09 汇总，不代替 09）：`NH-A-02-02,03,05,06,07,10`。

---

## 10. 优先级建造建议 + owner-gate 候选 `[核心]`

- **10.1 建造顺序（依赖序，分批不一次性深做）**：

| 顺序 | 工作簇 | 依赖 | 复用判定 |
|------|--------|------|----------|
| `P0-a` | 登记 truth-to-schema 冲突（glossary/S05/D04 vs `T-O-384`），停止在 AP 里当「已和解」 | QNA CITE；本面 §2.3 | `🆕净新`（文档/真相校准，非代码） |
| `P0-b` | 与面 01 对账 selected-route identity；与面 03 对账 evidence 链 | 邻面 analysis | 消费，不设计图 |
| `P0-c` | 两本账的存在性 + 一次 CAS seal（**列策略不锁**；形态交 `G-NH-01` 三选一） | `P0-a/b`；HEAD Outcome UoW | `♻️重 substrate` |
| `P0-d` | ProcessCommand/传播链改读封闭 actual；拆除 handler 表外 remap | `P0-c` | `♻️重 substrate` |
| `P0-e` | 三窗 replay 测试 + default-root e2e 消化不变式 | `P0-c/d` | `🆕净新` 测试合同 + `✅复用` fingerprint/CAS |
| `P1` | PublicationProof 回溯、scatter child 对齐 | `P0-d`；面 08 | `♻️重 substrate` |

- **10.2 owner-gate 候选（只 MARK 不裁决 → 上交 [[assessment-index]] §4 / 下游决策登记）**：

| gate-ID | 决策点 | 候选选项（不预设倾向） | 影响 |
|---------|--------|------------------------|------|
| `G-NH-01` | S05 两阶段 binding 的 schema/命名 | `保留 policy+新增 actual` / `nullable actual+sealed state` / `其他经证据支持方案`（含独立 binding 行） | Execution/Process/Snapshot/Gate/recovery；D04 reopen |
| `G-NH-11` | actual seal 与 selected-route Outcome 是否必须同事务 | `必须同 UoW` / `允许先 Outcome 再独立 seal CAS（需定义崩溃窗）` / `其他经证据支持的线性化点` | 崩溃在两提交之间会否重选工人；测试窗 `NH-A-02-06` |
| `G-NH-12` | Task causal restart 对 **已封闭 actual** 的继承 | `新 generation 清空 actual、允许按新表示再选（仍同 revision 政策）` / `复制封闭 actual、禁止再选` / `按 intent 分（retry vs rebuild）` | `S03-T018` × `S05-T026` × `T-O-388`；本面只 MARK |

`G-NH-02`（selected-output merge）/ `G-NH-09`（engine 是否留在 NH）由面 01 主责，本面只消费，不重复裁决。本面 `G-NH-11`（seal 同事务）与 `G-NH-12`（restart 继承）只 MARK、无推荐赢家；index §4 v0.2 已登记二者（仍不裁决）。**禁止**与面 08 reclean（`G-NH-19`）或他面自增 11 号共用 ID。

---

## 11. 核验记录 `[核心]`

> 对抗性自检：关键锚点是否真核验过；与叙事冲突处以实测为准并标「修正」。

| 锚点（host-ID） | 是否核验 | 方式（grep/read/run） | 备注 / 修正 |
|------------------|----------|------------------------|--------------|
| `RA-02-HEAD-01` fingerprint 双检 | `✅` | read `task_create.py:67-141` | 两段事务，非单检 |
| `RA-02-HEAD-09` s05=domain | `✅` | read `:179-180,:337-340`；run python 列写点 | 与 PROMPT 提示行一致，本次重读确认未漂移 |
| `D-12/D-13` | `✅` | 消费 index §2.2；抽读 DDL/acquisition_ingest/clean_preflight | **未另估** |
| `D-02-01..12` 本面分母 | `✅` | `uv run python` 计 ProcessCommand 字段、DDL 行、py 写点；`rg UPDATE` | HEAD `1221aa1` |
| `RA-02-HEAD-11` ProcessCommand | `✅` | read `models.py:13-29`；`runtime_core.py:888-917` | claim SELECT 无 `e.s05_binding_digest` |
| `RA-02-HEAD-14` dispatch_clean | `✅` | read `clean_preflight.py:28-121` | print_pdf 分支在 `:58-63` |
| Gate 传播 | `✅` | read `runtime_materialize.py:544-593` | 正例机制 / 反例值 |
| Outcome 同 tx | `✅` | read `runtime_outcome.py:62-137,145-182,287-368` | |
| Snapshot/Candidate/child | `✅` | read `acceptance_snapshot.py:137-157`；`clean_preflight.py:373-399`；`scatter_intake.py:159-173,577-618` | |
| 零 UPDATE s05 | `✅` | `rg UPDATE.*s05_binding_digest src` | 仅 INSERT 赋值 |
| PublicationProof 无 s05 | `✅` | read `001_initial.sql:1532-1558` | |
| 图工厂单 clean | `✅` | read `lsrag_definition.py:85-126,881-926` | |
| glossary/S05/S03/D04/D01 | `✅` | read 各 `path:line` | 冲突点名，不假装 QNA 已消 |
| QNA `T-O-382/383/384/388` §9.5.2 | `✅` | read QNA `:86-92,:756-765` | **修正**：不得写「QNA 已无冲突」 |
| `RA-02-LEGACY-01..06` | `✅` | grep + read mapper/restarter/router/dedicated processors/cleaner_web | 未 import/编译/运行 legacy |
| `RA-02-WEB-01..07` | `✅` | web_search + open_page 官方 URL | 访问日 `2026-08-29`；Stripe 博客被挡，改用 API Reference 官方页 |
| 邻面 01/03 文件 | `✅` | `list_dir` 2026-08-29 **已有** `assessment-analysis-01-*` 与 `03-*` | **收回**「文件不存在」；§5 改为消费 `NH-RA01-B01/B04`、`NH-RA03-B03` |
| index 所列 pytest 集合 | `未` | 未跑 | 集合偏 clean/API e2e，非本面 binding；避免用无关绿伪装。测试侧改为 `rg tests s05_binding_digest` |
| `T-P-NH-*` 当作已实现 | `✅` 拒绝 | 纪律 | 叙事/初判，非 HEAD 事实 |

**渠道事实核查记录**：

| ID | 渠道 | 结论原子句 | 来源与版本或访问日 | 正/反 | 置信 | substrate-fit | 命中 |
|----|------|------------|-------------------|-------|------|---------------|------|
| `RA-02-HEAD-01` | HEAD | 创建路径把 domain digest 写入 s05 列且无后续封闭 | `task_create.py:180` HEAD `1221aa1` | 反 | HEAD 实测 | ⛔反例 | `NH-RA02-B01` |
| `RA-02-HEAD-02` | HEAD | Task 指纹双检是可复用 policy 幂等 | `task_create.py:67-104` | 正 | HEAD 实测 | ✅借 | substrate |
| `RA-02-LEGACY-01` | LEGACY | dispatcher 分发写入 `action_branch`，无 immutable actual binding | `mapper.ts:195-200` | 反 | 仓内代码锚 | ⛔反例 | `NH-C-18` |
| `RA-02-LEGACY-02` | LEGACY | Restarter 区分 STEP_START/STEP_RESTART 但重读当前 workflow 定义 | `restarter.ts:802-850,478-483` | 正/反对 | 仓内代码锚 | 🔶部分借 | `NH-N-02-03` |
| `RA-02-WEB-01` | WEB | Temporal：选择写入 Event History 后 replay 不重做；Task 完成前 crash 则重跑决策 | docs.temporal.io 访问 `2026-08-29` | 正+限制 | 外部参考 | 🔶部分借 | `NH-A-02-06` |
| `RA-02-WEB-03` | WEB | Cadence `GetVersion` 首次记 marker，之后不可被 maxSupported 改变 | cadenceworkflow.io 访问 `2026-08-29` | 正+失败法 | 外部参考 | 🔶部分借 | `NH-C-13` |
| `RA-02-WEB-05` | WEB | SFN Choice 无匹配且无 Default → 转换错误；history 含 ChoiceStateEntered/Exited | AWS docs 访问 `2026-08-29` | 正+限制 | 外部参考 | 🔶部分借 | `NH-C-12` |
| `RA-02-WEB-06` | WEB | Kafka：默认 at-least-once；声称 exactly-once 必须读失败窗；Stripe 同 key 重放首次结果、并发不保存 | Confluent delivery-semantics + Stripe 官方 访问 `2026-08-29` | 正+限制 | 外部参考 | 🔶部分借 | `NH-A-02-03/05` |
| `RA-02-BASELINE-01` | BASELINE | glossary/`S05-T025`/`D04` 创建时 actual 与 `T-O-384` 晚封闭冲突仍在 | 各 baseline `path:line`；QNA `:756` | 反（冲突登记） | 仓内文档 < HEAD 实测 | 冲突显式登记 | `NH-RA02-B08` |

---

## 12. 收尾 Verdict 与交接 `[核心]`

- **本面裁定**：面 `02` 健康维持 `P0 / 🔴`。可复用的是 **policy 冻结 + fingerprint + Process fence + Outcome/route 同 UoW**；净新且阻断的是 **actual S05 两阶段状态、一次封闭、Command/传播证人、三窗 replay**。`s05_binding_digest = domain_binding_digest` 是谎言不是别名。QNA 与 S03-T017 的图时序可分账，但 **没有**消掉 glossary/S05/D04/DDL 创建时 actual 法——禁止再写「已无冲突」。
- **交接下游**：缺口台账（§4）→ 规划；净新契约（§6）→ 设计；owner-gate 候选（§10.2 `G-NH-01/11/12`，只 MARK）→ 决策登记；验收格栅（§9）→ 执行计划 / 面 09 汇总。
- **冻结前置**：① 面 01 selected-route 与面 03 evidence 闭集 **已引用**（本 v0.2）；② `G-NH-01`（及如需 `G-NH-11/12`）owner 裁决；③ 共享分母未变或 index 先修订；④ 本文不得在本轮标 `frozen`/`reviewed`。

---

## 附录 A · 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | `2026-08-29` | Grok analysis-fleet | 初稿（measure-first + 三渠道正反例 + 缺口台账 + 只 MARK 的 owner-gate）；状态 `draft` |
| v0.2 | `2026-08-29` | Grok fix-fleet | 吸收已核实 review：R4-I03 收回「无 01/03 文件」并消费 `NH-RA01-B01/B04`、`NH-RA03-B03`；R4-I08 附录占位 `RA-FF-CHANNEL-*` 换成 `RA-02-*`；R4-I09 P0-c 删除「policy 列保持」。状态仍 `draft` |
