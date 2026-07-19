-- ============================================================================
-- Silver: policy
-- Conformed / typed / deduped passthrough of bronze.policy, keyed by policy_no.
-- DQ NOTE (DLT-style expectation, enforced here by design, not DLT):
--   EXPECT policy_no IS NOT NULL
--   EXPECT status IN ('in_force','lapsed','paid_up')
--   EXPECT inception_date >= signed_date
-- Dedup: one row per policy_no (latest by inception_date, then signed_date).
-- ============================================================================
CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_claims_silver.policy AS
SELECT
    CAST(policy_no          AS STRING) AS policy_no,
    CAST(signed_date        AS DATE)   AS signed_date,
    CAST(inception_date     AS DATE)   AS inception_date,
    CAST(broker             AS STRING) AS broker,
    CAST(status             AS STRING) AS status,
    CAST(insurable_interest AS STRING) AS insurable_interest
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_bronze.policy
WHERE policy_no IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY policy_no
    ORDER BY inception_date DESC, signed_date DESC
) = 1;
