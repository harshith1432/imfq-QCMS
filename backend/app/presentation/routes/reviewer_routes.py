from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.infrastructure.database.models.models import (
    User, Project, ProjectReview, Department, ProjectStageTracker, ProjectWorkflow,
    Stage1ProblemDefinitionProjectInitiation, Stage2ObservationDataCollection, Stage3CauseIdentification,
    Stage4RootCauseAnalysisVerification, Stage5CountermeasurePlanningSolutionDevelopment, 
    Stage6ImplementationChangeManagement, Stage7PerformanceVerificationBenefitsRealization,
    Stage8Standardization, SOP, SOPTraining, SOPComment, SOPApproval, AuditLog
)
from sqlalchemy.orm.attributes import flag_modified
from app import db
from functools import wraps
from datetime import datetime
from app.utils.avatar_utils import get_profile_picture_url

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
    # All reviewers in the org can see all pending submissions (not filtered by reviewer_id).
    query = Project.query.filter(
        Project.org_id == org_id,
        Project.status != 'Closed'
    )
    if user_dept_id:
        query = query.filter(Project.department_id == user_dept_id)
        
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
        user = User.query.get(current_user_id)
        if not user or user.role.name not in ('Reviewer', 'Admin'):
            return jsonify({"msg": "Reviewer/Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function

# --- Dashboard Stats ---
@reviewer_bp.route('/stats', methods=['GET'])
@reviewer_required
def get_stats():
    user = User.query.get(get_jwt_identity())
    
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
    impact_query = Project.query.filter(
        Project.org_id == user.org_id,
        Project.current_stage == 8,
        Project.status != 'Closed',
        Project.status.in_(['Stage 8 Submitted', 'Stage 8 Reviewer Approved', 'Stage 8 Approved'])
    )
    if not is_admin:
        if user_dept_id:
            impact_query = impact_query.filter(Project.department_id == user_dept_id)
        else:
            impact_query = impact_query.filter(Project.reviewer_id == user.id)
    pending_impact = impact_query.count()

    # Stage 8 closure projects (SOP created, ready for closure)
    closure_query = Project.query.filter(
        Project.org_id == user.org_id,
        Project.current_stage == 8,
        Project.status != 'Closed',
        Project.status.in_(['Impact Approved', 'SOP Created', 'Pending Closure'])
    )
    if not is_admin:
        if user_dept_id:
            closure_query = closure_query.filter(Project.department_id == user_dept_id)
        else:
            closure_query = closure_query.filter(Project.reviewer_id == user.id)
    pending_closure = closure_query.count()

    # Average improvement
    impacts_query = Stage8Standardization.query.join(Project).filter(
        Project.org_id == user.org_id,
        Stage8Standardization.baseline_data.isnot(None),
        Stage8Standardization.final_data.isnot(None)
    )
    if not is_admin:
        if user_dept_id:
            impacts_query = impacts_query.filter(Project.department_id == user_dept_id)
        else:
            impacts_query = impacts_query.filter(Project.reviewer_id == user.id)
    impacts = impacts_query.all()
    avg_improvement = 0
    if impacts:
        avg_improvement = round(sum([i.kpi_improvement_pct or 0 for i in impacts]) / len(impacts), 1)

    return jsonify({
        "pending_count": pending_count,
        "pending_impact": pending_impact,
        "pending_closure": pending_closure,
        "avg_improvement": f"{avg_improvement}%"
    })

# --- Pending Approvals ---
@reviewer_bp.route('/pending', methods=['GET'])
@reviewer_required
def get_pending_approvals():
    user = User.query.get(get_jwt_identity())
    
    # Apply dept filter if user has a specific dept
    user_dept_id = None
    if user.dept and user.dept.name not in ['All', 'N/A']:
        user_dept_id = user.department_id
    
    is_admin = (user.role.name == 'Admin')
    
    # Only show projects assigned to THIS reviewer (or all pending closures for Admin)
    pending_data = _get_pending_projects(user.org_id, user.id, user_dept_id, is_admin=is_admin)
    
    result = []
    for p, stage, workflow in pending_data:
        dept = Department.query.get(p.department_id)
        tl = User.query.get(p.creator_id) if p.creator_id else None
        
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
    user = User.query.get(get_jwt_identity())
    data = request.json
    
    project_id = data.get('project_id')
    decision = data.get('decision')  # 'Approved', 'Rejected', 'Revision'
    comments = data.get('comments')
    pending_stage = data.get('pending_stage')
    return _process_decision_logic(user, project_id, decision, comments, pending_stage)

def _process_decision_logic(user, project_id, decision, comments, pending_stage):
    if not comments:
        return jsonify({"msg": "Comments are required"}), 400
        
    if decision not in ['Approved', 'Rejected', 'Revision']:
        return jsonify({"msg": "Invalid decision"}), 400
        
    project = Project.query.filter_by(id=project_id, org_id=user.org_id).first_or_404()
    
    # Enforce department restriction for Reviewer
    if user.role.name != 'Admin' and user.dept and user.dept.name not in ['All', 'N/A']:
        if project.department_id != user.department_id:
            return jsonify({"msg": "Unauthorized: This project does not belong to your department."}), 403
    
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
            
            # Legacy Stage 8 model if it exists
            s8 = Stage8Standardization.query.filter_by(project_id=project_id).first()
            if not s8:
                s8 = Stage8Standardization(project_id=project_id, org_id=project.org_id)
                db.session.add(s8)
            
            # Sync Stage 8 workflow data to specific columns on the Standardization model
            wf = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=8).first()
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
                from app.infrastructure.database.models.models import Stage2ObservationDataCollection
                s2 = Stage2ObservationDataCollection.query.filter_by(project_id=project_id).first()
                sv = s2.standard_verification or {} if s2 else {}
                deviation_found = sv.get('sop_dev') or sv.get('spec_dev') or sv.get('cp_dev')
                if not deviation_found:
                    is_early_closure = True

            if is_early_closure:
                if tracker:
                    tracker.status = 'Completed'
                    tracker.completed_at = datetime.utcnow()
                
                project.status = 'Pending Closure'
                
                # Send notification to Admin that this project is pending early closure
                from app.presentation.routes.notification_routes import create_notification
                from app.infrastructure.database.models.models import User, Role
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
                    tracker.completed_at = datetime.utcnow()
                project.status = f'Stage {pending_stage} Approved'
                project.current_stage = pending_stage + 1
                
                # Unlock Next Stage
                next_tracker = ProjectStageTracker.query.filter_by(project_id=project_id, stage_number=pending_stage + 1).first()
                if next_tracker:
                    next_tracker.status = 'Incomplete'
                    next_tracker.started_at = datetime.utcnow()
                action_label = f"Stage {pending_stage} Approved"
            
    elif decision_lower in ('reject', 'rejected'):
        if tracker:
            tracker.status = 'Rejected'
        if pending_stage == 8:
            project.status = 'Stage 8 Rejected'
        else:
            project.status = f'Stage {pending_stage} Rejected'
        action_label = f"Stage {pending_stage} Rejected"
    else: # send_back
        if tracker:
            tracker.status = 'Incomplete'
        if pending_stage == 8:
            project.status = 'Stage 8 In Progress'
        else:
            project.status = f'Stage {pending_stage} In Progress'
        action_label = f"Stage {pending_stage} Sent Back"

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
        'reviewed_at': datetime.utcnow().isoformat()
    }
    workflow.data = d
    flag_modified(workflow, 'data')

    # Add/Update the ProjectReview log
    approval = ProjectReview.query.filter_by(project_id=project_id, stage_number=pending_stage, status='Pending').first()
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
    approval.decided_at = datetime.utcnow()
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
            record.facilitator_approved_at = datetime.utcnow()
            record.facilitator_comments = comments
        else:
            record.reviewer_approved = (decision_lower in ('approve', 'approved'))
            record.reviewer_id = user.id
            record.reviewer_approved_at = datetime.utcnow()
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
                signature=f"Signed by {user.full_name or user.username} at {datetime.utcnow().isoformat()}"
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

    from app.presentation.routes.workflow_routes import log_action
    log_action(user.org_id, user.id, f"Stage {pending_stage} Reviewer Decision: {decision}", project_id, comments)
    
    db.session.commit()
    return jsonify({
        "msg": f"Decision '{decision}' for Stage {pending_stage} processed successfully",
        "project_id": project_id,
        "new_stage": project.current_stage
    })

# --- History ---
@reviewer_bp.route('/history', methods=['GET'])
@reviewer_required
def get_history():
    user = User.query.get(get_jwt_identity())
    
    # Only show review history for THIS reviewer's decisions
    query = ProjectReview.query.filter_by(org_id=user.org_id, reviewer_id=user.id)
    if user.dept and user.dept.name not in ['All', 'N/A']:
        query = query.join(Project, ProjectReview.project_id == Project.id).filter(Project.department_id == user.department_id)
        
    history = query.order_by(ProjectReview.decided_at.desc()).limit(10).all()
    
    result = []
    for h in history:
        p = Project.query.get(h.project_id)
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
    user = User.query.get(get_jwt_identity())
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
    user = User.query.get(get_jwt_identity())
    is_admin = user.role.name == 'Admin'
    
    query = Project.query.filter(
        Project.org_id == user.org_id,
        Project.current_stage == 8,
        Project.status != 'Closed',
        Project.status.in_(['Stage 8 Submitted', 'Stage 8 Reviewer Approved', 'Stage 8 Approved'])
    )
    # Apply dept filter if user has a specific dept
    user_dept_id = None
    if user.dept and user.dept.name not in ['All', 'N/A']:
        user_dept_id = user.department_id

    if not is_admin:
        if user_dept_id:
            query = query.filter(Project.department_id == user_dept_id)
        else:
            query = query.filter(Project.reviewer_id == user.id)
        
    projects = query.all()
    result = []
    for p in projects:
        impact = Stage8Standardization.query.filter_by(project_id=p.id).first()
        sop = SOP.query.filter_by(project_id=p.id).first()
        has_sop = sop is not None
        has_impact = bool(impact and impact.final_data is not None)

        kpi_pct = None
        if impact and impact.baseline_data and impact.final_data:
            try:
                baseline_val = float(str(impact.baseline_data.get('value', 0)))
                final_val = float(str(impact.final_data.get('value', 0)))
                if baseline_val > 0:
                    kpi_pct = round(((final_val - baseline_val) / baseline_val) * 100, 2)
                    if kpi_pct != impact.kpi_improvement_pct:
                        impact.kpi_improvement_pct = kpi_pct
                        db.session.commit()
            except (ValueError, TypeError, AttributeError):
                pass

        # Fetch action_plan from Stage 7
        from app.infrastructure.database.models.models import Stage7PerformanceVerificationBenefitsRealization
        s7 = Stage7PerformanceVerificationBenefitsRealization.query.filter_by(project_id=p.id).first()

        result.append({
            "id": p.id,
            "title": p.title,
            "baseline": impact.baseline_data if impact else None,
            "final": impact.final_data if impact else None,
            "kpi_improvement_pct": kpi_pct or (impact.kpi_improvement_pct if impact else 0),
            "kpi_target": s7.action_plan if s7 else {},
            "cost_savings": impact.cost_savings if impact else 0,
            "status": p.status,
            "impact_status": impact.status if impact else "Pending",
            "approved": impact.status == "Approved" if impact else False,
            "has_sop": has_sop,
            "sop_id": sop.id if sop else None,
            "has_impact": has_impact
        })
    return jsonify(result)

@reviewer_bp.route('/stage8/<int:project_id>/approve-submission', methods=['POST'])
@reviewer_required
def approve_stage8_submission(project_id):
    user = User.query.get(get_jwt_identity())
    project = Project.query.filter_by(id=project_id, org_id=user.org_id).first_or_404()

    # Enforce department restriction for Reviewer
    if user.role.name != 'Admin' and user.dept and user.dept.name not in ['All', 'N/A']:
        if project.department_id != user.department_id:
            return jsonify({"msg": "Unauthorized: This project does not belong to your department."}), 403

    if project.current_stage != 8:
        return jsonify({"msg": f"Project is not in Stage 8."}), 400

    if project.status != 'Stage 8 Submitted':
        return jsonify({"msg": f"Project submission not pending approval (current status: '{project.status}')."}), 400

    project.status = 'Stage 8 Approved'
    tracker = ProjectStageTracker.query.filter_by(project_id=project_id, stage_number=8).first()
    if tracker:
        tracker.status = 'Approved'
    log_action(project.org_id, user.id, "Approved Stage 8 Submission by Reviewer", project_id)
    db.session.commit()
    return jsonify({"msg": "Stage 8 submission approved. Proceed to Impact Review."}), 200

@reviewer_bp.route('/impact/<int:project_id>/post-data', methods=['POST'])
@reviewer_required
def add_post_data(project_id):
    user = User.query.get(get_jwt_identity())
    data = request.get_json()

    project = Project.query.filter_by(id=project_id, org_id=user.org_id).first_or_404()

    # Enforce department restriction for Reviewer
    if user.role.name != 'Admin' and user.dept and user.dept.name not in ['All', 'N/A']:
        if project.department_id != user.department_id:
            return jsonify({"msg": "Unauthorized: This project does not belong to your department."}), 403
    if project.current_stage != 8:
        return jsonify({"msg": "Project is not in Stage 8"}), 400

    impact = Stage8Standardization.query.filter_by(project_id=project_id).first()
    if not impact:
        impact = Stage8Standardization(project_id=project_id, org_id=project.org_id)
        db.session.add(impact)

    if 'baseline_data' in data:
        impact.baseline_data = data['baseline_data']
    if 'final_data' in data:
        impact.final_data = data['final_data']
    if 'impact_vouchers' in data:
        impact.impact_vouchers = data['impact_vouchers']

    # Auto-calculate KPI improvement
    if impact.baseline_data and impact.final_data:
        try:
            baseline_val = float(str(impact.baseline_data.get('value', 0)))
            final_val = float(str(impact.final_data.get('value', 0)))
            if baseline_val > 0:
                impact.kpi_improvement_pct = round(((final_val - baseline_val) / baseline_val) * 100, 2)
        except (ValueError, TypeError, AttributeError):
            pass

        # Automatically mark impact as approved and update project status
        project.status = 'Impact Approved'
        impact.status = 'Approved'
        impact.approved_by = user.id

    log_action(project.org_id, user.id, "Stage 8 Post-Data Added by Reviewer", project_id, str(data))
    db.session.commit()
    return jsonify({"msg": "Post-implementation data saved and impact review approved.", "kpi_improvement_pct": impact.kpi_improvement_pct}), 200

@reviewer_bp.route('/closure-projects', methods=['GET'])
@reviewer_required
def get_closure_projects():
    user = User.query.get(get_jwt_identity())
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
        if user_dept_id:
            query = query.filter(Project.department_id == user_dept_id)
        else:
            query = query.filter(Project.reviewer_id == user.id)
        
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
        elif std and std.sop_details:
            sop_status = "Uploaded"
        else:
            sop_status = "Pending"

        has_lessons = bool((std and std.lessons_learned) or wf_data.get('lessons_learned'))
        has_training = bool((std and (std.training_records or std.training_adoption)) or wf_data.get('training_adoption'))
        result.append({
            "id": p.id,
            "title": p.title,
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
    user = User.query.get(get_jwt_identity())
    data = request.get_json() or {}

    project = Project.query.filter_by(id=project_id, org_id=user.org_id).first_or_404()

    # Enforce department restriction for Reviewer
    if user.role.name != 'Admin' and user.dept and user.dept.name not in ['All', 'N/A']:
        if project.department_id != user.department_id:
            return jsonify({"msg": "Unauthorized: This project does not belong to your department."}), 403
    if project.current_stage != 8:
        return jsonify({"msg": "Project is not in Stage 8"}), 400

    sop = SOP.query.filter_by(project_id=project_id, org_id=project.org_id).first()
    if not sop:
        return jsonify({"msg": "Project closure blocked: No SOP is created or linked for this project."}), 400

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

    # Update the linked SOP with lessons learned and preventive actions
    if 'lessons_learned' in data:
        sop.lessons_learned = data['lessons_learned']
    if 'preventive_actions' in data:
        sop.preventive_actions = data['preventive_actions']

    # Validate gates
    lessons = s8.lessons_learned or ''
    if isinstance(lessons, dict) or isinstance(lessons, list):
        import json
        lessons = json.dumps(lessons)
    lessons = str(lessons).strip()

    preventive = s8.preventive_actions or ''
    if isinstance(preventive, dict) or isinstance(preventive, list):
        import json
        preventive = json.dumps(preventive)
    preventive = str(preventive).strip()

    if not lessons or lessons == 'null':
        return jsonify({"msg": "Project closure blocked: Lessons learned must be entered in the SOP."}), 400
    if not preventive or preventive == 'null':
        return jsonify({"msg": "Project closure blocked: Preventive actions must be completed and entered in the SOP."}), 400

    pending_training = SOPTraining.query.filter_by(sop_id=sop.id).filter(
        (SOPTraining.training_completion_status == False) | (SOPTraining.acknowledgement_status == False)
    ).first()
    if pending_training:
        user_info = db.session.get(User, pending_training.user_id)
        user_name = user_info.full_name or user_info.username if user_info else f"ID {pending_training.user_id}"
        return jsonify({"msg": f"Project closure blocked: Assigned training records are not fully completed (Pending for: {user_name})."}), 400

    # Move project to Closed stage directly
    project.status = 'Closed'
    project.end_date = datetime.utcnow().date()
    
    # Sign-offs
    s8.facilitator_validation = True
    s8.admin_closure = True
    s8.final_approval = True
    s8.final_comments = f"Reviewer signed off. Project closed."

    # Mark stage 8 tracker completed
    tracker = ProjectStageTracker.query.filter_by(project_id=project_id, stage_number=8).first()
    if tracker:
        tracker.status = 'Completed'
        tracker.completed_at = datetime.utcnow()

    # Flush session so all changes are visible in db nested transaction
    db.session.flush()

    # Auto-archive project to repository
    from app.presentation.routes.repository_routes import auto_archive_project_to_repository
    try:
        auto_archive_project_to_repository(project_id, user.org_id)
    except Exception as archive_err:
        print(f"[QCMS Reviewer] Auto-archiving failed: {archive_err}")

    # Notify Facilitator and Team
    from app.presentation.routes.notification_routes import create_notification
    
    notify_ids = set()
    if project.team_leader_id: notify_ids.add(project.team_leader_id)
    if project.creator_id: notify_ids.add(project.creator_id)
    if project.facilitator_id: notify_ids.add(project.facilitator_id)
    
    for uid in notify_ids:
        if uid != user.id:
            create_notification(
                user.org_id, uid,
                "Project Officially Closed",
                f"Reviewer signed off and closed project '{project.title}'.",
                f"/projects/project-details.html?id={project_id}",
                commit=False
            )

    log_action(project.org_id, user.id, "Stage 8 Closure Signed Off and Closed by Reviewer", project_id, str(data))
    db.session.commit()

    return jsonify({
        "msg": "Reviewer closure sign-off complete. Project has been officially closed and archived.",
        "facilitator_validation": True,
        "closed": True
    }), 200

# --- Reviewer Notes ---
@reviewer_bp.route('/notes', methods=['POST'])
@reviewer_required
def add_note():
    user = User.query.get(get_jwt_identity())
    data = request.get_json()

    project_id = data.get('project_id')
    stage_number = data.get('stage_number')
    note_text = data.get('note_text', '').strip()

    if not all([project_id, stage_number, note_text]):
        return jsonify({"msg": "project_id, stage_number, and note_text are required"}), 400

    from app.infrastructure.database.models.models import FacilitatorNote
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

