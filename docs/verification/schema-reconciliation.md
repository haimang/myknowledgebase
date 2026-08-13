# Schema reconciliation record: D04 × S09

Date: 2026-08-12

This implementation record resolves executable conflicts without creating a
second truth source. The domain-truth hierarchy remains authoritative.

## Resolution applied in code

1. D04's `mkb_executions` stale enum spelling is superseded by D02's frozen
   StateFamily spelling and S03's exact execution control contract:
   `created, ready, running, waiting, succeeded, failed, cancelling, cancelled`.
   No `pending` or `compensating` compatibility alias is implemented.
2. S09 requires durable `ActiveIndexPointer` and `PublicationProofV1` stores.
   The initial schema therefore adds `mkb_index_active_pointers` and
   `mkb_publication_proofs` to D04's 55-table baseline (57 required MKB tables).
   They are a S09-required additive migration, not an alternative outbox or
   second database.
3. `intake_scheduling_outbox` is only an S04 logical intent. All durable
   delivery uses the one physical `mkb_outbox` table.
4. Granularity is encoded as a validated generation-scoped unit coordinate in
   contracts and explicit vector fields where filtering needs it; it is never an
   untyped `payload_extra` convention.
5. New vector records are inserted as `withdrawn`. Only the S09 publication
   transaction may CAS them to `indexed`, after a durable publication proof and
   active-index pointer exist. The retrieval query always joins those two S09
   truths as well as the record state. This closes the D04 default-`indexed`
   versus S08/S09 half-write conflict without inventing another status family.
6. D04's duplicated `mkb_domain_events.severity` column is represented as
   `aggregate` (the domain aggregate enum) plus `severity`
   (`debug|info|warn|error`). This makes the schema executable and matches the
   S15 event contract; it is not a new StateFamily.
7. `mkb_tasks.created_at` is included as a non-null server timestamp (normally
   equal to `received_at` at creation), because D04's required task-list and
   intent indexes reference it even though its column list omits it.
8. Layer-A identity is stored in explicit, immutable vector namespace/record
   columns: `embedding_model_key`, `embedding_model_version`, and
   `adapter_kind`. It is never inferred from a floating display alias or stored
   in `payload_extra`; reads and publication validate these fields exactly.
9. A partial unique index enforces one root Execution per
   `(team_uuid, task_uuid, generation)` where `execution_role='root'` and
   `parent_execution_uuid IS NULL`; D04's index including `execution_uuid` is
   not sufficient because that UUID is already globally unique.
10. Executions persist an immutable L4 configuration snapshot reference and
    digest (not merely a digest) so recovery/retry cannot re-resolve changed
    prompts, models, schemas, or semantic knobs. Processes inherit that frozen
    reference.
11. S08 Layer-B facets use the additive normalized
    `mkb_vector_record_facets` table, with registered keys and a query index.
    This permits indexable copied facets without making `payload_extra` a filter
    truth store.
12. The canonical synchronous retrieval route is
    `POST /v1/teams/{team_uuid}/retrieval:search`. The route's path team UUID
    must equal the typed body team UUID; it creates no Task, Audit, Execution,
    Process, or outbox row and returns context-only data.
13. D04/S12 TX-08 “gate decision + waiting 投影原子” is executed as the S01
    two-step mapping already accepted by D02 R3: the public `decide_gate`
    UoW writes `mkb_execution_gate_decisions` + gates CAS + `mkb_outbox`
    `gate_decision` + `gate.decided`. Execution waiting release is applied
    later by `consume_gate_decision` replaying that outbox row. There is
    still one physical outbox and no second claim table. Folding resume
    into the HTTP decide UoW would reopen D02.

The record is deliberately small and is exercised by schema and architecture
tests. A future formal documentation freeze should fold these resolutions back
into D04's table ledger.
