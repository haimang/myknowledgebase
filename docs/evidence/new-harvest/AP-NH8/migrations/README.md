# AP-NH8 migrations

No DDL in this AP. `M-NH-09` is a behavioral exact-clean / lifecycle migration:

- rebuild/metadata skip acquire/decode/clean Processes
- metadata disposition is frozen at `prepare()` into `mkb_executions.payload_extra`
- `restart_scope` remains `atomic_intake_item|full_task` (`001_initial.sql`)
- no `upgrade` restart scope or eighth intent
