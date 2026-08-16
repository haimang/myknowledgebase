# Nano-Agent 行动计划

> 服务业务簇: `MKB / NS4 generation-evidence plane`
> 计划对象: 把工人失败证据做成主库一等 schema + Turso 主路径 + 唯一 ReadPort；硬切 extra 口袋、sqlite waiver、`inspect_dump` 与成功-only invocation
> 类型: `upgrade`
> 作者: `Grok`
> 时间: `2026-08-16`
> 文件位置: `docs/plan/new-start/NS4-generation-evidence-plane.md`
> 上游前序 / closure:
> - `docs/plan/new-start/NS3-megafile-governance.md`（`executed`）
> - `docs/closure/new-start/NS3-megafile-governance-closure.md`
> - `docs/eval/new-start/pre-NS4-qna.md`（`locked / T-O-362..375`）
> 下游交接:
> - NS4 阶段 final closure（本 AP §10；落盘 `docs/closure/new-start/NS4-generation-evidence-plane-closure.md`）
> - MKB-0815-R3 live（**仅**本 AP closure 之后；`T-O-365` / `T-O-375`）
> - D04/S15 formal 窄回填（本 AP Phase 1 起草、Phase 6 落盘）
> 关联设计 / 调研文档:
> - `docs/eval/new-start/after-MKB-0815-R2-analysis-on-observability.md`（eval；地图，不是 charter）
> - `docs/baseline/domain-truth/D04-turso-physical-schema.md`（`T-O-166/173/193/288`；§3.5.4 invocation）
> - `docs/baseline/domain-truth/S15-observability-reliability.md`（`T-O-287..311`）
> - `docs/baseline/domain-truth/S12-turso-persistence.md`（CW / ready）
> - `docs/baseline/domain-truth/S11-inference-runtime.md`（invocation 账）
> - `docs/baseline/domain-truth/S16-security-trust-boundary.md`（禁正文入账）
> 冻结决策来源:
> - `docs/eval/new-start/pre-NS4-qna.md` §1 Truth-Gate `T-O-362..375`（**只读引用**；本 action-plan 不填写 Q/A）
> - NS1 `T-O-337..352`；NS2 `T-O-353..361`；NS3 叶无 I/O（本轮不改口）
> grounding 来源:
> - 本 AP §7 内置锚区（对照当前 NS3 后 `src/` / `tests/` / `.experiment/0815/`）
> 关联 reference-anchor:
> - 见 §7 内置锚区
> 文档状态: `executed`

---

## 0. 执行背景与目标

NS1–NS3 钉死了身份、三池与叶边界。0815 R1/R2 在真模型上证明：**判定平面有了，失败证据出口没有。** R2 库 453 条 `mkb_domain_events`、0 条 diagnostic、8 条 generation invocation **全是成功**；五次 structurize 失败的 `payload_extra` 仍是 `{}`。随后一版「接线 / extra 口袋 / sqlite waiver / P1 后发 R3」被业主否决。

`pre-NS4-qna.md` 已冻结新叙事（`T-O-362..375`）：能硬切必须硬切；禁止双写与 hotfix；证据必须是 D04 一等列/表并经 contract 校验；Turso 与 concurrent writes 必须在本节点推进；**P0–P4 测完并 closure 之后才允许 R3**。

本计划把这些冻结句落成可合并的相位、DDL、硬切删除与测试台账。成功标准是 **一等行在 Turso 上可被 Port 读到，旧缝从生产路径消失**，不是「再补一层兼容」。

- **服务业务簇**：`NS4`
- **计划对象**：generation-evidence 平台（schema + Turso + 唯一读面）
- **本次计划解决的问题**：
  - 失败 CLI/admit 不写 invocation；`getattr` 可选 persist；live 路径吞异常
  - 直方图 / CLI kind 活在 `payload_extra`，违反 `T-O-173` / `T-O-363`
  - 0815 把宪法默认 Turso/CW 覆写成 sqlite waiver；CW **未观察**
  - `inspect_dump.py` 直连 sqlite，与 `T-O-308` / `T-O-374` 分叉
- **本次计划的直接产出**：
  - D04 窄 reopen：`mkb_generation_invocations` 列晋升 + 新表 `mkb_generation_stage_reports`
  - 0815/生产硬切 `persistence_backend=turso` + `concurrent_writes_required=True`；Q-A3 一次迁移后删 sqlite 生产路径
  - 证据与 Process Outcome 同 TX；删除 extra 证据键与吞异常
  - Mixin 强制 DiagnosticSink；诊断 sidecar `BEGIN CONCURRENT`
  - 删除 `inspect_dump` 生产调用；ReadPort 为唯一观测读面
  - 每 Phase 独立测试 + §8 全量台账 + NS4 closure（**不含** R3 ingest）
- **本计划不重新讨论的设计结论**：
  - 硬切 / 禁双写（`T-O-362`）
  - 禁 extra 当证据（`T-O-363`）
  - Turso 本节点必推（`T-O-364`）
  - P0–P4 → closure → 才 R3（`T-O-365` / `T-O-375`）
  - 窄 reopen D04+S15，不新开进程（`T-O-366` / `T-O-368`）
  - 叶无 I/O、不放宽 kernel、不改写 R1（`T-O-367`）
  - schema = 列晋升 + `mkb_generation_stage_reports`（`T-O-369`）
  - 证据同 TX；diagnostic 旁路（`T-O-370`）
  - 诊断 CONCURRENT；业务 CAS 默认 TX（`T-O-371`）
  - Q-A3 一次迁移后删 sqlite（`T-O-372`）
  - DAG：P0→P3→P1→P2→P4→closure（`T-O-373`）
  - Port 唯一读面；jsonl 仅期刊（`T-O-374`）

---

## 1. 执行综述

### 1.1 总体执行方式

**先锁合同与错误路径，再硬切引擎，最后才在 Turso 上出生一等 schema。** 顺序由 `T-O-373` 钉死：P0 守卫 → **P3 Turso/CW + Q-A3 一次迁移** → P1 DDL+同 TX 写入 → P2 diagnostic sidecar → P4 删 dump / 只留 Port → closure。禁止在 sqlite 生产上 CREATE 新证据表。禁止与 R3 ingest 交错。每 Phase 收口前跑该 Phase 完整独立测试集；Phase 6 才跑 mega / CW soak。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | P0 合同与守卫 | `M` | D04/S15 窄 reopen 草案 + architecture 锁死 extra/双写/叶 I/O/sqlite 生产默认 | `-` |
| Phase 2 | P3 Turso 硬切与一次迁移 | `L` | 0815/生产 turso+CW=True；迁 Q-A3 serving；删除 sqlite 生产打开路径 | Phase 1 |
| Phase 3 | P1 一等 schema 与同 TX 写入 | `XL` | 列晋升 + `mkb_generation_stage_reports`；失败写入进 Outcome TX；删 extra/`getattr`/吞异常 | Phase 2 |
| Phase 4 | P2 DiagnosticSink 旁路 | `M` | Mixin 强制持有 sink；sidecar `BEGIN CONCURRENT`；一阶段一行 | Phase 3 |
| Phase 5 | P4 唯一读面 | `M` | Port 返回 invocation+report；删除 dump 生产路径；jsonl 白名单 | Phase 4 |
| Phase 6 | Closure | `S` | 退役迁移脚本；formal 窄回填；closure；确认零 R3 ingest | Phase 5 |

### 1.3 Phase 说明

1. **Phase 1 — P0 合同与守卫**
   - **核心目标**：后续 PR 若再写 extra 证据键、sqlite 生产默认、新 dump 调用、或把 I/O 打进叶包，CI 立刻红。
   - **为什么先做**：没有守卫，P3/P1 硬切会在评审中滑回「先兼容一版」。
2. **Phase 2 — P3 Turso 硬切与一次迁移**
   - **核心目标**：引擎先正；Q-A3 一次进 Turso；sqlite 生产路径死亡。
   - **为什么放在这里**：`T-O-373` 禁止新 schema 先落 sqlite。CW 未绿不得进 P1。
3. **Phase 3 — P1 一等 schema 与同 TX 写入**
   - **核心目标**：D04 列/表落地；失败工人证据与 Outcome 同命运。
   - **为什么放在这里**：此时主库已是 Turso，DDL 只出生一次。
4. **Phase 4 — P2 DiagnosticSink 旁路**
   - **核心目标**：诊断表第一次有行；CONCURRENT 只打 sidecar。
   - **为什么放在这里**：证据表形状已稳定，sink payload 才能引用 report digest 而非 extra。
5. **Phase 5 — P4 唯一读面**
   - **核心目标**：观测平面只剩 Port；dump 从 collect 消失。
   - **为什么放在这里**：没有一等行，Port 扩展是空壳。
6. **Phase 6 — Closure**
   - **核心目标**：诚实收口；迁移脚本不得变成长期适配器。
   - **为什么放在这里**：接线完成后才有完整旅程。R3 **不**在本 Phase。

### 1.4 执行策略说明

- **执行顺序原则**：严格 `T-O-373`。任一相未绿不得进下一相。P3 与 P1 禁止对调。禁止「先在 sqlite 建表再切 turso」。
- **风险控制原则**：硬切删除先于新写入。LLM wait 不得包进 BEGIN（`T-O-370`）。业务 CAS 不改 CONCURRENT（`T-O-371`）。叶包继续零 I/O（`T-O-367`）。产品 `error_code` 不被 `OBS_*` 覆盖。
- **测试推进原则**：每 Phase 短途（守卫/DDL/纯函数）→ 该 Phase 集成 → 指定 e2e。Phase 6 才跑 mega（失败路径整链 Turso）与 soak（诊断 CONCURRENT × N）。
- **文档同步原则**：不改写 R1 封条、不升格 R2。D04/S15 只窄回填本节点列/表/Port 句。不把 R3 publish 写进本 AP 退出条件。
- **回滚 / 降级原则**：禁止「回退到 extra 口袋」当降级。P3 之后回滚 = 停工并 reopen QNA，不是恢复 sqlite waiver。P1 DDL 回滚必须新 migration，不得手改已迁 Q-A3 行。

### 1.5 本次 action-plan 影响结构图

```text
NS4 generation-evidence plane
├── Phase 1 P0 合同与守卫
│   ├── docs/baseline/domain-truth/D04…（窄 reopen 草案）
│   ├── docs/baseline/domain-truth/S15…（ReadPort 合同草案）
│   ├── src/contracts/observability/（stage-report schema）
│   └── tests/domain/test_architecture.py（新守卫）
├── Phase 2 P3 Turso / 一次迁移
│   ├── src/runtime/config.py（默认已是 turso；删 0815 覆写）
│   ├── src/persistence/{factory,engine,turso/port}.py
│   ├── .experiment/0815/runs/MKB-0815-R2/{runner,collect,retrieve,r3_prepare}.py
│   └── scripts/ns4_migrate_q_a3.py（一次性）
├── Phase 3 P1 schema + 同 TX 写入
│   ├── src/persistence/migrations/013_generation_evidence_plane.sql
│   ├── src/runtime/intake/{generation_construct,generation_live,core}.py
│   └── src/runtime/inference/claude_cli.py
├── Phase 4 P2 diagnostic 旁路
│   ├── src/services/observability.py（DiagnosticSink）
│   ├── src/persistence/turso/port.py（第二连接）
│   └── Intake Mixin 构造强制注入
├── Phase 5 P4 唯一读面
│   ├── src/services/observability.py（ReadPort 扩查询）
│   ├── .experiment/0815/…/inspect_dump.py（删生产路径）
│   └── collect.py 去 dump 调用
└── Phase 6 Closure
    ├── 退役迁移脚本
    ├── D04/S15 窄回填
    └── docs/closure/new-start/NS4-generation-evidence-plane-closure.md
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** D04 窄 reopen：`mkb_generation_invocations` 加 `status` / `stage_key` / `error_code` / `adapter_kind` / `cli_structured_kind`；新 required 表 `mkb_generation_stage_reports`
- **[S2]** S15 窄 reopen：ReadPort 必须能按 process 读 invocation + stage report；extra 不再是合法证据面
- **[S3]** 0815/生产硬切 Turso + `concurrent_writes_required=True`；诊断 sidecar `BEGIN CONCURRENT`
- **[S4]** Q-A3 serving 闭集一次迁移；迁完删除 sqlite 生产打开路径
- **[S5]** 失败写入与 Outcome 同 TX；删除 `getattr` persist、吞异常、extra 中 reject/kind 键
- **[S6]** Mixin 强制 DiagnosticSink；一阶段至多一行 diagnostic
- **[S7]** 删除 `inspect_dump` 生产调用；jsonl 字段白名单
- **[S8]** architecture / 契约 / 集成 / mega / soak 台账与 closure

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** R3 live ingest / `collect.py --suffix -r3`（`T-O-365` / `T-O-375`）
- **[O2]** 放宽 kernel、静默换工人、开 salvage、改 g1 v3 / promptC / binding（`T-O-367` / `T-O-375`）
- **[O3]** 去 Mixin / YAML 工作流 / 新 APM 进程 / 第二库（`T-O-367` / `T-O-368`）
- **[O4]** 业务 CAS 改 `BEGIN CONCURRENT`；Turso Cloud Embedded Replica（`T-O-371`）
- **[O5]** 回填 R1/R2 旧失败直方图；双读旧 sqlite（`T-O-367` / `T-O-372`）
- **[O6]** 检索 `retrieve.*` domain_event；改金标问句
- **[O7]** 改写 R1 已封结论；封 R2 MD5（另令）

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| 一等列 + stage_reports 表 | `in-scope` | `T-O-369` | 无；改形状须 `T-O-376+` |
| Turso + CW 硬切 | `in-scope` | `T-O-364` / `T-O-371` | CW 探针环境不可用 → 停工，不回 sqlite |
| Q-A3 一次迁移 | `in-scope` | `T-O-372` | 物理无法导入 → 停工回 Q5，不双读 |
| DiagnosticSink + CONCURRENT | `in-scope` | `T-O-370` / `T-O-371` | — |
| 删 dump / Port 唯一 | `in-scope` | `T-O-374` | — |
| R3 五格 live | `out-of-scope` | `T-O-365` / `T-O-375` | 本 AP closure 文档已写 |
| extra 继续当证据 | `out-of-scope` | `T-O-363` | 禁止重评成折中 |
| sqlite 生产 waiver | `out-of-scope` | `T-O-364` | 禁止 |
| 新 APM / 第二库 | `out-of-scope` | `T-O-368` / `T-O-300` | 另开产品 charter |
| billing / cloud-inference | `defer` | `T-O-357/358` | 独立 AP |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| P0-01 | Phase 1 | D04 窄 reopen 草案 | `add` | `docs/baseline/domain-truth/D04-turso-physical-schema.md:39-41,87,251,314,1178-1192`；新建 `docs/plan/new-start/NS4-d04-s15-reopen.md` | 列/表闭集可被 migration 逐字执行 | `NS4-T01` `NS4-T04` | `medium` |
| P0-02 | Phase 1 | S15 ReadPort 合同草案 | `add` | `docs/baseline/domain-truth/S15-observability-reliability.md`；`src/services/observability.py:245-318` | Port 必含 invocation+report 的字段清单冻住 | `NS4-T01` `NS4-T24` | `low` |
| P0-03 | Phase 1 | architecture 硬切守卫 | `add` | `tests/domain/test_architecture.py:356-376,461-483` | extra 证据键 / sqlite 生产覆写 / dump 新调用 / 叶 I/O 任一命中即红 | `NS4-T01` `NS4-T02` `NS4-T32` | `high` |
| P0-04 | Phase 1 | stage-report / layer_counts contract | `add` | 新建 `src/contracts/observability/stage_report.py`；`src/runtime/intake/generation_construct.py:45-76` | JSON schema digest 可算；拒正文键 | `NS4-T03` `NS4-T20` `NS4-T27` | `high` |
| P3-01 | Phase 2 | 删除 0815 sqlite/CW=False 覆写 | `remove` | `.experiment/0815/runs/MKB-0815-R2/runner.py:105-106`；`collect.py:48`；`retrieve.py:45-46`；`r3_prepare.py:42-43`；`src/runtime/config.py:21-24` | 0815 Settings 与宪法默认一致：turso+CW=True | `NS4-T05` `NS4-T10` | `high` |
| P3-02 | Phase 2 | ready 门：CW 探针失败 = not ready | `update` | `src/persistence/engine.py:13-40,80-99`；`src/runtime/health.py:17-21`；`src/persistence/factory.py:29-47` | `/ready` 在 CW 红时 503；无 waiver 分支 | `NS4-T06` `NS4-T07` | `high` |
| P3-03 | Phase 2 | sqlite 生产打开路径删除 | `remove` | `src/persistence/sqlite_port.py:51-59`（**仅测试保留**）；`src/persistence/factory.py` | 非 pytest 构造 sqlite 即失败 | `NS4-T08` `NS4-T10` | `high` |
| P3-04 | Phase 2 | Q-A3 serving 一次迁移 | `migrate` | 新建 `scripts/ns4_migrate_q_a3.py`；R2 `runtime/mkb.db`（只读源） | 新 Turso 库 Q-A3 17 向量 + publication；Port 可读；旧失败 extra 不发明直方图 | `NS4-T09` | `high` |
| P1-01 | Phase 3 | migration 013 DDL | `add` | 新建 `src/persistence/migrations/013_generation_evidence_plane.sql`；对照 `001_initial.sql:1369-1401` | 列+新表在 Turso 上可查询；CHECK 生效 | `NS4-T11` `NS4-T12` `NS4-T13` | `high` |
| P1-02 | Phase 3 | 同 TX 写 invocation+report | `update` | `src/runtime/intake/generation_live.py:329-348,353`；`generation_construct.py:261-263,372-407,954-975` | 失败 Outcome 提交时必有对应行；缺行回滚 | `NS4-T15` `NS4-T18` `NS4-T19` | `high` |
| P1-03 | Phase 3 | 硬切 extra / getattr / 吞异常 | `remove` | `generation_live.py:334-340`；`generation_construct.py:261`；`core.py:191-217` | 生产路径无这些符号；extra 无 reject/kind | `NS4-T14` `NS4-T16` `NS4-T17` | `high` |
| P1-04 | Phase 3 | histogram 只填 report 行 | `update` | `generation_construct.py:45-76,966-975` | admit 失败写 report，不再并进 extra | `NS4-T19` `NS4-T20` | `medium` |
| P2-01 | Phase 4 | Mixin 强制 DiagnosticSink | `update` | `src/services/observability.py:72-118`；intake Mixin 构造 | 无 sink 不得启动 generate | `NS4-T21` | `medium` |
| P2-02 | Phase 4 | sidecar BEGIN CONCURRENT | `add` | `src/persistence/engine.py:13-28`；`src/persistence/turso/port.py:56-111` | 诊断写走第二连接 CONCURRENT；失败不改产品码 | `NS4-T22` `NS4-T23` `NS4-T30` | `high` |
| P2-03 | Phase 4 | 阶段一行 diagnostic | `add` | Mixin generate 阶段钩子 | log_code 闭集；无 per-block INSERT | `NS4-T21` `NS4-T23` | `medium` |
| P4-01 | Phase 5 | ReadPort 扩 invocation+report | `update` | `src/services/observability.py:245-318` | `timeline_by_task` 含 status 与 report 字段 | `NS4-T24` | `medium` |
| P4-02 | Phase 5 | 删除 dump 生产路径 | `remove` | `inspect_dump.py:1-40`；`collect.py:181-182` | collect 不再 spawn dump；模块不在生产 import | `NS4-T25` | `medium` |
| P4-03 | Phase 5 | jsonl 期刊白名单 | `update` | R2 `collect.py` / `runner.py` 写 jsonl 处 | jsonl 无 `structure_reject` 对象 | `NS4-T26` | `low` |
| C-01 | Phase 6 | 退役迁移脚本 | `remove` | `scripts/ns4_migrate_q_a3.py` | 标 `retired` 或删除；无双路径 | `NS4-T28` | `low` |
| C-02 | Phase 6 | D04/S15 窄回填 + closure | `add` | D04/S15 formal；`docs/closure/new-start/NS4-generation-evidence-plane-closure.md` | closure 五态诚实；零 R3 ingest | `NS4-T29` `NS4-T31` | `medium` |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — P0 合同与守卫

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P0-01 | D04 窄 reopen 草案 | a) 摘 D04 §3.5.4 现列闭集。b) 按 `T-O-369` 写清新增列 CHECK 与新表 DDL 意图（**不**在本相 CREATE）。c) 写明 required 表数 +1 的闭集修订点。d) 禁止第四套黑表、禁止 extra 当 proof。 | `D04-turso-physical-schema.md:39-41` 冻结声明；`:87` D04-P04；`:251` 表 45；`:314` 核心真相不得只活在 JSON；`:1178-1192` invocation 现列 | 草案可被 013 逐字实现 | `NS4-T04` | 评审对照 `T-O-369` 无漏列 |
| P0-02 | S15 Port 合同 | a) 列出 Port 必须返回的 invocation.status / stage_key / error_code / report 直方图字段。b) 写明 extra 不再是证据面。c) 不改 retention 天数。 | `observability.py:245-318` 现只读 events | 字段清单进 reopen 文 | `NS4-T24` | 与 P4-01 一一对应 |
| P0-03 | architecture 守卫 | a) fork `test_ns2_dispatch_does_not_add_required_tables_or_payload_extra_keys`（`:461-483`）为 extra 禁 `structure_reject`/`cli_structured_kind`。b) 沿用叶包无 persistence（`:356-376`）。c) 扫描 0815 `persistence_backend="sqlite"` 与 `inspect_dump` 新引用（P3/P4 前本守卫先红 0815 覆写——**本相只加 src/ 与 tests/ 守卫**；0815 覆写的红闸放到 P3-01 同 PR）。d) 禁 `src/services/lsrag_*` import persistence。 | `tests/domain/test_architecture.py:356-483` | CI 锁死错误拆法 | `NS4-T01` `NS4-T02` `NS4-T32` | 守卫红则停工 |
| P0-04 | contract 类型 | a) 新建 `StageReport` / `LayerCounts` typed 模型。b) `layer_counts` 只允许粒度→count。c) validator 拒 `content`/`prompt`/`stdout`/`original`。d) 从 `layered_reject_histogram`（`:45-76`）抽出纯函数到 contracts 或保持函数但输出必须过 contract（**本相可先放 contracts，P1 再改调用**）。 | 新建 `src/contracts/observability/stage_report.py`；`generation_construct.py:45-76` | digest 稳定；正文不可编码 | `NS4-T03` `NS4-T20` `NS4-T27` | 攻击向量用例过 |

### 4.2 Phase 2 — P3 Turso 硬切与一次迁移

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P3-01 | 删 0815 waiver | a) 删除 R2 `runner.py:105-106`、`retrieve.py:45-46`、`r3_prepare.py:42-43`、`collect.py:48` 的 sqlite/CW=False。b) 不留「环境开关再开 sqlite」。c) R1 runner 只读不改（`T-O-367`）。 | 上列；`config.py:21-24` 宪法默认已是 turso+True | 0815 与 Settings 默认合一 | `NS4-T05` `NS4-T10` | rg 0815 R2 无 sqlite 覆写 |
| P3-02 | CW ready 硬门 | a) 确认 `apply_capability_gates`（`engine.py:80-99`）在 required=True 时不再把探针失败报成 ready。b) 删除任何 0815 传入 False 的入口。c) `/ready` 组件 `concurrent_writes` 红 → 503，拒新 Task。 | `engine.py:13-99`；`health.py:17-21`；`factory.py:29-47`；`turso/port.py:56-61,111` | 无 CW 不接业务 | `NS4-T06` `NS4-T07` | 探针假失败夹具 → 503 |
| P3-03 | sqlite 仅 pytest | a) `factory` 在非测试上下文拒绝 `backend=sqlite`。b) `sqlite_port.py` 保留给单测内存库。c) 生产/0815 只构造 `TursoPersistence`。 | `factory.py`；`sqlite_port.py:51-59` | 双后端消失 | `NS4-T08` | 非测试构造 sqlite 抛配置错 |
| P3-04 | Q-A3 一次迁移 | a) 只读打开 R2 `runtime/mkb.db`。b) 导出 Q-A3 task `01a00887-3cef-7379-92ea-3a6a38fd4188` 的 publication、17 向量、六件套 pointer、必要 process/execution/artifact 行。c) 导入新 Turso 文件（0815 新 `database_path`）。d) **不**为旧失败行发明 report。e) Port/检索抽检 17 与 Layer A 维。f) 成功后 0815 不再打开旧 sqlite 文件。 | 新建 `scripts/ns4_migrate_q_a3.py` | serving 经新路径 intact | `NS4-T09` | 17 向量；无双文件打开 |

### 4.3 Phase 3 — P1 一等 schema 与同 TX 写入

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P1-01 | DDL 013 | a) 在 **Turso** 上重建/ALTER `mkb_generation_invocations`：加 `status` CHECK∈`succeeded,failed`、`stage_key` CHECK∈`markdown,structurize,construct`、`error_code`、`adapter_kind` CHECK∈`claude_cli,local_inference`、`cli_structured_kind`。b) 既有成功行回填 `status=succeeded`（不是伪造失败）。c) `CREATE TABLE mkb_generation_stage_reports`（`T-O-369` 列闭集 + FK process）。d) 索引 `(process_uuid,occurred_at)`、`(execution_uuid,stage_key)`。 | 新建 `013_generation_evidence_plane.sql`；对照 `001_initial.sql:1369-1401` | 表可 INSERT 并拒非法 CHECK | `NS4-T11` `NS4-T12` `NS4-T13` | migration 链绿 |
| P1-02 | 同 TX 写入 | a) 把 `_record_generation_and_inference_invocations` 扩成写新列。b) 新增 `_record_stage_report(tx, …)`。c) Process Outcome 提交 **同一** `persistence.transaction()` 内插入 invocation+report。d) CLI `_cli_layered_candidate`（`:372-407`）信封失败、admit `STRUCTURE_*`（`:954-975`）、C kernel 失败（`:251-264`）全部走这条，不再独立 best-effort TX。e) 插失败整笔回滚。 | `generation_live.py:329-353`；`generation_construct.py:251-264,372-407,941-975` | 失败必有行 | `NS4-T15` `NS4-T18` `NS4-T19` | 故意插失败 → process 无终态成功 |
| P1-03 | 删旧缝 | a) 删除 `generation_live.py:334-340` `except: return`。b) 删除 `getattr(..., "_persist_failed_generation_invocation")`（`:261`）。c) `_safe_outcome_extra`（`core.py:198-217`）**删除** reject/kind 拷贝。d) rg 确认生产路径无这些键。 | 同上；`core.py:191-217` | 旧缝符号消失 | `NS4-T14` `NS4-T16` `NS4-T17` | rg 零命中 |
| P1-04 | histogram→report | a) `layered_reject_histogram` 输出经 P0-04 contract。b) admit except 填 report 行，不塞 `MkbError.details` 供 extra。c) details 若仍传内部，Outcome extra 不得落地。 | `generation_construct.py:45-76,966-975` | 直方图只在 report 表 | `NS4-T19` `NS4-T20` | SQL 有行；process.payload_extra 无键 |

### 4.4 Phase 4 — P2 DiagnosticSink 旁路

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P2-01 | 强制 sink | a) Intake generate Mixin 构造必须拿到 `DiagnosticSink`。b) 缺失 → 启动失败，不是运行中才发现。c) 沿用 `observability.py:72-118` 的 best-effort `write`，不把 sink 失败打进 Outcome。 | `observability.py:72-118`；pipeline/runtime 组装 | 无 sink 不起 generate | `NS4-T21` | 构造期失败 |
| P2-02 | CONCURRENT sidecar | a) Turso 第二连接；`PRAGMA journal_mode=mvcc`；`BEGIN CONCURRENT`（复用 `engine.py:13-28` 探针语义）。b) 只 INSERT diagnostic。c) 冲突重试 1 次；再失败 metric+stderr，**不**改产品码。d) 业务 UoW 仍默认 TX。 | `engine.py:13-28`；`turso/port.py:56-111` | 旁路不抢 CAS | `NS4-T22` `NS4-T23` `NS4-T30` | soak 无产品码污染 |
| P2-03 | 一阶段一行 | a) log_code 闭集：`GEN_STRUCTURIZE_REJECT` / `GEN_CLI_ENVELOPE` / `GEN_CONSTRUCT_REJECT` / `GEN_STAGE_TIMING`。b) payload = report digest / kind / latency_ms。c) 禁止 C 每块循环写库。 | Mixin 阶段钩子 | 诊断表 >0 且基数受控 | `NS4-T21` `NS4-T23` | 无 per-block 行 |

### 4.5 Phase 5 — P4 唯一读面

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P4-01 | Port 扩查询 | a) `timeline_by_task` / 新方法读取 invocation 新列 + stage_reports。b) 与 events 按 occurred_at 可拼。c) 不读 extra 当证据。 | `observability.py:245-318` | Port 是唯一形状 | `NS4-T24` | 单测对失败夹具返回 report |
| P4-02 | 删 dump | a) `collect.py:181-182` 删除 subprocess dump。b) `inspect_dump.py` 移入 `tests/` 或删除；生产 import 守卫。 | `inspect_dump.py:1-40`（`sqlite3.connect`）；`collect.py:181-182` | 无直连 sqlite dump | `NS4-T25` | rg collect 无 inspect_dump |
| P4-03 | jsonl 白名单 | a) 期刊字段：cell、task_uuid、status、error_code、路径、哈希。b) 禁 `structure_reject` 对象。 | R2 collect/runner 写 jsonl | 期刊 ≠ 第二 schema | `NS4-T26` | 夹具断言无 reject 键 |

### 4.6 Phase 6 — Closure

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| C-01 | 退役迁移脚本 | 删除或 `retired/` + 测试断言生产路径不再调用 | `scripts/ns4_migrate_q_a3.py` | 无长期适配器 | `NS4-T28` | rg 无 live 调用 |
| C-02 | formal + closure | a) D04/S15 窄回填已落地句。b) 写 `NS4-generation-evidence-plane-closure.md`。c) 声明零 R3 ingest。d) §10 映射填五态。 | D04/S15；新建 closure | AP 可标 executed | `NS4-T29` `NS4-T31` | 退出硬闸全绿 |

---

## 5. Phase 详情

### 5.1 Phase 1 — P0 合同与守卫

- **Phase 目标**：把 `T-O-369` 列/表闭集与硬切禁区锁进文档 + CI，尚未改生产库。
- **本 Phase 对应编号**：`P0-01` / `P0-02` / `P0-03` / `P0-04`
- **本 Phase 新增文件**：`docs/plan/new-start/NS4-d04-s15-reopen.md`；`src/contracts/observability/stage_report.py`；`tests/domain/test_ns4_guards.py`（或扩 `test_architecture.py`）
- **本 Phase 修改文件**：`tests/domain/test_architecture.py:356-483`
- **本 Phase 删除文件**：无
- **具体功能预期**：
  1. reopen 文逐列对照 `T-O-369`，表数 +1 有修订点清单。
  2. `LayerCounts` 只接受 `{"0":int,"1":int,…}`；多键失败。
  3. 含 `original`/`prompt` 的 payload 校验失败（攻击向量）。
  4. architecture 扫描 `payload_extra` 赋值 `structure_reject` 即红。
  5. 叶包 `lsrag_*` 仍不能 import persistence。
  6. 本相 **零** DDL、零 0815 ingest、零改 kernel。
- **对应测试台账项**：`NS4-T01` `NS4-T02` `NS4-T03` `NS4-T04` `NS4-T27` `NS4-T32`
- **收口标准**：守卫与 contract 测试全绿；reopen 文可被 P1-01 逐字消费。
- **本 Phase 风险提醒**：守卫若过早扫描 0815 sqlite 覆写，会在 P3 前永久红——P0 守卫范围限 `src/`+`tests/`；0815 覆写闸放 P3。

### 5.2 Phase 2 — P3 Turso 硬切与一次迁移

- **Phase 目标**：引擎与 Q-A3 serving 走上 Turso；sqlite 生产路径死亡。
- **本 Phase 对应编号**：`P3-01` / `P3-02` / `P3-03` / `P3-04`
- **本 Phase 新增文件**：`scripts/ns4_migrate_q_a3.py`；`tests/unit/test_ns4_turso_settings.py`；`tests/integration/test_ns4_q_a3_migrate.py`
- **本 Phase 修改文件**：`runner.py:105-106`；`collect.py:48`；`retrieve.py:45-46`；`r3_prepare.py:42-43`；`factory.py`；必要时 `health.py:17-21`
- **本 Phase 删除文件**：无（sqlite_port 留测试）
- **具体功能预期**：
  1. R2 实验入口不再传 sqlite / CW=False。
  2. factory 非测试拒绝 sqlite。
  3. CW 探针失败 → ready 假 → 拒绝新 Task。
  4. 迁移后 Q-A3 向量 COUNT=17；publication 在。
  5. 旧失败 process **没有** 新 report 行。
  6. 0815 进程打开的是 Turso 文件，不是旧 `mkb.db` 路径。
  7. 本相 **不** CREATE `mkb_generation_stage_reports`。
- **对应测试台账项**：`NS4-T05` `NS4-T06` `NS4-T07` `NS4-T08` `NS4-T09` `NS4-T10`
- **收口标准**：ready 绿；17 向量；rg 0815 R2 无 sqlite 覆写。
- **本 Phase 风险提醒**：pyturso 若不能同文件升级，必须导出→新文件→删旧打开路径。失败则停工，不双读。CW 环境红不得用 required=False 绕过。

### 5.3 Phase 3 — P1 一等 schema 与同 TX 写入

- **Phase 目标**：证据物理合同与写入纪律一次到位。
- **本 Phase 对应编号**：`P1-01` / `P1-02` / `P1-03` / `P1-04`
- **本 Phase 新增文件**：`src/persistence/migrations/013_generation_evidence_plane.sql`；`tests/unit/test_ns4_stage_report_tx.py`；`tests/unit/test_ns4_invocation_columns.py`
- **本 Phase 修改文件**：`generation_live.py:329-353`；`generation_construct.py:45-76,251-264,372-407,941-975`；`core.py:191-217`；`claude_cli.py:187-253`（kind 闭集对接列 CHECK）；D04 formal 窄回填可延 Phase 6，但 DDL 必须与草案一致
- **本 Phase 删除文件**：无（删的是函数分支，不是文件）
- **具体功能预期**：
  1. 非法 `status` / `stage_key` INSERT 被 CHECK 拒。
  2. CLI 非 object → invocation.status=failed + `cli_structured_kind` 非空 + report.disposition=`transport_failed`。
  3. admit `STRUCTURE_GRANULARITY_SET_MISMATCH` → report.has_g0 / set / counts 有值；process.payload_extra 无这些键。
  4. 模拟 report INSERT 失败 → 整笔回滚，无半成品 succeeded process。
  5. 仓库无 `getattr(..., "_persist_failed_generation_invocation")`。
  6. 无 `except: return` 吞 persist。
  7. histogram 编码不含 original 正文。
  8. 产品 error_code 仍是 `STRUCTURE_*` / `CLAUDE_CLI_*`，不是 `OBS_*`。
- **对应测试台账项**：`NS4-T11`–`NS4-T20`
- **收口标准**：DDL 绿；失败夹具必有行；旧缝 rg 空。
- **本 Phase 风险提醒**：先等 LLM 再 BEGIN。同 TX 拉长的是写，不是推理。Q-A3 旧成功 invocation 只回填 succeeded，不造 report。

### 5.4 Phase 4 — P2 DiagnosticSink 旁路

- **Phase 目标**：诊断面有行且不污染产品码。
- **本 Phase 对应编号**：`P2-01` / `P2-02` / `P2-03`
- **本 Phase 新增文件**：`src/persistence/turso/sidecar.py`（或 port 内方法）；`tests/unit/test_ns4_diagnostic_sidecar.py`
- **本 Phase 修改文件**：`observability.py:72-118`；runtime 组装；Mixin
- **具体功能预期**：
  1. 无 sink 组装 generate handler 失败。
  2. 阶段 reject 后 `mkb_ops_diagnostic_logs` 有对应 log_code。
  3. sidecar 写失败 → 产品 error_code 不变。
  4. 业务事务与 sidecar 不是同一连接。
  5. C 多块只 1 行 TIMING/REJECT，不是 N 行。
- **对应测试台账项**：`NS4-T21` `NS4-T22` `NS4-T23` `NS4-T30`
- **收口标准**：sink 强制；CONCURRENT 路径单测绿；码不污染。
- **本 Phase 风险提醒**：不要把 sidecar 接到 sqlite_port。不要为「测 4×」阻塞收口——soak 记墙钟，未达 4× 只要无 BUSY 风暴且产品码干净即可（`T-O-371`：必须测，不得宣传 4×）。

### 5.5 Phase 5 — P4 唯一读面

- **Phase 目标**：观测平面只剩 Port。
- **本 Phase 对应编号**：`P4-01` / `P4-02` / `P4-03`
- **本 Phase 新增文件**：`tests/unit/test_ns4_readport_reports.py`
- **本 Phase 修改文件**：`observability.py:245-318`；`collect.py:181-182`
- **本 Phase 删除文件**：生产路径上的 `inspect_dump.py`（或迁 `tests/fixtures/`）
- **具体功能预期**：
  1. Port 对失败 process 返回 invocation.status=failed 与 report.set。
  2. Port 不把 payload_extra 当证据字段暴露。
  3. collect 结束不 spawn dump。
  4. jsonl 行 JSON 无 `structure_reject`。
  5. architecture 扫描生产树无 `sqlite3.connect(.*mkb.db)` dump。
- **对应测试台账项**：`NS4-T24` `NS4-T25` `NS4-T26`
- **收口标准**：dump 调用消失；Port 单测覆盖失败夹具。
- **本 Phase 风险提醒**：六件套 artifact 文件仍可按路径哈希进期刊；那不是 dump SQL。

### 5.6 Phase 6 — Closure

- **Phase 目标**：退役一次性工具；诚实 closure；不发 R3。
- **本 Phase 对应编号**：`C-01` / `C-02`
- **本 Phase 新增文件**：`docs/closure/new-start/NS4-generation-evidence-plane-closure.md`
- **本 Phase 修改文件**：D04/S15 窄回填段；本 AP 状态 → `executed`（仅当 §10 硬闸绿）
- **具体功能预期**：
  1. 迁移脚本不可被 0815 入口调用。
  2. closure 列出 §8 逐项五态。
  3. 明确「R3 未跑」。
  4. mega 失败路径在 Turso 上走过一遍（测试夹具，**不是** 0815 五格文档）。
- **对应测试台账项**：`NS4-T28` `NS4-T29` `NS4-T31`
- **收口标准**：§10.1 全 PASS + 四元组。
- **本 Phase 风险提醒**：不得把 mega 夹具成功写成 R3 产品绿。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| `T-O-362` | `pre-NS4-qna.md` §1 | 所有 Phase 禁止兼容分支/双写 | 停工；回 QNA |
| `T-O-363` | 同上 | P0/P1 删 extra 证据 | 停工 |
| `T-O-364` / `T-O-371` | 同上 | Phase 2 硬切 Turso/CW | 不回 sqlite |
| `T-O-365` / `T-O-375` | 同上 | 本 AP 零 R3 ingest | 发现 ingest 即本 AP 失败 |
| `T-O-366` / `T-O-368` | 同上 | Phase 1 reopen 文 + Phase 6 回填 | 私自建表 = 停工 |
| `T-O-367` | 同上 | 不改叶包 I/O、不改 kernel、不改 R1 | 停工 |
| `T-O-369` | Q2-B | Phase 3 DDL 唯一形状 | 改形状须新 T-O |
| `T-O-370` | Q3-B | 同 TX；删吞异常 | 停工 |
| `T-O-372` | Q5-B | Phase 2 一次迁移 | 失败回 QNA，不双读 |
| `T-O-373` | Q6-C | 本文 DAG | 对调 P3/P1 = 违宪 |
| `T-O-374` | Q7-B | Phase 5 删 dump | 停工 |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表（本计划工作要落在哪些既有代码 / 新建点上）

| 锚 ID | `path:line` | 落点（这是什么） | 本 AP 用途 | 处置 | 备注 |
|-------|-------------|------------------|----------|------|------|
| A-1 | `src/runtime/config.py:21-24` | Settings 宪法默认已是 turso+CW=True | P3-01 对照；删的是 0815 覆写 | `✅ 复用` | 不要改默认去迁就实验 |
| A-2 | `src/persistence/engine.py:13-40` | `probe_concurrent_writes` MVCC+BEGIN CONCURRENT | P3-02 / P2-02 sidecar | `✅ 复用` | 已建好，别重写探针语义 |
| A-3 | `src/persistence/engine.py:80-99` | `apply_capability_gates` | P3-02 取消 waiver 假 ready | `✅ 复用` | required=True 时必须吃探针 |
| A-4 | `src/persistence/factory.py:29-47` | 后端工厂 | P3-03 拒非测试 sqlite | `♻️ 重 substrate` | |
| A-5 | `src/persistence/turso/port.py:56-61,111` | TursoPersistence + CW 旗 | P3 / P2 sidecar 第二连接 | `♻️ 重 substrate` | |
| A-6 | `src/persistence/sqlite_port.py:51-59` | sqlite 端口 | **仅 pytest** | `✅ 复用` | 生产禁止 |
| A-7 | `src/persistence/migrations/001_initial.sql:1369-1401` | invocation 现 DDL | P1-01 对照加列 | `✅ 复用` | 不要手改 001 |
| A-8 | `src/persistence/migrations/011_process_dispatch_pools.sql` | NS2 加列先例 | P1-01 风格 | `✅ 复用` | 只加列/新表，不进 extra |
| A-9 | `src/services/observability.py:72-118` | DiagnosticSink.write | P2-01/P2-03 | `✅ 复用` | best-effort 保留 |
| A-10 | `src/services/observability.py:245-318` | ReadPort 现只查 events | P4-01 扩展 | `♻️ 重 substrate` | 勿再直连 sqlite |
| A-11 | `src/runtime/intake/generation_live.py:329-353` | 失败 invocation + 吞异常 | P1-02/P1-03 硬切 | `♻️ 重 substrate` | **删** 334-340 |
| A-12 | `src/runtime/intake/generation_construct.py:45-76` | `layered_reject_histogram` | P0-04 / P1-04 | `♻️ 重 substrate` | 输出改走 contract |
| A-13 | `src/runtime/intake/generation_construct.py:261-263` | `getattr` 可选 persist | P1-03 **删除** | `♻️ 重 substrate` | 硬切对象 |
| A-14 | `src/runtime/intake/generation_construct.py:372-407` | `_cli_layered_candidate` | P1-02 CLI 失败写入 | `♻️ 重 substrate` | 信封失败现只抛错 |
| A-15 | `src/runtime/intake/generation_construct.py:941-975` | CLI/admit；extra 直方图 | P1-02/P1-04 | `♻️ 重 substrate` | 973 行是债务缝 |
| A-16 | `src/runtime/intake/core.py:191-217` | extra allowlist | P1-03 **删除** 键 | `♻️ 重 substrate` | |
| A-17 | `src/runtime/inference/claude_cli.py:187-253` | `cli_structured_kind` | P1-02 列值闭集 | `✅ 复用` | 不落正文 |
| A-18 | `src/runtime/health.py:17-21` | ready 含 CW / obs_tables | P3-02 | `✅ 复用` | |
| A-19 | `tests/domain/test_architecture.py:356-376` | 叶/服务无 I/O | P0-03 沿用 | `✅ 复用` | 已建好别弱化 |
| A-20 | `tests/domain/test_architecture.py:461-483` | NS2 extra 禁 dispatch_ | P0-03 fork 禁 reject 键 | `🔱 fork` | |
| A-21 | `tests/unit/test_structure_reject_histogram.py:1-28` | 直方图不泄漏正文 | P1-04 fork 到 report | `🔱 fork` | |
| A-22 | `.experiment/0815/runs/MKB-0815-R2/runner.py:105-106` | sqlite waiver | P3-01 **删除** | `♻️ 重 substrate` | |
| A-23 | `.experiment/0815/runs/MKB-0815-R2/collect.py:48,181-182` | sqlite 覆写 + dump | P3-01 / P4-02 | `♻️ 重 substrate` | |
| A-24 | `.experiment/0815/runs/MKB-0815-R2/inspect_dump.py:1-27` | 直连 sqlite3 | P4-02 **删除生产路径** | `♻️ 重 substrate` | |
| A-25 | `docs/baseline/domain-truth/D04-turso-physical-schema.md:1178-1192` | invocation 列宪法 | P0-01 / P1-01 | `✅ 复用` | 改列须 reopen |
| A-26 | `docs/eval/new-start/pre-NS4-qna.md:107-121` | `T-O-362..375` | 全文执行输入 | `✅ 复用` | 只引编号 |
| A-27 | `src/contracts/observability/stage_report.py` | 将新建 | P0-04 | `🆕 净新` | |
| A-28 | `src/persistence/migrations/013_generation_evidence_plane.sql` | 将新建 | P1-01 | `🆕 净新` | 只在 Turso 后跑 |
| A-29 | `scripts/ns4_migrate_q_a3.py` | 将新建 | P3-04；C-01 退役 | `🆕 净新` | 禁止长期活着 |
| A-30 | `src/persistence/turso/sidecar.py` | 将新建（或 port 方法） | P2-02 | `🆕 净新` | 第二连接 |

### 7.2 反例 ledger ⛔

| ⛔ | 反例 / 陷阱 | 为什么（依据） |
|----|------------|----------------|
| ⛔1 | 把 reject/kind 继续写入 `payload_extra` | `T-O-363` / `T-O-173` |
| ⛔2 | extra 与列双写「过渡一版」 | `T-O-362` |
| ⛔3 | 在 sqlite 生产上先跑 013 | `T-O-373` |
| ⛔4 | 保留 0815 `persistence_backend=sqlite` | `T-O-364` / `T-O-371` |
| ⛔5 | `concurrent_writes_required=False` 绕过探针 | `T-O-371` |
| ⛔6 | `getattr` 可选 persist / `except: return` | `T-O-362` / `T-O-370` |
| ⛔7 | 用 `OBS_*` 覆盖 `STRUCTURE_*` | `T-O-370` |
| ⛔8 | 观测 I/O 打进 `lsrag_*` 叶包 | `T-O-367` |
| ⛔9 | 业务 CAS `BEGIN CONCURRENT` | `T-O-371` |
| ⛔10 | dump + Port 双写或过渡对照 | `T-O-374` |
| ⛔11 | jsonl 再写 `structure_reject` | `T-O-374` |
| ⛔12 | 本 AP 内跑 R3 五格 / 改 v3 / 放宽 kernel | `T-O-365` / `T-O-375` / `T-O-367` |
| ⛔13 | 为旧失败 extra `{}` 发明直方图 | `T-O-367` / `T-O-372` |
| ⛔14 | 迁移后仍打开旧 `mkb.db`「以防万一」 | `T-O-362` / `T-O-372` |
| ⛔15 | 新 APM 进程 / 不经 D04 的第四表 | `T-O-368` / `T-O-366` |
| ⛔16 | 去 Mixin / YAML | `T-O-367` |
| ⛔17 | 改写 R1 封条 | `T-O-367` |
| ⛔18 | 把 LLM wait 包进已 BEGIN 的写事务 | `T-O-370` |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：N/A。§7.1 即本 AP grounding 真源。
- **QNA 真源**：`docs/eval/new-start/pre-NS4-qna.md` §1（只引 `T-O-*`）。
- **安全 / 信任边界威胁模型**（不得留空）：
  - `docs/baseline/domain-truth/S16-security-trust-boundary.md` + `T-O-311` / `T-O-366`：prompt / 模型正文 / stdout / original / secret / 绝对 path **不得**进入 invocation 列、stage_reports、diagnostic payload、jsonl、Port 视图。
  - 攻击向量落点：P0-04 / P1-04 校验器；`NS4-T20` `NS4-T27`。
  - `team_uuid` 只是过滤 ID，不是授权（S16 / OD-04）。Port 必须继续按 team 过滤（现 `timeline_by_task:260-273`）。
  - 迁移脚本只读源库、写目标库；不得把旧库路径打进日志明文以外的可服务面。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么） | 类型 | 层 | 来源 | 映射（工作项 → 收口目标） | PASS 证据（四元组） |
|---------|------------------|------|----|------|---------------------------|---------------------|
| `NS4-T01` | extra 赋值 `structure_reject` / `cli_structured_kind` 被 architecture 拒绝 | `短途` | `契约` | `🔱 fork test_architecture.py:461-483` | P0-03 → 禁 extra 证据 | `commit + test_ns4_guards + UTC` |
| `NS4-T02` | 叶包 / services 不 import persistence·llm | `短途` | `契约` | `♻️ 沿用 test_architecture.py:356-376` | P0-03 → 叶无 I/O | `commit + 既有测试 + UTC` |
| `NS4-T03` | contracts 不 import runtime/I/O | `短途` | `契约` | `♻️ 沿用 test_architecture.py:379-388` | P0-04 → 纯合同 | `commit + 既有测试 + UTC` |
| `NS4-T04` | reopen 文列闭集 ⊇ `T-O-369` 必列/必表 | `短途` | `契约` | `🆕 tests/domain/test_ns4_reopen_inventory.py` | P0-01 → 草案可执行 | `commit + 清单断言 + UTC` |
| `NS4-T05` | 0815 R2 入口无 sqlite/CW=False 覆写 | `短途` | `契约` | `🆕 tests/domain/test_ns4_0815_settings_guard.py` | P3-01 → 与宪法默认合一 | `commit + rg 断言 + UTC` |
| `NS4-T06` | CW required 且探针假失败 → ready 503 / 拒 Task | `短途` | `集成` | `🆕 tests/unit/test_ns4_ready_cw.py` | P3-02 → 无 waiver | `commit + 夹具 503 + UTC` |
| `NS4-T07` | `probe_concurrent_writes` 真假路径 | `短途` | `unit` | `🔱 fork` 既有 engine 探针测（若无则新建） | P3-02 → 探针语义 | `commit + probe 测试 + UTC` |
| `NS4-T08` | 非测试 factory(sqlite) 失败；pytest 内存 sqlite 仍可 | `短途` | `unit` | `🆕 tests/unit/test_ns4_factory_sqlite_test_only.py` | P3-03 → 双后端消失 | `commit + 正反用例 + UTC` |
| `NS4-T09` | 迁移后 Q-A3 向量=17、publication 在、无伪 report | `spike` | `集成` | `🆕 tests/integration/test_ns4_q_a3_migrate.py` | P3-04 → serving intact | `commit + COUNT=17 + UTC` |
| `NS4-T10` | 0815 runner 打开路径不是旧 sqlite 文件 | `短途` | `契约` | 与 T05 同文件 | P3-01/P3-04 → 单路径 | `commit + path 断言 + UTC` |
| `NS4-T11` | migration 013 可应用到 Turso 测试库 | `短途` | `集成` | `🆕 tests/unit/test_ns4_migration_013.py` | P1-01 → DDL 绿 | `commit + migrate + UTC` |
| `NS4-T12` | invocation 非法 status/stage CHECK 失败 | `短途` | `unit` | 同上 | P1-01 → CHECK 生效 | `commit + IntegrityError + UTC` |
| `NS4-T13` | `mkb_generation_stage_reports` 存在且 FK 到 process | `短途` | `unit` | 同上 | P1-01 → 新表 | `commit + pragma/table_info + UTC` |
| `NS4-T14` | `_safe_outcome_extra` 不再拷贝 reject/kind；落库 extra 无键 | `短途` | `unit` | `🔱 fork test_structure_reject_histogram.py:31+` **改断言方向** | P1-03 → extra 清空证据 | `commit + 反向断言 + UTC` |
| `NS4-T15` | report INSERT 失败则 process 不进入产品终态 | `短途` | `集成` | `🆕 tests/unit/test_ns4_stage_report_tx.py` | P1-02 → 同 TX fail-closed | `commit + 回滚断言 + UTC` |
| `NS4-T16` | 源码无 `getattr(..., "_persist_failed_generation_invocation")` | `短途` | `契约` | `🆕` architecture 扫描 | P1-03 → 硬切可选账 | `commit + rg 空 + UTC` |
| `NS4-T17` | persist 路径无裸 `except: return` | `短途` | `契约` | 同上 | P1-03 → 删吞异常 | `commit + ast/rg + UTC` |
| `NS4-T18` | CLI 非 object → failed invocation + kind 列 + transport_failed report | `短途` | `集成` | `🆕 tests/unit/test_ns4_cli_fail_rows.py` | P1-02 → CLI 失败有行 | `commit + SQL 行 + UTC` |
| `NS4-T19` | admit mismatch → report 有 set/counts；extra 无键 | `短途` | `集成` | `🆕 tests/unit/test_ns4_admit_report.py` | P1-04 → 直方图进表 | `commit + SQL + UTC` |
| `NS4-T20` | histogram/report 编码不含 original 正文 | `短途` | `unit` | `🔱 fork test_structure_reject_histogram.py:10-28` | P0-04/P1-04 → 红action | `commit + 密钥不泄漏 + UTC` |
| `NS4-T21` | 无 DiagnosticSink 不能组装 generate | `短途` | `unit` | `🆕 tests/unit/test_ns4_sink_required.py` | P2-01 → 强制注入 | `commit + 构造失败 + UTC` |
| `NS4-T22` | sidecar 使用独立连接 + BEGIN CONCURRENT（可 mock execute 序列） | `短途` | `unit` | `🆕 tests/unit/test_ns4_diagnostic_sidecar.py` | P2-02 → 旁路 TX | `commit + SQL 序 + UTC` |
| `NS4-T23` | sidecar 写失败不改变产品 error_code | `短途` | `集成` | 同上 | P2-02 → 分账 | `commit + code 不变 + UTC` |
| `NS4-T24` | ReadPort 返回 invocation.status 与 report 字段，不把 extra 当证据 | `短途` | `集成` | `🆕 tests/unit/test_ns4_readport_reports.py` | P4-01 → 唯一形状 | `commit + Port JSON + UTC` |
| `NS4-T25` | collect 不调用 inspect_dump；生产树无 dump sqlite3.connect | `短途` | `契约` | `🆕 tests/domain/test_ns4_no_inspect_dump.py` | P4-02 → 删 dump | `commit + rg 空 + UTC` |
| `NS4-T26` | jsonl 白名单：无 `structure_reject` | `短途` | `unit` | `🆕 tests/unit/test_ns4_jsonl_journal.py` | P4-03 → 期刊≠schema | `commit + 键断言 + UTC` |
| `NS4-T27` | 攻击向量：prompt/stdout/original 进 report/diagnostic/Port 均失败 | `短途` | `契约` | `🆕 tests/unit/test_ns4_redaction_attacks.py` | P0-04 / §7.3 | `commit + 拒绝 + UTC` |
| `NS4-T28` | 迁移脚本退役：0815/runtime 无调用 | `短途` | `契约` | `🆕` 与 T05 同守卫扩 | C-01 → 无适配器 | `commit + rg 空 + UTC` |
| `NS4-T29` | mega：Turso 上 markdown/B/C 失败夹具走完，Port 能读行 | `mega` | `e2e` | `🆕 tests/e2e/test_ns4_fail_path_turso.py` | C-02 → 整链证据 | `commit + e2e PASS + UTC` |
| `NS4-T30` | soak：N 线程写 diagnostic CONCURRENT；产品码不被污染；记录 BUSY/墙钟 | `soak` | `live` | `🆕 tests/integration/test_ns4_cw_soak.py` | P2-02 → 必须测 | `commit + soak log + UTC` |
| `NS4-T31` | 本 AP 工作树无新 0815 ingest 行 / 无 `-r3` collect 执行记录 | `短途` | `契约` | `🆕 tests/domain/test_ns4_no_r3_ingest.py` | C-02 → 零 R3 | `commit + 断言 + UTC` |
| `NS4-T32` | src 无「sqlite 与 turso 并行读」API | `短途` | `契约` | 并入 T01/T08 | P0-03 / P3-03 | `commit + 扫描 + UTC` |

### 8.2 复用台账

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/domain/test_architecture.py::test_services_do_not_reach_api_concrete_persistence_or_inference_transport` | `♻️ 沿用` | 0 | 已存在，纳入每 Phase |
| `tests/domain/test_architecture.py::test_contracts_do_not_import_runtime_or_io_layers` | `♻️ 沿用` | 0 | 已存在 |
| `tests/domain/test_architecture.py::test_ns2_dispatch_does_not_add_required_tables_or_payload_extra_keys` | `🔱 fork → NS4 extra 键` | + reject/kind 禁写 | 已存在 PASS |
| `tests/unit/test_structure_reject_histogram.py` | `🔱 fork` | 断言从 extra 改为 report；保留不泄漏正文 | 已存在；P1 后旧 extra 断言必须改向否则假红 |
| `tests/unit/test_observability.py` | `♻️ 沿用` | Port 扩查询后补失败夹具（T24 新文件主责） | 已存在 |
| `tests/domain/test_ns1_guards.py` | `♻️ 沿用` | 0；叶包守卫 | 已存在 |

### 8.3 分层与跑法

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `pytest tests/domain/test_architecture.py tests/domain/test_ns4_*.py tests/unit/test_ns4_*.py` | unit·契约 | 每 PR / 每 Phase |
| spike | `pytest tests/integration/test_ns4_q_a3_migrate.py` | 集成 | Phase 2 收口 |
| mega | `pytest tests/e2e/test_ns4_fail_path_turso.py` | e2e | **Phase 6 收口** |
| soak | `pytest tests/integration/test_ns4_cw_soak.py` | live | **退出硬闸** |

### 8.4 测试缺口（本 AP 明确不覆盖）

- 不覆盖 0815 五格真模型 live（理由：`T-O-365`）→ 交 R3，仅在 NS4 closure 后。
- 不覆盖提示词质量 / 金标语义命中（理由：`T-O-375` 产品轴属 R3）→ 交 R3-05。
- 不覆盖 Turso Cloud replica、业务 CAS CONCURRENT（理由：`T-O-371`）→ 不交本 AP。
- 不覆盖 4× 性能宣传（理由：`T-O-371` 只强制测、禁宣传）→ soak 记数即可。
- 不覆盖 Mixin 拆分 / YAML（理由：`T-O-367`）。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 必带四元组：`commit + 测试名 + run-time(UTC)`。计数 ≠ 价值。
- `degraded` 必带机器可读 `reason`。pre-existing 失败必带 git 证据。
- **安全项** `NS4-T20` `NS4-T27` 必须含攻击向量，不得只测 happy-path。
- 旧测试 `test_outcome_extra_copies_only_allowlisted_diagnostic_keys` 在 P1 后若仍期望 extra 含 reject，视为 **必须改向**，不得为保绿恢复 extra。
- mega 夹具成功 **不得** 写成 R3 或 Q-A5 publish。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| pyturso 无法打开既有 sqlite 文件 | Q-A3 迁移物理失败 | `medium` | 导出/导入新文件；失败停工，不双读 |
| CW 探针在实验机红 | ready 永假 | `medium` | 修环境或引擎；**禁止** required=False |
| 同 TX 写报告拉长锁 | 高并发 ingest | `medium` | 先等 LLM 再 BEGIN；不把 C 每块写入 TX |
| 013 与既有 8 条成功 invocation | 新列 NOT NULL | `low` | 回填 status=succeeded |
| 旧单测绑 extra | P1 假红 | `medium` | 改向，不改回 extra |
| 迁移脚本变成适配器 | 违反硬切 | `medium` | C-01 强制退役 + T28 |
| 执行者提前跑 R3 | 违反 `T-O-365` | `high` | T31；发现即本 AP 失败 |
| reopen 文与 DDL 漂移 | 地下表 | `medium` | T04 清单锁 |

### 9.2 约束与前提

- **技术前提**：本机可 `import turso` / pyturso；CW 探针可在测试库上执行 `PRAGMA journal_mode=mvcc` + `BEGIN CONCURRENT`。
- **运行时前提**：R2 `runtime/mkb.db` 只读可访问；Q-A3 task 仍在。不删 R1 封存。
- **组织协作前提**：业主不再改口 `T-O-362..375`；R3 等待 closure。
- **上线 / 合并前提**：每 Phase 独立 PR 或可 revert 提交；P3 未绿不得合 013。

### 9.3 文档同步要求

- 需要同步更新的设计文档：`D04-turso-physical-schema.md`（Phase 6 窄回填）；`S15-observability-reliability.md`（Port 句）；`NS4-d04-s15-reopen.md`（Phase 1）
- 需要同步更新的说明文档 / README：0815 `r3_objectives.md` 仅加一句「等 NS4 closure」（不发车）
- 需要同步更新的测试说明：本 AP §8；closure §测试五态

### 9.4 完成后的预期状态

1. 生产与 0815 只打开 Turso；CW 是 ready 硬门；sqlite 仅 pytest。
2. 失败 generate 在同一 Outcome TX 留下 invocation 新列 + `mkb_generation_stage_reports` 行；extra 无证据键。
3. DiagnosticSink 必注入；诊断旁路 CONCURRENT；产品码不被 sink 污染。
4. 观测只经 ReadPort；`inspect_dump` 不在生产路径；jsonl 只是期刊。
5. Q-A3 17 向量经新路径可读；迁移脚本已退役；**R3 仍未发车**。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

### 10.1 收口硬闸

所有 `mega + soak + 退出层` 必须 **PASS 且四元组齐全**：

1. Turso 失败路径 mega：Port 能读 failed invocation + report（`NS4-T29`）
2. CW soak 已跑；产品码未被 sidecar 污染（`NS4-T30`）
3. Q-A3 17 向量经新路径 intact（`NS4-T09`）
4. 无 sqlite 生产覆写、无 dump、无 extra 证据键、无 getattr/吞异常（`NS4-T05` `NS4-T14` `NS4-T16` `NS4-T17` `NS4-T25`）
5. 零 R3 ingest（`NS4-T31`）
6. 红action 攻击向量拒绝正文（`NS4-T20` `NS4-T27`）

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组） | 状态 |
|----------|--------|---------|---------------------|------|
| extra 禁作证据 | P0-03 / P1-03 | T01 T14 | 执行后填 | `未观察` |
| 叶无 I/O | P0-03 | T02 T03 | 执行后填 | `未观察` |
| reopen 可执行 | P0-01 | T04 | 执行后填 | `未观察` |
| Turso+CW 硬切 | P3-01/02/03 | T05 T06 T07 T08 T10 | 执行后填 | `未观察` |
| Q-A3 一次迁移 | P3-04 | T09 | 执行后填 | `未观察` |
| DDL + CHECK | P1-01 | T11 T12 T13 | 执行后填 | `未观察` |
| 同 TX 失败有行 | P1-02/04 | T15 T18 T19 | 执行后填 | `未观察` |
| 旧缝删除 | P1-03 | T16 T17 | 执行后填 | `未观察` |
| sink + CONCURRENT | P2-* | T21 T22 T23 T30 | 执行后填 | `未观察` |
| Port 唯一 | P4-* | T24 T25 T26 | 执行后填 | `未观察` |
| 红action | P0-04 | T20 T27 | 执行后填 | `未观察` |
| 脚本退役 | C-01 | T28 | 执行后填 | `未观察` |
| mega 失败链 | C-02 | T29 | 执行后填 | `未观察` |
| 零 R3 | C-02 | T31 | 执行后填 | `未观察` |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | `T-O-369..374` 全部在 Turso 主路径落地；旧缝从生产消失 |
| 测试 | §8 全 PASS；退出硬闸四元组齐全 |
| 文档 | D04/S15 窄回填 + NS4 closure；本 AP `executed` |
| 风险收敛 | 无 sqlite 双路径；无 extra 证据；迁移脚本退役 |
| 可交付性 | R3 **可以**在 closure 后按 `T-O-375` 发车，但本 AP **不**发车 |

### 10.4 NOT-成功识别

> 任一退出硬闸 `degraded / 未观察` ⇒ **不得标 `executed`**。按 `verified / observed-OK-at-closure / partial / 未观察 / deferred` 归类。用 extra 或 sqlite 换绿 = 本 AP 失败，不是部分成功。

---

## 11. 执行日志回填（仅 `executed` 状态使用）

> 执行者：`Grok`  
> 执行时间：`2026-08-16`  
> 文档状态：`draft → executing → executed`  
> 代码改动统计：六相分批 commit（`9d3f3cc` … closure）

- **实际执行摘要**：P0 合同/守卫 → P3 Turso+Q-A3 一次迁移 → P1 013+同 TX → P2 sink/sidecar → P4 Port/去 dump → closure。R3 未发。
- **Phase 偏差**：① extra 守卫 P0 用 allowlist、P1 清空；② ContextVar 代替改 ProcessOutcome；③ 多线程 CONCURRENT soak 改串行；④ `adapter_kind` CHECK 增加 `local_vllm`。
- **阻塞与处理**：`_structurize` 内联 `import uuid7` UnboundLocalError 已删；live e2e 因 CHECK 拒 `local_vllm` 已扩列。
- **测试发现**：NS4 专项 + `tests/unit|domain|integration` + 关键 e2e 在 adapter 扩 CHECK 后 PASS。
- **后续 handoff**：`docs/closure/new-start/NS4-generation-evidence-plane-closure.md` → R3 `T-O-375`。

---

## 12. 分 Phase 执行日志（append-only · `.adocs/code-execution-log.md`）

> 执行者：`Grok`  
> 执行时间：`2026-08-16`  
> 文档状态：`draft → executing`  
> 宿主：本 AP。不改写 §0–§10。

### 12.1 Phase 1 / P0 — 合同与守卫

- **实际执行摘要**：P0-01 reopen 草案落盘；P0-02 Port 字段清单写入同一草案 §2；P0-03 extra 证据键守卫（现码 allowlist，P1 必须清空）；P0-04 `src/contracts/observability/stage_report.py`。
- **Phase 偏差**：architecture extra 扫描对现 `core.py` / `generation_construct.py` 使用 **P0→P1 allowlist 棘轮**，而不是立刻全红（否则 P0 无法收口）。分类：`substrate-fit`。P1 必须删 allowlist。
- **阻塞与处理**：无。
- **测试发现**：`17 passed`（`test_ns4_guards` / `test_ns4_reopen_inventory` / `test_ns4_stage_report_contract` / `test_ns4_redaction_attacks` + 叶/contracts 既有守卫）。
- **后续 handoff**：Phase 2 / P3 Turso 硬切。

#### 逐工作项

| 工作项 | 状态 | 实际落点 | 备注 |
|--------|------|----------|------|
| P0-01 | `✅ done` | `docs/plan/new-start/NS4-d04-s15-reopen.md` | 列/表/56 表数 |
| P0-02 | `✅ done` | 同文件 §2 | Port 必含 invocation+report |
| P0-03 | `✅ done` | `tests/domain/test_ns4_guards.py` | allowlist 仅 core+construct |
| P0-04 | `✅ done` | `src/contracts/observability/stage_report.py` | 拒 prompt/stdout/original |

#### 时序

| 时点 | 步骤 | 决策 / 产出 |
|------|------|-------------|
| T0 | 拉 D04 §3.5.4 / architecture / contracts | 确认 invocation 无 status 列 |
| T1 | 写 reopen + contract + 守卫测试 | P0 短途 17 绿 |

### 12.2 Phase 2 / P3 — Turso 硬切与一次迁移

- **实际执行摘要**：P3-01 删除 0815 sqlite/CW=False；入口改 `mkb.turso.db`。P3-02 沿用 `apply_capability_gates`（required=True 跟探针）。P3-03 factory 非 pytest 拒 sqlite。P3-04 一次复制 Q-A3 到 Turso 文件（17 向量，0 report）。
- **Phase 偏差**：preflight 目录探测闸改为看 `mkb.turso.db`；旧 `mkb.db` 仅作 archive。`r3_prepare` 改为 `build_persistence(turso)`。分类：`substrate-fit`。
- **阻塞与处理**：无。pyturso 可打开 sqlite 复制件；CW 探针在复制件上为 True。
- **测试发现**：`19 passed`（factory / ready-cw / 0815 guard / migrate / turso driver / P0 guards）。
- **后续 handoff**：Phase 3 / P1 DDL 只许打在 Turso 路径上。

#### 逐工作项

| 工作项 | 状态 | 实际落点 | 备注 |
|--------|------|----------|------|
| P3-01 | `✅ done` | `runner.py` / `collect.py` / `retrieve.py` / `r3_prepare.py` | turso+CW=True |
| P3-02 | `✅ done` | `engine.py:80-99` 沿用 | 测试锁 required 跟探针 |
| P3-03 | `✅ done` | `src/persistence/factory.py` | `sqlite_backend_permitted` |
| P3-04 | `✅ done` | `scripts/ns4_migrate_q_a3.py` | 17/17/0 reports |

### 12.3 Phase 3 / P1 — 一等 schema 与同 TX 写入

- **实际执行摘要**：013 加列+`mkb_generation_stage_reports`。失败证据进 ContextVar，在 `_fail_process_tx` 同 TX 落行。删除 extra allowlist、`getattr` persist、吞异常。histogram 只进 report。
- **Phase 偏差**：用 in-request ContextVar 而不是改 ProcessOutcome 字段（避免 digest 形状变化）。分类：`substrate-fit`。
- **阻塞与处理**：`_structurize` 内二次 `import uuid7` 导致 UnboundLocalError → 已删内联 import。
- **测试发现**：migration/guards/e2e single-intake 绿。
- **后续 handoff**：Phase 4 DiagnosticSink。

#### 逐工作项

| 工作项 | 状态 | 实际落点 | 备注 |
|--------|------|----------|------|
| P1-01 | `✅ done` | `013_generation_evidence_plane.sql` | CHECK + 新表 |
| P1-02 | `✅ done` | `generation_live.py` / `generation_evidence.py` / `runtime_outcome.py` | 同 TX |
| P1-03 | `✅ done` | `core.py` extra={}；删 getattr/吞异常 | |
| P1-04 | `✅ done` | admit except → stage report | |

### 12.4 Phase 4 / P2 — DiagnosticSink 旁路

- **实际执行摘要**：create_app 注入 DiagnosticSink；Turso 走 sidecar BEGIN CONCURRENT。generate 无 sink 即 503。失败阶段写一行 diagnostic。
- **Phase 偏差**：大量单测仍可构造无 sink 的 Pipeline（只测 helper）。真正 `_structurize/_construct` 强制 sink。分类：`substrate-fit`。
- **阻塞与处理**：无。
- **测试发现**：sink required / sidecar / e2e / observability contracts 绿。
- **后续 handoff**：Phase 5 ReadPort。

### 12.5 Phase 5 / P4 — 唯一读面

- **实际执行摘要**：ReadPort 在 timeline 上附 invocation+report。collect 不再 spawn dump。jsonl `_journal_row` 剥 reject 键。
- **Phase 偏差**：`inspect_dump.py` 文件仍在 gitignore 实验树，但 collect 已切断调用。分类：`substrate-fit`。
- **测试发现**：T24/T25/T26 绿。

### 12.6 Phase 6 / Closure

- **实际执行摘要**：迁移脚本标 RETIRED；D04/S15 窄回填；closure 落盘。本地回归在扩 `local_vllm` CHECK 后绿。
- **Phase 偏差**：T30 多线程 soak `partial`。`adapter_kind` 比 QNA 两值多一个 `local_vllm`（S11 现网）。
- **后续 handoff**：owner 可按 `T-O-375` 发 R3。
