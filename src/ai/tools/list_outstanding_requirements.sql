-- ============================================================================
-- UC Function tool: list_outstanding_requirements(claim_no)
-- ----------------------------------------------------------------------------
-- Returns the requirement checklist for a claim split into received vs
-- outstanding, plus counts, as a JSON object:
--   { claim_no, reqs_total, reqs_received, reqs_outstanding,
--     outstanding: [{code, description}], received: [{code, description}] }
--
-- Drives the "REQUEST INFO" recommendation path and the outstanding-requirement
-- discrepancy flag (e.g. DS2's missing specialist medical report).
-- ============================================================================
CREATE OR REPLACE FUNCTION elexon_app_for_settlement_acc_catalog.momentum_claims_ai.list_outstanding_requirements(
    claim_no STRING COMMENT 'Claim number, e.g. CLM-DISAB-DISCREP'
)
RETURNS STRING
COMMENT 'Returns received vs outstanding requirements for a claim, with counts, as a JSON object.'
RETURN (
    SELECT to_json(
        struct(
            list_outstanding_requirements.claim_no AS claim_no,
            COUNT(*)                                                 AS reqs_total,
            COUNT_IF(r.status = 'received')                          AS reqs_received,
            COUNT_IF(r.status = 'outstanding')                       AS reqs_outstanding,
            collect_list(CASE WHEN r.status = 'outstanding'
                              THEN struct(r.code, r.description) END) AS outstanding,
            collect_list(CASE WHEN r.status = 'received'
                              THEN struct(r.code, r.description) END) AS received
        )
    )
    FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.requirement r
    WHERE r.claim_no = list_outstanding_requirements.claim_no
);
