-- NS5 P4: serving vector coordinates are unique per index generation so a
-- later upsert cannot collapse the active proof set by rewriting an older gen.

BEGIN;

DROP INDEX IF EXISTS ux_vec_coord_active;
CREATE UNIQUE INDEX IF NOT EXISTS ux_vec_coord_active
  ON mkb_vector_records(team_uuid, namespace_uuid, generation_artifact_uuid,
                        block_or_unit_id, channel, embedding_model, index_generation)
  WHERE deleted_at IS NULL;

COMMIT;
