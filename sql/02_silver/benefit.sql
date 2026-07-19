-- ============================================================================
-- Silver: benefit
-- Conformed / typed / deduped passthrough of bronze.benefit, keyed by benefit_id.
-- DQ NOTE (DLT-style expectation):
--   EXPECT benefit_id IS NOT NULL
--   EXPECT sum_assured >= 0
--   EXPECT status IN ('in_force','lapsed','excluded')
-- Casts: sum_assured -> DECIMAL(12,2).
-- Dedup: one row per benefit_id.
-- ============================================================================
CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_claims_silver.benefit AS
SELECT
    CAST(benefit_id   AS STRING)        AS benefit_id,
    CAST(policy_no    AS STRING)        AS policy_no,
    CAST(benefit_type AS STRING)        AS benefit_type,
    CAST(sum_assured  AS DECIMAL(12,2)) AS sum_assured,
    CAST(status       AS STRING)        AS status,
    CAST(loadings     AS STRING)        AS loadings,
    CAST(exclusions   AS STRING)        AS exclusions
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_bronze.benefit
WHERE benefit_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY benefit_id
    ORDER BY policy_no
) = 1;
