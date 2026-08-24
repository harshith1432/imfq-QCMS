from datetime import datetime
from app import db, bcrypt
import os
import json
from sqlalchemy.dialects.postgresql import ARRAY

database_url = os.environ.get('DATABASE_URL', '')
is_local = '127.0.0.1' in database_url or 'localhost' in database_url or not database_url

def _utc_now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).replace(tzinfo=None)

class SafeVector(db.TypeDecorator):
    impl = db.JSON
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                pass
        if hasattr(value, 'tolist'):
            return value.tolist()
        if isinstance(value, (list, tuple)):
            return list(value)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                clean = value.strip('[]() ')
                if clean:
                    try:
                        return [float(x.strip()) for x in clean.split(',') if x.strip()]
                    except Exception:
                        pass
                return []
        if hasattr(value, 'tolist'):
            return value.tolist()
        if isinstance(value, (list, tuple)):
            return list(value)
        return value

Vector = lambda dim: SafeVector
