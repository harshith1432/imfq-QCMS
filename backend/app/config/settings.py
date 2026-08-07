import os
from urllib.parse import urlparse, quote_plus, unquote, urlencode, parse_qs
from dotenv import load_dotenv

# Load env variables from root of backend
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path)

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'qcms_default_secret_key')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'qcms_secret')
    JWT_TOKEN_LOCATION = ['headers', 'query_string']
    JWT_QUERY_STRING_NAME = 'token'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    INTEGRATION_BASE_URL = os.getenv('INTEGRATION_BASE_URL', os.getenv('BASE_URL', '')).rstrip('/')
    
    # Connection Pool Settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 1800,
    }
    
    # File upload settings
    is_serverless = bool(os.getenv('VERCEL') or os.getenv('VERCEL_ENV') or os.getenv('VERCEL_REGION') or os.getenv('AWS_LAMBDA_FUNCTION_NAME'))
    if is_serverless:
        UPLOAD_FOLDER = '/tmp/uploads'
    else:
        UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'uploads'))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB limit
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')
    
    # Seed configuration
    SUPER_ADMIN_USERNAME = os.getenv('SUPER_ADMIN_USERNAME')
    SUPER_ADMIN_PASSWORD = os.getenv('SUPER_ADMIN_PASSWORD')
    
    # DB URL parsing
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        try:
            result = urlparse(db_url)
            username = result.username
            password = unquote(result.password) if result.password else None
            host = result.hostname
            port = result.port or 5432
            database = result.path.lstrip('/')
            query_string = result.query  # e.g. 'sslmode=require'

            driver_prefix = "postgresql+pg8000" if is_serverless else "postgresql"
            if password:
                encoded_password = quote_plus(password)
                base_uri = f"{driver_prefix}://{username}:{encoded_password}@{host}:{port}/{database}"
            else:
                base_uri = f"{driver_prefix}://{username}@{host}:{port}/{database}"

            # Re-append query string so sslmode=require etc. are preserved
            SQLALCHEMY_DATABASE_URI = f"{base_uri}?{query_string}" if query_string else base_uri
            if is_serverless and SQLALCHEMY_DATABASE_URI.startswith('postgresql://'):
                SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgresql://', 'postgresql+pg8000://', 1)
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
        if 'sslmode=require' in (SQLALCHEMY_DATABASE_URI or ''):
            SQLALCHEMY_ENGINE_OPTIONS['connect_args'] = {'sslmode': 'require'}
    elif SQLALCHEMY_DATABASE_URI and 'sqlite' not in SQLALCHEMY_DATABASE_URI:
        SQLALCHEMY_ENGINE_OPTIONS['pool_size'] = 5
        SQLALCHEMY_ENGINE_OPTIONS['max_overflow'] = 5
        # If Aiven (or any Postgres with sslmode=require), pass ssl args for psycopg2
        if 'sslmode=require' in (SQLALCHEMY_DATABASE_URI or ''):
            SQLALCHEMY_ENGINE_OPTIONS['connect_args'] = {'sslmode': 'require'}
    else:
        # For SQLite (including :memory:) use StaticPool so every session and
        # every Flask request handler share the SAME single connection.
        from sqlalchemy.pool import StaticPool
        SQLALCHEMY_ENGINE_OPTIONS = {
            'connect_args': {'check_same_thread': False},
            'poolclass': StaticPool,
        }
