# Nano-Agent 代码审查模板

> 审查对象: MKB new-harvest NH1–NH9 与 CROSS-NH campaign
> 审查类型: mixed
> 审查时间: 2026-08-30
> 审查人: Luna
> 审查范围:
> - src/runtime、src/services、src/contracts、src/workflows、intake、api
> - tests、docs/plan/new-harvest、docs/closure/new-harvest、docs/evidence/new-harvest
> 对照真相:
> - docs/eval/new-harvest/pre-initial-planning-qna.md 的 T-O-376、T-O-378、T-O-381～T-O-407
> - docs/eval/new-harvest/final-execution-plan.md
> - docs/plan/new-harvest/AP-NH1～AP-NH9 与 todo-list.md
> - 九份 AP closure 与 CROSS-NH-campaign.md
> 文档状态: changes-requested

---

## 0. 总结结论

> 核心骨架和若干 happy path 已落地，但策略适用性、实际 S05/fact 权威、registered_api 身份重放、publication 完整性、对象回收以及 L3/L4 证据仍有 blocker；本轮不能关闭。

- **整体判断**：四通道的正常代表路径已经接入工作流和 publication tail，但 NH1–NH9 的完整目标尚未完成，且 closure 对“完成”的证明强度高于当前实现和证据。
- **结论等级**：changes-requested
- **是否允许关闭本轮 review**：no
- **本轮最关键的 1-3 个判断**：
  1. inline、local_object、http_resource、registered_api 都有可运行的正常路径；但不合法的 source-kind、representation、clean-strategy 组合会被静默改走 fallback，不能称为完整的 dynamic late-bind。
  2. actual S05 与 RepresentationFact 虽有正常路径上的 UoW/CAS，但 DDL 与 reader 没有把 sealed-once、append-only、digest 一致性固化；普通内部 SQL 可以改写已 sealed 的实际绑定，检索也没有验证 publication set digest。
  3. 当前绿色测试主要证明精选配置和代表路径；NH1 digest 已在后续提交漂移，NH9 checker 是词法存在性检查，部分 L4 helper 还允许跨 Task fallback，因此不能作为完整 campaign closure 证据。

---

## 1. 审查方法与已核实事实

> 本节记录核查事实和证据边界。最终归因在 §2。

- **对照文档**：
  - docs/eval/new-harvest/pre-initial-planning-qna.md
  - docs/eval/new-harvest/final-execution-plan.md
  - docs/plan/new-harvest/AP-NH1-foundation-contracts-and-proof-baseline.md
  - docs/plan/new-harvest/AP-NH2-workflow-kind-family-and-merge.md
  - docs/plan/new-harvest/AP-NH3-representation-history-and-s05-binding.md
  - docs/plan/new-harvest/AP-NH4-public-upload-and-object-lifecycle.md
  - docs/plan/new-harvest/AP-NH5-semantic-ledger-and-retrieval-facets.md
  - docs/plan/new-harvest/AP-NH6-local-runtime-supply-and-security.md
  - docs/plan/new-harvest/AP-NH7-clean-capability-activation.md
  - docs/plan/new-harvest/AP-NH8-intake-lifecycle-and-compatibility.md
  - docs/plan/new-harvest/AP-NH9-closed-set-assurance.md
  - docs/plan/new-harvest/todo-list.md
  - 九份 AP closure 与 CROSS-NH-campaign.md
- **核查实现**：
  - source contract、strategy registry、semantic contract、workflow definitions/registry
  - runtime materialize/core/outcome/scatter 与 intake acquisition/clean/acceptance/vector/index stages
  - actual S05、RepresentationFact/History、upload/GC、retrieval、readiness 的迁移和实现
  - NH1–NH9 专用 unit/integration/e2e/domain tests 与 evidence pack
- **执行过的验证**：
  - git log --reverse --date=iso-strict --pretty=format:'%h %ad %s' -- docs/plan/new-harvest docs/closure/new-harvest src/workflows src/runtime/intake src/runtime/workflow api/public/routes.py
  - git show --stat --oneline 1cdc066 81f1271 b008702 7359a96 76f233b 63c4398 1c74afe be74417 6256a97 27fc3ca 8754df3 50c2246 8196a0a 6390d9b 6fbb1a7 f7db57c a608ea8
  - uv run ruff check api src intake tests/unit tests/integration tests/e2e tests/domain
  - git diff --check
  - uv run pytest -q --tb=short：当前进程退出 0；pytest --collect-only 确认 910 tests collected；末尾有依赖和子进程清理 warning
  - 临时只读 HTTP/DB probe：非法 strategy、metadata system semantic、registered_api replay、sealed actual 直接 UPDATE
  - 临时只读 inference probe：S11 web clean 的 prompt_ref
- **并发对抗审查**：
  - 状态/Schema/业务流转：攻击 actual S05、RepresentationFact、publication proof、lifecycle applicability、内部 DTO。
  - 四通道接线：逐 kind 追踪 admission → acquire/decode → clean → acceptance → S06/S07/S08/S09/S10。
  - declarative workflow：追踪 kind-only resolver、同 revision route/guard、reacquire、CONTROL、compat plan。
  - 竞态/幂等：攻击 CREATE、SEL、SEAL、PROCESS、FANIN、PUB、OUTBOX、PROM-CAT、GC-INGEST 及 cross-task identity。
  - 交付完整性：逐 commit、原 action-plan、closure、evidence、测试节点对账。
- **复用 / 对照的既有审查**：
  - none。既有 reviewer/analysis 报告未作为结论来源；docs/code-review/new-harvest/ 中已有的其他报告未读取、未修改。
  - 五个子代理只被用作独立的只读攻击面扫描；本报告采纳的每一项均由我回到源码、DDL、原始计划或独立 probe 复核。

### 1.1 已确认的正面事实

- NH2 的三张 single-root kind 图和 registered_api 的 root/child scatter 图都能通过 WorkflowDefinition 编译校验；kind-only resolver 根据 source_kind 选择图，caller 不能直接提交 workflow_key。
- kind 图通过 lsrag_shared_tail.py 复用 acceptance、structurize、construct、vectorize、publication 的主体 tail；selected_output CONTROL 的正常 exactly-one projection、UoW 连接和旧 pin 兼容路径存在。
- 正常 single ingest 的 acquire/decode fact、actual S05 seal、clean eligibility 和后续 Process outcome 在正常路径上由同一 Outcome UoW 线性化；同一成功 Outcome 的 terminal replay、普通 Process fence、outbox vector upsert 的效果一次机制存在。
- public upload 走 request.stream、Team 鉴权、CAS digest/size、catalog + upload_pending；上传本身不创建 IntakeItem，随后 local_object ingest 能进入相同的 publication/retrieval 链。
- NH5 的 happy path 已写入 six semantic tuple，facet predicate 位于候选 SQL 的 LIMIT 之前；NH8 的 dedicated tests 已落地 rebuild/metadata exact-clean、lifecycle withdraw/reactivate、delete tombstone 和 index generation 逻辑。
- NH7 的代表性测试确实进行了 namespaced retrieval 和 facet filter；不是所有成功节点都仅靠 Task status 或 publication_ready。
- OOS 围栏总体保持：未发现第五 source kind、R2/CF Browser Rendering、public raw object GET/list/presign、caller workflow_key 或新 upgrade intent 被重新打开。

### 1.2 已确认的负面事实

- public GenericSemanticSource 的 clean_strategy 只校验“十个字面量之一”，不校验 source_kind、实际 media/representation 和 acquire capability 的组合；同一个 invalid request 可 201/succeeded，却实际执行另一个 strategy。
- 020 migration 的 UPDATE trigger 只检查 NEW 行形状，不比较 OLD 行；candidate/snapshot/gate 的 actual state/digest 也没有同等复合约束。019 fact/history 没有数据库级 UPDATE/DELETE 禁止，reader 不重新验证 fact/path digest。
- stage output 对 acquire/decode/clean 仍保留完整 state、raw_text 和 acquisition/decode evidence；这与 NH3 要求的 fact UUID + digest-only、单一 typed authority 不一致。
- publication proof 会保存 required_set_digest 和 actual_set_digest，但 retrieval predicate 只验证坐标、数量和 indexed 状态；没有把 proof 中的 set digest 与当前向量集合重新比较。
- binary source 在 acceptance_snapshot.py 中先作为 Latin-1 transport string，再 encode 成 UTF-8 并标为 text/plain，raw artifact 的字节 digest/size 不再是原始输入。
- registered_api 的 raw_byte_digest 实际是包含 external key/member digest 的逻辑 hash，raw_byte_size 是各 member JSON 长度之和，不是 canonical records bytes 的 SHA-256/字节长度；同 observation key 的第二个 registered_api Task 会返回 201 后失败。
- metadata update 可由 caller 写入 canonical_content、source_representation 和 is_active；实际 probe 观察到 item lifecycle 仍为 active，但最新 Revision 的 is_active=0、source_representation=http_resource、canonical_content=ATTACKER-CONTENT，且 provenance=caller。
- deactivated Item 的 update_metadata 在 action registry 中标为允许，但 acceptance callback 要求 lifecycle_state=active；index.rebuild 对 frozen scope 的 stale target 直接 continue，空 plans 后仍可走成功 no-op。
- web.llm_rewrite 的 S11 入口将 frozen PromptRef 转成 promptA.runtime@v1，并把 inference team 固定为 mkb-runtime-clean；默认配置还启用 DeterministicNs1Stub、关闭 multimodal 和完整 supply readiness。NH7 的 multimodal 正例使用 hard-coded local server。
- NH1 closure 仍声称旧 matrix digest f7199ee…d235c3，而当前 manifest/evidence 已为 57c19c…a740a；后者来自 NH6 对 OCR strategy definition 的修改。PromptA inventory evidence 的 readers 也没有随 eae987c 更新。
- NH9 evidence checker 主要检查字符串、正则、文件存在和 PASS 文本；它不执行 evidence 中的命令，不验证 commit 是否存在/匹配当前文件，也不逐节点核对 query artifact。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | yes | 对照当前 HEAD，引用源码、DDL、测试和 closure 的具体行 |
| 本地命令 / 测试 | yes | ruff、diff check、全量 pytest、定向 pytest 与独立临时 HTTP/DB/inference probe |
| schema / contract 反向校验 | yes | 对照 019/020/021、001 initial schema、Pydantic contract、T-O-390/392/394/400/401/405/407 |
| live / deploy / preview 证据 | no | 没有真实生产 endpoint、部署镜像或 owner sign-off；local fake model 只作为“未达到 live”的证据 |
| 与上游 design / QNA 对账 | yes | 使用冻结 T-O-376、378、381～407；未采用其他 reviewer 的分析报告 |

### 1.4 本轮审查 TODO 与 DAG

本轮采用的执行图如下，D0 完成后并行执行 D1～D5，D6 汇总所有分支，D7 才形成最终 verdict：

| 节点 | 审查任务 | 输出 | 依赖 |
|------|----------|------|------|
| D0 | git history、原 action-plan、todo-list、closure、T-O 真相冻结 | 82 work IDs、10+3、七意图、四通道、九窗口基线 | none |
| D1 | contract/registry/schema | source-kind、strategy、actual/fact、semantic、publication schema 匹配矩阵 | D0 |
| D2 | state/UoW/authority | state machine、sealed-once、append-only、digest 和 propagation 审计 | D0 |
| D3 | 四通道接线 | inline/local/http/registered_api 的 acquire→clean→tail→query 证据 | D0 |
| D4 | declarative dynamic workflow | graph identity、route/guard、reacquire、CONTROL、compat | D0 |
| D5 | race/idempotency | identity replay、retry、GC、crash window、stale scope | D0 |
| D6 | evidence re-execution audit | L1/L2/L3/L4 层级、task scope、commit/time/digest 一致性 | D1～D5 |
| D7 | independent attribution | findings、alignment、OOS、close blockers、follow-up | D6 |

并发子代理使用的专用 prompt 约束是：只读当前 HEAD；先列 file:line 和可复现实验，再给 severity/blocker；必须对照冻结 T-O 和原始 AP；不能读取或采用同事报告；不能修改工作树。五个子代理均返回后关闭。

### 1.5 Git 交付链事实

| AP | 主要实现提交 | closure 提交 | 本轮核对 |
|---|---|---|---|
| NH1 | 1cdc066、87eeadf | ea4ba89 | foundation/shape 成立；T06 model 实弹和 frozen evidence 不完整 |
| NH2 | 81f1271 | afa0807 | kind graph、CONTROL、resolver 成立；策略适用性未闭合 |
| NH3 | b008702 | 1d551a5 | fact/history、actual S05 正常路径成立；schema/transport 权威仍有缺口 |
| NH4 | 7359a96 | b50bd64 | public upload/local ingest/GC 主体成立；orphan/staging/NUL/race 仍有缺口 |
| NH5 | 76f233b | ac929c3 | six tuple/facet 主体成立；metadata system-owned boundary 未封 |
| NH6 | 63c4398 | 19c23db | parser/browser/S11/OCR 供给代码存在；default/full readiness/SBOM/S16 未闭 |
| NH7 | 1c74afe、be74417、6256a97 | c5c8736 | 代表性 10+3 query 存在；strategy、live model、L4 证据不足 |
| NH8 | a575210、27fc3ca | e2fa958 | lifecycle/exact-clean 主路径成立；stale/applicability/replay 仍有边界 |
| NH9 | 8754df3、50c2246、8196a0a、6390d9b、6fbb1a7、f7db57c | 9673704 | campaign fixtures/窗口/pack 存在；完整性证据和部分窗口不够强 |
| CROSS | a608ea8 | a608ea8 | 九包齐全，但 closed-with-explicit-deferrals 不等于本轮完整目标完成 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | strategy applicability 未闭合且实际 worker authority 断裂 | high | correctness / protocol-drift | yes | 建立 admission applicability matrix，禁止非法组合静默 fallback |
| R2 | actual S05 与 RepresentationFact 的 sealed/append-only schema 不足 | critical | correctness | yes | 加 sealed-once、append-only、复合一致性约束和 digest reader fence |
| R3 | stage output 保留 raw/evidence，形成第二表示权威 | high | delivery-gap | yes | 只持久化 fact UUID/digest/typed refs，原始 bytes 留在 CAS |
| R4 | publication set digest 未进入 retrieval fence | high | correctness | yes | retrieval 重算并比对 proof set digest，冻结 indexed 内容字段 |
| R5 | binary raw artifact 被错误重编码 | high | correctness | yes | 原始 bytes 端到端保留并做 round-trip assertion |
| R6 | registered_api 的 raw-byte identity 不是真实 bytes | high | correctness | yes | 分离 observation digest 与 canonical records bytes digest/size |
| R7 | registered_api 同 observation replay 失败并留下业务副作用 | high | correctness | yes | admission/acceptance 以 observation key + digest 做 UoW replay/conflict |
| R8 | metadata 可覆盖 system-owned S04 semantics | high | correctness | yes | 拒绝保留键，system 值从 source/clean/lifecycle 重新派生 |
| R9 | lifecycle applicability 与 stale index scope 会晚失败或静默成功 | high | correctness / protocol-drift | yes | 统一 allowed-from matrix，stale scope typed 409 |
| R10 | retry/outcome/full-task 的 exact replay 法不统一 | high | correctness | yes | retry_wait 同 digest no-op，full retry exact copy 全部 frozen coordinates |
| R11 | CAS orphan、active staging 和 ingest reservation 回收竞态未封闭 | high | security / correctness | yes | 建立 orphan ledger、active lease、ingest reservation 和真实 interleaving |
| R12 | model-bound lane 不是默认 live 且 web PromptRef/tenant provenance 被改写 | high | platform-fitness / protocol-drift | yes | 真实供给、release readiness、complete_bound 和 correlation 全链路 |
| R13 | NH1 frozen matrix/evidence lineage 发生漂移 | high | docs-gap / delivery-gap | yes | 重新冻结或恢复 v1，更新 commit/time/readers，禁止 live registry 重写 baseline |
| R14 | L3/L4、crash、negative、pack checker 证据弱于 DoD | high | test-gap | yes | task-scoped exact assertions，真实中间窗口，checker 执行/核对证据 |
| R15 | upload filename 的 NUL 负例未实现 | medium | security / test-gap | no | URL decode 后拒绝 NUL，补 HTTP negative |
| R16 | 内部 Mapping retrieval v2 与 public typed contract 不一致 | medium | protocol-drift / test-gap | no | 统一 Mapping 与 RetrievalRequest 的 schema-version 分支 |

### R1. strategy applicability 未闭合且实际 worker authority 断裂

- **严重级别**：high
- **类型**：correctness / protocol-drift
- **是否 blocker**：yes
- **事实依据**：
  - src/contracts/api/models.py:37-55 让三个 GenericSemanticSource 都接受同一组十个 clean_strategy；没有 source_kind、media/representation 与 acquire capability 的交叉 validator。
  - src/services/config_snapshots.py:135-152 只按 source_kind resolve workflow，没有在 Task INSERT 前检查 strategy applicability。
  - src/runtime/workflow/runtime_materialize.py:177-204 从 task audit 读取 caller 的 clean_strategy；src/workflows/kind_family.py:317-341、399-410、473-542 对未命中的 guard 仍有 unguarded fallback。
  - src/runtime/intake/clean_preflight.py:54-61 又按 step_key/process_key 反推 strategy；src/runtime/workflow/runtime_outcome.py:450-469 把 fallback target 封存为 actual strategy。
  - 独立 probe：inline source 声明 clean_strategy=pdf.ocr，HTTP 201，Task 最终 succeeded；Execution actual_clean_strategy=doc.deterministic，成功 Process 为 clean.extract.deterministic。
- **为什么重要**：
  - 这不是同一策略的别名，而是调用方请求的 worker 被静默替换；T-O-381/382/384/405 要求合法闭集、绑定前可解释选择、非法组合 fail-loud。
  - 这会让“10 strategies 已接通”变成“10 个字面量可被提交”，并且给后续 S05、evidence、replay 留下错误的实际意图。
- **审查判断**：
  - kind-only graph 本身成立，但 strategy registry 与 graph guard 没有闭合成同一套 applicability authority。当前属于 partial/under-delivered，不可关闭 NH7 和 dynamic workflow 目标。
- **建议修法**：
  - 在 admission 建立由 CLEAN_STRATEGY_DEFINITIONS 生成的 applicability 闭集；已知非法组合在 Task/Process 之前返回稳定 409/422。
  - 未指定 strategy 才允许使用 server-side 默认规则；指定 strategy 必须精确满足已观测 representation，不得落到另一条 unguarded fallback。
  - 将 actual clean step/process/strategy 作为 command 可验证的 frozen authority；新路径禁止只靠 process→strategy 反推。补 inline、local image/PDF、HTTP PDF/browser 的 cross-kind negative matrix。

### R2. actual S05 与 RepresentationFact 的 sealed/append-only schema 不足

- **严重级别**：critical
- **类型**：correctness
- **是否 blocker**：yes
- **事实依据**：
  - src/persistence/migrations/020_nh3_actual_s05_binding.sql:36-53 的 UPDATE trigger 只检查 NEW 是否满足 sealed 或 unsealed 形状，没有 OLD.actual_binding_state/OLD.digest 的 sealed-once 条件。
  - 同一 migration:55-71 给 candidate set、snapshot、gate 加的 actual 字段没有 sealed ⇒ digest 的复合约束；只有 executions 有形状 trigger。
  - 019 migration:5-68 没有 fact/history 的数据库级 UPDATE/DELETE 防护；src/runtime/intake/representation_history.py:172-195 的 reader 直接读取最新 fact/history 关联字段，不验证 fact_digest、representation_path_digest 与字段内容重新计算后一致。
  - representation_path_digest 在 src/runtime/intake/representation_history.py:42-57 中没有纳入 main_text_presence；两个 route-relevant observation 只要其余字段相同，可能得到同一路径 digest。
  - 独立 probe 对已完成 Execution 执行普通 UPDATE，将 actual_binding_digest 改成 64 个 f、route 改成 64 个 e、seal_generation 改成 7，事务成功，行仍为 sealed。
- **为什么重要**：
  - T-O-390/392/400 把 actual 和 typed facts 定义为不可回写的权威坐标；只靠当前 Python helper 的 CAS 不能保证维护 SQL、修复脚本或故障注入不能改写 truth。
  - fact 被改写后，guard 会读取伪造的 representation；actual path digest 也可能与实际 observation 不同。
- **审查判断**：
  - 正常应用调用路径有 CAS，不足以抵消 schema 与 reader 的可写后门。NH3 state mechanism 和数据库 schema matching 仍是 critical partial。
- **建议修法**：
  - executions 的 trigger 只允许 unsealed/null/generation=0 一次性转为完整 sealed，任何 OLD sealed 的 actual 字段变化直接 abort；generation 使用精确闭集。
  - 对 candidate/snapshot/gate 增加同等复合约束或改为不可变 projection 表；补 team/execution/process 的复合外键。
  - facts/history 加 append-only triggers、digest revalidation 和 corruption fail-closed，并把 route-relevant typed observation 字段纳入 path digest；readiness 必须校验 migrations、columns、indexes、views、triggers，而不是只查 migration ledger。

### R3. stage output 保留 raw/evidence，形成第二表示权威

- **严重级别**：high
- **类型**：delivery-gap
- **是否 blocker**：yes
- **事实依据**：
  - AP-NH3:198-200、244-249 要求 RepresentationFact/History 为唯一 authority，Process output/Snapshot 只保存 fact UUID + digest。
  - src/runtime/intake/acquisition_ingest.py:88-127 把 raw_text、raw_byte digest、acquisition_evidence、decode state 写进 state；src/runtime/intake/core.py:404-423 生成 stage envelope。
  - src/runtime/intake/core.py:426-440 只对 lsrag.vectorize、index.validate_publication、index.rebuild 删除 raw_text 等字段；acquire/decode/clean 的 envelope 仍携带完整 state/evidence。
  - stage output 通过 OutcomeArtifactCommitter 进入 CAS；因此它不是 Python 临时变量，而是持久化的第二份表示事实。
- **为什么重要**：
  - 事实行与 stage JSON 的字段可以在不同 UoW、不同重放路径产生偏差；后续代码只要读 envelope，就绕过了 NH3 声称的 typed append-only authority。
  - raw body 被重复放入 process_io 对象，扩大保留面，也使 crash/retry 不能只通过 UUID/digest 重建。
- **审查判断**：
  - 当前 route reader 主要读 durable fact，但 clean/acceptance 仍消费 stage state，故 fact sole authority 未真正落地。
- **建议修法**：
  - stage envelope 只保存 typed fact references、raw/clean CAS handle+digest、representation path digest 和必要的 bounded state。
  - 后续 stage 通过 team-scoped CAS + fact reader 读取，禁止将完整 RepresentationObservation、raw_text 和重复 evidence 写进 acquire/decode/clean output。
  - 增加 source scan 和 round-trip test，断言每个 Process output 的 state 不含原始正文且只含 fact UUID/digest。

### R4. publication set digest 未进入 retrieval fence

- **严重级别**：high
- **类型**：correctness
- **是否 blocker**：yes
- **事实依据**：
  - src/runtime/intake/vector_publish_commit.py:38-80 计算并写入 required_set_digest/actual_set_digest，发布前仅在本次 callback 内比较 fetched set 与 expected set。
  - src/services/retrieval/models.py:71-86 的 proof predicate 是按完整坐标计数 indexed vector；src/services/retrieval/retrieval_rank.py:68-70 只要求 expected_count=actual_count=matched_count，再套该计数 predicate。
  - retrieval SQL 没有重算当前 vector_record_uuid + content_digest 集合并与 proof.required_set_digest 或 proof.actual_set_digest 比较；mkb_vector_records 也没有禁止 indexed 行的 content_digest 变更。
  - 独立攻击路径：发布后把一条 indexed vector 的 content_digest 改成另一合法 64-hex、保持数量和坐标不变，retrieval 仍可 200/ok。
- **为什么重要**：
  - proof 表示的集合和当前可见的向量集合可能已经不同，但 S10 仍会 hydrate stale/不对应 clean digest 的正文；这直接削弱 NH7-10/NH9-08 的 publication fence。
- **审查判断**：
  - 发布时校验过不等于读取时仍是同一集合。当前证明只覆盖 commit window，未覆盖 read-time corruption/TOCTOU。
- **建议修法**：
  - 在 retrieval candidate/revalidation SQL 中计算有界、确定性的 set digest，并与 active proof 的 actual_set_digest 比较；大集合使用登记的 partition/manifest digest，但必须是同一 SSOT。
  - indexed vector 的 content/embedding identity 只能通过新 generation INSERT，禁止原地更新；增加破坏 digest、数量、坐标的负向 query test。

### R5. binary raw artifact 被错误重编码

- **严重级别**：high
- **类型**：correctness
- **是否 blocker**：yes
- **事实依据**：
  - src/runtime/intake/acquisition_ingest.py:734-754 对 binary 使用 Latin-1 transport string 保存 raw_text；这一步便于 clean 阶段恢复原始 bytes，但不应成为 raw artifact bytes。
  - src/runtime/intake/acceptance_snapshot.py:53-70 将 state.raw_text 无条件 encode UTF-8，固定 raw CAS media_type=text/plain；:110-124 和 :238-275 再以该对象登记 raw_acquisition。
  - 独立 PDF probe 观察到原始 PDF 为 626 bytes，acceptance raw acquisition 对象为 655 bytes；RepresentationFact 的原始 digest/size 仍是 626 bytes，fact 与 artifact 不同。
- **为什么重要**：
  - S04 raw artifact、S13 object reference 和 NH3 RepresentationFact 的“原始表示”不再指向同一 bytes；PDF/image/print 的审计、重放和法证读取会得到被重编码的内容。
- **审查判断**：
  - clean 可能仍成功，不能掩盖 source representation 已不诚实；这是实际字节链的 correctness blocker。
- **建议修法**：
  - state 保存原始 CAS handle/digest/size 或显式 bytes coordinate；acceptance 直接引用已校验的原始对象，不把 binary transport string encode 成 UTF-8。
  - raw artifact 的 media_type、digest、size 必须与原始 bytes 一致；为 PDF、PNG、print PDF 增加 source object round-trip test。

### R6. registered_api 的 raw-byte identity 不是真实 bytes

- **严重级别**：high
- **类型**：correctness
- **是否 blocker**：yes
- **事实依据**：
  - src/runtime/intake/acquisition_ingest.py:310-327 为每个 member 生成逻辑 raw_member_digest；:337-349 又把 external key 和 member digest 列表 hash 成 root raw_digest。
  - :349 的 collection_byte_count 是各 member canonical JSON 长度之和，不是 canonical_json(records) 的整体字节长度；:357-368 将 root raw_digest 填入 raw_byte_digest，:413-416 再写入 RepresentationObservation。
  - _acquire 在 :68-69 直接转到 collection handler，src/runtime/intake/acquisition_ingest.py:548-560 那条真实 bytes acquire_content 分支不会为 registered_api 建立这份 fact。
  - src/runtime/intake/acceptance_scatter.py:201-224 将该逻辑 raw_digest 继续作为 raw artifact content_digest。
- **为什么重要**：
  - RepresentationFact 的字段名明确是 raw_byte_digest/raw_byte_size；当前值不对应任何实际 byte stream，不能支持 exact replay、raw audit 或 content integrity。
- **审查判断**：
  - 三个 provider 的 clean/member/query happy path 可以成功，但 registered_api channel 的表示契约 under-delivered。
- **建议修法**：
  - 先对 validated records 形成唯一 canonical_json(records) bytes，使用 SHA-256 和真实 UTF-8 byte length；另设 observation/identity digest 包含 external key、provider、operation、version。
  - raw artifact 的 logical handle/content digest/size 只能引用 canonical records bytes；member digest 保留为 member identity，不冒充 raw bytes。

### R7. registered_api 同 observation replay 失败并留下业务副作用

- **严重级别**：high
- **类型**：correctness
- **是否 blocker**：yes
- **事实依据**：
  - src/runtime/intake/acquisition_ingest.py:442-484 在 callback 中可以找到已有 source，但仍保留 fresh snapshot/candidate/member UUID；src/services/scatter_intake.py:180-203 对 snapshot 使用普通 INSERT，没有按 observation fingerprint 做 replay/conflict。
  - 独立 public HTTP probe：两个不同 task_uuid 使用同 Team、同 external_key、同 provider/operation、同 records；第一 Task succeeded，第二 POST 201 后终态 failed，error 为 INTAKE_SOURCE_MISSING；DB 结果为 source=1、snapshot=1、items=2、revisions=2。
  - NH9 专用 API retrieval 测试每个 team/key 只运行一次，因此未覆盖该路径。
- **为什么重要**：
  - T-O-383 要求同一 intake key + 同 digest replay 原坐标；当前第二次调用不是 replay，而是带失败和残留业务行的 partially admitted operation。
- **审查判断**：
  - registered_api 是第四 intake channel，不能因为三种 operation 的首次 ingest 能检索就视为幂等完成。
- **建议修法**：
  - 在 admission 或 acceptance UoW 锁定 team、source_kind、observation_key、observation_fingerprint；同 digest 返回已有 Snapshot/ChangeSet/member coordinates，禁止新 Item/Revision/artifact；异 digest 返回稳定 ConflictError。
  - 在并发、串行 replay、异 digest、失败回滚四种场景中用 PersistencePort 断言所有 side-effect counts。

### R8. metadata 可覆盖 system-owned S04 semantics

- **严重级别**：high
- **类型**：correctness
- **是否 blocker**：yes
- **事实依据**：
  - src/services/intake_lifecycle/targets.py:215-301 只拒绝 filter_metadata/context_metadata 两个 blob，其他 registered semantic key 均可由 caller 提交；DEFAULT_SEMANTICS 在 src/services/registry.py:229-240 明确注册 source_representation、canonical_content、is_active。
  - src/runtime/intake/acceptance_snapshot.py:641-675 在首次 acceptance 将 source_representation、canonical_content、blob 标成 system；但 src/runtime/intake/acceptance_lifecycle.py:426-493 的 merge/cohere 只重新生成两个 blob，保留 caller 对 source_representation、canonical_content、is_active 的 replacement。
  - 独立 metadata Task probe 成功，最新 semantics 为 canonical_content=ATTACKER-CONTENT、source_representation=http_resource、is_active=0，三者 provenance=caller；Item lifecycle_state 仍为 active。
- **为什么重要**：
  - S04 six tuple、clean identity、source kind 和 lifecycle truth 被分账后又可以被另一个 public intent 重新写成矛盾值。retrieval facet 可能把 active Item 当 inactive，canonical content 也不再等于 clean digest。
- **审查判断**：
  - NH5 T08-A 的 semantic cutover 只证明了正常 realm change；它没有守住 system-owned semantic key 的写权限。
- **建议修法**：
  - 以 reserved/system-owned key set 拒绝 public metadata replacement；source_representation 从 source kind/fact 派生，canonical_content 从 retained clean artifact digest 派生，is_active 只由 lifecycle transition 派生。
  - 增加 caller 试写每个 system key 的 admission negative；检查 latest Revision、Item lifecycle、vector facets、g0 clean 四者一致。

### R9. lifecycle applicability 与 stale index scope 会晚失败或静默成功

- **严重级别**：high
- **类型**：correctness / protocol-drift
- **是否 blocker**：yes
- **事实依据**：
  - src/services/registry.py:214-227 将 update_metadata 的 allowed_from_mask 登记为 active|deactivated；src/services/intake_lifecycle/targets.py:156-169 只在 deleted 时拒绝目标。
  - src/runtime/intake/acceptance_lifecycle.py:190-202 的 metadata callback 却要求 item.lifecycle_state == active；因此 deactivated metadata request 可以先创建 Task，随后以 METADATA_TARGET_STALE 失败。
  - src/runtime/intake/index_rebuild_plan.py:245-265 对 scope freeze 后 lifecycle/revision/serving 不再匹配的 target 直接 continue；src/runtime/intake/index_rebuild_commit.py:22-32 对 empty plans 直接 return。结果可把一个原本非空、后来 stale 的 scope 作为成功 no-op。
  - lifecycle_apply.py:231-246 对重复 deactivate/reactivate 有 success no-op 分支；当前没有将这一状态语义逐项写入 NH8 applicability evidence。
- **为什么重要**：
  - 同一业务 action 在 registry、admission、callback 三处有不同允许集；stale target 被漏掉时又缺少 requested-vs-processed accounting。客户端会看到成功，却没有得到请求的 state transition/index rebuild。
- **审查判断**：
  - NH8 的正常 lifecycle happy path 成立，但业务状态流转的边界和并发语义不闭合。
- **建议修法**：
  - 由单一 applicability matrix 生成 registry、resolver、callback 和 negative tests；明确 deactivated metadata 是合法还是 admission 409，不能登记为允许又在 acceptance 拒绝。
  - index.rebuild 对 frozen target set 做完整 cardinality/CAS；任何 stale target 返回 typed 409 或明确 partial disposition，只有真正空 team scope 才能 no-op success。

### R10. retry/outcome/full-task 的 exact replay 法不统一

- **严重级别**：high
- **类型**：correctness
- **是否 blocker**：yes
- **事实依据**：
  - src/runtime/workflow/runtime_outcome.py:54-60 只对 terminal Process 检查同 digest replay；:147-170 将 retryable outcome 写成 retry_wait 后，重复提交同一 accepted outcome 会落到 process-not-running，而不是 no-op。
  - src/runtime/task/task_commands.py:293-318 复制 full_task generation 时将 s05_binding_digest 写成 previous.domain_binding_digest，而不是原 generation 的物理兼容 alias；同时没有传递 task_create.py:206-211 写入的 payload_extra.metadata_disposition。
  - AP-NH3:227、T-O-401 要求 full_task exact copy workflow/policy/sealed actual/selected process/intent context；现有测试主要证明 current old execution 可运行，没有覆盖上述 retry copy。
- **为什么重要**：
  - crash-after-commit-before-response 可以产生 retryable outcome redelivery；拒绝同 digest 会把已经接受的结果变成错误告警。
  - old pin 的第二 generation 不是 exact reproduction，metadata route 也可能因 disposition 丢失重新落到 acquire 路径。
- **审查判断**：
  - 正常 success outcome replay 和 actual 字段复制部分成立，但全套 replay law 仍是 partial。
- **建议修法**：
  - 对 running、retry_wait、terminal 等所有已接受 outcome 状态按 digest 做同/异结果分流；同 digest no-op，异 digest typed conflict。
  - full_task 复制完整 frozen execution row，包括 legacy policy alias、actual selection、payload_extra 和 intent context；补 historical pin、metadata retry、crash-before-response 测试。

### R11. CAS orphan、active staging 和 ingest reservation 回收竞态未封闭

- **严重级别**：high
- **类型**：security / correctness
- **是否 blocker**：yes
- **事实依据**：
  - src/services/object_upload.py:55-64 先 promote final CAS，再检查 Team 和写 catalog/pending；src/services/artifacts.py:73-95 也先 promote stage output/proof，再等 Outcome UoW catalog。
  - src/services/object_gc.py:145-164 只从 mkb_stored_objects catalog 行收集候选；src/persistence/migrations/021_nh4_upload_pending.sql:55-64 的 orphan view 也只看 catalog。没有 catalog 的 final CAS 文件不会进入 GC。
  - tests/integration/test_nh4_upload_uow.py:151-160 明确观察到 rollback 后 catalog/ref 为零但 final CAS 文件仍存在；该测试把它称为 GC-reapable，但当前 GC 查询无法发现该对象。
  - src/storage/local_store.py:81-114 写 staging 时不持有 write lock；:228-244 的 reaper 只按 mtime 删除，没有 active upload marker/lease。src/runtime/intake/acquisition_ingest.py:706-732 的 live-local-object 检查结束后，:533-535 才 read_verified，期间没有 ingest reservation。
- **为什么重要**：
  - failed upload/outcome 会造成无限期 final object；慢 stream 可能被 staging reaper 删除；pending TTL 释放后，GC 可在 local_object 读和 acceptance 之间 quarantine/delete，导致合法 ingest 非确定失败。
- **审查判断**：
  - digest、pending、quarantine restore 的局部测试通过，但“所有 orphan 可回收、所有 in-flight bytes 受保护”的 NH4/NH9 race DoD 未成立。
- **建议修法**：
  - 建立 pre-catalog orphan ledger 或带状态/lease 的 staging-to-final 生命周期；GC 同时受 ledger 和 grace fence 保护，删除后可证明对象无任何 active owner。
  - upload stream 使用 active lease/touch；local_object 在读取前创建持久化 ingest hold，在 acceptance UoW 原子转 business ref，失败/取消释放。
  - 真正并发暂停在 live check/read/acceptance 之间，运行 TTL + GC，并断言成功 ingest 不丢 bytes。

### R12. model-bound lane 不是默认 live 且 web PromptRef/tenant provenance 被改写

- **严重级别**：high
- **类型**：platform-fitness / protocol-drift
- **是否 blocker**：yes
- **事实依据**：
  - src/runtime/config.py:40-63 默认 live_inference=false、ns1_cli_mode=stub、multimodal_enabled=false、runtime_supply_readiness_required=false；api/app.py:345-352 因此默认 clean_llm=None，:223-253 仅在 readiness_required=true 时 probe parser/browser/OCR/S11。
  - 默认 web.llm 可走 DeterministicNs1Stub；PDF document understanding 的 binary 输入会被 CLI clean 拒绝，doc.vision 在没有 clean_llm 时不可用，web.browser_print_pdf 没有 model supply 时也不能完整完成。
  - NH7 browser test :205-229 明确断言 container 使用 DeterministicNs1Stub；NH7 multimodal tests :63-77 使用 local_multimodal_server，tests/nh6_runtime_support.py:140-176 返回 hard-coded response，不是真实模型部署。
  - intake/web/__init__.py:82-103 调用 llm.complete(prompt=prompt.text)；src/runtime/inference/multimodal.py:66-88 为此合成 promptA.runtime@v1，并固定 team_uuid=mkb-runtime-clean。独立 fake facade probe 得到 prompt_ref=promptA.runtime@v1，而不是 frozen promptA.default@v1。
  - docs/evidence/new-harvest/AP-NH6/security/s16-egress-browser-review.md:3、:16-20 的 owner/reviewer/UTC/decision 仍为空；SBOM 的 s11.multimodal pin sha256 为 null，CVE status 为 weights_pinned_runtime_scan_required_at_deploy。
- **为什么重要**：
  - NH7-03 要求 llm_required strategy 的 PromptRef 与 frozen pointer 同一 identity；当前 evidence 可以写 promptA.default，但实际 S11 request 使用另一个 identity，且 invocation tenant 不能回溯真实 Team/Task。
  - 10+3 live-to-query 不能由 stub/fake endpoint 和关闭的 readiness gate 证明。缺少实际 release profile 时，四通道中 model-bound lanes 仍是 conditional wiring。
- **审查判断**：
  - 端口和 adapter 形状已落地，实际生产供给和身份/审计链未完成。NH6、NH7 的 closure 只能是 partial。
- **建议修法**：
  - 提供明确 new-harvest production profile：真实 parser/browser/OCR/S11 在场、model/image digest/SBOM/CVE report 完整，缺任一项时 /ready fail-closed。
  - web clean 使用带 team/task/execution correlation 的 complete_bound，传入冻结 CleanPrompt，不得合成 runtime prompt id；CLI subprocess 也要把 prompt identity 纳入可验证 evidence。
  - 只有真实 model endpoint 的 binary/text request、inference ledger 和 readiness probe 全部通过后，才能把相应 legal cell 标 L3/L4。

### R13. NH1 frozen matrix/evidence lineage 发生漂移

- **严重级别**：high
- **类型**：docs-gap / delivery-gap
- **是否 blocker**：yes
- **事实依据**：
  - git show 1cdc066 的 tests/fixtures/new_harvest/closed_set_manifest.v1.json digest 为 f7199ee795fabfe332ad1eadd024debe3633fad1d664349763903dc9f8d235c3。
  - git show 63c4398 修改 pdf.ocr/doc.ocr 的 llm_required 和 prompt 字段，并将当前 manifest digest 改为 57c19c6bcb1c4b82bb741886808b8f3b342259aa795dbaae8b285140e1da740a。
  - docs/closure/new-harvest/AP-NH1-foundation-contracts-and-proof-baseline.md:31-39 仍以 1cdc066 和旧 f7199ee…d235c3 作为 NH1-07 closure claim；docs/evidence/new-harvest/AP-NH1/manifest.json:5-8 的 implementation commits 也只有 NH1 commits，但 :44 已填写后续 digest，:45 observation time 仍早于 NH6。
  - eae987c 只修改 tests/unit/test_nh1_denominator_inventory.py:33-50 的 readers；docs/evidence/new-harvest/AP-NH1/queries/promptA-inventory.json:6-24 仍保留旧 readers。
  - tests/unit/test_nh9_closed_set_manifest.py:35-41 从当前 live registry 重新生成并比较 on-disk manifest，没有与不可变的 NH1 baseline 比较。
- **为什么重要**：
  - closed-set digest 是分母和 compatibility 的证据，不是可随下游实现直接改写的期望值。当前无法判断这是合法 re-freeze 还是未声明的 scope drift。
- **审查判断**：
  - 至少 NH1-07、NH1-08、NH9-T01、CROSS-NH evidence 应为 partial/stale，而不是 verified/closed。
- **建议修法**：
  - 选择其一：恢复 NH1 v1 digest 并使 OCR 修正另开明确版本；或由 owner 重新冻结 v2，记录 Truth、commit、time 和影响 AP，重跑 NH2–NH9 受影响矩阵。
  - evidence manifest 的 commit、observed_at、readers 和 digest 必须来自同一执行批次；测试应比较 immutable baseline，而不是用当前 registry 生成自身期望。

### R14. L3/L4、crash、negative、pack checker 证据弱于 DoD

- **严重级别**：high
- **类型**：test-gap
- **是否 blocker**：yes
- **事实依据**：
  - tests/e2e/test_nh1_runtime_smoke.py:62-95 的 binary model case 只构造 Nh1MultimodalProbeRequest 并验证 GenerateRequest 被拒绝，没有调用 adapter/model；但 NH1 closure:36、evidence tests.txt:15-19 把它写为三轮 real smoke。
  - tests/e2e/test_new_harvest_closed_set.py:614-630 只按 cell ID 选 runner 后调用 runner(tmp_path)，runner 不接收/返回 cell identity；多个 lane 只断言 retrieval results 非空。
  - tests/e2e/nh7_publication.py:61-82 将 proofs/pointers 按 Team 计数，artifact 不属于当前 task 时 fallback 到该 Team 任意 artifact；:136-144 在 g0 body 缺失时允许用 admitted clean 代替。
  - tests/e2e/test_nh7_failure_zero_vector.py:185-216、:219-286 主要查 422/status/vector count，未对每种失败做 namespaced search；tests/e2e/test_nh7_empty_clean_zero_vector.py:16-82 没有 search。
  - tests/e2e/test_new_harvest_crash_windows.py:251-323 的 W-NH-PUB 是正常发布后手工 UPDATE publication_proofs.actual_count，不是 publication commit 中间 crash；docs/evidence/new-harvest/AP-NH9/queries/crash-windows.json:14-18 只有四个 node 名称，却宣称九窗口。
  - tests/domain/test_nh9_evidence_pack_checker.py:37-82 只检查 SHA/UTC/Test-ID/PASS 字符串；:77 甚至把 sqlite3 作为 required evidence 字符串，不能证明禁止路径不存在。generate_closed_set_manifest.py:16-26 硬编码各 AP work count，不能从九份 action-plan 反向验证 traceability。
  - tests/e2e/test_registered_api_scatter.py:334 仍使用 publication_ready，:528 仍通过替换 handler 注入失败；NH9 虽明确把它排除在 T07 主证据外，但 todo-list.md:100-104 仍把 CROSS-NH-TEST/CLOSE 全部标成 [x]。
- **为什么重要**：
  - 910 tests 全部通过只代表当前测试断言通过，不能替代每个 legal cell 的 exact strategy、actual seal、g0、proof、facet、query 和 failure-zero 证明。
  - 这些 helper 的 fallback 会把“某 Team 有证据”误当作“当前 Task 有证据”，隐藏错误关联；手工损坏 proof 也不等于真实 crash window。
- **审查判断**：
  - campaign 的测试质量和 closure checker 低于 final execution plan §9.1、§9.2、§9.3 与 T-O-406；NH7/NH9/CROSS 不可仅据此关闭。
- **建议修法**：
  - 每个 legal cell runner 显式返回 task/execution/strategy/route and query coordinates；断言实际 strategy 与 manifest cell 一致，proof/pointer/artifact 全部 task-scoped。
  - 失败格在每个 scenario 后执行 namespaced search 和 indexed vector count；禁止 status、publication_ready 或同 Team artifact fallback。
  - 在真正的 Outcome/publish UoW 内增加 fault hook，覆盖 crash 前后；checker 解析命令、执行或校验真实 result file、验证 commit/tree/digest/time 四元组。

### R15. upload filename 的 NUL 负例未实现

- **严重级别**：medium
- **类型**：security / test-gap
- **是否 blocker**：no
- **事实依据**：
  - AP-NH4:239、:423 要求 Content-Disposition filename 含 NUL 时返回 SEC_PATH_REJECTED 422。
  - api/public/routes.py:100-105 URL-decode 后只扫描 ..、/、反斜杠，没有检查 NUL。
  - tests/e2e/test_nh4_upload_security.py:19-36 只覆盖 traversal、Windows path 和 percent-encoded traversal，没有 NUL。
- **为什么重要**：
  - 当前 NUL 不会进入 CAS path，但已明确违反 NH4 security contract，且未来 filename 日志/adapter 使用可能重新引入边界风险。
- **审查判断**：
  - 非本轮主要 blocker，但 NH4-08 不能称攻击矩阵完整。
- **建议修法**：
  - decoded Content-Disposition 和 filename parser 对 NUL、控制字符、绝对路径统一拒绝；补 %00 HTTP test 并断言不产生 catalog/file。

### R16. 内部 Mapping retrieval v2 与 public typed contract 不一致

- **严重级别**：medium
- **类型**：protocol-drift / test-gap
- **是否 blocker**：no
- **事实依据**：
  - src/contracts/api/models.py:502-544 和 parse_retrieval_request 支持 mkb.retrieval.v1/v2。
  - src/services/retrieval/retrieval_request.py:196-220 在 request 是 Mapping 时仍只接受 schema_version=mkb.retrieval.v1；typed RetrievalRequest v2 则可通过。
  - 同方法对 malformed v2 is_active list 可能在 value in {0,1} 处泄出裸 TypeError，而不是稳定 RETRIEVE_FILTER_INVALID。
- **为什么重要**：
  - internal service callers、recovery tools 或 tests 若走 Mapping，会得到与 public HTTP parser 不一致的 schema behavior；这破坏 NH5 channel split 的同一合同。
- **审查判断**：
  - public route 当前大多被 parse_retrieval_request 遮蔽，故不是本轮关闭 blocker，但属于接口 contract drift。
- **建议修法**：
  - Mapping 和 typed model 共用一个 schema-version normalizer；对所有 filter value 先做 type guard，再返回稳定 typed error。

---

## 3. In-Scope 逐项对齐审核

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| S1 | NH1 foundation contracts、denominator、CONTROL/S05/runtime smoke、evidence pack | partial | CONTROL/S05 shape 成立；T06 model 只是 request shape，matrix/evidence digest 后续漂移 |
| S2 | NH2 selected-output、三张 kind graph、kind-only resolver、old pin | done | 本 AP 的 bounded substrate 与兼容围栏成立；动态策略适用性另由 R1 阻断 |
| S3 | NH3 fact/history、honest representation、reacquire、actual S05、full replay | partial | 正常 UoW/CAS 成立；R2/R3/R5 和 R10 未满足 sole authority/exact replay |
| S4 | NH4 public upload、local_object handoff、catalog/pending、GC/race/security | partial | 首次 upload/handoff/GC 主体成立；R11 orphan/lease，R15 NUL 未闭 |
| S5 | NH5 four-kind six tuple、S06 overlay、v2 facet SQL、metadata cutover | partial | happy path facet 成立；R8 允许 caller 污染 system semantics |
| S6 | NH6 parser/browser/print/OCR/S11、readiness/SBOM/S16 | partial | 端口和 isolation code 存在；R12 说明默认/部署供给、SBOM 和签收未完成 |
| S7 | NH7 10 strategies + 3 operations live-to-retrieval | partial | 代表性 query 存在；R1、R6、R12、R14 使全部 actual/10+3 不成立 |
| S8 | NH8 seven intent applicability、exact-clean、lifecycle/index/API Item、compat | partial | exact-clean/正常 lifecycle 通过；R7/R9/R10 和未逐格 illegal tests 留下断点 |
| S9 | NH9 82 work IDs、9 windows、zero/replay/security/evidence pack | partial | fixture 和部分窗口有；R4、R7、R10、R11、R14 使 capstone 不能完整收口 |
| S10 | CROSS-NH 九 AP join、full regression、T-O drift=none | partial | 九包存在且当前全量测试退出 0，但 R13/R14 证明 drift/证据强度不足；closure 的 closed-with-explicit-deferrals 不是 complete |
| S11 | 四通道实际接线：inline/local/http/registered_api | partial | 四个正常代表 path 均存在；每个 channel 都有 R1、R5、R6、R7、R11、R12 的实际或证据限制 |
| S12 | 声明式 dynamic workflows 接管四通道路由 | partial | kind graph、guards、reacquire、shared tail 已接入；strategy legality/actual authority 仍由 caller audit + fallback/process map 断裂 |
| S13 | 接线所需竞态、错误、幂等机制 | partial | task/process/normal upload 局部 CAS 成立；cross-observation replay、retry_wait、full_task、GC/stale index 仍有问题 |
| S14 | raw GET/list/presign、第五 kind、R2/CF、upgrade、experiment 等冻结 OOS | out-of-scope-by-design | 本轮未把这些 deferred/OOS 项误报成 NH1–NH9 缺陷；experiment 仍不进 DoD |

### 3.1 四通道逐项判断

| 通道 | 当前真实接线 | 结论 |
|------|--------------|------|
| inline_payload | Task admission stage → inline acquire → text decode → deterministic clean → shared tail → namespaced query | 正常 doc.deterministic path done；跨 strategy 非法组合会被静默 fallback，整体 partial |
| local_object | public objects:upload → catalog/upload_pending → local_object acquire → PDF/image/doc clean → shared tail | upload/handoff 与代表性 PDF/OCR/DU/Vision path 存在；binary raw、GC lease、默认 model 仍 partial |
| http_resource | static → optional declared browser reacquire → browser DOM/print PDF/PDF decode → web/pdf clean → shared tail | graph edges 和真实 browser/print fixture 存在；default/live model、PromptRef/tenant identity、raw evidence partial |
| registered_api | typed provider/operation → scatter root acquire/map/seal → child LS-RAG tail → member query | 三 operation 首次 ingest/query done；raw byte fact、同 key replay、nonempty missing exhaustion admission partial |

### 3.2 dynamic workflow 逐项判断

- 已成立：WorkflowDefinition 对 step/route/guard/binding 做 unique、reachable、acyclic、terminal coverage；source_kind resolver 选择三张 kind root，registered_api 保持 scatter root+child；HTTP graph 声明 static/browser/print 的前向边；selected_output 不等待 sibling、不重跑 guard。
- 未完全成立：clean strategy 由 caller audit 的字符串参与 route context，graph 未对未声明/非法 strategy 区分；clean worker 又按 step map 反推，actual S05 的 selected strategy 没进入 ProcessCommand 可验证面。见 R1。
- 兼容保留不判缺陷：builtin_lsrag.py:42-52 和 api/app.py:424-429 保留旧 profile/compat definitions，是 T-O-398/T-O-401 的 old-pin 设计；只要 public resolver 不选它们，不构成第五图或 profile selector 回流。
- registered_api 的 child graph 不要求与三张 single kind graph 共享同一 tail；T-O-387 明确保留 scatter root+child，故不把 handler-owned fan-out 本身误报为 dynamic workflow 缺陷。

### 3.3 对当前全量测试的解释

当前全量 pytest 退出 0，且收集到 910 个节点；这证明最新提交修复了原 evidence 中记录的历史 namespace/rebuild 红债。但它不改变以下独立事实：R1、R2、R4、R6、R7、R8、R9、R10、R11 是业务/DDL/replay 行为，R13、R14 是证据资格行为，现有 pytest 没有覆盖或没有严密断言这些条件。

**对齐结论**：

- **done**: 1
- **partial**: 12
- **missing**: 0
- **stale**: 0（stale 内容作为 R13 记录在 partial 项内）
- **out-of-scope-by-design**: 1

这更像“kind/workflow 骨架和正常 vertical 已完成，但实际 authority、cross-channel legality、生产 supply 与 closure proof 尚未收口”，而不是 completed。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | raw object GET、object list、presign、R2/Cloudflare remote object adapter | 遵守 | public surface 只有 upload/stat/cancel；没有把下载能力误计入本轮 |
| O2 | 第五 source kind、caller workflow_key、action_branch、generic JOIN/DSL/loader | 遵守 | workflow registry 和 model 的 bounded fence 保持；旧 profile 只是 compat |
| O3 | live connector/cookie/tunnel/provider crawler | 遵守 | registered_api 使用 caller-frozen records；本轮只审 provider mapper/operation/child query |
| O4 | existing-object new-cleaner/validator upgrade | 遵守 | T-O-401/407 明确 OOS；本报告没有将其作为缺陷 |
| O5 | experiment launch_date/scores/0815/vendor score | 遵守 | manifest 与 closure 仍为 null/in_closure_join=false；没有要求它成为 DoD |
| O6 | S16 browser egress human sign-off、multimodal deploy image digest | 部分违反 | 它们不是 OOS，而是 NH6 deferred delivery gate；空签收和 null image sha256 不能标 verified，见 R12 |
| O7 | 旧 profile definitions 和 scatter child 独立 graph | 遵守 | 这是兼容/散列设计；本轮只指出新 dynamic path 不能受它们绕过，不要求删除 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：changes-requested。NH1–NH9 的主体工程已经形成：四 kind 正常 path、shared publication tail、actual/fact UoW、upload/local handoff、semantic facet、lifecycle、closed-set 和 crash/race harness 均有代码。但当前至少有策略静默替换、durable state 可改写、publication set fence 缺失、registered_api replay 失败、metadata system semantic 可篡改、对象 orphan/GC 窗口、model supply/PromptRef provenance 和 evidence lineage 等 blocker。
- **是否允许关闭本轮 review**：no
- **关闭前必须完成的 blocker**：
  1. 修复 R1：对四通道建立 machine-generated applicability matrix；非法 strategy/representation/kind 在 admission fail-loud，合法 late-bind 的 actual strategy 与 clean worker 必须同一 authority。
  2. 修复 R2/R3：actual S05、RepresentationFact/History 和 stage output 形成真正的 sealed-once、append-only、UUID/digest-only 权威；readiness 校验所有 NH migrations 的 schema objects。
  3. 修复 R4/R5/R6/R7：publication read fence 验证 set digest；binary raw bytes 保真；registered_api 使用真实 canonical raw bytes，并实现同 observation key+digest replay/异 digest conflict。
  4. 修复 R8/R9/R10：system-owned metadata 禁止 caller 改写；lifecycle/index stale 统一 applicability/CAS；retry_wait/full_task/metadata intent context exact replay。
  5. 修复 R11/R12：对象 orphan/staging/ingest lease race 有持久化保护；建立真实 new-harvest production supply profile，完成 S11 PromptRef/tenant correlation、model image digest/SBOM/CVE 和 S16 owner/reviewer sign-off。
  6. 修复 R13/R14：重新冻结 NH1 matrix/evidence lineage，逐 cell/task 补强 L3/L4、failure query、真实 PUB/GC crash window 和可执行 evidence checker；不能用当前 910 个绿色节点替代这些断言。
- **可以后续跟进的 non-blocking follow-up**：
  1. R15 upload filename NUL negative 和 R16 internal Mapping retrieval v2 contract。
  2. 明确重复 lifecycle action 的 success no-op 与 invalid transition 的边界，并把结论写入 applicability manifest。
  3. 清理只作为旧 pin 兼容保留的散射/旧测试，确保它们不会被错误列为 L4 主证据。
- **建议的二次审查方式**：independent reviewer
- **实现者回应入口**：请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。

本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。
