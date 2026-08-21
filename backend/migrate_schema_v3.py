"""
QCMS Enterprise Database Schema Hardening & Performance Migration (v3)
===================================================================
1. Converts financial float columns to fixed-precision NUMERIC(12, 2) / NUMERIC(5, 2).
2. Adds high-scale composite B-Tree indexes for multi-tenant query acceleration.
3. Enforces database-level idempotency and unique partial index constraints.
"""

import sys
import os
import logging
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app import create_app, db

logging.basicConfig(level=logging.INFO, format='[SCHEMA MIGRATION v3] %(levelname)s: %(message)s')

def run_migration():
    app = create_app()
    with app.app_context():
        logging.info("Starting Schema Migration v3 (NUMERIC precision, Composite Indexes, Unique Constraints)...")

        statements = [
            # 1. Financial Precision Alterations (FLOAT -> NUMERIC)
            "ALTER TABLE subscription_payments ALTER COLUMN amount TYPE NUMERIC(12, 2) USING COALESCE(amount, 0)::NUMERIC(12, 2);",
            "ALTER TABLE subscription_payments ALTER COLUMN discount_amount TYPE NUMERIC(12, 2) USING COALESCE(discount_amount, 0)::NUMERIC(12, 2);",
            "ALTER TABLE subscription_payments ALTER COLUMN gst_percent TYPE NUMERIC(5, 2) USING COALESCE(gst_percent, 18.00)::NUMERIC(5, 2);",
            "ALTER TABLE subscription_payments ALTER COLUMN gst_amount TYPE NUMERIC(12, 2) USING COALESCE(gst_amount, 0)::NUMERIC(12, 2);",
            "ALTER TABLE subscription_payments ALTER COLUMN final_amount TYPE NUMERIC(12, 2) USING COALESCE(final_amount, 0)::NUMERIC(12, 2);",
            "ALTER TABLE subscription_payments ALTER COLUMN refund_amount TYPE NUMERIC(12, 2) USING COALESCE(refund_amount, 0)::NUMERIC(12, 2);",

            "ALTER TABLE subscription_invoices ALTER COLUMN base_amount TYPE NUMERIC(12, 2) USING COALESCE(base_amount, 0)::NUMERIC(12, 2);",
            "ALTER TABLE subscription_invoices ALTER COLUMN discount_percent TYPE NUMERIC(5, 2) USING COALESCE(discount_percent, 0)::NUMERIC(5, 2);",
            "ALTER TABLE subscription_invoices ALTER COLUMN discount_amount TYPE NUMERIC(12, 2) USING COALESCE(discount_amount, 0)::NUMERIC(12, 2);",
            "ALTER TABLE subscription_invoices ALTER COLUMN gst_percent TYPE NUMERIC(5, 2) USING COALESCE(gst_percent, 18.00)::NUMERIC(5, 2);",
            "ALTER TABLE subscription_invoices ALTER COLUMN gst_amount TYPE NUMERIC(12, 2) USING COALESCE(gst_amount, 0)::NUMERIC(12, 2);",
            "ALTER TABLE subscription_invoices ALTER COLUMN total_amount TYPE NUMERIC(12, 2) USING COALESCE(total_amount, 0)::NUMERIC(12, 2);",

            "ALTER TABLE subscriptions ALTER COLUMN base_price TYPE NUMERIC(12, 2) USING COALESCE(base_price, 0)::NUMERIC(12, 2);",
            "ALTER TABLE subscriptions ALTER COLUMN discount_percent TYPE NUMERIC(5, 2) USING COALESCE(discount_percent, 0)::NUMERIC(5, 2);",
            "ALTER TABLE subscriptions ALTER COLUMN discount_amount TYPE NUMERIC(12, 2) USING COALESCE(discount_amount, 0)::NUMERIC(12, 2);",
            "ALTER TABLE subscriptions ALTER COLUMN gst_percent TYPE NUMERIC(5, 2) USING COALESCE(gst_percent, 18.00)::NUMERIC(5, 2);",
            "ALTER TABLE subscriptions ALTER COLUMN gst_amount TYPE NUMERIC(12, 2) USING COALESCE(gst_amount, 0)::NUMERIC(12, 2);",
            "ALTER TABLE subscriptions ALTER COLUMN final_amount TYPE NUMERIC(12, 2) USING COALESCE(final_amount, 0)::NUMERIC(12, 2);",

            "ALTER TABLE saas_plan_pricing ALTER COLUMN price TYPE NUMERIC(12, 2) USING COALESCE(price, 0)::NUMERIC(12, 2);",
            "ALTER TABLE saas_plan_pricing ALTER COLUMN discount TYPE NUMERIC(5, 2) USING COALESCE(discount, 0)::NUMERIC(5, 2);",
            "ALTER TABLE saas_plan_pricing ALTER COLUMN tax TYPE NUMERIC(5, 2) USING COALESCE(tax, 18.00)::NUMERIC(5, 2);",

            "ALTER TABLE offline_payment_proofs ALTER COLUMN amount TYPE NUMERIC(12, 2) USING COALESCE(amount, 0)::NUMERIC(12, 2);",

            # Deduplicate project_reviews before creating unique index
            "DELETE FROM project_reviews r1 USING project_reviews r2 WHERE r1.id < r2.id AND r1.project_id = r2.project_id AND r1.stage_number = r2.stage_number AND r1.reviewer_id = r2.reviewer_id;",

            # Deduplicate active subscriptions per org before creating unique index
            "UPDATE subscriptions SET subscription_status = 'Cancelled' WHERE id IN (SELECT id FROM (SELECT id, ROW_NUMBER() OVER (PARTITION BY org_id ORDER BY created_at DESC) as rnum FROM subscriptions WHERE subscription_status = 'Active') s WHERE s.rnum > 1);",

            # 2. Composite B-Tree Indexes for Multi-Tenancy
            "CREATE INDEX IF NOT EXISTS idx_projects_org_status_created ON projects (org_id, status, created_at DESC);",
            "CREATE INDEX IF NOT EXISTS idx_project_members_user_proj ON project_members (user_id, project_id);",
            "CREATE INDEX IF NOT EXISTS idx_proj_stage_tracker ON project_stage_tracker (project_id, stage_number);",
            "CREATE INDEX IF NOT EXISTS idx_proj_workflow_stage ON project_workflow (project_id, stage_id);",
            "CREATE INDEX IF NOT EXISTS idx_payments_status_org_date ON subscription_payments (payment_status, org_id, created_at DESC);",
            "CREATE INDEX IF NOT EXISTS idx_invoices_org_status_due ON subscription_invoices (org_id, invoice_status, due_date);",
            "CREATE INDEX IF NOT EXISTS idx_subscriptions_org_status ON subscriptions (org_id, subscription_status);",
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_org_created ON audit_logs (org_id, created_at DESC);",
            "CREATE INDEX IF NOT EXISTS idx_users_org_email_status ON users (org_id, email, status);",
            "CREATE INDEX IF NOT EXISTS idx_email_logs_rule_status ON email_notification_logs (rule_id, status);",

            # 3. Database-Level Unique Partial Indexes
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_org_monthly_billing_cycle ON subscription_invoices (org_id, billing_period_start, billing_period_end) WHERE invoice_status != 'Draft' AND billing_period_start IS NOT NULL;",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_project_stage_review ON project_reviews (project_id, stage_number, reviewer_id);",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_active_org_subscription ON subscriptions (org_id) WHERE subscription_status = 'Active';"
        ]

        try:
            with db.engine.begin() as connection:
                for idx, stmt in enumerate(statements, 1):
                    logging.info(f"Executing statement {idx}/{len(statements)}...")
                    connection.execute(text(stmt))
            logging.info("Schema Migration v3 completed successfully with 0 errors!")
        except Exception as e:
            logging.error(f"Migration error: {e}")
            sys.exit(1)

if __name__ == '__main__':
    run_migration()
