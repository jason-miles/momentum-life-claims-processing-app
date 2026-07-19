-- ============================================================================
-- UC Function tool: get_third_party_verifications(claim_no)
-- ----------------------------------------------------------------------------
-- Returns the third-party verification results for a claim (VPD, other_insurer,
-- bank, identity) as a JSON array of {source, result_summary, checked_ts}.
-- Lets the agent corroborate the claim against external checks -- e.g. DS3's
-- "2 prior claims at other insurers", a classic fraud signal.
--
-- Returns '[]' when the claim has no third-party checks.
-- ============================================================================
CREATE OR REPLACE FUNCTION elexon_app_for_settlement_acc_catalog.momentum_claims_ai.get_third_party_verifications(
    claim_no STRING COMMENT 'Claim number, e.g. CLM-SUSPECT-FRAUD'
)
RETURNS STRING
COMMENT 'Returns third-party verification summaries (VPD / other_insurer / bank / identity) for a claim as a JSON array.'
RETURN (
    SELECT COALESCE(
        to_json(
            collect_list(
                struct(
                    tp.source,
                    tp.result_summary,
                    tp.checked_ts
                )
            )
        ),
        '[]'
    )
    FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.tp_verification tp
    WHERE tp.claim_no = get_third_party_verifications.claim_no
);
