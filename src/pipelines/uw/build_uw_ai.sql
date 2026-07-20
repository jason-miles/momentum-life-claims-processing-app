-- ============================================================================
-- Underwriting AI layer — UC-function agent tools, Vector Search source table,
-- and the semantic retriever. Mirrors the live-deployed build.
--
-- NOTE: the Vector Search INDEX itself (momentum_uw_ai.idx_uw_notes on
-- valterra-vs-endpoint, gte-large-en embeddings over uw_note_chunks) is created
-- imperatively via src/ai/build_uw_index.py — Vector Search indexes are not a
-- first-class DAB/SQL resource. Run that after this file. search_uw_notes below
-- requires the index to be ONLINE.
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS elexon_app_for_settlement_acc_catalog.momentum_uw_ai;

-- Governed agent tools (JSON-returning) --------------------------------------
CREATE OR REPLACE FUNCTION elexon_app_for_settlement_acc_catalog.momentum_uw_ai.get_uw_case(policy STRING)
RETURNS STRING COMMENT 'Unified underwriting case view row as JSON'
RETURN (SELECT to_json(struct(*)) FROM elexon_app_for_settlement_acc_catalog.momentum_uw_gold.uw_case_view WHERE policy_no = policy LIMIT 1);

CREATE OR REPLACE FUNCTION elexon_app_for_settlement_acc_catalog.momentum_uw_ai.list_uw_requirements(policy STRING)
RETURNS STRING COMMENT 'Requirements + status for an underwriting case as JSON'
RETURN (SELECT to_json(collect_list(struct(code, description, status, requested_ts, returned_ts)))
        FROM elexon_app_for_settlement_acc_catalog.momentum_uw_silver.uw_requirement WHERE policy_no = policy);

CREATE OR REPLACE FUNCTION elexon_app_for_settlement_acc_catalog.momentum_uw_ai.get_uw_notes(policy STRING)
RETURNS STRING COMMENT 'Underwriter notepad free text for a case'
RETURN (SELECT to_json(collect_list(struct(author, note_ts, note_text)))
        FROM elexon_app_for_settlement_acc_catalog.momentum_uw_silver.uw_case_note WHERE policy_no = policy);

CREATE OR REPLACE FUNCTION elexon_app_for_settlement_acc_catalog.momentum_uw_ai.ntu_risk_reason(policy STRING)
RETURNS STRING COMMENT 'NTU propensity + drivers for a case as JSON'
RETURN (SELECT to_json(struct(ntu_propensity, reqs_outstanding, days_req_outstanding, sar_band, risk_score, journey_type, is_ntu, ntu_bucket))
        FROM elexon_app_for_settlement_acc_catalog.momentum_uw_gold.uw_case_view WHERE policy_no = policy LIMIT 1);

-- Vector Search source table (CDF enabled for delta-sync index) ---------------
CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_uw_ai.uw_note_chunks
TBLPROPERTIES (delta.enableChangeDataFeed=true) AS
SELECT policy_no AS chunk_id, policy_no, note_text AS chunk_text
FROM elexon_app_for_settlement_acc_catalog.momentum_uw_silver.uw_case_note WHERE note_text IS NOT NULL;

-- Semantic retriever over idx_uw_notes (index must be ONLINE) -----------------
CREATE OR REPLACE FUNCTION elexon_app_for_settlement_acc_catalog.momentum_uw_ai.search_uw_notes(query STRING)
RETURNS TABLE(policy_no STRING, chunk_text STRING, score DOUBLE)
COMMENT 'Semantic search over underwriter notepad text (Vector Search idx_uw_notes), top 5'
RETURN
SELECT policy_no, chunk_text, search_score AS score
FROM vector_search(index => 'elexon_app_for_settlement_acc_catalog.momentum_uw_ai.idx_uw_notes',
                   query_text => query, num_results => 5);
