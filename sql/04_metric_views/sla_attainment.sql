-- ============================================================================
-- Metric View: sla_attainment
-- Percentage of decided claims that reached a decision within the 20-day SLA.
-- Built on gold ops_metrics (which carries days_lodge_to_decision, sla_days
-- and the sla_breach flag). Dimensions: claim_type, assessor.
-- ============================================================================
CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_claims_gold.sla_attainment
WITH METRICS
LANGUAGE YAML
COMMENT 'Share of decided claims within the 20-day lodge-to-decision SLA.'
AS $$
version: 0.1
source: elexon_app_for_settlement_acc_catalog.momentum_claims_gold.ops_metrics
filter: sla_breach IS NOT NULL
dimensions:
  - name: claim_type
    expr: claim_type
  - name: assessor
    expr: assessor
measures:
  - name: n_decided_claims
    expr: COUNT(1)
  - name: n_within_sla
    expr: COUNT_IF(sla_breach = false)
  - name: sla_attainment_pct
    expr: 100.0 * COUNT_IF(sla_breach = false) / NULLIF(COUNT(1), 0)
$$;
