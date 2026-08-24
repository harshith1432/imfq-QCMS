import sys

def main():
    with open("trend_out.txt", "w") as out_f:
        try:
            from app import create_app, db
            from app.infrastructure.database.models.models import User, Project
            app = create_app()
            with app.app_context():
                user = User.query.filter_by(org_id=3).first()
                if not user:
                    out_f.write("User with org_id=3 not found in database. Skipping.\n")
                    return
                out_f.write(f"Testing Analytics API Trends for User ID {user.id}, Org ID {user.org_id}...\n")
                
                with app.test_client() as client:
                    from flask_jwt_extended import create_access_token
                    token = create_access_token(identity=user.id)
                    
                    res = client.get('/api/analytics/dashboard', headers={'Authorization': f'Bearer {token}'})
                    data = res.get_json()
                    trends = data.get('trends', [])
                    summary = data.get('summary', {})
                    
                    out_f.write("\n=== EXECUTIVE SUMMARY KPI CARDS ===\n")
                    out_f.write(f"Total Projects: {summary.get('total_projects')}\n")
                    out_f.write(f"Completed Projects: {summary.get('closed_projects')}\n")
                    out_f.write(f"Active Projects: {summary.get('active_projects')}\n")
                    
                    out_f.write("\n=== REAL-TIME PROJECT GROWTH & VELOCITY TRENDS ===\n")
                    for t in trends:
                        out_f.write(f"Month: {t.get('month')} => Completed: {t.get('completed')}, Active: {t.get('active')}, Total: {t.get('projects')}\n")
        except Exception as e:
            out_f.write(str(e))

if __name__ == '__main__':
    main()
