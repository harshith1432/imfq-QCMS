import os
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from .. import db, bcrypt
import sqlalchemy as sa
from ..models import (
    User, Role, Department, AuditLog, Project, ProjectWorkflow,
    ProjectStageTracker, Stage3RCA, Stage5Approval, Stage7Impact, Stage8Standardization,
    KnowledgeRepository, Organization
)
from ..utils.email_utils import EmailUtils
from datetime import datetime, timedelta
from functools import wraps

admin_bp = Blueprint('admin', __name__)

# Middleware for Admin-only access
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
        if not user or not user.role or user.role.name != 'Admin':
            return jsonify({"message": "Admin access required"}), 403
        return f(*args, **kwargs)
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

# --- User Management ---

@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    users = User.query.filter_by(org_id=current_user.org_id).all()
    return jsonify([{
        "id": u.id,
        "username": u.username,
        "full_name": u.full_name or u.username,
        "email": u.email,
        "role": u.role.name,
        "department": u.dept.name if u.dept else "N/A",
        "is_active": u.is_active,
        "profile_picture": f"/uploads/{u.profile_picture}" if u.profile_picture else None,
        "created_at": u.created_at.isoformat() + "Z" if u.created_at else None,
        "last_login": u.last_login.isoformat() + "Z" if u.last_login else None
    } for u in users]), 200

@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user_detail(user_id):
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "Admin user not found"}), 404
    user = User.query.filter_by(id=user_id, org_id=current_user.org_id).first_or_404()
    return jsonify({
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name or user.username,
        "email": user.email,
        "role": user.role.name,
        "department": user.dept.name if user.dept else "N/A",
        "is_active": user.is_active,
        "profile_picture": f"/uploads/{user.profile_picture}" if user.profile_picture else None
    }), 200

@admin_bp.route('/users', methods=['POST'])
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
    
    dept_name = data.get('dept_name') or data.get('department')
    dept = None
    
    # Safety for org_id
    org_id = current_user.org_id
    if not org_id:
        # Check if any organization exists, if not create one or default to 1
        first_org = Organization.query.first()
        org_id = first_org.id if first_org else 1

    if dept_name:
        dept = Department.query.filter_by(name=dept_name, org_id=org_id).first()
        if not dept:
            # Create department on the fly if it doesn't exist
            dept = Department(name=dept_name, org_id=org_id)
            db.session.add(dept)
            db.session.flush() # Get ID before user creation
    
    password = data.get('password', 'QCMS@Pass2026')
    
    try:
        new_user = User(
            username=username,
            full_name=data.get('full_name', username), # Save full name if provided
            email=email,
            hashed_password=bcrypt.generate_password_hash(password).decode('utf-8'),
            role_id=role.id,
            department_id=dept.id if dept else None,
            org_id=org_id,
            is_temp_password=True,
            status='Active'
        )
        db.session.add(new_user)
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

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    user = User.query.filter_by(id=user_id, org_id=current_user.org_id).first_or_404()
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
    
    if data.get('department'):
        dept_name = data.get('department')
        dept = Department.query.filter_by(name=dept_name, org_id=current_user.org_id).first()
        if not dept:
            # Create department on the fly to match create_user logic
            dept = Department(name=dept_name, org_id=current_user.org_id)
            db.session.add(dept)
            db.session.flush()
        user.department_id = dept.id
        
    if 'is_active' in data:
        user.is_active = data.get('is_active')
        if not user.is_active:
            user.deactivated_at = datetime.utcnow()

    if data.get('password'):
        user.hashed_password = bcrypt.generate_password_hash(data.get('password')).decode('utf-8')
        user.is_temp_password = True
        
    try:
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
        
    user = User.query.filter_by(id=user_id, org_id=current_user.org_id).first_or_404()
    
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

# --- Audit Logs ---

@admin_bp.route('/audit-logs', methods=['GET'])
@admin_required
def get_audit_logs():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    logs = AuditLog.query.filter_by(org_id=current_user.org_id).order_by(AuditLog.created_at.desc()).limit(100).all()
    results = []
    for l in logs:
        u = db.session.get(User, l.user_id) if l.user_id else None
        results.append({
            "id": l.id,
            "user": u.username if u else "System",
            "action": l.action,
            "target": f"{l.target_table} ({l.target_id})" if l.target_table else "Global",
            "details": l.details,
            "timestamp": l.created_at.isoformat() + "Z"
        })
    return jsonify(results), 200

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
    
    # Calculate pending validations (Impact approvals + Solution approvals)
    pending_impact = Stage7Impact.query.filter_by(org_id=org_id, status='Pending').count()
    pending_approval = Stage5Approval.query.filter_by(org_id=org_id, status='Pending').count()
    
    stages = db.session.query(ProjectStageTracker.stage_number, sa.func.count(ProjectStageTracker.id))\
        .filter(ProjectStageTracker.org_id == org_id, ProjectStageTracker.status == 'In Progress')\
        .group_by(ProjectStageTracker.stage_number).all()
    
    return jsonify({
        "users": user_count,
        "total_members": user_count,
        "projects": project_count,
        "active_projects": active_projects,
        "completed_projects": completed_projects,
        "pending_validations": pending_impact + pending_approval,
        "stage_distribution": dict(stages)
    }), 200


# --- Close Project (Module 3 + Module 6 trigger) ---

@admin_bp.route('/projects/<int:project_id>/close', methods=['POST'])
@admin_required
def close_project(project_id):
    """Admin closes a project at Stage 8 — triggers knowledge repository archive."""
    try:
        current_user_id = get_jwt_identity()
        current_user = db.session.get(User, current_user_id)
        if not current_user:
            return jsonify({"message": "User not found"}), 404
        project = Project.query.filter_by(id=project_id, org_id=current_user.org_id).first_or_404()
        
        if project.current_stage < 8:
            return jsonify({"message": f"Project is at Stage {project.current_stage}. Must be at Stage 8 to close."}), 400
        
        if project.status == 'Closed':
            return jsonify({"message": "Project is already closed"}), 400
        
        # Close the project
        project.status = 'Closed'
        project.end_date = datetime.utcnow().date()
        
        # Mark Stage 8 as completed
        tracker = ProjectStageTracker.query.filter_by(project_id=project_id, stage_number=8).first()
        if tracker:
            tracker.status = 'Completed'
            tracker.completed_at = datetime.utcnow()
        
        # Ensure changes are visible to subsequent queries in the same transaction
        db.session.flush()
        
        # Auto-archive into knowledge repository
        existing = KnowledgeRepository.query.filter_by(project_id=project_id, org_id=current_user.org_id).first()
        if not existing:
            # Gather data for archive
            stage1 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=1, org_id=current_user.org_id).first()
            rca = Stage3RCA.query.filter_by(project_id=project_id, org_id=current_user.org_id).first()
            stage4 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=4, org_id=current_user.org_id).first()
            impact = Stage7Impact.query.filter_by(project_id=project_id, org_id=current_user.org_id).first()
            std = Stage8Standardization.query.filter_by(project_id=project_id, org_id=current_user.org_id).first()
            
            entry = KnowledgeRepository(
                project_id=project_id,
                org_id=current_user.org_id,
                title=project.title,
                department_id=project.department_id,
                category=project.category,
                problem_summary=stage1.data.get('problem_statement', '') if stage1 and stage1.data else '',
                root_cause=rca.root_cause_summary if rca else '',
                solution_summary=stage4.data.get('proposed_solution', '') if stage4 and stage4.data else '',
                kpi_improvement_pct=impact.kpi_improvement_pct if impact else 0,
                cost_savings=impact.cost_savings if impact else 0,
                sop_path=std.sop_url if std else None,
                closure_report_path=std.closure_report_path if std else None,
                tags=[project.category] if project.category else [],
                keywords=f"{project.title} {project.category or ''}",
                archived_at=datetime.utcnow()
            )
            db.session.add(entry)
        
        log_action(
            user_id=current_user.id,
            action="PROJECT_CLOSED",
            target_table="projects",
            target_id=project_id,
            details={"title": project.title},
            org_id=current_user.org_id
        )
        
        db.session.commit()
        return jsonify({"message": "Project closed and archived successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in close_project: {str(e)}")
        return jsonify({
            "message": "Internal error during project closure",
            "error": str(e)
        }), 500

# --- All Projects (Admin view) ---

@admin_bp.route('/all-projects', methods=['GET'])
@admin_required
def get_all_projects():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    projects = Project.query.filter_by(org_id=current_user.org_id).all()
    results = []
    for p in projects:
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

# --- Role & Department Lists ---

@admin_bp.route('/roles', methods=['GET'])
@admin_required
def get_roles():
    roles = Role.query.all()
    return jsonify([r.name for r in roles]), 200

@admin_bp.route('/departments', methods=['GET'])
@admin_required
def get_departments():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    depts = Department.query.filter_by(org_id=current_user.org_id).all()
    return jsonify([{"id": d.id, "name": d.name} for d in depts]), 200

@admin_bp.route('/departments', methods=['POST'])
@admin_required
def create_department():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"message": "Department name required"}), 400
    
    new_dept = Department(name=data['name'], org_id=current_user.org_id)
    db.session.add(new_dept)
    db.session.commit()
    
    log_action(current_user.id, "CREATE_DEPARTMENT", current_user.org_id, "departments", new_dept.id, {"name": new_dept.name})
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
    return jsonify({"id": dept.id, "name": dept.name}), 200

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
        "industry": org.industry,
        "email": org.email,
        "phone": org.phone,
        "admin_name": org.admin_name
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
    data = request.get_json()
    
    if 'name' in data: org.name = data['name']
    if 'industry' in data: org.industry = data['industry']
    if 'email' in data: org.email = data['email']
    if 'phone' in data: org.phone = data['phone']
    if 'admin_name' in data: org.admin_name = data['admin_name']
    
    db.session.commit()
    log_action(current_user.id, "UPDATE_ORG_SETTINGS", current_user.org_id, "organizations", org.id, data)
    return jsonify({"message": "Organization settings updated"}), 200

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
