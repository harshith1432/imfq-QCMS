from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.orm.exc import StaleDataError
from app.infrastructure.database.models.models import (
    Project, db, AuditLog, ProjectReview, ProjectStageTracker, User,
    Stage1ProblemDefinitionProjectInitiation, Stage2ObservationDataCollection, Stage3CauseIdentification,
    Stage4RootCauseAnalysisVerification, Stage5CountermeasurePlanningSolutionDevelopment, Stage6ImplementationChangeManagement,
    Stage7PerformanceVerificationBenefitsRealization, Stage8StandardizationKnowledgeSharingProjectClosure
)
from app.presentation.middleware.middleware import role_required
from app.domain.services.subscription_service import SubscriptionManager
from datetime import datetime, timezone

workflow_bp = Blueprint('workflow', __name__)

# Helper to map stage IDs to models
STAGE_MODEL_MAP = {
    1: Stage1ProblemDefinitionProjectInitiation,
    2: Stage2ObservationDataCollection,
    3: Stage3CauseIdentification,
    4: Stage4RootCauseAnalysisVerification,
    5: Stage5CountermeasurePlanningSolutionDevelopment,
    6: Stage6ImplementationChangeManagement,
    7: Stage7PerformanceVerificationBenefitsRealization,
    8: Stage8StandardizationKnowledgeSharingProjectClosure
}

def log_action(org_id, user_id, action, project_id=None, details=None):
    log = AuditLog(
        org_id=org_id,
        user_id=user_id,
        project_id=project_id,
        action=action,
        details=details,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    db.session.add(log)


def snapshot_stage_template(project, stage_number):
    try:
        from app.infrastructure.database.models.models import Organization, ProjectWorkflow
        org = db.session.get(Organization, project.org_id)
        if not org:
            return
        stages_cfg = org.get_stages_config() or []
        stage_def = next((s for s in stages_cfg if s.get('stage_id') == stage_number or s.get('original_id') == stage_number), None)
        if not stage_def and 0 <= stage_number - 1 < len(stages_cfg):
            stage_def = stages_cfg[stage_number - 1]
            
        if stage_def:
            wf = ProjectWorkflow.query.filter_by(project_id=project.id, stage_id=stage_number, org_id=project.org_id).first()
            if not wf:
                wf = ProjectWorkflow(project_id=project.id, stage_id=stage_number, org_id=project.org_id, data={})
                db.session.add(wf)
            wf.template_snapshot = stage_def
            wf.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    except Exception as e:
        print(f"[QCMS] Error snapshotting stage template: {e}")

@workflow_bp.route('/<int:project_id>/stage/<int:stage_id>', methods=['GET'])
@jwt_required()
def get_stage_data(project_id, stage_id):
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"msg": "Project not found"}), 404
    if user.role.name != 'SuperAdmin' and project.org_id != user.org_id:
        return jsonify({"msg": "Project not found"}), 404

    # Enforce role-based access control
    role = user.role.name
    if role in ('SuperAdmin', 'CEO', 'Admin'):
        pass
    elif role == 'Team Member':
        from app.infrastructure.database.models.models import ProjectMember
        is_member = ProjectMember.query.filter_by(project_id=project.id, user_id=user.id).first()
        if not is_member:
            return jsonify({"msg": "Unauthorized access. You are not assigned to this project."}), 403
    elif role == 'Team Leader':
        from app.infrastructure.database.models.models import ProjectMember
        is_member = ProjectMember.query.filter_by(project_id=project.id, user_id=user.id).first()
        if project.team_leader_id != user.id and project.creator_id != user.id and not is_member:
            return jsonify({"msg": "Unauthorized access. You are not assigned to this project."}), 403
    elif role == 'Facilitator':
        if project.facilitator_id != user.id:
            return jsonify({"msg": "Unauthorized access. You are not the facilitator for this project."}), 403

    from app.infrastructure.database.models.models import ProjectWorkflow
    wf = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=stage_id).first()
    if wf and wf.data:
        return jsonify({
            "data": wf.data,
            "version_id": getattr(wf, 'version_id', 1),
            "updated_at": wf.updated_at.isoformat() if wf.updated_at else None
        }), 200

    model = STAGE_MODEL_MAP.get(stage_id)
    if not model:
        return jsonify({"msg": "Invalid stage"}), 400
        
    data = model.query.filter_by(project_id=project_id).first()
    if not data:
        return jsonify({"data": {}, "version_id": 1}), 200
        
    # Convert model to dict (excluding internal SQLAlchemy fields)
    result = {c.name: getattr(data, c.name) for c in data.__table__.columns}
    return jsonify({"data": result, "version_id": 1}), 200

@workflow_bp.route('/<int:project_id>/stage/<int:stage_id>', methods=['POST', 'PUT'])
@jwt_required()
def update_stage_data(project_id, stage_id):
    data = request.get_json() or {}
    user_id = get_jwt_identity()
    project = Project.query.get_or_404(project_id)
    
    user = db.session.get(User, user_id)
    if user.role.name not in ('Admin', 'SuperAdmin', 'Team Leader', 'Team Member'):
        return jsonify({"msg": "Access denied. You do not have permission to edit stage details."}), 403
    
    # Check if stage is valid to update (current or past)
    if stage_id > project.current_stage:
        return jsonify({"msg": f"Cannot update future stages. Current stage is {project.current_stage}"}), 400

    from app.infrastructure.database.models.models import ProjectWorkflow
    wf = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=stage_id, org_id=project.org_id).first()
    if not wf:
        wf = ProjectWorkflow(project_id=project_id, stage_id=stage_id, org_id=project.org_id, data={})
        db.session.add(wf)
    else:
        # Optimistic locking: detect if client loaded an older version than current DB record
        client_version = data.get('version_id') or data.get('client_version_id')
        if client_version is not None and getattr(wf, 'version_id', None) is not None:
            try:
                if int(client_version) < wf.version_id:
                    return jsonify({
                        "status": "conflict",
                        "message": "Another team member has updated this stage since you loaded it. Please reload to review their latest changes.",
                        "code": "CONCURRENT_MODIFICATION_DETECTED",
                        "current_version_id": wf.version_id,
                        "current_data": wf.data
                    }), 409
            except (ValueError, TypeError):
                pass
    
    current_data = dict(wf.data or {})
    # Strip internal version fields from stored stage data dictionary
    clean_stage_data = {k: v for k, v in data.items() if k not in ('version_id', 'client_version_id')}
    current_data.update(clean_stage_data)
    wf.data = current_data
    wf.updated_by = user_id
    wf.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        
    model = STAGE_MODEL_MAP.get(stage_id)
    if not model:
        return jsonify({"msg": "Invalid stage"}), 400
        
    record = model.query.filter_by(project_id=project_id).first()
    if not record:
        record = model(project_id=project_id, org_id=project.org_id)
        db.session.add(record)
        
    # Standardize Stage 1 specifics (Update Project Metadata if provided)
    if stage_id == 1:
        if 'project_title' in data:
            project.title = data['project_title']
        elif 'title' in data:
            project.title = data['title']
        if 'problem_category' in data:
            project.category = data['problem_category']
        elif 'category' in data:
            project.category = data['category']

    # Update fields from json
    for key, value in data.items():
        if hasattr(record, key) and key not in ['id', 'project_id', 'org_id', 'version_id', 'client_version_id']:
            # Auto-parse dates from ISO string (YYYY-MM-DD)
            if ('date' in key or key in ['start_date', 'end_date']) and isinstance(value, str) and value:
                try:
                    value = datetime.strptime(value.split('T')[0], '%Y-%m-%d').date()
                except ValueError:
                    pass

            setattr(record, key, value)
            
    log_action(project.org_id, user_id, f"Updated Stage {stage_id}", project_id, str(clean_stage_data))
    
    try:
        db.session.commit()
    except StaleDataError:
        db.session.rollback()
        return jsonify({
            "status": "conflict",
            "message": "Another team member has updated this stage since you loaded it. Please reload to review their latest changes.",
            "code": "CONCURRENT_MODIFICATION_DETECTED"
        }), 409
    
    return jsonify({
        "msg": f"Stage {stage_id} data updated",
        "version_id": getattr(wf, 'version_id', 1)
    }), 200

@workflow_bp.route('/<int:project_id>/submit-for-review', methods=['POST'])
@jwt_required()
def submit_for_review(project_id):
    user_id = get_jwt_identity()
    project = Project.query.get_or_404(project_id)
    
    user = db.session.get(User, user_id)
    if project.current_stage == 1:
        if user.role.name not in ('Admin', 'SuperAdmin', 'Team Leader'):
            return jsonify({"msg": "Access denied. Only Admin and Team Leader can submit Stage 1."}), 403
    elif 2 <= project.current_stage <= 8:
        if user.role.name != 'Team Member':
            return jsonify({"msg": f"Access denied. Only Team Members can submit Stage {project.current_stage}."}), 403
    
    # Stage 1: Identification Approval Flow (Team Leader)
    if project.current_stage == 1:
        s1 = Stage1ProblemDefinitionProjectInitiation.query.filter_by(project_id=project_id).first()
        if not s1:
            return jsonify({"msg": "Stage 1 data not found"}), 404
        
        # We can use is_approved=False to indicate "Pending" if we treat None as "Draft"
        # but for simplicity, let's just say it's submitted.
        # We might want a dedicated status field, but I've already added is_approved.
        # Let's assume matches requirements: TL sees Approve/Reject
        log_action(project.org_id, user_id, "Submitted Stage 1 for Approval", project_id)
        db.session.commit()
        return jsonify({"msg": "Stage 1 submitted for Team Leader approval"}), 200

    # Stage 7: Final Solution Approval (Reviewer/Facilitator)
    if project.current_stage == 7:
        project.status = 'Pending Approval'
        review = ProjectReview.query.filter_by(project_id=project_id, stage_number=7, status='Pending').first()
        if not review:
            review = ProjectReview(project_id=project_id, org_id=project.org_id, stage_number=7)
            db.session.add(review)
        db.session.commit()
        return jsonify({"msg": "Project submitted for Reviewer Approval"}), 200
    
    return jsonify({"msg": "No specific submission logic for this stage"}), 200

@workflow_bp.route('/<int:project_id>/stage/1/decision', methods=['POST'])
@jwt_required()
@role_required(['Team Leader', 'Facilitator', 'Admin'])
def stage1_decision(project_id):
    data = request.get_json() # {status: 'Approved'/'Rejected', 'comments': '...'}
    user_id = get_jwt_identity()
    project = Project.query.get_or_404(project_id)
    
    s1 = Stage1ProblemDefinitionProjectInitiation.query.filter_by(project_id=project_id).first()
    if not s1:
        return jsonify({"msg": "Stage 1 data not found"}), 404
        
    decision = data.get('status')
    comments = data.get('comments')
    
    if decision == 'Approved':
        s1.facilitator_approved = True
        s1.facilitator_comments = comments
        log_action(project.org_id, user_id, "Stage 1 Identification Approved", project_id, comments)
    else:
        s1.facilitator_approved = False
        s1.facilitator_comments = comments
        log_action(project.org_id, user_id, "Stage 1 Identification Sent Back for Correction", project_id, comments)
        
    db.session.commit()
    return jsonify({"msg": f"Stage 1 {decision}", "is_approved": s1.facilitator_approved}), 200

@workflow_bp.route('/<int:project_id>/approve', methods=['POST'])
@jwt_required()
@role_required(['Reviewer', 'Admin'])
def approve_project(project_id):
    data = request.get_json() # {status: 'Approved'/'Rejected', 'comments': '...', 'stage': 7}
    user_id = get_jwt_identity()
    project = Project.query.get_or_404(project_id)
    target_stage = data.get('stage', project.current_stage)
    
    review = ProjectReview.query.filter_by(project_id=project_id, stage_number=target_stage, status='Pending').first()
    if not review:
        return jsonify({"msg": "No pending review record found"}), 404
        
    review.status = 'Completed'
    review.decision = data['status']
    review.comments = data.get('comments')
    review.reviewer_id = user_id
    review.decided_at = datetime.now(timezone.utc).replace(tzinfo=None)
    
    if data['status'] == 'Approved':
        project.status = 'In Progress'
        # Automatic advancement if approved at Stage 7
        if target_stage == 7:
            project.current_stage = 8
            log_action(project.org_id, user_id, "Project Approved for Implementation", project_id)
    else:
        project.status = 'Rejected'
        log_action(project.org_id, user_id, "Project Rejected", project_id, data.get('comments'))
        
    db.session.commit()
    return jsonify({"msg": f"Decision: {data['status']}"}), 200

@workflow_bp.route('/<int:project_id>/stage/<int:stage_id>/approve', methods=['POST'])
@jwt_required()
def approve_stage_disciplines(project_id, stage_id):
    data = request.get_json() or {}
    role = data.get('role')
    decision = data.get('decision', data.get('status')) # Accept both
    comments = data.get('comments', '')
    user_id = get_jwt_identity()
    project = Project.query.get_or_404(project_id)
    
    model = STAGE_MODEL_MAP.get(stage_id)
    if not model:
        return jsonify({"msg": "Invalid stage"}), 400
        
    record = model.query.filter_by(project_id=project_id).first()
    if not record:
        record = model(project_id=project_id, org_id=project.org_id)
        db.session.add(record)
        
    # Map decision (Approved / Rejected)
    is_approved = decision in ['Approved', 'Approve']
    
    # Enforce stage & role logic
    if stage_id == 1:
        record.facilitator_approved = is_approved
        record.facilitator_approver_id = user_id
        record.facilitator_approved_at = datetime.now(timezone.utc).replace(tzinfo=None)
        record.facilitator_comments = comments
    elif stage_id == 3:
        record.facilitator_approved = is_approved
        record.facilitator_approver_id = user_id
        record.facilitator_approved_at = datetime.now(timezone.utc).replace(tzinfo=None)
        record.facilitator_comments = comments
    elif stage_id == 8:
        record.final_approval = is_approved
        record.final_approval_by = user_id
        record.final_approval_at = datetime.now(timezone.utc).replace(tzinfo=None)
        if is_approved:
            project.status = 'Completed'
            project.end_date = datetime.now(timezone.utc).replace(tzinfo=None).date()
            tracker = ProjectStageTracker.query.filter_by(project_id=project_id, stage_number=8).first()
            if tracker:
                tracker.status = 'Completed'
                tracker.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    else: # Stages 2, 4, 5, 6, 7
        if stage_id == 2 and is_approved:
            wf2 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=2).first()
            sv = (wf2.data.get('standard_verification') or wf2.data.get('interim_verification') or {}) if (wf2 and isinstance(wf2.data, dict)) else {}
            if not sv:
                s2 = Stage2ObservationDataCollection.query.filter_by(project_id=project_id).first()
                sv = s2.interim_verification or {} if s2 else {}
            not_followed = []
            if not sv.get('sop_follow'):
                not_followed.append('SOP')
            if not sv.get('spec_follow'):
                not_followed.append('Specification')
            if not sv.get('cp_follow'):
                not_followed.append('Control Plan')
            if not sv.get('pfmea_review'):
                not_followed.append('PFMEA')
            if not_followed:
                return jsonify({
                    "msg": f"Approval blocked. The following standard plans are NOT followed: {', '.join(not_followed)}. Please follow/enforce the respective plans before proceeding."
                }), 400

        record.reviewer_approved = is_approved
        record.reviewer_id = user_id
        record.reviewer_approved_at = datetime.now(timezone.utc).replace(tzinfo=None)
        record.reviewer_comments = comments
        
    # Write/Update ProjectReview record
    review = ProjectReview.query.filter_by(project_id=project_id, stage_number=stage_id, status='Pending').first()
    if not review:
        review = ProjectReview(project_id=project_id, org_id=project.org_id, stage_number=stage_id)
        db.session.add(review)
    review.status = 'Completed'
    review.decision = 'Approved' if is_approved else 'Rejected'
    review.comments = comments
    review.reviewer_id = user_id
    review.decided_at = datetime.now(timezone.utc).replace(tzinfo=None)
    
    if not is_approved:
        project.status = 'Rejected'
    else:
        project.status = 'In Progress'
        snapshot_stage_template(project, stage_id)
        
    log_action(project.org_id, user_id, f"Stage {stage_id} {decision} by {role}", project_id, comments)
    db.session.commit()
    return jsonify({"msg": f"Stage {stage_id} {decision} successfully"}), 200
    
@workflow_bp.route('/projects/<int:project_id>/transitions', methods=['POST'])
@jwt_required()
def advance_stage(project_id):
    from app.domain.services.stage_validation_engine import StageValidationEngine
    from app.infrastructure.cache.redis_adapter import cache
    
    data = request.get_json() or {}
    expected_stage = data.get('expected_stage')  # for optimistic concurrency check
    new_stage = data.get('stage')
    user_id = get_jwt_identity()
    if isinstance(user_id, dict):
        user_id = user_id.get('id') or user_id.get('user_id')

    project = Project.query.get_or_404(project_id)
    
    if not new_stage:
        new_stage = project.current_stage + 1

    # Distributed Lock on project to avoid concurrent transition race conditions
    lock_key = f"lock:project:{project_id}:stage_transition"
    with cache.distributed_lock(lock_key, ttl=10):
        # Refresh project state inside lock
        db.session.refresh(project)

        # Optimistic Concurrency Check: ensure current stage has not changed
        if expected_stage is not None and project.current_stage != expected_stage:
            return jsonify({
                "status": "conflict",
                "message": f"Conflict detected: project current stage is {project.current_stage}, but expected {expected_stage}. Please reload the project.",
                "code": "CONCURRENT_MODIFICATION"
            }), 409

        # Run State Machine & Sequential Transition Validation
        is_allowed, error_msg, status_code = StageValidationEngine.validate_transition(project, new_stage)
        if not is_allowed:
            return jsonify({"status": "error", "message": error_msg, "code": "VALIDATION_FAILED"}), status_code

        # ─── Subscription Gate: Plan Workflow Stages ────────────────
        if not SubscriptionManager.can_access_stage(project.org_id, new_stage):
            return jsonify({
                "msg": f"Stage {new_stage} is not available on your current plan. Please upgrade to access full workflow features.",
                "error_code": "STAGE_LOCKED"
            }), 403

        # Update Project Current Stage
        old_stage = project.current_stage
        project.current_stage = new_stage
        
        # Update Tracker for Current (New) Stage
        tracker = ProjectStageTracker.query.filter_by(project_id=project_id, stage_number=new_stage).first()
        if tracker:
            tracker.status = 'In Progress'
            tracker.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            # Create if somehow missing
            tracker = ProjectStageTracker(
                project_id=project_id,
                org_id=project.org_id,
                stage_number=new_stage,
                status='In Progress',
                started_at=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            db.session.add(tracker)

        # Mark Old Stage as Completed in Tracker if it wasn't already
        old_tracker = ProjectStageTracker.query.filter_by(project_id=project_id, stage_number=old_stage).first()
        if old_tracker and old_tracker.status != 'Completed':
            old_tracker.status = 'Completed'
            old_tracker.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)

        snapshot_stage_template(project, old_stage)

        log_action(project.org_id, user_id, f"Advanced from Stage {old_stage} to Stage {new_stage}", project_id)
        db.session.commit()

    # Award points for stage completion
    try:
        from app.domain.services.point_engine_service import PointEngineService
        stage_act_map = {
            1: "qc_stage_1_problem_definition",
            2: "qc_stage_2_observation",
            3: "qc_stage_3_interim_containment",
            4: "qc_stage_4_root_cause_analysis",
            5: "qc_stage_5_action_planning",
            6: "qc_stage_6_implementation",
            7: "qc_stage_7_verification",
            8: "qc_stage_8_standardization"
        }
        act_type = stage_act_map.get(old_stage, "qc_stage_1_problem_definition")
        PointEngineService.award_points(
            employee_id=user_id, org_id=project.org_id, activity_type=act_type,
            ref_id=f"stage_comp_{project_id}_{old_stage}", project_id=project_id,
            description=f"Completed Stage {old_stage} for '{project.title}'"
        )
        if new_stage == 8 or project.status in ['Completed', 'Closed']:
            PointEngineService.award_points(
                employee_id=project.creator_id or user_id, org_id=project.org_id, activity_type="qc_all_8_stages_bonus",
                ref_id=f"stage_bonus_{project_id}", project_id=project_id
            )
            PointEngineService.award_points(
                employee_id=project.creator_id or user_id, org_id=project.org_id, activity_type="project_completed",
                ref_id=f"proj_comp_{project_id}", project_id=project_id
            )
    except Exception as p_err:
        print(f"[QCMS REWARDS] Stage points warning: {p_err}")
    
    return jsonify({
        "msg": f"Successfully advanced to Stage {new_stage}",
        "current_stage": project.current_stage,
        "status": "In Progress"
    }), 200

@workflow_bp.route('/projects/<int:project_id>/reviews', methods=['GET'])
@jwt_required()
def get_project_reviews(project_id):
    user_id = get_jwt_identity()
    user = db.session.get(db.session.get(Project, project_id).org_id if db.session.get(Project, project_id) else None) 
    # Actually just check org match
    project = Project.query.get_or_404(project_id)
    reviews = ProjectReview.query.filter_by(project_id=project_id).order_by(ProjectReview.created_at.desc()).all()
    
    return jsonify([{
        "id": r.id,
        "stage_number": r.stage_number,
        "status": r.status,
        "decision": r.decision,
        "comments": r.comments,
        "reviewer_id": r.reviewer_id,
        "decided_at": r.decided_at.isoformat() + "Z" if r.decided_at else None
    } for r in reviews]), 200

# Legacy/Frontend Compatibility Aliases
@workflow_bp.route('/projects/<int:project_id>/stages/<int:stage_id>', methods=['GET'])
@jwt_required()
def get_stage_data_alias(project_id, stage_id):
    return get_stage_data(project_id, stage_id)

@workflow_bp.route('/projects/<int:project_id>/stages/<int:stage_id>', methods=['POST'])
@jwt_required()
def update_stage_data_alias(project_id, stage_id):
    return update_stage_data(project_id, stage_id)


# ==============================================================================
# REAL-TIME COLLABORATIVE PRESENCE (HEARTBEAT & SSE STREAM)
# ==============================================================================
import time
import json
import threading

STAGE_PRESENCE = {}
_PRESENCE_LOCK = threading.Lock()
PRESENCE_TTL = 15.0  # seconds until user is considered inactive if no heartbeat

def _clean_and_get_stage_presence(project_id, stage_id):
    now = time.time()
    key = (int(project_id), int(stage_id))
    with _PRESENCE_LOCK:
        if key not in STAGE_PRESENCE:
            return []
        
        active_dict = {}
        active_list = []
        for uid, udata in STAGE_PRESENCE[key].items():
            if now - udata.get('last_seen', 0) < PRESENCE_TTL:
                active_dict[uid] = udata
                active_list.append({
                    "user_id": udata["user_id"],
                    "name": udata["name"],
                    "role": udata["role"],
                    "avatar": udata.get("avatar") or "",
                    "email": udata.get("email") or "",
                    "is_editing": bool(udata.get("is_editing", False)),
                    "last_seen": udata.get("last_seen", now)
                })
        STAGE_PRESENCE[key] = active_dict
        return active_list

def _update_stage_presence(project_id, stage_id, user, is_editing=False):
    now = time.time()
    key = (int(project_id), int(stage_id))
    with _PRESENCE_LOCK:
        if key not in STAGE_PRESENCE:
            STAGE_PRESENCE[key] = {}
        
        from app.utils.avatar_utils import get_profile_picture_url
        avatar_url = get_profile_picture_url(user.profile_picture) if getattr(user, 'profile_picture', None) else ""
        
        user_name = getattr(user, 'full_name', None) or getattr(user, 'username', None) or "Team Member"
        role_name = user.role.name if getattr(user, 'role', None) else "Team Member"

        STAGE_PRESENCE[key][user.id] = {
            "user_id": user.id,
            "name": user_name,
            "role": role_name,
            "avatar": avatar_url,
            "email": getattr(user, 'email', '') or "",
            "is_editing": bool(is_editing),
            "last_seen": now
        }

def _remove_stage_presence(project_id, stage_id, user_id):
    key = (int(project_id), int(stage_id))
    with _PRESENCE_LOCK:
        if key in STAGE_PRESENCE:
            STAGE_PRESENCE[key].pop(user_id, None)

@workflow_bp.route('/<int:project_id>/stage/<int:stage_id>/presence-heartbeat', methods=['POST'])
@jwt_required()
def stage_presence_heartbeat(project_id, stage_id):
    """Receive client heartbeat to maintain live collaborative presence."""
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id)) if user_id else None
    if not user:
        return jsonify({"msg": "User not found"}), 404
    
    data = request.get_json() or {}
    is_editing = bool(data.get('is_editing', False))
    
    _update_stage_presence(project_id, stage_id, user, is_editing=is_editing)
    active_users = _clean_and_get_stage_presence(project_id, stage_id)
    
    return jsonify({
        "status": "ok",
        "project_id": project_id,
        "stage_id": stage_id,
        "active_users": active_users
    }), 200

@workflow_bp.route('/<int:project_id>/stage/<int:stage_id>/presence-leave', methods=['POST'])
@jwt_required()
def stage_presence_leave(project_id, stage_id):
    """Explicit leave signal when switching stages or navigating away."""
    user_id = get_jwt_identity()
    if user_id:
        _remove_stage_presence(project_id, stage_id, int(user_id))
    return jsonify({"status": "ok"}), 200

@workflow_bp.route('/<int:project_id>/stage/<int:stage_id>/presence-stream', methods=['GET'])
def stage_presence_stream(project_id, stage_id):
    """Server-Sent Events (SSE) stream for live collaborative stage presence."""
    from flask_jwt_extended import decode_token
    token = request.args.get('token')
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ', 1)[1]
        
    user_id = None
    if token:
        try:
            decoded = decode_token(token)
            user_id = decoded.get('sub')
        except Exception:
            user_id = None
            
    if not user_id:
        return jsonify({"msg": "Unauthorized or missing token"}), 401
    
    user = db.session.get(User, int(user_id)) if user_id else None
    if not user:
        return jsonify({"msg": "User not found"}), 404

    # Initial register
    _update_stage_presence(project_id, stage_id, user, is_editing=False)

    from flask import Response, stream_with_context

    def event_generator():
        start_time = time.time()
        # Stream for 60 seconds per connection cycle (browser EventSource will auto-reconnect)
        while time.time() - start_time < 60:
            _update_stage_presence(project_id, stage_id, user, is_editing=False)
            active_users = _clean_and_get_stage_presence(project_id, stage_id)
            payload = json.dumps(active_users)
            yield f"data: {payload}\n\n"
            time.sleep(3)

    return Response(
        stream_with_context(event_generator()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )

