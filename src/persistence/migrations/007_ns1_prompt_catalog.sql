-- NS1: promote the existing prompt pointer table into the four-role catalog.
-- This is a narrow column promotion of mkb_prompt_hash_pointers, not a new
-- required table and not a second prompt-body store.  Prompt bytes remain in
-- git under data/prompts/**; these columns are immutable pointer metadata.

BEGIN;

ALTER TABLE mkb_prompt_hash_pointers ADD COLUMN prompt_id TEXT NOT NULL DEFAULT '';
ALTER TABLE mkb_prompt_hash_pointers ADD COLUMN role TEXT NOT NULL DEFAULT 'json'
  CHECK (role IN ('clean', 'markdown', 'json', 'summarizer'));
ALTER TABLE mkb_prompt_hash_pointers ADD COLUMN status TEXT NOT NULL DEFAULT 'active'
  CHECK (status IN ('active', 'retired'));
ALTER TABLE mkb_prompt_hash_pointers ADD COLUMN granularity_set TEXT
  CHECK (granularity_set IS NULL OR length(granularity_set) <= 128);

UPDATE mkb_prompt_hash_pointers
SET prompt_id = prompt_key,
    role = CASE
      WHEN prompt_key LIKE 'promptA.%' THEN 'clean'
      WHEN prompt_key LIKE 'promptC.%' THEN 'summarizer'
      ELSE 'json'
    END,
    granularity_set = CASE
      WHEN prompt_key LIKE 'promptB.%' THEN '[0,1,2]'
      ELSE NULL
    END
WHERE prompt_id = '';

CREATE UNIQUE INDEX ux_mkb_prompt_catalog_id_version
  ON mkb_prompt_hash_pointers(prompt_id, prompt_version);

CREATE INDEX ix_mkb_prompt_catalog_role_status
  ON mkb_prompt_hash_pointers(role, status, prompt_id, prompt_version);

COMMIT;
