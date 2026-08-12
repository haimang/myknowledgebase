-- S09-T021..T026: freeze each old index-generation retirement behind an
-- explicit grace deadline.  The existing S04 cleanup intent/proof ledger is
-- deliberately reused: retiring a vector projection is a cleanup substrate,
-- not a second vector-state store.  ``eligible_at`` is additive because a
-- scanner must not reinterpret an already committed retirement when a future
-- deployment changes its configured grace duration.

BEGIN;

ALTER TABLE mkb_intake_cleanup_intents ADD COLUMN eligible_at TEXT;

CREATE INDEX ix_intake_cleanup_due
  ON mkb_intake_cleanup_intents(status, eligible_at, requested_at)
  WHERE status='open' AND eligible_at IS NOT NULL;

-- Only one open S09 retirement may own one exact item/namespace/index
-- generation.  A completed cleanup remains append-only evidence; a later,
-- separately governed rebuild can create a new open intent if required.
CREATE UNIQUE INDEX ux_intake_cleanup_open_index_generation
  ON mkb_intake_cleanup_intents(team_uuid, target_kind, target_ref)
  WHERE status='open' AND target_kind='index_generation';

COMMIT;
