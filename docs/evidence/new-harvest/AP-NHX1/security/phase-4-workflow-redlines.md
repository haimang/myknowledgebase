# Phase 4 workflow/replay redlines

- A rev1 Execution resolves only against the checked-in ba099ee manifest; the current kind-family builder is revision 2 and registry never rewrites rev1.
- ProcessingBinding keeps `clean_strategy` and `registered_api_operation` separate; `registered_api.map` is not counted as an eleventh clean strategy.
- A terminal Execution rejects a late Outcome; stale process failure checks the current fencing generation and returns without killing the newer owner.
- Full retry requires an accepted Observation and raw artifact. The retry uses the stored CAS bytes and carries the same observation/snapshot coordinates; changed upstream content is not fetched.
- Critical outbox dead rows carry owner coordinates and terminalize the owning Execution/Task; advisory dead rows remain advisory. Requeue inserts a new generation with a dead predecessor and an idempotent receipt.
