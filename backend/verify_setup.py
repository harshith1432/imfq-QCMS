from app import create_app, db
from app.models import User, Role, Organization
from sqlalchemy import text

app = create_app()
with app.app_context():
    print("--- CHECKING DB ---")
    try:
        # Check if roles exist
        admin_role = Role.query.filter_by(name='Admin').first()
        if not admin_role:
            print("WARNING: 'Admin' role NOT found! Attempting to seed...")
            roles = ['Admin', 'Reviewer', 'Facilitator', 'Team Leader', 'Team Member']
            for r_name in roles:
                if not Role.query.filter_by(name=r_name).first():
                    db.session.add(Role(name=r_name))
            db.session.commit()
            print("Roles seeded.")
            admin_role = Role.query.filter_by(name='Admin').first()

        # Check for users
        users = User.query.all()
        print(f"Total Users: {len(users)}")
        for u in users:
            print(f"User: {u.username}, Email: {u.email}, Role: {u.role.name if u.role else 'NONE'}")
            
    except Exception as e:
        print(f"ERROR: {e}")
