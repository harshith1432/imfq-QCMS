import psycopg2

db_url = "postgresql://postgres:Harshith%401432@127.0.0.1:5432/imfq_db"

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    print("--- USERS AND ORG IDS ---")
    cur.execute("SELECT u.id, u.username, u.org_id, o.name FROM users u JOIN organizations o ON u.org_id = o.id;")
    users = cur.fetchall()
    for u in users:
        print(f"User ID: {u[0]}, Username: {u[1]}, Org ID: {u[2]}, Org Name: {u[3]}")
        
    print("\n--- SOPS AND ORG IDS ---")
    cur.execute("SELECT s.id, s.title, s.org_id FROM sop_master s;")
    sops = cur.fetchall()
    for s in sops:
        print(f"SOP ID: {s[0]}, Title: {s[1]}, Org ID: {s[2]}")
        
    cur.close()
    conn.close()
except Exception as e:
    print("Error:", e)
