# Nano-Agent 行动计划 —— FF-F6c 认证与配置

> 服务业务簇: `smind-family · first-fixes · F6（执行器去桩与能力补全）的 auth/config 子簇`
> 计划对象: `F6-07 团队 API key 认证 + F6-09 prompt_versions/provider_configs 接线 + F6-11 统一 PBKDF2（删 legacy 密码兼容）`
> 类型: `modify`（含一处净新高风险认证边界 add）
> 作者: `MorrisonGentryowq（Claude Code）`
> 时间: `2026-05-31`
> 文件位置: `docs/action-plan/first-fixes/FF-F6c-auth-config.md`
> 上游前序 / closure:
> - `FF-F1-time-tx-base.md`（时间 SSOT + autocommit 事务模式）——本 AP 的 `api_keys`/会话时间写入、过期校验依赖 `strftime('%Y-%m-%dT%H:%M:%fZ','now')` 与显式 `BEGIN IMMEDIATE` 约束。
> 下游交接:
> - `FF-F6a-cleaners.md`（F6-02/03/08 universal cleaner / dedicated provider）——消费 F6-09 接线的 `provider_configs`。
> - `FF-F6b-rag-executors.md`（F6-04/05 structurize/construct）——消费 F6-09 接线的 `prompt_versions`。
> - `FF-F7-test-integrity.md`（测试整合 + closure 重定级）——本 AP 的先红后绿回归并入 F7 套件。
> 关联设计 / 调研文档:
> - `docs/design/first-fixes/initial-planning-by-opus.md`（§6.6 F6-07/09/11、§2.C [Q5][Q6] 定档、§3.2 O3、§8 DoD）
> - `docs/design/first-fixes/owner-gated-qna.md`（[Q5] API key 纳入、[Q6] 删密码兼容统一 PBKDF2、[Q7] 先红后绿）
> 关联 reference-anchor:
> - 见 §7 内置锚区（本链 reference-anchor 由 `part-cr-1.md~part-cr-8.md` 八簇审查预完成）
> grounding 来源:
> - `eval-reference-anchor: docs/eval/first-code-review-plan/part-cr-5.md`（G-CR5-01 api_keys 零访问认证断点[R1]、G-CR5-03 密码哈希不兼容[R3]，含 file:line）
> - `eval-reference-anchor: docs/eval/first-code-review-plan/part-cr-2.md`（G-CR2-03 prompt_versions/provider_configs 零访问[R3]）
> - `legacy 参照（只读校准）: legacy-family/smind-admin/services/auth.ts`（validate_api_key/hashApiKey/generateApiKey）、`core/db.ts`（findTeamByApiKeyHash/upsertTeamApiKey）
> 冻结决策来源:
> - `docs/design/first-fixes/owner-gated-qna.md`（[Q5][Q6][Q7]，只读引用；本 action-plan 不填写 Q/A）
> 文档状态: `draft`

---

## 0. 执行背景与目标

> 本 AP 是 final plan §10.A 把 F6 phase 按规模拆出的第三份 action-plan（`FF-F6c`），承接 F6 的**认证面 + 配置载体**两条非执行器主线。F6 主体（cleaners/rag executors）由 FF-F6a/FF-F6b 承接，本 AP 只做与执行器逻辑解耦、但同属"DDL 预留却零访问"的三块收口。

八簇审查（CR-2/CR-5）实测确认：`api_keys`、`prompt_versions`、`provider_configs` 三张表在全 Python 代码库**零读写**（仅存在于 `docs/refactor/core.sql` DDL），而 legacy `smind-admin` 有完整的 `validate_api_key` + `findTeamByApiKeyHash` + `upsertTeamApiKey` 认证链路；同时 `packages/auth/src/auth/service.py:17-18` 的 `_hash_legacy_password`（裸 sha256）与 legacy 真实格式 `hmac-sha512:salt:hash` 不一致，是一段"声称兼容但实现错误"的死代码。本 AP 把这三处从"看起来有、实际为空/为错"收口为可证明的真实现。

输入继承：范围由冻结 QnA `[Q5]`（API key 本轮纳入：校验中间件 + create_api_key + team 归属）、`[Q6]`（无存量用户，删 legacy 密码兼容声明、统一 PBKDF2）定档；执行纪律继承 `[Q7]`（全 phase 先红后绿铁律）。F6-09 的 `prompt_versions`/`provider_configs` 接线是 FF-F6a/FF-F6b 去桩从配置读 prompt/provider 的**前置载体**，故本 AP 必须先于（或与）F6a/F6b 配置消费侧交付。

- **服务业务簇**：`smind-family · first-fixes · F6 auth/config 子簇`
- **计划对象**：`F6-07（API key 认证）/ F6-09（配置载体接线）/ F6-11（统一 PBKDF2）`
- **本次计划解决的问题**：
  - `api_keys 表零访问 → 团队 API key 认证整簇缺失（G-CR5-01 / R1，认证断点 D）；外部系统集成仅能持用户会话 token。`
  - `prompt_versions / provider_configs 零访问 → F6a/F6b 真实 structurizer/provider 无配置载体可读，去桩缺前置（G-CR2-03 / G-CR2-03 余项）。`
  - `_hash_legacy_password 是与 legacy 真实格式不符的死代码 + 误导性"legacy 兼容"语义（G-CR5-03 / R3）。`
- **本次计划的直接产出**：
  - `AuthService.validate_api_key + create_api_key + get_auth_context 的 X-Api-Key 分支（key 仅以 sha256 hash 存储，team 归属经 api_keys.team_id 解析）。`
  - `prompt_versions / provider_configs 的读取访问层（config repository），供 F6a/F6b 按 (team_id, key, status='active') 解析 prompt 版本与 provider 配置。`
  - `删除 _hash_legacy_password 死分支 + login 中的 legacy rehash 分支，auth 统一 PBKDF2 单路径。`
- **本计划不重新讨论的设计结论**：
  - `API key 本轮纳入（校验中间件 + create_api_key + team 归属）`（来源：`[Q5]`）
  - `不保留 legacy 密码兼容、删声明、统一 PBKDF2（无存量用户）`（来源：`[Q6]`）
  - `全 phase 先红后绿铁律 + 禁止夹具掩盖`（来源：`[Q7]`）

---

## 1. 执行综述

### 1.1 总体执行方式

本 AP 采用"**先底层载体后认证边界、先审计后改动**"：Phase 1 先接线两张零访问的配置表（读路径，无安全面，解锁下游 F6a/F6b），Phase 2 集中做净新的 API key 认证边界（schema 读写 → key 生成/hash 存储 → 校验中间件 → team 归属 → create_api_key 端点，遵守先红后绿与威胁模型），Phase 3 做密码哈希死代码删除与 PBKDF2 单路径收口。认证边界（Phase 2）单独成 phase 以便集中施加威胁模型与攻击向量用例，不与配置读路径混改。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | 配置载体接线（prompt_versions / provider_configs 读路径） | S | 两张零访问表建读取访问层，供 F6a/F6b 解析 prompt/provider | FF-F1（时间 SSOT） |
| Phase 2 | 团队 API key 认证边界 | M | api_keys 读写 + key 生成/hash 存储 + 校验中间件 + team 归属 + create_api_key 端点 | FF-F1；Phase 1 不强依赖（可并行） |
| Phase 3 | 密码哈希统一 PBKDF2（删 legacy 兼容死代码） | XS | 删 `_hash_legacy_password` + legacy rehash 分支，单路径 PBKDF2 | FF-F1 |

> 说明：上表 `规模` 是描述性提示，不是开工前的体量判定闸。

### 1.3 Phase 说明

1. **Phase 1 — 配置载体接线**
   - **核心目标**：把 `prompt_versions`/`provider_configs` 从 DDL 预留接成真实可读访问层（`(team_id, key, status='active')` 解析 + 版本选择）。
   - **为什么先做**：F6-09 是 FF-F6a/FF-F6b 去桩"从配置读 prompt/provider"的前置载体；无安全面、规模小，先解锁下游。
2. **Phase 2 — 团队 API key 认证边界**
   - **核心目标**：补齐 legacy `validate_api_key`/`create_api_key` 全链路，作为程序化/集成认证方式，key 仅以 hash 存储、严格 team 归属。
   - **为什么放在这里**：净新认证信任边界，风险最高，需集中威胁模型 + 攻击向量用例；与配置读路径解耦施工，避免边界改动被稀释。
3. **Phase 3 — 密码哈希统一 PBKDF2**
   - **核心目标**：删除与 legacy 格式不符的 `_hash_legacy_password` 死代码 + `login` 中的 legacy 分支，auth 收敛为 PBKDF2 单路径。
   - **为什么放在这里**：依赖 [Q6] 裁决（无存量用户），是认证面就近小项；放最后避免与 Phase 2 的认证中间件改动交叠回归。

### 1.4 执行策略说明

> **纪律**：本节写执行策略，不重述 §6 已引用的冻结决策的理由。

- **执行顺序原则**：先无安全面的配置读路径（Phase 1）解锁下游，再做高风险认证边界（Phase 2），最后做删除型收口（Phase 3）；Phase 2 的子步严格按"schema 读写 → key 生成/hash → 校验中间件 → team 归属 → create 端点"有序推进。
- **风险控制原则**：API key 是认证信任边界，所有改动对照 §7.3 威胁模型；key 明文仅在生成时一次性返回、落库只存 sha256 hash；team 归属只信 `api_keys.team_id`，不接受请求侧传入 team。
- **测试推进原则**：`[Q7]` 先红后绿——每项先提交一条在当前 HEAD FAIL、修复后 PASS 的回归；认证项额外含攻击向量用例（伪造/重放/跨 team/明文存储），详见 §8。
- **文档同步原则**：删除"DDL 预留未接线"标注（三表接线后失效）；`database.md` 同步三表访问层状态；auth 文档去除"legacy 兼容"措辞。
- **回滚 / 降级原则**：Phase 1/3 为局部读路径/删除，回滚即 revert；Phase 2 认证中间件以新增 header 分支实现（不改既有 Bearer session 路径），异常时降级为"仅 session 认证可用"，不影响存量端点。

### 1.5 本次 action-plan 影响结构图

```text
FF-F6c 认证与配置
├── Phase 1: 配置载体接线
│   ├── packages/config/src/smind_config/（新增 config repository 读路径）
│   ├── core.sql: prompt_versions / provider_configs（DDL 已存在，建访问层）
│   └── 下游边界: FF-F6a(provider_configs) / FF-F6b(prompt_versions) 消费
├── Phase 2: 团队 API key 认证边界 ★ 信任边界
│   ├── packages/auth/src/auth/service.py（validate_api_key + create_api_key + hash_api_key + generate_api_key）
│   ├── apps/api/src/smind_api/deps.py（get_auth_context 增 X-Api-Key 分支）
│   ├── apps/api/src/smind_api/routes/team.py（POST create_api_key，owner 角色校验）
│   └── core.sql: api_keys（DDL 已存在，建读写层 + team 归属）
└── Phase 3: 密码哈希统一 PBKDF2
    ├── packages/auth/src/auth/service.py:17-18,28-29（删 _hash_legacy_password）
    └── packages/auth/src/auth/service.py:67-71（删 login legacy rehash 分支）
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** F6-09：`prompt_versions`/`provider_configs` 读取访问层（按 `(team_id, key, status='active')` 解析 + 版本选择），供 F6a/F6b 消费。
- **[S2]** F6-07：`api_keys` 读写层 + `generate_api_key`（`sm_` 前缀）+ `hash_api_key`（sha256）+ `validate_api_key`（hash 查表 → team 归属 → active 校验 + 可选 expires_at）。
- **[S3]** F6-07：`get_auth_context` 增加 `X-Api-Key` / `Authorization: ApiKey` 分支，与既有 Bearer session 分支并存。
- **[S4]** F6-07：`create_api_key` 端点（owner 角色校验，对齐 `team_members.role`），明文 key 仅一次性返回。
- **[S5]** F6-11：删除 `_hash_legacy_password` 死分支 + `login` 中 legacy 非 PBKDF2 rehash 分支，统一 PBKDF2 单路径。

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** API key 细粒度 scope 鉴权（`api_keys.scopes_json` 仅落库/解析，不在本轮做端点级 scope 强制）——重评条件：产品提出按 scope 限权需求。
- **[O2]** `reset_password` / `workflow update` / `static delete` 等其余缺失 legacy RPC（G-CR5-04，R4）——final §3.2 [O4] 延后。
- **[O3]** `prompt_versions`/`provider_configs` 的**写入/版本管理端点**（创建/激活新版本）——本轮只做读路径载体；写侧重评条件：F6a/F6b 需运行期改配置时。
- **[O4]** `workflow_step_links`（G-CR2-03 余项的第 4 张表）——归 FF-F3，不在本 AP。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| API key 校验中间件 + create_api_key + team 归属 | `in-scope` | [Q5] 本轮纳入；legacy 已有、属认证完整性 | — |
| prompt_versions/provider_configs 读路径 | `in-scope` | F6a/F6b 去桩前置载体（G-CR2-03 余项） | — |
| 删 legacy 密码兼容统一 PBKDF2 | `in-scope` | [Q6] 无存量用户，删不成立兼容声明 | 若出现 legacy 存量用户库需迁移登录 |
| api_keys scopes_json 端点级强制 | `out-of-scope` | 本轮只做认证（who），不做授权细粒度（what） | 产品提出按 scope 限权 |
| prompt/provider 写入/激活端点 | `defer / depends-on-design` | 本轮只需读载体支撑去桩 | F6a/F6b 需运行期改配置 |
| workflow_step_links 接线 | `out-of-scope` | 归属 FF-F3（DAG 边表） | — |

---

## 3. 业务工作总表

> **硬地板（不可约三元组）**：`涉及文件（file:line）` + `收口目标` + `测试映射`。安全/信任边界类工作项 `涉及文件` 须指向威胁模型落点（§7.3）。

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| P1-01 | Phase 1 | prompt_versions 读取访问层 | add | `packages/config/src/smind_config/`（新增 `config_repo.py`）；锚 `core.sql:362-376` | `按 (team_id, prompt_key, status='active') 取 active 版本，返回 template_path/digest/metadata` | `FF-F6c-T01` | low |
| P1-02 | Phase 1 | provider_configs 读取访问层 | add | `packages/config/src/smind_config/config_repo.py`；锚 `core.sql:378-390` | `按 (team_id, provider_key, status='active') 取 active settings_json（解析为 dict）` | `FF-F6c-T02` | low |
| P2-01 | Phase 2 | api_keys 读写层（CRUD 基元） | add | `packages/auth/src/auth/service.py`（新增方法）；锚 `core.sql:54-70` | `INSERT/SELECT api_keys 按 key_hash UNIQUE + team_id；裸 SQL 列名对齐 DDL` | `FF-F6c-T03` | medium |
| P2-02 | Phase 2 | key 生成 + hash 存储 | add | `packages/auth/src/auth/service.py`（`generate_api_key`/`hash_api_key`）；威胁落点 §7.3 | `生成 sm_<base64url(32B)> 明文仅返回一次；落库仅 sha256(key) hash + key_prefix；明文不入库不入日志` | `FF-F6c-T04` | **high** |
| P2-03 | Phase 2 | validate_api_key 校验中间件 | add | `apps/api/src/smind_api/deps.py:53-68`（get_auth_context 增分支）+ `auth/service.py`；威胁落点 §7.3 | `sm_ 前缀 → sha256 → 查 active key → 解析 team；伪造/无效/revoked/expired 拒绝；常量时间无关（直接 hash 查表）` | `FF-F6c-T05` / `FF-F6c-T07` | **high** |
| P2-04 | Phase 2 | team 归属解析 | add | `auth/service.py`（validate 返回 team_id）+ `deps.py`（AuthContext.team_id 注入）；威胁落点 §7.3 | `team 归属只取 api_keys.team_id，不信请求侧传入；跨 team key 不可访问他 team 资源` | `FF-F6c-T08` | **high** |
| P2-05 | Phase 2 | create_api_key 端点（owner 校验） | add | `apps/api/src/smind_api/routes/team.py`（新增 POST）+ `auth/service.py`+`team/service.py`（owner 角色） | `仅 team owner 可创建；返回明文 key 一次；非 owner → 403` | `FF-F6c-T06` | medium |
| P3-01 | Phase 3 | 删 `_hash_legacy_password` 死代码 | remove | `packages/auth/src/auth/service.py:17-18,28-29` | `文件无 _hash_legacy_password；_verify_password 仅 PBKDF2 路径` | `FF-F6c-T09` | low |
| P3-02 | Phase 3 | 删 login legacy rehash 分支 | remove | `packages/auth/src/auth/service.py:67-71` | `login 无非 PBKDF2 rehash 分支；非 PBKDF2 hash 一律登录失败` | `FF-F6c-T09` | low |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — 配置载体接线

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P1-01 | prompt_versions 读取访问层 | 扩展既有 config 包：新增 `config_repo.py`，提供 `get_active_prompt(conn, team_id, prompt_key) -> PromptVersion \| None`：`SELECT ... FROM prompt_versions WHERE team_id=? AND prompt_key=? AND status='active'`（命中 `ix_prompt_versions_lookup`），多版本时取最新 `activated_at`/`version`；team_id 可为 NULL（全局 prompt）时回退查询 `team_id IS NULL`。返回 `template_path/template_digest/metadata_json(解析)`。 | `packages/config/src/smind_config/config_repo.py`（新建）；锚 `core.sql:362-376` | F6b structurize 可按 prompt_key 拿到 active 版本与 digest | `FF-F6c-T01` | 读路径返回 active 行；无 active 返回 None；多版本取最新 |
| P1-02 | provider_configs 读取访问层 | 同表同构：`get_active_provider(conn, team_id, provider_key) -> ProviderConfig \| None`，解析 `settings_json`（`json_valid` 已由 DDL CHECK 保证）为 dict；team 级优先、回退全局 `team_id IS NULL`。 | `packages/config/src/smind_config/config_repo.py`；锚 `core.sql:378-390` | F6a dedicated provider（chinatax）可从配置读 settings | `FF-F6c-T02` | 读路径返回 active 配置 dict；无 active 返回 None |

### 4.2 Phase 2 — 团队 API key 认证边界（★ 信任边界，净新高风险，子步 a–e）

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P2-01 | api_keys 读写层 | **a)** 写基元 `_insert_api_key(team_id, name, key_prefix, key_hash, scopes_json, created_by_user_id)`：INSERT 对齐 `core.sql:54-70` 列（id=`apikey_<uuid>`、`status='active'`、时间走 DDL DEFAULT），`key_hash` UNIQUE 冲突 → raise；**b)** 读基元 `_find_active_key_by_hash(key_hash)`：`SELECT id,team_id,status,expires_at FROM api_keys WHERE key_hash=? AND status='active'`（命中 `ix_api_keys_team_status` 的逆向，按 key_hash UNIQUE 索引）。 | `packages/auth/src/auth/service.py`（新增）；锚 `core.sql:54-70` | api_keys 表从零访问变为可读写 | `FF-F6c-T03` | 写入/读取列与 DDL 一致；key_hash 重复被拒 |
| P2-02 | key 生成 + hash 存储 | **a)** `generate_api_key() -> str`：`sm_` + `base64url(secrets.token_bytes(32))`（对齐 legacy `auth.ts:80-90`）；**b)** `hash_api_key(raw) -> str`：`sha256(raw)`（对齐 legacy `auth.ts:68-74`，与会话 token 同策略）；**c)** 落库**只存** `key_hash` + `key_prefix`（明文前若干位，用于 UI 识别），**明文 key 绝不入库、不进日志、不二次可取**，仅创建时一次性返回调用方；**d)** 边界：raw 不以 `sm_` 开头 / 长度异常 → 校验侧直接判无效。 | `packages/auth/src/auth/service.py`；威胁落点 §7.3（⛔ 明文存储） | 明文 key 仅生成时返回一次；库内仅 hash | `FF-F6c-T04` | 库内无明文；hash 不可逆；重放需持原明文 |
| P2-03 | validate_api_key 校验中间件 | **a)** `AuthService.validate_api_key(raw) -> Row\|None`：前缀 `sm_` 检查（否则 None）→ `hash_api_key` → `_find_active_key_by_hash` → 命中后校验 `expires_at`（NULL=永久；否则 `> now`，用 SQL `strftime` 比较，对齐 FF-F1 时间 SSOT）→ 命中更新 `last_used_at`；**b)** `deps.get_auth_context` 增分支：当 `Authorization` 以 `ApiKey ` 开头或存在 `X-Api-Key` header 时走 api_key 路径，构造 `AuthContext`，否则沿用既有 Bearer session 分支；**c)** 失败语义：伪造/无前缀/无匹配/revoked(status≠active)/expired 一律 401，不泄漏"key 存在但 team 停用"等细节；**d)** 边界：两种 header 同时出现以哪个为准（取 Bearer 优先或显式 400，需固定一种并测）；**e)** 不做调用方可计时的分支差异（hash 后直接索引查表，无逐字节比较）。 | `apps/api/src/smind_api/deps.py:53-68` + `auth/service.py`；威胁落点 §7.3（伪造/重放/revoked/expired） | api_key 请求可鉴权；无效/过期/吊销被拒 | `FF-F6c-T05` / `FF-F6c-T07` | 有效 key 通过；伪造/无效/revoked/expired 全 401 |
| P2-04 | team 归属解析 | **a)** validate 命中后 `AuthContext.team_id = api_keys.team_id`（**唯一来源**），`user_id` 取 `created_by_user_id`（可 NULL → 标记机器身份）；**b)** 严格不接受请求 body/header 传入的 team_id 覆盖；**c)** 跨 team：team A 的 key 经 `require_team` 后只解析出 A，访问 B 资源的查询层 `WHERE team_id=?` 自然拒绝。 | `auth/service.py` + `deps.py`；威胁落点 §7.3（跨 team key） | api_key 持有者只能访问其归属 team 资源 | `FF-F6c-T08` | 跨 team 资源访问被拒；team 归属不可被请求侧篡改 |
| P2-05 | create_api_key 端点（owner 校验） | **a)** `POST /team/api-keys`（body: name, 可选 scopes/expires_at），`Depends(get_auth_context)` + `require_team`；**b)** 校验调用者在该 team 的 `team_members.role='owner'`（对齐 legacy `team.ts:180`），非 owner → 403；**c)** 调 `generate_api_key` → `hash_api_key` → `_insert_api_key`，响应**一次性**返回明文 key + id + key_prefix；**d)** 边界：重复创建生成不同 key（无确定性 request_id，避免 PK/UNIQUE 冲突）。 | `apps/api/src/smind_api/routes/team.py`（新增）+ `auth/service.py` + `team/service.py`（owner 角色查询） | owner 可创建 key 并取回明文一次 | `FF-F6c-T06` | owner 创建成功；非 owner 403；明文仅返回一次 |

### 4.3 Phase 3 — 密码哈希统一 PBKDF2

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P3-01 | 删 `_hash_legacy_password` 死代码 | 核对（part-cr-5 G-CR5-03）：`auth/service.py:17-18` `_hash_legacy_password` = 裸 `sha256`，与 legacy `auth.ts:59-66` 真实 `hmac-sha512:salt:hash` 三段格式不符 → **确认不兼容、为死代码**。删除该函数；`_verify_password:28-29` 的非 PBKDF2 fallback 分支一并删除，非 PBKDF2 stored_hash 直接返回 False（或视为损坏哈希拒绝）。 | `packages/auth/src/auth/service.py:17-18,28-29` | auth 无 legacy 哈希死代码 | `FF-F6c-T09` | 文件无 `_hash_legacy_password`；非 PBKDF2 一律不通过 |
| P3-02 | 删 login legacy rehash 分支 | `auth/service.py:67-71` 的 `if not row["password_hash"].startswith("pbkdf2_sha256$")` rehash 分支删除（既无 legacy 验证通过路径，该分支永不命中且语义误导）；login 仅保留 PBKDF2 校验。 | `packages/auth/src/auth/service.py:67-71` | login 单路径 PBKDF2 | `FF-F6c-T09` | login 无 legacy 分支；PBKDF2 校验保持正确 |

---

## 5. Phase 详情

### 5.1 Phase 1 — 配置载体接线

- **Phase 目标**：把 `prompt_versions`/`provider_configs` 接成真实读取访问层，解锁 F6a/F6b 去桩。
- **本 Phase 对应编号**：`P1-01` / `P1-02`
- **本 Phase 新增文件**：`packages/config/src/smind_config/config_repo.py`
- **本 Phase 修改文件**：`packages/config/src/smind_config/__init__.py`（导出 repo）
- **具体功能预期**：
  1. `get_active_prompt` 命中 `(team_id, prompt_key, status='active')` 返回单行，多版本取最新 `activated_at`。
  2. `get_active_provider` 返回解析后的 `settings_json` dict（DDL CHECK 已保证 json_valid）。
  3. team 级配置优先，未命中时回退 `team_id IS NULL` 全局配置。
  4. 无 active 行返回 None（调用方决定 degraded 行为，本 AP 不替 F6a/F6b 决策）。
- **对应测试台账项**：`FF-F6c-T01` / `FF-F6c-T02`（详见 §8）
- **收口标准**：两张表均有读路径；从零访问变为可读；先红后绿（修复前无读路径测试 FAIL）。
- **本 Phase 风险提醒**：F6-09 是 F6a/F6b 的配置前提，若本 phase 滞后会阻塞下游去桩——需先于或与 F6a/F6b 配置消费侧交付。

### 5.2 Phase 2 — 团队 API key 认证边界（★ 信任边界）

- **Phase 目标**：补齐团队 API key 认证全链路（生成/hash/校验/team 归属/创建端点），作为程序化集成认证方式。
- **本 Phase 对应编号**：`P2-01` / `P2-02` / `P2-03` / `P2-04` / `P2-05`
- **本 Phase 修改文件**：`packages/auth/src/auth/service.py`（新增 api_key 方法）、`apps/api/src/smind_api/deps.py:53-68`（get_auth_context 分支）、`apps/api/src/smind_api/routes/team.py`（create 端点）、`packages/team/src/team/service.py`（owner 角色查询，复用既有 `is_member` 模式扩展 role 校验）
- **本 Phase 新增文件**：无（落在既有 service/deps/route）
- **具体功能预期**（净新高风险，≥5 条，含边界与失败路径）：
  1. `generate_api_key` 产出 `sm_` 前缀 + 32 字节随机 base64url 明文；明文仅创建时返回一次。
  2. 落库**只存** `sha256(key)` 到 `key_hash`（UNIQUE）+ `key_prefix`；明文不入库、不进日志、不可二次取回。
  3. `validate_api_key`：前缀校验 → hash → 查 `status='active'` → `expires_at` 校验（SQL strftime 比较）→ 更新 `last_used_at`；命中失败统一 401。
  4. **失败/攻击路径**：伪造 key（无 `sm_` 前缀 / 随机串）→ None → 401；重放需持原明文（库内仅 hash，无法从库重构明文）；`revoked`/`expired` key → 不在 active 集 → 401；跨 team key → team_id 锁定为 `api_keys.team_id`，无法越权。
  5. **team 归属**只信 `api_keys.team_id`，拒绝请求侧传入覆盖；`created_by_user_id` 为 NULL 时标记机器身份。
  6. **边界**：`Authorization: Bearer` 与 `X-Api-Key` 同时出现时固定优先级（Bearer 优先）并测；`get_auth_context` 的 api_key 分支与既有 session 分支互不影响。
  7. `create_api_key` 端点仅 team owner 可调（`team_members.role='owner'`），非 owner → 403。
- **对应测试台账项**：`FF-F6c-T03`～`FF-F6c-T08`（详见 §8）
- **收口标准**：有效 key 创建并通过校验；伪造/无效/revoked/expired/跨 team key 全部被拒；非 owner 创建被拒；库内无明文 key。先红后绿（修复前所有 api_key 测试 FAIL，因表零访问）。
- **本 Phase 风险提醒**：净新认证信任边界——明文存储、跨 team 越权、重放是主要攻击向量（§7.3）；新增 header 分支不得削弱既有 Bearer session 路径。

### 5.3 Phase 3 — 密码哈希统一 PBKDF2

- **Phase 目标**：删除与 legacy 不兼容的密码兼容死代码，auth 统一 PBKDF2 单路径。
- **本 Phase 对应编号**：`P3-01` / `P3-02`
- **本 Phase 修改文件**：`packages/auth/src/auth/service.py:17-18,28-29,67-71`
- **本 Phase 删除文件**：无（删函数与分支，非删文件）
- **具体功能预期**：
  1. `_hash_legacy_password` 函数删除；`_verify_password` 非 PBKDF2 分支删除（非 PBKDF2 stored_hash 一律不通过）。
  2. `login` 的 legacy rehash 分支删除；login 仅 PBKDF2 校验。
  3. PBKDF2 注册/登录 happy-path 不回归（既有 `register`/`login`/`validate_session` 行为不变）。
- **对应测试台账项**：`FF-F6c-T09`（详见 §8）
- **收口标准**：文件无 `_hash_legacy_password`；非 PBKDF2 hash 登录失败；PBKDF2 正常路径绿。
- **本 Phase 风险提醒**：[Q6] 前提是"无存量用户"；若后续出现 legacy 用户库需迁移登录，须回退到"正确实现 hmac-sha512 回退验证"（见 §6 处置）。

---

## 6. 依赖的冻结设计决策（只读引用）

> 只引 register 的 Q 编号，不复制内容、不改口。

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| `[Q5]` | `owner-gated-qna.md` Q5（G-F-4 CLOSED） | Phase 2 全部子步（API key 校验中间件 + create_api_key + team 归属）启动 | 若改判延后：Phase 2 转为"docs 标注 api_keys 预留未接线"，本 AP 仅留 Phase 1/3 |
| `[Q6]` | `owner-gated-qna.md` Q6（G-F-5 CLOSED） | Phase 3 删 `_hash_legacy_password` + login legacy 分支，统一 PBKDF2 | 若出现 legacy 存量用户：改为正确实现 `hmac-sha512:salt:hash` 回退验证（对齐 legacy `auth.ts:92-104`），不删而修 |
| `[Q7]` | `owner-gated-qna.md` Q7（G-F-7 CLOSED） | 全部工作项以"先红后绿回归"为退出证据；认证项含攻击向量用例 | 不成立则本 AP 不得标 `executed`（违反全 phase 铁律） |
| `G-CR2-03 余项（prompt_versions/provider_configs）` | `initial-planning-by-opus.md` §2.B / §6.6 F6-09 | F6-09 是 FF-F6a（provider_configs）/ FF-F6b（prompt_versions）去桩的**配置前提**，须先于/同步交付 | 若 F6-09 滞后：F6a/F6b 配置读侧 blocked，需在那两份 AP 标依赖未满足 |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表（本计划工作要落在哪些既有代码 / 新建点上）

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| A-1 | `docs/refactor/core.sql:54-70` | `api_keys` 表 DDL（key_hash UNIQUE、team_id FK、status CHECK、key_prefix） | P2-01/02/03/04 读写落点 | `✅ 复用` | DDL 已建好，别重写；按列对齐裸 SQL |
| A-2 | `docs/refactor/core.sql:362-376` | `prompt_versions` 表 DDL（UNIQUE(team_id,prompt_key,version)、status） | P1-01 读路径落点 | `✅ 复用` | 已建好；命中 `ix_prompt_versions_lookup`（:481） |
| A-3 | `docs/refactor/core.sql:378-390` | `provider_configs` 表 DDL（settings_json json_valid CHECK） | P1-02 读路径落点 | `✅ 复用` | 已建好；命中 `ix_provider_configs_lookup`（:482） |
| A-4 | `apps/api/src/smind_api/deps.py:53-68` | `get_auth_context`（当前仅 Bearer session 分支） | P2-03/04 增 X-Api-Key 分支 | `✅ 复用` | 既有 Bearer 路径不动，新增并存分支 |
| A-5 | `packages/auth/src/auth/service.py:13-14` | `_hash_token`（sha256，会话 token 哈希） | P2-02 hash_api_key 同策略复用 | `✅ 复用` | api_key hash 与 token hash 同为 sha256（对齐 legacy hashApiKey） |
| A-6 | `packages/auth/src/auth/service.py:17-18,28-29,67-71` | `_hash_legacy_password` + verify fallback + login rehash 分支（死代码） | P3-01/02 删除点 | `🆕 净新`（删除型） | G-CR5-03：与 legacy `hmac-sha512` 格式不符，删 |
| A-7 | `packages/team/src/team/service.py:41-50` | `TeamService.is_member`（team 成员校验范式） | P2-05 owner 角色校验扩展基底 | `✅ 复用` | 按此模式加 `role='owner'` 查询 |
| A-8 | `packages/config/src/smind_config/config_repo.py` | 配置读取访问层 | P1-01/02 新建 | `🆕 净新` | 无既有 config repository，净新 |
| A-9 | `legacy-family/smind-admin/services/auth.ts:218-253` | legacy `handleValidateApiKey`（`sm_`→hash→find team→active） | P2-03 行为校准（只读参照） | — | 只读，不移植 TS；校准失败语义 |
| A-10 | `legacy-family/smind-admin/services/auth.ts:68-90` | legacy `hashApiKey`(sha256) / `generateApiKey`(sm_+32B base64url) | P2-02 算法校准（只读参照） | — | 只读，Python 对齐前缀/编码/hash |
| A-11 | `legacy-family/smind-admin/core/db.ts:429-485` | legacy `findTeamByApiKeyHash` / `upsertTeamApiKey` | P2-01/04 team 归属链路校准（只读） | — | 只读，校准"hash 查表→team" |

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | api_key 明文存储 / 写日志 / 二次可取回 | 认证 secret 明文落库 = 一旦库泄漏全部 key 暴露；必须只存 sha256 hash（legacy `auth.ts:68-74` 同此）。见 §7.3 攻击向量"明文存储" |
| ⛔2 | 保留不成立的 legacy 密码兼容死代码（`_hash_legacy_password` 裸 sha256） | 与 legacy 真实 `hmac-sha512:salt:hash` 格式不符（G-CR5-03 / R3），是"声称兼容但实现错误"的误导死代码；[Q6] 裁决删除 |
| ⛔3 | team 归属信任请求侧传入的 team_id | 跨 team 越权向量；team 必须只取 `api_keys.team_id`（§7.3） |
| ⛔4 | validate_api_key 失败时泄漏"key 存在但 team 停用/过期"等细节 | 信息泄漏便于枚举；失败统一 401，对齐 legacy `valid:false` 不区分原因 |
| ⛔5 | create_api_key 用确定性 request_id / 复用 key_hash | `key_hash` UNIQUE，确定性会 PK/UNIQUE 冲突（参照 R6 restart/purge 同类陷阱）；每次生成全新随机 key |
| ⛔6 | 改 api_key 分支时削弱既有 Bearer session 路径 | session 认证是存量端点唯一鉴权，回归即全端点失守；新增分支须与之并存不互斥 |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：本链 reference-anchor 由 `docs/eval/first-code-review-plan/part-cr-5.md`（R1 api_keys 认证断点、R3 密码哈希不兼容，含 file:line + legacy 对照）与 `part-cr-2.md`（R3 四表零访问）预完成；§7.1 是其与本 AP 相关子集的摘录，完整审查台账见两文真源。
- **安全 / 信任边界类工作项的威胁模型锚（API key 认证，P2-02/03/04，不得留空）**：

  威胁模型真源：`part-cr-5.md §R1`（认证断点 D 裁决）+ legacy `auth.ts:218-253` / `db.ts:429-485`（正确链路基线）+ §7.1 锚 A-1/A-9/A-10/A-11。攻击向量与对策：

  | 攻击向量 | 描述 | 本 AP 对策（落点） |
  |----------|------|--------------------|
  | **伪造（forgery）** | 攻击者构造任意 `sm_xxx` 串冒充 key | `validate_api_key` 前缀检查 + sha256 查 `api_keys` UNIQUE key_hash，无匹配 → 401（P2-03）；hash 不可逆，无法逆推出落库 hash 对应的明文 |
  | **重放（replay）** | 截获明文 key 后重复使用 | key 是 bearer 凭据，重放本质等同持有——对策是**最小化明文暴露面**：明文仅创建时返回一次、库内只存 hash、不进日志（P2-02）；可吊销（`status='revoked'`）即时失效（P2-03 active 过滤）；`expires_at` 限定有效期 |
  | **跨 team key（lateral）** | 用 team A 的 key 访问 team B 资源 | team 归属**唯一**取 `api_keys.team_id`，拒绝请求侧传入覆盖（P2-04）；下游查询层 `WHERE team_id=?` 二次隔离 |
  | **hash 存储而非明文（storage）** | 库泄漏导致 key 批量暴露 | 落库**只存 sha256(key)** + key_prefix，明文绝不入库（P2-02，⛔1）；sha256 不可逆，泄漏库无法直接得到可用明文 key |
  | **revoked/expired 绕过** | 用已吊销/过期 key 继续访问 | 校验仅匹配 `status='active'` 且 `expires_at` 未过（SQL strftime 比较，对齐 FF-F1 时间 SSOT）（P2-03） |
  | **枚举（enumeration）** | 通过错误细节区分 key 是否存在 | 失败统一 401，不区分"无此 key"/"team 停用"/"已过期"（⛔4） |

  > 威胁模型已在上游 part-cr-5 §R1 做过（认证断点裁决 + legacy 正确链路对照），本 AP 在此就地钉住攻击向量与对策；§8.5 含对应攻击向量用例。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| `FF-F6c-T01` | prompt_versions 读路径返回 active 版本（多版本取最新；无 active 返回 None） | 短途 | unit | `🆕 新增 tests/unit/test_config_repo.py` | `P1-01 → 读路径返回 active 行` | `commit {sha} + test_get_active_prompt PASS + {YYYY-MM-DD HH:MM UTC}` |
| `FF-F6c-T02` | provider_configs 读路径返回 active settings_json(dict)；team 级优先回退全局 | 短途 | unit | `🆕 新增 tests/unit/test_config_repo.py` | `P1-02 → 读路径返回 active 配置 dict` | `commit + test_get_active_provider PASS + run-time` |
| `FF-F6c-T03` | api_keys 读写基元：INSERT 后 by-hash 读回；key_hash 重复被拒 | 短途 | unit | `🆕 新增 tests/unit/test_api_key.py` | `P2-01 → 表可读写、列对齐 DDL` | `commit + test_api_key_crud PASS + run-time` |
| `FF-F6c-T04` | key 生成/hash：明文 `sm_` 前缀；库内仅 sha256 hash，明文不入库（断言查库无明文） | 短途 | unit | `🆕 新增 tests/unit/test_api_key.py` | `P2-02 → 库内无明文 key` | `commit + test_key_hash_only PASS + run-time` |
| `FF-F6c-T05` | 有效 key 创建后经 get_auth_context 校验通过，解析出正确 team | spike | 集成 | `🆕 新增 tests/integration/test_api_key_auth.py` | `P2-03 → 有效 key 通过校验` | `commit + test_valid_key_authenticates PASS + run-time` |
| `FF-F6c-T06` | create_api_key 端点：owner 创建成功返回明文一次；非 owner → 403 | spike | 集成·e2e | `🆕 新增 tests/integration/test_api_key_auth.py` | `P2-05 → owner 创建、非 owner 拒绝` | `commit + test_create_api_key_owner_only PASS + run-time` |
| `FF-F6c-T07` | ⚔️攻击向量：伪造/无 sm_ 前缀/revoked/expired key → 401（统一失败，无细节泄漏） | spike | 集成 | `🆕 新增 tests/integration/test_api_key_auth.py` | `P2-03 → 伪造/无效/revoked/expired 全拒` | `commit + test_invalid_key_rejected PASS + run-time` |
| `FF-F6c-T08` | ⚔️攻击向量：team A 的 key 访问 team B 资源被拒；team 归属不可被请求侧 team_id 篡改 | spike | 集成 | `🆕 新增 tests/integration/test_api_key_auth.py` | `P2-04 → 跨 team 越权被拒` | `commit + test_cross_team_key_denied PASS + run-time` |
| `FF-F6c-T09` | 统一 PBKDF2：非 PBKDF2 hash 登录失败；PBKDF2 注册/登录 happy-path 不回归；文件无 `_hash_legacy_password` | 短途 | unit·回归 | `🔱 fork tests/unit/test_auth.py + 加"legacy hash 拒绝"断言` | `P3-01/02 → 单路径 PBKDF2、无死代码` | `commit + test_pbkdf2_only PASS + run-time` |

**列定义（填法约束）**：
- **类型**：`短途`（每 PR 快测）/ `spike`（journey 验证）/ `mega`（长程整合）/ `soak`。
- **层**：`unit` / `集成` / `契约` / `回归` / `e2e` / `live(D1 forensic)`。
- **来源**：`🆕 新增` 点名新建文件；`🔱 fork` 点名 base + 加的断言。
- **PASS 证据**：四元组 `commit + 测试名 + run-time(UTC)`。

### 8.2 复用台账（沿用 / fork 的既有用例明细）

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/unit/test_auth.py`（PBKDF2 register/login，若存在；否则随 FF-F6c-T09 新建） | `🔱 fork → FF-F6c-T09` | `+ "非 PBKDF2 hash 拒绝" 断言 + "无 _hash_legacy_password 符号" 断言` | 当前 auth 含 legacy 分支，先红（legacy hash 仍被接受）后绿 |

> 注：F6-07 全部为净新认证链路，无既有用例可沿用（api_keys 零访问），故 T01–T08 均 `🆕 新增`。

### 8.3 分层与跑法（各类型在哪跑、何时跑）

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | 本地 / 每 PR | unit·回归 | 开发中持续（T01-04/T09） |
| spike | journey 用例（创建→校验→拒绝） | 集成·e2e | 每 Phase 收口（T05-08，Phase 2 收口） |
| mega | 端到端整合（并入 FF-F6/F7 capstone） | live 全链 | 由 FF-F7 capstone 承接（本 AP 不单跑 mega） |

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖 api_key **scope 级授权**（理由：[O1] 本轮只做认证非细粒度授权）→ 交后继 charter；不在本 AP 假装覆盖。
- 不覆盖 prompt/provider **写入/激活**路径（理由：[O3] 本轮只读载体）→ 交 F6a/F6b 需运行期改配置时。
- 端到端 mega（api_key 经真实端点投递 ingestion）交 `FF-F7` capstone（多 team 隔离步含 api_key 维度）。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 必带四元组证据；计数 ≠ 价值（对齐 closure 诚实收口）。
- `degraded` 必带机器可读 `reason`；`pre-existing` 失败必带 git 证据甩锅。
- **安全 / 信任边界项的攻击向量用例（对应 §7.3，不得只测 happy-path）**：
  - `FF-F6c-T07` 伪造（无 `sm_` 前缀 / 随机串 → 401）+ revoked（status='revoked' → 401）+ expired（expires_at 过期 → 401），且失败响应不区分原因（防枚举 ⛔4）。
  - `FF-F6c-T08` 跨 team（team A key 访问 team B 资源 → 拒绝）+ team 归属篡改（请求带 team_id 覆盖被忽略）。
  - `FF-F6c-T04` 明文存储（创建 key 后断言 `SELECT * FROM api_keys` 无明文、仅 hash；明文不在日志）。
  - **先红后绿**：T03–T08 在当前 HEAD（api_keys 零访问）必然 FAIL（无 validate_api_key / create_api_key），实现后 PASS；T09 在删除前 legacy hash 仍被接受（红）、删除后拒绝（绿）。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| API key 明文泄漏 | 明文若误入库/日志 → 全 key 暴露 | high | 只存 sha256 hash + key_prefix；明文一次性返回；T04 断言库内无明文（§7.3） |
| 跨 team 越权 | team 归属若信请求侧 → 横向越权 | high | team_id 唯一取 api_keys.team_id；T08 攻击向量用例（§7.3 ⛔3） |
| 新增 header 分支削弱 session 认证 | get_auth_context 改动回归既有 Bearer 路径 | medium | 新增分支与 Bearer 并存不互斥；既有 session 测试纳入回归（⛔6） |
| 依赖 FF-F1 时间 SSOT | expires_at / last_used_at / 会话时间比较依赖 `strftime` 格式可比 | medium | 前序 FF-F1 完成后再做 expires_at 比较；本 AP 全部时间走 SQL strftime（对齐 service.py:77,94） |
| F6-09 滞后阻塞下游 | F6a/F6b 配置读侧依赖 prompt_versions/provider_configs 接线 | medium | Phase 1 先交付；在 F6a/F6b AP 标本 AP 为前置 |
| [Q6] 前提"无存量用户"不成立 | 若出现 legacy 用户库需迁移登录 | low | 回退为正确实现 hmac-sha512 回退验证（§6 处置），不删而修 |

### 9.2 约束与前提

- **技术前提**：FF-F1 时间 SSOT 已落（`strftime('%Y-%m-%dT%H:%M:%fZ','now')`）；FF-F1 autocommit + 显式事务约束适用于本 AP 多写（create_api_key 的 INSERT）。
- **运行时前提**：`api_keys`/`prompt_versions`/`provider_configs` DDL 已在 `core.sql` 并经 migrations 应用（`apps/api/.../deps.py` 的 `apply_core_migrations`）。
- **组织协作前提**：FF-F6a/FF-F6b 在其配置消费侧引用本 AP 的 `config_repo` 接口签名（需先对齐签名再各自实现）。
- **上线 / 合并前提**：Phase 2 认证边界变更需 §8.5 攻击向量用例全 PASS 方可合并；先红后绿证据齐全。

### 9.3 文档同步要求

- 需要同步更新的设计文档：`docs/refactor/database.md`（三表从"DDL 预留未接线"改为"已接线"）。
- 需要同步更新的说明文档 / README：auth 包说明去除"legacy 兼容"措辞；新增 api_key 认证方式说明（`Authorization: ApiKey` / `X-Api-Key`）。
- 需要同步更新的测试说明：新增 `tests/unit/test_config_repo.py`、`test_api_key.py`、`tests/integration/test_api_key_auth.py` 纳入 CI。

### 9.4 完成后的预期状态

1. `api_keys`/`prompt_versions`/`provider_configs` 三张表从全代码库零访问变为有真实访问层（G-CR5-01 / G-CR2-03 余项闭环）。
2. 团队 API key 认证全链路可用：owner 创建 key、程序化请求经 `X-Api-Key`/`ApiKey` 鉴权、key 仅以 hash 存储、严格 team 归属。
3. F6a/F6b 去桩有可读的 prompt 版本与 provider 配置载体（F6-09 前置满足）。
4. auth 收敛为 PBKDF2 单路径，无 `_hash_legacy_password` 死代码与误导性"legacy 兼容"语义。
5. 认证边界有攻击向量回归用例（伪造/重放/跨 team/明文存储/revoked/expired），先红后绿证据齐全。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

### 10.1 收口硬闸

所有退出层测试项必须 PASS 且四元组证据齐全：

1. 有效 key 创建并通过校验、解析正确 team（由 `FF-F6c-T05` / `FF-F6c-T06` 证明）。
2. 攻击向量全拒：伪造/无效/revoked/expired/跨 team key、明文存储（由 `FF-F6c-T07` / `FF-F6c-T08` / `FF-F6c-T04` 证明）。
3. 配置载体可读、auth 单路径 PBKDF2（由 `FF-F6c-T01` / `FF-F6c-T02` / `FF-F6c-T09` 证明）。

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| prompt_versions 读路径返回 active | P1-01 | `FF-F6c-T01` | `commit + test + run-time` | `未观察` |
| provider_configs 读路径返回 active 配置 | P1-02 | `FF-F6c-T02` | `commit + test + run-time` | `未观察` |
| api_keys 可读写、列对齐 DDL | P2-01 | `FF-F6c-T03` | `commit + test + run-time` | `未观察` |
| 库内无明文 key（仅 hash） | P2-02 | `FF-F6c-T04` | `commit + test + run-time` | `未观察` |
| 有效 key 通过校验、解析 team | P2-03 | `FF-F6c-T05` | `commit + test + run-time` | `未观察` |
| owner 创建、非 owner 403 | P2-05 | `FF-F6c-T06` | `commit + test + run-time` | `未观察` |
| 伪造/无效/revoked/expired 全拒 | P2-03 | `FF-F6c-T07` | `commit + test + run-time` | `未观察` |
| 跨 team 越权被拒、归属不可篡改 | P2-04 | `FF-F6c-T08` | `commit + test + run-time` | `未观察` |
| 单路径 PBKDF2、无 legacy 死代码 | P3-01/02 | `FF-F6c-T09` | `commit + test + run-time` | `未观察` |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | 三表接线（读/读写）+ API key 认证全链路 + PBKDF2 单路径，均落地可用 |
| 测试 | §8 测试台账全 PASS（退出硬闸项四元组齐全；攻击向量用例 PASS）|
| 文档 | database.md 三表状态更新；auth 去 legacy 兼容措辞；api_key 认证方式文档化 |
| 风险收敛 | 明文存储/跨 team 越权/session 回归三项 high 风险经攻击向量用例与并存设计收敛 |
| 可交付性 | F6-09 配置载体可被 FF-F6a/FF-F6b 消费；接口签名对齐 |

### 10.4 NOT-成功识别

> 任一退出硬闸测试 `degraded / 未观察` ⇒ 不得标 `executed`；§7.3 威胁模型为上游 part-cr-5 §R1 已做，本 AP 钉住攻击向量。按 closure 五态（`verified / observed-OK-at-closure / partial / 未观察 / deferred`）如实归类 + handoff，不 silent overclaim。

---

## 11. 执行日志回填（仅 `executed` 状态使用）

> 文档状态为 `draft`，本节省略（待 `executed` 时按 `respond-execution-log` append 厚版回填）。
