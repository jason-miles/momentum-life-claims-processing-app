-- ============================================================================
-- Silver: claim_event
-- Conformed / typed / deduped passthrough of bronze.claim_event.
-- Event stream keyed by (claim_no, event).
-- DQ NOTE (DLT-style expectation):
--   EXPECT claim_no IS NOT NULL
--   EXPECT event IN ('initiated','lodged','in_assessment','decided','paid')
--   EXPECT event_ts IS NOT NULL
-- Casts: event_ts -> TIMESTAMP.
-- Dedup: one row per (claim_no, event) keeping the earliest occurrence.
-- ============================================================================
CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claim_event AS
SELECT
    CAST(claim_no AS STRING)    AS claim_no,
    CAST(event    AS STRING)    AS event,
    CAST(event_ts AS TIMESTAMP) AS event_ts
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_bronze.claim_event
WHERE claim_no IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY claim_no, event
    ORDER BY event_ts ASC
) = 1;
