import pytest
import json
import uuid
from datetime import datetime, timedelta, timezone
from app import db
from app.infrastructure.database.models.models import User, Organization, Role


def test_get_license_stats(client, super_admin_context):
    res = client.get('/api/licenses/stats', headers=super_admin_context['headers'])
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert 'total' in data['data']
    assert 'active' in data['data']


def test_list_licenses(client, super_admin_context):
    res = client.get('/api/licenses/', headers=super_admin_context['headers'])
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert isinstance(data['data'], list)


def test_get_license_details(client, super_admin_context, auth_context):
    org_id = auth_context['org_id']
    res = client.get(f'/api/licenses/{org_id}', headers=super_admin_context['headers'])
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert data['data']['organization_name'] == auth_context['org'].name


def test_create_license(client, super_admin_context, app):
    with app.app_context():
        uid = uuid.uuid4().hex[:6]
        new_org = Organization(
            name=f"Beta Inc {uid}",
            org_code=f"B_{uid}".upper(),
            email=f"admin_{uid}@beta.com",
            subscription_status="Trialing"
        )
        db.session.add(new_org)
        db.session.commit()
        org_id = new_org.id

    payload = {
        "org_id": org_id,
        "plan_name": "Professional",
        "license_type": "Lifetime",
        "max_users": 100,
        "storage_limit_gb": 10,
        "enabled_modules": ["Projects", "SOP"]
    }
    res = client.post('/api/licenses/', json=payload, headers=super_admin_context['headers'])
    assert res.status_code == 201
    data = res.get_json()
    assert data['status'] == 'success'
    assert data['license_key'].startswith('QCMS-')

    with app.app_context():
        updated_org = db.session.get(Organization, org_id)
        assert updated_org.subscription_plan == 'Professional'
        assert updated_org.subscription_status == 'Active'
        assert updated_org.max_users == 100


def test_license_status_actions(client, super_admin_context, app):
    with app.app_context():
        uid = uuid.uuid4().hex[:6]
        org = Organization(
            name=f"Status Test Org {uid}",
            org_code=f"ST_{uid}".upper(),
            email=f"status_{uid}@test.org",
            subscription_plan="Professional",
            subscription_status="Active",
            license_number=f"QCMS-{uid}-TEST-KEY"
        )
        db.session.add(org)
        db.session.commit()
        org_id = org.id

    # Suspend
    res = client.post(f'/api/licenses/{org_id}/suspend', json={"reason": "Non-payment"}, headers=super_admin_context['headers'])
    assert res.status_code == 200
    with app.app_context():
        assert db.session.get(Organization, org_id).subscription_status == 'Suspended'

    # Resume
    res = client.post(f'/api/licenses/{org_id}/resume', headers=super_admin_context['headers'])
    assert res.status_code == 200
    with app.app_context():
        assert db.session.get(Organization, org_id).subscription_status == 'Active'

    # Regenerate Key
    res = client.post(f'/api/licenses/{org_id}/regenerate-key', headers=super_admin_context['headers'])
    assert res.status_code == 200
    with app.app_context():
        assert db.session.get(Organization, org_id).license_number != f"QCMS-{uid}-TEST-KEY"

    # Download License File
    res = client.get(f'/api/licenses/{org_id}/download', headers=super_admin_context['headers'])
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert 'content' in data

    # Revoke
    res = client.post(f'/api/licenses/{org_id}/revoke', headers=super_admin_context['headers'])
    assert res.status_code == 200
    with app.app_context():
        assert db.session.get(Organization, org_id).subscription_status == 'Revoked'
