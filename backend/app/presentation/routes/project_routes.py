from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.infrastructure.database.models.models import Project, User, ProjectMember, KPIMetric, ProjectStageTracker, ProjectWorkflow, Department, db
from app.presentation.middleware.middleware import role_required
from app.domain.services.subscription_service import SubscriptionManager
from app.domain.services.feature_engine import feature_module_required
from app.presentation.middleware.idempotency_middleware import idempotent
from datetime import datetime, timezone
import uuid
import copy
from sqlalchemy.orm.attributes import flag_modified
from app.presentation.routes.error_helpers import internal_server_error

project_bp = Blueprint('projects', __name__)

# ── Shared utility: departments list (accessible by all authenticated users) ──
def get_plant_ids_by_name(org_id, name_str):
    if not name_str:
        return []
    from app.infrastructure.database.models.models import Plant
    s = name_str.strip().lower()
    terms = [s]
    if 'bengaluru' in s:
        terms.append(s.replace('bengaluru', 'bangalore'))
    if 'bangalore' in s:
        terms.append(s.replace('bangalore', 'bengaluru'))
    
    conds = []
    for t in terms:
        p_like = f"%{t}%"
        conds.append(Plant.name.ilike(p_like))
        conds.append(Plant.location.ilike(p_like))
        
    plants = Plant.query.filter(Plant.org_id == org_id, db.or_(*conds)).all()
    return [p.id for p in plants]

def apply_plant_filter_to_user_query(q, org_id, plant_id=None, plant_name=None):
    from app.infrastructure.database.models.models import Plant, Department
    if plant_id:
        try:
            p_int = int(plant_id)
            return q.filter(
                db.or_(
                    User.plant_id == p_int,
                    db.and_(User.plant_id.is_(None), User.dept.has(Department.plant_id == p_int))
                )
            )
        except (ValueError, TypeError):
            pass
    elif plant_name and str(plant_name).strip():
        p_name = str(plant_name).strip()
        p_ids = get_plant_ids_by_name(org_id, p_name)
        if p_ids:
            return q.filter(
                db.or_(
                    User.plant_id.in_(p_ids),
                    db.and_(User.plant_id.is_(None), User.dept.has(Department.plant_id.in_(p_ids)))
                )
            )
        else:
            return q.filter(
                db.or_(
                    User.plant.has(Plant.name.ilike(f"%{p_name}%")),
                    db.and_(User.plant_id.is_(None), User.dept.has(Department.plant.has(Plant.name.ilike(f"%{p_name}%"))))
                )
            )
    return q

@project_bp.route('/departments', methods=['GET'])
@jwt_required()
def list_departments():
    """Return all departments for the current user's organisation, filtered by plant if provided."""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    org_id = request.args.get('org_id', type=int)
    plant_id = request.args.get('plant_id')
    plant_name = request.args.get('plant_name')
    
    if user.role and user.role.name == 'SuperAdmin':
        target_org = org_id or user.org_id
        q = Department.query.filter_by(org_id=target_org) if target_org else Department.query
    else:
        q = Department.query.filter_by(org_id=user.org_id)
    
    if plant_id:
        try:
            p_int = int(plant_id)
            q = q.filter(db.or_(Department.plant_id == p_int, Department.plant_id.is_(None)))
        except ValueError:
            pass
    elif plant_name:
        p_ids = get_plant_ids_by_name(user.org_id, plant_name)
        if p_ids:
            q = q.filter(db.or_(Department.plant_id.in_(p_ids), Department.plant_id.is_(None)))
        else:
            from app.infrastructure.database.models.models import Plant
            q = q.filter(db.or_(Department.plant.has(Plant.name.ilike(f"%{plant_name}%")), Department.plant_id.is_(None)))

    depts = q.order_by(Department.name).all()
    return jsonify([{"id": d.id, "name": d.name, "plant_id": d.plant_id} for d in depts]), 200

# ── Shared utility: plants list (accessible by all authenticated users) ──
@project_bp.route('/plants', methods=['GET'])
@jwt_required()
def list_plants():
    """Return all plants/locations for the current user's organisation."""
    from app.infrastructure.database.models.models import Plant
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
    plants = Plant.query.filter_by(org_id=user.org_id).order_by(Plant.name).all()
    return jsonify([{"id": p.id, "name": p.name, "code": p.code or "", "location": p.location or ""} for p in plants]), 200

# ── Shared utility: facilitators list (accessible by all authenticated users) ──
@project_bp.route('/facilitators', methods=['GET'])
@jwt_required()
def list_facilitators():
    """Return Facilitators under the selected plant and department."""
    from app.infrastructure.database.models.models import Role, Department
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    dept_id = request.args.get('dept_id')
    plant_id = request.args.get('plant_id')
    plant_name = request.args.get('plant_name')

    q = User.query.filter(
        User.org_id == user.org_id,
        User.is_active == True
    )
    q = apply_plant_filter_to_user_query(q, user.org_id, plant_id=plant_id, plant_name=plant_name)
    
    target_dept_id = None
    if dept_id:
        try:
            target_dept_id = int(dept_id)
        except ValueError:
            pass

    if target_dept_id:
        q_dept = q.filter(db.or_(
            User.department_id == target_dept_id,
            User.department_id.is_(None)
        ))
        if q_dept.join(Role).filter(db.func.lower(Role.name) == 'facilitator').count() > 0:
            q = q_dept

    # Filter strictly for users with Facilitator role
    q_fac = q.join(Role).filter(db.func.lower(Role.name) == 'facilitator')
    facilitators = q_fac.order_by(User.full_name).all()

    # Fallback only within the SAME plant if plant filter is active, or org-wide if no plant specified
    if not facilitators:
        q_fallback = User.query.filter(User.org_id == user.org_id, User.is_active == True)
        if plant_id or plant_name:
            q_fallback = apply_plant_filter_to_user_query(q_fallback, user.org_id, plant_id=plant_id, plant_name=plant_name)
        facilitators = q_fallback.join(Role).filter(
            db.func.lower(Role.name) == 'facilitator'
        ).order_by(User.full_name).all()

    return jsonify([{
        "id": u.id,
        "full_name": u.full_name or u.username,
        "username": u.username,
        "role": u.role.name if u.role else "Facilitator",
        "plant_id": u.plant_id or (u.dept.plant_id if u.dept else None),
        "plant_name": u.plant.name if u.plant else (u.dept.plant.name if u.dept and u.dept.plant else None)
    } for u in facilitators]), 200

# ── Shared utility: all org members (accessible by all authenticated users) ──
@project_bp.route('/members', methods=['GET'])
@jwt_required()
def list_org_members():
    """Return all active users in the current user's organisation for team assignment, optionally filtered by plant."""
    from app.infrastructure.database.models.models import Role, Department
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    plant_id = request.args.get('plant_id')
    plant_name = request.args.get('plant_name')
    
    q = User.query.filter(
        User.org_id == user.org_id,
        User.is_active == True
    )
    q = apply_plant_filter_to_user_query(q, user.org_id, plant_id=plant_id, plant_name=plant_name)
    
    members = q.order_by(User.full_name).all()
    return jsonify([{
        "id": u.id,
        "full_name": u.full_name or u.username,
        "username": u.username,
        "email": u.email or '',
        "role": u.role.name if u.role else "Team Member",
        "department_id": u.department_id,
        "department": u.dept.name if u.dept else "General",
        "plant_id": u.plant_id or (u.dept.plant_id if u.dept else None),
        "plant_name": u.plant.name if u.plant else (u.dept.plant.name if u.dept and u.dept.plant else None)
    } for u in members]), 200

@project_bp.route('', methods=['GET'], strict_slashes=False)
@project_bp.route('/', methods=['GET'], strict_slashes=False)
@jwt_required()
@feature_module_required('projects.view')
def get_projects():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    role = user.role.name
    org_id = user.org_id
    
    page = request.args.get('page', type=int)
    per_page = min(max(1, request.args.get('per_page', default=25, type=int)), 100)
    search = request.args.get('search', type=str)
    
    from sqlalchemy.orm import joinedload
    query = Project.query.options(
        joinedload(Project.department),
        joinedload(Project.creator),
        joinedload(Project.team_leader),
        joinedload(Project.facilitator),
        joinedload(Project.reviewer)
    ).filter_by(org_id=org_id)
    
    as_member = (request.args.get('as_member') == 'true') or (request.args.get('scope') == 'member') or (request.args.get('role_filter') == 'member')

    if as_member or role in ('Team Leader', 'Team Member'):
        # Filter projects where user is team leader, team member, or creator
        query = query.filter(db.or_(Project.team_leader_id == user.id, Project.members.any(id=user.id), Project.creator_id == user.id))
    elif role in ('Admin', 'CEO'):
        pass # Full access within organization
    elif role == 'Facilitator':
        query = query.filter(Project.facilitator_id == user.id)
    elif role == 'Reviewer':
        query = query.filter(Project.reviewer_id == user.id)
    else:
        query = query.filter(False)

    if search:
        clean_search = search.strip()[:100]
        if clean_search:
            search_term = f"%{clean_search}%"
            query = query.filter(db.or_(
                Project.title.ilike(search_term),
                Project.project_uid.ilike(search_term),
                Project.category.ilike(search_term)
            ))

    query = query.order_by(Project.created_at.desc())

    # Performance optimization: Eager load relationships to eliminate N+1 query storm
    from sqlalchemy.orm import joinedload
    query = query.options(
        joinedload(Project.department),
        joinedload(Project.creator),
        joinedload(Project.team_leader),
        joinedload(Project.facilitator),
        joinedload(Project.reviewer)
    )

    from app.presentation.routes.repository_routes import calculate_project_realtime_efficiency
    from app.infrastructure.database.models.models import ProjectWorkflow

    def batch_prefetch_workflow_map(projects):
        p_ids = [p.id for p in projects if p]
        if not p_ids:
            return {}
        raw_wfs = ProjectWorkflow.query.filter(
            ProjectWorkflow.project_id.in_(p_ids),
            ProjectWorkflow.stage_id.in_([1, 7, 8])
        ).all()
        from app.infrastructure.database.models.models import (
            Stage7PerformanceVerificationBenefitsRealization,
            Stage8StandardizationKnowledgeSharingProjectClosure,
            KnowledgeRepository
        )
        s7_models = Stage7PerformanceVerificationBenefitsRealization.query.filter(
            Stage7PerformanceVerificationBenefitsRealization.project_id.in_(p_ids)
        ).all()
        s8_models = Stage8StandardizationKnowledgeSharingProjectClosure.query.filter(
            Stage8StandardizationKnowledgeSharingProjectClosure.project_id.in_(p_ids)
        ).all()
        repos = KnowledgeRepository.query.filter(
            KnowledgeRepository.project_id.in_(p_ids)
        ).all()

        wf_map = {pid: {'s7_model': None, 's8_model': None, 'repo': None} for pid in p_ids}
        for w in raw_wfs:
            if w.data:
                wf_map[w.project_id][w.stage_id] = w.data
        for s7 in s7_models:
            wf_map[s7.project_id]['s7_model'] = s7
        for s8 in s8_models:
            wf_map[s8.project_id]['s8_model'] = s8
        for r in repos:
            wf_map[r.project_id]['repo'] = r
        return wf_map

    def serialize_proj(p, wf_data_map=None):
        created_iso = p.created_at.isoformat() if p.created_at else None
        p_wf = wf_data_map.get(p.id) if wf_data_map else None
        eff_val = calculate_project_realtime_efficiency(p.id, p.current_stage, preloaded_wfs=p_wf)
        return {
            "id": p.id,
            "project_uid": p.project_uid,
            "title": p.title,
            "category": p.category,
            "current_stage": p.current_stage,
            "status": p.status,
            "department": p.department.name if p.department else "N/A",
            "creator": p.creator.username if p.creator else "System",
            "created_at": created_iso,
            "updated_at": created_iso,
            "last_updated": created_iso,
            "team_leader_id": p.team_leader_id,
            "team_leader_name": (p.team_leader.full_name or p.team_leader.username) if p.team_leader else None,
            "facilitator_id": p.facilitator_id,
            "facilitator_name": (p.facilitator.full_name or p.facilitator.username) if p.facilitator else None,
            "reviewer_id": p.reviewer_id,
            "reviewer_name": (p.reviewer.full_name or p.reviewer.username) if p.reviewer else None,
            "rejection_reason": p.rejection_reason,
            "efficiency": eff_val,
            "kpi_improvement_pct": eff_val
        }

    if page is not None:
        try:
            page_int = max(1, int(page))
        except (ValueError, TypeError):
            page_int = 1
        try:
            per_page_int = max(1, min(int(per_page), 250))
        except (ValueError, TypeError):
            per_page_int = 25

        pagination = query.paginate(page=page_int, per_page=per_page_int, error_out=False)
        wf_map = batch_prefetch_workflow_map(pagination.items)
        items = [serialize_proj(p, wf_map) for p in pagination.items]
        return jsonify({
            "items": items,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "total_pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev
        }), 200

    # Unbounded guard: cap unpaginated requests at 200 items
    projects = query.limit(200).all()
    wf_map = batch_prefetch_workflow_map(projects)
    return jsonify([serialize_proj(p, wf_map) for p in projects]), 200

@project_bp.route('/potential-members', methods=['GET'])
@jwt_required()
def get_potential_members():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    org_id = user.org_id
    role = user.role.name if user.role else 'User'
    
    from app.infrastructure.database.models.models import Role, Department, UserCustomField
    
    target_role_name = request.args.get('role')
    dept_id = request.args.get('dept_id')
    plant_id = request.args.get('plant_id')
    plant_name = request.args.get('plant_name')
    ignore_dept = request.args.get('ignore_dept', 'false').lower() == 'true'
    
    # Base query: active users in the same organization
    q = User.query.filter(User.org_id == org_id, User.is_active == True)
    q = apply_plant_filter_to_user_query(q, org_id, plant_id=plant_id, plant_name=plant_name)
    
    # Filter by department
    target_dept_id = None
    if dept_id:
        try:
            target_dept_id = int(dept_id)
        except ValueError:
            pass
    elif role in ('Team Leader', 'Team Member') and not ignore_dept:
        target_dept_id = user.department_id

    if target_dept_id and not ignore_dept:
        dept_obj = db.session.get(Department, target_dept_id) if target_dept_id else None
        if dept_obj:
            q_dept = q.filter(
                db.or_(
                    User.department_id == target_dept_id,
                    User.dept.has(db.func.lower(Department.name) == dept_obj.name.lower()),
                    User.department_id.is_(None)
                )
            )
        else:
            q_dept = q.filter(db.or_(User.department_id == target_dept_id, User.department_id.is_(None)))
            
        if q_dept.count() > 0:
            q = q_dept

    # Strictly enforce role matching when role parameter is provided:
    if target_role_name:
        req_role_lower = target_role_name.strip().lower()
        if req_role_lower == 'reviewer':
            q_rev = q.join(Role).filter(db.func.lower(Role.name) == 'reviewer')
            users = q_rev.order_by(User.full_name).all()
            if not users:
                q_fb = User.query.filter(User.org_id == org_id, User.is_active == True)
                if plant_id or plant_name:
                    q_fb = apply_plant_filter_to_user_query(q_fb, org_id, plant_id=plant_id, plant_name=plant_name)
                users = q_fb.join(Role).filter(
                    db.func.lower(Role.name) == 'reviewer'
                ).order_by(User.full_name).all()
        elif req_role_lower in ('team member', 'teammember'):
            q_tm = q.join(Role).filter(db.func.lower(Role.name).in_(['team member', 'team leader', 'teammember', 'teamleader', 'user', 'member', 'employee', 'staff']))
            users = q_tm.order_by(User.full_name).all()
            if not users:
                # Fallback: if no users found with exact team member role names, return all active plant users excluding platform admins
                q_fb = User.query.filter(User.org_id == org_id, User.is_active == True)
                if plant_id or plant_name:
                    q_fb = apply_plant_filter_to_user_query(q_fb, org_id, plant_id=plant_id, plant_name=plant_name)
                users = q_fb.join(Role).filter(~db.func.lower(Role.name).in_(['superadmin'])).order_by(User.full_name).all()
        elif req_role_lower == 'facilitator':
            q_fa = q.join(Role).filter(db.func.lower(Role.name) == 'facilitator')
            users = q_fa.order_by(User.full_name).all()
            if not users:
                q_fb = User.query.filter(User.org_id == org_id, User.is_active == True)
                if plant_id or plant_name:
                    q_fb = apply_plant_filter_to_user_query(q_fb, org_id, plant_id=plant_id, plant_name=plant_name)
                users = q_fb.join(Role).filter(
                    db.func.lower(Role.name) == 'facilitator'
                ).order_by(User.full_name).all()
        else:
            q_other = q.join(Role).filter(db.func.lower(Role.name) == req_role_lower)
            users = q_other.order_by(User.full_name).all()
    else:
        users = q.order_by(User.full_name).all()
    
    # Find the custom field key for phone number in this org:
    phone_field = UserCustomField.query.filter_by(org_id=org_id, data_type='phone').first()
    phone_key = phone_field.field_key if phone_field else None
    
    serialized_users = []
    for u in users:
        phone_val = None
        if u.custom_fields:
            if phone_key and phone_key in u.custom_fields:
                phone_val = u.custom_fields[phone_key]
            if not phone_val:
                for k, v in u.custom_fields.items():
                    if 'phone' in k.lower():
                        phone_val = v
                        break
                        
        serialized_users.append({
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "email": u.email,
            "phone": phone_val,
            "department_id": u.department_id,
            "role": u.role.name if u.role else "N/A",
            "department": u.dept.name if u.dept else "N/A",
            "plant_id": u.plant_id or (u.dept.plant_id if u.dept else None),
            "plant_name": u.plant.name if u.plant else (u.dept.plant.name if u.dept and u.dept.plant else None)
        })
        
    return jsonify(serialized_users), 200


@project_bp.route('/imported-idea/<string:idea_code>', methods=['GET'])
@jwt_required()
def get_imported_idea_by_code(idea_code):
    """
    Search ImportedIdea table using entered idea_code strictly within current user's organization.
    """
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    clean_code = idea_code.strip()
    from app.infrastructure.database.models.models import ImportedIdea
    from sqlalchemy import func

    # For SuperAdmin with no org_id, check optional ?org_id query param or fallback
    if not user.org_id and user.role and user.role.name == 'SuperAdmin':
        requested_org_id = request.args.get('org_id', type=int)
        if requested_org_id:
            idea = ImportedIdea.query.filter(
                ImportedIdea.organization_id == requested_org_id,
                func.lower(ImportedIdea.idea_code) == clean_code.lower()
            ).first()
        else:
            idea = ImportedIdea.query.filter(
                func.lower(ImportedIdea.idea_code) == clean_code.lower()
            ).first()
    else:
        # Strict tenant boundary check: ONLY search within current user's organization
        idea = ImportedIdea.query.filter(
            ImportedIdea.organization_id == user.org_id,
            func.lower(ImportedIdea.idea_code) == clean_code.lower()
        ).first()

    if not idea:
        return jsonify({
            "found": False,
            "message": "Idea Code not found in your organization. Please verify the reference code or check Additional Sources."
        }), 404

    return jsonify({
        "found": True,
        "idea": idea.to_dict()
    }), 200


@project_bp.route('', methods=['POST'])
@project_bp.route('/', methods=['POST'])
@jwt_required()
@feature_module_required('projects.create')
@role_required(['Team Leader', 'Team Member', 'Admin', 'SuperAdmin'])
@idempotent()
def create_project():
    data = request.get_json()
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    role_name = user.role.name

    if role_name not in ('Team Leader', 'Team Member', 'Admin', 'SuperAdmin'):
        return jsonify({"msg": "Access denied. Only Team Members, Team Leaders, and Admins can initialize projects."}), 403

    # Subscription Limit Check
    can_create, limit_msg = SubscriptionManager.check_project_limit(user.org_id)
    if not can_create:
        return jsonify({
            "msg": limit_msg,
            "error_code": "PROJECT_LIMIT_REACHED"
        }), 403
    
    # Generate unique ID format PRJ-XXXX
    import random
    import string
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    project_uid = f"PRJ-{random_suffix}"
    
    # Team Member creates and assigns team leader (either selected or self)
    team_leader_id = data.get('team_leader_id') or user_id
    dept_id = data.get('department_id') or user.department_id

    def _safe_parse_date(d_val):
        if not d_val or not str(d_val).strip():
            return None
        s = str(d_val).strip()
        for fmt in ('%Y-%m-%d', '%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%S', '%Y/%m/%d', '%d-%m-%Y'):
            try:
                date_part = s.split('T')[0] if 'T' in s else s
                return datetime.strptime(date_part, '%Y-%m-%d').date()
            except Exception:
                pass
            try:
                return datetime.strptime(s, fmt).date()
            except Exception:
                pass
        return None

    try:
        # Check if facilitator_id is provided and valid (not empty string)
        fid_val = data.get('facilitator_id')
        facilitator_id = int(fid_val) if fid_val is not None and str(fid_val).strip() != "" else None

        # Check if reviewer_id is provided and valid (not empty string)
        rid_val = data.get('reviewer_id')
        reviewer_id = int(rid_val) if rid_val is not None and str(rid_val).strip() != "" else None

        # Parse planned dates
        init_data = data.get('init_data', {})
        planned_start = init_data.get('planned_start_date')
        planned_end = init_data.get('planned_end_date')

        parsed_start = _safe_parse_date(planned_start)
        parsed_end = _safe_parse_date(planned_end)
        parsed_deadline = _safe_parse_date(data.get('deadline')) or parsed_end

        new_project = Project(
            project_uid=project_uid,
            title=data.get('title', 'Untitled Project'),
            description=data.get('description'),
            category=data.get('category', 'Quality'),
            creator_id=user_id,
            team_leader_id=team_leader_id,
            facilitator_id=facilitator_id,
            reviewer_id=reviewer_id,
            org_id=user.org_id,
            department_id=dept_id,
            start_date=parsed_start,
            end_date=parsed_end,
            deadline=parsed_deadline,
            work_area=init_data.get('work_area', ''),
            plant=init_data.get('plant', ''),
            project_source=init_data.get('source', '') or ('Ideation Tool' if data.get('idea_code') else 'Manual'),
            reference_number=data.get('idea_code') or init_data.get('ref_number', ''),
            sponsor=init_data.get('sponsor', ''),
            current_stage=1,
            status='Draft',
            stages_config=copy.deepcopy(user.organization.get_stages_config())
        )
        
        db.session.add(new_project)
        db.session.flush()

        # Link Imported Idea if created from an approved idea
        idea_code = data.get('idea_code') or init_data.get('idea_code')
        if idea_code:
            try:
                from app.infrastructure.database.models.models import ImportedIdea
                imp_idea = ImportedIdea.query.filter_by(organization_id=user.org_id, idea_code=str(idea_code).strip()).first()
                if imp_idea:
                    imp_idea.linked_project_id = new_project.id
                    db.session.add(imp_idea)
            except Exception as idea_err:
                print(f"[QCMS PROJECT] ImportedIdea link warning: {idea_err}")

        # 1. Build the complete set of member IDs — always includes: creator + team_leader + selected members
        member_ids_raw = data.get('member_ids', [])
        all_member_ids = set()
        if user_id:
            all_member_ids.add(int(user_id))
        if team_leader_id:
            all_member_ids.add(int(team_leader_id))
        for mid in member_ids_raw:
            if mid:
                try:
                    all_member_ids.add(int(mid))
                except (ValueError, TypeError):
                    pass

        # 2. Pre-fetch all user records upfront to prevent session query autoflush triggers
        users_by_id = {}
        if all_member_ids:
            found_users = User.query.filter(User.id.in_(list(all_member_ids))).all()
            users_by_id = {u.id: u for u in found_users}

        # Also pre-fetch facilitator, team leader, and reviewer users
        tl_user = users_by_id.get(team_leader_id) or (db.session.get(User, team_leader_id) if team_leader_id else None)
        fac_user = db.session.get(User, facilitator_id) if facilitator_id else None
        rev_user = db.session.get(User, reviewer_id) if reviewer_id else None

        # Calculate initial duration string
        duration_str = ""
        if parsed_start and parsed_end:
            days = max(1, abs((parsed_end - parsed_start).days))
            duration_str = f"{days} days ({parsed_start} → {parsed_end})"

        # 3. Insert ProjectMember rows safely under no_autoflush context
        team_members_list = []
        with db.session.no_autoflush:
            for mid in all_member_ids:
                db.session.add(ProjectMember(project_id=new_project.id, user_id=mid))
                m_user = users_by_id.get(mid)
                if m_user and mid != team_leader_id:
                    team_members_list.append({
                        "user_id": m_user.id,
                        "name": m_user.full_name or m_user.username,
                        "role": m_user.role.name if m_user.role else "Team Member",
                        "designation": ""
                    })
        
        # 4. Initialize 8 stages in tracker. Stage 1 = Incomplete, rest = Not Started
        for i in range(1, 9):
            tracker = ProjectStageTracker(
                project_id=new_project.id,
                org_id=user.org_id,
                stage_number=i,
                status='Incomplete' if i == 1 else 'Not Started',
                started_at=datetime.now(timezone.utc).replace(tzinfo=None) if i == 1 else None
            )
            db.session.add(tracker)
        
        # 5. Store Stage 1 initialization data in ProjectWorkflow as JSON (QC Story)
        stage1_workflow = ProjectWorkflow(
            project_id=new_project.id,
            org_id=user.org_id,
            stage_id=1,
            updated_by=user_id,
            data={
                "init": {
                    "project_title": data.get('title', 'Untitled Project'),
                    "project_type": data.get('category', 'Quality'),
                    "work_area": init_data.get('work_area', '') or new_project.work_area or '',
                    "plant": init_data.get('plant', '') or new_project.plant or '',
                    "source": init_data.get('source', '') or new_project.project_source or '',
                    "ref_number": init_data.get('ref_number', '') or new_project.reference_number or '',
                    "sponsor": init_data.get('sponsor', '') or new_project.sponsor or (f"{new_project.department.name} Head / Operations Manager" if new_project.department else "Plant Manager / Department Head"),
                    "planned_start_date": str(parsed_start) if parsed_start else (planned_start or ''),
                    "planned_end_date": str(parsed_end) if parsed_end else (planned_end or ''),
                    "duration": duration_str or "90 days (Standard 8D Lifecycle)",
                    "team_leader": (tl_user.full_name or tl_user.username) if tl_user else '',
                    "team_leader_id": team_leader_id,
                    "facilitator": (fac_user.full_name or fac_user.username) if fac_user else '',
                    "facilitator_id": facilitator_id,
                    "reviewer": (rev_user.full_name or rev_user.username) if rev_user else '',
                    "reviewer_id": reviewer_id,
                    "department_id": dept_id
                },
                "team": {
                    "circle_name": f"{data.get('title', 'Quality')} Circle",
                    "team_members": team_members_list
                },
                "background_5w2h": {},
                "current_performance": {},
                "justification": {},
                "emergency_response": {},
                "theme_target_schedule": {}
            }
        )
        db.session.add(stage1_workflow)
        
        # 5. Initialize KPI Metrics
        db.session.add(KPIMetric(project_id=new_project.id, org_id=user.org_id))
        
        # Send Notifications for project assignments safely
        try:
            from app.presentation.routes.notification_routes import create_notification
            if team_leader_id and team_leader_id != user_id:
                create_notification(
                    user.org_id, team_leader_id,
                    "Project Assigned",
                    f"You have been assigned as the Team Leader for project '{new_project.title}'.",
                    f"/projects/project-details.html?id={new_project.id}",
                    commit=False
                )
            if facilitator_id and facilitator_id != user_id:
                create_notification(
                    user.org_id, facilitator_id,
                    "Project Assigned",
                    f"You have been assigned as the Facilitator for project '{new_project.title}'.",
                    f"/projects/project-details.html?id={new_project.id}",
                    commit=False
                )
            if reviewer_id and reviewer_id != user_id:
                create_notification(
                    user.org_id, reviewer_id,
                    "Project Assigned",
                    f"You have been assigned as the Reviewer for project '{new_project.title}'.",
                    f"/projects/project-details.html?id={new_project.id}",
                    commit=False
                )
        except Exception as notif_err:
            print(f"[QCMS PROJECT] Notification warning: {notif_err}")

        # 6. Log the creation in Audit Log safely
        try:
            from app.infrastructure.database.models.models import AuditLog
            from flask import request as flask_request
            ua_str = getattr(flask_request.user_agent, 'string', str(flask_request.user_agent or ''))
            audit = AuditLog(
                org_id=user.org_id,
                project_id=new_project.id,
                user_id=user_id,
                action=f"Created Project {project_uid}",
                details=f"Project '{new_project.title}' initialized as Draft. Stage 1 started.",
                ip_address=flask_request.remote_addr,
                user_agent=ua_str,
                target_table="projects",
                target_id=new_project.id
            )
            db.session.add(audit)
        except Exception as audit_err:
            print(f"[QCMS PROJECT] AuditLog warning: {audit_err}")
        
        db.session.commit()
        
        try:
            from app.domain.services.cache_service import CacheService
            CacheService.invalidate_project_cache(user.org_id)
        except Exception:
            pass

        # Award Employee Points for Project Initialization & Role Assignments
        try:
            from app.domain.services.point_engine_service import PointEngineService
            PointEngineService.award_points(
                employee_id=user_id, org_id=user.org_id, activity_type="project_created",
                ref_id=f"proj_create_{new_project.id}", project_id=new_project.id,
                description=f"Created project '{new_project.title}'"
            )
            if team_leader_id:
                PointEngineService.award_points(
                    employee_id=team_leader_id, org_id=user.org_id, activity_type="project_became_leader",
                    ref_id=f"proj_leader_{new_project.id}", project_id=new_project.id,
                    description=f"Assigned Team Leader for '{new_project.title}'"
                )
            if facilitator_id:
                PointEngineService.award_points(
                    employee_id=facilitator_id, org_id=user.org_id, activity_type="project_became_facilitator",
                    ref_id=f"proj_facil_{new_project.id}", project_id=new_project.id,
                    description=f"Assigned Facilitator for '{new_project.title}'"
                )
            for mid in all_member_ids:
                if mid and int(mid) != team_leader_id:
                    PointEngineService.award_points(
                        employee_id=int(mid), org_id=user.org_id, activity_type="project_team_joined",
                        ref_id=f"proj_join_{new_project.id}_{mid}", project_id=new_project.id,
                        description=f"Joined project '{new_project.title}' team"
                    )
        except Exception as p_err:
            print(f"[QCMS REWARDS] Non-blocking points allocation warning: {p_err}")

        # Send Automated Email Notification to all assigned project members, reviewer, facilitator, and team leader
        try:
            from app.domain.services.email_notification_engine import EmailNotificationEngine
            EmailNotificationEngine.trigger_project_assigned_notification(new_project.id)
        except Exception as email_err:
            print(f"[QCMS EMAIL] Non-blocking project assigned email dispatch error: {email_err}")

        return jsonify({
            "msg": "Project initialized successfully", 
            "project_uid": project_uid, 
            "id": new_project.id
        }), 201

    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"[QCMS PROJECT] Initialization failed error: {e}", flush=True)
        traceback.print_exc()
        err_msg = str(e) or "Initialization failed"
        return internal_server_error(e, "Project initialization failed.")

# ─────────────────────────────────────────────────────────────────────────
# STAGE 1 – QC STORY ROUTES (Save / Submit / Review)
# ─────────────────────────────────────────────────────────────────────────

@project_bp.route('/<int:id>/stage1/save', methods=['POST'])
@jwt_required()
def save_stage1(id):
    """Save Stage 1 progress without submitting for review."""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    project = db.session.get(Project, id)

    user_is_sa = bool(user and user.role and user.role.name == 'SuperAdmin')
    if not project or (not user_is_sa and project.org_id != user.org_id):
        return jsonify({"msg": "Project not found"}), 404

    # Check if project is permanently rejected
    if project.status in ('Rejected', 'Stage 1 Rejected') or (project.status and 'Rejected' in str(project.status)):
        return jsonify({"msg": "This project has been permanently rejected and cannot be modified or re-submitted."}), 400

    # STRICT RULE: Only assigned Team Leader or Team Member can edit Stage 1 (Admin is read-only)
    is_authorized = user.role.name in ('Team Leader', 'Team Member')
    if not is_authorized:
        return jsonify({"msg": "Access denied. Only assigned Team Leaders and Team Members can edit project details."}), 403

    payload = request.get_json() or {}
    workflow = ProjectWorkflow.query.filter_by(project_id=id, stage_id=1).first()

    if not workflow:
        workflow = ProjectWorkflow(project_id=id, org_id=user.org_id, stage_id=1, data={})
        db.session.add(workflow)

    # Merge incoming sections into existing data
    existing = dict(workflow.data or {})
    for section, section_data in payload.items():
        existing[section] = section_data
    workflow.data = existing
    flag_modified(workflow, 'data')
    workflow.updated_by = user_id
    workflow.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # Sync Team Members, Facilitator, and Reviewer to the database so access control works
    team_data = payload.get('team')
    if team_data:
        from app.infrastructure.database.models.models import ProjectMember

        # 1. Sync Team Members
        if 'team_members' in team_data and isinstance(team_data['team_members'], list):
            old_member_ids = set([m.user_id for m in ProjectMember.query.filter_by(project_id=id).all()])
            new_member_ids = set()
            if project.team_leader_id:
                new_member_ids.add(project.team_leader_id)
            for mem in team_data['team_members']:
                uid = mem.get('user_id') if isinstance(mem, dict) else mem
                if uid:
                    try:
                        uid_int = int(uid)
                        if uid_int > 0:
                            new_member_ids.add(uid_int)
                    except (ValueError, TypeError):
                        pass

            now_dt = datetime.now(timezone.utc).replace(tzinfo=None)
            added_ids = new_member_ids - old_member_ids
            removed_ids = old_member_ids - new_member_ids

            for added_id in added_ids:
                u_obj = db.session.get(User, added_id)
                u_name = (u_obj.full_name or u_obj.username) if u_obj else f"User #{added_id}"
                db.session.add(AuditLog(
                    org_id=user.org_id, project_id=id, user_id=user_id,
                    action="Team Member Joined Project",
                    details=f"{u_name} was added and joined the active project team.",
                    ip_address=request.remote_addr if hasattr(request, 'remote_addr') else None,
                    target_table="project_members", target_id=added_id,
                    created_at=now_dt
                ))

            for rem_id in removed_ids:
                u_obj = db.session.get(User, rem_id)
                u_name = (u_obj.full_name or u_obj.username) if u_obj else f"User #{rem_id}"
                db.session.add(AuditLog(
                    org_id=user.org_id, project_id=id, user_id=user_id,
                    action="Team Member Left Project (Transitioned in Middle)",
                    details=f"{u_name} left the project team / membership was removed from active roster.",
                    ip_address=request.remote_addr if hasattr(request, 'remote_addr') else None,
                    target_table="project_members", target_id=rem_id,
                    created_at=now_dt
                ))

            ProjectMember.query.filter_by(project_id=id).delete()
            for uid in new_member_ids:
                db.session.add(ProjectMember(project_id=id, user_id=uid))

    init_data = payload.get('init')
    if init_data and isinstance(init_data, dict):
        if 'facilitator_id' in init_data:
            fid = init_data.get('facilitator_id')
            project.facilitator_id = int(fid) if fid else None
        if 'reviewer_id' in init_data:
            rid = init_data.get('reviewer_id')
            project.reviewer_id = int(rid) if rid else None

    # Log
    from app.infrastructure.database.models.models import AuditLog
    db.session.add(AuditLog(
        org_id=user.org_id, project_id=id, user_id=user_id,
        action="Stage 1 Draft Saved",
        details=f"Stage 1 data draft saved by {user.username}.",
        ip_address=request.remote_addr, user_agent=request.user_agent.string,
        target_table="project_workflow", target_id=workflow.id
    ))
    db.session.commit()
    return jsonify({"msg": "Stage 1 progress saved.", "status": "Draft"}), 200



@project_bp.route('/<int:id>/stage1/submit', methods=['POST'])
@jwt_required()
def submit_stage1(id):
    """Validate Stage 1 completion rules and submit for review."""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    project = db.session.get(Project, id)

    user_is_sa = bool(user and user.role and user.role.name == 'SuperAdmin')
    if not project or (not user_is_sa and project.org_id != user.org_id):
        return jsonify({"msg": "Project not found"}), 404

    # Check if project is permanently rejected
    if project.status in ('Rejected', 'Stage 1 Rejected') or (project.status and 'Rejected' in str(project.status)):
        return jsonify({"msg": "This project has been permanently rejected and cannot be submitted for review."}), 400

    # STRICT RULE: Only assigned Team Leader or Team Member can submit Stage 1 (Admin is read-only)
    is_authorized = user.role.name in ('Team Leader', 'Team Member')
    if not is_authorized:
        return jsonify({"msg": "Access denied. Only assigned Team Leaders and Team Members can submit project stages for review."}), 403

    workflow = ProjectWorkflow.query.filter_by(project_id=id, stage_id=1).first()
    if not workflow:
        workflow = ProjectWorkflow(project_id=id, org_id=user.org_id, stage_id=1, data={})
        db.session.add(workflow)
    
    d = dict(workflow.data or {})

    # Completion validation
    errors = []
    members_count = ProjectMember.query.filter_by(project_id=id).count()
    if not d.get('team', {}).get('team_members') and members_count == 0:
        errors.append("Team members must be assigned (Section 1).")
    
    bg_5w2h = d.get('background_5w2h', {})
    if not bg_5w2h or not any(bg_5w2h.get(k) for k in ['what', 'where', 'when', 'who', 'why', 'problem_definition']):
        if project.description:
            if not isinstance(bg_5w2h, dict):
                bg_5w2h = {}
            bg_5w2h['problem_definition'] = project.description
            d['background_5w2h'] = bg_5w2h
        else:
            errors.append("Problem Background / 5W2H must be completed (Section 2).")
    
    tts = d.get('theme_target_schedule', {})
    if not tts or (not tts.get('improvement_theme') and not tts.get('target_level')):
        if project.title:
            if not isinstance(tts, dict):
                tts = {}
            tts['improvement_theme'] = project.title
            d['theme_target_schedule'] = tts

    workflow.data = d
    flag_modified(workflow, 'data')
    workflow.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # Update stage tracker status
    tracker = ProjectStageTracker.query.filter_by(project_id=id, stage_number=1).first()
    if not tracker:
        tracker = ProjectStageTracker(project_id=id, org_id=user.org_id, stage_number=1)
        db.session.add(tracker)
    tracker.status = 'Submitted For Review'
    tracker.started_at = tracker.started_at or datetime.now(timezone.utc).replace(tzinfo=None)

    project.status = 'Stage 1 Submitted'

    from app.presentation.routes.notification_routes import create_notification
    if project.reviewer_id and project.reviewer_id != user_id:
        create_notification(
            user.org_id, project.reviewer_id,
            "Approval Request",
            f"Project '{project.title}' is awaiting your Stage 1 review.",
            f"/projects/project-details.html?id={project.id}",
            commit=False
        )
    elif not project.reviewer_id:
        # Notify all reviewers in the organization
        from app.infrastructure.database.models.models import Role
        rev_role = Role.query.filter_by(name='Reviewer').first()
        if rev_role:
            rev_users = User.query.filter_by(org_id=user.org_id, role_id=rev_role.id).all()
            for ru in rev_users:
                if ru.id != user_id:
                    create_notification(
                        user.org_id, ru.id,
                        "Approval Request",
                        f"Project '{project.title}' is awaiting Stage 1 review.",
                        f"/projects/project-details.html?id={project.id}",
                        commit=False
                    )

    from app.infrastructure.database.models.models import AuditLog
    db.session.add(AuditLog(
        org_id=user.org_id, project_id=id, user_id=user_id,
        action="Stage 1 Submitted For Review",
        details=f"Stage 1 submitted by {user.username}.",
        ip_address=request.remote_addr, user_agent=request.user_agent.string,
        target_table="project_stage_tracker", target_id=tracker.id if tracker else None
    ))
    db.session.commit()

    # Trigger Reviewer Email Notification
    try:
        from app.domain.services.email_notification_engine import EmailNotificationEngine
        EmailNotificationEngine.trigger_project_review_requested_notification(project.id, 1, user_id)
    except Exception as e:
        print(f"[EmailEngine] Stage 1 review notification error: {e}")

    return jsonify({
        "msg": "Stage 1 submitted for review successfully.",
        "message": "Stage 1 submitted for review successfully.",
        "status": "Stage 1 Submitted"
    }), 200


@project_bp.route('/<int:id>/stage1/review', methods=['POST'])
@jwt_required()
@role_required(['Reviewer'])
def review_stage1(id):
    """Reviewer Approve, Reject, or Send Back Stage 1."""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    project = db.session.get(Project, id)

    user_is_sa = bool(user and user.role and user.role.name == 'SuperAdmin')
    if not project or (not user_is_sa and project.org_id != user.org_id):
        return jsonify({"msg": "Project not found"}), 404

    if user.role.name != 'Reviewer':
        return jsonify({"msg": "Only a Reviewer can review Stage 1."}), 403

    payload = request.get_json()
    decision = payload.get('decision')  # 'approve' | 'reject' | 'send_back'
    comments = payload.get('comments', '')

    if decision not in ('approve', 'reject', 'send_back'):
        return jsonify({"msg": "Invalid decision. Use: approve, reject, send_back"}), 400

    tracker = ProjectStageTracker.query.filter_by(project_id=id, stage_number=1).first()

    if decision == 'approve':
        if tracker:
            tracker.status = 'Completed'
            tracker.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        project.status = 'Stage 1 Approved'
        project.current_stage = 2

        # Sync facilitator_approved flag in Stage 1 model
        from app.infrastructure.database.models.models import Stage1ProblemDefinitionProjectInitiation
        s1 = Stage1ProblemDefinitionProjectInitiation.query.filter_by(project_id=id).first()
        if s1:
            s1.facilitator_approved = True
            s1.facilitator_approver_id = user_id
            s1.facilitator_approved_at = datetime.now(timezone.utc).replace(tzinfo=None)
            s1.facilitator_comments = comments

        # Unlock Stage 2
        stage2_tracker = ProjectStageTracker.query.filter_by(project_id=id, stage_number=2).first()
        if stage2_tracker:
            stage2_tracker.status = 'Incomplete'
            stage2_tracker.started_at = datetime.now(timezone.utc).replace(tzinfo=None)

        action_label = "Stage 1 Approved"
        msg = "Stage 1 approved. Stage 2 is now unlocked."

    elif decision == 'reject':
        if tracker:
            tracker.status = 'Rejected'
        project.status = 'Rejected'
        project.rejection_reason = comments
        action_label = "Stage 1 Rejected"
        msg = "Stage 1 rejected."

    else:  # send_back
        if tracker:
            tracker.status = 'Incomplete'
        project.status = 'Stage 1 In Progress'
        action_label = "Stage 1 Sent Back"
        msg = "Stage 1 sent back for revision."

    # Save review comments to workflow
    workflow = ProjectWorkflow.query.filter_by(project_id=id, stage_id=1).first()
    if workflow:
        d = dict(workflow.data or {})
        d['review'] = {'decision': decision, 'comments': comments, 'reviewer': user.username, 'reviewed_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()}
        workflow.data = d
        flag_modified(workflow, 'data')

    from app.infrastructure.database.models.models import AuditLog
    db.session.add(AuditLog(
        org_id=user.org_id, project_id=id, user_id=user_id,
        action=action_label,
        details=f"{action_label} by {user.username}. Comments: {comments}",
        ip_address=request.remote_addr, user_agent=request.user_agent.string,
        target_table="projects", target_id=id
    ))
    db.session.commit()
    return jsonify({"msg": msg}), 200

# ── GENERIC ROUTES FOR STAGES 2-8 ──

def sync_sop_from_stage8(project_id, sop_data, user_id):
    """Sync inline SOP data from Stage 8 Standardization section to normalized sops & sop_steps tables."""
    if not sop_data:
        return
        
    from app.infrastructure.database.models.models import SOP, SOPStep, SOPApproval, Project, User, db
    
    project = db.session.get(Project, project_id)
    if not project:
        return
        
    sop = SOP.query.filter_by(project_id=project_id, org_id=project.org_id).first()
    
    title = sop_data.get('title') or f"{project.title} SOP"
    category = sop_data.get('category') or project.category or 'Quality'
    sop_type = sop_data.get('sop_type') or 'Operational'
    description = sop_data.get('description') or project.description
    purpose = sop_data.get('purpose')
    scope = sop_data.get('scope')
    applicability = sop_data.get('applicability')
    responsibilities = sop_data.get('responsibilities')
    
    if not sop:
        import random
        import string
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        sop_uid = f"SOP-{datetime.now(timezone.utc).replace(tzinfo=None).year}-{random_suffix}"
        
        sop = SOP(
            sop_uid=sop_uid,
            org_id=project.org_id,
            project_id=project_id,
            title=title,
            category=category,
            department_id=project.department_id,
            process_name=project.title,
            sop_type=sop_type,
            description=description,
            purpose=purpose,
            scope=scope,
            applicability=applicability,
            responsibilities=responsibilities,
            author_id=project.creator_id or user_id,
            owner_id=project.team_leader_id or project.creator_id or user_id,
            reviewer_id=project.reviewer_id,
            approver_id=project.facilitator_id,
            status='Draft',
            version=1
        )
        db.session.add(sop)
        db.session.flush() # Populate sop.id
        
        author_user = db.session.get(User, user_id)
        role_name = author_user.role.name if author_user else "System"
        approval = SOPApproval(
            sop_id=sop.id,
            user_id=user_id,
            role=role_name,
            action='Draft Created',
            comments='SOP automatically initialized via Stage 8 Standardization',
            signature=f"Signed by {author_user.full_name or author_user.username if author_user else 'System'} at {datetime.now(timezone.utc).replace(tzinfo=None).isoformat()}"
        )
        db.session.add(approval)
    else:
        # If active, we don't overwrite it directly unless in project flow
        sop.title = title
        sop.category = category
        sop.sop_type = sop_type
        sop.description = description
        sop.purpose = purpose
        sop.scope = scope
        sop.applicability = applicability
        sop.responsibilities = responsibilities
        sop.reviewer_id = project.reviewer_id
        sop.approver_id = project.facilitator_id
        sop.owner_id = project.team_leader_id or project.creator_id or user_id
        sop.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        
    # Delete old steps and recreate
    SOPStep.query.filter_by(sop_id=sop.id).delete()
    
    steps = sop_data.get('steps', [])
    for i, step in enumerate(steps):
        sop_step = SOPStep(
            sop_id=sop.id,
            step_number=step.get('step_number') or (i + 1),
            step_title=step.get('step_title', f"Step {i+1}"),
            instructions=step.get('instructions', ''),
            image_path=step.get('image_path'),
            video_path=step.get('video_path'),
            safety_notes=step.get('safety_notes'),
            quality_checkpoints=step.get('quality_checkpoints')
        )
        db.session.add(sop_step)

# ── GENERIC ROUTES FOR STAGES 2-N (DYNAMIC) ──

@project_bp.route('/<int:id>/stage/<int:stage_id>/save', methods=['POST'])
@jwt_required()
def save_stage_generic(id, stage_id):
    """Save Stage progress without submitting for review."""
    if stage_id < 2:
        return jsonify({"msg": "Invalid stage ID for generic route."}), 400

    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    project = db.session.get(Project, id)

    user_is_sa = bool(user and user.role and user.role.name == 'SuperAdmin')
    if not project or (not user_is_sa and project.org_id != user.org_id):
        return jsonify({"msg": "Project not found"}), 404

    # Check if project is permanently rejected
    if project.status in ('Rejected', 'Stage 1 Rejected') or (project.status and 'Rejected' in str(project.status)):
        return jsonify({"msg": "This project has been permanently rejected and cannot be modified or re-submitted."}), 400

    # STRICT RULE: Only assigned Team Leader or Team Member can edit stage details (Admin is read-only)
    is_authorized = user.role.name in ('Team Leader', 'Team Member')
    if not is_authorized:
        return jsonify({"msg": f"Access denied. Only assigned Team Leaders and Team Members can edit Stage {stage_id} details."}), 403

    payload = request.get_json() or {}
    workflow = ProjectWorkflow.query.filter_by(project_id=id, stage_id=stage_id).first()

    if not workflow:
        workflow = ProjectWorkflow(project_id=id, org_id=user.org_id, stage_id=stage_id, data={})
        db.session.add(workflow)

    # Merge incoming sections into existing data
    existing = dict(workflow.data or {})
    for section, section_data in payload.items():
        existing[section] = section_data
    workflow.data = existing
    flag_modified(workflow, 'data')
    workflow.updated_by = user_id
    workflow.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # Sync SOP if payload includes SOP data
    if 'sop' in payload:
        sync_sop_from_stage8(id, payload['sop'], user_id)

    from app.infrastructure.database.models.models import AuditLog
    db.session.add(AuditLog(
        org_id=user.org_id, project_id=id, user_id=user_id,
        action=f"Stage {stage_id} Draft Saved",
        details=f"Stage {stage_id} data draft saved by {user.username}.",
        ip_address=request.remote_addr, user_agent=request.user_agent.string,
        target_table="project_workflow", target_id=workflow.id
    ))
    db.session.commit()
    return jsonify({"msg": f"Stage {stage_id} progress saved."}), 200


@project_bp.route('/<int:id>/stage/<int:stage_id>/submit', methods=['POST'])
@jwt_required()
def submit_stage_generic(id, stage_id):
    """Submit Stage for advancement or Reviewer approval (Dynamically supports custom stages)."""
    if stage_id < 2:
        return jsonify({"msg": "Invalid stage ID."}), 400

    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    project = db.session.get(Project, id)

    user_is_sa = bool(user and user.role and user.role.name == 'SuperAdmin')
    if not project or (not user_is_sa and project.org_id != user.org_id):
        return jsonify({"msg": "Project not found"}), 404

    # Check if project is permanently rejected
    if project.status in ('Rejected', 'Stage 1 Rejected') or (project.status and 'Rejected' in str(project.status)):
        return jsonify({"msg": "This project has been permanently rejected and cannot be submitted for review."}), 400

    # STRICT RULE: Only assigned Team Leader or Team Member can submit stages (Admin is read-only)
    is_authorized = user.role.name in ('Team Leader', 'Team Member')
    if not is_authorized:
        return jsonify({"msg": f"Access denied. Only assigned Team Leaders and Team Members can submit Stage {stage_id} for review."}), 403

    org_stages = project.stages_config or (project.organization.get_stages_config() if project.organization else [])
    total_stages = len(org_stages) if org_stages else 8

    current_stage_cfg = None
    if org_stages and stage_id <= len(org_stages):
        current_stage_cfg = org_stages[stage_id - 1]
    
    original_id = current_stage_cfg.get('original_id', stage_id) if current_stage_cfg else stage_id
    is_closure_stage = (stage_id == total_stages) or (original_id == 8) or ('closure' in (current_stage_cfg.get('title', '') if current_stage_cfg else '').lower())

    tracker = ProjectStageTracker.query.filter_by(project_id=id, stage_number=stage_id).first()
    from app.presentation.routes.notification_routes import create_notification
    from app.infrastructure.database.models.models import AuditLog

    # SOP / Standard Verification gate: only check if this specific stage contains the standard verification section
    has_std_verif = False
    if current_stage_cfg and current_stage_cfg.get('sections'):
        has_std_verif = any(s.get('id') == 's2_std_verification' or 'standard verification' in s.get('label', '').lower() for s in current_stage_cfg.get('sections', []))
    elif original_id == 2:
        has_std_verif = True

    if has_std_verif:
        sv = {}
        wf_stage = ProjectWorkflow.query.filter_by(project_id=id, stage_id=stage_id).first()
        if wf_stage and isinstance(wf_stage.data, dict):
            sv = wf_stage.data.get('standard_verification') or wf_stage.data.get('interim_verification') or {}
        if not sv:
            from app.infrastructure.database.models.models import Stage2ObservationDataCollection
            s2 = Stage2ObservationDataCollection.query.filter_by(project_id=id).first()
            if s2:
                sv = s2.interim_verification or {}
        if sv:
            deviation_found = sv.get('sop_dev') or sv.get('spec_dev') or sv.get('cp_dev')
            if not deviation_found:
                not_followed = []
                if not sv.get('sop_follow'):
                    not_followed.append('SOP')
                if not sv.get('spec_follow'):
                    not_followed.append('Specification')
                if not sv.get('cp_follow'):
                    not_followed.append('Control Plan')
                if not sv.get('pfmea_review'):
                    not_followed.append('PFMEA')
                if not_followed:
                    return jsonify({
                        "msg": f"Submission blocked. No deviation was found, but the following standard plans are NOT followed: {', '.join(not_followed)}. Please follow/enforce the respective plans or mark the deviations before proceeding."
                    }), 400

    workflow = ProjectWorkflow.query.filter_by(project_id=id, stage_id=stage_id).first()
    if workflow:
        workflow.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # Intermediate Stages: Auto-complete and auto-advance to next stage
    if not is_closure_stage and stage_id < total_stages:
        if tracker:
            tracker.status = 'Completed'
            tracker.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)

        project.current_stage = stage_id + 1
        project.status = f"Stage {stage_id + 1} In Progress" if stage_id + 1 == total_stages else "In Progress"

        # Unlock next stage tracker
        next_tracker = ProjectStageTracker.query.filter_by(project_id=id, stage_number=stage_id + 1).first()
        if next_tracker:
            next_tracker.status = 'In Progress'
            next_tracker.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            next_tracker = ProjectStageTracker(
                project_id=id,
                org_id=project.org_id,
                stage_number=stage_id + 1,
                status='In Progress',
                started_at=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            db.session.add(next_tracker)

        db.session.add(AuditLog(
            org_id=user.org_id, project_id=id, user_id=user_id,
            action=f"Stage {stage_id} Completed",
            details=f"Stage {stage_id} submitted and auto-advanced to Stage {stage_id + 1}.",
            ip_address=request.remote_addr, user_agent=request.user_agent.string,
            target_table="project_stage_tracker", target_id=tracker.id if tracker else None
        ))
        db.session.commit()
        return jsonify({
            "msg": f"Stage {stage_id} completed and auto-advanced to Stage {stage_id + 1}.",
            "auto_advanced": True,
            "next_stage": stage_id + 1
        }), 200

    # Final Closure Stage: submit for Reviewer review
    if tracker:
        tracker.status = 'Submitted For Review'

    project.status = f"Stage {stage_id} Submitted"

    from app.infrastructure.database.models.models import SOP, SOPApproval
    sop = SOP.query.filter_by(project_id=id, org_id=user.org_id).first()
    if sop:
        sop.status = 'Under Review'
        approval = SOPApproval(
            sop_id=sop.id,
            user_id=user_id,
            role=user.role.name,
            action='Submit',
            comments=f"SOP submitted for review as part of Stage {stage_id} project closure",
            signature=f"Signed by {user.full_name or user.username} at {datetime.now(timezone.utc).replace(tzinfo=None).isoformat()}"
        )
        db.session.add(approval)

    # Notify the Reviewer
    if project.reviewer_id and project.reviewer_id != user_id:
        create_notification(
            user.org_id, project.reviewer_id,
            "Approval Request",
            f"Project '{project.title}' requires your approval for Stage {stage_id} closure.",
            f"/projects/project-details.html?id={project.id}",
            commit=False
        )

    db.session.add(AuditLog(
        org_id=user.org_id, project_id=id, user_id=user_id,
        action=f"Stage {stage_id} Submitted For Review",
        details=f"Stage {stage_id} submitted by {user.username}. Awaiting Reviewer approval.",
        ip_address=request.remote_addr, user_agent=request.user_agent.string,
        target_table="project_stage_tracker", target_id=tracker.id if tracker else None
    ))
    db.session.commit()

    # Trigger Reviewer Email Notification for Stage closure
    try:
        from app.domain.services.email_notification_engine import EmailNotificationEngine
        EmailNotificationEngine.trigger_project_review_requested_notification(project.id, stage_id, user_id)
    except Exception as e:
        print(f"[EmailEngine] Stage review notification error: {e}")

    return jsonify({"msg": f"Stage {stage_id} submitted for Reviewer review."}), 200

@project_bp.route('/<int:id>/request-facilitator-assistance', methods=['POST'])
@jwt_required()
def request_facilitator_assistance(id):
    """Allows a team member or leader to submit an assistance request directly to the assigned facilitator."""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    project = db.session.get(Project, id)

    user_is_sa = bool(user and user.role and user.role.name == 'SuperAdmin')
    if not project or (not user_is_sa and project.org_id != user.org_id):
        return jsonify({"msg": "Project not found"}), 404

    from app.infrastructure.database.models.models import Role, FacilitatorAssistanceRequest
    fac_user = project.facilitator
    if not fac_user or (fac_user.role and fac_user.role.name != 'Facilitator'):
        real_fac = User.query.join(Role).filter(
            User.org_id == project.org_id,
            User.is_active == True,
            Role.name == 'Facilitator'
        ).first()
        if real_fac:
            project.facilitator_id = real_fac.id
            db.session.commit()
            fac_user = real_fac

    if not project.facilitator_id:
        return jsonify({"msg": "No facilitator is currently assigned to this project."}), 400

    payload = request.get_json() or {}
    message = payload.get('message', '').strip()
    stage_id = int(payload.get('stage_id') or project.current_stage or 1)

    if not message:
        return jsonify({"msg": "Message is required."}), 400

    from app.presentation.routes.notification_routes import create_notification
    from app.infrastructure.database.models.models import AuditLog

    # Create assistance request record
    req_obj = FacilitatorAssistanceRequest(
        org_id=user.org_id,
        project_id=id,
        stage_id=stage_id,
        user_id=user_id,
        facilitator_id=project.facilitator_id,
        message=message,
        status='Pending'
    )
    db.session.add(req_obj)

    # Send notification to the facilitator
    create_notification(
        user.org_id,
        project.facilitator_id,
        "Assistance Requested",
        f"Team member '{user.full_name or user.username}' requested assistance for Stage {stage_id} on project '{project.title}': {message}",
        f"/projects/project-details.html?id={project.id}&stage={stage_id}",
        commit=False
    )

    db.session.add(AuditLog(
        org_id=user.org_id, project_id=id, user_id=user_id,
        action="Assistance Requested from Facilitator",
        details=f"Assistance requested from facilitator on Stage {stage_id}. Message: {message}",
        ip_address=request.remote_addr, user_agent=request.user_agent.string
    ))
    db.session.commit()

    # Trigger Facilitator Email Notification
    try:
        from app.domain.services.email_notification_engine import EmailNotificationEngine
        EmailNotificationEngine.trigger_facilitator_guidance_notification(project.id, user_id, message, stage_id)
    except Exception as e:
        print(f"[EmailEngine] Facilitator guidance notification error: {e}")

    return jsonify({"msg": "Assistance request sent to facilitator successfully."}), 200

@project_bp.route('/<int:id>/my-assistance-requests', methods=['GET'])
@jwt_required()
def get_my_assistance_requests(id):
    """Returns all assistance requests sent by the current user for a specific project (with facilitator replies)."""
    from app.infrastructure.database.models.models import FacilitatorAssistanceRequest
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    project = db.session.get(Project, id)

    if not project or (user.role.name != 'SuperAdmin' and project.org_id != user.org_id):
        return jsonify({"msg": "Project not found"}), 404

    stage_filter = request.args.get('stage')
    query = FacilitatorAssistanceRequest.query.filter_by(
        org_id=project.org_id,
        project_id=id,
        user_id=user_id
    )
    if stage_filter:
        query = query.filter_by(stage_id=int(stage_filter))

    requests_list = query.order_by(FacilitatorAssistanceRequest.created_at.desc()).all()
    return jsonify([{
        "id":            r.id,
        "stage_id":      r.stage_id,
        "message":       r.message,
        "status":        r.status,
        "response":      r.response,
        "created_at":    r.created_at.isoformat() + "Z" if r.created_at else None,
        "updated_at":    r.updated_at.isoformat() + "Z" if r.updated_at else None,
    } for r in requests_list]), 200

@project_bp.route('/<int:id>/stage/<int:stage_id>/review', methods=['POST'])
@jwt_required()
@role_required(['Reviewer', 'Facilitator', 'Admin'])
def review_stage_generic(id, stage_id):
    """Approve, Reject, or Send Back a stage."""
    if stage_id < 2 or stage_id > 8:
        return jsonify({"msg": "Invalid stage ID."}), 400

    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    project = db.session.get(Project, id)

    if not project or (user.role.name != 'SuperAdmin' and project.org_id != user.org_id):
        return jsonify({"msg": "Project not found"}), 404

    # Check if project is permanently rejected
    if project.status in ('Rejected', 'Stage 1 Rejected') or (project.status and 'Rejected' in str(project.status)):
        return jsonify({"msg": "This project has already been permanently rejected and cannot be reviewed again."}), 400

    # All 8 stages require Reviewer or Admin approval
    if user.role.name not in ('Reviewer', 'Admin'):
        return jsonify({"msg": f"Only a Reviewer can review Stage {stage_id}."}), 403

    payload = request.get_json()
    decision = payload.get('decision')  # 'approve' | 'reject' | 'send_back'
    comments = payload.get('comments', '')

    if decision not in ('approve', 'reject', 'send_back'):
        return jsonify({"msg": "Invalid decision."}), 400

    decision_map = {
        'approve': 'Approved',
        'reject': 'Rejected',
        'send_back': 'Revision'
    }
    mapped_decision = decision_map.get(decision)
    from app.presentation.routes.reviewer_routes import _process_decision_logic
    return _process_decision_logic(user, id, mapped_decision, comments, stage_id)

@project_bp.route('/<id_or_uid>', methods=['GET'])
@jwt_required()
def get_project_details(id_or_uid):
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    from sqlalchemy.orm import joinedload, selectinload
    proj_query = Project.query.options(
        joinedload(Project.department),
        joinedload(Project.creator),
        joinedload(Project.team_leader),
        joinedload(Project.facilitator),
        joinedload(Project.reviewer),
        selectinload(Project.members)
    )

    project = None
    if str(id_or_uid).isdigit():
        project = proj_query.filter_by(id=int(id_or_uid)).first()
    if not project:
        project = proj_query.filter(
            db.func.lower(Project.project_uid) == str(id_or_uid).lower()
        ).first()
        
    if not project:
        return jsonify({"msg": "Project not found"}), 404
    
    if user.role.name != 'SuperAdmin' and project.org_id != user.org_id:
        return jsonify({"msg": "Project not found"}), 404

    # Ensure project facilitator is a valid user with role 'Facilitator'
    from app.infrastructure.database.models.models import Role
    fac_user = project.facilitator
    if not fac_user or (fac_user.role and fac_user.role.name != 'Facilitator'):
        real_fac = User.query.join(Role).filter(
            User.org_id == project.org_id,
            User.is_active == True,
            Role.name == 'Facilitator'
        ).first()
        if real_fac:
            project.facilitator_id = real_fac.id
            db.session.commit()
            fac_user = real_fac
        else:
            fac_user = None
        
    role = user.role.name
    # Allow read-only visibility to closed/completed/archived projects for all users within the same organization
    is_archived_or_closed = project.status in ('Closed', 'Completed', 'Archived') or (project.current_stage == 8 and 'Approved' in (project.status or ''))
    
    if user.role.name != 'SuperAdmin' and not is_archived_or_closed:
        if role == 'Team Member':
            is_member = ProjectMember.query.filter_by(project_id=project.id, user_id=user.id).first()
            if not is_member and project.creator_id != user.id:
                return jsonify({"msg": "Unauthorized access. You are not assigned to this project."}), 403
        elif role == 'Team Leader':
            is_member = ProjectMember.query.filter_by(project_id=project.id, user_id=user.id).first()
            if project.team_leader_id != user.id and project.creator_id != user.id and not is_member and (user.dept and user.dept.name not in ['All', 'N/A'] and project.department_id != user.department_id):
                return jsonify({"msg": "Unauthorized access. You are not assigned to this project."}), 403
        elif role == 'Facilitator':
            if project.facilitator_id and project.facilitator_id != user.id and (not fac_user or fac_user.id != user.id):
                return jsonify({"msg": "Unauthorized access. You are not the facilitator for this project."}), 403
        elif role == 'Reviewer':
            # Reviewers can view projects they are specifically assigned to, or unassigned projects in their department/org
            if project.reviewer_id:
                if project.reviewer_id != user.id:
                    return jsonify({"msg": "Unauthorized access. You are not the reviewer for this project."}), 403
            else:
                if user.dept and user.dept.name not in ['All', 'N/A'] and project.department_id and project.department_id != user.department_id:
                    return jsonify({"msg": "Unauthorized access. You are not the reviewer for this project."}), 403


    # Fetch all stages for tracker
    stages = ProjectStageTracker.query.filter_by(project_id=project.id).order_by(ProjectStageTracker.stage_number).all()
    stage1_workflow = ProjectWorkflow.query.filter_by(project_id=project.id, stage_id=1).first()

    from app.infrastructure.database.models.models import ProjectReview, ImportedIdea
    reviews = ProjectReview.query.filter_by(project_id=project.id).order_by(ProjectReview.created_at.desc()).all()

    linked_idea = None
    if project.reference_number:
        imp_idea = ImportedIdea.query.filter_by(organization_id=user.org_id, idea_code=project.reference_number).first()
        if imp_idea:
            linked_idea = imp_idea.to_dict()

    completed_stage_numbers = {s.stage_number for s in stages if s.status in ('Completed', 'Approved')}
    wf_snapshots = {w.stage_id: w.template_snapshot for w in ProjectWorkflow.query.filter_by(project_id=project.id).all() if w.template_snapshot}

    return jsonify({
        "id": project.id,
        "project_uid": project.project_uid,
        "title": project.title,
        "description": project.description,
        "category": project.category,
        "project_source": project.project_source or "Manual",
        "reference_number": project.reference_number,
        "idea_code": project.reference_number if (project.project_source == 'Ideation Tool' or linked_idea) else None,
        "is_linked_idea": True if (project.project_source == 'Ideation Tool' or linked_idea) else False,
        "linked_idea": linked_idea,
        "current_stage": project.current_stage,
        "status": project.status,
        "rejection_reason": project.rejection_reason,
        "start_date": project.start_date.isoformat() if project.start_date else None,
        "end_date": project.end_date.isoformat() if project.end_date else None,
        "department": project.department.name if project.department else "N/A",
        "creator": project.creator.username if project.creator else "System",
        "creator_id": project.creator_id,
        "created_at": project.created_at.isoformat() + "Z",
        "work_area": project.work_area or (f"{project.plant} - {project.department.name}" if (project.plant and project.department) else (project.department.name if project.department else None)),
        "sponsor": project.sponsor or (f"{project.department.name} Head / Operations Manager" if project.department else "Plant Manager / Department Head"),
        "facilitator_id": fac_user.id if fac_user else None,
        "facilitator_name": (fac_user.full_name or fac_user.username) if fac_user else None,
        "facilitator_email": fac_user.email if fac_user else None,
        "team_leader_id": project.team_leader_id,
        "team_leader_name": (
            (project.team_leader.full_name or project.team_leader.username) if project.team_leader
            else (project.creator.full_name or project.creator.username if project.creator else "Team Leader")
        ),
        "reviewer_id": project.reviewer_id,
        "reviewer_name": (
            (db.session.get(User, project.reviewer_id).full_name or db.session.get(User, project.reviewer_id).username) if (project.reviewer_id and db.session.get(User, project.reviewer_id))
            else (User.query.join(Role).filter(User.org_id == user.org_id, Role.name == 'Reviewer', User.is_active == True).first().full_name if User.query.join(Role).filter(User.org_id == user.org_id, Role.name == 'Reviewer', User.is_active == True).first() else "Quality Reviewer")
        ),
        "department_id": project.department_id,
        "deadline": project.deadline.isoformat() if project.deadline else None,
        "plant_id": (
            project.department.plant_id if (project.department and project.department.plant_id)
            else (get_plant_ids_by_name(user.org_id, project.plant)[0] if (project.plant and get_plant_ids_by_name(user.org_id, project.plant))
            else (project.creator.plant_id if (project.creator and project.creator.plant_id) else None))
        ),
        "plant_name": (
            project.plant
            or (project.department.plant.name if project.department and project.department.plant else None)
            or (project.creator.plant.name if project.creator and project.creator.plant else None)
        ),
        "member_ids": [m.user_id for m in ProjectMember.query.filter_by(project_id=project.id).all()],
        "members": [{
            "id": m.user_id,
            "username": db.session.get(User, m.user_id).username if db.session.get(User, m.user_id) else "Member",
            "full_name": db.session.get(User, m.user_id).full_name if db.session.get(User, m.user_id) else "Member"
        } for m in ProjectMember.query.filter_by(project_id=project.id).all()],
        "stage1_data": stage1_workflow.data if stage1_workflow else {},
        "workflows": [{
            "stage_id": w.stage_id,
            "data": w.data
        } for w in ProjectWorkflow.query.filter_by(project_id=project.id).all()],
        "stages": [{
            "stage_number": s.stage_number,
            "status": s.status,
            "started_at": s.started_at.isoformat() + "Z" if s.started_at else None,
            "completed_at": s.completed_at.isoformat() + "Z" if s.completed_at else None
        } for s in stages],
        "reviews": [{
            "stage_number": r.stage_number,
            "decision": r.decision,
            "comments": r.comments,
            "decided_at": r.decided_at.isoformat() + "Z" if r.decided_at else None,
            "reviewer_name": db.session.get(User, r.reviewer_id).full_name if r.reviewer_id and db.session.get(User, r.reviewer_id) else "Reviewer"
        } for r in reviews],
        "stages_config": (lambda: [
            wf_snapshots.get(stg.get('stage_id') or stg.get('original_id')) if ((stg.get('stage_id') or stg.get('original_id')) in completed_stage_numbers and (stg.get('stage_id') or stg.get('original_id')) in wf_snapshots) else stg
            for stg in (project.stages_config or project.organization.get_stages_config())
        ])()
    }), 200

# ── Stage-Specific Meetings ──
@project_bp.route('/<int:project_id>/stage/<int:stage_id>/meetings', methods=['GET'])
@jwt_required()
def get_stage_meetings(project_id, stage_id):
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    project = db.session.get(Project, project_id)
    
    if not project or (user.role.name != 'SuperAdmin' and project.org_id != user.org_id):
        return jsonify({"msg": "Project not found"}), 404
        
    from app.infrastructure.database.models.models import ProjectMeeting
    meetings = ProjectMeeting.query.filter_by(project_id=project_id, stage_id=stage_id).order_by(ProjectMeeting.scheduled_at.asc()).all()
    
    return jsonify([{
        "id": m.id,
        "title": m.title,
        "meeting_type": m.meeting_type,
        "scheduled_at": m.scheduled_at.isoformat(),
        "duration": m.duration,
        "url": m.url
    } for m in meetings]), 200

@project_bp.route('/<int:project_id>/stage/<int:stage_id>/meetings', methods=['POST'])
@jwt_required()
def create_stage_meeting(project_id, stage_id):
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    project = db.session.get(Project, project_id)
    
    if not project or (user.role.name != 'SuperAdmin' and project.org_id != user.org_id):
        return jsonify({"msg": "Project not found"}), 404
        
    data = request.get_json() or {}
    title = data.get('title')
    meeting_type = data.get('meeting_type')
    scheduled_at_str = data.get('scheduled_at')
    duration = data.get('duration')
    url = data.get('url')
    
    if not title or not meeting_type or not scheduled_at_str or not duration:
        return jsonify({"msg": "Missing required fields"}), 400
        
    if meeting_type == 'online' and not url:
        return jsonify({"msg": "URL is required for online meetings"}), 400
        
    try:
        scheduled_at = datetime.fromisoformat(scheduled_at_str.replace('Z', ''))
    except ValueError:
        return jsonify({"msg": "Invalid date format, use ISO format (YYYY-MM-DDTHH:MM:SS)"}), 400
        
    try:
        duration = int(duration)
    except ValueError:
        return jsonify({"msg": "Duration must be an integer"}), 400

    from app.infrastructure.database.models.models import ProjectMeeting
    new_meeting = ProjectMeeting(
        org_id=user.org_id,
        project_id=project_id,
        stage_id=stage_id,
        title=title,
        meeting_type=meeting_type,
        scheduled_at=scheduled_at,
        duration=duration,
        url=url if meeting_type == 'online' else None
    )
    
    db.session.add(new_meeting)
    
    # Collect all user IDs involved in the project
    recipients = set()
    if project.creator_id:
        recipients.add(project.creator_id)
    if project.team_leader_id:
        recipients.add(project.team_leader_id)
    if project.facilitator_id:
        recipients.add(project.facilitator_id)
    if project.reviewer_id:
        recipients.add(project.reviewer_id)
    for m in project.members:
        recipients.add(m.id)

    # Exclude the user who scheduled it
    recipients.discard(user_id)

    # Create notifications
    from app.presentation.routes.notification_routes import create_notification
    for rid in recipients:
        create_notification(
            org_id=user.org_id,
            user_id=rid,
            title="Meeting Scheduled",
            message=f"Meeting '{title}' ({meeting_type}) has been scheduled for project '{project.title}' (Stage {stage_id}) at {scheduled_at.strftime('%Y-%m-%d %H:%M')}.",
            link=f"/projects/project-details.html?id={project.id}",
            commit=False
        )
    db.session.commit()
    
    return jsonify({
        "id": new_meeting.id,
        "title": new_meeting.title,
        "meeting_type": new_meeting.meeting_type,
        "scheduled_at": new_meeting.scheduled_at.isoformat(),
        "duration": new_meeting.duration,
        "url": new_meeting.url
    }), 201

@project_bp.route('/<int:id>/stage/<int:stage_num>', methods=['GET'])
@jwt_required()
def get_project_stage_details(id, stage_num):
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    project = db.session.get(Project, id)

    user_is_sa = bool(user and user.role and user.role.name == 'SuperAdmin')
    if not project or (not user_is_sa and project.org_id != user.org_id):
        return jsonify({"msg": "Project not found"}), 404

    from app.infrastructure.database.models.models import (
        Stage1ProblemDefinitionProjectInitiation, Stage2ObservationDataCollection, Stage3CauseIdentification,
        Stage4RootCauseAnalysisVerification, Stage5CountermeasurePlanningSolutionDevelopment, Stage6ImplementationChangeManagement,
        Stage7PerformanceVerificationBenefitsRealization, Stage8StandardizationKnowledgeSharingProjectClosure
    )

    stage_models = {
        1: Stage1ProblemDefinitionProjectInitiation, 2: Stage2ObservationDataCollection, 3: Stage3CauseIdentification,
        4: Stage4RootCauseAnalysisVerification, 5: Stage5CountermeasurePlanningSolutionDevelopment, 6: Stage6ImplementationChangeManagement,
        7: Stage7PerformanceVerificationBenefitsRealization, 8: Stage8StandardizationKnowledgeSharingProjectClosure
    }

    model = stage_models.get(stage_num)
    if not model:
        return jsonify({"msg": "Invalid stage number"}), 400

    stage_data = model.query.filter_by(project_id=id).first()

    # Standardize data to dict
    data = {}
    if stage_data:
        data = {c.name: getattr(stage_data, c.name) for c in stage_data.__table__.columns}
        if hasattr(stage_data, 'standard_verification') and 'standard_verification' not in data:
            data['standard_verification'] = stage_data.standard_verification
        # Clean up
        data.pop('id', None)
        data.pop('project_id', None)
        data.pop('org_id', None)
        # Convert datetimes to isoformat
        for k, v in data.items():
            if isinstance(v, datetime):
                data[k] = v.isoformat() + "Z"

    return jsonify(data), 200


@project_bp.route('/<int:id>/stage/<int:stage_num>', methods=['POST'])
@jwt_required()
def update_project_stage(id, stage_num):
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    project = db.session.get(Project, id)

    user_is_sa = bool(user and user.role and user.role.name == 'SuperAdmin')
    if not project or (not user_is_sa and project.org_id != user.org_id):
        return jsonify({"msg": "Project not found"}), 404

    if stage_num == 1:
        if user.role.name not in ('Admin', 'SuperAdmin', 'Team Leader', 'Team Member'):
            return jsonify({"msg": "Access denied. Only Admin, Team Leader and Team Member can add/edit Stage 1 details."}), 403
    elif 2 <= stage_num <= 8:
        if user.role.name not in ('Team Member', 'Team Leader'):
            return jsonify({"msg": f"Access denied. Only Team Members and Leaders can add/edit Stage {stage_num} details."}), 403

    # RBAC: TL, Admin, Facilitator or assigned members
    is_member = ProjectMember.query.filter_by(project_id=id, user_id=user_id).first()
    is_admin_or_global_role = user and user.role and user.role.name in ['Admin', 'Team Leader', 'Team Member', 'Facilitator']
    is_project_owner = project.creator_id == user_id
    is_project_leader = project.team_leader_id == user_id
    is_project_facilitator = project.facilitator_id == user_id

    if not any([is_member, is_admin_or_global_role, is_project_owner, is_project_leader, is_project_facilitator]):
        return jsonify({"msg": "Unauthorized"}), 403

    from app.infrastructure.database.models.models import (
        Stage1ProblemDefinitionProjectInitiation, Stage2ObservationDataCollection, Stage3CauseIdentification,
        Stage4RootCauseAnalysisVerification, Stage5CountermeasurePlanningSolutionDevelopment, Stage6ImplementationChangeManagement,
        Stage7PerformanceVerificationBenefitsRealization, Stage8StandardizationKnowledgeSharingProjectClosure, ProjectStageTracker,
        AuditLog
    )

    stage_models = {
        1: Stage1ProblemDefinitionProjectInitiation, 2: Stage2ObservationDataCollection, 3: Stage3CauseIdentification,
        4: Stage4RootCauseAnalysisVerification, 5: Stage5CountermeasurePlanningSolutionDevelopment, 6: Stage6ImplementationChangeManagement,
        7: Stage7PerformanceVerificationBenefitsRealization, 8: Stage8StandardizationKnowledgeSharingProjectClosure
    }

    model = stage_models.get(stage_num)
    if not model:
        return jsonify({"msg": "Invalid stage number"}), 400

    data = request.get_json()
    stage_data = model.query.filter_by(project_id=id).first()

    if not stage_data:
        # Initialize if missing
        stage_data = model(project_id=id, org_id=user.org_id)
        db.session.add(stage_data)

    # Dynamically update fields
    for key, value in data.items():
        if hasattr(stage_data, key) and key not in ['id', 'project_id', 'org_id']:
            setattr(stage_data, key, value)

    # Update tracker if stage is being completed
    if data.get('action') == 'submit':
        tracker = ProjectStageTracker.query.filter_by(project_id=id, stage_number=stage_num).first()
        if tracker:
            tracker.status = 'Completed'
            tracker.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)

            # Note: Stage advancement is now handled via the /api/workflow/projects/<id>/transitions endpoint
            # to ensure all security gates (approvals/validations) are checked.

        # If it's the final stage, we still want to mark the project as completed
        if stage_num == 8:
            project.status = 'Completed'

    # Audit Log
    audit = AuditLog(
        org_id=user.org_id,
        project_id=id,
        user_id=user_id,
        action=f"Updated Stage {stage_num}",
        details=f"Stage {stage_num} updated. Action: {data.get('action', 'save')}",
        target_table=model.__tablename__,
        target_id=stage_data.id if stage_data.id else id
    )
    db.session.add(audit)

    db.session.commit()
    return jsonify({"msg": f"Stage {stage_num} updated successfully", "current_stage": project.current_stage}), 200


@project_bp.route('/<int:id>/activity', methods=['GET'])
@jwt_required()
def get_project_activity(id):
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    project = db.session.get(Project, id)
    user_is_sa = bool(user and user.role and user.role.name == 'SuperAdmin')
    if not project or (not user_is_sa and project.org_id != user.org_id):
        return jsonify({"msg": "Project not found"}), 404
        
    # Check authorization
    role = user.role.name
    authorized = False
    if role in ('Admin', 'CEO', 'SuperAdmin'):
        authorized = True
    elif role == 'Facilitator':
        authorized = (project.facilitator_id == user.id or not project.facilitator_id)
    elif role == 'Reviewer':
        authorized = (project.reviewer_id == user.id or not project.reviewer_id or (project.department_id and project.department_id == user.department_id))
    elif role == 'Team Leader':
        authorized = (project.department_id == user.department_id or project.team_leader_id == user.id or project.creator_id == user.id)
    elif role == 'Team Member':
        is_member = ProjectMember.query.filter_by(project_id=id, user_id=user_id).first()
        authorized = (is_member is not None or project.creator_id == user.id)
        
    if not authorized:
        return jsonify({"msg": "Project not found"}), 404
        
    from app.infrastructure.database.models.models import AuditLog
    logs = AuditLog.query.filter_by(project_id=id).order_by(AuditLog.created_at.desc()).all()
    
    return jsonify([{
        "id": log.id,
        "action": log.action,
        "details": log.details,
        "created_at": log.created_at.isoformat() + "Z"
    } for log in logs]), 200

@project_bp.route('/<int:id>', methods=['PATCH', 'PUT'])
@jwt_required()
def update_project(id):
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    project = db.session.get(Project, id)

    user_is_sa = bool(user and user.role and user.role.name == 'SuperAdmin')
    if not project or (not user_is_sa and project.org_id != user.org_id):
        return jsonify({"msg": "Project not found"}), 404

    # RBAC: Only Admin, SuperAdmin, Project Creator, TL or TL of same dept
    can_edit = ((user.role and user.role.name in ('Admin', 'SuperAdmin')) or 
                project.creator_id == user.id or 
                project.team_leader_id == user.id or
                (user.role and user.role.name == 'Team Leader' and project.department_id == user.department_id))

    if not can_edit:
        return jsonify({"msg": "Permission denied"}), 403

    data = request.json
    if 'title' in data: project.title = data['title']
    if 'description' in data: project.description = data['description']
    if 'category' in data: project.category = data['category']
    if 'department_id' in data: project.department_id = data['department_id']
    old_tl = project.team_leader_id
    old_fac = project.facilitator_id
    old_rev = project.reviewer_id
    from app.infrastructure.database.models.models import AuditLog, User
    from flask import request as flask_request
    ua_str = getattr(flask_request.user_agent, 'string', str(flask_request.user_agent or ''))

    if 'facilitator_id' in data:
        fid = data['facilitator_id']
        new_fac = int(fid) if fid is not None and str(fid).strip() != "" else None
        if new_fac != old_fac:
            project.facilitator_id = new_fac
            old_f = db.session.get(User, old_fac) if old_fac else None
            new_f = db.session.get(User, new_fac) if new_fac else None
            db.session.add(AuditLog(
                org_id=user.org_id, project_id=id, user_id=user_id,
                action="Facilitator Assigned / Transitioned",
                details=f"Facilitator changed from {old_f.full_name or old_f.username if old_f else 'None'} to {new_f.full_name or new_f.username if new_f else 'Unassigned'}.",
                ip_address=flask_request.remote_addr, user_agent=ua_str,
                target_table="projects", target_id=id
            ))
            if new_fac and new_fac != user_id:
                from app.presentation.routes.notification_routes import create_notification
                create_notification(user.org_id, new_fac, "Project Assigned", f"You have been assigned as the Facilitator for project '{project.title}'.", f"/projects/project-details.html?id={project.id}", commit=False)

    if 'team_leader_id' in data:
        tl_val = data['team_leader_id']
        new_tl = int(tl_val) if tl_val is not None and str(tl_val).strip() != "" else None
        if new_tl != old_tl:
            project.team_leader_id = new_tl
            old_t = db.session.get(User, old_tl) if old_tl else None
            new_t = db.session.get(User, new_tl) if new_tl else None
            db.session.add(AuditLog(
                org_id=user.org_id, project_id=id, user_id=user_id,
                action="Team Leader Assigned / Transitioned",
                details=f"Team Leader changed from {old_t.full_name or old_t.username if old_t else 'None'} to {new_t.full_name or new_t.username if new_t else 'Unassigned'}.",
                ip_address=flask_request.remote_addr, user_agent=ua_str,
                target_table="projects", target_id=id
            ))
            if new_tl and new_tl != user_id:
                from app.presentation.routes.notification_routes import create_notification
                create_notification(user.org_id, new_tl, "Project Assigned", f"You have been assigned as the Team Leader for project '{project.title}'.", f"/projects/project-details.html?id={project.id}", commit=False)

    if 'reviewer_id' in data:
        rid = data['reviewer_id']
        new_rev = int(rid) if rid is not None and str(rid).strip() != "" else None
        if new_rev != old_rev:
            project.reviewer_id = new_rev
            old_r = db.session.get(User, old_rev) if old_rev else None
            new_r = db.session.get(User, new_rev) if new_rev else None
            db.session.add(AuditLog(
                org_id=user.org_id, project_id=id, user_id=user_id,
                action="Reviewer Assigned / Transitioned",
                details=f"Reviewer changed from {old_r.full_name or old_r.username if old_r else 'None'} to {new_r.full_name or new_r.username if new_r else 'Unassigned'}.",
                ip_address=flask_request.remote_addr, user_agent=ua_str,
                target_table="projects", target_id=id
            ))
            if new_rev and new_rev != user_id:
                from app.presentation.routes.notification_routes import create_notification
                create_notification(user.org_id, new_rev, "Project Assigned", f"You have been assigned as the Reviewer for project '{project.title}'.", f"/projects/project-details.html?id={project.id}", commit=False)

    if 'deadline' in data:
        try:
            if data['deadline']:
                project.deadline = datetime.strptime(data['deadline'], '%Y-%m-%d').date()
            else:
                project.deadline = None
        except (ValueError, TypeError):
            pass

    if 'member_ids' in data:
        raw_member_ids = data['member_ids']
        if isinstance(raw_member_ids, list):
            old_member_ids = set([m.user_id for m in ProjectMember.query.filter_by(project_id=id).all()])
            cleaned_member_ids = set()
            for mid in raw_member_ids:
                if mid is not None:
                    try:
                        uid_val = int(mid)
                        if uid_val > 0:
                            cleaned_member_ids.add(uid_val)
                    except (ValueError, TypeError):
                        pass

            # Ensure creator is always a member if creator_id exists and is valid
            if project.creator_id:
                try:
                    c_id = int(project.creator_id)
                    if c_id > 0:
                        cleaned_member_ids.add(c_id)
                except (ValueError, TypeError):
                    pass

            # Detect added members
            added_ids = cleaned_member_ids - old_member_ids
            for added_id in added_ids:
                u_obj = db.session.get(User, added_id)
                u_name = u_obj.full_name or u_obj.username if u_obj else f"User #{added_id}"
                db.session.add(AuditLog(
                    org_id=user.org_id, project_id=id, user_id=user_id,
                    action="Team Member Joined Project",
                    details=f"{u_name} was added and joined the active project team.",
                    ip_address=flask_request.remote_addr, user_agent=ua_str,
                    target_table="project_members", target_id=added_id
                ))

            # Detect removed members (left project in middle)
            removed_ids = old_member_ids - cleaned_member_ids
            for rem_id in removed_ids:
                u_obj = db.session.get(User, rem_id)
                u_name = u_obj.full_name or u_obj.username if u_obj else f"User #{rem_id}"
                db.session.add(AuditLog(
                    org_id=user.org_id, project_id=id, user_id=user_id,
                    action="Team Member Left Project (Transitioned in Middle)",
                    details=f"{u_name} left the project team / membership was removed from active roster.",
                    ip_address=flask_request.remote_addr, user_agent=ua_str,
                    target_table="project_members", target_id=rem_id
                ))

            # Clear existing members and re-insert sanitized list
            ProjectMember.query.filter_by(project_id=id).delete()
            for uid in cleaned_member_ids:
                db.session.add(ProjectMember(project_id=id, user_id=uid))

    db.session.commit()
    return jsonify({"msg": "Project updated successfully"}), 200


@project_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
@role_required(['Admin', 'Team Leader', 'Team Member'])
def delete_project(id):
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    project = db.session.get(Project, id)
    
    user_is_sa = bool(user and user.role and user.role.name == 'SuperAdmin')
    if not project or (not user_is_sa and project.org_id != user.org_id):
        return jsonify({"msg": "Project not found"}), 404
        
    # RBAC: Both Admin and Team Leader/Member (of the same department) should be able to delete
    can_delete = (user_is_sa or
                  user.role.name == 'Admin' or 
                  (user.role.name in ('Team Leader', 'Team Member') and project.department_id == user.department_id) or
                  project.creator_id == user.id)
    
    if not can_delete:
        return jsonify({"msg": "Permission denied. Only Admins and Team Leaders/Members (of the same department) can delete projects."}), 403
        
    try:
        from sqlalchemy import text
        import logging

        # ── DELETE order: grandchild tables first, then child tables, then projects ──
        # Ordered so that tables referencing other child tables come before the parent child
        tables_to_clean = [
            # ── Grandchild rows (rows that reference child table PKs) ──
            'qc_check_sheet_entries',   # -> qc_check_sheet_rows -> qc_check_sheets -> projects
            'qc_check_sheet_rows',      # -> qc_check_sheets -> projects
            'qc_pareto_items',          # -> qc_pareto_charts -> projects
            'qc_stratification_items',  # -> qc_stratifications -> projects
            'qc_process_steps',         # -> qc_process_maps -> projects
            'qc_fishbone_branches',     # -> qc_fishbone_diagrams -> projects
            'qc_scatter_points',        # -> qc_scatter_diagrams -> projects
            'qc_control_points',        # -> qc_control_charts -> projects

            # ── Direct child tables (FK -> projects.id) ──
            'audit_logs',
            'facilitator_notes',
            'facilitator_assistance_requests',
            'project_reviews',
            'project_workflow',
            'project_meetings',
            'project_members',
            'kpi_metrics',
            'kpi_dashboard_cache',
            'project_stage_tracker',
            'knowledge_repository',
            'employee_points',

            # ── QC tool parent tables ──
            'qc_check_sheets',
            'qc_pareto_charts',
            'qc_stratifications',
            'qc_process_maps',
            'qc_fishbone_diagrams',
            'qc_scatter_diagrams',
            'qc_control_charts',

            # ── Stage data tables ──
            'stage_1_problem_definition_project_initiation',
            'stage_2_observation_data_collection',
            'stage_3_cause_identification',
            'stage_4_root_cause_analysis_verification',
            'stage_5_countermeasure_planning_solution_development',
            'stage_6_implementation_change_management',
            'stage_7_performance_verification_benefits_realization',
            'stage_8_standardization_knowledge_sharing_project_closure',
        ]
        
        for table in tables_to_clean:
            try:
                with db.session.begin_nested():
                    db.session.execute(
                        text(f"DELETE FROM {table} WHERE project_id = :pid"),
                        {"pid": id}
                    )
            except Exception as e:
                err_str = str(e).lower()
                # Ignore if table doesn't exist yet (feature not used by this org)
                if "does not exist" not in err_str and "no such table" not in err_str and "undefined" not in err_str:
                    import logging
                    logging.warning(f"[delete_project] Failed to delete from '{table}': {e}")
        
        # Finally delete the project row itself
        db.session.execute(text("DELETE FROM projects WHERE id = :pid"), {"pid": id})
        db.session.commit()
        
        try:
            from app.domain.services.cache_service import CacheService
            CacheService.invalidate_project_cache(project.org_id)
        except Exception:
            pass

        return jsonify({"msg": "Project and all associated data deleted successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        import logging
        logging.getLogger('qcms.projects').exception("[delete_project] FATAL error deleting project %s: %s", id, e)
        return jsonify({
            "status": "error",
            "msg": "Failed to delete project due to system error. Please try again later."
        }), 500



@project_bp.route('/upload-evidence', methods=['POST'])
@jwt_required()
def upload_project_evidence():
    """General evidence upload for all project roles and stages (PDF, PPT, Images, Videos, Docs)."""
    if 'file' not in request.files:
        return jsonify({"msg": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"msg": "No selected file"}), 400
        
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    allowed_extensions = (
        'pdf', 'docx', 'xlsx', 'xls', 'pptx', 'ppt', 
        'png', 'jpg', 'jpeg', 'gif', 
        'mp4', 'mkv', 'avi', 'webm', 'mov'
    )
    import os
    from werkzeug.utils import secure_filename
    from datetime import datetime
    from flask import current_app

    # Check file size (Strict 2MB limit: 2 * 1024 * 1024 bytes)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
    if file_size > MAX_FILE_SIZE:
        size_mb = round(file_size / (1024 * 1024), 2)
        return jsonify({"msg": f"File size exceeds 2MB limit ({size_mb} MB). Please upload a document up to 2MB."}), 400
    
    from app.infrastructure.storage import storage
    filename = secure_filename(file.filename)
    target_name = f"ev_{datetime.now(timezone.utc).replace(tzinfo=None).strftime('%Y%m%d_%H%M%S')}_{filename}"
    result = storage.save_file(file, filename=target_name, subfolder="project_evidence")
    
    return jsonify({
        "url": result['url'],
        "name": file.filename,
        "storage_backend": result.get('backend', 'local')
    }), 200


@project_bp.route('/<int:project_id>/close', methods=['POST'])
@jwt_required()
def close_project(project_id):
    """
    Slim Route Handler delegating full closure lifecycle to ProjectClosureService.
    """
    current_user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    comments = data.get('comments', 'Project officially closed.')

    from app.domain.services.project_closure_service import ProjectClosureService
    try:
        result = ProjectClosureService.execute_closure(
            project_id=project_id,
            user_id=current_user_id,
            comments=comments,
            sign_off_by_role="Admin"
        )
        return jsonify(result), 200
    except ValueError as val_err:
        return jsonify({"status": "error", "message": str(val_err)}), 404
    except PermissionError as perm_err:
        return jsonify({"status": "error", "message": str(perm_err)}), 403
    except Exception as err:
        db.session.rollback()
        return internal_server_error(err, "Project closure failed.")

