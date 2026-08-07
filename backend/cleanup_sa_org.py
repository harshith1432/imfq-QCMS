"""
cleanup_sa_org.py
-----------------
1. Adds 'is_platform_org' boolean column to the organizations table (idempotent).
2. Marks the SuperAdmin's org as is_platform_org = TRUE.
3. Deletes all fake subscription, payment, and invoice data for that org.

Run ONCE from the backend/ directory:
    python cleanup_sa_org.py
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.infrastructure.database.models.models import (
    db, User, Organization, Role, Subscription, SubscriptionInvoice,
    SubscriptionPayment
)
from sqlalchemy import text

app = create_app()

with app.app_context():
    # ── Step 1: Add is_platform_org column if it doesn't exist ──────────────
    try:
        db.session.execute(text(
            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS is_platform_org BOOLEAN NOT NULL DEFAULT FALSE;"
        ))
        db.session.commit()
        print("✅ Column 'is_platform_org' ensured on organizations table.")
    except Exception as e:
        db.session.rollback()
        print(f"⚠️  Column alter skipped (may already exist): {e}")

    # ── Step 2: Find SA role and their org IDs ───────────────────────────────
    sa_role = Role.query.filter_by(name='SuperAdmin').first()
    if not sa_role:
        print("ERROR: No SuperAdmin role found.")
        sys.exit(1)

    sa_users = User.query.filter_by(role_id=sa_role.id).all()
    sa_org_ids = list({u.org_id for u in sa_users if u.org_id})
    print(f"SuperAdmin users: {[u.email for u in sa_users]}")
    print(f"Platform org IDs: {sa_org_ids}")

    if not sa_org_ids:
        print("No platform org found — nothing to clean.")
        sys.exit(0)

    # ── Step 3: Mark orgs as platform orgs & delete fake data ───────────────
    for org_id in sa_org_ids:
        org = Organization.query.get(org_id)
        if not org:
            print(f"  Org ID {org_id} not in DB. Skipping.")
            continue

        print(f"\n--- Cleaning '{org.name}' (ID={org_id}) ---")

        # Mark as platform org
        db.session.execute(text(
            "UPDATE organizations SET is_platform_org = TRUE WHERE id = :oid"
        ), {'oid': org_id})

        # Delete invoices for this org's subscriptions
        subs = Subscription.query.filter_by(org_id=org_id).all()
        sub_ids = [s.id for s in subs]
        inv_del = 0
        if sub_ids:
            inv_del = SubscriptionInvoice.query.filter(
                SubscriptionInvoice.subscription_id.in_(sub_ids)
            ).delete(synchronize_session=False)

        # Delete payments
        pay_del = SubscriptionPayment.query.filter_by(org_id=org_id).delete(synchronize_session=False)

        # Delete subscriptions
        sub_del = Subscription.query.filter_by(org_id=org_id).delete(synchronize_session=False)

        print(f"  Deleted: {sub_del} subscription(s), {inv_del} invoice(s), {pay_del} payment(s)")
        print(f"  Marked org as is_platform_org=TRUE")

    # ── Step 4: Commit ───────────────────────────────────────────────────────
    try:
        db.session.commit()
        print("\n✅ All done! Now restart the Flask server.")
        print("   The backend code already filters out is_platform_org=TRUE orgs")
        print("   from all tenant listings, subscriptions, and analytics.")
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Commit failed: {e}")
        raise
