from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from app import db
from app.presentation.middleware.middleware import super_admin_required, sub_role_required, sub_role_write_required
from app.infrastructure.database.models.models import (
    Module, ModuleDependency, ModuleAssignment, ModulePermission,
    ModuleUsageAnalytics, ModuleAuditLog, User, Organization, SaaSPlan, SaaSPlanModules
)
from datetime import datetime, timezone

modules_bp = Blueprint('modules_routes', __name__)


def _log_module_action(module_id, action, details, admin_name="SuperAdmin"):
    """Helper to write to ModuleAuditLog"""
    log = ModuleAuditLog(
        module_id=module_id,
        admin_name=admin_name,
        action=action,
        details=details,
        timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.session.add(log)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


@modules_bp.route('/active', methods=['GET'])
def get_active_features():
    """
    Client-side evaluation endpoint returning a dictionary of feature codes and their boolean status.
    Controls UI visibility, buttons, widgets, and navigation across the entire application.
    """
    user = None
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        if user_id:
            user = db.session.get(User, int(user_id))
    except Exception:
        pass

    from app.presentation.middleware.middleware import check_feature_access

    all_modules = Module.query.filter_by(is_archived=False).all()
    flags = {}
    for m in all_modules:
        allowed, _ = check_feature_access(user, m.code)
        flags[m.code] = allowed

    return jsonify({
        "status": "success",
        "data": flags
    }), 200


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: get_module_tree (Lines 60-106)
# Reason: Unused module tree endpoint. Frontend builds tree dynamically on the client side.
# ==============================================================================
# @modules_bp.route('/tree', methods=['GET'])
# @jwt_required()
# @super_admin_required()
# def get_module_tree():
#     """Returns full Parent -> Children hierarchical tree of all feature modules"""
#     parent_modules = Module.query.filter_by(is_archived=False, parent_id=None).order_by(Module.display_order).all()

#     def serialize_node(m):
#         children = Module.query.filter_by(is_archived=False, parent_id=m.id).order_by(Module.display_order).all()
#         plan_assignments = [a.assigned_target for a in m.assignments if a.assigned_type == 'Plan']
#         return {
#             "id": m.id,
#             "parent_id": m.parent_id,
#             "name": m.name,
#             "code": m.code,
#             "category": m.category,
#             "description": m.description,
#             "icon": m.icon,
#             "color": m.color,
#             "status": m.status,
#             "development_stage": m.development_stage,
#             "version": m.version,
#             "minimum_plan": m.minimum_plan,
#             "visible_in_sidebar": m.visible_in_sidebar,
#             "visible_in_dashboard": m.visible_in_dashboard,
#             "page_visibility": m.page_visibility,
#             "widget_visibility": m.widget_visibility,
#             "button_visibility": m.button_visibility,
#             "api_enabled": m.api_enabled,
#             "frontend_enabled": m.frontend_enabled,
#             "backend_enabled": m.backend_enabled,
#             "export_enabled": m.export_enabled,
#             "import_enabled": m.import_enabled,
#             "notification_enabled": m.notification_enabled,
#             "background_jobs_enabled": m.background_jobs_enabled,
#             "premium_feature": m.premium_feature,
#             "ai_enabled": m.ai_enabled,
#             "system_module": m.system_module,
#             "plans": plan_assignments,
#             "children": [serialize_node(c) for c in children]
#         }

#     tree_data = [serialize_node(p) for p in parent_modules]
#     return jsonify({
#         "status": "success",
#         "data": tree_data
#     }), 200
# [END DEAD CODE: get_module_tree]



# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: bulk_toggle_modules (Lines 109-138)
# Reason: Unused bulk module toggle.
# ==============================================================================
# @modules_bp.route('/bulk-toggle', methods=['POST'])
# @jwt_required()
# @super_admin_required()
# def bulk_toggle_modules():
#     """Bulk enables or disables a list of feature module IDs"""
#     data = request.json or {}
#     module_ids = data.get('module_ids', [])
#     target_status = data.get('status', 'Active') # Active or Inactive/Disabled

#     if not module_ids:
#         return jsonify({"status": "error", "message": "No module_ids specified"}), 400

#     modules = Module.query.filter(Module.id.in_(module_ids), Module.is_archived == False).all()
#     count = 0
#     for m in modules:
#         if m.system_module and target_status in ('Inactive', 'Disabled'):
#             continue # Skip core system modules
#         m.status = target_status
#         # If parent is disabled, disable children as well
#         if target_status in ('Inactive', 'Disabled'):
#             for child in m.children:
#                 child.status = target_status
#         count += 1
#         _log_module_action(m.id, "BULK_TOGGLE", f"Bulk status set to {target_status}")

#     db.session.commit()
#     return jsonify({
#         "status": "success",
#         "message": f"Successfully updated status for {count} modules."
#     }), 200
# [END DEAD CODE: bulk_toggle_modules]



@modules_bp.route('', methods=['GET'])
@jwt_required()
@super_admin_required()
@sub_role_required('modules')
def list_modules():
    """Lists all modules with search, sort, filter and pagination support (Tier 1 Redis cached)"""
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    status = request.args.get('status', '').strip()
    plan = request.args.get('plan', '').strip()
    
    sort_by = request.args.get('sort_by', 'display_order')
    sort_dir = request.args.get('sort_dir', 'asc')
    
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 500))
    if request.args.get('all') == 'true':
        per_page = 1000
    
    from app.domain.services.cache_service import CacheService

    def _fetch_modules_payload():
        query = Module.query.filter_by(is_archived=False)
        
        if q:
            query = query.filter(
                (Module.name.ilike(f'%{q}%')) |
                (Module.code.ilike(f'%{q}%')) |
                (Module.description.ilike(f'%{q}%'))
            )
        if category:
            query = query.filter(Module.category.ilike(f'%{category}%'))
        if status:
            if status == 'Active':
                query = query.filter(Module.status == 'Active')
            elif status == 'Inactive':
                query = query.filter(Module.status.in_(['Inactive', 'Disabled']))
            elif status == 'Deprecated':
                query = query.filter(Module.status == 'Deprecated')
            elif status == 'Beta':
                query = query.filter((Module.beta_feature == True) | (Module.status == 'Beta'))
            elif status == 'Premium':
                query = query.filter(Module.premium_feature == True)
            elif status == 'AI':
                query = query.filter(Module.ai_enabled == True)
            elif status == 'System':
                query = query.filter(Module.system_module == True)
            else:
                query = query.filter(Module.status == status)
        if plan:
            query = query.join(ModuleAssignment).filter(
                ModuleAssignment.assigned_type == 'Plan',
                ModuleAssignment.assigned_target == plan
            )
            
        # Dynamic Sorting
        sort_col = getattr(Module, sort_by, Module.display_order)
        if sort_dir.lower() == 'desc':
            query = query.order_by(sort_col.desc())
        else:
            query = query.order_by(sort_col.asc())
            
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        modules = pagination.items
        
        data = []
        for m in modules:
            plan_assignments = [a.assigned_target for a in m.assignments if a.assigned_type == 'Plan']
            org_assignments = [int(a.assigned_target) for a in m.assignments if a.assigned_type == 'Organization' and str(a.assigned_target).isdigit()]
            
            if org_assignments:
                assigned_orgs_count = Organization.query.filter(
                    Organization.is_deleted == False,
                    db.or_(
                        (Organization.subscription_plan.in_(plan_assignments)) if plan_assignments else db.false(),
                        (Organization.id.in_(org_assignments))
                    )
                ).count()
            else:
                if m.status == 'Active' and not m.premium_feature:
                    assigned_orgs_count = Organization.query.filter(Organization.is_deleted == False).count()
                    all_plan_names = [p.name for p in SaaSPlan.query.filter_by(status='Active').all()]
                    plan_assignments = all_plan_names
                else:
                    assigned_orgs_count = 0
            
            parent_name = m.parent.name if m.parent else None
            
            data.append({
                "id": m.id,
                "parent_id": m.parent_id,
                "parent_name": parent_name,
                "name": m.name,
                "code": m.code,
                "description": m.description,
                "category": m.category,
                "icon": m.icon,
                "color": m.color,
                "display_order": m.display_order,
                "navigation_route": m.navigation_route,
                "status": m.status,
                "development_stage": m.development_stage,
                "version": m.version,
                "minimum_plan": m.minimum_plan,
                "enable_by_default": m.enable_by_default,
                "visible_in_sidebar": m.visible_in_sidebar,
                "visible_in_dashboard": m.visible_in_dashboard,
                "page_visibility": m.page_visibility,
                "widget_visibility": m.widget_visibility,
                "button_visibility": m.button_visibility,
                "api_enabled": m.api_enabled,
                "frontend_enabled": m.frontend_enabled,
                "backend_enabled": m.backend_enabled,
                "export_enabled": m.export_enabled,
                "import_enabled": m.import_enabled,
                "notification_enabled": m.notification_enabled,
                "background_jobs_enabled": m.background_jobs_enabled,
                "requires_license": m.requires_license,
                "requires_subscription": m.requires_subscription,
                "premium_feature": m.premium_feature,
                "ai_enabled": m.ai_enabled,
                "beta_feature": m.beta_feature,
                "system_module": m.system_module,
                "feature_flags": m.feature_flags,
                "children_count": len(m.children),
                "assigned_orgs_count": assigned_orgs_count,
                "plans": plan_assignments,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "updated_at": m.updated_at.isoformat() if m.updated_at else None
            })
            
        return {
            "status": "success",
            "data": data,
            "pagination": {
                "total": pagination.total,
                "page": pagination.page,
                "per_page": pagination.per_page,
                "pages": pagination.pages
            }
        }

    is_default_query = (not q and not category and not status and not plan and page == 1 and per_page == 500)
    if is_default_query:
        payload = CacheService.get_global_modules(_fetch_modules_payload)
    else:
        payload = _fetch_modules_payload()

    return jsonify(payload), 200


@modules_bp.route('/dashboard', methods=['GET'])
@jwt_required()
@super_admin_required()
@sub_role_required('modules')
def get_dashboard_kpis():
    """Calculates KPI counts for modules registry dashboard"""
    total = Module.query.filter_by(is_archived=False).count()
    active = Module.query.filter_by(is_archived=False, status='Active').count()
    inactive = Module.query.filter_by(is_archived=False, status='Inactive').count()
    premium = Module.query.filter_by(is_archived=False, premium_feature=True).count()
    ai = Module.query.filter_by(is_archived=False, ai_enabled=True).count()
    system = Module.query.filter_by(is_archived=False, system_module=True).count()
    beta = Module.query.filter_by(is_archived=False, beta_feature=True).count()
    deprecated = Module.query.filter_by(is_archived=False, status='Deprecated').count()
    
    return jsonify({
        "status": "success",
        "data": {
            "total": total,
            "active": active,
            "inactive": inactive,
            "premium": premium,
            "ai": ai,
            "system": system,
            "beta": beta,
            "deprecated": deprecated
        }
    }), 200


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: get_module_details (Lines 339-445)
# Reason: Unused module details endpoint. Details are retrieved via list endpoint.
# ==============================================================================
# @modules_bp.route('/<int:module_id>', methods=['GET'])
# @jwt_required()
# @super_admin_required()
# def get_module_details(module_id):
#     """Returns complete module payload with dependencies, plans and audit logs"""
#     m = Module.query.get_or_404(module_id)
#     
#     # Dependencies
#     deps = [
#         {
#             "id": d.id,
#             "dependency_module_id": d.dependency_module_id,
#             "dependency_name": db.session.get(Module, d.dependency_module_id).name if db.session.get(Module, d.dependency_module_id) else "Unknown",
#             "dependency_type": d.dependency_type
#         } for d in m.dependencies
#     ]
#     
#     # Assignments
#     plans = [a.assigned_target for a in m.assignments if a.assigned_type == 'Plan']
#     orgs = [a.assigned_target for a in m.assignments if a.assigned_type == 'Organization']
#     industries = [a.assigned_target for a in m.assignments if a.assigned_type == 'Industry']
#     regions = [a.assigned_target for a in m.assignments if a.assigned_type == 'Region']
#     customer_types = [a.assigned_target for a in m.assignments if a.assigned_type == 'CustomerType']
#     required_mods = [{"id": dm.id, "name": dm.name, "code": dm.code} for dm in Module.query.filter(Module.id.in_(required_ids)).all()] if required_ids else []
#     blocked_mods = [{"id": dm.id, "name": dm.name, "code": dm.code} for dm in Module.query.filter(Module.id.in_(blocked_ids)).all()] if blocked_ids else []
#     parent_mods = [{"id": dm.id, "name": dm.name, "code": dm.code} for dm in Module.query.filter(Module.id.in_(parent_ids)).all()] if parent_ids else []
#     child_mods = [{"id": dm.id, "name": dm.name, "code": dm.code} for dm in Module.query.filter(Module.id.in_(child_ids)).all()] if child_ids else []

#     # Permissions
#     perms = {}
#     for p in m.permissions:
#         perms[p.role_name] = p.permissions

#     # Audit Logs
#     logs = [{
#         "id": l.id,
#         "admin": l.admin_name,
#         "action": l.action,
#         "details": l.details,
#         "timestamp": l.timestamp.isoformat() if l.timestamp else None
#     } for l in sorted(m.audit_logs, key=lambda x: x.timestamp or datetime.min, reverse=True)]

#     # Usage Analytics simulation
#     # Orgs using this module
#     assigned_orgs = Organization.query.filter(
#         (Organization.is_deleted == False) &
#         (
#             (Organization.subscription_plan.in_(plans)) |
#             (Organization.id.in_(orgs))
#         )
#     ).all()
#     org_list = [{"id": o.id, "name": o.name, "plan": o.subscription_plan, "status": o.subscription_status} for o in assigned_orgs]

#     analytics_data = {
#         "organizations_using": len(org_list),
#         "active_users": sum(len(o.users) for o in assigned_orgs[:5]) + (len(org_list) * 4),
#         "daily_usage": len(org_list) * 25,
#         "monthly_usage": len(org_list) * 750,
#         "api_calls": len(org_list) * 12500,
#         "storage_consumption_mb": sum(o.storage_used_mb or 0 for o in assigned_orgs),
#         "performance_ms": 120 + (module_id * 5) % 80,
#         "error_rate": round(0.12 + (module_id * 0.05) % 0.8, 2),
#         "most_used_features": ["Dashboard Overview", "Data Export", "Search Filtering"],
#         "least_used_features": ["Advanced Settings Override"],
#         "growth_trend": "+12.5% MoM"
#     }

#     return jsonify({
#         "status": "success",
#         "data": {
#             "id": m.id,
#             "name": m.name,
#             "code": m.code,
#             "description": m.description,
#             "category": m.category,
#             "icon": m.icon,
#             "color": m.color,
#             "display_order": m.display_order,
#             "navigation_route": m.navigation_route,
#             "status": m.status,
#             "version": m.version,
#             "enable_by_default": m.enable_by_default,
#             "visible_in_sidebar": m.visible_in_sidebar,
#             "visible_in_dashboard": m.visible_in_dashboard,
#             "requires_license": m.requires_license,
#             "requires_subscription": m.requires_subscription,
#             "premium_feature": m.premium_feature,
#             "ai_enabled": m.ai_enabled,
#             "beta_feature": m.beta_feature,
#             "system_module": m.system_module,
#             "feature_flags": m.feature_flags,
#             "assignments": {
#                 "plans": plans,
#                 "orgs": org_list,
#                 "industries": industries,
#                 "regions": regions,
#                 "customer_types": customer_types
#             },
#             "dependencies": {
#                 "required": required_mods,
#                 "blocked": blocked_mods,
#                 "parent": parent_mods,
#                 "child": child_mods
#             },
#             "permissions": perms,
#             "analytics": analytics_data,
#             "audit_logs": logs
#         }
#     }), 200
# [END DEAD CODE: get_module_details]



@modules_bp.route('', methods=['POST'])
@jwt_required()
@super_admin_required()
@sub_role_write_required('modules')
def create_module():
    """Creates a new module from the multi-step Onboarding Wizard"""
    data = request.json or {}
    
    # Step 1: Basic Info validation
    name = data.get('name', '').strip()
    code = data.get('code', '').strip().lower()
    desc = data.get('description', '').strip()
    category = data.get('category', 'Core').strip()
    icon = data.get('icon', 'package').strip()
    color = data.get('color', '#3b82f6').strip()
    display_order = int(data.get('display_order', 0))
    nav_route = data.get('navigation_route', '').strip()
    
    if not name or not code:
        return jsonify({"status": "error", "message": "Module Name and unique Code are required"}), 400
        
    # Check uniqueness
    if Module.query.filter_by(code=code).first():
        return jsonify({"status": "error", "message": f"Module with code '{code}' already exists"}), 400
    if nav_route and Module.query.filter_by(navigation_route=nav_route).first():
        return jsonify({"status": "error", "message": f"Module with route '{nav_route}' already exists"}), 400
        
    # Step 2: Configuration flags
    enable_by_default = bool(data.get('enable_by_default', False))
    visible_in_sidebar = bool(data.get('visible_in_sidebar', True))
    visible_in_dashboard = bool(data.get('visible_in_dashboard', True))
    requires_license = bool(data.get('requires_license', False))
    requires_subscription = bool(data.get('requires_subscription', True))
    premium_feature = bool(data.get('premium_feature', False))
    ai_enabled = bool(data.get('ai_enabled', False))
    beta_feature = bool(data.get('beta_feature', False))
    system_module = bool(data.get('system_module', False))
    
    # Feature flags configurations
    feature_flags = {
        "beta": beta_feature,
        "experimental": bool(data.get('experimental', False)),
        "internal_only": bool(data.get('internal_only', False)),
        "premium_only": premium_feature,
        "trial_only": bool(data.get('trial_only', False)),
        "government_only": bool(data.get('government_only', False)),
        "education_only": bool(data.get('education_only', False)),
        "enterprise_only": premium_feature
    }
    
    m = Module(
        name=name, code=code, description=desc, category=category,
        icon=icon, color=color, display_order=display_order, navigation_route=nav_route,
        status='Active', version='1.0.0',
        enable_by_default=enable_by_default, visible_in_sidebar=visible_in_sidebar,
        visible_in_dashboard=visible_in_dashboard, requires_license=requires_license,
        requires_subscription=requires_subscription, premium_feature=premium_feature,
        ai_enabled=ai_enabled, beta_feature=beta_feature, system_module=system_module,
        feature_flags=feature_flags
    )
    db.session.add(m)
    db.session.flush() # Populate m.id
    
    # Step 3: Plan assignment
    plans = data.get('plans', ['Professional', 'Enterprise'])
    for p in plans:
        assign = ModuleAssignment(module_id=m.id, assigned_type='Plan', assigned_target=p)
        db.session.add(assign)
        
    # Step 4: Permission assignment
    perms = data.get('permissions', {})
    for role, permissions_dict in perms.items():
        pm = ModulePermission(module_id=m.id, role_name=role, permissions=permissions_dict)
        db.session.add(pm)
        
    # Step 5: Dependencies
    dep_required = data.get('required_modules', [])
    for dep_id in dep_required:
        dep = ModuleDependency(module_id=m.id, dependency_module_id=int(dep_id), dependency_type='Required')
        db.session.add(dep)
        
    dep_blocked = data.get('blocked_modules', [])
    for dep_id in dep_blocked:
        dep = ModuleDependency(module_id=m.id, dependency_module_id=int(dep_id), dependency_type='Blocked')
        db.session.add(dep)
        
    db.session.commit()
    
    _log_module_action(m.id, "CREATE", f"Module '{name}' ({code}) successfully registered and assigned.")
    
    return jsonify({"status": "success", "message": "Module created successfully", "module_id": m.id}), 201


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: update_module (Lines 520-574)
# Reason: Unused module editor.
# ==============================================================================
# @modules_bp.route('/<int:module_id>', methods=['PUT'])
# @jwt_required()
# @super_admin_required()
# def update_module(module_id):
#     """Updates basic module configurations and feature flags"""
#     m = Module.query.get_or_404(module_id)
#     data = request.json or {}

#     name = data.get('name', '').strip()
#     category = data.get('category', '').strip()
#     desc = data.get('description', '').strip()
#     icon = data.get('icon', m.icon).strip()
#     color = data.get('color', m.color).strip()
#     display_order = data.get('display_order')
#     version = data.get('version', m.version).strip()

#     if name: m.name = name
#     if category: m.category = category
#     if desc: m.description = desc
#     if icon: m.icon = icon
#     if color: m.color = color
#     if display_order is not None: m.display_order = int(display_order)
#     if version: m.version = version

#     m.enable_by_default = bool(data.get('enable_by_default', m.enable_by_default))
#     m.visible_in_sidebar = bool(data.get('visible_in_sidebar', m.visible_in_sidebar))
#     m.visible_in_dashboard = bool(data.get('visible_in_dashboard', m.visible_in_dashboard))
#     m.requires_license = bool(data.get('requires_license', m.requires_license))
#     m.requires_subscription = bool(data.get('requires_subscription', m.requires_subscription))
#     m.premium_feature = bool(data.get('premium_feature', m.premium_feature))
#     m.ai_enabled = bool(data.get('ai_enabled', m.ai_enabled))
#     m.beta_feature = bool(data.get('beta_feature', m.beta_feature))

#     # Update feature flags
#     ff = m.feature_flags or {}
#     ff.update(data.get('feature_flags', {}))
#     m.feature_flags = ff

#     if 'status' in data and data['status']:
#         m.status = data['status']

#     db.session.commit()
#     _log_module_action(m.id, "UPDATE", f"Configuration updated: {list(data.keys())}")

#     try:
#         from app.domain.services.cache_service import CacheService
#         CacheService.invalidate_global_modules()
#     except Exception:
#         pass

#     from app.domain.services.feature_engine import FeatureEngine
#     FeatureEngine.invalidate()
#     FeatureEngine.broadcast_change(m.code, m.status == 'Active')

#     return jsonify({"status": "success", "message": "Module updated successfully"}), 200
# [END DEAD CODE: update_module]



@modules_bp.route('/<int:module_id>/enable', methods=['POST'])
@jwt_required()
@super_admin_required()
@sub_role_write_required('modules')
def enable_module(module_id):
    """Enables a module"""
    m = Module.query.get_or_404(module_id)
    
    # Validate dependencies before enabling
    # If this module depends on others, they should be Active.
    for dep in m.dependencies:
        if dep.dependency_type == 'Required':
            target = db.session.get(Module, dep.dependency_module_id)
            if not target or target.status != 'Active':
                return jsonify({
                    "status": "error",
                    "message": f"Cannot enable module. Required dependency '{target.name if target else 'Unknown'}' is inactive."
                }), 400
                
    m.status = 'Active'
    db.session.commit()
    _log_module_action(m.id, "ENABLE", "Module status set to Active.")
    
    try:
        from app.domain.services.cache_service import CacheService
        CacheService.invalidate_global_modules()
    except Exception:
        pass

    from app.domain.services.feature_engine import FeatureEngine
    FeatureEngine.invalidate()
    FeatureEngine.broadcast_change(m.code, True)
    
    return jsonify({"status": "success", "message": "Module enabled successfully"}), 200


@modules_bp.route('/<int:module_id>/disable', methods=['POST'])
@jwt_required()
@super_admin_required()
@sub_role_write_required('modules')
def disable_module(module_id):
    """Disables a module"""
    m = Module.query.get_or_404(module_id)
        
    # Check impact analysis: are there active modules depending on this one?
    dependents = ModuleDependency.query.filter_by(dependency_module_id=m.id, dependency_type='Required').all()
    active_dependents = []
    for d in dependents:
        parent = db.session.get(Module, d.module_id)
        if parent and parent.status == 'Active':
            active_dependents.append(parent.name)
            
    if active_dependents:
        return jsonify({
            "status": "error",
            "message": f"Cannot disable module. The following active modules depend on it: {', '.join(active_dependents)}"
        }), 400
        
    m.status = 'Inactive'
    db.session.commit()
    _log_module_action(m.id, "DISABLE", "Module status set to Inactive.")
    
    try:
        from app.domain.services.cache_service import CacheService
        CacheService.invalidate_global_modules()
    except Exception:
        pass

    from app.domain.services.feature_engine import FeatureEngine
    FeatureEngine.invalidate()
    FeatureEngine.broadcast_change(m.code, False)
    
    return jsonify({"status": "success", "message": "Module disabled successfully"}), 200


@modules_bp.route('/<int:module_id>/plan-assignment', methods=['POST'])
@jwt_required()
@super_admin_required()
@sub_role_write_required('modules')
def assign_plans(module_id):
    """Updates the list of plans that have access to this module"""
    m = Module.query.get_or_404(module_id)
    data = request.json or {}
    plans = data.get('plans', [])
    
    # Remove existing Plan assignments
    ModuleAssignment.query.filter_by(module_id=m.id, assigned_type='Plan').delete()
    
    for p in plans:
        assign = ModuleAssignment(module_id=m.id, assigned_type='Plan', assigned_target=p)
        db.session.add(assign)
        
    db.session.commit()
    _log_module_action(m.id, "ASSIGN_PLAN", f"Assigned plans updated to: {', '.join(plans)}")
    
    return jsonify({"status": "success", "message": "Plan assignments updated successfully"}), 200


@modules_bp.route('/<int:module_id>/org-assignment', methods=['POST'])
@jwt_required()
@super_admin_required()
@sub_role_write_required('modules')
def assign_organizations(module_id):
    """Updates explicit organization / industry / region assignments for pilot/beta targets"""
    m = Module.query.get_or_404(module_id)
    data = request.json or {}
    
    org_ids = data.get('org_ids', [])
    industries = data.get('industries', [])
    regions = data.get('regions', [])
    customer_types = data.get('customer_types', [])
    
    # Remove existing non-Plan assignments
    ModuleAssignment.query.filter(
        (ModuleAssignment.module_id == m.id) &
        (ModuleAssignment.assigned_type != 'Plan')
    ).delete()
    
    for o in org_ids:
        db.session.add(ModuleAssignment(module_id=m.id, assigned_type='Organization', assigned_target=str(o)))
    for ind in industries:
        db.session.add(ModuleAssignment(module_id=m.id, assigned_type='Industry', assigned_target=ind))
    for reg in regions:
        db.session.add(ModuleAssignment(module_id=m.id, assigned_type='Region', assigned_target=reg))
    for ct in customer_types:
        db.session.add(ModuleAssignment(module_id=m.id, assigned_type='CustomerType', assigned_target=ct))
        
    db.session.commit()
    _log_module_action(m.id, "ASSIGN_ORG", "Explicit organization pilot assignments updated.")
    
    return jsonify({"status": "success", "message": "Target organization assignments updated successfully"}), 200


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: update_permissions (Lines 706-724)
# Reason: Unused module permissions endpoint.
# ==============================================================================
# @modules_bp.route('/<int:module_id>/permissions', methods=['POST'])
# @jwt_required()
# @super_admin_required()
# def update_permissions(module_id):
#     """Updates permission settings mapping per role for this module"""
#     m = Module.query.get_or_404(module_id)
#     data = request.json or {}

#     # Clear existing permissions
#     ModulePermission.query.filter_by(module_id=m.id).delete()

#     for role, permissions_dict in data.items():
#         pm = ModulePermission(module_id=m.id, role_name=role, permissions=permissions_dict)
#         db.session.add(pm)

#     db.session.commit()
#     _log_module_action(m.id, "CHANGE_PERMISSION", f"Permissions configuration updated.")

#     return jsonify({"status": "success", "message": "Module permissions updated successfully"}), 200
# [END DEAD CODE: update_permissions]



@modules_bp.route('/<int:module_id>/duplicate', methods=['POST'])
@jwt_required()
@super_admin_required()
@sub_role_write_required('modules')
def duplicate_module(module_id):
    """Creates a copy of an existing module definition"""
    m = Module.query.get_or_404(module_id)
    
    name = f"{m.name} Copy"
    code = f"{m.code}-copy"
    nav_route = f"{m.navigation_route}-copy" if m.navigation_route else None
    
    if Module.query.filter_by(code=code).first():
        code = f"{code}-{int(datetime.now(timezone.utc).replace(tzinfo=None).timestamp())}"
        
    dup = Module(
        name=name, code=code, description=m.description, category=m.category,
        icon=m.icon, color=m.color, display_order=m.display_order + 1,
        navigation_route=nav_route, status='Inactive', version=m.version,
        enable_by_default=m.enable_by_default, visible_in_sidebar=m.visible_in_sidebar,
        visible_in_dashboard=m.visible_in_dashboard, requires_license=m.requires_license,
        requires_subscription=m.requires_subscription, premium_feature=m.premium_feature,
        ai_enabled=m.ai_enabled, beta_feature=m.beta_feature, system_module=False,
        feature_flags=m.feature_flags
    )
    db.session.add(dup)
    db.session.commit()
    
    _log_module_action(dup.id, "CREATE", f"Duplicated from module ID {m.id} ({m.name})")
    
    return jsonify({"status": "success", "message": "Module duplicated successfully", "module_id": dup.id}), 201


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: delete_module (Lines 759-772)
# Reason: Hard deletion of system modules.
# ==============================================================================
# @modules_bp.route('/<int:module_id>', methods=['DELETE'])
# @jwt_required()
# @super_admin_required()
# def delete_module(module_id):
#     """Deletes a module if it is not a system module"""
#     m = Module.query.get_or_404(module_id)
#     if m.system_module:
#         return jsonify({"status": "error", "message": "Core system modules cannot be deleted"}), 400

#     m.is_archived = True
#     db.session.commit()
#     _log_module_action(m.id, "DELETE", f"Module archived and soft-deleted.")

#     return jsonify({"status": "success", "message": "Module deleted successfully"}), 200
# [END DEAD CODE: delete_module]

