-- ============================================================================
-- Smoke verify — post-rebuild health check across BOTH domains.
-- Run after momentum_claims_build + momentum_uw_build. Every row should show
-- sensible non-zero counts and the seeded scenarios should resolve.
-- ============================================================================

-- Row counts (claims)
SELECT 'claims.claim'         AS obj, COUNT(*) n FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claim
UNION ALL SELECT 'claims.synopsis_view', COUNT(*) FROM elexon_app_for_settlement_acc_catalog.momentum_claims_gold.claim_synopsis_view
UNION ALL SELECT 'uw.application',        COUNT(*) FROM elexon_app_for_settlement_acc_catalog.momentum_uw_silver.application
UNION ALL SELECT 'uw.case_view',          COUNT(*) FROM elexon_app_for_settlement_acc_catalog.momentum_uw_gold.uw_case_view
ORDER BY obj;

-- Seeded claims scenarios resolve with planted signals
SELECT claim_no, occupation_mismatch, early_claim_flag, benefit_status
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_gold.claim_synopsis_view
WHERE claim_no IN ('CLM-DEATH-CLEAN','CLM-DISAB-DISCREP','CLM-SUSPECT-FRAUD') ORDER BY claim_no;

-- Seeded UW scenarios resolve (UW-NTU-RISK should be ~0.907 propensity)
SELECT policy_no, journey_type, decision_outcome, reqs_outstanding, ntu_propensity
FROM elexon_app_for_settlement_acc_catalog.momentum_uw_gold.uw_case_view
WHERE policy_no IN ('UW-CLEAN-FASTTRACK','UW-COUNTEROFFER','UW-NTU-RISK') ORDER BY policy_no;

-- Metric views resolve (claims + underwriting)
SELECT 'claims.ntu_rate' m, ROUND(MEASURE(ntu_rate),3) v FROM elexon_app_for_settlement_acc_catalog.momentum_claims_gold.ntu_rate
UNION ALL SELECT 'uw.stp_rate', ROUND(MEASURE(stp_rate),3) FROM elexon_app_for_settlement_acc_catalog.momentum_uw_gold.uw_stp_rate
UNION ALL SELECT 'uw.ntu_rate', ROUND(MEASURE(ntu_rate),3) FROM elexon_app_for_settlement_acc_catalog.momentum_uw_gold.uw_ntu_rate;

-- UW NTU funnel should match the spec buckets (~62/19/12/7)
SELECT ntu_bucket, pct FROM elexon_app_for_settlement_acc_catalog.momentum_uw_gold.uw_ntu_funnel ORDER BY n DESC;
