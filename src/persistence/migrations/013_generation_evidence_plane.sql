-- NS4 generation-evidence plane: first-class invocation columns + stage reports.
-- Must run on Turso (T-O-373). Does not invent histograms for historic failures.

BEGIN;

ALTER TABLE mkb_generation_invocations ADD COLUMN status TEXT
  CHECK (status IS NULL OR status IN ('succeeded', 'failed'));

ALTER TABLE mkb_generation_invocations ADD COLUMN stage_key TEXT
  CHECK (stage_key IS NULL OR stage_key IN ('markdown', 'structurize', 'construct'));

ALTER TABLE mkb_generation_invocations ADD COLUMN error_code TEXT;

ALTER TABLE mkb_generation_invocations ADD COLUMN adapter_kind TEXT
  CHECK (adapter_kind IS NULL OR adapter_kind IN ('claude_cli', 'local_inference', 'local_vllm'));

ALTER TABLE mkb_generation_invocations ADD COLUMN cli_structured_kind TEXT
  CHECK (
    cli_structured_kind IS NULL OR cli_structured_kind IN (
      'object', 'list', 'string', 'empty_result', 'missing', 'null', 'number', 'bool', 'other'
    )
  );

UPDATE mkb_generation_invocations
SET
  status = CASE json_extract(payload_extra, '$.status')
    WHEN 'succeeded' THEN 'succeeded'
    WHEN 'failed' THEN 'failed'
    ELSE COALESCE(status, 'succeeded')
  END,
  stage_key = CASE json_extract(payload_extra, '$.stage_key')
    WHEN 'markdown' THEN 'markdown'
    WHEN 'structurize' THEN 'structurize'
    WHEN 'construct' THEN 'construct'
    WHEN 'transcribe_markdown' THEN 'markdown'
    ELSE COALESCE(stage_key, 'structurize')
  END,
  error_code = COALESCE(error_code, json_extract(payload_extra, '$.error_code')),
  adapter_kind = CASE json_extract(payload_extra, '$.adapter_kind')
    WHEN 'claude_cli' THEN 'claude_cli'
    WHEN 'local_inference' THEN 'local_inference'
    WHEN 'local_vllm' THEN 'local_vllm'
    ELSE COALESCE(adapter_kind, 'claude_cli')
  END,
  cli_structured_kind = CASE json_extract(payload_extra, '$.cli_structured_kind')
    WHEN 'object' THEN 'object'
    WHEN 'list' THEN 'list'
    WHEN 'string' THEN 'string'
    WHEN 'empty_result' THEN 'empty_result'
    WHEN 'missing' THEN 'missing'
    WHEN 'null' THEN 'null'
    WHEN 'number' THEN 'number'
    WHEN 'bool' THEN 'bool'
    WHEN 'other' THEN 'other'
    ELSE cli_structured_kind
  END;

CREATE TABLE mkb_generation_stage_reports (
  report_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  trace_uuid TEXT NOT NULL,
  task_uuid TEXT NOT NULL,
  execution_uuid TEXT NOT NULL,
  process_uuid TEXT NOT NULL,
  stage_key TEXT NOT NULL CHECK (stage_key IN ('markdown', 'structurize', 'construct')),
  disposition TEXT NOT NULL CHECK (disposition IN ('accepted', 'rejected', 'transport_failed')),
  error_code TEXT,
  cli_structured_kind TEXT,
  has_g0 INTEGER CHECK (has_g0 IS NULL OR has_g0 IN (0, 1)),
  block_count INTEGER CHECK (block_count IS NULL OR block_count >= 0),
  granularity_set TEXT,
  layer_counts TEXT,
  latency_ms INTEGER NOT NULL CHECK (latency_ms >= 0),
  schema_digest TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (team_uuid, process_uuid)
    REFERENCES mkb_processes(team_uuid, process_uuid)
);

CREATE INDEX ix_mkb_stage_reports_process
  ON mkb_generation_stage_reports(process_uuid, occurred_at);

CREATE INDEX ix_mkb_stage_reports_execution
  ON mkb_generation_stage_reports(execution_uuid, stage_key);

COMMIT;
