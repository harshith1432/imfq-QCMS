from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    # Find users who are not verified and not using a temporary password
    # These users are currently "locked" out by the login logic 403 error
    users_to_fix = User.query.filter_by(is_verified=False, is_temp_password=False).all()
    
    if not users_to_fix:
        print("No locked users found.")
    else:
        print(f"Found {len(users_to_fix)} locked users. Fixing now...")
        for user in users_to_fix:
            print(f"Unlocking user: {user.username} ({user.email})")
            user.is_verified = True
            db.session.add(user)
        
        db.session.commit()
        print("Database update complete. All identified users have been verified.")

    # Also check if any users with is_temp_password=True are NOT verified (they should be allowed to login to reset)
    temp_pass_users = User.query.filter_by(is_temp_password=True, is_verified=False).all()
    if temp_pass_users:
        print(f"Note: Found {len(temp_pass_users)} users with temporary passwords who are unverified.")
        print("These users will now be able to log in to reset their password after the backend logic fix.")
