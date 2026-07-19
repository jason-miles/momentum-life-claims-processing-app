-- ============================================================================
-- Silver: life
-- Conformed / typed / deduped passthrough of bronze.life, keyed by life_id.
-- DQ NOTE (DLT-style expectation):
--   EXPECT life_id IS NOT NULL
--   EXPECT policy_no IS NOT NULL
--   EXPECT sensitivity IN ('L1','L2')
-- Casts: dob -> DATE, smoker_flag -> BOOLEAN.
-- Dedup: one row per life_id.
-- ============================================================================
CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_claims_silver.life AS
SELECT
    CAST(life_id                 AS STRING)  AS life_id,
    CAST(policy_no               AS STRING)  AS policy_no,
    CAST(id_number_masked        AS STRING)  AS id_number_masked,
    CAST(dob                     AS DATE)    AS dob,
    CAST(occupation_at_inception AS STRING)  AS occupation_at_inception,
    CAST(smoker_flag             AS BOOLEAN) AS smoker_flag,
    CAST(province                AS STRING)  AS province,
    CAST(sensitivity             AS STRING)  AS sensitivity
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_bronze.life
WHERE life_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY life_id
    ORDER BY policy_no
) = 1;
