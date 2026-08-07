from app import create_app, db
from app.infrastructure.database.models.models import Organization, UserCustomField

app = create_app()
with app.app_context():
    try:
        orgs = Organization.query.all()
        added_count = 0
        for org in orgs:
            # Check if email is registered as a custom field
            existing = UserCustomField.query.filter_by(org_id=org.id, field_key='email').first()
            if not existing:
                db.session.add(UserCustomField(
                    org_id=org.id,
                    field_key='email',
                    display_name='Email Address',
                    is_required=True,
                    is_system=True,
                    data_type='email'
                ))
                added_count += 1
        db.session.commit()
        print(f"SUCCESS: Added email system custom field for {added_count} organizations.")
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: {e}")
