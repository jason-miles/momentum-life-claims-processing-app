-- ============================================================================
-- Underwriting UC Metric Views. Query with MEASURE(<measure>).
-- ============================================================================
CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_uw_gold.uw_stp_rate
WITH METRICS LANGUAGE YAML
COMMENT 'Straight-through-processing rate: fast-track + tele as share of all applications.'
AS $$
version: 0.1
source: elexon_app_for_settlement_acc_catalog.momentum_uw_silver.application
dimensions:
  - name: benefit_type
    expr: benefit_type
  - name: channel
    expr: channel
measures:
  - name: stp_rate
    expr: COUNT_IF(journey_type IN ('fast_track','tele_underwriting')) / NULLIF(COUNT(1),0)
  - name: n_applications
    expr: COUNT(1)
$$;

CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_uw_gold.uw_turnaround
WITH METRICS LANGUAGE YAML
COMMENT 'Average underwriting cycle time (days, open to close).'
AS $$
version: 0.1
source: elexon_app_for_settlement_acc_catalog.momentum_uw_gold.uw_case_view
dimensions:
  - name: journey_type
    expr: journey_type
  - name: underwriter
    expr: underwriter
measures:
  - name: avg_cycle_days
    expr: AVG(cycle_days)
  - name: sla_breach_rate
    expr: COUNT_IF(sla_breach) / NULLIF(COUNT(1),0)
$$;

CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_uw_gold.uw_ntu_rate
WITH METRICS LANGUAGE YAML
COMMENT 'Not-Taken-Up rate: NTU cases as a share of all applications.'
AS $$
version: 0.1
source: elexon_app_for_settlement_acc_catalog.momentum_uw_gold.uw_case_view
dimensions:
  - name: journey_type
    expr: journey_type
  - name: sar_band
    expr: sar_band
measures:
  - name: ntu_rate
    expr: COUNT_IF(is_ntu) / NULLIF(COUNT(1),0)
  - name: n_applications
    expr: COUNT(1)
$$;
