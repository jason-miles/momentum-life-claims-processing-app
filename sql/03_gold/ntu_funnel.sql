-- ============================================================================
-- Gold: ntu_funnel  (VIEW)
-- Claim drop-off funnel: counts of claims and NTU ("Not Taken Up") claims by
-- stage (state) and claim_type. Feeds the pre-lodge leakage narrative.
-- Columns: claim_type, state, n_claims, n_ntu.
-- ============================================================================
CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_claims_gold.ntu_funnel AS
SELECT
    claim_type,
    state,
    COUNT(*)              AS n_claims,
    COUNT_IF(is_ntu)      AS n_ntu
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claim
GROUP BY claim_type, state;
