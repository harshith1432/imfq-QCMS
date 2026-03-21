from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import (
    Project, db, AuditLog,
    Stage1Problem, Stage2Data, Stage3RCA, 
    Stage4Solution, Stage5Approval, Stage6Implementation, 
    Stage7Impact, Stage8Standardization
)
from ..middleware import role_required
from datetime import datetime

workflow_bp = Blueprint('workflow', __name__)

# Helper to map stage IDs to models
STAGE_MODEL_MAP = {
    1: Stage1Problem,
    2: Stage2Data,
    3: Stage3RCA,
    4: Stage4Solution,
    5: Stage5Approval,
    6: Stage6Implementation,
    7: Stage7Impact,
    8: Stage8Standardization
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

@workflow_bp.route('/<int:project_id>/submit', methods=['POST'])
@jwt_required()
def submit_for_approval(project_id):
    user_id = get_jwt_identity()
    project = Project.query.get_or_404(project_id)
    
    if project.current_stage != 4:
        return jsonify({"msg": "Only Stage 4 (Solutions) can be submitted for approval"}), 400
        
    project.status = 'Pending Approval'
    project.current_stage = 5  # Move to Stage 5 for Reviewer
    
    # Ensure Stage 5 entry exists
    approval = Stage5Approval.query.filter_by(project_id=project_id).first()
    if not approval:
        approval = Stage5Approval(project_id=project_id, org_id=project.org_id)
        db.session.add(approval)
    
    approval.status = 'Pending'
    log_action(project.org_id, user_id, "Submitted for Review (Stage 5)", project_id)
    db.session.commit()
    
    return jsonify({"msg": "Project submitted to Reviewer (Stage 5)"}), 200

@workflow_bp.route('/<int:project_id>/approve', methods=['POST'])
@jwt_required()
@role_required(['Reviewer', 'Admin'])
def approve_stage(project_id):
    data = request.get_json() # {status: 'Approved'/'Rejected', 'comments': '...'}
    user_id = get_jwt_identity()
    project = Project.query.get_or_404(project_id)
    
    if project.current_stage != 4 or project.status != 'Pending Approval':
        return jsonify({"msg": "Project is not in a submittable state for approval"}), 400
        
    approval = Stage5Approval.query.filter_by(project_id=project_id, status='Pending').first()
    if not approval:
        return jsonify({"msg": "No pending approval record found"}), 404
        
    approval.status = 'Completed'
    approval.decision = data['status'] # 'Approved' or 'Rejected'
    approval.comments = data.get('comments')
    approval.reviewer_id = user_id
    approval.decided_at = datetime.utcnow()
    
    if data['status'] == 'Approved':
        project.status = 'In Progress'
        # In a strict 8-stage, after approval in 5, we jump to 6 for implementation
        project.current_stage = 6 
        log_action(project.org_id, user_id, "Project Approved", project_id)
    else:
        project.status = 'Rejected'
        log_action(project.org_id, user_id, "Project Rejected", project_id, data.get('comments'))
        
    db.session.commit()
    
    return jsonify({"msg": f"Project {data['status'].lower()}"}), 200
    
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

    # ─── Workflow Gate: Stage 3 → 4 ─────────────────────────────
    # Requires Facilitator RCA Validation Note
    if new_stage == 4:
        rca = Stage3RCA.query.filter_by(project_id=project_id).first()
        if not rca or not rca.rca_validation_note:
            return jsonify({
                "msg": "Stage 3 cannot close. A Facilitator must add an RCA Validation Note before the project can advance to Stage 4."
            }), 403

    # ─── Workflow Gate: Stage 6 → 7 ─────────────────────────────
    # Requires Stage 6 Implementation end_date
    if new_stage == 7:
        s6 = Stage6Implementation.query.filter_by(project_id=project_id).first()
        if not s6 or not s6.end_date:
            return jsonify({
                "msg": "Stage 6 (Implementation) end date must be filled before advancing to Stage 7 (Impact Measurement)."
            }), 400

    # ─── Workflow Gate: Stage 7 → 8 ─────────────────────────────
    # Exclusively controlled by Facilitator — stage_7.status must be 'Approved'
    if new_stage == 8:
        s7 = Stage7Impact.query.filter_by(project_id=project_id).first()
        if not s7 or s7.status != 'Approved':
            return jsonify({
                "msg": "Stage 7 results must be approved by a Facilitator before the project can advance to Stage 8."
            }), 403

    # ─── General Gate: Stage 6+ requires Stage 5 Approval ───────
    if new_stage >= 6 and new_stage != 8:  # Stage 8 already gated above
        approval = Stage5Approval.query.filter_by(project_id=project_id).first()
        if not approval or approval.decision != 'Approved':
            return jsonify({
                "msg": "Phase Gate: Transition to Stage 6 (Implementation) requires formal Reviewer Approval (Stage 5)."
            }), 403

    project.current_stage = new_stage
    log_action(project.org_id, user_id, f"Advanced to Stage {new_stage}", project_id)
    db.session.commit()
    
    return jsonify({"msg": f"Advanced to Stage {new_stage}", "current_stage": project.current_stage}), 200

# Legacy/Frontend Compatibility Aliases
@workflow_bp.route('/projects/<int:project_id>/stages/<int:stage_id>', methods=['GET'])
@jwt_required()
def get_stage_data_alias(project_id, stage_id):
    return get_stage_data(project_id, stage_id)

@workflow_bp.route('/projects/<int:project_id>/stages/<int:stage_id>', methods=['POST'])
@jwt_required()
def update_stage_data_alias(project_id, stage_id):
    return update_stage_data(project_id, stage_id)
