# [baseline-dev / v1 Codex handoff] Closure

> 阶段: `docs/baseline → 现有 MKB 实现收口`
> 范围: `截至 2026-08-12 20:51 CST 的已提交实现、未提交集成工作与可复现验证`
> Close-type: `close-with-known-issues`
> 状态: `close-with-known-issues`
> 日期: `2026-08-12` · 作者: `Codex (/root)`
> 关联 charter: `docs/baseline/`
> 关联 design: `N/A（执行真相为 docs/baseline/domain-truth/）`
> 关联 action-plan: `N/A`
> 关联 evidence: `inline §2`
> 关联 review: `N/A`

---

## 0. 一句话 verdict

> 已将基础持久化、Task/Workflow 生命周期、来源接入、LSRAG artifact 链、检索/安全/观测及 generation 只读 API 落为一组连续提交；当前工作区还包含已通过聚焦回归但未隔离提交的 S07 metadata refresh 与 S08 generation purge，且 S11 live generation ledger 和 S14 L3 override/feature flag 仍未完成，所以以 `close-with-known-issues` 交接，不能宣称整个 baseline 已完成。

**本阶段最关键的 known gap（对下游影响）**：

1. `live_inference=True` 的 S06/S07 仍没有实际调用 `structured_generate` / `text_generate`，也没有写 `mkb_generation_invocations` 与关联的 `mkb_inference_invocations`；这使 live provenance 的硬门未闭合。
2. `src/runtime/intake_pipeline.py` 同时存在 staged 与 unstaged hunk；已暂存的 S08 snapshot 依赖未暂存的 `Path` / `prompt_root` 预备代码，禁止直接提交 index。
3. 当前树未完成全量 `pytest` 与 `ruff` 绿灯；`ruff` 在收口时明确报出 6 个未使用 import，均来自未完成的 S11 预备接缝或其相邻 S07 import。

本 closure 文件按业主要求写入工作区，但未单独提交，以免在已有混合 index 上制造一个误导性的“干净收口”提交。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| Greenfield schema、Task/Execution/Process 基础、API 与对象存储骨架 | ✅ closed · `observed-OK-at-closure` | `3cb0cff` + 后续完整回归曾仅剩两个 rebuild 生命周期失败（其余通过） + 本会话 `2026-08-12 CST`；当前聚焦链路见 §2。 |
| S02 Task 生命周期、retry/restart、gate/public projection 加固 | ✅ closed · `observed-OK-at-closure` | `3ced2dd`, `e986cc4` + `tests/unit/test_task_api_contract.py`, `tests/unit/test_task_projections.py`, `tests/unit/test_workflow_runtime.py` 已随本轮回归运行 + `2026-08-12 CST`。 |
| S03 immutable workflow revision、cleanup fence、registered API scatter | ✅ closed · `observed-OK-at-closure` | `f5cfd43`, `4d49614`, `a397d8d` + workflow/runtime 回归 + `2026-08-12 CST`。 |
| S05 sources：inline/local/http/static/browser/pdf/registered API 的受控接入与证据 | ✅ closed · `short-verified` | `7e3703e` + `uv run pytest -q tests/e2e/test_source_capability_paths.py tests/unit/test_intake_source_capabilities.py`（包含于本次 19 passed）+ `2026-08-12 20:51 CST`。 |
| S06/S07 deterministic LSRAG compiler、artifact/pointer 合同与 construct→vectorize gate | ✅ closed · `short-verified` | `588a0ef`, `4d210db`, `1785142`, `ba38ce2` + `tests/e2e/test_generation_pipeline_contracts.py`（包含于本次 19 passed）+ `2026-08-12 20:51 CST`。 |
| S06 generation artifact 的 Task-scoped 安全只读 API | ✅ closed · `observed-OK-at-closure` | `ec3779c` + `tests/unit/test_generation_artifact_api.py`（此前回归）+ `2026-08-12 CST`。 |
| S09 index rebuild、generation retirement 与 S10 retrieval serving fence | ✅ closed · `observed-OK-at-closure` | `9412ce4`, `c26248e`, `6c46605` + `tests/unit/test_index_generation_retirement.py`, `tests/unit/test_retrieval_service.py`（此前回归）+ `2026-08-12 CST`。 |
| S16 token admission、egress、secret/supply fence | ✅ closed · `observed-OK-at-closure` | `b76d46e`, `9b59046` + `tests/unit/test_security_boundary.py`, `tests/unit/test_inference_runtime.py`（此前回归）+ `2026-08-12 CST`。 |
| rebuild 从已接收 clean artifact 的冻结证据重放，而非伪造外部 acquisition | 🟢 short-verified · `partial` | 未提交的 `src/runtime/intake_pipeline.py` root hunk + `uv run pytest -q tests/e2e/test_intake_rebuild_metadata.py tests/e2e/test_intake_reactivate.py` 曾为 `2 passed`，并包含于本次 19 passed + `2026-08-12 20:51 CST`；仍需隔离 review/commit。 |
| S07 metadata refresh：冻结完整源 artifact family、复用 summaries、重新构建 S07/S08 | 🟢 short-verified · `partial` | 未提交的 `src/runtime/intake_pipeline.py`, `src/workflows/builtin_lsrag.py`, `src/runtime/workflow_engine.py`, `tests/e2e/test_intake_rebuild_metadata.py` + 本次 19 passed + `2026-08-12 20:51 CST`；未形成独立提交，且 final lint 未通过。 |
| S08 typed `VectorizeCommand`/handoff 与 `purge_generation` generation/channel 级软删除 | 🟢 short-verified · `partial` | staged `src/contracts/vector/models.py`, `src/services/vector_purge.py`, `tests/e2e/test_vector_purge_generation.py` 与混合的 pipeline hunk + `uv run pytest -q tests/e2e/test_generation_pipeline_contracts.py tests/e2e/test_vector_purge_generation.py` 为 `2 passed`，后续本次 19 passed + `2026-08-12 20:51 CST`；index 不能直接提交。 |
| S11 live structured/text generation 与双 invocation ledger | ❌ missing · `deferred` | 只有未完成预备代码；未接进 `_structurize` / `_construct`，未写 ledger，未做测试。 |
| S14 L3 allowlisted override、override audit、feature flag bundle | ❌ missing · `deferred` | 现有 `ConfigSnapshotService` 已冻结 L0/L1/L2/L4，但未实现 L3 / `flag_bundle_digest`；无针对 S14-A07–A10/A17/A18 的测试。 |

### 已提交功能索引

下列提交构成当前可安全 checkout 的已提交基线（由新到旧列出关键闭环，而非声称它们替代最终全量回归）：

| 提交 | 内容 |
|------|------|
| `ec3779c` | Task-scoped generation artifact / pointer 只读 API 与单元测试。 |
| `7e3703e` | source capability profiles、HTTP acquisition 与 source E2E/单测。 |
| `1785142` / `ba38ce2` | generation artifact 合同、fenced construct-to-vectorize intent。 |
| `3ced2dd` / `e986cc4` | Task lifecycle 与 scheduling propagation。 |
| `4d210db` / `588a0ef` | deterministic LSRAG compiler 与 structure coverage。 |
| `4d49614` / `03c979d` / `a397d8d` | durable intake pipeline、cleanup eligibility、registered API scatter。 |
| `9412ce4` / `c26248e` | index-generation retirement 与 rebuild cutover test。 |
| `9b59046` / `6c46605` / `b76d46e` | inference/supply fence、retrieval fence、安全 admission/egress。 |
| `33a9235` / `95bbf6b` / `4cac174` | observability metrics/retention/read path 与 failure boundary。 |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| 当前主闭环聚焦回归 | `uv run pytest -q tests/e2e/test_intake_rebuild_metadata.py tests/e2e/test_intake_reactivate.py tests/e2e/test_generation_pipeline_contracts.py tests/e2e/test_vector_purge_generation.py tests/e2e/test_source_capability_paths.py tests/unit/test_intake_source_capabilities.py` | `19 passed` | rebuild、reactivate、metadata refresh、generation artifacts、S08 purge、source capability。 |
| S08 原始聚焦回归 | `uv run pytest -q tests/e2e/test_generation_pipeline_contracts.py tests/e2e/test_vector_purge_generation.py` | `2 passed` | typed S08 handoff 与 generation/channel scoped soft delete。 |
| rebuild 兼容修复 | `uv run pytest -q tests/e2e/test_intake_rebuild_metadata.py tests/e2e/test_intake_reactivate.py` | `2 passed` | accepted clean artifact 的 frozen evidence 分支。 |
| 当前 diff 结构检查 | `git diff --check && git diff --cached --check` | pass | 当前 index + worktree 无空白错误。 |
| 当前编译检查 | `uv run python -m compileall -q api src` | pass | `api/` 与 `src/` 可编译。 |
| 当前静态检查 | `uv run ruff check .` | **fail: 6 × F401** | `src/runtime/intake_pipeline.py` 中 `InvocationContext`, `StructuredGenerateRequest`, `StructuredGenerateResponse`, `TextGenerateRequest`, `TextGenerateResponse`, `summary_plan` 未使用。 |
| 最近一次全量 pytest | `uv run pytest -q`（在当前未提交三支工作汇合前） | 当时仅 `test_intake_reactivate` 与 `test_intake_rebuild_metadata` 两项失败；上述针对性修复已使二者通过 | 不是当前 worktree 的最终全量绿灯，不能作为 release proof。 |

**证据时间**：除另有说明外均为 `2026-08-12 20:51 CST` 本次会话。没有 live model endpoint、真实生产数据库、长期 worker soak 或 owner acceptance 测试证据。

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| 聚焦核心 intake/RAG 回归 | rebuild、metadata、reactivate、artifact、source、purge 同时通过 | 19 passed | ⚠ PARTIAL：仅聚焦集。 |
| 当前代码静态质量 | `ruff check .`、`compileall`、`diff --check` 均成功 | 编译与 diff 检查通过；ruff 6 个 F401 | ❌ FAIL。 |
| 可安全提交的工作树 | index 自洽、没有 staged/unstaged 依赖、每项可独立 commit | `src/runtime/intake_pipeline.py` 为 `MM`；staged S08 snapshot 依赖 unstaged S11 `Path`/`prompt_root` | ❌ FAIL。 |
| S11 live provenance | S06/S07 实际走 live facade 并写 generation + inference invocation ledger | 尚未实现 | ❌ FAIL。 |
| S14 配置治理 | L3 allowlist/audit、semantic-vs-ops、default-off flag bundle | 未实现 | ❌ FAIL。 |
| 最终回归 | 当前完整 worktree 的 `uv run pytest -q` 与 `uv run ruff check .` | 未运行且 ruff 已失败 | ⏸ PENDING。 |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| S11 live S06/S07 调用与 invocation persistence | `C` | 未实现；仅 pipeline 预备 imports/dataclasses/`prompt_root` 接缝存在 | 先清理或完成预备接缝；接入 `_structurize` 与 `_construct` 后新增 live/deterministic 双路径测试 | 下游 runtime/inference agent。 |
| S14 L3 overrides 与 feature flags | `C` | 未实现 | `src/contracts/api/models.py`、`src/services/config_snapshots.py`、`src/runtime/task_service.py`；实现 S14-A07–A10/A17/A18 | 下游 config/registry agent。 |
| S07 metadata refresh 的独立 review/commit | `C` | 工作区已实现、聚焦 E2E 通过，但未隔离提交 | review `src/runtime/intake_pipeline.py`, `src/workflows/builtin_lsrag.py`, `src/runtime/workflow_engine.py`, `tests/e2e/test_intake_rebuild_metadata.py` 后再提交 | 下游 workflow/RAG agent。 |
| S08 purge 的 index 重建与独立 commit | `C` | S08 文件已暂存，pipeline hunk 与未暂存代码交叉 | 先让 pipeline worktree/index 自洽，再按 `git diff --cached` 和 `git diff` 审核、重建有界提交 | 下游 vector/RAG agent。 |
| root integration hunk 的 review/commit | `C` | 18 个未暂存文件、约 3,682 行净变更；包含 app composition、Task/API/lifecycle/registry/config/storage/workflow 集成 | 按功能拆分并在每个提交前跑对应 unit/E2E；不可把它当作已发布 | 下游 lead agent。 |
| 当前 full regression / static gate | `C` | 聚焦测试通过，最终 gate 未绿 | 完成上列代码与 index 收口后跑 §6 的完整命令 | 下游 lead/CI agent。 |
| baseline 文档明示的非 v1 / deferred 项 | `A` | 不在本轮代码收口范围 | 例如 D02-DR007 指向的 S14–S15 runbook/R2；以各 domain-truth 的 deferred 说明为准 | owner / 后续 charter。 |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred） | ✅ §1 的每个已关闭项都标为 `observed-OK-at-closure` 或 `short-verified`；三个未完成项明确标为 `partial/deferred/missing`。 |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | ⚠ 已提交项给出 commit 与测试集合、时间；历史全量回归的精确总数不可从本次收口重新取得，因此没有将其升格为 live-verified。 |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改） | ⚠ `git diff --check` 通过，但当前共有 staged/unstaged 混合的实现 hunk；它们均与 baseline runtime/config/vector/test 范围相关，尚未形成可提交 scope。 |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ §4 已列出 A/C 分类、文件入口、触发条件和接手角色。 |
| owner-test 项未经 owner 复测的标 ⏸ PENDING（无“我修了”式宣称） | ✅ 没有 owner/live 验收；§2 与 §3 均明确为 pending / non-live。 |

---

## 6. Handoff / 下阶段 entry-gate 预核对

| 入口条件 | 状态 | 备注 |
|----------|------|------|
| 读取本 closure 与当前 `git status --short` | ✅ | 本文件以 `2026-08-12 20:51 CST` 为状态快照；开始前应重新采集 status。 |
| 保住当前所有 worktree 和 index hunk | ✅ | 不要 `reset --hard` 或盲目提交；`intake_pipeline.py` 的 index 与 worktree 必须一起审阅。 |
| 消除 staged/unstaged pipeline 依赖 | ⏸ | 当前 staged patch 单独提交会缺少 `Path`/`prompt_root` 定义；先重建可自洽 index。 |
| 恢复 lint 绿灯 | ⏸ | 完成 S11 或删除其未使用预备代码，并移除未使用 `summary_plan`；随后跑 `uv run ruff check .`。 |
| 完成 S11 | ⏸ | 详见下面的最小验收。 |
| 完成 S14 | ⏸ | 详见下面的最小验收。 |
| 完整 CI 式回归 | ⏸ | 代码收口后跑 §6 的推荐命令。 |

### 推荐接手顺序

1. **先保存和审阅当前两层 diff**：分别查看 `git diff --cached -- src/runtime/intake_pipeline.py` 与 `git diff -- src/runtime/intake_pipeline.py`。不要把当前 index 当成可靠 commit 候选。
2. **决定 S11 预备接缝的命运**：要么完整实现 live path，要么用最小补丁移除未使用的 imports、dataclasses 和 `prompt_root` 参数/成员；不可留下 lint 红灯的半接缝。
3. **隔离 S07/S08/root integration**：以逻辑闭环而不是“文件所有权”切分提交。pipeline 共享 hunk 需要人工确认；不应将 unrelated API/config/lifecycle 改动带入 vector-only commit。
4. **再做功能扩展**：先 S11，再 S14；两者是目前已知、未实现的 baseline 责任项。
5. **最后验证**：

   ```bash
   uv run ruff check .
   uv run python -m compileall -q api src
   git diff --check
   uv run pytest -q
   ```

### S11 最小验收清单

- [ ] deterministic profile 继续保持零外部模型调用。
- [ ] live S06 使用冻结 binding/prompt/schema 调 `InferenceFacade.structured_generate`；live S07 使用 `text_generate`。
- [ ] 每次 live 调用写一条 `mkb_generation_invocations`，含 frozen binding、prompt/schema、input/output/error digest、token、process attempt/ordinal，且不存 prompt/text 正文。
- [ ] 同次调用写关联 `mkb_inference_invocations`（带 `generation_invocation_uuid`）；成功、transport/validation 失败都能审计。
- [ ] 执行 retry/recovery 不重新 resolve active binding；测试覆盖 correlation、失败、deterministic 旁路与无秘密/正文泄漏。

### S14 最小验收清单

- [ ] 在严格 Task DTO 中增加显式 override 子模型；不可利用 `payload_extra` 绕过。
- [ ] allowlist 仅允许注册 `profile_id`、受 cap 限制的 `batch_size` / `top_k` / `return_k` / `recall_k` / pack budget，以及非语义 `dry_run` / `debug_trace`。
- [ ] 拒绝 model/prompt/schema/adapter/dimension/workflow/secret/absolute path/未注册 flag；拒绝写唯一 `mkb_security_audit_events`，成功写唯一 `config.override_applied` domain event。
- [ ] L4 包含 override digest、semantic effective values 与 `flag_bundle_digest`；ops-only `security.*` / `obs.*` 不改变 binding digest。
- [ ] checked-in default-off feature flag bundle；覆盖 S14-A07、A08、A09、A10、A17、A18。

---

## 7. Cross-cut 不变量（0-drift 确认）

| 不变量 | 状态 | 证据 |
|--------|------|------|
| 公开 Task API 不允许 caller 覆盖 workflow/graph/route/model/vector | ✅ 保持 | `src/contracts/api/models.py` 的 strict DTO 与既有 `tests/unit/test_task_api_contract.py`、retrieval validation tests；S14 override 尚未开放。 |
| Execution / Process 继续使用冻结 workflow/config digest，不在 retry 中热切 active revision | ✅ 保持 | 已提交 `f5cfd43`, `3ced2dd`, `e986cc4`；当前 metadata refresh 也以 frozen source family 为目标。 |
| 生成/对象/向量路径只传逻辑 ref 与 digest，不把绝对路径或正文写入公共 envelope | ✅ 保持 | 已提交 artifact/storage/security contract；S11 handoff 必须延续该约束。 |
| 自动 preflight 不伪造 human gate；runtime/evidence failure 走 Process failure/retry | ✅ 保持 | S05 pipeline + metadata/rebuild 聚焦回归通过。 |
| vector serving/purge 以 team/execution/generation/channel 边界为准 | ⚠ 部分保持 | S08 targeted E2E 通过，但未形成自洽独立 commit；完整 serving/purge 回归待 final suite。 |
| 任何交接结论不得把聚焦测试当作生产/live 验收 | ✅ 保持 | 本 closure 的 close-type 为 `close-with-known-issues`，§2–§5 明确区分 short verification 与 pending。 |

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| `v1` | `2026-08-12` | `Codex (/root)` | 当前 baseline 实现、测试、dirty worktree 与后续 handoff 的首次收口。 |
