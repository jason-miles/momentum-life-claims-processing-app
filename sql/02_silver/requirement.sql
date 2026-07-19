-- ============================================================================
-- Silver: requirement
-- Conformed / typed / deduped passthrough of bronze.requirement.
-- Keyed by (claim_no, code).
-- DQ NOTE (DLT-style expectation):
--   EXPECT claim_no IS NOT NULL
--   EXPECT code IS NOT NULL
--   EXPECT status IN ('received','outstanding')
--   EXPECT (status = 'received' AND received_ts IS NOT NULL)
--       OR (status = 'outstanding' AND received_ts IS NULL)
-- Casts: requested_ts/received_ts -> TIMESTAMP.
-- Dedup: one row per (claim_no, code) keeping the most recently received.
-- ============================================================================
CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_claims_silver.requirement AS
SELECT
    CAST(claim_no     AS STRING)    AS claim_no,
    CAST(code         AS STRING)    AS code,
    CAST(description  AS STRING)    AS description,
    CAST(status       AS STRING)    AS status,
    CAST(requested_ts AS TIMESTAMP) AS requested_ts,
    CAST(received_ts  AS TIMESTAMP) AS received_ts
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_bronze.requirement
WHERE claim_no IS NOT NULL AND code IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY claim_no, code
    ORDER BY received_ts DESC NULLS LAST, requested_ts DESC NULLS LAST
) = 1;
