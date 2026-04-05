from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Project, User, ProjectMember, KPIMetric, ProjectStageTracker, ProjectWorkflow, db
from ..middleware import role_required
from datetime import datetime
import uuid

project_bp = Blueprint('projects', __name__)

@project_bp.route('', methods=['GET'])
@jwt_required()
def get_projects():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    role = user.role.name
    org_id = user.org_id
    
    query = Project.query.filter_by(org_id=org_id)
    
    if role == 'Admin':
        pass # Full access within organization
    elif role == 'Facilitator':
        # Facilitators see projects they are assigned to
        query = query.filter(Project.facilitator_id == user.id)
    elif role == 'Reviewer':
        query = query.filter(Project.status.in_(['Pending Approval', 'Active']))
    elif role == 'Team Leader':
        # TL sees projects they are the assigned TL OR a member of
        query = query.join(ProjectMember).filter(
            db.or_(Project.team_leader_id == user.id, ProjectMember.user_id == user.id)
        ).distinct()
    elif role == 'Team Member':
        # Members see projects they are assigned to
        query = query.join(Project.members).filter(User.id == user.id)
    else:
        query = query.filter(False) # Deny all for unknown roles

    projects = query.order_by(Project.created_at.desc()).all()
    return jsonify([{
        "id": p.id,
        "project_uid": p.project_uid,
        "title": p.title,
        "category": p.category,
        "current_stage": p.current_stage,
        "status": p.status,
        "department": p.department.name if p.department else "N/A",
        "creator": p.creator.username if p.creator else "System"
    } for p in projects]), 200

@project_bp.route('/potential-members', methods=['GET'])
@jwt_required()
def get_potential_members():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    org_id = user.org_id
    role = user.role.name
    
    from ..models import Role
    
    target_role_name = request.args.get('role')
    dept_id = request.args.get('dept_id')
    
    # Base query: users in the same organization
    q = User.query.filter_by(org_id=org_id)
    
    # Filter by department if provided (Admin case) or if current user is TL
    if role == 'Admin' and dept_id:
        q = q.filter_by(department_id=dept_id)
    elif role == 'Team Leader':
        q = q.filter_by(department_id=user.department_id)
    
    # If a specific role is requested, filter by it
    if target_role_name:
        tr_role = Role.query.filter_by(name=target_role_name).first()
        if not tr_role:
            return jsonify({"msg": "Invalid target role"}), 400
        q = q.filter_by(role_id=tr_role.id)
    else:
        # Default behavior:
        # Admin gets all TLs and TMs if no role specified (Unified pool)
        # TL gets only TMs by default
        if role == 'Admin':
            tl_role = Role.query.filter_by(name='Team Leader').first()
            tm_role = Role.query.filter_by(name='Team Member').first()
            fa_role = Role.query.filter_by(name='Facilitator').first()
            rv_role = Role.query.filter_by(name='Reviewer').first()
            
            # Combine roles for unified selection pool (Admin can assign anyone)
            allowed_role_ids = [r.id for r in [tl_role, tm_role, fa_role, rv_role] if r]
            q = q.filter(User.role_id.in_(allowed_role_ids))
        elif role == 'Team Leader':
            tm_role = Role.query.filter_by(name='Team Member').first()
            q = q.filter_by(role_id=tm_role.id)
            
    users = q.all()
        
    return jsonify([{
        "id": u.id,
        "username": u.username,
        "full_name": u.full_name,
        "role": u.role.name if u.role else "N/A",
        "department": u.dept.name if u.dept else "N/A"
    } for u in users]), 200

@project_bp.route('', methods=['POST'])
@jwt_required()
@role_required(['Team Leader', 'Admin'])
def create_project():
    data = request.get_json()
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    role_name = user.role.name
    
    # Generate unique ID format PRJ-XXXX
    import random
    import string
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    project_uid = f"PRJ-{random_suffix}"
    
    # RBAC Logic for Team Leader Assignment
    if role_name == 'Admin':
        team_leader_id = data.get('team_leader_id')
        if not team_leader_id:
            return jsonify({"msg": "Team Leader assignment is mandatory for Admin-created projects"}), 400
        dept_id = data.get('department_id') or user.department_id
    else:
        # Team Leader creates and inherits ownership
        team_leader_id = user_id
        dept_id = user.department_id

    try:
        # Check if facilitator_id is provided and valid (not empty string)
        fid_val = data.get('facilitator_id')
        facilitator_id = int(fid_val) if fid_val is not None and str(fid_val).strip() != "" else None

        new_project = Project(
            project_uid=project_uid,
            title=data['title'],
            description=data.get('description'),
            category=data.get('category', 'Quality'),
            creator_id=user_id,
            team_leader_id=team_leader_id,
            facilitator_id=facilitator_id, # Safely parsed integer or None
            org_id=user.org_id,
            department_id=dept_id,
            deadline=datetime.strptime(data['deadline'], '%Y-%m-%d').date() if data.get('deadline') else None,
            current_stage=1,
            status='Draft'
        )
        
        db.session.add(new_project)
        db.session.flush()
        
        # 1. Assign Team Leader as a member
        db.session.add(ProjectMember(project_id=new_project.id, user_id=team_leader_id))
        
        # 2. Add other members if provided
        member_ids = data.get('member_ids', [])
        for mid in member_ids:
            if mid != team_leader_id:
                db.session.add(ProjectMember(project_id=new_project.id, user_id=mid))
        
        # 3. Initialize 8 stages in tracker
        for i in range(1, 9):
            tracker = ProjectStageTracker(
                project_id=new_project.id,
                org_id=user.org_id,
                stage_number=i,
                status='In Progress' if i == 1 else 'Not Started',
                started_at=datetime.utcnow() if i == 1 else None
            )
            db.session.add(tracker)
        
        # 4. Initialize Stage 1 Problem data
        from ..models import Stage1Identification
        stage1 = Stage1Identification(
            project_id=new_project.id,
            org_id=user.org_id,
            problem_statement=data.get('problem_statement', data['title']),
            description=data.get('description'),
            evidence=data.get('evidence'),
            location=data.get('location'),
            frequency_of_occurrence=data.get('frequency'),
            initial_impact=data.get('impact')
        )
        db.session.add(stage1)
        
        # 5. Initialize KPI Metrics
        db.session.add(KPIMetric(project_id=new_project.id, org_id=user.org_id))
        
        # 6. Log the creation in Audit Log
        from ..models import AuditLog
        from flask import request as flask_request
        audit = AuditLog(
            org_id=user.org_id,
            project_id=new_project.id,
            user_id=user_id,
            action=f"Created Project {project_uid}",
            details=f"Project '{new_project.title}' initialized as Draft.",
            ip_address=flask_request.remote_addr,
            user_agent=flask_request.user_agent.string,
            target_table="projects",
            target_id=new_project.id
        )
        db.session.add(audit)
        
        db.session.commit()
        
        return jsonify({
            "msg": "Project initialized successfully", 
            "project_uid": project_uid, 
            "id": new_project.id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Initialization failed", "error": str(e)}), 500

@project_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_project_details(id):
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    project = db.session.get(Project, id)
    if not project:
        return jsonify({"msg": "Project not found"}), 404
    
    if project.org_id != user.org_id:
        return jsonify({"msg": "Project not found"}), 404
        
    # Authorized for viewing if same organization, but we still track explicit roles for UI hinting
    is_org_member = (project.org_id == user.org_id)
    if not is_org_member:
        return jsonify({"msg": "Project not found"}), 404
    
    # We can still calculate 'authorized' for specific permissions later if needed, 
    # but for this GET route, being in the same org is enough to prevent a 404.

    # Fetch all stages for tracker
    stages = ProjectStageTracker.query.filter_by(project_id=id).order_by(ProjectStageTracker.stage_number).all()

    return jsonify({
        "id": project.id,
        "project_uid": project.project_uid,
        "title": project.title,
        "description": project.description,
        "category": project.category,
        "current_stage": project.current_stage,
        "status": project.status,
        "department": project.department.name if project.department else "N/A",
        "creator": project.creator.username if project.creator else "System",
        "creator_id": project.creator_id,
        "created_at": project.created_at.isoformat() + "Z",
        "facilitator_id": project.facilitator_id,
        "facilitator_name": project.facilitator.full_name if project.facilitator else (project.facilitator.username if project.facilitator else None),
        "team_leader_id": project.team_leader_id,
        "team_leader_name": project.team_leader.full_name if project.team_leader else (project.team_leader.username if project.team_leader else None),
        "department_id": project.department_id,
        "deadline": project.deadline.isoformat() if project.deadline else None,
        "member_ids": [m.user_id for m in ProjectMember.query.filter_by(project_id=id).all()],
        "stages": [{
            "stage_number": s.stage_number,
            "status": s.status,
            "started_at": s.started_at.isoformat() + "Z" if s.started_at else None,
            "completed_at": s.completed_at.isoformat() + "Z" if s.completed_at else None
        } for s in stages]
    }), 200

@project_bp.route('/<int:id>/stage/<int:stage_num>', methods=['GET'])
@jwt_required()
def get_project_stage_details(id, stage_num):
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    project = db.session.get(Project, id)
    
    if not project or project.org_id != user.org_id:
        return jsonify({"msg": "Project not found"}), 404
        
    from ..models import (
        Stage1Identification, Stage2Selection, Stage3Analysis, 
        Stage4Causes, Stage5RootCause, Stage6DataAnalysis, 
        Stage7Development, Stage8Implementation
    )
    
    stage_models = {
        1: Stage1Identification, 2: Stage2Selection, 3: Stage3Analysis,
        4: Stage4Causes, 5: Stage5RootCause, 6: Stage6DataAnalysis,
        7: Stage7Development, 8: Stage8Implementation
    }
    
    model = stage_models.get(stage_num)
    if not model:
        return jsonify({"msg": "Invalid stage number"}), 400
        
    stage_data = model.query.filter_by(project_id=id).first()
    
    # Standardize data to dict
    data = {}
    if stage_data:
        data = {c.name: getattr(stage_data, c.name) for c in stage_data.__table__.columns}
        # Clean up
        data.pop('id', None)
        data.pop('project_id', None)
        data.pop('org_id', None)
        # Convert datetimes to isoformat
        for k, v in data.items():
            if isinstance(v, datetime):
                data[k] = v.isoformat() + "Z"
    
    return jsonify(data), 200

@project_bp.route('/<int:id>/stage/<int:stage_num>', methods=['POST'])
@jwt_required()
def update_project_stage(id, stage_num):
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    project = db.session.get(Project, id)
    
    if not project or project.org_id != user.org_id:
        return jsonify({"msg": "Project not found"}), 404
        
    # RBAC: TL or assigned members
    is_member = ProjectMember.query.filter_by(project_id=id, user_id=user_id).first()
    if not is_member and user.role.name != 'Admin':
        return jsonify({"msg": "Unauthorized"}), 403

    from ..models import (
        Stage1Identification, Stage2Selection, Stage3Analysis, 
        Stage4Causes, Stage5RootCause, Stage6DataAnalysis, 
        Stage7Development, Stage8Implementation, ProjectStageTracker,
        AuditLog
    )
    
    stage_models = {
        1: Stage1Identification, 2: Stage2Selection, 3: Stage3Analysis,
        4: Stage4Causes, 5: Stage5RootCause, 6: Stage6DataAnalysis,
        7: Stage7Development, 8: Stage8Implementation
    }
    
    model = stage_models.get(stage_num)
    if not model:
        return jsonify({"msg": "Invalid stage number"}), 400
        
    data = request.get_json()
    stage_data = model.query.filter_by(project_id=id).first()
    
    if not stage_data:
        # Initialize if missing
        stage_data = model(project_id=id, org_id=user.org_id)
        db.session.add(stage_data)
    
    # Dynamically update fields
    for key, value in data.items():
        if hasattr(stage_data, key) and key not in ['id', 'project_id', 'org_id']:
            setattr(stage_data, key, value)
            
    # Update tracker if stage is being completed
    if data.get('action') == 'submit':
        tracker = ProjectStageTracker.query.filter_by(project_id=id, stage_number=stage_num).first()
        if tracker:
            tracker.status = 'Completed'
            tracker.completed_at = datetime.utcnow()
            
            # Note: Stage advancement is now handled via the /api/workflow/projects/<id>/transitions endpoint
            # to ensure all security gates (approvals/validations) are checked.
        
        # If it's the final stage, we still want to mark the project as completed
        if stage_num == 8:
            project.status = 'Completed'

    # Audit Log
    audit = AuditLog(
        org_id=user.org_id,
        project_id=id,
        user_id=user_id,
        action=f"Updated Stage {stage_num}",
        details=f"Stage {stage_num} updated. Action: {data.get('action', 'save')}",
        target_table=model.__tablename__,
        target_id=stage_data.id if stage_data.id else id
    )
    db.session.add(audit)
    
    db.session.commit()
    return jsonify({"msg": f"Stage {stage_num} updated successfully", "current_stage": project.current_stage}), 200

@project_bp.route('/<int:id>/activity', methods=['GET'])
@jwt_required()
def get_project_activity(id):
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    project = db.session.get(Project, id)
    if not project or project.org_id != user.org_id:
        return jsonify({"msg": "Project not found"}), 404
        
    # Check authorization
    role = user.role.name
    authorized = False
    if role == 'Admin':
        authorized = True
    elif role == 'Facilitator' or role == 'Reviewer':
        authorized = True
    elif role == 'Team Leader':
        authorized = (project.department_id == user.department_id)
    elif role == 'Team Member':
        is_member = ProjectMember.query.filter_by(project_id=id, user_id=user_id).first()
        authorized = (is_member is not None)
        
    if not authorized:
        return jsonify({"msg": "Project not found"}), 404
        
    from ..models import AuditLog
    logs = AuditLog.query.filter_by(project_id=id).order_by(AuditLog.created_at.desc()).all()
    
    return jsonify([{
        "id": log.id,
        "action": log.action,
        "details": log.details,
        "created_at": log.created_at.isoformat() + "Z"
    } for log in logs]), 200

@project_bp.route('/<int:id>', methods=['PATCH'])
@jwt_required()
def update_project(id):
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    project = db.session.get(Project, id)
    
    if not project or project.org_id != user.org_id:
        return jsonify({"msg": "Project not found"}), 404
        
    # RBAC: Only Admin or Project Creator or TL of same dept
    can_edit = (user.role.name == 'Admin' or 
                project.creator_id == user.id or 
                (user.role.name == 'Team Leader' and project.department_id == user.department_id))
    
    if not can_edit:
        return jsonify({"msg": "Permission denied"}), 403
        
    data = request.json
    if 'title' in data: project.title = data['title']
    if 'description' in data: project.description = data['description']
    if 'category' in data: project.category = data['category']
    if 'department_id' in data: project.department_id = data['department_id']
    if 'facilitator_id' in data:
        fid = data['facilitator_id']
        project.facilitator_id = int(fid) if fid is not None and str(fid).strip() != "" else None
    if 'team_leader_id' in data:
        project.team_leader_id = data['team_leader_id']

    if 'deadline' in data:
        try:
            if data['deadline']:
                project.deadline = datetime.strptime(data['deadline'], '%Y-%m-%d').date()
            else:
                project.deadline = None
        except (ValueError, TypeError):
            pass

    if 'member_ids' in data:
        member_ids = data['member_ids']
        # Clear existing members
        ProjectMember.query.filter_by(project_id=id).delete()
        # Ensure creator is always a member
        if project.creator_id not in member_ids:
            member_ids.append(project.creator_id)
        # Add new members
        for mid in member_ids:
            db.session.add(ProjectMember(project_id=id, user_id=mid))

    db.session.commit()
    return jsonify({"msg": "Project updated successfully"}), 200

@project_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
@role_required(['Admin', 'Team Leader'])
def delete_project(id):
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    project = db.session.get(Project, id)
    
    if not project or project.org_id != user.org_id:
        return jsonify({"msg": "Project not found"}), 404
        
    # RBAC: Both Admin and Team Leader (of the same department) should be able to delete
    can_delete = (user.role.name == 'Admin' or 
                  (user.role.name == 'Team Leader' and project.department_id == user.department_id) or
                  project.creator_id == user.id)
    
    if not can_delete:
        return jsonify({"msg": "Permission denied. Only Admins and Team Leaders (of the same department) can delete projects."}), 403
        
    try:
        # Delete related records that don't have automatic cascades
        ProjectMember.query.filter_by(project_id=id).delete()
        KPIMetric.query.filter_by(project_id=id).delete()
        
        # Import additional models for manual cleanup
        from ..models import (
            Stage1Identification, Stage2Selection, Stage3Analysis,
            Stage4Causes, Stage5RootCause, Stage6DataAnalysis, 
            Stage7Development, Stage8Implementation, KnowledgeRepository,
            ProjectStageTracker
        )
        
        # Manually clear workflow and tracker data
        ProjectStageTracker.query.filter_by(project_id=id).delete()
        
        Stage1Identification.query.filter_by(project_id=id).delete()
        Stage2Selection.query.filter_by(project_id=id).delete()
        Stage3Analysis.query.filter_by(project_id=id).delete()
        Stage4Causes.query.filter_by(project_id=id).delete()
        Stage5RootCause.query.filter_by(project_id=id).delete()
        Stage6DataAnalysis.query.filter_by(project_id=id).delete()
        Stage7Development.query.filter_by(project_id=id).delete()
        Stage8Implementation.query.filter_by(project_id=id).delete()
        KnowledgeRepository.query.filter_by(project_id=id).delete()
        
        # Finally delete the project itself
        db.session.delete(project)
        db.session.commit()
        
        return jsonify({"msg": "Project and all associated data deleted successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "msg": "Failed to delete project due to system error",
            "error": str(e)
        }), 500
