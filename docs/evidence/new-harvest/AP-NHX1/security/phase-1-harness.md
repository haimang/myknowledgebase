# Phase 1 harness truthfulness

- e2e AST scan found zero raw `sqlite3.connect` adapter-path inspections after the four known callers moved to `PersistenceInspectorPort.read_snapshot()`.
- The stale-fence regression remains an executable RED with `ConflictError(stale-process-fence)` and retains the assertion that a newer generation stays `running`.
- Evidence records require a full current SHA, an actually executed argv/exit code, UTC, profile, stdout digest, Truth/work coordinates, and a minimum layer.
- Injected fake SHA, digest mutation, pure `PASS`, `skipped`, `xfailed`, and observed-layer downgrade all fail the checker.
