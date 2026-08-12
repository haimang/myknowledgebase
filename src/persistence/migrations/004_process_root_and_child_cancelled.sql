-- D01 residual hardness: denorm Process.root_execution_uuid for ops isolation,
-- and cancelled_child_count so generation projections do not mix process-axis
-- cancelled counts into a child-shaped counts object.
BEGIN;

ALTER TABLE mkb_processes ADD COLUMN root_execution_uuid TEXT;

UPDATE mkb_processes
SET root_execution_uuid = (
  SELECT e.root_execution_uuid
  FROM mkb_executions AS e
  WHERE e.team_uuid = mkb_processes.team_uuid
    AND e.execution_uuid = mkb_processes.execution_uuid
)
WHERE root_execution_uuid IS NULL;

CREATE INDEX IF NOT EXISTS ix_mkb_proc_root
  ON mkb_processes(team_uuid, root_execution_uuid);

ALTER TABLE mkb_executions ADD COLUMN cancelled_child_count INTEGER NOT NULL DEFAULT 0
  CHECK (cancelled_child_count >= 0);

COMMIT;
