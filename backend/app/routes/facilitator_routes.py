from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from ..models import (
    User, Project, Department,
    Stage3RCA, Stage4Solution, Stage6Implementation,
    Stage7Impact, Stage8Standardization,
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
        if not user or user.role.name != 'Facilitator':
            return jsonify({"msg": "Facilitator access required"}), 403
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
    user = User.query.get(get_jwt_identity())
    org_id = user.org_id

    pending_rca = Project.query.filter_by(org_id=org_id, current_stage=3, status='In Progress').count()
    pending_impact = Project.query.filter_by(org_id=org_id, current_stage=7).count()

    # Stalled: In Progress for > 3 days without any movement
    stalled_cutoff = datetime.utcnow() - timedelta(days=3)
    stalled = Project.query.filter(
        Project.org_id == org_id,
        Project.status == 'In Progress',
        Project.created_at < stalled_cutoff
    ).count()

    impacts = Stage7Impact.query.filter(
        Stage7Impact.org_id == org_id,
        Stage7Impact.kpi_improvement_pct.isnot(None)
    ).all()
    avg_improvement = 0
    if impacts:
        avg_improvement = round(sum([i.kpi_improvement_pct or 0 for i in impacts]) / len(impacts), 1)

    total_savings = sum([
        i.cost_savings or 0
        for i in Stage7Impact.query.filter_by(org_id=org_id).all()
    ])

    return jsonify({
        "pending_rca": pending_rca,
        "pending_impact": pending_impact,
        "stalled_projects": stalled,
        "avg_improvement": f"{avg_improvement}%",
        "total_savings": total_savings,
        "total_projects": Project.query.filter_by(org_id=org_id).count()
    })


# ─── 2. All Projects Pipeline ─────────────────────────────────
@facilitator_bp.route('/projects', methods=['GET'])
@facilitator_required
def get_all_projects():
    user = User.query.get(get_jwt_identity())
    projects = Project.query.filter(
        Project.org_id == user.org_id,
        Project.status != 'Closed'
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


# ─── 3. RCA Workspace (Stage 3) ───────────────────────────────
@facilitator_bp.route('/rca-workspace', methods=['GET'])
@facilitator_required
def get_rca_workspace():
    user = User.query.get(get_jwt_identity())
    projects = Project.query.filter_by(org_id=user.org_id, current_stage=3).all()
    result = []
    for p in projects:
        rca = Stage3RCA.query.filter_by(project_id=p.id).first()
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


# ─── 4. Impact Review (Stage 7) ───────────────────────────────
@facilitator_bp.route('/impact-review', methods=['GET'])
@facilitator_required
def get_impact_review():
    user = User.query.get(get_jwt_identity())
    projects = Project.query.filter_by(org_id=user.org_id, current_stage=7).all()
    result = []
    for p in projects:
        impact = Stage7Impact.query.filter_by(project_id=p.id).first()
        s4 = Stage4Solution.query.filter_by(project_id=p.id).first()

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
            "kpi_target": s4.kpi_targets if s4 else {},
            "cost_savings": impact.cost_savings if impact else 0,
            "status": impact.status if impact else "Pending",
            "approved": impact.status == "Approved" if impact else False
        })
    return jsonify(result)


# ─── 5. Closure Projects (Stage 8) ───────────────────────────
@facilitator_bp.route('/closure-projects', methods=['GET'])
@facilitator_required
def get_closure_projects():
    user = User.query.get(get_jwt_identity())
    projects = Project.query.filter_by(org_id=user.org_id, current_stage=8).all()
    result = []
    for p in projects:
        std = Stage8Standardization.query.filter_by(project_id=p.id).first()
        result.append({
            "id": p.id,
            "title": p.title,
            "sop_status": "Uploaded" if std and std.sop_url else "Pending",
            "has_training_records": bool(std and std.training_records),
            "has_lessons": bool(std and std.lessons_learned),
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


# ─── 8. RCA Validation (Stage 3 Gate) ────────────────────────
@facilitator_bp.route('/rca/<int:project_id>/validate', methods=['POST'])
@facilitator_required
def validate_rca(project_id):
    user = User.query.get(get_jwt_identity())
    data = request.get_json()
    validation_note = data.get('validation_note', '').strip()

    if not validation_note:
        return jsonify({"msg": "validation_note is required"}), 400

    project = Project.query.get_or_404(project_id)
    if project.current_stage != 3:
        return jsonify({"msg": "Project is not in Stage 3"}), 400

    rca = Stage3RCA.query.filter_by(project_id=project_id).first()
    if not rca:
        rca = Stage3RCA(project_id=project_id, org_id=project.org_id)
        db.session.add(rca)

    rca.rca_validation_note = validation_note
    rca.facilitator_id = user.id

    log_action(user.org_id, user.id, "RCA Validated by Facilitator", project_id, validation_note)
    db.session.commit()

    return jsonify({
        "msg": "RCA Validated. Project is now eligible to advance to Stage 4.",
        "rca_validation_note": validation_note
    }), 200


# ─── 9. Stage 7 Post-Data Entry ───────────────────────────────
@facilitator_bp.route('/impact/<int:project_id>/post-data', methods=['POST'])
@facilitator_required
def add_post_data(project_id):
    user = User.query.get(get_jwt_identity())
    data = request.get_json()

    project = Project.query.get_or_404(project_id)
    if project.current_stage != 7:
        return jsonify({"msg": "Project is not in Stage 7"}), 400

    impact = Stage7Impact.query.filter_by(project_id=project_id).first()
    if not impact:
        impact = Stage7Impact(project_id=project_id, org_id=project.org_id)
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

    log_action(user.org_id, user.id, "Stage 7 Post-Data Added by Facilitator", project_id, str(data))
    db.session.commit()
    return jsonify({"msg": "Post-implementation data saved", "kpi_improvement_pct": impact.kpi_improvement_pct}), 200


# ─── 10. Approve Stage 7 Results → Advance to Stage 8 ────────
@facilitator_bp.route('/impact/<int:project_id>/approve', methods=['POST'])
@facilitator_required
def approve_impact(project_id):
    user = User.query.get(get_jwt_identity())

    project = Project.query.get_or_404(project_id)
    if project.current_stage != 7:
        return jsonify({"msg": "Project is not in Stage 7"}), 400

    impact = Stage7Impact.query.filter_by(project_id=project_id).first()
    if not impact:
        return jsonify({"msg": "No Stage 7 data found. Please enter post-implementation data first."}), 400

    if not impact.final_data:
        return jsonify({"msg": "Post-implementation data must be entered before approving."}), 400

    impact.status = 'Approved'
    impact.approved_by = user.id

    # Advance project to Stage 8
    project.current_stage = 8
    project.status = 'In Progress'

    # Auto-create Stage 8 record
    s8 = Stage8Standardization.query.filter_by(project_id=project_id).first()
    if not s8:
        s8 = Stage8Standardization(project_id=project_id, org_id=project.org_id)
        db.session.add(s8)

    log_action(user.org_id, user.id, "Stage 7 Approved by Facilitator → Advanced to Stage 8", project_id)
    db.session.commit()

    return jsonify({
        "msg": "Stage 7 results approved. Project advanced to Stage 8: Standardization.",
        "current_stage": 8
    }), 200


# ─── 11. Stage 8 Closure Complete ────────────────────────────
@facilitator_bp.route('/closure/<int:project_id>/complete', methods=['POST'])
@facilitator_required
def complete_closure(project_id):
    user = User.query.get(get_jwt_identity())
    data = request.get_json()

    project = Project.query.get_or_404(project_id)
    if project.current_stage != 8:
        return jsonify({"msg": "Project is not in Stage 8"}), 400

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

    # Facilitator sign-off
    s8.facilitator_validation = True
    project.status = 'Pending Closure'  # Admin must also close

    log_action(user.org_id, user.id, "Stage 8 Closure Signed Off by Facilitator", project_id, str(data))
    db.session.commit()

    return jsonify({
        "msg": "Facilitator closure sign-off complete. Awaiting Admin final closure.",
        "facilitator_validation": True
    }), 200
