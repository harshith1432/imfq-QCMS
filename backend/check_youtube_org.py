from app import create_app, db
from app.infrastructure.database.models.models import Organization, Subscription, SaaSPlan, SaaSPlanModules, Module, User
from app.domain.services.feature_engine import FeatureEngine

app = create_app()
with app.app_context():
    out = []
    out.append("=== CHECKING ALL USERS & ORGS ===")
    users = User.query.all()
    for u in users:
        if u.org:
            sub = Subscription.query.filter_by(org_id=u.org_id, subscription_status='Active').first()
            sub_plan = sub.plan_name if sub else 'None'
            out.append(f"User: '{u.username}' ({u.email}), Role: '{u.role.name if u.role else 'N/A'}', Org ID: {u.org_id}, Org Name: '{u.org.name}', Plan in Org: '{u.org.subscription_plan}', Active Sub: '{sub_plan}'")

    out.append("\n=== SAAS PLAN 'test' & OTHER PLANS DETAILS ===")
    plans = SaaSPlan.query.all()
    for pt in plans:
        mods = SaaSPlanModules.query.filter_by(plan_id=pt.id, is_enabled=True).all()
        out.append(f"\nPlan ID: {pt.id}, Name: '{pt.name}', Plan Type: '{pt.plan_type}', Modules Count: {len(mods)}")
        mod_names = [m.module_name for m in mods]
        out.append(f"Modules: {mod_names[:25]}")
        
        has_users = any(x.lower() in [m.lower() for m in mod_names] for x in ['users.view', 'View Users', 'users', 'IAM', 'User Management'])
        out.append(f"Contains User Management / View Users? {has_users}")

    out.append("\n=== SYSTEM CORE MODULES & IAM MODULES ===")
    iam_mods = Module.query.filter((Module.category == 'IAM') | (Module.code.startswith('users'))).all()
    for im in iam_mods:
        out.append(f"ID: {im.id}, Code: '{im.code}', Name: '{im.name}', SystemMod: {im.system_module}, ParentID: {im.parent_id}, Status: '{im.status}', MinPlan: '{im.minimum_plan}'")

    with open("org_report_final.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("Report written successfully to org_report_final.txt")
