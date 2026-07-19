-- Gold build: certified serving views. Generated from sql/03_gold/*.sql
CREATE SCHEMA IF NOT EXISTS elexon_app_for_settlement_acc_catalog.momentum_claims_gold;

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
    -- The benefit whose type matches the claim (income -> income_protection).
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
     AND b.benefit_type = CASE WHEN c.claim_type = 'income'
                               THEN 'income_protection' ELSE c.claim_type END
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY c.claim_no
        ORDER BY (b.status = 'in_force') DESC, b.sum_assured DESC
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

-- ============================================================================
-- Gold: decision_split  (VIEW)
-- Pay / decline / refer mix per claim_type, as counts and as a percentage of
-- all decided claims within that claim_type.
-- Columns: claim_type, decision, n, pct.
-- Only claims with a non-null decision are counted.
-- ============================================================================
CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_claims_gold.decision_split AS
SELECT
    claim_type,
    decision,
    COUNT(*)                                                                 AS n,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY claim_type), 2) AS pct
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claim
WHERE decision IS NOT NULL
GROUP BY claim_type, decision;

-- ============================================================================
-- Gold: ntu_at_risk  (VIEW)
-- Pre-lodge claims (state = 'initiated') that have gone quiet for more than
-- 7 days, scored with a drop_off_propensity (0-1) so ops can intervene before
-- the claim is Not Taken Up.
--
-- drop_off_propensity: blends how long the claim has been outstanding with how
-- many requirements are still missing, each normalised and capped to 0-1, then
-- weighted 60% days / 40% outstanding requirements.
--   days factor : LEAST(days_outstanding / 60, 1)
--   reqs factor : LEAST(n_outstanding_reqs / 5, 1)
-- Columns: claim_no, policy_no, claim_type, event_date, days_outstanding,
--          n_outstanding_reqs, drop_off_propensity.
-- ============================================================================
CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_claims_gold.ntu_at_risk AS
WITH outstanding AS (
    SELECT claim_no, COUNT_IF(status = 'outstanding') AS n_outstanding_reqs
    FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.requirement
    GROUP BY claim_no
)
SELECT
    c.claim_no,
    c.policy_no,
    c.claim_type,
    c.event_date,
    DATEDIFF(current_date(), c.event_date)          AS days_outstanding,
    COALESCE(o.n_outstanding_reqs, 0)               AS n_outstanding_reqs,
    ROUND(
        0.6 * LEAST(DATEDIFF(current_date(), c.event_date) / 60.0, 1.0)
      + 0.4 * LEAST(COALESCE(o.n_outstanding_reqs, 0) / 5.0, 1.0)
    , 3)                                            AS drop_off_propensity
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claim c
LEFT JOIN outstanding o ON o.claim_no = c.claim_no
WHERE c.state = 'initiated'
  AND c.event_date < current_date() - INTERVAL 7 DAYS;

-- ============================================================================
-- Gold: ntu_funnel  (VIEW)
-- Claim drop-off funnel: counts of claims and NTU ("Not Taken Up") claims by
-- stage (state) and claim_type. Feeds the pre-lodge leakage narrative.
-- Columns: claim_type, state, n_claims, n_ntu.
-- ============================================================================
CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_claims_gold.ntu_funnel AS
SELECT
    claim_type,
    state,
    COUNT(*)              AS n_claims,
    COUNT_IF(is_ntu)      AS n_ntu
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claim
GROUP BY claim_type, state;

-- ============================================================================
-- Gold: ops_metrics  (VIEW)
-- Per-claim throughput / SLA view built from the claim_event stream.
-- Measures wall-clock days from lodge to decision against a 20-day SLA.
-- Columns: claim_no, claim_type, assessor, lodge_ts, decided_ts,
--          days_lodge_to_decision, sla_days, sla_breach.
-- NOTE: only claims that have both lodged and decided timestamps produce a
-- finite days_lodge_to_decision; still-open claims carry NULL there and a
-- NULL sla_breach.
-- ============================================================================
CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_claims_gold.ops_metrics AS
WITH ev AS (
    SELECT
        claim_no,
        MIN(CASE WHEN event = 'lodged'  THEN event_ts END) AS lodge_ts,
        MIN(CASE WHEN event = 'decided' THEN event_ts END) AS decided_ts
    FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claim_event
    GROUP BY claim_no
)
SELECT
    c.claim_no,
    c.claim_type,
    c.assessor,
    ev.lodge_ts,
    ev.decided_ts,
    DATEDIFF(ev.decided_ts, ev.lodge_ts)                        AS days_lodge_to_decision,
    20                                                          AS sla_days,
    CASE
        WHEN ev.lodge_ts IS NULL OR ev.decided_ts IS NULL THEN NULL
        ELSE DATEDIFF(ev.decided_ts, ev.lodge_ts) > 20
    END                                                         AS sla_breach
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claim c
LEFT JOIN ev ON ev.claim_no = c.claim_no;

-- ============================================================================
-- Gold: requirement_analytics  (VIEW)
-- Requirement completion patterns per claim_type and requirement code: how
-- often each requirement is received vs still outstanding, and how long it
-- takes to arrive once requested. Surfaces the chronic bottleneck documents.
-- Columns: claim_type, code, description, n_total, n_received, n_outstanding,
--          pct_received, avg_days_to_receive.
-- avg_days_to_receive measured over received requirements only
-- (received_ts - requested_ts).
-- ============================================================================
CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_claims_gold.requirement_analytics AS
SELECT
    c.claim_type,
    r.code,
    MAX(r.description)                                                  AS description,
    COUNT(*)                                                            AS n_total,
    COUNT_IF(r.status = 'received')                                     AS n_received,
    COUNT_IF(r.status = 'outstanding')                                  AS n_outstanding,
    ROUND(100.0 * COUNT_IF(r.status = 'received') / COUNT(*), 2)        AS pct_received,
    ROUND(AVG(CASE WHEN r.status = 'received'
                   THEN DATEDIFF(r.received_ts, r.requested_ts) END), 2) AS avg_days_to_receive
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.requirement r
JOIN elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claim c
  ON c.claim_no = r.claim_no
GROUP BY c.claim_type, r.code;
