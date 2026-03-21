from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from ..models import User, Role, Department, Organization, db
from .. import bcrypt
from datetime import timedelta

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
        status='Active'
    )
    db.session.add(admin_user)
    db.session.commit()
    
    return jsonify({"msg": "Organization and Admin account created successfully"}), 201

@auth_bp.route('/register', methods=['POST'])
@jwt_required()
def register():
    # Only Admin can create users in their own org
    current_user_id = get_jwt_identity()
    admin = User.query.get(current_user_id)
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
        status='Active'
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({
        "msg": "User created successfully",
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
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
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
        "status": user.status
    }), 200

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    data = request.get_json()
    
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    if 'full_name' in data:
        user.full_name = data['full_name']
        
    db.session.commit()
    return jsonify({"msg": "Profile updated successfully", "full_name": user.full_name}), 200

@auth_bp.route('/change-password', methods=['PUT'])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    data = request.get_json()
    
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({"msg": "Current and new password required"}), 400
        
    if not bcrypt.check_password_hash(user.hashed_password, current_password):
        return jsonify({"msg": "Invalid current password"}), 401
        
    user.hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    user.is_temp_password = False
    db.session.commit()
    
    return jsonify({"msg": "Password updated successfully"}), 200

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    return jsonify({"msg": "Successfully logged out"}), 200

@auth_bp.route('/reset-password', methods=['POST'])
@jwt_required()
def reset_password():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    data = request.get_json()
    
    if not data or 'password' not in data:
        return jsonify({"msg": "Password required"}), 400
        
    user.hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    user.is_temp_password = False
    db.session.commit()
    
    return jsonify({"msg": "Password updated successfully"}), 200

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')
    user = User.query.filter_by(email=email).first()
    
    if user:
        # In a real app, send a reset email here
        # For this prototype, we return a success message
        return jsonify({"msg": "Reset link sent to your email"}), 200
    
    return jsonify({"msg": "Email not found"}), 404

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
