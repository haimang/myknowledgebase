# MKB new-harvest NHX1 第三轮本地代码审查

> 日期：2026-08-31 · 审查基线：`d843f00f990f589725addacb19d196367a8b9568`
> 范围：NHX1 P1–P9 代码、migration 025–029、public/operator/readiness、测试和证据目录

## 结论

本地工程审查未发现未解释的 critical/high 代码缺口。全仓 `uv run pytest -q` 为 `1010 passed`，ruff 与 diff 检查通过；架构守卫覆盖 service concrete-persistence/import、public workflow selector、raw object surface、legacy writer 和 migration history。

## 审查项

| 轴 | 结果 | 实测证据 |
|---|---|---|
| Identity/epoch/session | PASS | `test_nhx1_observation_identity.py`, `test_nhx1_item_epoch.py`, `test_nhx1_object_sessions.py` |
| Revision/binding/outcome/outbox | PASS | NHX1 T09–T14 与 `test_nhx1_outbox_owner.py` |
| Evidence/CAS/publication/cleanup | PASS | NHX1 T15–T20、migration 029 SQL attack、manifest/GC/cleanup tests |
| Roles/capability/readiness | PASS（工程） | `test_nhx1_roles_readiness.py`, `test_nhx1_capability_gate.py`, NH6 supply/security suite |
| Public/operator/error/signal | PASS | strict catalog/views、operator receipt/CAS、10 signal/runbook registry |
| Cutover/retirement | PASS（本地） | mismatch gate、v2-only、forward rollback、inventory tests |
| Graph/race/crash/full repo | PASS（工程） | closed-set `888/27/21`、3 seeds、真实 SIGKILL、1010 tests |

## 剩余硬闸

唯一未完成项是 `NHX1-T22-O / T-O-419`：真实 production model/binary identity、10 strategy + 3 operation L3/L4 evidence 与 S16 具名 owner attestation 尚未提供。该项不能由本地 stub、fixture、skip 或 xfail 替代，因此 NHX1 仅达到 `implementation-complete-awaiting-live-verification`，不得宣称 full-close。

## 复审触发

owner 提供 T22-O 后，重跑 production profile 的 T22/T30 evidence command 与 closure join；若发现功能性回归，必须回到对应 owner Phase 并顺序重跑后继链。
