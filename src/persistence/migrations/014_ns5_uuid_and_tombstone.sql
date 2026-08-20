-- NS5 P2: rewrite 010's 32-hex catalog UUIDs to RFC-4122 hyphenated form,
-- and make the stored-object digest unique only among live (non-tombstone) rows.

BEGIN;

UPDATE mkb_model_catalog
SET model_uuid =
  substr(model_uuid, 1, 8) || '-' ||
  substr(model_uuid, 9, 4) || '-' ||
  substr(model_uuid, 13, 4) || '-' ||
  substr(model_uuid, 17, 4) || '-' ||
  substr(model_uuid, 21, 12)
WHERE length(model_uuid) = 32
  AND instr(model_uuid, '-') = 0
  AND model_uuid GLOB '[0-9a-f]*';

DROP INDEX IF EXISTS ux_obj_stored_digest_size;
CREATE UNIQUE INDEX IF NOT EXISTS ux_obj_stored_digest_size_live
  ON mkb_stored_objects(team_uuid, content_digest, size_bytes)
  WHERE tombstoned_at IS NULL;

COMMIT;
