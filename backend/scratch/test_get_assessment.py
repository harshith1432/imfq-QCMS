import sys
import os

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from flask.testing import FlaskClient

app = create_app()

with app.test_client() as client:
    # 1. Login as reviewer
    login_res = client.post('/api/auth/login', json={
        'username': 'reviewer',
        'password': '123'  # Wait, is the password '123' or '123456'? Let's try '123456' which we just reset
    })
    print("Login Status:", login_res.status_code)
    print("Login JSON:", login_res.json)
    
    if login_res.status_code == 200:
        token = login_res.json.get('access_token')
        headers = {'Authorization': f'Bearer {token}'}
        
        # 2. Get SOP details
        sop_res = client.get('/api/sops/9', headers=headers)
        print("\nSOP 9 Details Status:", sop_res.status_code)
        if sop_res.status_code == 200:
            print("my_training:", sop_res.json.get('my_training'))
        else:
            print("SOP 9 Response:", sop_res.text)
            
        # 3. Get SOP assessment
        assess_res = client.get('/api/sops/9/assessment', headers=headers)
        print("\nSOP 9 Assessment Status:", assess_res.status_code)
        print("SOP 9 Assessment JSON:", assess_res.json)
    else:
        # Let's try with password '123456'
        login_res = client.post('/api/auth/login', json={
            'username': 'reviewer',
            'password': '123456'
        })
        print("Login with 123456 Status:", login_res.status_code)
        if login_res.status_code == 200:
            token = login_res.json.get('access_token')
            headers = {'Authorization': f'Bearer {token}'}
            sop_res = client.get('/api/sops/9', headers=headers)
            print("\nSOP 9 Details Status:", sop_res.status_code)
            if sop_res.status_code == 200:
                print("my_training:", sop_res.json.get('my_training'))
            else:
                print("SOP 9 Response:", sop_res.text)
            assess_res = client.get('/api/sops/9/assessment', headers=headers)
            print("\nSOP 9 Assessment Status:", assess_res.status_code)
            print("SOP 9 Assessment JSON:", assess_res.json)
