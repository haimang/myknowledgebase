-- NS1 catalog invariants: one active version per prompt_id, json rows must
-- carry a JSON-array profile, and non-json rows must not.  This is still a
-- column-level promotion of mkb_prompt_hash_pointers, not a new required table.

BEGIN;

UPDATE mkb_prompt_hash_pointers
SET status = 'retired'
WHERE status = 'active'
  AND rowid NOT IN (
    SELECT keep.rowid
    FROM mkb_prompt_hash_pointers AS keep
    WHERE keep.status = 'active'
      AND keep.prompt_version = (
        SELECT candidate.prompt_version
        FROM mkb_prompt_hash_pointers AS candidate
        WHERE candidate.prompt_id = keep.prompt_id
          AND candidate.status = 'active'
        ORDER BY CAST(substr(candidate.prompt_version, 2) AS INTEGER) DESC,
                 candidate.prompt_version DESC
        LIMIT 1
      )
  );

CREATE UNIQUE INDEX IF NOT EXISTS ux_mkb_prompt_catalog_one_active
  ON mkb_prompt_hash_pointers(prompt_id)
  WHERE status = 'active';

CREATE TRIGGER IF NOT EXISTS trg_mkb_prompt_catalog_profile_insert
BEFORE INSERT ON mkb_prompt_hash_pointers
BEGIN
  SELECT CASE
    WHEN NEW.role = 'json' AND (
      NEW.granularity_set IS NULL
      OR json_valid(NEW.granularity_set) = 0
      OR json_type(NEW.granularity_set) != 'array'
      OR json_array_length(NEW.granularity_set) < 1
    ) THEN RAISE(ABORT, 'json prompt requires granularity_set JSON array')
    WHEN NEW.role != 'json' AND NEW.granularity_set IS NOT NULL
      THEN RAISE(ABORT, 'non-json prompt must not declare granularity_set')
  END;
END;

CREATE TRIGGER IF NOT EXISTS trg_mkb_prompt_catalog_profile_update
BEFORE UPDATE OF role, granularity_set ON mkb_prompt_hash_pointers
BEGIN
  SELECT CASE
    WHEN NEW.role = 'json' AND (
      NEW.granularity_set IS NULL
      OR json_valid(NEW.granularity_set) = 0
      OR json_type(NEW.granularity_set) != 'array'
      OR json_array_length(NEW.granularity_set) < 1
    ) THEN RAISE(ABORT, 'json prompt requires granularity_set JSON array')
    WHEN NEW.role != 'json' AND NEW.granularity_set IS NOT NULL
      THEN RAISE(ABORT, 'non-json prompt must not declare granularity_set')
  END;
END;

COMMIT;
