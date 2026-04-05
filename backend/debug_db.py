from app import create_app, db
from app.models import User
import os

app = create_app()
with app.app_context():
    users = User.query.all()
    print(f"{'Username':<20} | {'Verified':<8} | {'Temp PW':<8} | {'Active':<6} | {'Hash'}")
    print("-" * 75)
    for u in users:
        print(f"{u.username:<20} | {str(u.is_verified):<8} | {str(u.is_temp_password):<8} | {str(u.is_active):<6} | {u.hashed_password[:15]}...")
