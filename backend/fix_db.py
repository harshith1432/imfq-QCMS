import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app import create_app, db

app = create_app()
with app.app_context():
    try:
        db.session.execute(db.text("ALTER TABLE stage_1_identification ADD COLUMN is_approved BOOLEAN DEFAULT FALSE;"))
        db.session.commit()
        print("Added is_approved column successfully.")
    except Exception as e:
        db.session.rollback()
        print(f"Failed to add is_approved: {e}")

    try:
        db.session.execute(db.text("ALTER TABLE stage_1_identification ADD COLUMN tl_comments TEXT;"))
        db.session.commit()
        print("Added tl_comments column successfully.")
    except Exception as e:
        db.session.rollback()
        print(f"Failed to add tl_comments: {e}")
