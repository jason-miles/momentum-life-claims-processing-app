-- ============================================================================
-- Silver: document
-- Conformed / typed / deduped passthrough of bronze.document, keyed by doc_id.
-- Holds parsed OCR text + extracted JSON for downstream AI / RAG use.
-- DQ NOTE (DLT-style expectation):
--   EXPECT doc_id IS NOT NULL
--   EXPECT claim_no IS NOT NULL
-- Dedup: one row per doc_id.
-- ============================================================================
CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_claims_silver.document AS
SELECT
    CAST(doc_id         AS STRING) AS doc_id,
    CAST(claim_no       AS STRING) AS claim_no,
    CAST(doc_type       AS STRING) AS doc_type,
    CAST(filenet_ref    AS STRING) AS filenet_ref,
    CAST(parsed_text    AS STRING) AS parsed_text,
    CAST(extracted_json AS STRING) AS extracted_json
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_bronze.document
WHERE doc_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY doc_id
    ORDER BY claim_no
) = 1;
