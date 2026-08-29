# AP-NH4 Evidence Closure Index

Canonical closure: `docs/closure/new-harvest/AP-NH4-public-upload-and-object-lifecycle.md`

| 台账 D 目标 | 状态 | Evidence |
|---|---|---|
| upload identity | PASS | `queries/public-upload.json`; NH4-T01/T02 |
| public boundary | PASS | `security/upload-negative-matrix.md`; NH4-T03/T07 |
| ingest handoff | PASS | `queries/upload-ingest-handoff.json`; NH4-T04 |
| GC safety | PASS | `queries/gc-lifecycle.json`; NH4-T05/T06 |
| migration | PASS | `migrations/M-NH-05-upload-pending.md` |

Verdict: executed, closed-with-explicit-deferrals. Implementation commit `7359a96`. Observed UTC `2026-08-29T20:37:37Z`.
