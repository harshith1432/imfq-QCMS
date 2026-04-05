from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, Project, ProjectReview, Stage1Identification, Stage5RootCause, Stage7Development, Department, db
from functools import wraps
from datetime import datetime

reviewer_bp = Blueprint('reviewer', __name__)

def reviewer_required(f):
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.role.name != 'Reviewer':
            return jsonify({"msg": "Reviewer access required"}), 403
        return f(*args, **kwargs)
    return decorated_function

# --- Dashboard Stats ---
@reviewer_bp.route('/stats', methods=['GET'])
@reviewer_required
def get_stats():
    user = User.query.get(get_jwt_identity())
    
    pending_count = Project.query.filter_by(org_id=user.org_id, current_stage=7).count()
    
    from app.models import ProjectReview
    approvals = ProjectReview.query.filter_by(org_id=user.org_id).all()
    approved_count = len([a for a in approvals if a.decision == 'Approved'])
    rejected_count = len([a for a in approvals if a.decision == 'Rejected'])
    
    # Avg Turnaround Time
    completed_approvals = [a for a in approvals if a.decided_at and a.created_at]
    avg_turnaround = "0h"
    if completed_approvals:
        total_seconds = sum([(a.decided_at - a.created_at).total_seconds() for a in completed_approvals])
        avg_seconds = total_seconds / len(completed_approvals)
        avg_turnaround = f"{round(avg_seconds / 3600, 1)}h"
    
    return jsonify({
        "pending_count": pending_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "avg_turnaround_time": avg_turnaround
    })

# --- Pending Approvals ---
@reviewer_bp.route('/pending', methods=['GET'])
@reviewer_required
def get_pending_approvals():
    user = User.query.get(get_jwt_identity())
    
    pending_projects = Project.query.filter_by(
        org_id=user.org_id,
        current_stage=7
    ).all()
    
    result = []
    for p in pending_projects:
        from app.models import Stage1Identification, Stage5RootCause, Stage7Development
        s1 = Stage1Identification.query.filter_by(project_id=p.id).first()
        s5 = Stage5RootCause.query.filter_by(project_id=p.id).first()
        s7 = Stage7Development.query.filter_by(project_id=p.id).first()
        dept = Department.query.get(p.department_id)
        tl = User.query.get(p.creator_id) if p.creator_id else None
        
        result.append({
            "project_id": p.id,
            "project_uid": p.project_uid,
            "title": p.title,
            "department": dept.name if dept else "N/A",
            "problem_statement": s1.problem_statement if s1 else "N/A",
            "root_cause_summary": s5.root_cause_summary if s5 else "N/A",
            "solution": s7.solution_details if s7 else "N/A",
            "estimated_cost": s7.estimated_cost if s7 else 0,
            "target_kpi": s7.action_plan if s7 else {},
            "submitted_at": s7.created_at.isoformat() + "Z" if s7 and s7.created_at else p.created_at.isoformat() + "Z",
            "team_leader": tl.full_name or tl.username if tl else "Unassigned",
            "team_leader_pic": tl.profile_picture if tl else None
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
    
    if not comments:
        return jsonify({"msg": "Comments are required"}), 400
        
    if decision not in ['Approved', 'Rejected', 'Revision']:
        return jsonify({"msg": "Invalid decision"}), 400
        
    project = Project.query.filter_by(id=project_id, org_id=user.org_id).first_or_404()
    
    if project.current_stage != 7:
        return jsonify({"msg": "Project is not in Stage 7"}), 400
        
    from app.models import ProjectReview
    approval = ProjectReview.query.filter_by(project_id=project_id, stage_number=7).first()
    if not approval:
        approval = ProjectReview(
            project_id=project_id,
            org_id=user.org_id,
            stage_number=7,
            reviewer_id=user.id
        )
        db.session.add(approval)
        
    approval.decision = decision
    approval.comments = comments
    approval.decided_at = datetime.utcnow()
    approval.status = 'Completed' if decision == 'Approved' else 'Action Required'
    
    if decision == 'Approved':
        project.current_stage = 8
        project.status = 'Approved'
    else:
        # Rejected or Revision -> back to Stage 7 for the team to fix
        project.current_stage = 7
        project.status = 'Revision Required' if decision == 'Revision' else 'Rejected'
        
    # Log action
    from app.routes.workflow_routes import log_action
    log_action(user.org_id, user.id, f"Reviewer Decision: {decision}", project_id, comments)
    
    db.session.commit()
    
    return jsonify({
        "msg": f"Decision '{decision}' processed successfully",
        "project_id": project_id,
        "new_stage": project.current_stage
    })

# --- History ---
@reviewer_bp.route('/history', methods=['GET'])
@reviewer_required
def get_history():
    user = User.query.get(get_jwt_identity())
    from app.models import ProjectReview
    history = ProjectReview.query.filter_by(org_id=user.org_id).order_by(ProjectReview.decided_at.desc()).limit(10).all()
    
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
    # This matches the existing dashboard-reviewer.html JS call
    data = request.json
    data['project_id'] = project_id
    # We need to hack the request object or just call the function manually
    # For now, let's just duplicate minimal logic or redirect
    user = User.query.get(get_jwt_identity())
    decision = data.get('decision')
    comments = data.get('comments')
    
    if not comments:
        return jsonify({"msg": "Comments are required"}), 400
        
    project = Project.query.filter_by(id=project_id, org_id=user.org_id).first_or_404()
    approval = ProjectReview.query.filter_by(project_id=project_id, stage_number=7).first()
    if not approval:
        approval = ProjectReview(project_id=project_id, org_id=user.org_id, stage_number=7, reviewer_id=user.id)
        db.session.add(approval)
    
    approval.decision = decision
    approval.comments = comments
    approval.decided_at = datetime.utcnow()
    
    if decision == 'Approved':
        project.current_stage = 8
        project.status = 'Approved'
    else:
        project.current_stage = 7
        project.status = 'Revision Required' if decision == 'Revision' else 'Rejected'
    
    db.session.commit()
    return jsonify({"msg": "Decision processed"})
