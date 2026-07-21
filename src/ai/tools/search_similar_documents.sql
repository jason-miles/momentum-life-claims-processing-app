-- Claims semantic retriever over the idx_documents Vector Search index.
-- Added alongside the lexical search_claim_documents tool so the claims synopsis
-- can cite semantically-similar prior claims (RAG symmetry with underwriting).
-- Requires momentum_claims_ai.idx_documents to be ONLINE.
CREATE OR REPLACE FUNCTION elexon_app_for_settlement_acc_catalog.momentum_claims_ai.search_similar_documents(query STRING)
RETURNS TABLE(claim_no STRING, doc_type STRING, chunk_text STRING, score DOUBLE)
COMMENT 'Semantic search over claim documents (Vector Search idx_documents), top 5'
RETURN
SELECT claim_no, doc_type, chunk_text, search_score AS score
FROM vector_search(index => 'elexon_app_for_settlement_acc_catalog.momentum_claims_ai.idx_documents',
                   query_text => query, num_results => 5);
