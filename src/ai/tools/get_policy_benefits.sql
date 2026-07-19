-- ============================================================================
-- UC Function tool: get_policy_benefits(policy_no)
-- ----------------------------------------------------------------------------
-- Returns every benefit line on a policy with its status, sum assured and any
-- loadings/exclusions, as a JSON array of objects. Lets the agent reason about
-- the full cover on a policy (not just the one benefit matching the claim), e.g.
-- to spot a lapsed benefit or an exclusion that bears on claimability.
--
-- Returns '[]' when the policy has no benefits / is unknown.
-- ============================================================================
CREATE OR REPLACE FUNCTION elexon_app_for_settlement_acc_catalog.momentum_claims_ai.get_policy_benefits(
    policy_no STRING COMMENT 'Policy number, e.g. POL-DISAB-DISCREP'
)
RETURNS STRING
COMMENT 'Returns all benefits on a policy (benefit_type, sum_assured, status, loadings, exclusions) as a JSON array.'
RETURN (
    SELECT COALESCE(
        to_json(
            collect_list(
                struct(
                    b.benefit_id,
                    b.benefit_type,
                    b.sum_assured,
                    b.status AS benefit_status,
                    b.loadings,
                    b.exclusions
                )
            )
        ),
        '[]'
    )
    FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.benefit b
    WHERE b.policy_no = get_policy_benefits.policy_no
);
