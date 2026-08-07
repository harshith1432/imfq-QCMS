from functools import wraps
from flask import request, jsonify
from app.domain.services.idempotency_service import IdempotencyService

def idempotent(ttl=60):
    """
    Route decorator ensuring single execution per request fingerprint or X-Idempotency-Key header.
    Ignores duplicate clicks, parallel API triggers, and retry spam.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if request.method not in ['POST', 'PUT', 'PATCH', 'DELETE']:
                return fn(*args, **kwargs)

            # Extract identity if available
            user_id = None
            org_id = None
            try:
                from flask_jwt_extended import get_jwt_identity
                user_id = get_jwt_identity()
                if user_id:
                    from app.infrastructure.database.models.models import User
                    from app import db
                    user = db.session.get(User, user_id)
                    if user:
                        org_id = user.org_id
            except Exception:
                pass

            # Read custom header or generate body hash fingerprint
            custom_key = request.headers.get('X-Idempotency-Key')
            if custom_key:
                lock_key = f"hdr:{custom_key}:{user_id or 'anon'}"
            else:
                raw_body = request.get_data() or b''
                lock_key = IdempotencyService.generate_key(user_id, org_id, request.method, request.path, raw_body)

            status, cached = IdempotencyService.check_and_lock(lock_key)

            if status == 'PROCESSING':
                return jsonify({
                    "msg": "A request for this action is already processing. Duplicate ignored.",
                    "error_code": "DUPLICATE_REQUEST_BLOCKED"
                }), 429

            if status == 'COMPLETED':
                data, code = cached
                return jsonify(data), code

            try:
                res = fn(*args, **kwargs)
                
                # Extract payload & status code
                data = None
                code = 200

                if isinstance(res, tuple):
                    data = res[0].get_json() if hasattr(res[0], 'get_json') else res[0]
                    code = res[1]
                elif hasattr(res, 'get_json'):
                    data = res.get_json()
                    code = getattr(res, 'status_code', 200)
                else:
                    data = res
                    code = 200

                IdempotencyService.complete(lock_key, data, code)
                return res
            except Exception as e:
                IdempotencyService.release(lock_key)
                raise e

        return wrapper
    return decorator
