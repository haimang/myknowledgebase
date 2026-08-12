-- A Task generation has one controller root regardless of whether its
-- ingress graph is the historical single-item root or the registered-API
-- scatter root.  The original partial index predated the explicit
-- ``scatter_root`` role and otherwise permits a duplicate controller tree.

BEGIN;

DROP INDEX IF EXISTS ux_mkb_exec_one_root;

CREATE UNIQUE INDEX ux_mkb_exec_one_root
  ON mkb_executions(team_uuid, task_uuid, generation)
  WHERE execution_role IN ('root', 'scatter_root') AND parent_execution_uuid IS NULL;

COMMIT;
