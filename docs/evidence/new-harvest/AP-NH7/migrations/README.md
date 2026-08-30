# AP-NH7 migrations

- `src/persistence/migrations/023_nh7_result_disposition.sql`
- Adds nullable `mkb_tasks.result_disposition` with CHECK `NULL | exhausted_zero`.
- Catalog alignment `M-NH-07` (`promptA.default`) was a pointer/catalog change in `be74417`, not DDL.
