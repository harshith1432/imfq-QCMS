import os
import sys
from app import create_app
from app.infrastructure.database.models.models import db, User, Role

def verify():
    app = create_app()
    with app.app_context():
        sa_user = User.query.join(Role).filter(Role.name == 'SuperAdmin').first()
        if not sa_user:
            print("[ERROR] No SuperAdmin user found in database.")
            return

        print(f"[INFO] Using SuperAdmin user: {sa_user.email}")
        
        from flask_jwt_extended import create_access_token
        access_token = create_access_token(identity=str(sa_user.id))
        
        client = app.test_client()
        headers = {"Authorization": f"Bearer {access_token}"}

        # 1. Verify stats endpoint
        res = client.get('/api/v1/dashboard/stats', headers=headers)
        print("Stats Status Code:", res.status_code)
        print("Stats JSON:", res.get_json())
        assert res.status_code == 200
        assert res.get_json()['status'] == 'success'
        assert 'active_organizations' in res.get_json()['data']

        # 2. Verify search endpoint
        res = client.get('/api/v1/dashboard/search?q=Gu', headers=headers)
        print("Search Status Code:", res.status_code)
        print("Search JSON:", res.get_json())
        assert res.status_code == 200
        assert 'organizations' in res.get_json()

        # 3. Verify health endpoint
        res = client.get('/api/v1/dashboard/health', headers=headers)
        print("Health Status Code:", res.status_code)
        print("Health JSON:", res.get_json())
        assert res.status_code == 200
        assert 'api_latency' in res.get_json()

        # 4. Verify org list GET endpoint
        res = client.get('/api/v1/dashboard', headers=headers)
        print("Orgs List Status Code:", res.status_code)
        print("Orgs List JSON Meta:", res.get_json()['meta'])
        assert res.status_code == 200
        assert len(res.get_json()['data']) > 0

        print("[SUCCESS] All endpoints queryable, functioning, and compliant!")

if __name__ == '__main__':
    verify()
