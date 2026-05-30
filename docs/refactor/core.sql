PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
PRAGMA temp_store = MEMORY;

BEGIN;

-- -----------------------------------------------------------------------------
-- core.db
-- SSOT for relational data, workflow state, scheduling, restart/purge control,
-- and auditability. Large payloads and vector blobs do NOT belong here.
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'disabled', 'deleted')),
    metadata_json TEXT
        CHECK (metadata_json IS NULL OR json_valid(metadata_json)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS teams (
    id TEXT PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'disabled', 'deleted')),
    metadata_json TEXT
        CHECK (metadata_json IS NULL OR json_valid(metadata_json)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS team_members (
    team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL
        CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('invited', 'active', 'suspended', 'removed')),
    invited_by_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    joined_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY (team_id, user_id)
);

CREATE TABLE IF NOT EXISTS api_keys (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    key_prefix TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    scopes_json TEXT
        CHECK (scopes_json IS NULL OR json_valid(scopes_json)),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'revoked', 'expired')),
    created_by_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    last_used_at TEXT,
    expires_at TEXT,
    revoked_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    team_id TEXT REFERENCES teams(id) ON DELETE SET NULL,
    token_hash TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'expired', 'revoked')),
    last_seen_at TEXT,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS uploads (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    source_kind TEXT NOT NULL
        CHECK (source_kind IN ('file', 'url', 'api')),
    object_key TEXT,
    original_filename TEXT,
    mime_type TEXT,
    size_bytes INTEGER CHECK (size_bytes IS NULL OR size_bytes >= 0),
    checksum_sha256 TEXT,
    created_by_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'initiated'
        CHECK (status IN ('initiated', 'uploaded', 'confirmed', 'abandoned', 'failed')),
    metadata_json TEXT
        CHECK (metadata_json IS NULL OR json_valid(metadata_json)),
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    upload_id TEXT REFERENCES uploads(id) ON DELETE SET NULL,
    source_kind TEXT NOT NULL
        CHECK (source_kind IN ('file', 'url', 'api')),
    source_uri TEXT,
    external_ref TEXT,
    title TEXT,
    mime_type TEXT,
    language_code TEXT,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'disabled', 'deleted', 'purged')),
    metadata_json TEXT
        CHECK (metadata_json IS NULL OR json_valid(metadata_json)),
    created_by_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    canonical_uri TEXT,
    title TEXT,
    language_code TEXT,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'archived', 'deleted', 'purged')),
    latest_clean_artifact_id TEXT,
    latest_structured_artifact_id TEXT,
    latest_constructed_artifact_id TEXT,
    latest_vectorized_at TEXT,
    metadata_json TEXT
        CHECK (metadata_json IS NULL OR json_valid(metadata_json)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS static_files (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    source_id TEXT REFERENCES sources(id) ON DELETE CASCADE,
    document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,
    parent_static_file_id TEXT REFERENCES static_files(id) ON DELETE SET NULL,
    upload_id TEXT REFERENCES uploads(id) ON DELETE SET NULL,
    object_key TEXT NOT NULL,
    file_role TEXT NOT NULL
        CHECK (file_role IN ('uploaded', 'child', 'generated', 'export')),
    mime_type TEXT,
    extension TEXT,
    size_bytes INTEGER CHECK (size_bytes IS NULL OR size_bytes >= 0),
    checksum_sha256 TEXT,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'deleted', 'purged')),
    metadata_json TEXT
        CHECK (metadata_json IS NULL OR json_valid(metadata_json)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS workflow_runs (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    source_id TEXT REFERENCES sources(id) ON DELETE SET NULL,
    document_id TEXT REFERENCES documents(id) ON DELETE SET NULL,
    workflow_kind TEXT NOT NULL
        CHECK (workflow_kind IN ('ingestion', 'clean', 'rag', 'full')),
    trigger_kind TEXT NOT NULL
        CHECK (trigger_kind IN ('api', 'cli', 'system', 'restart', 'replay')),
    requested_by_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    parent_workflow_run_id TEXT REFERENCES workflow_runs(id) ON DELETE SET NULL,
    restart_of_workflow_run_id TEXT REFERENCES workflow_runs(id) ON DELETE SET NULL,
    priority INTEGER NOT NULL DEFAULT 100,
    current_stage TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'paused', 'cancelled', 'purged')),
    config_snapshot_json TEXT NOT NULL
        CHECK (json_valid(config_snapshot_json)),
    metadata_json TEXT
        CHECK (metadata_json IS NULL OR json_valid(metadata_json)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    started_at TEXT,
    finished_at TEXT,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    workflow_run_id TEXT REFERENCES workflow_runs(id) ON DELETE SET NULL,
    workflow_step_id TEXT REFERENCES workflow_steps(id) ON DELETE SET NULL,
    source_id TEXT REFERENCES sources(id) ON DELETE SET NULL,
    document_id TEXT REFERENCES documents(id) ON DELETE SET NULL,
    parent_artifact_id TEXT REFERENCES artifacts(id) ON DELETE SET NULL,
    artifact_type TEXT NOT NULL
        CHECK (artifact_type IN (
            'raw_blob',
            'raw_text',
            'cleaned_text',
            'structured_json',
            'constructed_json',
            'chunk_text',
            'export_bundle',
            'event_log',
            'debug_dump'
        )),
    storage_backend TEXT NOT NULL DEFAULT 'object_store'
        CHECK (storage_backend IN ('object_store', 'sqlite_ref')),
    object_key TEXT,
    content_hash TEXT,
    mime_type TEXT,
    size_bytes INTEGER CHECK (size_bytes IS NULL OR size_bytes >= 0),
    status TEXT NOT NULL DEFAULT 'available'
        CHECK (status IN ('available', 'superseded', 'deleted', 'purged', 'failed')),
    metadata_json TEXT
        CHECK (metadata_json IS NULL OR json_valid(metadata_json)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    workflow_run_id TEXT NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    source_artifact_id TEXT REFERENCES artifacts(id) ON DELETE SET NULL,
    content_artifact_id TEXT REFERENCES artifacts(id) ON DELETE SET NULL,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content_hash TEXT NOT NULL,
    token_count INTEGER CHECK (token_count IS NULL OR token_count >= 0),
    char_count INTEGER CHECK (char_count IS NULL OR char_count >= 0),
    section_path_json TEXT
        CHECK (section_path_json IS NULL OR json_valid(section_path_json)),
    metadata_json TEXT
        CHECK (metadata_json IS NULL OR json_valid(metadata_json)),
    vec_status TEXT NOT NULL DEFAULT 'pending_vectorize'
        CHECK (vec_status IN ('pending_vectorize', 'vectorized', 'pending_purge', 'purged', 'failed')),
    embedding_model TEXT,
    latest_vectorized_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (document_id, chunk_index),
    UNIQUE (document_id, content_hash)
);

CREATE TABLE IF NOT EXISTS workflow_steps (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    workflow_run_id TEXT NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    parent_step_id TEXT REFERENCES workflow_steps(id) ON DELETE SET NULL,
    step_key TEXT NOT NULL,
    stage TEXT NOT NULL,
    action TEXT NOT NULL,
    executor_hint TEXT,
    priority INTEGER NOT NULL DEFAULT 100,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'succeeded', 'failed', 'retry_wait', 'cancelled', 'skipped')),
    payload_json TEXT NOT NULL
        CHECK (json_valid(payload_json)),
    input_artifact_id TEXT REFERENCES artifacts(id) ON DELETE SET NULL,
    output_artifact_id TEXT REFERENCES artifacts(id) ON DELETE SET NULL,
    result_ref TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts >= 1),
    retry_backoff_seconds INTEGER NOT NULL DEFAULT 60 CHECK (retry_backoff_seconds >= 0),
    available_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    error_code TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    started_at TEXT,
    finished_at TEXT,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (workflow_run_id, step_key)
);

CREATE TABLE IF NOT EXISTS task_claims (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    workflow_run_id TEXT NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    step_id TEXT NOT NULL REFERENCES workflow_steps(id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL CHECK (attempt_number >= 1),
    claim_token TEXT NOT NULL UNIQUE,
    worker_type TEXT NOT NULL,
    worker_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'finished', 'expired', 'released', 'cancelled')),
    claimed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    lease_expires_at TEXT NOT NULL,
    last_heartbeat_at TEXT,
    released_at TEXT,
    finished_at TEXT,
    notes_json TEXT
        CHECK (notes_json IS NULL OR json_valid(notes_json))
);

CREATE TABLE IF NOT EXISTS step_attempts (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    workflow_run_id TEXT NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    step_id TEXT NOT NULL REFERENCES workflow_steps(id) ON DELETE CASCADE,
    claim_id TEXT REFERENCES task_claims(id) ON DELETE SET NULL,
    attempt_number INTEGER NOT NULL CHECK (attempt_number >= 1),
    termination_reason TEXT NOT NULL
        CHECK (termination_reason IN ('success', 'executor_failure', 'lease_timeout', 'cancelled')),
    retryable INTEGER NOT NULL DEFAULT 0 CHECK (retryable IN (0, 1)),
    error_code TEXT,
    error_message TEXT,
    metrics_json TEXT
        CHECK (metrics_json IS NULL OR json_valid(metrics_json)),
    started_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    finished_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (step_id, attempt_number)
);

CREATE TABLE IF NOT EXISTS workflow_step_links (
    id TEXT PRIMARY KEY,
    workflow_run_id TEXT NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    from_step_id TEXT NOT NULL REFERENCES workflow_steps(id) ON DELETE CASCADE,
    to_step_id TEXT NOT NULL REFERENCES workflow_steps(id) ON DELETE CASCADE,
    link_type TEXT NOT NULL DEFAULT 'next'
        CHECK (link_type IN ('next', 'fanout', 'retry', 'restart', 'purge')),
    condition_json TEXT
        CHECK (condition_json IS NULL OR json_valid(condition_json)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (from_step_id, to_step_id, link_type)
);

CREATE TABLE IF NOT EXISTS workflow_events (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    workflow_run_id TEXT NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    step_id TEXT REFERENCES workflow_steps(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    event_payload_json TEXT
        CHECK (event_payload_json IS NULL OR json_valid(event_payload_json)),
    emitted_by TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS configs (
    id TEXT PRIMARY KEY,
    team_id TEXT REFERENCES teams(id) ON DELETE CASCADE,
    config_scope TEXT NOT NULL
        CHECK (config_scope IN ('system', 'workflow', 'stage', 'provider')),
    config_key TEXT NOT NULL,
    version TEXT NOT NULL,
    content_json TEXT NOT NULL
        CHECK (json_valid(content_json)),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'deprecated')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    activated_at TEXT,
    UNIQUE (team_id, config_scope, config_key, version)
);

CREATE TABLE IF NOT EXISTS prompt_versions (
    id TEXT PRIMARY KEY,
    team_id TEXT REFERENCES teams(id) ON DELETE CASCADE,
    prompt_key TEXT NOT NULL,
    version TEXT NOT NULL,
    template_path TEXT,
    template_digest TEXT NOT NULL,
    metadata_json TEXT
        CHECK (metadata_json IS NULL OR json_valid(metadata_json)),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'deprecated')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    activated_at TEXT,
    UNIQUE (team_id, prompt_key, version)
);

CREATE TABLE IF NOT EXISTS provider_configs (
    id TEXT PRIMARY KEY,
    team_id TEXT REFERENCES teams(id) ON DELETE CASCADE,
    provider_key TEXT NOT NULL,
    version TEXT NOT NULL,
    settings_json TEXT NOT NULL
        CHECK (json_valid(settings_json)),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'deprecated')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    activated_at TEXT,
    UNIQUE (team_id, provider_key, version)
);

CREATE TABLE IF NOT EXISTS restart_requests (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    workflow_run_id TEXT NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    target_step_id TEXT REFERENCES workflow_steps(id) ON DELETE SET NULL,
    requested_by_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    mode TEXT NOT NULL
        CHECK (mode IN ('kickstart', 'recovery', 'force_recovery', 'force_kickstart')),
    scope_json TEXT NOT NULL
        CHECK (json_valid(scope_json)),
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    started_at TEXT,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS purge_requests (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    target_kind TEXT NOT NULL
        CHECK (target_kind IN ('workflow_run', 'document', 'source', 'chunk')),
    target_id TEXT NOT NULL,
    requested_by_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    include_vectors INTEGER NOT NULL DEFAULT 1 CHECK (include_vectors IN (0, 1)),
    include_objects INTEGER NOT NULL DEFAULT 0 CHECK (include_objects IN (0, 1)),
    scope_json TEXT NOT NULL
        CHECK (json_valid(scope_json)),
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    started_at TEXT,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    team_id TEXT REFERENCES teams(id) ON DELETE CASCADE,
    actor_type TEXT NOT NULL
        CHECK (actor_type IN ('user', 'api_key', 'system', 'worker')),
    actor_id TEXT,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT,
    payload_json TEXT
        CHECK (payload_json IS NULL OR json_valid(payload_json)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- -----------------------------------------------------------------------------
-- Indexes
-- -----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS ix_team_members_user ON team_members(user_id, status);
CREATE INDEX IF NOT EXISTS ix_api_keys_team_status ON api_keys(team_id, status);
CREATE INDEX IF NOT EXISTS ix_sessions_user_status ON sessions(user_id, status, expires_at);
CREATE INDEX IF NOT EXISTS ix_uploads_team_status ON uploads(team_id, status, created_at);
CREATE INDEX IF NOT EXISTS ix_sources_team_kind_status ON sources(team_id, source_kind, status);
CREATE INDEX IF NOT EXISTS ix_documents_team_source_status ON documents(team_id, source_id, status);
CREATE INDEX IF NOT EXISTS ix_static_files_document_role ON static_files(document_id, file_role, status);
CREATE INDEX IF NOT EXISTS ix_artifacts_workflow_type ON artifacts(workflow_run_id, artifact_type, status);
CREATE INDEX IF NOT EXISTS ix_artifacts_document_type ON artifacts(document_id, artifact_type, status);
CREATE INDEX IF NOT EXISTS ix_chunks_document_vec_status ON chunks(document_id, vec_status, chunk_index);
CREATE INDEX IF NOT EXISTS ix_chunks_workflow_vec_status ON chunks(workflow_run_id, vec_status, created_at);
CREATE INDEX IF NOT EXISTS ix_workflow_runs_team_status ON workflow_runs(team_id, status, created_at);
CREATE INDEX IF NOT EXISTS ix_workflow_runs_document_status ON workflow_runs(document_id, status, created_at);
CREATE INDEX IF NOT EXISTS ix_workflow_steps_team_stage_status_available
    ON workflow_steps(team_id, stage, status, available_at, priority);
CREATE INDEX IF NOT EXISTS ix_workflow_steps_run_stage_status
    ON workflow_steps(workflow_run_id, stage, status, priority);
CREATE INDEX IF NOT EXISTS ix_workflow_steps_status_available
    ON workflow_steps(status, available_at);
CREATE INDEX IF NOT EXISTS ix_task_claims_step_status_expiry
    ON task_claims(step_id, status, lease_expires_at);
CREATE INDEX IF NOT EXISTS ix_task_claims_worker_status
    ON task_claims(worker_type, worker_id, status, claimed_at);
CREATE UNIQUE INDEX IF NOT EXISTS ux_task_claims_active_step
    ON task_claims(step_id)
    WHERE status = 'active';
CREATE INDEX IF NOT EXISTS ix_step_attempts_run_step ON step_attempts(workflow_run_id, step_id, attempt_number);
CREATE INDEX IF NOT EXISTS ix_step_attempts_termination ON step_attempts(termination_reason, finished_at);
CREATE INDEX IF NOT EXISTS ix_workflow_step_links_run ON workflow_step_links(workflow_run_id, from_step_id, to_step_id);
CREATE INDEX IF NOT EXISTS ix_workflow_events_run_created ON workflow_events(workflow_run_id, created_at);
CREATE INDEX IF NOT EXISTS ix_workflow_events_step_created ON workflow_events(step_id, created_at);
CREATE INDEX IF NOT EXISTS ix_configs_lookup ON configs(team_id, config_scope, config_key, status);
CREATE INDEX IF NOT EXISTS ix_prompt_versions_lookup ON prompt_versions(team_id, prompt_key, status);
CREATE INDEX IF NOT EXISTS ix_provider_configs_lookup ON provider_configs(team_id, provider_key, status);
CREATE INDEX IF NOT EXISTS ix_restart_requests_status_created ON restart_requests(status, created_at);
CREATE INDEX IF NOT EXISTS ix_restart_requests_workflow_status ON restart_requests(workflow_run_id, status, created_at);
CREATE INDEX IF NOT EXISTS ix_purge_requests_status_created ON purge_requests(status, created_at);
CREATE INDEX IF NOT EXISTS ix_purge_requests_target_status ON purge_requests(target_kind, target_id, status);
CREATE INDEX IF NOT EXISTS ix_audit_logs_team_created ON audit_logs(team_id, created_at);
CREATE INDEX IF NOT EXISTS ix_audit_logs_target ON audit_logs(target_type, target_id, created_at);

-- -----------------------------------------------------------------------------
-- Views
-- -----------------------------------------------------------------------------

CREATE VIEW IF NOT EXISTS v_active_claims AS
SELECT
    tc.id AS claim_id,
    tc.team_id,
    tc.workflow_run_id,
    tc.step_id,
    tc.attempt_number,
    tc.claim_token,
    tc.worker_type,
    tc.worker_id,
    tc.claimed_at,
    tc.lease_expires_at,
    tc.last_heartbeat_at,
    ws.stage,
    ws.action,
    ws.priority,
    ws.available_at,
    ws.status AS step_status
FROM task_claims tc
JOIN workflow_steps ws ON ws.id = tc.step_id
WHERE tc.status = 'active';

CREATE VIEW IF NOT EXISTS v_ready_steps AS
SELECT
    ws.id AS step_id,
    ws.team_id,
    ws.workflow_run_id,
    ws.stage,
    ws.action,
    ws.executor_hint,
    ws.priority,
    ws.available_at,
    ws.attempt_count,
    ws.max_attempts,
    ws.retry_backoff_seconds,
    ws.payload_json,
    wr.workflow_kind,
    wr.status AS workflow_status
FROM workflow_steps ws
JOIN workflow_runs wr ON wr.id = ws.workflow_run_id
WHERE ws.status IN ('pending', 'retry_wait')
  AND ws.available_at <= strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
  AND wr.status IN ('pending', 'running')
  AND NOT EXISTS (
        SELECT 1
        FROM task_claims tc
        WHERE tc.step_id = ws.id
          AND tc.status = 'active'
  );

CREATE VIEW IF NOT EXISTS v_latest_step_attempts AS
SELECT sa.*
FROM step_attempts sa
JOIN (
    SELECT step_id, MAX(attempt_number) AS max_attempt_number
    FROM step_attempts
    GROUP BY step_id
) latest
  ON latest.step_id = sa.step_id
 AND latest.max_attempt_number = sa.attempt_number;

CREATE VIEW IF NOT EXISTS v_failed_steps AS
SELECT
    ws.id AS step_id,
    ws.team_id,
    ws.workflow_run_id,
    ws.stage,
    ws.action,
    ws.executor_hint,
    ws.attempt_count,
    ws.max_attempts,
    ws.available_at,
    ws.error_code,
    ws.error_message,
    ws.started_at,
    ws.finished_at,
    ws.updated_at,
    wr.workflow_kind,
    wr.status AS workflow_status,
    sa.id AS latest_attempt_id,
    sa.claim_id AS latest_claim_id,
    sa.attempt_number AS latest_attempt_number,
    sa.termination_reason AS latest_termination_reason,
    sa.retryable AS latest_retryable,
    sa.error_code AS latest_attempt_error_code,
    sa.error_message AS latest_attempt_error_message,
    sa.finished_at AS latest_attempt_finished_at
FROM workflow_steps ws
JOIN workflow_runs wr ON wr.id = ws.workflow_run_id
LEFT JOIN v_latest_step_attempts sa ON sa.step_id = ws.id
WHERE ws.status = 'failed';

CREATE VIEW IF NOT EXISTS v_workflow_run_summary AS
SELECT
    wr.id AS workflow_run_id,
    wr.team_id,
    wr.workflow_kind,
    wr.current_stage,
    wr.status,
    wr.priority,
    wr.document_id,
    COUNT(ws.id) AS total_steps,
    SUM(CASE WHEN ws.status = 'pending' THEN 1 ELSE 0 END) AS pending_steps,
    SUM(CASE WHEN ws.status = 'running' THEN 1 ELSE 0 END) AS running_steps,
    SUM(CASE WHEN ws.status = 'retry_wait' THEN 1 ELSE 0 END) AS retry_wait_steps,
    SUM(CASE WHEN ws.status = 'succeeded' THEN 1 ELSE 0 END) AS succeeded_steps,
    SUM(CASE WHEN ws.status = 'failed' THEN 1 ELSE 0 END) AS failed_steps,
    SUM(CASE WHEN ws.status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled_steps,
    SUM(CASE WHEN ws.status = 'skipped' THEN 1 ELSE 0 END) AS skipped_steps,
    wr.created_at,
    wr.started_at,
    wr.finished_at,
    wr.updated_at
FROM workflow_runs wr
LEFT JOIN workflow_steps ws ON ws.workflow_run_id = wr.id
GROUP BY
    wr.id,
    wr.team_id,
    wr.workflow_kind,
    wr.current_stage,
    wr.status,
    wr.priority,
    wr.document_id,
    wr.created_at,
    wr.started_at,
    wr.finished_at,
    wr.updated_at;

-- Core-side vector readiness summary only.
-- Final retrieval eligibility still requires vec.db row visibility.
CREATE VIEW IF NOT EXISTS v_document_vector_status AS
SELECT
    d.id AS document_id,
    d.team_id,
    d.source_id,
    d.status AS document_status,
    COUNT(c.id) AS total_chunks,
    SUM(CASE WHEN c.vec_status = 'pending_vectorize' THEN 1 ELSE 0 END) AS pending_vectorize_chunks,
    SUM(CASE WHEN c.vec_status = 'vectorized' THEN 1 ELSE 0 END) AS vectorized_chunks,
    SUM(CASE WHEN d.status = 'active' AND c.vec_status = 'vectorized' THEN 1 ELSE 0 END) AS core_eligible_chunks,
    SUM(CASE WHEN c.vec_status = 'pending_purge' THEN 1 ELSE 0 END) AS pending_purge_chunks,
    SUM(CASE WHEN c.vec_status = 'purged' THEN 1 ELSE 0 END) AS purged_chunks,
    SUM(CASE WHEN c.vec_status = 'failed' THEN 1 ELSE 0 END) AS failed_chunks,
    MAX(c.latest_vectorized_at) AS latest_vectorized_at,
    d.updated_at
FROM documents d
LEFT JOIN chunks c ON c.document_id = d.id
GROUP BY
    d.id,
    d.team_id,
    d.source_id,
    d.status,
    d.updated_at;

-- POST-KNN hydration surface only.
-- Caller must first obtain candidate chunk_ids from vec.db and then hydrate/filter here.
-- Do not use this view as the candidate source for search.
CREATE VIEW IF NOT EXISTS v_search_hydration AS
SELECT
    c.id AS chunk_id,
    c.team_id,
    c.workflow_run_id,
    c.document_id,
    d.source_id,
    c.chunk_index,
    c.source_artifact_id,
    c.content_artifact_id,
    d.title AS document_title,
    d.canonical_uri,
    d.status AS document_status,
    s.source_kind,
    s.source_uri,
    s.title AS source_title,
    s.status AS source_status,
    wr.workflow_kind,
    wr.status AS workflow_status,
    c.vec_status,
    c.embedding_model,
    c.token_count,
    c.char_count,
    c.section_path_json,
    c.latest_vectorized_at,
    CASE
        WHEN d.status = 'active' AND c.vec_status = 'vectorized' THEN 1
        ELSE 0
    END AS core_post_filter_eligible,
    CASE
        WHEN d.status <> 'active' THEN 'document_not_active'
        WHEN c.vec_status = 'pending_vectorize' THEN 'chunk_pending_vectorize'
        WHEN c.vec_status = 'pending_purge' THEN 'chunk_pending_purge'
        WHEN c.vec_status = 'purged' THEN 'chunk_purged'
        WHEN c.vec_status = 'failed' THEN 'chunk_vector_failed'
        ELSE 'eligible'
    END AS core_post_filter_reason
FROM chunks c
JOIN documents d ON d.id = c.document_id
JOIN sources s ON s.id = d.source_id
JOIN workflow_runs wr ON wr.id = c.workflow_run_id;

CREATE VIEW IF NOT EXISTS v_stale_claims AS
SELECT
    tc.id AS claim_id,
    tc.team_id,
    tc.workflow_run_id,
    tc.step_id,
    tc.claim_token,
    tc.worker_type,
    tc.worker_id,
    tc.claimed_at,
    tc.lease_expires_at,
    tc.last_heartbeat_at,
    ws.stage,
    ws.action,
    wr.workflow_kind,
    wr.status AS workflow_status
FROM task_claims tc
JOIN workflow_steps ws ON ws.id = tc.step_id
JOIN workflow_runs wr ON wr.id = tc.workflow_run_id
WHERE tc.status = 'active'
  AND tc.lease_expires_at <= strftime('%Y-%m-%dT%H:%M:%fZ', 'now');

CREATE VIEW IF NOT EXISTS v_restart_backlog AS
SELECT
    rr.id AS restart_request_id,
    rr.team_id,
    rr.workflow_run_id,
    rr.target_step_id,
    rr.mode,
    rr.status,
    rr.created_at,
    rr.started_at,
    rr.completed_at
FROM restart_requests rr
WHERE rr.status IN ('pending', 'processing');

CREATE VIEW IF NOT EXISTS v_purge_backlog AS
SELECT
    pr.id AS purge_request_id,
    pr.team_id,
    pr.target_kind,
    pr.target_id,
    pr.include_vectors,
    pr.include_objects,
    pr.status,
    pr.created_at,
    pr.started_at,
    pr.completed_at
FROM purge_requests pr
WHERE pr.status IN ('pending', 'processing');

CREATE VIEW IF NOT EXISTS v_pending_purge_chunks AS
SELECT
    c.id AS chunk_id,
    c.team_id,
    c.workflow_run_id,
    c.document_id,
    d.source_id,
    d.status AS document_status,
    c.vec_status,
    c.embedding_model,
    c.latest_vectorized_at,
    c.updated_at
FROM chunks c
JOIN documents d ON d.id = c.document_id
WHERE c.vec_status = 'pending_purge';

COMMIT;
