-- ============================================================================
-- Gold: ntu_at_risk  (VIEW)
-- Pre-lodge claims (state = 'initiated') that have gone quiet for more than
-- 7 days, scored with a drop_off_propensity (0-1) so ops can intervene before
-- the claim is Not Taken Up.
--
-- drop_off_propensity: blends how long the claim has been outstanding with how
-- many requirements are still missing, each normalised and capped to 0-1, then
-- weighted 60% days / 40% outstanding requirements.
--   days factor : LEAST(days_outstanding / 60, 1)
--   reqs factor : LEAST(n_outstanding_reqs / 5, 1)
-- Columns: claim_no, policy_no, claim_type, event_date, days_outstanding,
--          n_outstanding_reqs, drop_off_propensity.
-- ============================================================================
CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_claims_gold.ntu_at_risk AS
WITH outstanding AS (
    SELECT claim_no, COUNT_IF(status = 'outstanding') AS n_outstanding_reqs
    FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.requirement
    GROUP BY claim_no
)
SELECT
    c.claim_no,
    c.policy_no,
    c.claim_type,
    c.event_date,
    DATEDIFF(current_date(), c.event_date)          AS days_outstanding,
    COALESCE(o.n_outstanding_reqs, 0)               AS n_outstanding_reqs,
    ROUND(
        0.6 * LEAST(DATEDIFF(current_date(), c.event_date) / 60.0, 1.0)
      + 0.4 * LEAST(COALESCE(o.n_outstanding_reqs, 0) / 5.0, 1.0)
    , 3)                                            AS drop_off_propensity
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claim c
LEFT JOIN outstanding o ON o.claim_no = c.claim_no
WHERE c.state = 'initiated'
  AND c.event_date < current_date() - INTERVAL 7 DAYS;
