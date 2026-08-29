# NH5 semantic provenance migration

- Production migration: `src/persistence/migrations/022_nh5_semantic_provenance.sql`.
- Adds `value_provenance` to `mkb_intake_revision_semantics` with closed values `caller|mapper|system|legacy_unverifiable`.
- Existing rows become explicitly unverifiable; no caller/mapper provenance is backfilled or guessed.
- New generic values record caller provenance except system-derived `is_active`; provider values record mapper provenance; aggregate metadata blobs record system provenance.
- `value_digest` and revision fingerprint do not include provenance, preserving the frozen value identity law.
- Verification: `tests/integration/test_nh5_semantic_uow.py`, PASS on commit `76f233b`.
