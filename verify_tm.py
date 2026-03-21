import os
import sys

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from app import create_app
from app.models import db, User, Role, Project, ProjectMember, ProjectWorkflow
from flask_jwt_extended import create_access_token
import json
import uuid

app = create_app()
app.config['TESTING'] = True

def run_tests():
    with app.app_context():
        print("--- Starting Team Member Verification ---")
        client = app.test_client()

        # 1. Setup Data
        uid = uuid.uuid4().hex[:6]
        print(f"Generating mock data with uid {uid}...")
        admin_role = Role.query.filter_by(name='Admin').first() or Role(name='Admin')
        tl_role = Role.query.filter_by(name='Team Leader').first() or Role(name='Team Leader')
        tm_role = Role.query.filter_by(name='Team Member').first() or Role(name='Team Member')
        db.session.add_all([admin_role, tl_role, tm_role])
        db.session.commit()
        
        tl = User(username=f'tl_{uid}', email=f'tl_{uid}@test.com', hashed_password='pass', role_id=tl_role.id, department_id=1)
        tm1 = User(username=f'tm1_{uid}', email=f'tm1_{uid}@test.com', hashed_password='pass', role_id=tm_role.id, department_id=1)
        tm2 = User(username=f'tm2_{uid}', email=f'tm2_{uid}@test.com', hashed_password='pass', role_id=tm_role.id, department_id=1)
        db.session.add_all([tl, tm1, tm2])
        db.session.commit()
        
        p1 = Project(project_uid=f'A-{uid}', title=f"Project A {uid}", department_id=1, creator_id=tl.id, current_stage=1)
        p2 = Project(project_uid=f'B-{uid}', title=f"Project B {uid}", department_id=1, creator_id=tl.id, current_stage=5)
        db.session.add_all([p1, p2])
        db.session.commit()

        # Assign tm1 to p1, and tm2 to p2
        db.session.add(ProjectMember(project_id=p1.id, user_id=tm1.id))
        db.session.add(ProjectMember(project_id=p2.id, user_id=tm2.id))
        db.session.commit()

        token_tm1 = create_access_token(identity=str(tm1.id), additional_claims={"role": "Team Member"})
        token_tm2 = create_access_token(identity=str(tm2.id), additional_claims={"role": "Team Member"})
        
        headers_tm1 = {"Authorization": f"Bearer {token_tm1}", "Content-Type": "application/json"}
        headers_tm2 = {"Authorization": f"Bearer {token_tm2}", "Content-Type": "application/json"}

        # Test 1: Accessing unassigned project should 403
        print("Test 1: Accessing unassigned project workspace...")
        res = client.get(f'/api/team-member/projects/{p2.id}', headers=headers_tm1)
        assert res.status_code == 403, f"Expected 403, got {res.status_code}"
        print("  ✓ Passed: Unassigned member blocked (403)")

        # Test 2: Accessing assigned project should 200
        print("Test 2: Accessing assigned project workspace...")
        res = client.get(f'/api/team-member/projects/{p1.id}', headers=headers_tm1)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        assert 'uid' in res.json
        print("  ✓ Passed: Assigned member allowed (200)")

        # Test 3: Updating Stage 1 on assigned project should 200
        print("Test 3: Updating assigned project stage...")
        payload = {"project_id": p1.id, "data": {"problem_statement": "Broken Widget"}}
        res = client.post('/api/team-member/stage/1/update', headers=headers_tm1, json=payload)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.json}"
        print("  ✓ Passed: Stage 1 update allowed (200)")

        # Test 4: Updating Stage 5 (Reviewer only) should 403
        print("Test 4: TM trying to update Stage 5...")
        payload5 = {"project_id": p2.id, "data": {"reviewer_comments": "Approved!"}}
        res = client.post('/api/team-member/stage/5/update', headers=headers_tm2, json=payload5)
        assert res.status_code == 403, f"Expected 403, got {res.status_code}"
        print("  ✓ Passed: Stage 5 update blocked for TM (403)")
        
        print("\nAll integration & security tests passed successfully!")

if __name__ == "__main__":
    run_tests()
