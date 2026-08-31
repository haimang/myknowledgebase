# MKB new-harvest NH1–NH9 第 2 轮代码审查（v4f · 独立静态审查）

> 审查对象: `MKB new-harvest NH1–NH9（intake 4 通道接线 / dynamic workflows 落地 / 竞态错误幂等）+ 第 1 轮修复质量核验（HEAD @ ba099ee）`
> 审查类型: `rereview | mixed（fix-verification + 全流程 + leaf-worker 接口 + 可观测性）`
> 审查时间: `2026-08-31`
> 审查人: `v4f（独立，不使用任何其他 reviewer 结论）`
> 审查范围:
> - `src/`（contracts / runtime / services / workflows / storage / persistence / migrations 018..024）
> - `intake/`、`api/`（public + internal）、`tests/`
> - `docs/closure/new-harvest/`（九份 AP + CROSS-NH）
> - `docs/plan/new-harvest/todo-list.md`、`docs/eval/new-harvest/final-execution-plan.md`、`pre-charter-qna.md`
> - git 提交 `59772f5` / `34ad2fb` / `ba099ee`（第 1 轮修复三连）与其前的 `a608ea8`
> 对照真相:
> - `docs/closure/new-harvest/CROSS-NH-campaign.md`（campaign 收口声明）
> - `docs/code-review/new-harvest/NH1-NH9-review-VF-ledger.md`（第 1 轮 42 条 VF 台账 — **作为被审查对象，非结论来源**）
> - 上游契约：`src/contracts/`、`api/models.py`、`persistence/migrations/`
> 文档状态: `changes-requested`（第 2 轮不收口）

---

## 0. 总结结论

> **一句话 verdict**：第 1 轮的核心正确性修复（strategies 闭集 / sealed-once DDL / GC 对账 / per-upload hold / fail-loud fence）**大部分真实落地并可通过代码证实**，但存在 2 条「名义修复」（VF16 恒假守卫、VF19 值域错配）、1 条修复未闭环（VF1 的 registered_api 侧），且第 2 轮在四通道接线、leaf-worker 接口、可观测性三个目标面上发现了 **不可忽视的静默正确性缺口与接口/埋点空白** — 主体骨架成立，但「closed-with-explicit-deferrals」中多项 deferred 实际以静默形式出现在生产路径上，本轮 review **不关闭**。

- **整体判断**：`第 1 轮修复大部分到位，但存在静默损坏路径（单通道重摄入悬挂引用、latest_revision LWW、deactivated 再 ingest 假账）与 3 条验收级名义修复；leaf-worker 接口与前端可观测性两面交付缺失。`
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. 单通道（inline/local/http）**内容变更重摄入**会产生静默悬挂 change_set + 丢失 accept_revision fact + 陈旧 fingerprint（`acceptance_snapshot.py:139-171/397-453`），与 registered_api 的严格 409 语义不对称 — **静默损坏路径仍在**。
  2. 第 1 轮台账存在「假性关闭」：VF19 的 `representation_fact_digest = output_manifest_digest`（`runtime_materialize.py:884`）值域错配且与 `selected_output.py` 投影代数双公式漂移；VF16 的 no-sandbox 扫描对本地常量自检恒假（`browser.py:249-251`）；VF1 修复后 `registered_api` 能力闭集无任何 consumer，且 `registered_api.map` 伪策略泄漏并被 scatter child 继承（`actual_s05.py:26`）。
  3. leaf-worker/前端视角：**没有分类/列表/能力目录接口**、**没有 stage/process 级别读取面**、事件 payload 被 timeline 主动剥离、admission 拒绝零记录、outbox 死信不可重投 —「可获取分类、列表、指定 intake 进入分支」「调试、重试、重启、删除、停止」的承诺与现状存在系统性落差。

---

## 1. 审查方法与已核实事实

- **对照文档**：
  - `docs/closure/new-harvest/CROSS-NH-campaign.md` + `AP-NH1..NH9` 九份 closure（campaign 承诺面）
  - `docs/plan/new-harvest/todo-list.md`、`docs/eval/new-harvest/final-execution-plan.md`
  - `docs/code-review/new-harvest/NH1-NH9-review-VF-ledger.md`（仅作修复台账被核验）
- **核查实现**：
  - 修复三连：`git show 59772f5`（intake/workflow 不变量）、`34ad2fb`（upload/GC/supply 边界）、`ba099ee`（docs/evidence 刷新）
  - 全流程源码：`src/runtime/intake/*`、`src/runtime/workflow/*`、`src/runtime/task/*`、`src/services/*`（intake_lifecycle / object_* / retrieval / scatter / observability）、`src/workflows/*`、`src/contracts/intake/strategies.py`、`api/public/routes.py`、`api/internal/routes.py`、`src/persistence/migrations/001/018..024`
- **执行过的验证**：
  - `git log --oneline --stat a608ea8..ba099ee`（第 1 轮修复影响面核对）
  - 关键代码位点逐行 Read：`acceptance_snapshot.py:130-459`、`runtime_materialize.py:795-924`、`representation_history.py:33-165`、`object_upload_ttl.py`、`object_gc.py:166-317`、`browser.py:240-260/355-390`、`strategies.py:46-208`、`actual_s05.py:26-34`、`lifecycle_apply.py:130-246`、`observability.py:298-412`、`task_create.py:86-115/449-480`
  - 三类 grep 反向校验：策略闭集 consumers、`payload_extra` 写入点、metrics 写入点、`released_at` 全部写入点
- **发起子代理（DAG 执行计划）**：
  - 本第 2 轮按「修复质量核验 → 全流程 → 接口面 → 可观测面」四簇 DAG（前一簇结论为后一簇线索，但各簇均以代码为唯一证据）：
    - `G0` 修复质量核验（本审查人自验，git diff + 台账逐条对照）→ 产出 R1-R3
    - `G1` 全流程簇（sub-agent A：intake→dynamic workflow→processing 4 nodes）→ 产出 R4-R10/部分 R17-R20
    - `G2` leaf-worker 接口簇（sub-agent B：分类/列表/分支/状态流转）→ 产出 R11-R16
    - `G3` 可观测簇（sub-agent C：埋点/可解释/前端调试运维）→ 产出 R21-R32
  - **复用 / 对照的既有审查**：`none`（本审查人与三个子代理均未采纳 `NH1-NH9-reviewed-by-*.md` 与 VF-ledger 的任何结论；VF 台账仅作为「修复声明」被逐条对代码核实。所有 file:line 证据均为本轮亲自 Read/Grep 复核）

### 1.1 已确认的正面事实

- `assert_clean_strategy_applicable` 的闭集检查真实生效：`inline_payload + pdf.ocr` 在 Task 插入前 422（`task_create.py:90-96` + `strategies.py:193-208`），有 e2e 钉死（`test_nh1_nh9_review_fixes.py:55-94`）。
- sealed-once / append-only / indexed-identity 三触发器中 `024_nh_review_invariants.sql` 已落库且位点正确（`OLD/NEW` 条件精细到列级）。
- VF24 fail-loud 真实：`_fail_process_tx` rowcount≠1 → `stale-process-fence` 409（`runtime_outcome.py:516-526`），不再静默。
- VF26 执法范围收窄真实：reacquire 仅当 plan 声明 guard 时 enforce（`runtime_materialize.py:69-100`），http 图去边 409、inline 空文本不 409。
- VF12 per-upload hold 闭环：每次上传独立 `hold_owner`（`object_upload.py:105-123`）；cancel/TTL 各释放一条且带 owner 语义（`object_upload_ttl.py:53-82`）；已核验取消不再误伤并发对端。
- VF7 双层观察查重：admission（`task_create.py:452-480`）与 scatter INSERT 前（`scatter_intake.py:180-196`）指纹算法一致（`canonical_json` + `stable_digest` 同源）。
- GC TX1/TX2 之间的 quarantine 对账（`reconcile_quarantine` + `restore_quarantined`）对「目录行仍 live」的字节可恢复；`_same_catalogue_row` + blocker 二次复检封闭了乒乓（子代理 A 已证伪 TOCTOU 主项）。
- `source_kind` 是唯一 public graph selector：`workflow_registry.py:79-103` 无密钥注入面（`config_snapshots.py:72` 禁 workflow_key 覆盖）。
- scatter 收敛分母以 ChangeSet+Membership 为权威（`runtime_scatter.py:134-196/277-485`），短子列表不静默丢失；`exhausted_zero` 独立路径成立。
- 单通道同内容重放（fingerprint 相同）走 `replay_frozen` 收敛，幂等成立；registered_api 409/`INTAKE_OBSERVATION_REPLAY` 类型化成立。

### 1.2 已确认的负面事实

- 单通道**内容变更**重摄入：`mkb_intake_change_sets` 唯一约束 `(team, snapshot)`（`001_initial.sql:1178`）导致 `INSERT OR IGNORE` 静默吞写 → 悬空 `change_set_uuid` 写入 `mkb_tasks`（`acceptance_snapshot.py:397-453` 已读证）。
- `mkb_intake_items.latest_revision_uuid` 无 CAS 条件更新（`acceptance_snapshot.py:191-195`）→ 并发双内容 LWW。
- `representation_fact_digest` 被赋值为 `output_manifest_digest`（`runtime_materialize.py:884`），字段名与值域不一致；与 `selected_output.py:88-124` 的 5 键投影公式不是同一公式。
- `SOURCE_KIND_ACQUIRE_CAPABILITIES["registered_api"]`（`strategies.py:182`）在 10 个 `CleanStrategyDefinition` 中无任何 consumer。
- `actual_s05.py:26` 将 `clean.map.registered_api` 映射到闭集外伪策略 `"registered_api.map"`，经 sealed actual 逐字继承进 scatter child。
- `lifecycle_apply.py:138-141` 的 delete 释放条件只按 `owner_uuid=intake_item_uuid` → 对所有以 snapshot/revision/source-object 为 owner 的引用是 no-op；`intake_artifact`/`derived_generation` cleanup substrate 无执行者。
- `browser.py:249-251` no-sandbox 扫描对象是本地常量 `["-headless"]`，恒 False；`_driver_command`（`browser.py:363-387`）同样自检自拼命令。
- timeline 事件读取面（`observability.py:304-306, 390-412`）不选 `status_before/status_after`、不返回 payload（只有 `payload_digest`）。
- `DiagnosticSink.write` 生产代码仅 1 处调用（retention，`observability.py:580`）；metrics 目录 ≥10 个系列无任何写入点（`mkb_lease_recover_total`、`mkb_gc_*`、`mkb_worker_queue_lag_seconds`、`mkb_alert_raised_total` 等）。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | 全部 finding 均给出当前 HEAD 的 file:line，且经本审查人逐行复读 |
| 本地命令 / 测试 | `partial` | 未运行 pytest（静态审查）；以 `.experiment` 不存在 与 closure 的 62 passed 为背景信息，不以测试断言为结论依据 |
| schema / contract 反向校验 | `yes` | `001_initial.sql` 唯一约束、`019/020/024` 迁移触发器、`api/models.py` 描述符字段集反向核对 |
| live / deploy / preview 证据 | `no` | 本环境无 live 部署 |
| 与上游 design / QNA 对账 | `yes` | 对照 `final-execution-plan.md` / `pre-charter-qna.md` 的 T-O-376..407 承诺面逐项 |
| 子代理证据 | `yes | 已复核` | A/B/C 三子代理 findings 中关键证据（A1/A2/A3/B4/C3/C7 等）由本审查人二次验证后才采纳；标注 [未验证] 的不采信为结论 |

---

## 2. 审查发现

> 编号 R1..R32；按业务簇分组；严重级别为多方复核后的最终值。

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | 单通道内容变更重摄入：悬挂 change_set + fact 丢失 + 陈旧 fingerprint | `critical` | `correctness` | `yes` | 快照级 fingerprint CAS + 独立 change-set |
| R2 | `latest_revision_uuid` 无 CAS 的 last-writer-wins | `high` | `race` | `yes` | UPDATE 加 revision 条件，失败 409 |
| R3 | VF19 名义修复：`representation_fact_digest` 值域错配 + CONTROL 双公式 | `high` | `correctness` | `yes` | 接真实 fact digest，收敛单公式 |
| R4 | VF1 未闭环：registered_api 能力闭集无 consumer + `registered_api.map` 泄漏 | `high` | `protocol-drift` | `yes` | 闭集登记或显式剔除 |
| R5 | local_object 源引用 / delete artifact 字节永不释放 | `high` | `delivery-gap` | `no` | 补 substrate 执行者与 owner 释放 |
| R6 | deactivated 项同 key 再 ingest：全流程白跑 + 假账 active→active | `high` | `correctness` | `yes` | admission 分支或真实过渡账 |
| R7 | 策略可达性全部晚期检查（201 后 409）+ registered_api 无法声明策略 | `high` | `delivery-gap` | `no` | admission 前置静态可达性 |
| R8 | 无分类/目录接口：kind 图、策略闭集、能力清单不可枚举 | `critical` | `interface-gap` | `yes` | 只读目录端点 + digest 版本化 |
| R9 | 列表维残缺：无 intake-items/lifecycle/process/namespace 列表 | `high` | `interface-gap` | `no` | 补列表端点与过滤维度 |
| R10 | timeline 剥离 payload，无 per-process 事件查询 | `high` | `explainability-gap` | `yes` | v2 debug 面 + status_before/after |
| R11 | DiagnosticSink 死代码（生产仅 1 处调用） | `high` | `observability-gap` | `no` | 故障点补写 + 读取端点 |
| R12 | metrics 目录死系列（≥10 个从未写入；repair 无正向计量） | `high` | `observability-gap` | `no` | 补打点或删除目录项 |
| R13 | admission 422/409 零记录 | `medium` | `observability-gap` | `no` | 审计/事件落拒绝档 |
| R14 | 无 stage/process 级读取面（卡在 decode 不可答） | `high` | `interface-gap` | `no` | per-item 最新 process 聚合 |
| R15 | 无 team 级 intake 总览 / observation_key 查询 / delete 结果不暴露 | `high` | `interface-gap` | `no` | `/intake-items` + applied 回显 |
| R16 | outbox 死信不可重投、repair 不可手动、无 kill/restart | `high` | `delivery-gap` | `no` | internal 运维端点 |
| R17 | observation 查重 TOCTOU：双并发 201，accept 期裸约束错误 | `medium` | `race` | `no` | 原子 ON CONFLICT + 类型化 |
| R18 | GC tombstone 后 destroy 前崩溃：quarantine 字节永久滞留 | `medium` | `storage` | `no` | reconcile 对 tombstoned 条目收尾 |
| R19 | pending TTL 与排队 Task 竞态（409 OBJECT_REFERENCE_REQUIRED） | `low` | `race` | `no` | 响应带 TTL 期限 / 文档 |
| R20 | admission 大 records 哈希 + 请求体上限缺失 [未验证] | `low` | `security` | `no` | 请求体上限核查 |
| R21 | 无 stage_report 读取接口（仅 timeline 附带） | `medium` | `interface-gap` | `no` | 按 process 查 stage |
| R22 | stale-process-fence 抛异常回滚失败事件，失败瞬态无痕 | `medium` | `observability-gap` | `no` | 独立 commit 诊断 |
| R23 | retry/cancel/delete 幂等对前端不可区分（无 replay 标志） | `medium` | `ui-gap` | `no` | 统一 `outcome` 字段 |
| R24 | payload_extra 全线 '{}' 空置 | `low` | `observability-gap` | `no` | 收敛列或真实填值 |
| R25 | path digest 公式变更（+main_text_presence）与离线冻结物漂移风险 | `medium` | `docs-gap` | `no` | 证据重算双签名或声明 v1 公式 |
| R26 | rebuild 对 inactive 项 admission 姿态不一致（延迟失败） | `medium` | `delivery-gap` | `no` | 与 metadata 对齐 require_active |
| R27 | supply 缺件默认全开门 + 无能力查询接口 | `medium` | `delivery-gap` | `no` | `/capabilities` + create 期预检 |
| R28 | 「leaf-worker 模式」不存在（无角色裁剪/能力宣告） | `medium` | `design-gap` | `no` | worker-only 模式与文档化 |
| R29 | reacquire 死路回旋（3 轮 lease、错误码 recovery-exhausted 失真） | `low` | `observability-gap` | `no` | 首次决策即 integrity 失败 |
| R30 | 二次 delete 静默 no-op 与 deactivate/reactivate 409 不对称 | `low` | `correctness` | `no` | 显式幂等回显 |
| R31 | index.rebuild noop / exhausted_zero 状态对前端不可见 | `low` | `ui-gap` | `no` | 投影 operation_mode |
| R32 | TTL/cancel 全程静默；outbox.enqueued 事件无调用方 | `low` | `observability-gap` | `no` | 计数 metric + 布尔回显 |

---

### 簇 A · 第 1 轮修复质量核验（fix-verification，本审查人自验）

### R1. 单通道内容变更重摄入：悬挂 change_set + 丢失 accept_revision fact + 陈旧 fingerprint

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/intake/acceptance_snapshot.py:139-145`：`existing_snap` 命中即复用旧 `intake_snapshot_uuid`，**不比对 `observation_fingerprint`**（registered_api 侧同位置是严格 409，`scatter_intake.py:180-196`）。
  - `001_initial.sql:1178`：`mkb_intake_change_sets` 唯一约束 `UNIQUE (team_uuid, intake_snapshot_uuid)`。
  - `acceptance_snapshot.py:397-415`：第二次接受（内容不同 → 新 digest）时 `INSERT OR IGNORE` 被唯一约束吞掉；`stored_change_set` 回查拿不到 → `change_set_uuid` 保持**从未落库的新 uuid**。
  - `acceptance_snapshot.py:416-439`：`inserted_change_set.rowcount == 1` 才写 `mkb_intake_change_set_facts` → 第二次观察的 accept_revision fact **丢失**。
  - `acceptance_snapshot.py:440-453`：`mkb_tasks.change_set_uuid` 被写成该悬空 uuid（无 FK，静默挂起）；快照 `observation_fingerprint` 停留在第一次内容的 digest。
- **为什么重要**：同内容重放恰是「幂等收敛」（走 `replay_frozen` 分支），容易被误判为安全；**内容变更的重摄入**却是静默断链审计 + 丢失证明记录 + 指纹陈旧，且与 registered_api 语义不对称。这是全链路唯一「成功返回但账目为假」的路径。
- **审查判断**：成立（逐行证实）。可归因第 1 轮修复只覆盖了 registered_api 引爆的 VF7/VF6，未对单通道做同构加固；单通道「静默聚合」是 pre-NH 遗留设计与新策略并存的产物。
- **建议修法**：`_accept_snapshot` 内对 `existing_snap.observation_fingerprint != state["raw_digest"]` 时写新 snapshot（唯一键改为 `(source, observation_fingerprint)` 或移除以允许多快照），并将 change-set 唯一键从 `(team, snapshot)` 放开为每次接受独立 change-set；对变更观察写 `INTAKE_OBSERVATION_CHANGED` 类型化事件。

### R2. `latest_revision_uuid` 无 CAS 的 last-writer-wins

- **严重级别**：`high`
- **类型**：`race`
- **是否 blocker**：`yes`
- **事实依据**：`acceptance_snapshot.py:191-195`：`UPDATE mkb_intake_items SET latest_revision_uuid=?, row_revision=row_revision+1 ... WHERE team_uuid=? AND intake_item_uuid=?` — 无 `AND latest_revision_uuid=?` / `AND row_revision=?` 条件。
- **为什么重要**：同 source 两个并发 Task（不同内容）都过 admission（单通道无观察查重，`task_create.py:97-98` 只拦 registered_api），先后提交，最终 serving/latest 指针取决于提交顺序，两个 Task 都 201+成功 — 用户无法确定「谁是当前版本」，与 registered_api 双保险（admission + acceptance 线性化）不对称。
- **审查判断**：成立。metadata 路径已用 CAS（`acceptance_lifecycle.py:303-316`），单通道接受路径未对齐。
- **建议修法**：UPDATE 加 `AND latest_revision_uuid=?` 条件（读到的旧值），rowcount≠1 → `INTAKE_REVISION_FENCE` 409。

### R3. VF19 名义修复：`representation_fact_digest` 值域错配 + CONTROL 双公式漂移

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`（对「CONTROL 绑定表示事实」的收口声明）
- **事实依据**：
  - `runtime_materialize.py:884`：`"representation_fact_digest": selected["output_manifest_digest"]` — 字段名承诺表示事实摘要，值却是 clean 进程输出 envelope digest（与同 dict 的 `output_manifest_digest` 重复）。
  - 生产公式（`runtime_materialize.py:875-888`，11 键含 execution_uuid/control_step_key/accepted_outcome_digest/route_decision_digest/fallback_used）与注册投影代数 `selected_output.py:88-96/108-124`（5 键，`representation_fact_digest` 语义为真实事实摘要）**不是同一个公式**；`project_selected_output()` 若用于验证生产行必然 `WORKFLOW_SELECTION_PROOF_INVALID`（目前仅测试自证 = oracle 与实现脱钩）。
  - `018_nh2_selected_output_control.sql` 持久化行无 `representation_fact_digest` 列 → 该参与 digest 的值不落库，重放依赖从同一过程行重算；对既有 durable selection 若重放时公式不一致会误报 `workflow-selected-output-conflict`（`runtime_materialize.py:911-923`）。
- **为什么重要**：第 1 轮台账将 VF19 标为 `fixed`（自证），但实际 CONTROL **未绑定任何表示事实**；注册代数与生产公式不互相承认 — 属于「名义修复」，离线/二次校验方必踩证据不匹配。
- **审查判断**：成立（字段错配）+ 成立（双公式漂移）。值域错配被 `_is_digest` 检查掩盖，能安然通过所有现有测试。
- **建议修法**：从 `mkb_representation_facts` 取该 execution 末位 fact digest 填 `representation_fact_digest`；以 `selected_output.py` 为规范收敛为单一公式实现，并补「生产行 ↔ 投影代数」一致性测试。

### R4. VF1 未闭环：registered_api 能力闭集无 consumer + `registered_api.map` 泄漏

- **严重级别**：`high`
- **类型**：`protocol-drift`
- **是否 blocker**：`yes`
- **事实依据**：
  - `strategies.py:178-183`：`SOURCE_KIND_ACQUIRE_CAPABILITIES["registered_api"]={"intake.acquire.registered_api"}`；但全仓 grep 十个 `CleanStrategyDefinition`（`strategies.py:46-147`）**无一声明该 capability** → `assert_clean_strategy_applicable` 对 registered_api 恒判 422（`strategies.py:199-208`），该分支是死码（admission 层过滤掉的组合根本到不了）。
  - 公开契约 `RegisteredApiSourceDescriptor`（`api/models.py:178-238`）**没有 `clean_strategy` 字段**且 `extra="forbid"` → 客户端无法表达该组合 — 所以「误伤合法成员」已证伪，但**契约与闭集双出、各自独立成立**，构成隐性协议漂移。
  - `actual_s05.py:26`：`"clean.map.registered_api": "registered_api.map"` — 该策略键不在 `CLEAN_STRATEGY_DEFINITIONS` 闭集中，`resolve_clean_strategy("registered_api.map")` 直接 `CLEAN_STRATEGY_UNSUPPORTED`（`actual_s05.py:34`）；该值被 sealed 进 root execution（`runtime_outcome.py:450-469`）并**逐字继承到每个 scatter child**（`scatter_intake.py:651-657`）— 任何未来严格按「actual_clean_strategy ∈ 注册表」的读取方必炸。
- **为什么重要**：NH9 的「closed-set assurance」承诺闭集无泄漏，但内部 `registered_api.map` 是闭集外的真值；策略层与契约层互相矛盾的「广告」会在运行时以 409 形式迟到爆发。
- **审查判断**：成立。第 1 轮 VF1 的修复只覆盖了 kind×strategy 的静态闭集，未做「闭集 ↔ 实际使用的策略键 ↔ 公开契约」三面对账。
- **建议修法**：在闭集登记 `registered_api.map`（channel 加 `api`），或删除 closed-set 外的映射并在 `strategies.py` 顶部声明 registered_api capability 是「采集侧非 clean 侧」；增加一条「sealed actual_clean_strategy ⊆ 闭集」的 DB/测试不变量。

---

### 簇 B · intake 4 通道接线 / 全流程（sub-agent A 产出 + 复核）

### R5. local_object 源对象引用 / delete artifact 字节永不释放

- **严重级别**：`high`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `acceptance_snapshot.py:318-329` 为 local_object 创建 `owner_kind='intake_snapshot_source_object'` 引用；全仓 `released_at` 写入点仅有：accept 释放 upload_pending（`:330-335`）、TTL/cancel 释放 pending（`object_upload_ttl.py:48-82`）、lifecycle delete 按 `owner_uuid=item` 释放（`lifecycle_apply.py:137-141`）— **没有任何代码释放 snapshot/revision/source-object 属主引用**。
  - `lifecycle_apply.py:138-141` 释放条件 `owner_uuid=intake_item_uuid` 对 snapshot/revision/gate/execution/hold 属主是 no-op。
  - `lifecycle_apply.py:289` delete 建立 cleanup intent，substrate 声明 `("derived_generation","intake_artifact","vector_projection")`；全仓唯一 cleanup 执行者是 `index_retirement.py`（仅 `vector_projection`）→ `intake_artifact`/`derived_generation` **无执行者**，intent 永远 open，artifact 与源对象字节不可回收（GC 因未释放引用阻塞）。
- **为什么重要**：每个 local_object 摄入的源字节 + 每次 delete 的 artifact 字节**永久留存**；「删除」是伪合约；`_ensure_delete_cleanup_tx` 承诺的清理永远不完成。
- **审查判断**：成立。属第 1 轮台账 VF11/VF13 的「defer-with-rationale」切片在真实数据面上的显形：GC 对账做了，但 `intake_artifact` substrate 从未接线。
- **建议修法**：实现 intake_artifact/derived_generation substrate 执行器（释放 revision/snapshot 属主引用并置 intent 完成）；delete 释放条件扩展 `owner_kind IN ('intake_revision','intake_snapshot','intake_snapshot_source_object')`。

### R6. deactivated 项同 key 再 ingest：全流程白跑 + 假账 active→active

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - identity 解析只排 deleted：`acquisition_ingest.py:235-246` `i.deleted_at IS NULL`，**不排 `lifecycle_state='deactivated'`** → deactivated 项被复用。
  - accept 无 lifecycle 条件：`INSERT OR IGNORE INTO mkb_intake_items` + 无条件 `UPDATE latest_revision_uuid`（`acceptance_snapshot.py:172-195`）。
  - 过渡账写死：`('accept_revision','v1','active','active')`（`acceptance_snapshot.py:492`）— 真值 deactivated 却记录 active→active。
  - publication 拒绝：`lifecycle_publish.py:75-76` 要求 `lifecycle_state='active'` 否则 `PUBLICATION_SERVING_FENCE` 409 → Task 在向量化之后失败（白跑整条清理/向量化/生成链路）。
- **为什么重要**：客户端直觉「deactivated 后重 upload 上线」被系统收下烧掉整条管线，最后一步 409；transition ledger 还撒谎 — 运维无法从账目发现真相，正确动作（reactivate→ingest）只能靠失败反推。
- **审查判断**：成立。属状态流转矩阵盲点，第 1 轮 VF9「完整 7×state 矩阵」defer 切片的直接后果。
- **建议修法**：identity 解析或 accept callback 增加 lifecycle 分支 — deactivated 项再 ingest 要么 admission 409（「请先 reactivate」），要么定义为隐式 reactivation 并写真实过渡（deactivated→active）。

### R7. 策略可达性全部晚期检查：201 后 `workflow-claimed-strategy-unreachable` 409

- **严重级别**：`high`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - admission 只做集合级检查（`task_create.py:90-96` + `strategies.py:193-208`），不查媒体事实与分支可达性。
  - 反例（已手证）：`http_resource` + 声明 `pdf.ocr` → admission 通过（`http_static` 交集存在）；实际 HTML → 路由 `clean_web_static`（bound=`web.deterministic`）→ `_route_decision` 交差（`runtime_materialize.py:105-114`）`workflow-claimed-strategy-unreachable` 409 — Task 已 201、流程白跑。
  - registered_api 无法声明策略：描述符无 `clean_strategy` 字段 + `extra="forbid"`（`api/models.py:178-193`）→ 声明即 422；scatter child 无策略声明直走 tail（`builtin_scatter.py:395-458`）不做 clean 分支。
- **为什么重要**：leaf-worker 在提交前无法判断「该声明是否可达」（且无 R8 的矩阵接口），只能 201→failed 试错 — 分支选择语义（声明 vs 媒体嗅探 derive，`strategies.py:229-253`）在 409 处对撞。
- **审查判断**：成立。
- **建议修法**：admission 或 materialize 前置做「声明策略 ×（声明的 media_type / 代表事实）可达性」静态检查，把该 409 提前为 422；公布策略×媒体分支适用矩阵。

---

### 簇 C · leaf-worker 接口 / dynamic workflow 完备性（sub-agent B 产出 + 复核）

### R8. 无分类/目录接口：kind 图、策略闭集、能力清单全部不可枚举

- **严重级别**：`critical`
- **类型**：`interface-gap`
- **是否 blocker**：`yes`（对「可获取分类」的目标面）
- **事实依据**：
  - 公开端点全量清单（`api/public/routes.py`）无任何 `/workflows`、`/strategies`、`/source-kinds`、`/capabilities`、`/namespaces`；internal 面（`api/internal/routes.py:17-161`）同样无 kind 图。
  - 运行时唯一选择器 `resolve_for_source`（`workflow_registry.py:79-103`）**丢弃 source_profile**（`del source_profile`，line 92）：realm/type/channel 完全不参与 workflow 身份选择；注册行 `read_exposure='internal'`（line 244）。
  - 闭集 `SOURCE_KIND_WORKFLOW_KEYS`（`kind_family.py:30-34`）、`CLEAN_STRATEGY_DEFINITIONS`（`strategies.py:46-147`）为纯代码常量；`frontend/` 目录为空壳。
- **为什么重要**：leaf-worker 回答「这个 intake 该走哪个分支」唯一能依赖的就是这份闭集；闭集不可枚举、无版本化、随代码演进 — 客户端只能用试错法。
- **审查判断**：成立。
- **建议修法**：只读目录端点（workflow 列表含 guard/route/branch；strategy×source_kind×media 适用矩阵；节点能力清单）或至少把闭集作为 OpenAPI 静态清单发布并做 digest 版本化。

### R9. 列表维残缺：无 intake-items / lifecycle / process / namespace 列表，task 列表过滤不足

- **严重级别**：`high`
- **类型**：`interface-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `tasks.list`（`task_commands.py:33-135`）过滤仅 status/request_intent/priority/时间窗/include_deleted；无 source_kind / realm / type / channel / external_key / intake_item_uuid 维度。
  - `/items` 投影（`task_projections.py:124-137`）无 lifecycle_state；无任何 process/execution 列表端点。
  - 检索强制 namespace（`api/models.py:608-613` 无即 422），而 namespace 是发布端自动生成（`vector_publish_commit.py:266-290`），**没有列举 namespace 的接口**。
- **为什么重要**：leaf-worker 无法回答「我有哪些 intake、哪些生命周期状态、哪些 namespace 可搜」，也无法按语义维度筛选任务 — 多 intake 集群运维必须回 DB。
- **审查判断**：成立。
- **建议修法**：补 `/intake-items`（含 lifecycle_state 过滤）与 `/namespaces` 只读端点；task 列表放开 external_key/source_kind 过滤。

### R10. timeline 剥离事件 payload，无 per-process 事件查询 — 可解释性断链

- **严重级别**：`high`（子代理判 critical，复核后按「失败即失败，但为运营面」定 high-高）
- **类型**：`explainability-gap`
- **是否 blocker**：`yes`（对「客观测性、可解释性」目标面）
- **事实依据**：
  - `observability.py:304-306` timeline SELECT **不选 `status_before/status_after`**；`_event_view`（`observability.py:390-412`）明确只返回 `payload_digest`（注释：完整 payload 需单独治理的 debug 面，不属于 v1 读口）。
  - guard 评估结果 `guard_results` 已持久化（`runtime_materialize.py:96-124` 写入 `decision["payload"]`，`_apply_routes_tx:328-334` 写进 status_changed 事件）— **数据在库里，但读不出来**。
  - internal 只有按 trace/task 的 timeline（`api/internal/routes.py:93-130`），无按 execution/process 查询、无 event_type/severity/时间过滤。
- **为什么重要**：前端无法回答「为什么 clean 路由选了 deterministic 而不是 LLM」「为什么走了 rebuild 分支」——排查必须直接查库。
- **审查判断**：成立。
- **建议修法**：v2 受控 debug 端点（`/internal/.../processes/{p}/events` 或 `include_payload=true` + redaction 策略），并把 `status_before/status_after` 加入 SELECT。

### R11. DiagnosticSink 死代码：全系统故障只有一处写诊断日志

- **严重级别**：`high`
- **类型**：`observability-gap`
- **是否 blocker**：`no`
- **事实依据**：`observability.py:97-173` 定义 `DiagnosticSink.write`；全仓生产唯一调用点为 `observability.py:580`（retention 失败）。`api/app.py:466` 组装了 sink 但未注入调用方。worker ConflictError（`worker.py:104-108`）、supervisor `last_error`（`workflow_supervisor.py:51-61`）、outbox 交付异常、repair 失败 — **全部无持久记录**。
- **为什么重要**：进程重启后故障现场即消失；「为什么这条任务失败了」在没有事件外的第二现场可查。
- **审查判断**：成立。
- **建议修法**：outbox 投递异常、supervisor 连续失败、accept_outcome ConflictError 三类补 DiagnosticSink 调用 + internal 诊断读取端点。

### R12. metrics 目录死系列：≥10 个系列从未写入，repair 无正向计量

- **严重级别**：`high`
- **类型**：`observability-gap`
- **是否 blocker**：`no`
- **事实依据**：`metrics.py:82-229` 目录声明 `mkb_lease_recover_total`(224)、`mkb_gc_orphans_deleted_total`(227)、`mkb_gc_fail_total`(228)、`mkb_worker_queue_lag_seconds`(138)、`mkb_alert_raised_total`(203)、`mkb_backup_*`(201-202)、`mkb_prompt_hash_mismatch_total`(145)、`mkb_registry_resolve_total`(142) 等；全仓实际写入点仅 11 处，以上系列**从未被写入**。`mkb_repair_applied_total` 只允许 ok/noop/fail（`metrics.py:97-102`），唯一写入是 bootstrap `outcome="fail"`（`app.py:596,601`）— repair 成功路径不计量。
- **为什么重要**：lease 恢复、GC、worker 队列延迟、告警在 Prometheus 侧完全盲；「目录存在但没数据」制造假安全感。
- **审查判断**：成立。
- **建议修法**：`recover_expired_leases` 按 outcome 打点、GC `scan_once` 后打点；或在发布说明中删除未落地系列。

### R13. admission 422/409 零记录

- **严重级别**：`medium`
- **类型**：`observability-gap`
- **是否 blocker**：`no`
- **事实依据**：`task_create.py` 全部拒绝路径（team-not-found/identity-conflict/SCATTER_EXHAUSTION_PROOF_REQUIRED/INTAKE_OBSERVATION_REPLAY 等，`task_create.py:76-109/473-479`）在写任何持久行前 raise；`SecurityAuditWriter` 只处理 auth/rate-limit/config-override（`dependencies.py:83`、`config_snapshots.py:884`）；`events.py:16-61` 无 admission-denied 类型。
- **为什么重要**：上游重放/冲突/重复观测全无残迹，做「为什么上周 200 次 intake 被拒」的复盘不可能。
- **审查判断**：成立。
- **建议修法**：`write_denied(action="task.admission_denied", denial_code=...)` 或任务域事件。

### R14. 无 stage/process 级读取面：「谁卡在 decode」不可答

- **严重级别**：`high`
- **类型**：`interface-gap`
- **是否 blocker**：`no`
- **事实依据**：public 任务子资源只有 result/items/generations/gates/restarts/lineage（`api/public/routes.py`）；`items` 最细到 child_status + `child_error_code`（`task_projections.py:20-148`），无 stage/step 概念；`mkb_acquire_decode_history` / `mkb_representation_facts`（019，append-only）无任何 API 读面；`mkb_generation_stage_reports` 只能作为 timeline 附带物出现（`observability.py:326-332/335-387`）。
- **为什么重要**：前端看到 task=running、item=active，无法区分在 acquire/decode/clean/等 gate/等 backoff — 整条摄入管线可定位性为零。
- **审查判断**：成立。
- **建议修法**：internal 或 public 提供 per-item「最新 process 状态 + stage + error_code + waiting_reason」聚合端点（join mkb_executions/mkb_processes）。

### R15. 无 team 级 intake 总览 / observation_key 查询 / delete 结果不暴露

- **严重级别**：`high`
- **类型**：`interface-gap`
- **是否 blocker**：`no`
- **事实依据**：public 无「列出某 team 全部 intake items / 按 lifecycle_state / 按 observation_key」端点；`intake_lifecycle`（deactivate/reactivate/delete）无独立 API 路由，只能借道 intent Task 创建（`task_create.py:45`），而 `LifecycleTransitionResult.applied`（`lifecycle_apply.py:353-373`）不暴露给前端 —「这 item 到底删没删成功」要等 task 终态。
- **为什么重要**：前端无法执行/确认删除、无法按 key 定位 intake — 属「删除、停止」目标面缺口。
- **审查判断**：成立。
- **建议修法**：`GET /teams/{t}/intake-items`（lifecycle_state / observation_key / updated 过滤 + 分页）；lifecycle Task 视图带 `applied` 汇总。

### R16. outbox 死信不可重投、repair 不可手动触发、无 kill/restart

- **严重级别**：`high`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：`_release_outbox`（`runtime_outbox.py:411-428`）attempts≥8 → dead；`dead_outbox` 只读端点（`internal/routes.py:133`）无 redeliver/reset；没有任何代码把 dead 拉回 pending。`repair_once` 幂等扫描（`runtime_repair.py:25-124`，覆盖 gate_decision 重投/ready wake/无 process wake）**不暴露 operator 端点**，也无法覆盖 `vectorize_construct` 类死信。进程级 kill/restart 不存在 — crash 恢复唯一路径是 lease 扫描（lease 30s + 扫描周期），期间前端看「running」假象。
- **为什么重要**：审查目标「调试、重试、重启、删除、停止」中 restart/stop 两个动词在系统里无实体动作可绑定。
- **审查判断**：成立（对运维面是 5.4 台账 deferred 的显形：VF27.r 进程级 kill、VF42 checker 均在承接登记中，但本审查确认它们不是「手术刀缺失」而是「无任何替代通道」）。
- **建议修法**：internal `POST /internal/repair:run`（幂等限量）与 `POST /internal/outbox/{id}:redeliver`（重置 attempts，白名单 kind）。

---

### 簇 D · 竞态 / 幂等（混合产出 + 复核）

### R17. registered_api observation 查重 TOCTOU：双并发 201，accept 期裸约束错误

- **严重级别**：`medium`
- **类型**：`race`
- **是否 blocker**：`no`
- **事实依据**：`task_create.py:452-480` 预查在独立事务做（并发双创建都见空、都通过）；唯一约束在 `mkb_intake_snapshots`（`001_initial.sql:934`）只在 accept 期生效；accept 路径 `SELECT` 后裸 `INSERT`（`acceptance_snapshot.py:139-171`）**无 IntegrityError 映射** → 败者以 stage-handler-exception/500 族收场（`worker.py:93-99`），不是 `INTAKE_OBSERVATION_REPLAY`。
- **为什么重要**：观察去重是 admit 语义的一部分（期望 200 replay 或 409 REPLAY），并发爆量时出现「两个都 201、一个默默 500」的不可解释结果。
- **审查判断**：边界成立（代码上无原子化保障）。
- **建议修法**：`INSERT ... ON CONFLICT DO NOTHING` + 回读，或在 accept 捕获 IntegrityError 映射为类型化 Conflict。

### R18. GC tombstone 后 destroy 前崩溃：quarantine 字节永久滞留

- **严重级别**：`medium`
- **类型**：`storage`
- **是否 blocker**：`no`
- **事实依据**：`object_gc.py:280-317`：TX2 提交 proof+tombstone 后调 `_destroy_candidate`；进程在两者间崩溃 → `list_quarantined` 仍报该条目，但 `reconcile_quarantine`（`object_gc.py:169-189`）只恢复「目录行仍 live」的条目，tombstoned 条目被跳过且**无任何 destroy 收尾**。
- **为什么重要**：第 1 轮 VF11 修复覆盖了「TX1→TX2 前」窗口，**未覆盖「TX2 提交后→destroy 前」窗口**；字节漏回收。
- **审查判断**：成立（窄窗口）。TX1/TX2 之间窗口的 TOCTOU 已由 `_same_catalogue_row` 封闭（正向量已核）。
- **建议修法**：reconcile 对「目录行 tombstoned + quarantine 存在字节」条目调用 `destroy_quarantined` 收尾。

### R19. pending TTL 与排队 Task 竞态（409 OBJECT_REFERENCE_REQUIRED）

- **严重级别**：`low`
- **类型**：`race`
- **是否 blocker**：`no`
- **事实依据**：`object_upload_ttl.py:40-60` 无条件释放超 TTL 的 upload_pending；`acquisition_ingest.py:718-728` 的 `_live_local_object` 要求存在未释放引用。Task 排队 > pending_ttl → 采集首步 409（fail-loud 但用户需重传重试）。
- **审查判断**：边界成立，属刻意取舍（stat 有 expired disposition 可观测），但文档未提示 TTL 语义。
- **建议修法**：upload 响应带 TTL 期限信息。

### R20. admission 大 records 哈希与请求体上限[未验证]

- **严重级别**：`low`
- **类型**：`security`
- **是否 blocker**：`no`
- **事实依据**：`api/models.py:186` records 上限 10_000 条、单条大小无约束；admission 对全量 records 做 `canonical_json + sha256`（`task_create.py:457-458`），audit 原样落库（`task_create.py:172-177`）— API 请求体大小上限是否存在 [未验证]，若无则大包可放大 CPU/存储。
- **审查判断**：未验证项，仅登记为防御性 follow-up，不升级为结论。

---

### 簇 E · 可观测性 / 前端调试（sub-agent C 产出 + 复核）— 其余项

### R21. 无 stage_report 读取接口

- **严重级别**：`medium`
- **类型**：`interface-gap`
- **是否 blocker**：`no`
- **事实依据**：`mkb_generation_stage_reports` 仅经 timeline 附带物读取（`observability.py:326-332/335-387`）且需「该页恰有带 process_uuid 的事件」；无按 process 查询端点。
- **建议修法**：`/internal/processes/{p}/stage-reports`。

### R22. stale-process-fence 抛异常回滚失败事件 —「失败但无记录」瞬态

- **严重级别**：`medium`
- **类型**：`observability-gap`
- **是否 blocker**：`no`
- **事实依据**：`_fail_process_tx`（`runtime_outcome.py:487-541`）在 UoW 内 UPDATE 后写事件；`rowcount != 1`（519-523）抛异常 → **整个事务回滚**（失败事件 530-541 随之消失）；worker 捕获 ConflictError 后 `_discard_pending; raise`（`worker.py:104-108`），supervisor 只写内存 `last_error`。最终 `recover_expired_leases` 会收敛（`runtime_outcome.py:287-393`），但窗口期内 DB 无「这次失败」的任何记录。
- **审查判断**：成立。与 R3 的 fail-loud 修复是同一机制的两面：正确性上 fail-loud 对，观测上失败瞬态无痕。
- **建议修法**：raise 前以独立 commit 写一条 `ops`/`process` 诊断；或 worker ConflictError 分支补 DiagnosticSink。

### R23. retry/cancel/delete 幂等对前端不可区分

- **严重级别**：`medium`
- **类型**：`ui-gap`
- **是否 blocker**：`no`
- **事实依据**：`retry` 同指纹重放直接返回视图（`task_commands.py:247-254`）无 replayed 字段；`cancel` 对终态返回 200（190-191）；`soft_delete` 对已删返回视图（382-383）；只有 create 的 200/201 可区分。
- **建议修法**：三端点统一响应 `outcome ∈ {applied, replay, noop}`。

### R24. payload_extra 全线 '{}' 空置

- **严重级别**：`low`
- **类型**：`observability-gap`
- **是否 blocker**：`no`
- **事实依据**：domain events（`events.py:95`）、security audit（166）、outbox 入队（`runtime_core.py:875-876`）、diagnostics（`observability.py:167`）、intake transitions（`lifecycle_apply.py:154`）全部硬编码 `'{}'` — 解释性槽位存在但无填值方。
- **建议修法**：删除列或真实填值（outbox delivery_count、超时 fence 上下文）。

### R25. representation path digest 公式变更与离线冻结物漂移风险

- **严重级别**：`medium`
- **类型**：`docs-gap`
- **是否 blocker**：`no`
- **事实依据**：`representation_history.py:42-57` 现把 `main_text_presence`（acquire 阶段恒 "unknown"，`acquisition_ingest.py:154/414`）纳入 path digest；history 查询改 INNER JOIN facts（`:78-85`）。join 丢行已证伪（`019` 迁移同建两表 + `representation_fact_uuid NOT NULL` FK）。
- **为什么重要**：任何 NH2/NH3 冻结期按旧公式生成的离线证据（tail digest / representation-path.json）与现公式无法对账 — 离线冻结物是否存在 [未验证]，但公式变更本身应显式声明版本。
- **审查判断**：边界成立。
- **建议修法**：声明 `representation_path_digest` 公式 v1 含 main_text_presence；若存在离线证据则重算双签名。

### R26. rebuild 对 inactive 项 admission 姿态不一致（延迟失败）

- **严重级别**：`medium`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：`resolve_rebuild`（`targets.py:37-45`）`require_active=False` → deactivated 项可 201，执行期才 `REBUILD_TARGET_STALE` 409（`acquisition_intents.py:103-114`）；而 metadata（`targets.py:169-170` `METADATA_TARGET_STALE`）与 index.rebuild（`targets.py:120-124`）都在创建期拒绝。
- **建议修法**：`resolve_rebuild` 打开 `require_active=True` 与 metadata 对齐。

### R27. supply 缺件默认全开门 + 无能力查询接口

- **严重级别**：`medium`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：`runtime_supply_readiness_required=False` 默认（`config.py:63`），`_health_required`（`app.py:265-271`）因此只要求 BASE → 缺 pdf 解析器的节点 `/ready=200`、Task 201，进程运行到 decode 才 `PDF_PARSE_CAPABILITY_UNAVAILABLE` 503（`acquisition_ingest.py:808-816`）；能力清单只存在于 `SUPPLY_IDENTITIES`（`identities.py:42-125`）代码常量，无接口。
- **审查判断**：成立。第 1 轮 VF15 修复了「multimodal 强制」方向，但整体「默认全开门」是设计取舍 — 对 leaf-worker 是盲区。
- **建议修法**：暴露只读 `/capabilities`；对声明 llm_required/browser_required 的策略在 create 期预检。

### R28. 「leaf-worker 模式」在系统内无实体

- **严重级别**：`medium`
- **类型**：`design-gap`
- **是否 blocker**：`no`
- **事实依据**：`app = FastAPI(title="MKB leaf worker")`（`app.py:657`）仅是标题；同进程总启动 supervisor+GC+upload lifecycle+retention（`app.py:604-625`）无可配置角色裁剪；lease owner 硬编码 `"mkb-leaf-worker"`（`workflow_supervisor.py:23`）；无发现/注册/能力宣告机制 — 若运维把各节点 data_dir 分开即得静默永久 queued 集群，且无指标暴露。
- **审查判断**：成立（对审查场景是设计性缺口；对单机部署无碍）。
- **建议修法**：worker-only 模式配置 + 共享 outbox 的文档化 + `/ready` 暴露 claim 状态。

### R29. reacquire 死路「回旋」：错误码失真

- **严重级别**：`low`
- **类型**：`observability-gap`
- **是否 blocker**：`no`
- **事实依据**：`runtime_materialize.py:66-94` 对 text+absent+声明 reacquire guard 而无匹配边时抛 `workflow-reacquire-edge-undeclared`，该异常在 outcome 事务末尾抛出 → 整体回滚 → worker discard+raise（`worker.py:104-108`）→ lease 后安全重放 decode（`runtime_outcome.py:334-393`）直到 max_recoveries 耗尽，前台最终看到 `recovery-exhausted` 而非真实原因（每 30s 一轮回旋）。
- **建议修法**：第一次路由决策时用 `_fail_execution_integrity_tx` 直接终态失败并写明真实错误码。

### R30. 二次 delete 静默 no-op 与 deactivate/reactivate 409 不对称

- **严重级别**：`low`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：`lifecycle_apply.py:231-246` `_target_state`：delete 对已删 item 返回 `None` → `applied=False`（93-104）；deactivate/reactivate 对 deleted 抛 `intake-item-deleted` 409。
- **建议修法**：统一为显式幂等并在响应带 `applied` 字段。

### R31. index.rebuild noop / exhausted_zero 状态对前端不可见

- **严重级别**：`low`
- **类型**：`ui-gap`
- **是否 blocker**：`no`
- **事实依据**：`index_rebuild_plan.py:47-48` noop 模式写 `operation_mode: index_rebuild_noop`；`task_views.py:61-94` 不输出 operation_mode；disposition `exhausted_zero` 无解释字段投影。
- **建议修法**：把 `operation_mode` 投影进 task/restart 视图。

### R32. TTL/cancel 静默；outbox.enqueued 事件无调用方；retention 删除无归档

- **严重级别**：`low`
- **类型**：`observability-gap`
- **是否 blocker**：`no`
- **事实依据**：`object_upload_ttl.py:40-82` scan/cancel 无事件/metrics；`objects:cancel` 返回 stat 视图无 cancelled 布尔；`events.py:59` 注册的 `outbox.enqueued` 全仓无调用方；`RetentionPolicy`（`observability.py:523-535`）domain 90 天/诊断 14 天直接 DELETE（594-605）无导出。
- **建议修法**：TTL 释放计数进 metric；cancel 返回 `cancelled: bool`；retention 删除前导出或批时间过滤。

---

## 3. In-Scope 逐项对齐审核

> 对齐面 = 本轮审查目标（四通道接线 / dynamic workflow 落地 / 竞态幂等）+ leaf-worker 接口面 + 可观测面。

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| S1 | intake 4 通道实际接线（inline/local/http/registered_api 全链到达 processing） | `partial` | 四通道 happy path 与 publish 均接通（A14 正向核验）；但单通道内容变更重摄入悬挂 change-set 且丢失 fact（R1）、latest_revision LWW（R2）、local_object 源引用永不释放（R5）、deactivated 再 ingest 白跑（R6）|
| S2 | dynamic workflows 实际落地（kind family + 共享 tail + guard 分支） | `partial` | 图解析/单一 tail/无注入面均为真（正向核验）；但 CONTROL 未绑定真实表示事实且双公式漂移（R3）、`registered_api.map` 泄漏闭集外（R4）、策略可达性全部晚期失败（R7）|
| S3 | 接线竞态 / 错误幂等机制完善 | `partial` | registered_api 双层查重为真（正向）；但 TOCTOU 窗口（R17）、GC 收尾窗口（R18）、TTL 竞态（R19）、stale-fence 瞬态无痕（R22）仍在 |
| S4 | leaf-worker 接口满足上游 dynamic workflow 齐全性（可获取分类） | `missing` | 无任何分类/策略/能力/namespace 目录接口（R8），`resolve_for_source` 丢弃 realm/type/channel |
| S5 | 可获取列表（分类 / 列表） | `partial` | task 列表在，但无 intake-items/lifecycle/process/namespace 列表，过滤维度不足（R9/R14）|
| S6 | 指定 intake 进入具体流程分支 | `partial` | 声明策略图内路由为真，但可达性晚期 409、registered_api 无法声明、断言矩阵不公开（R7）|
| S7 | 状态流转盲点 / 断点 | `partial` | 七意图主矩阵成立；deactivated 再 ingest 假账（R6）、rebuild admission 不一致（R26）、二次 delete 不对称（R30）为残余 |
| S8 | 内部数据埋点（可观测性 / 可解释性） | `partial` | 写入侧事件覆盖可观，但 DiagnosticSink 死代码（R11）、metrics 死系列（R12）、admission 零记录（R13）、payload 剥离（R10/R21）|
| S9 | 前端调试 / 重试 / 重启 / 删除 / 停止 | `missing` | 无 stage/process 视角（R14）、无 team intake 总览与 delete 回显（R15）、无 outbox 重投/repair 手动/进程 restart（R16）、retry/cancel 幂等不可区分（R23）|
| S10 | 第 1 轮 VF 台账修复到位性 | `partial` | 15 true-bug 中 VF24/26/30/31/12/11 等为真修复（正向核验）；VF19/VF16 名义修复（R3/R30 附）、VF1 带 registered_api 未闭环（R4）|

### 3.1 对齐结论

- **done**: `0`
- **partial**: `7`（S1 S2 S3 S5 S6 S7 S8 S10）
- **missing**: `3`（S4 S9 + S9 可拆两行计一）
- **stale**: `0`
- **out-of-scope-by-design**: `0`

> 总结：这更像「**核心后端骨架完成、默认 root 单机 happy path 成立，但四通道接线存在静默损坏路径，且 leaf-worker 接口与前端可观测面整体未交付**」的状态，而不是 `closed-with-explicit-deferrals` 的最终形态。campaign closure 的诚实性（deferred 登记、不伪造 S16）为真，但「closed」一词被「deferred 是切片而非面」所稀释。

---

## 4. Out-of-Scope 核查

> 本节确认 frozen/deferred 项是否被误判为 blocker，以及是否被越界实现。

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | 真实模型端点 / S11 身份改造 / PromptRef complete_bound（VF14.r） | `遵守` | 明确 owner-gated，本轮不视为缺口；但 R4 说明「registered_api.map」是**非委托的**闭集泄漏，不属于 O1 范围 |
| O2 | 进程级 kill + lease recovery（VF27.r） | `遵守` | 已登记 defer；本轮确认其外包络（R16 restart 面、R29 回旋）是运维缺口而非本战役承诺，分开记账 |
| O3 | stage envelope 去正文（VF3.r） | `遵守` | defer 有据（CAS-first 管线重写）；本轮未将其算入 R 项 |
| O4 | 全仓 910 证据（VF29） | `遵守` | campaign DoD 为 unique 62，非本阶段承诺 |
| O5 | kind 图 revision 升号（VF21）、四态预留（VF36）、sqlite 文本匹配（VF37）、checker 执行器（VF42） | `遵守` | 均为登记 defer 或 pre-existing；本轮不做 reopen |
| O6 | 本审查越过「已冻结 defer 清单」误报 | `误报风险` | R26 sink 显式防御：deactivated 再 ingest（R6/R26）不依赖任何 deferred 清单，是生产路径现状 — 维持成立 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`changes-requested — 第 2 轮不收口。四条 blocker 修复并将「分类/列表/分支/可观测」两面提交补充证据后，方可进入第 3 轮或 rereview。`
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. **R1**：单通道内容变更重摄入不得再产生悬挂 change_set / 丢失 accept_revision fact / 陈旧 fingerprint（`acceptance_snapshot.py`）。
  2. **R2**：`latest_revision_uuid` 更新加 CAS，败者 409（`acceptance_snapshot.py:191-195`）。
  3. **R3**：`representation_fact_digest` 接真实表示事实或删除该字段并声明 CONTROL 不绑定表示事实；生产公式与 `selected_output.py` 收敛单源（`runtime_materialize.py:884`）。
  4. **R6**：deactivated 项再 ingest 在 admission 拒绝（或显式 reactivate 过渡），不得白跑管线且不得写 active→active 假账。
  5. **R8/R9/R10**：补齐只读目录接口（分类/列表/namespace）、per-process 事件读取面（含 status_before/after）—— 否则「可获取分类/列表」「可解释性」两个目标面无法验收。
- **可以后续跟进的 non-blocking follow-up**：
  1. R4 闭集三面对账（registered_api capability 广告 / `registered_api.map`）
  2. R5 存储释放闭环（intake_snapshot_source_object + intake_artifact substrate）
  3. R7 admission 前置策略可达性（409 → 422）
  4. R11/R12/R13 诊断与 metrics 落地
  5. R14/R15/R16 前端 stage 视角 / team intake 总览 / outbox 重投 + repair 手动 + kill/restart
  6. R17-R19 竞态窗口原子化与文档
  7. R21-R32 其余 low/medium 项
- **建议的二次审查方式**：`independent reviewer rereview`（第 3 轮聚焦 5 个 blocker 的修复 diff，再验一次「名义修复」模式是否复现 — 本轮证实第 1 轮台账存在 ≥2 条自证修复与代码不符，rereview 必须要求 falsifiable 测试而非自评）
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> **归因总结（第 2 轮辩证结论）**：
> 1. **名义修复模式**：VF19（自证 fixed，值域错配）、VF16（自证 fixed，恒假守卫）两条修复在台账中标记 `self-claimed-only`，与代码实际不符 — 第 1 轮「ready-for-rereview」的自评门槛（§6.7 只复查 VF1/2/7/8/11/12/24）恰好漏掉了这两条与 VF1 的 registered_api 侧。
> 2. **静默正确性不对称**：registered_api 因其 public 冲击面获得了双层幂等/CAS，而单通道（inline/local/http）保留了「静默聚合」旧语义 — 同一接线段存在两套强度不一致的错误处理（R1/R2/R17）。
> 3. **「closed」与「deferred」的粒度问题**：closure 的 deferred 登记诚实，但多数 deferred（GC 收尾、artifact 清理、状态矩阵、observability 读面）实际是「生产路径上的真实缺口」而非「边界条件」；CROSS-NH 的 `closed-with-explicit-deferrals` 在数学上诚实，在交付语义上高估了完成度（S3/S5/S7/S9 现状）。
> 4. **接口/观察面从未进入 DoD**：campaign 的 62 unique 测试全部是后端内部闭环；「leaf-worker 接口齐全、前端可调试/重试/重启/删除/停止」没有一条测试或 evidence 锚点，因此该目标面的缺口在第 1 轮 4 方审查中全部未暴露 — 这是第 2 轮价值最大的新增面。

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| `v0.1` | 2026-08-31 | v4f | 第 2 轮独立静态审查（fix-verification + 全流程 + leaf-worker 接口 + 可观测性四簇 DAG；3 子代理进攻性审查 + 人工复核）；32 条 finding。 |