"""
One-shot migration: adds missing columns to stage_8_implementation table.
Run once: python migrate_stage8_columns.py

Adds:
  - cost_savings (FLOAT, default 0.0)
  - impact_vouchers (JSON)
  - status (VARCHAR(30), default 'Pending')
  - approved_by (INTEGER, FK -> users.id)
"""
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

TABLE = 'stage_8_implementation'

COLUMNS = [
    ("cost_savings",      "FLOAT DEFAULT 0.0"),
    ("productivity_gain", "FLOAT DEFAULT 0.0"),
    ("impact_vouchers",   "JSON"),
    ("status",            "VARCHAR(30) DEFAULT 'Pending'"),
    ("approved_by",       "INTEGER REFERENCES users(id)"),
]

with app.app_context():
    with db.engine.connect() as conn:
        added = []

        for col_name, col_def in COLUMNS:
            if not col_exists(conn, TABLE, col_name):
                conn.execute(text(f"ALTER TABLE {TABLE} ADD COLUMN {col_name} {col_def}"))
                added.append(f"{TABLE}.{col_name}")
                print(f"  + Added {TABLE}.{col_name}")
            else:
                print(f"  ~ {TABLE}.{col_name} already exists — skipping")

        conn.commit()

    if added:
        print(f"\n[OK] Migration complete. Added {len(added)} column(s): {', '.join(added)}")
    else:
        print("\n[OK] All columns already exist — no changes needed.")
