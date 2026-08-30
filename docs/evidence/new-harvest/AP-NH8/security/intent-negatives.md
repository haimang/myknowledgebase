# AP-NH8 security / fake-green negatives

Observed UTC `2026-08-30T04:53:13Z`. Commit `27fc3ca`.

## Illegal-cell admission (T-O-405 / FG-NH-15)

Public POST `/v1/teams/{team}/tasks` for illegal cells returns 422/409 with a closed code set and PersistencePort `COUNT(*)` of `mkb_tasks`/`mkb_processes` = 0 for that `task_uuid`. No 7×4 construction.

Attack cells exercised:

- eighth intent `intake.upgrade` → 422 `task-schema-invalid`
- fifth kind `supplier_crawl` → 422 `task-schema-invalid`
- caller `workflow_key` extra → 422 `task-schema-invalid`
- rebuild with `source` → 422 `task-schema-invalid`
- ingest with `intake_item_uuid` → 422 `task-schema-invalid`
- unregistered semantic key → 422 `INTAKE_SEMANTIC_KEY_UNREGISTERED` (before item lookup)
- empty semantics → 422 `task-schema-invalid` (pydantic `min_length=1`; resolver still has `METADATA_SEMANTICS_EMPTY`)
- deleted item rebuild/metadata/lifecycle → 409 `intake-item-deleted`
- deactivated item `index.rebuild` → 409 `index-rebuild-item-not-active`

Cross-team missing item remains 404 `intake-item-not-found` (same code, no leak).

## Namespace required (FG-NH-05)

T02–T08 omit `namespace_key` and expect 422 `RETRIEVE_SCHEMA_NAMESPACE_REQUIRED`. Empty-set positives always use a Layer-A key.

## No sqlite3-on-Turso (FG-NH-12)

T02/T03/T04/T05/T07 files contain no `import sqlite3` / `sqlite3.connect`. Reads go through PersistencePort.

## Exact-clean, not no-op cleaner (R-F11 / FG-NH-17)

Rebuild/metadata process_key family `intake.acquire.*` / `intake.decode.*` / `clean.*` count = 0. No `clean.extract.noop`. T08-B handoff count 3→0 without xfail.

## Reactivate does not restore serving (NH-C-74)

After reactivate: lifecycle=`active`, serving NULL, pointer/vector withdrawn, namespaced search empty until `intake.rebuild` publishes.

## Upgrade entrance = 0 (R-F12)

AST/DDL scan: seven intents; `restart_scope` two values; no `upgrade` on API models or task commands.

## No monkeypatch API member (FG-NH-01)

T08 reuses NH7 chinatax frozen records; no fetcher assignment.
