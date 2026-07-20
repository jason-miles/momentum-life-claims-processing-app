-- ============================================================================
-- Underwriting SILVER — conform bronze -> silver (typed, deduped).
-- Source: momentum_uw_bronze.*  (loaded by generate_underwriting.py)
-- Keyed on policy_no. Mirrors the live-deployed build.
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS elexon_app_for_settlement_acc_catalog.momentum_uw_silver;

CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_uw_silver.application AS
SELECT CAST(policy_no AS STRING) policy_no, CAST(submitted_date AS DATE) submitted_date,
       CAST(channel AS STRING) channel, CAST(broker AS STRING) broker,
       CAST(benefit_type AS STRING) benefit_type, CAST(sum_at_risk AS DECIMAL(14,2)) sum_at_risk,
       CAST(sar_band AS STRING) sar_band, CAST(province AS STRING) province,
       CAST(journey_type AS STRING) journey_type, CAST(underwriter AS STRING) underwriter
FROM elexon_app_for_settlement_acc_catalog.momentum_uw_bronze.application
WHERE policy_no IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY policy_no ORDER BY submitted_date DESC) = 1;

CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_uw_silver.uw_life AS
SELECT CAST(policy_no AS STRING) policy_no, CAST(age AS INT) age,
       CAST(smoker_flag AS BOOLEAN) smoker_flag, CAST(occupation_class AS STRING) occupation_class,
       CAST(id_number_masked AS STRING) id_number_masked, CAST(risk_score AS DOUBLE) risk_score
FROM elexon_app_for_settlement_acc_catalog.momentum_uw_bronze.uw_life
WHERE policy_no IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY policy_no ORDER BY policy_no) = 1;

CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_uw_silver.first_pass AS
SELECT * FROM elexon_app_for_settlement_acc_catalog.momentum_uw_bronze.first_pass;

CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_uw_silver.uw_requirement AS
SELECT * FROM elexon_app_for_settlement_acc_catalog.momentum_uw_bronze.uw_requirement;

CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_uw_silver.uw_decision AS
SELECT * FROM elexon_app_for_settlement_acc_catalog.momentum_uw_bronze.uw_decision;

CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_uw_silver.uw_case_note AS
SELECT * FROM elexon_app_for_settlement_acc_catalog.momentum_uw_bronze.uw_case_note;

CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_uw_silver.bpm_task AS
SELECT * FROM elexon_app_for_settlement_acc_catalog.momentum_uw_bronze.bpm_task;

CREATE OR REPLACE TABLE elexon_app_for_settlement_acc_catalog.momentum_uw_silver.ntu AS
SELECT * FROM elexon_app_for_settlement_acc_catalog.momentum_uw_bronze.ntu;
