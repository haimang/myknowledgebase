# NHX1 Phase 7 discovery / control / observability security evidence

- Public catalog endpoints expose only registered workflow revision, process capability, source-kind, and availability identities. Task creation remains a typed intent/source contract; `workflow_key`, raw process, branch, SQL, and model/vector overrides are not accepted.
- Task, Item, and Namespace projections are team-scoped and cursor-bound to their filters. The Task view adds observation, actual-binding, revision, phase, waiting, and retryability coordinates without returning raw stage payloads.
- Operator Process/Execution/Cleanup reads select bounded identity/status/digest fields. Operator mutations require internal token/network, expected generation or row revision, idempotency, CAS, and a durable CommandReceipt; terminal rows are never reset in place.
- Outbox requeue preserves the dead predecessor and increments delivery generation. Process restart clears the old lease and increments fencing generation before enqueueing a new wake. Execution stop delegates to the existing cancellation-tree owner.
- The signal catalog binds each alert to a low-cardinality metric, emitter, owner, and checked-in runbook. `MkbError.canonical_code`/`retryable` resolve v2 definitions while preserving legacy aliases for old callers.

All Phase 7 security/control tests passed without `skip`/`xfail`; operator routes remain unavailable from non-internal peers even with a valid token.
