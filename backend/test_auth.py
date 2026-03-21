from app import create_app, db, bcrypt
from app.models import User, Role

app = create_app()
with app.app_context():
    # 1. verify test user exists and has right password
    u = User.query.filter_by(username='admintestuser').first()
    if u:
        u.hashed_password = bcrypt.generate_password_hash('password123').decode('utf-8')
        db.session.commit()
        print(f"User: {u.username}, Email: {u.email}, Role: {u.role.name} - Password Reset Successful")
    else:
        print("User admintestuser not found")

    # 2. verify login with email
    email = 'test@example.com'
    password = 'password123'
    user = User.query.filter(
        (User.username.ilike(email)) | 
        (User.email.ilike(email))
    ).first()
    
    if user:
        if bcrypt.check_password_hash(user.hashed_password, password):
            print(f"LOGIN SUCCESS with {email}")
        else:
            print(f"LOGIN FAILED (wrong password) with {email}")
    else:
        print(f"LOGIN FAILED (user not found) with {email}")

    # 3. List all users and roles
    print("\nCurrent Users:")
    for u in User.query.all():
        print(f"- {u.username} ({u.email}) : {u.role.name}")
