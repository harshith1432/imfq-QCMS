import os
from urllib.parse import urlparse, quote_plus, unquote, urlencode, parse_qs
from dotenv import load_dotenv

# Load env variables from root of backend
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path)

class Config:
    ENVIRONMENT = os.getenv('FLASK_ENV', os.getenv('ENVIRONMENT', 'production'))
    SECRET_KEY = os.getenv('SECRET_KEY', 'qcms_default_secret_key')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'qcms_secret')

    # Security check on startup: Fail-fast in production if weak or default secrets are detected
    if ENVIRONMENT == 'production':
        INSECURE_SECRETS = ['qcms_default_secret_key', 'qcms_secret', 'secret', 'default', '123456']
        if not os.getenv('SECRET_KEY') or SECRET_KEY in INSECURE_SECRETS:
            raise ValueError("[QCMS Security Critical] Running in PRODUCTION with default/insecure SECRET_KEY! Set a strong SECRET_KEY in .env.")
        if not os.getenv('JWT_SECRET_KEY') or JWT_SECRET_KEY in INSECURE_SECRETS:
            raise ValueError("[QCMS Security Critical] Running in PRODUCTION with default/insecure JWT_SECRET_KEY! Set a strong JWT_SECRET_KEY in .env.")

    JWT_TOKEN_LOCATION = ['headers', 'cookies']
    JWT_ACCESS_COOKIE_NAME = 'access_token_cookie'
    JWT_ACCESS_COOKIE_PATH = '/'
    JWT_COOKIE_SECURE = (ENVIRONMENT == 'production')
    JWT_COOKIE_SAMESITE = 'Lax'
    JWT_COOKIE_CSRF_PROTECT = False
    JWT_ACCESS_TOKEN_EXPIRES = 1800   # 30 Minutes — reduces XSS token-theft window
    JWT_REFRESH_TOKEN_EXPIRES = 1209600  # 14 Days
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Security work factor: 12 in production, 4 in test/development for 10x faster execution
    is_testing = (ENVIRONMENT in ('test', 'testing') or os.getenv('TESTING', '').lower() in ('true', '1') or bool(os.getenv('PYTEST_CURRENT_TEST')))
    BCRYPT_LOG_ROUNDS = 4 if is_testing else 12
    INTEGRATION_BASE_URL = os.getenv('INTEGRATION_BASE_URL', os.getenv('BASE_URL', '')).rstrip('/')
    
    # Connection Pool Settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 1800,
        'pool_size': 10,
        'max_overflow': 10,
        'pool_timeout': 30,
    }
    
    # Storage Backend Configuration
    STORAGE_BACKEND = os.getenv('STORAGE_BACKEND', 'local').strip().lower()
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    SUPABASE_STORAGE_BUCKET = os.getenv('SUPABASE_STORAGE_BUCKET', 'ifqmqc')
    AZURE_STORAGE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    AZURE_STORAGE_CONTAINER_NAME = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'qcms-uploads')

    # Distributed Redis & Celery Configuration
    REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0'))
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'))
    REQUIRE_REDIS_SECURITY = os.getenv('REQUIRE_REDIS_SECURITY', 'false').lower() in ('true', '1', 'yes')

    # File upload settings
    is_serverless = bool(os.getenv('VERCEL') or os.getenv('VERCEL_ENV') or os.getenv('VERCEL_REGION') or os.getenv('AWS_LAMBDA_FUNCTION_NAME'))
    if is_serverless:
        UPLOAD_FOLDER = '/tmp/uploads'
    else:
        UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'uploads'))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB limit
    
    # CORS Configuration - explicit origin whitelist
    CORS_ORIGINS = os.getenv(
        'CORS_ORIGINS',
        'http://localhost:5000,http://127.0.0.1:5000,http://localhost:3000,http://127.0.0.1:3000'
        if ENVIRONMENT == 'development' or not os.getenv('FLASK_ENV')
        else 'http://localhost:5000,http://127.0.0.1:5000'
    )
    
    # Seed configuration
    SUPER_ADMIN_USERNAME = os.getenv('SUPER_ADMIN_USERNAME')
    SUPER_ADMIN_PASSWORD = os.getenv('SUPER_ADMIN_PASSWORD')
    
    # Default Temporary / Initial Passwords
    DEFAULT_TEMP_PASSWORD = os.getenv('DEFAULT_TEMP_PASSWORD', 'Welcome@123')
    DEFAULT_USER_PASSWORD = os.getenv('DEFAULT_USER_PASSWORD', os.getenv('DEFAULT_TEMP_PASSWORD', 'Welcome@123'))
    DEFAULT_ADMIN_PASSWORD = os.getenv('DEFAULT_ADMIN_PASSWORD', os.getenv('DEFAULT_TEMP_PASSWORD', 'Welcome@123'))

    # DB URL parsing
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        if db_url.startswith('sqlite'):
            SQLALCHEMY_DATABASE_URI = db_url
        else:
            try:
                result = urlparse(db_url)
                username = result.username
                password = unquote(result.password) if result.password else None
                host = result.hostname
                port = result.port or 5432
                database = result.path.lstrip('/')
                query_string = result.query  # e.g. 'sslmode=require'

                try:
                    import pg8000
                    has_pg8000 = True
                except ImportError:
                    has_pg8000 = False

                # Strip non-standard parameters like pgbouncer=true that break psycopg2
                if query_string:
                    qs_parts = [p for p in query_string.split('&') if not p.startswith('pgbouncer=') and p != 'pgbouncer']
                    query_string = '&'.join(qs_parts)

                if is_serverless and has_pg8000:
                    driver_prefix = "postgresql+pg8000"
                    if query_string:
                        qs_parts = [p for p in query_string.split('&') if not p.startswith('sslmode=')]
                        query_string = '&'.join(qs_parts)
                else:
                    driver_prefix = "postgresql"

                if password:
                    encoded_password = quote_plus(password)
                    base_uri = f"{driver_prefix}://{username}:{encoded_password}@{host}:{port}/{database}"
                else:
                    base_uri = f"{driver_prefix}://{username}@{host}:{port}/{database}"

                # Re-append query string so parameters other than sslmode are preserved
                SQLALCHEMY_DATABASE_URI = f"{base_uri}?{query_string}" if query_string else base_uri
            except Exception as e:
                SQLALCHEMY_DATABASE_URI = db_url
    else:
        # Fallback to local SQLite if PostgreSQL URL is not defined (useful for development fallback)
        SQLALCHEMY_DATABASE_URI = 'sqlite:///qcms.db'

    # Add connection pool parameters for Serverless vs standard PostgreSQL
    if is_serverless:
        from sqlalchemy.pool import NullPool
        SQLALCHEMY_ENGINE_OPTIONS = {
            'poolclass': NullPool,
            'pool_pre_ping': True,
        }
        if 'pg8000' in (SQLALCHEMY_DATABASE_URI or ''):
            import ssl
            ssl_ctx = ssl.create_default_context()
            SQLALCHEMY_ENGINE_OPTIONS['connect_args'] = {'ssl_context': ssl_ctx}
    elif SQLALCHEMY_DATABASE_URI and 'sqlite' not in SQLALCHEMY_DATABASE_URI:
        SQLALCHEMY_ENGINE_OPTIONS['pool_size'] = 10
        SQLALCHEMY_ENGINE_OPTIONS['max_overflow'] = 10
        SQLALCHEMY_ENGINE_OPTIONS['pool_pre_ping'] = True
        SQLALCHEMY_ENGINE_OPTIONS['pool_recycle'] = 1800
    else:
        # For SQLite (including :memory:) use StaticPool so every session and
        # every Flask request handler share the SAME single connection.
        from sqlalchemy.pool import StaticPool
        SQLALCHEMY_ENGINE_OPTIONS = {
            'connect_args': {'check_same_thread': False},
            'poolclass': StaticPool,
        }
