-- ============================================================================
-- UC Function tool: get_claim_context(claim_no)
-- ----------------------------------------------------------------------------
-- The agent's primary "give me everything about this claim" call. Returns the
-- ONE WIDE ROW from gold.claim_synopsis_view for the requested claim, serialised
-- as a JSON object string. This is the certified structured context (policy,
-- life, benefit, requirement completeness, third-party, decision-support flags)
-- the Synopsis Agent reads instead of swivel-chairing across ten screens.
--
-- Governed callable surface: registered in Unity Catalog, so every invocation is
-- lineage-tracked and permission-checked like any other UC object.
-- Returns NULL-safe JSON: an empty object {} if the claim_no is unknown.
-- ============================================================================
CREATE OR REPLACE FUNCTION elexon_app_for_settlement_acc_catalog.momentum_claims_ai.get_claim_context(
    claim_no STRING COMMENT 'Claim number, e.g. CLM-DISAB-DISCREP'
)
RETURNS STRING
COMMENT 'Returns the wide claim_synopsis_view row for a claim as a JSON object (policy, life, benefit, requirement completeness, third-party summary, decision-support flags).'
RETURN (
    SELECT to_json(struct(v.*))
    FROM elexon_app_for_settlement_acc_catalog.momentum_claims_gold.claim_synopsis_view v
    WHERE v.claim_no = get_claim_context.claim_no
    LIMIT 1
);
