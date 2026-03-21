from functools import wraps
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask import jsonify
from .models import User, Role

def role_required(allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            
            if not user or user.role.name not in allowed_roles:
                return jsonify({"msg": f"Access denied. Required roles: {allowed_roles}"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
