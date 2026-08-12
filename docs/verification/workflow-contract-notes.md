# Workflow contract verification notes

Date: 2026-08-12

## Implemented static definition

`src/workflows/builtin_lsrag.py` supplies the code-owned revision
`intake.ingest.single.inline.lsrag.v1`.  It is data validated by
`src/contracts/workflow/models.py`; it does not register, execute, or persist
the revision.

The required single-intake spine is explicit:

```text
acquire → decode → clean → seal/preflight → accept snapshot
  → structurize → construct → vectorize → validate publication → success
```

The admission branch is also declared rather than hidden in a handler:

- an automatically admitted result proceeds from accepted Intake revision to
  `lsrag.structurize`;
- a review-required result enters the declared `human_review_gate` control
  hook and resumes to structurize only after its typed outcome;
- a rejected result terminates as failure.

Every process/control node has explicit failed and cancelled terminal routes.
The final success route is available only after the independent
`index.validate_publication` process emits its required publication proof;
`lsrag.vectorize` success alone has no success terminal route.

## S03 correspondence

| S03 requirement | Static enforcement here |
|---|---|
| S03-T011 / E01 | One `start`, typed terminal steps, deterministic priorities, an acyclic graph, reachability, and terminal coverage are checked when `WorkflowDefinition` is built. |
| S03-T012 / E10 | Routes use only registered outcome selectors and the bounded, typed admission guard; there is no Python/SQL/free-expression field. |
| S03-T014 / E01 | Bindings carry logical slot names plus schema references. They reject filesystem/object-store paths by construction: no path, bucket, or object key field exists. |
| S03-T015 / E02 | Each process step names an exact versioned `process_key`, `contract_version`, typed input/output ports, and proof kind. `required_process_keys` must exactly match the required process steps. |
| S03-T038 / E11 | One `single_root` definition spans intake clean evidence, snapshot acceptance, LS-RAG construction, vectorization, and publication validation. Downstream LS-RAG steps consume the exact accepted-revision slot rather than a floating “latest” record. |
| S03-T042 | Failure/cancellation terminal routes are declared for every actionable step, while final success remains proof-gated. |

## D03 boundary check

The workflow module is only a typed declaration. It imports only the workflow
contract models and has no imports of runtime, services, persistence, storage,
LLM adapters, queues, or HTTP code. Its schema has no fields for claim, lease,
fence, retry, outbox, execution state, process state, or next-step scheduling.
Those responsibilities remain with the S03 engine and S12 implementation, as
required by D03-T003 and D03-T012.

The declared `human_review_gate` is a finite control hook, not a waiting-state
implementation: the engine owns gate persistence, CAS, execution `waiting`,
and resume behavior.

## Intentional scope

This is the source-specific inline single-intake seed. Other source kinds,
scatter/fan-in variants, capability manifest registration, canonical compilation
and immutable registry activation remain subsequent S03 implementation work.
