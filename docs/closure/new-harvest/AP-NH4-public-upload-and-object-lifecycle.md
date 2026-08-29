# [AP-NH4 / Public upload and object lifecycle] Closure

> 阶段: `new-harvest/AP-NH4 — authenticated upload/stat + pending/GC lifecycle`
> 范围: `NH4-01..08 / NH4-T01..T07`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-08-30` · 作者: `Codex`
> 关联 charter: `docs/eval/new-harvest/final-execution-plan.md`
> 关联 design: `docs/eval/new-harvest/pre-charter-qna.md`
> 关联 action-plan: `docs/plan/new-harvest/AP-NH4-public-upload-and-object-lifecycle.md`
> 关联 evidence: `docs/evidence/new-harvest/AP-NH4/`
> 关联 review: `inline §2–§3`

---

## 0. 一句话 verdict

> NH4 已交付受鉴权 streaming upload/stat/cancel、catalog+pending 原子成功定义、两步 local_object ingest、幂等 race 与 TTL/grace/quarantine 安全闭环，T01–T07 全绿且 public raw read 保持为零；facet 完整性与 10+3 local 格按 DAG 递交 NH5/NH7。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. NH4-T04 证明 namespace+content 命中，不声明 realm/type/channel facet；该层归 AP-NH5/NH7。
> 2. public raw export/list/presign 仍明确 OOS；本 closure 不授予下载能力。
> 3. 全仓仍有六个已登记的 namespace/rebuild/realestate 后继失败，与 NH4 hard gates 无交集。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| `NH4-01` bounded write | ✅ closed / verified | `7359a96` + NH4-T01/T07 PASS + Q24/T-O-404 + `2026-08-29T20:37:37Z` |
| `NH4-02` catalog+pending | ✅ closed / verified | `7359a96` + UoW rollback/migration PASS + Q24/T-O-404 + UTC |
| `NH4-03/07` public boundary | ✅ closed / verified | `7359a96` + upload/stat/cancel + zero raw scan + Q16/T-O-396 + UTC |
| `NH4-04` replay/conflict | ✅ closed / verified | `7359a96` + concurrent 201/200 one catalog + T-O-383/385 + UTC |
| `NH4-05` ingest handoff | ✅ closed / verified | `7359a96` + namespaced search before/after + Q5/T-O-385 + UTC |
| `NH4-06` GC lifecycle | ✅ closed / verified | `7359a96` + pending/quarantine/TTL/staging PASS + Q24 + UTC |
| `NH4-08` security | ✅ closed / verified | `7359a96` + negative matrix PASS + Q16/T-O-377/396 + UTC |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| Frozen + owned regressions | `tests.txt` NH4 command | `42 passed` | L1/L2/L3/L4/F/R |
| Public identity | `queries/public-upload.json` | 201 + catalog/pending + zero Intake | HTTP/UoW |
| Replay/race | `test_nh4_upload_replay_race.py` | one 201, one 200, one live row | L3/R |
| Ingest handoff | `queries/upload-ingest-handoff.json` | before false; after true; pending→business | L3/L4 |
| GC lifecycle | `queries/gc-lifecycle.json` | TTL release, grace delete, proof, restore | L2/F/R |
| Security/public fence | `security/upload-negative-matrix.md` | all typed failures; raw/presign zero | L1/L3/S |
| Full repository diagnostic | `pytest -q --tb=short` | `705 passed / 6 successor-owned failed / 711 collected` | repository regression |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| upload identity | commit 后同 bytes 同 handle；零 S04 identity | T01/T02 + DB query | ✅ PASS |
| catalog+pending | 同 UoW；fault rollback；legacy migration stable | T01 + M-NH-05 | ✅ PASS |
| public boundary | upload/stat 存在；raw/list/presign=0；401/403 | T03/T07 | ✅ PASS |
| ingest handoff | upload-only 不命中；独立 ingest 后 namespaced hit | T04 | ✅ PASS |
| GC safety | pending 不删；release 后重新起 grace；new ref restore | T05/T06 | ✅ PASS |
| bounded security | cap/digest/path/MIME/auth 全 typed fail | T07 | ✅ PASS |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| Semantic facet query | C | namespace/content only | AP-NH5 then NH7 local vertical | NH5/NH7 |
| PDF/doc/OCR local lanes | C | bytes entry ready | AP-NH6/NH7 | NH6/NH7 |
| Closed-set upload/GC mega replay | C | per-AP evidence ready | AP-NH9 capstone | NH9 |
| Raw object export/download | A | prohibited/OOS | future owner-gate only | owner |
| Remote object adapter/R2/presign | A | prohibited/OOS | new Truth required | owner |
| Six repository failures | C | unchanged successor debt | AP-NH5/AP-NH8 | NH5/NH8 |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态 | ✅ `verified`; downstream work=`deferred` |
| ✅ 证据为四元组 | ✅ implementation commit + named HTTP/query/test + Truth + UTC |
| scope diff 守卫 | ✅ upload/storage/GC contracts, migration, docs and focused tests only |
| deferred 已三分类 | ✅ A/C，均有 owner/trigger |
| owner-test | N/A；T04 L4 不冒充 facet mega |

---

## 6. Handoff / 下阶段 entry-gate 预核对

| 入口条件 | 状态 | 备注 |
|----------|------|------|
| NH4-T01..T07 | ✅ | 42 owned/related nodes PASS |
| public local_object handle | ✅ | catalog+pending before exposure |
| acceptance ref conversion | ✅ | pending released + business live |
| namespace/content L4 | ✅ | no internal promote/monkeypatch |
| GC pending/TTL/quarantine | ✅ | deterministic fake clock + race |

**下阶段 kickoff checklist**：

- [x] 引用本 closure、M-NH-05 与 three query artifacts
- [ ] NH5 独立交付 facets；不要把 NH4 content hit当语义完成
- [ ] NH7 local lane 必须经 public handle，不回退内部 promote
- [ ] NH9 重放 concurrent upload/GC windows，不第一次实现功能

---

## 7. Cross-cut 不变量（0-drift 确认）

| 不变量 | 状态 | 证据 |
|--------|------|------|
| upload 不造 Item/Source/Revision | ✅ 保持 | public DB snapshot all zero |
| bytes identity = Team + SHA-256 + size | ✅ 保持 | race/mime tests |
| usable handle requires catalog+pending | ✅ 保持 | UoW fault + M-NH-05 |
| no raw public read/list/presign | ✅ 保持 | route/source scan |
| local_object requires catalog/live ref | ✅ 保持 | internal promote 409 |
| reference release starts grace | ✅ 保持 | unowned-at query + TTL matrix |
| L1–L4不可互换 | ✅ 保持 | T01/T03 L3 and T04 L4 executed |
