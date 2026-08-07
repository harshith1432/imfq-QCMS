from app import create_app
from app.infrastructure.database.models.models import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE platform_settings ADD COLUMN landing_cms_settings JSON;"))
        db.session.commit()
        print("Successfully added landing_cms_settings column.")
    except Exception as e:
        print(f"Error adding column (it might already exist): {e}")
