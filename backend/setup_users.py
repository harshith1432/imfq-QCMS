import os
from app import create_app, db, bcrypt
from app.models import User, Role, Department

app = create_app()
with app.app_context():
    # 0. Load credentials from environment
    admin_user = os.getenv('ADMIN_USERNAME', 'admin')
    admin_pass = os.getenv('ADMIN_PASSWORD', 'admin123')

    # 1. Ensure roles exist
    roles_list = ['Admin', 'Reviewer', 'Facilitator', 'Team Leader', 'Team Member']
    role_objs = {}
    for r_name in roles_list:
        role = Role.query.filter_by(name=r_name).first()
        if not role:
            role = Role(name=r_name)
            db.session.add(role)
            db.session.commit()
        role_objs[r_name] = role

    # 2. Ensure default department exists
    dept_name = 'Quality Assurance'
    dept = Department.query.filter_by(name=dept_name).first()
    if not dept:
        dept = Department(name=dept_name)
        db.session.add(dept)
        db.session.commit()

    # 3. Create users
    users_data = [
        (admin_user, 'admin@example.com', admin_pass, 'Admin'),
        ('reviewer', 'reviewer@example.com', 'reviewer123', 'Reviewer'),
        ('facilitator', 'facilitator@example.com', 'facilitator123', 'Facilitator'),
        ('teamleader', 'teamleader@example.com', 'leader123', 'Team Leader'),
        ('member', 'member@example.com', 'member123', 'Team Member')
    ]

    for username, email, password, role_name in users_data:
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(
                username=username,
                email=email,
                hashed_password=bcrypt.generate_password_hash(password).decode('utf-8'),
                role_id=role_objs[role_name].id,
                department_id=dept.id
            )
            db.session.add(user)
            print(f"Created user: {username} with role {role_name}")
        else:
            # Update role, password and department if exists
            user.role_id = role_objs[role_name].id
            user.department_id = dept.id
            user.hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            print(f"Updated user: {username}")
    
    db.session.commit()
    print("Setup complete.")
