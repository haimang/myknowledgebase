-- MKB initial physical schema.
--
-- Source of truth: docs/baseline/domain-truth/D04-turso-physical-schema.md
-- (D04-v1.1, including the S11 reopen).  This migration includes all 55 D04
-- required MKB tables and views, plus the documented S08/S09 additive
-- reconciliations required for facets, publication proofs, and index pointers.
--
-- SQLite compatibility note
-- -------------------------
-- Turso/libSQL deployments may map `embedding` to their native F32 vector
-- type and replace the compatibility B-tree index named
-- `vec_idx_mkb_vector_records_embedding` with libsql_vector_idx(embedding).
-- Stock SQLite has no vector virtual type/function, so this portable initial
-- migration uses BLOB and creates the identically named structural index.
-- Runtime readiness must still fail closed unless the configured deployment
-- reports native vector + ANN support; a B-tree BLOB index is not an ANN
-- implementation.  Keeping the migration executable in stock SQLite makes
-- empty-DB/bootstrap and schema-gate tests deterministic.

PRAGMA foreign_keys = ON;

BEGIN;

-- --------------------------------------------------------------------------
-- ops (5 tables, plus the S11 inference invocation ledger below)
-- --------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS mkb_schema_migrations (
  migration_id TEXT PRIMARY KEY,
  checksum TEXT NOT NULL,
  applied_at TEXT NOT NULL,
  applied_by TEXT
);

CREATE TABLE mkb_teams (
  team_uuid TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'inactive', 'deleted')),
  row_revision INTEGER NOT NULL DEFAULT 0 CHECK (row_revision >= 0),
  creation_fingerprint TEXT NOT NULL,
  deactivated_at TEXT,
  deleted_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE mkb_domain_events (
  event_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  trace_uuid TEXT NOT NULL,
  event_type TEXT NOT NULL,
  -- D04 §3.1.3 declares `severity` twice.  The first is reconciled as the
  -- aggregate (business family); `severity` below remains the log-level enum.
  aggregate TEXT NOT NULL CHECK (aggregate IN
    ('task', 'execution', 'process', 'intake', 'generation', 'gate',
     'outbox', 'object', 'vector', 'registry', 'ops')),
  severity TEXT NOT NULL DEFAULT 'info'
    CHECK (severity IN ('debug', 'info', 'warn', 'error')),
  task_uuid TEXT,
  execution_uuid TEXT,
  process_uuid TEXT,
  subject_kind TEXT,
  subject_uuid TEXT,
  causation_event_uuid TEXT,
  actor_kind TEXT NOT NULL
    CHECK (actor_kind IN ('system', 'worker', 'upstream', 'operator')),
  actor_id TEXT,
  -- These are lifecycle values surrounding a state transition, not changes to
  -- the debug/info/warn/error severity.  D04's prose labels are reconciled.
  status_before TEXT,
  status_after TEXT,
  summary TEXT NOT NULL CHECK (length(summary) <= 512),
  payload_digest TEXT NOT NULL
    CHECK (length(payload_digest) = 64
           AND payload_digest NOT GLOB '*[^0-9a-f]*'),
  payload_json TEXT NOT NULL DEFAULT '{}',
  schema_version TEXT NOT NULL DEFAULT 'mkb.domain-event.v1',
  occurred_at TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid),
  FOREIGN KEY (causation_event_uuid) REFERENCES mkb_domain_events(event_uuid)
);

CREATE TABLE mkb_ops_diagnostic_logs (
  log_uuid TEXT PRIMARY KEY,
  team_uuid TEXT,
  trace_uuid TEXT,
  task_uuid TEXT,
  execution_uuid TEXT,
  process_uuid TEXT,
  log_level TEXT NOT NULL CHECK (log_level IN ('debug', 'info', 'warn', 'error')),
  log_code TEXT NOT NULL,
  log_message TEXT NOT NULL CHECK (length(log_message) <= 1024),
  calling_module TEXT NOT NULL,
  calling_worker TEXT NOT NULL DEFAULT 'mkb-leaf',
  payload_json TEXT NOT NULL DEFAULT '{}',
  payload_digest TEXT NOT NULL
    CHECK (length(payload_digest) = 64
           AND payload_digest NOT GLOB '*[^0-9a-f]*'),
  occurred_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid)
);

CREATE TABLE mkb_security_audit_events (
  audit_uuid TEXT PRIMARY KEY,
  team_uuid TEXT,
  trace_uuid TEXT,
  request_id TEXT,
  actor_kind TEXT NOT NULL
    CHECK (actor_kind IN ('anonymous', 'internal_token', 'system', 'operator')),
  actor_fingerprint TEXT,
  action TEXT NOT NULL,
  outcome TEXT NOT NULL CHECK (outcome IN ('allowed', 'denied')),
  denial_code TEXT,
  http_status INTEGER,
  target_kind TEXT,
  target_uuid TEXT,
  remote_addr_hash TEXT,
  summary TEXT NOT NULL CHECK (length(summary) <= 512),
  payload_json TEXT NOT NULL DEFAULT '{}',
  payload_digest TEXT NOT NULL
    CHECK (length(payload_digest) = 64
           AND payload_digest NOT GLOB '*[^0-9a-f]*'),
  occurred_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  CHECK ((outcome = 'denied' AND denial_code IS NOT NULL)
         OR (outcome = 'allowed' AND denial_code IS NULL)),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid)
);

-- --------------------------------------------------------------------------
-- runtime (9 tables)
-- --------------------------------------------------------------------------

CREATE TABLE mkb_tasks (
  team_uuid TEXT NOT NULL,
  task_uuid TEXT NOT NULL,
  trace_uuid TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  request_intent TEXT NOT NULL,
  creation_fingerprint TEXT NOT NULL,
  audit_bound INTEGER NOT NULL DEFAULT 1 CHECK (audit_bound = 1),
  title TEXT NOT NULL,
  description TEXT,
  priority TEXT NOT NULL DEFAULT 'normal'
    CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
  status TEXT NOT NULL DEFAULT 'queued'
    CHECK (status IN ('queued', 'running', 'cancelling', 'succeeded', 'failed', 'cancelled')),
  row_revision INTEGER NOT NULL DEFAULT 0 CHECK (row_revision >= 0),
  current_generation INTEGER NOT NULL DEFAULT 1 CHECK (current_generation >= 1),
  current_root_execution_uuid TEXT,
  cancel_requested_at TEXT,
  intake_snapshot_uuid TEXT,
  change_set_uuid TEXT,
  cnt_total INTEGER NOT NULL DEFAULT 0 CHECK (cnt_total >= 0),
  cnt_required INTEGER NOT NULL DEFAULT 0 CHECK (cnt_required >= 0),
  cnt_active INTEGER NOT NULL DEFAULT 0 CHECK (cnt_active >= 0),
  cnt_succeeded INTEGER NOT NULL DEFAULT 0 CHECK (cnt_succeeded >= 0),
  cnt_failed INTEGER NOT NULL DEFAULT 0 CHECK (cnt_failed >= 0),
  cnt_cancelled INTEGER NOT NULL DEFAULT 0 CHECK (cnt_cancelled >= 0),
  cnt_skipped INTEGER NOT NULL DEFAULT 0 CHECK (cnt_skipped >= 0),
  result_ref TEXT,
  error_code TEXT,
  error_message TEXT,
  proof_ref TEXT,
  received_at TEXT NOT NULL,
  started_at TEXT,
  completed_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  deleted_at TEXT,
  deleted_actor TEXT,
  deleted_reason TEXT,
  deadline_at TEXT,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (team_uuid, task_uuid),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid)
);

CREATE TABLE mkb_task_audits (
  team_uuid TEXT NOT NULL,
  task_uuid TEXT NOT NULL,
  request_envelope_digest TEXT NOT NULL,
  strict_payload_json TEXT NOT NULL,
  caller_token_fingerprint TEXT NOT NULL,
  received_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (team_uuid, task_uuid),
  FOREIGN KEY (team_uuid, task_uuid)
    REFERENCES mkb_tasks(team_uuid, task_uuid)
);

CREATE TABLE mkb_task_restarts (
  restart_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  restart_scope TEXT NOT NULL
    CHECK (restart_scope IN ('atomic_intake_item', 'full_task')),
  source_task_uuid TEXT NOT NULL,
  source_generation INTEGER NOT NULL CHECK (source_generation >= 1),
  source_root_execution_uuid TEXT,
  intake_item_uuid TEXT,
  intake_revision_uuid TEXT,
  restart_task_uuid TEXT,
  target_generation INTEGER CHECK (target_generation IS NULL OR target_generation >= 1),
  target_root_execution_uuid TEXT,
  causation_trace_uuid TEXT NOT NULL,
  command_fingerprint TEXT NOT NULL,
  admission_outcome TEXT NOT NULL CHECK (admission_outcome IN ('accepted', 'rejected')),
  decision_code TEXT NOT NULL,
  reason TEXT,
  requested_at TEXT NOT NULL,
  decided_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  CHECK (restart_scope <> 'atomic_intake_item' OR intake_item_uuid IS NOT NULL),
  FOREIGN KEY (team_uuid, source_task_uuid)
    REFERENCES mkb_tasks(team_uuid, task_uuid),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid)
);

CREATE TABLE mkb_executions (
  execution_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  task_uuid TEXT NOT NULL,
  trace_uuid TEXT NOT NULL,
  generation INTEGER NOT NULL CHECK (generation >= 1),
  root_execution_uuid TEXT NOT NULL,
  parent_execution_uuid TEXT,
  retry_of_execution_uuid TEXT,
  execution_role TEXT NOT NULL,
  requiredness TEXT NOT NULL DEFAULT 'required'
    CHECK (requiredness IN ('required', 'optional')),
  target_kind TEXT NOT NULL,
  target_uuid TEXT,
  intake_snapshot_uuid TEXT,
  intake_snapshot_digest TEXT,
  workflow_uuid TEXT NOT NULL,
  workflow_revision_uuid TEXT NOT NULL,
  compiled_digest TEXT NOT NULL,
  resolver_decision_digest TEXT NOT NULL,
  domain_binding_digest TEXT NOT NULL,
  s05_binding_digest TEXT NOT NULL,
  -- L4 freeze: retries/recovery must reuse this exact resolved configuration,
  -- rather than re-resolving prompts/models/definitions from current config.
  config_snapshot_ref TEXT NOT NULL,
  config_snapshot_digest TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'created'
    CHECK (status IN ('created', 'ready', 'running', 'waiting', 'succeeded', 'failed', 'cancelling', 'cancelled')),
  row_revision INTEGER NOT NULL DEFAULT 0 CHECK (row_revision >= 0),
  phase_key TEXT,
  waiting_reason TEXT,
  waiting_ref TEXT,
  next_wake_at TEXT,
  current_process_uuid TEXT,
  manifest_ref TEXT,
  manifest_digest TEXT,
  manifest_revision INTEGER NOT NULL DEFAULT 0 CHECK (manifest_revision >= 0),
  total_process_count INTEGER NOT NULL DEFAULT 0 CHECK (total_process_count >= 0),
  active_process_count INTEGER NOT NULL DEFAULT 0 CHECK (active_process_count >= 0),
  succeeded_process_count INTEGER NOT NULL DEFAULT 0 CHECK (succeeded_process_count >= 0),
  failed_process_count INTEGER NOT NULL DEFAULT 0 CHECK (failed_process_count >= 0),
  cancelled_process_count INTEGER NOT NULL DEFAULT 0 CHECK (cancelled_process_count >= 0),
  skipped_process_count INTEGER NOT NULL DEFAULT 0 CHECK (skipped_process_count >= 0),
  total_child_count INTEGER NOT NULL DEFAULT 0 CHECK (total_child_count >= 0),
  active_child_count INTEGER NOT NULL DEFAULT 0 CHECK (active_child_count >= 0),
  succeeded_child_count INTEGER NOT NULL DEFAULT 0 CHECK (succeeded_child_count >= 0),
  failed_child_count INTEGER NOT NULL DEFAULT 0 CHECK (failed_child_count >= 0),
  retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
  cancel_requested_at TEXT,
  cancel_command_revision INTEGER,
  cancel_converged_at TEXT,
  result_ref TEXT,
  publication_proof_ref TEXT,
  final_error_code TEXT,
  final_error_message TEXT,
  terminal_summary_digest TEXT,
  summary_completed_at TEXT,
  phase_history_ref TEXT,
  created_at TEXT NOT NULL,
  started_at TEXT,
  completed_at TEXT,
  updated_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  CHECK (status <> 'waiting' OR (waiting_reason IS NOT NULL AND waiting_ref IS NOT NULL)),
  CHECK (parent_execution_uuid IS NOT NULL OR root_execution_uuid = execution_uuid),
  UNIQUE (team_uuid, execution_uuid),
  FOREIGN KEY (team_uuid, task_uuid)
    REFERENCES mkb_tasks(team_uuid, task_uuid),
  FOREIGN KEY (team_uuid, root_execution_uuid)
    REFERENCES mkb_executions(team_uuid, execution_uuid),
  FOREIGN KEY (team_uuid, parent_execution_uuid)
    REFERENCES mkb_executions(team_uuid, execution_uuid),
  FOREIGN KEY (team_uuid, retry_of_execution_uuid)
    REFERENCES mkb_executions(team_uuid, execution_uuid)
);

CREATE TABLE mkb_processes (
  process_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  execution_uuid TEXT NOT NULL,
  task_uuid TEXT NOT NULL,
  workflow_step_uuid TEXT NOT NULL,
  step_key TEXT NOT NULL,
  process_key TEXT NOT NULL,
  process_contract_version TEXT NOT NULL,
  materialization_key TEXT NOT NULL,
  route_decision_digest TEXT,
  fan_out_item_key TEXT,
  requiredness TEXT NOT NULL DEFAULT 'required'
    CHECK (requiredness IN ('required', 'optional')),
  process_spec_digest TEXT NOT NULL,
  input_manifest_ref TEXT,
  input_manifest_digest TEXT,
  control_snapshot_ref TEXT,
  config_snapshot_ref TEXT NOT NULL,
  config_snapshot_digest TEXT NOT NULL,
  proof_kind TEXT,
  status TEXT NOT NULL DEFAULT 'ready'
    CHECK (status IN ('ready', 'claimed', 'running', 'retry_wait', 'succeeded', 'failed', 'cancelling', 'cancelled')),
  row_revision INTEGER NOT NULL DEFAULT 0 CHECK (row_revision >= 0),
  available_at TEXT NOT NULL,
  priority_rank INTEGER NOT NULL DEFAULT 0,
  deadline_at TEXT,
  claim_token_hash TEXT,
  lease_owner TEXT,
  lease_expires_at TEXT,
  fencing_generation INTEGER NOT NULL DEFAULT 0 CHECK (fencing_generation >= 0),
  heartbeat_at TEXT,
  delivery_count INTEGER NOT NULL DEFAULT 0 CHECK (delivery_count >= 0),
  recovery_count INTEGER NOT NULL DEFAULT 0 CHECK (recovery_count >= 0),
  retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
  max_retries INTEGER NOT NULL DEFAULT 0 CHECK (max_retries >= 0),
  max_recoveries INTEGER NOT NULL DEFAULT 0 CHECK (max_recoveries >= 0),
  next_retry_at TEXT,
  last_failure_retryability INTEGER CHECK (last_failure_retryability IN (0, 1)),
  backoff_policy_json TEXT,
  accepted_outcome_digest TEXT,
  output_manifest_ref TEXT,
  output_manifest_digest TEXT,
  proof_ref TEXT,
  proof_digest TEXT,
  error_class TEXT,
  error_code TEXT,
  error_message TEXT,
  error_details_ref TEXT,
  failure_disposition TEXT,
  cleanup_eligible_at TEXT,
  cleanup_fence_digest TEXT,
  created_at TEXT NOT NULL,
  started_at TEXT,
  completed_at TEXT,
  updated_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  CHECK (status <> 'claimed'
         OR (claim_token_hash IS NOT NULL AND lease_owner IS NOT NULL
             AND lease_expires_at IS NOT NULL)),
  UNIQUE (team_uuid, process_uuid),
  FOREIGN KEY (team_uuid, execution_uuid)
    REFERENCES mkb_executions(team_uuid, execution_uuid),
  FOREIGN KEY (team_uuid, task_uuid)
    REFERENCES mkb_tasks(team_uuid, task_uuid)
);

CREATE TABLE mkb_outbox (
  outbox_id TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  kind TEXT NOT NULL,
  topic TEXT,
  payload_json TEXT NOT NULL,
  payload_digest TEXT NOT NULL
    CHECK (length(payload_digest) = 64
           AND payload_digest NOT GLOB '*[^0-9a-f]*'),
  dedupe_key TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'in_flight', 'done', 'dead')),
  attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  available_at TEXT NOT NULL,
  lease_owner TEXT,
  lease_expires_at TEXT,
  last_error TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid)
);

CREATE TABLE mkb_execution_gates (
  gate_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  task_uuid TEXT NOT NULL,
  execution_uuid TEXT NOT NULL,
  generation INTEGER NOT NULL CHECK (generation >= 1),
  gate_kind TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open'
    CHECK (status IN ('open', 'released', 'rejected', 'superseded')),
  gate_revision INTEGER NOT NULL DEFAULT 0 CHECK (gate_revision >= 0),
  opened_at TEXT NOT NULL,
  terminal_at TEXT,
  workflow_revision_uuid TEXT,
  binding_digest TEXT,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (team_uuid, task_uuid)
    REFERENCES mkb_tasks(team_uuid, task_uuid),
  FOREIGN KEY (team_uuid, execution_uuid)
    REFERENCES mkb_executions(team_uuid, execution_uuid)
);

CREATE TABLE mkb_execution_gate_targets (
  gate_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  target_digest TEXT NOT NULL,
  review_target_json TEXT NOT NULL,
  clean_artifact_digest TEXT NOT NULL,
  preflight_outcome_ref TEXT,
  intake_refs_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (gate_uuid) REFERENCES mkb_execution_gates(gate_uuid),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid)
);

CREATE TABLE mkb_execution_gate_decisions (
  decision_uuid TEXT PRIMARY KEY,
  gate_uuid TEXT NOT NULL,
  team_uuid TEXT NOT NULL,
  expected_gate_revision INTEGER NOT NULL CHECK (expected_gate_revision >= 0),
  action TEXT NOT NULL CHECK (action IN ('approve', 'reject', 'reclean')),
  actor_fingerprint TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  target_digest TEXT NOT NULL,
  decision_digest TEXT NOT NULL,
  created_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (gate_uuid, idempotency_key),
  FOREIGN KEY (gate_uuid) REFERENCES mkb_execution_gates(gate_uuid),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid)
);

-- --------------------------------------------------------------------------
-- registry (14 tables, including model catalog and adapter bindings)
-- --------------------------------------------------------------------------

CREATE TABLE mkb_workflow_registry (
  workflow_uuid TEXT PRIMARY KEY,
  workflow_key TEXT NOT NULL,
  domain_key TEXT NOT NULL DEFAULT 'ls_rag',
  purpose_key TEXT NOT NULL,
  execution_role TEXT NOT NULL,
  selector_key TEXT,
  selector_priority INTEGER NOT NULL DEFAULT 100,
  read_exposure TEXT NOT NULL DEFAULT 'internal'
    CHECK (read_exposure IN ('internal', 'readable')),
  registry_status TEXT NOT NULL DEFAULT 'enabled'
    CHECK (registry_status IN ('enabled', 'disabled', 'deprecated')),
  active_revision_uuid TEXT,
  display_name TEXT,
  description TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  created_by_origin TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE mkb_workflow_revisions (
  workflow_revision_uuid TEXT PRIMARY KEY,
  workflow_uuid TEXT NOT NULL,
  revision_number INTEGER NOT NULL CHECK (revision_number >= 1),
  schema_version TEXT NOT NULL,
  capability_registry_digest TEXT NOT NULL,
  registration_source_kind TEXT,
  registration_module TEXT,
  source_commit_digest TEXT,
  migration_key TEXT,
  registration_fingerprint TEXT NOT NULL,
  canonical_definition_digest TEXT NOT NULL,
  compiled_digest TEXT NOT NULL,
  registered_at TEXT NOT NULL,
  activated_at TEXT,
  registration_trace_uuid TEXT,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (workflow_uuid) REFERENCES mkb_workflow_registry(workflow_uuid)
);

CREATE TABLE mkb_workflow_steps (
  workflow_step_uuid TEXT PRIMARY KEY,
  workflow_revision_uuid TEXT NOT NULL,
  step_key TEXT NOT NULL,
  step_kind TEXT NOT NULL
    CHECK (step_kind IN ('start', 'process', 'control', 'join', 'terminal')),
  process_key TEXT,
  process_contract_version TEXT,
  phase_key TEXT,
  requiredness TEXT NOT NULL DEFAULT 'required'
    CHECK (requiredness IN ('required', 'optional')),
  terminal_kind TEXT CHECK (terminal_kind IN ('success', 'failure', 'cancelled', 'noop')),
  order_hint INTEGER NOT NULL DEFAULT 0,
  display_name TEXT,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  CHECK ((step_kind = 'process' AND process_key IS NOT NULL
          AND process_contract_version IS NOT NULL)
         OR (step_kind <> 'process' AND process_key IS NULL
             AND process_contract_version IS NULL)),
  CHECK ((step_kind = 'terminal' AND terminal_kind IS NOT NULL)
         OR (step_kind <> 'terminal' AND terminal_kind IS NULL)),
  FOREIGN KEY (workflow_revision_uuid)
    REFERENCES mkb_workflow_revisions(workflow_revision_uuid)
);

CREATE TABLE mkb_workflow_routes (
  workflow_route_uuid TEXT PRIMARY KEY,
  workflow_revision_uuid TEXT NOT NULL,
  route_key TEXT NOT NULL,
  from_step_uuid TEXT NOT NULL,
  to_step_uuid TEXT NOT NULL,
  route_kind TEXT NOT NULL
    CHECK (route_kind IN ('normal', 'branch', 'fan_out', 'join', 'terminal')),
  outcome_selector TEXT NOT NULL
    CHECK (outcome_selector IN ('always', 'succeeded', 'failed', 'cancelled', 'skipped')),
  priority INTEGER NOT NULL DEFAULT 100,
  guard_group_key TEXT,
  join_mode TEXT NOT NULL DEFAULT 'none'
    CHECK (join_mode IN ('none', 'all_required', 'all_terminal')),
  predecessor_requiredness TEXT
    CHECK (predecessor_requiredness IS NULL
           OR predecessor_requiredness IN ('required', 'optional')),
  payload_extra TEXT NOT NULL DEFAULT '{}',
  CHECK (from_step_uuid <> to_step_uuid),
  CHECK ((route_kind = 'join') OR join_mode = 'none'),
  FOREIGN KEY (workflow_revision_uuid)
    REFERENCES mkb_workflow_revisions(workflow_revision_uuid),
  FOREIGN KEY (from_step_uuid) REFERENCES mkb_workflow_steps(workflow_step_uuid),
  FOREIGN KEY (to_step_uuid) REFERENCES mkb_workflow_steps(workflow_step_uuid)
);

CREATE TABLE mkb_workflow_bindings (
  workflow_binding_uuid TEXT PRIMARY KEY,
  workflow_revision_uuid TEXT NOT NULL,
  workflow_step_uuid TEXT NOT NULL,
  binding_kind TEXT NOT NULL
    CHECK (binding_kind IN ('context', 'input', 'output', 'parameter')),
  slot_name TEXT NOT NULL,
  value_type TEXT NOT NULL
    CHECK (value_type IN ('bool', 'int', 'real', 'text', 'uuid', 'ref')),
  schema_ref TEXT,
  required INTEGER NOT NULL DEFAULT 1 CHECK (required IN (0, 1)),
  multiplicity TEXT NOT NULL DEFAULT 'one' CHECK (multiplicity IN ('one', 'many')),
  binding_source_kind TEXT NOT NULL CHECK (binding_source_kind IN
    ('execution_context', 'intake_snapshot', 'prior_output', 'control_value',
     'registry_ref', 'literal')),
  binding_source_step_uuid TEXT,
  binding_source_port TEXT,
  binding_source_ref_key TEXT,
  value_bool INTEGER CHECK (value_bool IN (0, 1)),
  value_int INTEGER,
  value_real REAL,
  value_text TEXT,
  value_uuid TEXT,
  value_ref TEXT,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  CHECK (
    (binding_source_kind = 'literal' AND
      (CASE WHEN value_bool IS NOT NULL THEN 1 ELSE 0 END +
       CASE WHEN value_int IS NOT NULL THEN 1 ELSE 0 END +
       CASE WHEN value_real IS NOT NULL THEN 1 ELSE 0 END +
       CASE WHEN value_text IS NOT NULL THEN 1 ELSE 0 END +
       CASE WHEN value_uuid IS NOT NULL THEN 1 ELSE 0 END +
       CASE WHEN value_ref IS NOT NULL THEN 1 ELSE 0 END) = 1)
    OR
    (binding_source_kind <> 'literal' AND value_bool IS NULL AND value_int IS NULL
      AND value_real IS NULL AND value_text IS NULL AND value_uuid IS NULL
      AND value_ref IS NULL)
  ),
  FOREIGN KEY (workflow_revision_uuid)
    REFERENCES mkb_workflow_revisions(workflow_revision_uuid),
  FOREIGN KEY (workflow_step_uuid) REFERENCES mkb_workflow_steps(workflow_step_uuid),
  FOREIGN KEY (binding_source_step_uuid) REFERENCES mkb_workflow_steps(workflow_step_uuid)
);

CREATE TABLE mkb_workflow_controls (
  workflow_control_uuid TEXT PRIMARY KEY,
  workflow_revision_uuid TEXT NOT NULL,
  scope_type TEXT NOT NULL CHECK (scope_type IN ('revision', 'step', 'route')),
  workflow_step_uuid TEXT,
  workflow_route_uuid TEXT,
  timeout_ms INTEGER CHECK (timeout_ms IS NULL OR timeout_ms > 0),
  lease_duration_ms INTEGER CHECK (lease_duration_ms IS NULL OR lease_duration_ms > 0),
  heartbeat_interval_ms INTEGER CHECK (heartbeat_interval_ms IS NULL OR heartbeat_interval_ms > 0),
  max_retries INTEGER CHECK (max_retries IS NULL OR max_retries >= 0),
  retry_policy TEXT CHECK (retry_policy IS NULL
    OR retry_policy IN ('none', 'transient_only', 'contract_allowlist')),
  backoff_kind TEXT,
  backoff_initial_ms INTEGER CHECK (backoff_initial_ms IS NULL OR backoff_initial_ms > 0),
  backoff_max_ms INTEGER CHECK (backoff_max_ms IS NULL OR backoff_max_ms > 0),
  backoff_multiplier REAL CHECK (backoff_multiplier IS NULL OR backoff_multiplier >= 1.0),
  jitter_pct REAL CHECK (jitter_pct IS NULL OR (jitter_pct >= 0.0 AND jitter_pct <= 1.0)),
  max_recoveries INTEGER CHECK (max_recoveries IS NULL OR max_recoveries >= 0),
  indeterminate_side_effect_policy TEXT CHECK (indeterminate_side_effect_policy IS NULL
    OR indeterminate_side_effect_policy IN ('fail', 'verify_then_retry')),
  cancel_mode TEXT CHECK (cancel_mode IS NULL
    OR cancel_mode IN ('cooperative', 'fence_only', 'compensate')),
  cancel_grace_ms INTEGER CHECK (cancel_grace_ms IS NULL OR cancel_grace_ms > 0),
  case_mode TEXT,
  purge_mode TEXT,
  failure_policy TEXT,
  concurrency_limit INTEGER CHECK (concurrency_limit IS NULL OR concurrency_limit > 0),
  fan_out_limit INTEGER CHECK (fan_out_limit IS NULL OR fan_out_limit > 0),
  deadline_mode TEXT NOT NULL DEFAULT 'latest_claim_time'
    CHECK (deadline_mode = 'latest_claim_time'),
  payload_extra TEXT NOT NULL DEFAULT '{}',
  CHECK ((scope_type = 'revision' AND workflow_step_uuid IS NULL AND workflow_route_uuid IS NULL)
         OR (scope_type = 'step' AND workflow_step_uuid IS NOT NULL AND workflow_route_uuid IS NULL)
         OR (scope_type = 'route' AND workflow_step_uuid IS NULL AND workflow_route_uuid IS NOT NULL)),
  CHECK (heartbeat_interval_ms IS NULL OR lease_duration_ms IS NULL
         OR heartbeat_interval_ms < lease_duration_ms),
  CHECK (backoff_initial_ms IS NULL OR backoff_max_ms IS NULL
         OR backoff_initial_ms <= backoff_max_ms),
  FOREIGN KEY (workflow_revision_uuid)
    REFERENCES mkb_workflow_revisions(workflow_revision_uuid),
  FOREIGN KEY (workflow_step_uuid) REFERENCES mkb_workflow_steps(workflow_step_uuid),
  FOREIGN KEY (workflow_route_uuid) REFERENCES mkb_workflow_routes(workflow_route_uuid)
);

CREATE TABLE mkb_workflow_guards (
  workflow_guard_uuid TEXT PRIMARY KEY,
  workflow_revision_uuid TEXT NOT NULL,
  scope_type TEXT NOT NULL CHECK (scope_type IN ('route', 'terminal', 'proof')),
  scope_key TEXT NOT NULL,
  guard_group_key TEXT NOT NULL,
  group_mode TEXT NOT NULL CHECK (group_mode IN ('all', 'any')),
  order_index INTEGER NOT NULL CHECK (order_index >= 0),
  predicate_type TEXT NOT NULL,
  operand_kind TEXT NOT NULL,
  operand_ref TEXT NOT NULL,
  operator TEXT NOT NULL CHECK (operator IN
    ('eq', 'ne', 'lt', 'lte', 'gt', 'gte', 'exists', 'not_exists',
     'in_registered_set', 'digest_eq', 'schema_valid', 'proof_valid')),
  expected_type TEXT,
  expected_bool INTEGER CHECK (expected_bool IN (0, 1)),
  expected_int INTEGER,
  expected_real REAL,
  expected_text TEXT,
  expected_uuid TEXT,
  expected_ref TEXT,
  failure_code TEXT NOT NULL,
  failure_disposition TEXT NOT NULL
    CHECK (failure_disposition IN ('route_false', 'process_failed', 'execution_failed')),
  payload_extra TEXT NOT NULL DEFAULT '{}',
  CHECK (
    (operator IN ('exists', 'not_exists', 'schema_valid', 'proof_valid')
      AND expected_type IS NULL AND expected_bool IS NULL AND expected_int IS NULL
      AND expected_real IS NULL AND expected_text IS NULL AND expected_uuid IS NULL
      AND expected_ref IS NULL)
    OR
    (operator NOT IN ('exists', 'not_exists', 'schema_valid', 'proof_valid')
      AND expected_type IS NOT NULL
      AND (CASE WHEN expected_bool IS NOT NULL THEN 1 ELSE 0 END +
           CASE WHEN expected_int IS NOT NULL THEN 1 ELSE 0 END +
           CASE WHEN expected_real IS NOT NULL THEN 1 ELSE 0 END +
           CASE WHEN expected_text IS NOT NULL THEN 1 ELSE 0 END +
           CASE WHEN expected_uuid IS NOT NULL THEN 1 ELSE 0 END +
           CASE WHEN expected_ref IS NOT NULL THEN 1 ELSE 0 END) = 1)
  ),
  FOREIGN KEY (workflow_revision_uuid)
    REFERENCES mkb_workflow_revisions(workflow_revision_uuid)
);

CREATE TABLE mkb_intake_semantic_definitions (
  semantic_key TEXT NOT NULL,
  definition_version TEXT NOT NULL,
  value_kind TEXT NOT NULL CHECK (value_kind IN ('bool', 'int', 'real', 'text', 'ref')),
  schema_ref TEXT,
  schema_version TEXT,
  fingerprint_participation INTEGER NOT NULL DEFAULT 0 CHECK (fingerprint_participation IN (0, 1)),
  route_fact_key TEXT,
  canonicalizer_ref TEXT,
  canonicalizer_version TEXT,
  definition_digest TEXT NOT NULL,
  definition_body_json TEXT,
  registered_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (semantic_key, definition_version)
);

CREATE TABLE mkb_intake_action_definitions (
  action_key TEXT NOT NULL,
  definition_version TEXT NOT NULL,
  allowed_from_mask TEXT NOT NULL,
  required_proof_kind TEXT,
  precondition_class TEXT NOT NULL,
  core_effect_mask TEXT NOT NULL,
  route_fact_key TEXT,
  idempotency_scope TEXT NOT NULL,
  definition_digest TEXT NOT NULL,
  definition_body_json TEXT,
  registered_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (action_key, definition_version)
);

CREATE TABLE mkb_source_kind_definitions (
  source_kind TEXT NOT NULL,
  definition_version TEXT NOT NULL,
  definition_digest TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'disabled', 'deprecated')),
  descriptor_schema_ref TEXT NOT NULL,
  descriptor_schema_digest TEXT NOT NULL,
  config_schema_ref TEXT,
  config_schema_digest TEXT,
  cardinality TEXT NOT NULL CHECK (cardinality IN ('single', 'collection')),
  scope_profile_ref TEXT,
  completeness_profile_ref TEXT,
  acquisition_capability_digest TEXT,
  decode_capability_digest TEXT,
  clean_capability_digest TEXT,
  media_rules_ref TEXT,
  encoding_profile_ref TEXT,
  byte_budget_ref TEXT,
  external_key_normalizer_ref TEXT,
  external_key_normalizer_version TEXT,
  singleton_key TEXT,
  duplicate_policy TEXT,
  secret_slot_specs_ref TEXT,
  egress_policy_ref TEXT,
  auth_policy_ref TEXT,
  preflight_profile_key TEXT,
  eligibility_digest TEXT,
  definition_body_json TEXT,
  registered_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (source_kind, definition_version)
);

CREATE TABLE mkb_preflight_profile_definitions (
  profile_key TEXT NOT NULL,
  definition_version TEXT NOT NULL,
  check_set_digest TEXT NOT NULL,
  definition_digest TEXT NOT NULL,
  definition_body_json TEXT,
  registered_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (profile_key, definition_version)
);

CREATE TABLE mkb_structure_schema_definitions (
  schema_key TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  schema_digest TEXT NOT NULL,
  schema_dialect TEXT NOT NULL,
  deterministic_kernel_schema_digest TEXT NOT NULL,
  governed_extension_schema_digest TEXT,
  semantic_invariant_manifest_digest TEXT NOT NULL,
  validator_refs_json TEXT NOT NULL DEFAULT '[]',
  artifact_type TEXT NOT NULL,
  media_contracts_digest TEXT NOT NULL,
  compatibility_json TEXT,
  registration_origin TEXT NOT NULL,
  definition_body_json TEXT,
  registered_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (schema_key, schema_version)
);

CREATE TABLE mkb_construction_schema_definitions (
  schema_key TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  schema_digest TEXT NOT NULL,
  structure_schema_range TEXT NOT NULL,
  content_full_recipe_version TEXT NOT NULL,
  channel_contracts_digest TEXT NOT NULL,
  semantic_invariant_manifest_digest TEXT NOT NULL,
  validator_refs_json TEXT NOT NULL DEFAULT '[]',
  media_contracts_digest TEXT NOT NULL,
  registration_origin TEXT NOT NULL,
  definition_body_json TEXT,
  registered_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (schema_key, schema_version)
);

CREATE TABLE mkb_prompt_hash_pointers (
  prompt_key TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  git_relative_path TEXT NOT NULL,
  content_sha256 TEXT NOT NULL
    CHECK (length(content_sha256) = 64
           AND content_sha256 NOT GLOB '*[^0-9a-f]*'),
  registered_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (prompt_key, prompt_version)
);

CREATE TABLE mkb_model_catalog (
  model_uuid TEXT PRIMARY KEY,
  model_key TEXT NOT NULL,
  model_version TEXT NOT NULL,
  modality TEXT NOT NULL CHECK (modality IN
    ('embed', 'rerank', 'generate', 'multimodal_embed')),
  provider_family TEXT NOT NULL,
  default_dimension INTEGER CHECK (default_dimension IS NULL OR default_dimension > 0),
  definition_digest TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'disabled', 'deprecated')),
  display_name TEXT,
  registered_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE mkb_adapter_bindings (
  binding_uuid TEXT PRIMARY KEY,
  capability_key TEXT NOT NULL
    CHECK (capability_key IN ('embed', 'rerank', 'structured_generate', 'text_generate')),
  adapter_kind TEXT NOT NULL,
  model_key TEXT NOT NULL,
  model_version TEXT NOT NULL,
  priority INTEGER NOT NULL DEFAULT 100,
  team_uuid TEXT,
  enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
  binding_digest TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid),
  FOREIGN KEY (model_key, model_version)
    REFERENCES mkb_model_catalog(model_key, model_version)
);

-- --------------------------------------------------------------------------
-- object (3 tables).  Object bytes live under data/objects/, never in these
-- rows; all locations below are opaque logical handles/refs.
-- --------------------------------------------------------------------------

CREATE TABLE mkb_stored_objects (
  stored_object_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  digest_algorithm TEXT NOT NULL DEFAULT 'sha256'
    CHECK (digest_algorithm = 'sha256'),
  content_digest TEXT NOT NULL
    CHECK (length(content_digest) = 64
           AND content_digest NOT GLOB '*[^0-9a-f]*'),
  size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
  media_type TEXT,
  storage_backend TEXT NOT NULL DEFAULT 'local_fs',
  created_at TEXT NOT NULL,
  tombstoned_at TEXT,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (team_uuid, stored_object_uuid),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid)
);

CREATE TABLE mkb_object_references (
  reference_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  stored_object_uuid TEXT NOT NULL,
  purpose TEXT NOT NULL CHECK (purpose IN
    ('intake_snapshot_artifact', 'intake_revision_artifact', 'clean_candidate',
     'gate_evidence', 'generation_artifact', 'process_io', 'operator_hold',
     'backup_hold')),
  owner_kind TEXT NOT NULL,
  owner_uuid TEXT NOT NULL,
  expected_digest TEXT NOT NULL,
  expected_size INTEGER NOT NULL CHECK (expected_size >= 0),
  created_at TEXT NOT NULL,
  released_at TEXT,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid),
  FOREIGN KEY (team_uuid, stored_object_uuid)
    REFERENCES mkb_stored_objects(team_uuid, stored_object_uuid)
);

CREATE TABLE mkb_object_delete_proofs (
  delete_proof_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  stored_object_uuid TEXT NOT NULL,
  content_digest TEXT NOT NULL,
  size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
  delete_fence_digest TEXT NOT NULL,
  unlinked_at TEXT NOT NULL,
  scanner_id TEXT,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid),
  FOREIGN KEY (team_uuid, stored_object_uuid)
    REFERENCES mkb_stored_objects(team_uuid, stored_object_uuid)
);

-- --------------------------------------------------------------------------
-- intake (15 tables: ten canonical truths and five supporting ledgers)
-- --------------------------------------------------------------------------

CREATE TABLE mkb_intake_sources (
  team_uuid TEXT NOT NULL,
  intake_source_uuid TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  source_kind_definition_version TEXT NOT NULL,
  source_kind_definition_digest TEXT NOT NULL,
  source_descriptor_ref TEXT NOT NULL,
  source_descriptor_digest TEXT NOT NULL,
  connector_config_ref TEXT,
  secret_ref TEXT,
  accepts_new_snapshots INTEGER NOT NULL DEFAULT 1 CHECK (accepts_new_snapshots IN (0, 1)),
  row_revision INTEGER NOT NULL DEFAULT 0 CHECK (row_revision >= 0),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (team_uuid, intake_source_uuid),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid),
  FOREIGN KEY (source_kind, source_kind_definition_version)
    REFERENCES mkb_source_kind_definitions(source_kind, definition_version)
);

CREATE TABLE mkb_intake_snapshots (
  team_uuid TEXT NOT NULL,
  intake_snapshot_uuid TEXT NOT NULL,
  intake_source_uuid TEXT NOT NULL,
  observation_key TEXT NOT NULL,
  observation_fingerprint TEXT NOT NULL,
  candidate_root_digest TEXT NOT NULL,
  completeness TEXT NOT NULL CHECK (completeness IN ('complete', 'partial')),
  authoritative_scope_ref TEXT,
  source_validator_evidence_ref TEXT,
  preflight_outcome_ref TEXT,
  preflight_outcome_digest TEXT,
  s05_binding_digest TEXT,
  observed_at TEXT NOT NULL,
  accepted_at TEXT NOT NULL,
  producer_execution_uuid TEXT,
  raw_artifact_uuid TEXT,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (team_uuid, intake_snapshot_uuid),
  UNIQUE (team_uuid, intake_source_uuid, observation_key),
  FOREIGN KEY (team_uuid, intake_source_uuid)
    REFERENCES mkb_intake_sources(team_uuid, intake_source_uuid),
  -- Snapshot.raw_artifact and Artifact.owner_snapshot form the intentional
  -- immutable TX-05 cycle, so both sides are checked at commit, not mid-UoW.
  FOREIGN KEY (team_uuid, raw_artifact_uuid)
    REFERENCES mkb_intake_artifacts(team_uuid, intake_artifact_uuid)
    DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE mkb_intake_items (
  team_uuid TEXT NOT NULL,
  intake_item_uuid TEXT NOT NULL,
  intake_source_uuid TEXT NOT NULL,
  normalized_external_key TEXT NOT NULL,
  lifecycle_state TEXT NOT NULL DEFAULT 'active'
    CHECK (lifecycle_state IN ('active', 'deactivated', 'deleted')),
  latest_revision_uuid TEXT,
  serving_revision_uuid TEXT,
  row_revision INTEGER NOT NULL DEFAULT 0 CHECK (row_revision >= 0),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  deactivated_at TEXT,
  deleted_at TEXT,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (team_uuid, intake_item_uuid),
  UNIQUE (team_uuid, intake_source_uuid, normalized_external_key),
  CHECK (lifecycle_state = 'active' OR serving_revision_uuid IS NULL),
  FOREIGN KEY (team_uuid, intake_source_uuid)
    REFERENCES mkb_intake_sources(team_uuid, intake_source_uuid)
);

CREATE TABLE mkb_intake_revisions (
  team_uuid TEXT NOT NULL,
  intake_revision_uuid TEXT NOT NULL,
  intake_item_uuid TEXT NOT NULL,
  revision_ordinal INTEGER NOT NULL CHECK (revision_ordinal >= 1),
  predecessor_revision_uuid TEXT,
  revision_fingerprint TEXT NOT NULL,
  creation_action_key TEXT,
  creation_action_version TEXT,
  source_snapshot_uuid TEXT NOT NULL,
  created_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (team_uuid, intake_revision_uuid),
  UNIQUE (team_uuid, intake_item_uuid, revision_ordinal),
  UNIQUE (team_uuid, intake_item_uuid, revision_fingerprint),
  FOREIGN KEY (team_uuid, intake_item_uuid)
    REFERENCES mkb_intake_items(team_uuid, intake_item_uuid),
  FOREIGN KEY (team_uuid, predecessor_revision_uuid)
    REFERENCES mkb_intake_revisions(team_uuid, intake_revision_uuid),
  FOREIGN KEY (team_uuid, source_snapshot_uuid)
    REFERENCES mkb_intake_snapshots(team_uuid, intake_snapshot_uuid),
  FOREIGN KEY (creation_action_key, creation_action_version)
    REFERENCES mkb_intake_action_definitions(action_key, definition_version)
);

CREATE TABLE mkb_intake_artifacts (
  team_uuid TEXT NOT NULL,
  intake_artifact_uuid TEXT NOT NULL,
  owner_snapshot_uuid TEXT,
  owner_revision_uuid TEXT,
  artifact_role TEXT NOT NULL,
  media_type TEXT NOT NULL,
  digest_algorithm TEXT NOT NULL DEFAULT 'sha256'
    CHECK (digest_algorithm = 'sha256'),
  content_digest TEXT NOT NULL
    CHECK (length(content_digest) = 64
           AND content_digest NOT GLOB '*[^0-9a-f]*'),
  size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
  logical_handle TEXT NOT NULL CHECK (logical_handle NOT LIKE '/%'),
  stored_object_uuid TEXT,
  producer_execution_uuid TEXT,
  producer_process_uuid TEXT,
  retention_class_ref TEXT,
  created_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (team_uuid, intake_artifact_uuid),
  CHECK ((owner_snapshot_uuid IS NOT NULL AND owner_revision_uuid IS NULL)
         OR (owner_snapshot_uuid IS NULL AND owner_revision_uuid IS NOT NULL)),
  FOREIGN KEY (team_uuid, owner_snapshot_uuid)
    REFERENCES mkb_intake_snapshots(team_uuid, intake_snapshot_uuid)
    DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (team_uuid, owner_revision_uuid)
    REFERENCES mkb_intake_revisions(team_uuid, intake_revision_uuid),
  FOREIGN KEY (team_uuid, stored_object_uuid)
    REFERENCES mkb_stored_objects(team_uuid, stored_object_uuid)
);

CREATE TABLE mkb_intake_snapshot_memberships (
  team_uuid TEXT NOT NULL,
  intake_snapshot_uuid TEXT NOT NULL,
  member_ordinal INTEGER NOT NULL CHECK (member_ordinal >= 0),
  normalized_external_key TEXT NOT NULL,
  intake_item_uuid TEXT,
  observed_revision_uuid TEXT,
  decision_kind TEXT NOT NULL,
  required INTEGER NOT NULL DEFAULT 1 CHECK (required IN (0, 1)),
  decision_digest TEXT NOT NULL,
  created_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (team_uuid, intake_snapshot_uuid, member_ordinal),
  UNIQUE (team_uuid, intake_snapshot_uuid, normalized_external_key),
  FOREIGN KEY (team_uuid, intake_snapshot_uuid)
    REFERENCES mkb_intake_snapshots(team_uuid, intake_snapshot_uuid),
  FOREIGN KEY (team_uuid, intake_item_uuid)
    REFERENCES mkb_intake_items(team_uuid, intake_item_uuid),
  FOREIGN KEY (team_uuid, observed_revision_uuid)
    REFERENCES mkb_intake_revisions(team_uuid, intake_revision_uuid)
);

CREATE TABLE mkb_intake_revision_semantics (
  team_uuid TEXT NOT NULL,
  intake_revision_uuid TEXT NOT NULL,
  semantic_key TEXT NOT NULL,
  definition_version TEXT NOT NULL,
  value_digest TEXT NOT NULL,
  value_kind TEXT NOT NULL CHECK (value_kind IN ('bool', 'int', 'real', 'text', 'artifact_ref')),
  value_bool INTEGER CHECK (value_bool IN (0, 1)),
  value_int INTEGER,
  value_real REAL,
  value_text TEXT,
  value_artifact_uuid TEXT,
  created_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (team_uuid, intake_revision_uuid, semantic_key),
  CHECK (
    (value_kind = 'bool' AND value_bool IS NOT NULL AND value_int IS NULL
      AND value_real IS NULL AND value_text IS NULL AND value_artifact_uuid IS NULL)
    OR (value_kind = 'int' AND value_bool IS NULL AND value_int IS NOT NULL
      AND value_real IS NULL AND value_text IS NULL AND value_artifact_uuid IS NULL)
    OR (value_kind = 'real' AND value_bool IS NULL AND value_int IS NULL
      AND value_real IS NOT NULL AND value_text IS NULL AND value_artifact_uuid IS NULL)
    OR (value_kind = 'text' AND value_bool IS NULL AND value_int IS NULL
      AND value_real IS NULL AND value_text IS NOT NULL AND value_artifact_uuid IS NULL)
    OR (value_kind = 'artifact_ref' AND value_bool IS NULL AND value_int IS NULL
      AND value_real IS NULL AND value_text IS NULL AND value_artifact_uuid IS NOT NULL)
  ),
  FOREIGN KEY (team_uuid, intake_revision_uuid)
    REFERENCES mkb_intake_revisions(team_uuid, intake_revision_uuid),
  FOREIGN KEY (semantic_key, definition_version)
    REFERENCES mkb_intake_semantic_definitions(semantic_key, definition_version),
  FOREIGN KEY (team_uuid, value_artifact_uuid)
    REFERENCES mkb_intake_artifacts(team_uuid, intake_artifact_uuid)
);

CREATE TABLE mkb_intake_item_transitions (
  transition_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  intake_item_uuid TEXT NOT NULL,
  action_key TEXT NOT NULL,
  action_version TEXT NOT NULL,
  before_lifecycle TEXT NOT NULL CHECK (before_lifecycle IN ('active', 'deactivated', 'deleted')),
  after_lifecycle TEXT NOT NULL CHECK (after_lifecycle IN ('active', 'deactivated', 'deleted')),
  before_latest_revision_uuid TEXT,
  after_latest_revision_uuid TEXT,
  before_serving_revision_uuid TEXT,
  after_serving_revision_uuid TEXT,
  item_revision_before INTEGER NOT NULL CHECK (item_revision_before >= 0),
  item_revision_after INTEGER NOT NULL CHECK (item_revision_after >= 0),
  causation_task_uuid TEXT,
  causation_execution_uuid TEXT,
  causation_process_uuid TEXT,
  proof_ref TEXT,
  proof_digest TEXT,
  policy_ref TEXT,
  policy_version TEXT,
  transition_fence TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (team_uuid, intake_item_uuid)
    REFERENCES mkb_intake_items(team_uuid, intake_item_uuid),
  FOREIGN KEY (action_key, action_version)
    REFERENCES mkb_intake_action_definitions(action_key, definition_version)
);

CREATE TABLE mkb_intake_candidate_sets (
  candidate_set_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  intake_source_uuid TEXT NOT NULL,
  producer_execution_uuid TEXT NOT NULL,
  producer_process_uuid TEXT,
  producer_fencing_generation INTEGER,
  source_kind_definition_digest TEXT NOT NULL,
  acquisition_capability_digest TEXT,
  s05_binding_digest TEXT NOT NULL,
  observation_key TEXT NOT NULL,
  observation_fingerprint TEXT NOT NULL,
  authoritative_scope_ref TEXT,
  completeness TEXT NOT NULL CHECK (completeness IN ('complete', 'partial')),
  expected_member_count INTEGER CHECK (expected_member_count IS NULL OR expected_member_count >= 0),
  observed_member_count INTEGER NOT NULL DEFAULT 0 CHECK (observed_member_count >= 0),
  accepted_member_count INTEGER NOT NULL DEFAULT 0 CHECK (accepted_member_count >= 0),
  rejected_member_count INTEGER NOT NULL DEFAULT 0 CHECK (rejected_member_count >= 0),
  duplicate_member_count INTEGER NOT NULL DEFAULT 0 CHECK (duplicate_member_count >= 0),
  expected_page_count INTEGER CHECK (expected_page_count IS NULL OR expected_page_count >= 0),
  observed_page_count INTEGER NOT NULL DEFAULT 0 CHECK (observed_page_count >= 0),
  expected_bytes INTEGER CHECK (expected_bytes IS NULL OR expected_bytes >= 0),
  observed_bytes INTEGER NOT NULL DEFAULT 0 CHECK (observed_bytes >= 0),
  root_digest TEXT,
  preflight_outcome_ref TEXT,
  preflight_outcome_digest TEXT,
  staging_state TEXT NOT NULL DEFAULT 'open'
    CHECK (staging_state IN ('open', 'sealed', 'accepted', 'abandoned')),
  seal_at TEXT,
  expiry_at TEXT,
  accepted_snapshot_uuid TEXT,
  row_revision INTEGER NOT NULL DEFAULT 0 CHECK (row_revision >= 0),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (team_uuid, producer_execution_uuid),
  FOREIGN KEY (team_uuid, intake_source_uuid)
    REFERENCES mkb_intake_sources(team_uuid, intake_source_uuid),
  FOREIGN KEY (team_uuid, accepted_snapshot_uuid)
    REFERENCES mkb_intake_snapshots(team_uuid, intake_snapshot_uuid)
);

CREATE TABLE mkb_intake_candidate_pages (
  candidate_set_uuid TEXT NOT NULL,
  page_ordinal INTEGER NOT NULL CHECK (page_ordinal >= 0),
  team_uuid TEXT NOT NULL,
  member_first_ordinal INTEGER NOT NULL CHECK (member_first_ordinal >= 0),
  member_last_ordinal INTEGER NOT NULL CHECK (member_last_ordinal >= member_first_ordinal),
  ordered_member_digests_ref TEXT,
  page_digest TEXT NOT NULL,
  sealed_payload_ref TEXT,
  staged_artifact_refs_json TEXT NOT NULL DEFAULT '[]',
  validation_refs_json TEXT NOT NULL DEFAULT '[]',
  rejection_refs_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (candidate_set_uuid, page_ordinal),
  FOREIGN KEY (candidate_set_uuid) REFERENCES mkb_intake_candidate_sets(candidate_set_uuid),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid)
);

CREATE TABLE mkb_intake_change_sets (
  change_set_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  intake_snapshot_uuid TEXT NOT NULL,
  change_set_digest TEXT NOT NULL,
  created_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (team_uuid, intake_snapshot_uuid),
  UNIQUE (team_uuid, intake_snapshot_uuid, change_set_digest),
  FOREIGN KEY (team_uuid, intake_snapshot_uuid)
    REFERENCES mkb_intake_snapshots(team_uuid, intake_snapshot_uuid)
);

CREATE TABLE mkb_intake_change_set_facts (
  fact_uuid TEXT PRIMARY KEY,
  change_set_uuid TEXT NOT NULL,
  team_uuid TEXT NOT NULL,
  fact_kind TEXT NOT NULL,
  fact_ordinal INTEGER NOT NULL CHECK (fact_ordinal >= 0),
  intake_item_uuid TEXT,
  intake_revision_uuid TEXT,
  semantic_key TEXT,
  semantic_definition_version TEXT,
  absence_key TEXT,
  fact_digest TEXT NOT NULL,
  created_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (change_set_uuid, fact_ordinal),
  FOREIGN KEY (change_set_uuid) REFERENCES mkb_intake_change_sets(change_set_uuid),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid),
  FOREIGN KEY (team_uuid, intake_item_uuid)
    REFERENCES mkb_intake_items(team_uuid, intake_item_uuid),
  FOREIGN KEY (team_uuid, intake_revision_uuid)
    REFERENCES mkb_intake_revisions(team_uuid, intake_revision_uuid),
  FOREIGN KEY (semantic_key, semantic_definition_version)
    REFERENCES mkb_intake_semantic_definitions(semantic_key, definition_version)
);

CREATE TABLE mkb_intake_repair_intents (
  intent_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  invariant_kind TEXT NOT NULL,
  target_kind TEXT NOT NULL,
  target_uuid TEXT NOT NULL,
  observed_fence TEXT,
  allowed_repair_kind TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open'
    CHECK (status IN ('open', 'resolved', 'abandoned')),
  causation_trace_uuid TEXT,
  causation_task_uuid TEXT,
  causation_execution_uuid TEXT,
  causation_process_uuid TEXT,
  resolved_evidence_ref TEXT,
  resolved_at TEXT,
  created_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid)
);

CREATE TABLE mkb_intake_cleanup_intents (
  intent_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  policy_ref TEXT NOT NULL,
  target_kind TEXT NOT NULL,
  target_ref TEXT NOT NULL,
  required_substrate_set_digest TEXT NOT NULL,
  hold_refs_json TEXT NOT NULL DEFAULT '[]',
  reference_snapshot_ref TEXT,
  status TEXT NOT NULL DEFAULT 'open'
    CHECK (status IN ('open', 'completed', 'abandoned')),
  requested_trace_uuid TEXT,
  requested_at TEXT NOT NULL,
  completed_at TEXT,
  completion_projection_ref TEXT,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid)
);

CREATE TABLE mkb_intake_cleanup_proofs (
  proof_uuid TEXT PRIMARY KEY,
  intent_uuid TEXT NOT NULL,
  team_uuid TEXT NOT NULL,
  substrate_kind TEXT NOT NULL,
  target_ref TEXT NOT NULL,
  target_digest TEXT,
  proof_kind TEXT NOT NULL,
  proof_digest TEXT NOT NULL,
  producer_execution_uuid TEXT,
  producer_process_uuid TEXT,
  verified_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (intent_uuid) REFERENCES mkb_intake_cleanup_intents(intent_uuid),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid)
);

-- --------------------------------------------------------------------------
-- generation (4 immutable/CAS-ledger tables)
-- --------------------------------------------------------------------------

CREATE TABLE mkb_generation_artifacts (
  generation_artifact_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  artifact_type TEXT NOT NULL CHECK (artifact_type IN
    ('structure_document', 'retrieval_block_projection',
     'structure_validation_report', 'construction_document',
     'dual_channel_projection', 'construction_validation_report')),
  artifact_ordinal INTEGER NOT NULL DEFAULT 0 CHECK (artifact_ordinal >= 0),
  task_uuid TEXT,
  execution_uuid TEXT,
  process_uuid TEXT,
  process_attempt INTEGER CHECK (process_attempt IS NULL OR process_attempt >= 0),
  intake_item_uuid TEXT,
  intake_revision_uuid TEXT,
  clean_artifact_uuid TEXT,
  clean_artifact_digest TEXT,
  schema_key TEXT,
  schema_version TEXT,
  schema_digest TEXT,
  profile_key TEXT,
  profile_version TEXT,
  profile_digest TEXT,
  model_key TEXT,
  model_version TEXT,
  prompt_key TEXT,
  prompt_version TEXT,
  prompt_digest TEXT,
  process_fence TEXT,
  logical_handle TEXT NOT NULL CHECK (logical_handle NOT LIKE '/%'),
  media_type TEXT NOT NULL,
  size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
  digest_algorithm TEXT NOT NULL DEFAULT 'sha256'
    CHECK (digest_algorithm = 'sha256'),
  content_digest TEXT NOT NULL
    CHECK (length(content_digest) = 64
           AND content_digest NOT GLOB '*[^0-9a-f]*'),
  stored_object_uuid TEXT,
  validation_disposition TEXT NOT NULL
    CHECK (validation_disposition IN ('full_valid', 'invalid', 'partial_rejected')),
  validation_report_ref TEXT,
  validation_report_digest TEXT,
  proof_ref TEXT,
  proof_digest TEXT,
  predecessor_generation_artifact_uuid TEXT,
  repair_causation_ref TEXT,
  created_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (team_uuid, generation_artifact_uuid),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid),
  FOREIGN KEY (team_uuid, task_uuid)
    REFERENCES mkb_tasks(team_uuid, task_uuid),
  FOREIGN KEY (team_uuid, execution_uuid)
    REFERENCES mkb_executions(team_uuid, execution_uuid),
  FOREIGN KEY (team_uuid, intake_item_uuid)
    REFERENCES mkb_intake_items(team_uuid, intake_item_uuid),
  FOREIGN KEY (team_uuid, intake_revision_uuid)
    REFERENCES mkb_intake_revisions(team_uuid, intake_revision_uuid),
  FOREIGN KEY (team_uuid, stored_object_uuid)
    REFERENCES mkb_stored_objects(team_uuid, stored_object_uuid),
  FOREIGN KEY (predecessor_generation_artifact_uuid)
    REFERENCES mkb_generation_artifacts(generation_artifact_uuid)
);

CREATE TABLE mkb_generation_pointers (
  team_uuid TEXT NOT NULL,
  execution_uuid TEXT NOT NULL,
  artifact_type TEXT NOT NULL,
  current_generation_artifact_uuid TEXT NOT NULL,
  pointer_revision INTEGER NOT NULL DEFAULT 0 CHECK (pointer_revision >= 0),
  updated_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (team_uuid, execution_uuid, artifact_type),
  FOREIGN KEY (team_uuid, execution_uuid)
    REFERENCES mkb_executions(team_uuid, execution_uuid),
  FOREIGN KEY (team_uuid, current_generation_artifact_uuid)
    REFERENCES mkb_generation_artifacts(team_uuid, generation_artifact_uuid)
);

CREATE TABLE mkb_generation_pointer_transitions (
  transition_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  execution_uuid TEXT NOT NULL,
  artifact_type TEXT NOT NULL,
  before_artifact_uuid TEXT,
  after_artifact_uuid TEXT NOT NULL,
  expected_pointer_revision INTEGER NOT NULL CHECK (expected_pointer_revision >= 0),
  actual_pointer_revision INTEGER NOT NULL CHECK (actual_pointer_revision >= 0),
  causation_process_uuid TEXT,
  causation_task_uuid TEXT,
  occurred_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (team_uuid, execution_uuid)
    REFERENCES mkb_executions(team_uuid, execution_uuid),
  FOREIGN KEY (team_uuid, before_artifact_uuid)
    REFERENCES mkb_generation_artifacts(team_uuid, generation_artifact_uuid),
  FOREIGN KEY (team_uuid, after_artifact_uuid)
    REFERENCES mkb_generation_artifacts(team_uuid, generation_artifact_uuid)
);

CREATE TABLE mkb_generation_invocations (
  invocation_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  execution_uuid TEXT NOT NULL,
  process_uuid TEXT NOT NULL,
  process_attempt INTEGER NOT NULL CHECK (process_attempt >= 0),
  invocation_ordinal INTEGER NOT NULL CHECK (invocation_ordinal >= 0),
  invocation_kind TEXT NOT NULL CHECK (invocation_kind IN ('generation', 'repair')),
  model_key TEXT,
  model_version TEXT,
  prompt_key TEXT,
  prompt_version TEXT,
  prompt_digest TEXT,
  schema_key TEXT,
  schema_version TEXT,
  schema_digest TEXT,
  profile_key TEXT,
  profile_version TEXT,
  profile_digest TEXT,
  input_digest TEXT NOT NULL,
  output_digest TEXT,
  error_digest TEXT,
  input_tokens INTEGER CHECK (input_tokens IS NULL OR input_tokens >= 0),
  output_tokens INTEGER CHECK (output_tokens IS NULL OR output_tokens >= 0),
  total_tokens INTEGER CHECK (total_tokens IS NULL OR total_tokens >= 0),
  occurred_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (process_uuid, invocation_ordinal),
  FOREIGN KEY (team_uuid, execution_uuid)
    REFERENCES mkb_executions(team_uuid, execution_uuid),
  FOREIGN KEY (team_uuid, process_uuid)
    REFERENCES mkb_processes(team_uuid, process_uuid)
);

-- --------------------------------------------------------------------------
-- vector (D04's 2 required tables)
-- --------------------------------------------------------------------------

CREATE TABLE mkb_vector_namespaces (
  namespace_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  namespace_key TEXT NOT NULL,
  display_name TEXT,
  -- `embedding_model` is retained as a human-readable compatibility label;
  -- key/version/adapter are the authoritative Layer A fence (S11/S08).
  embedding_model TEXT NOT NULL,
  embedding_model_key TEXT NOT NULL,
  embedding_model_version TEXT NOT NULL,
  adapter_kind TEXT NOT NULL,
  dimension INTEGER NOT NULL CHECK (dimension > 0),
  distance_metric TEXT NOT NULL DEFAULT 'cosine'
    CHECK (distance_metric IN ('cosine', 'l2', 'inner_product')),
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'disabled', 'deleted')),
  index_generation INTEGER NOT NULL DEFAULT 0 CHECK (index_generation >= 0),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  deleted_at TEXT,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (team_uuid, namespace_key),
  UNIQUE (namespace_uuid, team_uuid),
  UNIQUE (namespace_uuid, team_uuid, embedding_model, embedding_model_key,
          embedding_model_version, adapter_kind, dimension),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid),
  FOREIGN KEY (embedding_model_key, embedding_model_version)
    REFERENCES mkb_model_catalog(model_key, model_version)
);

CREATE TABLE mkb_vector_records (
  vector_record_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  namespace_uuid TEXT NOT NULL,
  generation_artifact_uuid TEXT NOT NULL,
  generation_artifact_type TEXT NOT NULL,
  block_or_unit_id TEXT NOT NULL,
  channel TEXT NOT NULL DEFAULT 'original' CHECK (channel IN ('original', 'summary')),
  intake_source_uuid TEXT,
  intake_item_uuid TEXT,
  intake_revision_uuid TEXT,
  task_uuid TEXT,
  execution_uuid TEXT,
  industry_domain TEXT,
  content_digest_algorithm TEXT NOT NULL DEFAULT 'sha256'
    CHECK (content_digest_algorithm = 'sha256'),
  content_digest TEXT NOT NULL
    CHECK (length(content_digest) = 64
           AND content_digest NOT GLOB '*[^0-9a-f]*'),
  source_handle TEXT CHECK (source_handle IS NULL OR source_handle NOT LIKE '/%'),
  content_char_length INTEGER CHECK (content_char_length IS NULL OR content_char_length >= 0),
  embedding_model TEXT NOT NULL,
  embedding_model_key TEXT NOT NULL,
  embedding_model_version TEXT NOT NULL,
  adapter_kind TEXT NOT NULL,
  dimension INTEGER NOT NULL CHECK (dimension > 0),
  -- Stock SQLite compatible representation of Turso native F32_BLOB(d).
  embedding BLOB NOT NULL,
  embedding_digest TEXT,
  -- S08/S09 reconciliation: an upsert begins withdrawn.  It becomes indexed
  -- only in the S09 proof/pointer promotion transaction; half-writes cannot
  -- become candidates through the active view.
  publication_state TEXT NOT NULL DEFAULT 'withdrawn'
    CHECK (publication_state IN ('indexed', 'withdrawn')),
  index_generation INTEGER NOT NULL DEFAULT 0 CHECK (index_generation >= 0),
  deleted_at TEXT,
  outbox_dedupe_key TEXT,
  embedded_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (vector_record_uuid, team_uuid),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid),
  FOREIGN KEY (namespace_uuid, team_uuid, embedding_model, embedding_model_key,
               embedding_model_version, adapter_kind, dimension)
    REFERENCES mkb_vector_namespaces(namespace_uuid, team_uuid, embedding_model,
                                     embedding_model_key,
                                     embedding_model_version,
                                     adapter_kind, dimension),
  FOREIGN KEY (team_uuid, generation_artifact_uuid)
    REFERENCES mkb_generation_artifacts(team_uuid, generation_artifact_uuid),
  FOREIGN KEY (team_uuid, intake_source_uuid)
    REFERENCES mkb_intake_sources(team_uuid, intake_source_uuid),
  FOREIGN KEY (team_uuid, intake_item_uuid)
    REFERENCES mkb_intake_items(team_uuid, intake_item_uuid),
  FOREIGN KEY (team_uuid, intake_revision_uuid)
    REFERENCES mkb_intake_revisions(team_uuid, intake_revision_uuid),
  FOREIGN KEY (team_uuid, task_uuid)
    REFERENCES mkb_tasks(team_uuid, task_uuid),
  FOREIGN KEY (team_uuid, execution_uuid)
    REFERENCES mkb_executions(team_uuid, execution_uuid),
  FOREIGN KEY (embedding_model_key, embedding_model_version)
    REFERENCES mkb_model_catalog(model_key, model_version)
);

-- --------------------------------------------------------------------------
-- S08 additive reconciliation: normalized Layer-B facets, not payload_extra.
-- The key/version/digest must have been resolved by S04/S14 before this copied
-- retrieval filter is written.  This is deliberately a queryable projection,
-- never a model-generated or free-form JSON convention.
-- --------------------------------------------------------------------------

CREATE TABLE mkb_vector_record_facets (
  facet_uuid TEXT PRIMARY KEY,
  vector_record_uuid TEXT NOT NULL,
  team_uuid TEXT NOT NULL,
  facet_key TEXT NOT NULL,
  facet_value TEXT NOT NULL,
  definition_version TEXT NOT NULL,
  definition_digest TEXT NOT NULL,
  created_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (vector_record_uuid, facet_key),
  FOREIGN KEY (vector_record_uuid, team_uuid)
    REFERENCES mkb_vector_records(vector_record_uuid, team_uuid)
);

-- --------------------------------------------------------------------------
-- S09 additive reconciliation (2 tables).
-- D04-v1.1's 55-table closed set predates/omits these durable S09 SSOTs.
-- Together with the S08 normalized facet projection above, this initial
-- migration deliberately yields 58 MKB application tables.  None is a second
-- vector store or a replacement business state table.
-- --------------------------------------------------------------------------

CREATE TABLE mkb_publication_proofs (
  proof_uuid TEXT PRIMARY KEY,
  proof_type TEXT NOT NULL DEFAULT 'index.publication.v1'
    CHECK (proof_type = 'index.publication.v1'),
  proof_version TEXT NOT NULL DEFAULT 'v1',
  team_uuid TEXT NOT NULL,
  intake_item_uuid TEXT NOT NULL,
  intake_revision_uuid TEXT NOT NULL,
  execution_uuid TEXT,
  process_uuid TEXT,
  generation_artifact_uuid TEXT NOT NULL,
  generation_artifact_type TEXT NOT NULL,
  namespace_uuid TEXT NOT NULL,
  embedding_model TEXT NOT NULL,
  embedding_model_key TEXT NOT NULL,
  embedding_model_version TEXT NOT NULL,
  adapter_kind TEXT NOT NULL,
  dimension INTEGER NOT NULL CHECK (dimension > 0),
  index_generation INTEGER NOT NULL CHECK (index_generation >= 0),
  expected_count INTEGER NOT NULL CHECK (expected_count >= 0),
  actual_count INTEGER NOT NULL CHECK (actual_count >= 0),
  matched_count INTEGER NOT NULL CHECK (matched_count >= 0),
  required_set_digest TEXT NOT NULL,
  actual_set_digest TEXT NOT NULL,
  command_input_digest TEXT NOT NULL,
  layer_a_json TEXT NOT NULL DEFAULT '{}',
  layer_b_keys_echo_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  CHECK (matched_count <= actual_count AND matched_count <= expected_count),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid),
  FOREIGN KEY (team_uuid, intake_item_uuid)
    REFERENCES mkb_intake_items(team_uuid, intake_item_uuid),
  FOREIGN KEY (team_uuid, intake_revision_uuid)
    REFERENCES mkb_intake_revisions(team_uuid, intake_revision_uuid),
  FOREIGN KEY (team_uuid, execution_uuid)
    REFERENCES mkb_executions(team_uuid, execution_uuid),
  FOREIGN KEY (team_uuid, process_uuid)
    REFERENCES mkb_processes(team_uuid, process_uuid),
  FOREIGN KEY (team_uuid, generation_artifact_uuid)
    REFERENCES mkb_generation_artifacts(team_uuid, generation_artifact_uuid),
  FOREIGN KEY (namespace_uuid, team_uuid, embedding_model, embedding_model_key,
               embedding_model_version, adapter_kind, dimension)
    REFERENCES mkb_vector_namespaces(namespace_uuid, team_uuid, embedding_model,
                                     embedding_model_key,
                                     embedding_model_version,
                                     adapter_kind, dimension),
  FOREIGN KEY (embedding_model_key, embedding_model_version)
    REFERENCES mkb_model_catalog(model_key, model_version)
);

CREATE TABLE mkb_index_active_pointers (
  team_uuid TEXT NOT NULL,
  intake_item_uuid TEXT NOT NULL,
  namespace_uuid TEXT NOT NULL,
  active_index_generation INTEGER NOT NULL CHECK (active_index_generation >= 0),
  pointer_row_revision INTEGER NOT NULL DEFAULT 0 CHECK (pointer_row_revision >= 0),
  lifecycle_state TEXT NOT NULL DEFAULT 'building'
    CHECK (lifecycle_state IN ('building', 'validating', 'ready_candidate',
                               'active', 'retiring', 'withdrawn')),
  candidate_index_generation INTEGER CHECK (candidate_index_generation IS NULL
                                            OR candidate_index_generation >= 0),
  last_proof_uuid TEXT,
  generation_artifact_uuid TEXT,
  updated_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (team_uuid, intake_item_uuid, namespace_uuid),
  FOREIGN KEY (team_uuid, intake_item_uuid)
    REFERENCES mkb_intake_items(team_uuid, intake_item_uuid),
  FOREIGN KEY (namespace_uuid, team_uuid)
    REFERENCES mkb_vector_namespaces(namespace_uuid, team_uuid),
  FOREIGN KEY (last_proof_uuid) REFERENCES mkb_publication_proofs(proof_uuid),
  FOREIGN KEY (team_uuid, generation_artifact_uuid)
    REFERENCES mkb_generation_artifacts(team_uuid, generation_artifact_uuid)
);

-- --------------------------------------------------------------------------
-- S11 global inference invocation ledger (the final D04 required table).
-- --------------------------------------------------------------------------

CREATE TABLE mkb_inference_invocations (
  invocation_uuid TEXT PRIMARY KEY,
  team_uuid TEXT,
  trace_uuid TEXT,
  task_uuid TEXT,
  execution_uuid TEXT,
  process_uuid TEXT,
  capability_key TEXT NOT NULL,
  adapter_kind TEXT NOT NULL,
  model_key TEXT NOT NULL,
  model_version TEXT NOT NULL,
  request_digest TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('succeeded', 'failed', 'cancelled')),
  error_code TEXT,
  input_tokens INTEGER CHECK (input_tokens IS NULL OR input_tokens >= 0),
  output_tokens INTEGER CHECK (output_tokens IS NULL OR output_tokens >= 0),
  total_tokens INTEGER CHECK (total_tokens IS NULL OR total_tokens >= 0),
  latency_ms INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0),
  generation_invocation_uuid TEXT,
  occurred_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid),
  FOREIGN KEY (team_uuid, task_uuid)
    REFERENCES mkb_tasks(team_uuid, task_uuid),
  FOREIGN KEY (team_uuid, execution_uuid)
    REFERENCES mkb_executions(team_uuid, execution_uuid),
  FOREIGN KEY (team_uuid, process_uuid)
    REFERENCES mkb_processes(team_uuid, process_uuid),
  FOREIGN KEY (model_key, model_version)
    REFERENCES mkb_model_catalog(model_key, model_version),
  FOREIGN KEY (generation_invocation_uuid)
    REFERENCES mkb_generation_invocations(invocation_uuid)
);

-- --------------------------------------------------------------------------
-- Required indexes: tenant list, queue/state, subject reverse lookup, and
-- idempotency.  Names intentionally follow D04 where it specifies a name.
-- --------------------------------------------------------------------------

CREATE UNIQUE INDEX ux_mkb_teams_fingerprint
  ON mkb_teams(team_uuid, creation_fingerprint);
CREATE INDEX ix_mkb_teams_status ON mkb_teams(status, updated_at);

CREATE INDEX ix_de_team_time ON mkb_domain_events(team_uuid, occurred_at, event_uuid);
CREATE INDEX ix_de_trace ON mkb_domain_events(trace_uuid, occurred_at, event_uuid);
CREATE INDEX ix_de_task ON mkb_domain_events(team_uuid, task_uuid, occurred_at);
CREATE INDEX ix_de_execution ON mkb_domain_events(team_uuid, execution_uuid, occurred_at);
CREATE INDEX ix_de_process ON mkb_domain_events(team_uuid, process_uuid, occurred_at);
CREATE INDEX ix_de_type ON mkb_domain_events(team_uuid, event_type, occurred_at);
CREATE INDEX ix_de_subject ON mkb_domain_events(team_uuid, subject_kind, subject_uuid, occurred_at);

CREATE INDEX ix_diag_trace ON mkb_ops_diagnostic_logs(trace_uuid, occurred_at);
CREATE INDEX ix_diag_team_time ON mkb_ops_diagnostic_logs(team_uuid, occurred_at)
  WHERE team_uuid IS NOT NULL;
CREATE INDEX ix_diag_level_time ON mkb_ops_diagnostic_logs(log_level, occurred_at)
  WHERE log_level IN ('warn', 'error');
CREATE INDEX ix_diag_code ON mkb_ops_diagnostic_logs(log_code, occurred_at);
CREATE INDEX ix_diag_process ON mkb_ops_diagnostic_logs(process_uuid, occurred_at)
  WHERE process_uuid IS NOT NULL;

CREATE INDEX ix_sec_time ON mkb_security_audit_events(occurred_at, audit_uuid);
CREATE INDEX ix_sec_team_time ON mkb_security_audit_events(team_uuid, occurred_at);
CREATE INDEX ix_sec_outcome ON mkb_security_audit_events(outcome, occurred_at);
CREATE INDEX ix_sec_denial ON mkb_security_audit_events(denial_code, occurred_at)
  WHERE outcome = 'denied';
CREATE INDEX ix_sec_actor ON mkb_security_audit_events(actor_fingerprint, occurred_at)
  WHERE actor_fingerprint IS NOT NULL;
CREATE INDEX ix_sec_trace ON mkb_security_audit_events(trace_uuid, occurred_at)
  WHERE trace_uuid IS NOT NULL;

CREATE UNIQUE INDEX ux_mkb_tasks_fingerprint
  ON mkb_tasks(team_uuid, task_uuid, creation_fingerprint);
CREATE INDEX ix_mkb_tasks_list
  ON mkb_tasks(team_uuid, created_at DESC, task_uuid DESC);
CREATE INDEX ix_mkb_tasks_status ON mkb_tasks(team_uuid, status, updated_at);
CREATE INDEX ix_mkb_tasks_intent ON mkb_tasks(team_uuid, request_intent, created_at);
CREATE INDEX ix_mkb_tasks_trace ON mkb_tasks(trace_uuid);
CREATE INDEX ix_mkb_tasks_root_exec ON mkb_tasks(team_uuid, current_root_execution_uuid);
CREATE INDEX ix_mkb_task_audits_received ON mkb_task_audits(team_uuid, received_at);

CREATE UNIQUE INDEX ux_restart_atomic_accepted
  ON mkb_task_restarts(team_uuid, restart_task_uuid, restart_scope)
  WHERE admission_outcome = 'accepted' AND restart_scope = 'atomic_intake_item';
CREATE UNIQUE INDEX ux_restart_full_src_gen
  ON mkb_task_restarts(team_uuid, source_task_uuid, source_generation, restart_scope)
  WHERE admission_outcome = 'accepted' AND restart_scope = 'full_task';
CREATE UNIQUE INDEX ux_restart_full_tgt_gen
  ON mkb_task_restarts(team_uuid, source_task_uuid, target_generation, restart_scope)
  WHERE admission_outcome = 'accepted' AND restart_scope = 'full_task';
CREATE INDEX ix_restart_source_task
  ON mkb_task_restarts(team_uuid, source_task_uuid, requested_at, restart_uuid);
CREATE INDEX ix_restart_restart_task
  ON mkb_task_restarts(team_uuid, restart_task_uuid, requested_at, restart_uuid);
CREATE INDEX ix_restart_item
  ON mkb_task_restarts(team_uuid, intake_item_uuid, requested_at, restart_uuid);
CREATE INDEX ix_restart_scope_outcome
  ON mkb_task_restarts(team_uuid, restart_scope, admission_outcome, requested_at, restart_uuid);
CREATE INDEX ix_restart_trace ON mkb_task_restarts(causation_trace_uuid);

-- D04's historical `UNIQUE(..., execution_uuid)` cannot enforce one root,
-- because the primary key already makes execution_uuid unique.  This partial
-- unique index is the executable D02/D03 reconciliation.
CREATE UNIQUE INDEX ux_mkb_exec_one_root
  ON mkb_executions(team_uuid, task_uuid, generation)
  WHERE execution_role = 'root' AND parent_execution_uuid IS NULL;
CREATE INDEX ix_mkb_exec_task ON mkb_executions(team_uuid, task_uuid, generation, created_at);
CREATE INDEX ix_mkb_exec_status ON mkb_executions(team_uuid, status, next_wake_at);
CREATE INDEX ix_mkb_exec_root ON mkb_executions(team_uuid, root_execution_uuid);
CREATE INDEX ix_mkb_exec_parent ON mkb_executions(team_uuid, parent_execution_uuid);
CREATE INDEX ix_mkb_exec_workflow_rev ON mkb_executions(workflow_revision_uuid);
CREATE UNIQUE INDEX ux_mkb_exec_child_manifest
  ON mkb_executions(root_execution_uuid, manifest_revision, target_uuid)
  WHERE parent_execution_uuid IS NOT NULL AND target_uuid IS NOT NULL;

CREATE UNIQUE INDEX ux_mkb_proc_materialization
  ON mkb_processes(execution_uuid, workflow_step_uuid, materialization_key);
CREATE INDEX ix_mkb_proc_claim_queue
  ON mkb_processes(status, available_at, priority_rank)
  WHERE status IN ('ready', 'retry_wait');
CREATE INDEX ix_mkb_proc_team_status ON mkb_processes(team_uuid, status, available_at);
CREATE INDEX ix_mkb_proc_execution ON mkb_processes(team_uuid, execution_uuid, created_at);
CREATE INDEX ix_mkb_proc_lease ON mkb_processes(status, lease_expires_at)
  WHERE status IN ('claimed', 'running', 'cancelling');
CREATE INDEX ix_mkb_proc_fence ON mkb_processes(process_uuid, fencing_generation);

CREATE UNIQUE INDEX ux_mkb_outbox_dedupe ON mkb_outbox(team_uuid, dedupe_key);
CREATE INDEX ix_mkb_outbox_dispatch ON mkb_outbox(status, available_at, created_at)
  WHERE status IN ('pending', 'in_flight');
CREATE INDEX ix_mkb_outbox_team ON mkb_outbox(team_uuid, created_at);
CREATE INDEX ix_mkb_outbox_kind ON mkb_outbox(kind, status, available_at);

CREATE INDEX ix_mkb_gates_task_status
  ON mkb_execution_gates(team_uuid, task_uuid, status, opened_at);
CREATE INDEX ix_mkb_gates_execution ON mkb_execution_gates(execution_uuid);
CREATE INDEX ix_mkb_gates_open ON mkb_execution_gates(team_uuid, status)
  WHERE status = 'open';
CREATE INDEX ix_mkb_gate_targets_digest ON mkb_execution_gate_targets(team_uuid, target_digest);
CREATE INDEX ix_mkb_gate_decisions_gate ON mkb_execution_gate_decisions(gate_uuid, created_at);
CREATE INDEX ix_mkb_gate_decisions_team ON mkb_execution_gate_decisions(team_uuid, created_at);

CREATE UNIQUE INDEX ux_workflow_key ON mkb_workflow_registry(workflow_key);
CREATE INDEX ix_workflow_status_priority
  ON mkb_workflow_registry(registry_status, selector_priority);
CREATE INDEX ix_workflow_purpose_status
  ON mkb_workflow_registry(purpose_key, registry_status);
CREATE UNIQUE INDEX ux_workflow_revision_number
  ON mkb_workflow_revisions(workflow_uuid, revision_number);
CREATE UNIQUE INDEX ux_workflow_revision_fingerprint
  ON mkb_workflow_revisions(workflow_uuid, registration_fingerprint);
CREATE INDEX ix_workflow_revision_compiled ON mkb_workflow_revisions(compiled_digest);
CREATE INDEX ix_workflow_revision_registered
  ON mkb_workflow_revisions(workflow_uuid, registered_at);
CREATE UNIQUE INDEX ux_workflow_step_key
  ON mkb_workflow_steps(workflow_revision_uuid, step_key);
CREATE UNIQUE INDEX ux_workflow_route_key
  ON mkb_workflow_routes(workflow_revision_uuid, route_key);
CREATE UNIQUE INDEX ux_workflow_route_selector
  ON mkb_workflow_routes(workflow_revision_uuid, from_step_uuid, outcome_selector, priority);
CREATE UNIQUE INDEX ux_workflow_binding_slot
  ON mkb_workflow_bindings(workflow_step_uuid, binding_kind, slot_name);
CREATE INDEX ix_workflow_control_scope
  ON mkb_workflow_controls(workflow_revision_uuid, scope_type);
CREATE UNIQUE INDEX ux_workflow_guard_order
  ON mkb_workflow_guards(workflow_revision_uuid, guard_group_key, order_index);

CREATE INDEX ix_semantic_definition_digest ON mkb_intake_semantic_definitions(definition_digest);
CREATE INDEX ix_action_definition_digest ON mkb_intake_action_definitions(definition_digest);
CREATE INDEX ix_source_kind_definition_digest ON mkb_source_kind_definitions(definition_digest);
CREATE INDEX ix_preflight_definition_digest ON mkb_preflight_profile_definitions(definition_digest);
CREATE INDEX ix_structure_schema_digest ON mkb_structure_schema_definitions(schema_digest);
CREATE INDEX ix_construction_schema_digest ON mkb_construction_schema_definitions(schema_digest);
CREATE UNIQUE INDEX ux_prompt_path_digest
  ON mkb_prompt_hash_pointers(git_relative_path, content_sha256);
CREATE UNIQUE INDEX ux_mkb_model_catalog_key_version
  ON mkb_model_catalog(model_key, model_version);
CREATE INDEX ix_model_catalog_modality_status ON mkb_model_catalog(modality, status);
CREATE INDEX ix_model_catalog_digest ON mkb_model_catalog(definition_digest);
CREATE UNIQUE INDEX ux_adapter_binding_team
  ON mkb_adapter_bindings(capability_key, adapter_kind, model_key, model_version, team_uuid)
  WHERE team_uuid IS NOT NULL;
CREATE UNIQUE INDEX ux_adapter_binding_global
  ON mkb_adapter_bindings(capability_key, adapter_kind, model_key, model_version)
  WHERE team_uuid IS NULL;
CREATE INDEX ix_adapter_binding_capability
  ON mkb_adapter_bindings(capability_key, enabled, priority);
CREATE INDEX ix_adapter_binding_kind ON mkb_adapter_bindings(adapter_kind, enabled);

CREATE INDEX ix_obj_stored_team_created ON mkb_stored_objects(team_uuid, created_at);
CREATE UNIQUE INDEX ux_obj_stored_digest_size
  ON mkb_stored_objects(team_uuid, content_digest, size_bytes);
CREATE INDEX ix_obj_stored_tombstone ON mkb_stored_objects(tombstoned_at)
  WHERE tombstoned_at IS NOT NULL;
CREATE INDEX ix_obj_ref_live ON mkb_object_references(stored_object_uuid)
  WHERE released_at IS NULL;
CREATE INDEX ix_obj_ref_owner ON mkb_object_references(team_uuid, owner_kind, owner_uuid);
CREATE INDEX ix_obj_ref_purpose ON mkb_object_references(purpose, released_at);
CREATE INDEX ix_obj_ref_gc ON mkb_object_references(released_at, stored_object_uuid)
  WHERE released_at IS NOT NULL;
CREATE INDEX ix_obj_delete_stored ON mkb_object_delete_proofs(stored_object_uuid);
CREATE INDEX ix_obj_delete_team_time ON mkb_object_delete_proofs(team_uuid, unlinked_at);

CREATE INDEX ix_intake_sources_kind ON mkb_intake_sources(team_uuid, source_kind, created_at);
CREATE INDEX ix_intake_sources_accepts ON mkb_intake_sources(team_uuid, accepts_new_snapshots);
CREATE INDEX ix_intake_snapshots_source_time
  ON mkb_intake_snapshots(team_uuid, intake_source_uuid, accepted_at);
CREATE INDEX ix_intake_snapshots_producer ON mkb_intake_snapshots(producer_execution_uuid);
CREATE INDEX ix_intake_items_lifecycle
  ON mkb_intake_items(team_uuid, lifecycle_state, updated_at);
CREATE INDEX ix_intake_items_serving
  ON mkb_intake_items(team_uuid, serving_revision_uuid);
CREATE INDEX ix_intake_revisions_snapshot
  ON mkb_intake_revisions(team_uuid, source_snapshot_uuid);
CREATE INDEX ix_intake_artifacts_digest ON mkb_intake_artifacts(team_uuid, content_digest);
CREATE INDEX ix_intake_artifacts_snapshot ON mkb_intake_artifacts(owner_snapshot_uuid);
CREATE INDEX ix_intake_artifacts_revision ON mkb_intake_artifacts(owner_revision_uuid);
CREATE INDEX ix_intake_artifacts_stored ON mkb_intake_artifacts(stored_object_uuid);
CREATE INDEX ix_intake_membership_item
  ON mkb_intake_snapshot_memberships(team_uuid, intake_item_uuid);
CREATE INDEX ix_intake_membership_decision ON mkb_intake_snapshot_memberships(decision_kind);
CREATE INDEX ix_intake_semantics_definition
  ON mkb_intake_revision_semantics(semantic_key, definition_version);
CREATE INDEX ix_intake_transition_item
  ON mkb_intake_item_transitions(team_uuid, intake_item_uuid, occurred_at);
CREATE INDEX ix_intake_transition_fence ON mkb_intake_item_transitions(transition_fence);
CREATE INDEX ix_intake_candidate_expiry
  ON mkb_intake_candidate_sets(staging_state, expiry_at);
CREATE INDEX ix_intake_candidate_source
  ON mkb_intake_candidate_sets(team_uuid, intake_source_uuid, created_at);
CREATE INDEX ix_intake_candidate_page_digest ON mkb_intake_candidate_pages(page_digest);
CREATE INDEX ix_intake_changeset_snapshot
  ON mkb_intake_change_sets(team_uuid, intake_snapshot_uuid, created_at);
CREATE INDEX ix_intake_change_fact_kind
  ON mkb_intake_change_set_facts(change_set_uuid, fact_kind);
CREATE INDEX ix_intake_repair_status ON mkb_intake_repair_intents(team_uuid, status);
CREATE INDEX ix_intake_repair_target ON mkb_intake_repair_intents(team_uuid, target_kind, target_uuid);
CREATE INDEX ix_intake_cleanup_status ON mkb_intake_cleanup_intents(team_uuid, status);
CREATE INDEX ix_intake_cleanup_proof_intent ON mkb_intake_cleanup_proofs(intent_uuid);
CREATE INDEX ix_intake_cleanup_proof_target ON mkb_intake_cleanup_proofs(target_ref);

CREATE INDEX ix_gen_art_execution
  ON mkb_generation_artifacts(team_uuid, execution_uuid, artifact_type, created_at);
CREATE INDEX ix_gen_art_task ON mkb_generation_artifacts(team_uuid, task_uuid, created_at);
CREATE INDEX ix_gen_art_digest ON mkb_generation_artifacts(team_uuid, content_digest);
CREATE INDEX ix_gen_art_item_rev
  ON mkb_generation_artifacts(team_uuid, intake_item_uuid, intake_revision_uuid);
CREATE INDEX ix_gen_art_stored ON mkb_generation_artifacts(stored_object_uuid);
CREATE INDEX ix_gen_pointer_artifact
  ON mkb_generation_pointers(current_generation_artifact_uuid);
CREATE INDEX ix_gen_pointer_transition
  ON mkb_generation_pointer_transitions(team_uuid, execution_uuid, artifact_type, occurred_at);
CREATE INDEX ix_gen_invocation_execution
  ON mkb_generation_invocations(execution_uuid, occurred_at);

CREATE INDEX ix_vec_ns_team_status
  ON mkb_vector_namespaces(team_uuid, status, namespace_key);
CREATE INDEX ix_vec_ns_model_dimension
  ON mkb_vector_namespaces(embedding_model, dimension);
CREATE INDEX ix_vec_ns_model_version_dimension
  ON mkb_vector_namespaces(embedding_model_key, embedding_model_version, dimension);
CREATE UNIQUE INDEX ux_vec_coord_active
  ON mkb_vector_records(team_uuid, namespace_uuid, generation_artifact_uuid,
                        block_or_unit_id, channel, embedding_model)
  WHERE deleted_at IS NULL;
-- The D04 key above is sufficient because `namespace_uuid` now strongly FKs
-- the model/version/adapter/dimension tuple.  Keep an explicit Layer-A index
-- as a defense in depth and as the optimal lookup shape for validation.
CREATE UNIQUE INDEX ux_vec_coord_active_layer_a
  ON mkb_vector_records(team_uuid, namespace_uuid, generation_artifact_uuid,
                        block_or_unit_id, channel, embedding_model_key,
                        embedding_model_version, adapter_kind)
  WHERE deleted_at IS NULL;
CREATE INDEX ix_vec_team_ns ON mkb_vector_records(team_uuid, namespace_uuid, deleted_at);
CREATE INDEX ix_vec_generation
  ON mkb_vector_records(team_uuid, generation_artifact_uuid, deleted_at);
CREATE INDEX ix_vec_item_rev
  ON mkb_vector_records(team_uuid, intake_item_uuid, intake_revision_uuid);
CREATE INDEX ix_vec_source ON mkb_vector_records(team_uuid, intake_source_uuid);
CREATE INDEX ix_vec_industry_domain ON mkb_vector_records(team_uuid, industry_domain)
  WHERE industry_domain IS NOT NULL;
CREATE INDEX ix_vec_facet_filter
  ON mkb_vector_record_facets(team_uuid, facet_key, facet_value, vector_record_uuid);
CREATE INDEX ix_vec_facet_record ON mkb_vector_record_facets(vector_record_uuid);
CREATE INDEX ix_vec_task ON mkb_vector_records(team_uuid, task_uuid);
CREATE INDEX ix_vec_content_digest ON mkb_vector_records(team_uuid, content_digest);
CREATE INDEX ix_vec_publication
  ON mkb_vector_records(team_uuid, publication_state, deleted_at, index_generation);
-- Compatibility index name required by D04.  Turso/libSQL deployments replace
-- this expression with native `libsql_vector_idx(embedding)` in their adapter
-- migration variant; readiness refuses to mistake this B-tree for ANN.
CREATE INDEX vec_idx_mkb_vector_records_embedding ON mkb_vector_records(embedding);

CREATE INDEX ix_publication_proof_lookup
  ON mkb_publication_proofs(team_uuid, intake_item_uuid, namespace_uuid,
                             index_generation, generation_artifact_uuid, created_at);
CREATE INDEX ix_publication_proof_generation
  ON mkb_publication_proofs(team_uuid, generation_artifact_uuid, created_at);
CREATE INDEX ix_index_pointer_active
  ON mkb_index_active_pointers(team_uuid, namespace_uuid, lifecycle_state,
                                active_index_generation);

CREATE INDEX ix_inference_team_time ON mkb_inference_invocations(team_uuid, occurred_at);
CREATE INDEX ix_inference_trace_time ON mkb_inference_invocations(trace_uuid, occurred_at);
CREATE INDEX ix_inference_process ON mkb_inference_invocations(process_uuid);
CREATE INDEX ix_inference_capability_time
  ON mkb_inference_invocations(capability_key, occurred_at);
CREATE INDEX ix_inference_model_time
  ON mkb_inference_invocations(model_key, model_version, occurred_at);

-- --------------------------------------------------------------------------
-- D04 read-only views (14).  No INSTEAD OF triggers are installed: SQLite
-- rejects UPDATE/INSERT/DELETE against these views, preserving the SSOT/CAS
-- boundary.  `mkb_v_domain_events_by_trace` is a parameterless timeline view;
-- callers supply their trace predicate when selecting from it.
-- --------------------------------------------------------------------------

CREATE VIEW mkb_v_tasks_active AS
SELECT *
FROM mkb_tasks
WHERE deleted_at IS NULL;

CREATE VIEW mkb_v_processes_claimable AS
SELECT *
FROM mkb_processes
WHERE status IN ('ready', 'retry_wait')
  AND available_at <= strftime('%Y-%m-%dT%H:%M:%fZ', 'now');

CREATE VIEW mkb_v_outbox_pending AS
SELECT *
FROM mkb_outbox
WHERE status IN ('pending', 'in_flight');

CREATE VIEW mkb_v_object_live_refs AS
SELECT *
FROM mkb_object_references
WHERE released_at IS NULL;

CREATE VIEW mkb_v_object_orphan_candidates AS
SELECT o.*
FROM mkb_stored_objects AS o
WHERE o.tombstoned_at IS NULL
  AND NOT EXISTS (
    SELECT 1
    FROM mkb_object_references AS r
    WHERE r.stored_object_uuid = o.stored_object_uuid
      AND r.released_at IS NULL
  );

CREATE VIEW mkb_v_generation_current AS
SELECT
  p.team_uuid,
  p.execution_uuid,
  p.artifact_type,
  p.pointer_revision,
  p.updated_at AS pointer_updated_at,
  a.*
FROM mkb_generation_pointers AS p
JOIN mkb_generation_artifacts AS a
  ON a.generation_artifact_uuid = p.current_generation_artifact_uuid;

CREATE VIEW mkb_v_intake_items_serving AS
SELECT *
FROM mkb_intake_items
WHERE lifecycle_state = 'active'
  AND serving_revision_uuid IS NOT NULL
  AND deleted_at IS NULL;

CREATE VIEW mkb_v_gates_open AS
SELECT *
FROM mkb_execution_gates
WHERE status = 'open';

CREATE VIEW mkb_v_domain_events_by_trace AS
SELECT *
FROM mkb_domain_events;

-- S08/S09 half-write resolution: a vector can be exposed only when it is
-- indexed, in an active namespace, matches an active pointer, and has the
-- durable proof named by that pointer for the same generation/index tuple.
CREATE VIEW mkb_v_vectors_active AS
SELECT
  r.vector_record_uuid,
  r.team_uuid,
  r.namespace_uuid,
  n.namespace_key,
  n.distance_metric,
  r.generation_artifact_uuid,
  r.generation_artifact_type,
  r.block_or_unit_id,
  r.channel,
  r.intake_source_uuid,
  r.intake_item_uuid,
  r.intake_revision_uuid,
  r.industry_domain,
  r.content_digest,
  r.embedding_model,
  r.embedding_model_key,
  r.embedding_model_version,
  r.adapter_kind,
  r.dimension,
  r.publication_state,
  r.index_generation,
  r.embedded_at,
  p.last_proof_uuid AS publication_proof_uuid
FROM mkb_vector_records AS r
JOIN mkb_vector_namespaces AS n
  ON n.namespace_uuid = r.namespace_uuid
 AND n.team_uuid = r.team_uuid
JOIN mkb_index_active_pointers AS p
  ON p.team_uuid = r.team_uuid
 AND p.intake_item_uuid = r.intake_item_uuid
 AND p.namespace_uuid = r.namespace_uuid
 AND p.active_index_generation = r.index_generation
 AND p.lifecycle_state = 'active'
JOIN mkb_publication_proofs AS proof
  ON proof.proof_uuid = p.last_proof_uuid
 AND proof.team_uuid = r.team_uuid
 AND proof.intake_item_uuid = r.intake_item_uuid
 AND proof.namespace_uuid = r.namespace_uuid
 AND proof.generation_artifact_uuid = r.generation_artifact_uuid
 AND proof.generation_artifact_type = r.generation_artifact_type
 AND proof.embedding_model_key = r.embedding_model_key
 AND proof.embedding_model_version = r.embedding_model_version
 AND proof.adapter_kind = r.adapter_kind
 AND proof.dimension = r.dimension
 AND proof.index_generation = r.index_generation
WHERE r.deleted_at IS NULL
  AND r.publication_state = 'indexed'
  AND n.status = 'active'
  AND n.deleted_at IS NULL;

CREATE VIEW mkb_v_vector_by_generation AS
SELECT
  team_uuid,
  namespace_uuid,
  generation_artifact_uuid,
  generation_artifact_type,
  embedding_model_key,
  embedding_model_version,
  adapter_kind,
  index_generation,
  channel,
  COUNT(*) AS vector_count,
  MIN(embedded_at) AS first_embedded_at,
  MAX(embedded_at) AS last_embedded_at
FROM mkb_v_vectors_active
GROUP BY team_uuid, namespace_uuid, generation_artifact_uuid,
         generation_artifact_type, embedding_model_key,
         embedding_model_version, adapter_kind, index_generation, channel;

CREATE VIEW mkb_v_vector_namespaces_active AS
SELECT *
FROM mkb_vector_namespaces
WHERE status = 'active'
  AND deleted_at IS NULL;

CREATE VIEW mkb_v_adapter_bindings_enabled AS
SELECT *
FROM mkb_adapter_bindings
WHERE enabled = 1;

CREATE VIEW mkb_v_model_catalog_active AS
SELECT *
FROM mkb_model_catalog
WHERE status = 'active';

COMMIT;
