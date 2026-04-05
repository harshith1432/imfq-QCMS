import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print("No DATABASE_URL found.")
    exit(1)

try:
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cursor = conn.cursor()
    
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN profile_picture VARCHAR(255);')
        print("profile_picture column added.")
    except Exception as e:
        print(f"profile_picture error (might already exist): {e}")

    try:
        cursor.execute('ALTER TABLE users ADD COLUMN banner_image VARCHAR(255);')
        print("banner_image column added.")
    except Exception as e:
        print(f"banner_image error (might already exist): {e}")
        
    cursor.close()
    conn.close()
    print("Migration complete via psycopg2.")
except Exception as e:
    print(f"Connection error: {e}")
