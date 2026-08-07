from app import create_app, db
from app.infrastructure.database.models.models import User, Project
import json

app = create_app()
with app.app_context():
    user = User.query.filter_by(org_id=3).first()
    print(f"Testing Analytics API for User ID {user.id}, Org ID {user.org_id}...", flush=True)
    
    with app.test_client() as client:
        from flask_jwt_extended import create_access_token
        token = create_access_token(identity=user.id)
        
        res = client.get('/api/analytics/dashboard', headers={'Authorization': f'Bearer {token}'})
        print(f"HTTP Status: {res.status_code}", flush=True)
        data = res.get_json()
        summary = data.get('summary', {})
        print("\n=== ANALYTICS EXECUTIVE SUMMARY ===", flush=True)
        print(f"Total Projects: {summary.get('total_projects')}", flush=True)
        print(f"Closed Projects: {summary.get('closed_projects')}", flush=True)
        print(f"Active Projects: {summary.get('active_projects')}", flush=True)
        print(f"Total Cost Savings: ₹{summary.get('total_savings')}", flush=True)
        print(f"AVG DELIVERY TIME: {summary.get('avg_velocity')} Days", flush=True)
