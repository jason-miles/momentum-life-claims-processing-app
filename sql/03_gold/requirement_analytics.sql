-- ============================================================================
-- Gold: requirement_analytics  (VIEW)
-- Requirement completion patterns per claim_type and requirement code: how
-- often each requirement is received vs still outstanding, and how long it
-- takes to arrive once requested. Surfaces the chronic bottleneck documents.
-- Columns: claim_type, code, description, n_total, n_received, n_outstanding,
--          pct_received, avg_days_to_receive.
-- avg_days_to_receive measured over received requirements only
-- (received_ts - requested_ts).
-- ============================================================================
CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_claims_gold.requirement_analytics AS
SELECT
    c.claim_type,
    r.code,
    MAX(r.description)                                                  AS description,
    COUNT(*)                                                            AS n_total,
    COUNT_IF(r.status = 'received')                                     AS n_received,
    COUNT_IF(r.status = 'outstanding')                                  AS n_outstanding,
    ROUND(100.0 * COUNT_IF(r.status = 'received') / COUNT(*), 2)        AS pct_received,
    ROUND(AVG(CASE WHEN r.status = 'received'
                   THEN DATEDIFF(r.received_ts, r.requested_ts) END), 2) AS avg_days_to_receive
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.requirement r
JOIN elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claim c
  ON c.claim_no = r.claim_no
GROUP BY c.claim_type, r.code;
