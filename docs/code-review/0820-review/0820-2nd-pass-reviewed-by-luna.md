# Nano-Agent 代码审查模板

> 审查对象: 0820-review / NS5-0820-bug-fixes
> 审查类型: rereview | mixed
> 审查时间: 2026-08-20
> 审查人: luna
> 审查范围:
> - docs/closure/0820-review/NS5-0820-bug-fixes-closure.md
> - docs/code-review/0820-review/VF-ledger-0820-1st-review.md
> - src/、api/、tests/、src/persistence/migrations/ 以及 0820-review 相关 git 提交
> 对照真相:
> - docs/plan/new-start/NS5-0820-bug-fixes.md
> - docs/closure/0820-review/NS5-0820-bug-fixes-closure.md
> - docs/code-review/0820-review/VF-ledger-0820-1st-review.md
> 文档状态: changes-requested

---

## 0. 总结结论

> 核心修复骨架已经落地，但运行时取消、跨载体 durable state、Turso 生产可用性、leaf-worker 安全边界和全链路测试证据仍未闭合；本轮不应关闭。

- **整体判断**：第一轮提交解决了若干真实问题，但 closure 中的 completed/partial 边界与当前实现不完全一致，且仍存在会造成数据丢失、错误归因、伪造内网身份或永久不可用的 blocker。
- **结论等级**：changes-requested
- **是否允许关闭本轮 review**：no
- **本轮最关键的 1-3 个判断**：
  1. Turso 默认配置不能形成可工作的 ready/claim 主链；readiness 探针还会把数据库级 journal mode 从 wal 改为 mvcc，属于持久化平台阻断。
  2. external_key、human review、generation evidence、outbox、CAS object 和 worker cancellation 之间仍有非幂等或不可恢复的断点，不能以“已加 CAS/lease”推断业务状态已收敛。
  3. XFF、chunked body、CLI 子进程/环境、public payload 以及 Turso e2e 测试协议仍不足以证明接口安全和真实生产链路。

---

## 1. 审查方法与已核实事实

### 1.1 范围与文档路径核对

- 已读取并核对：
  - docs/closure/0820-review/NS5-0820-bug-fixes-closure.md
  - docs/code-review/0820-review/VF-ledger-0820-1st-review.md
  - docs/plan/new-start/NS5-0820-bug-fixes.md
  - .adocs/templates/code-review.md
- 用户指定的 docs/issue/v3-ready/VRX5-bounded-execution-activation-closure.md 在当前仓库不存在，git 历史中也没有该路径。为避免静默替换，本报告明确以 closure 实际引用的 VF-ledger-0820-1st-review.md 作为第一轮 VF 对照文档，并把路径缺失列为文档治理缺口。
- 未读取或引用仓库中其他 reviewer 的分析报告。本报告的判断来自当前代码、迁移、测试、git 历史和本轮临时复现；并行 agent 的输出只作为切片搜寻结果，所有纳入的 blocker 均再次以代码或本地结果核对。

### 1.2 Git 提交历史与第一轮修复簇对账

| 修复簇 | 主要提交 | 本轮对账 |
|---|---|---|
| P1 runtime / UoW / heartbeat / outbox / GC | d728d0b | 事务主体与部分 lease 保护成立，但 BEGIN 取消窗口、heartbeat 异常、outbox stale-owner 竞态和跨载体 GC 断点仍在 |
| P2 Turso / CAS / migration / readiness | 4ad95c5 | migration 与能力探针加入，但默认 ready 逻辑、全局 journal mode、副作用 schema 检查和 TTL 仍不完整 |
| P3 inference / CLI / evidence | fd5c969 | stdin 与部分 evidence 绑定已加入，但 gate double-release、默认 evidence 桶、timeout/client 生命周期和子进程边界未闭合 |
| P4 serving / proof / retrieval / acquisition | 52e3913、c7c74f2 | serving 查询约束增强，但 raw/clean、namespace、external_key revision、human review lifecycle 仍有逻辑冲突 |
| P5 proxy / extras / body / rate boundary | 34c86b6 | 规则更明确，但空 trusted CIDR 信任 XFF 和无 Content-Length body 绕过上限仍违反计划中的 fail-closed 合同 |
| P6 tests / wheel / ruff | 7bffb70、f7bec3f | ruff 与 migration wheel 证据成立；source-grep、吞异常、弱断言和 Turso/SQLite 混用测试仍使全链路证据不充分 |
| closure / remainder / self-audit | 59a3a8f、ee1f38f、c7c74f2、8cb2cb4 | 文档承认了 VF36、VF52、VF62、VF86、VF40.r 等余项，但这些余项与 0820-review “完成全部问题修复”的目标不相容，且部分真实 bug 被放进了 deferred 叙述 |

### 1.3 审查 DAG、todo-list 与 agent fleet

本轮执行 DAG：

    A0 范围/文档路径核对
       └─> A1 git 历史与 closure claim 对账
              ├─> B1 幂等、竞态、durable state
              ├─> B2 leaf-worker 接口、安全、运行时稳定性
              ├─> B3 Turso、SSOT 双写、可观测性
              └─> B4 本地复现与定向测试
                     └─> C1 证据去重、严重性分级、commit 归因
                            └─> D1 模板化写报告
                                   └─> D2 静态一致性复核

已完成的 todo：

- 核对用户给出的 VF 路径是否存在，并确定 closure 实际引用的 ledger。
- 按 P1 至 P6 聚类检查提交意图、代码落点、测试落点和 closure 声明。
- 并行发起四个定制切片：
  - 历史/closure 对账：逐提交反向验证“已修复”是否确实覆盖原问题，寻找修复冲突。
  - 幂等/竞态/durable state：围绕重复请求、取消点、租约失效、进程崩溃和恢复逐个 await 建立时序。
  - leaf-worker：围绕 untrusted input、HTTP header/body、CLI argv/stdin、子进程、timeout、取消和错误分类建立攻击路径。
  - Turso/SSOT：围绕 migration/readiness、CAS bytes、catalog/reference、vector/proof/pointer、evidence/metrics/sidecar 检查双写断点。
- 对关键切片进行独立本地复现，聚合后删除重复结论，只保留能够归因到实现、合同或证据链的 findings。
- 按模板写入本报告，并在落盘前检查“事实、判断、建议”是否分离。

四个对抗性 prompt 的共同约束是：只读代码、迁移、测试和 git 事实；不读取既有 reviewer 报告；不修改工作树；对每个结论给出文件/行号、失败时序和最小修法。并行结果已同步到本报告的 finding 归并中。

### 1.4 执行过的验证

- 通过：uv run pytest tests/unit/test_ns5_phase1_runtime.py tests/unit/test_ns5_phase2.py tests/unit/test_ns5_phase3.py tests/unit/test_ns5_phase4.py tests/unit/test_ns5_phase5.py tests/unit/test_ns5_audit_remainder.py tests/unit/test_inference_runtime.py -q
- 通过：Turso driver、security boundary、D04 write paths、domain、integration、NS5 Turso mainchain 及 retrieval unit/access 等定向集合。
- 通过：uv run ruff check .
- 通过：uv build；生成 wheel 中可见 15 个 migration SQL 文件。
- 未完成全量绿灯：uv run pytest -q 在首批失败后中断。已观察到 generation pipeline、inline ingress 等任务在超时后仍为 running，以及 human review、intake reactivate、index rebuild、intake rebuild metadata 等 e2e 直接用 sqlite3 读取 Turso 载体而报 sqlite3.DatabaseError: file is not a database。不能把该命令表述为全量通过。
- 本地复现：
  - inference retry 的退避等待中取消，得到 RuntimeError: inference concurrency gate release is unbalanced。
  - public human-review approve 返回 200 后，item 仍为 deactivated，publication validation process 仍为 running。
  - 相同 external_key 的第二次顺序请求返回 201，随后任务进入 failed，未收敛为成功 no-op/replay。
  - HealthAggregator 的 ttl_seconds=5 连续 ready 两次，probe 被执行两次。
  - Turso readiness 前后外部连接看到的 PRAGMA journal_mode 为 wal -> mvcc。
  - SubprocessClaudeCli 的环境保留 AWS_SECRET_ACCESS_KEY、ANTHROPIC_API_KEY 等非 MKB 变量。
  - layered content 的 processed_at 为无效日期前缀时仍能通过当前正则校验。

### 1.5 已确认的正面事实

- immediate_transaction 在已经进入事务后的 body/commit 异常路径会捕获 BaseException，并尝试 rollback；rollback/commit 不确定时会 discard connection。
- P2 的 migration apply、重复 migrate、Turso persistence port 的基本 execute/commit/rollback 路径在当前 pyturso 版本的定向测试中可运行。
- retrieval 的主要 serving 查询已绑定 active namespace、active pointer、publication proof、generation artifact、serving revision 和 complete-set 条件。
- native ANN 未被伪装为已实现能力；当前 factory 会拒绝不支持的 native_ann 路径。
- CLI 生产执行路径已倾向 stdin transport，且部分测试确实验证了 prompt 不应进入 argv。
- ruff、定向 unit/domain/integration 和 migration wheel 构建证据均为正面信号，但它们不能覆盖下列运行时与 e2e 缺口。

### 1.6 已确认的负面事实

- “cancellation-safe”只覆盖事务已开始后的窗口；BEGIN await 本身仍在保护区之外。
- 多个修复以单进程锁、内存 dict 或单次查询为边界，未形成跨 worker、跨连接、跨重启的 durable invariant。
- closure 已明确标记的 VF36、VF52、VF62、VF40.r、VF86 等余项仍能在代码或测试中观察到；其中部分属于本轮真正的 correctness/security blocker，不应通过文档改名为 deferred。
- readiness 与测试 harness 的“绿色”不能证明真实 Turso 业务主链：默认 readiness 失败、schema 检查过窄、多个 e2e 仍绕过 persistence port。

### 1.7 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|---|---|---|
| 文件 / 行号核查 | yes | 逐项核查 runtime、persistence、API、migration、worker、object/vector 和测试实现 |
| 本地命令 / 测试 | yes | 使用定向 pytest、ruff、uv build 和临时 Turso/SQLite 复现；全量 pytest 未宣称通过 |
| schema / contract 反向校验 | yes | 对照 migration unique/index、Pydantic/API 合同、layered JSON schema、retrieval serving 条件 |
| live / deploy / preview 证据 | no | 本轮没有真实 Turso Cloud、GPU、Claude 或生产部署凭证；不把 owner-gated live 项伪装成已验证 |
| 与上游 design / QNA 对账 | yes | 使用 NS5 action plan、第一轮 VF ledger 和 closure；用户指定但不存在的路径已明确记录 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|---|---|---|---|---|---|
| R1 | BEGIN 阶段取消未被 UoW 保护 | high | correctness | yes | 将 BEGIN 纳入不间断保护；不确定时 discard |
| R2 | inference retry 退避取消导致 gate double-release | high | correctness | yes | 明确 lease 所有权并置空已释放句柄 |
| R3 | external_key 解析/写入非原子且 revision 固定为 1 | critical | correctness | yes | durable idempotency record + 唯一约束 + ordinal/CAS |
| R4 | human review approve 不恢复可服务生命周期 | high | correctness | yes | 独立 pending/review projection，approve/reject 原子切换 |
| R5 | heartbeat 异常不能可靠 fencing worker | high | correctness | yes | heartbeat exception 必须进入 fail/fence 状态 |
| R6 | outbox stale owner 状态写入不检查 rowcount | high | correctness | yes | 所有 lease transition CAS 后再写 event/metric |
| R7 | generation evidence 仍是易丢失且可串 Process 的内存桶 | high | correctness | yes | durable、process/fence/invocation 绑定，删除默认桶 |
| R8 | CAS object 的 GC 与引用写入存在跨载体数据丢失竞态 | critical | correctness | yes | delete fence 或统一 durable delete protocol |
| R9 | tombstoned stored object 可被多条路径复用 | high | correctness | yes | 统一 live-object lookup 并过滤 tombstone |
| R10 | 默认 Turso profile 永远无法 ready/claim | critical | platform-fitness | yes | serial profile 与 readiness gate 重新定合同 |
| R11 | readiness probe 修改数据库全局 journal mode | critical | correctness | yes | 不在生产主库执行变更性 probe |
| R12 | migration ledger 不能证明核心 schema 完整 | high | correctness | yes | schema manifest + 关键表/列/索引/trigger 校验 |
| R13 | raw/clean 业务制品共用 acceptance envelope bytes | high | correctness | yes | 两套独立 bytes/digest/size/handle |
| R14 | namespace/维度切换与 generation/purge 合同未闭合 | high | correctness | yes | identity namespace + durable generation reservation |
| R15 | 空 trusted-proxy 配置仍可被私网 peer 伪造 XFF | high | security | yes | 只有明确 CIDR 才信任 forwarded headers |
| R16 | body cap 只检查 Content-Length，chunked body 可绕过 | high | security | yes | 包装 receive 流式累计并超限立即 413 |
| R17 | leaf-worker 的环境、子进程和 timeout 边界不安全 | high | security | yes | 严格 env allowlist、进程组终止、真正请求级 timeout/cap |
| R18 | public payload/source 输入可能把 secret/URL 写入 durable state | high | security | yes | public schema 复用安全验证并对 source 做 secret-free normalization |
| R19 | readiness/sidecar/metrics 与治理状态不能完整反映失败 | medium | observability | no | TTL、failure reason、sidecar 生命周期和 durable diagnostics |
| R20 | P6 假绿测试与 Turso/SQLite 协议漂移仍在 | high | test-gap | yes | 测试只通过真实 PersistencePort，删除 source-only/吞异常断言 |
| R21 | closure/ledger 路径缺失且多个 partial 被叙述成可收口 | medium | docs-gap | yes | 修复 SSOT 文档入口并按 blocker 重新计算 closure |

### R1. BEGIN 阶段取消未被 UoW 保护

- **严重级别**：high
- **类型**：correctness
- **是否 blocker**：yes
- **事实依据**：
  - src/persistence/uow.py:26-35 中，await asyncio.to_thread(connection.execute, begin_sql) 位于 try 之前；try 只从 yield body 开始。
  - P1 提交确实保护了 body、commit、rollback，但没有覆盖 BEGIN 的取消窗口。
- **为什么重要**：
  - cancellation 可能发生在数据库已经接受 BEGIN、Python 尚未记录状态的窗口。连接池重新复用该连接时，可能遇到未完成事务、锁残留或下一次 BEGIN 失败。
  - 这会把 worker 取消转化为后续任务的随机数据库故障，且当前 discard 逻辑不会必然执行。
- **审查判断**：
  - 第一轮“事务取消安全”只完成了后半段；不能宣称整个 UoW cancellation-safe。
- **建议修法**：
  - 把 BEGIN 纳入同一 protected region；若 BEGIN 的完成状态因取消不可知，直接 discard connection，不把连接交还池。
  - 增加“取消 BEGIN、再次借用同一连接、检查无锁/无事务”的可观测测试。

### R2. inference retry 退避取消导致 gate double-release

- **严重级别**：high
- **类型**：correctness
- **是否 blocker**：yes
- **事实依据**：
  - src/runtime/inference/facade.py:385-409 在 retry 时先 release(lease)，再 sleep；finally 仍无条件 release(lease)。
  - 本地取消退避 await 的复现结果为 RuntimeError: inference concurrency gate release is unbalanced。
- **为什么重要**：
  - 取消本应是正常的 bounded execution 控制流，却被 gate 状态错误包装；这可能污染背压计数、误判 worker failure，并进一步触发错误的 retry/poison 路由。
- **审查判断**：
  - P3 的重试修复引入了 lease 生命周期冲突；当前不是单纯测试缺口。
- **建议修法**：
  - 释放后立即将 lease 置为 None；重新 acquire 后再赋值。
  - 将 acquire/release 绑定到带状态的 lease object，并测试 transport retry、cancel、timeout、worker shutdown 四种时序。

### R3. external_key 解析/写入非原子且 revision 固定为 1

- **严重级别**：critical
- **类型**：correctness
- **是否 blocker**：yes
- **事实依据**：
  - src/runtime/intake/acquisition_ingest.py:91-178 先生成新 UUID，再在独立读取事务中解析已有 identity；source insert、item/revision 写入不是一个原子 idempotency fence。
  - src/runtime/intake/acceptance_snapshot.py:133-145 将 revision_ordinal 固定为 1；migration 001 对同一 item 的 revision ordinal 有唯一约束。
  - registered API 路径在 acquisition_ingest.py:240-307 仍可直接产生新 identity。
  - 本地顺序复现显示相同 external_key 的第二次请求先返回 201，随后任务进入 failed，而不是成功 no-op 或可重放结果。
- **为什么重要**：
  - 并发或重试请求可能各自通过“未找到”读取，产生多个 task/process；顺序重放也会碰到 ordinal=1 唯一约束或错误地复用旧 snapshot。
  - “数据库里最终只有一份 source/item”不等于接口幂等：调用方看到 201 后仍可能得到失败任务。
- **审查判断**：
  - 这是第一轮修复后的逻辑断点，不是 VF86 测试环境单独造成的问题。
- **建议修法**：
  - 以 team + source identity + external_key 建立 durable idempotency record/唯一约束，在同一事务中 resolve、reserve、写入和返回既有结果。
  - 同 fingerprint 重放必须返回既有成功/进行中状态；内容变化必须按当前最大 ordinal + 1 建新 revision，并用 predecessor/fingerprint CAS 防竞态。

### R4. human review approve 不恢复可服务生命周期

- **严重级别**：high
- **类型**：correctness
- **是否 blocker**：yes
- **事实依据**：
  - src/runtime/intake/acceptance_snapshot.py:106-107 在需要 review 时把 item lifecycle 设为 deactivated。
  - src/runtime/task/task_projections.py:378-389 与 src/runtime/workflow/runtime_gates.py:245-285 处理 public gate decision，但 approve 路径没有一致调用 item lifecycle publish/activate 事务。
  - src/services/intake_lifecycle/lifecycle_publish.py:75-77 要求 item active 且有 serving revision 才能发布。
  - 本地 public approve 返回 200 后，item 仍为 deactivated，publication validation process 仍为 running。
- **为什么重要**：
  - 用户得到“approve 成功”语义，但新 revision 仍不可服务；gate、item lifecycle、publication proof 三个状态分裂。
  - reject 新 revision 时还可能撤掉旧 serving revision；review 不是单纯新 item 时，旧服务版本保护不足。
- **审查判断**：
  - closure 已把 VF40.r 标为 partial；P4-08 不能按 completed 关闭。
- **建议修法**：
  - 增加 pending/reviewing projection 或显式状态，不使用 deactivated 同时表示“待审”和“主动停用”。
  - approve/reject、serving revision、publication gate、transition before/after 必须在一个 durable transaction 中完成；reject 新 revision 应保留旧 serving revision。

### R5. heartbeat 异常不能可靠 fencing worker

- **严重级别**：high
- **类型**：correctness
- **是否 blocker**：yes
- **事实依据**：
  - src/runtime/workflow/worker.py:139-162 的 heartbeat loop 只显式处理 CancelledError；adapter/数据库异常没有进入与 heartbeat=False 相同的 fence 路径。
  - worker.run_once 的 finally（worker.py:134-137）只取消并等待 heartbeat task，没有把 heartbeat task 的异常转成当前 process 的失败或 lease revoke。
- **为什么重要**：
  - heartbeat 连接失败时，handler 仍可能继续执行并 accept outcome；原 lease 到期后另一 worker 可以 reclaim，同一 process 形成双写/双发布。
- **审查判断**：
  - “heartbeat 失败会停止 handler”只对返回 false 的正常分支成立，对异常分支不成立。
- **建议修法**：
  - heartbeat task 与 handler 使用共享 cancellation/fence signal；任何非取消异常都必须触发 handler cancellation、process fence 和 durable failure evidence。
  - 增加 heartbeat exception、lease expiry、reclaim、旧 worker outcome 四段时序测试。

### R6. outbox stale owner 状态写入不检查 rowcount

- **严重级别**：high
- **类型**：correctness
- **是否 blocker**：yes
- **事实依据**：
  - src/runtime/workflow/runtime_outbox.py:343-355、379-406 的 dead/complete/release 路径执行带 owner 条件的 UPDATE 后，没有用 rowcount 判断是否仍是当前 owner，仍可能记录事件或指标。
  - outbox claim/dispatch（runtime_outbox.py:41-128）没有长处理 heartbeat；30 秒 lease 到期后，旧 owner 和新 owner 可交叠。
  - src/runtime/workflow/runtime_repair.py:40-61 对“存在任意 outbox row”的判断没有充分区分 dead/active 状态。
- **为什么重要**：
  - 旧 owner 的迟到结果可以产生假 outbox.dead、假完成或错误 repair 抑制；supervisor 还会把单条异常计入 progressed，持续数据库故障可能被报告成正常运行。
- **审查判断**：
  - 当前 lease 不是完整 fencing token；rowcount 不只是观测指标，而是状态转移的安全条件。
- **建议修法**：
  - 每次状态 transition 必须检查 rowcount=1，只有成功 CAS 才写 event/metric。
  - event 载荷必须含 outbox_id、lease owner、attempt、前后状态；长消费增加 heartbeat，supervisor 失败不能计作 progress。

### R7. generation evidence 仍是易丢失且可串 Process 的内存桶

- **严重级别**：high
- **类型**：correctness
- **是否 blocker**：yes
- **事实依据**：
  - src/runtime/intake/generation_evidence.py:9-32 使用进程内 _pending dict；src/runtime/intake/generation_evidence.py:50-52 只在显式调用时 flush。
  - generation_construct.py:287-290、1002-1035 等调用点存在未传 process_uuid 的 record_pending_generation_evidence，落入默认 key。
  - runtime_outcome.py:471-474 在终态失败时取 process evidence，且有无条件 default bucket fallback。
- **为什么重要**：
  - 进程重启会丢失未 flush 的失败 invocation/stage report；另一个 process 的失败可能取走默认桶中前一个 process 的证据，造成审计和 retry attribution 串台。
- **审查判断**：
  - P3-05 只绑定了部分正常路径，没有覆盖 crash、salvage 和 unrelated failure；内存字典不可能成为 durable SSOT。
- **建议修法**：
  - 将 pending evidence 写入 durable 表或 process outcome 字段，绑定 process_uuid、fencing_generation、invocation_uuid。
  - 删除默认桶和 fallback；缺证据要显式报告 missing，而不是借用别的 process 的 evidence。

### R8. CAS object 的 GC 与引用写入存在跨载体数据丢失竞态

- **严重级别**：critical
- **类型**：correctness
- **是否 blocker**：yes
- **事实依据**：
  - src/services/object_gc.py:196-215 先在数据库事务中检查无引用并提交，随后执行物理 unlink；219-235 再次检查不能恢复已删除 bytes。
  - src/services/artifacts.py:52-84 与 src/storage/local_store.py:27-29、120-133 的数据库事务锁和本地对象锁不是同一 durable fence。
  - promote 在 catalog/reference 写入前完成；进程若在此处崩溃，uncatalogued orphan 不在 object_gc.py:132-159 的数据库扫描范围内。
- **为什么重要**：
  - GC TX1 提交后到 unlink 之间，新引用可以成功提交并指向即将删除的 bytes；第二次检查最多发现“不一致”，无法恢复对象。
  - promote 后 crash 产生的 orphan 没有 catalog row，当前 GC 也没有目录 reconcile，既不能安全回收也不能纳入审计。
- **审查判断**：
  - P1-07 的“两阶段 GC”只降低了单一数据库竞态，尚未形成 CAS bytes 与 Turso references 的统一删除协议。
- **建议修法**：
  - 引入 durable delete fence/deleting 状态；新引用创建必须与 fence CAS 协调，物理删除后再完成 tombstone。
  - 增加 CAS 目录 reconcile 或 durable promoted-object intent，并以 grace period、digest 和 reference fence 处理未 catalog orphan。

### R9. tombstoned stored object 可被多条路径复用

- **严重级别**：high
- **类型**：correctness
- **是否 blocker**：yes
- **事实依据**：
  - 迁移 014 已把 live object unique 约束改为仅针对 tombstoned_at IS NULL。
  - 但 generation_artifacts.py:562、config_snapshots.py:333、index_rebuild_commit.py:305、scatter_intake.py:682、task_create.py:400 的 lookup 没有统一过滤 tombstoned_at IS NULL；services/artifacts.py:142 的实现才是正确参考。
- **为什么重要**：
  - 同 digest/size 重新 promote 后，lookup 可能返回旧 tombstoned stored_object_uuid；新 reference 指向逻辑上已死亡的 row，随后 gate/live-object 查询与 GC 互相矛盾。
- **审查判断**：
  - migration 的 partial unique 修复没有被所有读路径消费，属于“约束修好、调用方仍绕开约束”的典型断点。
- **建议修法**：
  - 提供唯一的 get_live_stored_object(team,digest,size) port，禁止业务路径自行拼 lookup。
  - 补充 tombstone 后重新 promote 的 config、generation、rebuild、scatter、task restart 全路径测试。

### R10. 默认 Turso profile 永远无法 ready/claim

- **严重级别**：critical
- **类型**：platform-fitness
- **是否 blocker**：yes
- **事实依据**：
  - src/runtime/config.py:21-29 默认 persistence_backend=turso、concurrent_writes_required=True、native_vector_required=True。
  - src/persistence/turso/port.py:171-183 在 serial writer 下将 concurrent_writes gate 设为 false，即使 probe 字段为 true。
  - src/runtime/health.py:14-24 将 concurrent_writes 纳入 required gates；TursoPersistence readiness 的默认结果为 concurrent_writes=False、concurrent_writes_probe=True。
  - 真实 mainchain 测试通过显式 concurrent_writes_required=False 绕过该条件，不能证明默认 production profile。
- **为什么重要**：
  - 默认 worker 的 /ready 为 503，WorkflowRuntime.claim_next 不能领取任务；代码可以测试通过但部署后没有业务吞吐。
- **审查判断**：
  - 这是“诚实报告能力不足”与“默认服务不可用”混在一起的配置逻辑冲突。fail-closed 不能成为默认永远不接单的隐式合同。
- **建议修法**：
  - 若当前正式模式就是 serial BEGIN IMMEDIATE，把 serial profile 的默认 required gate 改为可工作配置，并单独暴露 probe 能力。
  - 若必须要求 concurrent writes，则实现真实 BEGIN CONCURRENT 业务路径并补齐 writer/sidecar 协调；两者必须有默认配置测试。

### R11. readiness probe 修改数据库全局 journal mode

- **严重级别**：critical
- **类型**：correctness
- **是否 blocker**：yes
- **事实依据**：
  - src/persistence/engine.py:24-42 的 probe_concurrent_writes 会执行 PRAGMA journal_mode=mvcc。
  - src/persistence/turso/port.py:152-157 调用该 probe 时传 restore_journal_mode=False。
  - 独立临时数据库的外部连接复现结果为 readiness 前 wal、readiness 后 mvcc。
- **为什么重要**：
  - journal_mode 是数据库级持久化状态，不是旁路连接私有状态；高频 /ready 会改变业务连接及其他连接看到的模式，可能改变锁、事务和兼容性行为。
- **审查判断**：
  - closure 中“业务连接不切 journal_mode”的声明与当前实现不一致；这不是可接受的观测副作用。
- **建议修法**：
  - 生产主库 readiness 不执行变更性能力探针；对独立临时库/启动阶段副本探针，或严格保存并恢复外部可见的原模式。
  - 添加探针前后第二连接 journal_mode 相等的硬测试。

### R12. migration ledger 不能证明核心 schema 完整

- **严重级别**：high
- **类型**：correctness
- **是否 blocker**：yes
- **事实依据**：
  - src/persistence/migration_runner.py:148-163 的 verify_migrations 主要验证 migration ledger checksum 和 mkb_tasks 是否存在。
  - publication proof、vector records、outbox、namespace、pointer 等核心表/索引不在同等级结构完整性检查中。
  - 删除 mkb_publication_proofs 等关键表后，ledger checksum 仍可保持正确，readiness 可能继续为 green，直到业务走到对应阶段才失败。
- **为什么重要**：
  - 迁移文件未被篡改不等于运行中的 schema 没被破坏；假绿会让 worker 继续领取任务，把数据库损坏延迟到不可逆的业务阶段。
- **审查判断**：
  - P2-09 的“删除核心表应 not ready”覆盖面不足，当前 migration ledger 不是 schema SSOT。
- **建议修法**：
  - 建立版本化 schema manifest，检查关键表、列、索引、view、trigger 和必要约束；readiness 返回结构化 failure reason。
  - 对 publication、vector、outbox、namespace、generation、pointer 逐项增加破坏性测试。

### R13. raw/clean 业务制品共用 acceptance envelope bytes

- **严重级别**：high
- **类型**：correctness
- **是否 blocker**：yes
- **事实依据**：
  - acquisition_ingest.py:77-84 计算 raw/clean logical digest；acceptance_snapshot.py:63-64、149-184 却以同一个 acceptance envelope 的 bytes/size/handle 作为 artifact。
  - closure 已把 VF36 标为 under-delivery；当前 raw/clean handle 可能相同，而各自 content_digest 不等于该 handle 实际 bytes 的 sha256。
- **为什么重要**：
  - 读取并验证 raw 或 clean 时，digest、size、media type 和 bytes 不是同一制品的事实，审计、重建、去重和下游检索均可能被错误数据污染。
- **审查判断**：
  - 这不是“证据字段还不够精细”，而是 SSOT artifact identity 错配。
- **建议修法**：
  - raw 独立保存原始 bytes，clean 独立保存规范化 UTF-8 bytes；各自独立 promote/catalog/reference/digest/size/media_type。
  - acceptance envelope 只作为 metadata/evidence，不能冒充 raw/clean 制品。

### R14. namespace/维度切换与 generation/purge 合同未闭合

- **严重级别**：high
- **类型**：correctness
- **是否 blocker**：yes
- **事实依据**：
  - vectorize.py:99-104、265-305 和 vector_publish_commit.py:265-305 仍使用 namespace_key=default；model/version/adapter/dimension 变化会返回 VECTOR_NAMESPACE_BINDING_CONFLICT。
  - closure 已将 VF52 标为 partial；两个 worker 可在事务外同时读取 index_generation=N 并选择 N+1，现有 supervisor 的串行限制不是 durable allocator。
  - VectorizeChannelFilter 允许 original/summary，而 vector_purge.py:69-76 只接受 all；tests/e2e/test_vector_purge_generation.py 仍覆盖 partial contract。
- **为什么重要**：
  - 模型或维度切换无法按业务合同创建新 serving namespace；generation 冲突时可能重复计算或丢失发布；purge API、runtime 和测试对“全量/部分”语义不一致。
- **审查判断**：
  - VF52、VF62、purge contract 都是未闭合的真实协议问题，不应全部归类为未来多副本优化。
- **建议修法**：
  - namespace key 纳入 Layer-A identity，或用数据库内 CAS allocator 创建新 namespace；generation reservation 必须在同一 Turso transaction 内完成。
  - 明确 partial purge 是否允许；不允许则收窄 API contract，允许则必须重新计算 proof 并 CAS pointer。

### R15. 空 trusted-proxy 配置仍可被私网 peer 伪造 XFF

- **严重级别**：high
- **类型**：security
- **是否 blocker**：yes
- **事实依据**：
  - src/runtime/security.py:476-499 在 trusted CIDR 为空时，对 private peer 仍可能取 X-Forwarded-For 的首个地址。
  - 本地复现 peer=10.0.0.1、无 trusted CIDR、XFF=127.0.0.1 时，request_ip() 返回 127.0.0.1，is_internal_ip() 判定为 true。
  - closure 对“empty CIDR + private peer 使用 XFF”的描述与 action plan 中“仅 peer 属于显式 trusted CIDR 才解析 forwarded headers”冲突。
- **为什么重要**：
  - 任何能从私网访问服务的客户端都可能伪造内网来源，绕过 /internal、/metrics 或其他 source-IP 安全边界。
- **审查判断**：
  - P5-01 的默认 fail-closed 合同没有实现；私网 peer 不能自动等价于 trusted proxy。
- **建议修法**：
  - trusted CIDR 为空时完全忽略 XFF；仅显式 CIDR 命中时解析，并增加 spoofed private peer regression test。

### R16. body cap 只检查 Content-Length，chunked body 可绕过

- **严重级别**：high
- **类型**：security
- **是否 blocker**：yes
- **事实依据**：
  - api/app.py:527-538 只在 Content-Length 存在且可解析时提前拒绝；缺失或非法时直接 call_next(request)。
  - api/public/routes.py:452-464 仍直接 await request.json()，没有接收流的累计上限。
- **为什么重要**：
  - chunked 或无 Content-Length 请求可在 JSON 解析前把超大 body 读入内存，绕过 P5-08 的 OOM/resource-safety 目标。
- **审查判断**：
  - Content-Length 只能是 fast path，不是完整 body cap。
- **建议修法**：
  - 包装 ASGI receive，逐 chunk 累计并在超过上限时立即返回 413；同时保留 Content-Length 作为提前拒绝优化。
  - 增加无长度、chunked、断流和超限后的连接清理测试。

### R17. leaf-worker 的环境、子进程和 timeout 边界不安全

- **严重级别**：high
- **类型**：security
- **是否 blocker**：yes
- **事实依据**：
  - src/runtime/inference/claude_cli.py:377-379 的 _cli_child_env 仅过滤 MKB 前缀，当前环境中的 AWS_SECRET_ACCESS_KEY、ANTHROPIC_API_KEY、HOME 等变量会进入子进程。
  - claude_cli.py:320-340 先 communicate 再做 output cap 检查；_terminate_process（382-405）只处理主 PID，未建立 process group/杀死 descendants。
  - ClaudeCliRequest.timeout_seconds 默认 900；应用组装路径没有把配置 timeout 可靠注入每个请求。
  - src/llm_adapters/local_vllm.py:206-249 的 singleton client 使用首次创建的 timeout；readiness 先以 5 秒创建后，后续长 generation 可能复用该 timeout；response 也缺少明确的 bytes/structure cap。
- **为什么重要**：
  - 外部 prompt 可诱导 CLI 子进程继承云凭据；恶意/异常子进程可在父进程被终止后继续运行；超大输出会先占满内存；短 probe timeout 会随机截断正常 generation。
- **审查判断**：
  - stdin 修复只解决了 argv 泄漏的一条路径，未完成 leaf-worker 的资源和进程边界合同。
- **建议修法**：
  - 使用显式 allowlist 环境，不把父进程秘密传入 child；使用 process group/session 统一终止 descendants；采用受限 pipe/流式读取，超过 cap 立即 kill。
  - 对每次请求传递真正的 timeout/cap，或按 timeout 建立隔离 client；增加 probe 后长请求和 cancellation 的回归测试。

### R18. public payload/source 输入可能把 secret/URL 写入 durable state

- **严重级别**：high
- **类型**：security
- **是否 blocker**：yes
- **事实依据**：
  - api/contracts/models.py:50-59 的 TeamPatch 以及 TaskPatchRequest:362-377 没有统一调用 assert_safe_public_data。
  - services/teams.py:93-105、runtime/task/task_commands.py:158-177 会保存/回显 payload_extra；task_views.py:61-93 将其返回 public view。
  - services/config_snapshots.py:403-426 对 HTTP source 保留原始 execution payload；acquisition_ingest.py:68-89 将 source descriptor 进入 stage state，signed URL 因而可能进入 durable state。
- **为什么重要**：
  - public API 可把 token、signed URL、连接凭据或未限制的递归 JSON 写进数据库、日志和 API 响应，形成持久化 secret 泄漏和 SSRF/重放风险。
- **审查判断**：
  - P3/P5 的安全验证并未覆盖所有 public mutation 和 source descriptor；“内部调用方可信”不适用于 leaf-worker 接口。
- **建议修法**：
  - public schema 与内部 schema 分离，并在所有 mutation 入口统一执行安全递归验证、深度/键数/字节上限和 secret redaction。
  - durable state 只保存已规范化、无凭据的 source identity；实际凭据使用短期 secret reference，禁止原始 signed URL 落库。

### R19. readiness/sidecar/metrics 与治理状态不能完整反映失败

- **严重级别**：medium
- **类型**：observability
- **是否 blocker**：no
- **事实依据**：
  - src/runtime/health.py:26-45 保存 _ttl_seconds 但没有使用；连续 ready 调用会重复执行 probe，只实现了 in-flight coalesce。
  - src/persistence/turso/sidecar.py:62-78 使用独立连接和独立锁，主写事务竞争时可能 busy；max_queue 没有真实队列，lifespan 也未清晰关闭 sidecar。
  - metrics、GC、retirement、outbox、worker failure 等多个 emitter/scan result 不形成可恢复的 durable failure state；readiness 异常还被折叠成布尔 gates。
- **为什么重要**：
  - 运维无法区分 schema drift、busy、journal probe、vector failure、outbox poison 和 GC/retirement failure；sidecar 丢诊断时也没有可靠的 drop receipt。
- **审查判断**：
  - 这是长期治理目标的 partial，而非当前最先修复的业务 correctness blocker。
- **建议修法**：
  - 选择并实现真实短 TTL cache，或删除误导性的 ttl 参数；readiness 返回结构化 reason。
  - sidecar 要么进入单 writer durable outbox，要么明确 best-effort 丢弃计数、退避和 close 生命周期；补齐 scanner/worker/outbox/GC/retirement metrics。

### R20. P6 假绿测试与 Turso/SQLite 协议漂移仍在

- **严重级别**：high
- **类型**：test-gap
- **是否 blocker**：yes
- **事实依据**：
  - tests/unit/test_ns4_readport_reports.py、test_ns4_jsonl_journal.py 主要通过 inspect.getsource/读取源码文件断言；test_ns4_diagnostic_sidecar.py 吞掉异常后断言无关字段；test_ns4_cw_soak.py 未验证真实业务行数/结果。
  - 多个 tests/e2e 在 app 采用 Turso 时直接 sqlite3.connect 或 SqlitePersistence 读取文件，包括 human_review_gate、generation_pipeline_contracts、intake_reactivate、intake_rebuild_metadata、index_rebuild、inline_ingress_staging 等。
  - 全量测试首批失败中已出现任务保持 running 以及 sqlite3.DatabaseError: file is not a database；定向测试通过不等于真实 Turso 全链路通过。
- **为什么重要**：
  - source-only/吞异常测试不能证明实现行为；SQLite 文件读取更不能证明 Turso port 的事务、rowcount、journal、vector、CAS 和 publication 语义。
  - closure 将一部分问题归入 VF86，但同 external_key、human review、任务持续 running 等问题可以在独立复现中成立，不能整体由 harness waiver 覆盖。
- **审查判断**：
  - P6-01、P6-05、T60 和真实 Turso e2e 证据仍未完成。
- **建议修法**：
  - 测试统一通过 PersistencePort.transaction() 查询；若要测 SQLite，显式使用 sqlite backend，不得把 SQLite 文件当 Turso 数据库打开。
  - 删除 source-grep 和吞异常断言，使用可失败的真实 SUT；新增 clean wheel、默认 Settings、migration、ready、claim、publication、retrieval 的单条 Turso smoke。

### R21. closure/ledger 路径缺失且多个 partial 被叙述成可收口

- **严重级别**：medium
- **类型**：docs-gap
- **是否 blocker**：yes
- **事实依据**：
  - 用户给出的 docs/issue/v3-ready/VRX5-bounded-execution-activation-closure.md 不存在；实际 closure 指向 docs/code-review/0820-review/VF-ledger-0820-1st-review.md。
  - closure 的 P1-P6 表格已经承认 VF36、VF52、VF62、VF86、VF40.r、VF85 等 partial/deferred，但 action-plan 仍把部分对应问题放在本轮 in-scope。
  - closure 的“honest closure”文字不能替代对代码真实行为和 hard gate 的验证。
- **为什么重要**：
  - 审查真相入口不稳定时，后续 reviewer 可能对不同 VF 集合审查，并把明确 under-delivery 误当作已完成治理。
- **审查判断**：
  - 这是本轮不收口的证据治理 blocker；不是要求补一份说明文档就能消除的代码问题。
- **建议修法**：
  - 选定唯一 VF ledger canonical path，修正所有引用并建立 redirect/alias 规则。
  - 重新以 blocker、partial、deferred 三类生成 closure，不得把真正的 correctness/security 缺口仅改名为 owner-gated。

### 2.2 聚合后的根因与修复归因

| 根因簇 | 直接表现 | 归因到第一轮工作的判断 |
|---|---|---|
| 取消与 lease 所有权没有贯穿完整时序 | R1、R2、R5、R6 | P1/P3 添加了局部 cleanup/lease，但没有把“await 期间状态未知”视为 durable fence；属于修复边界不足 |
| 关系型状态与文件/内存/sidecar 双写没有统一协议 | R7、R8、R9、R13、R19 | P1/P3/P4 修复各自局部载体，未建立跨载体 reconcile/delete fence；属于架构断点 |
| “先查再写”被误当成幂等 | R3、R4、R14 | c7c74f2/8cb2cb4 增加了复用、CAS 或 gate，但关键 identity/lifecycle/generation 没有同事务 reservation；属于逻辑冲突 |
| readiness 只验证能力声明，不验证默认可用性与 schema 完整性 | R10、R11、R12 | P2 的 honest gate 方向正确，但默认配置、probe 副作用和 schema manifest 缺失；属于平台适配不完整 |
| 边界 enforcement 依赖“正常请求形态” | R15、R16、R17、R18 | P3/P5 处理了典型路径，却没有覆盖空配置、chunked、descendant、父环境和 public mutation；属于安全边界遗漏 |
| 测试验证实现痕迹而非业务结果 | R20 | P6 已修掉部分假绿，但仍保留 source-grep、吞异常和 SQLite/Turso 混用；属于证据链未完成 |
| 文档状态与实现状态不同步 | R21 及 VF36/VF52/VF40.r/VF62 | closure 已写入若干 partial，却没有让 hard-gate/verdict 与其一致；属于治理收口错误 |

---

## 3. In-Scope 逐项对齐审核

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|---|---|---|---|
| S1 | P1-01 cancellation-safe UoW | partial | body/commit 后 rollback 有保护，BEGIN await 仍暴露 |
| S2 | P1-04 heartbeat 与 worker fencing | partial | heartbeat=false 有路径，heartbeat exception 和旧 outcome 未闭合 |
| S3 | P1-05/P1-07 outbox、poison、GC | partial | poison 主体存在，stale owner、跨载体 unlink 和 uncatalogued orphan 仍在 |
| S4 | P2 Turso serial writer / honest readiness | partial | probe 字段与 required gate 冲突，默认 profile 不可 claim |
| S5 | P2 migration integrity / schema readiness | partial | ledger/mkb_tasks 检查成立，核心表/列/索引破坏可假绿 |
| S6 | P2-05 ready coalescing / TTL | partial | 只有并发 in-flight coalesce，ttl_seconds 没有缓存语义 |
| S7 | P3 inference retry / concurrency gate | partial | 一般 retry 可测，cancel 退避 double-release |
| S8 | P3-04 CLI stdin/env 与执行预算 | partial | 生产路径偏向 stdin，但 builder、env、child、timeout、output cap 未闭合 |
| S9 | P3-05 generation evidence process binding | partial | 部分调用点绑定，默认桶、重启丢失、fallback 串 Process |
| S10 | P4 acquisition external_key / human review | partial | 复用和 gate API 存在，幂等 revision 与 lifecycle 状态不成立 |
| S11 | P4-05/VF36 raw/clean artifact identity | partial | closure 已标 under-delivery，实际 bytes/digest/handle 仍错配 |
| S12 | P4-13/VF52 namespace dimension | partial | default namespace 冲突仍阻止维度切换 |
| S13 | VF62 generation reservation / purge contract | partial | supervisor serial 不是 durable reservation，API/runtime/test 合同漂移 |
| S14 | P5-01 trusted proxy / P5-08 body cap | partial | 典型路径测试存在，空 CIDR 和 chunked body 不满足 fail-closed |
| S15 | P6-01/P6-05 falsifiable tests / wheel | partial | ruff 与 migration wheel 成立，真实 Turso smoke、source-grep 清理未完成 |
| S16 | VF86 Turso e2e owner-gated harness | partial | 可以保留 live owner gate，但当前失败不能覆盖其他非 harness correctness findings |
| S17 | VF40.r pending lifecycle、VF85 source-grep | stale | closure/action-plan 的 in-scope 标记与“可关闭”叙述冲突，代码和测试仍能直接观察到问题 |

### 3.1 对齐结论

- **done**: 0
- **partial**: 15
- **missing**: 0
- **stale**: 1
- **out-of-scope-by-design**: 0（真实 GPU/Claude、生产 Turso Cloud 等 live gate 在本节单独核查，不等于代码缺口被豁免）

这更像“第一轮完成了大量局部骨架，但跨边界状态和交付证据仍未收口”，而不是 completed。P1-P6 的某些子项确实 done，但按本轮目标核查的完整合同均至少为 partial。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|---|---|---|---|
| O1 | 真实 GPU、Claude、外部 Turso Cloud、生产 deploy | 遵守 | 本轮没有把缺少 live 凭证误报成已通过，也没有要求伪造 live 证据 |
| O2 | native ANN 生产接线 | 遵守 | 当前代码拒绝未实现的 native_ann，没有把 fallback 宣称为生产 ANN |
| O3 | 多副本 overlap / VF62 的最终高并发 profile | 部分违反 | 可以 deferred 最终并发规模，但当前 generation reservation、serial profile 的可用性和 fence 不能一并 deferred |
| O4 | VF86 owner-gated Turso harness | 部分违反 | owner/live harness 可继续由 owner 提供，但本地 Turso port、默认 ready、测试绕过和独立业务复现不能全部归入 VF86 |
| O5 | VF66.r 目录 CAS SSOT | 部分违反 | 可以 deferred 完整目录治理，但 promote 后 orphan 的可发现性和 GC 安全不能因此消失 |
| O6 | billing、browser/OCR/Vision 等未纳入 NS5 的业务 | 遵守 | 未把这些领域扩展为本轮 blocker |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：changes-requested
- **是否允许关闭本轮 review**：no
- **关闭前必须完成的 blocker**：
  1. 修正 UoW BEGIN cancellation、inference gate lease、heartbeat exception fencing 和 outbox stale-owner CAS；为 cancel/retry/reclaim/crash 建立可重复测试。
  2. 将 external_key、revision、human review、serving revision 统一为 durable idempotent/lifecycle transaction；approve/reject 必须得到可验证的最终 serving 状态。
  3. 修正 Turso 默认 serial profile、禁止 readiness 改全局 journal mode，并建立关键 schema manifest，保证损坏时不假绿。
  4. 为 CAS bytes 与 Turso catalog/reference 建立 delete fence/reconcile；所有 object lookup 过滤 tombstone；raw/clean 使用独立制品。
  5. 完成 namespace identity、generation reservation、purge contract，并明确 VF36/VF52/VF40.r/VF62 的真实交付状态。
  6. 收紧 XFF、streaming body cap、CLI child env/process/output/timeout、public payload 和 signed URL durable-state 边界。
  7. 清除 P6 假绿与 Turso/SQLite 混用；以真实 PersistencePort 完成 clean wheel、默认 Settings、ready、claim、publication、retrieval smoke，并在全量测试结果可解释后重新审查。
  8. 修复唯一 VF ledger canonical path，重新生成 closure；任何 deferred 必须有 owner、验收条件、失败后的系统行为和明确期限。
- **可以后续跟进的 non-blocking follow-up**：
  1. HealthAggregator 的 TTL 语义、sidecar close/backoff/drop receipt、scanner/GC/retirement/outbox metrics。
  2. layered datetime 的完整 schema 校验、team restore 的 deleted_at 清理、retrieval 的状态 TOCTOU、retirement intent 的终止条件及 cancel/delete command idempotency key。
- **建议的二次审查方式**：independent reviewer
- **实现者回应入口**：请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。

本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。
