from app import create_app
from app.infrastructure.database.models.models import User

app = create_app()
with app.app_context():
    users = User.query.all()
    print("USER LIST IN DATABASE:")
    for u in users:
        print(f"Username: {u.username}, Email: {u.email}, Created At: {u.created_at}, Last Login: {u.last_login}")
