"""
Module 5: Impact & KPI Dashboard Routes
GET /api/dashboard/kpi-summary, /trends, /dept-comparison, /top-projects, /cost-variance
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.infrastructure.database.models.models import (
    User, Project, Stage4Solution, Stage6Implementation, Stage7Impact,
    Stage8Standardization, KPIMetric, KPIDashboardCache, Department, ProjectMeeting, db
)
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.orm import joinedload

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/kpi-summary', methods=['GET'])
@jwt_required()
def kpi_summary():
    """Aggregated KPI summary from completed Stage 7 data via single SQL aggregations with Tier 3 caching."""
    user = db.session.get(User, get_jwt_identity())
    if not user:
        return jsonify({"msg": "User not found"}), 404

    from app.domain.services.cache_service import CacheService

    role_name = user.role.name if user.role else 'User'
    dept_id = request.args.get('department_id')
    category = request.args.get('category')

    dept_int = None
    if dept_id:
        try:
            dept_int = int(dept_id)
        except ValueError:
            pass

    def _fetch_summary():
        query = Stage7Impact.query.join(Project).filter(Project.org_id == user.org_id)

        if role_name in ('Team Leader', 'Team Member'):
            query = query.filter(Project.department_id == user.department_id)

        if dept_int:
            query = query.filter(Project.department_id == dept_int)
        if category:
            query = query.filter(Project.category == category)

        agg = query.with_entities(
            func.coalesce(func.sum(Stage7Impact.cost_savings), 0),
            func.coalesce(func.sum(Stage7Impact.productivity_gain), 0),
            func.coalesce(func.avg(Stage7Impact.kpi_improvement_pct), 0.0),
            func.count(Stage7Impact.id)
        ).first()

        total_savings = float(agg[0] or 0)
        total_productivity = float(agg[1] or 0)
        avg_improvement = round(float(agg[2] or 0), 1)
        total_projects_measured = int(agg[3] or 0)

        # Batched stage counts via single SQL GROUP BY
        stage_counts = dict(
            db.session.query(Project.current_stage, func.count(Project.id))
            .filter(Project.org_id == user.org_id)
            .group_by(Project.current_stage)
            .all()
        )
        pipeline = {f"stage_{i}": stage_counts.get(i, 0) for i in range(1, 9)}

        return {
            "total_cost_savings": total_savings,
            "productivity_gain": total_productivity,
            "quality_improvement": f"{avg_improvement}%",
            "total_projects_measured": total_projects_measured,
            "pipeline": pipeline
        }

    cached_res = CacheService.get_dashboard_kpi_summary(
        org_id=user.org_id,
        role_name=role_name,
        dept_id=dept_int,
        category=category,
        fetcher_fn=_fetch_summary
    )

    return jsonify(cached_res)


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: kpi_trends (Lines 91-129)
# Reason: Unused legacy trend endpoint. Replaced by /analytics/drilldown.
# ==============================================================================
# @dashboard_bp.route('/trends', methods=['GET'])
# @jwt_required()
# def kpi_trends():
#     """Monthly KPI growth trend data."""
#     user = db.session.get(User, get_jwt_identity())
#     if not user:
#         return jsonify({"msg": "User not found"}), 404

#     impacts = (
#         db.session.query(
#             Stage7Impact.created_at,
#             func.coalesce(Stage7Impact.cost_savings, 0),
#             func.coalesce(Stage7Impact.kpi_improvement_pct, 0)
#         )
#         .join(Project, Stage7Impact.project_id == Project.id)
#         .filter(
#             Project.org_id == user.org_id,
#             Project.status.in_(['In Progress', 'Closed'])
#         )
#         .all()
#     )

#     monthly = {}
#     for created_at, savings, improvement in impacts:
#         month_key = created_at.strftime('%Y-%m') if created_at else 'Unknown'
#         if month_key not in monthly:
#             monthly[month_key] = {"savings": 0, "improvement": 0, "count": 0}
#         monthly[month_key]["savings"] += savings
#         monthly[month_key]["improvement"] += improvement
#         monthly[month_key]["count"] += 1

#     sorted_months = sorted(monthly.keys())
#     trend_data = {
#         "labels": sorted_months,
#         "savings": [monthly[m]["savings"] for m in sorted_months],
#         "improvement": [round(monthly[m]["improvement"] / max(monthly[m]["count"], 1), 1) for m in sorted_months]
#     }

#     return jsonify(trend_data)
# [END DEAD CODE: kpi_trends]



@dashboard_bp.route('/dept-comparison', methods=['GET'])
@jwt_required()
def dept_comparison():
    """Department-wise KPI comparison via batched SQL aggregations with Tier 3 caching."""
    user = db.session.get(User, get_jwt_identity())
    if not user:
        return jsonify({"msg": "User not found"}), 404

    from app.domain.services.cache_service import CacheService

    def _fetch_dept_comparison():
        departments = Department.query.filter_by(org_id=user.org_id).order_by(Department.name).all()

        # Batched impact stats grouped by department
        impact_rows = (
            db.session.query(
                Project.department_id,
                func.coalesce(func.sum(Stage7Impact.cost_savings), 0).label('total_savings'),
                func.coalesce(func.avg(Stage7Impact.kpi_improvement_pct), 0.0).label('avg_improvement')
            )
            .join(Stage7Impact, Stage7Impact.project_id == Project.id)
            .filter(Project.org_id == user.org_id)
            .group_by(Project.department_id)
            .all()
        )
        impact_map = {
            row[0]: {
                "total_savings": float(row[1] or 0),
                "avg_improvement": round(float(row[2] or 0), 1)
            }
            for row in impact_rows if row[0] is not None
        }

        # Batched project counts grouped by department
        proj_count_rows = (
            db.session.query(Project.department_id, func.count(Project.id))
            .filter(Project.org_id == user.org_id)
            .group_by(Project.department_id)
            .all()
        )
        proj_count_map = {row[0]: int(row[1] or 0) for row in proj_count_rows if row[0] is not None}

        result = []
        for dept in departments:
            imp = impact_map.get(dept.id, {"total_savings": 0.0, "avg_improvement": 0.0})
            p_count = proj_count_map.get(dept.id, 0)
            result.append({
                "department": dept.name,
                "dept_id": dept.id,
                "total_savings": imp["total_savings"],
                "avg_improvement": imp["avg_improvement"],
                "project_count": p_count
            })
        return result

    cached_res = CacheService.get_dept_comparison(org_id=user.org_id, fetcher_fn=_fetch_dept_comparison)
    return jsonify(cached_res)


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: top_projects (Lines 191-216)
# Reason: Unused top projects widget endpoint.
# ==============================================================================
# @dashboard_bp.route('/top-projects', methods=['GET'])
# @jwt_required()
# def top_projects():
#     """Top 5 projects by impact with eager loaded project references."""
#     user = db.session.get(User, get_jwt_identity())
#     if not user:
#         return jsonify({"msg": "User not found"}), 404

#     impacts = (
#         Stage7Impact.query
#         .options(joinedload(Stage7Impact.project_ref))
#         .join(Project, Stage7Impact.project_id == Project.id)
#         .filter(Project.org_id == user.org_id)
#         .order_by(Stage7Impact.cost_savings.desc().nullslast())
#         .limit(5)
#         .all()
#     )

#     return jsonify([{
#         "project_id": i.project_id,
#         "title": i.project_ref.title if i.project_ref else "Unknown",
#         "uid": i.project_ref.project_uid if i.project_ref else "",
#         "cost_savings": i.cost_savings or 0,
#         "kpi_improvement": i.kpi_improvement_pct or 0,
#         "productivity_gain": i.productivity_gain or 0
#     } for i in impacts])
# [END DEAD CODE: top_projects]



# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: cost_variance (Lines 219-259)
# Reason: Unused cost variance widget.
# ==============================================================================
# @dashboard_bp.route('/cost-variance', methods=['GET'])
# @jwt_required()
# def cost_variance():
#     """Cost variance analysis: single joined query replacing N+1 sequential loops."""
#     user = db.session.get(User, get_jwt_identity())
#     if not user:
#         return jsonify({"msg": "User not found"}), 404

#     rows = (
#         db.session.query(
#             Stage8Standardization.project_id,
#             Project.title,
#             func.coalesce(Stage8Standardization.actual_cost, 0).label('actual_cost'),
#             func.coalesce(Stage8Standardization.cost_savings, 0).label('cost_savings')
#         )
#         .join(Project, Stage8Standardization.project_id == Project.id)
#         .filter(
#             Stage8Standardization.org_id == user.org_id,
#             Project.org_id == user.org_id
#         )
#         .all()
#     )

#     result = []
#     for project_id, title, actual, savings in rows:
#         actual_val = float(actual or 0)
#         estimated_val = float(savings or 0)
#         variance = actual_val - estimated_val
#         variance_pct = round((variance / estimated_val) * 100, 1) if estimated_val > 0 else 0

#         result.append({
#             "project_id": project_id,
#             "title": title or "Unknown",
#             "estimated_cost": estimated_val,
#             "actual_cost": actual_val,
#             "variance": variance,
#             "variance_pct": variance_pct,
#             "over_budget": actual_val > estimated_val
#         })

#     return jsonify(result)
# [END DEAD CODE: cost_variance]



@dashboard_bp.route('/activity', methods=['GET'])
@jwt_required()
def get_dashboard_activity():
    user = db.session.get(User, get_jwt_identity())
    if not user:
        return jsonify({"msg": "User not found"}), 404
    from app.infrastructure.database.models.models import AuditLog, Project

    query = (
        db.session.query(AuditLog, Project.title)
        .outerjoin(Project, AuditLog.project_id == Project.id)
        .options(joinedload(AuditLog.user))
        .filter(AuditLog.org_id == user.org_id)
    )

    role_name = user.role.name if user.role else 'User'
    if role_name in ('Team Leader', 'Team Member'):
        query = query.filter(db.or_(
            Project.team_leader_id == user.id,
            Project.creator_id == user.id,
            Project.members.any(id=user.id)
        ))
    elif role_name == 'Facilitator':
        query = query.filter(Project.facilitator_id == user.id)
    elif role_name == 'Reviewer':
        query = query.filter(Project.reviewer_id == user.id)

    results = query.order_by(AuditLog.created_at.desc()).limit(10).all()

    return jsonify([{
        "id": log.id,
        "project_id": log.project_id,
        "project_title": project_title or (log.details.get('project_title', "Unknown") if isinstance(log.details, dict) else "Unknown"),
        "action": log.action,
        "user_name": log.user.full_name or log.user.username if log.user else "System",
        "created_at": log.created_at.isoformat() + "Z" if log.created_at else None,
        "details": log.details
    } for log, project_title in results]), 200


@dashboard_bp.route('/meetings', methods=['GET'])
@jwt_required()
def get_dashboard_meetings():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user:
        user = User.query.filter_by(email=user_id).first()
        if not user:
            return jsonify({"msg": "User not found"}), 404

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user_is_sa = bool(user and user.role and user.role.name == 'SuperAdmin')

    # Base query for future meetings with eager loaded project
    query = (
        ProjectMeeting.query
        .options(joinedload(ProjectMeeting.project))
        .join(Project, ProjectMeeting.project_id == Project.id)
        .filter(ProjectMeeting.scheduled_at >= now)
    )
    if not user_is_sa:
        query = query.filter(Project.org_id == user.org_id)

    role_name = user.role.name if user.role else 'User'
    if role_name in ('Team Leader', 'Team Member'):
        query = query.filter(db.or_(
            Project.team_leader_id == user.id,
            Project.creator_id == user.id,
            Project.members.any(id=user.id)
        ))
    elif role_name == 'Facilitator':
        query = query.filter(Project.facilitator_id == user.id)
    elif role_name == 'Reviewer':
        query = query.filter(Project.reviewer_id == user.id)

    meetings = query.order_by(ProjectMeeting.scheduled_at.asc()).all()

    return jsonify([{
        "id": m.id,
        "project_id": m.project_id,
        "project_title": m.project.title if m.project else "Unknown",
        "stage_id": m.stage_id,
        "title": m.title,
        "scheduled_at": m.scheduled_at.isoformat() + "Z" if m.scheduled_at else None,
        "duration": m.duration,
        "duration_minutes": m.duration,
        "meeting_type": m.meeting_type,
        "url": m.url,
        "meeting_link": m.url
    } for m in meetings]), 200
