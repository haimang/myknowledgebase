# NS4 · D04 + S15 窄 reopen 草案

> **地位**：Phase 1（P0）产出。供 `013_generation_evidence_plane.sql` 逐字执行。  
> **冻结输入**：`pre-NS4-qna.md` `T-O-366` / `T-O-368` / `T-O-369` / `T-O-374`  
> **文档状态**：`draft / awaiting Phase 6 formal backfill`  
> **日期**：`2026-08-16`

本文件 **不是** 执行 SSOT。执行 SSOT 仍是 D04/S15 formal。本草案只列出本节点允许改的物理闭集，禁止扩成 S15 全文重开。

---

## 1. D04 窄 reopen 清单

### 1.1 `mkb_generation_invocations` 列晋升（对照 D04 §3.5.4）

现列保持。**新增**（硬切，CHECK 一次到位）：

| 列 | 约束 |
|---|---|
| `status` | NOT NULL CHECK ∈ `succeeded,failed` |
| `stage_key` | NOT NULL CHECK ∈ `markdown,structurize,construct` |
| `error_code` | NULL；`failed` 时应用层要求 NOT NULL |
| `adapter_kind` | NOT NULL CHECK ∈ `claude_cli,local_inference` |
| `cli_structured_kind` | NULL；CLI 信封失败时应用层要求 NOT NULL CHECK ∈ `object,list,string,empty_result,missing,null,number,bool,other` |

既有成功行回填：`status=succeeded`；`stage_key` 从既有 `payload_extra.stage_key` 推断，缺省 `structurize`；`adapter_kind` 缺省 `claude_cli`。不发明失败直方图。

`payload_extra` 列保留为空袋。**禁止**再写入 `structure_reject` / `cli_structured_kind` / `status`。

### 1.2 新 required 表 `mkb_generation_stage_reports`

D04 §2.2.5 generation 模块表数 4 → **5**。全域 required 表数 55 → **56**。

| 列 | 约束 |
|---|---|
| `report_uuid` | TEXT PK |
| `team_uuid` | TEXT NOT NULL |
| `trace_uuid` | TEXT NOT NULL |
| `task_uuid` | TEXT NOT NULL |
| `execution_uuid` | TEXT NOT NULL |
| `process_uuid` | TEXT NOT NULL |
| `stage_key` | TEXT NOT NULL CHECK ∈ `markdown,structurize,construct` |
| `disposition` | TEXT NOT NULL CHECK ∈ `accepted,rejected,transport_failed` |
| `error_code` | TEXT NULL |
| `cli_structured_kind` | TEXT NULL |
| `has_g0` | INTEGER NULL CHECK ∈ `0,1` |
| `block_count` | INTEGER NULL CHECK `>=0` |
| `granularity_set` | TEXT NULL |
| `layer_counts` | TEXT NULL（仅计数字典，schema `mkb.layer-counts.v1`） |
| `latency_ms` | INTEGER NOT NULL CHECK `>=0` |
| `schema_digest` | TEXT NOT NULL |
| `occurred_at` | TEXT NOT NULL |
| `payload_extra` | TEXT NOT NULL DEFAULT `'{}'` |

FK：`(team_uuid, process_uuid)` → `mkb_processes`。  
索引：`(process_uuid, occurred_at)`；`(execution_uuid, stage_key)`。

### 1.3 明确不改

- 不新开第四套可观测表名家族（仍是 events / diagnostic_logs / security_audit + 本证据表）。
- 不改 `mkb_processes.payload_extra` 列类型。
- 不把 metrics 时序打进业务库。

---

## 2. S15 窄 reopen 清单（ReadPort）

`ObservabilityReadPort.timeline_by_task` / 等价方法 **必须**能返回：

| 字段 | 来源表 |
|---|---|
| 既有 event 时间线 | `mkb_domain_events` |
| `invocation.status` / `stage_key` / `error_code` / `adapter_kind` / `cli_structured_kind` | `mkb_generation_invocations` |
| `disposition` / `has_g0` / `block_count` / `granularity_set` / `layer_counts` / `latency_ms` | `mkb_generation_stage_reports` |

**禁止**把 `payload_extra.structure_reject` 当合法证据面。  
retention / alert 阈值 / ready 组件闭集本节点不改，除非 CW 已是 ready 组件（沿用）。

---

## 3. 执行对照

| 草案句 | 落地 |
|---|---|
| §1.1 列 | `013_generation_evidence_plane.sql`（Phase 3，Turso 之后） |
| §1.2 表 | 同上 |
| §2 Port | `src/services/observability.py`（Phase 5） |
| 禁 extra 键 | architecture 守卫 + `core.py` 删除 allowlist |
