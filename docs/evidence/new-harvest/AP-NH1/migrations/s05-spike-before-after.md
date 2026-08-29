# NH1 S05 spike before/after

- Before: production `mkb_executions.s05_binding_digest` remains NOT NULL and is populated from domain policy; no production DDL was changed by NH1.
- Spike session adds isolated test tables with `legacy_policy_alias_digest`, nullable `actual_binding_digest`, explicit `actual_binding_state`, and `seal_generation`.
- SQL states proven mutually distinguishable: `legacy_unverifiable`, `unsealed`, `sealed`.
- The caller's single PersistencePort UoW contains both the selected-route outcome row and unsealed→sealed CAS. Injected failure before commit rolls both back.
- Same route/digest replay returns generation 1; a different route/digest raises `ACTUAL_S05_SEAL_CONFLICT` HTTP 409.
- A legacy/domain 64-hex value never projects as actual and cannot be sealed in place.
- Production forward-only migration remains `M-NH-01` owned by AP-NH3 after `NH1-T05 PASS`.

Evidence: commit `1cdc066766a92eb1d8680bbf30689a443231234c`; `tests/integration/test_nh1_s05_seal_cas.py` 5 PASS; Q10/Q20; `2026-08-29T17:12:10Z`.
