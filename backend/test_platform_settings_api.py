import os
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['JWT_SECRET_KEY'] = 'test-secret-key'

import unittest
import json
from datetime import datetime, timedelta
from app import create_app
from app.infrastructure.database.models.models import db, User, Organization, Role, PlatformSettings, SuperAdminLog
from flask_jwt_extended import create_access_token

class TestPlatformSettingsAPI(unittest.TestCase):
    def setUp(self):
        # StaticPool is now configured in settings.py for all SQLite URIs,
        # so the engine created by create_app() already shares one connection.
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['JWT_SECRET_KEY'] = 'test-secret-key'

        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        
        db.create_all()
        self._seed_data()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _seed_data(self):
        # Create SuperAdmin role
        sa_role = Role.query.filter_by(name='SuperAdmin').first()
        if not sa_role:
            sa_role = Role(name='SuperAdmin')
            db.session.add(sa_role)
            
        admin_role = Role.query.filter_by(name='Admin').first()
        if not admin_role:
            admin_role = Role(name='Admin')
            db.session.add(admin_role)
        db.session.flush()

        # Create Organization
        self.org = Organization.query.filter_by(org_code="ALPHA").first()
        if not self.org:
            self.org = Organization(
                name="Alpha Corp",
                org_code="ALPHA",
                email="admin@alpha.com",
                subscription_plan="Starter",
                subscription_status="Active",
                max_users=50,
                storage_limit_mb=5120.0
            )
            db.session.add(self.org)
            db.session.flush()

        # Create SuperAdmin User
        self.sa_user = User.query.filter_by(email="sa@qcms.com").first()
        if not self.sa_user:
            self.sa_user = User(
                org_id=self.org.id,
                username="sa@qcms.com",
                email="sa@qcms.com",
                full_name="Super Admin",
                role_id=sa_role.id,
                is_active=True,
                is_verified=True,
                custom_fields={"super_admin_role": "Owner"}
            )
            self.sa_user.password = "12345678"
            db.session.add(self.sa_user)
            db.session.commit()

        # Generate JWT Token for Super Admin
        self.token = create_access_token(
            identity=str(self.sa_user.id),
            additional_claims={
                "org_id": self.sa_user.org_id,
                "role": "SuperAdmin",
                "dept_id": self.sa_user.department_id
            }
        )
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

        # Reuse the PlatformSettings row seeded by create_app() so that
        # LIMIT 1 queries in routes always refer to the same row the test modifies.
        # Creating a duplicate row (id=2) while the app seeds id=1 causes raw SQL
        # LIMIT 1 reads to return the seeded row while the test modifies the duplicate.
        self.settings = PlatformSettings.query.first()
        if not self.settings:
            self.settings = PlatformSettings()
            db.session.add(self.settings)
            db.session.commit()

    def test_settings_dashboard(self):
        res = self.client.get('/api/super-admin/settings/dashboard', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode())
        self.assertEqual(data['status'], 'success')
        self.assertIn('kpis', data['data'])
        self.assertIn('ai_insights', data['data'])
        self.assertEqual(data['data']['kpis']['platform_version'], '1.0.0')

    def test_get_settings(self):
        res = self.client.get('/api/super-admin/settings', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode())
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data']['site_name'], 'QCMS Enterprise')

    def test_update_settings(self):
        payload = {
            "site_name": "Updated QCMS Site Name",
            "trial_period_days": 30,
            "security_settings": {
                "password_min_length": 12,
                "password_uppercase": True
            }
        }
        res = self.client.put('/api/super-admin/settings', headers=self.headers, data=json.dumps(payload))
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode())
        self.assertEqual(data['status'], 'success')

        # Read back settings
        res = self.client.get('/api/super-admin/settings', headers=self.headers)
        data = json.loads(res.data.decode())
        self.assertEqual(data['data']['site_name'], "Updated QCMS Site Name")
        self.assertEqual(data['data']['trial_period_days'], 30)
        self.assertEqual(data['data']['security_settings']['password_min_length'], 12)
        self.assertEqual(data['data']['security_settings']['password_uppercase'], True)

    def test_email_config_validation(self):
        res = self.client.post('/api/super-admin/settings/test-email', headers=self.headers, data=json.dumps({
            "to_email": "test@test.com"
        }))
        # Since SMTP host is not configured, it should return 400 error
        self.assertEqual(res.status_code, 400)

    def test_api_keys_management(self):
        # 1. Create a key
        res = self.client.post('/api/super-admin/settings/api-keys', headers=self.headers, data=json.dumps({
            "label": "Test Key",
            "scopes": ["read", "write"]
        }))
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data.decode())
        self.assertIn('secret', data['data'])
        key_id = data['data']['id']

        # 2. List keys
        res = self.client.get('/api/super-admin/settings/api-keys', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode())
        self.assertEqual(len(data['data']), 1)
        self.assertEqual(data['data'][0]['label'], 'Test Key')

        # 3. Revoke key
        res = self.client.delete(f'/api/super-admin/settings/api-keys/{key_id}', headers=self.headers)
        self.assertEqual(res.status_code, 200)

        # 4. List keys again (should be empty)
        res = self.client.get('/api/super-admin/settings/api-keys', headers=self.headers)
        data = json.loads(res.data.decode())
        self.assertEqual(len(data['data']), 0)

    def test_toggle_feature_flag(self):
        res = self.client.patch('/api/super-admin/settings/feature-flags/beta_qc_charts', headers=self.headers, data=json.dumps({
            "enabled": True
        }))
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode())
        self.assertEqual(data['data']['enabled'], True)

    def test_backup_management(self):
        # 1. Trigger manual backup
        res = self.client.post('/api/super-admin/settings/backup', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode())
        self.assertEqual(data['status'], 'success')
        self.assertIn('id', data['data'])

        # 2. Get backup settings & history
        res = self.client.get('/api/super-admin/settings/backup', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode())
        self.assertEqual(len(data['data']['history']), 1)

    def test_maintenance_mode_status(self):
        # 1. Default (off)
        res = self.client.get('/api/auth/maintenance-status')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode())
        self.assertEqual(data['maintenance_mode'], False)

        # 2. Enabled
        self.settings.maintenance_mode = True
        self.settings.maintenance_settings = {"maintenance_message": "System is updating", "estimated_completion": "30 mins"}
        db.session.commit()

        res = self.client.get('/api/auth/maintenance-status')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode())
        self.assertEqual(data['maintenance_mode'], True)
        self.assertEqual(data['message'], "System is updating")
        self.assertEqual(data['eta'], "30 mins")

    def test_maintenance_mode_api_blocking(self):
        # Enable maintenance mode
        self.settings.maintenance_mode = True
        db.session.commit()

        # Create a non-super-admin user token
        user_role = Role.query.filter_by(name='Admin').first()
        if not user_role:
            user_role = Role(name='Admin')
            db.session.add(user_role)
            db.session.flush()
        regular_user = User(
            org_id=self.org.id,
            username="admin@alpha.com",
            email="admin@alpha.com",
            role_id=user_role.id,
            is_active=True,
            is_verified=True
        )
        regular_user.password = "12345678"
        db.session.add(regular_user)
        db.session.commit()

        user_token = create_access_token(
            identity=str(regular_user.id),
            additional_claims={
                "org_id": regular_user.org_id,
                "role": "Admin",
                "dept_id": regular_user.department_id
            }
        )
        user_headers = {
            'Authorization': f'Bearer {user_token}',
            'Content-Type': 'application/json'
        }

        # 1. Non-super-admin GET request should pass (can view)
        res = self.client.get('/api/admin/departments', headers=user_headers)
        # Note: endpoint may return 200 or 404 depending on existence, but NOT 503 Maintenance
        self.assertNotEqual(res.status_code, 503)

        # 2. Non-super-admin POST request should fail with 503 Service Unavailable
        res = self.client.post('/api/admin/departments', headers=user_headers, data=json.dumps({"name": "Engineering"}))
        self.assertEqual(res.status_code, 503)
        data = json.loads(res.data.decode())
        self.assertEqual(data['code'], 'MAINTENANCE_MODE')

        # 3. SuperAdmin post request should pass
        res = self.client.post('/api/super-admin/settings/backup', headers=self.headers)
        self.assertEqual(res.status_code, 200)

    def test_realtime_alerts(self):
        """Test GET /api/super-admin/alerts endpoint"""
        # Create an expiring organization
        expiring_org = Organization(
            name="Expiring Tenant Corp",
            org_code="EXPIRE",
            email="admin@expiring.com",
            subscription_plan="Professional",
            subscription_status="Active",
            license_expiry_date=datetime.utcnow() + timedelta(days=3)
        )
        db.session.add(expiring_org)
        db.session.commit()

        res = self.client.get('/api/super-admin/alerts', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode())
        self.assertEqual(data['status'], 'success')
        self.assertGreater(data['count'], 0)

        # Check if expiring org alert exists in returned list
        alert_titles = [a['title'] for a in data['data']]
        self.assertTrue(any("Expiring Tenant Corp" in t for t in alert_titles))

