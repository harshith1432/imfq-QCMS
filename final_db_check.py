import os
import sys
import traceback
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Base directory for the backend
BACKEND_DIR = r"d:\projects softwares\imfq\backend"
ENV_PATH = os.path.join(BACKEND_DIR, ".env")

# Load .env
load_dotenv(ENV_PATH)

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("DATABASE_URL not found in .env")
    exit(1)

# Mask password for display
print(f"Connecting to: {db_url.split('@')[-1]}")

try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT current_database();"))
        print(f"[QCMS] Connected to: {result.scalar()}")
        
        result = conn.execute(text("SELECT schema_name FROM information_schema.schemata;"))
        print(f"[QCMS] Schemas: {[r[0] for r in result]}")
except Exception:
    print("[QCMS] Database connection failed!")
    traceback.print_exc()
