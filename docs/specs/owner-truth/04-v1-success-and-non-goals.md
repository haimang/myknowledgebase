# OT-04 — V1 Success and Non-goals

> **项目**：`myknowledgebase`（MKB）
>
> **文件 ID**：`OT-04`
>
> **文档性质**：`owner-truth / foundational only`
>
> **版本 / 日期**：`OT-04-v1.0 / 2026-08-10`
>
> **文档状态**：`frozen`
>
> **导入状态**：`baseline import complete / foundational QNA closed`
>
> **Truth 状态**：`OT04-T001..T034 locked / inherited`；`OT04-T035 owner-frozen`
>
> **上游索引**：`docs/specs/index.md`
>
> **上游 Owner Truth**：`OT-01-v1.0`、`OT-02-v1.0`、`OT-03-v1.0`

本文件只回答 MKB v1 何时可以被声明为完成、internal orchestrator 可以观察到什么成功或失败、哪些质量底线不可降低，以及项目和能力容量的固定上限。测试框架、benchmark实现、metric字段、SLA数值、告警、runbook、故障注入工具和运维步骤不属于本文件。

---

## 1. Inherited Locked Truth

### 1.1 权威来源

| 来源 | 导入范围 | 导入纪律 |
|---|---|---|
| `docs/specs/index.md` §0–§1、§6 | 固定项目/文件/StateFamily容量、V1闭环、specification-ready条件与scope防线 | 直接继承硬上限；不因“验收完整”新增文件、服务、状态或产品能力 |
| `docs/specs/owner-truth/01-product-boundary.md` `OT-01-v1.0` | knowledge工具闭环、单体、internal orchestrator、final answer与上游业务OOS、内部状态自持 | 定义“做成什么”；不能用验收工作重新扩大产品责任 |
| `docs/specs/owner-truth/02-domain-model.md` `OT-02-v1.0` | runtime/Intake/derived truth分账、六StateFamily、proof与SelectionPointer边界 | 定义“什么事实可以证明成功”；不得以投影、文件或新状态替代 |
| `docs/specs/owner-truth/03-capability-and-external-contract.md` `OT-03-v1.0` | 有限调用能力、四类source、Task/result语义、LS-RAG/retrieval截止线、无raw vector | 定义caller可观察成功/失败与v1能力上限 |
| `S01-v1.5`、`S02-v1.3` acceptance/truth | strict ingress、Task/Audit、polling、proof-backed success、scatter、cancel、retry/rebuild、lineage | 只抽取HARD产品行为，不迁入HTTP字段、并发次数或测试工具 |
| `D01-v1.4`、`S03-v1.3 / T-O-12..29` | control向下/proof向上、typed Outcome、terminal guard、retry/recovery/cancel与summary-before-cleanup | 只导入可观察收敛与“不能假成功”的不变量；runtime算法下沉ES-02/04 |
| `S04-v1.2 / T-O-30..48`、`S05-v1.1 / T-O-49..76` | canonical Intake、serving/withdrawal、complete/partial、typed evidence、mandatory preflight、gate | 导入资产与admission质量底线；canonicalization、DDL和handler实现不进入本文件 |
| `S06 T-O-77..85` | immutable generation/invocation、exact schema binding、kernel/extension、repair与full validation | 只导入九条frozen Truth；未冻结的exact structure与后续QNA候选不成为验收标准 |
| `D02-v1.0 / T-O-86..92` | 六StateFamily、state-vs-fact、owner guard、fail-closed与truth drift纪律 | 所有Execution Spec必须证明没有新状态、跨owner写入或从projection猜Truth |

### 1.2 Acceptance invariant 覆盖对账

| Acceptance cluster | 本文件落点 | 主要冻结来源 |
|---|---|---|
| V1端到端完成定义 | `OT04-T001..T009/T035` | OT-01..03、S01/S03/S04/S05、S06 `T-O-77..85`、Owner Q1 |
| Caller-observable成功与失败 | `OT04-T010..T020` | S01/S02、S04 serving、S05 gate、OT-03 |
| 不可降低的质量底线 | `OT04-T021..T030/T035` | S03 proof/recovery、S04/S05 evidence、S06 schema、D02、Owner Q1 |
| 固定容量上限 | `OT04-T031..T034` | `docs/specs/index.md` §1、OT-01..03 |

### 1.3 导入截止线

1. Baseline acceptance matrix中的HARD assertion只有在能够追溯到冻结Truth时才进入本文件；测试数量、工具、报告格式、物理表、HTTP code和实现步骤不升级为Owner Truth。
2. `OT04-T001..T035`定义产品验收结果，不声称当前代码已经实现或通过验收；实现证据必须由ES-01..08后续交付。
3. S07–S10尚未冻结的exact structure、embedding、index、ranking和Retrieval Result字段不妨碍定义“grounded、traceable、proof-valid”的质量底线，也不得被本文件提前猜测。
4. Baseline没有冻结吞吐、延迟、并发、文档大小、token成本或存储容量的产品SLA。本基础版不发明数值；ES-07/08必须用证据给出安全运行包络，但不能把技术测量自动变成新的Owner承诺。
5. Legacy验收场景只作风险和反例证据；MKB成功不包含legacy兼容、迁移或相同输出字节。
6. 本文件只进行并关闭了一个foundational问题；不自动生成后续问题，也不把benchmark或运维选择上提给Owner。

---

## 2. Foundational Statements

### 2.1 V1完成定义

| Truth ID | 已固化 foundational truth | Provenance |
|---|---|---|
| `OT04-T001` | MKB v1只有在固定能力面形成完整闭环时才能声明完成：internal orchestrator提交knowledge输入或控制意图，MKB持久执行清洗、结构化、LS-RAG构建、结构化向量存储与proof-gated publication，并通过同步retrieval返回semantic Retrieval Result。只完成其中一段不等于v1完成。 | `OT01-T013/T015`、`OT03-T003/T012/T026/T031/T032` |
| `OT04-T002` | V1完成必须建立在一个Python应用、一个发布单元和caller-neutral MKB Contract之上；在没有legacy runtime、03-nano私有DTO或外部skill-worker注册生命周期的情况下，MKB核心仍能独立执行合法请求。 | `OT01-T001..T003/T009/T011/T012`、`S01-A25/A26` |
| `OT04-T003` | 最小接入与控制闭环必须完整：Team接入投影、简单内部token、严格Task+immutable Audit创建、六种异步request intent、polling、有限command/history与同步`retrieval.search`均具有已冻结语义。缺少任一已纳入v1的能力不能以“以后补充”宣称v1完成。 | `OT03-T001..T010` |
| `OT04-T004` | Intake/Clean闭环必须覆盖四类source kind以及inline/local、static/browser web、PDF、registered API single/scatter/pagination、local OCR和Vision/model-assisted clean，并产生可验证typed evidence；不得因legacy实现缺口静默缩减已冻结能力。 | `OT03-T011..T018`、`S05-T001..T018` |
| `OT04-T005` | Canonical Intake闭环必须形成稳定Source/Snapshot/Item/Revision/Artifact truth、complete/partial/gap/rejection证据和latest/serving分离；失败候选、partial observation或物理残留不得伪装为accepted、complete或serving knowledge。 | `OT02-T008..T015/T018/T022`、`S04-T015/T016/T022..T029` |
| `OT04-T006` | 所有进入LS-RAG的内容必须经过mandatory preflight；allowlist不能绕过验证。自动通过路径不得制造虚构gate，真实human review必须以bounded `action_required`收敛，缺失required evidence不能由人工批准。 | `OT03-T017/T018`、`S05-T014..T024` |
| `OT04-T007` | LS-RAG构建闭环必须产生immutable generation/invocation历史、exact Structure Schema binding、deterministic kernel与governed extension验证；只有full-valid artifact可以成为current并交给下游，失败/repair历史和token因果不得丢失。 | `OT03-T027..T030`、`T-O-77..85` |
| `OT04-T008` | 向量发布闭环只有在exact IntakeRevision、预期vector/filter metadata、serving pointer与active index generation通过type-specific PublicationProof后才完成。文件存在、queue空、日志、单vector ACK、Task/Process终态或`latest`都不是等价完成条件。 | `OT02-T018/T023`、`OT03-T021`、`S04-T015/T016/T023` |
| `OT04-T009` | Retrieval闭环必须只读取team-scoped、lifecycle-eligible、exact ServingRevision/IndexGeneration数据，并返回structured、grounded、traceable、reranked的semantic Retrieval Result。Final answer与最低层raw vector均不属于v1成功标准。 | `OT03-T031/T032`、`S04-T023` |

### 2.2 Caller-observable成功与失败

| Truth ID | 已固化 foundational truth | Provenance |
|---|---|---|
| `OT04-T010` | 本文件中的“用户可观察”只指持有效内部token的internal orchestrator/caller；MKB没有终端用户、UI、session或产品体验验收面。 | `OT01-T003/T004/T006` |
| `OT04-T011` | 合法异步请求被接受后，caller必须获得稳定Task ACK并能够仅依赖Task-scoped polling观察current generation的状态、result readiness、items、`action_required`、result/error summary与必要因果历史；caller不需要也不能依赖Execution/Process身份。 | `OT03-T005/T008..T010/T019/T020` |
| `OT04-T012` | Caller必须能稳定区分not-ready、ready success、terminal failure、terminal cancellation、running with action required与soft-deleted visibility；这些事实不能用404、一个generic pending或组合状态混淆。 | `OT03-T019/T020/T025`、`S01-A30`、`S02-T037/T039` |
| `OT04-T013` | 任一Task `succeeded`都必须有current root的intent-specific durable proof和可读取result summary；任一required proof缺失、无效或归属不一致时，caller只能观察not-ready或结构化失败，不能观察成功。 | `OT03-T021`、`S02-A09/A15`、`S03-T022/T042/T043` |
| `OT04-T014` | Scatter成功只有在accepted required set全部按policy terminal且required success均proof-valid时成立。Healthy child可在root terminal前独立ready；mixed outcome通过items/counts透明呈现，parent failure/cancel不得隐藏或回滚已proof-valid child。 | `OT03-T022`、`S02-A13..A18`、`S03-T039..T043` |
| `OT04-T015` | Strict contract、identity、authority、team gate或schema验证失败必须在产生下游业务工作前fail-loud；不得留下半个Task/Audit、未归属runtime、accepted Snapshot或虚假success。错误必须是caller可处理的结构化结果，并且不泄漏内部secret、stack、路径或driver信息。 | `OT03-T001/T006/T007/T010`、`S01-A01/A08..A15/A23/A31` |
| `OT04-T016` | 需要人工输入时，Task继续显示`running`并提供bounded、安全的`action_required`；stale、越权或冲突decision不得改变当前状态。无UI、无active Process lease等待、无自动approve。 | `OT03-T018/T020`、`S01-A37..A39`、`S05-T020..T024` |
| `OT04-T017` | Cancel的可观察完成是forward-stop收敛而非接收command：只有active descendants被fence/terminal且不再可能late commit时才`cancelled`。Cancel不等于rollback、deactivate、delete或purge，已proof-valid结果继续可见。 | `OT03-T023`、`S02-A10..A12/A18` |
| `OT04-T018` | Full retry与atomic rebuild必须保留不同且稳定的caller语义：前者在同Task创建新generation，后者创建新Task；两者均保留旧terminal result、proof与causal lineage，不原位复活或改写历史。 | `OT03-T024`、`S02-A21..A28` |
| `OT04-T019` | 新candidate、build或reindex失败不得污染或撤销旧proof-valid serving knowledge；deactivate/delete则必须先在逻辑围栏上停止正常检索，即使物理bytes/vector尚未清理。Runtime失败和资产lifecycle不得互相冒充。 | `OT02-T018/T022`、`S04-T015/T016/T021/T023`、`S04-A15/A18/A29` |
| `OT04-T020` | 同步retrieval只返回当前eligible的semantic Retrieval Result且不创建Task/Audit/Execution/Process；无eligible数据、输入无效、binding不兼容或内部失败不得被伪装成grounded hit或publication成功。Exact empty/error语义、字段与错误码由ES-07定义。 | `OT03-T004/T031/T032`、`S01-A24` |

### 2.3 不可降低的质量底线

| Truth ID | 已固化 foundational truth | Provenance |
|---|---|---|
| `OT04-T021` | MKB禁止silent loss。Required member malformed、page/gap缺失、duplicate conflict、source未证明exhausted、Artifact缺失或collection不完整时，必须保留typed rejection/gap evidence并阻断相应成功范围，不能catch-and-skip后宣称complete。 | `OT03-T016/T017`、`S05-T012..T017` |
| `OT04-T022` | Raw representation、source-grounded canonical semantics、clean-derived output与LS-RAG派生产物必须分账；OCR/Vision/model处理必须保留producer、loss/quality和source evidence，不能凭模型输出重写canonical source truth或制造Revision。 | `OT03-T014/T015`、`OT02-T010/T012/T013` |
| `OT04-T023` | 每个可serving或可retrieval结果必须具有从Team、IntakeSource/Item、exact IntakeRevision、clean/Generation artifact、派生structure与vector/index generation到source anchor/provenance的typed lineage；任何环节不得用路径、latest、裸digest或日志猜测。Exact derived kind仍归ES-06/07。 | `OT02-T008..T018/T023`、`OT03-T028/T029/T031` |
| `OT04-T024` | Task/Audit、restart/generation、IntakeRevision/Artifact、GenerationArtifact/Invocation、terminal summary与proof的已冻结历史必须保持immutable和可审计；retry、repair、soft-delete、runtime cleanup或schema升级不得覆盖过去。 | `OT02-T012/T013/T017/T022`、`OT03-T006/T024/T025/T027..T030` |
| `OT04-T025` | Exact definition/schema/workflow/capability/model-binding的缺失、不兼容或same-version digest drift必须fail-loud。Retry、resume、recovery与human decision不得切换`latest`、猜兼容或用generic fallback掩盖漂移。 | `OT03-T007/T013/T029/T030`、`S03-T017/T047/T053`、`S05-T025/T026` |
| `OT04-T026` | Deterministic kernel、identity、binding、order/coordinate、source fidelity与proof不能由agent修补；governed extension repair必须产生新artifact并从零full-validate。只有full-valid结果可以进入current/publication。 | `OT03-T030`、`T-O-82..85` |
| `OT04-T027` | Semantic Retrieval Result必须保留grounding、original/summary traceback、stable anchor、provenance和rerank可解释依据；不得以无来源context、最终答案或raw vector替代。Exact scoring和payload不是Owner Truth。 | `OT01-T008/T014`、`OT03-T026/T031/T032` |
| `OT04-T028` | 所有业务读写必须保持Team隔离和最小内部trust boundary。无效token、跨Team引用或未知identity不得泄漏资源存在性；public result不得泄漏secret、内部runtime payload、stack、SQL或物理路径。 | `OT01-T005/T006`、`OT03-T001/T010`、`S01-T017/T046`、`S02-T032/T038` |
| `OT04-T029` | 状态与成功必须由唯一owner和guard推进：control只向下，typed Outcome/proof只向上；queue、HTTP响应、callback、log、projection、`payload_extra`和物理文件均无成功权。六StateFamily之外的phase/reason/readiness/pointer/proof必须保持typed fact。 | `OT02-T019..T021`、`D02` §0.5、`OT03-T009/T019/T021` |
| `OT04-T030` | Crash、重复delivery、lost wake-up、lease expiry、retry、cancel race、partial fan-out/fan-in与cleanup不能造成双成功、重复canonical truth、永久stranded或历史断链。恢复必须收敛到与未发生故障相同的业务语义；具体机制和测试次数归Execution Spec。 | `S03-T027..T033/T044..T050`、`S02-T014/T031/T035`、`S04-T026/T029..T038` |

### 2.4 固定容量上限

| Truth ID | 已固化 foundational truth | Provenance |
|---|---|---|
| `OT04-T031` | V1架构容量上限固定为：`1`个MKB Python应用、`1`个发布单元、`1`类internal-orchestrator上游、`0`个UI/用户平台、`0`个compatibility/migration产品。内部module、adapter、worker loop或registry不得被验收需求升级为新服务或产品。 | `docs/specs/index.md` §1.1、`OT01-T001..T004/T011/T012` |
| `OT04-T032` | Specification容量上限固定为`4`份Owner Truth与`8`份Execution Spec；V1 StateFamily上限固定为`6`。Acceptance matrix、benchmark、ADR、风险、spike与runbook只能进入既有文件章节，不能创建第三层spec或第七StateFamily。 | `docs/specs/index.md` §1.1/§3.1、`OT02-T019..T021` |
| `OT04-T033` | 外部能力容量上限固定为：`6`种异步request intent、`4`类source kind、polling-only异步结果、`1`个同步semantic retrieval能力、`0`个raw-vector公共能力与`0`个final-answer能力。Exact endpoint数量不是Owner Truth，也不得被用来暗中增加capability。 | `OT03-T003/T004/T008/T011/T032`、`OT01-T014` |
| `OT04-T034` | V1完成不以任何OOS能力、未来adapter、可扩展plugin、多服务拆分、legacy迁移、通用内容管理或产品层功能为前置条件。实现不得以“完整性”“可扩展性”或“生产级”为理由提高上述容量上限。 | `docs/specs/index.md` §1.2、`OT01` §3、`OT03` §3 |

### 2.5 Owner-frozen semantic release gate

| Truth ID | 已固化 foundational truth | Provenance |
|---|---|---|
| `OT04-T035` | MKB v1必须通过有限、项目自有、代表性的semantic retrieval验收：预期查询能够找回预期grounded evidence并提供正确original traceback。仅有contract、schema、proof和traceback结构正确，但语义上无法找回预期knowledge的系统，不得宣告V1完成。Exact corpus、query数量、metric、阈值、topK、ranking/rerank策略、回归机制与工具由ES-07/08裁决；本条不构成通用准确率SLA，也不扩展到final answer或上游业务结果。 | Owner Q1选择A（2026-08-10）；`OT01-T008/T013`、`OT03-T026/T031/T032`、`OT04-T009/T027` |

---

## 3. Hard Scope / Non-goals

| Non-goal ID | 明确不属于V1成功或验收范围 | 边界说明 |
|---|---|---|
| `OT04-N001` | Final answer、Chat、Agent、会话、问答策略、用户体验或任何上游业务结果 | MKB成功止于semantic Retrieval Result，不对上游产品成败负责 |
| `OT04-N002` | Raw vector read/list/export、VectorRecord CRUD、caller-supplied raw-vector query或通用vector database | 已由`OT03-T032`明确排除 |
| `OT04-N003` | UI、终端用户账号、session、Team membership/RBAC、billing、plan或商业多租户平台 | 最小Team投影和token不是平台能力 |
| `OT04-N004` | Generic agent/worker平台、动态plugin市场、任意Workflow authoring或外部Schema/validator CRUD | V1只有内部、版本化、有限registry/capability |
| `OT04-N005` | Knowledge编辑、协作审核、CMS、RAG artifact人工patch或mass-scatter逐项精修产品 | ExecutionGate只处理有限admission，不形成内容产品 |
| `OT04-N006` | Webhook/callback、skill-worker注册/心跳/control plane或异步retrieval Task | 异步结果固定polling，retrieval固定同步 |
| `OT04-N007` | 第五类source、额外request intent、未冻结input modality或任意caller handler | 已冻结能力清单就是V1上限 |
| `OT04-N008` | 多应用、微服务、额外部署单元、外部Reconciler产品或通用状态治理平台 | 恢复行为保留在单体内部，不扩大拓扑 |
| `OT04-N009` | 第七StateFamily、stage-specific status、global production status或组合状态 | 使用现有六态族和typed facts |
| `OT04-N010` | Legacy importer、API/schema/status兼容、dual-read、migration、cutover、rollback或相同输出字节 | Legacy只作ReferenceAnchor |
| `OT04-N011` | 以allowlist、人工批准、模型输出、queue ACK、文件存在或单个vector ACK降低proof/validation门槛 | 任何fast path都必须满足同一质量底线 |
| `OT04-N012` | Exact endpoint/payload、表/列/DDL、Process key、Workflow图、transaction、retry算法、model/Prompt、embedding/index/ranking/backend | 全部属于既有Execution Spec |
| `OT04-N013` | 在Owner Truth中冻结测试框架、benchmark工具、metric字段、告警、dashboard、runbook或故障注入实现 | OT-04只冻结必须证明的结果 |
| `OT04-N014` | 在没有Owner产品承诺时发明吞吐、延迟、并发、容量、token成本或准确率SLA | ES必须测量并给出安全包络，但不得伪造Owner承诺 |
| `OT04-N015` | 依赖OOS或future-ready能力才能通过V1验收 | OOS缺失不能被记为V1缺陷，OOS存在也不能补偿核心闭环缺失 |
| `OT04-N016` | 用特定provider/model/backend/driver的存在代替质量或成功 | 验收面对行为、lineage、proof和fail-closed结果 |
| `OT04-N017` | 将有限代表性semantic验收扩展为跨领域、语言、规模或query风格的通用准确率SLA，或要求Owner选择corpus、query数量、metric、阈值与benchmark平台 | `OT04-T035`只冻结产品release gate；exact、有限、可重复的证据设计归ES-07/08 |

---

## 4. Open Foundational Decisions

### 4.1 Round 1 准入结论

本轮只准入`1`个问题：MKB v1是否必须证明semantic retrieval能够在有限、代表性场景中找回预期knowledge evidence，还是只要contract、schema、proof和traceback结构正确即可宣告完成。

该问题同时满足`docs/specs/index.md` §2.3：

1. `OT04-T009/T027`已冻结grounding、traceback与rerank结果形态，但没有冻结“语义上能否找回预期内容”是否为release blocker；
2. 两种答案会直接改变V1完成定义和质量底线，而不是改变测试工具；
3. “必须证明有限代表场景的semantic usefulness”与“只验contract/proof正确性”是两个产品结果实质不同、均可实现的选择；
4. 本题不需要Owner选择corpus、metric、阈值、topK、模型、index、reranker或benchmark框架。

其余候选轴全部剔除，见§4.3；本轮不为达到题数制造第2、3题。

### 4.2 Q1 — Semantic retrieval usefulness是否属于V1完成门槛

**单一决策轴**：当Task、Intake、structure、vector publication、eligibility、grounding与traceback全部技术正确，但代表性查询仍无法找回预期knowledge evidence时，MKB v1是否可以被声明为完成。

**已继承Truth**：

- `OT01-T008/T013`：LS-RAG结构化向量存储与上游knowledge retrieval是MKB的首要业务闭环；
- `OT03-T026/T031/T032`：公共结果是grounded、traceable、reranked的semantic Retrieval Result，不是final answer或raw vector；
- `OT04-T001/T008/T009`：V1必须闭合publication到retrieval，而不只是写入vector；
- `OT04-T021..T027`：无silent loss、exact lineage、source fidelity、full validation与traceback已经是不可降低的质量底线；
- Baseline `S10`尚未冻结exact metric、threshold、ranking与golden scenarios，因此不存在可直接复用的semantic usefulness release verdict。

**尚未关闭的歧义**：现有Truth能够证明“返回内容来自哪里、是否合法、是否可追溯”，但不能单独证明“系统是否把预期的相关知识找了回来”。若把这一点完全留给ES-07，工程侧可能在不知情中改变V1成功定义，因此需要Owner只裁决它是不是release gate。

#### Scope Impact Audit — 推荐选项A

```text
Scope Impact Audit
- New product responsibility: no
- New externally visible behavior: no
- New V1 capability: no
- New domain identity or StateFamily: no
- New deployment/runtime unit: no
- New owner-truth file: no
- New execution-spec file: no
- Raises a fixed capacity ceiling: no
- Can be solved inside an existing file and boundary: yes
- Classification: no expansion
```

#### 推荐执行选项A — Semantic usefulness必须通过有限代表性验收

**推荐规定：MKB v1只有在有限、项目自有、代表性knowledge场景中，能够为预期查询返回正确grounded evidence及其original traceback时，才可以宣告完成。仅有schema-valid、proof-valid、可追溯但语义上无法找回预期内容的系统，不算V1成功。**

推荐边界如下：

1. 本题只冻结“semantic usefulness是release gate”，不冻结如何测量；
2. 代表性验收必须有限、有明确预期evidence，并覆盖MKB已承诺的核心LS-RAG retrieval行为；
3. 返回结果仍止于semantic Retrieval Result，不评价final answer、用户满意度或上游业务转化；
4. Exact acceptance set、query数量、metric、阈值、topK、context budget、ranking/rerank策略和工具由ES-07自行设计并由ES-08汇总证据；
5. 不要求一个跨所有corpus、语言和业务的通用“准确率SLA”，也不创建online evaluation平台；
6. Model、embedding、index或reranker升级后，仍必须证明没有破坏已冻结的代表性semantic结果，但具体回归机制属于Execution Spec。

#### 完整Reasoning

1. **这是MKB核心价值，不是附加质量优化**：Owner已将MKB定义为knowledge处理与获取工具。如果系统只能证明vector被写入、schema合法，却无法在代表性查询中取回预期知识，端到端产品闭环并未成立。
2. **结构正确不等于检索可用**：Exact lineage、proof和traceback可以证明一个错误命中的来源，却不能证明召回了正确内容。两者必须分别验收，不能用可审计性代替相关性。
3. **与LS-RAG定位一致**：Structurizer、Constructor、original/summary双通道、Traceback和Reranker之所以进入v1，就是为了提高grounded retrieval。若semantic usefulness不阻塞release，这些能力只剩结构存在性而没有产品结果。
4. **有限验收可以阻止scope无限化**：推荐只要求项目自有、代表性的有限场景，不承诺覆盖任意corpus、语言、query风格或未来业务。它建立下限，而不是把MKB变成通用评测平台。
5. **不把execution选择上推Owner**：Owner无需决定precision/recall、NDCG、topK、阈值或corpus大小。ES-07可以根据实际数据选择最小、可重复的证据，只要能证明预期evidence被找回且traceback正确。
6. **能区分回归与合法演进**：Embedding、index、summary或rerank实现可以更换，但如果代表性知识从可找回变成不可找回，应该被识别为产品回归，而不是因contract仍合法就放行。
7. **不会引入answer-generation责任**：验收对象是retrieved evidence及其grounding，不是自然语言答案、citation presentation、用户偏好或业务效果，继续遵守OT-01/03截止线。
8. **与固定容量上限兼容**：该门槛使用既有ES-07/08、既有retrieval能力和既有文件，不增加source、intent、状态、服务、部署单元或Owner Truth文件。

#### 选择后果

| 选择 | 产品结果 | Scope判定 |
|---|---|---|
| **A — Semantic usefulness是V1 release gate（推荐）** | V1必须在有限代表场景中找回预期grounded evidence并正确traceback；exact测量由ES-07/08决定 | `no expansion / completes existing success definition` |
| **B — 只要求contract/proof/traceback正确** | 即使代表性查询找不到预期knowledge，只要结果结构合法、可追溯，仍可宣告V1完成 | `bounded foundational quality relaxation` |

选择B不会减少实现复杂度中的vector/retrieval链路，只会降低V1完成标准：系统可能“技术上正确、产品上不可用”。如果Owner选择B，OT-04必须明确semantic relevance不属于release blocker，ES-07仍要实现grounding/traceback，但不承担代表性usefulness证明。

#### 推荐A的明确Non-goals

- 不冻结accuracy、precision、recall、NDCG或任何统一数值；
- 不要求Owner选择测试语料、query、topK、阈值、model、embedding、index或reranker；
- 不建设benchmark SaaS、online evaluation、A/B testing、用户反馈或标注平台；
- 不验收final answer、用户满意度、业务转化或上游产品效果；
- 不承诺任意领域、语言、文档规模或query风格的通用质量SLA；
- 不新增source kind、request intent、StateFamily、服务、部署单元或spec文件。

#### Owner回答与冻结结论

Owner回答：`A`（2026-08-10）。

- **采纳A**：semantic usefulness是V1 release gate，并固化为`OT04-T035`；
- **拒绝B**：contract/proof/traceback结构正确但无法找回预期knowledge，不足以宣告V1完成；
- Exact corpus、query数量、metric、阈值、模型、索引、ranking/rerank与工具继续由ES-07/08自行裁决，不形成新的Owner问题；
- 决策分类保持`no expansion`，未改变任何固定容量上限。

### 4.3 未准入候选轴

| 候选决策轴 | 准入判定 | 证据与处置 |
|---|---|---|
| 吞吐、延迟、并发、文档大小、scatter规模、token或存储容量数值 | `rejected / executional` | Index已将性能和容量参数交给Execution Spec；没有Owner产品SLA时，ES-07/08测量安全包络即可 |
| Semantic acceptance采用什么metric、阈值、corpus、query数量或benchmark工具 | `rejected / executional` | Q1只裁决是否为release gate；exact evidence design归ES-07/08 |
| Clean/OCR/Vision是否必须byte-for-byte lossless | `rejected / derivable + executional cutoff` | Frozen Truth已要求raw/source/derived分账、original保留、loss/quality evidence和source fidelity；OCR/Vision天然可有声明损失，exact可接受loss policy归ES-03/06，不需要Owner设计 |
| 四类source与完整clean capability是否可延后 | `rejected / already frozen` | `T-O-49`、`OT03-T011/T012`已将完整能力面纳入v1 |
| Task、scatter、cancel、retry/rebuild、failure/readiness如何算成功 | `rejected / already frozen` | `OT03-T019..T025`与`OT04-T011..T020`已有完整可观察语义 |
| 是否要求crash/replay/recovery后保持同一业务语义 | `rejected / already frozen` | `S03-T044..T050`、`OT04-T030`已冻结收敛要求；exact机制归ES-02/04/08 |
| Final answer、raw vector或上游产品质量是否进入V1 | `rejected / already frozen OOS` | `OT01-T014`、`OT03-T032`、`OT04-N001/N002`已关闭 |
| 测试框架、metric字段、dashboard、alert、runbook与故障注入工具 | `rejected / executional` | `OT04-N013`明确下沉ES-08，不提交Owner |

### 4.4 Round 1关闭状态

| 项目 | 当前结论 |
|---|---|
| 通过准入的foundational问题 | `1` |
| Owner已回答 | `Q1 = A` |
| 新增Owner-frozen Truth | `OT04-T035` |
| 等待Owner回答 | `0` |
| 重问已冻结Truth | `0` |
| 上提executional unknown | `0` |
| 自动生成后续问题 | `0` |
| OT-04状态 | `frozen / v1.0` |

Round 1已关闭。Closure审计未发现新的foundational分歧；不生成Round 2。

---

## 5. Owner Decisions

| Decision cluster | 已有Owner裁决 | 固化落点 | 后续处理 |
|---|---|---|---|
| 产品完成边界 | 文档/knowledge输入必须闭合到清洗、结构化、LS-RAG向量存储和上游retrieval；final answer及上游业务OOS | `OT04-T001/T004..T009` | ES-01..08必须共同提供端到端证据 |
| 内部状态职责 | MKB自持Workflow、资产lifecycle、retry、recovery与cleanup；这些不是产品层扩张 | `OT04-T002/T003/T029/T030` | 不得用外部平台或transport替代Truth |
| 可观察结果 | 异步Task polling、六态/五轴、proof-backed success、scatter/cancel/retry/rebuild与同步retrieval | `OT04-T010..T020` | Exact wire归ES-01/07 |
| 质量底线 | 无silent loss；exact lineage/binding；immutable history；full validation；fail-loud/fail-closed；有限代表场景能够找回预期grounded evidence并正确traceback | `OT04-T021..T030/T035` | 任何provider/backend都必须达到同一结果；exact semantic验收设计归ES-07/08 |
| Retrieval截止线 | 只提供semantic Retrieval Result；无final answer、无最低层raw vector | `OT04-T009/T020/T027`、`OT04-N001/N002` | ES-07不得扩大公共面 |
| 架构与容量 | 单应用/单发布、4+8文件、六StateFamily、有限intent/source/capability、无兼容产品 | `OT04-T031..T034` | Acceptance工作不得新增容量 |

本节登记全部Owner裁决；§4.2的Q1已经回答并固化，当前没有开放的foundational approval request。

---

## 6. Constraints on Execution Specs

| Constraint ID | 必须由Execution Spec闭合的验收义务 | 主要落点 |
|---|---|---|
| `OT04-C001` | 每份ES必须把适用的`OT04-Txxx`映射为可复现Acceptance Evidence；可以自行选择测试框架、fixture和工具，但不能降低HARD结果或要求Owner审批实现。 | 全部ES |
| `OT04-C002` | ES-01必须证明strict Team/token/Task/Audit ingress、六种intent、polling、幂等、caller authority、structured error与无内部信息泄漏。 | `ES-01/08` |
| `OT04-C003` | ES-02必须证明single/scatter、typed Outcome/proof aggregation、六态族owner、cancel/retry/recovery收敛、无双终局、无permanent stranded与summary-before-cleanup。 | `ES-02/04/08` |
| `OT04-C004` | ES-03必须证明四类source与全部clean capability、complete/partial/rejection/gap、stable identity、mandatory preflight和bounded human gate均不silent skip或越权批准。 | `ES-03/05` |
| `OT04-C005` | ES-04必须证明canonical truth、artifact、durable scheduling、pointer、history与cleanup在提交失败、重放和恢复后不重复、不丢失、不破坏lineage或旧serving；exact transaction/outbox实现由ES-04自行裁决。 | `ES-04/08` |
| `OT04-C006` | ES-05必须证明model/Prompt/schema/capability exact binding、same-version drift fail-loud、retry/resume不切latest，以及provider替换不改变产品Contract。 | `ES-05/06/07` |
| `OT04-C007` | ES-06必须证明immutable generation/invocation、source grounding、kernel/extension cutoff、repair新artifact与full validation；exact structure由ES-06自行冻结。 | `ES-06` |
| `OT04-C008` | ES-07必须证明exact Revision的vector/filter publication、serving/index eligibility、失败候选不污染旧serving，以及grounded/traceable/reranked semantic Retrieval Result；不得开放raw vector或final answer。 | `ES-07` |
| `OT04-C009` | ES-08必须汇总单体启动、安全、隔离、readiness、observability、recovery与零legacy依赖证据，并给出测得的安全运行包络；不得将metric或benchmark结果包装成新产品SLA。 | `ES-08` |
| `OT04-C010` | 系统验收必须至少闭合一个single端到端journey：合法接入→Task/Audit→Intake/Clean→LS-RAG→publication proof→polling success→同步retrieval与traceback。Exact测试实现归ES。 | `ES-01..08` |
| `OT04-C011` | 系统验收必须闭合scatter journey：accepted required set→parallel child→collect-all→mixed outcome/early-ready→root aggregate，并证明cancel/retry/rebuild不回滚proof-valid child。 | `ES-01..08` |
| `OT04-C012` | 每个成功journey必须有相应negative/failure证据，证明缺proof、binding drift、并发冲突、partial collection、重复/遗漏执行、cancel race与旧serving保护不会产生假成功。Exact故障场景和注入方式由ES-08统筹。 | `ES-01..08` |
| `OT04-C013` | Acceptance Evidence必须证明六StateFamily和owner guard未被破坏，phase/readiness/pointer/proof仍为typed fact；不得从日志、queue、projection或物理对象推导Truth。 | 全部ES |
| `OT04-C014` | 所有验收设计必须留在既有8份ES及单体发布边界内；发现技术未知时给出默认方案和验证路径，不新增spec、service、state、intent、source kind或owner QNA。 | 全部ES |
| `OT04-C015` | ES-07必须设计有限、项目自有、可重复的代表性semantic retrieval验收，证明预期query能够找回预期grounded evidence并正确original traceback；ES-08必须将该证据作为V1 release gate并覆盖model、embedding、index或reranker变更后的回归。Exact corpus、query数量、metric、阈值、topK、策略与工具由ES自行裁决，不得升级为通用质量SLA、评测平台、final-answer验收或Owner QNA。 | `ES-07/08` |

---

## 7. Revision History

| 版本 | 日期 | 状态 | 变更 |
|---|---|---|---|
| `OT-04-v0.1` | `2026-08-10` | `pending consolidation` | 创建V1 Success and Non-goals基础文件；原义归并index固定上限、OT-01..03及S01-S06/D02冻结acceptance不变量，形成34条inherited foundational truth、16条hard non-goal和14条Execution acceptance constraint；明确区分产品成功标准与测试/benchmark/metric/运维实现，未生成QNA，未增加产品能力、状态、文件或部署单元。 |
| `OT-04-v0.2` | `2026-08-10` | `owner-review-needed` | 完成Round 1 foundational准入：仅“semantic retrieval usefulness是否属于V1完成门槛”无法由现有Truth唯一推导，形成Q1并推荐有限代表性semantic acceptance作为release gate；登记完整Scope Impact Audit、两项选择、reasoning、non-goals及8类未准入候选。Q1等待Owner回答，不生成第2/3题或后续轮次。 |
| `OT-04-v1.0` | `2026-08-10` | `frozen` | Owner选择A：有限、项目自有、代表性的semantic retrieval usefulness成为V1 release gate，固化`OT04-T035`、`OT04-N017`与`OT04-C015`；contract/schema/proof/traceback结构正确但无法找回预期knowledge不算V1成功。Exact corpus、query数量、metric、阈值、模型、索引、ranking/rerank与工具全部下沉ES-07/08；未新增产品责任、外部能力、状态、服务、部署单元或文件，Q1关闭且不生成Round 2。 |
