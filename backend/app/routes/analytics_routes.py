from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from ..models import Project, KPIMetric, db
from sqlalchemy import func
import sqlalchemy as sa

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard_data():
    from flask_jwt_extended import get_jwt_identity
    from ..models import User, Department, ProjectStageTracker, Stage7Impact, KnowledgeRepository
    from datetime import datetime, timedelta
    
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    
    org_id = user.org_id
    role = user.role.name if user.role else 'Team Member'

    # 1. Basic Totals (Org-scoped)
    total_projects = Project.query.filter_by(org_id=org_id).count()
    closed_projects = Project.query.filter_by(org_id=org_id, status='Closed').count()
    active_projects = total_projects - closed_projects
    
    # 2. Aggregated KPIs (Real data from Stage 7 or Repository)
    # Savings from Stage 7 Impact
    impact_savings = db.session.query(func.sum(Stage7Impact.cost_savings))\
        .filter(Stage7Impact.org_id == org_id).scalar() or 0.0
    # Add savings from Historical Knowledge Repo
    repo_savings = db.session.query(func.sum(KnowledgeRepository.cost_savings))\
        .filter(KnowledgeRepository.org_id == org_id).scalar() or 0.0
    total_savings = float(impact_savings) + float(repo_savings)
    
    # Avg Productivity Gain
    avg_prod_impact = db.session.query(func.avg(Stage7Impact.productivity_gain))\
        .filter(Stage7Impact.org_id == org_id).scalar() or 0.0
    
    # 3. Trends (Last 6 Months)
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    monthly_trend_query = db.session.query(
        func.to_char(Project.created_at, 'YYYY-MM').label('month'),
        func.count(Project.id).label('count')
    ).filter(Project.org_id == org_id, Project.created_at >= six_months_ago)\
     .group_by('month').order_by('month').all()
    
    trends = [{"month": row.month, "projects": row.count} for row in monthly_trend_query]
    
    # 4. Category Distribution
    cat_dist = db.session.query(Project.category, func.count(Project.id))\
        .filter(Project.org_id == org_id)\
        .group_by(Project.category).all()
    category_data = {cat if cat else "Uncategorized": count for cat, count in cat_dist}
    
    # 5. Department Distribution
    dept_dist = db.session.query(Department.name, func.count(Project.id))\
        .join(Project, Project.department_id == Department.id)\
        .filter(Project.org_id == org_id)\
        .group_by(Department.name).all()
    department_data = {name: count for name, count in dept_dist}

    # 6. Project Velocity (Avg days per completed stage)
    # Overall Velocity
    completed_stages = ProjectStageTracker.query.filter_by(org_id=org_id, status='Completed').all()
    total_days = 0.0
    vel_count = 0
    for s in completed_stages:
        if s.started_at and s.completed_at:
            total_days += (s.completed_at - s.started_at).days
            vel_count += 1
    avg_velocity = (total_days / vel_count) if vel_count > 0 else 0.0

    # Department-wise Velocity
    dept_velocity = db.session.query(
        Department.name,
        sa.func.avg(sa.func.extract('epoch', ProjectStageTracker.completed_at - ProjectStageTracker.started_at) / 86400.0)
    ).join(Project, Project.id == ProjectStageTracker.project_id)\
     .join(Department, Project.department_id == Department.id)\
     .filter(ProjectStageTracker.org_id == org_id, ProjectStageTracker.status == 'Completed')\
     .group_by(Department.name).all()
    
    dept_velocity_data = {name: round(float(avg), 1) for name, avg in dept_velocity if avg is not None}

    role_summary = {
        "total_projects": total_projects,
        "closed_projects": closed_projects,
        "active_projects": active_projects,
        "total_savings": total_savings,
        "avg_productivity": float(avg_prod_impact),
        "avg_velocity": round(avg_velocity, 1),
        "success_rate": round((closed_projects / total_projects * 100), 1) if total_projects > 0 else 0.0
    }

    if role == 'Admin':
        role_summary["user_count"] = User.query.filter_by(org_id=org_id).count()
        role_summary["department_count"] = Department.query.filter_by(org_id=org_id).count()
    
    # 7. Leaderboard (Top 5 by savings)
    top_projects_impact = db.session.query(
        Project.title, 
        Department.name.label('dept'), 
        Stage7Impact.cost_savings,
        Stage7Impact.kpi_improvement_pct
    ).join(Department, Project.department_id == Department.id)\
     .join(Stage7Impact, Project.id == Stage7Impact.project_id)\
     .filter(Project.org_id == org_id)\
     .order_by(Stage7Impact.cost_savings.desc()).limit(5).all()

    leaderboard = [{
        "title": p.title,
        "dept": p.dept,
        "savings": f"${p.cost_savings:,.0f}" if p.cost_savings else "$0",
        "improvement": f"{p.kpi_improvement_pct}%" if p.kpi_improvement_pct else "0%"
    } for p in top_projects_impact]

    return jsonify({
        "summary": role_summary,
        "trends": trends,
        "categories": category_data,
        "departments": department_data,
        "dept_velocity": dept_velocity_data,
        "leaderboard": leaderboard,
        "projects_exist": total_projects > 0
    }), 200

@analytics_bp.route('/qc-tools/<int:project_id>', methods=['GET'])
@jwt_required()
def get_qc_tool_data(project_id):
    # This would return data formatted for Chart.js
    return jsonify({
        "pareto": {
            "labels": ["Poor Quality", "Shipping Delay", "Machine Failure", "Worker Error"],
            "data": [45, 25, 15, 10]
        },
        "fishbone": {
            "Man": ["Lack of training", "Fatigue"],
            "Machine": ["Old hardware", "Poor calibration"],
            "Method": ["Vague SOPs"],
            "Material": ["Substandard raw goods"]
        }
    }), 200
