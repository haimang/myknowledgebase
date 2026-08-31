# NHX1 Phase 7 operational signal runbook

This runbook is a bounded reference for the registered S15 signal catalog.
It does not own Task, Execution, Process, outbox, or cleanup state transitions.

| Alert | First checks | Safe action |
|---|---|---|
| `ALERT_OUTBOX_DEAD` | Inspect the redacted dead-delivery projection and owner generation. | Repair the cause, then use the typed operator requeue command with the expected generation. |
| `ALERT_READINESS_FALSE` | Compare the role-specific readiness components and deployment profile. | Restore the missing dependency; never bypass the worker claim fence. |
| `ALERT_REPAIR_FAIL` / `ALERT_LEASE_STUCK` | Inspect diagnostic and lease recovery evidence. | Use generation-fenced control; do not edit terminal rows or run ad-hoc SQL. |
| `ALERT_DIAG_DROP` / `ALERT_RETENTION_JOB_FAIL` | Check the bounded drop/failure metric and S15 retention state. | Preserve business state; retry the observability operation on its next scheduled tick. |
| `ALERT_SECURITY_DENY_SPIKE` and `ALERT_SEC_*` | Review sampled, redacted security audit and low-cardinality metrics. | Keep the deny fence active and follow S16 token/egress/audit response. |

The signal definitions, metric names, alert IDs, and owner components are
code-owned in `src/runtime/signals.py` and projected durably by the governance
registry. New signals require a reviewed catalog change.
