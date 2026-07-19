-- ============================================================================
-- Silver: email
-- Conformed / typed / deduped passthrough of bronze.email, keyed by email_id.
-- Inbound / outbound claim correspondence.
-- DQ NOTE (DLT-style expectation):
--   EXPECT email_id IS NOT NULL
--   EXPECT claim_no IS NOT NULL
--   EXPECT direction IN ('inbound','outbound')
-- Casts: sent_ts -> TIMESTAMP.
-- Dedup: one row per email_id.
-- ============================================================================
CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_claims_silver.email AS
SELECT
    CAST(email_id    AS STRING)    AS email_id,
    CAST(claim_no    AS STRING)    AS claim_no,
    CAST(direction   AS STRING)    AS direction,
    CAST(subject     AS STRING)    AS subject,
    CAST(body        AS STRING)    AS body,
    CAST(attachments AS STRING)    AS attachments,
    CAST(sent_ts     AS TIMESTAMP) AS sent_ts
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_bronze.email
WHERE email_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY email_id
    ORDER BY sent_ts DESC NULLS LAST
) = 1;
