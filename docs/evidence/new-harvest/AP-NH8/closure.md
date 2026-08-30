# AP-NH8 evidence closure notes

Commit `27fc3ca`. Observed `2026-08-30T04:53:13Z`.

## Ledger D six targets

| Target | Result |
|--------|--------|
| Illegal-cell admission zero Task/Process | PASS T01 |
| Rebuild/metadata exact-clean | PASS T02/T03; T08-B=0 |
| Lifecycle query law | PASS T04–T06 |
| Index generation cutover | PASS T07 |
| API Item same services | PASS T08 |
| Compat + lineage | PASS T09/T10 |

## M-NH-09 sign-off

Signed. Exact-clean/lifecycle is a graph+admission behavioral migration with no DDL. Frozen admitted clean is replayed; new cleaner still only affects future ingest (`T-O-401/407`).

## Compat retirement review

Signed. Old compiled_digest pins complete on the historical v1 plan while kind-family is active. New Tasks resolve kind-only keys. Dropping the old key while an in-flight pin exists fails closed (`workflow-binding-mismatch` / `workflow-compiled-plan-unavailable`, zero Process). Re-injecting `compatibility_definitions` plus the old active key rolls back.

## NOT-success scan

1. no-op cleaner — absent (process-absence=0)
2. DB-only lifecycle — absent (namespaced search)
3. reactivate restore serving — absent
4. 7×4 matrix — absent
5. upgrade mixed into retry/rebuild — scan=0
6. sqlite3-on-Turso in T02–T08 files — absent
7. namespace-less 200 as PASS — absent
8. Task succeeded as retrieval — absent
9. T08-B xfail — absent (count=0 PASS)
10. monkeypatch API member — absent
11. L1 schema standing in for L4 — T04–T08 are L4
12. experiment in DoD — absent
