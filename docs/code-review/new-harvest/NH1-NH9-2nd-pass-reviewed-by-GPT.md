# MKB new-harvest NH1–NH9 第 2 轮代码审查

> 审查对象: `new-harvest NH1–NH9：四 intake channel、dynamic workflow、race/error/idempotency、leaf-worker contract、observability/control`
> 审查类型: `rereview | mixed`
> 审查时间: `2026-08-31`
> 审查人: `GPT`
> 审查基线: `HEAD ba099ee305577cca2281a669afbca364111f200b`
> 审查范围:
> - `api/`、`intake/`、`src/`、`tests/`
> - `src/persistence/migrations/018_nh2_selected_output_control.sql` … `024_nh_review_invariants.sql`
> - `docs/closure/new-harvest/CROSS-NH-campaign.md`
> - `docs/closure/new-harvest/AP-NH1-*.md` … `AP-NH9-*.md`
> - `git a608ea8..ba099ee` 与第一轮修复提交 `59772f5 / 34ad2fb / ba099ee`
> 对照真相:
> - `docs/eval/new-harvest/final-execution-plan.md`
> - `docs/eval/new-harvest/pre-initial-planning-qna.md`
> - `docs/eval/new-harvest/pre-charter-qna.md`
> - `docs/plan/new-harvest/AP-NH1-*.md` … `AP-NH9-*.md`
> - `docs/baseline/domain-truth/S03-workflow-engine.md`（leaf-worker workflow read/capability contract）
> 输出模板: `.adocs/templates/code-review.md`
> 文档状态: `changes-requested`

---

## 0. 总结结论

> **一句话 verdict：四通道 happy path、kind-only resolver、actual seal 与 publication/retrieval 主骨架真实存在，但 NH1–NH9 仍不能收口；当前是“fresh-DB 代表路径可跑，升级、重放、观察身份、终态竞态、真实 runtime 与 leaf-worker 契约仍有承重断点”，不是完整完成。**

- **整体判断**：`partial / under-delivered；存在会导致错误成功、永久 running/queued、升级 503、错误 lineage 与不可回收字节的 blocker。`
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **Finding 分布**：`critical 4 / high 9 / medium 4`
- **本轮最关键的判断**：
  1. `Execution` 已终态后仍可接受迟到 Outcome、把原 Process 写成 succeeded，并物化下一 Process；这是状态机 correctness blocker。
  2. 第一轮改动改变 inline kind graph canonical digest 却仍用 revision 1，旧数据库升级稳定 `REGISTRY_DIGEST_MISMATCH` 503；所谓 old-pin compat 未覆盖真实升级路径。
  3. 三个 single kind 会把同 external key 的不同正文压到同一 immutable Snapshot；`full_task` 又可在旧 actual-S05 下重新抓 HTTP 新字节，因果与 replay 法均不成立。
  4. 第一轮账本的“24 项 fully fixed”经 HEAD 复核只得到 `16 done / 13 partial / 8 missing / 5 n/a-by-design`；关键 partial 不是措辞问题，而是可复现的业务断点。
  5. `10+3 live` 中模型/OCR 正格仍由 stub、固定 HTTP handler 与同源 5×7 glyph fixture证明；workflow list/detail、ProcessCapabilityManifest、严格 response/error schema 仍缺失。

本轮 review 不收口，等待实现者按 §5 的 blocker 顺序修复，并以 persisted-DB upgrade、真实 retry、合法边生成器、进程级 fault 与 production supply profile 重新审查。

---

## 1. 审查方法与已核实事实

### 1.1 独立性与既有审查的使用边界

- 本轮未把 `docs/code-review/new-harvest/NH1-NH9-reviewed-by-*.md` 作为审查输入，未主动逐份研读或采纳其 finding/verdict。
- 按用户明确要求，`docs/code-review/new-harvest/NH1-NH9-review-VF-ledger.md` **仅作为第一轮声称修复项、commit 和目标文件的索引**；本报告没有把其 `fixed / independently-verified / deferred` 标签当作证据。
- 三个对抗性子审查均被明确禁止读取 `docs/code-review/**`；它们只读 frozen truth、action-plan、closure、HEAD 与 Git diff。所有进入本文的 blocker 均由主审再次打开源码、核对事务边界或用临时数据库/TestClient 复现。
- closure 是被审 claim，不是证明；测试绿灯是证据之一，不替代 schema、状态机和真实 supply 判断。

### 1.2 Todo-list 与审查 DAG

| Todo | 内容 | 状态 | 产物 |
|---|---|---|---|
| T1 | 读取模板、final/QNA、九份 action-plan closure、CROSS closure | completed | scope/DoD/OOS 基线 |
| T2 | 对账 `a608ea8..HEAD`、第一轮 VF 索引与三个修复提交 | completed | §3.2 修复追踪矩阵 |
| T3 | 四 intake 端到端攻击审查 | completed | 调用链、retry/snapshot/supply findings |
| T4 | leaf-worker/dynamic workflow 契约攻击审查 | completed | discovery/capability/version/state findings |
| T5 | durable data/observability/control 攻击审查 | completed | evidence/upload/GC/readiness/control findings |
| T6 | 主审交叉归因、反证、最小复现 | completed | R1–R17 |
| T7 | targeted tests、ruff、diff、自检 | completed | §1.5 |
| T8 | 依模板写入本文件 | completed | 本报告 |

```text
D0  冻结 truth / scope / closure claims
│
├── D1  Git + 第一轮修复逐项对账
├── D2  四通道 E2E：intake → graph → process → tail → retrieval
├── D3  leaf-worker：discover → select → pin → materialize → terminal
└── D4  durable/ops：lineage → race → observe → retry/cancel/delete
       │
       └──────────────┐
D1 + D2 + D3 + D4 ──> D5 跨簇不变量归并
                       │  identity / revision / actual / terminal / proof
                       v
                     D6 最小反例与定向回归
                       │
                       v
                     D7 severity / root cause / verdict
```

### 1.3 对抗性子审查话题与专用 Prompt 约束

| 泳道 | 专用攻击目标 | 强制反例 | 禁止项 |
|---|---|---|---|
| A · 四通道 E2E | 四 source kind 的 public admission、acquire/decode/clean、CONTROL、shared tail、L4 query | source mutation、same key different bytes、scatter child fail、zero、retry、wrong media/strategy | 禁读既有 review；禁把 helper/monkeypatch/Task success 当产品证明 |
| B · leaf-worker | workflow/category/list/detail、kind/strategy/capability、pin/version、状态/错误闭集 | persisted DB upgrade、unknown digest、unknown capability、late Outcome、invalid state intent | 禁把内部 Python resolver称 HTTP surface；禁开放 caller workflow key |
| C · durable/ops | Task→Execution→Process→fact→selection→publication lineage；debug/retry/restart/delete/stop | SQL mutation、upload replay/cancel、PROM-CAT、GC crash、dead outbox、readiness false-positive | 禁把内存 metric/log当 durable truth；区分 logical delete 与 physical purge |

### 1.4 已核实的真实业务链

```text
POST /v1/teams/{team}/tasks
  → TaskCreateRequest / SourceDescriptor
  → TaskCreateMixin.create
  → ConfigSnapshotService.prepare
  → WorkflowRegistryService.resolve_for_source
  → Task + Audit + root Execution + wake_execution（同 UoW）
  → WorkflowRuntime.materialize_root
  → WorkflowWorker claim / heartbeat / handler / accept_outcome
  → IntakePipeline acquire → decode → clean
  → RepresentationFact + AcquireDecodeHistory
  → selected clean edge + actual-S05 seal
  → selected-output CONTROL
  → seal/preflight/accept
  → structurize → construct → vectorize → validate_publication
  → proof + active pointer + serving revision
  → namespaced + facet retrieval
```

四个实际 source kind 为：

- `inline_payload`：`src/workflows/kind_family.py:257-381`
- `local_object`：`src/workflows/kind_family.py:384-445`
- `http_resource`：`src/workflows/kind_family.py:448-586`
- `registered_api`：`src/workflows/builtin_scatter.py:93-599`

三张 single kind 图确实共用 `src/workflows/lsrag_shared_tail.py`；registered API 保持 scatter root + child。public caller 没有直接 `workflow_key/action_branch` 字段，图 key 由 `WorkflowRegistryService.resolve_for_source()` 内部选择。

### 1.5 执行过的验证

| 验证 | 结果 | 说明 |
|---|---|---|
| `git log --reverse a608ea8..HEAD` | PASS | 修复提交为 `59772f5`、`34ad2fb`、`ba099ee` |
| `git diff --check a608ea8..HEAD` | PASS | 无 whitespace error |
| `uv run ruff check api intake src tests` | PASS | `All checks passed!` |
| 18-node targeted suite | PASS | review fixes + workflow compat + identity replay + readiness |
| leaf-worker 45-node targeted suite | PASS | kind/edge/CONTROL/fact/seal/intent/compat；但未覆盖反例 |
| four-channel 28-node targeted suite | PASS | resolver/lineage/closed-set/review-fix；但未覆盖 source mutation/retry |
| `uv run pytest -q` | **未完成，不计 PASS** | 跑至 23% 无失败后因耗时主动中断；本报告不伪造全仓绿 |
| `tests/unit/test_ns6_phase2.py::test_stale_fencing_fail_does_not_kill_new_generation` | **FAIL** | 第一轮 VF24 改成抛 `stale-process-fence`，旧回归仍期待 no-op |

主审临时库/TestClient 反例（均在临时目录执行，不改仓库）：

| 反例 | 实测 |
|---|---|
| terminal Execution + late success Outcome | `accepted=True`；failed Execution 下原 Process→succeeded，并新增 ready Process |
| a608 风格 inline graph rev1 → HEAD rev1 | old digest `210168b9…`、HEAD `06e0b8d2…`；register 返回 `REGISTRY_DIGEST_MISMATCH 503` |
| same external key + different inline body | 两 Task 均 succeeded；`sources=1 / snapshots=1 / items=1 / revisions=2 / memberships=1` |
| local PDF + `doc.deterministic` | create 201；2 秒后 decode Process 仍 running、error=NULL |
| same registered observation、首 Task 尚未运行 | 两个不同 Task 均 accepted；`tasks=2 / sources=0` |
| nonexistent Team upload | `team-not-found`；catalog=0，但 final CAS file=1 |
| same bytes upload twice | second 被标 replay；live pending=2、owner=2 |
| GC tombstone commit 后 destroy crash | tombstoned=true；reconcile=0；quarantine file=1 |
| selection fact | stored selection digest匹配 output-manifest alias，不匹配真实 representation fact |
| direct evidence mutation | selected output / 6 generation artifacts / 9 vector embeddings 可 UPDATE；fact trigger拒绝 |
| nested source `payload_extra.api_token` | model accepted，sentinel 被写入 `mkb_task_audits.strict_payload_json` |
| OpenAPI | workflow paths=0；Task get response=`additionalProperties: true` |
| `concurrent_writes_required=True` | persistence `concurrent_writes=false`，整体 `/ready` 仍 ready |

### 1.6 已确认的正面事实

- 四个 source kind 的代表 happy path 都有真实 Task/Execution/Process 链，并能在 fresh DB 上到达 publication/retrieval。
- kind-only graph identity 成立；caller 不能直接提交 workflow key、revision、digest 或 action branch。
- acquire/decode representation fact callback 与 Process Outcome 位于同一 UoW；`024` 对 fact/history UPDATE/DELETE 增加 trigger。
- actual-S05 首次 seal 把 ordered representation path、route、clean step/process/strategy纳入 digest，并用 CAS + sealed-once trigger。
- cancellation 先赢时会把 Execution/Process 置 cancelling、增加 fence，迟到 Outcome 会被拒绝。
- public raw object GET/list/presign 没有被打开；local object handle有 Team fence。
- semantic six-tuple、S06 overlay、v2 facet SQL 与 retrieval 的 proof/pointer/serving double fence主体成立。
- rebuild/metadata 已真实绕开 acquire/decode/clean；`exhausted_zero` 与 indexed success 分账。

### 1.7 已确认的负面事实

- fresh-DB 测试覆盖不等于 upgrade；HEAD 对已注册 rev1 inline graph不兼容。
- 相同 source identity 的新 observation、full retry 与 terminal callback 三条因果律均可破坏。
- 第一轮补丁对 observation、upload hold、GC reconcile、selection fact 的修复均只覆盖局部切片。
- runtime/capability/readiness 与 public discoverability 没有形成单一、版本化、可供 leaf caller 消费的 contract。
- observability 表很多，但普通 caller和 operator都无法从正式接口完整还原 workflow key、step/process、route result、retryability 与当前阻塞原因。
- NH9 manifest/fault suite没有生成全部 legal edge，也没有进程级 kill/重启证明。
- HEAD 至少有一个可独立复现的既有回归红灯；第一轮“全部 true-bug fully fixed / 无 blocked”不能作为全仓绿证明。

### 1.8 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|---|---|---|
| 文件 / 行号核查 | yes | 每条 finding 均落到 HEAD file:line |
| 本地命令 / 测试 | yes | targeted suite、ruff、Git、临时库反例 |
| schema / contract 反向校验 | yes | migrations 018–024、S03、QNA、OpenAPI、SQL mutation |
| live / deploy / preview 证据 | partial | browser/PDF 本地执行有；真实 model/OCR release profile无 |
| 与上游 design / QNA 对账 | yes | final/QNA/action-plan/closure；baseline S03仅用于 leaf contract |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | blocker | 建议处理 |
|---|---|---|---|---|---|
| R1 | terminal Execution 仍接受迟到 Outcome并推进 | critical | correctness | yes | 双层 terminal CAS fence |
| R2 | inline kind rev1 原位变化导致升级 503 | critical | protocol-drift | yes | 新 revision + exact compat + upgrade fixture |
| R3 | 不同 observation 被压到同一 Snapshot | critical | correctness | yes | source/observation 分账与原子 replay law |
| R4 | full_task 在旧 actual 下重抓新 HTTP；API retry失败 | critical | correctness | yes | frozen replay或重算 actual |
| R5 | caller 点名 clean strategy，非法组合会永久 running | high | protocol-drift | yes | 移除 public worker selector；分类 Conflict |
| R6 | registered API observation 无 in-flight reservation | high | race/idempotency | yes | Task UoW 原子 reservation |
| R7 | Workflow read API / ProcessCapabilityManifest / strict response contract缺失 | high | delivery-gap | yes | 实现只读 discover + capability compiler |
| R8 | upload/Task pre-catalog failure留下永久不可见 CAS | high | correctness/security | yes | uncatalogued CAS reconciler或 durable promotion intent |
| R9 | upload replay/cancel缺 session identity | medium | protocol-drift | yes | upload idempotency key + pending token CAS |
| R10 | selection fact失实且 evidence plane可普通 SQL 改写 | high | correctness | yes | 正确 fact FK/digest + append-only triggers |
| R11 | nested payload/URL/raw state可把秘密与正文复制进 audit/stage | high | security | yes | recursive safe validation + ref-only envelope |
| R12 | required concurrent writes 未进入 readiness | high | platform-fitness | yes | capability gate进入 overall ready/claim |
| R13 | 10+3 的 model/OCR/browser production proof未闭 | high | delivery-gap/security | yes | 真实 pinned supply + lane readiness + hard egress |
| R14 | 状态/错误/调试/控制 surface 仍 partial | medium | platform-fitness | no | owner terminalization + typed API/read models |
| R15 | quarantine 对账仍漏 post-tombstone与双 scanner窗 | medium | correctness | no | durable quarantine state/fence |
| R16 | NH9 legal-set/crash/evidence强度不足 | medium | test-gap | yes | graph-derived cells + process kill/restart |
| R17 | Item生命周期缺少跨Task epoch，旧callback可跨delete/reactivate | high | correctness | yes | lifecycle epoch + callback CAS |

### R1. terminal Execution 仍接受迟到 Outcome并推进

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/workflow/runtime_outcome.py:52-63` 只拒绝 `cancelling`，不拒绝 `succeeded/failed/cancelled` Execution。
  - `src/runtime/workflow/runtime_outcome.py:100-139` 先把 Process写 succeeded，再解释下一条 route。
  - `src/runtime/workflow/runtime_materialize.py:338-467` 在 INSERT 下一 Process前没有 terminal Execution guard；`:475-483` 只让 Execution UPDATE失败，却不回滚已 INSERT Process。
- **最小复现**：running acquire 所属 Execution先置 failed，再提交同 fence success Outcome；实测 `accepted=True`，failed Execution 的 acquire→succeeded，新增 decode→ready，`current_process_uuid`还指向新 Process。
- **为什么重要**：这是明确的“FAILED 后仍推进”。新 Process因 claim 查询过滤 terminal Execution而永远不能运行，又会阻塞 cleanup；若 outcome committer有业务副作用，还会在 owner终态后提交。
- **审查判断**：当前 Process fence 只证明 worker claim没变，未证明 owner Execution仍允许提交。状态机不闭合。
- **建议修法**：
  1. `accept_outcome` 在同一 UoW要求 Execution处于 `ready/running/waiting`，terminal/cancelling全部冲突；
  2. Process success UPDATE 加 owner status关联 CAS；
  3. `_materialize_process_tx` INSERT前再次检查 owner非终态；
  4. 增加三种 terminal × late success/failed/retryable 的并发测试。

### R2. inline kind rev1 被原位改变，真实升级与 old-pin compat断裂

- **严重级别**：`critical`
- **类型**：`protocol-drift`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/workflows/kind_family.py:239-253` 仍固定 `revision_number=1`。
  - 第一轮 `59772f5` 改变 guard排序/去重（`:253`, `:361-369`），canonical manifest顺序进入 digest。
  - `src/services/workflow_registry.py:171-197` 对同 revision不同 fingerprint/digest稳定返回 `REGISTRY_DIGEST_MISMATCH` 503。
  - `api/app.py:587-601` 吞 bootstrap错误并将 readiness置红；current runtime也没有上一版 inline-kind digest的 compatibility definition。
- **最小复现**：用修复前 guard次序注册 rev1，再注册 HEAD rev1：old compiled `210168b9…`，HEAD `06e0b8d2…`，返回 503。
- **为什么重要**：已有数据库升级后新 admission和worker claim均被 readiness挡住；旧 Execution即使保留 revision row，也没有可加载的 exact plan。
- **审查判断**：fresh DB old-pin test只证明“显式维护的历史 single profile”可跑，没有证明 `a608ea8 persisted DB → HEAD`。
- **建议修法**：运行语义变化发 revision 2；保留 rev1 exact definition；canonical compiler按 semantic key真正稳定排序；增加 persisted DB upgrade fixture。`representation_path_digest` 本轮又增加字段但 recipe仍 v1，也应显式版本化。

### R3. single-kind 不同 observation 被压进同一 immutable Snapshot

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/intake/acquisition_ingest.py:129-138,235-264` 按 `(team, kind, external_key)`复用 source/item/**snapshot**。
  - `src/runtime/intake/acceptance_snapshot.py:139-171` 发现旧 snapshot后只复用 UUID，不比较新 `observation_fingerprint`。
  - `src/runtime/intake/acceptance_snapshot.py:175-237` 仍可追加新 Revision；`:245-329` 把新 raw artifact挂到旧 Snapshot。
  - `src/runtime/intake/acceptance_snapshot.py:337-349` Membership用 `INSERT OR IGNORE`，保留旧 observed revision；`:362-453` 第二个 Task却指向这张旧 Snapshot。
- **最小复现**：相同 inline external key、不同正文，两 Task均 succeeded；只有 1 Snapshot、2 Revision、1 Membership，两个 Revision的 `source_snapshot_uuid`相同。
- **为什么重要**：第二版正文的 producer、fingerprint、raw artifact与公共 `/items` revision相互矛盾；local/http共享同一路径。
- **审查判断**：系统既没有按新 observation建 Snapshot，也没有返回 conflict，而是成功写出错误因果链。
- **建议修法**：分离 source identity与 observation identity；同 fingerprint才可原坐标 replay且不再挂 artifact，不同 fingerprint必须新 Snapshot或稳定 409；Snapshot/Membership/Revision在一个 acceptance UoW内一致。

### R4. full_task replay不 exact：旧 actual 下可重抓新 HTTP，registered API retry又不可恢复

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/task/task_commands.py:293-318` 新 generation复制旧 manifest和 sealed actual全字段。
  - `src/runtime/workflow/runtime_core.py:107-163` 新 Execution仍从 start重跑。
  - `src/runtime/intake/acquisition_ingest.py:560-701` HTTP重新请求 URL。
  - `src/runtime/workflow/runtime_outcome.py:448-476` 对已 sealed Execution只比 clean step/process/strategy，不比新 path/route digest。
  - registered API output在 callback前序列化随机 source UUID（`acquisition_ingest.py:366-437`），callback才改为旧 source（`:439-481`），retry后下游可报 `INTAKE_SOURCE_MISSING`。
- **现有测试缺口**：`tests/unit/test_nh3_lineage_matrix.py:82-134`、`test_nh8_lineage_matrix.py:20-72` 只用 SQL造 failed/sealed行并比较复制字段，没有运行第二代 worker。
- **为什么重要**：HTTP正文已变但 actual digest仍是上一代；registered API child failure又无法用正式 retry恢复。
- **审查判断**：复制字段不等于 exact replay；输入字节与 source coordinates才是 replay authority。
- **建议修法**：sealed full retry从 frozen Snapshot/admitted clean/selected output恢复；若业务决定重抓，则必须新 actual并禁止称 full exact。registered API应复用已接受 Snapshot/ChangeSet或只 retry失败 child。

### R5. caller 仍可点名 clean worker；不匹配会留下无错误 running Process

- **严重级别**：`high`
- **类型**：`protocol-drift`
- **是否 blocker**：`yes`
- **事实依据**：
  - frozen Q2-B明确选择图内晚绑，拒绝 caller直点 strategy：`pre-initial-planning-qna.md:243-273`。
  - public `GenericSemanticSource.clean_strategy`：`src/contracts/api/models.py:37-56`。
  - `runtime_materialize.py:198-214,242-253` 让 Audit声明优先于 durable representation fact。
  - 第一轮 checker `strategies.py:193-208` 只看 kind的 capability并集。
  - 不匹配在 `runtime_materialize.py:105-114` 抛普通 `ConflictError`；Worker `worker.py:103-108` 把所有 Conflict当 stale fence重抛。
- **最小复现**：local PDF + `doc.deterministic`（或 image + PDF strategy）返回 201；acquire成功后 decode保持 running、无 error；supervisor异常状态又被下一 tick清空。
- **为什么重要**：动态 policy退化成 caller worker selector；昂贵 lane可被caller强制，非法格也不是 admission fail-loud/terminal failed。
- **建议修法**：从 public descriptor删除 `clean_strategy`；由 versioned graph policy + durable representation fact导出。Worker只对明确的 stale/lease/fence code重抛，route/domain conflict应落 terminal failure。

### R6. registered API observation check没有 in-flight reservation

- **严重级别**：`high`
- **类型**：`race/idempotency`
- **是否 blocker**：`yes`
- **事实依据**：
  - `task_create.py:97-98,452-480` 只查已经存在的 Snapshot。
  - precheck事务结束后才 prepare/INSERT Task（`:110-151`），没有 `(team, source, observation)` reservation。
  - `scatter_intake.py:154-178` 的冲突检查在 acceptance晚期，无法撤销已存在的 Task/Execution/Process。
- **最小复现**：不启动 worker，连续提交两个不同 task UUID、同 external key/records；两者均 accepted，`tasks=2`、`sources=0`。
- **为什么重要**：真实异步系统中“首任务已排队但未建 Snapshot”是常态，当前 admission防重形同虚设。
- **建议修法**：在 Task create UoW原子插 observation reservation，唯一键覆盖 source identity + observation key；同 fingerprint返回原坐标，异 fingerprint 409；abort/terminal有明确 reservation生命周期。

### R7. leaf-worker 的 Workflow/Capability/response contract未交付

- **严重级别**：`high`
- **类型**：`delivery-gap | platform-fitness`
- **是否 blocker**：`yes`
- **事实依据**：
  - frozen S03要求 `/v1/workflows`、detail、revision只读面：`docs/baseline/domain-truth/S03-workflow-engine.md:497-537`。
  - public/internal routers没有 workflow route；OpenAPI实测 path=0。
  - `WorkflowRegistryService` 只有 bootstrap/resolve/register：`src/services/workflow_registry.py:59-152`。
  - frozen `ProcessCapabilityManifest`字段见 S03 `:420-464`；当前所谓 capability digest只是 process-key字符串排序：`workflow_registry.py:155-164`。
  - handler truth仍是运行时 dict：`src/runtime/intake/core.py:359-395`；构造带 `unknown.capability` 的 definition可成功 register。
  - Task API多为裸 `Response`/`dict`；OpenAPI Task get是 `additionalProperties: true`，`TaskView`未被 route使用。
- **为什么重要**：上游无法发现 kind/list/detail/version/digest、required facts/supply、error retryability；compiler也不能在注册期拒绝不存在的 worker/port/proof contract。
- **建议修法**：实现只读 workflow list/detail/history与严格 response models；实现 code-owned ProcessCapabilityManifest，compiled digest hash manifest digests；保持无 Workflow CUD、无 caller graph override。SkillWorker register/heartbeat仍是 OOS，不应混入。

### R8. pre-catalog失败留下永久不可见的 final CAS

- **严重级别**：`high`
- **类型**：`correctness | security`
- **是否 blocker**：`yes`
- **事实依据**：
  - upload先 final promote，后查 Team：`src/services/object_upload.py:47-71`。
  - `LocalObjectStore._promote_staging_sync` 已 `os.replace`进 final objects树：`local_store.py:127-150`。
  - GC只从 `mkb_stored_objects`取候选：`object_gc.py:134-167`；staging reaper只扫 `staging/promote-*`：`local_store.py:243-259`。
  - NH4 action-plan明确要求 uncatalogued-CAS reconciler：`AP-NH4-public-upload-and-object-lifecycle.md:238`，HEAD未实现。
  - `test_w_nh_prom_cat_crash_no_usable_handle` 只看 catalog/stat/staging（`test_new_harvest_crash_windows.py:390-433`），没有检查 final CAS。
- **最小复现**：不存在 Team上传返回 `team-not-found`，catalog=0、staging=0、final CAS=1、GC candidates=0。
- **为什么重要**：有效 token可借无效/停用 Team、DB fault、Task conflict持续填磁盘；config/input pre-UoW promote也有同类窗口。
- **建议修法**：先校验 Team但仍保留事务后竞态防线；使用 durable promotion intent或安全的 uncatalogued final-CAS scanner；PROM-CAT测试必须断言 grace后 final file消失。

### R9. upload replay/cancel没有可寻址 session identity

- **严重级别**：`medium`
- **类型**：`protocol-drift`
- **是否 blocker**：`yes`
- **事实依据**：
  - 同 bytes命中旧 catalog会标 replay（`object_upload.py:72-103`），但每次随机新 `hold_owner`并插新 pending（`:104-120`）。
  - HTTP仍以 200表达 replay：`api/public/routes.py:136-141`。
  - `PublicObjectView/ObjectCancelRequest` 只有 content handle，无 upload session/pending token：`src/contracts/api/objects.py:12-21`。
  - cancel按 handle释放“最新任意一条”pending：`object_upload_ttl.py:62-82`。
- **最小复现**：同 body上传两次得到一个 handle、两个 owner；同 cancel请求重放会把 pending 2→1→0，响应随之 pending→expired。
- **为什么重要**：一次网络重试产生额外副作用；caller无法只取消自己的 hold，两个并发会话互相影响。
- **建议修法**：请求携带 upload idempotency key；响应返回 upload/pending UUID；同 key重放不新增 hold；cancel用 pending UUID + expected state CAS。不同 key同 bytes可以共享 catalog，但不是 HTTP replay。

### R10. selected-output 的 fact字段失实，durable evidence plane仍可改写

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `runtime_materialize.py:875-888` 把 `representation_fact_digest` 赋成 `selected["output_manifest_digest"]`。
  - migration 018的 selected-output表没有 fact UUID/digest列或 append-only trigger：`018_nh2_selected_output_control.sql:6-32`。
  - 024只保护 fact/history与 indexed时的 `content_digest`：`024_nh_review_invariants.sql:5-51`。
  - 主审实测普通 SQL可改 selected output、generation artifact content digest、indexed vector embedding；只有 fact update被拒绝。
- **为什么重要**：selection digest不能证明做路由时观察到哪条 fact；proof/artifact/vector历史可被普通应用写路径重写，客观可解释性不成立。
- **建议修法**：selection一等绑定 fact UUID/digest或 sealed path digest并加 FK；selected output、generation artifact关键 identity、vector embedding/digest/facets采用 append-only或 sealed-once trigger；publication proof重算 exact set digest。

### R11. nested public数据可绕过安全校验，并被 stage envelope成倍复制

- **严重级别**：`high`
- **类型**：`security`
- **是否 blocker**：`yes`
- **事实依据**：
  - `PayloadExtraModel` 只校验 JSON/64KiB：`src/contracts/common/models.py:24-35`。
  - Task validator只检查 root `self.payload_extra`，不检查 source/audit的 nested bag：`api/models.py:414-426`。
  - `ConfigSnapshotService._execution_payload` dump整个 payload；`redacted_request_envelope` 对非 inline原样返回，对 inline只移除 content：`config_snapshots.py:408-478`。
  - Task audit持久化该 envelope：`task_create.py:164-179`。
  - `IntakeCore._envelope_state` 直到 vectorize/publish才丢 raw/clean正文：`core.py:398-440`。
- **最小复现**：`source.payload_extra.api_token=SENSITIVE_SENTINEL` 被模型接受并写进 audit；URL/query、source extra与 raw/clean state还会随多个 stage manifest复制。
- **为什么重要**：secret/cookie/path可能进入 DB和CAS；每阶段全状态快照又形成第二 representation authority与存储放大。
- **建议修法**：所有 public nested extensibility bag统一 safe-key validator；URL只持久化 redacted identity；audit与stage采用 allowlist；acquire后正文只通过 S13 handle/digest传递，fact/history为 route authority。

### R12. `concurrent_writes_required` 没有进入 readiness/claim gate

- **严重级别**：`high`
- **类型**：`platform-fitness`
- **是否 blocker**：`yes`
- **事实依据**：
  - Settings默认 `concurrent_writes_required=True`：`src/runtime/config.py:21-25`。
  - Turso readiness明确返回 `concurrent_writes=False`：`src/persistence/turso/port.py:185-205`。
  - `HealthAggregator.BASE_REQUIRED` 不含 `concurrent_writes`：`src/runtime/health.py:15-26`。
  - `tests/unit/test_ns6_default_ready.py:16-39` 明确把 “overall ready + concurrent_writes false + worker可claim” 锁成正期待。
- **为什么重要**：new-harvest大量 race结论来自 serialized SQLite/Turso profile；production声明并发写必需却在能力为 false时继续 admission/claim，race assurance没有对应运行基础。
- **建议修法**：当 settings要求时把 `concurrent_writes`加入 overall required；不能满足则 `/ready=503`且claim fence；若产品接受单写者，必须 reopen并去掉 required，不可同时声称二者。

### R13. `10+3 live` 与 browser security只证明了 fixture/形态，没有 production closure

- **严重级别**：`high`
- **类型**：`delivery-gap | security`
- **是否 blocker**：`yes`
- **事实依据**：
  - 默认 `ns1_cli_mode="stub"`、`multimodal_enabled=False`：`runtime/config.py:41-63`；composition注入 `DeterministicNs1Stub`：`api/app.py:456-460`。
  - stub直接回显或拼 JSON：`src/runtime/inference/claude_cli.py:522-573`。
  - `tests/nh6_runtime_support.py:129-180` 的“multimodal model”是固定 HTTP handler；PDF固定文案、图片用 glyph reader。
  - production OCR identity就是 `glyph5x7`，只识别同文件定义的 A–Z/0–9 pattern：`deterministic_ocr.py:62-83`、`glyph_ocr_worker.py:1-108`；正样本又由同文件 renderer生成。
  - browser用 Firefox prefs把 proxy指向 port 9（`browser.py:249-284`），driver只有 non-root `setpriv`（`:363-387`），没有 OS network namespace/filter；测试只证明无 `no-sandbox` 与首跳 redirect policy。
  - final truth明确 `stub不得complete`：`final-execution-plan.md:60`。
- **为什么重要**：真实扫描/JPEG/普通字体、真实 model-backed DU/Vision/LLM rewrite没有 release-profile证据；browser prefs也不是完整强制 egress边界。
- **建议修法**：真实 pinned OCR/model进程、普通非同源样本、模型 hash/usage/pid、正负 probe；lane-aware admission/readiness；browser放入可验证 network namespace/allowlist proxy，并做恶意 subresource/loopback实测。若只支持 capability subset，closure按 deployed matrix降档。

### R14. 状态、错误、调试与控制 surface仍是 partial

- **严重级别**：`medium`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - unknown compiled plan重试8次后只把 outbox标 dead；Execution仍 ready、Task仍 queued、error NULL，见 `runtime_outbox.py:102-127,411-428` 与 `runtime_repair.py:99-124`。
  - lifecycle resolver不按 action检查 target state：`targets.py:79-94`；`lifecycle_apply.py:92-105` 对重复 deactivate返回 `applied=False`，但 Task仍 succeeded且 public view不暴露 applied。
  - operator timeline隐藏 event payload，只给 digest：`src/services/observability.py:389-412`；无 Process detail/current step API，也没有 diagnostic log read API。
  - object registered/ref released/deleted event type已登记但无写入者。
- **能力现状**：Task cancel、full retry、soft delete、七 intent、gate decision、logical intake delete均存在；pause/stop、process retry、dead-outbox repair、physical intake purge、workflow/capability detail缺失或deferred。
- **审查判断**：控制“能调用”不等于可解释；caller无法区分 lifecycle applied/no-op、等待 supply、dead causal intent、route mismatch。
- **建议修法**：永久 outbox错误必须终结 owner并带 retryability；非法 target state admission前409；typed Task/result/item/workflow/process read models；operator可读的安全 route/error摘要与受控 repair命令。physical delete可继续 deferred，但必须公开其 logical-only语义和 cleanup状态。

### R15. quarantine reconcile仍漏 post-tombstone与双 scanner窗口

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `reconcile_quarantine` 只 restore live catalog，tombstoned/no-row直接 continue：`object_gc.py:169-189`。
  - delete流程 quarantine → TX2 proof/tombstone → transaction外 destroy：`object_gc.py:248-315`。
- **复现**：模拟 destroy前 crash：catalog已 tombstoned、reconcile=0、quarantine仍有字节。
- **相邻竞态**：scanner B可在scanner A quarantine与TX2间 restore；A随后写 tombstone/proof，但 live CAS可能仍存在。
- **建议修法**：durable quarantine state/fencing token；只有过期 in-flight可 restore；tombstoned quarantine验证 proof后 destroy；多 scanner用 owner lease/CAS并补进程 kill测试。

### R16. NH9 closed-set/crash/evidence并未证明“完整合法边 + 真实崩溃”

- **严重级别**：`medium`
- **类型**：`test-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - closed-set generator每个 strategy只造一个 cell，丢失多个 acquire capability：`tests/fixtures/new_harvest/generate_closed_set_manifest.py:51-112`。
  - T09直接 import并调用既有 test function：`test_new_harvest_closed_set.py:558-630`；不是 manifest-driven独立 public harness。
  - crash suite主要是函数 hook、手工 UPDATE与事后 proof篡改；没有 OS process kill/restart/lease recovery。
  - PROM-CAT test漏 final CAS；publication helper可回落到 Team任意 artifact：`tests/e2e/nh7_publication.py:61-82`。
  - HEAD现有回归 `tests/unit/test_ns6_phase2.py::test_stale_fencing_fail_does_not_kill_new_generation` 实测 FAIL；`runtime_outcome.py:519-523` 的第一轮变更与旧契约未同步。
  - 两实例并发首次 migrate可出现 `table mkb_teams already exists`；`verify_migrations` 又只核 ledger checksum/少量core表，删除018–024对象后仍可能返回true：`src/persistence/migration_runner.py:109-177`。
- **为什么重要**：13=10 strategy+3 operation，不等于全部 legal edge；正是未生成的 media/acquire/retry组合暴露了 R3–R6/R8。
- **建议修法**：从 source-kind registry + strategy capabilities + compiled routes + representation predicates生成 cell；每 cell独立 public Task并绑定当前 item/revision/proof；关键 CREATE/PROCESS/PUB/GC用子进程 kill+restart，禁止事后 SQL伪造窗。

### R17. Item生命周期缺少跨Task epoch，旧 ingest/publish callback可穿越 delete/reactivate

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - deactivate/delete只改 Item/pointer/vector，不 fence 同 Item 的其它 Task/Execution：`src/services/intake_lifecycle/lifecycle_apply.py:107-147`。
  - single acceptance 对已有 Item直接更新 `latest_revision_uuid`，没有 lifecycle/epoch/row-revision条件：`src/runtime/intake/acceptance_snapshot.py:172-195`。
  - publication callback 构造 `IntakePublicationCommand` 时没有传 `expected_item_revision`：`src/runtime/intake/vector_publish_commit.py:168-190`。
  - `publish_revision_tx` 虽支持 expected revision，但当前调用缺失，只检查“此刻 active + latest相同”：`src/services/intake_lifecycle/lifecycle_publish.py:69-81`。
- **触发序列**：旧 ingest在 acceptance前被并发 delete，仍可给 deleted Item改 latest/挂 artifact；或旧 publish在 deactivate→reactivate后到达，此刻 Item再次 active，可能把旧 vector/pointer/serving重新激活。
- **为什么重要**：顺序测试只证明动作完成后 query为空，不能阻止在途旧 callback跨生命周期边界提交；这是 delete/stop语义的核心竞态。
- **建议修法**：Item增加 lifecycle/publication epoch；acquire/accept/vector/publish命令冻结 epoch + row revision并在同一 UoW CAS；delete/deactivate按 Item反查并 fence关联执行树；增加 delete/reactivate × late accept/publish全排列。

---

## 3. In-Scope 逐项对齐审核

### 3.1 NH1–NH9 closure claim

| 编号 | 阶段 claim | 结论 | 说明 |
|---|---|---|---|
| S1 | NH1 foundation contracts / proof baseline | partial | 形态与短途 proof成立；真实 model、capability manifest、selection fact不成立 |
| S2 | NH2 kind family / CONTROL / resolver / compat | partial | kind-only与shared tail成立；rev1升级、caller strategy、capability compile断裂 |
| S3 | NH3 history / actual S05 / restart | partial | 首代 seal/UoW成立；Snapshot/retry/selection lineage失败 |
| S4 | NH4 upload / pending / GC | partial | public边界与live ref成立；uncatalogued CAS、session cancel、quarantine窗未闭 |
| S5 | NH5 semantics / S06 / facets | done | 未发现独立阻断；会被上游错误 Snapshot/evidence污染 |
| S6 | NH6 runtime supply / security | partial | PDF/parser/browser形态有实现；真实 model/OCR与hard browser egress未闭 |
| S7 | NH7 10+3 live-to-retrieval | partial | deterministic/API代表格可检索；模型/OCR与完整 legal edge未证 |
| S8 | NH8 intents / exact-clean / compat | partial | exact-clean/query主边成立；非法 target no-op、lifecycle epoch、full retry、真实 upgrade不成立 |
| S9 | NH9 closed-set / race / crash / security | partial | 有较强回归集；缺完整cell、process kill、上述真实race |
| S10 | CROSS-NH campaign join | partial | 文件齐与62-node结果不能覆盖本轮 blockers |

**对齐统计**：`done 1 / partial 9 / missing 0 / stale 0 / OOS 0`。

### 3.2 第一轮 VF1–VF42 修复追踪

> 下表只沿用编号，状态全部由本轮 HEAD 复核重判。

| 本轮状态 | VF 编号 | 复核说明 |
|---|---|---|
| done | `2,5,6,8,15,16,17,22,23,25,26,28,30,31,32,40` | 指定局部修法在 HEAD可证；不表示相邻业务簇已闭 |
| partial | `1,4,7,9,11,12,14,18,24,27,29,33,41` | source-only strategy、无reservation、GC半对账、hold无session、VF24测试红、fixture supply、异常仅日志、弱race仍在 |
| missing / under-delivered | `3,10,13,19,21,38,39,42` | stage正文、full retry、uncatalogued CAS、真实 fact、kind revision、inline orphan、retirement、checker执行器未交付 |
| n/a / by-design / backend-deferred | `20,34,35,36,37` | 防御 fallback、identity IGNORE、alias fallback、预留态、backend unique文字匹配；不作为本轮blocker |

**计数**：`done 16 / partial 13 / missing 8 / n/a 5 = 42`。

关键修复簇归因：

| 修复簇 | 第一轮动作 | 第二轮归因 |
|---|---|---|
| strategy/admission | kind×strategy intersection + runtime mismatch | 只关跨-kind；public selector与同-kind representation仍断，且错误不terminal |
| schema invariant | 024 sealed/fact/vector trigger | actual/fact局部有效；selection/artifact/vector主体仍可变 |
| observation | accepted Snapshot precheck + scatter late check | 无 in-flight reservation；三个 single kind甚至复用不同 observation |
| object lifecycle | random per-upload hold + reconcile live quarantine | 没有session cancel；pre-catalog CAS不可回收；post-tombstone仍漏 |
| compat | digest evidence刷新，revision defer | 本轮graph实际又变；defer从潜在风险变成可复现升级503 |
| crash/evidence | 为JSON增加 grain，补focused tests | 文档诚实度改善；真实process kill/legal-edge coverage仍缺 |

### 3.3 三个总目标与四通道

| 目标/通道 | 结论 | 说明 |
|---|---|---|
| 四通道实际接线 | partial | 四个代表 happy path真实；每个通道至少有一个 retry/identity/supply blocker |
| dynamic workflow落地 | partial | kind-only与图执行真实；strategy policy、revision、capability compiler、discover API未闭 |
| race/error/idempotency | partial | Task UUID、seal、cancel fence有；terminal callback、observation、upload、retry、GC仍断 |
| inline_payload | partial | 到retrieval成立；same key/different body污染 Snapshot |
| local_object | partial | upload→ingest→query成立；orphan、session、media strategy、OCR/model不闭 |
| http_resource | partial | static/browser/PDF路径存在；full retry可在旧 actual下抓新字节 |
| registered_api | partial | 三operation/scatter/zero成立；in-flight observation与full retry失败 |

### 3.4 leaf-worker 可消费性

| 能力 | public | internal | verdict |
|---|---|---|---|
| source kind / intent请求枚举 | OpenAPI request可见 | registry有 | done |
| strategy列表/适用性 | public字段可见但语义错误 | Python tuple | partial |
| workflow list/detail/revision/digest | 无 | resolve-only | missing |
| Process capability/ports/proof/retry policy | 无 | 散落常量/dict | missing |
| 指定 intake进入正确 graph | source_kind可用 | resolver可用 | done |
| 指定内部 workflow/branch | 应禁止且已禁止 | exact pin内部 | done |
| 当前 Task/generation/item/gate | 有部分read API | DB完整 | partial schema |
| 当前 step/process/route/wait/error retryability | 无 | timeline也隐藏payload | missing |

### 3.5 可观测性与控制能力

| 功能 | durable truth | API可见 | 控制正确性 | 结论 |
|---|---|---|---|---|
| Task list/detail/result | yes | public | 基本正确 | done/partial-schema |
| retry / full restart | restart ledger | public | HTTP/API exactness失败 | partial |
| cancel / stop | Task/Execution/Process fence | public cancel | 无pause；合作式停止 | partial |
| Task soft delete | tombstone | public | terminal-only | done |
| intake deactivate/reactivate/delete | transition ledger | 以新 Task提交 | 重复非法态会 success no-op | partial |
| rebuild/metadata/index rebuild | restart/transition/generation | 以新 Task提交 | exact-clean主边成立 | done/partial-errors |
| Workflow/Process调试 | DB有大量事实 | 无正式 public；operator timeline信息不足 | 无process repair | missing |
| dead outbox | durable | operator read-only | 不终结owner、无repair | partial |
| object upload/GC | DB proof部分有 | stat/cancel；无GC view | orphan/session/quarantine缺口 | partial |
| physical intake purge | cleanup intent | 无 | 无executor（deferred） | deferred / logical delete only |

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 结论 | 说明 |
|---|---|---|---|
| O1 | 第五 source kind、live connector/cookie/tunnel | 遵守 | registered API frozen records仍属合法契约 |
| O2 | caller workflow_key/action_branch、general JOIN/DSL/loader | 遵守 | 本报告要求只读 discovery，不要求开放写/选图 |
| O3 | raw object GET/list/presign/R2/cloud OCR | 遵守 | 未因本轮finding要求重开 |
| O4 | existing-object new-cleaner upgrade | 遵守 | full retry修复不得偷渡 upgrade intent |
| O5 | experiment发车/评分 | 遵守 | 不进DoD |
| O6 | 前端页面实现 / answer generation | 遵守 | 本轮只审后端接口是否足够，不要求建设UI |
| O7 | SkillWorker注册/heartbeat/NACP adapter | OOS-by-design | 不等于 S03 已冻结的 Workflow只读API，可继续defer |
| O8 | physical intake purge/retention executor | deferred | NH8只承诺logical tombstone/query law；API须明确这一点 |
| O9 | S16人工签收 | 未误报 | 不要求伪造签名；R13要求的是技术边界与证据，不是签字 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **整体状态**：`核心 happy path 已建成，但完整 NH1–NH9 目标仍为 partial；CROSS-NH 的 closed claim应回退为 re-opened/changes-requested。`

### 5.1 关闭前必须完成的 blocker

1. **状态机与因果**：修复 R1、R3、R4、R17；增加 terminal-owner callback、same source different observation、HTTP mutable retry、registered API child retry、lifecycle epoch的真实回归。
2. **Workflow版本与policy**：修复 R2、R5；发布新 revision并保留exact compat，从public移除clean worker selector。
3. **Capability/leaf contract**：修复 R7；交付只读 discovery、ProcessCapabilityManifest与严格Task/result/error schema。
4. **对象与幂等**：修复 R6、R8、R9；原子observation reservation、uncatalogued CAS回收、upload session idempotency。
5. **证据与安全**：修复 R10、R11；selection绑定真实fact，关键evidence immutable，stage ref-only，nested secret fail-closed。
6. **production fitness**：修复 R12、R13；并发写能力真正gate readiness；真实pinned OCR/model与browser hard egress。
7. **assurance**：修复 R16；用graph-derived legal cells和process kill/restart重新跑NH9，不得只刷新手写JSON。

### 5.2 可后续跟进的 non-blocking follow-up

1. R14：operator process/detail、dead-outbox repair、错误 retryability与 lifecycle applied/no-op可见性。
2. R15：durable quarantine state、多scanner lease、post-tombstone cleanup。
3. 物理 intake purge继续按 retention owner承接，但公开文档必须明确 logical delete边界。
4. old-pin bounded retirement需要真实 inventory/planner；在此之前可保留旧定义，但不能声称已完成retirement。

### 5.3 建议修复 DAG

```text
P0-A terminal Outcome fence ─┐
P0-B Snapshot/observation  ──┼─> P1 retry/replay matrix
P0-C graph revision/compat ──┘
P0-D Item lifecycle epoch ───┘

P0-E uncatalogued CAS + upload session ─> P1 GC/quarantine

P0-F remove public strategy selector
  └─> capability manifest/compiler
       └─> workflow readonly API + strict OpenAPI

P1 evidence immutability + ref-only stage
P1 production readiness/concurrent writes/model/browser
  └─> P2 graph-derived legal-set + process-kill NH9
       └─> independent rereview + CROSS closure
```

- **建议的二次审查方式**：`independent reviewer + persisted-upgrade fixture + adversarial rereview`
- **实现者回应入口**：请按 `.adocs/templates/code-review-respond.md` 在本文档 §6 append 回应，不要改写 §0–§5。

> 本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。
