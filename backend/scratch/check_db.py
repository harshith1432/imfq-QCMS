import psycopg2
import json

db_url = "postgresql://postgres:Harshith%401432@127.0.0.1:5432/imfq_db"

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    print("--- SOPS ---")
    cur.execute("SELECT id, title, project_id, status, is_archived, author_id, owner_id FROM sop_master;")
    sops = cur.fetchall()
    for s in sops:
        print(f"SOP ID: {s[0]}, Title: {s[1]}, Project ID: {s[2]}, Status: {s[3]}, Archived: {s[4]}, Author ID: {s[5]}, Owner ID: {s[6]}")

    print("\n--- TRAINING ASSIGNMENTS ---")
    cur.execute("SELECT id, sop_id, user_id, status, read_status, acknowledgement_status, training_completion_status, assessment_score FROM training_assignments;")
    trainings = cur.fetchall()
    for t in trainings:
        print(f"Training ID: {t[0]}, SOP ID: {t[1]}, User ID: {t[2]}, Status: {t[3]}, Read: {t[4]}, Ack: {t[5]}, Comp: {t[6]}, Score: {t[7]}")
        
    print("\n--- ASSESSMENT CONFIG ---")
    cur.execute("SELECT id, sop_id, pass_percentage, time_limit, attempts_allowed FROM training_assessments;")
    configs = cur.fetchall()
    for c in configs:
        print(f"Config ID: {c[0]}, SOP ID: {c[1]}, Pass%: {c[2]}, TimeLimit: {c[3]}, Attempts: {c[4]}")
        
    print("\n--- ASSESSMENT QUESTIONS ---")
    cur.execute("SELECT id, sop_id, question_text, question_type, options, correct_answers FROM assessment_questions;")
    questions = cur.fetchall()
    for q in questions:
        print(f"Q ID: {q[0]}, SOP ID: {q[1]}, Text: {q[2]}, Type: {q[3]}, Options: {q[4]}, Correct: {q[5]}")

    print("\n--- ASSESSMENT RESULTS ---")
    cur.execute("SELECT id, training_id, user_id, score, percentage, attempt_number, result FROM assessment_results;")
    results = cur.fetchall()
    for r in results:
        print(f"Result ID: {r[0]}, Training ID: {r[1]}, User ID: {r[2]}, Score: {r[3]}, Percentage: {r[4]}, Attempt: {r[5]}, Result: {r[6]}")

    cur.close()
    conn.close()
except Exception as e:
    print("Error:", e)
