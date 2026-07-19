-- ============================================================================
-- Gold: ops_metrics  (VIEW)
-- Per-claim throughput / SLA view built from the claim_event stream.
-- Measures wall-clock days from lodge to decision against a 20-day SLA.
-- Columns: claim_no, claim_type, assessor, lodge_ts, decided_ts,
--          days_lodge_to_decision, sla_days, sla_breach.
-- NOTE: only claims that have both lodged and decided timestamps produce a
-- finite days_lodge_to_decision; still-open claims carry NULL there and a
-- NULL sla_breach.
-- ============================================================================
CREATE OR REPLACE VIEW elexon_app_for_settlement_acc_catalog.momentum_claims_gold.ops_metrics AS
WITH ev AS (
    SELECT
        claim_no,
        MIN(CASE WHEN event = 'lodged'  THEN event_ts END) AS lodge_ts,
        MIN(CASE WHEN event = 'decided' THEN event_ts END) AS decided_ts
    FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claim_event
    GROUP BY claim_no
)
SELECT
    c.claim_no,
    c.claim_type,
    c.assessor,
    ev.lodge_ts,
    ev.decided_ts,
    DATEDIFF(ev.decided_ts, ev.lodge_ts)                        AS days_lodge_to_decision,
    20                                                          AS sla_days,
    CASE
        WHEN ev.lodge_ts IS NULL OR ev.decided_ts IS NULL THEN NULL
        ELSE DATEDIFF(ev.decided_ts, ev.lodge_ts) > 20
    END                                                         AS sla_breach
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claim c
LEFT JOIN ev ON ev.claim_no = c.claim_no;
