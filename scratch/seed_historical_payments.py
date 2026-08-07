import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))

from app import create_app
from app.infrastructure.database.models.models import db, Organization, SubscriptionPayment

app = create_app()

with app.app_context():
    print("1. Checking active organizations...")
    orgs = Organization.query.filter(Organization.subscription_status.in_(['Active', 'Trialing'])).all()
    print(f"Found {len(orgs)} active/trialing orgs.")

    plan_prices = {
        'Starter': 4999.0,
        'Professional': 14999.0,
        'Enterprise': 49999.0
    }

    now = datetime.utcnow()
    # Check existing payments count
    existing_count = SubscriptionPayment.query.count()
    print(f"Existing SubscriptionPayment count: {existing_count}")

    # Seed past 6 months of payments if fewer than 10 payments exist
    if existing_count < 10:
        added_count = 0
        for i in range(1, 6): # 1 to 5 months ago
            payment_date = now - timedelta(days=30 * i)
            for org in orgs:
                plan = org.subscription_plan or 'Starter'
                base_price = plan_prices.get(plan, 4999.0)
                gst = base_price * 0.18
                final_amt = base_price + gst

                pay = SubscriptionPayment(
                    org_id=org.id,
                    amount=base_price,
                    currency='INR',
                    plan_name=plan,
                    billing_cycle='Monthly',
                    payment_status='Completed',
                    transaction_id=f"TXN_HIST_{org.id}_{i}_{int(payment_date.timestamp())}",
                    payment_gateway='Razorpay',
                    gateway_reference=f"pay_hist_{i}_{org.id}",
                    gst_percent=18.0,
                    gst_amount=gst,
                    final_amount=final_amt,
                    created_at=payment_date,
                    billing_period_start=payment_date,
                    billing_period_end=payment_date + timedelta(days=30)
                )
                db.session.add(pay)
                added_count += 1

        db.session.commit()
        print(f"Successfully seeded {added_count} historical subscription payments!")
    else:
        print("Sufficient historical payments already present in DB.")
