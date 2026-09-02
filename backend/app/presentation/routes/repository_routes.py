"""
Module 6: Knowledge Repository Routes
GET /api/repository/search, /api/repository/<id>, /api/repository/archive
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.infrastructure.database.models.models import (
    User, Project, Organization, KnowledgeRepository, Stage3RCA, Stage7Impact,
    Stage8Standardization, ProjectWorkflow, AuditLog,
    Stage7PerformanceVerificationBenefitsRealization as Stage7Verification,
    Stage8StandardizationKnowledgeSharingProjectClosure as Stage8Implementation
)
from app import db
from datetime import datetime, timedelta, timezone
from functools import wraps

repository_bp = Blueprint('repository', __name__)

def admin_required(f):
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        user = db.session.get(User, get_jwt_identity())
        if not user:
            return jsonify({"msg": "User not found"}), 404
        role_name = user.role.name if user.role else ''
        if role_name in ('Admin', 'SuperAdmin', 'CEO'):
            return f(*args, **kwargs)
        from app.presentation.routes.admin_routes import check_user_module_permission
        if check_user_module_permission(user, 'knowledge_base'):
            return f(*args, **kwargs)
        return jsonify({"msg": "Admin access required"}), 403
    return decorated

import re

def parse_clean_float(val):
    if val is None or val == '' or val == 'N/A' or val == '--':
        return None
    if isinstance(val, (int, float)):
        return float(val)
    match = re.search(r'[-+]?\d*\.?\d+', str(val).replace(',', ''))
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return None
    return None

def calculate_weighted_progress(current_stage, weights=None):
    """
    Calculate cumulative progress percentage based on SuperAdmin-configured stage weightages.
    weights: list of floats summing to 100.0
    If weights is None, defaults to equal weights across stages.
    """
    if not weights or not isinstance(weights, list) or len(weights) < 1:
        weights = [12.5] * 8
    
    n_stages = len(weights)
    stage = max(1, min(n_stages, int(current_stage or 1)))
    # Sum weights of completed/current stages (1 to stage)
    cum_pct = sum(weights[:stage])
    return min(100.0, max(0.0, cum_pct))


def calculate_project_realtime_efficiency(project_id, project_current_stage=1):
    """
    Calculates real-time project efficiency & KPI improvement % across all QC Story workflow stages:
    1. Verified results from Stage 7 (before vs after, KPI verification, ROI improvement)
    2. Verified results from Stage 8 (benefits summary, standardization, closure impact)
    3. Dedicated Stage 7 & 8 relational models and Knowledge Repository records
    4. Interim realized efficiency from Stage 1-6 targets scaled by stage completion
    5. Fallback workflow milestone execution efficiency based on stage completion velocity
    """
    from app.infrastructure.database.models.models import (
        ProjectWorkflow,
        Stage7PerformanceVerificationBenefitsRealization,
        Stage8StandardizationKnowledgeSharingProjectClosure,
        KnowledgeRepository
    )

    stage_num = max(1, min(8, int(project_current_stage or 1)))

    # 1. Check ProjectWorkflow Stage 7 (Verified Before vs After / KPI Verification / ROI)
    wf7 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=7).first()
    if wf7 and wf7.data:
        d7 = wf7.data
        # A. before_vs_after
        bva = d7.get('before_vs_after') or d7.get('s7_before_vs_after') or []
        if isinstance(bva, list) and len(bva) > 0:
            imp_list = []
            for r in bva:
                if not isinstance(r, dict):
                    continue
                imp_p = parse_clean_float(r.get('improvement_pct'))
                if imp_p is not None and imp_p > 0:
                    imp_list.append(imp_p)
                else:
                    bef = parse_clean_float(r.get('before_condition'))
                    aft = parse_clean_float(r.get('after_condition'))
                    if bef and aft is not None and bef > 0:
                        imp_list.append(round(((bef - aft) / bef) * 100, 1))
            if imp_list:
                return round(sum(imp_list) / len(imp_list), 1)

        # B. kpi_verification
        kpi_ver = d7.get('kpi_verification') or d7.get('s7_kpi_verification') or []
        if isinstance(kpi_ver, list) and len(kpi_ver) > 0:
            kpi_imps = []
            for r in kpi_ver:
                if not isinstance(r, dict):
                    continue
                base = parse_clean_float(r.get('baseline'))
                act = parse_clean_float(r.get('actual'))
                if base and act is not None and base > 0:
                    kpi_imps.append(round(abs(base - act) / base * 100, 1))
            if kpi_imps:
                return round(sum(kpi_imps) / len(kpi_imps), 1)

        # C. roi_validation
        roi = d7.get('roi_validation') or d7.get('s7_roi_validation') or {}
        if isinstance(roi, dict):
            kpi_imp = parse_clean_float(roi.get('kpi_improvement_pct') or roi.get('kpi_improvement') or roi.get('s7_roi_pct'))
            if kpi_imp is not None and kpi_imp > 0:
                return round(kpi_imp, 1)

    # 2. Check ProjectWorkflow Stage 8 (Benefits Summary / Impact)
    wf8 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=8).first()
    if wf8 and wf8.data:
        d8 = wf8.data
        bs = d8.get('benefits_summary') or d8.get('s8_benefits_summary') or []
        if isinstance(bs, list) and len(bs) > 0:
            b_imps = []
            for r in bs:
                if not isinstance(r, dict):
                    continue
                imp_val = parse_clean_float(r.get('improvement_pct') or r.get('kpi_improvement'))
                if imp_val is not None and imp_val > 0:
                    b_imps.append(imp_val)
                else:
                    base = parse_clean_float(r.get('baseline'))
                    fin = parse_clean_float(r.get('final'))
                    if base and fin is not None and base > 0:
                        b_imps.append(round(abs(base - fin) / base * 100, 1))
            if b_imps:
                return round(sum(b_imps) / len(b_imps), 1)

    # 3. Check Dedicated Stage Models
    s7_model = Stage7PerformanceVerificationBenefitsRealization.query.filter_by(project_id=project_id).first()
    if s7_model:
        bva = s7_model.before_vs_after
        if isinstance(bva, list) and len(bva) > 0:
            imp_list = [parse_clean_float(r.get('improvement_pct')) for r in bva if isinstance(r, dict) and parse_clean_float(r.get('improvement_pct')) is not None]
            if imp_list:
                return round(sum(imp_list) / len(imp_list), 1)

    s8_model = Stage8StandardizationKnowledgeSharingProjectClosure.query.filter_by(project_id=project_id).first()
    if s8_model:
        if s8_model.kpi_improvement_pct:
            return round(float(s8_model.kpi_improvement_pct), 1)
        if s8_model.productivity_gain:
            p_gain = parse_clean_float(s8_model.productivity_gain)
            if p_gain and p_gain > 0:
                return round(p_gain, 1)

    # 4. Check Knowledge Repository (if archived/completed project)
    repo = KnowledgeRepository.query.filter_by(project_id=project_id).first()
    if repo and repo.kpi_improvement_pct:
        return round(float(repo.kpi_improvement_pct), 1)

    # 5. Calculate Interim Realized Efficiency from Stage 1 Targets
    wf1 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=1).first()
    if wf1 and wf1.data:
        d1 = wf1.data
        tts = d1.get('theme_target_schedule') or d1.get('s1_theme_target_schedule') or {}
        cur = parse_clean_float(tts.get('current_level') or d1.get('s1_tts_current'))
        tgt = parse_clean_float(tts.get('target_level') or d1.get('s1_tts_target'))
        if cur and tgt is not None and cur > 0:
            target_pct = abs(cur - tgt) / cur * 100.0
            stage_factor = min(1.0, stage_num / 8.0)
            interim_eff = target_pct * stage_factor
            if interim_eff > 0:
                return round(interim_eff, 1)

        # Check cp (current performance defect rate vs target)
        cp = d1.get('current_performance') or d1.get('s1_current_performance') or {}
        cp_def = parse_clean_float(cp.get('defect_rate') or d1.get('s1_cp_defect_rate'))
        if cp_def and cp_def > 0:
            stage_factor = min(1.0, stage_num / 8.0)
            interim_eff = min(100.0, (stage_factor * 100.0))
            return round(interim_eff, 1)

    # 6. Fallback Workflow Milestone Execution Efficiency
    # Progressive efficiency reflects the verified advancement across 8 standard QC stages
    workflow_eff = (stage_num / 8.0) * 100.0
    return round(min(100.0, max(10.0, workflow_eff)), 1)


# ============================
# PROJECT REPOSITORY MASTER LIST
# ============================
@repository_bp.route('/list', methods=['GET'])
@jwt_required()
def list_repository_projects():
    """Real-time project repository for all roles with stats and health metrics."""
    user = db.session.get(User, get_jwt_identity())
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    # Filters
    page = request.args.get('page', type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    q = request.args.get('q', '').strip()
    dept_id = request.args.get('department_id')
    status = request.args.get('status')
    stage = request.args.get('stage')
    category = request.args.get('category')
    plant_param = (request.args.get('plant') or request.args.get('plant_name') or request.args.get('plant_id') or '').strip()
    
    from app.infrastructure.database.models.models import ProjectMember, AuditLog, Plant, Department
    query = Project.query.filter_by(org_id=user.org_id)
    
    # Enforce Role-Based Access Control for visibility
    if user.role.name == 'Team Member':
        query = query.filter(Project.members.any(id=user.id))
    elif user.role.name == 'Team Leader':
        # Team Leaders can see projects they lead, created, or are assigned to
        query = query.filter(db.or_(
            Project.team_leader_id == user.id,
            Project.creator_id == user.id,
            Project.members.any(id=user.id)
        ))
    elif user.role.name == 'Facilitator':
        query = query.filter(Project.facilitator_id == user.id)
    # Reviewers, Admins, CEOs, SuperAdmins can see all org projects

    if plant_param:
        if plant_param.isdigit():
            plant_obj = Plant.query.filter_by(id=int(plant_param), org_id=user.org_id).first()
            pname = plant_obj.name if plant_obj else None
            if pname:
                query = query.filter(db.or_(
                    Project.plant.ilike(f"%{pname}%"),
                    Project.department.has(Department.plant_id == int(plant_param))
                ))
            else:
                query = query.filter(Project.department.has(Department.plant_id == int(plant_param)))
        else:
            query = query.filter(db.or_(
                Project.plant.ilike(f"%{plant_param}%"),
                Project.department.has(Department.plant.has(Plant.name.ilike(f"%{plant_param}%")))
            ))

    if q:
        q_term = f"%{q}%"
        query = query.filter(db.or_(
            Project.title.ilike(q_term),
            Project.project_uid.ilike(q_term),
            Project.category.ilike(q_term)
        ))

    if dept_id and str(dept_id).isdigit():
        query = query.filter_by(department_id=int(dept_id))

    # STRICT RULE: Closed / Completed / Archived projects belong in Knowledge Base ONLY.
    # They MUST NEVER be visible in Project Repository default listing.
    closed_statuses = ['Closed', 'Completed', 'Archived', 'CLOSED', 'COMPLETED', 'ARCHIVED', 'Stage 8 Approved']

    # ── Real-Time Overall Scope Statistics (Computed before pagination / status filters) ──
    stats_scope_query = Project.query.filter_by(org_id=user.org_id)
    if user.role.name == 'Team Member':
        stats_scope_query = stats_scope_query.filter(Project.members.any(id=user.id))
    elif user.role.name == 'Team Leader':
        stats_scope_query = stats_scope_query.filter(db.or_(
            Project.team_leader_id == user.id,
            Project.creator_id == user.id,
            Project.members.any(id=user.id)
        ))
    elif user.role.name == 'Facilitator':
        stats_scope_query = stats_scope_query.filter(Project.facilitator_id == user.id)

    if plant_param:
        if plant_param.isdigit():
            plant_obj = Plant.query.filter_by(id=int(plant_param), org_id=user.org_id).first()
            pname = plant_obj.name if plant_obj else None
            if pname:
                stats_scope_query = stats_scope_query.filter(db.or_(
                    Project.plant.ilike(f"%{pname}%"),
                    Project.department.has(Department.plant_id == int(plant_param))
                ))
            else:
                stats_scope_query = stats_scope_query.filter(Project.department.has(Department.plant_id == int(plant_param)))
        else:
            stats_scope_query = stats_scope_query.filter(db.or_(
                Project.plant.ilike(f"%{plant_param}%"),
                Project.department.has(Department.plant.has(Plant.name.ilike(f"%{plant_param}%")))
            ))

    if dept_id and str(dept_id).isdigit():
        stats_scope_query = stats_scope_query.filter_by(department_id=int(dept_id))

    if category:
        stats_scope_query = stats_scope_query.filter_by(category=category)

    all_scope_projects = stats_scope_query.all()

    inactivity_days = 30
    if user and hasattr(user, 'org_id') and user.org_id:
        org = db.session.get(Organization, user.org_id)
        if org and getattr(org, 'project_inactivity_days', None):
            inactivity_days = org.project_inactivity_days
            
    inactivity_cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=inactivity_days)

    stopped_scope_projects = [
        p for p in all_scope_projects 
        if (p.status or '') in ('Rejected', 'Cancelled', 'Stopped', 'On Hold', 'Stage 1 Rejected') or 
           ('reject' in (p.status or '').lower() or 'stop' in (p.status or '').lower())
    ]
    closed_scope_projects = [
        p for p in all_scope_projects 
        if (p.status or '') in closed_statuses
    ]
    active_scope_projects = [
        p for p in all_scope_projects 
        if p not in stopped_scope_projects and p not in closed_scope_projects
    ]

    scope_stalled_count = 0
    scope_active_count = 0
    for p in active_scope_projects:
        last_log = AuditLog.query.filter_by(project_id=p.id).order_by(AuditLog.created_at.desc()).first()
        last_activity = last_log.created_at if last_log else p.created_at
        if last_activity and last_activity < inactivity_cutoff:
            scope_stalled_count += 1
        else:
            scope_active_count += 1

    scope_stopped_count = len(stopped_scope_projects)
    scope_completed_count = len(closed_scope_projects)
    scope_total_count = len(all_scope_projects)

    # ── Table Data Filtering ────────────────────────────────────────────────
    if status and str(status).lower() != 'all':
        if status == 'Active':
            query = query.filter(~Project.status.in_(closed_statuses + ['Rejected', 'On Hold', 'Cancelled', 'Stage 1 Rejected']))
        elif status in ['Closed', 'Completed', 'Archived']:
            query = query.filter(Project.status.in_(closed_statuses))
        elif status in ['Inactive', 'Stalled']:
            three_days_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=3)
            recent_active_pids = db.session.query(AuditLog.project_id).filter(
                AuditLog.created_at >= three_days_ago,
                AuditLog.project_id.isnot(None)
            ).subquery()
            query = query.filter(
                ~Project.status.in_(closed_statuses),
                db.or_(
                    Project.created_at < three_days_ago,
                    ~Project.id.in_(recent_active_pids)
                )
            )
        elif status in ['Stopped', 'Rejected', 'Cancelled']:
            query = query.filter(db.or_(
                Project.status.in_(['Rejected', 'Cancelled', 'Stopped', 'On Hold', 'Stage 1 Rejected']),
                Project.status.ilike('Rejected%'),
                Project.status.ilike('Stopped%'),
                Project.status.ilike('%Rejected%'),
                Project.status.ilike('%Stopped%')
            ))
        elif status == 'Pending Approval':
            from app.infrastructure.database.models.models import (
                ProjectStageTracker, ProjectReview,
                Stage1ProblemDefinitionProjectInitiation,
                Stage8StandardizationKnowledgeSharingProjectClosure
            )

            pending_tracker_statuses = [
                'Submitted For Review', 'Pending Approval', 'Pending',
                'Submitted', 'Awaiting Reviewer Approval', 'Under Review', 'Pending Review'
            ]
            pending_review_statuses = ['Pending', 'Under Review', 'Submitted']

            pending_tracker_pids = db.session.query(ProjectStageTracker.project_id).filter(
                ProjectStageTracker.status.in_(pending_tracker_statuses)
            ).scalar_subquery()

            pending_review_pids = db.session.query(ProjectReview.project_id).filter(
                ProjectReview.status.in_(pending_review_statuses)
            ).scalar_subquery()

            stage1_pending_pids = db.session.query(Stage1ProblemDefinitionProjectInitiation.project_id).filter(
                db.or_(
                    Stage1ProblemDefinitionProjectInitiation.facilitator_approved.is_(False),
                    Stage1ProblemDefinitionProjectInitiation.facilitator_approved.is_(None)
                )
            ).scalar_subquery()

            stage8_pending_pids = db.session.query(Stage8StandardizationKnowledgeSharingProjectClosure.project_id).filter(
                db.or_(
                    Stage8StandardizationKnowledgeSharingProjectClosure.final_approval.is_(False),
                    Stage8StandardizationKnowledgeSharingProjectClosure.final_approval.is_(None),
                    Stage8StandardizationKnowledgeSharingProjectClosure.admin_closure.is_(False),
                    Stage8StandardizationKnowledgeSharingProjectClosure.admin_closure.is_(None),
                    Stage8StandardizationKnowledgeSharingProjectClosure.facilitator_validation.is_(False),
                    Stage8StandardizationKnowledgeSharingProjectClosure.facilitator_validation.is_(None)
                )
            ).scalar_subquery()

            query = query.filter(
                ~Project.status.in_(closed_statuses),
                db.or_(
                    Project.status.ilike('%Pending%'),
                    Project.status.ilike('%Submitted%'),
                    Project.status.ilike('%Awaiting%'),
                    Project.status.in_(['Stage 8 Submitted', 'Stage 8 Reviewer Approved', 'Pending Closure', 'SOP Created', 'Pending Review', 'Submitted', 'Awaiting Approval']),
                    Project.id.in_(pending_tracker_pids),
                    Project.id.in_(pending_review_pids),
                    Project.id.in_(stage1_pending_pids),
                    Project.id.in_(stage8_pending_pids)
                )
            )
        else:
            query = query.filter(Project.status == status)
    else:
        # STRICT DEFAULT: Exclude closed/completed/archived projects from Project Repository
        query = query.filter(~Project.status.in_(closed_statuses))

    if stage and str(stage).isdigit():
        query = query.filter_by(current_stage=int(stage))

    if category:
        query = query.filter_by(category=category)
        
    projects = query.order_by(Project.created_at.desc()).all()
    
    results = []
    
    from app.infrastructure.database.models.models import (
        ProjectStageTracker, ProjectReview,
        Stage1ProblemDefinitionProjectInitiation,
        Stage8StandardizationKnowledgeSharingProjectClosure,
        PlatformSettings
    )

    ps = PlatformSettings.query.first()
    stage_weights = (ps and ps.stage_weightage_config) or None

    for p in projects:
        # Efficiency: calculate real-time KPI improvement % from all active workflow stages (Stage 7 & Stage 8)
        efficiency = calculate_project_realtime_efficiency(p.id, p.current_stage)
        
        # Calculate weighted progress percentage
        progress_pct = round(calculate_weighted_progress(p.current_stage, stage_weights), 1)
        
        # Detect stalled/inactive status based on organization's configured inactivity threshold (days)
        last_log = AuditLog.query.filter_by(project_id=p.id).order_by(AuditLog.created_at.desc()).first()
        last_activity = last_log.created_at if last_log else p.created_at
        
        is_stalled = False
        if last_activity and last_activity < inactivity_cutoff:
            is_stalled = True

        display_status = p.status
        if p.status not in ('Closed', 'Completed', 'Archived'):
            is_p_approval = False
            if p.status and any(w in p.status for w in ['Pending', 'Submitted', 'Awaiting']):
                is_p_approval = True
            else:
                tr = ProjectStageTracker.query.filter_by(project_id=p.id, stage_number=p.current_stage).first()
                if tr and tr.status in ['Submitted For Review', 'Pending Approval', 'Pending', 'Submitted', 'Awaiting Reviewer Approval', 'Under Review', 'Pending Review']:
                    is_p_approval = True
                else:
                    rev = ProjectReview.query.filter_by(project_id=p.id, status='Pending').first()
                    if rev:
                        is_p_approval = True
                    elif p.current_stage == 1:
                        s1 = Stage1ProblemDefinitionProjectInitiation.query.filter_by(project_id=p.id).first()
                        if s1 and (s1.facilitator_approved is None or s1.facilitator_approved is False):
                            is_p_approval = True
                    elif p.current_stage == 8:
                        s8 = Stage8StandardizationKnowledgeSharingProjectClosure.query.filter_by(project_id=p.id).first()
                        if s8 and (s8.final_approval is None or s8.final_approval is False or s8.admin_closure is None or s8.admin_closure is False):
                            is_p_approval = True

            if is_p_approval:
                display_status = 'Pending Approval'

        results.append({
            "id": p.id,
            "project_uid": p.project_uid,
            "title": p.title,
            "category": p.category,
            "department": p.department.name if p.department else "N/A",
            "team_leader": p.team_leader.full_name if p.team_leader else "N/A",
            "current_stage": p.current_stage,
            "progress": progress_pct,
            "progress_pct": progress_pct,
            "efficiency": efficiency,
            "status": display_status,
            "is_stalled": is_stalled,
            "last_updated": last_activity.isoformat() + "Z"
        })

    total_items = len(results)
    if page is not None:
        start = (page - 1) * per_page
        end = start + per_page
        paginated_projects = results[start:end]
        total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 1
        return jsonify({
            "stats": {
                "total": scope_total_count,
                "active": scope_active_count,
                "stalled": scope_stalled_count,
                "stopped": scope_stopped_count,
                "completed": scope_completed_count
            },
            "page": page,
            "per_page": per_page,
            "total": total_items,
            "total_pages": total_pages,
            "projects": paginated_projects
        }), 200
        
    return jsonify({
        "stats": {
            "total": scope_total_count,
            "active": scope_active_count,
            "stalled": scope_stalled_count,
            "stopped": scope_stopped_count,
            "completed": scope_completed_count
        },
        "page": 1,
        "per_page": total_items,
        "total": total_items,
        "total_pages": 1,
        "projects": results
    }), 200

def sanitize_num(val):
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, (list, dict)):
        return 0.0
    s = str(val).replace(',', '').replace('%', '').replace('₹', '').replace('Rs', '').replace('INR', '').strip()
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0

def extract_project_kpi_and_savings(project_id, org_id):
    kpi_imp = 0.0
    cost_sav = 0.0

    workflows = {wf.stage_id: wf.data for wf in ProjectWorkflow.query.filter_by(project_id=project_id, org_id=org_id).all()}
    wf7 = workflows.get(7, {})
    if wf7 and isinstance(wf7, dict):
        roi = wf7.get('roi_validation') or wf7.get('roi') or {}
        if isinstance(roi, dict):
            cost_sav = sanitize_num(roi.get('annual_savings') or roi.get('savings') or roi.get('total_savings'))
            raw_kpi = roi.get('kpi_improvement_pct') or roi.get('kpi_improvement')
            if raw_kpi:
                kpi_imp = sanitize_num(raw_kpi)

        if not cost_sav:
            ben = wf7.get('benefit_realization') or {}
            if isinstance(ben, dict):
                cost_sav = sanitize_num(ben.get('actual') or ben.get('actual_savings') or ben.get('savings'))

        if not kpi_imp:
            b4_aft = wf7.get('before_vs_after') or wf7.get('comparison') or []
            if isinstance(b4_aft, list) and len(b4_aft) > 0:
                imps = [sanitize_num(item.get('improvement_pct') or item.get('improvement')) for item in b4_aft if isinstance(item, dict)]
                valid_imps = [v for v in imps if v > 0]
                if valid_imps:
                    kpi_imp = round(max(valid_imps), 1)

        if not kpi_imp:
            kpi_ver = wf7.get('kpi_verification') or []
            if isinstance(kpi_ver, list) and len(kpi_ver) > 0:
                imps = []
                for item in kpi_ver:
                    if isinstance(item, dict):
                        b = sanitize_num(item.get('baseline'))
                        a = sanitize_num(item.get('actual'))
                        if b > 0:
                            imp = round(abs(b - a) / b * 100, 1)
                            imps.append(imp)
                if imps:
                    kpi_imp = round(max(imps), 1)

    if not cost_sav or not kpi_imp:
        s8 = Stage8Implementation.query.filter_by(project_id=project_id, org_id=org_id).first()
        if s8:
            if not cost_sav and s8.cost_savings:
                cost_sav = sanitize_num(s8.cost_savings)
            if not kpi_imp and s8.kpi_improvement_pct:
                kpi_imp = sanitize_num(s8.kpi_improvement_pct)

    if not cost_sav or not kpi_imp:
        from app.infrastructure.database.models.models import Stage7Impact
        s7_imp = Stage7Impact.query.filter_by(project_id=project_id, org_id=org_id).first()
        if s7_imp:
            if not cost_sav and hasattr(s7_imp, 'cost_savings') and s7_imp.cost_savings:
                cost_sav = sanitize_num(s7_imp.cost_savings)
            if not kpi_imp and hasattr(s7_imp, 'kpi_improvement_pct') and s7_imp.kpi_improvement_pct:
                kpi_imp = sanitize_num(s7_imp.kpi_improvement_pct)

    return round(kpi_imp, 1), round(cost_sav, 2)

# ============================
# AUTO-ARCHIVE ENGINE
# ============================
def auto_archive_project_to_repository(project_id, org_id):
    """Archiving of a project into the knowledge repository from workflow stages JSON or fallback."""
    project = Project.query.filter_by(id=project_id, org_id=org_id).first()
    if not project:
        return None
        
    # Strictly enforce that ONLY closed/completed/archived projects can be in KnowledgeRepository
    if project.status not in ('Closed', 'Completed', 'Archived'):
        return None

    # Check if already archived
    existing = KnowledgeRepository.query.filter_by(project_id=project_id, org_id=org_id).first()
    if existing:
        return existing
        
    # Gather data from ProjectWorkflow records (which store stages 1 to 8 in JSON format)
    workflows = {wf.stage_id: (wf.data or {}) for wf in ProjectWorkflow.query.filter_by(project_id=project_id, org_id=org_id).all()}
    
    # 1. Problem summary (Stage 1)
    wf1 = workflows.get(1, {})
    prob_sum = ""
    if wf1:
        prob_sum = wf1.get('theme_target_schedule', {}).get('improvement_theme', '')
        if not prob_sum:
            prob_sum = wf1.get('background_5w2h', {}).get('what', '')
    if not prob_sum:
        # Fallback to stage 1 model or project description
        from app.infrastructure.database.models import Stage1ProblemDefinitionProjectInitiation
        stage1 = Stage1ProblemDefinitionProjectInitiation.query.filter_by(project_id=project_id, org_id=org_id).first()
        if stage1:
            theme_sched = getattr(stage1, 'theme_target_schedule', {}) or {}
            prob_sum = theme_sched.get('improvement_theme', '') if isinstance(theme_sched, dict) else ''
    if not prob_sum and project and project.description:
        prob_sum = project.description
            
    # 2. Root cause (Stage 4 / Stage 3)
    wf4 = workflows.get(4, {})
    root_cause_val = ""
    if wf4:
        rc_list = wf4.get('root_cause_register', [])
        if isinstance(rc_list, list):
            root_cause_val = ", ".join([rc.get('root_cause', '') for rc in rc_list if isinstance(rc, dict) and rc.get('root_cause')])
    if not root_cause_val:
        wf3 = workflows.get(3, {})
        if wf3:
            c_list = wf3.get('cause_register', [])
            if isinstance(c_list, list):
                root_cause_val = ", ".join([c.get('cause', '') for c in c_list if isinstance(c, dict) and c.get('cause')])
    if not root_cause_val:
        from app.infrastructure.database.models import Stage3CauseIdentification
        s3 = Stage3CauseIdentification.query.filter_by(project_id=project_id, org_id=org_id).first()
        if s3 and getattr(s3, 'shortlisted_causes', None) and isinstance(s3.shortlisted_causes, list):
            root_cause_val = ", ".join([str(c) for c in s3.shortlisted_causes if c])
            
    # 3. Solution summary (Stage 5)
    wf5 = workflows.get(5, {})
    sol_sum = ""
    if wf5:
        sol_list = wf5.get('root_cause_mapping', [])
        if isinstance(sol_list, list):
            sol_sum = "; ".join([s.get('proposed_solution', '') for s in sol_list if isinstance(s, dict) and s.get('proposed_solution')])
    if not sol_sum:
        from app.infrastructure.database.models import Stage5CountermeasurePlanningSolutionDevelopment
        stage5 = Stage5CountermeasurePlanningSolutionDevelopment.query.filter_by(project_id=project_id, org_id=org_id).first()
        if stage5:
            sol_list = getattr(stage5, 'proposed_countermeasures', None)
            if isinstance(sol_list, list):
                sol_sum = "; ".join([str(s) for s in sol_list if s])
            
    # 4. KPI Improvement Pct & Cost Savings (Stage 7 / 8)
    kpi_imp, cost_sav = extract_project_kpi_and_savings(project_id, org_id)
                
    # 5. SOP Path & Closure Report (Stage 8)
    wf8 = workflows.get(8, {})
    sop_url = None
    closure_report = None
    if wf8:
        std_list = wf8.get('standardization', [])
        if std_list and isinstance(std_list, list) and len(std_list) > 0 and isinstance(std_list[0], dict):
            sop_url = std_list[0].get('link') or std_list[0].get('document')
        repo_list = wf8.get('knowledge_repository', [])
        if repo_list and isinstance(repo_list, list) and len(repo_list) > 0 and isinstance(repo_list[0], dict):
            closure_report = repo_list[0].get('link')
            if not sop_url:
                sop_url = repo_list[0].get('link')
    if not sop_url or not closure_report:
        from app.infrastructure.database.models.models import Stage8Standardization
        std = Stage8Standardization.query.filter_by(project_id=project_id, org_id=org_id).first()
        if std:
            if not sop_url and hasattr(std, 'sop_url'):
                sop_url = std.sop_url
            if not closure_report and hasattr(std, 'closure_report_path'):
                closure_report = std.closure_report_path
                
    cat_val = project.category
    if isinstance(cat_val, list):
        cat_str = ", ".join([str(c) for c in cat_val if c])
    elif cat_val:
        cat_str = str(cat_val)
    else:
        cat_str = ""

    entry = KnowledgeRepository(
        project_id=project_id,
        org_id=org_id,
        title=project.title,
        department_id=project.department_id,
        category=cat_str[:20] if cat_str else None,
        problem_summary=prob_sum or '',
        root_cause=root_cause_val or '',
        solution_summary=sol_sum or '',
        kpi_improvement_pct=kpi_imp,
        cost_savings=cost_sav,
        sop_path=sop_url,
        closure_report_path=closure_report,
        tags=cat_val if isinstance(cat_val, list) else ([cat_str] if cat_str else []),
        keywords=f"{project.title} {cat_str}",
        archived_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.session.add(entry)
    db.session.flush()
    
    # Dispatch asynchronous vector indexing
    try:
        from app.infrastructure.tasks.ai_rag_tasks import process_document_for_rag
        process_document_for_rag.delay(entry.id, org_id)
    except Exception:
        # Background worker fallback
        import threading
        from flask import current_app
        try:
            app_obj = current_app._get_current_object()
        except Exception:
            app_obj = None

        def _bg_vector(app_inst, doc_id, o_id):
            if app_inst:
                with app_inst.app_context():
                    from app.infrastructure.database.models.models import KnowledgeRepository, db
                    from app.infrastructure.vector_db.vector_ingest import get_embedding_model
                    try:
                        d = db.session.get(KnowledgeRepository, doc_id)
                        if d:
                            model = get_embedding_model()
                            content = f"Title: {d.title or ''}\nCategory: {d.category or ''}\nProblem: {d.problem_summary or ''}\nRoot Cause: {d.root_cause or ''}\nSolution: {d.solution_summary or ''}\n"
                            raw_emb = model.encode(content)
                            d.embedding = raw_emb.tolist() if hasattr(raw_emb, 'tolist') else list(raw_emb)
                            db.session.commit()
                    except Exception as err:
                        print(f"[RAG Background Indexing Error] {err}")
                    finally:
                        try:
                            db.session.remove()
                        except Exception:
                            pass

        t = threading.Thread(target=_bg_vector, args=(app_obj, entry.id, org_id))
        t.daemon = True
        t.start()

    return entry

@repository_bp.route('/archive/<int:project_id>', methods=['POST'])
@admin_required
def archive_project(project_id):
    """Admin-triggered archive of a closed project into knowledge repository."""
    user = db.session.get(User, get_jwt_identity())
    project = Project.query.filter_by(id=project_id, org_id=user.org_id).first_or_404()
    
    if project.status != 'Closed':
        return jsonify({"msg": "Only closed projects can be archived"}), 400
    
    # Check if already archived
    existing = KnowledgeRepository.query.filter_by(project_id=project_id).first()
    if existing:
        return jsonify({"msg": "Project is already archived"}), 400
    
    entry = auto_archive_project_to_repository(project_id, user.org_id)
    
    # Audit log
    audit = AuditLog(
        user_id=user.id,
        org_id=user.org_id,
        action='PROJECT_ARCHIVED',
        target_table='knowledge_repository',
        target_id=project_id,
        details={"title": project.title}
    )
    db.session.add(audit)
    
    db.session.commit()
    return jsonify({"msg": "Project archived into knowledge repository"})


# ============================
# SEARCH
# ============================
@repository_bp.route('/search', methods=['GET'])
@jwt_required()
def search_repository():
    """Advanced search with keyword, department, category, date range, and pagination."""
    keyword = request.args.get('q', '')
    dept_id = request.args.get('department_id')
    category = request.args.get('category')
    plant_param = (request.args.get('plant') or request.args.get('plant_name') or request.args.get('plant_id') or '').strip()
    date_from = request.args.get('from')
    date_to = request.args.get('to')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 12))
    
    user = db.session.get(User, get_jwt_identity())

    closed_statuses = ['Closed', 'Completed', 'Archived', 'CLOSED', 'COMPLETED', 'ARCHIVED', 'Stage 8 Approved']

    # 1. Clean up KnowledgeRepository table: Remove entries for projects that are NOT Closed/Completed/Archived
    open_project_ids = [p.id for p in Project.query.filter(
        Project.org_id == user.org_id,
        ~Project.status.in_(closed_statuses)
    ).all()]
    if open_project_ids:
        KnowledgeRepository.query.filter(
            KnowledgeRepository.org_id == user.org_id,
            KnowledgeRepository.project_id.in_(open_project_ids)
        ).delete(synchronize_session=False)
        db.session.commit()

    # 2. Auto-sync ONLY closed/completed projects into KnowledgeRepository
    closed_projects = Project.query.filter(
        Project.org_id == user.org_id,
        Project.status.in_(closed_statuses)
    ).all()

    for p in closed_projects:
        auto_archive_project_to_repository(p.id, user.org_id)
    db.session.commit()

    closed_pids = [p.id for p in closed_projects]
    if not closed_pids:
        return jsonify({
            "results": [],
            "total": 0,
            "pages": 0,
            "current_page": page
        }), 200

    from sqlalchemy.orm import defer
    query = KnowledgeRepository.query.options(defer(KnowledgeRepository.embedding)).filter(
        KnowledgeRepository.org_id == user.org_id,
        KnowledgeRepository.project_id.in_(closed_pids)
    )
    
    if plant_param:
        from app.infrastructure.database.models.models import Plant, Department
        if plant_param.isdigit():
            plant_obj = Plant.query.filter_by(id=int(plant_param), org_id=user.org_id).first()
            pname = plant_obj.name if plant_obj else None
            if pname:
                query = query.join(Project, KnowledgeRepository.project_id == Project.id).filter(db.or_(
                    Project.plant.ilike(f"%{pname}%"),
                    Project.department.has(Department.plant_id == int(plant_param))
                ))
            else:
                query = query.join(Project, KnowledgeRepository.project_id == Project.id).filter(
                    Project.department.has(Department.plant_id == int(plant_param))
                )
        else:
            query = query.join(Project, KnowledgeRepository.project_id == Project.id).filter(db.or_(
                Project.plant.ilike(f"%{plant_param}%"),
                Project.department.has(Department.plant.has(Plant.name.ilike(f"%{plant_param}%")))
            ))

    if keyword:
        search_filter = f"%{keyword}%"
        query = query.filter(
            db.or_(
                KnowledgeRepository.title.ilike(search_filter),
                KnowledgeRepository.keywords.ilike(search_filter),
                KnowledgeRepository.problem_summary.ilike(search_filter),
                KnowledgeRepository.root_cause.ilike(search_filter)
            )
        )
    
    if dept_id:
        query = query.filter_by(department_id=int(dept_id))
    if category:
        query = query.filter_by(category=category)
    if date_from:
        query = query.filter(KnowledgeRepository.archived_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(KnowledgeRepository.archived_at <= datetime.strptime(date_to, '%Y-%m-%d'))
    
    # Paginate
    paginated = query.order_by(KnowledgeRepository.archived_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    results = []
    need_commit = False
    for r in paginated.items:
        kpi_val = r.kpi_improvement_pct or 0.0
        cost_val = r.cost_savings or 0.0
        if not kpi_val or not cost_val:
            calc_kpi, calc_sav = extract_project_kpi_and_savings(r.project_id, r.org_id)
            if not kpi_val and calc_kpi:
                kpi_val = calc_kpi
                r.kpi_improvement_pct = calc_kpi
                need_commit = True
            if not cost_val and calc_sav:
                cost_val = calc_sav
                r.cost_savings = calc_sav
                need_commit = True

        results.append({
            "id": r.id,
            "project_id": r.project_id,
            "title": r.title,
            "category": r.category,
            "department_name": (r.project_ref.department.name if r.project_ref and r.project_ref.department else None),
            "problem_summary": (r.problem_summary or (r.project_ref.description if r.project_ref else None) or ''),
            "kpi_improvement_pct": kpi_val,
            "cost_savings": cost_val,
            "archived_at": r.archived_at.isoformat() + "Z" if r.archived_at else None
        })
    if need_commit:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    return jsonify({
        "results": results,
        "total": paginated.total,
        "pages": paginated.pages,
        "current_page": page
    })

# ============================
# DETAIL VIEW
# ============================
# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: get_entry_detail (Lines 888-939)
# Reason: Unused repository entry detail. Frontend modal uses /search /list objects.
# ==============================================================================
# @repository_bp.route('/<int:entry_id>', methods=['GET'])
# @jwt_required()
# def get_entry_detail(entry_id):
#     """Full read-only detail view of an archived project."""
#     user = db.session.get(User, get_jwt_identity())
#     entry = KnowledgeRepository.query.filter_by(id=entry_id, org_id=user.org_id).first()
#     if not entry:
#         entry = KnowledgeRepository.query.filter_by(project_id=entry_id, org_id=user.org_id).first()
#     if not entry:
#         project = Project.query.filter_by(id=entry_id, org_id=user.org_id).first()
#         if project:
#             entry = auto_archive_project_to_repository(project.id, user.org_id)
#             db.session.commit()
#     if not entry:
#         return jsonify({"msg": "Repository entry not found"}), 404

#     # Get all stage data
#     workflows = ProjectWorkflow.query.filter_by(project_id=entry.project_id, org_id=user.org_id).all()
#     stages_data = {wf.stage_id: wf.data for wf in workflows}

#     kpi_val = entry.kpi_improvement_pct or 0.0
#     cost_val = entry.cost_savings or 0.0
#     if not kpi_val or not cost_val:
#         calc_kpi, calc_sav = extract_project_kpi_and_savings(entry.project_id, user.org_id)
#         if not kpi_val and calc_kpi:
#             kpi_val = calc_kpi
#             entry.kpi_improvement_pct = calc_kpi
#         if not cost_val and calc_sav:
#             cost_val = calc_sav
#             entry.cost_savings = calc_sav
#         if calc_kpi or calc_sav:
#             try:
#                 db.session.commit()
#             except Exception:
#                 db.session.rollback()

#     return jsonify({
#         "id": entry.id,
#         "project_id": entry.project_id,
#         "title": entry.title,
#         "category": entry.category,
#         "problem_summary": entry.problem_summary,
#         "root_cause": entry.root_cause,
#         "solution_summary": entry.solution_summary,
#         "kpi_improvement_pct": kpi_val,
#         "cost_savings": cost_val,
#         "sop_path": entry.sop_path,
#         "closure_report_path": entry.closure_report_path,
#         "tags": entry.tags,
#         "archived_at": entry.archived_at.isoformat() + "Z" if entry.archived_at else None,
#         "all_stages": stages_data
#     })
# [END DEAD CODE: get_entry_detail]


# ============================
# SOP LIBRARY
# ============================
# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: sop_library (Lines 944-970)
# Reason: Legacy SOP repository endpoint.
# ==============================================================================
# @repository_bp.route('/sop-library', methods=['GET'])
# @jwt_required()
# def sop_library():
#     """Searchable SOP index."""
#     user = db.session.get(User, get_jwt_identity())
#     query = KnowledgeRepository.query.filter_by(org_id=user.org_id)

#     dept_id = request.args.get('department_id')
#     if dept_id:
#         query = query.filter_by(department_id=int(dept_id))

#     entries = query.all()
#     from app.infrastructure.database.models.models import SOP
#     results = []
#     for e in entries:
#         sop = SOP.query.filter_by(project_id=e.project_id, org_id=user.org_id).first()
#         # Include if there is an active/approved database SOP OR a valid legacy file path
#         if (sop and sop.status in ['Active', 'Approved']) or (e.sop_path and e.sop_path != 'None'):
#             results.append({
#                 "id": e.id,
#                 "title": e.title,
#                 "category": e.category,
#                 "sop_path": e.sop_path if e.sop_path != 'None' else None,
#                 "department_id": e.department_id,
#                 "sop_id": sop.id if sop else None
#             })
#     return jsonify(results)
# [END DEAD CODE: sop_library]

