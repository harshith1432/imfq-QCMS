import os
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['JWT_SECRET_KEY'] = 'test-secret-key'

import unittest
import json
from datetime import datetime, timedelta
from app import create_app
from app.infrastructure.database.models.models import db, User, Organization, Role, SuperAdminLog
from flask_jwt_extended import create_access_token

class TestLicenseWorkflows(unittest.TestCase):
    def setUp(self):
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
                storage_limit_mb=5120.0,
                license_number="QCMS-1111-2222-3333-4444",
                license_start_date=datetime.utcnow(),
                license_expiry_date=datetime.utcnow() + timedelta(days=365)
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

    def test_get_license_stats(self):
        res = self.client.get('/api/licenses/stats', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertGreaterEqual(data['data']['total'], 1)
        self.assertGreaterEqual(data['data']['active'], 1)

    def test_list_licenses(self):
        res = self.client.get('/api/licenses/', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertGreaterEqual(len(data['data']), 1)
        org_names = [x['organization_name'] for x in data['data']]
        self.assertIn('Alpha Corp', org_names)

    def test_get_license_details(self):
        res = self.client.get(f'/api/licenses/{self.org.id}', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data']['organization_name'], 'Alpha Corp')

    def test_create_license(self):
        # Create a new organization with no license first
        new_org = Organization(
            name="Beta Inc",
            org_code="BETA",
            email="admin@beta.com",
            subscription_status="Trialing"
        )
        db.session.add(new_org)
        db.session.commit()

        payload = {
            "org_id": new_org.id,
            "plan_name": "Professional",
            "license_type": "Lifetime",
            "max_users": 100,
            "storage_limit_gb": 10,
            "enabled_modules": ["Projects", "SOP"]
        }
        res = self.client.post('/api/licenses/', json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(data['license_key'].startswith('QCMS-'))

        # Verify database update
        updated_org = Organization.query.get(new_org.id)
        self.assertEqual(updated_org.subscription_plan, 'Professional')
        self.assertEqual(updated_org.subscription_status, 'Active')
        self.assertEqual(updated_org.max_users, 100)

    def test_status_actions(self):
        # Suspend
        res = self.client.post(f'/api/licenses/{self.org.id}/suspend', json={"reason": "Non-payment"}, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.org.subscription_status, 'Suspended')

        # Resume
        res = self.client.post(f'/api/licenses/{self.org.id}/resume', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.org.subscription_status, 'Active')

        # Regenerate Key
        old_key = self.org.license_number
        res = self.client.post(f'/api/licenses/{self.org.id}/regenerate-key', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertNotEqual(self.org.license_number, old_key)

        # Download License File
        res = self.client.get(f'/api/licenses/{self.org.id}/download', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue('content' in data)

        # Revoke
        res = self.client.post(f'/api/licenses/{self.org.id}/revoke', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.org.subscription_status, 'Revoked')

if __name__ == '__main__':
    unittest.main()
