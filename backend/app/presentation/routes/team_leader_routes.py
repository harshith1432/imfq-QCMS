import os
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app.infrastructure.database.models.models import (
    User, Project, ProjectMember, ProjectWorkflow, ProjectStageTracker,
    Stage4Solution, Stage7Impact, AuditLog, Role, db, SOPTraining, SOP
)
from app import db as root_db
from functools import wraps
from datetime import datetime, timedelta
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
        if not user or not user.role or user.role.name not in ['Team Leader', 'Team Member', 'Admin']:
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
@team_leader_bp.route('/dashboard-stats', methods=['GET'])
@team_leader_or_admin_required
def get_stats():
    current_user = db.session.get(User, get_jwt_identity())
    dept_id = current_user.department_id if current_user else None
    
    if current_user.role.name == 'Admin':
        projects = Project.query.filter_by(org_id=current_user.org_id, department_id=dept_id).all()
    else:
        # Team Leaders see ONLY projects where they are acting as the Team Leader
        projects = Project.query.filter(
            Project.org_id == current_user.org_id,
            Project.team_leader_id == current_user.id
        ).all()
    
    completed_statuses = {'Closed', 'Completed', 'Stage 8 Approved', 'Archived'}
    inactive_statuses = {'Rejected', 'Cancelled', 'On Hold'}
    seven_days_ago = datetime.utcnow() - timedelta(days=7)

    completed_count = sum(
        1 for p in projects 
        if p.status in completed_statuses
    )

    inactive_count = 0
    for p in projects:
        if p.status in inactive_statuses:
            inactive_count += 1
        elif p.status not in completed_statuses:
            # Inactive if no AuditLog activity in 7 days
            last_log = AuditLog.query.filter_by(project_id=p.id).order_by(AuditLog.created_at.desc()).first()
            last_activity = last_log.created_at if last_log else p.created_at
            if last_activity and last_activity < seven_days_ago:
                inactive_count += 1

    active_count = sum(
        1 for p in projects 
        if p.status not in completed_statuses and p.status not in inactive_statuses
    ) - inactive_count
    active_count = max(0, active_count)
    
    # Queue count (stages needing TL validation)
    if current_user.role.name == 'Admin':
        pending_validations = Project.query.filter(
            Project.org_id == current_user.org_id,
            Project.department_id == dept_id, 
            Project.current_stage.in_([2, 5, 7])
        ).count()
    else:
        pending_validations = Project.query.filter(
            Project.org_id == current_user.org_id,
            Project.team_leader_id == current_user.id,
            Project.current_stage.in_([2, 5, 7])
        ).count()
    
    return jsonify({
        "total_projects": len(projects),
        "active_projects": active_count,
        "pending_validations": pending_validations,
        "queue_count": pending_validations,
        "completed_projects": completed_count,
        "stalled_projects": inactive_count,
        "inactive_projects": inactive_count
    })

# ============================
# DEPARTMENT MEMBERS (Module 2)
# ============================
@team_leader_bp.route('/members', methods=['GET'])
@team_leader_or_admin_required
def get_department_members():
    """Returns users assigned to projects led by this team leader (My Team Status)."""
    user = User.query.get(get_jwt_identity())

    page = request.args.get('page', type=int)
    per_page = request.args.get('per_page', default=10, type=int)

    # Find all project IDs where the logged-in user is the team leader
    led_project_ids = [
        p.id for p in Project.query.filter_by(
            org_id=user.org_id,
            team_leader_id=user.id
        ).with_entities(Project.id).all()
    ]

    if not led_project_ids:
        # Fallback: admin sees their department members
        if user.role and user.role.name == 'Admin':
            query = User.query.join(Role).filter(
                User.org_id == user.org_id,
                User.department_id == user.department_id,
                User.is_active == True,
                Role.name.in_(['Team Member', 'Team Leader']),
                User.id != user.id
            ).order_by(User.id.asc())
        else:
            # No projects led — return empty
            if page:
                return jsonify({"items": [], "total": 0, "page": page, "per_page": per_page, "total_pages": 0})
            return jsonify([])
    else:
        # Get distinct user IDs who are project_members on the led projects
        member_ids_subq = db.session.query(ProjectMember.user_id).filter(
            ProjectMember.project_id.in_(led_project_ids),
            ProjectMember.user_id != user.id
        ).distinct().subquery()

        query = User.query.join(Role).filter(
            User.id.in_(db.session.query(member_ids_subq.c.user_id)),
            User.is_active == True
        ).order_by(User.id.asc())

    if page:
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return jsonify({
            "items": [{
                "id": m.id,
                "username": m.full_name or m.username,
                "email": m.email,
                "role": m.role.name if m.role else 'Team Member'
            } for m in paginated.items],
            "total": paginated.total,
            "page": page,
            "per_page": per_page,
            "total_pages": paginated.pages
        })
    else:
        dept_members = query.all()
        return jsonify([{
            "id": m.id,
            "username": m.full_name or m.username,
            "email": m.email,
            "role": m.role.name if m.role else 'Team Member'
        } for m in dept_members])


# ============================
# PROJECT LISTING
# ============================
@team_leader_bp.route('/projects', methods=['GET'])
@team_leader_or_admin_required
def list_department_projects():
    user = db.session.get(User, get_jwt_identity())
    page = request.args.get('page', type=int)
    per_page = request.args.get('per_page', default=5, type=int)
    search = request.args.get('search', type=str)
    
    if user.role.name == 'Admin':
        query = Project.query.filter_by(org_id=user.org_id, department_id=user.department_id)
    else:
        query = Project.query.filter(
            Project.org_id == user.org_id,
            Project.team_leader_id == user.id
        )
        
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(db.or_(
            Project.title.ilike(search_term),
            Project.project_uid.ilike(search_term),
            Project.category.ilike(search_term)
        ))

    query = query.order_by(Project.id.desc())

    def serialize_project(p):
        return {
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
        }

    if page is not None:
        from app.shared.pagination import paginate_query
        return jsonify(paginate_query(query, page=page, per_page=per_page, serializer_fn=serialize_project)), 200

    projects = query.all()
    return jsonify([serialize_project(p) for p in projects]), 200

@team_leader_bp.route('/projects/<int:project_id>', methods=['GET'])
@team_leader_or_admin_required
def get_project_details(project_id):
    user = User.query.get(get_jwt_identity())
    project = Project.query.get_or_404(project_id)
    
    if project.org_id != user.org_id:
        return jsonify({"msg": "Unauthorized access"}), 403
        
    if user.role.name != 'Admin':
        is_member = ProjectMember.query.filter_by(project_id=project.id, user_id=user.id).first()
        if project.team_leader_id != user.id and project.creator_id != user.id and not is_member:
            return jsonify({"msg": "Unauthorized access to this project"}), 403
    
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
    if user.role.name == 'Admin':
        queue = Project.query.filter(
            Project.org_id == user.org_id,
            Project.department_id == user.department_id,
            Project.current_stage.in_([2, 7])
        ).all()
    else:
        queue = Project.query.filter(
            Project.org_id == user.org_id,
            Project.team_leader_id == user.id,
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

@team_leader_bp.route('/workload', methods=['GET'])
@team_leader_or_admin_required
def get_team_workload():
    import math
    user = User.query.get(get_jwt_identity())
    
    # Read pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 5, type=int)
    q = request.args.get('q', '', type=str).strip()
    target_member_id = request.args.get('member_id', type=int)

    # Base query for Team Members in the same org and department
    query = User.query.join(Role).filter(
        User.org_id == user.org_id,
        User.department_id == user.department_id,
        User.is_active == True,
        Role.name == 'Team Member'
    )

    if q:
        search_term = f"%{q}%"
        query = query.filter(db.or_(
            User.username.ilike(search_term),
            User.email.ilike(search_term),
            User.full_name.ilike(search_term)
        ))

    query = query.order_by(User.username.asc())
    total_count = query.count()

    # Calculate page number if specific member ID requested
    if target_member_id:
        all_ids = [m.id for m in query.all()]
        if target_member_id in all_ids:
            idx = all_ids.index(target_member_id)
            page = (idx // per_page) + 1

    # Fetch ONLY 5 (per_page) members for the current page from database
    if page and per_page:
        members = query.offset((page - 1) * per_page).limit(per_page).all()
    else:
        members = query.all()
    
    result = []
    completed_statuses = ['Closed', 'Completed', 'Stage 8 Approved']
    for m in members:
        # Active projects: projects where status is not completed/closed and stage < 8
        active_projects = Project.query.filter(
            Project.org_id == user.org_id,
            ~Project.status.in_(completed_statuses),
            Project.current_stage < 8,
            Project.members.any(id=m.id)
        ).all()
        
        # Completed projects count
        completed_projects_count = Project.query.filter(
            Project.org_id == user.org_id,
            db.or_(
                Project.status.in_(completed_statuses),
                Project.current_stage >= 8
            ),
            Project.members.any(id=m.id)
        ).count()
        
        # Pending trainings: SOPTraining where completion status is False
        pending_trainings = SOPTraining.query.filter_by(
            user_id=m.id,
            training_completion_status=False
        ).all()
        
        # Completed trainings count
        completed_trainings_count = SOPTraining.query.filter_by(
            user_id=m.id,
            training_completion_status=True
        ).count()
        
        # Format active projects list
        active_projects_list = [{
            "id": p.id,
            "project_uid": p.project_uid,
            "title": p.title,
            "status": p.status,
            "current_stage": p.current_stage
        } for p in active_projects]
        
        # Format pending trainings list
        pending_trainings_list = []
        for t in pending_trainings:
            sop = db.session.get(SOP, t.sop_id)
            if sop:
                pending_trainings_list.append({
                    "sop_id": sop.id,
                    "sop_uid": sop.sop_uid,
                    "title": sop.title,
                    "assigned_date": t.assigned_date.isoformat() + "Z" if t.assigned_date else None,
                    "due_date": t.due_date.isoformat() if t.due_date else None
                })
                
        result.append({
            "id": m.id,
            "username": m.username,
            "email": m.email,
            "active_projects": active_projects_list,
            "completed_projects_count": completed_projects_count,
            "pending_trainings": pending_trainings_list,
            "completed_trainings_count": completed_trainings_count
        })
        
    total_pages = math.ceil(total_count / per_page) if per_page and total_count > 0 else 1

    return jsonify({
        "members": result,
        "total": total_count,
        "page": page,
        "per_page": per_page,
        "pages": total_pages
    })
