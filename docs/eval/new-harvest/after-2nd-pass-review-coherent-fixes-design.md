# MKB new-harvest 二轮审查后内聚还债与长期治理设计

> 功能簇: `NH-Coherent-Fixes / new-harvest debt retirement`
> 讨论日期: `2026-08-31`
> 讨论者: `Owner（目标与范围）`、`GPT（代码分析与设计）`
> 关联调查报告:
> - `docs/code-review/new-harvest/NH1-NH9-2nd-pass-review-VF-ledger.md`
> - `docs/code-review/new-harvest/NH1-NH9-review-VF-ledger.md`
> - `docs/closure/new-start/deferred-items-ledger.md`
> 关联 QNA / 决策登记:
> - `docs/eval/new-harvest/pre-initial-planning-qna.md`（`T-O-376..389`）
> - `docs/eval/new-harvest/pre-charter-qna.md`（`T-O-390..407`）
> - 本文 §9 `CF-D01..CF-D16`
> 文档状态: `draft`
> 设计基线: `HEAD ba099ee305577cca2281a669afbca364111f200b`
> 本文只冻结目标架构、迁移法与 action-plan DAG；**不执行代码修复，也不改写既有 review/closure**。

---

## 0. 背景与前置约束

- **项目定位回顾**：new-harvest 的目标不是拥有若干能单独跑通的 handler，而是让四类 intake 从公开 admission 开始，经由 kind-family dynamic workflow、表示观察、晚绑定 processing、acceptance、LS-RAG、publication，最终形成可检索且可解释、可恢复、可运维的 durable 业务闭环。
- **为什么现在必须做长期治理设计**：二轮统一台账把 `86` 条原始 finding 归并为 `52` 条 VF，其中 `15` 条 `[true-bug]`、`18` 条 `[partial-delivery]`、`17` 条 `[true-deferred]`、`1` 条已接受设计取舍、`1` 条驳回。第一轮 deferred 总账又保留了 stage 正文、publication set、pre-catalog CAS、live supply、workflow revision、进程级恢复、全仓测试与证据执行器等切片。继续按严重级逐条 hotfix，只会在现有混合身份上叠加更多局部 guard。
- **本次讨论的前置共识**：
  - 不修改 `T-O-376..407` 的冻结产品法；若设计与其冲突，必须先通过正式 QNA append 新 Truth，不能由 action-plan 静默改口。
  - 业主明确选择“内聚、按业务簇、长期治理”的行动方案，不接受只关闭四个 critical 的 hotfix 批次。
  - 已有 review/closure 是问题来源和历史证据，不是当前代码正确性的替代证明；本设计以 HEAD 代码、DDL 与可复现行为为事实基础。
  - `VF27`（pending TTL 使未消费上传失效）保持已确认的 fail-loud 产品法，但会通过 session reservation 消除“已被 Task 合法占用仍过期”的竞态；`VF52` 已被请求体流式上限反证，不产生修复工作。
- **本设计必须回答的问题**：
  - 怎样把 50 条有效债务及第一轮 NH deferred 切成少数稳定的架构边界，而不是换一个编号继续逐项修补？
  - Source、Observation、Item、Task、Execution、WorkflowRevision、ObjectSession 各自的身份和 CAS owner 是谁？
  - full retry、Process retry、失败 observation 重试、delete/reactivate、outbox dead、operator restart 分别继承什么，禁止继承什么？
  - leaf-worker 上游如何发现 kind/workflow/strategy/operation/capability，如何读到实际绑定，又不获得 `workflow_key` 选图权？
  - 如何让 evidence、projection、diagnostic、metric、control 各守边界，并能证明迁移、崩溃恢复和真实 runtime supply？
  - 哪些历史 deferred 本轮吸收，哪些应通过删除无用形状来偿还，哪些仍是明确的产品扩张而非技术债？
- **显式排除的讨论范围**：
  - public raw object GET/export/list/presign、R2/remote object adapter；它们违反或超出 `T-O-396`，不是 upload/GC 欠账的修复手段。
  - 第五 source kind、live connector/cookie/tunnel、caller 指定 `workflow_key`、通用 JOIN/DSL/自由表达式/动态 loader；它们不属于 `T-O-377/379/398` 的有界 workflow。
  - existing-object 使用新 cleaner/validator 的产品级 upgrade；`T-O-401` 明确要求新的 owner-gate 和显式 operator command。本设计只保证 retry/recovery exact replay，不偷渡第八 intent。
  - 外部 vector engine、answer generation、experiment 发车与评分。experiment 继续服从 `T-O-380`，不得成为 closure 证据。

### 0.1 独立代码核查摘要

本设计没有把 VF ledger 的初步修法直接当作目标架构。对 HEAD 的重新追踪确认了以下根因族：

1. `src/runtime/intake/acquisition_ingest.py:129-137` 在 Process 期通过独立 UoW 采用 identity，而 `src/runtime/intake/acceptance_snapshot.py:139-195` 又把 `external_key` 当 observation key、复用旧 Snapshot，并无完整 fingerprint/CAS 法；Source/Observation/Item 三个身份被压成一个键。
2. `src/runtime/task/task_commands.py:293-318` 复制旧 sealed actual，却让新 Execution 从 start 重新进入 HTTP acquire；“exact binding”与“重新观察外部世界”同时成立，语义自相矛盾。
3. `src/services/object_upload.py:55-137` 先把字节 promote 到 final CAS，再验证 Team/提交 catalog，并且每次生成随机 hold owner；`src/services/object_upload_ttl.py:62-82` 只能释放“最新一条”，handle 的字节身份无法表达会话所有权。
4. `src/services/workflow_registry.py:152-210` 正确拒绝同 revision 异 digest，但 `src/workflows/kind_family.py:239-253` 仍把改变后的图登记为 revision 1；registry 的 immutable 法与 builtin 的版本纪律不一致。
5. `src/runtime/workflow/runtime_outcome.py:38-139` 只检查 Process status 和 Execution cancelling，不拒绝已 terminal Execution；`src/runtime/workflow/runtime_materialize.py:426-484` 创建 Process 后对 Execution 更新不核对 rowcount，终态后仍可能前进。
6. `src/runtime/intake/core.py:398-440` 在 acquire/decode/clean 阶段把完整 state 写入 stage envelope；公开 source 内的 nested `payload_extra` 又没有统一走递归拒密，transport body、URL 和 secret-shaped data 会横跨 audit/CAS。
7. public/internal API 没有 workflow/capability/namespace/intake-item/process discovery；Task GET/list 的 OpenAPI response 是 `additionalProperties: true`。数据库比 wire 丰富，但上游、前端和 operator 无法稳定读取或操作。
8. `src/runtime/metrics.py:82-229` 声明的多数系列没有 emitter；`src/runtime/workflow_supervisor.py:47-77` 只把异常放在进程内字段；`src/runtime/health.py:16-26` 又不把已配置为 required 的 `concurrent_writes` 纳入 overall readiness。
9. 现有定向用例 `tests/unit/test_ns6_phase2.py::test_stale_fencing_fail_does_not_kill_new_generation` 在 HEAD 失败，说明第一轮“fixed”与测试契约已经发生漂移；全仓 closure 不能继续以历史 62-test 集合代替当前回归。

因此，长期治理的最小正确单位不是单个 VF，而是以下四类不可混用的 durable token：

- `ObservationReservation`：一次外部观察的 idempotency 与恢复 owner；
- `ItemEpoch`：Item 所有 canonical mutation 的跨 Task CAS fence；
- `WorkflowRevisionPin`：Execution exact graph/capability/formula 版本；
- `ObjectSession / ObjectReference`：上传调用的会话所有权与业务字节所有权。

---

## 1. 讨论对象

### 1.1 功能簇定义

- **名称**：`NH-Coherent-Fixes / new-harvest debt retirement`
- **一句话定义**：以显式身份、版本化工作流、引用优先对象法和可操作读面，整体偿还 NH1–NH9 二轮审查债务及其直接 deferred，而不是继续扩张局部 hotfix。
- **边界描述**：这个功能簇**包含** observation/source/item 身份、workflow revision/replay/outcome、object session/ref/GC/purge、evidence authority、安全 stage envelope、runtime supply/role/readiness、discovery/read/debug/control/metrics、migration/compat/assurance；**不包含** §0 明列的产品扩张。
- **关键术语对齐**：

| 术语 | 定义 | 备注 |
|------|------|------|
| `DebtUniverse` | 本设计必须处置的 `VF1..VF51` 有效项（排除 acknowledged `VF27` 的错误定性但保留其竞态保护）、第一轮 NH deferred 及直接阻塞它们的跨阶段债务 | 每个 ID 必须恰好映射到一个 owner AP；不得再次无承接 defer |
| `SourceIdentity` | `(team, source_kind, normalized_external_key)` 的长期来源身份 | 不等于一次观察，也不等于 Snapshot |
| `ObservationReservation` | caller observation key 在一个 Source 下的 durable reservation，状态为 reserved/acquired/accepted/failed/abandoned | Task admission 与 reservation 同 UoW |
| `Snapshot` | 一次已接受 Observation 的 immutable 事实集合 | 不因相同 Source 自动复用；同 Observation 只允许 exact replay |
| `ItemEpoch` | Item 每次 latest/serving/lifecycle canonical mutation 都递增的单一 CAS 序号 | v2 逻辑上复用现有 `row_revision`，不再增设第二个会漂移的 counter |
| `WorkflowRevisionPin` | `(workflow_key, revision_number, canonical_digest, compiled_digest, capability_manifest_digest)` 的 immutable 版本坐标 | Execution 创建后只读；old pin 可执行、不可改写 |
| `ProcessingBinding` | 晚绑定后的 typed union：`clean_strategy` 或 `registered_api_operation` | 解决 10 strategy 与 3 operation 混进同一字符串空间的问题 |
| `ObjectUploadSession` | 一次 upload 命令、一个 idempotency key、一个 pending/ref owner 的 durable 会话 | handle 表示字节；session token 表示调用权与取消/消费权 |
| `EvidencePlane` | append-only、可重算 digest、不可原地改写的事实/证明 | Fact、history、selection、artifact identity、publication/delete proof 等 |
| `ProjectionPlane` | 从 Evidence/State 投影出的可变查询加速面 | Task/Execution/Process status、Item pointer、outbox、read model |
| `CommandReceipt` | 所有 mutation 对外返回的 `applied/replayed/noop/rejected`、revision、retryability 与 causation | 取代前端靠 HTTP 时序猜幂等结果 |
| `OperationalSignalDefinition` | 一个 signal 的 metric/event/alert owner、labels、emitter、runbook 与 test 的闭集定义 | 目录存在但无 emitter 不算交付 |
| `ReleaseGate` | 阻止新 writer/cutover/closure 的可证伪条件 | waiver 只能延期外部 gate，不能把缺层测试改绿 |

### 1.2 参考调查报告

- `docs/code-review/new-harvest/NH1-NH9-2nd-pass-review-VF-ledger.md` — 52 条 VF、三类归属、第一轮 claimed-fix 推翻与 preliminary plan。
- `docs/closure/new-start/deferred-items-ledger.md` — 第一轮 NH deferred 及与 NS harness/supply/object/replay 的重叠债务。
- `docs/eval/new-harvest/final-execution-plan.md` — `T-O-376..407`、chosen workflow shape、原 NH1–NH9 DAG 与 OOS。
- `docs/closure/new-harvest/AP-NH1..AP-NH9` / `CROSS-NH-campaign.md` — 已交付边界、历史证据与未签收项；closure claim 不作为当前正确性证明。
- `src/persistence/migrations/018..024`、`src/runtime/`、`src/services/`、`api/`、`tests/` — 当前真实 schema、runtime、API 与验证面。

---

## 2. 在 MKB 中的定位

### 2.1 角色

- **整体架构角色**：这是一个跨 intake/workflow/storage/ops 的“权威边界修复层”，不是新业务 kind，也不是通用 workflow 平台。
- **服务对象**：
  - 对上游/leaf-worker caller：提供可发现但不可越权选图的 workflow/capability 目录、稳定 Task/Item/Namespace 读面和精确命令收据；
  - 对 worker/runtime：提供 observation、epoch、revision、session 四类 fence；
  - 对前端/operator：提供 redacted debug、dead-letter/repair/restart/stop、cleanup 状态与 retryability；
  - 对 release：提供 persisted-upgrade、race/crash、真实 supply 和全仓 regression 证据。
- **依赖**：冻结 Truth `T-O-376..407`、现有 Task/Execution/Process/Outbox 内核、S13 local CAS、S04 Item/Revision/Publication、S15 operator guard。
- **被依赖**：未来所有 new-harvest 新 Task、新 workflow revision、leaf-worker 分角色部署、物理 purge、production capability profile 与第三轮 code review。

### 2.2 与其他功能簇的交互矩阵

| 相邻功能簇 | 交互方向 | 耦合强度 | 说明 |
|------------|----------|----------|------|
| Public Task API / S01–S02 | 双向 | 强 | admission 创建 observation reservation；mutation 返回 CommandReceipt；Task view 投影实际绑定与 retryability |
| Workflow / S03 | 双向 | 强 | revision pin、ProcessCapabilityManifest、route reachability、Outcome terminal fence、dead owner policy |
| Intake / S04 | 双向 | 强 | Source/Observation/Snapshot/ItemEpoch 分账；accept/publish/lifecycle 全部 CAS |
| S05 actual binding | 双向 | 强 | actual digest 绑定 versioned path + typed ProcessingBinding，retry exact |
| Object / S13 | 双向 | 强 | session journal、reference transfer、cleanup job、catalog/CAS reconciliation |
| LS-RAG / S06–S10 | 下游 | 强 | CAS-first admitted clean、immutable artifact identity、publication manifest 与 retrieval verification |
| Runtime supply / S11/S16 | 双向 | 中 | capability deployment 独立于 workflow definition；role/profile readiness 与 security sign-off |
| Observability / S15 | 双向 | 中 | authoritative event/metric/diagnostic/control，不得成为第二状态机 |
| Test/evidence governance | 下游 | 强 | graph-derived denominator、真实 subprocess crash、old DB upgrade、evidence command execution |

### 2.3 一句话定位陈述

> “在 MKB 里，`NH-Coherent-Fixes` 是 **new-harvest 的权威边界与债务退役层**，负责 **把观察、Item、工作流、对象与运维状态分账并建立闭环 fence**，对上游提供 **可发现、可解释、可控制的稳定契约**，对下游要求 **所有事实先 durable、所有 mutation 有 CAS、所有 closure 有可证伪证据**。”

---

## 3. 架构稳定性与未来扩展策略

### 3.1 精简点（哪里可以砍）

| 被砍项 | 参考来源 / 诱因 | 砍的理由 | 未来是否可能回补 / 重评条件 |
|--------|------------------|----------|-----------------------------|
| “critical 先修、其余继续 defer”的三批 hotfix | 二轮 ledger §5 | 根因横跨身份/UoW/API，逐条补丁会重复改同一边界 | 不回补；action-plan 必须按本文业务簇 |
| `external_key == observation_key` | VF1/VF3/VF4/VF8 | Source/Item 长期身份与一次观察混用，必然导致 Snapshot 压缩或永久 409 | 永不回补 |
| v2 caller 直接提交 authoritative `clean_strategy` | VF15、`T-O-382/384` | actual worker 应在 durable representation 后由 compiled rule 晚绑定 | v1 仅兼容为 one-member policy constraint；不得冒充 actual |
| revision 1 原位演进 | VF17/NH-VF21 | 与 registry immutable digest 直接冲突 | 永不回补；任何 canonical 变化必须升 revision/formula version |
| critical state 放在 `payload_extra` | VF7/VF41 | 无 schema、无 migration、易在 retry 丢失 | payload_extra 只保留非控制性扩展 |
| acquire/decode/clean envelope 复制正文 | NH-VF3.r/VF28 | 放大秘密与正文、制造第二 SSOT | 改为 CAS ref/digest/typed fact 后删除旧 writer |
| 未使用的 `building/retiring` pointer 状态 | NH-VF36 | 预留枚举没有 writer/reader，只制造假能力 | 本 campaign 删除或收窄；真需要双态 cutover 时由独立 index design 重开 |
| dead metric/alert 仅因“目录已声明”而保留 | VF40 | 未 emit/无 runbook 的名字会误导运维 | AP-NHCF6 中“补 emitter 或删定义”二选一，禁止空目录 |
| 单进程 `leaf worker` 仅作为 FastAPI 标题 | VF48 | 角色、readiness、进程所有权不可配置 | 由显式 role profile 取代 |
| 将 `registered_api.map` 塞进 10 个 CleanStrategy 字符串空间 | VF20 | 3 个 provider operation 与 10 clean strategy 是不同 taxonomy | 使用 typed ProcessingBinding union，不再靠特殊字符串 |

### 3.2 接口保留点（哪里要留扩展空间）

| 扩展点 | 表现形式 | 第一版行为 | 未来可能的演进方向 |
|--------|----------|------------|---------------------|
| Observation policy | `observation_key` + reservation state machine | v2 显式 key；v1 single 默认 task UUID、registered_api 保留旧兼容 key | connector watermark、scheduled observation，但不改变 Source/Item identity |
| ProcessingBinding | `binding_family + binding_key + definition_version/digest` | `clean_strategy` 与 `registered_api_operation` 两族 | 新的受控 operation family；仍禁止自由 handler key |
| Workflow catalog | read-only `/v1/workflows`、`/v1/capabilities` | 可发现 kind/revision/rule/capability/availability，不可在 Task create 传 workflow key | 控制面版本协商；选择权仍由 server |
| Capability deployment | code-owned `ProcessCapabilityManifest` + role readiness | 编译期验证每个 required process 有实现与 supply owner | 独立 worker pool/remote executor，但 contract/digest 不变 |
| Object adapter | staging/promotion journal + ObjectStorePort | local CAS 可恢复两阶段 | remote backend；仍须 session/catalog/ref 一致性，不开放 raw public read |
| Evidence formula | `schema_version/formula_version` registry | selection/path/publication manifest 使用 v2 公式 | v3 只新增版本，不重解释旧 digest |
| Operator control | typed command + CommandReceipt | requeue/repair/restart/stop/cleanup status | 多人审批或自动 runbook；永不开放任意 SQL |
| Role profile | `api / workflow_worker / maintenance / all` | 同 binary 按角色启动组件并计算 readiness | 独立部署/水平扩展，不改变 API/DB owner |
| Existing-object upgrade | 仅预留新 intent/command 插槽 | 本设计不实现 | 新 owner-gate 冻结 upgrade identity、S05 与 DAG 后重评 |

### 3.3 完全解耦点（哪里必须独立）

- **SourceIdentity 与 ObservationReservation**：Source 可产生多次 Observation；Observation 失败/重试不能篡改 Source 或占死未来观察。
- **WorkflowDefinition 与 CapabilityDeployment**：图声明“需要什么”，manifest/readiness 证明“当前角色能否提供”；缺 supply 不得改图或由 handler 暗 fallback。
- **EvidencePlane 与 ProjectionPlane**：事实不可原地改；Task/Item/status 等 projection 可 CAS 更新，并可从事实重建/审计。
- **Object bytes 与 upload session/reference**：digest handle 不拥有取消权；session/ref 才拥有 TTL、consume、release、purge 权。
- **public safe view 与 operator debug/control**：public 只看业务必要且 redacted 的状态；operator 受 token+network+审计保护，可看 digest-verified debug 与发 typed control。
- **六态 Task status 与内部 phase/waiting reason**：不为解释性扩展随意增加 Task terminal enum；以 `phase/waiting_reason/result_disposition` 补足信息。
- **生产 supply 交付与 owner 外部签收**：代码、profile、readiness、真实探针必须完成；凭据、S16 具名签名与 deploy 仍由 owner gate，禁止伪造。

### 3.4 聚合点（哪里要刻意收敛）

- **Admission UoW**：Team/intent/applicability/source identity/observation reservation/Task/root Execution/command receipt 必须在一个 owner UoW 内提交；任何非法格零 Task、零 reservation 残留。
- **Outcome UoW**：Execution/Process active fence、fact/history append、selection/actual seal、artifact registration、下一 Process materialize 必须一次提交；terminal owner 永远不能再推进。
- **Item mutation UoW**：accept revision、latest/serving/lifecycle、ItemEpoch、transition ledger 与 publication proof同一 CAS owner。
- **Object lifecycle state machine**：receive/prepared/promoted/committed/consumed/released 与 quarantine/tombstone/destroy 全部由 durable session/job 表统一表达。
- **Capability catalog**：source kind、workflow revision、route reachability、10 strategy、3 operation、process implementation、supply availability 从同一编译产物投影。
- **Operational signal catalog**：event/metric/alert/diagnostic/runbook/test 五元组集中登记，代码扫描保证无死 emitter、无死目录。
- **Debt/release manifest**：所有 VF/deferred/test/owner gate 在一个 append-only coverage manifest 中一一归属，第三轮 review 直接以此为分母。

---

## 4. 本仓库 precedent 对比

### 4.1 冻结 NH chosen-shape

- **实现概要**：kind-only resolver、selected-output CONTROL、typed representation history、sealed actual S05、reference-first GC、Task/Execution/Process/Outbox durable state 已建立。
- **亮点**：事实先 durable、old pin exact、Outcome UoW、无 raw public GET、retrieval double fence 是正确的长期方向。
- **值得借鉴**：保留这些 owner 边界，不重写成通用 workflow 或消息队列。
- **不打算照抄的地方**：不能继续用 revision 1、payload_extra、manifest digest alias、incidental child status 来证明这些边界已经闭合。

### 4.2 现有 CAS / outbox / lifecycle precedent

- **实现概要**：Process fencing generation、Task row revision、publication pointer CAS、outbox dedupe 与 lease recovery 已提供基本原语。
- **亮点**：`project_task_status_tx`、`publish_revision_tx`、`recover_expired_leases` 展示了单 owner + rowcount fence 的正确形状。
- **值得借鉴**：所有新增 control/recovery 都复用 typed command、idempotency key、expected revision 与 domain event。
- **不打算照抄的地方**：不能把所有 `ConflictError` 都视作 stale fence，也不能让 outbox dead 与 owning Execution 脱钩。

### 4.3 S13/S15 precedent

- **实现概要**：S13 使用 object reference ledger、quarantine、delete proof；S15 使用 tenant-scoped timeline、closed metric labels、redaction 与 retention。
- **亮点**：reference-first 删除、operator token+network guard、低基数 metric 是稳定安全边界。
- **值得借鉴**：物理删除只由引用/cleanup truth决定；debug/control 不公开 raw data。
- **不打算照抄的地方**：catalog 外 final CAS、tombstoned quarantine、session-less cancel、无 emitter metric 和只存在内存的 supervisor error 必须被 durable state 替代。

### 4.4 横向对比速查表

| 维度 | 当前局部修复形态 | 冻结 contract 的正确内核 | 本设计选择 |
|------|------------------|--------------------------|------------|
| 观察身份 | external key 复用 Snapshot | intake 是变换 SSOT、replay fail-loud | SourceIdentity + ObservationReservation + immutable Snapshot |
| retry | 复制 actual 后从 start 重跑 | full_task exact | frozen observation/artifact resume；无物料则拒绝 full replay |
| workflow 演进 | rev1 Python 定义可漂 | immutable revision / old pin | rev2+compat fixture+retirement inventory |
| processing taxonomy | strategy 与 API map 混字符串 | 10 strategy + 3 operation | typed ProcessingBinding union |
| object upload | digest handle + 随机 hold | catalog+pending 同 UoW后 usable | durable upload session + exact ref transfer + promotion journal |
| evidence | 部分 trigger、部分普通 SQL 可改 | fact/history authority | evidence/projection 分面 + formula version + verification ledger |
| leaf worker | monolith 标题 | caller 不选图、需要实际 worker | read-only catalog + role-specific manifest/readiness |
| 运维 | timeline/dead list，无 repair | fail-loud / durable recovery | typed control + receipt + audit + owner terminalization |
| assurance | 手写 cell、hook、文件存在 | L1–L4 不可互换 | graph-derived matrix、subprocess crash、命令型 evidence checker |

---

## 5. In-Scope / Out-of-Scope 判断

### 5.1 In-Scope（本设计确认要支持）

- **[S1] Canonical identity 与 admission** — Source/Observation/Snapshot/Item/Task 分账是 VF1–VF5/VF8–VF12 的共同根因，必须先修。
- **[S2] Workflow/version/replay/outcome** — rev2 compatibility、terminal Outcome fence、current-hop routing、exact retry、typed error family 是动态工作流可长期演进的前提。
- **[S3] Evidence 与 artifact authority** — selected fact、path/publication formula、stage CAS-first、append-only 与 legacy verification 必须统一，否则可解释性仍是假账。
- **[S4] Object session/reference/cleanup/purge** — upload replay、cancel、TTL、pre-catalog、quarantine、Item delete 物理释放构成同一对象生命周期，必须一簇闭合。
- **[S5] Production capability、security、role readiness** — 真实 parser/browser/OCR/model profile、no-sandbox、concurrent-write 画像、leaf-worker 角色与 supply discovery 一并完成。
- **[S6] Discovery/read/debug/control** — workflow/capability、Task actual、Item/Namespace/Process/Stage/Fact、dead outbox、retry/restart/delete/stop 必须形成前端和 operator 可用契约。
- **[S7] Operational signal governance** — admission、supervisor、GC、TTL、repair、outbox、readiness 的 event/metric/alert/diagnostic 必须有 owner 和 emitter。
- **[S8] Forward migration、compat retirement、physical cleanup** — 只新增 migration，旧事实不伪造 backfill；dual-read/write、cutover、retirement 与 rollback 法必须设计在先。
- **[S9] Graph-derived assurance 与 release** — 所有 valid VF、吸收 deferred、old DB、race/crash、real supply、全仓测试、evidence execution 与 owner sign-off 共同作为 closure 分母。

### 5.2 Out-of-Scope（本设计确认不做）

- **[O1] raw object read/export/presign/remote object** — 与本轮上传所有权、GC 正确性无关，并受 `T-O-396` 限制；重评条件：新的导出安全 QNA。
- **[O2] 第五 kind/live connector/cookie/tunnel** — 本轮只治理已冻结四 kind；重评条件：新的 intake completeness Truth。
- **[O3] caller workflow selection、通用 JOIN/DSL/loader** — 会重开 `T-O-379/398`；重评条件：独立 workflow-platform charter。
- **[O4] existing-object new-cleaner/validator upgrade** — 当前 retry 必须 exact；重评条件：按 `T-O-401` 新 owner-gate 冻结 operator command、identity 与 migration。
- **[O5] external vector engine** — 本轮修 publication identity/read snapshot，不换 serving substrate；重评条件：vector backend charter。
- **[O6] experiment launch/score** — 不是产品正确性 DoD；重评条件：`T-O-380` 单独发车。
- **[O7] 任意 SQL/debug raw payload 公共面** — 永不作为 repair shortcut；operator 也只能使用 typed、审计、带 CAS 的 control。

### 5.3 边界清单（容易混淆的灰色地带）

| 项目 | 判定 | 理由 | 后续落点 |
|------|------|------|----------|
| workflow/capability 目录 GET | `in-scope` | 可发现不等于可选图；上游需要分类、列表、availability | AP-NHCF6 |
| public Task actual binding | `in-scope` | 是已发生事实，不泄漏 handler/secret | AP-NHCF6 |
| process/stage/fact/debug payload | `in-scope / internal-only` | operator 需要，public 不需要；必须 redacted、digest-verified | AP-NHCF6 |
| process kill/restart、outbox requeue | `in-scope / internal-only` | 取代人工 SQL；需 state fence 与 receipt | AP-NHCF3/AP-NHCF6 |
| physical Intake purge | `in-scope` | VF25 与 open cleanup intent 已证明 logical-only 不能长期维持 | AP-NHCF4/AP-NHCF7 |
| 真实模型与 browser S16 | `in-scope + owner gate` | adapter/profile/test 属工程交付，外部凭据与签名不可伪造 | AP-NHCF5/AP-NHCF8 |
| multi-writer backend | `defer product substrate, fix truth now` | 本轮必须让 required=false/true 与 readiness 一致；不承诺新分布式数据库 | AP-NHCF5 |
| six Task states | `保留` | waiting 不是新的业务 terminal；补 phase/reason 即可解释 | AP-NHCF6 |
| index pointer building/retiring | `cut` | 无 writer 的预留不是能力；删除比实现假状态更内聚 | AP-NHCF1/AP-NHCF7 |
| v1 public `clean_strategy` | `compat-only` | 转为 policy constraint 并 deprecate；v2 不把它当 actual | AP-NHCF1/AP-NHCF3 |

---

## 6. Tradeoff 辩证分析与价值判断

### 6.1 核心取舍

1. **我们选择业务簇治理 campaign，而不是 finding-by-finding hotfix。**
   - **为什么**：VF1/3/4/5、VF6/7/13/15/16/17、VF22/23/24/25 分别共享同一身份或 UoW 根因。
   - **我们接受的代价**：迁移和 action-plan 数量增加，短期不会最快关闭 critical 数字。
   - **未来重评条件**：不重评；这是本轮 owner 明确要求。

2. **我们选择显式 ObservationReservation，而不是继续从 external key/fingerprint/Task UUID 猜 observation。**
   - **为什么**：它同时解决并发双 201、失败后永久 409、single Snapshot 压缩与 scatter 信封时序。
   - **我们接受的代价**：public v2 增加 observation key，v1 需要兼容派生。
   - **未来重评条件**：可扩展 key 生成策略，但不可重新合并 Source/Observation。

3. **我们选择一个 ItemEpoch（逻辑复用 row_revision），而不是另加 lifecycle/content 两个会漂移的 counter。**
   - **为什么**：所有 canonical mutation 都应互相 fence；单调一个序号最容易验证。
   - **我们接受的代价**：合法并发更新更保守，败者需要重读重试。
   - **未来重评条件**：只有真实吞吐证据证明冲突不可接受时才拆分子资源 ETag。

4. **我们选择新 workflow revision/formula version + old-pin exact，而不是修补已有 rev1 行。**
   - **为什么**：旧 digest 已持久化；原地修复等于破坏证据。
   - **我们接受的代价**：需要维护 compat definition、upgrade fixture 和 retirement inventory。
   - **未来重评条件**：永不允许同 revision 异 canonical digest。

5. **我们选择 frozen observation/artifact resume，而不是 full retry 再访问 HTTP/API。**
   - **为什么**：重访外部世界是新观察，不是 exact retry。
   - **我们接受的代价**：没有 durable input 的失败 Task 不能 full retry，必须创建新 Observation。
   - **未来重评条件**：若产品要 refresh，新增显式 `new_observation` 命令，不能复用 retry。

6. **我们选择 durable upload session + ref transfer，而不是把 digest handle 当 session。**
   - **为什么**：同字节可能有多个调用者/TTL/取消/消费，字节身份无法表达 owner。
   - **我们接受的代价**：upload/cancel/local_object contract 增加 session token。
   - **未来重评条件**：即使换 remote store，session/ref 分账仍保持。

7. **我们选择 forward-only evidence correction，而不是 UPDATE 历史“修成正确”。**
   - **为什么**：已经失实的 digest 不能靠改值变成当时事实。
   - **我们接受的代价**：legacy 行会保留 `legacy_unverifiable/invalid`，新 assertion 需要 supersedes 链。
   - **未来重评条件**：永不原地改 evidence；只能改变 projection/verification verdict。

8. **我们选择可发现但不可提交的 workflow catalog，而不是继续完全隐藏或开放 workflow selection。**
   - **为什么**：leaf-worker 上游需要分类、列表、availability；`T-O-379` 只禁止 caller 选图。
   - **我们接受的代价**：需要稳定 public schema 和兼容承诺。
   - **未来重评条件**：若目录字段会暴露内部拓扑，只在 operator 面提供该字段。

9. **我们选择 public safe summary + internal debug/control 双面，而不是把完整 payload 塞进 timeline 或让 operator 查 DB。**
   - **为什么**：既满足可解释性，也保持 S15/S16 redaction 与权限边界。
   - **我们接受的代价**：需要两套 response model、审计和权限测试。
   - **未来重评条件**：不开放任意 payload/SQL；只扩 registered debug schema。

10. **我们选择 role/profile-specific readiness，而不是一个 `/ready` 代表所有能力。**
    - **为什么**：API、worker、maintenance 的 required components 不同；配置要求必须真实进入 overall。
    - **我们接受的代价**：部署配置和 runbook 更明确，也更严格。
    - **未来重评条件**：新增 role 需声明 owner、components、failure policy。

11. **我们选择真实 production profile gate，而不是用 stub/fixture 继续声称 10+3 live。**
    - **为什么**：`T-O-376/378/381` 禁止假接线。
    - **我们接受的代价**：最终 closure 可能等待外部模型、binary、S16 签名窗口。
    - **未来重评条件**：owner 可具名延期 release，但不得把对应 L3/L4 改成 PASS。

12. **我们选择有状态 cleanup job 和 retention 后 purge，而不是 delete 立即递归 unlink。**
    - **为什么**：业务引用、generation、vector、proof 与 recovery window 需要可审计收敛。
    - **我们接受的代价**：删除不是瞬时物理释放，API 必须展示 cleanup progress。
    - **未来重评条件**：retention policy 可改，reference-first 法不改。

### 6.2 风险与缓解

| 风险 | 触发条件 | 影响 | 缓解方案 |
|------|----------|------|----------|
| migration 把 legacy 行伪造成 v2 evidence | 对旧行自动填新 digest/actual/session | 历史假绿 | 只 backfill projection；evidence 写 verification ledger=`legacy_unverifiable`，不造当时不存在的事实 |
| dual-write 漂移 | v1/v2 writer 同时运行 | read model 不一致 | shadow compare + mismatch metric + admission cutover gate；任何 mismatch 阻断 contract phase |
| old workflow pin 被删 | 只保留 active rev2 | retry/恢复 503 | persisted DB fixture、pin inventory、zero-pin+retention 后才 retirement |
| observation reservation 泄漏 | Task 在 acquire 前崩溃 | 同 key 长期 409 | reservation lease + owner Task terminal reconciliation + typed reclaim command |
| session token 泄漏或误消费 | handle/session 混用 | 释放他人 hold或 TTL 杀合法 Task | token hash、team fence、exact owner transfer、reserved session 不过期 |
| evidence 全量校验拖慢 retrieval | 每次查询重算整个 generation | 延迟/内存上涨 | publication manifest + read snapshot + sampled background auditor；只验证命中成员与 active manifest |
| operator control 误伤新世代 | requeue/kill 不带 fence | stale command 跨 generation | expected revision/generation + CommandReceipt + first-wins + audit + dry-run read |
| debug 泄密 | 输出 stage/audit raw JSON | secret/body 外泄 | registered redacted projection、payload digest 校验、operator guard、无 raw object read |
| production profile 长期被外部 gate 卡住 | model/S16/真机 unavailable | campaign 无法 final close | 工程 AP 可完成为 `ready-for-owner-gate`；release 明确 blocked，绝不改成 deferred complete |
| scope 蔓延成通用 workflow/storage 平台 | 借治理增加 DSL/remote store | 无法收口 | §5 OOS + AP coverage manifest + 每 AP architecture redline scan |
| 全仓测试成本过高 | L1–L4+subprocess crash+upgrade | 反馈慢 | PR 分层短套件；nightly/full release gate；四层仍不可互换 |

### 6.3 本次 tradeoff 能带来的价值

- **对开发者自己（我们）**：任何“这次调用是否重放、卡在哪一步、绑定了谁、还能否重试、字节由谁拥有”都能从一个稳定接口回答，不再需要临时 SQL 和日志猜测。
- **对 MKB 的长期演进**：新 workflow revision、source observation、supply role 或 object backend 都有明确扩展点，不需要破坏已持久化 digest。
- **对 intake / dynamic workflow / 稳定性三大方向的杠杆作用**：四通道共享同一 observation/epoch/session 法；dynamic workflow 共享 version/capability/replay 法；稳定性共享 evidence/control/assurance 法，减少每个新 kind/strategy 重复发明竞态补丁。

---

## 7. In-Scope 功能详细列表

### 7.1 功能清单

| 编号 | 功能名 | 描述 | 一句话收口目标 |
|------|--------|------|----------------|
| F1 | Debt truth 与 forward migration foundation | 冻结 debt universe、schema/version/compat 法、legacy verification 与 cutover gates | ✅ 每个 VF/deferred 恰好一个 owner AP，migration 可前滚且不伪造旧事实 |
| F2 | Observation / ItemEpoch canonical identity | Source、Observation、Snapshot、Item、Revision 分账；admission reservation 与所有 Item mutation CAS | ✅ 并发、失败重试、内容变化、delete/reactivate 都有唯一可预测结果 |
| F3 | Versioned workflow / replay / Outcome | rev2+old pin、capability manifest、typed binding、terminal fence、exact retry、dead owner | ✅ terminal 后零推进，retry 不重观测，所有 declared edge 都可编译和恢复 |
| F4 | Evidence / artifact / secure envelope | append-only evidence、正确 digest 代数、CAS-first stage、publication manifest、递归拒密 | ✅ 普通 SQL 不能改写已宣称事实，wire 不复制正文/秘密，retrieval 可验证 publication set |
| F5 | Object session / reference / cleanup | durable upload session、promotion journal、exact transfer、GC deletion job、Item purge | ✅ 每个字节和 hold 都有 owner；任一 crash 后可恢复或回收，无 invisible CAS/quarantine |
| F6 | Capability deployment / role / readiness | 真实 supply profile、ProcessCapabilityManifest、api/worker/maintenance roles、truthful readiness | ✅ prod 不以 stub ready，配置为 required 的能力失败必然阻止对应角色接活 |
| F7 | Discovery 与 strict read models | workflow/capability/strategy/operation、Task actual、Item/Namespace/Process/Stage/Fact 读面 | ✅ 上游和前端不查 DB 即能发现、分类、轮询并解释实际流程 |
| F8 | Typed control / observability / error governance | receipt、retry/restart/stop/requeue/repair、diagnostics、metrics/alerts、canonical error registry | ✅ 每个控制动作可判 applied/replay/noop，故障有 durable signal 与安全操作出口 |
| F9 | Compatibility / retirement / physical convergence | dual-read/write、old revision pin、legacy alias/evidence verdict、cleanup/purge、dead enum/definition retirement | ✅ 新 writer 唯一，旧任务仍 exact，旧形状只在零 pin/零 ref 后退役 |
| F10 | Graph-derived assurance / release | L1–L4、race/crash、old DB、real supply、全仓、evidence executor 与三轮复审 | ✅ closure 由执行证据证明，无 open in-scope debt、无 fake-green、无未解释 waiver |

### 7.2 详细阐述

#### F1: Debt truth 与 forward migration foundation

- **输入**：二轮 `VF1..VF52`、第一轮 `NH-VF*.r`、直接相关 NS carry-over、HEAD schema/version inventory。
- **输出**：
  - append-only `coherent-fixes coverage manifest`（finding → root cause → feature → AP → test → closure）；
  - `CF-D01..CF-D14` 决策冻结结果；
  - migration `025+` 的 expand/backfill/validate/cutover/contract 序列；
  - persisted pre-fix database 与 workflow rev1 canonical fixture。
- **主要调用者**：后续全部 AP、migration runner、第三轮 reviewer、release owner。
- **核心逻辑**：
  1. 不修改 `001` 或 `018..024` 来重写历史；新 invariant 只通过新 migration 前滚。
  2. 把表分为 `immutable evidence`、`mutable authority`、`rebuildable projection`、`ephemeral/retention` 四类；每类冻结可变列、删除法和修复法。
  3. legacy 行只允许得到 `verified | invalid | legacy_unverifiable` 的旁路 verdict；禁止把新公式、新 actual、新 session backfill 成“当时已存在”。
  4. 每个 action-plan 在开始前必须有修前 RED 或静态 invariant failure；没有分母不得写代码。
- **边界情况**：
  - 现有 selected-output 行值错：写 v2 correction assertion/supersedes，不 UPDATE 旧行。
  - rev1 builtin 与 persisted digest 冲突：先加载 checked-in rev1 fixture，再注册 rev2；应用不得以空库测试代替升级。
  - 未使用 schema enum：通过 contract migration 删除/收窄，不为“偿还 deferred”而造无业务 writer。
- **一句话收口目标**：✅ **任何债务、旧数据和迁移阶段都有唯一状态与 owner，不靠改历史或文档措辞收口。**

#### F2: Observation / ItemEpoch canonical identity

- **输入**：v2 `TaskCreate`、`SourceIdentity`、显式 `observation_key`、当前 ItemEpoch、source bytes/records。
- **输出**：ObservationReservation/Attempt、immutable Snapshot、ChangeSet、Revision/Item transition、Task/Execution 坐标与 CommandReceipt。
- **主要调用者**：四 intake admission、acquire/accept callback、lifecycle/rebuild/metadata/publication。
- **核心逻辑**：
  1. `(team, source_kind, normalized_external_key)` 唯一解析 `SourceIdentity`；v2 observation key 在该 Source 下唯一。v1 single request 从 `task_uuid` 派生兼容 key，v1 registered API 保留旧 external-key 语义并标 deprecated。
  2. admission UoW 同时创建/采用 SourceIdentity、ObservationReservation、Task 与 root Execution。`reserved/acquired` 的同 key 并发请求返回 409；`accepted` exact replay 返回原坐标；异 fingerprint 返回 conflict。
  3. `ObservationAttempt` append-only：失败可通过 typed retry CAS 增加 attempt generation；accepted 为终态，不删除 Snapshot。新一次真实观察必须使用新 observation key。
  4. acquire 完成后先绑定 raw artifact/fingerprint，再由 acceptance 创建**新的** Snapshot。不同 observation 即使同 Source 也不复用 Snapshot；同内容可以复用 Revision，但 ChangeSet 必须写显式 `no_change` fact。
  5. `ItemEpoch` 逻辑上使用 Item 的单一 `row_revision`：latest、serving、lifecycle 任何变化都递增。每个 Execution input 冻结 expected epoch，accept/publish/rebuild/metadata/lifecycle 都以它 CAS。
  6. deactivated/deleted 同 key ingest、同态 lifecycle、新旧 rebuild applicability 在 admission 决定；非法格零 Task。delete 后重新占用同 external key 不被隐式允许。
  7. scatter 先采用 Source/Observation identity，再创建 stage material；stage state只带 observation UUID，不冻结待替换的随机 source UUID。
- **边界情况**：
  - 两个不同 observation 同时更新一个 Item：至多一个 latest CAS 成功；败者有 typed `ITEM_EPOCH_CONFLICT`，其 Snapshot 可保留为已观察但未采纳证据。
  - delete 与迟到 accept/publish：expected epoch 不同，callback 不改 Item、pointer 或 vector publication。
  - team-scope index rebuild 中一个 target stale：整份 frozen target set fail-loud；不得 `continue` 后成功。初始空集合才是 `index_rebuild_noop`。
  - Task cancelling 与 worker failure 竞态：Task cancel wins；Process failure留作 evidence，不能把 Task 投影成 failed。
- **一句话收口目标**：✅ **四通道每一次观察、采纳、生命周期变化都有独立 identity 与 CAS，零静默压缩、零跨 Task 穿透。**

#### F3: Versioned workflow / replay / Outcome

- **输入**：SourceKind、Observation/facts、WorkflowRevisionPin、ProcessingPolicy、Process Outcome、operator/runtime command。
- **输出**：compiled reachability、typed ProcessingBinding、actual seal v2、terminal Execution/Task、restart/outbox owner result。
- **主要调用者**：registry bootstrap、runtime materialize/outcome/worker/repair、Task retry、leaf-worker dispatcher。
- **核心逻辑**：
  1. current builtin graph 升为 revision 2；checked-in rev1 exact definition永久可加载，直到 pin inventory 为零且超过 retention。canonical/compiled/capability/formula 任一变化必须升版本。
  2. `ProcessCapabilityManifest` 为 code-owned registry：每个 required process 声明 handler contract、role、supply、retry/side-effect/recovery law。registry 拒绝 unknown capability，readiness 投影部署 availability。
  3. `ProcessingBinding` 使用 `binding_family=clean_strategy|registered_api_operation`；10 strategy 与 3 provider operation分别引用自身 definition version/digest。public v1 `clean_strategy` 仅映射为 one-member policy constraint；实际绑定仍在 facts durable 后发生。
  4. compiler 生成每个 `(revision, from_step, outcome, fact-state)` 的 reachable route/strategy matrix。runtime 只检查当前 hop candidates，不再扫描整张图是否含某 guard。
  5. Outcome UoW 首先要求 Process running、fencing generation/current_process 匹配、Execution 属于 active set、Task generation/ItemEpoch仍有效；之后才执行 committer、Process terminal、route/actual seal、下一 Process materialization。任一 owner rowcount 失败整笔回滚。
  6. 引入明确的 `FenceConflict`/`LeaseConflict` 与 `DomainConflict` 类型；worker 只吞前两者，domain mismatch 必须提交 typed failed Outcome，不能留下 running。
  7. full Task retry 只从 frozen Observation/Snapshot/manifest恢复，并复制 typed execution context（含 metadata disposition）；不再调用 HTTP/API。没有 durable external input 时返回 `FULL_REPLAY_INPUT_UNAVAILABLE`，caller 必须发新 observation。
  8. outbox 增加 owner coordinates 与 terminal policy。永久 dead 时，同 UoW 将 owning Execution/Task 终结为 typed failure或登记 advisory disposition；不得留下 ready/queued owner。
- **边界情况**：
  - terminal Execution 收到相同迟到 Outcome：返回 `accepted=false/replayed`，不改 Process、不物化下一步；异 Outcome 返回 fence conflict。
  - old rev1 retry：exact old graph/actual/formula；新 capability不热切。
  - HTTP static→browser reacquire 后 absent：只按当前 decode step 的声明边选择 clean/print/failure；没有全图特判。
  - `registered_api.map`：绑定为 provider operation，不冒充第 11 个 clean strategy。
  - stale `_fail_process_tx`：业务 UoW不写失败，但在独立、best-effort diagnostic channel记录 fence rejection；新世代不受影响。
- **一句话收口目标**：✅ **同一 revision、observation、generation 的执行可 exact replay；终态、版本和 owner fence 永远优先于迟到工作。**

#### F4: Evidence / artifact / secure envelope

- **输入**：acquire/decode/selection/clean/generation/vector/publication/delete 事实与 CAS artifacts。
- **输出**：versioned append-only assertions、artifact refs、publication manifest、verification verdict 与 redacted debug projection。
- **主要调用者**：route/actual seal、retrieval、debug API、migration auditor、release evidence checker。
- **核心逻辑**：
  1. EvidencePlane 最少包含 RepresentationFact/History、SelectedOutputAssertion、Snapshot/ChangeSet facts、Intake/Generation artifact identity、PublicationManifest/Proof、ObjectDeleteProof；禁止 UPDATE/DELETE，或对所有 identity 列做 column trigger。
  2. selected-output v2 从 durable representation fact 取 `fact_digest`，统一调用一个公式实现；output manifest digest 与 fact digest 永不别名。selection/path/publication 公式均带 version。
  3. vector identity（artifact、unit、content digest、model、dimension、embedding digest/bytes）sealed 后不可改；availability/indexed/withdrawn 放在独立 mutable projection，避免通过改 state 绕过 identity trigger。
  4. acquire/decode/clean stage envelope 只持久化 typed ref/digest/size/fact UUID；raw/clean/records/body 先进入 Team-scoped CAS 并有 object reference。Audit 保存 redacted identity，不保存 signed URL、secret-shaped nested bag 或正文。
  5. 所有 public `PayloadExtraModel` 在基类递归执行 `assert_safe_public_data`；URL admission 禁 userinfo/signed secret query，并只持久化 normalized/redacted identity与受控 target ref。
  6. publication UoW 生成按 vector identity排序的 immutable manifest，proof/pointer引用其 digest。retrieval 在 Persistence `read_snapshot()` 中验证 active pointer/proof/manifest 与命中记录，不依赖普通 SQL 行可变假设。
  7. legacy evidence 由 verification ledger判为 verified/invalid/unverifiable；纠错写新 assertion，不修改旧 bytes。
- **边界情况**：
  - legacy selected output 值错但 route仍 exactly-one：保留旧行，写 v2 correction；public/operator view明确 `evidence_status`。
  - 大 generation：在线只验证命中记录与 manifest membership，后台 auditor 分批全量重算；异常使对应 publication fail closed。
  - debug 请求完整 payload：只返回注册 schema的 redacted projection和原 payload digest，不返回 CAS raw bytes。
- **一句话收口目标**：✅ **事实可证明、可版本解释、不可普通 SQL 重写；大正文只存在于受引用 CAS，不横穿状态信封。**

#### F5: Object session / reference / cleanup

- **输入**：authenticated upload command/idempotency key、byte stream、session token、local_object ingest、delete/retention/GC tick。
- **输出**：ObjectUploadSession、catalog/ref、promotion/deletion job、cleanup proof、safe status/receipt。
- **主要调用者**：public upload/stat/cancel、Task admission、acceptance、Item delete cleanup、maintenance worker。
- **核心逻辑**：
  1. upload 先验证 Team并在 DB 创建带随机 `staging_id` 的 session=`receiving`，storage只能写该session staging；fsync完成后CAS写 `prepared(digest,size)`，再 promote deterministic CAS；最后同 UoW提交 catalog+一个 exact `upload_pending` reference+session=`committed`，此后才返回 handle与 session token。
  2. crash recovery scanner以 session journal为权威：prepared+staging 可继续 promote；prepared/promoted 无 catalog可 finalize或过期删除；catalog+缺 bytes标 integrity failure并阻止使用。CAS inventory scanner只处理 journal可归因对象。
  3. 同 idempotency key replay返回同 session/ref；新 idempotency key即使相同字节也产生独立 session/ref。cancel/TTL/ingest都必须指定 session owner，绝不按“最新/全部 pending”释放。
  4. Task admission把 committed session CAS 为 `reserved_by_task`，TTL 不释放；acceptance只转移该 session为 snapshot/revision业务 ref。Task terminal未消费则由 reconciliation释放。
  5. local_object 只接受可转移的 upload session或明确 business reference，不接受“任意 live ref”。
  6. Item delete创建 durable cleanup job，枚举 snapshot/revision/generation/vector/object refs，按 retention 和 substrate executor推进；状态与失败对 operator可读。业务 ref 全释放后才让 GC候选。
  7. GC deletion job显式记录 selected→quarantined→tombstoned→destroyed。reconcile 对 live catalog恢复 quarantine，对 tombstoned catalog完成 destroy；两种都不会永久跳过。
- **边界情况**：
  - 相同字节两 session：取消 A 不影响 B；消费 A 后 B仍可单独取消/过期。
  - crash 在 promote 与 catalog：session=`prepared/promoted` 能找到 final CAS；不存在“扫描器都看不见”的文件。
  - crash 在 tombstone 与 destroy：job/tombstone使下次 scanner执行 destroy。
  - delete 后仍有 operator/backup hold：cleanup显示 blocked，不强行 unlink。
- **一句话收口目标**：✅ **字节、上传调用、业务引用和物理删除各有 durable owner，重放与崩溃都能收敛。**

#### F6: Capability deployment / role / readiness

- **输入**：ProcessCapabilityManifest、deployment role/profile、binary/model/supply probes、persistence capability与 owner waiver。
- **输出**：role-specific readiness、capability availability目录、真实 adapter evidence、security sign-off state。
- **主要调用者**：API admission、worker claim、deployment/orchestrator、upstream discovery、release gate。
- **核心逻辑**：
  1. role 明确为 `api`、`workflow_worker`、`maintenance`、`all`；lifespan只启动该 role拥有的 supervisor/GC/retention。每个 role有独立 required component set。
  2. `dev/test/prod` profile 明确：stub只允许 test；prod要求 subprocess/真实 endpoint、PDF parser、browser render/print、OCR、multimodal等 manifest中声明的 supply。
  3. `concurrent_writes_required`、`runtime_supply_readiness_required` 等配置必须实际加入该 role overall；serialized writer profile显式声明 `single_writer`，不再默认 require true后忽略 false。
  4. worker claim按 process capability availability过滤；缺 supply在 admission或dispatch前返回 typed unavailable，不让 Process进入 running再失败。
  5. browser guard检查即将提交的实际 args/capability；non-root、no `--no-sandbox`、S16 egress、profile identity、DOM/%PDF proof均为 prod gate。
  6. bounded pool concurrency只在 heartbeat/fencing/subprocess-kill suite通过后开启，吸收历史 overlapping `run_once` debt。
- **边界情况**：
  - API-only role不因本机无 browser而不可提供 catalog/reads，但创建需要该 capability的 Task会根据可路由 worker manifest fail closed。
  - worker supervisor连续失败超过阈值：worker readiness=false、持久化 diagnostic/metric/alert，API liveness仍真。
  - owner尚未提供模型凭据或S16签名：profile状态=`awaiting_owner_gate`，不能标 production-ready。
- **一句话收口目标**：✅ **“图声明、部署供给、角色可接活、release已签收”四件事分别可读且一致。**

#### F7: Discovery 与 strict read models

- **输入**：registry/capability manifest、Task/Execution/Process、Item/Snapshot/Namespace、Evidence verification。
- **输出**：严格 OpenAPI models、cursor-bounded public/operator reads、稳定 filter 与 links。
- **主要调用者**：leaf-worker 上游、前端、SDK、operator、测试。
- **核心逻辑**：
  1. authenticated read-only catalog提供 source kinds、workflow revisions、processing policies、10 strategies、3 operations、required/deployed capabilities、availability与 compatibility status。Task create schema仍不接受 workflow key/process key。
  2. Task view新增 source kind、observation UUID/key、declared acquisition mode、processing policy、actual binding family/key、workflow revision、snapshot/item、phase/waiting reason、operation mode、retryable、error message（redacted）。
  3. Task list支持 status/intent/source_kind/created filters；Intake Item list支持 lifecycle/source kind/external key；Namespace list提供 team-scoped key/model/dimension/status；所有 cursor绑定 filter digest。
  4. `/tasks/{id}/items` 对 single 使用 root/Task outcome，不依赖不存在的 child；scatter继续使用 membership+child summary。
  5. public仍保持六 Task 状态；fan-in/retry/gate通过 `phase`、`waiting_reason`、counts暴露，避免 waiting伪装成无解释 running。
  6. operator read增加 Process、stage report、representation fact/history、selection/actual、cleanup job、diagnostic与outbox owner视图；默认不回 raw payload。
  7. 所有 route声明 `response_model`；OpenAPI不得出现业务 response `additionalProperties: true` 或空 schema。
- **边界情况**：
  - old rev1 execution：actual/evidence字段可为 `legacy_unverifiable`，不能伪造新绑定。
  - 另 Team UUID/handle/item/namespace：保持 404/403等价防枚举。
  - availability随 deployment变化：目录返回 manifest revision/observed_at，不改变 workflow revision digest。
- **一句话收口目标**：✅ **上游能发现“可做什么”，前端能解释“实际做了什么”，但任何 caller仍不能指定图内步骤。**

#### F8: Typed control / observability / error governance

- **输入**：mutation command、expected revision/generation、idempotency key、operator auth、domain/supervisor/GC/outbox events。
- **输出**：CommandReceipt、typed control result、domain/diagnostic signals、metrics/alerts/runbooks、canonical errors。
- **主要调用者**：public frontend、operator UI/runbook、supervisor、alerting、第三轮 tests。
- **核心逻辑**：
  1. create/cancel/retry/delete/lifecycle/upload-cancel与 operator controls统一返回 `command_uuid/fingerprint/disposition/applied/current_revision/retryable/links`；HTTP status不再是唯一幂等信号。
  2. internal controls至少包含 outbox `requeue|abandon`、Execution `repair|stop`、Process `restart`、cleanup `resume`；每个命令都带 expected owner generation与审计，不能原地把 terminal Process改回 ready，restart创建新 attempt/generation。
  3. dead outbox必须先有 owner terminalization；requeue只针对已修复原因且生成新 delivery generation。repair有 dry-run/read model，执行后有 receipt。
  4. supervisor/GC/upload TTL/admission/repair/stale-fence均写 durable、redacted diagnostic/event；DiagnosticSink拥有读取 API和 bounded retention。
  5. `OperationalSignalDefinition` 要求每个 metric有 emitter owner、allowed labels、alert/runbook或明确 no-alert。目录审计删除未用系列或补齐 emitter；alert有实际 evaluator，而非只列 `ALERT_*` 字面。
  6. 建立 error registry：canonical code、HTTP status、category、retryable、public message、legacy aliases。v2统一 `UPPER_SNAKE_CASE`；v1 alias受文档兼容，不再新增 kebab/snake 双轨。
  7. admission拒绝也进入安全审计/metric，但不建业务 Task；payload只记录 code、kind、policy digest等低敏坐标。
- **边界情况**：
  - 重放同一 cancel/retry：receipt=`replayed`且引用第一次结果；新命令对终态可为 `noop`，不假装 applied。
  - stale process failure：不改变业务状态，diagnostic标 `fence_rejected`；不把瞬态诊断变成第二状态机。
  - operator restart副作用不安全的 Process：拒绝并给 `retryable=false`，不能绕过 safe_replay policy。
- **一句话收口目标**：✅ **所有故障既能被安全看到，也有受控出口；所有 mutation 的实际效果可机器判断。**

#### F9: Compatibility / retirement / physical convergence

- **输入**：dual-write shadow结果、pin/ref/session/job inventory、legacy verdict、retention deadline与 release gates。
- **输出**：v2 writer cutover、old readers关闭、rev1/alias退役、物理 ref/purge完成证明。
- **主要调用者**：migration operator、maintenance role、release owner。
- **核心逻辑**：
  1. 采用 `expand → dual-write/shadow-read → validate → new-admission cutover → legacy drain → contract`；每阶段有独立 feature flag和停止条件。
  2. dual-write只用于 mutable authority/projection；immutable evidence不双写两个不同公式，而是明确写 v1/v2 assertion与cross-link。
  3. new Task只 pin rev2后，rev1仍供 old Execution/retry；zero pin、zero pending outbox、zero restart window、retention到期后才disable/retire。
  4. legacy `s05_binding_digest`、old selected output、old path formula由compat reader隔离；不物理删列直到全仓无 reader/writer扫描和升级回滚窗口结束。
  5. Item cleanup、object deletion job、generation retirement、diagnostic retention全部收敛到 terminal proof；open intent有 age metric/alert/operator view。
  6. rollback 在 cutover前可关新 admission；cutover后禁止旧 writer复活，只能停 admission并前滚修复。
- **边界情况**：
  - invalid legacy evidence：不阻止读取其历史 status，但阻止把它当 verified proof参与新 publication/retry。
  - migration中途崩溃：每步 idempotent，schema version与backfill cursor durable。
  - physical purge失败：业务 tombstone保持，cleanup job可重试；不撤销已成立的 logical delete。
- **一句话收口目标**：✅ **兼容不是永久双轨：有进入、验证、排空和删除条件，且任何阶段都不改写历史事实。**

#### F10: Graph-derived assurance / release

- **输入**：compiled capability/reachability manifest、all debt coverage、old DB fixture、runtime profiles、fault scenarios、test commands。
- **输出**：L1–L4 results、race/crash/upgrade/security evidence、全仓结果、owner gate status、不可变 closure pack。
- **主要调用者**：CI、release owner、第三轮 adversarial review、closure checker。
- **核心逻辑**：
  1. legal/illegal cells由 compiled graph+capability manifest生成，而不是“每 strategy 手写一格”；每条 reachable edge至少有正例，每条禁止边有零副作用负例。
  2. race矩阵覆盖 Task/observation、ItemEpoch、Outcome terminal、upload session、GC/ingest、outbox/requeue、delete/publish；断言业务行数和 owner，而不只看 HTTP。
  3. crash测试至少一层使用真实子进程 kill/restart与持久化 DB/object root；hook只作精确窗口 unit/integration，不替代进程恢复。
  4. upgrade从 pre-fix persisted fixture跑 migration/bootstrap/retry/read；禁止只测空库。
  5. production 10+3 L3/L4必须使用非 stub profile与可核验 supply identity；无法取得外部 gate就明确 blocked。
  6. 全仓 pytest使用 PersistencePort/adapter-aware inspector，移除 sqlite3-on-Turso；修复现有 stale-fence红灯并补第一轮名义修复专项测试。
  7. evidence checker实际执行/核验命令、exit code、commit、artifact digest、timestamp与环境 profile；文件中写 `PASS` 不算证据。
  8. 第三轮 review以 Appendix C/D 分母逐项复验；closure要求 in-scope debt=0、unknown waiver=0、unexecuted evidence=0。
- **边界情况**：
  - 环境没有 live GPU/model：对应 release gate blocked，不以 skip绿替代。
  - flaky timing：用 durable state/fault barrier，不用任意 sleep作为 race 证明。
  - experiment文件存在：checker断言其不进入 closure join。
- **一句话收口目标**：✅ **每个业务边界都有能在修前失败、修后通过并能从冷启动重现的证据。**

### 7.3 非功能性要求与验证策略

- **性能目标**：admission identity/reservation为索引 O(1)；所有列表 cursor分页，public page ≤100、operator page ≤200；background scanner批次可配置且默认≤100；在线 retrieval不全量重算大 generation，只验证 read-snapshot内命中成员与 manifest。
- **可观测性要求**：每个 state-machine transition有 domain event；每个 scanner/supervisor有 success/failure/age/depth signal；所有控制命令有 receipt+audit；不得只有 in-memory `last_error`。
- **稳定性要求**：terminal monotonic、ItemEpoch monotonic、workflow revision immutable、session/ref owner exact、evidence append-only；进程在任一列出的 crash window重启后必须收敛为成功、typed failure或安全待处理，不能隐形卡住。
- **安全 / 权限要求**：public与operator强分面；跨 Team防枚举；nested data递归拒密；无 raw object read；browser non-root/no-sandbox禁用；debug/control全审计；metric label低基数。
- **测试覆盖要求**：L1 unit、L2 UoW/integration、L3 composed-root/real role、L4 retrieval/product、R race、C crash、S security、U upgrade全部有不可替代的最低层；每个 absorbed deferred至少一个专项断言。
- **验证策略**：短套件在每 AP 运行，join后执行 graph-derived closed set、subprocess crash、old DB upgrade、adapter-aware全仓、live profile与第三轮独立审查；具体命令由各 action-plan冻结。

### 7.4 目标数据与 UoW invariant

| 权威对象 | 建议 durable 形状 | 唯一键 / CAS | 允许的终态 | 禁止事项 |
|----------|-------------------|--------------|------------|----------|
| SourceIdentity | 现 `mkb_intake_sources` v2语义或独立 source key row | team+kind+normalized external key | active/retired | 用一次 observation fingerprint 定义 Source |
| Observation | `mkb_intake_observations` + append-only attempts | team+source+observation key；attempt generation CAS | accepted/failed/abandoned | accepted后改 fingerprint；失败后无合法 retry出口 |
| Snapshot | 现表+observation FK/version | one accepted snapshot per observation | immutable | 不同 observation 复用同 UUID |
| Item | 现表，`row_revision`冻结为 ItemEpoch | expected epoch + lifecycle/head predicates | active/deactivated/deleted | blind latest LWW；迟到 publish穿透 lifecycle |
| Workflow revision | registry/revision + checked-in compat manifest | workflow+revision number+canonical digest | active/retired | 同 revision异 digest；无 pin inventory退役 |
| Processing binding | Execution v2 binding family/key/version/digest | seal-once CAS | sealed/legacy_unverifiable | registered operation冒充 clean strategy |
| Selected output | append-only v2 assertion | execution+control+assertion generation | verified/invalid旁路 verdict | manifest digest冒充 fact digest；UPDATE旧证据 |
| Upload session | `mkb_object_upload_sessions` | team+idempotency key；state revision CAS | committed/consumed/cancelled/expired/failed | 仅凭 handle取消；TTL释放reserved Task session |
| Object deletion | `mkb_object_deletion_jobs` | stored object+job generation | destroyed/blocked/failed | tombstoned quarantine无人收尾 |
| Publication manifest | immutable ordered vector identity manifest | item+revision+namespace+index generation | verified/invalid | retrieval仅信mutable row且无read snapshot |
| Outbox delivery | owner kind/uuid/generation + terminal policy | dedupe+delivery generation | done/dead/abandoned | dead后owner继续ready/queued |
| Command receipt | command fingerprint+target generation | team+command kind+fingerprint | applied/replayed/noop/rejected | 重放无法区分；operator command无审计 |

### 7.5 治理 DAG 与派生 action-plan

```text
AP-NHCF0  debt truth / decisions / pre-fix fixtures
    │
    ▼
AP-NHCF1  canonical identity + migration scaffolding
    ├──────────────┬────────────────┬────────────────┐
    ▼              ▼                ▼                ▼
AP-NHCF2       AP-NHCF3         AP-NHCF4         AP-NHCF5
intake /       workflow /       object /         capability /
ItemEpoch      replay/outcome   evidence/purge   roles/readiness
    └──────────────┴────────────────┴────────────────┘
                           │
                           ▼
                     AP-NHCF6
             discovery / read / control / obs
                           │
                           ▼
                     AP-NHCF7
          compat drain / legacy retirement / convergence
                           │
               owner live/S16 gate ───────┐
                           │              │
                           └──────┬───────┘
                                  ▼
                            AP-NHCF8
           graph-derived assurance / full regression / closure
```

并行纪律：`NHCF2..NHCF5` 可在 NHCF1 的 contract/migration interfaces 冻结后并行，但不得各自修改相邻簇 schema；跨簇变更必须回到 NHCF1 interface revision。`NHCF6` 必须等四支 authority 稳定后再冻结 wire，避免 API 再次投影错误状态。`NHCF7` 只能删除已由 NHCF6 读面与 inventory证明零使用的旧形状。`NHCF8` 不第一次发现功能缺口；出现新 blocker必须回 owner AP修复并重跑 join。

### 7.6 Action-plan 工作簇与 exit gate

| AP | 业务簇 / 主要范围 | blocked-by | 必须产出的 exit gate |
|----|-------------------|------------|------------------------|
| `AP-NHCF0` | debt truth、CF决策、root-cause/coverage、pre-fix DB/rev1 fixture、测试分母 | none | 50有效债务+第一轮deferred 100%归属；`CF-D*`无影响执行路径的OPEN；当前红灯/静态反例已冻结 |
| `AP-NHCF1` | observation/session/receipt/evidence verification/capability manifest schema、version规则、migration scaffold | NHCF0 | migration 025+空库/旧库均可跑；旧事实不伪造；dual-read shadow接口冻结 |
| `AP-NHCF2` | Source/Observation/Snapshot/ItemEpoch、admission/lifecycle/rebuild/scatter | NHCF1 | 四通道 identity+7 intent/state+races全绿；非法格零Task；terminal lifecycle无迟到穿透 |
| `AP-NHCF3` | workflow rev2、processing binding、reachability、Outcome/worker/retry/outbox owner | NHCF1 | persisted rev1升级不503；terminal outcome零推进；HTTP/API full retry零外部调用；dead owner终结 |
| `AP-NHCF4` | CAS-first stage/evidence、publication manifest、upload session/journal、GC/cleanup/purge/security | NHCF1 | session隔离、pre-catalog/GC crash、append-only SQL attacks、delete physical convergence、retrieval verification全绿 |
| `AP-NHCF5` | ProcessCapabilityManifest、10+3 adapters、role profile、readiness/no-sandbox/supervisor/pool | NHCF1 | role-specific正负readiness；stub不可prod；actual args security；真实profile达到ready-for-owner-gate |
| `AP-NHCF6` | strict catalog/Task/Item/Namespace/Process/Fact APIs、receipt/control、signals/errors | NHCF2–5 | OpenAPI无业务空schema；frontend/operator无需SQL完成发现/诊断/重试/停止/修复；每个signal有emitter/test |
| `AP-NHCF7` | dual-write验证、new writer切换、rev1/alias/enum retirement、cleanup/purge drain | NHCF6 | mismatch=0、new writer唯一、old pin/ref/open cleanup inventory满足门限；rollback/forward-only演练通过 |
| `AP-NHCF8` | graph-derived L1–L4/R/C/S/U、adapter-aware全仓、live/S16 gate、第三轮review、closure | NHCF7 + owner gates | in-scope debt=0；全仓绿；真实或明确blocked的owner gate；evidence命令已执行；第三轮无未解释blocker |

### 7.7 AP 执行纪律

1. 每个 AP 必须同时覆盖 contract/schema/service/runtime/API-or-operator-view/observability/test/migration-doc 中适用的层，禁止以“核心代码已改，读面以后补”收口。
2. 每个 finding 的 closure 证据至少包含：修前反例、修后 assertion、目标 commit、运行环境/profile、UTC、受影响的 Truth/decision；只有字段存在或测试文件存在不算完成。
3. migration 和 public contract 变更必须独立 review；security boundary、operator control、physical deletion必须有第二 reviewer/owner sign-off。
4. AP 可以 `blocked-by-owner`，但不能 `closed`；外部模型/S16/真实部署是唯一预期 owner blocker，其余 true-deferred 已被本设计吸收。
5. 不允许修改历史 review 来减少分母；只在本设计 coverage manifest和新 closure append disposition。

---

## 8. 可借鉴的代码位置清单

### 8.1 正向 precedent

| 文件:行 | 内容 | 借鉴点 | 备注 |
|---------|------|--------|------|
| `src/services/workflow_registry.py:152` | immutable workflow revision register | 同 revision异 digest fail-loud、old pin坐标 | builtin version纪律需补齐 |
| `src/runtime/binding/actual_s05.py:55` | sealed-once actual CAS | history+route+binding聚合、rowcount fence | v2扩展 ProcessingBinding/formula version |
| `src/runtime/intake/representation_history.py:60` | fact/history同UoW append | fact-first、ordered path | 补全所有 evidence immutable law |
| `src/services/intake_lifecycle/lifecycle_publish.py:28` | publication proof+pointer+Item CAS | 单 owner UoW、expected revision | caller必须实际传 expected epoch |
| `src/runtime/workflow/runtime_outcome.py:287` | lease recovery | safe replay与fencing generation分账 | 加role signals和真实process-kill证据 |
| `src/services/object_gc.py:218` | quarantine→recheck→proof+tombstone | reference-first删除与双检查 | 加durable deletion job和post-tombstone收尾 |
| `src/services/observability.py:246` | tenant-scoped bounded reads | cursor/filter digest、operator boundary | 扩Process/Fact/Diagnostic/control但不开放SQL |
| `src/runtime/metrics.py:46` | closed low-cardinality catalog | 固定labels与allowlist | 目录必须绑定emitter/alert/runbook |

### 8.2 当前需要避开的反例

| 文件:行 | 问题 / precedent | 我们借鉴或避开的原因 |
|---------|------------------|----------------------|
| `src/runtime/intake/acceptance_snapshot.py:139` | 相同source/external key复用Snapshot不比fingerprint | 证明Source与Observation必须分账 |
| `src/runtime/intake/acceptance_snapshot.py:191` | latest revision blind UPDATE | 证明所有Item mutation都要ItemEpoch CAS |
| `src/runtime/task/task_create.py:452` | registered API observation预查独立UoW | reservation必须与Task INSERT同UoW |
| `src/runtime/intake/acquisition_ingest.py:423` | scatter先冻结随机identity再在callback采用旧identity | 先确定reservation identity，envelope只带稳定UUID |
| `src/runtime/task/task_commands.py:293` | full retry复制actual但不复制typed context/仍重跑acquire | retry必须从frozen observation resume |
| `src/runtime/workflow/runtime_outcome.py:38` | terminal Execution未进入Outcome admission | Outcome先检查owner终态/current process |
| `src/runtime/workflow/runtime_materialize.py:65` | reacquire以整图guard存在性执法 | compiler/runtime必须按current hop reachability |
| `src/runtime/workflow/runtime_materialize.py:884` | fact digest使用output manifest digest | 所有formula集中一个versioned实现 |
| `src/workflows/kind_family.py:239` | 改图仍revision 1 | 任何canonical变化升revision |
| `src/services/object_upload.py:55` | final promote早于Team/catalog | durable promotion journal消除invisible CAS |
| `src/services/object_upload_ttl.py:62` | cancel释放最新pending | session token拥有精确取消权 |
| `src/services/object_gc.py:169` | quarantine reconcile跳过tombstoned | durable deletion job收尾两类状态 |
| `src/runtime/intake/core.py:398` | early stage envelope复制完整state | CAS-first refs替代正文/secret复制 |
| `src/runtime/task/task_views.py:61` | Task view缺actual/phase/item | strict read model从authority投影 |
| `src/runtime/task/task_projections.py:111` | single item无child被判active | single/scatter outcome明确分支 |
| `src/runtime/workflow/runtime_outbox.py:411` | 8次后dead但owner无terminal policy | outbox必须携带owner和dead disposition |
| `src/runtime/workflow_supervisor.py:47` | 异常只留内存 | role readiness+diagnostic+metric+alert |
| `src/runtime/health.py:16` | required set不含concurrent_writes | 配置要求必须进入role overall |
| `api/public/routes.py:228` | Task endpoints无strict response_model | OpenAPI不能用additionalProperties替代契约 |
| `tests/domain/test_nh9_evidence_pack_checker.py:22` | 检查文件/字符串而不执行命令 | evidence checker必须验证真实execution result |

---

## 9. QNA / 决策登记与设计收口

### 9.1 需要冻结的 owner / architect 决策

| 决策 ID | 问题 | 影响范围 | 当前建议 | 状态 | 答复来源 |
|---------|------|----------|----------|------|----------|
| `CF-D01` | 本轮是否按长期治理 campaign，而非 critical hotfix？ | 全DAG | 采用本文9 AP；所有有效debt必须归属 | `frozen` | 本轮owner请求 |
| `CF-D02` | v2如何区分Source与Observation？ | API/S04/migration | 显式 observation key+reservation；v1按kind兼容派生 | `answered` | 本设计 §7 F2 |
| `CF-D03` | 是否新增多个Item counter？ | lifecycle/publication | 逻辑复用单一row_revision为ItemEpoch，所有canonical mutation递增 | `answered` | 本设计 §6/§7 F2 |
| `CF-D04` | full retry能否重新访问HTTP/API？ | retry/S05 | 禁止；只从frozen observation/artifact resume，无物料则新observation | `answered` | `T-O-401` + 本设计 F3 |
| `CF-D05` | 当前kind family如何升级？ | workflow/compat | checked-in rev1 exact + 新rev2；canonical/formula/capability变化必升版 | `answered` | 本设计 F3/F9 |
| `CF-D06` | registered API map如何进入actual binding？ | strategy/operation/catalog | typed ProcessingBinding union，保持10 strategy与3 operation分账 | `answered` | 本设计 F3 |
| `CF-D07` | upload handle是否继续承担会话所有权？ | object/API/TTL | 否；新增session token/idempotency owner，handle只代表字节 | `answered` | 本设计 F5 |
| `CF-D08` | 已失实legacy evidence如何修？ | evidence/migration | 旁路verification verdict+新correction assertion，禁原地UPDATE | `answered` | 本设计 F4/F9 |
| `CF-D09` | workflow/read/debug/control面如何分权？ | leaf/API/S15 | catalog/Task/Item/Namespace安全读；Process/Fact/payload/control为operator面 | `answered` | 本设计 F7/F8 |
| `CF-D10` | leaf-worker是否成为真实deployment role？ | composition/readiness | `api/workflow_worker/maintenance/all`显式role与各自required set | `answered` | 本设计 F6 |
| `CF-D11` | logical delete后是否本campaign完成物理收敛？ | object/retention | 是；durable cleanup job+retention+ref release+purge proof | `answered` | 本设计 F5/F9 |
| `CF-D12` | 错误码如何结束双轨？ | public/operator/SDK | v2 canonical UPPER_SNAKE registry；v1 legacy alias只兼容、不新增 | `answered` | 本设计 F8 |
| `CF-D13` | 真模型/S16未签时能否close？ | runtime/release | 工程可到ready-for-owner-gate，campaign不得final close | `answered` | `T-O-376/378/399/406` |
| `CF-D14` | 是否顺带支持existing-object新cleaner upgrade？ | product/S05/DAG | 不支持；继续服从T-O-401，必须独立owner-gate | `answered` | `T-O-401` |
| `CF-D15` | deleted Item的external key能否被新ingest隐式复用？ | Source/Item lifecycle | 不能；tombstone永久保留identity，新命令409，未来restore/recreate须显式产品命令 | `answered` | 本设计 F2/A.2 |
| `CF-D16` | outbox永久dead是否可以只记告警、不处理owner？ | workflow/ops | business-critical delivery必须同UoW终结owner；advisory必须在manifest中显式分类 | `answered` | 本设计 F3/F8/A.5 |

> `answered` 表示本文已经给出 architect 推荐，不表示 owner 已 append 冻结。派生 action-plan 前，必须把 `CF-D02..D16` 在本文或独立 `coherent-fixes-qna.md` 标为 `frozen`；若 owner 改选，先修订设计和 coverage，再开始 NHCF1。

### 9.2 设计完成标准

设计进入 `frozen` 前必须满足：

1. `CF-D02..CF-D16` 全部 frozen，且与 `T-O-376..407` 无冲突；冲突只能通过正式 Truth append解决。
2. Appendix B 的 `VF1..VF52` 与 Appendix C 的历史 deferred 每项恰好一个 disposition/owner AP，无“misc/后续再看”。
3. `AP-NHCF0..8` 的 contract、blocked-by、exit gate、最低测试层与 owner gate均被接受。
4. migration expand/cutover/contract、old rev1 fixture、legacy evidence法与rollback posture已由 persistence/architecture owner review。
5. public/operator权限边界、physical purge、真实 runtime supply/S16 gate已由 security/owner review。
6. 所有影响 action-plan执行路径的问题都已在本设计或关联QNA register中回答。

### 9.3 下一步行动

- **可解锁的 action-plan**（设计冻结后创建，不在本文直接执行）：
  - `docs/plan/new-harvest-coherent-fixes/AP-NHCF0-debt-truth-and-fixtures.md`
  - `AP-NHCF1-canonical-identity-and-migration-foundation.md`
  - `AP-NHCF2-observation-item-epoch-and-lifecycle.md`
  - `AP-NHCF3-workflow-version-replay-and-outcome.md`
  - `AP-NHCF4-object-evidence-and-physical-convergence.md`
  - `AP-NHCF5-capability-role-readiness-and-security.md`
  - `AP-NHCF6-discovery-control-and-observability.md`
  - `AP-NHCF7-compat-drain-and-retirement.md`
  - `AP-NHCF8-graph-derived-assurance-and-closure.md`
- **需要同步更新的设计文档**：冻结后 append `docs/closure/new-start/deferred-items-ledger.md` 的承接指针；不重写 NH1–NH9 旧 closure/review。
- **需要进入 QNA register 的问题**：`CF-D02..D16`；其中 production credential/S16签收只登记外部 gate，不在QNA中伪造答案。

---

## 10. 综述总结与 Value Verdict

### 10.1 功能簇画像

本设计把 new-harvest 的二轮欠账归因为五个边界错误：身份混用、版本纪律破裂、对象/证据所有权不完整、部署能力与图声明混同、库内状态没有形成可操作 wire。目标实现由四个 durable token和十个功能面组成，既保留现有 kind-only/selected-output/fact-first/sealed-actual/reference-first 的正确内核，又用 v2 identity、forward migration和 role/control plane补齐长期演进。复杂度主要来自 legacy persisted data、cross-filesystem/DB crash recovery和真实 runtime owner gate，因此通过九 AP DAG隔离，而不是靠一个大提交处理。最终 closure 的定义不是“测试文件存在”，而是所有 valid debt已归零、旧 pin可验证、真实角色可ready、operator不查SQL即可恢复。

### 10.2 Value Verdict

| 评估维度 | 评级 (1-5) | 一句话说明 |
|----------|------------|------------|
| 对 MKB 核心定位的贴合度 | `5` | 直接服务四通道→dynamic workflow→retrieval的主链，不扩第五kind或通用引擎 |
| 第一版实现的性价比 | `3` | migration/API/ops投入较大，但比第三轮继续返工局部fix更低总成本 |
| 对未来 intake/workflow/稳定性演进的杠杆 | `5` | observation/epoch/revision/session四类token可复用到所有后续kind与worker |
| 对开发者/前端/operator日用友好度 | `5` | discovery、actual、retryability、receipt、debug/control消除临时SQL |
| 风险可控程度 | `4` | forward-only、old fixture、分支DAG和role gate可控；真实supply仍有外部依赖 |
| **综合价值** | `5` | 能把deferred“库存”转成可执行、可退役、可证明的长期治理闭环 |

---

## 附录

### A. 关键状态机与产品法

#### A.1 ObservationReservation

| 当前状态 | 命令/事件 | 下一状态 | 结果法 |
|----------|-----------|----------|--------|
| absent | Task admission + unique observation key | reserved | 同UoW建Task/Execution；并发至多一个winner |
| reserved | acquire fact/artifact commit | acquired | fingerprint与artifact sealed；first durable observation wins |
| reserved/acquired | typed stage failure | failed | 记录attempt/error/retryability，不删reservation |
| failed | `retry_failed_observation` + expected attempt | reserved(new attempt) | 新attempt append；相同命令replayed |
| acquired | acceptance + ItemEpoch CAS | accepted | 绑定immutable Snapshot/ChangeSet/coordinates |
| reserved/acquired | cancel/retention reconciliation | abandoned | 无Snapshot；允许显式reclaim或新key |
| accepted | exact replay | accepted | 返回原coordinates/receipt=replayed |
| accepted | 不同fingerprint | accepted | 409 conflict；新观察必须新key |

#### A.2 七 intent × Item lifecycle admission

| Intent | active | deactivated | deleted |
|--------|--------|-------------|---------|
| `intake.ingest` | allow（new observation） | 409，先reactivate | 409，禁止隐式复活/重占key |
| `intake.rebuild` | allow + expected epoch | 409 | 409 |
| `intake.update_metadata` | allow + expected epoch | 409 | 409 |
| `intake.deactivate` | allow | 409（新命令no-op非法；exact command replay例外） | 409 |
| `intake.reactivate` | 409 | allow | 409 |
| `intake.delete` | allow | allow | 409（exact command replay例外） |
| `index.rebuild` | allow | 409 | 409 |

所有 `409` 在 admission 前发生并保持零新 Task/Process。exact command replay通过 CommandReceipt返回第一次结果，不重新执行 applicability。

#### A.3 Retry / refresh / upgrade 分账

| 动作 | 外部 acquire | Workflow/actual | Observation | 使用场景 |
|------|--------------|-----------------|-------------|----------|
| Process retry（acquire尚未commit） | 可在同attempt重试；first durable result wins | 同revision，尚未seal | 同reservation/attempt | transient transport failure |
| Process retry（acquire已commit） | 禁止；读frozen artifact | exact | 同reservation/attempt | downstream retry/recovery |
| full Task retry | 禁止 | exact workflow/policy/actual/formula | 同accepted/frozen observation | Task failed后的causal replay |
| new observation | 允许 | 当前active revision，未来新actual | 新observation key | refresh/re-ingest外部变化 |
| existing-object cleaner upgrade | 本设计不提供 | 新owner-gate决定 | 显式operator scope | `T-O-401`未来能力 |

#### A.4 ObjectUploadSession

| 状态 | durable事实 | 合法动作 |
|------|-------------|----------|
| receiving | session/idempotency/Team | stream/abort |
| prepared | staging id + digest + size | promote/reconcile/expire |
| promoted | final CAS可验证、catalog未必存在 | commit catalog+pending或reconcile删除 |
| committed | catalog + exact pending ref | stat/reserve/cancel/expire |
| reserved_by_task | owner Task/generation | acceptance consume或Task terminal release；TTL禁止释放 |
| consumed | business refs已转移 | stat/retention；session不再cancel业务ref |
| cancelled/expired/failed | pending ref已释放、typed proof/error | GC after grace；exact replay返回terminal receipt |

#### A.5 Outbox dead 与 operator restart

- outbox row必须有 `owner_kind/owner_uuid/owner_generation/terminal_policy`。
- delivery到达dead阈值时，若为business-critical，dead row、owner failed projection和event在同UoW；若为advisory，写明确 `advisory_dead`，不得默认为无影响。
- requeue创建新delivery generation并引用dead predecessor；原row保持dead evidence。
- Process restart创建新attempt/Process，复用exact immutable input和policy；不把terminal row改回ready。
- stop/cancel first-wins；迟到 Outcome只得到replayed/fenced receipt。

---

### B. VF1–VF52 全量处置映射

> 本表是设计覆盖分母，不改变 VF ledger 原判。`absorbed` 表示原 true-deferred 在本长期 campaign 中转为实际交付，不得再次 deferred。最终 action-plan 可细化测试 ID，但不能改变 owner AP 而不修订本文。

| VF | Ledger归属 | 根因簇 | 本设计处置 | Owner AP / 关键证明 |
|----|------------|--------|------------|----------------------|
| VF1 | true-bug | F2 Observation | 不同observation必建新Snapshot；exact replay回原坐标；ChangeSet不悬挂 | NHCF2：同source不同正文=2 Snapshot或明确冲突，无假UUID |
| VF2 | true-bug | F2 ItemEpoch | latest Revision更新带expected ItemEpoch，败者409 | NHCF2：并发双内容只有一个head winner |
| VF3 | partial | F2 Admission | ObservationReservation与Task/root同UoW，unique映射稳定409 | NHCF2：并发至多一个201且零500 |
| VF4 | partial | F2 Observation retry | failed observation有typed retry/reclaim attempt；accepted保持terminal | NHCF2：失败同key可合法恢复且不删历史Snapshot |
| VF5 | true-bug | F2 Scatter identity | 先采用Source/Observation identity，再冻结envelope/manifest | NHCF2：scatter失败后retry无`INTAKE_SOURCE_MISSING` |
| VF6 | partial | F3 Exact replay | full retry从frozen observation/artifact resume，禁止HTTP refetch | NHCF3：HTTP内容改变后retry外部调用数=0 |
| VF7 | true-bug | F3 Typed context | metadata disposition进入typed Execution context并exact复制 | NHCF3：no_change retry仍走no_change route |
| VF8 | true-bug | F2 Tombstone identity | deleted same key在admission 409零Task；不隐式复活 | NHCF2：delete后再ingest零新Task/Source冲突异常 |
| VF9 | partial | F2 Lifecycle admission | deactivated ingest拒绝；transition ledger使用真实before/after | NHCF2：无active→active假账、无白跑管线 |
| VF10 | true-bug | F2 ItemEpoch | 所有accept/publish/rebuild callback携带expected epoch | NHCF2：delete/reactivate与迟到callback race矩阵 |
| VF11 | partial | F2 Applicability | 冻结7 intent×3 state矩阵；同态新命令非法、exact replay例外 | NHCF2：非法格零Task/Process |
| VF12 | partial | F2 Rebuild cardinality | frozen target任一stale使整Task fail；初始空才noop | NHCF2：team target count与processed count一致 |
| VF13 | true-bug | F3 Outcome state | Outcome先检查active Execution/current Process；terminal返回fenced/replay | NHCF3：failed Execution迟到success无Process/状态变化 |
| VF14 | true-deferred→absorbed | F2/F3 Task projection | cancel first-wins；queued/cancelling不得被worker投影failed | NHCF2/3：Task状态合法边race |
| VF15 | true-bug | F3 Error taxonomy | reachability预检；DomainConflict落typed failed，只有FenceConflict吞掉 | NHCF3：非法媒体/策略不留running |
| VF16 | true-bug | F3 Route reachability | 按current hop compiled candidates执法，删除整图guard特判 | NHCF3：browser/reacquire各hop正负矩阵 |
| VF17 | true-bug | F3/F9 Version | checked-in rev1 exact、新rev2、pin inventory与retirement | NHCF3/7：pre-fix DB bootstrap/retry不503 |
| VF18 | true-bug | F3/F4 Formula | selection v2读取真实fact digest；公式单实现、带版本 | NHCF3/4：fact/manifest digest不同且各自可重算 |
| VF19 | partial | F4 Evidence | identity/state分表或全列trigger；selection/artifact/vector不可改 | NHCF4：direct SQL update/delete attack全拒绝或只改projection |
| VF20 | partial | F3 Processing taxonomy | `registered_api_operation`与`clean_strategy` typed union | NHCF3：sealed binding全部可在对应registry解析 |
| VF21 | partial | F3/F9 Formula version | path v2升formula version；legacy v1 reader/verification保留 | NHCF3/7：v1/v2 fixture digest均稳定 |
| VF22 | partial | F5 Object session | cancel/TTL/consume按session/ref owner，不按最新/全部 | NHCF4：pending=2，取消A后B仍live |
| VF23 | partial | F5 Promotion journal | Team/session先durable；prepared/promoted可reconcile | NHCF4：promote-catalog crash后无invisible final CAS |
| VF24 | partial | F5 Deletion job | tombstoned+quarantined由job完成destroy | NHCF4：TX2后kill/restart最终quarantine=0 |
| VF25 | true-deferred→absorbed | F5/F9 Physical purge | delete cleanup枚举并释放artifact/source/generation/vector refs | NHCF4/7：cleanup terminal且磁盘/ref单调收敛 |
| VF26 | partial | F5 Session gate | local_object只接受transferable session或明确business ref | NHCF4：其它purpose ref不能冒充public upload |
| VF27 | n/a acknowledged | F5 TTL law | 保留未占用pending会过期；Task reservation后TTL不得释放 | NHCF4：两格测试区分unreserved与reserved |
| VF28 | true-bug | F4 Security | 所有nested extras递归拒密；stage/audit CAS-first/redacted URL | NHCF4：secret/path/signed URL负样本422且DB/CAS零正文 |
| VF29 | true-deferred→absorbed | F6 Readiness | 明确single-writer/concurrent-writer profile；required必入overall | NHCF5：probe=false在required profile时ready=false |
| VF30 | true-deferred→absorbed | F6/F10 Live supply | 实现prod非stub 10+3 profile；外部凭据/S16为final gate | NHCF5/8：真实adapter L3/L4或明确blocked，不得stub PASS |
| VF31 | true-bug | F6 Browser security | 校验实际webdriver/browser args与runtime evidence | NHCF5：实际args含no-sandbox必503 |
| VF32 | true-deferred→absorbed | F6 Capability readiness | role/profile manifest决定admission/claim与目录availability | NHCF5：缺PDF/model在需要它的role/Task前fail closed |
| VF33 | true-deferred→absorbed | F6/F7 Discovery | 编译ProcessCapabilityManifest并提供只读workflow/capability目录 | NHCF5/6：上游可分类/list，Task schema仍禁workflow key |
| VF34 | partial | F7 Task actual | Task strict view投影kind/mode/policy/actual/item/observation/revision | NHCF6：终态GET可回答实际绑定 |
| VF35 | true-deferred→absorbed | F7 Lists | Team-scoped Item/Namespace lists与Task source_kind filter | NHCF6：冷启动只用API获得合法retrieval namespace |
| VF36 | true-bug | F7 Outcome projection | single从root/Task终态投影，scatter从child投影 | NHCF6：single succeeded item不再active |
| VF37 | true-deferred→absorbed | F7 Phase | 保留六态，增加phase/waiting_reason/waiting_ref安全摘要 | NHCF6：fanin/retry/gate能区分而不扩Task enum |
| VF38 | partial | F7/F8 Debug | public redacted error；operator Process/Stage/Fact与registered payload view | NHCF6：无需SQL回答“卡在哪、为何失败” |
| VF39 | true-deferred→absorbed | F8 Diagnostics | supervisor/GC/outbox等接入DiagnosticSink并提供operator read | NHCF6：故障有durable diagnostic且retention有界 |
| VF40 | true-deferred→absorbed | F8 Signals | 每个metric/alert补emitter+runbook+test或删除definition | NHCF6：catalog-emitter双向零孤儿 |
| VF41 | true-deferred→absorbed | F8 Admission/events | 拒绝、TTL、cancel、repair写低敏event/metric；typed context不空置 | NHCF6：关键负路径均有signal且零业务Task |
| VF42 | true-deferred→absorbed | F6/F8 Supervisor | consecutive failure进入role readiness、diagnostic、metric/alert | NHCF5/6：supervisor反复失败worker不再ready |
| VF43 | partial | F3/F8 Dead/control | dead终结owner；typed requeue/repair/restart/stop入口 | NHCF3/6：unknown plan dead后owner terminal且可审计requeue |
| VF44 | true-deferred→absorbed | F8 Receipt | 所有mutation返回applied/replayed/noop/retryable | NHCF6：相同命令重放与新noop机器可区分 |
| VF45 | partial | F3/F8 Disposition | ingestion/lifecycle/rebuild/metadata各有规范result disposition/metric | NHCF3/6：rebuild/metadata不计indexed_success |
| VF46 | true-deferred→absorbed | F7/F8 Projection | Task/result暴露index_rebuild_noop/exhausted_zero等operation mode | NHCF6：前端可区分真实工作与noop/zero |
| VF47 | true-deferred→absorbed | F3/F8 Fence diagnostics | stale fence保持业务回滚，在独立diagnostic记录拒绝 | NHCF3/6：新世代不死且operator看见旧fail被拒 |
| VF48 | true-deferred→absorbed | F6 Roles | 显式api/worker/maintenance/all role与组件owner | NHCF5：各role只启动所属loop，readiness正确 |
| VF49 | true-bug | F10 Assurance | 修红测；graph-derived legal edges与真实process-kill | NHCF0/8：旧红灯先RED后绿，edge/crash分母来自compiler |
| VF50 | partial | F10 Regression | 为第一轮名义fix补专项常驻测试，不借既有happy path | NHCF0/8：每个claimed-fix有falsifiable test ID |
| VF51 | true-deferred→absorbed | F8 Error registry | v2 canonical code+legacy alias映射+retryability | NHCF6：新端点零双轨，SDK可按registry判定 |
| VF52 | stale-rejected | F10 Guard regression | 不改body cap；保留Content-Length+stream cap回归测试 | NHCF8：大records/超限请求仍受1MiB/配置上限保护 |

### C. 历史 deferred 内聚承接

#### C.1 第一轮 NH deferred

| 历史 ID | 原内容 | 本设计最终处置 | Owner AP |
|---------|--------|----------------|----------|
| `NH-VF3.r` | acquire/decode/clean envelope含raw_text | CAS-first stage refs，正文只在有ref的CAS | NHCF4 |
| `NH-VF4.r` | retrieval不重算publication set | publication manifest+read snapshot+auditor | NHCF4/NHCF8 |
| `NH-VF9.r` | 7×state与rebuild stale cardinality | 全矩阵admission+all-or-none frozen scope | NHCF2 |
| `NH-VF10` | retry_wait/full_task replay切片 | ObservationAttempt与frozen full replay分账 | NHCF2/NHCF3 |
| `NH-VF13` | pre-catalog CAS/staging lease/ingest reservation | upload session promotion journal+Task reservation | NHCF4 |
| `NH-VF14.r` | 真模型/S16/PromptRef/OCR | prod capability profile+owner final gate | NHCF5/NHCF8 |
| `NH-VF21` | kind rev1原位演进 | rev1 fixture+rev2+pin retirement | NHCF3/NHCF7 |
| `NH-VF27.r` | process kill+lease recovery | role worker subprocess kill/restart+operator stop/restart | NHCF3/NHCF5/NHCF8 |
| `NH-VF29` | 全仓910/910未进入closure | adapter-aware全仓作为final硬闸；数量以当前collection为准 | NHCF8 |
| `NH-VF36` | pointer四态无writer | 删除/收窄未使用building/retiring，而非造假writer | NHCF1/NHCF7 |
| `NH-VF37` | unique错误文本+single writer | typed conflict mapping+明确persistence profile | NHCF1/NHCF5/NHCF8 |
| `NH-VF38` | inline promote在第二UoW前 | 同promotion journal统一解决 | NHCF4 |
| `NH-VF39` | old graph常驻无retirement | pin inventory、disable/retire条件与compat read | NHCF3/NHCF7 |
| `NH-VF41.r` | helper/sentinel/missing-supply测试治理 | contract helper整理、graph-derived negatives、canonical error | NHCF6/NHCF8 |
| `NH-VF42` | evidence checker不执行命令 | checker执行并校验exit/commit/digest/profile | NHCF8 |
| `S16` | browser egress签收未伪造 | 实现与证据in-scope；具名签名为final owner gate | NHCF5/NHCF8 |
| `experiment` | 发车/评分 | 保持OOS，不是技术债；继续断言不入closure | NHCF8 guard only |

#### C.2 直接阻塞 NH 的跨阶段 carry-over（去重吸收）

| Carry-over 集合 | 与NH的直接关系 | 本设计承接 |
|-----------------|----------------|------------|
| `NS1-V11` / `NS2-O7` / `NS5-VF86` / `NS6-VF86` | sqlite3-on-Turso使全仓与mega证据不可信 | NHCF8统一adapter-aware inspector/harness，四条只算一个根因 |
| `NS5-T60` | generation→vector→retrieval mega被harness挡住 | NHCF8 L4 join |
| `NS5-VF30.r` / `NS5-VF37.r` / `NS5-VF97` / `NS6-VF97` | PDF/production model/browser/OCR/Vision直接决定10+3真接线 | NHCF5 production profile、NHCF8 real L3/L4 |
| `NS5-VF66.r` / `NS6-VF25.r` | object目录/CAS orphan与VF23同根 | NHCF4 promotion journal/inventory reconciliation |
| `NS5-VF36` | raw/clean envelope authority与NH-VF3.r同根 | NHCF4 CAS-first evidence |
| `NS5-VF62` / `NS6-VF62` | worker overlap受heartbeat/fence限制，与leaf role吞吐同边界 | NHCF5在fencing/process-kill通过后启用bounded pool |
| `NS5-VF91.r` | 真机concurrent-write/readiness证据 | NHCF5 persistence profile，NHCF8 adapter test |
| `NS6-VF11.r` | CLI/process group kill是NH-VF27.r真实恢复前提 | NHCF5/NHCF8 subprocess tree termination |
| `NS6-VF20` | retrieval read transaction是publication manifest一致读前提 | NHCF4新增`read_snapshot()`，NHCF8 TOCTOU test |
| `NS6-VF4.r` | 证据/状态表分类不完整 | NHCF1对全schema做四类inventory；只保护承重identity |
| `NS6-VF15.r` | 同指纹replay短路与Observation/Revision adoption相交 | NHCF2/NHCF3统一replay law |
| `NS6-VF36.r` | diagnostic sidecar有界性影响operator debug | NHCF6 role-aware bounded queue/drop signal |
| `NS6-T01-hotfix` | BEGIN cancel harness不能作为长期race证明 | NHCF8用子进程/adapter barrier替代睡眠门 |

以下 new-start 项不因“减少 deferred 数量”被偷渡：billing、cloud inference provider、MiniMax选型、urgent aging、S06全树、外部vector、`/docs`公网姿态等没有直接因果边到 NH1–NH9 目标，继续由各自 charter承担。

### D. 验证矩阵与 release evidence

| 证明簇 | L1 | L2/UoW | L3 composed role | L4 product/retrieval | Race/Crash/Upgrade |
|--------|----|--------|------------------|----------------------|--------------------|
| Observation/ItemEpoch | key/state/matrix | reservation+Task、accept+epoch atomic | 四kind public requests | changed/no-change均可检索且旧serving不泄漏 | 并发双create、delete×accept、failed retry |
| Workflow/replay | compiler/reachability/formula | terminal Outcome、actual/selection same UoW | api+worker role full retry | 10+3 actual route→retrieval | persisted rev1 upgrade、kill、late outcome、dead outbox |
| Evidence/security | digest/validator/trigger | artifact/fact/proof atomic | nested secret/path/signed URL负样本 | publication manifest membership/TOCTOU | direct SQL attack、legacy correction |
| Object/cleanup | session state/ref law | catalog+pending、consume transfer、delete job | public upload/stat/cancel/local ingest | delete后retrieval zero、retention后bytes zero | promote/catalog、TTL/reserve、quarantine/tombstone kill |
| Capability/role | manifest/schema/arg guard | readiness composition | api/worker/maintenance正负启动 | 非stub 10+3 | supervisor loop fail、process-tree kill、CW adapter |
| Read/control/obs | response/error/receipt model | command owner CAS、event/metric emitter | frontend/operator route auth | cold-start namespace→search | stale command、新世代fence、requeue predecessor |
| Migration/retirement | manifest/version rules | migration idempotency | old DB app startup/read/retry | old/new data coexist query | mid-migration kill、rollback posture、zero-pin drain |

#### D.1 Final release 硬闸

1. `ruff`/type/schema checks与所有AP短套件绿。
2. 当前 `test_stale_fencing_fail_does_not_kill_new_generation` 红灯已按新契约修正，且保留“新世代不被旧fail杀死”的原始断言。
3. adapter-aware full pytest 无排除绿；若测试总数变化，evidence记录collection与commit，不复用历史“910/910”字面。
4. graph-derived legal/illegal manifest与实际 compiled/capability digests一致；每个 route/operation有对应证据。
5. subprocess crash suite覆盖 observation、Outcome、promotion、GC、outbox、lease/process group；hook-only结果不能替代。
6. pre-fix persisted DB迁移、bootstrap、old pin read/retry与new Task rev2通过。
7. public OpenAPI业务response零空schema/additionalProperties；operator所有control有auth/audit/CAS负例。
8. metric/emitter/alert/runbook目录双向零孤儿；supervisor/cleanup/dead outbox age可观测。
9. production profile不含stub；真实supply evidence齐。缺凭据/S16签名时状态为blocked，禁止final closure。
10. Appendix B/C中in-scope disposition全部有commit/test/UTC/evidence；第三轮review无未解释critical/high blocker。

### E. 版本历史

| 版本 | 日期 | 修改者 | 主要变更 |
|------|------|--------|----------|
| `v0.1` | `2026-08-31` | `GPT` | 基于二轮VF ledger、冻结QNA、HEAD与deferred总账，提出9-AP内聚还债设计、全量coverage与迁移/验收法 |
