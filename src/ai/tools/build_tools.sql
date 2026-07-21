-- Deploy the six UC-function agent tools (schema momentum_claims_ai).
-- Generated from src/ai/tools/*.sql — one CREATE FUNCTION per file.
CREATE SCHEMA IF NOT EXISTS elexon_app_for_settlement_acc_catalog.momentum_claims_ai;

-- check_claimability.sql
-- ============================================================================
-- UC Function tool: check_claimability(claim_no)
-- ----------------------------------------------------------------------------
-- Evaluates a claim against the externalised rulebook in
-- silver.claimability_rule for its own claim_type PLUS the 'all' rules, using
-- facts from gold.claim_synopsis_view and silver.requirement. Returns JSON:
--   { claimable: bool,
--     failed_hard_rules: [{rule_id, rule_key, description}],
--     soft_warnings:     [{rule_id, rule_key, description}],
--     missing_docs:      [{rule_id, rule_key, description}] }
--
-- claimable == (no HARD rule failed). This is decision SUPPORT, never a final
-- pay/decline decision — the agent stays advisory.
--
-- Rule -> fact mapping (implemented in SQL):
--   benefit_in_force              -> benefit_status = 'in_force'
--   policy_in_force               -> policy_status  = 'in_force'
--   death_cert_received           -> REQ-DEATH-CERT requirement received
--   specialist_report_received    -> REQ-SPECIALIST requirement received
--   income_proof_received         -> an income-proof requirement received
--   diagnosis_confirmed           -> a diagnosis requirement received (else pass)
--   occupation_consistent         -> NOT occupation_mismatch
--   not_within_suicide_exclusion  -> days_since_inception_at_event >= 730
--                                    OR claim_type <> 'death'
--   beneficiary_nominated         -> assumed satisfied (no beneficiary entity modelled)
--
-- "missing_docs" surfaces failed hard rules whose remedy is an outstanding
-- document/requirement (so the UI can route them to a REQUEST INFO action).
-- ============================================================================
CREATE OR REPLACE FUNCTION elexon_app_for_settlement_acc_catalog.momentum_claims_ai.check_claimability(
    claim_no STRING COMMENT 'Claim number, e.g. CLM-DISAB-DISCREP'
)
RETURNS STRING
COMMENT 'Evaluates a claim against silver.claimability_rule (claim_type + all) and returns {claimable, failed_hard_rules, soft_warnings, missing_docs} as JSON.'
RETURN (
    SELECT to_json(
        struct(
            (COUNT_IF(NOT t.passed AND t.severity = 'hard') = 0)          AS claimable,
            collect_list(CASE WHEN NOT t.passed AND t.severity = 'hard'
                              THEN struct(t.rule_id, t.rule_key, t.description) END) AS failed_hard_rules,
            collect_list(CASE WHEN NOT t.passed AND t.severity = 'soft'
                              THEN struct(t.rule_id, t.rule_key, t.description) END) AS soft_warnings,
            collect_list(CASE WHEN NOT t.passed
                               AND t.rule_key IN ('death_cert_received',
                                                  'specialist_report_received',
                                                  'income_proof_received',
                                                  'diagnosis_confirmed')
                              THEN struct(t.rule_id, t.rule_key, t.description) END) AS missing_docs
        )
    )
    FROM (
        SELECT
            r.rule_id,
            r.rule_key,
            r.description,
            r.severity,
            CASE r.rule_key
                WHEN 'benefit_in_force'             THEN (v.benefit_status = 'in_force')
                WHEN 'policy_in_force'              THEN (v.policy_status  = 'in_force')
                WHEN 'death_cert_received'          THEN (COALESCE(rq.has_death_cert, 0) = 1)
                WHEN 'specialist_report_received'   THEN (COALESCE(rq.has_specialist, 0) = 1)
                WHEN 'income_proof_received'        THEN (COALESCE(rq.has_income_proof, 0) = 1)
                WHEN 'diagnosis_confirmed'          THEN (COALESCE(rq.has_diagnosis, 1) = 1)
                WHEN 'occupation_consistent'        THEN (NOT COALESCE(v.occupation_mismatch, false))
                WHEN 'not_within_suicide_exclusion' THEN (v.days_since_inception_at_event >= 730
                                                          OR v.claim_type <> 'death')
                WHEN 'beneficiary_nominated'        THEN true
                ELSE true
            END AS passed
        FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claimability_rule r
        JOIN elexon_app_for_settlement_acc_catalog.momentum_claims_gold.claim_synopsis_view v
          ON v.claim_no = check_claimability.claim_no
         AND (r.claim_type = v.claim_type OR r.claim_type = 'all')
        LEFT JOIN (
            SELECT
                claim_no,
                MAX(CASE WHEN code = 'REQ-DEATH-CERT'   AND status = 'received' THEN 1 ELSE 0 END) AS has_death_cert,
                MAX(CASE WHEN code = 'REQ-SPECIALIST'   AND status = 'received' THEN 1 ELSE 0 END) AS has_specialist,
                MAX(CASE WHEN (code ILIKE '%INCOME%' OR description ILIKE '%income%')
                          AND status = 'received' THEN 1 ELSE 0 END)                               AS has_income_proof,
                MAX(CASE WHEN (code ILIKE '%DIAG%' OR description ILIKE '%diagnos%')
                          AND status = 'received' THEN 1 ELSE 0 END)                               AS has_diagnosis
            FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.requirement
            GROUP BY claim_no
        ) rq ON rq.claim_no = v.claim_no
    ) t
);

-- get_claim_context.sql
-- ============================================================================
-- UC Function tool: get_claim_context(claim_no)
-- ----------------------------------------------------------------------------
-- The agent's primary "give me everything about this claim" call. Returns the
-- ONE WIDE ROW from gold.claim_synopsis_view for the requested claim, serialised
-- as a JSON object string. This is the certified structured context (policy,
-- life, benefit, requirement completeness, third-party, decision-support flags)
-- the Synopsis Agent reads instead of swivel-chairing across ten screens.
--
-- Governed callable surface: registered in Unity Catalog, so every invocation is
-- lineage-tracked and permission-checked like any other UC object.
-- Returns NULL-safe JSON: an empty object {} if the claim_no is unknown.
-- ============================================================================
CREATE OR REPLACE FUNCTION elexon_app_for_settlement_acc_catalog.momentum_claims_ai.get_claim_context(
    claim_no STRING COMMENT 'Claim number, e.g. CLM-DISAB-DISCREP'
)
RETURNS STRING
COMMENT 'Returns the wide claim_synopsis_view row for a claim as a JSON object (policy, life, benefit, requirement completeness, third-party summary, decision-support flags).'
RETURN (
    SELECT to_json(struct(v.*))
    FROM elexon_app_for_settlement_acc_catalog.momentum_claims_gold.claim_synopsis_view v
    WHERE v.claim_no = get_claim_context.claim_no
    LIMIT 1
);

-- get_policy_benefits.sql
-- ============================================================================
-- UC Function tool: get_policy_benefits(policy_no)
-- ----------------------------------------------------------------------------
-- Returns every benefit line on a policy with its status, sum assured and any
-- loadings/exclusions, as a JSON array of objects. Lets the agent reason about
-- the full cover on a policy (not just the one benefit matching the claim), e.g.
-- to spot a lapsed benefit or an exclusion that bears on claimability.
--
-- Returns '[]' when the policy has no benefits / is unknown.
-- ============================================================================
CREATE OR REPLACE FUNCTION elexon_app_for_settlement_acc_catalog.momentum_claims_ai.get_policy_benefits(
    policy_no STRING COMMENT 'Policy number, e.g. POL-DISAB-DISCREP'
)
RETURNS STRING
COMMENT 'Returns all benefits on a policy (benefit_type, sum_assured, status, loadings, exclusions) as a JSON array.'
RETURN (
    SELECT COALESCE(
        to_json(
            collect_list(
                struct(
                    b.benefit_id,
                    b.benefit_type,
                    b.sum_assured,
                    b.status AS benefit_status,
                    b.loadings,
                    b.exclusions
                )
            )
        ),
        '[]'
    )
    FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.benefit b
    WHERE b.policy_no = get_policy_benefits.policy_no
);

-- get_third_party_verifications.sql
-- ============================================================================
-- UC Function tool: get_third_party_verifications(claim_no)
-- ----------------------------------------------------------------------------
-- Returns the third-party verification results for a claim (VPD, other_insurer,
-- bank, identity) as a JSON array of {source, result_summary, checked_ts}.
-- Lets the agent corroborate the claim against external checks -- e.g. DS3's
-- "2 prior claims at other insurers", a classic fraud signal.
--
-- Returns '[]' when the claim has no third-party checks.
-- ============================================================================
CREATE OR REPLACE FUNCTION elexon_app_for_settlement_acc_catalog.momentum_claims_ai.get_third_party_verifications(
    claim_no STRING COMMENT 'Claim number, e.g. CLM-SUSPECT-FRAUD'
)
RETURNS STRING
COMMENT 'Returns third-party verification summaries (VPD / other_insurer / bank / identity) for a claim as a JSON array.'
RETURN (
    SELECT COALESCE(
        to_json(
            collect_list(
                struct(
                    tp.source,
                    tp.result_summary,
                    tp.checked_ts
                )
            )
        ),
        '[]'
    )
    FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.tp_verification tp
    WHERE tp.claim_no = get_third_party_verifications.claim_no
);

-- list_outstanding_requirements.sql
-- ============================================================================
-- UC Function tool: list_outstanding_requirements(claim_no)
-- ----------------------------------------------------------------------------
-- Returns the requirement checklist for a claim split into received vs
-- outstanding, plus counts, as a JSON object:
--   { claim_no, reqs_total, reqs_received, reqs_outstanding,
--     outstanding: [{code, description}], received: [{code, description}] }
--
-- Drives the "REQUEST INFO" recommendation path and the outstanding-requirement
-- discrepancy flag (e.g. DS2's missing specialist medical report).
-- ============================================================================
CREATE OR REPLACE FUNCTION elexon_app_for_settlement_acc_catalog.momentum_claims_ai.list_outstanding_requirements(
    claim_no STRING COMMENT 'Claim number, e.g. CLM-DISAB-DISCREP'
)
RETURNS STRING
COMMENT 'Returns received vs outstanding requirements for a claim, with counts, as a JSON object.'
RETURN (
    SELECT to_json(
        struct(
            list_outstanding_requirements.claim_no AS claim_no,
            COUNT(*)                                                 AS reqs_total,
            COUNT_IF(r.status = 'received')                          AS reqs_received,
            COUNT_IF(r.status = 'outstanding')                       AS reqs_outstanding,
            collect_list(CASE WHEN r.status = 'outstanding'
                              THEN struct(r.code, r.description) END) AS outstanding,
            collect_list(CASE WHEN r.status = 'received'
                              THEN struct(r.code, r.description) END) AS received
        )
    )
    FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.requirement r
    WHERE r.claim_no = list_outstanding_requirements.claim_no
);

-- search_claim_documents.sql
-- ============================================================================
-- UC Function tool: search_claim_documents(claim_no, query)
-- ----------------------------------------------------------------------------
-- The governed, callable document-retrieval surface for a claim. Returns the
-- claim's documents (doc_id, doc_type, parsed_text) as a JSON array, preferring
-- rows whose parsed_text matches the free-text `query` (ILIKE) but always
-- falling back to the claim's full document set so the agent is never starved
-- of context.
--
-- NOTE: semantic retrieval is served by the Delta Sync vector index
-- momentum_claims_ai.idx_documents (see build_indexes.py). This SQL tool is the
-- governed, permission-checked callable that the Agent Framework can register
-- as a function tool; for the demo it does a lexical match over the same corpus.
--
-- Returns '[]' when the claim has no documents.
-- ============================================================================
CREATE OR REPLACE FUNCTION elexon_app_for_settlement_acc_catalog.momentum_claims_ai.search_claim_documents(
    claim_no STRING COMMENT 'Claim number, e.g. CLM-DISAB-DISCREP',
    query    STRING COMMENT 'Free-text query; matched against parsed_text (ILIKE). Pass empty string to return all docs.'
)
RETURNS STRING
COMMENT 'Returns a claim''s documents (doc_id, doc_type, parsed_text), preferring lexical matches on the query but always returning the claim''s docs, as a JSON array.'
RETURN (
    SELECT COALESCE(
        to_json(
            collect_list(
                struct(
                    d.doc_id,
                    d.doc_type,
                    d.parsed_text,
                    -- surface whether this row actually matched the query text
                    (get_search_query.q = '' OR d.parsed_text ILIKE '%' || get_search_query.q || '%') AS matched_query
                )
            )
        ),
        '[]'
    )
    FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.document d
    CROSS JOIN (SELECT COALESCE(search_claim_documents.query, '') AS q) get_search_query
    WHERE d.claim_no = search_claim_documents.claim_no
);
echo ""
echo "-- search_similar_documents.sql (semantic retriever; needs idx_documents ONLINE)"
cat src/ai/tools/search_similar_documents.sql

-- search_similar_documents.sql (semantic retriever; needs idx_documents ONLINE)
-- Claims semantic retriever over the idx_documents Vector Search index.
-- Added alongside the lexical search_claim_documents tool so the claims synopsis
-- can cite semantically-similar prior claims (RAG symmetry with underwriting).
-- Requires momentum_claims_ai.idx_documents to be ONLINE.
CREATE OR REPLACE FUNCTION elexon_app_for_settlement_acc_catalog.momentum_claims_ai.search_similar_documents(query STRING)
RETURNS TABLE(claim_no STRING, doc_type STRING, chunk_text STRING, score DOUBLE)
COMMENT 'Semantic search over claim documents (Vector Search idx_documents), top 5'
RETURN
SELECT claim_no, doc_type, chunk_text, search_score AS score
FROM vector_search(index => 'elexon_app_for_settlement_acc_catalog.momentum_claims_ai.idx_documents',
                   query_text => query, num_results => 5);
