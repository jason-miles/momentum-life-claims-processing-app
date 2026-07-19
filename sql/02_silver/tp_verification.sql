-- ============================================================================
-- Silver: tp_verification
-- Conformed / typed / deduped passthrough of bronze.tp_verification.
-- Third-party verification results (VPD / other_insurer / bank / identity).
-- Keyed by (claim_no, source).
-- DQ NOTE (DLT-style expectation):
--   EXPECT claim_no IS NOT NULL
--   EXPECT source IN ('VPD','other_insurer','bank','identity')
-- Casts: checked_ts -> TIMESTAMP.
-- Dedup: one row per (claim_no, source) keeping the latest check.
-- ============================================================================
CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_claims_silver.tp_verification AS
SELECT
    CAST(claim_no       AS STRING)    AS claim_no,
    CAST(source         AS STRING)    AS source,
    CAST(result_json    AS STRING)    AS result_json,
    CAST(result_summary AS STRING)    AS result_summary,
    CAST(checked_ts     AS TIMESTAMP) AS checked_ts
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_bronze.tp_verification
WHERE claim_no IS NOT NULL AND source IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY claim_no, source
    ORDER BY checked_ts DESC NULLS LAST
) = 1;
