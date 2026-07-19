-- Metric Views build. Generated from sql/04_metric_views/*.sql

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
