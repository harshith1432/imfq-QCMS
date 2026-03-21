from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, Project, ProjectMember, ProjectWorkflow, db
from functools import wraps
from datetime import datetime

team_member_bp = Blueprint('team_member', __name__)

def team_member_required(f):
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.role.name != 'Team Member':
            return jsonify({"msg": "Team Member access required"}), 403
        return f(*args, **kwargs)
    return decorated_function

def verify_membership(project_id, user_id, org_id):
    """Ensure the user is assigned to the project and belongs to the right org."""
    project = Project.query.filter_by(id=project_id, org_id=org_id).first()
    if not project:
        return False
    is_member = ProjectMember.query.filter_by(project_id=project_id, user_id=user_id).first()
    return is_member is not None

@team_member_bp.route('/projects', methods=['GET'])
@team_member_required
def list_my_projects():
    user_id = get_jwt_identity()
    
    # Get all projects where the user is a member AND belongs to their org
    projects = Project.query.join(ProjectMember).filter(
        ProjectMember.user_id == user_id,
        Project.org_id == User.query.get(user_id).org_id
    ).all()
    
    return jsonify([{
        "id": p.id,
        "uid": p.project_uid,
        "project_uid": p.project_uid,
        "title": p.title,
        "category": p.category or 'General',
        "stage": p.current_stage,
        "status": p.status
    } for p in projects])

@team_member_bp.route('/projects/<int:project_id>', methods=['GET'])
@team_member_required
def get_project_workspace(project_id):
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not verify_membership(project_id, user_id, user.org_id):
        return jsonify({"msg": "Unauthorized: Not assigned to this project or wrong org"}), 403
        
    project = Project.query.filter_by(id=project_id, org_id=user.org_id).first_or_404()
    workflows = ProjectWorkflow.query.filter_by(project_id=project.id, org_id=user.org_id).all()
    
    # Build stage data map
    stage_data = {wf.stage_id: wf.data for wf in workflows}
    
    return jsonify({
        "id": project.id,
        "uid": project.project_uid,
        "title": project.title,
        "description": project.description,
        "current_stage": project.current_stage,
        "status": project.status,
        "stage_data": stage_data
    })

@team_member_bp.route('/stage/<int:stage_num>/update', methods=['POST'])
@team_member_required
def update_stage_data(stage_num):
    data = request.json
    project_id = data.get('project_id')
    user_id = get_jwt_identity()
    
    if not project_id:
        return jsonify({"msg": "Project ID required"}), 400
        
    user = User.query.get(user_id)
    if not verify_membership(project_id, user_id, user.org_id):
        return jsonify({"msg": "Unauthorized: Not assigned to this project or wrong org"}), 403
        
    project = Project.query.filter_by(id=project_id, org_id=user.org_id).first_or_404()
    
    # Conditional logic based on stage
    # Stage 5 is strictly Reviewer only. Members cannot update it.
    if stage_num == 5:
        return jsonify({"msg": "Stage 5 is read-only for Team Members"}), 403
        
    # Check if the project is actually at the target stage (or if they are just updating previous stage data)
    # Typically, you can only realistically update the current active stage or previous unlocked stages
    if project.status == 'Closed':
        return jsonify({"msg": "Project is closed"}), 403
        
    # Ensure a workflow record exists for the stage
    wf = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=stage_num, org_id=user.org_id).first()
    if not wf:
        wf = ProjectWorkflow(project_id=project_id, stage_id=stage_num, org_id=user.org_id, data={})
        db.session.add(wf)
        
    # Update JSON data for the stage
    # In a real app we would validate the JSON payload schema depending on the stage_num
    wf.data = data.get('stage_data', {})
    wf.updated_by = user_id
    wf.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({"msg": f"Stage {stage_num} updated successfully", "data": wf.data})
