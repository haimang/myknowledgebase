# M-NH-03 — selected-output CONTROL

- Migration: `src/persistence/migrations/018_nh2_selected_output_control.sql`.
- Adds `mkb_workflow_selected_outputs`, unique on `(execution_uuid, control_step_key)`.
- Stores CONTROL version, selected candidate port/process, canonical output ref/digest, entry route digest, selection digest, fallback flag and UTC.
- Does not alter `ux_workflow_binding_slot`; every CONTROL candidate remains a separate optional input with one binding.
- Registration persists step-scoped CONTROL metadata; absent NH2 fields are omitted from serialization so all 16 old compiled digests remain byte-identical.
- Runtime reads only succeeded durable Process outcomes, persists exactly one projection, and routes a single required canonical output to the shared tail.
- Zero candidates fail `workflow-selected-output-missing`; double candidates/prior-different replay fail `workflow-selected-output-conflict`; neither enters a scatter wait.

Evidence: commit `81f1271`; NH2-T02 `6 passed`; Q11/T-O-391; `2026-08-29T18:53:27Z`.
