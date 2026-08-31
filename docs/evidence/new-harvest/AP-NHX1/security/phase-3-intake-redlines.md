# Phase 3 intake redlines

- Same Observation key and matching fingerprint returns the original Task coordinates; a different fingerprint is rejected before Task/Attempt creation.
- Source identity remains `(team, source_kind, normalized_external_key)` while Observation identity is a separate durable UUID/key/attempt ledger.
- `row_revision` is the only ItemEpoch. `changed` acceptance increments it once; `no_change` records equal before/after epochs; lifecycle/publication callbacks must carry the same fence.
- Failed acquisition retries CAS the failed attempt generation and preserve Source identity; accepted observations have no retry path through ordinary ingest.
- The 21-cell intent/lifecycle matrix rejects illegal states before Task creation. Deleted external keys remain tombstones and physical cleanup cannot release them.
- Rebuild target drift fails the whole frozen target set. An active item with withdrawn serving state is a typed no-op, not an execution-time target disappearance.
