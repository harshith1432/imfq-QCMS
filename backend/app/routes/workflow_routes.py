from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import (
    Project, db, AuditLog, ProjectReview, ProjectStageTracker,
    Stage1Identification, Stage2Selection, Stage3Analysis, 
    Stage4Causes, Stage5RootCause, Stage6DataAnalysis, 
    Stage7Development, Stage8Implementation
)
from ..middleware import role_required
from datetime import datetime

workflow_bp = Blueprint('workflow', __name__)

# Helper to map stage IDs to models
STAGE_MODEL_MAP = {
    1: Stage1Identification,
    2: Stage2Selection,
    3: Stage3Analysis,
    4: Stage4Causes,
    5: Stage5RootCause,
    6: Stage6DataAnalysis,
    7: Stage7Development,
    8: Stage8Implementation
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

@workflow_bp.route('/<int:project_id>/stage/<int:stage_id>', methods=['GET'])
@jwt_required()
def get_stage_data(project_id, stage_id):
    model = STAGE_MODEL_MAP.get(stage_id)
    if not model:
        return jsonify({"msg": "Invalid stage"}), 400
        
    data = model.query.filter_by(project_id=project_id).first()
    if not data:
        return jsonify({"data": {}}), 200
        
    # Convert model to dict (excluding internal SQLAlchemy fields)
    result = {c.name: getattr(data, c.name) for c in data.__table__.columns}
    return jsonify({"data": result}), 200

@workflow_bp.route('/<int:project_id>/stage/<int:stage_id>', methods=['POST'])
@jwt_required()
def update_stage_data(project_id, stage_id):
    data = request.get_json()
    user_id = get_jwt_identity()
    project = Project.query.get_or_404(project_id)
    
    # Check if stage is valid to update (current or past)
    if stage_id > project.current_stage:
        return jsonify({"msg": f"Cannot update future stages. Current stage is {project.current_stage}"}), 400
        
    model = STAGE_MODEL_MAP.get(stage_id)
    if not model:
        return jsonify({"msg": "Invalid stage"}), 400
        
    record = model.query.filter_by(project_id=project_id).first()
    if not record:
        record = model(project_id=project_id, org_id=project.org_id)
        db.session.add(record)
        
    # Standardize Stage 1 specifics (Update Project Metadata if provided)
    if stage_id == 1:
        if 'title' in data:
            project.title = data['title']
        if 'category' in data:
            project.category = data['category']
        if 'department' in data:
            project.department = data['department']

    # Update fields from json
    for key, value in data.items():
        if hasattr(record, key) and key not in ['id', 'project_id', 'org_id']:
            # Auto-parse dates from ISO string (YYYY-MM-DD)
            if key in ['start_date', 'end_date'] and isinstance(value, str) and value:
                try:
                    value = datetime.strptime(value.split('T')[0], '%Y-%m-%d').date()
                except ValueError:
                    pass # Keep as string if parsing fails, allow SQLAlchemy to handle or error

            setattr(record, key, value)
            
    log_action(project.org_id, user_id, f"Updated Stage {stage_id}", project_id, str(data))
    db.session.commit()
    
    return jsonify({"msg": f"Stage {stage_id} data updated"}), 200

@workflow_bp.route('/<int:project_id>/submit-for-review', methods=['POST'])
@jwt_required()
def submit_for_review(project_id):
    user_id = get_jwt_identity()
    project = Project.query.get_or_404(project_id)
    
    # Stage 1: Identification Approval Flow (Team Leader)
    if project.current_stage == 1:
        s1 = Stage1Identification.query.filter_by(project_id=project_id).first()
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
    
    s1 = Stage1Identification.query.filter_by(project_id=project_id).first()
    if not s1:
        return jsonify({"msg": "Stage 1 data not found"}), 404
        
    decision = data.get('status')
    comments = data.get('comments')
    
    if decision == 'Approved':
        s1.is_approved = True
        s1.tl_comments = comments
        log_action(project.org_id, user_id, "Stage 1 Identification Approved", project_id, comments)
    else:
        s1.is_approved = False
        s1.tl_comments = comments
        log_action(project.org_id, user_id, "Stage 1 Identification Sent Back for Correction", project_id, comments)
        
    db.session.commit()
    return jsonify({"msg": f"Stage 1 {decision}", "is_approved": s1.is_approved}), 200

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
    review.decided_at = datetime.utcnow()
    
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
    
@workflow_bp.route('/projects/<int:project_id>/transitions', methods=['POST'])
@jwt_required()
def advance_stage(project_id):
    data = request.get_json()
    new_stage = data.get('stage')
    user_id = get_jwt_identity()
    project = Project.query.get_or_404(project_id)
    
    if not new_stage:
        new_stage = project.current_stage + 1
        
    if new_stage > 8:
        return jsonify({"msg": "Project has reached the final workflow stage (Stage 8). Final administrative closure must be performed by a Facilitator."}), 400

    # ─── Workflow Gate: Stage 1 → 2 ─────────────────────────────
    # Requires Team Leader Approval
    if new_stage == 2:
        s1 = Stage1Identification.query.filter_by(project_id=project_id).first()
        if not s1 or not s1.is_approved:
            return jsonify({
                "msg": "Stage 1 Identification must be approved by a Team Leader before advancing to Selection."
            }), 403

    # ─── Workflow Gate: Stage 2 → 3 ─────────────────────────────
    # Requires Facilitator Validation
    if new_stage == 3:
        s2 = Stage2Selection.query.filter_by(project_id=project_id).first()
        if not s2 or not s2.facilitator_validation:
            return jsonify({
                "msg": "Stage 2 Selection must be validated by a Facilitator before advancing to Analysis."
            }), 403

    # ─── Workflow Gate: Stage 5 → 6 ─────────────────────────────
    # Requires Facilitator RCA Validation
    if new_stage == 6:
        s5 = Stage5RootCause.query.filter_by(project_id=project_id).first()
        if not s5 or not s5.facilitator_validation:
            return jsonify({
                "msg": "Root Cause Analysis (Stage 5) must be validated by a Facilitator before Data Analysis."
            }), 403

    # ─── Workflow Gate: Stage 7 → 8 ─────────────────────────────
    # Requires Reviewer Approval
    if new_stage == 8:
        review = ProjectReview.query.filter_by(project_id=project_id, stage_number=7, decision='Approved').first()
        if not review:
            return jsonify({
                "msg": "Stage 7 Solution must be formally approved by a Reviewing Officer before Implementation (Stage 8)."
            }), 403

    # Update Project Current Stage
    old_stage = project.current_stage
    project.current_stage = new_stage
    
    # Update Tracker for Current (New) Stage
    tracker = ProjectStageTracker.query.filter_by(project_id=project_id, stage_number=new_stage).first()
    if tracker:
        tracker.status = 'In Progress'
        tracker.started_at = datetime.utcnow()
    else:
        # Create if somehow missing
        tracker = ProjectStageTracker(
            project_id=project_id,
            org_id=project.org_id,
            stage_number=new_stage,
            status='In Progress',
            started_at=datetime.utcnow()
        )
        db.session.add(tracker)

    # Mark Old Stage as Completed in Tracker if it wasn't already
    old_tracker = ProjectStageTracker.query.filter_by(project_id=project_id, stage_number=old_stage).first()
    if old_tracker and old_tracker.status != 'Completed':
        old_tracker.status = 'Completed'
        old_tracker.completed_at = datetime.utcnow()

    log_action(project.org_id, user_id, f"Advanced from Stage {old_stage} to Stage {new_stage}", project_id)
    db.session.commit()
    
    return jsonify({
        "msg": f"Successfully advanced to Stage {new_stage}",
        "current_stage": project.current_stage,
        "status": "In Progress"
    }), 200

@workflow_bp.route('/projects/<int:project_id>/reviews', methods=['GET'])
@jwt_required()
def get_project_reviews(project_id):
    user_id = get_jwt_identity()
    user = db.session.get(Project.query.get(project_id).org_id if Project.query.get(project_id) else None) 
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
