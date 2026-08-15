# S14 — Config, Prompt & Model Registry

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 子系统**：`F2 治理基础 / S14 Config, Prompt & Model Registry`（配置分层·一致快照·Prompt 登记·Model Catalog 产品面·受控 override·产物 provenance）
>
> **日期**：`2026-08-12`
>
> **作者 / 裁决者**：`MKB owner + Grok workflow domain-truth-s14-s16`
>
> **文档性质**：`domain truth / formal subsystem specification`（**唯一执行真相 SSOT**）
>
> **文档状态**：`accepted`（S14 域内已接受；全系统 truth layer 尚未 frozen）
>
> **Truth 版本**：`S14-v1.1`
>
> **上游权威输入**：`D01–D05`、`S01–S13` accepted；`qna-truth/S14.md v1.0-qna-locked`（**证据层 / progressive 中间态 only**，非执行 SSOT）；冻结 Truth `T-O-263..286`；`spec-index` §3.14 / **G-10 closed for v1 transport** / **G-12 deferred** / G-13·G-14 closed
>
> **词汇权威**：`docs/baseline/spec-glossary.md`（`PromptRef` / `promptA|B|C` / `Readiness` / `WorkflowRevision` / `s05_binding_digest` / `GreenfieldBootstrap` / `ConfigSnapshot` 等）
>
> **事实证据**：`context/legacy-family/` 仅作 ReferenceAnchor（prompt/model/config 行为考古）；网络 Reference-Check（12-factor、GitOps、Fowler toggles、MLflow registry、OTel GenAI、RFC 9457、OWASP secrets）**仅作设计对照**；**禁止** `legacy-specs` / `legacy-python` / `legacy-python-2` 作为本域证据源
>
> **下游消费者**：`S01`、`S02`、`S03`、`S05–S11`、`S12`、`S15–S16`、跨系统拓扑 `17`、验收冻结 `18`、实现与 architecture tests

> **★ 执行 SSOT 声明（Owner 强制）**：实现、验收、对账 **只依赖本 domain-truth 文件**。`qna-truth/S14.md` 仅保留 progressive 形成过程（`T-O-263..286` 冻结轨迹），**不得**被引用为第二执行真相；冲突时 **以本文为准**。禁止「细节在 QNA、Spec 只写原则」。实现 **无需** 打开 QNA 即可编码。

> **★ 约束级别**：「必须 / 禁止 / 仅允许」= 强制；「应当」= 默认，偏离须 reopen S14；「可以 / 建议」= 非冻结不变量。

> **Owner 产品边界**：S14 是 **Config / Prompt / Model Registry 产品治理域**。它回答：配置从哪里来、如何热更新、如何构造一致快照、Task override 白名单、模型产物如何复现。**关键不变量**：每个模型产物可追溯到 **model + prompt + schema + params** 版本。  
> **不**拥有：Process/Task/Execution 状态机与 `max_retries`（S03/D01）；Inference transport/adapter SDK（S11）；ANN/publication 算法（S09）；prompt **正文**字节 SSOT（D03 `data/prompts/**` git）；Workflow 七表定义 SSOT（S03）；密钥生命周期（S16）；event retention 数值（S15）；平台 UI config console / agent authoring（OD-01 / G-12）。

> **邻域分账（入口）**：
>
> | 邻域 | S14 边界 |
> |---|---|
> | **D03** | Prompt 正文 SSOT = `data/prompts/**`（git）；DB **仅** hash/指针；`data/config/**` 非秘密默认；contracts = typed 唯一 SSOT |
> | **D04** | 物理表：`mkb_prompt_hash_pointers`、`mkb_model_catalog`、`mkb_adapter_bindings`（+ workflow 七表等）；S14 **不**另起第二 schema 闭集 |
> | **D05** | 生产 prompt 三身份闭集 **promptA/B/C**；`PromptRef` = identity + content_hash；S14 登记 identity→path→hash |
> | **S03** | Workflow **七表 relational SSOT** + compiled JSON 派生；S14 **不**双持 workflow 定义真相；只读 version/digest 治理视图 |
> | **S05/S06/S07** | 业务只持 **PromptRef / schema digest / model binding ref**；retry **不热切** active；正文与 catalog 物理解析归 S14/S11 |
> | **S08/S09/S10** | 阈值/topk/ANN knobs **可版本化配置** 可挂 S14；metric 默认/publication 定义不归 S14；promptA/B/C **不**用于 embed/vectorize 产品身份 |
> | **S11** | Inference 门面 + adapter transport + **invocation 写** + **runtime resolve 唯一权威**；S14 = 产品 registry / catalog·binding **bootstrap 写权威** / 版本治理 / provenance；默认行内容清单协作 S11 |
> | **G-10** | **closed for v1 transport**：禁 silent 换 model/adapter；跨模型须显式 binding/reopen |
> | **G-12** | **deferred**：agent authoring / external publication 治理 out-of-scope |
> | **S12/S13** | 表/字节 substrate；S14 不拥有 TX/GC；不把 log 当业务 SSOT |
> | **S15/S16** | 已 accepted 执行 SSOT：S15=export/retention/alert/readiness 聚合；S16=token/secret/egress；S14 钩子映射到 S15 目录，配置键分类含 `security.*`/`obs.*` Ops-only |

> **Legacy 边界（T-O-274 / T-O-42）**：不继承 D1+KV 双 prompt SSOT、`PROMPT_KV` 动态未哈希 key、硬编码 `@cf/...` / `gemini-*` 当唯一目录、structurizer 未注册 key 静默透传、contexter tenant override 热缓存无 digest、console prompt CRUD/deploy、`payload_config` 任意 merge 当 binding SSOT。

---

## 1. Domain 介绍

### 1.1 Domain 价值

S14 把 **可版本化的配置与 registry 产品语义** 变成 **可审计、可复现、可 fail-closed 的执行事实**，并保证：

1. 配置读取有 **分层优先级** 与 **materialize 一次冻结** 的 ConfigSnapshot / binding digest；  
2. Prompt 正文只在 git；DB 与 ProcessCommand 只持 **hash 指针**，运用路径 **hash 校验失败即停**；  
3. Model 身份 = `model_key`+`model_version`；路由 = `mkb_adapter_bindings`；**无** 浮动 `latest` / `@champion` 产品解析层；  
4. Task/Execution override **窄白名单**；未知键 reject；信任关键身份键 **不可** Task 覆盖；  
5. Binding-affecting 变更 **只影响未来** resolve；in-flight **只读** 已冻结 L4 快照；  
6. 每个模型产物可追溯到 **model + prompt + schema + params** 版本（provenance 进关系/CAS，**不是**日志字符串）；  
7. 实现者 **无需** 打开 QNA 即可编码与验收。

### 1.2 在整体拓扑中的位置

```text
git data/prompts/**  ──hash──►  mkb_prompt_hash_pointers / PromptRef
src/contracts/**     ──digest─► schema registry pointers (S06/S07/S14)
code bootstrap       ──rows───► mkb_model_catalog + mkb_adapter_bindings
git data/config/**   ──L0─────► defaults / feature_flags / profiles
env (S16 secrets)    ──L2─────► deploy topology + secret values only
S03 七表             ──SSOT───► workflow version / compiled digest (S14 read-only view)
         │
         ▼
S14 RegistryPort + ConfigResolve
  ├── resolve layers L0→L1→L2→L3
  ├── materialize once → L4 ConfigSnapshot / binding digests
  └── readiness probe (digest drift / bootstrap / hash mismatch)
         │
         ▼
S05/S06/S07/S08/S10  (consume PromptRef / snapshot / knobs)
S11 Inference        (consume catalog+binding; G-10 no silent swap)
```

**配置分层（产品序）**：

```text
L0  git data/config/** + code defaults          （非秘密语义默认）
L1  DB registry 指针行                          （prompt hash / catalog / bindings / schema digests / workflow revision 指针）
L2  env                                         （仅部署拓扑 + secret 值；禁改 digest/正文）
L3  allowlisted task/execution override         （窄白名单）
L4  Frozen ConfigSnapshot / binding digests     （materialize 一次；in-flight 只读）
```

### 1.3 Scope fence

**S14 负责：**

- 可版本化配置分层、merge 规则、冲突码与一致快照构造时机；  
- 热更新协议：binding-affecting vs ops-only；  
- Task/Execution override 白名单、cap、审计最小字段；  
- Registry 产品操作面：bootstrap 写权、`RegistryPort` 读语义、readiness 挂钩；  
- Prompt identity→path→hash 登记协议、生产三元组 + `aux.*` 命名空间；  
- Model catalog / binding 的 **产品 registry 语义与 bootstrap 写权威**（S11 仅 resolve + invocation 写）；禁浮动 alias；  
- Semantic vs Ops knobs 与 `flag_bundle_digest`；  
- 最小 typed provenance envelope 字段闭集与禁写清单；  
- 配置/Registry 错误轴 `CONFIG_*` / `REGISTRY_*` / `PROMPT_*` …；  
- 安全围栏语义（secret/path/team）与低基数可观测钩子逻辑名；  
- v1 OOS 闭包。

**S14 不负责：**

| 排除项 | 归属 |
|---|---|
| Task/Execution/Process 状态机与 max_retries | D01 / S03 / S02 |
| Inference transport / adapter SDK / 并发闸 | **S11** |
| ANN / PublicationProof / ActiveIndexPointer | **S09** |
| Prompt **正文**字节 SSOT | **D03** `data/prompts/**` |
| Workflow 七表定义 SSOT / 外部 CUD | **S03** / G-13/G-14 |
| Structure/Construction schema **正文** | **contracts** / S06 / S07 |
| 密钥签发/轮换/存放 | **S16** |
| retention 天数 / 告警阈值 / metric 导出实现 | **S15** |
| UI config console / multi-tenant marketplace | **OOS v1** |
| Agent 写 registry | **G-12 deferred** |
| 向量写 / serving CAS / eligibility 产品 map | S08 / S04 |

### 1.4 身份与关键对象

| 对象 | 定义 | 非定义 |
|---|---|---|
| **ConfigSnapshot** | materialize 时一次构造的不可变配置视图；含 digests | 非 mid-flight 可变 bag；非 env 全文 dump |
| **config_snapshot_digest** | L4 材料规范哈希 `H(canonical(L4 materials))`；**必须**产生 | 非可选并列 SSOT |
| **binding_digest** / **command_input_digest** | 域级 digest；**必须嵌入** config_snapshot_digest（或等价材料清单） | 不另立平行业务表 |
| **RegistryPort** | list/get by key+version + readiness probe | 非公网 CRUD API；非 agent write 面 |
| **PromptRef** | `{ identity, content_hash, path? }` | 非 prompt 正文；非 KV key |
| **promptA/B/C** | 生产主链三身份闭集 | 非查询 rewrite；非 embed 身份 |
| **aux.\*** | 非生产辅助模板命名空间 | 不可被 S05–S07 主链 binding |
| **Model identity** | `model_key` + `model_version` | 非浮动 `latest`；非 `display_name` resolve |
| **Adapter binding** | capability → exact model + adapter_kind | 非自动 fallback 列表 |
| **Semantic knob** | 改变行为/过滤/模型路径的配置；进 digest | 非 log level |
| **Ops knob** | 运维旋钮；不进 binding_digest | 非 silent remote SSOT |
| **ProvenanceEnvelope** | 模型产物/invocation 最小可追溯字段 | 非完整 messages 回放包 |

### 1.5 完成定义

1. §2 全部 Truth 被 contracts / ports / bootstrap 实现；  
2. Prompt 运用路径 `H(file)==content_hash`；失败 fail-closed；DB **无** `body_text`；  
3. materialize 后 in-flight **不**重读可变 active 当 SSOT；  
4. 未知 override 键 reject；model/prompt/schema/workflow 身份键不可 Task 覆盖；  
5. 无浮动 model alias 产品层；换默认 = bootstrap 更新 binding → 仅 future；  
6. provenance 最小字段写入关系/CAS；log **非** SSOT；  
7. readiness 在 bootstrap fail / digest drift / hash mismatch 时为 false；  
8. 零 legacy KV 双正文 / console deploy / payload_config 任意 merge 语义依赖；  
9. 实现 **无需** 打开 QNA；  
10. §6 验收矩阵通过。

---

## 2. 真相层

### 2.1 Owner Truth 登记（全局 T-O · S14 段 · 执行摘要）

| Truth-ID | 子类型 | 摘要 | 本域强制 |
|---|---|---|---|
| `T-O-263` | fence / scope | S14 = Config/Prompt/Model Registry 产品域；不吞 S03/S11/D03/S15/S16 | scope |
| `T-O-264` | fence / prompt-ssot | 正文 = git `data/prompts/**`；DB 仅 hash/path；`H(file)==hash` | prompt |
| `T-O-265` | fence / prompt-trinity | 生产闭集 promptA/B/C；S05–S07 只持 PromptRef | prompt |
| `T-O-266` | fence / model-catalog-split | 物理表 D04/S11；S14 产品 registry 语义；code bootstrap 可 | catalog |
| `T-O-267` | fence / no-silent-swap | G-10：禁 silent 换 model/adapter；禁 auto-fallback 平台 | G-10 |
| `T-O-268` | fence / workflow-ssot | Workflow SSOT = S03 七表；S14 只读治理视图 | workflow |
| `T-O-269` | fence / binding-freeze | materialize 后 exact refs 禁热切；只影响 future | freeze |
| `T-O-270` | fence / g12-agent | G-12 deferred：禁 agent 写 registry | OOS |
| `T-O-271` | fence / non-goals | 禁 UI console / marketplace / remote SSOT / DB 正文 / auto-fallback / webhook | non-goals |
| `T-O-272` | fence / provenance-invariant | 产物 ↔ model+prompt+schema+params；log ≠ SSOT | provenance |
| `T-O-273` | fence / schema-digest | schema 正文 contracts；registry 仅 digest 指针 | schema |
| `T-O-274` | fence / evidence | 仅 legacy-family；不继承双正文/硬编码/静默透传 | evidence |
| `T-O-275` | fence / bootstrap | GreenfieldBootstrap 幂等灌入；禁 runtime 远程未钉 SSOT | bootstrap |
| `T-O-276` | fence / config-surfaces | 载体族 git/env/DB/L4；禁 silent remote 作 SSOT | surfaces |
| `T-O-277` | execution / config-layers | L0–L4 分层 + materialize 冻结；L2 仅拓扑+secret | config |
| `T-O-278` | execution / hot-reload | binding-affecting 仅 future；ops-only 可 reload last-good | reload |
| `T-O-279` | execution / override-allowlist | 窄白名单；禁换心；未知键 reject；进 digest+审计 | override |
| `T-O-280` | execution / registry-surface | bootstrap 写；Port 读；外部无 CUD | registry |
| `T-O-281` | execution / knob-digest | Semantic 进 digest；Ops 不进；flag git+digest 默认 OFF | knobs |
| `T-O-282` | execution / provenance-envelope | 最小 typed envelope；禁 secret/正文/messages | provenance |
| `T-O-283` | execution / prompt-namespace | A/B/C + aux.*；仅 A/B/C 主链 binding | namespace |
| `T-O-284` | execution / no-floating-alias | 身份 key+version；路由=bindings；无 latest 产品层 | model-id |
| `T-O-285` | execution / error-taxonomy | typed codes；trust fail-closed；digest≠transient | errors |
| `T-O-286` | execution / security-obs-oos | secret/path/team 围栏；钩子；OOS 闭包 | sec/oos |

### 2.2 域内 Truth 编号（S14-T）

> 域内 `S14-Txxx` 为本文引用别名，**映射**全局 T-O；**不**构成第二编号空间的改写权。变更须显式 reopen 并 append 新 T-O。

#### 2.2.1 Fence 映射（S14-T001..T014 ↔ T-O-263..276）

| ID | 冻结内容 | 来源 | 验收要点 |
|---|---|---|---|
| `S14-T001` | S14 拥有配置/registry/provenance 产品语义；不拥有状态机、transport、ANN、prompt 正文、workflow 七表、密钥/retention 数值。 | T-O-263 | scope architecture |
| `S14-T002` | Prompt 正文唯一载体 = git `data/prompts/**`；`mkb_prompt_hash_pointers` **禁止** `body_text`；运用 `H(file bytes)==content_sha256` 否则 fail-closed。 | T-O-264 | D03/D04 对齐 |
| `S14-T003` | 生产主链三身份闭集 promptA/B/C；命名 `prompt{A\|B\|C}.variant.version`；S05–S07 只绑 PromptRef。 | T-O-265 | D05 对齐 |
| `S14-T004` | catalog/bindings 物理表归 D04；**bootstrap 写权威=S14 RegistryBootstrap**；**runtime resolve=S11-E03 唯一**；S14 产品 registry 语义与 digest 一致性；禁口头 config 唯一目录。 | T-O-266 | dual ownership matrix |
| `S14-T005` | 禁止 silent 换 model_key/adapter_kind/dimension；registry/override **不得**提供失败即换模型默认路径。 | T-O-267 | G-10 |
| `S14-T006` | Workflow 定义 SSOT = S03 七表；S14 可暴露只读 version/digest 视图；禁第二 workflow JSON truth / 外部 CUD。 | T-O-268 | G-13/G-14 |
| `S14-T007` | materialize 后 exact schema/profile/model/prompt refs 与 digests 在 retry/recovery/resume 中 **禁止热切 active**；更新只影响 future resolve。 | T-O-269 | freeze |
| `S14-T008` | G-12 deferred：v1 **无** agent 写 registry 生产路径。 | T-O-270 | OOS |
| `S14-T009` | 非目标：UI console、marketplace、silent remote config SSOT、DB 正文第二真相、auto-fallback 平台、webhook 配置推送。 | T-O-271 | non-goals |
| `S14-T010` | 每个模型产物可追溯 model+prompt+schema+params 版本；provenance **不得**仅存日志；log ≠ 业务 SSOT。 | T-O-272 | provenance |
| `S14-T011` | schema 正文在 `src/contracts/**`；registry 仅 schema_key+version+content_digest；同 version 异 digest → fail-loud。 | T-O-273 | schema |
| `S14-T012` | 唯一 legacy 证据树 = `context/legacy-family/`；不继承 N-01..N-12 反模式。 | T-O-274 | evidence |
| `S14-T013` | v1 registry 以 code-owned / migration **GreenfieldBootstrap** 幂等灌入；禁 runtime 从远程市场/legacy 拉未钉版本定义作 SSOT。 | T-O-275 | bootstrap |
| `S14-T014` | 配置载体族闭集：git config、env/secret、DB registry、L4 frozen snapshot；禁 silent remote/UI marketplace 作 SSOT。 | T-O-276 | surfaces |

#### 2.2.2 Execution 映射（S14-T015..T024 ↔ T-O-277..286）

| ID | 冻结内容 | 来源 | 验收要点 |
|---|---|---|---|
| `S14-T015` | 配置分层 L0→L1→L2→L3→L4；L2 **仅**部署拓扑+secret 值；**禁止** env 改写 prompt 正文 / model definition_digest / schema digest / workflow revision；L4 于 **Execution 创建** `resolve_for_new_execution` **一次**构造并冻结 binding digests（含 PromptRef/model/schema/knobs）；**Process materialize 只读** Execution/L4 快照，**禁止**再 merge L0–L3；scatter 子 Execution **各自** resolve 一次；in-flight **只读** L4。 | T-O-277 | E02 |
| `S14-T016` | Binding-affecting 变更仅影响尚未 materialize 的 future resolve；**禁止** in-flight 重 resolve。Ops-only 白名单可进程 reload；失败 → last-good ops + `CONFIG_OPS_RELOAD_FAIL`；**semantic 永不** availability-over-consistency。Prompt 文件变更必须更新指针且 `H(file)==hash`；禁无指针 inotify 直读新正文。 | T-O-278 | E03 |
| `S14-T017` | Override 窄白名单；未知键 `CONFIG_OVERRIDE_REJECTED`。禁止覆盖 model/prompt/schema/adapter/dimension/workflow 身份与 secret/绝对 path/未注册 flag。有条件允许：已注册 `profile_id`、cap 内 `batch_size`/`top_k`/`pack_budget`、非语义 `dry_run`/`debug_trace`。覆盖进 digest。**成功 allowlisted override → 唯一写 `mkb_domain_events` `config.override_applied`（aggregate=ops）**；**安全/越权拒绝 → 唯一写 `mkb_security_audit_events`**（S16 action 闭集）；**禁止**「和/或」双选或 log-only。审计字段 `override_keys[]`/`override_digest`/`actor_origin`/`team_uuid`/`task_uuid|execution_uuid`/时间戳 → payload_json（见 OverrideAuditPayload）。 | T-O-279 | E04 |
| `S14-T018` | **catalog/binding bootstrap 写权威 = S14 RegistryBootstrap/migration 幂等**（默认行内容协作 S11 必须清单）；读 = RegistryPort list/get + readiness；**runtime resolve 不归 S14**（S11-E03）。v1 **外部 HTTP registry list = OOS**（不进入 S16 EndpointClass；禁隐式 HTTP CUD/list）。Workflow 只读 S03；无 agent 写；无远程市场扫描作 SSOT。 | T-O-280 | E05 |
| `S14-T019` | Semantic knobs **进入** binding_digest；Ops knobs **不进**；Capacity caps **生效值**进 digest，超 cap reject。Feature-flag：`data/config/feature_flags.yaml`（或等价）+ `flag_bundle_digest`；默认 OFF；禁远程 flag SSOT；禁 flag 触发 auto model fallback。 | T-O-281 | E06 |
| `S14-T020` | Provenance 最小字段：model_key+version、adapter_kind、capability_key；prompt_identity+content_hash（若适用）；schema_key+version+content_digest（structured）；params_profile_id+params_digest；config_snapshot_digest（嵌入 domain binding_digest）；workflow_revision_uuid+compiled_digest（若经 Workflow）；team/task/execution/process（有则填）；推荐 definition_digest。**禁止** secret、prompt 正文、完整 messages、向量全文、绝对 path、预签名 URL。OTel 仅导出映射。 | T-O-282 | E07 |
| `S14-T021` | 生产 `prompt{A\|B\|C}.variant.version`；辅助 `aux.<domain>.<name>.version`；均可进指针表；**仅** A/B/C 可被 S05–S07 主链 binding。禁裸字符串静默透传；禁 production 浮动 alias 作 durable binding 身份。 | T-O-283 | E08 |
| `S14-T022` | v1 **无**浮动 latest/@champion 产品解析层；身份 = model_key+version；路由 = adapter_bindings；display_name 不进 resolve；Index「alias/revision」中 revision=model_version。换默认 = bootstrap 更新 binding → 仅 future。独立 alias 表仅显式 reopen。 | T-O-284 | E09 |
| `S14-T023` | 错误码闭集见 §4.10；trust 路径 fail-closed；digest/hash mismatch **不得**标 transient/429；对外可 RFC 9457 + `error_code`。 | T-O-285 | E10 |
| `S14-T024` | secret 永不进 git config / 非 secret 列 / envelope / 诊断明文；path 仅 repo 相对 `data/prompts/**`/`data/config/**`，禁 `..`；`team_uuid` 不是授权凭证；低基数钩子；OOS 闭包见 §4.11。 | T-O-286 | E11 |

#### 2.2.3 派生执行 Truth（S14-T025..T055 · 可编码细则）

| ID | 冻结内容 | 来源 |
|---|---|---|
| `S14-T025` | L0 默认布局（v1）：`data/config/defaults.yaml`（或拆分 profiles）、`data/config/feature_flags.yaml`、`data/config/profiles/**`（可选）；**code registry** 登记合法 `profile_id` 闭集；git 模板必须与 code 注册一致，否则 bootstrap/readiness fail。 | T-O-277 residual |
| `S14-T026` | L1 指针材料：`mkb_prompt_hash_pointers`、`mkb_model_catalog`、`mkb_adapter_bindings`；**schema digests 物理 SSOT = D04 `mkb_structure_schema_definitions` / `mkb_construction_schema_definitions`（S06/S07 写定义）**；S03 workflow revision 指针（只读）。**S14 禁止**新建 schema digest 专用表。同 version 异 digest → `REGISTRY_DIGEST_MISMATCH` / readiness false。 | T-O-277/273 |
| `S14-T027` | L2 允许键族（示例闭集意图）：`MKB_VLLM_BASE_URL`、`MKB_OBJECT_ROOT`、`MKB_DATA_ROOT`、secret ref 解析结果；**禁止** `PROMPT_BODY_*`、`MODEL_DEFINITION_DIGEST_*`、`SCHEMA_DIGEST_*`、`WORKFLOW_REVISION_*` 经 env 覆盖。 | T-O-277 Δ1 |
| `S14-T028` | L4 材料最小集合：resolved PromptRef(s)、model_key/version/adapter_kind/capability、schema digests（若适用）、params_profile_id+params_digest、semantic knobs 生效值、flag_bundle_digest、override_digest（若有）、workflow_revision_uuid+compiled_digest（若经 Workflow）。 | T-O-277/282 |
| `S14-T029` | Binding-affecting 键类：prompt hash/identity、model/version、schema digest、semantic threshold/profile、改变行为的 feature flag、params 影响生成语义的字段。 | T-O-278/281 |
| `S14-T030` | Ops-only 键类（默认）：log level、metric export、**域声明不改语义** HTTP 超时、S15 scrape interval；**强制** `security.*` 与 `obs.*` 前缀 = **Ops-only / 不进 binding_digest / 不可 Task override**（默认值与语义归 S16/S15，**分类标签归 S14**）。未知**无登记前缀**键默认 Semantic（fail-safe）；**禁止**将未登记 `security.*`/`obs.*` 落入 Semantic。 | T-O-278/281 |
| `S14-T031` | Override **禁止**键闭集：`model_key`、`model_version`、`adapter_kind`、`prompt_identity`、`prompt_content_hash`、`schema_key`、`schema_version`、`schema_content_digest`、embedding `dimension`、`workflow_key`、`workflow_revision`、任意 secret、绝对 path、未注册 feature flag、跨 capability 换 binding、automatic fallback 列表。 | T-O-279 |
| `S14-T032` | Override **有条件允许**键闭集（v1）：`profile_id`（∈ code registry）、`batch_size`、`top_k`/`return_k`/`recall_k`（≤ 域 max 与 S09 `max_topk`）、`pack_budget`/`pack_max_hits`/`pack_max_chars`（≤ 域 max）、`dry_run`、`debug_trace`（若域支持且不改 generation 语义身份）。 | T-O-279 |
| `S14-T033` | RegistryPort 逻辑操作：`get_prompt_pointer`、`list_prompt_pointers`、`get_model`、`list_models`、`get_binding`、`list_bindings`、`get_schema_digest`（**读 façade**：S06/S07/D04 definition 表 digest，非第二 store）、`get_workflow_revision_view`（只读 S03）、`probe_readiness()`（实现 `registry_bootstrap` 组件谓词）、`resolve_for_new_execution(ctx)→ConfigSnapshot`。 | T-O-280 |
| `S14-T034` | **禁止** RegistryPort：`create/update/delete` 公网语义；runtime upsert prompt body；agent mutate catalog；scan remote marketplace as SSOT。 | T-O-280/270/271 |
| `S14-T035` | Bootstrap 幂等：empty-DB 或 migration 后同 digest 重跑不产生冲突行；冲突（同 version 异 digest）→ `BOOTSTRAP_FAIL` + readiness false。 | T-O-275/280 |
| `S14-T036` | Semantic vs Ops 默认归类表见 §4.6/§4.12；`security.*`/`obs.*` 强制 Ops-only；其他未知键 → Semantic（进入 digest 或 reject 若不可解析）。 | T-O-281 |
| `S14-T037` | `flag_bundle_digest` = 规范化 feature_flags 文件字节 hash；materialize 时钉入 L4；默认全部 flag OFF。 | T-O-281 |
| `S14-T038` | Provenance 必填矩阵：见 §4.7（embed / structured_generate / text_generate / rerank 分型）。 | T-O-282 |
| `S14-T039` | Prompt 路径约定：A=`data/prompts/intake/clean/<variant>.<version>.*`；B=`data/prompts/lsrag/structure/...`；C=`data/prompts/lsrag/construct/...`；aux=`data/prompts/aux/<domain>/...`。 | T-O-283；D05 |
| `S14-T040` | PromptRefV1 逻辑类型：`{ identity, content_hash, path? }`；`content_hash` 形式 `sha256:…` 或与 D04 `content_sha256` 对齐的规范编码。 | T-O-264/283；D05 |
| `S14-T041` | S05 仅可绑 `promptA.*`；S06 仅 `promptB.*`；S07 仅 `promptC.*`（metadata_refresh 显式空 promptC 的 S07 规则保留）；CI/architecture 测试必须阻止 aux 误绑主链。 | T-O-283；D05 |
| `S14-T042` | **非规范性完整解析序**：runtime binding resolve **见 S11-E03 唯一权威**。S14 仅冻结：`resolve_for_new_execution` 将 **exact model_key+version+adapter_kind+capability** 钉入 L4/ConfigSnapshot；**禁止**在 S14 另写完整 enabled→priority 步骤。 | T-O-284；S11-E03 |
| `S14-T043` | `display_name` / 文档别名 **不**参与 resolve；禁止 durable binding 使用字符串 `latest` / `@champion` / `@production` 作为 model_version。 | T-O-284 |
| `S14-T044` | 错误码闭集（完整）：`CONFIG_MISSING`、`CONFIG_CONFLICT`、`CONFIG_OVERRIDE_REJECTED`、`REGISTRY_NOT_FOUND`、`REGISTRY_DIGEST_MISMATCH`、`PROMPT_NOT_REGISTERED`、`PROMPT_HASH_MISMATCH`、`SCHEMA_DIGEST_MISMATCH`、`MODEL_DISABLED`、`BINDING_NOT_FOUND`、`SNAPSHOT_INCONSISTENT`、`BOOTSTRAP_FAIL`、`CONFIG_OPS_RELOAD_FAIL`。 | T-O-285 |
| `S14-T045` | 非 S14 错误：transport 429/超时 → S11；业务 CAS → S03/S12；auth → S16。 | T-O-285 |
| `S14-T046` | **`registry_bootstrap` 组件（谓词权威=S14）** false 条件（任一）：`BOOTSTRAP_FAIL`；required prompt 指针缺失；bootstrap 校验集 `PROMPT_HASH_MISMATCH`；catalog **行**缺失或同 version 异 digest；schema digest 与 contracts/D04 definition 不一致。**不含** transport 可探（归 `inference_binding`/S11）。binding「存在 enabled 行」若影响 catalog 完整性可由 S14 报缺行；transport/local 可探 **仅** S11。 | T-O-285/275 |
| `S14-T047` | Readiness 与业务：readiness=false 时 **禁止** 接受依赖 registry 的新 Execution materialize；已 in-flight 的 L4 快照继续按冻结执行（不重 resolve）。 | T-O-269/278 |
| `S14-T048` | 安全：secret 永不进入 `data/config/**`、`mkb_*` 非 secret 列、ProvenanceEnvelope、诊断明文；prompt 文件仅模板。 | T-O-286 |
| `S14-T049` | path fence：仅允许 repo 相对 `data/prompts/**`、`data/config/**`；规范化后禁 `..` 与绝对 path。 | T-O-286 |
| `S14-T050` | `team_uuid` **不是**授权凭证；Registry resolve 仍须上游 token 鉴权（S16）。 | T-O-286；OD-04 |
| `S14-T051` | **逻辑钩子→S15 导出名（强制映射，architecture 禁未映射名）**：`registry_resolve_total`→`mkb_registry_resolve_total{result}`；`prompt_hash_mismatch_total`→`mkb_prompt_hash_mismatch_total`；`bootstrap_fail_total`→`mkb_registry_bootstrap_fail_total`；`override_rejected_total`→`mkb_config_override_rejected_total`；`config_ops_reload_total{result}`→`mkb_config_ops_reload_total{result}`（reload fail 用 result=fail，**metric+event only，默认不 page**）。事件（须 D04/S15 登记）：`registry.bootstrap_completed`、`registry.digest_mismatch`、`config.ops_reload`、`config.override_applied`（无 secret/正文）。导出实现归 S15。 | T-O-286 |
| `S14-T052` | **禁止** log 存在性定义 registry/bootstrap 业务成功。 | T-O-272/286 |
| `S14-T053` | v1 OOS 闭包：见 §4.11 完整列表。 | T-O-286 |
| `S14-T054` | contracts 落点建议：`src/contracts/registry/`（ConfigSnapshot、PromptRef、ProvenanceEnvelope、RegistryError、OverrideSpec）；与 D03 contracts 纪律一致。 | D03；T-O-280 |
| `S14-T055` | 实现无需打开 QNA；本文为唯一执行 SSOT。 | SSOT |
| `S14-T056` | **所有权矩阵（catalog/binding）**：bootstrap 写=S14；runtime resolve=S11-E03；status/enabled 变更=S14 ops/bootstrap；S14 复述不得并行改 resolve 算法。 | T-O-266/280 |
| `S14-T057` | **config_snapshot_digest 封缄**：L4 **必须**计算 `config_snapshot_digest = H(canonical(L4 materials))`；各域 `*_binding_digest` / `command_input_digest` **必须嵌入**该 digest（或等价材料清单 hash）；**禁止**「或 merge 或独立」二选一悬空；验证伪代码见 §4.2。 | T-O-277/282 |
| `S14-T058` | **params profile v1**：identity 命名空间 `params.<capability>.<name>`；存储=`data/config/profiles/**` 或 code defaults；空 profile → 常量 `params_digest=sha256:empty_profile_v1`；进入 params_digest 的 knobs = 影响生成语义的参数；纯 ops 超时不进。 | T-O-282 |
| `S14-T059` | **v1 profile_id 闭集（override 用）**：`clean.web.v1`、`clean.document.v1`、`clean.default.v1`；未登记 profile_id → `CONFIG_OVERRIDE_REJECTED`。S05 默认 profile 须与此闭集对齐或显式子集。 | T-O-279 |
| `S14-T060` | **Render-time prompt**：in-flight 仅读 L4 PromptRef path+hash；使用时 **重读文件** 校验 `H(file)==hash`；缺失/不匹配 → `PROMPT_HASH_MISMATCH` fail-closed **non-transient**；retries **复用同一 L4**（禁 silent 换 active）。 | T-O-264/269 |
| `S14-T061` | **Provenance 落表映射**：见 §4.7 矩阵；SSOT 优先 Execution/Process digest 列与 generation 附属；`mkb_inference_invocations` 仅 model 身份+request_digest+usage；额外 digest 仅允许 `payload_extra` **闭集键**（`prompt_content_hash`,`schema_content_digest`,`params_digest`,`config_snapshot_digest`）；**禁止** log/OTel 当唯一 provenance。 | T-O-282 |
| `S14-T062` | **OverrideAuditPayload v1**（domain_events.payload_json）：`override_keys[]`、`override_digest`、`actor_origin`、`team_uuid`、`task_uuid?`、`execution_uuid?`、`result`∈applied\|rejected、`error_code?`；禁 values/secrets。拒绝且属越权/未登记 → 另写 security_audit（S16）。 | T-O-279 |

### 2.3 继承上游（不重开）

- **D03**：`data/prompts/**` git 正文；`data/config/**` 非秘密；`T-O-146/155/159`。  
- **D04**：`mkb_prompt_hash_pointers`（禁 body_text）、`mkb_model_catalog`、`mkb_adapter_bindings`、`mkb_inference_invocations`；55 表闭集。  
- **D05**：promptA/B/C 三元组；PromptRefV1；路径约定；`T-O-208/210`。  
- **S03**：七表 workflow SSOT；compiled digest 派生；binding freeze；外部仅 list/get。  
- **S05/S06/S07**：PromptRef / schema digest / command_input_digest / s05_binding_digest；retry 不热切。  
- **S11**：Inference≠Adapter；binding 解析序；G-10；code-owned catalog bootstrap 协作。  
- **S08/S09/S10**：域默认 knobs（threshold/topk 等）；S14 管版本化与 digest 参与，不改产品默认定义权。  
- **G-10 / G-12 / G-13 / G-14**：closed/deferred 状态继承。  
- **OD-01 / OD-04**：leaf-worker 无平台 UI；team_uuid 非授权凭证。

### 2.4 所有权分账总表（S14 owns vs consumes）

| 主题 | S14 owns | S14 consumes | 禁止 |
|---|---|---|---|
| Prompt 正文 bytes | — | D03 git 树 | DB 第二正文 |
| Prompt 指针/校验协议 | **是** | D04 表 | 无 hash 直读 |
| Prompt 产品身份 A/B/C | 登记/闭集执行 | D05 定义 | 第四生产身份 |
| Model catalog DDL | — | D04 | 私自增表 |
| Model catalog 产品语义 | **是**（status/digest 一致性） | S11 解析协作 | 口头唯一目录 |
| Binding 解析 runtime | 产品规则复述 | **S11-E03 权威** | silent swap |
| Workflow 定义 | 只读视图 | **S03 七表** | 第二 SSOT |
| Schema 正文 | — | contracts/S06/S07 | registry 存 shape 正文 |
| Config 分层/snapshot | **是** | 各域 knobs 默认 | mid-flight 重 resolve |
| Override 白名单 | **是** | S02 payload schema 交叉 | 任意 merge |
| Provenance 字段 | **是**（逻辑 envelope） | S11 invocation / S06–S07 generation 落表 | log-as-SSOT |
| Transport 错误 | — | S11 | 把 digest mismatch 当 429 |
| Secrets | 围栏语义 | **S16 生命周期** | secret 进 git |
| Metrics export | 逻辑名 | **S15 导出** | 高基数标签 |

---

## 3. 总体方案陈述

1. **分层配置 + 一次冻结**：L0–L3 只在 **Execution 创建 resolve** 时解析；L4 是该次 Execution（及下属 Process）的唯一配置权威。  
2. **Git 正文 + Hash 指针双围栏**：正文不可漂移第二真相；指针与文件必须同 hash。  
3. **Registry 是产品目录而非运行时市场**：bootstrap 写、Port 读、无 UI/agent/remote SSOT。  
4. **Binding freeze 高于热更新**：运维可变未来默认；不可偷换 inflight 语义。  
5. **窄 override 白名单**：可用性不靠任意 JSON merge；换心走 registry/bootstrap/workflow revision。  
6. **Semantic 进 digest / Ops 可热更**：复现实验不被 log level 抖动污染。  
7. **无浮动 alias**：exact key+version + binding 路由；G-10 可验收。  
8. **Provenance 进关系/CAS**：model+prompt+schema+params 可对账；OTel 仅导出。  
9. **Typed 错误与 readiness**：trust 路径 fail-closed；digest 问题非 transient。  
10. **QNA 零依赖**：全部执行细节在本文 §4。

---

## 4. 具体执行方案清单

### 4.1 `S14-E01` — 范围、非目标与邻域分账

**真相**：S14-T001/T008/T009/T053；T-O-263/270/271/286

| 项 | 规范 |
|---|---|
| 域身份 | F2 / S14 Config, Prompt & Model Registry |
| 代码落点（建议） | `src/services/registry/` 或 `src/registry/`；`src/contracts/registry/` |
| 公共 surface | 内部 Port 为主；**v1 外部 HTTP list = OOS** |
| 非能力 | 不是 Process capability；不创建 Task/Execution |
| 硬非目标 | UI console、marketplace、remote config SSOT、DB prompt body、auto-fallback 平台、webhook 配置推送、agent 写 registry |

**执行台账**

1. 目录与 architecture 测试：services 不得直读未校验 prompt 文件绕过 Port。  
2. 依赖方向：S05–S10/S11 → RegistryPort；**禁止** adapters 反向拥有 catalog SSOT。  
3. 分账表（§2.4）进入 architecture 文档与 code comments 的允许依赖列表。

**小结**：S14 是治理门面，不是第二 workflow/inference 引擎。

---

### 4.2 `S14-E02` — 配置分层 L0–L4 与 ConfigSnapshot

**真相**：S14-T014/T015/T025..T028；T-O-276/277

**分层规范**

| 层 | 来源 | 内容 | 规则 |
|---|---|---|---|
| **L0** | git `data/config/**` + code defaults | 非秘密语义默认、profiles、feature_flags | 必须可 git 审计 |
| **L1** | DB registry 指针 | prompt hash、catalog、bindings、schema digests、workflow revision 指针 | 同 version 异 digest → fail-loud |
| **L2** | env + secret 解析（S16） | **仅**部署拓扑（如 `vllm.base_url`、路径根）+ secret **值** | **禁止**改写 prompt 正文、definition_digest、schema digest、workflow revision |
| **L3** | Task/Execution allowlisted override | §4.4 白名单 | 未知键 reject |
| **L4** | Frozen snapshot | materialize 产物 | in-flight **只读** |

**构造时机（必须 · S14-T015/T057）**

```text
trigger: Execution 创建 → resolve_for_new_execution（唯一 materialize 点）
  scatter: 每个子 Execution 各自 resolve 一次
steps:
  1. load L0 defaults + profile template
  2. load L1 pointers (fail if missing required)
  3. apply L2 topology/secrets (reject if L2 attempts digest rewrite)
  4. apply L3 overrides (allowlist)
  5. validate hash/digests (prompt files, schema, catalog)
  6. seal L4 + ALWAYS compute config_snapshot_digest = H(canonical(L4 materials))
  7. domain *_binding_digest / command_input_digest MUST include config_snapshot_digest
     (or hash the same enumerated L4 materials checklist)
  8. persist freeze materials on Execution; ProcessCommand materialize READS L4 only
Process materialize:
  - READ Execution/L4 snapshot only
  - FORBIDDEN: re-merge L0/L1/L2/L3 or re-resolve bindings
in_flight:
  - read L4 only; re-read prompt file under frozen path+hash (S14-T060)
  - FORBIDDEN: re-merge L0/L1/L2/L3 as SSOT
verify(digest, materials):
  assert H(canonical(materials)) == config_snapshot_digest
  assert domain_binding_digest embeds config_snapshot_digest
```

**Workflow 特例**：`workflow_revision_uuid` / `compiled_digest` **只读自 S03 七表**；S14 **不** merge 第二 workflow JSON。

**冲突**

| 条件 | 错误 |
|---|---|
| 必选 profile/key 缺失 | `CONFIG_MISSING` |
| 多层同键类型/值不兼容 | `CONFIG_CONFLICT` |
| L4 材料不自洽 | `SNAPSHOT_INCONSISTENT` |
| 同 version 异 digest | `REGISTRY_DIGEST_MISMATCH` |

**小结**：可复现性来自 L4 封印，不是运行时「当前最新配置」。

---

### 4.3 `S14-E03` — 热更新协议（binding vs ops）

**真相**：S14-T007/T016/T029/T030/T047；T-O-278/269

| 变更类 | 例 | 生效范围 | 失败语义 |
|---|---|---|---|
| **Binding-affecting** | prompt hash、model/version、schema digest、semantic threshold/profile、语义 feature flag | **仅 future** materialize | 不得 in-flight 重 resolve；trust 路径 fail-closed |
| **Ops-only** | log level、metric export、声明非语义超时 | 进程信号 / 显式 admin hook reload | last-good ops 视图 + `CONFIG_OPS_RELOAD_FAIL` 告警；**不**改 binding |

**强制规则**

1. **禁止** contexter 式 TTL 热缓存偷换业务 prompt。  
2. Prompt **文件**变更：必须更新 `mkb_prompt_hash_pointers` 且校验 `H(file)==hash`；**禁止**无指针更新的 inotify 直读新正文当 SSOT。  
3. Semantic **永不**采用 availability-over-consistency（不得为了可用性而返回漂移语义配置）。  
4. 已 materialize Execution 在 retry/recovery/human resume 中继续使用冻结 digests（S05-T025 / S06 / S07 继承）。

**小结**：热更新存在，但不得破坏 binding freeze。

---

### 4.4 `S14-E04` — Override 白名单与审计

**真相**：S14-T017/T031/T032；T-O-279/267

**禁止覆盖（闭集）**

```text
model_key, model_version, adapter_kind,
prompt_identity, prompt_content_hash,
schema_key, schema_version, schema_content_digest,
dimension, workflow_key, workflow_revision,
*secret*, absolute paths, unregistered feature flags,
cross-capability binding swap, automatic fallback lists
```

**有条件允许（v1）**

| 键 | 条件 |
|---|---|
| `profile_id` | ∈ code registry 闭集 + git 模板存在 |
| `batch_size` | 1..domain_max |
| `top_k` / `return_k` / `recall_k` | 域规则 + ≤ S09 `max_topk`（若适用） |
| `pack_budget` / `pack_max_hits` / `pack_max_chars` | ≤ 域 max |
| `dry_run` / `debug_trace` | 若域支持；不得改变 generation 语义身份 |

**算法**

```text
for each key in request.overrides:
  if key not in allowlist → CONFIG_OVERRIDE_REJECTED
  if key in forbidlist → CONFIG_OVERRIDE_REJECTED
  if numeric and > cap → CONFIG_OVERRIDE_REJECTED
apply → include values in L4 digest materials
emit audit: override_keys[], override_digest, actor_origin, team_uuid,
            task_uuid|execution_uuid, timestamp
```

**审计落点（单一权威 · 禁止和/或）**

| 结果类 | 唯一落点 | type/action | 写入方 |
|---|---|---|---|
| 允许的 override 已应用 | **`mkb_domain_events`** | `event_type=config.override_applied`（aggregate=`ops`；须 D04 登记） | 业务/S14 经 DomainEventWriter 同 TX |
| override 拒绝（未知键/越权/secret/path） | **`mkb_security_audit_events`** | action∈`config.override_denied`（S16 action 闭集）；denial_code=`CONFIG_OVERRIDE_REJECTED` 或 `SEC_*` | S16 SecurityAuditWriter 语义；S14 触发 |
| bootstrap 成功/digest mismatch / ops reload | **`mkb_domain_events`** | `registry.bootstrap_completed` / `registry.digest_mismatch` / `config.ops_reload` | S14 via DomainEventWriter |

**禁止**：实现任选一表；双写作 SSOT；仅 metric/log 冒充审计。Payload 见 S14-T062。

**小结**：可用性靠 cap 内旋钮，不靠 Task 换心。

---

### 4.5 `S14-E05` — Registry 写/读面与 GreenfieldBootstrap

**真相**：S14-T013/T018/T033..T035；T-O-280/275/268

**写权威分账（单一 writer · 与 S11 双向）**

| 对象 | **bootstrap 写权威** | **运行时解析权威** | **status/enabled 运维** | 禁止 |
|---|---|---|---|---|
| `data/prompts/**` 正文 | git commit | S14 hash 校验 | n/a | DB body |
| `mkb_prompt_hash_pointers` | **S14** bootstrap/migration | S14 get_prompt_pointer | S14 bootstrap | 无审计 runtime upsert |
| `mkb_model_catalog` | **S14 RegistryBootstrap**（内容清单协作 S11） | **S11-E03 resolve**（只读行） | S14 bootstrap/ops | S11 平行 INSERT；口头目录 |
| `mkb_adapter_bindings` | **S14 RegistryBootstrap** | **S11-E03 resolve** 唯一算法 | S14 bootstrap/ops | S14 另立解析序；公网 CUD |
| schema digests | **S06/S07** 写 definition 表 | S14 `get_schema_digest` 读 façade | S06/S07 | S14 新建指针表 |
| Workflow revision | S03 七表 | S14 只读视图 | S03 | 第二 workflow SSOT |
| `mkb_inference_invocations` | **S11** | n/a | n/a | S14 写 invocation |
| Agent 写 registry | — | — | — | v1 不存在 |

**Bootstrap 最小灌入（写路径 = S14；必须行内容 = S11-E03 清单）**

| 表/树 | 必须 |
|---|---|
| `mkb_prompt_hash_pointers` | promptA/B/C 默认 variant + 生产 aux 指针 |
| `mkb_model_catalog` | embed/rerank/local-json-generator 等 + definition_digest |
| `mkb_adapter_bindings` | 每 required capability ≥1 enabled `local_vllm` |
| schema digests | **消费** S06/S07/D04 definition 行；不另建表 |
| feature_flags | 默认 OFF bundle |

**冲突/readiness**：digest 冲突 / 缺行 → `BOOTSTRAP_FAIL` 或 `REGISTRY_DIGEST_MISMATCH` + **`registry_bootstrap` false（S14 probe）**；transport 不可探 → **`inference_binding` false（S11 probe）**。

**RegistryPort（逻辑 API）** — 见 S14-T033；**v1 不暴露**外部 HTTP list（OOS；S01 若未来暴露须 reopen 并入 S16 EndpointClass=Operator+token）。

**小结**：单一写模块 S14 RegistryBootstrap；S11 只消费 Port + resolve。

---

### 4.6 `S14-E06` — Semantic / Ops knobs 与 feature flags

**真相**：S14-T019/T030/T036/T037；T-O-281/272

**默认归类表（v1）**

| 类别 | 例 | 进 binding_digest？ | 热更 |
|---|---|---|---|
| **Semantic** | score threshold 策略、pack 预算、schema/profile id、prompt/model refs、plan_mode、thinkingBudget、改变过滤/模型行为的 flag | **是** | 仅 future |
| **Ops** | log level、metric export、声明非语义超时、S15 scrape interval、**`security.*`**、**`obs.*`** | **否** | 可进程 reload（secret/token 生命周期仍归 S16） |
| **Capacity caps** | max_topk、max batch、object size cap | **是（生效值）** | 仅 future；超 cap reject |

**Feature-flag 规则**

1. 定义于 git `data/config/feature_flags.yaml`（或等价）+ `flag_bundle_digest`。  
2. 默认 **OFF**（fail-safe）。  
3. 生产开启须显式 profile/bootstrap，不得靠远程未钉版本服务。  
4. **禁止** flag 触发 automatic model fallback（G-10）。  
5. **禁止** 用 flag 承载静态长寿配置（DB URL 等）——此类归 L0/L2 正规配置。

**未知键**：无登记前缀 → Semantic；若无法解析类型 → `CONFIG_CONFLICT` 或 `CONFIG_MISSING`（实现选 fail-closed 之一并固定）。**`security.*` / `obs.*` 前缀永不落入 Semantic**（即使未知子键：按 Ops 忽略进 digest，或 reject 未知 ops 子键——实现固定为 **reject 未登记子键** 更严）。

**小结**：digest 只对行为路径过敏，不对运维噪声过敏。

---

### 4.7 `S14-E07` — Provenance envelope 必填矩阵

**真相**：S14-T010/T020/T038；T-O-282/272

**逻辑字段闭集**

| 字段 | embed | rerank | structured_generate | text_generate | 说明 |
|---|---|---|---|---|---|
| `model_key`+`model_version` | 必 | 必 | 必 | 必 | catalog 身份 |
| `adapter_kind` | 必 | 必 | 必 | 必 | G-10 审计 |
| `capability_key` | 必 | 必 | 必 | 必 | |
| `prompt_identity`+`prompt_content_hash` | 否* | 否* | 必（若用 prompt） | 必（若用 prompt） | *辅助 aux 若用则填 |
| `schema_key`+`version`+`content_digest` | 否 | 否 | 必 | 否 | contracts |
| `params_profile_id`+`params_digest` | 必 | 必 | 必 | 必 | 见 S14-T058；空=`sha256:empty_profile_v1` |
| `config_snapshot_digest` | 必 | 必 | 必 | 必 | L4 封缄；域 binding_digest **嵌入**之 |
| `workflow_revision_uuid`+`compiled_digest` | 若经 WF | 若经 WF | 若经 WF | 若经 WF | 只读 S03 |
| `team/task/execution/process_uuid` | 有则填 | 有则填 | 有则填 | 有则填 | |
| `definition_digest`（model） | 推荐 | 推荐 | 推荐 | 推荐 | |

\* 查询侧 aux prompt（如 rewrite）若触发模型调用，必须带 PromptRef hashes。

**禁止写入 envelope**

```text
secret values, prompt body, full messages[], vector full text,
absolute filesystem paths, presigned URLs
```

**落表映射矩阵（S14-T061 · 禁止 log-only）**

| Provenance 字段 | 物理落点（SSOT） | 导出/附属 |
|---|---|---|
| model_key/version/adapter_kind | `mkb_inference_invocations` 一等列 + L4/Execution binding | OTel model 属性 |
| request_digest / usage / latency | invocations 一等列 | metric |
| prompt_identity + content_hash | Execution/Process `*_binding_digest` 材料 / generation 附属；**非** invocations 必列 | 可选 `payload_extra.prompt_content_hash` |
| schema_* digests | S06/S07 generation / command_input_digest | 可选 `payload_extra.schema_content_digest` |
| params_profile_id + params_digest | L4 + domain binding digest 材料 | 可选 `payload_extra.params_digest` |
| config_snapshot_digest | L4 封缄；**嵌入** domain `*_binding_digest` / `command_input_digest` | 可选 `payload_extra.config_snapshot_digest` |
| workflow digests | S03 revision + Execution binding | — |
| team/task/execution/process | 业务表一等列 | events 关联 |

**payload_extra 允许 digest 键闭集**：`prompt_content_hash`、`schema_content_digest`、`params_digest`、`config_snapshot_digest`。其他键须 change-request。

**导出**：可映射 OTel GenAI；**关系/CAS 为 SSOT**。诊断 content capture **默认 OFF**。

**小结**：复现四元组强制、内容回放默认拒绝、落表可编码。

---

### 4.8 `S14-E08` — Prompt 命名空间与 hash 校验

**真相**：S14-T002/T003/T021/T039..T041；T-O-264/265/283

**命名**

| 空间 | 模式 | 主链可绑？ | 路径 |
|---|---|---|---|
| 生产 | `prompt{A\|B\|C}.variant.version` | 是（按域） | D05 约定目录 |
| 辅助 | `aux.<domain>.<name>.version` | **否**（S05–S07） | `data/prompts/aux/...` |

**校验管道（运用路径必须）**

```text
1. identity ∈ registered set (pointer table)
2. load git_relative_path under data/prompts/**
3. compute H(file bytes)
4. H == content_sha256 / content_hash else PROMPT_HASH_MISMATCH
5. render template → pass bytes/hash to S11 (S11 再校验 key+hash)
In-flight (S14-T060): re-read file under L4 path+hash only; missing/mismatch → PROMPT_HASH_MISMATCH non-transient;
retries reuse same L4 (no silent active swap); readiness probe of required prompt set is separate
FORBIDDEN: unregistered identity silent pass-through as raw key
FORBIDDEN: production floating alias as durable binding identity
FORBIDDEN: DB body_text column
```

**默认 bootstrap identities（示例，可扩展 variant）**

| identity | 角色 |
|---|---|
| `promptA.default.v1` / `promptA.web.v1` / `promptA.document.v1` | Clean |
| `promptB.default.v1` | Structurizer |
| `promptC.default.v1` | Summarizer |
| `aux.query.rewrite.v1`（若启用） | 非生产 |

**小结**：三元组神圣；辅助可哈希但不污染产品身份。

---

### 4.9 `S14-E09` — Model 身份与 binding 路由

**真相**：S14-T004/T005/T022/T042/T043；T-O-266/267/284

| 项 | 规范 |
|---|---|
| Durable 身份 | `model_key` + `model_version`（D04 UNIQUE） |
| 路由 | `mkb_adapter_bindings`：capability → adapter_kind + exact model |
| 展示 | `display_name` 仅展示，**不进** resolve |
| Index 用语 | revision = `model_version`；alias ≠ MLflow 浮动解析层（v1） |
| 换默认 | bootstrap 更新 binding 行（enabled/priority）→ **仅 future** resolve |
| Team 覆盖 / 解析序 | **权威 = S11-E03**；S14 不复述完整算法 |
| L4 钉死 | materialize 写入 exact key+version+adapter_kind；S11 主路径 **只消费冻结身份** |
| 浮动 alias 表 | **v1 不实现**；选项 C 仅显式 reopen |

**禁止**

- durable binding 使用 `latest` / `@champion` / `@production` 作为 version；  
- transport 失败自动换 model/adapter/dimension 或 **重 resolve** 换 binding（G-10）；  
- Task override 换 model/prompt（E04）；  
- 硬编码 `@cf/...` / `gemini-*` 当唯一目录（v1 默认 local_vllm）；  
- 在 S14 维护第二套可执行 resolve 步骤表。

**与 G-10**：S14 registry **不得**暴露「失败即换模型」产品路径；跨模型切换 = 显式 binding 变更或 reopen。

**小结**：binding 表是路由材料；解析算法单点在 S11-E03。

---

### 4.10 `S14-E10` — 错误轴与 Readiness

**真相**：S14-T023/T044..T047；T-O-285/273

**错误码闭集与默认策略**

| Code | 含义 | 默认策略 | 可标 transient？ |
|---|---|---|---|
| `CONFIG_MISSING` | 必选键/profile 缺失 | fail-closed；不 materialize | 否 |
| `CONFIG_CONFLICT` | 多层同键不兼容 | fail-closed | 否 |
| `CONFIG_OVERRIDE_REJECTED` | 未知/越权 override | fail-closed（请求错） | 否 |
| `REGISTRY_NOT_FOUND` | catalog/binding/指针不存在 | fail-closed | 否 |
| `REGISTRY_DIGEST_MISMATCH` | 同 version 异 digest | fail-closed；readiness false | **否** |
| `PROMPT_NOT_REGISTERED` | identity 不在闭集/指针表 | fail-closed | 否 |
| `PROMPT_HASH_MISMATCH` | `H(file) != content_sha256` | fail-closed | **否** |
| `SCHEMA_DIGEST_MISMATCH` | contracts ≠ registry 指针 | readiness false | **否** |
| `MODEL_DISABLED` | status≠active 或 binding disabled | fail-closed（该 capability） | 否 |
| `BINDING_NOT_FOUND` | capability 无 enabled binding | fail-closed | 否 |
| `SNAPSHOT_INCONSISTENT` | materialize 材料不自洽 | fail-closed | 否 |
| `BOOTSTRAP_FAIL` | empty-DB 灌入失败 | readiness false；禁新业务 materialize | 否 |
| `CONFIG_OPS_RELOAD_FAIL` | ops-only 热更失败 | 保持 last-good ops；告警 | 可（ops 面） |

**对外映射（若 HTTP）**：RFC 9457 problem details（`type`/`title`/`detail`/`status`）+ 扩展 `error_code` = 上表 code。内部保持细粒度。

**`registry_bootstrap`=false（S14 谓词权威，OR）**

1. `BOOTSTRAP_FAIL`  
2. required prompt 指针缺失或 hash mismatch（bootstrap 校验集）  
3. required **catalog 行**缺失  
4. 同 version 异 digest（model/schema/prompt bundle）  
5. schema digest 与 contracts/D04 definition 不一致  

**非本组件（禁止双主）**：enabled binding 可探/transport → **`inference_binding`（S11）**；token 非空 → **`sec_token_loaded`（S16）**；DB → S12。

**非 S14**：S11/S12/S16 组件 — 经 S15 HealthAggregator 组合。

**小结**：配置错误可机读；digest 问题永不当 429。

---

### 4.11 `S14-E11` — 安全围栏、可观测钩子与 OOS

**真相**：S14-T024/T048..T053；T-O-286

**安全围栏**

| 围栏 | 规范 |
|---|---|
| Secret | 永不进 git `data/config/**`、`mkb_*` 非 secret 列、ProvenanceEnvelope、诊断明文 |
| Prompt 文件 | 仅模板；禁止嵌入 API key |
| team_uuid | **不是**授权凭证；resolve 仍须 token（S16） |
| Path | 仅 repo 相对 `data/prompts/**`、`data/config/**`；禁 `..` |
| Remote | 禁 silent remote config endpoint 作 SSOT |
| Override | 白名单外拒绝 |

**可观测钩子（逻辑名 → S15 导出名强制映射）**

| 逻辑名（S14 域内） | S15 导出名（Prometheus） | 类型 | 标签 |
|---|---|---|---|
| `registry_resolve_total` | `mkb_registry_resolve_total` | counter | `result` |
| `prompt_hash_mismatch_total` | `mkb_prompt_hash_mismatch_total` | counter | — |
| `bootstrap_fail_total` | `mkb_registry_bootstrap_fail_total` | counter | — |
| `override_rejected_total` | `mkb_config_override_rejected_total` | counter | — |
| `config_ops_reload_total` | `mkb_config_ops_reload_total` | counter | `result`∈ok\|fail |
| `registry.bootstrap_completed` | domain_events | event | 无 secret/正文 |
| `registry.digest_mismatch` | domain_events | event | key/version；无 body |
| `config.ops_reload` | domain_events | event | |
| `config.override_applied` | domain_events | event | keys[]；无 secrets |

`CONFIG_OPS_RELOAD_FAIL` → metric `result=fail` + event；**默认不 page**（S15 无强制 ALERT；可选 ticket residual）。Architecture 测试：禁止注册未映射逻辑名。

**v1 OOS 闭包（完整）**

1. UI config console / prompt 编辑器 / deploy-to-KV  
2. multi-tenant feature marketplace  
3. agent 写 registry（G-12）  
4. automatic multi-provider fallback 平台  
5. 远程 flag/config 服务作业务 SSOT  
6. webhook 配置推送  
7. 浮动 model alias 产品层（含独立 alias 表，除非 reopen）  
8. 第二 workflow 定义编辑面  
9. retention 天数最终 runbook（S15）  
10. 公网 registry CRUD API  
11. 诊断默认 content capture 进业务库  

**小结**：leaf-worker 最小治理面；平台化能力全部延期。

---

### 4.12 配置键逻辑目录（跨域消费 · S14 版本化）

> 下列为 **逻辑配置键**；产品默认值权威仍在各域 Spec。S14 负责：键是否 Semantic、是否可 override、是否进 digest、热更类。

| 逻辑键 | 默认权威域 | Semantic? | Override? | 备注 |
|---|---|---|---|---|
| `retrieve.default_score_threshold` | S10（0.0） | 是 | 可（≤实现 max） | legacy 0.65 非 Truth |
| `retrieve.return_k` / `recall_k` | S10 | 是 | 可（cap） | ≤ max_topk |
| `retrieve.pack_*` | S10 | 是 | 可（cap） | |
| `index.max_topk` | S09 | capacity | 否（caller 不可抬升定义） | 生效值进 digest |
| `s05.profile_id` / clean knobs | S05 | 是 | profile 可 | 身份键不可 |
| `s06.structure_schema_*` | S06 | 是 | 否（schema 身份） | |
| `s07.construction_schema_*` | S07 | 是 | 否 | |
| `inference.*` timeouts（非语义） | S11 | ops（若域声明） | 否 v1 | 声明后才 ops |
| `feature_flags.*` | S14 | 视 flag | 否（未注册） | 默认 OFF |
| `vllm.base_url` | S11/S16 | L2 topology | 否 | env |
| `security.*` | **S16** 默认值/语义；**S14** 分类标签 | **Ops-only** | **否** | **不进** binding_digest |
| `obs.*` | **S15** 默认值/语义；**S14** 分类标签 | **Ops-only** | **否** | **不进** binding_digest |

---

### 4.13 与邻域交接合同

| 邻域 | S14 提供 | S14 要求 |
|---|---|---|
| S03 | 只读 workflow revision/digest 视图；snapshot 含 workflow digests | 七表 SSOT；materialize 调用 resolve |
| S05 | PromptRef 解析+hash；s05 profile 版本化；override 白名单协作 | 只持 PromptRef；retry 不热切 |
| S06/S07 | schema digest 校验协作；promptB/C；provenance 字段 | command_input_digest 冻结 |
| S08/S09/S10 | knobs 版本化与 digest 参与 | 产品默认与 publication 定义权保留 |
| S11 | catalog/binding **bootstrap 写**；L4 冻结身份；provenance 字段 | Inference 门面；G-10；**resolve 权威 S11-E03**；invocation 写 |
| S01/S02 | Port 语义；override 键与错误映射 | 是否暴露 HTTP list；payload schema |
| S12/D04 | 使用既有表；不新增 required 表 | migration 承载 DDL |
| S15 | 钩子逻辑名与事件形状 | 导出/retention/alert |
| S16 | secret/path/team 围栏语义 | 密钥生命周期与鉴权 |

### 4.14 已冻邻域交接合同（S15-v1.0 / S16-v1.0 · accepted）

> **升级**：S15/S16 已 `accepted`；下列为 **强制交接合同**（非 provisional）。

| 邻域 Truth | 合同 |
|---|---|
| S15-T017/T031/E03 | 必须收录 S14-T051 映射之 `mkb_registry_*` / `mkb_config_*` / `mkb_prompt_hash_mismatch_total`；未收录不得 export |
| S15-T040 `registry_bootstrap` | 谓词权威 **仅 S14**（见 S14-T046） |
| S15 event 登记 | `registry.*` / `config.*` 经 D04 扩展表 + S15 DomainEventWriter 闭集 |
| S16-T044/T050 | secret 注入 L2；SupplyFence 与 binding exact identity |
| S16-T003/T017 | token 鉴权；team≠凭证；v1 registry HTTP **OOS** 故不进 EndpointClass |
| S16-T056 | redaction；S14 envelope 服从永不字段 |
| 共同 | **不得**用 log 定义 registry/bootstrap 业务成功 |

---

## 5. 事实反例 + 风险台账

### 5.1 Legacy 反模式（必须删除/改写）

| ID | 反模式 | 订正 | Truth |
|---|---|---|---|
| N-01 | KV 为 Prompt 正文运行时 SSOT | git + hash 指针 | T-O-264 |
| N-02 | DB 存 prompt 正文 + deploy→KV | 禁 body_text；禁 deploy 平台 | T-O-264/271 |
| N-03 | 未注册 key 静默透传 | 闭集 + `PROMPT_NOT_REGISTERED` | T-O-283/285 |
| N-04 | 动态 `KV:` 前缀旁路 | 禁；override 白名单 | T-O-279 |
| N-05 | 硬编码 `@cf/...` / gemini 唯一目录 | catalog+binding | T-O-266/284 |
| N-06 | 租户 override TTL 热缓存无 hash | L4 freeze；禁 silent 热切 | T-O-269/278 |
| N-07 | `payload_config` 任意 JSON merge | 窄白名单 + typed layers | T-O-277/279 |
| N-08 | 三份 cloudflare_ai / 密钥进配置树 | adapter 单落点；secret→S16 | T-O-286 |
| N-09 | console prompt CRUD/deploy | v1 OOS | T-O-271/286 |
| N-10 | 缺 prompt silent “helpful assistant” | fail-closed | T-O-285 |
| N-11 | threshold 魔法数当产品真理 | 配置化 + 域默认 | T-O-281；S10 |
| N-12 | embedding 常量无 catalog 围栏 | definition_digest + Layer A | T-O-266；S11 |

### 5.2 可升级原型（Positive · 非直接移植）

| ID | 原型 | MKB 升级 |
|---|---|---|
| P-01 | 静态 Prompt 别名注册表 | promptA/B/C identity→git path |
| P-02 | 缺 prompt fail-fast | + hash mismatch fail |
| P-04 | action_branch→model 策略表 | S11 binding + S14 profile |
| P-05 | usage/model 回写 | 强制 provenance envelope |
| P-06 | 未注册 alias 显式报错 | 闭集校验 |
| P-07 | 阈值/预算集中配置对象 | 版本化键 + digest |

### 5.3 风险台账

| 风险 | 围栏 |
|---|---|
| mid-flight 配置漂移 | L4 只读；禁重 resolve |
| digest 与 contracts 双写漂移 | bootstrap/readiness fail-loud |
| override 变成换心通道 | 禁止键闭集 + G-10 |
| ops reload 误伤语义 | Semantic/Ops 二分；未知当 Semantic |
| prompt 路径逃逸 | path fence 禁 `..` |
| log 当 provenance SSOT | 强制关系/CAS 字段 |
| S15/S16 钩子未同步目录 | formal 同步 S15-E03；未收录禁 export |
| profile 闭集 code vs git 不一致 | S14-T025 双源一致校验 |

### 5.4 硬性禁止方向（复述）

1. **禁止** DB/KV 存 prompt 正文第二真相。  
2. **禁止** silent model/adapter swap / automatic fallback 平台。  
3. **禁止** in-flight binding 热切 / 无指针 prompt 热加载。  
4. **禁止** Task 任意 merge 覆盖 model/prompt/schema/workflow 身份。  
5. **禁止** silent remote config / 远程 flag 作业务 SSOT。  
6. **禁止** UI config console / agent 写 registry / webhook 配置推送。  
7. **禁止** 第二 workflow 定义 SSOT。  
8. **禁止** log-as-business-SSOT。  
9. **禁止** 引用 `context/legacy-specs/**`、`context/legacy-python/**`、`context/legacy-python-2/**`。  
10. **禁止** 复用/改写既有 `T-O-N`。

---

## 6. 测试与验收台账

> 下列为 **HARD 验收意图**；**不**声称已交付测试代码。实现阶段必须提供对应证据。

### 6.1 强制验收矩阵

| ID | 场景 | 类型 | Truth |
|---|---|---|---|
| S14-A01 | git prompt 变更但未更新指针 → 运用路径 `PROMPT_HASH_MISMATCH` | 集成 | T-O-264/285 |
| S14-A02 | 指针 hash 与文件一致 → 加载成功；envelope 含 prompt_identity+hash | 集成 | T-O-282 |
| S14-A03 | DB/schema **无** `body_text` 列 / 禁止写入正文 | architecture | T-O-264 |
| S14-A04 | materialize 后修改 L1 active → in-flight 仍用 L4；新 Execution 用新值 | 集成 | T-O-269/277/278 |
| S14-A05 | ops log level reload 成功不改 binding_digest | 集成 | T-O-278/281 |
| S14-A06 | ops reload 失败 → last-good + `CONFIG_OPS_RELOAD_FAIL`；binding 不变 | 故障 | T-O-278 |
| S14-A07 | override 未知键 → `CONFIG_OVERRIDE_REJECTED` | 合同 | T-O-279 |
| S14-A08 | override `model_key` → reject | 合同 | T-O-279/267 |
| S14-A09 | override `top_k` 在 cap 内 → 进入 snapshot digest | 集成 | T-O-279 |
| S14-A10 | override 超 cap → reject | 合同 | T-O-279 |
| S14-A11 | empty-DB bootstrap 幂等两次同 digest | 集成 | T-O-275 |
| S14-A12 | 同 version 异 definition_digest → readiness false / `BOOTSTRAP_FAIL` 或 `REGISTRY_DIGEST_MISMATCH` | 集成 | T-O-273/285 |
| S14-A13 | required capability 无 enabled binding → `BINDING_NOT_FOUND` | 合同 | T-O-285 |
| S14-A14 | model status disabled → `MODEL_DISABLED` | 合同 | T-O-285 |
| S14-A15 | RegistryPort 无外部 CUD 路径（architecture + HTTP 若有） | architecture | T-O-280 |
| S14-A16 | workflow 视图只读；无法经 S14 写 S03 七表 | architecture | T-O-268 |
| S14-A17 | Semantic knob 变更改变 binding_digest；Ops knob 不改变 | 单元 | T-O-281 |
| S14-A18 | feature flag 默认 OFF；远程 flag 客户端不存在 | architecture | T-O-281 |
| S14-A19 | structured_generate provenance 缺 schema digest → fail | 合同 | T-O-282 |
| S14-A20 | envelope 写入 prompt 正文 / secret → 拒绝 | 安全 | T-O-282/286 |
| S14-A21 | `aux.*` 不能被 S06 binding 接受 | architecture | T-O-283 |
| S14-A22 | resolve 不接受 `model_version=latest` | 合同 | T-O-284 |
| S14-A23 | display_name 变更不改变 resolve 结果 | 单元 | T-O-284 |
| S14-A24 | digest mismatch **不**映射为 429/transient | 合同 | T-O-285 |
| S14-A25 | path 含 `..` → reject | 安全 | T-O-286 |
| S14-A26 | secret 不出现在 git config fixture / envelope dump | 安全 | T-O-286 |
| S14-A27 | services 不直连 llm_adapters 绕过 catalog（与 S11 共测） | architecture | T-O-266；S11 |
| S14-A28 | 无 agent 写 registry API | architecture | T-O-270 |
| S14-A29 | 实现树不依赖 QNA 路径 | architecture | SSOT |
| S14-A30 | 禁止依赖 legacy-specs/python 树 | architecture | T-O-274 |

### 6.2 必须留存的验收证据

1. contracts：`PromptRef`、`ConfigSnapshot`、`ProvenanceEnvelope`、错误码枚举。  
2. bootstrap 幂等与 digest drift 报告。  
3. hash mismatch / override reject 否定用例。  
4. L4 freeze vs future resolve 对比用例。  
5. architecture 测试：无 body_text、无 CUD、无 latest、无 silent fallback 路径。  
6. 与 S11 binding 解析、S05–S07 PromptRef 交叉集成摘要。

---

## 7. Reference-anchor 台账

### 7.1 权威文档锚

| 锚 | 用途 |
|---|---|
| `qna-truth/S14.md` v1.0-qna-locked | `T-O-263..286` 形成轨迹（**非**执行 SSOT） |
| `D03-v1.0` | prompts git + hash；`data/config` |
| `D04-v1.1` | `mkb_prompt_hash_pointers` / catalog / bindings DDL |
| `D05-v1.0` | promptA/B/C；PromptRefV1 |
| `S03` | workflow 七表 SSOT |
| `S05/S06/S07` | binding freeze；PromptRef only |
| `S11-v1.1` | Inference≠Adapter；bootstrap；G-10 |
| `S10-v1.0` | threshold/pack 配置化先例 |
| `spec-index` §3.14 / G-10 / G-12 / G-13 / G-14 | 范围与 gates |
| `spec-glossary` | PromptRef / GreenfieldBootstrap 等 |

### 7.2 Legacy-family 代码事实锚（ReferenceAnchor only）

| 组件 | 路径（legacy-family） | 用途 |
|---|---|---|
| Clean universal | `smind-skill-clean-universal/core/kv.ts` | P-01/P-06 注册表；N-01/N-04 |
| Structurizer | `smind-skill-rag-structurizer/` | P-04/P-05；N-03/N-05 |
| Constructor | `smind-skill-rag-constructor/` | P-02 fail-fast；N-05 |
| Vectorizer | `smind-skill-rag-vectorizer/` | N-05/N-12 硬编码 model |
| Contexter | `smind-contexter/core/prompt_manager.ts`、`ai/topK.ts` | N-06 热缓存；P-07 knobs |
| Dispatcher | `smind-*-dispatcher/` | N-07 payload_config merge |
| Console | `smind-console/functions/api/prompts/*`、`db/03-workflows.sql` | N-02/N-09 平台 CRUD |

**判定**：retain 概念（注册表、fail-fast、usage 回写）；**rewrite** 为 git/hash/catalog/binding/digest；**delete** KV 正文 SSOT、静默透传、TTL 热切、任意 merge、平台 deploy。

### 7.3 网络对照（design contrast only · 非 Truth）

| Ref | 主题 | 用途 |
|---|---|---|
| XR-01 | 12-factor Config | L2=env 拓扑/secret 分账 |
| XR-02 | OpenGitOps | 版本化 desired state；bootstrap 写 |
| XR-03 | K8s ConfigMap immutable | L4 冻结；env 不自动热更 |
| XR-05/06 | Unleash / Fowler toggles | Semantic vs Ops；禁 flag 承载静态配置 |
| XR-08 | OPA default deny | override 白名单 |
| XR-12/13 | MLflow Model/Prompt Registry | version/lineage 正例；UI/runtime production alias **反例** |
| XR-14 | Braintrust prompt versioning | content-addressed + immutability |
| XR-16/17/18 | W3C PROV / OTel GenAI | typed provenance；导出映射；禁默认 content |
| XR-19 | RFC 9457 | 对外错误映射 |
| XR-21/22 | OWASP secrets / misconfig | secret 围栏 |

**规则**：网络材料 **不得** 覆盖 Owner / D* / S* 冻结。

### 7.4 证据使用判定

- legacy / 网络 **不得** 成为运行时依赖、兼容目标或 dual-read。  
- 仅用于正/反例与验收启发。  
- 禁止 evidence 树：`context/legacy-specs/**`、`context/legacy-python/**`、`context/legacy-python-2/**`。

---

## 8. Domain verdict

### 8.1 最终评价

S14-v1.0 将 progressive `T-O-263..286` 升格为 **唯一可编码执行真相**：配置分层 L0–L4、热更新边界、override 白名单、Registry bootstrap/Port、Semantic/Ops digests、provenance envelope、prompt 命名空间、无浮动 model alias、错误/readiness、安全与 OOS 均已闭包。与 S01/S02/S10 同构的九段式可验收结构 + **E01–E11** 执行台账；实现 **无需** 打开 QNA。

**`ACCEPTED / GO`**

### 8.2 GO 判据（全部满足）

| # | 判据 | 状态 |
|---|---|---|
| 1 | fence+execution T-O 全部映射 S14-T 与 E 包 | met |
| 2 | 关键不变量（model+prompt+schema+params）可测 | met（§6） |
| 3 | 与 D03/D04/D05/S03/S05–S11 无静默冲突 | met（§2.3/2.4） |
| 4 | Hard bans 复述且有验收 | met |
| 5 | QNA 降为证据层 | met（SSOT 声明） |
| 6 | 残差移交明确（非 blocker） | met（§8.3） |

### 8.3 残差 OOS / 移交（非本域 blocker）

| 主题 | 归属 |
|---|---|
| retention 天数 / 告警阈值 / metric 后端 | **S15** |
| secret 轮换 / token 签发 / 网络边界 | **S16** |
| 是否暴露只读 HTTP registry list | **S01** 面裁决 |
| Task payload override 字段 schema 精确 JSON | **S02** 交叉验收 |
| 浮动 alias 表（materialize 钉死） | **未来 reopen**（原 Q8-C） |
| 多环境 promotion UI | OOS |
| 商业 SLO / golden 平台 | S15 |
| agent authoring | G-12 deferred |

### 8.4 对下游约束

- **S05/S06/S07**：只持 PromptRef / schema digest / model binding ref；materialize 必须经 S14 resolve；retry 不热切。  
- **S11**：catalog/binding 继续 code-owned bootstrap 协作；解析权威保留；G-10 不可被 S14 override 面破坏。  
- **S03**：workflow SSOT 不变；S14 只读视图。  
- **S08/S09/S10**：knobs 配置键可版本化；产品默认仍归各域。  
- **S01/S02**：外部只读 list 可选；override 键服从本文白名单。  
- **S15/S16**：导出钩子与密钥生命周期按 §4.11/§4.14。  
- **D04**：不新增 required 表；不引入 body_text。  
- **实现**：contracts 落 `src/contracts/registry/`（或等价）；architecture 测试覆盖 A03/A15/A21/A22/A27–A30。

### 8.5 完成状态

| 项 | 状态 |
|---|---|
| QNA progressive | **locked**（`T-O-263..286`） |
| Formal Spec | **S14-v1.1 accepted**（v1.0→v1.1 对抗评审） |
| 执行 SSOT | **本文 only** |
| G-10 | **closed for v1 transport**（继承 + S14-T005 加固） |
| G-12 | **deferred**（继承） |
| 全局下一 T-O | **T-O-337**（S15/S16 已占 287..336；本战役审计不新占） |

### 8.6 一句话结论

> **S14 冻结「分层配置 + 一次快照 + git/hash prompt + catalog/binding 路由 + 窄 override + typed provenance」：每个模型产物可复现，任何 silent 漂移路径在 v1 被显式关闭。**

---

## 9. 修订历史

| 版本 | 日期 | 作者 | 状态 | 变更 |
|---|---|---|---|---|
| `S14-v1.0` | `2026-08-12` | `MKB owner + Grok workflow domain-truth-s14-s16` | `accepted` | 自 `qna-truth/S14.md v1.0-qna-locked`（`T-O-263..286`，Q1–Q10 workflow-frozen / RC-adjusted B + Δ1–Δ6）升格唯一执行 SSOT；九段式 + E01–E11；L0–L4 快照、热更新、override、RegistryPort/bootstrap、knobs/flags、provenance、prompt 命名空间、无浮动 alias、错误/readiness、安全/OOS 闭包；实现无需 QNA |
| `S14-v1.1` | `2026-08-12` | `MKB owner + Grok workflow domain-truth-s14-s16` | `accepted` | 对抗评审修复：catalog/binding 单一写权威矩阵；override 审计单一 sink；metric 逻辑名→`mkb_*` 映射；security/obs Ops-only；T042 降为 S11-E03 引用；schema digest 物理消费 D04；L4/Execution materialize 钉死；provenance 落表矩阵；params/profile 闭集；邻域合同升格 S15/S16-v1.0；next T-O=337 |

---

## 附录 A · 全局 T-O 占用（S14）

```text
… S10 T-O-247..262
S14 fence          T-O-263..276   FROZEN
S14 execution      T-O-277..286   FROZEN (Q1–Q10 · RC-adjusted)
next free global   T-O-337
```

## 附录 B · 域内 ID 映射速查

| 域内 | 全局 |
|---|---|
| `S14-T001..T014` | `T-O-263..276` |
| `S14-T015..T024` | `T-O-277..286` |
| `S14-T025..T062` | 派生可编码细则（映射上列 T-O，不新占全局号） |
| `S14-E01..E11` | 执行包 |
| `S14-A01..A30` | 验收意图 |

## 附录 C · 物理表消费清单（不新增）

| 表 | S14 角色 |
|---|---|
| `mkb_prompt_hash_pointers` | 指针 SSOT（无 body） |
| `mkb_model_catalog` | 产品目录 |
| `mkb_adapter_bindings` | 路由/binding |
| `mkb_inference_invocations` | provenance 协作只写侧归 S11 |
| S03 workflow 七表 | 只读 version/digest 视图 |
| `mkb_domain_events` | 成功 override/bootstrap/ops_reload 事件（登记 type） |
| `mkb_security_audit_events` | 仅越权/安全拒绝 override（S16 写语义） |
| `mkb_structure_schema_definitions` / `mkb_construction_schema_definitions` | schema digest 读 façade |

## 附录 D · Forbidden evidence 自检

| 检查 | 结果 |
|---|---|
| 引用 `context/legacy-specs/**` | **无** |
| 引用 `context/legacy-python/**` | **无** |
| 引用 `context/legacy-python-2/**` | **无** |
| legacy 证据树 | **仅** `context/legacy-family/**` |
| dual SSOT（QNA 执行） | **无**（QNA 明确非 SSOT） |
| 新增全局 T-O 改写 263..286 | **无** |

## 附录 E · NS1 窄回填：四 role prompt catalog

> 本附录只记录 NS1 的实现落点，不改写 S14 已冻结的产品句，也不把 QNA
> 升格为执行 SSOT。

- `intake.ingest` 的外部 payload 只接收 catalog identity：`json_prompt_id` 必填，
  `markdown_prompt_id`、`clean_prompt_id`、`summarizer_prompt_id` 可选；请求不得携带
  prompt 正文、文件路径或自由格式 `prompt_ref`。未指定的 clean/summarizer 使用
  catalog 默认项。
- catalog 仍由既有 `mkb_prompt_hash_pointers` 承载并晋升
  `prompt_id / prompt_version / role / status / granularity_set`；每个 resolved row
  同时冻结 `git_relative_path` 与 `content_sha256`。正文只存在于 git 的
  `data/prompts/**`，数据库不保存正文或 `body_text`。
- L4 materialize 将四 role 的 identity、版本、字节 hash、相对路径和 JSON 粒度闭集
  写入 frozen `selected_prompts` 与 execution input manifest。重试只复用该冻结选择；
  运行时重新校验 role、路径和 hash，漂移即 fail-closed，不热切换 catalog 新版本。
- `markdown` 是可选的独立转写跳；`json` 必须声明闭集粒度（当前为 `[0,1,2]`），
  B.json 经过 layered kernel adoption 后才可进入 C；C 只消费已验收的 layered JSON。
- catalog CRUD 仅是内部 registry service / internal-token 面，版本不可原位覆盖，
  不提供 public、agent 或 marketplace authoring 面。

## 附录 F · NS2 窄回填：L2 `channel_source`

- ingest L2 增加 `compression_channel` 与 `channel_source`（`priority|explicit`）。omit 时由 `Task.priority` 派生，不再默认 `non-interactive`。
- 显式 `compression_channel` 写入 `channel_source=explicit`，并在 Task 创建 UoW 写 `mkb_security_audit_events`（`config.compression_channel_override`，outcome=`allowed`，禁正文）。
- execution payload 同步写入派生通道，避免 handler 再从 omit 回落 NI。
