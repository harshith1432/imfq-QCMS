import psycopg2

db_url = "postgresql://postgres:Harshith%401432@127.0.0.1:5432/imfq_db"

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    cur.execute("SELECT u.id, u.username, u.email, r.name FROM users u JOIN roles r ON u.role_id = r.id;")
    users = cur.fetchall()
    print("--- USERS ---")
    for u in users:
        print(f"ID: {u[0]}, Username: {u[1]}, Email: {u[2]}, Role: {u[3]}")
        
    cur.close()
    conn.close()
except Exception as e:
    print("Error:", e)
