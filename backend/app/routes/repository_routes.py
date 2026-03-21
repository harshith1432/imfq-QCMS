"""
Module 6: Knowledge Repository Routes
GET /api/repository/search, /api/repository/<id>, /api/repository/archive
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import (
    User, Project, KnowledgeRepository, Stage3RCA, Stage7Impact,
    Stage8Standardization, ProjectWorkflow, AuditLog, db
)
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
    dept_id = request.args.get('department_id')
    status = request.args.get('status')
    stage = request.args.get('stage')
    category = request.args.get('category')
    
    query = Project.query.filter_by(org_id=user.org_id)
    
    if dept_id:
        query = query.filter_by(department_id=int(dept_id))
    if status:
        query = query.filter_by(status=status)
    if stage:
        query = query.filter_by(current_stage=int(stage))
    if category:
        query = query.filter_by(category=category)
        
    projects = query.order_by(Project.created_at.desc()).all()
    
    three_days_ago = datetime.utcnow() - timedelta(days=3)
    
    results = []
    total_count = len(projects)
    active_count = 0
    completed_count = 0
    stalled_count = 0
    
    for p in projects:
        # Efficiency from Stage 7 Impact
        impact = Stage7Impact.query.filter_by(project_id=p.id).first()
        efficiency = impact.kpi_improvement_pct if impact and impact.kpi_improvement_pct else 0
        
        # Detect stalled status (no activity in 3 days)
        # Check latest audit log for this project
        last_log = AuditLog.query.filter_by(project_id=p.id).order_by(AuditLog.created_at.desc()).first()
        last_activity = last_log.created_at if last_log else p.created_at
        
        is_stalled = False
        if p.status not in ['Closed', 'Archived'] and last_activity < three_days_ago:
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
        
    return jsonify({
        "stats": {
            "total": total_count,
            "active": active_count,
            "completed": completed_count,
            "stalled": stalled_count
        },
        "projects": results
    }), 200

# ============================
# AUTO-ARCHIVE ENGINE
# ============================
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
    
    # Extract data from all stages
    stage1 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=1, org_id=user.org_id).first()
    rca = Stage3RCA.query.filter_by(project_id=project_id, org_id=user.org_id).first()
    stage4 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=4, org_id=user.org_id).first()
    impact = Stage7Impact.query.filter_by(project_id=project_id, org_id=user.org_id).first()
    std = Stage8Standardization.query.filter_by(project_id=project_id, org_id=user.org_id).first()
    
    entry = KnowledgeRepository(
        project_id=project_id,
        org_id=user.org_id,
        title=project.title,
        department_id=project.department_id,
        category=project.category,
        problem_summary=stage1.data.get('problem_statement', '') if stage1 and stage1.data else '',
        root_cause=rca.root_cause_summary if rca else '',
        solution_summary=stage4.data.get('proposed_solution', '') if stage4 and stage4.data else '',
        kpi_improvement_pct=impact.kpi_improvement_pct if impact else 0,
        cost_savings=impact.cost_savings if impact else 0,
        sop_path=std.sop_url if std else None,
        closure_report_path=std.closure_report_path if std else None,
        tags=[project.category] if project.category else [],
        keywords=f"{project.title} {project.category or ''}",
        archived_at=datetime.utcnow()
    )
    db.session.add(entry)
    
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
    date_from = request.args.get('from')
    date_to = request.args.get('to')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 12))
    
    user = User.query.get(get_jwt_identity())
    query = KnowledgeRepository.query.filter_by(org_id=user.org_id)
    
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
    
    return jsonify({
        "results": [{
            "id": r.id,
            "project_id": r.project_id,
            "title": r.title,
            "category": r.category,
            "kpi_improvement_pct": r.kpi_improvement_pct,
            "cost_savings": r.cost_savings,
            "archived_at": r.archived_at.isoformat() + "Z" if r.archived_at else None
        } for r in paginated.items],
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
    entry = KnowledgeRepository.query.filter_by(id=entry_id, org_id=user.org_id).first_or_404()
    
    # Get all stage data
    workflows = ProjectWorkflow.query.filter_by(project_id=entry.project_id, org_id=user.org_id).all()
    stages_data = {wf.stage_id: wf.data for wf in workflows}
    
    return jsonify({
        "id": entry.id,
        "project_id": entry.project_id,
        "title": entry.title,
        "category": entry.category,
        "problem_summary": entry.problem_summary,
        "root_cause": entry.root_cause,
        "solution_summary": entry.solution_summary,
        "kpi_improvement_pct": entry.kpi_improvement_pct,
        "cost_savings": entry.cost_savings,
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
    query = KnowledgeRepository.query.filter(
        KnowledgeRepository.org_id == user.org_id,
        KnowledgeRepository.sop_path.isnot(None)
    )
    dept_id = request.args.get('department_id')
    if dept_id:
        query = query.filter_by(department_id=int(dept_id))
    
    entries = query.all()
    return jsonify([{
        "id": e.id,
        "title": e.title,
        "category": e.category,
        "sop_path": e.sop_path,
        "department_id": e.department_id
    } for e in entries])
