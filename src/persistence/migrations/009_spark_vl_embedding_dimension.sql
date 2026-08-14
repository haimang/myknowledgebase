-- Align the D06 qwen-vl-2b catalog row with the Spark VL embedder's
-- production MRL dimension (1024).  Logical model_key stays qwen-vl-2b.
-- definition_digest matches RegistryService.DEFAULT_MODELS for v1/1024.

BEGIN;

UPDATE mkb_model_catalog
SET default_dimension = 1024,
    definition_digest = 'aee65bc0023bfafc3c1f4eb1291ecf96207971b5edc085646cd0cadc65685d32'
WHERE model_key = 'qwen-vl-2b'
  AND model_version = 'v1'
  AND default_dimension = 64;

COMMIT;
