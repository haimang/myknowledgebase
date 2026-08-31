-- NHX1 P2-03: typed processing binding, append-only correction, and publication manifest.

BEGIN;

CREATE TABLE mkb_processing_binding_assertions (
  binding_assertion_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  execution_uuid TEXT NOT NULL,
  binding_family TEXT NOT NULL
    CHECK (binding_family IN ('clean_strategy','registered_api_operation')),
  binding_key TEXT NOT NULL,
  definition_version TEXT NOT NULL,
  definition_digest TEXT NOT NULL
    CHECK (length(definition_digest) = 64 AND definition_digest NOT GLOB '*[^0-9a-f]*'),
  selected_process_key TEXT NOT NULL,
  selected_route_digest TEXT NOT NULL,
  assertion_digest TEXT NOT NULL
    CHECK (length(assertion_digest) = 64 AND assertion_digest NOT GLOB '*[^0-9a-f]*'),
  formula_version TEXT NOT NULL,
  seal_generation INTEGER NOT NULL CHECK (seal_generation >= 1),
  asserted_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (execution_uuid),
  FOREIGN KEY (team_uuid, execution_uuid)
    REFERENCES mkb_executions(team_uuid, execution_uuid)
);

CREATE TABLE mkb_selection_assertions_v2 (
  selection_assertion_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  execution_uuid TEXT NOT NULL,
  control_step_key TEXT NOT NULL,
  assertion_generation INTEGER NOT NULL CHECK (assertion_generation >= 1),
  selected_source_process_uuid TEXT,
  representation_fact_uuid TEXT NOT NULL,
  representation_fact_digest TEXT NOT NULL
    CHECK (length(representation_fact_digest) = 64
           AND representation_fact_digest NOT GLOB '*[^0-9a-f]*'),
  output_manifest_ref TEXT NOT NULL,
  output_manifest_digest TEXT NOT NULL,
  route_decision_digest TEXT NOT NULL,
  selection_digest TEXT NOT NULL,
  formula_version TEXT NOT NULL,
  supersedes_selection_uuid TEXT,
  asserted_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (execution_uuid, control_step_key, assertion_generation),
  FOREIGN KEY (team_uuid, execution_uuid)
    REFERENCES mkb_executions(team_uuid, execution_uuid),
  FOREIGN KEY (selected_source_process_uuid) REFERENCES mkb_processes(process_uuid),
  FOREIGN KEY (representation_fact_uuid) REFERENCES mkb_representation_facts(representation_fact_uuid),
  FOREIGN KEY (supersedes_selection_uuid) REFERENCES mkb_workflow_selected_outputs(selection_uuid)
);

CREATE TABLE mkb_evidence_verifications (
  verification_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  evidence_kind TEXT NOT NULL
    CHECK (evidence_kind IN ('representation_fact','representation_history','selected_output','processing_binding',
                             'generation_artifact','vector_identity','publication_proof','publication_manifest',
                             'object_delete_proof')),
  evidence_uuid TEXT NOT NULL,
  formula_version TEXT,
  verdict TEXT NOT NULL CHECK (verdict IN ('verified','invalid','legacy_unverifiable')),
  reason_code TEXT NOT NULL,
  verifier_key TEXT NOT NULL,
  verifier_version TEXT NOT NULL,
  observed_digest TEXT,
  recomputed_digest TEXT,
  correction_uuid TEXT,
  checked_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (evidence_kind, evidence_uuid, verifier_key, verifier_version),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid)
);

CREATE TABLE mkb_evidence_corrections (
  correction_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  evidence_kind TEXT NOT NULL,
  evidence_uuid TEXT NOT NULL,
  correction_kind TEXT NOT NULL,
  corrected_assertion_uuid TEXT NOT NULL,
  corrected_digest TEXT NOT NULL,
  formula_version TEXT NOT NULL,
  reason_code TEXT NOT NULL,
  created_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (evidence_kind, evidence_uuid, corrected_assertion_uuid),
  FOREIGN KEY (team_uuid) REFERENCES mkb_teams(team_uuid)
);

CREATE TABLE mkb_publication_manifests (
  publication_manifest_uuid TEXT PRIMARY KEY,
  team_uuid TEXT NOT NULL,
  proof_uuid TEXT NOT NULL,
  intake_item_uuid TEXT NOT NULL,
  intake_revision_uuid TEXT NOT NULL,
  item_epoch INTEGER NOT NULL CHECK (item_epoch >= 0),
  generation_artifact_uuid TEXT NOT NULL,
  namespace_uuid TEXT NOT NULL,
  index_generation INTEGER NOT NULL CHECK (index_generation >= 0),
  record_count INTEGER NOT NULL CHECK (record_count >= 0),
  record_set_digest TEXT NOT NULL,
  manifest_digest TEXT NOT NULL,
  formula_version TEXT NOT NULL,
  published_at TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  UNIQUE (proof_uuid),
  UNIQUE (team_uuid, intake_item_uuid, namespace_uuid, index_generation),
  FOREIGN KEY (proof_uuid) REFERENCES mkb_publication_proofs(proof_uuid),
  FOREIGN KEY (team_uuid, intake_item_uuid)
    REFERENCES mkb_intake_items(team_uuid, intake_item_uuid),
  FOREIGN KEY (team_uuid, intake_revision_uuid)
    REFERENCES mkb_intake_revisions(team_uuid, intake_revision_uuid),
  FOREIGN KEY (team_uuid, generation_artifact_uuid)
    REFERENCES mkb_generation_artifacts(team_uuid, generation_artifact_uuid),
  FOREIGN KEY (namespace_uuid, team_uuid)
    REFERENCES mkb_vector_namespaces(namespace_uuid, team_uuid)
);

CREATE TABLE mkb_publication_manifest_members (
  publication_manifest_uuid TEXT NOT NULL,
  team_uuid TEXT NOT NULL,
  vector_record_uuid TEXT NOT NULL,
  member_ordinal INTEGER NOT NULL CHECK (member_ordinal >= 0),
  member_digest TEXT NOT NULL,
  payload_extra TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (publication_manifest_uuid, vector_record_uuid),
  UNIQUE (publication_manifest_uuid, member_ordinal),
  FOREIGN KEY (publication_manifest_uuid) REFERENCES mkb_publication_manifests(publication_manifest_uuid),
  FOREIGN KEY (vector_record_uuid, team_uuid)
    REFERENCES mkb_vector_records(vector_record_uuid, team_uuid)
);

CREATE INDEX ix_nhx1_evidence_verdict
  ON mkb_evidence_verifications(team_uuid, verdict, evidence_kind, checked_at);
CREATE INDEX ix_nhx1_publication_manifest_lookup
  ON mkb_publication_manifests(team_uuid, intake_item_uuid, namespace_uuid, index_generation);

CREATE TRIGGER ck_nhx1_processing_binding_no_update
BEFORE UPDATE ON mkb_processing_binding_assertions
BEGIN SELECT RAISE(ABORT, 'processing binding assertions are append-only'); END;
CREATE TRIGGER ck_nhx1_processing_binding_no_delete
BEFORE DELETE ON mkb_processing_binding_assertions
BEGIN SELECT RAISE(ABORT, 'processing binding assertions are append-only'); END;
CREATE TRIGGER ck_nhx1_selection_v2_no_update
BEFORE UPDATE ON mkb_selection_assertions_v2
BEGIN SELECT RAISE(ABORT, 'selection assertions are append-only'); END;
CREATE TRIGGER ck_nhx1_selection_v2_no_delete
BEFORE DELETE ON mkb_selection_assertions_v2
BEGIN SELECT RAISE(ABORT, 'selection assertions are append-only'); END;
CREATE TRIGGER ck_nhx1_verification_no_update
BEFORE UPDATE ON mkb_evidence_verifications
BEGIN SELECT RAISE(ABORT, 'evidence verifications are append-only'); END;
CREATE TRIGGER ck_nhx1_verification_no_delete
BEFORE DELETE ON mkb_evidence_verifications
BEGIN SELECT RAISE(ABORT, 'evidence verifications are append-only'); END;
CREATE TRIGGER ck_nhx1_correction_no_update
BEFORE UPDATE ON mkb_evidence_corrections
BEGIN SELECT RAISE(ABORT, 'evidence corrections are append-only'); END;
CREATE TRIGGER ck_nhx1_correction_no_delete
BEFORE DELETE ON mkb_evidence_corrections
BEGIN SELECT RAISE(ABORT, 'evidence corrections are append-only'); END;
CREATE TRIGGER ck_nhx1_publication_manifest_no_update
BEFORE UPDATE ON mkb_publication_manifests
BEGIN SELECT RAISE(ABORT, 'publication manifests are append-only'); END;
CREATE TRIGGER ck_nhx1_publication_manifest_no_delete
BEFORE DELETE ON mkb_publication_manifests
BEGIN SELECT RAISE(ABORT, 'publication manifests are append-only'); END;
CREATE TRIGGER ck_nhx1_publication_member_no_update
BEFORE UPDATE ON mkb_publication_manifest_members
BEGIN SELECT RAISE(ABORT, 'publication manifest members are append-only'); END;
CREATE TRIGGER ck_nhx1_publication_member_no_delete
BEFORE DELETE ON mkb_publication_manifest_members
BEGIN SELECT RAISE(ABORT, 'publication manifest members are append-only'); END;

COMMIT;
