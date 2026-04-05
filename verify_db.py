import sys
import os

# Adjust sys.path to include the backend directory
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app import create_app, db
from app.models import User, Role, Organization, Department

app = create_app()
with app.app_context():
    print("--- ROLES ---")
    roles = Role.query.all()
    for r in roles:
        print(f"ID: {r.id}, Name: '{r.name}'")
    
    print("\n--- USERS ---")
    users = User.query.all()
    for u in users:
        role_name = u.role.name if u.role else "No Role"
        print(f"ID: {u.id}, Username: '{u.username}', Role: '{role_name}', Name: '{u.full_name}'")

    print("\n--- DEPARTMENTS ---")
    depts = Department.query.all()
    for d in depts:
        print(f"ID: {d.id}, Name: '{d.name}'")
