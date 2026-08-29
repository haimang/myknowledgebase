# M-NH-05 — upload_pending purpose

- Production migration: `src/persistence/migrations/021_nh4_upload_pending.sql`.
- `021` is the collision-safe realization of the plan's provisional `018`: NH2/NH3 already consumed `018..020` before serial NH4 execution.
- Rebuilds `mkb_object_references` with the prior eight purpose values plus `upload_pending`, copies every legacy row, recreates four indexes and both dependent object views, and adds one live-pending uniqueness fence.
- Forward migration test starts at migrations `001..020`, inserts a legacy `process_io` reference, applies `021`, and proves the row plus `mkb_v_object_live_refs`/`mkb_v_object_orphan_candidates` remain readable.
- Runtime contract `PromoteRequest.purpose` and DDL closed set are updated together.
- Verification: `tests/integration/test_nh4_upload_uow.py`, PASS on commit `7359a96` at `2026-08-29T20:37:37Z`.
