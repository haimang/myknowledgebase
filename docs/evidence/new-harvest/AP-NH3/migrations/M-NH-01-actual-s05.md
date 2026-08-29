# M-NH-01 — actual S05 binding split

- Production migration: `src/persistence/migrations/020_nh3_actual_s05_binding.sql`.
- Number `020` is the collision-safe realization of the plan's provisional `019`; NH2 consumed `018` before NH3 opened, and NH3 history therefore uses `019`.
- Existing rows receive `actual_binding_state='legacy_unverifiable'`, `actual_binding_digest=NULL`, and `seal_generation=0`.
- The migration contains no `UPDATE` and never copies `domain_binding_digest` or the physical compatibility `s05_binding_digest` into actual truth.
- New ingest creation writes `unsealed + NULL`; sealed rows require digest, route, clean step/process/strategy, and positive seal generation through insert/update triggers.
- CandidateSet, Snapshot, and Gate receive explicit actual digest/state columns; scatter children copy the root's complete sealed selection while their physical legacy alias remains policy-only.
- Verification: `tests/integration/test_nh3_s05_migration.py` and `tests/domain/test_nh3_actual_readers_scan.py`, PASS at `2026-08-29T19:56:38Z` on commit `b008702`.
