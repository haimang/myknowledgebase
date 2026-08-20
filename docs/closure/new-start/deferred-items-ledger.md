# New-start deferred items ledger

> **文档性质**：跨阶段后延项承接台账。只登记经核实、且本阶段诚实不修的项。
> **维护人**：实现者在 review-fix / closure 时 append。
> **关联**：`docs/code-review/new-start/NS1-review-VF-ledger.md` · `docs/code-review/new-start/NS2-review-VF-ledger.md` · `docs/closure/new-start/NS1-new-pipeline-closure.md` · `docs/closure/new-start/NS2-pipeline-priority-closure.md`

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

## NS2 — 2026-08-15 第 1 轮审查后

| ID | 来源 | 归属 | 摘要 | 后延原因 | reopen 触发器 | 承接 |
|----|------|------|------|----------|----------------|------|
| `NS2-V14.r` | VF-ledger V14 剩余切片 | `[partial-delivery] 剩余切片` | 011 未加表级状态耦合 CHECK；Turso 真机 010→011 未跑 | SQLite ALTER 无法廉价加表级 CHECK；本环境无 Turso 升级 harness。写路径已在 retry/recovery 清空 admission | 需要表重建约束，或授权 Turso 升级窗口 | NS2 closure §4 B |
| `NS2-O1` | AP O1 / T-O-357 | `[true-deferred]` | 真实 billing 套餐计量/扣减 | 本阶段只承诺恒真端口 | billing AP 立项 | billing AP |
| `NS2-O2` | AP O2 / T-O-358 | `[true-deferred]` | `cloud-inference` 适配器/路由/密钥 | 本阶段禁止当泄洪 | cloud AP | cloud AP |
| `NS2-O3` | AP O3 | `[true-deferred]` | MiniMax 替换 Claude `-p` | NI 抽象保持线上质量通道 | 模型选型 charter | owner |
| `NS2-O4` | AP O4 | `[true-deferred]` | urgent 插队老化 | 本阶段只提供 priority_rank 队头 | 若 high 被持续饿死 | 后继调度 charter |
| `NS2-O7` | AP O7 / NS1-V11 | `[true-deferred]` | pyturso raw sqlite inspection I/O | 非 NS2 引入；owner 禁止本阶段改 harness | harness charter 落地后重跑 `tests/e2e` | `NS1-V11` |
| `NS2-GPU` | AP §8.4 | `[true-deferred]` | 真机 GPU 双流争用 soak | 无稳定 GPU CI；AP 明确不假装覆盖 | owner 授权手工 soak | owner |

## NS5 — 2026-08-20 0820 first-round 修复后

| ID | 来源 | 归属 | 摘要 | 后延原因 | reopen 触发器 | 承接 |
|----|------|------|------|----------|----------------|------|
| `NS5-VF86` | VF86 / NS1-V11 | `[true-deferred]` | e2e 用 `sqlite3.connect` 打开 Turso 文件 | owner 冻结为 harness charter；NS5 不以全量 pytest 为 DoD | harness 去掉 sqlite3-on-Turso 后重跑 e2e | NS1-V11 |
| `NS5-T60` | AP P6-05 | `[true-deferred]` | 生成+vectorize+retrieval 主链 mega | 被 VF86 挡住，禁止用 sqlite3 路径当绿 | 无 sqlite3-on-Turso 的 mega harness | owner |
| `NS5-VF23` | VF23 | `[true-deferred]` | billing always-permit | AP O3 | billing AP | billing AP |
| `NS5-VF88` | VF88 | `[true-deferred]` | live GPU | AP O3 | NS2-GPU | owner |
| `NS5-VF97` | VF97 | `[true-deferred]` | browser/OCR/Vision 未接线 | AP O3 | capability charter | owner |
| `NS5-VF30.r` | VF30 余项 | `[partial-delivery] 剩余切片` | 完整 PDF 库 | 本轮只去 latin-1 回退 | PDF charter | 下游 |
| `NS5-VF37.r` | VF37 余项 | `[partial-delivery] 剩余切片` | 生产默认切 stub | stub 已可区分双通道；默认切生产模型需单独授权 | 生产模型默认 charter | 下游 |
| `NS5-VF41.r` | VF41 余项 | `[partial-delivery] 剩余切片` | S06 全树 | v1 两节点诚实 | 全树 charter | 下游 |
| `NS5-VF46.r` | VF46 余项 | `[partial-delivery] 剩余切片` | 全程 jsonschema | layered validator 已补 UUID/array/URI/date-time | 契约升级 | 下游 |
| `NS5-VF66.r` | VF66 余项 | `[true-deferred]` | 目录 CAS SSOT | T-O-120 | owner 授权 | owner |
| `NS5-VF91.r` | VF91 余项 | `[partial-delivery] 剩余切片` | 真机 CW e2e | unit 已 skipIf；constitution e2e 依赖真机 | NS4 constitution e2e | 下游 |
| `NS5-VF40.r` | VF40 | `[partial-delivery] 剩余切片` | Item pending/reviewing | CHECK 无 pending；review 用 deactivated 失败关闭检索 | 016 扩 lifecycle | 下游 |
| `NS5-VF36` | VF36 | `[true-bug]` 未关 | raw/clean 共享 envelope digest | 双 CAS 对象 | 后继 serving AP | 下游 |
| `NS5-VF52` | VF52 | `[true-bug]` 未关 | dim 切换 409 default | namespace 按 (model,ver,adapter,dim) 分键 | 后继 serving AP | 下游 |
| `NS5-VF62` | VF62 | `[partial-delivery]` 未关 | 重叠 run_once | heartbeat 已绿；supervisor 仍串行 | T04 后再开 | 下游 |

## NS6 — 2026-08-20 0820 second-pass 修复后

| ID | 来源 | 归属 | 摘要 | 后延原因 | reopen 触发器 | 承接 |
|----|------|------|------|----------|----------------|------|
| `NS6-VF86` | VF35.r / VF86 | `[true-deferred]` | e2e sqlite3-on-Turso | owner NS1-V11 | harness charter | owner |
| `NS6-VF6` | VF6 | `[true-deferred]` | 014 脏 unique 自愈 | 001 全行 unique 已拦正常升级 | 真实升级 UNIQUE 失败 | owner |
| `NS6-VF20` | VF20 | `[true-deferred]` | 检索 `read_transaction` | NS5 交 hydration cache | ingest 期间检索 503 | owner |
| `NS6-VF32` | VF32 | `[true-deferred]` | `/docs` 默认开 | NS5 O3 | 公网 bind | owner |
| `NS6-VF62` | VF62 | `[true-deferred]` | 重叠 `run_once` | 本轮仍关 | 后继 charter | owner |
| `NS6-VF4.r` | VF4.r | `[partial-delivery] 剩余切片` | D04 55 表闭集 | 本轮只核心表 | 全表 charter | 下游 |
| `NS6-VF11.r` | VF11.r | `[partial-delivery] 剩余切片` | 进程组杀孙 | CLI terminate 已 shield | 进程组 charter | 下游 |
| `NS6-VF25.r` | VF25.r | `[partial-delivery] 剩余切片` | 未编目 orphan / 目录 CAS | T-O-120 | owner 授权磁盘 SSOT | owner |
| `NS6-VF36.r` | VF36.r | `[partial-delivery] 剩余切片` | sidecar 真有界队列 | TTL cache 已切 | 有界队列 charter | 下游 |
| `NS6-VF38.r` | VF38.r | `[partial-delivery] 剩余切片` | VF14/VF16 关闭后的文档再核对 | 本循环已切 digest/namespace/purge | 文档 recut | 下游 |
| `NS6-VF15.r` | VF15 | `[partial-delivery] 剩余切片` | 同指纹二次 ingest 的 structurize outcome-commit | accept replay + items=1 已切 | 再生成 unique / 短路 replay | 下游 |
| `NS6-VF88` | 第1轮 VF88 | `[true-deferred]` | live GPU | NS5 O3 / NS6 O4 | live_profile | owner |
| `NS6-VF97` | 第1轮 VF97 | `[true-deferred]` | browser/OCR/Vision | NS5 O3 / NS6 O4 | 能力 charter | owner |
| `NS6-T01-hotfix` | VF1 soak | `known-hotfix` | BEGIN-cancel 用 `to_thread` 睡眠门 | in-process sqlite BEGIN cancel SIGSEGV | pyturso cancel-during-BEGIN 另开 harness | 文档 |
| `NS6-VF62` | 第1轮 VF62 | NS5 carry-forward | 重叠 `run_once` 仍关 | **不是**业主 true-deferred；NS6 AP 本轮仍不得打开 | heartbeat soak 后新 charter | owner |
