-- ============================================================================
-- Silver: claim
-- Conformed / typed / deduped passthrough of bronze.claim, keyed by claim_no.
-- This is the spine of the claims domain.
-- DQ NOTE (DLT-style expectation):
--   EXPECT claim_no IS NOT NULL
--   EXPECT claim_type IN ('death','disability','critical_illness','income')
--   EXPECT state IN ('initiated','lodged','in_assessment','decided','paid')
--   EXPECT decision IN ('pay','decline','refer') OR decision IS NULL
--   EXPECT event_date IS NOT NULL
-- Casts: event_date/lodge_date/decided_date -> DATE, risk_score -> DOUBLE,
--        is_ntu -> BOOLEAN.
-- Dedup: one row per claim_no (keep the most recently decided / lodged record).
-- ============================================================================
CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claim AS
SELECT
    CAST(claim_no            AS STRING)  AS claim_no,
    CAST(policy_no           AS STRING)  AS policy_no,
    CAST(claim_type          AS STRING)  AS claim_type,
    CAST(event_date          AS DATE)    AS event_date,
    CAST(lodge_date          AS DATE)    AS lodge_date,
    CAST(state               AS STRING)  AS state,
    CAST(occupation_at_claim AS STRING)  AS occupation_at_claim,
    CAST(decision            AS STRING)  AS decision,
    CAST(decided_date        AS DATE)    AS decided_date,
    CAST(assessor            AS STRING)  AS assessor,
    CAST(risk_score          AS DOUBLE)  AS risk_score,
    CAST(is_ntu              AS BOOLEAN) AS is_ntu
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_bronze.claim
WHERE claim_no IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY claim_no
    ORDER BY decided_date DESC NULLS LAST, lodge_date DESC NULLS LAST, event_date DESC
) = 1;
