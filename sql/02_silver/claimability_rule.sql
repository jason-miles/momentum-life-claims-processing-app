-- ============================================================================
-- Silver: claimability_rule
-- Conformed / typed / deduped passthrough of bronze.claimability_rule.
-- Externalised claimability rulebook, keyed by rule_id.
-- DQ NOTE (DLT-style expectation):
--   EXPECT rule_id IS NOT NULL
--   EXPECT severity IN ('hard','soft')
--   EXPECT claim_type IN ('death','disability','critical_illness','income','all')
-- Dedup: one row per rule_id.
-- ============================================================================
CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claimability_rule AS
SELECT
    CAST(rule_id     AS STRING) AS rule_id,
    CAST(claim_type  AS STRING) AS claim_type,
    CAST(rule_key    AS STRING) AS rule_key,
    CAST(description AS STRING) AS description,
    CAST(severity    AS STRING) AS severity
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_bronze.claimability_rule
WHERE rule_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY rule_id
    ORDER BY rule_key
) = 1;
