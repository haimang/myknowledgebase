# Nano-Agent 行动计划

> 服务业务簇: `new-harvest / public-object-lifecycle`
> 计划对象: `authenticated public upload + stat/status + catalog/upload_pending 同 UoW + GC`
> 类型: `new`（public surface）+ `upgrade`（S13/GC）
> 作者: `Grok workflow new-harvest-nh1-nh5-action-plans`
> 时间: `2026-08-29`
> 文件位置: `docs/plan/new-harvest/AP-NH4-public-upload-and-object-lifecycle.md`
> 上游前序 / closure:
> - `AP-NH1` `stop-or-go.md=GO`（`NH1-T01..T07` 全 PASS）后进入并行窗（fail → STOP/reopen，禁止静默换方案、禁止部分绿）。`NH1-T03` 仅作 T04 namespaced search 夹具依赖，不替代 GO
> 下游交接:
> - `AP-NH7` local_object 格依赖本 AP 的 public handle 入口（join 在 NH7 local lane 前）
> - `AP-NH9` 消费本 AP 的 upload replay / GC TOCTOU / security 证据，不在 NH9 第一次发现功能缺口
> 关联设计 / 调研文档:
> - `docs/eval/new-harvest/final-execution-plan.md` v1.0 `frozen` §7.4
> - `docs/eval/new-harvest/pre-charter-qna.md` v1.0 Q16/Q24 → `T-O-396`/`T-O-404`
> - `docs/eval/new-harvest/pre-initial-planning-qna.md` v0.5 Q5 → `T-O-385`；`T-O-377`/`T-O-383`/`T-O-381`
> 冻结决策来源:
> - `docs/eval/new-harvest/pre-charter-qna.md` Q16/`T-O-396`、Q24/`T-O-404`、Q26/`T-O-406`（只读引用；本 action-plan 不填写 Q/A）
> - `docs/eval/new-harvest/pre-initial-planning-qna.md` Q5/`T-O-385`、`T-O-377`、`T-O-383`
> grounding 来源:
> - `eval-reference-anchor` RA06 全文；RA09 仅消费 upload/GC 竞态（`W-GC-INGEST` / `NH-RA09-B05` / `RA-09-HEAD-12`）
> - HEAD `1221aa1` 实测（§7.1 行号以本文件独立 `read_file` 为准）
> 关联 reference-anchor:
> - [`docs/eval/new-harvest/reference-anchor/assessment-analysis-06-public-upload-and-object-lifecycle.md`](../../eval/new-harvest/reference-anchor/assessment-analysis-06-public-upload-and-object-lifecycle.md)
> - [`docs/eval/new-harvest/reference-anchor/assessment-analysis-09-assurance-replay-concurrency-and-compatibility.md`](../../eval/new-harvest/reference-anchor/assessment-analysis-09-assurance-replay-concurrency-and-compatibility.md)（只消费 upload/GC 竞态，不改写）
> 文档状态: `draft`
> 台账 ID 区间（final §11.A）: `NH4-01..08 / NH4-A01..06 / NH4-T01..07`
> migration: `M-NH-05` pending hold（本 AP 规定 forward-only DDL，不在本文伪造已 migrate 的 SHA）

---

## 0. 执行背景与目标

new-harvest 四通道 completeness（`T-O-376`/`T-O-381`）要求**公共对象上传到位**：调用方能把真实 PDF/doc 字节送进 Team-scoped CAS，再另一次 `intake.ingest` + `local_object` 进入既有 publication/retrieval 链。HEAD `1221aa1` 已有 S13 内核（CAS path、verify-on-read、live unique、GC quarantine fence），但 public `/v1` **0** 条 upload/stat 路由（`T-R-NH-25`；`D-14=28/0`），purpose 闭集 **8/0** 无 caller-upload（`D-15`）。把内部 `LocalObjectStore.promote(bytes)` 挂到 HTTP **不能**当 DoD：promote 不写 catalog/ref（`local_store.py:71-105`），catalog-without-ref 已是 GC orphan 候选（`object_gc.py:133-161`），且 ASGI 默认 1MiB 体帽 + 全内存 `bytes` 无法承载 256MiB 对象帽。

本 AP 只消费已冻结结论，把 Q16/Q24/Q5 落成可交付物：受鉴权 upload + stat/status；返回 usable handle **之前**同 UoW 提交 catalog + `upload_pending` live ref/hold；upload **不**造 Source/Item/Revision；无 raw GET/list/presign；pending/grace/quarantine 与 ingest 交错可证。`G-NH-07`/`G-NH-16` 已 CLOSED，本文件不重开 owner-gate。

- **服务业务簇**：`new-harvest / public-object-lifecycle`
- **计划对象**：authenticated public upload + stat/status + catalog/`upload_pending` 同 UoW + GC
- **本次计划解决的问题**：
  - public `/v1` 无 object upload/stat，调用方无法合法喂入 `local_object`（`NH-RA06-B01` / `T-R-NH-25`）
  - upload 成功缺 catalog+live ref，GC 要么看不见（磁盘泄漏）要么把合法待 ingest 当 orphan 误删（`NH-RA06-B03/B04` / `R-F07`）
  - `ObjectStorePort.promote(data: bytes)` + `max_request_bytes=1MiB` 无法有界流式写入真实对象（`NH-RA06-B05/B09`）
- **本次计划的直接产出**：
  - 受鉴权 `POST .../objects:upload` + `GET .../objects:stat`（建议落点，见 §4.3；HEAD 尚无）
  - `M-NH-05`：purpose 闭集登记 `upload_pending`；返回 handle 前 catalog+pending 同 UoW
  - Port 有界流式写 + pending TTL/cancel + GC 扩 pending/grace + 安全负例闭集
- **本计划不重新讨论的设计结论**：
  - 上传只创造 S13 handle+digest+size，不创造 IntakeSource/Item/Revision；随后独立 `intake.ingest` + `local_object`（来源：Q5 / `T-O-385`）
  - public v1 = authenticated upload + stat/status（无 path/filename，跨 team 403），无 raw byte GET；业务 artifact read 独立；未来导出另 reopen（来源：Q16 / `T-O-396`）
  - 返回 usable handle 前必须同 UoW 提交 catalog + `upload_pending` live ref/hold；无任一不算成功；ingest acceptance 转业务 ref；取消/TTL 后才 grace/GC；未完成流只 staging scanner 清（来源：Q24 / `T-O-404`）

---

## 1. 执行综述

### 1.1 总体执行方式

先底层后上层、先内核契约后 public 缝：Phase 1 把 Port 从全内存 `bytes` 扩成有界 chunk 流并保住 atomic promote；Phase 2 用既有 S12 UoW 模式把 catalog+`upload_pending` 钉成「usable handle」的充分必要；Phase 3 才在现有 `/v1` + `BusinessToken` 旁并列两条 upload/stat 路由（并扫零 raw）；Phase 4 把幂等/冲突与独立 ingest handoff 接到既有 unique 与 `read_verified`；Phase 5 扩 GC pending/grace/quarantine 并关闭攻击向量。禁止把内部 `promote()` 或 Task inline staging 当 public DoD（`FG-NH-10`）。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | Bounded write | `L` | chunk 流 + 增量 sha/size + cap/expected 校验 + atomic promote/staging cleanup | `stop-or-go.md=GO`；不依赖 NH2/NH3/NH5 |
| Phase 2 | Catalog+pending UoW | `L` | promote 成功后同 UoW catalog+`upload_pending` 才返回 handle；`M-NH-05` | Phase 1 |
| Phase 3 | Public API fence | `M` | auth upload+stat；字段闭集；零 raw/list/presign | Phase 2 |
| Phase 4 | 幂等与 ingest 交接 | `M` | team+digest+size replay；upload UoW ≠ Task UoW；acceptance 转业务 ref | Phase 3；T04 的 L4 消费 NH1-T03 namespace fixture |
| Phase 5 | GC + 安全负例 | `L` | pending 不可删；TTL/cancel→grace→tombstone；quarantine restore；攻击向量 typed fail | Phase 2（GC 内核）与 Phase 3（HTTP 负例） |

> 说明：上表 `规模` 是每个 Phase 的**描述性提示**，**不是开工前的体量判定闸**。

### 1.3 Phase 说明

1. **Phase 1 — Bounded write**
   - **核心目标**：`ObjectStorePort` 可流式写入；对象层 cap=`object_max_bytes`；expected SHA-256 失败 422；超 cap 413；半写只留 staging。
   - **为什么先做**：没有有界流，公共 HTTP 会在 1MiB ASGI 帽或全内存 `promote` 处假绿/OOM（`NH-RA06-B05`）。
2. **Phase 2 — Catalog+pending UoW**
   - **核心目标**：usable handle ⇔ catalog 行 ∧ live `upload_pending` ref 已 commit；缺一即失败且不返回 handle。
   - **为什么放在这里**：`T-O-404` 是产品成功定义；先有内核再挂路由，避免「HTTP 200 + 无 ref」。
3. **Phase 3 — Public API fence**
   - **核心目标**：`/v1` 并列 upload+stat；`BusinessToken`；stat 无 path/name；不注册 raw GET。
   - **为什么放在这里**：内核可证后才暴露表面，且必须用架构扫描锁住 `O-NH-04`。
4. **Phase 4 — 幂等与 ingest 交接**
   - **核心目标**：同 team+sha256+size 并发双传同一 handle；跨 team 403；upload 后检索空；独立 ingest 后 namespace 命中。
   - **为什么放在这里**：表面存在后才能用真实 HTTP 证明 `T-O-385` 两步法，而不是 `container.storage.promote`。
5. **Phase 5 — GC + 安全负例**
   - **核心目标**：pending 存活；release+grace 可删；quarantine 窗口新 ref restore；filename/MIME/oversize/digest/auth/presign 全 typed fail。
   - **为什么放在这里**：GC 扩 pending 依赖 Phase 2 的 purpose；HTTP 负例依赖 Phase 3 路由。

### 1.4 执行策略说明

- **执行顺序原则**：CAS 流 → UoW 身份 → public 缝 → 幂等/handoff → GC/安全。禁止先加路由再补 catalog。
- **风险控制原则**：`R-F07` 视为本 AP 主风险：任何「只 promote」或「catalog 无 ref」路径不得返回 handle；未完成流只 staging scanner；GC 与 ingest 走既有 TX1 quarantine / TX2 recheck，禁止用 24h grace 赌竞态。
- **测试推进原则**：Phase 1–2 先 L1/L2（流、UoW、GC fake clock）；Phase 3 起 L3 `create_app()` e2e；T04 为 mega（L3/L4），NH5 facet 未就绪则 L4 只断言 namespace+content hit（§8.4 交给 NH5，不假装覆盖）。分层服从 `T-O-406`，最低层以台账 C 为准。
- **文档同步原则**：执行期同步 S13 purpose 登记与 public 合同；evidence pack 落 `docs/evidence/new-harvest/AP-NH4/`。本轮只写本 AP，不改 QNA/final/RA。
- **回滚 / 降级原则**：`M-NH-05` 必须 forward-only；若 purpose CHECK 重建失败则 STOP，不得用无 CHECK 的字符串列绕过闭集。禁止降级为「内部 promote 冒充上传」或抬全局 `MKB_MAX_REQUEST_BYTES` 当上传面。NH1 若证伪，本并行窗不得继续装成已交付。

### 1.5 本次 action-plan 影响结构图

```text
authenticated public upload + object lifecycle
├── Phase 1: Bounded write
│   ├── ObjectStorePort 流式方法（ports.py / local_store.py）
│   ├── ASGI upload 路径绕开 1MiB 全缓冲，改 object_max_bytes 流式计数
│   └── staging mkstemp → fsync → os.replace；失败 unlink
├── Phase 2: Catalog+pending UoW
│   ├── M-NH-05 purpose CHECK + Literal 扩 upload_pending
│   ├── object_upload 服务：同 UoW INSERT catalog + pending ref 后才返回
│   └── 复用 artifacts.live_stored_object_uuid（digest+size live unique）
├── Phase 3: Public API fence
│   ├── POST /v1/teams/{team_uuid}/objects:upload
│   ├── GET  /v1/teams/{team_uuid}/objects:stat
│   ├── 架构扫描：raw/list/presign = 0；generation-artifact 元数据读保持独立
│   └── BusinessToken / 跨 team 403 / 未鉴权 401
├── Phase 4: Replay + ingest handoff
│   ├── unique (team,digest,size) live → 同一 handle
│   ├── local_object acquire: read_verified + catalog/live-ref fence
│   └── acceptance UoW：upload_pending → 业务 ref；Task UoW ≠ upload UoW
└── Phase 5: GC + security
    ├── pending live-ref 使 collect_candidates 不选中
    ├── TTL/cancel release 后 grace（unowned-at = last released_at）再 quarantine
    ├── TX2 见新 ref → restore（🔱 test_ns6_gc_toctou）
    └── 安全：../ filename、假 MIME、oversize、digest mismatch、零 presign/R2
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** `S-NH-F4`：authenticated upload+stat、bounded CAS、pending hold、GC（`T-O-385/396/404`）
- **[S2]** 有界流式写：chunk → 增量 SHA-256/size → `object_max_bytes` cap → expected digest → atomic promote / staging cleanup（`NH4-01`）
- **[S3]** 返回 handle 前同 UoW 提交 `mkb_stored_objects` + `mkb_object_references.purpose=upload_pending`；`M-NH-05` 扩 purpose 闭集（`NH4-02`）
- **[S4]** public v1 路由 upload+stat；stat 字段闭集 handle/digest/size/media/disposition；无 path/filename；跨 team 403；无 raw GET（`NH4-03`/`NH4-07`；`T-O-396`）
- **[S5]** team+digest+size 幂等 replay 与 typed conflict；tombstone 后再传（`NH4-04`；`T-O-383/385`）
- **[S6]** upload → 独立 `intake.ingest` `local_object`；acceptance 转业务 ref；upload-only 检索空（`NH4-05`）
- **[S7]** pending/grace/quarantine/restore；TTL/cancel release；staging scanner 清未完成流（`NH4-06`；`R-F07`）
- **[S8]** 上传安全负例：filename/path、MIME 不信、unauth/cross-team、oversize/digest mismatch、零 presign/R2（`NH4-08`；`T-O-377`）

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** `O-NH-01` live connector/cookie/tunnel、第五 kind、caller `workflow_key`、`action_branch`
- **[O2]** `O-NH-02` cuts/g0 算法重开、按通道复制 tail、前端/answer generation
- **[O3]** `O-NH-03` existing-object new-cleaner/validator upgrade（`T-O-401`）
- **[O4]** `O-NH-04` raw object GET/list/presign/browser；未来导出另 reopen（`T-O-396`）
- **[O5]** `O-NH-05` experiment 发车/评分；骨架非 DoD（`T-O-380`）
- **[O6]** `O-NH-06` 通用 Workflow JOIN/DSL/自由表达式/loader；云 OCR/CF/R2/SMCP runtime
- **[O7]** NH6–NH9 的 live 供给 / 10+3 激活 / 七意图 / campaign mega（本 AP 只提供 local_object **字节入口**）
- **[O8]** 把 generation-artifact 元数据 GET 升级成 object browser；实现 TUS/S3 MPU/OCI 分发栈；改 S13-T002 handle 为 stored_object_uuid（HEAD digest-in-handle 与 `T-O-385` replay 相容，本 AP 不重开身份；见 RA06 `NH-RA06-B07` 只登记）

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| authenticated upload + stat/status | `in-scope` | `S-NH-F4`；`T-O-385/396/404` | 推翻 Q16/Q24 须新 Truth |
| catalog + `upload_pending` 同 UoW | `in-scope` | `T-O-404`；`M-NH-05` | 无 |
| bounded stream Port | `in-scope` | `NH-RA06-B05`；对象帽 256MiB vs HTTP 1MiB | 无 |
| 独立 `local_object` ingest handoff | `in-scope` | `T-O-385`；NH7 local lane 依赖 | ingest 供给本身属 NH6/NH7 |
| raw GET / list / presign / 浏览器直读 | `out-of-scope` | `O-NH-04`；`T-O-396` | 未来导出独立 reopen |
| CF / R2 / Workers / SMCP | `out-of-scope` | `O-NH-06`；`T-O-377` | 无 |
| 第五 source kind / caller workflow_key | `out-of-scope` | `O-NH-01` | 无 |
| existing-object new-cleaner upgrade | `out-of-scope` | `O-NH-03`；`T-O-401` | 新 owner-gate |
| NH5 realm facet 检索 | `defer / depends-on-design` | T04 L4 若 NH5 未就绪只做 namespace+content hit | NH5 台账 C 通过后由 NH7/NH9 mega 补 facet |
| 公开 object 导出 / CDN | `out-of-scope` | Q16 未来导出另 reopen | 新 Q/A |
| TUS 协议 URL/头/SHA1 | `out-of-scope` | RA06 只借 checksum/lease **失败法** | 无 |
| handle 改为 stored_object_uuid | `out-of-scope` | 与 `T-O-385` digest+size replay 及 HEAD adapter 冲突未裁；本 AP 沿用 HEAD `mkbobj:v1:{team}:{sha256}` | 若将来对齐 S13-T002 须新 Truth |

---

## 3. 业务工作总表

> 编号 = final 台账 A。每个工作项保持不可约三元组：file:line / 收口目标 / Test-ID。

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| `NH4-01` | Phase 1 | Bounded write | `add`/`update` | `src/storage/ports.py:10-24`；`src/storage/local_store.py:32-39,71-105,89-99`；`src/runtime/config.py:26,58`；`api/app.py:536-556` | 流式 chunk 写入 CAS；超 cap 413、expected 不符 422；半写不进 catalog 且 staging 可清 | `NH4-T01` / `NH4-T07` | `high` |
| `NH4-02` | Phase 2 | Catalog+pending | `add`/`migrate` | `src/services/artifacts.py:27-35,143-169`；`src/contracts/storage/models.py:16-29`；`src/persistence/migrations/001_initial.sql:855-873`；新建 `018_nh4_upload_pending.sql`；新建 `src/services/object_upload.py` | commit 后存在 catalog **且** live `purpose=upload_pending`；缺一不返回 handle；零 Intake 行 | `NH4-T01` | `high` |
| `NH4-03` | Phase 3 | Upload+stat routes | `add` | `api/public/routes.py:56-452`（今日 0 upload）；`api/dependencies.py:109-156,206`；`api/app.py:70-73,558`；新建 `src/contracts/api/objects.py` | auth 上传返回 handle/digest/size/media/disposition；stat 同闭集且无 path/name | `NH4-T01` / `NH4-T03` | `high` |
| `NH4-04` | Phase 4 | Replay/conflict | `update` | `src/persistence/migrations/014_ns5_uuid_and_tombstone.sql:17-20`；`src/storage/local_store.py:84-87,100-105`；`src/contracts/common/errors.py:92-94` | 同 team+digest+size → 同一 handle；异 size/冲突 typed 409/422；跨 team 403；tombstone 后再传不分裂对外 handle | `NH4-T02` / `NH4-T03` | `high` |
| `NH4-05` | Phase 4 | local_object ingest | `update` | `src/runtime/intake/acquisition_ingest.py:404-455`（local_object `443-455`）；`src/contracts/api/models.py:116-121`；`src/runtime/intake/acceptance_snapshot.py:274-283`；`src/runtime/intake/generation_artifacts.py:597-621`；`src/runtime/task/task_create.py:67-92` | upload 后 `retrieval:search` 空；独立 ingest Task 才可命中；acceptance 将 pending 转为业务 ref；两 UoW 分离 | `NH4-T04` | `high` |
| `NH4-06` | Phase 5 | Pending/grace/quarantine | `update` | `src/services/object_gc.py:133-161,189-282,304-331`；`src/runtime/object_gc.py:32-61`；`api/app.py:348-351`；`tests/unit/test_ns6_gc_toctou.py:68-89` | pending 不可删；TTL/cancel release 后过 grace 可 quarantine/tombstone；quarantine 中新 ref restore | `NH4-T05` / `NH4-T06` | `high` |
| `NH4-07` | Phase 3 | No raw read | `add`（fence） | `api/public/routes.py:56-452,226-294`；`src/contracts/api/generation.py:1-6,28-62` | 不注册 raw/list/presign；stat 不泄 path/name；artifact 元数据读保持独立 | `NH4-T03` | `medium` |
| `NH4-08` | Phase 5 | Upload negatives | `add` | `src/storage/local_store.py:38-39,72-76,107-113`；`src/runtime/security.py:94-109`；`api/app.py:536-556`；§7.3 威胁模型 | `../` filename、假 MIME、unauth、cross-team、oversize、digest mismatch、零 presign 全部 typed fail | `NH4-T03` / `NH4-T07` | `high` |

---

## 4. Phase 业务表格

> **建议落点（写一次，HEAD 不存在，与现有 28 条 `/v1` 路由并列）**：
>
> | 方法 | 路径 | 鉴权 | 体 | 成功 |
> |------|------|------|----|------|
> | `POST` | `/v1/teams/{team_uuid}/objects:upload` | `BusinessToken` | **raw bytes 流**（`application/octet-stream` 或声明 `Content-Type`）；**禁止** multipart/TUS/presign | `201` 首次 / `200` replay |
> | `GET` | `/v1/teams/{team_uuid}/objects:stat?handle={url-encoded mkbobj:v1:...}` | `BusinessToken` | 无 | `200` JSON |
> | `POST` | `/v1/teams/{team_uuid}/objects:cancel` | `BusinessToken` | JSON `{"handle": "..."}` | `200` 释放 pending |
>
> 选择理由：现有路由已用 `{resource}:action`（`:activate` / `:search`）；handle 含冒号，**不**放进 path 段以免分裂。upload 用 raw stream 以便有界计数，不借 TUS URL。cancel 属于 `T-O-404` 的取消释放，不是 raw GET。
>
> **stat / upload 响应字段闭集**（`T-O-396`）：`handle`、`digest`、`size_bytes`（语义=size，键名对齐 `generation.py:52`）、`media_type`、`disposition` ∈ `{pending, ingested, expired, tombstoned}`。**禁止** `path` / `filename` / `object_root` / 存储 uuid 泄漏为下载权。
>
> **upload 请求头（非身份）**：`Content-Type` = 声明 media（不信）；可选 `X-MKB-Expected-SHA256` = 64-hex；可选 `Content-Disposition` filename **只用于拒绝扫描**，永不进 CAS path。
>
> **ASGI cap 分账**：非 upload 路径继续 `max_request_bytes`（默认 1MiB，`config.py:26` / `app.py:536-556`）。**仅** `objects:upload` 使用 `object_max_bytes`（默认 256MiB，`config.py:58`），且 **禁止** 把 chunk 拼成完整 `request._body`。禁止抬全局 `MKB_MAX_REQUEST_BYTES` 冒充上传面。

### 4.1 Phase 1 — Bounded write

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH4-01` | Bounded write | **净新/高风险，有序子步：** a) 在 `ObjectStorePort` 增 `open_write_stream` / `write_chunk` / `finalize_write` / `abort_write`（或等价 `promote_stream(AsyncIterator[bytes])`），保留现有 `promote(bytes)` 给内部小对象，内部实现改为走同一 hasher+staging，避免两套 CAS。b) chunk 循环：增量 `hashlib.sha256.update` + 累加 size；`size > max_object_bytes` 立即 `OBJECT_BUDGET_SIZE` 413 并 `abort_write`。c) finalize：若 `expected_sha256` 存在且 ≠ 实算 digest → `OBJECT_INTEGRITY_DIGEST` 422，不 `os.replace`。d) 命中已有 CAS 文件则再哈希校验，碰撞 `OBJECT_INTEGRITY_COLLISION` 503；否则 staging `mkstemp` → write/fsync → `os.replace` → fsync dir（沿用 `local_store.py:89-99`）。e) `finally` 清理 staging；崩溃/取消留下的 `object_root/staging/promote-*` 只归 staging scanner。f) ASGI `reject_oversize_body`（`app.py:536-556`）对 upload 路径 **停止** `chunks.append` 全缓冲，改为透传 `request.stream()` 并由对象层计数；Content-Length 预检改用 `object_max_bytes`。g) 失败路径：空 body size=0 是否允许？本 AP 定 **拒绝** `size_bytes < 1` → 422 `OBJECT_BUDGET_SIZE`（与 inline `size_bytes < 1` 栅栏同构，`acquisition_ingest.py:427-431`）。h) 不把 `media_type` 写入 CAS 路径（路径仍 `objects/<team>/sha256/<aa>/<bb>/<64hex>`，`local_store.py:38-39`）。 | `src/storage/ports.py:10-24`；`src/storage/local_store.py:32-39,71-105,89-99`；`src/runtime/config.py:26,58`；`api/app.py:212,536-556` | Port 可在不超过 cap 的前提下流式 promote；L3 上传 >1MiB 且 ≤object cap 不再被 ASGI 1MiB 413；超 cap/坏 digest 无 catalog | `NH4-T01` / `NH4-T07` | 无全内存 `data: bytes` 作为 public 唯一写路径；失败不留 catalog；staging 半写可被 scanner 识别 |

### 4.2 Phase 2 — Catalog+pending UoW

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH4-02` | Catalog+pending | **净新/高风险，有序子步：** a) `M-NH-05` forward-only：新建 `src/persistence/migrations/018_nh4_upload_pending.sql`，把 `mkb_object_references.purpose` CHECK 从 8 值扩到含 `upload_pending`（SQLite 不能 ALTER CHECK → 重建表 + `INSERT SELECT` + 重建 `ix_obj_ref_*`，**不得**丢行）。b) 同步 `PromoteRequest.purpose` Literal（`models.py:18-27`）。c) 新建 `ObjectUploadService`：CAS finalize 成功后 `async with persistence.transaction()`：`live_stored_object_uuid`（`artifacts.py:27-35`）按 `(team,digest,size)` 查找 live 行；无则 `uuid7` INSERT `mkb_stored_objects`；**无论新旧** INSERT `mkb_object_references` `purpose='upload_pending'`、`owner_kind='authenticated_upload'`、`owner_uuid=upload_session_uuid`、`expected_digest/size` 与实算一致；`payload_extra.expires_at` 或列 `expires_at`（建议列，便于 TTL SQL；若用 extra 必须有可扫索引策略）。d) **commit 成功后**才构造响应 handle（HEAD 格式 `mkbobj:v1:{team}:{sha256}`，`local_store.py:17-21,101`）。e) 任一步失败：不返回 handle；CAS 已 promote 的字节视为 S13 orphan（对 GC 不可见）→ Phase 5 uncatalogued reconciler；未 finalize 的只 staging。f) 同 digest+size 已有 **live pending** → 不插第二 live unique catalog 行，replay 同一 handle（可刷新 TTL，不得制造双 live catalog）。g) 禁止在此 UoW 写 `mkb_intake_sources` / `mkb_intake_items` / `mkb_intake_revisions`。h) 与 Task create 解耦：不调用 `task_create.py:70-72` 的「只为 new Task promote」。 | `src/services/artifacts.py:27-35,143-169`；`src/contracts/storage/models.py:16-29`；`001_initial.sql:855-873,1800-1801`；`014_ns5_uuid_and_tombstone.sql:17-20`；新建 migration + `src/services/object_upload.py`；`api/app.py:70-98` Container 接线 | 成功响应前 DB：`mkb_stored_objects` ≥1 live 行 ∧ live ref purpose=`upload_pending`；`mkb_intake_sources`/`items`/`revisions` 计数=0 | `NH4-T01` | 无 catalog 或无 live pending ⇒ HTTP 非 2xx 且无 handle |

### 4.3 Phase 3 — Public API fence

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH4-03` | Upload+stat routes | **净新/高风险，有序子步：** a) 在 `api/public/routes.py` **并列**增加 §4 建议三条路由，继续 `APIRouter(prefix="/v1")` + `token: BusinessToken`。b) upload handler：校验 `team_uuid` path 与 token 后的 team 资源存在且 `active`（同 `task_create.py:74-78`）；把 `request.stream()` 交给 `ObjectUploadService`；声明 media 取 `Content-Type`（去掉 charset 参数，截断 255）。c) 响应 JSON 仅闭集五字段；首次 201、replay 200。d) stat：解析 handle；handle.team ≠ path team → `OBJECT_AUTH_TEAM_MISMATCH` 403（**禁止** 404 当存在性神谕）；本 team tombstoned → 200 `disposition=tombstoned`；live pending → `pending`；已有业务 ref → `ingested`；pending 已 release 尚未 tombstone → `expired`。e) 不读、不返回文件系统 path。f) 失败：未鉴权 401 `SEC_TOKEN_MISSING`/`SEC_TOKEN_INVALID`（`security.py:94-109`）；team 不存在 404；未 active 409。g) 不在 handler 内 `storage.promote(await request.body())`。 | `api/public/routes.py:29,56-452`；`api/dependencies.py:109-156,206`；新建 `src/contracts/api/objects.py`；`src/services/object_upload.py` | 28+2（或+3 cancel）条 `/v1` 路由；upload/stat 可调用；响应无 path/filename | `NH4-T01` / `NH4-T03` | 经 public HTTP 得到 handle；内部 Port 调用不算 |
| `NH4-07` | No raw read | a) **不**注册 `GET` 返回 `application/octet-stream` / `FileResponse` / `StreamingResponse` 对象字节的路由。b) 架构扫描：`api/public/routes.py` 与 `api/internal/routes.py` 零匹配 `upload` 以外的 object bytes GET、零 `presign`、零对象 list collection。c) 现有 generation-artifact GET（`routes.py:226-294`）保持 Task 作用域元数据，**不**改成 object browser，**不**返回 bytes。d) `read_verified` 仍仅内部 ingest/repair 使用，不 export 到 public。 | `api/public/routes.py:226-294,452`；`src/contracts/api/generation.py:1-6,50-54`；`src/storage/local_store.py:107-122` | raw/list/presign=0；artifact 读仍须 token 且无字节 | `NH4-T03` | 扫描器 0 命中禁止模式 |

### 4.4 Phase 4 — 幂等与 ingest 交接

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH4-04` | Replay/conflict | a) 身份分母 = live unique `(team_uuid, content_digest, size_bytes)`（`src/persistence/migrations/014_ns5_uuid_and_tombstone.sql:17-20`）。b) 并发双传同字节：一方 INSERT catalog 成功，另一方 unique 冲突 → 再读 live 行，返回**同一 handle**，不得第二 live catalog。c) 「异 size 冲突」：caller `expected_sha256` 已指向本 team live 对象，但实算 size ≠ catalog `size_bytes`，或试图以不同 size 登记同一 digest → typed `ConflictError`/`OBJECT_INTEGRITY_*`（409/422），不得覆盖 CAS。d) 跨 team：B team 路由携带 A team handle → 403；同 digest 在两 team **分 path**（`local_store.py:38-39`），禁止复用文件。e) tombstone 后同一 digest+size 允许新 `stored_object_uuid`（现测 `test_object_gc.py:285-303`），但对外 handle 仍是 digest 格式 → replay 同一字符串；响应不得改成 uuid handle。f) 并发第二 catalog 不得 silent last-write-wins。 | `src/persistence/migrations/014_ns5_uuid_and_tombstone.sql:17-20`；`local_store.py:38-39,84-87,100-105`；`errors.py:92-94`；`object_upload.py` | 并行同字节 → 1 live catalog + 1 handle；冲突 typed | `NH4-T02` | 无双 live unique 行 |
| `NH4-05` | local_object ingest | **有序子步：** a) 调用方用 upload 返回的 `logical_handle` 建 `request_intent=intake.ingest`、`source_kind=local_object`（既有 DTO `models.py:116-121`）。b) acquire：`read_verified`（`acquisition_ingest.py:443-455`）**之前**加 catalog/live-ref fence：无 live catalog 或无 live ref（pending 或业务）→ typed 409/422，禁止「持猜测 handle 读未 catalog 字节」当 public 成功。c) Task create 走既有 UoW（`task_create.py:67-92`），**禁止**把 upload 字节再 promote 进 Task 事务当新身份。d) acceptance（`acceptance_snapshot.py:274-283` + `_reference_object` `generation_artifacts.py:597-621`）在 **自己的** Outcome UoW：对**原始** `stored_object_uuid` INSERT 业务 ref（`purpose=intake_snapshot_artifact` 或既有闭集内业务 purpose，`owner_kind=intake_source`/`intake_snapshot`）并 `UPDATE ... SET released_at=?` 释放 `upload_pending`。e) 失败 ingest 不 release pending（留给 TTL）。f) upload-only 后 `POST /v1/teams/{team}/retrieval:search` 带 NH1 namespace fixture → 0 hit（`FG-NH-03/05`）。g) 不得 monkeypatch `container.storage.promote`（`test_source_capability_paths.py:77-82` 是反例，`FG-NH-10`）。 | `acquisition_ingest.py:404-455`；`models.py:116-121`；`acceptance_snapshot.py:54-67,274-283`；`generation_artifacts.py:597-621`；`task_create.py:67-92`；`routes.py:452-468` | 两步可证；检索只在 ingest 后命中 | `NH4-T04` | upload 事务 Item=0；ingest 后 namespace content hit |

### 4.5 Phase 5 — GC + 安全负例

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH4-06` | Pending/grace/quarantine | **有序子步：** a) live `upload_pending` 使 `collect_candidates` 的 `NOT EXISTS live ref` 为假 → 不可删（blocker 走 `LIVE_REFERENCE`；不必把 pending 塞进 `operator_hold` 集合，以免与 ops hold 混淆）。b) TTL scanner（fake clock 可注入，同 `object_gc.py:114-127`）：`now >= expires_at` 且仍 live pending → `released_at=now`，**不**立刻 unlink。cancel 路由同样只 release。c) **grace 起点**：既有 SQL 用 `stored_objects.created_at`（`object_gc.py:143-160`）。若 pending 持有期间已超过 grace，release 后会**立即**成为候选，违反「TTL 后才进入 grace」。必须扩候选谓词：无任何历史 ref 的真 orphan 仍用 `created_at`；曾有 ref 的对象用 `max(released_at) <= now-grace`（未释放则不可见）。既有 `_seed_orphan` 无 ref 行，回归不得红。d) TX1 recheck → `quarantine_object` → TX2 recheck；见新 live ref（含新 pending 或 ingest 业务 ref）→ `restore_quarantined`（`object_gc.py:189-282`；`test_ns6_gc_toctou.py:68-89`）。e) staging scanner：只扫 `object_root/staging/`，mtime/ctime 超过 `object_staging_ttl_seconds` 的 `promote-*` unlink；**不**碰 `objects/` CAS。f) uncatalogued-CAS reconciler（`R-F07`）：`objects/` 下文件无 catalog 行且年龄≥grace → 删除磁盘副本，**永不**返回过 handle 的对象走这条（那些有 catalog）。g) 0 grace 继续构造期 `ValueError`（`object_gc.py:116-120`）。 | `src/services/object_gc.py:112-161,189-331`；`src/runtime/object_gc.py:19-61`；`api/app.py:348-351`；新建 ttl/staging scanner；`tests/unit/test_object_gc.py:33-73,274-279` | pending 扫描 0 删除；release+grace 后 tombstone+proof；交错 restore | `NH4-T05` / `NH4-T06` | 无「grace 赌竞态」；无 pending 被删 |
| `NH4-08` | Upload negatives | a) filename/`Content-Disposition` 含 `..`、`/`、NUL、绝对路径 → `SEC_PATH_REJECTED` 422，不写盘。b) `Content-Type` 谎报不改变 digest 身份、不进 path；stat.media_type 仅声明。c) 无 `Authorization` → 401；跨 team handle → 403。d) body > `object_max_bytes` → 413 `OBJECT_BUDGET_SIZE` 或 `REQUEST_BODY_TOO_LARGE`（upload 路径应走对象码，避免与 1MiB 帽混淆）。e) expected digest 不符 → 422 `OBJECT_INTEGRITY_DIGEST`，无错误终态 catalog。f) 仓库扫描零 `presign`/`r2`/`cloudflare` 作为本表面实现。g) chunked 无 CL 超 cap 必须在落到 handler 前 413（沿用 `test_ns6_phase5.py:101-127` 模式，目标改 upload 路径与 object cap）。 | `local_store.py:38-39,72-76,107-113`；`security.py:94-109`；`app.py:536-556`；§7.3 | 攻击矩阵全 typed fail | `NH4-T07` / `NH4-T03` | 无 200 成功路径；无 path 泄漏 |

---

## 5. Phase 详情

### 5.1 Phase 1 — Bounded write

- **Phase 目标**：公共可写路径不再依赖全内存 `promote(bytes)`；有界、可校验、可 abort。
- **本 Phase 对应编号**：`NH4-01`
- **本 Phase 新增文件**：无强制独立模块；允许 `src/storage/stream_write.py` 若 `local_store.py` 过长则拆 session 类型（仍属 storage adapter）
- **本 Phase 修改文件**：`src/storage/ports.py:10-24`；`src/storage/local_store.py:71-105`；`api/app.py:536-556`；`src/runtime/config.py`（仅当需 `object_staging_ttl_seconds`，默认可放 Phase 5）
- **本 Phase 删除文件**：无
- **具体功能预期**：
  1. `write_chunk` 后 hasher/size 单调增加；达到 cap+1 立即失败，已写 staging 被 abort unlink。
  2. `finalize_write` 在 expected 匹配且 size≥1 时 atomic promote，返回 `ObjectStat`（handle+sha256+size+声明 media）。
  3. 已存在 CAS 且内容哈希等于 digest → 复用文件，不写第二副本。
  4. 已存在 CAS 但内容哈希 ≠ digest → 503 `OBJECT_INTEGRITY_COLLISION`，不覆盖。
  5. **失败/降级**：客户端中断/超时 → abort；ASGI 对非 upload 路径行为不变（1MiB 帽仍在）；upload 路径不得 `request._body = b"".join(chunks)`。
  6. **失败**：size=0 → 422；expected 非 64-hex → 422（契约层）。
- **对应测试台账项**：`NH4-T01` / `NH4-T07`（详见 §8）
- **收口标准**：public 写路径流式；内部 `promote(bytes)` 仍可用但不算 public DoD
- **本 Phase 风险提醒**：只改 Port 不改 ASGI 会在 1MiB 处假失败；只改 ASGI 抬全局 cap 会造成 Task JSON DoS（`R-F07` 的带宽面）

### 5.2 Phase 2 — Catalog+pending UoW

- **Phase 目标**：usable handle 的充分必要 = CAS bytes ∧ catalog ∧ live `upload_pending` 已提交。
- **本 Phase 对应编号**：`NH4-02`
- **本 Phase 新增文件**：`src/persistence/migrations/018_nh4_upload_pending.sql`；`src/services/object_upload.py`
- **本 Phase 修改文件**：`src/contracts/storage/models.py:16-29`；`api/app.py` Container 注册 upload 服务；必要时 `src/services/artifacts.py` 抽出共享 catalog helper（不要复制 SQL 漂移）
- **本 Phase 删除文件**：无
- **具体功能预期**：
  1. 成功 commit 后：`SELECT` live catalog by digest+size 恰好 1 行；live ref `purpose=upload_pending` ≥1。
  2. `mkb_intake_sources` / `mkb_intake_items` / `mkb_intake_revisions` 对该 team 在 upload 事务内增量为 0。
  3. 故意在 catalog INSERT 后注入失败（L2）：调用方拿不到 handle；随后 GC/reconciler 不把该失败当成业务成功。
  4. 重复相同字节：不新增 live catalog 行；handle 字符串相等。
  5. **失败**：purpose 仍为旧 8 值时 INSERT `upload_pending` 必须被 DDL 拒绝——证明 `M-NH-05` 已应用。迁移前测试红、迁移后绿。
  6. **失败**：无 pending ref 的「只 catalog」不得被服务标成功（与 GC orphan 类相同，`test_object_gc.py:33-63`）。
- **对应测试台账项**：`NH4-T01`
- **收口标准**：`T-O-404` 谓词在 HTTP+DB 同时成立
- **本 Phase 风险提醒**：SQLite CHECK 重建丢索引/丢 `released_at` 行；必须在 evidence `migrations/` 放 before/after

### 5.3 Phase 3 — Public API fence

- **Phase 目标**：调用方可经 `/v1` + Bearer 上传并 stat；不能经 public 读字节。
- **本 Phase 对应编号**：`NH4-03` / `NH4-07`
- **本 Phase 新增文件**：`src/contracts/api/objects.py`
- **本 Phase 修改文件**：`api/public/routes.py`（在 `:452` 检索路由旁追加，不插入 raw GET）；`api/app.py` 中间件分路径 cap
- **本 Phase 删除文件**：无
- **具体功能预期**：
  1. `POST .../objects:upload` 鉴权成功返回闭集 JSON；`GET .../objects:stat` 同 handle 字段一致。
  2. 响应 JSON keys ⊆ `{handle, digest, size_bytes, media_type, disposition}`（允许加 `digest_algorithm=sha256` 常数，**禁止** path/filename）。
  3. 未鉴权 401；跨 team 403；stat 不返回 objects/ 下任何相对路径。
  4. generation-artifact 三条 GET 仍 2xx 且 body 无对象字节。
  5. **失败**：对 handle 发 `GET /v1/teams/{t}/objects/{digest}` 或任意新 raw 路径 → 404/405，测试扫描不得发现已注册 raw。
  6. **失败**：内部调用 `read_verified` 成功不得作为本 Phase public DoD。
- **对应测试台账项**：`NH4-T01` / `NH4-T03`
- **收口标准**：`D-14` 从「28/0」变为「存在 upload+stat 且 raw=0」；`FG-NH-10` 机器可检
- **本 Phase 风险提醒**：误把 `StreamingResponse(read_verified())` 当成「方便调试」即违反 `O-NH-04`

### 5.4 Phase 4 — 幂等与 ingest 交接

- **Phase 目标**：upload 服从 `T-O-383`；对象存在 ≠ 可检索；ingest 另 UoW。
- **本 Phase 对应编号**：`NH4-04` / `NH4-05`
- **本 Phase 新增 / 修改 / 删除文件**：修改 `acquisition_ingest.py:443-455`（catalog fence）；修改 acceptance 释放 pending；不删除 Task inline promote
- **具体功能预期**：
  1. 并发 N=2 同 body → 1 handle、1 live catalog。
  2. 跨 team 同 digest 产生不同 handle 前缀（team uuid 段不同）。
  3. upload 后立即 search（合法 namespace）hits=0，且 Item 计数=0。
  4. 随后 ingest Task 独立 commit；acceptance 后原对象 pending `released_at` 非空且业务 ref live；search content 命中（L4 无 facet 要求见 §8.4）。
  5. **失败**：未 catalog 的内部 promote handle 做 `local_object` ingest → fence 失败（修复 `test_source_capability_paths.py:77-82` 类路径：执行期该 e2e 须改为 public upload 或先 catalog，属本 AP 兼容债，不是 NH7 范围外溢）。
  6. **失败**：upload UoW 与 Task UoW 同一事务实现 → 拒绝合入（代码审 + 测试可观测到两次 commit）。
- **对应测试台账项**：`NH4-T02` / `NH4-T04`
- **收口标准**：两步法；`FG-NH-03`/`FG-NH-10`
- **本 Phase 风险提醒**：T04 依赖 NH1 namespace fixture 与真实 ingest 供给；NH6 runtime 未就绪时 local 文本/html 仍可 ingest，不把 PDF/OCR 供给失败算本 AP 功能缺口（交 NH6/NH7）

### 5.5 Phase 5 — GC + 安全负例

- **Phase 目标**：合法 pending 不被收；放弃后可收；攻击面 fail-closed。
- **本 Phase 对应编号**：`NH4-06` / `NH4-08`
- **本 Phase 新增文件**：`src/services/object_upload_ttl.py`（或并入 `object_gc.py` 旁路模块，禁止把 TTL 写进 HTTP handler）；`tests/unit/test_nh4_upload_ttl_gc.py`；`tests/e2e/test_nh4_upload_security.py`
- **本 Phase 修改文件**：`src/services/object_gc.py:133-161` 候选谓词；`tests/unit/test_ns6_gc_toctou.py` 增 pending 交错；`src/runtime/config.py` TTL knobs
- **本 Phase 删除文件**：无
- **具体功能预期**：
  1. 刚 upload、age&lt;grace 且 pending live → `collect_candidates` 不含该对象。
  2. fake clock 过 TTL → pending `released_at` 有值，字节仍 `read_verified` 成功。
  3. 再推进 grace → quarantine + proof + tombstone；`read_verified` 404 `OBJECT_MISSING`。
  4. quarantine 窗口插入新 live ref → `LIVE_REFERENCE` + 字节 restore（🔱 扩 NS6）。
  5. **失败**：`../etc/passwd` filename → 422；假 `image/png` 不改变 sha256 身份；超 cap 413；digest mismatch 422；无 token 401；他队 handle 403；代码/路由零 presign。
  6. **失败**：0 grace 配置拒绝；staging 泄漏文件在 TTL 后消失且从未出现 catalog。
- **对应测试台账项**：`NH4-T05` / `NH4-T06` / `NH4-T07`
- **收口标准**：`R-F07` 缓解可证；威胁模型向量均有负例
- **本 Phase 风险提醒**：改 `created_at` 谓词可能误删从未持有 pending 的新 catalog——必须用「无 ref 史用 created_at / 有 ref 史用 last released_at」双路径，并用既有 `test_object_gc.py` 全绿做回归

---

## 6. 依赖的冻结设计决策（只读引用）

> 只引 Q 编号 + T-O-ID，不复制业主长文、不改口、不开新 Q/A。

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Q5 / `T-O-385` | `pre-initial-planning-qna.md` | upload=S13 handle+digest+size；不造 Item；随后独立 ingest；同 team+sha256+size replay | STOP；禁止改成上传即 Item |
| Q16 / `T-O-396` | `pre-charter-qna.md`；gate `G-NH-07` CLOSED | public v1 仅 upload+stat；无 raw GET；跨 team 403；artifact 读独立 | STOP；禁止加 raw 作为「临时调试」 |
| Q24 / `T-O-404` | `pre-charter-qna.md`；gate `G-NH-16` CLOSED；`M-NH-05` | catalog+`upload_pending` 同 UoW 后才返回 handle | 不返回 handle；标 blocked |
| Q3 / `T-O-383` | `pre-initial-planning-qna.md` | 上传幂等/冲突与 Task 同一 fail-loud 法 | 冲突必须 typed，禁止覆盖 |
| `T-O-377` | foundational fence | 零 CF/R2/SMCP；禁止 presign 实现 | 扫描命中即失败 |
| `T-O-381` | live-matrix | 公共上传必须落地（completeness 面，不是 Item） | 本 AP 未完成则 NH7 local 格不得标 live |
| Q26 / `T-O-406` | `pre-charter-qna.md` | L1–L4 不可互换；本 AP 最低层以台账 C 为准 | 禁止用 L1 顶 T01/T04 |
| `T-O-376` | completeness | 接通到检索链；T04 是本 AP 对 completeness 的交接，不是 10+3 全矩阵 | 不把本 AP 扩成 NH7 |
| `O-NH-04` / `O-NH-06` | final §4.2 | raw/list/presign/R2 OOS | 出现在 diff 即 S1 |
| `T-R-NH-25` | final §2.1 | HEAD upload/stat/purpose=0，必须从 public auth route 验证 | 禁止内部 promote 当绿 |
| `FG-NH-10` | proposed §9.6（防假绿；final DoD 引用） | 经 public route 上传 + 零 Item 直到独立 ingest | 违反则不得标本 AP 完成 |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表（本计划工作要落在哪些既有代码 / 新建点上）

> `处置`：`✅ 复用` / `♻️ 重 substrate` / `🆕 净新`。台账 B `NH4-A01..A06` 全覆盖。行号为 2026-08-29 HEAD `1221aa1` 独立核验；相对 final 台账 B 的漂移写在备注。

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| `NH4-A01` | `src/storage/local_store.py:71-122` | CAS `promote` + `read_verified` team mismatch 403 | `NH4-01` 流式化写；`NH4-04/05/08` 复用 verify-on-read / 403 | `✅ 复用` | 独立核验：`promote` `71-105`（size 413、expected 422、staging `89-99`、handle `101`）；`read_verified` `107-122`（非法 handle 422、team 403、缺文件 404、坏哈希 503）。**promote 成功 ≠ public DoD** |
| `NH4-A02` | `src/services/object_gc.py:133-282` | catalog-without-ref 候选 + quarantine/recheck | `NH4-06` 扩 pending；TX2 restore | `✅ 复用` / 扩 pending | 台账 B 写 `:133-245`。独立核验：`collect_candidates` **133-161**（`NOT EXISTS` live ref）；`delete_candidate` **189-282**（TX1/quarantine/TX2/tombstone）；blocker **304-331**（`operator_hold`/`backup_hold`→HOLD，其它 live→`LIVE_REFERENCE`）。实现时以 133-161 + 189-331 为准 |
| `NH4-A03` | `api/public/routes.py:56-452` | 28 条 `/v1` 路由，0 upload/stat | `NH4-03` 并列新路由；`NH4-07` 扫描底数 | `🆕 净新` public surface | 独立 `rg @router.(get\|post\|patch\|delete\|put)` = **28**；首条 `:56` `POST /teams`，末条装饰器 `:452` `POST /retrieval:search`。`T-R-NH-25` |
| `NH4-A04` | `src/storage/ports.py:10-24` | Port 仅 `promote(data: bytes)` 等，无 stream | `NH4-01` ♻️ bounded stream | `♻️ 重 substrate` | 独立核验 Protocol `11-24`：`promote`/`read_verified`/`delete_if_unreferenced`/`quarantine_object`/`restore_quarantined`/`destroy_quarantined`/`readiness`。全内存不可 public |
| `NH4-A05` | `src/runtime/intake/acquisition_ingest.py:404-455` | local handle `read_verified` | `NH4-05` handoff + catalog/ref fence | `✅ 复用` | 台账 B / RA 写 `:413-455`。独立核验：`_acquire_content` 自 **404**；`source_kind` 于 **412**；**local_object 分支 443-455**（handle 非 str→422；`read_verified` 后构造 representation，**不查 catalog**）。fence 加在 447 前 |
| `NH4-A06` | RA06 WEB TUS/S3/OCI/OWASP | checksum / lease / 上传安全失败法 | `NH4-01/06/08` 只借失败法 | `🆕` 本仓 UoW | 不借云 key/presign/TUS URL。真源见 §7.3 |
| `NH4-H01`（补充，非台账 B） | `src/contracts/storage/models.py:16-29` | purpose Literal 8 值，无 `upload_pending` | `NH4-02` `M-NH-05` | `♻️ 重 substrate` | 独立核验 purpose **18-27**；`PromoteRequest` **16-29**。DDL CHECK `001_initial.sql:859-862` 同 8 值 |
| `NH4-H02`（补充） | `src/services/artifacts.py:27-35,143-169` | live unique 查找 + catalog+ref 同 UoW 范例 | `NH4-02` 复用 helper，purpose 改为 pending | `✅ 复用` | HEAD 写死 `purpose='process_io'`（`:167`）；upload 不得照抄成 process_io |
| `NH4-H03`（补充） | `api/app.py:212,348-351,536-556` | LocalObjectStore 构造；GC 接线；ASGI 全缓冲 1MiB 帽 | `NH4-01` 中间件分账；`NH4-06` scanner | `♻️ 重 substrate` | upload 路径禁止 `chunks.append` |
| `NH4-H04`（补充） | `src/persistence/migrations/014_ns5_uuid_and_tombstone.sql:17-20` | live unique `(team,digest,size)` | `NH4-04` 幂等分母 | `✅ 复用` | tombstone 后可新 uuid；对外 handle 仍 digest |
| `NH4-H05`（补充） | `tests/unit/test_object_gc.py` + `tests/unit/test_ns6_gc_toctou.py:68-89` | orphan GC 与 quarantine restore 🔱 | `NH4-06` fork pending 交错 | `✅ 复用` | `_seed_orphan` **只 catalog 不 ref**（`:48-62`）= 反例类，也是 GC 正例种子 |
| `NH4-H06`（补充） | 新建 `POST/GET /v1/teams/{team_uuid}/objects:*` | public 缝 | `NH4-03` | `🆕 净新` | HEAD 无此文件级符号 |
| `NH4-H07`（补充） | `src/runtime/intake/generation_artifacts.py:597-621` | `_reference_object` 幂等插 ref | `NH4-05` acceptance 转业务 ref | `✅ 复用` | 在 Outcome UoW 调，不在 upload UoW |
| `NH4-H08`（补充） | `api/public/routes.py:226-268` + `generation.py:1-6` | 业务 artifact **元数据**读 | `NH4-07` 保持独立 | `✅ 复用` | 正例：不泄 runtime path；反例：若升级成字节下载 |

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | 直接把 `ObjectStorePort.promote` 暴露为 public HTTP | 不写 catalog/ref、忽略 purpose、整段内存（`ports.py:12`；`local_store.py:71-105`；`FG-NH-10`） |
| ⛔2 | `tests/e2e/test_source_capability_paths.py:77-82` 内部 `container.storage.promote` 冒充上传 | `FG-NH-10`；`T-R-NH-25`；RA06 `NH-A-06-16` |
| ⛔3 | Task inline staging / `task_create.py:70-72`「只为 new Task promote」当 public 入口 | `T-O-385` 要独立 upload 事务；inline 1MiB 帽无法替代 |
| ⛔4 | catalog 无 live ref 当 upload 成功 | 与 GC orphan 同类（`object_gc.py:146-161`；`test_object_gc.py:41-63`；`T-O-404`） |
| ⛔5 | 未 catalog 的 CAS 当成功；GC 看不见则泄漏 | `local_store.py:25-29` vs `object_gc.py:146-150`；`R-F07` |
| ⛔6 | raw GET / list / presign / 浏览器直读 | `O-NH-04`；`T-O-396`；OWASP public retrieval |
| ⛔7 | 用 24h grace 区分「等 ingest」与「遗弃」 | Q24；`NH-RA06-B03` |
| ⛔8 | 信任 `Content-Type` / filename 当身份 | RA06-WEB-04；CAS 身份是 digest+size |
| ⛔9 | 遗产 R2 key / `{file_uuid}.ext` / presign PUT | `T-O-377`；RA06-LEGACY-02/⛔ |
| ⛔10 | `static_upload` 跳过 workflow、上传即 ready | `T-O-385/386`；RA06-LEGACY-03 |
| ⛔11 | confirm 只 HEAD 存在性、MPU ETag 当全对象 digest | 必须全对象 SHA-256 |
| ⛔12 | 抬 `MKB_MAX_REQUEST_BYTES` 到 256MiB 当上传面 | 放大 Task JSON DoS；RA06 §6.3 |
| ⛔13 | sqlite3 直读 Turso 当 DB 证据 | `FG-NH-12`；必须 `PersistencePort` UoW |
| ⛔14 | Task `succeeded` / `publication_ready` 当可检索 | `FG-NH-03/04`；T04 必须 search |
| ⛔15 | monkeypatch fetcher/storage 当 L3 成功 | `FG-NH-01/10` |
| ⛔16 | 跨 team 404 当存在性神谕 | `T-O-396`；`read_verified` 已 403 |
| ⛔17 | 把 MIME 当 CAS 权威 / unique 键 | unique 不含 media（`014:17-20`）；`NH-C-53` |
| ⛔18 | 第五 kind / workflow_key / CF/SMCP / `--no-sandbox` 默认 / existing-object upgrade | 共享法硬禁；`O-NH-01/03/06` |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：
  - RA06 全文：[`assessment-analysis-06-public-upload-and-object-lifecycle.md`](../../eval/new-harvest/reference-anchor/assessment-analysis-06-public-upload-and-object-lifecycle.md) — §7.1 是与本 AP 相关子集；完整 ✅借/🔶部分借/⛔反例/🆕净新 见 RA06 §3。
  - RA09 只消费：`W-GC-INGEST`（`object_gc.py:189-240` + `test_ns6_gc_toctou.py:68-89`）；`NH-RA09-B05` public upload=0；`RA-09-HEAD-12` quarantine restore。**不改写** RA09 功能设计。
- **外部借鉴（§7.1 不混用图例）**：

| 来源 | verdict | 借 / 不借 |
|------|---------|-----------|
| TUS checksum/expiration | `🔶部分借` | 借块校验失败丢弃、未完成过期。不借 URL/头/SHA1/公网协议 |
| S3 integrity / MPU | `🔶部分借` | 借「分块校验 ≠ 对象身份哈希」、未 complete 必须回收。不借 bucket/key/ETag |
| OCI descriptor | `🔶部分借` | 借 digest 身份 + size 防碰撞 + media 非键。不借镜像分发栈 |
| OWASP File Upload CS | `🔶部分借` | 借鉴权、尺寸、不信 MIME、不用 filename 当身份、勿公开取回。杀毒/扩展名白名单不自动 DoD |
| GCS generation-match | `🔶部分借` | 借条件写防覆盖。本仓身份是 digest unique + typed conflict |
| containerd lease | `🔶部分借` | 借「未引用但合法必须 hold」。不借标签/gRPC；映射到 `upload_pending` live ref |
| legacy admin init/confirm | `🔶部分借` | 借字节进仓与 ingest 分步。不借 R2/presign/file_uuid |
| legacy static_upload / presign | `⛔反例` | 上传即 ready；云 key |

- **安全 / 信任边界威胁模型（不得留空；对齐 S16 与 `T-O-396/404`）**：

| 向量 | 攻击者目标 | 落点 | 缓解（本 AP） | 测试 |
|------|------------|------|---------------|------|
| path traversal via filename | 写出 `object_root` 外 / 覆盖系统文件 | `Content-Disposition` / 任意 filename 头；CAS path `local_store.py:38-39` | filename **永不**拼接进 path；`..` `/` NUL → `SEC_PATH_REJECTED` 422 | `NH4-T07` |
| MIME 谎报 | 把可执行/HTML 当 image 绕过后续策略 | `Content-Type` | media 只声明、不进 unique、不进 path；身份=digest | `NH4-T07` |
| 跨 team handle | 读/stat/cancel 他队对象；存在性神谕 | handle 内 team uuid vs path | `OBJECT_AUTH_TEAM_MISMATCH` 403（`local_store.py:111-112` 同构） | `NH4-T03` |
| 超大 body / chunked 无 CL | 内存 DoS；绕 1MiB 帽 | `app.py:536-556` | upload 路径流式计数 `object_max_bytes`；超限立即 413，不 join 全缓冲 | `NH4-T07` |
| digest mismatch | 用错误 expected 顶替已有对象 | `expected_sha256` | 422 `OBJECT_INTEGRITY_DIGEST`；不 catalog 错误终态 | `NH4-T07` |
| 未鉴权 | 匿名写入/stat | `BusinessToken` | 401 `SEC_TOKEN_MISSING`/`INVALID`（`security.py:94-109`） | `NH4-T03`/`T07` |
| 未完成 staging 磁盘泄漏 | 填满磁盘 | `object_root/staging` | abort unlink + staging TTL scanner | `NH4-T06`/`T07` |
| GC TOCTOU 删仍-pending | 丢掉合法待 ingest 字节 | `collect_candidates` / quarantine 窗 | pending=live ref；TX2 restore；禁止 0 grace | `NH4-T05` |
| raw GET / presign | 把 CAS 当 CDN / 托管恶意内容 | 新路由 | 不注册；架构扫描 0 | `NH4-T03`/`T07` |
| 把 handle 当下载权 | 持 handle 即读字节 | `read_verified` 不查 catalog（`107-122`） | public 不 export Port；ingest 加 catalog fence | `NH4-T03`/`T04` |

S16 对齐：先 `require_business_token` 再碰 team 资源（`dependencies.py:109-110`）；失败审计 fail-closed；对象路径 sandbox 在 `object_root` 下。本 AP **不**把 upload 放到 operator-only 网，调用方是 business token（与 28 条现网一致）。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| `NH4-T01` | public upload→handle 且零 Item；DB 有 stored_object+pending ref | `spike`/`mega` 短途 e2e | `e2e` **L3** | `🆕` `tests/e2e/test_nh4_public_upload.py` | `NH4-01..03` → upload identity | `commit SHA + pytest node PASS + Q16/Q24 + UTC` |
| `NH4-T02` | 同 bytes replay/concurrency；异 size 冲突 | `soak`/`race` | **L2/L3** | `🆕` `tests/e2e/test_nh4_upload_replay_race.py` | `NH4-04` → 同 handle / typed conflict | `commit SHA + parallel PASS + T-O-383 + UTC` |
| `NH4-T03` | stat 字段/跨 team/无 raw | `短途` 契约/S | **L1/L3** | `🆕` `tests/unit/test_nh4_object_routes_contract.py` + e2e stat | `NH4-03/07/08` → public boundary | `commit SHA + route/auth PASS + Q16 + UTC` |
| `NH4-T04` | upload→ingest→retrieval | `mega` | **L3/L4** | `🆕` `tests/e2e/test_nh4_upload_then_ingest.py` | `NH4-05` → handoff | `commit SHA + handle/query PASS + T-O-385 + UTC` |
| `NH4-T05` | pending 与 GC 交错 | `spike` fault/race | **L2/F/R** | `🔱` `tests/unit/test_ns6_gc_toctou.py` + pending 交错 | `NH4-06` → GC safety | `commit SHA + restore/tombstone PASS + Q24 + UTC` |
| `NH4-T06` | TTL 未 ingest 回收 | `soak` | **L2** | `🆕` `tests/unit/test_nh4_upload_ttl_gc.py`（fake clock） | `NH4-06` → release+grace 可删 | `commit SHA + scanner PASS + T-O-404 + UTC` |
| `NH4-T07` | oversize/digest/path/MIME | `短途` security | **L1/L3** | `🆕` `tests/e2e/test_nh4_upload_security.py` | `NH4-08` → bounded security | `commit SHA + negative suite PASS + Q16 + UTC` |

#### `NH4-T01`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_nh4_public_upload.py::test_auth_upload_returns_handle_catalog_pending_zero_intake`；同文件强制 L2 node `::test_upload_stream_respects_object_cap_not_global_1mib` |
| 用途 | 证明 `NH4-01..03`；`FG-NH-10`（经 public route，非内部 promote）；零 S04 identity |
| 前置 | `create_app()` 默认组合根；`Settings.internal_token`；新建 Team `active`；**禁止** `container.storage.promote`；**禁止** `sqlite3.connect`（`FG-NH-12`）——断言经 `app.state.container.persistence.transaction()` |
| 步骤 | a) `POST /v1/teams` 建 team。b) `POST /v1/teams/{team}/objects:upload` Bearer + raw body（含 ≥1KiB 可识别 sentinel 字节）+ 可选 expected sha。c) 解析 JSON 闭集。d) 同一 UoW 查询 catalog/ref/intake 三表。e) `GET .../objects:stat?handle=` 字段一致 |
| 断言细节 | HTTP 201；`handle` 匹配 `^mkbobj:v1:{team}:{64hex}$`；`digest` = sha256(body)；`size_bytes=len(body)`；`disposition=pending`；keys 无 `path`/`filename`。DB：`mkb_stored_objects` live 1 行 digest/size 匹配；`mkb_object_references` live `purpose='upload_pending'` ≥1；`COUNT(*)` `mkb_intake_sources`=0、`mkb_intake_items`=0、`mkb_intake_revisions`=0 |
| 负例 | 无 token → 401；空 body → 422；catalog 事务失败不得 2xx（L2 可注入） |
| 跑法 | `uv run pytest tests/e2e/test_nh4_public_upload.py::test_auth_upload_returns_handle_catalog_pending_zero_intake tests/e2e/test_nh4_public_upload.py::test_upload_stream_respects_object_cap_not_global_1mib -q` |
| 层与来源 | L3；`🆕`；适用 `FG-NH-10`/`FG-NH-12` |

#### `NH4-T02`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_nh4_upload_replay_race.py::test_concurrent_same_team_digest_size_same_handle`；`::test_expected_digest_conflicting_size_typed_fail` |
| 用途 | `NH4-04`；`T-O-383/385` 上传幂等 |
| 前置 | 两线程/asyncio 同 app、同 token、同 body；PersistencePort 查 live unique |
| 步骤 | a) 并行双 `POST upload` 同字节。b) 收集 handle 与 HTTP 码（201/200 均可，禁止 5xx）。c) DB 查 live catalog count。d) 第二场景：expected=已有 digest 但 body 不同 size（或截断） |
| 断言细节 | 两响应 `handle` 字符串相等；`SELECT COUNT(*) FROM mkb_stored_objects WHERE tombstoned_at IS NULL AND team=? AND content_digest=? AND size_bytes=?` = 1。冲突场景 HTTP 409 或 422，错误码 ∈ `{OBJECT_INTEGRITY_DIGEST, OBJECT_INTEGRITY_COLLISION, ConflictError.code}`，live 行不被覆盖（digest 字节仍等于第一次 body） |
| 负例 | 跨 team 同 body → **不同** handle，且各 1 行；用 A handle 打 B stat → 403 |
| 跑法 | `uv run pytest tests/e2e/test_nh4_upload_replay_race.py -q` |
| 层与来源 | L2/L3；`🆕`；race 标签 |

#### `NH4-T03`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/unit/test_nh4_object_routes_contract.py::test_public_router_has_upload_stat_and_zero_raw_list_presign`；e2e `tests/e2e/test_nh4_public_upload.py::test_stat_closed_set_cross_team_403_unauth_401` |
| 用途 | `NH4-03/07/08` public boundary；`O-NH-04` |
| 前置 | 读 `api/public/routes.py` AST 或 `router.routes`；第二 team+token |
| 步骤 | a) 收集全部 public/internal 路由 path+method。b) 断言存在 upload 与 stat。c) 断言零匹配 `(raw, presign, objects 列表 GET bytes)`。d) HTTP stat 无 path。e) 跨 team 403。f) 无 Authorization 401 |
| 断言细节 | upload 路径包含 `objects:upload` 且 method POST；stat 为 GET 且非 `StreamingResponse` bytes。stat JSON 不得含 `/` 的文件系统 path、不得含 `filename`。跨 team：`error.code=OBJECT_AUTH_TEAM_MISMATCH` status=403。unauth：`SEC_TOKEN_MISSING` 或 `SEC_TOKEN_INVALID` status=401。generation-artifact GET 仍存在且 schema 无对象字节字段 |
| 负例 | 若 diff 增加 `FileResponse`/`StreamingResponse` 对象下载 → 本测试必须红 |
| 跑法 | `uv run pytest tests/unit/test_nh4_object_routes_contract.py tests/e2e/test_nh4_public_upload.py::test_stat_closed_set_cross_team_403_unauth_401 -q` |
| 层与来源 | L1 扫描 + L3 HTTP；`🆕` |

#### `NH4-T04`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_nh4_upload_then_ingest.py::test_upload_search_empty_then_independent_ingest_namespace_hit` |
| 用途 | `NH4-05`；`T-O-385` 两步法；`FG-NH-03/05/10` |
| 前置 | NH1-T03 namespace fixture（`namespace_key` 或 `namespace_uuid` 合法 Layer-A）；Team+token；**真实** ingest 文本/html local_object（不要 PDF/OCR 供给）。查询走 `POST /v1/teams/{t}/retrieval:search`。PersistencePort 断言 Item。禁止 monkeypatch `_http_fetcher`/`storage.promote` |
| 步骤 | a) public upload sentinel 文本。b) search 该 sentinel → hits=0。c) `POST /v1/teams/{t}/tasks` `intake.ingest` + `source_kind=local_object` + `logical_handle`。d) 轮询 Task 至 terminal（**不得**以 succeeded 当 PASS）。e) 再 search，断言 content/hit。f) DB：ingest 后 Item≥1；原 pending `released_at` 非空；业务 ref live |
| 断言细节 | 步骤 b：HTTP 2xx 且 hits 空或无该 digest。步骤 e：命中文档含 sentinel；响应含合法 namespace（`FG-NH-05`）。**不**断言 realm facet（见 §8.4）。upload 与 ingest 为两次 HTTP 事务 |
| 负例 | 仅 upload 就出现 Item → fail；search 省略 namespace → 422 `RETRIEVE_SCHEMA_NAMESPACE_REQUIRED` 不得改测试去删 namespace |
| 跑法 | `uv run pytest tests/e2e/test_nh4_upload_then_ingest.py::test_upload_search_empty_then_independent_ingest_namespace_hit -q` |
| 层与来源 | L3 + L4（无 facet）；`🆕`；消费 NH1-T03 |

#### `NH4-T05`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🔱 `tests/unit/test_ns6_gc_toctou.py::test_gc_restore_when_live_reference_arrives_during_quarantine` **沿用回归**；🆕 同文件 `test_gc_restore_when_upload_pending_arrives_during_quarantine`；补充 `test_collect_candidates_skips_live_upload_pending` |
| 用途 | `NH4-06`；Q24；RA09 `W-GC-INGEST` |
| 前置 | `_seed_orphan` + `ObjectGcService`；在 quarantine hook 内 INSERT `purpose=upload_pending` live ref（对照现 `process_io` 交错 `test_ns6_gc_toctou.py:41-56`） |
| 步骤 | a) 无 pending 的 orphan 仍可删（回归）。b) 有 pending 的对象 `collect_candidates` 为空或 delete → `LIVE_REFERENCE`。c) 无 ref 过 grace 进入 quarantine 后插入 pending → restore，`tombstoned_at IS NULL`，`read_verified` 成功 |
| 断言细节 | `result.disposition is ObjectGcDisposition.LIVE_REFERENCE`；catalog 未 tombstone；live ref count=1；字节与种子相等 |
| 负例 | 把 pending 当无主删除 → fail；硬 `unlink` 绕过 quarantine → 禁止 |
| 跑法 | `uv run pytest tests/unit/test_ns6_gc_toctou.py -q` |
| 层与来源 | L2/F/R；`🔱 fork` + 新断言 |

#### `NH4-T06`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/unit/test_nh4_upload_ttl_gc.py::test_ttl_without_ingest_releases_then_grace_tombstone`；`::test_staging_incomplete_never_catalogued_is_reaped` |
| 用途 | `NH4-06` TTL/staging；`T-O-404`；`R-F07` |
| 前置 | `ObjectGcService(..., clock=lambda: frozen)` + TTL scanner 同一 clock；短 `orphan_grace`/`ttl`（仍 &gt;0） |
| 步骤 | a) 服务层完成 catalog+pending（可用内部 upload service，不必 HTTP）。b) clock + ttl-1 → pending 仍 live，`scan_once` 不删。c) clock ≥ ttl → `released_at` 有值，字节仍在。d) clock ≥ ttl+grace → `DELETED` + delete proof + tombstone；`read_verified` 404。e) 另测：只 staging 半写、不 finalize → catalog=0，scanner 后 staging 文件消失 |
| 断言细节 | 步骤 b `collect_candidates` 不含该 uuid；步骤 c `released_at IS NOT NULL` 且 `tombstoned_at IS NULL`；步骤 d `mkb_object_delete_proofs` 1 行、`disposition=deleted`。staging 测：`objects/` 无对应 digest 文件 |
| 负例 | 0 grace 构造 → `ValueError`；TTL 未到就 tombstone → fail |
| 跑法 | `uv run pytest tests/unit/test_nh4_upload_ttl_gc.py -q` |
| 层与来源 | L2 soak（fake clock deterministic）；`🆕` |

#### `NH4-T07`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_nh4_upload_security.py::test_filename_path_traversal_rejected`；`::test_declared_mime_is_not_identity`；`::test_oversize_and_chunked_413`；`::test_digest_mismatch_422`；`::test_unauth_and_cross_team`；`::test_zero_presign_symbols_in_upload_surface` |
| 用途 | `NH4-08`；§7.3 威胁模型；OWASP 失败法 |
| 前置 | create_app；可把 `object_max_bytes` 降到较小值测 413；chunked 无 CL（对照 `tests/unit/test_ns6_phase5.py:101-127`） |
| 步骤 | a) `Content-Disposition: filename="../x"` 或 `..\\..\\windows`。b) `Content-Type: image/png` 上传实为 `text/plain` sentinel，断言 digest=明文 sha256、path 不含 `.png`。c) body = cap+1。d) expected 全 `0` 与真哈希不符。e) 无 token；他队 handle。f) `rg` 本 PR 新增文件无 `presign`/`r2.cloudflare` 实现 |
| 断言细节 | a) 422 `SEC_PATH_REJECTED`，`object_root` 无 `..` 段目录。b) 201/200 且 `media_type` 可为声明值，但 CAS 路径 `.../sha256/aa/bb/{digest}`。c) 413 `OBJECT_BUDGET_SIZE` 或 upload 专用码，**无** catalog 行。d) 422 `OBJECT_INTEGRITY_DIGEST`，无错误 digest 的 catalog。e) 401 / 403。f) 扫描 0 命中 |
| 负例 | 200 成功即失败；1MiB ASGI 帽误伤合法 &lt;object cap 的 upload（若 cap 测试设 8KiB，body=2KiB 必须 2xx） |
| 跑法 | `uv run pytest tests/e2e/test_nh4_upload_security.py -q` |
| 层与来源 | L1 扫描 + L3 HTTP；`🆕`；security 标签 |

### 8.2 复用台账（沿用 / fork 的既有用例明细）

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/unit/test_ns6_gc_toctou.py::test_gc_restore_when_live_reference_arrives_during_quarantine` | `🔱 fork` 保留 + 新 pending 用例 | + `upload_pending` 交错断言 | HEAD 实测存在，RA06 记 10 passed（GC 两文件合计） |
| `tests/unit/test_object_gc.py` 全文件 | `♻️ 沿用` 回归 | 0 或仅适配候选 SQL（若扩 unowned-at 谓词，必须保持 orphan 种子行为） | 已存在 |
| `tests/unit/test_ns6_phase5.py::test_chunked_body_without_content_length_is_capped` | `♻️ 沿用` 非 upload 1MiB 帽 | 0 改动 | 已存在；证明全局帽仍在 |
| `tests/e2e/test_source_capability_paths.py:77-82` | `⛔` 反例 | 执行期若 catalog fence 落地，该内部 promote 路径须改为 public upload 或同 UoW catalog；**不得**把它继续当 NH4 DoD | 现用内部 promote+monkeypatch |
| NH1-T03 namespace fixture | `♻️ 沿用` 消费 | T04 search 必须带 namespace | 依赖 NH1；`NH1-T03` 未 GO ⇒ 本 AP 保持 `draft`/`未观察`，**不得**标本 AP 完成。禁止把 T04 L4 标 `deferred` 当缓解 |

### 8.3 分层与跑法（各类型在哪跑、何时跑）

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `uv run pytest tests/unit/test_nh4_object_routes_contract.py tests/unit/test_nh4_upload_ttl_gc.py tests/unit/test_object_gc.py tests/unit/test_ns6_gc_toctou.py -q` | L1/L2 | 每 PR |
| spike | `uv run pytest tests/e2e/test_nh4_public_upload.py tests/e2e/test_nh4_upload_security.py -q` | L3 | 每 Phase 3/5 收口 |
| mega | `uv run pytest tests/e2e/test_nh4_upload_then_ingest.py tests/e2e/test_nh4_upload_replay_race.py -q` | L3/L4 | **本 AP 收口** |
| soak | fake clock TTL×N；并发双传 deterministic | L2/L3 | **退出硬闸**（T02/T06） |

服从 `T-O-406`：不得用 T03 L1 扫描代替 T01 L3；不得用 T06 L2 代替 T04 L4。

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖 **realm/type/channel facet 检索**（理由：属 `S-NH-F5` / AP-NH5）→ 交 `AP-NH5`/`AP-NH7`；T04 L4 **只**断言 namespace+content hit，**不假装覆盖** facet。
- 不覆盖 **PDF/OCR/Vision/browser 真供给**（理由：属 NH6）→ 交 `AP-NH6`；T04 用 local 文本/html 即可证明 handoff。
- 不覆盖 **10+3 vertical 全矩阵**（理由：属 NH7）→ 交 `AP-NH7`；本 AP 只保证 local_object **字节入口**存在。
- 不覆盖 **七意图非法格 / exact-clean / old-pin** → `AP-NH8`。
- 不覆盖 **campaign capstone I/J 全量 crash/compat 包** → `AP-NH9` 消费本 AP 证据，不在本 AP 重跑 82 work IDs。
- 不覆盖 **raw 导出授权/审计/流量帽** → `O-NH-04` 未来 reopen。
- **NH1-T03 未 GO ⇒ 本 AP 保持 `draft`/`未观察`，不得标本 AP 完成**（DAG：NH4 在 NH1 之后）。T04 步骤保持 namespaced search；禁止改成只轮询 Task terminal；禁止用无 namespace 的 search 假绿（`FG-NH-05`）。禁止把 T04 L4 标 `deferred` 当作风险缓解。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ PASS 必带四元组：`commit SHA + pytest node PASS + Truth/Q + UTC`。
- 本 AP 适用 FG：`FG-NH-01`（T04 成功路径无 monkeypatch）、`FG-NH-03`（search 非 Task succeeded）、`FG-NH-05`（namespace）、`FG-NH-10`（public route 非内部 promote）、`FG-NH-12`（PersistencePort 非 sqlite3 直读）、`FG-NH-13`（不降层）。
- `degraded` 必带机器可读 reason；pre-existing 失败必带 git 证据。
- 安全项必须含 §7.3 攻击向量（T07），不得只测 happy-path。
- 计数 ≠ 价值：28+2 条路由存在 ≠ upload 成功；GC unit 10 passed ≠ pending 契约。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| `R-F07` upload 误删/泄漏 | 无 pending 或 staging 无 scanner | `high` | `T-O-404` + T05/T06 interleavings；staging+uncatalogued scanner |
| ASGI 全缓冲 vs 对象帽 | `app.py:536-556` 会在 Port 之前 OOM/413 | `high` | Phase 1 强制分路径流式；T01/T07 |
| `M-NH-05` CHECK 重建 | SQLite 重建 `mkb_object_references` 丢数据/索引 | `high` | forward-only；evidence `migrations/` before/after；失败 STOP |
| 候选 SQL 改 created_at | 误删真 orphan 或误收 pending | `high` | 双时钟谓词；全量 `test_object_gc.py` 回归 |
| NH1 未 GO | 并行窗本应在 `stop-or-go.md=GO` 后 | `medium` | DAG：NH1 fail → STOP；不静默继续标 NH4 executed；T03 不替代 GO |
| NH1-T03 / 检索 namespace | T04 L4 依赖 | `medium` | NH1-T03 未 GO ⇒ 本 AP 不得收口；禁止删 namespace；禁止 T04 L4 deferred |
| NH6 供给 | PDF 真文件非本 AP | `low` | T04 用文本；local PDF 格交 NH7 |
| handle digest vs S13 uuid | `NH-RA06-B07` | `low`（本 AP OOS） | 沿用 HEAD digest handle 以满足 `T-O-385` replay |
| 假绿 `FG-NH-10` | 内部 promote 冒充 | `high` | T01 只走 HTTP；代码审禁 test 调 Port 当 L3 |

### 9.2 约束与前提

- **技术前提**：HEAD `1221aa1` S13 CAS/GC 内核保持；`BusinessToken` 现网；Turso/sqlite PersistencePort；purpose 闭集扩展须 DDL+Literal 同步。
- **运行时前提**：`object_max_bytes` 默认 256MiB；`object_gc_grace_seconds` 默认 86400 且 ge=1；新增 `object_upload_pending_ttl_seconds`（建议默认 86400，ge=1）、`object_staging_ttl_seconds`（建议默认 3600，ge=1）。
- **组织协作前提**：`stop-or-go.md=GO` 后开工本并行窗；不重开 Q16/Q24。`NH1-T03` 不替代 GO。
- **上线 / 合并前提**：`M-NH-05` 先于或同 PR 于 public 路由；T01–T07 规定最低层 PASS；无 raw GET。

### 9.3 文档同步要求

- 需要同步更新的设计文档：S13 purpose 闭集登记（执行期 calibration，不在本 AP 改 baseline 除非执行 PR 明确）；public API 说明（README 现「无公共上传端点」句，执行后改写）
- 需要同步更新的说明文档 / README：`README.md` local_object 前置条件（今日 `:211` 叙事）
- 需要同步更新的测试说明：本 AP §8 + evidence pack `tests.txt`

### 9.4 完成后的预期状态

1. 调用方可用 Bearer 向 `/v1/teams/{team}/objects:upload` 写入有界字节，获得稳定 handle；DB 有 catalog+`upload_pending`，无 Intake 身份。
2. `objects:stat` 可观察 pending/ingested/expired/tombstoned；无 path/filename；跨 team 403；无 raw GET。
3. 同 team 同 digest+size replay 同一 handle；随后独立 ingest 才可 namespace 检索命中。
4. pending 不被 GC 删；TTL/cancel + grace 后可 tombstone；quarantine 窗口新 ref restore。
5. evidence pack 于 `docs/evidence/new-harvest/AP-NH4/` 待执行回填（本文不伪造 SHA）。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

### 10.1 收口硬闸

所有台账 C 项必须 **PASS 且四元组证据齐全**（DoD：`NH4-T01..T07` 全 PASS；`FG-NH-10`/public route scan 通过）：

1. **upload identity**：commit 后同 bytes 同 handle；upload 事务内 Item/Source/Revision 计数=0；存在 live catalog ∧ live `upload_pending`（由 `NH4-T01`/`NH4-T02` 证明）
2. **public boundary**：upload/stat 存在；raw/list/presign=0；跨 team 403；stat 无 path/filename；未鉴权 401（由 `NH4-T03` 证明）
3. **ingest handoff**：upload-only `retrieval:search` 空；独立 ingest 后 namespace+content 命中；两 UoW 分离（由 `NH4-T04` 证明）
4. **GC safety**：pending 存活；release+grace 可删；quarantine 新 ref restore（由 `NH4-T05`/`NH4-T06` 证明）
5. **bounded security**：cap/integrity/auth/path/MIME/presign 全部 typed fail（由 `NH4-T07` 证明）

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS 标准（可判定谓词） | PASS 证据（四元组）| 状态 |
|----------|--------|---------|-------------------------|---------------------|------|
| upload identity | `NH4-01..04` | `NH4-T01`/`NH4-T02` | 同 body 两次（含并发）`handle` 相等；`mkb_stored_objects` live 行 digest/size 匹配；`mkb_object_references.purpose='upload_pending' AND released_at IS NULL` 存在；`mkb_intake_sources`/`mkb_intake_items`/`mkb_intake_revisions` 在 upload 提交后计数增量=0 | `commit SHA + pytest node PASS + Q16/Q24/T-O-385 + UTC` | `未观察` |
| public boundary | `NH4-03/07/08` | `NH4-T03` | router 含 upload+stat；raw/list/presign 扫描=0；stat JSON 无 path/filename；跨 team 403 `OBJECT_AUTH_TEAM_MISMATCH`；无 token 401 | `commit SHA + route/auth PASS + Q16 + UTC` | `未观察` |
| ingest handoff | `NH4-05` | `NH4-T04` | upload 后 search hits 不含该 sentinel；独立 Task ingest 后 search 含 sentinel；pending 已 release；业务 ref live；禁止内部 promote | `commit SHA + handle/query PASS + T-O-385 + UTC` | `未观察` |
| GC safety | `NH4-06` | `NH4-T05`/`NH4-T06` | live pending 时 `collect_candidates` 不含该对象；TTL 后 `released_at` 非空且未 tombstone；grace 后 proof+tombstone；quarantine 中新 ref → `LIVE_REFERENCE` 且字节 restore | `commit SHA + restore/tombstone/scanner PASS + Q24 + UTC` | `未观察` |
| bounded security | `NH4-01/08` | `NH4-T07` | `../` → 422；假 MIME 不改 digest 路径；oversize/chunked → 413 无 catalog；digest mismatch → 422；零 presign 符号 | `commit SHA + negative suite PASS + Q16 + UTC` | `未观察` |

**谓词备忘（台账 D 逐行展开）**：

- upload identity：`commit 后同 bytes 同 handle；upload 不造 S04 identity` — 即 HTTP+DB snapshot 同时成立，而非只 assert 函数返回值。
- public boundary：`upload/stat 存在 ∧ raw/list/presign=0 ∧ 跨 team 403`。
- ingest handoff：`upload 单独检索空 ∧ 独立 ingest 后命中`。
- GC safety：`pending 不删 ∧ release+grace 可删 ∧ new ref restore`。
- bounded security：`cap/integrity/auth/path 全部 typed fail`。

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | public auth upload+stat 可用；handle 仅在 catalog+pending commit 后出现；无 raw GET；ingest 两步法；GC 认 pending |
| 测试 | §8 `NH4-T01..T07` 全 PASS（退出硬闸项四元组齐全）；最低层不低于台账 C |
| 文档 | 本 AP 仍为 draft 直至执行日志回填；evidence pack 目录存在且文件名如下（内容由执行产生） |
| 风险收敛 | `R-F07` 有 T05/T06 证明；`FG-NH-10` 扫描通过 |
| 可交付性 | NH7 local_object 格可依赖 public handle；不把内部 promote 留给调用方 |

**evidence pack 目录**（final §9.3；本 AP 只规定文件名与内容，不伪造已产生的 SHA）：`docs/evidence/new-harvest/AP-NH4/`

| 文件 | 内容 |
|------|------|
| `manifest.json` | commit、Truth/Q（Q5/Q16/Q24）、work `NH4-01..08`、test `NH4-T01..07`、UTC |
| `tests.txt` | 上表 pytest node、exit code、duration、environment |
| `queries/` | upload/stat HTTP 响应；catalog/ref/intake COUNT SQL 结果；T04 search before/after |
| `migrations/` | `018_nh4_upload_pending.sql` before/after schema、legacy 8 值行仍可读、forward-only proof |
| `security/` | T07 负例矩阵；路由扫描；无 presign；适用 pin 声明 |
| `closure.md` | 台账 D 五目标 PASS/FAIL 与 NOT-success 扫描 |

### 10.4 NOT-成功识别

> 任一退出硬闸测试 `degraded / 未观察` ⇒ **不得标 `executed`**。

下列均**不算**本 AP 完成（final §7.4 NOT-成功 + 本 AP 特有假绿）：

1. **internal `promote()`** 返回 ObjectStat
2. **Task inline staging** 当 public upload（`task_create.py` / inline e2e）
3. **catalog 无 live ref**
4. **raw GET** 或 list/presign/浏览器直读
5. **grace 赌竞态**（无 pending hold，靠 24h 窗口「大概够 ingest」）
6. **把 MIME 当权威**（unique/path/身份）
7. `FG-NH-10`：测试里 `container.storage.promote` 冒充 L3
8. Task `succeeded` / `publication_ready` 当可检索（`FG-NH-03/04`）
9. 无 namespace 的 search（`FG-NH-05`）
10. sqlite3 直读当 DB 证据（`FG-NH-12`）
11. 用 L1 路由计数代替 L3 上传（`FG-NH-13`/`T-O-406`）
12. 抬全局 `max_request_bytes` 冒充有界对象上传
13. monkeypatch 供给当 T04 成功（`FG-NH-01`）
14. 空/半写 staging 当成功；503 当通道 DoD

---

## 11. 执行日志回填（仅 `executed` 状态使用）

> 文档状态为 `draft`，非 `executed`。本节按模板占位；执行完成后改用 `respond-execution-log` 厚回填。residual 交后继 charter，不回填本阶段。

- **实际执行摘要**：尚未执行。
- **Phase 偏差**（逐条带分类）：尚未执行。
- **阻塞与处理**：尚未执行。
- **测试发现**（含全绿计数 + 新暴露事实）：尚未执行。
- **后续 handoff**：执行后交接 NH7 local_object 格与 NH9 capstone B/I 的 upload/GC 证据。

---

## 附录 · 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| `v0.1` | `2026-08-29` | Grok workflow | 由 final §7 派生 |
| `v0.2` | `2026-08-29` | Grok fix-fleet | 吸收已核实 review：删除 T04 L4 `deferred` 缓解；NH1-T03 未 GO 则本 AP 不得收口；`NH4-H04` 补全 `src/persistence/migrations/` 前缀 |
| `v0.3` | `2026-08-29` | Grok parent | 独立复核：补模板 H1；T01 跑法纳入强制 L2 cap node，去掉「可放」 |
| `v0.4` | `2026-08-29` | Grok recon-fix | 头部/Phase 1 开工闸改为 `stop-or-go.md=GO`；`NH1-T03` 仅 T04 夹具，不替代 GO |
