# NHX1 Phase 9 assurance security evidence

- The closed-set manifest is generated from current workflow/capability/intent registries, not a hand-written subset; every route/process/intent cell carries a test ID and minimum layer.
- Race soak uses fixed seeds, concurrent requests, and durable owner/effect assertions. A response code or delayed polling alone cannot satisfy the cell.
- Crash evidence kills an actual process group after a READY barrier and verifies a cold restart; hook-only or post-hoc SQL evidence is not used as the sole proof.
- Full repository validation ran on the current code commit with no path exclusion, skip, or xfail. Architecture/static checks cover public selector/raw payload and service-boundary redlines.
- T-O-419 remains an external hard gate: local code reaches `ready-for-owner-gate`, but real production model/binary identity and S16 named attestation are not present. The final closure therefore cannot be `full-close`.
