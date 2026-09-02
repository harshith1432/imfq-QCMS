import pytest
import os
import sys
import uuid
import time

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.infrastructure.database.models import User, Role, Organization, Project
from flask_jwt_extended import create_access_token


@pytest.fixture(scope='session')
def app():
    """Session-scoped application fixture."""
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    return app


@pytest.fixture(scope='function')
def client(app):
    """Provides test client."""
    return app.test_client()


@pytest.fixture(scope='function')
def auth_context(app):
    """Provides authenticated test organization and admin user."""
    with app.app_context():
        # Retrieve existing test organization or fallback
        org = Organization.query.first()
        if not org:
            org = Organization(name="Test Org Pytest", email="pytest_org@test.org", subscription_plan="Enterprise")
            db.session.add(org)
            db.session.commit()

        admin_role = Role.query.filter_by(name='Admin').first()
        if not admin_role:
            admin_role = Role(name='Admin', description='Administrator')
            db.session.add(admin_role)
            db.session.commit()

        # Find or create active user
        user = User.query.filter_by(org_id=org.id, is_active=True).first()
        if not user:
            uid = uuid.uuid4().hex[:8]
            user = User(
                email=f"test_{uid}@pytest.org",
                username=f"pytest_admin_{uid}",
                full_name="Pytest Admin",
                org_id=org.id,
                role_id=admin_role.id,
                is_active=True,
                status="Active"
            )
            user.set_password("TestPassword123!")
            db.session.add(user)
            db.session.commit()

        from app.infrastructure.database.models.auth import SaaSUserSession
        import datetime

        # Ensure user status is Active
        user.status = "Active"
        user.is_active = True
        
        # Clean up any old terminated sessions and ensure an active session exists
        sess_id = f"pytest_sess_{user.id}_{uuid.uuid4().hex}"
        session_entry = SaaSUserSession(
            user_id=user.id,
            org_id=user.org_id,
            session_id=sess_id,
            ip_address="127.0.0.1",
            browser="Pytest",
            status="Active",
            login_time=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
            last_activity=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        )
        db.session.add(session_entry)
        db.session.commit()

        token = create_access_token(identity=str(user.id), additional_claims={"session_id": sess_id})
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        return {
            "user": user,
            "user_id": user.id,
            "org": org,
            "org_id": org.id,
            "token": token,
            "headers": headers
        }


@pytest.fixture(scope='function')
def super_admin_context(app):
    """Provides authenticated SuperAdmin user and headers."""
    with app.app_context():
        from app.infrastructure.database.models.auth import SaaSUserSession
        import datetime

        sa_role = Role.query.filter_by(name='SuperAdmin').first()
        if not sa_role:
            sa_role = Role(name='SuperAdmin', description='Super Administrator')
            db.session.add(sa_role)
            db.session.commit()

        sa_user = User.query.filter_by(role_id=sa_role.id).first()
        if not sa_user:
            sa_user = User(
                email="sa_pytest@qcms.io",
                username="sa_pytest",
                full_name="Super Admin Pytest",
                role_id=sa_role.id,
                org_id=None,
                is_active=True,
                status="Active",
                custom_fields={"super_admin_role": "Owner"}
            )
            sa_user.set_password("SuperSecret123!")
            db.session.add(sa_user)
            db.session.commit()
        else:
            sa_user.custom_fields = {"super_admin_role": "Owner"}
            sa_user.is_active = True
            sa_user.status = "Active"

        sess_id = f"pytest_sa_sess_{sa_user.id}_{uuid.uuid4().hex}"
        session_entry = SaaSUserSession(
            user_id=sa_user.id,
            org_id=None,
            session_id=sess_id,
            ip_address="127.0.0.1",
            browser="Pytest",
            status="Active",
            login_time=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
            last_activity=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        )
        db.session.add(session_entry)
        db.session.commit()

        token = create_access_token(
            identity=str(sa_user.id),
            additional_claims={
                "session_id": sess_id,
                "role": "SuperAdmin",
                "org_id": None
            }
        )
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        return {
            "user": sa_user,
            "user_id": sa_user.id,
            "token": token,
            "headers": headers
        }
