-- ============================================================================
-- Gold: decision_split  (VIEW)
-- Pay / decline / refer mix per claim_type, as counts and as a percentage of
-- all decided claims within that claim_type.
-- Columns: claim_type, decision, n, pct.
-- Only claims with a non-null decision are counted.
-- ============================================================================
CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_claims_gold.decision_split AS
SELECT
    claim_type,
    decision,
    COUNT(*)                                                                 AS n,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY claim_type), 2) AS pct
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claim
WHERE decision IS NOT NULL
GROUP BY claim_type, decision;
