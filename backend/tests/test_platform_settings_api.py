import pytest
import json
import uuid
from datetime import datetime, timedelta, timezone
from app import db
from app.infrastructure.database.models.models import User, Organization, Role, PlatformSettings


def test_settings_dashboard(client, super_admin_context):
    res = client.get('/api/super-admin/settings/dashboard', headers=super_admin_context['headers'])
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert 'kpis' in data['data']
    assert 'ai_insights' in data['data']
    assert data['data']['kpis']['platform_version'] == '1.0.0'


def test_get_settings(client, super_admin_context):
    res = client.get('/api/super-admin/settings', headers=super_admin_context['headers'])
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert 'site_name' in data['data']


def test_update_settings(client, super_admin_context):
    payload = {
        "site_name": "Updated QCMS Site Name",
        "trial_period_days": 30,
        "security_settings": {
            "password_min_length": 12,
            "password_uppercase": True
        }
    }
    res = client.put('/api/super-admin/settings', headers=super_admin_context['headers'], json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'

    # Read back settings
    res = client.get('/api/super-admin/settings', headers=super_admin_context['headers'])
    data = res.get_json()
    assert data['data']['site_name'] == "Updated QCMS Site Name"
    assert data['data']['trial_period_days'] == 30
    assert data['data']['security_settings']['password_min_length'] == 12
    assert data['data']['security_settings']['password_uppercase'] is True


def test_email_config_validation(client, super_admin_context):
    res = client.post('/api/super-admin/settings/test-email', headers=super_admin_context['headers'], json={
        "to_email": "test@test.com"
    })
    # Since SMTP is not configured, it should return 400
    assert res.status_code == 400


def test_api_keys_management(client, super_admin_context):
    # 1. Create a key
    res = client.post('/api/super-admin/settings/api-keys', headers=super_admin_context['headers'], json={
        "label": "Test Key Pytest",
        "scopes": ["read", "write"]
    })
    assert res.status_code == 201
    data = res.get_json()
    assert 'secret' in data['data']
    key_id = data['data']['id']

    # 2. List keys
    res = client.get('/api/super-admin/settings/api-keys', headers=super_admin_context['headers'])
    assert res.status_code == 200
    data = res.get_json()
    assert any(k['id'] == key_id for k in data['data'])

    # 3. Revoke key
    res = client.delete(f'/api/super-admin/settings/api-keys/{key_id}', headers=super_admin_context['headers'])
    assert res.status_code == 200

    # 4. List keys again (should not include revoked key)
    res = client.get('/api/super-admin/settings/api-keys', headers=super_admin_context['headers'])
    data = res.get_json()
    assert not any(k['id'] == key_id for k in data['data'])


def test_toggle_feature_flag(client, super_admin_context):
    res = client.patch('/api/super-admin/settings/feature-flags/beta_qc_charts', headers=super_admin_context['headers'], json={
        "enabled": True
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data['data']['enabled'] is True


def test_maintenance_mode_status(client, app):
    with app.app_context():
        s = PlatformSettings.query.order_by(PlatformSettings.id.asc()).first()
        if not s:
            s = PlatformSettings()
            db.session.add(s)
        s.maintenance_mode = False
        db.session.commit()

    # 1. Default (off)
    res = client.get('/api/auth/maintenance-status')
    assert res.status_code == 200
    data = res.get_json()
    assert data['maintenance_mode'] is False

    # 2. Enabled
    with app.app_context():
        s = PlatformSettings.query.order_by(PlatformSettings.id.asc()).first()
        s.maintenance_mode = True
        s.maintenance_settings = {"maintenance_message": "System is updating", "estimated_completion": "30 mins"}
        db.session.commit()

    try:
        res = client.get('/api/auth/maintenance-status')
        assert res.status_code == 200
        data = res.get_json()
        assert data['maintenance_mode'] is True
        assert data['message'] == "System is updating"
        assert data['eta'] == "30 mins"
    finally:
        # Reset
        with app.app_context():
            s = PlatformSettings.query.order_by(PlatformSettings.id.asc()).first()
            s.maintenance_mode = False
            db.session.commit()


def test_realtime_alerts(client, super_admin_context, app):
    uid = uuid.uuid4().hex[:6]
    with app.app_context():
        expiring_org = Organization(
            name=f"Expiring Corp {uid}",
            org_code=f"EXP_{uid}".upper(),
            email=f"admin_{uid}@expiring.com",
            subscription_plan="Professional",
            subscription_status="Active",
            license_expiry_date=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=3)
        )
        db.session.add(expiring_org)
        db.session.commit()

    res = client.get('/api/super-admin/alerts', headers=super_admin_context['headers'])
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert data['count'] > 0

    alert_titles = [a['title'] for a in data['data']]
    assert any(f"Expiring Corp {uid}" in t for t in alert_titles)
