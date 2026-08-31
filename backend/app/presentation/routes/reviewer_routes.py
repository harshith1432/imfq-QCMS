from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.infrastructure.database.models.models import (
    User, Role, Project, ProjectReview, Department, ProjectStageTracker, ProjectWorkflow,
    Stage1ProblemDefinitionProjectInitiation, Stage2ObservationDataCollection, Stage3CauseIdentification,
    Stage4RootCauseAnalysisVerification, Stage5CountermeasurePlanningSolutionDevelopment, 
    Stage6ImplementationChangeManagement, Stage7PerformanceVerificationBenefitsRealization,
    Stage8Standardization, SOP, SOPTraining, SOPComment, SOPApproval, AuditLog, FacilitatorNote
)
from sqlalchemy.orm.attributes import flag_modified
from app import db
from functools import wraps
from datetime import datetime, timezone
from app.utils.avatar_utils import get_profile_picture_url
from app.presentation.routes.error_helpers import internal_server_error

STAGE_MODEL_MAP_REV = {
    2: Stage2ObservationDataCollection,
    3: Stage3CauseIdentification,
    4: Stage4RootCauseAnalysisVerification,
    5: Stage5CountermeasurePlanningSolutionDevelopment,
    6: Stage6ImplementationChangeManagement,
    7: Stage7PerformanceVerificationBenefitsRealization,
    8: Stage8Standardization
}

def _get_pending_projects(org_id, reviewer_id, user_dept_id=None, is_admin=False):
    """Return projects awaiting review that are assigned to this specific reviewer or admin.
    All 8 stages require Reviewer approval.
    
    A project appears in the reviewer's queue if its current stage tracker status is
    'Submitted For Review'. Any Reviewer in the org can see and action any submission
    (projects are not restricted to a single reviewer's queue).
    """
    if is_admin:
        pending_list = []
        
        # 1. Stage 8 closures
        query = Project.query.filter(
            Project.org_id == org_id,
            Project.current_stage == 8,
            Project.status.in_(['Pending Closure', 'SOP Created'])
        )
        if user_dept_id:
            query = query.filter(Project.department_id == user_dept_id)
        active_projects = query.all()
        for p in active_projects:
            workflow = ProjectWorkflow.query.filter_by(project_id=p.id, stage_id=8).first()
            pending_list.append((p, 8, workflow))
            
        # 2. Stage 2-7 submissions (Admin does not review Stage 1)
        sub_query = Project.query.filter(
            Project.org_id == org_id,
            Project.current_stage > 1,
            Project.current_stage < 8,
            Project.status != 'Closed'
        )
        if user_dept_id:
            sub_query = sub_query.filter(Project.department_id == user_dept_id)
        sub_projects = sub_query.all()
        for p in sub_projects:
            tracker = ProjectStageTracker.query.filter_by(project_id=p.id, stage_number=p.current_stage).first()
            if tracker and tracker.status == 'Submitted For Review':
                workflow = ProjectWorkflow.query.filter_by(project_id=p.id, stage_id=p.current_stage).first()
                pending_list.append((p, p.current_stage, workflow))
                
        return pending_list

    # Reviewer pending queue: any stage 1-8 in this org where tracker is 'Submitted For Review'.
    # All reviewers in the org can see pending submissions in their department, unassigned departments, or projects assigned to them.
    from sqlalchemy import or_
    query = Project.query.filter(
        Project.org_id == org_id,
        Project.status != 'Closed'
    )
    if user_dept_id:
        query = query.filter(or_(
            Project.department_id == user_dept_id,
            Project.reviewer_id == reviewer_id,
            Project.department_id.is_(None)
        ))
        
    active_projects = query.all()
    pending_list = []
    for p in active_projects:
        tracker = ProjectStageTracker.query.filter_by(project_id=p.id, stage_number=p.current_stage).first()
        if tracker and tracker.status == 'Submitted For Review':
            workflow = ProjectWorkflow.query.filter_by(project_id=p.id, stage_id=p.current_stage).first()
            pending_list.append((p, p.current_stage, workflow))
            
    return pending_list

reviewer_bp = Blueprint('reviewer', __name__)

def reviewer_required(f):
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = db.session.get(User, current_user_id)
        if not user or user.role.name not in ('Reviewer', 'Admin'):
            return jsonify({"msg": "Reviewer/Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function

# --- Dashboard Stats ---
@reviewer_bp.route('/stats', methods=['GET'])
@reviewer_required
def get_stats():
    user = db.session.get(User, get_jwt_identity())
    
    # Apply dept filter if user has a specific dept
    user_dept_id = None
    if user.dept and user.dept.name not in ['All', 'N/A']:
        user_dept_id = user.department_id
        
    is_admin = (user.role.name == 'Admin')
    
    if is_admin:
        pending_count = len(_get_pending_projects(user.org_id, user.id, user_dept_id, is_admin=True))
    else:
        pending_count = len(_get_pending_projects(user.org_id, user.id, user_dept_id, is_admin=False))
        
    # Stage 8 impact projects (pending impact review)
    approved_impact_ids = [s.project_id for s in Stage8Standardization.query.filter_by(status='Approved').all()]

    impact_query = Project.query.filter(
        Project.org_id == user.org_id,
        Project.current_stage == 8,
        ~Project.status.in_(['Closed', 'Pending CEO Review', 'Pending CEO Closure', 'Impact Approved']),
        Project.status.in_(['Stage 8 Submitted', 'Stage 8 Reviewer Approved', 'Stage 8 Approved'])
    )
    if approved_impact_ids:
        impact_query = impact_query.filter(~Project.id.in_(approved_impact_ids))

    if not is_admin:
        from sqlalchemy import or_
        if user_dept_id:
            impact_query = impact_query.filter(or_(Project.department_id == user_dept_id, Project.reviewer_id == user.id, Project.department_id.is_(None)))
        else:
            impact_query = impact_query.filter(or_(Project.reviewer_id == user.id, Project.department_id.is_(None)))
    pending_impact = impact_query.count()

    # Stage 8 closure projects (SOP created, ready for closure)
    closure_query = Project.query.filter(
        Project.org_id == user.org_id,
        Project.current_stage == 8,
        Project.status != 'Closed',
        Project.status.in_(['Impact Approved', 'SOP Created', 'Pending Closure'])
    )
    if not is_admin:
        from sqlalchemy import or_
        if user_dept_id:
            closure_query = closure_query.filter(or_(Project.department_id == user_dept_id, Project.reviewer_id == user.id, Project.department_id.is_(None)))
        else:
            closure_query = closure_query.filter(or_(Project.reviewer_id == user.id, Project.department_id.is_(None)))
    pending_closure = closure_query.count()

    # Average improvement
    try:
        impacts_query = Stage8Standardization.query.join(Project).filter(
            Project.org_id == user.org_id,
            Stage8Standardization.kpi_improvement_pct.isnot(None),
            Stage8Standardization.kpi_improvement_pct > 0
        )
        if not is_admin:
            from sqlalchemy import or_
            if user_dept_id:
                impacts_query = impacts_query.filter(or_(Project.department_id == user_dept_id, Project.reviewer_id == user.id, Project.department_id.is_(None)))
            else:
                impacts_query = impacts_query.filter(or_(Project.reviewer_id == user.id, Project.department_id.is_(None)))
        impacts = impacts_query.all()
        avg_improvement = 0
        if impacts:
            avg_improvement = round(sum([i.kpi_improvement_pct or 0 for i in impacts]) / len(impacts), 1)
    except Exception:
        avg_improvement = 0

    # Approved count for this reviewer
    try:
        if is_admin:
            approved_count = ProjectReview.query.filter_by(org_id=user.org_id, decision='Approved').count()
            rejected_count = ProjectReview.query.filter_by(org_id=user.org_id, decision='Rejected').count()
        else:
            approved_count = ProjectReview.query.filter(
                ProjectReview.org_id == user.org_id,
                ProjectReview.decision == 'Approved'
            ).count()
            rejected_count = ProjectReview.query.filter(
                ProjectReview.org_id == user.org_id,
                ProjectReview.decision == 'Rejected'
            ).count()
    except Exception:
        approved_count = 0
        rejected_count = 0

    return jsonify({
        "pending_count": pending_count,
        "pending_impact": pending_impact,
        "pending_closure": pending_closure,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "avg_improvement": f"{avg_improvement}%"
    })

@reviewer_bp.route('/approved-projects', methods=['GET'])
@reviewer_required
def get_approved_projects():
    user = db.session.get(User, get_jwt_identity())
    is_admin = (user.role and user.role.name == 'Admin')
    
    # Fetch all discrete stage approval reviews made by this reviewer (or across org if Admin)
    if is_admin:
        approved_reviews = ProjectReview.query.filter_by(
            org_id=user.org_id,
            decision='Approved'
        ).order_by(ProjectReview.decided_at.desc()).all()
    else:
        approved_reviews = ProjectReview.query.filter_by(
            org_id=user.org_id,
            reviewer_id=user.id, 
            decision='Approved'
        ).order_by(ProjectReview.decided_at.desc()).all()
    
    result = []
    reviewed_keys = set()
    
    for r in approved_reviews:
        p = Project.query.filter_by(id=r.project_id, org_id=user.org_id).first()
        if not p:
            continue
            
        stage_num = r.stage_number or 1
        if (p.id, stage_num) in reviewed_keys:
            continue
        reviewed_keys.add((p.id, stage_num))
        tl = p.team_leader
        tl_name = (tl.full_name or tl.username) if tl else "Unassigned"
        
        approved_at = r.decided_at.isoformat() + "Z" if r.decided_at else (p.created_at.isoformat() + "Z" if p.created_at else "")
        stage_num = r.stage_number or 1
        comments = (r.comments or "").strip()
        if not comments:
            wf = ProjectWorkflow.query.filter_by(project_id=p.id, stage_id=stage_num).first()
            if wf and wf.data and isinstance(wf.data, dict):
                comments = wf.data.get('review', {}).get('comments') or ""
        
        result.append({
            "id": p.id,
            "review_id": r.id,
            "project_uid": p.project_uid or f"PRJ-{p.id}",
            "title": p.title,
            "department": p.department.name if p.department else "N/A",
            "plant": p.plant or (p.department.plant.name if p.department and p.department.plant else "General"),
            "team_leader": tl_name,
            "approved_stage": stage_num,
            "stage_number": stage_num,
            "current_stage": p.current_stage,
            "status": f"Stage {stage_num} Approved",
            "comments": comments,
            "approved_at": approved_at
        })
        
    # Also include any closed/completed projects assigned to this reviewer without explicit review records
    if is_admin:
        assigned_closed = Project.query.filter(
            Project.org_id == user.org_id,
            Project.status.in_(['Completed', 'Closed'])
        ).all()
    else:
        assigned_closed = Project.query.filter(
            Project.org_id == user.org_id,
            Project.reviewer_id == user.id,
            Project.status.in_(['Completed', 'Closed'])
        ).all()
    
    for p in assigned_closed:
        if (p.id, p.current_stage) not in reviewed_keys and (p.id, 8) not in reviewed_keys:
            tl = p.team_leader
            tl_name = (tl.full_name or tl.username) if tl else "Unassigned"
            stage_num = p.current_stage or 8
            wf = ProjectWorkflow.query.filter_by(project_id=p.id, stage_id=stage_num).first()
            comments = wf.data.get('review', {}).get('comments') if (wf and wf.data and isinstance(wf.data, dict)) else ""
            result.append({
                "id": p.id,
                "review_id": None,
                "project_uid": p.project_uid or f"PRJ-{p.id}",
                "title": p.title,
                "department": p.department.name if p.department else "N/A",
                "plant": p.plant or (p.department.plant.name if p.department and p.department.plant else "General"),
                "team_leader": tl_name,
                "approved_stage": stage_num,
                "stage_number": stage_num,
                "current_stage": p.current_stage,
                "status": f"Stage {stage_num} Approved",
                "comments": comments,
                "approved_at": p.created_at.isoformat() + "Z" if p.created_at else ""
            })
            
    return jsonify(result), 200

@reviewer_bp.route('/rejected-projects', methods=['GET'])
@reviewer_required
def get_rejected_projects():
    user = db.session.get(User, get_jwt_identity())
    is_admin = (user.role and user.role.name == 'Admin')
    
    if is_admin:
        rejected_reviews = ProjectReview.query.filter_by(
            org_id=user.org_id,
            decision='Rejected'
        ).order_by(ProjectReview.decided_at.desc()).all()
    else:
        rejected_reviews = ProjectReview.query.filter_by(
            org_id=user.org_id,
            reviewer_id=user.id, 
            decision='Rejected'
        ).order_by(ProjectReview.decided_at.desc()).all()
    
    result = []
    reviewed_keys = set()
    
    for r in rejected_reviews:
        p = Project.query.filter_by(id=r.project_id, org_id=user.org_id).first()
        if not p:
            continue
            
        stage_num = r.stage_number or 1
        if (p.id, stage_num) in reviewed_keys:
            continue
        reviewed_keys.add((p.id, stage_num))
        tl = p.team_leader
        tl_name = (tl.full_name or tl.username) if tl else "Unassigned"
        
        rejected_at = r.decided_at.isoformat() + "Z" if r.decided_at else (p.created_at.isoformat() + "Z" if p.created_at else "")
        stage_num = r.stage_number or 1
        comments = (r.comments or p.rejection_reason or "").strip()
        if not comments or comments == 'No reason specified':
            wf = ProjectWorkflow.query.filter_by(project_id=p.id, stage_id=stage_num).first()
            if wf and wf.data and isinstance(wf.data, dict):
                comments = wf.data.get('review', {}).get('comments') or comments
        
        result.append({
            "id": p.id,
            "review_id": r.id,
            "project_uid": p.project_uid or f"PRJ-{p.id}",
            "title": p.title,
            "department": p.department.name if p.department else "N/A",
            "plant": p.plant or (p.department.plant.name if p.department and p.department.plant else "General"),
            "team_leader": tl_name,
            "rejected_stage": stage_num,
            "stage_number": stage_num,
            "rejection_reason": comments or "No reason specified",
            "comments": comments,
            "rejected_at": rejected_at
        })
        
    if is_admin:
        direct_rejected = Project.query.filter(
            Project.org_id == user.org_id,
            Project.status == 'Rejected'
        ).all()
    else:
        direct_rejected = Project.query.filter(
            Project.org_id == user.org_id,
            Project.reviewer_id == user.id,
            Project.status == 'Rejected'
        ).all()
    
    for p in direct_rejected:
        if (p.id, p.current_stage) not in reviewed_keys:
            tl = p.team_leader
            tl_name = (tl.full_name or tl.username) if tl else "Unassigned"
            stage_num = p.current_stage or 1
            wf = ProjectWorkflow.query.filter_by(project_id=p.id, stage_id=stage_num).first()
            comments = wf.data.get('review', {}).get('comments') if (wf and wf.data and isinstance(wf.data, dict)) else (p.rejection_reason or "No reason specified")
            result.append({
                "id": p.id,
                "review_id": None,
                "project_uid": p.project_uid or f"PRJ-{p.id}",
                "title": p.title,
                "department": p.department.name if p.department else "N/A",
                "plant": p.plant or (p.department.plant.name if p.department and p.department.plant else "General"),
                "team_leader": tl_name,
                "rejected_stage": stage_num,
                "stage_number": stage_num,
                "rejection_reason": comments or "No reason specified",
                "comments": comments,
                "rejected_at": p.created_at.isoformat() + "Z" if p.created_at else ""
            })
            
    return jsonify(result), 200

# --- Pending Approvals ---
@reviewer_bp.route('/pending', methods=['GET'])
@reviewer_required
def get_pending_approvals():
    user = db.session.get(User, get_jwt_identity())
    
    # Apply dept filter if user has a specific dept
    user_dept_id = None
    if user.dept and user.dept.name not in ['All', 'N/A']:
        user_dept_id = user.department_id
    
    is_admin = (user.role.name == 'Admin')
    
    # Only show projects assigned to THIS reviewer (or all pending closures for Admin)
    pending_data = _get_pending_projects(user.org_id, user.id, user_dept_id, is_admin=is_admin)
    
    result = []
    for p, stage, workflow in pending_data:
        dept = db.session.get(Department, p.department_id) if p.department_id else None
        tl = db.session.get(User, p.creator_id) if p.creator_id else None
        
        # Build stage_data dict safely from the workflow's JSON data column.
        # For Admin closure review, pull lessons/preventive from SOP instead.
        record_dict = {}
        if stage == 8 and is_admin:
            s8 = Stage8Standardization.query.filter_by(project_id=p.id).first()
            sop = SOP.query.filter_by(project_id=p.id).first()
            record_dict = {
                "lessons_learned": sop.lessons_learned if sop else (s8.lessons_learned if s8 else ""),
                "preventive_actions": sop.preventive_actions if sop else (s8.preventive_actions if s8 else "")
            }
        else:
            # workflow is a ProjectWorkflow object; its .data is the stage JSON payload.
            # The reviewer modal reads `p.stage_data.data` (e.g. `const s3 = d.data || {}`),
            # so wrap the payload under a "data" key to match that shape.
            raw_data = dict(workflow.data) if workflow and workflow.data else {}
            if stage == 1:
                if 'init' not in raw_data:
                    raw_data['init'] = {}
                raw_data['init']['plant'] = p.plant or ''
                raw_data['init']['work_area'] = p.work_area or ''
                raw_data['init']['source'] = p.project_source or ''
                raw_data['init']['ref_number'] = p.reference_number or ''
                if 'planned_start_date' not in raw_data['init'] or not raw_data['init']['planned_start_date']:
                    raw_data['init']['planned_start_date'] = p.start_date.isoformat() if p.start_date else ''
                if 'planned_end_date' not in raw_data['init'] or not raw_data['init']['planned_end_date']:
                    raw_data['init']['planned_end_date'] = p.end_date.isoformat() if p.end_date else ''
            record_dict = {"data": raw_data}
        
        result.append({
            "project_id": p.id,
            "project_uid": p.project_uid,
            "title": p.title,
            "department": dept.name if dept else "N/A",
            "pending_stage": stage,
            "stages_config": p.organization.get_stages_config() if p.organization else [],
            "stage_data": record_dict,
            "submitted_at": (workflow.updated_at.isoformat() + "Z") if (workflow and workflow.updated_at) else (p.created_at.isoformat() + "Z"),
            "team_leader": tl.full_name or tl.username if tl else "Unassigned",
            "team_leader_pic": get_profile_picture_url(tl)
        })
        
    return jsonify(result)

# --- Process Decision ---
@reviewer_bp.route('/decision', methods=['POST'])
@reviewer_required
def process_decision():
    user = db.session.get(User, get_jwt_identity())
    data = request.json or {}
    
    project_id = data.get('project_id')
    decision = data.get('decision')  # 'Approved', 'Rejected', 'Revision'
    comments = data.get('comments')
    pending_stage = data.get('pending_stage') or data.get('stage')
    return _process_decision_logic(user, project_id, decision, comments, pending_stage)

def _process_decision_logic(user, project_id, decision, comments, pending_stage):
    if not comments:
        return jsonify({"msg": "Comments are required"}), 400
        
    if decision not in ['Approved', 'Rejected', 'Revision']:
        return jsonify({"msg": "Invalid decision"}), 400
        
    project = Project.query.filter_by(id=project_id, org_id=user.org_id).first_or_404()
    
    # If project is already permanently rejected, block further decisions
    if project.status in ('Rejected', 'Stage 1 Rejected') or (project.status and 'Rejected' in str(project.status)):
        return jsonify({"msg": "This project has already been permanently rejected and cannot be reviewed again."}), 400

    # Enforce department restriction for Reviewer (unless explicitly assigned as reviewer or global department)
    if user.role.name != 'Admin' and user.dept and user.dept.name not in ['All', 'N/A']:
        if project.reviewer_id != user.id and project.department_id and project.department_id != user.department_id:
            return jsonify({"msg": "Unauthorized: This project does not belong to your department."}), 403
    
    if not pending_stage:
        pending_stage = project.current_stage
    if not pending_stage or pending_stage < 1 or pending_stage > 8:
        return jsonify({"msg": "Invalid or missing pending_stage"}), 400

    # All 8 stages require Reviewer or Admin approval
    if user.role.name not in ('Reviewer', 'Admin'):
        return jsonify({"msg": f"Only a Reviewer can review Stage {pending_stage}."}), 403
        
    decision_lower = decision.lower()
    if decision_lower == 'revision':
        decision_lower = 'send_back'

    tracker = ProjectStageTracker.query.filter_by(project_id=project_id, stage_number=pending_stage).first()
    
    if decision_lower in ('approve', 'approved'):
        if pending_stage == 8:
            # Reviewer approves Stage 8 submission.
            project.status = 'Stage 8 Reviewer Approved'
            if tracker:
                tracker.status = 'Approved'
            
            wf = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=8).first()
            
            # Check if reviewer submitted team_recognition awards
            data_payload = request.get_json() or {}
            team_rec_payload = data_payload.get('team_recognition')
            if team_rec_payload and wf:
                d = dict(wf.data or {})
                d['team_recognition'] = team_rec_payload
                wf.data = d
                flag_modified(wf, 'data')
            
            # Legacy Stage 8 model if it exists
            s8 = Stage8Standardization.query.filter_by(project_id=project_id).first()
            if not s8:
                s8 = Stage8Standardization(project_id=project_id, org_id=project.org_id)
                db.session.add(s8)
            
            # Sync Stage 8 workflow data to specific columns on the Standardization model
            if wf and wf.data:
                wf_data = wf.data
                s8.standardization = wf_data.get('standardization')
                s8.training_adoption = wf_data.get('training_adoption')
                s8.horizontal_deployment = wf_data.get('horizontal_deployment')
                s8.lessons_learned = wf_data.get('lessons_learned')
                s8.benefits_summary = wf_data.get('benefits_summary')
                s8.remaining_opportunities = wf_data.get('remaining_opportunities')
                s8.knowledge_repository = wf_data.get('knowledge_repository')
                s8.team_recognition = wf_data.get('team_recognition')
                s8.project_closure = wf_data.get('project_closure')
                if not s8.training_records:
                    s8.training_records = wf_data.get('training_adoption')

            action_label = "Stage 8 Reviewer Approved"
        else:
            is_early_closure = False
            if pending_stage == 2:
                wf2 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=2).first()
                sv = (wf2.data.get('standard_verification') or wf2.data.get('interim_verification') or {}) if (wf2 and isinstance(wf2.data, dict)) else {}
                if not sv:
                    s2 = Stage2ObservationDataCollection.query.filter_by(project_id=project_id).first()
                    sv = s2.interim_verification or {} if s2 else {}
                deviation_found = sv.get('sop_dev') or sv.get('spec_dev') or sv.get('cp_dev')
                if not deviation_found:
                    is_early_closure = True

            if is_early_closure:
                if tracker:
                    tracker.status = 'Completed'
                    tracker.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                
                project.status = 'Pending Closure'
                
                # Send notification to Admin that this project is pending early closure
                from app.presentation.routes.notification_routes import create_notification
                admins = User.query.join(Role).filter(
                    User.org_id == project.org_id,
                    Role.name == 'Admin'
                ).all()
                for admin in admins:
                    create_notification(
                        org_id=project.org_id,
                        user_id=admin.id,
                        title="Project Awaiting Early Closure Approval",
                        message=f"Project '{project.title}' has no deviations found. Awaiting your final sign-off to close the project.",
                        link=f"/projects/project-details.html?id={project_id}"
                    )
                action_label = "Stage 2 Approved (No Deviation - Early Closure Requested)"
            else:
                if tracker:
                    tracker.status = 'Completed'
                    tracker.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                project.status = f'Stage {pending_stage} Approved'
                project.current_stage = pending_stage + 1
                
                # Unlock Next Stage
                next_tracker = ProjectStageTracker.query.filter_by(project_id=project_id, stage_number=pending_stage + 1).first()
                if next_tracker:
                    next_tracker.status = 'Incomplete'
                    next_tracker.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
                action_label = f"Stage {pending_stage} Approved"
            
    elif decision_lower in ('reject', 'rejected'):
        if tracker:
            tracker.status = 'Rejected'
        project.status = 'Rejected'
        project.rejection_reason = comments
        action_label = f"Project Rejected"
    else: # send_back / revision
        # Reset project to Stage 1 for team edits
        project.current_stage = 1
        project.status = 'Revision Required'
        project.rejection_reason = comments
        
        # Reset Stage 1 tracker
        t1 = ProjectStageTracker.query.filter_by(project_id=project_id, stage_number=1).first()
        if t1:
            t1.status = 'Incomplete'
        if tracker and pending_stage != 1:
            tracker.status = 'Incomplete'
            
        action_label = f"Revision Requested for Stage {pending_stage}"

    # Save review comments to workflow
    workflow = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=pending_stage).first()
    if not workflow:
        workflow = ProjectWorkflow(
            project_id=project_id,
            org_id=user.org_id,
            stage_id=pending_stage,
            data={}
        )
        db.session.add(workflow)
        
    d = dict(workflow.data or {})
    d['review'] = {
        'decision': decision_lower,
        'comments': comments,
        'reviewer': user.username,
        'reviewed_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    }
    workflow.data = d
    flag_modified(workflow, 'data')

    # Add/Update the ProjectReview log (find existing review for this stage or create new)
    approval = ProjectReview.query.filter_by(project_id=project_id, stage_number=pending_stage).order_by(ProjectReview.id.desc()).first()
    if not approval:
        approval = ProjectReview(
            project_id=project_id,
            org_id=user.org_id,
            stage_number=pending_stage,
            reviewer_id=user.id
        )
        db.session.add(approval)
        
    approval.decision = decision
    approval.comments = comments
    approval.decided_at = datetime.now(timezone.utc).replace(tzinfo=None)
    approval.status = 'Completed' if decision == 'Approved' else 'Action Required'

    # Safely update legacy stage-specific models if they exist in the DB for backwards compatibility
    model = STAGE_MODEL_MAP_REV.get(pending_stage)
    if model:
        record = model.query.filter_by(project_id=project_id).first()
        if not record:
            record = model(project_id=project_id, org_id=project.org_id)
            db.session.add(record)
            
        if pending_stage == 8:
            # Stage 8 final approval fields are updated by Facilitator on final closure, not Reviewer
            pass
        elif pending_stage in (1, 3):
            record.facilitator_approved = (decision_lower in ('approve', 'approved'))
            record.facilitator_approver_id = user.id
            record.facilitator_approved_at = datetime.now(timezone.utc).replace(tzinfo=None)
            record.facilitator_comments = comments
        else:
            record.reviewer_approved = (decision_lower in ('approve', 'approved'))
            record.reviewer_id = user.id
            record.reviewer_approved_at = datetime.now(timezone.utc).replace(tzinfo=None)
            record.reviewer_comments = comments

    # Sync SOP status to match Stage 8 review decision
    if pending_stage == 8:
        sop = SOP.query.filter_by(project_id=project_id, org_id=user.org_id).first()
        if sop:
            if decision_lower in ('reject', 'rejected'):
                sop.status = 'Rejected'
                action_word = 'Reject'
            elif decision_lower == 'send_back':
                sop.status = 'Draft'
                action_word = 'Send Back'
            else:
                sop.status = 'Under Review'
                action_word = 'Approve Submission'
                
            sop_approval = SOPApproval(
                sop_id=sop.id,
                user_id=user.id,
                role=user.role.name,
                action=action_word,
                comments=comments,
                signature=f"Signed by {user.full_name or user.username} at {datetime.now(timezone.utc).replace(tzinfo=None).isoformat()}"
            )
            db.session.add(sop_approval)

    from app.presentation.routes.notification_routes import create_notification
    if project.team_leader_id and project.team_leader_id != user.id:
        create_notification(
            user.org_id, project.team_leader_id,
            "Stage Review Update",
            f"Project '{project.title}' Stage {pending_stage} has been {decision} by the reviewer.",
            f"/projects/project-details.html?id={project.id}",
            commit=False
        )

    # When Stage 8 is approved by Reviewer, notify CEO for final closure sign-off
    if pending_stage == 8 and decision_lower in ('approve', 'approved'):
        ceo_role = Role.query.filter_by(name='CEO').first()
        if ceo_role:
            ceo_users = User.query.filter_by(org_id=user.org_id, role_id=ceo_role.id, is_active=True).all()
            for c_u in ceo_users:
                create_notification(
                    user.org_id, c_u.id,
                    "Executive Sign-Off Required",
                    f"Project '{project.title}' ({project.project_uid}) has been approved by Reviewer {user.full_name or user.username} and awaits your final sign-off.",
                    f"/dashboard/dashboard-ceo.html?view=executive-approvals",
                    commit=False
                )

    from app.presentation.routes.workflow_routes import log_action
    log_action(user.org_id, user.id, f"Stage {pending_stage} Reviewer Decision: {decision}", project_id, comments)
    
    db.session.commit()

    # Trigger CEO Email Notification for Stage 8 Reviewer Approval
    if pending_stage == 8 and decision_lower in ('approve', 'approved'):
        try:
            from app.domain.services.email_notification_engine import EmailNotificationEngine
            EmailNotificationEngine.trigger_project_forwarded_to_ceo_notification(project.id, reviewer_id=user.id, comments=comments)
        except Exception as e:
            print(f"[EmailEngine] CEO review notification error: {e}")
    return jsonify({
        "msg": f"Decision '{decision}' for Stage {pending_stage} processed successfully",
        "project_id": project_id,
        "new_stage": project.current_stage
    })

# --- History ---
@reviewer_bp.route('/history', methods=['GET'])
@reviewer_required
def get_history():
    user = db.session.get(User, get_jwt_identity())
    
    # Only show review history for THIS reviewer's decisions
    query = ProjectReview.query.filter_by(org_id=user.org_id, reviewer_id=user.id)
    history = query.order_by(ProjectReview.decided_at.desc()).limit(10).all()
    
    result = []
    for h in history:
        p = db.session.get(Project, h.project_id)
        result.append({
            "project_title": p.title if p else "Deleted Project",
            "decision": h.decision,
            "created_at": h.decided_at.isoformat() + "Z" if h.decided_at else h.created_at.isoformat() + "Z"
        })
    return jsonify(result)

# Legacy alias for frontend compatibility if needed
@reviewer_bp.route('/queue', methods=['GET'])
@reviewer_required
def get_queue_alias():
    return get_pending_approvals()

@reviewer_bp.route('/decision/<int:project_id>', methods=['POST'])
@reviewer_required
def process_decision_alias(project_id):
    user = db.session.get(User, get_jwt_identity())
    data = request.json or {}
    decision = data.get('decision')
    comments = data.get('comments')
    pending_stage = data.get('pending_stage')
    return _process_decision_logic(user, project_id, decision, comments, pending_stage)

# ─── Audit Log Helper ─────────────────────────────────────────
def log_action(org_id, user_id, action, project_id=None, details=None):
    log = AuditLog(
        org_id=org_id,
        user_id=user_id,
        project_id=project_id,
        action=action,
        details=details
    )
    db.session.add(log)

# ─── Stage 8 Reviewer Impact & Closure Routes ──────────────────

@reviewer_bp.route('/impact-projects', methods=['GET'])
@reviewer_required
def get_impact_review():
    user = db.session.get(User, get_jwt_identity())
    is_admin = user.role.name == 'Admin'
    
    approved_impact_ids = [s.project_id for s in Stage8Standardization.query.filter_by(status='Approved').all()]

    query = Project.query.filter(
        Project.org_id == user.org_id,
        Project.current_stage == 8,
        ~Project.status.in_(['Closed', 'Pending CEO Review', 'Pending CEO Closure', 'Impact Approved']),
        Project.status.in_(['Stage 8 Submitted', 'Stage 8 Reviewer Approved', 'Stage 8 Approved'])
    )
    if approved_impact_ids:
        query = query.filter(~Project.id.in_(approved_impact_ids))

    # Apply dept filter if user has a specific dept
    user_dept_id = None
    if user.dept and user.dept.name not in ['All', 'N/A']:
        user_dept_id = user.department_id

    if not is_admin:
        from sqlalchemy import or_
        if user_dept_id:
            query = query.filter(or_(Project.department_id == user_dept_id, Project.reviewer_id == user.id, Project.department_id.is_(None)))
        else:
            query = query.filter(or_(Project.reviewer_id == user.id, Project.department_id.is_(None)))
        
    projects = query.all()
    result = []
    for p in projects:
        impact = Stage8Standardization.query.filter_by(project_id=p.id).first()
        sop = SOP.query.filter_by(project_id=p.id).first()
        wf = ProjectWorkflow.query.filter_by(project_id=p.id, stage_id=8).first()
        wf_data = wf.data if (wf and wf.data) else {}

        has_sop = (sop is not None) or bool(impact and impact.sop_standardization) or bool(wf_data.get('sop_standardization'))
        
        baseline_data = getattr(impact, 'baseline_data', None) or wf_data.get('baseline') or wf_data.get('baseline_data')
        final_data = getattr(impact, 'final_data', None) or wf_data.get('final') or wf_data.get('final_data') or wf_data.get('metrics')
        has_impact = bool(final_data is not None)

        kpi_pct = getattr(impact, 'kpi_improvement_pct', None)
        if (kpi_pct is None or kpi_pct == 0) and baseline_data and final_data:
            try:
                b_val = float(str(baseline_data.get('value', 0) if isinstance(baseline_data, dict) else baseline_data))
                f_val = float(str(final_data.get('value', 0) if isinstance(final_data, dict) else final_data))
                if b_val > 0:
                    kpi_pct = round(((f_val - b_val) / b_val) * 100, 2)
            except (ValueError, TypeError, AttributeError):
                pass
        if kpi_pct is None:
            kpi_pct = wf_data.get('kpi_improvement_pct', 0)

        # Fetch action_plan from Stage 7
        s7 = Stage7PerformanceVerificationBenefitsRealization.query.filter_by(project_id=p.id).first()

        result.append({
            "id": p.id,
            "title": p.title,
            "baseline": baseline_data,
            "final": final_data,
            "kpi_improvement_pct": kpi_pct or 0,
            "kpi_target": s7.action_plan if (s7 and s7.action_plan) else {},
            "cost_savings": impact.cost_savings if impact else (wf_data.get('cost_savings', 0) or 0),
            "status": p.status,
            "impact_status": impact.status if impact else "Pending",
            "approved": (impact.status == "Approved") if impact else False,
            "has_sop": has_sop,
            "sop_id": sop.id if sop else None,
            "has_impact": has_impact
        })
    return jsonify(result)

@reviewer_bp.route('/stage8/<int:project_id>/approve-submission', methods=['POST'])
@reviewer_required
def approve_stage8_submission(project_id):
    user = db.session.get(User, get_jwt_identity())
    project = Project.query.filter_by(id=project_id, org_id=user.org_id).first_or_404()

    # Enforce department restriction for Reviewer (unless explicitly assigned as reviewer or global department)
    if user.role.name != 'Admin' and user.dept and user.dept.name not in ['All', 'N/A']:
        if project.reviewer_id != user.id and project.department_id and project.department_id != user.department_id:
            return jsonify({"msg": "Unauthorized: This project does not belong to your department."}), 403

    if project.current_stage != 8:
        return jsonify({"msg": f"Project is not in Stage 8."}), 400

    if project.status in ('Closed', 'Rejected', 'Stage 1 Rejected'):
        return jsonify({"msg": f"Project is already {project.status.lower()} and cannot be approved."}), 400

    if project.status != 'Impact Approved':
        project.status = 'Stage 8 Approved'
    tracker = ProjectStageTracker.query.filter_by(project_id=project_id, stage_number=8).first()
    if tracker:
        tracker.status = 'Approved'

    payload = request.get_json() or {}
    team_recognition = payload.get('team_recognition')
    if team_recognition:
        wf = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=8).first()
        if wf:
            d = dict(wf.data or {})
            d['team_recognition'] = team_recognition
            wf.data = d
            flag_modified(wf, 'data')
        s8 = Stage8Standardization.query.filter_by(project_id=project_id).first()
        if not s8:
            s8 = Stage8Standardization(project_id=project_id, org_id=project.org_id)
            db.session.add(s8)
        s8.team_recognition = team_recognition

    log_action(project.org_id, user.id, "Approved Stage 8 Submission by Reviewer", project_id)
    db.session.commit()
    return jsonify({"msg": "Stage 8 submission approved. Proceed to Impact Review."}), 200

@reviewer_bp.route('/impact/<int:project_id>/post-data', methods=['POST'])
@reviewer_required
def add_post_data(project_id):
    user = db.session.get(User, get_jwt_identity())
    data = request.get_json() or {}

    project = Project.query.filter_by(id=project_id, org_id=user.org_id).first_or_404()

    # Enforce department restriction for Reviewer (unless explicitly assigned as reviewer or global department)
    if user.role.name != 'Admin' and user.dept and user.dept.name not in ['All', 'N/A']:
        if project.reviewer_id != user.id and project.department_id and project.department_id != user.department_id:
            return jsonify({"msg": "Unauthorized: This project does not belong to your department."}), 403
    if project.current_stage != 8:
        return jsonify({"msg": "Project is not in Stage 8"}), 400

    impact = Stage8Standardization.query.filter_by(project_id=project_id).first()
    if not impact:
        impact = Stage8Standardization(project_id=project_id, org_id=project.org_id)
        db.session.add(impact)

    wf = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=8).first()
    if not wf:
        wf = ProjectWorkflow(project_id=project_id, stage_id=8, org_id=project.org_id, data={})
        db.session.add(wf)
    wf_dict = dict(wf.data or {})

    metrics = data.get('metrics') or []
    if metrics and isinstance(metrics, list):
        wf_dict['metrics'] = metrics
        wf_dict['benefits_summary'] = metrics
        first_metric = metrics[0]
        wf_dict['baseline'] = {"label": first_metric.get('label', 'KPI'), "value": first_metric.get('baseline', 0)}
        wf_dict['final'] = {"label": first_metric.get('label', 'KPI'), "value": first_metric.get('final', 0)}

        pct_sum = 0
        pct_cnt = 0
        for m in metrics:
            try:
                b_val = float(str(m.get('baseline', 0)))
                f_val = float(str(m.get('final', 0)))
                if b_val > 0:
                    chg = round(((f_val - b_val) / b_val) * 100, 2)
                    pct_sum += chg
                    pct_cnt += 1
            except (ValueError, TypeError):
                pass
        if pct_cnt > 0:
            impact.kpi_improvement_pct = round(pct_sum / pct_cnt, 2)
            wf_dict['kpi_improvement_pct'] = impact.kpi_improvement_pct
    else:
        if 'baseline_data' in data:
            wf_dict['baseline'] = data['baseline_data']
        if 'final_data' in data:
            wf_dict['final'] = data['final_data']
        if 'baseline_data' in data and 'final_data' in data:
            try:
                b_val = float(str(data['baseline_data'].get('value', 0) if isinstance(data['baseline_data'], dict) else data['baseline_data']))
                f_val = float(str(data['final_data'].get('value', 0) if isinstance(data['final_data'], dict) else data['final_data']))
                if b_val > 0:
                    impact.kpi_improvement_pct = round(((f_val - b_val) / b_val) * 100, 2)
                    wf_dict['kpi_improvement_pct'] = impact.kpi_improvement_pct
            except (ValueError, TypeError, AttributeError):
                pass

    if 'impact_vouchers' in data:
        wf_dict['impact_vouchers'] = data['impact_vouchers']

    wf.data = wf_dict
    flag_modified(wf, 'data')

    project.status = 'Impact Approved'
    impact.status = 'Approved'
    impact.approved_by = user.id

    log_action(project.org_id, user.id, "Stage 8 Post-Data Added by Reviewer", project_id, str(data))
    db.session.commit()
    return jsonify({"msg": "Post-implementation impact data saved and review approved.", "kpi_improvement_pct": impact.kpi_improvement_pct}), 200

@reviewer_bp.route('/closure-projects', methods=['GET'])
@reviewer_required
def get_closure_projects():
    user = db.session.get(User, get_jwt_identity())
    is_admin = user.role.name == 'Admin'
    
    query = Project.query.filter(
        Project.org_id == user.org_id,
        Project.current_stage == 8,
        Project.status != 'Closed'
    )
    # Apply dept filter if user has a specific dept
    user_dept_id = None
    if user.dept and user.dept.name not in ['All', 'N/A']:
        user_dept_id = user.department_id

    if not is_admin:
        from sqlalchemy import or_
        if user_dept_id:
            query = query.filter(or_(Project.department_id == user_dept_id, Project.reviewer_id == user.id, Project.department_id.is_(None)))
        else:
            query = query.filter(or_(Project.reviewer_id == user.id, Project.department_id.is_(None)))
        
    projects = query.all()
    result = []
    for p in projects:
        std = Stage8Standardization.query.filter_by(project_id=p.id).first()
        sop = SOP.query.filter_by(project_id=p.id).first()
        
        # Fallback to Stage 8 workflow JSON data if available
        wf = ProjectWorkflow.query.filter_by(project_id=p.id, stage_id=8).first()
        wf_data = wf.data if (wf and wf.data) else {}

        if sop:
            sop_status = sop.status
        elif std and (std.sop_standardization or getattr(std, 'sop_details', None)):
            sop_status = "Uploaded"
        elif wf_data.get('sop_standardization'):
            sop_status = "Uploaded"
        else:
            sop_status = "Pending"

        has_lessons = bool((std and std.lessons_learned) or wf_data.get('lessons_learned'))
        has_training = bool(
            (std and (getattr(std, 'horizontal_deployment', None) or getattr(std, 'training_records', None) or getattr(std, 'training_adoption', None))) 
            or wf_data.get('training_adoption') 
            or wf_data.get('training_records')
            or wf_data.get('horizontal_deployment')
        )
        result.append({
            "id": p.id,
            "title": p.title,
            "status": p.status,
            "is_pending_ceo": p.status in ['Pending CEO Review', 'Pending CEO Closure'],
            "sop_status": sop_status,
            "sop_id": sop.id if sop else None,
            "has_training_records": has_training,
            "has_lessons": has_lessons,
            "facilitator_signoff": std.facilitator_validation if std else False,
            "admin_closure": std.admin_closure if std else False
        })
    return jsonify(result)

@reviewer_bp.route('/closure/<int:project_id>/complete', methods=['POST'])
@reviewer_required
def complete_closure(project_id):
    user = db.session.get(User, get_jwt_identity())
    data = request.get_json() or {}

    project = Project.query.filter_by(id=project_id, org_id=user.org_id).first_or_404()

    # Enforce department restriction for Reviewer (unless explicitly assigned as reviewer or global department)
    if user.role.name != 'Admin' and user.dept and user.dept.name not in ['All', 'N/A']:
        if project.reviewer_id != user.id and project.department_id and project.department_id != user.department_id:
            return jsonify({"msg": "Unauthorized: This project does not belong to your department."}), 403
    if project.current_stage != 8:
        return jsonify({"msg": "Project is not in Stage 8"}), 400

    sop = SOP.query.filter_by(project_id=project_id, org_id=project.org_id).first()
    s8 = Stage8Standardization.query.filter_by(project_id=project_id).first()
    if not s8:
        s8 = Stage8Standardization(project_id=project_id, org_id=project.org_id)
        db.session.add(s8)

    # Update closure fields
    if 'lessons_learned' in data:
        s8.lessons_learned = data['lessons_learned']
    if 'preventive_actions' in data:
        s8.preventive_actions = data['preventive_actions']
    if 'training_records' in data:
        s8.training_records = data['training_records']

    # Update the linked SOP with lessons learned and preventive actions if SOP exists
    if sop:
        if 'lessons_learned' in data:
            sop.lessons_learned = data['lessons_learned']
        if 'preventive_actions' in data:
            sop.preventive_actions = data['preventive_actions']

    send_to_ceo = data.get('send_to_ceo', False) or data.get('action') == 'send_to_ceo'

    if send_to_ceo:
        # Escalate to CEO for Final Review and Closure
        project.status = 'Pending CEO Review'
        s8.facilitator_validation = True
        reviewer_note = data.get('reviewer_notes') or data.get('comments') or 'Reviewer validated Stage 8. Sent to CEO for final executive sign-off & closure.'
        s8.final_comments = f"Reviewer validated: {reviewer_note}"

        db.session.flush()

        from app.presentation.routes.notification_routes import create_notification

        # Find CEO users in this organization
        ceo_users = User.query.join(Role).filter(
            User.org_id == project.org_id,
            Role.name == 'CEO'
        ).all()

        for ceo in ceo_users:
            create_notification(
                user.org_id, ceo.id,
                "Project Awaiting CEO Review & Closure",
                f"Reviewer completed Stage 8 review for project '{project.title}'. Awaiting your executive review and closure sign-off.",
                f"/dashboard/dashboard-ceo.html?view=executive-approvals",
                commit=False
            )

        log_action(project.org_id, user.id, "Stage 8 Review: Sent to CEO for Final Review and Closure", project_id, str(data))
        db.session.commit()

        return jsonify({
            "msg": f"Project '{project.title}' has been successfully forwarded to the CEO for executive review and closure.",
            "status": "Pending CEO Review",
            "pending_ceo": True
        }), 200

    # Direct Reviewer Closure via Domain Service
    from app.domain.services.project_closure_service import ProjectClosureService
    try:
        res = ProjectClosureService.execute_closure(
            project_id=project_id,
            user_id=user.id,
            comments="Reviewer signed off. Project closed.",
            sign_off_by_role="Reviewer"
        )
        return jsonify({
            "msg": res["message"],
            "facilitator_validation": True,
            "closed": True
        }), 200
    except Exception as e:
        db.session.rollback()
        return internal_server_error(e, "Failed to complete project closure.")

# --- Reviewer Notes ---
@reviewer_bp.route('/notes', methods=['POST'])
@reviewer_required
def add_note():
    user = db.session.get(User, get_jwt_identity())
    data = request.get_json()

    project_id = data.get('project_id')
    stage_number = data.get('stage_number')
    note_text = data.get('note_text', '').strip()

    if not all([project_id, stage_number, note_text]):
        return jsonify({"msg": "project_id, stage_number, and note_text are required"}), 400

    note = FacilitatorNote(
        org_id=user.org_id,
        project_id=project_id,
        stage_number=stage_number,
        note_text=note_text,
        created_by=user.id
    )
    db.session.add(note)
    
    log_action(user.org_id, user.id, f"Added Note for Stage {stage_number}", project_id, note_text)
    db.session.commit()
    
    return jsonify({
        "msg": "Note added successfully",
        "id": note.id
    }), 201
