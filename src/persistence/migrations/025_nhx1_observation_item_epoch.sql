-- NHX1 P2-01: Source/Observation separation and the single ItemEpoch law.

BEGIN;

CREATE TABLE mkb_intake_observations (
  observation_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  intake_source_uuid TEXT NOT NULL,
  observation_key TEXT NOT NULL,
  observation_fingerprint TEXT NOT NULL
    CHECK (length(observation_fingerprint) = 64
           AND observation_fingerprint NOT GLOB '*[^0-9a-f]*'),
  state TEXT NOT NULL DEFAULT 'reserved'
    CHECK (state IN ('reserved','acquired','accepted','failed','abandoned')),
  current_attempt_generation INTEGER NOT NULL DEFAULT 1
    CHECK (current_attempt_generation >= 1),
  owner_task_uuid TEXT,
  owner_execution_uuid TEXT,
  accepted_snapshot_uuid TEXT,
  row_revision INTEGER NOT NULL DEFAULT 0 CHECK (row_revision >= 0),
  reserved_at TEXT NOT NULL,
  acquired_at TEXT,
  accepted_at TEXT,
  terminal_at TEXT,
  last_error_code TEXT,
  compatibility_mode TEXT NOT NULL DEFAULT 'v2_explicit'
    CHECK (compatibility_mode IN ('v2_explicit','v1_task_derived','v1_registered_external_key','legacy_unverifiable')),
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (team_uuid, intake_source_uuid, observation_key),
  UNIQUE (team_uuid, observation_uuid),
  CHECK (state <> 'accepted' OR (accepted_snapshot_uuid IS NOT NULL AND accepted_at IS NOT NULL)),
  CHECK (state NOT IN ('failed','abandoned') OR terminal_at IS NOT NULL),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid),
  FOREIGN KEY (team_uuid, intake_source_uuid)
    REFERENCES mkb_intake_sources(team_uuid, intake_source_uuid),
  FOREIGN KEY (team_uuid, owner_task_uuid)
    REFERENCES mkb_tasks(team_uuid, task_uuid),
  FOREIGN KEY (team_uuid, owner_execution_uuid)
    REFERENCES mkb_executions(team_uuid, execution_uuid),
  FOREIGN KEY (team_uuid, accepted_snapshot_uuid)
    REFERENCES mkb_intake_snapshots(team_uuid, intake_snapshot_uuid)
    DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE mkb_observation_attempts (
  attempt_uuid TEXT PRIMARY KEY,
  observation_uuid TEXT NOT NULL,
  team_uuid TEXT NOT NULL,
  attempt_generation INTEGER NOT NULL CHECK (attempt_generation >= 1),
  task_uuid TEXT NOT NULL,
  execution_uuid TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'reserved'
    CHECK (state IN ('reserved','acquiring','acquired','accepted','failed','abandoned')),
  acquired_artifact_ref TEXT,
  acquired_artifact_digest TEXT
    CHECK (acquired_artifact_digest IS NULL OR
           (length(acquired_artifact_digest) = 64
            AND acquired_artifact_digest NOT GLOB '*[^0-9a-f]*')),
  expected_observation_revision INTEGER NOT NULL CHECK (expected_observation_revision >= 0),
  row_revision INTEGER NOT NULL DEFAULT 0 CHECK (row_revision >= 0),
  error_code TEXT,
  created_at TEXT NOT NULL,
  acquired_at TEXT,
  terminal_at TEXT,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (observation_uuid, attempt_generation),
  UNIQUE (team_uuid, attempt_uuid),
  CHECK (state NOT IN ('failed','abandoned') OR terminal_at IS NOT NULL),
  FOREIGN KEY (team_uuid, observation_uuid)
    REFERENCES mkb_intake_observations(team_uuid, observation_uuid),
  FOREIGN KEY (team_uuid, task_uuid)
    REFERENCES mkb_tasks(team_uuid, task_uuid),
  FOREIGN KEY (team_uuid, execution_uuid)
    REFERENCES mkb_executions(team_uuid, execution_uuid)
);

CREATE TABLE mkb_observation_attempt_transitions (
  transition_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  observation_uuid TEXT NOT NULL,
  attempt_uuid TEXT NOT NULL,
  attempt_generation INTEGER NOT NULL CHECK (attempt_generation >= 1),
  state_before TEXT,
  state_after TEXT NOT NULL
    CHECK (state_after IN ('reserved','acquiring','acquired','accepted','failed','abandoned')),
  expected_row_revision INTEGER NOT NULL CHECK (expected_row_revision >= 0),
  actual_row_revision INTEGER NOT NULL CHECK (actual_row_revision >= 0),
  transition_digest TEXT NOT NULL
    CHECK (length(transition_digest) = 64 AND transition_digest NOT GLOB '*[^0-9a-f]*'),
  occurred_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (team_uuid, observation_uuid)
    REFERENCES mkb_intake_observations(team_uuid, observation_uuid),
  FOREIGN KEY (team_uuid, attempt_uuid)
    REFERENCES mkb_observation_attempts(team_uuid, attempt_uuid)
);

CREATE TABLE mkb_observation_snapshot_links (
  observation_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  intake_snapshot_uuid TEXT NOT NULL,
  linked_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (team_uuid, intake_snapshot_uuid),
  FOREIGN KEY (team_uuid, observation_uuid)
    REFERENCES mkb_intake_observations(team_uuid, observation_uuid),
  FOREIGN KEY (team_uuid, intake_snapshot_uuid)
    REFERENCES mkb_intake_snapshots(team_uuid, intake_snapshot_uuid)
);

CREATE TABLE mkb_intake_acceptance_facts (
  acceptance_fact_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  observation_uuid TEXT NOT NULL,
  intake_snapshot_uuid TEXT NOT NULL,
  intake_item_uuid TEXT,
  intake_revision_uuid TEXT,
  disposition TEXT NOT NULL
    CHECK (disposition IN ('changed','no_change','observed_not_adopted')),
  expected_item_epoch INTEGER,
  resulting_item_epoch INTEGER,
  fact_digest TEXT NOT NULL
    CHECK (length(fact_digest) = 64 AND fact_digest NOT GLOB '*[^0-9a-f]*'),
  created_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (observation_uuid),
  CHECK ((disposition = 'observed_not_adopted') OR
         (intake_item_uuid IS NOT NULL AND intake_revision_uuid IS NOT NULL
          AND expected_item_epoch IS NOT NULL AND resulting_item_epoch IS NOT NULL
          AND resulting_item_epoch = expected_item_epoch + 1)),
  FOREIGN KEY (team_uuid, observation_uuid)
    REFERENCES mkb_intake_observations(team_uuid, observation_uuid),
  FOREIGN KEY (team_uuid, intake_snapshot_uuid)
    REFERENCES mkb_intake_snapshots(team_uuid, intake_snapshot_uuid),
  FOREIGN KEY (team_uuid, intake_item_uuid)
    REFERENCES mkb_intake_items(team_uuid, intake_item_uuid),
  FOREIGN KEY (team_uuid, intake_revision_uuid)
    REFERENCES mkb_intake_revisions(team_uuid, intake_revision_uuid)
);

CREATE TABLE mkb_item_epoch_transitions (
  transition_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  intake_item_uuid TEXT NOT NULL,
  epoch_before INTEGER NOT NULL CHECK (epoch_before >= 0),
  epoch_after INTEGER NOT NULL CHECK (epoch_after = epoch_before + 1),
  mutation_kind TEXT NOT NULL
    CHECK (mutation_kind IN ('accept_latest','publish_serving','deactivate','reactivate','delete','metadata_update')),
  task_uuid TEXT,
  execution_uuid TEXT,
  observation_uuid TEXT,
  transition_digest TEXT NOT NULL
    CHECK (length(transition_digest) = 64 AND transition_digest NOT GLOB '*[^0-9a-f]*'),
  occurred_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (team_uuid, intake_item_uuid, epoch_after),
  FOREIGN KEY (team_uuid, intake_item_uuid)
    REFERENCES mkb_intake_items(team_uuid, intake_item_uuid),
  FOREIGN KEY (team_uuid, task_uuid)
    REFERENCES mkb_tasks(team_uuid, task_uuid),
  FOREIGN KEY (team_uuid, execution_uuid)
    REFERENCES mkb_executions(team_uuid, execution_uuid),
  FOREIGN KEY (team_uuid, observation_uuid)
    REFERENCES mkb_intake_observations(team_uuid, observation_uuid)
);

ALTER TABLE mkb_tasks ADD COLUMN observation_uuid TEXT;
ALTER TABLE mkb_tasks ADD COLUMN observation_attempt_generation INTEGER
  CHECK (observation_attempt_generation IS NULL OR observation_attempt_generation >= 1);
ALTER TABLE mkb_tasks ADD COLUMN expected_item_epoch INTEGER
  CHECK (expected_item_epoch IS NULL OR expected_item_epoch >= 0);
ALTER TABLE mkb_executions ADD COLUMN observation_uuid TEXT;
ALTER TABLE mkb_executions ADD COLUMN observation_attempt_generation INTEGER
  CHECK (observation_attempt_generation IS NULL OR observation_attempt_generation >= 1);
ALTER TABLE mkb_executions ADD COLUMN expected_item_epoch INTEGER
  CHECK (expected_item_epoch IS NULL OR expected_item_epoch >= 0);

CREATE INDEX ix_nhx1_observation_state
  ON mkb_intake_observations(team_uuid, state, reserved_at, observation_uuid);
CREATE INDEX ix_nhx1_observation_owner
  ON mkb_intake_observations(team_uuid, owner_task_uuid, current_attempt_generation);
CREATE INDEX ix_nhx1_attempt_state
  ON mkb_observation_attempts(team_uuid, state, created_at, attempt_uuid);
CREATE INDEX ix_nhx1_item_epoch_transition
  ON mkb_item_epoch_transitions(team_uuid, intake_item_uuid, epoch_after);
CREATE INDEX ix_nhx1_task_observation ON mkb_tasks(team_uuid, observation_uuid);
CREATE INDEX ix_nhx1_execution_observation ON mkb_executions(team_uuid, observation_uuid);

CREATE TRIGGER ck_nhx1_acceptance_fact_no_update
BEFORE UPDATE ON mkb_intake_acceptance_facts
BEGIN
  SELECT RAISE(ABORT, 'intake acceptance facts are append-only');
END;

CREATE TRIGGER ck_nhx1_acceptance_fact_no_delete
BEFORE DELETE ON mkb_intake_acceptance_facts
BEGIN
  SELECT RAISE(ABORT, 'intake acceptance facts are append-only');
END;

COMMIT;
