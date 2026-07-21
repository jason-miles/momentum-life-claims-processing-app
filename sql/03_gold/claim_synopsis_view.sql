-- ============================================================================
-- Gold: claim_synopsis_view  (VIEW)
-- The "anti-swivel-chair" object: ONE WIDE ROW PER CLAIM, joining the claim
-- spine to policy, primary life, the matching benefit, requirement
-- completeness, third-party verification, and the document list. This is the
-- certified structured context the assessment agent reads instead of hopping
-- across ten screens.
--
-- Guarantees ONE ROW FOR EVERY CLAIM (LEFT JOINs off the claim spine), so the
-- three seeded scenarios (CLM-DEATH-CLEAN, CLM-DISAB-DISCREP,
-- CLM-SUSPECT-FRAUD) are always present.
--
-- NOTE on benefit matching: claim_type uses 'income' while the benefit
-- taxonomy uses 'income_protection'; we normalise claim_type -> benefit_type
-- so the correct benefit is picked for the claim.
-- ============================================================================
CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_claims_gold.claim_synopsis_view AS
WITH primary_life AS (
    -- One representative life per policy (the "first" life, matching the loader).
    SELECT
        policy_no, life_id, occupation_at_inception, province, dob, sensitivity, smoker_flag
    FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.life
    QUALIFY ROW_NUMBER() OVER (PARTITION BY policy_no ORDER BY life_id) = 1
),
claim_benefit AS (
    -- The benefit backing the claim. PREFER the benefit whose type matches the
    -- claim (income -> income_protection); otherwise fall back to any benefit on
    -- the policy (preferring in-force, then largest). A real claim is always
    -- against a held benefit, so we join at policy level and rank by type-match
    -- rather than filtering to the exact type (which left ~38% of synthetic
    -- claims with no benefit, since a policy carries only a random 1-4 types).
    SELECT
        c.claim_no,
        b.benefit_type,
        b.sum_assured,
        b.status      AS benefit_status,
        b.loadings,
        b.exclusions
    FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claim c
    JOIN elexon_app_for_settlement_acc_catalog.momentum_claims_silver.benefit b
      ON b.policy_no = c.policy_no
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY c.claim_no
        ORDER BY
            (b.benefit_type = CASE WHEN c.claim_type = 'income'
                                   THEN 'income_protection' ELSE c.claim_type END) DESC,
            (b.status = 'in_force') DESC,
            b.sum_assured DESC
    ) = 1
),
req_rollup AS (
    SELECT
        claim_no,
        COUNT(*)                                                       AS reqs_total,
        COUNT_IF(status = 'received')                                  AS reqs_received,
        CONCAT_WS(', ', COLLECT_LIST(CASE WHEN status = 'outstanding'
                                          THEN code END))              AS outstanding_codes
    FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.requirement
    GROUP BY claim_no
),
tp_rollup AS (
    SELECT
        claim_no,
        CONCAT_WS(', ', COLLECT_LIST(CONCAT(source, ':', result_summary))) AS tp_summary
    FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.tp_verification
    GROUP BY claim_no
),
doc_rollup AS (
    SELECT
        claim_no,
        CONCAT_WS(', ', COLLECT_LIST(doc_id)) AS document_ids,
        COUNT(*)                              AS document_count
    FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.document
    GROUP BY claim_no
)
SELECT
    -- ---- claim spine ----
    c.claim_no,
    c.policy_no,
    c.claim_type,
    c.event_date,
    c.lodge_date,
    c.state,
    c.occupation_at_claim,
    c.decision,
    c.decided_date,
    c.assessor,
    c.risk_score,
    c.is_ntu,
    -- ---- policy ----
    p.status                            AS policy_status,
    p.inception_date,
    p.broker,
    -- ---- primary life ----
    pl.occupation_at_inception,
    pl.province,
    pl.dob,
    pl.sensitivity,
    pl.smoker_flag,
    -- ---- matching benefit ----
    cb.benefit_type,
    cb.sum_assured,
    cb.benefit_status,
    cb.loadings,
    cb.exclusions,
    -- ---- requirement completeness ----
    COALESCE(rr.reqs_received, 0)       AS reqs_received,
    COALESCE(rr.reqs_total, 0)          AS reqs_total,
    rr.outstanding_codes,
    -- ---- third-party summary ----
    tp.tp_summary,
    -- ---- document list ----
    dr.document_ids,
    COALESCE(dr.document_count, 0)      AS document_count,
    -- ---- computed decision-support flags ----
    (c.occupation_at_claim <> pl.occupation_at_inception)              AS occupation_mismatch,
    DATEDIFF(c.lodge_date, c.event_date)                               AS days_pre_lodge,
    DATEDIFF(c.event_date, p.inception_date)                           AS days_since_inception_at_event,
    (DATEDIFF(c.event_date, p.inception_date) < 180)                   AS early_claim_flag
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claim c
LEFT JOIN elexon_app_for_settlement_acc_catalog.momentum_claims_silver.policy p
       ON p.policy_no = c.policy_no
LEFT JOIN primary_life pl ON pl.policy_no = c.policy_no
LEFT JOIN claim_benefit cb ON cb.claim_no = c.claim_no
LEFT JOIN req_rollup    rr ON rr.claim_no = c.claim_no
LEFT JOIN tp_rollup     tp ON tp.claim_no = c.claim_no
LEFT JOIN doc_rollup    dr ON dr.claim_no = c.claim_no;
