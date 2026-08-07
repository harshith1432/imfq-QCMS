import sys
import os

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.infrastructure.database.models.models import db, Project

app = create_app()

with app.app_context():
    # Set project 33 status to 'Active'
    proj = Project.query.get(33)
    if proj:
        proj.status = 'Active'
        db.session.commit()
        print("Project 33 status set to Active")

with app.test_client() as client:
    # Login as reviewer
    login_res = client.post('/api/auth/login', json={
        'username': 'reviewer',
        'password': '123456'
    })
    token = login_res.json.get('access_token')
    headers = {'Authorization': f'Bearer {token}'}
    
    # Get SOP details
    sop_res = client.get('/api/sops/9', headers=headers)
    print("SOP 9 Details Status (when project is Active):", sop_res.status_code)
    if sop_res.status_code == 200:
        print("Success! Details loaded.")
    else:
        print("Failed! Status code:", sop_res.status_code, "Response:", sop_res.text)

with app.app_context():
    # Revert project 33 status to 'Closed'
    proj = Project.query.get(33)
    if proj:
        proj.status = 'Closed'
        db.session.commit()
        print("Project 33 status reverted to Closed")
