# new-harvest pre-charter Q&A · singular（单轮一次性业主决策册）

> **范围（scope）**：一次性关闭 [`proposed-planning.md`](proposed-planning.md) §8 的全部 18 个 canonical owner-gate，使 `planning-final` 能冻结 chosen branch、`AP-NH1` stop/reopen law 与后续 `AP-NH2..NH9` 的可施工合同。
> **qna 位点**：`pre-charter`（charter / planning-final 前关 execution gate）
> **角色配置（自填）**：提问 `GPT` · second-opinion `Grok` · 裁决 `owner`
> **second-opinion 模式**：`present`（Grok 已于 `2026-08-29` 填完 Q10–Q27 三槽；文本是 second opinion，不是 owner truth。GPT/owner 不得改写这些槽后冒充 Grok）
> **Q 编号**：续接 [`pre-initial-planning-qna.md`](pre-initial-planning-qna.md) 的 `Q1–Q9`，本册使用 `Q10–Q27`；稳定 append，不回收。
> **Truth-ID 冻结**：续接 foundational `T-O-376..389`；Q10–Q27 的 owner 回答已依序冻结为 execution truth `T-O-390..407`，append-only、不回收。
> **上游输入**：[`proposed-planning.md`](proposed-planning.md) v0.1 draft；[`assessment-index.md`](assessment-index.md) v0.2；[`reference-anchor/`](reference-anchor/) 九面分析；HEAD `1221aa1`。
> **下游消费者**：`planning-final` §2/§6/§7；new-harvest charter；`AP-NH1..AP-NH9` action-plan；S05/D04/glossary append-only truth repair。
> **文档状态**：`frozen`（Q10–Q27 全量回答；无 OPEN owner-gate；Truth-Gate `T-O-390..407` 已登记）
> **文档版本**：`v1.0 / 2026-08-29`（owner 整包接受 GPT v0.3 post-second-opinion 最终推荐；Grok v0.2 原槽保留为独立意见）
> **Owner 冻结授权**：业主确认接受 Q10–Q27 的全部 GPT v0.3 最终推荐；本文件据此填写逐题答案并冻结 execution truth。若未来推翻，只能 append 修订，不得在 planning/action-plan 静默改口。

---

## 1. Workflow、actual binding 与 durable representation 主干

### Q10 — policy / actual S05 的长期 schema 与旧行解释（gate：`G-NH-01`；来源：proposed §8、RA02）

- **影响范围**：S05/D04/glossary truth；Execution DDL；Task create；ProcessCommand；CandidateSet/Snapshot/Gate/scatter child；recovery/compat；`M-NH-01`；`AP-NH1/NH3/NH8/NH9`。
- **为什么必须确认**：HEAD 在 Task 创建时把 `domain_binding_digest` 写入名为 `s05_binding_digest` 的 NOT NULL 列，且没有 actual seal UPDATE（`src/runtime/task/task_create.py:179-180`; `src/persistence/migrations/001_initial.sql:245-246`; `NH-RA02-B01..B04`）。QNA `T-O-384/388` 又要求选边后才封闭实际路径。若不先定义旧列、旧行和 unsealed 的法律身份，migration 只能靠改名或填假 hash 冒充完成。
- **当前建议 / 倾向**（`GPT` · post-second-opinion）：保留 `domain_binding_digest` 作为 policy ledger；在 Execution 上新增明确命名的 nullable `actual_binding_digest` + `actual_binding_state/seal_generation`。旧物理列必须立即从新 domain model、command、Snapshot/CandidateSet/Gate/child projection 中逻辑隔离，repository 只以 `legacy_policy_alias_digest / actual_unverifiable` 暴露；若 migration/compat 证明安全再物理 rename/retire，绝不原地翻义或用 domain hash backfill actual。明细只住 typed history，Execution 新 actual 是一次 CAS 封闭的唯一快速 SSOT。
- **Reasoning**：
  1. 原地把旧 NOT NULL 列“改解释”为 actual，会让旧 domain hash 与新 actual hash 在形状上不可区分，任何 traceback 都可能假绿。
  2. actual digest 放在 Execution 可直接复用现有 Process/Gate/Snapshot 的传播和 CAS 关系；路径明细另存 history，避免把可变 JSON 再当 SSOT。
  3. nullable actual + explicit state 能诚实表达“图/policy 已冻、工人尚未选”；这正是当前 schema 消失的窗口。
  4. 该方案是 forward-only：旧行不伪造 backfill，永久保持 `actual-unverifiable`；未来独立新 ingest 可产生自己的 actual，但不得声称重建了旧 Execution 的历史 actual。

- **`Grok` 的问题分解**：
  1. 本题要拆开的不是「多一个 hash 列」，而是两本法律身份：`domain_binding_digest` 已是创建时冻结的 **policy/envelope**（`001_initial.sql:245`；`config_snapshots.py:254-263`）；QNA `T-O-384/388` 要的 **actual** 是选边后才存在的 acquire 路径 + 选中 clean/preflight。HEAD 把后者的名字写在前者的值上。
  2. 实测盗用点不只有 Task create：`s05_binding_digest=(prepared.domain_binding_digest …)`（`task_create.py:179-180`）；DDL `NOT NULL`（`001_initial.sql:246`）；`rg UPDATE.*s05_binding_digest src` 为零。ProcessCommand 只读 `binding_digest ← domain_binding_digest`（`runtime_core.py:888-917`）。Snapshot / CandidateSet / Gate / scatter child 继续复制这个伪值（面 02 `D-02-04..09`）。
  3. 因此必须同时回答三件事：旧行如何标记为 **actual-unverifiable**；未选边如何 **合法 unsealed**（今日非空伪值堵住 NULL）；下游唯一 actual SSOT 是哪一列/哪一行，而不是「名为 s05 的任意 64-hex」。
  4. 路径明细不能再塞进 Process `payload_extra` 或单槽 `acquisition_evidence`（`acquisition_ingest.py:89,660`）；actual digest 只能聚合 **已持久化、有序** 的 history，否则 crash replay 无法重算同一 digest。
- **`Grok` 对 `GPT` 推荐线路的分析**：
  - **主线路正确**：保留 `domain_binding_digest` 作 policy；新增明确命名的 nullable actual + 显式 seal state；禁止把旧 NOT NULL 列原地改解释。这正是面 02 候选 C 的表达力，也是唯一能同时满足「图已冻、工人未选」和「旧行不伪造 backfill」的形状。
  - **GPT 低估的脚枪**：继续把物理列叫 `s05_binding_digest`、只靠「新代码不要读它」是社会契约。该名字会被 grep、fixture、Gate 传播当成 actual（`runtime_materialize.py:555-591`；`task_commands.py:306` 已整行复制）。与 `domain` 同形的 64-hex 无法在 traceback 中区分（`FG-NH-08`）。
  - **范围必须扩到 Execution 以外**：CandidateSet 的 `s05_binding_digest` 今日是 `stable_digest({"binding": domain})`；Snapshot 可空但写入的仍是 `command.binding_digest`。若只改 Execution，传播链仍会把伪值送进 proof。
  - **不接受的替代**：把现列改 nullable 并「从现在起当 actual」——旧行的 domain hash 会瞬间变成假封闭。独立 binding 表可以做明细，但不能让 Execution 失去一次 CAS 的快速传播点（Outcome 已在同 UoW，`runtime_outcome.py:88-137`）。
- **`Grok` 的最终建议**：
  **接受 GPT 主线路，并收紧三条执行条件。** ① 物理 **重命名或隔离** 旧 `mkb_executions.s05_binding_digest`（例如只经 compatibility 映射读成 `legacy_s05_alias_digest`），新列用不会被误读的名字（`actual_binding_digest` + `actual_binding_state`/`seal_generation`）。② 旧行一律 `legacy-policy-alias / actual-unverifiable`，禁止用 domain hash backfill actual。③ Snapshot/CandidateSet/Gate/scatter child **未封复制 unsealed，已封只复制 actual**；路径明细只引用 typed history UUID/digest。下游唯一 actual SSOT = Execution 上一次 CAS 封闭的 actual digest；明细行不得成为第二 SSOT。此建议仍不是 Truth。

- **问题**：是否确认采用“policy 与 actual 分账；旧 `s05_binding_digest` 从新 domain/wire/传播链逻辑隔离且不 backfill actual；Execution 新 actual unsealed→sealed-once 为唯一快速 SSOT；typed history 只供明细”的 schema 法？物理 rename 可由 migration 在兼容证明后执行。如不确认，请同时给出旧行判真、unsealed 表达和唯一 actual SSOT。
- **业主回答**：🔒 **FROZEN**：确认 policy/actual 分账；旧 `s05_binding_digest` 从新 domain/wire/传播链逻辑隔离且不得 backfill actual；Execution 新 `actual_binding_digest/state/seal_generation` 是 unsealed→sealed-once 唯一快速 SSOT，typed history 只供明细；物理 rename/retire 在兼容证明后执行。→ `T-O-390`

### Q11 — selected-output 如何在七表内汇合（gate：`G-NH-02`；来源：proposed §8、RA01）

- **影响范围**：WorkflowDefinition/DDL/runtime materialization；kind graph；seal 前 candidate convergence；old revision compatibility；`M-NH-03`；`AP-NH1/NH2/NH3/NH9`。
- **为什么必须确认**：当前每个 target input port 只能有一条 binding，runtime 也只有 human-review/scatter-join 两种 CONTROL（`src/contracts/workflow/models.py:496-497`; `src/runtime/workflow/runtime_materialize.py:505-514`; `NH-RA01-B01`）。不回答汇合法，多个已声明 clean 分支只能复制整条 publication tail、用 handler if 暗调，或改变 binding algebra；三者影响完全不同。
- **当前建议 / 倾向**（`GPT` · post-second-opinion）：新增 registered `selected-output` merge CONTROL：candidate 绑定不同且 `required=False` 的显式端口；CONTROL 只投影同 revision **已持久化**的 route/selection proof，不重跑 guard、不等待未 materialize 分支、不复用 scatter fan-in；只输出一个 canonical candidate，再以现有单 binding 接 seal。v1 为 exactly-one：零命中失败（仅登记版本可声明 fallback），双命中完整性失败；CONTROL semantics/version 进入 compiled digest。
- **Reasoning**：
  1. 该形态保留“单 target input / 单 binding”的已有 DDL 围栏，不需要让任意 port 接多 source，也不会打开自由表达式。
  2. 多 candidate 进不同端口、单 canonical output，能让 publication tail 只存在一份；避免回到 13 张 profile 的整图复制。
  3. registered CONTROL 已是现引擎受控扩展点；新增一种有版本语义的 control，比在 handler 中 if/try-all 更可编译、可 replay、可 compat。
  4. exactly-one 的零/双命中失败法可直接形成 integration tests；不会用“任选一个”掩盖 guard 冲突。

- **`Grok` 的问题分解**：
  1. 目标法是 `T-O-384/387`：同一 immutable revision 预声明多条 acquire/decode/clean 边，选边后并入 **一份** publication tail。HEAD 做不到：编译器 `each workflow input port may have only one binding`（`models.py:496-497`）+ DDL `ux_workflow_binding_slot`；runtime CONTROL 只有 `scatter_children_join` 与 `human_review_gate`（`runtime_materialize.py:505-514`）。
  2. 未使用的 `WorkflowStepKind.JOIN` / `WorkflowJoinMode.ALL_REQUIRED|ALL_TERMINAL`（`models.py:32-67`）是 **AND fan-in**，不是 XOR 选输出。Airflow `all_success` 级联 skip 已是面 01 反例。
  3. 未选中的 candidate PROCESS **根本不会被 materialize**。任何「等所有 candidate 到达再选」的 join 都会在未走边上死等。human_review 只证明登记 CONTROL 可扩展，不证明多 clean 汇合（`T-R-NH-02`）。
  4. 因此原语必须同时满足：保持单 port 单 binding；不复制 13 张 tail；`eq`-only 无自由表达式；选边结果进 compiled digest / replay；旧 pin 仍跑旧图。
- **`Grok` 对 `GPT` 推荐线路的分析**：
  - **赞成 registered merge CONTROL**：多 candidate 绑到 CONTROL 上 **不同、显式命名** 的 input port，CONTROL 只输出一个 canonical port，下游 seal/tail 仍一条 binding。这是七表上唯一不破坏 unique 约束、也不打开 CWL `pickValue` 表达式的缝。
  - **必须反对把 scatter_join 当模板**：`runtime_scatter.py:76-98` 的零成员 SUCCESS 和 children wait 是成员集合 fan-in。选中输出是 XOR projection。照搬 wait/ALL_REQUIRED 会让未选中的 `pdf.ocr` 边永远不来。
  - **exactly-one 失败法正确**：零命中 fail-loud（除非该 CONTROL **版本** 显式登记 fallback port）；双命中完整性失败。禁止「任选一个」和 SFN `Default` 式自由缺省。
  - **GPT 未写清的运行时形状**：candidate 端口在图上必须 `required=False`（`WorkflowPortDefinition.required`，`models.py:118`），否则未选中边在编译期就「缺 binding」。CONTROL 运行时只读 **已提交的 route/selection proof**，禁止再跑一遍 guard（否则 W-NH-SEL 会重选）。
  - **不选 one-of binding**：要改编译器+DDL unique，等于重开 binding algebra，NH1 spike 面更大。不选整图复制：直接违反 kind 家族与 `FG-NH-09`。
- **`Grok` 的最终建议**：
  **确认 v1 原语 = 新注册 `selected-output` merge CONTROL，失败法 exactly-one。** 附加执行围栏：CONTROL 是 **已持久化 selection 的投影** 不是第二决策器；候选端口可选、未 materialize = absent；**禁止**复用 `scatter_children_join` 等待语义；CONTROL semantics/version 进入 compiled digest；fallback 只能是该 CONTROL 的登记版本而不能是表达式 Default。NH1-04 spike 必须覆盖零/双命中、缺 fact、环、未知 predicate。此建议仍不是 Truth。

- **问题**：是否确认 v1 使用 registered selected-output merge CONTROL，候选端口 optional，CONTROL 只投影 durable selection、不重跑 guard/不等待未 materialize 分支，并冻结 exactly-one、零/双命中失败法？如不确认，请说明替代原语如何无表达式、无整尾复制、可 replay/compat。
- **业主回答**：🔒 **FROZEN**：v1 使用 registered `selected-output` merge CONTROL；候选端口 optional，CONTROL 只投影 durable selection，不重跑 guard、不等待未 materialize 分支、不复用 scatter fan-in；exactly-one，零/双命中 fail-loud，登记 fallback 例外进入 compiled digest。→ `T-O-391`

### Q12 — representation fact / acquire-decode history 的 durable authority（gate：`G-NH-03`；来源：proposed §8、RA01/03）

- **影响范围**：acquire/decode state；route guard context；actual S05 digest；retry/recovery；representation audit；`M-NH-02`；`AP-NH1/NH2/NH3/NH6/NH9`。
- **为什么必须确认**：HEAD 只有被覆盖的单份 `acquisition_evidence` / `decode_evidence`，representation-aware guard 为 0（`src/runtime/intake/acquisition_ingest.py:89,660`; `src/runtime/workflow/runtime_materialize.py:101-117`; `NH-RA03-B03/B04`）。若 guard 读 handler 内存或 opaque output dict，恢复时无法证明当时看到了什么，也无法 digest 两次已声明 acquire 的真实顺序。
- **当前建议 / 倾向**（`GPT` · post-second-opinion）：建立正式 typed、append-only 的 `RepresentationFact + AcquireDecodeHistory` durable rows，按 Execution/step/ordinal 定位；每条 fact/history append 与对应 acquire/decode Process Outcome **同一 UoW**，同 step 第二次成功拒绝。Process outcome/Snapshot 只引用 fact UUID/digest；route context 由注册 projection 生成，未知/缺字段 fail-closed；actual S05 聚合有序 history digest，不 hash 任意 JSON/S13 manifest。
- **Reasoning**：
  1. 正式行让 guard、seal、debug、compat 都读同一个 durable authority；避免 runtime state、Process payload、Snapshot 各发明一套字段。
  2. append-only ordinal 能证明有限正向再获取的路径顺序，并阻止同 step 第二次成功被覆盖。
  3. typed/versioned schema 可把 media、text-layer、opaque、print/profile 等字段纳入闭集；未知字段不会被自由表达式消费。
  4. Process output 保留 reference 而不是复制事实，既能沿用 Outcome 关系，也不会让 output JSON 变成第二 SSOT。

- **`Grok` 的问题分解**：
  1. 选边、actual digest、static→browser、print 诚实性全部依赖「当时看见了什么」。HEAD 只有会被覆盖的单份 `acquisition_evidence` / `decode_evidence`（`acquisition_ingest.py:89,660`），声明式 reacquire 边 = 0，representation-aware guard = 0（`models.py:249-255`；`runtime_materialize.py:101-117`）。
  2. 现成正例是 `_typed_route_context_tx`：guard 已经从 **durable Task / CandidateSet / transition** 投影，缺键 fail-closed（`runtime_materialize.py:101-117,119-168`）。反例是 handler 内存、`payload_extra`、常量 `injected-browser-renderer.v1`（`acquisition_ingest.py:535-536`）。
  3. decode 今日用 `CLEAN_OCR_CAPABILITY_UNAVAILABLE` 冒充无文本层（`types.py:154-159`），`representation_kind` 从不写 `print_pdf`。fact schema 必须把「观察」和「能力未部署」分码，否则 history digest 会把供给缺口写进表示。
  4. actual S05（Q10）只能 hash **有序 history**，不能 hash 任意 JSON blob。
- **`Grok` 对 `GPT` 推荐线路的分析**：
  - **赞成 typed append-only `RepresentationFact + AcquireDecodeHistory` 行**：按 Execution/step/ordinal；每步至多一条成功；Process outcome 只引用 UUID/digest。这是唯一能同时服务 guard、seal、debug、compat 的权威。
  - **赞成注册 projection + 未知/缺字段 fail-closed**：直接扩展 `_typed_route_context_tx` 的模式，新增 representation predicate 仍 `eq` only。不要给 guard 一个「读 output JSON」的后门。
  - **赞成 actual 聚合有序 history digest**：与 `T-O-388`「有限正向再获取」同构。
  - **风险**：若把 fact 做成 S13 artifact 字节，guard 每次解析 JSON，schema 漂移不可编译。正式表 + 版本化闭集字段优于通用 blob。也不要把 acquire Process 的 output manifest 当第二 SSOT。
- **`Grok` 的最终建议**：
  **确认 GPT 方案。** 唯一权威 = 正式 typed durable rows；Process output / Snapshot 只存引用；guard 只读登记 projection；缺键/未知字段 fail-closed；同 step 第二次成功禁止覆盖。实现上把 history append 放进 **该 acquire/decode Process 的 Outcome UoW**（已有 artifact commit 线性化，`runtime_outcome.py:88-92`），而不是事后补写。此建议仍不是 Truth。

- **问题**：是否确认正式 typed fact/history rows 为唯一权威，并与各 acquire/decode Process Outcome 同 UoW append；Process/Snapshot 只引用、guard 只读注册 projection、同 step第二次成功拒绝？如不确认，请说明另一权威如何支持 crash replay、path digest和缺键 fail-closed。
- **业主回答**：🔒 **FROZEN**：正式 typed append-only RepresentationFact/AcquireDecodeHistory rows 为唯一权威；与对应 Process Outcome 同 UoW append，同 step 第二次成功拒绝；Process/Snapshot 只引用，guard 只读注册 projection，actual digest 聚合有序 history。→ `T-O-392`

### Q13 — PDF/browser/OCR/Vision 与 S11 inference boundary 如何分工（gate：`G-NH-04`；来源：proposed §8、RA03/04/05）

- **影响范围**：S11 contracts/adapters/pools；intake ports；PDF parser；browser render/print；OCR；Vision/document-understanding；default root/readiness；`AP-NH1/NH3/NH6/NH7/NH9`。
- **为什么必须确认**：`GenerateRequest` 只有 `input_text`，Claude CLI 明确拒 binary；默认组合根也没有 browser/clean_llm（`src/contracts/inference/models.py:96-108`; `src/runtime/inference/claude_cli.py:505-508`; `api/app.py:330-345`; `NH-RA05-B01..B04`）。把所有能力都称作“复用已有推理面”会把 parser/browser 与 model inference 混成一个万能 blob invoke。
- **当前建议 / 倾向**（`GPT` · post-second-opinion）：按“是否需要 PromptRef + model identity + inference budget”分层，而不按能力名称粗分：无 prompt 的 PDF parse/browser render+print/确定性 OCR 走独立 local capability ports；Vision、DU 及任何 model-bound OCR 走扩展后的 S11 multimodal request（PromptRef、media type、digest、S13 handle/受控 bytes）。两类可复用 SupplyFence/ConcurrencyGate/health 聚合器，但 identity/limit/readiness 分账；CLI 保持 binary fail-closed，pool 个数本题不锁。
- **Reasoning**：
  1. parser 与 browser 的主要职责是表示获取/观察，不是生成文本模型；塞入 S11 会模糊 egress、sandbox 和错误码。
  2. Vision/DU 确实需要模型 binding、prompt identity、模型 readiness 和推理预算，留在 S11 能复用现有 inference governance。
  3. 显式 multimodal request 解决 text-only 事实；禁止 `payload_extra`/base64 text 偷运大对象，保留 digest/handle 血统。
  4. 调度池数量不应替代接口裁决：不同 capability 可共享 gate 实现，但必须有独立 identity、limit 与指标。

- **`Grok` 的问题分解**：
  1. `T-P-NH-6`「复用现有推理面即可」已被请求协议证伪：`GenerateRequest` 只有 `input_text`（`inference/models.py:96-108`）；Claude CLI 拒 binary（`claude_cli.py:505-508`）；默认组合根未注入 `browser_fetcher`/`clean_llm`（`api/app.py:330-345`）；生产依赖无 PDF/browser/OCR（`pyproject.toml:13-21`）。
  2. 现成正例是端口分离：`IntakeCoreMixin` 把 http/browser/clean_llm 分成三个注入点，并禁止 browser 回落到 static fetcher（`core.py:39-75`）。调度池、ConcurrencyGate、EgressPolicy、SupplyFence 可复用 **治理实现**，不证明 **同一契约身份**。
  3. 能力不是一类东西：PDF text-layer / Chromium print / 确定性 OCR 是本地变换；Vision / document-understanding 需要 PromptRef、模型 binding、推理预算（`T-O-386` promptA 仅 LLM）。用「OCR」一词不能决定归属。
  4. readiness 今日只探模型名单（`health.py:16-25`）。`inference_binding` 绿不能当 parser/browser 在场。
- **`Grok` 对 `GPT` 推荐线路的分析**：
  - **赞成分层边界**：parser/browser/确定性 OCR = 独立 local capability adapter；Vision/DU = 扩展后的 S11 multimodal request。`intake/` 只调 typed ports。这保住 S11 的 egress/sandbox/错误码，也保住 LLM 策略的 PromptRef 血统。
  - **赞成禁止 `payload_extra`/base64 偷运**：bytes 走 S13 handle 或受控 digest+bytes。CLI 继续诚实拒 binary，除非另开明确合同。
  - **赞成「共享 gate 实现 ≠ 合并身份」**：`NH-C-49`。不增第四个池名仍 OPEN，但不能拿它当「不改 GenerateRequest」的借口。
  - **需收紧分类准则**：凡需要 PromptRef + model identity + inference budget 的走 S11；凡是无 prompt 的本地 binary 变换走 capability port。`pdf.ocr`/`doc.ocr` 按这个准则落点，而不是预先把「OCR」整词塞进 parser 桶。库名不在本题冻结。
- **`Grok` 的最终建议**：
  **确认 GPT 边界。** parser/browser/print/确定性 OCR：独立 local ports，可复用 SupplyFence/ConcurrencyGate/health **聚合器**，但必须有独立 identity、limit、负样本 probe。Vision/DU：显式 S11 multimodal request（PromptRef + media type + digest/handle）。禁止把 PDF 解析伪装成 `GenerateRequest`。本题不锁库、不锁池个数。此建议仍不是 Truth。

- **问题**：是否确认以“需要 PromptRef+model budget”作为边界：无 prompt 的 parser/browser/确定性 OCR 走独立 local ports，model-bound OCR/Vision/DU 走 S11 multimodal request；共享治理但 identity/limit/readiness 分账，pool 个数不在本题锁？如不确认，请逐能力明确 contract、binary、budget/readiness。
- **业主回答**：🔒 **FROZEN**：以 PromptRef+model identity+inference budget 划边界；无 prompt 的 parser/browser/确定性 OCR 走独立 local ports，model-bound OCR/Vision/DU 走 S11 multimodal request；共享治理但 identity/limit/readiness 分账，CLI binary fail-closed，pool 数量不在本 Truth 锁定。→ `T-O-393`

---
## 2. 语义权威、公共对象边界与零集合终态

### Q14 — 非 API 五维权威、冲突合并与 `unknown` 法（gate：`G-NH-05`；来源：proposed §8、RA07/08）

- **影响范围**：public ingest descriptor；S04 revision semantics；acceptance eligibility；S06 context overlay；retrieval facets；metadata update；`AP-NH5/NH7/NH8/NH9`。
- **为什么必须确认**：registered_api 已能按 operation 派生严格五维+tags 六元组，但 inline/local/http 没有 caller 字段或派生器，仍以 `{"source_kind":...}` stub complete（`src/contracts/intake/semantics.py:12-63`; `src/runtime/intake/acceptance_snapshot.py:589-615`; `NH-RA07-B01/B02`）；现 API mapper 还存在缺值自动写 `unknown` 的习惯。不同 kind 不可能由同一 URL 规则完整推导 realm/type/channel/source_name；若 `unknown` 自动填充，“六键齐全”仍是假完成。
- **当前建议 / 倾向**（`GPT` · post-second-opinion）：v1 采用更严格的字段级 merge：generic inline/local/http 的 `realm/type/channel/source_name` 由 caller 必填、非空且不得为 `unknown`，`is_active` 由注册系统规则派生；其它登记 deterministic derivation 只能写其明确拥有字段，冲突 422，逐字段 provenance。registered_api 继续以 operation mapper 为 SSOT，caller 若重复提交必须逐字段相等；禁止任何 `or "unknown"` 自动填空。`unknown` 仅可用于 registry 明列的 API 可选字段，且必须是 frozen record 中的显式字面。
- **Reasoning**：
  1. caller-only 会迫使 API/可确定来源重复填值；derive-only 又无法从任意文件/URL可靠得到业务 realm，merge 才能按 kind 分责。
  2. 字段级 provenance 让 metadata update、S06 overlay 与 facet 能解释值来自哪里，并能在规则升级时决定是否新 Revision。
  3. 冲突 fail-loud 避免 caller 标签与 registry 派生悄悄覆盖；这符合现有 extra-forbid/unknown-key 围栏。
  4. v1 先以严格拒绝修复现有 stub/自动填空债：generic source 不接受 sentinel；API 也只有 operation registry 声明且 frozen record 显式携带时才合法，避免把 `unknown` 换皮成“字段齐全”。

- **`Grok` 的问题分解**：
  1. FilterMeta 五维是 `realm/type/channel/source_name/is_active`（`semantics.py:12-19`），加上 `context_tags` 共六元组。`T-O-389` 要求四通道强制进 S04、不进 g0。HEAD：registered_api 能写六键；inline/local/http 的公开 descriptor **没有** FilterMeta 字段（`api/models.py:107-128`），acceptance 用 `{"source_kind":...}` stub 仍可 complete（`acceptance_snapshot.py:589-615`）。
  2. 不同 kind 不可能共用一套 URL 派生器得到 realm。API 侧已是 operation 闭集派生，但 mapper 会把缺字段填 `"unknown"`（`intake/api/providers/chinatax.py:33-34`；`realestate.py:105`；`domain.py:52`）。
  3. S06 今日不读 Revision semantics（`generation_construct.py:330-343`；assemble 只保证 g0.body=clean）。五维权威一旦允许自动 `unknown`，「六键齐全」会变成假完成（`FG-NH-07`）。
  4. 冲突优先级、provenance、是否新 Revision，直接决定 metadata update 的指纹（面 07 `NH-C-66`）。
- **`Grok` 对 `GPT` 推荐线路的分析**：
  - **赞成字段级 merge**：API 继续 mapper 权威派生；generic 三 kind 对不可安全派生的字段 caller 必填；仅登记的 deterministic derivation 可填其拥有字段。caller-only 强迫 API 重复填；derive-only 会从 URL 伪造 realm。
  - **赞成冲突 fail-loud + 逐字段 provenance**：符合 extra-forbid / unknown-key 围栏；metadata 升级时能决定哪一字段变化触发新 Revision。
  - **对 `unknown` 比 GPT 更紧**：GPT 允许「registry 显式允许的 kind/field 可提交」。对 **inline/local/http 的必填五维**，`unknown` 不应作为缺省，也不应作为 caller 偷懒字面——否则 stub 换皮。对 **registered_api**，只有 operation schema 把某可选业务字段列为合法枚举（含 `unknown`），且该字面来自 **冻结 records 的显式值** 而非 mapper 填空，才可写入。禁止 `or "unknown"` 自动填充继续扩张。
- **`Grok` 的最终建议**：
  **确认 merge + 冲突 fail-loud + 逐字段 provenance；默认禁止自动 `unknown`。** 执行解释：generic 三 kind 的 `realm/type/channel/source_name` caller 必填、非空、非 `unknown`；`is_active` 系统可派生。API 保持 mapper SSOT，caller 若重复提交必须逐字段相等否则 422。`unknown` 只允许出现在 registry 列出的 API 可选字段，且必须是冻结记录里的显式字面。此建议仍不是 Truth。

- **问题**：是否确认 v1：generic 三 kind 的 `realm/type/channel/source_name` caller必填且非 `unknown`，`is_active`系统派生；registered_api mapper权威、重复caller值须相等；冲突422、逐字段provenance、禁止自动填 `unknown`，仅 registry列出的API可选字段可从 frozen record显式携带？
- **业主回答**：🔒 **FROZEN**：generic inline/local/http 的 `realm/type/channel/source_name` caller 必填、非空、非 `unknown`，`is_active` 系统派生；registered_api mapper 为 SSOT，重复 caller 值须相等；冲突 422、逐字段 provenance、禁止自动填 `unknown`，仅 registry 明列的 API 可选字段可从 frozen record 显式携带。→ `T-O-394`

### Q15 — semantic channel 与 vector channel 的公开命名（gate：`G-NH-06`；来源：proposed §8、RA07/08/09）

- **影响范围**：retrieval request/response；FilterMeta schema；`mkb_vector_records.channel`；facet rows/index；API compatibility；`M-NH-06/08`；`AP-NH5/NH7/NH8/NH9`。
- **为什么必须确认**：当前 public retrieval 的 `channel` 表示 `original|summary`，而 frozen FilterMeta 也有业务 `channel`（`src/services/retrieval/models.py:14-34`; `src/services/retrieval/retrieval_request.py:354-355`; `NH-RA07-B04`）。扩 facet 时若继续用同名，`channel=sold` 与 `channel=summary` 无法同时表达，也无法判断旧请求语义。
- **当前建议 / 倾向**（`GPT` · post-second-opinion）：新 public contract 只使用 `semantic_channel`（FilterMeta.channel）与 `vector_channel`（`original|summary`），内部 vector column 可暂留物理名 `channel`。兼容只发生在**旧 request schema/version**：旧 `channel` 按其既有闭集机械翻译为 `vector_channel`，仅允许 `original|summary` 并发弃用信号；其它值 422。新 schema 禁止旧 `channel`，绝不在同一 schema 内根据 value 猜轴。
- **Reasoning**：
  1. 两个业务概念必须能在同一请求同时出现；分名是最小且可测试的 contract surface。
  2. 先分 public semantic、暂不强制重命名内部列，可以降低 DDL/历史数据迁移范围，但不会继续向调用方暴露歧义。
  3. 新 schema 中按 value 猜语义会让业务 channel 恰好叫 `summary` 时失真；旧 schema 的 `channel` 本来就是严格 vector enum，按 schema/version 机械翻译不是猜测。
  4. 旧键只允许既有 `original|summary` 并发弃用信号，其它 422；这比长期双义或 silent reinterpretation 更符合 fail-closed。

- **`Grok` 的问题分解**：
  1. 两个不同轴撞名：公开 retrieval `filters.channel ∈ {original, summary}`（`retrieval/models.py:14`；`retrieval_request.py:354-355`）；FilterMeta.channel 是业务频道（`semantics.py:17`）。同一请求无法同时写 `channel=sold` 与 `channel=summary`。
  2. 内部物理列 `mkb_vector_records.channel` 的含义对向量层是对的；碰撞发生在 **public contract**。这与 Q10 的列名盗用不同：这里内部语义并未撒谎。
  3. 未知 filter 已 fail-closed（`retrieval_request.py:333-340`）。按 value 猜（`summary`→向量，其它→业务）会在业务频道恰好叫 `summary` 时失真。
  4. 现有 e2e 检索调用还缺 namespace 必 422（`api/models.py:505-509`）。「旧客户端」面很小，兼容期不必设计成长期双义。
- **`Grok` 对 `GPT` 推荐线路的分析**：
  - **赞成 public 分名 `semantic_channel` / `vector_channel`**：两轴必须能同请求出现；`source_channel` 会让人以为这是 source_kind 的别名，更差。
  - **赞成暂不强制改内部向量列名**：降低 DDL/回填范围，service 做明确映射。
  - **兼容策略收紧**：不要「根据 value 猜」。允许的过渡只有一种机械规则：若请求仍带旧键 `channel` 且值 ∈ {`original`,`summary`}，则视为 `vector_channel` 并标记弃用；**任何其它值一律 422**，提示改用 `semantic_channel`。禁止 `channel=sold` 被解释成业务维。
- **`Grok` 的最终建议**：
  **确认分名，禁止 value-guess。** public 合同使用 `semantic_channel`（FilterMeta.channel）与 `vector_channel`（`original|summary`）。内部向量列可保持 `channel`。旧 public `channel`：仅 `original|summary` 可过渡映射为 `vector_channel`，其余立即 422。未知新键继续 422。此建议仍不是 Truth。

- **问题**：是否确认新 public schema 只用 `semantic_channel`/`vector_channel`；旧 schema 的 `channel` 仅按原闭集 `original|summary` 机械翻译并弃用，其它422；新 schema禁止旧键，绝不在同一 schema 按 value猜轴？
- **业主回答**：🔒 **FROZEN**：新 public schema 只用 `semantic_channel` 与 `vector_channel`；旧 schema 的 `channel` 仅对既有 `original|summary` 机械映射为 vector channel 并弃用，其它值 422；新 schema 禁旧键，不在同一 schema 按 value 猜轴；内部向量列可暂保留物理名。→ `T-O-395`

### Q16 — public object surface 是否包含 raw byte read（gate：`G-NH-07`；来源：proposed §8、RA06）

- **影响范围**：public routes；auth/team scope；object stat/read；GC/hold；DoS/内容托管风险；local_object ingest；`AP-NH4/NH7/NH9`。
- **为什么必须确认**：`T-O-385` 冻结“必须有受鉴权上传、只返回 handle/digest/size、不造 Item”，但没有冻结 caller 是否能凭 handle 读 raw bytes。HEAD 仅有内部 `read_verified` 和业务 artifact metadata read（`src/storage/local_store.py:107-122`; `api/public/routes.py:226-294`; `NH-RA06-B06/B10/B11`）。误开 raw GET 会扩大数据外泄、带宽和非法内容托管面。
- **当前建议 / 倾向**（`GPT` · post-second-opinion）：public v1 提供 authenticated upload + authenticated stat/status，最小字段为 handle/digest/size/media declaration 与 pending/ingested/expired/tombstoned disposition，不返回 path/filename；跨 team handle 403、未鉴权失败。不提供 raw byte GET，bytes 仅由授权 `local_object` intake 内部 `read_verified`；现有 generation/business artifact read 不升级成 object browser，未来导出需独立 reopen。
- **Reasoning**：
  1. 调用方完成两步 ingest 只需要稳定 handle 与状态，不需要把 CAS 变成下载服务。
  2. 禁 raw read 显著缩小未鉴权/越权、带宽 DoS、恶意内容托管和 retention/GC 的产品面。
  3. stat/status 能解决“上传是否成功、是否已 ingest/过期”的可观察性，不需要返回原始内容。
  4. 若未来确有导出需求，应以独立业务 artifact contract 和审计/授权 reopen，而不是让持 handle 等同持下载权。

- **`Grok` 的问题分解**：
  1. `T-O-385` 冻结的是「必须有受鉴权上传、返回 handle/digest/size、不造 Item」，**没有**冻结持 handle 可读 raw bytes。HEAD：public object 路由 0（`D-14`）；内部 `read_verified`（`local_store.py:107-122`）；业务 generation-artifact 只读元数据（`api/public/routes.py:226-294`）。
  2. 两步 ingest 的调用方需要确认「字节已在、digest/size 稳定、是否仍 pending/已 ingest/已过期」。这是 **stat**，不是下载。
  3. 误开 raw GET 的代价是数据外泄、带宽 DoS、把 CAS 变成内容托管/CDN。handle 不是授权令牌以外的下载权。
  4. 现有 artifact GET 是 Task 作用域的业务合同，升级成通用 object browser 会破坏 S13 身份。
- **`Grok` 对 `GPT` 推荐线路的分析**：
  - **赞成 v1 = authenticated upload + authenticated stat/status，无 raw byte GET。** 内部 ingest 经 `read_verified`；artifact 元数据路由保持独立。
  - **stat 的最小闭集**应包括 handle、digest、size、media declaration、disposition（pending/ingested/expired/tombstoned），**不含** path/filename。
  - **安全附加**：跨 team 的 handle 必须 403 而不是用 404 当存在性神谕（`read_verified` 已有 team mismatch 403）。未鉴权必须失败。
  - 若未来要导出，走独立业务 artifact + 审计 reopen，不把 G-NH-07 的 v1 面做成「持 handle = 持下载权」。
- **`Grok` 的最终建议**：
  **确认 GPT 的 public v1 边界。** upload + 鉴权 stat/status；无 raw GET；raw bytes 仅内部 `local_object` ingest；generation-artifact 元数据读不升级。此建议仍不是 Truth。

- **问题**：是否确认 public v1 为 authenticated upload + stat/status（无path/filename、跨team 403）且无 raw byte GET，bytes只供内部 local_object ingest，业务artifact read保持独立？如不确认，请明确 raw read授权、审计、流量帽和retention/GC法。
- **业主回答**：🔒 **FROZEN**：public v1 提供 authenticated upload + stat/status（handle/digest/size/media/disposition，无 path/filename），跨 team handle 403；不提供 raw byte GET，bytes 只供内部 `local_object` ingest，业务 artifact read 保持独立，未来导出另行 reopen。→ `T-O-396`

### Q17 — registered API exhausted-zero 的产品终态（gate：`G-NH-08`；来源：proposed §8、RA04/08/09）

- **影响范围**：scatter root terminal；Task status/result；metrics；Item/Revision/vector counts；retrieval response；caller retry；`AP-NH1/NH7/NH9`。
- **为什么必须确认**：HEAD 对 `records=[] + exhaustion proof` 返回父 Task `succeeded`、counts 全 0、Items 空；无 proof 的空集失败，empty member 也失败（`src/runtime/workflow/runtime_scatter.py:76-98`; `tests/e2e/test_registered_api_scatter.py:352-373`; `NH-RA04-B07`）。现 `WorkflowTerminalKind.NOOP` 最终也映射成 succeeded，不能自动提供业务口径。若普通 success 同时表示“发布了知识”和“确定没有知识”，运营指标与调用方重试语义会混淆。
- **当前建议 / 倾向**（`GPT` · post-second-opinion）：冻结独立 `result_disposition=exhausted_zero`，与 metadata `no_change` 分字面但同属“流程完整、非 indexed success”家族。Task/Execution 技术状态可继续 complete/succeeded，不能只靠 `WorkflowTerminalKind.NOOP`；必须携 immutable exhaustion proof，child/item/revision/vector/publication counts 全零，retrieval 合法空，同 fingerprint replay 同 disposition，指标不计 indexed success。
- **Reasoning**：
  1. 有 exhaustion proof 的零集合不是内容错误，判 explicit failure 会诱导无意义重试；但普通 success 又会误报产出。
  2. distinct business disposition 保留“流程成功执行”和“产生知识”两种指标，符合两账分离。
  3. 不造 child/Revision/vector 保持身份诚实；检索空是该终态的正确产品结果，不是缺 proof。
  4. same-fingerprint replay 返回同一结果，与现 Task idempotency 法一致；单独切换 `WorkflowTerminalKind.NOOP` 仍会投影 succeeded，不能代替可查询的 business disposition。

- **`Grok` 的问题分解**：
  1. HEAD：`records=[]` + exhaustion proof → scatter join 把零成员当 **SUCCESS**（`runtime_scatter.py:76-98`）；e2e 父 Task `succeeded`、counts 全 0、items `[]`（`test_registered_api_scatter.py:352-373`）。无 proof 的空集失败；empty member 整批 422。
  2. 引擎已有 `WorkflowTerminalKind.NOOP`，但 runtime 把它 **映射成 `ExecutionStatus.SUCCEEDED`**（`runtime_outcome.py:505-509`）。所以「改用 NOOP 终端」**不会**单独给出可检索/指标口径，只是换了图枚举。
  3. 已有另一类业务无变更：`metadata_no_change` 守卫直接进 succeeded（`lsrag_definition.py:290-297`，priority 4）。它表示「语义没变」，不是「集合合法为空」。两者重试语义不同。
  4. 产品要分清：流程跑完 vs 产生了可检索知识。`FG-NH-03/04` 禁止 Task succeeded / `publication_ready` 冒充检索。
- **`Grok` 对 `GPT` 推荐线路的分析**：
  - **赞成独立业务 disposition，而不是 explicit failure，也不是普通 success。** 有 proof 的零集合诱导重试是错的；计入「已索引 item」也是错的。
  - **赞成不造 child/Revision/vector，retrieval 合法空，同 fingerprint replay 同一结果。**
  - **不要把 exhausted-zero 与 metadata `no_change` 合成一个字面**：GPT 写的 `no_change / exhausted_zero` 应读成 **同一家族、两个登记值**。metadata 无变更保持 `no_change`；API 穷尽零集合用 `exhausted_zero`。
  - **Task.status 可以继续是 succeeded/complete 族，但 result disposition 必须可查询、进指标标签、进 L4 断言。** 仅改 `WorkflowTerminalKind.NOOP` 不够。
- **`Grok` 的最终建议**：
  **确认独立 `exhausted_zero` result disposition**（与 metadata `no_change` 分字面、同属「流程完整、非 indexed success」家族）。不造 child/Revision/vector；必须有 immutable exhaustion proof；retrieval 空是正确产品结果；同 fingerprint 重放同一 disposition。禁止计入已索引计数，禁止用父 `succeeded` 单独当 DoD。此建议仍不是 Truth。

- **问题**：是否确认独立 `result_disposition=exhausted_zero`（与 metadata `no_change` 分字面），Task技术状态可complete/succeeded但不计indexed success、不造child/Revision/vector/proof，并以immutable exhaustion proof + retrieval empty +同fingerprint replay收口？
- **业主回答**：🔒 **FROZEN**：登记独立 `result_disposition=exhausted_zero`，与 metadata `no_change` 分字面；Task 技术状态可 complete/succeeded，但不计 indexed success，不造 child/Revision/vector/publication proof，必须有 immutable exhaustion proof、retrieval empty 与同 fingerprint replay。→ `T-O-397`

---


## 3. Campaign 归属、安全隔离、seal 事务与 restart 语义

### Q18 — Workflow substrate 留在 new-harvest 还是外置前置（gate：`G-NH-09`；来源：proposed §6/§8、RA01/02）

- **影响范围**：campaign scope；planning-final DAG；`AP-NH1/NH2/NH3` ownership；migration；交付节奏；如果外置则涉及前置 campaign/接口版本。
- **为什么必须确认**：`T-O-384/387/388` 要求 kind family、多候选、声明式再获取与选后 seal，而 HEAD 没有 selected-output merge、representation guard 或 actual binding（`NH-RA01-B01..B07`; `NH-RA02-B01..B04`）。这些不是可选优化：不改 substrate，10+3 的多数 capability 即使存在也无法合法选中。
- **当前建议 / 倾向**（`GPT` · post-second-opinion）：把必要 Workflow substrate 保留在 new-harvest 的 `AP-NH1..NH3`，闭集只含 registered selected-output CONTROL、typed fact guard、kind-only resolver、actual seal/compat；明确排除通用 JOIN、自由表达式、动态 loader/DSL。NH1 任一承重 spike 证伪即 stop/reopen `G-NH-02/09`，不得实施中退回 graph duplication。
- **Reasoning**：
  1. graph/binding 是四通道目标的直接前置，外置不会消除工作，只会新增跨 campaign 版本/验收接口。
  2. 本仓已有七表、无环、pin、guard、CAS 等大部分 substrate；本次是有界增量，不是从零建设引擎。
  3. 把范围钉在 NH 所需原语，可以防止“顺手做通用 DSL/JOIN/自由表达式”的引擎膨胀。
  4. NH1 stop/reopen 提供风险阀：事实若证明增量失控，再拆役，而不是预先制造假依赖。

- **`Grok` 的问题分解**：
  1. `T-O-384/387/388` 要求 kind 家族、多候选、声明式再获取、选后 seal。HEAD 缺 selected-output merge、representation guard、actual binding（`NH-RA01-B01..B07`；`NH-RA02-B01..B04`）。这些不是优化项：不改 substrate，6 张 live 图与 10+3 能力即使存在也无法合法选中。
  2. 底座大半已在：七表无环、登记 guard、compiled digest pin、compat definitions、Outcome CAS。本次是 **有界增量**，不是从零做引擎。
  3. 外置 campaign 不会减少工作，只会增加跨战役接口版本与验收门；而 NH 的 DoD 是四通道 live-to-vector，离不开这些原语。
  4. 风险是相反方向：借「留在 NH」顺手做 JOIN/自由表达式/通用 DSL（面 01 已禁 CWL/Temporal/FEEL）。
- **`Grok` 对 `GPT` 推荐线路的分析**：
  - **赞成保留在 new-harvest，作为 AP-NH1 chosen-shape + NH2/NH3 foundation。** 范围钉死：registered merge CONTROL、typed fact guard、kind resolver、actual seal/compat。
  - **赞成 NH1 证伪即 stop/reopen**：若七表在 bounded spike 中证明无法表达 merge，回到本册 reopen `G-NH-02/09`，禁止实施中改去复制 13 张图。
  - **不赞成预先外置**：没有独立引擎战役的 Frozen 接口可接；现在拆只会制造假依赖。
  - **围栏**：本 gate 的「纳入 NH」**不是**授权通用 workflow 重建。JOIN 步、自由表达式、动态 loader 仍排除。
- **`Grok` 的最终建议**：
  **确认 substrate 留在 new-harvest 的 AP-NH1–NH3**，闭集仅限 NH 所需原语；NH1 任一承重 spike 证伪即 stop/reopen，不得静默换 duplication/表达式方案。不另开引擎战役。此建议仍不是 Truth。

- **问题**：是否确认将有界 NH substrate（selected-output CONTROL、typed fact guard、kind resolver、actual seal/compat）纳入 AP-NH1–NH3，排除通用JOIN/DSL/表达式，NH1证伪即stop/reopen且不得退回duplication？如不确认，请指定外置campaign及冻结接口。
- **业主回答**：🔒 **FROZEN**：NH 所需有界 Workflow substrate 纳入 AP-NH1–NH3：selected-output CONTROL、typed fact guard、kind-only resolver、actual seal/compat；排除通用 JOIN/DSL/自由表达式/动态 loader；NH1 证伪即 stop/reopen，禁止退回 duplication。→ `T-O-398`

### Q19 — untrusted/native dependency 的逐能力隔离与风险接受线（gate：`G-NH-10`；来源：proposed §8、RA03/05）

- **影响范围**：PDF parser、OCR binary/trained data、browser/Chromium、Vision model server；deployment；license/SBOM；CVE；resource/egress；readiness；`AP-NH1/NH6/NH9`。
- **为什么必须确认**：HEAD PDF 解析在 API 进程内，browser 不存在；公开资料和 advisory 表明 parser 有 DoS/RCE 类风险，browser root/no-sandbox 对不可信 URL 风险更高；仓库又标 Proprietary（`src/runtime/intake/types.py:100-171`; `pyproject.toml:11-21`; `NH-RA05-B06/B11/B12`）。隔离/许可证不能由实现者看到某个方便库后临时决定。
- **当前建议 / 倾向**（`GPT` · post-second-opinion）：逐能力冻结接受线：PDF parser/确定性 OCR 默认 isolated subprocess（CPU/memory/time/output caps、无网络、受控 tmp、kill/restart）；browser/print 为 hardened non-root local sidecar/隔离进程，生产默认禁止 `--no-sandbox`，网络必须走 S16 egress/SSRF fence；Vision/DU 留 local inference boundary。任何 native/binary 入生产前须 pin identity、license/SBOM、CVE baseline、恶意/加密/超大负样本与实弹 readiness；豁免只能 owner 具名。
- **Reasoning**：
  1. PDF 与 browser 的威胁模型不同，应分别隔离；“同一个 sandbox 故事”无法覆盖解析炸弹和浏览器逃逸/egress。
  2. subprocess/sidecar 允许操作系统限额和 kill，而不会让 parser crash 与 API 主进程同命运。
  3. 许可证与部署形态相关：链接进 proprietary 进程、调用 CLI、独立 sidecar 的义务不同，必须与技术选型同票。
  4. readiness 必须证明具体 binary/model/data 与负样本行为，而不是 import/which 或模型名单；browser no-sandbox 与 parser/browser 共用网络策略都应作为 hard failure。

- **`Grok` 的问题分解**：
  1. HEAD PDF 解析在 API 进程内（`types.py:144-171` 的 literal regex）；browser 供给不存在；仓库标 Proprietary（`pyproject.toml:11`）；无 PDF/browser/OCR 生产依赖。
  2. 威胁模型不同：parser 是恶意 PDF 的 DoS/RCE（面 03/05 advisory）；browser 是不可信 URL 的逃逸 + SSRF/egress；Vision 是模型服务面。一个 sandbox 故事盖不住（`NH-C-45`）。
  3. 许可证与链接形态同票：GPL 解析器链进 proprietary 进程 vs 调 CLI vs sidecar，义务不同。本题裁 **接受线**，不锁库名。
  4. readiness 必须证明具体 binary/model/data + 负样本；`/v1/models`、import、`which` 不足（`T-R-NH-10`）。
- **`Grok` 对 `GPT` 推荐线路的分析**：
  - **赞成逐能力接受线**：PDF parser 与确定性 OCR → isolated subprocess（CPU/memory/time/output cap、无网络、受控 tmp、kill/restart）；browser/print → hardened local sidecar 或等价隔离进程（non-root sandbox、egress/SSRF、独立资源帽）；Vision/DU 留在 local inference boundary。
  - **赞成 production 前置**：pinned identity、license/SBOM、CVE baseline、恶意/加密/超大负样本、实弹 probe。不在 API 主进程直接解析不可信 PDF/URL。
  - **附加硬围栏**：Chromium `--no-sandbox` **不得**作为生产默认（容器里常见但与 untrusted URL 目标冲突）。parser 进程默认无网络，browser 进程 **有** 网络但必须走现有 S16 egress（`http_acquisition.py` / app egress），两者不可共用一份策略文件假装相同。
  - 本题仍不选定 pypdf/playwright/tesseract/poppler。
- **`Grok` 的最终建议**：
  **确认 GPT 的逐能力隔离接受线，并加上「生产默认禁止 browser no-sandbox、parser 无网络 / browser 受控 egress 分账」。** 任何 native/binary 入生产必须过 pin/SBOM/CVE/负样本/readiness。豁免只能由 owner 具名，不能由库作者在 AP 里临时决定。此建议仍不是 Truth。

- **问题**：是否确认 PDF/确定性OCR isolated subprocess无网、browser hardened non-root隔离且生产禁`--no-sandbox`并走受控egress、Vision/DU留local inference，同时把pin/SBOM/CVE/负样本/readiness设为production前置，豁免仅owner具名？
- **业主回答**：🔒 **FROZEN**：PDF parser/确定性 OCR 使用无网 isolated subprocess；browser/print 使用 hardened non-root 隔离、生产禁止 `--no-sandbox` 并走 S16 受控 egress；Vision/DU 留 local inference；pin/SBOM/CVE/负样本/readiness 为 production 前置，豁免仅 owner 具名。→ `T-O-399`

### Q20 — selected-route Outcome 与 actual S05 seal 是否同一 UoW（gate：`G-NH-11`；来源：proposed §8/§9.5、RA02/09）

- **影响范围**：runtime Outcome transaction；Execution actual fields；Process materialization；W-NH-SEL/SEAL；retry/recovery；`AP-NH1/NH3/NH9`。
- **为什么必须确认**：HEAD 已有 Outcome+route 同事务 CAS，但没有 actual seal。若 route 先提交、seal 后提交，中间 crash 会留下“图说已选，binding 仍 unsealed”的窗口；若 seal 先提交、route 后失败，又会留下无可达 selected route 的 actual（`src/runtime/workflow/runtime_outcome.py:88-137`; `NH-RA02-B04`; `NH-RA09-B14`）。
- **当前建议 / 倾向**（`GPT` · post-second-opinion）：以现 Outcome UoW 为唯一线性化点：先前 acquire/decode facts 已 durable；本 UoW 同时提交 selected-route Outcome、Execution actual unsealed→sealed CAS 与 clean Process eligibility，commit 后才 outbox/dispatch。second seal 的不同 route/digest 一律 ConflictError，同 route/digest replay 原 seal；v1 不接受 route 与 seal 两提交。
- **Reasoning**：
  1. 同 UoW 消除最危险的两提交 split-brain，不需要再发明 pending reconciliation 状态机。
  2. 本仓 Outcome/route 已在同 UoW，扩一枚 Execution CAS 比引入新 saga 更贴合 substrate。
  3. “commit 后才 dispatch”与现 outbox/Process fence 一致，可承受 at-least-once delivery而实现 effect-once。
  4. representation facts 先提交，seal transaction 才能计算/校验完整路径，不会 hash 未 durable 的内存事实。

- **`Grok` 的问题分解**：
  1. HEAD 已有 Outcome + route 同事务 CAS（`runtime_outcome.py:88-137`），但 **没有** actual seal。这是可扩的线性化点，不是已完成的两阶段 binding。
  2. 若 route 先提交、seal 后提交：crash 留下「图说已选、actual 仍 unsealed」——恢复可能重选工人，违反绑定后 fail-loud（`T-O-383`）。若 seal 先提交、route 失败：留下无可达 selected route 的 actual。两者都是无名态，面 09 的 `W-NH-SEAL` 无法测。
  3. acquire/decode facts 来自 **更早的 Process Outcome**（各自已提交）。seal 事务读这些 durable 行，不 hash 内存。
  4. 第二次不同 digest / 不同 selected route 必须 ConflictError；同 digest replay 返回原 seal。这是 Stripe 幂等键机制，不是 Kafka EOS。
- **`Grok` 对 `GPT` 推荐线路的分析**：
  - **赞成同一 S12 UoW**：selected-route Outcome + actual unsealed→sealed CAS + 后继 clean Process 行的 eligibility。commit 之后才 dispatch clean。这消除最危险的两提交 split-brain，且贴合现 outbox/Process fence。
  - **赞成「facts 必须已经 durable」**：通常它们已在先前 acquire/decode Outcome 提交；seal 事务只读。不必为每个 fact 再发明 saga。
  - **赞成 second-seal / 不同 digest = ConflictError，同 digest replay 原 seal。**
  - **不赞成**「先 Outcome 再独立 seal」作为 v1：那正是要定义的崩溃窗，测试与恢复成本高于多一枚 Execution CAS。
- **`Grok` 的最终建议**：
  **确认 GPT 的同 UoW 法。** 线性化点 = 现 Outcome 事务扩一枚 Execution actual CAS 与 clean eligibility；commit 后 dispatch；二次不同 seal → ConflictError。W-NH-SEL 仅存在于 facts 已写、seal 未写（选边前）；一旦本 UoW 提交，禁止重选。此建议仍不是 Truth。

- **问题**：是否确认先前facts已durable，selected-route Outcome + actual seal CAS + clean eligibility在同一Outcome UoW，commit后才dispatch；同seal replay、异route/digest ConflictError，v1拒绝两提交？如不确认，请定义中间crash与是否可重选。
- **业主回答**：🔒 **FROZEN**：先前 acquire/decode facts 已 durable；selected-route Outcome、actual seal CAS 与 clean eligibility 在同一 Outcome UoW，commit 后才 dispatch；同 seal replay，异 route/digest ConflictError；v1 禁止 route/seal 两提交。→ `T-O-400`

### Q21 — causal restart 对 actual binding / clean 的 intent-specific 继承法（gate：`G-NH-12`；来源：proposed §8、RA02/08/09）

- **影响范围**：same-Execution retry；new generation；implementation upgrade；intake.rebuild；metadata refresh；Task commands；old pin；`AP-NH3/NH8/NH9`。
- **为什么必须确认**：代码与 `S03-T018` 要求现 `full_task` retry 新 generation 复制 exact revision/digests（`src/runtime/task/task_commands.py:293-311`; `docs/baseline/domain-truth/S03-workflow-engine.md:182`）；rebuild/metadata 又从 frozen clean 入场却仍走 deterministic clean（`src/runtime/intake/clean_preflight.py:28-127`）。同时 S05 §4.6 声称 existing Task implementation upgrade 走 `task_restarts` 新 generation，但 DDL 只允许 `full_task|atomic_intake_item` 两种 scope（`src/persistence/migrations/001_initial.sql:198-219`），没有 upgrade 槽。若不拆开，会把 full retry、exact-clean rebuild 与 implementation upgrade 混成一条不可能同时正确的语义。
- **当前建议 / 倾向**（`GPT` · post-second-opinion/code-review）：四分法冻结：① Process retry/recovery/resume 与现有同 Task `restart_scope=full_task`（虽建新 generation）都属于同一承诺，保留 exact workflow/policy/sealed actual/selected process；② rebuild/changed-metadata 不 acquire、不绑定原 source worker，只 replay frozen clean；③ index.rebuild 不碰 S05/Revision；④“已有对象使用新 cleaner/validator”在当前 S02/S03 七意图与两种 restart_scope 中没有合法入口，建议 **不纳入 NH v1**，新实现只影响未来新 ingest，并对 S05 §4.6 追加 erratum。若 owner 坚持 v1 支持，必须另开显式 operator command/restart identity 与 scope/DAG，而不能复用 full retry/rebuild。
- **Reasoning**：
  1. 代码和 `S03-T018` 都证明 `full_task` retry 虽创建新 generation，仍是“重做同一承诺”：复制 exact workflow/revision/digests；因此不能用“new generation”推导清 actual。
  2. rebuild/metadata 的业务输入是 accepted clean artifact，不是源表示；它们既不应复制源 worker 为新 actual，也不应再次 acquire/clean。
  3. `S05` §4.6 描述已有 Task implementation upgrade，但 S02/S03/DDL 只有 `full_task` 与 `atomic_intake_item` 两种 scope，当前没有能既换实现又不冒充 retry/rebuild 的合法入口；这是 Truth/代码缝，不应在 AP 偷补。
  4. NH v1 暂不支持已有对象 upgrade 是最小一致收口；若 owner 要求支持，必须显式扩 scope/Task contract/状态机并重估 proposed DAG，而不是复用当前 `retry` 或 `intake.rebuild`。

- **`Grok` 的问题分解**：
  1. HEAD 混了三类「再来一次」：Process retry 保留 `process_key`（`runtime_outcome.py:145-182`）；Task causal restart **新 generation、新 Execution 行**，却复制 previous 的 `s05_binding_digest`（`task_commands.py:293-311`）；`intake.rebuild` / changed-metadata 从 frozen clean 入场，图仍走 `acquire.to_decode` + `dispatch_clean`（`acquisition_intents.py:25-93`；`lsrag_definition.py:299-306`；`clean_preflight.py:28-127`）。
  2. 一律复制 actual：升级/新表示无法换工人。一律清空：基础设施 retry 会热切。rebuild 再 bind 源通道工人：把已接受 clean 伪装成新 acquisition。
  3. `G-NH-12` 管 **generation / actual / graph pin 继承**；`G-NH-19` 管 rebuild 是否执行 clean Process。二者必须分号。
  4. **关键易混点**：HEAD 的 causal restart 已经是新 generation，但它的产品意图是「同一失败 Task 再跑」，**不是** implementation-upgrade。不能把「新 generation」自动等同于「清 actual」。
- **`Grok` 对 `GPT` 推荐线路的分析**：
  - **赞成按 intent 分账，反对单一 `restart=true`。**
  - **对 GPT ① 同意，但要把因果 restart 划进去**：同一 Task 的失败重试 / resume / causal restart（新 Execution 行、`retry_of_execution_uuid` 指向先前 root）**保留 sealed actual、selected process、graph pin**。这是「重做同一承诺」。
  - **对 GPT ② 同意，但 upgrade 不是现有七意图之一**：implementation-upgrade / 新 ingest 必须是 **显式新 Task**（可带 lineage），清空 actual，在新 frozen revision/policy 内重绑。禁止借用 rebuild 或 causal restart 偷换工人。不要在本册偷偷发明第八个 public intent；若需要公开入口，另开 Truth，而不是挤进 `intake.rebuild`。
  - **对 GPT ③④ 同意**：rebuild/changed-metadata 不重 acquire、不 bind 原 source worker，只引用 frozen admitted clean；index.rebuild 不碰 S05/Revision。
- **`Grok` 的最终建议**：
  **确认 intent-specific 继承，但把 HEAD causal restart 归入「保留 actual」而不是「新 generation 清 actual」。** 矩阵：Process retry / 同 Task causal restart → 保留 sealed actual + pin；显式新 ingest/upgrade Task → 清 actual 后重绑；rebuild/metadata → 不 acquire、不 bind 源工人、只 replay frozen clean（是否跑 clean Process 见 Q27）；index.rebuild → 不碰 S05/Revision。此建议仍不是 Truth。

- **问题**：是否确认：Process retry与现有同Task `full_task` retry均复制exact workflow/policy/sealed actual；rebuild/metadata只replay frozen clean；index.rebuild不碰S05；已有对象使用新cleaner不纳入NH v1、新版本只影响未来ingest，并对S05 §4.6追加erratum？若owner要求v1升级，请另裁显式operator command/restart identity与scope/DAG。
- **业主回答**：🔒 **FROZEN**：Process retry/recovery/resume 与现有同 Task `full_task` retry 均复制 exact workflow/policy/sealed actual；rebuild/metadata 只 replay frozen clean，index.rebuild 不碰 S05。已有对象使用新 cleaner/validator 不纳入 NH v1，新实现只影响未来新 ingest；S05 §4.6 据此 append erratum。未来若支持须新 owner-gate 冻结显式 operator command/restart identity 与 scope/DAG。→ `T-O-401`

### Q22 — HTML 空壳 / 主文缺失是否进入 representation fact 闭集（gate：`G-NH-13`；来源：proposed §8、RA03）

- **影响范围**：static→browser declared reacquire；RepresentationFact schema；guard registry；HTML observer；错误码；`AP-NH1/NH2/NH3/NH7/NH9`。
- **为什么必须确认**：HTML 带标签但无主文当前可 acquire/decode 成功，系统没有 typed shell observation（`src/runtime/intake/acquisition_ingest.py:65-66`; `NH-RA03-B10`）。若 static→browser 的 route 需要该信号，它就不能只藏在 cleaner 的质量判断或运行时启发式中，否则会重新变成暗升。
- **当前建议 / 倾向**（`GPT` · post-second-opinion）：在 decode 阶段由 registered deterministic observer 产生 versioned `main_text_presence=present|absent|unknown` fact + observer identity/evidence；仅明确 `absent` 可被 eq guard 用于已声明 browser edge，`unknown` fail-closed。observer 版本进入 fact/path digest并可能要求新 graph revision；禁止 LLM/clean quality score 成为 route fact。
- **Reasoning**：
  1. 凡是改变 acquire path 的输入都必须 durable、可 replay；否则 static→browser 会变成 handler 内暗升。
  2. bounded structural/text observer 可用确定规则和 fixture 回归；LLM 判主文会让 route 非确定且难以进入 compiled digest。
  3. 三态而非 boolean 能诚实区分“确认为 absent”和“observer 无法判断”；unknown fail-closed 防误抓浏览器。
  4. fact 只表达 route 所需的最小观察，不重开网页质量评分/clean 算法。

- **`Grok` 的问题分解**：
  1. `T-O-388` 允许绑定前有限、声明式、无环正向再获取；禁止 handler 暗升。static→browser 若要合法，路由输入必须是 durable representation fact，而不是 cleaner 质量分。
  2. HEAD：非 binary 且 `raw_text` 全空白才 `ACQUISITION_EMPTY`（`acquisition_ingest.py:65-66`）。带标签无主文的 HTML **会 acquire/decode 成功**，系统没有 typed shell observation（`NH-RA03-B10`）。
  3. observer 若用 LLM，route 进入 compiled digest 会变成非确定；若把「页面好不好」整体上升为 representation，会重开 clean 算法。
  4. 三态必要：`present` / `absent` / `unknown`。boolean 无法表达「observer 这次看不懂」。
- **`Grok` 对 `GPT` 推荐线路的分析**：
  - **赞成 versioned `main_text_presence` 三态 + 登记 deterministic observer + eq guard。** `unknown` 不命中 forward edge（fail-closed），避免误抓浏览器。
  - **赞成不把 LLM 和质量分做成 route fact。** 最小结构观察即可（例如规范化后主文本长度/标签比的闭集规则），必须有 fixture。
  - **观察时机**：decode observer，不是 cleaner，也不是 acquire 成功的副作用。observer identity/version 写入 fact；改观察器 = 新 fact 版本，可能需要新 graph revision，不得热切旧 pin。
  - **产品后果要诚实**：unknown fail-closed 意味着部分 SPA 不会自动 static→browser。那是正确的；调用方可直接走已声明的 browser acquire，而不是靠启发式暗升。
- **`Grok` 的最终建议**：
  **确认 GPT 方案。** registered deterministic observer 产出 `main_text_presence=present|absent|unknown`；仅明确 `absent` 可命中已声明 browser edge；`unknown` fail-closed；禁止 LLM 判主文。observer 版本进入 fact/digest。此建议仍不是 Truth。

- **问题**：是否确认 decode阶段 registered deterministic observer 产 versioned `main_text_presence=present|absent|unknown`，版本进fact/digest；仅absent命中已声明browser edge、unknown fail-closed，禁止LLM/quality score路由？
- **业主回答**：🔒 **FROZEN**：decode 阶段 registered deterministic observer 产 versioned `main_text_presence=present|absent|unknown`，版本进入 fact/path digest；仅 absent 可命中已声明 browser edge，unknown fail-closed；禁止 LLM/quality score 路由。→ `T-O-402`

---


## 4. Browser/print 供给、upload UoW、intent 错误法与 closure

### Q23 — page render 与 print-to-PDF 是否共享 browser runtime（gate：`G-NH-15`；来源：proposed §8、RA03/05）

- **影响范围**：browser binary/driver；capability identity；sandbox/egress；profile evidence；resource budget；readiness；`AP-NH1/NH3/NH6/NH7/NH9`。
- **为什么必须确认**：rendered DOM 与 PDF print 都需要真实浏览器，但输出合同、失败条件和资源曲线不同。HEAD 既无 supply，也用常量 `injected-browser-renderer.v1` 冒充 profile；legacy 把两者焊在 CF Browser Rendering（`src/runtime/intake/acquisition_ingest.py:535-536`; `NH-RA05-B07`; `RA-03-LEGACY-03/04`）。若不分清“共享 binary”和“共享 capability identity”，证据和预算会混账。
- **当前建议 / 倾向**（`GPT` · post-second-opinion）：v1 共享同一 hardened local browser binary、导航与受控 egress sandbox，但注册 `browser.render` / `browser.print_pdf` 两个独立 capability/profile/timeout/size/concurrency/readiness/evidence；render 验 DOM，print 验 `%PDF-`，淘汰常量 profile。部署以后可拆实例，不改变 contract、strategy 或 graph taxonomy。
- **Reasoning**：
  1. 共享 binary/driver 能避免两套 Chromium 版本、sandbox 与导航实现漂移；两个 capability 又保留输出和预算的真实差异。
  2. print 不是 render 后改名，必须验证 `%PDF-`、page/print参数与独立 profile；DOM render 也不能用 PDF success 证明。
  3. 合同与部署拓扑分离后，未来因资源隔离拆实例不需要发新 business strategy 或 graph taxonomy。
  4. 两项均受同一 egress/SSRF fence，但 metrics/backpressure 分开，避免 print 大任务拖死普通 render。

- **`Grok` 的问题分解**：
  1. 两者都需要真实浏览器，但输出合同完全不同：rendered DOM vs `%PDF-` bytes。HEAD 既无供给，又用常量 `injected-browser-renderer.v1` 冒充 profile（`acquisition_ingest.py:535-536`）；`representation_kind` 从不写 `print_pdf`。
  2. legacy 把 content 与 pdf 焊在同一 CF Browser Rendering 产品上（不同 HTTP 路径）。可借「同一浏览器产品、不同方法」，不可借云栈。
  3. CDP `Page.printToPDF` 的官方失败模式（零页才报错、pageRanges 被 quietly cap）证明 print 必须有独立 evidence/budget，不能用 DOM render 成功顶替。
  4. 身份分账失败会让 `web.browser_print_pdf` 与 `web.deterministic/rendered` 抢同一个并发帽，或让 print 大任务拖死 render。
- **`Grok` 对 `GPT` 推荐线路的分析**：
  - **赞成 v1 共享同一 hardened local browser binary + 导航/egress sandbox，注册两个 capability**：`browser.render` / `browser.print_pdf`，各自 timeout/size/concurrency/readiness/evidence。
  - **赞成合同与部署拓扑分离**：以后因资源隔离拆实例不改 strategy/graph taxonomy。
  - **证据法**：print 必须验证 `%PDF-` + 真实 profile identity；render 必须验证 rendered DOM，不得把 screenshot/HTML 改名。禁止常量 profile。
  - 与 Q13/Q19 一致：这是 local capability，不是 S11 generate。
- **`Grok` 的最终建议**：
  **确认 GPT 方案。** 共享 hardened local browser runtime；render 与 print 两个独立 capability/profile/预算/readiness；允许日后拆实例不改合同。`injected-browser-renderer.v1` 必须淘汰。此建议仍不是 Truth。

- **问题**：是否确认 v1 共享 hardened browser binary/navigation/egress，但 render/print 为两个独立 capability/profile/预算/readiness，分别验DOM/%PDF并淘汰常量profile；部署可拆实例而不改合同？
- **业主回答**：🔒 **FROZEN**：v1 共享 hardened browser binary/navigation/egress，但 render/print 为两个独立 capability/profile/预算/readiness/evidence，分别验证 DOM/%PDF，淘汰常量 profile；部署可拆实例而不改 contract/strategy/graph taxonomy。→ `T-O-403`

### Q24 — upload success 的 catalog/reference/hold 原子事务（gate：`G-NH-16`；来源：proposed §8、RA06/09）

- **影响范围**：ObjectStorePort bounded write；stored-object catalog；purpose/ref/hold；public response；GC scanner/quarantine；upload→ingest handoff；`M-NH-05`；`AP-NH4/NH7/NH9`。
- **为什么必须确认**：`promote(bytes)` 不写 catalog/ref；未 catalog bytes 对 GC 不可见会泄漏，而 catalog-without-ref 又是现 GC orphan 候选（`src/storage/local_store.py:71-105`; `src/services/object_gc.py:146-161`; `NH-RA06-B03/B04`）。仅靠 24h grace 不能区分“合法等待 ingest”和“永远遗弃”。
- **当前建议 / 倾向**（`GPT` · post-second-opinion）：CAS bytes 成功后，同一 S12 UoW upsert catalog + `upload_pending` live ref/hold，commit 后才返回 usable handle；无 catalog或无 live ref均不算 upload success。后续 ingest acceptance 在自己的 UoW 新增业务 ref并 release/convert pending；取消/TTL释放后才进 grace/quarantine，GC TX2 recheck可 restore。未完成流只留 bounded staging并由 scanner清理，不进 usable catalog、不造 Item。
- **Reasoning**：
  1. catalog+pending ownership 让上传成功成为 durable 事实，同时让 GC 能看见且不误删；只 promote 或只 catalog 都缺半边。
  2. handle 仅在事务提交后返回，避免 caller 拿到一个可能被回滚/GC 的对象。
  3. pending→business ref 的转换保持“upload 不造 Item”，又让 ingest 完成后 ownership 不依赖客户端再确认。
  4. TTL/release+grace 能回收从未 ingest 的合法上传；quarantine recheck 处理与 ingest 并发。

- **`Grok` 的问题分解**：
  1. `promote(bytes)` 只写 CAS 文件，不写 catalog/ref（`local_store.py:71-105`）。未 catalog 的字节对 GC **不可见**，会泄漏。catalog 无 live ref 又是现 GC orphan 候选（`object_gc.py:146-161`）。24h grace 分不清「合法等 ingest」和「永远遗弃」。
  2. `T-O-385`：upload 成功不得制造 Item。因此 pending 状态必须是 **S13 的 ref/hold**，不是 S04 identity。
  3. 返回 handle 必须发生在事务提交之后，否则 caller 持有一个可被回滚/GC 的名字。
  4. upload UoW 与后续 local_object ingest Task UoW **必须分离**；ingest 经 `read_verified` 接 handle。purpose 字面仍是执行项，不在本题锁。
- **`Grok` 对 `GPT` 推荐线路的分析**：
  - **赞成 CAS bytes 成功后，同一 S12 UoW upsert catalog + `upload_pending` live ref/hold，提交后才返回 usable handle。** 只 promote 或只 catalog 都缺半边。
  - **赞成 ingest acceptance 在自己的 UoW 新增业务 ref 并 release/convert pending hold**；取消/TTL 释放，过 grace 后 GC 可 quarantine。未完成流只留 bounded staging，独立 scanner 清理，不进 usable catalog。
  - **赞成同 digest replay 同一 handle、并发不造双 live row**（已有 CAS unique）。GC 与 ingest 交错走现成 TX2 recheck（`object_gc.py` / `test_ns6_gc_toctou.py`）。
  - purpose 字符串、HTTP path/multipart 继续留给 action-plan。
- **`Grok` 的最终建议**：
  **确认 GPT 的原子 catalog+pending-hold 法。** 无 catalog 不返回 handle；无 live ref 不得算 upload success；upload 不造 Item；TTL/release 后才进 grace/GC。此建议仍不是 Truth。

- **问题**：是否确认返回handle前必须原子提交catalog+`upload_pending` live ref/hold，无任一不算success；ingest acceptance转换业务ref，取消/TTL后才grace/GC，未完成流仅staging scanner清理且不造Item？
- **业主回答**：🔒 **FROZEN**：返回 usable handle 前必须同 UoW 提交 catalog + `upload_pending` live ref/hold，无任一不算成功；ingest acceptance 转换业务 ref，取消/TTL 后才进入 grace/GC；未完成流仅 staging scanner 清理，upload 不造 Item。→ `T-O-404`

### Q25 — 七意图非法格是否冻结稳定 public error contract（gate：`G-NH-17`；来源：proposed §8/§9.4、RA08）

- **影响范围**：Task create public schema；seven-intent applicability；HTTP status/error code；caller compatibility；charter；`AP-NH1/NH8/NH9`。
- **为什么必须确认**：HEAD 有若干零散 422/409（deleted Item、inactive index.rebuild、unknown intent），但没有一张 stable 非法格合同；六个事后意图也不是 source-kind 选择器（`src/contracts/api/models.py:278-286`; `src/services/config_snapshots.py:138-144,474-501`; `NH-RA08-B05`）。若只在实现里碰到什么报什么，调用方和测试会把相同行为解释成 skip、no-op 或系统错误。
- **当前建议 / 倾向**（`GPT` · post-second-opinion）：把七意图合法/非法 applicability 与 machine-readable code 闭集写入 charter/API；422 仅请求形状/非法组合，409 仅目标状态/并发冲突。承重非法格在 admission fail-loud，**不创建 Task/Process**，不允许 no-op/skip；非 ingest 仍可复用 skeleton，但不得按 kind 生造 7×4 任务。code 字面由 action-plan登记，类别与无 silent skip 本题冻结。
- **Reasoning**：
  1. HTTP status 只能表达粗分类；stable code 才能让 caller 决定修请求、等待状态还是停止重试。
  2. applicability table 明确只有 ingest 以 kind 选图，可同时防止 28 格施工和非法 source+lifecycle payload。
  3. 复用 422/409 保持现 API 风格，不需要为每个格发明新状态码；注册 code 又能锁兼容。
  4. charter 化可阻止未来 action-plan 通过“当前没实现所以 skip”缩小产品面。

- **`Grok` 的问题分解**：
  1. 七意图不是 7×4 笛卡尔积：只有 `intake.ingest` 读 SourceDescriptor/kind 选图；其余按 Item 或 scope 寻址（`api/models.py:278-286`；`config_snapshots.py:138-144,474-501`；`T-R-NH-21`）。
  2. HEAD 已有零散 422/409（unknown intent `workflow-intent-not-supported`，`config_snapshots.py:488`；pipeline `INTAKE_INTENT_UNSUPPORTED`），但没有一张 **稳定非法格合同**。非 ingest 的 workflow_purpose 仍映射 `intake.ingest`（`config_snapshots.py:489`）——这是图复用，不是「该 intent 以 kind 选图」。
  3. 若实现里碰到什么报什么，测试会把相同行为解释成 skip / no-op / 系统错误，从而滑向 28 格施工或静默缩小产品面。
  4. HTTP status 只粗分：422 = 请求形状/非法组合；409 = 目标当前状态/并发冲突。caller 决策依赖 machine-readable code。
- **`Grok` 对 `GPT` 推荐线路的分析**：
  - **赞成把 applicability + 稳定 code 写入 charter。** 非法格一律 fail-loud，不 materialize Task/Process，不为 7×4 生造运行任务。
  - **赞成继续 422/409 两个 HTTP 家族**，不发明新状态码。
  - **必须登记承重非法格的 code 闭集**（例：带 source 的 rebuild、deleted Item 上 rebuild、inactive 上 index.rebuild、第五 kind、caller `workflow_key`）。本题不锁每个 code 字面，但要锁「有闭集、无 silent skip」。
  - 图复用（非 ingest 仍跑同一 skeleton）可以保留，**前提是** 非法 payload 在 admission 就被拒绝，而不是进 handler 再 skip。
- **`Grok` 的最终建议**：
  **确认 GPT 方案。** charter 化合法/非法格；HTTP 422/409 粗分 + 稳定 code；非法格 fail-loud、不造 Task/Process。不允许 no-op 顶替非法格。此建议仍不是 Truth。

- **问题**：是否确认 charter冻结七意图 applicability + machine-readable code闭集，422/409粗分；非法格在admission fail-loud且不建Task/Process，no-op/skip不可顶替，非ingest skeleton复用也不生造7×4任务？
- **业主回答**：🔒 **FROZEN**：charter/API 冻结七意图合法/非法 applicability 与 machine-readable code 闭集；422 仅请求形状/非法组合，409 仅目标状态/并发；非法格在 admission fail-loud且不建 Task/Process，no-op/skip 不可顶替，不生造 7×4 任务。→ `T-O-405`

### Q26 — 四层测试不可互换是否成为 charter completeness 法（gate：`G-NH-18`；来源：proposed §8/§9、RA09）

- **影响范围**：全 `AP-NH1..NH9` exit；charter/waiver；CI；closure evidence；default-root/runtime环境；retrieval mega；实验边界。
- **为什么必须确认**：当前 33 unit 全绿却不能证明默认组合根；source e2e monkeypatch且停 running；部分 search 调用缺 namespace必422；API只到 `publication_ready`（`tests/e2e/test_source_capability_paths.py:99-101,166-168`; `src/services/retrieval/retrieval_request.py:265-269`; `NH-RA09-B02..B04`）。若测试层只是 planning 建议，后续很容易以较便宜的层替代承重证明。
- **当前建议 / 倾向**（`GPT` · post-second-opinion）：把 L1 unit/contract、L2 integration/UoW、L3 default-root e2e、L4 retrieval-facet mega 不可互换写入 charter，每 AP 锁最低层；fault/race/security 只是附着标签。waiver 只能**延期**尚未满足的层，不能把 L3/L4改写成L1已足够；须 owner/指定治理角色具名，记录 affected Truth/AP/gate、理由、到期/reopen，并禁止覆盖 `T-O-376/378/381/383` 或修改期待值掩盖 S1。
- **Reasoning**：
  1. 四层分别证明算法、事务、接线与产品终态；它们的 failure surface 不同，数量再多也不能互换。
  2. charter 化让 `FG-NH-*` 成为退出法而非作者偏好，能阻止 monkeypatch、503、Task success 假绿。
  3. waiver 需要期限和 Truth 影响，且只能延期不能降层，才能区分暂时环境问题与实际缩小产品承诺。
  4. `.experiment` 继续不入四层证明：真实跑分也不能替代 deterministic contract/replay/facet。

- **`Grok` 的问题分解**：
  1. 当前假绿已经发生：33 unit 全绿不证明默认组合根；source e2e monkeypatch 且停 `running`（`test_source_capability_paths.py:99-101,166-168`）；search 缺 namespace 必 422（`retrieval_request.py:265-269`；`api/models.py:505-509`）；API 停在 `publication_ready`。
  2. 四层证明对象不同：L1 算法/合同、L2 UoW、L3 默认组合根接线、L4 可检索终态。数量再多也不能互换（`T-R-NH-19`；`FG-NH-13`）。
  3. fault/race/security 是附着标签，不是第五层。`.experiment` 继续服从 `T-O-380`，不是 completeness。
  4. 若只写在 planning，后续 AP 作者会用较便宜的层替代承重证明。只有 charter 化 + 具名 waiver 才能保住 `FG-NH-01..17`。
- **`Grok` 对 `GPT` 推荐线路的分析**：
  - **赞成写入 charter：四层不可互换；每 AP 明列最低层；waiver 由 owner 或指定治理角色批准，记录 affected Truth/AP/gate、理由、到期与 reopen。**
  - **赞成禁止 waiver 覆盖 `T-O-376/378/381/383`。** 环境问题可以延期 L3，但不能把 monkeypatch 成功写成 live。
  - **赞成 `.experiment` 不入四层。**
  - 补充：waiver 不能把某格的 L3 改写成「L1 已足够」；只能 **延期** 并到期 reopen。修改测试期待值掩盖 S1 = `FG-NH-17` 失败。
- **`Grok` 的最终建议**：
  **确认把四层不可互换、AP 最低层和 waiver 治理写入 charter**；禁止 waiver 覆盖 foundational completeness；fault/race 不是可替代层。此建议仍不是 Truth。

- **问题**：是否确认charter冻结四层不可互换与AP最低层，fault/race/security非替代层；waiver只能具名延期、不能降层/改期待值，须到期reopen且不得覆盖foundational completeness？
- **业主回答**：🔒 **FROZEN**：L1 unit、L2 integration/UoW、L3 default-root e2e、L4 retrieval-facet mega 不可互换并进入 charter，每 AP 锁最低层；fault/race/security 非替代层；waiver 仅具名延期、不得降层/改期待值，须到期 reopen，且不得覆盖 `T-O-376/378/381/383`。→ `T-O-406`

### Q27 — rebuild / changed-metadata 是否彻底跳过 decode+clean（gate：`G-NH-19`；来源：proposed §8、RA07/08）

- **影响范围**：intake.rebuild；intake.update_metadata；accepted clean artifact；S05 lineage；Revision/generation；API Item lifecycle；`M-NH-09`；`AP-NH5/NH8/NH9`。
- **为什么必须确认**：HEAD rebuild/changed-metadata 从 frozen accepted clean 读取，但仍走 inline decode + `clean.extract.deterministic`，可能再次归一化字节并换掉原 strategy（`src/runtime/intake/acquisition_intents.py:25-93`; `src/runtime/intake/clean_preflight.py:28-127`; `NH-RA08-B04`）。这与“复用 exact admitted clean”和绑定后不热切存在直接张力。
- **当前建议 / 倾向**（`GPT` · post-second-opinion/code-review）：rebuild 与 changed-metadata 通过既有 registered intent guard 从图上真正旁路 acquire/decode/clean，直接引用 frozen admitted-clean artifact/digest；禁止新增 no-op/deterministic clean worker冒充 skip。changed metadata 继续跳 structurize、复用 summaries，只重做消费新 semantics 的 construct/projection/publication。新 cleaner 只用于未来新 ingest；已有对象 upgrade 服从 Q21，NH v1 默认不借 rebuild 偷换。
- **Reasoning**：
  1. frozen clean 已是已接受事实，再跑任何 cleaner 即使声称 deterministic，也可能因代码/contract升级改变字节。
  2. 跳过 Process 比“运行 no-op 后断言 byte-equal”更简单、可审计，也不会错误记录成原 source worker的新 actual binding。
  3. metadata change 的目标是语义账变更，不是正文重洗；现有 skip structurize/reuse summaries 已证明可以复用生成资产。
  4. NH v1 的新 clean 只用于未来新 ingest；已有对象 re-clean 目前无合法 command，按 Q21 暂不支持，不能借 rebuild/no-op worker 偷换。

- **`Grok` 的问题分解**：
  1. 产品张力：rebuild 的业务输入已经是 accepted clean artifact（`acquisition_intents.py:33-54` 明确「不是第二次外源获取」），但图仍 `acquire.to_decode`（priority 10，`lsrag_definition.py:299-306`），`_clean` 无 rebuild 短路并 `dispatch_clean`（`clean_preflight.py:28-127`）。changed-metadata 复用 `_acquire_rebuild`（`acquisition_intents.py:207-214`）。
  2. 即便声称 deterministic，代码/canonicalizer 升级也会改字节，从而换掉 admitted clean digest 与策略身份。这与 `T-O-383` 绑定后不热切、面 08 `NH-RA08-B04` 直接冲突。
  3. HEAD 已有 `registered_request_intent` 守卫闭集（`models.py:264-271`）和 metadata `no_change` 短路。**跳过 decode+clean 可以用已有 intent guard 画边**，不必发明 no-op clean worker——后者仍会留下「又跑了一次 clean」的 actual/process_key。
  4. 真正需要新 cleaner 时，必须走 Q21 的显式新 ingest/upgrade，获得新 policy/actual/PromptRef。
- **`Grok` 对 `GPT` 推荐线路的分析**：
  - **赞成彻底跳过 acquire-decode-clean Process 链**，直接引用 frozen admitted-clean artifact/digest 作为新 generation/Revision 的正文输入。比「跑 no-op 再断言 byte-equal」更可审计，也不会给源通道工人写新 actual。
  - **赞成 changed-metadata 继续跳 structurize、复用 summaries**，只重做消费新 semantics 的 construct/projection/publication。
  - **赞成禁止借 rebuild 偷换 cleaner。**
  - **实现偏好**（执行意见，不锁 step_key）：用已登记 `registered_request_intent` 守卫把 rebuild/changed-metadata 从 decode/clean 旁路到后续阶段，而不是新增一个声称 deterministic 的 clean PROCESS。这比 GPT 字面「跳过 Process 链」更贴合现七表。
- **`Grok` 的最终建议**：
  **确认 rebuild 与 changed-metadata 均不再执行任何 acquire/decode/clean Process**，只 replay frozen admitted-clean artifact/digest；需要新 cleaner 必须显式新 ingest/upgrade。实现上优先用已有 intent guard 旁路，禁止 no-op clean 冒充 skip。此建议仍不是 Truth。

- **问题**：是否确认 rebuild/changed-metadata 以 registered intent guard 真正旁路 acquire/decode/clean，禁止no-op cleaner，只replay frozen clean；changed metadata仅重做semantic consumers，新 cleaner只影响未来ingest，已有对象upgrade按Q21另裁？
- **业主回答**：🔒 **FROZEN**：rebuild/changed-metadata 以 registered intent guard 真正旁路 acquire/decode/clean，禁止 no-op cleaner，只 replay frozen admitted clean；changed metadata 仅重做 semantic consumers；新 cleaner 只影响未来新 ingest，已有对象 upgrade 服从 `T-O-401`。→ `T-O-407`

---


## 5. ★ Truth-Gate 台账（frozen · owner-gated execution truth · 供 planning-final §2 CITE）`[核心]`

> **已冻结（2026-08-29）**。owner 整包接受 GPT v0.3 post-second-opinion 推荐；Q10–Q27 逐题答案已压成 `T-O-390..407` 的下游唯一口径。ID append-only、不回收；推翻须本文件追加修订和新 Truth。

| Truth-ID | 子类型 | 已锁定真相（一句话 · 下游唯一口径） | 来源 Q | 下游约束 |
|---|---|---|---|---|
| `T-O-390` | `execution / two-stage-s05-schema` | S05 policy/actual 分账：旧 `s05_binding_digest` 从新 domain/wire/传播链逻辑隔离、不得 backfill actual；Execution 新 nullable actual digest/state/seal generation 是 sealed-once 快速 SSOT，typed history 只供明细；物理 rename/retire 待兼容证明。 | `[Q10]` | planning-final §2；`M-NH-01`; AP-NH1/NH3；S05/D04/glossary calibration |
| `T-O-391` | `execution / selected-output-merge` | v1 使用 registered selected-output CONTROL：optional candidate ports，只投影 durable selection，不重跑 guard/等待未 materialize 分支/复用 scatter；exactly-one，零/双命中 fail-loud，登记 fallback/version 入 compiled digest。 | `[Q11]` | planning-final §6/§7；AP-NH1/NH2 |
| `T-O-392` | `execution / representation-authority` | Typed append-only RepresentationFact/AcquireDecodeHistory rows 是唯一权威，与对应 Process Outcome 同 UoW append；同 step 二次成功拒绝；Process/Snapshot只引用，guard只读注册projection，actual聚合有序history。 | `[Q12]` | `M-NH-02`; AP-NH2/NH3 |
| `T-O-393` | `execution / runtime-boundary` | 以 PromptRef+model identity+inference budget 分界：无prompt本地binary变换走local capability ports，model-bound OCR/Vision/DU走S11 multimodal；共享治理但identity/limit/readiness分账，CLI binary fail-closed，pool数不锁。 | `[Q13]` | AP-NH1/NH6 runtime boundary |
| `T-O-394` | `execution / semantic-authority` | Generic三kind的realm/type/channel/source_name caller必填且非unknown、is_active系统派生；registered_api mapper为SSOT；冲突422、逐字段provenance、禁自动unknown，仅registry明列API可选字段可从frozen record显式携带。 | `[Q14]` | AP-NH5 semantic authority；S04/S06/S10 projection |
| `T-O-395` | `execution / channel-naming` | 新public schema分为semantic_channel与vector_channel；旧schema channel仅对original/summary机械映射并弃用，其它422；新schema禁旧键且不按value猜轴；内部vector列可暂留物理名。 | `[Q15]` | `M-NH-06/08`; retrieval contract |
| `T-O-396` | `execution / public-object-surface` | Public v1仅authenticated upload+stat/status（无path/filename，跨team 403），无raw byte GET；bytes仅供内部local_object ingest，业务artifact read独立，未来导出另reopen。 | `[Q16]` | AP-NH4 public object surface；S13 narrow reopen |
| `T-O-397` | `execution / exhausted-zero` | Registered API合法零集合使用独立exhausted_zero disposition，与metadata no_change分字面；Task技术状态可complete/succeeded但非indexed success，不造child/Revision/vector/proof，须exhaustion proof、retrieval empty和fingerprint replay。 | `[Q17]` | AP-NH7/NH9 zero terminal/metrics |
| `T-O-398` | `execution / workflow-scope` | NH所需selected-output CONTROL、typed fact guard、kind-only resolver、actual seal/compat纳入AP-NH1–NH3；排除通用JOIN/DSL/表达式/loader；NH1证伪即stop/reopen，禁退回duplication。 | `[Q18]` | planning-final scope/DAG；AP-NH1/NH2 |
| `T-O-399` | `execution / native-isolation` | PDF parser/确定性OCR无网isolated subprocess；browser/print hardened non-root隔离且生产禁no-sandbox、走S16 egress；Vision/DU留local inference；pin/SBOM/CVE/负样本/readiness为生产门，豁免仅owner具名。 | `[Q19]` | AP-NH1/NH6 security/deploy；S16 calibration |
| `T-O-400` | `execution / seal-linearization` | Durable facts在先；selected-route Outcome、actual seal CAS与clean eligibility在同一Outcome UoW，commit后dispatch；同seal replay、异route/digest ConflictError；v1禁止route/seal两提交。 | `[Q20]` | `M-NH-01`; W-NH-SEL/SEAL；AP-NH3/NH9 |
| `T-O-401` | `execution / retry-rebuild-upgrade` | Process retry/recovery/resume及同Task full_task retry复制exact workflow/policy/sealed actual；rebuild/metadata只replay frozen clean，index.rebuild不碰S05；existing-object new-cleaner upgrade不在NH v1，新实现仅影响未来ingest，未来支持须新owner-gate。 | `[Q21]` | AP-NH3/NH8；S02/S03/S05 erratum |
| `T-O-402` | `execution / main-text-fact` | Decode阶段registered deterministic observer产versioned main_text_presence三态并进fact/path digest；仅absent命中已声明browser edge，unknown fail-closed；禁LLM/quality-score路由。 | `[Q22]` | AP-NH2/NH3/NH7 route fact |
| `T-O-403` | `execution / browser-supply` | v1共享hardened browser binary/navigation/egress，但render/print为独立capability/profile/budget/readiness/evidence并分别验DOM/PDF；淘汰常量profile；部署可拆实例而不改合同。 | `[Q23]` | AP-NH6 browser/print supply |
| `T-O-404` | `execution / upload-transaction` | 返回usable handle前同UoW提交catalog+upload_pending live ref/hold；无任一不算成功；ingest转换业务ref，取消/TTL后才grace/GC；未完成流只staging scanner清理，upload不造Item。 | `[Q24]` | `M-NH-05`; AP-NH4/GC；S13 calibration |
| `T-O-405` | `execution / intent-error-contract` | Charter/API冻结七意图applicability与machine-readable code闭集；422请求形状/组合、409状态/并发；非法格admission fail-loud且不建Task/Process，no-op/skip不可顶替，不生造7×4任务。 | `[Q25]` | charter/API；AP-NH8 intent matrix |
| `T-O-406` | `execution / completeness-proof` | L1 unit、L2 integration/UoW、L3 default-root、L4 retrieval-facet不可互换且每AP锁最低层；fault/race/security非替代层；waiver仅具名延期、不得降层/改期待值、须到期reopen且不得覆盖foundational completeness。 | `[Q26]` | charter completeness；全 AP/FG-NH |
| `T-O-407` | `execution / exact-clean-replay` | Rebuild/changed-metadata以registered intent guard旁路acquire/decode/clean，禁no-op cleaner，只replay frozen admitted clean；changed metadata仅重做semantic consumers；新cleaner只影响未来ingest，existing upgrade服从T-O-401。 | `[Q27]` | `M-NH-09`; AP-NH8 exact-clean |

---

## 6. 使用约束

### 6.1 单一真源与回答方式

- Q10–Q27 的 `业主回答` 与 §5 `T-O-390..407` 是本 campaign execution decision 的单一真源；其它文档只引用 `Q编号 + T-O-ID`。
- GPT 推荐与 Grok second opinion 继续保留为 decision record，但不与 owner truth 并列；冲突时以 §5 最新 append-only frozen Truth 为准。
- 本册无部分冻结、无 OPEN gate；planning-final 不得重新选择候选线路，只能按 Truth 落 AP/DAG 或正式 reopen。

### 6.2 Second opinion

- 模式为 `present`。Q10–Q27 每题三个 Grok 槽已由 Grok 于 `2026-08-29` 填入；不得由 GPT/owner 转述或改写后冒充。
- Grok 文本仍不是 owner truth；业主已采用 GPT v0.3 综合方案并逐题写出完整答案，不以“同意某模型”替代合同。

### 6.3 冻结完成记录

1. `[x]` Q10–Q27 owner answer 完整；
2. `[x]` §5 `T-O-390..407` 已删除 RESERVED 并冻结；
3. `[x]` S05/S03/D04/glossary/qna-truth-S05 calibration 及 S13 public-upload、S16 native/browser 窄校准已在同一冻结工作单元登记；
4. `[x]` 文档状态=`frozen`、版本=`v1.0`、日期=`2026-08-29`；
5. `[ ]` `planning-final` §2 CITE 新 Truth、§6/§7 吸收 DAG/AP/DoD——下游待执行；
6. 后续推翻只能在本文件追加修订说明与新 Truth，不在 action-plan 静默改口。

### 6.4 不进入本册的事项

- 具体 `step_key`、predicate 字面、HTTP path/multipart、purpose 字符串、测试文件名、物理 migration 编号；这些在 owner contract 下由 action-plan 决定。
- promptA 三 catalog 的具体 id/正文迁移；这是 known execution item，`G-NH-14` 保持空号。
- `.experiment` 发车日；继续服从 `T-O-380`，不因本册冻结而自动发车。
- live connector/cookie/tunnel、第五 kind、cuts/g0 重开、CF/R2/SMCP 栈；已被 foundational Truth 排除，除非正式 reopen。

---

## 7. 与 proposed-planning 的双向一致性核对（撰稿后）`[核心]`

### 7.1 Gate 覆盖与下游映射

| proposed gate | 本册 Q | frozen Truth | proposed 主 AP / contract | 核对结果 |
|---|---|---|---|---|
| `G-NH-01` | Q10 | `T-O-390` | `M-NH-01`; NH1/NH3 | `一致` |
| `G-NH-02` | Q11 | `T-O-391` | `M-NH-03`; NH1/NH2 | `一致` |
| `G-NH-03` | Q12 | `T-O-392` | `M-NH-02`; NH2/NH3 | `一致` |
| `G-NH-04` | Q13 | `T-O-393` | NH1/NH6 runtime | `一致` |
| `G-NH-05` | Q14 | `T-O-394` | NH5 semantic authority | `一致` |
| `G-NH-06` | Q15 | `T-O-395` | `M-NH-06/08`; NH5 | `一致` |
| `G-NH-07` | Q16 | `T-O-396` | NH4 public surface | `一致` |
| `G-NH-08` | Q17 | `T-O-397` | NH7/NH9 zero terminal | `一致` |
| `G-NH-09` | Q18 | `T-O-398` | planning-final DAG；NH1/NH2 | `一致` |
| `G-NH-10` | Q19 | `T-O-399` | NH1/NH6 security | `一致` |
| `G-NH-11` | Q20 | `T-O-400` | W-NH-SEL/SEAL；NH3 | `一致` |
| `G-NH-12` | Q21 | `T-O-401` | NH3/NH8 restart | `一致` |
| `G-NH-13` | Q22 | `T-O-402` | NH2/NH3/NH7 fact | `一致` |
| `G-NH-15` | Q23 | `T-O-403` | NH6 browser/print | `一致` |
| `G-NH-16` | Q24 | `T-O-404` | `M-NH-05`; NH4/GC | `一致` |
| `G-NH-17` | Q25 | `T-O-405` | NH8 intent/charter | `一致` |
| `G-NH-18` | Q26 | `T-O-406` | all AP/FG-NH/charter | `一致` |
| `G-NH-19` | Q27 | `T-O-407` | `M-NH-09`; NH8 | `一致` |

### 7.2 叙事 / 逻辑冲突审查

| 核对项 | proposed 口径 | 本册口径 | 结果 |
|---|---|---|---|
| planning 冻结零决策 | §8 全 OPEN，不给答案，等待本册 | owner answers 已冻结为 `T-O-390..407`；planning-final 只 CITE | `一致 / gate closed` |
| 治理顺序 | proposed→pre-charter→planning-final→AP；NH1证伪则reopen | §6.3 同顺序；Q18/Q26负责scope/证明治理 | `一致` |
| S05 truth冲突 | planning-final前 append-only repair，NH1验证 | Q10/Q20/Q21共同提供schema/事务/restart答案 | `一致` |
| AP 编号与 DAG | `AP-NH1..NH9`，NH1 chosen-shape validation | 每题影响面与主 AP 对应，不创建 AP-NH0/新相位 | `一致` |
| 已交付勿重做 | 保留 intake、S04/S13、g0/tail/CAS | 推荐均为接线/重 substrate；无 CF/R2/新 kernel 回流 | `一致` |
| 10+3 / 七意图 | legal matrix + exact terminal，非笛卡尔积 | Q17/Q25/Q27分别锁zero、非法格、exact-clean | `一致` |
| 防假绿 | 四层不可互换、FG-NH-01..17 | `T-O-406` 已冻结 charter 化与 waiver 围栏 | `一致 / gate closed` |
| owner-gate 数 | 18；`G-NH-14`空号 | Q10–Q27恰好18题；无新增gate；G-NH-14仍空 | `一致` |
| 实验 | readiness骨架非DoD，发车日OPEN | §6.4继续排除发车 | `一致` |

### 7.3 冻结后的必要回写

- `planning-final` 必须在 §2 CITE `T-O-390..407`；不得重新采用 GPT/Grok 的未冻候选，也不得改变 `T-R` HEAD 事实。
- `T-O-398` 已确认 Workflow substrate 留在 NH，proposed §6 的 NH1–NH3 位置保持；`T-O-390..393/399..403` 冻结 NH1 chosen-shape 与 stop/reopen 条件。
- `T-O-394..397/404..407` 分别冻结 NH4/NH5/NH7/NH8/NH9 的 contract/DoD，planning-final 必须同步更新 AP entry/exit、migration 与测试矩阵，不能只把 §8 标 CLOSED。
- Q21 暴露的 S02/S03 与 S05 §4.6 旧缝已由 `T-O-401` 裁为“existing-object upgrade 不在 NH v1”，并以 append-only calibration 关闭；未来支持必须新 owner-gate。
- 本次冻结未发现 gate 漏项、重复或编号冲突。Grok v0.2 历史意见见 §7.4，GPT v0.3 被接受的综合来源见 §7.5；两节均为 decision record，不是额外 Truth。

### 7.4 Grok 相对 GPT 的收紧 / 分歧（second opinion · 非 Truth）

| Q | 相对 GPT | 一句话 |
|---|---|---|
| Q10 | 收紧 | 同意分账；旧 `s05_binding_digest` 应物理隔离/重命名，传播链 Snapshot/CandidateSet/Gate 一体改 |
| Q11 | 收紧 | 同意 merge CONTROL；**禁止**用 `scatter_children_join` 等待语义；候选端口必须 optional |
| Q12 | 同意 | durable fact/history 行；投影扩 `_typed_route_context_tx` |
| Q13 | 收紧 | 同意分层；用「是否需要 PromptRef+模型预算」分类 OCR，不按「OCR」一词整桶 |
| Q14 | 收紧 | 同意 merge；generic 三 kind 禁止 `unknown` 当缺省/偷懒字面 |
| Q15 | 收紧 | 同意分名；旧 `channel` 只机械映射 `original\|summary`，其它立即 422 |
| Q16–Q18、Q20、Q22–Q26 | 同意 | 主线路与 GPT 同，仅补 HEAD 锚与围栏 |
| Q17 | 收紧 | `WorkflowTerminalKind.NOOP` 仍映射 `succeeded`，必须另有 result disposition |
| Q19 | 收紧 | 生产默认禁止 browser `--no-sandbox`；parser 无网 / browser 受控 egress 分账 |
| Q21 | **分歧** | HEAD causal restart（新 generation 行）= 同承诺重试，应 **保留** sealed actual；upgrade 必须是显式新 Task，不是「凡新 generation 就清空」 |
| Q27 | 收紧 | 同意 skip clean；实现优先用已有 `registered_request_intent` 旁路，禁止 no-op clean worker 冒充 skip |

### 7.5 GPT post-second-opinion 综合方案（v0.3 · 非 Truth）

| Q | v0.3 吸收结果 | 对 owner answer 的实质变化 |
|---|---|---|
| Q10 | 接受“旧列必须隔离”；新 actual 唯一 SSOT，旧行永久 unverifiable | 冻结逻辑/domain/wire隔离；物理 rename 留 migration 在兼容证明后执行 |
| Q11 | 完整吸收 optional ports、durable selection projection、禁 scatter wait | owner 回答需同时冻结 CONTROL 不是第二决策器 |
| Q12 | 完整吸收 Outcome UoW append | fact/history 不允许事后补写或 S13 JSON 作权威 |
| Q13 | 用 PromptRef/model budget 分类 OCR | pool个数不锁；model-bound OCR归S11，deterministic OCR归local port |
| Q14 | 采用更严格 v1 unknown 法 | generic 四字段 non-unknown必填；API禁自动填空，仅显式registry+frozen-record值 |
| Q15 | 合并“禁止猜轴”与旧合同兼容 | 按request schema/version机械映射旧vector enum，新schema禁旧键 |
| Q16 | 吸收stat闭集、跨team与未来导出reopen | public v1无raw GET，stat不泄path/filename |
| Q17 | 修正原先斜杠歧义 | `exhausted_zero` 与 metadata `no_change` 分字面；NOOP/Task succeeded单独不够 |
| Q18 | 完整吸收有界NH substrate围栏 | 纳入NH不等于通用Workflow重建；NH1证伪即reopen |
| Q19 | 吸收no-sandbox与网络分账 | parser无网、browser受控egress；owner具名豁免 |
| Q20 | 完整吸收单UoW法 | v1拒绝route/seal两提交 |
| Q21 | 修正“new generation”歧义并新增代码审查结论 | 现full_task保留exact actual；已有对象upgrade建议不入NH v1，并修S05 §4.6；若坚持支持须扩scope/DAG |
| Q22 | 吸收decode时机与observer版本 | version进入fact/digest，unknown fail-closed |
| Q23 | 完整吸收共享binary/分capability | render/print独立预算/readiness/evidence，常量profile淘汰 |
| Q24 | 完整吸收原子catalog+pending法 | 无catalog或live ref均不返回usable handle |
| Q25 | 吸收admission即拒绝 | 非法格不建Task/Process，no-op不可顶替 |
| Q26 | 吸收waiver只能延期 | 不能降层或改期待值，必须到期reopen |
| Q27 | 吸收intent-guard旁路 | 禁no-op cleaner；新clean仅未来ingest，existing upgrade交Q21 |

---

## 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|---|---|---|---|
| `v0.1` | `2026-08-29` | GPT | singular pre-charter 初稿：Q10–Q27 全量覆盖 18 gate；逐题 GPT 推荐/support reasoning；保留 Grok 三槽；预留 T-O-390..407；完成 proposed 双向核对 |
| `v0.2` | `2026-08-29` | Grok | 填完 Q10–Q27 三槽 second opinion（HEAD `file:line` + reference-anchor）；§7.4 登记与 GPT 的收紧/分歧；Truth 仍全部 RESERVED；业主回答仍空 |
| `v0.3` | `2026-08-29` | GPT | 全面吸收/辩证处理 Grok 回填并复核 S02/S03/S05/HEAD；更新 Q10–Q27 GPT 推荐与问题；Q21 修正 full_task 继承并建议 NH v1 暂不支持 existing-object upgrade；§7.5 记录当前综合方案；Grok 原文不改 |
| `v1.0` | `2026-08-29` | MKB owner + GPT | owner 整包接受 GPT v0.3；逐题填写 Q10–Q27；冻结 `T-O-390..407`；关闭全部 18 gate；登记 S05/S03/D04/S13/S16/glossary/qna-truth-S05 calibration；交接 planning-final |
