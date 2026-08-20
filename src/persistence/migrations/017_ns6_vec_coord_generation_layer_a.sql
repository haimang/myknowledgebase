-- NS6: Layer-A coordinate unique must include index_generation so a new
-- serving generation can INSERT without colliding with an indexed prior gen.

BEGIN;

DROP INDEX IF EXISTS ux_vec_coord_active_layer_a;
CREATE UNIQUE INDEX IF NOT EXISTS ux_vec_coord_active_layer_a
  ON mkb_vector_records(team_uuid, namespace_uuid, generation_artifact_uuid,
                        block_or_unit_id, channel, embedding_model_key,
                        embedding_model_version, adapter_kind, index_generation)
  WHERE deleted_at IS NULL;

COMMIT;
