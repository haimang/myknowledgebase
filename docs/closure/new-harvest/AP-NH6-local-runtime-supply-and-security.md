# [AP-NH6 / Local runtime supply and security] Closure

> 阶段: `new-harvest/AP-NH6 — isolated parser / browser dual-cap / S11 multimodal / readiness / SBOM`
> 范围: `NH6-01..10 / NH6-T01..T10`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-08-30` · 作者: `Grok`
> 关联 charter: `docs/eval/new-harvest/final-execution-plan.md`
> 关联 design: `docs/eval/new-harvest/pre-charter-qna.md`
> 关联 action-plan: `docs/plan/new-harvest/AP-NH6-local-runtime-supply-and-security.md`
> 关联 evidence: `docs/evidence/new-harvest/AP-NH6/`
> 关联 review: `inline §2–§3`

---

## 0. 一句话 verdict

> NH6 已把 parse/render/print/确定性 OCR/S11 multimodal 接到默认可部署供给：无网 parser、S16 prefetch browser 双能力、具名闸、正负 readiness 与 SBOM；T01–T10 全绿。10+3 live-to-query、七 intent 与 campaign mega 按 DAG 递交 NH7/NH8/NH9。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. 本 AP 无 L4；四通道可检索仍属 AP-NH7。T03/T04 的 DOM/`%PDF-` 不得顶 NH7-T05/T06。
> 2. 生产完整 `/ready=200` 需 `runtime_supply_readiness_required=true` 且 multimodal endpoint 在场；默认离线 profile 仍用 BASE 九项以免假绿掩盖缺供给。
> 3. 全仓 5 个 namespace/rebuild 失败仍为 NH8 红债；S16 签收栏存在且未伪造签名。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| `NH6-01` identities | ✅ closed / verified | `63c4398` + T09/T10 identity/readiness keys PASS + Q13/Q19 + `2026-08-30T00:01:17Z` |
| `NH6-02` PDF parser | ✅ closed / verified | `63c4398` + T01/T02 PASS + Q19/T-O-378 + UTC |
| `NH6-03` render | ✅ closed / verified | `63c4398` + T03/T05 PASS + Q23/T-O-399 + UTC |
| `NH6-04` print | ✅ closed / verified | `63c4398` + T04/T05 PASS + `%PDF-` + Latin ToUnicode + Q23 + UTC |
| `NH6-05` multimodal request | ✅ closed / verified | `63c4398` + T06 PASS + Q13 + UTC |
| `NH6-06` OCR/Vision bindings | ✅ closed / verified | `63c4398` + T06/T07 PASS + T-O-386/378 + UTC |
| `NH6-07` gates | ✅ closed / verified | `63c4398` + T08 zero-downstream PASS + Q13 + UTC |
| `NH6-08` readiness | ✅ closed / verified | `63c4398` + T09 positive/negative/models-list PASS + Q19 + UTC |
| `NH6-09` SBOM | ✅ closed / verified | `63c4398` + T10 inventory EXIT0 + Q19 + UTC |
| `NH6-10` default root | ✅ closed / verified | `63c4398` + T03/T04/T06/T09 no-patch PASS + Q19 + UTC |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| NH6 hard-gate suite | `tests.txt` command | `45 passed` | T01–T10 L1/L2/L3 |
| Readiness | `queries/readiness-positive-negative.json` | 正 200；缺 binary 503；models-list 不足 | T09 |
| Backpressure | `queries/gate-metrics.json` | `INFERENCE_BACKPRESSURE`；下游调用不增 | T08 |
| Isolation/S16 | `security/isolation-parser-browser.md` | 无网 parser；每跳 egress；无 `--no-sandbox` | T02/T05 |
| SBOM | `security/sbom-inventory.json` | 五能力 pin/license/CVE；无 waiver | T10 |
| Static review | `ruff check`; `git diff --check` | PASS | changed production/tests |
| Full repository diagnostic | `pytest -q --tb=line` | `794 passed / 5 successor-owned failed / 799 collected` | repository regression |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| PDF supply | 真 ToUnicode/压缩；absent/encrypted；恶意不杀 API | T01/T02 | ✅ PASS |
| browser supply | DOM 与 `%PDF-` 各自真实；render≠print | T03/T04 | ✅ PASS |
| isolation policy | non-root；无 `--no-sandbox`；每跳 egress | T05 | ✅ PASS |
| model supply | bytes/handle+PromptRef；空/错 typed；CLI 拒 binary | T06/T07 | ✅ PASS |
| budget/readiness | 满载零调用；组件==在场；名单不足 | T08/T09 | ✅ PASS |
| supply trust | pin/license/SBOM/CVE 或具名 waiver | T10 | ✅ PASS |
| default wiring | `create_app()` 无 patch | T03/T04/T06/T09 | ✅ PASS |
| S16 签收栏 | 文件存在且未预填假签 | `s16-egress-browser-review.md` | ✅ PASS（文档门） |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| 10+3 live-to-retrieval / namespace query | C | supply ready; no L4 | AP-NH7 | NH7 |
| Seven intents / exact-clean bypass | C | unchanged | AP-NH8 | NH8 |
| Index/reactivate namespace + rebuild STRUCTURE_PROFILE_INVALID | C | five repository failures | AP-NH8 | NH8 |
| Campaign mega / crash windows / NH9-T10 🔱 | C | security file nodes exist | AP-NH9 | NH9 |
| S16 owner/reviewer signature | B | checklist present, unsigned | owner/reviewer UTC sign | owner |
| Production `--no-sandbox` / cloud OCR / CF Browser Rendering | A | prohibited | reopen Q19 / T-O-377 | owner |
| Raw GET / fifth kind / existing-object upgrade | A | OOS | future owner-gate | owner |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态 | ✅ hard gates=`verified`; S16 signature=`deferred` document gate |
| ✅ 证据为四元组 | ✅ implementation commit + named pytest/query + Truth + UTC |
| scope diff 守卫 | ✅ supply/runtime/inference/intake wiring, tests, SBOM; no NH7 query or NH8 intent rewrite |
| deferred 已三分类 | ✅ A/B/C with owner/trigger |
| owner-test | N/A；T03/T04 不冒充 NH7 live-to-query |

---

## 6. Handoff / 下阶段 entry-gate 预核对

| 入口条件 | 状态 | 备注 |
|----------|------|------|
| NH1 GO | ✅ | unchanged |
| parser/browser/OCR ports in `create_app()` | ✅ | missing binary → typed 503 + component false |
| S11 multimodal request | ✅ | PromptRef + media digest/handle/bytes |
| readiness keys 1:1 with caps | ✅ | T09 |
| SBOM inventory | ✅ | T10 |
| L4 query | ⏸ | NH7 |

**下阶段 kickoff checklist**：

- [x] 引用本 closure 与 `sbom-inventory.json`
- [ ] NH7 每格 namespaced search；禁止 monkeypatch success
- [ ] NH7 不得把 T09 503 写成通道 DoD
- [ ] NH8 消化五个 namespace/rebuild 失败并关 T08-B
- [ ] NH9 🔱 `tests/e2e/test_new_harvest_runtime_security.py`

---

## 7. Cross-cut 不变量（0-drift 确认）

| 不变量 | 状态 | 证据 |
|--------|------|------|
| 库名不进 Truth | ✅ 保持 | identities registry 无 playwright/pypdf/tesseract/poppler |
| 无第四无名 DispatchPool | ✅ 保持 | `DispatchPool` 仍三值；OCR/browser unpooled |
| GPL 不链入主进程 | ✅ 保持 | pyproject 七依赖不变；poppler subprocess |
| CLI 拒 binary | ✅ 保持 | T06 `CLEAN_MEDIA_UNSUPPORTED` |
| 生产无 `--no-sandbox` | ✅ 保持 | T05 argv scan |
| parser 无网 / browser 受控 egress 分账 | ✅ 保持 | T02 vs T05 |
| `payload_extra` 禁 media 偷运 | ✅ 保持 | T06 |
| 无 L4 宣称 | ✅ 保持 | 本 AP 测试无 retrieval search DoD |
