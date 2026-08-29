# AP-NH4 upload security matrix

Observed UTC `2026-08-29T20:37:37Z`; implementation commit `7359a96`.

| Vector | Expected | Observed |
|---|---|---|
| missing bearer | 401 `SEC_TOKEN_MISSING` | PASS |
| cross-Team handle stat | 403 `OBJECT_AUTH_TEAM_MISMATCH` | PASS |
| `../`, Windows path, percent-encoded traversal filename | 422 `SEC_PATH_REJECTED` | PASS |
| multipart body | 422 `OBJECT_MEDIA_TYPE_INVALID` | PASS |
| declared `image/png` over plain bytes | digest/path remain byte-derived | PASS |
| content-length and chunked over object cap | 413 `OBJECT_BUDGET_SIZE`, zero catalog | PASS |
| expected SHA mismatch | 422 `OBJECT_INTEGRITY_DIGEST`, zero catalog | PASS |
| empty body | 422 `OBJECT_EMPTY`, zero CAS target/catalog | PASS |
| raw GET/list | route absent (404/405) | PASS |
| presign/R2 symbols in production upload surface | zero | PASS |
| internal promote without catalog/live ref | 409 `OBJECT_CATALOG_REQUIRED` | PASS |

Primary evidence: `tests/e2e/test_nh4_upload_security.py`, `tests/unit/test_nh4_object_routes_contract.py`, and `tests/integration/test_nh4_upload_uow.py`.
