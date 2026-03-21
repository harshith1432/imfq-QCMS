from app import create_app, db
from app.models import User, Role, Organization

app = create_app()
with app.app_context():
    print("--- ROLES ---")
    roles = Role.query.all()
    for r in roles:
        print(f"ID: {r.id}, Name: {r.name}")
    
    print("\n--- USERS ---")
    users = User.query.all()
    if not users:
        print("No users found.")
    for u in users:
        print(f"ID: {u.id}, Username: {u.username}, Email: {u.email}, Org: {u.org_id}, Role ID: {u.role_id}")
    
    print("\n--- ORGANIZATIONS ---")
    orgs = Organization.query.all()
    for o in orgs:
        print(f"ID: {o.id}, Name: {o.name}, Email: {o.email}")
