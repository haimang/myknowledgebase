-- NH5 semantic authority: provenance is audit identity, never fingerprint input.

BEGIN;

ALTER TABLE mkb_intake_revision_semantics
ADD COLUMN value_provenance TEXT NOT NULL DEFAULT 'legacy_unverifiable'
  CHECK (value_provenance IN ('caller','mapper','system','legacy_unverifiable'));

CREATE INDEX ix_intake_semantics_provenance
  ON mkb_intake_revision_semantics(value_provenance, semantic_key);

COMMIT;
