# 调查面 `09` · fail-loud、replay/竞态、兼容迁移与闭集证明 — 深度评估

> **对象 / scope-fence**：横切 Task / intake / upload / binding 的 replay、`ConflictError`/CAS、crash windows、retry/recovery、old Workflow compatibility、default-root e2e、retrieval/facet mega matrix、fake-green 封堵；**本面不含**：重写 01–08 的功能设计（交由面 `01`–`08`）。本面只校验不变量和证明分母。
> **日期**：`2026-08-29`
> **作者**：`Grok analysis-fleet / review-fleet`（fleet / panel：`new-harvest-reference-anchor`）
> **文档性质**：`assessment / analysis`（单面 measure-first 深评；零决策——只 MARK 不裁决）
> **文档状态**：`draft`
> **流水线位置**：站② · 上游 = [[assessment-index]]（消费其冻结分母）
> **对照参考**：`docs/eval/new-harvest/pre-initial-planning-qna.md` v0.5 `T-O-376/378/380/383`；`docs/baseline/spec-glossary.md` `S05Binding`；`docs/baseline/domain-truth/S05-intake-cleaning.md` `S05-T025`；`docs/baseline/domain-truth/D08-legacy-capabilities-migration.md` `D08-T004/T008/T011`（**draft / owner-review**）；IETF Idempotency-Key **draft-07（访问日已过期 I-D）**；Temporal Workflow Definition / Safe Deployments；Confluent Kafka delivery-semantics；TigerBeetle Protocol-Aware DST
> **上游权威输入**：
> - `docs/eval/new-harvest/assessment-index.md` — §2.2 冻结分母 `D-12/D-13/D-23/D-24` / §3.09 本面登记 / `G-NH-01..10`
> - `docs/eval/new-harvest/pre-initial-planning-qna.md` — `T-O-376/378/380/383`（只 CITE）
> **下游消费者**：`docs/eval/new-harvest/planning-proposed.md` · `pre-charter-qna.md`（owner-gate 裁决）· 设计/执行制品
>
> **邻面落盘状态（本轮复测）**：`docs/eval/new-harvest/reference-anchor/` 已有 `assessment-analysis-01`…`08` 共 9 份，状态皆 `draft`。本面 **不重写** 功能设计（index §1.2）；功能 S1 改为 **消费** 邻面 `NH-RA0X-B*`。Wave C 冻结前须引用这些稳定 gap ID，而不是再声称「文件不存在」。

---

## 0. Verdict（结论先行）`[核心]`

- **0.1 一句话缺口 / 现状判断**：HEAD `1221aa1` 已有可复用的 Task 指纹 replay、无环图拒注册、Gate/Process/object CAS、scatter fan-in 修复代码、compat revision pin 与部分 fail-closed（空 clean / 未注入 browser / 未配置 OCR），但 **闭集证明未成立**：actual `s05_binding_digest` 仍由 domain digest 冒充；source capability e2e 用 monkeypatch 且停在 `running`；sqlite3-on-Turso 使 recovery 检验红灯；公共上传面为 0；`CLEAN_EMPTY` / `task-identity-conflict` 几乎无对应用例；retrieval e2e 缺 Layer-A namespace。`T-O-376` live-to-vector 与 `T-O-383` 绑定后 fail-loud **不能**在本 HEAD 上冻结。
- **0.2 Top blockers（最关键断点）**：
  1. `NH-RA09-B01`（**消费** `NH-RA02-B01/B03`）/ `NH-RA09-B12`：创建时 `s05_binding_digest=domain_binding_digest`，ProcessCommand 只带 domain binding——无法证明「选边后封闭、封闭后不换工人」。
  2. `NH-RA09-B02` / `NH-RA09-B03` / `NH-RA09-B15`（**消费** `NH-RA05-B01`）：monkeypatch browser、source e2e 8s 窗仍 `running`、默认组合根未注入——`T-O-378` 点名的假接线仍是现行 e2e。
  3. `NH-RA09-B04` / `NH-RA09-B05`（**消费** `NH-RA06-B01`）/ `NH-RA09-B06`：retrieval 无 namespace/facet；public upload 为 0；上传 / 未封闭 binding / 空 clean / OCR 未部署的最小 fail-loud 证明缺位。
  4. `NH-RA09-B07` / `NH-RA09-B08`：old pinned + **kind 家族新图**的共同验证未建；每面冻结所需 failure/replay/race 格栅尚未落地（本面主产品，见 §9）。邻面 01–08 **已落盘**，B13 不再以「无文件」作红灯。
- **0.3 总体方向建议**：沿用已交付 CAS/replay/compat substrate，**扩到 actual binding / 四通道 default-root / 上传 / mega**；把测试分层写进 charter 候选（`G-NH-18`，只 MARK）；实验发车日保持 OPEN（`T-O-380`）。不把 `.experiment`、503、monkeypatch、Task succeeded、`publication_ready` 当 DoD。
- **0.4 如何读本台账**：见模板图例。本面主题轴 = `fail-loud` / `replay·idempotency` / `CAS·race·crash-window` / `compat-migration` / `anti-fake-green·mega-proof`。

---

## 1. 方法与证据基线 `[核心]`

> 读了哪些代码/文档/参考；什么算可采信；怎么复现。**先证可证性，再下判断。**

- **1.1 本仓证据（如何测量）**：HEAD `1221aa1`。`grep` + `read_file` 覆盖 `task_create.py`、`models.py` 无环校验、`runtime_{core,gates,outcome,scatter,outbox}.py`、`lsrag_definition.py` / `lsrag_historical.py` / `builtin_lsrag.py`、`api/app.py` 组合根、`clean_preflight.py` / `types.py` / `acquisition_ingest.py`、`local_store.py` / `object_gc.py`、`retrieval_request.py`、e2e `test_registered_api_scatter.py` / `test_source_capability_paths.py` / `test_intake_identity_replay.py` / `test_inline_ingress_staging.py`、unit `test_workflow_revision_compatibility.py` / `test_ns6_gc_toctou.py`、README K1、QNA `T-O-376..383`、glossary `S05Binding`、S05-T025、D08-T004。邻面 01–08 analysis **已落盘**（`list_dir` 2026-08-29）；功能事实 **消费** 其 `NH-RA0X-B*` / `NH-C-01..79`，index §3.01–3.08 只作「叙事/初判」。
- **1.2 外部 / 参考来源 + 置信**：见每条 `RA-09-WEB-*`。搜索词与 primary URL 如下（访问日一律 `2026-08-29`）：

| 原子问题 | 搜索词 | 打开的 primary | 版本/发布 | 支持的原子结论 | 限制/失败条件 |
|----------|--------|----------------|-----------|----------------|----------------|
| idempotency key + replay conflict | `idempotency key HTTP original IETF` | `https://www.ietf.org/archive/id/draft-ietf-httpapi-idempotency-key-header-07.txt`（本轮核对；**-06 已过期** Expires 2025-08-28） | draft-07，2025-10-15，Expires **2026-04-18**；访问日 2026-08-29 时 **-07 亦已过期**；datatracker 标 Expired I-D | §2.6–2.7：同 key+fingerprint replay 返回原结果；并发未完成 → **409**；同 key 异 payload → **422**（-07 正文仍成立） | **过期 I-D，未成 RFC**；不得当现行规范。MKB 用 `task_uuid`+`creation_fingerprint`，不是 HTTP 头 |
| CAS / crash consistency | `compare-and-swap crash recovery Herlihy 1991` | 线索：https://en.wikipedia.org/w/index.php?title=Compare-and-swap&oldid=1366573606 ；权威应挂 Herlihy 1991 *Wait-Free Synchronization* / 数据库手册，**不占机制 RA** | wiki `oldid=1366573606` | CAS 只在期望值匹配时提交；ABA；persistent gap | **百科非论文原文**，降为线索。本仓是 SQL `rowcount` CAS 不是 CPU 指令 |
| exactly-once illusion | `at-least-once processing exactly-once illusion` | Confluent 设计文档 `https://docs.confluent.io/kafka/design/delivery-semantics.html`；Sequin 工程文 `https://blog.sequinstream.com/at-most-once-at-least-once-and-exactly-once-delivery/`（2024-09-29） | Kafka delivery-semantics；Sequin 博文 | EOS 是闭集内「效果一次」；出界 **不**保证；**无 exactly-once delivery** | 不得把 Kafka 事务栈借进 MKB；Sequin **只打 delivery 宣称**，不得支撑 MKB 机制 |
| workflow version compatibility tests | `Temporal workflow versioning testing official` | `https://docs.temporal.io/workflow-definition`；`https://docs.temporal.io/develop/safe-deployments` | 页面日期 2026-08-28 | 确定性 replay；非确定性变更须 pin 或 patch；**replay test** 用旧 Event History 跑新代码 | Temporal 事件史/Worker Versioning **不可**作本仓 runtime；只借「pin compiled plan + replay 旧史」 |
| fault injection / PBT 限度 | `fault injection property-based testing database invariants` | TigerBeetle Protocol-Aware DST (2026-08-20)；对照 Jepsen 外黑盒 | 2026-08-20 | 生成式+故障注入测安全/活性；黑盒测不到协议内不变量；DST 需确定性与协议可见性 | 本仓单体 FastAPI + local Turso，**不**引入分布式 DST 运行时；PBT 不能替代 default-root e2e |

- **1.3 ★ 可复现命令清单（measure-first）**：
```bash
git rev-parse --short HEAD   # 1221aa1

uv run python - <<'PY'
from intake import _REGISTERED_CLEAN
from intake.api.registry import REGISTERED_PROVIDER_OPERATIONS
from src.contracts.intake.strategies import CLEAN_STRATEGY_DEFINITIONS
from src.services.registry import DEFAULT_SEMANTICS, DEFAULT_SOURCE_KINDS
from src.workflows.builtin_scatter import (
    BUILTIN_REGISTERED_API_SCATTER_CHILD_WORKFLOW,
    BUILTIN_REGISTERED_API_SCATTER_ROOT_WORKFLOW,
)
from src.workflows.lsrag_definition import (
    BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW,
    BUILTIN_SOURCE_PROFILE_WORKFLOWS,
    SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS,
)
single = (BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW, *BUILTIN_SOURCE_PROFILE_WORKFLOWS)
public = set(SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS.values())
print("source_kinds", len(DEFAULT_SOURCE_KINDS))
print("clean_strategies", len(CLEAN_STRATEGY_DEFINITIONS))
print("clean_process_capabilities", len(_REGISTERED_CLEAN))
print("provider_operations", len(REGISTERED_PROVIDER_OPERATIONS))
print("single_root_identities", len(single))
print("public_selector_keys", len(SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS))
print("unselectable_single_identities", sum(x.workflow_key not in public for x in single))
print("scatter_identities", len((BUILTIN_REGISTERED_API_SCATTER_ROOT_WORKFLOW, BUILTIN_REGISTERED_API_SCATTER_CHILD_WORKFLOW)))
print("semantic_definitions", len(DEFAULT_SEMANTICS))
PY

# D-23 选定 clean/provider unit+intake
uv run pytest tests/unit/test_intake_provider_registry.py \
  tests/unit/test_intake_clean_dispatch.py tests/intake/test_web_clean.py \
  tests/intake/test_pdf_clean.py tests/intake/test_doc_clean.py -q --tb=no

# 本面附加：compat / GC TOCTOU / identity replay
uv run pytest tests/unit/test_workflow_revision_compatibility.py \
  tests/unit/test_ns6_gc_toctou.py tests/e2e/test_intake_identity_replay.py -q --tb=no

# D-24 / 本面复跑
uv run pytest tests/e2e/test_registered_api_scatter.py::test_registered_api_three_raw_provider_operations_map_seal_and_persist_semantics \
  tests/e2e/test_registered_api_scatter.py::test_registered_api_scatter_auto_zero_and_fanin_recovery \
  tests/e2e/test_registered_api_scatter.py::test_registered_api_scatter_collects_child_failure_before_parent_terminal -q --tb=line
uv run pytest tests/e2e/test_source_capability_paths.py::test_local_static_browser_and_pdf_sources_produce_distinct_frozen_acquisition_evidence -q --tb=short
```

本轮实测（2026-08-29）：分母脚本与 index `D-01..D-08/D-16` 一致；D-23 选定集 **33 passed**；compat+GC+identity-replay **4 passed**；API 三测 **2 passed / 1 failed**（fan-in 在 `sqlite3.connect` 检验处 `disk I/O error`）；source capability **1 failed**（`local` 在 8s 窗仍 `running`）。

- **1.4 范围围栏**：本面**只**覆盖横切 replay / CAS / crash window / compat / 防假绿证明分母；功能图代数、actual S05 schema 形态、representation 闭集、clean 合同、runtime 选型、upload 产品面、五维权威、publication 意图矩阵 **不在此设计**，只校验其失败法与测试格。`.experiment` 发车日 OPEN（`T-O-380`）。禁止 CF/R2/SMCP、第五 kind、caller `workflow_key`、cuts/g0 重开。

---

## 2. 当前结构分析（HEAD 实测 · measure-first）★ `[核心]`

### 2.1 ★ 冻结分母（FROZEN denominators · HEAD）

> 共享值只引用 index §2.2，不另估。本面新测另表。

| 分母 | HEAD 实测值 | 证据锚（`path:line`） | 来源 |
|------|-------------|------------------------|------|
| `D-02` CleanStrategyKey | `10` | `src/contracts/intake/strategies.py`；§1.3 脚本 | index §2.2 |
| `D-04` registered API operation | `3` | `intake/api/registry.py:73-104` | index §2.2 |
| `D-05` single-root Workflow identity | `13` | 脚本 `len(single)=13` = inline `lsrag_definition.py:612-714` + `BUILTIN_SOURCE_PROFILE_WORKFLOWS` `:943-1069`。index §2.2 锚 `614-714,943-1069`。**不**用 `:929-1070`（那是 selector map + 12 张 profile，不含 inline 定义） | index §2.2 |
| `D-06` public selector / unselectable | `7 / 6` | `lsrag_definition.py:929-940,1003-1069` | index §2.2 |
| `D-07` scatter Workflow identity | `2` | `src/workflows/builtin_scatter.py` | index §2.2 |
| `D-11` runtime CONTROL 实现 | `2`（human review / scatter join） | `src/runtime/workflow/runtime_materialize.py:505-514` | index §2.2 |
| `D-12` Execution actual S05 digest 字段 | `1`，`NOT NULL`，创建时由 **domain digest 填入** | `001_initial.sql:245-246`；`task_create.py:179-180` | index §2.2 · **本面核心反例** |
| `D-13` acquisition/decode evidence history | 单值 `1+1`；声明式 reacquire edge `0` | `acquisition_ingest.py:597-676` | index §2.2 |
| `D-15` S13 purpose / caller-upload purpose | `8 / 0` | `src/contracts/storage/models.py:18-27` | index §2.2 |
| `D-17` FilterMeta+tags semantic key | `6` | `src/contracts/intake/semantics.py:12-63` | index §2.2 |
| `D-19` public retrieval filter / FilterMeta facet | `3 / 0` | `src/services/retrieval/models.py:14-34` | index §2.2 |
| `D-21` 默认组合根 browser_fetcher / clean_llm | `0 / 0` | `api/app.py:330-345`；`src/runtime/intake/core.py:39-75` | index §2.2 |
| `D-23` 选定 clean/provider unit+intake | `33 passed / 0 failed` | 2026-08-29 复跑 §1.3 | index §2.2 · **本面确认** |
| `D-24` 三 provider e2e / source capability e2e | index 记 `1 passed / 1 failed` | 本面**复跑不得照抄**，见下表 | index §2.2 |

**本面新测分母（不得回写 index §2.2）**

| ID | 分母 | 本面实测 | 证据 | 命令 |
|----|------|----------|------|------|
| `D-09-01` | 选定 clean/provider 33 格 | `33 passed` | pytest 输出 33 dots | §1.3 D-23 命令 |
| `D-09-02` | API 三 provider map/seal/semantics | `1 passed` | `test_registered_api_scatter.py:209-296` | 命名用例 |
| `D-09-03` | API zero+fan-in recovery | `1 failed` · `sqlite3.OperationalError: disk I/O error` at `test_registered_api_scatter.py:367` | harness 在 TestClient **外**用 `sqlite3.connect` 打开 `persistence_backend="turso"` 文件 | 命名用例 |
| `D-09-04` | API child failure collect-all | `1 passed` | `test_registered_api_scatter.py:484-499` | 命名用例 |
| `D-09-05` | source local/static/browser/pdf e2e | `1 failed` · `local` 状态 `running` ≠ `succeeded`（8s 窗，`_await_terminal` `tests/e2e/test_source_capability_paths.py:58-68,166-168`） | monkeypatch 仍在 `99-101` | 命名用例 |
| `D-09-06` | workflow revision compatibility unit | `2 passed` | `tests/unit/test_workflow_revision_compatibility.py:105-194` | §1.3 |
| `D-09-07` | GC quarantine vs live-ref | `1 passed` | `tests/unit/test_ns6_gc_toctou.py:68-89` | §1.3 |
| `D-09-08` | intake identity replay 指针 | `1 passed` | `tests/e2e/test_intake_identity_replay.py:71-119` | §1.3 |
| `D-09-09` | `CLEAN_EMPTY` 测试命中 | `0` | `rg CLEAN_EMPTY tests` 空 | grep |
| `D-09-10` | `task-identity-conflict` 测试命中 | `0` | `rg task-identity-conflict tests` 空 | grep |
| `D-09-11` | 默认组合根注入 browser/clean_llm | `0 / 0` | `api/app.py:330-345` 未传 `browser_fetcher`/`clean_llm` | read |
| `D-09-12` | public object-upload route | `0` | `api/public/routes.py` `@router.` 28 条，无 upload/multipart | 与 `D-14` 一致 |

### 2.2 轴 fail-loud（绑定后失败即失败、不出向量）

- **正例（handler 层）**：web/pdf/doc 空正文抛 `CLEAN_EMPTY`（`intake/web/__init__.py:28-29,90`；`intake/pdf/__init__.py:59-60`；`intake/doc/__init__.py:20,74,97`）。API member `clean_text` `min_length=1`（`src/contracts/intake/semantics.py:44`）。preflight 空候选 `admission=rejected` / `clean_candidate_empty`（`src/runtime/intake/clean_preflight.py:544-547`）。未注入 browser **不**回退 static：`ACQUISITION_BROWSER_CAPABILITY_UNAVAILABLE` 503（`acquisition_ingest.py:477-485`；`core.py:67-70` 注释禁止 fallback）。未配置 OCR：source e2e 断言 `clean.ocr.local` `failed` + `CLEAN_OCR_CAPABILITY_UNAVAILABLE`（`test_source_capability_paths.py:220-272`）。
- **反例（证明/语义层）**：PDF 无字面量在 **decode** 抛 `CLEAN_OCR_CAPABILITY_UNAVAILABLE`（`types.py:154-158`）——`T-O-378` 谎言清单，`T-O-388` 要求 decode 只观察。创建时把 domain digest 写入 `s05_binding_digest`（`task_create.py:179-180`），与 glossary「创建时锁定 **actual** source/acquisition/clean/preflight」（`spec-glossary.md:231`）及 `S05-T025`（`S05-intake-cleaning.md:229`）冲突；QNA 已把该表面张力标为和解、把封闭时刻推迟到选边后（QNA `763-764` 行表 #4），**HEAD 代码尚未实现推迟封闭**。`CLEAN_EMPTY` 在 `tests/` **零命中**（`D-09-09`）。OCR 未部署的 503/失败关闭是诚实 fail-loud，但 **不是** `T-O-376` 通道 DoD——禁止用「能拒绝」代替 live-to-vector。
- **为什么是问题**：`T-O-383` 成功定义是「绑定后不换工人；内容失败显式失败、不出向量」。若 digest 在创建时已用 domain 值填满 `NOT NULL` 列，测试无法区分「未封闭」与「已封闭」；若 e2e 靠 monkeypatch 才绿，失败法只在假通道上成立。

### 2.3 轴 replay / idempotency

- Task 创建：先解析 idempotency identity，**exact replay 不**再 promote 对象（`task_create.py:67-85`）。同 `(team,task)` 同 fingerprint → 返回原视图 `replayed=True`；不同 fingerprint → `ConflictError("task-identity-conflict")`（`83-84,102-103,139-140`）。`ConflictError` HTTP 409（`src/contracts/common/errors.py:92-94`）。inline e2e：同 payload 二次 POST `200` 而非第二套 UoW（`test_inline_ingress_staging.py:85-88`）。
- Gate：`idempotency_key` 已存在则 `return False`（幂等）；revision 不匹配 → `gate-revision-conflict`（`runtime_gates.py:51-59`）。e2e `test_human_review_gate.py:167-174` 断言 `idempotent is True`。
- Intake 身份：同 `external_key` + 同内容 replay **不得**悬空 `latest_revision_uuid`（`test_intake_identity_replay.py:1-6,71-119`，本面复跑通过）。
- 缺口：`tests/` **没有** `task-identity-conflict` 用例（`D-09-10`）。上传 replay（`T-O-385` 同 team+sha256+size → 同一 handle）无 public 面可测（`D-14/D-15`）。IETF draft 的「并发未完成 → 409」在 Task 创建路径有 IntegrityError 回收（`task_create.py:130-141`），但缺并发测试。

### 2.4 轴 CAS / 竞态 / crash window

HEAD 已有多处 `row_revision` / `rowcount` CAS，不是「最后写赢」：

| 窗口 ID | 窗口 | HEAD 机制 | 证明水位 | 映射外部机制 |
|---------|------|-----------|----------|--------------|
| `W-SEL` | 清洁边选定前 | 无独立「未封闭」状态；`s05_binding_digest` 创建即 NOT NULL | **缺** | 选边前崩溃应恢复到未封闭，不得假装已绑工人 |
| `W-PROM-CAT` | promote 后、catalog 前 | Task 双事务：先查 identity，再 prepare/catalog（`task_create.py:70-92` 注释：并发赢家原子；预 promote 字节作 S13 orphan） | 注释+代码；缺 crash 注入测 | CAS 失败不得把 orphan 当业务成功 |
| `W-CHILD-FANIN` | 子证明已终、父投影前 | scatter 用 Snapshot/ChangeSet 分母而非队列空（`test_registered_api_scatter.py:323-326`；`runtime_scatter.py:320-322`） | 产品断言或已跑；**检验红** sqlite3-on-Turso | at-least-once wake + 幂等终态 |
| `W-GATE` | decision 与 execution wait | gate revision + waiting_ref CAS（`runtime_gates.py:57-65`） | e2e 人审门存在 | IETF 409 进行中 |
| `W-OUTCOME` | handler 成功 vs Outcome CAS | 成功须 output+proof；`rowcount!=1` → `stale-process-fence`（`runtime_outcome.py:62-117`） | unit 有部分；缺 crash 在 commit 后 | exactly-once **效果**，不是 delivery |
| `W-OUTBOX` | outbox 可投递多次 | vectorize construct consumer **无业务副作用**（`runtime_outbox.py:131-139`） | 代码正例 | at-least-once delivery + idempotent processing |
| `W-PUB` | publication alias 切中 | `IndexGenerationRetirementService` 切后 grace，再核活指针（`index_retirement.py:1-7`） | lifecycle/rebuild e2e 部分；retrieval 缺 namespace | 切中崩溃不得双 serving |
| `W-GC-INGEST` | grace 内 upload/ingest vs GC | 无抢先 tombstone；quarantine 后二次 fence；live-ref 则 restore（`object_gc.py:189-240`；`test_ns6_gc_toctou.py:68-89` **绿**） | unit 正例；**无 public upload 并发** | persistent visibility gap |
| `W-RETRY` | retry/recovery 热切 | `_assert_execution_binding` 用 **存储 compiled_digest** 而非 active 图（`runtime_core.py:591-621`） | compat unit 绿 | Temporal pin |

ABA 风险：CAS 比较 `row_revision` 单调递增（DDL `001_initial.sql:253`），降低指针回收式 ABA；仍须禁止「读-改-写不带 expected revision」的公共命令（`task_commands.py:142-144` `revision-conflict`）。

### 2.5 轴 兼容迁移（old pinned + new kind graph）

- **已有**：`WorkflowRegistryService.register` 同 revision 指纹冲突则 `REGISTRY_DIGEST_MISMATCH`；新 revision **插入**、不原地改旧行（`workflow_registry.py:153-211`）。历史 v1/v2 图在 `lsrag_historical.py:60-67`。NS1 pre-markdown compat 由现行定义 `revision_number-1` 派生（`lsrag_definition.py:1073-1080`）。`api/app.py:296-304` 把 `BUILTIN_SOURCE_PROFILE_WORKFLOWS` 作 `additional_definitions`，`BUILTIN_EXECUTION_COMPATIBILITY_WORKFLOWS` 作 `compatibility_definitions`。runtime 按 Execution 存储 digest 取 plan；未知 digest → `workflow-compiled-plan-unavailable` 且 **不**物化 Process（`runtime_core.py:615-621`；`test_workflow_revision_compatibility.py:174-192`）。
- **未有**：kind 家族（`T-O-387` 三张 single-root）相对今日 13 身份 + 7/6 公开/不可选（`D-05/D-06`）的 **联合**验证：部署新 kind 图后，（a）旧 pinned Execution 仍按旧 compiled digest 跑完；（b）新 Task 不得解析到旧 profile key；（c）compat 表必须 **显式收录** 被合并的旧 `workflow_key`/revision，而不是靠 handler 暗升。今日 compat 测的是 markdown/index-rebuild 历史，**不是** kind 合并。

### 2.6 轴 测试分层与假绿

| 层 | HEAD 现状 | 假绿模式 |
|----|-----------|----------|
| 单元 | D-23 33 绿；compat/GC 绿 | 纯函数绿 ≠ 通道 live |
| 集成 / binding | Task fingerprint、gate idempotency、lifecycle CAS 有测 | 缺 identity-conflict、缺 actual S05 封闭 |
| default-root e2e | API scatter 部分绿；source 红；inline 绿 | `pipeline._http_fetcher` / `_browser_fetcher` 赋值（`test_source_capability_paths.py:99-101`）；`persistence_backend="turso"` + `sqlite3.connect`（多份 e2e）；8s 超时把 `running` 当失败但仍是假进度 |
| retrieval / facet mega | 若干 e2e 打 `/retrieval:search` **不带** `namespace_key`（`test_single_intake_pipeline.py:121-130`；`test_intake_reactivate.py:102-115`；`test_intake_rebuild_metadata.py:229-238`）；服务端强制 namespace（`retrieval_request.py:265-269`） | README K1：5 个检索用例未带必填 namespace；facet key `D-19=0`；「Task succeeded」或 `publication_ready`（scatter 子成功父失败，`test_registered_api_scatter.py:496-499`）≠ 可检索 |

`T-O-380`：unit/e2e 属于 completeness；**.experiment 发车日不冻**。本面验收格栅不得把实验骨架当退出条件。

### 2.7 必须回答（本面五问）

#### Q1. 每面最少哪组 failure/replay/race tests 才能冻结？

> 通道是验收格，不是施工包：公共机制（fingerprint、CAS、empty-clean、compat pin）**只测一次**；各面只补 **本面拥有的** crash window。`禁止 monkeypatch` 列针对 **default-root e2e / mega**；单元允许 fixture。

| 面 | 单元（允许 fixture） | 集成 / binding（允许注入 port，禁止改生产路由） | default-root e2e（**禁止** monkeypatch http/browser/ocr/llm） | retrieval/facet mega（禁止 503/空正文当成功） |
|----|----------------------|-----------------------------------------------|--------------------------------------------------------------|-----------------------------------------------|
| `01` 图代数 | 无环/自边/单 binding 编译失败；未知 guard 拒 | 新 revision 不改旧行；未知 compiled digest 拒物化 | 非法图 **不能** 被默认 app 注册成功 | n/a（图不是检索） |
| `02` S05 binding | 未封闭 vs 已封闭状态机纯函数 | seal 与 route outcome 同事务；封闭后 retry 重放封闭 digest | 选边前崩溃 → 未封闭；选边后崩溃 → 不换工人 | 失败 Execution 向量不可检索 |
| `03` representation | MIME mismatch、无层观察、print_pdf 种类 | evidence history digest（今 `D-13=单值`） | 真 PDF / 空壳 HTML **无** monkeypatch | n/a |
| `04` clean | `CLEAN_EMPTY`；strategy/capability mismatch；API empty member 拒 | admitted clean digest 进入 g0 | 默认根跑通确定性 web/pdf；LLM 策略缺注入 **失败** 而非空成功 | 空 clean 无向量 |
| `05` runtime | readiness 缺二进制 → 不可用码 | 隔离边界（不测库选型） | 未部署 = 稳定拒绝；**部署后** 无补丁 e2e | n/a |
| `06` upload | digest/size 合同 | catalog-without-Item；orphan grace | 公共上传 replay/冲突；**无** ingest 不创造 Item | n/a |
| `07` semantics | stub `source_kind` 不得当五维 | 非 API 写入权威 | 四通道写入六键 | facet 过滤命中/未命中 |
| `08` publication | 七意图 applicability 表（纯数据） | lifecycle CAS；rebuild 不重 clean | 意图终态 | 「可检索」= query + facet + proof |
| `09` 横切（本面） | identity-conflict；CAS rowcount | crash 窗口清单 W-* | 无 monkeypatch 的失败+重放+竞态 | mega 矩阵按通道展开 |

**禁止 fixture 的格子**：default-root e2e 与 mega 的 **成功路径**不得用 monkeypatch 冒充 browser/http/ocr；**允许**的 fixture：API **冻结 records**（已是 HEAD 正例）、纯函数输入、通过 **构造注入** 的 unit（`D08-T004`）。Recovery 测试允许在 **PersistencePort** 上制造 crash 状态，**禁止** `sqlite3.connect` 打开 Turso 文件当绿（`NS1-V11` / README K1）。

#### Q2. old pinned + new kind graph 如何共同验证？

最小共同验证包（草案，非冻结实现）：

1. **Pin**：Execution 行保存 `workflow_revision_uuid` + `compiled_digest`；runtime 只从 `compatibility_definitions ∪ active` 按 digest 取 plan（已有）。
2. **Register**：新 kind 图以 **新 `workflow_key` 或新 `revision_number`** 插入；旧行指纹不变（已有 register 法）。
3. **联合测 A**：种子一个旧 profile Execution（今日 `http_resource.static` 等 key），部署 kind 家族后 `materialize_root` 仍走出 **旧** `process_key` 序列（类比 `test_workflow_revision_compatibility.py:105-169`）。
4. **联合测 B**：新 Task 按 `source_kind` 选 **新** 图，不得 `resolve_by_key` 到已合并的旧 selector。
5. **联合测 C**：故意丢掉 compat 定义 → `workflow-compiled-plan-unavailable` 且 `mkb_processes` 仍空（已有 fence 测，须扩到 kind 旧 digest）。
6. **禁止**：decode 后换 revision（QNA 已否 Q4-C）；handler 写假 `browser_profile`（`T-O-378`）。

Temporal Worker Versioning / Event History replay **不可**作本仓引擎（substrate-fit 失败）；只借「旧史必须能在新二进制上重放或显式 pin」这一失败法。

#### Q3. 哪些测试允许 fixture，哪些禁止 monkeypatch？

| 允许 | 禁止 |
|------|------|
| 单元：构造的 HTML/PDF bytes、provider **frozen records** | 把 `pipeline._browser_fetcher = lambda` 写入 **e2e 成功路径**（`test_source_capability_paths.py:101`） |
| `tests/intake/*`：构造注入 `HttpFetch`/`CleanLanguageModel`（`D08-T004`） | e2e monkeypatch 生产 `create_app()` 的 http/browser/ocr 后称「通道接通」（`T-O-378`） |
| crash 注入：经 PersistencePort / 测试专用 harness 改 status | `sqlite3.connect` 打开 `persistence_backend="turso"` 文件（K1 / `NS1-V11`） |
| gate/task 的 `idempotency_key` 字符串 fixture | 空 `clean_text` 当 succeeded |
| | 503 当通道 DoD（`T-O-376`） |
| | `.experiment` 发车当 completeness（`T-O-380`） |

#### Q4. 绑定后 fail-loud（`T-O-383`）在 upload、未封闭 binding、空 clean、OCR 未部署上的最小证明

| 场景 | 最小可验证 | 今日水位 |
|------|------------|----------|
| 公共上传 | 同 team+sha256+size → 同一 handle（replay）；异 fingerprint/冲突码；**不**创造 Item/Revision；无 ingest 对象可被 GC | **无 route**（`D-14=0`）；CAS 内核在 `local_store.py:71-105` |
| 未封闭 binding | 存在合法非 sealed 状态；此时失败/崩溃 **不**写出 `s05_binding_digest` 的「已绑工人」含义；封闭后 retry 不换边 | HEAD 创建即写 NOT NULL domain digest（`task_create.py:180`） |
| 空 clean | `CLEAN_EMPTY` 或 preflight `clean_candidate_empty`；Task/Process 失败；**无**向量行 | handler 有；**测试 0**；API member schema 有 `min_length=1` |
| OCR 未部署 | typed `CLEAN_OCR_CAPABILITY_UNAVAILABLE`（或未来观察事实 + 清洁边失败）；**禁止** decode 盗用该码；**禁止**用该失败宣称 `T-O-381` 格子完成 | OCR e2e 失败关闭是正例（`test_source_capability_paths.py:220-272`）；decode 盗码是反例（`types.py:154-158`） |

#### Q5. mega 矩阵如何按通道展开而不把通道当施工包？

- **列** = 测试层（单元 / 集成 / default-root e2e / retrieval-facet）。
- **行** = `T-O-381` 闭集格子（10 strategy + 3 API operation + 七意图 applicability），**不是**四个独立施工包。
- **共享列先测一次**：fingerprint、ConflictError、CAS、empty-clean、compat pin、GC fence——属本面。
- **通道行只填差**：acquire 起点、representation 观察、strategy 证据、facet 键。
- 0815-R7 inline 4/4 **不得**列入（`T-O-376`）。
- 每格产品终态：「可检索」必须包含 query 命中 **且** traceback resolved **且** facet（`D-19` 今日 0）。`publication_ready` 单独不足。

---

## 3. 借鉴锚定矩阵（Reference Anchor Matrix）★ `[核心]`

> 每个可借鉴点钉到 `path:line` / URL，给**借鉴 verdict**。**这是「能借什么」的台账，不是设计决策。**

| 借鉴点 | 来源锚（`path:line` / URL） | 借鉴 verdict | 借什么 / 不借什么 |
|--------|------------------------------|--------------|--------------------|
| Task 指纹双检 + replay 原视图 | `src/runtime/task/task_create.py:67-85` | `✅借` | 借「先解析 identity、exact replay 不第二套 UoW」。不把 audit 时钟字段纳入 fingerprint 的未来改动当已冻。 |
| 同 identity 异 fingerprint → 409 | `task_create.py:83-84,102-103,138-140`；`errors.py:92-94` | `✅借` | 借 typed `task-identity-conflict`。不借「测试已覆盖」——`tests/` 零命中。 |
| 无环图 + 终端覆盖，编译期拒 | `src/contracts/workflow/models.py:327-460,389-432` | `✅借` | 借注册前失败。不借把无环当 kind 合并已完成。 |
| scatter fan-in 用 Snapshot 分母 | `runtime_scatter.py:320-338`；`test_registered_api_scatter.py:323-326` | `✅借` | 借 crash-after-children 修复思路。不借 sqlite3 检验当绿。 |
| 子失败 collect-all，父 failed | `test_registered_api_scatter.py:470-499`（本面复跑 passed） | `✅借` | 借 required-child 失败码。不借「sibling `publication_ready` ⇒ 任务可检索」。 |
| pinned compiled digest + 未知 plan 拒物化 | `runtime_core.py:591-621`；`test_workflow_revision_compatibility.py:105-192`；`api/app.py:296-304` | `✅借` | 借 pin 与 fence。不借历史 markdown compat 覆盖 kind 家族。 |
| 空正文 fail-loud（handler） | `intake/web/__init__.py:28-29`；`semantics.py:44`；`clean_preflight.py:544-547` | `✅借` | 借空成功禁令。不借「已有测试」。 |
| 缺 browser 不静默降级 | `acquisition_ingest.py:477-485`；`core.py:67-70` | `✅借` | 借 fail-closed。不借 503 当通道完成。 |
| Gate / Process / object CAS | `runtime_gates.py:51-59`；`runtime_outcome.py:46-117`；`local_store.py:71-105`；`001_initial.sql:1800-1801` | `✅借` | 借 expected-revision + rowcount。不把 CPU CAS 论文当本仓 API。 |
| GC vs live-ref restore | `object_gc.py:189-240`；`test_ns6_gc_toctou.py:68-89` | `✅借` | 借 quarantine 窗口。不借「已有 public upload 竞态证明」。 |
| intake 身份 replay 指针 | `tests/e2e/test_intake_identity_replay.py:71-119` | `✅借` | 借 NS9-FX2。须扩到四通道+上传。 |
| outbox at-least-once 无副作用 | `runtime_outbox.py:131-139` | `✅借` | 借「投递多次、效果一次」的本地形态。 |
| domain digest 冒充 actual S05 | `task_create.py:179-180`；`runtime_core.py:888-915` | `⛔反例` | 避开：创建时写满 actual 列。ProcessCommand `binding_digest=domain_binding_digest`。 |
| monkeypatch browser e2e | `tests/e2e/test_source_capability_paths.py:99-101` | `⛔反例` | 避开：补丁当接线（`T-O-378`）。 |
| sqlite3-on-Turso 检验 | `test_registered_api_scatter.py:26-33,327,366-367`；README `610` | `⛔反例` | 避开：用 sqlite3 打开 Turso 文件当绿。 |
| source e2e 停在 running | `test_source_capability_paths.py:58-68,166-168`（本面复跑 `running`） | `⛔反例` | 避开：超时窗假进度。 |
| decode 盗用 OCR 码 | `src/runtime/intake/types.py:154-158` | `⛔反例` | 避开：无层 ≠ OCR 未部署。 |
| retrieval 无 namespace / facet 0 | `retrieval_request.py:265-269` vs e2e `test_single_intake_pipeline.py:121-130`；`D-19` | `⛔反例` | 避开：检索 200 无 namespace 当 mega。 |
| 默认根未注入 | `api/app.py:330-345`；`D-21` | `⛔反例` | 避开：单测绿 = 通道 live。 |
| dedicated parser catch 后 skip | `context/legacy-family/smind-skill-clean-dedicated-apis/providers/chinatax/processor.ts:150-154`；`domain/processor.ts:168-172`；`realestate/processor.ts:284-286` | `⛔反例` | **不借** silent skip。本仓必测：parser 失败 → typed rejection，required member 阻断 root。 |
| `plainTextAvailable: true` 无非空检查 | `smind-skill-clean-universal/services/cleaner_web.ts:321-322`；`cleaner_doc.ts:140-141` | `⛔反例` | **不借** 空成功。映射 `CLEAN_EMPTY` 测试格。 |
| finalizer 以 R2 key 推成功 | `smind-clean-dispatcher/flows/finalizer.ts:106-129` | `⛔反例` | **不借**「有 output key = clean_completed」。本仓须 Outcome proof + 非空 admitted clean。 |
| restarter 先入队再写库 | `smind-clean-dispatcher/services/restarter.ts:785-814,850-853` | `⛔反例` | **不借** 队列先发（重复副作用窗口）。本仓 outbox 可重投但 handler 必须幂等。 |
| D08 禁 silent skip / 空成功 | `D08-legacy-capabilities-migration.md:95,99` `D08-T004/T008` | `✅借`（仓内基线） | 借禁令。测试分层见 `D08-T011`（unit / per-domain / e2e）。 |
| IETF Idempotency-Key | draft-06 §2.6–2.7 URL 见 §1.2 | `🔶部分借` | 借 replay vs 409 vs 422 分账。不借 HTTP 头、过期策略、RFC7807 体为已冻 API。**规范草案单源**（同系列无第二 IETF 头标准）。 |
| CAS + ABA + persistent gap | Wikipedia Compare-and-swap（`RA-09-WEB-02` 线索） | 线索，**不**占机制 | 百科非论文。SQL `row_revision` 已是本仓形态；不借 DCAS/HTM。 |
| Kafka EOS 边界 | Confluent 2017/2025 博文 | `🔶部分借` | 借「exactly-once 只在闭集；出界 RPC 不保证」。**不借** Kafka 事务/Streams。 |
| 无 exactly-once delivery | Sequin 2024-09-29 | `⛔反例`（对「宣称 exactly-once 投递」） | 借用语：at-least-once 投递 + 幂等处理。不把邮件/双提交幻觉写成本仓已实现 EOS。 |
| Temporal replay test | `docs.temporal.io/develop/safe-deployments`；Workflow Definition 确定性 | `🔶部分借` | 借「用旧史跑新代码 / pin 旧 Worker」。**不借** Temporal SDK、Event History、Worker Versioning 栈（`T-O-42` / 单体约束）。 |
| DST / PBT 限度 | TigerBeetle 2026-08-20；对照 Jepsen 外黑盒 | `🔶部分借` | 借「黑盒生成测不到协议内不变量；crash 窗口要内建断言」。不借 VOPR/仿真器进本仓。PBT **不能**替代 default-root e2e。 |
| kind 图 × 旧 pin 的联合套件 | 三渠道均无 MKB 同构先例 | `🆕净新` | 见 §6 `NH-N-09-03`。 |
| 未封闭 actual S05 状态 + 上传同一失败法的证明包 | 无 substrate-fit 先例（创建时 NOT NULL 列 vs QNA 推迟封闭） | `🆕净新` | 见 §6 `NH-N-09-04`。 |

**RA 原子记录（结论 / 来源 / 正反 / 置信 / substrate-fit / 缺口）**

| RA-ID | 结论原子句 | 来源与版本或访问日 | 正/反 | 置信 | substrate-fit | 命中缺口 |
|-------|------------|-------------------|-------|------|---------------|----------|
| `RA-09-HEAD-01` | 同 Task 指纹重放返回原视图且不第二套 promote | HEAD `task_create.py:67-85` + `test_inline_ingress_staging.py:85-88` | 正 | HEAD 实测 | ✅复用 | 扩到上传 `NH-RA09-B05` |
| `RA-09-HEAD-02` | 异指纹 → `ConflictError` 409 | `task_create.py:83-84`；`errors.py:92-94` | 正 | HEAD 实测 | ✅复用 | 测试缺 `NH-RA09-B09` |
| `RA-09-HEAD-03` | 环/自边/无终端覆盖 → 定义校验失败，不能注册 | `models.py:389-432,345,449-460` | 正 | HEAD 实测 | ✅复用 | `NH-RA09-B07` 不覆盖 kind |
| `RA-09-HEAD-04` | fan-in 修复以 Snapshot/ChangeSet 为准 | `runtime_scatter.py:320-322`；e2e 注释 `323-326` | 正 | HEAD 代码高 / 测试红 | ✅复用机制 | `NH-RA09-B10` |
| `RA-09-HEAD-05` | 一子失败则父 `scatter-required-child-failed`，兄弟可 publication_ready | e2e `484-499` 本面 passed | 正 | HEAD 实测 | ✅复用 | 须防「父失败仍检索兄弟」`NH-RA09-B04` |
| `RA-09-HEAD-06` | 运行时按 pinned compiled digest 物化；未知 plan 不插 Process | `runtime_core.py:615-621`；compat 测 `174-192` 绿 | 正 | HEAD 实测 | ✅复用 | `NH-RA09-B07` |
| `RA-09-HEAD-07` | 空 admitted clean 在 handler/schema/preflight 被拒 | `web/__init__.py:28-29`；`semantics.py:44`；`clean_preflight.py:544-547` | 正 | HEAD 代码 | ✅复用 | 测试 0 `NH-RA09-B09` |
| `RA-09-HEAD-08` | 未配置 OCR 走 exact `clean.ocr.local` 后失败关闭 | `test_source_capability_paths.py:220-272` | 正 | HEAD 实测 | ✅复用 | 非 live DoD `NH-RA09-B06` |
| `RA-09-HEAD-09` | Gate 决策幂等键 + revision CAS | `runtime_gates.py:51-59` | 正 | HEAD 实测 | ✅复用 | 扩到新路径 |
| `RA-09-HEAD-10` | 终态 Process 拒不同 outcome；成功须 proof | `runtime_outcome.py:46-117` | 正 | HEAD 代码 | ✅复用 | crash 注入不足 `NH-RA09-B14` |
| `RA-09-HEAD-11` | 同 digest 字节 promote 幂等；碰撞 503；catalog unique(team,digest,size) | `local_store.py:84-105`；`001_initial.sql:1800-1801` | 正 | HEAD 代码 | ✅复用 | 无 public 面 `NH-RA09-B05` |
| `RA-09-HEAD-12` | GC quarantine 中出现 live-ref 则 restore、不 tombstone | `object_gc.py:189-240`；GC 测绿 | 正 | HEAD 实测 | ✅复用 | 无 ingest 并发 `NH-RA09-B14` |
| `RA-09-HEAD-13` | 同键同内容 replay 保持 revision 指针可解析 | identity replay e2e 绿 | 正 | HEAD 实测 | ✅复用 | 未覆盖新通道 |
| `RA-09-HEAD-14` | outbox 可多次投递且该 consumer 无业务副作用 | `runtime_outbox.py:131-139` | 正 | HEAD 代码 | ✅复用 | 映射 W-OUTBOX |
| `RA-09-HEAD-15` | **反** 创建时 `s05_binding_digest=domain_binding_digest` | `task_create.py:179-180`；DDL `245-246` | 反 | HEAD 实测 | ⛔ | `NH-RA09-B01` |
| `RA-09-HEAD-16` | **反** ProcessCommand.binding_digest 取 domain | `runtime_core.py:888-915` | 反 | HEAD 实测 | ⛔ | `NH-RA09-B12` |
| `RA-09-HEAD-17` | **反** e2e 赋值 `_browser_fetcher` | `test_source_capability_paths.py:99-101` | 反 | HEAD 实测 | ⛔ | `NH-RA09-B02` |
| `RA-09-HEAD-18` | **反** Turso 文件上 sqlite3.connect | scatter 测 `26-33,367`；README `610` | 反 | HEAD 实测 | ⛔ | `NH-RA09-B10` |
| `RA-09-HEAD-19` | **反** source e2e local 停 running | 本面复跑 `166-168` | 反 | HEAD 实测 | ⛔ | `NH-RA09-B03` |
| `RA-09-HEAD-20` | **反** decode 无层抛 OCR 未部署码 | `types.py:154-158` | 反 | HEAD 实测 | ⛔ | `NH-RA09-B06` |
| `RA-09-HEAD-21` | **反** 默认根 browser/clean_llm=0 | `api/app.py:330-345` | 反 | HEAD 实测 | ⛔ | `NH-RA09-B15` |
| `RA-09-HEAD-22` | **反** retrieval e2e 不供 namespace | `test_single_intake_pipeline.py:121-130` vs `retrieval_request.py:265-269` | 反 | HEAD 实测 | ⛔ | `NH-RA09-B04` |
| `RA-09-HEAD-23` | **反** public upload 0 | `api/public/routes.py` 无 upload | 反 | HEAD 实测 | ⛔ | `NH-RA09-B05` |
| `RA-09-HEAD-24` | **反** `CLEAN_EMPTY`/`task-identity-conflict` 测试 0 | grep `tests/` | 反 | HEAD 实测 | ⛔ | `NH-RA09-B09` |
| `RA-09-LEGACY-01` | dedicated 单 member parse 失败 warn+return null/skip | chinatax `processor.ts:150-154` 等 | 反 | legacy-family 读码 | ⛔不回流 | 映射测试格 `NH-A-09-04` |
| `RA-09-LEGACY-02` | universal 写完 output 即 `plainTextAvailable: true` | `cleaner_web.ts:321` | 反 | 读码 | ⛔ | `NH-RA09-B09` |
| `RA-09-LEGACY-03` | finalizer 有 `cleaned_content_r2_key` 即 `clean_completed` | `finalizer.ts:116-129` | 反 | 读码 | ⛔ | 防假绿 §9 |
| `RA-09-LEGACY-04` | restarter 先 `sendStepDispatch` 再插/更新步骤行 | `restarter.ts:812-814` | 反 | 读码 | ⛔重复副作用 | `W-RETRY` |
| `RA-09-BASELINE-01` | D08 **草案**禁 silent skip / 空成功；测试分三层 | `D08-legacy-capabilities-migration.md:8-9,16` `D08-T004/T008/T011` | 正（基线禁令） | 仓内 **draft / owner-review**（未 owner-freeze），不覆盖 QNA/HEAD | ✅借禁令句，不把 D08 升格 frozen；不借 Worker | `NH-C-88` |
| `RA-09-WEB-01` | 同 key+fingerprint 应返回原结果；并发未完成 409；异 payload 422 | IETF **draft-07** §2.6–2.7（https://www.ietf.org/archive/id/draft-ietf-httpapi-idempotency-key-header-07.txt）；访问 2026-08-29。**-06 已过期**；**-07 Expires 2026-04-18，访问日亦过期** | 正（语义） | **过期 I-D**，未成 RFC | 🔶部分借 | `NH-RA09-B09` |
| `RA-09-WEB-02` | （线索，不占机制）CAS 匹配才写；ABA | Wikipedia `oldid=1366573606` https://en.wikipedia.org/w/index.php?title=Compare-and-swap&oldid=1366573606 ；应改挂 Herlihy 1991 | 线索 | 百科非论文 | 线索，**不**支撑 MKB 机制 | `W-*` |
| `RA-09-WEB-03` | EOS 是闭集效果一次；出界不保证 | `https://docs.confluent.io/kafka/design/delivery-semantics.html`（与面 02 对齐），访问 2026-08-29 | 正/限 | 官方设计文档 | 🔶部分借 · 不借栈 | `NH-C-80` |
| `RA-09-WEB-04` | 跨两处物理提交无法 100% exactly-once **delivery** | `https://blog.sequinstream.com/at-most-once-at-least-once-and-exactly-once-delivery/` 2024-09-29 | 反（对 delivery 宣称） | 工程博客 | **⛔宣称**；禁止当 MKB 机制 | `W-OUTBOX` |
| `RA-09-WEB-05` | 新代码必须用旧 Event History replay 或 pin，否则非确定性错误 | Temporal Safe Deployments / Workflow Definition，2026-08-28 页，访问 2026-08-29 | 正 | 官方文档 | 🔶部分借 · 不借引擎 | `NH-RA09-B07` |
| `RA-09-WEB-06` | Eager start 可忽略 Worker versioning（官方限制） | Temporal Safe Deployments caution | 反/限 | 官方 | ⛔勿照搬部署模型 | 本仓无 Temporal |
| `RA-09-WEB-07` | 黑盒生成+故障注入测不到协议内不变量 | TigerBeetle DST 2026-08-20，访问 2026-08-29 | 正/限 | 官方工程 | 🔶部分借 · 不借仿真器 | `NH-RA09-B14` |
| `RA-09-WEB-08` | PBT/FI 是补充不是替代；须先写不变量 | TigerBeetle + 搜索包内 ACM FI+PBT 2013 线索 | 限 | 中 | 🔶 | §9 不把 PBT 当 mega |

---

## 4. 缺口 / 断点台账 ★ `[核心]`

> 编号稳定。邻面功能缺口只 **引用** index 初判 ID 叙事，不改写。

| 编号 | 缺口 / 断点 | 严重度 | 证据（`path:line`） | 影响 |
|------|-------------|--------|----------------------|------|
| `NH-RA09-B01` | **消费** `NH-RA02-B01`：actual `s05_binding_digest` 创建时用 domain digest 填满 NOT NULL 列。本面只负证明义务（`NH-A-09-10/11`），不重开 binding 设计 | `S1 阻断`（横切证明） | `task_create.py:179-180`；`001_initial.sql:245-246`；功能权威在面 `02` | 无法证明选边后封闭 / 封闭后不换工人；与 `T-O-384/388` 及 `G-NH-01` 直接相关 |
| `NH-RA09-B12` | ProcessCommand 只携带 `domain_binding_digest` | `S1 阻断` | `runtime_core.py:888-915` | retry/recovery 热切风险；与 B01 同根 |
| `NH-RA09-B02` | e2e monkeypatch browser/http 冒充接线 | `S1 阻断` | `test_source_capability_paths.py:99-101`；`T-O-378` | 假绿；不能冻 default-root |
| `NH-RA09-B03` | source capability e2e 停在 `running` | `S1 阻断` | 本面复跑 `test_source_capability_paths.py:166-168`；8s 窗 `:58-68` | `D-24` 红灯属实，非抄写 |
| `NH-RA09-B15` | **消费** `NH-RA05-B01`：默认组合根 browser/clean_llm 未注入。本面只证「无注入则 default-root 不能绿」 | `S1 阻断`（横切证明） | `api/app.py:330-345`；`D-21`；供给权威在面 `05` | 无 monkeypatch 的成功路径不存在 |
| `NH-RA09-B04` | retrieval/facet mega 未成立：无 namespace、facet=0、R7 inline 不可顶替 | `S1 阻断` | `retrieval_request.py:265-269`；e2e 检索体无 namespace；`D-19=0` | 「可检索」未证明；K1 |
| `NH-RA09-B05` | **消费** `NH-RA06-B01`：公共上传面 0，上传幂等/冲突法无 API 可测。本面只证横切 replay 窗 | `S1 阻断`（横切证明） | `api/public/routes.py`；`D-14/D-15`；功能权威在面 `06` | `T-O-376` 闭集缺上传 |
| `NH-RA09-B06` | fail-loud 最小四格（upload / 未封闭 / 空 clean / OCR 未部署）未闭合 | `S1 阻断` | 上表 Q4；`types.py:154-158`；`D-09-09` | `T-O-383` 不能冻 |
| `NH-RA09-B07` | old pinned × **kind 家族新图**联合验证缺失 | `S1 阻断` | compat 测只覆盖历史 markdown/index（`lsrag_historical.py` / `test_workflow_revision_compatibility.py`）；`D-05/D-06` 仍是 13+7/6 | kind 迁移可把 in-flight Execution 卡死或暗切图 |
| `NH-RA09-B08` | 每面冻结所需 failure/replay/race 格栅未落地 | `S1 阻断` | index §8.1 Wave C；01–08 analysis **已落盘**但格栅测试目录仍无；须 **引用** 各面 `NH-A-0X-*` 再汇总 | Wave C 无法冻结 |
| `NH-RA09-B09` | `CLEAN_EMPTY` 与 `task-identity-conflict` 无测试命中 | `S2 重要` | grep `tests/` 空 | 失败法只在生产函数，防回归不足 |
| `NH-RA09-B10` | sqlite3-on-Turso 使 recovery 检验红 | `S2 重要` | `test_registered_api_scatter.py:367` 本面 `disk I/O error`；README `610` | 不得把产品 fan-in 称为已证明绿 |
| `NH-RA09-B11` | exhausted-zero API Task `succeeded` counts 全 0 | `S2 重要` | `test_registered_api_scatter.py:352-364` | 与 `G-NH-08` 相关；是否违反「空不是成功」待裁决，本面不裁 |
| `NH-RA09-B13` | ~~01–08 未落盘~~ **关闭（事实过期）**：9 份 analysis 均在盘；缺口改为「已落盘但 v0.1 未引用 gap ID」。本 v0.2 改为消费 `NH-RA0X-B*` | `S3 次要`（过程债） | `list_dir docs/eval/new-harvest/reference-anchor/` 2026-08-29 | 不得再用「无文件」给横切汇总假红通行证 |
| `NH-RA09-B14` | crash window 覆盖不完整（W-SEL / W-PROM-CAT / W-PUB 缺注入） | `S2 重要` | `task_create.py:179-180`（无未封闭态）；`index_retirement.py:1-7`（切后 grace 无 crash e2e）；`test_ns6_gc_toctou.py:68-89` 仅 GC 一窗 | 竞态只在部分窗口有测 |
| `NH-RA09-B16` | 实验发车日 OPEN，易被误当 DoD | `S3 次要` | `T-O-380` | 规划须隔离 `.experiment` |

**邻面 S1（已落盘，本面只消费）**：`NH-RA01-B01/B04` selected-output merge；`NH-RA02-B01/B03` s05 冒充 / ProcessCommand；`NH-RA03-B02/B13` print_pdf 死键 / monkeypatch e2e；`NH-RA04-B01` 未选中 LLM/print 图；`NH-RA05-B01` 默认根未注入；`NH-RA06-B01` upload 面 0；`NH-RA07-B01` 非 API 五维 stub；`NH-RA08-B01/B02/B04` 四通道未接通 / 检索终验假绿 / reclean。本面 **不改写** 功能设计。

---

## 5. 跨功能系统一致性 ★ `[核心]`

- **5.1 整体形态一句话**：功能面各自拥有图/binding/表示/clean/runtime/upload/语义/publication；本面拥有横切 **失败法 + 重放 + 竞态 + 兼容 + 证明分层**。成功路径必须同时满足 `T-O-376`（真走通）与 `T-O-383`（坏文件真失败）。
- **5.2 功能间一致性契约（不变量）**：

| 编号 | 不变量 | 跨哪些面/模块 | 违反后果 |
|------|--------|----------------|----------|
| `NH-C-80` | 清洁边一旦封闭，该 Execution 不再换清洁工人；内容失败不出向量 | `02/04/08/09` | 血统不可读；假向量 |
| `NH-C-81` | 同 Task 指纹 replay 原视图；异指纹 409 ConflictError | `06/08/09` · Task API | 双树 / 静默覆盖 |
| `NH-C-82` | 同 intake 键 + 同 digest = replay，指针必须解析 | `08/09` | NS9-FX2 回归 |
| `NH-C-83` | 并发提交走 typed ConflictError / rowcount CAS，禁止 last-writer-wins | `01/02/06/09` | serving 撕裂 |
| `NH-C-84` | 空 admitted clean 不是成功 | `04/08/09` | 无知识入索引 |
| `NH-C-85` | 上传服从同一套幂等/冲突法，且不创造 S04 身份 | `06/09` | 孤儿当业务成功 |
| `NH-C-86` | `s05_binding_digest` 表示 **已封闭 actual** 路径，不得用 domain digest 冒充 | `02/09` | 晚绑定无法证明 |
| `NH-C-87` | 旧 Execution 按 pinned compiled digest 跑；新 kind 图不得改旧行 | `01/09` | 升级卡死或暗切图 |
| `NH-C-88` | 单元 / 集成 / default-root e2e / retrieval 四层不可互换；monkeypatch ≠ live | 全面 | 假绿冻战役 |
| `NH-C-89` | 通道是验收行；crash window 与 CAS 是共享列，只实现一次 | `03/04/06/08/09` | 按通道复制失败法 |

消费（不改定义）邻面已落盘不变量：`NH-C-01..09`（面 01 图/merge）、`NH-C-11..19`（面 02 seal）、`NH-C-20..29`（面 03 表示）、`NH-C-30..39`（面 04 clean）、`NH-C-40..49`（面 05 供给）、`NH-C-50..59`（面 06 上传≠Item）、`NH-C-60..69`（面 07 五维；`NH-C-66` 是目标法，reclean 测量在 `NH-RA08-B04`）、`NH-C-70..79`（面 08 可检索）。本面只校验横切 replay/fake-green，不重开这些 C。冲突候选（gate 号碰撞）已在各面 v0.2 分号，index §4 增补 **deferred**。

- **5.3 数据 / 控制流贯穿图**：
```text
caller POST /tasks
  -> fingerprint identity CAS          [NH-C-81] [W-PROM-CAT]
  -> Execution pin workflow revision   [NH-C-87]
  -> acquire/decode evidence           [D-13 单值]  -- 选边前 W-SEL
  -> bind clean edge, seal s05 digest  [NH-C-86]  -- HEAD 今日过早写入
  -> admitted clean nonempty           [NH-C-84]
  -> Outcome+proof CAS                 [W-OUTCOME]
  -> publication pointer / retirement  [W-PUB]
  -> retrieval query+facet             [NH-C-88 mega]
失败任意绑定后步骤 --X--> 向量
upload promote CAS --X--> Item         [NH-C-85]
outbox redelivery --> idempotent no extra side effect [W-OUTBOX]
GC grace vs ingest                     [W-GC-INGEST]
```

**与邻面消费/提供**：本面 **消费** 01 图身份、02 seal 合同、03 evidence、04 empty 合同、05 readiness 码、06 handle CAS、07 facet 键、08 「可检索」定义；**提供** 防假绿格栅、crash window 清单、compat 联合测包。不提供功能设计。

---

## 6. 净新契约 / 架构边界草案 `[核心]`

> 草案，非冻结。不冻结库、谓词字面、HTTP 路径、purpose 字符串。

- **6.1 净新聚合 / 解耦点**：
  - `NH-N-09-01` 防假绿验收格栅（本面主产品，§9）——与功能 AP 解耦的证明物。
  - `NH-N-09-02` crash-window 目录（W-*）作为跨面共享测试夹具，而不是每通道一套。
  - `NH-N-09-03` old-pinned × kind-family 联合验证套件。
  - `NH-N-09-04` 「未封闭 actual S05」合法状态 + 上传同一失败法的最小证明包。

- **6.2 净新契约叙述规格**：
  - **输入**：Execution 身份、是否已封闭 actual binding、crash 点枚举、测试层标签。
  - **输出**：typed 错误码 / replay 视图 / ConflictError / 无向量证明（负向查询）。
  - **边**：禁止用 domain digest 填 actual；禁止 monkeypatch 成功路径；禁止 sqlite3-on-Turso 当绿。
  - **未封闭状态**：合法表达由 `G-NH-01` 裁决（本面只要求「可区分、可测、retry 不热切」）。

- **6.3 架构边界（与既有 / 相邻面）**：证明层不得改图代数（01）、不得选 runtime 库（05）、不得发明第五 kind。上传证明调用 06 的 handle 合同。Mega 调用 07 facet 与 08 终态，不重开 cuts。

---

## 7. Substrate-fit / 技术路线过滤 ★ `[核心]`

| 借鉴点 | 原机制（参考处） | 是否冲突本仓路线 / 约束 | 落地形态（降级 / 重映射 / 直采） |
|--------|------------------|--------------------------|-----------------------------------|
| Task fingerprint / ConflictError | HEAD | 不冲突 | **直采** 扩到新路径 |
| 无环编译拒 | HEAD S03 七表 | 不冲突 | **直采** |
| scatter Snapshot fan-in | HEAD | 不冲突 | **直采**；换 PersistencePort 检验 |
| object CAS + GC restore | HEAD S13 | 不冲突 | **直采**；upload 面是 06 的 delta |
| IETF Idempotency-Key 头 | draft-06 | 头字段/过期/RFC7807 未冻；本仓已有 UUID 身份 | **降级** 为语义：replay / 409 / 422 分账 |
| CPU CAS / DCAS / HTM | Wikipedia | 非 SQL 单体 | **重映射** 为 `row_revision` + `rowcount` |
| Kafka transactions / Streams EOS | Confluent | 禁引入 Kafka 栈；出界不保证正合本仓 | **降级** 为闭集效果一次 + 出界 fail-loud |
| Temporal pin / replay tester | Temporal 官方 | 禁 Temporal/云 Worker；本仓静态图+digest | **降级** 为 compatibility_definitions + 旧 Execution 种子测 |
| Worker Versioning / Event History | Temporal | 完全不同执行模型 | **不采用** |
| legacy restarter 先入队 | restarter.ts | CF 队列 + 重复副作用 | **反例**；对照本仓 outbox 幂等 |
| legacy catch skip / empty success | dedicated/universal | D08 已禁 | **反例**；变测试格 |
| TigerBeetle DST / Jepsen | 官方 DST | 分布式仿真器超本仓范围 | **降级** 为：crash 窗口清单 + 内建断言；不引入仿真器 |
| PBT 随机生成 | 搜索包 | 不能替代 e2e | **部分**：仅对纯函数 digest/CAS 不变量 |

---

## 8. 反例坑表 + 净新表 `[核心]`

### 8.1 反例坑表 ⛔

| 反例 | 来源锚 | 为什么不可借 |
|------|--------|--------------|
| e2e monkeypatch 当接线 | `test_source_capability_paths.py:99-101`；`T-O-378` | 假绿；与 live-to-vector 对打 |
| sqlite3.connect 打开 Turso 文件 | scatter `367`；README K1；`NS1-V11` | harness 红灯冒充产品失败或反过来掩盖产品失败 |
| domain digest 当 actual S05 | `task_create.py:180` | 与 S05-T025 / `T-O-384` 封闭时刻冲突 |
| decode 盗用 OCR 未部署 | `types.py:154-158` | 绑定前观察与绑定后失败法混为一谈 |
| 503 当通道 DoD | `T-O-376`；`D-21` | 「诚实未部署」被业主禁止作为完成 |
| Task succeeded / publication_ready 当可检索 | scatter `496-499`；retrieval 无 namespace | 终态层被下层顶替 |
| dedicated per-member catch skip | chinatax/domain/REA processor catch | silent skip；required 集被悄悄缩小 |
| `plainTextAvailable: true` 无非空 | `cleaner_web.ts:321` | 空成功入下游 |
| finalizer 凭 R2 key 成功 | `finalizer.ts:116-129` | 无 admitted clean / proof |
| restarter 先 dispatch 再写库 | `restarter.ts:812-814` | 崩溃 → 重复技能副作用 |
| Kafka/Temporal 运行时 | WEB 锚 | `T-O-42` 绿地；单体 FastAPI + local Turso |
| exactly-once **delivery** 宣称 | Sequin / Kafka 自身边界 | 物理双提交不可能；本仓只承诺幂等效果 |
| `.experiment` 当 completeness | `T-O-380` | 发车日 OPEN |
| 0815-R7 inline 4/4 当四通道 | `T-O-376` | 明确排除 |

### 8.2 净新表 🆕

| 项 | 为什么无先例 | 草案落点 |
|----|--------------|----------|
| `NH-N-09-01` 防假绿格栅作物 | 行业有测试金字塔，无 MKB 四层×T-O-381 闭集 | §9 → planning-proposed |
| `NH-N-09-02` crash-window 目录 | 外部 CAS/EOS 不映射本仓 W-SEL/W-PUB | §2.4 / §6 |
| `NH-N-09-03` kind 家族 × 旧 pin 联合套件 | Temporal pin 不同模型；HEAD compat 只覆盖 markdown/index | §2.5 Q2 |
| `NH-N-09-04` 未封闭 actual + 上传同一失败法证明包 | HEAD 无未封闭状态；upload 面 0 | `G-NH-01` 消费；§2.7 Q4 |

---

## 9. 验收格栅草案（防假绿）`[核心]`

> 本面主产品。落地验收归下游执行计划；此处封堵 fake-green。实验发车 **不是** 退出条件。

| 功能 F | 收口目标（一句话可验证） | Test-ID（拟） | 测试层 | 防假绿要点 |
|--------|--------------------------|----------------|--------|------------|
| Task 同指纹 replay | 二次 POST 返回同一 task 视图，不新增 Execution/对象引用 | `NH-A-09-01` | 集成 + default-root e2e | 禁止刷新 audit 时钟导致假冲突 |
| Task 异指纹冲突 | 同 UUID 不同 payload → 409 `task-identity-conflict`，原行不变 | `NH-A-09-02` | 单元 + 集成 | 今日测试 0，必须补 |
| 并发 create | 双飞同身份：一成功一 409 或 replay，无双根 | `NH-A-09-03` | 集成 | 禁止 last-writer-wins |
| 空 clean | 空 HTML/空 PDF 文本 → Process 失败，检索 0 命中 | `NH-A-09-04` | 单元 + default-root | 禁止 `CLEAN_EMPTY` 只存在于 handler |
| API empty member | parser/schema 拒；不得 skip 后 root succeeded | `NH-A-09-05` | 单元 | 对打 legacy catch skip |
| API exhausted-zero | 终态符合 **裁决后** 的 G-NH-08；无论哪选项都必须 **可检索证明一致**（无向量或显式空） | `NH-A-09-06` | e2e | 不在本文裁 succeeded vs failed |
| 子失败 collect-all | 父 failed 码稳定；兄弟 publication 不得使父检索成功 | `NH-A-09-07` | e2e + retrieval | 禁止只 assert sibling publication_ready |
| fan-in crash | 子已终、父 waiting 时修复 exactly-once 父成功 | `NH-A-09-08` | e2e | **禁止** sqlite3-on-Turso 检验 |
| Gate 幂等 | 同 idempotency_key 不双决策 | `NH-A-09-09` | e2e | 已有；回归保留 |
| 未封闭 binding crash | 选边前杀进程 → 恢复后仍未封闭、未出向量 | `NH-A-09-10` | 集成 | 依赖 G-NH-01 状态表达 |
| 封闭后 retry | 不换 clean process_key / 不热切图 | `NH-A-09-11` | 集成 | 对打 B01/B12 |
| OCR 未部署 | typed 失败；decode **不得**抛同一码 | `NH-A-09-12` | 单元 + e2e | 对打 `types.py:154-158`；此格 **不是** live DoD |
| OCR/browser **已部署** live | 默认 `create_app()` 无补丁走到向量或生命周期终态 | `NH-A-09-13` | default-root e2e | **禁止 monkeypatch**；禁止 503 |
| 公共上传 replay | 同 digest+size → 同 handle；不造 Item | `NH-A-09-14` | e2e | 无 ingest 可 GC |
| 上传 vs GC | grace 内 ingest 与 GC 交错不丢 live 字节、不把 orphan 当 Item | `NH-A-09-15` | 集成 | 扩 GC TOCTOU |
| old pin × 新 kind 图 | §2.7 Q2 的 A/B/C 三测全过 | `NH-A-09-16` | 单元 + 集成 | 不跑 Temporal |
| 未知 compiled digest | 不插入 Process | `NH-A-09-17` | 单元 | 已有，扩 kind digest |
| retrieval mega 每通道 | query 命中 + traceback resolved + facet（待 07 键名） | `NH-A-09-18` | retrieval-facet mega | **必须** namespace；禁止 R7 inline 顶替 |
| 默认根负例 | 未注入 browser/OCR 时稳定拒绝，**不**称为通道完成 | `NH-A-09-19` | default-root e2e | 负例 ≠ DoD |
| 无 monkeypatch 源路径 | local/static/pdf **真**终端（succeeded 或 typed failed），不得 `running` 超时 | `NH-A-09-20` | default-root e2e | 今日反例 B03 |

**四层对照（防互换）**

| 声称 | 不得用什么顶替 |
|------|----------------|
| 单元绿 | 顶替接线 |
| fixture provider records | 顶替 live 供应商（live 供应商本就 OOS）但 **可以** 顶替 API 三 operation 的 map 正确性 |
| Task succeeded | 顶替 retrieval |
| 503 | 顶替 `T-O-381` 格子 |
| monkeypatch | 顶替 default-root |
| `.experiment` | 顶替 completeness |

---

## 10. 优先级建造建议 + owner-gate 候选 `[核心]`

- **10.1 建造顺序（依赖序，分批不一次性深做）**：

| 顺序 | 工作簇 | 依赖 | 复用判定 |
|------|--------|------|----------|
| `P0-a` | 去掉 e2e monkeypatch 与 sqlite3-on-Turso 检验；source 窗不得以 `running` 冒充 | harness / PersistencePort | `♻️重 substrate` |
| `P0-b` | 补 `CLEAN_EMPTY` + `task-identity-conflict` + decode 不再盗 OCR 码的负测 | 04/03 合同 | `✅复用` handler + `🆕` 测试 |
| `P0-c` | actual S05 封闭时刻可测（状态表达不在本面裁决） | `G-NH-01`；面 02 | `🆕净新` 证明 / `♻️` 列 |
| `P0-d` | old pin × kind 图联合套件 | 面 01 图身份 | `✅复用` compat 机制 + `🆕` 种子 |
| `P1-a` | 上传 replay/GC 竞态格 | 面 06 产品面 | `✅复用` S13 CAS |
| `P1-b` | retrieval mega + namespace + facet | 面 07/08 | `♻️` 检索栈 |
| `P2` | crash 窗口注入扩到 W-SEL/W-PUB | P0-c | `🆕` 夹具 |
| `P-x` | `.experiment` | `T-O-380` OPEN | **不进** 本面 DoD |

- **10.2 owner-gate 候选（只 MARK 不裁决 → 上交 index §4 / 下游决策登记）**：

| gate-ID | 决策点 | 候选选项（不预设倾向） | 影响 |
|---------|--------|------------------------|------|
| `G-NH-01` | S05 两阶段 binding 的 schema/命名（本面 **消费**） | `保留 policy+新增 actual` / `nullable actual+sealed state` / `其他经证据支持方案` | 决定 `NH-A-09-10/11` 如何写；本面不选 |
| `G-NH-08` | exhausted-zero registered API 终态（本面 **消费**） | `typed no-op success` / `distinct no-change terminal` / `explicit empty failure` | 与 `NH-C-84` 表面张力；本面不选 |
| `G-NH-09` | Workflow substrate 是否留在 new-harvest（本面 **消费**） | `NH 内前置 AP` / `独立 engine campaign` / `在不破产品法前提下采用现 substrate 方案` | 决定 compat 套件深度 |
| `G-NH-06` | FilterMeta channel 公共查询命名（mega facet 行依赖） | `semantic_channel` / `source_channel` / `重命名 vector channel` / `其他无歧义方案` | mega 列名；本面不选 |
| `G-NH-18` | **测试分层（unit / 集成 / default-root e2e / retrieval mega）是否写入 charter** 作为 completeness 义务 | `写入 charter 四层不可互换` / `仅写入 planning 不入 charter` / `其他经证据支持的分层` | 本面主产品能否成为战役退出法；**不预设倾向** |

本面 **不新开产品法**。不裁决 PDF/browser 库、不裁决 kind 张数（已冻 `T-O-387`）、不裁决 upload-only vs read（`G-NH-07` 属面 06）。`G-NH-18` 只 MARK、无推荐赢家；index §4 v0.2 已登记本 gate（仍不裁决）。`G-NH-11` 留给面 02 seal 事务。

---

## 11. 核验记录 `[核心]`

> 对抗性自检：关键锚点是否真核验过；与叙事冲突处以实测为准。

| 锚点（host-ID） | 是否核验 | 方式（grep/read/run） | 备注 / 修正 |
|------------------|----------|------------------------|--------------|
| HEAD `1221aa1` | `✅` | `git rev-parse --short HEAD` | 与 index §2.2 一致 |
| 分母脚本 D-01.. | `✅` | `uv run python` §1.3 | kinds 4 / strategies 10 / capabilities 9 / ops 3 / single 13 / public 7 / unsel 6 / scatter 2 / semantics 10 |
| `D-23` 33 passed | `✅` | pytest 选定 5 文件 | **确认** 33 dots，0 failed |
| API 三 provider e2e | `✅` | pytest 命名用例 | **passed**（本面） |
| API fan-in recovery | `✅` | pytest | **failed** `disk I/O error` at `:367`；不得抄 index「1 failed」而不跑。失败点在 TestClient 外 sqlite3 检验，**整测仍红**，不宣称产品路径已绿 |
| API child failure | `✅` | pytest | **passed** |
| source capability e2e | `✅` | pytest | **failed** `local` `running`；与 README K1 / index D-24 方向一致，本面用复跑事实 |
| compat + GC + identity replay | `✅` | pytest | 2+1+1 passed |
| `task_create.py:180` domain→s05 | `✅` | read_file | 行号确认 |
| `test_source_capability_paths.py:99-101` | `✅` | read_file | 赋值 `_http_fetcher` 与 `_browser_fetcher` |
| `types.py:154-158` OCR 盗码 | `✅` | read_file | 确认 |
| `api/app.py:330-345` 未注入 browser | `✅` | read_file | `IntakePipeline(... http_fetcher=http_acquirer ...)` 无 `browser_fetcher=` |
| `CLEAN_EMPTY` 测试 0 | `✅` | grep `tests/` | 修正「handler 有 = 已证明」 |
| `task-identity-conflict` 测试 0 | `✅` | grep `tests/` | 生产有、测试无 |
| retrieval namespace 强制 vs e2e | `✅` | read `retrieval_request.py:265-269` + e2e 检索体 | 确认 K1 机制根因 |
| public upload 0 | `✅` | grep `@router` `routes.py` | 28 条无 upload |
| legacy catch skip | `✅` | read dedicated processors | 三 provider 均有 |
| `plainTextAvailable: true` | `✅` | read `cleaner_web.ts:321` | 无非空断言 |
| finalizer R2 成功 | `✅` | read `finalizer.ts:116-129` | |
| restarter 先入队 | `✅` | read `restarter.ts:812-814` | |
| IETF draft-07 | `✅` | `web_fetch` `-07.txt` | 409/422 仍在；**-06 已过期**；**-07 Expires 2026-04-18，访问日 2026-08-29 亦过期** |
| Temporal safe-deployments | `✅` | `web_fetch` | replay test；eager start 限制 |
| Kafka delivery-semantics | `✅` | URL 与面 02 对齐 | 闭集；出界不保证；**不再**用博文口径 |
| Sequin EOS delivery | `✅` | `https://blog.sequinstream.com/at-most-once-at-least-once-and-exactly-once-delivery/` | 只打 delivery 宣称；禁止当机制 |
| Wikipedia CAS | `✅` | 补完整 oldid URL | **降为线索**，不占机制 RA |
| TigerBeetle DST | `✅` | `web_fetch` | 黑盒限度 |
| 01–08 analysis | `✅` | `list_dir` reference-anchor | **9 份均在**；B13 关闭「无文件」；功能行改为消费 `NH-RA0X-B*` |
| QNA T-O-376/378/380/383 | `✅` | read_file 表与 Q3 | 只 CITE |
| 叙事「全量 558/11」 | `部分` | 读 README K1，**未**复跑全量 pytest | 全量水位保持 README 声称，不在本面冒充实测全绿或全红 |

---

## 12. 收尾 Verdict 与交接 `[核心]`

- **本面裁定**：横切失败法的 **substrate 大半已在**（fingerprint、无环拒、Gate/Process/object CAS、scatter 失败收集、compat pin、空 clean handler、缺能力 fail-closed），但 **闭集证明是红的**：actual S05 冒充（消费 02-B01）、monkeypatch、source `running`、Turso harness、upload 0（消费 06-B01）、mega 无 namespace、关键负测 0。01–08 **已落盘**，本面必须引用其 gap ID；健康维持 index 预核 `P0 / 🔴`。
- **交接下游**：缺口台账（§4）→ 规划；净新契约（§6）→ 设计；owner-gate 候选（§10.2，含 `G-NH-18`）→ 决策登记；验收格栅（§9）→ 执行计划。功能 S1 只消费 `NH-RA0X-B*`。
- **冻结前置**：① 01–08 gap ID 已引用（本 v0.2 起步）且仍 `draft`；② `G-NH-01` 给出可测的未封闭状态（裁决本身不在本文）；③ `NH-A-09-01..20` 中 S1 格有 HEAD 证据或显式 waiver；④ 无 monkeypatch 的 default-root 负例/正例分账；⑤ 本文件仍为 `draft`——**本轮禁止标 frozen**。

---

## 附录 A · 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-08-29 | Grok analysis-fleet / review-fleet | 初稿（measure-first + 三渠道正反例 + 防假绿格栅 + 五问作答）；01–08 未落盘故横切汇总用 index 初判 |
| v0.2 | 2026-08-29 | Grok fix-fleet | 吸收已核实 review：R4-I04 关闭「01–08 未落盘」/B13；功能 S1 改为消费 `NH-RA02-B01`/`NH-RA05-B01`/`NH-RA06-B01`；R4-I01 `G-NH-11`→`G-NH-18`；R2-I06 D08 改 `RA-09-BASELINE-01` draft；R1-I03 D-05 行段改回 inline+profile；R3-I07/I08 WEB 过期 I-D / Wikipedia 线索 / Kafka 设计文档 / Sequin URL。状态仍 `draft` |
| v0.3 | 2026-08-29 | Grok parent independent-verify | §3 矩阵 Wikipedia CAS 行与 `RA-09-WEB-02` 对齐为线索，取消 `🔶部分借` |
