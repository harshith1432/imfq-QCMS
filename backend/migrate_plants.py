import os
import sys

from app import create_app
from app.infrastructure.database.models.models import db, Plant, Department, User, Organization
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("[QCMS Migration] Adding missing tables and columns for Plant Locations...")
    
    statements = [
        """CREATE TABLE IF NOT EXISTS plants (
            id SERIAL PRIMARY KEY,
            org_id INTEGER NOT NULL REFERENCES organizations(id),
            name VARCHAR(100) NOT NULL,
            code VARCHAR(50),
            location VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        "ALTER TABLE departments ADD COLUMN IF NOT EXISTS plant_id INTEGER REFERENCES plants(id);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS plant_id INTEGER REFERENCES plants(id);"
    ]

    for stmt in statements:
        try:
            db.session.execute(text(stmt))
            db.session.commit()
            print(f"[QCMS Migration] Executed DDL successfully.")
        except Exception as e:
            db.session.rollback()
            print(f"[QCMS Migration] DDL warning: {e}")

    # Now verify all organizations and create 'jain' plant
    orgs = Organization.query.all()
    for o in orgs:
        print(f"\nProcessing Organization ID {o.id} ({o.name})...")
        
        # Check if plant 'jain' already exists
        jain_plant = Plant.query.filter_by(org_id=o.id, name='jain').first()
        if not jain_plant:
            jain_plant = Plant(
                org_id=o.id,
                name='jain',
                code='ja 01',
                location='jainuniversity'
            )
            db.session.add(jain_plant)
            db.session.commit()
            print(f"  + Created new Plant 'jain' (ID: {jain_plant.id}, Code: ja 01, Location: jainuniversity)")
        else:
            print(f"  * Plant 'jain' exists (ID: {jain_plant.id})")

        # Map all existing departments to plant 'jain'
        depts = Department.query.filter_by(org_id=o.id).all()
        for d in depts:
            d.plant_id = jain_plant.id
            print(f"    - Assigned Department '{d.name}' (ID: {d.id}) -> Plant ID {jain_plant.id}")
        db.session.commit()

        # Map all existing users to plant 'jain'
        users = User.query.filter_by(org_id=o.id).all()
        for u in users:
            if not u.plant_id:
                u.plant_id = jain_plant.id
        db.session.commit()
        print(f"  + Assigned {len(users)} users to Plant 'jain'")

    print("\n[QCMS Migration] COMPLETED SUCCESSFULLY!")
