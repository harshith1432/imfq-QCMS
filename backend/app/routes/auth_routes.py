from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from ..models import User, Role, Department, Organization, EmailVerification, db
import random
from .. import bcrypt
from ..utils.email_utils import EmailUtils
from datetime import timedelta, datetime
import os
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register-org', methods=['POST'])
def register_org():
    data = request.get_json()
    
    # Validation
    email = data.get('email')
    username = data.get('username')
    
    if not email or not username or not data.get('password') or not data.get('company_name'):
        return jsonify({"msg": "Missing required fields"}), 400

    if Organization.query.filter_by(email=email).first():
        return jsonify({"msg": "Organization with this email already exists"}), 400
        
    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "Username already taken"}), 400

    # Check if verified in EmailVerification
    verification = EmailVerification.query.filter_by(email=email).first()
    if not verification or not verification.is_verified:
        return jsonify({"msg": "Email not verified. Please verify your email first."}), 400
    
    # 1. Create Organization
    new_org = Organization(
        name=data.get('company_name'),
        industry=data.get('industry'),
        admin_name=data.get('admin_name'),
        email=email,
        phone=data.get('phone')
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

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    identifier = data.get('username') or data.get('email')
    
    if not identifier:
        return jsonify({"msg": "Username or Email required"}), 400
        
    user = User.query.filter(
        (User.username.ilike(identifier)) | 
        (User.email.ilike(identifier))
    ).first()
    
    if user and bcrypt.check_password_hash(user.hashed_password, data['password']):
        # If it's a temporary password, allow login (they will be asked to change it)
        # OR if they are verified
        if not user.is_verified and not user.is_temp_password:
            return jsonify({"msg": "Please verify your email address before logging in"}), 403
            
        # Scoped access token
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                "org_id": user.org_id,
                "role": user.role.name,
                "dept_id": user.department_id
            },
            expires_delta=timedelta(days=1)
        )
        return jsonify({
            "access_token": access_token,
            "org_id": user.org_id,
            "org_name": user.organization.name,
            "role": user.role.name,
            "username": user.username,
            "is_temp_password": user.is_temp_password
        }), 200
        
    return jsonify({"msg": "Invalid credentials"}), 401

@auth_bp.route('/me', methods=['GET'])
@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
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
        "profile_picture": user.profile_picture,
        "banner_image": user.banner_image
    }), 200

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
    else:
        if 'full_name' in request.form:
            user.full_name = request.form['full_name']
            
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
        
    db.session.commit()
    return jsonify({
        "msg": "Profile updated successfully", 
        "full_name": user.full_name,
        "profile_picture": user.profile_picture,
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
        "profile_picture": user.profile_picture,
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
    return jsonify({"msg": "Successfully logged out"}), 200

@auth_bp.route('/reset-password', methods=['POST'])
@jwt_required()
def reset_password():
    user_id = int(get_jwt_identity())
    print(f"[AUTH] Resetting password for user_id: {user_id}")
    user = db.session.get(User, user_id)
    data = request.get_json()
    
    if not data or 'password' not in data:
        return jsonify({"msg": "Password required"}), 400
        
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
    roles = ['Admin', 'Reviewer', 'Facilitator', 'Team Leader', 'Team Member']
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
