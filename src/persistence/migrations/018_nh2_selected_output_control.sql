-- M-NH-03: durable selected-output CONTROL projection.
-- One Execution/control step may seal exactly one canonical predecessor.

BEGIN;

CREATE TABLE mkb_workflow_selected_outputs (
  selection_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  execution_uuid TEXT NOT NULL,
  control_step_key TEXT NOT NULL,
  control_version TEXT NOT NULL,
  candidate_port TEXT NOT NULL,
  selected_source_process_uuid TEXT,
  output_manifest_ref TEXT NOT NULL,
  output_manifest_digest TEXT NOT NULL
    CHECK (length(output_manifest_digest) = 64
           AND output_manifest_digest NOT GLOB '*[^0-9a-f]*'),
  route_decision_digest TEXT NOT NULL
    CHECK (length(route_decision_digest) = 64
           AND route_decision_digest NOT GLOB '*[^0-9a-f]*'),
  selection_digest TEXT NOT NULL
    CHECK (length(selection_digest) = 64
           AND selection_digest NOT GLOB '*[^0-9a-f]*'),
  fallback_used INTEGER NOT NULL DEFAULT 0 CHECK (fallback_used IN (0, 1)),
  projected_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (execution_uuid, control_step_key),
  FOREIGN KEY (team_uuid, execution_uuid)
    REFERENCES mkb_executions(team_uuid, execution_uuid),
  FOREIGN KEY (selected_source_process_uuid)
    REFERENCES mkb_processes(process_uuid)
);

CREATE INDEX ix_mkb_selected_output_execution
  ON mkb_workflow_selected_outputs(team_uuid, execution_uuid, control_step_key);

COMMIT;
