from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from app.infrastructure.database.models.models import User, Role, Department, Organization, EmailVerification, SupportTicket, Notification, db
import random
from app import bcrypt
from app.infrastructure.mailer.email_service import EmailUtils
from app.domain.services.subscription_service import SubscriptionManager
from datetime import timedelta, datetime
import os
import re
from werkzeug.utils import secure_filename
from app.utils.avatar_utils import get_profile_picture_url

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register-org', methods=['POST'])
def register_org():
    # Check PlatformSettings to see if native registration is disabled
    from app.infrastructure.database.models.models import PlatformSettings
    settings = PlatformSettings.query.first()
    auth_settings = (settings.authentication_settings or {}) if settings else {}
    if auth_settings.get('native_email_enabled') is False:
        return jsonify({"msg": "Direct registration is disabled. Please use Single Sign-On (SSO)."}), 403

    from app.shared.validation import (
        ValidationError,
        sanitize_payload,
        validate_email,
        validate_string_length,
        validate_password
    )
    
    data = sanitize_payload(request.get_json() or {})
    
    try:
        email = validate_email(data.get('email'), "Email address")
        username = validate_string_length(data.get('username'), "Username", min_len=3, max_len=50)
        password = validate_password(data.get('password'), "Password")
        company_name = validate_string_length(data.get('company_name'), "Company Name", min_len=2, max_len=100)
    except ValidationError as ve:
        return jsonify({"msg": ve.message}), 400

    if Organization.query.filter_by(email=email).first():
        return jsonify({"msg": "Organization with this email already exists"}), 400
        
    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "A user with this email already exists"}), 400
        
    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "Username already taken"}), 400

    # Check if verified in EmailVerification
    verification = EmailVerification.query.filter_by(email=email).first()
    if not verification or not verification.is_verified:
        return jsonify({"msg": "Email not verified. Please verify your email first."}), 400
    
    # 1. Create Organization
    plan_name = data.get('plan_name', 'Starter')
    plan_config = SubscriptionManager.get_plan_config(plan_name)
    
    trial_days = 14
    trial_ends = datetime.utcnow() + timedelta(days=trial_days)
    
    new_org = Organization(
        name=data.get('company_name'),
        industry=data.get('industry'),
        admin_name=data.get('admin_name'),
        email=email,
        phone=data.get('phone'),
        subscription_plan=plan_name,
        subscription_status='Trialing',
        trial_ends_at=trial_ends,
        max_users=plan_config['max_users'],
        is_white_label=plan_config['white_label'],
        multi_plant=plan_config['multi_plant'],
        api_access=plan_config['api_access']
    )
    db.session.add(new_org)
    db.session.flush() # Get ID

    # 2. Create Admin User
    admin_role = Role.query.filter_by(name='Admin').first()
    hashed_pw = bcrypt.generate_password_hash(data.get('password')).decode('utf-8')
    
    admin_user = User(
        org_id=new_org.id,
        username=username,
        email=email,
        hashed_password=hashed_pw,
        role_id=admin_role.id,
        status='Active',
        is_verified=True # Already verified via OTP
    )
    db.session.add(admin_user)
    
    # Clean up verification record
    db.session.delete(verification)
    
    db.session.commit()
    
    return jsonify({"msg": "Organization and Admin account created successfully."}), 201

@auth_bp.route('/request-registration-otp', methods=['POST'])
def request_registration_otp():
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({"msg": "Email is required"}), 400
        
    # Check if email is already taken
    if Organization.query.filter_by(email=email).first():
        return jsonify({"msg": "An organization with this email is already registered."}), 400
        
    # Generate 6-digit OTP
    otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    # Update or create verification record
    verification = EmailVerification.query.filter_by(email=email).first()
    if verification:
        verification.otp = otp
        verification.is_verified = False
        verification.expires_at = datetime.utcnow() + timedelta(minutes=10)
    else:
        verification = EmailVerification(
            email=email,
            otp=otp,
            expires_at = datetime.utcnow() + timedelta(minutes=10)
        )
        db.session.add(verification)
    
    # Send email via standardized utility
    EmailUtils.send_registration_otp(email, otp)
    
    db.session.commit()
    return jsonify({"msg": "Verification code sent to your email."}), 200

@auth_bp.route('/verify-registration-otp', methods=['POST'])
def verify_registration_otp():
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')
    
    if not email or not otp:
        return jsonify({"msg": "Email and OTP are required"}), 400
        
    verification = EmailVerification.query.filter_by(email=email, otp=otp).first()
    
    if not verification:
        return jsonify({"msg": "Invalid verification code."}), 400
        
    if verification.expires_at < datetime.utcnow():
        return jsonify({"msg": "Verification code has expired. Please request a new one."}), 400
        
    verification.is_verified = True
    db.session.commit()
    
    return jsonify({"msg": "Email verified successfully. You can now proceed."}), 200

@auth_bp.route('/register', methods=['POST'])
@jwt_required()
# DEPRECATED: Use /api/admin/users instead for audit logging and standardized creation.
def register():
    # Check PlatformSettings to see if native registration is disabled
    from app.infrastructure.database.models.models import PlatformSettings
    settings = PlatformSettings.query.first()
    auth_settings = (settings.authentication_settings or {}) if settings else {}
    if auth_settings.get('native_email_enabled') is False:
        return jsonify({"msg": "Direct registration is disabled. Please use Single Sign-On (SSO)."}), 403
    # Only Admin can create users in their own org
    identity = get_jwt_identity()
    try:
        current_user_id = int(identity)
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid user identity"}), 401
    admin = db.session.get(User, current_user_id)
    if admin.role.name != 'Admin':
        return jsonify({"msg": "Unauthorized"}), 403

    data = request.get_json()
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"msg": "Username already exists"}), 400
        
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"msg": "A user with this email already exists"}), 400
        
    role = Role.query.filter_by(name=data.get('role', 'Team Member')).first()
    if not role:
        return jsonify({"msg": "Invalid role"}), 400
        
    # Temporary password logic
    temp_password = data.get('password', 'QCMS@123') # Default temp pass if not provided
    hashed_pw = bcrypt.generate_password_hash(temp_password).decode('utf-8')
    
    dept_id = None
    if data.get('department'):
        dept = Department.query.filter_by(name=data['department'], org_id=admin.org_id).first()
        if not dept:
            # Create department if it doesn't exist for this org
            dept = Department(name=data['department'], org_id=admin.org_id)
            db.session.add(dept)
            db.session.flush()
        dept_id = dept.id
    
    new_user = User(
        org_id=admin.org_id,
        username=data['username'],
        email=data['email'],
        hashed_password=hashed_pw,
        role_id=role.id,
        department_id=dept_id,
        is_temp_password=True,
        is_verified=True,  # Users created by Admin are pre-verified
        status='Active'
    )
    
    db.session.add(new_user)
    
    # Send email with temporary password
    EmailUtils.send_temp_password_email(new_user, temp_password)
    
    db.session.commit()
    
    return jsonify({
        "msg": "User created successfully. Credentials sent to their email.",
        "temp_password": temp_password if not data.get('password') else "provided by admin"
    }), 201

@auth_bp.route('/login-config', methods=['GET'])
def get_login_config():
    """
    Public endpoint — no JWT required.
    Given ?identifier=xxx, finds the user's org and returns
    the allowed login options + human-readable field labels.
    Used by the login page to dynamically update its input label/placeholder.
    """
    from app.infrastructure.database.models.models import PlatformSettings
    settings = PlatformSettings.query.first()
    auth_settings = (settings.authentication_settings or {}) if settings else {}
    
    sso_config = {
        "google_enabled": auth_settings.get('oauth_google_enabled', False),
        "google_client_id": auth_settings.get('oauth_google_client_id', ''),
        "microsoft_enabled": auth_settings.get('oauth_microsoft_enabled', False) or auth_settings.get('azure_ad_enabled', False),
        "microsoft_client_id": auth_settings.get('oauth_microsoft_client_id', ''),
        "saml_enabled": auth_settings.get('saml_enabled', False),
        "saml_url": auth_settings.get('saml_metadata_url', ''),
        "native_enabled": auth_settings.get('native_email_enabled', True)
    }

    identifier = request.args.get('identifier', request.args.get('email', '')).strip().lower()
    if not identifier:
        # Fallback to general system settings: return union of all login options active in the system
        from app.infrastructure.database.models.models import Organization
        all_orgs = Organization.query.filter(Organization.login_options.isnot(None)).all()
        options = ["email"]
        for o in all_orgs:
            for opt in (o.login_options or []):
                if opt not in options:
                    options.append(opt)
        
        system_labels = {"email": "Email ID", "username": "Username"}
        field_labels = {}
        for key in options:
            if key in system_labels:
                field_labels[key] = system_labels[key]
            else:
                field_labels[key] = key.replace('_', ' ').title()
                
        return jsonify({
            "login_options": options,
            "field_labels": field_labels,
            "sso_config": sso_config
        }), 200

    from sqlalchemy import or_
    # Try finding user by email or username first
    user = User.query.filter(
        or_(
            User.email.ilike(identifier),
            User.username.ilike(identifier)
        )
    ).first()

    # If not found, search custom columns that are login options
    if not user:
        from app.infrastructure.database.models.models import Organization
        from sqlalchemy import text
        all_orgs_with_custom_login = Organization.query.filter(
            Organization.login_options.isnot(None)
        ).all()
        checked_keys = set()
        for org in all_orgs_with_custom_login:
            opts = org.login_options or []
            for key in opts:
                if key in ('email', 'username') or key in checked_keys:
                    continue
                checked_keys.add(key)
                try:
                    result = db.session.execute(
                        text(f"SELECT id FROM users WHERE LOWER({key}::text) = LOWER(:val) LIMIT 1"),
                        {"val": identifier}
                    ).fetchone()
                    if result:
                        user = db.session.get(User, result[0])
                        break
                except Exception:
                    continue
            if user:
                break

    if not user or not user.organization:
        return jsonify({
            "login_options": ["email"], 
            "field_labels": {"email": "Email ID"},
            "sso_config": sso_config
        }), 200

    org = user.organization
    options = org.login_options or ["email"]
    if "email" not in options:
        options = ["email"] + options

    # Build human-readable labels
    from app.infrastructure.database.models.models import UserCustomField
    custom_fields = UserCustomField.query.filter_by(org_id=org.id).all()
    cf_map = {cf.field_key: cf.display_name for cf in custom_fields}

    system_labels = {"email": "Email ID", "username": "Username"}
    field_labels = {}
    for key in options:
        if key in system_labels:
            field_labels[key] = system_labels[key]
        elif key in cf_map:
            field_labels[key] = cf_map[key]
        else:
            field_labels[key] = key.replace('_', ' ').title()

    return jsonify({
        "login_options": options,
        "field_labels": field_labels,
        "sso_config": sso_config
    }), 200


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    identifier = data.get('username') or data.get('email') or data.get('identifier')
    password = data.get('password', '')
    
    if not identifier:
        return jsonify({"msg": "Login identifier required"}), 400

    # Brute-force / lockout check (enforces security_settings.max_login_attempts)
    try:
        from app.presentation.middleware.security import is_login_locked
        client_ip = (request.headers.get('X-Forwarded-For', '') or '').split(',')[0].strip() or request.remote_addr or ''
        if is_login_locked(identifier) or (client_ip and is_login_locked(client_ip)):
            return jsonify({
                "msg": "Account is temporarily locked due to too many failed login attempts. Please try again later.",
                "error_code": "ACCOUNT_LOCKED"
            }), 429
    except Exception:
        pass  # Never block login on middleware errors

    # Build a flexible query: always check username and email first (system fields)
    from sqlalchemy import or_
    user = User.query.filter(
        or_(
            User.username.ilike(identifier),
            User.email.ilike(identifier)
        )
    ).first()

    # Check PlatformSettings to see if native login is disabled
    from app.infrastructure.database.models.models import PlatformSettings
    settings = PlatformSettings.query.first()
    auth_settings = (settings.authentication_settings or {}) if settings else {}
    if auth_settings.get('native_email_enabled') is False:
        # Check if the user is a SuperAdmin (must load user to check role)
        if user and user.role.name != 'SuperAdmin':
            return jsonify({"msg": "Native password login is disabled. Please use Single Sign-On (SSO)."}), 403
        elif not user:
            # If user not found, we still return 403 block if native login is disabled globally
            return jsonify({"msg": "Native password login is disabled. Please use Single Sign-On (SSO)."}), 403

    # If not found via system fields, check custom field columns that are enabled as login options
    if not user:
        from app.infrastructure.database.models.models import UserCustomField
        # We can't know the org without finding the user, so search across all custom field columns
        # by looking at ALL organizations' login_options (safe since identifier must be unique)
        from app.infrastructure.database.models.models import Organization
        from sqlalchemy import text
        # Get all unique custom field keys that are marked as login options anywhere
        all_orgs_with_custom_login = Organization.query.filter(
            Organization.login_options.isnot(None)
        ).all()
        checked_keys = set()
        for org in all_orgs_with_custom_login:
            options = org.login_options or []
            for key in options:
                if key in ('email', 'username') or key in checked_keys:
                    continue
                checked_keys.add(key)
                # Check if this column exists in users table and search it
                try:
                    result = db.session.execute(
                        text(f"SELECT id FROM users WHERE LOWER({key}::text) = LOWER(:val) LIMIT 1"),
                        {"val": identifier}
                    ).fetchone()
                    if result:
                        user = db.session.get(User, result[0])
                        break
                except Exception:
                    continue
            if user:
                break

    if not user:
        # Record failed attempt (wrong identifier)
        try:
            from app.presentation.middleware.security import record_failed_login
            client_ip = (request.headers.get('X-Forwarded-For', '') or '').split(',')[0].strip() or request.remote_addr or ''
            record_failed_login(identifier)
            if client_ip:
                record_failed_login(client_ip)
        except Exception:
            pass
        return jsonify({"msg": "Invalid credentials"}), 401

    if not bcrypt.check_password_hash(user.hashed_password, password):
        # Record failed attempt (wrong password)
        try:
            from app.presentation.middleware.security import record_failed_login
            client_ip = (request.headers.get('X-Forwarded-For', '') or '').split(',')[0].strip() or request.remote_addr or ''
            is_locked, attempts = record_failed_login(identifier)
            if client_ip:
                record_failed_login(client_ip)
            if is_locked:
                return jsonify({
                    "msg": "Account locked due to too many failed attempts. Try again later.",
                    "error_code": "ACCOUNT_LOCKED"
                }), 429
        except Exception:
            pass
        return jsonify({"msg": "Invalid credentials"}), 401

    # Check email verification (skip for temp passwords)
    if not user.is_verified and not user.is_temp_password:
        return jsonify({"msg": "Please verify your email address before logging in"}), 403

    # If organization is suspended, restrict login to Admin, CEO, or SuperAdmin only
    if user.organization and user.organization.subscription_status == 'Suspended':
        if user.role.name not in ('Admin', 'CEO', 'SuperAdmin'):
            return jsonify({"msg": "Your organization's account is suspended. Access denied. Please contact your administrator."}), 403
        
    # Clear lockout on successful authentication
    try:
        from app.presentation.middleware.security import clear_login_lockout
        client_ip = (request.headers.get('X-Forwarded-For', '') or '').split(',')[0].strip() or request.remote_addr or ''
        clear_login_lockout(identifier)
        if client_ip:
            clear_login_lockout(client_ip)
    except Exception:
        pass

    # Scoped access token
    # Include sa_sub_role in claims so the frontend can enforce sub-role
    # restrictions immediately without an extra API call.
    sa_sub_role = None
    if user.role and user.role.name == 'SuperAdmin':
        cf = user.custom_fields if isinstance(user.custom_fields, dict) else {}
        sa_sub_role = cf.get('super_admin_role', 'Owner')

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            "org_id": user.org_id,
            "role": user.role.name,
            "dept_id": user.department_id,
            "sa_sub_role": sa_sub_role,   # None for non-SuperAdmin users
        },
        expires_delta=timedelta(days=1)
    )
    
    # Update last login time
    from datetime import datetime
    user.last_login = datetime.utcnow()

    # Generate session ID
    session_id = f"SESS-{int(datetime.utcnow().timestamp())}-{user.id}"
    
    # Track session in db
    from app.infrastructure.database.models.models import SaaSUserSession
    from app.presentation.routes.audit_routes import parse_user_agent, get_geo_location, log_audit_event
    
    # Mark old sessions as LoggedOut for security
    SaaSUserSession.query.filter_by(user_id=user.id, status='Active').update({"status": "LoggedOut", "logout_time": datetime.utcnow()})
    
    ua_str = request.headers.get('User-Agent')
    ip_addr = request.remote_addr
    os_name, browser_name, device_name = parse_user_agent(ua_str)
    
    new_sess = SaaSUserSession(
        session_id=session_id,
        user_id=user.id,
        org_id=user.org_id,
        device=device_name,
        browser=browser_name,
        os=os_name,
        ip_address=ip_addr,
        location=get_geo_location(ip_addr),
        status='Active'
    )
    db.session.add(new_sess)
    db.session.commit()

    # Log enriched login audit event
    log_audit_event(
        org_id=user.org_id,
        user_id=user.id,
        action="USER_LOGIN",
        target_table="users",
        target_id=user.id,
        details={"username": user.username, "ip": ip_addr}
    )

    return jsonify({
        "access_token": access_token,
        "session_id": session_id,
        "org_id": user.org_id,
        "org_name": user.organization.name if user.organization else None,
        "role": user.role.name,
        "subscription_plan": user.organization.subscription_plan if user.organization else 'Starter',
        "subscription_status": user.organization.subscription_status if user.organization else 'Active',
        "username": user.username,
        "is_temp_password": user.is_temp_password,
        "language": user.language,
        "id": user.id,
        "org_primary_color": user.organization.primary_color if user.organization else None,
        "org_logo_url": user.organization.logo_url if user.organization else None,
        "org_favicon_url": user.organization.favicon_url if user.organization else None,
        "org_timezone": user.organization.timezone if user.organization else "Asia/Kolkata",
        "trial_ends_at": user.organization.trial_ends_at.isoformat() if user.organization and user.organization.trial_ends_at else None
    }), 200

@auth_bp.route('/me', methods=['GET'])
@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    try:
        from app.domain.services.document_branding_service import DocumentBrandingService
        branding_ctx = DocumentBrandingService.get_branding_context(user.org_id if user.role.name != 'SuperAdmin' else None)
    except Exception as e:
        branding_ctx = {}

    return jsonify({
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name or user.username,
        "email": user.email,
        "role_name": user.role.name,
        "department": user.dept.name if user.dept else None,
        "org_id": user.org_id,
        "org_name": user.organization.name,
        "status": user.status,
        "is_active": user.is_active,
        "deactivated_at": user.deactivated_at.isoformat() if getattr(user, 'deactivated_at', None) else None,
        "profile_picture": get_profile_picture_url(user),
        "banner_image": user.banner_image,
        "language": user.language,
        "org_primary_color": user.organization.primary_color if user.organization else None,
        "org_logo_url": (user.organization.logo_url if user.organization and user.organization.logo_url else branding_ctx.get("logo_url")),
        "platform_logo_url": branding_ctx.get("logo_url"),
        "platform_software_name": branding_ctx.get("software_name"),
        "platform_short_name": branding_ctx.get("software_short_name"),
        "platform_title": branding_ctx.get("platform_title"),
        "org_favicon_url": user.organization.favicon_url if user.organization else None,
        "org_timezone": user.organization.timezone if user.organization else "Asia/Kolkata",
        "subscription_status": user.organization.subscription_status if user.organization else 'Active',
        "subscription_plan": user.organization.subscription_plan if user.organization else 'Starter',
        "trial_ends_at": user.organization.trial_ends_at.isoformat() if user.organization and user.organization.trial_ends_at else None
    }), 200

@auth_bp.route('/user-reactivation-request', methods=['POST'])
@jwt_required()
def user_reactivation_request():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    data = request.get_json() or {}
    message_text = data.get('message', '').strip()
    if not message_text:
        return jsonify({"msg": "Request message is required"}), 400
        
    ticket_num = f"REACT-USER-{user.id}-{int(datetime.utcnow().timestamp())}"
    ticket = SupportTicket(
        org_id=user.org_id,
        user_id=user.id,
        subject=f"Account Reactivation Request: {user.full_name or user.username}",
        message=f"Deactivated User: {user.full_name or user.username} ({user.email})\nRole: {user.role.name}\nDepartment: {user.dept.name if user.dept else 'N/A'}\n\nRequest Message:\n{message_text}",
        category="User Access",
        status="Open",
        priority="High",
        ticket_number=ticket_num
    )
    db.session.add(ticket)
    
    admin_users = User.query.join(Role).filter(
        User.org_id == user.org_id,
        Role.name == 'Admin',
        User.is_active == True
    ).all()
    
    for admin in admin_users:
        notif = Notification(
            org_id=user.org_id,
            user_id=admin.id,
            title="Account Reactivation Request",
            message=f"{user.full_name or user.username} has requested account reactivation: '{message_text[:100]}...'",
            link="/admin/users.html"
        )
        db.session.add(notif)
        
    try:
        from app.presentation.routes.audit_routes import log_audit_event
        log_audit_event(
            org_id=user.org_id,
            user_id=user.id,
            action="USER_REACTIVATION_REQUEST_SUBMITTED",
            target_table="users",
            target_id=user.id,
            details={"username": user.username, "request_message": message_text}
        )
    except Exception as e:
        print("Failed to log audit event:", e)
        
    db.session.commit()
    
    return jsonify({
        "status": "success",
        "message": "Your reactivation request has been sent to your administrator successfully."
    }), 201

@auth_bp.route('/request-reactivation', methods=['POST'])
@jwt_required()
def request_reactivation():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    org = user.organization
    if not org or org.subscription_status != 'Suspended':
        return jsonify({"msg": "Organization is not suspended"}), 400
        
    data = request.get_json()
    message_text = data.get('message', '').strip()
    if not message_text:
        return jsonify({"msg": "Request message is required"}), 400
        
    # Create support ticket in DB
    ticket = SupportTicket(
        org_id=org.id,
        user_id=user.id,
        subject="Account Reactivation Request",
        message=f"Request by {user.role.name} ({user.username}):\n\n{message_text}",
        status="Open",
        priority="High"
    )
    db.session.add(ticket)

    # Notify all SuperAdmins
    try:
        sa_role = Role.query.filter_by(name='SuperAdmin').first()
        if sa_role:
            sa_users = User.query.filter_by(role_id=sa_role.id).all()
            for sa in sa_users:
                notif = Notification(
                    org_id=sa.org_id or org.id,
                    user_id=sa.id,
                    title=f"Organization Reactivation Request: {org.name}",
                    message=f"Organization '{org.name}' (Org ID: {org.id}) requested account reactivation. Message: '{message_text}'",
                    link="/admin/super-admin.html?view=support",
                    is_read=False
                )
                db.session.add(notif)
    except Exception as e:
        print("[QCMS] Warning: Failed to send SuperAdmin notification:", e)

    db.session.commit()
    
    return jsonify({"status": "success", "message": "Reactivation request submitted successfully."}), 201

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    if request.is_json:
        data = request.get_json()
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'language' in data:
            user.language = data['language']
    else:
        if 'full_name' in request.form:
            user.full_name = request.form['full_name']
        if 'language' in request.form:
            user.language = request.form['language']
            
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"avatar_{user.id}_{file.filename}")
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                user.profile_picture = f"/uploads/{filename}"
                
        if 'banner_image' in request.files:
            file = request.files['banner_image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"banner_{user.id}_{file.filename}")
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                user.banner_image = f"/uploads/{filename}"
        
    from app.utils.i18n_utils import _
    db.session.commit()
    return jsonify({
        "msg": _("auth.update_success", user_id=user.id), 
        "full_name": user.full_name,
        "profile_picture": get_profile_picture_url(user),
        "banner_image": user.banner_image
    }), 200

@auth_bp.route('/public-profile/<int:user_id>', methods=['GET'])
@jwt_required()
def get_public_profile(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    return jsonify({
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name or user.username,
        "role_name": user.role.name,
        "department": user.dept.name if user.dept else None,
        "profile_picture": get_profile_picture_url(user),
        "banner_image": user.banner_image
    }), 200

@auth_bp.route('/request-password-otp', methods=['POST'])
@jwt_required()
def request_password_otp():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    data = request.get_json()
    
    current_password = data.get('current_password')
    if not current_password:
        return jsonify({"msg": "Current password required"}), 400
        
    if not bcrypt.check_password_hash(user.hashed_password, current_password):
        return jsonify({"msg": "Invalid current password"}), 401
        
    # Generate 6-digit OTP
    import random
    otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    user.otp_token = otp
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()
    
    # Send OTP email
    EmailUtils.send_otp_email(user, otp)
    
    return jsonify({"msg": "OTP sent to your email"}), 200

@auth_bp.route('/change-password', methods=['PUT'])
@jwt_required()
def change_password():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    data = request.get_json()
    
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    otp = data.get('otp')
    
    if not current_password or not new_password or not otp:
        return jsonify({"msg": "Current password, new password, and OTP required"}), 400
        
    if not user.check_password(current_password):
        return jsonify({"msg": "Invalid current password"}), 401
        
    # Verify OTP
    if user.otp_token != otp:
        return jsonify({"msg": "Invalid OTP"}), 400
        
    if user.otp_expiry < datetime.utcnow():
        return jsonify({"msg": "OTP has expired"}), 400
        
    user.password = new_password
    user.is_temp_password = False
    user.is_verified = True
    
    # Clear OTP
    user.otp_token = None
    user.otp_expiry = None
    
    db.session.add(user)
    
    # Send notification email
    EmailUtils.send_password_change_notification(user)
    
    db.session.commit()
    
    return jsonify({"msg": "Password updated successfully"}), 200

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if user:
        from app.presentation.routes.audit_routes import log_audit_event
        from app.infrastructure.database.models.models import SaaSUserSession
        from datetime import datetime
        
        # Terminate active sessions in db
        active_sess = SaaSUserSession.query.filter_by(user_id=user.id, status='Active').all()
        for s in active_sess:
            s.status = 'LoggedOut'
            s.logout_time = datetime.utcnow()
            s.session_duration = int((s.logout_time - s.login_time).total_seconds())
        
        log_audit_event(
            org_id=user.org_id,
            user_id=user.id,
            action="USER_LOGOUT",
            target_table="users",
            target_id=user.id,
            details={"username": user.username, "ip": request.remote_addr}
        )
        db.session.commit()
    return jsonify({"msg": "Successfully logged out"}), 200

def validate_password_complexity(password):
    import re
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter (A-Z)."
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number (0-9)."
    if not re.search(r'[^A-Za-z0-9]', password):
        return False, "Password must contain at least one special character (!@#$...)."
    return True, None

@auth_bp.route('/reset-password', methods=['POST'])
@jwt_required()
def reset_password():
    user_id = int(get_jwt_identity())
    print(f"[AUTH] Resetting password for user_id: {user_id}")
    user = db.session.get(User, user_id)
    data = request.get_json()
    
    if not data or 'password' not in data:
        return jsonify({"msg": "Password required"}), 400
        
    is_valid, error_msg = validate_password_complexity(data['password'])
    if not is_valid:
        return jsonify({"msg": error_msg}), 400

    # Use direct hashed_password assignment to be absolutely sure
    user.hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    user.is_temp_password = False
    user.is_verified = True
    db.session.add(user)
    
    try:
        db.session.commit()
        print(f"[AUTH] Password successfully updated and saved for user_id: {user_id}")
    except Exception as e:
        db.session.rollback()
        print(f"[AUTH] Error saving password for user_id: {user_id}: {e}")
        return jsonify({"msg": "Internal database error while saving password"}), 500
    
    return jsonify({"msg": "Password updated successfully"}), 200

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')
    user = User.query.filter_by(email=email).first()
    
    if user:
        EmailUtils.send_reset_password_email(user)
        db.session.commit()
        return jsonify({"msg": "Password reset link sent to your email"}), 200
    
    return jsonify({"msg": "If that email exists in our system, a reset link has been sent."}), 200

@auth_bp.route('/seed-roles', methods=['POST'])
def seed_roles():
    # Updating roles to match enterprise requirements:
    # Admin, Project Manager, Lead Auditor, Quality Head, Team Member
    roles = ['Admin', 'Reviewer', 'Facilitator', 'Team Leader', 'Team Member', 'CEO']
    for r_name in roles:
        if not Role.query.filter_by(name=r_name).first():
            db.session.add(Role(name=r_name))
    db.session.commit()
    return jsonify({"msg": "Enterprise roles seeded"}), 200

@auth_bp.route('/verify-email/<token>', methods=['GET'])
def verify_email(token):
    user = User.query.filter_by(verification_token=token).first()
    
    if not user:
        return jsonify({"msg": "Invalid or expired verification token"}), 400
        
    if user.token_expiry < datetime.utcnow():
        return jsonify({"msg": "Verification token has expired"}), 400
        
    user.is_verified = True
    user.verification_token = None
    user.token_expiry = None
    db.session.commit()
    
    return """
    <html>
        <body style="font-family: Arial; text-align: center; padding-top: 50px;">
            <h1 style="color: #2563eb;">Verification Successful!</h1>
            <p>Your email has been verified. You can now log in to the application.</p>
            <a href="http://localhost:3000/login" style="color: #2563eb;">Go to Login</a>
        </body>
    </html>
    """, 200

@auth_bp.route('/reset-password-confirm', methods=['POST'])
def reset_password_confirm():
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('new_password')
    
    if not token or not new_password:
        return jsonify({"msg": "Token and new password required"}), 400
        
    user = User.query.filter_by(reset_token=token).first()
    
    if not user:
        return jsonify({"msg": "Invalid or expired reset token"}), 400
        
    if user.token_expiry < datetime.utcnow():
        return jsonify({"msg": "Reset link has expired"}), 400
        
    user.hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    user.reset_token = None
    user.token_expiry = None
    user.is_temp_password = False
    user.is_verified = True
    db.session.add(user)
    db.session.commit()
    
    return jsonify({"msg": "Password reset successfully. You can now log in with your new password."}), 200

@auth_bp.route('/avatar/<username>', methods=['GET'])
def get_avatar_svg(username):
    initials = "".join([part[0] for part in username.split() if part])[:2].upper()
    if not initials:
        initials = "U"
    
    colors = [
        "#f87171", "#fb923c", "#fbbf24", "#34d399", 
        "#2dd4bf", "#38bdf8", "#60a5fa", "#818cf8", 
        "#a78bfa", "#f472b6", "#fb7185"
    ]
    color_index = sum(ord(c) for c in username) % len(colors)
    bg_color = colors[color_index]
    
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
        <rect width="100%" height="100%" fill="{bg_color}" />
        <text x="50%" y="55%" font-family="Arial, Helvetica, sans-serif" font-size="40" font-weight="bold" fill="#ffffff" dominant-baseline="middle" text-anchor="middle">{initials}</text>
    </svg>"""
    from flask import Response
    return Response(svg, mimetype='image/svg+xml')

@auth_bp.route('/support/tickets', methods=['GET', 'POST'])
@jwt_required()
def handle_support_tickets():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    if request.method == 'GET':
        tickets = SupportTicket.query.filter_by(user_id=user_id).order_by(SupportTicket.created_at.desc()).all()
        output = []
        for t in tickets:
            output.append({
                "id": t.id,
                "subject": t.subject,
                "message": t.message,
                "priority": t.priority,
                "status": t.status,
                "category": t.category,
                "created_at": t.created_at.isoformat(),
                "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
                "resolution": t.resolution
            })
        return jsonify({"status": "success", "data": output})

    elif request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({"msg": "Request body must be JSON"}), 400
            
        subject = data.get('subject', '').strip()
        message = data.get('message', '').strip()
        priority = data.get('priority', 'Medium').strip()
        category = data.get('category', 'Technical').strip()
        
        if not subject or not message:
            return jsonify({"msg": "Subject and message are required"}), 400
            
        ticket = SupportTicket(
            org_id=user.org_id,
            user_id=user.id,
            subject=subject,
            message=message,
            priority=priority,
            category=category,
            status="Open"
        )
        db.session.add(ticket)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Ticket created successfully",
            "ticket_id": ticket.id
        }), 201


@auth_bp.route('/sso/<provider>', methods=['POST'])
def sso_login(provider):
    data = request.get_json() or {}
    email = data.get('email')
    token = data.get('token')
    
    if not email:
        return jsonify({"msg": "Email is required for SSO"}), 400
        
    from app.infrastructure.database.models.models import PlatformSettings
    settings = PlatformSettings.query.first()
    auth_settings = (settings.authentication_settings or {}) if settings else {}
    
    # Verify provider configuration
    if provider == 'google':
        if not auth_settings.get('oauth_google_enabled'):
            return jsonify({"msg": "Google OAuth is disabled"}), 403
        client_id = auth_settings.get('oauth_google_client_id')
        if not client_id:
            return jsonify({"msg": "Google OAuth is not configured properly"}), 400
    elif provider == 'microsoft':
        if not auth_settings.get('oauth_microsoft_enabled') and not auth_settings.get('azure_ad_enabled'):
            return jsonify({"msg": "Azure AD / Microsoft login is disabled"}), 403
        client_id = auth_settings.get('oauth_microsoft_client_id')
        if not client_id:
            return jsonify({"msg": "Microsoft login is not configured properly"}), 400
    elif provider == 'saml':
        if not auth_settings.get('saml_enabled'):
            return jsonify({"msg": "SAML SSO is disabled"}), 403
        metadata_url = auth_settings.get('saml_metadata_url')
        if not metadata_url:
            return jsonify({"msg": "SAML SSO is not configured properly"}), 400
    else:
        return jsonify({"msg": "Invalid SSO provider"}), 400
        
    # Authenticate the user by email
    user = User.query.filter(User.email.ilike(email)).first()
    if not user:
        if settings.registration_open:
            # Find or create a default organization for SSO users
            from app.infrastructure.database.models.models import Organization, Role
            org = Organization.query.first()
            if not org:
                org = Organization(name="Default Organization", email=email, subscription_plan="Starter")
                db.session.add(org)
                db.session.flush()
                
            role = Role.query.filter_by(name='Team Member').first()
            
            # Generate a random username from email
            username = email.split('@')[0]
            base_username = username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
                
            user = User(
                org_id=org.id,
                username=username,
                email=email,
                hashed_password=bcrypt.generate_password_hash("SSO_TEMP_PASSWORD").decode('utf-8'),
                role_id=role.id,
                is_verified=True,
                status='Active'
            )
            db.session.add(user)
            db.session.flush()
        else:
            return jsonify({"msg": "SSO user not registered on this platform. Please contact your admin."}), 404
            
    # Generate token
    from datetime import datetime, timedelta
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            "org_id": user.org_id,
            "role": user.role.name,
            "dept_id": user.department_id
        },
        expires_delta=timedelta(hours=int(auth_settings.get('jwt_expiry_hours', 24)))
    )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        "access_token": access_token,
        "org_id": user.org_id,
        "org_name": user.organization.name if user.organization else None,
        "role": user.role.name,
        "username": user.username,
        "id": user.id,
        "org_primary_color": user.organization.primary_color if user.organization else None,
        "org_logo_url": user.organization.logo_url if user.organization else None
    }), 200


@auth_bp.route('/maintenance-status', methods=['GET'])
def maintenance_status():
    from app.infrastructure.database.models.models import PlatformSettings
    from sqlalchemy import text
    # Use raw SQL to bypass the SQLAlchemy identity map / session cache entirely
    row = db.session.execute(
        text("SELECT maintenance_mode, maintenance_settings FROM platform_settings LIMIT 1")
    ).fetchone()
    if not row:
        return jsonify({"maintenance_mode": False}), 200

    maint_mode = bool(row[0]) if row[0] is not None else False
    import json as _json
    try:
        maint_settings = _json.loads(row[1]) if isinstance(row[1], str) else (row[1] or {})
    except Exception:
        maint_settings = {}
    return jsonify({
        "maintenance_mode": maint_mode,
        "message": maint_settings.get("maintenance_message") or "The system is currently undergoing scheduled maintenance. Please try again later.",
        "eta": maint_settings.get("estimated_completion") or ""
    }), 200


