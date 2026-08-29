-- M-NH-01: split policy compatibility aliases from the sealed actual S05 truth.

BEGIN;

ALTER TABLE mkb_executions ADD COLUMN actual_binding_digest TEXT
  CHECK (actual_binding_digest IS NULL OR
         (length(actual_binding_digest)=64 AND actual_binding_digest NOT GLOB '*[^0-9a-f]*'));
ALTER TABLE mkb_executions ADD COLUMN actual_binding_state TEXT NOT NULL DEFAULT 'legacy_unverifiable'
  CHECK (actual_binding_state IN ('legacy_unverifiable','unsealed','sealed'));
ALTER TABLE mkb_executions ADD COLUMN seal_generation INTEGER NOT NULL DEFAULT 0
  CHECK (seal_generation >= 0);
ALTER TABLE mkb_executions ADD COLUMN actual_selected_route_digest TEXT
  CHECK (actual_selected_route_digest IS NULL OR
         (length(actual_selected_route_digest)=64 AND actual_selected_route_digest NOT GLOB '*[^0-9a-f]*'));
ALTER TABLE mkb_executions ADD COLUMN actual_clean_step_key TEXT;
ALTER TABLE mkb_executions ADD COLUMN actual_clean_process_key TEXT;
ALTER TABLE mkb_executions ADD COLUMN actual_clean_strategy TEXT;

CREATE TRIGGER ck_mkb_executions_actual_binding_insert
BEFORE INSERT ON mkb_executions
WHEN NOT (
  (NEW.actual_binding_state='sealed' AND NEW.actual_binding_digest IS NOT NULL
   AND NEW.seal_generation >= 1 AND NEW.actual_selected_route_digest IS NOT NULL
   AND NEW.actual_clean_step_key IS NOT NULL AND NEW.actual_clean_process_key IS NOT NULL
   AND NEW.actual_clean_strategy IS NOT NULL)
  OR
  (NEW.actual_binding_state IN ('legacy_unverifiable','unsealed')
   AND NEW.actual_binding_digest IS NULL AND NEW.seal_generation=0
   AND NEW.actual_selected_route_digest IS NULL AND NEW.actual_clean_step_key IS NULL
   AND NEW.actual_clean_process_key IS NULL AND NEW.actual_clean_strategy IS NULL)
)
BEGIN
  SELECT RAISE(ABORT, 'execution actual binding state mismatch');
END;

CREATE TRIGGER ck_mkb_executions_actual_binding_update
BEFORE UPDATE OF actual_binding_digest,actual_binding_state,seal_generation,
  actual_selected_route_digest,actual_clean_step_key,actual_clean_process_key,actual_clean_strategy
ON mkb_executions
WHEN NOT (
  (NEW.actual_binding_state='sealed' AND NEW.actual_binding_digest IS NOT NULL
   AND NEW.seal_generation >= 1 AND NEW.actual_selected_route_digest IS NOT NULL
   AND NEW.actual_clean_step_key IS NOT NULL AND NEW.actual_clean_process_key IS NOT NULL
   AND NEW.actual_clean_strategy IS NOT NULL)
  OR
  (NEW.actual_binding_state IN ('legacy_unverifiable','unsealed')
   AND NEW.actual_binding_digest IS NULL AND NEW.seal_generation=0
   AND NEW.actual_selected_route_digest IS NULL AND NEW.actual_clean_step_key IS NULL
   AND NEW.actual_clean_process_key IS NULL AND NEW.actual_clean_strategy IS NULL)
)
BEGIN
  SELECT RAISE(ABORT, 'execution actual binding state mismatch');
END;

ALTER TABLE mkb_intake_candidate_sets ADD COLUMN actual_binding_digest TEXT
  CHECK (actual_binding_digest IS NULL OR
         (length(actual_binding_digest)=64 AND actual_binding_digest NOT GLOB '*[^0-9a-f]*'));
ALTER TABLE mkb_intake_candidate_sets ADD COLUMN actual_binding_state TEXT NOT NULL DEFAULT 'legacy_unverifiable'
  CHECK (actual_binding_state IN ('legacy_unverifiable','unsealed','sealed'));

ALTER TABLE mkb_intake_snapshots ADD COLUMN actual_binding_digest TEXT
  CHECK (actual_binding_digest IS NULL OR
         (length(actual_binding_digest)=64 AND actual_binding_digest NOT GLOB '*[^0-9a-f]*'));
ALTER TABLE mkb_intake_snapshots ADD COLUMN actual_binding_state TEXT NOT NULL DEFAULT 'legacy_unverifiable'
  CHECK (actual_binding_state IN ('legacy_unverifiable','unsealed','sealed'));

ALTER TABLE mkb_execution_gates ADD COLUMN actual_binding_digest TEXT
  CHECK (actual_binding_digest IS NULL OR
         (length(actual_binding_digest)=64 AND actual_binding_digest NOT GLOB '*[^0-9a-f]*'));
ALTER TABLE mkb_execution_gates ADD COLUMN actual_binding_state TEXT NOT NULL DEFAULT 'legacy_unverifiable'
  CHECK (actual_binding_state IN ('legacy_unverifiable','unsealed','sealed'));

CREATE INDEX ix_mkb_executions_actual_binding
  ON mkb_executions(team_uuid, actual_binding_state, actual_binding_digest);

COMMIT;
