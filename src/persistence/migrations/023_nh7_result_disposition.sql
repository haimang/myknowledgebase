-- NH7-T09: product terminal disposition is independent of Task.status.

BEGIN;

ALTER TABLE mkb_tasks
ADD COLUMN result_disposition TEXT
  CHECK (result_disposition IS NULL OR result_disposition = 'exhausted_zero');

COMMIT;
