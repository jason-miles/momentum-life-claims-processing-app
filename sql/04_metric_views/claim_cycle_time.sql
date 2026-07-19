-- ============================================================================
-- Metric View: claim_cycle_time
-- Average wall-clock days from lodge to decision. Built on the gold
-- ops_metrics view (which already resolves lodge_ts / decided_ts from the
-- event stream). Dimensions let you slice cycle time by claim_type and assessor.
-- ============================================================================
CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_claims_gold.claim_cycle_time
WITH METRICS
LANGUAGE YAML
COMMENT 'Average lodge-to-decision cycle time (days) per claim_type / assessor.'
AS $$
version: 0.1
source: elexon_app_for_settlement_acc_catalog.momentum_claims_gold.ops_metrics
dimensions:
  - name: claim_type
    expr: claim_type
  - name: assessor
    expr: assessor
measures:
  - name: avg_cycle_days
    expr: AVG(days_lodge_to_decision)
  - name: median_cycle_days
    expr: MEDIAN(days_lodge_to_decision)
  - name: n_decided_claims
    expr: COUNT(days_lodge_to_decision)
$$;
