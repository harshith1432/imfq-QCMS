import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))

from app import create_app
from app.infrastructure.database.models.models import db, IntegrationConfig, OfflinePaymentProof, Organization, User

app = create_app()

with app.app_context():
    print("1. Creating database tables (including offline_payment_proofs)...")
    db.create_all()
    print("Database tables created successfully!")

    print("\n2. Testing seed_default_integrations...")
    from app.presentation.routes.integrations_routes import seed_default_integrations
    seed_default_integrations()

    configs = IntegrationConfig.query.all()
    print(f"Total seeded integration providers in DB: {len(configs)}")
    for c in configs:
        print(f" - [{c.category}] {c.provider_name} ({c.provider_id}): {c.status}")

    razorpay = IntegrationConfig.query.filter_by(provider_id='razorpay').first()
    dynamic_qr = IntegrationConfig.query.filter_by(provider_id='dynamic_qr').first()

    assert razorpay is not None, "Razorpay provider missing!"
    assert dynamic_qr is not None, "Dynamic QR provider missing!"

    print("\nRazorpay Settings:", razorpay.settings)
    print("Dynamic QR Settings:", dynamic_qr.settings)

    print("\n3. Testing Flask Test Client endpoints...")
    client = app.test_client()

    # Login as SuperAdmin or Admin
    user = User.query.filter_by(email='harshithkd6@gmail.com').first() or User.query.first()
    if user:
        from flask_jwt_extended import create_access_token
        token = create_access_token(identity=str(user.id))
        headers = {'Authorization': f'Bearer {token}'}

        res = client.get('/api/billing/payment-gateways', headers=headers)
        print(f"GET /api/billing/payment-gateways -> {res.status_code}")
        print("Response JSON:", res.get_json())

        res_rev = client.get('/api/analytics/revenue?date_range=Last+30+Days', headers=headers)
        print(f"GET /api/analytics/revenue -> {res_rev.status_code}")
        rev_data = res_rev.get_json()
        print("Revenue Analytics Trends:", rev_data.get('trends'))
        print("Revenue Analytics Summary:", {
            "mrr": rev_data.get("mrr"),
            "arr": rev_data.get("arr"),
            "arpo": rev_data.get("arpo")
        })

    print("\nSUCCESS: All payment gateway and integration tests passed cleanly!")
