# AP-NH9 migrations

No DDL in this AP. Assurance-only join of NH1–NH8 contracts.

- Closed-set manifest appends 82 work IDs / windows / FG without rewriting NH1-T07 `strategy_cells` / `op_cells` / `intent_illegal` digest bytes.
- `W-NH-PROM-CAT` uses the existing ObjectUploadService fault hook with a new `after_promote_before_catalog` stage; catalog/pending remain the same UoW.
- Experiment skeleton is not a migration and is not in closure join.
