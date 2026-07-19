-- ============================================================================
-- Metric View: decision_split
-- Pay / decline / refer distribution as percentages. Uses the silver claim
-- spine as source so `decision` is available as both a dimension (to slice)
-- and the basis for the share measures. Dimensions: claim_type, decision,
-- assessor.
-- NOTE: same name as the gold decision_split VIEW but a distinct object in the
-- metric-view layer; deploy after the gold view. If a naming clash is a
-- concern in a given workspace, deploy this as gold.decision_split_metric.
-- ============================================================================
CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_claims_gold.decision_split_metric
WITH METRICS
LANGUAGE YAML
COMMENT 'Decision outcome mix (pay/decline/refer) as counts and percentages.'
AS $$
version: 0.1
source: elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claim
filter: decision IS NOT NULL
dimensions:
  - name: claim_type
    expr: claim_type
  - name: decision
    expr: decision
  - name: assessor
    expr: assessor
measures:
  - name: n_decisions
    expr: COUNT(1)
  - name: n_pay
    expr: COUNT_IF(decision = 'pay')
  - name: n_decline
    expr: COUNT_IF(decision = 'decline')
  - name: n_refer
    expr: COUNT_IF(decision = 'refer')
  - name: pay_pct
    expr: 100.0 * COUNT_IF(decision = 'pay') / NULLIF(COUNT(1), 0)
  - name: decline_pct
    expr: 100.0 * COUNT_IF(decision = 'decline') / NULLIF(COUNT(1), 0)
  - name: refer_pct
    expr: 100.0 * COUNT_IF(decision = 'refer') / NULLIF(COUNT(1), 0)
$$;
