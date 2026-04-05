from app import create_app
from app.models import db
from sqlalchemy import text

app = create_app()

def col_exists(conn, table, column):
    result = conn.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name=:t AND column_name=:c"
    ), {"t": table, "c": column})
    return result.fetchone() is not None

with app.app_context():
    with db.engine.connect() as conn:
        print("[QCMS] Checking for facilitator_id in projects table...")
        if not col_exists(conn, 'projects', 'facilitator_id'):
            print("[QCMS] Adding facilitator_id column...")
            # Use nullable=True consistently with existing optional fields
            conn.execute(text("ALTER TABLE projects ADD COLUMN facilitator_id INTEGER REFERENCES users(id)"))
            conn.commit()
            print("[OK] Column facilitator_id added to projects table.")
        else:
            print("[OK] Column facilitator_id already exists.")
