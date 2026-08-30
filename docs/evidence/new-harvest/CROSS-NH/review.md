# CROSS-NH review

Observed: 2026-08-30T06:20:00Z
HEAD at review: 9673704

## Packs

Nine closures under `docs/closure/new-harvest/AP-NH1`…`AP-NH9` exist.
Nine evidence packs have `manifest.json`, `tests.txt`, and `closure.md`.

## Truth drift

`docs/eval/new-harvest/pre-charter-qna.md` remains frozen `T-O-390..407`.
NH9 did not rewrite Q/A. Foundational `T-O-376/378/381/383` are not waived.
Production `--no-sandbox` remains forbidden (`T-O-399`). S16 was not forged.

## Coupling

- Kind-only resolver (NH2) is still the public path; old pin completes on historical digest (NH8/NH9-T08).
- Actual S05 seal stays in one Outcome UoW (NH3-T07 wrap in NH9-T04).
- Public upload catalog+pending UoW unchanged except PROM-CAT hook stage (NH4/NH9-T06).
- Retrieval still requires Layer-A namespace (`RETRIEVE_SCHEMA_NAMESPACE_REQUIRED`).
- Rebuild/metadata still replay frozen clean (NH8); NH9 did not add a no-op cleaner.

## Residual

- `test_registered_api_scatter.py` remains ⛔ as T07 PASS.
- `.experiment` is gitignored and not in closure join.

## CROSS-NH-TEST

Command: `uv run pytest tests/unit/test_nh9_closed_set_manifest.py tests/e2e/test_nh9_task_identity_conflict.py tests/e2e/test_intake_identity_replay.py tests/e2e/test_new_harvest_closed_set.py tests/e2e/test_new_harvest_crash_windows.py tests/e2e/test_nh3_seal_crash_windows.py tests/e2e/test_nh1_fanin_recovery_port.py::test_fanin_crash_repairs_via_persistence_port tests/unit/test_workflow_revision_compatibility.py tests/domain/test_nh9_evidence_pack_checker.py tests/e2e/test_new_harvest_runtime_security.py::test_campaign_security_signoff_aggregates_nh6_gates -q --tb=line`

Result: PASS, 62 passed, ~451s. In-scope unique campaign files green.
