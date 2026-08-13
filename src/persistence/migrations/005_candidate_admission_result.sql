-- D02 R1/R2: persist CandidateSet admission as a typed column so route
-- guards do not read ProcessOutcome.payload_extra. Seal (open→sealed)
-- writes this together with preflight refs.
BEGIN;

ALTER TABLE mkb_intake_candidate_sets ADD COLUMN admission_result TEXT
  CHECK (
    admission_result IS NULL
    OR admission_result IN ('auto_admitted', 'human_review_required', 'rejected')
  );

COMMIT;
