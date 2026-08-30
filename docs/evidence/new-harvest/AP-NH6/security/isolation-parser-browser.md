# AP-NH6 parser / browser isolation

Observed UTC `2026-08-29T23:48:02Z`.

## PDF parser

- Execution: `unshare --net` + `prlimit` (address space / CPU / fds / output) + `setpriv` to uid 65534 when the API is root.
- Network: new network namespace; environment proxies cleared; isolation probe `connect_ex(('127.0.0.1', 9))` returns denied.
- Extraction authority: isolated `pdftotext -enc UTF-8`; `_extract_pdf_text` remains a bounded observer only.
- Failures: timeout SIGTERM then SIGKILL; malicious/cyclic structure returns typed `absent`/`corrupt` without killing the API PID.

## Browser

- Shared binary/driver; distinct `browser.render` and `browser.print_pdf` caps, budgets, and readiness keys.
- Navigation: S16 `HttpAcquirer` prefetch with per-hop `check_url` / `validate_redirect`. Page HTTP(S) is forced to `127.0.0.1:9`. Script `fetch` of a local beacon is not observed.
- Process: non-root (`uid != 0`); argv contains no `--no-sandbox`.
- Print: `%PDF-` bytes; Latin `DejaVu Sans` print font so ASCII ToUnicode survives CJK host defaults.
- Missing port: typed 503, not HTTP fallback.

Primary tests: `tests/e2e/test_nh6_parser_isolation.py`, `tests/e2e/test_new_harvest_runtime_security.py` named NH6 nodes.
