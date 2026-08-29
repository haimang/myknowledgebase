# NH1 isolation / license / CVE boundary

- Parser: `unshare --net` creates a no-network namespace before `setpriv` drops to `nobody`; `prlimit` bounds address space, CPU and file descriptors. Timeout and output cap are enforced by the parent.
- Browser: geckodriver and Firefox both ran with real UID `65534`; launch arguments contain no `no-sandbox`; the fixture uses a `data:` URL and therefore performs no external egress.
- Encrypted input: a real Ghostscript-encrypted PDF is rejected as `NH1_PDF_ENCRYPTED` (422), not emitted as empty clean text.
- Python dependency surface: `pyproject.toml` was not changed; no parser/browser package name was frozen as Truth.
- License posture: executable subprocess use is recorded separately from linking. Exact redistribution obligations and system-package SBOM remain NH6 review work.
- CVE posture: NH1 records observed versions only. Production acceptance requires NH6 pinned identity, license/SBOM, current CVE baseline, malicious/oversize fixtures, readiness and rollback.
- Owner waiver: none.
