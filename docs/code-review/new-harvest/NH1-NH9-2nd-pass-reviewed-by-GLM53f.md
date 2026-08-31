# MKB new-harvest NH1–NH9 第 2 轮代码审查（GLM-5.3-Flash）

> 审查对象: `MKB new-harvest NH1–NH9 第 1 轮修复后代码（HEAD @ ba099ee，修复提交 59772f5 / 34ad2fb / ba099ee）`
> 审查类型: `rereview | mixed`（第 1 轮修复复核 + 端到端流程 / leaf-worker 接口面 / 可观测性运维面三路增量审查）
> 审查时间: `2026-08-30`
> 审查人: `GLM-5.3-Flash`（主审，独立思考）
> 审查范围:
> - `docs/code-review/new-harvest/NH1-NH9-review-VF-ledger.md`（第 1 轮合并台账，§6 为修复回填）
> - `src/`、`api/`、`tests/` 当前 HEAD 全量（四通道端到端链、HTTP 接口面、观测/运维面）
> 对照真相:
> - `docs/eval/new-harvest/final-execution-plan.md`（T-O-376..407）
> - `docs/closure/new-harvest/` 九份 AP closure + CROSS-NH campaign
> - `docs/closure/new-start/deferred-items-ledger.md`（NH-review-1 承接段）
> 文档状态: `changes-requested`

---

## 0. 总结结论

> 一句话 verdict：第 1 轮 24 项声称为 `fixed` 的修复中约 20 项经对抗复核真实落地（含 024 迁移、GC 对账、策略闭集、observation 409 语义等硬修复），四通道正向链端到端成立；但本轮发现**比第 1 轮任何 finding 都重的业务断点——registered-api 通道的失败恢复链是死路**（retry 确定性二次失败 + observation 快照永久 409），另有 2 项第 1 轮修复被证实为"假修复"（死代码守卫、假 digest 值），以及可观测面"库内证据完整、对外读取面断裂"的系统性缺口。目标③（竞态/错误幂等完善）在"正向幂等"维度成立、在"失败后恢复"维度不成立。

- **整体判断**：修复主体真实、正向链成立，但通道④恢复链断裂 + 两处假修复 + 观测读取面缺失，不满足第 1 轮"竞态、错误幂等机制完善"目标的完整口径，不应整体关闭。
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`（等待实现者按 §6 响应并修复 R1–R4）
- **本轮最关键的 1-3 个判断**：
  1. **通道④（registered-api）失败恢复链断裂**：child 失败后 `:retry` 的 root 重执行必然在 seal 步以 `INTAKE_SOURCE_MISSING` 二次失败——identity 采纳发生在 stage 信封序列化**之后**，采纳结果永远进不了信封（R1）；叠加 observation 快照永不删除且无条件 409（R2），accept 之后失败的采集数据**永久无法用同一 external_key 补齐**。这是"错误幂等机制完善"目标的正面断裂，非边界态。
  2. **两处假修复**：VF16 的 no-sandbox 扫描扫描的是自己一行前写死的 `["-headless"]` 字面量，raise 分支不可达（R6）；VF19 把 `output_manifest_digest` 直接别名成 `representation_fact_digest` 持久化，字段存在、值是假的（R3）。台账中两者均记为 `fixed`，台账可信度需打折。
  3. **可观测性呈"库内富、对外贫"结构**：append-only 事件流、process 行、stage envelope、representation facts 在库里基本完整，但真实 `error_message` 无任何接口可读（公开视图是固定文案）、封闭 metrics 目录约 2/3 全仓零 emit、supervisor 吞异常零感知、dead outbox 只能人工 SQL 解卡——"前端拥有足够接口进行调试/重试/恢复"不成立（R4、R5、R8、R9、R15）。

---

## 1. 审查方法与已核实事实

- **对照文档**：
  - `docs/code-review/new-harvest/NH1-NH9-review-VF-ledger.md`（64 原始 finding → 42 UF/VF 合并 + §6 修复回填，宣称 24 fixed / 6 partial / 9 defer / 3 ack）
  - `docs/eval/new-harvest/final-execution-plan.md`（T-O-376/378/381/383/390/397/402/407 等冻结真相）
  - `docs/closure/new-harvest/CROSS-NH-campaign.md` 及九份 AP closure（第 1 轮审查对象）
  - `docs/closure/new-start/deferred-items-ledger.md:77`（NH-review-1 承接段，已确认存在）
- **核查实现**：
  - 修复提交变更面：`git show --stat 59772f5 / 34ad2fb / ba099ee`（19 个生产文件 + 4 个测试文件 + 证据/文档，与台账 §6.4 清单吻合）
  - 修复位点逐一读码：`strategies.py`、`task_create.py`、`runtime_materialize.py`、`runtime_outcome.py`、`024_nh_review_invariants.sql`、`object_gc.py`、`local_store.py`、`object_upload.py`、`object_upload_ttl.py`、`acceptance_snapshot.py`、`acquisition_ingest.py`、`scatter_intake.py`、`kind_family.py`、`browser.py`、`pdf_parser.py`、`deterministic_ocr.py`、`api/app.py`、`api/public/routes.py`、`retrieval_request.py`
  - 接口面：`api/public/routes.py` + `api/internal/routes.py` 全部路由注册、`task_views.py`、`task_projections.py`、`task_commands.py`
  - 观测面：`runtime/metrics.py`、`workflow_supervisor.py`、`runtime_outbox.py`、`runtime_repair.py`、`runtime/health.py`、`observability.py`、`retrieval_pack.py`
- **执行过的验证**：
  - `.venv/bin/python -m pytest tests/e2e/test_nh1_nh9_review_fixes.py` → **7 passed**（主审亲跑）
  - 子代理簇 A 实测：review-fixes 7 passed、`test_nh4_upload_uow.py` 5 passed、`test_new_harvest_crash_windows.py` 12 passed、`test_nh3_declared_reacquire.py + test_nh7_exhausted_zero.py` 8 passed、nh4 race/security/public 15 passed；另以 /tmp 临时探针实证 VF1 闭集四组合行为与 VF7 三态（成功/REPLAY/CONFLICT 零新行），探针未入库
  - 子代理簇 B 实测：`test_new_harvest_closed_set.py + test_nh4_upload_then_ingest.py + test_registered_api_scatter.py` 26 passed（334s）；另以临时探针实证通道④ retry 死路（构造 root 成功 + child 失败，`POST :retry` 后 seal 步 `INTAKE_SOURCE_MISSING`）
  - 全仓 grep 反证：`INTAKE_OBSERVATION_REPLAY` 与 `lifecycle_success` 在 `tests/` 零引用（R18 依据）；`mkb_outbox_depth` / `mkb_process_claim_total` / `mkb_lease_recover_total` / `mkb_worker_queue_lag_seconds` 在 `src/`（metrics.py 之外）零 emit（R5 依据）；`DELETE FROM mkb_intake_snapshots` 全仓零命中（R2 依据）；`requeue` 在 src/api 零命中（R9 依据）
- **复用 / 对照的既有审查**：
  - 第 1 轮四份审查与本轮 `NH1-NH9-review-VF-ledger.md` — 作为复核基线与对照真相使用；本轮全部承重结论由主审独立读码/复跑测试/读探针记录后采纳，未采纳任何未经验证的子代理断言

### 1.1 已确认的正面事实

- **修复主体真实**：VF1（策略闭集 422 + 运行时 claimed≠bound 409，主审确认 claimed 来源真实可触发）、VF2/VF4（024 trigger 列集与正常 UPDATE 不相交，migration runner 真实加载，trigger 实弹测试通过）、VF5（latin-1 双射 round-trip + 原 media_type 保真）、VF6（canonical records SHA-256 两侧同算法）、VF7（admission 前查重 + scatter 事务内二次查重，409 语义经探针实证正确）、VF8（5 系统键拒写 + 未注册键 422，无大小变体绕过面）、VF11（reconcile_quarantine 只对 `tombstoned_at IS NULL` 行 restore，不复活用户删除）、VF15（readiness 剔除未启用 multimodal）、VF17（非 root 加 `-U --map-root-user`）、VF18（prefix 守卫显式声明 + dict 去重）、VF22/VF23/VF28/VF40（digest 钉死进测试、closure 销账）、VF24（stale-process-fence 与成功路径同构，crash-windows 12 用例过）、VF26（reacquire 仅 plan 声明才执法，http 图声明/inline 不声明符合 T-O-402）、VF30/VF31/VF32/VF33 均为 `fixed-verified`。
- **四通道正向链端到端成立**：inline / local-object / http-resource 三通道从入口到检索命中的完整链均有 e2e 以检索断言收口（closed-set 26 passed）；失败路径收敛（lease 过期 → `recover_expired_leases`、waiting 五种 reason 均有 repair 分支、`repair_once` fail-closed），未发现 stuck 状态。
- **024 trigger 不阻断合法发布路径**：indexed-identity trigger 只在 OLD='indexed' 且 content_digest 变化时 abort；publish 前置 withdrawn 断言；全库无 facts/history 的 UPDATE/DELETE。
- **cancel 语义干净**：202 + CAS 置 cancelling + fencing_generation 提升 + outcome 双重拒绝，cancel 后 node 不会继续写库；deactivate 后检索读时逐条校验 lifecycle，下一次查询即生效。
- **deferred 诚实**：9 项 deferred 全部登记于 `deferred-items-ledger.md` NH-review-1 段；未伪造真模型 live、未伪造 S16、未做 kind revision 升号——与台账 §6.7 前提一致。

### 1.2 已确认的负面事实

- **通道④恢复链断裂**（R1/R2，主审读码确认机制 + 簇 B 探针实证行为）：`_acquire_registered_api_collection` 在 `acquisition_ingest.py:423` 用含新造 `intake_source_uuid=uuid7()`（`:384`）的 `next_state` 构建并序列化 stage 信封；identity 采纳只发生在其后定义的 outcome 回调内（`:447-476`，INSERT OR IGNORE + 采纳已存在 uuid），对已冻结的信封字节永不可见。单条通道因 `_material` 之前预解析 identity（`:129-137`）而正确；scatter 路径缺此步。`ScatterAcceptanceWriter.commit` 对已存在快照无条件 409（`scatter_intake.py:180-196`），全库无快照删除路径。
- **两处假修复**（R3/R6）：`runtime_materialize.py:884` `"representation_fact_digest": selected["output_manifest_digest"]`；`browser.py:249-251` 扫描对象是上一行刚写死的 `["-headless"]`。
- **VF12 降级**：hold 创建已独立化（每上传独立 uuid7 owner，`object_upload.py:105-126`），但 cancel/TTL 释放按 `ORDER BY created_at DESC LIMIT 1` 取"最新一条"而非"调用者的"（`object_upload_ttl.py:73-81`），且 cancel API 无会话标识；`acceptance_snapshot.py:331-335` ingest 时仍释放该对象全部 upload_pending hold。台账记 `fixed` 不准确。
- **观测读取面断裂**：`runtime_outcome.py:615-616` final_error_message 固定文案；公开 task view 只有 error.code + 该固定 message；失败 event payload 不含 message；operator timeline 只返回 payload_digest；无 per-task processes 端点。
- **metrics 死目录**：`mkb_outbox_depth`、`mkb_outbox_dead_oldest_age_seconds`、`mkb_process_claim_total`、`mkb_process_running`、`mkb_worker_queue_lag_seconds`、`mkb_lease_recover_total`、`mkb_repair_applied_total`（runtime 内）、`mkb_gc_*`、`mkb_alert_raised_total` 等全仓零 emit；无每通道/每阶段维度（目录刻意禁 label）。
- **supervisor 静默**：`workflow_supervisor.py:47-61,72-77` 吞 Exception 只写内存字段，无日志无指标；`runtime/health.py` 只聚合 probe，不读 `last_error/consecutive_failures`。
- **测试缺口与台账夸大**：VF5（CAS 逐位 round-trip）、VF6/VF7（`INTAKE_OBSERVATION_*` 零测试引用）、VF12（cancel 所有权）、VF17、VF19、VF24（无专项）、VF25（`lifecycle_success` 零断言）、VF33 均无对应测试；台账 §6.5 将 VF6/VF7/VF25 记在"NH7 scatter 等既有用例 pass"名下，属覆盖声明夸大。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | yes | 全部承重 finding 均由主审亲读 file:line 复核 |
| 本地命令 / 测试 | yes | 主审亲跑 review-fixes 7 passed；子代理另跑 6 组共 65+ 用例全绿 + 2 个临时探针 |
| schema / contract 反向校验 | yes | 024 trigger 列集 × 正常 UPDATE 语句逐条比对；closed-set 422/409 错误码形状核对 |
| live / deploy / preview 证据 | no | 单机本地系统，无 deploy 面 |
| 与上游 design / QNA 对账 | yes | T-O-376/381/397/402/407 与实现逐条对账 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | 通道④ retry 死路：identity 采纳晚于信封冻结 | high | correctness | yes | fix |
| R2 | 通道④ observation 快照永久 409，失败采集无法同 key 补齐 | high | correctness | yes | fix |
| R3 | VF19 假修复：output_manifest_digest 冒充 representation_fact_digest | high | correctness | no | fix |
| R4 | 失败原因不可通过任何接口回答 | high | platform-fitness | no | fix |
| R5 | 封闭 metrics 目录约 2/3 零 emit，ALERT 永不触发 | high | platform-fitness | no | partial-fix |
| R6 | VF16 假修复：no-sandbox 扫描是死代码 | medium | test-gap | no | fix |
| R7 | VF12 降级：hold 释放未按所有者归属化 | medium | correctness | no | fix |
| R8 | supervisor 吞异常零感知 | medium | platform-fitness | no | fix |
| R9 | dead outbox 无重投路径，只能人工 SQL | medium | platform-fitness | no | fix |
| R10 | 单 kind 任务 /items outcome 恒 active | medium | correctness | no | fix |
| R11 | fan-in waiting 对外折叠为 running，无解释字段 | medium | platform-fitness | no | fix |
| R12 | retrieval 冷启动死锁：namespace_key 无发现端点 | medium | platform-fitness | no | fix |
| R13 | 并发同 external_key 的 identity 采纳竞态（R1 同根因） | medium | correctness | no | fix（与 R1 同修） |
| R14 | quarantine 永久滞留泄漏（VF11 残余） | medium | correctness | no | fix |
| R15 | DiagnosticSink 形同虚设 | medium | platform-fitness | no | partial-fix |
| R16 | 分类/发现面缺失：兼容矩阵与 workflow 列表不可查询 | medium | platform-fitness | no | fix |
| R17 | admission 不校验 local_object handle 存在性 | low | correctness | no | fix |
| R18 | VF6/VF7/VF25 等 fixed 项零专项测试，台账 §6.5 覆盖声明夸大 | medium | test-gap | no | fix |
| R19 | 可解释性最后一公里断裂：表示链三表无 API、检索不回显源身份 | medium | platform-fitness | no | partial-fix |
| R20 | 错误码双轨命名削弱上游契约 | low | protocol-drift | no | followup |
| R21 | 可重试性无标志、item 级重试"看得见发不出"、列表缺 kind 过滤 | low | platform-fitness | no | followup |

### R1. 通道④ retry 死路：identity 采纳晚于信封冻结

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/intake/acquisition_ingest.py:384` — scatter acquire 在 `next_state` 中新造 `"intake_source_uuid": uuid7()`
  - `src/runtime/intake/acquisition_ingest.py:423` — `material = self._material(command, next_state, ...)` 在此刻把 `next_state` canonical_json 冻结进信封字节
  - `src/runtime/intake/acquisition_ingest.py:447-476` — identity 采纳（`INSERT OR IGNORE` + 采纳已存在行的 uuid 回写 `next_state`）发生在其后定义的 outcome 回调内，对已冻结信封永不可见
  - 对照：单条通道在 `_material` **之前**预解析 identity（`acquisition_ingest.py:129-137`），故正确；scatter 路径缺此步
  - 行为实证（簇 B 临时探针）：root 成功 + 一个 child 失败的任务，`POST :retry` 后 generation+1 root 重执行，`acquire_registered_api` succeeded、`seal_candidate_set` failed(`INTAKE_SOURCE_MISSING`)、root failed
- **为什么重要**：
  - retry 是通道④失败后唯一内建恢复手段；当前实现使 retry 从"幂等重放"变成"确定性二次失败"。retry_wait 自动重试路径同理。这直接击穿第 1 轮目标③"错误幂等机制完善"在通道④的承诺。
- **审查判断**：
  - 这是本轮最重的生产路径 correctness 缺陷，且是"幂等意图（INSERT OR IGNORE 表达的采纳）与实现（信封时序）逻辑冲突"的结构性问题，不是边界态。closed-set 测试全部走首跑路径，所以 62 用例全绿也测不到它。
- **建议修法**：
  - 把 identity 预解析提前到 `_material` 之前（对齐单条通道 `:129-137` 的模式），或在回调采纳后重建/重算信封 state 再提交；同时补一条"child 失败 → :retry → 成功收敛"的 e2e。

### R2. 通道④ observation 快照永久 409，失败采集无法同 key 补齐

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/services/scatter_intake.py:180-196` — 对已存在 `(intake_source_uuid, observation_key)` 快照无条件 409（REPLAY / CONFLICT），无任何"采纳已有坐标"的放行分支
  - 全仓 grep `DELETE FROM mkb_intake_snapshots` 零命中——快照永不删除
  - `src/runtime/task/task_create.py:452-480` — admission 侧同 key 同 records → `INTAKE_OBSERVATION_REPLAY` 409
  - 错误文案 "reuse the original coordinates" 所指的采纳路径在代码中不存在
- **为什么重要**：
  - 叠加 R1：一个在 accept 之后失败的 registered-api 采集（child 失败、gate reject），其数据**永久无法用同一 external_key 补齐**——retry 死于 R1，重提死于本条 409。caller 唯一出路是换 external_key，产生重复 intake item，违背幂等目标。409 作为"防重放守卫"本身正确，问题是没有为"失败后合法补齐"留任何出口。
- **审查判断**：
  - 409 守卫语义本身经探针实证正确（首跑成功、二次同 key 409 零新行），问题在于恢复通道整体缺位，与 R1 构成通道④恢复链的完整死锁。
- **建议修法**：
  - 定义"失败任务的 observation 复用"语义：同 key 同 fingerprint + 原 Task 处于 failed/cancelled → 放行复用原 intake_source/快照坐标（而非 409），或在任务彻底失败时提供显式的 observation 释放命令。

### R3. VF19 假修复：output_manifest_digest 冒充 representation_fact_digest

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/workflow/runtime_materialize.py:884` — `"representation_fact_digest": selected["output_manifest_digest"]`，直接把 output manifest digest 别名成 representation fact digest
  - 真实的表示事实 digest 是 `mkb_representation_facts.fact_digest`（`representation_history.py:29`），两者语义不同
  - `selection_digest` 仅与自己重放比较（`runtime_materialize.py:912-916`），故假值不会自爆；零测试断言该字段
- **为什么重要**：
  - 第 1 轮 Gemini-R19 的核心诉求是"selection 绑定真实表示事实"；当前修复只是让字段存在、值是错的。未来任何真实的 digest 校验者（或消费该字段的下游）都会被持久化的假值误导，且它已被 seal 进 selected_outputs 表。
- **审查判断**：
  - 台账 §6.2 将 VF19 记为 `fixed`，不成立——"字段存在、值错误、零测试"比"字段缺失"更糟。
- **建议修法**：
  - 在 materialize 时从 `mkb_representation_facts` 取真实 `fact_digest`（或显式把字段改名/删除并诚实登记 defer），并补断言测试。

### R4. 失败原因不可通过任何接口回答

- **严重级别**：`high`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/workflow/runtime_outcome.py:615-616` — `final_message = "Workflow reached a terminal failure route"`（固定文案），真实 error_message 只落 `mkb_processes.error_message`（`:501-518`，redact + 512 截断）
  - 公开 task view 只给 `error.code` + 上述固定 message；失败 event payload 只有 `error_code + failure_disposition`（`runtime_outcome.py:527`）
  - operator timeline 只返回 `payload_digest` 不返回 payload（`observability.py:405-410`，注释自认）
  - 无 per-task processes 端点——每 node 的 IO digest/耗时/失败点封死在库内
- **为什么重要**：
  - "这条文档为什么没进库"是 intake 系统最基本的可回答问题；当前必须人工 SQL。本轮审查目标之四（前端拥有足够接口和信息进行调试）在此维度不成立。
- **审查判断**：
  - 库内证据链本身完整（这是正面事实），缺的纯粹是读取面；修复成本低（公开 view 放行 redacted message + per-task processes 只读端点）。
- **建议修法**：
  - 公开 task/generation view 放行 redacted error_message；增加 `GET /tasks/{id}/processes` 只读投影；失败 event payload 补 redacted message。

### R5. 封闭 metrics 目录约 2/3 零 emit，ALERT 永不触发

- **严重级别**：`high`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - 全仓 grep：`mkb_outbox_depth`、`mkb_outbox_dead_oldest_age_seconds`、`mkb_process_claim_total`、`mkb_process_running`、`mkb_worker_queue_lag_seconds`、`mkb_lease_recover_total`、`mkb_repair_applied_total`（runtime 内）、`mkb_gc_orphans_deleted_total`、`mkb_gc_fail_total`、`mkb_alert_raised_total`、`mkb_index_generation_active`、`mkb_inference_duration_seconds` 等在 metrics.py 之外零 emit
  - 实际有 emit 点的仅约 15 条（sec_*、readiness、retention、diagnostic_drop、outbox_dead、task_result_disposition、workflow_legacy_pin、cardinality_drop）
  - 目录刻意禁 per-channel / per-process_key label（`metrics.py:15-17` `_FORBIDDEN_LABELS`），四通道无任何独立可观测维度
  - 10 个 `ALERT_*` 常量永不触发（含 `ALERT_OUTBOX_DEAD`——而 outbox 8 次后即 dead）
- **为什么重要**：
  - outbox 积压、死信年龄、lease 卡死、修复量是本系统最核心的运维信号；当前全部不可观察。指标目录的存在给人"已覆盖"的错觉，实际是死目录。
- **审查判断**：
  - 这与第 1 轮 R20（后台扫描吞异常）同族——"面向故障的观测点写了目录、没写 emit"。进程内存注册表重启清零也使累计值无意义。
- **建议修法**：
  - 至少为 outbox 深度/死信年龄/lease 恢复/repair 应用四处补 emit；要么删掉死目录要么诚实标注 reserved。per-channel 维度可另立 charter（目录禁 label 是反基数决策，尊重之，但至少补 process_key=none 的聚合维度）。

### R6. VF16 假修复：no-sandbox 扫描是死代码

- **严重级别**：`medium`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/supply/browser.py:249-251` — `firefox_args = ["-headless"]` 是上一行刚写死的字面量，紧接其后的 `any("no-sandbox" in argument ...)` 恒为 False，raise 分支不可达
  - 该守卫不扫描任何来自配置/请求的输入（session args 本就 code-owned）
- **为什么重要**：
  - 台账 §6.2 将 VF16 记为 `fixed`，是假阳性。守卫给人"已有防护"的错觉；未来若 args 配置化，这个守卫形态（扫描局部字面量）也会被复制错。
- **审查判断**：
  - 无运行时危害（今天没有输入源），属"修复形态错误 + 台账可信度"问题，与 R3 同族但危害低。
- **建议修法**：
  - 把守卫移到 session args 的真实组装点（`/session` payload 的 `moz:firefoxOptions.args`）并扫描该列表；或诚实承认当前 args 全 code-owned、删除守卫并登记。

### R7. VF12 降级：hold 释放未按所有者归属化

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - hold 创建已独立化：`src/services/object_upload.py:105-126` 每上传独立 uuid7 owner（`021` 唯一索引允许 N 条并发 hold，race 测试 pending=2 过）
  - 但释放未归属化：`src/services/object_upload_ttl.py:73-81` cancel/TTL 释放 `ORDER BY created_at DESC LIMIT 1`（最新一条，而非调用者的）；cancel API 只有 team+handle、无会话标识（`api/public/routes.py:159-169`）
  - `src/runtime/intake/acceptance_snapshot.py:331-335` — ingest 成功时释放该对象**全部** upload_pending hold（含他人未完成上传的）
- **为什么重要**：
  - 并发同字节上传场景下，A 的 cancel 会打掉 B 的在途 hold；ingest 收口会清掉所有人的 hold。24h TTL 是唯一兜底，行为可用但与第 1 轮 R5 的修复意图（hold 归属化）不符。
- **审查判断**：
  - 损害有 TTL 兜底、窗口小，不 blocker；但台账记 `fixed` 过度——修了"创建侧"没修"释放侧"。
- **建议修法**：
  - cancel API 增加 owner/session 标识并只释放对应 hold；ingest 收口只释放触发本次 ingest 的 hold（或保留语义但文档化"收口=全释放"的取舍）。

### R8. supervisor 吞异常零感知

- **严重级别**：`medium`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/workflow_supervisor.py:47-61,72-77` — `drain_once`/`run` 捕获 Exception 只写内存字段 `last_error/consecutive_failures`，无日志、无指标
  - `src/runtime/health.py` — readiness 聚合器只读 probe，不读 supervisor 的 `last_error/consecutive_failures`
- **为什么重要**：
  - 单进程架构下 supervisor 是唯一推进循环；它可以永久空转（每 tick 吞一个异常）而外部零感知——/ready 仍绿、无日志、无指标。这是最重的单点静默。
- **审查判断**：
  - 与第 1 轮 VF33 的修复精神（fail-loud 扫描）一致但未覆盖此位点；属修复范围的系统性遗漏。
- **建议修法**：
  - `except` 分支补 `logging.exception` + 计数器；readiness 纳入 `consecutive_failures` 阈值（或至少暴露在 /ready body）。

### R9. dead outbox 无重投路径，只能人工 SQL

- **严重级别**：`medium`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/runtime_outbox.py:417` — 8 次后 dead
  - `api/internal/routes.py:14-161` — 只有 prompts/timeline/dead-outbox（只读）/security-audit；全仓 grep `requeue` 零命中；无 CLI 命令
  - `ALERT_OUTBOX_DEAD` 永不触发（R5）
- **为什么重要**：
  - dead outbox 里的可能是某条 intake 的关键事件；解卡唯一手段是人工 `UPDATE mkb_outbox SET status='pending'`，绕过全部审计。
- **审查判断**：
  - operator 面自认 "bounded v1 operator surface is empty"（`internal/routes.py:11-13`），是既定 bounded v1 取舍；但 dead-outbox 只读端点的存在说明作者已意识到该需求，只差一个 requeue 命令。
- **建议修法**：
  - internal 面补一个带审计的 `POST /outbox/{id}:requeue`（operator token），并接 `ALERT_OUTBOX_DEAD`。

### R10. 单 kind 任务 /items outcome 恒 active

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/task/task_projections.py:112-122` — item outcome 由 child execution 子查询推导（`child_status` 来自 `parent_execution_uuid=root AND target_uuid=intake_item_uuid` 的 execution）
  - inline/local_object/http_resource 图无 child execution → `child_status` NULL → outcome 恒 "active"、result_ref/proof_ref NULL——即使 Task 已 succeeded
  - 簇 C 以 TestClient 实测：succeeded 任务的 GET /items 返回 `'outcome': 'active', 'result_ref': None`
- **为什么重要**：
  - 上游若以 item outcome 判断单 kind 任务完成会永久挂起；三个单 kind 通道的正确完成信号只剩 Task 根视图。
- **审查判断**：
  - scatter 专用投影被无差别套用到单 kind 任务；`publication_ready` 字段反而正确——投影层口径分裂。
- **建议修法**：
  - 单 kind 任务从 root execution 状态推导 outcome（succeeded → item succeeded），或文档明示单 kind 以 Task 视图为准并给 item 加 `outcome: "n/a-single-kind"`。

### R11. fan-in waiting 对外折叠为 running，无解释字段

- **严重级别**：`medium`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/workflow/runtime_scatter.py:108` — fan-in 等待写 `status='waiting', waiting_reason='scatter_children'`
  - `src/runtime/task/task_views.py:203-215` — `_public_execution_status` 把 waiting 映射为 running；任何视图不含 waiting_reason
  - Task 停在 running 且 counts.active 已归零（`runtime_core.py:765,850`）——"running 但 active=0"是上游唯一可猜的 fan-in 信号
- **为什么重要**：
  - "指定 intake 进入流程分支后观察状态流转"（本轮目标三）在 scatter fan-in 这一步对外不可解释；Process 级 claimed/retry_wait/attempt 计数同样对上游不可见。
- **审查判断**：
  - 六态词表是有意收窄（正向取舍），但 waiting→running 的折叠让 fan-in 与真 running 不可区分，属口径选择遗漏。
- **建议修法**：
  - generation view 增加 `waiting_reason` 透传（不扩态，只加解释字段），或在 counts 中加 `awaiting_fanin`。

### R12. retrieval 冷启动死锁：namespace_key 无发现端点

- **严重级别**：`medium`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/contracts/api/models.py:608-611` + `src/services/retrieval/retrieval_request.py:268-274` — namespace_key/uuid 必填，否则 422 `RETRIEVE_SCHEMA_NAMESPACE_REQUIRED`
  - namespace_key 由内部 embedding 绑定坐标拼出（`vector_publish_commit.py:266-270`），全仓无列出端点
  - NH8 e2e 自己也只能直读 `mkb_vector_namespaces` 表（`tests/e2e/test_nh8_api_item_intents.py:135`）——连官方测试都绕过 API
- **为什么重要**：
  - 上游发不出第一次搜索；"用检索发现 intake_item_uuid"的路径实际不可用。
- **审查判断**：
  - 强制 namespace 是 Layer-A 安全决策（正确），缺的只是配套发现端点。
- **建议修法**：
  - 补 `GET /teams/{t}/namespaces` 只读端点（或 retrieval 422 的 details 回显该 team 的合法 namespace_key）。

### R13. 并发同 external_key 的 identity 采纳竞态（R1 同根因）

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - 与 R1 同机制：两个同 external_key 任务并发 ingest 时，后者的 `INSERT OR IGNORE` 被唯一索引忽略而信封仍带自己的新 uuid，seal 步 `INTAKE_SOURCE_MISSING` 409 终态失败——表现为可观察终态（不卡死），但与"INSERT OR IGNORE 表达的幂等意图"逻辑冲突
- **为什么重要**：
  - 1/2/3 通道同样中招（单条通道的预解析与 outcome UoW 之间有竞态窗口），只是触发条件更窄。
- **审查判断**：
  - 与 R1 同根因不同触发；修 R1 时一并覆盖。
- **建议修法**：
  - 同 R1（预解析 + 信封时序修复后此窗口自然闭合；再补并发同 key 测试）。

### R14. quarantine 永久滞留泄漏（VF11 残余）

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/services/object_gc.py:169-189` + `local_store.py:222-234` — reconcile 只对 `tombstoned_at IS NULL` 行 restore（正确，不复活用户删除）
  - 残余：TX2 commit 后、destroy 前崩溃 → 行已 tombstoned，该 quarantined 文件被 reconcile 跳过（`:183`）也被 `collect_candidates` 排除（`:152`）→ **永久滞留 quarantine，无任何清理路径**
- **为什么重要**：
  - "字节已删"的证据与磁盘现实脱节；泄漏缓慢累积。删除语义未被破坏（不会复活）。
- **审查判断**：
  - VF11 主修复成立（crash 窗口已闭合大半），这是残余边角；触发条件是 TX2 后 destroy 前的窄崩溃窗口。
- **建议修法**：
  - scan 增加对 tombstoned 行的 quarantined 文件清理分支（确认 tombstoned 后直接物理删除）。

### R15. DiagnosticSink 形同虚设

- **严重级别**：`medium`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - `mkb_ops_diagnostic_logs` 的业务写入者只有 `generation_construct.py:1277,1371` 两处；acquire/decode/clean/vectorize 失败一律不进诊断表
  - 该表无任何读取 API（ObservabilityReadService 只有 timeline/dead_outbox/security_audit）
- **为什么重要**：
  - 诊断基建存在、无人写入、无法读取——三重空转。
- **审查判断**：
  - 与 R4 同族（读取面缺失），但写入面也缺；不 blocker，因为失败证据在 mkb_processes 里仍可 SQL 还原。
- **建议修法**：
  - 至少把 acquire/decode/clean/vectorize 的失败统一写 DiagnosticSink，并补 operator 读取端点；或诚实降级为 reserved。

### R16. 分类/发现面缺失：兼容矩阵与 workflow 列表不可查询

- **严重级别**：`medium`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - 合法 source_kind（4 值）/clean_strategy（10 值）/七 intent 只存在于 pydantic Literal（`src/contracts/api/models.py:22/44/346`），仅可经隐式 /openapi.json 反射得知
  - kind×strategy 兼容矩阵唯一 oracle 是运行时 422 `CLEAN_STRATEGY_KIND_INCOMPATIBLE`（`src/contracts/intake/strategies.py:193-208`）
  - workflow 注册 `read_exposure='internal'`（`workflow_registry.py:244-245` 附近），无任何 GET 列出端点
- **为什么重要**：
  - 上游无法在发请求前知道"什么合法"；只能试错。leaf-worker 的"分类"维度判定 partial。
- **审查判断**：
  - kind-only resolver 本身工作正确（NH8 七意图 admission 闭集 10 用例过）；缺的是发现面而非路由能力。
- **建议修法**：
  - 补只读 `GET /workflow-catalog`（或 /capabilities）端点回显 kind×strategy 矩阵与活跃 workflow key。

### R17. admission 不校验 local_object handle 存在性

- **严重级别**：`low`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/contracts/api/models.py:165` — `logical_handle` 仅 pattern 校验格式（`^mkbobj:v1:...$`），无存在性/pending 校验；拼错 handle 的任务排队后才在 acquire 步以 `OBJECT_CATALOG_REQUIRED` 失败，且失败前占住 pending hold 至 TTL
- **为什么重要**：
  - 非 stuck、可观察终态，但错误反馈延迟到异步阶段并白占 hold 24h。
- **审查判断**：fail-fast 缺失，非断链。
- **建议修法**：admission 时校验 handle 对象存在且非 tombstoned（一次 SELECT 的成本）。

### R18. VF6/VF7/VF25 等 fixed 项零专项测试，台账 §6.5 覆盖声明夸大

- **严重级别**：`medium`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `tests/e2e/test_nh1_nh9_review_fixes.py`（7 用例）只覆盖 VF1/VF2/VF8/VF11/VF15/VF18/VF31
  - 全仓 grep：`INTAKE_OBSERVATION_REPLAY`、`lifecycle_success` 在 tests/ 零引用；VF5（CAS 逐位 round-trip）、VF12（cancel 所有权）、VF17、VF19、VF24（无专项）、VF33 同样零专项测试
  - 台账 §6.5 将 VF6/VF7/VF25 记在"NH7 exhausted/zero/multimodal/scatter pass"名下，那些是既有用例，并不覆盖这三个修复点
- **为什么重要**：
  - 没有 regression 护栏，任何后续改动（如 records 模型加字段导致 observation digest 漂移）会静默把 REPLAY 变 CONFLICT 或反之（R7 的 409 语义尤其依赖 digest 稳定性）。台账的 `independently-verified` 标记与 §6.5 覆盖声明需要区分对待。
- **审查判断**：
  - 修复语义本身经本轮探针实证正确（这是正面事实），缺的是常驻护栏；§6.5 的覆盖表述属诚实性瑕疵而非伪造（实现者在 §6.2 自己标了 self-claimed-only）。
- **建议修法**：
  - 为 VF6/VF7（三态 409 + digest 稳定性）、VF25、VF5 round-trip 补常驻测试。

### R19. 可解释性最后一公里断裂：表示链三表无 API、检索不回显源身份

- **严重级别**：`medium`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - 检索结果带 `generation_refs` + coordinate + traceback/inflation status（`retrieval_pack.py:92-114`）——链回 generation 完整、诚实降级可观察（正面）
  - 但不含源层身份：无 `source_external_key`、无 raw/clean digest 回显；`mkb_representation_facts`/`mkb_acquire_decode_history`/`mkb_intake_revision_semantics.value_provenance` 三张解释性表全部无 API；无公开 intake item 端点
  - `/task-lineage` 自认 "restart ledger truth only"（`task_projections.py:538-541`），只覆盖 restart 因果
- **为什么重要**：
  - 从检索 hit 追到源文档"最后一公里"链不上（前端视角）；digest 链在库里连续，读取面断了。
- **审查判断**：
  - 与 R4/R15 同族（库内富、对外贫）；因涉及新公开面设计，列为 partial。
- **建议修法**：
  - 检索 hit 回显 source_external_key + team；补 intake item 只读端点回显 representation facts 摘要。

### R20. 错误码双轨命名削弱上游契约

- **严重级别**：`low`
- **类型**：`protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - `SCREAMING_SNAKE`（`SOURCE_KIND_INVALID`、`CLEAN_STRATEGY_KIND_INCOMPATIBLE`、`INTAKE_SEMANTIC_KEY_UNREGISTERED`、`INTAKE_OBSERVATION_REPLAY`）与 kebab/lower（`task-schema-invalid`、`intake-item-deleted`、`gate-revision-conflict`）双轨并存
  - closed-set `_CLOSED_422/_CLOSED_409` 闭集同时收纳两种风格（`tests/unit/test_nh8_intent_applicability.py:17-34`）；intake 域 409 无 details 而 metadata 域 409 带 details
- **为什么重要**：上游无法按统一形状编程错误处理。
- **审查判断**：错误信封本身统一（MkbError → error{code,message,details} + trace/request），新 4xx 遵循同一信封（改善）；双轨是历史包袱。
- **建议修法**：登记 alias 迁移 charter，新错误码一律 SCREAMING_SNAKE + details。

### R21. 可重试性无标志、item 级重试"看得见发不出"、列表缺 kind 过滤

- **严重级别**：`low`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - task view 无 retryable 标志，上游只能试错（`task_commands.py:259-262` 只收 failed/cancelled）
  - `/task-restarts` 暴露 `scope=atomic_intake_item` 过滤，但 item 级重试无直接 HTTP 命令（只能经 intake.rebuild 间接产生）
  - `GET /tasks` 无 source_kind / intake_item 过滤
- **为什么重要**：上游编排需要自己猜状态机；能力"看得见发不出"。
- **审查判断**：均为小的接口面补全，不 blocker。
- **建议修法**：view 加 retryable 布尔；列表加 source_kind 过滤；评估 item 级重试命令。

---

## 3. In-Scope 逐项对齐审核

> 本轮 In-Scope = 第 1 轮 VF 台账的修复承诺 + 第 2 轮三项增量审查维度。结论统一 `done | partial | missing | stale | out-of-scope-by-design`。

| 编号 | 计划项 / 承诺 | 审查结论 | 说明 |
|------|--------------|----------|------|
| S1 | VF 台账 §6.2 宣称的 24 项 `fixed` 真实落地 | `partial` | 约 20 项 fixed-verified（含全部 [true-bug] 硬修复）；VF16/VF19 假修复（R6/R3）、VF12 降级（R7）、VF6/7/25/5/12/17/19/24/33 零专项测试（R18） |
| S2 | 目标① 四通道实际接线（端到端正向链） | `done` | 四通道正向链全部端到端成立并各有 e2e 检索断言收口；closed-set 26 passed 复跑确认 |
| S3 | 目标② dynamic workflows 落地与路由接管 | `done` | kind-only resolver 正确、路由完整、024 不阻断发布、T-O-376 成立；发现面缺失（R16）不影响路由能力本身 |
| S4 | 目标③ 竞态/错误幂等机制完善 | `partial` | 正向幂等成立（fingerprint/replay/seal-once/hold/409 守卫）；但通道④失败恢复链死路（R1/R2 blocker）+ 并发采纳竞态（R13）——"失败后恢复"维度不成立 |
| S5 | 第 2 轮维度：端到端流程正确性（含失败流转） | `partial` | ①②③通道失败流转收敛无 stuck；④失败即死路（R1/R2）；横切（024/stale-fence/exhausted_zero）验证无阻断 |
| S6 | 第 2 轮维度：leaf-worker 接口完备性 | `partial` | 列表 complete、分支进入 complete；分类 partial（R12/R16）、状态流转 partial（R10/R11）、可重试性弱（R21） |
| S7 | 第 2 轮维度：可观测性/可解释性/运维操作面 | `partial` | 库内埋点基本完整（正面）；读取面断裂（R4/R15/R19）、metrics 死目录（R5）、supervisor 静默（R8）、dead outbox 无重投（R9）；重试 partial（VF10 承接中）、重启恢复 partial（repair_once 覆盖广）、删除停止 sufficient |
| S8 | deferred 9 项诚实登记 | `done` | `deferred-items-ledger.md:77` NH-review-1 段确认存在，未伪造不修项 |

### 3.1 对齐结论

- **done**: 3（S2/S3/S8）
- **partial**: 5（S1/S4/S5/S6/S7）
- **missing**: 0
- **stale**: 0
- **out-of-scope-by-design**: 0

> 一句话：第 1 轮修复让"正向链"达到可关闭质量（目标①②可判 done），但本轮新增的三个审查维度一致指向同一个结构性状态——**系统在"失败之后"的世界里尚未完工**：通道④失败即死路（correctness），失败原因不可读（observability），失败信号不可见（metrics/supervisor）。目标③与三个增量维度同判 partial，且共享同一个根因家族。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | T-O-381 registered-api 无网络 fetcher（caller_frozen_records.v1） | `遵守` | 修复未引入任何网络 fetcher；VF6/VF7 只动了 digest 与查重 |
| O2 | 真模型 live / S16 签收（owner-gated） | `遵守` | 未伪造 live、未伪造 S16；VF14 保持诚实披露 |
| O3 | kind revision 升号（VF21 deferred） | `遵守` | `revision_number=1` 未动，旧 pin 兼容保持；升级登记在 deferred ledger |
| O4 | stage envelope 去正文（VF3.r）/ 读时 set digest（VF4.r）/ retry no-op（VF10）/ 进程级 kill（VF27.r）/ checker 执行器（VF42） | `遵守` | 均未假装完成，deferred ledger 有 reopen 触发器 |
| O5 | 全仓 910 用例作为发版闸（VF29 owner-gated） | `遵守` | 未纳入本轮 DoD |
| O6 | reviewer 结论仅作线索的纪律 | `遵守` | 本轮全部承重结论经主审独立复核；子代理断言（含 VF12 降级、VF16/VF19 假修复）均亲读 file:line 采纳 |
| O7 | 误报自查 | `无` | 本轮子代理承重断言经复验无一为误报；第 1 轮 O7（pending 无界追加误报）结论维持 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`changes-requested`——第 1 轮修复主体真实（全部 [true-bug] 硬修复 verified），四通道正向链与声明式路由达到可关闭质量；但通道④失败恢复链死路（R1/R2）构成目标③"错误幂等"承诺的正面断裂，且第 1 轮台账存在 2 项假修复与覆盖声明夸大，不应在本轮关闭。
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. R1：通道④ identity 采纳与信封冻结的时序修复（预解析提前到 `_material` 之前或回调采纳后重算信封），并补"child 失败 → :retry → 收敛"e2e。
  2. R2：定义失败任务 observation 复用语义（同 fingerprint 放行复用原坐标，或显式释放命令），打破"retry 死 + 重提 409"双死锁。
- **可以后续跟进的 non-blocking follow-up**：
  1. R3/R6 两个假修复的纠正（真实 fact_digest / 真实 args 扫描点）——建议与 R1 同批，因都触及台账可信度。
  2. R4/R5/R8/R9/R15 观测面一族（error_message 放行、per-task processes 端点、metrics 四处 emit、supervisor 日志、outbox requeue）——可成一个"可观测 v2"小 AP。
  3. R7（hold 归属化收尾）、R10/R11（投影口径）、R12/R16（发现面端点）、R14（quarantine 清理）、R18（护栏测试）。
  4. R20/R21 登记 alias/接口面 charter。
- **建议的二次审查方式**：`same reviewer rereview`（仅针对 R1/R2 修复 + 两个假修复纠正；观测面一族可 independent reviewer）。
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> 本轮 review 不收口：等待实现者按 §6 响应并修复 R1/R2 后进行 same-reviewer rereview。R1/R2 关闭后，本阶段可按 `approve-with-followups` 收口（其余 follow-up 不阻塞）。

---

## 附录 A：子代理审查分簇与独立性声明

- 本轮共派 4 个对抗性子代理簇（A 修复复核 / B 端到端流程 / C leaf-worker 接口面 / D 可观测运维面），每簇均要求"只写亲证证据、禁止臆测"，全部承重断言（VF16 死代码、VF19 假值、VF12 降级、VF11 残余泄漏、R1/R2 机制、items active、waiting 折叠、namespace 死锁、metrics 零 emit、supervisor 静默、error_message 固定文案、diagnostic 空转）均由主审亲读当前 HEAD 代码逐条复核后才收录。
- 测试证据：主审亲跑 `test_nh1_nh9_review_fixes.py` 7 passed；子代理共复跑 6 组 65+ 用例全绿 + 2 个临时探针（VF1 闭集四组合、VF7 三态、通道④ retry 死路），探针未入库、结论以行为描述收录。
- 独立性声明：本分析仅使用主审自身 reasoning 与本轮/第 1 轮代码事实，未参考 DeepSeek、Grok、Grok 之外的任何模型报告（第 1 轮四份 review 与 VF 台账作为"审查对象/对照真相"使用，其结论仅在被本轮独立复核后采纳）。
