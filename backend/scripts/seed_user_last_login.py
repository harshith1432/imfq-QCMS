from app import create_app, db
from app.infrastructure.database.models.models import User
from datetime import datetime

app = create_app()
with app.app_context():
    try:
        users = User.query.all()
        updated_count = 0
        for u in users:
            if u.last_login is None:
                u.last_login = u.created_at or datetime.utcnow()
                updated_count += 1
        db.session.commit()
        print(f"SUCCESS: Seeded last_login timestamp for {updated_count} users.")
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: {e}")
