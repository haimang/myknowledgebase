# Nano-Agent 代码审查模板

> 审查对象: `MKB new-harvest NH1–NH9（intake 4 通道接线 / kind-family dynamic workflows / 竞态幂等 / leaf-worker 上游面）`
> 审查类型: `rereview`
> 审查时间: `2026-08-30`
> 审查人: `Grok`
> 审查范围:
> - `src/`（task admission、kind 图、runtime materialize/outcome、intake pipeline、upload/GC、retrieval）
> - `api/public/routes.py` · `api/internal/routes.py` · `api/app.py` · `src/contracts/api/models.py`
> - `src/persistence/migrations/018..024`
> - `tests/e2e` · `tests/unit` 中与 NH1–NH9 / 第 1 轮修复相关的钉死断言
> - `docs/closure/new-harvest/` 九份 AP + `CROSS-NH-campaign.md`（仅作声称，不以 self-claim 为证）
> 对照真相:
> - `docs/eval/new-harvest/final-execution-plan.md`（`T-O-376..407`）
> - `docs/eval/new-harvest/pre-initial-planning-qna.md`（`T-O-376..389`）
> - `docs/plan/new-harvest/AP-NH1..AP-NH9`
> - `docs/baseline/domain-truth/S01-skill-worker-integration.md` · `S02-task-api.md` · `S15-observability-reliability.md`
> - `docs/code-review/new-harvest/NH1-NH9-review-VF-ledger.md`（**仅**作第 1 轮「声称已修」地图，不采信其 verdict）
> 文档状态: `changes-requested`

---

## 0. 总结结论

> 四通道已经能从 public Task create 进入 kind 图并跑出可检索向量，dynamic workflow 的选图权威也已落到 `source_kind`；但第 1 轮台账里若干「fully-fixed」并未钉死，HTTP 再获取执法盖住了已声明的 clean 边，tombstone 后同 key 再 ingest 会先建 Task 再撞 UNIQUE，leaf-worker 写得进分支却读不出实际绑边。本轮审查不能关闭。

- **整体判断**：实现主体已接通，三大目标均为 `partial`；第 1 轮 24 条「已完全修复」不能按台账收口。
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. 第 1 轮生产路径上的 fail-loud（kind×strategy 422、sealed-once DDL、fail-process `rowcount`、系统键拒绝、reacquire 不再误伤 inline）是真的；但 VF7 观察幂等非原子且无测试、VF12 cancel 仍按「最新一条 hold」释放，属于 **声称 fixed 的 under-delivery**。
  2. HTTP kind 图把「图上存在 `main_text_absent` 守卫」当成每一个 SUCCEEDED hop 的义务，`acquisition_mode=browser` 的空壳页、以及再获取后仍 absent，会在已声明的 clean/print 边之前被 `workflow-reacquire-edge-undeclared` 409 掉。这是对 `T-O-388` 的路由断点，不是诚实 defer。
  3. leaf-worker 上游用三轴（`source_kind` × `acquisition_mode` × `clean_strategy`）可以把 intake 送进正确 kind 图，且不能点名 `workflow_key`；但 public GET 看不到实际绑边，delete 后同 `external_key` 再 ingest 不是 admission 闭集，调试/停止/检索确认面不足以支撑运营闭环。

---

## 1. 审查方法与已核实事实

> 这一节只写事实，不写结论。

本轮是第 2 轮静态审查。组织方式是主审先读冻结真相与第 1 轮修复提交，再按 DAG 并发进攻，最后 **主审对每一条拟收录 finding 重新 Read 代码**，子代理结论只作线索。

**审查 DAG（本轮实际执行）**：

```text
Phase 0  主审：git log / 59772f5 / 34ad2fb / ba099ee
         + VF-ledger §6.2 声称清单（不采信 verdict）
         + T-O-376..407 / S01 / S02 / S15 / 九份 closure
              │
              ▼
Phase 1  三条横切进攻（并行）
         ├─ 端到端：intake → kind 图 → 4 节点 processing → publication
         ├─ leaf-worker 上游：分类 / 列表 / 进分支 / 状态机
         └─ 可观测性：调试 / 重试 / 重启 / 删除 / 停止
              │
              ▼
Phase 2  四业务簇对抗（并行，与 Phase 1 同时发出）
         ├─ 簇 A  四通道实际接线诚实性（10+3）
         ├─ 簇 B  dynamic workflows 选图/选边/CONTROL/reacquire
         ├─ 簇 C  竞态 / CAS / 幂等 / crash 窗
         └─ 簇 D  七意图 / exact-clean / 生命周期
              │
              ▼
Phase 3  主审独立复核 file:line → 归因 → 本文
```

- **对照文档**：
  - `docs/eval/new-harvest/final-execution-plan.md` · `pre-initial-planning-qna.md`
  - `docs/plan/new-harvest/AP-NH1..AP-NH9`
  - `docs/closure/new-harvest/AP-NH1..AP-NH9` · `CROSS-NH-campaign.md`
  - `docs/closure/new-start/deferred-items-ledger.md` 的 `NH1–NH9 第 1 轮审查后` 段
  - `docs/baseline/domain-truth/S01-skill-worker-integration.md` · `S02-task-api.md` · `S15-observability-reliability.md`
- **核查实现**：
  - `src/runtime/task/task_create.py` · `task_commands.py` · `task_views.py` · `task_projection.py` · `task_projections.py`
  - `src/workflows/kind_family.py` · `src/services/workflow_registry.py`
  - `src/runtime/workflow/runtime_materialize.py` · `runtime_outcome.py` · `selected_output.py`
  - `src/runtime/intake/acquisition_ingest.py` · `acceptance_snapshot.py` · `acquisition_intents.py` · `index_rebuild_plan.py`
  - `src/contracts/intake/strategies.py` · `src/contracts/api/models.py`
  - `src/services/object_upload.py` · `object_upload_ttl.py` · `object_gc.py`
  - `src/services/intake_lifecycle/targets.py` · `lifecycle_apply.py` · `src/services/registry.py`
  - `src/services/observability.py` · `api/public/routes.py` · `api/internal/routes.py`
  - `src/persistence/migrations/024_nh_review_invariants.sql` · `001_initial.sql:944-960`
- **执行过的验证**：
  - `git log --oneline`；`git rev-parse HEAD` → `ba099ee`
  - `git show --stat 59772f5`（intake/workflow 不变量）
  - `git show --stat 34ad2fb`（upload/GC/supply）
  - `git show --stat ba099ee`（VF-ledger 与 evidence 刷新）
  - 主审对下列位点的直接 Read（见各 finding 事实依据）
- **复用 / 对照的既有审查**：
  - `NH1-NH9-review-VF-ledger.md` — **仅作声称修法地图**。本轮不采纳其 `fully-fixed` / `independently-verified` 判定；每条须重新坐实。
  - `NH1-NH9-reviewed-by-gemini.md` / `GLM53f` / `luna` / `v4f` — **本轮未作为结论来源**。不引用、不调和、不修改这些文件。
  - 本轮 8 个对抗性子代理（流程 / leaf-worker / 可观测性 / 四通道 / 工作流 / 竞态 / 七意图 / 第 1 轮 VF 复核）的输出 **只作进攻线索**。下文每条 R 均经主审重新读码；子代理过称项在 §4 降级。

### 1.1 已确认的正面事实

- HEAD 为 `ba099ee`。第 1 轮生产修复落在 `59772f5`（intake/workflow 不变量 + `024`）与 `34ad2fb`（upload hold / GC reconcile / supply 边界）。
- 新 `intake.ingest` Task 的选图只认 `source_kind`：`WorkflowRegistryService.resolve_for_source` 在 `src/services/workflow_registry.py:79-103` 把四 kind 映射到三张 single kind 图或 scatter root；非 ingest 意图落到 inline-kind 骨架。仓库无 `action_branch` 选图。
- Public 契约四通道闭集在 `src/contracts/api/models.py:153-244`（`inline_payload` / `local_object` / `http_resource` / `registered_api`）；七意图闭集在 `:344-352`。
- kind×strategy 能力求交在 Task INSERT 之前：`task_create.py:90-96` 调 `assert_clean_strategy_applicable`（`strategies.py:193-208`）。`inline_payload × pdf.ocr` 为 422 零 Task，有 `tests/e2e/test_nh1_nh9_review_fixes.py:55-94`。
- `_fail_process_tx` 在 `rowcount != 1` 时抛 `stale-process-fence`（`runtime_outcome.py:519-523`），不再静默继续 FAILED 路由。
- `024_nh_review_invariants.sql:5-20` 对 `mkb_executions` sealed 列有 `BEFORE UPDATE` abort；facts/history 禁 UPDATE/DELETE（`:22-44`）。
- 系统拥有语义键拒绝在 `targets.py:228-239`（`canonical_content` / `source_representation` / `is_active` 与两 blob）。
- upload 创建路径已按会话 `hold_owner=uuid7()` 分 hold（`object_upload.py:105-120`）。`scan_once` 开头调用 `reconcile_quarantine`（`object_gc.py`）。
- filename NUL/`%00` 在 `api/public/routes.py:100-106` 拒绝。Mapping retrieval 接受 v1|v2（`retrieval_request.py`）。
- inline prefix 声明了 rebuild / metadata / index.rebuild 守卫（`kind_family.py:284-316`），compose 去重（`:253`）。
- 三张 kind 图共享 tail digest 被 `tests/domain/test_nh2_architecture_scan.py` 钉为 `48c39059…`。
- `S01-T003` 不要求 SkillWorkerManifest；`S15-T050` 默认 timeline 只回 `payload_digest`。caller 禁 `workflow_key` 与 `T-O-379` 一致。
- rebuild/metadata 在 inline kind 主路径上有 start-route 旁路；NH8 closure 已把 lifecycle「仍物化 1 个 acquire」写成已知口径，而不是「零进程」的无限扩张。
- CLI stub / 36 字形 OCR / S11 fixture 在 NH7/NH6 closure 中有披露；本轮不把已登记的诚实 stub 重新打成 fake-green。

### 1.2 已确认的负面事实

- `object_upload_ttl.py:73-82` 的 cancel 按 handle 取 **最新一条** `upload_pending`，WHERE 不含创建时写入的 `owner_uuid`。ingest 释放 hold 也不按会话（`acceptance_snapshot.py:330-334`）。
- registered_api 观察查重在 Task INSERT **之外** 的独立事务（`task_create.py:97-98,452-480`）。全仓测试 **零** `INTAKE_OBSERVATION_REPLAY` / `INTAKE_OBSERVATION_CONFLICT` 命中。
- 生产 CONTROL 把 `representation_fact_digest` 赋成 `output_manifest_digest`（`runtime_materialize.py:882-888`）。NH1 `selected_output.selection_digest()` 要求独立 fact 字段（`selected_output.py:108-124`）。
- HTTP kind 图的 reacquire 执法看 `plan.guards` 是否 **存在** `representation_main_text_presence=absent`，而不是当前 hop 是否声明了该边（`runtime_materialize.py:65-94`）。`decode_web_browser` / `decode_web_reacquire` 的后继是 print/llm/web，没有 reacquire 边（`kind_family.py:513-541`）。
- `resolve_rebuild` 不传 `require_active`（`targets.py:37-45`，默认 False）。rebuild callback 才要求 `lifecycle_state == "active"`（`acquisition_intents.py:108-114`）。
- `lifecycle_apply._target_state` 对已 deactivated 的再 deactivate、已 active 的再 reactivate 返回 `None`（`lifecycle_apply.py:231-247`），HTTP 仍 201 建 Task。
- `mkb_intake_items` UNIQUE `(team_uuid, intake_source_uuid, normalized_external_key)` **不是** 部分唯一（`001_initial.sql:960`）。身份查找跳过 `deleted_at` 行（`acquisition_ingest.py:238-244`），acceptance `INSERT OR IGNORE`（`acceptance_snapshot.py:175-190`）。
- GET Task 投影无 `source_kind` / `acquisition_mode` / `actual_clean_strategy`（`task_views.py:61-94`）。operator timeline `_event_view` 只回 `payload_digest`（`observability.py:390-411`），且无 debug 开关。
- Task 状态投影允许 `cancelling → failed` 与 `queued → failed`（`task_projection.py:63-65`）。`S02-T009` 基础边只有 `cancelling → cancelled`，没有这两条。
- `full_task` retry 调用 `_insert_root_execution` 时不传 `payload_extra`（`task_commands.py:293-318`）。admission 把 `metadata_disposition` 写在 Execution extra（`task_create.py:216-222`）。
- `lifecycle_success` 指标分桶不含 `intake.rebuild` / `intake.update_metadata`（`runtime_outcome.py:710-718`）。Task 列只允许写入 `exhausted_zero`（`task_projection.py:51-52`）。
- `024` 的 indexed identity trigger 只在 `publication_state='indexed'` 时拦截 `content_digest` 原地 UPDATE（`024_nh_review_invariants.sql:46-51`）。
- `browser.py:249-251` 对字面量 `["-headless"]` 扫描 `no-sandbox`，该列表无任何外部输入。
- `_live_local_object` 只要求 catalog + **任意** 未释放 reference（`acquisition_ingest.py:703-728`），不要求 `purpose=upload_pending`。
- GET `/items` 用 **child** Execution 推导 outcome；无 child 时恒为 `active`（`task_projections.py:111-122`）。single 路径会写 snapshot membership（`acceptance_snapshot.py:336-347`）但没有 scatter child。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | 每条 R 的关键路径均主审 Read；git 两笔修复提交 stat 已核 |
| 本地命令 / 测试 | `yes` | 只跑 git 历史/stat；**未**复跑 pytest。测试覆盖结论来自测试文件的断言文本，不是本轮 live 绿 |
| schema / contract 反向校验 | `yes` | `TaskCreateRequest` Literal、七意图 payload、`001` UNIQUE、`024` trigger 与 S01/S02/S15 对照 |
| live / deploy / preview 证据 | `n/a` | 本轮纯静态 |
| 与上游 design / QNA 对账 | `yes` | `T-O-376..407`、S01-T003/T009、S02-T009、S15-T050 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | HTTP reacquire 按「整图有守卫」执法，盖住 browser 起点与再获取后的已声明 clean 边 | `high` | `correctness` | `yes` | 按当前 hop 是否声明 reacquire 边执法 |
| R2 | delete 后同 key 再 ingest：lookup 跳过墓碑，UNIQUE 仍占槽，Task 已 201 | `high` | `correctness` | `yes` | admission 对 deleted 同 key 409；或部分唯一 + 显式复活协议 |
| R3 | VF7 观察查重不在 Task UoW，且零测试 | `high` | `correctness` | `yes` | 查重与 snapshot UNIQUE 同 UoW；补 409 e2e |
| R4 | VF12 cancel/ingest 仍不按会话 hold 隔离 | `high` | `correctness` | `yes` | cancel/TTL/ingest 按 `owner_uuid`；加「A cancel 不放 B」断言 |
| R5 | public GET 看不到实际绑边，leaf-worker 无法确认进了哪条分支 | `high` | `delivery-gap` | `yes` | GET Task 投影 bounded：kind / mode / declared+actual strategy / item uuid |
| R6 | 七意图非法格未停在 admission：deactivated×rebuild 先建 Task；同态 lifecycle 201 no-op | `high` | `protocol-drift` | `yes` | rebuild `require_active`；同态 lifecycle 409 零 Task |
| R7 | Task 投影允许 `cancelling→failed` / `queued→failed`，违反 S02-T009 | `high` | `protocol-drift` | `no` | FAILED 仅从 `running`；过期走 cancel 语义 |
| R8 | `full_task` retry 丢掉 `metadata_disposition`，no_change 可被 refresh 边吃掉 | `high` | `correctness` | `no` | retry 复制 Execution `payload_extra` |
| R9 | GET `/items` 对 single 恒 `outcome=active` | `medium` | `protocol-drift` | `no` | 无 child 时用 root/Task 终态 |
| R10 | VF19 用 manifest digest 冒充 representation fact | `medium` | `protocol-drift` | `no` | CONTROL 读 facts 表 digest |
| R11 | VF25 只修了四意图；rebuild/metadata 成功仍计 `indexed_success` | `medium` | `delivery-gap` | `no` | 非 ingest 成功一律 `lifecycle_success` |
| R12 | VF4 indexed `content_digest` trigger 可被改 state 后绕过 | `medium` | `delivery-gap` | `no` | 禁 indexed 行改身份列组合；补负例 |
| R13 | local_object acquire 不要求 public upload hold | `medium` | `delivery-gap` | `no` | acquire 限定 `upload_pending` 或已转换的 snapshot source ref |
| R14 | VF16 session no-sandbox 扫描是对字面量列表的空转 | `low` | `test-gap` | `no` | 扫即将 POST 的可变 args；或删除伪守卫 |
| R15 | index.rebuild 规划期对 stale 目标 `continue`，可 SUCCESS 空转 | `medium` | `correctness` | `no` | 冻结集与实际 rebuild_count 分叉则 409 |
| R16 | admission 能力求交粗于图边：`http_resource × pdf.ocr` 不是 422 | `low` | `protocol-drift` | `no` | 闭集生成自可达边；或接受「运行时 409」并写进契约 |

### R1. HTTP reacquire 按「整图有守卫」执法，盖住 browser 起点与再获取后的已声明 clean 边

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/workflow/runtime_materialize.py:65-94`：当 `media_family=text` 且 `main_text_presence=absent` 时，只要 **整张 plan** 存在 `representation_main_text_presence=absent` 守卫，且 **当前 hop 的候选边** 没有该守卫，即 409 `workflow-reacquire-edge-undeclared`。
  - HTTP 图只在 `decode_web_static → acquire_browser_reacquire` 声明了该边（`kind_family.py:491-496`）。
  - `decode_web_browser` 的后继是 print / web_llm / web（`:513-526`）；`decode_web_reacquire` 同样（`:528-541`）。这些 hop **没有** reacquire 出边。
  - 现测只覆盖「从 HTTP 图删掉 static→reacquire 边仍 409」（`tests/e2e/test_nh3_declared_reacquire.py`）。**没有** browser 起点 / 再获取后仍 absent 的用例。
- **为什么重要**：
  - `T-O-388` 的产品例是「HTML 空壳 → 已声明的正向再获取，然后落到已声明 clean」。再获取是有限次、每 `step_key` 至多一次，不是「HTTP 图任意 hop 在 absent 时必须还能再获取」。
  - 调用方已经用 `acquisition_mode=browser` 选了起点，空壳页应能走 `decode_browser.web`（无守卫默认）或声明的 print/llm，而不是在选边前被 409。
  - 第 1 轮 VF26 把全局 kind 前缀收成「仅当 plan 声明了 reacquire 守卫」。这修好了 inline 误伤，但把执法范围留在 HTTP **整图**。
- **审查判断**：
  - inline 空文本不 409（图上无该谓词）——VF26 的 inline 半句成立。
  - HTTP static→reacquire 的声明边执法成立。
  - **browser 起点与再获取后仍 absent** 是本轮新发现的路由断点，不是 VF26 的诚实剩余切片。
- **建议修法**：
  - 仅当 **当前 hop 的 compiled routes** 里存在 reacquire 候选、但被其它原因拿掉时，才 409 undeclared。
  - `decode_web_browser` / `decode_web_reacquire` 在 absent 时应落到已声明 clean/print，或在 clean 绑定后 `CLEAN_EMPTY`，不要在选边前以「整图有守卫」拦截。
  - 补三条测试：browser 起点 + 空正文；static→reacquire 后仍 absent；inline 空文本不得 409。

### R2. delete 后同 key 再 ingest：lookup 跳过墓碑，UNIQUE 仍占槽，Task 已 201

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - 活 Item 查找带 `deleted_at IS NULL`（`acquisition_ingest.py:238-244`），墓碑被跳过，运行时会准备 **新** `intake_item_uuid`。
  - 表 UNIQUE 是全行 `(team_uuid, intake_source_uuid, normalized_external_key)`（`001_initial.sql:960`），墓碑仍占槽。
  - acceptance `INSERT OR IGNORE`（`acceptance_snapshot.py:175-190`）后按 **新 UUID** UPDATE（`:191-194`）→ 0 行。Task 在 `task_create` 已 201。
  - NH8 delete 测例覆盖 rebuild/再 delete/reactivate/search（`tests/e2e/test_nh8_delete_tombstone.py`），**没有**同 `external_key` 再 ingest。
- **为什么重要**：
  - `T-O-405` 要求非法/冲突格不建 Task。tombstone 后的同键 ingest 要么是显式 409（键占用），要么是受控复活协议。当前是「先 ACK 再在 Process 里失败」。
  - 这是 leaf-worker 生命周期闭环的断点：上游按契约 delete 后再投同一业务键，得到的是失败 Task，不是闭集错误。
- **审查判断**：
  - 二次 **HTTP delete** 对已 deleted Item 是 409 零 Task（`targets.py:167-168`）——这一格成立。
  - 同 key **再 ingest** 未进入 admission 闭集，是 NH8 未测格，不是 closure 已披露的「lifecycle 仍 1 个 acquire」。
- **建议修法**：
  - admission（或 identity resolve）对同 `(team, source_kind, normalized_external_key)` 的 deleted 行返回 typed 409，零新 Task。
  - 若产品要允许复活，必须是显式 intent + 部分唯一索引，禁止 `INSERT OR IGNORE` 吞掉墓碑冲突。

### R3. VF7 观察查重不在 Task UoW，且零测试

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `_assert_registered_api_observation_free` 使用 **独立** `async with self.persistence.transaction()`（`task_create.py:452-471`），在业务 INSERT UoW（`:111`）之前调用（`:97-98`）。
  - scatter 层 INSERT 前再查一次（`scatter_intake.py:180-196`），DDL 有 `UNIQUE(team, source, observation_key)`。
  - 全仓 grep `INTAKE_OBSERVATION_`：测试目录 **零命中**。scatter e2e 用 `collection-{task_uuid}` 规避同 observation。
- **为什么重要**：
  - 顺序二次：已有 snapshot 时 409，代码路径存在。
  - 两个不同 `task_uuid` 并发、都在 snapshot 写入前通过预检 → 双 201。线性化点推迟到 accept。败者可留下失败 Task/Process。这与 VF7 原题「二次 ingest 失败留行」同构。
  - VF-ledger §6.2 将此项标 `fixed` / `self-claimed-only`。无测试的 self-claim 在本轮不能升级为 fully-fixed。
- **审查判断**：
  - 双层查重是真的；「在 Task INSERT 前关闭并发」不成立。
  - 这是目标③（竞态幂等）的 in-scope 缺口，不是 owner-gated 真模型问题。
- **建议修法**：
  - 观察占位与 Task INSERT 同 UoW；UNIQUE 失败映射 409。
  - e2e：同 observation 二次 → 409、零新 snapshot、零新成功 Task；并发双飞至多一个 201。

### R4. VF12 cancel/ingest 仍不按会话 hold 隔离

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - 创建：`hold_owner = uuid7()` 写入 `owner_uuid`（`object_upload.py:105-120`）。并发 pending=2 的测试已对齐。
  - cancel：子查询 `ORDER BY created_at DESC, reference_uuid DESC LIMIT 1`（`object_upload_ttl.py:73-82`），**不**匹配 `owner_uuid`。
  - ingest 成功：`UPDATE ... purpose='upload_pending' ... released_at IS NULL` **全放**（`acceptance_snapshot.py:330-334`）。
  - 无「A cancel 后 B 的 hold 仍在」断言。`pending==2` 只证明能插入两条。
- **为什么重要**：
  - 同字节双飞正是原修复场景。会话 hold 写入了身份，释放路径没用它。
  - A 201 + B 200 后 cancel 一次会放掉 **B 的新 hold**，A 的旧 hold 仍使 `stat=pending`。B 以为自己的会话还在。
- **审查判断**：
  - 「每上传独立 hold」的 **写入** 半句成立。
  - 「cancel 只放一条」被实现成「只放最新一条」，不是「调用者那一条」。VF12 是 under-delivered，不是 fully-fixed。
- **建议修法**：
  - cancel/TTL 按 `reference_uuid` 或 `owner_uuid`；HTTP 若只有 handle，则文档化「cancel 释放该 handle 上调用者可见的 pending」，并避免误伤并发会话——更干净的是把 hold id 纳入 stat/cancel 契约。
  - ingest 只释放 **本 Task/本会话** 的 pending。
  - 测试：pending=2 → A cancel → pending=1 且 B 的 reference 仍 live。

### R5. public GET 看不到实际绑边，leaf-worker 无法确认进了哪条分支

- **严重级别**：`high`
- **类型**：`delivery-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - GET Task 字段闭集：`request_intent` / `status` / counts / `result_disposition` / `error`（`task_views.py:61-94`）。无 `source_kind`、`acquisition_mode`、declared/actual `clean_strategy`、`intake_item_uuid`。
  - 实际绑边写在 `mkb_executions.actual_clean_strategy`（seal 路径 `actual_s05.py`；retry 复制见 `task_commands.py:307-313`），**从未投影到 Contract**。
  - 公开路由无 `GET /workflows` / `GET /kinds` / `GET /strategies` / `GET /intake-items`。发现面是 OpenAPI Literal + `/ready` 的 supply 布尔（不映射到 10 策略）。
  - operator timeline 故意只回 `payload_digest`（`observability.py:406-411` 注释写明「完整 payload 需要另开 debug 面」）。**没有** debug 开关。`process.materialized` / `execution.selection_projected` 的 payload 含 `step_key` / `candidate_port`，HTTP 读不到。
- **为什么重要**：
  - 本轮明确问题是：leaf-worker 设定下，上游能否拿到分类、列表，并把一次 intake 送进具体分支，以及状态流转是否有断点。
  - **写面**：三轴足够选图/选起点/选清洁边，且 `workflow_key` extra=forbid。这与 `T-O-379` / `T-O-387` 一致，**不**要求 GET catalog。
  - **确认面**：晚绑定发生在 decode 之后。调用方省略 `clean_strategy` 时，唯一能回答「到底绑了谁」的字段在 Execution 列上，public 看不到。这不是 S01 禁止的 Execution 写面，而是调用方自己提交过的三轴 + 系统封印结果的只读投影。
  - `S01-T003` 豁免 SkillWorkerManifest，不能用来豁免「Task GET 不告诉你绑了哪条边」。
- **审查判断**：
  - 「缺 GET /workflows」**不是** blocker（by-design）。
  - 「GET Task 无实际分支身份」是 NH 动态工作流对上游的交付缺口，构成本轮 blocker。
- **建议修法**：
  - 在 Get Task（及 result，若已终态）增加 bounded 只读块：`source_kind`、`acquisition_mode`、`declared_clean_strategy`、`actual_clean_strategy`（封印后）、`intake_item_uuid`（若已有）。
  - 可选：`GET /v1/capabilities` 列出四 kind / 十 strategy / 三 acquire / 三 API operation，以及 supply→strategy 映射。仍禁止 `workflow_key`。

### R6. 七意图非法格未停在 admission：deactivated×rebuild 先建 Task；同态 lifecycle 201 no-op

- **严重级别**：`high`
- **类型**：`protocol-drift`
- **是否 blocker**：`yes`
- **事实依据**：
  - `resolve_rebuild` 不传 `require_active`（`targets.py:37-45`）。`_target_tx` 只对 deleted 409；`require_active` 默认 False（`:155-170`）。metadata 才 `require_active=True`（`:47-58,169-170`）。
  - rebuild 真正要求 active 的是 Process callback（`acquisition_intents.py:108-114`）→ 409 `REBUILD_TARGET_STALE`。此时 Task 已 201。
  - registry seed：`("rebuild", "active", ...)`、`("deactivate", "active")`、`("reactivate", "deactivated")`（`registry.py:216-221`）。
  - `_target_state`：deactivated 再 deactivate、active 再 reactivate 返回 `None`（`lifecycle_apply.py:231-247`），`_action_definition_tx` 的 `allowed_from_mask` **不会执行**。HTTP 仍建 Task，Process 跑 1 个 lifecycle acquire，Task `succeeded`。
  - `test_nh8_intent_applicability.py` 有 deactivated 后 `index.rebuild` 的 409；**没有** deactivated×rebuild HTTP 格，也没有同态 deactivate/reactivate 负例。
- **为什么重要**：
  - `T-O-405`：非法格 422/409 **且不建 Task/Process**。禁止用 no-op/skip 顶替。
  - VF9 第 1 轮只把 metadata 收到 `require_active`。7×state 其余格仍是 registry / admission / callback 三套法律。
- **审查判断**：
  - metadata × deactivated 的 admission 409 是真的（代码路径在，HTTP 用例弱）。
  - rebuild × deactivated、同态 lifecycle 是 **未停在 admission** 的真缺口。
  - 二次 HTTP delete → 409 零 Task 成立；服务层 `apply()` 对已 deleted 仍 no-op（`lifecycle_apply.py:244-247`），但是内部入口，降为 follow-up。
- **建议修法**：
  - `resolve_rebuild(..., require_active=True)`。
  - 同态 deactivate/reactivate 在 resolver 返回 409 `intake-lifecycle-transition-invalid`，零 Task。
  - 把 T01 矩阵补全：每格 HTTP 状态码 + Task 行数。

### R7. Task 投影允许 `cancelling→failed` / `queued→failed`，违反 S02-T009

- **严重级别**：`high`
- **类型**：`protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - `S02-T009`：基础边只有 `queued → running/cancelling`、`running → succeeded/failed/cancelling`、`cancelling → cancelled`。
  - `task_projection.py:63-65`：`FAILED` 允许来源 `running | cancelling | queued`。
  - `accept_outcome` 在 execution 已 `cancelling` 时抛 `execution-cancelling`（`runtime_outcome.py:61-62`），能挡住 **该窗** 的 outcome。Task 投影仍允许 cancelling→failed。
- **为什么重要**：
  - 上游 `POST :cancel` 收到 202 `cancelling` 后 poll，可能看到 `failed` 而不是 `cancelled`。停止闭环的终态不稳定。
  - 第 1 轮 VF24 修好了 process fence 静默丢写；**没有**把 Task 六态边收到 S02。
- **审查判断**：
  - 这是状态机契约漂移，影响运营，但不阻断四通道接线。列为 non-blocking，但建议与 R5 同一批修。
- **建议修法**：
  - `FAILED` 仅从 `running`。queued 过期走 cancel 语义。cancelling 只允许 `CANCELLED`。若产品需要「取消过程中发现失败」，须 reopen S02。

### R8. `full_task` retry 丢掉 `metadata_disposition`，no_change 可被 refresh 边吃掉

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - admission 把 disposition 写入 root Execution `payload_extra`（`task_create.py:216-222`）。
  - start-route：`metadata_no_change` priority 2 vs `metadata_refresh` priority 3（`kind_family.py:301-316`）。context 从 Execution extra 读取（`runtime_materialize.py:186-195`）。
  - retry `_insert_root_execution` **不传** `payload_extra`（`task_commands.py:293-318`），形参默认 `None` → `'{}'`（`task_create.py:367,448`）。
  - `replay_frozen_clean` 要求 `clean_text`（`acquisition_intents.py:128-131`）；`metadata_no_change` 路径没有这份正文（`:180-195`）。
- **为什么重要**：
  - `T-O-401` 要求 full_task 复制 exact 绑定。disposition 不是 sealed actual 列，但是 start-route 的选边事实。丢掉后 no_change Task 会走 refresh/replay，并在缺 `clean_text` 时 `PIPELINE_INPUT_INVALID`。
- **审查判断**：
  - 合法 metadata no_change 的 **首次** 路径成立。缺口在 retry。不把本轮三大目标判 missing，但必须修。
- **建议修法**：
  - retry 复制 previous Execution 的 `payload_extra`（至少 `metadata_disposition`）。
  - 测试：no_change Task 失败后 `:retry` 仍走 `metadata_no_change` 步，零 acquire/decode/clean。

### R9. GET `/items` 对 single 恒 `outcome=active`

- **严重级别**：`medium`
- **类型**：`protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - `/items` 用 `parent_execution_uuid=root AND target_uuid=item` 的 **child** 推导 outcome（`task_projections.py:63-122`）。无 child → `else: outcome = "active"`。
  - single acceptance 写入 snapshot membership（`acceptance_snapshot.py:336-347`），不创建 scatter child Execution。
  - 文档字符串自称「scatter projection」（`task_projections.py:29-32`），但 single 调用该路由会得到撒谎的 `active`。
- **为什么重要**：
  - 上游若用 `/items` 列「这次 ingest 的 Item」，会看到已 succeeded 的 Task 下 Item 仍是 `active`。`intake_item_uuid` 仍在，故还能拿 ID。
- **审查判断**：
  - S02 的 TaskItem 本意是 scatter。实现却让 single 也有 membership。这是列表语义裂缝，不是选图失败。
- **建议修法**：
  - 无 child 时用 root Execution / Task 终态映射 outcome；或 single 的 `/items` 明确 404/空页并在 OpenAPI 写清「仅 scatter」。

### R10. VF19 用 manifest digest 冒充 representation fact

- **严重级别**：`medium`
- **类型**：`protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - `runtime_materialize.py:882-888`：`"representation_fact_digest": selected["output_manifest_digest"]`。同 dict 已有 `output_manifest_digest`。
  - NH1 代数 `selection_digest()` 把 fact 当作独立输入（`selected_output.py:108-124`）。生产 `_enter_selected_output_tx` **不调用** `project_selected_output`。
- **为什么重要**：
  - 第 1 轮声称「material 纳入 representation_fact_digest」。字段名在，绑定的是 manifest 副本。fact 变、manifest 不变时 CONTROL 无感。
  - kind 图 XOR 下通常只有一个 candidate，所以 **路由功能** 仍能 exactly-one。这不是选图断裂。
- **审查判断**：
  - VF19 under-delivered。降为 follow-up：CONTROL 权威与 NH1 投影合同分叉。
- **建议修法**：
  - 写入前读 `mkb_representation_facts` 的 fact digest；`selection_digest` 与 `selected_output.py` 同一代数。

### R11. VF25 只修了四意图；rebuild/metadata 成功仍计 `indexed_success`

- **严重级别**：`medium`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `runtime_outcome.py:710-718`：`lifecycle_success` 仅 `deactivate/reactivate/delete/index.rebuild`。
  - Task 列拒绝写入非 `exhausted_zero` 的 disposition（`task_projection.py:51-52`）。上游 GET 看不到 `lifecycle_success`。
- **为什么重要**：
  - 原诉是「非 ingest 成功计入 indexed」。lifecycle 四意图的 **metrics** 已分桶；rebuild / metadata no_change 仍进 `indexed_success`。产品字段仍只有 `exhausted_zero`。
- **审查判断**：
  - 部分修复如声称；口径未闭合。不阻断接线。
- **建议修法**：
  - 七意图里非 ingest 的成功一律 `lifecycle_success`；若要给 caller 看，须放开 Task 列闭集并投影。

### R12. VF4 indexed `content_digest` trigger 可被改 state 后绕过

- **严重级别**：`medium`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `024_nh_review_invariants.sql:46-51`：仅当 `OLD.publication_state='indexed'` 且 UPDATE `content_digest`。
  - 先把 `publication_state` 改成非 indexed，再改 digest，不触发。DELETE+INSERT 不触发。无该 trigger 的负例测试。
- **为什么重要**：
  - 应用层检索仍要求 proof 匹配。这是 DDL 不变量的剩余切片，与已 defer 的「读时重算 set digest」（`NH-VF4.r`）相邻但不是同一句话。
- **审查判断**：
  - 「禁原地改 indexed digest」对 **直接 UPDATE content_digest** 成立。声称 independently-verified 的不可绕过，不成立。
- **建议修法**：
  - 禁止 indexed 行修改身份列（或 state+digest 组合）；补「直接 UPDATE abort」与「先改 state 再改 digest abort」。

### R13. local_object acquire 不要求 public upload hold

- **严重级别**：`medium`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `_live_local_object`：catalog 存在 + **任意** `released_at IS NULL` 的 reference（`acquisition_ingest.py:703-728`）。
  - upload 写入的是 `purpose=upload_pending AND owner_kind=public_upload`（`object_upload.py:107-110`）。
  - 无 catalog → 409 发生在 Process，Task 已 201（仅 integration 覆盖）。
- **为什么重要**：
  - `T-O-385` 的产品法是 upload 造 handle，随后独立 ingest。happy path（`test_nh4_upload_then_ingest.py`）成立。
  - acquire 不强制 pending，意味着 config/generation 的 `process_io` 引用只要 digest 对得上就能当通道成功。这是身份门，不是「没接线」。
- **审查判断**：
  - 四通道 **能** 经 public upload 接通。未强制「只能经 public upload」是围栏缺口。
- **建议修法**：
  - ingest 要求 live `upload_pending` 或已转换的 snapshot source ref；拒绝其它 purpose。补公共 e2e：无 catalog handle → 409，最好停在 admission。

### R14. VF16 session no-sandbox 扫描是对字面量列表的空转

- **严重级别**：`low`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `browser.py:249-251`：`firefox_args = ["-headless"]` 后立刻 `any("no-sandbox" in argument ...)`。该列表不可变、无外部源。
  - geckodriver argv 扫描仍在命令行路径上。
- **为什么重要**：
  - 第 1 轮声称扫 session args。当前实现扫不到任何可注入输入。生产风险取决于「以后会不会把 args 做成可配置」——现在是虚假修复，不是现洞。
- **审查判断**：
  - 不是生产 `--no-sandbox` 泄漏（默认列表确实没有该 token）。
  - 不能算 fully-fixed。
- **建议修法**：
  - 对即将 POST 的可变 `moz:firefoxOptions.args` 扫描，并用可变列表单测；或删除这段恒假的守卫以免误导后续修改者。

### R15. index.rebuild 规划期对 stale 目标 `continue`，可 SUCCESS 空转

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `index_rebuild_plan.py:258-265`：非 active / 无 serving / revision 漂移 → `continue`。
  - 空 plans 时 commit 直接 return（`index_rebuild_commit.py` 对 noop）。T08 把 reactivate 后的 index.rebuild 当作合法空转。
  - commit 期 `INDEX_REBUILD_TARGET_STALE` 只打 **已经进入 plan** 的目标。规划期跳过测不到。
- **为什么重要**：
  - VF9.r 已登记「index.rebuild stale cardinality」。team scope 冻结集与实际 rebuild_count 可静默分叉，Task 仍 SUCCEEDED。
- **审查判断**：
  - item scope + 明确无 serving 的空转，可能是产品法（reactivate 后须先有 serving）。team scope 静默少 rebuild 是真缺口。
- **建议修法**：
  - 冻结 target 在执行前消失 → 409，而不是 SUCCESS。T08 若要保留 A∅ 空转，须在契约写明，且不得用于 team 子集静默跳过。

### R16. admission 能力求交粗于图边：`http_resource × pdf.ocr` 不是 422

- **严重级别**：`low`
- **类型**：`protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - `pdf.ocr` 的 `acquire_capabilities` 含 `http_static`（`strategies.py:99-105`）。admission 求交放行。
  - HTTP static HTML 走 `decode_web_static`，声明 `pdf.ocr` 时由 `workflow-claimed-strategy-unreachable` 在 **已有 Task** 之后 409（`runtime_materialize.py:105-114`）。
  - `acquisition_mode=pdf` 时图上有 `clean_pdf_ocr`（`kind_family.py:542-543`）。无 HTTP OCR 到检索的 L3。
- **为什么重要**：
  - VF1 的「非法组合零 Task」只覆盖能力不相交（inline×pdf.ocr）。可达边闭集与 admission 不一致。运行时仍 fail-loud，不是静默换工人。
- **审查判断**：
  - 不是 VF1 回潮。是闭集粒度问题。运行时 409 可以保留（需要观察），但 GET Task 必须能解释（回 R5）。
- **建议修法**：
  - 用 kind 图可达 `(mode, media, strategy)` 生成 admission 矩阵；或在契约写明「kind×strategy 只保证能力相交，表示不匹配是 409 失败 Task」。

---

## 3. In-Scope 逐项对齐审核

结论统一使用：`done | partial | missing | stale | out-of-scope-by-design`。

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| S1 | 目标①：intake 4 通道实际接线（`T-O-376/381`） | `partial` | 四 kind 均从 public create → kind/scatter 图 → 真实 acquire/decode/clean Process → publication/search。inline 确定性、http static、local 文本、API map 为 live adapter。LLM/通用 OCR/Vision 为诚实 stub/闭集/fixture（`NH-VF14.r`）。local_object 身份门未强制 upload（R13）。 |
| S2 | 目标②：dynamic workflows 落地并接管路由（`T-O-379/384/387/388/391`） | `partial` | 选图只认 `source_kind`；三图共享 tail；CONTROL exactly-one；选边后 actual seal；旧 pin 共存、upgrade=0。未闭合：HTTP reacquire 过宽（R1）；CONTROL 未消费 representation fact（R10）；kind revision 仍钉在 1（`NH-VF21` defer）。unguarded 默认边是登记边，不单独打成 missing。 |
| S3 | 目标③：接线过程竞态 / 错误 / 幂等（`T-O-383/400/404`） | `partial` | Task 指纹 201/200、seal CAS、catalog+pending 同 UoW、fail-process fence、024 sealed-once 为生产路径 done。observation 非原子（R3）、upload cancel 无会话（R4）、九窗仍是 hook（`NH-VF27.r`）、`retry_wait` 非 no-op（`NH-VF10`）未闭合。 |
| S4 | leaf-worker：分类 / 列表 / 指定进分支 | `partial` | 写面三轴齐全且禁 `workflow_key`。分类靠 OpenAPI，符合 S01-T003。列表无 kind/strategy 过滤。确认面缺失（R5）。 |
| S5 | leaf-worker：状态流转（六态 + 七意图 + retry/cancel/restart/delete/stop） | `partial` | 七意图 HTTP 入口唯一；rebuild/metadata 旁路在主路径成立。非法格未全部停在 admission（R6）。cancel 终态可能 failed（R7）。delete 后再 ingest 断（R2）。retry 丢 disposition（R8）。 |
| S6 | 可观测性：调试选边 / acquire 路径 / actual digest | `partial` | 内部表（history / actual S05 / selected_output）足够让读库的人解释。HTTP（含 internal timeline）按 S15-T050 默认不回 payload，且 **无 debug 门控**；public 也无 bounded 决策投影（R5）。 |
| S7 | 第 1 轮 VF 声称 fully-fixed（24 条） | `partial` | 坐实 fully-fixed：VF1 准入、VF2 executions trigger、VF8、VF11 对账入口、VF15、VF18、VF22/23 证据刷新、VF24、VF26 的 inline 半句、VF30、VF31。under-delivered：VF7、VF12、VF19、VF16、VF25、VF4 可绕过。其余 self-claimed 项代码方向对、测试弱。 |
| S8 | NH7 10+3 live-to-retrieval | `partial` | Process 图与 namespaced search 接通；embed 在 NH7 测试为 hash；LLM/OCR/VL 非生产模型。closure 已披露，本轮不改写成 fake-green，也不改写成 done。 |
| S9 | NH8 exact-clean / T08-B=0 | `done` | inline kind start-route 旁路；forbidden process 可到 0。lifecycle 1 个 acquire 是已披露口径，不是 T-O-407 对 rebuild/metadata 的字面失败。 |
| S10 | NH4 upload 身份与 GC | `partial` | catalog+pending 同 UoW、pending=2、quarantine reconcile 成立。cancel/ingest 隔离（R4）与 pre-catalog orphan（`NH-VF13`）未闭合。 |
| S11 | NH3 actual S05 sealed-once + 同 UoW | `done` | 应用 CAS + 024 trigger 双保险；reseal 409。崩溃窗仍是 hook，归 S3/VF27。 |
| S12 | NH2 kind-only + 共享 tail + CONTROL | `done` | 选图/tail/exactly-one 成立。R1 是 HTTP 图内选边，不否定选图权威。 |
| S13 | CROSS-NH「九 AP 已 closed」 | `stale` | 文档状态 `closed` 描述的是战役 DoD（unique 62 + 四元组）。本轮审查的是三大目标在代码上的闭合，不以 CROSS 自我关闭为证。 |

### 3.1 对齐结论

- **done**: `3`（S9、S11、S12）
- **partial**: `9`（S1–S8、S10、S13 不计）
- **missing**: `0`
- **stale**: `1`（S13 CROSS 自我关闭相对本轮目标）
- **out-of-scope-by-design**: 见 §4

> 这更像「四通道与 kind 图已经接管新 Task 的主路径，但第 1 轮收口有 under-delivery、HTTP 再获取与生命周期 admission 仍有断点、leaf-worker 读面不足以运营」，而不是 completed，也不是「图还没落地」。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | 真模型 / S16 签收 / PromptRef complete_bound / 封闭字形扩成通用 OCR（`NH-VF14.r` / `T-O-378` 诚实 stub） | `遵守` | 本轮不把 stub 当 fake-green，也不要求本阶段接 vLLM。过称「live-to-retrieval」是文档语气，已在 NH7 closure gap 披露。 |
| O2 | 进程级 kill + `recover_expired_leases` 新进程证明（`NH-VF27.r`） | `遵守` | supervisor tick **会**调 `recover_expired_leases`。九窗测试是 hook/事后 SQL。本轮不把「未做 kill」升级为新的 true-bug。 |
| O3 | kind 图 `revision_number=1` 原位演进（`NH-VF21`） | `遵守` | registry 对 digest mismatch 503，是故意不热切。运维地雷，但是登记 defer。 |
| O4 | stage envelope 去正文（`NH-VF3.r`） | `遵守` | acquire/decode/clean 仍复制 `raw_text`。本轮不要求 CAS-first 重写。R5 的读面缺口是另一件事。 |
| O5 | `retry_wait` 同 digest no-op（`NH-VF10`） | `遵守` | 再投是 `process-not-running` / fence，不是双计 retry。保持 defer。 |
| O6 | pre-catalog CAS orphan / staging（`NH-VF13`） | `遵守` | promote 在 TX 外是设计。本轮不把 S13 大改拉进 blocker。 |
| O7 | caller `workflow_key` / `action_branch` / 第五 kind / raw GET / experiment 进 DoD | `遵守` | 未发现回流。 |
| O8 | 建设 UI / SkillWorkerManifest / webhook | `遵守` | OD-01 / S01-T003/T005。本轮「前端」= HTTP 上游。R5 要求的是 Contract 只读投影，不是 UI。 |
| O9 | timeline 默认不回完整 payload（S15-T050） | `遵守` | 子代理有把「timeline 无 payload」写成缺陷。规范明文默认 digest-only。缺口是 **没有 debug 门控 + public 无 bounded 决策字段**（收入 R5），不是违反 T050。 |
| O10 | 把 `derive_selected_clean_strategy` + 无守卫默认边当成「表外策略包、campaign blocker」 | `误报风险` | 该函数把 decode 观察写成 `selected_clean_strategy` 事实，供 **已登记** `registered_clean_strategy` 守卫消费；无声明时 HTML 落到图上已画出的 priority=10 边。这是晚绑定观察器，不是 handler 暗改 `process_key`。本轮不收录为 blocker。 |
| O11 | scatter child 失败不回滚 sibling 向量 | `误报风险` | 代码注释写明 forward-stop。`T-O-387` 允许 child 独立 construct。失败 child 自身通常未 publish。列为产品张力，本轮不升 blocker。 |
| O12 | 缺 GET `/workflows` 即动态工作流未落地 | `误报风险` | 与 `T-O-379` 冲突。选图权威在 `source_kind`。 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`changes-requested`。四通道与 kind-family 主路径已接通，第 1 轮多数 fail-loud 修复属实；但 VF7/VF12/VF19 等声称 fixed 未钉死，HTTP reacquire 与 tombstone 后再 ingest 是真实正确性断点，leaf-worker 读面不能确认分支。三大目标均为 `partial`。
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. **R1**：HTTP reacquire 改为按当前 hop 的声明边执法；补 browser 起点 / 再获取后 absent / inline 空文本三条测试。
  2. **R2**：deleted 同 key 再 ingest 必须在 admission fail-loud（409 零 Task）或显式复活协议；禁止 201 后撞 UNIQUE。
  3. **R3 + R4**：观察查重与 Task INSERT 同 UoW 并补测试；cancel/ingest 按会话 hold 释放并补「不误伤」断言。
  4. **R5**：GET Task（终态至少）投影 `source_kind` / `acquisition_mode` / declared+actual `clean_strategy` / `intake_item_uuid`。
  5. **R6**：rebuild 要求 active；同态 deactivate/reactivate 409 零 Task；补 7×state HTTP 矩阵。
- **可以后续跟进的 non-blocking follow-up**：
  1. R7 六态边收到 S02-T009；R8 retry 复制 `metadata_disposition`。
  2. R9 `/items` single 语义；R10 CONTROL 读 fact digest；R11/R12 指标与 DDL 剩余切片。
  3. R13 local_object 限定 upload hold；R15 index.rebuild cardinality；R14 删除空转守卫。
  4. 为 timeline 增加 S15-T050 允许的 debug 门控（仍脱敏）；capabilities 只读面。
  5. 保持 `NH-VF14.r` / `NH-VF27.r` / `NH-VF21` / `NH-VF3.r` / `NH-VF10` / `NH-VF13` 在 deferred ledger，不在本轮假装完成。
- **建议的二次审查方式**：`same reviewer rereview`
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> 本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。

---

## 附录 A. 第 1 轮 VF 声称-fixed 主审复核摘要

> 详细攻击见审查 DAG Phase 0/2。此处只保留主审独立判定，便于实现者对照台账 §6.2。

| VF | 台账声称 | 主审判定 | 进入本轮 |
|----|----------|----------|----------|
| VF1 | admission 422 + runtime 409 | 准入 `fully-fixed`；runtime 409 无测试；求交粗于图边 | R16 |
| VF2 | 024 sealed-once | executions trigger `fully-fixed`；facts/history 无测 | — |
| VF4 | 禁 indexed digest 改写 | `under-delivered` | R12 |
| VF7 | observation 409 零新行 | `under-delivered` | R3 |
| VF8 | 系统键拒绝 | `fully-fixed`（覆盖只打了 canonical_content） | — |
| VF9 | metadata 仅 active | `partial-as-claimed` | R6 |
| VF11 | quarantine reconcile | 入口 `fully-fixed` | — |
| VF12 | 会话 hold + cancel 一条 | `under-delivered` | R4 |
| VF15 | readiness 不强制未启用 multimodal | `fully-fixed` | — |
| VF16 | session no-sandbox | `under-delivered`（空转） | R14 |
| VF18 | prefix 守卫 | `fully-fixed` | — |
| VF19 | material 纳入 fact digest | `under-delivered` | R10 |
| VF24 | fail_process rowcount | 代码 `fully-fixed`；无该函数专测 | — |
| VF25 | lifecycle_success | `under-delivered` | R11 |
| VF26 | reacquire 仅声明图 | inline 半句成立；HTTP 过宽是新洞 | R1 |
| VF30 | filename NUL | `fully-fixed` | — |
| VF31 | Mapping v2 | `fully-fixed`（规范化，非检索） | — |
| VF3/14/27/41 | partial-as-claimed | 与 defer ledger 一致 | O1–O4 |

---

## 附录 B. 四通道接线诚实矩阵（主审裁剪）

判定只用于目标①，不把测试绿写成 live 模型。

| 通道 | acquire | decode | clean | tail |
|------|---------|--------|-------|------|
| `inline_payload` | live（admission promote） | live `text_json_html` | live `doc.deterministic` | 图 live；LLM 步 default-root stub |
| `local_object` | live 读 CAS；身份门不强制 upload | text/pdf live；image 空 decode | 图边 live 或供给缺失 503；OCR 36 字形 | 同上 |
| `http_resource` | static live；browser/print 真 Firefox 或 503 | text/pdf live 或 503 | 确定性 live；llm_rewrite stub；print clean 常 S11 fixture | 同上 |
| `registered_api` | live（冻结 records，合同内无 fetch） | 有意无 decode 节点 | live `clean.map.*` | child 图独立 construct；LLM 仍 stub |

**无 L3 fetcher/LLM 赋值冒充成功**（NH7 有扫描）。假绿主战场不在 monkeypatch，而在把诚实 stub 写成 T-O-376 完成态——closure 已披露，本轮不新开 fake-green blocker。

---

## 附录 C. leaf-worker 操作闭环（调试 / 重试 / 重启 / 删除 / 停止）

| 操作 | 接口 | 判定 | 缺口 |
|------|------|------|------|
| 指定进分支 | POST `/tasks` 三轴 | 写面足够 | 确认面见 R5 |
| 分类 | OpenAPI Literal | 部分 | 无运行时 catalog；`/ready` 不映射策略 |
| 列表 | GET `/tasks?request_intent=` | 部分 | 不能按 kind/strategy/lifecycle 滤 |
| 调试选边 | — | 缺失 | R5；timeline 无 debug 门控 |
| 重试 | POST `:retry` + `expected_revision` | 部分 | 202 无 replay 标志；R8；caller 不知是否徒劳（仍绑同一 actual） |
| 重启 | `:retry` vs 新 Task `intake.rebuild` | 部分 | 身份可区分；S05 法律差（copy vs 不写新 actual）HTTP 不解释 |
| 删除知识 | 新 Task `intake.delete` | 部分 | R2；无 GET item；检索空须另 search |
| 停止 | POST `:cancel` | 部分 | R7 终态可能 failed |
| 对象 cancel | `objects:cancel` | 部分 | R4；无 revision fence |
