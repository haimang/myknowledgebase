-- NH1-NH9 review-fix: sealed-once, append-only facts, indexed vector identity.

BEGIN;

CREATE TRIGGER IF NOT EXISTS ck_mkb_executions_actual_binding_sealed_once
BEFORE UPDATE OF actual_binding_digest,actual_binding_state,seal_generation,
  actual_selected_route_digest,actual_clean_step_key,actual_clean_process_key,actual_clean_strategy
ON mkb_executions
WHEN OLD.actual_binding_state = 'sealed' AND (
  NEW.actual_binding_state IS NOT OLD.actual_binding_state
  OR NEW.actual_binding_digest IS NOT OLD.actual_binding_digest
  OR NEW.seal_generation IS NOT OLD.seal_generation
  OR NEW.actual_selected_route_digest IS NOT OLD.actual_selected_route_digest
  OR NEW.actual_clean_step_key IS NOT OLD.actual_clean_step_key
  OR NEW.actual_clean_process_key IS NOT OLD.actual_clean_process_key
  OR NEW.actual_clean_strategy IS NOT OLD.actual_clean_strategy
)
BEGIN
  SELECT RAISE(ABORT, 'execution actual binding is sealed');
END;

CREATE TRIGGER IF NOT EXISTS ck_mkb_representation_facts_no_update
BEFORE UPDATE ON mkb_representation_facts
BEGIN
  SELECT RAISE(ABORT, 'representation facts are append-only');
END;

CREATE TRIGGER IF NOT EXISTS ck_mkb_representation_facts_no_delete
BEFORE DELETE ON mkb_representation_facts
BEGIN
  SELECT RAISE(ABORT, 'representation facts are append-only');
END;

CREATE TRIGGER IF NOT EXISTS ck_mkb_acquire_decode_history_no_update
BEFORE UPDATE ON mkb_acquire_decode_history
BEGIN
  SELECT RAISE(ABORT, 'representation history is append-only');
END;

CREATE TRIGGER IF NOT EXISTS ck_mkb_acquire_decode_history_no_delete
BEFORE DELETE ON mkb_acquire_decode_history
BEGIN
  SELECT RAISE(ABORT, 'representation history is append-only');
END;

CREATE TRIGGER IF NOT EXISTS ck_mkb_vector_records_indexed_identity
BEFORE UPDATE OF content_digest ON mkb_vector_records
WHEN OLD.publication_state = 'indexed' AND NEW.content_digest IS NOT OLD.content_digest
BEGIN
  SELECT RAISE(ABORT, 'indexed vector content identity is immutable');
END;

COMMIT;
