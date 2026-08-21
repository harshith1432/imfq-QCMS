"""
QCMS Employee Reward & Leaderboard System - Presentation Routes
REST APIs for points management, leaderboard rankings, employee history, and admin analytics.
"""

from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from app import db
from app.infrastructure.database.models.models import User, Organization, Department, Project, EmployeePoints, EmployeeLeaderboard
from app.domain.services.point_engine_service import PointEngineService, POINT_RULES
from app.presentation.middleware.middleware import role_required
from app.utils.avatar_utils import get_profile_picture_url

points_bp = Blueprint('points', __name__)


# ─── 1. POST /api/points/add ──────────────────────────────────────────────────
@points_bp.route('/points/add', methods=['POST'])
@jwt_required()
def add_points():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404

    data = request.get_json() or {}
    employee_id = data.get('employee_id') or current_user_id
    activity_type = data.get('activity_type')
    points = data.get('points')
    description = data.get('description')
    ref_id = data.get('activity_reference_id') or data.get('ref_id')
    project_id = data.get('project_id')

    if not activity_type:
        return jsonify({"message": "activity_type is required"}), 400

    # Ensure security — non-admins can only earn points for themselves unless triggered by system
    if employee_id != current_user_id and current_user.role.name not in ['Admin', 'SuperAdmin', 'CEO', 'Team Leader']:
        return jsonify({"message": "Unauthorized to award points to other employees"}), 433

    res = PointEngineService.award_points(
        employee_id=int(employee_id),
        org_id=current_user.org_id,
        activity_type=activity_type,
        points=points,
        description=description,
        ref_id=ref_id,
        project_id=project_id,
        created_by=current_user_id
    )

    if not res:
        return jsonify({"message": "Failed to award points"}), 400

    if res.get("status") == "duplicate":
        return jsonify({
            "message": "Duplicate points transaction blocked",
            "earned_points": 0,
            "duplicate": True
        }), 200

    return jsonify({
        "message": f"+{res['earned_points']} Points Earned!",
        "earned_points": res['earned_points'],
        "total_points": res['total_points'],
        "badge": res['badge'],
        "badge_upgraded": res['badge_upgraded'],
        "description": res['description']
    }), 201


# ─── 2. GET /api/points/history ──────────────────────────────────────────────
@points_bp.route('/points/history', methods=['GET'])
@jwt_required()
def get_points_history():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404

    # Allow querying specific employee_id within the same organization, defaults to current_user_id
    target_emp_id = request.args.get('employee_id', type=int)
    if target_emp_id:
        target_user = db.session.get(User, target_emp_id)
        if not target_user or target_user.org_id != current_user.org_id:
            return jsonify({"message": "Employee not found in organization"}), 404
        emp_id = target_emp_id
    else:
        emp_id = current_user_id

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 15, type=int)

    query = EmployeePoints.query.filter_by(
        employee_id=emp_id,
        organization_id=current_user.org_id
    ).order_by(EmployeePoints.created_at.desc())

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        "items": [{
            "id": p.id,
            "activity_type": p.activity_type,
            "points": p.points,
            "description": p.description,
            "project_id": p.project_id,
            "project_title": p.project.title if p.project else None,
            "created_at": p.created_at.isoformat() + "Z" if p.created_at else None
        } for p in items],
        "total": total,
        "page": page,
        "per_page": per_page
    }), 200


# ─── 3. GET /api/leaderboard ──────────────────────────────────────────────────
@points_bp.route('/leaderboard', methods=['GET'])
@jwt_required()
def get_leaderboard():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404

    # Ensure leaderboard is initialized for this organization
    PointEngineService.seed_initial_points_if_needed(current_user.org_id)

    search_q = (request.args.get('q') or '').strip()
    dept_id = request.args.get('department_id', type=int)
    plant_param = (request.args.get('plant') or request.args.get('plant_name') or request.args.get('plant_id') or '').strip()
    role_param = (request.args.get('role') or request.args.get('role_name') or '').strip()
    time_filter = request.args.get('period', 'all')  # 'all', 'monthly', 'yearly'
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 5, type=int)
    if page < 1: page = 1
    if per_page < 1 or per_page > 100: per_page = 5

    query = db.session.query(EmployeeLeaderboard)\
        .join(User, User.id == EmployeeLeaderboard.employee_id)\
        .outerjoin(Department, User.department_id == Department.id)\
        .filter(EmployeeLeaderboard.organization_id == current_user.org_id)

    if plant_param:
        from app.infrastructure.database.models.models import Plant
        if plant_param.isdigit():
            query = query.filter(db.or_(getattr(User, 'plant_id', None) == int(plant_param), Department.plant_id == int(plant_param)))
        else:
            query = query.outerjoin(Plant, getattr(User, 'plant_id', None) == Plant.id).filter(db.or_(
                Plant.name.ilike(f"%{plant_param}%"),
                Department.plant.has(Plant.name.ilike(f"%{plant_param}%"))
            ))

    if dept_id:
        query = query.filter(User.department_id == dept_id)

    if role_param:
        from app.infrastructure.database.models.models import Role
        query = query.join(Role, User.role_id == Role.id).filter(Role.name.ilike(f"%{role_param}%"))

    if search_q:
        pattern = f"%{search_q}%"
        query = query.filter(
            db.or_(
                User.username.ilike(pattern),
                User.full_name.ilike(pattern),
                Department.name.ilike(pattern)
            )
        )

    # Order using exact tie-breaking specification
    query = query.order_by(
        EmployeeLeaderboard.total_points.desc(),
        EmployeeLeaderboard.projects_completed.desc(),
        EmployeeLeaderboard.ideas_approved.desc(),
        EmployeeLeaderboard.knowledge_articles.desc(),
        User.created_at.asc()
    )

    results = query.all()
    full_leaderboard = []

    for rank, lb in enumerate(results, start=1):
        u = lb.employee
        if not u:
            continue
        full_leaderboard.append({
            "rank": rank,
            "employee_id": u.id,
            "name": u.full_name or u.username,
            "username": u.username,
            "email": u.email,
            "avatar": get_profile_picture_url(u),
            "department": u.dept.name if u.dept else "General",
            "plant": u.plant.name if getattr(u, 'plant', None) else (u.dept.plant.name if u.dept and u.dept.plant else "Main Plant"),
            "role": u.role.name if u.role else "Team Member",
            "total_points": lb.total_points,
            "badge": lb.badges or PointEngineService.get_badge_for_points(lb.total_points),
            "projects_completed": lb.projects_completed,
            "projects_created": lb.projects_created,
            "ideas_submitted": lb.ideas_submitted,
            "ideas_approved": lb.ideas_approved,
            "knowledge_articles": lb.knowledge_articles,
            "meetings_attended": lb.meetings_attended
        })

    import math
    total_count = len(full_leaderboard)
    total_pages = math.ceil(total_count / per_page) if total_count > 0 else 1
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paged_leaderboard = full_leaderboard[start_idx:end_idx]

    # Find current user's entry and Top 3 podium from full ranked list
    my_entry = next((e for e in full_leaderboard if e['employee_id'] == current_user_id), None)
    podium = full_leaderboard[:3]

    # Compute Comprehensive Champions Summary (Overall, Plant-Level, Department-Level, Role-Level)
    all_org_entries = db.session.query(EmployeeLeaderboard)\
        .join(User, User.id == EmployeeLeaderboard.employee_id)\
        .outerjoin(Department, User.department_id == Department.id)\
        .filter(EmployeeLeaderboard.organization_id == current_user.org_id)\
        .order_by(
            EmployeeLeaderboard.total_points.desc(),
            EmployeeLeaderboard.projects_completed.desc(),
            EmployeeLeaderboard.ideas_approved.desc(),
            EmployeeLeaderboard.knowledge_articles.desc(),
            User.created_at.asc()
        ).all()

    overall_champ = None
    plant_champs_dict = {}
    dept_champs_dict = {}
    role_champs_dict = {}

    for rank_i, lb_item in enumerate(all_org_entries, start=1):
        u_item = lb_item.employee
        if not u_item:
            continue
        p_name = u_item.plant.name if getattr(u_item, 'plant', None) else (u_item.dept.plant.name if u_item.dept and u_item.dept.plant else '')
        d_name = u_item.dept.name if u_item.dept else ''
        r_name = u_item.role.name if u_item.role else 'Team Member'
        
        u_summary = {
            "rank": rank_i,
            "employee_id": u_item.id,
            "name": u_item.full_name or u_item.username,
            "username": u_item.username,
            "avatar": get_profile_picture_url(u_item),
            "department": d_name or "General",
            "plant": p_name or "Main Plant",
            "role": r_name,
            "total_points": lb_item.total_points,
            "badge": lb_item.badges or PointEngineService.get_badge_for_points(lb_item.total_points),
            "projects_completed": lb_item.projects_completed
        }
        
        if overall_champ is None:
            overall_champ = u_summary
            
        if p_name and p_name not in plant_champs_dict:
            plant_champs_dict[p_name] = u_summary
            
        if d_name and d_name not in dept_champs_dict:
            dept_champs_dict[d_name] = u_summary
            
        EXCLUDED_ROLE_CHAMPS = {'admin', 'ceo', 'superadmin', 'system admin', 'administrator'}
        if r_name and r_name.strip().lower() not in EXCLUDED_ROLE_CHAMPS and r_name not in role_champs_dict:
            role_champs_dict[r_name] = u_summary

    champions_summary = {
        "overall": overall_champ,
        "plants": [{"plant_name": k, "champion": v} for k, v in plant_champs_dict.items()],
        "departments": [{"department_name": k, "champion": v} for k, v in dept_champs_dict.items()],
        "roles": [{"role_name": k, "champion": v} for k, v in role_champs_dict.items()]
    }

    return jsonify({
        "status": "success",
        "leaderboard": paged_leaderboard,
        "podium": podium,
        "champions_summary": champions_summary,
        "my_summary": my_entry or {
            "rank": "-",
            "total_points": 0,
            "badge": "Newbie",
            "projects_completed": 0
        },
        "pagination": {
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "pages": total_pages
        }
    }), 200


# ─── 4. GET /api/employee/<id>/points ─────────────────────────────────────────
@points_bp.route('/employee/<int:emp_id>/points', methods=['GET'])
@jwt_required()
def get_employee_points_summary(emp_id):
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404

    emp = db.session.get(User, emp_id)
    if not emp or emp.org_id != current_user.org_id:
        return jsonify({"message": "Employee not found"}), 404

    lb = EmployeeLeaderboard.query.filter_by(employee_id=emp_id).first()
    if not lb:
        PointEngineService.sync_employee_metrics(emp_id, current_user.org_id)
        lb = EmployeeLeaderboard.query.filter_by(employee_id=emp_id).first()

    pts = lb.total_points if lb else 0
    badge = PointEngineService.get_badge_for_points(pts)

    # Next Badge Threshold Calculation
    next_badge = None
    next_threshold = 100
    for thresh, b_name in sorted(PointEngineService.get_badge_thresholds_list(), key=lambda x: x[0]):
        if pts < thresh:
            next_badge = b_name
            next_threshold = thresh
            break

    points_to_next = max(0, next_threshold - pts) if next_badge else 0
    progress_pct = min(100, round((pts / next_threshold) * 100, 1)) if next_threshold > 0 else 100

    # Recent activities (last 10)
    recent = EmployeePoints.query.filter_by(employee_id=emp_id)\
        .order_by(EmployeePoints.created_at.desc()).limit(10).all()

    return jsonify({
        "employee": {
            "id": emp.id,
            "name": emp.full_name or emp.username,
            "avatar": get_profile_picture_url(emp),
            "department": emp.dept.name if emp.dept else "General",
            "role": emp.role.name if emp.role else "Member"
        },
        "metrics": {
            "total_points": pts,
            "rank": lb.rank if lb else 0,
            "badge": badge,
            "next_badge": next_badge,
            "next_threshold": next_threshold,
            "points_to_next": points_to_next,
            "progress_pct": progress_pct,
            "projects_completed": lb.projects_completed if lb else 0,
            "projects_created": lb.projects_created if lb else 0,
            "ideas_submitted": lb.ideas_submitted if lb else 0,
            "ideas_approved": lb.ideas_approved if lb else 0,
            "knowledge_articles": lb.knowledge_articles if lb else 0
        },
        "recent_activities": [{
            "id": r.id,
            "activity_type": r.activity_type,
            "points": r.points,
            "description": r.description,
            "created_at": r.created_at.isoformat() + "Z" if r.created_at else None
        } for r in recent]
    }), 200


# ─── 5. GET /api/points/admin-analytics ──────────────────────────────────────
@points_bp.route('/points/admin-analytics', methods=['GET'])
@jwt_required()
@role_required(['Admin', 'SuperAdmin', 'CEO', 'Team Leader'])
def get_points_admin_analytics():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404

    org_id = current_user.org_id

    # Department-wise total points ranking
    dept_rankings = db.session.query(
        Department.name.label('department'),
        func.sum(EmployeeLeaderboard.total_points).label('dept_points'),
        func.count(EmployeeLeaderboard.id).label('member_count')
    ).join(User, User.id == EmployeeLeaderboard.employee_id)\
     .join(Department, Department.id == User.department_id)\
     .filter(EmployeeLeaderboard.organization_id == org_id)\
     .group_by(Department.name)\
     .order_by(func.sum(EmployeeLeaderboard.total_points).desc()).all()

    # Most Active Facilitators
    active_facilitators = db.session.query(
        User.id, User.full_name, User.username,
        func.count(Project.id).label('project_count')
    ).join(Project, Project.facilitator_id == User.id)\
     .filter(Project.org_id == org_id)\
     .group_by(User.id, User.full_name, User.username)\
     .order_by(func.count(Project.id).desc()).limit(5).all()

    # Most Active Team Leaders
    active_leaders = db.session.query(
        User.id, User.full_name, User.username,
        func.count(Project.id).label('project_count')
    ).join(Project, Project.team_leader_id == User.id)\
     .filter(Project.org_id == org_id)\
     .group_by(User.id, User.full_name, User.username)\
     .order_by(func.count(Project.id).desc()).limit(5).all()

    return jsonify({
        "department_rankings": [{
            "department": d.department,
            "points": int(d.dept_points or 0),
            "members": int(d.member_count or 0)
        } for d in dept_rankings],
        "active_facilitators": [{
            "id": f.id,
            "name": f.full_name or f.username,
            "projects": f.project_count
        } for f in active_facilitators],
        "active_leaders": [{
            "id": l.id,
            "name": l.full_name or l.username,
            "projects": l.project_count
        } for l in active_leaders]
    }), 200


# Helper method on Service for Threshold List
PointEngineService.get_badge_thresholds_list = staticmethod(lambda: [
    (10000, "Quality Champion"),
    (5000, "Diamond"),
    (3000, "Platinum"),
    (1500, "Gold"),
    (700, "Silver"),
    (300, "Bronze"),
    (100, "Beginner"),
    (0, "Newbie")
])
