-- ============================================================================
-- Underwriting GOLD — certified serving views. Mirrors the live-deployed build.
-- uw_case_view is the unified case view (R2.1), keyed on policy_no, joining
-- AS400-style application/life + requirements + decision + BPM task + NTU, with
-- a computed NTU propensity (features: days outstanding, outstanding reqs,
-- risk score, sum-at-risk band).
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS elexon_app_for_settlement_acc_catalog.momentum_uw_gold;

CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_uw_gold.uw_case_view AS
WITH req AS (
  SELECT policy_no, COUNT(*) reqs_total, COUNT_IF(status='returned') reqs_returned,
         COUNT_IF(status='outstanding') reqs_outstanding,
         CONCAT_WS(', ', COLLECT_LIST(CASE WHEN status='outstanding' THEN code END)) outstanding_codes,
         MIN(CASE WHEN status='outstanding' THEN requested_ts END) oldest_outstanding_req
  FROM elexon_app_for_settlement_acc_catalog.momentum_uw_silver.uw_requirement GROUP BY policy_no),
dec AS (
  SELECT policy_no, outcome decision_outcome, decided_ts, loading_pct, exclusion, counteroffer_accepted
  FROM elexon_app_for_settlement_acc_catalog.momentum_uw_silver.uw_decision
  QUALIFY ROW_NUMBER() OVER (PARTITION BY policy_no ORDER BY decided_ts DESC)=1),
tsk AS (
  SELECT policy_no, status task_status, cycle_days, sla_days, sla_breach, opened_ts, closed_ts
  FROM elexon_app_for_settlement_acc_catalog.momentum_uw_silver.bpm_task),
n AS (SELECT policy_no, ntu_bucket, days_in_diary FROM elexon_app_for_settlement_acc_catalog.momentum_uw_silver.ntu)
SELECT a.policy_no, a.submitted_date, a.channel, a.broker, a.benefit_type, a.sum_at_risk, a.sar_band,
       a.province, a.journey_type, a.underwriter,
       l.age, l.smoker_flag, l.occupation_class, l.risk_score, l.id_number_masked,
       COALESCE(r.reqs_total,0) reqs_total, COALESCE(r.reqs_returned,0) reqs_returned,
       COALESCE(r.reqs_outstanding,0) reqs_outstanding, r.outstanding_codes, r.oldest_outstanding_req,
       d.decision_outcome, d.decided_ts, d.loading_pct, d.exclusion, d.counteroffer_accepted,
       t.task_status, t.cycle_days, t.sla_days, t.sla_breach, t.opened_ts, t.closed_ts,
       (n.policy_no IS NOT NULL) is_ntu, n.ntu_bucket, n.days_in_diary,
       DATEDIFF(current_date(), r.oldest_outstanding_req) days_req_outstanding,
       ROUND(LEAST(1.0,
         0.45*LEAST(COALESCE(DATEDIFF(current_date(), r.oldest_outstanding_req),0)/30.0,1.0)
       + 0.30*LEAST(COALESCE(r.reqs_outstanding,0)/3.0,1.0)
       + 0.15*l.risk_score
       + 0.10*(CASE WHEN a.sar_band IN ('R3m-10m','>R10m') THEN 1 ELSE 0 END)),3) ntu_propensity
FROM elexon_app_for_settlement_acc_catalog.momentum_uw_silver.application a
LEFT JOIN elexon_app_for_settlement_acc_catalog.momentum_uw_silver.uw_life l ON l.policy_no=a.policy_no
LEFT JOIN req r ON r.policy_no=a.policy_no
LEFT JOIN dec d ON d.policy_no=a.policy_no
LEFT JOIN tsk t ON t.policy_no=a.policy_no
LEFT JOIN n ON n.policy_no=a.policy_no;

CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_uw_gold.uw_journey_split AS
SELECT journey_type, COUNT(*) n, ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER (),1) pct
FROM elexon_app_for_settlement_acc_catalog.momentum_uw_silver.application GROUP BY journey_type;

CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_uw_gold.uw_decision_split AS
SELECT outcome, COUNT(*) n, ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER (),1) pct,
       COUNT_IF(loading_pct IS NOT NULL) n_loadings, COUNT_IF(exclusion IS NOT NULL) n_exclusions
FROM elexon_app_for_settlement_acc_catalog.momentum_uw_silver.uw_decision GROUP BY outcome;

CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_uw_gold.uw_requirement_analytics AS
SELECT code, MAX(description) description, COUNT(*) n_requested,
       COUNT_IF(status='returned') n_returned, COUNT_IF(status='outstanding') n_outstanding,
       ROUND(100.0*COUNT_IF(status='returned')/COUNT(*),1) pct_returned,
       ROUND(AVG(CASE WHEN status='returned' THEN DATEDIFF(returned_ts,requested_ts) END),1) avg_days_to_return
FROM elexon_app_for_settlement_acc_catalog.momentum_uw_silver.uw_requirement GROUP BY code;

CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_uw_gold.uw_ntu_funnel AS
SELECT ntu_bucket, COUNT(*) n, ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER (),1) pct,
       ROUND(SUM(sum_at_risk),0) total_sar
FROM elexon_app_for_settlement_acc_catalog.momentum_uw_silver.ntu GROUP BY ntu_bucket;

CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_uw_gold.uw_ntu_at_risk AS
SELECT policy_no, benefit_type, sar_band, sum_at_risk, journey_type, underwriter,
       reqs_outstanding, days_req_outstanding, ntu_propensity
FROM elexon_app_for_settlement_acc_catalog.momentum_uw_gold.uw_case_view
WHERE task_status='open' AND reqs_outstanding>0 AND days_req_outstanding>=7
ORDER BY ntu_propensity DESC, sum_at_risk DESC;

CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_uw_gold.uw_ops_metrics AS
SELECT underwriter, COUNT(*) n_cases, COUNT_IF(sla_breach) n_breach,
       ROUND(AVG(cycle_days),1) avg_cycle_days, COUNT_IF(task_status='closed') n_closed
FROM elexon_app_for_settlement_acc_catalog.momentum_uw_gold.uw_case_view GROUP BY underwriter;
