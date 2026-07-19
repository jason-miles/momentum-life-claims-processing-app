-- ============================================================================
-- UC Function tool: search_claim_documents(claim_no, query)
-- ----------------------------------------------------------------------------
-- The governed, callable document-retrieval surface for a claim. Returns the
-- claim's documents (doc_id, doc_type, parsed_text) as a JSON array, preferring
-- rows whose parsed_text matches the free-text `query` (ILIKE) but always
-- falling back to the claim's full document set so the agent is never starved
-- of context.
--
-- NOTE: semantic retrieval is served by the Delta Sync vector index
-- momentum_claims_ai.idx_documents (see build_indexes.py). This SQL tool is the
-- governed, permission-checked callable that the Agent Framework can register
-- as a function tool; for the demo it does a lexical match over the same corpus.
--
-- Returns '[]' when the claim has no documents.
-- ============================================================================
CREATE OR REPLACE FUNCTION elexon_app_for_settlement_acc_catalog.momentum_claims_ai.search_claim_documents(
    claim_no STRING COMMENT 'Claim number, e.g. CLM-DISAB-DISCREP',
    query    STRING COMMENT 'Free-text query; matched against parsed_text (ILIKE). Pass empty string to return all docs.'
)
RETURNS STRING
COMMENT 'Returns a claim''s documents (doc_id, doc_type, parsed_text), preferring lexical matches on the query but always returning the claim''s docs, as a JSON array.'
RETURN (
    SELECT COALESCE(
        to_json(
            collect_list(
                struct(
                    d.doc_id,
                    d.doc_type,
                    d.parsed_text,
                    -- surface whether this row actually matched the query text
                    (get_search_query.q = '' OR d.parsed_text ILIKE '%' || get_search_query.q || '%') AS matched_query
                )
            )
        ),
        '[]'
    )
    FROM elexon_app_for_settlement_acc_catalog.momentum_claims_silver.document d
    CROSS JOIN (SELECT COALESCE(search_claim_documents.query, '') AS q) get_search_query
    WHERE d.claim_no = search_claim_documents.claim_no
);
