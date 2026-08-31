-- NHX1 P2-04/P2-05: durable operation ownership, receipts, registries, and cutover state.

BEGIN;

ALTER TABLE mkb_outbox ADD COLUMN owner_kind TEXT;
ALTER TABLE mkb_outbox ADD COLUMN owner_uuid TEXT;
ALTER TABLE mkb_outbox ADD COLUMN owner_generation INTEGER
  CHECK (owner_generation IS NULL OR owner_generation >= 0);
ALTER TABLE mkb_outbox ADD COLUMN delivery_generation INTEGER NOT NULL DEFAULT 1
  CHECK (delivery_generation >= 1);
ALTER TABLE mkb_outbox ADD COLUMN criticality TEXT NOT NULL DEFAULT 'critical'
  CHECK (criticality IN ('critical','advisory'));
ALTER TABLE mkb_outbox ADD COLUMN attempt_budget INTEGER NOT NULL DEFAULT 8
  CHECK (attempt_budget >= 1);
ALTER TABLE mkb_outbox ADD COLUMN dead_error_code TEXT;
ALTER TABLE mkb_outbox ADD COLUMN retry_of_outbox_id TEXT;
ALTER TABLE mkb_outbox ADD COLUMN row_revision INTEGER NOT NULL DEFAULT 0
  CHECK (row_revision >= 0);

CREATE TABLE mkb_outbox_kind_definitions (
  kind TEXT PRIMARY KEY,
  definition_version TEXT NOT NULL,
  definition_digest TEXT NOT NULL,
  owner_kind TEXT NOT NULL,
  criticality TEXT NOT NULL CHECK (criticality IN ('critical','advisory')),
  attempt_budget INTEGER NOT NULL CHECK (attempt_budget >= 1),
  dead_error_code TEXT NOT NULL,
  requeue_policy TEXT NOT NULL CHECK (requeue_policy IN ('generation_fenced','forbidden','advisory_only')),
  registered_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE mkb_command_receipts (
  command_receipt_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  command_kind TEXT NOT NULL,
  target_kind TEXT NOT NULL,
  target_uuid TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  command_fingerprint TEXT NOT NULL,
  expected_generation INTEGER CHECK (expected_generation IS NULL OR expected_generation >= 0),
  observed_generation INTEGER CHECK (observed_generation IS NULL OR observed_generation >= 0),
  disposition TEXT NOT NULL CHECK (disposition IN ('applied','replayed','noop','rejected')),
  result_ref TEXT,
  result_digest TEXT,
  error_code TEXT,
  first_applied_at TEXT,
  decided_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (team_uuid, command_kind, target_kind, target_uuid, idempotency_key),
  CHECK ((disposition = 'applied' AND first_applied_at IS NOT NULL) OR disposition <> 'applied'),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid)
);

CREATE TABLE mkb_process_capability_definitions (
  process_key TEXT NOT NULL,
  contract_version TEXT NOT NULL,
  definition_digest TEXT NOT NULL,
  handler_key TEXT NOT NULL,
  deployment_roles_json TEXT NOT NULL,
  supply_requirements_json TEXT NOT NULL,
  side_effect_class TEXT NOT NULL
    CHECK (side_effect_class IN ('pure','durable_idempotent','external_idempotent','external_nonrepeatable')),
  replay_law TEXT NOT NULL
    CHECK (replay_law IN ('recompute','frozen_input','effect_once','verify_then_retry')),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','disabled','retired')),
  registered_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (process_key, contract_version)
);

CREATE TABLE mkb_error_definitions (
  error_code TEXT PRIMARY KEY,
  definition_version TEXT NOT NULL,
  category TEXT NOT NULL
    CHECK (category IN ('validation','conflict','dependency','fence','integrity','security','internal')),
  http_status INTEGER NOT NULL CHECK (http_status BETWEEN 400 AND 599),
  retryable INTEGER NOT NULL CHECK (retryable IN (0,1)),
  public_message TEXT NOT NULL,
  definition_digest TEXT NOT NULL,
  registered_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  CHECK (error_code = upper(error_code) AND error_code NOT GLOB '*[^A-Z0-9_]*')
);

CREATE TABLE mkb_error_aliases (
  legacy_code TEXT PRIMARY KEY,
  canonical_error_code TEXT NOT NULL,
  route_version TEXT NOT NULL,
  registered_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (canonical_error_code) REFERENCES mkb_error_definitions(error_code)
);

CREATE TABLE mkb_operational_signal_definitions (
  signal_key TEXT PRIMARY KEY,
  definition_version TEXT NOT NULL,
  definition_digest TEXT NOT NULL,
  severity TEXT NOT NULL CHECK (severity IN ('info','warn','error','critical')),
  emitter_key TEXT NOT NULL,
  metric_name TEXT,
  alert_id TEXT,
  runbook_ref TEXT NOT NULL,
  owner_component TEXT NOT NULL,
  registered_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE mkb_nhx1_migration_state (
  migration_key TEXT PRIMARY KEY,
  stage TEXT NOT NULL CHECK (stage IN ('expand','backfill','validate','cutover','contract')),
  status TEXT NOT NULL CHECK (status IN ('pending','running','blocked','completed')),
  cursor_value TEXT,
  processed_count INTEGER NOT NULL DEFAULT 0 CHECK (processed_count >= 0),
  mismatch_count INTEGER NOT NULL DEFAULT 0 CHECK (mismatch_count >= 0),
  row_revision INTEGER NOT NULL DEFAULT 0 CHECK (row_revision >= 0),
  started_at TEXT,
  updated_at TEXT NOT NULL,
  completed_at TEXT,
  last_error_code TEXT,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  CHECK (status <> 'completed' OR completed_at IS NOT NULL)
);

CREATE TABLE mkb_nhx1_shadow_mismatches (
  mismatch_uuid TEXT PRIMARY KEY,
  migration_key TEXT NOT NULL,
  team_uuid TEXT,
  aggregate_kind TEXT NOT NULL,
  aggregate_uuid_hash TEXT NOT NULL,
  old_digest TEXT NOT NULL,
  new_digest TEXT NOT NULL,
  mismatch_kind TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  resolved_at TEXT,
  resolution_code TEXT,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (migration_key) REFERENCES mkb_nhx1_migration_state(migration_key),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid)
);

CREATE TABLE mkb_nhx1_cutover_state (
  cutover_key TEXT PRIMARY KEY,
  writer_mode TEXT NOT NULL CHECK (writer_mode IN ('legacy','dual','v2_only')),
  reader_mode TEXT NOT NULL CHECK (reader_mode IN ('legacy','shadow','v2')),
  admission_enabled INTEGER NOT NULL DEFAULT 1 CHECK (admission_enabled IN (0,1)),
  expected_migration_revision INTEGER NOT NULL CHECK (expected_migration_revision >= 0),
  row_revision INTEGER NOT NULL DEFAULT 0 CHECK (row_revision >= 0),
  updated_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX ix_nhx1_outbox_owner
  ON mkb_outbox(team_uuid, owner_kind, owner_uuid, owner_generation, status);
CREATE INDEX ix_nhx1_outbox_predecessor ON mkb_outbox(retry_of_outbox_id);
CREATE INDEX ix_nhx1_receipt_target
  ON mkb_command_receipts(team_uuid, target_kind, target_uuid, decided_at);
CREATE INDEX ix_nhx1_shadow_open
  ON mkb_nhx1_shadow_mismatches(migration_key, resolved_at, observed_at);

COMMIT;
