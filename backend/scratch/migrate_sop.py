import os
import sys
from dotenv import load_dotenv

# Add backend root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

from app import create_app, db

app = create_app()

with app.app_context():
    print("[QCMS] Creating new tables for SOP Management...")
    # Executing raw SQL to ensure exact constraints and avoid SQLAlchemy metadata issues
    try:
        with db.engine.connect() as conn:
            # Create sops table
            conn.execute(db.text("""
            CREATE TABLE IF NOT EXISTS sops (
                id SERIAL PRIMARY KEY,
                sop_uid VARCHAR(50) UNIQUE NOT NULL,
                org_id INTEGER REFERENCES organizations(id) NOT NULL,
                title VARCHAR(255) NOT NULL,
                category VARCHAR(100) NOT NULL,
                department_id INTEGER REFERENCES departments(id),
                process_name VARCHAR(255),
                sop_type VARCHAR(100),
                description TEXT,
                purpose TEXT,
                scope TEXT,
                applicability TEXT,
                responsibilities TEXT,
                owner_id INTEGER REFERENCES users(id),
                author_id INTEGER REFERENCES users(id),
                reviewer_id INTEGER REFERENCES users(id),
                approver_id INTEGER REFERENCES users(id),
                effective_date DATE,
                review_date DATE,
                expiry_date DATE,
                version INTEGER DEFAULT 1,
                status VARCHAR(50) DEFAULT 'Draft',
                project_id INTEGER REFERENCES projects(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                attachments JSON
            );
            """))
            print("  - Table 'sops' verified/created.")

            # Create sop_steps table
            conn.execute(db.text("""
            CREATE TABLE IF NOT EXISTS sop_steps (
                id SERIAL PRIMARY KEY,
                sop_id INTEGER REFERENCES sops(id) ON DELETE CASCADE NOT NULL,
                step_number INTEGER NOT NULL,
                step_title VARCHAR(255) NOT NULL,
                instructions TEXT NOT NULL,
                image_path VARCHAR(500),
                video_path VARCHAR(500),
                safety_notes TEXT,
                quality_checkpoints TEXT
            );
            """))
            print("  - Table 'sop_steps' verified/created.")

            # Create sop_approvals table
            conn.execute(db.text("""
            CREATE TABLE IF NOT EXISTS sop_approvals (
                id SERIAL PRIMARY KEY,
                sop_id INTEGER REFERENCES sops(id) ON DELETE CASCADE NOT NULL,
                user_id INTEGER REFERENCES users(id) NOT NULL,
                role VARCHAR(50) NOT NULL,
                action VARCHAR(50) NOT NULL,
                comments TEXT,
                signature VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """))
            print("  - Table 'sop_approvals' verified/created.")

            # Create sop_versions table
            conn.execute(db.text("""
            CREATE TABLE IF NOT EXISTS sop_versions (
                id SERIAL PRIMARY KEY,
                sop_id INTEGER REFERENCES sops(id) ON DELETE CASCADE NOT NULL,
                version_number INTEGER NOT NULL,
                changes_made TEXT,
                changed_by_id INTEGER REFERENCES users(id) NOT NULL,
                changed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approval_date TIMESTAMP,
                sop_data JSON
            );
            """))
            print("  - Table 'sop_versions' verified/created.")

            # Create sop_training table
            conn.execute(db.text("""
            CREATE TABLE IF NOT EXISTS sop_training (
                id SERIAL PRIMARY KEY,
                sop_id INTEGER REFERENCES sops(id) ON DELETE CASCADE NOT NULL,
                user_id INTEGER REFERENCES users(id) NOT NULL,
                assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                read_status BOOLEAN DEFAULT FALSE,
                acknowledgement_status BOOLEAN DEFAULT FALSE,
                training_completion_status BOOLEAN DEFAULT FALSE,
                assessment_score INTEGER,
                completed_at TIMESTAMP
            );
            """))
            print("  - Table 'sop_training' verified/created.")
            
            # Commit changes
            conn.commit()

        print("[QCMS] SOP Management tables migration successful!")
    except Exception as e:
        print(f"[QCMS] Error running SOP migration: {e}")
        sys.exit(1)
