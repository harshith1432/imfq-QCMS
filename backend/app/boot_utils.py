import os
import psycopg2
from urllib.parse import urlparse, unquote

def bootstrap_database():
    """
    Checks if the database specified in DATABASE_URL exists.
    If not, attempts to create it using the 'postgres' default database.
    """
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("[QCMS] Error: DATABASE_URL not set. Skipping bootstrap.")
        return

    try:
        # Parse connection details
        # format: postgresql://user:password@host:port/database
        result = urlparse(db_url)
        username = result.username
        # Decode password in case it contains URL-encoded characters (like @ or !)
        password = unquote(result.password) if result.password else None
        host = result.hostname
        port = result.port or 5432
        database = result.path.lstrip('/')

        if not database:
            print("[QCMS] Error: No database name specified in DATABASE_URL.")
            return

        # 1. Check if target database exists by connecting to 'postgres' maintenance DB
        # We use 'postgres' as it's the standard default database on all installs.
        try:
            print(f"[QCMS] Verifying database connection to '{host}:{port}' as user '{username}'...")
            
            # Maintenance DBs to try: postgres, template1
            maintenance_db = 'postgres'
            
            conn = psycopg2.connect(
                dbname=maintenance_db,
                user=username,
                password=password,
                host=host,
                port=port,
                connect_timeout=10
            )
            conn.autocommit = True
            cur = conn.cursor()

            # Check existence of the target database
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,))
            exists = cur.fetchone()

            if not exists:
                print(f"[QCMS] Database '{database}' not found. Initializing auto-creation...")
                try:
                    cur.execute(f'CREATE DATABASE "{database}"')
                    print(f"[QCMS] SUCCESS: Database '{database}' created successfully.")
                except Exception as e:
                    print(f"[QCMS] FATAL: Failed to create database '{database}': {e}")
            else:
                print(f"[QCMS] Database '{database}' verified.")

            cur.close()
            conn.close()
        except psycopg2.OperationalError as e:
            error_str = str(e)
            if "password authentication failed" in error_str:
                print(f"\n" + "!" * 60)
                print(f"[QCMS] CRITICAL ERROR: Password authentication failed for user '{username}'.")
                print(f"[QCMS] The password in backend/.env does not match your system's PostgreSQL account.")
                print(f"[QCMS] Current DATABASE_URL: postgresql://{username}:****@{host}:{port}/{database}")
                print("!" * 60 + "\n")
            elif "is not accepting connections" in error_str or "connection refused" in error_str.lower():
                print(f"\n" + "!" * 60)
                print(f"[QCMS] CRITICAL: POSTGRESQL SERVICE NOT REACHABLE at {host}:{port}.")
                print(f"[QCMS] Ensure PostgreSQL is running and accepting connections on port {port}.")
                print("!" * 60 + "\n")
            else:
                print(f"[QCMS] Warning: Could not connect to 'postgres' maintenance DB: {e}")


    except Exception as e:
        # General backup to prevent crash
        print(f"[QCMS] Warning during database bootstrap: {e}")

