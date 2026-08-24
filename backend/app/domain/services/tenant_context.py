"""
QCMS Enterprise Centralized Tenant Isolation & RBAC Permission Engine
=====================================================================
Eliminates scattered raw queries and prevents accidental Cross-Tenant Data Leakage (IDOR).
Standardizes resource access through strict tenant-bounded query fetchers:
- get_current_user()
- get_current_org()
- get_org_project(project_id)
- get_org_user(user_id)
- get_org_document(doc_id)
- require_permission(perm_key)
"""

from functools import wraps
from typing import Optional, Any, List
from flask import jsonify, g, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from werkzeug.exceptions import Forbidden, NotFound

from app import db
from app.infrastructure.database.models.models import User, Organization, Project


# Canonical Role -> Granular Permissions Mapping (Item 12)
ROLE_PERMISSIONS = {
    'SuperAdmin': [
        'platform.manage', 'platform.view', 'tenant.manage', 'tenant.view',
        'tenant.delete', 'user.manage', 'user.create', 'user.edit', 'user.delete',
        'users.manage', 'users.create', 'users.edit', 'users.delete',
        'project.create', 'project.edit', 'project.delete', 'project.view',
        'projects.create', 'projects.edit', 'projects.delete', 'projects.view',
        'stage.edit', 'stage.submit', 'stage.review', 'stage.approve',
        'report.view', 'report.export', 'reports.view', 'reports.export',
        'billing.manage', 'billing.view', 'analytics.view', 'audit.view', 'settings.manage'
    ],
    'Admin': [
        'tenant.view', 'tenant.manage', 'user.manage', 'user.create', 'user.edit', 'user.delete',
        'users.manage', 'users.create', 'users.edit', 'users.delete',
        'project.create', 'project.edit', 'project.delete', 'project.view',
        'projects.create', 'projects.edit', 'projects.delete', 'projects.view',
        'stage.edit', 'stage.submit', 'stage.review', 'stage.approve',
        'report.view', 'report.export', 'reports.view', 'reports.export',
        'billing.manage', 'billing.view', 'analytics.view', 'audit.view', 'settings.manage'
    ],
    'CEO': [
        'project.view', 'projects.view', 'stage.review', 'stage.approve',
        'report.view', 'report.export', 'reports.view', 'reports.export',
        'analytics.view', 'dashboard.view', 'audit.view'
    ],
    'Reviewer': [
        'project.view', 'projects.view', 'stage.review', 'stage.approve',
        'report.view', 'reports.view', 'analytics.view'
    ],
    'Facilitator': [
        'project.create', 'project.edit', 'project.view',
        'projects.create', 'projects.edit', 'projects.view',
        'stage.edit', 'stage.submit', 'stage.review', 'stage.approve',
        'report.view', 'reports.view', 'analytics.view'
    ],
    'Team Leader': [
        'project.create', 'project.edit', 'project.view',
        'projects.create', 'projects.edit', 'projects.view',
        'stage.edit', 'stage.submit', 'stage.approve',
        'report.view', 'reports.view', 'analytics.view'
    ],
    'Team Member': [
        'project.view', 'projects.view', 'stage.edit', 'stage.submit',
        'report.view', 'reports.view'
    ]
}


def get_current_user() -> Optional[User]:
    """Retrieves the currently authenticated User instance cached in Flask request context."""
    if hasattr(g, 'current_user') and g.current_user is not None:
        return g.current_user

    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity:
            user_id = int(identity) if not isinstance(identity, dict) else int(identity.get('id') or identity.get('user_id'))
            user = db.session.get(User, user_id)
            g.current_user = user
            return user
    except Exception:
        pass
    return None


def get_current_org() -> Optional[Organization]:
    """Retrieves the current user's owning Organization."""
    user = get_current_user()
    if not user or not user.org_id:
        return None
    return db.session.get(Organization, user.org_id)


def is_super_admin(user: Optional[User] = None) -> bool:
    """Checks if the user has platform SuperAdmin privileges."""
    u = user or get_current_user()
    if not u:
        return False
    role_name = u.role.name if u.role else ''
    is_sa_flag = getattr(u, 'is_super_admin', False) or u.org_id is None
    is_sa_custom = isinstance(u.custom_fields, dict) and bool(u.custom_fields.get('super_admin_role'))
    return role_name in ('SuperAdmin', 'Admin') and (is_sa_flag or is_sa_custom or u.org_id is None)


def has_permission(user: User, permission_key: str) -> bool:
    """Evaluates whether the user possesses the requested granular permission."""
    if not user:
        return False
    if is_super_admin(user):
        return True

    role_name = user.role.name if user.role else 'Team Member'
    allowed_perms = ROLE_PERMISSIONS.get(role_name, [])
    return permission_key in allowed_perms


def require_permission(permission_key: str):
    """
    Route decorator enforcing granular RBAC permissions.
    Usage:
        @project_bp.route('/<int:project_id>', methods=['DELETE'])
        @jwt_required()
        @require_permission('project.delete')
        def delete_project(project_id):
            ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"status": "error", "message": "Authentication required.", "code": "UNAUTHORIZED"}), 401

            if not has_permission(user, permission_key):
                return jsonify({
                    "status": "error",
                    "message": f"Access denied: missing required permission '{permission_key}'.",
                    "code": "FORBIDDEN",
                    "required_permission": permission_key
                }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def get_org_project(project_id: int, required_permission: Optional[str] = None) -> Project:
    """
    Safely retrieves a Project strictly bounded by the authenticated user's organization.
    SuperAdmins can access any project.
    Raises NotFound (404) or Forbidden (403) appropriately.
    """
    user = get_current_user()
    if not user:
        raise Forbidden("Authentication required.")

    if is_super_admin(user):
        project = db.session.get(Project, project_id)
        if not project:
            raise NotFound("Project not found.")
        return project

    if not user.org_id:
        raise Forbidden("User organization context is missing.")

    # Strictly filter by tenant org_id
    project = Project.query.filter_by(id=project_id, org_id=user.org_id).first()
    if not project:
        raise NotFound("Project not found within your organization.")

    if required_permission and not has_permission(user, required_permission):
        raise Forbidden(f"You do not have '{required_permission}' permission on this project.")

    return project


def get_org_user(user_id: int, required_permission: Optional[str] = None) -> User:
    """
    Safely retrieves a User bounded by the current organization context.
    SuperAdmins can access any user.
    """
    current_user = get_current_user()
    if not current_user:
        raise Forbidden("Authentication required.")

    if is_super_admin(current_user):
        target_user = db.session.get(User, user_id)
        if not target_user:
            raise NotFound("User not found.")
        return target_user

    if not current_user.org_id:
        raise Forbidden("User organization context is missing.")

    target_user = User.query.filter_by(id=user_id, org_id=current_user.org_id, is_deleted=False).first()
    if not target_user:
        raise NotFound("User not found within your organization.")

    if required_permission and not has_permission(current_user, required_permission):
        raise Forbidden(f"You do not have '{required_permission}' permission for this user.")

    return target_user
