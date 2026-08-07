import os
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app import db, bcrypt
import sqlalchemy as sa
from app.infrastructure.database.models.models import (
    User, Role, Department, AuditLog, Project, ProjectWorkflow,
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
from app.utils.avatar_utils import get_profile_picture_url
from app.domain.services.feature_engine import feature_module_required
from functools import wraps

admin_bp = Blueprint('admin', __name__)

# Middleware for Admin-only access (SuperAdmin also has full Admin privileges)
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
            
        return jsonify({"message": "Admin access required"}), 403
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
        if not re.match(r'^[\w.+\-]+@[\w\-]+\.[a-zA-Z]{2,}$', val_str):
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
        if fd.field_key in ('username', 'role', 'department'):
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
    
    plant_input = data.get('plant_id') or data.get('plant')
    user_plant_id = None
    if plant_input and str(plant_input).isdigit():
        user_plant_id = int(plant_input)
    elif dept and dept.plant_id:
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
        for key in ('username', 'role', 'department', 'email')
    )
    if missing_any:
        system_fields = [
            ('username', 'User', True, True, 'both'),
            ('role', 'User Role', True, True, 'both'),
            ('department', 'Department', True, True, 'both'),
            ('email', 'Email Address', True, True, 'email')
        ]
        for key, name, req, sys, dtype in system_fields:
            if not UserCustomField.query.filter_by(org_id=org_id, field_key=key).first():
                db.session.add(UserCustomField(org_id=org_id, field_key=key, display_name=name, is_required=req, is_system=sys, data_type=dtype))
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
        
    forbidden_keys = {'id', 'username', 'email', 'role', 'department', 'org_id', 'hashed_password', 'password', 'is_active', 'status', 'created_at', 'custom_fields'}
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
    base_headers = ['username', 'email', 'role', 'department', 'full_name', 'password']
    custom_headers = [f.field_key for f in custom_fields if f.field_key not in base_headers]
    headers = base_headers + custom_headers
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    
    sample_row = ['john_doe', 'john.doe@example.com', 'Team Member', 'Manufacturing', 'John Doe', 'Welcome@123']
    sample_row += [''] * len(custom_headers)
    writer.writerow(sample_row)
    
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=qcms_users_bulk_template.csv'
    return response

@admin_bp.route('/users/bulk-upload', methods=['POST'])
@admin_required
def bulk_upload_users():
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

    import csv
    import io
    
    try:
        stream = io.StringIO(file.stream.read().decode("utf-8"), newline=None)
        csv_reader = csv.DictReader(stream)
    except Exception as parse_err:
        return jsonify({"message": f"Failed to parse file: {str(parse_err)}"}), 400

    added_count = 0
    errors = []
    valid_roles = {r.name: r for r in Role.query.all()}
    custom_field_defs = UserCustomField.query.filter_by(org_id=org_id).all()
    
    row_num = 1
    for row in csv_reader:
        row_num += 1
        username = (row.get('username') or '').strip()
        email = (row.get('email') or '').strip()
        role_name = (row.get('role') or '').strip()
        dept_name = (row.get('department') or '').strip()
        full_name = (row.get('full_name') or '').strip() or username
        password = (row.get('password') or '').strip() or 'Welcome@123'

        if not username or not email or not role_name:
            errors.append({"row": row_num, "username": username, "email": email, "error": "Username, email, and role are required."})
            continue

        missing_required = []
        custom_values = {}
        type_validation_error = None
        for fd in custom_field_defs:
            if fd.field_key in ('username', 'role', 'department'):
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
            errors.append({"row": row_num, "username": username, "email": email, "error": f"Required fields missing: {', '.join(missing_required)}"})
            continue
            
        if type_validation_error:
            errors.append({"row": row_num, "username": username, "email": email, "error": type_validation_error})
            continue

        can_add, limit_msg = SubscriptionManager.check_user_limit(org_id)
        if not can_add:
            errors.append({"row": row_num, "username": username, "email": email, "error": f"Limit reached: {limit_msg}"})
            break

        if User.query.filter_by(email=email).first():
            errors.append({"row": row_num, "username": username, "email": email, "error": "Email already exists."})
            continue
            
        if User.query.filter_by(username=username).first():
            errors.append({"row": row_num, "username": username, "email": email, "error": "Username is already taken."})
            continue

        role = valid_roles.get(role_name)
        if not role:
            errors.append({"row": row_num, "username": username, "email": email, "error": f"Invalid role: '{role_name}'."})
            continue

        dept = None
        if dept_name and dept_name != 'N/A' and dept_name.lower() != 'all':
            dept = Department.query.filter_by(name=dept_name, org_id=org_id).first()
            if not dept:
                try:
                    dept = Department(name=dept_name, org_id=org_id)
                    db.session.add(dept)
                    db.session.flush()
                except Exception as dept_err:
                    errors.append({"row": row_num, "username": username, "email": email, "error": f"Failed to create department: {str(dept_err)}"})
                    continue

        try:
            new_user = User(
                username=username,
                full_name=full_name,
                email=email,
                hashed_password=bcrypt.generate_password_hash(password).decode('utf-8'),
                role_id=role.id,
                department_id=dept.id if dept else None,
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
                
            added_count += 1
            try:
                EmailUtils.send_temp_password_email(new_user, password)
            except Exception as mail_err:
                current_app.logger.error(f"Failed to send bulk welcome email to {email}: {str(mail_err)}")
                
            log_action(current_user.id, "CREATE_USER_BULK", current_user.org_id, "users", new_user.id, {"username": new_user.username})
        except Exception as create_err:
            db.session.rollback()
            errors.append({"row": row_num, "username": username, "email": email, "error": f"Database insertion failed: {str(create_err)}"})
            continue

    return jsonify({
        "message": "Bulk user upload completed.",
        "added_count": added_count,
        "errors": errors
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

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    current_user_id = int(get_jwt_identity())
    current_user = db.session.get(User, current_user_id)
    
    if user_id == current_user_id:
        return jsonify({"message": "You cannot delete your own account."}), 400
        
    user = User.query.join(Role).filter(
        User.id == user_id, 
        User.org_id == current_user.org_id,
        Role.name != 'SuperAdmin'
    ).first_or_404()
    
    # Dependency Checks
    # 1. Projects where user is Leader, Facilitator, or Creator
    active_roles = Project.query.filter(
        (Project.team_leader_id == user_id) | 
        (Project.facilitator_id == user_id) | 
        (Project.creator_id == user_id)
    ).first()
    
    if active_roles:
        return jsonify({
            "message": "User is assigned as a Leader, Facilitator, or Creator in active projects. Please reassign those roles or deactive the user instead.",
            "code": "DEPENDENCY_EXISTS"
        }), 400
        
    # 2. Project Memberships
    is_member = ProjectMember.query.filter_by(user_id=user_id).first()
    if is_member:
        return jsonify({
            "message": "User is a member of one or more projects. Please remove them from all projects before deleting.",
            "code": "DEPENDENCY_EXISTS"
        }), 400

    # 3. Project Reviews
    is_reviewer = ProjectReview.query.filter_by(reviewer_id=user_id).first()
    if is_reviewer:
        return jsonify({
            "message": "User has historical review records. Deletion would break audit trails. Please deactivate the user instead.",
            "code": "DEPENDENCY_EXISTS"
        }), 400

    try:
        # Before deleting, clear any relationships that might block deletion but aren't critical dependencies
        # (e.g. audit logs usually stay but if there's a hard FK without cascade, we might need a strategy)
        # Assuming cascade delete is NOT set for AuditLogs to preserve history, but they have user_id.
        # If AuditLog.user_id is NOT NULL, we might fail. 
        # Looking at AuditLog in models.py: user_id=db.ForeignKey('users.id'), nullable=False.
        # Since AuditLog must be preserved, we really SHOULD suggest deactivation.
        
        # However, many systems NULL out the user_id or use a "Deleted User" shell.
        # Given the instruction to prioritize data integrity, let's enforce deactivation for anyone with logs.
        has_logs = AuditLog.query.filter_by(user_id=user_id).first()
        if has_logs:
             return jsonify({
                "message": "User has historical activity logs. Deletion would break audit trails. Please deactivate the user instead.",
                "code": "DEPENDENCY_EXISTS"
            }), 400

        db.session.delete(user)
        db.session.commit()
        log_action(current_user_id, "DELETE_USER", current_user.org_id, "users", user_id, {"username": user.username})
        return jsonify({"message": "User deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to delete user", "error": str(e)}), 500


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
    
    return jsonify({
        "users": user_count,
        "total_members": user_count,
        "projects": project_count,
        "active_projects": active_projects,
        "completed_projects": completed_projects,
        "pending_validations": pending_validations,
        "stage_distribution": dict(stages)
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
    
    plant_id = data.get('plant_id')
    plant_id_val = int(plant_id) if plant_id and str(plant_id).isdigit() else None

    new_dept = Department(name=data['name'], plant_id=plant_id_val, org_id=current_user.org_id)
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
    
    if 'name' in data:
        dept.name = data['name']

    if 'plant_id' in data:
        pid = data['plant_id']
        dept.plant_id = int(pid) if pid and str(pid).isdigit() else None
        
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

@admin_bp.route('/departments/<int:dept_id>', methods=['DELETE'])
@admin_required
def delete_department(dept_id):
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    dept = Department.query.filter_by(id=dept_id, org_id=current_user.org_id).first_or_404()
    
    # Check for assigned users
    has_users = User.query.filter_by(department_id=dept_id).first()
    if has_users:
        return jsonify({"message": "Cannot delete department with assigned members. Reassign them first."}), 400
        
    db.session.delete(dept)
    db.session.commit()
    log_action(current_user.id, "DELETE_DEPARTMENT", current_user.org_id, "departments", dept_id)
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
        return jsonify({"message": "Organization not found"}), 404
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
        "api_key": org.api_key if org.api_access else None
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

@admin_bp.route('/upgrade-plan', methods=['POST'])
@admin_required
def upgrade_plan():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    org = db.session.get(Organization, current_user.org_id)
    
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
    
    stats = SubscriptionManager.get_usage_stats(current_user.org_id)
    if not stats:
        return jsonify({"message": "Stats not found"}), 404
        
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

