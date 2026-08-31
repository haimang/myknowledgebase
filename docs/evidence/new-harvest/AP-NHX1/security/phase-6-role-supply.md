# NHX1 Phase 6 role / supply security evidence

- `T-O-415`: the API role owns authenticated reads/admission only; it never starts the workflow supervisor or maintenance scanners. Process and supply internals remain outside the public role boundary.
- `T-O-416`: `api`, `workflow_worker`, `maintenance`, and `all` are explicit deployment roles. `all` is a composed role, not an implicit fallback. Lease ownership remains distinct from durable workflow execution roles.
- Capability claim is closed over the 27 code-owned process manifests. Unknown process keys fail with `CAPABILITY_UNKNOWN`; a worker allowlist is validated against the same registry and missing native supplies remove affected keys before claim.
- Role readiness includes the workflow supervisor failure threshold only for claim-owning roles. API/maintenance can remain ready without local browser/model supplies; worker/all profiles requiring supply probe the actual parser, browser, OCR, and multimodal bindings.
- `T-O-419`: production settings reject the deterministic NS1 stub, require `subprocess` plus runtime supply readiness and pinned multimodal configuration. The local implementation reaches `ready-for-owner-gate`; no real model/binary/S16 owner attestation is fabricated.
- Existing S16 controls remain active: browser non-root/no-`--no-sandbox`, egress recheck per redirect, isolated parser network denial, bounded concurrency, and fail-closed supply fences.

No Phase 6 test uses `skip`/`xfail` to stand in for the owner gate.
