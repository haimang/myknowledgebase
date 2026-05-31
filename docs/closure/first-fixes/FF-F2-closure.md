# [FF-F2 / 连接与装配可靠性] Closure

> 阶段: `first-fixes/FF-F2 — 连接与装配可靠性（Connection lifecycle + API assembly）`
> 范围: `F2-01..F2-04（P1-01..P3-02，单 sub-phase；与 F1 并行）`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-05-31` · 作者: `Claude Opus 4.8 (1M context)`
> 关联 charter: `docs/design/first-fixes/initial-planning-by-opus.md`
> 关联 design: `docs/design/first-fixes/owner-gated-qna.md（[Q7] test-first）`
> 关联 action-plan: `docs/action-plan/first-fixes/FF-F2-conn-wiring.md`
> 关联 evidence: `inline §2 + action-plan §11 执行日志`
> 关联 review: `docs/eval/first-code-review-plan/part-cr-2.md / part-cr-5.md / part-cr-8.md`
> 关联 commit: `ed7b609`（fix(F2): 连接生命周期 + API 装配）

---

## 0. 一句话 verdict

> F2 收口：API/CLI 连接归生命周期管理（generator yield+finally close / CLI contextmanager），API 补 lifespan(迁移+自检 fail-loud)/CORS/全局异常映射(ValueError·SmindError→4xx)/真 healthz 探测；先红后绿成立（pre-fix 4 failed → post-fix 4 passed），全量 **59 passed in 4.20s**；close-type = closed-with-explicit-deferrals（restart→409 端到端依赖 FF-F3，标 handoff）。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. `restart→409 端到端验证依赖 FF-F3 精细 restart 语义（未完成）→ FF-F3；本轮 401/404 已真实验证，409 映射逻辑由 unit 覆盖`
> 2. `CORS 源生产收紧为技术债（本轮保守默认 *）`

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + test + run-time） |
|------|------|----------------------------------------|
| F2-01 API 连接 generator 依赖 | ✅ | `ed7b609` + `test_conn_lifecycle.py::test_no_connection_leak_over_many_requests PASSED` + `2026-05-31`；grep `yield conn`=2；先红：HEAD return 型 → 60 请求泄漏 FAIL |
| F2-02 CLI 连接 contextlib | ✅ | `ed7b609` + `test_cli_conn_close.py PASSED` + `2026-05-31` |
| F2-03 lifespan/CORS/异常映射/真 healthz | ✅ | `ed7b609` + `test_app_lifespan / test_cors / test_error_mapping / test_error_mapping_realapp / test_healthz_probe / unit/test_app_support PASSED` + `2026-05-31`；grep `exception_handler`=2 |
| F2-04 先红后绿测试 | ✅ | `ed7b609` + 全量 `59 passed in 4.20s`；先红后绿：pre-fix `4 failed` → post-fix `4 passed` |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| 全量回归 | `python3 -m pytest tests/` | `59 passed in 4.20s`（p1-p7 + smoke + F2 新增） | 全仓 |
| 先红后绿（文件备份法） | `cp main.py/deps.py 备份; git show HEAD:... > 还原 pre-fix; pytest realapp+conn_lifecycle+error_mapping` → `4 failed`；还原 F2 版 → `4 passed` | RED→GREEN 成立 | F2-01 / G-CR5-05 |
| generator 依赖 | `grep -c "yield conn" apps/api/src/smind_api/deps.py` | `2`（core+vec） | F2-01 |
| 异常 handler 注册（真 app） | `test_error_mapping_realapp::test_real_create_app_registers_business_exception_handlers` + `grep -c exception_handler main.py` | PASS；`2` | F2-03 |
| healthz 探测连接即关 | `unit/test_app_support::test_probe_connections_are_closed`（opened==closed） | PASS | F2-03 |
| F1 未回归 | F1 用例纳入全量（test_time_ssot 8 + p1_kernel_closure） | 全绿 | 回归护栏 |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| 请求级连接无泄漏 | T01 绿 + 先红 | 60 次请求净 open 不增长；HEAD return 型 FAIL | ✅ PASS |
| API 装配完整 | lifespan/CORS/真 healthz 绿 | 启动迁移+自检 fail-loud；CORS 头；healthz 200/503+reason | ✅ PASS |
| 业务异常映射 4xx | T05 + realapp 绿 + 先红 | invalid creds→401 / not found→404 / 未识别→400；真 app 注册 handler；pre-fix 无 handler FAIL | ✅ PASS |
| restart→409 端到端 | — | restart 精细语义归 FF-F3，未就绪 | ⏸ PENDING（handoff FF-F3；409 映射逻辑已 unit 覆盖） |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| `restart→409 端到端映射` | C (handoff) | 401/404 已验；409 映射 unit 覆盖；端到端依赖 restart 端点 | FF-F3 完成后补端到端 | F3 执行者 |
| `CORS 源生产收紧` | B (主动 defer) | 本轮保守默认 `*` | 生产部署前 | 后继/运维 |
| `smind_common.errors 领域异常体系补全` | A (charter OOS) | 现用 ValueError/SmindError 映射 | F6 业务面稳定后统一 | 后继 |
| `numpy/bs4/lxml/uvicorn 等离线缺失` | C (handoff) | F2 不依赖；F5/F6 需适配（stdlib/纯 Python） | FF-F5/F6 | 各阶段执行者 |
| `FF-F1 closure "fastapi 缺失" 推测需更正` | C (handoff) | F2 已证 fastapi 可用、全量 59 passed | FF-F7 统一回链更正 | F7 执行者 |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred）| ✅ —— F2-01..04 全部 `verified`（commit `ed7b609` + 命名测试 + run-time + 先红后绿 + grep）。restart→409 端到端 `deferred`（handoff FF-F3）。 |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | ✅ —— 见 §1/§2 |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改）| ✅ —— 改动限于 deps.py/main.py/cli main.py/app_support.py(新) + p2 6 测试 + realapp 测试 + unit/test_app_support + smoke healthz 断言更新 + 本 closure + AP §11；未触 engine.py/workflow_core |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ —— 见 §4（A×1 / B×1 / C×3） |
| owner-test 项未经 owner 复测的标 ⏸ PENDING（无「我修了」式宣称）| N/A —— F2 无 owner-test/live gate |

> 诚实附注：
> 1. **环境修正**：fastapi 在本环境真实可用（系统 dist-packages：fastapi 0.136.3 / pydantic 2 / pydantic_settings / starlette / httpx），F2 的 p2-p7 + 新增测试全部真实运行（59 passed）。FF-F1 closure 中 "fastapi 缺失致 p2-p7 不可运行" 的推测**不成立**，记入 §4 待 FF-F7 统一更正。真正离线缺失仅 numpy/uvicorn/bs4/lxml/requests/sentence_transformers/sqlite_vec。
> 2. **error_mapping 先红严谨性**：原 `test_error_mapping.py` 自建最小 app，对真实 `create_app` wiring 非先红；本阶段补 `test_error_mapping_realapp.py` 断言真实 app 注册 handler（pre-fix RED）。
> 3. **smoke 契约对齐**：`test_api_smoke::test_api_healthz` 旧断言静态 `{"status":"ok"}` 与真探测契约冲突，据 F2-04 升级更新（契约升级，非削弱断言）。
> 4. **会话 IO**：执行期 bash/Read 显示层间歇截断/串读（曾误显 "1 passed"）；最终结论以文件重定向 + 退出码 + 多次复跑取证，全量 `59 passed` 经多次一致确认。下游可用 §2 命令原样复跑。
