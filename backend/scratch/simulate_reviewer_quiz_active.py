import sys
import os

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.infrastructure.database.models.models import db, Project

app = create_app()

# Set project status to Active
with app.app_context():
    proj = Project.query.get(33)
    if proj:
        proj.status = 'Active'
        db.session.commit()
        print("Project 33 status set to Active")

try:
    with app.test_client() as client:
        # 1. Login as reviewer
        login_res = client.post('/api/auth/login', json={
            'username': 'reviewer',
            'password': '123456'
        })
        token = login_res.json.get('access_token')
        headers = {'Authorization': f'Bearer {token}'}
        
        # 2. Get SOP details (should succeed now with status 200!)
        sop_res = client.get('/api/sops/9', headers=headers)
        print("SOP 9 Details Status (when project is Active):", sop_res.status_code)
        
        # 3. Track reading (5 seconds, 100% scroll)
        track_res = client.post('/api/sops/training/33/track', json={
            'reading_time': 6,
            'reading_percentage': 100.0
        }, headers=headers)
        print("Track reading status:", track_res.status_code)
        
        # 4. Acknowledge training
        ack_res = client.post('/api/sops/training/33/acknowledge', json={
            'digital_signature': 'Reviewer User',
            'employee_id': 'EMP-REV-01'
        }, headers=headers)
        print("Acknowledge status:", ack_res.status_code)
        
        # 5. Get assessment questions
        assess_res = client.get('/api/sops/9/assessment', headers=headers)
        print("Assessment questions status:", assess_res.status_code)
        
        # 6. Submit assessment answers
        submit_res = client.post('/api/sops/training/33/assessment/submit', json={
            'answers': [
                {
                    'question_id': 21,
                    'answers': ['test']
                }
            ]
        }, headers=headers)
        print("Submit assessment status:", submit_res.status_code)
        print("Submit assessment JSON:", submit_res.json)
        
        # 7. Login as facilitator (user 7) to check if trainings list contains the score
        login_fac = client.post('/api/auth/login', json={
            'username': 'facilitator',
            'password': '123456'
        })
        token_fac = login_fac.json.get('access_token')
        headers_fac = {'Authorization': f'Bearer {token_fac}'}
        
        sop_fac_res = client.get('/api/sops/9', headers=headers_fac)
        print("SOP Details (Facilitator) status:", sop_fac_res.status_code)
        for t in sop_fac_res.json.get('trainings', []):
            if t.get('employee_name') == 'reviewer':
                print(f"Verified Facilitator Table - Employee: {t.get('employee_name')}, Status: {t.get('status')}, Score: {t.get('assessment_score')}")

finally:
    # Revert project status to Closed
    with app.app_context():
        proj = Project.query.get(33)
        if proj:
            proj.status = 'Closed'
            db.session.commit()
            print("Project 33 status reverted to Closed")
