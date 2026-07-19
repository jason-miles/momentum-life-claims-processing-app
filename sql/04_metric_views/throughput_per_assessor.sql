-- ============================================================================
-- Metric View: throughput_per_assessor
-- Claims decided per assessor per period. Built on the silver claim spine,
-- restricted to claims that reached a decision. Slice by assessor and by the
-- month the decision was made to get decided-claims-per-assessor-per-month.
-- ============================================================================
CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_claims_gold.throughput_per_assessor
WITH METRICS
LANGUAGE YAML
COMMENT 'Claims decided per assessor per period (throughput).'
AS $$
version: 0.1
source: elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claim
filter: decided_date IS NOT NULL
dimensions:
  - name: assessor
    expr: assessor
  - name: claim_type
    expr: claim_type
  - name: decided_month
    expr: DATE_TRUNC('MONTH', decided_date)
measures:
  - name: n_decided
    expr: COUNT(1)
  - name: n_paid
    expr: COUNT_IF(decision = 'pay')
$$;
