# ES-01 — Service and Task API

> **项目**：`myknowledgebase`（MKB）
>
> **文件 ID**：`ES-01`
>
> **文档性质**：`execution-spec / implementation authority`
>
> **版本 / 日期**：`ES-01-v1.0 / 2026-08-10`
>
> **文档状态**：`ready`
>
> **Truth 输入**：`OT-01-v1.0`、`OT-02-v1.0`、`OT-03-v1.0`、`OT-04-v1.0`
>
> **Baseline 输入**：`S01-v1.5`、`S02-v1.3`、`D01-v1.4`、`D02-v1.0`
>
> **下游 contract 校准**：`ES-06-v1.0`（Task-scoped GenerationArtifact metadata read）、`ES-07-v1.0`（semantic RetrievalSearch/Result）
>
> **上游索引**：`docs/specs/index.md`

本文件是 MKB v1 外部服务边界、Team 接入投影、Task/Audit/Restart 公共契约及 Task aggregate 写入权的唯一 Execution Spec。它完整冻结 API 语义、Task 状态机、接收事务、幂等与并发、逻辑数据库 schema、application ports 和跨模块消息协议。Execution/Process 的内部状态机由 ES-02 持有；Intake、Gate、derived artifact、vector 与 retrieval 的专属 schema 分别由 ES-03、ES-06、ES-07 持有。

---

## 1. Inherited Truth

### 1.1 权威输入与采用方式

| 来源 | 本文件直接继承 | 本文件不得改变 |
|---|---|---|
| `OT-01-v1.0` | standalone leaf-worker、caller-neutral Contract、单应用/单发布、最小 Team 投影、简单 token、polling、内部状态自持 | 不得引入 UI、用户平台、RBAC、callback、legacy compatibility 或 final answer |
| `OT-02-v1.0` | Task/Execution/Process 身份分离、Task:Execution=`1:N`、六 StateFamily、control 向下/proof 向上 | 不得公开 Execution/Process mutation，不得增加 Attempt 或第七 StateFamily |
| `OT-03-v1.0` | 六种异步 intent、同步 retrieval、Task/Audit、五轴查询、cancel/retry/rebuild、bounded polling | 不得增加 intent、异步 retrieval、raw vector 或 final-answer surface |
| `OT-04-v1.0` | strict ingress、proof-backed success、结构化错误、single/scatter验收与固定容量 | 不得以 API 成功、queue ACK 或日志替代业务成功 proof |
| `S01-v1.5` | exact Team/Task/Audit identity、UUID法则、create envelope、patch权限、fingerprint、token | legacy/upstream 私有 DTO 不能进入 core contract |
| `S02-v1.3` | Task 六态、HTTP语义、五轴查询、scatter collect-all、restart/lineage、gate projection | Task status 不承载 phase、waiting、readiness、visibility 或 mixed outcome |
| `D01-v1.4` | current root、generation、root/child execution tree、Task aggregation boundary | Task 不保存 singular current Process；Process/Execution状态不由本文件伪造 |
| `D02-v1.0` | 六StateFamily、唯一owner、typed fact分账、owner-port mutation | API/controller/repository/outbox均无跨owner状态写入权 |

### 1.2 适用 Truth 映射

| Truth cluster | ES-01 交付落点 |
|---|---|
| `OT01-T001..T009/T011..T015`、`OT01-C001..C006/C009/C010` | §2边界、§4服务/API、§5内部port、§7 legacy裁决 |
| `OT02-T001..T007/T019..T023`、`OT02-C001..C006/C008/C010` | §4.6 Task状态机、§5.7跨域协议、§6一致性 |
| `OT03-T001..T010/T019..T025`、`OT03-C001..C006/C015` | §4公共Contract、§5 schema、§6错误/幂等 |
| `OT04-T002/T003/T010..T020/T024/T028..T034`、`OT04-C001/C002/C010..C014` | §4执行链、§6 failure、§8验收 |
| `S01-T001..T061`、`S02-T001..T042` | exact wire、状态边、Task/Audit/Restart数据与查询语义 |

### 1.3 跨 ES ownership

| Concern | 唯一owner | ES-01的权限 |
|---|---|---|
| Team接入投影 | ES-01 | 完整读写与CAS；不拥有上游Team本体 |
| Task aggregate | ES-01 | 唯一transition owner；接收ES-02 typed aggregate proposal后校验并推进 |
| Workflow/Execution/Process | ES-02 | 只发送Task command、读取Workflow只读投影与durable summary；不能注册/激活Workflow或直写runtime状态 |
| Intake/Revision/Membership | ES-03 | 只保存typed refs并投影TaskItem；不创建或修改canonical Intake truth |
| ExecutionGate | ES-03 | 提供Task-scoped安全facade；Gate transition仍走ES-03 owner port |
| Registry/binding | ES-05 | capabilities read model只读取已发布registry；不允许caller CUD |
| Generation/derived asset | ES-06 | Task-scoped只读投影；不允许普通Create/Update/Delete |
| Vector/retrieval | ES-07 | 承载exact同步retrieval facade；ES-01不解释ranking或定义raw vector surface |
| Transaction/outbox/driver | ES-04 | 本文件冻结原子语义和逻辑schema，ES-04冻结physical DDL/migration/driver |
| Token/network/limits | ES-08 | 本文件冻结valid/invalid授权口径；ES-08冻结载体、rotation和网络围栏 |

---

## 2. Scope / Non-scope

### 2.1 Scope

ES-01只负责：

1. 一个版本化、caller-neutral 的 HTTP/JSON 内部 Contract，含capability与Workflow只读发现面；
2. Team 注册、读取、修改、activate/deactivate、soft-delete/restore；
3. 六种异步 request intent 的 Task Create、Get/List、有限 Patch、cancel/full-retry、soft-delete；
4. Task result、items、generations、Audit、restart、lineage 与 action-required 的bounded polling；
5. Task + immutable Audit + durable scheduling intent 的原子接收；
6. Task aggregate 六态的唯一 transition service；
7. create/command replay、revision CAS、稳定错误和安全响应；
8. 对 ES-02/03/04 的typed application port和durable message contract。
9. ES-07唯一同步semantic retrieval request/result的认证、HTTP与safe problem facade。

### 2.2 Non-scope

- 不提供 Execution/Process/Workflow CRUD、phase、claim、lease、fence 或 stage restart API；
- 不提供 webhook/callback、skill-worker registration/heartbeat、UI、session、membership、RBAC、billing；
- 不定义 acquisition/clean、Gate、LS-RAG、embedding/index 的内部算法；
- 不提供 raw vector API、异步 retrieval 或 final answer；
- 不迁移或兼容 legacy route、job/file/status/UUID；
- 不新增 `task_attempts`、child Task、generic Job 或 singular `current_process_uuid`；
- 不把 `payload_extra`、日志、HTTP状态或outbox delivery当作业务Truth。

### 2.3 完成定义

ES-01的`ready`是规范状态：以下义务已被完整定义并通过cross-spec audit，不表示它们已在尚未构建的实现上运行。任何实现要声明符合ES-01-v1.0并进入release，必须同时满足：

1. §4全部public route和envelope形成OpenAPI snapshot；
2. §4.6 Task六态边由一个transition owner以CAS实施；
3. §5四张业务表及ES-04 outbox提交边界可在真实Turso-compatible驱动上运行；
4. §5.7消息可被重复投递且仍只形成一次业务效果；
5. public读取不泄漏Execution/Process/secret/path/driver；
6. §8所有HARD acceptance有自动化证据；
7. 全系统audit确认与ES-02..08无schema、owner或协议冲突。

### 2.4 术语

| 术语 | ES-01 exact含义 |
|---|---|
| `MKB Contract` | `/v1` caller-neutral HTTP/JSON contract；不等于任一上游私有DTO |
| `Task generation` | 同一Task在full retry后产生的单调整数运行代次；首代为`1`，不是领域身份 |
| `Task aggregate proposal` | ES-02提交给Task owner的typed状态/summary/proof候选；不是直接UPDATE |
| `Result readiness` | `not_ready/ready/terminal_failed/terminal_cancelled` typed fact，不是Task状态 |
| `TaskItem outcome` | `active/succeeded/failed/cancelled/skipped`投影，不是StateFamily |
| `Visibility` | `visible/deleted`读取事实，由`deleted_at`推导，不是Task状态 |
| `action_required` | open Gate的安全bounded投影；Task仍为`running` |
| `creation fingerprint` | 通过strict model后的immutable create envelope确定性digest |

---

## 3. Scope Impact Audit

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

执行裁决只把已冻结的 Team/Task/Audit/polling 语义落到exact wire、schema和port。新增的表列、HTTP路径、cursor、fingerprint算法与消息版本都是既有能力的有限实现，不创建产品能力或第七StateFamily。

---

## 4. Architecture Decisions

### 4.1 单体内部边界

```text
HTTP adapter
  → strict contract models
  → application service
  → domain owner service
  → repository / unit-of-work ports
  → Turso-compatible relational adapter

committed outbox
  → in-process scheduler lane
  → ES-02 workflow ingress

ES-02 aggregate proposal
  → ES-01 TaskTransitionService
  → Task CAS + domain event/outbox
```

依赖方向固定为`adapter → application → domain ← ports`。Domain/application禁止导入03-nano DTO、legacy schemas、Turso driver、FastAPI request object或queue implementation。HTTP server、scheduler loop与recovery loop均在同一个Python应用、同一个发布单元内。

### 4.2 公共协议约定

| 项 | 冻结值 |
|---|---|
| Transport | internal HTTPS + JSON；application tests可用ASGI in-process transport |
| Auth | `Authorization: Bearer <internal-token>`；业务route全部必需 |
| Content type | `application/json`；未知/缺失为`415 unsupported-media-type` |
| Contract validation | Pydantic v2 strict models、`extra='forbid'`、无隐式类型coercion |
| UUID | boundary只接受v4/v7；MKB内生领域ID使用v7 |
| Time | RFC3339带时区；持久化/输出UTC `Z`，至少毫秒精度 |
| JSON extension | `payload_extra`必须是object；核心代码不得从中读取状态、路由、权限或proof |
| Request correlation | `X-Request-Id`可传UUIDv4/v7；缺失时MKB生成UUIDv7；不等于Task/Trace |
| Conditional mutation | JSON body中的`expected_revision`；成功响应同时返回`ETag: "r{revision}"` |
| Pagination | opaque keyset cursor；默认`50`、最大`200`；禁止offset |
| Response | `mkb.response.v1` success envelope或`mkb.error.v1` error envelope |

### 4.3 路由清单

#### 4.3.1 Capability、Workflow与Team

| Method / route | 语义 | 成功 |
|---|---|---|
| `GET /v1/capabilities` | 读取Contract版本、六intent、同步retrieval、只读Workflow registry与已发布能力摘要 | `200` |
| `GET /v1/workflows` | 读取ES-02公开为`readable`的有限Workflow registry，按purpose/role分页过滤 | `200` |
| `GET /v1/workflows/{workflow_key}` | registry summary与当前active compiled detail | `200` |
| `GET /v1/workflows/{workflow_key}/revisions/{revision_number}` | immutable historical compiled detail | `200` |
| `POST /v1/teams` | 注册Team投影；同fingerprint replay幂等 | `201` / replay `200` |
| `GET /v1/teams` | status/keyset分页 | `200` |
| `GET /v1/teams/{team_uuid}` | 精确读取；deleted返回tombstone | `200` / `410` |
| `PATCH /v1/teams/{team_uuid}` | name/description/payload_extra + CAS | `200` |
| `POST /v1/teams/{team_uuid}:deactivate` | active→inactive | `200` |
| `POST /v1/teams/{team_uuid}:activate` | inactive→active | `200` |
| `DELETE /v1/teams/{team_uuid}` | active/inactive→deleted | `200` |
| `POST /v1/teams/{team_uuid}:restore` | deleted→inactive | `200` |

`Team.status=active|inactive|deleted`是上游Team接入投影的admission fact，不是D02生产流转StateFamily；它不得参与Workflow route、Task结果或资产lifecycle推导。

Workflow definition、revision、compiler与read projection均由ES-02唯一拥有；ES-01只承载caller-neutral HTTP adapter。任意`POST/PUT/PATCH/DELETE /v1/workflows...`均返回`405 workflow-read-only`，不得形成Task、Audit、Workflow或outbox写入。

#### 4.3.2 Task与控制

| Method / route | 语义 | 成功 |
|---|---|---|
| `POST /v1/teams/{team_uuid}/tasks` | Task+Audit+scheduling intent原子创建 | `201` / replay `200` |
| `GET /v1/teams/{team_uuid}/tasks` | bounded keyset list | `200` |
| `GET /v1/teams/{team_uuid}/tasks/{task_uuid}` | current aggregate；deleted为tombstone | `200` / `410` |
| `GET /v1/teams/{team_uuid}/tasks/{task_uuid}/audit` | immutable Audit snapshot | `200` |
| `PATCH /v1/teams/{team_uuid}/tasks/{task_uuid}` | 描述字段；priority仅queued | `200` |
| `DELETE /v1/teams/{team_uuid}/tasks/{task_uuid}` | terminal Task soft-delete | `200` |
| `POST /v1/teams/{team_uuid}/tasks/{task_uuid}:cancel` | forward-stop cancel intent | `202` / terminal no-op `200` |
| `POST /v1/teams/{team_uuid}/tasks/{task_uuid}:retry` | failed/cancelled→新generation queued | `202` |
| `GET /v1/teams/{team_uuid}/tasks/{task_uuid}/result` | readiness polling | `202` not-ready / terminal `200` |
| `GET /v1/teams/{team_uuid}/tasks/{task_uuid}/items` | generation-scoped TaskItem projection | `200` |
| `GET /v1/teams/{team_uuid}/tasks/{task_uuid}/generations` | immutable generation summaries | `200` |
| `GET /v1/teams/{team_uuid}/tasks/{task_uuid}/generation-artifacts` | ES-06 immutable artifact metadata history，bounded/filterable | `200` |
| `GET /v1/teams/{team_uuid}/tasks/{task_uuid}/generation-artifacts/{artifact_uuid}` | Task-reachable artifact safe metadata/detail；不下载bytes | `200` |
| `GET /v1/teams/{team_uuid}/tasks/{task_uuid}/generation-artifacts:current` | generation+IntakeItem消歧后的per-type current metadata set | `200` |
| `GET /v1/teams/{team_uuid}/tasks/{task_uuid}/gates` | bounded Gate projection，默认open | `200` |
| `GET /v1/teams/{team_uuid}/tasks/{task_uuid}/gates/{gate_uuid}` | 安全ReviewTarget/evidence摘要 | `200` |
| `POST /v1/teams/{team_uuid}/tasks/{task_uuid}/gates/{gate_uuid}:decide` | exact target/revision受控decision | `200` / conflict `409` |
| `GET /v1/teams/{team_uuid}/task-restarts` | Team全局restart分页/过滤 | `200` |
| `GET /v1/teams/{team_uuid}/task-restarts/{restart_uuid}` | restart+joined Task summary | `200` |
| `GET /v1/teams/{team_uuid}/task-lineage` | 单seed bounded causal graph | `200` |

GenerationArtifact三条route的exact query/response、owner-chain、filter与redaction由ES-06 §5.9拥有；ES-01只承载token/Team/Task HTTP adapter。List/get/current均为metadata read，不返回logical handle、artifact bytes、model/Prompt/Invocation、Execution/Process/fence或absolute path。任意POST/PUT/PATCH/DELETE及download/export route均返回`405 generation-artifact-read-only`且零side effect。

#### 4.3.3 同步Retrieval

`POST /v1/teams/{team_uuid}/retrieval:search`是唯一同步retrieval入口。它使用`mkb.retrieval-search.v1`/`mkb.retrieval-result.v1`，exact request/result由ES-07冻结。该route直接调用ES-07 read port，不写Task、Audit、Execution、Process或outbox；任何raw-vector route均禁止。

HTTP facade固定执行：

1. authenticate token并在任何resource/filter lookup前绑定path Team；
2. strict parse schema_version、query、optional scope/where、top_k与context_budget_scalars；
3. 拒绝body Team、raw query vector、model/metric/index/threshold/backend、SQL和unknown fields；
4. 调用一次RetrievalSearchPort.search，传trusted TeamAuthContext而不是caller body identity；
5. 200只序列化hits或typed empty；4xx/5xx使用ES-01 safe RFC7807 envelope；
6. response leak guard拒绝vector array/BLOB、query embedding、model/provider/path/secret、Execution/Process/fence或final answer字段。

Request边界由ES-07固定为query 1..2048 Unicode scalars且UTF-8最多16KiB、scope source最多32/item最多128、where最多16、top_k 1..20、context budget 1000..32000。Body仍受ES-08 transport总上限，任一更小限制优先。

Result必须含request UUID、outcome、retrieval policy ref、serving snapshot digest、eligible counts、hits与budget。每个hit含matched representation、1..3个original evidence、exact anchors、Item/Revision/commit/projection/generation/publication provenance及score explanation；绝不返回raw vector。

Status mapping：

| Condition | HTTP |
|---|---|
| valid hits或typed empty | 200 |
| invalid query/scope/filter/budget | 422 |
| Team auth/anti-enumeration failure | ES-01统一401/403/404 |
| embedding/provider/DB temporarily unavailable | 503 |
| binding/snapshot/integrity failure | 503；不得伪装empty |
| unexpected safe internal error | 500 |

retrieval不使用202、不返回Task location、不接受Idempotency-Key映射为Task。Caller重发是新的同步request/receipt；ES-07内部query Invocation/receipt不是公共异步resource。

### 4.4 公共envelope

#### 4.4.1 Task Create

```json
{
  "schema_version": "mkb.task.v1",
  "team_uuid": "UUIDv4-or-v7",
  "task_uuid": "UUIDv4-or-v7",
  "trace_uuid": "UUIDv4-or-v7",
  "request_intent": "intake.ingest",
  "title": "optional",
  "description": "optional",
  "priority": "normal",
  "deadline_at": null,
  "payload": {},
  "payload_extra": {},
  "audit": {
    "schema_version": "mkb.task-audit.v1",
    "team_uuid": "same",
    "task_uuid": "same",
    "trace_uuid": "same",
    "audit_type": "business_review",
    "audit_status": "approved",
    "source": "upstream-orchestrator",
    "source_version": null,
    "actor_uuid": null,
    "parent_task_uuid": null,
    "created_at": "2026-08-10T00:00:00.000Z",
    "reviewed_at": null,
    "expires_at": null,
    "reason": null,
    "payload_extra": {}
  }
}
```

必填：`schema_version/team_uuid/task_uuid/trace_uuid/request_intent/payload/payload_extra/audit`。`task_type`、caller-supplied Intake identity（ingest时）、Execution/Process/status/progress/result/claim/lease字段一律strict reject。`priority=low|normal|high|urgent`，默认`normal`；`deadline_at`若提供必须晚于server `received_at`，但它不是Task状态或成功条件。

#### 4.4.2 六种intent payload discriminator

| Intent | payload schema | Exact顶层字段 | 专属owner |
|---|---|---|---|
| `intake.ingest` | `mkb.intake-ingest.v1` | `source_descriptor`、`clean_profile_ref?`、`canonical_metadata?`、`external_resource_uuid?` | ES-03 |
| `intake.rebuild` | `mkb.intake-rebuild.v1` | `source_task_uuid`、`source_generation`、`intake_item_uuid`、`expected_intake_revision_uuid?`、`reason` | ES-01/03 |
| `intake.update_metadata` | `mkb.intake-update-metadata.v1` | `intake_item_uuid`、`expected_item_revision`、`expected_intake_revision_uuid?`、`canonical_metadata`、`reason` | ES-03 |
| `intake.deactivate` | `mkb.intake-deactivate.v1` | `intake_item_uuid`、`expected_item_revision`、`reason` | ES-03 |
| `intake.delete` | `mkb.intake-delete.v1` | `intake_item_uuid`、`expected_item_revision`、`reason` | ES-03 |
| `index.rebuild` | `mkb.index-rebuild.v1` | discriminated `scope`、`reason` | ES-07 |

共同规则：所有payload均`extra='forbid'`；引用UUID只接受v4/v7；`reason`为1..2000字符；secret只允许`secret_ref`，不得携带credential bytes。`source_descriptor`只允许四个kind；其exact union由ES-03写入同名OpenAPI component。`index.rebuild.scope`只允许`team|intake_source|intake_item|intake_revision`四个已存在资源范围，不接受SQL、物理index名、backend或path。

#### 4.4.3 Mutation command

```json
{
  "schema_version": "mkb.task-command.v1",
  "command_uuid": "UUIDv4-or-v7",
  "expected_revision": 7,
  "reason": "bounded reason",
  "payload_extra": {}
}
```

Cancel、full retry、Team lifecycle command都使用等价的strict command envelope。Gate decision改用ES-03的`mkb.gate-decision.v1`，但必须包含`decision_uuid/expected_gate_revision/target_digest/action/actor_evidence/payload_extra`。

#### 4.4.4 Success/error envelope

```json
{
  "schema_version": "mkb.response.v1",
  "request_id": "UUIDv7",
  "trace_uuid": "UUIDv4-or-v7-or-null",
  "data": {},
  "links": {}
}
```

```json
{
  "schema_version": "mkb.error.v1",
  "request_id": "UUIDv7",
  "trace_uuid": "UUIDv4-or-v7-or-null",
  "error": {
    "code": "revision-conflict",
    "message": "safe bounded message",
    "retryable": false,
    "details": {}
  }
}
```

`details`只允许schema issue、safe current revision/status、poll hint等白名单字段；禁止token、stack、SQL、driver、absolute path、Process input/output或secret reference value。

### 4.5 Task public read model

| Axis | Exact内容 |
|---|---|
| Identity | `team_uuid/task_uuid/trace_uuid/schema_version/request_intent` |
| Description | `title/description/priority/deadline_at/payload_extra` |
| Aggregate status | 六态、`revision/current_generation`、时间、bounded progress |
| Readiness | `not_ready/ready/terminal_failed/terminal_cancelled` |
| Scatter | `total/required/active/succeeded/failed/cancelled/skipped`及items link |
| Result/error | intent-specific typed summary、proof refs和canonical Intake/derived links |
| Action required | open gate count/kinds、安全summary和Task-scoped links |
| Visibility | `visible/deleted`、`deleted_at`、tombstone summary |
| History | generations/restarts/lineage + Task-scoped GenerationArtifact metadata links |

禁止返回root/child `execution_uuid`、`process_uuid`、phase、lease/fence、retry counter、internal storage locator或raw model payload。内部引用可存在于数据库，但必须由response mapper删除。

### 4.6 Task aggregate状态机

```text
create
  → queued
      ├─→ running ─→ succeeded
      │      ├─────→ failed
      │      └─────→ cancelling ─→ cancelled
      └────────────→ cancelling ─→ cancelled

failed ── full retry/new generation ─→ queued
cancelled ─ full retry/new generation ─→ queued
```

| Transition | 唯一触发 | Guard | 同提交效果 |
|---|---|---|---|
| create→`queued` | TaskIngressService | token、strict schema、active Team、fingerprint、Audit | Task/Audit/outbox；generation=1，revision=1 |
| queued→`running` | ES-02 aggregate proposal | current root durable且与generation绑定；无cancel winner | started_at、revision、root pointer |
| queued/running→`cancelling` | cancel command | command replay/CAS；Task非terminal | cancel fact、revision、control outbox |
| running→`succeeded` | ES-02 terminal proposal | current root、generation、all required guards、intent proof valid、cancel未赢 | result/proof/count summary、completed_at、revision |
| running→`failed` | ES-02 terminal proposal | current generation terminal、无active recovery、aggregate guard valid | error/count summary、completed_at、revision |
| cancelling→`cancelled` | ES-02 convergence proposal | descendants fenced/terminal、无late commit | cancel summary、completed_at、revision |
| failed/cancelled→`queued` | full retry command | expected revision、source generation、retry admission、command fingerprint | restart row、generation+1、清空current projection、新outbox、revision |

所有其他边非法。Terminal不可原地复活；full retry是创建新generation/root的唯一回边。`succeeded`只能通过新`intake.rebuild`或`index.rebuild` Task重做。Success/cancel race以Task row的CAS first-commit-wins为唯一线性化点。

### 4.7 Team admission mutation graph

```text
register → active ↔ inactive
              \       /
               → deleted → restore → inactive
```

`deleted`不能直接activate。每个mutation必须带`expected_revision`；Team soft-delete不取消Task、不删除Audit/结果/资产。该graph只约束接入投影字段，明确不构成D02第七StateFamily。

### 4.8 核心执行链与原子边界

#### 4.8.1 Create

```text
verify token
→ parse strict Task/Audit/payload
→ validate UUID versions + path/body identity equality
→ canonicalize immutable create envelope
→ SHA-256 fingerprint
→ begin unit of work
   → require Team.active
   → resolve same replay / identity conflict
   → validate referenced resource causation where applicable
   → insert Task
   → insert immutable Audit
   → for intake.rebuild insert accepted TaskRestart
   → insert outbox(TaskStartRequested.v1)
→ commit
→ return poll links
→ scheduler may deliver only committed outbox
```

任一步失败均不得留下Task/Audit/Restart/Execution/Process/Intake/derived row或可claim work。

#### 4.8.2 Poll

Get Task从Task aggregate读取有界主体；items/generations/gates/lineage通过owner read ports keyset分页组合。组合只生成read model，不回写StateFamily。`not_ready`返回`202`，terminal failure/cancel返回`200` terminal envelope，success返回`200 ready`。

#### 4.8.3 Cancel

Cancel command先按`command_uuid+fingerprint`幂等解析，再以`expected_revision`将Task推进`cancelling`并提交`TaskCancelRequested.v1`。ES-02负责向下传播和fence；只有`TaskCancellationConverged.v1` proposal通过guard后才能`cancelled`。已proof-valid child不回滚。

#### 4.8.4 Full retry

failed/cancelled Task在一个事务内创建`TaskRestart(scope=full_task)`、generation+1、Task→queued与`TaskStartRequested.v1`。旧generation summary永不修改。重复command返回同一restart/target generation；不同fingerprint冲突。

#### 4.8.5 Atomic rebuild

新`intake.rebuild` Task必须使用新caller Task identity，并在同一create事务写`TaskRestart(scope=atomic_intake_item)`、Task、Audit和outbox。旧Task/tree/Revision不修改；rebuild本身不创建新Revision。

#### 4.8.6 Gate decision

API只做token、Task scope和strict envelope校验，然后调用本文件声明、由ES-03实现的`GateFacadePort`。ES-03再经`ExecutionGateOwnerPort`在append decision + Gate CAS + Execution wake/failure outbox提交后返回committed result。HTTP接收、UI action或API日志均不等于release。

---

## 5. Contracts and Data

### 5.1 数据类型约定

| Logical type | Physical default | 约束 |
|---|---|---|
| UUID | `TEXT` lowercase canonical | v4/v7 validator；内生v7 |
| Timestamp | `TEXT` UTC RFC3339 | lexical order可用，但正确性不依赖UUID时间序 |
| JSON object | `TEXT` canonical JSON | `json_valid=1`且`json_type='object'` |
| Digest | `TEXT` lowercase hex SHA-256 | 长度64 |
| Boolean | `INTEGER` | `0/1` |
| Counter/revision | `INTEGER` | `>=0`；不是领域ID |

所有下列MKB-owned业务表都必须包含非空`payload_extra` object。Exact SQL、FK defer模式和migration由ES-04生成，但不得减少本节列/约束。

### 5.2 `teams`

| Column | Null/default | Constraint / semantics |
|---|---|---|
| `team_uuid` | no | PK；caller UUIDv4/v7；immutable |
| `schema_version` | no | `mkb.team.v1` |
| `name` | no | 1..200字符 |
| `description` | yes | 最大2000字符 |
| `status` | no/`active` | `active/inactive/deleted` admission fact |
| `revision` | no/`1` | CAS counter |
| `creation_fingerprint` | no | Team create canonical digest |
| `fingerprint_version` | no | `mkb-jcs-sha256-v1` |
| `created_at/updated_at` | no | server UTC |
| `deactivated_at/deleted_at` | yes | lifecycle evidence |
| `payload_extra` | no/`{}` | uninterpreted JSON object |

索引：`(status, created_at, team_uuid)`。禁止owner/member/role/plan/billing/quota/password/user列。

### 5.3 `tasks`

| Column group | Exact columns | Constraint / semantics |
|---|---|---|
| Identity | `team_uuid, task_uuid, trace_uuid` | PK`(team_uuid,task_uuid)`；三者immutable |
| Contract | `schema_version, request_intent, payload_schema_version, payload_json` | immutable strict input |
| Idempotency | `creation_fingerprint, fingerprint_version` | immutable；复合identity冲突判定 |
| Description | `title, description, priority, deadline_at, payload_extra` | 白名单mutation；priority仅queued |
| Lifecycle | `status, revision, current_generation, current_root_execution_uuid` | 六态；root pointer内部only |
| Cancel fact | `cancel_command_uuid, cancel_fingerprint, cancel_requested_at, cancel_reason` | nullable；本generation至多一个winner |
| Scatter refs | `intake_snapshot_uuid, change_set_digest` | typed refs，不拥有Intake truth |
| Counts | `total_count, required_count, active_count, succeeded_count, failed_count, cancelled_count, skipped_count` | 非负；projection可重建 |
| Summary | `progress_schema_version, progress_json, result_schema_version, result_summary_json, error_schema_version, error_summary_json, proof_schema_version, proof_ref_json` | typed JSON；不得塞payload_extra |
| Time | `received_at, started_at, completed_at, updated_at` | server UTC |
| Visibility | `deleted_at, deleted_reason` | status不含deleted |

约束：

- status check=`queued/running/cancelling/succeeded/failed/cancelled`；
- priority check=`low/normal/high/urgent`；
- `current_generation>=1`、`revision>=1`、counts非负；
- `(team_uuid, current_root_execution_uuid)`必须逻辑归属于同Task/current generation；ES-04以deferred FK/trigger和ES-02 guard实现；
- terminal必须有`completed_at`；succeeded必须有type-specific proof；active不得有ready result；
- ordinary update不得修改immutable列。

索引：

```text
PK (team_uuid, task_uuid)
INDEX (team_uuid, status, received_at DESC, task_uuid DESC)
INDEX (team_uuid, request_intent, received_at DESC, task_uuid DESC)
INDEX (team_uuid, priority, status, received_at, task_uuid)
INDEX (trace_uuid, received_at, team_uuid, task_uuid)
INDEX (team_uuid, deleted_at, updated_at DESC, task_uuid DESC)
```

### 5.4 `task_audits`

| Column | Null/default | Constraint / semantics |
|---|---|---|
| `team_uuid, task_uuid` | no | PK+FK to Task；1:1，ON DELETE RESTRICT |
| `schema_version` | no | `mkb.task-audit.v1` |
| `trace_uuid` | no | 等于Task.trace_uuid |
| `audit_type` | no | v1=`business_review` |
| `audit_status` | no | `pending/approved/rejected/waived/not_required`；MKB不解释 |
| `source/source_version` | source no | upstream evidence |
| `actor_uuid/parent_task_uuid` | yes | UUIDv4/v7；不建立权限或workflow |
| `created_at` | no | upstream timestamp，原offset事实规范化输出 |
| `reviewed_at/expires_at` | yes | 不触发MKB admission/token expiry |
| `reason` | yes | bounded upstream reason |
| `received_at` | no | server UTC；与created_at分离 |
| `payload_extra` | no/`{}` | immutable object |

表无update/delete repository；Task patch/retry/delete均不得改变Audit。

### 5.5 `task_restarts`

| Column group | Exact columns | Constraint / semantics |
|---|---|---|
| Identity | `restart_uuid, team_uuid` | restart UUIDv7 PK；team fence |
| Scope | `restart_scope` | `atomic_intake_item/full_task`；不是StateFamily |
| Cause | `source_task_uuid, source_generation, source_root_execution_uuid, intake_item_uuid, intake_revision_uuid, causation_trace_uuid` | atomic/full按schema必填 |
| Target | `restart_task_uuid, target_generation, target_root_execution_uuid` | accepted后可解析；rejected可空 |
| Command | `command_uuid, command_fingerprint, fingerprint_version, reason` | replay/冲突依据 |
| Admission | `admission_outcome, decision_code` | `accepted/rejected` immutable typed fact |
| Time | `requested_at, decided_at` | server UTC |
| Extension | `payload_extra` | object，immutable |

索引/约束：

```text
PK (restart_uuid)
UNIQUE (team_uuid, source_task_uuid, command_uuid)
INDEX (team_uuid, source_task_uuid, requested_at DESC, restart_uuid DESC)
INDEX (team_uuid, restart_task_uuid, requested_at DESC, restart_uuid DESC)
INDEX (team_uuid, intake_item_uuid, requested_at DESC, restart_uuid DESC)
INDEX (team_uuid, restart_scope, admission_outcome, requested_at DESC, restart_uuid DESC)
INDEX (causation_trace_uuid)

accepted atomic_intake_item:
  UNIQUE (team_uuid, restart_task_uuid, restart_scope)

accepted full_task:
  UNIQUE (team_uuid, source_task_uuid, source_generation, restart_scope)
  UNIQUE (team_uuid, source_task_uuid, target_generation, restart_scope)
```

Restart没有current status列；查询状态必须LEFT JOIN target Task/generation summary。

### 5.6 Read projections（非SSOT）

| Projection | Source Truth | 稳定排序 |
|---|---|---|
| Task list | `tasks` | `received_at DESC, task_uuid DESC` |
| TaskItem page | ES-03 Membership/ChangeSet + ES-02 child summaries + ES-07 publication proof | frozen set rank + `intake_item_uuid` |
| Generation page | ES-02 root Execution terminal summaries + Restart | `generation DESC` |
| Gate page | ES-03 Gate/Decision | `created_at DESC, gate_uuid DESC` |
| Restart page | `task_restarts` + Task LEFT JOIN | `requested_at DESC, restart_uuid DESC` |
| Lineage graph | Restart + Task + Intake + generation summaries | bounded BFS then stable typed key |

Projection可以物化缓存，但缓存无transition权；任一漂移以owner Truth重建。

### 5.7 Application ports

```python
class TaskIngressPort(Protocol):
    async def create(self, command: CreateTaskV1) -> TaskCreateResult: ...

class TaskQueryPort(Protocol):
    async def get(self, key: TaskKey) -> TaskViewV1: ...
    async def list(self, query: TaskListQueryV1) -> CursorPage[TaskSummaryV1]: ...
    async def result(self, key: TaskKey) -> TaskResultEnvelopeV1: ...

class TaskMutationPort(Protocol):
    async def patch(self, command: PatchTaskV1) -> TaskViewV1: ...
    async def cancel(self, command: CancelTaskV1) -> TaskViewV1: ...
    async def retry(self, command: RetryTaskV1) -> TaskViewV1: ...
    async def soft_delete(self, command: DeleteTaskV1) -> TaskTombstoneV1: ...

class TaskAggregateOwnerPort(Protocol):
    async def apply(self, proposal: TaskAggregateProposalV1) -> TaskViewV1: ...

class WorkflowIngressPort(Protocol):
    async def on_task_start(self, message: TaskStartRequestedV1) -> None: ...
    async def on_task_cancel(self, message: TaskCancelRequestedV1) -> None: ...

class WorkflowReadPort(Protocol):
    async def list(self, query: WorkflowListQueryV1) -> CursorPage[WorkflowSummaryV1]: ...
    async def get_active(self, workflow_key: str) -> CompiledWorkflowViewV1: ...
    async def get_revision(self, workflow_key: str, revision_number: int) -> CompiledWorkflowViewV1: ...

class TaskItemReadPort(Protocol): ...       # implemented by ES-02/03/07 composition
class GateFacadePort(Protocol): ...         # implemented by ES-03
class LineageReadPort(Protocol): ...        # composed across ES-02/03/04
class GenerationArtifactQueryPort(Protocol): ...  # implemented by ES-06; Task-scoped safe metadata only
class RetrievalSearchPort(Protocol):
    async def search(self, auth: TeamAuthContext, request: RetrievalSearchV1) -> RetrievalResultV1: ...  # ES-07
```

Repository只能保存/读取aggregate；只有`TaskTransitionService`实现`TaskAggregateOwnerPort`。ES-02 worker、outbox consumer、HTTP controller均不得获得裸`update_status`方法。

### 5.8 Internal durable protocol

统一消息envelope：

```json
{
  "message_version": "mkb.internal-message.v1",
  "message_uuid": "UUIDv7",
  "message_type": "task.start-requested.v1",
  "occurred_at": "UTC RFC3339",
  "team_uuid": "UUID",
  "task_uuid": "UUID",
  "trace_uuid": "UUID",
  "generation": 1,
  "causation_uuid": "request-or-command UUID",
  "correlation_uuid": "root trace UUID",
  "payload": {},
  "payload_extra": {}
}
```

| Message | Producer→Consumer | Required payload | Idempotency/guard |
|---|---|---|---|
| `task.start-requested.v1` | ES-01→ES-02 | intent、payload schema/digest、task revision、restart ref? | `(task,generation)`最多一个root；consumer加载immutable Task input |
| `task.cancel-requested.v1` | ES-01→ES-02 | command UUID、task revision、generation、requested_at | 同command/generation重放幂等；旧generation忽略并留event |
| `task.aggregate-proposed.v1` | ES-02→ES-01 | root UUID、generation、expected task revision、target status、counts、summary、proof ref | ES-01验证root/generation/status edge/proof；不能由consumer直写 |
| `task.cancellation-converged.v1` | ES-02→ES-01 | root UUID、descendant fence summary | 只允许cancelling→cancelled |
| `gate.decision-requested.v1` | ES-01 facade→ES-03 | opaque gate ref、revision、target digest、decision/actor | ES-03 owns append+CAS；stale fail-closed |
| `task.projection-repair-requested.v1` | ES-08 scanner→ES-01 | mismatch evidence digest、expected owner refs | 必须走同一transition/rebuild path并留repair event |

投递语义固定为at-least-once；正确性来自committed outbox、message UUID去重、aggregate CAS和type-specific guards，不来自exactly-once transport。

---

## 6. State / Consistency / Failure

### 6.1 核心不变量

1. Task权威键永远是`(team_uuid,task_uuid)`；任何裸task lookup均为代码审计失败。
2. Task/Audit为1:1且原子成立；Audit immutable。
3. 同identity同fingerprint只返回原Task；不同fingerprint永不覆盖。
4. 一个Task可有多代root，但任一时刻只有一个current generation/root。
5. Task状态只能由TaskTransitionService推进；ES-02只提交proposal。
6. Task succeeded必须消费current root的intent-specific proof；无proof即fail-closed。
7. Cancel只停止未来工作，不回滚proof-valid资产。
8. Soft-delete只改变可见性，不改变status或长期证据。
9. open Gate时Task为running；action_required不是状态。
10. 所有public读面team-scoped、bounded，且Process cleanup后仍可解释。

### 6.2 Fingerprint

Fingerprint输入为strict解析后的完整immutable create模型，使用UTF-8、确定性object-key排序、规范number/string/null表示；排除header、token、request ID和所有server-generated字段。算法标识`mkb-jcs-sha256-v1`与digest一起持久化。Task后续Patch不改变fingerprint。若未来算法升级，旧行继续用原version比较，不重算覆盖。

### 6.3 CAS与并发

- 所有Team/Task mutation谓词至少包含`identity + expected_revision + expected status/visibility + current_generation`；
- success/cancel race只认Task row first committed CAS；失败方重新读current truth，不做补偿反转；
- full retry先按command UUID/fingerprint查重，再验证source generation/revision，避免成功响应丢失后的重放产生双generation；
- ES-02 proposal必须绑定root execution、generation和proof digest；stale proposal写`stale-proposal` event后no-op；
- cursor绑定filter digest与snapshot boundary；被篡改、跨filter复用或版本未知返回`400 invalid-cursor`。

### 6.4 错误分类

| HTTP | Code | Retryable | 处理 |
|---:|---|---:|---|
| 400 | `invalid-cursor` | no | 重启分页 |
| 401 | `invalid-internal-token` | no | 在资源lookup前拒绝 |
| 404 | `team-not-registered` / `task-not-found` | no | 不泄漏跨team资源 |
| 409 | `team-not-active` | no | activate/restore后重试 |
| 409 | `task-identity-conflict` | no | 使用新Task identity或原始payload |
| 409 | `revision-conflict` | conditional | 刷新current revision |
| 409 | `task-active` | conditional | 等待/cancel |
| 409 | `retry-not-allowed` | no | succeeded需新rebuild Task |
| 409 | `restart-causation-conflict` | no | 修正source Task/Item/Revision |
| 409 | `gate-decision-conflict` | conditional | 刷新Gate current truth |
| 410 | `team-deleted` / `task-deleted` | no | 返回安全tombstone |
| 413 | `request-too-large` | no | 改用local_object或减小envelope |
| 415 | `unsupported-media-type` | no | 使用JSON |
| 422 | `contract-schema-invalid` / `invalid-uuid-version` | no | 修正输入；无业务行 |
| 202 | `task-result-not-ready` | yes/poll | 正常polling，不是失败 |
| 429 | `rate-limited` | yes | 遵守Retry-After；policy归ES-08 |
| 500 | `internal-error` | conditional | 不泄漏详情；按request ID诊断 |
| 503 | `dependency-not-ready` | yes | readiness/依赖恢复后重试 |

### 6.5 Failure与恢复

| Failure point | Required outcome |
|---|---|
| strict validation/token/team gate失败 | 零业务行；仅安全rejection event |
| Audit/Restart/outbox insert失败 | 整个Task事务回滚 |
| commit成功、response丢失 | caller replay得到原Task/restart，不创建新root |
| commit成功、wake-up丢失 | ES-04/08 outbox scanner重投；Task仍queued而非丢失 |
| duplicate message | handler以message UUID和aggregate guard幂等 |
| stale aggregate proposal | no-op + drift event；不得覆盖新generation |
| Task projection/count损坏 | 从Execution/Membership/proof重建，经owner repair path提交 |
| Process cleanup | Task/generation/result/proof/restart/lineage保持完整 |
| token/secret/driver异常 | safe error；无敏感信息进入response/payload_extra |

### 6.6 Retention fence

Task、Audit、Restart、generation terminal summary和proof引用按ES-08-v1.0保留deployment lifetime，V1不自动hard-delete。Process detail只有terminal满90天、ES-02 summary/cleanup fence/无pointer、lease、outbox或hold全部闭合后，才可由`process_detail_retention_v1`清理；清理前后所有本文件public projection canonical digest必须相同。

---

## 7. Legacy Retain / Rewrite / Drop

| Legacy evidence | Retain | Rewrite | Drop |
|---|---|---|---|
| `smind-admin/ingestion/files.ts` | team/trace/resource/workflow身份分面、commit后投递意图 | caller-owned Task + atomic outbox | 内部临时job作为外部Task、R2/queue拓扑 |
| `smind-admin/ingestion/apis.ts` | API scatter需求、stable member identity | 一个Task+root+children+SnapshotMembership | user/plan/phone gate、平台authority |
| `smind-clean-dispatcher/core/schemas_smcp.ts` | identity/control/extra分面、case语义 | `request_intent` + versioned process manifest | callback contract、generic job/task type |
| `smind-clean-dispatcher/flows/finalizer.ts` | 完整member set后fan-out、siblings并行 | transactional membership/outbox/collect-all | first-child hint、重新生成job、callback驱动成功 |
| `smind-clean-dispatcher/services/restarter.ts` | 人工重做与max-retry风险 | full retry generation + atomic rebuild新Task | public stage/process restart、force step |
| `smind-rag-dispatcher/flows/finalizer.ts` | healthy child可独立ready | proof-backed TaskItem projection | parent-untouched passive completion |
| `smind-console` file/restart/debug routes | team-scoped原子项查询和诊断需求 | bounded Task/items/generation/lineage read models | UI、platform auth、legacy schema兼容 |

Legacy仅是ReferenceAnchor。新runtime、DDL、wire、bootstrap和acceptance必须零legacy依赖。

---

## 8. Acceptance Evidence

本节45项全部为`HARD`；实现任一失败即conformance/release blocked，且不得以manual waiver、partial pass或后续补测跳过。

### 8.1 Contract与边界

| ID | Scenario | HARD assertion |
|---|---|---|
| `ES01-A001` | 无/错token访问任一业务route | 资源lookup前401；零side effect |
| `ES01-A002` | UUIDv4/v7与其他UUID版本 | v4/v7 round-trip；其他422且零行 |
| `ES01-A003` | unknown field、旧`task_type`、caller runtime字段 | strict reject；零业务行 |
| `ES01-A004` | API inventory | 恰含有限capability/Workflow-read/Team/Task/polling/gate/artifact-read/retrieval surface；Workflow/artifact mutation均405，且无callback/raw-vector/Execution CRUD |
| `ES01-A005` | schema/import scan | 无user/member/role/billing、Attempt、legacy/03-nano DTO依赖 |

### 8.2 Transaction、幂等、并发

| ID | Scenario | HARD assertion |
|---|---|---|
| `ES01-A006` | Task/Audit/outbox逐点fault injection | all-or-nothing；未提交work不可claim |
| `ES01-A007` | 同identity同fingerprint并发create | 恰一Task/Audit/root request；所有caller得到同identity |
| `ES01-A008` | 同identity不同fingerprint | 409；原input/Audit不变 |
| `ES01-A009` | stale Team/Task revision | 409 safe current summary；无lost update |
| `ES01-A010` | duplicate cancel/retry message | 一个cancel winner或一个target generation |
| `ES01-A011` | cancel/success竞态重复1,000次 | 每次一个durable terminal winner，无反转 |

### 8.3 状态与查询

| ID | Scenario | HARD assertion |
|---|---|---|
| `ES01-A012` | 六态合法/非法边穷举 | 只允许§4.6；retry回边总伴随新generation/root |
| `ES01-A013` | queued/running/cancelling result | 202 + not_ready，不是404 |
| `ES01-A014` | succeeded无valid proof proposal | Task拒绝succeeded |
| `ES01-A015` | failed/cancelled/succeeded result | readiness三类terminal可区分 |
| `ES01-A016` | open Gate | Task仍running；action_required有界且无runtime身份 |
| `ES01-A017` | soft-delete | status不变；精确Get 410 tombstone；Audit/restart/lineage仍可读 |
| `ES01-A018` | 大items/restarts/lineage分页 | stable cursor，无重复/遗漏/跨team泄漏 |

### 8.4 Single/scatter/restart

| ID | Scenario | HARD assertion |
|---|---|---|
| `ES01-A019` | single ingest | 1 Task/1 current root/0 child；外部只依赖Task |
| `ES01-A020` | scatter N required | 1 Task/1 root/N child；无child Task或singular current Process |
| `ES01-A021` | child proof早于root终态 | child ready可见；parent仍running |
| `ES01-A022` | collect-all mixed outcome | siblings继续；全部required terminal后Task failed；ready child不回滚 |
| `ES01-A023` | forward-stop cancel | 未完成work停止；proof-valid child保留；收敛后才cancelled |
| `ES01-A024` | full retry | 同Task新generation/root；旧summary immutable |
| `ES01-A025` | atomic rebuild | 新Task/Audit/restart/outbox原子成立；Item/Revision identity不变 |

### 8.5 Failure、安全与可恢复性

| ID | Scenario | HARD assertion |
|---|---|---|
| `ES01-A026` | response/log leak scan | 无token、secret、stack、SQL、path、driver、Process payload |
| `ES01-A027` | wake-up丢失/重复 | scanner补发；只形成一棵root业务事实 |
| `ES01-A028` | stale old-generation proposal | no-op+event；current Task不变 |
| `ES01-A029` | projection corruption | owner repair从durable truth恢复并留证据 |
| `ES01-A030` | Process projection清理 | Task/result/items/generation/restart/lineage语义完整 |
| `ES01-A031` | 03-nano与legacy全部不可用 | MKB core可独立启动并执行合法journey |
| `ES01-A032` | 同步retrieval.search | Task/Audit/Execution/Process/outbox新增均为0 |

### 8.6 GenerationArtifact只读面

| ID | Scenario | HARD assertion |
|---|---|---|
| `ES01-A033` | artifact history list | Task-scoped、bounded稳定分页，type/disposition/generation/Item filter exact |
| `ES01-A034` | artifact safe detail | 只返回ES-06 safe metadata/lineage/validation/current，不返回bytes/internal refs |
| `ES01-A035` | scatter current query | 必填generation+Item消歧；不公开Execution identity |
| `ES01-A036` | cross-Team/unreachable artifact | uniform 404，零existence disclosure |
| `ES01-A037` | artifact mutation/download | POST/PUT/PATCH/DELETE/export均405且零side effect |

### 8.7 Semantic retrieval facade

| ID | Scenario | HARD assertion |
|---|---|---|
| ES01-A038 | valid semantic request | exact ES-07 schema进入port；200 result schema-valid |
| ES01-A039 | body Team/raw vector/model/SQL/unknown field | strict 422；port/provider calls=0 |
| ES01-A040 | no eligible/no semantic match | 200 typed empty，不能是404/202/假error |
| ES01-A041 | provider/snapshot/integrity failure | safe 503；不得转empty或partial hits |
| ES01-A042 | hit response | original evidence/anchor/provenance/scores完整 |
| ES01-A043 | disclosure scan | no vector/model/path/secret/runtime/final-answer field |
| ES01-A044 | retrieval side effects | Task/Audit/Execution/Process/outbox新增均0；内部receipt不外显 |
| ES01-A045 | wrong-Team/anti-enumeration | auth在lookup前；zero hit/existence leakage |

### 8.8 必须交付的证据包

1. OpenAPI + JSON Schema golden snapshot；
2. strict Pydantic model和response-redaction tests；
3. Task/Team状态边property tests；
4. 真实Turso-compatible driver transaction、FK、partial unique和CAS tests；
5. create/cancel/retry并发及fault-injection报告；
6. dependency/import/schema architecture gates；
7. single、scatter、gate、cancel、retry、atomic rebuild、GenerationArtifact metadata read及semantic retrieval端到端记录；
8. DDL inspection：四张业务表均有`payload_extra`，无Attempt/平台表；
9. owner-truth trace matrix，证明本文件列出的每个适用Truth至少命中一个test或schema gate。

---

## 9. Remaining Technical Decisions and Defaults

本节没有Owner问题。以下均为已裁决默认值；只有技术证据证明不满足同一Truth时才可在本文件内修订。

| Topic | v1 default | 验证/变更门槛 |
|---|---|---|
| HTTP framework | FastAPI + Pydantic v2 strict models | OpenAPI稳定性、ASGI integration、dependency gate |
| API prefix | `/v1`；schema内部仍显式`mkb.*.v1` | breaking change必须新contract version |
| Fingerprint | deterministic canonical JSON + SHA-256，id=`mkb-jcs-sha256-v1` | cross-language golden vectors |
| UUID generation | 单一UUIDv7 provider | monotonicity非正确性依赖；碰撞/clock rollback tests |
| Page size | default 50，max 200 | ES-08 measured envelope可下调effective默认，不能取消bounded语义 |
| Cursor | versioned canonical payload + HMAC-SHA256；含filter digest/last key/expiry | tamper/filter replay/key rotation tests |
| Request body | 默认上限8 MiB；`payload_extra`编码后默认64 KiB | ES-08 strict config与measurement可下调；超限413；非产品SLA |
| Inline content | 默认1 MiB；更大输入使用`local_object` | ES-03/08真实语料测量后调整，不新增source kind |
| Transaction | Task/Audit/Restart/outbox同一local write transaction | ES-04必须用真实driver证明，不接受mock等价声称 |
| Delivery | committed outbox + in-process at-least-once scheduler | duplicate/lost wake-up tests |
| Hard delete | v1不自动hard-deleteTeam/Task/Audit/Restart | ES-08已冻结deployment-lifetime policy |
| Public diagnostics | 仅safe error/request ID；无internal admin API进入v1 contract | ES-08只提供非产品`/livez`、`/readyz`、authenticated metrics与本地closed CLI |

---

## 10. Revision History

| 版本 | 日期 | 状态 | 变更 |
|---|---|---|---|
| `ES-01-v0.1` | `2026-08-10` | `internally-consistent / awaiting cross-spec audit` | 基于4份frozen Owner Truth、S01-v1.5、S02-v1.3、D01-v1.4与D02-v1.0，冻结caller-neutral HTTP contract、Team接入投影、Task/Audit/Restart exact wire、Task六态、polling五轴、原子接收、逻辑schema、application ports、durable message、错误/恢复与acceptance；参考legacy identity/scatter/restart实践并删除其平台、callback和多Worker拓扑。未新增产品责任、StateFamily、部署单元或spec文件。 |
| `ES-01-v0.2` | `2026-08-10` | `internally-consistent / awaiting cross-spec audit` | 校准S03-v1.3 `T-O-14`：把ES-02拥有的Workflow list/get compiled detail只读面补入公共route inventory、capability discovery、application read port和acceptance；所有Workflow mutation明确405。该修订仅补齐baseline locked Truth，不新增Workflow authoring或产品能力。 |
| `ES-01-v0.3` | `2026-08-10` | `internally-consistent / awaiting cross-spec audit` | 接收ES-06-v0.1对`T-O-79`的exact实现：补入Task-scoped GenerationArtifact list/get/current三条metadata-only route、safe query port/redaction和5项acceptance；所有artifact mutation/download/export明确405。该修订不开放内容浏览、Execution身份、raw vector或新产品能力。 |
| ES-01-v0.4 | 2026-08-10 | internally-consistent / awaiting cross-spec audit | 接收ES-07-v0.1 exact retrieval contract：冻结唯一同步route的strict query/scope/filter/budget facade、hits/empty与4xx/5xx mapping、grounded result disclosure guard及8项acceptance；查询仍不创建Task/Audit/Execution/Process/outbox，raw vector/final answer继续禁止。未新增route capability、StateFamily、服务或spec。 |
| ES-01-v1.0 | 2026-08-10 | ready | 完成OT-01..04、baseline locked Truth及ES-02..08最终对账；33条产品route、六种异步intent、唯一同步semantic retrieval、Task六态、4张owner tables与45项HARD acceptance均已set-exact，版本引用统一。未新增产品能力、raw vector、final answer、状态族、服务或spec文件。 |
