# NHX1 Phase 8 cutover / compatibility security evidence

- Shadow mismatch is a durable blocker. The v2 cutover CAS requires zero unresolved mismatch rows and the expected cutover revision; interrupted or concurrent transitions cannot skip the gate.
- After cutover the durable writer mode is `v2_only` and reader mode is `v2`. Legacy rows/manifests remain readable for exact interpretation, but `assert_writer_allowed(..., "legacy")` fails loudly.
- Forward rollback is only `admission_enabled=0` followed by a forward fix. It never restores the legacy writer or mutates v2 evidence.
- Inventory counts rev1 active pins, pending/in-flight outbox, accepted restart windows, live object references, open cleanup jobs, legacy evidence verdicts, and unresolved shadow mismatches before retirement.
- Legacy evidence verification and correction use separate append-only rows. Retiring a writer does not delete legacy verdicts or old manifests.

Phase 8 tests include unresolved-mismatch negative, expected-revision CAS, writer-disable, forward rollback, persisted restart, and legacy correction checks; no `skip`/`xfail` is used.
