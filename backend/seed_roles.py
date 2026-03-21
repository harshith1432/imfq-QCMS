from app import create_app, db
from app.models import Role

def seed_roles():
    app = create_app()
    with app.app_context():
        roles = ['Admin', 'Reviewer', 'Facilitator', 'Team Leader', 'Team Member']
        for role_name in roles:
            role = Role.query.filter_by(name=role_name).first()
            if not role:
                db.session.add(Role(name=role_name))
                print(f"Added role: {role_name}")
        db.session.commit()
        print("Roles seeded successfully.")

if __name__ == "__main__":
    seed_roles()
