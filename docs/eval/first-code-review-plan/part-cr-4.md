# Nano-Agent 代码审查报告 — CR-4 · 工作流内核 (Workflow Kernel)

> 审查对象: `packages/workflow_core/`(claim / scheduler / leases / retry / restart / purge / events / graph / health / _utils)
> 审查类型: `code-review`
> 审查时间: `2026-05-31`
> 审查人: `Claude (Opus 4.8) 主审 + 4 个 sub-agent 分工作面调查（Face A claim/lease、Face B retry/终态、Face C restart/purge、Face D 事件/时间总账/可观测性）`
> 审查范围:
> - `packages/workflow_core/src/workflow_core/*.py`(11 文件,~850 行)
> - 调用面: `apps/worker/src/smind_worker/main.py`、`apps/api/routes/ops.py`、`management/service.py`、`workflow_clean/service.py`、`workflow_rag/service.py`
> 对照真相:
> - `docs/refactor/index.md`(§4.5 调度语义、§4.4 workflow_steps、§7.1 BEGIN IMMEDIATE、§10.7 restart/purge)、`docs/refactor/core.sql`(v_ready_steps/v_stale_claims/task_claims/workflow_steps/step_attempts/restart_requests/purge_requests + ux_task_claims_active_step)
> - `legacy-family/smind-clean-dispatcher/{flows,services}/*`、`smind-rag-dispatcher/*`、`smind-skill-rag-vectorizer/src/{vectorizer_do,purger_logic}.ts`、`*/core/{db,log,queues}.ts`
> - `docs/eval/first-code-review-plan/part-cr-1.md`(G-CR1-01)、`part-cr-2.md`(G-CR2-02 事务模式)、`part-cr-3.md`(G-CR3-12 purge processing)
> 文档状态: `changes-requested`

---

## 0. 总结结论

- **整体判断**：`内核是全系统状态中心,但其 lease 恢复机制是死代码、时间比较被畸形格式打穿、执行器与 claim 终态职责撕裂导致双重执行、restart 路径非确定性失效 —— 内核当前不具备生产可用的可靠性,绝不可标记为 completed。`
- **结论等级**：`changes-requested`（实质 `blocked`：含 5 个 blocker,均触及状态机核心可靠性）
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 5 个判断（均经主审独立复核/实测)**：
  1. **lease 回收是死代码(critical/D)**：`reap_expired_claims` 全仓**无任何运行时调用**;worker 崩溃后其 claim 永不释放,step 因 `ux_task_claims_active_step` 唯一索引永久卡 `running`,无人工干预不可恢复。
  2. **时间格式打穿 lease 比较(critical/L)**：`now_iso/add_seconds_iso` 缺 `%S`,写入畸形 `lease_expires_at`,与 `v_stale_claims`/reap 的 SQL `strftime` 比较恒错位 → 即使修复 #1,reap 也永不命中。这是 G-CR1-01 在内核的**真正落点**。
  3. **双重执行(critical/L)**：执行器(clean/rag service)在内部就 commit `step='succeeded'` + 下游 step + run 推进,**早于** `succeed_claim`;main 忽略 `succeed_claim/fail_claim` 返回值,副作用无幂等键 → 过期租约/reap 竞态下 artifact/向量重复落盘、状态撕裂。
  4. **restart 非确定性失效(high/L+D)**：restart 用 `now_iso()` 写畸形 `available_at`,`v_ready_steps` 比较结果数据依赖,约 40% 概率(微秒首位 6-9)被重启 step 本分钟内永不就绪 → restart 静默不生效。
  5. **restart 丢失精细粒度(high/B+L)**：无论失败在哪一阶段,restart **总是从 clean 头重跑**;`mode` 参数是死参;丢失 legacy 的按失败 step/阶段精细重启。
- **重要跨簇纠偏(本簇独立验证后修正前序)**：
  - **纠正 CR-1 / G-CR1-01**：CR-1 称时间 bug 使"fresh step 永不就绪"属**过度断言**。实测裁决:`available_at` 对 fresh step(DDL DEFAULT)与 retry step(SQL strftime)**均为正确格式,不受影响**;G-CR1-01 在调度就绪上的影响**仅限 restart 路径**。真正被打穿的比较是 `lease_expires_at`(reap/v_stale_claims)。
  - **纠正 CR-3 / G-CR3-12**：CR-3 称 purge 崩溃"卡 processing 不被重捞"。实测裁决:因 engine 默认隐式事务 + 批末单 commit,崩溃会**回滚整批、request 退回 pending**(可被重捞),**不卡 processing**。但由此暴露另一问题:整批单事务 → 一个坏 request 拖垮整批(R12)。

---

## 1. 审查方法与已核实事实

采用"主审 + 4 工作面并行 sub-agent"。四个 Face 独立实跑取证后回归,主审对 5 个 blocker 全部独立复核(reap 死代码 grep、时间格式实测、执行器自提交 + main 忽略返回值、restart available_at 畸形、processing 崩溃语义)。四个 Face 互相纠偏的结论(CR-1 过度、CR-3 误判)主审已逐一复跑确认。

- **核查实现**：workflow_core 全部 11 文件 + 上述全部调用面。
- **执行过的验证(主审亲测)**：
  - `grep reap_expired_claims` → 仅定义 + __init__ 导出 + 测试,**0 运行时调用**;worker main.py:36-56 调用序列确认无 reap。
  - 时间格式实测:`now_iso()` → `2026-05-31T07:31:863796Z`(缺秒);SQL strftime → `...07:31:15.866Z`;畸形 `lease_expires_at <= 正确 now` 比较失真。
  - `workflow_clean/service.py:118` `UPDATE status='succeeded'` + `:129 commit`(执行器内,早于 succeed_claim);`workflow_rag/service.py:226,233` 同;main.py:53 调 succeed_claim **不检查返回值**。
  - restart.py:79 `available_at=?` 绑定 `now_iso()`(畸形);`v_ready_steps` 用 SQL strftime 比较。
  - process_restart/purge 均批末单 `conn.commit()`(restart.py:138 / purge.py:149)。
- **执行过的验证(sub-agent 实跑)**：reap 比较失真(假阳/假阴构造)、restart 就绪非确定性(微秒首位概率表)、processing 崩溃回滚退 pending、purge delete_chunks 幂等、retry 退避恒 1s、claim BEGIN IMMEDIATE happy-path 安全。
- **复用 / 对照的既有审查**：part-cr-1/2/3 —— 独立复核后引用并**主动纠正**其过度/误判结论。

### 1.1 已确认的正面事实

- **claim 原子性在单 worker happy-path 下成立**:engine 默认隐式事务下 SELECT 不开事务,restart/purge 末尾 commit 后进入 claim,`BEGIN IMMEDIATE` 安全;`ux_task_claims_active_step`(WHERE status='active' 唯一)+ IMMEDIATE 写锁双重兜住 TOCTOU,同一 step 不会被双 claim。
- **主状态转移可观测(C4 基本达标)**:claim/succeed/fail/reap/restart-complete 均成对写 `workflow_events` + `audit_logs`。
- **purge 跨库崩溃窗口可自愈**:vec 侧 `delete_chunks` 幂等(deleted_at IS NULL 守卫),core 回滚后重处理安全;符合设计 §5.5 顺序。
- **attempt 计数自洽**:claim 时 `attempt_count+1`,retryable 判定 `attempt_count < max_attempts`,边界正确。
- **退避 SQL 侧格式正确**:fail_claim 的 `strftime('now','+N seconds')` 实测产出合法 ISO(问题在退避值未接线,见 R7)。

### 1.2 已确认的负面事实

- `reap_expired_claims` 死代码;lease 恢复机制不执行。
- `now_iso/add_seconds_iso` 缺 `%S` → `lease_expires_at`/restart `available_at` 畸形,破坏比较。
- 执行器自提交 succeeded + 下游 step;main 忽略 succeed/fail 返回值;副作用无幂等键 → 双重执行。
- restart 硬编码从 clean 重跑;mode 死参;二次 restart PK 冲突 500。
- retry 退避恒 1s(schema 60s 列从不读);error_code 恒 EXECUTOR_FAILURE。
- `graph.write_workflow_event` 死代码且行为(commit + 正确时间)与内核实用的 `events.append_workflow_event`(无 commit + 畸形时间)错位。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | yes | 11 文件 + 调用面逐处核行号 |
| 本地命令 / 测试 | yes | 5 blocker 主审亲测;reap 比较/restart 就绪/processing 崩溃 sub-agent 实跑 |
| schema / contract 反向校验 | yes | v_ready_steps/v_stale_claims 比较表达式 ↔ 写入格式;step_attempts UNIQUE ↔ id 设计 |
| live / deploy / preview 证据 | n/a | 内核逻辑无需 live |
| 与上游 design / QNA 对账 | yes | index §4.5/7.1/10.7;legacy DO/restarter/finalizer;并纠正 part-cr-1/cr-3 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | `reap_expired_claims` 死代码,lease 恢复不执行,崩溃 step 永久卡 running | critical | correctness / D | yes | worker 循环接线 reap(且须先修 R2) |
| R2 | `now_iso/add_seconds_iso` 缺 %S → lease_expires_at 比较被打穿(reap/health 失真) | critical | correctness / L | yes | 修 _utils 格式串对齐 SQL `SS.mmm` |
| R3 | 执行器自提交 succeeded + main 忽略返回值 + 无幂等键 → 双重执行 | critical | correctness / L | yes | 终态职责归 claim 函数;副作用幂等键;检查返回值 |
| R4 | restart 写畸形 available_at → 被重启 step 非确定性永不就绪(restart 静默失效) | high | correctness / L+D | yes | restart available_at 改用 SQL strftime |
| R5 | restart 总从 clean 重跑,mode 死参,丢失精细重启 | high | scope-drift / B+L | yes | 按 mode/失败 step 决定重启锚点 |
| R6 | 确定性 request_id + 无 ON CONFLICT → 二次 restart/purge PK 冲突 500 | high | correctness / L | no | request_id 随机化或 ON CONFLICT |
| R7 | retry 退避恒 1s,schema retry_backoff_seconds(60)从不读,reap 退避 0s | medium | correctness / B | no | fail_claim 读列 + 指数退避;reap 同 |
| R8 | error_code 恒 EXECUTOR_FAILURE,丢失 legacy 错误分类与不可重试判定 | medium | correctness / B | no | 领域异常带 error_code;据类型决定 retryable |
| R9 | 重复事件写入器:graph(导出/死代码/正确时间/commit) vs events(内用/畸形时间/无commit) | high | correctness / B+D | no | 删 graph,统一 events 且去掉显式 created_at |
| R10 | create_*_request `**kwargs:str` 类型错误 + scope/include_objects 不可达 | medium | scope-drift / B | no | 显式具名参数 + 透传 scope/include_* |
| R11 | step_attempts id=attempt_{claim_id} 依赖 claim↔attempt 1:1,与 UNIQUE 语义错位 | medium | correctness / L | no | id 改 (step_id, attempt_number) |
| R12 | restart/purge 整批单事务 → 一个坏 request 拖垮整批核心改动 | medium | correctness / C1 | no | per-request 事务提交 |
| R13 | 失败/中间态转移只写 audit 不写 event;孤儿文档 purge 跳过 event | medium | correctness / C4 | no | 失败/中间态补 event |
| R14 | new_id 与 common.ids 重复实现(联动 CR-1) | low | reuse | no | 内核复用 smind_common |
| R15 | clean 执行器用 CURRENT_TIMESTAMP(系统第三种时间格式) | low | correctness | no | 统一时间格式(移交 CR-6) |

### R1. `reap_expired_claims` 死代码,lease 恢复不执行,崩溃 step 永久卡 running

- **严重级别**：`critical`
- **类型**：`correctness / D`
- **是否 blocker**：`yes`
- **事实依据**：
  - 主审 grep:`reap_expired_claims` 仅 `leases.py:27`(定义)、`__init__.py:4,13`(导出)、`tests/.../test_kernel_flow.py`(测试),**无运行时调用**。
  - worker `_run_once`(main.py:36-56)调用序列:process_restart → process_purge → claim_one → heartbeat → succeed/fail,**不含 reap**。
- **为什么重要**：
  - lease 过期回收(连同 v_stale_claims、step_attempts 的 lease_timeout 记录)永不执行。worker 在 heartbeat 后崩溃 → claim 永久 `active`、step 永久 `running`;`ux_task_claims_active_step` 阻止任何其他 worker 再 claim → step 永久死锁。legacy DO 靠 alarm 重排 + DO 重启自恢复提供该能力,本地把 reaper 写了却没接线 = 净退化。
- **审查判断**：断点 D。修前必须先修 R2,否则 reap 接线后仍因格式不匹配 0 命中。
- **建议修法**：在 `_run_once` 开头(restart/purge 后、claim 前)加 `reap_expired_claims(core_conn)`,或独立 reaper 循环。

### R2. `now_iso/add_seconds_iso` 缺 %S → lease_expires_at 比较被打穿

- **严重级别**：`critical`
- **类型**：`correctness / L`（G-CR1-01 在内核的真正落点)
- **是否 blocker**：`yes`
- **事实依据**：
  - `_utils.py:6,10` 格式串 `"%Y-%m-%dT%H:%M:%fZ"` 缺 `%S`;Python `%f`=6 位微秒。实测 `now_iso()` → `2026-05-31T07:31:863796Z`(秒槽被微秒占据)。
  - `claim.py:64`/`leases.py:21` 用 `add_seconds_iso` 写 `task_claims.lease_expires_at`(畸形);`v_stale_claims`(core.sql:713)与 `reap`(leases.py:34)用 SQL `strftime('%Y-%m-%dT%H:%M:%fZ','now')`(SQL `%f`=`SS.mmm`,正确)比较。
  - 实测:畸形 lease 与正确 now 字符串比较可构造**假阳(误判 stale)**与**假阴(漏判过期)**。
- **为什么重要**：
  - reap(R1 接线后)与 `collect_health.stale_claims` 都依赖该比较。格式失真 → 误回收活跃 worker 的 claim,或放任死 claim;health 计数失真。
- **审查判断**：逻辑错误 L。`%f` 被误当毫秒后缀,实为 6 位微秒且无前导秒。**这是 G-CR1-01 在内核真正破坏功能的点**(区别于 CR-1 错指的 v_ready_steps fresh step)。
- **建议修法**：`_utils` 改 `"%Y-%m-%dT%H:%M:%S.%fZ"` 并截断到 3 位毫秒,与 SQL `%f` 对齐;或全程统一用 SQL strftime 生成时间。同步修复 G-CR1-02/03(common.time 与双源)。

### R3. 执行器自提交 succeeded + main 忽略返回值 + 无幂等键 → 双重执行

- **严重级别**：`critical`
- **类型**：`correctness / L`
- **是否 blocker**：`yes`
- **事实依据**：
  - `workflow_clean/service.py:118` `UPDATE workflow_steps SET status='succeeded'` + `:103` INSERT 下游 rag step + `:124` run→running + `:129 conn.commit()` —— 全在 `process_clean_step` 内,**早于** succeed_claim。`workflow_rag/service.py:226,233` 同。
  - main.py:53 `succeed_claim(...)` / :56 `fail_claim(...)` **返回值未检查**。
  - clean 副作用(artifact、下游 step)用 `uuid4()` 无幂等键。
- **为什么重要(场景推演)**：
  - worker-A claim(attempt 1)→ 卡住 lease 过期 →(若 R1 修复)reap → step retry_wait → worker-B claim(attempt 2)→ worker-A 恢复,执行器 commit 了 artifact+下游 step+succeeded → 调 succeed_claim(token-A):claim 已非 active → 返回 False(被忽略)→ worker-B 完成再写一遍。**artifact/向量/下游 step 重复落盘,at-most-once 被破坏,且静默无观测。** `WHERE status='active'` 只保护 claim 表自身,保护不了已 commit 的业务副作用。
- **审查判断**：逻辑错误 L。终态写入职责在执行器与 claim 函数间撕裂,缺单一事务边界。
- **建议修法**：执行器只产出结果、不写 step 终态/下游/run 推进;由 succeed_claim/fail_claim 在确认 claim 仍 active 的同一事务内完成终态 + 派生 + 推进;副作用带幂等键;main 检查返回值,False 告警/补偿。

### R4. restart 写畸形 available_at → 被重启 step 非确定性永不就绪

- **严重级别**：`high`
- **类型**：`correctness / L+D`（G-CR1-01 第二落点)
- **是否 blocker**：`yes`
- **事实依据**：
  - `restart.py:79,88` ON CONFLICT `SET available_at=?` 绑定 `updated_at = now_iso()`(畸形)。`v_ready_steps`(core.sql:535)用 SQL strftime 比较。
  - 实测:畸形 available_at 秒槽是微秒首位(0-9),正确 now 秒槽是秒十位(0-5);微秒首位 6-9 时本分钟内 `available_at <= now` 恒 False → 永不就绪。约 40% 概率当前分钟完全不就绪,其余延迟。
- **为什么重要**：被 restart 重启的 `clean:init` step 能否被 claim 数据依赖、间歇失效 → restart 非确定性静默不生效。
- **审查判断**：逻辑错误 L + 调度断点 D。G-CR1-01 在调度就绪上的**唯一真实落点**(fresh/retry step 不受影响,纠正 CR-1)。
- **建议修法**：修 R2 根因;或 restart ON CONFLICT 的 available_at 直接用 SQL `strftime('%Y-%m-%dT%H:%M:%fZ','now')` 与就绪判定同源。

### R5. restart 总从 clean 重跑,mode 死参,丢失精细重启

- **严重级别**：`high`
- **类型**：`scope-drift / B+L`
- **是否 blocker**：`yes`
- **事实依据**：
  - `process_restart_requests` 无条件 INSERT/重置 `stage='clean', action='clean.start', step_key='clean:init'` step + run 重置 `current_stage='clean'`(restart.py:72-99)。`mode` 入参仅写入 audit/event payload,不影响行为。
  - legacy `clean/rag restarter.ts` 有 analyzeHistory + KICKSTART/RECOVERY/FORCE 三态决策,RECOVERY 默认**定位 last-failed step 原地重启**,支持 step/workflow/stage 三种粒度。schema 完整保留 mode/target_step_id/scope_json(core.sql:396-401),设计意图明显要支持精细重启。
- **为什么重要**：rag 阶段失败的 workflow 被整段从 clean 重跑(浪费 + 可能违反幂等);API 暴露的 `mode`(ops.py)是死参。相对 legacy 功能性退化(非有意简化)。
- **审查判断**：盲点 B(粒度缺失)+ 逻辑错误 L(mode 被忽略)。
- **建议修法**：按 mode 分流;recovery 查 run 的 last-failed step/current_stage 决定锚点;至少重置到实际失败的 stage。

### R6. 确定性 request_id + 无 ON CONFLICT → 二次 restart/purge 500

- **严重级别**：`high`
- **类型**：`correctness / L`
- **是否 blocker**：`no`
- **事实依据**：`management/service.py:136` `request_id=f"restart_{workflow_run_id}"`(确定性);`:148` `f"purge_{document_id}"`;`RestartRequestRepository.create`(requests.py:20)裸 INSERT 无 ON CONFLICT;restart_requests.id 是 PK。
- **为什么重要**：同一 workflow 第二次 restart(首次已 completed)PK 冲突抛 IntegrityError → API 500。"重启一次后永久无法再重启"。
- **审查判断**：逻辑错误 L,可重入性缺陷。
- **建议修法**：request_id 用 `new_id("restart")` 随机化,或 INSERT ON CONFLICT,或先查 pending 去重。

### R7. retry 退避恒 1s,schema 列从不读,reap 退避 0s

- **严重级别**：`medium`
- **类型**：`correctness / B`
- **是否 blocker**：`no`
- **事实依据**：`fail_claim(retry_backoff_seconds=1)` 默认 1s,main.py:56 不传 → 恒 1s;`workflow_steps.retry_backoff_seconds DEFAULT 60`(core.sql:270)从未读取;reap(leases.py:76)用 `'now'`(0s)。固定退避,非指数。
- **为什么重要**：设计意图(每 step 可配 60s、可指数)被旁路;失败 step 高频空转重试。
- **审查判断**：盲点 B(schema 列未接线)。
- **建议修法**：fail_claim 从 ws.retry_backoff_seconds 读;考虑 `backoff * 2^(attempt-1)`;reap 同。

### R8. error_code 恒 EXECUTOR_FAILURE,丢失错误分类

- **严重级别**：`medium`
- **类型**：`correctness / B`
- **是否 blocker**：`no`
- **事实依据**：main.py:54-56 `except Exception` 转 fail_claim 不传 error_code → 恒默认 EXECUTOR_FAILURE,termination_reason 恒 executor_failure。legacy `errors.ts:28-76` 有完整 ErrorCodes + 不可重试错误(WORKFLOW_DEFINITION_INVALID 等)。
- **为什么重要**：无法据错误类型区分重试策略(永久性错误也一律重试到上限)。
- **审查判断**：盲点 B/退化。
- **建议修法**：执行器抛带 error_code 的领域异常;main 透传;据类型决定 retryable。

### R9. 重复事件写入器:graph(导出/死代码)vs events(内用)

- **严重级别**：`high`
- **类型**：`correctness / B+D`
- **是否 blocker**：`no`
- **事实依据**：
  - `events.append_workflow_event` 真实调用 6 处(claim/retry×2/leases/restart/purge);`graph.write_workflow_event` **0 内部调用**,仅 `__init__.py` 导出。
  - events 版:传 `created_at=now_iso()`(8 列,畸形),不 commit;graph 版:不传 created_at(7 列,DDL DEFAULT 正确),自带 commit。
- **为什么重要**：公共 API 导出的是没人用、却行为更"正确"的 graph 版,内核自己用有 bug 的 events 版 → 导出面与内核行为不一致。graph 版的 commit 若被用在 claim 的 `BEGIN IMMEDIATE` 内会提前 commit 破坏原子性(当前无该调用路径,属潜在地雷)。
- **审查判断**：B(死代码 + 导出面错误)+ 潜在 D。
- **建议修法**：删 graph.py,统一导出/使用 events 版,并去掉显式 created_at(交 DDL DEFAULT,顺带消除该处时间 bug)。

### R10. create_*_request `**kwargs:str` 类型错误 + scope 不可达

- **严重级别**：`medium`
- **类型**：`scope-drift / B`
- **是否 blocker**：`no`
- **事实依据**：`create_restart_request(conn_or_repo, **kwargs:str)` 必键直取(缺键裸 KeyError);repo `create` 还接受 `scope:dict`/`include_vectors:bool`,但门面层不透传,只用 repo 硬编码默认;`**kwargs:str` 注解对 dict scope 错误。
- **为什么重要**：schema 的 `include_objects`/`scope_json` 精细控制全程不可达(关联 CR-3 G-CR3-05 不删 object_store)。
- **审查判断**：盲点 B(不健壮 + 能力不可达)。
- **建议修法**：改显式具名参数,scope/include_* 可选透传,修正类型注解。

### R11. step_attempts id 依赖 claim↔attempt 1:1,与 UNIQUE 语义错位

- **严重级别**：`medium`
- **类型**：`correctness / L`
- **是否 blocker**：`no`
- **事实依据**：retry.py:35,127 / leases.py:60 用 `id=f"attempt_{claim_id}"` + INSERT OR REPLACE;schema UNIQUE(step_id, attempt_number)。当前每 attempt 一个新 claim,历史不丢,但依赖隐含前提。
- **审查判断**：设计气味/轻微 L,当前不丢历史。
- **建议修法**：`id=f"attempt_{step_id}_{attempt_number}"` 与 UNIQUE 对齐。

### R12. restart/purge 整批单事务 → 一个坏 request 拖垮整批

- **严重级别**：`medium`
- **类型**：`correctness / C1`
- **是否 blocker**：`no`
- **事实依据**：process_restart/purge 循环内多 request,批末单 `conn.commit()`(restart.py:138 / purge.py:149)。实测:循环中途抛异常 → 整批回滚、request 退回 pending(故 CR-3 G-CR3-12"卡 processing"不成立);但前面已成功的 request 的 core 改动也一并回滚。
- **为什么重要**：一个坏 request 使整批核心改动丢失;'processing' 中间态从不持久可见。
- **审查判断**：C1 批量原子缺陷(同时确认 CR-3 G-CR3-12 需纠正为"退回 pending")。
- **建议修法**：per-request 事务提交。

### R13. 失败/中间态转移只写 audit 不写 event

- **严重级别**：`medium`
- **类型**：`correctness / C4`
- **是否 blocker**：`no`
- **事实依据**：restart failed(restart.py:60)、purge failed(purge.py:65)仅 audit 无 event;restart/purge 'processing' 中间态无 event/audit;purge `document.purged` event 在 `run_row is None`(孤儿文档)时被跳过(purge.py:128)。legacy 在这些失败路径有对应 ERROR 级 log。
- **为什么重要**：设计硬约束"所有 step 可观测";失败/中间态 event 缺失,孤儿文档 purge 无 workflow_event。
- **审查判断**：C4 缺口(legacy 失败可观测性反而更全)。
- **建议修法**：失败/中间态补 event。

### R14. new_id 与 common.ids 重复实现

- **严重级别**：`low` · **类型**：`reuse` · **blocker**：`no`
- **事实依据**：`_utils.new_id` 与 `smind_common.ids.new_id` 重复(联动 CR-1 G-CR1-03 时间双源)。
- **建议修法**：内核复用 smind_common,确立单一来源。

### R15. clean 执行器用 CURRENT_TIMESTAMP(第三种时间格式)

- **严重级别**：`low` · **类型**：`correctness` · **blocker**：`no`
- **事实依据**：`workflow_clean/service.py:118` `finished_at=CURRENT_TIMESTAMP` → SQLite 产出 `YYYY-MM-DD HH:MM:SS`(空格分隔,无 T/Z/毫秒),与畸形 now_iso、正确 strftime ISO 都不同 —— 系统第三种时间格式。
- **审查判断**：时间格式碎片化,移交 CR-6 深审。
- **建议修法**：统一全系统时间格式来源。

---

## 3. In-Scope 逐项对齐审核

> 计划项来自 index §3 CR-4 表格的"关注"与"已知风险"。

| 编号 | 计划项 / 设计项 | 审查结论 | 说明 |
|------|----------------|----------|------|
| S1 | claim 事务(BEGIN IMMEDIATE)+ v_ready_steps 语义 | `done` | 单 worker happy-path 原子安全,唯一索引兜 TOCTOU |
| S2 | lease 过期回收(v_stale_claims) | `missing` | R1 reap 死代码 + R2 比较被打穿,双重失效 |
| S3 | retry 退避与 max_attempts | `partial` | max_attempts 自洽;退避恒 1s 未接线(R7) |
| S4 | restart/purge 请求消费 | `partial` | 能消费,但 restart 非确定性失效(R4)、从 clean 重跑(R5)、二次 500(R6)、批量单事务(R12) |
| S5 | 事件/审计落库(C4) | `partial` | 主转移达标;失败/中间态缺 event(R13);重复写入器(R9) |
| S6 | 已知风险 G-CR1-01 在内核落点(CR-1 联合 own) | `done`(已核实=纠偏) | 真正落点是 lease_expires_at(R2)+ restart available_at(R4);CR-1 的 fresh step 断言撤回 |
| S7 | 已知风险 G-CR2-02 事务模式 | `done`(已核实) | claim happy-path 安全;批量单事务(R12)是另一面 |

### 3.1 对齐结论

- **done**: `3`(S1、S6、S7)
- **partial**: `3`(S3、S4、S5)
- **missing**: `1`(S2)
- **stale**: `0`
- **out-of-scope-by-design**: `0`

> 它更像"claim/调度的快乐路径已实现,但故障恢复(lease reap)、重试退避、restart 三大可靠性支柱要么是死代码、要么被时间 bug 打穿、要么非确定性失效",而非 completed。内核作为"restart/retry/purge 控制中心"的核心承诺(设计 §4.1)尚未兑现。

### 3.2 stub / 真实现标定表(index §7.1 必交项)

| 符号 | 标定 | 依据 |
|------|------|------|
| `claim_next_step` | 真实现 | 原子安全(单 worker) |
| `WorkflowScheduler.claim_one` | 真实现 | 薄封装 |
| `heartbeat_claim` | 真实现(写畸形 lease) | R2 |
| `reap_expired_claims` | **死代码** | R1 无调用 + R2 比较失效 |
| `succeed_claim` | 真实现(职责撕裂) | R3 与执行器冲突 |
| `fail_claim` | 真实现(退避/错误码未接线) | R7/R8 |
| `process_restart_requests` | 真实现(非确定性失效) | R4/R5/R6/R12 |
| `process_purge_requests` | 真实现(跨库自愈但批量单事务) | R12;CR-3 R5 不删对象 |
| `append_workflow_event`/`append_audit_log` | 真实现(畸形时间) | R2/R9 |
| `write_workflow_event` (graph) | **死代码** | R9,0 内部调用 |
| `collect_health` | 真实现(stale 计数失真) | R2 |

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | G-CR1-01 根因修复(_utils) | `本簇联合 own` | 物理落点在 CR-4 _utils.py,根因是 CR-1 时间 SSOT 缺失;R2 给出修法,需 CR-1/CR-4 联合修 |
| O2 | 执行器业务逻辑(clean/rag service) | `部分(移交 CR-6/7)` | 本簇审执行器与 claim 终态的职责边界(R3),业务逻辑归 CR-6/7 |
| O3 | CR-3 G-CR3-12(purge processing) | `已纠正` | 实测裁定不成立(批回滚退 pending),改记为 R12 批量单事务问题 |
| O4 | CR-3 G-CR3-05(purge 不删对象) | `复核成立(归 CR-3)` | 本簇确认 + 补充 R10 scope 不可达根因,不重复深挖 |
| O5 | CR-1 v_ready_steps fresh step 断言 | `已纠正` | 实测 fresh/retry available_at 走 SQL 正确;撤回 CR-1 该断言,收窄至 R4 restart |

### 横切维度 C1–C5 对 CR-4 的逐项结论

| 维度 | 结论 | 证据 |
|------|------|------|
| C1 事务与并发 | `partial` | claim 原子安全(正面);但执行器/claim 职责撕裂致双重执行(R3)、批量单事务(R12) |
| C2 错误处理 | `fail` | error_code 塌缩(R8);main 忽略 succeed/fail 返回值(R3) |
| C3 一致性 | `partial` | purge 跨库自愈(正面);vectorize 窗口(CR-3 R13);lease 比较失真(R2) |
| C4 可观测性 | `partial` | 主转移达标(正面);失败/中间态缺 event(R13);重复写入器(R9) |
| C5 适配层纪律 | `n.a.(本簇)` | 内核裸 SQL 访问 core.db(同 CR-2 R5 记录);非 ObjectStore/VectorStore 越层 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`changes-requested`（实质 blocked：5 个 blocker 触及状态机核心可靠性)
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. **R2(根因,联动 CR-1)**:修 `_utils.now_iso/add_seconds_iso` 时间格式 —— 这是 R1/R4/health 失真的共同前提,必须先修。
  2. **R1**:worker 循环接线 `reap_expired_claims`(R2 修复后才有效),恢复 lease 故障回收。
  3. **R3**:消除执行器与 claim 函数的终态职责撕裂,副作用幂等键,main 检查返回值 —— 杜绝双重执行。
  4. **R4**:restart 的 available_at 改用 SQL strftime,使重启 step 确定性就绪。
  5. **R5**:restart 按 mode/失败 step 决定重启锚点,恢复精细重启(或显式声明 P 阶段只支持 clean 全量重启)。
- **可以后续跟进的 non-blocking follow-up**：
  1. **R6** 二次 restart 可重入;**R7** 退避接线 + 指数;**R8** 错误分类;**R9** 删除重复事件写入器。
  2. **R10** create_* 入参/scope 透传;**R11** step_attempts id;**R12** per-request 事务;**R13** 失败/中间态 event。
  3. **R14** new_id 复用 common;**R15** 时间格式统一(CR-6)。
- **建议的二次审查方式**：`independent reviewer`（R1/R2 修复后需复跑 reap 命中 + lease 过期回收回归;R3 需复跑过期租约双重执行场景;R4 需复跑 restart→就绪→claim 端到端)
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应,不要改写 §0–§5。`

> 本轮 review 不收口。CR-4 是全系统状态中心,但其故障恢复(reap 死代码 R1 + lease 比较被打穿 R2)、副作用一致性(双重执行 R3)、restart(非确定性失效 R4 + 丢失精细粒度 R5)三大支柱均未达可靠生产标准。claim 快乐路径与主转移可观测性是健康的。本簇同时独立纠正了 CR-1(v_ready_steps fresh step 断言过度)与 CR-3(purge processing 卡死误判)两处前序结论。须先修 R1–R5 再复审。

---

## 附录 · 内核时间格式落点总表(Face D 实证)

| 列 | 写入来源 | 格式 | 是否比较/排序 | 影响 |
|---|---|---|---|---|
| task_claims.lease_expires_at | claim/heartbeat `add_seconds_iso` | **畸形** | **WHERE** v_stale_claims/reap | **严重(R2):reap 误/漏回收** |
| workflow_steps.available_at (fresh) | DDL DEFAULT strftime | 正确 | WHERE v_ready_steps | 不受影响(纠正 CR-1) |
| workflow_steps.available_at (retry) | retry/leases SQL strftime | 正确 | 同上 | 不受影响 |
| workflow_steps.available_at (restart) | **restart.py:79 `now_iso`** | **畸形** | 同上 | **R4:仅 restart step 受影响** |
| workflow_events.created_at (events 版) | events.py:34 `now_iso` | 畸形 | ORDER BY | PY 自洽,排序内部一致,影响小 |
| audit_logs.created_at | events.py:66 `now_iso` | 畸形 | ORDER BY | 同上,影响小 |
| claimed_at/started_at/finished_at/updated_at/last_heartbeat_at | `now_iso` | 畸形 | 否 | 仅审计展示,影响小 |
| restart/purge_requests.created_at | DDL DEFAULT strftime | 正确 | ORDER BY ASC | 正确 |
| workflow_runs.created_at | DDL DEFAULT strftime | 正确 | ORDER BY DESC(选最新 run) | 正确 |
| workflow_clean finished_at | CURRENT_TIMESTAMP | **第三种格式** | 否 | R15,移交 CR-6 |
