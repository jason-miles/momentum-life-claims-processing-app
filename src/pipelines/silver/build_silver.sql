-- Silver build: conform bronze -> silver (typed, deduped). Generated from sql/02_silver/*.sql
CREATE SCHEMA IF NOT EXISTS elexon_app_for_settlement_acc_catalog.momentum_claims_silver;

-- ============================================================================
-- Silver: benefit
-- Conformed / typed / deduped passthrough of bronze.benefit, keyed by benefit_id.
-- DQ NOTE (DLT-style expectation):
--   EXPECT benefit_id IS NOT NULL
--   EXPECT sum_assured >= 0
--   EXPECT status IN ('in_force','lapsed','excluded')
-- Casts: sum_assured -> DECIMAL(12,2).
-- Dedup: one row per benefit_id.
-- ============================================================================
CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_claims_silver.benefit AS
SELECT
    CAST(benefit_id   AS STRING)        AS benefit_id,
    CAST(policy_no    AS STRING)        AS policy_no,
    CAST(benefit_type AS STRING)        AS benefit_type,
    CAST(sum_assured  AS DECIMAL(12,2)) AS sum_assured,
    CAST(status       AS STRING)        AS status,
    CAST(loadings     AS STRING)        AS loadings,
    CAST(exclusions   AS STRING)        AS exclusions
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_bronze.benefit
WHERE benefit_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY benefit_id
    ORDER BY policy_no
) = 1;

-- ============================================================================
-- Silver: claim
-- Conformed / typed / deduped passthrough of bronze.claim, keyed by claim_no.
-- This is the spine of the claims domain.
-- DQ NOTE (DLT-style expectation):
--   EXPECT claim_no IS NOT NULL
--   EXPECT claim_type IN ('death','disability','critical_illness','income')
--   EXPECT state IN ('initiated','lodged','in_assessment','decided','paid')
--   EXPECT decision IN ('pay','decline','refer') OR decision IS NULL
--   EXPECT event_date IS NOT NULL
-- Casts: event_date/lodge_date/decided_date -> DATE, risk_score -> DOUBLE,
--        is_ntu -> BOOLEAN.
-- Dedup: one row per claim_no (keep the most recently decided / lodged record).
-- ============================================================================
CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claim AS
SELECT
    CAST(claim_no            AS STRING)  AS claim_no,
    CAST(policy_no           AS STRING)  AS policy_no,
    CAST(claim_type          AS STRING)  AS claim_type,
    CAST(event_date          AS DATE)    AS event_date,
    CAST(lodge_date          AS DATE)    AS lodge_date,
    CAST(state               AS STRING)  AS state,
    CAST(occupation_at_claim AS STRING)  AS occupation_at_claim,
    CAST(decision            AS STRING)  AS decision,
    CAST(decided_date        AS DATE)    AS decided_date,
    CAST(assessor            AS STRING)  AS assessor,
    CAST(risk_score          AS DOUBLE)  AS risk_score,
    CAST(is_ntu              AS BOOLEAN) AS is_ntu
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_bronze.claim
WHERE claim_no IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY claim_no
    ORDER BY decided_date DESC NULLS LAST, lodge_date DESC NULLS LAST, event_date DESC
) = 1;

-- ============================================================================
-- Silver: claim_event
-- Conformed / typed / deduped passthrough of bronze.claim_event.
-- Event stream keyed by (claim_no, event).
-- DQ NOTE (DLT-style expectation):
--   EXPECT claim_no IS NOT NULL
--   EXPECT event IN ('initiated','lodged','in_assessment','decided','paid')
--   EXPECT event_ts IS NOT NULL
-- Casts: event_ts -> TIMESTAMP.
-- Dedup: one row per (claim_no, event) keeping the earliest occurrence.
-- ============================================================================
CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claim_event AS
SELECT
    CAST(claim_no AS STRING)    AS claim_no,
    CAST(event    AS STRING)    AS event,
    CAST(event_ts AS TIMESTAMP) AS event_ts
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_bronze.claim_event
WHERE claim_no IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY claim_no, event
    ORDER BY event_ts ASC
) = 1;

-- ============================================================================
-- Silver: claimability_rule
-- Conformed / typed / deduped passthrough of bronze.claimability_rule.
-- Externalised claimability rulebook, keyed by rule_id.
-- DQ NOTE (DLT-style expectation):
--   EXPECT rule_id IS NOT NULL
--   EXPECT severity IN ('hard','soft')
--   EXPECT claim_type IN ('death','disability','critical_illness','income','all')
-- Dedup: one row per rule_id.
-- ============================================================================
CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_claims_silver.claimability_rule AS
SELECT
    CAST(rule_id     AS STRING) AS rule_id,
    CAST(claim_type  AS STRING) AS claim_type,
    CAST(rule_key    AS STRING) AS rule_key,
    CAST(description AS STRING) AS description,
    CAST(severity    AS STRING) AS severity
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_bronze.claimability_rule
WHERE rule_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY rule_id
    ORDER BY rule_key
) = 1;

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

-- ============================================================================
-- Silver: email
-- Conformed / typed / deduped passthrough of bronze.email, keyed by email_id.
-- Inbound / outbound claim correspondence.
-- DQ NOTE (DLT-style expectation):
--   EXPECT email_id IS NOT NULL
--   EXPECT claim_no IS NOT NULL
--   EXPECT direction IN ('inbound','outbound')
-- Casts: sent_ts -> TIMESTAMP.
-- Dedup: one row per email_id.
-- ============================================================================
CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_claims_silver.email AS
SELECT
    CAST(email_id    AS STRING)    AS email_id,
    CAST(claim_no    AS STRING)    AS claim_no,
    CAST(direction   AS STRING)    AS direction,
    CAST(subject     AS STRING)    AS subject,
    CAST(body        AS STRING)    AS body,
    CAST(attachments AS STRING)    AS attachments,
    CAST(sent_ts     AS TIMESTAMP) AS sent_ts
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_bronze.email
WHERE email_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY email_id
    ORDER BY sent_ts DESC NULLS LAST
) = 1;

-- ============================================================================
-- Silver: life
-- Conformed / typed / deduped passthrough of bronze.life, keyed by life_id.
-- DQ NOTE (DLT-style expectation):
--   EXPECT life_id IS NOT NULL
--   EXPECT policy_no IS NOT NULL
--   EXPECT sensitivity IN ('L1','L2')
-- Casts: dob -> DATE, smoker_flag -> BOOLEAN.
-- Dedup: one row per life_id.
-- ============================================================================
CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_claims_silver.life AS
SELECT
    CAST(life_id                 AS STRING)  AS life_id,
    CAST(policy_no               AS STRING)  AS policy_no,
    CAST(id_number_masked        AS STRING)  AS id_number_masked,
    CAST(dob                     AS DATE)    AS dob,
    CAST(occupation_at_inception AS STRING)  AS occupation_at_inception,
    CAST(smoker_flag             AS BOOLEAN) AS smoker_flag,
    CAST(province                AS STRING)  AS province,
    CAST(sensitivity             AS STRING)  AS sensitivity
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_bronze.life
WHERE life_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY life_id
    ORDER BY policy_no
) = 1;

-- ============================================================================
-- Silver: policy
-- Conformed / typed / deduped passthrough of bronze.policy, keyed by policy_no.
-- DQ NOTE (DLT-style expectation, enforced here by design, not DLT):
--   EXPECT policy_no IS NOT NULL
--   EXPECT status IN ('in_force','lapsed','paid_up')
--   EXPECT inception_date >= signed_date
-- Dedup: one row per policy_no (latest by inception_date, then signed_date).
-- ============================================================================
CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_claims_silver.policy AS
SELECT
    CAST(policy_no          AS STRING) AS policy_no,
    CAST(signed_date        AS DATE)   AS signed_date,
    CAST(inception_date     AS DATE)   AS inception_date,
    CAST(broker             AS STRING) AS broker,
    CAST(status             AS STRING) AS status,
    CAST(insurable_interest AS STRING) AS insurable_interest
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_bronze.policy
WHERE policy_no IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY policy_no
    ORDER BY inception_date DESC, signed_date DESC
) = 1;

-- ============================================================================
-- Silver: requirement
-- Conformed / typed / deduped passthrough of bronze.requirement.
-- Keyed by (claim_no, code).
-- DQ NOTE (DLT-style expectation):
--   EXPECT claim_no IS NOT NULL
--   EXPECT code IS NOT NULL
--   EXPECT status IN ('received','outstanding')
--   EXPECT (status = 'received' AND received_ts IS NOT NULL)
--       OR (status = 'outstanding' AND received_ts IS NULL)
-- Casts: requested_ts/received_ts -> TIMESTAMP.
-- Dedup: one row per (claim_no, code) keeping the most recently received.
-- ============================================================================
CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_claims_silver.requirement AS
SELECT
    CAST(claim_no     AS STRING)    AS claim_no,
    CAST(code         AS STRING)    AS code,
    CAST(description  AS STRING)    AS description,
    CAST(status       AS STRING)    AS status,
    CAST(requested_ts AS TIMESTAMP) AS requested_ts,
    CAST(received_ts  AS TIMESTAMP) AS received_ts
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_bronze.requirement
WHERE claim_no IS NOT NULL AND code IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY claim_no, code
    ORDER BY received_ts DESC NULLS LAST, requested_ts DESC NULLS LAST
) = 1;

-- ============================================================================
-- Silver: role_player
-- Conformed / typed / deduped passthrough of bronze.role_player.
-- The bronze table has no natural single-column key, so we dedup on the full
-- business grain (policy_no, role, relationship, name).
-- DQ NOTE (DLT-style expectation):
--   EXPECT policy_no IS NOT NULL
--   EXPECT role IN ('policyholder','payer','beneficiary')
-- ============================================================================
CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_claims_silver.role_player AS
SELECT
    CAST(policy_no    AS STRING) AS policy_no,
    CAST(role         AS STRING) AS role,
    CAST(relationship AS STRING) AS relationship,
    CAST(name         AS STRING) AS name
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_bronze.role_player
WHERE policy_no IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY policy_no, role, relationship, name
    ORDER BY policy_no
) = 1;

-- ============================================================================
-- Silver: tp_verification
-- Conformed / typed / deduped passthrough of bronze.tp_verification.
-- Third-party verification results (VPD / other_insurer / bank / identity).
-- Keyed by (claim_no, source).
-- DQ NOTE (DLT-style expectation):
--   EXPECT claim_no IS NOT NULL
--   EXPECT source IN ('VPD','other_insurer','bank','identity')
-- Casts: checked_ts -> TIMESTAMP.
-- Dedup: one row per (claim_no, source) keeping the latest check.
-- ============================================================================
CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_claims_silver.tp_verification AS
SELECT
    CAST(claim_no       AS STRING)    AS claim_no,
    CAST(source         AS STRING)    AS source,
    CAST(result_json    AS STRING)    AS result_json,
    CAST(result_summary AS STRING)    AS result_summary,
    CAST(checked_ts     AS TIMESTAMP) AS checked_ts
FROM elexon_app_for_settlement_acc_catalog.momentum_claims_bronze.tp_verification
WHERE claim_no IS NOT NULL AND source IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY claim_no, source
    ORDER BY checked_ts DESC NULLS LAST
) = 1;
