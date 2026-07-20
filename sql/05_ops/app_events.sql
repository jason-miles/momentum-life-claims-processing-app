-- ============================================================================
-- Ops: app_events  (Delta table)
-- Write-state / audit trail for the Assessment Analytics Portal. Every
-- Accept-synopsis / Edit / Record-referral action from the Claim Detail page
-- is appended here by the app's service principal (POST /api/action).
--
-- The app SP holds USE/SELECT/MODIFY on the momentum_claims_ops schema.
-- (Phase 2+: this write-state moves to Lakebase managed Postgres.)
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS elexon_app_for_settlement_acc_catalog.momentum_claims_ops;

CREATE TABLE IF NOT EXISTS elexon_app_for_settlement_acc_catalog.momentum_claims_ops.app_events (
    event_id   STRING    COMMENT 'uuid() generated at insert',
    claim_no   STRING    COMMENT 'claim the action was taken on',
    user_role  STRING    COMMENT 'View-as role of the acting user (Assessor/Manager/...)',
    action     STRING    COMMENT 'accept_synopsis | edit_synopsis | record_referral',
    payload    STRING    COMMENT 'JSON: {assignee, comment}',
    ts         TIMESTAMP COMMENT 'server insert time'
)
USING DELTA
COMMENT 'Assessment portal action/audit log (write-state).';
