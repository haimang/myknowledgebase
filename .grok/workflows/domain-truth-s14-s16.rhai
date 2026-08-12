// =============================================================================
// domain-truth-s14-s16.rhai
//
// Complete remaining MKB domain-truth SSOT for S14 / S15 / S16, then
// adversarial alignment review + fix, then glossary/index full truth audit.
//
// Method (each S* phase, sequential agents, self-contained prompts):
//   [1] legacy-family archaeology + existing domain-truth alignment
//   [2] one-shot full QNA with complete recommendations (no progressive batches)
//   [3] web Reference-Check for every question (W-P / W-N)
//   [4] seal QNA: freeze T-O truths + external reference links
//   [5] formal domain-truth (S01/S02 density; nine-section + E-packages)
//
// Authority:
//   domain-truth/* = sole execution SSOT
//   qna-truth/*    = progressive evidence only (never second SSOT)
//   D* > S*
//   legacy-family only (forbid legacy-specs / legacy-python*)
// =============================================================================

let meta = #{
    name: "domain-truth-s14-s16",
    description: "Produce S14-S16 domain-truth via archaeology/QNA/web-RC/freeze/formal, adversarial review+fix, then glossary/index full audit",
    when_to_use: "Finish remaining MKB baseline domain-truth for S14 Config/Prompt/Model Registry, S15 Observability/Reliability, S16 Security/Trust Boundary",
    phases: [
        #{ title: "S14", detail: "Config Prompt Model Registry full pipeline" },
        #{ title: "S15", detail: "Observability Reliability full pipeline" },
        #{ title: "S16", detail: "Security Trust Boundary full pipeline" },
        #{ title: "Adversarial-Review", detail: "race blind-spot breakpoint gap review of S14-S16" },
        #{ title: "Adversarial-Fix", detail: "apply verified fixes to S14-S16 QNA and formal" },
        #{ title: "Glossary-Index-Audit", detail: "full truth-layer audit + glossary + spec-index" },
    ],
};

// ---------------------------------------------------------------------------
// Output schemas
// ---------------------------------------------------------------------------
let step_schema = #{
    "type": "object",
    "required": ["subsystem", "step", "status", "output_paths", "summary"],
    "properties": #{
        "subsystem": #{ "type": "string" },
        "step": #{ "type": "string" },
        "status": #{ "type": "string" },
        "output_paths": #{ "type": "array", "items": #{ "type": "string" } },
        "summary": #{ "type": "string" },
        "truth_id_range": #{ "type": "string" },
        "question_count": #{ "type": "integer" },
        "web_refs_count": #{ "type": "integer" },
        "notes": #{ "type": "string" },
    },
};

let review_schema = #{
    "type": "object",
    "required": ["reviewer_id", "dimension", "summary", "issues"],
    "properties": #{
        "reviewer_id": #{ "type": "string" },
        "dimension": #{ "type": "string" },
        "summary": #{ "type": "string" },
        "issues": #{
            "type": "array",
            "maxItems": 30,
            "items": #{
                "type": "object",
                "required": ["severity", "target", "section", "claim", "evidence", "required_fix"],
                "properties": #{
                    "severity": #{ "type": "string" },
                    "target": #{ "type": "string" },
                    "section": #{ "type": "string" },
                    "claim": #{ "type": "string" },
                    "evidence": #{ "type": "string" },
                    "required_fix": #{ "type": "string" },
                },
            },
        },
    },
};

let fix_schema = #{
    "type": "object",
    "required": ["status", "files_touched", "fixes_applied", "summary"],
    "properties": #{
        "status": #{ "type": "string" },
        "files_touched": #{ "type": "array", "items": #{ "type": "string" } },
        "fixes_applied": #{ "type": "integer" },
        "summary": #{ "type": "string" },
        "deferred": #{ "type": "array", "items": #{ "type": "string" } },
    },
};

let audit_schema = #{
    "type": "object",
    "required": ["status", "glossary_version", "index_version", "summary", "files_touched"],
    "properties": #{
        "status": #{ "type": "string" },
        "glossary_version": #{ "type": "string" },
        "index_version": #{ "type": "string" },
        "summary": #{ "type": "string" },
        "files_touched": #{ "type": "array", "items": #{ "type": "string" } },
        "open_gaps": #{ "type": "array", "items": #{ "type": "string" } },
    },
};

// ---------------------------------------------------------------------------
// Shared campaign law (injected into every production prompt)
// ---------------------------------------------------------------------------
fn campaign_law() {
    let p = "";
    p += "You are a specialized MKB domain-truth producer operating inside workspace root.\n";
    p += "LANGUAGE: Write all deliverable docs in Chinese technical prose; keep IDs/paths/code identifiers in English.\n";
    p += "DATE: 2026-08-12. Author attribution: `MKB owner + Grok workflow domain-truth-s14-s16`.\n\n";

    p += "## HIGHEST AUTHORITY (non-negotiable order)\n";
    p += "1. Owner direction in docs/baseline/spec-index.md §0 (OD-01..12) and D* > S* rule (§0.2b).\n";
    p += "2. Accepted/frozen domain-truth under docs/baseline/domain-truth/** (D01–D05, S01–S13 already accepted).\n";
    p += "3. docs/baseline/spec-glossary.md and docs/baseline/spec-index.md gates/progress.\n";
    p += "4. Frozen qna-truth for neighbors (evidence only; never second execution SSOT).\n";
    p += "5. context/legacy-family/** ONLY as ReferenceAnchor (behavior archaeology / pitfalls / counterexamples).\n";
    p += "6. External web Reference-Check: design contrast only — never overrides owner/D*/S* freezes.\n\n";

    p += "## HARD BANS\n";
    p += "- FORBIDDEN evidence trees: context/legacy-specs/**, context/legacy-python/**, context/legacy-python-2/**.\n";
    p += "- FORBIDDEN: invent production code, reopen closed gates without explicit change-request, create dual SSOT.\n";
    p += "- FORBIDDEN: platform UI/membership/billing/session, webhook as v1 default, answer-generation into S10.\n";
    p += "- FORBIDDEN: silent model/adapter swap (G-10 closed), team_uuid as auth credential, log-as-business-SSOT.\n";
    p += "- domain-truth/* is SOLE execution SSOT after formalization; qna-truth/* is evidence/progressive only.\n";
    p += "- second-opinion mode: waived (owner delegated freeze to RC-adjusted recommendations via this workflow).\n";
    p += "- Do NOT wait for interactive owner answers. Freeze recommended (RC-adjusted) answers as T-O with source `workflow-frozen / RC-adjusted recommendation`.\n\n";

    p += "## TRUTH-ID CONTINUITY\n";
    p += "- Global T-O namespace is append-only across the whole campaign.\n";
    p += "- S10 already used T-O-247..262. S14 must start at T-O-263 unless a higher free ID exists.\n";
    p += "- Before allocating IDs: grep docs/baseline for the highest existing T-O-N and continue N+1. Never reuse/rewrite.\n";
    p += "- Domain-local IDs: S14-Txxx / S15-Txxx / S16-Txxx independent series.\n\n";

    p += "## MANDATORY TOOL USE\n";
    p += "- Always use read_file / grep / list_dir / web_search / open_page before writing claims.\n";
    p += "- Do not answer from memory about accepted truths — open the files.\n";
    p += "- Write deliverables with the write tool (overwrite full file). After write, re-read to verify sections exist.\n";
    p += "- Prefer relative paths from workspace root.\n\n";
    return p;
}

fn nine_section_contract() {
    let p = "";
    p += "## FORMAL DOMAIN-TRUTH REQUIRED SHAPE (spec-index §0.3 + S01/S02/S10 density)\n";
    p += "Header metadata block (project/domain/date/status/version/upstream/downstream/SSOT declaration/scope fence notes).\n";
    p += "Then exactly these sections in order:\n";
    p += "1. Domain 介绍 — value, topology ascii, scope fence in/out tables, key objects, completion definition\n";
    p += "2. 真相层 — T-O summary table + domain-local Sxx-T tables (dense, normative)\n";
    p += "3. 总体方案陈述 — numbered master axes\n";
    p += "4. 具体执行方案清单 — E01..En packages each with: 编号与说明 → 真相层对应 → 执行台账 → 小结\n";
    p += "5. 事实反例 + 风险台账 — legacy anti-patterns, bans, risks, fences\n";
    p += "6. 测试与验收台账 — HARD invariants + required evidence (no fake delivered tests)\n";
    p += "7. Reference-anchor 台账 — legacy-family file anchors + retain/rewrite/delete; web refs as contrast only\n";
    p += "8. Domain verdict — GO/ACCEPTED criteria, residual OOS, downstream constraints\n";
    p += "9. 修订历史 — version/date/status/owner decisions\n";
    p += "Density target: comparable to S01 (~800+ lines) / S02 / S10 formal — not a thin outline.\n";
    p += "Must be implementable without opening QNA. Every MUST/禁止 must map to a Truth ID.\n\n";
    return p;
}

fn qna_full_contract() {
    let p = "";
    p += "## QNA FILE CONTRACT (one-shot full QNA; not multi-round progressive batches)\n";
    p += "Path pattern: docs/baseline/qna-truth/S{NN}.md\n";
    p += "Adapt progressive skeleton into a SINGLE sealed campaign file with:\n";
    p += "- Header: scope, method constraints, evidence authorization, second-opinion waived, workflow-freeze mode\n";
    p += "- §0 状态总览 (archaeology / EC / QNA / RC / freeze / formal)\n";
    p += "- §1 Truth-Gate 台账 (append-only T-O table; final freeze)\n";
    p += "- §2 Existing Conditions (neighbor constraints ledger)\n";
    p += "- §3 legacy-family Archaeology (P positive / N negative anchors with file paths)\n";
    p += "- §4 Full QNA — ALL questions at once (typically 8–12 Qs covering fence+execution+ops+OOS)\n";
    p += "  Each Q must include: title, impact, why-must-decide, options A/B/C(+), RECOMMENDED option,\n";
    p += "  Reasoning, evidence (internal truth IDs + legacy anchors), residual risks\n";
    p += "- §5 Web Reference-Check — for EACH Q: W-P (supporting) / W-N (counter) with URLs + how recommendation adjusted\n";
    p += "- §6 Frozen recommendations (post-RC) mapped to T-O IDs\n";
    p += "- §7 External reference link freeze table (stable URLs + access date 2026-08-12 + purpose)\n";
    p += "- §8 Formal handoff checklist → domain-truth path\n";
    p += "Pre-round fence truths may be recorded as T-O without options if uniquely determined by neighbors.\n";
    p += "Execution questions MUST have options + recommendation + RC adjustment note.\n\n";
    return p;
}

fn step_return_instructions(subsystem, step) {
    let p = "";
    p += "## RETURN\n";
    p += "After writing files, return JSON matching the step schema with:\n";
    p += "- subsystem: \"" + subsystem + "\"\n";
    p += "- step: \"" + step + "\"\n";
    p += "- status: completed|partial|blocked\n";
    p += "- output_paths: absolute or repo-relative paths you wrote\n";
    p += "- summary: 3-8 sentences of what was frozen or produced\n";
    p += "- truth_id_range if applicable (e.g. T-O-263..278)\n";
    p += "- question_count / web_refs_count when applicable\n";
    p += "- notes: residual risks\n";
    return p;
}

// ---------------------------------------------------------------------------
// Per-subsystem identity
// ---------------------------------------------------------------------------
fn subsystem_identity(sid) {
    let p = "";
    if sid == "S14" {
        p += "## SUBSYSTEM IDENTITY: S14 Config, Prompt & Model Registry\n";
        p += "- Domain: F2 治理基础\n";
        p += "- QNA path: docs/baseline/qna-truth/S14.md\n";
        p += "- Formal path: docs/baseline/domain-truth/S14-config-prompt-model-registry.md\n";
        p += "- Truth version target: S14-v1.0 accepted\n";
        p += "- Priority: P1\n";
        p += "- Index scope: workflow version, prompt digest, schema version, model alias/revision,\n";
        p += "  threshold/batch/feature-flag, controlled override, provenance for model outputs.\n";
        p += "- Must answer: config sources, hot-reload, consistent snapshot, task override allowlist, reproducibility.\n";
        p += "- Key invariant: every model product traceable to model + prompt + schema + params versions.\n";
        p += "- Neighbor constraints to inherit (must open and extract):\n";
        p += "  D03 prompts git data/prompts/** + DB hash pointer only; D05 promptA/B/C trinity;\n";
        p += "  D04 mkb_prompt_hash_pointers / model_catalog / adapter_bindings;\n";
        p += "  S11 Inference≠Adapter, binding, no silent swap; S05/S06/S07 PromptRef only;\n";
        p += "  S03 workflow registry relational SSOT; G-10 closed; G-12 deferred agent authoring.\n";
        p += "- legacy-family hunt areas: structurizer/constructor prompt loading, model names, config flags,\n";
        p += "  smind-skill-* prompt/schema paths, dispatcher thresholds.\n";
        p += "- Non-goals: UI config console, multi-tenant feature marketplace, silent remote config as SSOT,\n";
        p += "  storing prompt body in DB as second truth, automatic model fallback platforms.\n\n";
    } else if sid == "S15" {
        p += "## SUBSYSTEM IDENTITY: S15 Observability & Reliability\n";
        p += "- Domain: F3 运行基础\n";
        p += "- QNA path: docs/baseline/qna-truth/S15.md\n";
        p += "- Formal path: docs/baseline/domain-truth/S15-observability-reliability.md\n";
        p += "- Truth version target: S15-v1.0 accepted\n";
        p += "- Priority: P0\n";
        p += "- Index scope: log/trace/metric, task/workflow events, queue/GPU/index metrics,\n";
        p += "  dead-letter, reconciliation, health, operator surfaces.\n";
        p += "- Must answer: event storage location, cardinality control, alerts, ready/live,\n";
        p += "  trace propagation, data-repair authority.\n";
        p += "- Key invariant: team_uuid/task_uuid/trace_uuid on events; failures not log-string-only.\n";
        p += "- D04 already froze physical tables: mkb_domain_events, mkb_ops_diagnostic_logs,\n";
        p += "  mkb_security_audit_events — S15 owns retention/alert/export/runbook semantics NOT table names.\n";
        p += "- Neighbor constraints: D01/S03 process events, S02 polling not events, S12 TX+outbox,\n";
        p += "  S09/S10 readiness probes, S13 GC metrics, S16 security_audit ownership split.\n";
        p += "- legacy-family hunt: smind-console diagnostics, dispatcher logs, vectorizer purge logs,\n";
        p += "  admin ops — extract anti-patterns (log-as-SSOT, missing team scope, UI coupling).\n";
        p += "- Non-goals: full APM SaaS product, public metrics marketplace, replacing business CAS with logs.\n\n";
    } else if sid == "S16" {
        p += "## SUBSYSTEM IDENTITY: S16 Security & Trust Boundary\n";
        p += "- Domain: F4 信任基础\n";
        p += "- QNA path: docs/baseline/qna-truth/S16.md\n";
        p += "- Formal path: docs/baseline/domain-truth/S16-security-trust-boundary.md\n";
        p += "- Truth version target: S16-v1.0 accepted\n";
        p += "- Priority: P0\n";
        p += "- Index scope: internal token, rotation, network boundary, request limit, replay,\n";
        p += "  SSRF, path safety, secrets, log redaction, model supply-chain trust.\n";
        p += "- Must answer: who mints/rotates tokens; which endpoints internal-only; URL fetch policy;\n";
        p += "  how debug isolation works.\n";
        p += "- Key invariant: simple auth ≠ no security; team_uuid is NOT an authorization credential.\n";
        p += "- Neighbor constraints: S01 simple internal token + Team Registry; S02 admission;\n";
        p += "  S05 allowlist/SSRF/secret refs; S13 path bans; S10 dual-fence; D04 security_audit table;\n";
        p += "  OD-01/05 leaf-worker no platform RBAC product.\n";
        p += "- legacy-family hunt: console ACL, team keys, URL fetch, path traversal, secret leakage,\n";
        p += "  fake isolation user≠team.\n";
        p += "- Non-goals: full IdP/OAuth product, fine-grained end-user RBAC platform, public internet multi-tenant SaaS hardening as product scope.\n\n";
    }
    return p;
}

// ---------------------------------------------------------------------------
// Step prompts (1..5) for a given subsystem
// ---------------------------------------------------------------------------
fn prompt_step1_archaeology(sid) {
    let p = campaign_law();
    p += subsystem_identity(sid);
    p += "## YOUR STEP: [1/5] legacy-family archaeology + existing domain-truth alignment\n";
    p += "GOAL: Create/overwrite the QNA file with completed §2 Existing Conditions and §3 Archaeology.\n";
    p += "Also draft header + §0 status (mark archaeology/EC completed; later steps incomplete).\n\n";
    p += "### Required work order\n";
    p += "A. Read docs/baseline/spec-index.md sections for this subsystem + open gates that mention it.\n";
    p += "B. Grep docs/baseline/domain-truth and qna-truth for this subsystem ID and related terms;\n";
    p += "   build Existing Conditions ledger (must/forbid/defer) with Truth IDs cited.\n";
    p += "C. Explore context/legacy-family/ with list_dir+grep for behaviors relevant to this domain.\n";
    p += "   Produce P (positive retain archetypes) and N (negative delete/rewrite anti-patterns)\n";
    p += "   with concrete paths (file:line when possible).\n";
    p += "D. Write docs/baseline/qna-truth/" + sid + ".md with full header discipline (evidence ban, T-O continuity note).\n";
    p += "E. Do NOT invent final execution freezes yet beyond uniquely determined fence inheritances.\n";
    p += "F. Allocate provisional pre-round fence T-O IDs starting from next free global ID if uniquely forced.\n\n";
    p += step_return_instructions(sid, "1-archaeology-ec");
    return p;
}

fn prompt_step2_full_qna(sid) {
    let p = campaign_law();
    p += qna_full_contract();
    p += subsystem_identity(sid);
    p += "## YOUR STEP: [2/5] one-shot full QNA with COMPLETE recommendations\n";
    p += "GOAL: Expand docs/baseline/qna-truth/" + sid + ".md to include the FULL question set + options + recommendations.\n";
    p += "This is NOT progressive multi-round owner chat. Create ALL remaining undecided execution questions at once.\n\n";
    p += "### Required work order\n";
    p += "A. Re-read the current QNA file from step 1 (must exist).\n";
    p += "B. Re-open critical neighbor domain-truth files that constrain this domain.\n";
    p += "C. Identify still-unfrozen execution forks that cannot be uniquely derived.\n";
    p += "D. Author 8–12 high-signal questions covering:\n";
    p += "   - scope fence / ownership split\n";
    p += "   - primary data model & versioning\n";
    p += "   - runtime load/snapshot/consistency\n";
    p += "   - mutation & override policy\n";
    p += "   - failure/error taxonomy\n";
    p += "   - security/observability touchpoints\n";
    p += "   - OOS / deferred list\n";
    p += "E. For each Q: options A/B/C(+), pick RECOMMENDED, deep Reasoning, cite internal evidence.\n";
    p += "F. Keep §5 Web RC as placeholder headers if not yet filled (step 3 fills).\n";
    p += "G. Update §0 status; do not claim freeze yet.\n\n";
    p += "### Recommendation quality bar\n";
    p += "- Prefer greenfield leaf-worker simplicity over platformization.\n";
    p += "- Prefer fail-closed over silent degradation for trust-affecting paths.\n";
    p += "- Prefer explicit versions/hashes over mutable latest for reproducibility domains (esp S14).\n";
    p += "- Prefer events-not-SSOT and retention/export ownership (esp S15).\n";
    p += "- Prefer simple internal token + team scope + SSRF/path/secret fences (esp S16).\n\n";
    p += step_return_instructions(sid, "2-full-qna");
    return p;
}

fn prompt_step3_web_rc(sid) {
    let p = campaign_law();
    p += subsystem_identity(sid);
    p += "## YOUR STEP: [3/5] Web Reference-Check for EVERY question + adjust recommendations\n";
    p += "GOAL: For each Q in docs/baseline/qna-truth/" + sid + ".md, run external web checks and adjust recommendations.\n\n";
    p += "### Required work order\n";
    p += "A. Read the full QNA file; enumerate all Q IDs.\n";
    p += "B. For EACH question, use web_search (and open_page on 1–3 high-quality hits) to gather:\n";
    p += "   - W-P: industry positive patterns supporting the recommendation direction\n";
    p += "   - W-N: counterexamples / failure modes that challenge it\n";
    p += "C. Prefer primary sources: official docs, OWASP, OpenTelemetry, CNCF, model-registry patterns,\n";
    p += "   config management best practices, multi-tenant isolation writeups — as relevant to domain.\n";
    p += "D. Write §5 Web Reference-Check with per-Q W-P/W-N tables including URLs.\n";
    p += "E. Explicitly ADJUST recommendations when W-N is material; document delta (before → after).\n";
    p += "F. Web evidence NEVER overrides D*/accepted S* freezes; only shapes still-open execution choices.\n";
    p += "G. Build draft §7 external reference link freeze table (URL, title, date 2026-08-12, used-by-Q).\n";
    p += "H. Do not mark campaign locked until step 4.\n\n";
    p += "### Search topic hints\n";
    if sid == "S14" {
        p += "- prompt versioning content-addressed; model registry provenance; config snapshot immutability;\n";
        p += "  feature flags vs config as code; ML model card/version pinning; git-ops config.\n";
    } else if sid == "S15" {
        p += "- OpenTelemetry semantic conventions; high-cardinality pitfalls; RED/USE metrics;\n";
        p += "  readiness vs liveness; DLQ patterns; audit log retention; structured event envelopes.\n";
    } else if sid == "S16" {
        p += "- OWASP SSRF/path traversal/secrets; service-to-service tokens; least privilege multi-tenant;\n";
        p += "  log redaction PII; model supply chain; rate limiting internal APIs.\n";
    }
    p += "\n";
    p += step_return_instructions(sid, "3-web-rc");
    return p;
}

fn prompt_step4_freeze(sid) {
    let p = campaign_law();
    p += qna_full_contract();
    p += subsystem_identity(sid);
    p += "## YOUR STEP: [4/5] Seal complete QNA — freeze truths + external reference links\n";
    p += "GOAL: Lock docs/baseline/qna-truth/" + sid + ".md as workflow-frozen evidence package.\n\n";
    p += "### Required work order\n";
    p += "A. Re-read QNA after RC adjustments; ensure every Q has a final recommended option.\n";
    p += "B. Assign final T-O IDs (append-only from next free global ID) for:\n";
    p += "   - pre-round fence truths\n";
    p += "   - each frozen Q recommendation (execution truths)\n";
    p += "C. Fill §1 Truth-Gate table completely (Truth-ID, subtype, locked sentence, source Q, downstream).\n";
    p += "D. Fill §6 Frozen recommendations mapping Q → option → T-O.\n";
    p += "E. Finalize §7 reference link freeze (only URLs actually used; note access date).\n";
    p += "F. Mark document status: locked / Q1–Qn frozen / T-O-a..b / formal pending.\n";
    p += "G. §8 handoff checklist for formal writer (must-have E packages, bans, neighbor backfill notes).\n";
    p += "H. Declare Round-style residual open items as waived or OOS with reason.\n";
    p += "I. Re-verify no forbidden legacy trees are cited.\n\n";
    p += "### Freeze language\n";
    p += "Owner answer field for each Q: `🔒 workflow-frozen / RC-adjusted recommendation {OPTION} → T-O-xxx`\n";
    p += "Campaign status must say second-opinion waived and workflow freeze mode.\n\n";
    p += step_return_instructions(sid, "4-freeze-qna");
    return p;
}

fn prompt_step5_formal(sid) {
    let p = campaign_law();
    p += nine_section_contract();
    p += subsystem_identity(sid);
    p += "## YOUR STEP: [5/5] Formal domain-truth output (S01/S02 information density)\n";
    p += "GOAL: Write the sole execution SSOT formal file for this subsystem.\n\n";
    p += "### Required work order\n";
    p += "A. Read frozen QNA end-to-end (T-O table + recommendations + archaeology + web refs).\n";
    p += "B. Read S01 and S02 and S10 formal headers/structure as density templates (structure, not content).\n";
    p += "C. Read all neighbor truths that this domain must obey or split with.\n";
    p += "D. Write formal domain-truth path for this subsystem with full nine sections + E01..En.\n";
    p += "E. Map every T-O into domain-local Sxx-T IDs; execution packages must be codeable.\n";
    p += "F. Include explicit ownership split tables to neighbors (what this domain owns vs consumes).\n";
    p += "G. Include error families, readiness/health touchpoints, config keys, retention numbers when owned.\n";
    p += "H. Verdict: accepted / GO for domain; list residual OOS and downstream constraints.\n";
    p += "I. After write: re-read file; if thin (<~400 lines) or missing sections, expand before return.\n";
    p += "J. Optionally add a short calibration note block if S14/S15/S16 need mutual forward references\n";
    p += "   without contradicting freeze (mark as provisional neighbor expectation).\n\n";
    p += "### SSOT declaration (must appear near header)\n";
    p += "Implementation/acceptance may depend ONLY on this domain-truth file. QNA is evidence-only.\n\n";
    p += step_return_instructions(sid, "5-formal-domain-truth");
    return p;
}

// ---------------------------------------------------------------------------
// Review / fix / audit prompts
// ---------------------------------------------------------------------------
fn prompt_adversarial_review(dimension) {
    let p = campaign_law();
    p += "## YOU ARE AN ADVERSARIAL REVIEWER (read-mostly; report only — do not edit files)\n";
    p += "Dimension focus: " + dimension + "\n\n";
    p += "### Targets (must open with tools)\n";
    p += "- docs/baseline/qna-truth/S14.md, S15.md, S16.md\n";
    p += "- docs/baseline/domain-truth/S14-config-prompt-model-registry.md\n";
    p += "- docs/baseline/domain-truth/S15-observability-reliability.md\n";
    p += "- docs/baseline/domain-truth/S16-security-trust-boundary.md\n";
    p += "- Cross-check against: D01–D05, S01–S13 key freezes, glossary, spec-index gates\n\n";
    p += "### Finding rules\n";
    p += "- severity: critical | high | medium | low\n";
    p += "- Only report issues with concrete evidence (quote Truth IDs / section headers / contradictions).\n";
    p += "- Prefer cross-document races, ownership double-claims, missing handoffs, silent reopen of closed gates.\n";
    p += "- Empty issues array is valid ONLY after thorough reading of all three formals + QNAs.\n";
    p += "- max 30 issues; prioritize actionable required_fix.\n\n";
    p += "### Dimension guides\n";
    if dimension == "race-and-ownership" {
        p += "Hunt dual SSOT, two domains owning same table/field/state, D* vs S* conflicts, QNA vs formal drift.\n";
    } else if dimension == "blind-spots" {
        p += "Hunt missing failure modes, missing error families, missing retention/secret/lifecycle edges,\n";
        p += "missing readiness, missing team scoping, missing audit paths.\n";
    } else if dimension == "breakpoints-and-handoffs" {
        p += "Hunt broken ports between S14↔S11/S05/S06/S07, S15↔D04/S03/S12, S16↔S01/S05/S13,\n";
        p += "and undefined cut lines for events vs business truth.\n";
    } else if dimension == "coverage-and-oos" {
        p += "Hunt index §3.14-3.16 must-answer gaps, incomplete E packages, underspecified OOS,\n";
        p += "and glossary terms not introduced for new frozen concepts.\n";
    }
    p += "\nReturn JSON matching review schema. Do not modify files.\n";
    return p;
}

fn prompt_adversarial_fix(issues_json) {
    let p = campaign_law();
    p += nine_section_contract();
    p += "## YOUR STEP: Apply adversarial review fixes to S14–S16\n";
    p += "You receive verified review issues (JSON). Fix only real issues with evidence.\n\n";
    p += "### Issues JSON\n";
    p += issues_json;
    p += "\n\n### Required work order\n";
    p += "A. Re-read each cited target file section before editing.\n";
    p += "B. Apply minimal coherent fixes to domain-truth formals first (SSOT).\n";
    p += "C. If a freeze was incomplete, update corresponding qna-truth T-O notes without renumbering existing IDs.\n";
    p += "   New truths only if required: append next free T-O IDs.\n";
    p += "D. Do not 'fix' by deleting coverage; expand or correct.\n";
    p += "E. Skip low-confidence issues; list them under deferred.\n";
    p += "F. Keep D* supremacy; if S contradicts D, fix S.\n";
    p += "G. After edits, re-read changed sections for consistency.\n\n";
    p += "Return JSON matching fix schema.\n";
    return p;
}

fn prompt_glossary_index_audit() {
    let p = campaign_law();
    p += "## YOUR STEP: Full truth-layer audit + glossary + spec-index update\n";
    p += "GOAL: After S14–S16 accepted formals exist, audit entire baseline truth layer for races/blind spots/coverage,\n";
    p += "then update glossary and spec-index comprehensively.\n\n";
    p += "### Required work order\n";
    p += "A. Read docs/baseline/spec-index.md fully; read glossary fully.\n";
    p += "B. Confirm S14/S15/S16 formal files exist and are non-thin; extract versions and T-O ranges.\n";
    p += "C. Update progress table rows 14–16 to accepted with accurate backfill summaries.\n";
    p += "D. Expand §3.14 / §3.15 / §3.16 with frozen status, key invariants, completion backfill.\n";
    p += "E. Close or annotate any gates that S14–S16 fully resolve; leave truly deferred gates as deferred.\n";
    p += "F. Update §1.2 cross-system docs row for glossary version; bump index revision history.\n";
    p += "G. Update docs/baseline/spec-glossary.md with all new frozen terms from S14–S16\n";
    p += "   (registry objects, event envelope terms, security boundary terms, etc.).\n";
    p += "H. Full-layer adversarial scan notes (races/blind spots/coverage) — if critical gaps found in S01–S13\n";
    p += "   that are caused by S14–S16 freezes, apply minimal calibration notes to affected domain-truth\n";
    p += "   headers only (do not rewrite unrelated history).\n";
    p += "I. Ensure index status vocabulary remains coherent (active index; not frozen truth index yet unless\n";
    p += "   all 16 S + D + 00 are accepted — 17/18 may still be pending; do NOT claim full truth freeze).\n";
    p += "J. Write a short audit report to docs/baseline/qna-truth/_s14-s16-campaign-audit.md summarizing\n";
    p += "   coverage, residual gaps, and files touched.\n\n";
    p += "Return JSON matching audit schema (glossary_version, index_version, files_touched, open_gaps).\n";
    return p;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
fn agent_ok(r) {
    r != () && r.success
}

// NOTE: Rhai host functions do not close over top-level `let` maps.
// Schemas must be passed in explicitly.
fn run_subsystem_pipeline(sid, schema) {
    log("=== " + sid + " pipeline start ===");

    // Step 1 — archaeology + EC
    let r1 = agent(prompt_step1_archaeology(sid), #{
        label: sid + "-1-archaeology",
        capability_mode: "all",
        output_schema: schema,
    });
    if !agent_ok(r1) {
        log(sid + " step1 FAILED");
        await_user("verification", sid + " step1 archaeology failed. Inspect agent output, repair, then resume.");
    } else {
        log(sid + " step1 ok: " + r1.output.status);
    }

    // Step 2 — full QNA
    let r2 = agent(prompt_step2_full_qna(sid), #{
        label: sid + "-2-full-qna",
        capability_mode: "all",
        output_schema: schema,
    });
    if !agent_ok(r2) {
        log(sid + " step2 FAILED");
        await_user("verification", sid + " step2 full QNA failed. Resume after repair.");
    } else {
        log(sid + " step2 ok: " + r2.output.status);
    }

    // Step 3 — web RC
    let r3 = agent(prompt_step3_web_rc(sid), #{
        label: sid + "-3-web-rc",
        capability_mode: "all",
        output_schema: schema,
    });
    if !agent_ok(r3) {
        log(sid + " step3 FAILED");
        await_user("verification", sid + " step3 web RC failed. Resume after repair.");
    } else {
        log(sid + " step3 ok: " + r3.output.status);
    }

    // Step 4 — freeze QNA
    let r4 = agent(prompt_step4_freeze(sid), #{
        label: sid + "-4-freeze",
        capability_mode: "all",
        output_schema: schema,
    });
    if !agent_ok(r4) {
        log(sid + " step4 FAILED");
        await_user("verification", sid + " step4 freeze failed. Resume after repair.");
    } else {
        log(sid + " step4 ok: " + r4.output.status);
    }

    // Step 5 — formal domain-truth
    let r5 = agent(prompt_step5_formal(sid), #{
        label: sid + "-5-formal",
        capability_mode: "all",
        output_schema: schema,
    });
    if !agent_ok(r5) {
        log(sid + " step5 FAILED");
        await_user("verification", sid + " step5 formal failed. Resume after repair.");
    } else {
        log(sid + " step5 ok: " + r5.output.status);
    }

    log("=== " + sid + " pipeline done ===");
    return #{
        sid: sid,
        step1: if agent_ok(r1) { r1.output } else { () },
        step2: if agent_ok(r2) { r2.output } else { () },
        step3: if agent_ok(r3) { r3.output } else { () },
        step4: if agent_ok(r4) { r4.output } else { () },
        step5: if agent_ok(r5) { r5.output } else { () },
    };
}

// ---------------------------------------------------------------------------
// Main orchestration
// ---------------------------------------------------------------------------

// Optional args:
//   args.only = "S14" | "S15" | "S16" | "review" | "audit" | "all" (default all)
//   args.skip_review = true
//   args.skip_audit = true
let only = "all";
let skip_review = false;
let skip_audit = false;
if args != () {
    if args.only != () { only = args.only; }
    if args.skip_review != () && args.skip_review == true { skip_review = true; }
    if args.skip_audit != () && args.skip_audit == true { skip_audit = true; }
}

let results = #{};
let run_s14 = only == "all" || only == "S14";
let run_s15 = only == "all" || only == "S15";
let run_s16 = only == "all" || only == "S16";
let run_review = !skip_review && (only == "all" || only == "review");
let run_audit = !skip_audit && (only == "all" || only == "audit" || only == "review");

// ----- Phase S14 -----
if run_s14 {
    phase("S14");
    results.s14 = run_subsystem_pipeline("S14", step_schema);
}

// ----- Phase S15 -----
if run_s15 {
    phase("S15");
    results.s15 = run_subsystem_pipeline("S15", step_schema);
}

// ----- Phase S16 -----
if run_s16 {
    phase("S16");
    results.s16 = run_subsystem_pipeline("S16", step_schema);
}

// ----- Phase Adversarial Review -----
let all_issues = [];
if run_review {
    phase("Adversarial-Review");
    log("Adversarial review panel on S14-S16");
    let dimensions = [
        "race-and-ownership",
        "blind-spots",
        "breakpoints-and-handoffs",
        "coverage-and-oos",
    ];
    let jobs = [];
    for d in dimensions {
        jobs.push(#{
            prompt: prompt_adversarial_review(d),
            label: "review-" + d,
            capability_mode: "read-only",
            output_schema: review_schema,
        });
    }
    let review_results = parallel(jobs);
    let i = 0;
    for rr in review_results {
        if rr != () && rr.success && rr.output.issues != () {
            for issue in rr.output.issues {
                all_issues.push(issue);
            }
            log("reviewer " + dimensions[i] + " issues=" + rr.output.issues.len().to_string());
        } else {
            log("reviewer " + dimensions[i] + " FAILED or empty");
        }
        i += 1;
    }
    log("Total adversarial issues collected: " + all_issues.len().to_string());
    let scratch_path = write_scratch_file("s14-s16-review-issues.json", json_encode(all_issues));
    log("Review issues scratch: " + scratch_path);
    results.review_issue_count = all_issues.len();
}

// ----- Phase Adversarial Fix -----
if run_review {
    phase("Adversarial-Fix");
    if all_issues.len() == 0 {
        log("No issues to fix — skip fix agent");
        results.fix = #{ status: "noop", fixes_applied: 0, summary: "No adversarial issues" };
    } else {
        let issues_json = json_encode(all_issues);
        let fix_r = agent(prompt_adversarial_fix(issues_json), #{
            label: "s14-s16-fix",
            capability_mode: "all",
            output_schema: fix_schema,
        });
        if agent_ok(fix_r) {
            results.fix = fix_r.output;
            log("Fix applied: " + fix_r.output.fixes_applied.to_string());
        } else {
            log("Fix agent FAILED");
            await_user("verification", "Adversarial fix agent failed. Resume after manual repair.");
            results.fix = #{ status: "failed" };
        }
    }
}

// ----- Phase Glossary + Index + full truth audit -----
if run_audit {
    phase("Glossary-Index-Audit");
    let audit_r = agent(prompt_glossary_index_audit(), #{
        label: "glossary-index-audit",
        capability_mode: "all",
        output_schema: audit_schema,
    });
    if agent_ok(audit_r) {
        results.audit = audit_r.output;
        log("Audit: " + audit_r.output.summary);
    } else {
        log("Audit agent FAILED");
        await_user("verification", "Glossary/index audit agent failed. Resume after repair.");
        results.audit = #{ status: "failed" };
    }
}

// ----- Complete -----
let summary = "domain-truth-s14-s16 complete; only=" + only;
if results.review_issue_count != () {
    summary += "; review_issues=" + results.review_issue_count.to_string();
}
if results.audit != () && results.audit.summary != () {
    summary += "; audit=" + results.audit.summary;
}

complete(#{
    summary: summary,
    only: only,
    results: results,
});
