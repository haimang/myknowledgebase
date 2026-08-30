# Nano-Agent 代码审查报告

> 审查对象: `new-harvest NH1–NH9 九阶段总收口（三目标：intake 4 通道接线 / dynamic workflows 落地 / 竞态与错误幂等机制）`
> 审查类型: `closure-review + code-review + mixed`
> 审查时间: `2026-08-30`
> 审查人: `v4f（deepseek-v4-flash，独立第一轮审查）`
> 审查范围:
> - `docs/closure/new-harvest/CROSS-NH-campaign.md` + 9× `AP-NH1..NH9` closure
> - `docs/evidence/new-harvest/AP-NH1..9/`（manifest / tests.txt / queries / migrations / security / closure.md）
> - `src/`（runtime/intake、runtime/workflow、runtime/task、runtime/binding、workflows、contracts、services、storage）+ `intake/` + `api/` + `tests/`（NH 系列单元/e2e/domain）
> 对照真相:
> - `docs/eval/new-harvest/final-execution-plan.md`（T-O-376..407 / T-R-NH-01..27 / 9 AP 四台账 / capstone A–J / DoD）
> - `docs/plan/new-harvest/AP-NH1..9`（原始 action-plan 台账 A/B/C/D）
> - git 历史 `1221aa1..HEAD`（33 个 NH 提交）
> 文档状态: `reviewed`（结论：主体成立 + 明确 follow-ups，未推翻 nine-AP closed）

---

## 0. 总结结论

> **一句话 verdict**：NH1–NH9 的三目标"4 通道接线 / dynamic workflows 落地 / 竞态幂等"主体全部真实落地、可复现，未发现系统性假绿或"diff 只有测试没有生产代码"的欺诈闭环；但存在 1 处跨 4 份 closure 传播的失实陈述、1 处战役体量最大的 under-delivery（模型依赖格以 stub/fixture 顶替"live"）、1 处违反 fail-loud 的状态写漏洞，以及崩溃窗/幂等覆盖的"诚实但不完备"粒度问题——当前状态更像 `approve-with-followups`，而不是 `blocked`。

- **整体判断**：`三目标中两项（4 通道接线、workflows 接管）成立且证据可复验；第三项（竞态/错误幂等）机制层真实但覆盖不完备（partial），crash 注入深度低于台账描述。`
- **结论等级**：`approve-with-followups`
- **是否允许关闭本轮 review**：`yes`（本轮审查发现已完整归档；CROSS-NH 的最终 closed 需在下列 follow-up 落账后达成）
- **本轮最关键的 1-3 个判断**：
  1. `"HEAD scatter 文件仍含 sqlite3 段"在 NH7/NH8/NH9/CROSS-NH 四份文档中反复出现，但经 git 核验（HEAD 与 6256a97 两个版本）该文件早已 Port 化，仅剩 database_path 文件名串——这是跨 closure 的失实陈述传播，说明 closure 的 evidence 互引缺乏重新核验。`
  2. `NH7 的"10+3 live-to-retrieval"中模型依赖格（web.llm_rewrite / pdf.doc.llm / doc.vision / OCR）在 default-root 由 DeterministicNs1Stub 恒等回显与本地 fixture 顶替（claude_cli.py:522/565），真实模型端点从未出场——战役最大体量 partial，虽已披露但未在证据中显式降档标注。`
  3. `幂等机制的真实性成立（Outcome CAS / seal CAS / task create 唯一约束 / outbox 无副作用消费者 / GC TX1→TX2 recheck 全部为真 effect-once），但九窗注入全部为同进程函数级 hook，零进程级 kill+lease-recovery 验证，且 W-NH-PUB 只验证"事后篡改被 fence 挡住"而非"切中崩溃无双重 serving"——属于 assurance 力度不足，非假证。`

---

## 1. 审查方法与已核实事实

- **对照文档**：
  - `docs/eval/new-harvest/final-execution-plan.md`（冻结 Truth、9 AP 台账、DAG、capstone、DoD）
  - `docs/plan/new-harvest/AP-NH1..9`（台账 A/B/C/D 与 DoD 硬闸）
  - `docs/closure/new-harvest/AP-NH1..9 + CROSS-NH-campaign.md`
  - `docs/evidence/new-harvest/AP-NH1..9/`（manifest.json / tests.txt / queries / migrations / security）
- **核查实现**：
  - `src/workflows/kind_family.py`（三张 kind 图 + selected_output CONTROL + guard/route）
  - `src/runtime/workflow/runtime_materialize.py / runtime_outcome.py / runtime_core.py / runtime_scatter.py / runtime_outbox.py / selected_output.py / dispatch.py`
  - `src/runtime/intake/`（acquisition_ingest / clean_preflight / acquisition_intents / generation_* / vector_publish_commit / representation_history）
  - `src/runtime/task/task_create.py / task_commands.py / task_projection*.py`；`src/runtime/binding/actual_s05.py`
  - `src/runtime/inference/claude_cli.py`；`src/runtime/supply/`；`src/services/`（workflow_registry / config_snapshots / object_gc / retrieval）
  - `intake/`（web/api/pdf/doc 四通道 + dispatch_clean 9 capability）；`api/public/routes.py`
  - `src/persistence/migrations/001..023`（M-NH-01..09 ∩ 018/019/020/021/023）
  - `tests/`（NH1–NH9 的 unit / e2e / domain，含 `test_new_harvest_closed_set.py / crash_windows.py / runtime_security.py`）
- **执行过的验证**（本审查人直接执行）：
  - `git log --oneline 1221aa1..HEAD`（33 个 NH 提交，时间线 08-29→08-30）
  - `git grep -n sqlite3 6256a97 -- tests/e2e/test_registered_api_scatter.py` 与 HEAD 版本：**均只有 `database_path=tmp_path/"mkb.sqlite3"` 一行文件名，无 import sqlite3 / sqlite3.connect**（复核子代理 B/E 结论）
  - `claude_cli.py:522-573`：`DeterministicNs1Stub` 存在，非 json 角色直接 `return ClaudeCliResult(request.user_prompt.strip(), ...)` —— **恒等回显确认**
  - `runtime_materialize.py:65-85`：reacquire 法律 `intake.ingest.kind.*` 全图生效且 text+absent 无 reacquire 边即 409 `workflow-reacquire-edge-undeclared` —— **全局化确认（非仅 http 图）**
  - `runtime_outcome.py:501-519`：`_fail_process_tx` UPDATE 后无 rowcount 检查；`runtime_outcome.py:697-703`：非 exhausted_zero 的 SUCCEEDED 一律计 `indexed_success` —— **确认**
- **子代理执行**（本会话委派 5 个对抗性 sub-agent，均重新读取文档 + 代码 + 实测测试）：
  - SA-A 状态机制/schema/状态流转：重跑 8 组核心套件 79 项全绿
  - SA-B intake 4 通道接线：逐通道重走 acquire→clean→publish→query 证据链
  - SA-C workflows 路由接管：重跑 resolver/guard/compiler/compat 套件
  - SA-D 竞态/崩溃/幂等：重跑 crash_windows / seal_crash / identity / GC 交错套件
  - SA-E 交付完整性：`uv run pytest -q --tb=no`（约 2h15m）**910 collected → 910 passed**，并逐 commit `git show --stat` 核对实现体量
- **复用 / 对照的既有审查**：无。本报告不采纳、不引用 `docs/code-review/` 下任何既有分析（0820-review / baseline-dev / new-start）；所有结论来自本轮独立阅读 + 上述实测，仅一处以 git 证据复核子代理对账结论。

### 1.1 已确认的正面事实

- **三层状态机枚举闭合**：TaskStatus/ExecutionStatus/ProcessStatus 三枚举定义于 `src/contracts/common/models.py:47-75`，terminate/回收路径一致；`project_task_status_tx` 对迁入迁出白名单。
- **exhausted_zero 真独立**：`migrations/023_nh7_result_disposition.sql:5-7` 独立列 + proof 豁免仅限该 disposition（task_projection.py:53；runtime_outcome.py:579）；scatter 零成员 SUCCESS+exhausted_zero 强制 durable proof（runtime_scatter.py:76-99）；metrics 独立 label；NOOP 组合被显式拒绝（runtime_outcome.py:587-594）。
- **seal 是唯一线性点且同 UoW**：全仓对 actual 列的写仅 `seal_actual_binding_tx` 一处（actual_s05.py:112-128）；CAS `WHERE actual_binding_state='unsealed' AND ... AND seal_generation=0`；W-SEL/W-SEAL 钩子在同一 tx 内（runtime_outcome.py:443-473）；`test_mid_uow_crash_no_half_seal` 实测过。
- **旧 s05 零 actual 决策读者**（结合 grep 与子代理 A/E 双重核验）：`s05_binding_digest` 在生产代码只出现在 INSERT/SELECT 参数位并一律被 `policy_binding_digest` 语义写入，无读取该列做路由/投影/决策的代码。
- **full_task exact 复制 actual**：task_commands.py:307-313 复制 actual 六字段+seal_generation；succeeded Task 禁 retry。
- **rebuild/metadata exact-clean 真实旁路**：三处 guard 豁免一致（runtime_materialize.py:342-353 / clean_preflight.py:37,350 / runtime_core.py:928-937）；NH5 红灯 T08-B count=3 在 NH8 被真消化为 0。
- **kind-only resolver 真实接管**：`resolve_for_source` 只消费 purpose+source_kind（workflow_registry.py:79-103），`registered_api→scatter`，未知 kind 422；public 入口链唯一（api/public/routes.py:227 → task_create.py:100 → config_snapshots.py:138-142），overrides 禁 workflow_key；mode/media 全仓生产路径不再映射 workflow key，仅作 route guard fact。
- **selected_output CONTROL 是 durable exactly-one**：runtime_materialize.py:775-933 只读 succeeded 行，零候选/多候选均 fail-closed，`INSERT OR IGNORE` 唯一键 `(execution_uuid, control_step_key)`（migration 018:27），无旧单 clean 回退。
- **暗 dispatch 已收编**：`_material_for` 登记表未登记 409（core.py:364-395）；claim 前 `_assert_process_declared` 409（runtime_core.py:647-662）；未知 compiled digest 503 前置（runtime_core.py:622-628）；`action_branch` 全仓零出现。
- **old-pin compat 真实**：旧图 enabled-but-unselected（api/app.py:418-431），旧 execution `actual_binding_state='legacy_unverifiable'`（migration 020），零 backfill、零写串；`test_old_pin_sequence_unchanged_after_kind_family_activation` 实测过。
- **4 通道端到端接线成立**（SA-B 逐通道核验）：dispatch_clean 9 capability 与 core.py 分发表一一对应无死路；registered-api 三 op 真实走 scatter root→child 独立发布并 namespaced+facet 命中（test_nh7_registered_api_retrieval.py:119-139）；HTTP-PDF 不再被当 HTML sanitize（intake/__init__.py:80-104）；browser 真 Firefox+geckodriver+setpriv non-root；检索端 namespace 缺失 422 + facet EXISTS 前置（retrieval_rank.py:38-154）；失败/空 clean 零向量三组 e2e 全绿。
- **上传/GC 生命周期安全闭环**：catalog+upload_pending 同 UoW（M-NH-05）；GC TX1→quarantine→TX2 recheck→restore/destroy（object_gc.py:195-294）；quarantine 期间新 ref 交错实测 restore 字节可读（test_ns6_gc_toctou.py）。
- **outbox 消费者无业务副作用**（runtime_outbox.py:131-139），向量 upsert 只在 vectorize Process outcome CAS 事务内（vector_publish_commit.py:57-212），双投递断言 vector_records 不增（crash_windows.py:326-387）。
- **证据链四元组可对账**：抽查多个 AP 的 manifest/tests.txt/queries 与 git log 中的 commit SHA 一致；NH9 的 62 passed 命令与文件可逐字符复现；子代理 E 独立全量复跑得 `910/910 passed`（本会话补充证据，闭包了 NH6 之后的全仓绿缺口）。

### 1.2 已确认的负面事实

- **跨文档失实陈述**：NH7 closure §0 gap#2、NH8 closure §0 gap#2/#3、NH9 closure gap#3、CROSS-NH review §Residual 均声称 `test_registered_api_scatter.py` 仍含 sqlite3 直读段；git 核验 **6256a97 与 HEAD 均无**（只余 `database_path` 文件名）。该条目在 4 份证据文档中反复出现且从未销账。
- **模型依赖格 live 语义缺失**：`DeterministicNs1Stub`（claude_cli.py:522）非 json 角色恒等回显 user_prompt（:565）；S11 为本地 fixture 服务器（nh6_runtime_support.py:140-180）对 PDF 恒返 "PDF INPUT OBSERVED"；`test_nh7_multimodal_lanes.py:152-154` 证明的是传输+blob 保真而非理解质量。
- **静默吞状态写漏洞**：`_fail_process_tx`（runtime_outcome.py:501-519）UPDATE 不检查 rowcount，与取消并发 bump fencing_generation 后（:784-801）失败结局会被静默放弃，执行/任务 failed 而 Process 行残留 running，直到 lease recovery 才收敛；与同文件 seal CAS 的 `rowcount!=1→raise`（:118-119）纪律不一致。
- **NOOP→SUCCEEDED 映射仍保留**（runtime_outcome.py:556），且非 exhausted_zero 的 SUCCEEDED 一律计 `indexed_success`（:697-703）——deactivate/delete/index.rebuild(no-op)/rebuild/metadata no_change 等零产物任务被计为"产品成功"口径。
- **七意图非法格闭集只覆盖 payload-shape 6 格**（closed_set_manifest.v1.json:28-69）；state×intent 组合（deactivate-on-deactivated→no-op SUCCESS、rebuild-on-deactivated→建 Task 后 409 等）在 resolver/callback/no-op 三层口径各异且未成文、未测试。
- **reacquire 法律被全局化**：runtime_materialize.py:65-83 对全部 `intake.ingest.kind.*` 图生效，而只有 http 图声明了 main-text-absent 的边——inline/local 的合法空文本源在 decode 决策点会得到 409 `workflow-reacquire-edge-undeclared`（错误归因，历史语义为 CLEAN_EMPTY 422）。
- **策略声称静默降级**：多个注册策略格在图中无 guard 命中时静默落默认边（如 local 图 decode_image 默认 doc.ocr、http static-PDF 的 print 声明落到 pdf_text），caller 声称与执行策略分歧无 409/告警。
- **崩溃窗覆盖实况**：九窗全部为进程内函数级 hook（wrapper raise / _uow_fault_hook / DB 回卷），零进程级 kill+重启；`recover_expired_leases`/`promote_due_retries`（runtime_outcome.py:236-393）从未被崩溃测试真实触发；W-NH-PUB 只测"发布成功后篡改 proof 被 fence 挡住"（crash_windows.py:302-316），未切中 tx 中间崩溃。
- **必查竞态组合零覆盖**：vector publish 回调中途 crash、GC TX1 commit 后 kill（MISSING_BYTES 路径，object_gc.py:225-227）、upload∥真实 delete_candidate、metadata refresh∥publish 的 pointer CAS 并发、outbox 重投幂等——均无测试 node；crash-windows.json nodes 仅 4 个具名，与 tests.txt 实际 node 集不对账。
- **个别断言弱化/死代码**：`codes == [200,200]` 在空库双飞下不可达（test_nh9_task_identity_conflict.py:149-152）；`ttl.released_pending in {0,1}`（test_nh4_upload_replay_race.py:247）；child-fail 后 succeeded sibling 的检索语义未断言。
- **enabled 旧图常驻**：13+1 旧图 + 16 历史 plan 仍在 active/registered 面（api/app.py:418-431），仅靠 `_active_workflow_keys` 与 metrics 维持；NH8 retirement 被一再推迟。
- **测试工程耦合**：NH7-T08 import scatter 文件 helper（test_nh7_registered_api_retrieval.py:12）；NH9 closed-set 直接 import 重跑 NH7 测试函数（test_new_harvest_closed_set.py:505-585）；browser 测试无环境即硬失败（无 skip 提示，报错模糊）。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | 全部关键结论均落 file:line；跨子代理结论再做 git/源码复核 |
| 本地命令 / 测试 | `yes` | 本审查人执行 git grep/git show/sed 核验；子代理复跑核心套件全绿；SA-E 全量 910/910 |
| schema / contract 反向校验 | `yes` | 001..023 migration 与三枚举、seal CAS、trigger 逐一对照 |
| live / deploy / preview 证据 | `partial` | default-root 浏览器/parser 为真实供给，但 LLM 格为 stub/fixture（已核验） |
| 与上游 design / QNA 对账 | `yes` | 每项结论对照 T-O-376..407 与 AP 台账 C/D |
| 引用既有 reviewer 报告 | `no` | 本轮未使用任何既有审查报告 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | "scatter 仍含 sqlite3"失实陈述跨 4 份 closure 传播 | `high` | `docs-gap` | `no` | CROSS-NH 台账修订 + 销账 |
| R2 | 10+3 中模型依赖格以 stub/fixture 顶替"live" | `high` | `delivery-gap` | `no` | manifest 打 model_backing 标签 + owner 书面签收 |
| R3 | `_fail_process_tx` 失败写入静默吞掉（违反 fail-loud） | `high` | `correctness` | `no` | rowcount!=1 抛 ConflictError + 补取消并发 fault 测试 |
| R4 | NOOP→SUCCEEDED 残留 + 非产物成功全计 indexed_success | `medium` | `correctness` | `no` | disposition 加 noop/lifecycle bucket 或删映射 |
| R5 | 七意图非法格闭集只闭合 payload-shape，state×intent 未成文 | `medium` | `scope-drift` | `no` | state×intent 矩阵入 closed set + 测试 |
| R6 | reacquire 法律被错误全局化到 inline/local 图 | `medium` | `correctness` | `no` | 限定 http 图或拆分错误码 |
| R7 | 注册策略格不可达时静默降级默认边 | `medium` | `protocol-drift` | `no` | claimed→executed 差异字段或 409 |
| R8 | W-NH-PUB 未测真实切中崩溃点 | `medium` | `test-gap` | `no` | vector_publish_commit callback 内加 fault hook |
| R9 | 九窗无进程级 kill+lease-recovery 验证 | `medium` | `test-gap` | `no` | 至少 PROCESS 窗改为重建 app+recover 断言 |
| R10 | NH6 之后四份 closure 缺全仓绿证据 | `high` | `test-gap` | `no` | CROSS-NH pack 追加 910/910 记录（本轮已补跑） |
| R11 | crash 注入粒度与台账 A 描述不符 | `medium` | `docs-gap` | `no` | 九个窗注入点逐一写入 tests.txt |
| R12 | 必查真实竞态组合零覆盖（GC 中段/发布中途/upload∥tombstone/metadata∥publish/outbox 重投） | `low` | `test-gap` | `no` | 每项补确定性交错测试 |
| R13 | 双飞/GC 断言弱化与死代码 | `low` | `test-gap` | `no` | 收紧为确定性断言 |
| R14 | 020 trigger 不防同形态改写 sealed 行 | `low` | `correctness` | `no` | trigger 加 OLD=NEW 一致性 |
| R15 | actual-reader 扫描为弱代理（不匹配 SELECT 列名） | `low` | `test-gap` | `no` | 增加列名/AST 扫描 |
| R16 | "零 acquire/decode/clean 进程"口径未限定（lifecycle 意图仍物化 acquire 进程） | `low` | `docs-gap` | `no` | 证据文档注明口径 |
| R17 | M-NH-04 冠名 migration 但无 DDL；旧图常驻 registered 面 | `low` | `docs-gap` | `no` | 更名 compat note；NH8 明确 retirement 边界 |
| R18 | 测试跨文件 import 耦合 + browser 环境硬失败 | `low` | `test-gap` | `no` | helper 独立模块 + 显式 skip/环境指纹 |
| R19 | sentinel 查询 + 确定性嵌入区分度低 | `low` | `test-gap` | `no` | 补一条非原词命中断言 |

### R1. "scatter 仍含 sqlite3"失实陈述跨 4 份 closure 传播

- **严重级别**：`high`
- **类型**：`docs-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - NH7 closure §0 gap#2、NH8 closure §0 gap#2/#4、NH9 closure gap#3、CROSS-NH review §Residual 均声称 `test_registered_api_scatter.py` 仍含 sqlite3 直读段且不得作为 T07/T08 PASS
  - `git grep -n sqlite3 6256a97 -- tests/e2e/test_registered_api_scatter.py` → 仅 `tests/e2e/test_registered_api_scatter.py:28: database_path=tmp_path / "mkb.sqlite3"`（文件名字符串，非直读）
  - HEAD 版本同样仅有该行；`1cdc066`（NH1）已删除全部 `import sqlite3`/`sqlite3.connect`
- **为什么重要**：
  - closure 被当作不可变证据消费。继任者（NH8/NH9/CROSS-NH）按此去"清一个不存在的段"，或误判 T08 的权威依据；该条目以"successor-owned red debt"形式在 4 份文档中悬空，从未销账，说明 closure 之间互引时未做重新核验。
- **审查判断**：
  - 属证据链诚实性污点，但不构成功能缺陷（该文件可收集且通过）。根因是 NH7 作者由基线期旧认知（0815 时代 source 测试 patch+running+sqlite3 直读）直接推断"HEAD 仍含"，之后 NH8/NH9/CROSS-NH 复制粘贴未复核——典型的 stale-fact 传播。
- **建议修法**：
  - CROSS-NH 台账补一行"scatter sqlite3 段：已于 1cdc066 去除，条目关闭；精确点名仍含 `sqlite3.connect` 的 4 个其他 e2e 文件（test_inline_ingress_staging.py:105 / test_ns1_pipeline.py:115 / test_ns2_dispatch_lanes.py:80,141 / test_human_review_gate.py:120）为后继 Port 化对象"。

### R2. 10+3 中模型依赖格以 stub/fixture 顶替"live"

- **严重级别**：`high`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`（已披露，非假绿；但需要 owner 书面收口）
- **事实依据**：
  - `src/runtime/inference/claude_cli.py:522` `class DeterministicNs1Stub`；`:565` 非 json 角色 `return ClaudeCliResult(request.user_prompt.strip(), ...)`（恒等回显）
  - `test_nh7_browser_dom_retrieval.py` 断言 `isinstance(cli, DeterministicNs1Stub)`（子代理 B/E 双重核验）
  - `nh6_runtime_support.py:140-180` S11 本地 fixture 服务器对 PDF 恒返 "PDF INPUT OBSERVED"；`test_nh7_multimodal_lanes.py:152-154` 只断言传输/blob 保真
  - plan `T-O-378` 明文"假PDF、OCR盗码、monkeypatch、空clean不得冒充完成"；final-execution-plan §7.7 台账 D"每合法格至少一 L3+L4 正例 live"
- **为什么重要**：
  - 这是整个战役实质体量最大的一处 under-delivery：web.llm_rewrite / pdf.document_understanding / doc.vision / OCR 等模型依赖格从未接触真实模型端点。closure 的 gap#3 与 review notes 有披露，因此不算假绿；但"10+3 live-to-retrieval"的 DoD 措辞被静默降级为"live-shaped + deterministic/stub"，读者无法从 manifest 区分哪些格是真模型、哪些是 stub。
- **审查判断**：
  - 定性为"已披露的诚实降级"，而非欺诈；但按 T-O-406 四层不可互换的精神，stub 格不应与真格同列 L3/L4"live"证据，需要显式分档。
- **建议修法**：
  - closed-set manifest 对每个策略格增加 `model_backing: "deterministic-stub" | "local-fixture" | "real-model"` 字段；closure 为 stub 格单列"transport-level 证据"行；为真实模型端点（`ns1_cli_mode="subprocess"` 已存在）预留可配置的 L4 验收入口。

### R3. `_fail_process_tx` 失败写入静默吞掉（违反 fail-loud）

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`no`（窗口小、lease recovery 可自愈，但违背 T-O-383 fail-loud）
- **事实依据**：
  - `src/runtime/workflow/runtime_outcome.py:501-519`：`UPDATE mkb_processes SET status='failed' ... WHERE process_uuid=? AND status NOT IN ('succeeded','failed','cancelled') AND fencing_generation=?`，随后只 `if updated: 写事件`，`updated==0` 时**不抛错不中止**
  - 调用链：`accept_outcome` failed/retry-exhausted/indeterminate 分支（:197-207/:213-224/:336-359）在 `_fail_process_tx` 返回后**继续执行 FAILED 路由**（:222-223）
  - 与取消并发时取消 UoW bump fencing_generation（:784-801），使失败结局静默弃写、Process 残留 running
  - 对比 seal CAS 的 `rowcount!=1→raise` 纪律（actual_s05.py:118-119）
- **为什么重要**：
  - 在"取消并发 + accept failed outcome"组合下产生"Process running / Execution failed"的可观测不一致，与全仓唯一的终态写纪律（seal/outcome 均 rowcount 校验）不一致；metrics/observability 会一段时间内看到幽灵 running 进程。
- **审查判断**：
  - 真实缺陷，但触发面窄（需取消与失败窗口重叠）且有 lease recovery 兜底收敛，故不构成集成 blocker；属于 CROSS-NH 阶段应修复的第一优先级正确性项。
- **建议修法**：
  - `_fail_process_tx` rowcount != 1 时抛 `ConflictError("stale-process-fence")` 并使 accept_outcome 停止 FAILED 路由（与 seal 同法）；补一条"取消并发中 accept failed outcome"的 fault 测试（W-* 窗目前未覆盖此组合）。

### R4. NOOP→SUCCEEDED 映射残留 + 非产物成功全计 indexed_success

- **严重级别**：`medium`
- **类型**：`correctness`（telemetry 语义漂移）
- **是否 blocker**：`no`
- **事实依据**：
  - `runtime_outcome.py:556` `WorkflowTerminalKind.NOOP → ExecutionStatus.SUCCEEDED` 映射仍在
  - `runtime_outcome.py:571-586` 只要求 source process+proof 即算成功，不区分 NOOP/SUCCESS
  - `runtime_outcome.py:697-703` 非 exhausted_zero 的 SUCCEEDED 一律 `indexed_success`；metrics.py:122-127 disposition 仅 4 值无 third bucket
  - `test_nh7_exhausted_zero.py:219-277` 明确把 NOOP→SUCCEEDED 的存在作为断言保留
- **为什么重要**：
  - `mkb_task_result_disposition_total{disposition="indexed_success"}` 目前包含 deactivate/delete/index.rebuild(no-op)/rebuild/metadata no_change 等从未产出向量的任务；未来任何新图注册 NOOP 终端（contracts/workflow/models.py:41-45 无禁止）将得到与 SUCCESS 无差别、被计成产品成功的"成功"。指标本应回答"产品是否产出可检索知识"。
- **审查判断**：
  - 潜伏面大于现伤面：当前无图注册 NOOP 终端，且 exhausted_zero 已拦截 NOOP 组合；属 telemetry/语义漂移的 medium 风险。
- **建议修法**：
  - disposition 增加 `noop`/`lifecycle` bucket，或对非 ingest 意图使用独立 label；删除或守卫 NOOP→SUCCEEDED 映射（或在契约中禁止新图注册 NOOP 终端）。

### R5. 七意图非法格闭集只闭合 payload-shape，state×intent 网格未成文

- **严重级别**：`medium`
- **类型**：`scope-drift + protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - `tests/fixtures/new_harvest/closed_set_manifest.v1.json:28-69` intent_illegal 仅 6 格，全为 payload-shape 格
  - 执行期三层 enforcing 口径各异：resolver 409（`targets.py:165-166` delete-on-deleted）、进程内 callback 409（`acquisition_intents.py:108-114` rebuild-on-deactivated→REBUILD_TARGET_STALE、:215-221 metadata）、no-op SUCCESS（`lifecycle_apply.py:92-104` deactivate-on-deactivated→applied=False 且 Task 仍 SUCCEEDED、:231-246）
  - `test_nh8_intent_applicability.py` 只覆盖 shape 格，未覆盖 state×intent 组合
- **为什么重要**：
  - T-O-405 要求"七意图 applicability+code 闭集；非法格不建 Task/Process"。当前闭集声明的覆盖面小于实际判定面：deactivate-on-deactivated 以"受理+无副作用 SUCCESS"表达，既不在 NOSUCCESS 识别清单，也没有 L3/L4 断言。NH8 closure note 3 只解释了 delete 的 409 不对称，未说明 deactivate/reactivate 的 no-op SUCCESS 是设计还是残留。
- **审查判断**：
  - 属"闭集声明与执行面不一致"的 scope-drift；行为本身（no-op 不产生副作用）是安全的，问题在可审计性。
- **建议修法**：
  - 将 state×intent 组合矩阵（每意图 × {active/deactivated/deleted/不存在}）写进 closed set 并固定 disposition/code；对 no-op SUCCESS 显式文档化或改为同 idempotency 语义的 409；补 L3/L4 断言"非法 state 组合零 Task 或确定性 code"。

### R6. reacquire 法律被错误全局化到 inline/local 图

- **严重级别**：`medium`
- **类型**：`correctness`（错误归因）
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/workflow/runtime_materialize.py:65-83`：对**所有** `workflow_key.startswith("intake.ingest.kind.")` 图，凡 `media_family=text && main_text_presence=absent` 且候选 route 无 reacquire 边即 409 `workflow-reacquire-edge-undeclared`
  - 只有 http 图声明了 `representation_main_text_presence=absent` 的边（kind_family.py:495,571）
  - inline/local 图刻意无 reacquire 设计 → 空 txt / 空 inline payload 这类合法空文本源在 decode 决策点 409，历史语义是 clean 阶段 `CLEAN_EMPTY` 422
- **为什么重要**：
  - T-O-402/388 的 reacquire 法律本意是 http 通道"有限声明式正向再获取"；把该法律施加到无此设计的图上，使真实原因被错误归因为"reacquire 问题"，误导运维/使用者的排查方向。
- **审查判断**：
  - 属语义误伤 + 错误码误导；fail-closed 方向正确（空文本不产生向量），但归因与图设计不符。
- **建议修法**：
  - 法律限定为仅对声明了 reacquire 能力的图（http kind）生效；或至少把错误消息区分为"该 kind 不支持 reacquire"与"声明了 reacquire 但无边可走"，保持 fail-closed。

### R7. 注册策略格不可达时静默降级默认边

- **严重级别**：`medium`
- **类型**：`protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - `kind_family.py:389-410` local 图 `clean_doc_ocr`/`clean_doc_ocr` 无显式 guard（decode_image 默认落 `clean_doc_ocr`、decode_text 默认落 `clean_deterministic`）；`kind_family.py:460-471` http 图 static-PDF 的 `web.browser_print_pdf` 声明落到 `clean_pdf_text`、`pdf.text_layer` 声明落到 OCR
  - `strategies.py:159-176` bound clean 以 step_key 为身份执行并记录于 evidence，但 claimed→executed 分歧无 409 无告警
- **为什么重要**：
  - "registered guard 选边"承诺的部分策略组合实际是"被忽略的声称"：caller 声称的策略可能在图中不可达而静默执行默认策略，产物与声称语义不符，且无任何可见信号——诚实性打折。
- **审查判断**：
  - 属可观测性缺口（每格至少一条路径可达，未违反"所有合法格可达"），但"声称与执行符"的契约强度低于 QNA 描述。
- **建议修法**：
  - route decision payload / clean evidence 增加 `claimed_strategy→executed_strategy` 差异字段；更激进：对注册值在本 kind 图不可达的组合返回 409。

### R8. W-NH-PUB 未测真实切中崩溃点

- **严重级别**：`medium`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `test_new_harvest_crash_windows.py:302-316` `test_w_nh_pub_incomplete_proof_not_visible` 全程无注入：先完成发布成功，再事后 `UPDATE mkb_publication_proofs SET actual_count=actual_count+1`，再断言 search 空——验证的是 fence 可见性，不是"发布事务中途崩溃"
  - "无双 serving"仅以事后 `serving_revision_uuid IS NOT NULL == 1` 成立（:278-284/:317-323）
  - pointer CAS 与 publish_revision_tx 之间、proof insert 后 pointer CAS 前崩溃，均无注入；crash-windows.json 的 PUB 无具名 node
- **为什么重要**：
  - PUB 是唯一直接切 serving 的窗口；若 outcome tx 内 proof 写后、pointer CAS 前崩溃（或 ACK 前崩溃引发回调重放），现有证据给不出"无双 serving/无双指针"保证。
- **审查判断**：
  - 非假证（fence 本身经证明有效），但 assurance 粒度低于"切中窗口"标准。
- **建议修法**：
  - 在 `vector_publish_commit.py` callback 内加与 `_uow_fault_hook` 同款 fault hook（proof insert 后 / pointer CAS 后各自 raise），断言整 tx 回滚、search 0、serving 唯一；并将该 node 具名补进 crash-windows.json。

### R9. 九窗无进程级 kill + lease-recovery 验证

- **严重级别**：`medium`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - 九窗注入全部为同进程函数级：`tasks.create` wrapper raise（crash_windows.py:100-111）、`actual_s05_fault_hook`（test_nh3_seal_crash_windows.py:166-170）、`_uow_fault_hook`（crash_windows.py:393-397）、DB 回卷（fanin:35-58）、`_FailOneScatterChild`（closed_set.py:455）
  - `recover_expired_leases`/`promote_due_retries`（runtime_outcome.py:236-393，fencing_generation+1 恢复路径）在整组崩溃测试中从未被真实触发
- **为什么重要**：
  - 生产 crash 后由 supervisor/新进程经 lease recovery 恢复；该路径的 fencing 递增与重放安全性（不重跑、不换 process_key、不双 effect）没有一条崩溃窗直接证明——恰好是幂等保证在生产中最关键的一段。
- **审查判断**：
  - 与 R8 同属"诚实但不完备"：代码层 effect-once CAS 扎实，但未闭环到进程生命周期。
- **建议修法**：
  - 至少 PROCESS 窗改造为：执行后强制析构 runtime/重建 app（同 sqlite 文件）→ 触发 `recover_expired_leases` → 断言不重跑、不换 process_key、无双 effect。

### R10. NH6 之后四份 closure 缺全仓绿证据

- **严重级别**：`high`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - NH1..NH6 closure 各有全仓诊断（595/602 → 635/641 → 672/678 → 705/711 → 748/753 → 794/799）；NH7/NH8/NH9/CROSS-NH 之后的全仓数字全部消失，CROSS-NH 只记录"unique 62 passed"
  - campaign DoD 含"无 in-scope 失败"；todo-list CROSS-NH-TEST 要求"持续测试↔修复直到无 in-scope 失败"但无最终全仓测量
  - 本会话子代理 E 独立全量复跑：`uv run pytest -q --tb=no` → **910 collected / 910 passed**（约 2h15m）
- **为什么重要**：
  - 62 与 910 之间差额（848 个节点）从未在任何 closure 被证明绿；结论"全部 closed"的文档层证据链在最后四个阶段出现空档——本次补测通过，但证据链本身是空的。
- **审查判断**：
  - 属文档/流程缺口（evidence 缺失而非测试失败），已被本轮补测闭合。
- **建议修法**：
  - CROSS-NH pack 追加 HEAD 全仓 run（910/910）的记录与 SHA，作为 campaign DoD 的终态测量。

### R11. crash 注入粒度与台账 A 描述不符

- **严重级别**：`medium`
- **类型**：`docs-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - NH9-04 台账描述"W-window injection: CREATE/SEL/SEAL…"；实际 `test_new_harvest_crash_windows.py:91` 的 CREATE 窗是"在 `tasks.create` 外层包一个首次调用 raise 的 wrapper"，crash 发生在原 create（含 fingerprint CAS）执行**之前**，而非"identity 与 insert 之间"
  - SEL/SEAL 窗为事务内拦截（test_nh3:133-176，真实打在 UoW 中间，最强）
  - crash-windows.json nodes 仅具名 4 个（create/process/fanin/prom-cat），SEL/SEAL/FANIN-PORT/PUB/OUTBOX/GC-INGEST 不具名；"62 passed"在 tests.txt 无逐项对账行
- **为什么重要**：
  - "崩溃后无半提交+幂等重放"的结论成立（API 行为真实），但"插入点精确性"低于台账承诺，作为不可变 assurance 证据的粒度被夸大。
- **审查判断**：
  - 证据诚实度问题（不涉功能），需台账如实标注注入粒度。
- **建议修法**：
  - 把九窗注入点（fn wrapper / 事务内 hook / 回卷）逐一写入 tests.txt 注释与 crash-windows.json。

### R12. 必查真实竞态组合零覆盖

- **严重级别**：`low`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - GC TX1 commit 后 kill：quarantine 孤儿/catalogue 活而 bytes 缺 → `MISSING_BYTES` 路径（object_gc.py:225-227）无测试
  - upload∥真实 `delete_candidate`：T06 的 upload∥GC 只是并发 scan `collect_candidates`，非删除并发
  - metadata refresh∥publish 的 pointer CAS `active_index_generation < ?` 竞态（vector_publish_commit.py:144-162）无并发测试
  - `wake_execution`/`gate_decision` 类 outbox 重投：只测了无副作用的 vectorize_construct，materialize 的 existing-check（runtime_materialize.py:396-401）靠设计保证、未测
- **为什么重要**：
  - 这些正是生产故障最常见的交错组合；"九窗"之外的覆盖为零，属钳位外风险。
- **审查判断**：
  - 覆盖缺口而非实现缺陷；按风险等级属低-中优先的 follow-up。
- **建议修法**：
  - 每项补一条确定性交错测试（准 T06 手法）；GC 补一条 quarantine 后 kill 的恢复路径测试。

### R13. 双飞/GC 断言弱化与死代码

- **严重级别**：`low`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `test_nh9_task_identity_conflict.py:149-152`：`assert codes[0] in {200,201,409}` 且 `201 in codes or codes == [200,200]`——`[200,200]` 在空库双飞下不可达，`409` 在相同指纹下不可达，断言未收紧到确定性 `[200,201]`
  - `test_nh4_upload_replay_race.py:247`：`assert ttl.released_pending in {0, 1}`（靠后续最终态断言兜底才可接受）
  - child-fail 后 succeeded sibling 是否可检索未断言（closed_set.py:466-484），FG-NH-04"不使父检索成功"以父状态而非 query 表达
- **为什么重要**：
  - 断言宽松降低回归检出率；race 类测试是幂等防线的主体，弱断言会放过回归。
- **审查判断**：
  - 非当前缺陷，属测试强度问题。
- **建议修法**：
  - 双飞收紧为 `sorted(codes)==[200,201]`；child-fail 补一条对 succeeded sibling 内容的 search 断言；TTL 断言改为最终态裁定。

### R14. 020 UPDATE 触发器不构成 sealed-once 完整性保证

- **严重级别**：`low`
- **类型**：`correctness`（schema hardening）
- **是否 blocker**：`no`
- **事实依据**：
  - `src/persistence/migrations/020:36-53`：UPDATE 触发器只校验 NEW 形态（全 sealed 或全空），不比较 OLD；同形态改写（如单独改 `actual_clean_strategy`）不触发
  - sealed-once 真实保证完全依赖应用层 CAS（actual_s05.py:115-116）与唯一写者纪律
- **为什么重要**：
  - 目前无生产写路径做同形态改写（写者唯一、全量写），属于"保证靠应用层纪律"而非 DB 不变量；未来新增写路径时无底层防线。
- **审查判断**：
  - 加固项，非风险项。
- **建议修法**：
  - trigger 增加 OLD=NEW 一致性校验（sealed 行禁止改 digest/step_key/selection 字段），把 sealed-once 下沉为 DB 不变量。

### R15. actual-reader 扫描为弱代理

- **严重级别**：`low`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `tests/domain/test_nh3_actual_readers_scan.py:17` 只匹配 `["s05_binding_digest"]` 索引与 `.get("s05_binding_digest")` 模式；不覆盖 SELECT/INSERT 列名
  - 仓库实际旧列引用全部为 INSERT/SELECT 列名（task_create.py:402 / scatter_intake.py:183,607 / acceptance_snapshot.py:143 / clean_preflight.py:385,494）
  - `SELECT *` 传播后 `row["s05_binding_digest"]` 做决策的回归会漏检
- **为什么重要**：
  - "旧列零 readers"目前靠人工审计成立，扫描是弱代理；这是 NH3 DoD 硬闸的看门测试，弱代理会放过回潮。
- **审查判断**：
  - 测试强度问题，非当前缺陷。
- **建议修法**：
  - 增加"列名出现在 SELECT 且结果进入业务路径"的扫描，或 AST 检查 SELECT * + 下游索引组合。

### R16. "零 acquire/decode/clean 进程"口径未限定，lifecycle 意图仍物化 acquire 进程

- **严重级别**：`low`
- **类型**：`docs-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `rebuild-process-absence.json` 与 NH8 closure §3 断言 acquire/decode/clean=0，对象是 rebuild/metadata（T02/T03）
  - 但 deactivate/reactivate/delete 在 inline 图 start→acquire_inline 无 guard 直连（kind_family.py:317），必然物化 1 个 `intake.acquire.inline` 进程（handler 分流为 `_acquire_lifecycle`，acquisition_ingest.py:49-50）
  - test_nh8_api_item_intents.py:180-190 对 lifecycle 意图无 `_forbidden_keys` 反向断言
- **为什么重要**：
  - 外部审计读到"exact-clean 零进程"可能误以为七种意图均零 ingest 进程；且"以 acquire 进程名跑 lifecycle 无获取动作"的命名不对称造成 lineage 困惑。
- **审查判断**：
  - 口径文档缺限，行为无错。
- **建议修法**：
  - 证据查询/closure 显式注明口径（rebuild/metadata/index.rebuild 零 ingest 进程；lifecycle 单 acquire 进程承载 lifecycle handler），或引入独立 process_key。

### R17. M-NH-04 冠名 migration 却无 DDL；旧图常驻 registered 面

- **严重级别**：`low`
- **类型**：`docs-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `docs/evidence/new-harvest/AP-NH2/migrations/M-NH-04-kind-compat.md` 无 SQL（migrations 目录 018/019/020 为真实 DDL），实为 registry/resolver/metrics 运维变更
  - 13+1 旧图 + 16 历史 plan 仍 enabled 注册（api/app.py:418-431），future 改变活跃集必须同步 `_assert_execution_binding`（runtime_core.py:617）的 key 集合
- **为什么重要**：
  - migration inventory 命名失实影响审计对账；旧图常驻面使 retirement 边界窄。
- **审查判断**：
  - 前者文档事实问题，后者已知 deferred（NH8）但未关闭。
- **建议修法**：
  - 更名 M-NH-04 为 compat note 或在证据索引标注"operational compat"；CROSS-NH 明确旧图 retirement 的边界与 in-flight 纪律。

### R18. 测试跨文件 import 耦合 + browser 环境硬失败

- **严重级别**：`low`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - T08 `test_nh7_registered_api_retrieval.py:12` import scatter 文件 helper；NH9 closed-set 直接 import 重跑 NH7 测试函数（test_new_harvest_closed_set.py:505-585）——helper 改动会无声改变多个 AP 的"PASS"含义
  - browser 测试（T05/T06）无环境即硬失败且报错模糊（nh6_runtime_support.py:93-104 仅提示 "requires one non-loopback local address"，无 skip）
  - `test_nh7_no_fetcher_patch.py:22-24` 对缺失文件 `continue`
- **为什么重要**：
  - 证据可复现性脆弱 + 跨 AP 语义耦合，降低闭集证据的隔离性。
- **审查判断**：
  - 工程债，非功能缺陷。
- **建议修法**：
  - 将 T08 依赖的 helper 拆到独立 support 模块并加内容快照；browser 测试显式 skip 条件与环境指纹记录。

### R19. sentinel 查询 + 确定性嵌入区分度低

- **严重级别**：`low`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - 命中文本与查询词几乎逐字相同，经 `deterministic_embedding`（deterministic_embedding.py:19-36）token-hash 向量 cosine 命中（retrieval_rank.py:156-223）；`excluded` 断言的区分度主要来自 facet 谓词而非语义打分
- **为什么重要**：
  - offline profile 下未证明语义泛化；"改写/总结而非原词命中"的质量维度无否定断言。
- **审查判断**：
  - 与 R2 同源（模型 stub 的后遗症），低优先级。
- **建议修法**：
  - 增加"改写/非原词命中"的验证入口（配合真模型配置），或在闭集 manifest 标注确定性嵌入的限定范围。

---

## 3. In-Scope 逐项对齐审核

> 依据 final-execution-plan §4.1 与用户三目标逐项对齐。结论统一使用 `done | partial | missing | stale | out-of-scope-by-design`。

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| S1 | 目标一：intake 4 通道实际接线（web/api/pdf/doc 真实输入→namespaced+facet 检索） | `done` | 四通道端到端证据链成立；负向桩（空 clean 零向量/namespace 422/失败零向量）齐；R2/R19 的模型格降级已披露但需分档标注 |
| S2 | 目标二：dynamic workflows 实际落地并接管 4 通道路由（kind-only resolver / selected_output CONTROL / 暗 dispatch 停用 / tail 唯一 / old-pin compat） | `done` | 生产路由唯一入口已接管；R6（reacquire 全局化）、R7（策略静默降级）、R17（旧图常驻）为行为精度/文档问题 |
| S3 | 目标三：竞态与错误幂等机制完善（seal CAS / create 唯一 / outbox / GC TX1→TX2 / crash 九窗） | `partial` | 机制层全真（effect-once CAS 扎实）；但崩溃窗无 kill-重启验证（R9）、PUB 未切中（R8）、必查竞态零覆盖（R12）、注入粒度过账（R11）、`_fail_process_tx` 吞失败（R3） |
| S4 | S-NH-F1 NH1 chosen-shape validation + proof baseline（T01..T07 GO） | `done` | NH1 套件复现 76 passed；stop-or-go=GO 成立；生产未污染 |
| S5 | S-NH-F2 NH2 kind graph、merge CONTROL、resolver、compat（T01..T07） | `done` | 33 passed 复现；CONTROL exactly-one 真 durable；compat digest 0/16 |
| S6 | S-NH-F3 NH3 typed history、representation、reacquire、actual S05/restart（T01..T08） | `done` | 35/36 passed（子代理 A 复跑）；seal 同 UoW + full_task exact 成立；R6 为全局化误伤 |
| S7 | S-NH-F4 NH4 authenticated upload+stat、bounded CAS、pending hold、GC（T01..T07） | `done` | 43 passed 复现；catalog+pending 同 UoW；GC TX1→TX2 交错安全；R12 的 GC 中段 kill 未覆盖 |
| S8 | S-NH-F5 NH5 strict semantic authority、S06 overlay、facet/query naming（T01..T08） | `partial` | 39 hard-gate 绿；T08-B 红账真实 3→NH8 消化为 0；六元组/S06/channel/facet 均真 |
| S9 | S-NH-F6 NH6 real local parser/browser/OCR/Vision/DU supply 与安全（T01..T10） | `done` | 45 passed；真实 Firefox/parser/TTL；R2 的 S11 fixture 属已披露降级 |
| S10 | S-NH-F7 NH7 10+3 vertical live-to-retrieval + exhausted_zero（T01..T10） | `partial` | 40 passed 精确复现；exhausted_zero 独立；但 10 格中模型依赖格为 stub/fixture（R2），非"真实模型 live" |
| S11 | S-NH-F8 NH8 七意图、exact-clean、publication lifecycle、old-pin（T01..T10） | `done` | 29 passed 复现；T08-B=0 真消化；rebuild/metadata 真旁路；R5 state×intent 网格未成文 |
| S12 | S-NH-F9 NH9 closed-set、race/crash/security/compat/retrieval mega（T01..T11） | `partial` | 62 passed 复现；FG 17 绿；九窗诚实但不完备（R8/R9/R11/R12） |
| S13 | Capstone A–J / campaign DoD（无 in-scope 失败 + evidence pack 四元组） | `partial` | 本轮补测 910/910 通过；但 NH6 后无全仓绿记录（R10）；CROSS-NH 尚未做九 AP 耦合总账（正由本审查补齐） |
| S14 | 证据纪律：closure/evidence 四元组、诚实 5 态、无假绿 | `partial` | 四元组可对账；但 R1（sqlite3 失实陈述跨 4 文档传播）与 R11（注入粒度）违反"每个 ✅ 归类 verified"的严谨度 |

### 3.1 对齐结论

- **done**: `9`（S1/S2/S4/S5/S6/S7/S9/S11 + 部分子项）
- **partial**: `5`（S3/S8/S10/S12/S13/S14 中计 5）——S8 中 T08-A done / T08-B 设计内 handoff；S10/S12 主体 done、模型格与崩溃窗粒度 partial
- **missing**: `0`
- **stale**: `1`（R1 scatter sqlite3 条目在 4 份 closure 中均为 stale 事实）
- **out-of-scope-by-design**: `3`（raw GET、existing-object upgrade、experiment 发车）

> 整体印象：这更像 **"三目标中两项完整收口、第三项机制层完整但 assurance 力度未达台账承诺；证据链主体可信但有 1 处失实陈述与 1 处体量级降级未分档"**，而不是 completed 的完美闭环；更不是 blocked。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | S16 browser egress review 签收 | `遵守` | 文件存在且未伪造签名（NH6 closure B 类 deferred），跨 NH7/NH9 保持诚实 |
| O2 | experiment 发车（日期/分数为空，不进 closure join） | `遵守` | `.experiment` gitignore 且 `in_closure_join=false`；T-O-380 遵守 |
| O3 | Raw object GET/list/presign（O-NH-04） | `遵守` | 全仓 raw/public read 为零（route/source scan 与 NH4 核验一致） |
| O4 | Existing-object new-cleaner upgrade（O-NH-03 / T-O-401） | `遵守` | upgrade 入口=0，NH8-T10 复现 |
| O5 | 通用 Workflow JOIN/DSL/loader（O-NH-06） | `遵守` | 架构扫描禁自由表达式/JOIN/action_branch，T07 复现 |
| O6 | 第五 kind / caller workflow_key / live connector（O-NH-01） | `遵守` | 生产入口禁 workflow_key；kind-only 唯一选图 |
| O7 | 旧图 enabled 常驻面（NH8 retirement 推迟） | `部分违反`（设计内） | 13+1 旧图 + 16 plan 仍 registered；有 telemetry 与 in-flight 纪律，但"有界 retire"承诺在 CROSS-NH 仍未关闭 |
| O8 | scatter sqlite3 条目（NH7/NH8/NH9 的 B 类 deferral） | `误报风险` | 事实已不存在（1cdc066 已 Port 化），条目悬空传播（R1），属误报而非真实 deferred |
| O9 | T08-B（NH5 红账 3 process） | `关闭` | NH8 已消化为 0，非悬空 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`approve-with-followups`。NH1–NH9 三大目标中"4 通道接线"与"dynamic workflows 接管"结论成立且证据可复验；"竞态/错误幂等机制"机制层为真、覆盖层为 partial。整体无系统性假绿、无欺诈性闭环、无级联断点；但存在 1 处跨文档失实陈述（R1）、1 处战役最大体量降级未分档（R2）、1 处违反 fail-loud 的状态写漏洞（R3）与崩溃/幂等 assurance 力度不足（R8/R9/R11/R12），故 CROSS-NH 在下列项目落账前不应视为最终 closed。
- **是否允许关闭本轮 review**：`yes`（本轮为独立审查，发现已完整归档；关闭针对"review 本身的完成度"）
- **关闭前必须完成的 blocker**：
  1. `R1 账目修订`：CROSS-NH 台账修订 scatter sqlite3 失实陈述并销账（含精确点名 4 个仍含 sqlite3.connect 的 e2e 文件）；
  2. `R2 分档与 owner 签收`：closed-set manifest 对模型依赖格打 `model_backing` 标签（stub/fixture/real），并由 owner 对"模型格 live 由 stub/fixture 顶替"做出书面签收或 waiver 化；
  3. `R3 修复或显式豁免`：`_fail_process_tx` rowcount!=1 抛错，或 owner 书面接受 lease-recovery 兜底并登记。
- **可以后续跟进的 non-blocking follow-up**：
  1. `R5`：七意图 state×intent 组合矩阵入 closed set 并补测试；
  2. `R6/R7`：reacquire 法律限定 http 图 + claimed→executed 差异字段；
  3. `R8/R9`：W-NH-PUB 真 fault hook + 至少 PROCESS 窗进程级 kill-重启验证；
  4. `R12`：GC 中段/发布中途/upload∥tombstone/metadata∥publish/outbox 重投五条确定性交错测试；
  5. `R4`：disposition 增加 noop/lifecycle bucket；`R14`：020 trigger 下沉 sealed-once；`R10`：追加 910/910 全仓记录。
- **建议的二次审查方式**：`same reviewer rereview`（对本报告 §6 响应后再审 R1/R2/R3 三项）或 `independent reviewer`（对 crash windows 注入粒度做深度重审）
- **实现者回应入口**：请按 `.adocs/templates/code-review-respond.md` 在本文档 §6 append 回应，不要改写 §0–§5。

> 本轮 review 结论：campaign 主体收口成立，附 2 项必办账目修订 + 1 项必办签收/修复；CROSS-NH 的正式 closed 需等待实现者按 §6 响应。