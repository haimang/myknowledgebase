# new-harvest NH1–NH9 第一轮代码审查（by GLM-5.3-Flash）

> 审查对象: `new-harvest NH1–NH9 阶段全部交付（代码 + 测试 + closure + evidence pack）`
> 审查类型: `code-review | closure-review | mixed`
> 审查时间: `2026-08-30`
> 审查人: `GLM-5.3-Flash（独立静态审查，未参考 deepseek / Grok / Gemini / GPT 的任何分析报告；closure 文档本身作为被审对象而非参考结论）`
> 审查范围:
> - `docs/closure/new-harvest/AP-NH1..AP-NH9-*.md`（9 份 closure）
> - `docs/closure/new-harvest/CROSS-NH-campaign.md`
> - `docs/plan/new-harvest/`（9 份原始 action-plan + todo-list）
> - 生产代码：`src/`、`intake/`、`api/`；测试：`tests/`；evidence：`docs/evidence/new-harvest/`
> 对照真相:
> - `docs/eval/new-harvest/final-execution-plan.md`（frozen v1.0，T-O-376..407 / T-R-NH-01..27）
> - 本轮三大目标：① intake 4 通道实际接线；② 声明式 dynamic workflows 实际落地；③ 接线过程竞态与错误幂等机制完善
> 文档状态: `reviewed`

---

## 0. 总结结论

> 一句话 verdict：new-harvest 的三大目标在代码层**实质达成**——4 通道默认组合根真实走通 Process→decode→clean→S04/S06/g0→publish→namespaced retrieval，全部意图经声明式 kind 图路由且无业务入口绕过 workflow engine，幂等与竞态由 DB 约束和谓词式 CAS 兜底且无 fake-green 主证据；但本轮审查发现**一处已独立复算证实的证据漂移（NH2 共享 tail digest 失实）与一处升级阻断风险（kind 图同 revision 原位改写）**，以及 GC 隔离区 crash 窗口无恢复等真实缺口，closure 文档在 4 处对边界的措辞强于代码事实。

- **整体判断**：三大目标交付为真，机制主体扎实；closure 证据层的完整性与措辞诚实度存在系统性但非致命的夸大。
- **结论等级**：`approve-with-followups`
- **是否允许关闭本轮 review**：`yes`（followups 见 §5，其中 R1/R2/R3 建议在下一阶段开工前处理）
- **本轮最关键的 1-3 个判断**：
  1. **NH2 冻结的共享 tail digest 证据已经失实**：当前 live tail digest = `48c39059…fe1b2`，与 AP-NH2 evidence 冻结值 `e36b5bac…af13` 不一致；NH8 提交 `27fc3ca` 修改了 tail 唯一源（新增 `accept_snapshot.rebuild_publication` 路由与 `request_intent_rebuild` guard）。不变量基数 1 仍成立（三图 tail 仍逐字节相等），但"digest fixed"这一四元组证据现在是假的，且无任何测试锚定 live digest。
  2. **kind 图在 `revision_number=1` 下被原位改写**：NH8 对三张 kind 图内容的变更未升 revision，命中 `workflow_registry.py:190-194` 的 `REGISTRY_DIGEST_MISMATCH 503` fail-loud——任何含 pre-NH8 kind 图 revision 的已有部署升级即阻断；compat 列表只含旧 single/profile/scatter 历史 revision，不含旧 kind revision，"old pin 可完结"仅对旧 single-workflow pin 成立。
  3. **GC 隔离区存在无恢复的 crash 窗口**：`object_gc.py` 的 quarantine rename（TX1）与 tombstone CAS（TX2）之间进程崩溃，catalog 行永久 live 而字节永久缺失，且无任何启动/周期对账扫描，九窗具名测试均未覆盖 GC 自身两事务之间的窗口。

---

## 1. 审查方法与已核实事实

- **对照文档**：
  - `docs/eval/new-harvest/final-execution-plan.md`（冻结执行基线，逐条 T-O/T-R-NH 对照）
  - `docs/closure/new-harvest/` 全部 10 份文件 + `docs/plan/new-harvest/AP-NH1..9`、`todo-list.md`
- **核查实现**：
  - 通道与管线：`intake/`（doc/pdf/web/api providers）、`src/runtime/intake/`（acquisition/generation/index_rebuild/clean_preflight 等 26 个模块）、`src/runtime/supply/`
  - 工作流：`src/workflows/`（kind_family/lsrag_definition/lsrag_shared_tail/builtin_scatter 等）、`src/contracts/workflow/models.py`、`src/runtime/workflow/`（runtime_core/materialize/outcome/scatter/outbox/repair/supervisor/dispatch/worker）
  - 持久化：`src/persistence/migrations/`（001..023 全量）、`src/persistence/uow.py`、`factory.py`
  - 服务与 API：`src/services/`（object_upload/object_gc/retrieval/intake_lifecycle/workflow_registry 等）、`api/app.py`、`api/public/routes.py`
- **执行过的验证**：
  - 主审独立重算：`shared_tail_digest(BUILTIN_INLINE_KIND_WORKFLOW)` → `48c39059…`，与 AP-NH2 `queries/compiled-tail-digest.json` 的 `e36b5bac…af13` 比对 → **证实漂移**；`git log -S request_intent_rebuild -- src/workflows/` 定位变更来源 `27fc3ca`
  - 主审亲读：`object_upload.py:100-127`（owner_uuid=stored_object_uuid 共享 hold）、`object_upload_ttl.py:66-78`（cancel 释放对象全部 live hold）、AP-NH3/AP-NH9 `queries/` 目录清点、021 迁移唯一索引
  - 簇C/簇D 子代理实测：NH2/NH3/NH5/NH8 相关测试 10+2+1 passed 全绿；`tests/e2e/test_new_harvest_closed_set.py` 单文件 **21 passed**（exit 0）；CROSS-NH 全量 campaign 命令 **62 collected / 62 passed**（exit 0，约 9-10 分钟，与 closure ~451s 量级一致）；`test_new_harvest_crash_windows.py` 12 passed、`test_nh7_exhausted_zero.py` 4 passed、browser DOM 检索 3 passed（真 firefox）
- **审查组织**：主审构建 4 簇对抗性审查 DAG 并行执行——簇A（状态机制/schema/状态流转）、簇B（intake 4 通道接线）、簇C（dynamic workflows 路由接管）、簇D（竞态幂等 + fake-green/证据真实性）；全部子代理结论仅作为审查输入，**承重 finding 均经主审独立复核后才写入本文**。
- **复用 / 对照的既有审查**：
  - closure 内嵌 review notes（AP-NH7 §3、AP-NH8 §3、AP-NH9 §3）— 作为被审对象的"自认缺口"清单，逐条到代码证伪；本审查**新发现**了这些 notes 未覆盖的问题（R1/R2/R3/R5/R12 等）

### 1.1 已确认的正面事实

- **同 UoW 三项声称全部属实**：route+seal+clean Process 创建同事务（`runtime_outcome.py:51,462-477`）；fact/history/artifact catalog 经同一事务在 CAS 前执行、CAS 失败连带回滚（`runtime_outcome.py:90-99` + `artifacts.py:103-138`）；catalog+upload_pending 同一事务（`object_upload.py:66-136`）。全仓 `src/` 无 persistence 层之外的 commit 调用点（grep 证实）。
- **seal-once CAS 真实防 reseal**：`actual_s05.py:111-128` 谓词 CAS + `runtime_outcome.py:451-460` sealed 分支冲突 + `020` 迁移 trigger 双保险；单写者 `BEGIN IMMEDIATE` 消除 SQLite 侧 TOCTOU（`uow.py:26-50`）。
- **exhausted_zero 与 NOOP→succeeded 彻底切分**：`023` 迁移 + `task_projection.py:51-53`（succeeded 无 proof 且非 exhausted_zero → 拒绝）+ `runtime_outcome.py:587-594`（NOOP 禁止 materialize exhausted_zero）。
- **kind-only 红线成立**：公开 `TaskCreateRequest` 无 `workflow_key`/`action_branch` 字段（`contracts/api/models.py:342-360`），AST 扫描测试禁止复活（`tests/domain/test_nh2_architecture_scan.py:19-29`）；全仓 caller 侧无 `workflow_key=` 传参；选图唯一入口 `workflow_registry.py:79-103`（未知 kind 422 fail-loud）。
- **四通道默认组合根真实接线**：`api/app.py:458-479` 注入 pdf_parser/browser/clean_llm/deterministic_ocr/http_fetcher，discover 失败置 None 并注释"must not turn into a silent observer fallback"；缺供给时 typed 503 而非静默降级；浏览器通道为真 firefox + geckodriver 会话（`browser.py:238-342`，无 `--no-sandbox`，代理指向 port 9 断网）。
- **全部意图经声明式图路由、无绕过**：start-route 优先级 0/1/2/3/10 与 NH8 closure 一致（`runtime_materialize.py:59-64` 按 priority 排序）；`IntakePipeline` 仅在 `api/app.py:460` 构造后交给 WorkflowWorker，services/scripts 无 stage 直调；CONTROL exactly-one 在 runtime 强制（0 或 >1 候选均 integrity fail，`runtime_materialize.py:834-901`）。
- **幂等由 DB 约束兜底而非应用层 check-then-insert**：Task PK + `ux_mkb_tasks_fingerprint` + IntegrityError 回读判 replay/conflict（`task_create.py:79-153`）；upload 同 bytes 由两个部分唯一索引兜底（`014:17-19`、`021`），并发双飞测试断言精确 `[200,201]` + 单 catalog 行。
- **crash 恢复是真实常驻机制**：lifespan 启动 supervisor（`api/app.py:597`），每 tick 末尾必调 `repair_once`（`workflow_supervisor.py:42-62`），含 lease 过期回收（fencing generation+1）、retry 提升、孤儿 ready 重入队、终态投影收敛、歧义态 fail-loud；fanin 测试通过回拨 DB 到 crash 前态、由在跑的生产 supervisor 自愈收敛。
- **closed_set 主文件 PASS 判据是产品终态**：断言走持久层 SQL 直查 + 真实 `/retrieval:search` 响应体；`publication_ready` 是 SQL 衍生（proofs ⋈ active index pointers）而非 mock 标志；`_FailOneScatterChild` 仅存在于测试；monkeypatch 全部限定在测试内；`src/` 无 `_Fail` 类泄漏。
- **schema 与业务代码零列漂移**：程序化交叉比对 23 个迁移合成 schema 与全部 INSERT/UPDATE/SELECT 列（含动态列清单），零缺失；legacy `s05_binding_digest` 在 `src/` 零 truth 读取者；多代检索 fence 完整（`retrieval_rank.py:37-39,70-71`，publish 指针 UPDATE 带 `active_index_generation < ?` 防降级）。
- **closure 的多数诚实披露与仓库现状吻合**：`intake.delete` 二次 409 非 no-op、`.experiment/` gitignored 且 `in_closure_join=false`、S16 无伪造签收、裸 sqlite3 仅残留在未入 campaign 的测试文件。

### 1.2 已确认的负面事实

- **NH2 冻结 tail digest 失实**（主审独立重算证实，见 §0 判断 1 / R1）。
- **kind 图同 revision 原位改写，升级即 503 阻断**（见 §0 判断 2 / R2）；"old pin 可完结"的 compat 叙事只覆盖旧 single-workflow pin。
- **GC quarantine 两事务之间 crash 窗口无恢复、无对账扫描**（见 §0 判断 3 / R3）。
- **"九窗 crash windows" 的证据强度被夸大**：`test_new_harvest_crash_windows.py` 12 个节点中 4 个是对 `test_nh3_seal_crash_windows.py` 两个底层测试的重复包装；W-NH-PROCESS 窗无任何中断注入、W-NH-PUB 是读时 proof fence、W-NH-OUTBOX 是手工置回 pending；真正等价 crash 语义的只有 FANIN 窗（DB 注入 + 生产 supervisor 收敛）与 UoW 原子性窗口。`crash-windows.json` 9 窗只挂 4 个具名 node。
- **同字节并发上传共享单一 upload_pending hold**：hold 的 `owner_uuid=stored_object_uuid`（`object_upload.py:105-119`），021 迁移唯一索引保证每对象一个 live hold，第二个并发上传 `INSERT OR IGNORE` 静默共享；任一方 cancel/TTL 释放**对象全部** live hold（`object_upload_ttl.py:66-78`），另一会话 handle 立即失效，后续 ingest 得 `OBJECT_REFERENCE_REQUIRED` 409。
- **closure 有 4 处措辞强于代码事实**：① registered-api 通道无任何网络获取实现（`exhaustion_proof: Literal["caller_frozen_records.v1"]`，T-O-381 冻结边界，closure 未声明）；② "确定性 OCR" 是封闭 5×7 字形识别器（`glyph_ocr_worker.py:17-108`，36 个 pin 字形，未知字形 typed 失败），真实扫描件不可用；③ LLM-required 格（vision/DU/print、web.llm_rewrite）在默认 Settings 下走确定性 stub 或 typed 503，10+3 矩阵的 verified 依赖测试专用配置；④ AP-NH3 closure 引用的 "three-state query/no-backfill scan" 证据件在其 queries/ 目录中不存在（仅 2 件）。
- **证据链上限**：T11 evidence pack checker 仅做字符串存在性检查（`test_nh9_evidence_pack_checker.py:48-82`），无法识别伪造 PASS；AP-NH9 的 queries/*.json 是手写摘要（`"result": "PASS"` 字符串），显著低于 AP-NH4 的产物级质量；"62 passed" 的真实归属是 CROSS-NH 十文件 campaign 命令，closed_set 主文件本身只有 21 个测试，CROSS-NH-campaign.md 的表述易误读。
- **并发正确性仅在单连接 + `asyncio.Lock` 写锁的 sqlite 系后端验证**（`factory.py:69-97`），从未在多写者/PG 语义下运行；`_is_unique_conflict` 靠错误文本字符串匹配（`task_create.py:29-31`）。
- **`mkb_index_active_pointers.lifecycle_state` 六态枚举中四态（building/validating/ready_candidate/retiring）全仓零写入者**，实际只有 active/withdrawn 两态。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | yes | 全部 finding 均有 file:line；承重项经主审亲读复核 |
| 本地命令 / 测试 | yes | digest 重算、git log -S、pytest 选择性运行（closed_set 21、CROSS campaign 62、NH2/NH3/NH5/NH8 相关全绿） |
| schema / contract 反向校验 | yes | 子代理程序化比对 23 迁移 × 全部 SQL 列；主审复核 021 唯一索引 |
| live / deploy / preview 证据 | no | 本轮为静态审查 + 本机测试；owner live soak 未观察（closure 亦未宣称） |
| 与上游 design / QNA 对账 | yes | T-O-376..407 逐条对照代码行为 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | 共享 tail digest 与 NH2 冻结证据漂移且无测试锚定 | high | protocol-drift | no（不阻断功能） | 立即 |
| R2 | kind 图 revision_number=1 原位改写，升级阻断且旧 kind pin 无 compat | high | delivery-gap | no | 下一阶段前 |
| R3 | GC 隔离区两事务之间 crash 窗口无恢复 | high | correctness | no | 下一阶段前 |
| R4 | "九窗 crash windows" 证据强度夸大 | high | docs-gap | no | 立即（措辞降级） |
| R5 | 同字节并发上传共享单一 pending hold，cancel/TTL 误伤并发会话 | medium | correctness | no | followup |
| R6 | registered-api 通道无网络获取为冻结边界，closure 未声明 | medium | docs-gap | no | 文档 |
| R7 | 确定性 OCR 为封闭 5×7 字形集，真实扫描件不可用 | medium | delivery-gap | no | 披露/owner gate |
| R8 | LLM-required 格默认部署不可用，10+3 verified 依赖测试配置 | medium | docs-gap | no | 文档 |
| R9 | T11 evidence checker 仅字符串校验，无法识别伪造 PASS | medium | evidence-gap | no | followup |
| R10 | AP-NH9 证据查询件为手写摘要，不可独立复核 | medium | evidence-gap | no | followup |
| R11 | 并发语义仅在单写锁 sqlite 验证；unique 冲突靠文本匹配 | medium | test-gap | no | 披露+加固 |
| R12 | lifecycle_state 六态枚举四态无写入者 | medium | state-gap | no | followup |
| R13 | full_task retry 源漂移以 seal conflict 深处暴露 | low | state-gap | no | followup |
| R14 | alias/actual 兜底写入与"alias 非承载 actual"承诺矛盾 | low | correctness | no | followup |
| R15 | metadata no_change 双实现判定 | low | correctness | no | followup |
| R16 | declared-reacquire 强制依赖可选 reader 注入，引擎级 fail-open 缝 | low | correctness | no | followup |
| R17 | local-object 图 media 守卫缺省兜底 decode_text | low | correctness | no | followup |
| R18 | clean evidence producer 标签不区分真模型与 fixture 端点 | low | test-gap | no | followup |
| R19 | 生产构造器内建 fault hook；INSERT OR IGNORE 吞掉全部约束冲突 | low | correctness | no | followup |
| R20 | 后台扫描器（upload-lifecycle/GC）静默吞异常 | low | correctness | no | followup |
| R21 | 文档卫生：CROSS ⛔ 披露过期、"62 passed" 归属、NH3 query 件缺失 | low | docs-gap | no | 文档 |
| R22 | inline 内容在 Team 校验前落盘 | low | correctness | no | 可接受 |
| R23 | missing_supply 测试双分支宽容，路径不钉死 | low | test-gap | no | followup |

### R1. 共享 tail digest 与 NH2 冻结证据漂移且无测试锚定

- **严重级别**：high
- **类型**：protocol-drift
- **是否 blocker**：no（不变量基数 1 仍成立，功能未破坏；破坏的是证据链）
- **事实依据**：
  - 主审独立重算：`shared_tail_digest(BUILTIN_INLINE_KIND_WORKFLOW)` = `48c390595f603617cc0923f649e67d9dd0a1cf61a7636f8029dc16fd551fe1b2`，而 `docs/evidence/new-harvest/AP-NH2/queries/compiled-tail-digest.json:2` 冻结值为 `e36b5bac…af13`；三个 kind 图 compiled digest 同步全部改变
  - 变更来源：NH8 提交 `27fc3ca` 修改 tail 唯一源 `BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW`（`git log -S request_intent_rebuild -- src/workflows/` 唯一命中）
  - `tests/domain/test_nh2_architecture_scan.py:51` 只断言 `len(digests)==1`，tail 内容再变也测不出来
- **为什么重要**：NH2 hard-gate"one shared tail digest fixed"的四元组证据（commit+query+digest）现在失实；NH7/NH8 closure 均引用该证据。下游与审计若以冻结 digest 为锚做 diff，会得出"实现漂移"的错误结论，或反过来掩盖真实变更。
- **审查判断**：这不是 fake-green（运行时行为正确、基数不变量真实），而是**证据生命周期管理缺陷**——冻结证据没有随图演进刷新，也没有 live-side 测试钉住真值。
- **建议修法**：加一个断言常量 live digest 的测试（或 digest 变更即失败的 canary）；刷新 AP-NH2 evidence 并附 NH8 变更说明；closure 补 drift 备注。

### R2. kind 图 revision_number=1 原位改写，升级阻断且旧 kind pin 无 compat

- **严重级别**：high
- **类型**：delivery-gap
- **是否 blocker**：no（fail-closed 方向安全，但与 compat 叙事不符）
- **事实依据**：
  - `src/workflows/kind_family.py:242` 固定 `revision_number=1`，而图内容在 NH8 被改写（主审重算 digest 已变）
  - `src/services/workflow_registry.py:190-194`：同号 revision 指纹不一致 → `REGISTRY_DIGEST_MISMATCH 503`，bootstrap 即失败；同文件 `:179-191` 自己声明"只能新增不可变 revision"
  - `builtin_lsrag.py:48-52` 的 `BUILTIN_EXECUTION_COMPATIBILITY_WORKFLOWS` 只含旧 single/profile/scatter 历史 revision，**不含任何旧 kind revision**；pre-NH8 kind digest 的 in-flight Execution 在 `runtime_core.py:622-628` 找不到 plan → 503
- **为什么重要**：NH8/NH9 closure 宣称"old pin 可完结"（T08 ✅），实测只对旧 single-workflow pin 成立；NH2→NH8 之间创建的 kind Task 在新代码下无法完结。fail-closed 本身安全，但"回滚靠手工重注 compatibility definitions"（M-NH-09 注）不是生产化 compat，且已有部署的升级路径被静默阻断。
- **审查判断**：交付完整性缺口。campaign 在"closed-set/单机"语境下可辩护（in-flight=0 时无影响），但该前提未写成 owner gate。
- **建议修法**：图演进必须升 `revision_number` 并把旧 revision 加入 compat 注册；或显式记录"kind 图升级要求 in-flight=0"的 owner gate 与回滚程序。

### R3. GC 隔离区两事务之间 crash 窗口无恢复

- **严重级别**：high
- **类型**：correctness
- **是否 blocker**：no
- **事实依据**：
  - `src/services/object_gc.py:225-235`（rename 到 quarantine/，TX1）与 `:236-295`（复查 + tombstone CAS，TX2）为两个独立事务
  - restore 仅在同进程失败路径执行（`object_gc.py:285-293,306-309`）；`local_store.py:186-219` 只提供显式 restore
  - 全仓无任何启动/周期扫描对"catalog live 但字节在 quarantine/"对账（`api/app.py:597-621` 的四个后台循环均无此职责）；crash 后下次 GC 扫描因源文件缺失得 `MISSING_BYTES`（`object_gc.py:227`），不会 restore
  - 对照：PROM-CAT 窗的 staging reap 有 `object_upload_lifecycle.scan_once()` 兜底（`test_new_harvest_crash_windows.py:428-433`），GC quarantine 无等价物
- **为什么重要**：该窗口内 crash 导致 verified readers 永久 404 且无自愈——这是全链路中唯一发现的"数据不可用且不可恢复"窗口，与 NH9 的 crash-assurance 主张直接相关。
- **审查判断**：真实缺口，非文档问题。概率低（窗口窄）但后果是静默永久丢失可用性。
- **建议修法**：GC 扫描开头加 quarantine 对账（按 catalog 状态决定 restore/重做），或改为"先 TX 标记后物理删"的墓碑优先协议 + 补偿扫描。

### R4. "九窗 crash windows" 证据强度夸大

- **严重级别**：high
- **类型**：docs-gap
- **是否 blocker**：no
- **事实依据**：
  - `test_new_harvest_crash_windows.py:226-244`：4 个"独立节点"实为对 `test_nh3_seal_crash_windows.py` 两个底层测试的重复调用
  - W-NH-PROCESS（`:160-223`）无任何中断注入，只是 CAS effect-once/冲突断言；W-NH-PUB（`:251-323`）是读时 proof fence；W-NH-OUTBOX（`:326-387`）是手工置回 pending 后投递
  - "crash"多为测试内 fault hook 抛异常验证 UoW rollback（`test_nh3_seal_crash_windows.py:166-173`），非进程中断后重启收敛；真正 crash 语义的只有 FANIN 窗（`test_nh1_fanin_recovery_port.py:35-61`，DB 注入 + 生产 supervisor 收敛）
  - `docs/evidence/new-harvest/AP-NH9/queries/crash-windows.json`：9 窗只挂 4 个 node 名
- **为什么重要**：closure hard-gate 写"九窗 deterministic ✅"，若下游理解为"进程中断后系统可恢复"，是失实的安全假设。
- **审查判断**：机制本身（rollback/原子性/幂等投递）真实且已验证，但"crash window"标签名不符实。
- **建议修法**：为 CREATE/PROCESS/PROM-CAT 各补"中断后以新 app 实例继续"的测试；把 `crash-windows.json` 与 closure 措辞降级为 "rollback/atomicity windows"，或补齐 9 窗→node 映射。

### R5. 同字节并发上传共享单一 pending hold，cancel/TTL 误伤并发会话

- **严重级别**：medium
- **类型**：correctness
- **是否 blocker**：no
- **事实依据**：
  - `object_upload.py:105-119`：pending hold 的 `owner_uuid = stored_object_uuid`（对象自身），主审亲读确认；`021_nh4_upload_pending.sql:46-48` 唯一索引 `(team, stored_object, owner_kind, owner_uuid) WHERE purpose='upload_pending' AND released_at IS NULL` —— 每对象仅一个 live hold
  - `object_upload_ttl.py:66-78`：cancel 释放该对象**全部** live hold，TTL scan 同理
  - 并发同 bytes 上传因 identity=Team+SHA256+size 必然共享对象；A cancel / TTL 到期 → B 的 handle 变 expired（`object_upload.py:149-163`），B ingest 得 `OBJECT_REFERENCE_REQUIRED` 409（`acquisition_ingest.py:706-733`）
- **为什么重要**：NH4 race 测试只证"one 201 one 200 one live row"，未覆盖 cancel/TTL 对并发会话的误伤窗口；后果是静默可用性丢失。（注：审查中一子代理曾主张"重复上传无界追加 pending 行"，经主审对照 021 唯一索引证伪——live 行受唯一约束；行累积只发生在 release 后的跨会话历史，属轻微存储增长，不构成缺陷。）
- **审查判断**：低概率真实缺陷。
- **建议修法**：hold 的 `owner_uuid` 改为每次上传会话 UUID（唯一索引天然容纳多 hold），cancel/TTL 只释放自己的 hold。

### R6. registered-api 通道无网络获取为冻结边界，closure 未声明

- **严重级别**：medium
- **类型**：docs-gap
- **是否 blocker**：no
- **事实依据**：`intake/api/providers/` 三文件均为纯 parser/mapper（无 HTTP 客户端）；acquire 仅冻结 `descriptor["records"]`（`acquisition_ingest.py:283-486`）；`exhaustion_proof: Literal["caller_frozen_records.v1"]`。T-O-381 冻结裁定 live fetch 不纳入——代码合规，但 NH7 closure "3 个 registered-api operation 接到 default-root live-to-retrieval" 的行文易被读成已有 API connector。
- **审查判断**：四通道中最弱一环，且弱在**语义边界披露**而非实现错误。
- **建议修法**：closure/README 显式声明"registered_api v1 = caller-frozen records 契约通道，无供应商客户端"，并给出 connector 的 reopen 条件。

### R7. 确定性 OCR 为封闭 5×7 字形集，真实扫描件不可用

- **严重级别**：medium
- **类型**：delivery-gap
- **是否 blocker**：no
- **事实依据**：`glyph_ocr_worker.py:17-108` 只匹配 36 个 pin 的 5×7 字形位图，未知字形 → worker exit 2 → `OCR_INPUT_INVALID` 422；NH7 OCR 格输入全部是 `render_fixture_pdf/png` 生成的字形 fixture。模块 docstring 有诚实披露，但 closure 将 `pdf.ocr`/`doc.ocr` 判 ✅ verified。
- **审查判断**：T-O-376 的"真实 Process→可检索"在**闭集 fixture 语义**下成立，在通用 OCR 语义下不成立；这是边界的披露缺口，与 T-O-378"不得冒充完成"的诚实精神存在张力。
- **建议修法**：closure 披露 closed-glyph 边界；通用 OCR 引擎列为 A 类 owner-gate reopen。

### R8. LLM-required 格默认部署不可用，10+3 verified 依赖测试配置

- **严重级别**：medium
- **类型**：docs-gap
- **是否 blocker**：no
- **事实依据**：默认 `ns1_cli_mode="stub"`（`config.py:46`）→ web.llm_rewrite/DU 的 clean 文本由 `DeterministicNs1Stub` 确定性生成（`claude_cli.py:522-573`）；默认 `multimodal_enabled=False`（`config.py:49`）→ vision/print/DU 在 clean 阶段 typed 503（`CLEAN_VISION_CAPABILITY_UNAVAILABLE` 等）；NH7 known gap 只承认了 web.llm_rewrite 一格。
- **审查判断**：fail-closed 行为正确、无假绿（typed 503 不冒充成功），但"10+3 矩阵 verified"依赖测试专用 Settings 的事实未完整披露。
- **建议修法**：closure 增加"各策略默认部署可用性矩阵"；提供含 `runtime_supply_readiness_required=true` + multimodal endpoint 的生产 profile 样例（当前 repo 无固化样例，且默认 readiness 探针不含 supply 五项，/ready=200 ≠ 四通道可跑）。

### R9. T11 evidence checker 仅字符串校验，无法识别伪造 PASS

- **严重级别**：medium
- **类型**：evidence-gap
- **是否 blocker**：no
- **事实依据**：`test_nh9_evidence_pack_checker.py:48`（`assert "PASS" in tests`）、`:53-82`（test_id/commit/UTC/FG 均为字符串包含检查）；queries/*.json 无 schema/计数校验。
- **为什么重要**：九包四元组的"已执行"声明最终依赖手写 tests.txt 与人的诚实——这是结构性上限，closure 未明说。本轮实测（62/62 复跑通过）表明当前未伪造，但机制不防未来。
- **建议修法**：checker 升级为重放式：至少对 manifest digest 类字段现场重算（`test_nh9_closed_set_manifest.py:23-32` 已示范），逐步推广到 evidence 摘要。

### R10. AP-NH9 证据查询件为手写摘要，不可独立复核

- **严重级别**：medium
- **类型**：evidence-gap
- **是否 blocker**：no
- **事实依据**：`closed-set-digest.json` 纯计数、`crash-windows.json` 9 窗仅 4 node 名、`mega-cells.json`/`negative-zero-hits.json` 是 `"result": "PASS"` 类字符串；对照 AP-NH4 `public-upload.json` 含真实 content_digest/size/counts/来源测试节点。AP-NH3 closure 引用的 three-state query 件在其 queries/ 中也不存在（主审清点仅 2 件）。
- **审查判断**：capstone 阶段证据质量反而低于中期阶段，四元组纪律在收尾时松了。
- **建议修法**：按 NH4 格式补 raw 字段；补 NH3 缺失的 query 件。

### R11. 并发语义仅在单写锁 sqlite 验证；unique 冲突靠文本匹配

- **严重级别**：medium
- **类型**：test-gap
- **是否 blocker**：no
- **事实依据**：`factory.py:69-97` TursoPersistence 单连接 + `asyncio.Lock` 写锁；并发测试均经同一 TestClient portal 双线程；`task_create.py:29-31` `_is_unique_conflict` 以 `"unique"/"constraint"` 文本匹配判定。
- **为什么重要**：全部 CAS 是谓词式（可移植性好），但"并发正确性"的实际保证范围是单写者模型；换多写者后端时 IntegrityError 判定可能失效。closure 未披露该边界。
- **建议修法**：披露"单写锁 sqlite 系验证"边界；`_is_unique_conflict` 改为异常类型 + 驱动错误码判定。

### R12. lifecycle_state 六态枚举四态无写入者

- **严重级别**：medium
- **类型**：state-gap
- **是否 blocker**：no
- **事实依据**：`001_initial.sql:1584-1586` 枚举 building/validating/ready_candidate/active/retiring/withdrawn；全仓唯一写入点是 `vector_publish_commit.py:134,146` 与 `index_rebuild_commit.py:106`（均 `'active'`）、`lifecycle_apply.py:125`（`'withdrawn'`）；旧代失效实际靠检索 JOIN 代数 fence + cleanup intents 实现。
- **为什么重要**：schema 宣告的指针状态机在代码里不存在；按这些态写的运维查询/告警永远空集。
- **建议修法**：收紧 CHECK 枚举到实际两态，或补齐 retiring 推进写入。

### R13–R23（低级别，逐条简述）

- **R13**（low/state-gap）：full_task retry 复制上一代 sealed actual（`task_commands.py:300-315`，符合 T-O-401 exact 法律），但 acquire 产出漂移时以 `ACTUAL_S05_SEAL_CONFLICT`（`runtime_outcome.py:451-460`）在深处暴露，根因"源已变化"难归因；复制的 `seal_generation=1` 使新代 seal 不过 CAS 路径。建议 admission 前置 `RETRY_SOURCE_DRIFT` 专用错误码。
- **R14**（low/correctness）：`clean_preflight.py:402,509`、`scatter_intake.py:611` 附近 `policy_binding_digest or binding_digest` 兜底可把 actual 写进 legacy alias 列（现实中不可达——policy 恒为 NOT NULL domain digest），但与"alias 永远是 policy 值"承诺矛盾，应删兜底。
- **R15**（low/correctness）：metadata no_change 判定双实现——admission 期 value_digest（`intake_lifecycle/targets.py:60-77`）与执行期 fingerprint 重算（`acquisition_intents.py:172-178`），两层分歧时 no_change 步可能执行 changed 全路径仍 SUCCEEDED 终结；建议以冻结 disposition 为单一权威。
- **R16**（low/correctness）：declared-reacquire 强制仅在 context 含 `media_family=text && main_text_presence=absent` 时生效（`runtime_materialize.py:65-83`），`representation_facts` 是可选注入（`runtime_core.py:67,91`）——无 reader 实例化时检查整体跳过；生产装配已注入（`api/app.py:441`），属引擎级 fail-open 缝，建议 kind 图把 reader 设为必选。
- **R17**（low/correctness）：local-object 图 media 守卫（p0 pdf/p1 image）缺省时 p10 无守卫兜底 `decode_text`（`kind_family.py:401-403`），对 PDF 可能先选错 decode 能力再靠下游报错；建议加显式 media 终点或稳定 422。
- **R18**（low/test-gap）：clean evidence producer 标签 `s11.multimodal`/`s11.text_generate` 不区分真实 vLLM 与本地 fixture 端点（`intake/pdf/__init__.py`、`intake/doc/__init__.py`），审计链无法从 artifact 判断 clean 是否真实模型产出；建议纳入 endpoint 指纹。
- **R19**（low/correctness）：`object_upload.py:41,174-179` 生产构造器内建 `uow_fault_hook`；两处 `INSERT OR IGNORE`（`:80-92,105-119`）会静默吞掉 FK/NOT NULL 冲突，靠 re-select 转 503 兜底。建议无唯一索引兜底处改普通 INSERT，hook 文档化。
- **R20**（low/correctness）：`runtime/object_upload.py:42-43`、`runtime/object_gc.py:50-57` 后台扫描 `except Exception: pass` 无日志无指标（对照 supervisor 有 last_error/consecutive_failures）；建议至少递增 metrics。
- **R21**（low/docs-gap）：① CROSS review 残留 "`test_registered_api_scatter.py` remains ⛔"，该文件现无 sqlite3 import（真正的裸 sqlite3 残留在 `test_inline_ingress_staging.py:8,105`），披露漂移削弱其余披露可信度；② CROSS-NH-campaign.md "62 passed" 未附命令，真实归属是十文件 campaign（closed_set 单文件 21 个测试）；③ AP-NH3 three-state query 件缺失（并入 R10）。
- **R22**（low/correctness）：inline bytes 在 Team active 校验前落盘（`config_snapshots.py:148` 先于 `task_create.py:101-109`），无效 Team 可制造 orphan bytes（有 cap 与 24h GC grace 兜底）；可接受，如收紧可加轻量预检。
- **R23**（low/test-gap）：`test_new_harvest_closed_set.py:344-354` missing_supply 格 201-then-fail 与 422/503 双分支均可 PASS——非 fake-green，但路径不钉死，建议固定单一分支。

---

## 3. In-Scope 逐项对齐审核

> 对照对象：9 份 AP closure 的 hard-gate claim + 本轮三大目标。结论统一使用 `done | partial | missing | stale | out-of-scope-by-design`。

| 编号 | 计划项 / closure claim | 审查结论 | 说明 |
|------|------------------------|----------|------|
| S1 | NH1 foundation contracts / proof baseline / GO | `done` | harness、CONTROL/S05 spike 生产化路径、分母与法律矩阵均被后续 AP 实际消费；无残留 spike 双 SSOT |
| S2 | NH2 kind family + selected-output + old-pin compat | `partial` | 机制 done（kind-only、exactly-one、共享尾基数 1 均实况成立）；但 tail digest 冻结证据失实（R1）、kind 图同 revision 原位改写违背自身不可变法律（R2） |
| S3 | NH3 representation history + actual S05 分账/seal/replay | `done` | 同 UoW、seal-once CAS、三态分账、alias 零 truth 读者、传播链全部独立核实；仅 closure 引用的 query 件缺失（R10/R21） |
| S4 | NH4 public upload + object lifecycle + GC | `partial` | upload 幂等/handoff/UoW done；GC quarantine crash 窗口无恢复（R3）、并发同 bytes 共享 hold（R5）为真实缺口 |
| S5 | NH5 semantic ledger + S06 + SQL facets | `done` | 六元组权威、unknown 拒收、channel 分名、facet 前置于 LIMIT、T08-B 红灯如实保留并被 NH8 归零 |
| S6 | NH6 local runtime supply + security | `done` | 真 firefox/真 pdftotext 隔离子进程、readiness 正负、SBOM、default wiring 均实况成立；OCR 封闭字形边界未披露（R7）、默认 profile 可用性矩阵缺失（R8） |
| S7 | NH7 10+3 clean capability activation | `partial` | 通道级 live-to-retrieval 实测全绿、无 monkeypatch；但 registered-api 冻结边界（R6）、OCR 闭集（R7）、LLM 格依赖测试配置（R8）三处 verified 的语义弱于行文 |
| S8 | NH8 七意图 / exact-clean / lifecycle query / old-pin | `partial` | 意图路由、exact-clean 旁路、query law、T08-B 归零全部实况成立；old-pin compat 叙事窄于实际（R2）、tail 源变更未升 revision（R1） |
| S9 | NH9 closed-set / crash / race / compat / security mega | `partial` | closed_set 判据为产品终态、campaign 62/62 复跑通过、无 fake-green 主证据；但"九窗"证据强度夸大（R4）、GC 窗口缺口（R3）、证据包质量为手写摘要（R10）、checker 仅字符串（R9） |
| S10 | 目标①：intake 4 通道实际接线 | `done` | 四通道 default-root 无 patch 全链路真实（含实测命中）；语义边界（registered-api 无 fetcher、OCR 闭集、LLM 格配置可达）需按 R6-R8 披露 |
| S11 | 目标②：声明式 dynamic workflows 实际落地 | `done` | 三 kind 图 + scatter 覆盖四通道，全部意图经图路由，无业务入口绕过；守卫/CONTROL/环检测/兼容 fail-loud 在 runtime 强制；证据卫生见 R1/R2 |
| S12 | 目标③：竞态与错误幂等机制完善 | `partial` | 幂等键 DB 兜底、谓词式 CAS、常驻 supervisor repair、crash 恢复真实存在；剩余两个真实缺口（R3 GC 窗口、R5 共享 hold）+ sqlite 单写者边界未披露（R11） |

### 3.1 对齐结论

- **done**: 6　**partial**: 6　**missing**: 0　**stale**: 0　**out-of-scope-by-design**: 0

> 总结：这更像"三大目标的核心功能全部落地且可复跑验证，但证据层与边界披露未跟上实现演进"，而不是未交付。所有 partial 均由可指名的高/中级别 finding 承载，不存在笼统的"未完成"。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | raw GET / list / presign 公开读为零 | `遵守` | route/source 扫描零命中，子代理独立复核 |
| O2 | 第五 kind / existing-object upgrade / experiment 发车 | `遵守` | upgrade 入口=0（T-O-401/O-NH-03）；`.experiment` gitignored 且 `in_closure_join=false`；caller 无 workflow_key/action_branch 的红线有 AST 测试兜底 |
| O3 | S16 browser egress 签收 | `遵守`（未伪造） | 签收栏存在且未预填签名；closure 如实标 deferred，CROSS join 未把 S16 计入 DoD |
| O4 | 通用 workflow 引擎扩张 / free expression / JOIN 扩张 | `遵守` | 守卫 eq-only、无 eval/表达式面（AST 测试）；JOIN DSL 全量声明但零使用，fan-in 由 scatter CONTROL + accepted-denominator 实现 |
| O5 | cloud OCR / CF Browser Rendering / `--no-sandbox` / GPL 链入主进程 | `遵守` | OCR/browser 为本地隔离 subprocess；argv 扫描无 `--no-sandbox`；poppler 走 subprocess 不链入主进程 |
| O6 | 旧 single/profile/scatter 历史 revision compat | `遵守` | compat 列表存在且 old single pin 可完结——但注意 R2：kind 图旧 revision 不在此列，closure 未声明该边界 |
| O7 | 误报风险 | 已排除 | 本轮曾出现一例子代理误报（R5 相关"pending 行无界增长"），经主审对照 021 部分唯一索引证伪，未计入 finding |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`approve-with-followups` —— new-harvest NH1–NH9 的三大目标（4 通道接线、dynamic workflows 落地接管路由、竞态/幂等机制）在代码与测试层实质完成，未发现 fake-green 主证据；closure 总体可信但存在一处已证实的证据失实（R1）、一处升级路径风险（R2）、一处真实恢复缺口（R3）和系统性的一档措辞夸大（R4/R6/R7/R8）。
- **是否允许关闭本轮 review**：`yes`
- **关闭前必须完成的 blocker**：无（本轮无 critical 级 finding，无 fake-green，无功能未交付）
- **建议在下一阶段开工前完成的 follow-up（按优先级）**：
  1. R1：锚定 live tail digest 的 canary 测试 + 刷新 AP-NH2 evidence + closure drift 备注
  2. R2：kind 图演进升 revision 并纳入 compat，或写成 in-flight=0 的 owner gate
  3. R3：GC quarantine 对账/补偿扫描，补"crash 后新实例收敛"测试
  4. R4+R6+R7+R8：closure 措辞降级与边界披露（crash windows、registered-api、OCR 闭集、LLM 格默认可用性矩阵）
- **可以后续跟进的 non-blocking follow-up**：R5、R9、R10、R11、R12 及 R13–R23（见 §2.1 建议处理列）
- **建议的二次审查方式**：`same reviewer rereview`（针对 R1-R4 修复后逐条复核即可，无需全量重审）
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

---

### 附：本轮审查独立性声明

本审查由 GLM-5.3-Flash 独立完成：审查基线仅使用仓库内的冻结执行基线（final-execution-plan）、原始 action-plan、closure 与代码/测试本体；未参考、未采纳 deepseek、Grok、Gemini 或 GPT 的任何既有分析报告（closure 文档署名的 Codex/Grok 为被审对象本身）。4 个对抗性审查子代理（状态机制/schema、4 通道接线、dynamic workflows、竞态幂等+证据真实性）的结论仅作为输入线索，全部承重 finding（R1、R2、R3、R5、R10/R21 相关）均经主审以 digest 重算、代码亲读、目录清点、选择性测试复跑等方式独立复核后收录；一例子代理误报经复核后排除（见 §4 O7）。
