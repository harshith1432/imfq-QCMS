import sys
from app import create_app
from app.domain.services.feature_engine import FeatureEngine
from app.infrastructure.database.models.models import Organization

def main():
    app = create_app()
    with app.app_context():
        FeatureEngine.invalidate()
        orgs = Organization.query.all()
        print("=== TESTING FIX FOR ALL ORGANIZATIONS ===", flush=True)
        for o in orgs:
            flags = FeatureEngine.get_all_flags(o.id)
            view_user_flag = flags.get('users.view') or flags.get('View Users')
            print(f"Org ID: {o.id}, Name: '{o.name}', Sub Plan: '{o.subscription_plan}' => View Users Enabled: {view_user_flag}", flush=True)

if __name__ == '__main__':
    main()
