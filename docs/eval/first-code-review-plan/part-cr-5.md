# Nano-Agent 代码审查报告 — CR-5 · 控制面 (Control Plane)

> 审查对象: `CR-5 控制面 (auth / team / ingestion / management + apps/api)`
> 审查类型: `code-review`
> 审查时间: `2026-05-31`
> 审查人: `Claude sub-agent (CR-5)`
> 审查范围:
> - `packages/auth/src/auth/service.py`（密码哈希 / 会话 / 无 API key 校验，112 行）
> - `packages/team/src/team/service.py`（团队 bootstrap / 成员 / 选队，54 行）
> - `packages/ingestion/src/ingestion/service.py`（file / url / api / static 四类入口，217 行）
> - `packages/management/src/management/service.py`（列表 / 详情 / search / restart / purge / health，160 行）
> - `apps/api/src/smind_api/{deps,main}.py` + `routes/{auth,me,team,ingestion,management,search,ops,workflow_config}.py`
> 对照真相:
> - `legacy-family/smind-admin/services/{auth,user,team,password,workflow}.ts`
> - `legacy-family/smind-admin/ingestion/{files,urls,apis}.ts`
> - `legacy-family/smind-admin/management/{list,static,apis_registry}.ts`
> - `legacy-family/smind-admin/src/index.ts`（RPC 路由总表，20 个 RPC）
> - `docs/refactor/core.sql`（SSOT schema）、`docs/eval/first-code-review-plan/index.md`（B/D/L 口径 + C1–C5 + §7 owner 口径）
> 文档状态: `changes-requested`

---

## 0. 总结结论

- **整体判断**：控制面 CRUD 骨架成立、team 隔离在查询层基本到位、三类 ingestion 真实创建出可被 worker claim 的 `stage='clean'` step（**附录 A1 在 CR-5 创建侧证伪——不是断点**）；但**团队 API key 认证链路整簇缺失（盲点 B + 认证断点 D）**，且承接了 CR-3 路径遍历的**未校验源头**（`filename` 直拼 object_key），密码哈希算法与 legacy 不兼容（"legacy 兼容"声称不成立）。
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. **api_keys 表零访问 = 真盲点 B + 认证断点 D（裁决：缺失成立，但严重度 high 非 critical）**：legacy 有独立的 `validate_api_key` / `create_api_key` RPC 与 `findTeamByApiKeyHash` 全链路（machine-to-machine 认证），Python 侧 `api_keys` 表仅存在于 DDL，无任何读写代码，对外 API（`ingestion/apis/submit` 等）当前**只能用用户会话 token**，外部系统集成认证能力整体缺失。
  2. **路径遍历源头收口缺失（security，与 CR-3 G-CR3-01 联动）**：`FileInitiateBody.filename`（HTTP body，零校验）→ `ingestion/service.py:17` `object_key = f"raw/{team_id}/{upload_id}/{filename}"`，控制面未做 basename/校验纵深防御，是 G-CR3-01 任意文件读写的**注入入口**。
  3. **密码哈希与 legacy 不兼容（L）**：Python 用 `pbkdf2_sha256` + sha256 legacy fallback；legacy 用 `hmac-sha512:salt:hash`。所谓"legacy 兼容"分支（`_hash_legacy_password` = 裸 sha256）**与 legacy 真实格式不符**，legacy 用户密码迁移后全部无法登录。

---

## 1. 审查方法与已核实事实

- **对照文档**：
  - `docs/eval/first-code-review-plan/index.md`（B/D/L + C1–C5 + §7 owner 口径）
  - `docs/eval/smind-family-strucure-analysis-by-GPT.md` §3.2（20 个 RPC 路由表）
  - `docs/refactor/core.sql`（23 表 / 11 视图 SSOT）
- **核查实现**：上列 4 个 service.py + `apps/api` 全部 10 个 py 文件，逐行读取。
- **legacy 取证**：`services/auth.ts`(285)、`team.ts`(268)、`workflow.ts`(207)、`user.ts`、`password.ts`、`ingestion/files.ts`(568)、`urls.ts`、`apis.ts`、`management/{list,static}.ts`、`src/index.ts`(340，RPC 路由总表)。
- **执行过的验证**：
  - `grep -rn "api_key|api_keys|key_hash|validate_api_key" packages/ apps/` → 仅命中 `migrations/core.sql`（DDL），**业务代码零命中**，确认 api_keys 表零访问（独立复现 G-CR2-03）。
  - 逐列比对 ingestion/management 裸 SQL 与 `core.sql` 的 uploads/sources/documents/static_files/workflow_runs/workflow_steps/configs 列名与 CHECK 约束 → 全部匹配（无列名/占位符/约束违例）。
  - 核对 worker 派发：`apps/worker/main.py:47` `step["stage"].startswith("clean")` ↔ ingestion `service.py:208` 创建 `stage='clean'` → **匹配，可路由**；`workflow_clean/service.py:106` 创建 `stage='rag:structurize'` ↔ `main.py:49` `startswith("rag:")` → **匹配**。附录 A1 在 CR-5 创建侧证伪。
  - 核对 `workflow_steps.stage` 在 `core.sql:257` **无 CHECK 约束** → `'clean'` 可合法插入。
- **复用 / 对照的既有审查**：
  - `G-CR2-03`（api_keys 等 4 表零访问）— **独立复核并采纳**，本簇负责认证断点归属裁决。
  - `G-CR3-01`（object_key 零校验路径遍历）— **采纳为源头链证据**，本簇补记控制面未做纵深防御 finding。
  - `G-CR1-01 / G-CR4-02`（时间格式缺秒）— 作为线索核对本簇是否传播：**ingestion/auth/team/management 全部用 `strftime('%Y-%m-%dT%H:%M:%fZ','now')` 或依赖 DDL DEFAULT，未传播该 bug**（见 1.1）。

### 1.1 已确认的正面事实

- **三类 ingestion（file/url/api）均为真实现**，都创建 source + document + workflow_run + workflow_step（`stage='clean'`），并真正投递出可被 worker `claim_one()` 捞取的 step（`ingestion/service.py:83-123,183-217`）。**附录 A1 在创建侧不成立**：ingestion 写 `stage='clean'`（无冒号），worker `startswith("clean")`（无冒号），匹配。
- **time 格式未被 G-CR1-01 污染**：本簇所有写时间处用 SSOT 一致的 `strftime('%Y-%m-%dT%H:%M:%fZ','now')`（`auth/service.py:77,94,104,107`、`team/service.py:20`、`ingestion/service.py:58`、`me.py:36`），或走 DDL DEFAULT。
- **team 隔离在查询层强制**：management 所有查询（`list_workflows`/`get_workflow`/`list_documents`/`get_document`/`list_static_files`/`get_static_file` 及 v_active_claims/v_restart_backlog/v_purge_backlog）均带 `WHERE team_id = ?`；ingestion 的 `file_confirm`/`static_confirm` 用 `WHERE id=? AND team_id=?` 防跨 team 确认。
- **鉴权依赖挂载完整**：除公开的 `/auth/register`、`/auth/login` 外，所有路由均 `Depends(get_auth_context)`；所有 team 资源路由（ingestion/management/search/ops）均额外 `require_team(ctx)`。`/healthz` 无鉴权属合理。
- **密码校验本身实现正确**：`_verify_password` 用 `hmac.compare_digest` 常量时间比较，PBKDF2 参数解析有 try/except 防注入，登录成功对 legacy 格式做透明 rehash 升级（`auth/service.py:67-71`）。
- **会话过期校验正确**：`validate_session` 用 SQL 侧 `strftime` 比较 `expires_at`，过期则惰性置 `expired`（`auth/service.py:84-112`），不受 Python 时间格式 bug 影响。
- **裸 SQL 本身全部正确**：列名、占位符数量、team_id 过滤逐条核对无误（不重复 CR-2 "绕过抽象"结论）。

### 1.2 已确认的负面事实

- `api_keys` 表在整个 Python 代码库（packages + apps）**零读写**；无 `validate_api_key`、无 `create_api_key`，对外 API 集成无独立认证。
- `ingestion/service.py:17` `object_key = f"raw/{team_id}/{upload_id}/{filename}"` 中 `filename` 直接来自 `FileInitiateBody.filename`（`routes/ingestion.py:18`，HTTP body，无任何 basename/字符校验）。
- `auth/service.py:17-18` `_hash_legacy_password` = 裸 `sha256(password)`，与 legacy `auth.ts:59-66` 真实格式 `hmac-sha512:salt:hash` **不一致**；"legacy 兼容" claim 不成立。
- legacy 20 个 RPC 中：`user/reset_password`、`team/create_api_key`、`auth/validate_api_key`、`workflow/update`、`management/static_files/delete` 共 **5 个在 Python 无对应实现**（详见 §3.2 矩阵）。
- `management.restart_workflow` / `purge_document` 用确定性 request_id（`restart_{run_id}` / `purge_{doc_id}`），二次调用 PK 冲突（已由 CR-4 记为 G-CR4-06，本簇复现确认入口在此）。
- 路由层异常处理薄弱：service 抛 `ValueError("invalid credentials")` / `ValueError("upload not found")` 未被路由捕获转 4xx，将冒泡为 **500**（`routes/auth.py:31`、`routes/ingestion.py:68`）。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | 全部 14 个 in-scope 文件逐行读 + legacy 11 个 TS 文件取证 |
| 本地命令 / 测试 | `yes` | grep 全仓搜 api_key 用法、stage 匹配核对、SQL 列名对照 core.sql |
| schema / contract 反向校验 | `yes` | 逐列比对裸 SQL ↔ core.sql 23 表 DDL/CHECK |
| live / deploy / preview 证据 | `no` | 未起 API/worker 实跑（依赖 CR-8 端到端） |
| 与上游 design / QNA 对账 | `yes` | 对账 legacy RPC 路由表 + index.md B/D/L/C1–C5/§7 口径 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | 团队 API key 认证整簇缺失（api_keys 零访问） | high | B+D / security | yes | 实现 api_key 校验中间件 + create_api_key，或 owner 显式声明 deferred |
| R2 | 路径遍历源头未收口（filename 直拼 object_key） | high | B+security / 联动 CR-3 | yes | 控制面对 filename 做 basename + 白名单校验（纵深防御） |
| R3 | 密码哈希与 legacy 不兼容，"legacy 兼容"claim 不成立 | medium | L / correctness | no | 修正 fallback 为 hmac-sha512 解析，或声明不迁移 legacy 密码 |
| R4 | 5 个 legacy RPC 在 Python 缺失（reset_password/update_workflow/static delete 等） | medium | B / scope-drift | no | 按需补实现或 owner 标记 deferred |
| R5 | service 层 ValueError 未映射 HTTP 状态码 → 500 | medium | L / correctness | no | 路由捕获业务异常映射 401/404/409 |
| R6 | 确定性 request_id 致二次 restart/purge PK 冲突 | medium | L / correctness | no | 复用 G-CR4-06：随机 id 或 ON CONFLICT（CR-4 own） |
| R7 | file/static confirm 缺 uploader 归属校验 + 状态机校验 | low | L / security | no | 增加 uploader_uuid 校验与重复 confirm 幂等保护 |
| R8 | `static_initiate` 冗余写 + `static_confirm` 不创建 workflow_run | low | B / correctness | no | 核对 static 语义是否应触发流程，去除死写 |

---

### R1. 团队 API key 认证整簇缺失（api_keys 表零访问）

- **严重级别**：`high`
- **类型**：`B（盲点）+ D（认证断点）/ security`
- **是否 blocker**：`yes`
- **事实依据**：
  - `grep -rn "api_key" packages/ apps/` 仅命中 `migrations/core.sql:54-70`（DDL）与 `:435`（audit actor_type）；业务代码零命中（独立复现 G-CR2-03）。
  - legacy `services/auth.ts:218-253 handleValidateApiKey` + `core/db.ts findTeamByApiKeyHash`：完整的 `sm_` 前缀 → sha256 hash → 查 team → 校验 active 链路。
  - legacy `services/team.ts:180-268 handleCreateTeamApiKey`：owner 权限校验 + `generateApiKey()` + `upsertTeamApiKey`，是 api_keys 表的写入侧。
  - legacy `src/index.ts:174,190`：`auth/validate_api_key`、`team/create_api_key` 两个独立 RPC。
  - Python `apps/api/deps.py:53-68 get_auth_context`：**仅支持** `Bearer <session_token>`，无 api_key 分支；`auth/service.py` 无任何 api_key 方法。
- **为什么重要**：
  - legacy 设计 api_keys 用于**机器对机器集成认证**（`ingestion/apis/submit` 等外部系统投递场景）。Python 侧外部集成方目前**只能持有用户会话 token**，无法用长期 API key——这是对外能力的实质缺失，且 `audit_logs.actor_type` 预留了 `'api_key'` 枚举值印证设计意图。
- **审查判断**：
  - **裁决：盲点 B 成立 + 认证断点 D 成立**。归属本簇（认证断点簇）。
  - **严重度定为 high 而非 critical**：当前所有端点仍被 session-token 强制鉴权（无未鉴权敏感端点），不构成"鉴权可绕过"的 critical 漏洞；缺的是一类认证**方式**，非鉴权失效。区分事实与推断：是否属于本轮必须交付取决于 owner 是否将"外部 API 集成"纳入 MVP——**需 owner 决策**。
- **建议修法**：
  - 实现 `AuthService.validate_api_key(raw_key)`：`sm_` 前缀检查 → sha256 → 查 `api_keys WHERE key_hash=? AND status='active'`（可选 expires_at 校验）→ 返回 team_id；在 `get_auth_context` 增加 `X-Api-Key` / `Authorization: ApiKey` 分支构建 AuthContext。
  - 实现 `team/create_api_key`（owner 角色校验，对齐 legacy `team_members.role`）。
  - 若 MVP 不含外部集成，请 owner 在 plan 中**显式登记为 deferred**，避免长期隐性盲点。

### R2. 路径遍历源头未收口（filename 直拼 object_key）

- **严重级别**：`high`
- **类型**：`B（纵深防御缺失）+ security / 联动 CR-3 G-CR3-01`
- **是否 blocker**：`yes`
- **事实依据**：
  - `routes/ingestion.py:17-19 FileInitiateBody.filename`：纯 `str`，无 `pattern`/校验。
  - `ingestion/service.py:17`：`object_key = f"raw/{team_id}/{upload_id}/{filename}"`，`filename` 原样拼接。
  - 下游 `storage_objects/filesystem_store.py:11-20`（CR-3 G-CR3-01）：object_key 零校验，`../` 与绝对路径双逃逸 → 任意文件读写 + 跨 team 越权。
- **为什么重要**：
  - CR-3 已确认存储层是漏洞落点，但**注入入口在本簇**：攻击者 `POST /ingestion/file/initiate {"filename": "../../../../etc/passwd"}` → object_key 被污染 → confirm 时 `put_text` 写任意路径。纵深防御原则下，控制面**必须**在入口收口，不能仅依赖存储层（且存储层当前也没收口）。
- **审查判断**：
  - **裁决：security finding 成立，本簇应做收口**。事实：filename 完全未经校验进入路径构造。这是 G-CR3-01 的可达性证明——确认该路径遍历**真实可由 HTTP 触发**，非理论风险。
- **建议修法**：
  - `file_initiate` 中 `filename = os.path.basename(filename)` 并拒绝空/含 `/`/`\`/`..` 的值；或在 `FileInitiateBody` 加 `pydantic` 校验（`pattern=r'^[\w.\- ]+$'`）。`static_confirm` 的 `path` 同理（虽不进 object_key，但作为 title/canonical_uri 仍应清洗）。
  - 与 CR-3 协同：存储层 basename 收口为最终防线，控制面校验为第一道。

### R3. 密码哈希与 legacy 不兼容，"legacy 兼容"claim 不成立

- **严重级别**：`medium`
- **类型**：`L / correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - Python `auth/service.py:9,17-24`：新哈希 `pbkdf2_sha256$120000$salt$digest`；legacy fallback `_hash_legacy_password` = 裸 `sha256(password).hexdigest()`。
  - legacy `auth.ts:59-66 hashPassword`：`hmac-sha512:${saltHex}:${hashHex}`（HMAC-SHA512 加盐）。
  - `_verify_password:28-29`：非 pbkdf2 前缀时走 `compare_digest(sha256(pw), stored)` —— 永远无法匹配 legacy 的 `hmac-sha512:...` 三段格式。
- **为什么重要**：
  - 若声称兼容 legacy 用户库迁移，则**所有 legacy 用户登录必失败**（格式根本不被解析）。当前 Python 自建用户走 pbkdf2 路径正常，但 fallback 分支是死代码 + 误导性"兼容"语义。
- **审查判断**：
  - **裁决：逻辑错误 L（语义错误，能跑但与 legacy 行为不一致）**。区分事实与推断：纯 Python 新建用户不受影响（推断系统当前可用）；事实是 legacy 兼容分支错误。
- **建议修法**：
  - 若需迁移 legacy 密码：fallback 改为解析 `hmac-sha512:salt:hash` 三段并用 HMAC-SHA512 复算比对（对齐 `auth.ts:92-104 verifyPassword`），登录成功后 rehash 为 pbkdf2。
  - 若不迁移：删除 `_hash_legacy_password` 死分支，避免误导。

### R4. 5 个 legacy RPC 在 Python 缺失

- **严重级别**：`medium`
- **类型**：`B / scope-drift`
- **是否 blocker**：`no`
- **事实依据**（详见 §3.2 矩阵）：
  - `services/user/reset_password`（`password.ts:70 handleResetPassword`）→ Python 无密码重置端点。
  - `services/team/create_api_key`（`team.ts:180`）→ 无（见 R1）。
  - `services/auth/validate_api_key`（`auth.ts:218`）→ 无（见 R1）。
  - `services/workflow/update`（`workflow.ts:113 handleAdminUpdateWorkflow`）→ Python `management` 只读，无 workflow 更新端点。
  - `management/static_files/delete`（`management/static.ts handleDeleteStaticFile`）→ Python management 无 delete，purge 是另一条 ops 路径（语义不同：purge=合规删除 vs static delete=单文件删）。
- **为什么重要**：控制面对外能力面相对 legacy 收窄；reset_password 是常见刚需，缺失影响可用性。
- **审查判断**：
  - **裁决：盲点 B（多项能力缺失）**。部分（api_key 相关）已在 R1 单列为 blocker；其余（reset_password / workflow update / static delete）为 non-blocking scope gap，需 owner 确认是否 MVP 内。
- **建议修法**：按 owner MVP 范围补实现或在 plan 显式标 deferred。

### R5. service 层 ValueError 未映射 HTTP 状态码

- **严重级别**：`medium`
- **类型**：`L / correctness（C2 错误处理）`
- **是否 blocker**：`no`
- **事实依据**：
  - `auth/service.py:66` `raise ValueError("invalid credentials")` → `routes/auth.py:31` 未捕获 → FastAPI 默认 **500**（应 401）。
  - `ingestion/service.py:53,139` `raise ValueError("upload not found")` → 路由未捕获 → 500（应 404）。
  - `management/service.py:83,97` `raise ValueError("vec connection required")` → 500。
- **为什么重要**：登录失败返回 500 而非 401，客户端无法区分"凭据错"与"服务故障"；违反 index.md C2（错误处理）口径。
- **审查判断**：`裁决：逻辑错误 L`。语义错误：业务错误暴露为服务错误。
- **建议修法**：service 抛领域异常（`smind_common.errors`，目前空壳见 G-CR1-05），路由层统一 exception handler 映射；或路由内 try/except 转 `HTTPException`。

### R6. 确定性 request_id 致二次 restart/purge PK 冲突

- **严重级别**：`medium`
- **类型**：`L / correctness`
- **是否 blocker**：`no`（CR-4 own）
- **事实依据**：
  - `management/service.py:136` `request_id = f"restart_{workflow_run_id}"`；`:148` `f"purge_{document_id}"`。
  - 入口在本簇（`routes/ops.py:59,84` → `restart_workflow`/`purge_document`），但 PK 冲突机制已由 CR-4 记为 G-CR4-06（`create_restart_request` 无 ON CONFLICT）。
- **为什么重要**：同一 workflow 重启一次后再次重启 → restart_requests PK 冲突 → 500，永不可再重启。
- **审查判断**：`裁决：逻辑错误 L`，与 G-CR4-06 同根，本簇仅确认 HTTP 入口可触发。
- **建议修法**：复用 CR-4 修法（随机 id 或 ON CONFLICT DO UPDATE）。归 CR-4 own，本簇 cross-ref。

### R7. file/static confirm 缺 uploader 归属与状态机校验

- **严重级别**：`low`
- **类型**：`L / security`
- **是否 blocker**：`no`
- **事实依据**：
  - Python `ingestion/service.py:48-52 file_confirm` 仅 `WHERE id=? AND team_id=?`，无 uploader 校验，无 status 校验（重复 confirm 会重复建 source/document/run）。
  - legacy `files.ts:301` 校验 `uploader_uuid !== auth.user_uuid → FORBIDDEN`；`:307` 校验非 pending 状态 → 幂等返回。
- **为什么重要**：同 team 内任意成员可 confirm 他人 upload；重复 confirm 产生重复 workflow_run（无幂等）。team 内信任模型下风险较低，故 low。
- **审查判断**：`裁决：逻辑错误 L（弱于 legacy 的归属/幂等保护）`。
- **建议修法**：confirm 前校验 `created_by_user_id == ctx.user_id`（或 owner 角色）+ `status='initiated'` 幂等保护。

### R8. static_initiate 冗余写 + static_confirm 不触发 workflow

- **严重级别**：`low`
- **类型**：`B / correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `ingestion/service.py:30-37 static_initiate` 调 `file_initiate` 后又 `UPDATE uploads SET source_kind='file'`——而 `file_initiate` 已写 `'file'`，是**无操作冗余写 + 多余 commit**。
  - `static_confirm:125-181` 建 source/document/static_files 但**不调 `_create_workflow_run`**——静态文件不进入 clean/rag 流程。需确认这是否符合 legacy（legacy `files.ts:86` static_upload 分支确实"跳过工作流"，故此处**可能是有意简化/等价**，但与 file_confirm 行为分裂未注释）。
- **为什么重要**：冗余写无害但是代码异味；static 不触发 workflow 若非有意则是断点。
- **审查判断**：`裁决：盲点 B（语义不清）`。legacy 比对显示 static 确实跳过 workflow（`等价`倾向），但冗余 UPDATE 是确定的无用代码。
- **建议修法**：删除 `static_initiate` 的冗余 UPDATE+commit；为 static_confirm 不建 run 的设计加注释或确认对齐 legacy。

---

## 3. In-Scope 逐项对齐审核

### 3.0 RPC / 能力 parity 矩阵（legacy 20 RPC → Python）

| # | legacy RPC (file:line) | Python 实现 (file:line) | 裁决 |
|---|------------------------|--------------------------|------|
| 1 | `services/auth/login` (`index.ts:170` / `auth.ts:255`) | `routes/auth.py:30` → `auth/service.py:60 login` | **有意简化**（JWT→DB session，语义等价）|
| 2 | `services/auth/register` (`index.ts:172` / `auth.ts:168`) | `routes/auth.py:24` → `auth/service.py:48 register` | **等价**（注册建 user）|
| 3 | `services/auth/validate_api_key` (`index.ts:174` / `auth.ts:218`) | **无** | **盲点B + 断点D**（R1，api_keys 零访问）|
| 4 | `services/user/profile` (`index.ts:178` / `user.ts:76`) | `routes/me.py:16 me` → `SELECT users` | **等价**（me 端点）|
| 5 | `services/user/update` (`index.ts:180` / `user.ts:94`) | `routes/me.py:28 update_me` → `UPDATE users` | **等价**（仅 display_name，legacy 字段更全=部分简化）|
| 6 | `services/user/reset_password` (`index.ts:182` / `password.ts:70`) | **无** | **盲点B**（R4）|
| 7 | `services/team/create` (`index.ts:186` / `team.ts:64`) | `routes/team.py:21 bootstrap` → `team/service.py:11 bootstrap` | **等价**（建 team + owner 成员）|
| 8 | `services/team/info` (`index.ts:188` / `team.ts:146`) | `routes/team.py:33 list` → `list_memberships` | **有意简化**（list 替代单 team info，可覆盖）|
| 9 | `services/team/create_api_key` (`index.ts:190` / `team.ts:180`) | **无** | **盲点B**（R1/R4）|
| 10 | `services/workflow/list` (`index.ts:194` / `workflow.ts:86`) | `routes/management.py:17 list_workflows` → `list_workflows` | **等价** |
| 11 | `services/workflow/update` (`index.ts:196` / `workflow.ts:113`) | **无** | **盲点B**（R4，无 workflow 更新）|
| 12 | `ingestion/files/initiate` (`index.ts:204` / `files.ts`) | `routes/ingestion.py:47` → `file_initiate` | **等价**（建 upload）|
| 13 | `ingestion/files/confirm` (`index.ts:206` / `files.ts:175`) | `routes/ingestion.py:62` → `file_confirm` | **有意简化+逻辑错误L**（建 source/doc/run/step；缺 uploader/状态校验 R7；缺 workflow 选择/plan 校验）|
| 14 | `ingestion/urls/submit` (`index.ts:208` / `urls.ts`) | `routes/ingestion.py:77` → `url_submit` | **等价**（建 url source/doc/run/clean step）|
| 15 | `ingestion/apis/submit` (`index.ts:210` / `apis.ts`) | `routes/ingestion.py:87` → `api_submit` | **有意简化**（建 api source；legacy 走 dedicated cleaner 注册，Python 统一进 clean step）|
| 16 | `management/files/list` (`index.ts:214` / `list.ts`) | `routes/management.py:42 list_documents` | **等价** |
| 17 | `management/files/detail` (`index.ts:216` / `list.ts`) | `routes/management.py:53 get_document` | **等价** |
| 18 | `management/static_files/list` (`index.ts:220` / `list.ts`) | `routes/management.py:67 list_static_files` | **等价** |
| 19 | `management/static_files/detail` (`index.ts:222` / `static.ts`) | `routes/management.py:78 get_static_file` | **等价** |
| 20 | `management/static_files/delete` (`index.ts:224` / `static.ts`) | **无**（purge 非等价替代）| **盲点B**（R4）|

**parity 覆盖率**：20 个 legacy RPC 中，**15 个有 Python 对应**（等价 11 + 有意简化 4），**5 个缺失**（reset_password / validate_api_key / create_api_key / workflow_update / static_delete）。覆盖率 **15/20 = 75%**。

> Python 侧另有 legacy 无直接 RPC 对应的**新增能力**（属设计扩展，非越界）：`team/bootstrap+select`（会话选队）、`search`/`search/debug`、`ops/{health,claims,restarts,purges}`、`workflow-configs`、`ingestion/static/{initiate,confirm}`。

### 3.1 对齐结论

| 编号 | 计划项 / 能力 | 审查结论 | 说明 |
|------|----------------|----------|------|
| S1 | 三类 ingestion 真实创建 source/document/workflow_run/step | `done` | file/url/api 全实现并投递 `stage='clean'` 可被 claim |
| S2 | ingestion step 可被 worker 路由（A1 创建侧核实） | `done` | `stage='clean'` ↔ `startswith("clean")` 匹配；A1 在 CR-5 创建侧证伪 |
| S3 | 鉴权 / team 隔离强制 | `done` | get_auth_context + require_team 全挂载；查询层 team_id 过滤 |
| S4 | 团队 API key 认证 | `missing` | api_keys 零访问（R1，盲点B+断点D）|
| S5 | 密码 legacy 兼容 | `partial` | pbkdf2 自建可用；legacy fallback 格式错误（R3）|
| S6 | management 只读 + restart/purge 入口 | `done` | 入口齐全；二次调用 PK 冲突属 CR-4 own（R6）|
| S7 | reset_password / workflow update / static delete | `missing` | 5 RPC 缺失之三（R4）|
| S8 | conn 注入纪律（auth/team 不 import storage_sqlite） | `done` | auth/team/ingestion/management 均 conn 由 deps 注入，无直接 import |
| S9 | 路径安全（filename 收口） | `missing` | filename 零校验直拼 object_key（R2）|
| S10 | 错误处理 → 正确 HTTP 状态 | `partial` | ValueError 冒泡 500（R5）|

### 3.1 对齐结论汇总

- **done**: 5（S1/S2/S3/S6/S8）
- **partial**: 2（S5/S10）
- **missing**: 3（S4/S7/S9）
- **stale**: 0
- **out-of-scope-by-design**: 0

> 状态判定：这更像**"控制面 CRUD 骨架 + 三类 ingestion 真实联通完成，但认证面（api_key）、安全收口（路径）、legacy 兼容（密码）三处未收口"**，而非 completed。核心数据流（ingestion→clean step→可 claim）真实贯通是本簇最强的正面结论。

### 3.2 stub / 真实现标定表（每个公开符号）

| 模块 | 公开符号 | 标定 | 依据 |
|------|----------|------|------|
| auth | `AuthService.register` | **真实现** | 建 user，pbkdf2 |
| auth | `AuthService.login` | **真实现** | 校验+rehash+建 session（legacy fallback 分支 L，见 R3）|
| auth | `AuthService.validate_session` | **真实现** | JOIN+过期惰性失效，SQL 时间比较正确 |
| auth | `validate_api_key`（应有） | **缺失** | api_keys 零访问（R1）|
| auth | `reset_password`（应有） | **缺失** | R4 |
| team | `TeamService.bootstrap` | **真实现** | 建 team + owner member |
| team | `TeamService.list_memberships` | **真实现** | JOIN team_members |
| team | `TeamService.is_member` | **真实现** | 成员校验 |
| team | `TeamService.select_team` | **真实现** | 更新 session.team_id |
| team | `create_api_key`（应有） | **缺失** | R1/R4 |
| ingestion | `file_initiate` | **真实现**（含安全缺陷 R2）| 建 upload，filename 未校验 |
| ingestion | `file_confirm` | **真实现**（弱校验 R7）| 建 source/doc/run/clean-step |
| ingestion | `url_submit` | **真实现** | 建 url source/doc/run/clean-step |
| ingestion | `api_submit` | **真实现** | 建 api source/doc/run/clean-step |
| ingestion | `static_initiate` | **部分**（冗余写 R8）| 包装 file_initiate + 无用 UPDATE |
| ingestion | `static_confirm` | **部分**（不建 run R8）| 建 source/doc/static_files，不触发 workflow |
| ingestion | `_create_workflow_run` | **真实现** | 建 run + `stage='clean'` step（核心联通点）|
| management | `list_workflows`/`get_workflow` | **真实现** | team_id 过滤 |
| management | `list_documents`/`get_document` | **真实现** | team_id 过滤 |
| management | `list_static_files`/`get_static_file` | **真实现** | team_id 过滤 |
| management | `search`/`search_debug` | **真实现**（委托 rag_vectorizer，质量见 CR-3/CR-7）| 转发 SearchService |
| management | `list_active_claims`/`list_restart_backlog`/`list_purge_backlog` | **真实现** | 查 v_ 视图，team_id 过滤 |
| management | `restart_workflow`/`purge_document` | **真实现**（二次调用 PK 冲突 R6）| 委托 workflow_core |
| management | `health` | **真实现** | 委托 collect_health |
| api/deps | `get_auth_context`/`require_team` | **真实现** | 仅 session token（无 api_key 分支，R1）|
| api/deps | `get_core_conn`/`get_vec_conn` | **真实现**（连接泄漏 G-CR2-01，CR-2 own）| return 非 yield |
| api/routes | `workflow_config.list_workflow_configs` | **真实现**（含 default fallback 桩）| 查 configs，空则返回硬编码 default |

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | 连接泄漏 G-CR2-01（deps `return` 非 `yield`）| `误报风险（已 CR-2 own）` | 本簇不重复裁决，仅确认入口在 deps.py:33-42 |
| O2 | 引擎隐式事务 G-CR2-02 | `遵守` | 属 CR-2，本簇 service commit 约定与之共生 |
| O3 | restart/purge PK 冲突 G-CR4-06 | `遵守（cross-ref）` | 入口在本簇 ops route，逻辑归 CR-4 |
| O4 | 时间格式 G-CR1-01 | `遵守` | 本簇未传播（全用 SSOT strftime / DDL DEFAULT）|
| O5 | search/vectorizer 质量 G-CR3-* | `遵守` | management 仅转发，质量归 CR-3/CR-7 |

**C1–C5 横切结论（逐项 pass/fail）**：

| 维度 | 结论 | 证据 |
|------|------|------|
| **C1 事务与并发** | `fail` | service 各方法独立 `commit()`，多写非原子（如 `file_confirm` 建 upload-update+source+doc+run+step 一个 commit 但失败无补偿）；继承 G-CR2-05 |
| **C2 错误处理** | `fail` | ValueError 未映射 HTTP（R5）；`me.py:24` row 为 None 时返回 `{"user": None}` 而非 404（弱）|
| **C3 一致性** | `pass`（控制面层面）| ingestion 仅写 core.db，不跨 vec.db；search/purge 跨库委托 workflow_core/rag（归 CR-3/CR-4）|
| **C4 可观测性** | `fail` | ingestion/auth/team **完全不写 workflow_events / audit_logs**；建 source/doc/run/step 无事件落库，违反"所有 workflow step 必须可观测"硬约束（创建侧无 event）|
| **C5 适配层纪律** | `pass` | ingestion/management 经 `FileSystemObjectStore` 访问对象存储，未直碰文件系统；未碰 sqlite-vec 方言（search 走 rag_vectorizer）|

> C4 fail 是本簇新增观察：legacy ingestion 有 verboseModules 全量日志（`index.ts:257-262`），Python 控制面创建 workflow_run/step 时**零事件/审计落库**，下游可观测性从创建点就断。建议补记为 followup（与 G-CR4-13 同族但落点在创建侧）。

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`changes-requested` —— 控制面骨架与三类 ingestion 数据流真实成立（A1 在创建侧证伪、stage 可路由是强正面），但**认证面（api_key 盲点B+断点D）、路径安全收口（security）、密码 legacy 兼容（L）**三处未收口，不能标记 completed。
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. **R1** — api_key 认证：实现 validate_api_key + create_api_key，或 owner 显式 defer（裁决待 owner：是否 MVP 含外部集成）。
  2. **R2** — filename 路径收口（控制面纵深防御，与 CR-3 G-CR3-01 协同）。
- **可以后续跟进的 non-blocking follow-up**：
  1. R3 密码 legacy 兼容修正 / R5 异常映射 HTTP / R7 confirm 归属校验。
  2. R4 补 reset_password 等缺失 RPC（按 owner 范围）；C4 控制面创建侧补 workflow_events/audit_logs。
  3. R6/R8 cross-ref CR-4，及 static 语义注释。
- **建议的二次审查方式**：`same reviewer rereview`（R1/R2 修复后复核 + CR-8 端到端验证 ingestion→clean→rag 真实跑通）
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> 本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。R1（api_key）的 blocker 性质取决于 owner 对"外部 API 集成是否 MVP 内"的裁决；R2（路径遍历源头）无条件 blocker。
