-- NHX1 P2-02: upload session ownership and durable physical convergence.

BEGIN;

CREATE TABLE mkb_object_upload_sessions (
  upload_session_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  session_token_hash TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  command_fingerprint TEXT NOT NULL,
  staging_id TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'receiving'
    CHECK (state IN ('receiving','prepared','promoted','committed','reserved','consumed','cancelled','expired','failed')),
  stored_object_uuid TEXT,
  prepared_content_digest TEXT
    CHECK (prepared_content_digest IS NULL OR
           (length(prepared_content_digest) = 64
            AND prepared_content_digest NOT GLOB '*[^0-9a-f]*')),
  prepared_size_bytes INTEGER CHECK (prepared_size_bytes IS NULL OR prepared_size_bytes >= 0),
  media_type TEXT,
  pending_reference_uuid TEXT UNIQUE,
  reserved_task_uuid TEXT,
  reserved_task_generation INTEGER CHECK (reserved_task_generation IS NULL OR reserved_task_generation >= 1),
  row_revision INTEGER NOT NULL DEFAULT 0 CHECK (row_revision >= 0),
  expires_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  prepared_at TEXT,
  promoted_at TEXT,
  committed_at TEXT,
  terminal_at TEXT,
  last_error_code TEXT,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (team_uuid, session_token_hash),
  UNIQUE (team_uuid, idempotency_key),
  UNIQUE (team_uuid, staging_id),
  CHECK (state NOT IN ('prepared','promoted','committed','reserved','consumed') OR
         (prepared_content_digest IS NOT NULL AND prepared_size_bytes IS NOT NULL)),
  CHECK (state NOT IN ('promoted','committed','reserved','consumed') OR stored_object_uuid IS NOT NULL),
  CHECK (state NOT IN ('committed','reserved','consumed') OR pending_reference_uuid IS NOT NULL),
  CHECK (state <> 'reserved' OR (reserved_task_uuid IS NOT NULL AND reserved_task_generation IS NOT NULL)),
  CHECK (state NOT IN ('consumed','cancelled','expired','failed') OR terminal_at IS NOT NULL),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid),
  FOREIGN KEY (team_uuid, stored_object_uuid)
    REFERENCES mkb_stored_objects(team_uuid, stored_object_uuid),
  FOREIGN KEY (pending_reference_uuid) REFERENCES mkb_object_references(reference_uuid),
  FOREIGN KEY (team_uuid, reserved_task_uuid)
    REFERENCES mkb_tasks(team_uuid, task_uuid)
);

ALTER TABLE mkb_object_references ADD COLUMN upload_session_uuid TEXT;
CREATE UNIQUE INDEX ux_nhx1_upload_pending_session
  ON mkb_object_references(team_uuid, upload_session_uuid)
  WHERE purpose='upload_pending' AND released_at IS NULL AND upload_session_uuid IS NOT NULL;

CREATE TABLE mkb_object_promotion_journals (
  promotion_journal_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  upload_session_uuid TEXT NOT NULL,
  staging_id TEXT NOT NULL,
  stored_object_uuid TEXT,
  state TEXT NOT NULL DEFAULT 'receiving'
    CHECK (state IN ('receiving','prepared','promoted','catalog_committed','reconciled','rolled_back','failed')),
  expected_content_digest TEXT,
  expected_size_bytes INTEGER CHECK (expected_size_bytes IS NULL OR expected_size_bytes >= 0),
  row_revision INTEGER NOT NULL DEFAULT 0 CHECK (row_revision >= 0),
  predecessor_journal_uuid TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  terminal_at TEXT,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (upload_session_uuid),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid),
  FOREIGN KEY (upload_session_uuid) REFERENCES mkb_object_upload_sessions(upload_session_uuid),
  FOREIGN KEY (team_uuid, stored_object_uuid)
    REFERENCES mkb_stored_objects(team_uuid, stored_object_uuid),
  FOREIGN KEY (predecessor_journal_uuid) REFERENCES mkb_object_promotion_journals(promotion_journal_uuid)
);

CREATE TABLE mkb_object_promotion_transitions (
  transition_uuid TEXT PRIMARY KEY,
  promotion_journal_uuid TEXT NOT NULL,
  team_uuid TEXT NOT NULL,
  state_before TEXT,
  state_after TEXT NOT NULL
    CHECK (state_after IN ('receiving','prepared','promoted','catalog_committed','reconciled','rolled_back','failed')),
  expected_row_revision INTEGER NOT NULL CHECK (expected_row_revision >= 0),
  actual_row_revision INTEGER NOT NULL CHECK (actual_row_revision >= 0),
  transition_digest TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (promotion_journal_uuid) REFERENCES mkb_object_promotion_journals(promotion_journal_uuid),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid)
);

CREATE TABLE mkb_object_deletion_jobs (
  deletion_job_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  stored_object_uuid TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'pending'
    CHECK (state IN ('pending','blocked','quarantined','tombstoned','destroyed','failed')),
  expected_content_digest TEXT NOT NULL,
  expected_reference_snapshot_digest TEXT NOT NULL,
  quarantine_ref TEXT,
  delete_proof_uuid TEXT,
  predecessor_job_uuid TEXT,
  row_revision INTEGER NOT NULL DEFAULT 0 CHECK (row_revision >= 0),
  available_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  terminal_at TEXT,
  last_error_code TEXT,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (team_uuid, stored_object_uuid, expected_reference_snapshot_digest),
  CHECK (state <> 'quarantined' OR quarantine_ref IS NOT NULL),
  CHECK (state <> 'destroyed' OR (delete_proof_uuid IS NOT NULL AND terminal_at IS NOT NULL)),
  FOREIGN KEY (team_uuid, stored_object_uuid)
    REFERENCES mkb_stored_objects(team_uuid, stored_object_uuid),
  FOREIGN KEY (delete_proof_uuid) REFERENCES mkb_object_delete_proofs(delete_proof_uuid),
  FOREIGN KEY (predecessor_job_uuid) REFERENCES mkb_object_deletion_jobs(deletion_job_uuid)
);

CREATE TABLE mkb_cleanup_jobs (
  cleanup_job_uuid TEXT PRIMARY KEY,
  intent_uuid TEXT NOT NULL,
  team_uuid TEXT NOT NULL,
  intake_item_uuid TEXT NOT NULL,
  item_epoch INTEGER NOT NULL CHECK (item_epoch >= 0),
  owner_graph_digest TEXT NOT NULL,
  required_substrate_set_digest TEXT NOT NULL,
  retention_until TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'pending'
    CHECK (state IN ('pending','blocked','running','completed','failed')),
  blocked_reason TEXT,
  row_revision INTEGER NOT NULL DEFAULT 0 CHECK (row_revision >= 0),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  completed_at TEXT,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (intent_uuid),
  CHECK (state <> 'blocked' OR blocked_reason IS NOT NULL),
  CHECK (state <> 'completed' OR completed_at IS NOT NULL),
  FOREIGN KEY (intent_uuid) REFERENCES mkb_intake_cleanup_intents(intent_uuid),
  FOREIGN KEY (team_uuid, intake_item_uuid)
    REFERENCES mkb_intake_items(team_uuid, intake_item_uuid)
);

CREATE TABLE mkb_cleanup_job_steps (
  cleanup_step_uuid TEXT PRIMARY KEY,
  cleanup_job_uuid TEXT NOT NULL,
  team_uuid TEXT NOT NULL,
  substrate_kind TEXT NOT NULL
    CHECK (substrate_kind IN ('intake_artifact','derived_generation','vector_projection','object_reference','object_gc')),
  ordinal INTEGER NOT NULL CHECK (ordinal >= 1),
  target_set_digest TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'pending'
    CHECK (state IN ('pending','blocked','running','completed','failed')),
  attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  proof_uuid TEXT,
  blocked_reason TEXT,
  row_revision INTEGER NOT NULL DEFAULT 0 CHECK (row_revision >= 0),
  available_at TEXT NOT NULL,
  started_at TEXT,
  terminal_at TEXT,
  last_error_code TEXT,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (cleanup_job_uuid, substrate_kind),
  UNIQUE (cleanup_job_uuid, ordinal),
  FOREIGN KEY (cleanup_job_uuid) REFERENCES mkb_cleanup_jobs(cleanup_job_uuid),
  FOREIGN KEY (proof_uuid) REFERENCES mkb_intake_cleanup_proofs(proof_uuid),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid)
);

CREATE TABLE mkb_legacy_object_reference_verdicts (
  verdict_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  reference_uuid TEXT NOT NULL,
  verdict TEXT NOT NULL CHECK (verdict IN ('legacy_unverifiable','verified_exact_owner','invalid')),
  reason_code TEXT NOT NULL,
  checked_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (reference_uuid),
  FOREIGN KEY (reference_uuid) REFERENCES mkb_object_references(reference_uuid),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid)
);

CREATE INDEX ix_nhx1_upload_session_state
  ON mkb_object_upload_sessions(team_uuid, state, expires_at, upload_session_uuid);
CREATE INDEX ix_nhx1_promotion_state
  ON mkb_object_promotion_journals(state, updated_at, promotion_journal_uuid);
CREATE INDEX ix_nhx1_deletion_state
  ON mkb_object_deletion_jobs(state, available_at, deletion_job_uuid);
CREATE INDEX ix_nhx1_cleanup_state
  ON mkb_cleanup_jobs(team_uuid, state, retention_until, cleanup_job_uuid);
CREATE INDEX ix_nhx1_cleanup_step_state
  ON mkb_cleanup_job_steps(state, available_at, cleanup_step_uuid);

COMMIT;
