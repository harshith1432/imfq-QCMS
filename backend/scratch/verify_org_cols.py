from app import create_app
from app.infrastructure.database.models.models import db, Organization

app = create_app()
with app.app_context():
    orgs = Organization.query.all()
    print(f"Loaded {len(orgs)} organizations.")
    for o in orgs[:5]:
        print(f"Org: {o.name}, GST: {o.gst_number}, License start: {o.license_start_date}, License expiry: {o.license_expiry_date}, Storage: {o.storage_used_mb}MB")
