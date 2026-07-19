-- ============================================================================
-- Metric View: avg_days_in_pre_lodge
-- Average days a claim spends in the pre-lodge window (initiate -> lodge),
-- i.e. how long claimants take to formally lodge after first contact. Built on
-- the silver claim spine; only lodged claims contribute (lodge_date NOT NULL).
-- Dimensions: claim_type, event month.
-- ============================================================================
CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_claims_gold.avg_days_in_pre_lodge
WITH METRICS
LANGUAGE YAML
COMMENT 'Average days from event/initiation to lodge (pre-lodge dwell time).'
AS $$
version: 0.1
source: elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claim
filter: lodge_date IS NOT NULL
dimensions:
  - name: claim_type
    expr: claim_type
  - name: event_month
    expr: DATE_TRUNC('MONTH', event_date)
measures:
  - name: avg_days_pre_lodge
    expr: AVG(DATEDIFF(lodge_date, event_date))
  - name: median_days_pre_lodge
    expr: MEDIAN(DATEDIFF(lodge_date, event_date))
  - name: n_lodged_claims
    expr: COUNT(1)
$$;
