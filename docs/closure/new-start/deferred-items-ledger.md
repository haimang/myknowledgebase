# New-start deferred items ledger

> **文档性质**：跨阶段后延项承接台账。只登记经核实、且本阶段诚实不修的项。
> **维护人**：实现者在 review-fix / closure 时 append。
> **关联**：`docs/code-review/new-start/NS1-review-VF-ledger.md` · `docs/closure/new-start/NS1-new-pipeline-closure.md`

---

## NS1 — 2026-08-14 第 1 轮审查后

| ID | 来源 | 归属 | 摘要 | 后延原因 | reopen 触发器 | 承接 |
|----|------|------|------|----------|----------------|------|
| `NS1-V11` | VF-ledger V11 / 三方 review | `[true-deferred]` | 若干 e2e 用标准 `sqlite3.connect` 打开 `persistence_backend="turso"` 文件，出现 `disk I/O` / `file is not a database` | baseline harness 固有问题，非 NS1 机制；owner 本轮禁止改测试引擎 / 发版 | successor test-harness/adapter charter 落地后，无排除重跑 `tests/e2e` | owner + harness charter |
| `NS1-V5.r` | VF-ledger V5 剩余切片 | `[partial-delivery] 剩余切片` | CLI 大物料已改走 stdin，本地假 executable 证明不再 E2BIG；未对真实 `claude` 二进制做 vendor 验证 | owner 明确禁止 live vendor 验证 | owner 授权 live Claude 验证窗口 | owner live-verification charter |
| `NS1-O-live-deploy` | NS1 closure O5 | `[true-deferred]` | live migration / worker publish / Pages publish | owner 本轮 scope 禁止 | 单独 release charter | owner |

已知 Turso inspection 用例名（至少）：

- `scoped_index_rebuild_promotes_generation_without_new_intake_revision`
- `index_rebuild_stale_fence_fails_without_cutover_and_old_generation_remains_retrievable`
- `reactivate_restores_active_lifecycle_but_not_stale_serving_state`
- `rebuild_and_metadata_lifecycle_paths_complete_through_public_http`
- `registered_api_scatter_auto_zero_and_fanin_recovery`
