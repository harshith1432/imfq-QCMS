"""
One-shot migration: adds facilitator columns to existing tables.
Run once: python migrate_facilitator.py
"""
from app import create_app
from app.models import db
from sqlalchemy import text, inspect

app = create_app()

def col_exists(conn, table, column):
    result = conn.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name=:t AND column_name=:c"
    ), {"t": table, "c": column})
    return result.fetchone() is not None

with app.app_context():
    with db.engine.connect() as conn:
        added = []

        if not col_exists(conn, 'stage_3_rca', 'rca_validation_note'):
            conn.execute(text("ALTER TABLE stage_3_rca ADD COLUMN rca_validation_note TEXT"))
            added.append('stage_3_rca.rca_validation_note')

        if not col_exists(conn, 'stage_7_impact', 'status'):
            conn.execute(text("ALTER TABLE stage_7_impact ADD COLUMN status VARCHAR(20) DEFAULT 'Pending'"))
            added.append('stage_7_impact.status')

        if not col_exists(conn, 'stage_7_impact', 'approved_by'):
            conn.execute(text("ALTER TABLE stage_7_impact ADD COLUMN approved_by INTEGER REFERENCES users(id)"))
            added.append('stage_7_impact.approved_by')

        conn.commit()

    if added:
        print(f"[OK] Added columns: {', '.join(added)}")
    else:
        print("[OK] All columns already exist — no changes needed.")
