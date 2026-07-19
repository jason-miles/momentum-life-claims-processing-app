-- ============================================================================
-- Silver: role_player
-- Conformed / typed / deduped passthrough of bronze.role_player.
-- The bronze table has no natural single-column key, so we dedup on the full
-- business grain (policy_no, role, relationship, name).
-- DQ NOTE (DLT-style expectation):
--   EXPECT policy_no IS NOT NULL
--   EXPECT role IN ('policyholder','payer','beneficiary')
-- ============================================================================
CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_claims_silver.role_player AS
SELECT
    CAST(policy_no    AS STRING) AS policy_no,
    CAST(role         AS STRING) AS role,
    CAST(relationship AS STRING) AS relationship,
    CAST(name         AS STRING) AS name
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_bronze.role_player
WHERE policy_no IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY policy_no, role, relationship, name
    ORDER BY policy_no
) = 1;
