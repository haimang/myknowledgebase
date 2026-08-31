# NHX1 上线测试与最终 Closure 前置条件

> 当前基线：NHX1 工程代码已完成，当前 closure 类型为
> `implementation-complete-awaiting-live-verification`。
> 当前唯一未满足的硬闸：`T-O-419 / NHX1-T22-O`。

## 1. 先说结论

NHX1 现在不是“本地测试没跑完”，而是“工程验证已完成，真实上线证据还没有齐”。

上线测试前，必须准备真实部署角色、真实 supply、真实安全边界和可恢复的运行环境；最终 closure 前，还必须把这些上线结果绑定到当前 commit，并由 owner 完成真实 production/S16 签收。

## 2. 上线测试前必须具备的条件

| # | 前置条件 | 最低要求 | 为什么 NHX1 需要 |
|---|---|---|---|
| 1 | 固定发布物 | 固定 image/binary、代码 commit、配置版本和 migration checksum；测试结果必须指向同一版本 | NHX1 要证明“当前可部署系统”，不能用历史测试结果或另一个工作树的 PASS |
| 2 | 明确 deployment role | 明确运行 `api`、`workflow_worker`、`maintenance` 或显式 `all`；每个实例有独立 lease owner | T-O-416 要求 API 不 claim Process、worker 不跑 GC、maintenance 不执行业务；旧 NH 的 leaf-worker 名称没有形成这个部署契约 |
| 3 | 非空数据库升级 | 用真实非空 pre-fix 数据验证 024→当前 migration；025–029 forward-only、旧 migration checksum 不变、备份可恢复 | NHX1 同时治理旧库、rev1 pin、legacy evidence 和新 writer；空库迁移不能证明兼容性 |
| 4 | 主库与一致读 | 主库可写、`read_snapshot()` 可用、Turso/目标 adapter readiness 为真、schema registry 已 bootstrap | publication manifest、TOCTOU retrieval、ItemEpoch 和 cleanup 都依赖一致读与 durable owner |
| 5 | 10 个 clean strategy 真实可供给 | 每个 strategy 有真实 handler、contract/version/digest、输入输出和 replay law；不能用 stub/fixture 冒充 | T-O-412/T-O-419 把 10 strategy 纳入闭集；旧 NH 可在本地 deterministic 路径结束，NHX1 要证明生产供给存在 |
| 6 | 3 个 registered API operation 真实可供给 | 每个 provider/operation/version 有真实 parser、schema、identity 和错误路径；不能把 `registered_api.map` 算成第 11 个 strategy | NHX1 明确要求 10+3 分账；这是旧 NH deferred 被吸收后的 production gate |
| 7 | Browser/PDF/OCR/Model supply | browser 非 root、无 `--no-sandbox`；redirect 每跳过 S16 egress；PDF parser 无网络；OCR 可杀进程；模型 endpoint、adapter、model version、secret slot 均 pinned | T-O-419 与 S16 要求真实 supply identity 和安全 evidence；本地 glyph/stub 只能证明工程接线，不能证明生产能力 |
| 8 | S16 安全环境 | business/operator token、internal network、egress/SSRF policy、audit 写入、secret resolver、redaction、process-group kill 均可实测 | NHX1 将安全边界纳入 closure；旧 NH 的本地/阶段 closure 不要求具名 S16 live attestation |
| 9 | 有界测试数据 | 至少准备 team、Source、Observation、Snapshot、ItemEpoch、Namespace、ObjectUploadSession、publication manifest、cleanup/hold 数据 | NHX1 的核心断言是 owner、CAS、replay、retention 和物理收敛；只有空数据或单一 happy path 不足以触发这些边界 |
| 10 | Operator 控制和 runbook | 能读取 redacted Process/Execution/Cleanup/Outbox；能用 expected generation/row revision、idempotency 和 CommandReceipt 执行 stop/restart/requeue/resume | T-O-415/T-O-422 禁止人工 SQL 作为恢复面；旧 NH 结束时没有 NHX1 这套统一 operator control 硬要求 |
| 11 | Crash/race 运行权限 | 测试环境允许启动/杀死 API、worker、maintenance 子进程，保存 stdout/stderr/exit code/UTC，并能 cold restart | NHX1-T28/T29 要证明真实竞态和进程崩溃恢复，不接受 sleep、hook 或事后 SQL 作为唯一证据 |
| 12 | Evidence executor 可运行 | T01–T30 命令能在当前 commit 执行，记录 profile、argv、exit、stdout digest、minimum layer；禁止 skip/xfail/degraded 代替 | NHX1 把“证据真实性”本身列为硬闸；旧 NH 多数只需各 AP 的局部测试证据 |

## 3. 上线测试的最小顺序

1. 先验证 `/live`，再验证当前 role 的 `/ready`；API ready 不等于 worker ready。
2. 验证 capability catalog 和真实 10+3 supply；缺件必须 fail-closed，不能让 Process 先进入 running 再失败。
3. 按 `Observation → ItemEpoch → revision/replay → session/evidence → publication/cleanup` 顺序跑身份、CAS、重放、对象和物理收敛测试。
4. 验证 operator control、outbox dead owner、process-group kill、cold restart、retention/hold 和 GC。
5. 验证 shadow mismatch 为零后再做 v2-only cutover；rollback 只能停 admission 并前滚修复，不能恢复 legacy writer。
6. 用当前发布物执行全仓测试和 T01–T30 evidence executor，保存可复核的四元组。

## 4. 最终 Closure 还必须补齐的条件

| 条件 | 必须达到的状态 | 当前状态 |
|---|---|---|
| P1–P8 工程链 | 每 Phase 有 code EXIT、测试、日志、evidence、分簇 commit | 已满足 |
| P9 本地 assurance | graph-derived manifest、race、crash、persisted upgrade、full repo、third review 全通过 | 已满足；全仓 `1010 passed` |
| 迁移/兼容收口 | shadow mismatch=0、v2-only、legacy writer disabled；rev1/legacy reader 仍可解释 | 已有本地证据 |
| cleanup/GC drain | open cleanup、可释放 ref、quarantine/tombstone 未知态清零，或有明确 typed blocked/hold | 已有本地证据；线上 inventory 仍需执行 |
| 当前版本 evidence | T01–T30 绑定上线 commit、profile、UTC、exit、digest、层级 | 本地记录已齐；线上版本待执行 |
| 真实 10+3 production evidence | 每个 strategy/operation 的真实 L3/L4 identity、成功/失败路径与安全证据 | 待上线环境 |
| S16 named attestation | owner 对 model、binary、egress、secret、non-root、kill/process-tree 等签名并带 UTC/版本 | 待 owner 提供 |
| Closure verdict | 上述条件全部满足后才可 `full-close` | 当前为 `implementation-complete-awaiting-live-verification` |

## 5. 为什么之前 NH1–NH9 结束时不需要这一整套内容

这不是说旧 NH 没有测试，而是两次收口的完成谓词不同：

旧 closure 的实际口径也能直接看到：

- [AP-NH1 closure](/mnt/usb/workspace/myknowledgebase/docs/closure/new-harvest/AP-NH1-foundation-contracts-and-proof-baseline.md) 使用 `closed-with-explicit-deferrals`，把 `10+3 live-to-retrieval` 交给 NH7。
- [AP-NH6 closure](/mnt/usb/workspace/myknowledgebase/docs/closure/new-harvest/AP-NH6-local-runtime-supply-and-security.md) 仍把 `10+3 live-to-query` 交给 NH7，S16 owner signature 记录为 unsigned/deferred。
- [AP-NH9 closure](/mnt/usb/workspace/myknowledgebase/docs/closure/new-harvest/AP-NH9-closed-set-assurance.md) 明确保留 “S16 is not signed here”，仍以显式 deferred 结束。
- NHX1 的冻结 Q39 / `T-O-419` 后，真实 production supply 与 S16 签收不再是普通 carry-over，而是 NHX1 final closure 的必要条件；因此本次不能复用旧 NH 的 `closed-with-explicit-deferrals` 口径。

| 旧 NH 的收口口径 | 当时可以成立的原因 | NHX1 的变化 |
|---|---|---|
| 以各 AP 的局部工程实现、domain/integration/E2E 回归为主 | 旧 NH1–NH9 按既有 scope 逐 AP 收口，production supply/S16 等项目仍可留在 deferred/OOS ledger | NHX1 明确吸收二轮审查后的完整债务，并把 production closure 设为最终硬闸 |
| leaf-worker 作为单体名称即可 | 当时没有要求把 API、worker、maintenance 的授权和 readiness 拆成部署契约 | T-O-416 新增四 role、loop owner、claim owner、role-specific readiness |
| 本地 deterministic/stub 路径可作为工程回归 | 旧 closure 没有声称真实 10+3 production supply 已被 owner 验收 | T-O-419 明确禁止 stub/fixture 代替真实 model、binary、browser/PDF/OCR 和 S16 证据 |
| 旧对象、legacy evidence、open cleanup 可以记录为后续 ledger | 这些内容在旧 NH 中仍是分散 deferred，未组成同一个 closure gate | NHX1 将 session、legacy correction、publication manifest、physical cleanup、dead owner 和 cutover 统一为一条治理链 |
| 各 AP 的测试结果足以说明本 AP 代码 | 没有当前 commit 的 30 项闭集 executor 和全链 graph-derived denominator 要求 | NHX1-T01–T30 要求当前版本、当前 profile、真实 exit/digest/层级，禁止历史 PASS 文本冒充 |
| 未需要 owner 对 live runtime 作最终具名签收 | 旧阶段没有把“真实 production 可 claim”写进最终完成谓词 | NHX1 把 T22-O 作为 owner-only gate；缺签收只能 blocked，不能改名为 deferred-complete |

所以，之前 NH 结束“不需要”这些内容，根本原因是：旧 NH 结束的是既定工程 AP 的局部交付；NHX1 结束的是“二轮欠账全部还清并可在真实生产边界负责地上线”。后者的完成证明必然更严格。

## 6. 当前需要 Owner/上线环境提供的最短清单

1. production image/binary 与 commit/config/migration checksum。
2. 四 role 的实际部署拓扑和 lease owner。
3. 10 strategy + 3 registered operation 的真实 pinned supply inventory。
4. model/binary/browser/PDF/OCR 的版本、运行身份、egress 和 process-tree 安全记录。
5. S16 owner 具名签收（含 UTC、环境、版本和失败/拒绝路径）。
6. 在该环境重跑 T22/T30，并将结果追加到 NHX1 evidence 和 closure。

在这 6 项补齐前，当前 closure 保持 blocked 是正确状态，不是测试失败，也不是可以静默删除的文档欠账。
