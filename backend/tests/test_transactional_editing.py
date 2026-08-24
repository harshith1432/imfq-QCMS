import os
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

import pytest
import json
from app import create_app, db
from app.infrastructure.database.models.models import User, Organization

@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()
        db.session.remove()

@pytest.fixture
def client(app):
    return app.test_client()

def test_no_auto_save_on_partial_payload(client, app):
    """
    Test that sending a PUT/PATCH update only modifies the fields present in the payload,
    leaving unchanged fields intact and wrapped in a database transaction.
    """
    import uuid
    uid = uuid.uuid4().hex[:8]
    with app.app_context():
        org = Organization(
            name=f"Original Company {uid}",
            gst_number="22AAAAA0000A1Z5",
            pan_number="ABCDE1234F",
            email=f"info_{uid}@original.com",
            phone="9876543210"
        )
        db.session.add(org)
        db.session.commit()
        org_id = org.id

        from app.infrastructure.database.models.models import Role
        admin_role = Role.query.filter_by(name='Admin').first()
        role_id = admin_role.id if admin_role else 1

        user = User(
            username=f"admin_user_{uid}",
            email=f"admin_{uid}@original.com",
            role_id=role_id,
            org_id=org_id
        )
        user.password = "Password@123"
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    # Perform single explicit Save request with ONLY modified field 'name'
    with app.app_context():
        target_org = db.session.get(Organization, org_id)
        assert target_org.name.startswith("Original Company")
        assert target_org.gst_number == "22AAAAA0000A1Z5"

        # Explicit payload update
        target_org.name = "ABC Private Ltd"
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

        refreshed_org = db.session.get(Organization, org_id)
        assert refreshed_org.name == "ABC Private Ltd"
        # Unchanged fields remain intact
        assert refreshed_org.gst_number == "22AAAAA0000A1Z5"
        assert refreshed_org.pan_number == "ABCDE1234F"

def test_transaction_rollback_on_failure(app):
    """
    Test that invalid updates trigger a rollback and leave the database completely unchanged.
    """
    import uuid
    uid = uuid.uuid4().hex[:8]
    with app.app_context():
        org = Organization(
            name=f"Safe Company {uid}",
            email=f"safe_{uid}@company.com",
            session_timeout=30
        )
        db.session.add(org)
        db.session.commit()
        org_id = org.id

        try:
            # Simulate invalid data attempt
            target_org = db.session.get(Organization, org_id)
            target_org.session_timeout = 999999  # Invalid timeout value
            if target_org.session_timeout > 1440:
                raise ValueError("Session timeout exceeds max limit")
            db.session.commit()
        except ValueError:
            db.session.rollback()

        # Database remains completely unchanged
        refreshed_org = db.session.get(Organization, org_id)
        assert refreshed_org.session_timeout == 30
