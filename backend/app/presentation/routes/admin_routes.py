import os
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app import db, bcrypt
import sqlalchemy as sa
from app.infrastructure.database.models.models import (
    User, Role, Department, Plant, AuditLog, Project, ProjectMember, ProjectReview, ProjectWorkflow,
    ProjectStageTracker, Stage3CauseIdentification,
    Stage5CountermeasurePlanningSolutionDevelopment,
    Stage7PerformanceVerificationBenefitsRealization,
    Stage8StandardizationKnowledgeSharingProjectClosure,
    KnowledgeRepository, Organization, SubscriptionPayment,
    SOP, SOPTraining, SOPComment, UserCustomField,
    ComplianceStandard, SupportTicket, Notification, ImportedIdea
)
from app.domain.services.subscription_service import SubscriptionManager
from app.infrastructure.mailer.email_service import EmailUtils
from datetime import datetime, timedelta
import secrets
import copy
from sqlalchemy.orm.attributes import flag_modified
from app.utils.avatar_utils import get_profile_picture_url
from app.domain.services.feature_engine import feature_module_required
from functools import wraps

admin_bp = Blueprint('admin', __name__)

# ── Role Access Control (RBAC) Matrix Defaults ──
DEFAULT_ROLE_PERMISSIONS = {
    "Team Member": {
        "overview": True,
        "project_repo": True,
        "knowledge_base": True,
        "leaderboard": True,
        "additional_sources": True,
        "analytics": False,
        "user_management": False,
        "plants": False,
        "departments": False,
        "audit_logs": False,
        "stage_template": False,
        "settings": True
    },
    "CEO": {
        "overview": True,
        "project_repo": True,
        "knowledge_base": True,
        "leaderboard": True,
        "additional_sources": True,
        "analytics": True,
        "user_management": False,
        "plants": False,
        "departments": False,
        "audit_logs": False,
        "stage_template": False,
        "settings": True
    },
    "Facilitator": {
        "overview": True,
        "project_repo": True,
        "knowledge_base": True,
        "leaderboard": True,
        "additional_sources": True,
        "analytics": True,
        "user_management": False,
        "plants": False,
        "departments": False,
        "audit_logs": False,
        "stage_template": False,
        "settings": True
    },
    "Reviewer": {
        "overview": True,
        "project_repo": True,
        "knowledge_base": True,
        "leaderboard": True,
        "additional_sources": True,
        "analytics": True,
        "user_management": False,
        "plants": False,
        "departments": False,
        "audit_logs": False,
        "stage_template": False,
        "settings": True
    },
    "Admin": {
        "overview": True,
        "project_repo": True,
        "knowledge_base": True,
        "leaderboard": True,
        "additional_sources": True,
        "analytics": True,
        "user_management": True,
        "plants": True,
        "departments": True,
        "audit_logs": True,
        "stage_template": True,
        "settings": True
    }
}

def check_user_module_permission(user, module_key=None):
    """
    Checks if a user has permission to access a module based on organization's role_permissions matrix.
    Admin, SuperAdmin, CEO always have full admin privileges.
    For other roles, checks org.security_settings['role_permissions'][role_name][module_key].
    """
    if not user:
        return False
    role_name = user.role.name if user.role else ''
    is_sa_custom = isinstance(user.custom_fields, dict) and bool(user.custom_fields.get('super_admin_role'))
    if role_name in ('Admin', 'SuperAdmin', 'CEO') or is_sa_custom:
        return True
    
    org_id = user.org_id
    if not org_id:
        return False
    
    org = db.session.get(Organization, org_id)
    sec = getattr(org, 'security_settings', {}) or {} if org else {}
    role_perms = sec.get('role_permissions') if isinstance(sec, dict) else None
    
    target_role = role_name
    if target_role == 'Team Leader':
        target_role = 'Team Member'
        
    perms = {}
    if role_perms and isinstance(role_perms, dict) and target_role in role_perms and isinstance(role_perms[target_role], dict):
        perms = role_perms[target_role]
    elif target_role in DEFAULT_ROLE_PERMISSIONS:
        perms = DEFAULT_ROLE_PERMISSIONS[target_role]
        
    if module_key:
        return bool(perms.get(module_key, False))
        
    # If no specific module is passed, check if any administration module is enabled for this role
    admin_modules = ['user_management', 'plants', 'departments', 'audit_logs', 'stage_template', 'settings']
    return any(bool(perms.get(m, False)) for m in admin_modules)

# Middleware for Admin/Module access (SuperAdmin & Admin have full privileges, other roles checked against org RBAC matrix)
def admin_required(f):
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        identity = get_jwt_identity()
        try:
            current_user_id = int(identity)
        except (ValueError, TypeError):
            return jsonify({"message": "Invalid token identity"}), 401
            
        user = db.session.get(User, current_user_id)
        if not user:
            return jsonify({"message": "Admin access required"}), 403
            
        role_name = user.role.name if user.role else ''
        is_sa_custom = isinstance(user.custom_fields, dict) and bool(user.custom_fields.get('super_admin_role'))
        if role_name in ('Admin', 'SuperAdmin', 'CEO') or is_sa_custom:
            return f(*args, **kwargs)
            
        # Determine module based on request endpoint/path
        path = request.path.lower()
        mod_key = None
        if '/users' in path or '/user-custom-fields' in path or '/import-users' in path or '/bulk-users' in path:
            mod_key = 'user_management'
        elif '/plants' in path:
            mod_key = 'plants'
        elif '/departments' in path:
            mod_key = 'departments'
        elif '/audit' in path or '/logs' in path:
            mod_key = 'audit_logs'
        elif '/stage-template' in path or '/stage-templates' in path:
            mod_key = 'stage_template'
        elif '/settings' in path or '/branding' in path or '/security' in path or '/subscription' in path or '/compliance' in path:
            mod_key = 'settings'
            
        if check_user_module_permission(user, mod_key):
            return f(*args, **kwargs)
            
        return jsonify({"message": "Access denied: insufficient module permissions"}), 403
    return decorated_function

def log_action(user_id, action, org_id, target_table=None, target_id=None, details=None):
    log = AuditLog(
        user_id=user_id,
        org_id=org_id,
        action=action,
        target_table=target_table,
        target_id=target_id,
        details=details
    )
    db.session.add(log)
    db.session.commit()

def validate_custom_field_value(display_name, value, data_type):
    if not value:
        return None
    val_str = str(value).strip()
    data_type = (data_type or 'both').lower()
    import re
    
    if data_type == 'numeric':
        if not val_str.isdigit():
            return f"Field '{display_name}' must contain numbers only."
    elif data_type == 'character':
        if not all(c.isalpha() or c.isspace() for c in val_str):
            return f"Field '{display_name}' must contain letters only."
    elif data_type == 'phone':
        # Accept: exactly 10 digits  OR  +91 followed by exactly 10 digits
        if not re.match(r'^(\+91[\s\-]?)?\d{10}$', val_str.replace(' ', '').replace('-', '')):
            return f"Field '{display_name}' must be a valid 10-digit phone number (e.g. 9876543210 or +919876543210)."
    elif data_type == 'date':
        from datetime import datetime
        parsed = False
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y'):
            try:
                datetime.strptime(val_str, fmt)
                parsed = True
                break
            except ValueError:
                continue
        if not parsed:
            return f"Field '{display_name}' must be a valid date (e.g. YYYY-MM-DD)."
    elif data_type == 'email':
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', val_str):
            return f"Field '{display_name}' must be a valid email address."
    return None

# --- User Management ---

import math

@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404

    page = request.args.get('page', type=int)
    per_page = request.args.get('per_page', 10, type=int)
    q = (request.args.get('q') or '').strip()
    status_filter = (request.args.get('filter') or '').strip()

    query = User.query.join(Role).outerjoin(Department, User.department_id == Department.id).filter(
        User.org_id == current_user.org_id,
        Role.name != 'SuperAdmin'
    )

    plant_filter = request.args.get('plant_id')
    if plant_filter and str(plant_filter).isdigit():
        query = query.filter(User.plant_id == int(plant_filter))

    if status_filter == 'active':
        query = query.filter(User.is_active == True)

    if q:
        search_pattern = f"%{q}%"
        query = query.filter(
            db.or_(
                User.username.ilike(search_pattern),
                User.email.ilike(search_pattern),
                User.full_name.ilike(search_pattern),
                Role.name.ilike(search_pattern),
                Department.name.ilike(search_pattern)
            )
        )

    query = query.order_by(User.id.asc())

    def format_user(u):
        p_name = "N/A"
        if u.plant:
            p_name = u.plant.name
        elif u.dept and u.dept.plant:
            p_name = u.dept.plant.name
            if not u.plant_id:
                u.plant_id = u.dept.plant_id
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()
        else:
            # Fallback for org users without plant_id: auto-link to org's first plant
            def_plant = Plant.query.filter_by(org_id=u.org_id).first()
            if def_plant:
                p_name = def_plant.name
                if not u.plant_id:
                    u.plant_id = def_plant.id
                    try:
                        db.session.commit()
                    except Exception:
                        db.session.rollback()
            
        return {
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name or u.username,
            "email": u.email,
            "role": u.role.name,
            "department": u.dept.name if u.dept else "N/A",
            "plant_id": u.plant_id or (u.dept.plant_id if u.dept else None),
            "plant_name": p_name,
            "is_active": u.is_active,
            "profile_picture": get_profile_picture_url(u),
            "created_at": u.created_at.isoformat() + "Z" if u.created_at else None,
            "last_login": u.last_login.isoformat() + "Z" if u.last_login else None,
            "last_active": u.last_login.isoformat() + "Z" if u.last_login else None,
            "custom_fields": u.custom_fields or {}
        }

    if page is not None:
        total = query.count()
        total_pages = max(1, math.ceil(total / per_page)) if total > 0 else 1
        users = query.offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            "items": [format_user(u) for u in users],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages
        }), 200

    users = query.all()
    return jsonify([format_user(u) for u in users]), 200

@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user_detail(user_id):
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "Admin user not found"}), 404
    user = User.query.join(Role).filter(
        User.id == user_id, 
        User.org_id == current_user.org_id,
        Role.name != 'SuperAdmin'
    ).first_or_404()
    return jsonify({
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name or user.username,
        "email": user.email,
        "role": user.role.name,
        "department": user.dept.name if user.dept else "N/A",
        "is_active": user.is_active,
        "profile_picture": get_profile_picture_url(user),
        "custom_fields": user.custom_fields or {}
    }), 200

@admin_bp.route('/users', methods=['POST'])
@jwt_required()
@feature_module_required('users.create')
@admin_required
def create_user():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    data = request.get_json()
    if not data:
        return jsonify({"message": "No input data provided"}), 400
    
    email = data.get('email')
    if not email:
        return jsonify({"message": "Email is required"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Email already exists"}), 400
    
    username = data.get('username')
    if not username:
        return jsonify({"message": "Username is required"}), 400
        
    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Username already taken"}), 400
    
    role_name = data.get('role')
    role = Role.query.filter_by(name=role_name).first() if role_name else None
    if not role:
        return jsonify({"message": f"Invalid role: {role_name}"}), 400
    
    # Safety for org_id
    org_id = current_user.org_id
    if not org_id:
        first_org = Organization.query.first()
        org_id = first_org.id if first_org else 1

    custom_field_defs = UserCustomField.query.filter_by(org_id=org_id).all()
    custom_values = {}
    missing_required = []
    for fd in custom_field_defs:
        if fd.field_key in ('username', 'role', 'department', 'plant_location', 'plant_id', 'plant') or 'plant' in (fd.field_key or '').lower() or 'plant' in (fd.display_name or '').lower():
            continue
        val = data.get(fd.field_key)
        if fd.is_required and (val is None or str(val).strip() == ''):
            missing_required.append(fd.display_name)
        if val is not None and str(val).strip() != '':
            val_str = str(val).strip()
            err = validate_custom_field_value(fd.display_name, val_str, fd.data_type)
            if err:
                return jsonify({"message": err}), 400
            custom_values[fd.field_key] = val_str
            
    if missing_required:
        return jsonify({"message": f"Required fields missing: {', '.join(missing_required)}"}), 400

    dept_input = data.get('dept_name') or data.get('department')
    dept = None
    if dept_input and dept_input != 'N/A':
        # 1. Try as ID if it's numeric
        if str(dept_input).isdigit():
            dept = Department.query.filter_by(id=int(dept_input), org_id=org_id).first()
        
        # 2. If not found by ID, try as Name
        if not dept:
            dept = Department.query.filter_by(name=str(dept_input), org_id=org_id).first()
            
        # 3. Create if still not found (only if it doesn't look like an ID)
        if not dept and not str(dept_input).isdigit():
            dept = Department(name=str(dept_input), org_id=org_id)
            db.session.add(dept)
            db.session.flush()
    
    # Subscription Limit Check
    can_add, limit_msg = SubscriptionManager.check_user_limit(org_id)
    if not can_add:
        return jsonify({
            "message": limit_msg,
            "error_code": "USER_LIMIT_REACHED"
        }), 403

    password = data.get('password', 'Welcome@123')
    
    plant_input = data.get('plant_id') or data.get('plant_location') or data.get('plant')
    user_plant_id = None
    if plant_input:
        if str(plant_input).isdigit():
            user_plant_id = int(plant_input)
        else:
            from app.infrastructure.database.models.models import Plant
            p_match = Plant.query.filter(
                Plant.org_id == org_id,
                db.or_(Plant.name.ilike(str(plant_input).strip()), Plant.code.ilike(str(plant_input).strip()))
            ).first()
            if p_match:
                user_plant_id = p_match.id

    if not user_plant_id and dept and dept.plant_id:
        user_plant_id = dept.plant_id

    try:
        new_user = User(
            username=username,
            full_name=data.get('full_name', username), # Save full name if provided
            email=email,
            hashed_password=bcrypt.generate_password_hash(password).decode('utf-8'),
            role_id=role.id,
            department_id=dept.id if dept else None,
            plant_id=user_plant_id,
            org_id=org_id,
            is_temp_password=True,
            is_verified=True,
            status='Active',
            custom_fields=custom_values
        )
        db.session.add(new_user)
        db.session.commit()
        
        if custom_values:
            update_cols = ", ".join(f"{k} = :val_{k}" for k in custom_values.keys())
            params = {f"val_{k}": v for k, v in custom_values.items()}
            params["user_id"] = new_user.id
            from sqlalchemy import text
            db.session.execute(text(f"UPDATE users SET {update_cols} WHERE id = :user_id"), params)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to create user", "error": str(e)}), 500
    
    # Send credentials email (Non-blocking)
    try:
        EmailUtils.send_temp_password_email(new_user, password)
    except Exception as e:
        current_app.logger.error(f"Failed to send welcome email to {email}: {str(e)}")

    log_action(current_user.id, "CREATE_USER", current_user.org_id, "users", new_user.id, {"username": new_user.username})
    return jsonify({
        "message": "User provisioned successfully. Credentials sent to their email.",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email
        }
    }), 201

@admin_bp.route('/users/custom-fields', methods=['GET'])
@admin_required
def get_custom_fields():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    org_id = current_user.org_id
    if not org_id:
        first_org = Organization.query.first()
        org_id = first_org.id if first_org else 1
        
    fields = UserCustomField.query.filter_by(org_id=org_id).order_by(UserCustomField.created_at).all()
    # Check if any system field is missing
    missing_any = not all(
        any(f.field_key == key for f in fields) 
        for key in ('username', 'role', 'department', 'plant_location', 'email')
    )
    if missing_any:
        system_fields = [
            ('username', 'User', True, True, 'both'),
            ('role', 'User Role', True, True, 'both'),
            ('department', 'Department', True, True, 'both'),
            ('plant_location', 'Plant Location', True, True, 'both'),
            ('email', 'Email Address', True, True, 'email')
        ]
        for key, name, req, sys, dtype in system_fields:
            existing_f = UserCustomField.query.filter_by(org_id=org_id, field_key=key).first()
            if not existing_f:
                db.session.add(UserCustomField(org_id=org_id, field_key=key, display_name=name, is_required=req, is_system=sys, data_type=dtype))
            elif sys and not existing_f.is_system:
                existing_f.is_system = True
                existing_f.is_required = req
        db.session.commit()
        fields = UserCustomField.query.filter_by(org_id=org_id).order_by(UserCustomField.created_at).all()

    return jsonify([{
        "id": f.id,
        "field_key": f.field_key,
        "display_name": f.display_name,
        "is_required": f.is_required,
        "is_system": f.is_system,
        "data_type": f.data_type or 'both'
    } for f in fields]), 200

@admin_bp.route('/users/custom-fields', methods=['POST'])
@admin_required
def add_custom_field():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    org_id = current_user.org_id
    if not org_id:
        first_org = Organization.query.first()
        org_id = first_org.id if first_org else 1
        
    data = request.get_json() or {}
    display_name = (data.get('display_name') or '').strip()
    is_required = bool(data.get('is_required'))
    data_type = (data.get('data_type') or 'both').strip().lower()
    
    if data_type not in ('character', 'numeric', 'phone', 'date', 'email', 'both'):
        return jsonify({"message": "Invalid data type"}), 400
        
    if not display_name:
        return jsonify({"message": "Display name is required"}), 400
        
    import re
    field_key = re.sub(r'[^a-zA-Z0-9_]', '', display_name.lower().replace(' ', '_'))
    if not field_key:
        return jsonify({"message": "Invalid display name format"}), 400
        
    forbidden_keys = {'id', 'username', 'email', 'role', 'department', 'plant_location', 'org_id', 'hashed_password', 'password', 'is_active', 'status', 'created_at', 'custom_fields'}
    if field_key in forbidden_keys:
        return jsonify({"message": f"Field name '{display_name}' is reserved by the system"}), 400
        
    if UserCustomField.query.filter_by(org_id=org_id, field_key=field_key).first():
        return jsonify({"message": "A field with this name already exists"}), 400
        
    from sqlalchemy import text
    try:
        db.session.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {field_key} TEXT;"))
        db.session.commit()
    except Exception as ddl_err:
        db.session.rollback()
        return jsonify({"message": "Failed to update database schema", "error": str(ddl_err)}), 500
        
    new_field = UserCustomField(
        org_id=org_id,
        field_key=field_key,
        display_name=display_name,
        is_required=is_required,
        is_system=False,
        data_type=data_type
    )
    db.session.add(new_field)
    db.session.commit()
    
    return jsonify({
        "message": "Custom field added successfully",
        "field": {
            "id": new_field.id,
            "field_key": new_field.field_key,
            "display_name": new_field.display_name,
            "is_required": new_field.is_required,
            "is_system": new_field.is_system,
            "data_type": new_field.data_type
        }
    }), 201

@admin_bp.route('/users/custom-fields/<int:field_id>', methods=['DELETE'])
@admin_required
def delete_custom_field(field_id):
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    org_id = current_user.org_id
    if not org_id:
        first_org = Organization.query.first()
        org_id = first_org.id if first_org else 1
        
    field = UserCustomField.query.filter_by(id=field_id, org_id=org_id).first_or_404()
    if field.is_system:
        return jsonify({"message": "Cannot delete system default compulsory fields"}), 400
        
    from sqlalchemy import text
    try:
        db.session.execute(text(f"ALTER TABLE users DROP COLUMN IF EXISTS {field.field_key};"))
        db.session.commit()
    except Exception as ddl_err:
        db.session.rollback()
        return jsonify({"message": "Failed to update database schema", "error": str(ddl_err)}), 500
        
    db.session.delete(field)
    db.session.commit()
    
    return jsonify({"message": "Custom field deleted successfully"}), 200

# ─── Login Options ─────────────────────────────────────────────────────────────

@admin_bp.route('/login-options', methods=['GET'])
@admin_required
def get_login_options():
    """Return which field keys are allowed as login identifiers for this org."""
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    org = current_user.organization
    if not org:
        return jsonify({"message": "Organization not found"}), 404

    # Always include email (system default) even if not explicitly set
    options = org.login_options or ["email"]
    if "email" not in options:
        options = ["email"] + options

    # Also return all available custom fields so the admin can pick from them
    custom_fields = UserCustomField.query.filter_by(org_id=org.id).order_by(UserCustomField.created_at).all()
    available_fields = [
        {
            "key": "email",
            "label": "Email ID",
            "is_system": True,
            "can_disable": False   # email is always mandatory login
        },
        {
            "key": "username",
            "label": "Username",
            "is_system": True,
            "can_disable": True
        }
    ]
    for cf in custom_fields:
        if not cf.is_system:
            available_fields.append({
                "key": cf.field_key,
                "label": cf.display_name,
                "is_system": False,
                "can_disable": True
            })

    return jsonify({
        "login_options": options,
        "available_fields": available_fields
    }), 200


@admin_bp.route('/login-options', methods=['PUT'])
@admin_required
def update_login_options():
    """Update which field keys are allowed as login identifiers for this org."""
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    org = current_user.organization
    if not org:
        return jsonify({"message": "Organization not found"}), 404

    data = request.get_json()
    new_options = data.get("login_options", [])

    # Ensure at least email is always present
    if not isinstance(new_options, list):
        return jsonify({"message": "login_options must be a list"}), 400
    if "email" not in new_options:
        new_options = ["email"] + new_options

    # Validate: only allow known field keys (email, username, + custom field keys of this org)
    valid_keys = {"email", "username"}
    custom_fields = UserCustomField.query.filter_by(org_id=org.id).all()
    for cf in custom_fields:
        valid_keys.add(cf.field_key)

    invalid = [k for k in new_options if k not in valid_keys]
    if invalid:
        return jsonify({"message": f"Unknown field keys: {invalid}"}), 400

    org.login_options = new_options
    db.session.commit()

    return jsonify({
        "message": "Login options updated successfully",
        "login_options": new_options
    }), 200

@admin_bp.route('/users/template', methods=['GET'])
@admin_required
def download_users_template():
    import io
    import csv
    from flask import Response
    
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    org_id = current_user.org_id
    if not org_id:
        first_org = Organization.query.first()
        org_id = first_org.id if first_org else 1
        
    custom_fields = UserCustomField.query.filter_by(org_id=org_id).order_by(UserCustomField.created_at).all()
    base_headers = ['username', 'email', 'role', 'plant_location', 'department', 'full_name', 'password']
    custom_headers = [f.field_key for f in custom_fields if f.field_key not in base_headers]
    headers = base_headers + custom_headers
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    
    sample_row = ['john_doe', 'john.doe@example.com', 'Team Member', 'Unit 1 - Pune', 'Manufacturing', 'John Doe', 'Welcome@123']
    sample_row += [''] * len(custom_headers)
    writer.writerow(sample_row)
    
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=qcms_users_bulk_template.csv'
    return response

@admin_bp.route('/users/bulk-upload', methods=['POST'])
@admin_required
def bulk_upload_users():
    from sqlalchemy import func as sqlfunc
    import csv
    import io

    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404

    org_id = current_user.org_id
    if not org_id:
        first_org = Organization.query.first()
        org_id = first_org.id if first_org else 1

    if 'file' not in request.files:
        return jsonify({"message": "No file part in the request"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "No file selected"}), 400
    if not (file.filename.endswith('.csv') or file.filename.endswith('.txt')):
        return jsonify({"message": "Invalid file format. Please upload a CSV template."}), 400

    try:
        stream = io.StringIO(file.stream.read().decode("utf-8"), newline=None)
        csv_reader = csv.DictReader(stream)
    except Exception as parse_err:
        return jsonify({"message": f"Failed to parse file: {str(parse_err)}"}), 400

    # ------------------------------------------------------------------
    # Pre-load org-scoped plants and departments into lookup maps
    # (case-insensitive: key = lower-stripped name or code)
    # ------------------------------------------------------------------
    all_plants = Plant.query.filter_by(org_id=org_id).all()
    plant_map = {}
    for p in all_plants:
        if p.name:
            plant_map[p.name.strip().lower()] = p
        if p.code:
            plant_map[p.code.strip().lower()] = p

    all_depts = Department.query.filter_by(org_id=org_id).all()
    dept_map = {d.name.strip().lower(): d for d in all_depts if d.name}

    added_count = 0
    rejected_count = 0
    rejected_rows = []   # detailed list shown to user after import
    valid_roles = {r.name.strip().lower(): r for r in Role.query.all()}
    custom_field_defs = UserCustomField.query.filter_by(org_id=org_id).all()

    row_num = 1
    for row in csv_reader:
        row_num += 1
        username      = (row.get('username') or row.get('User Name') or '').strip()
        email         = (row.get('email') or row.get('Email Address') or '').strip()
        role_name     = (row.get('role') or row.get('Role') or '').strip()
        plant_raw     = (row.get('plant_location') or row.get('plant') or row.get('location') or row.get('Plant') or row.get('Location') or row.get('Plant / Location') or '').strip()
        dept_raw      = (row.get('department') or row.get('dept') or row.get('Department') or row.get('Dept') or row.get('Department Name') or '').strip()
        full_name     = (row.get('full_name') or row.get('Full Name') or '').strip() or username
        password      = (row.get('password') or row.get('Password') or '').strip() or 'Welcome@123'

        def reject(reason):
            nonlocal rejected_count
            rejected_count += 1
            rejected_rows.append({
                "row":            row_num,
                "username":       username,
                "email":          email,
                "role":           role_name,
                "plant_location": plant_raw,
                "department":     dept_raw,
                "full_name":      full_name,
                "password":       password,
                "reason":         reason
            })

        # ── 1. Required base fields ────────────────────────────────────
        if not username or not email or not role_name:
            reject("Username, email, and role are required.")
            continue

        # ── 2. Plant Location validation / auto-matching ────────────────
        matched_plant = None
        if plant_raw and plant_raw.lower() not in ('', 'n/a', 'none', 'all'):
            p_key = plant_raw.strip().lower()
            matched_plant = plant_map.get(p_key)
            if not matched_plant:
                for p_name, p_obj in plant_map.items():
                    if p_key in p_name or p_name in p_key or ('bengaluru' in p_key and 'bangalore' in p_name) or ('bangalore' in p_key and 'bengaluru' in p_name):
                        matched_plant = p_obj
                        break
            if not matched_plant:
                try:
                    code_val = ''.join([w[0].upper() for w in plant_raw.split() if w])[:4] or 'PL'
                    matched_plant = Plant(org_id=org_id, name=plant_raw, code=code_val, location=plant_raw)
                    db.session.add(matched_plant)
                    db.session.commit()
                    plant_map[p_key] = matched_plant
                except Exception as p_err:
                    db.session.rollback()
                    reject(f"Could not resolve or create plant location '{plant_raw}': {str(p_err)}")
                    continue

        # ── 3. Department validation / auto-matching ───────────────────
        matched_dept = None
        if dept_raw and dept_raw.lower() not in ('', 'n/a', 'none', 'all'):
            d_key = dept_raw.strip().lower()
            matched_dept = dept_map.get(d_key)
            if not matched_dept:
                for d_name, d_obj in dept_map.items():
                    if d_key in d_name or d_name in d_key or ('manufacture' in d_key and 'manufacturing' in d_name) or ('manufacturing' in d_key and 'manufacture' in d_name):
                        matched_dept = d_obj
                        break
            if not matched_dept:
                try:
                    matched_dept = Department(org_id=org_id, plant_id=matched_plant.id if matched_plant else None, name=dept_raw)
                    db.session.add(matched_dept)
                    db.session.commit()
                    dept_map[d_key] = matched_dept
                except Exception as d_err:
                    db.session.rollback()
                    reject(f"Could not resolve or create department '{dept_raw}': {str(d_err)}")
                    continue

        # Ensure matched department is linked to matched plant
        if matched_dept and matched_plant and not matched_dept.plant_id:
            try:
                matched_dept.plant_id = matched_plant.id
                db.session.commit()
            except Exception:
                db.session.rollback()

        # ── 4. Role validation ─────────────────────────────────────────
        role = valid_roles.get(role_name.strip().lower())
        if not role:
            for r_key, r_obj in valid_roles.items():
                if role_name.strip().lower() in r_key or r_key in role_name.strip().lower():
                    role = r_obj
                    break
        if not role:
            reject(f"Invalid role: '{role_name}'.")
            continue

        # ── 5. Duplicate email / username ──────────────────────────────
        if User.query.filter_by(email=email).first():
            reject("Email already exists in the system.")
            continue
        if User.query.filter_by(username=username).first():
            reject("Username is already taken.")
            continue

        # ── 6. Subscription limit ──────────────────────────────────────
        can_add, limit_msg = SubscriptionManager.check_user_limit(org_id)
        if not can_add:
            reject(f"Organisation user limit reached: {limit_msg}")
            break

        # ── 7. Custom field validation ─────────────────────────────────
        missing_required = []
        custom_values = {}
        type_validation_error = None
        for fd in custom_field_defs:
            if fd.field_key in ('username', 'role', 'department', 'plant_location'):
                continue
            val = (row.get(fd.field_key) or '').strip()
            if fd.is_required and not val:
                missing_required.append(fd.display_name)
            if val:
                err = validate_custom_field_value(fd.display_name, val, fd.data_type)
                if err:
                    type_validation_error = err
                    break
                custom_values[fd.field_key] = val

        if missing_required:
            reject(f"Required fields missing: {', '.join(missing_required)}")
            continue
        if type_validation_error:
            reject(type_validation_error)
            continue

        # ── 8. Create user ─────────────────────────────────────────────
        try:
            new_user = User(
                username=username,
                full_name=full_name,
                email=email,
                hashed_password=bcrypt.generate_password_hash(password).decode('utf-8'),
                role_id=role.id,
                plant_id=matched_plant.id if matched_plant else None,
                department_id=matched_dept.id if matched_dept else None,
                org_id=org_id,
                is_temp_password=True,
                is_verified=True,
                status='Active',
                custom_fields=custom_values
            )
            db.session.add(new_user)
            db.session.commit()

            if custom_values:
                from sqlalchemy import text
                update_cols = ", ".join(f"{k} = :val_{k}" for k in custom_values.keys())
                params = {f"val_{k}": v for k, v in custom_values.items()}
                params["user_id"] = new_user.id
                db.session.execute(text(f"UPDATE users SET {update_cols} WHERE id = :user_id"), params)
                db.session.commit()

            added_count += 1
            try:
                EmailUtils.send_temp_password_email(new_user, password)
            except Exception as mail_err:
                current_app.logger.error(f"Bulk import welcome email failed for {email}: {mail_err}")

            log_action(current_user.id, "CREATE_USER_BULK", current_user.org_id,
                       "users", new_user.id, {"username": new_user.username})

        except Exception as create_err:
            db.session.rollback()
            reject(f"Database insertion failed: {str(create_err)}")
            continue

    total_processed = row_num - 1
    return jsonify({
        "message": "Bulk user import completed.",
        "total_processed": total_processed,
        "accepted_count": added_count,
        "rejected_count": rejected_count,
        "pending_count": 0,
        "rejected_rows":  rejected_rows
    }), 200

@admin_bp.route('/users/<int:user_id>', methods=['PUT', 'PATCH'])
@admin_required
def update_user(user_id):
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    user = User.query.join(Role).filter(
        User.id == user_id, 
        User.org_id == current_user.org_id,
        Role.name != 'SuperAdmin'
    ).first_or_404()
    data = request.get_json()
    if not data:
        return jsonify({"message": "No data provided"}), 200
    
    if data.get('username'):
        user.username = data.get('username')
    
    if data.get('full_name'):
        user.full_name = data.get('full_name')

    if data.get('email'):
        email = data.get('email')
        # Check if email is already taken by another user
        existing = User.query.filter(User.email == email, User.id != user_id).first()
        if existing:
            return jsonify({"message": "Email already in use"}), 400
        user.email = email

    if data.get('role'):
        role = Role.query.filter_by(name=data.get('role')).first()
        if role: user.role_id = role.id
    
    dept_input = data.get('department') or data.get('dept_name')
    if dept_input:
        if dept_input == 'N/A':
            user.department_id = None
        else:
            dept = None
            # Try as ID first if numeric
            if str(dept_input).isdigit():
                dept = Department.query.filter_by(id=int(dept_input), org_id=current_user.org_id).first()
            
            # Try as Name if not found
            if not dept:
                dept = Department.query.filter_by(name=str(dept_input), org_id=current_user.org_id).first()
                
            if not dept and not str(dept_input).isdigit():
                dept = Department(name=str(dept_input), org_id=current_user.org_id)
                db.session.add(dept)
                db.session.flush()
                
            if dept:
                user.department_id = dept.id
                if dept.plant_id and not ('plant_id' in data or 'plant' in data):
                    user.plant_id = dept.plant_id

    if 'plant_id' in data or 'plant' in data:
        pid = data.get('plant_id') or data.get('plant')
        user.plant_id = int(pid) if pid and str(pid).isdigit() else None
        
    if 'is_active' in data:
        user.is_active = data.get('is_active')
        if not user.is_active:
            user.deactivated_at = datetime.utcnow()
        else:
            user.deactivated_at = None
            # Auto-resolve pending reactivation tickets for this user
            try:
                SupportTicket.query.filter_by(user_id=user.id, category='User Access', status='Open').update({
                    'status': 'Resolved',
                    'resolved_at': datetime.utcnow(),
                    'resolution': 'Account reactivated by Organization Administrator.'
                })
                notif = Notification(
                    org_id=user.org_id,
                    user_id=user.id,
                    title="Account Reactivated",
                    message="Your account has been reactivated by your administrator. You now have full access to your dashboard.",
                    link="/dashboard/dashboard.html"
                )
                db.session.add(notif)
            except Exception as e:
                print("Failed to auto-resolve tickets/notify user on reactivation:", e)

    if data.get('password'):
        user.password = data.get('password')
        user.is_temp_password = True
        
    custom_field_defs = UserCustomField.query.filter_by(org_id=user.org_id).all()
    custom_values = user.custom_fields or {}
    if not isinstance(custom_values, dict):
        custom_values = {}
        
    updated_customs = {}
    for fd in custom_field_defs:
        if fd.field_key in ('username', 'role', 'department'):
            continue
        if fd.field_key in data:
            val_str = str(data[fd.field_key]).strip()
            if fd.is_required and not val_str:
                return jsonify({"message": f"Compulsory field '{fd.display_name}' cannot be empty"}), 400
            err = validate_custom_field_value(fd.display_name, val_str, fd.data_type)
            if err:
                return jsonify({"message": err}), 400
            custom_values[fd.field_key] = val_str
            updated_customs[fd.field_key] = val_str
            
    user.custom_fields = custom_values
        
    try:
        db.session.commit()
        if updated_customs:
            update_cols = ", ".join(f"{k} = :val_{k}" for k in updated_customs.keys())
            params = {f"val_{k}": v for k, v in updated_customs.items()}
            params["user_id"] = user.id
            from sqlalchemy import text
            db.session.execute(text(f"UPDATE users SET {update_cols} WHERE id = :user_id"), params)
            db.session.commit()
        log_action(current_user.id, "UPDATE_USER", current_user.org_id, "users", user.id, data)
        return jsonify({
            "message": "User updated successfully",
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role.name,
                "department": user.dept.name if user.dept else "N/A"
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to update user", "error": str(e)}), 500


@admin_bp.route('/users/<int:user_id>/regenerate-credentials', methods=['POST'])
@admin_required
def regenerate_credentials(user_id):
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
        
    user = User.query.join(Role).filter(
        User.id == user_id, 
        User.org_id == current_user.org_id,
        Role.name != 'SuperAdmin'
    ).first_or_404()
    
    # Generate new random password
    import string
    import random
    new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    
    try:
        user.hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        user.is_temp_password = True
        db.session.commit()
        
        # Send email
        EmailUtils.send_temp_password_email(user, new_password)
        
        log_action(current_user.id, "REGENERATE_CREDENTIALS", current_user.org_id, "users", user.id)
        return jsonify({"message": "New temporary credentials generated and emailed successfully."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to regenerate credentials", "error": str(e)}), 500

def disassociate_and_delete_user(target_user, admin_user_id=None):
    """
    Safely remove user record permanently from users table while
    disassociating audit logs and project references so historical
    records remain 100% intact with deleted user timestamp notes.
    """
    uid = target_user.id
    org_id = target_user.org_id
    uname = target_user.username
    uemail = target_user.email
    now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    import app.infrastructure.database.models.models as models_mod
    from app.infrastructure.database.models.models import AuditLog

    # 1. Clean audit logs owned by target_user
    try:
        AuditLog.query.filter_by(user_id=uid).delete(synchronize_session=False)
    except Exception as e:
        print(f"[DELETE USER AUDIT LOG WARNING] {e}")

    # 2. Log explicit deletion audit record
    if admin_user_id:
        try:
            log_action(
                admin_user_id,
                "DELETE_USER",
                org_id,
                "users",
                None,
                {
                    "deleted_user_id": uid,
                    "deleted_username": uname,
                    "deleted_email": uemail,
                    "deleted_at": now_str,
                    "note": f"User '{uname}' ({uemail}) was permanently deleted on {now_str}."
                }
            )
        except Exception:
            pass

    # 3. Disassociate optional nullable FK references across all modules
    nullify_specs = [
        ('ProjectReview', 'reviewer_id'),
        ('Project', 'creator_id'),
        ('Project', 'team_leader_id'),
        ('Project', 'facilitator_id'),
        ('Project', 'reviewer_id'),
        ('SOP', 'owner_id'),
        ('SOP', 'author_id'),
        ('SOP', 'reviewer_id'),
        ('SOP', 'approver_id'),
        ('SupportTicket', 'user_id'),
        ('SupportTicket', 'assigned_engineer_id'),
        ('FacilitatorNote', 'created_by'),
        ('IssueEscalation', 'escalated_by_id'),
        ('IssueEscalation', 'escalated_to_id'),
        ('LessonLearned', 'created_by_id'),
        ('KnowledgeRepository', 'created_by_id'),
        ('KnowledgeRepositoryVerification', 'verified_by_id'),
        ('SOPVersionHistory', 'changed_by_id'),
        ('SOPAssignment', 'assigned_by_id'),
        ('StandardizationDocument', 'uploaded_by_id')
    ]
    for model_name, attr_name in nullify_specs:
        try:
            model_cls = getattr(models_mod, model_name, None)
            if model_cls and hasattr(model_cls, attr_name):
                model_cls.query.filter(getattr(model_cls, attr_name) == uid).update({attr_name: None}, synchronize_session=False)
        except Exception as e:
            print(f"[DELETE USER NULLIFY WARNING {model_name}.{attr_name}] {e}")

    # 4. Delete user-owned child records (ephemeral / activity logs)
    delete_specs = [
        ('ProjectMember', 'user_id'),
        ('EmployeeLeaderboard', 'employee_id'),
        ('EmployeePoints', 'employee_id'),
        ('SaaSUserSession', 'user_id'),
        ('Notification', 'user_id'),
        ('MeetingLog', 'user_id'),
        ('TeamMemberLog', 'user_id'),
        ('KnowledgeRepositoryRating', 'user_id'),
        ('SOPTraining', 'user_id'),
        ('SOPComment', 'user_id'),
        ('SOPFeedback', 'user_id'),
        ('SOPQuizAttempt', 'user_id'),
        ('SOPCertificate', 'user_id')
    ]
    for model_name, attr_name in delete_specs:
        try:
            model_cls = getattr(models_mod, model_name, None)
            if model_cls and hasattr(model_cls, attr_name):
                model_cls.query.filter(getattr(model_cls, attr_name) == uid).delete(synchronize_session=False)
        except Exception as e:
            print(f"[DELETE USER CHILD DELETE WARNING {model_name}.{attr_name}] {e}")

    # 5. Execute hard delete on target_user
    db.session.delete(target_user)


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    current_user_id = int(get_jwt_identity())
    current_user = db.session.get(User, current_user_id)
    
    if user_id == current_user_id:
        return jsonify({"message": "You cannot delete your own account."}), 400
        
    sa_role = Role.query.filter_by(name='SuperAdmin').first()
    sa_role_id = sa_role.id if sa_role else None

    query = User.query.filter(
        User.id == user_id, 
        User.org_id == current_user.org_id
    )
    if sa_role_id:
        query = query.filter(User.role_id != sa_role_id)
    user = query.first_or_404()

    try:
        disassociate_and_delete_user(user, admin_user_id=current_user_id)
        db.session.commit()
        return jsonify({"message": "User permanently deleted."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to delete user", "error": str(e)}), 500


@admin_bp.route('/users/bulk-action', methods=['POST'])
@admin_required
def bulk_user_action():
    current_user_id = int(get_jwt_identity())
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404

    data = request.get_json() or {}
    user_ids = data.get('user_ids', [])
    action = data.get('action')

    if not user_ids or not isinstance(user_ids, list):
        return jsonify({"message": "No users selected"}), 400

    if action not in ('activate', 'deactivate', 'delete', 'resend_credentials'):
        return jsonify({"message": "Invalid bulk action"}), 400

    try:
        user_ids = [int(i) for i in user_ids]
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid user ID format"}), 400

    sa_role = Role.query.filter_by(name='SuperAdmin').first()
    sa_role_id = sa_role.id if sa_role else None

    query = User.query.filter(
        User.id.in_(user_ids),
        User.org_id == current_user.org_id
    )
    if sa_role_id:
        query = query.filter(User.role_id != sa_role_id)

    targets = query.all()

    if not targets:
        return jsonify({"message": "No valid eligible users found for this operation"}), 404

    success_count = 0
    skipped_count = 0
    errors = []

    if action == 'activate':
        for u in targets:
            u.is_active = True
            u.status = 'Active'
            success_count += 1
        db.session.commit()
        log_action(current_user.id, "BULK_ACTIVATE_USERS", current_user.org_id, "users", None, {"count": success_count})
        return jsonify({"status": "success", "message": f"Successfully activated {success_count} user(s).", "affected": success_count}), 200

    elif action == 'deactivate':
        for u in targets:
            if u.id == current_user_id:
                skipped_count += 1
                continue
            u.is_active = False
            u.status = 'Inactive'
            success_count += 1
        db.session.commit()
        log_action(current_user.id, "BULK_DEACTIVATE_USERS", current_user.org_id, "users", None, {"count": success_count})
        return jsonify({"status": "success", "message": f"Successfully deactivated {success_count} user(s).", "affected": success_count, "skipped": skipped_count}), 200

    elif action == 'resend_credentials':
        import string, random
        for u in targets:
            try:
                new_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                u.hashed_password = bcrypt.generate_password_hash(new_pass).decode('utf-8')
                u.is_temp_password = True
                EmailUtils.send_temp_password_email(u, new_pass)
                success_count += 1
            except Exception as err:
                skipped_count += 1
                errors.append(f"{u.username}: {str(err)}")
        db.session.commit()
        log_action(current_user.id, "BULK_RESEND_CREDENTIALS", current_user.org_id, "users", None, {"count": success_count})
        return jsonify({"status": "success", "message": f"Sent new credentials to {success_count} user(s).", "affected": success_count, "skipped": skipped_count}), 200

    elif action == 'delete':
        deleted_ids = []
        for u in targets:
            if u.id == current_user_id:
                skipped_count += 1
                errors.append(f"{u.username}: Cannot delete your own account.")
                continue

            try:
                disassociate_and_delete_user(u, admin_user_id=current_user_id)
                success_count += 1
                deleted_ids.append(u.id)
            except Exception as err:
                skipped_count += 1
                errors.append(f"{u.username}: {str(err)}")

        db.session.commit()
        log_action(current_user.id, "BULK_DELETE_USERS", current_user.org_id, "users", None, {"count": success_count, "deleted_ids": deleted_ids})
        return jsonify({
            "status": "success",
            "message": f"Successfully deleted {success_count} user(s).",
            "affected": success_count,
            "skipped": skipped_count,
            "errors": errors
        }), 200


# --- System Dashboard ---

@admin_bp.route('/stats', methods=['GET'])
@admin_required
def get_stats():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    org_id = current_user.org_id
    
    user_count = User.query.filter_by(org_id=org_id).count()
    project_count = Project.query.filter_by(org_id=org_id).count()
    
    # Active Pipeline: Anything not Closed or Archived
    active_projects = Project.query.filter(
        Project.org_id == org_id, 
        ~Project.status.in_(['Closed', 'Archived'])
    ).count()
    
    completed_projects = Project.query.filter(
        Project.org_id == org_id, 
        Project.status.in_(['Closed', 'Archived'])
    ).count()
    
    # Calculate pending validations — stages awaiting reviewer/admin approval (Stage 1-7 submitted for review + Stage 8 pending closure)
    from app.infrastructure.database.models.models import ProjectStageTracker
    pending_submissions = db.session.query(Project.id).join(
        ProjectStageTracker,
        sa.and_(
            ProjectStageTracker.project_id == Project.id,
            ProjectStageTracker.stage_number == Project.current_stage
        )
    ).filter(
        Project.org_id == org_id,
        Project.current_stage > 1,
        Project.current_stage < 8,
        ProjectStageTracker.status == 'Submitted For Review'
    ).count()

    pending_closures = Project.query.filter(
        Project.org_id == org_id,
        Project.current_stage == 8,
        Project.status.in_(['Pending Closure', 'SOP Created'])
    ).count()

    pending_validations = pending_submissions + pending_closures
    
    stages = db.session.query(ProjectStageTracker.stage_number, sa.func.count(ProjectStageTracker.id))\
        .filter(ProjectStageTracker.org_id == org_id, ProjectStageTracker.status == 'In Progress')\
        .group_by(ProjectStageTracker.stage_number).all()
    
    plant_count = Plant.query.filter_by(org_id=org_id).count()
    
    return jsonify({
        "users": user_count,
        "total_members": user_count,
        "projects": project_count,
        "active_projects": active_projects,
        "completed_projects": completed_projects,
        "pending_validations": pending_validations,
        "total_plants": plant_count,
        "stage_distribution": dict(stages)
    }), 200


@admin_bp.route('/plants/directory-breakdown', methods=['GET'])
@admin_required
def get_plant_directory_breakdown():
    """Returns detailed hierarchical breakdown of plants, departments, running/closed projects, and members count."""
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    org_id = current_user.org_id

    plants = Plant.query.filter_by(org_id=org_id).order_by(Plant.name).all()
    all_depts = Department.query.filter_by(org_id=org_id).order_by(Department.name).all()
    all_users = User.query.filter_by(org_id=org_id).all()
    all_projects = Project.query.filter_by(org_id=org_id).all()

    # Pre-group departments by plant_id
    plant_depts = {p.id: [] for p in plants}
    unassigned_depts = []

    for d in all_depts:
        if d.plant_id and d.plant_id in plant_depts:
            plant_depts[d.plant_id].append(d)
        else:
            unassigned_depts.append(d)

    total_org_running = 0
    total_org_closed = 0
    total_org_members = len(all_users)
    total_org_departments = len(all_depts)

    plant_data_list = []

    for p in plants:
        depts_in_plant = plant_depts.get(p.id, [])
        dept_breakdown = []

        plant_running = 0
        plant_closed = 0
        plant_members_set = set()

        for d in depts_in_plant:
            # Users belonging to this department (or plant)
            d_users = [u for u in all_users if u.department_id == d.id]
            for u in d_users:
                plant_members_set.add(u.id)

            # Projects in this department
            d_projects = [pr for pr in all_projects if pr.department_id == d.id]
            d_running = len([pr for pr in d_projects if str(pr.status or '').strip() not in ('Closed', 'Archived', 'Completed')])
            d_closed = len([pr for pr in d_projects if str(pr.status or '').strip() in ('Closed', 'Archived', 'Completed')])

            plant_running += d_running
            plant_closed += d_closed

            dept_breakdown.append({
                "id": d.id,
                "name": d.name,
                "running_projects": d_running,
                "closed_projects": d_closed,
                "total_members": len(d_users),
                "members": [
                    {
                        "id": u.id,
                        "name": u.full_name or u.username,
                        "email": u.email,
                        "role": u.role.name if u.role else "Member"
                    }
                    for u in d_users
                ]
            })

        # Also add users explicitly assigned to this plant via plant_id
        direct_plant_users = [u for u in all_users if u.plant_id == p.id]
        for u in direct_plant_users:
            plant_members_set.add(u.id)

        total_org_running += plant_running
        total_org_closed += plant_closed

        plant_data_list.append({
            "id": p.id,
            "name": p.name,
            "code": p.code or f"PLANT-{p.id}",
            "location": p.location or p.name,
            "total_departments": len(depts_in_plant),
            "total_members": len(plant_members_set),
            "running_projects": plant_running,
            "closed_projects": plant_closed,
            "departments": dept_breakdown
        })

    # Include unassigned departments if any exist
    if unassigned_depts:
        unassigned_breakdown = []
        u_running_total = 0
        u_closed_total = 0
        u_members_set = set()

        for d in unassigned_depts:
            d_users = [u for u in all_users if u.department_id == d.id]
            for u in d_users:
                u_members_set.add(u.id)

            d_projects = [pr for pr in all_projects if pr.department_id == d.id]
            d_running = len([pr for pr in d_projects if str(pr.status or '').strip() not in ('Closed', 'Archived', 'Completed')])
            d_closed = len([pr for pr in d_projects if str(pr.status or '').strip() in ('Closed', 'Archived', 'Completed')])

            u_running_total += d_running
            u_closed_total += d_closed

            unassigned_breakdown.append({
                "id": d.id,
                "name": d.name,
                "running_projects": d_running,
                "closed_projects": d_closed,
                "total_members": len(d_users),
                "members": [
                    {
                        "id": u.id,
                        "name": u.full_name or u.username,
                        "email": u.email,
                        "role": u.role.name if u.role else "Member"
                    }
                    for u in d_users
                ]
            })

        plant_data_list.append({
            "id": 0,
            "name": "General / Unassigned Location",
            "code": "HQ-GENERAL",
            "location": "Global / Unassigned",
            "total_departments": len(unassigned_depts),
            "total_members": len(u_members_set),
            "running_projects": u_running_total,
            "closed_projects": u_closed_total,
            "departments": unassigned_breakdown
        })

    return jsonify({
        "summary": {
            "total_plants": len(plants),
            "total_departments": total_org_departments,
            "total_members": total_org_members,
            "running_projects": total_org_running,
            "closed_projects": total_org_closed
        },
        "plants": plant_data_list
    }), 200


# --- Close Project (Module 3 + Module 6 trigger) ---

@admin_bp.route('/projects/<int:project_id>/close', methods=['POST'])
@admin_required
def close_project(project_id):
    """Admin project closure restricted — only Reviewers can close projects."""
    return jsonify({"message": "Unauthorized: Project closure can only be performed by a Reviewer."}), 403

# --- All Projects (Admin view) ---

@admin_bp.route('/all-projects', methods=['GET'])
@admin_required
def get_all_projects():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404

    page_param = request.args.get('page', type=int)
    per_page_param = request.args.get('per_page', type=int, default=5)
    status_param = request.args.get('status', type=str, default='').strip()
    search_param = request.args.get('search', type=str, default='').strip()

    base_query = Project.query.filter_by(org_id=current_user.org_id)
    all_org_projects = base_query.all()

    if page_param is None:
        results = []
        for p in all_org_projects:
            dept = db.session.get(Department, p.department_id) if p.department_id else None
            results.append({
                "id": p.id,
                "project_uid": p.project_uid,
                "title": p.title,
                "stage": p.current_stage,
                "status": p.status,
                "category": p.category,
                "department": dept.name if dept else "N/A",
                "created_at": p.created_at.isoformat() + "Z" if p.created_at else None,
                "facilitator_id": p.facilitator_id,
                "team_leader_id": p.team_leader_id,
                "creator_id": p.creator_id,
                "member_ids": [m.id for m in p.members]
            })
        return jsonify(results), 200

    filtered_query = base_query
    if status_param:
        filtered_query = filtered_query.filter(Project.status == status_param)

    if search_param:
        search_pattern = f"%{search_param}%"
        filtered_query = filtered_query.filter(
            sa.or_(
                Project.title.ilike(search_pattern),
                Project.project_uid.ilike(search_pattern)
            )
        )

    total_count = filtered_query.count()
    page = max(1, page_param)
    per_page = max(1, min(100, per_page_param))
    import math
    total_pages = math.ceil(total_count / per_page) if total_count > 0 else 1

    paginated_projects = (
        filtered_query.order_by(Project.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    items = []
    for p in paginated_projects:
        dept = db.session.get(Department, p.department_id) if p.department_id else None
        items.append({
            "id": p.id,
            "project_uid": p.project_uid,
            "title": p.title,
            "stage": p.current_stage,
            "status": p.status,
            "category": p.category,
            "department": dept.name if dept else "N/A",
            "created_at": p.created_at.isoformat() + "Z" if p.created_at else None,
            "facilitator_id": p.facilitator_id,
            "team_leader_id": p.team_leader_id,
            "creator_id": p.creator_id,
            "member_ids": [m.id for m in p.members]
        })

    pending_closures = []
    for p in all_org_projects:
        if p.status in ["Pending Closure", "SOP Created"]:
            pending_closures.append({
                "id": p.id,
                "title": p.title,
                "stage": p.current_stage,
                "status": p.status
            })

    return jsonify({
        "items": items,
        "total": total_count,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "pending_closures": pending_closures,
        "all_projects_summary": [{
            "id": p.id,
            "title": p.title,
            "stage": p.current_stage,
            "category": p.category,
            "status": p.status
        } for p in all_org_projects]
    }), 200

# --- Role & Department Lists ---

@admin_bp.route('/roles', methods=['GET'])
@admin_required
def get_roles():
    roles = Role.query.all()
    return jsonify([r.name for r in roles]), 200

@admin_bp.route('/departments', methods=['GET'])
@jwt_required()
def get_departments():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
        
    plant_id = request.args.get('plant_id')
    query = Department.query.filter_by(org_id=current_user.org_id)
    if plant_id and str(plant_id).isdigit():
        query = query.filter_by(plant_id=int(plant_id))

    depts = query.order_by(Department.name).all()
    return jsonify([{
        "id": d.id, 
        "name": d.name,
        "plant_id": d.plant_id,
        "plant_name": d.plant.name if d.plant else "All Plants / Unassigned"
    } for d in depts]), 200

@admin_bp.route('/departments', methods=['POST'])
@jwt_required()
@feature_module_required('departments.create')
@admin_required
def create_department():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"message": "Department name required"}), 400

    dept_name = data['name'].strip()
    if not dept_name:
        return jsonify({"message": "Department name cannot be blank."}), 400

    plant_id = data.get('plant_id')
    plant_id_val = int(plant_id) if plant_id and str(plant_id).isdigit() else None

    # ── Case-insensitive duplicate check within the same plant + org ──
    from sqlalchemy import func as sqlfunc
    existing = Department.query.filter(
        Department.org_id == current_user.org_id,
        Department.plant_id == plant_id_val,
        sqlfunc.lower(Department.name) == dept_name.lower()
    ).first()
    if existing:
        plant_label = existing.plant.name if existing.plant else "(no plant)"
        return jsonify({
            "message": f"A department named '{existing.name}' already exists "
                       f"under '{plant_label}'. Department names must be unique "
                       f"within the same plant location (case-insensitive)."
        }), 409

    new_dept = Department(name=dept_name, plant_id=plant_id_val, org_id=current_user.org_id)
    db.session.add(new_dept)
    db.session.commit()

    log_action(current_user.id, "CREATE_DEPARTMENT", current_user.org_id, "departments", new_dept.id, {"name": new_dept.name, "plant_id": new_dept.plant_id})
    return jsonify({"message": "Department created", "id": new_dept.id}), 201

@admin_bp.route('/departments/<int:dept_id>', methods=['PUT'])
@admin_required
def update_department(dept_id):
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    dept = Department.query.filter_by(id=dept_id, org_id=current_user.org_id).first_or_404()
    data = request.get_json()

    new_name = data.get('name', dept.name).strip() if 'name' in data else dept.name
    new_plant_id = dept.plant_id
    if 'plant_id' in data:
        pid = data['plant_id']
        new_plant_id = int(pid) if pid and str(pid).isdigit() else None

    # ── Case-insensitive duplicate check (exclude self) ──
    from sqlalchemy import func as sqlfunc
    conflict = Department.query.filter(
        Department.org_id == current_user.org_id,
        Department.plant_id == new_plant_id,
        sqlfunc.lower(Department.name) == new_name.lower(),
        Department.id != dept_id
    ).first()
    if conflict:
        plant_label = conflict.plant.name if conflict.plant else "(no plant)"
        return jsonify({
            "message": f"A department named '{conflict.name}' already exists "
                       f"under '{plant_label}'. Department names must be unique "
                       f"within the same plant location (case-insensitive)."
        }), 409

    dept.name = new_name
    dept.plant_id = new_plant_id
    db.session.commit()
    log_action(current_user.id, "UPDATE_DEPARTMENT", current_user.org_id, "departments", dept.id, data)
    return jsonify({"message": "Department updated"}), 200

@admin_bp.route('/departments/<int:dept_id>', methods=['GET'])
@admin_required
def get_department_detail(dept_id):
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    dept = Department.query.filter_by(id=dept_id, org_id=current_user.org_id).first_or_404()
    return jsonify({
        "id": dept.id, 
        "name": dept.name,
        "plant_id": dept.plant_id,
        "plant_name": dept.plant.name if dept.plant else "All Plants / Unassigned"
    }), 200

@admin_bp.route('/departments/<int:dept_id>/stats', methods=['GET'])
@admin_required
def get_department_stats(dept_id):
    """Return user count for deletion confirmation dialog."""
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    dept = Department.query.filter_by(id=dept_id, org_id=current_user.org_id).first_or_404()
    user_count = User.query.filter_by(department_id=dept_id, org_id=current_user.org_id).count()
    return jsonify({
        "dept_id": dept_id,
        "dept_name": dept.name,
        "user_count": user_count
    }), 200

@admin_bp.route('/departments/<int:dept_id>', methods=['DELETE'])
@admin_required
def delete_department(dept_id):
    """
    Smart department delete.
    Body JSON params:
      action         : 'delete_users' | 'move_to_dept' | 'new_dept'
      target_dept_id : (required for move_to_dept) existing dept id to move users to
      new_dept_name  : (required for new_dept) name for the new department to create
    If no body / action supplied → old behaviour (reject if users exist).
    """
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    dept = Department.query.filter_by(id=dept_id, org_id=current_user.org_id).first_or_404()

    data   = request.get_json(silent=True) or {}
    action = data.get('action', '').strip()  # delete_users | move_to_dept | new_dept

    users_in_dept = User.query.filter_by(department_id=dept_id, org_id=current_user.org_id).all()

    if not action:
        # Legacy fallback: block if users exist
        if users_in_dept:
            return jsonify({
                "message": f"This department has {len(users_in_dept)} member(s). "
                           "Please choose what to do with them before deleting."
            }), 400
    elif action == 'delete_users':
        # Safely disassociate and delete all users in this department
        try:
            db.session.execute(db.text("ALTER TABLE audit_logs ALTER COLUMN user_id DROP NOT NULL;"))
            db.session.commit()
        except Exception:
            db.session.rollback()

        for u in users_in_dept:
            disassociate_and_delete_user(u, admin_user_id=current_user_id)

    elif action == 'move_to_dept':
        target_id = data.get('target_dept_id')
        if not target_id:
            return jsonify({"message": "'target_dept_id' is required for move_to_dept action."}), 400
        target_dept = Department.query.filter_by(id=int(target_id), org_id=current_user.org_id).first()
        if not target_dept:
            return jsonify({"message": "Target department not found in your organisation."}), 404
        for u in users_in_dept:
            u.department_id = target_dept.id
            if target_dept.plant_id:
                u.plant_id = target_dept.plant_id

    elif action == 'new_dept':
        new_name = (data.get('new_dept_name') or '').strip()
        if not new_name:
            return jsonify({"message": "'new_dept_name' is required for new_dept action."}), 400
        # Case-insensitive duplicate check
        from sqlalchemy import func as sqlfunc
        clash = Department.query.filter(
            Department.org_id == current_user.org_id,
            Department.plant_id == dept.plant_id,
            sqlfunc.lower(Department.name) == new_name.lower()
        ).first()
        if clash:
            return jsonify({"message": f"A department named '{clash.name}' already exists under this plant."}), 409
        new_dept = Department(name=new_name, plant_id=dept.plant_id, org_id=current_user.org_id)
        db.session.add(new_dept)
        db.session.flush()  # get new_dept.id
        for u in users_in_dept:
            u.department_id = new_dept.id
            if new_dept.plant_id:
                u.plant_id = new_dept.plant_id
    else:
        return jsonify({"message": f"Unknown action '{action}'."}), 400

    db.session.delete(dept)
    db.session.commit()
    log_action(current_user.id, "DELETE_DEPARTMENT", current_user.org_id, "departments", dept_id,
               {"action": action, "users_affected": len(users_in_dept)})
    return jsonify({"message": "Department deleted successfully"}), 200

# --- Organization Settings ---

@admin_bp.route('/org-settings', methods=['GET'])
@admin_required
def get_org_settings():
    identity = get_jwt_identity()
    try:
        current_user_id = int(identity)
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid token identity"}), 401
        
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
        
    org_id = current_user.org_id
    print(f"[QCMS ADMIN] Fetching settings for User ID {current_user_id}, Org ID {org_id}")
    
    org = db.session.get(Organization, org_id)
    if not org:
        print(f"[QCMS ADMIN] ERROR: Organization with ID {org_id} not found in database.")
    # Auto-approve any pending trial extensions if 5 minutes passed
    try:
        from app.presentation.routes.subscription_routes import check_and_apply_pending_trial_extensions
        check_and_apply_pending_trial_extensions(org)
    except Exception:
        pass

    # Calculate Corporate Profile completion metrics
    fields_to_check = [
        ('name', org.name, 'Legal Entity Name'),
        ('org_code', org.org_code, 'Organization Code'),
        ('industry', org.industry, 'Industry Sector'),
        ('admin_name', org.admin_name, 'Primary Admin Name'),
        ('website', org.website, 'Website URL'),
        ('email', org.email, 'Business Email'),
        ('phone', org.phone, 'Phone Number'),
        ('gst_number', org.gst_number, 'GST Number'),
        ('pan_number', org.pan_number, 'PAN Number'),
        ('address', org.address, 'HQ Address'),
        ('city', org.city, 'City'),
        ('state', org.state, 'State / Province'),
        ('country', org.country, 'Country'),
        ('zip_code', org.zip_code, 'ZIP Code')
    ]

    filled_count = sum(1 for _, v, _ in fields_to_check if v and str(v).strip())
    total_count = len(fields_to_check)
    completed_pct = int(round((filled_count / total_count) * 100))
    pending_pct = 100 - completed_pct
    is_complete = (completed_pct == 100)

    profile_completion = {
        "completed_pct": completed_pct,
        "pending_pct": pending_pct,
        "filled_count": filled_count,
        "total_count": total_count,
        "is_complete": is_complete,
        "missing_fields": [label for _, v, label in fields_to_check if not (v and str(v).strip())]
    }

    return jsonify({
        "id": org.id,
        "name": org.name,
        "org_code": org.org_code,
        "industry": org.industry,
        "website": org.website,
        "gst_number": org.gst_number,
        "pan_number": org.pan_number,
        "email": org.email,
        "phone": org.phone,
        "admin_name": org.admin_name,
        "logo_url": org.logo_url,
        "favicon_url": org.favicon_url,
        "primary_color": org.primary_color,
        "timezone": org.timezone,
        "date_format": org.date_format,
        "currency": org.currency,
        "language": org.language,
        "address": org.address,
        "city": org.city,
        "state": org.state,
        "country": org.country,
        "zip_code": org.zip_code,
        "auto_archive": org.auto_archive,
        "notifications_enabled": org.notifications_enabled,
        "maintenance_mode": org.maintenance_mode,
        "session_timeout": org.session_timeout,
        "data_retention_days": org.data_retention_days,
        "security_settings": getattr(org, 'security_settings', {}) or {},
        "compliance_standards": org.compliance_standards,
        "subscription_plan": org.subscription_plan,
        "subscription_status": org.subscription_status,
        "trial_ends_at": org.trial_ends_at.isoformat() if org.trial_ends_at else None,
        "max_users": org.max_users,
        "is_white_label": org.is_white_label,
        "multi_plant": org.multi_plant,
        "api_access": org.api_access,
        "api_key": org.api_key if org.api_access else None,
        "profile_completion": profile_completion
    }), 200


@admin_bp.route('/org-settings', methods=['PUT'])
@admin_required
def update_org_settings():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    org = db.session.get(Organization, current_user.org_id)
    if not org:
        return jsonify({"message": "Organization not found"}), 404
    data = request.get_json() or {}
    
    from app.shared.validation import (
        ValidationError,
        sanitize_payload,
        validate_string_length,
        validate_email,
        validate_phone,
        validate_gstin,
        validate_pan,
        validate_pincode
    )
    
    data = sanitize_payload(data)
    
    try:
        if 'name' in data and data['name']:
            org.name = validate_string_length(data['name'], "Organization Name", min_len=2, max_len=150)
        if 'org_code' in data:
            if data['org_code']:
                org.org_code = validate_string_length(data['org_code'], "Organization Code", min_len=2, max_len=30)
            else:
                org.org_code = None
        if 'industry' in data: org.industry = data['industry']
        if 'website' in data: org.website = data['website'] or None
        if 'gst_number' in data:
            if data['gst_number']:
                org.gst_number = validate_gstin(data['gst_number'], "GST Number", required=False)
            else:
                org.gst_number = None
        if 'pan_number' in data:
            if data['pan_number']:
                org.pan_number = validate_pan(data['pan_number'], "PAN Number", required=False)
            else:
                org.pan_number = None
        if 'email' in data and data['email']:
            org.email = validate_email(data['email'], "Organization Email", required=False)
        if 'phone' in data:
            if data['phone']:
                org.phone = validate_phone(data['phone'], "Organization Phone", required=False)
            else:
                org.phone = None
        if 'admin_name' in data: org.admin_name = data['admin_name']
        if 'logo_url' in data: org.logo_url = data['logo_url']
        if 'favicon_url' in data: org.favicon_url = data['favicon_url']
        if 'primary_color' in data: org.primary_color = data['primary_color']
        if 'timezone' in data: org.timezone = data['timezone']
        if 'date_format' in data: org.date_format = data['date_format']
        if 'currency' in data: org.currency = data['currency']
        if 'language' in data: org.language = data['language']
        if 'address' in data: org.address = data['address']
        if 'city' in data: org.city = data['city']
        if 'state' in data: org.state = data['state']
        if 'country' in data: org.country = data['country']
        if 'zip_code' in data:
            if data['zip_code']:
                org.zip_code = validate_pincode(data['zip_code'], "ZIP / PIN Code", required=False)
            else:
                org.zip_code = None
    except ValidationError as ve:
        return jsonify({"message": ve.message}), 400
    old_settings = {
        "maintenance_mode": org.maintenance_mode,
        "session_timeout": org.session_timeout,
        "data_retention_days": org.data_retention_days,
        "auto_archive": org.auto_archive,
        "notifications_enabled": org.notifications_enabled,
        "security_settings": getattr(org, 'security_settings', {}) or {}
    }

    if 'auto_archive' in data: org.auto_archive = bool(data['auto_archive'])
    if 'notifications_enabled' in data: org.notifications_enabled = bool(data['notifications_enabled'])
    if 'maintenance_mode' in data: org.maintenance_mode = bool(data['maintenance_mode'])
    if 'session_timeout' in data and data['session_timeout'] is not None:
        try:
            st = int(data['session_timeout'])
            if st < 5 or st > 1440:
                return jsonify({"message": "Session timeout must be between 5 and 1440 minutes."}), 400
            org.session_timeout = st
        except (ValueError, TypeError):
            return jsonify({"message": "Invalid session timeout value."}), 400

    if 'data_retention_days' in data and data['data_retention_days'] is not None:
        try:
            dr = int(data['data_retention_days'])
            if dr < 30 or dr > 3650:
                return jsonify({"message": "Data retention must be between 30 and 3650 days."}), 400
            org.data_retention_days = dr
        except (ValueError, TypeError):
            return jsonify({"message": "Invalid data retention value."}), 400

    if 'compliance_standards' in data: org.compliance_standards = data['compliance_standards']
    
    # Store advanced Security & Privacy settings blob (SSO, IP Whitelist, Password Policy, MFA, API Security)
    if 'security_settings' in data and isinstance(data['security_settings'], dict):
        current_sec = dict(getattr(org, 'security_settings', {}) or {})
        current_sec.update(data['security_settings'])
        if hasattr(org, 'security_settings'):
            org.security_settings = current_sec

    # Toggle API access if plan allows
    if 'api_access' in data:
        if data['api_access'] and not SubscriptionManager.has_feature(org.id, 'api_access'):
            pass
        else:
            org.api_access = data['api_access']
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Database commit failed: {str(e)}"}), 500

    new_settings = {
        "maintenance_mode": org.maintenance_mode,
        "session_timeout": org.session_timeout,
        "data_retention_days": org.data_retention_days,
        "auto_archive": org.auto_archive,
        "notifications_enabled": org.notifications_enabled,
        "security_settings": getattr(org, 'security_settings', {}) or {}
    }

    audit_delta = {
        "old": old_settings,
        "new": new_settings,
        "changed_fields": [k for k in data.keys() if k in old_settings]
    }
    
    log_action(current_user.id, "UPDATE_SECURITY_SETTINGS", current_user.org_id, "organizations", org.id, audit_delta)
    return jsonify({"message": "Security settings updated successfully", "settings": new_settings}), 200

# ── Role Access Control (RBAC) Matrix Endpoints ──
DEFAULT_ROLE_PERMISSIONS = {
    "Team Member": {
        "overview": True,
        "project_repo": True,
        "knowledge_base": True,
        "leaderboard": True,
        "additional_sources": True,
        "analytics": False,
        "user_management": False,
        "plants": False,
        "departments": False,
        "audit_logs": False,
        "stage_template": False,
        "settings": True
    },
    "CEO": {
        "overview": True,
        "project_repo": True,
        "knowledge_base": True,
        "leaderboard": True,
        "additional_sources": True,
        "analytics": True,
        "user_management": False,
        "plants": False,
        "departments": False,
        "audit_logs": False,
        "stage_template": False,
        "settings": True
    },
    "Facilitator": {
        "overview": True,
        "project_repo": True,
        "knowledge_base": True,
        "leaderboard": True,
        "additional_sources": True,
        "analytics": True,
        "user_management": False,
        "plants": False,
        "departments": False,
        "audit_logs": False,
        "stage_template": False,
        "settings": True
    },
    "Reviewer": {
        "overview": True,
        "project_repo": True,
        "knowledge_base": True,
        "leaderboard": True,
        "additional_sources": True,
        "analytics": True,
        "user_management": False,
        "plants": False,
        "departments": False,
        "audit_logs": False,
        "stage_template": False,
        "settings": True
    },
    "Admin": {
        "overview": True,
        "project_repo": True,
        "knowledge_base": True,
        "leaderboard": True,
        "additional_sources": True,
        "analytics": True,
        "user_management": True,
        "plants": True,
        "departments": True,
        "audit_logs": True,
        "stage_template": True,
        "settings": True
    }
}

@admin_bp.route('/role-permissions', methods=['GET'])
@jwt_required()
def get_role_permissions():
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
        
    org_id = user.org_id or 1
    org = db.session.get(Organization, org_id) if org_id else None
    sec = getattr(org, 'security_settings', {}) or {} if org else {}
    role_perms = sec.get('role_permissions') if isinstance(sec, dict) else None

    # Check if request explicitly asks for platform defaults
    if request.args.get('defaults') == 'true' or request.args.get('reset') == 'true':
        perms_to_return = copy.deepcopy(DEFAULT_ROLE_PERMISSIONS)
    else:
        # Merge with default structure to guarantee all roles and keys exist
        perms_to_return = {}
        for role, def_keys in DEFAULT_ROLE_PERMISSIONS.items():
            perms_to_return[role] = dict(def_keys)
            if role_perms and isinstance(role_perms, dict) and role in role_perms and isinstance(role_perms[role], dict):
                perms_to_return[role].update(role_perms[role])

    return jsonify({
        "status": "success",
        "roles": ["Team Member", "CEO", "Facilitator", "Reviewer", "Admin"],
        "modules": [
            {"key": "overview", "label": "Dashboard / Overview", "icon": "layout-dashboard"},
            {"key": "project_repo", "label": "Project Repository", "icon": "layers"},
            {"key": "knowledge_base", "label": "Knowledge Base", "icon": "database"},
            {"key": "leaderboard", "label": "Leaderboard & Rewards", "icon": "award"},
            {"key": "additional_sources", "label": "Additional Sources", "icon": "sparkles"},
            {"key": "analytics", "label": "Analytics & Insights", "icon": "bar-chart-3"},
            {"key": "user_management", "label": "User Management", "icon": "users"},
            {"key": "plants", "label": "Plant Locations", "icon": "building-2"},
            {"key": "departments", "label": "Departments", "icon": "briefcase"},
            {"key": "audit_logs", "label": "Audit Logs", "icon": "scroll-text"},
            {"key": "stage_template", "label": "8 Stage Template", "icon": "layout-list"},
            {"key": "settings", "label": "Settings", "icon": "settings"}
        ],
        "permissions": perms_to_return
    }), 200

@admin_bp.route('/role-permissions/reset', methods=['POST'])
@admin_required
def reset_role_permissions_defaults():
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
        
    org_id = user.org_id or 1
    org = db.session.get(Organization, org_id) if org_id else None
    if not org:
        return jsonify({"message": "Organization not found"}), 404

    sec = dict(getattr(org, 'security_settings', {}) or {})
    sec['role_permissions'] = copy.deepcopy(DEFAULT_ROLE_PERMISSIONS)
    org.security_settings = sec
    flag_modified(org, 'security_settings')
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Role Access Control reset to platform defaults successfully.",
        "roles": ["Team Member", "CEO", "Facilitator", "Reviewer", "Admin"],
        "modules": [
            {"key": "overview", "label": "Dashboard / Overview", "icon": "layout-dashboard"},
            {"key": "project_repo", "label": "Project Repository", "icon": "layers"},
            {"key": "knowledge_base", "label": "Knowledge Base", "icon": "database"},
            {"key": "leaderboard", "label": "Leaderboard & Rewards", "icon": "award"},
            {"key": "additional_sources", "label": "Additional Sources", "icon": "sparkles"},
            {"key": "analytics", "label": "Analytics & Insights", "icon": "bar-chart-3"},
            {"key": "user_management", "label": "User Management", "icon": "users"},
            {"key": "plants", "label": "Plant Locations", "icon": "building-2"},
            {"key": "departments", "label": "Departments", "icon": "briefcase"},
            {"key": "audit_logs", "label": "Audit Logs", "icon": "scroll-text"},
            {"key": "stage_template", "label": "8 Stage Template", "icon": "layout-list"},
            {"key": "settings", "label": "Settings", "icon": "settings"}
        ],
        "permissions": copy.deepcopy(DEFAULT_ROLE_PERMISSIONS)
    }), 200

@admin_bp.route('/role-permissions', methods=['PUT'])
@admin_required
def update_role_permissions():
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
        
    org_id = user.org_id or 1
    org = db.session.get(Organization, org_id) if org_id else None
    if not org:
        return jsonify({"message": "Organization not found"}), 404
        
    data = request.get_json() or {}
    new_perms = data.get('permissions')
    if not isinstance(new_perms, dict):
        return jsonify({"message": "Invalid permissions payload"}), 400

    sec = dict(getattr(org, 'security_settings', {}) or {})
    sec['role_permissions'] = new_perms
    org.security_settings = sec

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Database commit failed: {str(e)}"}), 500

    log_action(user.id, "UPDATE_ROLE_PERMISSIONS", user.org_id, "organizations", org.id, {"permissions": new_perms})
    return jsonify({"status": "success", "message": "Role Access Control matrix updated successfully", "permissions": new_perms}), 200

@admin_bp.route('/upgrade-plan', methods=['POST'])
@admin_required
def upgrade_plan():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    org = db.session.get(Organization, current_user.org_id)

    # GST / PAN guard — required before plan purchase
    missing = []
    if not org.gst_number or not str(org.gst_number).strip():
        missing.append("GST Number")
    if not org.pan_number or not str(org.pan_number).strip():
        missing.append("PAN Number")
    if missing:
        fields = " and ".join(missing)
        return jsonify({
            "message": (
                f"Your organisation's {fields} {'are' if len(missing) > 1 else 'is'} required to "
                "purchase a plan and generate a GST invoice. "
                "Please go to Settings → Corporate Profile and enter "
                f"your {fields} before proceeding."
            ),
            "missing_fields": missing,
            "redirect": "/admin/settings.html?tab=personal"
        }), 422

    data = request.get_json()
    new_plan = data.get('plan_name')
    
    if new_plan not in ['Starter', 'Professional', 'Enterprise']:
        return jsonify({"message": "Invalid plan name"}), 400
        
    plan_config = SubscriptionManager.get_plan_config(new_plan)
    
    # Update Org with new plan limits
    org.subscription_plan = new_plan
    org.subscription_status = 'Active'
    org.max_users = plan_config['max_users']
    org.is_white_label = plan_config['white_label']
    org.multi_plant = plan_config['multi_plant']
    org.api_access = plan_config['api_access']
    
    db.session.commit()
    log_action(current_user_id, "UPGRADE_PLAN", org.id, "organizations", org.id, {"new_plan": new_plan})
    
    return jsonify({
        "message": f"Successfully upgraded to {new_plan} plan",
        "plan": new_plan
    }), 200

@admin_bp.route('/billing-history', methods=['GET'])
@admin_required
def get_billing_history():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    
    payments = SubscriptionPayment.query.filter_by(org_id=current_user.org_id)\
        .order_by(SubscriptionPayment.created_at.desc()).limit(10).all()
        
    return jsonify([{
        "id": p.id,
        "amount": p.amount,
        "currency": p.currency,
        "plan": p.plan_name,
        "status": p.payment_status,
        "date": p.created_at.isoformat() + "Z",
        "transaction_id": p.transaction_id
    } for p in payments]), 200

@admin_bp.route('/api-key/rotate', methods=['POST'])
@admin_required
def rotate_api_key():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    org = db.session.get(Organization, current_user.org_id)
    
    if not SubscriptionManager.has_feature(org.id, 'api_access'):
        return jsonify({"message": "API access is not available on your current plan. Please upgrade to Enterprise."}), 403
        
    new_key = f"qcms_live_sk_{secrets.token_urlsafe(32)}"
    org.api_key = new_key
    db.session.commit()
    
    log_action(current_user_id, "ROTATE_API_KEY", org.id, "organizations", org.id)
    
    return jsonify({
        "message": "API key rotated successfully",
        "api_key": new_key
    }), 200

@admin_bp.route('/stats/usage', methods=['GET'])
@admin_required
def get_usage_stats():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    
    stats = SubscriptionManager.get_usage_stats(current_user.org_id) or {}
    org = db.session.get(Organization, current_user.org_id)
    if org:
        sec = getattr(org, 'security_settings', {}) or {}
        auto_count = sec.get('auto_approved_trial_extensions', org.trial_extension_count or 0)
        manual_count = sec.get('manual_approved_trial_extensions', 0)
        total_reqs = sec.get('total_trial_requests', auto_count + manual_count)

        stats['total_trial_requests'] = total_reqs
        stats['auto_approved_trial_extensions'] = auto_count
        stats['manual_approved_trial_extensions'] = manual_count
        stats['trial_extension_count'] = org.trial_extension_count or 0

    return jsonify(stats), 200

# --- File Uploads ---

@admin_bp.route('/upload-evidence', methods=['POST'])
@admin_required
def upload_evidence():
    if 'file' not in request.files:
        return jsonify({"message": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "No selected file"}), 400
    
    if file:
        filename = secure_filename(file.filename)
        # Add timestamp to filename to avoid collisions
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Return the URL to access the file
        file_url = f"/uploads/{filename}"
        return jsonify({"url": file_url}), 200

# --- Enterprise Branding & Settings ---

@admin_bp.route('/org-branding/upload', methods=['POST'])
@admin_required
def upload_branding():
    if 'file' not in request.files:
        return jsonify({"message": "No file part"}), 400
    file = request.files['file']
    asset_type = request.form.get('type') # 'logo' or 'favicon'
    
    if file.filename == '':
        return jsonify({"message": "No selected file"}), 400
    
    if asset_type not in ['logo', 'favicon']:
        return jsonify({"message": "Invalid asset type"}), 400

    current_user_id = int(get_jwt_identity())
    current_user = db.session.get(User, current_user_id)
    org = db.session.get(Organization, current_user.org_id)

    if asset_type == 'logo':
        from app.domain.services.feature_engine import FeatureEngine
        if not FeatureEngine.is_enabled(current_user.org_id, 'branding.logo'):
            return jsonify({"message": "Company logo upload module is temporarily disabled. Please contact the Support team to enable this."}), 403

    if file:
        filename = secure_filename(file.filename)
        ext = os.path.splitext(filename)[1]
        new_filename = f"org_{org.id}_{asset_type}{ext}"
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], new_filename)
        
        # Ensure upload folder exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        file.save(file_path)
        file_url = f"/uploads/{new_filename}"
        
        if asset_type == 'logo':
            org.logo_url = file_url
        else:
            org.favicon_url = file_url
            
        db.session.commit()
        log_action(current_user.id, "UPDATE_BRANDING", org.id, "organizations", org.id, {"type": asset_type})
        
        return jsonify({"url": file_url}), 200

@admin_bp.route('/audit-logs', methods=['GET'])
@admin_required
def get_audit_logs():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    
    logs = AuditLog.query.filter_by(org_id=current_user.org_id)\
        .order_by(AuditLog.created_at.desc()).limit(100).all()
        
    return jsonify([{
        "id": log.id,
        "user": log.user.full_name if log.user else "System",
        "action": log.action,
        "target": f"{log.target_table} ({log.target_id})" if log.target_table else "Global",
        "details": log.details,
        "date": log.created_at.isoformat() + "Z",
        "timestamp": log.created_at.isoformat() + "Z"
    } for log in logs]), 200

@admin_bp.route('/projects/<int:project_id>/reject', methods=['POST'])
@admin_required
def reject_project(project_id):
    """Admin rejects a project closure — resets progress to Stage 1, unlocks stages, notifies team."""
    try:
        current_user_id = get_jwt_identity()
        current_user = db.session.get(User, current_user_id)
        if not current_user:
            return jsonify({"message": "User not found"}), 404
        
        project = Project.query.filter_by(id=project_id, org_id=current_user.org_id).first_or_404()
        
        if project.status == 'Closed':
            return jsonify({"message": "Project is already closed"}), 400
            
        data = request.get_json() or {}
        comments = data.get('comments', 'Rejected by Admin. Please revise all stages as needed.').strip()
        
        # Reset project status and current stage
        project.status = 'Rejected'
        project.current_stage = 1
        
        # Reset all stage trackers so progress is re-tracked from Stage 1
        # Set Stage 1 to In Progress and all others to Pending/Started/Completed = None
        for tracker in project.stage_tracker:
            if tracker.stage_number == 1:
                tracker.status = 'In Progress'
                tracker.completed_at = None
            else:
                tracker.status = 'Pending'
                tracker.started_at = None
                tracker.completed_at = None
                
        # Reset Stage 8 closure validations
        from app.infrastructure.database.models.models import Stage8StandardizationKnowledgeSharingProjectClosure
        s8 = Stage8StandardizationKnowledgeSharingProjectClosure.query.filter_by(project_id=project_id).first()
        if s8:
            s8.facilitator_validation = False
            s8.admin_closure = False
            s8.final_approval = False
            s8.final_comments = f"Rejected by Admin. Comments: {comments}"
            
        # Add a rejection review entry
        from app.infrastructure.database.models.models import ProjectReview
        review = ProjectReview(
            org_id=current_user.org_id,
            project_id=project_id,
            stage_number=8,
            reviewer_id=current_user.id,
            status='Approved',
            decision='Rejected',
            comments=comments,
            decided_at=datetime.utcnow()
        )
        db.session.add(review)
        
        # Notify team, facilitator and reviewer
        from app.presentation.routes.notification_routes import create_notification
        notify_ids = set()
        if project.team_leader_id: notify_ids.add(project.team_leader_id)
        if project.facilitator_id: notify_ids.add(project.facilitator_id)
        if project.reviewer_id: notify_ids.add(project.reviewer_id)
        if project.creator_id: notify_ids.add(project.creator_id)
        
        for uid in notify_ids:
            if uid != current_user.id:
                create_notification(
                    current_user.org_id, uid,
                    "Project Rejected & Reset",
                    f"Admin rejected closure for '{project.title}': {comments}",
                    f"/projects/project-details.html?id={project_id}",
                    commit=False
                )
            
        log_action(
            user_id=current_user.id,
            action="PROJECT_REJECTED",
            target_table="projects",
            target_id=project_id,
            details={"title": project.title, "comments": comments},
            org_id=current_user.org_id
        )
        
        db.session.commit()
        return jsonify({"message": "Project rejected and reset to Stage 1 successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in reject_project: {str(e)}")
        return jsonify({
            "message": "Internal error during project rejection",
            "error": str(e)
        }), 500


# ──────────────────────────────────────────────────────────────────────────────
# 8-Stage Workflow Template (org-level)
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/stages-template', methods=['GET'])
@admin_required
def get_stages_template():
    """Return the organisation's current 8-stage workflow configuration."""
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    org = db.session.get(Organization, user.org_id)
    return jsonify({"stages": org.get_stages_config()}), 200


@admin_bp.route('/stages-template', methods=['POST'])
@admin_required
def save_stages_template():
    """
    Save (or reset to defaults) the org-level 8-stage workflow template.
    Body: { "stages": [...], "reset": false }
    Each stage object must contain: stage_id (1-8 sequence position),
    original_id (1-8 module binding), title (string), icon (lucide name).
    """
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    org = db.session.get(Organization, user.org_id)
    data = request.get_json() or {}

    # Allow admin to reset to defaults
    if data.get('reset'):
        org.stages_config = None
        db.session.commit()
        log_action(user_id, 'STAGES_TEMPLATE_RESET', user.org_id,
                   target_table='organizations', target_id=org.id)
        return jsonify({"message": "Stage template reset to defaults.", "stages": org.get_stages_config()}), 200

    stages = data.get('stages')
    if not stages or not isinstance(stages, list) or len(stages) < 1 or len(stages) > 20:
        return jsonify({"message": "Stages list must contain between 1 and 20 stages."}), 400

    # Validate each entry
    required_keys = {'stage_id', 'original_id', 'title', 'icon'}
    seen_seq = set()
    for s in stages:
        if not required_keys.issubset(s.keys()):
            return jsonify({"message": f"Each stage must have: {required_keys}"}), 400
        sid = s['stage_id']
        oid = s['original_id']
        if not (1 <= sid <= len(stages)) or not (1 <= oid <= 8):
            return jsonify({"message": f"stage_id must be between 1 and {len(stages)}, and original_id must be 1-8."}), 400
        if sid in seen_seq:
            return jsonify({"message": f"Duplicate stage_id: {sid}"}), 400
        if not isinstance(s['title'], str) or not s['title'].strip():
            return jsonify({"message": "Every stage must have a non-empty title."}), 400
        seen_seq.add(sid)

    org.stages_config = stages
    db.session.commit()
    log_action(user_id, 'STAGES_TEMPLATE_SAVED', user.org_id,
               target_table='organizations', target_id=org.id,
               details={"stages": [s['title'] for s in stages]})
    return jsonify({"message": "Stage template saved successfully.", "stages": stages}), 200


# ===========================================================================
# Compliance Standards — real certificate data endpoints
# ===========================================================================

# Default catalogue of compliance frameworks supported by QCMS
_DEFAULT_STANDARDS = [
    {"code": "iso9001",   "name": "ISO 9001:2015",   "description": "Quality Management System",                  "icon": "award"},
    {"code": "iso14001",  "name": "ISO 14001:2015",  "description": "Environmental Management System",           "icon": "leaf"},
    {"code": "as9100",    "name": "AS9100 Rev D",    "description": "Aerospace Quality Management System",       "icon": "plane"},
    {"code": "iatf16949", "name": "IATF 16949:2016", "description": "Automotive Quality Management System",      "icon": "settings"},
    {"code": "iso45001",  "name": "ISO 45001:2018",  "description": "Occupational Health & Safety Management",   "icon": "shield"},
    {"code": "iso27001",  "name": "ISO 27001:2022",  "description": "Information Security Management System",   "icon": "lock"},
]


@admin_bp.route('/compliance/standards', methods=['GET'])
@admin_required
def get_compliance_standards():
    """Return all compliance standards for this org.
    Auto-seeds the catalogue rows on first call so no migration step is needed.
    """
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid token"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    org_id = user.org_id

    # Auto-seed: create a row for every default standard if not present
    for s in _DEFAULT_STANDARDS:
        existing = ComplianceStandard.query.filter_by(
            org_id=org_id, standard_code=s["code"]
        ).first()
        if not existing:
            row = ComplianceStandard(
                org_id=org_id,
                standard_name=s["name"],
                standard_code=s["code"],
                description=s["description"],
                icon=s["icon"],
                is_enabled=False,
                status="not_configured",
            )
            db.session.add(row)
    db.session.commit()

    records = ComplianceStandard.query.filter_by(org_id=org_id).order_by(
        ComplianceStandard.id
    ).all()
    return jsonify({"standards": [r.to_dict() for r in records]}), 200


@admin_bp.route('/compliance/standards/<string:code>', methods=['PUT'])
@admin_required
def update_compliance_standard(code):
    """Save certificate details for a specific standard."""
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid token"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    org_id = user.org_id

    record = ComplianceStandard.query.filter_by(
        org_id=org_id, standard_code=code
    ).first()
    if not record:
        return jsonify({"message": f"Standard '{code}' not found for this organisation"}), 404

    data = request.get_json() or {}

    # Update certificate fields if provided
    if 'certificate_number' in data:
        record.certificate_number = data['certificate_number'] or None
    if 'owner' in data:
        record.owner = data['owner'] or None
    if 'registrar_body' in data:
        record.registrar_body = data['registrar_body'] or None
    if 'lead_auditor' in data:
        record.lead_auditor = data['lead_auditor'] or None
    if 'framework_scope' in data:
        record.framework_scope = data['framework_scope'] or None
    if 'risk_level' in data:
        record.risk_level = data['risk_level'] or None
    if 'audit_score' in data:
        val = data['audit_score']
        record.audit_score = int(val) if val not in (None, '') else None
    if 'cert_file_url' in data:
        record.cert_file_url = data['cert_file_url'] or None

    # Parse date fields
    from datetime import date as _date
    def _parse_date(val):
        if not val:
            return None
        try:
            return _date.fromisoformat(str(val))
        except ValueError:
            return None

    if 'issue_date' in data:
        record.issue_date = _parse_date(data['issue_date'])
    if 'expiry_date' in data:
        record.expiry_date = _parse_date(data['expiry_date'])
    if 'last_audit_date' in data:
        record.last_audit_date = _parse_date(data['last_audit_date'])
    if 'next_audit_date' in data:
        record.next_audit_date = _parse_date(data['next_audit_date'])

    # Re-derive status
    record.status = record.compute_status()
    record.updated_at = datetime.utcnow()

    db.session.commit()
    log_action(user_id, 'COMPLIANCE_STANDARD_UPDATED', org_id,
               target_table='compliance_standard_records', target_id=record.id,
               details={"code": code, "status": record.status})
    return jsonify({"message": "Compliance standard updated", "standard": record.to_dict()}), 200


@admin_bp.route('/compliance/standards/<string:code>/toggle', methods=['POST'])
@admin_required
def toggle_compliance_standard(code):
    """Enable or disable a compliance standard."""
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid token"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    org_id = user.org_id

    record = ComplianceStandard.query.filter_by(
        org_id=org_id, standard_code=code
    ).first()
    if not record:
        return jsonify({"message": f"Standard '{code}' not found"}), 404

    data = request.get_json() or {}
    record.is_enabled = bool(data.get('is_enabled', not record.is_enabled))
    record.updated_at = datetime.utcnow()
    db.session.commit()
    log_action(user_id, 'COMPLIANCE_STANDARD_TOGGLED', org_id,
               target_table='compliance_standard_records', target_id=record.id,
               details={"code": code, "is_enabled": record.is_enabled})
    return jsonify({"message": "Toggle updated", "is_enabled": record.is_enabled}), 200


# ===========================================================================
# Organization API Key & Integration Management
# ===========================================================================
import secrets
import hashlib
from app.infrastructure.database.models.models import OrgApiKey, Organization

def _hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode('utf-8')).hexdigest()

@admin_bp.route('/integrations/api-key', methods=['GET'])
@jwt_required()
def get_org_api_key():
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid token"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    org_id = user.org_id

    org = db.session.get(Organization, org_id)
    org_name = org.name if org else 'Organization'

    api_key_rec = OrgApiKey.query.filter_by(organization_id=org_id).first()
    if not api_key_rec:
        return jsonify({
            "exists": False,
            "organization_name": org_name,
            "status": "Disabled",
            "usage_count": 0,
            "created_at": None,
            "last_used": None
        }), 200

    masked = api_key_rec.secret_key_masked or ""
    if "..." in masked or "•" in masked or len(masked) < 40:
        # Auto-fix legacy dot masked format to full character key
        new_raw_key = f"qcms_live_sk_{secrets.token_hex(24)}"
        api_key_rec.api_key_hash = _hash_api_key(new_raw_key)
        api_key_rec.secret_key_masked = new_raw_key
        db.session.commit()
        masked = new_raw_key

    return jsonify({
        "exists": True,
        "organization_name": org_name,
        "api_key": masked,
        "secret_key_masked": masked,
        "key_prefix": api_key_rec.key_prefix,
        "status": api_key_rec.status,
        "usage_count": api_key_rec.usage_count or 0,
        "created_at": api_key_rec.created_at.strftime('%Y-%m-%d %H:%M') if api_key_rec.created_at else None,
        "last_used": api_key_rec.last_used.strftime('%Y-%m-%d %H:%M') if api_key_rec.last_used else "Never"
    }), 200


@admin_bp.route('/integrations/api-key/generate', methods=['POST'])
@jwt_required()
def generate_org_api_key():
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid token"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    org_id = user.org_id

    # Check if key already exists
    existing = OrgApiKey.query.filter_by(organization_id=org_id).first()

    raw_key = f"qcms_live_sk_{secrets.token_hex(24)}"
    key_hash = _hash_api_key(raw_key)

    if existing:
        existing.api_key_hash = key_hash
        existing.secret_key_masked = raw_key
        existing.status = 'Active'
        existing.created_at = datetime.utcnow()
        key_rec = existing
    else:
        key_rec = OrgApiKey(
            organization_id=org_id,
            api_key_hash=key_hash,
            key_prefix="qcms_live_sk_",
            secret_key_masked=raw_key,
            status='Active',
            usage_count=0
        )
        db.session.add(key_rec)

    db.session.commit()
    log_action(user_id, 'ORG_API_KEY_GENERATED', org_id, details={"masked": raw_key})

    return jsonify({
        "success": True,
        "message": "API Key generated successfully.",
        "api_key": raw_key,
        "secret_key_masked": raw_key,
        "status": key_rec.status,
        "created_at": key_rec.created_at.strftime('%Y-%m-%d %H:%M') if key_rec.created_at else None,
        "last_used": "Never",
        "usage_count": key_rec.usage_count or 0
    }), 201


@admin_bp.route('/integrations/api-key/regenerate', methods=['POST'])
@jwt_required()
def regenerate_org_api_key():
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid token"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    org_id = user.org_id

    raw_key = f"qcms_live_sk_{secrets.token_hex(24)}"
    key_hash = _hash_api_key(raw_key)

    key_rec = OrgApiKey.query.filter_by(organization_id=org_id).first()
    if not key_rec:
        key_rec = OrgApiKey(
            organization_id=org_id,
            api_key_hash=key_hash,
            key_prefix="qcms_live_sk_",
            secret_key_masked=raw_key,
            status='Active',
            usage_count=0
        )
        db.session.add(key_rec)
    else:
        key_rec.api_key_hash = key_hash
        key_rec.secret_key_masked = raw_key
        key_rec.status = 'Active'
        key_rec.updated_at = datetime.utcnow()

    db.session.commit()
    log_action(user_id, 'ORG_API_KEY_REGENERATED', org_id, details={"masked": raw_key})

    return jsonify({
        "success": True,
        "message": "API Key regenerated successfully. The previous key is now invalidated.",
        "api_key": raw_key,
        "secret_key_masked": raw_key,
        "status": key_rec.status,
        "created_at": key_rec.created_at.strftime('%Y-%m-%d %H:%M') if key_rec.created_at else None,
        "last_used": key_rec.last_used.strftime('%Y-%m-%d %H:%M') if key_rec.last_used else "Never",
        "usage_count": key_rec.usage_count or 0
    }), 200


@admin_bp.route('/integrations/api-key/toggle-status', methods=['POST'])
@jwt_required()
def toggle_org_api_key_status():
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid token"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    org_id = user.org_id

    key_rec = OrgApiKey.query.filter_by(organization_id=org_id).first()
    if not key_rec:
        return jsonify({"message": "No API Key exists for this organization."}), 404

    data = request.get_json() or {}
    new_status = data.get('status')
    if not new_status:
        new_status = 'Disabled' if key_rec.status == 'Active' else 'Active'

    key_rec.status = new_status
    key_rec.updated_at = datetime.utcnow()
    db.session.commit()

    log_action(user_id, 'ORG_API_KEY_STATUS_CHANGED', org_id, details={"new_status": new_status})

    return jsonify({
        "success": True,
        "message": f"API Key status changed to {new_status}.",
        "status": key_rec.status
    }), 200


@admin_bp.route('/integrations/api-key', methods=['DELETE'])
@jwt_required()
def delete_org_api_key():
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid token"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    org_id = user.org_id

    key_rec = OrgApiKey.query.filter_by(organization_id=org_id).first()
    if not key_rec:
        return jsonify({"message": "No API Key found to delete."}), 404

    db.session.delete(key_rec)
    db.session.commit()

    log_action(user_id, 'ORG_API_KEY_DELETED', org_id)

    return jsonify({
        "success": True,
        "message": "API Key deleted successfully."
    }), 200


@admin_bp.route('/additional-sources/ideas', methods=['GET'])
@jwt_required()
def get_additional_sources_ideas():
    current_user_id = int(get_jwt_identity())
    user = db.session.get(User, current_user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
        
    org_id = user.org_id
    
    # 1. Attempt live sync from configured external API endpoint
    base_url = (os.environ.get('INTEGRATION_BASE_URL') or os.environ.get('BASE_URL') or request.host_url).rstrip('/')
    external_url = f"{base_url}/api/v1/integrations/ideas"
    try:
        import requests
        resp = requests.get(external_url, headers={"Accept": "application/json"}, timeout=3)
        if resp.status_code == 200 and 'json' in resp.headers.get('Content-Type', '').lower():
            ext_data = resp.json()
            ideas_list = ext_data.get('ideas') if isinstance(ext_data, dict) else (ext_data if isinstance(ext_data, list) else [])
            for item in ideas_list:
                code = item.get('ideaCode') or item.get('idea_code')
                if code and not ImportedIdea.query.filter_by(organization_id=org_id, idea_code=str(code).strip()).first():
                    new_idea = ImportedIdea(
                        organization_id=org_id,
                        idea_code=str(code).strip(),
                        title=item.get('title') or 'External Idea',
                        problem_statement=item.get('problem_statement') or item.get('presentSituation') or '',
                        proposed_solution=item.get('proposed_solution') or item.get('proposedSolution') or '',
                        department=item.get('department') or 'General',
                        category=item.get('category') or 'Quality',
                        submitted_by=item.get('submittedBy') or item.get('submitted_by') or 'External API',
                        co_suggesters=item.get('coSuggesters') or [],
                        tangible_benefit=float(item.get('tangibleBenefit') or 0.0),
                        intangible_benefit=item.get('intangibleBenefit') or '',
                        investment_required=float(item.get('investmentRequired') or 0.0),
                        implementation_time=item.get('implementationTime') or '2 Weeks',
                        impact_level=item.get('impactLevel') or 'High',
                        status=item.get('status') or 'Approved',
                        source='Cloudflare Integration API'
                    )
                    db.session.add(new_idea)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print("[Additional Sources Sync]: External API fetch skipped:", e)
        
    # 2. Query all real ideas imported for this org via API keys or live integrations
    ideas = ImportedIdea.query.filter_by(organization_id=org_id).order_by(ImportedIdea.created_at.desc()).all()

    return jsonify({
        "status": "success",
        "total": len(ideas),
        "api_endpoint": f"{base_url}/api/v1/integrations/ideas",
        "ideas": [i.to_dict() for i in ideas]
    }), 200

