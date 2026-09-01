from functools import wraps
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask import jsonify, request
from app import db
from app.infrastructure.database.models.models import User, Organization
from app.domain.services.subscription_service import SubscriptionManager

# ─────────────────────────────────────────────────────────────────────────────
# Super Admin Sub-Role Definitions & Permission Map
# ─────────────────────────────────────────────────────────────────────────────

# Canonical sub-role names (match exactly what's stored in custom_fields)
SA_OWNER           = 'Owner'
SA_PLATFORM_OPS    = 'Platform Operations'
SA_BILLING         = 'Billing'
SA_SUPPORT         = 'Support'
SA_PRODUCT         = 'Product'
SA_READ_ONLY       = 'Read Only'

# Map: section → which sub-roles can WRITE (POST/PUT/DELETE)
# Owner always has write access everywhere; this map only applies to restricted roles.
SA_WRITE_PERMISSIONS = {
    'organizations':  [SA_PLATFORM_OPS],
    'subscriptions':  [SA_BILLING],
    'licenses':       [SA_PLATFORM_OPS, SA_BILLING],
    'admins':         [SA_PLATFORM_OPS],
    'users':          [SA_PLATFORM_OPS],
    'plans':          [SA_BILLING, SA_PRODUCT],
    'modules':        [SA_BILLING, SA_PRODUCT],
    'analytics':      [SA_PLATFORM_OPS, SA_BILLING],
    'support':        [SA_PLATFORM_OPS, SA_SUPPORT],
    'billing':        [SA_BILLING],
    'announcements':  [SA_PLATFORM_OPS, SA_PRODUCT],
    'logs':           [SA_PLATFORM_OPS],
    'integrations':   [SA_PLATFORM_OPS],
    'settings':       [SA_PLATFORM_OPS],
    'admin-logins':   [],   # Owner only
}

# Map: section → which sub-roles can even READ (navigate to)
SA_READ_PERMISSIONS = {
    'overview':       [SA_PLATFORM_OPS, SA_BILLING, SA_SUPPORT, SA_PRODUCT, SA_READ_ONLY],
    'organizations':  [SA_PLATFORM_OPS, SA_BILLING, SA_SUPPORT, SA_READ_ONLY],
    'subscriptions':  [SA_BILLING, SA_READ_ONLY, SA_PLATFORM_OPS],
    'licenses':       [SA_PLATFORM_OPS, SA_BILLING, SA_READ_ONLY],
    'admins':         [SA_PLATFORM_OPS, SA_SUPPORT, SA_READ_ONLY],
    'users':          [SA_PLATFORM_OPS, SA_SUPPORT, SA_READ_ONLY],
    'plans':          [SA_BILLING, SA_PRODUCT, SA_READ_ONLY, SA_PLATFORM_OPS],
    'modules':        [SA_PLATFORM_OPS, SA_BILLING, SA_SUPPORT, SA_PRODUCT, SA_READ_ONLY],
    'analytics':      [SA_PLATFORM_OPS, SA_BILLING, SA_READ_ONLY, SA_PRODUCT],
    'support':        [SA_PLATFORM_OPS, SA_SUPPORT, SA_READ_ONLY],
    'billing':        [SA_BILLING, SA_READ_ONLY, SA_PLATFORM_OPS],
    'announcements':  [SA_PLATFORM_OPS, SA_PRODUCT, SA_READ_ONLY, SA_SUPPORT],
    'logs':           [SA_PLATFORM_OPS, SA_READ_ONLY],
    'integrations':   [SA_PLATFORM_OPS, SA_READ_ONLY],
    'settings':       [SA_PLATFORM_OPS, SA_READ_ONLY],
    'admin-logins':   [SA_READ_ONLY],
}


def _is_super_admin(user):
    if not user:
        return False
    role_name = user.role.name if user.role else ''
    if role_name == 'SuperAdmin':
        return True
    if getattr(user, 'is_super_admin', False):
        return True
    if isinstance(user.custom_fields, dict) and bool(user.custom_fields.get('super_admin_role')):
        if role_name in ('SuperAdmin', '') or user.org_id is None:
            return True
    return False


def _get_sa_sub_role(user):
    """Return the Super Admin sub-role string, or 'Owner' if none is set."""
    if not user:
        return SA_OWNER
    cf = user.custom_fields if isinstance(user.custom_fields, dict) else {}
    return cf.get('super_admin_role', SA_OWNER)


def get_sa_permissions(sub_role):
    """Return a dict of {section: {can_read, can_write}} for the given sub-role."""
    if sub_role == SA_OWNER:
        # Owner has full access everywhere
        all_sections = set(SA_READ_PERMISSIONS.keys()) | set(SA_WRITE_PERMISSIONS.keys())
        return {s: {'can_read': True, 'can_write': True} for s in all_sections}

    perms = {}
    all_sections = set(SA_READ_PERMISSIONS.keys()) | set(SA_WRITE_PERMISSIONS.keys())
    for section in all_sections:
        can_read = sub_role in SA_READ_PERMISSIONS.get(section, [])
        can_write = sub_role in SA_WRITE_PERMISSIONS.get(section, [])
        perms[section] = {'can_read': can_read, 'can_write': can_write}
    return perms


# ─────────────────────────────────────────────────────────────────────────────
# Decorators
# ─────────────────────────────────────────────────────────────────────────────

def role_required(allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                return jsonify({"msg": "Invalid identity"}), 401

            user = db.session.get(User, user_id)
            if not user:
                return jsonify({"msg": "User not found"}), 403

            if _is_super_admin(user):
                return fn(*args, **kwargs)

            role_name = user.role.name if user.role else ''
            if role_name not in allowed_roles:
                return jsonify({"msg": f"Access denied. Required roles: {allowed_roles}"}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def plan_required(required_plans):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                return jsonify({"msg": "Invalid identity"}), 401

            user = db.session.get(User, user_id)
            if not user:
                return jsonify({"msg": "User not found"}), 403

            if _is_super_admin(user):
                return fn(*args, **kwargs)

            if not user.org_id:
                return jsonify({"msg": "Organization context required"}), 403

            org = db.session.get(Organization, user.org_id)
            if not org or org.subscription_plan not in required_plans:
                return jsonify({
                    "msg": "Premium feature",
                    "error_code": "PLAN_UPGRADE_REQUIRED",
                    "required_plans": required_plans,
                    "current_plan": org.subscription_plan if org else "None"
                }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def feature_required(feature_name):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                return jsonify({"msg": "Invalid identity"}), 401

            user = db.session.get(User, user_id)
            if not user:
                return jsonify({"msg": "User not found"}), 403

            if _is_super_admin(user):
                return fn(*args, **kwargs)

            if not user.org_id:
                return jsonify({"msg": "Organization context required"}), 403

            if not SubscriptionManager.has_feature(user.org_id, feature_name):
                return jsonify({
                    "msg": f"Feature '{feature_name}' is not available on your current plan.",
                    "error_code": "FEATURE_LOCKED",
                    "feature": feature_name
                }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def super_admin_required():
    """Verifies the caller is a Super Admin of any sub-role."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                return jsonify({"msg": "Invalid identity"}), 401

            user = db.session.get(User, user_id)
            if not _is_super_admin(user):
                return jsonify({"msg": "Super Admin access required"}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def sub_role_required(section):
    """
    Enforce read-level sub-role access for a given section.
    Owner always passes. Other sub-roles are checked against SA_READ_PERMISSIONS.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                return jsonify({"msg": "Invalid identity"}), 401

            user = db.session.get(User, user_id)
            if not _is_super_admin(user):
                return jsonify({"msg": "Super Admin access required"}), 403

            sub_role = _get_sa_sub_role(user)
            if sub_role == SA_OWNER:
                return fn(*args, **kwargs)

            allowed = SA_READ_PERMISSIONS.get(section, [])
            if sub_role not in allowed:
                return jsonify({
                    "status": "error",
                    "message": f"Your sub-role '{sub_role}' does not have access to the '{section}' section.",
                    "error_code": "SUB_ROLE_ACCESS_DENIED",
                    "sub_role": sub_role,
                    "section": section
                }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def sub_role_write_required(section):
    """
    Enforce write-level sub-role access for a given section.
    Owner always passes. Read Only is always blocked on writes.
    Other sub-roles are checked against SA_WRITE_PERMISSIONS.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                return jsonify({"msg": "Invalid identity"}), 401

            user = db.session.get(User, user_id)
            if not _is_super_admin(user):
                return jsonify({"msg": "Super Admin access required"}), 403

            sub_role = _get_sa_sub_role(user)
            if sub_role == SA_OWNER:
                return fn(*args, **kwargs)

            # Read Only Auditor can never write
            if sub_role == SA_READ_ONLY:
                return jsonify({
                    "status": "error",
                    "message": "Read Only Auditor accounts cannot perform write operations.",
                    "error_code": "READ_ONLY_ACCESS",
                    "sub_role": sub_role
                }), 403

            allowed = SA_WRITE_PERMISSIONS.get(section, [])
            if sub_role not in allowed:
                return jsonify({
                    "status": "error",
                    "message": f"Your sub-role '{sub_role}' does not have write access to the '{section}' section.",
                    "error_code": "SUB_ROLE_WRITE_DENIED",
                    "sub_role": sub_role,
                    "section": section
                }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# Enterprise Feature Flag & Module Management Guard
# ─────────────────────────────────────────────────────────────────────────────

def check_feature_access(user, feature_code):
    """
    Evaluates whether a feature is active, parent enabled, plan allowed, and org override satisfied.
    Delegates to FeatureEngine for cached fast evaluation.
    Returns (allowed: bool, reason: str)
    """
    if not feature_code:
        return True, "No feature code specified"

    if user and _is_super_admin(user):
        return True, "SuperAdmin bypass"

    org_id = user.org_id if user else None
    from app.domain.services.feature_engine import FeatureEngine
    allowed = FeatureEngine.is_enabled(org_id, feature_code)
    
    if not allowed:
        return False, f"Feature '{feature_code}' is disabled or not allowed for your plan/organization"

    return True, "Access granted"


def feature_required(feature_code):
    """
    Decorator to enforce Enterprise Feature Flag access on API routes.
    If the feature is disabled or not included in the plan, returns HTTP 403 Forbidden.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            try:
                user_id = int(user_id)
                user = db.session.get(User, user_id)
            except Exception:
                user = None

            allowed, reason = check_feature_access(user, feature_code)
            if not allowed:
                return jsonify({
                    "status": "error",
                    "error": "Forbidden",
                    "message": f"Access denied: {reason}",
                    "feature_code": feature_code
                }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator

