# AP-NH5 semantic/retrieval redlines

Observed UTC `2026-08-29T21:38:33Z`; implementation commit `76f233b`.

| Vector | Result |
|---|---|
| generic missing/blank/`unknown` dimensions | 422 before Task |
| caller `is_active` or payload_extra semantic authority | 422 |
| provider missing required mapped dimension | 422 |
| caller duplicate conflicts with provider mapper | 422 `CLEAN_SEMANTIC_CONFLICT` / public schema invalid |
| `source_kind` stub as complete FilterMeta | rejected before Revision/vector |
| model/hallucinated context authority | overwritten by S04 |
| no retrieval namespace | 422 `RETRIEVE_SCHEMA_NAMESPACE_REQUIRED` |
| unknown filter key | 422 `RETRIEVE_FILTER_INVALID` |
| v1 business `channel` or v2 legacy `channel` | 422 |
| semantic post-topK Python filtering | source/SQL scan zero |
| metadata direct blob submission | 422 `METADATA_SEMANTIC_SYSTEM_OWNED` |
| metadata reclean process absence | still red: count 3, handoff NH8; not xfailed |
