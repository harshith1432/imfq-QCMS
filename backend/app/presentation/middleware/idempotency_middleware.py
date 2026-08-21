"""
QCMS Enterprise Idempotency & Concurrency Middleware
===================================================
Prevents duplicate POST, PUT, PATCH, and DELETE request executions.
Reads Idempotency-Key / X-Idempotency-Key headers and returns:
- HTTP 409 Conflict if an identical request is currently PROCESSING.
- Cached JSON response & status code if key status is COMPLETED.
"""

import time
from threading import Lock
from functools import wraps
from flask import request, jsonify, make_response

def idempotent(f=None):
    """Decorator alias for explicit route-level idempotency protection."""
    if f is None:
        def decorator(fn):
            @wraps(fn)
            def decorated_function(*args, **kwargs):
                return fn(*args, **kwargs)
            return decorated_function
        return decorator
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

# Thread-safe in-memory cache for idempotency keys
IDEMPOTENCY_CACHE = {}
CACHE_LOCK = Lock()
CACHE_TTL_SECONDS = 120  # 2-minute TTL

def init_idempotency_middleware(app):
    @app.before_request
    def handle_idempotency_before_request():
        if request.method not in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return None

        # Ignore public login/auth endpoints
        if request.path and ('/auth/login' in request.path or '/auth/register' in request.path):
            return None

        idempotency_key = request.headers.get('Idempotency-Key') or request.headers.get('X-Idempotency-Key')
        if not idempotency_key:
            return None

        now = time.time()

        with CACHE_LOCK:
            # Purge expired cache entries
            expired_keys = [k for k, v in IDEMPOTENCY_CACHE.items() if now - v.get('timestamp', 0) > CACHE_TTL_SECONDS]
            for k in expired_keys:
                del IDEMPOTENCY_CACHE[k]

            entry = IDEMPOTENCY_CACHE.get(idempotency_key)
            if entry:
                if entry.get('status') == 'PROCESSING':
                    return jsonify({
                        "status": "error",
                        "message": "Action currently in-flight. Please wait.",
                        "idempotency_key": idempotency_key
                    }), 409
                elif entry.get('status') == 'COMPLETED':
                    res = make_response(entry['response_body'], entry['status_code'])
                    res.headers['Content-Type'] = 'application/json'
                    res.headers['X-Idempotent-Replay'] = 'true'
                    return res

            # Register key as PROCESSING
            IDEMPOTENCY_CACHE[idempotency_key] = {
                'status': 'PROCESSING',
                'timestamp': now
            }
            request._idempotency_key = idempotency_key

    @app.after_request
    def handle_idempotency_after_request(response):
        idempotency_key = getattr(request, '_idempotency_key', None)
        if idempotency_key and response.status_code < 500:
            with CACHE_LOCK:
                IDEMPOTENCY_CACHE[idempotency_key] = {
                    'status': 'COMPLETED',
                    'response_body': response.get_data(as_text=True),
                    'status_code': response.status_code,
                    'timestamp': time.time()
                }
        return response
