from app import create_app
from app.infrastructure.database.models.models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    engine = db.engine
    with engine.connect() as conn:
        # Add gst_number
        try:
            conn.execute(text("ALTER TABLE organizations ADD COLUMN gst_number VARCHAR(50)"))
            conn.commit()
            print("Added gst_number column.")
        except Exception as e:
            print("gst_number column might already exist:", e)
            
        # Add license_start_date
        try:
            conn.execute(text("ALTER TABLE organizations ADD COLUMN license_start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
            conn.commit()
            print("Added license_start_date column.")
        except Exception as e:
            print("license_start_date column might already exist:", e)

        # Add license_expiry_date
        try:
            conn.execute(text("ALTER TABLE organizations ADD COLUMN license_expiry_date TIMESTAMP"))
            conn.commit()
            print("Added license_expiry_date column.")
        except Exception as e:
            print("license_expiry_date column might already exist:", e)

        # Add storage_used_mb
        try:
            conn.execute(text("ALTER TABLE organizations ADD COLUMN storage_used_mb FLOAT DEFAULT 0.0"))
            conn.commit()
            print("Added storage_used_mb column.")
        except Exception as e:
            print("storage_used_mb column might already exist:", e)
            
        # Update existing records to have default license start/expiry dates if null
        try:
            conn.execute(text("UPDATE organizations SET license_start_date = created_at WHERE license_start_date IS NULL"))
            conn.execute(text("UPDATE organizations SET license_expiry_date = (created_at + interval '365 days') WHERE license_expiry_date IS NULL"))
            conn.execute(text("UPDATE organizations SET storage_used_mb = 0.0 WHERE storage_used_mb IS NULL"))
            conn.commit()
            print("Updated existing organization records.")
        except Exception as e:
            print("Error updating existing records:", e)
