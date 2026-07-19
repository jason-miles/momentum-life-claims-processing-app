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
