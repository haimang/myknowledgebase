# AP-NH5 Evidence Closure Index

Canonical closure: `docs/closure/new-harvest/AP-NH5-semantic-ledger-and-retrieval-facets.md`

| 台账 D 目标 | 状态 | Evidence |
|---|---|---|
| strict semantic authority | PASS | `queries/generic-contract.json`; `queries/six-tuple-four-kinds.json` |
| S06/g0 split | PASS | `queries/overlay-diff.json` |
| channel contract | PASS | `queries/channel-split.json` |
| SQL facets | PASS | `queries/facet-sql.json` |
| metadata T08-A | PASS | `queries/metadata-lineage.json` |
| metadata T08-B | RED HANDOFF | `security/semantic-redlines.md` → NH8-T03 |

Verdict: executed, closed-with-explicit-deferrals. Implementation commit `76f233b`. Observed UTC `2026-08-29T21:38:33Z`.
