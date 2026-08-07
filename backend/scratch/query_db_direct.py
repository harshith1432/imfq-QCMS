import psycopg2

db_url = "postgresql://postgres:Harshith%401432@127.0.0.1:5432/imfq_db"

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    print("PROJECT 33 DETAILS:")
    cur.execute("SELECT id, title, creator_id, team_leader_id, facilitator_id, reviewer_id, status FROM projects WHERE id=33;")
    proj = cur.fetchone()
    if proj:
        print(f"ID: {proj[0]}, Title: {proj[1]}, Creator: {proj[2]}, Leader: {proj[3]}, Facilitator: {proj[4]}, Reviewer: {proj[5]}, Status: {proj[6]}")
        
    print("\nPROJECT 33 MEMBERS:")
    cur.execute("SELECT pm.id, pm.user_id, u.username, pm.role FROM project_members pm JOIN users u ON pm.user_id = u.id WHERE pm.project_id=33;")
    members = cur.fetchall()
    for m in members:
        print(f"PM ID: {m[0]}, User ID: {m[1]}, Username: {m[2]}, Project Role: {m[3]}")
        
    cur.close()
    conn.close()
except Exception as e:
    print("Error:", e)
