-- NS2 review fix: covering index for independent embed FIFO claim.
-- Column promotion remains on mkb_processes (T-O-173 / T-O-360). No new table.

BEGIN;

CREATE INDEX IF NOT EXISTS ix_mkb_proc_dispatch_embed_fifo
  ON mkb_processes(available_at, created_at, process_uuid)
  WHERE status = 'ready' AND dispatch_admitted = 1 AND dispatch_pool = 'embed';

COMMIT;
