from app import create_app, db
from app.models import Role, User
from app import bcrypt

app = create_app()

def seed():
    with app.app_context():
        # 1. Create Roles
        roles = ['Admin', 'Reviewer', 'Facilitator', 'Team Leader', 'Team Member']
        for r_name in roles:
            if not Role.query.filter_by(name=r_name).first():
                db.session.add(Role(name=r_name))
        db.session.commit()
        
        # 2. Create Default Admin
        if not User.query.filter_by(username='admin').first():
            admin_role = Role.query.filter_by(name='Admin').first()
            hashed_pw = bcrypt.generate_password_hash('admin123').decode('utf-8')
            admin = User(
                username='admin',
                email='admin@qcms.com',
                hashed_password=hashed_pw,
                role_id=admin_role.id,
                department='Core'
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created: admin / admin123")
        else:
            print("Admin user already exists")

if __name__ == "__main__":
    seed()
