# Nano-Agent 代码审查报告 — CR-1 · 基础底座与契约 (Foundation & Contracts)

> 审查对象: `CR-1 基础底座与契约（packages/common, packages/config, packages/contracts）`
> 审查类型: `code-review`
> 审查时间: `2026-05-31`
> 审查人: `Claude sub-agent (CR-1)`
> 审查范围:
> - `packages/common/src/smind_common/{errors,ids,logging,time}.py`
> - `packages/config/src/smind_config/{loader,settings}.py`
> - `packages/contracts/src/smind_contracts/workflow.py`
> 对照真相:
> - `docs/eval/first-code-review-plan/index.md`（审查口径 B/D/L、横切维度 C1–C5、附录 A 候选疑点 A3/A6、§7 owner 口径）
> - `docs/refactor/core.sql`（时间格式 SSOT，视图 `v_ready_steps` / `v_stale_claims` 的时间比较）
> - `docs/refactor/database.md` §9.2（时间格式权威约定）
> - `legacy-family/smind-admin/core/errors.ts`（错误类型体系基线）
> - `legacy-family/smind-admin/core/log.ts`（日志体系基线）
> - `legacy-family/smind-admin/core/schemas_common.ts` / `core/schemas_smcp.ts`（契约/schema 面基线）
> - `packages/workflow_core/src/workflow_core/_utils.py`（时间/ID 的重复实现，交叉核对）
> 文档状态: `changes-requested`

---

## 0. 总结结论

- **整体判断**：CR-1 的代码量极小、可以运行，但**它作为"全系统时间戳 SSOT"的职责没有兑现**——`smind_common.time.utc_now_iso()` 产出的字符串与设计 SSOT(`docs/refactor/database.md` §9.2)和 `core.sql` 的 `strftime('%Y-%m-%dT%H:%M:%fZ')` **格式不一致**;更严重的是真正被工作流内核使用的 `workflow_core/_utils.now_iso()` 产出的是一个**结构错误(丢失秒字段)的时间串**,会使 `v_ready_steps.available_at <= strftime(...)` 字符串比较出错,导致 step 永不就绪。A6 经亲自核实**确有高危 bug**。
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. **A6 = 真 bug(L,blocker)**：时间格式三处分裂。设计 SSOT=`...SS.mmmZ`;`common.utc_now_iso()`=`...SS.ffffff+00:00`(错,微秒+偏移);`_utils.now_iso()`=`...HH:MM:ffffffZ`(错,**无秒字段**)。后者实际写入 `available_at`/`lease_expires_at`,与 SQL `strftime` 字符串比较结果错误(实测 `app_now <= sqlite_now` 返回 `False`,本应 `True`)。
  2. **A3 = 盲点 B(确认,但范围之外的设计欠账)**：`contracts` 仅 2 个无校验 dataclass,且全仓库 **0 处 import**,既薄又是死代码;legacy 契约面有 40+ Zod schema(`schemas_common.ts`)+11 SMCP payload schema(`schemas_smcp.ts`)。运行时校验实际散落在 `apps/api` 各路由的 pydantic 模型中,未沉淀为契约层。
  3. **错误体系塌缩(B)**：`SmindError` 是一个仅含 `code` 的空壳,全仓库 **0 处使用**;legacy `errors.ts` 有 25+ 错误码常量 + HTTP status 映射 + `ApiException.toResponseJSON()`。能力大幅缺失且未声明替代落点。

---

## 1. 审查方法与已核实事实

> 本节只写事实。

- **对照文档**：
  - `docs/eval/first-code-review-plan/index.md`（§1 口径、§1 横切维度、§3 CR-1 关注/已知风险、§7 owner 口径、附录 A 的 A3/A6）
  - `docs/refactor/database.md` §9.1/§9.2（ID 与时间约定）
  - `docs/refactor/core.sql`（时间默认值与视图比较）
- **核查实现**（全部用 Read 看过真实行号）：
  - `packages/common/src/smind_common/{__init__,errors,ids,logging,time}.py`
  - `packages/config/src/smind_config/{__init__,loader,settings}.py`
  - `packages/contracts/src/smind_contracts/{__init__,workflow}.py`
  - 交叉核对：`packages/workflow_core/src/workflow_core/_utils.py`、`graph.py`
  - 测试：`tests/smoke/test_shared_imports_smoke.py`
- **执行过的验证**（实测命令）：
  - `python3 -c "import sqlite3; ...strftime('%Y-%m-%dT%H:%M:%fZ','now')"` → `'2026-05-31T07:26:11.380Z'`（24 字符,含秒,毫秒 3 位,`Z` 结尾）
  - `datetime.now(timezone.utc).isoformat()`（= `common.utc_now_iso`）→ `'2026-05-31T07:26:11.388082+00:00'`（32 字符,微秒 6 位,`+00:00` 结尾)
  - `datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%fZ')`（= `_utils.now_iso`)→ `'2026-05-31T07:26:395298Z'`（**无秒字段**,`%f` 在 Python 是 6 位微秒,与前置 `%M:` 直接拼接)
  - 比较实测：`app_now('...07:26:979490Z') <= sqlite_now('...07:26:44.979Z')` → `False`（本应 `True`,step 本应就绪却被判未就绪)
  - `basicConfig` 幂等性实测：二次调用为 no-op,handlers 仍为 1,level/format 不可被二次修改
  - `grep` 全仓库使用面：`SmindError` 0 处使用;`smind_contracts` 0 处 import;`common.utc_now_iso` 仅被自身导出(业务侧不引用),内核改用 `_utils.now_iso`
- **复用 / 对照的既有审查**：
  - `index.md` 附录 A 的 A3/A6 — 作为**线索**,本轮独立复核并下裁决,未直接采纳其结论。

### 1.1 已确认的正面事实

- 三个包都能 import、能跑、无语法错误;`tests/smoke/test_shared_imports_smoke.py` 可通过。
- `new_id(prefix)`（`ids.py:4-5`）实现正确,`prefix_<uuid4.hex>` 满足 database.md §9.1"应用层生成稳定字符串 ID"约定;与 `_utils.new_id`（`_utils.py:15-16`)行为**完全一致**(同为 `uuid4().hex`),无行为冲突。
- `get_logger`（`logging.py:4-9`）的 `basicConfig` 调用是**幂等**的,重复调用不会叠加 handler(实测)。
- `Settings`（`settings.py:4-10`）正确使用 `pydantic_settings`,`env_prefix="SMIND_"`、`extra="ignore"`,可由环境变量覆盖默认值。
- `load_settings`（`loader.py:6-8`）用 `lru_cache(maxsize=1)` 提供进程级单例。

### 1.2 已确认的负面事实

- `common/time.py:5` `utc_now_iso()` 用 `isoformat()`,产出 `+00:00` 偏移与 6 位微秒,**不等于** database.md §9.2 SSOT 示例 `2026-05-30T18:16:48.420Z`,也不等于 `core.sql` 的 `strftime('%Y-%m-%dT%H:%M:%fZ')`。
- `_utils.now_iso()`/`add_seconds_iso()`（`_utils.py:6,10-12`）用 `strftime("%Y-%m-%dT%H:%M:%fZ")`:`%f` 在 **Python = 6 位微秒**(而 SQLite `%f` = `SS.SSS`),且格式串中 `%M:` 后直接接 `%f` **没有 `%S` 秒字段**,产出形如 `...07:26:979490Z` 的畸形串。
- `_utils.now_iso` 而非 `common.utc_now_iso` 才是写入 `task_claims.lease_expires_at`/`workflow_steps.available_at` 等时间列的实际来源(见 `leases.py:14,21`、`claim.py:34,64`、`retry.py`、`restart.py`、`purge.py`)。两套时间实现并存且**都偏离 SSOT**。
- `contracts` 仅 `WorkflowRunContract`/`WorkflowStepContract` 两个 dataclass,无校验、无 status 枚举;全仓库 **0 处 import**(死代码)。
- `errors.py` 的 `SmindError` 仅 `message`+`code`,无 HTTP 映射、无错误码常量、无结构化响应;全仓库 **0 处使用**。
- CR-1 三包**无专属单元测试**;唯一覆盖来自 `tests/smoke/test_shared_imports_smoke.py`,且仅断言 `"T" in utc_now_iso()`——不校验时间格式(假绿)。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | CR-1 全部源码 + `_utils.py`/`graph.py` 逐行核对 |
| 本地命令 / 测试 | `yes` | 用 `python3 -c` 实测三种时间格式输出字符串与字符串比较结果;实测 `basicConfig` 幂等性;`grep` 统计使用面 |
| schema / contract 反向校验 | `yes` | 对照 `core.sql` 时间列与视图比较;对照 legacy `schemas_common.ts`/`schemas_smcp.ts` 契约面规模 |
| live / deploy / preview 证据 | `n/a` | 本簇为库代码,无部署面 |
| 与上游 design / QNA 对账 | `yes` | 对账 `database.md` §9.2 时间 SSOT 与 `index.md` §3 CR-1 关注点 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | `_utils.now_iso()` 时间格式畸形(丢秒),破坏 `v_ready_steps`/`v_stale_claims` 比较 | critical | correctness / L | yes | 修复 strftime 格式串,统一收口到 common |
| R2 | `common.utc_now_iso()` 不符合 SSOT 时间格式(微秒+偏移) | high | correctness / L | yes | 改为毫秒 3 位 + `Z` 后缀,与 SQL 一致 |
| R3 | 时间/ID 在 common 与 _utils 双重实现且时间格式不一致 | high | correctness / D | yes | 删除 `_utils` 时间函数,全系统单一来源 |
| R4 | `contracts` 过薄且为死代码(0 import) | medium | scope-drift / B | no | 决策:补全契约层或显式删除/降级 |
| R5 | `SmindError` 错误体系塌缩,远薄于 legacy 且 0 使用 | medium | scope-drift / B | no | 补错误码/HTTP 映射或声明 API 层替代 |
| R6 | `get_logger` 无结构化/级别配置/审计落库能力 | low | platform-fitness / B | no | 声明可观测性落点(C4 由内核承担) |
| R7 | `Settings` 相对路径默认值导致 cwd 依赖脆弱 | low | correctness | no | 改用 anchor 路径或文档约束启动目录 |
| R8 | CR-1 无专属测试,smoke 断言空洞(假绿) | medium | test-gap | no | 增加时间格式 round-trip 断言 |

### R1. `_utils.now_iso()` 时间格式畸形(丢秒),破坏 `v_ready_steps`/`v_stale_claims` 时间比较

- **严重级别**：`critical`
- **类型**：`correctness / L`（index §1 逻辑错误）
- **是否 blocker**：`yes`
- **事实依据**：
  - `packages/workflow_core/src/workflow_core/_utils.py:6` `return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%fZ")`
  - `_utils.py:9-12` `add_seconds_iso` 同款格式串
  - `docs/refactor/core.sql:271,292` `available_at`/`lease_expires_at` 列 DEFAULT 与写入语义
  - `docs/refactor/core.sql:535` `v_ready_steps`：`AND ws.available_at <= strftime('%Y-%m-%dT%H:%M:%fZ', 'now')`
  - `docs/refactor/core.sql:713` `v_stale_claims`：`AND tc.lease_expires_at <= strftime('%Y-%m-%dT%H:%M:%fZ', 'now')`
  - 写入侧:`leases.py:14,21`、`claim.py:34,64`、`retry.py:14,87`、`restart.py`、`purge.py` 均用 `_utils.now_iso`/`add_seconds_iso`
  - 实测:SQLite 输出 `'2026-05-31T07:26:44.979Z'`;Python `_utils` 输出 `'2026-05-31T07:26:979490Z'`(无秒);`app_now <= sqlite_now` → `False`(本应 `True`)
- **为什么重要**：
  - `%f` 在 Python `datetime.strftime` 是 6 位**微秒**,而格式串中 `%M:` 后没有 `%S`,所以 Python 产出 `分:微秒` 而**完全没有秒**;SQLite 的 `%f` 是 `秒.毫秒`。两端用同一格式串却产生**不同结构、不同长度排序键**的字符串。
  - `v_ready_steps` 用字符串比较 `available_at <= now`。当应用写入的 `available_at` 串里"分"之后紧跟微秒(如 `07:26:979490Z`),而 SQLite 的 `now` 串是 `07:26:44.979Z`,在 `07:26:` 之后第一位 `9` vs `4`,字典序判定 `available_at > now`,于是 step **被判为尚未就绪、永不进入 ready 集合**——这是 index 附录 A6 标注的高危链路,经实测确认成立。
  - 同理 `v_stale_claims` 的 lease 过期回收会失灵(过期 claim 不被回收或被错误回收)。
- **审查判断**：
  - A6 裁决 = **逻辑错误 L,blocker**。bug 的物理落点在 `workflow_core/_utils.py`(属 CR-4 文件),但根因是 CR-1 未把时间格式作为强约束的单一 SSOT 提供并强制全系统复用,导致内核另起炉灶且写错。CR-1 与 CR-4 联合 own。
- **建议修法**：
  - 时间格式串改为毫秒 3 位 + 秒 + `Z`,例如 `dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"`(或用 `isoformat(timespec="milliseconds")` 再把 `+00:00` 替换为 `Z`)。
  - 删除 `_utils.now_iso/add_seconds_iso`,内核改 import `smind_common.time`,确保**唯一来源**。
  - 增加 round-trip 测试:`utc_now_iso()` 与 SQLite `strftime('%Y-%m-%dT%H:%M:%fZ','now')` 长度一致、字典序可比。

### R2. `common.utc_now_iso()` 不符合 SSOT 时间格式(微秒 + 偏移)

- **严重级别**：`high`
- **类型**：`correctness / L`
- **是否 blocker**：`yes`
- **事实依据**：
  - `packages/common/src/smind_common/time.py:5` `return datetime.now(timezone.utc).isoformat()`
  - `docs/refactor/database.md:480-484` SSOT 示例 `2026-05-30T18:16:48.420Z`
  - 实测输出 `'2026-05-31T07:26:11.388082+00:00'`（6 位微秒 + `+00:00`,非 `Z`,32 字符）
- **为什么重要**：
  - 这是 CR-1 对外宣称的"全系统时间戳"函数,却与 SSOT 和 SQL `strftime` 都不一致。一旦未来有任何代码改回用 `common.utc_now_iso()` 写时间列(它本就是设计意图),会引入与 R1 同类的字符串比较错误(此处 `+00:00` 的 `+` 字符 ASCII 比数字小,排序行为更不可预测)。
  - 当前侥幸未触发,仅因为业务侧没有 import 它——但这恰恰说明 CR-1 的核心交付物处于"写错且无人用"的状态。
- **审查判断**：
  - 逻辑错误 L,与 R1 同根。即便当前无人调用,作为底座 SSOT 函数其正确性是 blocker 级。
- **建议修法**：
  - 与 R1 统一:输出 `YYYY-MM-DDTHH:MM:SS.mmmZ`(毫秒 3 位,`Z` 结尾),与 SQL 严格一致。

### R3. 时间/ID 在 `common` 与 `_utils` 双重实现,时间格式分裂

- **严重级别**：`high`
- **类型**：`correctness / D`（index §1 断点：单一职责链被复制并分叉）
- **是否 blocker**：`yes`
- **事实依据**：
  - `common/time.py` vs `workflow_core/_utils.py:5-12`(时间);`common/ids.py` vs `_utils.py:15-16`(ID)
  - `grep` 显示内核全程用 `_utils.*`,`common.utc_now_iso` 业务侧 0 引用
- **为什么重要**：
  - ID 两份实现行为一致(均 `uuid4().hex`),无即时危害但属重复;时间两份实现**行为不一致且都错**,是 R1/R2 的结构性成因。底座存在两个"真理来源"会让任何"修一处"的修复无法生效全局。
- **审查判断**：
  - 断点 D:时间戳一致性链路在 common→内核之间断裂(内核绕过 common 自建)。
- **建议修法**：
  - 删除 `_utils` 的 `now_iso/add_seconds_iso/new_id`,统一 import `smind_common`;`add_seconds_iso` 这类带偏移的工具应下沉到 `smind_common.time` 作为唯一实现。

### R4. `contracts` 过薄且为死代码(0 import)

- **严重级别**：`medium`
- **类型**：`scope-drift / B`（index §1 盲点:应有未有 + §7.1 stub 标定)
- **是否 blocker**：`no`
- **事实依据**：
  - `packages/contracts/src/smind_contracts/workflow.py:1-17`（2 个无校验 dataclass）
  - `grep` 全仓库 `smind_contracts` import 数 = 0
  - legacy `schemas_common.ts`:40+ 导出 schema(`TeamSchema`/`UserSchema`/`FileSchema`/`WorkflowSchema`/`WorkflowStepSchema`/各类 Request/Response…),含 Zod 运行时校验;`schemas_smcp.ts`:11 个 SMCP payload schema(`SmcpStepStart`/`SmcpStepRestart`/`SmcpStepCallback`…)
  - 运行时校验实际散落在 `apps/api/routes/*` 的 pydantic 模型(`auth/me/ops/ingestion/search/team`)
- **为什么重要**：
  - index 附录 A3 疑点确认:契约面相比 legacy 隐含的契约缩水到不足 5%。更糟的是它**完全没被使用**,既不是"契约 SSOT"也未被任何层引用,等于占位空壳。
  - 契约缺失本身在底座层不会立刻 crash,但会让上层(CR-5 API、CR-4/6/7 step payload)各自手写散装校验,跨层一致性无单一来源——这是后续簇 D/L 的温床。
- **审查判断**：
  - A3 裁决 = **盲点 B**(应有未有)。非 blocker,因为校验当前由 API pydantic 兜底未致命;但需 owner 决策:是把契约层补成真 SSOT(承载 step payload / SMCP 控制面契约),还是显式降级删除以免误导。
- **建议修法**：
  - 决策二选一:(a) 将 `WorkflowStepContract.status`/`stage` 等改为枚举并新增 step payload / 控制面(restart/purge/callback)契约,被 API 与内核共同 import;(b) 若短期不做,在 `contracts/__init__.py` 与 todo 中明确标注"占位,未承载校验",避免被误当作契约 SSOT。

### R5. `SmindError` 错误体系塌缩,远薄于 legacy 且 0 使用

- **严重级别**：`medium`
- **类型**：`scope-drift / B`
- **是否 blocker**：`no`
- **事实依据**：
  - `packages/common/src/smind_common/errors.py:1-4`（仅 `message` + `code` 默认 `"SMIND_ERROR"`）
  - `grep` 全仓库 `SmindError` 使用数 = 0(仅自身导出 + smoke 测试构造一次)
  - legacy `errors.ts:49-92`:25+ `ErrorCodeDefinition`(code+message+HTTP status),`errors.ts:98-119` `ApiException.toResponseJSON()` 结构化响应
- **为什么重要**：
  - legacy 的错误体系是 API 错误码/HTTP 映射/审计的基础设施(401/403/402/409/413/429/500…)。Python 侧塌缩为一个无分类、无 HTTP 映射、且全系统没人 `raise/except` 的空壳。
  - 这与 index §1 C2(错误处理)直接相关:没有统一错误类型,失败语义无法标准化落到 `step_attempts`/`audit_logs`(C4)。
- **审查判断**：
  - 盲点 B。非 blocker(API 层用 FastAPI HTTPException 兜底),但底座未提供错误码/HTTP 映射能力是明确缺口。
- **建议修法**：
  - 至少补:错误码常量表(对齐 legacy `ErrorCodes`)+ `status` 字段 + `to_response()` 方法;或显式声明"错误码体系由 apps/api 层 own,common 仅提供基类",并写入设计文档以消除盲点歧义。

### R6. `get_logger` 仅 basicConfig,无结构化/级别阈值/审计落库

- **严重级别**：`low`
- **类型**：`platform-fitness / B`
- **是否 blocker**：`no`
- **事实依据**：
  - `packages/common/src/smind_common/logging.py:4-9`
  - legacy `log.ts`:`Logger` 类含 LogLevel 优先级、verboseModules 白名单、`dbPersistFn` 审计落库、trace/team/calling 上下文
- **为什么重要**：
  - index §1 C4 要求"所有 workflow step 必须可观测/落 `workflow_events`/`audit_logs`"。CR-1 的 logger 只做控制台输出,无审计落库能力。
  - `basicConfig` 幂等(实测):重复 `get_logger` 安全,但意味着**级别/格式一旦被首个调用方(或第三方库)固定即不可改**,且若他人先配置 root,本配置被静默忽略。
- **审查判断**：
  - 盲点 B,但 C4 的可观测性落库职责实际由 `workflow_core/graph.py:write_workflow_event` 与 `events.py` 承担(写 `workflow_events`/`audit_logs`)。因此对 CR-1 而言 C4 判 **n.a.**(落点不在本簇),logger 简化属可接受的有意收敛,仅作 follow-up。
- **建议修法**：
  - 文档声明"审计/事件落库由内核 events 层负责,common.logger 仅控制台";如需运行期改级别,提供 `level` 参数或 env 读取而非硬编码 `INFO`。

### R7. `Settings` 相对路径默认值导致 cwd 依赖脆弱

- **严重级别**：`low`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `packages/config/src/smind_config/settings.py:6-9`：`data_dir="data"`、`core_db_path="data/db/core.db"`、`vec_db_path="data/db/vec.db"`、`object_store_dir="data/objects"`
- **为什么重要**：
  - 相对路径在不同 cwd 下解析到不同位置:从仓库根 vs 从 `apps/worker` 启动会指向不同的 db 文件,可能导致 worker 与 api 实际操作两个不同的 `core.db`(静默数据分裂)。`load_settings` 的 `lru_cache` 又使其在进程内固化。
- **审查判断**：
  - 真实脆弱性,但属可由环境变量(`SMIND_CORE_DB_PATH` 等)覆盖的低危项;非 blocker。
- **建议修法**：
  - 默认值改为基于某个 anchor(如 `Settings` 解析时相对项目根)的绝对路径,或在启动文档/CLI 中强制指定 cwd / 显式传 env。

### R8. CR-1 无专属测试,smoke 断言空洞(假绿)

- **严重级别**：`medium`
- **类型**：`test-gap`（呼应 index §7.4"查假绿"）
- **是否 blocker**：`no`
- **事实依据**：
  - `tests/smoke/test_shared_imports_smoke.py:10` 仅 `assert "T" in utc_now_iso()`
  - 无任何测试断言时间格式与 SQL 一致(若有,R1/R2 早该被测出)
- **为什么重要**：
  - 现有 smoke 测试对最危险的时间格式只做了"含字母 T"的空洞断言,正是 §7.4 警告的假绿:测试通过却掩盖了 R1/R2 这类致命格式错误。
- **审查判断**：
  - 测试缺口。该测试归属 CR-8,但其对 CR-1 的"假绿"性质需在此登记。
- **建议修法**：
  - 增加断言:`utc_now_iso()` 形如 `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$`,且与 SQLite `strftime('%Y-%m-%dT%H:%M:%fZ','now')` 长度一致、可字典序比较。

---

## 3. In-Scope 逐项对齐审核

> 计划项来自 index §3 CR-1 表格"关注"与"已知风险"。

| 编号 | 计划项 / 设计项 | 审查结论 | 说明 |
|------|----------------|----------|------|
| S1 | ID 生成 | `done` | `ids.new_id` 正确,符合 database.md §9.1;与 `_utils.new_id` 行为一致 |
| S2 | 时间戳格式(ISO/UTC 一致性) | `missing` | `common.utc_now_iso` 与 `_utils.now_iso` 均不符 SSOT `...SS.mmmZ`;A6 实证为 bug(R1/R2) |
| S3 | 日志 | `partial` | `get_logger` 能用但无级别配置/审计落库,远薄于 legacy `log.ts`(R6) |
| S4 | 错误类型体系 | `partial` | `SmindError` 是空壳,无错误码/HTTP 映射,0 使用,远薄于 legacy `errors.ts`(R5) |
| S5 | 配置加载与默认值 | `partial` | `Settings`/`load_settings` 机制正确,但相对路径默认值脆弱(R7) |
| S6 | 契约 dataclass 完整性 | `missing` | `contracts` 2 个无校验 dataclass + 0 import,A3 确认盲点 B(R4) |
| S7 | 已知风险:contracts 过薄(疑 B) | `done`(已核实=B) | 确认且更严重(死代码) |
| S8 | 已知风险:time.py 格式须与 strftime 一致(疑 L) | `done`(已核实=L) | A6 确认为真 bug,blocker |

### 3.1 对齐结论

- **done**: `3`（S1、S7、S8 —— 注:S7/S8 是"已核实"的风险确认)
- **partial**: `3`（S3、S4、S5）
- **missing**: `2`（S2、S6）
- **stale**: `0`
- **out-of-scope-by-design**: `0`

> 它更像"能 import、能跑的最小占位骨架",而非"可作为全系统 SSOT 的底座"。核心交付物(时间戳一致性、契约层、错误体系)要么写错、要么是空壳/死代码。

### 3.2 stub / 真实现标定表(index §7.1 必交项)

| 包 | 公开符号 | 标定 | 依据 |
|----|----------|------|------|
| common | `new_id` | 真实现 | `ids.py:4-5` 正确 |
| common | `utc_now_iso` | 真实现但**逻辑错误** | `time.py:5` 格式不符 SSOT |
| common | `get_logger` | 部分 | `logging.py` 仅控制台,无审计/级别配置 |
| common | `SmindError` | 部分(空壳) | `errors.py` 仅 code,0 使用 |
| config | `Settings` | 真实现 | `settings.py` 机制正确,默认值脆弱 |
| config | `load_settings` | 真实现 | `loader.py` lru_cache 单例 |
| contracts | `WorkflowRunContract` | 部分(占位,死代码) | `workflow.py:4-7`,0 import,无校验 |
| contracts | `WorkflowStepContract` | 部分(占位,死代码) | `workflow.py:11-17`,0 import,无校验 |

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | `_utils.py` 属 CR-4 文件 | `遵守(但必须联合 own)` | 未修改任何源码;但 A6 bug 物理落点在此,CR-1 作为时间 SSOT 责任方需与 CR-4 共担,已在 R1/R3 标注双向引用 |
| O2 | C4 可观测性落库 | `误报风险(已澄清)` | logger 不落审计不算 CR-1 缺陷,因落库由内核 events 层承担,本簇 C4 判 n.a. |
| O3 | API 层校验/HTTPException | `遵守` | API 用 pydantic/HTTPException 兜底属上层职责,CR-1 不越界实现路由校验 |
| O4 | legacy 错误码全量移植 | `误报风险` | 不要求 CR-1 一比一移植 25 个错误码;但"完全空壳 + 0 使用 + 无替代声明"仍记 B(R5) |

### 横切维度 C1–C5 对 CR-1 的逐项结论

| 维度 | 结论 | 证据 |
|------|------|------|
| C1 事务与并发 | `n.a.` | CR-1 无 DB 事务/锁逻辑(纯工具/配置/契约) |
| C2 错误处理 | `fail` | `SmindError` 空壳 + 0 使用,无统一错误分类(R5);底座未提供错误落库语义支撑 |
| C3 一致性 | `n.a.` | CR-1 不触碰 core.db/vec.db 跨库操作 |
| C4 可观测性 | `n.a.` | step 事件/审计落库由 `workflow_core/events.py`/`graph.py` 承担,不在本簇;logger 简化属有意收敛(R6) |
| C5 适配层纪律 | `pass` | CR-1 不直接碰文件/sqlite-vec 方言,无越层 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. **R1**:修复 `workflow_core/_utils.now_iso/add_seconds_iso` 的时间格式(丢秒 + 微秒/毫秒混淆),使其与 `core.sql` 的 `strftime('%Y-%m-%dT%H:%M:%fZ')` 字符串严格可比;并增加 round-trip 断言。(A6 高危,确认为真 bug)
  2. **R2**:修复 `common.utc_now_iso()` 使其输出 `YYYY-MM-DDTHH:MM:SS.mmmZ`,与 SSOT 一致。
  3. **R3**:消除时间实现双源,内核统一复用 `smind_common.time`,确立单一 SSOT。
- **可以后续跟进的 non-blocking follow-up**：
  1. **R4**:owner 决策 contracts 层是补全为真契约 SSOT 还是显式降级标注。
  2. **R5**:补错误码/HTTP 映射,或文档声明错误体系归属。
  3. **R7**:Settings 默认路径改绝对/anchor,消除 cwd 依赖。
  4. **R8**:为 CR-1 增加时间格式真断言,消除 smoke 假绿(归并入 CR-8 测试有效性核查)。
- **建议的二次审查方式**：`same reviewer rereview`（时间格式修复后需 reviewer 复跑 round-trip 验证;契约层决策需 owner 介入)
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应,不要改写 §0–§5。`

> 本轮 review 不收口。CR-1 的时间戳 SSOT 存在已实证的高危逻辑错误(A6),直接影响 CR-4 内核 `v_ready_steps`/`v_stale_claims` 的就绪/回收判定,必须先修复时间格式并统一为单一来源,再次更新代码后复审。
