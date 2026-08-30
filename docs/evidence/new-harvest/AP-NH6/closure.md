# AP-NH6 Evidence Closure Index

Canonical closure: `docs/closure/new-harvest/AP-NH6-local-runtime-supply-and-security.md`

| 台账 D 目标 | 状态 | Evidence |
|---|---|---|
| PDF supply | PASS | `tests/e2e/test_nh6_pdf_parser.py`; `tests/e2e/test_nh6_parser_isolation.py` |
| browser supply | PASS | `tests/e2e/test_nh6_browser_render.py`; `tests/e2e/test_nh6_browser_print.py` |
| browser/parser policy | PASS | `tests/e2e/test_new_harvest_runtime_security.py` named NH6 nodes; `security/isolation-parser-browser.md` |
| model supply | PASS | `tests/integration/test_nh6_multimodal_request.py`; `tests/e2e/test_nh6_multimodal_adapter.py`; OCR typed errors |
| budget/readiness | PASS | `queries/gate-metrics.json`; `queries/readiness-positive-negative.json` |
| supply trust | PASS | `security/sbom-inventory.json`; `tests/domain/test_nh6_sbom_inventory.py` |
| default wiring | PASS | T03/T04/T06/T09 `create_app()` without fetcher assignment |
| S16 sign-off | document gate | `security/s16-egress-browser-review.md` empty reviewer/owner/UTC |

Verdict: executed, closed-with-explicit-deferrals. Implementation commit `63c4398`. Observed UTC `2026-08-30T00:01:17Z`.
