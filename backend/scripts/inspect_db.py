import sys
import os

with open("output.txt", "w", encoding="utf-8") as f:
    sys.stdout = f
    sys.stderr = f
    try:
        from app import create_app, db
        from app.infrastructure.database.models.models import Organization, Subscription, SaaSPlan, SaaSPlanModules, Module
        from app.domain.services.feature_engine import FeatureEngine

        app = create_app()
        with app.app_context():
            print("=== ORGANIZATIONS ===")
            orgs = Organization.query.all()
            for o in orgs:
                sub = Subscription.query.filter_by(org_id=o.id, subscription_status='Active').first()
                sub_plan = sub.plan_name if sub else 'None'
                print(f"Org ID: {o.id}, Name: '{o.name}', Org Sub Plan: '{o.subscription_plan}', Active Sub Plan: '{sub_plan}', EnabledMods: {o.enabled_modules}")
                
                flags = FeatureEngine.get_all_flags(o.id)
                details = FeatureEngine.get_all_details(o.id)
                print(f"  Total Flags evaluated: {len(flags)}")
                print(f"  users.view flag: {flags.get('users.view')} (Detail: {details.get('users.view')})")
                print(f"  View Users flag: {flags.get('View Users')} (Detail: {details.get('View Users')})")
                print(f"  users.view_users flag: {flags.get('users.view_users')}")

            print("\n=== SAAS PLANS & MODULES ===")
            plans = SaaSPlan.query.all()
            for p in plans:
                mods = SaaSPlanModules.query.filter_by(plan_id=p.id, is_enabled=True).all()
                mod_names = [m.module_name for m in mods]
                print(f"\nPlan ID: {p.id}, Name: '{p.name}', Plan Type: '{p.plan_type}', Enabled Count: {len(mods)}")
                print(f"Enabled Module Names: {mod_names[:40]}")

            print("\n=== SEARCH 'View Users' or 'users' in MODULES TABLE ===")
            user_mods = Module.query.filter(Module.name.ilike('%user%') | Module.code.ilike('%user%')).all()
            for m in user_mods:
                print(f"Mod ID: {m.id}, Name: '{m.name}', Code: '{m.code}', Category: '{m.category}', Min Plan: '{m.minimum_plan}', Status: '{m.status}'")
    except Exception as e:
        import traceback
        traceback.print_exc(file=f)
