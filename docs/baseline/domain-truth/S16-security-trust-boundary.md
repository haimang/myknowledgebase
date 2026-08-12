# S16 — Security & Trust Boundary

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 子系统**：`F4 信任基础 / S16 Security & Trust Boundary`（内部 token·rotation·网络边界·request limit·replay·SSRF·路径安全·secrets·日志脱敏·模型供应链信任）
>
> **日期**：`2026-08-12`
>
> **作者 / 裁决者**：`MKB owner + Grok workflow domain-truth-s14-s16`
>
> **文档性质**：`domain truth / formal subsystem specification`（**唯一执行真相 SSOT**）
>
> **文档状态**：`accepted`（S16 域内已接受；全系统 truth layer 尚未 frozen）
>
> **Truth 版本**：`S16-v1.1`
>
> **上游权威输入**：`D01–D05`、`S01–S15` accepted；`qna-truth/S16.md v1.0-qna-locked`（**证据层 / progressive 中间态 only**，非执行 SSOT）；冻结 Truth `T-O-312..336`；`spec-index` §3.16 / **OD-01/04/05** / **G-02 closed** / **G-10 closed** / **G-12 deferred** / **G-29 closed（T-O-42）** / G-07 closed / G-31 closed
>
> **词汇权威**：`docs/baseline/spec-glossary.md`（`SecurityAuditEvent` / `Team` / `LogicalObjectHandle` / `PreflightAllowlistBinding` / `Fence` / `payload_extra` 禁 secret 等）
>
> **事实证据**：`context/legacy-family/` 仅作 ReferenceAnchor（console ACL、team keys、URL proxy、path/secret leakage、假隔离）；网络 Reference-Check（API key storage、rotation overlap、K8s probes、Prometheus security、SSRF OWASP、12-factor secrets、RFC 9457、OWASP logging）**仅作设计对照**；**禁止** `legacy-specs` / `legacy-python` / `legacy-python-2` 作为本域证据源
>
> **下游消费者**：`S01`、`S02`、`S05`、`S10`–`S15`、跨系统拓扑 `17`、验收冻结 `18`、实现与 architecture tests

> **★ 执行 SSOT 声明（Owner 强制）**：实现、验收、对账 **只依赖本 domain-truth 文件**。`qna-truth/S16.md` 仅保留 progressive 形成过程（`T-O-312..336` 冻结轨迹），**不得**被引用为第二执行真相；冲突时 **以本文为准**。禁止「细节在 QNA、Spec 只写原则」。实现 **无需** 打开 QNA 即可编码。

> **★ 约束级别**：「必须 / 禁止 / 仅允许」= 强制；「应当」= 默认，偏离须 reopen S16；「可以 / 建议」= 非冻结不变量。

> **Owner 产品边界**：S16 是 MKB **Security & Trust Boundary** 域。它回答：**token 由谁签发/轮换**；**哪些 endpoint 内部可见**；**URL fetch 策略**；**调试能力如何隔离**。  
> **关键不变量**：**简单认证 ≠ 无安全边界**；**`team_uuid` 绝不是授权凭证**。  
> **D04 分账**：物理表 `mkb_security_audit_events` 列/索引已冻；**S16 拥有** 威胁模型、admission 写入语义、actor_kind/denial 语义共治、token 指纹策略；**S15 拥有** 该表 retention/export/alert 与查询协作。  
> **不**拥有：业务状态机/CAS（S02/S03/D01）；物理表名闭集/DDL（D04）；event retention 天数（S15）；ANN dual-fence 算法（S09/S10）；object CAS 布局协议（S13）；prompt/model 产品 registry（S14）；Task Audit 上游快照（S01）；完整 IdP/OAuth 产品；细粒度 end-user RBAC 平台；公网多租户 SaaS 加固作为产品范围。

> **邻域分账（入口）**：
>
> | 邻域 | S16 边界 |
> |---|---|
> | **OD-01/05** | leaf-worker；简单内部 token；无 session/RBAC 平台产品 |
> | **OD-04** | `team_uuid` = 审计/分区/追踪/过滤；**非** ownership / membership / 授权凭证 |
> | **S01** | 权限口径 valid/invalid；业务面强制 token；invalid 先于资源读取；Team Registry 预注册；**token 载体/轮换/网络/限流归 S16** |
> | **S02** | team-scoped 查询即使 token 全局；错误 envelope 禁 path/token/stack；rate/rotation 归 S16 |
> | **S05** | URL fetch allowlist + secret **logical ref**；canonical 拒 userinfo；auth 仅 registered secret slot；egress policy 引用 S16 |
> | **S10** | dual-fence；`team_uuid` 服务端强制；细粒度 RBAC **v1 不做** |
> | **S11** | 禁 silent 换 model；invocation 禁 secret/prompt 正文；binding/catalog 非密钥仓 |
> | **S13** | handle only；禁 path 进契约；team CAS；无公网 object API；盘加密/密钥共治 |
> | **S14** | L2 env 仅拓扑+secret **值**；S16 拥有 secret **生命周期/解析策略**；配置键非 secret |
> | **S15** | security_audit **retention/export/alert**；脱敏与 event payload 禁 secret；operator 只读面 **内网+token** 交叉 |
> | **D04** | `mkb_security_audit_events` 物理 schema；admission deny 写此表；非业务 SSOT |
> | **G-02/10/12/29** | 无 webhook 默认；禁 silent model swap；agent authoring deferred；legacy-family reference-only |

> **Legacy 边界（T-O-326 / T-O-42）**：不继承 JWT user+team+role 平台 auth、team API key 当 membership 产品、公开 `/api/proxy` 开放 SSRF、`source_name`/`user_uuid` 假隔离、console ACL 中台、plan/phone membership gate、明文密钥进 log、恒 ok 安全叙事。

> **S14/S15 互指校准（provisional neighbor expectation · 不 reopen 邻域）**：  
> - S14：L2 secret **值**注入接口已冻；本文钉 SecretResolver 生命周期与 slot fail-closed。  
> - S15：operator/repair「内网+token」形状已冻（`T-O-308`）；本文钉 token 载体/轮换/endpoint 矩阵与 security_audit **写入**语义；S15 retention **180d hot** 不变。

---

## 1. Domain 介绍

### 1.1 Domain 价值

S16 把 **内部信任下的最小可编码安全边界** 变成 **可验收、可审计、与业务 CAS 严格分账的执行事实**，并保证：

1. 业务面 **必须** 校验内部 token（valid/invalid 单轴），invalid **先于** 任何资源读；  
2. **`team_uuid` 永不** 被解释为授权凭证；数据隔离靠 team-scoped 查询 + Registry；  
3. token **ops mint**、at-rest **仅指纹**、dual-active 轮换、显式吊销 + audit；  
4. endpoint **分级鉴权**（业务/ops 必 token；probe 可免但内网消毒）；  
5. request limit **token+IP 双维**；限流故障可见 degraded，鉴权永不 fail-open；  
6. 业务重复真相防重放以 **S01/S02 幂等** 为权威；v1 无强制传输 nonce 产品；  
7. 出站 **fail-closed** SSRF 宪法 + DNS rebinding 防护；与 S05 descriptor/allowlist 分账；  
8. secret **仅 logical slot**；env/file 解析；禁 git/DB/log 明文；  
9. 生产 **debug 默认 OFF**；operator/repair = 内网 + token + 审计；  
10. 模型出站 **binding-only** + G-10 禁 silent swap；  
11. `SEC_*` typed 错误 + `mkb_security_audit_events` 必写 denied + redaction 权威；  
12. 实现者 **无需** 打开 QNA 即可编码与验收。

### 1.2 在整体拓扑中的位置

```text
上游 orchestrator（内网）
    │  Authorization: Bearer <token>  （主路径）
    │  team_uuid 仅寻址/过滤（非凭证）
    ▼
┌──────────────────────────────────────────────────────────┐
│ S16 Trust Boundary (admission chain)                        │
│  1. RateLimit (token + IP)                               │
│  2. TokenValidate (timing-safe · active hash set)        │
│  3. Schema / Team-active (S01/S02)                       │
│  4. team-scoped repository fence (S02)                   │
│  denied → mkb_security_audit_events (fail-closed write)  │
└──────────────────────────────────────────────────────────┘
    │ allowed
    ▼
Business surfaces (S01/S02 Task/Team/capability)
    │
    ├── S05 HTTP source ──► S16 EgressPolicy + SecretResolver
    ├── S11 inference   ──► S16 SupplyFence (binding-only)
    ├── S13 objects     ──► path/handle safety reinforcement
    ├── S10 retrieval   ──► dual-fence + team force (consume)
    └── S15 operator    ──► 内网 + token + redaction rules
```

**控制面 vs 数据面（本域）**：

```text
控制面（进程内 · 非业务 SSOT）
  active token fingerprints · rate counters · egress policy · resolver map
数据面（关系库 · D04）
  mkb_security_audit_events  → admission/安全拒绝证据（非业务成功定义）
禁止：用 log/audit 字符串冒充 Task/CAS 成功；用 team_uuid claim 冒充 auth
```

### 1.3 Scope fence

**S16 负责：**

| 主题 | 内容 |
|---|---|
| Token 载体与存储 | header 主路径、ops mint、at-rest hash、timing-safe compare、actor_fingerprint |
| Token 轮换/吊销 | dual-active N=2、重叠窗、ops reload、revoke + audit |
| Endpoint 分级 | Business / Operator / Repair / live / ready / metrics 鉴权矩阵 |
| Request limit | per-token / per-IP 默认、429、故障策略、ops knobs |
| Replay 边界 | 相对业务幂等的声明；禁传输 nonce 产品默认 |
| Egress / SSRF | fail-closed 宪法、硬拒网段、redirect 预算、DNS→IP |
| Secret 生命周期 | SecretResolver 后端优先级、slot fail-closed、禁落点 |
| Path/handle 加固 | 错误消毒、部署侧 object_root 沙箱共治（合同仍 S13） |
| Debug isolation | 生产 OFF、禁 break-glass 任意读盘、ops 审计 |
| 供应链信任围栏 | binding-only、key slot 绑定、G-10 |
| security_audit 写入 | denied 必写、actor_kind、采样策略、admission fail-closed |
| Redaction 权威 | 永不出现字段闭集；S15 执行 obs 路径 |
| 威胁模型 | TM-01..10 可验收控制 |
| 错误轴 | typed `SEC_*` + HTTP 映射 + RFC 9457 字段意图 |
| 配置键 | `security.*` ops knobs（不进 binding_digest） |
| Metric/钩子 | 安全低基数计数（导出归 S15） |

**S16 不负责：**

| 排除项 | 归属 |
|---|---|
| 权限口径「valid=全功能 / 无 team RBAC」定义 | **S01-T046**（S16 实现载体，不扩大口径） |
| Task 六态 / team-scoped 查询契约 | **S02** |
| HTTP descriptor / allowlist-preflight / source definition | **S05** |
| dual-fence 算法 / ANN publication | **S09/S10** |
| object CAS 布局 / handle 协议 | **S13** |
| prompt/model registry 产品 | **S14** |
| security_audit **retention 天数 / export / alert 阈值** | **S15** |
| 物理表 DDL / 列闭集 | **D04** |
| 业务幂等 digest / Idempotency-Key 业务语义 | **S01/S02** |
| 完整 IdP/OAuth/session/refresh | **OOS v1** |
| 细粒度 end-user RBAC 平台 | **OOS v1** |
| 公网多租户 SaaS 加固产品 | **OOS v1** |
| webhook secret / callback 默认 | **G-02 / OOS** |
| 完整 SBOM/attestation SaaS | **OOS v1** |

#### 1.3.1 In-scope / Out-of-scope 对照表

| In | Out |
|---|---|
| 内部 shared-secret token | 用户 login/register/password/reset |
| Ops mint + dual-active rotation | OAuth refresh 链 / per-user session 表 |
| 内网业务 API + token | 公网匿名业务写面 |
| Fail-closed egress 引擎 | 中心化 open proxy 产品 + UI allowlist 台 |
| Env/file SecretResolver | 强制 Vault 唯一后端 |
| Binding-only model 出站 | Silent model/adapter fallback 列表 |
| Typed `SEC_*` + security_audit | SIEM/IdP 安全运营中台产品 |
| Redaction 规则权威 | 把 secret 塞进 metric label「便于排障」 |

### 1.4 身份与关键对象

| 对象 | 定义 | 非定义 |
|---|---|---|
| **InternalToken** | 高熵 shared secret；语义仅 valid/invalid | 非 JWT claims；非 team membership 凭证 |
| **TokenFingerprint** | `SHA-256(token)`（或更强）十六进制指纹 | 非明文；不可逆恢复 token |
| **ActiveTokenSet** | 进程内最多 N=2 同时 valid 的指纹集合 | 非 DB 业务表；非 session 表 |
| **AdmissionDecision** | allow / deny + `SEC_*` code | 非 Task 状态 |
| **SecurityAuditEvent** | `mkb_security_audit_events` 行 | 非 Task Audit；非 domain_events 子集；非业务 SSOT |
| **SecretSlot** | logical ref 名（契约持有） | 非明文值；非 path |
| **SecretResolver** | slot → 值 的进程内解析器 | 非 Vault 产品强制；非 git SSOT |
| **EgressPolicy** | 出站 host/IP/scheme/redirect 规则引擎 | 非 S05 source definition；非 open proxy |
| **EndpointClass** | Business / Operator / Repair / Live / Ready / Metrics | 非用户 RBAC 角色 |
| **RateLimitCounter** | 进程内 token/IP 窗口计数 | 非商业配额；非 per-team billing |
| **SupplyFence** | binding exact identity 出站闸 | 非完整 SBOM SaaS |
| **RedactionRule** | 永不出现字段闭集 + allowlist | 非「日志全开」调试开关 |
| **SEC_* Error** | 安全域 typed 错误码 | 非业务 CAS 主轴；映射 S02 envelope |

### 1.5 完成定义

1. §2 全部 Truth 被 contracts / middleware / ports 实现；  
2. 业务 endpoint：无/错 token → **401 先于资源读**；无 side effect 业务行；  
3. `team_uuid` 不参与 token claim 授权；查询/写强制 team-scoped；  
4. ActiveTokenSet dual-active 轮换与吊销可运维；吊销写 security_audit；  
5. Egress 拒 metadata/link-local/默认私网；DNS resolve 后校验 IP；  
6. Secret 永不进 git/DB 业务列/log/event/metric label；未登记 slot fail-closed；  
7. 生产无 file-debug / 任意读盘 HTTP；operator 内网+token；  
8. 模型路径未绑定 binding → `SEC_SUPPLY_UNBOUND`；无 silent swap；  
9. `outcome=denied` 必写 security_audit（或合法采样聚合）；admission audit 失败 → 5xx；  
10. 零 legacy JWT-RBAC / open-proxy / team-key-auth / 假隔离依赖；  
11. 实现 **无需** 打开 QNA；§6 验收矩阵可通过。

---

## 2. 真相层

### 2.1 真相层使用纪律

本节是 S16 的 **唯一执行 SSOT**。真相映射：

- **全局 Owner Truth**：`T-O-312..336`（fence + execution，来源 `workflow-frozen / RC-adjusted recommendation` 或 uniquely-forced inheritance）；  
- **域内 Truth**：`S16-Txxx`（本文规范编号；每个 MUST/禁止 必须可映射到 T-O 与/或 S16-T）；  
- **QNA**：仅证据；冲突以本文为准。

偏离任一 `S16-Txxx` 必须 change-request、列出受影响 spec，并重新取得 owner 裁决。

### 2.2 Owner Truth 登记（全局 T-O · S16 段 · 执行摘要）

#### 2.2.1 Fence（T-O-312..326）

| Truth-ID | 子类型 | 摘要 | 本域强制 |
|---|---|---|---|
| `T-O-312` | fence / scope | S16 = Security & Trust Boundary；token/网络/限流/replay/egress/secret/path/供应链/audit/debug | scope |
| `T-O-313` | fence / simple-token-authz | valid/invalid 单轴；valid=全业务功能；禁 login/session/RBAC 平台 | authz |
| `T-O-314` | fence / team-not-credential | `team_uuid`≠授权凭证；寻址+隔离；查询仍 team-scoped | team |
| `T-O-315` | fence / admission-before-resource | 先 token 后资源读；unknown team 可 audit 禁建业务行 | admission |
| `T-O-316` | fence / security-audit-table | `mkb_security_audit_events`；denied 必写；actor 闭集；分表 | audit |
| `T-O-317` | fence / secret-refs-only | 契约只持 logical ref；值不进 log/event/audit payload | secrets |
| `T-O-318` | fence / ssrf-egress | 出站受控；canonical；禁 open proxy；S05 协作 | egress |
| `T-O-319` | fence / path-handle-safety | handle only；禁 `..`/绝对 path 进 wire；错误消毒 | path |
| `T-O-320` | fence / dual-fence-data-isolation | 存在≠可服务；强制 team；禁 source_name/user 假隔离；无 end-user RBAC | isolation |
| `T-O-321` | fence / redaction-envelope | 禁 token/secret/path/stack 进 envelope/obs；S16 规则权威 | redact |
| `T-O-322` | fence / no-webhook-no-platform | G-02 polling；无 webhook 默认；无 UI/membership | non-goals |
| `T-O-323` | fence / supply-chain-no-silent-swap | G-10；binding 信任围栏；禁 silent swap | supply |
| `T-O-324` | fence / log-not-ssot | 拒绝不可只存日志；admission→security_audit；业务→CAS | ssot |
| `T-O-325` | fence / internal-surfaces | 业务/ops 内网假设；禁公网裸奔；debug 默认关 | network |
| `T-O-326` | fence / evidence-non-goals | 仅 legacy-family 证据；IdP/RBAC/SaaS hardening OOS | evidence |

#### 2.2.2 Execution（T-O-327..336）

| Truth-ID | 子类型 | 摘要 | 本域强制 |
|---|---|---|---|
| `T-O-327` | execution / token-mint-carrier | Ops mint shared-secret；at-rest hash；timing-safe；主 header Bearer | E03 |
| `T-O-328` | execution / token-rotation | Dual-active N=2；重叠窗默认 24h；吊销+audit | E04 |
| `T-O-329` | execution / endpoint-auth-matrix | 业务/ops/repair 必 token；live 可免；metrics 禁公网匿名 | E05 |
| `T-O-330` | execution / rate-limit | 600/min token + 120/min IP；限流 fail-open+degraded；鉴权 fail-closed | E06 |
| `T-O-331` | execution / replay-boundary | 业务幂等权威；无强制传输 nonce 产品 | E07 |
| `T-O-332` | execution / egress-ssrf | Fail-closed；DNS→IP；redirect≤3；硬拒私网/metadata | E08 |
| `T-O-333` | execution / secret-lifecycle | Env(+file) resolver；slot fail-closed；Vault 可选非强制 | E09 |
| `T-O-334` | execution / debug-isolation | 生产 debug OFF；ops=内网+token+audit；无 break-glass 读盘 | E10 |
| `T-O-335` | execution / supply-chain-trust | Binding-only exact identity；G-10；`SEC_SUPPLY_*` | E11 |
| `T-O-336` | execution / sec-errors-audit-redact-oos | `SEC_*`；audit 纪律；redaction；TM；OOS 闭包 | E12 |

### 2.3 域内 Truth 表（S16-T · 规范）

#### 2.3.1 范围与关键不变量（S16-T001..T015）

| Truth ID | 冻结真相 | 映射 T-O | 下游约束 |
|---|---|---|---|
| `S16-T001` | S16 拥有 token 载体/存储/轮换/吊销、endpoint 分级、限流、replay 边界声明、egress 宪法、secret 生命周期、path 错误消毒、供应链围栏、security_audit **写入语义**、debug 隔离、redaction **规则权威**、威胁模型。不拥有业务状态机、DDL 表名、retention 天数、ANN 算法、object CAS 协议、prompt 正文 registry、Task Audit。 | T-O-312 | 禁吞邻域 |
| `S16-T002` | 权限口径 **继承** S01-T046：token 仅 valid/invalid；任一 valid token 可调用全部业务 Team/Task/capability API；**禁止** 在 S16 扩大为 team-scoped RBAC claim 或 session 产品。 | T-O-313 | S01 不变 |
| `S16-T003` | `team_uuid` 是审计/分区/追踪/过滤 ID 与 Team Registry 投影键，**绝不是**授权凭证。不得从 token claim 推导 membership。即使 token 全局有效，读/写仍强制 team-scoped（S02-T032）。 | T-O-314 | OD-04 |
| `S16-T004` | 业务 admission 序：**token 校验 → schema → team active → 业务幂等/写**。Invalid token **禁止**用于枚举 team/task 是否存在。 | T-O-315 | S01 gate |
| `S16-T005` | 物理表 `mkb_security_audit_events` required（D04）。S16 拥有写入语义；S15 拥有 retention/export/alert。**禁止** security 事件写入 `mkb_domain_events`。与 Task Audit **分表分义**。 | T-O-316 | D04-P13/15 |
| `S16-T006` | 业务契约/descriptor/identity **只**持 logical secret ref/slot。**禁止** 明文 credential、任意 headers/cookies/fetch options、绝对 path 进入 identity 或 `payload_extra`。解析值 **禁止** 进入 log/event/audit payload/metric label。 | T-O-317 | S05/S14 |
| `S16-T007` | 业务 HTTP/API 出站必须受 S16 EgressPolicy + S05 descriptor 约束。**禁止** open proxy endpoint。Allowlist 不绕过 preflight（G-31）。 | T-O-318 | S05 |
| `S16-T008` | 对象契约只用 `mkbobj:v1` handle；**禁止** 绝对 path、`..`、跨 team CAS 复用进 wire。对外错误 **禁止** 泄漏绝对路径。布局协议归 S13；S16 加固错误消毒与部署沙箱要求。 | T-O-319 | S13 |
| `S16-T009` | 检索/向量读：**强制** dual-fence + Layer B team；存在≠可服务；**禁止** 用 `source_name`/`user_uuid` 假隔离替代 team。细粒度 end-user RBAC v1 OOS。 | T-O-320 | S10/S11 |
| `S16-T010` | Redaction 规则权威在 S16；S15/S02 执行路径必须服从。永不字段见 §4.12。 | T-O-321 | S15/S02 |
| `S16-T011` | v1 结果交付 = polling；**不为** webhook/callback secret/重试 worker 建默认设施。无 UI/membership/billing。G-12 agent authoring 安全面 deferred/OOS。 | T-O-322 | G-02/12 |
| `S16-T012` | 禁止 transport/429/5xx 驱动 silent 换 model/adapter（G-10）。业务模型出站必须已注册 binding。 | T-O-323 | S11/S14 |
| `S16-T013` | 安全拒绝与业务失败 **不得** 只存在于 console/stderr。业务终态→CAS/Outcome；admission deny→security_audit。**禁止** log-as-business-SSOT。 | T-O-324 | S15 |
| `S16-T014` | 业务 API、operator 只读、repair、metrics：**内网/受控**假设。**禁止** 默认公网匿名业务写面与公网 object API。 | T-O-325 | deploy |
| `S16-T015` | 唯一 legacy 证据树 = `context/legacy-family/`。v1 Non-goals 闭包见 §4.12 / §5。不继承 N-01..N-16。 | T-O-326 | T-O-42 |

#### 2.3.2 Token 与轮换（S16-T016..T025）

| Truth ID | 冻结真相 | 映射 T-O | 执行包 |
|---|---|---|---|
| `S16-T016` | Mint 主体 = **运维/部署者** 在受控环境生成高熵随机 token。MKB **不**暴露公网 self-service mint API；**不**建用户注册/登录。 | T-O-327 | E03 |
| `S16-T017` | **主路径 header**：`Authorization: Bearer <token>`。**可选兼容**：`X-MKB-Internal-Token: <token>`（两者并存 **Bearer 优先**）。**入口归一**：ingress 应归一为单一内部凭证表示；日志 redaction **必须**覆盖 Authorization **与** `X-MKB-Internal-Token` 头值（S16-T056）。 | T-O-327 | E03 |
| `S16-T018` | At-rest / 进程配置中仅存 **SHA-256（或更强）指纹集合**；明文 **只** 在 mint 交付通道出现一次。明文 **永不** 写 DB 业务列 / security_audit `payload_json` / log。 | T-O-327 | E03 |
| `S16-T019` | Token 比较 **必须** timing-safe / constant-time。校验成功 → `actor_kind=internal_token`，`actor_fingerprint=H(token)`。 | T-O-327 | E03 |
| `S16-T020` | **mTLS** 仅部署可选网络加固；**不**改变应用层 valid/invalid；**不**替代 `actor_fingerprint`。 | T-O-327 | E03 |
| `S16-T021` | ActiveTokenSet 默认 **N=2**（current + previous）。超过 N 的额外指纹须先 drop 或被显式拒绝加载（fail-closed load 策略：拒绝加载超集并告警）。 | T-O-328 | E04 |
| `S16-T022` | 重叠窗默认 **24h**（ops knob `security.token.overlap_hours`，建议 1–72）；**不进** binding_digest。 | T-O-328 | E04 |
| `S16-T023` | 滚动步骤：(1) 生成 new → (2) 注入 active 集（env/file 热载或滚动重启）→ (3) 上游改用 new → (4) 重叠结束 drop old。 | T-O-328 | E04 |
| `S16-T024` | 允许 **ops-only** 重载 active 集；失败 → **last-good** + `ALERT_SEC_TOKEN_RELOAD_FAIL`；**不**改业务 binding。成功 revoke **必须**写 security_audit（即使后续 reload fail）。last-good **建议 TTL** `security.token.last_good_max_age_hours` 默认 **72**；超龄 → readiness degraded 可配置 forced-fail。ActiveTokenSet 空 → `sec_token_loaded` false。 | T-O-328 | E04 |
| `S16-T025` | 吊销 = 从 active 集移除指纹 → 立即 invalid；**必须** 写 security_audit（action 如 `ops.token_revoke` 或 denial 观测）。禁止用户自助 revoke UI / OAuth refresh / per-user session 表 / 对外 rotation SaaS API。 | T-O-328 | E04 |

#### 2.3.3 Endpoint / 限流 / Replay（S16-T026..T035）

| Truth ID | 冻结真相 | 映射 T-O | 执行包 |
|---|---|---|---|
| `S16-T026` | **Business**（Team/Task/result/command/gate/capability/retrieval 等）**必须** valid token + 内网/受控入口。Invalid → **401** 先于资源读。 | T-O-329 | E05 |
| `S16-T027` | **Operator read**（S15 Observability Port / CLI）**必须** valid token + **内网**；team **过滤** 非凭证。 | T-O-329 | E05 |
| `S16-T028` | **Repair hook**（如 `repair_scan_once`）**必须** token + **localhost/内网**；必 audit；禁公网。 | T-O-329 | E05 |
| `S16-T029` | **Liveness** `GET /live`（兼容 `/healthz`）**可免 token**；**禁** DB/依赖探测；JSON **禁** secret/path/token。 | T-O-329 | E05 |
| `S16-T030` | **Readiness** `GET /ready` **默认可免 token**（同信任网；部署可加可选 token）；not ready=**503**；JSON 消毒同 S15。 | T-O-329 | E05 |
| `S16-T031` | **Metrics** `GET /metrics` **禁止公网匿名**；默认 ClusterIP/内网 scrape；scrape bearer **ops knob 默认关**（`security.metrics.require_token=false`）。 | T-O-329 | E05 |
| `S16-T032` | **Object**：无公网 object HTTP API（S13）。 | T-O-329 | E05 |
| `S16-T033` | 限流双维：**per-token 默认 600 req/min**；**per-IP 默认 120 req/min**；窗口算法 = **固定窗口**（1 分钟桶）。v1 **不做** per-team 商业配额。 | T-O-330 | E06 |
| `S16-T034` | 超限 → HTTP **429** + `SEC_RATE_LIMITED`（可选 `Retry-After`）；**不**创建业务行。计数默认 **进程内**；多副本无共享时有效限速约 ×N = **v1 已知残差**（不强制 Redis）。 | T-O-330 | E06 |
| `S16-T035` | **鉴权路径永不**因限流器故障变 valid。计数器故障 → fail-open + `mkb_sec_rate_limiter_degraded` + **`ALERT_SEC_RATE_LIMITER_DEGRADED`（S15）**。`security.rate_limit.enabled=false` 须同 alert。配置不进 binding_digest。 | T-O-330 | E06 |

| Truth ID | 冻结真相 | 映射 T-O | 执行包 |
|---|---|---|---|
| `S16-T036` | 防「重复创建业务真相」权威 = S01/S02 Task Create digest/idempotency（及适用时已有 Idempotency-Key）。v1 **不**强制 client nonce / signed timestamp / HMAC 传输产品；**不**建全局 request-id 去重表作第二业务 SSOT。 | T-O-331 | E07 |
| `S16-T037` | **禁止** 用重放缓存命中改写业务 CAS 成功语义；**禁止** log 当 replay SSOT。公网暴露威胁模型 → **显式 reopen**。 | T-O-331 | E07 |

#### 2.3.4 Egress / Secrets / Debug / Supply（S16-T038..T050）

| Truth ID | 冻结真相 | 映射 T-O | 执行包 |
|---|---|---|---|
| `S16-T038` | 业务出站默认 **deny unless allowed**（fail-closed）。 | T-O-332 | E08 |
| `S16-T039` | 硬拒：link-local、loopback、RFC1918（**除非** ops knob `security.egress.profile=internal_only` **且**部署允许；**默认 off / allow_private_default=false**）、metadata、默认拒字面 IP。`internal_only` **不进** binding_digest；**启用须** security_audit action=`egress.profile_enable` + ops 可见。用途：local vLLM 等 **SupplyFence 已登记 base URL**，**非**泛化 HTTP source 放行。架构测试：默认 deny private。 | T-O-332 | E08 |
| `S16-T040` | Scheme：业务 HTTP source **https 优先/强制**（对齐 S05）；禁 `file:` / 任意 scheme；**拒 userinfo**。 | T-O-332 | E08 |
| `S16-T041` | Redirect 默认 **≤3**；**每跳**重跑 host/IP 策略。 | T-O-332 | E08 |
| `S16-T042` | **DNS rebinding 防御**：resolve 后校验 IP **再** connect；IP 落入硬拒网段 → `SEC_EGRESS_DENIED`。 | T-O-332 | E08 |
| `S16-T043` | Caller **禁止** 任意 headers/cookies/fetch options；auth **仅** registered secret slot（S05）。模型出站基址必须已注册 binding（T-O-335）。policy 失败 fail-closed。 | T-O-332 | E08 |
| `S16-T044` | SecretResolver 后端优先级：(1) env 映射表（S14 L2 部署注入）；(2) 可选 secret file **0600**（路径部署注入，非业务 path 契约）；(3) Vault/KMS **可选扩展非 v1 强制**。未登记 slot → **fail-closed** `SEC_SECRET_UNRESOLVED`。 | T-O-333 | E09 |
| `S16-T045` | **禁止** secret 落点：git `data/config/**`；`mkb_*` 明文 secret 列；provenance；event/log/metric label；`payload_extra`。内部 token 与业务 secret slot **分账命名**（`MKB_INTERNAL_TOKEN*` vs model API keys）。 | T-O-333 | E09 |
| `S16-T046` | Secret 轮换 = 更新 env/file + 滚动/ops reload；**原子激活** versioned slot map（禁半更新空值静默）。reload 失败 → last-good + 告警；可选 `security.secret.last_good_max_age_hours`（默认 72）超龄 degraded。解析失败写 denial/diagnostic（无值）；成功不记明文。 | T-O-333 | E09 |
| `S16-T047` | 生产任意读盘/file-debug/process payload dump **默认 OFF**；**无**公网 HTTP 路径参数读文件；**无** break-glass 任意读盘产品。Dev 详细开关 **不得**默认进入 production image。 | T-O-334 | E10 |
| `S16-T048` | Operator 只读 = S15 Port + 可选 CLI；内网 + 内部 token；team 过滤。Repair：无外部业务状态写面；可选 hook = localhost/内网 + token + security_audit + domain_event。**禁止** operator 任意 SQL/shell；只读面升级写状态；合成 user 主体。 | T-O-334 | E10 |
| `S16-T049` | 业务推理/embedding **必须** 解析 `mkb_adapter_bindings`/catalog 中 **exact `model_key`+`model_version`+`adapter`**。API key slot **关联**注册项。Base URL 来自注册 binding / L2 拓扑。**禁止**请求体注入任意 endpoint；**禁止** silent fallback 列表；**禁止** catalog 存明文 key。 | T-O-335 | E11 |
| `S16-T050` | G-10：transport/429/5xx **不得**自动换 model/adapter。失败码含 `SEC_SUPPLY_UNBOUND` / `SEC_MODEL_ENDPOINT_REJECTED`。完整 SBOM/signing SaaS OOS。 | T-O-335 | E11 |

#### 2.3.5 错误 / Audit / Redaction / 配置 / 可观测（S16-T051..T070）

| Truth ID | 冻结真相 | 映射 T-O | 执行包 |
|---|---|---|---|
| `S16-T051` | `SEC_*` 错误闭集至少含：`SEC_TOKEN_MISSING`、`SEC_TOKEN_INVALID`、`SEC_RATE_LIMITED`、`SEC_RATE_LIMITER_DEGRADED`、`SEC_EGRESS_DENIED`、`SEC_EGRESS_REDIRECT_DENIED`、`SEC_SECRET_UNRESOLVED`、`SEC_SUPPLY_UNBOUND`、`SEC_MODEL_ENDPOINT_REJECTED`、`SEC_PATH_REJECTED`、`SEC_TEAM_SCOPE_VIOLATION`、`SEC_AUDIT_WRITE_FAIL`、`SEC_DEBUG_DISABLED`。对外可映射 RFC 9457；envelope 服从 S02-T038。 | T-O-336 | E12 |
| `S16-T052` | `outcome=denied` 的 admission/安全拒绝 **必须** 留下证据：`metric 全量` + audit **至少** 明细或聚合 summary（见 S16-T055 扩展）。`actor_kind` 闭集。`denial_code` denied 时 NOT NULL。payload 禁明文敏感。**禁止**仅 metric 冒充 audit SSOT。 | T-O-336 | E12 |
| `S16-T053` | Admission 路径 audit 写失败 → 请求 **5xx** + `SEC_AUDIT_WRITE_FAIL`（fail-closed）。**禁止** silent deny。 | T-O-336 | E12 |
| `S16-T054` | security_audit **不写** domain_events；Task Audit 仍 S01。 | T-O-316/336 | E12 |
| `S16-T055` | 高 QPS 采样策略（**metric 全量；audit 采样/聚合**）：(1) invalid-token 每 IP/min ≤N=10 明细，超出 `action=auth.token_invalid_sampled` 聚合行；(2) **`SEC_RATE_LIMITED`** 与高量 **`SEC_EGRESS_DENIED`** 同样：明细 cap + summary（action=`auth.rate_limited_sampled` / `egress.denied_sampled`）。聚合行 **写失败仍 `SEC_AUDIT_WRITE_FAIL`**（admission 路径 5xx）。rate-limit 路径：audit 写失败 **不**强制 5xx（metric 全量 + 尽力 summary；防放大），但 **禁止 silent**；authz invalid/missing 仍 fail-closed on audit fail（T053）。键：`security.audit.*_sample_per_ip_per_min`。 | T-O-336 | E12 |
| `S16-T056` | Redaction 永不出现：token 原文、password、API key、**Authorization 头值**、**`X-MKB-Internal-Token` 头值**、预签名 URL、prompt 全文、向量全文、绝对 path、连接串、内部 stack/SQL（受控诊断面除外）。允许：fingerprint、handle、digest、枚举 code、有界 uuid、截断 summary。**字段闭集变更仅 S16 change-request**（S15/S02 同步引用）。 | T-O-321/336 | E12 |
| `S16-T057` | 威胁模型 TM-01..10 为 v1 **必控**条目（§4.2）；每条映射控制与验收。 | T-O-336 | E02 |
| `S16-T058` | v1 OOS 闭包（完整列表 §5.3）：IdP/OAuth/OIDC；end-user RBAC；公网 SaaS 加固产品；team API key 授权；webhook secret 默认；console 安全中台；强制 Vault 唯一；强制传输 nonce；完整 SBOM SaaS；agent authoring 安全面；answer-gen 密钥面；`team_uuid`/user_uuid 当凭证。 | T-O-336 | E12 |
| `S16-T059` | 配置键（ops knobs，**不进** binding_digest）闭集见 §4.13。变更不改变业务 binding_digest。 | T-O-328/330 | all |
| `S16-T060` | 安全 metric（**名称已收录 S15-E03 闭集**）：`mkb_sec_auth_total`、`mkb_sec_rate_limited_total`、`mkb_sec_egress_denied_total`、`mkb_sec_secret_unresolved_total`、`mkb_sec_audit_write_fail_total`、`mkb_sec_rate_limiter_degraded`、`mkb_sec_token_reload_total`、`mkb_sec_supply_reject_total`。S16 定义语义；S15 唯一 export registry。label 低基数。 | T-O-330/336 | E12 |
| `S16-T061` | 告警协作（S15 拥有 alert_id 与阈值键）：`ALERT_SECURITY_DENY_SPIKE` 默认开，阈=`obs.alert.security_deny_spike_per_min`（S15）；另 `ALERT_SEC_RATE_LIMITER_DEGRADED` / `ALERT_SEC_TOKEN_RELOAD_FAIL` / `ALERT_SEC_AUDIT_WRITE_FAIL`。S16 提供 metric 谓词。 | T-O-330 | S15 |
| `S16-T062` | Readiness 组件 `sec_token_loaded`：ActiveTokenSet 非空且可 timing-safe 比较；空集 → not ready（**禁止**「无 token 却放行业务」）。不阻塞 `/live`。 | T-O-325/329 | E05 |
| `S16-T063` | 错误响应不得区分「token 格式错」与「token 不在 active 集」到可枚举粒度以外；统一 `SEC_TOKEN_INVALID`（缺失用 `SEC_TOKEN_MISSING`）。 | T-O-327 | E03 |
| `S16-T064` | `SEC_TEAM_SCOPE_VIOLATION`：跨 team 或缺失 team 围栏；HTTP 映射服从 S02（常 403/404 策略）；**不**把 team 匹配当 auth 成功条件。 | T-O-314/336 | E12 |
| `S16-T065` | `SEC_PATH_REJECTED`：path/handle 安全拒绝；对外不回显绝对 path。 | T-O-319/336 | E12 |
| `S16-T066` | `SEC_DEBUG_DISABLED`：生产 debug 面关闭时的拒绝码（404/403）。 | T-O-334/336 | E10 |
| `S16-T067` | contracts 建议落点：`src/contracts/security/`（TokenClaims 空壳/仅 valid、SecError、EgressDecision、SecretSlotRef、AuditWriteIntent、RateLimitDecision、EndpointClass）。 | D03 | impl |
| `S16-T068` | 建议代码边界：`TokenAuthenticator`、`ActiveTokenSet`、`RateLimiter`、`EgressPolicyEngine`、`SecretResolver`、`SupplyFence`、`SecurityAuditWriter`、`RedactionMiddleware`、`EndpointAuthMatrix`。Port 名可微调，语义不可丢。 | T-O-312+ | impl |
| `S16-T069` | 实现 **无需** 打开 QNA；本文为唯一执行 SSOT。 | SSOT | all |
| `S16-T070` | 与 S14/S15 互指：L2 secret 值注入服从 S14；operator 形状服从 S15+本文矩阵；冲突时 **D\* > S\*** 且 security_audit 物理列以 D04 为准。 | fence | neighbors |

### 2.4 继承上游（不重开）

- **S01-T046/E09**：权限口径 valid/invalid；token 载体归 S16；invalid 先于资源。  
- **S02-T032/T038**：team-scoped 强制；安全 error envelope。  
- **S05**：HTTP canonical、secret-ref、allowlist-preflight、G-31；egress 引擎归 S16。  
- **S10 T-O-249/257**：dual-fence + team 强制。  
- **S11 T-O-199 / Layer B**：禁 silent swap；team 强制。  
- **S13**：handle-only；无公网 object API。  
- **S14 T-O-277/286**：L2 仅拓扑+secret 值；禁 git secret。  
- **S15 T-O-293/302/308/311**：security_audit 分表；180d retention；operator 内网+token；脱敏执行。  
- **D04 §3.1.5 / T-O-166/177**：表列/索引/denied 必写。  
- **G-02/G-07/G-10/G-12/G-29/G-31**：polling；context-only；禁 silent swap；agent deferred；legacy-family only；allowlist 不绕 preflight。  
- **OD-01/04/05**：leaf-worker；team≠credential；简单内部 token。

### 2.5 所有权分账总表（S16 owns vs consumes）

| 主题 | S16 owns | S16 consumes | 禁止 |
|---|---|---|---|
| 权限口径 valid/invalid | 实现载体/校验 | **S01-T046** 定义 | 扩大为 RBAC 平台 |
| team 数据围栏 | 加固 + 错误码 | **S02** 强制查询 | team-as-auth |
| token mint/rotate/store | **是** | 部署 env | self-service mint API |
| endpoint 鉴权矩阵 | **是** | S15 探针形状 | 公网匿名业务写 |
| rate limit | **是** | S14 knobs 登记协作 | per-team 计费配额产品 |
| 业务幂等 | 边界声明 | **S01/S02** 权威 | replay ledger SSOT |
| HTTP descriptor/allowlist | — | **S05** | open proxy |
| Egress 引擎/硬拒网段 | **是** | S05 canonical URI | https-only 当 SSRF 防护 |
| Secret 生命周期/resolver | **是** | S14 L2 注入接口 | git/DB 明文 SSOT |
| Object handle 协议 | 错误消毒 | **S13** | path 进 wire |
| dual-fence 算法 | 强制服从 | **S09/S10** | 假隔离 |
| model binding 身份 | 出站围栏 | **S14/S11** registry | silent swap |
| security_audit DDL | — | **D04** | 第二套表名 |
| security_audit 写入语义 | **是** | D04 列 | silent deny |
| security_audit retention | — | **S15** | 并入 domain_events |
| redaction 规则 | **权威** | S15 执行 obs | secret-in-log |
| operator 只读 Port | 鉴权 | **S15** 形状 | console UI 中台 |
| Task Audit | — | **S01** | 混表 |

---

## 3. 总体方案陈述

1. **简单 token + 完整威胁边界**：valid/invalid 单轴，但 admission/SSRF/secret/path/redact/audit 全覆盖。  
2. **`team_uuid` 永不 auth**：全局 token + 请求 team 寻址 + team-scoped 数据围栏。  
3. **Ops mint · at-rest hash · dual-active 轮换**：无 IdP；可运维；可吊销可审计。  
4. **分级 endpoint 矩阵**：业务/ops 必 token；探针可免；metrics 禁公网匿名。  
5. **Token+IP 限流 + 显式故障分账**：鉴权 fail-closed；限流 degraded 可见。  
6. **业务幂等 > 传输 nonce 产品**：内网威胁模型；公网须 reopen。  
7. **Egress fail-closed + DNS→IP + redirect 预算**：与 S05 分账 descriptor/引擎。  
8. **Secret slot · env 主路径 · 禁明文落点**：Vault 可选非强制。  
9. **生产 debug OFF · ops 内网+token+审计**：无 break-glass 任意读盘。  
10. **Binding-only 供应链 · G-10**：无影子端点；无 silent swap。  
11. **typed SEC_* · denied 必写 audit · redaction 权威**：禁 silent deny。  
12. **QNA 零依赖**：全部执行细节在本文 §4。

---

## 4. 具体执行方案清单

### 4.1 `S16-E01` — 范围、非目标、邻域分账

**编号与说明**：建立 Security 模块边界、硬非目标、与 S01/S02/S05/S10/S13/S14/S15/D04 的依赖方向。

**真相层对应**：S16-T001..T015；T-O-312..326

| 项 | 规范 |
|---|---|
| 域身份 | F4 / S16 Security & Trust Boundary |
| 代码落点（建议） | `src/services/security/` 或 `src/security/`；`src/contracts/security/` |
| 公共 surface | admission middleware；SecretResolver port；EgressPolicy port；无独立公网产品 UI |
| 非能力 | 不是 Process capability；不创建/推进 Task/Execution/Process；不拥有 Team membership |
| 硬非目标 | IdP/OAuth；end-user RBAC；公网 SaaS 加固产品；webhook 默认；console 安全中台；完整 SBOM SaaS |

**执行台账**

1. Architecture 测试：业务 services 不得绕过 `TokenAuthenticator` 写业务入口。  
2. 分账表（§2.5）进入允许依赖列表；security 模块不得直接 CAS 改 Task status。  
3. 登记 readiness 组件 `sec_token_loaded`。  
4. 文档/code 声明：security_audit 非业务 SSOT；log 非 SSOT。  
5. 禁止依赖 `legacy-specs` / `legacy-python*`。

**小结**：S16 是信任闸与围栏，不是第二状态机或用户平台。

---

### 4.2 `S16-E02` — 威胁模型 TM-01..10

**编号与说明**：将威胁模型条目化为可验收控制。

**真相层对应**：S16-T057；T-O-336

| ID | 威胁 | v1 控制 | 验收要点 |
|---|---|---|---|
| **TM-01** | 无/错 token 调业务 API | E03/E05；401 先于资源 | S16-A01 |
| **TM-02** | token 暴力 / 滥用 | E06 限流；metric + 可选 audit 采样 | S16-A08 |
| **TM-03** | 用 team_uuid 冒充授权 | T-O-314；team-scoped 数据非 auth | S16-A02 |
| **TM-04** | SSRF 打 metadata/内网 | E08 | S16-A12 |
| **TM-05** | secret 进 log/表 | E09/E12 redaction | S16-A15 |
| **TM-06** | path 遍历 / path 进 wire | T-O-319；S13 + `SEC_PATH_REJECTED` | S16-A16 |
| **TM-07** | 假隔离（source_name/user） | T-O-320；S10 dual-fence | 邻域 A + S16-A17 |
| **TM-08** | silent model swap / 影子端点 | E11；G-10 | S16-A18 |
| **TM-09** | debug 面泄 payload | E10 | S16-A14 |
| **TM-10** | audit 沉默丢拒绝 | E12 fail-closed 写 | S16-A10 |

**执行台账**

1. 将 TM 表纳入 architecture review checklist。  
2. 每条 TM 至少一条自动化验收或明确邻域验收引用。  
3. 新增威胁须 change-request append（不静默改 TM 语义）。

**小结**：简单 token 仍有可列举、可测试的威胁面。

---

### 4.3 `S16-E03` — Token mint、载体、at-rest、校验

**编号与说明**：钉死 mint 主体、header 主路径、指纹存储、timing-safe 校验与 actor 字段。

**真相层对应**：S16-T016..T020/T063；T-O-327

**规范表**

| 项 | v1 规则 |
|---|---|
| Mint 主体 | Ops/部署者；高熵 CSPRNG（建议 ≥256 bit 熵） |
| 交付 | 明文只展示/交付一次；之后仅指纹 |
| 主 header | `Authorization: Bearer <token>` |
| 兼容 header | `X-MKB-Internal-Token`（可选） |
| 冲突解析 | 同时存在时 **Bearer 优先** |
| At-rest | `SHA-256` hex 指纹集合（可用更强；算法须全站一致） |
| 进程加载 | 启动加载 active 明文集用于 compare，或仅 hash 集 + 对 input hash 比较；明文不落库 |
| Compare | timing-safe |
| 成功 actor | `actor_kind=internal_token`；`actor_fingerprint=H(token)` |
| 失败 | 缺 header → `SEC_TOKEN_MISSING`/401；不匹配 → `SEC_TOKEN_INVALID`/401 |
| mTLS | 部署可选；不改应用语义 |
| 禁止 | JWT user/team/role/plan claims；team API key 产品；token 明文 log/DB |

**Env 命名（建议闭集）**

| 键 | 含义 |
|---|---|
| `MKB_INTERNAL_TOKENS` | 逗号分隔 active 明文（部署注入；优先于单值）或 |
| `MKB_INTERNAL_TOKEN` | 单 token 明文（兼容单密钥部署） |
| `MKB_INTERNAL_TOKEN_PREVIOUS` | 可选 previous（双活） |
| `security.token.*` | 见 §4.13 配置键（也可 YAML ops，非 git secret） |

> 明文 env 是 **部署注入接口**，不是 git SSOT；仓库 fixture 仅用假 token。

**执行台账**

1. 实现 `TokenAuthenticator` + `ActiveTokenSet`。  
2. Architecture 测试：业务路由挂载鉴权中间件。  
3. 单元测试：timing-safe；缺失 vs invalid 码；Bearer 优先。  
4. 禁止：从请求 body 读 token 作主路径。  
5. OpenAPI/contract 声明 Bearer security scheme。

**小结**：ops mint shared-secret + 指纹 at-rest；简单且可审计。

---

### 4.4 `S16-E04` — Rotation、dual-active、吊销

**编号与说明**：零停机轮换与紧急吊销。

**真相层对应**：S16-T021..T025；T-O-328

| 项 | v1 规则 |
|---|---|
| N | **2**（current + previous） |
| 重叠窗 | 默认 **24h**；`security.token.overlap_hours` ∈ [1,72] 建议 |
| 滚动 | 生成 new → 注入 → 上游切换 → drop old |
| 热载 | ops-only reload；single-flight；失败 last-good + metric/alert |
| 吊销 | 移指纹立即 invalid + security_audit |
| 禁止 | 自助 UI；refresh 链；session 表；对外 rotation SaaS API |

**吊销 audit 字段意图**

| 字段 | 值意图 |
|---|---|
| `action` | `ops.token_revoke` |
| `outcome` | `allowed`（运维动作成功）或上下文 `denied`（若表示拒绝使用旧 token 的观测） |
| `actor_kind` | `operator` 或 `system` |
| `actor_fingerprint` | 操作者 token 指纹（若适用） |
| `payload_json` | 仅 `revoked_fingerprint_prefix`（短前缀）等低基数；**禁**明文 token |

**执行台账**

1. 实现 reload hook（SIGHUP 或内网 ops endpoint，**必 token**）。  
2. Metric：`mkb_sec_token_reload_total{result}`。  
3. 验收：双活窗口两 token 均 200；吊销后旧 token 401。  
4. Runbook：泄漏响应 = 立即 revoke + 轮换。

**小结**：运维轮换而非生命周期平台。

---

### 4.5 `S16-E05` — Endpoint 鉴权矩阵与探针

**编号与说明**：按表面分级鉴权；对齐 S15 live/ready 形状。

**真相层对应**：S16-T026..T032/T062；T-O-329

| Surface | 路径意图 | Token | 网络 | 额外 |
|---|---|---|---|---|
| Business | Team/Task/result/command/gate/capability/retrieval | **必须** | 内网/受控 | 401 先于资源 |
| Operator read | Observability Port/CLI | **必须** | **内网** | team 过滤 |
| Repair | `repair_scan_once` 等 | **必须** | localhost/内网 | audit |
| Liveness | `GET /live` `/healthz` | **可免** | 探针网 | 禁依赖；JSON 消毒 |
| Readiness | `GET /ready` | **默认可免**；可选 token | 内网 | 503；含 `sec_token_loaded` |
| Metrics | `GET /metrics` | 默认网络边界；scrape bearer **默认关** | 内网 scrape | 禁公网匿名 |
| Object | — | — | — | **无公网 API** |

**共同网络宪法**

1. 禁止默认公网匿名 Business/Operator/Repair。  
2. 即使 probe 免 token：响应与 header 永不含 secret/绝对 path/token 原文。  
3. 部署推荐：ClusterIP / 内网 LB；公网网关非 v1 产品范围。  
4. **metrics 验收**：绑定内网 listener；非内网暴露 → 部署 fail / readiness 文档检查点；可选 `security.metrics.require_token=true` 测试。

**EndpointClass × rate-limit 矩阵**

| EndpointClass | rate-limit | 备注 |
|---|---|---|
| Live | **exempt** | 防探针 429→重启发风暴；k8s 默认 ~10s 可假设 |
| Ready | **exempt** 或独立高预算（≥600/min/IP） | 默认 exempt |
| Metrics | **独立预算** 默认 30/min/IP scrape | 与业务 120 分离 |
| Business / Operator / Repair | 默认 120/IP + 600/token | 双维 |

**执行台账**

1. 路由表标注 `EndpointClass` + rate-limit class。  
2. Integration：无 token 业务 → 401 且无 DB team 查询。  
3. `/live` 不触 DB；`/ready` 含 `sec_token_loaded`。  
4. `/metrics` 内网 + 可选 bearer。  
5. 禁止：debug 挂到免 token 路径；探针路径被 429。

**小结**：探针兼容与业务强制 token 并存。

---

### 4.6 `S16-E06` — Request limit

**编号与说明**：双维防滥用与故障策略。

**真相层对应**：S16-T033..T035；T-O-330

| 维度 | 默认 | 键 |
|---|---|---|
| Per-token | **600**/min | `security.rate_limit.token_per_min` |
| Per-IP | **120**/min | `security.rate_limit.ip_per_min` |
| Per-team | **不做** | — |
| 算法 | **固定窗口** 60s | `security.rate_limit.window_seconds=60` |
| 存储 | 进程内 | 多副本有效上限 ≈×N 残差 accepted |
| 超限 | 429 + `SEC_RATE_LIMITED` + 可选 Retry-After | metric 全量；audit 可采样 |
| 计数故障 | fail-open + degraded metric + **ALERT_SEC_RATE_LIMITER_DEGRADED** | 鉴权仍 fail-closed |

**多副本验收/运维**

- 产品不要求 Redis；**验收环境默认 N=1 进程**（或声明 `max_replicas` 并按 ×N 调阈）。  
- 部署建议：admission sticky IP / 单 admission 入口收敛有效限流。  
- 可选 metric `mkb_sec_replica_count_estimate`（ops，非必须）。

**执行台账**

1. 实现 `RateLimiter`；Live/Ready 按矩阵 exempt。  
2. 序：IP 粗限流 → token 校验 → token 细限流。  
3. Metric + S15 alerts。  
4. 禁止：限流故障当 authenticated。

**小结**：防滥用默认开启，且故障行为显式。

---

### 4.7 `S16-E07` — Replay 边界

**编号与说明**：划清传输层与业务幂等权威。

**真相层对应**：S16-T036..T037；T-O-331

| 层 | v1 规则 |
|---|---|
| 业务幂等 | S01/S02 digest / 已有 Idempotency-Key **权威** |
| 传输层 | **不**强制 nonce/HMAC/timestamp 产品 |
| 网络 | 内网 + TLS（部署）+ token |
| 禁止 | 重放缓存改写 CAS 成功；log 当 replay SSOT；全局 request-id 去重表第二 SSOT |
| 未来公网 | 须显式 reopen |

**执行台账**

1. 文档与 architecture 注释声明：S16 不实现传输 nonce 中间件为默认。  
2. 验收：重复合法幂等 Create 收敛同一业务结果（邻域测试）；invalid token 重放仍 401。  
3. 禁止：security 模块写入业务成功旁路。

**小结**：防重复业务真相归业务层；S16 不另起 SSOT。

---

### 4.8 `S16-E08` — Egress / SSRF 宪法

**编号与说明**：全局出站引擎；与 S05 分账。

**真相层对应**：S16-T038..T043；T-O-332

**分账**

| 职责 | 所有者 |
|---|---|
| Source definition、canonical URI、allowlist↔preflight、secret **ref** | **S05** |
| Egress 引擎、硬拒网段、redirect 预算、DNS→IP、`SEC_EGRESS_*` | **S16** |
| Model base URL 注册 | **S14/S11**；S16 SupplyFence 强制 |

**硬拒目标（默认）**

| 类 | 示例 |
|---|---|
| Link-local | `169.254.0.0/16`、`fe80::/10` |
| Loopback | `127.0.0.0/8`、`::1` |
| RFC1918 | `10/8`、`172.16/12`、`192.168/16`（除非 `internal_only` profile） |
| Metadata | `169.254.169.254`、metadata 主机名惯例 |
| Scheme | 非 https（业务 HTTP source）；`file:` 等 |
| Userinfo | 任何 `user:pass@host` |
| 字面 IP | 默认拒（ops 可开受控例外，仍跑硬拒网段） |

**强制流水线（S05 HTTP source 主路径 · 不可短路）**

```text
1. S05: build descriptor + canonicalize URI (reject userinfo)
2. S05: allowlist-preflight / secret-ref 绑定（secret 不在此解析为明文 URL）
3. S16: egress_check(url, profile)  ← allowlist 命中 **不能** 绕过
4. S16/S05: resolve secret slot → 注入（失败 SEC_SECRET_UNRESOLVED）
5. fetch with validated IPs only
6. on deny: SEC_EGRESS_* + metric + audit（可采样）
```

```text
function egress_check(url, profile):
  u = canonicalize(url)          # S05 rules; reject userinfo
  if scheme not allowed: deny SEC_EGRESS_DENIED
  host = u.host
  ips = resolve(host)            # DNS
  for ip in ips:
    if ip in hard_deny_cidrs(profile): deny SEC_EGRESS_DENIED
  connect only to validated ips
  on redirect (count <= 3):
    re-run egress_check(redirect_url, profile)
  else: deny SEC_EGRESS_REDIRECT_DENIED
```

**错误码映射**：`SEC_EGRESS_DENIED` / `SEC_EGRESS_REDIRECT_DENIED`（S16）vs S05 acquisition 业务错误（allowlist miss 等）——**不得**互相吞并。

**执行台账**

1. 实现 `EgressPolicyEngine`；所有业务 HTTP 客户端强制经此。  
2. 禁 open proxy。  
3. Architecture：**allowlist 命中 + RFC1918/metadata 仍 deny**（默认 profile）。  
4. DNS rebinding mock。  
5. `internal_only` 启用审计 + 默认 off 测试。  
6. 失败写 security_audit（采样策略见 T055）。

**小结**：deny-unless-allowed；allowlist 不绕硬拒。

---

### 4.9 `S16-E09` — SecretResolver 与生命周期

**编号与说明**：logical slot → 值；禁明文落点。

**真相层对应**：S16-T044..T046；T-O-333

| 项 | v1 规则 |
|---|---|
| 契约持有 | `secret_slot` / logical ref only |
| 解析 | `SecretResolver.resolve(slot) -> SecretValue`（内存短时；不返回给 log） |
| 缺 slot | fail-closed `SEC_SECRET_UNRESOLVED` |
| 后端 1 | env 映射（S14 L2） |
| 后端 2 | 可选 file 0600 |
| 后端 3 | Vault/KMS 可选扩展 **非强制** |
| 轮换 | 更新注入源 + reload；失败 last-good |
| 分账命名 | `MKB_INTERNAL_TOKEN*` vs `MKB_SECRET_<SLOT>` / binding key slots |
| 禁止落点 | git config；DB 明文列；provenance；event/log/metric；payload_extra |

**执行台账**

1. 实现 resolver + slot registry（code 或 L2 map）。  
2. Architecture 测试：扫描禁止 secret 字面量进 `data/config/**` fixtures。  
3. 单元：未知 slot fail-closed；成功路径不 log 值。  
4. 文档记录进程 env/core dump 残差 → 部署缓解（权限、禁 core）。  
5. Extension point：`SecretBackend` trait 预留 Vault，无 v1 必选实现。

**小结**：12-factor 注入 + 严格禁落点 + slot fail-closed。

---

### 4.10 `S16-E10` — Debug isolation 与 operator/repair

**编号与说明**：生产 debug 默认 OFF；ops 受控。

**真相层对应**：S16-T047..T048/T066；T-O-334

| 面 | v1 规则 |
|---|---|
| file-debug / 任意读盘 / payload dump HTTP | 生产 **OFF**；无路径参数读文件 API |
| Operator 只读 | S15 Port；内网+token；team 过滤 |
| Repair | 无外部业务写面；hook=内网+token+audit+event |
| 对外错误 | S02 envelope；禁 stack/path/token/Process payload |
| Dev | 本地可开；**禁止**默认进 production image |
| 禁止 | 任意 SQL/shell；只读升写；合成 user 主体 |

**执行台账**

1. Feature flag `security.debug.filesystem_enabled` 默认 **false**；production profile 强制 false。  
2. 若请求 debug 面 → `SEC_DEBUG_DISABLED`。  
3. Operator 路由复用 E05 矩阵。  
4. 验收：生产配置下 debug 路径 404/403；无文件内容回显。  
5. 与 S15-T048 repair hook 交叉：写 security_audit `ops.repair_scan`。

**小结**：排障靠受控只读 Port，不靠 console file-debug。

---

### 4.11 `S16-E11` — 模型/adapter 供应链信任围栏

**编号与说明**：binding-only 出站 + G-10。

**真相层对应**：S16-T049..T050；T-O-335

| 规则 | v1 |
|---|---|
| 出站身份 | exact `model_key` + `model_version` + `adapter` |
| Key slot | 绑定注册项；禁全局一把 key 打任意 URL 默认 |
| Base URL | binding / L2 拓扑；禁请求体 override endpoint |
| G-10 | 失败即失败；无自动换 model/adapter |
| 失败码 | `SEC_SUPPLY_UNBOUND` / `SEC_MODEL_ENDPOINT_REJECTED` |
| OOS | 完整 SBOM/signing SaaS |

**执行台账**

1. `SupplyFence` 在 S11 transport 前校验 binding 解析结果。  
2. Architecture：禁止业务路径 `httpx/fetch(arbitrary_url)` 调模型。  
3. 验收：未登记 endpoint → fail-closed；模拟 429 不换 binding。  
4. Catalog **禁**明文 key 列（密钥走 slot）。

**小结**：注册身份是信任根；影子端点不可走业务路径。

---

### 4.12 `S16-E12` — `SEC_*`、security_audit 写语义、redaction、OOS

**编号与说明**：错误轴、审计纪律、脱敏权威与 OOS 闭包。

**真相层对应**：S16-T051..T058/T060..T066；T-O-336

#### 4.12.1 `SEC_*` 码表与 HTTP 映射

| Code | 含义 | HTTP（业务面） |
|---|---|---|
| `SEC_TOKEN_MISSING` | 无 token | **401** |
| `SEC_TOKEN_INVALID` | 无效/已吊销 | **401** |
| `SEC_RATE_LIMITED` | 限流 | **429** |
| `SEC_RATE_LIMITER_DEGRADED` | 限流器故障（metric/ops；通常不单独替代业务码） | — |
| `SEC_EGRESS_DENIED` | 出站策略拒绝 | 4xx/domain 映射（常见 400/422） |
| `SEC_EGRESS_REDIRECT_DENIED` | redirect 非法 | 同上 |
| `SEC_SECRET_UNRESOLVED` | slot 无法解析 | fail-closed 5xx/domain |
| `SEC_SUPPLY_UNBOUND` | 未绑定 catalog/binding | fail-closed 5xx/domain |
| `SEC_MODEL_ENDPOINT_REJECTED` | 非法 model endpoint | fail-closed |
| `SEC_PATH_REJECTED` | path/handle 安全拒绝 | 4xx |
| `SEC_TEAM_SCOPE_VIOLATION` | 跨 team / 缺围栏 | 403/404（S02 策略） |
| `SEC_AUDIT_WRITE_FAIL` | admission audit 写失败 | **5xx** |
| `SEC_DEBUG_DISABLED` | 生产 debug 关闭 | 404/403 |

对外 RFC 9457 意图字段：`type`/`title`/`detail` + 扩展 `error_code`/`trace_uuid?`；**禁** stack/path/token。

#### 4.12.2 security_audit 写语义

| 规则 | v1 |
|---|---|
| 必须写 | `outcome=denied` 的 admission/安全拒绝（认证失败、跨 trust、egress 安全拒绝等未进业务表） |
| actor_kind | `anonymous` / `internal_token` / `system` / `operator` |
| actor_fingerprint | `H(token)` 或 NULL |
| denial_code | denied 时 NOT NULL；对齐 `SEC_*` / 适用 S02 code |
| payload | 低基数 JSON；禁 token/secret/prompt/path 明文 |
| 分表 | **不写** domain_events |
| 失败 | admission 路径 → **5xx** fail-closed |
| 采样 | 见 S16-T055（invalid-token / rate-limit / egress）；metric 全量；至少明细或 summary |
| 列 | 服从 D04 §3.1.5；S16 不改 DDL |

#### 4.12.2.1 security_audit `action` 闭集（v1 · 扩展须 CR）

| action | 场景 |
|---|---|
| `auth.token_validate` | 成功/尝试校验 |
| `auth.token_invalid` | invalid/missing 明细 |
| `auth.token_invalid_sampled` | 采样聚合 |
| `auth.rate_limited_sampled` | 429 聚合 |
| `task.create` | 业务 create 相关 admission |
| `team.access` | team 围栏 |
| `egress.fetch` | 出站尝试 |
| `egress.denied_sampled` | egress deny 聚合 |
| `egress.profile_enable` | internal_only 等 profile 启用 |
| `ops.token_revoke` | 吊销 |
| `ops.token_reload` | 重载 |
| `ops.repair_scan` | repair hook |
| `config.override_denied` | S14 越权 override |

**D04 列使用纪律（S16）**

| 列 | S16 写入纪律 |
|---|---|
| `audit_uuid` | UUIDv7 |
| `team_uuid` | 可知则填；team-not-registered 可 NULL |
| `actor_kind` / `actor_fingerprint` | 上表 |
| `action` | **闭集表权威=本文 §4.12.2.1**；扩展=S16 change-request |
| `outcome` | `allowed` \| `denied` |
| `http_status` | 若适用 |
| `summary` | 短、无 secret |
| `payload_json` / `payload_digest` | 消毒后 JSON + digest |
| `remote_addr_hash` | 可选 `H(ip)`；政策可禁存 |

#### 4.12.3 Redaction 权威

**永不出现在** event / diagnostic / metric label / alert / 对外 error：  
token 原文、password、API key、Authorization 头值、**X-MKB-Internal-Token 头值**、预签名 URL、prompt 全文、向量全文、绝对 path、连接串、内部 stack/SQL（受控诊断面除外）。

**允许**：fingerprint、handle、digest、枚举 code、有界 uuid、截断 summary。

实现：统一 `RedactionMiddleware` + schema 拒绝（升级 legacy Authorization redact）。

#### 4.12.4 v1 OOS 闭包

- 完整 IdP / OAuth / OIDC 登录产品  
- 细粒度 end-user RBAC / 权限中台  
- 公网多租户 SaaS 加固作为产品范围  
- Team API key 授权模型 / membership / plan / phone gate  
- Webhook/callback secret 默认设施  
- Console UI 安全运营中台 / 任意 file-debug  
- 强制 Vault/KMS 唯一后端  
- 强制传输 nonce 签名协议  
- 完整 SBOM/attestation SaaS  
- Agent authoring 安全产品面  
- Answer-generation 密钥面  
- 用 `team_uuid` 或 `user_uuid` 当授权凭证  

**执行台账**

1. 实现 `SecurityAuditWriter`；admission deny 路径强制调用。  
2. 注入测试：audit INSERT 失败 → 5xx，业务行不存在。  
3. 采样器实现 + metric 对照。  
4. Redaction 单测：fixture 含 Authorization 不出现在序列化输出。  
5. `SEC_*` 与 S02 envelope 映射表单测。  
6. OOS 清单 architecture 扫描（禁 OAuth route、禁 proxy 开放路由）。

**小结**：可观测拒绝 + 不泄漏 secret + 范围不平台化。

---

### 4.13 配置键台账（ops knobs · 不进 binding_digest）

| 键 | 默认 | 说明 |
|---|---|---|
| `security.token.overlap_hours` | **24** | dual-active 重叠窗 |
| `security.token.max_active` | **2** | ActiveTokenSet 上限 |
| `security.rate_limit.token_per_min` | **600** | per-token |
| `security.rate_limit.ip_per_min` | **120** | per-IP |
| `security.rate_limit.window_seconds` | **60** | 固定窗口 |
| `security.rate_limit.enabled` | **true** | 总开关（关须告警） |
| `security.metrics.require_token` | **false** | scrape bearer |
| `security.ready.require_token` | **false** | ready 可选 token |
| `security.egress.max_redirects` | **3** | redirect 预算 |
| `security.egress.allow_literal_ip` | **false** | 字面 IP |
| `security.egress.allow_private_default` | **false** | 默认拒 RFC1918 |
| `security.audit.invalid_token_sample_per_ip_per_min` | **10** | 采样上限 |
| `security.debug.filesystem_enabled` | **false** | 生产强制 false |
| `security.alert.deny_spike_threshold_per_min` | **legacy/镜像 only** | **阈值 SSOT = S15 `obs.alert.security_deny_spike_per_min`** |
| `security.egress.profile` | `default` | `default`\|`internal_only`；默认 default；启 internal_only 须 audit |
| `security.token.last_good_max_age_hours` | **72** | last-good 超龄策略 |
| `security.secret.last_good_max_age_hours` | **72** | secret map 超龄 |
| `security.audit.rate_limited_sample_per_ip_per_min` | **10** | 429 audit 采样 |
| `security.audit.egress_denied_sample_per_ip_per_min` | **10** | egress deny 采样 |

---

### 4.14 安全 Metric 钩子（**已同步 S15-E03 闭集** · 导出唯一路径=S15 MetricRegistry）

| 逻辑名（= 导出名） | 类型意图 | labels |
|---|---|---|
| `mkb_sec_auth_total` | counter | `result`∈missing\|invalid\|ok |
| `mkb_sec_rate_limited_total` | counter | `dim`∈token\|ip |
| `mkb_sec_rate_limiter_degraded` | gauge 0/1 | — |
| `mkb_sec_egress_denied_total` | counter | `reason` 短闭集 |
| `mkb_sec_secret_unresolved_total` | counter | — |
| `mkb_sec_audit_write_fail_total` | counter | — |
| `mkb_sec_token_reload_total` | counter | `result`∈ok\|fail\|last_good |
| `mkb_sec_supply_reject_total` | counter | `code` 短闭集 |

禁止：token 明文、完整 URL、uuid 任务级 label。**禁止** S16 另起第二 metric registry。

---

## 5. 事实反例 + 风险台账

### 5.1 Legacy 反模式（必须删除/改写）

| ID | 反模式 | 锚点（legacy-family） | MKB 禁令 |
|---|---|---|---|
| **N-01** | JWT 承载 user+team+role+plan 授权 | `smind-admin/services/auth.ts` | 禁平台 claims token |
| **N-02** | Team API Key 当租户凭证 | `auth.ts` / `team.ts` / console middleware | 全局 token + team 寻址 |
| **N-03** | login/register/password 用户平台 | admin/console auth | OD-01 删除 |
| **N-04** | 公开 `/api/proxy` 任意 URL | `proxy.ts` + middleware 白名单 | 禁 open proxy |
| **N-05** | safeFetch 过窄/缺私网拒 | `safe-fetch.ts` | 升格 egress 宪法 |
| **N-06** | URL 摄入无 host 策略 | `ingestion/urls.ts` | S05+S16 |
| **N-07** | cleaner 任意 source_url | `cleaner_web.ts` | 技能内不得绕过 egress |
| **N-08** | `source_name` 可选假隔离 | `internal_retrieve.ts` | 强制 team + dual-fence |
| **N-09** | `user_uuid` 向量 filter 假隔离 | `topK.ts` | 禁 user≠team 冒充 |
| **N-10** | membership/plan/phone gate | `ingestion/apis.ts` | 禁商业门闸 |
| **N-11** | 限流 KV 故障不透明放行 | middleware | 显式 degraded |
| **N-12** | 合成用户 `apikey-system` | middleware | actor_kind 闭集 |
| **N-13** | console debug/restart 泄 payload | `files/debug/*` | 无中台；E10 |
| **N-14** | R2 path/key 进协议 | skills r2 / cms-media | handle only |
| **N-15** | 多 Worker 密钥碎片 | 各 JWT_SECRET | 单体统一 admission |
| **N-16** | 「有 JWT=有安全」 | family 分散 | 完整 TM |

### 5.2 正向原型（升级吸收）

| ID | 原型 | MKB 升级 |
|---|---|---|
| P-01 | API key 存 SHA-256 | token 指纹 + actor_fingerprint |
| P-02 | 创建只展示一次 | ops mint 交付一次 |
| P-03 | timing-safe compare | TokenAuthenticator 强制 |
| P-04 | https + allowlist + timeout | EgressPolicy + 硬拒网段 |
| P-05 | Authorization 日志脱敏 | Redaction 全路径 |
| P-06 | 模型 key 来自 env | SecretResolver + S14 L2 |
| P-07 | SQL `team_uuid=?` | 强制 repository 围栏 |
| P-08 | IP 固定窗限流直觉 | token+IP 双维 |
| P-09 | 未授权统一 401 | 业务面无 side effect |
| P-10 | 结构化 denial log_code | security_audit + SEC_* |

### 5.3 硬禁清单（实现/验收）

1. 完整 IdP/OAuth/OIDC/session/refresh 用户平台  
2. 细粒度 end-user RBAC / 权限中台 / plan·phone gate  
3. `team_uuid` 或 `user_uuid` 当作授权凭证  
4. Team API key → team 授权模型  
5. 公网匿名业务写面 / open proxy / 公网 object API / 公网 metrics marketplace  
6. Webhook/callback secret 默认设施  
7. silent model/adapter swap  
8. log-as-business-SSOT；security_audit 并入 domain_events  
9. 引用 `context/legacy-specs/**` / `legacy-python/**` / `legacy-python-2/**`  
10. dual SSOT：以 QNA 作执行权威  
11. 生产 file-debug / 路径读盘 API  
12. secret 进 git/DB/log/metric label  

### 5.4 风险台账

| ID | 风险 | 等级 | 缓解 |
|---|---|---|---|
| `S16-R01` | 多副本限流有效值 ×N | P2 | 文档残差；后续共享计数器非强制 |
| `S16-R02` | env secret 进程泄漏 | P2 | 部署权限；可选 file 0600；禁 core dump |
| `S16-R03` | `/ready` 免 token 信息探测 | P3 | 内网 + 低明细 code |
| `S16-R04` | 高 QPS invalid audit 爆表 | P2 | 采样 S16-T055 + metric 全量 |
| `S16-R05` | 合法内网源被默认拒 | P3 | 显式 `internal_only` profile |
| `S16-R06` | valid token 被误当 team-scoped token | P1 | S16-A02；文档+测试 |
| `S16-R07` | 公网暴露后威胁模型不足 | P1 | OOS；须 reopen HMAC/nonce/mTLS 产品 |
| `S16-R08` | audit 失败被吞 → silent deny | P0 | 5xx fail-closed S16-T053 |
| `S16-R09` | DNS rebinding 实现遗漏 | P1 | 验收 connect 前 IP 校验 |
| `S16-R10` | 限流器故障被当鉴权失败 | P2 | 故障分账：限流 open / 鉴权 closed |

---

## 6. 测试与验收台账

> **纪律**：下列为 **必须具备的验收设计与证据类型**；本文件 **不** 伪称已交付 CI 绿测。实现阶段补自动化。

### 6.1 HARD invariants

| ID | 不变量 |
|---|---|
| H-01 | 业务 endpoint 无/错 token → 401；且不读 team/task 存在性用于差异化响应枚举 |
| H-02 | `team_uuid` 不授予权限；team-scoped 查询仍强制 |
| H-03 | denied admission → security_audit 行（或合法聚合采样）存在；admission audit 失败 → 5xx |
| H-04 | secret/token 明文不出现在 log/event/audit payload/metric label |
| H-05 | egress 拒 metadata/link-local/默认私网；DNS 后校验 IP |
| H-06 | 生产 debug 任意读盘关闭 |
| H-07 | 未绑定 binding 的模型出站失败；无 silent swap |
| H-08 | security 事件不写 domain_events |
| H-09 | ActiveTokenSet 空 → ready 失败；业务不放行 |
| H-10 | 实现仅依赖本 domain-truth，不依赖 QNA 条款 |

### 6.2 验收用例矩阵

| ID | 类 | 场景 | 期望 |
|---|---|---|---|
| `S16-A01` | API | 无 token 调 Task Create | 401 `SEC_TOKEN_MISSING`；无业务行；可 audit |
| `S16-A02` | API | valid token + 任意已注册 team | 无 membership gate；按资源状态处理 |
| `S16-A03` | API | invalid token + 存在的 task_uuid | 401；**不**因资源存在返回不同 body 枚举 |
| `S16-A04` | Token | dual-active 两指纹 | 两者均可 200 |
| `S16-A05` | Token | revoke previous | 旧 401；新 200；audit 有 revoke |
| `S16-A06` | Token | timing-safe 单测 | 固定时间比较路径存在 |
| `S16-A07` | Header | Bearer 优先于 X-header | 冲突时以 Bearer 为准 |
| `S16-A08` | Rate | 超 token/IP 配额 | 429 `SEC_RATE_LIMITED`；无业务行 |
| `S16-A09` | Rate | 限流器故障注入 | 请求仍可走鉴权；degraded metric=1 |
| `S16-A10` | Audit | audit 写失败注入 | 5xx `SEC_AUDIT_WRITE_FAIL`；无业务行 |
| `S16-A11` | Audit | invalid-token 洪水 | metric 上升；audit 行受采样上限 |
| `S16-A12` | Egress | URL=`http://169.254.169.254/` | `SEC_EGRESS_DENIED` |
| `S16-A13` | Egress | redirect 链至私网 | `SEC_EGRESS_REDIRECT_DENIED` 或 DENIED |
| `S16-A14` | Debug | 生产 profile 调 file-debug | `SEC_DEBUG_DISABLED` |
| `S16-A15` | Redact | 日志含 Authorization | 输出为 redacted |
| `S16-A16` | Path | 错误路径含绝对 path | 对外 envelope 无绝对 path |
| `S16-A17` | Isolation | 缺 team 的检索 | fail-closed（邻域+SEC_TEAM_SCOPE） |
| `S16-A18` | Supply | 任意 base_url override | `SEC_MODEL_ENDPOINT_REJECTED` / UNBOUND |
| `S16-A19` | Probe | `/live` 无 token | 200；无 secret |
| `S16-A20` | Probe | 空 ActiveTokenSet `/ready` | 503；`sec_token_loaded` 失败 |
| `S16-A21` | Metrics | 模拟公网匿名策略 | 部署文档禁止；可选 bearer 可测 |
| `S16-A22` | Secret | 未知 slot | `SEC_SECRET_UNRESOLVED` |
| `S16-A23` | Replay | 幂等 Create 重放 | 同业务结果（S01/S02）；非新 SSOT 表 |
| `S16-A24` | OOS | 不存在 OAuth login 路由 | architecture 扫描通过 |

### 6.3 证据类型（非伪交付）

- 单元：token compare、redaction、egress CIDR、采样器。  
- 集成：admission 序、audit 行、401 先于资源（DB spy）。  
- Architecture：禁 open proxy；禁 secret 进 git config；中间件挂载。  
- 运维 runbook：轮换/吊销/泄漏响应（文档证据）。

---

## 7. Reference-anchor 台账

### 7.1 Legacy-family 文件锚点

| 锚点 ID | 路径（相对 `context/legacy-family/`） | 关系 | 处置 |
|---|---|---|---|
| RA-01 | `smind-admin/services/auth.ts` | JWT/API key/hash | **rewrite**：仅保留 hash/timing-safe 思想；删平台 JWT |
| RA-02 | `smind-admin/services/team.ts` | team API key 产品 | **delete** 授权模型；**retain** 展示一次思想 |
| RA-03 | `smind-console/functions/api/_middleware.ts` | ACL/限流/公网白名单 | **rewrite** 限流；**delete** 双轨 JWT+APIKey 平台 |
| RA-04 | `smind-console/functions/api/proxy.ts` | open proxy | **delete** |
| RA-05 | `smind-console/functions/lib/core/safe-fetch.ts` | https+allowlist | **retain→upgrade** 至 EgressPolicy |
| RA-06 | `smind-admin/ingestion/urls.ts` | URL 无 SSRF | **rewrite** via S05+S16 |
| RA-07 | `smind-skill-clean-universal/services/cleaner_web.ts` | 任意 URL 渲染 | **rewrite** 强制 egress |
| RA-08 | `smind-contexter/rag/internal_retrieve.ts` | source_name 假隔离 | **delete** 可选租户 filter |
| RA-09 | `smind-contexter/ai/topK.ts` | user_uuid filter | **delete** |
| RA-10 | `*/cloudflare_ai/ai_gateway.ts` | Authorization redact | **retain→upgrade** 全路径 redaction |
| RA-11 | `smind-console/functions/api/files/debug/*` | debug 泄密 | **delete** 产品面 |
| RA-12 | skills `core/r2.ts` / cms-media | path 进协议 | **delete** path wire；S13 handle |

### 7.2 Web Reference-Check（设计对照 only · 不覆盖 D\*/S\*）

| XR | 主题 | 对照用途 |
|---|---|---|
| XR-01..05 | API key hash / timing-safe / keys vs OAuth | 支持 E03；拒 JWT 平台 |
| XR-06..08 | rotation overlap | 支持 E04 dual-active |
| XR-09..11 | K8s probes / Prometheus security | 支持 E05 分级 |
| XR-12..13 | rate limit token+IP / fail-open | 支持 E06 |
| XR-14..16 | Idempotency vs HMAC nonce | 支持 E07；公网 OOS |
| XR-17..19 | OWASP SSRF / DNS rebinding | 支持 E08 |
| XR-20..21 | 12-factor env / env 风险 | 支持 E09 |
| XR-22..23 | 生产禁 debug / logging | 支持 E10/E12 |
| XR-24..27 | AI supply chain / namespace reuse | 支持 E11 |
| XR-28..31 | A09 audit / RFC 9457 / path traversal | 支持 E12 |

> 完整 URL 冻结表见 `qna-truth/S16.md` §7（证据层）；执行不依赖打开 QNA。

### 7.3 处置汇总

| 处置 | 含义 |
|---|---|
| **retain** | 思想可升级吸收 |
| **rewrite** | 结构保留问题域但语义改写 |
| **delete** | 禁止进入 MKB 产品/运行时 |

---

## 8. Domain verdict

### 8.1 GO / ACCEPTED 标准

当且仅当：

1. 本文九节齐全；E01–E12 可编码；  
2. `T-O-312..336` 全部映射到 `S16-Txxx` 与执行包；  
3. 关键不变量可验收：token 401 序、team≠auth、SSRF 硬拒、secret 不进 log、denied 必 audit；  
4. 无 dual SSOT；QNA 降为证据；  
5. 邻域分账无吞并 S01 权限口径 / S05 descriptor / S15 retention / D04 DDL；  
6. OOS 闭包阻止平台回潮。

**Verdict：`accepted / S16-v1.1 / GO for domain implementation`**

### 8.2 残差 OOS / 已知残差

| 项 | 状态 |
|---|---|
| 公网暴露 + HMAC/nonce/mTLS 产品化 | **OOS**（须 reopen） |
| 多副本限流共享计数器 / Redis | **v1 非强制**；×N 残差 accepted |
| Vault/KMS 唯一后端 | **可选扩展**；非 v1 强制 |
| 完整 SBOM/signing SaaS | **OOS** |
| IdP/OAuth/end-user RBAC | **OOS** |
| 默认 600/120 压测商业 SLA | **非 SLA**；ops knob |
| Progressive Round / second-opinion | **waived** |

### 8.3 下游约束

| 下游 | 约束 |
|---|---|
| **S01** | 保持 T046；载体/轮换/限流实现服从本文 |
| **S02** | envelope 禁 token/path；rate 语义 429 对齐 SEC_* |
| **S05** | 出站必须调 EgressPolicy；secret 仅 ref |
| **S10/S11** | team 强制；SupplyFence；无假隔离 |
| **S13** | handle-only；错误无 path；无公网 object |
| **S14** | L2 注入；binding 身份 exact；禁 catalog 明文 key |
| **S15** | retention 180d；operator 内网+token；redaction 执行；可选 DENY_SPIKE |
| **17/18** | 拓扑与验收继承 security surfaces 与 HARD invariants |
| **实现** | 仅以本文为 SSOT；architecture tests 覆盖 H-01..H-10 |

### 8.4 前向校准（provisional · 不 reopen 邻域）

- S14 formal 已接受：secret 值 L2 与本文 E09 对齐；registry resolve 仍须 token。  
- S15 formal 已接受：operator/repair 形状与 E05/E10 对齐；security_audit 写入以本文为准。  
- 若未来公网暴露：同时 reopen S16 replay + endpoint 矩阵 + 可能 S02 envelope，不静默加功能。

---

## 9. 修订历史

| 版本 | 日期 | 状态 | 作者 / 裁决 | 说明 |
|---|---|---|---|---|
| `S16-v1.1` | `2026-08-12` | `accepted` | `MKB owner + Grok workflow domain-truth-s14-s16` | 对抗评审：采样扩展 rate-limit/egress；EndpointClass 限流矩阵；action 闭集表；internal_only ops；last-good TTL；X-header redaction；S15 metric/alert 同步；多副本验收 |
| `S16-v1.0` | `2026-08-12` | `accepted` | `MKB owner + Grok workflow domain-truth-s14-s16` | 正式执行 SSOT：映射 `T-O-312..336` → `S16-T001..T070`；E01–E12；TM-01..10；`SEC_*`；security_audit 写语义；redaction；endpoint 矩阵；egress 宪法；SecretResolver；SupplyFence；OOS 闭包。QNA `v1.0-qna-locked` 降为证据层。second-opinion waived；workflow-frozen RC-adjusted B+Δ1–Δ10。Header 主路径 `Authorization: Bearer`；固定窗口限流；audit 采样默认 10/IP/min。关 G-02/G-10 服从；不 reopen 邻域。 |

---

## 附录 A · T-O ↔ S16-T ↔ E 包速查

| T-O | S16-T（主） | E 包 |
|---|---|---|
| T-O-312..326 | T001..T015 | E01 |
| T-O-336 (TM) | T057 | E02 |
| T-O-327 | T016..T020 | E03 |
| T-O-328 | T021..T025 | E04 |
| T-O-329 | T026..T032 | E05 |
| T-O-330 | T033..T035 | E06 |
| T-O-331 | T036..T037 | E07 |
| T-O-332 | T038..T043 | E08 |
| T-O-333 | T044..T046 | E09 |
| T-O-334 | T047..T048 | E10 |
| T-O-335 | T049..T050 | E11 |
| T-O-336 | T051..T070 | E12 |

## 附录 B · 邻域引用速查

| 主题 | 主引用 |
|---|---|
| 简单 token 权限口径 | S01-T046；S01-E09 |
| team≠credential | OD-04；S02-T032；S16-T003 |
| security_audit 表 | D04 §3.1.5；S16-T005/T052 |
| secret-ref / SSRF | S05；S16-E08/E09 |
| path/handle | S13；S16-T008 |
| dual-fence | S10；S16-T009 |
| redaction | S02-T038；S15-T025；S16-T056 |
| G-10 silent swap | G-10；S16-T012/T050 |
| operator 面 | S15-T022；S16-E05/E10 |

## 附录 C · Admission 伪序（实现必遵）

```text
on_request(req):
  classify EndpointClass
  if class in {Live}:
    return live_handler()  # no token; no deps
  if class == Ready and not security.ready.require_token:
    return ready_handler()  # includes sec_token_loaded
  if class == Metrics and not security.metrics.require_token:
    assert_internal_network(); return metrics_handler()

  rate_limit_ip(req)           # may 429
  token = extract_token(req)   # Bearer primary
  if token is None: audit_denied(MISSING); return 401
  if not active_set.verify_timing_safe(token):
      audit_denied_sampled(INVALID); return 401
  rate_limit_token(token)      # may 429
  actor = {kind: internal_token, fp: H(token)}

  # then S01/S02 schema → team active → team-scoped business
  # never read resource existence before token validity for Business class
```

---

**文件结束 · S16-v1.1 accepted · 执行 SSOT**
