# Phase 2 schema attack results

- Invalid observation/session/migration states are rejected by DDL checks.
- Lower/kebab canonical error codes are rejected; legacy names exist only in the alias table.
- UPDATE/DELETE against v2 binding, selection, verification, correction, publication manifest/member authorities abort through append-only triggers.
- A nonzero shadow mismatch atomically increments durable mismatch count and moves migration state to `blocked`; stale cursor advance is fenced.
- The migration does not UPDATE rev1 workflow rows, selected-output v1, or legacy upload pending rows, and creates no synthetic Observation/session/evidence history.
