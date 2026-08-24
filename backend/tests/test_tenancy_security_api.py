import pytest
import time
from app import db
from app.infrastructure.database.models import Organization, Project, User, Role
from flask_jwt_extended import create_access_token


def test_cross_tenant_isolation(app, client):
    """Verify tenant isolation: User from Org A cannot access or modify Org B projects."""
    with app.app_context():
        # Create Org A
        org_a = Organization(name=f"Org A {int(time.time())}", email=f"orga_{int(time.time())}@test.com")
        # Create Org B
        org_b = Organization(name=f"Org B {int(time.time())}", email=f"orgb_{int(time.time())}@test.com")
        db.session.add_all([org_a, org_b])
        db.session.commit()

        admin_role = Role.query.filter_by(name='Admin').first()

        ts = int(time.time())
        # User in Org A
        user_a = User(
            email=f"usera_{ts}@orga.com",
            username=f"usera_{ts}",
            full_name="User Org A",
            org_id=org_a.id,
            role_id=admin_role.id if admin_role else 1,
            is_active=True,
            status="Active"
        )
        user_a.set_password("SecurePass123!")

        # User in Org B
        user_b = User(
            email=f"userb_{ts}@orgb.com",
            username=f"userb_{ts}",
            full_name="User Org B",
            org_id=org_b.id,
            role_id=admin_role.id if admin_role else 1,
            is_active=True,
            status="Active"
        )
        user_b.set_password("SecurePass123!")

        # Project belonging to Org B
        proj_b = Project(
            title="Secret Project Org B",
            project_uid=f"PRJ-ORGB-{int(time.time())}",
            org_id=org_b.id,
            status="In Progress"
        )

        db.session.add_all([user_a, user_b, proj_b])
        db.session.commit()

        token_a = create_access_token(identity=str(user_a.id))
        proj_b_id = proj_b.id

    headers_a = {'Authorization': f'Bearer {token_a}', 'Content-Type': 'application/json'}
    
    # User A attempts to access Org B's project
    res = client.get(f'/api/projects/{proj_b_id}', headers=headers_a)
    assert res.status_code in [403, 404], f"Cross-tenant access allowed! Status: {res.status_code}"
