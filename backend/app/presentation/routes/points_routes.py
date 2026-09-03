"""
QCMS Employee Reward & Leaderboard System - Presentation Routes
REST APIs for points management, leaderboard rankings, employee history, and admin analytics.
"""

from datetime import datetime, timedelta, timezone
import csv
import io
from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from app import db
from app.infrastructure.database.models.models import User, Organization, Department, Project, EmployeePoints, EmployeeLeaderboard
from app.domain.services.point_engine_service import PointEngineService, POINT_RULES
from app.presentation.middleware.middleware import role_required
from app.utils.avatar_utils import get_profile_picture_url

points_bp = Blueprint('points', __name__)


# ─── 1. POST /api/points/add ──────────────────────────────────────────────────
# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: add_points (Lines 22-73)
# Reason: Manual points injection endpoint. Points are computed automatically by point_engine_service on stage approvals.
# ==============================================================================
# @points_bp.route('/points/add', methods=['POST'])
# @jwt_required()
# def add_points():
#     current_user_id = get_jwt_identity()
#     current_user = db.session.get(User, current_user_id)
#     if not current_user:
#         return jsonify({"message": "User not found"}), 404

#     data = request.get_json() or {}
#     employee_id = data.get('employee_id') or current_user_id
#     activity_type = data.get('activity_type')
#     points = data.get('points')
#     description = data.get('description')
#     ref_id = data.get('activity_reference_id') or data.get('ref_id')
#     project_id = data.get('project_id')

#     if not activity_type:
#         return jsonify({"message": "activity_type is required"}), 400

#     # Ensure security — non-admins can only earn points for themselves unless triggered by system
#     if employee_id != current_user_id and current_user.role.name not in ['Admin', 'SuperAdmin', 'CEO', 'Team Leader']:
#         return jsonify({"message": "Unauthorized to award points to other employees"}), 433

#     res = PointEngineService.award_points(
#         employee_id=int(employee_id),
#         org_id=current_user.org_id,
#         activity_type=activity_type,
#         points=points,
#         description=description,
#         ref_id=ref_id,
#         project_id=project_id,
#         created_by=current_user_id
#     )

#     if not res:
#         return jsonify({"message": "Failed to award points"}), 400

#     if res.get("status") == "duplicate":
#         return jsonify({
#             "message": "Duplicate points transaction blocked",
#             "earned_points": 0,
#             "duplicate": True
#         }), 200

#     return jsonify({
#         "message": f"+{res['earned_points']} Points Earned!",
#         "earned_points": res['earned_points'],
#         "total_points": res['total_points'],
#         "badge": res['badge'],
#         "badge_upgraded": res['badge_upgraded'],
#         "description": res['description']
#     }), 201
# [END DEAD CODE: add_points]



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

    is_superadmin = bool(current_user.role and current_user.role.name and current_user.role.name.lower() in ('superadmin', 'system admin', 'system administrator'))
    req_org = request.args.get('org_id', type=int)

    org_id = None
    if req_org:
        org_id = req_org
    elif not is_superadmin:
        org_id = current_user.org_id
    elif current_user.org_id:
        org_id = current_user.org_id

    # Ensure leaderboard is initialized
    PointEngineService.seed_initial_points_if_needed(org_id)

    search_q = (request.args.get('q') or '').strip()
    if search_q.lower() in ('undefined', 'null'): search_q = ''

    dept_id = request.args.get('department_id', type=int)
    plant_param = (request.args.get('plant') or request.args.get('plant_name') or request.args.get('plant_id') or '').strip()
    if plant_param.lower() in ('undefined', 'null'): plant_param = ''

    role_param = (request.args.get('role') or request.args.get('role_name') or '').strip()
    if role_param.lower() in ('undefined', 'null'): role_param = ''

    time_filter = request.args.get('period', 'all')  # 'all', 'monthly', 'yearly'
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 5, type=int)
    if page < 1: page = 1
    if per_page < 1 or per_page > 100: per_page = 5

    from app.infrastructure.database.models.models import Role
    
    query = db.session.query(EmployeeLeaderboard)\
        .join(User, User.id == EmployeeLeaderboard.employee_id)\
        .outerjoin(Role, User.role_id == Role.id)\
        .outerjoin(Department, User.department_id == Department.id)

    if org_id:
        query = query.filter(EmployeeLeaderboard.organization_id == org_id)

    # Filter out only platform administration / superadmin accounts so all organizational contributors appear
    query = query.filter(db.or_(
        Role.id == None,
        db.not_(Role.name.ilike('%superadmin%'))
    ))

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
        query = query.filter(Role.name.ilike(f"%{role_param}%"))

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
    all_org_query = db.session.query(EmployeeLeaderboard)\
        .join(User, User.id == EmployeeLeaderboard.employee_id)\
        .outerjoin(Role, User.role_id == Role.id)\
        .outerjoin(Department, User.department_id == Department.id)

    if org_id:
        all_org_query = all_org_query.filter(EmployeeLeaderboard.organization_id == org_id)

    all_org_entries = all_org_query.filter(db.or_(
        Role.id == None,
        db.not_(Role.name.ilike('%superadmin%'))
    )).order_by(
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
            "department_id": u_item.department_id,
            "plant": p_name or "Main Plant",
            "plant_id": getattr(u_item, 'plant_id', None) or (u_item.dept.plant_id if u_item.dept else None),
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
        "plants": [
            {
                "plant_id": v.get("plant_id") if v else None,
                "plant_name": k,
                "champion_name": v.get("name") if v else "N/A",
                "total_points": v.get("total_points", 0) if v else 0,
                "champion": v
            } for k, v in plant_champs_dict.items()
        ],
        "departments": [
            {
                "department_id": v.get("department_id") if v else None,
                "department_name": k,
                "champion_name": v.get("name") if v else "N/A",
                "total_points": v.get("total_points", 0) if v else 0,
                "champion": v
            } for k, v in dept_champs_dict.items()
        ],
        "roles": [
            {
                "role_name": k,
                "champion_name": v.get("name") if v else "N/A",
                "total_points": v.get("total_points", 0) if v else 0,
                "champion": v
            } for k, v in role_champs_dict.items()
        ]
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



# ─── 3b. GET /api/leaderboard/export & /api/points/leaderboard/export ─────────
@points_bp.route('/leaderboard/export', methods=['GET'])
@points_bp.route('/points/leaderboard/export', methods=['GET'])
@jwt_required()
def export_leaderboard():
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"message": "User not found"}), 404

    # Enforce strict access control: Only Organization Administrators can export
    user_role_name = (current_user.role.name if current_user.role else (getattr(current_user, 'role', None) or '')).strip()
    is_admin = user_role_name in ['Admin', 'SuperAdmin', 'admin', 'superadmin', 'Owner', 'owner', 'Organization Admin', 'CEO', 'ceo'] or getattr(current_user, 'is_super_admin', False)
    if not is_admin:
        return jsonify({"message": "Forbidden: Only Organization Administrators can export employee leaderboard rankings."}), 403

    search_q = (request.args.get('q') or '').strip()
    dept_id = request.args.get('department_id', type=int)
    plant_param = (request.args.get('plant') or request.args.get('plant_name') or request.args.get('plant_id') or '').strip()
    role_param = (request.args.get('role') or request.args.get('role_name') or '').strip()
    user_ids_param = (request.args.get('user_ids') or '').strip()
    limit = request.args.get('limit', 0, type=int)
    time_range = (request.args.get('time_range') or 'all').lower().strip()
    start_date_str = (request.args.get('start_date') or '').strip()
    end_date_str = (request.args.get('end_date') or '').strip()
    export_format = (request.args.get('format') or 'csv').lower()

    # Determine timeline date filters
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    filter_start = None
    filter_end = None
    timeline_label = "All Time (Lifetime)"

    try:
        if time_range == 'month' or time_range == 'this_month':
            filter_start = datetime(now.year, now.month, 1, 0, 0, 0)
            filter_end = now
            timeline_label = f"This Month ({now.strftime('%B %Y')})"
        elif time_range == 'last_month':
            first_this_month = datetime(now.year, now.month, 1)
            last_day_prev = first_this_month - timedelta(days=1)
            filter_start = datetime(last_day_prev.year, last_day_prev.month, 1, 0, 0, 0)
            filter_end = datetime(last_day_prev.year, last_day_prev.month, last_day_prev.day, 23, 59, 59)
            timeline_label = f"Last Month ({last_day_prev.strftime('%B %Y')})"
        elif time_range == 'quarter' or time_range == 'this_quarter':
            q_month = ((now.month - 1) // 3) * 3 + 1
            filter_start = datetime(now.year, q_month, 1, 0, 0, 0)
            filter_end = now
            q_num = (now.month - 1) // 3 + 1
            timeline_label = f"Q{q_num} {now.year} (Quarter to Date)"
        elif time_range == 'year' or time_range == 'this_year':
            filter_start = datetime(now.year, 1, 1, 0, 0, 0)
            filter_end = now
            timeline_label = f"Year {now.year} (YTD)"
        elif time_range == 'custom' or (start_date_str and end_date_str):
            if start_date_str:
                filter_start = datetime.strptime(start_date_str, "%Y-%m-%d")
            if end_date_str:
                filter_end = datetime.strptime(end_date_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            timeline_label = f"Custom Period ({start_date_str or 'Start'} to {end_date_str or 'Present'})"
    except Exception as e:
        filter_start = None
        filter_end = None
        timeline_label = "All Time"

    from app.infrastructure.database.models.models import Role, Plant
    from sqlalchemy import func

    # Calculate period points from EmployeePoints table if timeline is constrained
    period_points_map = {}
    if filter_start:
        pts_query = db.session.query(
            EmployeePoints.employee_id,
            func.sum(EmployeePoints.points).label('p_points'),
            func.count(db.case((EmployeePoints.activity_type.ilike('%PROJECT_COMPLETED%'), 1))).label('p_completed'),
            func.count(db.case((EmployeePoints.activity_type.ilike('%IDEA_APPROVED%'), 1))).label('p_ideas'),
            func.count(db.case((EmployeePoints.activity_type.ilike('%KNOWLEDGE_ARTICLE%'), 1))).label('p_articles')
        ).filter(
            EmployeePoints.organization_id == current_user.org_id,
            EmployeePoints.created_at >= filter_start
        )
        if filter_end:
            pts_query = pts_query.filter(EmployeePoints.created_at <= filter_end)
        
        pts_res = pts_query.group_by(EmployeePoints.employee_id).all()
        for r in pts_res:
            period_points_map[r.employee_id] = {
                'points': int(r.p_points or 0),
                'completed': int(r.p_completed or 0),
                'ideas': int(r.p_ideas or 0),
                'articles': int(r.p_articles or 0)
            }

    query = db.session.query(EmployeeLeaderboard)\
        .join(User, User.id == EmployeeLeaderboard.employee_id)\
        .outerjoin(Role, User.role_id == Role.id)\
        .outerjoin(Department, User.department_id == Department.id)\
        .filter(EmployeeLeaderboard.organization_id == current_user.org_id)\
        .filter(db.or_(
            Role.name.in_(['Team Member', 'Team Leader', 'Facilitator', 'Reviewer']),
            Role.id == None
        ))\
        .filter(db.not_(Role.name.in_(['Admin', 'admin', 'SuperAdmin', 'superadmin', 'CEO', 'ceo', 'Owner', 'owner', 'System Admin', 'Administrator'])))

    if user_ids_param:
        try:
            target_ids = [int(x.strip()) for x in user_ids_param.split(',') if x.strip().isdigit()]
            if target_ids:
                query = query.filter(User.id.in_(target_ids))
        except Exception:
            pass

    if plant_param:
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
        query = query.filter(Role.name.ilike(f"%{role_param}%"))

    if search_q:
        pattern = f"%{search_q}%"
        query = query.filter(
            db.or_(
                User.username.ilike(pattern),
                User.full_name.ilike(pattern),
                Department.name.ilike(pattern)
            )
        )

    all_candidates = query.all()
    ranked_candidates = []

    for lb in all_candidates:
        u = lb.employee
        if not u:
            continue
        p_info = period_points_map.get(u.id, {})
        period_pts = p_info.get('points', lb.total_points if not filter_start else 0)
        period_completed = p_info.get('completed', lb.projects_completed if not filter_start else 0)
        period_ideas = p_info.get('ideas', lb.ideas_approved if not filter_start else 0)
        period_articles = p_info.get('articles', lb.knowledge_articles if not filter_start else 0)

        ranked_candidates.append({
            "employee_id": u.id,
            "name": u.full_name or u.username,
            "username": u.username,
            "email": u.email or "N/A",
            "role": u.role.name if u.role else "Team Member",
            "plant": u.plant.name if getattr(u, 'plant', None) else (u.dept.plant.name if u.dept and u.dept.plant else "Main Plant"),
            "department": u.dept.name if u.dept else "General",
            "badge": lb.badges or PointEngineService.get_badge_for_points(lb.total_points),
            "period_points": period_pts,
            "total_points": lb.total_points,
            "projects_completed": period_completed if filter_start else lb.projects_completed,
            "lifetime_projects_completed": lb.projects_completed,
            "projects_created": lb.projects_created,
            "ideas_submitted": lb.ideas_submitted,
            "ideas_approved": period_ideas if filter_start else lb.ideas_approved,
            "knowledge_articles": period_articles if filter_start else lb.knowledge_articles,
            "meetings_attended": lb.meetings_attended,
            "user_created_at": u.created_at
        })

    # Sort based on timeframe score with tie-breaking
    if filter_start:
        ranked_candidates.sort(key=lambda x: (x['period_points'], x['total_points'], x['projects_completed'], x['ideas_approved']), reverse=True)
    else:
        ranked_candidates.sort(key=lambda x: (x['total_points'], x['projects_completed'], x['ideas_approved'], x['knowledge_articles']), reverse=True)

    if limit and limit > 0:
        ranked_candidates = ranked_candidates[:limit]

    # Assign rank
    for idx, item in enumerate(ranked_candidates, start=1):
        item['rank'] = idx

    if export_format == 'json':
        return jsonify({
            "status": "success",
            "timeline": timeline_label,
            "count": len(ranked_candidates),
            "items": ranked_candidates
        }), 200

    # Build CSV Response with Excel UTF-8 BOM
    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output, lineterminator='\n')

    # Header metadata
    org_name = current_user.organization.name if current_user.organization else "QCMS Organization"
    gen_time = now.strftime("%d-%b-%Y %H:%M UTC")

    writer.writerow(["# QCMS EMPLOYEE RECOGNITION & REWARDS LEADERBOARD REPORT"])
    writer.writerow([f"# Organization: {org_name}"])
    writer.writerow([f"# Timeline Scope: {timeline_label}"])
    writer.writerow([f"# Generated At: {gen_time}"])
    writer.writerow([f"# Total Records Exported: {len(ranked_candidates)}"])
    writer.writerow([]) # Empty separator line

    writer.writerow([
        "Rank",
        "Employee Name",
        "Username / Employee ID",
        "Email Address",
        "Role",
        "Plant Location",
        "Department",
        "Period Points (PTS)",
        "Lifetime Points (PTS)",
        "Recognition Badge / Tier",
        "Projects Completed",
        "Ideas Approved",
        "Knowledge Articles",
        "Meetings Attended"
    ])

    for r in ranked_candidates:
        writer.writerow([
            r["rank"],
            r["name"],
            r["username"],
            r["email"],
            r["role"],
            r["plant"],
            r["department"],
            r["period_points"],
            r["total_points"],
            r["badge"],
            r["projects_completed"],
            r["ideas_approved"],
            r["knowledge_articles"],
            r["meetings_attended"]
        ])

    csv_data = output.getvalue()
    filename_clean = f"QCMS_Rewards_Export_{time_range}_{now.strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename_clean}",
            "Content-Type": "text/csv; charset=utf-8",
            "Cache-Control": "no-cache, no-store, must-revalidate"
        }
    )




