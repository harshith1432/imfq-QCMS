import sys
import os

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, bcrypt
from app.infrastructure.database.models.models import db, User

app = create_app()

with app.app_context():
    usernames = ['reviewer', 'facilitator', 'team leader', 'team member ']
    hashed_pw = bcrypt.generate_password_hash('123456').decode('utf-8')
    
    for username in usernames:
        user = User.query.filter_by(username=username).first()
        if user:
            user.hashed_password = hashed_pw
            print(f"Reset password for user: {username}")
        else:
            print(f"User not found: {username}")
            
    db.session.commit()
    print("Done!")
