# NHX1 Phase 5 security evidence

- `NHX1-T15`: explicit idempotency keys resolve to an opaque session token; token lookup is team-scoped and binds one pending reference. Legacy digest replay preserves the pre-NHX1 pending-hold behavior without exposing a session token.
- `NHX1-T16`: promotion and deletion are represented by durable journal/job states. Quarantined bytes are destroyed only after the catalog is tombstoned; live catalog rows are never removed by the reconciliation pass.
- `NHX1-T17`: generation/intake artifact identity and deletion are SQL-fenced by migration `029`; legacy verification is append-only and corrections are separate rows.
- `NHX1-T18`: raw, decoded, clean, and collection bodies are hydrated from CAS handles for execution but recursively redacted from persisted stage/envelope projections; nested secrets, paths, and signed URLs are absent.
- `NHX1-T19`: retrieval uses a single `read_snapshot()` and, where a publication manifest exists, requires exact membership before returning a hit. Manifest/member identity is immutable for the read.
- `NHX1-T20`: cleanup creates five substrate steps, blocks visibly on operator/backup holds, releases exact references first, and emits one terminal proof per substrate before job completion.

All Phase 5 negative tests completed with no `skip`/`xfail`; cross-team session lookup, identity mutation, body leakage, TOCTOU, hold, and tombstone races fail closed.
