import sys
import os

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app

app = create_app()

with app.test_client() as client:
    # 1. Login as reviewer
    login_res = client.post('/api/auth/login', json={
        'username': 'reviewer',
        'password': '123456'
    })
    token = login_res.json.get('access_token')
    headers = {'Authorization': f'Bearer {token}'}
    
    # 2. Track reading (5 seconds, 100% scroll)
    track_res = client.post('/api/sops/training/33/track', json={
        'reading_time': 6,
        'reading_percentage': 100.0
    }, headers=headers)
    print("Track reading status:", track_res.status_code)
    print("Track reading JSON:", track_res.json)
    
    # 3. Acknowledge training
    ack_res = client.post('/api/sops/training/33/acknowledge', json={
        'digital_signature': 'Reviewer User',
        'employee_id': 'EMP-REV-01'
    }, headers=headers)
    print("\nAcknowledge status:", ack_res.status_code)
    print("Acknowledge JSON:", ack_res.json)
    
    # 4. Get assessment questions
    assess_res = client.get('/api/sops/9/assessment', headers=headers)
    print("\nAssessment questions status:", assess_res.status_code)
    print("Assessment questions JSON:", assess_res.json)
    
    # 5. Submit assessment answers
    submit_res = client.post('/api/sops/training/33/assessment/submit', json={
        'answers': [
            {
                'question_id': 21,
                'answers': ['test']
            }
        ]
    }, headers=headers)
    print("\nSubmit assessment status:", submit_res.status_code)
    print("Submit assessment JSON:", submit_res.json)
    
    # 6. Fetch SOP Details as reviewer to see if my_training is updated
    sop_res = client.get('/api/sops/9', headers=headers)
    print("\nSOP Details my_training status:", sop_res.status_code)
    print("my_training:", sop_res.json.get('my_training'))
    
    # 7. Login as facilitator (user 7) to check if trainings list contains the score
    login_fac = client.post('/api/auth/login', json={
        'username': 'facilitator',
        'password': '123456'
    })
    token_fac = login_fac.json.get('access_token')
    headers_fac = {'Authorization': f'Bearer {token_fac}'}
    
    sop_fac_res = client.get('/api/sops/9', headers=headers_fac)
    print("\nSOP Details (Facilitator) status:", sop_fac_res.status_code)
    print("Trainings list:")
    for t in sop_fac_res.json.get('trainings', []):
        print(f"Employee: {t.get('employee_name')}, Status: {t.get('status')}, Score: {t.get('assessment_score')}")
