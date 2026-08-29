-- M-NH-02: typed append-only representation authority and ordered path history.

BEGIN;

CREATE TABLE mkb_representation_facts (
  representation_fact_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  execution_uuid TEXT NOT NULL,
  process_uuid TEXT NOT NULL,
  step_key TEXT NOT NULL,
  fact_kind TEXT NOT NULL CHECK (fact_kind IN ('acquire', 'decode', 'print')),
  schema_version TEXT NOT NULL CHECK (schema_version = 'mkb.representation-fact.v1'),
  capability TEXT NOT NULL,
  representation_kind TEXT NOT NULL,
  declared_media_type TEXT,
  detected_media_type TEXT,
  verified_media_type TEXT NOT NULL,
  raw_byte_digest TEXT NOT NULL
    CHECK (length(raw_byte_digest) = 64 AND raw_byte_digest NOT GLOB '*[^0-9a-f]*'),
  raw_byte_size INTEGER NOT NULL CHECK (raw_byte_size >= 0),
  text_layer TEXT NOT NULL
    CHECK (text_layer IN ('present','absent','encrypted','corrupt','not_applicable','unknown')),
  main_text_presence TEXT NOT NULL CHECK (main_text_presence IN ('present','absent','unknown')),
  media_family TEXT NOT NULL CHECK (media_family IN ('text','pdf','image','opaque')),
  canonicalizer_key TEXT NOT NULL,
  canonicalizer_version TEXT NOT NULL,
  observer_key TEXT NOT NULL,
  observer_version TEXT NOT NULL,
  profile_identity TEXT,
  fact_digest TEXT NOT NULL
    CHECK (length(fact_digest) = 64 AND fact_digest NOT GLOB '*[^0-9a-f]*'),
  created_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (execution_uuid, step_key),
  FOREIGN KEY (team_uuid, execution_uuid)
    REFERENCES mkb_executions(team_uuid, execution_uuid),
  FOREIGN KEY (process_uuid) REFERENCES mkb_processes(process_uuid)
);

CREATE TABLE mkb_acquire_decode_history (
  history_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  execution_uuid TEXT NOT NULL,
  process_uuid TEXT NOT NULL,
  step_key TEXT NOT NULL,
  ordinal INTEGER NOT NULL CHECK (ordinal >= 1),
  capability TEXT NOT NULL,
  representation_fact_uuid TEXT NOT NULL,
  representation_fact_digest TEXT NOT NULL
    CHECK (length(representation_fact_digest) = 64
           AND representation_fact_digest NOT GLOB '*[^0-9a-f]*'),
  raw_byte_digest TEXT NOT NULL
    CHECK (length(raw_byte_digest) = 64 AND raw_byte_digest NOT GLOB '*[^0-9a-f]*'),
  representation_kind TEXT NOT NULL,
  observer_version TEXT NOT NULL,
  representation_path_digest TEXT NOT NULL
    CHECK (length(representation_path_digest) = 64
           AND representation_path_digest NOT GLOB '*[^0-9a-f]*'),
  created_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (execution_uuid, step_key),
  UNIQUE (execution_uuid, ordinal),
  FOREIGN KEY (team_uuid, execution_uuid)
    REFERENCES mkb_executions(team_uuid, execution_uuid),
  FOREIGN KEY (process_uuid) REFERENCES mkb_processes(process_uuid),
  FOREIGN KEY (representation_fact_uuid)
    REFERENCES mkb_representation_facts(representation_fact_uuid)
);

CREATE INDEX ix_mkb_representation_fact_execution
  ON mkb_representation_facts(team_uuid, execution_uuid, fact_kind, created_at);
CREATE INDEX ix_mkb_acquire_decode_history_path
  ON mkb_acquire_decode_history(team_uuid, execution_uuid, ordinal);

COMMIT;
