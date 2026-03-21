import os
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from ..models import (
    User, Project, ProjectMember, ProjectWorkflow, ProjectStageTracker,
    Stage4Solution, Stage7Impact, AuditLog, db
)
from .. import db as root_db
from functools import wraps
from datetime import datetime
import uuid

team_leader_bp = Blueprint('team_leader', __name__)

# ============================
# DECORATORS
# ============================
def team_leader_or_admin_required(f):
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = db.session.get(User, current_user_id)
        if not user or not user.role or user.role.name not in ['Team Leader', 'Admin']:
            return jsonify({"msg": "Team Leader or Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function

def check_project_access(user_id, project_id):
    """Reusable: checks if user is creator or member of the project."""
    project = Project.query.get(project_id)
    if not project:
        return False
    if str(project.creator_id) == str(user_id):
        return True
    member = ProjectMember.query.filter_by(project_id=project_id, user_id=user_id).first()
    return member is not None

# ============================
# DASHBOARD STATS
# ============================
@team_leader_bp.route('/dashboard', methods=['GET'])
@team_leader_or_admin_required
def get_stats():
    current_user = db.session.get(User, get_jwt_identity())
    dept_id = current_user.department_id if current_user else None
    
    # Base query for projects in the TL's department
    projects = Project.query.filter_by(org_id=current_user.org_id, department_id=dept_id).all()
    
    # Calculate stats
    active_count = len([p for p in projects if p.status in ['In Progress', 'Pending Approval', 'Revision Required']])
    completed_count = len([p for p in projects if p.current_stage == 8 or p.status == 'Closed'])
    
    # Queue count (stages needing TL validation - e.g. Team Member submissions in Stage 2/7)
    pending_validations = Project.query.filter(
        Project.org_id == current_user.org_id,
        Project.department_id == dept_id, 
        Project.current_stage.in_([2, 5, 7]) # Including 5 as TL might want to track what's at review
    ).count()
    
    return jsonify({
        "total_projects": len(projects),
        "active_projects": active_count,
        "pending_validations": pending_validations,
        "completed_projects": completed_count
    })

# ============================
# DEPARTMENT MEMBERS (Module 2)
# ============================
@team_leader_bp.route('/members', methods=['GET'])
@team_leader_or_admin_required
def get_department_members():
    """Returns all users in the TL's department for member assignment."""
    user = User.query.get(get_jwt_identity())
    from app.models import Role
    dept_members = User.query.join(Role).filter(
        User.org_id == user.org_id,
        User.department_id == user.department_id,
        User.is_active == True,
        Role.name == 'Team Member'
    ).all()
    
    return jsonify([{
        "id": m.id,
        "username": m.username,
        "email": m.email,
        "role": m.role.name
    } for m in dept_members if m.id != user.id])  # Exclude TL from list

# ============================
# PROJECT LISTING
# ============================
@team_leader_bp.route('/projects', methods=['GET'])
@team_leader_or_admin_required
def list_department_projects():
    user = User.query.get(get_jwt_identity())
    projects = Project.query.filter_by(org_id=user.org_id, department_id=user.department_id).all()
    return jsonify([{
        "id": p.id,
        "project_uid": p.project_uid,
        "title": p.title,
        "description": p.description,
        "current_stage": p.current_stage,
        "status": p.status,
        "category": p.category,
        "deadline": p.deadline.isoformat() + "Z" if p.deadline else None,
        "members": [{"id": m.id, "name": m.username} for m in p.members],
        "member_ids": [m.id for m in p.members]
    } for p in projects])

@team_leader_bp.route('/projects/<int:project_id>', methods=['GET'])
@team_leader_or_admin_required
def get_project_details(project_id):
    user = User.query.get(get_jwt_identity())
    project = Project.query.get_or_404(project_id)
    
    if project.department_id != user.department_id:
        return jsonify({"msg": "Unauthorized department"}), 403
    
    proposal = Stage4Solution.query.filter_by(project_id=project.id).first()
    
    # Get stage data
    workflows = ProjectWorkflow.query.filter_by(project_id=project.id).all()
    stage_data = {}
    for wf in workflows:
        stage_data[wf.stage_id] = wf.data
    
    return jsonify({
        "id": project.id,
        "project_uid": project.project_uid,
        "title": project.title,
        "description": project.description,
        "current_stage": project.current_stage,
        "status": project.status,
        "category": project.category,
        "deadline": project.deadline.isoformat() + "Z" if project.deadline else None,
        "members": [{"id": m.id, "name": m.username} for m in project.members],
        "stage_data": stage_data,
        "proposal": {
            "budget": proposal.budget_required if proposal else 0,
            "roi": proposal.estimated_roi if proposal else 0,
            "resources": proposal.resource_plan if proposal else "",
            "kpis": proposal.kpi_targets if proposal else {}
        } if proposal else None
    })

# ============================
# PROJECT INITIALIZATION (Module 2 Enhanced)
# ============================
# Note: Project initialization is now handled via the unified /api/projects endpoint
# to ensure consistent role-based member assignment.

# ============================
# VALIDATION QUEUE
# ============================
@team_leader_bp.route('/queue', methods=['GET'])
@team_leader_or_admin_required
def get_queue():
    user = User.query.get(get_jwt_identity())
    queue = Project.query.filter(
        Project.org_id == user.org_id,
        Project.department_id == user.department_id,
        Project.current_stage.in_([2, 7])
    ).all()
    
    return jsonify([{
        "id": p.id,
        "project_id": p.id,
        "project_uid": p.project_uid,
        "title": p.title,
        "stage": p.current_stage,
        "type": "Data Validation" if p.current_stage == 2 else "Final Result Approval"
    } for p in queue])

# --- File Uploads ---

@team_leader_bp.route('/upload-evidence', methods=['POST'])
@team_leader_or_admin_required
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

# Note: Stage transitions and data management are now handled via workflow_routes.py
# utilizing the 8-stage STAGE_MODEL_MAP for strict data integrity.
