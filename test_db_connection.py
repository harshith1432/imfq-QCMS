import os
from dotenv import load_dotenv
import psycopg2

def test_connection():
    # Load .env
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'backend', '.env')
    load_dotenv(dotenv_path)
    
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("Error: DATABASE_URL not found in .env")
        return
    
    print(f"Testing URL: {db_url.split('@')[-1]}")
    
    try:
        conn = psycopg2.connect(db_url)
        print("Success: Successfully connected to the database!")
        conn.close()
    except Exception as e:
        print(f"FAILED: Connection failed: {e}")

if __name__ == "__main__":
    test_connection()
