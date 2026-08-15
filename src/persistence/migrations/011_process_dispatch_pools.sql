-- NS2 pipeline priority: elevate dispatch pool, admission gate, and queue timestamp to first-class columns on mkb_processes.
-- Note: This is a column promotion on an existing required table, NOT a new table, and NOT stored in payload_extra (T-O-173 / T-O-360 / D04-P04).

BEGIN;

ALTER TABLE mkb_processes ADD COLUMN dispatch_pool TEXT
  CHECK (dispatch_pool IS NULL OR dispatch_pool IN ('local-inference', 'non-interactive', 'embed'));

ALTER TABLE mkb_processes ADD COLUMN dispatch_admitted INTEGER NOT NULL DEFAULT 0
  CHECK (dispatch_admitted IN (0, 1));

ALTER TABLE mkb_processes ADD COLUMN dispatch_enqueued_at TEXT;

CREATE INDEX IF NOT EXISTS ix_mkb_proc_dispatch_ready
  ON mkb_processes(dispatch_pool, dispatch_admitted, available_at)
  WHERE status = 'ready';

COMMIT;
