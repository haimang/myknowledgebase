-- D04 R10: persist scatter child identity as typed columns so CAS/projection
-- does not treat payload_extra as the identity SSOT.
BEGIN;

ALTER TABLE mkb_executions ADD COLUMN scatter_intake_revision_uuid TEXT;
ALTER TABLE mkb_executions ADD COLUMN scatter_member_ordinal INTEGER
  CHECK (scatter_member_ordinal IS NULL OR scatter_member_ordinal >= 0);
ALTER TABLE mkb_executions ADD COLUMN scatter_change_set_uuid TEXT;

CREATE INDEX IF NOT EXISTS ix_mkb_exec_scatter_identity
  ON mkb_executions(team_uuid, scatter_change_set_uuid, scatter_member_ordinal);

COMMIT;
