-- NHX1 P5-03: immutable identity fences for legacy evidence authorities.

BEGIN;

CREATE TRIGGER ck_nhx1_generation_artifact_identity
BEFORE UPDATE OF generation_artifact_uuid,artifact_type,content_digest,stored_object_uuid,logical_handle
ON mkb_generation_artifacts
WHEN OLD.generation_artifact_uuid IS NOT NEW.generation_artifact_uuid
  OR OLD.artifact_type IS NOT NEW.artifact_type
  OR OLD.content_digest IS NOT NEW.content_digest
  OR OLD.stored_object_uuid IS NOT NEW.stored_object_uuid
  OR OLD.logical_handle IS NOT NEW.logical_handle
BEGIN
  SELECT RAISE(ABORT, 'generation artifact identity is immutable');
END;

CREATE TRIGGER ck_nhx1_intake_artifact_identity
BEFORE UPDATE OF intake_artifact_uuid,owner_snapshot_uuid,owner_revision_uuid,content_digest,stored_object_uuid,logical_handle
ON mkb_intake_artifacts
WHEN OLD.intake_artifact_uuid IS NOT NEW.intake_artifact_uuid
  OR OLD.owner_snapshot_uuid IS NOT NEW.owner_snapshot_uuid
  OR OLD.owner_revision_uuid IS NOT NEW.owner_revision_uuid
  OR OLD.content_digest IS NOT NEW.content_digest
  OR OLD.stored_object_uuid IS NOT NEW.stored_object_uuid
  OR OLD.logical_handle IS NOT NEW.logical_handle
BEGIN
  SELECT RAISE(ABORT, 'intake artifact identity is immutable');
END;

CREATE TRIGGER ck_nhx1_generation_artifact_no_delete
BEFORE DELETE ON mkb_generation_artifacts
BEGIN
  SELECT RAISE(ABORT, 'generation artifacts are append-only');
END;

CREATE TRIGGER ck_nhx1_intake_artifact_no_delete
BEFORE DELETE ON mkb_intake_artifacts
BEGIN
  SELECT RAISE(ABORT, 'intake artifacts are append-only');
END;

COMMIT;
