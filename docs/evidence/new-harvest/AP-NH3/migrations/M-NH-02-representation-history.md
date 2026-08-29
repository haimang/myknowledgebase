# M-NH-02 — typed representation authority

- Production migration: `src/persistence/migrations/019_nh3_representation_fact_history.sql`.
- Adds `mkb_representation_facts` and `mkb_acquire_decode_history` with one successful row per `(execution_uuid, step_key)` and one ordered ordinal per Execution.
- The path digest closes `step_key × capability × raw_byte_digest × representation_kind × observer_version`; row UUIDs and timestamps are deliberately excluded.
- Acquire/decode/print callbacks append through the OutcomeArtifactCommitter transaction. A callback exception or later Process CAS failure rolls the rows back.
- Route guards use `PersistenceRepresentationFactReader` inside the runtime transaction; they do not parse Process output JSON.
- Verification: `NH3-T01/T03/T04/T05`, PASS at `2026-08-29T19:56:38Z` on commit `b008702`.
