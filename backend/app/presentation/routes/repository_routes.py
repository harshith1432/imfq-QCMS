"""
Module 6: Knowledge Repository Routes
GET /api/repository/search, /api/repository/<id>, /api/repository/archive
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.infrastructure.database.models.models import (
    User, Project, KnowledgeRepository, Stage3RCA, Stage7Impact,
    Stage8Standardization, ProjectWorkflow, AuditLog,
    Stage7PerformanceVerificationBenefitsRealization as Stage7Verification
)
from app import db
from datetime import datetime, timedelta
from functools import wraps

repository_bp = Blueprint('repository', __name__)

def admin_required(f):
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        user = User.query.get(get_jwt_identity())
        if not user or user.role.name != 'Admin':
            return jsonify({"msg": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated

# ============================
# PROJECT REPOSITORY MASTER LIST
# ============================
@repository_bp.route('/list', methods=['GET'])
@jwt_required()
def list_repository_projects():
    """Real-time project repository for all roles with stats and health metrics."""
    user = User.query.get(get_jwt_identity())
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

    if status:
        if status == 'Active':
            query = query.filter(~Project.status.in_(['Closed', 'Completed', 'Archived', 'Rejected', 'On Hold', 'Cancelled']))
        elif status in ['Closed', 'Completed']:
            query = query.filter(Project.status.in_(['Closed', 'Completed', 'Archived']))
        elif status in ['Inactive', 'Stalled']:
            three_days_ago = datetime.utcnow() - timedelta(days=3)
            recent_active_pids = db.session.query(AuditLog.project_id).filter(
                AuditLog.created_at >= three_days_ago,
                AuditLog.project_id.isnot(None)
            ).subquery()
            query = query.filter(
                ~Project.status.in_(['Closed', 'Completed', 'Archived']),
                db.or_(
                    Project.created_at < three_days_ago,
                    ~Project.id.in_(recent_active_pids)
                )
            )
        elif status == 'Pending Approval':
            query = query.filter(db.or_(
                Project.status.ilike('%Pending%'),
                Project.status.ilike('%Submitted%')
            ))
        else:
            query = query.filter_by(status=status)

    if stage and str(stage).isdigit():
        query = query.filter_by(current_stage=int(stage))

    if category:
        query = query.filter_by(category=category)
        
    projects = query.order_by(Project.created_at.desc()).all()
    
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    
    results = []
    total_count = len(projects)
    active_count = 0
    completed_count = 0
    stalled_count = 0
    
    for p in projects:
        # Efficiency: read real KPI improvement % from Stage 7 before_vs_after data
        efficiency = 0
        s7_verify = Stage7Verification.query.filter_by(project_id=p.id).first()
        if s7_verify and s7_verify.before_vs_after:
            try:
                rows = s7_verify.before_vs_after if isinstance(s7_verify.before_vs_after, list) else []
                pcts = [float(r.get('improvement_pct', 0) or 0) for r in rows if r.get('improvement_pct') not in (None, '', 'N/A')]
                if pcts:
                    efficiency = round(sum(pcts) / len(pcts), 1)
            except Exception:
                pass
        # Fallback: use Stage 8 closure kpi_improvement_pct if Stage 7 data unavailable
        if efficiency == 0:
            impact = Stage7Impact.query.filter_by(project_id=p.id).first()
            if impact and impact.kpi_improvement_pct:
                efficiency = round(float(impact.kpi_improvement_pct), 1)
        
        # Detect stalled/inactive status: no AuditLog activity in 7 days
        last_log = AuditLog.query.filter_by(project_id=p.id).order_by(AuditLog.created_at.desc()).first()
        last_activity = last_log.created_at if last_log else p.created_at
        
        is_stalled = False
        if p.status not in ['Closed', 'Archived', 'Completed'] and last_activity and last_activity < seven_days_ago:
            is_stalled = True
            stalled_count += 1
            
        if p.status == 'Closed' or p.status == 'Archived':
            completed_count += 1
        else:
            active_count += 1
            
        results.append({
            "id": p.id,
            "project_uid": p.project_uid,
            "title": p.title,
            "category": p.category,
            "department": p.department.name if p.department else "N/A",
            "team_leader": p.team_leader.full_name if p.team_leader else "N/A",
            "current_stage": p.current_stage,
            "progress": round((p.current_stage / 8) * 100),
            "efficiency": efficiency,
            "status": p.status,
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
                "total": total_count,
                "active": active_count,
                "completed": completed_count,
                "stalled": stalled_count
            },
            "page": page,
            "per_page": per_page,
            "total": total_items,
            "total_pages": total_pages,
            "projects": paginated_projects
        }), 200
        
    return jsonify({
        "stats": {
            "total": total_count,
            "active": active_count,
            "completed": completed_count,
            "stalled": stalled_count
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
        from app.infrastructure.database.models.models import Stage1ProblemDefinitionProjectInitiation
        stage1 = Stage1ProblemDefinitionProjectInitiation.query.filter_by(project_id=project_id, org_id=org_id).first()
        if stage1:
            prob_sum = stage1.data.get('problem_statement', '') if stage1.data else ''
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
        from app.infrastructure.database.models.models import Stage3RCA
        rca = Stage3RCA.query.filter_by(project_id=project_id, org_id=org_id).first()
        if rca and hasattr(rca, 'root_cause_summary'):
            root_cause_val = rca.root_cause_summary or ''
            
    # 3. Solution summary (Stage 5)
    wf5 = workflows.get(5, {})
    sol_sum = ""
    if wf5:
        sol_list = wf5.get('root_cause_mapping', [])
        if isinstance(sol_list, list):
            sol_sum = "; ".join([s.get('proposed_solution', '') for s in sol_list if isinstance(s, dict) and s.get('proposed_solution')])
    if not sol_sum:
        from app.infrastructure.database.models.models import Stage5CountermeasurePlanningSolutionDevelopment
        stage4 = Stage5CountermeasurePlanningSolutionDevelopment.query.filter_by(project_id=project_id, org_id=org_id).first()
        if stage4:
            if hasattr(stage4, 'data') and isinstance(stage4.data, dict):
                sol_sum = stage4.data.get('proposed_solution', '')
            elif getattr(stage4, 'solution_brainstorming', None) and isinstance(stage4.solution_brainstorming, list):
                sol_sum = "; ".join([s.get('solution', '') for s in stage4.solution_brainstorming if isinstance(s, dict) and s.get('solution')])
            
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
                
    entry = KnowledgeRepository(
        project_id=project_id,
        org_id=org_id,
        title=project.title,
        department_id=project.department_id,
        category=project.category,
        problem_summary=prob_sum or '',
        root_cause=root_cause_val or '',
        solution_summary=sol_sum or '',
        kpi_improvement_pct=kpi_imp,
        cost_savings=cost_sav,
        sop_path=sop_url,
        closure_report_path=closure_report,
        tags=[project.category] if project.category else [],
        keywords=f"{project.title} {project.category or ''}",
        archived_at=datetime.utcnow()
    )
    db.session.add(entry)
    db.session.flush()
    
    # Try generating embedding
    try:
        from app.infrastructure.vector_db.vector_ingest import get_embedding_model
        model = get_embedding_model()
        content = f"Title: {entry.title or ''}\n"
        content += f"Category: {entry.category or ''}\n"
        content += f"Problem: {entry.problem_summary or ''}\n"
        content += f"Root Cause: {entry.root_cause or ''}\n"
        content += f"Solution: {entry.solution_summary or ''}\n"
        content += f"Keywords: {entry.keywords or ''}"
        entry.embedding = model.encode(content).tolist()
    except Exception as e:
        print(f"[RAG] Vector encoding skipped or failed during auto-archive: {e}")
        
    return entry

@repository_bp.route('/archive/<int:project_id>', methods=['POST'])
@admin_required
def archive_project(project_id):
    """Admin-triggered archive of a closed project into knowledge repository."""
    user = User.query.get(get_jwt_identity())
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
    
    user = User.query.get(get_jwt_identity())

    # 1. Clean up KnowledgeRepository table: Remove entries for projects that are NOT Closed/Completed/Archived
    open_project_ids = [p.id for p in Project.query.filter(
        Project.org_id == user.org_id,
        ~Project.status.in_(['Closed', 'Completed', 'Archived'])
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
        Project.status.in_(['Closed', 'Completed', 'Archived'])
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

    query = KnowledgeRepository.query.filter(
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
@repository_bp.route('/<int:entry_id>', methods=['GET'])
@jwt_required()
def get_entry_detail(entry_id):
    """Full read-only detail view of an archived project."""
    user = User.query.get(get_jwt_identity())
    entry = KnowledgeRepository.query.filter_by(id=entry_id, org_id=user.org_id).first()
    if not entry:
        entry = KnowledgeRepository.query.filter_by(project_id=entry_id, org_id=user.org_id).first()
    if not entry:
        project = Project.query.filter_by(id=entry_id, org_id=user.org_id).first()
        if project:
            entry = auto_archive_project_to_repository(project.id, user.org_id)
            db.session.commit()
    if not entry:
        return jsonify({"msg": "Repository entry not found"}), 404
    
    # Get all stage data
    workflows = ProjectWorkflow.query.filter_by(project_id=entry.project_id, org_id=user.org_id).all()
    stages_data = {wf.stage_id: wf.data for wf in workflows}

    kpi_val = entry.kpi_improvement_pct or 0.0
    cost_val = entry.cost_savings or 0.0
    if not kpi_val or not cost_val:
        calc_kpi, calc_sav = extract_project_kpi_and_savings(entry.project_id, user.org_id)
        if not kpi_val and calc_kpi:
            kpi_val = calc_kpi
            entry.kpi_improvement_pct = calc_kpi
        if not cost_val and calc_sav:
            cost_val = calc_sav
            entry.cost_savings = calc_sav
        if calc_kpi or calc_sav:
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
    
    return jsonify({
        "id": entry.id,
        "project_id": entry.project_id,
        "title": entry.title,
        "category": entry.category,
        "problem_summary": entry.problem_summary,
        "root_cause": entry.root_cause,
        "solution_summary": entry.solution_summary,
        "kpi_improvement_pct": kpi_val,
        "cost_savings": cost_val,
        "sop_path": entry.sop_path,
        "closure_report_path": entry.closure_report_path,
        "tags": entry.tags,
        "archived_at": entry.archived_at.isoformat() + "Z" if entry.archived_at else None,
        "all_stages": stages_data
    })

# ============================
# SOP LIBRARY
# ============================
@repository_bp.route('/sop-library', methods=['GET'])
@jwt_required()
def sop_library():
    """Searchable SOP index."""
    user = User.query.get(get_jwt_identity())
    query = KnowledgeRepository.query.filter_by(org_id=user.org_id)
    
    dept_id = request.args.get('department_id')
    if dept_id:
        query = query.filter_by(department_id=int(dept_id))
    
    entries = query.all()
    from app.infrastructure.database.models.models import SOP
    results = []
    for e in entries:
        sop = SOP.query.filter_by(project_id=e.project_id, org_id=user.org_id).first()
        # Include if there is an active/approved database SOP OR a valid legacy file path
        if (sop and sop.status in ['Active', 'Approved']) or (e.sop_path and e.sop_path != 'None'):
            results.append({
                "id": e.id,
                "title": e.title,
                "category": e.category,
                "sop_path": e.sop_path if e.sop_path != 'None' else None,
                "department_id": e.department_id,
                "sop_id": sop.id if sop else None
            })
    return jsonify(results)
