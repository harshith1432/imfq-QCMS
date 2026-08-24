import psycopg2

conn = psycopg2.connect(
    host='127.0.0.1', port=5432, dbname='ifqmm',
    user='postgres', password='Harshith@1432'
)
conn.autocommit = True
cur = conn.cursor()

# 1. Add column
cur.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS is_platform_org BOOLEAN NOT NULL DEFAULT FALSE")
print("Column is_platform_org ensured.")

# 2. Mark SA orgs
cur.execute("""
    UPDATE organizations
    SET is_platform_org = TRUE
    WHERE id IN (
        SELECT DISTINCT u.org_id
        FROM users u
        JOIN roles r ON u.role_id = r.id
        WHERE r.name = 'SuperAdmin'
          AND u.org_id IS NOT NULL
    )
""")
print(f"Marked {cur.rowcount} org(s) as platform orgs.")

# 3. Delete invoices for SA org subscriptions
cur.execute("""
    DELETE FROM subscription_invoices
    WHERE subscription_id IN (
        SELECT s.id FROM subscriptions s
        JOIN organizations o ON s.org_id = o.id
        WHERE o.is_platform_org = TRUE
    )
""")
print(f"Deleted {cur.rowcount} invoice(s).")

# 4. Delete payments for SA org
cur.execute("""
    DELETE FROM subscription_payments
    WHERE org_id IN (
        SELECT id FROM organizations WHERE is_platform_org = TRUE
    )
""")
print(f"Deleted {cur.rowcount} payment(s).")

# 5. Delete subscriptions for SA org
cur.execute("""
    DELETE FROM subscriptions
    WHERE org_id IN (
        SELECT id FROM organizations WHERE is_platform_org = TRUE
    )
""")
print(f"Deleted {cur.rowcount} subscription(s).")

cur.execute("SELECT COUNT(*) FROM subscriptions")
print(f"Remaining subscriptions: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM organizations WHERE is_platform_org = TRUE")
print(f"Platform orgs marked: {cur.fetchone()[0]}")

conn.close()
print("DONE - Restart Flask server now.")
