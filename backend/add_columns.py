import psycopg2
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get('DATABASE_URL')
if not url:
    url = "postgresql://postgres:Harshith%401432@127.0.0.1:5432/imfq_db"

print("Connecting to:", url.replace("Harshith%401432", "PASSWORD"))
try:
    conn = psycopg2.connect(url)
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE stage_1_identification ADD COLUMN is_approved BOOLEAN DEFAULT FALSE;")
    print("is_approved added")
except Exception as e:
    print("Error 1:", e)

try:
    cursor.execute("ALTER TABLE stage_1_identification ADD COLUMN tl_comments TEXT;")
    print("tl_comments added")
except Exception as e:
    print("Error 2:", e)

if 'conn' in locals():
    conn.close()
