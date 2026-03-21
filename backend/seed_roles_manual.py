from app import create_app
from app.models import db
from app.routes.auth_routes import seed_roles

app = create_app()
with app.app_context():
    seed_roles()
    print("Roles seeded successfully!")
