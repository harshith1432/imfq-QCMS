from app import create_app
from app.models import db
from sqlalchemy import text, inspect

app = create_app()
with app.app_context():
    insp = inspect(db.engine)
    
    tables = ['stage_7_impact', 'stage_3_rca', 'facilitator_notes']
    for table in tables:
        if table in insp.get_table_names():
            cols = [c['name'] for c in insp.get_columns(table)]
            print(f"Table {table} columns: {cols}")
        else:
            print(f"Table {table} does NOT exist!")
