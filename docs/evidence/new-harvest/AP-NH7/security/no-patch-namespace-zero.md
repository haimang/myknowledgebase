# AP-NH7 fake-green / security negatives

Observed UTC `2026-08-30T02:28:40Z`. Commit `6256a97`.

## No success-path patch (FG-NH-01)

`tests/domain/test_nh7_no_fetcher_patch.py` scans T03–T08/T09 files for:

- `_browser_fetcher =`
- `_http_fetcher =`
- `_clean_llm =`
- `import sqlite3` / `sqlite3.connect`

PASS. T06 sanitizer counting wraps `sanitize_html_document` / `clean_html_representation` only as a zero-call meter, not a success fake.

## Namespace required (FG-NH-05)

Inline, browser llm_rewrite, and registered-API retrieval tests POST search without `namespace_key` and expect HTTP 422 `RETRIEVE_SCHEMA_NAMESPACE_REQUIRED`.

## Empty clean / member / worker fail → zero vectors (FG-NH-06, T-O-383)

- `tests/e2e/test_nh7_empty_clean_zero_vector.py`
- `tests/e2e/test_nh7_failure_zero_vector.py`
- unit `tests/unit/test_nh7_clean_empty.py` asserts literal `CLEAN_EMPTY`

## exhausted_zero is not indexed success (T-O-397)

- Task `result_disposition == exhausted_zero`
- child / item / revision / vector / publication_proof counts = 0
- metric `mkb_task_result_disposition_total{disposition="exhausted_zero"}` increments; `indexed_success` does not
- NOOP mapping cannot write `exhausted_zero`
- empty records without `caller_frozen_records.v1` → 422 `SCATTER_EXHAUSTION_PROOF_REQUIRED` and no Task
