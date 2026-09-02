import logging
logger = logging.getLogger('qcms.boot_utils')
import os
from urllib.parse import urlparse, unquote

def bootstrap_database():
    """
    Checks if the database specified in DATABASE_URL exists.
    Skipped on Vercel serverless environment to prevent cold-start execution timeouts.
    """
    if os.getenv('VERCEL') or os.getenv('VERCEL_ENV') or os.getenv('VERCEL_REGION') or os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
        return

    try:
        import psycopg2
    except ImportError:
        return

    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        logger.info("[QCMS] Error: DATABASE_URL not set. Skipping bootstrap.")
        return
    if db_url.startswith('sqlite'):
        logger.info("[QCMS] SQLite database detected. Skipping bootstrap.")
        return

    try:
        result = urlparse(db_url)
        username = result.username
        password = unquote(result.password) if result.password else None
        host = result.hostname
        port = result.port or 5432
        database = result.path.lstrip('/')

        # Strip query params from the database name (e.g. "defaultdb?sslmode=require")
        if '?' in database:
            database = database.split('?')[0]

        # Detect SSL requirement from the URL query string
        use_ssl = 'sslmode=require' in db_url
        connect_kwargs = {
            'user': username,
            'password': password,
            'host': host,
            'port': port,
            'connect_timeout': 10
        }
        if use_ssl:
            connect_kwargs['sslmode'] = 'require'

        if not database:
            logger.info("[QCMS] Error: No database name specified in DATABASE_URL.")
            return

        # For cloud providers (Aiven, Supabase, etc.) the target DB always exists.
        # First try connecting directly to the target DB to verify connectivity.
        try:
            logger.info(f"[QCMS] Verifying database connection to '{host}:{port}/{database}' as user '{username}'...")
            conn = psycopg2.connect(dbname=database, **connect_kwargs)
            conn.close()
            logger.info(f"[QCMS] Database '{database}' verified and reachable.")
            return
        except psycopg2.OperationalError as direct_err:
            logger.info(f"[QCMS] Warning: Could not connect directly to '{database}': {direct_err}")

        # Fallback: try maintenance DB (local PostgreSQL setups)
        try:
            maintenance_db = 'postgres'
            logger.info(f"[QCMS] Attempting maintenance DB connection to '{maintenance_db}'...")
            conn = psycopg2.connect(dbname=maintenance_db, **connect_kwargs)
            conn.autocommit = True
            cur = conn.cursor()

            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,))
            exists = cur.fetchone()

            if not exists:
                logger.info(f"[QCMS] Database '{database}' not found. Attempting auto-creation...")
                try:
                    import re
                    from psycopg2 import sql
                    if not re.match(r'^[a-zA-Z0-9_-]+$', database):
                        raise ValueError(f"Invalid database name: {database}")
                    stmt = sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database))
                    cur.execute(stmt)
                    logger.info(f"[QCMS] SUCCESS: Database '{database}' created successfully.")
                except Exception as e:
                    logger.info(f"[QCMS] FATAL: Failed to create database '{database}': {e}")
            else:
                logger.info(f"[QCMS] Database '{database}' verified via maintenance DB.")

            cur.close()
            conn.close()
        except psycopg2.OperationalError as e:
            error_str = str(e)
            if "password authentication failed" in error_str:
                logger.info(f"[QCMS] CRITICAL: Password authentication failed for user '{username}'.")
            elif "is not accepting connections" in error_str or "connection refused" in error_str.lower():
                logger.info(f"[QCMS] CRITICAL: PostgreSQL not reachable at {host}:{port}.")
            else:
                logger.info(f"[QCMS] Warning: Could not connect to maintenance DB: {e}")

    except Exception as e:
        # General backup to prevent crash
        logger.info(f"[QCMS] Warning during database bootstrap: {e}")
