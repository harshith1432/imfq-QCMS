from app import create_app, db
from app.models import User, Role, Department

app = create_app()
with app.app_context():
    print("--- ROLES ---")
    roles = Role.query.all()
    for r in roles:
        print(f"Role: {r.name} (ID: {r.id})")
        
    print("\n--- DEPARTMENTS ---")
    depts = Department.query.all()
    for d in depts:
        print(f"Dept: {d.name} (ID: {d.id})")
        
    print("\n--- USERS ---")
    users = User.query.all()
    for u in users:
        print(f"User: {u.username}, Email: {u.email}, Role ID: {u.role_id}, Dept ID: {u.department_id}")
