-- M-NH-05: add the public-upload pending hold to the closed S13 purpose set.

BEGIN;

DROP VIEW mkb_v_object_live_refs;
DROP VIEW mkb_v_object_orphan_candidates;

CREATE TABLE mkb_object_references_nh4 (
  reference_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  stored_object_uuid TEXT NOT NULL,
  purpose TEXT NOT NULL CHECK (purpose IN
    ('intake_snapshot_artifact', 'intake_revision_artifact', 'clean_candidate',
     'gate_evidence', 'generation_artifact', 'process_io', 'upload_pending',
     'operator_hold', 'backup_hold')),
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

INSERT INTO mkb_object_references_nh4(
  reference_uuid,team_uuid,stored_object_uuid,purpose,owner_kind,owner_uuid,
  expected_digest,expected_size,created_at,released_at,payload_extra
)
SELECT
  reference_uuid,team_uuid,stored_object_uuid,purpose,owner_kind,owner_uuid,
  expected_digest,expected_size,created_at,released_at,payload_extra
FROM mkb_object_references;

DROP TABLE mkb_object_references;
ALTER TABLE mkb_object_references_nh4 RENAME TO mkb_object_references;

CREATE INDEX ix_obj_ref_live ON mkb_object_references(stored_object_uuid)
  WHERE released_at IS NULL;
CREATE INDEX ix_obj_ref_owner ON mkb_object_references(team_uuid, owner_kind, owner_uuid);
CREATE INDEX ix_obj_ref_purpose ON mkb_object_references(purpose, released_at);
CREATE INDEX ix_obj_ref_gc ON mkb_object_references(released_at, stored_object_uuid)
  WHERE released_at IS NOT NULL;
CREATE UNIQUE INDEX ux_obj_upload_pending_live
  ON mkb_object_references(team_uuid, stored_object_uuid, owner_kind, owner_uuid)
  WHERE purpose='upload_pending' AND released_at IS NULL;

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

COMMIT;
