-- ============================================================================
-- Metric View: ntu_rate
-- Pre-lodge drop-off rate = NTU claims / initiated claims. Computed as the
-- ratio of two measures over the silver claim spine, restricted to the
-- pre-lodge ('initiated') population that can actually drop off.
-- Dimensions: claim_type, event month.
-- ============================================================================
CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_claims_gold.ntu_rate
WITH METRICS
LANGUAGE YAML
COMMENT 'Not-Taken-Up rate: NTU claims as a share of pre-lodge (initiated) claims.'
AS $$
version: 0.1
source: elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claim
filter: state = 'initiated'
dimensions:
  - name: claim_type
    expr: claim_type
  - name: event_month
    expr: DATE_TRUNC('MONTH', event_date)
measures:
  - name: n_initiated
    expr: COUNT(1)
  - name: n_ntu
    expr: COUNT_IF(is_ntu)
  - name: ntu_rate
    expr: COUNT_IF(is_ntu) / NULLIF(COUNT(1), 0)
$$;
