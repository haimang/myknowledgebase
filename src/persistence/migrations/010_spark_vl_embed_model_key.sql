-- Replace the retired catalog identity qwen-vl-2b with the Spark VL
-- provider model id.  Existing global embed bindings are retargeted in the
-- same transaction so bootstrap does not see two active embed winners.

BEGIN;

INSERT INTO mkb_model_catalog (
  model_uuid, model_key, model_version, modality, provider_family,
  default_dimension, definition_digest, status, display_name, registered_at, payload_extra
)
SELECT
  lower(hex(randomblob(16))),
  'LifetimeMistake/Qwen3-VL-Embedding-2B-NVFP4',
  model_version,
  modality,
  provider_family,
  1024,
  '80f0388f5590a243080ea8929eb3339258fd3c1140f3b1d22993499e6147acb2',
  'active',
  'LifetimeMistake/Qwen3-VL-Embedding-2B-NVFP4',
  registered_at,
  payload_extra
FROM mkb_model_catalog
WHERE model_key = 'qwen-vl-2b'
  AND model_version = 'v1'
  AND NOT EXISTS (
    SELECT 1 FROM mkb_model_catalog
    WHERE model_key = 'LifetimeMistake/Qwen3-VL-Embedding-2B-NVFP4'
      AND model_version = 'v1'
  );

UPDATE mkb_adapter_bindings
SET model_key = 'LifetimeMistake/Qwen3-VL-Embedding-2B-NVFP4',
    binding_digest = '2f7fcbdd1209c682e6be58acfb0bbd1fb3afcbe06cbb6af8226088076c1741ee'
WHERE model_key = 'qwen-vl-2b'
  AND model_version = 'v1';

UPDATE mkb_model_catalog
SET status = 'deprecated'
WHERE model_key = 'qwen-vl-2b'
  AND model_version = 'v1';

COMMIT;
