"""
Module 5: Impact & KPI Dashboard Routes
GET /api/dashboard/kpi-summary, /trends, /dept-comparison, /top-projects, /cost-variance
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import (
    User, Project, Stage4Solution, Stage6Implementation, Stage7Impact,
    Stage8Standardization, KPIMetric, KPIDashboardCache, Department, db
)
from datetime import datetime
from sqlalchemy import func

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/kpi-summary', methods=['GET'])
@jwt_required()
def kpi_summary():
    """Aggregated KPI summary from completed Stage 7 data."""
    user = User.query.get(get_jwt_identity())
    
    # Base query — only projects past Stage 7, strictly scoped to org
    query = Stage7Impact.query.join(Project).filter(Project.org_id == user.org_id)
    
    # Role-based filtering within the organization
    if user.role.name == 'Team Leader':
        query = query.filter(Project.department_id == user.department_id)
    elif user.role.name == 'Team Member':
        from app.models import ProjectMember
        my_projects = [pm.project_id for pm in ProjectMember.query.filter_by(user_id=user.id, org_id=user.org_id).all()]
        query = query.filter(Project.id.in_(my_projects))
    # Admin/Facilitator/Reviewer see all within their own org
    
    # Apply optional filters
    dept_id = request.args.get('department_id')
    category = request.args.get('category')
    if dept_id:
        query = query.filter(Project.department_id == int(dept_id))
    if category:
        query = query.filter(Project.category == category)
    
    impacts = query.all()
    
    total_savings = sum(i.cost_savings or 0 for i in impacts)
    total_productivity = sum(i.productivity_gain or 0 for i in impacts)
    avg_improvement = round(sum(i.kpi_improvement_pct or 0 for i in impacts) / max(len(impacts), 1), 1)
    
    # Pipeline count (scoped to org)
    pipeline = {}
    for stage in range(1, 9):
        pipeline[f"stage_{stage}"] = Project.query.filter_by(current_stage=stage, org_id=user.org_id).count()
    
    return jsonify({
        "total_cost_savings": total_savings,
        "productivity_gain": total_productivity,
        "quality_improvement": f"{avg_improvement}%",
        "total_projects_measured": len(impacts),
        "pipeline": pipeline
    })

@dashboard_bp.route('/trends', methods=['GET'])
@jwt_required()
def kpi_trends():
    """Monthly KPI growth trend data."""
    user = User.query.get(get_jwt_identity())
    impacts = Stage7Impact.query.join(Project).filter(
        Project.org_id == user.org_id,
        Project.status.in_(['In Progress', 'Closed'])
    ).all()
    
    monthly = {}
    for impact in impacts:
        month_key = impact.created_at.strftime('%Y-%m') if impact.created_at else 'Unknown'
        if month_key not in monthly:
            monthly[month_key] = {"savings": 0, "improvement": 0, "count": 0}
        monthly[month_key]["savings"] += impact.cost_savings or 0
        monthly[month_key]["improvement"] += impact.kpi_improvement_pct or 0
        monthly[month_key]["count"] += 1
    
    # Sort by month
    sorted_months = sorted(monthly.keys())
    trend_data = {
        "labels": sorted_months,
        "savings": [monthly[m]["savings"] for m in sorted_months],
        "improvement": [round(monthly[m]["improvement"] / max(monthly[m]["count"], 1), 1) for m in sorted_months]
    }
    
    return jsonify(trend_data)

@dashboard_bp.route('/dept-comparison', methods=['GET'])
@jwt_required()
def dept_comparison():
    """Department-wise KPI comparison."""
    user = User.query.get(get_jwt_identity())
    departments = Department.query.filter_by(org_id=user.org_id).all()
    result = []
    
    for dept in departments:
        impacts = Stage7Impact.query.join(Project).filter(
            Project.department_id == dept.id,
            Project.org_id == user.org_id
        ).all()
        total_savings = sum(i.cost_savings or 0 for i in impacts)
        avg_improvement = round(sum(i.kpi_improvement_pct or 0 for i in impacts) / max(len(impacts), 1), 1)
        project_count = Project.query.filter_by(department_id=dept.id, org_id=user.org_id).count()
        
        result.append({
            "department": dept.name,
            "dept_id": dept.id,
            "total_savings": total_savings,
            "avg_improvement": avg_improvement,
            "project_count": project_count
        })
    
    return jsonify(result)

@dashboard_bp.route('/top-projects', methods=['GET'])
@jwt_required()
def top_projects():
    """Top 5 projects by impact."""
    user = User.query.get(get_jwt_identity())
    impacts = Stage7Impact.query.join(Project).filter(
        Project.org_id == user.org_id
    ).order_by(
        Stage7Impact.cost_savings.desc().nullslast()
    ).limit(5).all()
    
    return jsonify([{
        "project_id": i.project_id,
        "title": i.project_ref.title if i.project_ref else "Unknown",
        "uid": i.project_ref.project_uid if i.project_ref else "",
        "cost_savings": i.cost_savings or 0,
        "kpi_improvement": i.kpi_improvement_pct or 0,
        "productivity_gain": i.productivity_gain or 0
    } for i in impacts])

@dashboard_bp.route('/cost-variance', methods=['GET'])
@jwt_required()
def cost_variance():
    """Cost variance analysis: estimated vs actual."""
    user = User.query.get(get_jwt_identity())
    proposals = Stage4Solution.query.filter_by(org_id=user.org_id).all()
    result = []
    
    for p in proposals:
        impl = Stage6Implementation.query.filter_by(project_id=p.project_id, org_id=user.org_id).first()
        project = Project.query.filter_by(id=p.project_id, org_id=user.org_id).first()
        
        estimated = p.budget_required or 0
        actual = impl.actual_cost if impl else 0
        variance = actual - estimated
        variance_pct = round((variance / estimated) * 100, 1) if estimated > 0 else 0
        
        result.append({
            "project_id": p.project_id,
            "title": project.title if project else "Unknown",
            "estimated_cost": estimated,
            "actual_cost": actual,
            "variance": variance,
            "variance_pct": variance_pct,
            "over_budget": actual > estimated
        })
    
    return jsonify(result)
