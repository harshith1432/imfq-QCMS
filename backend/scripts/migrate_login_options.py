from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS login_options JSONB DEFAULT '[\"email\"]'::jsonb;"))
        db.session.commit()
        print("SUCCESS: login_options column added to organizations table")
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: {e}")
