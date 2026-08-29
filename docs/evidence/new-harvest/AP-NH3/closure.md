# AP-NH3 Evidence Closure Index

Canonical closure: `docs/closure/new-harvest/AP-NH3-representation-history-and-s05-binding.md`

| 台账 D 目标 | 状态 | Evidence |
|---|---|---|
| durable facts | PASS | `migrations/M-NH-02-representation-history.md`; NH3-T01–T04 |
| finite path | PASS | `queries/representation-path.json`; NH3-T05 |
| actual truth | PASS | `migrations/M-NH-01-actual-s05.md`; NH3-T06/T07 |
| propagation | PASS | `queries/actual-propagation.json`; NH3-T07 |
| retry law | PASS | NH3-T08 / `tests.txt` |
| redlines | PASS | `security/redline-scan.txt` |

Verdict: executed, closed-with-explicit-deferrals. Implementation commit `b008702`. Observed UTC `2026-08-29T19:56:38Z`.
