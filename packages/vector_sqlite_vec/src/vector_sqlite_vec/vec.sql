PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = OFF;
PRAGMA busy_timeout = 5000;
PRAGMA temp_store = MEMORY;

BEGIN;

-- -----------------------------------------------------------------------------
-- vec.db
-- SSOT for vector indexing. This database is intentionally loosely coupled to
-- core.db and uses logical keys only. The deployment assumes one primary
-- embedding dimension per environment. V1 default: 1536.
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS vector_namespaces (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL,
    namespace_key TEXT NOT NULL,
    description TEXT,
    embedding_model TEXT NOT NULL,
    embedding_dimension INTEGER NOT NULL CHECK (embedding_dimension = 1536),
    distance_metric TEXT NOT NULL DEFAULT 'cosine'
        CHECK (distance_metric IN ('cosine', 'l2', 'inner_product')),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'disabled', 'deleted')),
    metadata_json TEXT
        CHECK (metadata_json IS NULL OR json_valid(metadata_json)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at TEXT,
    UNIQUE (team_id, namespace_key)
);

CREATE TABLE IF NOT EXISTS vector_records (
    chunk_id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL,
    workflow_run_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    namespace_id TEXT NOT NULL,
    embedding_rowid INTEGER NOT NULL UNIQUE,
    embedding_model TEXT NOT NULL,
    embedding_dimension INTEGER NOT NULL CHECK (embedding_dimension = 1536),
    content_hash TEXT NOT NULL,
    metadata_json TEXT
        CHECK (metadata_json IS NULL OR json_valid(metadata_json)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at TEXT,
    CHECK (deleted_at IS NULL OR deleted_at >= created_at)
);

-- sqlite-vec virtual table
-- If the active embedding model changes dimension, this virtual table must be
-- recreated as part of a controlled schema migration.
-- Application writes must keep chunk_embedding_index.rowid =
-- vector_records.embedding_rowid so post-KNN rowid -> chunk_id mapping remains valid.
CREATE VIRTUAL TABLE IF NOT EXISTS chunk_embedding_index USING vec0(
    embedding float[1536]
);

-- -----------------------------------------------------------------------------
-- Indexes
-- -----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS ix_vector_namespaces_team_status
    ON vector_namespaces(team_id, status, namespace_key);
CREATE INDEX IF NOT EXISTS ix_vector_records_namespace
    ON vector_records(namespace_id, deleted_at, created_at);
CREATE INDEX IF NOT EXISTS ix_vector_records_document
    ON vector_records(document_id, deleted_at, created_at);
CREATE INDEX IF NOT EXISTS ix_vector_records_workflow
    ON vector_records(workflow_run_id, deleted_at, created_at);
CREATE INDEX IF NOT EXISTS ix_vector_records_team_namespace
    ON vector_records(team_id, namespace_id, deleted_at);
CREATE INDEX IF NOT EXISTS ix_vector_records_content_hash
    ON vector_records(content_hash, deleted_at);

-- -----------------------------------------------------------------------------
-- Views
-- -----------------------------------------------------------------------------

CREATE VIEW IF NOT EXISTS v_active_vector_namespaces AS
SELECT
    vn.id AS namespace_id,
    vn.team_id,
    vn.namespace_key,
    vn.description,
    vn.embedding_model,
    vn.embedding_dimension,
    vn.distance_metric,
    vn.created_at,
    vn.updated_at
FROM vector_namespaces vn
WHERE vn.deleted_at IS NULL
  AND vn.status = 'active';

-- POST-KNN rowid -> chunk mapping surface.
-- Caller must scope production queries by team_id and resolve namespace before querying.
-- Final retrieval eligibility is decided after core.db hydration/post-filter.
CREATE VIEW IF NOT EXISTS v_active_vector_records AS
SELECT
    vr.chunk_id,
    vr.team_id,
    vr.workflow_run_id,
    vr.document_id,
    vn.namespace_id,
    vn.namespace_key,
    vn.distance_metric,
    vr.embedding_rowid,
    vr.embedding_model,
    vr.embedding_dimension,
    vr.content_hash,
    vr.metadata_json,
    vr.created_at,
    vr.updated_at
FROM vector_records vr
JOIN v_active_vector_namespaces vn ON vn.namespace_id = vr.namespace_id
WHERE vr.deleted_at IS NULL;

-- Vec-side operational stats only.
-- active_vector_count may temporarily exceed truly retrievable chunks during the
-- pending_purge window before vec.db soft deletion completes.
CREATE VIEW IF NOT EXISTS v_namespace_stats AS
SELECT
    vn.id AS namespace_id,
    vn.team_id,
    vn.namespace_key,
    vn.embedding_model,
    vn.embedding_dimension,
    vn.distance_metric,
    vn.status,
    COUNT(vr.chunk_id) AS active_vector_count,
    MIN(vr.created_at) AS first_vector_created_at,
    MAX(vr.updated_at) AS last_vector_updated_at
FROM vector_namespaces vn
LEFT JOIN vector_records vr
       ON vr.namespace_id = vn.id
      AND vr.deleted_at IS NULL
WHERE vn.deleted_at IS NULL
GROUP BY
    vn.id,
    vn.team_id,
    vn.namespace_key,
    vn.embedding_model,
    vn.embedding_dimension,
    vn.distance_metric,
    vn.status;

COMMIT;
