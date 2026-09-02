"""
QCMS Enterprise Idempotency & Concurrency Middleware
===================================================
Prevents duplicate POST, PUT, PATCH, and DELETE request executions across all distributed workers.
Reads Idempotency-Key / X-Idempotency-Key headers and:
- Returns HTTP 409 Conflict if an identical request is currently PROCESSING.
- Returns Cached JSON response & status code if key status is COMPLETED.
- Returns HTTP 422 Unprocessable Entity if the key is reused with a different request payload.

Stores idempotency records in the unified Redis cache adapter with 1-hour TTL.
"""

import hashlib
import json
import logging
from functools import wraps
from flask import request, jsonify, make_response
from flask_jwt_extended import decode_token
from app.infrastructure.cache.redis_adapter import cache

logger = logging.getLogger('qcms.idempotency')
IDEMPOTENCY_DEFAULT_TTL = 3600  # 1 hour


class RedisIdempotency:
    """Unified Redis-backed idempotency handler."""

    @staticmethod
    def generate_key(user_id: str, org_id: str, idempotency_key: str) -> str:
        return f"idempotency:{org_id}:{user_id}:{idempotency_key}"

    @staticmethod
    def compute_payload_hash(method: str, path: str, raw_body: bytes) -> str:
        hasher = hashlib.sha256()
        hasher.update(method.upper().encode('utf-8'))
        hasher.update(path.encode('utf-8'))
        if raw_body:
            hasher.update(raw_body)
        return hasher.hexdigest()

    @classmethod
    def check_and_lock(cls, cache_key: str, payload_hash: str) -> tuple:
        record = cache.get(cache_key)
        if not record:
            new_record = {
                'status': 'PROCESSING',
                'payload_hash': payload_hash,
                'status_code': None,
                'data': None
            }
            cache.setex(cache_key, IDEMPOTENCY_DEFAULT_TTL, new_record)
            return 'NEW', None

        if isinstance(record, str):
            try:
                record = json.loads(record)
            except Exception:
                record = {}

        if record.get('payload_hash') != payload_hash:
            return 'PAYLOAD_MISMATCH', None

        if record.get('status') == 'PROCESSING':
            return 'PROCESSING', None

        if record.get('status') == 'COMPLETED':
            return 'COMPLETED', (record.get('data'), record.get('status_code', 200))

        return 'NEW', None

    @classmethod
    def complete(cls, cache_key: str, data: any, status_code: int = 200):
        record = cache.get(cache_key)
        if isinstance(record, str):
            try:
                record = json.loads(record)
            except Exception:
                record = {}
        if not record or not isinstance(record, dict):
            record = {}
        record['status'] = 'COMPLETED'
        record['data'] = data
        record['status_code'] = status_code
        cache.setex(cache_key, IDEMPOTENCY_DEFAULT_TTL, record)

    @classmethod
    def release(cls, cache_key: str):
        cache.delete(cache_key)


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


def _extract_user_and_org() -> tuple:
    """Extract user_id and org_id from Authorization: Bearer JWT header (Option A: Header-only)."""
    auth_header = request.headers.get('Authorization', '')
    user_id = 'anon'
    org_id = 'public'

    token = None
    if auth_header.startswith('Bearer '):
        token = auth_header[7:].strip()

    if token:
        try:
            decoded = decode_token(token)
            identity = decoded.get('sub')
            if isinstance(identity, dict):
                user_id = str(identity.get('id') or identity.get('user_id') or 'anon')
                org_id = str(identity.get('org_id') or 'public')
            elif identity is not None:
                user_id = str(identity)
                org_id = str(decoded.get('org_id') or 'public')
        except Exception:
            pass

    return user_id, org_id


def init_idempotency_middleware(app):
    @app.before_request
    def handle_idempotency_before_request():
        if request.method not in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return None

        # Ignore public login/auth endpoints
        if request.path and ('/auth/login' in request.path or '/auth/register' in request.path):
            return None

        raw_idempotency_key = request.headers.get('Idempotency-Key') or request.headers.get('X-Idempotency-Key')
        if not raw_idempotency_key:
            return None

        user_id, org_id = _extract_user_and_org()
        cache_key = RedisIdempotency.generate_key(user_id, org_id, raw_idempotency_key)
        raw_body = request.get_data()
        payload_hash = RedisIdempotency.compute_payload_hash(request.method, request.path, raw_body)

        status, cached_res = RedisIdempotency.check_and_lock(cache_key, payload_hash)

        if status == 'PAYLOAD_MISMATCH':
            return jsonify({
                "status": "error",
                "message": "Idempotency key has already been used with a different request body or endpoint.",
                "idempotency_key": raw_idempotency_key
            }), 422

        if status == 'PROCESSING':
            return jsonify({
                "status": "error",
                "message": "Action currently in-flight. Please wait.",
                "idempotency_key": raw_idempotency_key
            }), 409

        if status == 'COMPLETED' and cached_res:
            res_data, status_code = cached_res
            if isinstance(res_data, (dict, list)):
                res = jsonify(res_data)
                res.status_code = status_code
            else:
                res = app.response_class(
                    response=res_data,
                    status=status_code,
                    mimetype='application/json'
                )
            res.headers['Content-Type'] = 'application/json'
            res.headers['X-Idempotent-Replay'] = 'true'
            return res

        request._idempotency_cache_key = cache_key

    @app.after_request
    def handle_idempotency_after_request(response):
        cache_key = getattr(request, '_idempotency_cache_key', None)
        if cache_key:
            if response.status_code < 500:
                body = response.get_data(as_text=True)
                RedisIdempotency.complete(cache_key, body, status_code=response.status_code)
            else:
                RedisIdempotency.release(cache_key)
        return response
