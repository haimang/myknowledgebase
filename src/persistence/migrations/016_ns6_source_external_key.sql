-- NS6 P4-04: idempotent intake identity is (team, source_kind, normalized_external_key).

BEGIN;

ALTER TABLE mkb_intake_sources ADD COLUMN normalized_external_key TEXT;

UPDATE mkb_intake_sources
SET normalized_external_key = (
  SELECT i.normalized_external_key
  FROM mkb_intake_items AS i
  WHERE i.team_uuid = mkb_intake_sources.team_uuid
    AND i.intake_source_uuid = mkb_intake_sources.intake_source_uuid
  ORDER BY i.created_at ASC
  LIMIT 1
)
WHERE normalized_external_key IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_intake_source_kind_external_key
  ON mkb_intake_sources(team_uuid, source_kind, normalized_external_key)
  WHERE normalized_external_key IS NOT NULL;

COMMIT;
