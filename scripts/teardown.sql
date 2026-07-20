-- ============================================================================
-- Teardown — drop ALL Momentum demo schemas (claims + underwriting).
-- DESTRUCTIVE. Run only to fully reset the demo. The app, dashboards, Genie
-- spaces and Vector Search indexes are NOT dropped here (delete those via their
-- own tools / `databricks bundle destroy`).
--
-- Vector Search indexes must be deleted BEFORE their source tables, or the drop
-- will leave orphaned indexes. Delete idx_documents / idx_uw_notes / idx_email
-- via the Vector Search UI or API first if you are fully resetting.
-- ============================================================================
DROP SCHEMA IF EXISTS elexon_app_for_settlement_acc_catalog.momentum_claims_bronze CASCADE;
DROP SCHEMA IF EXISTS elexon_app_for_settlement_acc_catalog.momentum_claims_silver CASCADE;
DROP SCHEMA IF EXISTS elexon_app_for_settlement_acc_catalog.momentum_claims_gold CASCADE;
DROP SCHEMA IF EXISTS elexon_app_for_settlement_acc_catalog.momentum_claims_ai CASCADE;
DROP SCHEMA IF EXISTS elexon_app_for_settlement_acc_catalog.momentum_claims_ops CASCADE;

DROP SCHEMA IF EXISTS elexon_app_for_settlement_acc_catalog.momentum_uw_bronze CASCADE;
DROP SCHEMA IF EXISTS elexon_app_for_settlement_acc_catalog.momentum_uw_silver CASCADE;
DROP SCHEMA IF EXISTS elexon_app_for_settlement_acc_catalog.momentum_uw_gold CASCADE;
DROP SCHEMA IF EXISTS elexon_app_for_settlement_acc_catalog.momentum_uw_ai CASCADE;
