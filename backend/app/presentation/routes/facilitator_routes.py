from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from app.infrastructure.database.models.models import (
    User, Project, Department,
    Stage5RootCause, Stage7Development, Stage8Implementation,
    FacilitatorNote, AuditLog, db
)
from functools import wraps

facilitator_bp = Blueprint('facilitator', __name__)


# ─── RBAC Decorator ───────────────────────────────────────────
def facilitator_required(f):
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.role.name not in ('Facilitator', 'Admin', 'SuperAdmin'):
            return jsonify({"msg": "Facilitator or Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function


# ─── Audit Log Helper ─────────────────────────────────────────
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


# ─── 1. Dashboard Stats ───────────────────────────────────────
@facilitator_bp.route('/stats', methods=['GET'])
@facilitator_required
def get_stats():
    user = db.session.get(User, get_jwt_identity())
    org_id = user.org_id

    if user.role.name in ('Admin', 'SuperAdmin'):
        projects = Project.query.filter_by(org_id=org_id).all()
    else:
        # Strictly projects assigned to this particular Facilitator
        projects = Project.query.filter_by(org_id=org_id, facilitator_id=user.id).all()

    completed_statuses = {'Closed', 'Completed', 'Stage 8 Approved'}
    inactive_statuses = {'Inactive', 'On Hold', 'Stalled', 'Archived', 'Cancelled'}
    rejected_statuses = {'Rejected'}

    # Needs Guidance: Assistance requests assigned to this facilitator that are 'Pending'
    from app.infrastructure.database.models.models import FacilitatorAssistanceRequest as FAR
    pending_rca = FAR.query.filter(
        FAR.org_id == org_id,
        FAR.facilitator_id == user.id,
        FAR.status == 'Pending'
    ).count()

    pending_impact = sum(
        1 for p in projects 
        if p.current_stage == 8 and p.status not in completed_statuses and p.status not in rejected_statuses
    )

    # Inactive Projects (assigned to this facilitator):
    # Projects with status in inactive_statuses OR active projects with no AuditLog activity in > 7 days
    stalled_cutoff = datetime.utcnow() - timedelta(days=7)
    inactive_projects_count = 0
    for p in projects:
        if p.status in inactive_statuses:
            inactive_projects_count += 1
        elif p.status not in completed_statuses and p.status not in rejected_statuses and (p.current_stage or 1) < 8:
            last_log = AuditLog.query.filter_by(project_id=p.id).order_by(AuditLog.created_at.desc()).first()
            last_activity = last_log.created_at if last_log else p.created_at
            if last_activity and last_activity < stalled_cutoff:
                inactive_projects_count += 1

    # Total Active Projects: Projects assigned to this facilitator currently active in-progress
    active_projects_count = sum(
        1 for p in projects 
        if p.status not in completed_statuses 
        and p.status not in inactive_statuses 
        and p.status not in rejected_statuses
        and (p.current_stage or 1) < 8
    )

    from app.infrastructure.database.models.models import Stage8Implementation, FacilitatorAssistanceRequest
    impacts_query = Stage8Implementation.query.join(Project).filter(
        Project.org_id == org_id,
        Project.facilitator_id == user.id,
        Stage8Implementation.results_data.isnot(None)
    )
    impacts = impacts_query.all()
    avg_improvement = 0
    if impacts:
        avg_improvement = round(sum([i.kpi_improvement_pct or 0 for i in impacts]) / len(impacts), 1)

    pending_assistance = FacilitatorAssistanceRequest.query.filter(
        FacilitatorAssistanceRequest.org_id == org_id,
        FacilitatorAssistanceRequest.facilitator_id == user.id,
        FacilitatorAssistanceRequest.status == 'Pending'
    ).count()

    return jsonify({
        "pending_rca": pending_rca,
        "pending_impact": pending_impact,
        "pending_assistance": pending_assistance,
        "stalled_projects": inactive_projects_count,
        "avg_improvement": f"{avg_improvement}%",
        "total_savings": 0,
        "total_projects": active_projects_count
    })


# ─── 2. All Projects Pipeline ─────────────────────────────────
@facilitator_bp.route('/projects', methods=['GET'])
@facilitator_required
def get_all_projects():
    user = User.query.get(get_jwt_identity())
    # Show all active projects where this user is the assigned facilitator.
    # Exclude closed and archived projects so only active projects appear.
    query = Project.query.filter(
        Project.org_id == user.org_id,
        Project.facilitator_id == user.id,
        Project.status != 'Closed',
        Project.status != 'Archived'
    )
    projects = query.order_by(Project.created_at.desc()).all()

    result = []
    for p in projects:
        creator = User.query.get(p.creator_id) if p.creator_id else None
        leader = User.query.get(p.team_leader_id) if p.team_leader_id else creator
        dept = Department.query.get(p.department_id) if p.department_id else None
        result.append({
            "id": p.id,
            "uid": p.project_uid,
            "title": p.title,
            "stage": p.current_stage,
            "status": p.status,
            "team_leader": leader.full_name or leader.username if leader else "Unknown",
            "dept": dept.name if dept else (p.plant or "General"),
            "plant": p.plant or "Main Plant",
            "created_at": p.created_at.isoformat() + "Z" if p.created_at else None
        })
    return jsonify(result)

@facilitator_bp.route('/assisted-history', methods=['GET'])
@facilitator_required
def get_assisted_history():
    user = User.query.get(get_jwt_identity())
    from app.infrastructure.database.models.models import FacilitatorAssistanceRequest
    
    # Query all assistance records handled/assisted by this facilitator (where responded or non-pending)
    requests = FacilitatorAssistanceRequest.query.filter(
        FacilitatorAssistanceRequest.org_id == user.org_id,
        FacilitatorAssistanceRequest.facilitator_id == user.id,
        (FacilitatorAssistanceRequest.status != 'Pending') | (FacilitatorAssistanceRequest.response.isnot(None))
    ).order_by(
        FacilitatorAssistanceRequest.updated_at.desc(),
        FacilitatorAssistanceRequest.created_at.desc()
    ).all()

    res = []
    for r in requests:
        req_user = User.query.get(r.user_id) if r.user_id else None
        proj = Project.query.get(r.project_id) if r.project_id else None
        dept = Department.query.get(proj.department_id) if (proj and proj.department_id) else None
        
        res.append({
            "id": r.id,
            "project_id": r.project_id,
            "project_uid": proj.project_uid if proj else "PRJ-???",
            "project_title": proj.title if proj else "Unknown",
            "dept": dept.name if dept else (proj.plant if proj else "General"),
            "stage_id": r.stage_id,
            "requested_by": (req_user.full_name or req_user.username) if req_user else "Unknown User",
            "user_email": req_user.email if req_user else "",
            "message": r.message or "",
            "response": r.response or "",
            "status": r.status or "Responded",
            "project_status": proj.status if proj else "Unknown",
            "created_at": r.created_at.isoformat() + "Z" if r.created_at else None,
            "assisted_at": (r.updated_at or r.created_at).isoformat() + "Z" if (r.updated_at or r.created_at) else None
        })
    return jsonify(res), 200

@facilitator_bp.route('/completed-projects', methods=['GET'])
@facilitator_required
def get_completed_projects():
    user = User.query.get(get_jwt_identity())
    # Show closed projects where this user is the assigned facilitator.
    projects = Project.query.filter(
        Project.org_id == user.org_id,
        Project.facilitator_id == user.id,
        Project.status == 'Closed'
    ).all()

    result = []
    for p in projects:
        creator = User.query.get(p.creator_id)
        dept = Department.query.get(p.department_id)
        result.append({
            "id": p.id,
            "uid": p.project_uid,
            "title": p.title,
            "stage": p.current_stage,
            "status": p.status,
            "team_leader": creator.full_name if creator else "Unknown",
            "dept": dept.name if dept else "Unknown",
            "created_at": p.created_at.isoformat() + "Z"
        })
    return jsonify(result)

# ─── 3. RCA Workspace (Stage 5) ───────────────────────────────
@facilitator_bp.route('/rca-workspace', methods=['GET'])
@facilitator_bp.route('/rca-projects', methods=['GET'])
@facilitator_required
def get_rca_workspace():
    user = User.query.get(get_jwt_identity())
    # Only Stage-5 projects assigned to THIS facilitator
    query = Project.query.filter(
        Project.org_id == user.org_id,
        Project.facilitator_id == user.id,
        Project.current_stage == 5
    )
    projects = query.all()
    result = []
    for p in projects:
        from app.infrastructure.database.models.models import Stage5RootCause
        rca = Stage5RootCause.query.filter_by(project_id=p.id).first()
        dept = Department.query.get(p.department_id)

        qc_tools = {}
        if rca:
            qc_tools = {
                "fishbone": bool(rca.fishbone_data),
                "5_why": bool(rca.why_analysis),
                "pareto": bool(rca.pareto_data),
                "histogram": bool(rca.histogram_data),
                "control_chart": bool(rca.control_chart_data),
                "scatter": bool(rca.scatter_data),
                "checksheet": bool(rca.checksheet_data),
            }

        tools_done = sum(1 for v in qc_tools.values() if v)
        has_summary = bool(rca and rca.root_cause_summary)
        has_validation = bool(rca and rca.rca_validation_note)

        result.append({
            "id": p.id,
            "title": p.title,
            "dept": dept.name if dept else "Unknown",
            "qc_tools": qc_tools,
            "tools_completed": f"{tools_done}/7",
            "has_summary": has_summary,
            "has_validation_note": has_validation,
            "rca_validation_note": rca.rca_validation_note if rca else None,
            "ready_to_advance": has_summary and has_validation
        })
    return jsonify(result)


# ─── 4. Impact Review (Stage 8) ───────────────────────────────
@facilitator_bp.route('/impact-review', methods=['GET'])
@facilitator_bp.route('/impact-projects', methods=['GET'])
@facilitator_required
def get_impact_review():
    user = User.query.get(get_jwt_identity())
    # Only Stage-8 projects assigned to THIS facilitator that have been submitted or further in the flow
    query = Project.query.filter(
        Project.org_id == user.org_id,
        Project.facilitator_id == user.id,
        Project.current_stage == 8,
        Project.status != 'Closed',
        Project.status.in_(['Stage 8 Submitted', 'Stage 8 Reviewer Approved', 'Stage 8 Approved', 'Impact Approved', 'SOP Created', 'Pending Closure'])
    )
    projects = query.all()
    result = []
    for p in projects:
        from app.infrastructure.database.models.models import Stage8Implementation, Stage7Development, SOP
        impact = Stage8Implementation.query.filter_by(project_id=p.id).first()
        s7 = Stage7Development.query.filter_by(project_id=p.id).first()
        sop = SOP.query.filter_by(project_id=p.id).first()
        has_sop = sop is not None
        has_impact = bool(impact and impact.final_data is not None)

        # Auto-calculate KPI improvement %
        kpi_pct = None
        if impact and impact.baseline_data and impact.final_data:
            try:
                baseline_val = float(str(impact.baseline_data.get('value', 0)))
                final_val = float(str(impact.final_data.get('value', 0)))
                if baseline_val > 0:
                    kpi_pct = round(((final_val - baseline_val) / baseline_val) * 100, 2)
                    # Save the computed value back
                    if kpi_pct != impact.kpi_improvement_pct:
                        impact.kpi_improvement_pct = kpi_pct
                        db.session.commit()
            except (ValueError, TypeError, AttributeError):
                pass

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


# ─── 4b. Approve Stage 8 Submission ──────────────────────────
@facilitator_bp.route('/stage8/<int:project_id>/approve-submission', methods=['POST'])
@facilitator_required
def approve_stage8_submission(project_id):
    user = User.query.get(get_jwt_identity())
    project = Project.query.get_or_404(project_id)

    if project.facilitator_id != user.id:
        return jsonify({"msg": "You are not the facilitator assigned to this project."}), 403

    if project.current_stage != 8:
        return jsonify({"msg": f"Project is not in Stage 8 (current stage: {project.current_stage})."}), 400

    if project.status != 'Stage 8 Submitted':
        return jsonify({"msg": f"Project submission not pending approval (current status: '{project.status}')."}), 400

    project.status = 'Stage 8 Approved'
    log_action(user.org_id, user.id, "Approved Stage 8 Submission", project_id)
    db.session.commit()
    return jsonify({"msg": "Stage 8 submission approved. Proceed to Impact Review."}), 200


# ─── 5. Closure Projects (Stage 8) ───────────────────────────
@facilitator_bp.route('/closure-projects', methods=['GET'])
@facilitator_required
def get_closure_projects():
    user = User.query.get(get_jwt_identity())
    # Only Stage-8 closure projects assigned to THIS facilitator
    query = Project.query.filter(
        Project.org_id == user.org_id,
        Project.facilitator_id == user.id,
        Project.current_stage == 8,
        Project.status != 'Closed'
    )
    projects = query.all()
    result = []
    for p in projects:
        std = Stage8Implementation.query.filter_by(project_id=p.id).first()
        from app.infrastructure.database.models.models import SOP
        sop = SOP.query.filter_by(project_id=p.id).first()
        
        # Fallback to Stage 8 workflow JSON data if available
        from app.infrastructure.database.models.models import ProjectWorkflow
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


# ─── 6. Facilitator Notes (Read) ──────────────────────────────
@facilitator_bp.route('/notes/<int:project_id>', methods=['GET'])
@facilitator_required
def get_notes(project_id):
    notes = FacilitatorNote.query.filter_by(project_id=project_id).order_by(FacilitatorNote.created_at.desc()).all()
    return jsonify([{
        "id": n.id,
        "stage_number": n.stage_number,
        "note_text": n.note_text,
        "created_by": User.query.get(n.created_by).full_name if User.query.get(n.created_by) else "Unknown",
        "created_at": n.created_at.isoformat() + "Z"
    } for n in notes])


# ─── 7. Facilitator Notes (Add) ───────────────────────────────
@facilitator_bp.route('/notes', methods=['POST'])
@facilitator_required
def add_note():
    user = User.query.get(get_jwt_identity())
    data = request.get_json()

    project_id = data.get('project_id')
    stage_number = data.get('stage_number')
    note_text = data.get('note_text', '').strip()

    if not all([project_id, stage_number, note_text]):
        return jsonify({"msg": "project_id, stage_number, and note_text are required"}), 400

    project = Project.query.get_or_404(project_id)

    note = FacilitatorNote(
        org_id=user.org_id,
        project_id=project_id,
        stage_number=stage_number,
        note_text=note_text,
        created_by=user.id
    )
    db.session.add(note)
    log_action(user.org_id, user.id, f"Added Facilitator Note to Stage {stage_number}", project_id, note_text)
    db.session.commit()
    return jsonify({"msg": "Note added"}), 201


# ─── 8. RCA Validation (Stage 5 Gate) ────────────────────────
@facilitator_bp.route('/rca/<int:project_id>/validate', methods=['POST'])
@facilitator_required
def validate_rca(project_id):
    user = User.query.get(get_jwt_identity())
    data = request.get_json()
    validation_note = data.get('validation_note', '').strip()

    if not validation_note:
        return jsonify({"msg": "validation_note is required"}), 400

    project = Project.query.get_or_404(project_id)
    if project.current_stage != 5:
        return jsonify({"msg": "Project is not in Stage 5"}), 400

    from app.infrastructure.database.models.models import Stage5RootCause
    rca = Stage5RootCause.query.filter_by(project_id=project_id).first()
    if not rca:
        rca = Stage5RootCause(project_id=project_id, org_id=project.org_id)
        db.session.add(rca)

    rca.rca_validation_note = validation_note
    rca.facilitator_id = user.id

    from app.presentation.routes.notification_routes import create_notification
    if project.team_leader_id and project.team_leader_id != user.id:
        create_notification(
            user.org_id, project.team_leader_id,
            "RCA Validated",
            f"Facilitator has validated the RCA for project '{project.title}'. Note: '{validation_note}'",
            f"/projects/project-details.html?id={project.id}",
            commit=False
        )

    log_action(user.org_id, user.id, "RCA Validated by Facilitator", project_id, validation_note)
    db.session.commit()

    return jsonify({
        "msg": "RCA Validated. Project is now eligible to advance to Stage 6.",
        "rca_validation_note": validation_note
    }), 200


# ─── 9. Stage 8 Post-Data Entry ───────────────────────────────
@facilitator_bp.route('/impact/<int:project_id>/post-data', methods=['POST'])
@facilitator_required
def add_post_data(project_id):
    user = User.query.get(get_jwt_identity())
    data = request.get_json()

    project = Project.query.get_or_404(project_id)
    if project.current_stage != 8:
        return jsonify({"msg": "Project is not in Stage 8"}), 400

    from app.infrastructure.database.models.models import Stage8Implementation
    impact = Stage8Implementation.query.filter_by(project_id=project_id).first()
    if not impact:
        impact = Stage8Implementation(project_id=project_id, org_id=project.org_id)
        db.session.add(impact)

    # Update allowed fields (Facilitator cannot touch financial fields directly)
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

    log_action(user.org_id, user.id, "Stage 7 Post-Data Added by Facilitator", project_id, str(data))
    db.session.commit()
    return jsonify({"msg": "Post-implementation data saved and impact review approved.", "kpi_improvement_pct": impact.kpi_improvement_pct}), 200


# ─── 10. Approve Stage 8 Results → Mark Final Approval ────────
@facilitator_bp.route('/impact/<int:project_id>/approve', methods=['POST'])
@facilitator_required
def approve_impact(project_id):
    user = User.query.get(get_jwt_identity())

    project = Project.query.get_or_404(project_id)
    if project.current_stage != 8:
        return jsonify({"msg": "Project is not in Stage 8"}), 400

    from app.infrastructure.database.models.models import Stage8Implementation, SOP
    
    # Check if SOP exists
    sop = SOP.query.filter_by(project_id=project_id, org_id=user.org_id).first()
    if not sop:
        return jsonify({"msg": "Approval blocked: Standard Operating Procedure (SOP) must be created before approving impact results."}), 400

    impact = Stage8Implementation.query.filter_by(project_id=project_id).first()
    if not impact:
        return jsonify({"msg": "No Stage 8 data found. Please enter post-implementation data first."}), 400

    if not impact.final_data:
        return jsonify({"msg": "Post-implementation data must be entered before approving."}), 400

    impact.status = 'Approved'
    impact.approved_by = user.id

    # Mark as ready for SOP creation
    project.status = 'Impact Approved'

    from app.presentation.routes.notification_routes import create_notification
    if project.team_leader_id and project.team_leader_id != user.id:
        create_notification(
            user.org_id, project.team_leader_id,
            "Impact Approved",
            f"Facilitator has approved impact results for project '{project.title}'.",
            f"/projects/project-details.html?id={project.id}",
            commit=False
        )

    log_action(user.org_id, user.id, "Stage 8 Approved by Facilitator → Awaiting SOP", project_id)
    db.session.commit()

    return jsonify({
        "msg": "Stage 8 results approved. Proceed to SOP Creation.",
        "current_stage": 8
    }), 200


# ─── 11. Stage 8 Closure Complete ────────────────────────────
@facilitator_bp.route('/closure/<int:project_id>/complete', methods=['POST'])
@facilitator_required
def complete_closure(project_id):
    """Facilitator project closure restricted — only Reviewers can close projects."""
    return jsonify({"msg": "Unauthorized: Project closure can only be performed by a Reviewer."}), 403
    
    sop = SOP.query.filter_by(project_id=project_id, org_id=project.org_id).first()
    if not sop:
        return jsonify({"msg": "Project closure blocked: No SOP is created or linked for this project."}), 400

    s8 = Stage8Implementation.query.filter_by(project_id=project_id).first()
    if not s8:
        s8 = Stage8Implementation(project_id=project_id, org_id=project.org_id)
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

    # Close the project workflow
    project.status = 'Closed'
    project.end_date = datetime.utcnow().date()
    
    # Activate linked SOP
    sop.status = 'Active'
    sop.effective_date = datetime.utcnow().date()
    sop.review_date = datetime.utcnow().date()

    # Complete Stage 8 tracker
    tracker = ProjectStageTracker.query.filter_by(project_id=project_id, stage_number=8).first()
    if tracker:
        tracker.status = 'Completed'
        tracker.completed_at = datetime.utcnow()

    # Facilitator sign-off
    s8.facilitator_validation = True
    s8.admin_closure = True
    s8.final_approval = True
    s8.final_approval_by = user.id
    s8.final_approval_at = datetime.utcnow()
    s8.final_comments = f"Final closure approved by Facilitator {user.username}."

    # Flush session so all changes are visible in db nested transaction
    db.session.flush()

    # Auto-archive into knowledge repository
    from app.presentation.routes.repository_routes import auto_archive_project_to_repository
    try:
        with db.session.begin_nested():
            auto_archive_project_to_repository(project_id, user.org_id)
    except Exception as archive_err:
        print(f"[QCMS Facilitator] Auto-archiving failed: {archive_err}")

    # Notify team
    from app.presentation.routes.notification_routes import create_notification
    notify_ids = set()
    if project.team_leader_id: notify_ids.add(project.team_leader_id)
    if project.reviewer_id: notify_ids.add(project.reviewer_id)
    if project.creator_id: notify_ids.add(project.creator_id)
    for uid in notify_ids:
        if uid != user.id:
            create_notification(
                user.org_id, uid,
                "Project Closed",
                f"Project '{project.title}' has been officially closed by Facilitator.",
                f"/projects/project-details.html?id={project_id}",
                commit=False
            )

    log_action(user.org_id, user.id, "Stage 8 Closure Signed Off and Closed by Facilitator", project_id, str(data))
    db.session.commit()

    return jsonify({
        "msg": "Facilitator closure sign-off complete. Project has been officially closed.",
        "facilitator_validation": True,
        "closed": True
    }), 200


# ─── 9. Facilitator Assistance Requests Feed ──────────────────────────
@facilitator_bp.route('/assistance-requests', methods=['GET'])
@facilitator_required
def get_assistance_requests():
    user = User.query.get(get_jwt_identity())
    from app.infrastructure.database.models.models import FacilitatorAssistanceRequest
    requests = FacilitatorAssistanceRequest.query.filter_by(
        org_id=user.org_id,
        facilitator_id=user.id
    ).order_by(FacilitatorAssistanceRequest.created_at.desc()).all()

    res = []
    for r in requests:
        req_user = User.query.get(r.user_id)
        proj = Project.query.get(r.project_id)
        res.append({
            "id": r.id,
            "project_id": r.project_id,
            "project_uid": proj.project_uid if proj else "PRJ-???",
            "project_title": proj.title if proj else "Unknown",
            "stage_id": r.stage_id,
            "user_name": (req_user.full_name or req_user.username) if req_user else "Unknown User",
            "user_email": req_user.email if req_user else "",
            "message": r.message,
            "status": r.status,
            "response": r.response,
            "created_at": r.created_at.isoformat() + "Z" if r.created_at else None
        })
    return jsonify(res), 200

@facilitator_bp.route('/assistance-requests/<int:req_id>/respond', methods=['POST'])
@facilitator_required
def respond_assistance_request(req_id):
    user = User.query.get(get_jwt_identity())
    from app.infrastructure.database.models.models import FacilitatorAssistanceRequest
    req_obj = db.session.get(FacilitatorAssistanceRequest, req_id)
    if not req_obj or req_obj.facilitator_id != user.id:
        return jsonify({"msg": "Request not found or unauthorized"}), 404
    data = request.get_json() or {}
    req_obj.response = data.get('response', '')
    req_obj.status = data.get('status', 'Responded')
    req_obj.updated_at = datetime.utcnow()

    # Notify requester
    from app.presentation.routes.notification_routes import create_notification
    proj = Project.query.get(req_obj.project_id)
    proj_title = proj.title if proj else "your project"
    create_notification(
        user.org_id,
        req_obj.user_id,
        f"Facilitator Assistance: {req_obj.status}",
        f"Facilitator {user.full_name or user.username} responded to your Stage {req_obj.stage_id} request on '{proj_title}'.",
        f"/projects/project-details.html?id={req_obj.project_id}&stage={req_obj.stage_id}",
        commit=False
    )

    db.session.commit()
    return jsonify({"msg": "Response updated successfully", "status": req_obj.status, "response": req_obj.response}), 200

